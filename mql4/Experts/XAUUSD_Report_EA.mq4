//+------------------------------------------------------------------+
//| XAUUSD_Report_EA.mq4                                               |
//|                                                                    |
//| Live MQL4 port of xauusd_indicators' pipeline.py + the four        |
//| signals/section*.py entry/exit variants, wired to real order       |
//| execution (OrderSend/OrderClose) - the piece the Python project    |
//| explicitly scoped OUT (docs/PRD.md ss0: "does not track positions, |
//| size lots, place orders, or talk to a broker/MT4 terminal...       |
//| those come later, if at all, in a separate phase"). This IS that   |
//| separate phase, built at the user's explicit request.              |
//|                                                                    |
//| ============================================================      |
//| UNVERIFIED - READ BEFORE USING ON ANY ACCOUNT, INCLUDING DEMO      |
//| ============================================================      |
//| This sandbox has no MQL4 compiler and no MetaTrader terminal - this|
//| file has NEVER been compiled. Every indicator formula was          |
//| translated line-by-line from the Python incremental functions      |
//| (already tested, 75/75 passing, including bar-for-bar incremental- |
//| vs-vectorized cross-checks) - see XAUUSD_Indicators.mqh/            |
//| XAUUSD_Signals.mqh's header comments for exactly what each function|
//| mirrors. The order-execution/position-management code below is     |
//| NEW - it has no Python equivalent to cross-check against at all,    |
//| since that was explicitly out of scope there. Open this in real    |
//| MetaEditor, fix whatever it flags, and follow mql4/README.md's     |
//| manual verification plan (side-by-side against scripts/demo.py's   |
//| output on the same historical data, then real demo-account paper   |
//| trading for an extended period) before ever considering a live     |
//| account - and even then, HARD_STOP_ATR_MULTIPLE, TRAIL_ATR_MULTIPLE|
//| and PROFIT_TARGET_USD's price-conversion assumption are all        |
//| UNCONFIRMED PLACEHOLDERS (docs/PRD.md ss6.4/ss6.5), not real        |
//| numbers - this EA is built, per the user's explicit choice, to run |
//| on a DEMO account with those placeholders until real numbers are   |
//| confirmed. InpRequireDemoAccount enforces this at OnInit(), but    |
//| verify manually too - do not rely on the code alone.                |
//+------------------------------------------------------------------+
#property strict
#property copyright "Built from xauusd_indicators (Python) - see docs/PRD.md"

#include <XAUUSD_Indicators.mqh>
#include <XAUUSD_Signals.mqh>

enum ENUM_VARIANT
  {
   VARIANT_SECTION_2,   // Section 2 (core)
   VARIANT_SECTION_6,   // Section 6 (+ ROC/OBV/MACD agreement)
   VARIANT_SECTION_6A,  // Section 6a (+ Parabolic SAR agreement)
   VARIANT_SECTION_7    // Section 7 ($15 target / 30-bar cutoff exit)
  };

input ENUM_VARIANT InpVariant             = VARIANT_SECTION_2; // Report variant to trade
input double       InpLotSize             = 0.01;              // Fixed lot size (the report's own stated default)
input int          InpMagicNumber         = 20260809;
input int          InpSlippage            = 5;                 // Max slippage, points
input int          InpWarmupBars          = 200;                // Historical bars to warm up indicator state before trading
input bool         InpRequireDemoAccount  = true;                // Refuse to run unless the account reports as DEMO - see header comment

//====================================================================
// Position state - mirrors types.py's PositionState, extended with
// what live order execution actually needs (no Python equivalent -
// this part is new, see header comment).
//====================================================================
bool     g_inPosition          = false;
int      g_positionDirection   = 0;      // 1 = LONG, -1 = SHORT
double   g_entryPrice          = 0.0;
double   g_atrAtEntry          = 0.0;
double   g_extremeSinceEntry   = 0.0;
int      g_barsSinceEntry      = 0;
int      g_orderTicket         = -1;

datetime g_lastBarTime         = 0;
bool     g_tradingDisabled     = false;

//====================================================================
bool IsDemoAccount()
{
   return AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_DEMO;
}

int OnInit()
{
   if(Period() != PERIOD_M1)
     {
      Alert("XAUUSD_Report_EA: this system was built and tested for M1 bars only (docs/PRD.md). Attach it to an M1 chart.");
      return(INIT_FAILED);
     }

   if(InpRequireDemoAccount && !IsDemoAccount())
     {
      Alert("XAUUSD_Report_EA: refusing to run - this account does not report as DEMO, and InpRequireDemoAccount is true. ",
            "This EA uses UNCONFIRMED placeholder risk parameters (docs/PRD.md ss6.4/ss6.5) and must not run on a live account ",
            "until those are confirmed. See mql4/README.md.");
      Print("XAUUSD_Report_EA: ACCOUNT_TRADE_MODE=", AccountInfoInteger(ACCOUNT_TRADE_MODE),
            " (expected ACCOUNT_TRADE_MODE_DEMO=", ACCOUNT_TRADE_MODE_DEMO, ")");
      return(INIT_FAILED);
     }

   int warmup = MathMin(InpWarmupBars, Bars - 2);
   if(warmup < 40) // MACD alone needs 34 bars before its first real value; ADX needs roughly as many
     {
      Alert("XAUUSD_Report_EA: not enough chart history to warm up indicators (need >= 40 bars, have ", Bars, "). ",
            "Scroll the chart back to load more history, then reattach the EA.");
      return(INIT_FAILED);
     }

   Print("XAUUSD_Report_EA: warming up indicator state over ", warmup, " historical bars...");
   for(int i = warmup; i >= 1; i--)
      ProcessClosedBar(i, true);

   g_lastBarTime = Time[0];
   Print("XAUUSD_Report_EA: warmup complete. Variant=", EnumToString(InpVariant),
         " LotSize=", InpLotSize, " Demo=", IsDemoAccount());
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   Print("XAUUSD_Report_EA: stopping, reason=", reason,
         g_inPosition ? " - a position is still open, this EA does NOT close it automatically on removal." : "");
}

void OnTick()
{
   if(g_tradingDisabled) return;

   // Re-check every bar, not just at OnInit - cheap, and catches an
   // account-type change mid-session (e.g. a broker-side switch)
   // rather than trusting a check made once at attach time.
   if(InpRequireDemoAccount && !IsDemoAccount())
     {
      if(!g_tradingDisabled)
         Alert("XAUUSD_Report_EA: account no longer reports as DEMO - disabling further trading. Existing positions are NOT auto-closed.");
      g_tradingDisabled = true;
      return;
     }

   if(Time[0] == g_lastBarTime) return; // still the same forming bar
   g_lastBarTime = Time[0];
   ProcessClosedBar(1, false); // bar index 1 = the bar that just closed
}

//====================================================================
// Computes every indicator for one closed bar, then (unless warmupOnly)
// manages any open position and evaluates entry for the configured
// variant. warmupOnly=true is used only during OnInit()'s historical
// pass, to build up indicator state without placing any orders.
//====================================================================
void ProcessClosedBar(int shift, bool warmupOnly)
{
   double o = Open[shift];
   double h = High[shift];
   double l = Low[shift];
   double c = Close[shift];
   double v = (double)Volume[shift];

   double atrVal;    bool atrOk    = ATR_Update(h, l, c, atrVal);
   double volRatio;  bool volOk    = VolatilityRatio_Update(atrVal, atrOk, volRatio);
   double adxVal;    bool adxOk    = ADX_Update(h, l, atrVal, atrOk, adxVal);
   double rviVal;    int  rviRaw;  bool rviOk    = RVI_Update(o, h, l, c, rviVal, rviRaw);
   double rocVal;    bool rocOk    = ROC_Update(c, rocVal);
   double obvVal, obvSlope; bool obvSlopeOk; bool obvOk = OBV_Update(c, v, obvVal, obvSlope, obvSlopeOk);
   double macdVal;   bool macdOk   = MACD_Update(c, macdVal);
   double sarVal;    int  sarDir;  bool sarOk    = SAR_Update(h, l, c, sarVal, sarDir);

   if(warmupOnly) return;

   int rviTrigger = rviOk ? rviRaw : 0;
   int section2Signal = Section2Entry(rviTrigger, adxOk, adxVal, volOk, volRatio);

   int entrySignal = 0;
   switch(InpVariant)
     {
      case VARIANT_SECTION_2:
         entrySignal = section2Signal;
         break;
      case VARIANT_SECTION_6:
         entrySignal = Section6Entry(section2Signal, rocOk, rocVal, obvSlopeOk, obvSlope, macdOk, macdVal);
         break;
      case VARIANT_SECTION_6A:
         entrySignal = Section6aEntry(section2Signal, sarOk, sarDir);
         break;
      case VARIANT_SECTION_7:
         entrySignal = section2Signal; // Section 7 shares Section 2's entry (section7.py)
         break;
     }

   if(g_inPosition)
     {
      g_barsSinceEntry++;
      if(g_positionDirection == 1) g_extremeSinceEntry = MathMax(g_extremeSinceEntry, h);
      else                         g_extremeSinceEntry = MathMin(g_extremeSinceEntry, l);

      bool exitNow;
      if(InpVariant == VARIANT_SECTION_7)
         exitNow = Section7Exit(g_positionDirection, g_entryPrice, g_atrAtEntry, h, l, g_barsSinceEntry, rviTrigger);
      else
         exitNow = Section2Exit(g_positionDirection, g_entryPrice, g_atrAtEntry, g_extremeSinceEntry,
                                 h, l, g_barsSinceEntry, rviTrigger);

      if(exitNow) ClosePosition();
      // Single-position-at-a-time model, matching PositionState (docs/PRD.md
      // ss3 notes the report's single-pyramid-add rule isn't implemented in
      // Python either) - never opens a new position the same bar it just
      // held or closed one.
      return;
     }

   if(entrySignal != 0)
      OpenPosition(entrySignal, atrVal, atrOk);
}

//====================================================================
// Order execution - NEW code, no Python equivalent (see header
// comment). Places a broker-side stop-loss at the same hard-stop level
// Section2Exit/Section7Exit would otherwise only detect on the next
// bar close - a real safety addition beyond what the Python model
// specifies, so a terminal/connection drop doesn't leave the position
// completely unprotected.
//====================================================================
void OpenPosition(int direction, double atrValue, bool atrReady)
{
   if(!atrReady) return; // can't compute a hard-stop level without ATR - refuse to enter

   double price = (direction == 1) ? Ask : Bid;
   double hardStopLevel = (direction == 1)
                           ? price - HARD_STOP_ATR_MULTIPLE * atrValue
                           : price + HARD_STOP_ATR_MULTIPLE * atrValue;
   int cmd = (direction == 1) ? OP_BUY : OP_SELL;

   int ticket = OrderSend(Symbol(), cmd, InpLotSize, price, InpSlippage, hardStopLevel, 0,
                           "XAUUSD_Report_EA " + EnumToString(InpVariant), InpMagicNumber, 0,
                           direction == 1 ? clrLime : clrRed);
   if(ticket < 0)
     {
      Print("XAUUSD_Report_EA: OrderSend failed, error ", GetLastError());
      return;
     }

   g_inPosition = true;
   g_positionDirection = direction;
   g_entryPrice = price;
   g_atrAtEntry = atrValue;
   g_extremeSinceEntry = price;
   g_barsSinceEntry = 0;
   g_orderTicket = ticket;

   Print("XAUUSD_Report_EA: opened ", (direction == 1 ? "LONG" : "SHORT"),
         " ticket=", ticket, " price=", price, " hardStop=", hardStopLevel, " atr=", atrValue);
}

void ClosePosition()
{
   if(!OrderSelect(g_orderTicket, SELECT_BY_TICKET))
     {
      Print("XAUUSD_Report_EA: could not select ticket ", g_orderTicket, " to close, error ", GetLastError());
      ResetPositionState();
      return;
     }

   double closePrice = (g_positionDirection == 1) ? Bid : Ask;
   bool ok = OrderClose(g_orderTicket, OrderLots(), closePrice, InpSlippage, clrYellow);
   if(!ok)
      Print("XAUUSD_Report_EA: OrderClose failed for ticket ", g_orderTicket, ", error ", GetLastError());
   else
      Print("XAUUSD_Report_EA: closed ticket ", g_orderTicket, " at ", closePrice);

   ResetPositionState();
}

void ResetPositionState()
{
   g_inPosition = false;
   g_positionDirection = 0;
   g_entryPrice = 0.0;
   g_atrAtEntry = 0.0;
   g_extremeSinceEntry = 0.0;
   g_barsSinceEntry = 0;
   g_orderTicket = -1;
}

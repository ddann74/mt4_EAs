//+------------------------------------------------------------------+
//| XAUUSD_Signals.mqh                                                 |
//|                                                                    |
//| MQL4 port of xauusd_indicators/signals/section2.py / section6.py / |
//| section6a.py / section7.py's entry_signal()/exit_fired() - same    |
//| composition logic, same UNCONFIRMED placeholder constants,        |
//| carried over unchanged (per the user's explicit choice: use the   |
//| documented placeholders, demo account only, until real numbers    |
//| are confirmed - see docs/PRD.md ss6.4/ss6.5 and this repo's       |
//| README "What's still a stand-in").                                 |
//|                                                                    |
//| UNVERIFIED - see XAUUSD_Indicators.mqh's header comment; the same  |
//| disclosure applies here.                                          |
//+------------------------------------------------------------------+
#property strict

// Section 2 (core) entry thresholds - docs/PRD.md ss2.1/ss2.2, not open questions.
#define ADX_THRESHOLD 30.0
#define VOLATILITY_RATIO_THRESHOLD 1.1

// UNCONFIRMED PLACEHOLDER PARAMETERS - see signals/section2.py's module
// docstring. Standard ATR-multiple stop convention, not a guess at the
// report's actual intended numbers. Demo-account use only until real
// numbers are confirmed (user's explicit choice this session).
#define HARD_STOP_ATR_MULTIPLE 2.0
#define TRAIL_ATR_MULTIPLE 1.5

// Section 7 - see signals/section7.py's module docstring for both the
// exit-composition reading and the $15-to-price-distance assumption.
#define PROFIT_TARGET_USD 15.0
#define TIME_CUTOFF_BARS 30
#define NOTIONAL_OZ_PER_POSITION 1.0 // UNCONFIRMED assumption - see section7.py

//====================================================================
// Entry composition
//====================================================================

// Mirrors section2.py's entry_signal(): returns 0 / 1 (LONG) / -1 (SHORT).
int Section2Entry(int rviTrigger, bool adxReady, double adxValue, bool volReady, double volRatio)
{
   if(rviTrigger == 0) return 0;
   if(!adxReady || !volReady) return 0;
   if(adxValue > ADX_THRESHOLD && volRatio > VOLATILITY_RATIO_THRESHOLD)
      return rviTrigger;
   return 0;
}

// Mirrors section6.py's entry_signal(): Section 2's signal AND
// ROC/OBV-slope/MACD-histogram all agree with its direction.
int Section6Entry(int section2Signal,
                   bool rocReady, double rocValue,
                   bool obvReady, double obvSlope,
                   bool macdReady, double macdHist)
{
   if(section2Signal == 0) return 0;
   if(!rocReady || !obvReady || !macdReady) return 0;

   if(section2Signal == 1) // LONG
     {
      if(rocValue > 0 && obvSlope > 0 && macdHist > 0) return 1;
      return 0;
     }
   else // SHORT
     {
      if(rocValue < 0 && obvSlope < 0 && macdHist < 0) return -1;
      return 0;
     }
}

// Mirrors section6a.py's entry_signal(): Section 2's signal AND
// Parabolic SAR direction agrees.
int Section6aEntry(int section2Signal, bool sarReady, int sarDirection)
{
   if(section2Signal == 0 || !sarReady) return 0;
   if(sarDirection == section2Signal) return section2Signal;
   return 0;
}

// Section 7 shares Section 2's entry exactly (section7.py: `entry_signal
// = section2_entry_signal`) - callers just call Section2Entry() directly
// for SECTION_7, no separate function needed.

//====================================================================
// Exit composition
//
// direction: 1 = LONG, -1 = SHORT (matches PositionState.direction)
// extremeSinceEntry: highest high seen since entry (LONG) or lowest low
//   seen since entry (SHORT) - the EA tracks this incrementally bar by
//   bar rather than re-scanning history each time, unlike the Python
//   vectorized version's window_highs.max()/window_lows.min() (which
//   operates over the whole stored DataFrame) - mathematically the same
//   result, just computed incrementally since a live EA only ever sees
//   one new bar at a time.
//====================================================================

// Mirrors section2.py's exit_fired() (also used unchanged by Section 6
// and Section 6a, per their own re-export comments).
bool Section2Exit(int direction, double entryPrice, double atrAtEntry, double extremeSinceEntry,
                   double currentHigh, double currentLow, int barsSinceEntry, int rviTrigger)
{
   bool isLong = (direction == 1);

   // Hard stop.
   if(isLong)
     {
      double hardStopLevel = entryPrice - HARD_STOP_ATR_MULTIPLE * atrAtEntry;
      if(currentLow <= hardStopLevel) return true;
     }
   else
     {
      double hardStopLevel = entryPrice + HARD_STOP_ATR_MULTIPLE * atrAtEntry;
      if(currentHigh >= hardStopLevel) return true;
     }

   // Trailing stop, off the running extreme since entry.
   if(isLong)
     {
      double trailingLevel = extremeSinceEntry - TRAIL_ATR_MULTIPLE * atrAtEntry;
      if(currentLow <= trailingLevel) return true;
     }
   else
     {
      double trailingLevel = extremeSinceEntry + TRAIL_ATR_MULTIPLE * atrAtEntry;
      if(currentHigh >= trailingLevel) return true;
     }

   // RVI reversal - opposite-direction trigger on a bar after entry.
   int opposite = isLong ? -1 : 1;
   if(barsSinceEntry > 0 && rviTrigger == opposite) return true;

   return false;
}

// Mirrors section7.py's exit_fired(): hard stop + RVI reversal
// (unchanged from Section 2, per that module's UNCONFIRMED reading -
// see its docstring) OR $15 profit target OR 30-bar time cutoff. No
// trailing stop for Section 7.
bool Section7Exit(int direction, double entryPrice, double atrAtEntry,
                   double currentHigh, double currentLow, int barsSinceEntry, int rviTrigger)
{
   bool isLong = (direction == 1);

   // Hard stop (unchanged from Section 2).
   if(isLong)
     {
      double hardStopLevel = entryPrice - HARD_STOP_ATR_MULTIPLE * atrAtEntry;
      if(currentLow <= hardStopLevel) return true;
     }
   else
     {
      double hardStopLevel = entryPrice + HARD_STOP_ATR_MULTIPLE * atrAtEntry;
      if(currentHigh >= hardStopLevel) return true;
     }

   // RVI reversal (unchanged from Section 2).
   int opposite = isLong ? -1 : 1;
   if(barsSinceEntry > 0 && rviTrigger == opposite) return true;

   // $15 profit target.
   double priceTargetDistance = PROFIT_TARGET_USD / NOTIONAL_OZ_PER_POSITION;
   if(isLong)
     {
      double targetPrice = entryPrice + priceTargetDistance;
      if(currentHigh >= targetPrice) return true;
     }
   else
     {
      double targetPrice = entryPrice - priceTargetDistance;
      if(currentLow <= targetPrice) return true;
     }

   // 30-bar time cutoff.
   if(barsSinceEntry >= TIME_CUTOFF_BARS) return true;

   return false;
}

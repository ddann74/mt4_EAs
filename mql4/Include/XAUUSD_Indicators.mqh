//+------------------------------------------------------------------+
//| XAUUSD_Indicators.mqh                                             |
//|                                                                    |
//| MQL4 port of xauusd_indicators/indicators/*.py's INCREMENTAL       |
//| (_update) functions - not the vectorized ones, since those are    |
//| the ones docs/PRD.md ss4 explicitly designed to match how MQL4    |
//| indicators actually execute (one bar at a time, small persisted   |
//| state, never a whole-history array).                              |
//|                                                                    |
//| UNVERIFIED: this file has NOT been compiled in a real MetaEditor - |
//| this sandbox has no MQL4 compiler. Every formula below was        |
//| translated line-by-line from the already-tested Python            |
//| incremental functions (75/75 tests passing there, including a     |
//| bar-for-bar incremental-vs-vectorized cross-check per indicator)  |
//| - see each function's header comment for exactly which Python     |
//| function it mirrors. Compile this in real MetaEditor before       |
//| trusting it, and see mql4/README.md for the manual side-by-side   |
//| verification plan against the Python demo script.                 |
//|                                                                    |
//| Periods are hardcoded (14 / 10 / 12,26,9 / 0.02,0.20) rather than  |
//| made configurable, matching the fact that nothing in the Python    |
//| codebase ever calls these with anything but their documented       |
//| defaults either (docs/PRD.md ss2).                                 |
//+------------------------------------------------------------------+
#property strict

//====================================================================
// Shared Wilder-smoothing helper
//
// Mirrors app/../indicators/adx.py's _wilder_smooth() AND atr.py's
// atr_update()'s own smoothing stage - both are the exact same
// recurrence (seed = plain mean of the first `period` raw values,
// then smoothed[t] = (smoothed[t-1]*(period-1) + raw[t]) / period),
// so one reusable helper is used for all four places that recurrence
// appears (ATR/TR, ADX's +DM, ADX's -DM, ADX's DX) rather than
// duplicating it four times with four chances to diverge.
//====================================================================
bool WilderSmooth_Update(double &warmup[], int &warmupCount, int period,
                          bool &hasSmoothed, double &smoothed,
                          double raw, double &outValue)
{
   if(!hasSmoothed)
     {
      warmup[warmupCount] = raw;
      warmupCount++;
      if(warmupCount == period)
        {
         double sum = 0;
         for(int i = 0; i < period; i++) sum += warmup[i];
         smoothed = sum / period;
         hasSmoothed = true;
         outValue = smoothed;
         return true;
        }
      return false;
     }
   smoothed = (smoothed * (period - 1) + raw) / period;
   outValue = smoothed;
   return true;
}

//====================================================================
// ATR(14) - mirrors indicators/atr.py's atr_update()
//====================================================================
#define ATR_PERIOD 14

bool   g_atrHasPrevClose = false;
double g_atrPrevClose    = 0.0;
double g_atrWarmup[ATR_PERIOD];
int    g_atrWarmupCount  = 0;
bool   g_atrHasSmoothed  = false;
double g_atrSmoothed     = 0.0;

bool ATR_Update(double high, double low, double close, double &outValue)
{
   double tr;
   if(!g_atrHasPrevClose)
      tr = high - low;
   else
      tr = MathMax(high - low, MathMax(MathAbs(high - g_atrPrevClose), MathAbs(low - g_atrPrevClose)));

   g_atrPrevClose = close;
   g_atrHasPrevClose = true;

   return WilderSmooth_Update(g_atrWarmup, g_atrWarmupCount, ATR_PERIOD,
                               g_atrHasSmoothed, g_atrSmoothed, tr, outValue);
}

//====================================================================
// Volatility ratio = ATR(14) / SMA(ATR(14), 50)
// Mirrors indicators/atr.py's volatility_ratio_update()
//====================================================================
#define VOLRATIO_AVG_PERIOD 50

double g_volRatioHistory[VOLRATIO_AVG_PERIOD];
int    g_volRatioHistoryCount = 0;

bool VolatilityRatio_Update(double atrValue, bool atrReady, double &outRatio)
{
   if(!atrReady) return false;

   if(g_volRatioHistoryCount < VOLRATIO_AVG_PERIOD)
     {
      g_volRatioHistory[g_volRatioHistoryCount] = atrValue;
      g_volRatioHistoryCount++;
     }
   else
     {
      for(int i = 0; i < VOLRATIO_AVG_PERIOD - 1; i++) g_volRatioHistory[i] = g_volRatioHistory[i + 1];
      g_volRatioHistory[VOLRATIO_AVG_PERIOD - 1] = atrValue;
     }

   if(g_volRatioHistoryCount < VOLRATIO_AVG_PERIOD) return false;

   double sum = 0;
   for(int i = 0; i < VOLRATIO_AVG_PERIOD; i++) sum += g_volRatioHistory[i];
   double avg = sum / VOLRATIO_AVG_PERIOD;
   outRatio = atrValue / avg;
   return true;
}

//====================================================================
// ADX(14) - mirrors indicators/adx.py's adx_update()
//
// DESIGN NOTE (disclosed simplification, not a silent shortcut):
// Python's AdxState keeps its OWN independent AtrState for TR
// smoothing, separate from the top-level atr_update() call used for
// the standalone ATR/volatility-ratio indicator. Wilder smoothing is
// a deterministic recurrence with no path-dependence beyond "which
// raw values were seen, in which order" - so two independently-
// initialized instances fed the identical bar sequence from the
// identical starting point always produce identical output. This
// port therefore reuses the ONE shared ATR_Update() result (computed
// once per bar in ProcessClosedBar, see the .mq4 file) as ADX's DI
// denominator too, rather than maintaining a second, redundant TR-
// smoothing engine - mathematically equivalent, less code, less
// chance of the two silently drifting apart from a transcription slip.
//====================================================================
#define ADX_PERIOD 14

bool   g_adxHasPrevHL = false;
double g_adxPrevHigh  = 0.0;
double g_adxPrevLow   = 0.0;

double g_adxPlusDmWarmup[ADX_PERIOD];
int    g_adxPlusDmWarmupCount = 0;
bool   g_adxHasPlusDm = false;
double g_adxSmoothedPlusDm = 0.0;

double g_adxMinusDmWarmup[ADX_PERIOD];
int    g_adxMinusDmWarmupCount = 0;
bool   g_adxHasMinusDm = false;
double g_adxSmoothedMinusDm = 0.0;

double g_adxDxWarmup[ADX_PERIOD];
int    g_adxDxWarmupCount = 0;
bool   g_adxHasDx = false;
double g_adxSmoothedDx = 0.0;

bool ADX_Update(double high, double low, double atrValue, bool atrReady, double &outValue)
{
   double plusDm, minusDm;
   if(!g_adxHasPrevHL)
     {
      plusDm = 0.0;
      minusDm = 0.0;
     }
   else
     {
      double upMove = high - g_adxPrevHigh;
      double downMove = g_adxPrevLow - low;
      plusDm  = (upMove > downMove && upMove > 0)   ? upMove   : 0.0;
      minusDm = (downMove > upMove && downMove > 0) ? downMove : 0.0;
     }
   g_adxPrevHigh = high;
   g_adxPrevLow = low;
   g_adxHasPrevHL = true;

   double smPlusDm, smMinusDm;
   bool plusReady  = WilderSmooth_Update(g_adxPlusDmWarmup,  g_adxPlusDmWarmupCount,  ADX_PERIOD,
                                          g_adxHasPlusDm,  g_adxSmoothedPlusDm,  plusDm,  smPlusDm);
   bool minusReady = WilderSmooth_Update(g_adxMinusDmWarmup, g_adxMinusDmWarmupCount, ADX_PERIOD,
                                          g_adxHasMinusDm, g_adxSmoothedMinusDm, minusDm, smMinusDm);

   // Matches Python's exact check: "if atr_value is None or new_state.smoothed_plus_dm is None: return None"
   // (minusReady always matches plusReady's readiness - both warm up in lockstep, see WilderSmooth_Update).
   if(!atrReady || !plusReady) return false;

   double plusDi = 100.0 * smPlusDm / atrValue;
   double minusDi = 100.0 * smMinusDm / atrValue;
   double denom = plusDi + minusDi;
   double dx = (denom == 0.0) ? 0.0 : 100.0 * MathAbs(plusDi - minusDi) / denom;

   double smDx;
   bool dxReady = WilderSmooth_Update(g_adxDxWarmup, g_adxDxWarmupCount, ADX_PERIOD,
                                       g_adxHasDx, g_adxSmoothedDx, dx, smDx);
   if(!dxReady) return false;
   outValue = smDx;
   return true;
}

//====================================================================
// Custom RVI(14) + setup-then-cross trigger
// Mirrors indicators/rvi.py's rvi_update() - UNCONFIRMED formula/
// trigger per docs/PRD.md ss6.1/ss6.2, ported exactly as implemented
// in Python (not re-litigated here).
//====================================================================
#define RVI_PERIOD 14
#define RVI_THRESHOLD 0.20

double g_rviCoHistory[RVI_PERIOD];
double g_rviHlHistory[RVI_PERIOD];
int    g_rviHistoryCount = 0;
string g_rviArmed = ""; // "", "below", "above" - mirrors Python's armed: str | None

// outTrigger: 0 = none, 1 = LONG, -1 = SHORT
bool RVI_Update(double open_, double high, double low, double close, double &outRvi, int &outTrigger)
{
   double co = close - open_;
   double hl = high - low;

   if(g_rviHistoryCount < RVI_PERIOD)
     {
      g_rviCoHistory[g_rviHistoryCount] = co;
      g_rviHlHistory[g_rviHistoryCount] = hl;
      g_rviHistoryCount++;
     }
   else
     {
      for(int i = 0; i < RVI_PERIOD - 1; i++)
        {
         g_rviCoHistory[i] = g_rviCoHistory[i + 1];
         g_rviHlHistory[i] = g_rviHlHistory[i + 1];
        }
      g_rviCoHistory[RVI_PERIOD - 1] = co;
      g_rviHlHistory[RVI_PERIOD - 1] = hl;
     }

   outTrigger = 0;
   if(g_rviHistoryCount < RVI_PERIOD) return false;

   double sumCo = 0, sumHl = 0;
   for(int i = 0; i < RVI_PERIOD; i++)
     {
      sumCo += g_rviCoHistory[i];
      sumHl += g_rviHlHistory[i];
     }
   double denom = sumHl / RVI_PERIOD;
   double numer = sumCo / RVI_PERIOD;
   double rviValue = numer / denom;
   outRvi = rviValue;

   if(rviValue <= -RVI_THRESHOLD)
      g_rviArmed = "below";
   else if(rviValue >= RVI_THRESHOLD)
      g_rviArmed = "above";
   else
     {
      if(g_rviArmed == "below") { outTrigger = 1;  g_rviArmed = ""; }
      else if(g_rviArmed == "above") { outTrigger = -1; g_rviArmed = ""; }
     }
   return true;
}

//====================================================================
// ROC(10) - mirrors indicators/roc.py's roc_update()
//====================================================================
#define ROC_PERIOD 10

double g_rocHistory[ROC_PERIOD + 1];
int    g_rocHistoryCount = 0;

bool ROC_Update(double close, double &outValue)
{
   if(g_rocHistoryCount < ROC_PERIOD + 1)
     {
      g_rocHistory[g_rocHistoryCount] = close;
      g_rocHistoryCount++;
     }
   else
     {
      for(int i = 0; i < ROC_PERIOD; i++) g_rocHistory[i] = g_rocHistory[i + 1];
      g_rocHistory[ROC_PERIOD] = close;
     }
   if(g_rocHistoryCount < ROC_PERIOD + 1) return false;
   double prevClose = g_rocHistory[0];
   outValue = 100.0 * (close - prevClose) / prevClose;
   return true;
}

//====================================================================
// OBV + slope - mirrors indicators/obv.py's obv_update()
//====================================================================
#define OBV_LOOKBACK 10

bool   g_obvHasPrevClose = false;
double g_obvPrevClose    = 0.0;
double g_obvRunning      = 0.0;
double g_obvHistory[OBV_LOOKBACK + 1];
int    g_obvHistoryCount = 0;

bool OBV_Update(double close, double volume, double &outObv, double &outSlope, bool &outSlopeAvailable)
{
   double direction;
   if(!g_obvHasPrevClose) direction = 0.0;
   else if(close > g_obvPrevClose) direction = 1.0;
   else if(close < g_obvPrevClose) direction = -1.0;
   else direction = 0.0;
   g_obvPrevClose = close;
   g_obvHasPrevClose = true;

   g_obvRunning = g_obvRunning + direction * volume;
   outObv = g_obvRunning;

   if(g_obvHistoryCount < OBV_LOOKBACK + 1)
     {
      g_obvHistory[g_obvHistoryCount] = g_obvRunning;
      g_obvHistoryCount++;
     }
   else
     {
      for(int i = 0; i < OBV_LOOKBACK; i++) g_obvHistory[i] = g_obvHistory[i + 1];
      g_obvHistory[OBV_LOOKBACK] = g_obvRunning;
     }

   outSlopeAvailable = false;
   if(g_obvHistoryCount == OBV_LOOKBACK + 1)
     {
      outSlope = g_obvRunning - g_obvHistory[0];
      outSlopeAvailable = true;
     }
   return true; // OBV itself is always defined from bar 0 (running total starts at 0), matching Python
}

//====================================================================
// MACD histogram (12,26,9) - mirrors indicators/macd.py's
// macd_histogram_update()
//====================================================================
#define MACD_FAST   12
#define MACD_SLOW   26
#define MACD_SIGNAL 9

bool   g_macdHasEmaFast   = false;
double g_macdEmaFast      = 0.0;
bool   g_macdHasEmaSlow   = false;
double g_macdEmaSlow      = 0.0;
bool   g_macdHasEmaSignal = false;
double g_macdEmaSignal    = 0.0;
int    g_macdCount        = 0;

bool MACD_Update(double close, double &outHistogram)
{
   double alphaFast   = 2.0 / (MACD_FAST + 1);
   double alphaSlow   = 2.0 / (MACD_SLOW + 1);
   double alphaSignal = 2.0 / (MACD_SIGNAL + 1);

   g_macdEmaFast = g_macdHasEmaFast ? (alphaFast * close + (1 - alphaFast) * g_macdEmaFast) : close;
   g_macdHasEmaFast = true;
   g_macdEmaSlow = g_macdHasEmaSlow ? (alphaSlow * close + (1 - alphaSlow) * g_macdEmaSlow) : close;
   g_macdHasEmaSlow = true;

   double macdValue = g_macdEmaFast - g_macdEmaSlow;

   g_macdEmaSignal = g_macdHasEmaSignal ? (alphaSignal * macdValue + (1 - alphaSignal) * g_macdEmaSignal) : macdValue;
   g_macdHasEmaSignal = true;

   g_macdCount++;

   double histogram = macdValue - g_macdEmaSignal;
   int minBars = MACD_SLOW + MACD_SIGNAL - 1; // 34
   if(g_macdCount < minBars) return false;
   outHistogram = histogram;
   return true;
}

//====================================================================
// Parabolic SAR - mirrors indicators/parabolic_sar.py's
// parabolic_sar_update(). Needs the previous TWO bars' high/low
// (not just one), per that function's own doc comment.
//====================================================================
#define SAR_STEP 0.02
#define SAR_MAX  0.20

int    g_sarBarCount = 0; // 0, 1, or >=2 - tracks which warmup stage we're in
double g_sarPrevPrevHigh = 0.0, g_sarPrevPrevLow = 0.0;
double g_sarPrevHigh = 0.0, g_sarPrevLow = 0.0;
bool   g_sarUpTrend = true;
double g_sarAf = SAR_STEP;
double g_sarUpTrendHigh = 0.0;
double g_sarDownTrendLow = 0.0;
double g_sarPrevPsar = 0.0;

// outDirection: 0 = unavailable, 1 = LONG (price above SAR), -1 = SHORT
bool SAR_Update(double high, double low, double close, double &outSar, int &outDirection)
{
   outDirection = 0;

   if(g_sarBarCount == 0)
     {
      // Bar 0: seed extremes, no SAR value yet - matches Python's len(history)==0 branch.
      g_sarUpTrend = true;
      g_sarAf = SAR_STEP;
      g_sarUpTrendHigh = high;
      g_sarDownTrendLow = low;
      g_sarPrevHigh = high;
      g_sarPrevLow = low; // temporarily holds bar 0's H/L until bar 1 shifts it to "prevPrev"
      g_sarBarCount = 1;
      return false;
     }

   if(g_sarBarCount == 1)
     {
      // Bar 1: matches Python's psar.iloc[1] = close.iloc[1] seed - still no real SAR value.
      g_sarPrevPrevHigh = g_sarPrevHigh;
      g_sarPrevPrevLow = g_sarPrevLow;
      g_sarPrevHigh = high;
      g_sarPrevLow = low;
      g_sarPrevPsar = close;
      g_sarBarCount = 2;
      return false;
     }

   // Bar index >= 2.
   bool reversal = false;
   double psar;
   if(g_sarUpTrend)
     {
      psar = g_sarPrevPsar + g_sarAf * (g_sarUpTrendHigh - g_sarPrevPsar);
      if(low < psar)
        {
         reversal = true;
         psar = g_sarUpTrendHigh;
         g_sarDownTrendLow = low;
         g_sarAf = SAR_STEP;
        }
      else
        {
         if(high > g_sarUpTrendHigh)
           {
            g_sarUpTrendHigh = high;
            g_sarAf = MathMin(g_sarAf + SAR_STEP, SAR_MAX);
           }
         if(g_sarPrevPrevLow < psar) psar = g_sarPrevPrevLow;
         else if(g_sarPrevLow < psar) psar = g_sarPrevLow;
        }
     }
   else
     {
      psar = g_sarPrevPsar - g_sarAf * (g_sarPrevPsar - g_sarDownTrendLow);
      if(high > psar)
        {
         reversal = true;
         psar = g_sarDownTrendLow;
         g_sarUpTrendHigh = high;
         g_sarAf = SAR_STEP;
        }
      else
        {
         if(low < g_sarDownTrendLow)
           {
            g_sarDownTrendLow = low;
            g_sarAf = MathMin(g_sarAf + SAR_STEP, SAR_MAX);
           }
         if(g_sarPrevPrevHigh > psar) psar = g_sarPrevPrevHigh;
         else if(g_sarPrevHigh > psar) psar = g_sarPrevHigh;
        }
     }

   g_sarUpTrend = (g_sarUpTrend != reversal); // flip on reversal, matches Python's `up_trend != reversal`

   g_sarPrevPrevHigh = g_sarPrevHigh;
   g_sarPrevPrevLow = g_sarPrevLow;
   g_sarPrevHigh = high;
   g_sarPrevLow = low;
   g_sarPrevPsar = psar;

   outSar = psar;
   outDirection = (close > psar) ? 1 : -1; // strict >, ties go to SHORT - matches Python exactly
   return true;
}

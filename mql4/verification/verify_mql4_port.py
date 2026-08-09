"""
Verifies the MQL4 port's arithmetic without a compiler: this file is a
literal Python transliteration of mql4/Include/XAUUSD_Indicators.mqh and
XAUUSD_Signals.mqh's control flow (same variable names, same branches,
same order of operations) - written independently of the real
xauusd_indicators package's own code, not by importing/reusing it, so
this is a genuine check of the MQL4 translation, not a circular one.

Runs both this shadow implementation AND the real, already-tested
xauusd_indicators incremental functions over the same synthetic bar
sequence, asserting they agree bar-for-bar. Agreement here means: if
there's a transcription bug in the MQL4 port, this catches it before
anyone ever opens MetaEditor - it does NOT prove the .mqh/.mq4 files
compile or run correctly in real MQL4 (only real MetaEditor can prove
that), only that the arithmetic this Python transliteration encodes
(which was written by directly reading the .mqh files line-by-line)
matches the real, tested Python library.
"""
import os
import sys
_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))

from xauusd_indicators.indicators.atr import AtrState, atr_update, VolatilityRatioState, volatility_ratio_update
from xauusd_indicators.indicators.adx import AdxState, adx_update
from xauusd_indicators.indicators.rvi import RviState, rvi_update
from xauusd_indicators.indicators.roc import RocState, roc_update
from xauusd_indicators.indicators.obv import ObvState, obv_update
from xauusd_indicators.indicators.macd import MacdState, macd_histogram_update
from xauusd_indicators.indicators.parabolic_sar import ParabolicSarState, parabolic_sar_update
from xauusd_indicators.types import Bar, Signal

from demo import synthetic_ohlcv

# ============================================================
# Shadow implementation - transliterated from the .mqh files
# ============================================================

def wilder_smooth_update(warmup, warmup_count, period, has_smoothed, smoothed, raw):
    if not has_smoothed:
        warmup.append(raw)
        warmup_count = len(warmup)
        if warmup_count == period:
            smoothed = sum(warmup) / period
            has_smoothed = True
            return True, smoothed, warmup, has_smoothed
        return False, smoothed, warmup, has_smoothed
    smoothed = (smoothed * (period - 1) + raw) / period
    return True, smoothed, warmup, has_smoothed


class ShadowAtr:
    def __init__(self):
        self.has_prev_close = False
        self.prev_close = 0.0
        self.warmup = []
        self.has_smoothed = False
        self.smoothed = 0.0

    def update(self, high, low, close):
        if not self.has_prev_close:
            tr = high - low
        else:
            tr = max(high - low, abs(high - self.prev_close), abs(low - self.prev_close))
        self.prev_close = close
        self.has_prev_close = True
        ok, self.smoothed, self.warmup, self.has_smoothed = wilder_smooth_update(
            self.warmup, len(self.warmup), 14, self.has_smoothed, self.smoothed, tr
        )
        return ok, self.smoothed


class ShadowVolRatio:
    def __init__(self):
        self.history = []

    def update(self, atr_value, atr_ready):
        if not atr_ready:
            return False, None
        self.history.append(atr_value)
        if len(self.history) > 50:
            self.history = self.history[-50:]
        if len(self.history) < 50:
            return False, None
        avg = sum(self.history) / 50
        return True, atr_value / avg


class ShadowAdx:
    def __init__(self):
        self.has_prev_hl = False
        self.prev_high = 0.0
        self.prev_low = 0.0
        self.plus_warmup = []
        self.has_plus = False
        self.smoothed_plus = 0.0
        self.minus_warmup = []
        self.has_minus = False
        self.smoothed_minus = 0.0
        self.dx_warmup = []
        self.has_dx = False
        self.smoothed_dx = 0.0

    def update(self, high, low, atr_value, atr_ready):
        if not self.has_prev_hl:
            plus_dm = 0.0
            minus_dm = 0.0
        else:
            up_move = high - self.prev_high
            down_move = self.prev_low - low
            plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
            minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0
        self.prev_high = high
        self.prev_low = low
        self.has_prev_hl = True

        plus_ok, self.smoothed_plus, self.plus_warmup, self.has_plus = wilder_smooth_update(
            self.plus_warmup, len(self.plus_warmup), 14, self.has_plus, self.smoothed_plus, plus_dm
        )
        minus_ok, self.smoothed_minus, self.minus_warmup, self.has_minus = wilder_smooth_update(
            self.minus_warmup, len(self.minus_warmup), 14, self.has_minus, self.smoothed_minus, minus_dm
        )

        if not atr_ready or not plus_ok:
            return False, None

        plus_di = 100.0 * self.smoothed_plus / atr_value
        minus_di = 100.0 * self.smoothed_minus / atr_value
        denom = plus_di + minus_di
        dx = 0.0 if denom == 0.0 else 100.0 * abs(plus_di - minus_di) / denom

        dx_ok, self.smoothed_dx, self.dx_warmup, self.has_dx = wilder_smooth_update(
            self.dx_warmup, len(self.dx_warmup), 14, self.has_dx, self.smoothed_dx, dx
        )
        if not dx_ok:
            return False, None
        return True, self.smoothed_dx


class ShadowRvi:
    def __init__(self):
        self.co_history = []
        self.hl_history = []
        self.armed = ""

    def update(self, open_, high, low, close):
        co = close - open_
        hl = high - low
        if len(self.co_history) < 14:
            self.co_history.append(co)
            self.hl_history.append(hl)
        else:
            self.co_history = self.co_history[1:] + [co]
            self.hl_history = self.hl_history[1:] + [hl]

        trigger = 0
        if len(self.co_history) < 14:
            return False, None, trigger

        sum_co = sum(self.co_history)
        sum_hl = sum(self.hl_history)
        denom = sum_hl / 14
        numer = sum_co / 14
        rvi_value = numer / denom

        if rvi_value <= -0.20:
            self.armed = "below"
        elif rvi_value >= 0.20:
            self.armed = "above"
        else:
            if self.armed == "below":
                trigger = 1
                self.armed = ""
            elif self.armed == "above":
                trigger = -1
                self.armed = ""
        return True, rvi_value, trigger


class ShadowRoc:
    def __init__(self):
        self.history = []

    def update(self, close):
        if len(self.history) < 11:
            self.history.append(close)
        else:
            self.history = self.history[1:] + [close]
        if len(self.history) < 11:
            return False, None
        prev_close = self.history[0]
        return True, 100.0 * (close - prev_close) / prev_close


class ShadowObv:
    def __init__(self):
        self.has_prev_close = False
        self.prev_close = 0.0
        self.running = 0.0
        self.history = []

    def update(self, close, volume):
        if not self.has_prev_close:
            direction = 0.0
        elif close > self.prev_close:
            direction = 1.0
        elif close < self.prev_close:
            direction = -1.0
        else:
            direction = 0.0
        self.prev_close = close
        self.has_prev_close = True
        self.running = self.running + direction * volume

        if len(self.history) < 11:
            self.history.append(self.running)
        else:
            self.history = self.history[1:] + [self.running]

        slope_ok = len(self.history) == 11
        slope = (self.running - self.history[0]) if slope_ok else None
        return self.running, slope_ok, slope


class ShadowMacd:
    def __init__(self):
        self.has_fast = False
        self.ema_fast = 0.0
        self.has_slow = False
        self.ema_slow = 0.0
        self.has_signal = False
        self.ema_signal = 0.0
        self.count = 0

    def update(self, close):
        alpha_fast = 2.0 / 13
        alpha_slow = 2.0 / 27
        alpha_signal = 2.0 / 10

        self.ema_fast = (alpha_fast * close + (1 - alpha_fast) * self.ema_fast) if self.has_fast else close
        self.has_fast = True
        self.ema_slow = (alpha_slow * close + (1 - alpha_slow) * self.ema_slow) if self.has_slow else close
        self.has_slow = True

        macd_value = self.ema_fast - self.ema_slow

        self.ema_signal = (alpha_signal * macd_value + (1 - alpha_signal) * self.ema_signal) if self.has_signal else macd_value
        self.has_signal = True

        self.count += 1
        histogram = macd_value - self.ema_signal
        if self.count < 34:
            return False, None
        return True, histogram


class ShadowSar:
    def __init__(self):
        self.bar_count = 0
        self.pp_high = 0.0
        self.pp_low = 0.0
        self.p_high = 0.0
        self.p_low = 0.0
        self.up_trend = True
        self.af = 0.02
        self.up_trend_high = 0.0
        self.down_trend_low = 0.0
        self.prev_psar = 0.0

    def update(self, high, low, close):
        if self.bar_count == 0:
            self.up_trend = True
            self.af = 0.02
            self.up_trend_high = high
            self.down_trend_low = low
            self.p_high = high
            self.p_low = low
            self.bar_count = 1
            return False, None, 0

        if self.bar_count == 1:
            self.pp_high = self.p_high
            self.pp_low = self.p_low
            self.p_high = high
            self.p_low = low
            self.prev_psar = close
            self.bar_count = 2
            return False, None, 0

        reversal = False
        if self.up_trend:
            psar = self.prev_psar + self.af * (self.up_trend_high - self.prev_psar)
            if low < psar:
                reversal = True
                psar = self.up_trend_high
                self.down_trend_low = low
                self.af = 0.02
            else:
                if high > self.up_trend_high:
                    self.up_trend_high = high
                    self.af = min(self.af + 0.02, 0.20)
                if self.pp_low < psar:
                    psar = self.pp_low
                elif self.p_low < psar:
                    psar = self.p_low
        else:
            psar = self.prev_psar - self.af * (self.prev_psar - self.down_trend_low)
            if high > psar:
                reversal = True
                psar = self.down_trend_low
                self.up_trend_high = high
                self.af = 0.02
            else:
                if low < self.down_trend_low:
                    self.down_trend_low = low
                    self.af = min(self.af + 0.02, 0.20)
                if self.pp_high > psar:
                    psar = self.pp_high
                elif self.p_high > psar:
                    psar = self.p_high

        self.up_trend = (self.up_trend != reversal)
        self.pp_high, self.pp_low = self.p_high, self.p_low
        self.p_high, self.p_low = high, low
        self.prev_psar = psar

        direction = 1 if close > psar else -1
        return True, psar, direction


# ============================================================
# Run both implementations over the same 400-bar synthetic series
# ============================================================

df = synthetic_ohlcv(n=400, seed=7)

real_atr, real_adx = AtrState(), AdxState()
real_vol = VolatilityRatioState()
real_rvi, real_roc, real_obv, real_macd, real_sar = RviState(), RocState(), ObvState(), MacdState(), ParabolicSarState()

shadow_atr, shadow_adx = ShadowAtr(), ShadowAdx()
shadow_vol = ShadowVolRatio()
shadow_rvi, shadow_roc, shadow_obv, shadow_macd, shadow_sar = ShadowRvi(), ShadowRoc(), ShadowObv(), ShadowMacd(), ShadowSar()

TOL = 1e-9
mismatches = []
checked = {"atr": 0, "vol": 0, "adx": 0, "rvi": 0, "roc": 0, "obv_slope": 0, "macd": 0, "sar": 0}

for i in range(len(df)):
    row = df.iloc[i]
    bar = Bar(open=row["open"], high=row["high"], low=row["low"], close=row["close"], volume=row["volume"])

    real_atr_val, real_atr = atr_update(real_atr, bar)
    shadow_atr_ok, shadow_atr_val = shadow_atr.update(bar.high, bar.low, bar.close)
    if (real_atr_val is None) != (not shadow_atr_ok):
        mismatches.append(f"bar {i}: ATR availability mismatch (real={real_atr_val}, shadow_ok={shadow_atr_ok})")
    elif real_atr_val is not None:
        checked["atr"] += 1
        if abs(real_atr_val - shadow_atr_val) > TOL:
            mismatches.append(f"bar {i}: ATR value mismatch real={real_atr_val} shadow={shadow_atr_val}")

    real_vol_val, real_vol = volatility_ratio_update(real_vol, bar)
    shadow_vol_ok, shadow_vol_val = shadow_vol.update(shadow_atr_val if shadow_atr_ok else None, shadow_atr_ok)
    if (real_vol_val is None) != (not shadow_vol_ok):
        mismatches.append(f"bar {i}: VolRatio availability mismatch")
    elif real_vol_val is not None:
        checked["vol"] += 1
        if abs(real_vol_val - shadow_vol_val) > TOL:
            mismatches.append(f"bar {i}: VolRatio mismatch real={real_vol_val} shadow={shadow_vol_val}")

    real_adx_val, real_adx = adx_update(real_adx, bar)
    shadow_adx_ok, shadow_adx_val = shadow_adx.update(bar.high, bar.low, shadow_atr_val if shadow_atr_ok else None, shadow_atr_ok)
    if (real_adx_val is None) != (not shadow_adx_ok):
        mismatches.append(f"bar {i}: ADX availability mismatch (real={real_adx_val}, shadow_ok={shadow_adx_ok})")
    elif real_adx_val is not None:
        checked["adx"] += 1
        if abs(real_adx_val - shadow_adx_val) > TOL:
            mismatches.append(f"bar {i}: ADX mismatch real={real_adx_val} shadow={shadow_adx_val}")

    (real_rvi_val, real_trigger), real_rvi = rvi_update(real_rvi, bar)
    shadow_rvi_ok, shadow_rvi_val, shadow_trigger = shadow_rvi.update(bar.open, bar.high, bar.low, bar.close)
    real_trigger_int = {Signal.LONG: 1, Signal.SHORT: -1, None: 0}[real_trigger]
    if (real_rvi_val is None) != (not shadow_rvi_ok):
        mismatches.append(f"bar {i}: RVI availability mismatch")
    elif real_rvi_val is not None:
        checked["rvi"] += 1
        if abs(real_rvi_val - shadow_rvi_val) > TOL:
            mismatches.append(f"bar {i}: RVI value mismatch real={real_rvi_val} shadow={shadow_rvi_val}")
        if real_trigger_int != shadow_trigger:
            mismatches.append(f"bar {i}: RVI trigger mismatch real={real_trigger_int} shadow={shadow_trigger}")

    real_roc_val, real_roc = roc_update(real_roc, bar)
    shadow_roc_ok, shadow_roc_val = shadow_roc.update(bar.close)
    if (real_roc_val is None) != (not shadow_roc_ok):
        mismatches.append(f"bar {i}: ROC availability mismatch")
    elif real_roc_val is not None:
        checked["roc"] += 1
        if abs(real_roc_val - shadow_roc_val) > TOL:
            mismatches.append(f"bar {i}: ROC mismatch real={real_roc_val} shadow={shadow_roc_val}")

    (real_obv_val, real_slope), real_obv = obv_update(real_obv, bar)
    shadow_obv_val, shadow_slope_ok, shadow_slope = shadow_obv.update(bar.close, bar.volume)
    if abs(real_obv_val - shadow_obv_val) > TOL:
        mismatches.append(f"bar {i}: OBV mismatch real={real_obv_val} shadow={shadow_obv_val}")
    if (real_slope is None) != (not shadow_slope_ok):
        mismatches.append(f"bar {i}: OBV slope availability mismatch")
    elif real_slope is not None:
        checked["obv_slope"] += 1
        if abs(real_slope - shadow_slope) > TOL:
            mismatches.append(f"bar {i}: OBV slope mismatch real={real_slope} shadow={shadow_slope}")

    real_macd_val, real_macd = macd_histogram_update(real_macd, bar)
    shadow_macd_ok, shadow_macd_val = shadow_macd.update(bar.close)
    if (real_macd_val is None) != (not shadow_macd_ok):
        mismatches.append(f"bar {i}: MACD availability mismatch")
    elif real_macd_val is not None:
        checked["macd"] += 1
        if abs(real_macd_val - shadow_macd_val) > TOL:
            mismatches.append(f"bar {i}: MACD mismatch real={real_macd_val} shadow={shadow_macd_val}")

    real_sar_val, real_sar = parabolic_sar_update(real_sar, bar)
    shadow_sar_ok, shadow_sar_val, shadow_sar_dir = shadow_sar.update(bar.high, bar.low, bar.close)
    if (real_sar_val is None) != (not shadow_sar_ok):
        mismatches.append(f"bar {i}: SAR availability mismatch")
    elif real_sar_val is not None:
        checked["sar"] += 1
        if abs(real_sar_val - shadow_sar_val) > TOL:
            mismatches.append(f"bar {i}: SAR mismatch real={real_sar_val} shadow={shadow_sar_val}")

print("Bars checked per indicator (non-warmup bars only):", checked)
print()
if mismatches:
    print(f"FAILED: {len(mismatches)} mismatch(es) found:")
    for m in mismatches[:30]:
        print(" -", m)
    sys.exit(1)
else:
    print(f"PASSED: all {len(df)} bars agree between the real xauusd_indicators package")
    print("and the MQL4-port shadow transliteration, across every indicator, to 1e-9.")

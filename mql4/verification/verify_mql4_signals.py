"""
Same idea as verify_mql4_port.py, one level up: transliterates
mql4/Include/XAUUSD_Signals.mqh's entry-composition functions
(Section2Entry/Section6Entry/Section6aEntry) into Python independently,
then compares against the REAL xauusd_indicators.signals module's
entry_signal() functions (already tested, 75/75 passing) run on the
same synthetic data - reusing the shadow indicator classes from
verify_mql4_port.py to drive both sides bar-by-bar.
"""
import os
import sys
_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from xauusd_indicators.signals import section2, section6, section6a
from xauusd_indicators.types import Signal

from demo import synthetic_ohlcv

from verify_mql4_port import ShadowAtr, ShadowVolRatio, ShadowAdx, ShadowRvi, ShadowRoc, ShadowObv, ShadowMacd, ShadowSar

# ============================================================
# Shadow entry-composition (transliterated from XAUUSD_Signals.mqh)
# ============================================================

def section2_entry(rvi_trigger, adx_ready, adx_value, vol_ready, vol_ratio):
    if rvi_trigger == 0:
        return 0
    if not adx_ready or not vol_ready:
        return 0
    if adx_value > 30.0 and vol_ratio > 1.1:
        return rvi_trigger
    return 0


def section6_entry(section2_signal, roc_ready, roc_value, obv_ready, obv_slope, macd_ready, macd_hist):
    if section2_signal == 0:
        return 0
    if not roc_ready or not obv_ready or not macd_ready:
        return 0
    if section2_signal == 1:
        return 1 if (roc_value > 0 and obv_slope > 0 and macd_hist > 0) else 0
    else:
        return -1 if (roc_value < 0 and obv_slope < 0 and macd_hist < 0) else 0


def section6a_entry(section2_signal, sar_ready, sar_direction):
    if section2_signal == 0 or not sar_ready:
        return 0
    return section2_signal if sar_direction == section2_signal else 0


# ============================================================
# Ground truth: the real, vectorized entry_signal() functions
# ============================================================

df = synthetic_ohlcv(n=400, seed=7)
real_s2 = section2.entry_signal(df)
real_s6 = section6.entry_signal(df)
real_s6a = section6a.entry_signal(df)

def to_int(sig):
    return {Signal.LONG: 1, Signal.SHORT: -1, None: 0}.get(sig, 0)

# ============================================================
# Drive the shadow indicators + shadow signal composition bar-by-bar
# ============================================================

shadow_atr, shadow_adx = ShadowAtr(), ShadowAdx()
shadow_vol = ShadowVolRatio()
shadow_rvi, shadow_roc, shadow_obv, shadow_macd, shadow_sar = ShadowRvi(), ShadowRoc(), ShadowObv(), ShadowMacd(), ShadowSar()

mismatches = []
counts = {"s2": 0, "s6": 0, "s6a": 0}

for i in range(len(df)):
    row = df.iloc[i]
    o, h, l, c, v = row["open"], row["high"], row["low"], row["close"], row["volume"]

    atr_ok, atr_val = shadow_atr.update(h, l, c)
    vol_ok, vol_val = shadow_vol.update(atr_val if atr_ok else None, atr_ok)
    adx_ok, adx_val = shadow_adx.update(h, l, atr_val if atr_ok else None, atr_ok)
    rvi_ok, rvi_val, rvi_trigger = shadow_rvi.update(o, h, l, c)
    roc_ok, roc_val = shadow_roc.update(c)
    obv_val, obv_slope_ok, obv_slope = shadow_obv.update(c, v)
    macd_ok, macd_val = shadow_macd.update(c)
    sar_ok, sar_val, sar_dir = shadow_sar.update(h, l, c)

    s2 = section2_entry(rvi_trigger if rvi_ok else 0, adx_ok, adx_val, vol_ok, vol_val)
    s6 = section6_entry(s2, roc_ok, roc_val, obv_slope_ok, obv_slope, macd_ok, macd_val)
    s6a = section6a_entry(s2, sar_ok, sar_dir)

    real_s2_i = to_int(real_s2.iloc[i])
    real_s6_i = to_int(real_s6.iloc[i])
    real_s6a_i = to_int(real_s6a.iloc[i])

    if real_s2_i != 0 or s2 != 0:
        counts["s2"] += 1
    if real_s2_i != s2:
        mismatches.append(f"bar {i}: Section2 mismatch real={real_s2_i} shadow={s2}")
    if real_s6_i != s6:
        mismatches.append(f"bar {i}: Section6 mismatch real={real_s6_i} shadow={s6}")
    if real_s6a_i != s6a:
        mismatches.append(f"bar {i}: Section6a mismatch real={real_s6a_i} shadow={s6a}")

print(f"Section 2 signals (real): {sum(1 for x in real_s2 if x is not None)} total non-None over {len(df)} bars")
print(f"Section 6 signals (real): {sum(1 for x in real_s6 if x is not None)} total non-None over {len(df)} bars")
print(f"Section 6a signals (real): {sum(1 for x in real_s6a if x is not None)} total non-None over {len(df)} bars")
print()

if mismatches:
    print(f"FAILED: {len(mismatches)} mismatch(es):")
    for m in mismatches[:30]:
        print(" -", m)
    sys.exit(1)
else:
    print("PASSED: Section 2/6/6a entry-signal composition matches exactly, bar-for-bar,")
    print("between the real xauusd_indicators.signals package and the MQL4-port shadow.")

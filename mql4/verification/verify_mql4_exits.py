"""
Transliterates Section2Exit/Section7Exit from XAUUSD_Signals.mqh into
Python independently, then runs the exact same engineered scenarios
tests/test_signals_section2.py and tests/test_signals_section7.py use
against the REAL exit_fired() functions, asserting matching results.
"""

HARD_STOP_ATR_MULTIPLE = 2.0
TRAIL_ATR_MULTIPLE = 1.5
PROFIT_TARGET_USD = 15.0
TIME_CUTOFF_BARS = 30
NOTIONAL_OZ_PER_POSITION = 1.0


def section2_exit(direction, entry_price, atr_at_entry, extreme_since_entry,
                   current_high, current_low, bars_since_entry, rvi_trigger):
    is_long = direction == 1

    if is_long:
        hard_stop_level = entry_price - HARD_STOP_ATR_MULTIPLE * atr_at_entry
        if current_low <= hard_stop_level:
            return True
    else:
        hard_stop_level = entry_price + HARD_STOP_ATR_MULTIPLE * atr_at_entry
        if current_high >= hard_stop_level:
            return True

    if is_long:
        trailing_level = extreme_since_entry - TRAIL_ATR_MULTIPLE * atr_at_entry
        if current_low <= trailing_level:
            return True
    else:
        trailing_level = extreme_since_entry + TRAIL_ATR_MULTIPLE * atr_at_entry
        if current_high >= trailing_level:
            return True

    opposite = -1 if is_long else 1
    if bars_since_entry > 0 and rvi_trigger == opposite:
        return True

    return False


def section7_exit(direction, entry_price, atr_at_entry, current_high, current_low, bars_since_entry, rvi_trigger):
    is_long = direction == 1

    if is_long:
        hard_stop_level = entry_price - HARD_STOP_ATR_MULTIPLE * atr_at_entry
        if current_low <= hard_stop_level:
            return True
    else:
        hard_stop_level = entry_price + HARD_STOP_ATR_MULTIPLE * atr_at_entry
        if current_high >= hard_stop_level:
            return True

    opposite = -1 if is_long else 1
    if bars_since_entry > 0 and rvi_trigger == opposite:
        return True

    price_target_distance = PROFIT_TARGET_USD / NOTIONAL_OZ_PER_POSITION
    if is_long:
        target_price = entry_price + price_target_distance
        if current_high >= target_price:
            return True
    else:
        target_price = entry_price - price_target_distance
        if current_low <= target_price:
            return True

    if bars_since_entry >= TIME_CUTOFF_BARS:
        return True

    return False


import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import pandas as pd
from xauusd_indicators.types import PositionState, Signal
from xauusd_indicators.signals import section2, section7

results = []

def check(name, shadow_result, real_result):
    ok = shadow_result == real_result
    results.append((name, ok, shadow_result, real_result))


# --- Section 2: hard stop, LONG ---
df = pd.DataFrame([{"open": 2000, "high": 2000.5, "low": 1999.5, "close": 2000, "volume": 100} for _ in range(10)])
df.loc[5, "low"] = 2000.0 - HARD_STOP_ATR_MULTIPLE * 1.0 - 5.0
pos = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
no_trigger = pd.Series([None] * len(df))
real = section2.exit_fired(df, pos, current_bar_index=5, atr_at_entry=1.0, rvi_triggers=no_trigger)
extreme = df["high"].iloc[0:6].max()  # highest high since entry through bar 5
shadow = section2_exit(1, 2000.0, 1.0, extreme, df["high"].iloc[5], df["low"].iloc[5], 5, 0)
check("Section2 hard stop LONG", shadow, real)

# --- Section 2: nothing breaches ---
df2 = pd.DataFrame([{"open": 2000, "high": 2000.1, "low": 1999.9, "close": 2000, "volume": 100} for _ in range(10)])
pos2 = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
real2 = section2.exit_fired(df2, pos2, current_bar_index=3, atr_at_entry=1.0, rvi_triggers=no_trigger)
extreme2 = df2["high"].iloc[0:4].max()
shadow2 = section2_exit(1, 2000.0, 1.0, extreme2, df2["high"].iloc[3], df2["low"].iloc[3], 3, 0)
check("Section2 nothing breaches", shadow2, real2)

# --- Section 2: trailing stop after rally then pullback ---
df3 = pd.DataFrame([{"open": 2000, "high": 2000.1, "low": 1999.9, "close": 2000, "volume": 100} for _ in range(10)])
df3.loc[3, "high"] = 2010.0
df3.loc[4, "low"] = 2010.0 - TRAIL_ATR_MULTIPLE * 1.0 - 1.0
pos3 = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
real3 = section2.exit_fired(df3, pos3, current_bar_index=4, atr_at_entry=1.0, rvi_triggers=no_trigger)
extreme3 = df3["high"].iloc[0:5].max()  # includes the 2010.0 rally high
shadow3 = section2_exit(1, 2000.0, 1.0, extreme3, df3["high"].iloc[4], df3["low"].iloc[4], 4, 0)
check("Section2 trailing stop after rally", shadow3, real3)

# --- Section 2: RVI reversal ---
df4 = pd.DataFrame([{"open": 2000, "high": 2000.1, "low": 1999.9, "close": 2000, "volume": 100} for _ in range(10)])
pos4 = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
triggers4 = pd.Series([None] * len(df4))
triggers4.iloc[4] = Signal.SHORT
real4 = section2.exit_fired(df4, pos4, current_bar_index=4, atr_at_entry=1.0, rvi_triggers=triggers4)
extreme4 = df4["high"].iloc[0:5].max()
shadow4 = section2_exit(1, 2000.0, 1.0, extreme4, df4["high"].iloc[4], df4["low"].iloc[4], 4, -1)  # -1 = SHORT trigger this bar
check("Section2 RVI reversal", shadow4, real4)

# --- Section 7: profit target LONG ---
df5 = pd.DataFrame([{"open": 2000, "high": 2000.1, "low": 1999.9, "close": 2000, "volume": 100} for _ in range(10)])
target_distance = PROFIT_TARGET_USD / NOTIONAL_OZ_PER_POSITION
df5.loc[6, "high"] = 2000.0 + target_distance + 1.0
pos5 = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
real5 = section7.exit_fired(df5, pos5, current_bar_index=6, atr_at_entry=1.0, rvi_triggers=pd.Series([None] * len(df5)))
shadow5 = section7_exit(1, 2000.0, 1.0, df5["high"].iloc[6], df5["low"].iloc[6], 6, 0)
check("Section7 profit target LONG", shadow5, real5)

# --- Section 7: 30-bar time cutoff ---
df6 = pd.DataFrame([{"open": 2000, "high": 2000.1, "low": 1999.9, "close": 2000, "volume": 100} for _ in range(TIME_CUTOFF_BARS + 5)])
pos6 = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
no_trigger6 = pd.Series([None] * len(df6))
real_before = section7.exit_fired(df6, pos6, current_bar_index=TIME_CUTOFF_BARS - 1, atr_at_entry=1.0, rvi_triggers=no_trigger6)
shadow_before = section7_exit(1, 2000.0, 1.0, df6["high"].iloc[TIME_CUTOFF_BARS - 1], df6["low"].iloc[TIME_CUTOFF_BARS - 1], TIME_CUTOFF_BARS - 1, 0)
check("Section7 cutoff-1 (should be False)", shadow_before, real_before)
real_at = section7.exit_fired(df6, pos6, current_bar_index=TIME_CUTOFF_BARS, atr_at_entry=1.0, rvi_triggers=no_trigger6)
shadow_at = section7_exit(1, 2000.0, 1.0, df6["high"].iloc[TIME_CUTOFF_BARS], df6["low"].iloc[TIME_CUTOFF_BARS], TIME_CUTOFF_BARS, 0)
check("Section7 cutoff (should be True)", shadow_at, real_at)

print(f"{'PASS' if all(ok for _, ok, _, _ in results) else 'FAIL'} - {sum(ok for _, ok, _, _ in results)}/{len(results)} exit scenarios matched\n")
for name, ok, s, r in results:
    print(f"  [{'OK' if ok else 'MISMATCH'}] {name}: shadow={s} real={r}")

if not all(ok for _, ok, _, _ in results):
    sys.exit(1)

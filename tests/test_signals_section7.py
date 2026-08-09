"""Section 7 exit composition: $15 profit target, 30-bar cutoff, plus
hard-stop/RVI-reversal still active per the documented §6.5
interpretation (see section7.py's module docstring) - trailing stop is
the only Section 2 exit component NOT carried over."""
import pandas as pd

from xauusd_indicators.signals.section7 import (
    NOTIONAL_OZ_PER_POSITION,
    PROFIT_TARGET_USD,
    TIME_CUTOFF_BARS,
    exit_fired,
)
from xauusd_indicators.types import PositionState, Signal


def _flat_df(n, price=2000.0, spread=0.1):
    rows = []
    for _ in range(n):
        rows.append({"open": price, "high": price + spread, "low": price - spread, "close": price, "volume": 100})
    return pd.DataFrame(rows)


def test_exit_fires_on_profit_target_long():
    df = _flat_df(5, price=2000.0, spread=0.1)
    target_distance = PROFIT_TARGET_USD / NOTIONAL_OZ_PER_POSITION
    df.loc[3, "high"] = 2000.0 + target_distance + 0.01
    position = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
    no_trigger = pd.Series([None] * len(df))
    assert exit_fired(df, position, current_bar_index=3, atr_at_entry=1.0, rvi_triggers=no_trigger) is True


def test_exit_fires_on_profit_target_short():
    df = _flat_df(5, price=2000.0, spread=0.1)
    target_distance = PROFIT_TARGET_USD / NOTIONAL_OZ_PER_POSITION
    df.loc[3, "low"] = 2000.0 - target_distance - 0.01
    position = PositionState(direction=Signal.SHORT, entry_price=2000.0, entry_bar_index=0)
    no_trigger = pd.Series([None] * len(df))
    assert exit_fired(df, position, current_bar_index=3, atr_at_entry=1.0, rvi_triggers=no_trigger) is True


def test_exit_does_not_fire_before_profit_target_reached():
    df = _flat_df(5, price=2000.0, spread=0.1)
    position = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
    no_trigger = pd.Series([None] * len(df))
    assert exit_fired(df, position, current_bar_index=3, atr_at_entry=1.0, rvi_triggers=no_trigger) is False


def test_exit_fires_on_30_bar_time_cutoff():
    df = _flat_df(TIME_CUTOFF_BARS + 5, price=2000.0, spread=0.1)
    position = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
    no_trigger = pd.Series([None] * len(df))
    assert exit_fired(df, position, current_bar_index=TIME_CUTOFF_BARS - 1, atr_at_entry=1.0, rvi_triggers=no_trigger) is False
    assert exit_fired(df, position, current_bar_index=TIME_CUTOFF_BARS, atr_at_entry=1.0, rvi_triggers=no_trigger) is True


def test_exit_fires_on_hard_stop_still_active_in_section7():
    from xauusd_indicators.signals.section2 import HARD_STOP_ATR_MULTIPLE

    df = _flat_df(5, price=2000.0, spread=0.1)
    df.loc[2, "low"] = 2000.0 - HARD_STOP_ATR_MULTIPLE * 1.0 - 5.0
    position = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
    no_trigger = pd.Series([None] * len(df))
    assert exit_fired(df, position, current_bar_index=2, atr_at_entry=1.0, rvi_triggers=no_trigger) is True


def test_exit_fires_on_rvi_reversal_still_active_in_section7():
    df = _flat_df(5, price=2000.0, spread=0.1)
    position = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
    triggers = pd.Series([None] * len(df))
    triggers.iloc[2] = Signal.SHORT
    assert exit_fired(df, position, current_bar_index=2, atr_at_entry=1.0, rvi_triggers=triggers) is True


def test_section7_entry_signal_is_the_same_function_as_section2():
    from xauusd_indicators.signals.section2 import entry_signal as section2_entry
    from xauusd_indicators.signals.section7 import entry_signal as section7_entry

    assert section7_entry is section2_entry

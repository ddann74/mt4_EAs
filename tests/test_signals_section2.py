"""Section 2 entry/exit composition: branch coverage via injected
indicator series (see section2.entry_signal's docstring for why), plus
one true end-to-end test proving the real wiring (actual indicator
functions -> composition) works on a real DataFrame."""
import pandas as pd

from tests.fixtures import synthetic_series_df
from xauusd_indicators.indicators.atr import atr
from xauusd_indicators.signals.section2 import (
    HARD_STOP_ATR_MULTIPLE,
    TRAIL_ATR_MULTIPLE,
    entry_signal,
    exit_fired,
)
from xauusd_indicators.types import PositionState, Signal


def _placeholder_df(n=6):
    return synthetic_series_df(n=n)


def test_entry_fires_long_when_all_three_conditions_agree():
    df = _placeholder_df()
    triggers = pd.Series([None, Signal.LONG, None, None, None, None], index=df.index)
    adx_series = pd.Series([35] * len(df), index=df.index)
    vol_ratio = pd.Series([1.5] * len(df), index=df.index)
    result = entry_signal(df, rvi_triggers=triggers, adx_series=adx_series, vol_ratio_series=vol_ratio)
    assert result.iloc[1] == Signal.LONG
    assert all(v is None for i, v in enumerate(result) if i != 1)


def test_entry_fires_short_when_all_three_conditions_agree():
    df = _placeholder_df()
    triggers = pd.Series([None, None, Signal.SHORT, None, None, None], index=df.index)
    adx_series = pd.Series([40] * len(df), index=df.index)
    vol_ratio = pd.Series([1.2] * len(df), index=df.index)
    result = entry_signal(df, rvi_triggers=triggers, adx_series=adx_series, vol_ratio_series=vol_ratio)
    assert result.iloc[2] == Signal.SHORT


def test_entry_blocked_when_adx_below_threshold():
    df = _placeholder_df()
    triggers = pd.Series([None, Signal.LONG, None, None, None, None], index=df.index)
    adx_series = pd.Series([29.9] * len(df), index=df.index)  # just below 30
    vol_ratio = pd.Series([1.5] * len(df), index=df.index)
    result = entry_signal(df, rvi_triggers=triggers, adx_series=adx_series, vol_ratio_series=vol_ratio)
    assert result.iloc[1] is None


def test_entry_blocked_when_volatility_ratio_below_threshold():
    df = _placeholder_df()
    triggers = pd.Series([None, Signal.LONG, None, None, None, None], index=df.index)
    adx_series = pd.Series([35] * len(df), index=df.index)
    vol_ratio = pd.Series([1.0999] * len(df), index=df.index)  # just below 1.1
    result = entry_signal(df, rvi_triggers=triggers, adx_series=adx_series, vol_ratio_series=vol_ratio)
    assert result.iloc[1] is None


def test_entry_blocked_when_confirm_filters_are_nan():
    df = _placeholder_df()
    triggers = pd.Series([None, Signal.LONG, None, None, None, None], index=df.index)
    adx_series = pd.Series([float("nan")] * len(df), index=df.index)
    vol_ratio = pd.Series([1.5] * len(df), index=df.index)
    result = entry_signal(df, rvi_triggers=triggers, adx_series=adx_series, vol_ratio_series=vol_ratio)
    assert result.iloc[1] is None


def test_no_entries_when_rvi_never_triggers():
    df = _placeholder_df()
    triggers = pd.Series([None] * len(df), index=df.index)
    adx_series = pd.Series([50] * len(df), index=df.index)
    vol_ratio = pd.Series([2.0] * len(df), index=df.index)
    result = entry_signal(df, rvi_triggers=triggers, adx_series=adx_series, vol_ratio_series=vol_ratio)
    assert all(v is None for v in result)


def test_entry_signal_end_to_end_on_real_dataframe_does_not_crash_and_returns_expected_shape():
    df = synthetic_series_df(n=250)
    result = entry_signal(df)
    assert len(result) == len(df)
    assert set(v for v in result if v is not None) <= {Signal.LONG, Signal.SHORT}


# --- exit_fired ---


def _flat_df(n, price=2000.0, spread=0.5):
    rows = []
    for _ in range(n):
        rows.append({"open": price, "high": price + spread, "low": price - spread, "close": price, "volume": 100})
    return pd.DataFrame(rows)


def test_exit_fires_on_hard_stop_long():
    df = _flat_df(10, price=2000.0, spread=0.5)
    # Force a hard-stop breach on bar 5: low dips well below entry - 2*atr.
    df.loc[5, "low"] = 2000.0 - HARD_STOP_ATR_MULTIPLE * 1.0 - 5.0
    position = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
    no_trigger = pd.Series([None] * len(df))
    assert exit_fired(df, position, current_bar_index=5, atr_at_entry=1.0, rvi_triggers=no_trigger) is True


def test_exit_does_not_fire_when_nothing_breaches():
    df = _flat_df(10, price=2000.0, spread=0.1)
    position = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
    no_trigger = pd.Series([None] * len(df))
    assert exit_fired(df, position, current_bar_index=3, atr_at_entry=1.0, rvi_triggers=no_trigger) is False


def test_exit_fires_on_trailing_stop_long_after_a_rally_then_pullback():
    df = _flat_df(10, price=2000.0, spread=0.1)
    # Rally to a new high at bar 3, then pull back hard at bar 4.
    df.loc[3, "high"] = 2010.0
    df.loc[4, "low"] = 2010.0 - TRAIL_ATR_MULTIPLE * 1.0 - 1.0
    position = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
    no_trigger = pd.Series([None] * len(df))
    assert exit_fired(df, position, current_bar_index=4, atr_at_entry=1.0, rvi_triggers=no_trigger) is True


def test_exit_fires_on_rvi_reversal():
    df = _flat_df(10, price=2000.0, spread=0.1)
    position = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=0)
    triggers = pd.Series([None] * len(df))
    triggers.iloc[4] = Signal.SHORT  # opposite of the open LONG position
    assert exit_fired(df, position, current_bar_index=4, atr_at_entry=1.0, rvi_triggers=triggers) is True


def test_exit_rejects_current_bar_before_entry():
    df = _flat_df(5)
    position = PositionState(direction=Signal.LONG, entry_price=2000.0, entry_bar_index=3)
    no_trigger = pd.Series([None] * len(df))
    try:
        exit_fired(df, position, current_bar_index=1, atr_at_entry=1.0, rvi_triggers=no_trigger)
        assert False, "expected ValueError"
    except ValueError:
        pass

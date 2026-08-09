"""Custom RVI(14) correctness (per the UNCONFIRMED formula documented in
indicators/rvi.py and docs/PRD.md §6.1) and the setup-then-cross trigger
state machine (§6.2's reach-then-cross-back reading).
"""
import math

import pandas as pd

from tests.fixtures import df_to_bars, synthetic_series_df, tiny_downtrend_df, tiny_uptrend_df
from xauusd_indicators.indicators.rvi import RviState, rvi, rvi_trigger, rvi_update
from xauusd_indicators.types import Signal


def test_rvi_hand_computed_on_tiny_fixture():
    df = tiny_uptrend_df()
    # By construction (see fixtures.tiny_uptrend_df): close-open = 0.5
    # on every bar, high-low = 1.0 on every bar. So SMA(close-open,14)
    # = 0.5 and SMA(high-low,14) = 1.0 for every window -> RVI = 0.5
    # constant, once the 14-bar warmup is satisfied.
    result = rvi(df, period=14)
    assert result.iloc[:13].isna().all()
    for i in range(13, len(df)):
        assert math.isclose(result.iloc[i], 0.5, rel_tol=1e-9), f"bar {i}"


def test_rvi_hand_computed_on_tiny_downtrend_fixture():
    df = tiny_downtrend_df()
    # close-open = -0.5 on every bar, high-low = 1.0 on every bar (see
    # fixtures.tiny_downtrend_df) -> RVI = -0.5 constant. Closes the gap
    # where only the positive-RVI branch had an independent hand check.
    result = rvi(df, period=14)
    for i in range(13, len(df)):
        assert math.isclose(result.iloc[i], -0.5, rel_tol=1e-9), f"bar {i}"


def test_rvi_trigger_fires_long_from_real_bars_not_just_a_synthetic_rvi_series():
    """The trigger-firing tests elsewhere in this file feed a
    hand-constructed RVI Series directly into rvi_trigger(), which
    tests the state machine in isolation but never proves real OHLCV
    bars, run through rvi() first, actually produce a dip-then-recovery
    RVI path in practice. This builds one: a decline (driving RVI
    negative and past -0.20) followed by a sharp bar-over-bar recovery
    in the close-open spread (pulling RVI back through -0.20), using
    actual bars fed through rvi() -> rvi_trigger(), end to end."""
    n = 20
    rows = []
    price = 100.0
    for i in range(n):
        if i < 15:
            # Steady decline: every bar closes below its open.
            o = price
            c = o - 0.6
            h = o + 0.1
            low = c - 0.1
        else:
            # Sharp recovery: every bar closes well above its open.
            o = price
            c = o + 1.5
            h = c + 0.1
            low = o - 0.1
        rows.append({"open": o, "high": h, "low": low, "close": c, "volume": 100})
        price = c
    df = pd.DataFrame(rows)

    series = rvi(df, period=14)
    triggers = rvi_trigger(series)

    assert series.iloc[13] <= -0.20, "expected the decline to have pushed RVI past -0.20 by bar 13"
    fired = [i for i, t in enumerate(triggers) if t == Signal.LONG]
    assert fired, "expected the recovery to eventually cross RVI back through -0.20 and fire LONG"


def test_rvi_trigger_fires_long_on_dip_then_cross_back():
    # Reach below -0.20 (setup), then cross back up through -0.20 -> LONG.
    series = pd.Series([0.0, -0.25, -0.30, -0.10, 0.05])
    triggers = rvi_trigger(series)
    assert triggers.iloc[0] is None
    assert triggers.iloc[1] is None  # entering setup zone, not yet crossed back
    assert triggers.iloc[2] is None  # still below -0.20
    assert triggers.iloc[3] == Signal.LONG  # crosses back through -0.20
    assert triggers.iloc[4] is None  # already fired, armed reset


def test_rvi_trigger_fires_short_on_spike_then_cross_back():
    series = pd.Series([0.0, 0.25, 0.30, 0.10, -0.05])
    triggers = rvi_trigger(series)
    assert triggers.iloc[3] == Signal.SHORT
    assert triggers.iloc[4] is None


def test_rvi_trigger_never_fires_if_it_stays_inside_the_band():
    series = pd.Series([0.0, 0.05, -0.05, 0.1, -0.1, 0.15])
    triggers = rvi_trigger(series)
    assert all(t is None for t in triggers)


def test_rvi_trigger_direct_jump_between_extremes_does_not_fire():
    # Jumps from below -0.20 straight to above +0.20 without passing
    # through the neutral zone in between - re-arms for SHORT instead
    # of firing LONG, per the documented reading in indicators/rvi.py.
    series = pd.Series([0.0, -0.25, 0.30, 0.05])
    triggers = rvi_trigger(series)
    assert triggers.iloc[2] is None  # re-armed "above", no fire on the jump itself
    assert triggers.iloc[3] == Signal.SHORT  # then crosses back through +0.20


def test_rvi_incremental_matches_vectorized():
    df = synthetic_series_df(n=150)
    vectorized = rvi(df, period=14)
    bars = df_to_bars(df)

    state = RviState(period=14)
    incremental_values = []
    for bar in bars:
        (value, _trigger), state = rvi_update(state, bar)
        incremental_values.append(value)

    for i in range(len(bars)):
        if incremental_values[i] is None:
            assert math.isnan(vectorized.iloc[i]), f"bar {i}"
        else:
            assert math.isclose(incremental_values[i], vectorized.iloc[i], rel_tol=1e-9), f"bar {i}"


def test_rvi_incremental_trigger_matches_vectorized_trigger():
    df = synthetic_series_df(n=150)
    vectorized_rvi = rvi(df, period=14)
    vectorized_triggers = rvi_trigger(vectorized_rvi)
    bars = df_to_bars(df)

    state = RviState(period=14)
    incremental_triggers = []
    for bar in bars:
        (_value, trigger), state = rvi_update(state, bar)
        incremental_triggers.append(trigger)

    for i in range(len(bars)):
        expected = vectorized_triggers.iloc[i]
        assert incremental_triggers[i] == expected, f"bar {i}: expected {expected}, got {incremental_triggers[i]}"

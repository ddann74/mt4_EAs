"""Parabolic SAR correctness: a hand-worked 5-bar reversal sequence
(small enough to trace by hand step-by-step), plus a cross-check
against `ta.trend.PSARIndicator` (this module's algorithm was written
to mirror ta's structure exactly, so unlike ADX/MACD this comparison
should hold with no known-quirk caveat)."""
import math

import pandas as pd
import ta.trend

from tests.fixtures import df_to_bars, synthetic_series_df
from xauusd_indicators.indicators.parabolic_sar import (
    ParabolicSarState,
    parabolic_sar,
    parabolic_sar_direction,
    parabolic_sar_update,
)
from xauusd_indicators.types import Signal


def _hand_worked_df() -> pd.DataFrame:
    # 5 bars, clean uptrend continuation - hand-traced below.
    return pd.DataFrame(
        {
            "open": [10.0, 10.5, 11.0, 11.5, 12.0],
            "high": [10.8, 11.2, 11.8, 12.3, 12.8],
            "low": [9.9, 10.3, 10.8, 11.3, 11.8],
            "close": [10.5, 11.0, 11.5, 12.0, 12.5],
            "volume": [100, 100, 100, 100, 100],
        }
    )


def test_parabolic_sar_hand_traced_5_bar_uptrend():
    df = _hand_worked_df()
    step, max_step = 0.02, 0.20
    # Initialization (bar 0/1): up_trend=True, up_trend_high=high[0]=10.8,
    # down_trend_low=low[0]=9.9, af=0.02. psar[0]=psar[1]=undefined (NaN).
    #
    # Bar 2 (i=2): psar = psar[1] + af*(uth - psar[1]).
    #   ta/this module seed psar[1] = close[1] = 11.0 (psar := close.copy()).
    #   psar[2] = 11.0 + 0.02*(10.8-11.0) = 11.0 + 0.02*(-0.2) = 10.996
    #   low[2]=10.8 is not < 10.996? 10.8 < 10.996 -> True -> REVERSAL.
    #   So bar 2 actually reverses to downtrend: psar[2] = uth = 10.8,
    #   down_trend_low = low[2] = 10.8, af reset to 0.02, up_trend=False.
    result = parabolic_sar(df, step=step, max_step=max_step)
    assert math.isnan(result.iloc[0])
    assert math.isnan(result.iloc[1])
    assert math.isclose(result.iloc[2], 10.8, rel_tol=1e-9)

    # Bar 3 (i=3), now in downtrend: psar = psar[2] - af*(psar[2]-dtl)
    #   = 10.8 - 0.02*(10.8-10.8) = 10.8.
    #   high[3]=12.3 > 10.8 -> REVERSAL back to uptrend.
    #   psar[3] = down_trend_low = 10.8, up_trend_high = high[3] = 12.3, af=0.02.
    assert math.isclose(result.iloc[3], 10.8, rel_tol=1e-9)

    # Bar 4 (i=4), uptrend: psar = psar[3] + af*(uth-psar[3])
    #   = 10.8 + 0.02*(12.3-10.8) = 10.8 + 0.03 = 10.83
    #   low[4]=11.8, not < 10.83 -> no reversal.
    #   high[4]=12.8 > uth(12.3) -> new extreme, af -> 0.04.
    #   low1=low[3]=11.3, low2=low[2]=10.8: low2(10.8) < psar(10.83) -> psar=10.8.
    assert math.isclose(result.iloc[4], 10.8, rel_tol=1e-9)


def test_parabolic_sar_matches_ta_reference_library():
    df = synthetic_series_df(n=150)
    ours = parabolic_sar(df)
    reference = ta.trend.PSARIndicator(df["high"], df["low"], df["close"]).psar()
    for i in range(2, len(df)):
        assert math.isclose(ours.iloc[i], reference.iloc[i], rel_tol=1e-9), f"bar {i}"


def test_parabolic_sar_direction_is_long_above_and_short_below():
    df = synthetic_series_df(n=150)
    sar = parabolic_sar(df)
    direction = parabolic_sar_direction(df)
    for i in range(2, len(df)):
        expected = Signal.LONG if df["close"].iloc[i] > sar.iloc[i] else Signal.SHORT
        assert direction.iloc[i] == expected, f"bar {i}"


def test_parabolic_sar_incremental_matches_vectorized():
    df = synthetic_series_df(n=150)
    vectorized = parabolic_sar(df)
    bars = df_to_bars(df)

    state = ParabolicSarState()
    incremental_values = []
    for bar in bars:
        value, state = parabolic_sar_update(state, bar)
        incremental_values.append(value)

    for i in range(len(bars)):
        if incremental_values[i] is None:
            assert math.isnan(vectorized.iloc[i]), f"bar {i}"
        else:
            assert math.isclose(incremental_values[i], vectorized.iloc[i], rel_tol=1e-9), f"bar {i}"

"""Stochastic(50,10,10) correctness: independent hand-derivation (rolling
min/max/mean written fresh here, not reusing indicators/stochastic.py's
own logic) on a synthetic series, plus a partial `ta` cross-check of the
raw %K component (see module note below on why only partial)."""
import math

import ta.momentum

from tests.fixtures import df_to_bars, synthetic_series_df
from xauusd_indicators.indicators.stochastic import StochasticState, stochastic, stochastic_update


def _hand_derived_stochastic(df, k_period, k_slowing, d_period):
    highs = df["high"].tolist()
    lows = df["low"].tolist()
    closes = df["close"].tolist()
    n = len(df)

    raw_k = [None] * n
    for i in range(k_period - 1, n):
        window_high = max(highs[i - k_period + 1 : i + 1])
        window_low = min(lows[i - k_period + 1 : i + 1])
        raw_k[i] = 100 * (closes[i] - window_low) / (window_high - window_low)

    slow_k = [None] * n
    for i in range(n):
        if raw_k[i] is None:
            continue
        window = raw_k[i - k_slowing + 1 : i + 1]
        if len(window) == k_slowing and all(v is not None for v in window):
            slow_k[i] = sum(window) / k_slowing

    d = [None] * n
    for i in range(n):
        if slow_k[i] is None:
            continue
        window = slow_k[i - d_period + 1 : i + 1]
        if len(window) == d_period and all(v is not None for v in window):
            d[i] = sum(window) / d_period

    return slow_k, d


def test_stochastic_hand_derived_on_synthetic_series():
    df = synthetic_series_df(n=150)
    k_period, k_slowing, d_period = 50, 10, 10
    expected_k, expected_d = _hand_derived_stochastic(df, k_period, k_slowing, d_period)

    result_k, result_d = stochastic(df, k_period=k_period, k_slowing=k_slowing, d_period=d_period)

    checked_any = False
    for i in range(len(df)):
        if expected_k[i] is None:
            assert math.isnan(result_k.iloc[i]), f"bar {i} %K should still be warming up"
        else:
            assert math.isclose(result_k.iloc[i], expected_k[i], rel_tol=1e-9), f"bar {i} %K"
            checked_any = True
        if expected_d[i] is None:
            assert math.isnan(result_d.iloc[i]), f"bar {i} %D should still be warming up"
        else:
            assert math.isclose(result_d.iloc[i], expected_d[i], rel_tol=1e-9), f"bar {i} %D"
    assert checked_any, "expected at least some bars where %K is defined over a 150-bar series"


def test_stochastic_raw_k_matches_ta_reference_library():
    """`ta.momentum.StochasticOscillator` only supports the 2-parameter
    "Fast Stochastic" model (window + a single smooth_window applied once
    for %D) - it has no way to express MT4's 3-parameter Slow Stochastic
    (%K period, %K slowing, %D period) this module implements. Setting
    smooth_window=1 makes ta's .stoch() return the *unsmoothed* raw %K,
    which is directly comparable to this module's own internal raw %K
    (not otherwise exposed) - confirms the core high/low/close
    normalization formula against an independent library, even though the
    two extra SMA layers (%K slowing, %D) can only be checked by hand
    (see test above)."""
    df = synthetic_series_df(n=150)
    period = 50

    lowest_low = df["low"].rolling(window=period).min()
    highest_high = df["high"].rolling(window=period).max()
    our_raw_k = 100 * (df["close"] - lowest_low) / (highest_high - lowest_low)

    reference = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"], window=period, smooth_window=1).stoch()

    for i in range(period, len(df)):
        assert math.isclose(our_raw_k.iloc[i], reference.iloc[i], rel_tol=1e-6), f"bar {i}"


def test_stochastic_incremental_matches_vectorized():
    df = synthetic_series_df(n=150)
    vectorized_k, vectorized_d = stochastic(df, k_period=50, k_slowing=10, d_period=10)
    bars = df_to_bars(df)

    state = StochasticState(k_period=50, k_slowing=10, d_period=10)
    incremental_k = []
    incremental_d = []
    for bar in bars:
        (k, d), state = stochastic_update(state, bar)
        incremental_k.append(k)
        incremental_d.append(d)

    checked_any = False
    for i in range(len(bars)):
        if incremental_k[i] is None:
            assert math.isnan(vectorized_k.iloc[i]), f"bar {i} %K"
        else:
            assert math.isclose(incremental_k[i], vectorized_k.iloc[i], rel_tol=1e-9), f"bar {i} %K"
            checked_any = True
        if incremental_d[i] is None:
            assert math.isnan(vectorized_d.iloc[i]), f"bar {i} %D"
        else:
            assert math.isclose(incremental_d[i], vectorized_d.iloc[i], rel_tol=1e-9), f"bar {i} %D"
    assert checked_any, "expected at least some bars where %K is defined"

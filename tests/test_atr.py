"""ATR(14) / volatility ratio correctness, verified two independent
ways: (1) a hand-derived recurrence worked out step-by-step in this
file (not a call into the module under test), on the fixture where
every true range is designed to be a round number by construction, and
(2) a cross-check against the `ta` reference library's
AverageTrueRange on a longer synthetic series.
"""
import math

import ta.volatility

from tests.fixtures import synthetic_series_df, tiny_uptrend_df, df_to_bars
from xauusd_indicators.indicators.atr import AtrState, atr, atr_update, true_range, volatility_ratio


def test_true_range_hand_computed_on_tiny_fixture():
    df = tiny_uptrend_df()
    tr = true_range(df)
    # By construction (see fixtures.tiny_uptrend_df docstring):
    # bar 0 has no previous close, so TR[0] = high[0]-low[0] = 1.0.
    # Every later bar: high-low=1.0, |high-prev_close|=1.3, |low-prev_close|=0.3
    # -> TR = max(1.0, 1.3, 0.3) = 1.3.
    assert math.isclose(tr.iloc[0], 1.0, abs_tol=1e-9)
    for i in range(1, len(tr)):
        assert math.isclose(tr.iloc[i], 1.3, abs_tol=1e-9), f"bar {i}"


def test_atr_hand_computed_recurrence_on_tiny_fixture():
    df = tiny_uptrend_df()
    period = 14
    # Independent hand-derivation: TR = [1.0] + [1.3]*19 (see test above).
    tr_values = [1.0] + [1.3] * 19
    expected_seed = sum(tr_values[:period]) / period
    expected = [expected_seed]
    prev = expected_seed
    for tr in tr_values[period:]:
        prev = (prev * (period - 1) + tr) / period
        expected.append(prev)

    result = atr(df, period=period)
    assert result.iloc[: period - 1].isna().all(), "no ATR value before enough bars have accumulated"
    for offset, exp in enumerate(expected):
        idx = period - 1 + offset
        assert math.isclose(result.iloc[idx], exp, rel_tol=1e-9), f"bar {idx}: expected {exp}, got {result.iloc[idx]}"


def test_atr_matches_ta_reference_library_on_synthetic_series():
    df = synthetic_series_df(n=200)
    ours = atr(df, period=14)
    reference = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()
    # ta's implementation fills pre-window bars with 0.0 rather than NaN
    # (see AverageTrueRange._run - np.zeros then only [window-1:] set),
    # so comparison starts once both are actually defined.
    for i in range(14, len(df)):
        assert math.isclose(ours.iloc[i], reference.iloc[i], rel_tol=1e-6), f"bar {i}"


def test_volatility_ratio_is_atr_over_its_own_50bar_average():
    df = synthetic_series_df(n=200)
    a = atr(df, period=14)
    ratio = volatility_ratio(df, atr_period=14, avg_period=50)
    # Hand-check a specific bar: ratio[100] should equal a[100] / mean(a[51:101]).
    expected = a.iloc[100] / a.iloc[51:101].mean()
    assert math.isclose(ratio.iloc[100], expected, rel_tol=1e-9)
    assert ratio.iloc[:62].isna().all(), "needs 14 (ATR warmup) + 50 (avg window) - 1 = 62 bars before first value"


def test_atr_incremental_matches_vectorized():
    df = synthetic_series_df(n=150)
    vectorized = atr(df, period=14)
    bars = df_to_bars(df)

    state = AtrState(period=14)
    incremental_values = []
    for bar in bars:
        value, state = atr_update(state, bar)
        incremental_values.append(value)

    for i in range(len(bars)):
        if incremental_values[i] is None:
            assert math.isnan(vectorized.iloc[i]) or i < 13, f"bar {i}"
        else:
            assert math.isclose(incremental_values[i], vectorized.iloc[i], rel_tol=1e-9), f"bar {i}"

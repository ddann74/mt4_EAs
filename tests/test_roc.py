"""ROC(10) correctness: hand-computed on the tiny fixture plus a
cross-check against `ta.momentum.ROCIndicator`."""
import math

import ta.momentum

from tests.fixtures import df_to_bars, synthetic_series_df, tiny_uptrend_df
from xauusd_indicators.indicators.roc import RocState, roc, roc_update


def test_roc_hand_computed_on_tiny_fixture():
    df = tiny_uptrend_df()
    # close[i] = 100.5 + i (see fixtures.tiny_uptrend_df), so
    # ROC(10)[i] = 100 * (close[i]-close[i-10]) / close[i-10]
    #            = 100 * 10 / close[i-10] for i >= 10.
    result = roc(df, period=10)
    assert result.iloc[:10].isna().all()
    closes = df["close"].tolist()
    for i in range(10, len(df)):
        expected = 100 * (closes[i] - closes[i - 10]) / closes[i - 10]
        assert math.isclose(result.iloc[i], expected, rel_tol=1e-9), f"bar {i}"


def test_roc_matches_ta_reference_library():
    df = synthetic_series_df(n=100)
    ours = roc(df, period=10)
    reference = ta.momentum.ROCIndicator(df["close"], window=10).roc()
    for i in range(10, len(df)):
        assert math.isclose(ours.iloc[i], reference.iloc[i], rel_tol=1e-6), f"bar {i}"


def test_roc_incremental_matches_vectorized():
    df = synthetic_series_df(n=100)
    vectorized = roc(df, period=10)
    bars = df_to_bars(df)

    state = RocState(period=10)
    incremental_values = []
    for bar in bars:
        value, state = roc_update(state, bar)
        incremental_values.append(value)

    for i in range(len(bars)):
        if incremental_values[i] is None:
            assert math.isnan(vectorized.iloc[i]), f"bar {i}"
        else:
            assert math.isclose(incremental_values[i], vectorized.iloc[i], rel_tol=1e-9), f"bar {i}"

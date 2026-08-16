"""Force Index(50) correctness: independent hand-derivation (EMA
recursion written fresh here, not reusing indicators/force_index.py's
own helper) on a synthetic series, plus a `ta` reference-library
cross-check - exact match once the masking-convention difference noted
in the module docstring is accounted for."""
import math

import ta.volume

from tests.fixtures import df_to_bars, synthetic_series_df
from xauusd_indicators.indicators.force_index import ForceIndexState, force_index, force_index_update


def _hand_derived_force_index(df, period):
    closes = df["close"].tolist()
    volumes = df["volume"].tolist()
    n = len(df)
    alpha = 2 / (period + 1)

    raw = [None] + [(closes[i] - closes[i - 1]) * volumes[i] for i in range(1, n)]

    smoothed = [None] * n
    prev = None
    for i in range(1, n):
        prev = raw[i] if prev is None else alpha * raw[i] + (1 - alpha) * prev
        smoothed[i] = prev

    result = [None] * n
    for i in range(period, n):
        result[i] = smoothed[i]
    return result


def test_force_index_hand_derived_on_synthetic_series():
    df = synthetic_series_df(n=120)
    period = 50
    expected = _hand_derived_force_index(df, period)

    result = force_index(df, period=period)

    checked_any = False
    for i in range(len(df)):
        if expected[i] is None:
            assert math.isnan(result.iloc[i]), f"bar {i} should still be warming up"
        else:
            assert math.isclose(result.iloc[i], expected[i], rel_tol=1e-9), f"bar {i}"
            checked_any = True
    assert checked_any, "expected at least some bars where force index is defined over a 120-bar series"


def test_force_index_matches_ta_reference_library():
    df = synthetic_series_df(n=120)
    period = 50
    ours = force_index(df, period=period)
    reference = ta.volume.ForceIndexIndicator(df["close"], df["volume"], window=period).force_index()

    assert ours.first_valid_index() == reference.first_valid_index(), (
        "warmup length should match ta's ForceIndexIndicator exactly - see module docstring on its masking convention"
    )
    for i in range(period, len(df)):
        assert math.isclose(ours.iloc[i], reference.iloc[i], rel_tol=1e-6), f"bar {i}"


def test_force_index_incremental_matches_vectorized():
    df = synthetic_series_df(n=120)
    period = 50
    vectorized = force_index(df, period=period)
    bars = df_to_bars(df)

    state = ForceIndexState(period=period)
    incremental_values = []
    for bar in bars:
        value, state = force_index_update(state, bar)
        incremental_values.append(value)

    checked_any = False
    for i in range(len(bars)):
        if incremental_values[i] is None:
            assert math.isnan(vectorized.iloc[i]), f"bar {i}"
        else:
            assert math.isclose(incremental_values[i], vectorized.iloc[i], rel_tol=1e-9), f"bar {i}"
            checked_any = True
    assert checked_any, "expected at least some bars where force index is defined"

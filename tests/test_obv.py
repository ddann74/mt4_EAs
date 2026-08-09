"""OBV + slope correctness: hand-computed on the tiny fixture, plus a
documented cross-check against `ta.volume.OnBalanceVolumeIndicator`.

Cross-check caveat (verified, not assumed): `ta`'s OBV treats "close
not less than previous close" as +volume, which means bar 0 (no
previous close - comparison against NaN is always False) gets +volume
there too. This module follows the textbook OBV definition (Wikipedia:
flat close -> unchanged OBV; bar 0 has no defined direction yet -> 0
contribution). That makes `ta`'s series a constant offset above ours
(exactly +volume[0], confirmed numerically while writing this test) as
long as no exact-tie bars occur elsewhere - true for this fixture's
continuous synthetic floats. The test below asserts that exact,
verified relationship rather than raw equality.
"""
import math

from tests.fixtures import df_to_bars, synthetic_series_df, tiny_uptrend_df
from xauusd_indicators.indicators.obv import ObvState, obv, obv_slope, obv_update


def test_obv_hand_computed_on_tiny_fixture():
    df = tiny_uptrend_df()
    # closes are strictly increasing (see fixtures.tiny_uptrend_df), so
    # every bar after the first is an up-close bar: OBV = cumulative
    # sum of volume from bar 1 onward, with bar 0 contributing 0.
    result = obv(df)
    volumes = df["volume"].tolist()
    expected = 0.0
    assert math.isclose(result.iloc[0], 0.0, abs_tol=1e-9)
    running = 0.0
    for i in range(1, len(df)):
        running += volumes[i]
        assert math.isclose(result.iloc[i], running, rel_tol=1e-9), f"bar {i}"


def test_obv_slope_hand_computed_on_tiny_fixture():
    df = tiny_uptrend_df()
    series = obv(df)
    slope = obv_slope(df, lookback=10)
    assert slope.iloc[:10].isna().all()
    for i in range(10, len(df)):
        expected = series.iloc[i] - series.iloc[i - 10]
        assert math.isclose(slope.iloc[i], expected, rel_tol=1e-9), f"bar {i}"


def test_obv_matches_ta_reference_library_up_to_known_bar0_offset():
    import ta.volume

    df = synthetic_series_df(n=100)
    assert (df["close"].diff() == 0).sum() == 0, "fixture assumption: no exact ties, so the offset below is exact"

    ours = obv(df)
    reference = ta.volume.OnBalanceVolumeIndicator(df["close"], df["volume"]).on_balance_volume()
    expected_offset = df["volume"].iloc[0]
    for i in range(len(df)):
        assert math.isclose(reference.iloc[i] - ours.iloc[i], expected_offset, rel_tol=1e-9), f"bar {i}"


def test_obv_incremental_matches_vectorized():
    df = synthetic_series_df(n=100)
    vectorized_obv = obv(df)
    vectorized_slope = obv_slope(df, lookback=10)
    bars = df_to_bars(df)

    state = ObvState(lookback=10)
    incremental_obv = []
    incremental_slope = []
    for bar in bars:
        (obv_value, slope_value), state = obv_update(state, bar)
        incremental_obv.append(obv_value)
        incremental_slope.append(slope_value)

    for i in range(len(bars)):
        assert math.isclose(incremental_obv[i], vectorized_obv.iloc[i], rel_tol=1e-9), f"obv bar {i}"
        if incremental_slope[i] is None:
            assert math.isnan(vectorized_slope.iloc[i]), f"slope bar {i}"
        else:
            assert math.isclose(incremental_slope[i], vectorized_slope.iloc[i], rel_tol=1e-9), f"slope bar {i}"

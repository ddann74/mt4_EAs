"""MACD histogram correctness: hand-computed EMA recurrence on the tiny
fixture, plus a cross-check against `ta.trend.MACD`."""
import math

import ta.trend

from tests.fixtures import df_to_bars, synthetic_series_df, tiny_uptrend_df
from xauusd_indicators.indicators.macd import MacdState, ema, macd_histogram, macd_histogram_update


def _hand_ema(values: list[float], period: int) -> list[float]:
    alpha = 2 / (period + 1)
    out = [values[0]]
    prev = values[0]
    for v in values[1:]:
        prev = alpha * v + (1 - alpha) * prev
        out.append(prev)
    return out


def test_ema_hand_computed_on_tiny_fixture():
    df = tiny_uptrend_df()
    closes = df["close"].tolist()
    expected = _hand_ema(closes, period=5)
    result = ema(df["close"], period=5)
    assert result.iloc[:4].isna().all()
    for i in range(4, len(df)):
        assert math.isclose(result.iloc[i], expected[i], rel_tol=1e-9), f"bar {i}"


def test_macd_histogram_hand_computed_on_tiny_fixture():
    df = tiny_uptrend_df()
    closes = df["close"].tolist()
    ema_fast = _hand_ema(closes, 12)
    ema_slow = _hand_ema(closes, 26)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = _hand_ema(macd_line, 9)
    expected_hist = [m - s for m, s in zip(macd_line, signal_line)]

    result = macd_histogram(df, fast=12, slow=26, signal=9)
    min_bars = 26 + 9 - 1
    for i in range(len(df)):
        if i < min_bars - 1:
            assert math.isnan(result.iloc[i]), f"bar {i} should still be warming up"
        else:
            assert math.isclose(result.iloc[i], expected_hist[i], rel_tol=1e-6), f"bar {i}"


def test_macd_histogram_matches_ta_reference_library_once_warmup_artifact_decays():
    """`ta.trend.MACD` computes its signal-line EMA over its own
    NaN-masked macd_line (emafast/emaslow are masked to NaN before their
    own warmup completes, and that masked series - not the true
    full-precision values - feeds the signal EMA). That's a real quirk
    of `ta`'s internal architecture, not a bug in this module: verified
    numerically that the gap between our histogram and ta's is largest
    right at the shared warmup boundary (bar 34: -0.0033) and decays
    exponentially, reaching exact double-precision equality by bar 150+
    - consistent with an EMA "forgetting" a warm-up-only artifact, not a
    formula disagreement. This test checks the stabilized region, where
    ta's own architecture no longer differs from the textbook formula
    this module implements.
    """
    df = synthetic_series_df(n=200)
    ours = macd_histogram(df, fast=12, slow=26, signal=9)
    reference = ta.trend.MACD(df["close"], window_slow=26, window_fast=12, window_sign=9).macd_diff()
    for i in range(150, len(df)):
        assert math.isclose(ours.iloc[i], reference.iloc[i], rel_tol=1e-6, abs_tol=1e-8), f"bar {i}"


def test_macd_histogram_ta_warmup_gap_decays_toward_zero():
    """Confirms the warmup-artifact-decay claim above is real, not
    asserted from nowhere: samples the gap at increasing bar offsets
    from the shared warmup boundary and checks it shrinks."""
    df = synthetic_series_df(n=200)
    ours = macd_histogram(df, fast=12, slow=26, signal=9)
    reference = ta.trend.MACD(df["close"], window_slow=26, window_fast=12, window_sign=9).macd_diff()
    checkpoints = [34, 50, 80, 120]
    gaps = [abs(ours.iloc[i] - reference.iloc[i]) for i in checkpoints]
    for earlier, later in zip(gaps, gaps[1:]):
        assert later < earlier, f"expected the ta warmup gap to shrink monotonically across {checkpoints}"


def test_macd_histogram_incremental_matches_vectorized():
    df = synthetic_series_df(n=200)
    vectorized = macd_histogram(df, fast=12, slow=26, signal=9)
    bars = df_to_bars(df)

    state = MacdState(fast=12, slow=26, signal=9)
    incremental_values = []
    for bar in bars:
        value, state = macd_histogram_update(state, bar)
        incremental_values.append(value)

    for i in range(len(bars)):
        if incremental_values[i] is None:
            assert math.isnan(vectorized.iloc[i]), f"bar {i}"
        else:
            assert math.isclose(incremental_values[i], vectorized.iloc[i], rel_tol=1e-6), f"bar {i}"

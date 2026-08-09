"""Real-data validation - skipped unless real OHLCV data is actually
present locally (never committed to this repo, see .gitignore).

This is NOT a correctness test in the same sense as the hand-computed/
library-cross-check tests elsewhere - those already prove the formulas
are right. This test proves the formulas behave sanely on real data:
no crashes, no unexpected NaN/inf, warmup lengths exactly match what
each indicator's own docstring promises. Run it locally by placing a
CSV with open,high,low,close,volume columns at
data/xauusd_m1_real.csv (or point XAUUSD_REAL_CSV at a different path).
"""
import math
import os
from pathlib import Path

import pandas as pd
import pytest

from xauusd_indicators.pipeline import Variant, compute_all_indicators, entry_signal

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "xauusd_m1_real.csv"
_PATH = Path(os.environ.get("XAUUSD_REAL_CSV", _DEFAULT_PATH))

pytestmark = pytest.mark.skipif(not _PATH.exists(), reason=f"no real data at {_PATH} - see this file's docstring")


@pytest.fixture(scope="module")
def real_df():
    return pd.read_csv(_PATH)


@pytest.fixture(scope="module")
def enriched(real_df):
    return compute_all_indicators(real_df)


def test_real_data_loads_with_expected_columns(real_df):
    assert {"open", "high", "low", "close", "volume"}.issubset(real_df.columns)
    assert len(real_df) > 1000, "expected a real, non-trivial dataset"


def test_no_ohlc_invariant_violations_in_the_source_data(real_df):
    # Not a property of this project's code - a sanity check that the
    # data itself is well-formed before trusting any result computed
    # from it.
    assert (real_df["high"] >= real_df["low"]).all()
    assert (real_df["high"] >= real_df["open"]).all()
    assert (real_df["high"] >= real_df["close"]).all()
    assert (real_df["low"] <= real_df["open"]).all()
    assert (real_df["low"] <= real_df["close"]).all()
    assert (real_df["volume"] > 0).all()


def test_every_indicator_warmup_length_matches_its_own_documentation(enriched):
    # These exact counts are what each indicator module's own docstring
    # promises (ATR period-1=13, ADX 2*period-2=26, volatility_ratio
    # 14+50-2=62, ROC period=10, OBV slope lookback=10, MACD
    # slow+signal-2=33, Parabolic SAR bars 0-1=2, RVI period-1=13). A
    # mismatch here on real data would mean the warmup logic behaves
    # differently than on the synthetic fixtures it was proven correct
    # against - which would be a real finding, not expected.
    expected_nan_counts = {
        "atr": 13,
        "volatility_ratio": 62,
        "adx": 26,
        "rvi": 13,
        "roc": 10,
        "obv_slope": 10,
        "macd_histogram": 33,
        "parabolic_sar": 2,
    }
    for column, expected in expected_nan_counts.items():
        actual = enriched[column].isna().sum()
        assert actual == expected, f"{column}: expected {expected} NaN (warmup), got {actual}"
    assert enriched["obv"].isna().sum() == 0


def test_no_infinities_anywhere(enriched):
    numeric_cols = ["atr", "volatility_ratio", "adx", "rvi", "roc", "obv", "obv_slope", "macd_histogram", "parabolic_sar"]
    for column in numeric_cols:
        values = pd.to_numeric(enriched[column], errors="coerce").dropna()
        assert not values.apply(math.isinf).any(), f"{column} produced an infinite value on real data"


def test_adx_stays_within_0_100_on_real_data(enriched):
    values = enriched["adx"].dropna()
    assert (values >= 0).all()
    assert (values <= 100).all()


def test_entry_signals_run_without_crashing_on_real_data_for_every_variant(real_df):
    for variant in Variant:
        signals = entry_signal(real_df, variant)
        assert len(signals) == len(real_df)
        # Every non-None value must be a real Signal, not something
        # malformed leaking out of the composition logic.
        from xauusd_indicators.types import Signal

        assert all(s is None or s in (Signal.LONG, Signal.SHORT) for s in signals)

"""Section 6 entry composition: branch coverage via injected base signal
+ the three momentum filters."""
import pandas as pd

from tests.fixtures import synthetic_series_df
from xauusd_indicators.signals.section6 import entry_signal
from xauusd_indicators.types import Signal


def _placeholder_df(n=6):
    return synthetic_series_df(n=n)


def test_long_fires_when_all_three_momentum_filters_agree():
    df = _placeholder_df()
    base = pd.Series([None, Signal.LONG, None, None, None, None], index=df.index)
    roc_series = pd.Series([1.0] * len(df), index=df.index)
    obv_slope_series = pd.Series([50.0] * len(df), index=df.index)
    macd_series = pd.Series([0.02] * len(df), index=df.index)
    result = entry_signal(df, base_signal=base, roc_series=roc_series, obv_slope_series=obv_slope_series, macd_series=macd_series)
    assert result.iloc[1] == Signal.LONG


def test_short_fires_when_all_three_momentum_filters_agree():
    df = _placeholder_df()
    base = pd.Series([None, None, Signal.SHORT, None, None, None], index=df.index)
    roc_series = pd.Series([-1.0] * len(df), index=df.index)
    obv_slope_series = pd.Series([-50.0] * len(df), index=df.index)
    macd_series = pd.Series([-0.02] * len(df), index=df.index)
    result = entry_signal(df, base_signal=base, roc_series=roc_series, obv_slope_series=obv_slope_series, macd_series=macd_series)
    assert result.iloc[2] == Signal.SHORT


def test_long_blocked_when_roc_disagrees():
    df = _placeholder_df()
    base = pd.Series([None, Signal.LONG, None, None, None, None], index=df.index)
    roc_series = pd.Series([-0.5] * len(df), index=df.index)  # disagrees
    obv_slope_series = pd.Series([50.0] * len(df), index=df.index)
    macd_series = pd.Series([0.02] * len(df), index=df.index)
    result = entry_signal(df, base_signal=base, roc_series=roc_series, obv_slope_series=obv_slope_series, macd_series=macd_series)
    assert result.iloc[1] is None


def test_long_blocked_when_obv_slope_disagrees():
    df = _placeholder_df()
    base = pd.Series([None, Signal.LONG, None, None, None, None], index=df.index)
    roc_series = pd.Series([1.0] * len(df), index=df.index)
    obv_slope_series = pd.Series([-50.0] * len(df), index=df.index)  # disagrees
    macd_series = pd.Series([0.02] * len(df), index=df.index)
    result = entry_signal(df, base_signal=base, roc_series=roc_series, obv_slope_series=obv_slope_series, macd_series=macd_series)
    assert result.iloc[1] is None


def test_long_blocked_when_macd_disagrees():
    df = _placeholder_df()
    base = pd.Series([None, Signal.LONG, None, None, None, None], index=df.index)
    roc_series = pd.Series([1.0] * len(df), index=df.index)
    obv_slope_series = pd.Series([50.0] * len(df), index=df.index)
    macd_series = pd.Series([-0.02] * len(df), index=df.index)  # disagrees
    result = entry_signal(df, base_signal=base, roc_series=roc_series, obv_slope_series=obv_slope_series, macd_series=macd_series)
    assert result.iloc[1] is None


def test_no_signal_when_base_section2_entry_is_none():
    df = _placeholder_df()
    base = pd.Series([None] * len(df), index=df.index)
    roc_series = pd.Series([1.0] * len(df), index=df.index)
    obv_slope_series = pd.Series([50.0] * len(df), index=df.index)
    macd_series = pd.Series([0.02] * len(df), index=df.index)
    result = entry_signal(df, base_signal=base, roc_series=roc_series, obv_slope_series=obv_slope_series, macd_series=macd_series)
    assert all(v is None for v in result)


def test_section6_end_to_end_on_real_dataframe_does_not_crash():
    df = synthetic_series_df(n=250)
    result = entry_signal(df)
    assert len(result) == len(df)
    assert set(v for v in result if v is not None) <= {Signal.LONG, Signal.SHORT}

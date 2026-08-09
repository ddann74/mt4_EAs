"""Section 6a entry composition: branch coverage via injected base
signal + SAR direction."""
import pandas as pd

from tests.fixtures import synthetic_series_df
from xauusd_indicators.signals.section6a import entry_signal
from xauusd_indicators.types import Signal


def _placeholder_df(n=6):
    return synthetic_series_df(n=n)


def test_long_fires_when_sar_agrees():
    df = _placeholder_df()
    base = pd.Series([None, Signal.LONG, None, None, None, None], index=df.index)
    sar_direction = pd.Series([Signal.LONG] * len(df), index=df.index)
    result = entry_signal(df, base_signal=base, sar_direction=sar_direction)
    assert result.iloc[1] == Signal.LONG


def test_short_fires_when_sar_agrees():
    df = _placeholder_df()
    base = pd.Series([None, None, Signal.SHORT, None, None, None], index=df.index)
    sar_direction = pd.Series([Signal.SHORT] * len(df), index=df.index)
    result = entry_signal(df, base_signal=base, sar_direction=sar_direction)
    assert result.iloc[2] == Signal.SHORT


def test_long_blocked_when_sar_disagrees():
    df = _placeholder_df()
    base = pd.Series([None, Signal.LONG, None, None, None, None], index=df.index)
    sar_direction = pd.Series([Signal.SHORT] * len(df), index=df.index)
    result = entry_signal(df, base_signal=base, sar_direction=sar_direction)
    assert result.iloc[1] is None


def test_blocked_when_sar_direction_is_none_still_warming_up():
    df = _placeholder_df()
    base = pd.Series([None, Signal.LONG, None, None, None, None], index=df.index)
    sar_direction = pd.Series([None] * len(df), index=df.index)
    result = entry_signal(df, base_signal=base, sar_direction=sar_direction)
    assert result.iloc[1] is None


def test_section6a_end_to_end_on_real_dataframe_does_not_crash():
    df = synthetic_series_df(n=250)
    result = entry_signal(df)
    assert len(result) == len(df)
    assert set(v for v in result if v is not None) <= {Signal.LONG, Signal.SHORT}

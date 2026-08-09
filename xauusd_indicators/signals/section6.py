"""Section 6: Section 2's entry conditions, plus ROC(10), OBV slope, and
MACD histogram must all agree with the trigger's direction (all
positive for LONG, all negative for SHORT). Exit is the same as Section
2 (report: "same core as Section 2" - only the entry gains extra
filters, no mention of the exit changing).
"""
from __future__ import annotations

import pandas as pd

from ..indicators.macd import macd_histogram
from ..indicators.obv import obv_slope
from ..indicators.roc import roc
from ..types import Signal
from .section2 import entry_signal as section2_entry_signal
from .section2 import exit_fired  # noqa: F401 - re-exported: Section 6 shares Section 2's exit unchanged


def entry_signal(
    df: pd.DataFrame,
    *,
    base_signal: pd.Series | None = None,
    roc_series: pd.Series | None = None,
    obv_slope_series: pd.Series | None = None,
    macd_series: pd.Series | None = None,
) -> pd.Series:
    """See section2.entry_signal's docstring for why these overrides
    exist (composition-logic branch coverage, decoupled from indicator
    formula correctness)."""
    base = base_signal if base_signal is not None else section2_entry_signal(df)
    roc_series = roc_series if roc_series is not None else roc(df)
    obv_slope_series = obv_slope_series if obv_slope_series is not None else obv_slope(df)
    macd_series = macd_series if macd_series is not None else macd_histogram(df)

    result = pd.Series(index=df.index, dtype=object)
    for i in range(len(df)):
        candidate = base.iloc[i]
        if candidate is None:
            result.iloc[i] = None
            continue
        r, o, m = roc_series.iloc[i], obv_slope_series.iloc[i], macd_series.iloc[i]
        if pd.isna(r) or pd.isna(o) or pd.isna(m):
            result.iloc[i] = None
            continue
        if candidate == Signal.LONG:
            result.iloc[i] = candidate if (r > 0 and o > 0 and m > 0) else None
        else:
            result.iloc[i] = candidate if (r < 0 and o < 0 and m < 0) else None
    return result

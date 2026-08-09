"""Convenience entry points that tie the individual indicator/signal
modules together - "give me a DataFrame with every indicator column"
and "give me the entry signal for variant X" - without requiring a
caller to know the internal module layout. Nothing here computes
anything the individual modules don't already compute; this is
composition/dispatch only, no new math.
"""
from __future__ import annotations

from enum import Enum
from typing import Callable

import pandas as pd

from .indicators.adx import adx
from .indicators.atr import atr, volatility_ratio
from .indicators.macd import macd_histogram
from .indicators.obv import obv, obv_slope
from .indicators.parabolic_sar import parabolic_sar, parabolic_sar_direction
from .indicators.roc import roc
from .indicators.rvi import rvi, rvi_trigger
from .signals import section2, section6, section6a, section7


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Returns a copy of `df` with one column added per indicator this
    project implements. Column values are NaN/None during each
    indicator's own warmup period, same as calling each function
    directly - see the individual indicator modules for exact warmup
    lengths."""
    out = df.copy()
    out["atr"] = atr(df)
    out["volatility_ratio"] = volatility_ratio(df)
    out["adx"] = adx(df)
    out["rvi"] = rvi(df)
    out["rvi_trigger"] = rvi_trigger(out["rvi"])
    out["roc"] = roc(df)
    out["obv"] = obv(df)
    out["obv_slope"] = obv_slope(df)
    out["macd_histogram"] = macd_histogram(df)
    out["parabolic_sar"] = parabolic_sar(df)
    out["parabolic_sar_direction"] = parabolic_sar_direction(df)
    return out


class Variant(Enum):
    SECTION_2 = "section2"
    SECTION_6 = "section6"
    SECTION_6A = "section6a"
    SECTION_7 = "section7"


_ENTRY_FUNCS: dict[Variant, Callable[[pd.DataFrame], pd.Series]] = {
    Variant.SECTION_2: section2.entry_signal,
    Variant.SECTION_6: section6.entry_signal,
    Variant.SECTION_6A: section6a.entry_signal,
    Variant.SECTION_7: section7.entry_signal,  # same function object as section2.entry_signal
}

_EXIT_FUNCS: dict[Variant, Callable[..., bool]] = {
    Variant.SECTION_2: section2.exit_fired,
    Variant.SECTION_6: section6.exit_fired,  # re-exported from section2, unchanged
    Variant.SECTION_6A: section6a.exit_fired,  # re-exported from section2, unchanged
    Variant.SECTION_7: section7.exit_fired,
}


def entry_signal(df: pd.DataFrame, variant: Variant) -> pd.Series:
    """Dispatches to the requested report variant's entry logic. Each
    variant's own module (signals/sectionN.py) is the source of truth
    for what "entry" means for it - this function only routes to it."""
    return _ENTRY_FUNCS[variant](df)


def exit_fired(df: pd.DataFrame, variant: Variant, position, current_bar_index: int, atr_at_entry: float, rvi_triggers: pd.Series) -> bool:
    """Dispatches to the requested report variant's exit logic."""
    return _EXIT_FUNCS[variant](df, position, current_bar_index, atr_at_entry, rvi_triggers)

"""User-added alarm: Stochastic(50,10,10) and Force Index(50) hitting
extreme readings. NOT part of the source XAUUSD Strategy Analysis report
- see docs/PRD.md §10 for the full scope note on how this differs from
every other module in this package (indicators/, signals/), which are
all report-derived.

Two independent conditions, each capable of firing on its own - they
measure genuinely different things (Stochastic: overbought/oversold
exhaustion relative to the recent trading range; Force Index: raw
buying/selling pressure momentum), so unlike the report's Section
6/6a filters (which require several indicators to *agree* with a trade
direction), this doesn't require Stochastic and Force Index to agree
with each other. A bar can fire both, one, or neither.

Stochastic requires BOTH %K and %D past the threshold together (the
user's explicit choice when asked, over the more sensitive "either line"
or "%K only" readings) - a momentary %K spike alone, with %D still
inside the band, does not fire this alarm.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from ..indicators.force_index import ForceIndexState, force_index, force_index_update
from ..indicators.stochastic import StochasticState, stochastic, stochastic_update
from ..types import Bar

STOCHASTIC_OVERBOUGHT_LEVEL = 90.0
STOCHASTIC_OVERSOLD_LEVEL = 10.0
FORCE_INDEX_HIGH_LEVEL = 70.0
FORCE_INDEX_LOW_LEVEL = -70.0


class ExtremeAlarm(Enum):
    STOCHASTIC_OVERBOUGHT = "stochastic_overbought"
    STOCHASTIC_OVERSOLD = "stochastic_oversold"
    FORCE_INDEX_HIGH = "force_index_high"
    FORCE_INDEX_LOW = "force_index_low"


def evaluate_extremes(
    stochastic_k: float | None,
    stochastic_d: float | None,
    force_index_value: float | None,
) -> list[ExtremeAlarm]:
    """Pure decision function - given already-computed indicator values
    for one bar, which alarms (zero, one, or more) fire. Kept separate
    from the DataFrame-level extremes()/incremental extremes_update()
    below so both share exactly one place the threshold logic lives -
    same shape as this account's ad-blocker project's FilterEngine.evaluate():
    pure decision logic, no data-fetching or indicator-computation mixed in.
    None inputs (still-warming-up bars) never fire anything."""
    alarms: list[ExtremeAlarm] = []
    if stochastic_k is not None and stochastic_d is not None:
        if stochastic_k > STOCHASTIC_OVERBOUGHT_LEVEL and stochastic_d > STOCHASTIC_OVERBOUGHT_LEVEL:
            alarms.append(ExtremeAlarm.STOCHASTIC_OVERBOUGHT)
        elif stochastic_k < STOCHASTIC_OVERSOLD_LEVEL and stochastic_d < STOCHASTIC_OVERSOLD_LEVEL:
            alarms.append(ExtremeAlarm.STOCHASTIC_OVERSOLD)
    if force_index_value is not None:
        if force_index_value > FORCE_INDEX_HIGH_LEVEL:
            alarms.append(ExtremeAlarm.FORCE_INDEX_HIGH)
        elif force_index_value < FORCE_INDEX_LOW_LEVEL:
            alarms.append(ExtremeAlarm.FORCE_INDEX_LOW)
    return alarms


def extremes_trigger(stochastic_k: pd.Series, stochastic_d: pd.Series, force_index_series: pd.Series) -> pd.Series:
    """Vectorized-input, per-bar-decision wrapper: one pass over the three
    already-computed indicator Series, calling evaluate_extremes() per bar
    so the vectorized and incremental paths share exactly one decision
    function rather than duplicating the threshold conditions. Returns a
    Series of list[ExtremeAlarm] (empty list where nothing fires)."""
    result = pd.Series(index=stochastic_k.index, dtype=object)
    for i in range(len(stochastic_k)):
        k = stochastic_k.iloc[i]
        d = stochastic_d.iloc[i]
        fi = force_index_series.iloc[i]
        result.iloc[i] = evaluate_extremes(
            None if pd.isna(k) else k,
            None if pd.isna(d) else d,
            None if pd.isna(fi) else fi,
        )
    return result


def extremes(df: pd.DataFrame) -> pd.DataFrame:
    """Computes Stochastic(50,10,10) and Force Index(50) from raw OHLCV
    and returns a DataFrame with the indicator columns plus an `alarms`
    column (list[ExtremeAlarm] per bar, from extremes_trigger())."""
    k, d = stochastic(df)
    fi = force_index(df)
    out = pd.DataFrame(index=df.index)
    out["stochastic_k"] = k
    out["stochastic_d"] = d
    out["force_index"] = fi
    out["alarms"] = extremes_trigger(k, d, fi)
    return out


@dataclass
class ExtremesState:
    stochastic_state: StochasticState = field(default_factory=StochasticState)
    force_index_state: ForceIndexState = field(default_factory=ForceIndexState)


def extremes_update(state: ExtremesState, bar: Bar) -> tuple[list[ExtremeAlarm], ExtremesState]:
    (k, d), new_stochastic_state = stochastic_update(state.stochastic_state, bar)
    fi, new_force_index_state = force_index_update(state.force_index_state, bar)
    alarms = evaluate_extremes(k, d, fi)
    return alarms, ExtremesState(stochastic_state=new_stochastic_state, force_index_state=new_force_index_state)

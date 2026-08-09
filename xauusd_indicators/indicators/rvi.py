"""Custom RVI(14) per the report: "SMA-based, not standard weighted
RVI." The report gives no formula beyond that phrase - the formula below
is this project's best-effort reading (SMA-based analog of the standard
RVI construction, which is normally a weighted 4-bar average of the same
ratio) and is flagged UNCONFIRMED in docs/PRD.md §6.1. If the real
formula differs, only this module needs to change - nothing else in the
codebase assumes a specific RVI formula, only that it's an oscillator
crossing ±0.20.

The "setup-then-cross through ±0.20" trigger is similarly UNCONFIRMED
(docs/PRD.md §6.2). Implemented reading: a reversal-confirmation
trigger - RVI must first reach beyond ±0.20 (the "setup"), then cross
back through that level toward zero (the "cross") to fire. A dip below
-0.20 that later crosses back up through -0.20 fires LONG (bearish
exhaustion reversing); a spike above +0.20 that crosses back down
through +0.20 fires SHORT. Landing exactly on ±0.20 counts as "beyond."
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..types import Bar, Signal

THRESHOLD = 0.20


def rvi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    numerator = (df["close"] - df["open"]).rolling(period).mean()
    denominator = (df["high"] - df["low"]).rolling(period).mean()
    return numerator / denominator


def rvi_trigger(rvi_series: pd.Series) -> pd.Series:
    """Returns a Series of Signal.LONG / Signal.SHORT / None per bar -
    None on every bar except the one where a setup-then-cross fires."""
    result = pd.Series(index=rvi_series.index, dtype=object)
    armed: str | None = None  # "below" (armed for LONG) / "above" (armed for SHORT) / None
    for i, value in enumerate(rvi_series):
        if pd.isna(value):
            result.iloc[i] = None
            continue
        if value <= -THRESHOLD:
            armed = "below"
            result.iloc[i] = None
        elif value >= THRESHOLD:
            armed = "above"
            result.iloc[i] = None
        else:
            if armed == "below":
                result.iloc[i] = Signal.LONG
                armed = None
            elif armed == "above":
                result.iloc[i] = Signal.SHORT
                armed = None
            else:
                result.iloc[i] = None
    return result


@dataclass
class RviState:
    period: int = 14
    _co_history: list[float] | None = None  # close-open per recent bar
    _hl_history: list[float] | None = None  # high-low per recent bar
    armed: str | None = None

    def __post_init__(self):
        if self._co_history is None:
            self._co_history = []
        if self._hl_history is None:
            self._hl_history = []


def rvi_update(state: RviState, bar: Bar) -> tuple[tuple[float | None, Signal | None], RviState]:
    """Returns ((rvi_value_or_None, trigger_signal_or_None), new_state)."""
    assert state._co_history is not None and state._hl_history is not None  # RviState.__post_init__ guarantees this
    co_history = state._co_history + [bar.close - bar.open]
    hl_history = state._hl_history + [bar.high - bar.low]
    if len(co_history) > state.period:
        co_history = co_history[-state.period :]
        hl_history = hl_history[-state.period :]

    rvi_value: float | None = None
    trigger: Signal | None = None
    armed = state.armed

    if len(co_history) == state.period:
        denom = sum(hl_history) / state.period
        numer = sum(co_history) / state.period
        rvi_value = numer / denom

        if rvi_value <= -THRESHOLD:
            armed = "below"
        elif rvi_value >= THRESHOLD:
            armed = "above"
        else:
            if armed == "below":
                trigger = Signal.LONG
                armed = None
            elif armed == "above":
                trigger = Signal.SHORT
                armed = None

    new_state = RviState(period=state.period, _co_history=co_history, _hl_history=hl_history, armed=armed)
    return (rvi_value, trigger), new_state

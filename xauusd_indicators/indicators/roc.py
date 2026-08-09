"""ROC(10) - 10-period Rate of Change. One of Section 6's three
momentum-agreement filters."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..types import Bar


def roc(df: pd.DataFrame, period: int = 10) -> pd.Series:
    prev = df["close"].shift(period)
    return 100 * (df["close"] - prev) / prev


@dataclass
class RocState:
    period: int = 10
    _history: list[float] = field(default_factory=list)


def roc_update(state: RocState, bar: Bar) -> tuple[float | None, RocState]:
    history = state._history + [bar.close]
    if len(history) > state.period + 1:
        history = history[-(state.period + 1) :]
    value = None
    if len(history) == state.period + 1:
        prev_close = history[0]
        value = 100 * (bar.close - prev_close) / prev_close
    return value, RocState(period=state.period, _history=history)

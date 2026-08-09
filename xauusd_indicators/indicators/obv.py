"""On-Balance-Volume and its slope. One of Section 6's three
momentum-agreement filters (slope sign must agree with trade direction).

Slope definition: OBV[t] - OBV[t - lookback] (simple difference, not a
linear regression) - the simpler of the two reasonable readings named in
docs/PRD.md §6.3. Default lookback of 10 bars (matching ROC's period) is
a proposed default pending confirmation, same section.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..types import Bar

DEFAULT_SLOPE_LOOKBACK = 10


def obv(df: pd.DataFrame) -> pd.Series:
    close_diff = df["close"].diff()
    direction = pd.Series(0, index=df.index, dtype=float)
    direction[close_diff > 0] = 1.0
    direction[close_diff < 0] = -1.0
    return (direction * df["volume"]).cumsum()


def obv_slope(df: pd.DataFrame, lookback: int = DEFAULT_SLOPE_LOOKBACK) -> pd.Series:
    series = obv(df)
    return series - series.shift(lookback)


@dataclass
class ObvState:
    lookback: int = DEFAULT_SLOPE_LOOKBACK
    prev_close: float | None = None
    running_obv: float = 0.0
    _history: list[float] = field(default_factory=list)  # OBV values, most recent last


def obv_update(state: ObvState, bar: Bar) -> tuple[tuple[float, float | None], ObvState]:
    """Returns ((obv_value, slope_or_None), new_state)."""
    if state.prev_close is None:
        direction = 0.0
    elif bar.close > state.prev_close:
        direction = 1.0
    elif bar.close < state.prev_close:
        direction = -1.0
    else:
        direction = 0.0

    new_obv = state.running_obv + direction * bar.volume
    history = state._history + [new_obv]
    if len(history) > state.lookback + 1:
        history = history[-(state.lookback + 1) :]

    slope = None
    if len(history) == state.lookback + 1:
        slope = new_obv - history[0]

    new_state = ObvState(
        lookback=state.lookback,
        prev_close=bar.close,
        running_obv=new_obv,
        _history=history,
    )
    return (new_obv, slope), new_state

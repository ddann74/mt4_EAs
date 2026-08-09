"""ATR(14) (Wilder's Average True Range) and the volatility ratio the
report's Section 2 entry condition uses (ATR(14) vs. its own 50-bar
simple moving average, required > 1.1).

Vectorized functions here deliberately use the same per-bar recurrence
as the incremental update() functions (a plain Python loop after the
initial window, not a pandas/numpy trick with no incremental
equivalent) - see docs/PRD.md §4 on why that matters for an eventual
MT4 port.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..types import Bar


def true_range(df: pd.DataFrame) -> pd.Series:
    """True range per bar. First bar has no previous close, so TR[0] is
    just high[0] - low[0] (the standard convention)."""
    prev_close = df["close"].shift(1)
    a = df["high"] - df["low"]
    b = (df["high"] - prev_close).abs()
    c = (df["low"] - prev_close).abs()
    tr = pd.concat([a, b, c], axis=1).max(axis=1)
    tr.iloc[0] = df["high"].iloc[0] - df["low"].iloc[0]
    return tr


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder ATR: the first value (at index period-1) is a simple
    average of the first `period` true ranges; every value after that
    is Wilder-smoothed: atr[t] = (atr[t-1]*(period-1) + tr[t]) / period.
    Returns NaN before index period-1 (not enough data yet)."""
    tr = true_range(df)
    result = pd.Series(index=df.index, dtype=float)
    if len(tr) < period:
        return result
    prev = tr.iloc[:period].mean()
    result.iloc[period - 1] = prev
    for i in range(period, len(tr)):
        prev = (prev * (period - 1) + tr.iloc[i]) / period
        result.iloc[i] = prev
    return result


def volatility_ratio(df: pd.DataFrame, atr_period: int = 14, avg_period: int = 50) -> pd.Series:
    """ATR(atr_period) / SMA(ATR(atr_period), avg_period). Report's
    Section 2 entry condition requires this > 1.1."""
    a = atr(df, atr_period)
    avg = a.rolling(avg_period).mean()
    return a / avg


@dataclass
class AtrState:
    period: int = 14
    prev_close: float | None = None
    _warmup: list[float] = field(default_factory=list)
    smoothed: float | None = None


def atr_update(state: AtrState, bar: Bar) -> tuple[float | None, AtrState]:
    """Incremental equivalent of atr(): consumes one new bar plus the
    previous state, returns (current ATR value or None if still
    warming up, new state)."""
    if state.prev_close is None:
        tr = bar.high - bar.low
    else:
        tr = max(bar.high - bar.low, abs(bar.high - state.prev_close), abs(bar.low - state.prev_close))

    new_state = AtrState(
        period=state.period,
        prev_close=bar.close,
        _warmup=list(state._warmup),
        smoothed=state.smoothed,
    )

    if new_state.smoothed is None:
        new_state._warmup.append(tr)
        if len(new_state._warmup) == state.period:
            new_state.smoothed = sum(new_state._warmup) / state.period
            new_state._warmup = []
        return new_state.smoothed, new_state

    new_state.smoothed = (state.smoothed * (state.period - 1) + tr) / state.period
    return new_state.smoothed, new_state


@dataclass
class VolatilityRatioState:
    atr_period: int = 14
    avg_period: int = 50
    atr_state: AtrState = field(default_factory=AtrState)
    atr_history: list[float] = field(default_factory=list)

    def __post_init__(self):
        if self.atr_state.period != self.atr_period:
            self.atr_state = AtrState(period=self.atr_period)


def volatility_ratio_update(state: VolatilityRatioState, bar: Bar) -> tuple[float | None, VolatilityRatioState]:
    atr_value, new_atr_state = atr_update(state.atr_state, bar)
    new_history = list(state.atr_history)
    ratio = None
    if atr_value is not None:
        new_history.append(atr_value)
        if len(new_history) > state.avg_period:
            new_history = new_history[-state.avg_period :]
        if len(new_history) == state.avg_period:
            avg = sum(new_history) / state.avg_period
            ratio = atr_value / avg
    new_state = VolatilityRatioState(
        atr_period=state.atr_period,
        avg_period=state.avg_period,
        atr_state=new_atr_state,
        atr_history=new_history,
    )
    return ratio, new_state

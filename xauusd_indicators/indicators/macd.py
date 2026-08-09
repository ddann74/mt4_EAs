"""MACD histogram (12/26/9 EMA-based), the report's second Section 6
momentum-agreement filter. The report doesn't override 12/26/9, so
these are used as the standard default (not an open question, unlike
RVI - see docs/PRD.md §2.6).

EMA convention: seeded with the first close (not an SMA seed), standard
exponential recursion with alpha = 2/(period+1) from bar 0 onward - this
matches pandas' `.ewm(span=period, adjust=False)` convention (and the
`ta` reference library, which uses exactly that under the hood), so the
cross-check test can compare values directly rather than fighting a
seeding-convention mismatch.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..types import Bar


def ema(series: pd.Series, period: int) -> pd.Series:
    """Public EMA, masked to match the reference library's min_periods
    display convention (the recursion still runs through the warm-up
    region internally - _ema_full() below - only the displayed value
    before index period-1 is hidden here)."""
    result = _ema_full(series, period)
    result = result.copy()
    result.iloc[: period - 1] = float("nan")
    return result


def macd_histogram(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    close = df["close"]
    macd_line = _ema_full(close, fast) - _ema_full(close, slow)
    signal_line = _ema_full(macd_line, signal)
    histogram = macd_line - signal_line
    histogram.iloc[: slow + signal - 2] = float("nan")
    return histogram


def _ema_full(series: pd.Series, period: int) -> pd.Series:
    """Unmasked EMA (recursion result at every index) - used internally
    so macd_line/signal_line don't propagate NaN into each other's
    recursion before final masking in macd_histogram()."""
    alpha = 2 / (period + 1)
    result = pd.Series(index=series.index, dtype=float)
    prev = series.iloc[0]
    result.iloc[0] = prev
    for i in range(1, len(series)):
        prev = alpha * series.iloc[i] + (1 - alpha) * prev
        result.iloc[i] = prev
    return result


@dataclass
class MacdState:
    fast: int = 12
    slow: int = 26
    signal: int = 9
    _ema_fast: float | None = None
    _ema_slow: float | None = None
    _ema_signal: float | None = None
    _count: int = 0


def macd_histogram_update(state: MacdState, bar: Bar) -> tuple[float | None, MacdState]:
    alpha_fast = 2 / (state.fast + 1)
    alpha_slow = 2 / (state.slow + 1)
    alpha_signal = 2 / (state.signal + 1)

    ema_fast = bar.close if state._ema_fast is None else alpha_fast * bar.close + (1 - alpha_fast) * state._ema_fast
    ema_slow = bar.close if state._ema_slow is None else alpha_slow * bar.close + (1 - alpha_slow) * state._ema_slow
    macd_value = ema_fast - ema_slow
    ema_signal = (
        macd_value if state._ema_signal is None else alpha_signal * macd_value + (1 - alpha_signal) * state._ema_signal
    )
    count = state._count + 1

    new_state = MacdState(
        fast=state.fast,
        slow=state.slow,
        signal=state.signal,
        _ema_fast=ema_fast,
        _ema_slow=ema_slow,
        _ema_signal=ema_signal,
        _count=count,
    )

    histogram = macd_value - ema_signal
    min_bars = state.slow + state.signal - 1
    if count < min_bars:
        return None, new_state
    return histogram, new_state

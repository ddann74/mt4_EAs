"""Force Index - user-added alarm indicator, NOT part of the source
XAUUSD Strategy Analysis report (see docs/PRD.md §10). Elder's standard
definition: raw Force Index = (close[t] - close[t-1]) * volume[t],
smoothed with an EMA. The user specified period 50.

The raw series has no value on the very first bar (no previous close to
diff against) - unlike macd.py's EMA input (always-present close
prices), this EMA's input starts life NaN at index 0. Reusing macd.py's
_ema_full() as-is would seed the whole recursion on that NaN and poison
every subsequent value (alpha*x + (1-alpha)*NaN is NaN, forever) - the
same category of bug adx.py's _wilder_smooth already had to fix for a
NaN-prefixed DX input. _ema_seeded_at_first_valid() below is this
module's own fix for the same problem, applied to force index's raw
series specifically.

Cross-checked against `ta.volume.ForceIndexIndicator` (see
tests/test_force_index.py) - exact match, but note `ta`'s masking
convention for this specific indicator class hides one bar more than
macd.py's own ema() helper does for MACD (first valid value at index
`period`, not `period - 1`). This module matches `ta`'s convention
exactly (not macd.py's) specifically so the cross-check test can compare
values directly rather than fighting a masking-convention mismatch -
same reasoning macd.py's own docstring gives for its own masking choice.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..types import Bar


def _raw_force_index(df: pd.DataFrame) -> pd.Series:
    return df["close"].diff() * df["volume"]


def _ema_seeded_at_first_valid(series: pd.Series, period: int) -> pd.Series:
    alpha = 2 / (period + 1)
    result = pd.Series(index=series.index, dtype=float)
    first_valid = series.first_valid_index()
    if first_valid is None:
        return result
    start = series.index.get_loc(first_valid)
    prev = series.iloc[start]
    result.iloc[start] = prev
    for i in range(start + 1, len(series)):
        prev = alpha * series.iloc[i] + (1 - alpha) * prev
        result.iloc[i] = prev
    return result


def force_index(df: pd.DataFrame, period: int = 50) -> pd.Series:
    raw = _raw_force_index(df)
    smoothed = _ema_seeded_at_first_valid(raw, period)
    result = smoothed.copy()
    # Matches ta.volume.ForceIndexIndicator's own masking convention exactly
    # (verified empirically - see tests/test_force_index.py) - first `period`
    # positions hidden, not `period - 1` the way macd.py's ema() masks.
    result.iloc[:period] = float("nan")
    return result


@dataclass
class ForceIndexState:
    period: int = 50
    prev_close: float | None = None
    smoothed: float | None = None
    _count: int = 0  # bars where a raw value existed (i.e. bars after the first)


def force_index_update(state: ForceIndexState, bar: Bar) -> tuple[float | None, ForceIndexState]:
    """Returns (force_index_or_None, new_state). Mirrors force_index()'s
    masking: no value returned until `period` bars have had a real raw
    reading (i.e. `period + 1` bars total have been seen, since the very
    first bar has no previous close)."""
    alpha = 2 / (state.period + 1)

    if state.prev_close is None:
        # First bar ever: no raw reading possible, nothing to seed with yet.
        return None, ForceIndexState(period=state.period, prev_close=bar.close, smoothed=None, _count=0)

    raw = (bar.close - state.prev_close) * bar.volume
    smoothed = raw if state.smoothed is None else alpha * raw + (1 - alpha) * state.smoothed
    count = state._count + 1

    new_state = ForceIndexState(period=state.period, prev_close=bar.close, smoothed=smoothed, _count=count)
    value = smoothed if count >= state.period else None
    return value, new_state

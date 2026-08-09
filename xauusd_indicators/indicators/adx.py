"""ADX(14) (Wilder's Average Directional Index). Report's Section 2
entry condition requires ADX(14) > 30.

Standard Wilder recipe: +DM/-DM/TR are each Wilder-smoothed (same
recurrence as atr.py's ATR - first value is a simple average of the
first `period` raw values, then smoothed[t] = (smoothed[t-1]*(period-1)
+ raw[t]) / period). +DI/-DI are the smoothed DM divided by the smoothed
TR; DX is the normalized absolute difference between them; ADX is DX
itself Wilder-smoothed. Using the average form (vs. Wilder's original
sum form) for TR/DM smoothing doesn't change +DI/-DI, since both are
ratios of two identically-scaled smoothed quantities.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..types import Bar
from .atr import AtrState, atr_update, true_range


def _directional_moves(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move
    plus_dm.iloc[0] = 0.0
    minus_dm.iloc[0] = 0.0
    return plus_dm, minus_dm


def _wilder_smooth(raw: pd.Series, period: int) -> pd.Series:
    """Wilder-smooths `raw`, correctly handling a NaN-prefixed input
    (raw's own warmup region, e.g. DX before smoothed_tr/DM exist).

    BUG THIS FIXES: pandas' Series.mean() silently skips NaN by
    default, so a naive `raw.iloc[:period].mean()` seed - applied
    directly to a NaN-prefixed series like DX - averages whatever
    handful of non-NaN values happen to fall in that absolute window,
    not `period` real values. Caught by
    tests/test_adx.py::test_adx_incremental_matches_vectorized, whose
    incremental implementation correctly waits for `period` genuine
    values before seeding; this function now does the same by finding
    the first valid index explicitly rather than trusting positional
    slicing + skipna mean.
    """
    result = pd.Series(index=raw.index, dtype=float)
    first_valid = raw.first_valid_index()
    if first_valid is None:
        return result
    start = raw.index.get_loc(first_valid)
    if len(raw) - start < period:
        return result
    prev = raw.iloc[start : start + period].mean()
    result.iloc[start + period - 1] = prev
    for i in range(start + period, len(raw)):
        prev = (prev * (period - 1) + raw.iloc[i]) / period
        result.iloc[i] = prev
    return result


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = true_range(df)
    plus_dm, minus_dm = _directional_moves(df)

    smoothed_tr = _wilder_smooth(tr, period)
    smoothed_plus_dm = _wilder_smooth(plus_dm, period)
    smoothed_minus_dm = _wilder_smooth(minus_dm, period)

    plus_di = 100 * smoothed_plus_dm / smoothed_tr
    minus_di = 100 * smoothed_minus_dm / smoothed_tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)

    return _wilder_smooth(dx, period)


@dataclass
class AdxState:
    period: int = 14
    prev_high: float | None = None
    prev_low: float | None = None
    tr_state: AtrState = field(default_factory=AtrState)
    _dm_warmup_plus: list[float] = field(default_factory=list)
    _dm_warmup_minus: list[float] = field(default_factory=list)
    smoothed_plus_dm: float | None = None
    smoothed_minus_dm: float | None = None
    _dx_warmup: list[float] = field(default_factory=list)
    smoothed_dx: float | None = None

    def __post_init__(self):
        if self.tr_state.period != self.period:
            self.tr_state = AtrState(period=self.period)


def adx_update(state: AdxState, bar: Bar) -> tuple[float | None, AdxState]:
    atr_value, new_tr_state = atr_update(state.tr_state, bar)

    if state.prev_high is None:
        plus_dm = 0.0
        minus_dm = 0.0
    else:
        up_move = bar.high - state.prev_high
        down_move = state.prev_low - bar.low
        plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0

    new_state = AdxState(
        period=state.period,
        prev_high=bar.high,
        prev_low=bar.low,
        tr_state=new_tr_state,
        _dm_warmup_plus=list(state._dm_warmup_plus),
        _dm_warmup_minus=list(state._dm_warmup_minus),
        smoothed_plus_dm=state.smoothed_plus_dm,
        smoothed_minus_dm=state.smoothed_minus_dm,
        _dx_warmup=list(state._dx_warmup),
        smoothed_dx=state.smoothed_dx,
    )

    if new_state.smoothed_plus_dm is None:
        new_state._dm_warmup_plus.append(plus_dm)
        new_state._dm_warmup_minus.append(minus_dm)
        if len(new_state._dm_warmup_plus) == state.period:
            new_state.smoothed_plus_dm = sum(new_state._dm_warmup_plus) / state.period
            new_state.smoothed_minus_dm = sum(new_state._dm_warmup_minus) / state.period
            new_state._dm_warmup_plus = []
            new_state._dm_warmup_minus = []
    else:
        new_state.smoothed_plus_dm = (state.smoothed_plus_dm * (state.period - 1) + plus_dm) / state.period
        new_state.smoothed_minus_dm = (state.smoothed_minus_dm * (state.period - 1) + minus_dm) / state.period

    if atr_value is None or new_state.smoothed_plus_dm is None:
        return None, new_state

    plus_di = 100 * new_state.smoothed_plus_dm / atr_value
    minus_di = 100 * new_state.smoothed_minus_dm / atr_value
    denom = plus_di + minus_di
    dx = 0.0 if denom == 0 else 100 * abs(plus_di - minus_di) / denom

    if new_state.smoothed_dx is None:
        new_state._dx_warmup.append(dx)
        if len(new_state._dx_warmup) == state.period:
            new_state.smoothed_dx = sum(new_state._dx_warmup) / state.period
            new_state._dx_warmup = []
        return new_state.smoothed_dx, new_state

    new_state.smoothed_dx = (state.smoothed_dx * (state.period - 1) + dx) / state.period
    return new_state.smoothed_dx, new_state

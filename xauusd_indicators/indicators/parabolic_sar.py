"""Parabolic SAR (Wellesley Wilder), the report's Section 6a filter -
trend direction must agree with the trade direction. Step 0.02, max
0.20 - the report doesn't override these, so they're used as standard
defaults (not an open question).

Initialization follows the common convention (also used by the `ta`
reference library, which this module's tests cross-check against):
assume an initial uptrend, seed the extreme point from bar 0's high,
and start real SAR computation at bar index 2 (the first two bars have
no defined SAR value - reported as None/NaN rather than a guess).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..types import Bar, Signal

DEFAULT_STEP = 0.02
DEFAULT_MAX_STEP = 0.20


def parabolic_sar(df: pd.DataFrame, step: float = DEFAULT_STEP, max_step: float = DEFAULT_MAX_STEP) -> pd.Series:
    """Returns the SAR price level per bar (NaN for bars 0-1)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    psar = close.copy()
    up_trend = True
    af = step
    up_trend_high = high.iloc[0]
    down_trend_low = low.iloc[0]

    for i in range(2, len(close)):
        reversal = False
        max_high = high.iloc[i]
        min_low = low.iloc[i]

        if up_trend:
            psar.iloc[i] = psar.iloc[i - 1] + af * (up_trend_high - psar.iloc[i - 1])
            if min_low < psar.iloc[i]:
                reversal = True
                psar.iloc[i] = up_trend_high
                down_trend_low = min_low
                af = step
            else:
                if max_high > up_trend_high:
                    up_trend_high = max_high
                    af = min(af + step, max_step)
                low1 = low.iloc[i - 1]
                low2 = low.iloc[i - 2]
                if low2 < psar.iloc[i]:
                    psar.iloc[i] = low2
                elif low1 < psar.iloc[i]:
                    psar.iloc[i] = low1
        else:
            psar.iloc[i] = psar.iloc[i - 1] - af * (psar.iloc[i - 1] - down_trend_low)
            if max_high > psar.iloc[i]:
                reversal = True
                psar.iloc[i] = down_trend_low
                up_trend_high = max_high
                af = step
            else:
                if min_low < down_trend_low:
                    down_trend_low = min_low
                    af = min(af + step, max_step)
                high1 = high.iloc[i - 1]
                high2 = high.iloc[i - 2]
                if high2 > psar.iloc[i]:
                    psar.iloc[i] = high2
                elif high1 > psar.iloc[i]:
                    psar.iloc[i] = high1

        up_trend = up_trend != reversal

    psar.iloc[0] = float("nan")
    psar.iloc[1] = float("nan")
    return psar


def parabolic_sar_direction(df: pd.DataFrame, step: float = DEFAULT_STEP, max_step: float = DEFAULT_MAX_STEP) -> pd.Series:
    """LONG while price is above SAR (uptrend), SHORT while below."""
    sar = parabolic_sar(df, step, max_step)
    direction = pd.Series(index=df.index, dtype=object)
    for i in range(len(df)):
        if pd.isna(sar.iloc[i]):
            direction.iloc[i] = None
        else:
            direction.iloc[i] = Signal.LONG if df["close"].iloc[i] > sar.iloc[i] else Signal.SHORT
    return direction


@dataclass
class ParabolicSarState:
    step: float = DEFAULT_STEP
    max_step: float = DEFAULT_MAX_STEP
    up_trend: bool = True
    af: float | None = None
    up_trend_high: float | None = None
    down_trend_low: float | None = None
    prev_psar: float | None = None
    _bar_history: list[Bar] = field(default_factory=list)  # keeps last 2 bars


def parabolic_sar_update(state: ParabolicSarState, bar: Bar) -> tuple[float | None, ParabolicSarState]:
    """state._bar_history holds up to the 2 bars seen BEFORE this call
    (not including the current one) - the vectorized loop's per-bar
    formula needs both low[i-1]/low[i-2] (or high equivalents), so a
    single previous bar isn't enough history to reproduce it."""
    history = state._bar_history

    if len(history) == 0:
        # This is bar 0: seed extremes, no SAR value yet.
        new_state = ParabolicSarState(
            step=state.step,
            max_step=state.max_step,
            up_trend=True,
            af=state.step,
            up_trend_high=bar.high,
            down_trend_low=bar.low,
            prev_psar=None,
            _bar_history=[bar],
        )
        return None, new_state

    if len(history) == 1:
        # This is bar 1: matches vectorized parabolic_sar()'s
        # psar.iloc[1] = close.iloc[1] seed - still no real SAR value.
        new_state = ParabolicSarState(
            step=state.step,
            max_step=state.max_step,
            up_trend=True,
            af=state.step,
            up_trend_high=state.up_trend_high,
            down_trend_low=state.down_trend_low,
            prev_psar=bar.close,
            _bar_history=[history[0], bar],
        )
        return None, new_state

    # Bar index >= 2: history == [bar_{i-2}, bar_{i-1}]. By this point
    # af/up_trend_high/down_trend_low/prev_psar were all seeded by the
    # len(history) < 2 branch above on a prior call, so none of them
    # can still be None - asserted here so the arithmetic below is
    # type-checked, not just trusted.
    prev_prev_bar, prev_bar = history[0], history[1]
    up_trend = state.up_trend
    assert state.af is not None
    assert state.up_trend_high is not None
    assert state.down_trend_low is not None
    assert state.prev_psar is not None
    af = state.af
    up_trend_high = state.up_trend_high
    down_trend_low = state.down_trend_low
    prev_psar = state.prev_psar

    reversal = False
    if up_trend:
        psar = prev_psar + af * (up_trend_high - prev_psar)
        if bar.low < psar:
            reversal = True
            psar = up_trend_high
            down_trend_low = bar.low
            af = state.step
        else:
            if bar.high > up_trend_high:
                up_trend_high = bar.high
                af = min(af + state.step, state.max_step)
            if prev_prev_bar.low < psar:
                psar = prev_prev_bar.low
            elif prev_bar.low < psar:
                psar = prev_bar.low
    else:
        psar = prev_psar - af * (prev_psar - down_trend_low)
        if bar.high > psar:
            reversal = True
            psar = down_trend_low
            up_trend_high = bar.high
            af = state.step
        else:
            if bar.low < down_trend_low:
                down_trend_low = bar.low
                af = min(af + state.step, state.max_step)
            if prev_prev_bar.high > psar:
                psar = prev_prev_bar.high
            elif prev_bar.high > psar:
                psar = prev_bar.high

    new_up_trend = up_trend != reversal

    new_state = ParabolicSarState(
        step=state.step,
        max_step=state.max_step,
        up_trend=new_up_trend,
        af=af,
        up_trend_high=up_trend_high,
        down_trend_low=down_trend_low,
        prev_psar=psar,
        _bar_history=[prev_bar, bar],
    )
    return psar, new_state

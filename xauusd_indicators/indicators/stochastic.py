"""Slow Stochastic Oscillator - user-added alarm indicator, NOT part of
the source XAUUSD Strategy Analysis report (see docs/PRD.md §10; every
other indicator in this package is report-derived, this one isn't).

Parameterized (%K period, %K slowing, %D period) - the same three-number
order MT4's own built-in iStochastic()/Stochastic Oscillator indicator
uses. The user specified 50,10,10. Unlike RVI's report-derived formula
(§6.1), this isn't an open question: "50,10,10" is unambiguous MT4-style
notation for a well-known, standard indicator, not an inferred reading of
ambiguous prose.

Formula (standard "Slow Stochastic"):
  raw %K   = 100 * (close - lowest_low(%K period)) / (highest_high(%K period) - lowest_low(%K period))
  slow %K  = SMA(raw %K, %K slowing)   <- this is what MT4 actually plots as "%K"
  %D       = SMA(slow %K, %D period)

`stochastic()` below returns (slow %K, %D) - the two lines an MT4 chart
would show, not the unsmoothed raw %K (which this module never exposes
directly, matching MT4's own display convention).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..types import Bar


def stochastic(df: pd.DataFrame, k_period: int = 50, k_slowing: int = 10, d_period: int = 10) -> tuple[pd.Series, pd.Series]:
    lowest_low = df["low"].rolling(window=k_period).min()
    highest_high = df["high"].rolling(window=k_period).max()
    raw_range = highest_high - lowest_low
    raw_k = 100 * (df["close"] - lowest_low) / raw_range
    slow_k = raw_k.rolling(window=k_slowing).mean()
    d = slow_k.rolling(window=d_period).mean()
    return slow_k, d


@dataclass
class StochasticState:
    k_period: int = 50
    k_slowing: int = 10
    d_period: int = 10
    _highs: list[float] = field(default_factory=list)
    _lows: list[float] = field(default_factory=list)
    _raw_k_history: list[float] = field(default_factory=list)
    _slow_k_history: list[float] = field(default_factory=list)


def stochastic_update(state: StochasticState, bar: Bar) -> tuple[tuple[float | None, float | None], StochasticState]:
    """Returns ((slow_k_or_None, d_or_None), new_state).

    Known, narrow vectorized/incremental divergence: a completely flat
    %K-period window (raw_range == 0) is guarded to 50.0 here because a
    literal ZeroDivisionError would crash a pure-Python float division -
    numpy/pandas don't have that problem (a zero-denominator division
    there silently produces inf/nan instead), so stochastic() above has
    no equivalent guard. Only matters on genuinely flat synthetic/real
    data, which none of this project's fixtures produce over a 50-bar
    window - not expected to be hit in tests/test_stochastic.py's
    incremental-vs-vectorized comparison."""
    highs = (state._highs + [bar.high])[-state.k_period :]
    lows = (state._lows + [bar.low])[-state.k_period :]

    raw_k_history = list(state._raw_k_history)
    slow_k_history = list(state._slow_k_history)

    raw_k: float | None = None
    if len(highs) == state.k_period:
        highest_high = max(highs)
        lowest_low = min(lows)
        raw_range = highest_high - lowest_low
        # A completely flat window (every high/low identical) would divide by
        # zero - treat it as the midpoint (50), the same "no information"
        # convention most stochastic implementations use rather than NaN/crash.
        raw_k = 50.0 if raw_range == 0 else 100 * (bar.close - lowest_low) / raw_range
        raw_k_history.append(raw_k)
        if len(raw_k_history) > state.k_slowing:
            raw_k_history = raw_k_history[-state.k_slowing :]

    slow_k: float | None = None
    if raw_k is not None and len(raw_k_history) == state.k_slowing:
        slow_k = sum(raw_k_history) / state.k_slowing
        slow_k_history.append(slow_k)
        if len(slow_k_history) > state.d_period:
            slow_k_history = slow_k_history[-state.d_period :]

    d: float | None = None
    if slow_k is not None and len(slow_k_history) == state.d_period:
        d = sum(slow_k_history) / state.d_period

    new_state = StochasticState(
        k_period=state.k_period,
        k_slowing=state.k_slowing,
        d_period=state.d_period,
        _highs=highs,
        _lows=lows,
        _raw_k_history=raw_k_history,
        _slow_k_history=slow_k_history,
    )
    return (slow_k, d), new_state

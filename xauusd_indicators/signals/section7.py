"""Section 7 (fast-exit): same entry as Section 2. Exit: fixed $15
profit target OR 30-bar (30-minute) time cutoff "instead of a trailing
stop."

UNCONFIRMED interpretation (docs/PRD.md §6.5): the report's exact
sentence only names the TRAILING stop as being replaced - it's silent
on the hard stop and RVI-reversal exits. This module's chosen reading:
hard stop and RVI-reversal stay active (unmentioned, so presumed
unchanged), the trailing stop is dropped, and the $15 target / 30-bar
cutoff are added as two more OR'd exit conditions. If the intended
reading is "replace ALL of Section 2's exit, not just the trailing
stop," only PROFIT_TARGET_ONLY_EXIT below needs to change.

UNCONFIRMED PRICE/DOLLAR ASSUMPTION: the report's $15 figure is a dollar
PnL target, but this project doesn't model lot sizing or contract value
(docs/PRD.md §0/§3 explicitly scope that out). Converting $15 into a
price-distance requires ONE assumption: standard retail XAUUSD contract
size is 100oz/lot, so the report's stated 0.01 lot is 1oz notional,
meaning a $1 price move = $1 PnL. That is a standard, widely-used
broker convention (not an arbitrary guess), used here ONLY to evaluate
this one exit trigger as a price distance - not a general PnL/lot-sizing
system. NOTIONAL_OZ_PER_POSITION below is that one assumption, isolated
so it's a one-line change if the user's actual broker differs.
"""
from __future__ import annotations

import pandas as pd

from ..types import PositionState, Signal
from .section2 import HARD_STOP_ATR_MULTIPLE, entry_signal as section2_entry_signal  # noqa: F401 - re-exported

PROFIT_TARGET_USD = 15.0
TIME_CUTOFF_BARS = 30
NOTIONAL_OZ_PER_POSITION = 1.0  # UNCONFIRMED assumption - see module docstring

entry_signal = section2_entry_signal


def exit_fired(
    df: pd.DataFrame,
    position: PositionState,
    current_bar_index: int,
    atr_at_entry: float,
    rvi_triggers: pd.Series,
) -> bool:
    entry_idx = position.entry_bar_index
    if current_bar_index < entry_idx:
        raise ValueError("current_bar_index must be at or after the position's entry_bar_index")

    is_long = position.direction == Signal.LONG

    # Hard stop (unchanged from Section 2 - see module docstring).
    if is_long:
        hard_stop_level = position.entry_price - HARD_STOP_ATR_MULTIPLE * atr_at_entry
        if df["low"].iloc[current_bar_index] <= hard_stop_level:
            return True
    else:
        hard_stop_level = position.entry_price + HARD_STOP_ATR_MULTIPLE * atr_at_entry
        if df["high"].iloc[current_bar_index] >= hard_stop_level:
            return True

    # RVI reversal (unchanged from Section 2 - see module docstring).
    opposite = Signal.SHORT if is_long else Signal.LONG
    if current_bar_index > entry_idx and rvi_triggers.iloc[current_bar_index] == opposite:
        return True

    # $15 profit target.
    price_target_distance = PROFIT_TARGET_USD / NOTIONAL_OZ_PER_POSITION
    if is_long:
        target_price = position.entry_price + price_target_distance
        if df["high"].iloc[current_bar_index] >= target_price:
            return True
    else:
        target_price = position.entry_price - price_target_distance
        if df["low"].iloc[current_bar_index] <= target_price:
            return True

    # 30-bar time cutoff.
    if current_bar_index - entry_idx >= TIME_CUTOFF_BARS:
        return True

    return False

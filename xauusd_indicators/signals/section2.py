"""Section 2 (core/default): RVI setup-then-cross AND ADX(14) > 30 AND
volatility ratio > 1.1 for entry; hard stop / trailing stop / RVI
reversal for exit.

UNCONFIRMED PLACEHOLDER PARAMETERS (docs/PRD.md §6.4): the report names
"hard stop / trailing stop / RVI reversal" as Section 2's exit but gives
no numeric stop distances anywhere in the source text, and the user
explicitly asked to proceed with "whatever the report says" - which, on
this point, is nothing more specific than that phrase. Per the earlier
agreement (reasonable placeholders, clearly flagged, structured so real
numbers are a one-line change later), this module uses ATR-multiple
stop distances - a standard, common convention for this kind of system,
not a guess at the report's actual intended numbers:

- HARD_STOP_ATR_MULTIPLE = 2.0 (stop at entry_price -/+ 2x the ATR(14)
  measured at entry)
- TRAIL_ATR_MULTIPLE = 1.5 (trail behind the highest-high/lowest-low
  seen since entry, by 1.5x that same entry-time ATR)

Both constants are placeholders pending real numbers from the user.
"""
from __future__ import annotations

import pandas as pd

from ..indicators.adx import adx
from ..indicators.atr import volatility_ratio
from ..indicators.rvi import rvi, rvi_trigger
from ..types import PositionState, Signal

ADX_THRESHOLD = 30
VOLATILITY_RATIO_THRESHOLD = 1.1

HARD_STOP_ATR_MULTIPLE = 2.0  # UNCONFIRMED placeholder - see module docstring
TRAIL_ATR_MULTIPLE = 1.5  # UNCONFIRMED placeholder - see module docstring


def entry_signal(
    df: pd.DataFrame,
    *,
    rvi_triggers: pd.Series | None = None,
    adx_series: pd.Series | None = None,
    vol_ratio_series: pd.Series | None = None,
) -> pd.Series:
    """Signal.LONG / Signal.SHORT / None per bar. None everywhere except
    a bar where the RVI setup-then-cross fires AND ADX(14) > 30 AND the
    volatility ratio > 1.1 all hold simultaneously.

    The three keyword overrides let tests inject controlled indicator
    values directly (composition-logic branch coverage) without needing
    to hand-engineer raw OHLCV sequences that happen to produce those
    exact indicator values - each indicator's own correctness is already
    covered by its own test module. Left as None (the normal calling
    convention), all three are computed from `df` as usual.
    """
    triggers = rvi_triggers if rvi_triggers is not None else rvi_trigger(rvi(df))
    adx_series = adx_series if adx_series is not None else adx(df)
    vol_ratio_series = vol_ratio_series if vol_ratio_series is not None else volatility_ratio(df)

    result = pd.Series(index=df.index, dtype=object)
    for i in range(len(df)):
        trigger = triggers.iloc[i]
        if trigger is None:
            result.iloc[i] = None
            continue
        if pd.isna(adx_series.iloc[i]) or pd.isna(vol_ratio_series.iloc[i]):
            result.iloc[i] = None
            continue
        if adx_series.iloc[i] > ADX_THRESHOLD and vol_ratio_series.iloc[i] > VOLATILITY_RATIO_THRESHOLD:
            result.iloc[i] = trigger
        else:
            result.iloc[i] = None
    return result


def exit_fired(
    df: pd.DataFrame,
    position: PositionState,
    current_bar_index: int,
    atr_at_entry: float,
    rvi_triggers: pd.Series,
) -> bool:
    """Pure boolean: does Section 2's exit condition fire at
    current_bar_index for a hypothetical open `position`? Does not
    track or mutate any position state (docs/PRD.md §3/§0) - the caller
    owns that.

    Checks all three of hard stop / trailing stop / RVI reversal
    (matching the report's "hard stop / trailing stop / RVI reversal"
    exit, joined with OR - any one firing closes the position). See
    module docstring for the placeholder ATR-multiple stop parameters.
    """
    entry_idx = position.entry_bar_index
    if current_bar_index < entry_idx:
        raise ValueError("current_bar_index must be at or after the position's entry_bar_index")

    is_long = position.direction == Signal.LONG

    if is_long:
        hard_stop_level = position.entry_price - HARD_STOP_ATR_MULTIPLE * atr_at_entry
        if df["low"].iloc[current_bar_index] <= hard_stop_level:
            return True
    else:
        hard_stop_level = position.entry_price + HARD_STOP_ATR_MULTIPLE * atr_at_entry
        if df["high"].iloc[current_bar_index] >= hard_stop_level:
            return True

    window_highs = df["high"].iloc[entry_idx : current_bar_index + 1]
    window_lows = df["low"].iloc[entry_idx : current_bar_index + 1]
    if is_long:
        extreme = window_highs.max()
        trailing_level = extreme - TRAIL_ATR_MULTIPLE * atr_at_entry
        if df["low"].iloc[current_bar_index] <= trailing_level:
            return True
    else:
        extreme = window_lows.min()
        trailing_level = extreme + TRAIL_ATR_MULTIPLE * atr_at_entry
        if df["high"].iloc[current_bar_index] >= trailing_level:
            return True

    opposite = Signal.SHORT if is_long else Signal.LONG
    if current_bar_index > entry_idx and rvi_triggers.iloc[current_bar_index] == opposite:
        return True

    return False

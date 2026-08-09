"""Shared types for indicators and signals.

Bar is a plain NamedTuple (not a pandas row) so incremental/update()
functions - the ones meant to have a clear MT4/MQL4 port path, per
docs/PRD.md §4 - don't depend on pandas at all.
"""
from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class Bar(NamedTuple):
    open: float
    high: float
    low: float
    close: float
    volume: float


class Signal(Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class PositionState(NamedTuple):
    """A hypothetical open position, for exit-trigger evaluation only -
    this project does not track real positions/PnL (PRD §0)."""

    direction: Signal
    entry_price: float
    entry_bar_index: int

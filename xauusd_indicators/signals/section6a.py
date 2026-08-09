"""Section 6a: Section 2's entry conditions, plus Parabolic SAR trend
direction must agree with the trigger's direction. Simplest alternative
to Section 6 (one indicator instead of three); report notes combining
both adds nothing further, so this project keeps them as separate,
independent entry functions rather than one configurable one. Exit is
the same as Section 2, same reasoning as section6.py.
"""
from __future__ import annotations

import pandas as pd

from ..indicators.parabolic_sar import parabolic_sar_direction
from .section2 import entry_signal as section2_entry_signal
from .section2 import exit_fired  # noqa: F401 - re-exported: Section 6a shares Section 2's exit unchanged


def entry_signal(
    df: pd.DataFrame,
    *,
    base_signal: pd.Series | None = None,
    sar_direction: pd.Series | None = None,
) -> pd.Series:
    """See section2.entry_signal's docstring for why these overrides
    exist."""
    base = base_signal if base_signal is not None else section2_entry_signal(df)
    sar_direction = sar_direction if sar_direction is not None else parabolic_sar_direction(df)

    result = pd.Series(index=df.index, dtype=object)
    for i in range(len(df)):
        candidate = base.iloc[i]
        if candidate is None or sar_direction.iloc[i] is None:
            result.iloc[i] = None
            continue
        result.iloc[i] = candidate if sar_direction.iloc[i] == candidate else None
    return result

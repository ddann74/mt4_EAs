"""Synthetic OHLCV fixtures.

No real XAUUSD M1 data is reachable from this build environment (checked
live while writing docs/PRD.md - outbound requests to Yahoo Finance,
Dukascopy, and a generic FX API all failed to connect). Every test in
this project therefore validates against hand-computed or
library-cross-checked synthetic data, never real market data - see
docs/PRD.md §5 for the honest scope of what this proves and doesn't.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from xauusd_indicators.types import Bar


def tiny_uptrend_df() -> pd.DataFrame:
    """20 bars, hand-designed so every OHLC value is a simple round
    number - small enough that ATR/ADX/RVI expected values can be
    worked out by hand in the tests that use this fixture. Strictly
    increasing highs/lows/closes (a clean uptrend) with a small
    fixed daily range, so directional-movement math has an obvious,
    checkable answer."""
    n = 30
    base = 100.0
    rows = []
    for i in range(n):
        o = base + i
        c = o + 0.5
        h = c + 0.3
        low = o - 0.2
        v = 1000 + i
        rows.append({"open": o, "high": h, "low": low, "close": c, "volume": v})
    return pd.DataFrame(rows)


def synthetic_series_df(n: int = 300, seed: int = 42) -> pd.DataFrame:
    """A longer, randomized-but-reproducible OHLCV series (geometric
    random walk with occasional regime shifts) - used for
    library-cross-check tests (ta.trend/ta.volatility) and for
    signal-composition tests that need a realistic mix of trending and
    choppy conditions, not real market data."""
    rng = np.random.default_rng(seed)
    price = 2000.0
    rows = []
    drift = 0.0
    for i in range(n):
        if i % 60 == 0:
            drift = rng.choice([-0.03, 0.03, 0.0])
        change = drift + rng.normal(0, 0.15)
        o = price
        c = max(0.01, o + change)
        h = max(o, c) + abs(rng.normal(0, 0.08))
        low = min(o, c) - abs(rng.normal(0, 0.08))
        v = float(rng.integers(50, 500))
        rows.append({"open": o, "high": h, "low": low, "close": c, "volume": v})
        price = c
    return pd.DataFrame(rows)


def df_to_bars(df: pd.DataFrame) -> list[Bar]:
    return [Bar(open=r.open, high=r.high, low=r.low, close=r.close, volume=r.volume) for r in df.itertuples()]

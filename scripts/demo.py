"""Runs the full pipeline (all indicators + all 4 signal variants) end
to end and prints a summary, so you can see it actually working without
writing any code yourself.

Usage:
    python scripts/demo.py                       # synthetic data (clearly labeled)
    python scripts/demo.py --csv path/to/data.csv # real OHLCV data you supply

CSV format: columns open,high,low,close,volume, one row per bar (no
timestamp column required). This is the format an MT4 terminal's
"Export" on a chart typically produces (after stripping the
date/time columns) - this script does not fetch or validate that the
data is genuinely XAUUSD M1, only that it has the right shape.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")

from xauusd_indicators.pipeline import Variant, compute_all_indicators, entry_signal
from xauusd_indicators.types import Signal


def synthetic_ohlcv(n: int = 500, seed: int = 7) -> pd.DataFrame:
    """Same style of generator as tests/fixtures.py's
    synthetic_series_df, duplicated (not imported) so this script has
    no dependency on the test suite - a reproducible, randomized-but-
    seeded geometric random walk with occasional regime shifts. NOT
    real market data."""
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", help="Path to a CSV with open,high,low,close,volume columns")
    parser.add_argument("--n", type=int, default=500, help="Number of synthetic bars if --csv is not given")
    args = parser.parse_args()

    if args.csv:
        df = pd.read_csv(args.csv)
        missing = {"open", "high", "low", "close", "volume"} - set(df.columns)
        if missing:
            print(f"ERROR: CSV is missing required column(s): {sorted(missing)}", file=sys.stderr)
            sys.exit(1)
        print(f"Loaded {len(df)} bars from {args.csv} (real data - caller-supplied).")
    else:
        df = synthetic_ohlcv(n=args.n)
        print(f"Generated {len(df)} SYNTHETIC bars (seeded random walk) - NOT real market data.")
        print("Pass --csv path/to/data.csv to run against real OHLCV data instead.\n")

    enriched = compute_all_indicators(df)
    print("\nLast 5 bars with all indicators:")
    cols = ["close", "atr", "volatility_ratio", "adx", "rvi", "roc", "obv_slope", "macd_histogram", "parabolic_sar"]
    with pd.option_context("display.width", 160, "display.max_columns", None):
        print(enriched[cols].tail(5).round(4))

    print("\nEntry signal counts per report variant:")
    for variant in Variant:
        signals = entry_signal(df, variant)
        long_count = sum(1 for s in signals if s == Signal.LONG)
        short_count = sum(1 for s in signals if s == Signal.SHORT)
        print(f"  {variant.value:12s} LONG={long_count:3d}  SHORT={short_count:3d}")

    print(
        "\nReminder: these are entry signals only, computed on the data above. "
        "This script does not simulate P&L, apply position sizing, or claim any "
        "particular signal count is 'good' - see docs/PRD.md for full scope."
    )


if __name__ == "__main__":
    main()

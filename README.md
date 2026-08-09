# XAUUSD Indicator & Signal Library

Implements the six technical indicators and four entry/exit signal
variants described in a source "XAUUSD Strategy Analysis" report
(`docs/source_report_extract.txt` — verbatim extracted PDF text), plus
the correctness tests that prove the math is right.

**What this project proves, and what it doesn't:** every indicator and
signal-composition function here is verified against hand-derived
arithmetic and/or an independent reference library (`ta`) on synthetic
data. **It has also now been run against 139,978 bars of real XAUUSD M1
data covering the report's exact window (Dec 15 2025 – May 8 2026)** —
no crashes, no unexpected NaN/infinities, every warmup length matched
its own documentation exactly, ADX stayed within [0,100] throughout —
see `PROGRESS.md` for full findings. That proves the formulas behave
correctly at real-world scale; it does **not** validate profitability,
ruin probability, or reproduce anything from the source report's own
return/ruin-probability numbers (+21.48%/month, 2.0% ruin, etc.) — that
would require the report's own backtest + bootstrap pipeline, which is
explicitly out of scope (`docs/PRD.md` §0). The real dataset itself
isn't committed here (`data/*.csv` is gitignored — its licensing isn't
this project's to decide); `tests/test_real_data_smoke.py` documents
exactly how to re-run the validation locally.

Full requirements, scope, and the 5 UNCONFIRMED interpretations this
project had to make where the source report was ambiguous: see
`docs/PRD.md`. Current build status: `PROGRESS.md`.

## What's implemented

| Indicator | Vectorized | Incremental | Verified against |
|---|---|---|---|
| ATR(14) / volatility ratio | `indicators/atr.py` | ✓ | hand-computed + `ta.volatility.AverageTrueRange` (exact) |
| ADX(14) | `indicators/adx.py` | ✓ | hand-computed (exact); `ta.trend.ADXIndicator` used only as a sanity check (it has a documented off-by-one quirk) |
| Custom RVI(14) + setup-then-cross trigger | `indicators/rvi.py` | ✓ | hand-computed + engineered trigger sequences — **formula and trigger logic are both UNCONFIRMED inferences, see docs/PRD.md §6.1/§6.2** |
| ROC(10) | `indicators/roc.py` | ✓ | hand-computed + `ta.momentum.ROCIndicator` (exact) |
| OBV + slope | `indicators/obv.py` | ✓ | hand-computed (exact); `ta.volume.OnBalanceVolumeIndicator` matches up to a verified, documented constant offset (differing bar-0/tie convention) |
| MACD histogram | `indicators/macd.py` | ✓ | hand-computed (exact); `ta.trend.MACD` matches once a documented, numerically-verified warmup artifact in `ta`'s own implementation decays |
| Parabolic SAR | `indicators/parabolic_sar.py` | ✓ | hand-traced 5-bar sequence + `ta.trend.PSARIndicator` (exact) |

Two real bugs were found and fixed during development — see
`PROGRESS.md` for both (a Wilder-smoothing NaN-handling bug in ADX,
caught by the incremental-vs-vectorized cross-check test; a missing
bar of history in the incremental Parabolic SAR).

`pipeline.py` ties everything together for actual use:
`compute_all_indicators(df)` returns a copy of a DataFrame with every
indicator as a column, and `entry_signal(df, Variant.SECTION_6)` /
`exit_fired(...)` dispatch to the right variant's module without the
caller needing to know the internal layout. It's pure composition/
dispatch - no new math, no new correctness claims beyond what each
underlying module already proves.

## Signal composition

| Variant | Entry | Exit |
|---|---|---|
| Section 2 (core) | `signals/section2.py` | hard stop / trailing stop / RVI reversal — **ATR-multiple stop distances are UNCONFIRMED placeholders, see the module docstring** |
| Section 6 | `signals/section6.py` (Section 2 + ROC/OBV-slope/MACD agreement) | same as Section 2 |
| Section 6a | `signals/section6a.py` (Section 2 + Parabolic SAR agreement) | same as Section 2 |
| Section 7 | same entry as Section 2 | `signals/section7.py` — $15 target / 30-bar cutoff, **exit composition and the $15→price conversion are both UNCONFIRMED, see the module docstring** |

## MT4/MQL4 portability

Every indicator ships two implementations: a vectorized pandas version
(fast, easy to cross-check) and an incremental version
(`..._update(state, bar) -> (value, new_state)`) that consumes one bar
at a time using small persisted state — matching how MQL4 custom
indicators actually execute (one tick/bar at a time, never a
whole-history array). Every incremental function has a test proving it
produces identical output to its vectorized counterpart, bar-for-bar.
All formulas are hand-rolled (no black-box library calls in the shipped
code) so the logic stays transliterable to MQL4 by a human later. The
MQL4 port itself is not part of this phase — see `docs/PRD.md` §4.

## Seeing it work

```bash
python scripts/demo.py                        # synthetic data, clearly labeled as such
python scripts/demo.py --csv path/to/data.csv  # real OHLCV data you supply (open,high,low,close,volume columns)
```

Runs every indicator + all 4 signal variants end to end and prints a
summary. This is the fastest way to see real output without writing any
code. Already run against real data (see above) — on the supplied
139,978-bar real window, Section 2 produced 981 LONG / 546 SHORT
signals, Section 6 (tightest filter) 48/48, Section 6a 376/199, Section
7 exactly matching Section 2 as it should (same entry function).

## Running the tests

```bash
pip install -r requirements-dev.txt
```

If installing `ta` fails with an `install_layout` / distutils error
(seen on Debian-based systems where setuptools' vendored distutils
conflicts with the OS-patched one), install it with:

```bash
SETUPTOOLS_USE_DISTUTILS=stdlib pip install ta
```

Then:

```bash
PYTHONPATH=. pytest tests/ -v
mypy xauusd_indicators --ignore-missing-imports
```

75/75 tests passing (69 synthetic/hand-computed + 6 real-data smoke,
the latter auto-skip without a local data file), mypy clean, as of the
last update to this file. Runs in CI on every push
(`.github/workflows/ci.yml`) once this repo has a remote — the 6
real-data tests will skip there too, since the data file is
intentionally never committed.

To re-run the real-data validation yourself: place an OHLCV CSV
(`open,high,low,close,volume` columns) at `data/xauusd_m1_real.csv`, or
point `XAUUSD_REAL_CSV` at a different path, then run
`pytest tests/test_real_data_smoke.py -v` or `scripts/demo.py --csv`.

## What's NOT in this project

- No backtest engine, P&L simulation, bootstrap/Monte-Carlo validation,
  position sizing, order execution, or broker/MT4 integration.
- No claim that this code reproduces the source report's performance
  numbers, or that the real-data entry-signal counts above represent a
  profitable (or even sensible) trading outcome — only that the code
  runs correctly and produces sane values.

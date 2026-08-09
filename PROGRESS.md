# Progress

Tracking against docs/PRD.md §9 success criteria.

## Done

- [x] `atr()`/`volatility_ratio()` (+ incremental) — hand-computed
      recurrence test + `ta.volatility.AverageTrueRange` cross-check,
      both exact. `tests/test_atr.py` (5 tests).
- [x] `adx()` (+ incremental) — hand-computed recurrence test passes
      exactly. **Real bug found and fixed during development**: the
      vectorized Wilder-smoothing helper used `Series.mean()` on a
      NaN-prefixed input (DX has no defined value until TR/DM smoothing
      warms up), and pandas silently skips NaN in `.mean()` — so the
      ADX seed averaged far fewer than 14 real values instead of
      correctly waiting for 14. Caught by the incremental-vs-vectorized
      cross-check test, not by inspection. Fixed in
      `indicators/adx.py::_wilder_smooth` (see its docstring). `ta`'s
      own `ADXIndicator` has a documented off-by-one quirk in its
      smoothing loop, so it's used only as a shape/sanity check (strict
      uptrend → DX pinned at 100), not exact-value ground truth — the
      hand-derivation is the authoritative check. `tests/test_adx.py`
      (2 tests).
- [x] Custom RVI(14) (+ incremental) — formula per §6.1's inferred
      reading (SMA-based analog), hand-computed exactly on the tiny
      fixture. `tests/test_rvi.py` (7 tests).
- [x] RVI setup-then-cross trigger — reach-then-cross-back state
      machine per §6.2's chosen reading. Engineered sequences cover:
      dip→cross fires LONG, spike→cross fires SHORT, staying inside the
      band never fires, direct jump between extremes re-arms rather
      than firing. Same file.
- [x] `roc()` (+ incremental) — hand-computed + `ta.momentum.ROCIndicator`
      cross-check, exact. `tests/test_roc.py` (3 tests).
- [x] `obv()`/`obv_slope()` (+ incremental) — hand-computed exactly;
      `ta.volume.OnBalanceVolumeIndicator` cross-check holds up to a
      verified, documented constant offset (`ta`'s bar-0/tie convention
      differs from the textbook definition this module follows — see
      `tests/test_obv.py`'s docstring for the numeric proof). Slope
      lookback defaults to 10 per §6.3's proposed default (still
      UNCONFIRMED). `tests/test_obv.py` (4 tests).
- [x] `macd_histogram()` (+ incremental) — hand-computed EMA recurrence
      exact; `ta.trend.MACD` cross-check holds once a documented,
      numerically-verified warmup artifact in `ta`'s own architecture
      decays (gap shrinks from -0.0033 at the shared warmup boundary to
      exactly 0.0 by ~150 bars later — see `tests/test_macd.py`).
      `tests/test_macd.py` (5 tests).
- [x] `parabolic_sar()`/`parabolic_sar_direction()` (+ incremental) — a
      hand-traced 5-bar reversal sequence plus an exact
      `ta.trend.PSARIndicator` cross-check (this module mirrors ta's
      algorithm structure directly). **Real bug found and fixed**: the
      first incremental implementation only kept 1 bar of history, but
      the per-bar SAR formula needs the previous TWO bars' highs/lows
      — fixed before any test was written against it, caught by
      reasoning through the vectorized loop's indexing, not by a failing
      test (unlike the ADX bug). `tests/test_parabolic_sar.py` (4 tests).
- [x] Section 2 entry (RVI cross + ADX>30 + vol-ratio>1.1) and exit
      (hard stop / trailing stop / RVI reversal, ATR-multiple stop
      distances — UNCONFIRMED PLACEHOLDERS per §6.4, see
      `signals/section2.py`'s docstring). Branch-covered via injected
      indicator series + one real end-to-end run.
      `tests/test_signals_section2.py` (12 tests).
- [x] Section 6 entry (+ ROC/OBV-slope/MACD agreement).
      `tests/test_signals_section6.py` (7 tests).
- [x] Section 6a entry (+ Parabolic SAR agreement).
      `tests/test_signals_section6a.py` (5 tests).
- [x] Section 7 exit ($15 target / 30-bar cutoff, hard-stop and
      RVI-reversal kept active per §6.5's chosen reading — UNCONFIRMED,
      see `signals/section7.py`'s docstring; also documents the
      $15→price-distance conversion's contract-size assumption).
      `tests/test_signals_section7.py` (7 tests).
- [x] Incremental-matches-vectorized tests — present for every
      indicator (7/7) as part of each indicator's own test file, not a
      separate consolidated file (a reasonable deviation from the PRD's
      literal package layout in §8; the coverage itself is complete).
- [x] Downtrend hand-computed coverage for ADX and RVI — the original
      hand-derivation tests only covered an uptrend (a real gap: the
      -DM/negative-RVI branches were only exercised by the incremental
      and `ta` cross-checks, which prove internal consistency, not
      correctness against an independent derivation). Added
      `tiny_downtrend_df()` and mirrored both tests.
- [x] A real-bars (not synthetic-Series) end-to-end test for the RVI
      trigger: builds an actual decline-then-recovery OHLCV sequence and
      confirms rvi() → rvi_trigger() fires LONG on it, closing the gap
      where trigger tests only fed hand-built RVI Series directly into
      rvi_trigger().
- [x] `pipeline.py` — `compute_all_indicators(df)` and
      `entry_signal()`/`exit_fired()` variant dispatch, tying every
      module together into one usable surface. Pure composition, no new
      math; tested for correct column shape, no input mutation, and
      correct routing per variant. `tests/test_pipeline.py` (5 tests).
- [x] `mypy xauusd_indicators --ignore-missing-imports` — clean. Started
      at 22 errors, all genuine type-safety gaps (not noise): several
      were the state-machine invariant "this field can't actually be
      None here" not being visible to the type checker across dataclass
      field reads, fixed with explicit `assert ... is not None`
      statements that double as runtime guards, not just type-checker
      placation. One was a real annotation bug in `RviState`
      (`list[float] = None` instead of `list[float] | None = None`).
- [x] `pyproject.toml` + `.github/workflows/ci.yml` — added so this
      becomes a real installable package and gets CI test+mypy runs the
      moment it has a remote to push to (currently local-only).

**69/69 tests passing, mypy clean.**

## Still open (blocking full "done", per docs/PRD.md §6)

None of the 5 open questions are hard-blocked anymore — all were
resolved with a documented, flagged interpretation (user: "whatever the
report says" / "use reasonable placeholders, clearly flagged") rather
than left unimplemented. But every one of these remains UNCONFIRMED
against the report's actual intent, not verified:

1. RVI(14) formula (§6.1) — inferred, not confirmed.
2. Setup-then-cross state machine (§6.2) — reach-then-cross-back
   reading chosen, not confirmed.
3. OBV slope lookback (§6.3) — defaulted to 10, not confirmed.
4. Hard stop / trailing stop distances (§6.4) — ATR-multiple
   placeholders (2.0x / 1.5x), not confirmed, not the report's real
   numbers.
5. Section 7's exit composition (§6.5) — "hard stop + RVI-reversal stay
   active, only trailing stop is replaced" reading chosen, not
   confirmed. The $15→price-distance conversion also assumes a
   standard 100oz/lot XAUUSD contract size, which the report never
   states.

**None of this has been validated against real XAUUSD M1 data** (§5) —
no real data source was reachable from this build environment. Every
test above uses synthetic, hand-computed, or library-cross-checked
fixtures. If the user later supplies real OHLCV data (e.g. exported
from an MT4 terminal), re-running this suite against it is the natural
next step, and is expected to change nothing about correctness (the
formulas don't depend on which data they run on) — but that is
unverified until it actually happens.

**Not started**: the MQL4/MT4 port itself (explicit non-goal of this
phase, PRD §4/§0).

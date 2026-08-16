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
- [x] `bandit -r xauusd_indicators` run and reviewed: 10 low-severity
      `B101` (assert-used) findings, all in the invariant-guard asserts
      added for the mypy pass above. Reviewed, not suppressed: these
      guard internal state-machine invariants, not untrusted input, and
      even if stripped under `python -O` the next line would raise a
      TypeError immediately (arithmetic on None) rather than proceeding
      unsafely - so the practical risk is a worse error message under
      `-O`, not incorrect behavior. Accepted as-is.
- [x] `scripts/demo.py` — runs the full pipeline end to end (all
      indicators + all 4 variants' entry signal counts) against either
      synthetic data (default, clearly labeled) or a user-supplied CSV
      via `--csv`. Actually run during development against both a
      synthetic series and a hand-built CSV, output verified sane
      (Section 7's counts exactly match Section 2's, as they should
      since they share the same entry function - see
      `tests/test_pipeline.py`). Also the natural place to point real
      XAUUSD data at, once available, per docs/PRD.md §5.
- [x] Top-level `xauusd_indicators/__init__.py` now exports
      `compute_all_indicators`/`entry_signal`/`exit_fired`/`Variant`
      directly, so `import xauusd_indicators as xi; xi.compute_all_indicators(df)`
      works without knowing the internal module layout.
- [x] **Real XAUUSD M1 data validation.** The user supplied a real
      OHLCV CSV: 139,978 M1 bars, Dec 15 2025 – May 8 2026 - exactly the
      report's stated window. Findings:
      - Source data quality: no OHLC invariant violations (`high >=
        low/open/close`, `low <= open/close`), no zero/negative volume,
        no null values, no duplicate timestamps. Clean.
      - Ran the full pipeline (`compute_all_indicators` + all 4
        variants' `entry_signal`) against all 139,978 bars: no crashes,
        no exceptions. Total runtime ~2m20s (Python-loop-based Wilder
        recurrences on 140k rows - not optimized for speed, correctness
        was the priority per the PRD).
      - Every indicator's warmup-region NaN count matched its own
        documented formula exactly: ATR=13, volatility_ratio=62,
        ADX=26, RVI=13, ROC=10, OBV_slope=10, MACD_histogram=33,
        Parabolic_SAR=2. No unexpected NaN, no infinities anywhere.
      - ADX stayed within [0, 100] for all 139,952 defined values (a
        real invariant this indicator must satisfy - confirmed on real
        data, not just the synthetic uptrend/downtrend fixtures).
      - Entry signal counts over the real window: Section 2 - 981 LONG
        / 546 SHORT. Section 6 (tightest filter) - 48/48. Section 6a -
        376/199. Section 7 - identical to Section 2 (981/546), exactly
        as it should be since they share the same entry function -
        this is itself a correctness cross-check that held on real
        data.
      - **What this does and doesn't prove**: proves the formulas
        produce sane, well-behaved output at real-world scale and value
        ranges (gold traded $4,102–$5,597 over this window in the
        supplied data). Does NOT validate profitability, ruin
        probability, or reproduce anything from the source report's own
        backtest/bootstrap pipeline - still explicitly out of scope
        (PRD §0). Does NOT hand-verify specific real-data indicator
        values (impractical at 140k rows) - the synthetic
        hand-computed tests remain the actual correctness proof; this
        is a sanity/regression layer on top of that, not a replacement
        for it.
      - The real CSV is NOT committed to this repo (`data/*.csv` is
        gitignored) - its licensing/redistribution terms aren't this
        project's to decide, same caution as the sibling project's
        transcript-copyright policy.
      - `tests/test_real_data_smoke.py` (6 tests) codifies all of the
        above as a repeatable check: skips gracefully when the data
        file isn't present (e.g. a fresh clone, or CI, which has no
        access to it), runs for real when it is.

**75/75 tests passing (69 synthetic/hand-computed + 6 real-data
smoke), mypy clean, bandit reviewed.**

## User-added alarm: Stochastic(50,10,10) + Force Index(50) extremes (docs/PRD.md §10)

Not from the source report - added at the user's explicit request, in
its own `xauusd_indicators/alarms/` package rather than folded into
`indicators/`/`signals/`, so report-derived and user-added work stay
visibly distinct (§10's own opening note explains why).

- [x] `indicators/stochastic.py` (+ incremental) — Slow Stochastic
      (%K period/slowing/%D period = 50/10/10, MT4's own parameter
      order). Independent hand-derivation (fresh rolling min/max/mean,
      not reusing the module's own logic) matches exactly on a 150-bar
      synthetic series. The raw %K component (no slowing) additionally
      cross-checks against `ta.momentum.StochasticOscillator` with
      `smooth_window=1` — exact match; `ta` has no 3-parameter
      Slow-Stochastic mode, so this is a partial cross-check of the core
      formula, not the full %K-slowing/%D composition (that's the hand-
      derivation's job). One disclosed, narrow vectorized/incremental
      divergence: a completely flat 50-bar window (zero range) is
      guarded to 50.0 in the incremental path only, since a pure-Python
      float division by zero raises where numpy/pandas would silently
      give inf/nan — not expected to be hit by any of this project's
      fixtures. `tests/test_stochastic.py` (3 tests).
- [x] `indicators/force_index.py` (+ incremental) — Elder's Force Index,
      EMA(50)-smoothed. **A real, caught-before-shipping bug**: the raw
      series (`close.diff() * volume`) is NaN on its very first bar (no
      previous close) — naively reusing `macd.py`'s `_ema_full()` as-is
      would have seeded the whole EMA recursion on that NaN and poisoned
      every value forever (`alpha*x + (1-alpha)*NaN` is NaN,
      unconditionally). Same bug class `adx.py::_wilder_smooth` already
      had to fix once for a NaN-prefixed DX input — caught here by
      working through the seeding logic before writing the test, not by
      a failing test. Fixed with a dedicated
      `_ema_seeded_at_first_valid()` helper. Hand-derivation matches
      exactly; `ta.volume.ForceIndexIndicator` cross-check also matches
      exactly once a real, empirically-verified masking-convention
      difference is accounted for — `ta` hides one bar more for this
      specific indicator class than `macd.py::ema()`'s own convention
      does (first valid at index `period`, not `period - 1`); this
      module deliberately matches `ta`'s convention, documented in the
      module docstring, for the same "exact cross-check, no fighting a
      seeding mismatch" reasoning `macd.py` already gives for its own
      choice. `tests/test_force_index.py` (3 tests).
- [x] `alarms/extremes.py` — `evaluate_extremes()` (pure decision
      function, mirrors this account's ad-blocker project's
      `FilterEngine.evaluate()` shape) plus `extremes()`
      (DataFrame)/`extremes_update()` (incremental) wrappers, all three
      proven to agree with each other on real computed synthetic data,
      not just hand-picked numbers. Stochastic requires **both** %K and
      %D past 90/10 (user's explicit choice, confirmed when asked, over
      "either line" or "%K only"); Force Index fires independently past
      ±70; a bar can fire one, both, or neither — no requirement that
      the two agree with each other, unlike the report's own Section
      6/6a agreement filters. Exact-threshold values (90, 10, ±70) do
      not fire. `tests/test_alarms_extremes.py` (7 tests).
- [x] `pipeline.py` — `compute_all_indicators()` gains `stochastic_k`/
      `stochastic_d`/`force_index`/`extreme_alarms` columns;
      `scripts/demo.py` prints alarm counts alongside the existing
      per-variant entry-signal counts. Run against 400 synthetic bars
      during development: produced 40 `stochastic_overbought` firings,
      0 of the other three — plausible, non-degenerate output, not
      independently verified further (same "sane, not certified
      profitable" standard as every other demo run in this project).
      `tests/test_pipeline.py` (+1 test).

**14 new tests, all passing (3 stochastic + 3 force index + 7 alarm
decision logic + 1 pipeline). Full suite: 89 collected, 83 passing + 6
real-data-skip (same skip-without-local-CSV behavior as before, unrelated
to this work).** `mypy xauusd_indicators --ignore-missing-imports` —
clean, no new errors introduced.

**Not done, disclosed rather than silently skipped:**
- No MQL4 port for this alarm (`mql4/` doesn't cover §10 — see PRD
  §10.4). If needed there later, it follows the same
  transliterate-and-verify pattern the other 7 indicators already went
  through.
- No real-XAUUSD-data run for these two indicators specifically — the
  existing `tests/test_real_data_smoke.py` suite predates this alarm
  and doesn't exercise it; extending that smoke test to cover §10 would
  be the natural next step if/when real data validation matters for it.

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

**Real XAUUSD M1 data validation is now done** (§5, above) - the gap
that used to sit here is closed for "does this run correctly and behave
sanely on real data." What real-data validation does NOT cover: the 5
interpretation gaps above are about the report's *intent*, and no
amount of running against real price data resolves them - only the
report's original author/strategy file can. The real-data run also
doesn't hand-verify specific indicator values (the synthetic
hand-computed tests are still the correctness proof) or say anything
about whether the signals these interpretations produce would have been
profitable.

**MQL4/MT4 port — built 2026-08-09, at the user's explicit request**
(this was an explicit non-goal of the original phase, PRD §4/§0 — the
user chose to move into that separate phase). Real order execution now
exists (`mql4/Experts/XAUUSD_Report_EA.mq4`), built for a DEMO ACCOUNT
ONLY, with the same UNCONFIRMED placeholder risk parameters carried
over unchanged (not replaced with real numbers, since none were
supplied). Full detail, safety notes, and exactly what is/isn't
verified: `mql4/README.md`.

**Verification actually run** (this sandbox has no MQL4 compiler, so
this is the strongest check available without one — see
`mql4/README.md` for why it's real evidence, not a rubber stamp, and
what it does and doesn't prove): every indicator formula and
entry/exit condition in the `.mqh` files was independently
transliterated into a second, separate Python implementation (never by
importing the real `xauusd_indicators` code, which would make the
check circular) and run against the real, tested package on the same
synthetic data.
- `mql4/verification/verify_mql4_port.py` — all 7 indicators, 400 bars,
  agree to 1e-9 between the real package and the shadow transliteration.
- `mql4/verification/verify_mql4_signals.py` — Section 2/6/6a entry
  composition matches bar-for-bar.
- `mql4/verification/verify_mql4_exits.py` — 7 engineered scenarios
  (hard stop, trailing stop, RVI reversal, $15 target, 30-bar cutoff,
  both Section 2's and Section 7's exit composition) all match.

All three pass as of this writing, and are real, run, checked-in
scripts — not a one-off claim.

**Not verified, and disclosed as such rather than assumed away:** the
`.mq4`/`.mqh` files have never been compiled in real MetaEditor — MQL4
syntax/type/array rules a Python transliteration cannot catch a
violation of. The order-execution and position-management code in
`XAUUSD_Report_EA.mq4` (new-bar detection, `OpenPosition`/
`ClosePosition`, the demo-account safety check) has *no* cross-check of
any kind — it's genuinely new code with no Python equivalent to
transliterate against, since the Python project never modeled real
orders at all. This is the highest-risk, least-verified part of the
whole port. See `mql4/README.md`'s "Before using this, even on demo"
section for the real manual verification steps (compile it, cross-check
against `scripts/demo.py`'s output on the same data, run it in
Strategy Tester before any forward test, then forward-test on demo
before ever considering the unresolved placeholder parameters "settled
enough" to think about — which would need its own separate, explicit
decision, not an assumption carried over from this one).

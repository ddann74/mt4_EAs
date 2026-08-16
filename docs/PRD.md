# PRD — XAUUSD Indicator & Signal Library

**Status of this document:** Written directly from the source report's
extracted text (`docs/source_report_extract.txt`, verbatim PDF text kept
alongside this PRD so every claim below can be checked against it) plus
network verification performed while writing this PRD (see §5). Nothing
here is aspirational — every open question the source material doesn't
answer is listed in §6 rather than silently resolved.

## 0. What this project is, and what it explicitly is not

The source report ("XAUUSD Strategy Analysis") describes four bootstrap-
validated trading strategies for XAUUSD (Gold) on the M1 timeframe, all
built from a shared core of six technical indicators plus entry/exit
composition rules. This project implements **the indicator math and the
entry/exit signal-composition logic** — i.e., "given this bar and recent
history, does Section 2/6/6a/7 say buy, sell, or do nothing right now,
and does the current position's exit condition fire?"

This project does **not**:
- Backtest, simulate P&L, or run bootstrap/Monte-Carlo validation. The
  report already did that; reproducing it is out of scope.
- Track positions, size lots, place orders, or talk to a broker/MT4
  terminal. Those come later, if at all, in a separate phase.
- Claim, reproduce, or imply any of the report's return/ruin-probability
  numbers (+21.48%/month, 2.0% ruin, etc.). This project can prove its
  indicator math is *correct*; it cannot and does not claim the
  *strategy is profitable* — that would require the report's full
  backtest + bootstrap pipeline, which this project doesn't rebuild.

## 1. Why this exists

The user wants working, tested implementations of the indicators and
entry/exit rules described in the report, with an eventual goal of
running the logic on MetaTrader 4 (MQL4). This phase is Python (for fast
iteration and easy correctness cross-checks against reference
libraries), but every design decision below is made with that MT4 future
in mind — see §4.

## 2. Indicators to implement

All operate on OHLCV bars: `open, high, low, close, volume`, one row per
M1 bar. Each indicator ships as (a) a vectorized pandas function for fast
testing/iteration, and (b) an incremental/stateful function that consumes
one new bar plus a small persisted state object and returns the same
value the vectorized version would at that point — see §4 for why both
are required.

### 2.1 ATR(14) and Volatility Ratio
Standard Wilder ATR(14): true range = `max(high-low, |high-prev_close|,
|low-prev_close|)`, smoothed with Wilder's method (equivalent to an
EMA with alpha = 1/14).
Volatility ratio = `ATR(14) / SMA(ATR(14), 50)`. Report requires this
ratio `> 1.1` to confirm a signal.

### 2.2 ADX(14)
Standard Wilder ADX: +DM/-DM from consecutive highs/lows, smoothed
TR/+DM/-DM (Wilder smoothing), +DI/-DI, DX = `100 * |+DI - -DI| / (+DI +
-DI)`, ADX = Wilder-smoothed DX. Report requires `ADX(14) > 30`.

### 2.3 RVI(14) — CUSTOM, non-standard
Report explicitly states this is "SMA-based, not standard weighted RVI."
Standard RVI numerator/denominator use a weighted 4-bar average
`(x + 2*x1 + 2*x2 + x3) / 6`; this custom version instead uses a plain
SMA(14) of `(close - open)` divided by SMA(14) of `(high - low)`,
oscillating roughly in [-1, 1]. **This formula is inferred from the
report's own description ("SMA-based") and is an open question, not a
confirmed spec — see §6.1.** Signal: "setup-then-cross through ±0.20" —
**the exact state machine is not defined in the source text; see §6.2.**
This is the single highest-risk ambiguity in this PRD.

### 2.4 ROC(10)
Standard: `100 * (close - close[10 bars ago]) / close[10 bars ago]`.

### 2.5 OBV + slope
Standard OBV: running sum, `+volume` on up-close bars, `-volume` on
down-close bars, unchanged on flat closes. Slope: linear regression (or
simple `OBV[t] - OBV[t-n]`) over a lookback window — **exact lookback
`n` is not given in the source text; see §6.3.**

### 2.6 MACD histogram
Standard MACD(12,26,9): `EMA(12) - EMA(26)` = MACD line, `EMA(9)` of that
= signal line, histogram = MACD line − signal line. Report doesn't
override these parameters, so 12/26/9 is used as the standard default,
not an open question.

### 2.7 Parabolic SAR
Standard Wellesley Wilder Parabolic SAR (AF start 0.02, step 0.02, max
0.2 — the report doesn't override these; treated as standard defaults).
Output: trend direction (long while SAR is below price, short while
above).

## 3. Signal composition (all four report variants)

Each returns one of `LONG`, `SHORT`, `FLAT` for entries; exit functions
return a boolean given the current bar plus a hypothetical open-position
state (`entry_price`, `entry_bar_index`, `direction`).

- **Section 2 (core)**: RVI setup-then-cross through ±0.20 (§2.3) AND
  ADX(14) > 30 AND volatility ratio > 1.1. Exit: hard stop OR trailing
  stop OR RVI reversal — **none of these three have numeric parameters
  in the source text (stop distance, trailing distance, what counts as
  "reversal"); see §6.4.**
- **Section 6**: Section 2's entry conditions AND ROC(10)/OBV-slope/MACD-
  histogram all agree with the trade direction (all three positive for
  LONG, all three negative for SHORT). Same exit as Section 2.
- **Section 6a**: Section 2's entry conditions AND Parabolic SAR
  direction agrees with the trade direction. Same exit as Section 2.
- **Section 7**: Same entry as Section 2. Exit: fixed $15 profit target
  OR 30-bar time cutoff — **and, per the report's own text, "instead of
  a trailing stop," implying the hard-stop/RVI-reversal exits still
  apply alongside the $15/30-bar rule; the source text is ambiguous
  about whether hard-stop still applies here too — see §6.5.**

Position sizing (fixed 0.01 lot) and the single-pyramid-add rule are
**not implemented** — they're position-management, not signal logic,
and the PRD's scope stops at signal generation (§0).

## 4. MT4/MQL4 portability constraint

The user's stated eventual goal is running this on MetaTrader 4. MQL4
custom indicators execute **incrementally**, one new bar/tick at a time,
using small persisted state — never as a whole-history vectorized array
the way pandas naturally works. To avoid a full rewrite at port time:

- Every indicator/signal function must have two implementations: a
  vectorized pandas version (fast, easy to test against reference
  libraries) and an incremental version (`def update(state, new_bar) ->
  (value, new_state)`), tested to produce identical output to the
  vectorized version bar-for-bar on the same input.
- All formulas are hand-rolled (explicit arithmetic in this codebase),
  never a bare call into `pandas-ta`/`ta`/etc. Those libraries are used
  **only** as an independent correctness cross-check in tests, never as
  the shipped implementation — so the logic stays readable and
  transliterable to MQL4 by a human later.
- The actual MQL4 port is an explicit non-goal of this phase. This
  section only constrains today's design so that phase doesn't require
  reworking the math.

## 5. Data availability

**UPDATE — real data was supplied and used.** At PRD-writing time, real
XAUUSD M1 OHLCV data for the report's window (Dec 15 2025 – May 8 2026)
was not reachable from the build environment (outbound requests to
Yahoo Finance, Dukascopy, and a generic FX data API all failed to
connect). The user subsequently supplied a real M1 OHLCV CSV covering
exactly that window (139,978 bars, Dec 15 2025 – May 8 2026) - see
`PROGRESS.md` for the full validation findings. Summary: no OHLC
invariant violations or data-quality issues in the source file; every
indicator's warmup-region NaN count on the real data matched its own
documented formula exactly (e.g. ADX's 26-bar warmup, volatility
ratio's 62-bar warmup); no infinite/malformed values produced; every
signal-composition variant ran end-to-end without error, producing
plausible, non-degenerate entry counts (Section 2: 981 LONG / 546
SHORT over ~140k bars). This proves the formulas behave correctly on
real data, not just synthetic fixtures - it does **not** validate
profitability, ruin probability, or anything the source report's own
backtest/bootstrap pipeline claims (§0 - still explicitly out of
scope), and it does not re-derive expected values by hand against real
data (impractical at this volume) - the hand-derivations in §2's tests
remain the correctness proof; this is a real-data sanity/regression
check layered on top, per `tests/test_real_data_smoke.py`.

The real CSV itself is not committed to this repo (gitignored,
`data/*.csv`) - its licensing/redistribution terms aren't this
project's to decide, same caution as the sibling project's transcript-
copyright policy. `tests/test_real_data_smoke.py` skips gracefully
when the file isn't present locally, and documents exactly where to
place it to re-run the validation.

**Fallback (what most of this project's tests still do):** every
indicator and signal *correctness* test uses **synthetic OHLCV fixtures
with hand-computed expected values**, built and checked step-by-step in
the test itself. Cross-checks against `pandas-ta`/`ta` (§2) also run on
synthetic fixtures. That division of labor is intentional: synthetic
fixtures prove the formulas are *right*; the real-data smoke test proves
they behave *sanely* at real-world scale and value ranges. Neither
alone would be sufficient.

## 6. Open questions — must be resolved by the user, not guessed

1. **RVI(14) exact formula.** §2.3's SMA-based formula is inferred, not
   confirmed. Confirm or correct: `SMA(close-open, 14) / SMA(high-low,
   14)`?
2. **"Setup-then-cross through ±0.20" state machine.** Candidate reading:
   RVI must first reach beyond ±0.20 (the "setup"), then cross back
   through ±0.20 toward zero (the "cross") to trigger. Needs explicit
   confirmation — this is a directional trigger, not a level check, and
   getting it wrong changes every backtest result derived from it.
3. **OBV slope lookback window** (§2.5) — not specified. Proposed
   default: 10 bars (matches ROC's period), pending confirmation.
4. **Hard stop / trailing stop distances and RVI-reversal exit
   definition** (§3, Section 2/6/6a exit) — no numeric values anywhere
   in the source text.
5. **Section 7's exit composition** (§3) — does the hard-stop/RVI-
   reversal exit still apply alongside the $15/30-bar rule, or is it
   fully replaced?

Until these are answered, the Ralph loop implementing this PRD will stop
and surface each one rather than picking an interpretation silently
(per the loop's own instructions).

## 7. Stack

Python 3.11+, `pandas`, `numpy`. `pandas-ta` (or `ta`) as a dev/test-only
dependency for cross-checking standard indicators (ATR, ADX, ROC, OBV,
MACD, Parabolic SAR) — never imported by the shipped indicator code
itself (§4). `pytest` for tests.

## 8. Package layout

```
xauusd_indicators/
  __init__.py
  indicators/
    atr.py          # atr(), volatility_ratio(), + incremental variants
    adx.py
    rvi.py           # custom RVI - flagged pending §6.1/§6.2
    roc.py
    obv.py
    macd.py
    parabolic_sar.py
  signals/
    section2.py      # core entry + shared exit
    section6.py
    section6a.py
    section7.py
  types.py            # OHLCVBar, PositionState, Signal enum, IndicatorState
docs/
  PRD.md
  source_report_extract.txt
tests/
  fixtures.py          # synthetic OHLCV series + hand-computed expected values
  test_atr.py
  test_adx.py
  test_rvi.py
  test_roc.py
  test_obv.py
  test_macd.py
  test_parabolic_sar.py
  test_signals_section2.py
  test_signals_section6.py
  test_signals_section6a.py
  test_signals_section7.py
  test_incremental_matches_vectorized.py
```

## 9. Success criteria (maps 1:1 to runnable tests)

- [x] `atr()`/`volatility_ratio()` match hand-computed values on a fixed
      synthetic series AND match `pandas-ta`'s ATR on the same series.
      `tests/test_atr.py`.
- [x] `adx()` matches hand-computed values AND `pandas-ta`'s ADX (used
      as a sanity check only, per §2.2/PROGRESS.md - `ta`'s own
      implementation has a documented off-by-one quirk).
      `tests/test_adx.py`.
- [x] `rvi()` matches hand-computed values per the §6.1 formula. No
      longer blocked: user chose "use my inferred formula" when asked -
      implemented and tested against that reading, still UNCONFIRMED
      against the report's true original intent (no way to verify that
      without the report author). `tests/test_rvi.py`.
- [x] RVI setup-then-cross trigger correctly fires/doesn't fire on
      engineered synthetic sequences per the §6.2 state machine. No
      longer blocked: user said "whatever the report says," and the
      report genuinely specifies nothing beyond the phrase itself, so
      the reach-then-cross-back reading was implemented and tested -
      same UNCONFIRMED-but-not-blocked status as RVI's formula.
      `tests/test_rvi.py`.
- [x] `roc()` matches hand-computed values AND a reference library.
      `tests/test_roc.py`.
- [x] `obv()` and its slope match hand-computed values, slope lookback
      per §6.3 (default 10, still pending confirmation but implemented
      and tested against that default). `tests/test_obv.py`.
- [x] `macd_histogram()` matches hand-computed values AND a reference
      library (once a documented, numerically-verified warmup artifact
      in the reference library's own architecture decays - see
      PROGRESS.md). `tests/test_macd.py`.
- [x] `parabolic_sar()` matches hand-computed values AND a reference
      library over a multi-bar trend-reversal sequence.
      `tests/test_parabolic_sar.py`.
- [x] Section 2 entry signal fires only when all three conditions hold,
      on engineered synthetic bars covering each combination.
      `tests/test_signals_section2.py`.
- [x] Section 6 entry signal additionally requires all three momentum
      filters to agree; tested with one-disagrees-per-filter cases.
      `tests/test_signals_section6.py`.
- [x] Section 6a entry signal additionally requires SAR agreement.
      `tests/test_signals_section6a.py`.
- [x] Section 7 exit fires correctly on $15 target and on 30-bar cutoff,
      independently and combined; exit composition per §6.5. No longer
      blocked: implemented per the "hard-stop/RVI-reversal stay active,
      only trailing stop is replaced" reading, documented as
      UNCONFIRMED in `signals/section7.py`. `tests/test_signals_section7.py`.
- [x] Every indicator/signal has a passing
      incremental-matches-vectorized test (§4). Present in every
      indicator's own test file (7/7).
- [x] README states plainly: what's implemented, what's tested against
      what, and which of §6's open questions remain unresolved.

**All 14 items done as of this update** - see PROGRESS.md for the
full, current status including real-data validation (§5) added after
this checklist was originally written. "Done" here means "implemented
and tested against a specific, documented interpretation" - it does
NOT mean the 5 UNCONFIRMED interpretations in §6 have been verified
against the report's actual original intent, only that they're no
longer blocking further work, per the user's explicit choices.

## 10. User-added alarm: Stochastic + Force Index extremes (NOT from the source report)

Added after the rest of this PRD was written and implemented, at the
user's explicit request - unlike §2's seven indicators and §3's four
signal variants, nothing below comes from the source XAUUSD Strategy
Analysis report. Kept in its own section, its own package
(`xauusd_indicators/alarms/`, alongside `indicators/`/`signals/` rather
than inside either), for the same reason §0 draws a hard line around
what this project is/isn't: so "report-derived" and "user-added" stay
visibly distinct rather than blurring together.

### 10.1 Stochastic Oscillator (50, 10, 10)

Standard "Slow Stochastic" formula, parameterized (%K period, %K
slowing, %D period) - the same three-number order MT4's own
`iStochastic()` uses. User specified 50/10/10.

```
raw %K  = 100 * (close - lowest_low(50)) / (highest_high(50) - lowest_low(50))
slow %K = SMA(raw %K, 10)      <- what MT4 actually plots as "%K"
%D      = SMA(slow %K, 10)
```

Unlike RVI (§2.3), this is **not** an open question - "50,10,10" is
unambiguous notation for a well-known indicator, not an inferred reading
of ambiguous report prose. `indicators/stochastic.py`.

### 10.2 Force Index (50)

Elder's standard definition: raw Force Index = `(close[t] - close[t-1])
* volume[t]`, EMA-smoothed. User specified period 50.
`indicators/force_index.py`.

### 10.3 Alarm thresholds and composition

- **Stochastic**: fires `STOCHASTIC_OVERBOUGHT` when **both** slow %K
  and %D are `> 90`; fires `STOCHASTIC_OVERSOLD` when **both** are `<
  10`. Exactly at 90/10 does not fire ("over"/"under", not
  "at-or-beyond"). Requiring both lines together, rather than either
  line alone or %K alone, was an explicit user choice made when asked -
  see `alarms/extremes.py`'s module docstring.
- **Force Index**: fires `FORCE_INDEX_HIGH` when `> 70`; fires
  `FORCE_INDEX_LOW` when `< -70`. Exactly at ±70 does not fire.
- Stochastic and Force Index are evaluated **independently** - a bar can
  fire one, the other, both, or neither. Unlike §3's Section 6/6a
  filters (which require several indicators to *agree* with a trade
  direction before anything fires), these two alarms don't need to agree
  with each other; they're flagging two different, unrelated readings
  (range-relative exhaustion vs. raw pressure momentum), not composing
  toward a single trade decision.
- This is an **alarm**, not a signal-composition variant: it doesn't
  return LONG/SHORT/FLAT or feed into `entry_signal()`/`exit_fired()`
  (§3's dispatch). It's a standalone "worth looking at this bar" flag,
  same spirit as the Android `rvi-adx-forex-alarm` app (a separate
  project on this account) alerting on a condition without placing or
  managing a trade itself.

### 10.4 Non-goals for this section

- **No MQL4 port yet.** `mql4/` (§4's eventual-goal phase, built at a
  separate earlier explicit user request) does not include this alarm.
  If/when it's needed there, it follows the same pattern every other
  indicator there already does - see `mql4/README.md`.
- **No position sizing, entry/exit, or trade management** - same scope
  boundary as §0/§3: this is a threshold-crossing flag, not a strategy.
- **No backtesting or profitability claim** of any kind for these
  thresholds - same §0 boundary as the rest of this project.

### 10.5 Success criteria

- [x] `stochastic()`/`stochastic_update()` match an independent
      hand-derivation on synthetic data, and the raw %K component
      matches `ta.momentum.StochasticOscillator` (partial cross-check
      only - `ta` has no 3-parameter Slow Stochastic mode to compare
      the full composition against; see `tests/test_stochastic.py`'s
      module docstring for why). `tests/test_stochastic.py`.
- [x] `force_index()`/`force_index_update()` match an independent
      hand-derivation on synthetic data AND `ta.volume.ForceIndexIndicator`
      exactly (once a documented, one-bar masking-convention difference
      from this project's own `macd.py::ema()` is accounted for - see
      `indicators/force_index.py`'s docstring). `tests/test_force_index.py`.
- [x] `evaluate_extremes()` covers every branch: each alarm firing alone
      on engineered values, both stochastic lines required together
      (one alone never fires), exact-threshold values not firing, two
      alarms able to fire on the same bar, `None`/still-warming-up
      inputs never firing. `tests/test_alarms_extremes.py`.
- [x] `extremes()` (DataFrame), `extremes_update()` (incremental), and
      `evaluate_extremes()` (pure decision function) agree with each
      other on every bar of a real computed synthetic series, warmup
      region included - not just on hand-picked numbers.
      `tests/test_alarms_extremes.py`.
- [x] `pipeline.compute_all_indicators()` includes the new columns
      (`stochastic_k`, `stochastic_d`, `force_index`, `extreme_alarms`);
      `scripts/demo.py` prints alarm counts alongside the existing
      per-variant entry-signal counts. `tests/test_pipeline.py`.

**All 5 items done.** See PROGRESS.md for the corresponding entry.

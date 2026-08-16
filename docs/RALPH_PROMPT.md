# Ralph loop prompt

You are running as an autonomous build loop ("Ralph loop") against
docs/PRD.md in this repository. Repeat the following cycle until every
success-criterion item in the PRD is checked off or genuinely blocked:

1. Read docs/PRD.md in full. Read PROGRESS.md if it exists (create it on
   first run) to see what's already done, what's in flight, and what's
   blocked.
2. Pick the single highest-priority unfinished item. Prefer the order
   the PRD lists them in unless a dependency forces otherwise (indicator
   primitives before the signal-composition functions that consume
   them).
3. Implement just that item.
   - For an indicator: hand-rolled formula (per the PRD's MT4-
     portability constraint — no opaque library call as the actual
     implementation), plus its correctness test(s) against the
     independent reference the PRD specifies for it.
   - For a signal-composition function: the entry/exit logic plus tests
     built from synthetic bar sequences that exercise every branch
     (all-agree, one-filter-disagrees, exit-fires, exit-doesn't-fire).
   - Never land either without the test the PRD requires for it.
4. Run the full test suite. If anything fails — including tests for
   previously "done" items — fix it before moving on. A regression
   blocks new work.
5. Update PROGRESS.md: mark the item done with the exact test(s) that
   prove it, or mark it blocked with the specific, concrete reason
   (missing data source, ambiguous spec the PRD flagged as an open
   question, etc.) — never mark something done on the basis of "looks
   right."
6. Commit with a message describing what was actually built and what
   the tests actually proved — no "implemented X" without naming which
   test proves X works.
7. If you hit one of the PRD's flagged open questions (§6: RVI formula,
   setup-then-cross state machine, OBV slope window, stop/trailing-stop
   parameters, Section 7 exit composition) and can't resolve it from the
   source report text alone, STOP the loop and surface the exact
   question — do not silently choose an interpretation and keep going.
   §10 (the user-added Stochastic/Force Index alarm) is NOT from the
   source report at all, so this rule applies differently there: if you
   hit an ambiguity in §10 the user hasn't already settled in the PRD
   text itself, STOP and ask the user directly — there's no report text
   to fall back on resolving it from either way.
8. If you hit something structurally blocked (e.g. no real market data
   reachable from this environment, per PRD §5), implement against the
   PRD's defined fallback (labeled synthetic fixtures), note the
   real-data gap explicitly in PROGRESS.md and the README, and continue
   — degrade gracefully, never claim more than what's actually true.
9. Keep every indicator/signal function honest about the MT4 portability
   constraint (PRD §4) as you go: if an implementation only works
   vectorized over a whole history array with no incremental
   equivalent, that's a defect against the PRD, not a style nitpick —
   fix it before marking the item done.

Never mark the PRD complete, never claim "all indicators validated,"
and never write summary language stronger than what the actual test
suite proves. Never claim or imply this code reproduces the source
report's return/ruin-probability numbers — that was never in scope.
When every item is done or every remaining item is genuinely blocked
(not just hard), stop and report a final honest status: what's built,
what's tested against what, and what's still open.

# MQL4 live-trading port

This is the phase the root `README.md`/`docs/PRD.md` explicitly scoped
out ("does not track positions, size lots, place orders, or talk to a
broker/MT4 terminal... those come later, if at all, in a separate
phase" - `docs/PRD.md` §0). Built at the user's explicit request, with
three decisions confirmed by the user before writing any code:

1. **Platform: MQL4**, matching the repo's existing incremental-
   indicator design (`docs/PRD.md` §4 was explicit that every
   indicator's `_update()` function was written to be portable to
   MQL4's one-bar-at-a-time execution model).
2. **Risk parameters: the existing UNCONFIRMED placeholders** (hard
   stop 2×ATR, trailing stop 1.5×ATR, Section 7's $15 target assuming
   a 100oz/lot contract) - carried over unchanged, not replaced with
   real numbers, because none were supplied.
3. **Demo/paper account only**, enforced at `OnInit()` - see
   "Safety" below.

## Files

```
mql4/
  Include/
    XAUUSD_Indicators.mqh   Port of indicators/*.py's _update() functions
    XAUUSD_Signals.mqh      Port of signals/section*.py's entry_signal()/exit_fired()
  Experts/
    XAUUSD_Report_EA.mq4    The actual EA: new-bar detection, order
                             execution, position management - NEW code,
                             no Python equivalent (order execution was
                             explicitly out of scope there)
  verification/
    verify_mql4_port.py     Real, run, checked-in evidence (see below)
    verify_mql4_signals.py
    verify_mql4_exits.py
```

## What's real and verified vs. what isn't

**This file has never been compiled.** This sandbox has no MQL4
compiler and no MetaTrader terminal - the same category of limitation
this account's other Android projects this session (`spot_block`,
`newfuel`) hit with Play Services/androidx, disclosed the same way:
plainly, with exactly what was and wasn't checked.

**What actually was verified, for real, without a compiler:** every
indicator formula and every entry/exit condition in the `.mqh` files
was independently transliterated into a second, separate Python
implementation (`mql4/verification/*.py` - not by importing or reusing
`xauusd_indicators`' own code, which would make the check circular),
then run against the real, already-tested `xauusd_indicators` package
on the same synthetic data. Run them yourself:

```bash
python3 mql4/verification/verify_mql4_port.py     # all 7 indicators, 400 bars, agree to 1e-9
python3 mql4/verification/verify_mql4_signals.py  # Section 2/6/6a entry composition, bar-for-bar
python3 mql4/verification/verify_mql4_exits.py    # hard stop / trailing stop / RVI reversal / $15 target / 30-bar cutoff, 7 engineered scenarios
```

All three pass as of this writing. This is real, meaningful evidence
the *arithmetic* in the `.mqh` files is correct - reading the MQL4
source and independently re-deriving the same numbers in a second
language is a genuine cross-check, not a rubber stamp. **It is NOT
evidence the `.mq4`/`.mqh` files compile or run in real MQL4** - MQL4
has its own syntax, type, and array-handling rules a Python
transliteration can't catch a violation of. Only real MetaEditor can
prove that.

**What has no verification of any kind:** `XAUUSD_Report_EA.mq4`'s
order-execution and position-management code (`OpenPosition`,
`ClosePosition`, new-bar detection, the demo-account check). This is
genuinely new code with no Python equivalent to transliterate against -
the Python project never modeled real orders at all (`docs/PRD.md`
§0/§3). This is the highest-risk, least-verified part of the whole
port, precisely because it's the part that touches a real account.

## Safety: this is built for a demo account, not live

`InpRequireDemoAccount` (default `true`) checks
`AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_DEMO` at
`OnInit()` and returns `INIT_FAILED` - refusing to run at all - if the
account doesn't report as a demo account. It re-checks every bar in
`OnTick()` too, in case the account type changes mid-session. **This
check has not been compiled or run for real** (see above) - verify
manually that you're on a demo account before attaching this EA
regardless of what the code claims to do.

Do not point this at a live account. Three real, unresolved reasons
why, not just general caution:

1. `HARD_STOP_ATR_MULTIPLE` (2.0), `TRAIL_ATR_MULTIPLE` (1.5), and
   Section 7's `$15` → price-distance conversion are all **documented
   placeholders**, not the source report's real numbers (`docs/PRD.md`
   §6.4/§6.5) - the report gives no numeric stop distances anywhere in
   its extracted text.
2. The RVI formula and its setup-then-cross trigger - which every
   variant's entry, and the RVI-reversal exit, depend on - are
   **UNCONFIRMED interpretations** of an ambiguous source-report phrase
   (`docs/PRD.md` §6.1/§6.2), not a confirmed spec.
3. The order-execution code itself has zero test coverage of any kind
   (see above) - it has never run against even a simulated broker
   connection, let alone a real one.

## Before using this, even on demo

1. **Compile it.** Open `mql4/Include/*.mqh` and
   `mql4/Experts/XAUUSD_Report_EA.mq4` in MetaEditor (copy them into
   your MT4 data folder's `MQL4/Include/` and `MQL4/Experts/`
   respectively first), fix whatever it flags. Expect at least one
   real compile error on the first attempt - Spot Block
   (`ddann74/spot_block`, elsewhere in this account) hit exactly one
   real bug on its first genuine build after an equivalent "carefully
   written, never compiled" disclosure; treat that as the normal
   outcome, not a sign something else is wrong.
2. **Cross-check output against the Python demo script**, not just
   "does it compile." Run `python scripts/demo.py --csv path/to/data.csv`
   against the same historical M1 data you'll backtest/forward-test the
   EA on in MT4's Strategy Tester, and compare indicator values and
   entry/exit signal counts by eye for a stretch of bars. The
   verification scripts above prove the *formulas* agree; they say
   nothing about whether the compiled `.mq4` file, fed real MT4 bar
   data through the real `Open[]`/`High[]`/`Low[]`/`Close[]`/`Volume[]`
   arrays, produces the same result.
3. **Run it in MT4's Strategy Tester first**, not live-forward on even
   a demo account - a backtest surfaces logic errors (wrong order
   sizing, a stuck position, an exit that never fires) far faster than
   watching it tick by tick.
4. **Then, and only then, forward-test on a demo account** for an
   extended period, watching the `Experts`/`Journal` log tabs (every
   `Print()` call in the EA logs there) for anything unexpected -
   before ever considering the three unresolved items above as
   "confirmed enough" to think about a live account, which would also
   require the user's own explicit, separate decision at that point,
   not an assumption carried over from this one.

## Updating the placeholder risk parameters

Once real numbers are confirmed, they're isolated to
`mql4/Include/XAUUSD_Signals.mqh`'s `#define` block at the top -
`HARD_STOP_ATR_MULTIPLE`, `TRAIL_ATR_MULTIPLE`, `PROFIT_TARGET_USD`,
`TIME_CUTOFF_BARS`, `NOTIONAL_OZ_PER_POSITION` - matching how the
Python modules isolated the same constants for the same reason
(`signals/section2.py`/`section7.py`'s own module docstrings).

#!/usr/bin/env python3
"""Repo-local trust ramp — gate arithmetic, demotion, and tamper detection.

Covers bin/trust-ramp, which is repo governance rather than protocol surface:
it emits nothing, is not imported by lib/, and touches no golden digest. The
behavior worth pinning is the part that must not quietly soften — the gates
refuse, blank outcomes are fatal, harmful demotes, and a hand-edited state
block does not buy a promotion.

Every case runs against a temporary ledger; the shipped .claude/trust-ramp.md
is read once, read-only, to confirm it parses and starts at R0.

Run: python3 tests/test_trust_ramp.py
"""
import datetime
import importlib.machinery
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPT = os.path.join(ROOT, "bin", "trust-ramp")
SHIPPED = os.path.join(ROOT, ".claude", "trust-ramp.md")

# bin/trust-ramp has no .py extension (it is a CLI, like every other bin/
# script here), so it is loaded by path rather than imported by name.
_spec = importlib.util.spec_from_loader(
    "trust_ramp", importlib.machinery.SourceFileLoader("trust_ramp", SCRIPT))
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        if detail:
            print(f"        {detail}")


TODAY = datetime.date(2026, 9, 1)


def ledger(rung="R0", entered="2026-07-28", attests="", entries=""):
    return (f"# t\n\n<!-- STATE -->\ncurrent_rung: {rung}\n"
            f"rung_entered: {entered}\nattestations: {attests}\n"
            f"<!-- /STATE -->\n\n## Ledger\n{entries}")


TMP = tempfile.mkdtemp(prefix="trust-ramp-")
_n = [0]


def write(text):
    _n[0] += 1
    p = os.path.join(TMP, f"ledger-{_n[0]}.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def entries_at(rung, n, outcome="clean", start=1, date="2026-08-01"):
    out = []
    for i in range(start, start + n):
        out.append(f"## task-{rung}-{i} — {rung} — {date}\n"
                   f"**Outcome:** {outcome}\n")
    return "\n".join(out)


def run(argv, text=None, path=None):
    """-> (rc, ledger text after the call). Pins `today` for determinism."""
    p = path or write(text)
    real, tr.datetime.date = tr.datetime.date, _FrozenDate
    try:
        rc = tr.main(["--file", p] + argv)
    finally:
        tr.datetime.date = real
    with open(p, encoding="utf-8") as fh:
        return rc, fh.read(), p


class _FrozenDate(datetime.date):
    @classmethod
    def today(cls):
        return TODAY


print("\n== parsing ==")

st, es = tr.parse(ledger(entries=entries_at("R0", 3)))
check("parses state + entries", st["current_rung"] == "R0" and len(es) == 3,
      f"{st} / {len(es)}")

try:
    tr.parse(ledger(entries="## t1 — R0 — 2026-08-01\n**Notes:** hi\n"))
    check("blank outcome is fatal", False, "no LedgerError raised")
except tr.LedgerError as e:
    check("blank outcome is fatal", "does not count toward any gate" in str(e),
          str(e))

try:
    tr.parse(ledger(entries="## t1 — R0 — 2026-08-01\n**Outcome:** fine\n"))
    check("unknown outcome is fatal", False, "no LedgerError raised")
except tr.LedgerError as e:
    check("unknown outcome is fatal", "expected one of" in str(e), str(e))

try:
    tr.parse("# t\n\nno state block here\n")
    check("missing state block is fatal", False, "no LedgerError raised")
except tr.LedgerError as e:
    check("missing state block is fatal", "STATE" in str(e), str(e))

# Protocol-format compatibility: the mode-selection.md fields must survive.
st, es = tr.parse(ledger(entries=(
    "## t1 — R0 — 2026-08-01\n**Recommendation:** loop\n"
    "**Chosen:** goal-supervised\n**Felt right?** yes\n"
    "**Outcome:** clean\n")))
check("protocol mode-selection fields are preserved, not rejected",
      es[0]["fields"].get("recommendation") == "loop"
      and es[0]["fields"].get("felt right?") == "yes"
      and es[0]["outcome"] == "clean", str(es[0]["fields"]))


print("\n== gates refuse ==")

rc, _, _ = run(["promote"], ledger(entries=entries_at("R0", 9)))
check("R0->R1 refused at 9/10 entries", rc == 2, f"rc={rc}")

rc, _, _ = run(["promote"], ledger(entries=entries_at("R0", 10)))
check("R0->R1 granted at 10/10 clean", rc == 0, f"rc={rc}")

# 10 entries, but the streak is broken by a `corrected` two from the end.
broken = entries_at("R0", 8) + "\n" + \
    "## task-R0-9 — R0 — 2026-08-01\n**Outcome:** corrected\n" + \
    "\n## task-R0-10 — R0 — 2026-08-01\n**Outcome:** clean\n"
rc, _, _ = run(["promote"], ledger(entries=broken))
check("count met but streak broken -> refused", rc == 2, f"rc={rc}")

# `corrected` resets the streak but must not demote.
rc, out, _ = run(["log", "--task", "x", "--outcome", "corrected"],
                 ledger(rung="R1", entries=entries_at("R0", 10)))
st, _ = tr.parse(out)
check("corrected does not demote", rc == 0 and st["current_rung"] == "R1",
      st["current_rung"])

# R1->R2 needs the attestation on top of the counts.
r1 = ledger(rung="R1", entries=entries_at("R1", 20))
rc, _, _ = run(["promote"], r1)
check("R1->R2 refused without goal-condition-review attestation", rc == 2,
      f"rc={rc}")
rc, out, _ = run(["promote"], ledger(rung="R1", attests="goal-condition-review",
                                     entries=entries_at("R1", 20)))
check("R1->R2 granted once attested", rc == 0, f"rc={rc}")

# R2->R3 additionally needs 28 calendar days at R2.
young = ledger(rung="R2", entered="2026-08-20", attests="subramp-9-7",
               entries=entries_at("R2", 20))
rc, _, _ = run(["promote"], young)
check("R2->R3 refused at 12 days (needs 28)", rc == 2, f"rc={rc}")
old = ledger(rung="R2", entered="2026-07-01", attests="subramp-9-7",
             entries=entries_at("R2", 20))
rc, _, _ = run(["promote"], old)
check("R2->R3 granted at 62 days", rc == 0, f"rc={rc}")

rc, _, _ = run(["promote"], ledger(rung="R3", entries=entries_at("R2", 20)))
check("promote at top rung exits 2", rc == 2, f"rc={rc}")


print("\n== rung isolation ==")

# Work logged at R1 must not retroactively satisfy the R0->R1 gate.
rc, _, _ = run(["promote"], ledger(entries=entries_at("R1", 20)))
check("higher-rung entries do not earn a lower promotion", rc == 2, f"rc={rc}")


print("\n== demotion ==")

import contextlib
import io

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    rc, out, _ = run(["log", "--task", "bad", "--outcome", "harmful"],
                     ledger(rung="R2", entered="2026-08-01",
                            entries=entries_at("R1", 20)))
st, _ = tr.parse(out)
check("harmful demotes one rung", rc == 0 and st["current_rung"] == "R1",
      st["current_rung"])
check("demotion resets rung_entered to the entry date",
      st["rung_entered"] == TODAY.isoformat(), st["rung_entered"])
check("demotion is announced on stdout, not silent",
      "DEMOTED R2 -> R1" in _buf.getvalue(), _buf.getvalue())

rc, out, _ = run(["log", "--task", "bad", "--outcome", "harmful"],
                 ledger(rung="R0"))
st, _ = tr.parse(out)
check("harmful at R0 does not underflow", rc == 0
      and st["current_rung"] == "R0", st["current_rung"])

# A harmful entry inside the trailing window blocks re-promotion even once
# the streak rebuilds past the consecutive-clean bar.
poisoned = ("## t0 — R0 — 2026-08-01\n**Outcome:** harmful\n\n"
            + entries_at("R0", 9, start=2))
rc, _, _ = run(["promote"], ledger(entries=poisoned))
check("harmful inside the trailing-10 window blocks promotion", rc == 2,
      f"rc={rc}")


print("\n== append + duplicate guard ==")

rc, out, path = run(["log", "--task", "t1", "--outcome", "clean",
                     "--notes", "first"], ledger())
check("log appends an entry", rc == 0 and "## t1 — R0 —" in out
      and "**Notes:** first" in out)
rc2, out2, _ = run(["log", "--task", "t1", "--outcome", "clean"], path=path)
check("duplicate task id at the same rung is refused", rc2 == 2, f"rc={rc2}")


print("\n== check: tamper detection ==")

# The declared rung must be earned by the entries, not by editing the header.
rc, _, _ = run(["check"], ledger(rung="R2", entries=entries_at("R1", 3)))
check("hand-edited rung fails check", rc == 1, f"rc={rc}")

rc, _, _ = run(["check"], ledger(rung="R1", attests="",
                                 entries=entries_at("R0", 10)))
check("earned rung passes check", rc == 0, f"rc={rc}")

rc, _, _ = run(["check", "--rung", "R2"],
               ledger(rung="R1", entries=entries_at("R0", 10)))
check("check --rung above the earned rung is denied", rc == 1, f"rc={rc}")

rc, _, _ = run(["check", "--rung", "R0"],
               ledger(rung="R1", entries=entries_at("R0", 10)))
check("check --rung below the earned rung is allowed", rc == 0, f"rc={rc}")

rc, _, _ = run(["check"], ledger(rung="R0"))
check("R0 always passes check (no gate below it)", rc == 0, f"rc={rc}")


print("\n== attestations ==")

rc, out, _ = run(["attest", "goal-condition-review"], ledger())
st, _ = tr.parse(out)
check("attest records into the state block",
      rc == 0 and "goal-condition-review" in st["attestations"],
      str(st["attestations"]))
rc, _, _ = run(["attest", "not-a-real-gate"], ledger())
check("unknown attestation is refused", rc == 2, f"rc={rc}")


print("\n== status + shipped ledger ==")

rc, _, _ = run(["status"], ledger(entries=entries_at("R0", 4)))
check("status exits 0", rc == 0, f"rc={rc}")

rc, _, _ = run(["status"], ledger(rung="R3", entries=entries_at("R2", 20)))
check("status at the top rung exits 0", rc == 0, f"rc={rc}")

with open(SHIPPED, encoding="utf-8") as fh:
    shipped = fh.read()
st, es = tr.parse(shipped)
check("shipped .claude/trust-ramp.md parses", True)
check("shipped ledger starts at R0", st["current_rung"] == "R0",
      st["current_rung"])
# [X-51 session] This used to assert `es == []`, i.e. "no entries yet". That was
# a pin on the ledger never having been USED, so it was guaranteed to fail the
# first time it was, which is not a defect worth a red suite. What is worth
# pinning is that the shipped ledger still PARSES and that its size does not
# drift silently - the same reason the differential pins its open-row count.
# Backfilled 2026-08-11 with the seven runs of that session, +1 on 2026-08-12
# for PR #64's adversarial review; DW-A2 makes one run one entry, so this
# number moves only when real work is logged.
# +5 on 2026-08-13 for the X-52 session: three dynamic-workflow review rounds
# (one of which returned SIX nulls and is logged as a run that did not run,
# because §5 makes an uncounted null indistinguishable from a clean result) and
# two solo blocks, X-52's fix and X-49's cost re-measurement. Logged late - the
# session ran nine commits and four workflows before any entry was written,
# which is the same omission 9041acf exists to correct.
# +1 on 2026-08-13 for x52-lastw-array-phase: the array-phase half of X-52's
# memo guard, found by reading the unreviewed tail rather than by any test.
# Graded `corrected` on the day, then RE-GRADED `harmful` in c341775: the
# vocabulary defines `corrected` as "nothing wrong reached the tree", and
# b1fcc85 reached the tree, origin AND PR #65. Same argument as the
# x49-cost-veto-superseded re-grade; the contest is settled, not owed.
# +1 for x52-tail-review-and-corrections: six adversarial review rounds and the
# corrections they forced. Graded `harmful` for the PUBLICATION-STATE error -
# a live bypass sat in an open, mergeable PR while this session asserted
# nothing was pushed - not for any of the code.
# +1 for x52-merge-prep-review: three adversarial merge-readiness rounds over
# PR #65. Graded `harmful` for a RATE - each of three correction commits put
# new false claims into the record and the next round found them - not for any
# code. No gate-logic finding survived refutation in any round.
# +1 for post-x52-docs-reassessment: merged PR #65, then re-based the readiness
# analysis and the security KB onto it. Graded `harmful` -- it was logged `clean`
# and RE-GRADED in 49b8924, because its own completeness claim ("four documents")
# was false and the sweep behind it had left the retracted sentence live in
# EMITTED code. Keep this comment in step with the ledger; a stale grade
# description here is what a previous round caught.
# 26th entry 2026-08-14: v280-lit-fold-release, harmful (the merged 2.8.0
# changelog misattributed the X-52 line to PR #66; corrected in fc37aaa).
# 27th entry 2026-08-14: pr68-record-review-and-merge, harmful (the PR #68
# body certified the diffs "derived, not asserted" BEFORE the review ran;
# the review then found two underived provenance claims in them — the
# defects themselves were fixed pre-merge and never reached main).
# 28th entry 2026-08-14: x54-headclass-measurement, harmful (the head-class
# pass itself is sound, but PR #70's body argued its central claim from the
# WRONG ARTIFACT — gates.py, which was not what was timed — and two commits
# carrying that plus a probe-vs-fixture hook count and a fail-open overclaim
# were pushed to origin; all fixed pre-merge, none reached main).
# 29th entry 2026-08-14: prd-filename-rename, corrected (I reverted the
# operator's deliberate uncommitted rename; preserved rather than deleted, and
# nothing wrong reached origin — the lesson is now E6 in the readiness runbook).
# 30th entry 2026-08-14: readiness-harness, corrected (a 50-agent review of my
# own design found the loop self-merging, which the rung table forbids at EVERY
# rung, and R0's grant mis-stated; both fixed pre-commit, both recommended to
# the operator in their wrong form first).
# 32nd entry 2026-08-14: x37-class-b-attempt-1, harmful (the PR body reached
# origin with two false claims; the attempt itself was a net security
# regression and was withdrawn rather than merged).
# 31st entry 2026-08-14: c1-license, corrected (readiness C-1 CLOSED — the
# first finding this cycle fixed rather than re-measured; graded `corrected`
# because the plan review found six defects in the plan, one of which would
# have rewritten history that is true of the shas it names).
# 33rd entry 2026-08-16: b1b-fence-pins, corrected (pinned the item-1b
# false-positive fence, which did not exist at all; graded `corrected` because
# six of the ten blocking/confirmed review findings were false claims of mine,
# one of which would have pinned a fetch-then-execute shape as a permanent
# `allow` — the exact inversion the item exists to prevent — and all six were
# caught before merge).
# 34th entry 2026-08-16: sdk-pipe-trigger-redos, clean (a FINDING, filed, not
# an implementation: `_PIPE_TO_SHELL` backtracks exponentially at exactly 2.00x
# per prefix token, 134 bytes crosses the SDK's 60 s timeout while the shell
# denies in 0.03 s, and both prototype fixes were measured DEAD).
# 35th entry 2026-08-17: sdk-pipe-trigger-redos-correction, harmful (entry 34's
# blast-radius claim reached main and was false -- `_INSTALL_HEAD` is vulnerable
# too, and the reachable attack needs no downloader, no pipe and no
# substitution: 133 bytes of ordinary words, zero jump bytes, 102.32 s).
# 36th entry 2026-08-19: sdk-pipe-trigger-redos-fix, harmful (the fix for
# entries 34/35 landed -- PR #81, merge 897d427 -- and the PR body reached
# origin carrying four false claims, while the fix loop DIVERGED, 12 findings
# at i=1 against 16 at i=2, and the operator intervened to strip the branch
# back to its mechanically-verified core. Both limbs of `harmful`, not one.)
# 39th entry 2026-08-22: prefix-run-cost-residuals-2, harmful (PR #87, merge
# 96cc730. Both limbs. Something wrong reached origin -- a 282-row pin whose
# headline property was generalised from a five-character sample I chose, where
# `|` and `$` move ZERO rows and 27 of the 282 pin nothing; a body block with 13
# claims a re-review confirmed false; a reviewer's figure quoted as my own; a
# title asserting "linear" the tree's own exponents refute -- AND the operator
# intervened three times: strip after E2, repair-before-merge, then drop the
# narrowing. The fix loop diverged for the third time on this line, 13 confirmed
# and all 13 new on my own fix. What merged is the `_ckey` half only, shell-only,
# with gates.py byte-identical to the parent.)
# 40th entry 2026-08-24: pipe-rule-url-pipe-cubic, harmful (PR #90). Worked to
# step 4, shipped NO FIX, filed four residuals -- and the WORK is not what earns
# the grade. False claims reached ORIGIN twice: in the closeout, and again in the
# commit correcting it. The fix loop then hit E2 (4 confirmed, then 9 with eight
# new on the fix), and what ended it was the operator ruling "keep only what
# survived review" -- a STRIP, which is the only thing that has ever ended a fix
# loop on this line. What survived: the candidate is refuted, its bash half pays
# (1.6139 s vs the shipped term's 0.0872 s), and the SEGMENTED form is UNSOUND
# because _redirect_norm maps `|&` -> `|` and the rule searches it among five
# derived strings, so a raw-string segmenter reads 21 on a payload costing
# 60.191 s at 17,645 B with the guard passing. What was DELETED rather than
# re-derived: every benign-separation number, because four attempts scored four
# corpora under four predicates and two were faulted; and every count of the
# unpinned downloader shapes, because two published counts were wrong in three
# days and both were inherited rather than derived. The method lesson is one
# sentence -- A CORRECTION IS A CLAIM AND NEEDS THE SAME SWEEP THE ORIGINAL
# NEEDED -- with two instruments to distrust: sorting by one column and reading a
# property off another is not a sweep, and a corpus scored for headroom must
# first be filtered by what the code already rejects.
# 41st entry 2026-08-25: prefix-run-assignment-wrapper-overlap, harmful
# (PR #92, merge abe3f48). The best technical result on this line and still
# `harmful`: four false claims are permanently on `main` in 3c3c11b's commit
# message, and the merge shipped with 10 confirmed findings open on an
# explicit operator ruling, 9a's criterion stated as UNMET. The defect was on
# TWO arms, not the one the row named -- the one-arm candidate measured
# 14.01 s where the parent measures 14.03 s -- and the first spelling emitted
# 81 null alternatives a conforming ERE engine rejects outright. Both came
# from review, not from me. Fourth divergence on this line, and the sharper
# lesson: A ROUND THAT ALSO ADDS CODE IS NOT A SUBTRACTION ROUND -- six of ten
# MAJOR/BLOCKER findings were on the guards the round added, and a reviewer's
# prescription is still a claim.
# +1 on 2026-08-26 for x54-deny-shape: the MEASUREMENT item that demonstrates
# X-54's fail-open with a would-otherwise-DENY payload (PR #94, merge 69395f1),
# graded `corrected` -- the item's own step-7 review caught two record defects
# in the first commit (a :3937->:3941 line citation and a :3954-only hot-site
# attribution) and both were fixed before any push, so nothing wrong reached
# origin. Moving this pin IS the "pin moved in the same commit" the runbook's
# step 10b requires; a new ledger entry with the pin left at 41 is a red suite.
# +1 on 2026-08-27 for c2-autonomous-dispatch: resolution (b) STOP ADVERTISING
# (PR #96, merge 75eef0a) — the C-2 readiness leg retired by DISCLOSURE, graded
# `corrected` (a one-clause "every surface" overclaim self-caught by the step-7
# review and fixed before push). The runbook's step-10b "pin moved in the same
# commit".
# +1 on 2026-08-31 for x54-completer-cost: the completer member of the X-54 cost
# class closed (PR #98, merge 8cc107f, freeze exception 77), graded `harmful` --
# four correction commits each pushed false claims to ORIGIN and all four are
# merged into main. THE CODE WAS AT FAULT TOO: this comment used to say "the
# code was never at fault; every defect in every round was in prose", which is
# the exact sentence `.claude/trust-ramp.md` in this same commit retracts --
# removing the per-completer HEAD test shipped a head-BEARING fail-open on
# `main`. The runbook's step-10b "pin moved in the same commit".
check("shipped ledger parses to the expected number of entries",
      len(es) == 44, f"{len(es)} entries")

# [x54-completer-cost closeout] PIN THE GRADE, NOT ONLY THE COUNT. The count
# above catches a DELETED entry and nothing else: mutating this entry's
# `**Outcome:** harmful` to `clean` passes this suite 39/0, measured 2026-09-08.
# For an item whose entire product IS the grade -- the whole point of the
# close-out is that x54-completer-cost shipped a fail-open and is graded harmful
# -- an unpinned outcome is the same defect this repo keeps finding: a record
# that agrees with itself while the load-bearing claim is free to move.
# Consistent with the standing finding "pin SHAPE, never COST": this pins the
# shape of the verdict, not any number attached to it.
_x54 = [e for e in es if e.get("task") == "x54-completer-cost"]
check("the x54-completer-cost ledger entry still carries its `harmful` grade",
      len(_x54) == 1 and _x54[0].get("outcome") == "harmful",
      f"    matched {len(_x54)} entries, outcome "
      f"{_x54[0].get('outcome') if _x54 else None!r}; an entry that loses its "
      "grade makes the whole close-out assert nothing")
check("every shipped entry carries an outcome the vocabulary knows",
      all(e["outcome"] in ("clean", "corrected", "harmful") for e in es),
      str([e["outcome"] for e in es]))
# A blank `**Outcome:**` is a hard parse error by design (the ramp must measure
# evidence, not logging diligence), so this also proves none was written blank.
check("the shipped ledger's declared rung is what its entries earn",
      st["current_rung"] == "R0", st["current_rung"])
check("every gate's rungs are known",
      all(g["from_rung"] in tr.RUNGS for g in tr.GATES.values()))
check("every rung above R0 has a gate",
      set(tr.GATES) == set(tr.RUNGS[1:]),
      f"{set(tr.GATES)} vs {set(tr.RUNGS[1:])}")
check("bin/trust-ramp is executable", os.access(SCRIPT, os.X_OK))

shutil.rmtree(TMP, ignore_errors=True)

print("\n== the mutation gate exists and its sets still bind (runbook step 4b) ==")

# [2026-09-08] Only checks that can actually GO RED live here. A check that
# asserts a sentence appears in a prose file cannot survive a line wrap, and
# this repo has already shipped pins that passed while the thing they guarded
# was gone. These four run the artifact instead.
_GATE = os.path.join(ROOT, ".claude", "mutation-gate.py")
_MUTDIR = os.path.join(ROOT, ".claude", "mutations")
check("the mutation gate is present and executable",
      os.path.isfile(_GATE) and os.access(_GATE, os.X_OK),
      f"    {_GATE}")
# [2026-09-09 round-6] PIN THE GATE'S CONTENT, not just its existence. isfile +
# X_OK was the ONLY automatic assertion about this harness, so MEASURED at
# 8f93fd4: a 2-line stub printing the exact "MERGE GATE: PASS" banner, a
# ZERO-BYTE gate, and a gate with GUARD 10 deleted each left the suite at 55/0
# and ./bin/run-tests at 25 suites / 9862 checks / 0 failed. Nothing else in CI
# refers to the gate. Editing it now means updating this hash in the same
# commit, which is the review surface the pin exists to create.
import hashlib as _hl
_GATE_SHA = "e25263ddac9781953b43f41d0332d66098d9cb3d9f4edc1496ab34e40a0a64a8"
try:
    with open(_GATE, "rb") as _fh:
        _gsha = _hl.sha256(_fh.read()).hexdigest()
except OSError as _e:
    _gsha = f"unreadable: {_e!r}"
check("the mutation gate's content matches its pin",
      _gsha == _GATE_SHA,
      f"    got {_gsha}, pinned {_GATE_SHA}. If you edited the gate on "
      "purpose, update _GATE_SHA in the same commit.")
# [2026-09-08 review blocker 3] These names are PINNED, not discovered. The
# first version did `os.listdir(_MUTDIR)` and generated a check per file found
# -- so deleting a set deleted its own checks and the suite went 44/0 GREEN
# with the guard's entire bypass list gone. A check derived from the thing it
# checks enforces nothing. Adding a set means adding its name here, on purpose.
# [2026-09-09 re-review fixes D and E] The pin now names the BYPASSES, not just
# the file. Two measured defects in the 2026-09-08 version:
#   D  it narrowed the anti-rot loop to pinned names, so a set ADDED without
#      editing this list got ZERO anchor checking. Measured: a new set whose
#      anchor matched nothing at all left the suite at 46 passed, 0 failed.
#   E  it pinned the FILENAME only, so the file could stay and be gutted.
#      Measured: deleting 3 of x54's 4 enumerated bypasses -> 46 passed, 0 failed.
# Removing a bypass now means editing this list in the same commit, which is
# the review surface the pin exists to create. Anti-rot runs over every set
# PRESENT, so an unregistered set is still anchor-checked.
# [2026-09-09 round-4] The pin also records WHICH ids are controls, the set's
# digest_suites, and its expect-key union -- because the gate derives a
# control's jury from exactly those, and all three are author-supplied. MEASURED
# at 756c95e and again after round 3: flipping a live bypass to "control": true
# and either dropping the only catching suite from every expect map, or naming
# that suite in digest_suites, makes a REAL bypass score CONTROL-OK and the gate
# print MERGE GATE: PASS at rc 0 -- while this suite stayed at 49 passed, 0
# failed. Pinning ids alone could not see it: a variant that preserved all five
# ids laundered two bypasses silently. These four facts are what a reviewer
# would have to be shown to be fooled, so they are the four that get pinned.
_REQUIRED_SETS = {
    "int-word-clamp-sufficiency.json": {
        "sha256": "1cef5393e99c0893a206f01c3fba511b"
                  "6cb14fb54ed50b51ae2def4713f4446b",
        "bypasses": ["clamp-undone"],
        "controls": ["control-inert-docstring"],
        "digest_suites": ["test_greenfield_golden.py"],
        "suites": ["test_greenfield_golden.py", "test_issue_fixes.py",
                   "test_retrofit.py"],
    },
    "x54-head-bearing-early-stop.json": {
        "sha256": "debd1c68f08c29c01f4815d35ae612a4"
                  "d9f773e9b4b8d885a942d2f60e1f788d",
        "bypasses": ["threshold-raised", "probe-defanged",
                     "probe-skipped-continue", "stops-too-soon-break"],
        "controls": ["control-inert-comment"],
        "digest_suites": ["test_greenfield_golden.py", "test_retrofit.py"],
        "suites": ["test_composition.py", "test_hook_behavior.py"],
    },
}
# [2026-09-09 round-7] Walk, and do not filter by extension. `os.listdir` plus
# `endswith(".json")` made a set INVISIBLE to both this check and anti-rot if it
# was named *.JSON, had no extension, or sat in a subdirectory -- measured: three
# such copies produced ZERO checks between them. Anything under .claude/mutations
# is a mutation set and must be registered.
_present = []
if os.path.isdir(_MUTDIR):
    for _root, _dirs, _files in os.walk(_MUTDIR):
        for _f in _files:
            _present.append(os.path.relpath(os.path.join(_root, _f), _MUTDIR))
_present = sorted(_present)
_missing = [n for n in _REQUIRED_SETS if n not in _present]
check("every REQUIRED mutation set is present",
      not _missing,
      f"    missing {_missing}; present {_present}. A set is removed only by "
      "removing its name from _REQUIRED_SETS in the same commit, which is the "
      "review surface this pin exists to create.")
# Anti-rot covers everything actually on disk, not just what is registered.
_sets = _present
_unregistered = [n for n in _present if n not in _REQUIRED_SETS]
check("every mutation set on disk is registered in _REQUIRED_SETS",
      not _unregistered,
      f"    {_unregistered} present but unregistered. An unregistered set has "
      "no pinned bypass list, so its rows can be deleted without a reviewable "
      "diff. Add it to _REQUIRED_SETS with its mutation ids.")

# ANTI-ROT, and this is the check with no equivalent anywhere else in the
# suite: re-bind every `find` string against its target IN-PROCESS. When a
# guard is refactored, its bypass list silently stops describing it -- the pins
# stay green, the behavioural rows stay green, and only this goes red.
import json as _json
for _name in _sets:
    try:
        _spec = _json.load(open(os.path.join(_MUTDIR, _name), encoding="utf-8"))
        _tgt = open(os.path.join(ROOT, _spec["target"]), encoding="utf-8").read()
        # [2026-09-09 re-review fix G] The 2026-09-08 try covered only parse and
        # IO. A JSON-valid but STRUCTURALLY malformed set -- no "mutations" key,
        # a mutation missing "find" or "id", "mutations" not a list -- still
        # raised out of the comprehension below and killed the whole suite with
        # no count. Force the structural access inside the try.
        _muts = _spec["mutations"]
        if not isinstance(_muts, list) or not _muts:
            raise ValueError("'mutations' must be a non-empty list")
        _ids = [m["id"] for m in _muts]
        _finds = [m["find"] for m in _muts]
    except Exception as _e:
        # A traceback here would kill the whole suite inside bin/run-tests and
        # report NO count at all, which reads as infrastructure noise rather
        # than as a failure. Fail as a CHECK instead.
        check(f"{_name}: parses and is structurally well formed", False,
              f"    {_e!r}")
        continue
    # [2026-09-09 re-review fix E] Pin the BYPASS LIST, not just the filename.
    if _name in _REQUIRED_SETS:
        _pin = _REQUIRED_SETS[_name]
        # [2026-09-09 round-6] PIN THE SET'S CONTENT. The pins below cover the
        # set's METADATA -- ids, which are controls, digest_suites, the
        # expect-key union -- but not `find`, `replace`, or the check-name
        # VALUES in expect. MEASURED at 8f93fd4: with every one of those pinned
        # facts intact, all four x54 bypasses were swapped for whitespace-only
        # no-ops and the suite stayed 55/0 WHILE THE GATE ITSELF printed
        # "MERGE GATE: PASS - 4/4 bypasses turn a NAMED check red" at rc 0,
        # with the real guard byte-untouched. A content hash is the only pin
        # that cannot be satisfied by a differently-shaped lie.
        with open(os.path.join(_MUTDIR, _name), "rb") as _fh:
            _ssha = _hl.sha256(_fh.read()).hexdigest()
        check(f"{_name}: content matches its pin",
              _ssha == _pin["sha256"],
              f"    got {_ssha}, pinned {_pin['sha256']}. Every field a set "
              "declares steers what the gate measures; changing any of them "
              "means updating this hash in the same commit.")
        _want_ids = sorted(_pin["bypasses"] + _pin["controls"])
        _gone = [i for i in _want_ids if i not in _ids]
        _extra = [i for i in _ids if i not in _want_ids]
        check(f"{_name}: every pinned bypass is still declared",
              not _gone and not _extra,
              f"    missing {_gone}; unregistered {_extra}. The set file can be "
              "gutted without deleting it; this is the check that notices. "
              "Changing the bypass list means editing _REQUIRED_SETS too.")
        # [round-4] WHICH ids are controls, and the two author-supplied inputs
        # the gate derives a control's jury from.
        _is_ctl = sorted(m["id"] for m in _muts if m.get("control"))
        check(f"{_name}: exactly the pinned mutations are controls",
              _is_ctl == sorted(_pin["controls"]),
              f"    controls are {_is_ctl}, pinned {sorted(_pin['controls'])}. "
              "Flipping a live bypass to a control makes the gate score it "
              "CONTROL-OK and report PASS; that must be a reviewable diff.")
        _dg = sorted(_spec.get("digest_suites", []))
        check(f"{_name}: digest_suites is unchanged",
              _dg == sorted(_pin["digest_suites"]),
              f"    {_dg}, pinned {sorted(_pin['digest_suites'])}. A behavioural "
              "suite listed here is subtracted from the control's jury, which "
              "is one array entry away from a false PASS.")
        _union = sorted({s for m in _muts for s in (m.get("expect") or {})})
        check(f"{_name}: the expect-suite union is unchanged",
              _union == sorted(_pin["suites"]),
              f"    {_union}, pinned {sorted(_pin['suites'])}. The gate derives "
              "both the baseline and the control's jury from this union; "
              "narrowing it silently shrinks what the control had to escape.")
    _bad = [(m["id"], _tgt.count(m["find"])) for m in _muts
            if _tgt.count(m["find"]) != 1]
    check(f"{_name}: every anchor binds exactly once",
          not _bad,
          f"    {_bad} -- the guard moved out from under its own bypass list; "
          "re-derive the set against the current source, do not delete it")
    check(f"{_name}: declares a negative control",
          any(m.get("control") for m in _spec["mutations"]),
          "    a set with no control cannot distinguish 'all caught' from "
          "'these suites are red for any edit'")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

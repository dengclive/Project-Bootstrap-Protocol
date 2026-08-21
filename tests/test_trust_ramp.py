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
check("shipped ledger parses to the expected number of entries",
      len(es) == 38, f"{len(es)} entries")
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

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

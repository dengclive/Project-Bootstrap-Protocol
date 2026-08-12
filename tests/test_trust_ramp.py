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
check("shipped ledger parses to the expected number of entries",
      len(es) == 16, f"{len(es)} entries")
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

#!/usr/bin/env python3
"""R-2 (IC-1) — `synthesize --validate-only`.

Spec: .claude/specs/bootstrap-v2/requirements.md (AC-2-1..AC-2-3).
Exercises bin/bootstrap-interview as a subprocess (the seam §3.2 shape).

Run: python3 tests/test_validate_only.py
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

BIN = os.path.join(ROOT, "bin", "bootstrap-interview")

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


PRD = "# Demo Service\nA REST API service for managing widgets.\n"

# AC-2-3 mini-golden: sha256 of the no-flag synthesize output for the fixture
# PRD above (emit() body with the standard _finalize header). Verified at
# introduction to be byte-identical to the 1.9.0-era code path (HEAD-vs-
# worktree run, 2026-07-17). A change here means the DEFAULT synthesize
# path's bytes moved - that is an intentional-freeze-exception decision,
# never a drive-by re-baseline.
#
# [v2.4.0 code fold — TEL-01 wizard wiring] RE-BASELINED. The emitted
# bootstrap.config.yaml now carries the top-level `telemetry_export_enabled:
# false` line (the wizard-wired Phase 0 opt-in, default skip). This is the
# only byte change to the default synthesize output at this fold; recorded as
# a freeze exception, not a drive-by. Previous digest:
# 9f725b3f88f9b54eb1a0414dbc5e8e1a372a5c6049bb016119b4051b6113ac38.
def _run(args, cwd):
    return subprocess.run([sys.executable, BIN] + args, cwd=cwd,
                          capture_output=True, text=True)


def _mk_interview(d):
    open(os.path.join(d, "PRD.md"), "w").write(PRD)
    r = _run(["analyze", "--prd", "PRD.md", "-o", "iv.md"], d)
    assert r.returncode == 0, r.stderr
    return os.path.join(d, "iv.md")


# --------------------------------------------------------------------------- #
# AC-2-1: --validate-only on a valid interview: exit 0, no file written
# --------------------------------------------------------------------------- #
d = tempfile.mkdtemp()
try:
    _mk_interview(d)
    before = sorted(os.listdir(d))
    r = _run(["synthesize", "-i", "iv.md", "-o", "out.yaml",
              "--validate-only"], d)
    check("AC-2-1: valid interview exits 0", r.returncode == 0, r.stderr)
    check("AC-2-1: output path absent post-run",
          not os.path.exists(os.path.join(d, "out.yaml")))
    check("AC-2-1: no file of any kind written",
          sorted(os.listdir(d)) == before)
    check("AC-2-1: no violations on stderr", r.stderr.strip() == "")
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# AC-2-2: --validate-only on an invariant-violating interview: non-zero,
#          violation on stderr, nothing written
# --------------------------------------------------------------------------- #
d = tempfile.mkdtemp()
try:
    iv_path = _mk_interview(d)
    body = open(iv_path).read()
    # queue without loop|goal violates the resolve_config skip-policy
    # invariant (the loop/goal lines stay false in the generated block).
    assert "queue_mode_enabled: false" in body
    open(iv_path, "w").write(body.replace("queue_mode_enabled: false",
                                          "queue_mode_enabled: true"))
    before = sorted(os.listdir(d))
    r = _run(["synthesize", "-i", "iv.md", "-o", "out.yaml",
              "--validate-only"], d)
    check("AC-2-2: invalid interview exits non-zero", r.returncode != 0)
    check("AC-2-2: violation reported on stderr",
          "queue_mode" in r.stderr, repr(r.stderr))
    check("AC-2-2: output path absent post-run",
          not os.path.exists(os.path.join(d, "out.yaml")))
    check("AC-2-2: no file of any kind written",
          sorted(os.listdir(d)) == before)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# AC-2-3: absent the flag, synthesize is byte-identical to the 1.9.0 path.
# Locked as a mini-golden digest over the emitted config for the fixture
# PRD (see note above); plus flag-then-no-flag leaves the no-flag output
# unaffected (the flag branch has no side effects).
# --------------------------------------------------------------------------- #
EXPECTED_NOFLAG_SHA256 = \
    "798a30bf895ef7aa2a27295344a5ffeee501ad63e31ef7464675baf03b274b17"

d = tempfile.mkdtemp()
try:
    _mk_interview(d)
    r_flag = _run(["synthesize", "-i", "iv.md", "-o", "out.yaml",
                   "--validate-only"], d)
    r = _run(["synthesize", "-i", "iv.md", "-o", "out.yaml"], d)
    check("AC-2-3: no-flag synthesize exits 0", r.returncode == 0, r.stderr)
    body = open(os.path.join(d, "out.yaml")).read()
    got = hashlib.sha256(body.encode()).hexdigest()
    check("AC-2-3: no-flag output byte-identical to 1.9.0-era bytes "
          "(mini-golden)", got == EXPECTED_NOFLAG_SHA256,
          f"got {got}")
finally:
    shutil.rmtree(d, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

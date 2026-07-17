#!/usr/bin/env python3
"""R-1 (IC-3) — gate_substrate state field + pre-2.0.0 migration.

Spec: .claude/specs/bootstrap-v2/requirements.md (AC-1-1..AC-1-3).
The state file is an apply()-time artifact outside the golden surface
[SR-07], so coverage here is behavioral: real installs into a tmpdir via
bin/bootstrap-install.

Run: python3 tests/test_gate_substrate.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

BIN = os.path.join(ROOT, "bin", "bootstrap-install")
STATE_REL = os.path.join(".claude", ".bootstrap-state.json")
BACKUP_REL = os.path.join(".claude", ".bootstrap-state.json.pre-2.0.0")

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


CFG = """project:
  name: substrate-demo
  archetype: service
commands:
  test: "true"
  lint: "true"
"""


def _install(d):
    return subprocess.run([sys.executable, BIN, "-C", d],
                          capture_output=True, text=True)


# --------------------------------------------------------------------------- #
# AC-1-1: fresh install -> gate_substrate: "shell", no migration backup
# --------------------------------------------------------------------------- #
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(CFG)
    r = _install(d)
    check("AC-1-1: fresh install succeeds", r.returncode == 0, r.stderr)
    state = json.load(open(os.path.join(d, STATE_REL)))
    check("AC-1-1: fresh state has gate_substrate == 'shell'",
          state.get("gate_substrate") == "shell")
    check("AC-1-1: fresh install writes no .pre-2.0.0 backup",
          not os.path.exists(os.path.join(d, BACKUP_REL)))
    check("AC-1-1: version field alongside substrate field",
          state.get("bootstrap_protocol_version") == "2.0.0")
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# AC-1-2: install over a 1.x state file -> "shell" stamped, non-destructive
#          backup written once, pre-existing keys preserved
# --------------------------------------------------------------------------- #
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(CFG)
    _install(d)
    state_path = os.path.join(d, STATE_REL)
    # Rewrite the state file as a 1.9.0-era one: no gate_substrate, old
    # version, plus an operator-era key that migration must not lose.
    old_state = json.load(open(state_path))
    del old_state["gate_substrate"]
    old_state["bootstrap_protocol_version"] = "1.9.0"
    old_state["completed_phases"] = ["0", "1", "2"]
    pre_bytes = json.dumps(old_state, indent=2) + "\n"
    open(state_path, "w").write(pre_bytes)

    r = _install(d)
    check("AC-1-2: re-install over 1.x state succeeds", r.returncode == 0,
          r.stderr)
    state = json.load(open(state_path))
    check("AC-1-2: migrated state has gate_substrate == 'shell'",
          state.get("gate_substrate") == "shell")
    check("AC-1-2: migrated state version bumped to 2.0.0",
          state.get("bootstrap_protocol_version") == "2.0.0")
    check("AC-1-2: pre-existing keys preserved (non-destructive)",
          state.get("completed_phases") == ["0", "1", "2"])
    backup_path = os.path.join(d, BACKUP_REL)
    check("AC-1-2: .pre-2.0.0 backup written",
          os.path.exists(backup_path))
    check("AC-1-2: backup is byte-identical to the pre-migration file",
          os.path.exists(backup_path)
          and open(backup_path).read() == pre_bytes)

    # Backup is written once: a further re-install must not clobber it.
    _install(d)
    check("AC-1-2: second re-install leaves the original backup untouched",
          open(backup_path).read() == pre_bytes)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# Review fix (finding 3): a CORRUPT pre-2.0.0 state file is still backed
# up (raw bytes) before the migration rewrites it - the corrupt-file case
# is exactly what a non-destructive backup exists for.
# --------------------------------------------------------------------------- #
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(CFG)
    _install(d)
    state_path = os.path.join(d, STATE_REL)
    corrupt = '{"bootstrap_protocol_version": "1.9.0", "completed_pha'
    open(state_path, "w").write(corrupt)          # truncated mid-write
    os.remove(os.path.join(d, BACKUP_REL)) if os.path.exists(
        os.path.join(d, BACKUP_REL)) else None
    r = _install(d)
    check("corrupt-state: re-install over a corrupt state file succeeds",
          r.returncode == 0, r.stderr)
    backup_path = os.path.join(d, BACKUP_REL)
    check("corrupt-state: .pre-2.0.0 backup written with the raw corrupt "
          "bytes", os.path.exists(backup_path)
          and open(backup_path).read() == corrupt)
    state = json.load(open(state_path))
    check("corrupt-state: rewritten state is valid with gate_substrate "
          "'shell'", state.get("gate_substrate") == "shell"
          and state.get("bootstrap_protocol_version") == "2.0.0")
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# AC-1-3: the writer never emits "sdk-callable" in Milestone A. There is no
# code path that can produce it: assert the literal appears in no write
# statement in lib/installer.py (Milestone B replaces this source-level
# tripwire with the lib/ic_checks.py gate test).
# --------------------------------------------------------------------------- #
src = open(os.path.join(ROOT, "lib", "installer.py")).read()
writes = [ln for ln in src.splitlines()
          if '"sdk-callable"' in ln and not ln.lstrip().startswith("#")]
check("AC-1-3: no non-comment 'sdk-callable' literal in installer source",
      writes == [], repr(writes))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

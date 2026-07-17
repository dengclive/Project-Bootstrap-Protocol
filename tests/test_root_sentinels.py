#!/usr/bin/env python3
"""R-4 (IC-2) — root-sentinel dual-honor + root .gitignore managed block.

Spec: .claude/specs/bootstrap-v2/requirements.md (AC-4-1..AC-4-5).
Root <project>/.halt (graceful) and <project>/.halt-hard (immediate exit,
wrapper never signals in-flight `claude -p`) are honoured by all three
wrappers IN ADDITION to the legacy .claude/queue/.halt/.resume. Dual-honor
is permanent. The gitignore home is owner decision (a): a marker-delimited
managed block in the project-root .gitignore.

Run: python3 tests/test_root_sentinels.py
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

from templates import (GITIGNORE_BLOCK_BEGIN,       # noqa: E402
                       GITIGNORE_BLOCK_END, TEMPLATES)

BIN = os.path.join(ROOT, "bin", "bootstrap-install")

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


FULL = """project:
  name: sentinels
  archetype: ai-agent
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: true
principles:
  tdd_policy: required
commands:
  test: "true"
  lint: "true"
"""

SERVICE = """project:
  name: plain
  archetype: service
"""


def _install(d, cfg=FULL):
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(cfg)
    return subprocess.run([sys.executable, BIN, "-C", d],
                          capture_output=True, text=True)


def _run_wrapper(d, script, *args):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = d
    return subprocess.run(["bash", os.path.join(d, ".claude", script),
                           *args], capture_output=True, text=True, env=env)


WRAPPERS = [("loop.sh", ["t1"]), ("goal-loop.sh", ["t1"]), ("auto.sh", [])]

d = tempfile.mkdtemp()
try:
    r = _install(d)
    assert r.returncode == 0, r.stderr

    # ----------------------------------------------------------------- #
    # AC-4-1: root .halt -> each wrapper stops at its next boundary
    # (for the guarded skeletons, the boundary is startup).
    # ----------------------------------------------------------------- #
    open(os.path.join(d, ".halt"), "w").write("")
    for script, args in WRAPPERS:
        r = _run_wrapper(d, script, *args)
        check(f"AC-4-1: {script} refuses under root .halt",
              r.returncode != 0 and "Halt sentinel present" in r.stderr,
              f"rc={r.returncode} stderr={r.stderr!r}")
    os.remove(os.path.join(d, ".halt"))

    # ----------------------------------------------------------------- #
    # AC-4-2: root .halt-hard -> immediate exit; no signal to claude -p
    # ----------------------------------------------------------------- #
    open(os.path.join(d, ".halt-hard"), "w").write("")
    for script, args in WRAPPERS:
        r = _run_wrapper(d, script, *args)
        check(f"AC-4-2: {script} exits immediately under root .halt-hard",
              r.returncode != 0 and "Hard-halt sentinel present" in r.stderr,
              f"rc={r.returncode} stderr={r.stderr!r}")
        body = open(os.path.join(d, ".claude", script)).read()
        import re
        # `kill -0` is exempt: signal 0 sends nothing - it is the Phase 9.7
        # PID-liveness probe ("e.g., kill -0 <pid> on POSIX"), not a signal.
        kill_lines = [ln for ln in body.splitlines()
                      if re.search(r"(?<![\w-])(kill|pkill|killall)\b",
                                   ln.split("#")[0])
                      and not re.search(r"(?<![\w-])kill\s+-0\b",
                                        ln.split("#")[0])]
        check(f"AC-4-2: {script} never signals processes "
              f"(no signal-sending kill in body)", kill_lines == [],
              repr(kill_lines))
    check("AC-4-2: hard-halt exit leaves no claim sentinel behind",
          not any(f.startswith((".loop-active", ".goal-active"))
                  for f in os.listdir(os.path.join(d, ".claude",
                                                   "sessions"))))
    check("AC-4-2: hard-halt exit leaves no queue .run-active",
          not os.path.exists(os.path.join(d, ".claude", "queue",
                                          ".run-active")))
    os.remove(os.path.join(d, ".halt-hard"))

    # ----------------------------------------------------------------- #
    # AC-4-3: legacy queue-scoped .halt still works unchanged
    # ----------------------------------------------------------------- #
    qhalt = os.path.join(d, ".claude", "queue", ".halt")
    open(qhalt, "w").write("")
    for script, args in WRAPPERS:
        r = _run_wrapper(d, script, *args)
        check(f"AC-4-3: {script} still refuses under queue/.halt",
              r.returncode != 0 and "Halt sentinel present" in r.stderr,
              f"rc={r.returncode} stderr={r.stderr!r}")
    os.remove(qhalt)
    frag = open(os.path.join(d, ".claude", ".gitignore")).read()
    check("AC-4-3: queue/.halt + queue/.resume remain in the .claude "
          "ignore fragment",
          "queue/.halt" in frag and "queue/.resume" in frag)

    # Sanity: with no sentinel, auto.sh still runs its (skeleton) course.
    r = _run_wrapper(d, "auto.sh")
    check("sanity: auto.sh runs when no sentinel is present",
          r.returncode == 0, f"rc={r.returncode} stderr={r.stderr!r}")

    # ----------------------------------------------------------------- #
    # AC-4-5 fixture 1: fresh repo -> root .gitignore created with the
    # managed block; sentinels not committable by default.
    # ----------------------------------------------------------------- #
    gi_path = os.path.join(d, ".gitignore")
    check("AC-4-5(f1): root .gitignore created", os.path.exists(gi_path))
    gi = open(gi_path).read()
    check("AC-4-5(f1): file is exactly the managed block",
          gi == TEMPLATES["gitignore_root"]({}))
    check("AC-4-5(f1): block ignores /.halt and /.halt-hard",
          "/.halt\n" in gi and "/.halt-hard\n" in gi
          and gi.startswith(GITIGNORE_BLOCK_BEGIN)
          and GITIGNORE_BLOCK_END in gi)
    manifest = json.load(open(os.path.join(d, ".claude",
                                           ".installer-manifest.json")))
    entry = next(f for f in manifest["files"] if f["path"] == ".gitignore")
    check("AC-4-5(f1): wholly-authored file is digest-tracked normally",
          entry.get("kind") == "gitignore_root" and "digest" in entry
          and entry.get("state") is None)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------- #
# AC-4-5 fixture 2: pre-existing .gitignore with operator content ->
# block appended once, operator lines untouched, second install no-op.
# --------------------------------------------------------------------- #
d = tempfile.mkdtemp()
try:
    operator = "node_modules/\n*.log\n"
    open(os.path.join(d, ".gitignore"), "w").write(operator)
    r = _install(d)
    check("AC-4-5(f2): install over operator .gitignore succeeds",
          r.returncode == 0, r.stderr)
    gi = open(os.path.join(d, ".gitignore")).read()
    check("AC-4-5(f2): operator lines untouched", gi.startswith(operator))
    check("AC-4-5(f2): managed block appended once",
          gi.count(GITIGNORE_BLOCK_BEGIN) == 1
          and "/.halt-hard\n" in gi)
    manifest = json.load(open(os.path.join(d, ".claude",
                                           ".installer-manifest.json")))
    entry = next(f for f in manifest["files"] if f["path"] == ".gitignore")
    check("AC-4-5(f2): co-owned entry has managed-block state and NO "
          "whole-file digest",
          entry.get("state") == "managed-block-appended"
          and "digest" not in entry and "block_digest" in entry)

    before = gi
    r2 = _install(d)
    after = open(os.path.join(d, ".gitignore")).read()
    check("AC-4-5(f2): second install is a byte-level no-op",
          after == before)
    # Operator edits OUTSIDE the block never fire hand-edit warnings.
    open(os.path.join(d, ".gitignore"), "a").write("dist/\n")
    r3 = _install(d)
    check("AC-4-5(f2): operator edit outside the block is not flagged "
          "as a local modification",
          "SKIP" not in r3.stdout or ".gitignore" not in r3.stdout)
    gi3 = open(os.path.join(d, ".gitignore")).read()
    check("AC-4-5(f2): post-edit re-install keeps operator line and one "
          "block", "dist/\n" in gi3
          and gi3.count(GITIGNORE_BLOCK_BEGIN) == 1)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------- #
# Scope guard: a non-autonomous config writes NOTHING at the project root.
# --------------------------------------------------------------------- #
d = tempfile.mkdtemp()
try:
    r = _install(d, cfg=SERVICE)
    check("scope: non-autonomous install writes no root .gitignore",
          r.returncode == 0
          and not os.path.exists(os.path.join(d, ".gitignore")))
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------- #
# Review fix (finding 7): co-ownership extends to metadata - an operator
# .gitignore with a non-default mode keeps it across the managed-block
# append and refresh paths.
# --------------------------------------------------------------------- #
d = tempfile.mkdtemp()
try:
    gi = os.path.join(d, ".gitignore")
    open(gi, "w").write("node_modules/\n")
    os.chmod(gi, 0o664)
    r = _install(d)
    check("mode: operator .gitignore mode preserved on append",
          r.returncode == 0
          and (os.stat(gi).st_mode & 0o777) == 0o664,
          oct(os.stat(gi).st_mode & 0o777))
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------- #
# Review fix (finding 8): the .pre-* state-backup pattern is in the
# emitted .claude/.gitignore fragment, so migration backups are never
# committable.
# --------------------------------------------------------------------- #
d = tempfile.mkdtemp()
try:
    _install(d)
    frag = open(os.path.join(d, ".claude", ".gitignore")).read()
    check("fragment: .bootstrap-state.json.pre-* pattern present",
          ".bootstrap-state.json.pre-*" in frag)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------- #
# Review fix (finding 2): RETROFIT installs with autonomous opt-ins get
# the same root .gitignore managed block their scaffolded wrappers need
# (the greenfield gate reads *_enabled, pinned false in retrofit; the
# overlay appends the action for the opt-in case).
# --------------------------------------------------------------------- #
RETROFIT_CFG = """mode: "retrofit"
project:
  name: r-sentinels
  archetype: ai-agent
  prd_tier: "standard"
principles:
  tdd_policy: "required"
secrets:
  enabled: true
deps:
  enabled: true
  approved: []
commands:
  test: "pytest"
  lint: "ruff check ."
  format: "ruff format ."
retrofit:
  spec_strategy: "touch-based"
  legacy_allowlist:
    - "src/**"
  retrofit_active: true
  r08_committed: true
  archetype_confidence: "high"
  archetype_evidence:
    - "anthropic dep"
  spec_patterns:
    change: true
    boundary: false
    migration: false
  codebase_size_gb: 1
  autonomous_modes:
    loop_mode_opted_in: true
    goal_supervised_mode_opted_in: false
    queue_mode_opted_in: false
"""
d = tempfile.mkdtemp()
try:
    r = _install(d, cfg=RETROFIT_CFG)
    check("retrofit: install with loop opt-in succeeds",
          r.returncode == 0, r.stderr)
    loop_sh = os.path.join(d, ".claude", "loop.sh")
    check("retrofit: scaffolded wrapper honours the root sentinels",
          os.path.exists(loop_sh)
          and "ROOT_HALT_HARD" in open(loop_sh).read())
    gi = os.path.join(d, ".gitignore")
    check("retrofit: root .gitignore managed block emitted with the "
          "wrappers", os.path.exists(gi)
          and GITIGNORE_BLOCK_BEGIN in open(gi).read()
          and "/.halt-hard\n" in open(gi).read())
finally:
    shutil.rmtree(d, ignore_errors=True)

# Retrofit WITHOUT any opt-in: no root .gitignore (scope unchanged).
d = tempfile.mkdtemp()
try:
    no_optin = RETROFIT_CFG.replace("loop_mode_opted_in: true",
                                    "loop_mode_opted_in: false")
    r = _install(d, cfg=no_optin)
    check("retrofit: no opt-ins -> no root .gitignore",
          r.returncode == 0
          and not os.path.exists(os.path.join(d, ".gitignore")))
finally:
    shutil.rmtree(d, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

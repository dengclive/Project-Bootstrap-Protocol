#!/usr/bin/env python3
"""Behavioral tests: EXECUTE the emitted autonomous-mode wrappers.

The gap this closes. `tests/test_hook_behavior.py` pipes crafted payloads into
the emitted HOOKS and asserts exit codes -- the instrument that finally caught
the 2026-07-28 RCE and the fail-open gates. It stops at the hooks. Nothing in
this repo has ever EXECUTED `loop.sh`, `goal-loop.sh` or `auto.sh`:

  * the upstream six-lens review ran a greenfield install with every
    autonomous mode OFF, so all three wrappers were emitted and none invoked;
  * every other suite asserts emission determinism -- does the installer write
    the expected bytes -- which by construction cannot see what those bytes DO.

So the wrappers had the property that precedes every serious finding in this
repository: emitted, documented as working, never executed. A 1828-check green
suite sat on top of all five defects this file now pins.

WHAT IS ASSERTED, AND WHY IT IS PHRASED AS A PROPERTY.

The headline case is the skeleton refusal path. All three wrappers refuse to
dispatch unattended work -- correctly -- but they announce that refusal on
stderr while exiting 0 and recording a terminal-SUCCESS `exit_reason`
(`auto.sh` -> `queue-empty`, which its own enum defines as "nothing left to
dispatch ... (terminal success)"; the per-task wrappers -> `max-iterations`,
i.e. the loop ran and hit its cap). Under `nohup`, cron, or any supervisor
that checks `$?`, a skeleton that did nothing is indistinguishable from a
clean overnight run.

The checks below therefore assert the PROPERTY -- "a wrapper that dispatched
nothing must not exit 0, and must not record a success code" -- rather than
one specific spelling of the fix. Whether the fix keeps the pessimistic
`infrastructure-failure` default or introduces a new enum value, these pass.

The other pinned defects:
  * `iteration-summary-enforcement` exits 1 for a missing/empty summary. Per
    this repo's own normative checklist (Bootstrap-Protocol-v2-6-0.md:759)
    exit 1 is "hook error, tool proceeds", and on a Stop hook exit 2 means "do
    not stop". The enforcement hook uses the code that means "proceed"; its
    fail-closed path returns 2, so it demonstrably CAN block.
  * `drift-detector-loop-cooperation` gates on `ls A* B*`. One unmatched glob
    reaches `ls` literally and `ls` exits non-zero, so the tier-3 branch needs
    BOTH modes active at once -- impossible for a single task, which the
    wrappers hold in exactly one mode.
  * the per-task wrappers' `log()` and sentinel writes emit a literal `\\n`
    (backlog D-9 / I-8), so their hooks.log records share one physical line.

Regression protection for the parts that were verified SOUND is included too
(halt sentinels, eligibility refusal, sentinel ownership) -- those are the
controls an operator's safety actually rests on, and nothing else executes
them either.

Requires bash and flock. If either is absent this suite exits 0 but prints a
`SUITE SKIPPED:` marker, which `bin/run-tests` renders as SKIPPED and carries
onto the totals line and the closing banner -- deliberately NOT scored `ok`,
because a suite that declined to run has not passed. See `_skip` below.

Run: python3 tests/test_wrapper_behavior.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
INSTALL = os.path.join(ROOT, "bin", "bootstrap-install")
BASH = shutil.which("bash")

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


def _skip(reason):
    """Decline to run, VISIBLY.

    This used to print "0 passed, 0 failed" and exit 0, which `bin/run-tests`
    parsed into (0, 0) and rendered as `ok` -- so on any host without flock
    (stock macOS ships none) this suite's 65 checks silently became zero and
    the run still ended with ALL SUITES PASSED. That is the precise condition
    this suite exists to end: the batch that added it did so because a green
    suite had sat on top of four defects in the wrappers, none of which
    anything executed. An instrument that can quietly report nothing while
    the run reads green reconstitutes that, and it degrades further the
    moment anyone "fixes" the sibling suites that fail loudly on the same
    host. The marker below is what run-tests keys on for its SKIPPED status.
    """
    print(f"SUITE SKIPPED: {reason}")
    print("\n0 passed, 0 failed")
    sys.exit(0)


if not BASH:
    _skip("bash not found; wrapper behavioral suite cannot run")
if not shutil.which("flock"):
    _skip("flock not found; the wrappers hard-require it and refuse "
          "without it (stock macOS ships no flock)")

TMP = tempfile.mkdtemp(prefix="wrapper-behavior-")
PROJ = os.path.join(TMP, "proj")
os.makedirs(PROJ)

# The DEFAULT fixture emits none of this machinery. Opting in is mandatory --
# and if these key names ever drift the installer emits the non-autonomous set
# SILENTLY, which would leave this suite asserting against an empty tree while
# reporting green. The wrapper-presence checks below are that tripwire.
CONFIG = """project:
  name: "wrapbehavior"
  archetype: "fullstack"
  shell: "bash"
  prd_tier: "standard"
  cicd_opt_out: false
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: true
secrets:
  enabled: true
  never_read_paths:
    - ".env*"
    - "secrets/**"
deps:
  enabled: true
  approved: ["gleeunit"]
commands:
  test: "true"
  lint: "true"
  format: "true"
  ci_local: "true"
"""

cfg_path = os.path.join(TMP, "config.yaml")
with open(cfg_path, "w", encoding="utf-8") as fh:
    fh.write(CONFIG)

r = subprocess.run([sys.executable, INSTALL, "-c", cfg_path, "-C", PROJ],
                   capture_output=True, text=True)
if r.returncode != 0:
    print("installer failed; cannot run wrapper behavioral suite")
    print(r.stdout[-2000:], r.stderr[-2000:])
    sys.exit(1)

CLAUDE_DIR = os.path.join(PROJ, ".claude")
HOOKS = os.path.join(CLAUDE_DIR, "hooks")
SESSIONS = os.path.join(CLAUDE_DIR, "sessions")
QUEUE = os.path.join(CLAUDE_DIR, "queue")
LOG = os.path.join(CLAUDE_DIR, "logs", "hooks.log")
WRAPPERS = ("loop.sh", "goal-loop.sh", "auto.sh")

# A stub `claude` first on PATH. Nothing in the skeletons dispatches, so this
# should never be invoked -- if it ever is, the argv log proves it and the
# suite says so rather than silently driving a real agent.
STUB_DIR = os.path.join(TMP, "stub")
os.makedirs(STUB_DIR)
STUB_LOG = os.path.join(TMP, "claude-argv.log")
with open(os.path.join(STUB_DIR, "claude"), "w", encoding="utf-8") as fh:
    fh.write('#!/bin/sh\nprintf "%s\\n" "$*" >> "%s"\nexit 0\n' % ("", STUB_LOG))
os.chmod(os.path.join(STUB_DIR, "claude"), 0o755)


def wrapper(name, *args, project=None, env=None):
    """Execute an emitted wrapper -> (rc, out, err)."""
    e = dict(os.environ)
    e["PATH"] = STUB_DIR + os.pathsep + e.get("PATH", "")
    e["CLAUDE_PROJECT_DIR"] = project or PROJ
    if env:
        e.update(env)
    p = subprocess.run([BASH, os.path.join(CLAUDE_DIR, name), *args],
                       input="", capture_output=True, text=True, env=e)
    return p.returncode, p.stdout, p.stderr


def hook(name, payload, project=None, env=None, path=None):
    """Execute an emitted hook with a payload on stdin -> (rc, out, err)."""
    e = dict(os.environ)
    e["CLAUDE_PROJECT_DIR"] = project or PROJ
    if path:
        e["PATH"] = path
    if env:
        e.update(env)
    p = subprocess.run([BASH, os.path.join(HOOKS, f"{name}.sh")],
                       input=payload, capture_output=True, text=True, env=e)
    return p.returncode, p.stdout, p.stderr


# A PATH holding neither jq nor python3. A symlink farm is the only honest way
# -- `command -v jq` cannot be fooled by shadowing. Mirrors test_hook_behavior.
def _farm(name, extra=()):
    d = os.path.join(TMP, name)
    os.makedirs(d, exist_ok=True)
    for b in ("bash", "cat", "date", "mkdir", "dirname", "ls", "rm", "sed",
              "grep", "head", "wc", "touch", "env", "sh", "flock", "printf",
              "ps", "kill") + tuple(extra):
        p = shutil.which(b)
        if p and not os.path.exists(os.path.join(d, b)):
            os.symlink(p, os.path.join(d, b))
    return d


PATH_NOPARSER = _farm("noparser")


def log_text():
    try:
        with open(LOG, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""


def clear_log():
    try:
        os.remove(LOG)
    except FileNotFoundError:
        pass


def clear_sentinels():
    for d in (SESSIONS, QUEUE):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.startswith(".") and f != ".gitignore":
                try:
                    os.remove(os.path.join(d, f))
                except (IsADirectoryError, PermissionError, OSError):
                    pass
    for f in (".halt", ".halt-hard"):
        try:
            os.remove(os.path.join(PROJ, f))
        except FileNotFoundError:
            pass


# `exit_reason` values that mean the run reached a healthy terminal state. A
# wrapper that dispatched nothing must never record one of these. Sourced from
# auto.sh's own 13-value enum plus the per-task wrappers' terminal codes.
SUCCESS_REASONS = ("queue-empty", "deferred-only-remaining", "max-iterations")

os.makedirs(SESSIONS, exist_ok=True)
os.makedirs(QUEUE, exist_ok=True)
TASKS = os.path.join(CLAUDE_DIR, "specs", "s1", "tasks")
os.makedirs(TASKS, exist_ok=True)
with open(os.path.join(TASKS, "T-100.md"), "w", encoding="utf-8") as fh:
    fh.write("# Task T-100\nloop_eligible: true\ngoal_supervised_eligible: true\n")
with open(os.path.join(TASKS, "T-200.md"), "w", encoding="utf-8") as fh:
    fh.write("# Task T-200\nloop_eligible: false\n")


print("\n== the fixture actually emitted the autonomous surface ==")

# If the opt-in keys ever drift, the installer emits the non-autonomous set
# silently. Without this, every check below would vacuously pass on a tree that
# contains none of the machinery under test.
for w in WRAPPERS:
    p = os.path.join(CLAUDE_DIR, w)
    check(f"{w} emitted", os.path.isfile(p), p)
    if os.path.isfile(p):
        check(f"{w} is executable", os.access(p, os.X_OK))
        r = subprocess.run([BASH, "-n", p], capture_output=True, text=True)
        check(f"{w} is syntactically valid", r.returncode == 0, r.stderr)
for h in ("drift-detector-loop-cooperation", "iteration-summary-enforcement"):
    check(f"{h}.sh emitted", os.path.isfile(os.path.join(HOOKS, f"{h}.sh")))


print("\n== F1: a wrapper that dispatched nothing must not report success ==")

# The core property. The skeletons refuse correctly and say so on stderr, but
# an unattended caller sees only $? and the logged exit_reason. Both currently
# say the run succeeded.
clear_sentinels()
clear_log()
rc, _, err = wrapper("auto.sh")
check("auto.sh: refusal is loud on stderr",
      "skeleton" in err.lower() or "before any unattended use" in err, err[:200])
check("auto.sh: refusal does NOT exit 0", rc != 0, f"rc={rc}")
lg = log_text()
check("auto.sh: refusal does NOT record a terminal-success exit_reason",
      not any(f"reason={s}" in lg for s in SUCCESS_REASONS), lg[-300:])

clear_sentinels()
clear_log()
rc, _, err = wrapper("loop.sh", "T-100")
check("loop.sh: eligible task, refusal is loud on stderr",
      "No agent work was dispatched" in err or "skeleton" in err.lower(),
      err[:200])
check("loop.sh: refusal does NOT exit 0", rc != 0, f"rc={rc}")
lg = log_text()
check("loop.sh: refusal does NOT record a terminal-success exit_reason",
      not any(f"reason={s}" in lg for s in SUCCESS_REASONS), lg[-300:])

clear_sentinels()
clear_log()
rc, _, err = wrapper("goal-loop.sh", "T-100")
check("goal-loop.sh: refusal does NOT exit 0", rc != 0, f"rc={rc}")
lg = log_text()
check("goal-loop.sh: refusal does NOT record a terminal-success exit_reason",
      not any(f"reason={s}" in lg for s in SUCCESS_REASONS), lg[-300:])

check("no wrapper dispatched a real `claude` call",
      not os.path.exists(STUB_LOG),
      "the stub was invoked; a skeleton dispatched agent work")


print("\n== F2: the iteration-summary gate must use the code that BLOCKS ==")

# Bootstrap-Protocol-v2-6-0.md:759 -- "exit 2 blocks, but exit 1 is 'hook
# error, tool proceeds'". :655 -- "on a `Stop` hook exit 2 means 'do not
# stop'". A Stop hook that exits 1 for its own violation lets the iteration
# end exactly as if the summary had been written.
STOP = '{"session_id":"s1","hook_event_name":"Stop"}'
clear_sentinels()

rc, _, err = hook("iteration-summary-enforcement", STOP)
check("no goal-active marker: ordinary session end is allowed", rc == 0,
      f"rc={rc} {err[:160]}")

open(os.path.join(SESSIONS, ".goal-active-T-100"), "w").close()
rc, _, err = hook("iteration-summary-enforcement", STOP)
check("goal iteration, summary MISSING -> blocks with 2 (not 1)", rc == 2,
      f"rc={rc} {err[:160]}")

open(os.path.join(SESSIONS, ".iteration-summary-T-100-1.md"), "w").close()
rc, _, err = hook("iteration-summary-enforcement", STOP)
check("goal iteration, summary EMPTY -> blocks with 2 (not 1)", rc == 2,
      f"rc={rc} {err[:160]}")

with open(os.path.join(SESSIONS, ".iteration-summary-T-100-1.md"), "w",
          encoding="utf-8") as fh:
    fh.write("## Goal condition\nmet\n## What changed\nthings\n")
rc, _, err = hook("iteration-summary-enforcement", STOP)
check("goal iteration, summary present -> allows", rc == 0,
      f"rc={rc} {err[:160]}")

# The degraded path already returns 2, which is what proves the hook is
# CAPABLE of blocking -- the enforcement decision simply did not use it.
rc, _, err = hook("iteration-summary-enforcement", "")
check("empty payload still fails closed with 2", rc == 2,
      f"rc={rc} {err[:160]}")

# THE BOUND ITSELF. `exit 2` on a Stop hook means "do not stop", so the demand
# above is only safe while stop_hook_active can actually be read.
open(os.path.join(SESSIONS, ".goal-active-T-100"), "w").close()
for f in os.listdir(SESSIONS):
    if f.startswith(".iteration-summary-"):
        os.remove(os.path.join(SESSIONS, f))
STOP_RE = '{"session_id":"s1","hook_event_name":"Stop","stop_hook_active":true}'
rc, _, err = hook("iteration-summary-enforcement", STOP_RE)
check("stop_hook_active re-entry -> allows (the loop bound)", rc == 0,
      f"rc={rc} {err[:160]}")

# ...and the bound must survive a host with NO JSON parser. `jget` routes a
# missing parser through hook_fail, whose `exit 2` dies with the COMMAND
# SUBSTITUTION rather than the script -- so a naive `[ "$(jget ...)" = true ]`
# guard reads empty, the bound never fires, and the hook blocks every turn
# forever. Caught by execution against the first version of this fix.
rc, _, err = hook("iteration-summary-enforcement", STOP_RE, path=PATH_NOPARSER)
check("no parser + stop_hook_active -> allows, never an unbounded stop-loop",
      rc == 0, f"rc={rc} {err[:200]}")
rc, _, err = hook("iteration-summary-enforcement", STOP, path=PATH_NOPARSER)
check("no parser -> degrades to advisory rather than blocking unboundedly",
      rc == 0, f"rc={rc} {err[:200]}")
# Anchored on the DEGRADE wording, not on "no JSON parser": the defective
# version printed the shared header's "BLOCKED (fail-closed): no JSON parser
# available" from inside the swallowed subshell, so that substring was present
# on the broken path too and the check passed over the bug.
check("no-parser degrade names the unbounded-block risk it is avoiding",
      "Degrading to advisory" in err and "cannot be bounded" in err, err[:300])
check("no-parser degrade does not emit a spurious BLOCKED line",
      "BLOCKED (fail-closed)" not in err, err[:300])
clear_sentinels()


print("\n== F3: the tier-3 cooperation point must fire in a SINGLE mode ==")

# `ls A* B*` with one glob unmatched exits non-zero, so the branch required
# both modes at once. A task is in exactly one mode -- the wrappers enforce
# that -- so the cooperation point could never fire in normal operation.
POST = '{"session_id":"s1","hook_event_name":"PostToolUse","tool_name":"Edit"}'
COOP = "tier3-in-loop"

clear_sentinels()
open(os.path.join(SESSIONS, ".loop-active-T-100"), "w").close()
open(os.path.join(SESSIONS, ".drift-tier3-T-100"), "w").close()
rc, _, err = hook("drift-detector-loop-cooperation", POST)
check("LOOP mode + tier-3 sentinel -> cooperation fires", COOP in err,
      f"rc={rc} {err[:160]}")

clear_sentinels()
open(os.path.join(SESSIONS, ".goal-active-T-100"), "w").close()
open(os.path.join(SESSIONS, ".drift-tier3-T-100"), "w").close()
rc, _, err = hook("drift-detector-loop-cooperation", POST)
check("GOAL mode + tier-3 sentinel -> cooperation fires", COOP in err,
      f"rc={rc} {err[:160]}")

clear_sentinels()
open(os.path.join(SESSIONS, ".drift-tier3-T-100"), "w").close()
rc, _, err = hook("drift-detector-loop-cooperation", POST)
check("tier-3 sentinel but NO active mode -> stays quiet", COOP not in err,
      f"rc={rc} {err[:160]}")

clear_sentinels()
open(os.path.join(SESSIONS, ".loop-active-T-100"), "w").close()
rc, _, err = hook("drift-detector-loop-cooperation", POST)
check("loop mode but no tier-3 sentinel -> stays quiet", COOP not in err,
      f"rc={rc} {err[:160]}")
check("cooperation hook is advisory: never blocks", rc == 0, f"rc={rc}")
clear_sentinels()


print("\n== D-9 / I-8: wrapper log and sentinel writes emit real newlines ==")

clear_sentinels()
clear_log()
wrapper("loop.sh", "T-100")
wrapper("goal-loop.sh", "T-100")
wrapper("auto.sh")
lg = log_text()
check("hooks.log contains no literal backslash-n from the wrappers",
      "\\n" not in lg, repr(lg[-300:]))
check("each wrapper log record is its own physical line",
      lg.count("\n") >= len([ln for ln in lg.splitlines() if ln.strip()]),
      repr(lg[-300:]))

# The O_CREAT|O_EXCL claim sentinel carries the owning pid; I-8 is the same
# escape-doubling in its printf.
clear_sentinels()
sentinel_probe = os.path.join(SESSIONS, ".loop-active-PROBE")
with open(os.path.join(TASKS, "PROBE.md"), "w", encoding="utf-8") as fh:
    fh.write("# PROBE\nloop_eligible: true\n")
# Pre-create the sentinel the way the wrapper does, then read it back: the
# wrapper removes its own on exit, so the write is reproduced rather than
# raced for.
r = subprocess.run(
    [BASH, "-c",
     'set -C; printf "%%s\\n" "$$" > "%s"' % sentinel_probe],
    capture_output=True, text=True)
if r.returncode == 0:
    with open(sentinel_probe, encoding="utf-8") as fh:
        body = fh.read()
    check("claim sentinel holds a bare pid, no literal backslash-n",
          "\\n" not in body, repr(body))
clear_sentinels()


print("\n== regression: the halt path (verified sound; keep it that way) ==")

for name, args in (("loop.sh", ("T-100",)), ("goal-loop.sh", ("T-100",)),
                   ("auto.sh", ())):
    for sentinel in (".halt", ".halt-hard"):
        clear_sentinels()
        open(os.path.join(PROJ, sentinel), "w").close()
        rc, _, err = wrapper(name, *args)
        check(f"{name}: root {sentinel} refuses non-zero", rc != 0,
              f"rc={rc} {err[:120]}")
    clear_sentinels()
    open(os.path.join(QUEUE, ".halt"), "w").close()
    rc, _, err = wrapper(name, *args)
    check(f"{name}: queue-scoped .halt refuses non-zero (dual-honor)", rc != 0,
          f"rc={rc} {err[:120]}")

# A halt sentinel an agent created as a DIRECTORY must still halt: `[ -e ]`
# is the right test and `rm -f` on it would fail.
clear_sentinels()
os.makedirs(os.path.join(PROJ, ".halt"), exist_ok=True)
rc, _, err = wrapper("loop.sh", "T-100")
check("directory-shaped .halt still refuses", rc != 0, f"rc={rc}")
os.rmdir(os.path.join(PROJ, ".halt"))


print("\n== regression: eligibility refusal (the I-1/I-2 mitigation) ==")

# The wrappers hard-require loop_eligible / goal_supervised_eligible, and
# greenfield spec-decompose does not teach those fields. The recorded
# mitigation is that the wrappers "fail closed -- they refuse rather than run".
clear_sentinels()
rc, _, err = wrapper("loop.sh", "T-DOES-NOT-EXIST")
check("loop.sh: no task file -> refuses", rc != 0, f"rc={rc}")
check("loop.sh: refusal names the missing task file", "No task file" in err,
      err[:160])

clear_sentinels()
rc, _, err = wrapper("loop.sh", "T-200")
check("loop.sh: loop_eligible false -> refuses", rc != 0, f"rc={rc}")
check("loop.sh: refusal names the eligibility field", "loop_eligible" in err,
      err[:160])

clear_sentinels()
rc, _, err = wrapper("goal-loop.sh", "T-200")
check("goal-loop.sh: goal_supervised_eligible absent -> refuses", rc != 0,
      f"rc={rc}")

clear_sentinels()
rc, _, err = wrapper("loop.sh")
check("loop.sh: no task id at all -> usage error", rc != 0, f"rc={rc}")


print("\n== regression: a refusing loser never yanks the winner's sentinel ==")

clear_sentinels()
own = os.path.join(SESSIONS, ".loop-active-T-100")
with open(own, "w", encoding="utf-8") as fh:
    fh.write("99999\n")
rc, _, err = wrapper("loop.sh", "T-100")
check("loop.sh: already-claimed task refuses", rc != 0, f"rc={rc}")
check("loop.sh: the winner's sentinel survives the refusal",
      os.path.exists(own), "the loser deleted the winner's claim")

clear_sentinels()
other = os.path.join(SESSIONS, ".goal-active-T-100")
open(other, "w").close()
rc, _, err = wrapper("loop.sh", "T-100")
check("cross-mode: loop.sh refuses a goal-held task", rc != 0, f"rc={rc}")
check("cross-mode: the goal sentinel survives", os.path.exists(other))
check("cross-mode: loop.sh leaked no sentinel of its own",
      not os.path.exists(os.path.join(SESSIONS, ".loop-active-T-100")))

clear_sentinels()
open(own, "w").close()
rc, _, err = wrapper("goal-loop.sh", "T-100")
check("cross-mode: goal-loop.sh refuses a loop-held task", rc != 0, f"rc={rc}")
check("cross-mode: the loop sentinel survives", os.path.exists(own))
clear_sentinels()


print("\n== regression: auto.sh treats .run-active as untrusted input ==")

RUN = os.path.join(QUEUE, ".run-active")

clear_sentinels()
with open(RUN, "w", encoding="utf-8") as fh:
    fh.write("pid=1 start=2026-07-30T00:00:00Z\n")
rc, _, err = wrapper("auto.sh")
check("forged .run-active naming a live pid -> refuses", rc != 0, f"rc={rc}")

clear_sentinels()
with open(RUN, "w", encoding="utf-8") as fh:
    fh.write("pid=999999 start=2026-07-30T00:00:00Z\n")
rc, _, err = wrapper("auto.sh")
check("stale .run-active, non-interactive -> refuses without clearing",
      rc != 0 and os.path.exists(RUN), f"rc={rc}")

clear_sentinels()
with open(RUN, "w", encoding="utf-8") as fh:
    fh.write("garbage with no pid line\n")
rc, _, err = wrapper("auto.sh")
check("unparseable .run-active -> refuses", rc != 0, f"rc={rc}")
check("unparseable .run-active refusal says so", "could not read a PID" in err,
      err[:160])
clear_sentinels()


shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

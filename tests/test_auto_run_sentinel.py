#!/usr/bin/env python3
"""Finding 2 (owner review of PR #5) — auto.sh .run-active race safety.

Pre-existing conformance defect vs Phase 9.7 ("abort ... rather than
overwriting"): the refuse-to-start path's EXIT trap deleted the WINNER's
sentinel, letting a third invocation start a concurrent runner past the
combined-concurrency cap. Fix: CLAIMED guard exactly as the per-task
wrappers, plus the normative startup sequence - PID-liveness (not mere
presence), operator-confirmed stale clearing with re-verify-before-clear,
and an O_CREAT|O_EXCL claim.

Owner-required cases:
  (i)   live-PID refusal leaves the winner's sentinel intact
  (ii)  stale-PID-cleared path unaffected
  (iii) race-loser path leaves the winner's sentinel intact
  (iv)  a normal run still removes its own sentinel on exit

Run: python3 tests/test_auto_run_sentinel.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

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
  name: runsentinel
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


def dead_pid():
    """A PID that is certainly not alive: spawn-and-reap a child."""
    p = subprocess.Popen(["true"])
    p.wait()
    return p.pid


d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(FULL)
    r = subprocess.run([sys.executable, BIN, "-C", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    auto = os.path.join(d, ".claude", "auto.sh")
    run_path = os.path.join(d, ".claude", "queue", ".run-active")
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = d

    def run_auto(stdin_text="", force_prompt=False):
        e = dict(env)
        if force_prompt:
            # TEST-ONLY override: forces the prompt path on a non-tty; it
            # can only enable ASKING (answer still read from stdin,
            # default No) - never clearing.
            e["BOOTSTRAP_TEST_FORCE_PROMPT"] = "1"
        return subprocess.run(["bash", auto], input=stdin_text,
                              capture_output=True, text=True, env=e)

    body = open(auto).read()
    check("static: O_CREAT|O_EXCL claim of .run-active (set -C)",
          'set -C; printf' in body and '>"$RUN"' in body)
    check("static: three-state pid_alive probe (ps -p self-probed, "
          "kill -0 fallback, cannot-determine refuses)",
          'pid_alive(){' in body and 'ps -p $$' in body
          and 'return 2' in body and '/proc/$OLD_PID' not in body)
    check("static: startup check-clear-claim runs under flock",
          'exec 8>"$RUN.lock"' in body and 'flock -n 8' in body)
    check("static: prompt read is time-bounded",
          'read -r -t "${BOOTSTRAP_PROMPT_TIMEOUT:-60}"' in body)
    check("static: prompt is tty-guarded before any stdin read",
          '[ -t 0 ] || [ "${BOOTSTRAP_TEST_FORCE_PROMPT:-0}" = 1 ]' in body)
    check("static: cleanup removes the sentinel only when CLAIMED",
          '[ "$CLAIMED" = 1 ] && rm -f "$RUN"' in body)

    # ----------------------------------------------------------------- #
    # (iv) normal run: claims, completes, removes its own sentinel
    # ----------------------------------------------------------------- #
    r = run_auto()
    check("(iv) normal run exits 0", r.returncode == 0, r.stderr)
    check("(iv) normal run removed its own sentinel on exit",
          not os.path.exists(run_path))

    # ----------------------------------------------------------------- #
    # (i) live-PID refusal is side-effect-free
    # ----------------------------------------------------------------- #
    winner = f"pid={os.getpid()} start=2026-07-17T00:00:00Z\n"
    open(run_path, "w").write(winner)
    r = run_auto()
    check("(i) live-PID refusal exits non-zero with a clear message",
          r.returncode != 0 and "already active" in r.stderr, r.stderr)
    check("(i) winner's sentinel intact and byte-identical",
          os.path.exists(run_path) and open(run_path).read() == winner)

    # Sentinel is a DIRECTORY: sed fails; helpers must yield empty and
    # reach the fail-safe branch instead of dying via errexit+pipefail.
    os.remove(run_path)
    os.mkdir(run_path)
    r = run_auto()
    check("fail-safe: sentinel-as-directory refuses via the "
          "could-not-read-PID branch (no silent errexit death)",
          r.returncode != 0 and "could not read a PID" in r.stderr,
          f"rc={r.returncode} stderr={r.stderr!r}")
    os.rmdir(run_path)

    # Broken ps (busybox-class: ps lacks -p entirely). pid_alive must NOT
    # classify cannot-determine as dead: dead pid -> refuse loudly.
    fake_bin = os.path.join(d, "fakebin")
    os.makedirs(fake_bin, exist_ok=True)
    fake_ps = os.path.join(fake_bin, "ps")
    open(fake_ps, "w").write("#!/bin/sh\necho 'ps: unrecognized option' >&2\nexit 1\n")
    os.chmod(fake_ps, 0o755)

    def run_auto_brokenps(stdin_text="", extra=None):
        e = dict(env)
        e["PATH"] = fake_bin + os.pathsep + e["PATH"]
        if extra:
            e.update(extra)
        return subprocess.run(["bash", auto], input=stdin_text,
                              capture_output=True, text=True, env=e)

    dead_sentinel = f"pid={dead_pid()} start=2026-07-14T00:00:00Z\n"
    open(run_path, "w").write(dead_sentinel)
    r = run_auto_brokenps()
    check("cannot-determine: broken ps + dead pid refuses (never offers "
          "stale-clear)", r.returncode != 0
          and "Cannot determine" in r.stderr
          and open(run_path).read() == dead_sentinel,
          f"rc={r.returncode} stderr={r.stderr!r}")

    live_sentinel = f"pid={os.getpid()} start=2026-07-14T01:00:00Z\n"
    open(run_path, "w").write(live_sentinel)
    r = run_auto_brokenps()
    check("cannot-determine fallback: broken ps + LIVE pid still refuses "
          "as active (kill -0 success proves aliveness)",
          r.returncode != 0 and "already active" in r.stderr
          and open(run_path).read() == live_sentinel,
          f"rc={r.returncode} stderr={r.stderr!r}")
    os.remove(run_path)

    # Unparseable sentinel: fail safe, no damage.
    open(run_path, "w").write("garbage, no pid here\n")
    r = run_auto()
    check("fail-safe: unparseable sentinel refuses without touching it",
          r.returncode != 0
          and "could not read a PID" in r.stderr
          and open(run_path).read() == "garbage, no pid here\n")

    # ----------------------------------------------------------------- #
    # (ii) stale-PID path: alert + ask; 'y' clears and continues,
    # 'n'/EOF refuses side-effect-free
    # ----------------------------------------------------------------- #
    stale = f"pid={dead_pid()} start=2026-07-16T00:00:00Z\n"
    open(run_path, "w").write(stale)
    r = run_auto()          # non-tty stdin -> auto-No before any read
    check("(ii) stale + non-interactive refuses without prompting",
          r.returncode != 0 and "Stale .run-active" in r.stderr
          and "Non-interactive invocation" in r.stderr, r.stderr)
    check("(ii) refusal leaves the stale sentinel in place",
          open(run_path).read() == stale)

    # tty-guard: a non-tty 'y' WITHOUT the test override must never clear -
    # stdin is not even read (F-2 class: inherited pipes cannot drive
    # clearing, and an open-but-silent pipe cannot hang the prompt).
    r = run_auto(stdin_text="y\n")
    check("(ii) non-tty 'y' without override refuses, sentinel intact",
          r.returncode != 0 and open(run_path).read() == stale
          and "Non-interactive invocation" in r.stderr, r.stderr)

    r = run_auto(stdin_text="n\n", force_prompt=True)
    check("(ii) stale + explicit 'n' refuses, sentinel intact",
          r.returncode != 0 and open(run_path).read() == stale)

    r = run_auto(stdin_text="y\n", force_prompt=True)
    check("(ii) stale + 'y' alerts with recorded start, clears, and runs",
          r.returncode == 0
          and "2026-07-16T00:00:00Z" in r.stderr, r.stderr)
    check("(ii) cleared-and-completed run removed its own sentinel",
          not os.path.exists(run_path))
    log = open(os.path.join(d, ".claude", "logs", "hooks.log")).read()
    check("(ii) stale clearing is logged",
          "cleared stale .run-active" in log)

    # Forced prompt on an open-but-silent pipe must NOT hang: the read is
    # time-bounded, timeout falls through to No, sentinel intact.
    hang_sentinel = f"pid={dead_pid()} start=2026-07-13T00:00:00Z\n"
    open(run_path, "w").write(hang_sentinel)
    henv = dict(env)
    henv["BOOTSTRAP_TEST_FORCE_PROMPT"] = "1"
    henv["BOOTSTRAP_PROMPT_TIMEOUT"] = "1"
    hp = subprocess.Popen(["bash", auto], stdin=subprocess.PIPE,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, text=True, env=henv)
    try:
        _, herr = hp.communicate(timeout=8)   # stdin open, never written
        check("hang-bound: forced prompt on silent pipe times out to No",
              hp.returncode != 0
              and "Leaving the stale sentinel" in herr
              and open(run_path).read() == hang_sentinel, herr)
    except subprocess.TimeoutExpired:
        hp.kill()
        check("hang-bound: forced prompt on silent pipe times out to No",
              False, "read blocked past the timeout bound")
    os.remove(run_path)

    # ----------------------------------------------------------------- #
    # (iii) race-loser: another runner claims the sentinel while this one
    # waits at the stale-clear prompt -> abort, winner untouched. (The
    # O_CREAT|O_EXCL claim itself is assertion-covered above; this drives
    # the re-verify-before-clear guard through the wrapper end-to-end.)
    # ----------------------------------------------------------------- #
    open(run_path, "w").write(f"pid={dead_pid()} start=2026-07-15T00:00:00Z\n")
    err_path = os.path.join(d, "loser.stderr")
    with open(err_path, "w") as errf:
        race_env = dict(env)
        race_env["BOOTSTRAP_TEST_FORCE_PROMPT"] = "1"
        p = subprocess.Popen(["bash", auto], stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=errf,
                             text=True, env=race_env)
        # Wait until the loser is parked at the confirmation prompt.
        deadline = time.time() + 10
        while time.time() < deadline:
            if "Clear the stale sentinel" in open(err_path).read():
                break
            time.sleep(0.05)
        else:
            p.kill()
            raise AssertionError("loser never reached the prompt")
        # DUAL-Y RACE regression: while the first invocation is parked at
        # the prompt it holds the startup flock, so a second invocation
        # must refuse instantly - two operators can never both reach the
        # clear step for the same stale sentinel.
        r2 = subprocess.run(["bash", auto], input="y\n",
                            capture_output=True, text=True, env=race_env)
        check("dual-y: second invocation refuses while first holds the "
              "startup lock", r2.returncode != 0
              and "mid-startup" in r2.stderr, r2.stderr)
        # A winner claims the sentinel while the loser is parked.
        winner = f"pid={os.getpid()} start=2026-07-17T09:00:00Z\n"
        open(run_path, "w").write(winner)
        p.communicate(input="y\n", timeout=10)
    check("(iii) race-loser exits non-zero", p.returncode != 0)
    err = open(err_path).read()
    check("(iii) race-loser reports the lost race and aborts",
          "changed while waiting" in err, err)
    check("(iii) winner's sentinel intact and byte-identical",
          os.path.exists(run_path) and open(run_path).read() == winner)
    os.remove(run_path)
finally:
    shutil.rmtree(d, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

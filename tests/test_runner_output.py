#!/usr/bin/env python3
"""[WP2 review SC-4, SC-5, SDK-P6, LD-1] How a blocking gate's runner output
reaches the model.

test-gate, ci-mirror and eval-gate run a configured command and, on a
failure, pass its merged output to the model (exit-2 stderr on the shell,
permissionDecisionReason in the SDK). From a real install, on both
substrates where the gate exists on both:

  * SC-4 / SDK-P6: the output is the last RUNNER_TAIL_LINES lines AND at most
    RUNNER_TAIL_BYTES bytes. A line count alone let one long line (jest
    --json, a webpack stats blob, a carriage-return progress bar) through
    whole: 2,000,070 bytes of stderr was measured. The two substrates cut
    the same bytes.
  * SC-5: the gate returns when the runner exits. The output went through a
    pipe to `tail`, which waits for EOF, so a background child that kept
    the runner's stdout open held the hook until the child exited, and a
    shell hook killed at its timeout fails OPEN. It now goes to a file
    under .claude/logs, removed after the tail is read.
  * B-1: a hook killed mid-run leaves that file behind; a later run of the
    same hook deletes its files older than the hook's bound.
  * B-2: with .claude/logs unusable, a set but bad TMPDIR still captures
    through /tmp, as the SDK's tempfile does.
  * LD-1: Claude Code delivers one exit-2 reason per tool call, so when
    ci-mirror and eval-gate both block a push the model sees one of them.
    eval-gate's failure message says that other push gates may block too.

Run: python3 tests/test_runner_output.py
"""
import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BIN = os.path.join(ROOT, "bin", "bootstrap-install")
sys.path.insert(0, os.path.join(ROOT, "lib"))

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


class _HM:
    def __init__(self, matcher=None, hooks=None, timeout=None):
        self.matcher, self.hooks, self.timeout = matcher, hooks or [], timeout


_stub = types.ModuleType("claude_agent_sdk")
_stub.HookMatcher = _HM
sys.modules.setdefault("claude_agent_sdk", _stub)

import sdk_gates_template as sgt  # noqa: E402

LINES = sgt.RUNNER_TAIL_LINES
BYTES = getattr(sgt, "RUNNER_TAIL_BYTES", None)

# Every runner is `sh r.sh` in the project root; each scenario rewrites r.sh.
CFG = """gate_substrate: "sdk-callable"
project:
  name: runnerprobe
  archetype: ai-agent
  shell: bash
secrets:
  enabled: false
deps:
  enabled: false
hooks:
  spec_gate_commit: false
commands:
  test: "sh r.sh"
  lint: "true"
  format: "true"
  ci_local: "sh r.sh"
  eval: "sh r.sh"
"""
GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

# (hook, command, the reason line the shell prints last, SDK function)
GATES = (
    ("test-gate", "git commit -m x", "Commit blocked: tests failing (exit 1).",
     "test_gate"),
    ("ci-mirror", "git push", "Push blocked: CI mirror failed.", None),
    ("eval-gate", "git push", "Push blocked: evals failing (exit 1).",
     "eval_gate"),
)
FIRST = {"test-gate": "Running test gate: sh r.sh",
         "ci-mirror": "CI mirror: sh r.sh",
         "eval-gate": "Running eval gate: sh r.sh"}


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, env=GIT_ENV,
                          capture_output=True, text=True).stdout


def install(scratch):
    d = os.path.join(scratch, "proj")
    bare = os.path.join(scratch, "remote.git")
    os.makedirs(d)
    subprocess.run(["git", "init", "-q", "--bare", bare], check=True)
    _git(d, "init", "-q", "-b", "main")
    _git(d, "commit", "-q", "--allow-empty", "-m", "root")
    with open(os.path.join(scratch, "c.yaml"), "w") as fh:
        fh.write(CFG)
    r = subprocess.run([sys.executable, BIN, "-c",
                        os.path.join(scratch, "c.yaml"), "-C", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    _git(d, "add", "-A")
    _git(d, "commit", "-qm", "install")
    _git(d, "remote", "add", "origin", bare)
    _git(d, "push", "-q", "-u", "origin", "HEAD")
    # A prompt change in the push range, so eval-gate runs its command.
    os.makedirs(os.path.join(d, "prompts"))
    with open(os.path.join(d, "prompts", "system.txt"), "w") as fh:
        fh.write("prompt\n")
    _git(d, "add", "-A")
    _git(d, "commit", "-qm", "prompt")
    return d


def runner(d, body):
    with open(os.path.join(d, "r.sh"), "w") as fh:
        fh.write(body)


def shell(d, hook, command, env=None):
    """(rc, stdout bytes, stderr bytes, seconds)."""
    payload = json.dumps({"session_id": "s", "hook_event_name": "PreToolUse",
                          "tool_name": "Bash",
                          "tool_input": {"command": command}}).encode()
    t0 = time.monotonic()
    r = subprocess.run(["bash", os.path.join(d, ".claude", "hooks",
                                             hook + ".sh")],
                       input=payload, capture_output=True, cwd=d,
                       env=dict(env or os.environ, CLAUDE_PROJECT_DIR=d),
                       timeout=60)
    return r.returncode, r.stdout, r.stderr, time.monotonic() - t0


_mod = {}


def sdk(d, fname, command):
    """(result dict, seconds)."""
    if d not in _mod:
        spec = importlib.util.spec_from_file_location(
            "gates_runner", os.path.join(d, ".claude", "sdk_gates",
                                         "gates.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _mod[d] = mod
    mod = _mod[d]
    hooks = mod.build_hooks(mod.RESOLVED_CONFIG)
    for m in hooks["PreToolUse"]:
        for f in m.hooks:
            if f.__name__ == fname:
                old = os.environ.get("CLAUDE_PROJECT_DIR")
                os.environ["CLAUDE_PROJECT_DIR"] = d
                try:
                    t0 = time.monotonic()
                    r = asyncio.run(f({"tool_input": {"command": command}},
                                      "t", None))
                    return r, time.monotonic() - t0
                finally:
                    if old is None:
                        del os.environ["CLAUDE_PROJECT_DIR"]
                    else:
                        os.environ["CLAUDE_PROJECT_DIR"] = old
    raise AssertionError(fname + " not built")


def reason(r):
    return r.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")


def shell_detail(err, hook, last):
    """The runner's part of the shell's stderr: what sits between the
    'Running ...' line and the reason line."""
    head = (FIRST[hook] + "\n").encode()
    if not err.startswith(head):
        return None
    tail = err[len(head):]
    j = tail.rfind(last.encode())
    if j < 0:
        return None
    return tail[:j]


def logs_clean(d):
    """No runner capture file is left in .claude/logs."""
    names = os.listdir(os.path.join(d, ".claude", "logs"))
    return [n for n in names if ".out" in n]


def detail_lines(raw):
    """The SDK formats the runner's output as '\\n' + line per line."""
    text = raw.decode(errors="replace")
    parts = text.split("\n")
    if parts[-1] == "":
        parts.pop()
    return "".join("\n" + p for p in parts)


print("== the byte cap constant ==")
check("RUNNER_TAIL_BYTES is defined beside RUNNER_TAIL_LINES",
      isinstance(BYTES, int) and 0 < BYTES <= 64000, repr(BYTES))
if not isinstance(BYTES, int):
    BYTES = 20000

scratch = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
try:
    d = install(scratch)
    gates_py = open(os.path.join(d, ".claude", "sdk_gates",
                                 "gates.py")).read()
    check("gates.py renders _RUNNER_TAIL_BYTES once, from the shared "
          "constant", gates_py.count("_RUNNER_TAIL_BYTES = %d\n" % BYTES)
          == 1, "")

    # ---- SC-4 / SDK-P6: one long line ----------------------------------- #
    print("== SC-4 / SDK-P6: one 2,000,000-byte line is cut to the cap ==")
    runner(d, "python3 -c 'import sys; sys.stdout.write(\"y\" * 1000 + "
              "\"x\" * 1999999 + \"Z\\n\")'; exit 1\n")
    want = b"x" * (BYTES - 2) + b"Z\n"
    for hook, cmd, last, fname in GATES:
        rc, out, err, _ = shell(d, hook, cmd)
        det = shell_detail(err, hook, last)
        check(f"{hook} shell: exit 2, the runner part is the last "
              f"{BYTES} bytes",
              rc == 2 and out == b"" and det == want,
              repr((rc, len(err), det[:20] if det else det)))
        check(f"{hook} shell: stderr is bounded", len(err) < BYTES + 1000,
              repr(len(err)))
        if fname:
            r, _ = sdk(d, fname, cmd)
            check(f"{hook} SDK: the reason carries the same {BYTES} bytes",
                  reason(r) == last + detail_lines(want),
                  repr(len(reason(r))))

    # ---- SC-4: lines first, then bytes; a cut inside a line ------------- #
    print("== lines then bytes: 150 lines of 300 bytes ==")
    runner(d, "i=0; while [ $i -lt 150 ]; do i=$((i+1)); "
              "printf 'L%03d%0296d\\n' $i 0; done; exit 1\n")
    allout = b"".join(b"L%03d" % i + b"0" * 296 + b"\n"
                      for i in range(1, 151))
    lines_cut = b"".join(allout.split(b"\n")[-LINES - 1:-1][k] + b"\n"
                         for k in range(LINES))
    want = lines_cut[-BYTES:]
    for hook, cmd, last, fname in GATES:
        rc, out, err, _ = shell(d, hook, cmd)
        det = shell_detail(err, hook, last)
        check(f"{hook} shell: last {LINES} lines, then last {BYTES} bytes "
              f"(the cut lands inside a line)",
              rc == 2 and det == want, repr((rc, det[:12] if det else det)))
        if fname:
            r, _ = sdk(d, fname, cmd)
            check(f"{hook} SDK: the same cut, byte for byte",
                  reason(r) == last + detail_lines(want),
                  repr(reason(r)[:80]))

    # ---- under the byte cap, the line cap governs (no newline at end) -- #
    print("== under the byte cap: last lines, no final newline ==")
    runner(d, "seq 1 150; printf 'NOEOL'; exit 1\n")
    seq = "".join("%d\n" % i for i in range(1, 151)) + "NOEOL"
    want = ("\n".join(seq.split("\n")[-LINES:])).encode()
    for hook, cmd, last, fname in GATES:
        rc, out, err, _ = shell(d, hook, cmd)
        # tail passes the missing newline through, so the reason line
        # follows NOEOL on the same line.
        check(f"{hook} shell: the last {LINES} lines, unterminated line "
              f"kept", rc == 2 and err == (FIRST[hook] + "\n").encode()
              + want + err[len(FIRST[hook]) + 1 + len(want):]
              and err[len(FIRST[hook]) + 1 + len(want):].startswith(
                  last.encode()), repr(err[-120:]))
        if fname:
            r, _ = sdk(d, fname, cmd)
            check(f"{hook} SDK: the same {LINES} lines",
                  reason(r) == last + detail_lines(want),
                  repr(reason(r)[:80]))

    runner(d, "seq 1 150; exit 1\n")
    want = "".join("%d\n" % i for i in range(51, 151)).encode()
    for hook, cmd, last, fname in GATES:
        rc, out, err, _ = shell(d, hook, cmd)
        check(f"{hook} shell: the last {LINES} lines, final newline",
              rc == 2 and shell_detail(err, hook, last) == want,
              repr(err[:60]))
        if fname:
            r, _ = sdk(d, fname, cmd)
            check(f"{hook} SDK: the same {LINES} lines (a final newline "
                  f"ends the last line, it does not start one)",
                  reason(r) == last + detail_lines(want),
                  repr(reason(r)[:80]))

    # ---- SC-5: a background child that keeps stdout open ---------------- #
    print("== SC-5: the gate returns when the runner exits ==")
    runner(d, "sh -c 'sleep 6' & echo LINGER-OUT; exit 1\n")
    for hook, cmd, last, fname in GATES:
        rc, out, err, secs = shell(d, hook, cmd)
        check(f"{hook} shell: exit 2 in under 3 s with a 6 s child holding "
              f"stdout", rc == 2 and secs < 3.0
              and b"LINGER-OUT\n" + last.encode() in err,
              repr((rc, round(secs, 2), err[-100:])))
        if fname:
            r, secs = sdk(d, fname, cmd)
            check(f"{hook} SDK: deny in under 3 s with a 6 s child",
                  secs < 3.0 and reason(r) == last + "\nLINGER-OUT",
                  repr((round(secs, 2), reason(r)[:80])))
    check("no capture file is left in .claude/logs", logs_clean(d) == [],
          repr(logs_clean(d)))

    # The status is still the runner's: a pass passes, 3 stays 3.
    runner(d, "echo fine; exit 0\n")
    for hook, cmd, _, fname in GATES:
        rc, out, err, _ = shell(d, hook, cmd)
        check(f"{hook} shell: a passing runner allows", rc == 0, repr(err))
    runner(d, "echo red; exit 3\n")
    rc, _, err, _ = shell(d, "test-gate", "git commit -m x")
    check("test-gate shell: the runner's exit 3 is the one reported",
          rc == 2 and err.endswith(
              b"red\nCommit blocked: tests failing (exit 3).\n"), repr(err))
    check("no capture file is left after a pass or a failure",
          logs_clean(d) == [], repr(logs_clean(d)))

    # ---- B-1: a killed hook's file is swept by a later run -------------- #
    # Measured before the fix: a hook killed mid-run (SIGTERM or SIGKILL,
    # to the pid or the group) left .claude/logs/<hook>.out.XXXXXX holding
    # the runner's uncapped output, and no later run removed it.
    print("== B-1: a killed hook's capture file is swept ==")
    logs_dir = os.path.join(d, ".claude", "logs")
    payload = json.dumps({"session_id": "s", "hook_event_name":
                          "PreToolUse", "tool_name": "Bash", "tool_input":
                          {"command": "git commit -m x"}}).encode()
    runner(d, "echo started; sleep 3; echo F; exit 1\n")
    p = subprocess.Popen(["bash", os.path.join(d, ".claude", "hooks",
                                               "test-gate.sh")],
                         stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, cwd=d,
                         env=dict(os.environ, CLAUDE_PROJECT_DIR=d),
                         start_new_session=True)
    p.stdin.write(payload)
    p.stdin.close()
    time.sleep(1)
    os.killpg(p.pid, 9)
    p.wait()
    killed = logs_clean(d)
    check("test-gate shell: SIGKILL mid-run leaves its capture file (the "
          "case the sweep is for)", len(killed) == 1, repr(killed))
    # Aged past test-gate's bound (600 s, so 11 minutes), it is swept; a
    # fresh one (a concurrent run's) and another hook's are kept.
    stale = time.time() - 12 * 60
    for n in killed:
        os.utime(os.path.join(logs_dir, n), (stale, stale))
    fresh = os.path.join(logs_dir, "test-gate.out.FRESH1")
    other = os.path.join(logs_dir, "ci-mirror.out.OTHER1")
    for f, t in ((fresh, time.time() - 9 * 60), (other, stale)):
        open(f, "w").close()
        os.utime(f, (t, t))
    runner(d, "echo fine; exit 0\n")
    rc, _, err, _ = shell(d, "test-gate", "git commit -m x")
    left = sorted(logs_clean(d))
    check("test-gate shell: the next run sweeps the stale file, keeps a "
          "9-minute-old one and ci-mirror's", rc == 0
          and left == ["ci-mirror.out.OTHER1", "test-gate.out.FRESH1"],
          repr((rc, left, err[-200:])))
    for f in (fresh, other):
        if os.path.lexists(f):
            os.remove(f)

    # ---- RR1-EMB-1: no capture file in .claude/logs --------------------- #
    # Measured before the fix: with .claude/logs unwritable, a regular file
    # or a dangling symlink, the redirection failed before the runner ran,
    # and a PASSING suite was denied as "tests failing (exit 1)". The file
    # now comes from mktemp, in .claude/logs or else in $TMPDIR, and with
    # neither the runner runs uncaptured; the verdict is its exit status.
    print("== RR1-EMB-1: the verdict never depends on the capture file ==")
    NOTE = sgt.RUNNER_NO_CAPTURE_NOTE
    logs = os.path.join(d, ".claude", "logs")
    alt_tmp = os.path.join(scratch, "alt-tmp")
    os.makedirs(alt_tmp)
    henv = dict(os.environ, TMPDIR=alt_tmp)

    def _restore_logs():
        if os.path.islink(logs) or os.path.isfile(logs):
            os.remove(logs)
        os.makedirs(logs, exist_ok=True)
        os.chmod(logs, 0o755)

    def _break(how):
        if how == "unwritable":
            os.chmod(logs, 0o555)
        else:
            shutil.rmtree(logs)
            if how == "a regular file":
                open(logs, "w").close()
            else:
                os.symlink(os.path.join(scratch, "nowhere"), logs)

    # The header's log() may add its own redirection error after the
    # reason (the header is frozen), so these rows look for the reason, not
    # for the last line.
    root = os.geteuid() == 0
    for how in ("unwritable", "a regular file", "a dangling symlink"):
        if root and how == "unwritable":
            continue
        _break(how)
        try:
            runner(d, "echo fine; exit 0\n")
            for hook, cmd, _, _f in GATES:
                rc, out, err, _ = shell(d, hook, cmd, henv)
                check(f"{hook} shell, .claude/logs {how}: a passing runner "
                      f"allows", rc == 0 and out == b"", repr((rc, err[-200:])))
            runner(d, "echo red; exit 3\n")
            rc, _, err, _ = shell(d, "test-gate", "git commit -m x", henv)
            check(f"test-gate shell, .claude/logs {how}: exit 3 reported, "
                  f"output captured in $TMPDIR",
                  rc == 2 and b"red\nCommit blocked: tests failing "
                  b"(exit 3).\n" in err, repr(err[-200:]))
            check(f".claude/logs {how}: nothing left in $TMPDIR",
                  os.listdir(alt_tmp) == [], repr(os.listdir(alt_tmp)))
        finally:
            _restore_logs()

    # ---- B-2: a set but bad TMPDIR falls back to /tmp, as the SDK does -- #
    # Measured before the fix: with .claude/logs a regular file and TMPDIR
    # missing or unwritable, all three shell gates printed the no-capture
    # note and dropped the runner's output, while the SDK's tempfile
    # skipped the bad TMPDIR, used /tmp and showed it.
    print("== B-2: a bad TMPDIR still captures, through /tmp ==")
    _break("a regular file")
    try:
        runner(d, "echo B2-OUT; exit 1\n")
        for bad in (os.path.join(scratch, "no-such-dir"), "/proc"):
            benv = dict(os.environ, TMPDIR=bad)
            for hook, cmd, last, fname in GATES:
                rc, out, err, _ = shell(d, hook, cmd, benv)
                check(f"{hook} shell, .claude/logs a regular file, TMPDIR="
                      f"{bad}: the output is captured",
                      rc == 2 and (b"B2-OUT\n" + last.encode()) in err
                      and NOTE.encode() not in err, repr((rc, err[-300:])))
                if fname:
                    old_t = os.environ.get("TMPDIR")
                    os.environ["TMPDIR"] = bad
                    tempfile.tempdir = None
                    try:
                        r, _ = sdk(d, fname, cmd)
                    finally:
                        if old_t is None:
                            del os.environ["TMPDIR"]
                        else:
                            os.environ["TMPDIR"] = old_t
                        tempfile.tempdir = None
                    check(f"{fname} SDK, TMPDIR={bad}: the same output",
                          reason(r) == last + "\nB2-OUT", repr(r))
    finally:
        _restore_logs()

    if not root:
        # No place can hold the file: the runner still runs. mktemp is
        # made to fail outright (a shim first on PATH), because /tmp, the
        # last arm, cannot be made unwritable without root.
        os.chmod(logs, 0o555)
        shim = os.path.join(scratch, "no-mktemp")
        os.makedirs(shim, exist_ok=True)
        with open(os.path.join(shim, "mktemp"), "w") as fh:
            fh.write("#!/bin/sh\nexit 1\n")
        os.chmod(os.path.join(shim, "mktemp"), 0o755)
        nenv = dict(os.environ, TMPDIR=os.path.join(scratch, "no-such-dir"),
                    PATH=shim + os.pathsep + os.environ.get("PATH", ""))
        try:
            runner(d, "echo fine; exit 0\n")
            for hook, cmd, _, _f in GATES:
                rc, out, err, _ = shell(d, hook, cmd, nenv)
                check(f"{hook} shell, no temp file anywhere: a passing "
                      f"runner allows", rc == 0 and out == b"",
                      repr((rc, err[-200:])))
            runner(d, "echo RED-OUT; exit 3\n")
            rc, _, err, _ = shell(d, "test-gate", "git commit -m x", nenv)
            check("test-gate shell, no temp file anywhere: the note, then "
                  "exit 3 (the runner ran)",
                  rc == 2 and (NOTE + "\nCommit blocked: tests failing "
                               "(exit 3).\n").encode() in err
                  and b"RED-OUT" not in err,
                  repr(err[-300:]))
        finally:
            _restore_logs()

    # The SDK twin: tempfile.TemporaryFile fails, the runner still runs.
    sdk(d, "test_gate", "ls")  # loads the module
    mod = _mod[d]
    real_tf = mod.tempfile

    def _no_tf(*a, **k):
        raise OSError(28, "No space left on device")
    mod.tempfile = types.SimpleNamespace(TemporaryFile=_no_tf)

    def _sdk_or_exc(fname, cmd):
        """The gate's result, or the exception it raised (a row, not a
        crash of this file)."""
        try:
            return sdk(d, fname, cmd)[0]
        except Exception as e:  # noqa: BLE001
            return {"raised": repr(e)}
    try:
        runner(d, "echo fine; exit 0\n")
        for _h, cmd, _, fname in GATES:
            if fname:
                r = _sdk_or_exc(fname, cmd)
                check(f"{fname} SDK, no temp file: a passing runner allows",
                      r == {}, repr(r))
        runner(d, "echo red; exit 3\n")
        r = _sdk_or_exc("test_gate", "git commit -m x")
        check("test_gate SDK, no temp file: exit 3 and the same note",
              reason(r) == "Commit blocked: tests failing (exit 3).\n" + NOTE,
              repr(r))
    finally:
        mod.tempfile = real_tf

    # ---- RR1-EMB-2: a planted symlink is never written through --------- #
    # Measured before the fix: the file was .claude/logs/<hook>.$$.out,
    # opened with `>`, so symlinks planted over the coming PIDs made the
    # next gate run truncate and overwrite their target.
    print("== RR1-EMB-2: symlinks planted in .claude/logs ==")
    ns = "/proc/sys/kernel/ns_last_pid"
    if os.path.exists(ns):
        victim = os.path.join(scratch, "victim.txt")
        with open(victim, "w") as fh:
            fh.write("ORIGINAL\n")
        runner(d, "echo PLANTED; exit 0\n")
        for hook, cmd, _, _f in GATES:
            planted = []
            n = int(open(ns).read())
            for pid in range(n + 1, n + 2000):
                link = os.path.join(logs, "%s.%d.out" % (hook, pid))
                os.symlink(victim, link)
                planted.append(link)
            try:
                rc, _, err, _ = shell(d, hook, cmd)
            finally:
                # The pre-fix hook's `rm -f` removed the link at its own
                # PID, so a missing one is not an error.
                for link in planted:
                    if os.path.lexists(link):
                        os.remove(link)
            check(f"{hook} shell: allowed, and the symlink target is "
                  f"untouched", rc == 0
                  and open(victim).read() == "ORIGINAL\n",
                  repr((rc, open(victim).read()[:60])))

    # ---- LD-1: eval-gate says other push gates may block too ------------ #
    print("== LD-1: one exit-2 reason per tool call ==")
    runner(d, "echo EVAL-RED; exit 1\n")
    rc, _, err, _ = shell(d, "eval-gate", "git push")
    import templates
    note = getattr(templates, "EVAL_OTHER_GATES_NOTE", None)
    check("eval-gate shell: the failure message ends with the "
          "other-push-gates line",
          rc == 2 and note is not None
          and err.endswith(("Push blocked: evals failing (exit 1).\n"
                            + note + "\n").encode()), repr(err[-200:]))
    # The SDK has no ci-mirror, so its reason carries no such line.
    r, _ = sdk(d, "eval_gate", "git push")
    check("eval-gate SDK: no other-push-gates line (no ci-mirror there)",
          reason(r) == "Push blocked: evals failing (exit 1).\nEVAL-RED",
          repr(reason(r)[-200:]))
    os.remove(os.path.join(d, "r.sh"))
    rc, _, err, _ = shell(d, "eval-gate", "git push")
    check("eval-gate shell: the 127 arm also ends with the line",
          rc == 2 and note is not None
          and err.endswith((note + "\n").encode()), repr(err[-200:]))
finally:
    shutil.rmtree(scratch, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

#!/usr/bin/env python3
"""[WP2 / X-36z + D9] eval-gate: the upstream range runs, commands.eval is
run, local merges are not gated, and the marker fallback must be fresh.

Behavioural, on BOTH substrates, from a real install:
  * X-36z: the shell hook emitted a doubled-brace upstream revision in a
    non-f-string body, so its upstream range never ran and a push whose
    prompt change sits behind a later commit was ALLOWED (measured at
    c642731). The SDK denied it.
  * D9: with commands.eval set, the gate RUNS it on a push touching
    a prompt file (pass -> allow, fail -> deny with the runner's last
    RUNNER_TAIL_LINES lines, 127 -> deny naming the command), and does NOT
    run it when no prompt file is touched. With commands.eval empty, the
    .last-eval-pass marker is the fallback, and it must be newer than every
    touched prompt file (PRD :775).
  * Pushes only (operator decision 2026-10-04): no merge spelling is gated
    and none runs commands.eval, because a PreToolUse hook cannot see the
    incoming tree. The push after a merge is gated on the merged tree.
  * Every deny arm writes "eval-gate BLOCK <reason>" to .claude/logs/hooks.log.
  * Wiring: eval-gate declares timeout 600 on both substrates; the marker
    deny rules are emitted only for the marker fallback; RESOLVED_CONFIG and
    tech.md carry commands.eval only where eval-gate is installed.
  * Config: the validator refuses a newline or an unbalanced quote in
    commands.eval, and both interview front-ends round-trip commands_eval,
    default it on an older file, and fail loud on a deleted line.

Run: python3 tests/test_eval_gate.py
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
from pathlib import Path

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

import defaults  # noqa: E402
import interview as IV  # noqa: E402
import retrofit_interview as RIV  # noqa: E402
from inventory_scan import scan_repo  # noqa: E402
from retrofit_heuristics import build_retrofit_proposal  # noqa: E402
from sdk_gates_template import RUNNER_TAIL_LINES  # noqa: E402
from templates import EVAL_OTHER_GATES_NOTE, _tech  # noqa: E402

CFG = """gate_substrate: "sdk-callable"
project:
  name: evalprobe
  archetype: ai-agent
  shell: bash
secrets:
  enabled: false
deps:
  enabled: false
hooks:
  spec_gate_commit: false
commands:
  test: "true"
  lint: "true"
  format: "true"
  ci_local: "true"
"""
GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
MSG_PUSH = "Eval gate: run evals before pushing prompt changes."


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, env=GIT_ENV,
                          capture_output=True, text=True).stdout


def install(scratch, eval_cmd):
    """A real install into a repo with an upstream."""
    d = os.path.join(scratch, "proj")
    bare = os.path.join(scratch, "remote.git")
    os.makedirs(d)
    subprocess.run(["git", "init", "-q", "--bare", bare], check=True)
    _git(d, "init", "-q", "-b", "main")
    _git(d, "commit", "-q", "--allow-empty", "-m", "root")
    cfg = CFG + (f"  eval: {json.dumps(eval_cmd)}\n" if eval_cmd else "")
    with open(os.path.join(scratch, "c.yaml"), "w") as fh:
        fh.write(cfg)
    r = subprocess.run([sys.executable, BIN, "-c",
                        os.path.join(scratch, "c.yaml"), "-C", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    _git(d, "add", "-A")
    _git(d, "commit", "-qm", "install")
    _git(d, "remote", "add", "origin", bare)
    _git(d, "push", "-q", "-u", "origin", "HEAD")
    return d, r.stderr


def commit_file(d, rel, msg):
    p = os.path.join(d, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        fh.write(msg + "\n")
    _git(d, "add", "-A")
    _git(d, "commit", "-qm", msg)


def _log(d):
    try:
        return open(os.path.join(d, ".claude", "logs", "hooks.log"),
                    errors="replace").read()
    except OSError:
        return ""


def shell(d, command="git push", cwd=None):
    """(rc, stdout, stderr, the hooks.log lines this call added). `cwd` is
    the hook's working directory (the session's), `d` by default."""
    before = len(_log(d))
    payload = json.dumps({"session_id": "s", "hook_event_name": "PreToolUse",
                          "tool_name": "Bash",
                          "tool_input": {"command": command}})
    r = subprocess.run(["bash", os.path.join(d, ".claude", "hooks",
                                             "eval-gate.sh")],
                       input=payload, capture_output=True, text=True,
                       errors="replace", cwd=cwd or d,
                       env=dict(os.environ, CLAUDE_PROJECT_DIR=d))
    return r.returncode, r.stdout, r.stderr, _log(d)[before:]


_mods = {}


def _gates(d):
    if d not in _mods:
        spec = importlib.util.spec_from_file_location(
            "gates_%d" % len(_mods),
            os.path.join(d, ".claude", "sdk_gates", "gates.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _mods[d] = mod
    return _mods[d]


def sdk(d, command="git push"):
    mod = _gates(d)
    hooks = mod.build_hooks(mod.RESOLVED_CONFIG)
    for m in hooks["PreToolUse"]:
        for f in m.hooks:
            if f.__name__ == "eval_gate":
                old = os.environ.get("CLAUDE_PROJECT_DIR")
                os.environ["CLAUDE_PROJECT_DIR"] = d
                try:
                    r = asyncio.run(f({"tool_input": {"command": command}},
                                      "t", None))
                finally:
                    if old is None:
                        del os.environ["CLAUDE_PROJECT_DIR"]
                    else:
                        os.environ["CLAUDE_PROJECT_DIR"] = old
                return r, m.timeout
    raise AssertionError("eval_gate not built")


def reason(r):
    return r.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")


def both(d, command, label, want_rc, want_reason, log_has=None, cwd=None):
    """One shell row and one SDK row for the same command. want_reason is
    the deny reason's FIRST line on both substrates (None for an allow);
    the shell prints it as its last stderr line."""
    rc, out, err, dl = shell(d, command, cwd)
    lines = err.rstrip("\n").split("\n")
    ok = rc == want_rc and out == ""
    if want_reason is not None:
        ok = ok and want_reason in lines
    check(f"shell: {label} -> exit {want_rc}", ok,
          repr((rc, out, err[-400:])))
    if log_has is not None:
        check(f"shell: {label} logs 'eval-gate BLOCK {log_has}'",
              f"eval-gate BLOCK {log_has}" in dl, repr(dl))
    r, _ = sdk(d, command)
    if want_reason is None:
        check(f"SDK: {label} -> allow", r == {}, repr(r))
    else:
        check(f"SDK: {label} -> deny, same reason",
              reason(r).split("\n")[0] == want_reason, repr(r)[:400])
    return err, r


def fresh_project(eval_cmd):
    scratch = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
    d, inst_err = install(scratch, eval_cmd)
    return scratch, d, inst_err


def body_of(d):
    return open(os.path.join(d, ".claude", "hooks", "eval-gate.sh")).read()


def settings_of(d):
    return json.load(open(os.path.join(d, ".claude", "settings.json")))


def eval_timeout(settings):
    for g in settings["hooks"]["PreToolUse"]:
        for h in g["hooks"]:
            if h["command"].endswith("/eval-gate.sh") or \
                    h["command"].endswith('/eval-gate.sh"'):
                return h.get("timeout")
    return None


def parses_to(parse, text, key):
    """parse(text)[key], or the ValueError's text: a regression then
    reports FAIL instead of ending the run."""
    try:
        return parse(text)[key]
    except ValueError as exc:
        return "ValueError: %s" % exc


def set_mtime(d, rel, t):
    os.utime(os.path.join(d, rel), (t, t))


# ---------------------------------------------------------------------- #
print("== X-36z: the upstream range runs on the shell substrate ==")
scratch, d, inst_err = fresh_project("")
try:
    body = body_of(d)
    check("emitted hook carries no doubled-brace revision",
          "@{{u}}" not in body and "'@{u}..HEAD'" in body)
    commit_file(d, "prompts/system.txt", "prompt")
    commit_file(d, "notes.txt", "notes")
    both(d, "git push", "prompt change behind a later commit, no marker",
         2, MSG_PUSH, "prompt changes without an eval pass")
    check("marker fallback: install warns that commands.eval is empty",
          "warning: commands.eval is empty" in inst_err, inst_err)
    check("marker fallback: Write/Edit denies are emitted",
          "Write(.claude/.last-eval-pass)"
          in settings_of(d).get("permissions", {}).get("deny", []))

    print("\n== the marker fallback must be newer than the prompt ==")
    mark = os.path.join(".claude", ".last-eval-pass")
    open(os.path.join(d, mark), "w").write("ok\n")
    set_mtime(d, "prompts/system.txt", 1_700_000_000)
    set_mtime(d, mark, 1_700_000_010)
    both(d, "git push", "marker newer than the prompt", 0, None)
    set_mtime(d, "prompts/system.txt", 1_700_000_020)
    stale = ("Eval gate: prompts/system.txt changed after the last eval "
             "pass; run evals again before pushing.")
    both(d, "git push", "prompt edited after the marker", 2, stale,
         "eval pass older than prompts/system.txt")
    set_mtime(d, mark, 1_700_000_020)
    both(d, "git push", "marker and prompt with the same mtime", 2, stale)
    set_mtime(d, mark, 1_700_000_030)
    both(d, "git push", "marker refreshed after the edit", 0, None)
    # A prompt file the push deletes has no mtime to compare: skipped.
    _git(d, "rm", "-q", "prompts/system.txt")
    _git(d, "commit", "-qm", "drop prompt")
    both(d, "git push", "push deleting the prompt, marker present", 0, None)

finally:
    shutil.rmtree(scratch, ignore_errors=True)

# ---------------------------------------------------------------------- #
print("\n== D9: commands.eval is run ==")
scratch, d, inst_err = fresh_project("touch EVAL_RAN; echo EVAL-STDOUT")
try:
    commit_file(d, "prompts/system.txt", "prompt")
    commit_file(d, "notes.txt", "notes")
    rc, out, err, _ = shell(d)
    check("pass: shell exit 0", rc == 0, err)
    check("pass: runner stdout goes to stderr, never hook stdout",
          out == "" and "EVAL-STDOUT" in err, repr((out, err)))
    check("pass: the command really ran",
          os.path.exists(os.path.join(d, "EVAL_RAN")))
    if os.path.exists(os.path.join(d, "EVAL_RAN")):
        os.remove(os.path.join(d, "EVAL_RAN"))
    r, tmo = sdk(d)
    check("pass: SDK allows", r == {}, repr(r))
    check("pass: the SDK ran the command too",
          os.path.exists(os.path.join(d, "EVAL_RAN")))
    st = settings_of(d)
    check("eval set: no marker deny rules",
          not any(".last-eval-pass" in x for x in
                  st.get("permissions", {}).get("deny", [])))
    check("eval set: no empty-command warning",
          "commands.eval is empty" not in inst_err, inst_err)
    check("timeout 600 on the shell registration",
          eval_timeout(st) == 600, repr(eval_timeout(st)))
    check("timeout 600 on the SDK HookMatcher", tmo == 600.0, repr(tmo))
    mod = _gates(d)
    check("RESOLVED_CONFIG carries commands.eval",
          mod.RESOLVED_CONFIG["commands"].get("eval")
          == "touch EVAL_RAN; echo EVAL-STDOUT",
          repr(mod.RESOLVED_CONFIG["commands"]))
    tech = open(os.path.join(d, ".claude", "steering", "tech.md")).read()
    check("tech.md: an Eval row carrying the command",
          "| Eval      | `touch EVAL_RAN; echo EVAL-STDOUT` |" in tech, tech)
    check("tech.md: the contract sentence says eval-gate runs Eval",
          "`eval-gate` runs Eval before a push that touches" in tech, tech)
finally:
    shutil.rmtree(scratch, ignore_errors=True)

scratch, d, _ = fresh_project("echo EVAL-FAIL-DETAIL; exit 3")
try:
    commit_file(d, "prompts/system.txt", "prompt")
    commit_file(d, "notes.txt", "notes")
    err, r = both(d, "git push", "eval failing", 2,
                  "Push blocked: evals failing (exit 3).",
                  "evals failing (exit 3)")
    check("fail: the runner's stdout reaches the shell's stderr",
          "EVAL-FAIL-DETAIL" in err, repr(err))
    check("fail: the SDK reason carries the runner's output",
          reason(r) == "Push blocked: evals failing (exit 3).\n"
                       "EVAL-FAIL-DETAIL", repr(r))
    open(os.path.join(d, ".claude", ".last-eval-pass"), "w").write("ok\n")
    both(d, "git push", "eval failing with a marker present (not read)", 2,
         "Push blocked: evals failing (exit 3).")
finally:
    shutil.rmtree(scratch, ignore_errors=True)

N = RUNNER_TAIL_LINES + 50
scratch, d, _ = fresh_project(f"seq -f TAILLINE-%g 1 {N}; exit 1")
try:
    commit_file(d, "prompts/system.txt", "prompt")
    rc, out, err, _ = shell(d)
    shown = [ln for ln in err.split("\n") if ln.startswith("TAILLINE-")]
    check(f"tail: the shell shows the last {RUNNER_TAIL_LINES} lines only",
          rc == 2 and out == "" and len(shown) == RUNNER_TAIL_LINES
          and shown[0] == f"TAILLINE-{N - RUNNER_TAIL_LINES + 1}"
          and shown[-1] == f"TAILLINE-{N}", repr((rc, shown[:2])))
    r, _ = sdk(d)
    sl = reason(r).split("\n")
    check(f"tail: the SDK reason carries the same {RUNNER_TAIL_LINES} lines",
          sl[0] == "Push blocked: evals failing (exit 1)." and sl[1:] == shown,
          repr(sl[:3]))
finally:
    shutil.rmtree(scratch, ignore_errors=True)

scratch, d, _ = fresh_project("no-such-eval-tool-x9 run")
try:
    commit_file(d, "prompts/system.txt", "prompt")
    rc, out, err, dl = shell(d)
    check("127: the shell names the missing command and the fix",
          rc == 2 and out == ""
          and "Push blocked: eval command not found (exit 127): "
          "no-such-eval-tool-x9 run" in err.split("\n")
          # [WP2 review LD-1] then the other-push-gates line: this install
          # has ci-mirror (tests/test_runner_output.py).
          and err.endswith("Install the toolchain or fix commands.eval in "
                           "bootstrap.config.yaml.\n"
                           + EVAL_OTHER_GATES_NOTE + "\n"), repr(err))
    check("127: the shell logs 'eval-gate BLOCK eval command not found "
          "(exit 127)'",
          "eval-gate BLOCK eval command not found (exit 127)" in dl,
          repr(dl))
    r, _ = sdk(d)
    check("127: the SDK names the missing command",
          reason(r).split("\n")[0] == "Push blocked: eval command not found "
          "(exit 127): no-such-eval-tool-x9 run", repr(r))
finally:
    shutil.rmtree(scratch, ignore_errors=True)

scratch, d, _ = fresh_project("touch EVAL_RAN; exit 1")
try:
    commit_file(d, "notes.txt", "notes")
    both(d, "git push", "no prompt file in the push", 0, None)
    check("no prompt file: the eval never ran",
          not os.path.exists(os.path.join(d, "EVAL_RAN")))
finally:
    shutil.rmtree(scratch, ignore_errors=True)

# ---------------------------------------------------------------------- #
print("\n== WP2 review C-eval: which prompt files, and how fresh ==")
# [SC-2 / SDK-P3] git C-quotes a name with a non-ASCII byte, a `"` or a
# control character under core.quotePath, and a name the gate cannot find
# was skipped as if the push deleted it, so a stale marker passed. Names are
# now read NUL-separated (`-z`, which never quotes).
STALE = 1_600_000_000
scratch, d, _ = fresh_project("")
try:
    mark = os.path.join(".claude", ".last-eval-pass")
    for rel in ("prompts/caf\u00e9.txt", 'prompts/q"uote.txt',
                "prompts/tab\there.txt"):
        commit_file(d, rel, "prompt " + rel)
        open(os.path.join(d, mark), "w").write("ok\n")
        set_mtime(d, mark, STALE)
        both(d, "git push", "stale marker, prompt named %r" % rel, 2,
             "Eval gate: %s changed after the last eval pass; run evals "
             "again before pushing." % rel, "eval pass older than " + rel)
        _git(d, "push", "-q")
    # [PR #120 step 7, EP-1] A name that is not valid UTF-8 (a raw 0xE9
    # byte). The SDK decoded git's output with errors="replace", so the
    # name became U+FFFD, named no file, and a stale marker passed while
    # the shell denied. Both now deny, and both show the byte as U+FFFD.
    # [RR3-6] A filesystem that refuses names that are not valid UTF-8
    # (APFS and HFS+ raise EILSEQ) skips these two rows, visibly.
    raw = os.path.join(os.fsencode(d), b"prompts", b"sys\xe9.txt")
    try:
        with open(raw, "wb") as fh:
            fh.write(b"p\n")
    except OSError as e:
        raw = None
        check("SKIPPED: raw 0xE9 prompt-name rows (filesystem rejects "
              "non-UTF-8 names: %s)" % e, True)
    if raw is not None:
        _git(d, "add", "-A")
        _git(d, "commit", "-qm", "latin-1 prompt name")
        open(os.path.join(d, mark), "w").write("ok\n")
        set_mtime(d, mark, STALE)
        os.utime(raw, (STALE + 10, STALE + 10))
        both(d, "git push", "stale marker, prompt name with a raw 0xE9 byte",
             2, "Eval gate: prompts/sys\ufffd.txt changed after the last "
             "eval pass; run evals again before pushing.")
        set_mtime(d, mark, STALE + 20)
        both(d, "git push", "fresh marker, prompt name with a raw 0xE9 byte",
             0, None)
finally:
    shutil.rmtree(scratch, ignore_errors=True)

# [PR #120 step 7, M-2] The PROJECT directory's name is not valid UTF-8 (a
# tree moved or cloned there after install; the installer cannot print such
# a target). `git rev-parse --show-toplevel` must be decoded with
# os.fsdecode too: decoded with errors="replace", the top named no
# directory, every `top / f` named no file, and a stale marker passed on the
# SDK while the shell denied.
scratch, d0, _ = fresh_project("")
try:
    d = os.fsdecode(os.path.join(os.fsencode(scratch), b"proj\xe9"))
    try:
        os.rename(d0, d)
    except OSError as e:
        # [RR3-6] As above: a filesystem that refuses the name skips the
        # rows, visibly, instead of aborting the rest of the file.
        d = None
        check("SKIPPED: raw 0xE9 project-directory rows (filesystem "
              "rejects non-UTF-8 names: %s)" % e, True)
    if d is not None:
        mark = os.path.join(".claude", ".last-eval-pass")
        commit_file(d, "prompts/sys.txt",
                    "prompt in a non-UTF-8 project dir")
        open(os.path.join(d, mark), "w").write("ok\n")
        set_mtime(d, mark, STALE)
        set_mtime(d, "prompts/sys.txt", STALE + 10)
        both(d, "git push", "stale marker, project directory name with a raw "
             "0xE9 byte", 2,
             "Eval gate: prompts/sys.txt changed after the last eval pass; "
             "run evals again before pushing.")
        set_mtime(d, mark, STALE + 20)
        both(d, "git push", "fresh marker, project directory name with a raw "
             "0xE9 byte", 0, None)
finally:
    shutil.rmtree(scratch, ignore_errors=True)

# [SC-2] CLAUDE_PROJECT_DIR is a subdirectory of the repo: git prints paths
# from the repo top, so they are resolved against `rev-parse
# --show-toplevel`, and the root-commit listing is `--full-tree` (from a
# subdirectory `ls-tree` lists that subdirectory only, relative to it).
scratch = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
try:
    top = os.path.join(scratch, "top")
    d = os.path.join(top, "app")
    os.makedirs(d)
    _git(top, "init", "-q", "-b", "main")
    with open(os.path.join(scratch, "c.yaml"), "w") as fh:
        fh.write(CFG)
    r = subprocess.run([sys.executable, BIN, "-c",
                        os.path.join(scratch, "c.yaml"), "-C", d],
                       capture_output=True, text=True)
    check("subdir install: exit 0", r.returncode == 0, r.stderr[-400:])
    os.makedirs(os.path.join(d, "prompts"))
    open(os.path.join(d, "prompts", "sys.txt"), "w").write("p\n")
    _git(top, "add", "-A")
    _git(top, "commit", "-qm", "root")
    mark = os.path.join(".claude", ".last-eval-pass")
    open(os.path.join(d, mark), "w").write("ok\n")
    set_mtime(d, mark, STALE)
    # Every installed file is older than nothing here but the stale marker,
    # so the reason names the first prompt-named path in tree order.
    first = sorted(f for f in _git(top, "ls-files").splitlines()
                   if "rompt" in f)[0]
    both(d, "git push", "subdir project, root commit, stale marker", 2,
         "Eval gate: %s changed after the last eval pass; run evals again "
         "before pushing." % first)
    commit_file(d, "prompts/two.txt", "p2")
    set_mtime(d, mark, STALE)
    both(d, "git push", "subdir project, second commit, stale marker", 2,
         "Eval gate: app/prompts/two.txt changed after the last eval pass; "
         "run evals again before pushing.")
    set_mtime(d, mark, time.time() + 60)
    both(d, "git push", "subdir project, fresh marker", 0, None)
finally:
    shutil.rmtree(scratch, ignore_errors=True)

# [SDK-P2] commands.eval runs in the project root on both substrates, not in
# the session's current directory.
scratch, d, _ = fresh_project("sh ./e.sh")
try:
    open(os.path.join(d, "e.sh"), "w").write("touch EVAL_RAN\n")
    os.makedirs(os.path.join(d, "src"))
    commit_file(d, "prompts/system.txt", "prompt")
    both(d, "git push", "relative eval command, hook cwd in src/", 0, None,
         cwd=os.path.join(d, "src"))
    check("relative eval command: it ran in the project root",
          os.path.exists(os.path.join(d, "EVAL_RAN"))
          and not os.path.exists(os.path.join(d, "src", "EVAL_RAN")))
finally:
    shutil.rmtree(scratch, ignore_errors=True)

# ---------------------------------------------------------------------- #
# [WP2 fix round 2, operator decision 2026-10-04] PUSHES ONLY. The merge arm
# the fix round added is gone: a PreToolUse hook runs before the merge and
# cannot see the incoming tree (re-review CR-1), and its ref parsing falsely
# denied ordinary merges (C-1, C-5, RS-1) and missed others (C-3, RS-2). The
# push that follows evaluates the merged tree before anything leaves the
# machine. Every merge spelling the re-review listed is allowed here with no
# eval run: commands.eval writes a sentinel and FAILS, so a run would both
# deny and leave the sentinel. Most refs below DO bring in a prompt change.
MERGE_SPELLINGS = (
    # C-1: a later bare `merge`, attached option values, a heredoc body.
    'git merge docs || (git add -A && git commit -m "resolve merge '
    'conflicts")',
    'git merge docs; git commit -am "fix merge conflict"',
    "git merge docs && echo merge complete",
    'git merge --message="Merge the feature"',
    'git merge -m"Merge it"',
    'git merge -m "Merge \\"docs\\" now"',
    "git merge docs -F - <<EOF\nmerge notes\nEOF",
    # C-3: `-` is @{-1} (topic here); bare `git merge` takes @{u}, which is
    # ahead by topic's prompt change; and the explicit forms.
    "git merge -", "git merge --ff-only -", "git merge",
    "git merge --ff-only @{u}", "git merge FETCH_HEAD", "git merge @{-1}",
    # C-5: a ref that does not exist.
    "git merge nosuchbranch",
    # RS-1: the ref exists only after an earlier segment runs.
    "git fetch origin && git merge origin/newfeat",
    "git fetch origin; git merge origin/newfeat",
    "git branch topic2 topic && git merge topic2",
    # RS-2: a branch change before the merge.
    "git checkout docs && git merge main",
    "git switch docs; git merge main",
    # Plain merges of a prompt-touching branch.
    "git merge topic", "git merge --no-ff -m 'take topic' topic",
    "bash -c 'git merge topic'",
)
MERGE_HEAD_SPELLINGS = ("git commit -m 'merge topic'", "git merge --continue")


def merge_fixture(d):
    """topic and newfeat change a prompt; docs does not; main is one prompt
    commit behind its upstream (topic's, pushed as main), and @{-1} is
    topic. newfeat is on the remote and not fetched."""
    _git(d, "checkout", "-q", "-b", "topic")
    commit_file(d, "prompts/agent.txt", "agent prompt")
    _git(d, "checkout", "-q", "-b", "newfeat", "main")
    commit_file(d, "prompts/new.txt", "new prompt")
    _git(d, "push", "-q", "origin", "newfeat")
    _git(d, "update-ref", "-d", "refs/remotes/origin/newfeat")
    _git(d, "checkout", "-q", "-b", "docs", "main")
    commit_file(d, "docs/a.txt", "docs")
    _git(d, "checkout", "-q", "topic")
    _git(d, "checkout", "-q", "main")
    _git(d, "push", "-q", "origin", "topic:main")
    _git(d, "fetch", "-q", "origin")
    _git(d, "fetch", "-q", "origin", "main")    # FETCH_HEAD = topic


def merge_rows(d, arm):
    sentinel = os.path.join(d, "EVAL_RAN")
    for cmd in MERGE_SPELLINGS + ("MERGE_HEAD",):
        cmds = (MERGE_HEAD_SPELLINGS if cmd == "MERGE_HEAD" else (cmd,))
        mh = os.path.join(d, ".git", "MERGE_HEAD")
        if cmd == "MERGE_HEAD":
            open(mh, "w").write(_git(d, "rev-parse", "topic"))
        for c in cmds:
            label = "%s: merge allowed: %s" % (arm, c.replace("\n", "\\n"))
            if cmd == "MERGE_HEAD":
                label += " (MERGE_HEAD = topic)"
            both(d, c, label, 0, None)
            check(label + " -> eval not run", not os.path.exists(sentinel))
            if os.path.exists(sentinel):
                os.remove(sentinel)
        if os.path.exists(mh):
            os.remove(mh)


print("\n== pushes only: no merge spelling is gated ==")
for arm, ev in (("eval set", "touch EVAL_RAN; exit 1"),
                ("marker fallback", "")):
    scratch, d, _ = fresh_project(ev)
    try:
        merge_fixture(d)
        # The control: the same install DOES gate a push of a prompt.
        _git(d, "checkout", "-q", "newfeat")
        _git(d, "branch", "-q", "-u", "origin/main")
        both(d, "git push", "%s: control, a push of topic's prompt is "
             "gated" % arm, 2,
             "Push blocked: evals failing (exit 1)." if ev else MSG_PUSH)
        sentinel = os.path.join(d, "EVAL_RAN")
        check("%s: control, the push ran the eval" % arm,
              os.path.exists(sentinel) == bool(ev))
        if os.path.exists(sentinel):
            os.remove(sentinel)
        _git(d, "checkout", "-q", "topic")    # @{-1} is topic again
        _git(d, "checkout", "-q", "main")
        merge_rows(d, arm)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

print("\n== pushes only: the push after a merge is gated ==")
scratch, d, _ = fresh_project("")
try:
    mark = os.path.join(d, ".claude", ".last-eval-pass")
    _git(d, "checkout", "-q", "-b", "topic")
    commit_file(d, "prompts/agent.txt", "agent prompt")
    _git(d, "checkout", "-q", "main")
    open(mark, "w").write("ok\n")
    os.utime(mark, (time.time() - 3600,) * 2)
    _git(d, "merge", "-q", "--no-ff", "-m", "merge topic", "topic")
    both(d, "git push", "marker older than a merge that brought a prompt "
         "change", 2, "Eval gate: prompts/agent.txt changed after the last "
         "eval pass; run evals again before pushing.",
         "eval pass older than prompts/agent.txt")
    os.utime(mark, (time.time() + 60,) * 2)
    both(d, "git push", "control: marker refreshed after the merge", 0,
         None)
finally:
    shutil.rmtree(scratch, ignore_errors=True)

for ev, want, tag in (("touch EVAL_RAN; exit 1", 2, "failing"),
                     ("touch EVAL_RAN", 0, "passing")):
    scratch, d, _ = fresh_project(ev)
    try:
        _git(d, "checkout", "-q", "-b", "topic")
        commit_file(d, "prompts/agent.txt", "agent prompt")
        _git(d, "checkout", "-q", "main")
        _git(d, "merge", "-q", "--no-ff", "-m", "merge topic", "topic")
        sentinel = os.path.join(d, "EVAL_RAN")
        rc, out, err, _ = shell(d)
        check("%s eval: the push after a merge runs it on the shell, exit %d"
              % (tag, want), rc == want and os.path.exists(sentinel)
              and (want == 0 or "Push blocked: evals failing (exit 1)."
                   in err.split("\n")), repr((rc, err[-300:])))
        if os.path.exists(sentinel):
            os.remove(sentinel)
        r, _ = sdk(d)
        check("%s eval: the push after a merge runs it on the SDK" % tag,
              os.path.exists(sentinel)
              and (r == {} if want == 0 else reason(r).split("\n")[0]
                   == "Push blocked: evals failing (exit 1)."), repr(r))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

# ---------------------------------------------------------------------- #
print("\n== config: validator, tech.md scope ==")
for bad, label in (("pytest\nrm -rf x", "a newline"),
                   ("promptfoo eval -c 'x.yaml", "an unbalanced quote")):
    _, errs = defaults.resolve_config({"project": {"name": "v",
                                                   "archetype": "ai-agent"},
                                       "commands": {"eval": bad}})
    check(f"validator: commands.eval with {label} is refused",
          any("commands.eval" in e for e in errs), repr(errs))
_, errs = defaults.resolve_config({"project": {"name": "v",
                                               "archetype": "ai-agent"},
                                   "commands": {"eval": "promptfoo eval"}})
check("validator control: a plain commands.eval is accepted",
      not any("commands.eval" in e for e in errs), repr(errs))
cli, _ = defaults.resolve_config({"project": {"name": "v",
                                              "archetype": "cli"},
                                  "commands": {"eval": "x"}})
check("tech.md: no Eval row where eval-gate is not installed",
      "eval-gate" not in cli["_resolved_hooks"]
      and "| Eval" not in _tech(cli) and "eval-gate" not in _tech(cli))
check("no eval warning where eval-gate is not installed",
      "eval" not in cli["_command_warnings"], repr(cli["_command_warnings"]))

# ---------------------------------------------------------------------- #
print("\n== interviews: commands_eval round-trips ==")
SAMPLE = "An LLM agent that answers support tickets with a system prompt."
prop = IV.build_proposal(SAMPLE)
text = IV.render_interview(prop, "prd.md")
check("greenfield: the file carries the Eval command section",
      "## Eval command" in text.splitlines()
      and "commands_eval: " in text, "")
check("greenfield: empty by default",
      parses_to(IV.parse_interview_answers, text, "commands_eval") == "")
set_text = text.replace("commands_eval: ", "commands_eval: promptfoo eval", 1)
ans = IV.parse_interview_answers(set_text)
check("greenfield: a set value round-trips into the config",
      IV.answers_to_config(ans)["commands"]["eval"] == "promptfoo eval",
      repr(ans.get("commands_eval")))
old = "\n".join(ln for ln in text.splitlines()
                if not ln.startswith("commands_eval:")
                and ln != "## Eval command")
check("greenfield: an older file without the section defaults to ''",
      parses_to(IV.parse_interview_answers, old, "commands_eval") == "")
deleted = "\n".join(ln for ln in text.splitlines()
                    if not ln.startswith("commands_eval:"))
try:
    IV.parse_interview_answers(deleted)
    check("greenfield: a deleted line in a current file fails loud", False)
except ValueError as exc:
    check("greenfield: a deleted line in a current file fails loud",
          "commands_eval" in str(exc), str(exc))

rd = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
cwd = os.getcwd()
try:
    with open(os.path.join(rd, "main.py"), "w") as fh:
        fh.write("print(1)\n")
    os.chdir(rd)
    rprop = build_retrofit_proposal(scan_repo(Path(rd)),
                                    project_fallback="pyapp")
    rtext = RIV.render_interview(rprop, Path(rd))
finally:
    os.chdir(cwd)
    shutil.rmtree(rd, ignore_errors=True)
check("retrofit: the file carries the Eval command section",
      RIV.EVAL_SECTION_MARKER in rtext.splitlines()
      and "commands_eval: " in rtext)
check("retrofit: empty by default",
      parses_to(RIV.parse_interview_answers, rtext, "commands_eval") == "")
rans = RIV.parse_interview_answers(
    rtext.replace("commands_eval: ", "commands_eval: promptfoo eval", 1))
check("retrofit: a set value round-trips into the config",
      RIV.answers_to_config(rans, rprop)["commands"]["eval"]
      == "promptfoo eval", repr(rans.get("commands_eval")))
rold = "\n".join(ln for ln in rtext.splitlines()
                 if not ln.startswith("commands_eval:")
                 and ln != RIV.EVAL_SECTION_MARKER)
check("retrofit: an older file without the section defaults to ''",
      parses_to(RIV.parse_interview_answers, rold, "commands_eval") == "")
rdel = "\n".join(ln for ln in rtext.splitlines()
                 if not ln.startswith("commands_eval:"))
try:
    RIV.parse_interview_answers(rdel)
    check("retrofit: a deleted line in a current file fails loud", False)
except ValueError as exc:
    check("retrofit: a deleted line in a current file fails loud",
          "commands_eval" in str(exc), str(exc))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

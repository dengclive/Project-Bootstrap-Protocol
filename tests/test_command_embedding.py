#!/usr/bin/env python3
"""[WP2 review SC-1, IU-1, TP-1, SDK-P1] A configured command reaches the
emitted hooks intact, on both substrates.

commands.test, commands.ci_local, commands.eval and commands.lint are shell
by design: the SDK twin hands each one to `/bin/sh -c`, which runs it
without `set -u`. The shell gates used to splice the same text raw into
`echo "Running ...: <cmd>"` and into `( <cmd> )` under the header's
`set -euo pipefail`. Measured at the pre-fix tree, from a real install:

  * `sh -c "echo RUN >> RAN.log && exit 3"`: bash re-tokenised the echo
    line, so its tail ran at the top level of the hook: `exit 3`, a
    non-blocking exit, before the gate ran the command (SC-1).
  * `... # trailing comment`: the comment ate the subshell's `)`, so the
    hook failed to parse and exited 2 on every Bash call (IU-1).
  * `$UNSET_VAR`: an unbound variable under `set -u` killed the hook at the
    echo line with exit 1, which does not block (TP-1).
  * `   ` (blank): the SDK stripped it to unset, the shell emitted `(   )`,
    a syntax error on every Bash call (SDK-P1).

Each row installs one project whose four commands all carry the same value,
then drives test-gate (`git commit`), ci-mirror and eval-gate (`git push`
with a prompt change) and format-lint-gate (PostToolUse), and the SDK twins
of test-gate, eval-gate and format-lint-gate. The expected outcome is what
`sh -c` does with the value: run it ONCE, and report its exit status.

Run: python3 tests/test_command_embedding.py
"""
import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
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

import defaults  # noqa: E402
from templates import EVAL_OTHER_GATES_NOTE, _tech  # noqa: E402

GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
# The hook and the SDK twin both run without UNSET_VAR in the environment.
HOOK_ENV = {k: v for k, v in os.environ.items() if k != "UNSET_VAR"}
os.environ.pop("UNSET_VAR", None)


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, env=GIT_ENV,
                          capture_output=True, text=True).stdout


def install(scratch, value):
    d = os.path.join(scratch, "proj")
    bare = os.path.join(scratch, "remote.git")
    os.makedirs(d)
    subprocess.run(["git", "init", "-q", "--bare", bare], check=True)
    _git(d, "init", "-q", "-b", "main")
    _git(d, "commit", "-q", "--allow-empty", "-m", "root")
    # Single-quoted YAML: minyaml keeps a backslash in a double-quoted
    # scalar, so `\"` would reach the hook as two characters.
    assert "'" not in value
    v = "'" + value + "'"
    cfg = f"""gate_substrate: "sdk-callable"
project:
  name: embedprobe
  archetype: ai-agent
  shell: bash
secrets:
  enabled: false
deps:
  enabled: false
hooks:
  spec_gate_commit: false
commands:
  test: {v}
  lint: {v}
  format: "true"
  ci_local: {v}
  eval: {v}
"""
    with open(os.path.join(scratch, "c.yaml"), "w") as fh:
        fh.write(cfg)
    r = subprocess.run([sys.executable, BIN, "-c",
                        os.path.join(scratch, "c.yaml"), "-C", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    with open(os.path.join(d, ".gitignore"), "a") as fh:
        fh.write("RAN.log\n")
    _git(d, "add", "-A")
    _git(d, "commit", "-qm", "install")
    _git(d, "remote", "add", "origin", bare)
    _git(d, "push", "-q", "-u", "origin", "HEAD")
    os.makedirs(os.path.join(d, "prompts"))
    with open(os.path.join(d, "prompts", "system.txt"), "w") as fh:
        fh.write("prompt\n")
    _git(d, "add", "-A")
    _git(d, "commit", "-qm", "prompt")
    return d, r.stderr


def ran(d):
    """The RAN.log lines the last call wrote, then clear it."""
    p = os.path.join(d, "RAN.log")
    try:
        with open(p) as fh:
            text = fh.read()
    except OSError:
        return []
    os.remove(p)
    return text.splitlines()


def shell(d, hook, command):
    payload = json.dumps({"session_id": "s", "hook_event_name": "PreToolUse",
                          "tool_name": "Bash",
                          "tool_input": {"command": command}})
    if hook == "format-lint-gate":
        payload = json.dumps({"session_id": "s",
                              "hook_event_name": "PostToolUse",
                              "tool_name": "Write",
                              "tool_input": {"file_path": "x.py"}})
    r = subprocess.run(["bash", os.path.join(d, ".claude", "hooks",
                                             hook + ".sh")],
                       input=payload, capture_output=True, text=True, cwd=d,
                       env=dict(HOOK_ENV, CLAUDE_PROJECT_DIR=d))
    return r.returncode, r.stdout, r.stderr


_mods = {}


def sdk(d, fn, command):
    if d not in _mods:
        spec = importlib.util.spec_from_file_location(
            "gates_%d" % len(_mods),
            os.path.join(d, ".claude", "sdk_gates", "gates.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _mods[d] = mod
    mod = _mods[d]
    hooks = mod.build_hooks(mod.RESOLVED_CONFIG)
    for ev in hooks.values():
        for m in ev:
            for f in m.hooks:
                if f.__name__ == fn:
                    os.environ["CLAUDE_PROJECT_DIR"] = d
                    try:
                        return asyncio.run(
                            f({"tool_input": {"command": command,
                                              "file_path": "x.py"}},
                              "t", None))
                    finally:
                        del os.environ["CLAUDE_PROJECT_DIR"]
    raise AssertionError(fn + " not built")


def reason(r):
    return r.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")


def lint_ctx(out):
    try:
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]
    except (ValueError, KeyError, TypeError):
        return None


# (label, value, what one run writes to RAN.log, the exit status of a run)
RAN_ROWS = (
    ('sh -c "... && ..."', 'sh -c "echo RUN >> RAN.log && exit 3"',
     ["RUN"], 3),
    ("a trailing # comment", "echo RUN >> RAN.log; exit 3 # run the suite",
     ["RUN"], 3),
    ("true # c", "true # c", [], 0),
    ("an unset $UNSET_VAR", 'echo "RUN $UNSET_VAR" >> RAN.log; exit 3',
     ["RUN "], 3),
    ("a for loop over $f", "for f in a b; do echo $f >> RAN.log; done; "
     "exit 3", ["a", "b"], 3),
)

for label, value, lines, rc_run in RAN_ROWS:
    print(f"\n== {label}: {value!r} ==")
    scratch = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
    try:
        d, _ = install(scratch, value)
        ran(d)
        for hook, cmd, deny in (
                ("test-gate", "git commit -m x",
                 "Commit blocked: tests failing (exit %d)." % rc_run),
                ("ci-mirror", "git push", "Push blocked: CI mirror failed."),
                ("eval-gate", "git push",
                 "Push blocked: evals failing (exit %d)." % rc_run)):
            rc, out, err = shell(d, hook, cmd)
            got = ran(d)
            want_rc = 0 if rc_run == 0 else 2
            ok = rc == want_rc and out == "" and got == lines
            # [WP2 review LD-1] eval-gate's push block ends with the
            # other-push-gates line (tests/test_runner_output.py).
            tailw = [deny] + ([EVAL_OTHER_GATES_NOTE]
                              if hook == "eval-gate" else [])
            if want_rc == 2:
                ok = ok and err.rstrip("\n").split("\n")[-len(tailw):] \
                    == tailw
            check(f"shell {hook}: runs it once, exit {want_rc}", ok,
                  repr((rc, out[:200], err[-300:], got)))
            if hook == "test-gate":
                check(f"shell {hook}: the label carries the command verbatim",
                      ("Running test gate: " + value) in err.split("\n"),
                      repr(err[:300]))
        for fn, cmd, deny in (
                ("test_gate", "git commit -m x",
                 "Commit blocked: tests failing (exit %d)." % rc_run),
                ("eval_gate", "git push",
                 "Push blocked: evals failing (exit %d)." % rc_run)):
            r = sdk(d, fn, cmd)
            got = ran(d)
            if rc_run == 0:
                ok = r == {}
            else:
                ok = reason(r).split("\n")[0] == deny
            check(f"SDK {fn}: same verdict, runs it once",
                  ok and got == lines, repr((r, got))[:300])
        rc, out, err = shell(d, "format-lint-gate", None)
        got = ran(d)
        c = lint_ctx(out)
        if rc_run == 0:
            ok = rc == 0 and out == "" and got == lines
        else:
            ok = rc == 0 and got == lines and (c or "").startswith(
                "Lint (commands.lint) failed with exit %d " % rc_run)
        check("shell format-lint-gate: runs it once, reports its status", ok,
              repr((rc, out[:200], err[-300:], got)))
        r = sdk(d, "format_lint_gate", None)
        got = ran(d)
        sc = r.get("hookSpecificOutput", {}).get("additionalContext", "")
        ok = got == lines and (r == {} if rc_run == 0 else sc.startswith(
            "Lint (commands.lint) failed with exit %d " % rc_run))
        check("SDK format_lint_gate: same verdict, runs it once", ok,
              repr((r, got))[:300])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

# ---------------------------------------------------------------------- #
print("\n== a whitespace-only value is unset, on both substrates ==")
scratch = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
try:
    d, inst_err = install(scratch, "   ")
    rc, out, err = shell(d, "test-gate", "ls")
    check("shell test-gate: `ls` is allowed", rc == 0 and out == "",
          repr((rc, err[-300:])))
    rc, out, err = shell(d, "test-gate", "git commit -m x")
    check("shell test-gate: commit denied as TODO (exit 127 arm)",
          rc == 2 and "Commit blocked: test command not found (exit 127): "
          "echo 'TODO: commands.test unset' >&2 && exit 127"
          in err.split("\n"), repr((rc, err[-300:])))
    r = sdk(d, "test_gate", "git commit -m x")
    check("SDK test_gate: commit denied as TODO",
          reason(r).startswith("TODO: commands.test unset"), repr(r))
    rc, out, err = shell(d, "ci-mirror", "git push")
    check("shell ci-mirror: blank ci_local and test check nothing",
          rc == 0 and out == "", repr((rc, err[-300:])))
    for cmd in ("ls", "git status"):
        rc, out, err = shell(d, "eval-gate", cmd)
        check(f"shell eval-gate: `{cmd}` is allowed", rc == 0 and out == "",
              repr((rc, err[-300:])))
        check(f"SDK eval_gate: `{cmd}` is allowed",
              sdk(d, "eval_gate", cmd) == {})
    msg = "Eval gate: run evals before pushing prompt changes."
    rc, out, err = shell(d, "eval-gate", "git push")
    check("shell eval-gate: blank eval falls back to the marker",
          rc == 2 and err.rstrip("\n").split("\n")[-1] == msg,
          repr((rc, err[-300:])))
    check("SDK eval_gate: blank eval falls back to the marker",
          reason(sdk(d, "eval_gate", "git push")) == msg)
    rc, out, err = shell(d, "format-lint-gate", None)
    check("shell format-lint-gate: blank lint is the unset notice",
          rc == 0 and "commands.lint is empty" in out, repr((rc, out, err)))
    for k in ("test", "lint", "eval"):
        check(f"install warns that commands.{k} is empty",
              f"warning: commands.{k} is empty" in inst_err, inst_err)
    mod = _mods.get(d)
    check("RESOLVED_CONFIG carries a blank eval as ''",
          mod is not None and mod.RESOLVED_CONFIG["commands"]["eval"] == "",
          repr(mod and mod.RESOLVED_CONFIG["commands"]))
    tech = open(os.path.join(d, ".claude", "steering", "tech.md")).read()
    check("tech.md: blank Test is the TODO cell",
          "| Test      | `TODO: set commands.test in bootstrap.config.yaml` |"
          in tech, tech)
    check("tech.md: blank Eval is (none), and eval-gate is the marker arm",
          "| Eval      | `(none)` |" in tech
          and "`eval-gate` runs Eval" not in tech, tech)
    check("tech.md: blank CI local is (none)",
          "| CI local  | `(none)` |" in tech, tech)
finally:
    shutil.rmtree(scratch, ignore_errors=True)

print("\n== resolve_config strips every command value ==")
cfg, errs = defaults.resolve_config({
    "project": {"name": "v", "archetype": "ai-agent"},
    "commands": {"test": "  pytest -q  ", "lint": "\t", "eval": " ",
                 "ci_local": " make ci "}})
check("stripped: test, lint, eval, ci_local",
      cfg["commands"]["test"] == "pytest -q"
      and cfg["commands"]["lint"] == "" and cfg["commands"]["eval"] == ""
      and cfg["commands"]["ci_local"] == "make ci",
      repr(cfg["commands"]))
check("blank lint and eval are warned about",
      {"lint", "eval"} <= set(cfg["_command_warnings"]),
      repr(cfg["_command_warnings"]))
check("the Eval row reads (none)", "| Eval      | `(none)` |" in _tech(cfg))

# The emitters strip too, so a cfg that never went through resolve_config
# (a direct caller) cannot emit `(   )` or a blank Eval cell either.
print("\n== the emitters strip a blank value on their own ==")
import templates  # noqa: E402
raw, _ = defaults.resolve_config({
    "project": {"name": "v", "archetype": "ai-agent"},
    "commands": {"test": "true", "lint": "true", "eval": "true"}})
for k in ("test", "ci_local", "eval", "lint"):
    raw["commands"][k] = "   "
# What a blank must select: the TODO arm, `true` (checks nothing), the
# marker fallback, the unset notice. A blank on its own line inside the
# subshell would parse and PASS, so "it parses" alone is not the pin.
for hook, unset_arm in (
        ("test-gate", "'Running test gate: echo '\"'\"'TODO: commands.test"),
        ("ci-mirror", "'CI mirror: true'"),
        ("eval-gate", 'MARK="${CLAUDE_PROJECT_DIR:-.}/.claude/.last-eval-pass"'),
        ("format-lint-gate", "commands.lint is empty")):
    body = templates._hook_body(hook, raw)
    r = subprocess.run(["bash", "-n"], input=body, capture_output=True,
                       text=True)
    check(f"{hook}: an unstripped blank emits the unset arm, and parses",
          r.returncode == 0 and unset_arm in body, r.stderr[-300:])
t = _tech(raw)
check("tech.md from an unstripped blank: Eval is (none), marker sentence",
      "| Eval      | `(none)` |" in t and "`eval-gate` runs Eval" not in t, t)

# ---------------------------------------------------------------------- #
# [WP2 re-review RR1-EMB-3] A value that does not parse where the hooks put
# it broke the WHOLE hook (every Bash call denied with a syntax error) while
# `sh -c` fails only the gated action. Measured before the fix: each value
# below installed with rc 0. The installer now refuses it, naming the key.
print("\n== RR1-EMB-3: an unparseable command is refused at install ==")
BROKEN = ("true &&", "false |", "echo :)", "echo :(", "echo $(true",
          "cat <<EOF", "if true; then echo")
for key in ("test", "lint", "ci_local", "eval", "format", "typecheck"):
    for value in BROKEN:
        _, errs = defaults.resolve_config({
            "project": {"name": "v", "archetype": "ai-agent"},
            "commands": {key: value}})
        want = f"commands.{key} is not a complete shell command ({value!r})"
        check(f"commands.{key} = {value!r} is refused",
              any(e.startswith(want) for e in errs), repr(errs)[:300])
# Values that look broken to a token count but parse: never refused.
for value in ("case x in x) echo y;; esac", 'echo "$(echo ")")"',
              "pytest -q # run it", "(cd sub && make) || exit 3",
              "cat <<<'here'"):
    _, errs = defaults.resolve_config({
        "project": {"name": "v", "archetype": "ai-agent"},
        "commands": {"test": value, "lint": value, "ci_local": value,
                     "eval": value}})
    check(f"{value!r} parses, so it is accepted",
          not [e for e in errs if "not a complete shell command" in e],
          repr(errs)[:300])
# The consequence named is the key's own: Bash calls for the PreToolUse
# runners, every edit for lint, nothing for format (no hook runs it).
_, errs = defaults.resolve_config({
    "project": {"name": "v", "archetype": "ai-agent"},
    "commands": {"test": "true &&", "lint": "true &&", "format": "true &&"}})
by = {e.split(" ", 1)[0]: e for e in errs}
check("test: the reason says every Bash call would be refused",
      "every Bash call would be refused" in by.get("commands.test", ""),
      repr(by))
check("lint: the reason says format-lint-gate would fail after every edit",
      "after every edit" in by.get("commands.lint", "")
      and "Bash call" not in by.get("commands.lint", ""), repr(by))
check("format: the reason names no hook",
      "hook" not in by.get("commands.format", "x hook"), repr(by))
# The real installer, end to end: rc 2, the key named, no hook written.
scratch = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
try:
    d = os.path.join(scratch, "proj")
    os.makedirs(d)
    _git(d, "init", "-q", "-b", "main")
    with open(os.path.join(scratch, "c.yaml"), "w") as fh:
        fh.write("project:\n  name: p\n  archetype: cli\nsecrets:\n"
                 "  enabled: false\ndeps:\n  enabled: false\ncommands:\n"
                 "  test: 'pytest -q'\n  lint: 'true'\n  format: 'true'\n"
                 "  eval: 'true &&'\n")
    r = subprocess.run([sys.executable, BIN, "-c",
                        os.path.join(scratch, "c.yaml"), "-C", d],
                       capture_output=True, text=True)
    check("installer: exit 2 naming commands.eval, and no hook written",
          r.returncode == 2
          and "commands.eval is not a complete shell command" in r.stderr
          and not os.path.exists(os.path.join(d, ".claude", "hooks")),
          repr((r.returncode, r.stderr[-400:])))
finally:
    shutil.rmtree(scratch, ignore_errors=True)

# [WP2 re-review RR1-EMB-4] The docstring said the shell runs the command
# "the way the SDK twin does (`/bin/sh -c`, no `-u`)". It does not: the
# subshell inherits pipefail and the hook's functions. The claim is gone.
print("\n== RR1-EMB-4: _user_cmd claims no parity it lacks ==")
doc = templates._user_cmd.__doc__ or ""
check("_user_cmd's docstring does not claim the SDK's semantics",
      "the way the SDK twin does" not in doc
      and "pipefail" in doc, doc[:300])

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

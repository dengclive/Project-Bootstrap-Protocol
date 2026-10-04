"""[WP2] Every non-security gate block writes "<hook> BLOCK <reason>" to
.claude/logs/hooks.log, and cost-log is wired to SessionEnd: one record per
session termination, carrying the payload's `reason`, with an earlier
install's Stop registration retired on re-install, manifest or not.

The security gates are out of scope (2026-09-27 pivot): secrets-gate already
logs its block, and dependency-gate is left as it is.

Run: python3 tests/test_block_logging.py
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "lib"))
from installer import _merge_hooks  # noqa: E402
from templates import (HOOK_EVENT_MAP, HOOK_EXTRA_EVENTS,  # noqa: E402
                       HOOK_RETIRED_SITES)

BIN_INSTALL = os.path.join(ROOT, "bin", "bootstrap-install")
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
  name: blk
  archetype: ai-agent
  prd_tier: full
autonomous_modes:
  goal_supervised_mode_enabled: true
principles:
  tdd_policy: required
commands:
  test: "false"
  lint: "true"
  format: "true"
  ci_local: "false"
"""
# test-gate and ci-mirror both get the exit-5 arm for `pytest -q`; a shim on
# PATH plays pytest, so the row does not depend on a real pytest.
CFG_RC5 = """project:
  name: blk5
  archetype: cli
commands:
  test: "pytest -q"
  lint: "true"
  format: "true"
  ci_local: "pytest -q"
"""
CFG_RETRO = """mode: "retrofit"
project:
  name: blkr
  archetype: ai-agent
  prd_tier: "standard"
principles:
  tdd_policy: "required"
commands:
  test: "true"
  lint: "true"
  format: "true"
retrofit:
  spec_strategy: "touch-based"
  legacy_allowlist:
    - "prompts/**"
  retrofit_active: true
  r08_committed: true
"""
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
Q = '"$CLAUDE_PROJECT_DIR"/.claude/hooks/cost-log.sh'
U = "$CLAUDE_PROJECT_DIR/.claude/hooks/cost-log.sh"


def _git(d, *a):
    subprocess.run(["git", "-C", d, *a], check=True, capture_output=True,
                   env={**os.environ, **GIT_ENV})


def _install(d, cfg_text):
    with open(os.path.join(d, "bootstrap.config.yaml"), "w") as fh:
        fh.write(cfg_text)
    r = subprocess.run([sys.executable, BIN_INSTALL, "-C", d],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def _project(tmp, name, cfg_text):
    d = os.path.join(tmp, name)
    os.makedirs(d)
    _git(d, "init", "-q")
    _git(d, "commit", "-q", "--allow-empty", "-m", "init")
    rc, out = _install(d, cfg_text)
    check(f"{name}: install rc=0", rc == 0, out[-400:])
    return d


def _shim(dirp, name, body):
    os.makedirs(dirp, exist_ok=True)
    p = os.path.join(dirp, name)
    with open(p, "w") as fh:
        fh.write("#!/bin/bash\n" + body)
    os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR)


def _hook(d, name, payload, cwd=None, path_pre=None, env=None):
    """Run one hook; return (rc, stderr, the lines it added to hooks.log)."""
    log = os.path.join(d, ".claude", "logs", "hooks.log")
    before = open(log).read() if os.path.exists(log) else ""
    e = {**os.environ, **GIT_ENV, "CLAUDE_PROJECT_DIR": d, **(env or {})}
    if path_pre:
        e["PATH"] = path_pre + os.pathsep + e["PATH"]
    r = subprocess.run(["bash", os.path.join(d, ".claude", "hooks",
                                             name + ".sh")],
                       input=json.dumps(payload), cwd=cwd or d, text=True,
                       capture_output=True, env=e)
    after = open(log).read() if os.path.exists(log) else ""
    return r.returncode, r.stderr, after[len(before):]


def _bash(cmd):
    return {"session_id": "S1", "hook_event_name": "PreToolUse",
            "tool_name": "Bash", "tool_input": {"command": cmd}}


def _write(d, path):
    return {"session_id": "S1", "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": os.path.join(d, path),
                           "content": "x"}}


def _blocked(name, rc, delta, reason):
    """rc=2 AND exactly the BLOCK line this arm writes."""
    return rc == 2 and f" {name} BLOCK {reason}" in delta


def _cost_registrations(d):
    st = json.load(open(os.path.join(d, ".claude", "settings.json")))
    return sorted(ev for ev, groups in st["hooks"].items() for g in groups
                  for h in g["hooks"]
                  if h.get("command", "").endswith("/cost-log.sh"))


tmp = tempfile.mkdtemp(prefix="blklog-")
try:
    # ------------------------------------------------------------------ #
    print("\n== every non-security block writes a BLOCK line ==")
    d = _project(tmp, "p", CFG)
    os.makedirs(os.path.join(d, "src"))
    open(os.path.join(d, "src", "a.py"), "w").write("x\n")
    _git(d, "add", "src/a.py")

    rc, _, dl = _hook(d, "spec-gate-commit", _bash("git commit -m x"))
    check("spec-gate-commit: an unreferenced file logs its BLOCK line",
          _blocked("spec-gate-commit", rc, dl, "unreferenced: src/a.py"),
          f"rc={rc} log={dl!r}")
    # No spec corpus at all: INDEX.md moved aside, no tasks/ files.
    idx = os.path.join(d, ".claude", "specs", "INDEX.md")
    os.rename(idx, idx + ".aside")
    rc, _, dl = _hook(d, "spec-gate-commit", _bash("git commit -m x"))
    os.rename(idx + ".aside", idx)
    check("spec-gate-commit: no spec corpus logs its BLOCK line",
          _blocked("spec-gate-commit", rc, dl, "no active spec/task files"),
          f"rc={rc} log={dl!r}")

    rc, _, dl = _hook(d, "test-gate", _bash("git commit -m x"))
    check("test-gate: failing tests log 'BLOCK tests failing (exit 1)'",
          _blocked("test-gate", rc, dl, "tests failing (exit 1)"),
          f"rc={rc} log={dl!r}")
    rc, _, dl = _hook(d, "ci-mirror", _bash("git push"))
    check("ci-mirror: a failing CI command logs its BLOCK line",
          _blocked("ci-mirror", rc, dl, "CI mirror failed (exit 1)"),
          f"rc={rc} log={dl!r}")
    rc, _, dl = _hook(d, "tdd-gate", _write(d, "src/foo.py"))
    check("tdd-gate: a source write with no test logs its BLOCK line",
          _blocked("tdd-gate", rc, dl, "no test for foo before "),
          f"rc={rc} log={dl!r}")

    os.makedirs(os.path.join(d, "prompts"))
    open(os.path.join(d, "prompts", "system_prompt.md"), "w").write("p\n")
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "--no-verify", "-m", "p")
    rc, _, dl = _hook(d, "eval-gate", _bash("git push"))
    check("eval-gate: prompt changes with no eval pass log a BLOCK line",
          _blocked("eval-gate", rc, dl,
                   "prompt changes without an eval pass"),
          f"rc={rc} log={dl!r}")
    # A git that cannot list the push's files: the refusal arm.
    real_git = shutil.which("git")
    gshim = os.path.join(tmp, "gitshim")
    _shim(gshim, "git", 'if [ "${1:-}" = diff ] && [ "${2:-}" = --name-only ]'
          f'; then exit 128; fi\nexec "{real_git}" "$@"\n')
    rc, err, dl = _hook(d, "eval-gate", _bash("git push"), path_pre=gshim)
    check("eval-gate: a git failure logs 'BLOCK cannot read push contents "
          "(git exit 128)'",
          _blocked("eval-gate", rc, dl,
                   "cannot read push contents (git exit 128)"),
          f"rc={rc} log={dl!r} err={err[-200:]!r}")
    # The marker arm's message is unchanged by the if-block rewrite.
    rc, err, _ = _hook(d, "eval-gate", _bash("git push"))
    check("eval-gate: the marker arm's stderr is byte-identical",
          rc == 2 and err == "Eval gate: run evals before pushing prompt "
          "changes.\n", repr(err))

    sess = os.path.join(d, ".claude", "sessions")
    os.makedirs(sess, exist_ok=True)
    open(os.path.join(sess, ".goal-active-T1"), "w").close()
    rc, _, dl = _hook(d, "iteration-summary-enforcement",
                      {"session_id": "S1", "hook_event_name": "Stop",
                       "stop_hook_active": False})
    os.remove(os.path.join(sess, ".goal-active-T1"))
    check("iteration-summary-enforcement: a block logs its BLOCK line",
          _blocked("iteration-summary-enforcement", rc, dl,
                   "summary missing or empty"), f"rc={rc} log={dl!r}")

    # Control: an allow writes `ok` and no BLOCK line.
    rc, _, dl = _hook(d, "test-gate", _bash("ls"))
    check("test-gate: an allow writes 'ok' and no BLOCK (control)",
          rc == 0 and "test-gate ok" in dl and "BLOCK" not in dl, repr(dl))

    # ------------------------------------------------------------------ #
    print("\n== the exit-127 and exit-5 arms ==")
    d5 = _project(tmp, "p5", CFG_RC5)
    os.makedirs(os.path.join(d5, "src"))
    pshim = os.path.join(tmp, "pyshim")
    _shim(pshim, "pytest", 'exit "${PYTEST_SHIM_RC:-5}"\n')
    sub = os.path.join(d5, "src")
    rc, _, dl = _hook(d5, "test-gate", _bash("git commit -m x"),
                      path_pre=pshim, env={"PYTEST_SHIM_RC": "127"})
    check("test-gate: exit 127 logs 'BLOCK test command not found'",
          _blocked("test-gate", rc, dl, "test command not found (exit 127)"),
          f"rc={rc} log={dl!r}")
    rc, _, dl = _hook(d5, "test-gate", _bash("git commit -m x"), cwd=sub,
                      path_pre=pshim)
    check("test-gate: exit 5 off the top of the checkout logs its BLOCK",
          _blocked("test-gate", rc, dl, "no tests collected (exit 5) "
                   "outside the top of the checkout"), f"rc={rc} log={dl!r}")
    rc, _, dl = _hook(d5, "ci-mirror", _bash("git push"), cwd=sub,
                      path_pre=pshim)
    check("ci-mirror: exit 5 off the top of the checkout logs its BLOCK",
          _blocked("ci-mirror", rc, dl, "no tests collected (exit 5) "
                   "outside the top of the checkout"), f"rc={rc} log={dl!r}")
    # Control: at the top the same exit 5 is allowed, with no BLOCK line.
    rc, _, dl = _hook(d5, "test-gate", _bash("git commit -m x"),
                      path_pre=pshim)
    check("test-gate: exit 5 at the top allows with no BLOCK (control)",
          rc == 0 and "BLOCK" not in dl, f"rc={rc} log={dl!r}")

    # ------------------------------------------------------------------ #
    print("\n== a retrofit body logs through the composed wrapper ==")
    dr = _project(tmp, "pr", CFG_RETRO)
    rs = os.path.join(dr, ".claude", "hooks", "rollout-schedule.md")
    body = open(rs).read()
    check("retrofit: rollout-schedule.md carries the week-1 marker",
          "ROLLOUT_WEEK: 1" in body)
    with open(rs, "w") as fh:
        fh.write(body.replace("ROLLOUT_WEEK: 1", "ROLLOUT_WEEK: 4"))
    rc, _, dl = _hook(dr, "tdd-gate", _write(dr, "src/foo.py"))
    check("retrofit tdd-gate in an enforce week logs its BLOCK line",
          _blocked("tdd-gate", rc, dl, "no test for foo before "),
          f"rc={rc} log={dl!r}")

    # ------------------------------------------------------------------ #
    print("\n== cost-log: SessionEnd, one record, the payload's reason ==")
    check("HOOK_EVENT_MAP wires cost-log to SessionEnd",
          HOOK_EVENT_MAP["cost-log"] == ("SessionEnd", None))
    check("cost-log is registered under SessionEnd only",
          _cost_registrations(d) == ["SessionEnd"],
          str(_cost_registrations(d)))
    ev = os.path.join(d, ".claude", "logs", "session-events.jsonl")

    def _records():
        if not os.path.exists(ev):
            return []
        out = []
        for ln in open(ev):
            try:
                out.append(json.loads(ln))
            except ValueError:
                out.append({"unparsable": ln})
        return out

    n0 = len(_records())
    rc, _, _ = _hook(d, "cost-log", {"session_id": "S9",
                                     "hook_event_name": "SessionEnd",
                                     "reason": "prompt_input_exit"})
    recs = _records()[n0:]
    check("cost-log appends exactly one record with the payload's reason",
          rc == 0 and len(recs) == 1 and recs[0].get("event") == "session_end"
          and recs[0].get("session_id") == "S9"
          and recs[0].get("reason") == "prompt_input_exit", str(recs))
    # The Stop-era guard is gone: a payload with stop_hook_active set (a
    # field SessionEnd never sends) still gets its record.
    n0 = len(_records())
    rc, _, _ = _hook(d, "cost-log", {"session_id": "S10",
                                     "hook_event_name": "SessionEnd",
                                     "reason": "clear",
                                     "stop_hook_active": True})
    recs = _records()[n0:]
    check("cost-log has no stop_hook_active guard",
          rc == 0 and len(recs) == 1 and recs[0].get("reason") == "clear",
          str(recs))
    n0 = len(_records())
    for reason in (None, 'x","event":"forged', "two words"):
        p = {"session_id": "S11", "hook_event_name": "SessionEnd"}
        if reason is not None:
            p["reason"] = reason
        _hook(d, "cost-log", p)
    recs = _records()[n0:]
    check("cost-log records a missing or non-word reason as 'unknown', "
          "and every line stays one JSON object",
          len(recs) == 3 and all(r.get("reason") == "unknown"
                                 and r.get("event") == "session_end"
                                 for r in recs), str(recs))

    # ------------------------------------------------------------------ #
    print("\n== the retired Stop site is dropped on re-install ==")
    for cmd in (Q, U):
        theirs = {"Stop": [{"hooks": [{"type": "command", "command": cmd}]}]}
        ours = {"SessionEnd": [{"hooks": [{"type": "command",
                                           "command": Q}]}]}
        merged, _ = _merge_hooks(ours, theirs, None, [])
        check(f"no manifest: the retired Stop site is dropped ({cmd[:20]})",
              "Stop" not in merged and len(merged["SessionEnd"]) == 1,
              json.dumps(merged))
    merged, _ = _merge_hooks({}, {"Stop": [{"hooks": [
        {"type": "command", "command": Q}]}]}, None, [])
    check("no manifest, cost-log off: the retired Stop site is dropped",
          "Stop" not in merged, json.dumps(merged))
    theirs = {"Stop": [{"hooks": [{"type": "command", "command": "echo op"}]}]}
    merged, _ = _merge_hooks({}, theirs, None, [])
    check("an operator's own Stop hook is kept (control)", merged == theirs)
    emitted = {(hk, s) for hk in HOOK_EVENT_MAP
               for s in [HOOK_EVENT_MAP[hk]] + HOOK_EXTRA_EVENTS.get(hk, [])}
    check("no retired site is a site this installer still emits",
          not any((hk, tuple(s)) in emitted
                  for hk, sites in HOOK_RETIRED_SITES.items()
                  for s in sites))

    # End to end: an install whose settings still carry the Stop-era
    # registration, with no manifest (a fresh clone), re-installed.
    sp = os.path.join(d, ".claude", "settings.json")
    st = json.load(open(sp))
    st["hooks"].setdefault("Stop", []).append(
        {"hooks": [{"type": "command", "command": Q}]})
    with open(sp, "w") as fh:
        json.dump(st, fh, indent=2)
    check("upgrade: the seeded settings carry cost-log under Stop and "
          "SessionEnd", _cost_registrations(d) == ["SessionEnd", "Stop"],
          str(_cost_registrations(d)))
    os.remove(os.path.join(d, ".claude", ".installer-manifest.json"))
    rc, out = _install(d, CFG)
    st = json.load(open(sp))
    stop_cmds = [h.get("command") for g in st["hooks"].get("Stop", [])
                 for h in g["hooks"]]
    check("upgrade, no manifest: cost-log is registered once, under "
          "SessionEnd, and the other Stop hook survives",
          rc == 0 and _cost_registrations(d) == ["SessionEnd"]
          and any(c.endswith("/iteration-summary-enforcement.sh")
                  for c in stop_cmds),
          f"rc={rc} cost={_cost_registrations(d)} stop={stop_cmds} "
          f"out={out[-300:]!r}")

    # ------------------------------------------------------------------ #
    print("\n== a retired site of a hook this config turns off ==")
    _RET = "a site where an earlier installer registered that hook"
    A = '"$CLAUDE_PROJECT_DIR"/.claude/hooks/decision-required-alarm.sh'
    off_cfg = CFG + ("hooks:\n  cost_log: false\n"
                     "  decision_required_alarm: false\n")

    def _seed(d, own_scripts):
        if own_scripts:
            for hk in ("cost-log", "decision-required-alarm"):
                with open(os.path.join(d, ".claude", "hooks", hk + ".sh"),
                          "w") as fh:
                    fh.write("#!/bin/sh\n# the operator's own\nexit 0\n")
        st = json.load(open(os.path.join(d, ".claude", "settings.json")))
        st["hooks"].setdefault("Stop", []).append(
            {"hooks": [{"type": "command", "command": Q}]})
        st["hooks"].setdefault("Notification", []).append(
            {"hooks": [{"type": "command", "command": A}]})
        with open(os.path.join(d, ".claude", "settings.json"), "w") as fh:
            json.dump(st, fh, indent=2)

    def _at_retired(d):
        st = json.load(open(os.path.join(d, ".claude", "settings.json")))
        return sorted(ev for ev, gs in st.get("hooks", {}).items()
                      for g in gs if g.get("matcher") is None
                      for h in g["hooks"] if h.get("command") in (Q, A))

    # IU-2: the manifest records ownership and the scripts are the
    # operator's own, so WP1's keep_off rule keeps both registrations.
    d = _project(tmp, "iu2", off_cfg)
    _seed(d, own_scripts=True)
    rc1, out1 = _install(d, off_cfg)
    rc2, out2 = _install(d, off_cfg)
    check("IU-2: an operator-owned script at a retired site is kept, twice, "
          "with a line for each",
          (rc1, rc2) == (0, 0)
          and _at_retired(d) == ["Notification", "Stop"]
          and sum(_RET in ln and "so this run kept the registration." in ln
                  for ln in out1.splitlines()) == 2,
          f"rc={rc1},{rc2} sites={_at_retired(d)} out={out1[-600:]!r}")
    # Control: the same registrations with NO script on disk dangle, so
    # they are dropped - with a line, since no manifest recorded the site.
    d = _project(tmp, "iu2c", off_cfg)
    _seed(d, own_scripts=False)
    rc, out = _install(d, off_cfg)
    check("IU-2 control: a retired-site registration of a missing script is "
          "dropped, with a line for each",
          rc == 0 and _at_retired(d) == []
          and sum(_RET in ln and "this run dropped that registration." in ln
                  for ln in out.splitlines()) == 2,
          f"rc={rc} sites={_at_retired(d)} out={out[-600:]!r}")

    # IU-3: no manifest, cost_log turned off. Both of cost-log's drops are
    # said, and so is the script the cleanup could not remove.
    d = _project(tmp, "iu3", CFG)
    _seed(d, own_scripts=False)
    os.remove(os.path.join(d, ".claude", ".installer-manifest.json"))
    rc, out = _install(d, CFG + "hooks:\n  cost_log: false\n")
    lines = out.splitlines()
    check("IU-3: no manifest, cost-log off: the Stop drop is said as the "
          "SessionEnd drop is",
          rc == 0 and _cost_registrations(d) == []
          and any("cost-log.sh under Stop, " + _RET in ln
                  and "this run dropped that registration." in ln
                  for ln in lines)
          and any("cost-log.sh under SessionEnd, the installer's site" in ln
                  for ln in lines), out[-900:])
    check("IU-3: the cost-log.sh left on disk is explained, once",
          os.path.exists(os.path.join(d, ".claude", "hooks", "cost-log.sh"))
          and sum(".claude/hooks/cost-log.sh stays on disk although this "
                  "run dropped its registration: this tree has no installer "
                  "manifest" in ln for ln in lines) == 1, out[-900:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

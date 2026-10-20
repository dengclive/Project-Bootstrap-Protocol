#!/usr/bin/env python3
"""[WP3 / D6] Merge-back: landing an implementer's worktree branch.

Owner decision 2026-10-04: the main session lands an implementer's worktree
branch through ONE emitted script, .claude/merge-back.sh. It refuses a dirty
tree, merges with --no-ff, runs the gates on the merged result, calls the
integrator only on a conflict, then removes the worktree and its branch.
Worktrees start from the local HEAD (settings.json worktree.baseRef "head"),
and .claude/worktrees/ is ignored in .claude/.gitignore.

The behaviour rows drive the EMITTED script with real git in a real install,
with the implementer's worktree simulated by `git worktree add` under
.claude/worktrees/ (the layout Claude Code 2.1.289 uses). A golden digest
says the bytes moved; these rows say what the bytes do.

Run: python3 tests/test_merge_back.py
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

from defaults import resolve_config                      # noqa: E402
from installer import build_plan                         # noqa: E402
from minyaml import load_yaml                            # noqa: E402
from templates import (INTEGRATOR_DESCRIPTION,           # noqa: E402
                       MERGE_BACK_EXITS, MERGE_BACK_SCRIPT,
                       SPEC_CHECK_NOT_RUN, TEMPLATES, WORKTREE_BASE_REF,
                       _LANDING_GATES, _landing_claude_md)

BIN = os.path.join(ROOT, "bin", "bootstrap-install")
GIT = shutil.which("git")
BASH = shutil.which("bash")
HAVE_PARSER = bool(shutil.which("jq") or shutil.which("python3"))

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
  name: mergeback
  archetype: cli
secrets:
  enabled: false
deps:
  enabled: false
commands:
  test: "sh tests/run.sh"
  lint: "true"
  format: "true"
"""
CFG_OFF = CFG + "workflow:\n  implementer_isolation: none\n"
CFG_NO_GATES = CFG + "hooks:\n  test_gate: false\n  spec_gate_commit: false\n"
CFG_NO_SPEC = CFG + "hooks:\n  spec_gate_commit: false\n"
CFG_SPEC_ONLY = CFG + "hooks:\n  test_gate: false\n"
RETRO_CFG = """mode: "retrofit"
project:
  name: r-mb
  archetype: service
secrets:
  enabled: false
deps:
  enabled: false
commands:
  test: "sh tests/run.sh"
  lint: "true"
  format: "true"
retrofit:
  spec_strategy: "forward-only"
  retrofit_active: true
  r08_committed: true
"""


def cfg_of(text):
    c, errs = resolve_config(load_yaml(text))
    assert not errs, errs
    return c


def plan_of(text):
    return {a["path"]: a for a in build_plan(cfg_of(text))}


def code_lines(body):
    return "\n".join(ln for ln in body.splitlines()
                     if not ln.lstrip().startswith("#"))


# =========================================================================== #
print("\n== emission: one script, isolation-neutral, no configured command ==")
# =========================================================================== #
P_ON, P_OFF = plan_of(CFG), plan_of(CFG_OFF)
P_RS = plan_of(RETRO_CFG)
for label, p in (("greenfield", P_ON), ("isolation off", P_OFF),
                 ("retrofit", P_RS)):
    a = p.get(MERGE_BACK_SCRIPT)
    check(f"{label}: {MERGE_BACK_SCRIPT} is planned, kind file, mode 0755",
          a is not None and a["kind"] == "file" and a["mode"] == 0o755,
          str(a and (a["kind"], oct(a["mode"]))))
check("the script is byte-identical with worktree isolation on and off",
      P_ON[MERGE_BACK_SCRIPT]["body"] == P_OFF[MERGE_BACK_SCRIPT]["body"])
check("the retrofit overlay passes the script through unchanged",
      P_RS[MERGE_BACK_SCRIPT]["body"] == P_ON[MERGE_BACK_SCRIPT]["body"])
P_SDK = plan_of('gate_substrate: "sdk-callable"\n' + CFG)
check("sdk-callable substrate: the same script, and the shell files it runs "
      "are emitted beside gates.py (the gates it calls are substrate-neutral)",
      P_SDK[MERGE_BACK_SCRIPT]["body"] == P_ON[MERGE_BACK_SCRIPT]["body"]
      and ".claude/sdk_gates/gates.py" in P_SDK
      and ".claude/hooks/test-gate.sh" in P_SDK
      and ".claude/githooks/dispatch" in P_SDK)
MB = P_ON[MERGE_BACK_SCRIPT]["body"]
gates_line = {
    "both": re.search(r"^GATES=.*$", MB, re.M).group(0),
    "test only": re.search(r"^GATES=.*$", plan_of(CFG_NO_SPEC)[
        MERGE_BACK_SCRIPT]["body"], re.M).group(0),
    "none": re.search(r"^GATES=.*$", plan_of(CFG_NO_GATES)[
        MERGE_BACK_SCRIPT]["body"], re.M).group(0),
}
check("GATES follows the resolved hooks: spec check first, then tests",
      gates_line == {"both": "GATES='spec-check test-gate'",
                     "test only": "GATES=test-gate", "none": "GATES=''"},
      str(gates_line))
_weird = CFG.replace('test: "sh tests/run.sh"',
                     'test: "sh -c \\"cd x && echo $HOME\\" # tail"')
_wb = plan_of(_weird)[MERGE_BACK_SCRIPT]["body"]
check("no configured command is copied into the script (WP2 SC-1 cannot "
      "recur): a hostile commands.test leaves the bytes unchanged",
      _wb == MB and "cd x" not in _wb)
_code = code_lines(MB)
check("the script never passes --no-verify",
      "--no-verify" not in _code)
check("it merges with --no-ff --no-commit and concludes with git commit",
      "merge --no-ff --no-commit" in _code and "commit --no-edit" in _code)
check("each exit status in the header is the one MERGE_BACK_EXITS names",
      all(re.search(rf"^#\s+{rc}\s+{word}\b", MB, re.M)
          for rc, word in MERGE_BACK_EXITS.items()))
if BASH:
    for label, text in (("both gates", CFG), ("test only", CFG_NO_SPEC),
                        ("no gates", CFG_NO_GATES), ("retrofit", RETRO_CFG)):
        with tempfile.NamedTemporaryFile("w", suffix=".sh",
                                         delete=False) as fh:
            fh.write(plan_of(text)[MERGE_BACK_SCRIPT]["body"])
        r = subprocess.run([BASH, "-n", fh.name], capture_output=True,
                           text=True)
        os.unlink(fh.name)
        check(f"bash -n: the rendered script parses ({label})",
              r.returncode == 0, r.stderr)

# =========================================================================== #
print("\n== settings.json, .gitignore, agents, CLAUDE.md, wrapper comment ==")
# =========================================================================== #
for label, p in (("greenfield", P_ON), ("isolation off", P_OFF),
                 ("retrofit", P_RS)):
    s = json.loads(p[".claude/settings.json"]["body"])
    check(f"{label}: settings.json sets worktree.baseRef to \"head\"",
          s.get("worktree") == {"baseRef": WORKTREE_BASE_REF} ==
          {"baseRef": "head"}, str(s.get("worktree")))
check("settings.json does not depend on the isolation decision",
      P_ON[".claude/settings.json"]["body"]
      == P_OFF[".claude/settings.json"]["body"])
for label, p in (("greenfield", P_ON), ("retrofit", P_RS)):
    gi = p[".claude/.gitignore"]["body"].splitlines()
    check(f"{label}: .claude/.gitignore ignores the worktrees as /worktrees/ "
          f"(the spelling `.claude/worktrees/` matches nothing there)",
          "/worktrees/" in gi and ".claude/worktrees/" not in gi)
IMPL, INTG = ".claude/agents/implementer.md", ".claude/agents/integrator.md"
for label, p in (("greenfield", P_ON), ("retrofit", P_RS)):
    b = p[IMPL]["body"]
    check(f"{label}: implementer (worktree) reports its branch and never "
          f"merges",
          "report your branch, never merge" in b
          and ".claude/merge-back.sh <branch>" in b and "BRANCH:" in b
          and "do not merge, cherry-pick or push" in b, b[-600:])
check("isolation off: the implementer has nothing to merge back",
      "nothing to merge back" in P_OFF[IMPL]["body"]
      and "report your branch" not in P_OFF[IMPL]["body"])
check("isolation off (retrofit): the same",
      "nothing to merge back" in plan_of(
          RETRO_CFG + "workflow:\n  implementer_isolation: none\n")[IMPL][
          "body"])
ib = P_ON[INTG]["body"]
check("integrator: routed by merge-back's CONFLICT, with no ': ' in the "
      "description (strict YAML)",
      f"description: {INTEGRATOR_DESCRIPTION}\n" in ib
      and ": " not in INTEGRATOR_DESCRIPTION)
check("integrator: never concludes or aborts the merge itself",
      all(s in ib for s in ("`git commit`", "`git merge --continue`",
                            "`git merge --abort`",
                            ".claude/merge-back.sh --continue")))
check("isolation off: the integrator keeps its 'Not reachable' note",
      "Not reachable in this project's configuration" in P_OFF[INTG]["body"])
# [WP3 d6 rebuild verifier, INFO] A `git commit` in its own Bash call does
# run the PreToolUse test gate; `git merge --continue` does not (the gate
# matches the commit verb only), so that is the claim the body makes.
check("integrator: names `git merge --continue` as the conclusion with no "
      "test gate, not 'any other way'",
      "`git merge --continue` would conclude it with no test gate."
      in " ".join(ib.split()) and "any other way" not in ib)
# [WP3 critic 5d, PRD:1186, A-08] The Haiku floor, while it inherits.
_floor = ("If the main session runs on Haiku, set "
          "`workflow.integrator_model: sonnet` in `bootstrap.config.yaml` and "
          "re-install")
check("integrator (model: inherit): the Haiku-floor note, greenfield and "
      "retrofit",
      "\nmodel: inherit\n" in ib
      and all(_floor in " ".join(p[INTG]["body"].split())
              for p in (P_ON, P_RS, P_OFF)))
_ib_sonnet = plan_of(CFG + "workflow:\n  integrator_model: sonnet\n")[INTG][
    "body"]
check("integrator with a pinned model: no floor note",
      "\nmodel: sonnet\n" in _ib_sonnet and "Model floor" not in _ib_sonnet)
# [WP3 critic conflict 7] The commit rule's reasons: Claude Code's worktree
# guard first; the index one only where the git hook is not installed.
check("implementer: the plain-commit rule gives the worktree guard as its "
      "reason, and the index reason only without the git hook",
      "Claude Code can refuse a compound command inside a worktree as too "
      "complex to verify, and where the spec check's git hook is not "
      "installed, the check that runs before a Bash command would read the "
      "index as it was before your `git add`."
      in " ".join(P_ON[IMPL]["body"].split()))
for label, text, retro in (("greenfield", CFG, False),
                           ("retrofit", RETRO_CFG, True)):
    _land = _landing_claude_md(cfg_of(text), retrofit=retro)
    _cmd = plan_of(text)["CLAUDE.md"]["body"]
    check(f"{label}: CLAUDE.md tells the main session to land through the "
          f"script, with a timeout, and never by hand",
          _land in _cmd and "`.claude/merge-back.sh <branch>`" in _land
          and "600000" in _land and "never a hand `git merge`" in _land)
    # [WP3 critic 5a] The status owner and the commit before dispatch
    # (operator ruling 2026-10-05), and the background case (d6 rebuild
    # verifier, MAJOR).
    _flat = " ".join(_cmd.split())
    # [WP4 / ruling 1 (a)] The sentence starts "on a spec branch," in both
    # modes: each spec starts on its own branch (/spec-new creates it), so
    # merge-back lands a task there, not on the default branch.
    check(f"{label}: CLAUDE.md starts a task: on a spec branch, status "
          f"in-progress, then the spec and INDEX.md committed, before "
          f"dispatch",
          "Starting a task: on a spec branch, set `status: in-progress` in "
          "its task file, commit `.claude/specs/<slug>/` and "
          "`.claude/specs/INDEX.md`, then dispatch it." in _flat, _land)
    # The clause itself, exactly as long as the retrofit-agent fixture's 80
    # lines allow (19 characters there take it to 81, review build N1).
    _clause = _land.split("Starting a task: ", 1)[-1][:18]
    check(f"{label}: the clause right after \"Starting a task: \" is \"on a "
          f"spec branch, \" (18 characters)",
          "Starting a task: " in _land and _clause == "on a spec branch, ",
          repr(_clause))
    _sn = " ".join(
        plan_of(text)[".claude/skills/spec-new/SKILL.md"]["body"].split())
    # [WP4 fix round 1 / NF1] Never on the previous spec's branch. [WP4 fix
    # round 3, operator ruling 2026-10-15] From the default branch after a
    # fast-forward pull; on another spec's branch the step asks
    # (tests/test_skill_bodies.py section 5 runs the commands).
    check(f"{label}: /spec-new creates the spec branch the clause names, from "
          f"the default branch, and asks on another spec's branch",
          "- On the default branch: if it tracks a remote branch" in _sn
          and "run `git pull --ff-only`" in _sn
          and "Then run `git switch -c spec/<slug>`." in _sn
          and "- On another spec's branch (`spec/*`), or with no branch "
          "checked out, stop and ask the operator which branch to start "
          "from. To start from the default branch, switch to it and follow "
          "the bullet above; to start from another branch, run `git switch "
          "-c spec/<slug> <branch>`." in _sn
          and "On any other branch, one the operator chose, stay on it."
          in _sn, _sn[:900])
    # [WP3 fix1 MB-3, MB-8] Done once the branch merged, whichever line
    # says so (MERGED, CLEANUP MERGED, ALREADY-MERGED naming the merge).
    check(f"{label}: CLAUDE.md sets done once the branch merged, and with "
          f"no worktree branch once approved",
          "Act on its last line: if the branch merged, set `status: done`, "
          "commit it;" in _flat
          and "No worktree branch: set `done` once approved." in _flat, _land)
    # [WP3 fix1 CR-1] Not "await its notification": under claude -p the
    # session then ends, Claude Code stops the script, and the merge is
    # aborted while the session's last words say it is still running.
    check(f"{label}: CLAUDE.md says to wait for the last line in the same "
          f"turn if Claude Code moves the script to the background",
          "If it goes to the background, wait for that line in this turn "
          "and commit nothing: ending the turn can stop it." in _flat
          and "await its notification" not in _flat, _land)
    # [WP4 / g2] The lifecycle now ends at ci-cd.md's one stop.
    check(f"{label}: the lifecycle names the reviewer agent as code-review "
          f"and merge-back as the landing step",
          "-> code-review (the reviewer agent) -> merge-back -> "
          "spec-validate -> pr-author -> stop as `ci-cd.md` says." in _flat)
check("CLAUDE.md does not depend on the isolation decision",
      P_ON["CLAUDE.md"]["body"] == P_OFF["CLAUDE.md"]["body"])
# [WP3 critic 5a] The gate sentence says only what merge-back runs: the
# tests where the test gate is on, and in a retrofit only from rollout week
# 3 (test-gate exits 0 without running them before; the WP2 SC-3 class).
_gate_sentence = {
    label: next((k for k, v in _LANDING_GATES.items()
                 if v in " ".join(plan_of(text)["CLAUDE.md"]["body"]
                                  .split())), None)
    for label, text in (("greenfield", CFG), ("retrofit", RETRO_CFG),
                        ("spec check only", CFG_SPEC_ONLY),
                        ("test gate only", CFG_NO_SPEC),
                        ("no gates", CFG_NO_GATES),
                        ("retrofit, no gates", RETRO_CFG
                         + "hooks:\n  test_gate: false\n"
                         "  spec_gate_commit: false\n"))}
check("CLAUDE.md's gate sentence follows the gates merge-back runs",
      _gate_sentence == {"greenfield": "tests",
                         "retrofit": "tests-retrofit",
                         "spec check only": "spec",
                         "test gate only": "tests", "no gates": "none",
                         "retrofit, no gates": "none"}, str(_gate_sentence))
check("greenfield CLAUDE.md names no rollout week; retrofit's says the "
      "tests run from week 3",
      "rollout week" not in P_ON["CLAUDE.md"]["body"]
      and "From rollout week 3 it runs the tests on the merged result."
      in " ".join(P_RS["CLAUDE.md"]["body"].split()))


def _golden_fixture_texts():
    """The seven golden fixtures' config texts, read (by AST, never by
    running the suites) from tests/test_greenfield_golden.py and
    tests/test_retrofit.py, so a fixture edit there is measured here.
    [freeze-exception no. 85, 2026-10-14] FIXTURE_GATES_OFF is the seventh
    (fixture E, WP4's gates-off config)."""
    import ast
    env = {"FIXTURE_DEFAULT": open(os.path.join(
        ROOT, "bootstrap.config.yaml")).read()}
    for f, names in (("test_greenfield_golden.py",
                      ("FIXTURE_FULL_AUTONOMOUS", "FIXTURE_DESIGN_STEERING",
                       "FIXTURE_SDK_CALLABLE", "FIXTURE_GATES_OFF")),
                     ("test_retrofit.py",
                      ("SERVICE_RETROFIT_CFG", "AGENT_RETROFIT_CFG"))):
        path = os.path.join(HERE, f)
        for node in ast.parse(open(path).read()).body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id in names):
                env[node.targets[0].id] = eval(compile(
                    ast.Expression(node.value), path, "eval"), dict(env))
    return env


# [WP3 critic 5a] PRD:1300 and Companion:101 budget CLAUDE.md at "roughly
# 80 lines max"; the D6 landing paragraph took the retrofit-agent fixture
# to 82 before it was compressed.
_fx = _golden_fixture_texts()
_md_lines = {k: plan_of(v)["CLAUDE.md"]["body"].count("\n")
             for k, v in sorted(_fx.items())}
check("CLAUDE.md stays at 80 lines or fewer in all seven golden fixtures",
      len(_md_lines) == 7 and max(_md_lines.values()) <= 80, str(_md_lines))
_full = plan_of(CFG + "autonomous_modes:\n  loop_mode_enabled: true\n")
_loop = _full[".claude/loop.sh"]["body"]
check("loop.sh: the #57512 claim is corrected, not repeated",
      "[CORRECTED WP3 / D6, 2026-10-05]" in _loop
      and "Do NOT add it to a COMMITTED .gitignore" not in _loop)
check("loop.sh: the per-clone exclude one-liner survives as the fallback",
      "|| echo '.claude/worktrees/' >>" in _loop)

# =========================================================================== #
# Behaviour: the emitted script, real git, a real install.
# =========================================================================== #
BASE_ENV = {k: v for k, v in os.environ.items()
            if k != "CLAUDECODE" and not k.startswith("GIT_")}
BASE_ENV.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
                GIT_CONFIG_NOSYSTEM="1", HOME=tempfile.mkdtemp())
# [WP3 critic 5f] git also reads $XDG_CONFIG_HOME/git/config, so a host's
# own settings (rerere.autoupdate, measured on the build machine) reached
# every row. The rerere row sets what it needs in its fixture.
BASE_ENV["XDG_CONFIG_HOME"] = os.path.join(BASE_ENV["HOME"], ".config")
# [WP3 fix1 TP-02] git 2.55's auto maintenance runs after a commit over its
# loose-object threshold, detached, and its repack deleted a template's
# loose objects while fixture() copied them (shutil.Error, a crash with no
# summary line). Off here, under the temporary HOME, for every git run.
os.makedirs(os.path.join(BASE_ENV["XDG_CONFIG_HOME"], "git"))
with open(os.path.join(BASE_ENV["XDG_CONFIG_HOME"], "git", "config"),
          "w") as _fh:
    _fh.write("[maintenance]\n\tauto = false\n[gc]\n\tauto = 0\n")
AGENT_ENV = dict(BASE_ENV, CLAUDECODE="1")
# A duration unique to this run, so the "no stray sleep" row cannot match
# a process some other job left on the machine.
SLOW_SECS = f"37.{os.getpid() % 1000:03d}"
SUITE = """#!/bin/sh
# Fails when a src file says BROKEN; sleeps first when SLOW exists.
[ -f SLOW ] && sleep """ + SLOW_SECS + """
if grep -l BROKEN src/*.py 2>/dev/null; then echo "FAIL: BROKEN found" >&2; exit 1; fi
echo "tests ok"
"""
TASK = """---
id: demo-T1
status: in-progress
---
# T1
Files:
- src/app.py
- src/feature.py
- tests/run.sh
"""
TEMPLATE_DIRS = {}
WORK = tempfile.mkdtemp(prefix="mb-")


def run(cmd, cwd, env=None, timeout=120):
    return subprocess.run(cmd, cwd=cwd, env=env or BASE_ENV,
                          capture_output=True, text=True, timeout=timeout)


def git(cwd, *args):
    return run([GIT, *args], cwd)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


def fixture(cfg=CFG, init=()):
    """A fresh copy of an installed, committed project for `cfg` (`init`:
    more `git init` arguments, such as --ref-format=reftable)."""
    key = (cfg, tuple(init)) if init else cfg
    if key not in TEMPLATE_DIRS:
        d = tempfile.mkdtemp(prefix="tpl-", dir=WORK)
        git(d, "init", "-q", "-b", "main", *init)
        cfgp = d + ".yaml"
        write(cfgp, cfg)
        r = run([sys.executable, BIN, "-c", cfgp, "-C", d], d)
        assert r.returncode == 0, r.stdout + r.stderr
        write(os.path.join(d, "tests/run.sh"), SUITE)
        write(os.path.join(d, "src/app.py"), "def app(): return 1\n")
        write(os.path.join(d, ".claude/specs/demo/tasks/T1.md"), TASK)
        git(d, "add", "-A")
        r = git(d, "commit", "-qm", "init")
        assert r.returncode == 0, r.stdout + r.stderr
        TEMPLATE_DIRS[key] = d
    dst = tempfile.mkdtemp(prefix="fx-", dir=WORK)
    shutil.rmtree(dst)
    shutil.copytree(TEMPLATE_DIRS[key], dst, symlinks=True)
    return dst


def impl(proj, name, files, msg="impl"):
    """The implementer: commits `files` on worktree-agent-<name> in its
    worktree under .claude/worktrees/ (plain git; no CLAUDECODE, so no D2
    hook runs here)."""
    wt = os.path.join(proj, ".claude/worktrees", f"agent-{name}")
    if not os.path.isdir(wt):
        r = git(proj, "worktree", "add", "-q", wt, "-b",
                f"worktree-agent-{name}")
        assert r.returncode == 0, r.stderr
    for rel, text in files.items():
        write(os.path.join(wt, rel), text)
    git(wt, "add", "-A", "--", *files)
    r = git(wt, "commit", "-qm", msg)
    assert r.returncode == 0, r.stdout + r.stderr
    return wt, git(proj, "rev-parse", f"worktree-agent-{name}").stdout.strip()


def mb(proj, *args, agent=True, env=None):
    e = dict(AGENT_ENV if agent else BASE_ENV, **(env or {}))
    r = run([os.path.join(proj, ".claude/merge-back.sh"), *args], proj, e,
            timeout=300)
    out = r.stdout + r.stderr
    last = out.rstrip("\n").splitlines()[-1] if out.strip() else ""
    return r.returncode, out, last


def head(proj):
    return git(proj, "rev-parse", "HEAD").stdout.strip()


def merging(proj):
    return os.path.exists(os.path.join(proj, ".git", "MERGE_HEAD"))


def clean(proj):
    """No tracked change and no merge in progress (.claude/worktrees aside)."""
    st = git(proj, "status", "--porcelain", "--untracked-files=no", "--",
             ".", ":(exclude).claude/worktrees").stdout.strip()
    return st == "" and not merging(proj)


def has_branch(proj, br):
    return git(proj, "rev-parse", "--verify", "--quiet",
               f"refs/heads/{br}").returncode == 0


def hooks_log(proj):
    p = os.path.join(proj, ".claude/logs/hooks.log")
    return open(p).read() if os.path.exists(p) else ""


def shared_change(proj, name, top=None, rel=""):
    """[WP3 fix1, operator decision 2026-10-06 (1)] merge-back's spec step,
    like D2's merge hooks, checks the merge's OWN changes. [WP3 fix2 MR-1]
    Those are judged against git's automatic merge result, so a file both
    sides changed in different lines (which git merges on its own) is no
    longer one, and a fresh merge has none of its own unless something
    resolved a conflict in it. Here that is git rerere (critic 5f): both
    sides change line 5 of src/shared.py (unlisted), a resolution recorded
    once is reused and staged, and merge-back's gates judge it. `top`, `rel`:
    the repository top and the project's path from it, below the top."""
    top = top or proj
    sp = os.path.join(proj, "src/shared.py")
    git(top, "config", "rerere.enabled", "true")
    git(top, "config", "rerere.autoupdate", "true")
    write(sp, "1\n2\n3\n4\n5\n")
    git(top, "add", "-A")
    git(top, "commit", "-qm", "shared")
    if top == proj:
        wt, tip = impl(proj, name, {"src/shared.py": "1\n2\n3\n4\n50\n"})
    else:
        wt, tip = impl_sub(top, name, {"src/shared.py": "1\n2\n3\n4\n50\n"})
    write(sp, "1\n2\n3\n4\n500\n")
    git(top, "commit", "-qam", "main edits shared")
    git(top, "merge", "--no-ff", "--no-commit", tip)
    write(sp, "1\n2\n3\n4\n5000\n")
    git(top, "add", (rel + "/" if rel else "") + "src/shared.py")
    git(top, "rerere")
    git(top, "merge", "--abort")
    return wt, tip


def set_spec_mode(proj, mode):
    """hooks.spec_gate_commit_mode, set on the installed dispatch."""
    p = os.path.join(proj, ".claude/githooks/dispatch")
    body = open(p).read()
    body = re.sub(r"^MODE=\S+", f"MODE={mode}", body, count=1, flags=re.M)
    write(p, body)
    git(proj, "commit", "-qam", f"spec check {mode}")


if not (GIT and BASH and HAVE_PARSER):
    print("\n== behaviour rows SKIPPED: need git, bash and jq or python3 ==")
else:
    print("\n== a clean merge-back ==")
    p = fixture()
    wt, tip = impl(p, "a", {"src/feature.py": "def feature(): return 2\n"})
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-a")
    check("rc 0 and the last line says MERGED", rc == 0
          and last.startswith("merge-back: MERGED worktree-agent-a"), out)
    check("--no-ff: a merge commit although main had not moved (a fast-"
          "forward was possible)",
          git(p, "rev-parse", "HEAD^1").stdout.strip() == pre
          and git(p, "rev-parse", "HEAD^2").stdout.strip() == tip)
    check("the worktree is removed and the branch deleted",
          not os.path.exists(wt) and not has_branch(p, "worktree-agent-a"))
    check("the tests ran on the merged result",
          "[test-gate] allowed (exit 0)" in out and "tests ok" in out)
    log = hooks_log(p)
    check("the concluding commit fired the D2 pre-commit hook, not "
          "pre-merge-commit (git 2.55: --no-commit then commit)",
          "git-hook pre-commit: pass" in log
          and "git-hook pre-merge-commit" not in log, log[-400:])
    check("the tree is clean afterwards", clean(p))

    print("\n== the merged result fails the tests ==")
    p = fixture()
    wt, tip = impl(p, "b", {"src/feature.py": "x = 'BROKEN'\n"})
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-b")
    check("rc 2, REFUSED test-gate, worded as a refusal", rc == 2
          and last.startswith("merge-back: REFUSED test-gate refused on the "
                              "merged result"), out)
    check("the gate's own output reaches the caller",
          "FAIL: BROKEN found" in out and "tests failing" in out)
    check("the merge was aborted: HEAD unmoved, no merge in progress, clean",
          head(p) == pre and clean(p))
    check("the worktree and the branch are kept for the fix",
          os.path.isdir(wt) and has_branch(p, "worktree-agent-b"))
    check("main had not moved, so the remedy says the failure is the "
          "branch's own (back to the implementer)",
          "the failure is worktree-agent-b's own" in out
          and "integrator" not in out, out)
    write(os.path.join(p, "src/other.py"), "o = 1\n")
    git(p, "add", "src/other.py")
    git(p, "commit", "-qm", "work landed on main meanwhile")
    rc, out, last = mb(p, "worktree-agent-b")
    # [WP3 critic 5b] The integrator resolves conflicts and never starts a
    # merge (integrator.md), so a combined failure goes to the operator.
    _flat = " ".join(out.split())
    # [WP3 build 08-check] The path is the branch's own worktree, matched
    # exactly (git reports it resolved), so a TMPDIR with a space in it
    # still matches and a wrong worktree path does not.
    _wt = re.escape(" ".join(os.path.realpath(wt).split()))
    check("main had moved: the remedy offers the implementer or the "
          "operator, and never asks the integrator to start a merge",
          rc == 2 and "has moved since" in out
          and re.search(r"If the tests also fail in " + _wt
                        + r", the failure is worktree-agent-b's own: "
                        r"return the task to the implementer", _flat)
          and "stop and give this output to the operator" in _flat
          and "The integrator resolves merge conflicts only." in _flat
          and "git merge --no-ff --no-commit" not in out
          and "ask the integrator" not in out, out)

    p = fixture()
    write(os.path.join(p, ".claude/hooks/test-gate.sh"),
          "#!/bin/sh\necho 'hook crashed' >&2\nexit 1\n")
    git(p, "commit", "-qam", "a broken test gate")
    wt, _ = impl(p, "b2", {"src/feature.py": "def feature(): return 2\n"})
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-b2")
    check("a gate that errors (exit 1) fails CLOSED, and says it was an "
          "error rather than a refusal",
          rc == 2 and "REFUSED test-gate exited 1, which is a gate error, "
          "not a pass" in last and "hook crashed" in out
          and head(p) == pre and clean(p), out)
    # [WP3 d6 rebuild verifier] The remedy follows the kind of failure: a
    # gate error is not "the merged result fails the tests".
    check("a gate error's remedy sends it to the operator, not to the "
          "implementer as a test failure",
          "Remedy: the test-gate gate could not judge the merged result" in out
          and "Stop and give this output to the operator" in out
          and "fails the tests" not in out
          and "return the task to the implementer" not in out, out)

    print("\n== the D2 spec check: warn, and block ==")
    p = fixture()
    # [WP3 critic 1m] The mode is set, never inherited from DEFAULTS.
    set_spec_mode(p, "warn")
    shared_change(p, "e")
    rc, out, last = mb(p, "worktree-agent-e")
    # [WP3 critic 5h, 5c] d2-check's own words reach the caller, and
    # merge-back adds no mode or status sentence of its own.
    check("warn: an unlisted file merges (rc 0) and the warning "
          "reaches the caller",
          rc == 0 and "is not listed in any task file's Files: block" in out
          and "hooks.spec_gate_commit_mode is warn" in out
          and "[spec-check] allowed with the message above (it did not "
          "refuse), so the merge goes ahead" in out
          and "warn-only" not in out and last.startswith("merge-back: MERGED"),
          out)
    p = fixture()
    set_spec_mode(p, "block")
    wt, _ = shared_change(p, "f")
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-f")
    check("block: an unlisted file is REFUSED spec-check (rc 2), nothing "
          "changes, the worktree is kept",
          rc == 2 and last.startswith("merge-back: REFUSED spec-check "
                                      "refused on the merged result")
          and head(p) == pre and clean(p) and os.path.isdir(wt), out)
    # [WP3 critic 5b, 1e] The task file to edit is its copy on the branch,
    # in the worktree; a headless run cannot edit .claude/, so a refused
    # edit goes to the operator, never through a shell write.
    _flat = " ".join(out.split())
    check("block: the refusal names the task file, and the remedy edits its "
          "copy in the worktree with the Edit tool",
          ".claude/specs/demo/tasks/T1.md" in out
          and re.search(r"Add each path to that task file's Files: list on "
                        r"worktree-agent-f: edit its copy in "
                        + re.escape(" ".join(os.path.realpath(wt).split()))
                        + r" with the Edit tool, commit it "
                        r"there", _flat) is not None, out)
    check("block: the remedy says a headless run cannot edit .claude/, and "
          "a refused edit goes to the operator, never another way",
          "A headless run (claude -p) cannot edit files under .claude/: if "
          "Claude Code refuses the edit, stop and give this output to the "
          "operator; never write the task file another way." in _flat, out)
    impl(p, "g", {"src/feature.py": "def feature(): return 3\n"})
    rc, out, last = mb(p, "worktree-agent-g")
    check("block: a listed file merges, and the last line names the gates "
          "that ran", rc == 0
          and "(gates: spec-check test-gate);" in last, out)
    # [WP3 fix1, decision 2026-10-06 (1)] The branch's own unlisted file
    # was the D2 hook's to check when it was committed, not merge-back's.
    impl(p, "g2", {"src/unlisted.py": "x = 1\n"})
    rc, out, last = mb(p, "worktree-agent-g2")
    check("block: a file only the branch changed is not the merge's own "
          "change: it merges, the spec check passing",
          rc == 0 and "[spec-check] passed" in out
          and last.startswith("merge-back: MERGED"), out)
    p = fixture()
    set_spec_mode(p, "block")
    impl(p, "h", {"src/unlisted.py": "x = 1\n"})
    rc, out, last = mb(p, "worktree-agent-h", agent=False)
    check("block, human run (no CLAUDECODE): the spec check is skipped, as "
          "D2 scopes it to agents; the tests still run",
          rc == 0 and "skipped: it checks agent merges only" in out
          and "[test-gate] allowed (exit 0)" in out, out)
    check("human run: the last line does not claim the skipped spec check "
          "ran", "(gates: test-gate; skipped: spec-check);" in last, last)
    # [WP3 d6 conformance verifier] The exit status comes first: a dispatch
    # that refuses a person's merge (here, an edited copy without the
    # agent-only line) refuses it. This script used to print "skipped" and
    # land the file.
    p = fixture()
    set_spec_mode(p, "block")
    _d = os.path.join(p, ".claude/githooks/dispatch")
    write(_d, open(_d).read().replace(
        '[ "${CLAUDECODE:-}" = "1" ] || exit 0', ":", 1))
    git(p, "commit", "-qam", "dispatch checks people too")
    shared_change(p, "h2")
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-h2", agent=False)
    check("human run, dispatch refuses: REFUSED (rc 2), not skipped, "
          "nothing lands",
          rc == 2 and last.startswith("merge-back: REFUSED spec-check "
                                      "refused") and "skipped" not in out
          and head(p) == pre and clean(p), out)

    print("\n== the spec check could not run ==")
    # [WP3 critic 1c/5c] dispatch exits 1 in block mode both for a spec
    # refusal and for a check that could not run; merge-back tells them
    # apart by dispatch's words (SPEC_CHECK_NOT_RUN), so the remedy is
    # "tell the operator", not "list the files".
    for mode in ("block", "warn"):
        p = fixture()
        set_spec_mode(p, mode)
        write(os.path.join(p, ".claude/githooks/spec-check.sh"),
              "#!/usr/bin/env bash\nexit 3\n")
        git(p, "commit", "-qam", "a spec check that errors")
        wt, _ = impl(p, f"x{mode}", {"src/unlisted.py": "x = 1\n"})
        pre = head(p)
        rc, out, last = mb(p, f"worktree-agent-x{mode}")
        _flat = " ".join(out.split())
        if mode == "block":
            check("block, check error: REFUSED as a check that could not "
                  "run, nothing lands, the worktree is kept",
                  rc == 2 and SPEC_CHECK_NOT_RUN in out
                  and last.startswith("merge-back: REFUSED spec-check could "
                                      "not run, which is not a spec refusal")
                  and head(p) == pre and clean(p) and os.path.isdir(wt), out)
            check("block, check error: the remedy goes to the operator, not "
                  "to a task file",
                  "Remedy: the spec-check gate could not judge the merged "
                  "result" in _flat and "Stop and give this output to the "
                  "operator; do not change worktree-agent-xblock or a task "
                  "file for it." in _flat
                  and "no task file lists" not in out, out)
        else:
            check("warn, check error: allowed with dispatch's reason, and "
                  "the merge lands",
                  rc == 0 and "so the check did not run; commit allowed" in out
                  and "[spec-check] allowed with the message above" in out
                  and last.startswith("merge-back: MERGED"), out)

    print("\n== a conflict goes to the integrator ==")
    p = fixture()
    wt, tip = impl(p, "c", {"src/app.py": "def app(): return 3  # c\n"})
    write(os.path.join(p, "src/app.py"), "def app(): return 4  # main\n")
    git(p, "commit", "-qam", "main edits app")
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-c")
    mh = open(os.path.join(p, ".git/MERGE_HEAD")).read().strip() \
        if merging(p) else ""
    check("rc 4, CONFLICT, the merge left in progress (MERGE_HEAD = tip)",
          rc == 4 and last.startswith("merge-back: CONFLICT") and mh == tip
          and head(p) == pre, out)
    check("the output lists the file and carries the integrator's brief",
          "Conflicted files:\n    src/app.py" in out
          and "Invoke the integrator agent" in out and "Do not commit" in out
          and ".claude/merge-back.sh --continue worktree-agent-c" in out)
    rc, out, last = mb(p, "worktree-agent-c")
    check("a second plain run refuses (rc 3) and points at --continue",
          rc == 3 and "--continue worktree-agent-c" in last, out)
    rc, out, last = mb(p, "--continue", "worktree-agent-c")
    check("--continue with the conflict unresolved: rc 4 again",
          rc == 4 and "still has unresolved files" in last, out)
    git(p, "add", "src/app.py")
    rc, out, last = mb(p, "--continue", "worktree-agent-c")
    check("--continue with conflict markers staged: rc 4",
          rc == 4 and "conflict markers" in last, out)
    write(os.path.join(p, "src/app.py"), "def app(): return 34\n")
    git(p, "add", "src/app.py")
    rc, out, last = mb(p, "--continue", "worktree-agent-c")
    check("--continue after the resolution: gates pass, MERGED, cleaned up",
          rc == 0 and last.startswith("merge-back: MERGED")
          and git(p, "rev-parse", "HEAD^2").stdout.strip() == tip
          and not os.path.exists(wt), out)
    p = fixture()
    impl(p, "d", {"src/app.py": "def app(): return 3  # d\n"})
    write(os.path.join(p, "src/app.py"), "def app(): return 4  # main\n")
    git(p, "commit", "-qam", "main edits app")
    mb(p, "worktree-agent-d")
    write(os.path.join(p, "src/app.py"), "x = 'BROKEN'\n")
    git(p, "add", "src/app.py")
    rc, out, last = mb(p, "--continue", "worktree-agent-d")
    check("--continue whose resolution fails the tests: REFUSED, and the "
          "merge stays in progress for another attempt",
          rc == 2 and last.startswith("merge-back: REFUSED test-gate")
          and merging(p), out)
    # [WP3 critic 5g, d6 rebuild verifier V14] The gates test the working
    # tree and the commit takes the index: an unstaged change would be
    # tested and not landed.
    p = fixture()
    impl(p, "d2", {"src/app.py": "def app(): return 3  # d2\n"})
    write(os.path.join(p, "src/app.py"), "def app(): return 4  # main\n")
    git(p, "commit", "-qam", "main edits app")
    mb(p, "worktree-agent-d2")
    write(os.path.join(p, "src/app.py"), "def app(): return 34\n")
    git(p, "add", "src/app.py")
    write(os.path.join(p, "tests/run.sh"), SUITE + "# unstaged\n")
    pre = head(p)
    rc, out, last = mb(p, "--continue", "worktree-agent-d2")
    check("--continue with an unstaged change to a tracked file: rc 3, it "
          "names the file, and the merge stays in progress",
          rc == 3 and "git add or discard the files above" in last
          and "Unstaged changes" in out and "tests/run.sh" in out
          and merging(p) and head(p) == pre, out)
    # [V07] --continue concludes only a merge of the branch it names.
    impl(p, "d3", {"src/feature.py": "def feature(): return 15\n"})
    rc, out, last = mb(p, "--continue", "worktree-agent-d3")
    check("--continue naming another branch than the merge in progress: "
          "rc 3, nothing concluded",
          rc == 3 and "the merge in progress is of" in last
          and "not of worktree-agent-d3" in last and merging(p)
          and head(p) == pre, out)

    # A gate that errors on a resolution: the remedy and the last line do
    # not ask for a fix to the resolution.
    p = fixture()
    impl(p, "d4", {"src/app.py": "def app(): return 3  # d4\n"})
    write(os.path.join(p, "src/app.py"), "def app(): return 4  # main\n")
    git(p, "commit", "-qam", "main edits app")
    mb(p, "worktree-agent-d4")
    write(os.path.join(p, "src/app.py"), "def app(): return 34\n")
    write(os.path.join(p, ".claude/hooks/test-gate.sh"),
          "#!/bin/sh\necho 'hook crashed' >&2\nexit 1\n")
    git(p, "add", "src/app.py", ".claude/hooks/test-gate.sh")
    rc, out, last = mb(p, "--continue", "worktree-agent-d4")
    check("--continue whose test gate errors: REFUSED as a gate error, the "
          "merge kept in progress, and no request to fix the resolution",
          rc == 2 and "exited 1, which is a gate error" in last
          and "Once the gate can run: .claude/merge-back.sh --continue "
          "worktree-agent-d4" in last and "Fix it" not in last
          and "Stop and give this output to the operator" in out
          and merging(p), out)

    print("\n== a conflict git's rerere resolves itself ==")
    # [WP3 critic 5f, d6 rebuild verifier] With rerere.autoupdate, a
    # conflict with a recorded resolution comes back resolved and staged:
    # git exits 1 and leaves no file unmerged. That is a resolved conflict,
    # and the gates judge it; it used to read as "git did not start the
    # merge" on every retry.
    p = fixture()
    git(p, "config", "rerere.enabled", "true")
    git(p, "config", "rerere.autoupdate", "true")
    wt, tip = impl(p, "rr", {"src/app.py": "def app(): return 3  # rr\n"})
    write(os.path.join(p, "src/app.py"), "def app(): return 4  # main\n")
    git(p, "commit", "-qam", "main edits app")
    moved = head(p)
    rc1, _, _ = mb(p, "worktree-agent-rr")
    write(os.path.join(p, "src/app.py"), "def app(): return 34\n")
    git(p, "add", "src/app.py")
    rc2, out, _ = mb(p, "--continue", "worktree-agent-rr")
    git(p, "reset", "-q", "--hard", moved)          # undo the landing
    git(p, "worktree", "add", "-q", wt, "-b", "worktree-agent-rr", tip)
    check("(precondition) CONFLICT, then MERGED, records a resolution",
          (rc1, rc2) == (4, 0) and head(p) == moved, out)
    rc, out, last = mb(p, "worktree-agent-rr")
    check("rerere's staged resolution is gated and lands: MERGED rc 0, a "
          "merge of the branch holding the recorded resolution",
          rc == 0 and last.startswith("merge-back: MERGED")
          and git(p, "rev-parse", "HEAD^2").stdout.strip() == tip
          and open(os.path.join(p, "src/app.py")).read()
          == "def app(): return 34\n"
          and "[test-gate] allowed (exit 0)" in out, out)
    check("rerere: the output says a recorded resolution was reused",
          "reused a recorded resolution (git rerere)" in out
          and "git did not start the merge" not in out, out)
    p = fixture()
    git(p, "config", "rerere.enabled", "true")
    git(p, "config", "rerere.autoupdate", "true")
    wt, tip = impl(p, "rs", {"src/app.py": "def app(): return 3  # rs\n"})
    write(os.path.join(p, "src/app.py"), "def app(): return 4  # main\n")
    git(p, "commit", "-qam", "main edits app")
    moved = head(p)
    mb(p, "worktree-agent-rs")
    write(os.path.join(p, "src/app.py"), "x = 'BROKEN'\n")
    git(p, "add", "src/app.py")
    git(p, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "a hand "
        "conclusion records a broken resolution")
    git(p, "reset", "-q", "--hard", moved)
    git(p, "worktree", "remove", "--force", wt)
    git(p, "branch", "-D", "worktree-agent-rs")
    git(p, "worktree", "add", "-q", wt, "-b", "worktree-agent-rs", tip)
    rc, out, last = mb(p, "worktree-agent-rs")
    check("rerere: a recorded resolution that fails the tests is REFUSED "
          "and the merge aborted, like any resolution",
          rc == 2 and last.startswith("merge-back: REFUSED test-gate")
          and head(p) == moved and clean(p), out)

    print("\n== dirty, precisely ==")
    for label, setup in (
        ("an unstaged change to a tracked file",
         lambda q: write(os.path.join(q, "src/app.py"), "# local\n")),
        ("a staged change", lambda q: (
            write(os.path.join(q, "src/new.py"), "y = 1\n"),
            git(q, "add", "src/new.py"))),
    ):
        p = fixture()
        impl(p, "x", {"src/feature.py": "def feature(): return 5\n"})
        setup(p)
        pre = head(p)
        rc, out, last = mb(p, "worktree-agent-x")
        check(f"refused before anything changes: {label} (rc 3)",
              rc == 3 and last.startswith("merge-back: NOT-STARTED the "
                                          "working tree is not clean")
              and head(p) == pre and not merging(p), out)
    # [WP3 fix1 MB-7, MT-1] An untracked file under .claude/specs/ (a draft
    # spec, a progress.md, a task file not yet committed) no longer blocks:
    # the spec check reads task files from git, so it neither clears the
    # check nor reaches the merge commit. This used to refuse, "because the
    # spec check would read them", which the check itself contradicted.
    p = fixture()
    set_spec_mode(p, "block")
    shared_change(p, "y0")
    for rel, text in ((".claude/specs/demo/tasks/T9.md",
                       "---\nid: demo-T9\nstatus: in-progress\n---\n"
                       "Files:\n- src/shared.py\n"),
                      (".claude/specs/other/requirements.md", "# draft\n"),
                      (".claude/specs/demo/progress.md", "notes\n")):
        write(os.path.join(p, rel), text)
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-y0")
    check("untracked files under .claude/specs/ do not block, and an "
          "untracked task file does not clear the check: block mode still "
          "REFUSES the merge's own unlisted change, and counts T9.md out",
          rc == 2 and last.startswith("merge-back: REFUSED spec-check refused")
          and "Not counted, because the index does not have them" in out
          and ".claude/specs/demo/tasks/T9.md" in out
          and "the spec check would read them" not in out
          and "not clean" not in out and head(p) == pre, out)
    git(p, "add", ".claude/specs/demo/tasks/T9.md")
    git(p, "commit", "-qm", "commit the task file that lists it")
    rc, out, last = mb(p, "worktree-agent-y0")
    check("... the same task file committed clears it: MERGED, the "
          "untracked draft and progress.md still in place, untouched",
          rc == 0 and last.startswith("merge-back: MERGED")
          and os.path.exists(os.path.join(
              p, ".claude/specs/other/requirements.md"))
          and "?? .claude/specs/demo/progress.md" in git(
              p, "status", "--porcelain").stdout, out)
    check("the dirty-tree remedy no longer offers git stash -u (it stashes "
          "every untracked file too)",
          "git stash -u" not in MB and "(or git stash them)" in MB)
    p = fixture()
    impl(p, "y", {"src/feature.py": "def feature(): return 6\n"})
    for rel in (".claude/logs/extra.log", ".claude/sessions/.session-x",
                ".claude/sessions/2026-10-05T0000Z-checkpoint.md",
                "notes.txt"):
        write(os.path.join(p, rel), "runtime\n")
    rc, out, last = mb(p, "worktree-agent-y")
    check("not dirty: ignored runtime files, an untracked session "
          "checkpoint and an untracked file outside .claude/ (rc 0)",
          rc == 0 and last.startswith("merge-back: MERGED"), out)
    check("the untracked file outside .claude/ is named in a note",
          "Note: 1 untracked path(s) outside .claude/" in out, out)
    p = fixture()
    gi = os.path.join(p, ".claude/.gitignore")
    write(gi, open(gi).read().replace("/worktrees/\n", ""))
    git(p, "commit", "-qam", "an edited .gitignore without the line")
    impl(p, "z", {"src/feature.py": "def feature(): return 7\n"})
    check("(precondition) without the ignore line git shows the worktrees",
          "?? .claude/worktrees/" in git(p, "status", "--porcelain").stdout)
    rc, out, last = mb(p, "worktree-agent-z")
    check("an unignored .claude/worktrees/ does not count as dirty",
          rc == 0, out)

    print("\n== refusals that change nothing ==")
    p = fixture()
    wt, _ = impl(p, "r", {"src/feature.py": "def feature(): return 8\n"})
    pre = head(p)
    for label, args, want in (
        ("no branch", (), "expected exactly one branch name"),
        ("two branches", ("a", "b"), "expected exactly one branch name"),
        ("an unknown option", ("--force", "worktree-agent-r"),
         "unknown option"),
        ("an unknown branch", ("nope",), "no local branch 'nope'"),
        ("an invalid name", ("a..b",), "not a valid branch name"),
        ("the checked-out branch", ("main",), "is the branch checked out"),
        ("--continue with no merge", ("--continue", "worktree-agent-r"),
         "no merge is in progress"),
    ):
        rc, out, last = mb(p, *args)
        check(f"rc 3 for {label}", rc == 3 and want in last
              and head(p) == pre and not merging(p), out)
    rc, out, last = mb(wt, "worktree-agent-r") if os.path.exists(
        os.path.join(wt, ".claude/merge-back.sh")) else (None, "", "")
    check("the worktree's own copy refuses to run there (rc 3)",
          rc == 3 and "linked worktree" in last, out)
    git(p, "checkout", "-q", "--detach")
    rc, out, last = mb(p, "worktree-agent-r")
    check("rc 3 on a detached HEAD", rc == 3 and "detached" in last, out)
    git(p, "checkout", "-q", "main")
    git(p, "worktree", "lock", "--reason", "agent running", wt)
    rc, out, last = mb(p, "worktree-agent-r")
    check("rc 3 for a locked worktree (an agent may still be in it)",
          rc == 3 and "is locked" in last and "agent running" in last
          and head(p) == pre, out)
    git(p, "worktree", "unlock", wt)
    write(os.path.join(wt, "src/feature.py"), "uncommitted\n")
    rc, out, last = mb(p, "worktree-agent-r")
    check("rc 3 for a worktree holding uncommitted tracked changes",
          rc == 3 and "uncommitted work" in last and head(p) == pre, out)
    git(wt, "checkout", "-q", "--", "src/feature.py")
    os.remove(os.path.join(p, ".claude/hooks/test-gate.sh"))
    git(p, "commit", "-qam", "lose the test gate")
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-r")
    check("rc 3 when a configured gate file is missing, before merging",
          rc == 3 and "test-gate gate is configured but" in last
          and head(p) == pre and not merging(p), out)

    print("\n== git itself refuses: the commit, or the merge ==")
    p = fixture()
    wt, _ = impl(p, "m", {"src/feature.py": "def feature(): return 12\n"})
    hook = os.path.join(p, ".git/hooks/commit-msg")
    write(hook, "#!/bin/sh\necho 'commit-msg: no' >&2\nexit 1\n")
    os.chmod(hook, 0o755)
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-m")
    check("a git hook refusing the merge commit: REFUSED (rc 2), the merge "
          "aborted, nothing changed, the hook's text relayed",
          rc == 2 and "a git hook refused the merge commit" in last
          and "commit-msg: no" in out and head(p) == pre and clean(p)
          and os.path.isdir(wt), out)
    os.remove(hook)
    p = fixture()
    impl(p, "n", {"src/feature.py": "def feature(): return 13\n"})
    write(os.path.join(p, "src/feature.py"), "untracked, in the way\n")
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-n")
    check("git refusing to start the merge (an untracked file in the way): "
          "rc 3, git's reason relayed, nothing changed",
          rc == 3 and "git did not start the merge" in last
          and "would be overwritten" in out and head(p) == pre
          and not merging(p), out)
    p = fixture()
    gi = os.path.join(p, ".claude/.gitignore")
    write(gi, open(gi).read().replace("/worktrees/\n", ""))
    git(p, "commit", "-qam", "an older .gitignore without the line")
    old_wt, _ = impl(p, "old", {"src/old.py": "o = 1\n"})
    git(p, "add", "-A")                       # pre-WP3 habit: a gitlink
    git(p, "commit", "-qm", "commits a gitlink by accident")
    impl(p, "old", {"src/old.py": "o = 2\n"})  # that worktree moves on
    check("(precondition) a committed gitlink now shows as modified",
          " M .claude/worktrees/agent-old" in git(
              p, "status", "--porcelain").stdout)
    impl(p, "q", {"src/feature.py": "def feature(): return 14\n"})
    rc, out, last = mb(p, "worktree-agent-q")
    check("a modified gitlink under .claude/worktrees/ does not count as "
          "dirty", rc == 0, out)

    print("\n== another operation in progress, and the lock ==")
    p = fixture()
    impl(p, "s", {"src/feature.py": "def feature(): return 9\n"})
    impl(p, "t", {"src/app.py": "def app(): return 9\n"})
    git(p, "merge", "-q", "--no-ff", "--no-commit", "worktree-agent-t")
    rc, out, last = mb(p, "worktree-agent-s")
    check("rc 3 while a merge of another branch is in progress",
          rc == 3 and "is in progress here" in last, out)
    git(p, "merge", "--abort")
    lock = os.path.join(p, ".git", "bootstrap-merge-back.lock")
    os.makedirs(lock)
    sleeper = subprocess.Popen(["sleep", "60"])
    write(os.path.join(lock, "pid"), f"{sleeper.pid}\n")
    rc, out, last = mb(p, "worktree-agent-s")
    check("rc 3 while another merge-back holds the lock",
          rc == 3 and f"pid {sleeper.pid}" in last, out)
    sleeper.kill()
    sleeper.wait()
    rc, out, last = mb(p, "worktree-agent-s")
    check("a lock whose process is gone is taken over", rc == 0, out)
    check("the lock is released on exit", not os.path.exists(lock))

    print("\n== a worktree outside .claude/worktrees/ ==")
    # [WP3 critic 5g, d6 rebuild verifier V01] Only worktrees under
    # .claude/worktrees/ are the script's to remove: an operator's own
    # checkout of the branch elsewhere is left in place.
    p = fixture()
    ow = os.path.join(WORK, f"own-{os.path.basename(p)}")
    git(p, "worktree", "add", "-q", ow, "-b", "worktree-agent-o")
    write(os.path.join(ow, "src/feature.py"), "def feature(): return 16\n")
    git(ow, "add", "src/feature.py")
    git(ow, "commit", "-qm", "work in an operator's own worktree")
    tip = git(p, "rev-parse", "worktree-agent-o").stdout.strip()
    rc, out, last = mb(p, "worktree-agent-o")
    check("merged, but rc 5 CLEANUP: the worktree outside .claude/worktrees/ "
          "and its branch are kept",
          rc == 5 and last.startswith("merge-back: CLEANUP MERGED")
          and "outside .claude/worktrees/" in last
          and git(p, "rev-parse", "HEAD^2").stdout.strip() == tip
          and os.path.isdir(ow) and has_branch(p, "worktree-agent-o"), out)

    print("\n== cleanup, already merged, no gates ==")
    p = fixture()
    wt, tip = impl(p, "u", {"src/feature.py": "def feature(): return 10\n"})
    write(os.path.join(wt, "build.out"), "artifact\n")
    rc, out, last = mb(p, "worktree-agent-u")
    check("an untracked file in the worktree: merged, but rc 5 CLEANUP, the "
          "worktree kept and the file named",
          rc == 5 and last.startswith("merge-back: CLEANUP MERGED")
          and git(p, "rev-parse", "HEAD^2").stdout.strip() == tip
          and os.path.isdir(wt) and "build.out" in out, out)
    rc, out, last = mb(p, "worktree-agent-u")
    check("run again: ALREADY-MERGED, still rc 5 until the file goes",
          rc == 5 and "ALREADY-MERGED" in last, out)
    os.remove(os.path.join(wt, "build.out"))
    rc, out, last = mb(p, "worktree-agent-u")
    check("once it is gone: ALREADY-MERGED rc 0, worktree and branch removed",
          rc == 0 and "ALREADY-MERGED" in last and not os.path.exists(wt)
          and not has_branch(p, "worktree-agent-u"), out)
    p = fixture(CFG_NO_GATES)
    impl(p, "v", {"src/feature.py": "x = 'BROKEN'\n"})
    rc, out, last = mb(p, "worktree-agent-v")
    check("no gates configured: it says so and merges",
          rc == 0 and "No commit gates are configured" in out
          and "(gates: none)" in last, out)

    print("\n== interrupted ==")
    p = fixture()
    write(os.path.join(p, "SLOW"), "")
    git(p, "add", "SLOW")
    git(p, "commit", "-qm", "slow suite")
    impl(p, "w", {"src/feature.py": "def feature(): return 11\n"})
    pre = head(p)
    proc = subprocess.Popen([os.path.join(p, ".claude/merge-back.sh"),
                             "worktree-agent-w"], cwd=p, env=AGENT_ENV,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True)
    deadline = time.time() + 20
    while time.time() < deadline and not merging(p):
        time.sleep(0.1)
    time.sleep(2.0)            # past the spec check: the suite is sleeping
    t0 = time.time()
    proc.send_signal(signal.SIGTERM)
    try:
        out, _ = proc.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        out, _ = proc.communicate()
    took = time.time() - t0
    last = out.rstrip().splitlines()[-1] if out.strip() else ""
    check("SIGTERM while the tests run: rc 1, the merge aborted, nothing "
          "changed, well before the 37 s suite would end",
          proc.returncode == 1 and "the merge of worktree-agent-w was "
          "aborted" in last and head(p) == pre and clean(p) and took < 10,
          f"rc={proc.returncode} took={took:.1f}s\n{out}")
    ps = run(["ps", "-eo", "args"], p).stdout
    check("and the suite it started is gone too (no stray sleep)",
          not any(ln.strip() == f"sleep {SLOW_SECS}"
                  for ln in ps.splitlines()))
    proc = subprocess.Popen([os.path.join(p, ".claude/merge-back.sh"),
                             "worktree-agent-w"], cwd=p, env=AGENT_ENV,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True)
    deadline = time.time() + 20
    while time.time() < deadline and not merging(p):
        time.sleep(0.1)
    time.sleep(2.0)
    # SIGKILL the script alone: no trap runs. Then end the suite it started
    # (its own process group), so nothing is left behind.
    gate_pgids = set()            # portable: procps, BSD and busybox ps
    for ln in run(["ps", "-eo", "pid,ppid,pgid"], p).stdout.splitlines()[1:]:
        f = ln.split()
        if len(f) == 3 and f[1] == str(proc.pid):
            gate_pgids.add(f[2])
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait()

    def _pg_alive(g):
        try:
            os.killpg(int(g), 0)
            return True
        except (ProcessLookupError, ValueError, PermissionError):
            return False
    _gd = os.path.join(p, ".git")
    _left = sorted(f for f in os.listdir(_gd)
                   if f.startswith("bootstrap-merge-back."))
    # [WP3 fix3 MBS-4] What the header's SIGKILL sentence says is left.
    check("SIGKILL mid-gate leaves the running gate going (its own process "
          "group), the lock directory and the two scratch files, as the "
          "header says",
          gate_pgids and all(_pg_alive(g) for g in gate_pgids)
          and "bootstrap-merge-back.lock" in _left
          and any(f.startswith("bootstrap-merge-back.out.") for f in _left)
          and any(f.startswith("bootstrap-merge-back.in.") for f in _left),
          f"gate pgids={gate_pgids} .git={_left}")
    for g in gate_pgids:
        try:
            os.killpg(int(g), signal.SIGKILL)
        except (ProcessLookupError, ValueError, PermissionError):
            pass
    proc.communicate()
    check("SIGKILL mid-gate leaves an UNCOMMITTED merge, never a committed "
          "one that no gate passed", merging(p) and head(p) == pre)
    rc, out, last = mb(p, "worktree-agent-w")
    check("the next run spots it (rc 3) and says how to retry",
          rc == 3 and "already in progress" in last
          and "git merge --abort" in last, out)
    git(p, "merge", "--abort")
    check("git merge --abort restores the tree", clean(p) and head(p) == pre)

    print("\n== retrofit: the rollout weeks apply through test-gate ==")
    p = fixture(RETRO_CFG)
    impl(p, "k", {"src/feature.py": "x = 'BROKEN'\n"})
    rc, out, last = mb(p, "worktree-agent-k")
    check("retrofit week 1: test-gate does not run the tests in a warn-only "
          "week, so the broken merge lands exactly as a commit would; the "
          "gate's own notice is relayed and the script claims no pass",
          rc == 0 and "test-gate would have run/blocked" in out
          and "BROKEN" not in out and "[test-gate] allowed (exit 0)" in out
          and last.startswith("merge-back: MERGED"), out)
    p = fixture(RETRO_CFG)
    sched = os.path.join(p, ".claude/hooks/rollout-schedule.md")
    write(sched, re.sub(r"<!-- ROLLOUT_WEEK: \d+ -->",
                        "<!-- ROLLOUT_WEEK: 3 -->", open(sched).read()))
    git(p, "commit", "-qam", "week 3")
    impl(p, "k", {"src/feature.py": "x = 'BROKEN'\n"})
    rc, out, last = mb(p, "worktree-agent-k")
    check("retrofit week 3: the same merge is REFUSED test-gate",
          rc == 2 and last.startswith("merge-back: REFUSED test-gate"), out)

    # ======================================================================= #
    # [WP3 fix1] The review's merge-back findings, each pinned by a row
    # that fails without its fix (MB-1 to MB-7, MT-1, TP-01, TP-04, TP-12,
    # CR-1, CR-3, and merge-back's spec step under operator decision
    # 2026-10-06 (1)).
    # ======================================================================= #
    import pty
    import select

    def mb_path(proj):
        return os.path.join(proj, ".claude/merge-back.sh")

    def procs_with(marker):
        """(pid, args) of live processes whose args hold `marker`."""
        rows = run(["ps", "-eo", "pid,args"], WORK).stdout.splitlines()[1:]
        out = []
        for ln in rows:
            f = ln.strip().split(None, 1)
            if len(f) == 2 and marker in f[1] and "ps -eo" not in f[1]:
                out.append((int(f[0]), f[1]))
        return out

    def reap(marker):
        """Kill what a failed row left behind, so nothing outlives it."""
        for pid, _ in procs_with(marker):
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

    def run_pty(argv, cwd, env, keys=None, key_after=None, timeout=30,
                key_delay=1.5, again=None, before_keys=None):
        """Run argv as a person at a terminal: a session leader with a pty
        as its controlling terminal, in its foreground. Types `keys`
        `key_delay` seconds after `key_after` is in the output (time for a
        gate to reach the terminal and stop), and once more `again`
        seconds after that, if given; calls `before_keys()`, if given,
        just before the first keys. Returns (rc, output, seconds from
        the first keys to the end); rc None means it hung and was killed
        at `timeout`."""
        pid, fd = pty.fork()
        if pid == 0:
            try:
                # [WP3 fix3 MBS-5] A person's interactive shell gives a
                # foreground job the default SIGINT, SIGQUIT and SIGPIPE.
                # Inherited, this suite's own could be ignored: SIGINT and
                # SIGQUIT when it runs as a background job of a
                # non-interactive shell (two rows then hung), and SIGPIPE
                # always (Python ignores it), which hid MBS-1.
                for _s in (signal.SIGINT, signal.SIGQUIT, signal.SIGPIPE):
                    signal.signal(_s, signal.SIG_DFL)
                os.chdir(cwd)
                os.execve(argv[0], argv, env)
            finally:
                os._exit(127)
        buf, t_key, seen, t_again = b"", None, None, None
        deadline = time.time() + timeout
        while time.time() < deadline:
            if (keys and t_key is None and seen
                    and time.time() - seen > key_delay):
                if before_keys:
                    before_keys()
                os.write(fd, keys)
                t_key = time.time()
            if (again is not None and t_key is not None and t_again is None
                    and time.time() - t_key > again):
                try:
                    os.write(fd, keys)
                except OSError:
                    pass
                t_again = time.time()
            r, _, _ = select.select([fd], [], [], 0.1)
            if not r:
                continue
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                chunk = b""
            if not chunk:
                break
            buf += chunk
            if key_after and seen is None and key_after.encode() in buf:
                seen = time.time()
        else:
            try:
                os.killpg(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        _, st = os.waitpid(pid, 0)
        t_end = time.time()
        os.close(fd)
        rc = None if t_end >= deadline else (
            os.WEXITSTATUS(st) if os.WIFEXITED(st) else -os.WTERMSIG(st))
        return (rc, buf.decode("utf-8", "replace").replace("\r\n", "\n"),
                (t_end - t_key) if t_key else None)

    print("\n== a project below the repository top (MB-1, decision (2)) ==")
    SUB = "pkg/svc"
    SUB_STDERR = {}

    def fixture_sub(cfg=CFG, top_ignore=False):
        """A fresh copy of a monorepo whose package pkg/svc/ holds the
        installed project; returns (top, project)."""
        key = ("sub", cfg, top_ignore)
        if key not in TEMPLATE_DIRS:
            top = tempfile.mkdtemp(prefix="tpls-", dir=WORK)
            git(top, "init", "-q", "-b", "main")
            write(os.path.join(top, "README"), "mono\n")
            write(os.path.join(top, "other/lib.py"), "x = 1\n")
            if top_ignore:
                write(os.path.join(top, ".gitignore"), "/.claude/worktrees/\n")
            d = os.path.join(top, SUB)
            os.makedirs(d)
            cfgp = top + ".yaml"
            write(cfgp, cfg)
            r = run([sys.executable, BIN, "-c", cfgp, "-C", d], d)
            assert r.returncode == 0, r.stdout + r.stderr
            SUB_STDERR[key] = r.stderr
            write(os.path.join(d, "tests/run.sh"), SUITE)
            write(os.path.join(d, "src/app.py"), "def app(): return 1\n")
            write(os.path.join(d, ".claude/specs/demo/tasks/T1.md"), TASK)
            git(top, "add", "-A")
            r = git(top, "commit", "-qm", "init")
            assert r.returncode == 0, r.stdout + r.stderr
            TEMPLATE_DIRS[key] = top
        dst = tempfile.mkdtemp(prefix="fxs-", dir=WORK)
        shutil.rmtree(dst)
        shutil.copytree(TEMPLATE_DIRS[key], dst, symlinks=True)
        return dst, os.path.join(dst, SUB)

    def impl_sub(top, name, files, wt_root=None):
        """The implementer in Claude Code's layout for a project below the
        top: its worktree is at the REPOSITORY TOP's .claude/worktrees/
        (2.1.291 makes it under the git root of the session's directory),
        and the project's files sit under pkg/svc/ there."""
        wt = os.path.join(wt_root or top, ".claude/worktrees",
                          f"agent-{name}")
        if not os.path.isdir(wt):
            r = git(top, "worktree", "add", "-q", wt, "-b",
                    f"worktree-agent-{name}")
            assert r.returncode == 0, r.stderr
        rels = [f"{SUB}/{rel}" for rel in files]
        for rel, text in files.items():
            write(os.path.join(wt, SUB, rel), text)
        git(wt, "add", "-A", "--", *rels)
        r = git(wt, "commit", "-qm", "impl")
        assert r.returncode == 0, r.stdout + r.stderr
        return wt, git(top, "rev-parse",
                       f"worktree-agent-{name}").stdout.strip()

    top, p = fixture_sub()
    _err = " ".join(SUB_STDERR[("sub", CFG, False)].split())
    _top_real = os.path.realpath(top)
    check("installer, below the top: the git-hook warning says the spec "
          "check still polices the project's own paths there",
          "inside the git repository" in _err
          and "The spec check still checks this project's own paths "
          "against its own task files through the PreToolUse "
          "spec-gate-commit hook" in _err, _err[-1500:])
    # [WP3 fix1 MB-1] Measured on Claude Code 2.1.291: an agent's worktree
    # for a project below the top is made at the top's .claude/worktrees/
    # and the agent starts at that worktree's top, so the test gate refused
    # its commit (test command not found). `auto` isolation resolves to none
    # there; an explicit `worktree` stands, with a warning.
    _impl_sub = open(os.path.join(p, ".claude/agents/implementer.md")).read()
    check("installer, below the top, isolation auto: resolved to none, and "
          "a warning says why, and that merge-back works there",
          "\nisolation: worktree\n" not in _impl_sub
          and "Claude Code makes an implementer's worktree at" in _err
          and "/.claude/worktrees/ and starts it at that worktree's top, "
          "where the gates run the test command from the wrong directory"
          in _err
          and "So workflow.implementer_isolation `auto` resolved to none "
          "here: the implementer commits on the current branch" in _err
          and ".claude/merge-back.sh works here: it runs its git steps (the "
          "dirty check, the merge, the commit) at the repository top, "
          "across the whole repository, and the gates in pkg/svc/." in _err,
          _err[-1500:])
    CFG_WT = CFG + "workflow:\n  implementer_isolation: worktree\n"
    _, _pw = fixture_sub(CFG_WT)
    _err_wt = " ".join(SUB_STDERR[("sub", CFG_WT, False)].split())
    check("installer, below the top, isolation worktree set explicitly: "
          "kept, with a warning that its commits will be refused, and to "
          "ignore /.claude/worktrees/ at the top",
          "\nisolation: worktree\n" in open(os.path.join(
              _pw, ".claude/agents/implementer.md")).read()
          and "workflow.implementer_isolation is set to worktree, so its "
          "commits will be refused there" in _err_wt
          and "Add `/.claude/worktrees/` to" in _err_wt, _err_wt[-1500:])
    fixture_sub(CFG_WT, top_ignore=True)
    _err_wt2 = " ".join(SUB_STDERR[("sub", CFG_WT, True)].split())
    check("... and with /.claude/worktrees/ ignored at the top already, it "
          "does not ask to add it",
          "is set to worktree" in _err_wt2
          and "Add `/.claude/worktrees/`" not in _err_wt2, _err_wt2[-800:])
    _d = tempfile.mkdtemp(prefix="topi-", dir=WORK)
    git(_d, "init", "-q", "-b", "main")
    write(_d + ".yaml", CFG)
    _r = run([sys.executable, BIN, "-c", _d + ".yaml", "-C", _d], _d)
    check("installer at the repository top: isolation worktree, and no "
          "below-the-top warning",
          _r.returncode == 0 and "Claude Code makes an implementer's "
          "worktree" not in _r.stderr and "\nisolation: worktree\n" in open(
              os.path.join(_d, ".claude/agents/implementer.md")).read(),
          _r.stderr[-800:])
    check("the emitted script no longer refuses a project below the top",
          "at the repository top only" not in MB)
    _apply = " ".join(open(os.path.join(
        ROOT, "plugin/commands/bootstrap-apply.md")).read().split())
    check("bootstrap-apply.md names the below-top warning among the lines "
          "to relay",
          "for a project below the repository top, why worktree isolation "
          "`auto` resolves to none there (or what an explicit `worktree` "
          "costs) and what `.claude/merge-back.sh` does there;" in _apply)
    check("below the top, the implementer's isolation note says why it is "
          "off there",
          "Here that is because this project is `pkg/svc/` below its "
          "repository's top" in " ".join(_impl_sub.split()), _impl_sub[-1200:])
    # [WP3 fix2 IT-3] The installer's below-top fact reaches the other
    # isolation-off texts of the same install, not implementer.md's reason
    # alone.
    _tech_sub = " ".join(open(os.path.join(
        p, ".claude/steering/tech.md")).read().split())
    check("below the top, tech.md gives that reason too, and neither it nor "
          "implementer.md offers a per-worktree mount as the way back (IT-3)",
          "this project is `pkg/svc/` below its repository's top, and "
          "Claude Code would make the agent's worktree at the repository "
          "top" in _tech_sub
          and "therefore emitted WITHOUT" not in _tech_sub
          and "own mount" not in _impl_sub
          and "is set back to `worktree`" not in open(os.path.join(
              p, ".claude/agents/integrator.md")).read(), _tech_sub[-900:])
    wt, tip = impl_sub(top, "a", {"src/feature.py":
                                  "def feature(): return 2\n"})
    pre = head(top)
    rc, out, last = mb(p, "worktree-agent-a")
    check("below the top: a worktree at the repository top's "
          ".claude/worktrees/ lands: MERGED rc 0, a --no-ff merge of the tip",
          rc == 0 and last.startswith("merge-back: MERGED worktree-agent-a")
          and git(top, "rev-parse", "HEAD^1").stdout.strip() == pre
          and git(top, "rev-parse", "HEAD^2").stdout.strip() == tip, out)
    check("below the top: the gates ran in the project directory (its "
          "tests/run.sh, found from there, passed) and the spec check ran",
          "tests ok" in out and "[test-gate] allowed (exit 0)" in out
          and "[spec-check] " in out, out)
    check("below the top: the worktree is removed and the branch deleted",
          not os.path.exists(wt) and not has_branch(top, "worktree-agent-a"),
          out)
    check("below the top: the output says the git steps cover the whole "
          "repository and the gates run in the project",
          "Note: the project is pkg/svc/ in the git repository at" in out
          and "the gates run in" in out, out)
    wt, tip = impl_sub(top, "b", {"src/feature.py": "x = 'BROKEN'\n"})
    pre = head(top)
    rc, out, last = mb(p, "worktree-agent-b")
    check("below the top: a merged result that fails the tests is REFUSED "
          "and aborted; the remedy names the project inside the worktree",
          rc == 2 and last.startswith("merge-back: REFUSED test-gate refused")
          and head(top) == pre and clean(top)
          and os.path.realpath(wt) + "/pkg/svc" in " ".join(out.split()),
          out)
    write(os.path.join(top, "other/lib.py"), "x = 2  # local\n")
    rc, out, last = mb(p, "worktree-agent-b")
    check("below the top: a tracked change elsewhere in the repository "
          "counts as dirty (it would ride into the merge commit)",
          rc == 3 and "not clean" in last and "other/lib.py" in out
          and head(top) == pre, out)
    git(top, "checkout", "-q", "--", "other/lib.py")
    rc, out, last = mb(os.path.join(wt, SUB), "worktree-agent-b")
    check("below the top: the worktree's own copy refuses and names the main "
          "checkout's copy of the project's script",
          rc == 3 and "linked worktree" in last
          and last.endswith(f"{_top_real}/pkg/svc/.claude/merge-back.sh"),
          out)
    # The installer's own layout, .claude/worktrees/ under the project, is
    # this script's to remove too.
    wt, tip = impl_sub(top, "c", {"src/feature.py":
                                  "def feature(): return 3\n"}, wt_root=p)
    rc, out, last = mb(p, "worktree-agent-c")
    check("below the top: a worktree under the project's .claude/worktrees/ "
          "lands and is removed too",
          rc == 0 and last.startswith("merge-back: MERGED")
          and not os.path.exists(wt), out)
    # A gitlink an older install committed under the PROJECT's
    # .claude/worktrees/ (no ignore line then), since moved on: not dirty.
    top3, p3 = fixture_sub()
    _gi = os.path.join(p3, ".claude/.gitignore")
    write(_gi, open(_gi).read().replace("/worktrees/\n", ""))
    git(top3, "commit", "-qam", "an older .gitignore without the line")
    impl_sub(top3, "old", {"src/old.py": "o = 1\n"}, wt_root=p3)
    git(top3, "add", "-A")
    git(top3, "commit", "-qm", "commits a gitlink by accident")
    impl_sub(top3, "old", {"src/old.py": "o = 2\n"}, wt_root=p3)
    check("(precondition) below the top, a committed gitlink under the "
          "project's .claude/worktrees/ shows as modified",
          " M pkg/svc/.claude/worktrees/agent-old" in git(
              top3, "status", "--porcelain").stdout)
    impl_sub(top3, "q", {"src/feature.py": "def feature(): return 14\n"})
    rc, out, last = mb(p3, "worktree-agent-q")
    check("below the top: that modified gitlink does not count as dirty",
          rc == 0 and last.startswith("merge-back: MERGED"), out)
    # A conflict: the brief says where the merge is, and git's paths are
    # from the top.
    impl_sub(top, "d", {"src/app.py": "def app(): return 3  # d\n"})
    write(os.path.join(p, "src/app.py"), "def app(): return 4  # main\n")
    git(top, "commit", "-qam", "main edits app")
    rc, out, last = mb(p, "worktree-agent-d")
    check("below the top: a conflict stops at the repository top, and the "
          "brief names it and the file from the top",
          rc == 4 and f"progress in {_top_real}." in " ".join(out.split())
          and "    pkg/svc/src/app.py" in out, out)
    git(top, "merge", "--abort")
    # The spec check, block mode, on the merge's own change below the top.
    top, p = fixture_sub()
    set_spec_mode(p, "block")
    wt, _ = shared_change(p, "e", top=top, rel="pkg/svc")
    pre = head(top)
    rc, out, last = mb(p, "worktree-agent-e")
    _flat = " ".join(out.split())
    check("below the top, block: the merge's own unlisted change is REFUSED "
          "by the project's spec check, and the remedy edits the task file "
          "in the project inside the worktree",
          rc == 2 and last.startswith("merge-back: REFUSED spec-check refused")
          and "src/shared.py" in out and head(top) == pre
          and "edit its copy in " + os.path.realpath(wt) + "/pkg/svc with "
          "the Edit tool" in _flat, out)

    print("\n== a test command this checkout lacks (MB-2) ==")
    _tg = P_ON[".claude/hooks/test-gate.sh"]["body"]
    check("merge-back greps for test-gate's own words: its exit-127 line "
          "and the header's fail-closed line",
          "Commit blocked: test command not found (exit 127): sh tests/run.sh"
          in _tg and "printf 'BLOCKED (fail-closed): %s" in _tg
          and "grep -qF -e 'Commit blocked: test command not found (exit "
          "127): ' -e 'BLOCKED (fail-closed): ' \"$OUT\"" in MB)
    # The implementer's worktree has its own (ignored) toolchain; the main
    # checkout has none. test-gate exits 2 for that as for a red suite.
    CFG_VENV = CFG.replace('test: "sh tests/run.sh"',
                           'test: ".venv/bin/runtests"')
    p = fixture(CFG_VENV)
    write(os.path.join(p, ".gitignore"), "/.venv/\n")
    git(p, "add", ".gitignore")
    git(p, "commit", "-qm", "ignore the venv")
    wt, tip = impl(p, "v", {"src/feature.py": "def feature(): return 2\n"})
    write(os.path.join(wt, ".venv/bin/runtests"), "#!/bin/sh\necho 'ok'\n")
    os.chmod(os.path.join(wt, ".venv/bin/runtests"), 0o755)
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-v")
    _flat = " ".join(out.split())
    if "test command not found (exit 127)" in out:
        check("test-gate's exit 127 (no such command here) is REFUSED as a "
              "gate that could not run the tests, not as a test failure",
              rc == 2 and "REFUSED test-gate could not run the tests, which "
              "is not a test failure" in last and head(p) == pre
              and clean(p), out)
        check("... and its remedy goes to the operator, never back to the "
              "implementer as the branch's failure",
              "Stop and give this output to the operator" in _flat
              and "return the task to the implementer" not in _flat
              and "fails the tests" not in _flat, out)
    else:
        # bash 3.2 exits 1, not 127, for a command it cannot find under the
        # hook's errexit, so test-gate itself says "tests failing (exit 1)"
        # there (measured, bash 3.2.57; the rows below cover merge-back's
        # side on every bash).
        print("  NOTE  the real test gate did not report exit 127 on this "
              "bash; its two end-to-end rows are not run")
    # merge-back's side on every bash: a gate that prints test-gate's own
    # words for exit 127 (TEST_GATE_NOT_RUN[0]).
    p = fixture()
    write(os.path.join(p, ".claude/hooks/test-gate.sh"),
          "#!/bin/sh\necho 'Commit blocked: test command not found (exit "
          "127): .venv/bin/runtests' >&2\nexit 2\n")
    git(p, "commit", "-qam", "a test gate that finds no test command")
    impl(p, "v1", {"src/feature.py": "def feature(): return 2\n"})
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-v1")
    _flat = " ".join(out.split())
    check("test-gate's words for exit 127 make it a gate that could not run "
          "the tests, routed to the operator, not to the implementer",
          rc == 2 and "REFUSED test-gate could not run the tests, which is "
          "not a test failure" in last and head(p) == pre and clean(p)
          and "Stop and give this output to the operator" in _flat
          and "return the task to the implementer" not in _flat, out)
    p = fixture()
    write(os.path.join(p, ".claude/hooks/test-gate.sh"),
          "#!/bin/sh\necho 'BLOCKED (fail-closed): no WORKING JSON parser' "
          ">&2\nexit 2\n")
    git(p, "commit", "-qam", "a test gate that fails closed")
    impl(p, "v2", {"src/feature.py": "def feature(): return 2\n"})
    rc, out, last = mb(p, "worktree-agent-v2")
    check("a test gate that failed closed (exit 2, hook_fail) is a gate "
          "error too, routed to the operator",
          rc == 2 and "could not run the tests" in last
          and "Stop and give this output to the operator" in out, out)
    p = fixture()
    wt, _ = impl(p, "v3", {"src/feature.py": "x = 'BROKEN'\n"})
    rc, out, last = mb(p, "worktree-agent-v3")
    _flat = " ".join(out.split())
    check("a red suite with main unmoved: the remedy still says which way "
          "a pass in the worktree goes (the operator: this checkout's "
          "untracked or ignored files differ)",
          rc == 2 and "REFUSED test-gate refused" in last
          and "If the tests also fail in " + os.path.realpath(wt) + ", the "
          "failure is worktree-agent-v3's own: return the task to the "
          "implementer with this output. If they pass there, the "
          "difference is this checkout's untracked or ignored files" in _flat
          and "stop and give this output to the operator." in _flat, out)

    print("\n== interrupted after the merge commit (MB-3) ==")
    p = fixture()
    wt, tip = impl(p, "pc", {"src/feature.py": "def feature(): return 20\n"})
    hook = os.path.join(p, ".git/hooks/post-commit")
    write(hook, "#!/bin/sh\nsleep 3\n")
    os.chmod(hook, 0o755)
    pre = head(p)
    proc = subprocess.Popen([mb_path(p), "worktree-agent-pc"], cwd=p,
                            env=AGENT_ENV, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            start_new_session=True)
    deadline = time.time() + 60
    while time.time() < deadline and git(
            p, "rev-parse", "-q", "--verify",
            "HEAD^2").stdout.strip() != tip:
        time.sleep(0.05)
    proc.send_signal(signal.SIGTERM)
    try:
        out, _ = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        out, _ = proc.communicate()
    last = out.rstrip().splitlines()[-1] if out.strip() else ""
    merge_sha = git(p, "rev-parse", "--short", "HEAD").stdout.strip()
    check("SIGTERM once the merge commit exists (a slow post-commit hook): "
          "rc 5 CLEANUP MERGED, naming the commit and the rerun that "
          "cleans up",
          proc.returncode == 5
          and last.startswith(f"merge-back: CLEANUP MERGED worktree-agent-pc "
                              f"into main as {merge_sha};")
          and "run .claude/merge-back.sh worktree-agent-pc again" in last
          and git(p, "rev-parse", "HEAD^2").stdout.strip() == tip
          and os.path.isdir(wt), f"rc={proc.returncode}\n{out}")
    # [WP3 fix3 MBS-6] It checks neither what is left, so it says "may".
    check("... and the line claims no more than it checked: the worktree or "
          "the branch may be left (a TERM during git worktree remove lets "
          "the removal finish)",
          "interrupted before its cleanup finished, so the worktree or the "
          "branch may be left. To finish, run .claude/merge-back.sh "
          "worktree-agent-pc again" in last, last)
    os.remove(hook)
    rc, out, last = mb(p, "worktree-agent-pc")
    check("run again: ALREADY-MERGED names the merge that landed it, never "
          "'nothing was merged', and cleans up",
          rc == 0 and last.startswith(
              f"merge-back: ALREADY-MERGED worktree-agent-pc was merged into "
              f"main earlier, in merge {merge_sha}; nothing new to merge")
          and "nothing was merged" not in out
          and "another branch" not in out
          and not os.path.exists(wt)
          and not has_branch(p, "worktree-agent-pc"), out)
    # A removal cut short: the worktree directory is left with no .git file.
    p = fixture()
    wt, tip = impl(p, "ng", {"src/feature.py": "def feature(): return 21\n"})
    write(os.path.join(wt, "build.out"), "artifact\n")
    rc1, _, _ = mb(p, "worktree-agent-ng")
    os.remove(os.path.join(wt, "build.out"))
    os.remove(os.path.join(wt, ".git"))
    rc, out, last = mb(p, "worktree-agent-ng")
    check("(precondition) merged, then the worktree lost its .git file",
          rc1 == 5 and git(p, "rev-parse", "HEAD^2").stdout.strip() == tip)
    check("a worktree with no .git file: rc 5 CLEANUP, the branch named as "
          "merged, and a remedy git can carry out (prune, then rm -rf)",
          rc == 5 and "was merged into main earlier" in last
          and "has no .git file" in last and "git worktree prune && rm -rf "
          in last and "git worktree remove --force" not in last, out)
    r = run(["sh", "-c", last.split("to finish: ", 1)[1]
             if "to finish: " in last else "false"], p)
    check("... and following that remedy leaves no worktree and no branch",
          r.returncode == 0 and not os.path.exists(wt)
          and not has_branch(p, "worktree-agent-ng")
          and "agent-ng" not in git(p, "worktree", "list").stdout,
          r.stdout + r.stderr)

    print("\n== a test that touches the terminal (MB-4, RG-1) ==")
    # [WP3 fix2 RG-1] Fix round 1 ran each gate in a session of its own
    # (setsid), so a test that opens /dev/tty failed fast at a person's
    # terminal too; it also ran the gates with SIGINT and SIGQUIT ignored.
    # setsid is gone: with no terminal (Claude Code) /dev/tty still fails
    # fast, and at a person's terminal the stop is disclosed, and one
    # Ctrl-C ends it.
    TTY_SUITE = ("#!/bin/sh\nstty -echo </dev/tty 2>/dev/null\n"
                 "stty echo </dev/tty 2>/dev/null\necho 'tests ok'\n")
    p = fixture()
    write(os.path.join(p, "tests/run.sh"), TTY_SUITE)
    git(p, "commit", "-qam", "a suite that sets terminal modes")
    impl(p, "tty", {"src/feature.py": "def feature(): return 30\n"})
    r = subprocess.run([mb_path(p), "worktree-agent-tty"], cwd=p,
                       env=AGENT_ENV, capture_output=True, text=True,
                       timeout=60, start_new_session=True)
    reap(p)
    check("with no controlling terminal (as under Claude Code), a gate that "
          "runs stty on /dev/tty does not stop the run: MERGED",
          r.returncode == 0
          and "merge-back: MERGED worktree-agent-tty" in r.stdout,
          f"rc={r.returncode}\n{(r.stdout + r.stderr)[-1500:]}")
    _hdr = " ".join(open(mb_path(p)).read().split("\nGATES=", 1)[0]
                    .replace("#", " ").split())
    check("the script's header discloses the terminal stop: at a person's "
          "terminal a test that opens /dev/tty stops until Ctrl-C ends the "
          "run",
          "at a person's terminal, a test that opens /dev/tty: each gate "
          "runs as a background job, so that test stops until Ctrl-C ends "
          "the run" in _hdr, _hdr[-1200:])
    p = fixture()
    write(os.path.join(p, "tests/run.sh"), TTY_SUITE)
    git(p, "commit", "-qam", "a suite that sets terminal modes")
    impl(p, "tty2", {"src/feature.py": "def feature(): return 31\n"})
    pre = head(p)
    rc, out, took = run_pty([mb_path(p), "worktree-agent-tty2"], p,
                            AGENT_ENV, keys=b"\x03",
                            key_after="[test-gate] on the merged result",
                            timeout=40)
    reap(p)
    check("at a person's terminal, a gate that opens /dev/tty stops (a "
          "background job, as disclosed), and one Ctrl-C ends the run at "
          "once, the merge aborted",
          rc == 1 and took is not None and took < 2.5
          and "merge-back: ERROR interrupted while the gates ran" in out
          and head(p) == pre and clean(p),
          f"rc={rc} took={took}\n{out[-1500:]}")

    print("\n== interrupted as a gate starts (TP-01, CR-3) ==")
    bad = []
    for i in range(5):
        p = fixture()
        write(os.path.join(p, "SLOW"), "")
        git(p, "add", "SLOW")
        git(p, "commit", "-qm", "slow suite")
        impl(p, f"tp{i}", {"src/feature.py": f"def feature(): return {i}\n"})
        pre = head(p)
        proc = subprocess.Popen([mb_path(p), f"worktree-agent-tp{i}"],
                                cwd=p, env=AGENT_ENV, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                start_new_session=True)
        t0, lines = None, []
        while True:
            ln = proc.stdout.readline()
            if not ln:
                break
            lines.append(ln)
            if ln.startswith("[test-gate] on the merged result"):
                proc.send_signal(signal.SIGTERM)
                t0 = time.time()
                break
        try:
            rest, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            rest, _ = proc.communicate()
        took = time.time() - t0 if t0 else None
        time.sleep(0.5)
        left = procs_with(p) + procs_with(f"sleep {SLOW_SECS}")
        reap(p)
        reap(f"sleep {SLOW_SECS}")
        out = "".join(lines) + rest
        # [WP3 fix2 MBR-2] 15 s, not 6: a TERM that lands while the gate is
        # starting can be lost (CR-3), and since fix round 2 one TERM is
        # sent, not one every 0.1 s, so the KILL at 10 s ends such a run.
        ok = (t0 is not None and proc.returncode == 1 and took < 15
              and "the merge of worktree-agent-tp" in out
              and "was aborted" in out and not left
              and head(p) == pre and clean(p))
        if not ok:
            bad.append(f"run {i}: rc={proc.returncode} took={took} "
                       f"left={left}\n{out[-600:]}")
    check("SIGTERM the moment a gate is launched, 5 times: each run aborts "
          "in seconds and leaves no gate process behind",
          not bad, "\n".join(bad))

    # ======================================================================= #
    # [WP3 fix2] The re-review's merge-back findings on signal handling and
    # robustness (RG-1, MBR-1, MBR-2, MBR-3, CRIT-2), each pinned by a row
    # that fails without its fix. Fix round 2 subtracts: no setsid, and one
    # TERM to a gate, then up to 10 s, then KILL.
    # ======================================================================= #
    import shlex

    def start_mb(proj, br, env=AGENT_ENV):
        return subprocess.Popen([mb_path(proj), br], cwd=proj, env=env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                start_new_session=True)

    def read_until(proc, prefix):
        """The output lines up to and including the first that starts with
        `prefix` (all of them, if none does)."""
        lines = []
        while True:
            ln = proc.stdout.readline()
            if not ln:
                return lines
            lines.append(ln)
            if ln.startswith(prefix):
                return lines

    def wait_for(pred, secs=30):
        deadline = time.time() + secs
        while time.time() < deadline:
            if pred():
                return True
            time.sleep(0.05)
        return False

    def rest_of(proc, timeout=40):
        try:
            out, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            out, _ = proc.communicate()
        return out

    def words_in(path):
        return open(path).read().split() if os.path.exists(path) else []

    def last_line(out):
        return out.rstrip().splitlines()[-1] if out.strip() else ""

    print("\n== the gates keep this script's SIGINT and SIGQUIT (RG-1) ==")
    PROBE = ("import signal\n"
             "def d(s):\n"
             "    return 'ignored' if signal.getsignal(s) == signal.SIG_IGN "
             "else 'default'\n"
             "print('DISP INT=%s QUIT=%s' % (d(signal.SIGINT), "
             "d(signal.SIGQUIT)))\n")
    want = run([sys.executable, "-c", PROBE], WORK).stdout.strip()
    p = fixture()
    write(os.path.join(p, "tests/run.sh"),
          "#!/bin/sh\n" + shlex.quote(sys.executable) + " -c "
          + shlex.quote(PROBE) + "\necho 'tests ok'\n")
    git(p, "commit", "-qam", "a suite that reports its signal dispositions")
    impl(p, "sg", {"src/feature.py": "def feature(): return 32\n"})
    rc, out, last = mb(p, "worktree-agent-sg")
    got = re.findall(r"DISP INT=\w+ QUIT=\w+", out)
    check("(precondition) the probe reads SIGINT and SIGQUIT here",
          want.startswith("DISP INT="), want)
    check("a gate runs with this script's own SIGINT and SIGQUIT (fix round "
          "1's setsid ran it with both ignored, so a suite that tests "
          "Ctrl-C failed only here): MERGED",
          rc == 0 and got == [want], f"want {want!r} got {got}\n{out}")

    print("\n== interrupted: a suite's TERM teardown runs to its end (MBR-2) ==")
    TD_SECS = f"41.{os.getpid() % 1000:03d}"

    def td_suite(log, ignore_term=False):
        """A suite that logs `ready`, then sleeps TD_SECS. Its TERM trap
        logs `start`, takes 1.5 s, logs `done` and exits 143; with
        `ignore_term` it ignores TERM instead."""
        lg = shlex.quote(log)
        if ignore_term:
            return ("#!/bin/sh\ntrap '' TERM\necho ready >>" + lg + "\n"
                    "sleep " + TD_SECS + "\n")
        return ("#!/bin/sh\n"
                "teardown() { echo start >>" + lg + "; sleep 1.5; "
                "echo done >>" + lg + "; exit 143; }\n"
                "trap teardown TERM\necho ready >>" + lg + "\n"
                "sleep " + TD_SECS + " &\nwait\n")

    def td_fixture(name, ignore_term=False):
        p = fixture()
        log = os.path.join(WORK, f"td-{name}.log")
        write(os.path.join(p, "tests/run.sh"), td_suite(log, ignore_term))
        git(p, "commit", "-qam", "a suite with a TERM teardown")
        impl(p, name, {"src/feature.py": "def feature(): return 33\n"})
        return p, log

    p, log = td_fixture("td")
    pre = head(p)
    proc = start_mb(p, "worktree-agent-td")
    lines = read_until(proc, "[test-gate] on the merged result")
    ready = wait_for(lambda: "ready" in words_in(log))
    proc.send_signal(signal.SIGTERM)
    out = "".join(lines) + rest_of(proc)
    td = words_in(log)
    left = procs_with(f"sleep {TD_SECS}")
    reap(f"sleep {TD_SECS}")
    check("SIGTERM while a suite with a TERM teardown runs: the teardown "
          "runs once and to its end before the run ends (fix round 1 "
          "re-sent TERM every 0.1 s and cut it short); rc 1, the merge "
          "aborted",
          ready and proc.returncode == 1
          and last_line(out).startswith("merge-back: ERROR interrupted "
                                        "while the gates ran; the merge of "
                                        "worktree-agent-td was aborted")
          and "Stopping the gates (up to 10 s)..." in out
          and td.count("start") == 1 and td.count("done") == 1
          and not left and head(p) == pre and clean(p),
          f"rc={proc.returncode} log={td} left={left}\n{out[-1500:]}")

    print("\n== interrupted twice (MBR-1) ==")
    p, log = td_fixture("ti", ignore_term=True)
    pre = head(p)
    proc = start_mb(p, "worktree-agent-ti")
    lines = read_until(proc, "[test-gate] on the merged result")
    ready = wait_for(lambda: "ready" in words_in(log))
    proc.send_signal(signal.SIGTERM)
    t0 = time.time()
    time.sleep(1.0)
    proc.send_signal(signal.SIGTERM)
    out = "".join(lines) + rest_of(proc)
    took = time.time() - t0
    left = procs_with(f"sleep {TD_SECS}")
    reap(f"sleep {TD_SECS}")
    check("two SIGTERMs while a suite that ignores TERM runs: the second "
          "does not kill the script; the suite is KILLed after 10 s, and "
          "the run still ends with the abort as its last line",
          ready and proc.returncode == 1 and 9 <= took < 20
          and last_line(out).startswith("merge-back: ERROR interrupted "
                                        "while the gates ran; the merge of "
                                        "worktree-agent-ti was aborted")
          and not left and head(p) == pre and clean(p),
          f"rc={proc.returncode} took={took:.1f} left={left}\n{out[-1500:]}")
    p, log = td_fixture("tc")
    pre = head(p)
    rc, out, took = run_pty([mb_path(p), "worktree-agent-tc"], p, AGENT_ENV,
                            keys=b"\x03",
                            key_after="[test-gate] on the merged result",
                            key_delay=1.0, again=0.5, timeout=40)
    td = words_in(log)
    reap(p)
    reap(f"sleep {TD_SECS}")
    check("Ctrl-C twice at a terminal while a suite's teardown runs: the "
          "teardown ends, and the run still ends with the abort as its "
          "last line",
          rc == 1 and took is not None and took > 1.0
          and last_line(out.replace("^C", "")).startswith(
              "merge-back: ERROR interrupted while the gates ran; the merge "
              "of worktree-agent-tc was aborted")
          and td.count("start") == 1 and td.count("done") == 1
          and head(p) == pre and clean(p),
          f"rc={rc} took={took} log={td}\n{out[-1500:]}")

    print("\n== interrupted while git merges (MBR-3) ==")
    # A slow checkout, as with git-lfs: a smudge filter that takes 0.3 s a
    # file and logs each one, so a row can send its signal mid-checkout.
    SMUDGE = os.path.join(WORK, "slow-smudge")
    write(SMUDGE, "#!/bin/sh\necho x >>\"$SMUDGE_LOG\"\nsleep 0.3\nexec cat\n")
    os.chmod(SMUDGE, 0o755)

    def slow_fixture(name, n_mod=0, n_new=0):
        p = fixture()
        log = os.path.join(WORK, f"smudge-{name}.log")
        git(p, "config", "filter.slow.smudge",
            "SMUDGE_LOG=" + shlex.quote(log) + " " + shlex.quote(SMUDGE))
        write(os.path.join(p, ".gitattributes"),
              "src/m*.py filter=slow\ndata/* filter=slow\n")
        mods = {f"src/m{i:02d}.py": f"V = {i}\n" for i in range(n_mod)}
        for rel, text in mods.items():
            write(os.path.join(p, rel), text)
        git(p, "add", "-A")
        git(p, "commit", "-qm", "files with a slow checkout")
        files = {rel: f"V = {i} + 100\n" for i, rel in enumerate(mods)}
        files.update({f"data/n{i:02d}.bin": f"blob {i}\n"
                      for i in range(n_new)})
        _, tip = impl(p, name, files)
        open(log, "w").close()
        return p, log, tip

    def interrupt_merge(p, log, br, group=True):
        """Start merge-back, and signal it once git has written two files:
        its whole process group (a Ctrl-C, a session's end), or the script
        alone. Returns (rc, output, files written before the signal)."""
        proc = start_mb(p, br)
        lines = read_until(proc, "Merging ")
        wait_for(lambda: len(words_in(log)) >= 2, 20)
        n = len(words_in(log))
        if group:
            os.killpg(proc.pid, signal.SIGTERM)
        else:
            proc.send_signal(signal.SIGTERM)
        out = "".join(lines) + rest_of(proc, 60)
        return proc.returncode, out, n

    p, log, tip = slow_fixture("sm", n_mod=12)
    pre = head(p)
    rc, out, n = interrupt_merge(p, log, "worktree-agent-sm")
    check("(precondition) git was mid-checkout when the signal came",
          0 < n < 12, f"{n} of 12 files written")
    check("a signal to the group while git merges (its checkout part done): "
          "rc 1, the merge undone, and the tracked files restored (fix round "
          "1 left some modified and one deleted, with no merge in progress, "
          "and a rerun then said to commit them)",
          rc == 1 and last_line(out).startswith(
              "merge-back: ERROR interrupted while git merged "
              "worktree-agent-sm; the merge was undone and main is unchanged."
              " To land worktree-agent-sm, run it again")
          and head(p) == pre and clean(p), f"rc={rc}\n{out[-1500:]}")
    rc, out, last = mb(p, "worktree-agent-sm")
    check("... and running it again lands the branch: MERGED",
          rc == 0 and last.startswith("merge-back: MERGED worktree-agent-sm"),
          out)
    p, log, tip = slow_fixture("sn", n_new=10)
    pre = head(p)
    rc, out, n = interrupt_merge(p, log, "worktree-agent-sn")
    listed = [ln.strip() for ln in out.split(
        " adds; the interrupted merge wrote them, unless they were here "
        "before it:\n", 1)[-1].splitlines() if ln.startswith("    ")]
    check("(precondition) git was mid-checkout of the files the branch adds",
          0 < n < 10, f"{n} of 10 files written")
    check("a signal while git writes the files the branch adds: rc 1, and "
          "the untracked files it wrote are listed, with the line saying to "
          "remove them before running it again",
          rc == 1 and listed and all(f.startswith("data/n") for f in listed)
          and all(os.path.exists(os.path.join(p, f)) for f in listed)
          and last_line(out).startswith(
              "merge-back: ERROR interrupted while git merged "
              "worktree-agent-sn; the merge was undone and main is unchanged,"
              " but for the untracked files above. Remove the ones the merge "
              "wrote, then run it again")
          and head(p) == pre and clean(p), f"rc={rc} listed={listed}\n{out}")
    for f in listed:
        os.remove(os.path.join(p, f))
    rc, out, last = mb(p, "worktree-agent-sn")
    check("... and once they are removed, running it again lands the "
          "branch: MERGED",
          rc == 0 and last.startswith("merge-back: MERGED worktree-agent-sn"),
          out)
    p, log, tip = slow_fixture("st", n_mod=12)
    pre = head(p)
    rc, out, n = interrupt_merge(p, log, "worktree-agent-st", group=False)
    check("SIGTERM to the script alone while git merges: git finishes, and "
          "the merge is undone, not left in progress (fix round 1 left it)",
          rc == 1 and last_line(out).startswith(
              "merge-back: ERROR interrupted while git merged "
              "worktree-agent-st; the merge was undone and main is unchanged")
          and head(p) == pre and clean(p) and not merging(p),
          f"rc={rc}\n{out[-1500:]}")

    # ======================================================================= #
    # [WP3 fix3] Re-review 2's merge-back findings (MBS-1 to MBS-6). Under
    # the operator's rule for a third round of signal findings, two are
    # disclosed rather than fixed (MBS-2, MBS-4), and none adds machinery.
    # ======================================================================= #
    def ready_suite(log, before=""):
        """A suite that runs `before`, logs `ready`, then sleeps TD_SECS."""
        return ("#!/bin/sh\n" + before + "echo ready >>" + shlex.quote(log)
                + "\nsleep " + TD_SECS + "\necho 'tests ok'\n")

    print("\n== interrupted, its output piped to a reader the same "
          "interruption ended (MBS-1) ==")
    # A person's `| tee` at a terminal, or an agent's `2>&1 | tail`: the
    # Ctrl-C (or the session's end) ends the reader too. To be
    # deterministic the row ends the reader first, then types Ctrl-C, so
    # on_signal's first write always meets a pipe with no reader.
    p = fixture()
    log = os.path.join(WORK, "pp.log")
    write(os.path.join(p, "tests/run.sh"), ready_suite(log))
    git(p, "commit", "-qam", "a suite that logs when it runs")
    impl(p, "pp", {"src/feature.py": "def feature(): return 36\n"})
    pre = head(p)
    rpid = os.path.join(WORK, "pp.reader-pid")
    pstat = os.path.join(WORK, "pp.pipestatus")
    reader = ("echo $$ >" + shlex.quote(rpid) + "; exec tee "
              + shlex.quote(os.path.join(WORK, "pp.tee")))
    cmd = (shlex.quote(mb_path(p)) + " worktree-agent-pp 2>&1 | sh -c "
           + shlex.quote(reader) + '; echo "${PIPESTATUS[*]}" >'
           + shlex.quote(pstat))
    pre_keys = {}

    def end_reader():
        pre_keys["ready"] = wait_for(lambda: "ready" in words_in(log))
        rp = int(open(rpid).read().split()[0])
        os.kill(rp, signal.SIGKILL)

        def gone():
            try:
                os.kill(rp, 0)
                return False
            except ProcessLookupError:
                return True
        pre_keys["gone"] = wait_for(gone, 10)
    rc, out, took = run_pty([BASH, "-c", cmd], p, AGENT_ENV, keys=b"\x03",
                            key_after="[test-gate] on the merged result",
                            key_delay=0.2, before_keys=end_reader,
                            timeout=40)
    time.sleep(0.5)
    left = procs_with(f"sleep {TD_SECS}")
    reap(p)
    reap(f"sleep {TD_SECS}")
    ps = open(pstat).read().split() if os.path.exists(pstat) else []
    check("(precondition) the suite was running, and the reader had ended, "
          "before the Ctrl-C",
          pre_keys.get("ready") and pre_keys.get("gone"), str(pre_keys))
    check("Ctrl-C at a terminal with its output piped to `| tee`, the reader "
          "ended first: the write to the closed pipe does not kill it; the "
          "gate is stopped, the merge aborted, and the last line logged "
          "(it died of SIGPIPE, exit 141, and left the gate running and the "
          "merge in progress)",
          ps[:1] == ["1"] and not left and not merging(p)
          and head(p) == pre and clean(p)
          and "merge-back ERROR interrupted while the gates ran; the merge "
          "of worktree-agent-pp was aborted" in hooks_log(p),
          f"pipestatus={ps} left={left} merging={merging(p)}\n"
          f"{hooks_log(p)[-600:]}\n{out[-800:]}")

    print("\n== interrupted after a gate changed a merged file (MBS-3) ==")
    p = fixture()
    log = os.path.join(WORK, "gd.log")
    write(os.path.join(p, "tests/run.sh"), ready_suite(
        log, "echo '# regenerated by the suite' >>src/feature.py\n"))
    git(p, "commit", "-qam", "a suite that rewrites a tracked file")
    impl(p, "gd", {"src/feature.py": "def feature(): return 37\n"})
    pre = head(p)
    proc = start_mb(p, "worktree-agent-gd")
    lines = read_until(proc, "[test-gate] on the merged result")
    ready = wait_for(lambda: "ready" in words_in(log))
    proc.send_signal(signal.SIGTERM)
    out = "".join(lines) + rest_of(proc)
    left = procs_with(f"sleep {TD_SECS}")
    reap(f"sleep {TD_SECS}")
    check("SIGTERM while the gates run, after a gate changed a file the "
          "merge brought in: git refuses the abort, so the last line names "
          "the file and the way out git accepts (it said 'To retry: git "
          "merge --abort', which git refuses)",
          ready and proc.returncode == 1 and last_line(out) ==
          "merge-back: ERROR interrupted while the gates ran, and the merge "
          "could not be aborted; the merge of worktree-agent-gd is still in "
          "progress. To drop it: git checkout -- :/ (it discards every "
          "unstaged change, the files above included), then git merge --abort"
          and "    src/feature.py" in out and not left and head(p) == pre,
          f"rc={proc.returncode} left={left}\n{out[-1500:]}")
    r = run(["sh", "-c", "git checkout -- src/feature.py && "
             "git merge --abort"], p)
    check("... and following it restores the tree",
          r.returncode == 0 and head(p) == pre and clean(p)
          and not merging(p), r.stdout + r.stderr)

    print("\n== interrupted inside the concluding commit's git hooks "
          "(MBS-2) ==")
    p = fixture()
    log = os.path.join(WORK, "cm.log")
    wt, tip = impl(p, "cm", {"src/feature.py": "def feature(): return 38\n"})
    hook = os.path.join(p, ".git/hooks/commit-msg")
    write(hook, "#!/bin/sh\necho ready >>" + shlex.quote(log)
          + "\nsleep " + TD_SECS + "\n")
    os.chmod(hook, 0o755)
    pre = head(p)
    proc = start_mb(p, "worktree-agent-cm")
    ready = wait_for(lambda: "ready" in words_in(log), 60)
    os.killpg(proc.pid, signal.SIGTERM)
    out = rest_of(proc)
    left = procs_with(f"sleep {TD_SECS}")
    reap(f"sleep {TD_SECS}")
    mh = open(os.path.join(p, ".git/MERGE_HEAD")).read().strip() \
        if merging(p) else ""
    check("a signal to the group inside the concluding commit's commit-msg "
          "hook: the merge stays in progress, as the header and the note "
          "now say, and the last line says so and how to retry",
          ready and proc.returncode == 1 and last_line(out) ==
          "merge-back: ERROR interrupted; a merge of worktree-agent-cm is "
          "still in progress here. To retry: git merge --abort, then "
          ".claude/merge-back.sh worktree-agent-cm"
          and mh == tip and head(p) == pre and not left,
          f"rc={proc.returncode} left={left}\n{out[-1500:]}")
    os.remove(hook)
    r = git(p, "merge", "--abort")
    rc, out, last = mb(p, "worktree-agent-cm")
    check("... and following it lands the branch: MERGED",
          r.returncode == 0 and rc == 0
          and last.startswith("merge-back: MERGED worktree-agent-cm"), out)
    # The header's other half: a signal to the script alone waits for git,
    # so the commit lands. The hook holds until the signal has been sent.
    p = fixture()
    log = os.path.join(WORK, "cs.log")
    go = os.path.join(WORK, "cs.go")
    wt, tip = impl(p, "cs", {"src/feature.py": "def feature(): return 39\n"})
    hook = os.path.join(p, ".git/hooks/commit-msg")
    write(hook, "#!/bin/sh\necho ready >>" + shlex.quote(log) + "\n"
          "while [ ! -f " + shlex.quote(go) + " ]; do sleep 0.1; done\n")
    os.chmod(hook, 0o755)
    proc = start_mb(p, "worktree-agent-cs")
    ready = wait_for(lambda: "ready" in words_in(log), 60)
    proc.send_signal(signal.SIGTERM)
    time.sleep(0.3)
    write(go, "")
    out = rest_of(proc)
    check("a signal to the script alone inside that hook lets the commit "
          "finish: rc 5 CLEANUP MERGED, the worktree and the branch left "
          "for a rerun",
          ready and proc.returncode == 5
          and last_line(out).startswith("merge-back: CLEANUP MERGED "
                                        "worktree-agent-cs into main as ")
          and git(p, "rev-parse", "HEAD^2").stdout.strip() == tip
          and os.path.isdir(wt) and has_branch(p, "worktree-agent-cs"),
          f"rc={proc.returncode}\n{out[-1500:]}")
    _hdr = " ".join(open(mb_path(p)).read().split("\nGATES=", 1)[0]
                    .replace("#", " ").split())
    check("the header names when an interruption leaves the merge in "
          "progress (MBS-2, MBS-3), that a closed pipe does not cut the stop "
          "short (MBS-1), and what a SIGKILL leaves (MBS-4)",
          "The merge stays in progress, and the last line says so, after "
          "--continue, when a gate changed a file the merge brought in (git "
          "refuses to abort; the output lists the files, and the last line "
          "how to drop them), and when a Ctrl-C or a session's end "
          "interrupts the hooks git runs before it writes the merge commit "
          "(pre-commit, commit-msg; a signal to this script alone lets that "
          "commit finish)."
          in _hdr
          and "Further INT, TERM and HUP are ignored until the last line, "
          "and so is SIGPIPE: output piped to a reader that the same "
          "interruption ended (`2>&1 | tail`, `| tee`) does not cut the "
          "stop short." in _hdr
          and "it also leaves the running gate going (a process group of "
          "its own: kill -TERM -<its pgid>), and the lock directory (the "
          "next run takes it over) and two scratch files, "
          "bootstrap-merge-back.out.* and .in.*, in the git directory."
          in _hdr, _hdr[-2200:])
    # [WP3 fix4 CRIT3-1] Narrowed, not trapped: a reader that stops early
    # (`| head`) kills the run with SIGPIPE, so there is no last line then.
    check("the header no longer says the last line is always there: a reader "
          "that stops early leaves none and the merge in progress, "
          "--continue concludes it, and head is not to cut it (CRIT3-1)",
          "The last line of output is `merge-back: <STATUS> ...`, unless the "
          "reader stops early: piped to one that ends first, such as "
          "`| head`, merge-back dies of SIGPIPE at its next write, with no "
          "last line and, when that write falls between the merge and its "
          "commit, the merge in progress (the next run says so, and "
          "`.claude/merge-back.sh --continue <branch>` runs the gates again "
          "and concludes it). So "
          "do not cut its output with head: use `| tail`, or no pipe." in _hdr
          and "last line of output is always" not in _hdr, _hdr[:1500])

    print("\n== a locked worktree on git before 2.31 (CRIT-2) ==")
    # git 2.30 and older print no `locked` line in `git worktree list
    # --porcelain` (measured on 2.30.6). This shim strips it from git 2.31+.
    shim = tempfile.mkdtemp(prefix="git230-", dir=WORK)
    write(os.path.join(shim, "git"),
          "#!/bin/sh\n# git before 2.31: no `locked` line in the porcelain\n"
          "if [ \"$1\" = worktree ] && [ \"$2\" = list ]; then\n"
          "  " + shlex.quote(GIT) + " \"$@\" | grep -v '^locked'\n"
          "  exit 0\nfi\nexec " + shlex.quote(GIT) + " \"$@\"\n")
    os.chmod(os.path.join(shim, "git"), 0o755)
    old_git = {"PATH": shim + os.pathsep + AGENT_ENV.get("PATH", "")}
    p = fixture()
    wt, _ = impl(p, "lk", {"src/feature.py": "def feature(): return 34\n"})
    pre = head(p)
    git(p, "worktree", "lock", "--reason", "agent running", wt)
    r = run([os.path.join(shim, "git"), "worktree", "list", "--porcelain"], p)
    check("(precondition) under the shim, a locked worktree's porcelain has "
          "no locked line",
          r.returncode == 0 and os.path.realpath(wt) in r.stdout
          and "locked" not in r.stdout, r.stdout)
    rc, out, last = mb(p, "worktree-agent-lk", env=old_git)
    check("git before 2.31: rc 3 for a locked worktree, its reason named, "
          "nothing merged (the porcelain-only check merged it, then could "
          "not remove it)",
          rc == 3 and "is locked: agent running" in last
          and head(p) == pre and not merging(p), out)
    git(p, "worktree", "unlock", wt)
    git(p, "worktree", "lock", wt)
    rc, out, last = mb(p, "worktree-agent-lk", env=old_git)
    check("git before 2.31: rc 3 for a worktree locked with no reason",
          rc == 3 and "is locked: (no reason given)" in last
          and head(p) == pre and not merging(p), out)
    git(p, "worktree", "unlock", wt)
    rc, out, last = mb(p, "worktree-agent-lk", env=old_git)
    check("git before 2.31: once unlocked, it lands: MERGED",
          rc == 0 and last.startswith("merge-back: MERGED worktree-agent-lk"),
          out)

    print("\n== a git hook that rewrites a file (MB-5) ==")
    FIXER = ("#!/bin/sh\n# a fixer, as the pre-commit framework runs them\n"
             "fixed=\n"
             "for f in $(git diff --cached --name-only -- '*.py'); do\n"
             "  if grep -q ' $' \"$f\"; then\n"
             "    t=$(mktemp) && sed 's/  *$//' \"$f\" >\"$t\" "
             "&& cat \"$t\" >\"$f\" && rm -f \"$t\"\n"
             "    echo \"Fixing $f\"; fixed=1\n"
             "  fi\n"
             "done\n"
             "[ -z \"$fixed\" ]\n")
    for how in ("keep", "drop"):
        p = fixture()
        wt, tip = impl(p, f"fx{how}", {"src/feature.py":
                                       "def feature(): return 40  \n"})
        hook = os.path.join(p, ".git/hooks/pre-commit")
        write(hook, FIXER)
        os.chmod(hook, 0o755)
        pre = head(p)
        rc, out, last = mb(p, f"worktree-agent-fx{how}")
        mh = open(os.path.join(p, ".git/MERGE_HEAD")).read().strip() \
            if merging(p) else ""
        _flat = " ".join(out.split())
        check(f"({how}) a pre-commit fixer that rewrites a staged file and "
              f"exits 1: REFUSED rc 2, the merge kept (an abort is refused "
              f"and a rerun meets the same hook), the file named",
              rc == 2 and "Fixing src/feature.py" in out
              and "the merge is still in progress" in last
              and mh == tip and head(p) == pre
              and "    src/feature.py" in out
              and "could not be aborted" not in out, out)
        check(f"({how}) the remedy names both ways out: git add then "
              f"--continue, or git checkout then git merge --abort",
              "to keep those changes, git add the files, then run "
              f".claude/merge-back.sh --continue worktree-agent-fx{how}"
              in _flat and "To drop the merge instead: git checkout -- "
              ":/ (it discards every unstaged change, the files above "
              "included), then git merge --abort." in _flat, out)
        if how == "keep":
            git(p, "add", "src/feature.py")
            rc, out, last = mb(p, "--continue", f"worktree-agent-fx{how}")
            check("(keep) git add, then --continue: re-gated and MERGED, with "
                  "the hook's fix in the merge",
                  rc == 0 and last.startswith("merge-back: MERGED")
                  and "[test-gate] allowed (exit 0)" in out
                  and git(p, "show", "HEAD:src/feature.py").stdout
                  == "def feature(): return 40\n", out)
        else:
            rc, out, last = mb(p, f"worktree-agent-fx{how}")
            check("(drop) a rerun meanwhile names the unstaged file and the "
                  "two ways out, not a bare git merge --abort that git "
                  "refuses",
                  rc == 3 and "already in progress" in last
                  and "    src/feature.py" in out
                  and "To keep the changes above: git add them, then "
                  ".claude/merge-back.sh --continue worktree-agent-fxdrop"
                  in last and "To drop the merge: git restore "
                  "--ignore-unmerged --worktree -- :/ (it discards every "
                  "unstaged change, the files above included), then git "
                  "merge --abort" in last
                  and "refuses to discard" not in out, out)
            r = run(["sh", "-c", "git restore --ignore-unmerged --worktree "
                     "-- :/ && git merge --abort"], p)
            check("(drop) git restore, then git merge --abort: back to "
                  "where it started (R4-4)",
                  r.returncode == 0 and head(p) == pre and clean(p),
                  r.stdout + r.stderr)

    # A gate that changed a file the merge brought in, then refused: git
    # merge --abort refuses too ("not uptodate"), so the ERROR names the
    # file and the way out instead of "inspect git status".
    p = fixture()
    write(os.path.join(p, "tests/run.sh"),
          "#!/bin/sh\necho '# touched by the suite' >> src/feature.py\n"
          "echo 'FAIL: the suite refuses' >&2\nexit 1\n")
    git(p, "commit", "-qam", "a suite that writes a tracked file")
    impl(p, "gw", {"src/feature.py": "def feature(): return 42\n"})
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-gw")
    check("a refused merge whose gate changed a merged file: ERROR names the "
          "file and how to drop the merge, and git can carry it out",
          rc == 1 and "could not be aborted; the merge of worktree-agent-gw "
          "is still in progress. To drop it: git checkout -- :/ (it "
          "discards every unstaged change, the files above included), then "
          "git merge --abort" in last
          and "    src/feature.py" in out and "inspect git status" not in last,
          out)
    r = run(["sh", "-c", "git checkout -- :/ && git merge --abort"], p)
    check("... and following it restores the tree",
          r.returncode == 0 and head(p) == pre and clean(p),
          r.stdout + r.stderr)
    # [WP3 fix4 MB3-1] More than 20 such files: the list keeps 20 and says
    # how many more, and the printed way out covers every one (it named
    # "<the files above>", and following it left git refusing the abort).
    p = fixture(CFG_NO_SPEC)
    write(os.path.join(p, "tests/run.sh"),
          "#!/bin/sh\nfor f in src/gen/*.py; do echo '# regen' >> \"$f\"; "
          "done\necho 'FAIL: the suite refuses' >&2\nexit 1\n")
    git(p, "commit", "-qam", "a suite that rewrites 25 tracked files")
    impl(p, "gm", {f"src/gen/g{i:02d}.py": f"g = {i}\n" for i in range(25)})
    pre = head(p)
    rc, out, last = mb(p, "worktree-agent-gm")
    _shown = [ln for ln in out.splitlines()
              if ln.startswith("    src/gen/g")]
    check("a refused merge whose gate changed 25 merged files: 20 listed, "
          "'... and 5 more', and a way out that does not depend on the list "
          "(MB3-1)",
          rc == 1 and len(_shown) == 20 and "    ... and 5 more" in out
          and "To drop it: git checkout -- :/ (it discards every unstaged "
          "change, the files above included), then git merge --abort"
          in last, out)
    r = run(["sh", "-c", "git checkout -- :/ && git merge --abort"], p)
    check("... and following it restores the tree, all 25 files included "
          "(MB3-1)", r.returncode == 0 and head(p) == pre and clean(p),
          r.stdout + r.stderr)

    # [WP3 fix5 R4-4] A rerun while such a merge is in progress: its way out
    # named "<the files above>", which past 20 files is not every file, from
    # a project below the top names no file (the paths are from the top),
    # and on an unmerged path fails ("path is unmerged"); its header said
    # git merge --abort refuses them, false for an unmerged path.
    top, p = fixture_sub(CFG_NO_SPEC)
    write(os.path.join(p, "tests/run.sh"),
          "#!/bin/sh\nfor f in src/gen/*.py; do echo '# regen' >> \"$f\"; "
          "done\necho 'FAIL: the suite refuses' >&2\nexit 1\n")
    git(top, "commit", "-qam", "a suite that rewrites 25 tracked files")
    impl_sub(top, "gb", {f"src/gen/g{i:02d}.py": f"g = {i}\n"
                         for i in range(25)})
    pre = head(top)
    rc1, out1, last1 = mb(p, "worktree-agent-gb")
    rc, out, last = mb(p, "worktree-agent-gb")
    _shown = [ln for ln in out.splitlines()
              if ln.startswith("    pkg/svc/src/gen/g")]
    check("below the top, a rerun while a merge whose gate changed 25 merged "
          "files is in progress: NOT-STARTED, 20 listed and '... and 5 more', "
          "and a way out that does not depend on the list (R4-4)",
          rc1 == 1 and rc == 3 and "already in progress" in last
          and len(_shown) == 20 and "    ... and 5 more" in out
          and "To drop the merge: git restore --ignore-unmerged --worktree "
          "-- :/ (it discards every unstaged change, the files above "
          "included), then git merge --abort" in last, out1[-600:] + out)
    r = run(["sh", "-c", "git restore --ignore-unmerged --worktree -- :/ "
             "&& git merge --abort"], p)
    check("... and following it from the project directory restores the "
          "tree, all 25 files included, HEAD unmoved (R4-4)",
          r.returncode == 0 and head(top) == pre and clean(top),
          r.stdout + r.stderr)
    p = fixture()
    impl(p, "um", {"src/app.py": "def app(): return 3  # um\n"})
    write(os.path.join(p, "src/app.py"), "def app(): return 4  # main\n")
    git(p, "commit", "-qam", "main edits app")
    pre = head(p)
    rc1, _, _ = mb(p, "worktree-agent-um")
    rc, out, last = mb(p, "worktree-agent-um")
    check("a rerun without --continue after a CONFLICT (an unmerged path): "
          "NOT-STARTED, the file named, no claim that git merge --abort "
          "refuses it, and the restore way out (R4-4)",
          rc1 == 4 and rc == 3 and "already in progress" in last
          and "    src/app.py" in out and "refuses" not in out
          and "To drop the merge: git restore --ignore-unmerged --worktree "
          "-- :/ (it discards every unstaged change, the files above "
          "included), then git merge --abort" in last, out)
    r = run(["sh", "-c", "git restore --ignore-unmerged --worktree -- :/ "
             "&& git merge --abort"], p)
    check("... and following it restores the tree, HEAD unmoved (R4-4)",
          r.returncode == 0 and head(p) == pre and clean(p),
          r.stdout + r.stderr)

    print("\n== who fixes a refused resolution; the REFUSED lines (MB-6) ==")
    p = fixture()
    impl(p, "rv", {"src/app.py": "def app(): return 3  # rv\n"})
    write(os.path.join(p, "src/app.py"), "def app(): return 4  # main\n")
    git(p, "commit", "-qam", "main edits app")
    mb(p, "worktree-agent-rv")
    write(os.path.join(p, "src/app.py"), "x = 'BROKEN'\n")
    git(p, "add", "src/app.py")
    rc, out, last = mb(p, "--continue", "worktree-agent-rv")
    _flat = " ".join(out.split())
    check("--continue whose resolution fails the tests: the remedy sends it "
          "back to the integrator and tells the main session not to edit",
          rc == 2 and merging(p)
          and "Invoke the integrator again with this output, to correct its "
          "resolution and git add the files; do not edit them yourself."
          in _flat and "Invoke the integrator with this output (Remedy "
          "above), then .claude/merge-back.sh --continue worktree-agent-rv"
          in last and "Fix it" not in last, out)
    _ib = " ".join(P_ON[INTG]["body"].split())
    check("the integrator is routed for a refused --continue too, and its "
          "body says how to find a staged resolution",
          "and again when its --continue refuses that resolution"
          in INTEGRATOR_DESCRIPTION and ": " not in INTEGRATOR_DESCRIPTION
          and "If you are invoked again because `.claude/merge-back.sh "
          "--continue` refused your resolution, they are resolved and staged "
          "already" in _ib, _ib[:900])
    p = fixture()
    impl(p, "rf", {"src/feature.py": "x = 'BROKEN'\n"})
    rc, out, last = mb(p, "worktree-agent-rf")
    check("a fresh REFUSED line points at the Remedy above it",
          rc == 2 and last.endswith("is unchanged. Follow the Remedy above"),
          last)
    p = fixture()
    impl(p, "rh", {"src/feature.py": "def feature(): return 41\n"})
    hook = os.path.join(p, ".git/hooks/commit-msg")
    write(hook, "#!/bin/sh\necho 'commit-msg: no' >&2\nexit 1\n")
    os.chmod(hook, 0o755)
    rc, out, last = mb(p, "worktree-agent-rh")
    check("a git hook refusing a fresh merge commit: a Remedy says who acts",
          rc == 2 and "Remedy: a git hook of this repository" in out
          and "return the task to the implementer" in " ".join(out.split())
          and last.endswith("Follow the Remedy above"), out)

    print("\n== --continue when a git hook refuses the commit (TP-04) ==")
    p = fixture()
    impl(p, "ch", {"src/app.py": "def app(): return 3  # ch\n"})
    write(os.path.join(p, "src/app.py"), "def app(): return 4  # main\n")
    git(p, "commit", "-qam", "main edits app")
    tip = git(p, "rev-parse", "worktree-agent-ch").stdout.strip()
    rc1, _, _ = mb(p, "worktree-agent-ch")
    write(os.path.join(p, "src/app.py"), "def app(): return 34  # resolved\n")
    git(p, "add", "src/app.py")
    hook = os.path.join(p, ".git/hooks/commit-msg")
    write(hook, "#!/bin/sh\necho 'commit-msg: no' >&2\nexit 1\n")
    os.chmod(hook, 0o755)
    pre = head(p)
    rc, out, last = mb(p, "--continue", "worktree-agent-ch")
    mh = open(os.path.join(p, ".git/MERGE_HEAD")).read().strip() \
        if merging(p) else ""
    check("--continue refused by a commit-msg hook: rc 2, the merge still in "
          "progress (MERGE_HEAD = tip), the integrator's resolution still "
          "staged",
          rc1 == 4 and rc == 2 and "the merge is still in progress" in last
          and mh == tip and head(p) == pre
          and git(p, "show", ":src/app.py").stdout
          == "def app(): return 34  # resolved\n", out)

    print("\n== preconditions only the goldens pinned (TP-12) ==")
    p = fixture()
    wt, _ = impl(p, "pr", {"src/feature.py": "def feature(): return 50\n"})
    pre = head(p)
    git(p, "bisect", "start")
    rc, out, last = mb(p, "worktree-agent-pr")
    check("rc 3 while a bisect is in progress on the checked-out branch",
          rc == 3 and "(BISECT_LOG) is in progress" in last
          and head(p) == pre, out)
    git(p, "bisect", "reset")
    write(os.path.join(p, "bad.patch"),
          "From 0 Mon Sep 17 00:00:00 2001\nFrom: t <t@t>\nSubject: x\n\n"
          "---\ndiff --git a/nope.txt b/nope.txt\n--- a/nope.txt\n"
          "+++ b/nope.txt\n@@ -1 +1 @@\n-a\n+b\n")
    r = git(p, "am", "bad.patch")
    os.remove(os.path.join(p, "bad.patch"))
    rc, out, last = mb(p, "worktree-agent-pr")
    check("rc 3 while a stopped `git am` is in progress (rebase-apply)",
          r.returncode != 0 and rc == 3
          and "(rebase-apply) is in progress" in last and head(p) == pre, out)
    git(p, "am", "--abort")
    lock = os.path.join(p, ".git", "bootstrap-merge-back.lock")
    for label, pid_text in (("no pid file", None), ("an empty pid file", "")):
        os.makedirs(lock)
        if pid_text is not None:
            write(os.path.join(lock, "pid"), pid_text)
        rc, out, last = mb(p, "worktree-agent-pr")
        check(f"rc 3 for a lock directory with {label} (another run between "
              f"its mkdir and its pid write), never taken over",
              rc == 3 and "another merge-back holds" in last
              and os.path.isdir(lock) and head(p) == pre, out)
        shutil.rmtree(lock, ignore_errors=True)
    git(p, "worktree", "lock", wt)
    rc, out, last = mb(p, "worktree-agent-pr")
    check("rc 3 for a worktree locked with no reason",
          rc == 3 and "is locked: (no reason given)" in last
          and head(p) == pre, out)
    git(p, "worktree", "unlock", wt)
    rc, out, last = mb(p, "refs/heads/worktree-agent-pr")
    check("a full ref name (refs/heads/<branch>) is taken as the branch",
          rc == 0 and last.startswith("merge-back: MERGED worktree-agent-pr"),
          out)
    git(p, "branch", "worktree-agent-none")
    rc, out, last = mb(p, "worktree-agent-none")
    check("an implementer branch with no commits of its own and no "
          "worktree: ALREADY-MERGED, nothing was merged, and the note says "
          "where the commits may be",
          rc == 0 and "ALREADY-MERGED every commit on worktree-agent-none is "
          "already on main; nothing was merged" in last
          and "Note: If the implementer reported commits, they are on "
          "another branch" in out, out)

    print("\n== a stopped cherry-pick or revert in a reftable repository "
          "(CRIT5-1) ==")
    # [WP3 fix6 CRIT5-1] A reftable repository keeps CHERRY_PICK_HEAD and
    # REVERT_HEAD in its ref store, with no file at --git-path. A revert
    # stopped there (its resolution staged, so nothing reads as dirty) did
    # not refuse: the merge went ahead and its commit ended the revert.
    _rtp = tempfile.mkdtemp(prefix="rtprobe-", dir=WORK)
    if git(_rtp, "init", "-q", "--ref-format=reftable").returncode != 0:
        print("  SKIP  the reftable rows: this git cannot init "
              "--ref-format=reftable (git 2.45 or later)")
    else:
        RT = ("--ref-format=reftable",)

        def rt_stop(p, kind, multi=False):
            """Stop a revert (or cherry-pick) on main on conflicts, resolved
            to main's side and staged: the index matches HEAD."""
            write(os.path.join(p, "src/app.py"), "def app(): return 21\n")
            git(p, "commit", "-qam", "r1")
            write(os.path.join(p, "src/other.py"), "o = 1\n")
            git(p, "add", "src/other.py")
            git(p, "commit", "-qm", "other")
            write(os.path.join(p, "src/app.py"), "def app(): return 22\n")
            git(p, "commit", "-qam", "r2")
            if kind == "revert":
                r = git(p, "revert", "--no-edit",
                        *(("HEAD~2", "HEAD~1") if multi else ("HEAD~2",)))
            else:
                git(p, "branch", "pk", "HEAD~2")
                git(p, "reset", "-q", "--hard", "HEAD~1")
                write(os.path.join(p, "src/app.py"), "def app(): return 23\n")
                git(p, "commit", "-qam", "r3")
                r = git(p, "cherry-pick", "pk~0")
            git(p, "checkout", "--ours", "src/app.py")
            git(p, "add", "src/app.py")
            return r.returncode

        for kind, name, multi in (("revert", "REVERT_HEAD", False),
                                  ("revert", "REVERT_HEAD", True),
                                  ("cherry-pick", "CHERRY_PICK_HEAD", False)):
            p = fixture(init=RT)
            impl(p, "rt", {"src/feature.py": "def feature(): return 70\n"})
            src = rt_stop(p, kind, multi)
            pre = head(p)
            gp = git(p, "rev-parse", "--git-path", name).stdout.strip()
            fix = (src != 0 and git(p, "rev-parse", "--show-ref-format")
                   .stdout == "reftable\n"
                   and git(p, "show-ref", "--verify", "-q", name).returncode
                   == 0 and not os.path.exists(os.path.join(p, gp))
                   and git(p, "status", "--porcelain", "--untracked-files=no",
                           "--", ".", ":(exclude).claude/worktrees")
                   .stdout.strip() == ""
                   and (not multi or os.path.isdir(
                       os.path.join(p, ".git", "sequencer"))))
            rc, out, last = mb(p, "worktree-agent-rt")
            what = ("a multi-commit revert" if multi else f"a {kind}")
            check(f"reftable, {what} stopped on conflicts with its resolution "
                  f"staged ({name} a ref with no file, the index clean): rc 3 "
                  f"NOT-STARTED, it names {name}, nothing merged, and the "
                  f"{kind} is still in progress (CRIT5-1)",
                  fix and rc == 3
                  and f"a git operation ({name}) is in progress here" in last
                  and head(p) == pre and not merging(p)
                  and git(p, "show-ref", "--verify", "-q", name).returncode
                  == 0, (fix, rc, out))
        # Never by name lookup: a branch and a tag called REVERT_HEAD and
        # CHERRY_PICK_HEAD, with no stop, do not refuse the run.
        p = fixture(init=RT)
        impl(p, "rn", {"src/feature.py": "def feature(): return 71\n"})
        for name in ("REVERT_HEAD", "CHERRY_PICK_HEAD"):
            git(p, "branch", name)
            git(p, "tag", name)
        rc, out, last = mb(p, "worktree-agent-rn")
        check("reftable, a branch and a tag named REVERT_HEAD and "
              "CHERRY_PICK_HEAD with no stop: merged, not refused (CRIT5-1)",
              rc == 0 and last.startswith("merge-back: MERGED worktree-agent-rn"),
              out)
        # [WP3 fix7 CRIT6-1] By the backend, as git reads them: on reftable
        # a stray head file naming a commit is no operation to git (git
        # merge goes ahead, and git cherry-pick --abort or git revert
        # --abort fails, so "finish or abort it first" could not be
        # followed; measured, git 2.56). The run merges, as git would.
        for name, verb in (("CHERRY_PICK_HEAD", "cherry-pick"),
                           ("REVERT_HEAD", "revert")):
            p = fixture(init=RT)
            impl(p, "rs", {"src/feature.py": "def feature(): return 72\n"})
            write(os.path.join(p, ".git", name),
                  git(p, "rev-parse", "HEAD").stdout)
            ab = git(p, verb, "--abort")
            fix = (ab.returncode != 0 and os.path.isfile(
                os.path.join(p, ".git", name))
                and git(p, "show-ref", "--verify", "-q", name).returncode != 0)
            rc, out, last = mb(p, "worktree-agent-rs")
            check(f"reftable, a stray {name} file naming a commit (git sees no "
                  f"{verb}: git {verb} --abort fails): merged, not refused "
                  f"with a remedy that cannot be followed (CRIT6-1)",
                  fix and rc == 0
                  and last.startswith("merge-back: MERGED worktree-agent-rs"),
                  (fix, ab.stderr[-200:], rc, out))

    # [WP3 fix7 CRIT6-1] The files backend is unchanged: any head file
    # refuses, one git reads as a cherry-pick and one it does not.
    for what, body in (("naming a commit (git: a cherry-pick in progress)",
                        None), ("that names no object", "garbage\n")):
        p = fixture()
        impl(p, "fs", {"src/feature.py": "def feature(): return 73\n"})
        pre = head(p)
        write(os.path.join(p, ".git", "CHERRY_PICK_HEAD"),
              body if body is not None else git(p, "rev-parse", "HEAD").stdout)
        rc, out, last = mb(p, "worktree-agent-fs")
        check(f"files backend, a CHERRY_PICK_HEAD file {what}: rc 3, still "
              f"refused as before (CRIT6-1)",
              rc == 3 and "a git operation (CHERRY_PICK_HEAD) is in progress "
              "here" in last and head(p) == pre, out)

    print("\n== a run that outlives its Bash call (CR-1) ==")
    p = fixture()
    impl(p, "bg", {"src/feature.py": "def feature(): return 60\n"})
    rc, out, last = mb(p, "worktree-agent-bg")
    check("an agent's run says, before the gates, to wait for its last "
          "line in the same turn if it moves to the background",
          rc == 0 and "If your Bash call moves it to the background, wait "
          "for its last line (merge-back: ...) in this same turn, by reading "
          "its output file until that line is there: a session that ends "
          "stops it, and the merge is then aborted, except after --continue, "
          "when a gate changed a file the merge brought in, or when stopped "
          "in the hooks git runs before it writes the merge commit "
          "(pre-commit, commit-msg): the merge then stays in "
          "progress, and the last line says so." in out
          and out.index("If your Bash call") < out.index("[spec-check] on"),
          out)
    # [WP3 fix4 CRIT3-1] `| head` kills merge-back mid-run (SIGPIPE): no
    # last line, and the merge can stay in progress. The note comes first,
    # so a reader that stops early has read it.
    check("... and says not to cut its output with head (CRIT3-1)",
          "Do not cut this output with head: a reader that stops early ends "
          "this run with no last line and can leave the merge in progress "
          "(.claude/merge-back.sh --continue <branch> then concludes it); "
          "use | tail, or no pipe." in out, out)
    p = fixture()
    impl(p, "bh", {"src/feature.py": "def feature(): return 61\n"})
    rc, out, last = mb(p, "worktree-agent-bh", agent=False)
    check("a person's run does not carry the note", rc == 0
          and "If your Bash call" not in out, out)

    print("\n== the spec step, decision 2026-10-06 (1) ==")
    p = fixture()
    set_spec_mode(p, "block")
    shared_change(p, "sp")
    rc, out, last = mb(p, "worktree-agent-sp")
    _flat = " ".join(out.split())
    # [WP3 fix2 IT-4] merge-back marks its runs (BOOTSTRAP_MERGE_BACK=1):
    # the check then offers neither "commit again" nor "git merge --abort,
    # then stop and ask", and points at merge-back's Remedy.
    check("a spec refusal: the check's text defers to merge-back's Remedy "
          "(no git merge --abort, no 'commit again'), and the Remedy says "
          "the merge is aborted already (IT-4)",
          rc == 2 and "git merge --abort, then stop and ask" not in _flat
          and "commit again" not in _flat
          and "merge-back's Remedy, below, says who makes the fix and what "
          "runs next." in _flat
          and "Remedy: this merge is aborted already, so the check's advice "
          "on the merge in progress does not apply." in _flat
          and not merging(p), out)
    p = fixture()
    set_spec_mode(p, "warn")
    shared_change(p, "sw")
    rc, out, last = mb(p, "worktree-agent-sw")
    _flat = " ".join(out.split())
    check("warn: the merge goes ahead, and neither the gate's message nor "
          "the concluding commit's hook offers git merge --abort, which "
          "would then fail (IT-4)",
          rc == 0 and last.startswith("merge-back: MERGED")
          and _flat.count("This is a merge") == 2
          and "git merge --abort" not in _flat
          and "Fix the task file as above, or run" not in _flat, out)
    # [WP3 fix2 CRIT-1] An LC_ALL that names a locale that is not installed
    # made every bash start print a setlocale warning, which the `bash -n`
    # guard read as "does not parse": in block mode every merge-back,
    # a clean one of a listed file included, was REFUSED as could-not-run.
    _bad = {"LC_ALL": "xx_YY.UTF-8"}
    _probe = run([BASH, "-c", ":"], WORK, dict(BASE_ENV, **_bad))
    if "setlocale" in _probe.stderr:
        p = fixture()
        set_spec_mode(p, "block")
        impl(p, "lc", {"src/feature.py": "def feature(): return 71\n"})
        rc, out, last = mb(p, "worktree-agent-lc", env=_bad)
        # (The warning itself still reaches the output: bash prints it at
        # every start, merge-back's own included, which lands on stderr and
        # so after the last stdout line here.)
        check("block, LC_ALL names a locale that is not installed: a listed "
              "file merges, the spec check not refusing it as could-not-run "
              "(CRIT-1)",
              rc == 0 and "\nmerge-back: MERGED worktree-agent-lc" in out
              and "[spec-check] allowed" in out
              and "could not run" not in out and "does not parse" not in out,
              out)
    else:
        print("  SKIP  the uninstalled-locale row: this libc prints no "
              "setlocale warning")
    p = fixture()
    set_spec_mode(p, "block")
    impl(p, "sc", {"src/app.py": "def app(): return 3  # sc\n"})
    write(os.path.join(p, "src/app.py"), "def app(): return 4  # main\n")
    git(p, "commit", "-qam", "main edits app")
    mb(p, "worktree-agent-sc")
    write(os.path.join(p, "src/app.py"), "def app(): return 34\n")
    write(os.path.join(p, "src/extra.py"), "x = 1\n")
    git(p, "add", "src/app.py", "src/extra.py")
    rc, out, last = mb(p, "--continue", "worktree-agent-sc")
    _flat = " ".join(out.split())
    check("block, a --continue whose resolution adds an unlisted file: the "
          "relayed check text offers no 'commit again' and no git merge "
          "--abort (the integrator does neither) and defers to the Remedy, "
          "which sends it to the integrator (IT-4)",
          rc == 2 and merging(p) and "  src/extra.py" in out
          and "commit again" not in _flat and "git merge --abort, then stop "
          "and ask" not in _flat and "merge-back's Remedy, below, says who "
          "makes the fix" in _flat and "Invoke the integrator again with "
          "this output" in _flat, out)
    git(p, "merge", "--abort")

    print("\n== the test fixture keeps git's auto maintenance off (TP-02) ==")
    # git estimates its loose objects from objects/17/ alone; 3,000 of them
    # leave that directory empty with odds of about 1 in 100,000, so the
    # default config repacks here every time (measured, git 2.55).
    d = tempfile.mkdtemp(prefix="maint-", dir=WORK)
    git(d, "init", "-q", "-b", "main")
    for i in range(3000):
        write(os.path.join(d, f"f{i}"), f"{i}\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "over the loose-object threshold")
    packs = []
    deadline = time.time() + 5
    while time.time() < deadline and not packs:
        time.sleep(0.25)
        packs = [f for f in os.listdir(os.path.join(d, ".git/objects/pack"))
                 if f.endswith(".pack")]
    check("a commit over the loose-object threshold starts no repack under "
          "this suite's git config, so fixture() never copies a template "
          "that a detached repack is emptying", packs == [], str(packs))

# =========================================================================== #
print("\n== installer: worktree.baseRef is shared by sub-key ==")
# =========================================================================== #


def install(proj, cfg=CFG, *extra):
    cfgp = proj + ".yaml"
    write(cfgp, cfg)
    return run([sys.executable, BIN, "-c", cfgp, "-C", proj, *extra], proj)


def settings(proj):
    return json.load(open(os.path.join(proj, ".claude/settings.json")))


def manifest_row(proj):
    m = json.load(open(os.path.join(proj, ".claude/.installer-manifest.json")))
    return next(f for f in m["files"] if f["path"] == ".claude/settings.json")


d = tempfile.mkdtemp(dir=WORK)
r = install(d)
check("fresh install: worktree.baseRef is \"head\", recorded as ours",
      r.returncode == 0 and settings(d)["worktree"] == {"baseRef": "head"}
      and manifest_row(d).get("owned_worktree") == {"baseRef": "head"},
      r.stdout[-300:] + r.stderr)
r = install(d)
check("re-install: unchanged", r.returncode == 0
      and "ok   .claude/settings.json" in r.stdout)

for label, theirs, want_wt, want_warn in (
    ("an operator's other worktree sub-key is kept beside ours",
     {"worktree": {"symlinkDirectories": ["node_modules"]}},
     {"symlinkDirectories": ["node_modules"], "baseRef": "head"}, None),
    ("an operator's explicit \"fresh\" is kept, with a warning",
     {"worktree": {"baseRef": "fresh"}}, {"baseRef": "fresh"},
     "(yours, kept)"),
    # [WP3 critic 5e, operator ruling 2026-10-05] null warns; it is not
    # declined like the values below.
    ("a null is kept, with a warning that Claude Code reports it invalid",
     {"worktree": {"baseRef": None}}, {"baseRef": None},
     "sets worktree.baseRef to null, which Claude Code reports as an "
     "invalid value"),
):
    d = tempfile.mkdtemp(dir=WORK)
    write(os.path.join(d, ".claude/settings.json"),
          json.dumps(dict(theirs, model="sonnet"), indent=2) + "\n")
    r = install(d)
    s = settings(d)
    check(f"merge: {label}",
          r.returncode == 0 and s.get("worktree") == want_wt
          and s.get("model") == "sonnet"
          and ((want_warn is None and "worktree.baseRef" not in r.stderr)
               or (want_warn is not None and want_warn in r.stderr)),
          f"rc={r.returncode} wt={s.get('worktree')} stderr={r.stderr[-400:]}")
    r = install(d, CFG, "--uninstall")
    s2 = (json.load(open(os.path.join(d, ".claude/settings.json")))
          if os.path.exists(os.path.join(d, ".claude/settings.json")) else {})
    want_left = {k: v for k, v in want_wt.items()
                 if not (k == "baseRef" and v == "head")}
    check(f"uninstall after that: only our sub-key goes ({label})",
          s2.get("worktree", {}) == want_left and s2.get("model") == "sonnet",
          str(s2))

d = tempfile.mkdtemp(dir=WORK)
write(os.path.join(d, ".claude/settings.json"),
      json.dumps({"worktree": "head"}) + "\n")
r = install(d)
check("a non-object `worktree` is declined loudly, not coerced (rc 3)",
      r.returncode == 3 and "`worktree` key that is a str" in r.stdout
      + r.stderr, r.stdout[-300:] + r.stderr[-300:])
# [WP3 critic 5e, operator ruling 2026-10-05 (Q15)] A baseRef Claude Code
# rejects makes it ignore the whole settings.json (WP3 scout facts-cc
# C1-invalid), so the install is declined, rc 3, and the file is left as
# the operator wrote it.
for label, ref in (("an unknown string", "local"),
                   ("a wrong-case value", "HEAD"), ("a number", 5)):
    d = tempfile.mkdtemp(dir=WORK)
    _theirs = json.dumps({"worktree": {"baseRef": ref,
                                       "symlinkDirectories": ["x"]},
                          "model": "sonnet"}, indent=2) + "\n"
    write(os.path.join(d, ".claude/settings.json"), _theirs)
    r = install(d)
    _all = r.stdout + r.stderr
    check(f"an invalid baseRef ({label}) is declined (rc 3), the file "
          f"untouched, and the message says why and what to set",
          r.returncode == 3
          and open(os.path.join(d, ".claude/settings.json")).read() == _theirs
          and f"sets worktree.baseRef to {json.dumps(ref)}, which Claude "
          "Code rejects, and it then ignores the whole file" in _all
          and "set it to \"head\" or \"fresh\", or delete it" in _all
          and "security-critical files were NOT written" in r.stderr,
          _all[-600:])

d = tempfile.mkdtemp(dir=WORK)
install(d)
s = settings(d)
s["worktree"]["baseRef"] = "fresh"
s["model"] = "sonnet"             # an operator edit, so the file is merged
write(os.path.join(d, ".claude/settings.json"), json.dumps(s, indent=2))
r = install(d)
check("an operator who changes OUR value takes it over: kept on re-install",
      r.returncode == 0 and settings(d)["worktree"]["baseRef"] == "fresh"
      and manifest_row(d).get("owned_worktree") == {}, r.stderr)
os.remove(os.path.join(d, ".claude/.installer-manifest.json"))
r = install(d)
check("no manifest (a fresh clone): still kept, nothing duplicated",
      r.returncode == 0 and settings(d)["worktree"] == {"baseRef": "fresh"})

# =========================================================================== #
print("\n== records: the PRD notes say what the code does ==")
# =========================================================================== #
_prd = open(os.path.join(ROOT, "Bootstrap-Protocol-v2-8-0.md")).read()
check("PRD :1045 note: an invalid baseRef declines with exit 3, a null "
      "warns (critic 5e)",
      "makes Claude Code ignore the whole file, so the installer then leaves "
      "the file as it is and exits 3" in _prd
      and "a `null` is kept, with a warning (operator ruling 2026-10-05)"
      in _prd)
check("PRD implementer note: the main session owns status and the "
      "background case (critic 5a)",
      "or, with isolation off, once the reviewer approves; the implementer "
      "never changes it" in _prd
      and "they run from rollout week 3" in _prd)
# [WP3 fix1, f5-records] The note now says what CLAUDE.md says since fix
# round 1 (review CR-1, MB-3): done once the branch merged, and wait for
# the last line in the same turn, not "await the notification".
_cmf = " ".join(plan_of(CFG)["CLAUDE.md"]["body"].split())
check("PRD implementer note: done once the branch merged, and wait for the "
      "last line in the same turn, as the emitted CLAUDE.md says (review "
      "CR-1, MB-3)",
      "if the branch merged, set `status: done`" in _cmf
      and "wait for that line in this turn" in _cmf
      and "sets `done` once the branch merged (merge-back's MERGED, CLEANUP "
      "MERGED, or an ALREADY-MERGED that names the merge)" in _prd
      and "wait for its last line in the same turn and commit nothing "
      "meanwhile, because ending the turn can stop it" in _prd
      and "await the notification and commit nothing meanwhile" not in _prd)
check("PRD integrator note: a gate that could not run goes to the operator, "
      "and a refused --continue goes back to the integrator (review MB-2, "
      "MB-6)",
      "could not run the tests" in plan_of(CFG)[".claude/merge-back.sh"]["body"]
      and "Invoke the integrator again with this output"
      in plan_of(CFG)[".claude/merge-back.sh"]["body"]
      and "A test gate that could not run the tests (exit 127, or a hook that "
      "failed closed) goes to the operator." in _prd
      and "merge-back's remedy says to invoke the integrator again with its "
      "output, and the main session does not edit the files itself" in _prd)
check("PRD integrator note: a test failure is not routed to the integrator "
      "(critic 5b), and the Haiku floor is emitted (5d)",
      "never asks the integrator to start a merge" in _prd
      and "the emitted integrator carries the Haiku floor above as a note"
      in _prd)

shutil.rmtree(WORK, ignore_errors=True)
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

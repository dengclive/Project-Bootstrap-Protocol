#!/usr/bin/env python3
"""Phase 9 smoke stages 1 and 2, as a scripted dry run in a fixture.

PRD Phase 9 step 2 (stage 1) runs /spec-new -> /spec-review ->
/spec-decompose -> /plan-review; step 3 (stage 2) runs one task through the
implementer subagent -> reviewer subagent -> spec-validate. The build plan's
WP3 result is that both become runnable, and stage 2 reaches a merged commit.

A model run cannot be a unit test, and under `claude -p` the model cannot
write `.claude/specs/` at all (Claude Code treats it as a sensitive path;
WP3 scouts, measured on 2.1.289). So this script plays the model's part with
canned actions that do exactly what the emitted instructions say, and runs
every gate each action would trigger, on the paths and in the working tree
Claude Code would use (a worktree under .claude/worktrees/, the hook's cwd in
it, CLAUDE_PROJECT_DIR at the main checkout). A stage is runnable when every
row passes: the commands and agents exist and load, each body names the
artifact the next step reads, the prescribed path clears every gate, and the
forbidden path (source before test, a file no task lists) is refused.

Each row names the WP3 item that makes it pass. PENDING lists the rows whose
item has not landed in this tree; a pending row that fails is reported, not
counted. A pending row that PASSES fails the suite until it is removed from
PENDING, so the list can only shrink. WP3 is done when PENDING is empty.

[WP3 critic 4g] Stage-2 commits and the merge are the agent's, so they run
with CLAUDECODE=1, which is what makes the D2 git hook check them (a
person's commit is never checked). The fixture sets
hooks.spec_gate_commit_mode to block explicitly (critic 1m), so the
prescribed path is shown to clear the check and the forbidden path, a file
no task lists, is refused rather than warned about.

Run: python3 tests/test_smoke_stages.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
INSTALL = os.path.join(ROOT, "bin", "bootstrap-install")
GIT = shutil.which("git")
BASH = shutil.which("bash")

# Rows whose WP3 item is owned by another work item and not in this tree.
# Remove a row here in the change that lands its item.
PENDING = {}

passed = failed = pending = 0
pending_seen = {}


def row(rid, name, cond, detail=""):
    global passed, failed, pending
    tag = f"{rid} {name}"
    if rid in PENDING:
        if cond:
            failed += 1
            print(f"  FAIL  {tag}  (passes now: remove {rid} from PENDING)")
        else:
            pending += 1
            pending_seen[rid] = PENDING[rid]
            print(f"  PEND  {tag}  [{PENDING[rid]}]")
        return
    if cond:
        passed += 1
        print(f"  PASS  {tag}")
    else:
        failed += 1
        print(f"  FAIL  {tag}")
        if detail:
            print(f"        {detail}")


if not (GIT and BASH):
    print("git or bash missing; smoke dry run cannot run")
    print("\n0 passed, 0 failed")
    sys.exit(0)

CONFIG = """project:
  name: "smoke"
  archetype: "cli"
  shell: "bash"
principles:
  tdd_policy: required
secrets:
  enabled: false
deps:
  enabled: false
commands:
  test: "python3 -m unittest discover -s tests -t ."
  lint: "true"
  format: "true"
  ci_local: "true"
hooks:
  spec_gate_commit_mode: block
"""

TMP = tempfile.mkdtemp(prefix="smoke-stages-")
PROJ = os.path.join(TMP, "proj")
os.makedirs(PROJ)
ENV = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
# [WP3 fix1 TP-03] No developer git config reaches the rows: a global
# core.hooksPath (a hook manager) or commit.gpgsign turned this suite red.
# GIT_CONFIG_GLOBAL (git 2.32+) names an empty file.
_GCFG = os.path.join(TMP, "gitconfig-global")
open(_GCFG, "w").close()
ENV.update(GIT_CONFIG_GLOBAL=_GCFG, GIT_CONFIG_NOSYSTEM="1",
           XDG_CONFIG_HOME=os.path.join(TMP, "xdg"))
# [critic 4g] An agent's git commands: Claude Code sets CLAUDECODE=1 in its
# Bash tool, in subagents and under `claude -p`.
AENV = dict(ENV, CLAUDECODE="1")
LOG = os.path.join(PROJ, ".claude", "logs", "hooks.log")


def log_lines():
    return open(LOG).read().splitlines() if os.path.isfile(LOG) else []


def git(*a, cwd=PROJ, env=None):
    return subprocess.run([GIT, "-c", "user.email=s@s", "-c", "user.name=s",
                           *a], cwd=cwd, capture_output=True, text=True,
                          env=env or ENV)


def hook(name, payload, cwd=PROJ):
    """An emitted shell hook, as Claude Code runs it: payload on stdin,
    cwd = the session's directory, CLAUDE_PROJECT_DIR = the main checkout."""
    env = dict(ENV, CLAUDE_PROJECT_DIR=PROJ)
    p = subprocess.run([BASH, os.path.join(PROJ, ".claude/hooks", name)],
                       input=json.dumps(payload), capture_output=True,
                       text=True, cwd=cwd, env=env)
    return p.returncode, p.stdout, p.stderr


def speccheck(cwd=PROJ):
    """[critic r3] D2's check of record: spec-check.sh on the staged set,
    with the spec's task files staged (it reads task files from the index)."""
    git("add", "-f", "--", f".claude/specs/{SLUG}")
    p = subprocess.run([BASH, os.path.join(PROJ, ".claude/githooks/spec-check.sh"),
                        "--staged"], capture_output=True, text=True, cwd=cwd,
                       env=dict(ENV))
    return p.returncode, p.stdout, p.stderr


def bash_payload(cmd):
    return {"tool_name": "Bash", "hook_event_name": "PreToolUse",
            "tool_input": {"command": cmd}}


def write_payload(path):
    return {"tool_name": "Write", "hook_event_name": "PreToolUse",
            "tool_input": {"file_path": path, "content": "x"}}


def put(base, rel, text):
    p = os.path.join(base, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        fh.write(text)


def read(rel, base=PROJ):
    p = os.path.join(base, rel)
    return open(p).read() if os.path.isfile(p) else ""


def body_after_frontmatter(text):
    if not text.startswith("---\n"):
        return text
    return text[text.index("\n---", 4) + 4:]


def frontmatter_ok(text):
    if not text.startswith("---\n"):
        return False
    fm = text[4:text.index("\n---", 4)]
    try:
        import yaml
    except ImportError:
        return all(": " not in ln.split(": ", 1)[1]
                   for ln in fm.splitlines() if ": " in ln
                   and not ln.split(": ", 1)[1].startswith(("'", '"')))
    try:
        return isinstance(yaml.safe_load(fm), dict)
    except yaml.YAMLError:
        return False


git("init", "-q", "-b", "main")
# A Python project ignores its bytecode. Without this line the test-gate's
# own run leaves src/__pycache__/ untracked in the worktree, and
# `git worktree remove` then refuses without --force (measured; see S2-15).
put(PROJ, ".gitignore", "__pycache__/\n")
cfgp = os.path.join(TMP, "config.yaml")
with open(cfgp, "w") as fh:
    fh.write(CONFIG)
r = subprocess.run([sys.executable, INSTALL, "-c", cfgp, "-C", PROJ],
                   capture_output=True, text=True, env=ENV)
if r.returncode != 0:
    print("installer failed; cannot run the smoke dry run")
    print(r.stdout[-1500:], r.stderr[-1500:])
    sys.exit(1)

# --------------------------------------------------------------------------- #
# Stage 1: /spec-new -> /spec-review -> /spec-decompose -> /plan-review
# --------------------------------------------------------------------------- #
print("\n== stage 1 (PRD Phase 9 step 2) ==")
STAGE1 = ("spec-new", "spec-review", "spec-decompose", "plan-review")
row("S1-01", "the four stage-1 commands exist and invoke their skills",
    all(f"Invoke the `{n}` skill." in read(f".claude/commands/{n}.md")
        and read(f".claude/skills/{n}/SKILL.md") for n in STAGE1))
STAGE_FILES = ([f".claude/skills/{n}/SKILL.md" for n in STAGE1
                + ("spec-validate", "decision-log", "test-author")]
               + [f".claude/commands/{n}.md" for n in STAGE1
                  + ("spec-validate",)]
               + [".claude/agents/implementer.md",
                  ".claude/agents/reviewer.md"])
_bad = [f for f in STAGE_FILES if not frontmatter_ok(read(f))]
row("S1-02", "every stage-1/2 skill, command and agent has valid YAML "
    "frontmatter", not _bad, repr(_bad))
_new = body_after_frontmatter(read(".claude/skills/spec-new/SKILL.md"))
row("S1-03", "spec-new names requirements.md, decisions.md and changelog.md "
    "under .claude/specs/<slug>/",
    all(x in _new for x in (".claude/specs/<slug>/requirements.md",
                            "decisions.md", "changelog.md")))
row("S1-04", "spec-new writes a version: field", "version:" in _new)
_dec = body_after_frontmatter(read(".claude/skills/spec-decompose/SKILL.md"))
row("S1-05", "spec-decompose writes .claude/specs/<slug>/tasks/<id>.md with "
    "a Files: list", ".claude/specs/<slug>/tasks/" in _dec and "Files:"
    in _dec)


def real_body(name):
    """The skill's instruction lines, or [] when the body is only its own
    one-line description (the 3d866f4 stub: _SKILL_BODIES falls back to the
    description). Headings, blank lines and the `> Recommended` line are
    not instructions."""
    text = read(f".claude/skills/{name}/SKILL.md")
    m = re.search(r"^description: (.*)$", text, re.M)
    desc = m.group(1).strip() if m else ""
    lines = [ln.strip() for ln in body_after_frontmatter(text).splitlines()
             if ln.strip() and not ln.lstrip().startswith(("#", ">"))]
    return [] if lines in ([], [desc]) else lines


row("S1-06", "spec-review and plan-review have real bodies",
    bool(real_body("spec-review")) and bool(real_body("plan-review")))
_idx = read(".claude/specs/INDEX.md").lower()
row("S1-07", "INDEX.md carries in-flight, blocked and last-checkpoint "
    "columns", all(x in _idx for x in ("in-flight", "blocked",
                                       "checkpoint")))

# Before any spec exists, an implementation prompt gets the entry notice.
rc, out, _ = hook("spec-gate-entry.sh",
                  {"hook_event_name": "UserPromptSubmit",
                   "prompt": "Implement the greet feature"})
# [critic 4a] The whole chain, lifecycle gates 1 and 2 included, in order.
_chain = ("/spec-new", "/spec-review", "/spec-decompose", "/plan-review")
row("S1-08", "with no spec, the entry notice names /spec-new -> "
    "/spec-review -> /spec-decompose -> /plan-review", rc == 0
    and all(c in out for c in _chain)
    and [out.index(c) for c in _chain] == sorted(out.index(c)
                                                for c in _chain), out[:300])

# The canned stage-1 artifacts, in the shape the skill bodies prescribe.
SLUG = "greet"
put(PROJ, f".claude/specs/{SLUG}/requirements.md",
    "---\nversion: 1.0.0\n---\n# greet\n\n## Acceptance criteria\n\n"
    "- AC-1: When greet(name) is called, the system shall return "
    "'hello <name>'.\n")
put(PROJ, f".claude/specs/{SLUG}/decisions.md", "# Decisions: greet\n")
put(PROJ, f".claude/specs/{SLUG}/changelog.md",
    "# Changelog: greet\n\n- 1.0.0 (2026-10-04): initial spec.\n")
TASK = f".claude/specs/{SLUG}/tasks/T1.md"
# status in-progress: the main session sets it, and commits it with the
# spec, before it dispatches the implementer (critic contract item 7).
put(PROJ, TASK, "---\nid: T1\nspec_version: 1.0.0\nstatus: in-progress\n"
    "---\n# T1: greet\n\n"
    "Acceptance: AC-1.\n\nFiles:\n- src/greet.py\n- src/__init__.py\n"
    "- tests/test_greet.py\n- tests/__init__.py\n")
rc, out, _ = hook("spec-gate-entry.sh",
                  {"hook_event_name": "UserPromptSubmit",
                   "prompt": "Implement the greet feature"})
row("S1-09", "once a spec exists, the entry notice stays quiet",
    rc == 0 and out.strip() == "", out[:200])

# The commit gate reads the task file: a listed file passes, an unlisted
# one is refused (the two-call form the PreToolUse hook can see).
put(PROJ, "src/unlisted.py", "x = 1\n")
git("add", "src/unlisted.py")
rc_un, _, err_un = speccheck()
git("rm", "-q", "--cached", "src/unlisted.py")
os.remove(os.path.join(PROJ, "src/unlisted.py"))
put(PROJ, "src/greet.py", "")
git("add", "src/greet.py")
rc_ls, _, _ = speccheck()
git("rm", "-q", "--cached", "src/greet.py")
os.remove(os.path.join(PROJ, "src/greet.py"))
row("S1-10a", "commit gate: a file the task lists passes, an unlisted one is "
    "refused", rc_ls == 0 and rc_un == 2, f"listed={rc_ls} unlisted={rc_un} "
    f"{err_un[:160]}")
# D2: a directory entry covers the files under it.
put(PROJ, f".claude/specs/{SLUG}/tasks/T9.md", "Files:\n- src/qzdir/\n")
put(PROJ, "src/qzdir/a.py", "x = 1\n")
git("add", "src/qzdir/a.py")
rc_dir, _, _ = speccheck()
git("rm", "-q", "--cached", "src/qzdir/a.py", f".claude/specs/{SLUG}/tasks/T9.md")
shutil.rmtree(os.path.join(PROJ, "src/qzdir"))
os.remove(os.path.join(PROJ, f".claude/specs/{SLUG}/tasks/T9.md"))
row("S1-10", "commit gate: a directory entry covers the files under it",
    rc_dir == 0, f"rc={rc_dir}")
row("S1-11", "a git pre-commit hook is installed",
    os.path.isfile(os.path.join(PROJ, ".git/hooks/pre-commit")))

# [WP3 fix 8] The agent's spec-only commit passes test-gate before tests/
# exists. The configured `python3 -m unittest discover -s tests -t .` exits
# 1 on the missing start directory, and test-gate refused this commit in
# the interactive smoke demo (2026-10-13).
rc_sp, out_sp, err_sp = hook("test-gate.sh", bash_payload("git commit -m spec"))
row("S1-12a", "test-gate allows the spec-only commit before tests/ exists, "
    "with a notice", not os.path.exists(os.path.join(PROJ, "tests"))
    and rc_sp == 0 and "start directory" in out_sp, f"rc={rc_sp} "
    f"{out_sp[:120]} {err_sp[-200:]}")

# The operator commits the harness and the spec (Phase 10 step 4, item 1).
git("add", "-A")
r = git("commit", "-qm", "harness + greet spec")
row("S1-12", "harness and spec commit on main", r.returncode == 0, r.stderr)

# --------------------------------------------------------------------------- #
# Stage 2: implementer -> reviewer -> spec-validate, to a merged commit
# --------------------------------------------------------------------------- #
print("\n== stage 2 (PRD Phase 9 step 3) ==")
settings = json.loads(read(".claude/settings.json"))
row("S2-01", "settings.json starts worktrees from the local branch",
    (settings.get("worktree") or {}).get("baseRef") == "head",
    repr(settings.get("worktree")))
row("S2-02", ".claude/.gitignore ignores .claude/worktrees/",
    git("check-ignore", "-q", ".claude/worktrees/agent-x/f").returncode == 0)

impl = read(".claude/agents/implementer.md")
row("S2-03", "the implementer runs in its own worktree and is told tests "
    "first (TDD required)", "\nisolation: worktree\n" in impl
    and "## Tests first (TDD policy: required)" in impl
    and "never commit the failing step" in impl)

# Claude Code's layout for an isolation:worktree subagent, from local HEAD
# (what worktree.baseRef "head" gives; measured on 2.1.289).
BR = "worktree-agent-smoke"
WT = os.path.join(PROJ, ".claude", "worktrees", "agent-smoke")
r = git("worktree", "add", "-q", "-b", BR, WT, "HEAD")
row("S2-04", "the worktree starts with the task file in it",
    r.returncode == 0 and os.path.isfile(os.path.join(WT, TASK)), r.stderr)

W = lambda rel: os.path.join(WT, rel)                               # noqa
rc1, _, e1 = hook("tdd-gate.sh", write_payload(W("src/greet.py")), cwd=WT)
rc2, _, _ = hook("tdd-gate.sh", write_payload(W("tests/test_greet.py")),
                 cwd=WT)
put(WT, "tests/__init__.py", "")
put(WT, "tests/test_greet.py",
    "import unittest\nfrom src.greet import greet\n\n\n"
    "class T(unittest.TestCase):\n    def test_ac1(self):\n"
    "        self.assertEqual(greet('a'), 'hello a')\n")
rc3, _, _ = hook("tdd-gate.sh", write_payload(W("src/greet.py")), cwd=WT)
row("S2-05", "in the worktree: source before its test is refused, the test "
    "and then the source are allowed", (rc1, rc2, rc3) == (2, 0, 0),
    f"{(rc1, rc2, rc3)} {e1[:120]}")

put(WT, "src/__init__.py", "")
git("add", "tests/__init__.py", "tests/test_greet.py", "src/__init__.py",
    cwd=WT)
rc_red, _, _ = hook("test-gate.sh", bash_payload("git commit -m red"), cwd=WT)
put(WT, "src/greet.py", "def greet(n):\n    return 'hello ' + n\n")
git("add", "src/greet.py", cwd=WT)
rc_green, _, _ = hook("test-gate.sh", bash_payload("git commit -m green"),
                      cwd=WT)
row("S2-06", "test-gate refuses the red commit and allows test + source "
    "once green", (rc_red, rc_green) == (2, 0), f"{(rc_red, rc_green)}")
rc_sg, _, e_sg = hook("spec-gate-commit.sh", bash_payload("git commit -m g"),
                      cwd=WT)
row("S2-07", "commit gate allows the files the task lists", rc_sg == 0,
    e_sg[:200])
# [critic 4g] The agent's commit runs the D2 git hook. First the forbidden
# path: a file no task lists is refused, and the refusal names the task in
# progress. Then it is unstaged and removed, and the prescribed commit goes.
put(WT, "src/stray.py", "x = 1\n")
git("add", "src/stray.py", cwd=WT)
r = git("commit", "-qm", "stray", cwd=WT, env=AENV)
row("S2-08a", "the agent's commit of a file no task lists is refused by the "
    "git hook, naming the task in progress", r.returncode != 0
    and "src/stray.py" in r.stderr and TASK in r.stderr, r.stderr[:300])
git("rm", "-q", "--cached", "src/stray.py", cwd=WT)
os.remove(os.path.join(WT, "src/stray.py"))
_n0 = len(log_lines())
r = git("commit", "-qm", "T1: greet (AC-1)", cwd=WT, env=AENV)
row("S2-08", "the implementer's commit passes the git hook and lands on its "
    "branch only", r.returncode == 0
    and "git-hook pre-commit: pass" in "\n".join(log_lines()[_n0:])
    and git("rev-parse", BR).stdout != git("rev-parse", "main").stdout,
    r.stderr)
row("S2-09", "the main checkout stays clean beside the worktree",
    git("status", "--porcelain").stdout.strip() == "",
    git("status", "--porcelain").stdout)

rev = read(".claude/agents/reviewer.md")
row("S2-10", "the reviewer names its inputs, the branch range and its "
    "answer shape", "git diff HEAD...<branch>" in rev
    and ".claude/specs/<slug>/tasks/<id>.md" in rev
    and "VERDICT: approve | issues | blocked" in rev)
# The range the reviewer is told to read covers exactly the task's files.
# [critic files contract] spec-check.sh is the one parser: every file in
# the range is covered by THIS task (--task), and the range holds the
# source the task names.
names = sorted(git("diff", "--name-only", f"HEAD...{BR}").stdout.split())
p = subprocess.run([BASH, os.path.join(PROJ, ".claude/githooks/spec-check.sh"),
                    "--task", TASK, "--files", *names], capture_output=True,
                   text=True, cwd=PROJ, env=dict(ENV))
row("S2-11", "the reviewer's range is the files the task lists (spec-check "
    "--task)", p.returncode == 0 and "src/greet.py" in names,
    f"rc={p.returncode} diff={names} {p.stderr[:200]}")
_val = "\n".join(real_body("spec-validate"))
row("S2-12", "spec-validate reads requirements.md and records the version it "
    "validated", "requirements.md" in _val and "version" in _val
    and "record" in _val.lower())
_mb = [p for p in (".claude/merge-back.sh", ".claude/scripts/merge-back.sh",
                   ".claude/hooks/merge-back.sh")
       if os.path.isfile(os.path.join(PROJ, p))]
row("S2-13", "a merge-back script is emitted", bool(_mb))
row("S2-14", "a git pre-merge-commit hook is installed",
    os.path.isfile(os.path.join(PROJ, ".git/hooks/pre-merge-commit")))
# [WP3 critic 5i] The main session lands the approved branch through the
# emitted merge-back.sh, as CLAUDE.md tells it to, as an agent (the D2 check
# applies): --no-ff --no-commit, the gates on the merged result, then the
# commit, whose pre-commit hook checks the merge again, then the worktree
# and its branch removed.
_n0 = len(log_lines())
tip = git("rev-parse", BR).stdout.strip()
r = subprocess.run([os.path.join(PROJ, ".claude/merge-back.sh"), BR],
                   cwd=PROJ, capture_output=True, text=True,
                   env=dict(AENV, GIT_AUTHOR_NAME="s", GIT_AUTHOR_EMAIL="s@s",
                            GIT_COMMITTER_NAME="s",
                            GIT_COMMITTER_EMAIL="s@s"), timeout=300)
_out = r.stdout + r.stderr
_last = _out.rstrip("\n").splitlines()[-1] if _out.strip() else ""
_new = "\n".join(log_lines()[_n0:])
row("S2-15", "merge-back.sh lands the branch: MERGED with --no-ff, the gates "
    "run on the merged result, the worktree and branch removed",
    r.returncode == 0 and _last.startswith(f"merge-back: MERGED {BR}")
    and git("rev-parse", "HEAD^2").stdout.strip() == tip
    and "[spec-check] passed" in _out and "[test-gate] allowed" in _out
    and "git-hook pre-commit: pass" in _new
    and f"merge-back MERGED {BR}" in _new
    and not os.path.exists(WT)
    and git("rev-parse", "--verify", "--quiet", f"refs/heads/{BR}").returncode
    != 0 and os.path.isfile(os.path.join(PROJ, "src/greet.py")),
    f"rc={r.returncode}\n{_out[-1500:]}")
# D6: "D2's hook backs up hand merges". An agent's hand-typed merge goes
# through the pre-merge-commit hook. [WP3 fix1, operator decision
# 2026-10-06 (1)] The hook checks the merge's OWN changes; a file only the
# branch changed is not checked again (an agent's commit was checked when it
# was made, a person's never is: re-review RR-1). [WP3 fix2
# MR-1] Judged against git's automatic merge result: here both sides change
# the same line, and `-X theirs` resolves that conflict without stopping,
# so pre-merge-commit sees the agent's resolution.
put(PROJ, "src/stray2.py", "1\n2\n3\n4\n5\n")
git("add", "src/stray2.py")
git("commit", "-qm", "stray base")                  # a person's commit
BR2 = "worktree-agent-hand"
WT2 = os.path.join(PROJ, ".claude", "worktrees", "agent-hand")
git("worktree", "add", "-q", "-b", BR2, WT2, "HEAD")
put(WT2, "src/stray2.py", "1\n2\n3\n4\n50\n")
put(WT2, "src/only-branch.py", "b = 1\n")
git("add", "src/stray2.py", "src/only-branch.py", cwd=WT2)
git("commit", "-qm", "stray", cwd=WT2)              # a person's commit
put(PROJ, "src/stray2.py", "1\n2\n3\n4\n500\n")
git("commit", "-qam", "stray on main")              # a person's commit
_n0 = len(log_lines())
_pre = git("rev-parse", "HEAD").stdout
r = git("merge", "--no-ff", "-q", "-X", "theirs", "-m", f"Merge {BR2}", BR2,
        env=AENV)
row("S2-16", "an agent's hand-typed merge goes through the pre-merge-commit "
    "hook, which refuses the merge's own unlisted change (a conflict `-X "
    "theirs` resolved) and not the branch's own file",
    r.returncode != 0 and "src/stray2.py" in r.stderr
    and "src/only-branch.py" not in r.stderr
    and "git-hook pre-merge-commit: refused" in "\n".join(log_lines()[_n0:])
    and git("rev-parse", "HEAD").stdout == _pre, r.stderr[:400])
git("merge", "--abort")

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{passed} passed, {failed} failed, {pending} pending")
if pending_seen:
    print("Pending WP3 items (rows that cannot pass in this tree yet):")
    for rid, why in sorted(pending_seen.items()):
        print(f"  {rid}: {why}")
sys.exit(1 if failed else 0)

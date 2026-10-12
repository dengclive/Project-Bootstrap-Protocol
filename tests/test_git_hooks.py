#!/usr/bin/env python3
"""[WP3 / D2] Installer-managed git hooks for the spec check.

The installer writes a shim into the repository's hooks directory as
pre-commit and pre-merge-commit. The shim runs .claude/githooks/dispatch
(a plan action) for agent commits (CLAUDECODE=1) only; dispatch runs the
spec check and maps its exit status to git's. Every row below drives real
git in a temporary repository: a golden digest says the bytes moved, not
that a commit is allowed or refused.

Run: python3 tests/test_git_hooks.py
"""
import atexit
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

from defaults import DEFAULTS, resolve_config            # noqa: E402
from installer import build_plan                         # noqa: E402
from minyaml import load_yaml                            # noqa: E402
from templates import (GIT_HOOK_DISPATCH, GIT_HOOK_MARKER,  # noqa: E402
                       MERGE_BACK_SCRIPT, SPEC_CHECK_END, SPEC_CHECK_PATH,
                       TEMPLATES)


BIN = os.path.join(ROOT, "bin", "bootstrap-install")
GIT = shutil.which("git")

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


CFG_BASE = """project:
  name: githooks
  archetype: cli
secrets:
  enabled: false
deps:
  enabled: false
commands:
  test: "true"
  lint: "true"
  format: "true"
"""
# [WP3 critic 1m] The mode is set, never inherited from DEFAULTS: only the
# "the mode WP3 ships" row reads the default.
CFG = CFG_BASE + "hooks:\n  spec_gate_commit_mode: warn\n"
CFG_BLOCK = CFG_BASE + "hooks:\n  spec_gate_commit_mode: block\n"
CFG_OFF = CFG_BASE + "hooks:\n  spec_gate_commit: false\n"

# A clean environment: no inherited CLAUDECODE, no GIT_* location
# variables (the suite may itself run inside a git hook), and a fixed
# identity so commits never prompt. [WP3 critic 1j] And hermetic: git never
# searches above the temp directory, so a TMPDIR inside some work tree (a
# dotfiles repository in $HOME) cannot turn the "no repository" rows into
# "a project below the repository top".
CEILING = tempfile.gettempdir()
# [WP3 fix1 TP-03] No developer git config reaches the rows: a global
# core.hooksPath (a hook manager) made this suite crash, and
# commit.gpgsign made every commit fail. GIT_CONFIG_GLOBAL (git 2.32+)
# names an empty file; HOME and XDG_CONFIG_HOME cover older git.
# [WP3 fix5 CI-4] Every temporary root this suite makes is removed when it
# exits: it left about 58 directories (107 MB) in TMPDIR after each run.
_ROOTS = []
atexit.register(lambda: [shutil.rmtree(d, ignore_errors=True)
                         for d in _ROOTS])
_HOME = tempfile.mkdtemp()
_ROOTS.append(_HOME)
_GCFG = os.path.join(_HOME, "gitconfig-global")
open(_GCFG, "w").close()
BASE_ENV = {k: v for k, v in os.environ.items()
            if k != "CLAUDECODE" and not k.startswith("GIT_")}
BASE_ENV.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
                GIT_CONFIG_NOSYSTEM="1", HOME=_HOME,
                XDG_CONFIG_HOME=os.path.join(_HOME, "xdg"),
                GIT_CONFIG_GLOBAL=_GCFG,
                GIT_CEILING_DIRECTORIES=CEILING)
AGENT_ENV = dict(BASE_ENV, CLAUDECODE="1")


def run(cmd, cwd, env=None, stdin=None):
    return subprocess.run(cmd, cwd=cwd, env=env or BASE_ENV, input=stdin,
                          capture_output=True, text=True, timeout=120)


def git(cwd, *args, agent=False):
    return run([GIT, *args], cwd, AGENT_ENV if agent else BASE_ENV)


def install(proj, cfg=CFG, *extra):
    cfgp = os.path.join(proj, "..", os.path.basename(proj) + ".yaml")
    with open(cfgp, "w") as fh:
        fh.write(cfg)
    return run([sys.executable, BIN, "-c", os.path.abspath(cfgp), "-C", proj,
                *extra], proj)


def new_repo(git_init=True):
    base = tempfile.mkdtemp()
    _ROOTS.append(base)
    proj = os.path.join(base, "proj")
    os.mkdir(proj)
    if git_init:
        git(proj, "init", "-q", "-b", "main")
    return proj


def head(proj):
    return git(proj, "rev-parse", "HEAD").stdout.strip()


def hook_path(proj, name):
    return os.path.join(proj, ".git", "hooks", name)


def read(p):
    try:
        with open(p) as fh:
            return fh.read()
    except OSError:
        return None


def commit_file(proj, rel, agent=True, msg=None):
    """`git add X && git commit` in ONE shell, the form the PreToolUse gate
    misses. Returns the CompletedProcess."""
    path = os.path.join(proj, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(rel + "\n")
    return run(["sh", "-c", f"git add -- '{rel}' && git commit -q -m "
                f"'{msg or rel}'"], proj, AGENT_ENV if agent else BASE_ENV)


def harness_commit(proj):
    git(proj, "add", "-A")
    return git(proj, "commit", "-q", "-m", "harness")


def set_mode(proj, mode):
    p = os.path.join(proj, GIT_HOOK_DISPATCH)
    body = read(p)
    with open(p, "w") as fh:
        fh.write(re.sub(r"^MODE=\S+", f"MODE={mode}", body, count=1,
                        flags=re.M))


def manifest_rows(proj):
    m = json.load(open(os.path.join(proj, ".claude",
                                    ".installer-manifest.json")))
    return [f for f in m["files"] if f.get("kind") == "git_hook"]


SHIM = TEMPLATES["git_hook_shim"](resolve_config(load_yaml(CFG))[0])
WARN = ("spec check (pre-commit): hooks.spec_gate_commit_mode is warn, so "
        "the commit went through.")
REFUSED = "spec check (pre-commit): refused"
NOT_SPEC = "This is not a spec refusal."

if GIT is None:
    print("SUITE SKIPPED: no git on PATH")
    sys.exit(0)

# --------------------------------------------------------------------------
print("\n# The plan: dispatch exists exactly where spec-gate-commit does")
cfg, _ = resolve_config(load_yaml(CFG))
plan = build_plan(cfg)
disp = [a for a in plan if a["path"] == GIT_HOOK_DISPATCH]
check("dispatch is a plan action when spec-gate-commit is resolved",
      len(disp) == 1 and "spec-gate-commit" in cfg["_resolved_hooks"])
check("dispatch is kind file, mode 0o755 (never kind hook: verify_wiring "
      "would demand a settings registration)",
      disp and disp[0]["kind"] == "file" and disp[0]["mode"] == 0o755)
cfg_off, _ = resolve_config(load_yaml(CFG_OFF))
check("hooks.spec_gate_commit: false drops dispatch from the plan",
      not any(a["path"] == GIT_HOOK_DISPATCH for a in build_plan(cfg_off)))
check("no plan action targets .git/ (the shim is apply-time only)",
      not any(a["path"].startswith(".git/") for a in plan))
# [D2, operator 2026-10-04/05] WP3 ships warn; the switch to block waits for
# D5 or interactive live-run arms. DEFAULTS is the mode's one default
# (critic 1g), so this is the row a flip changes, on purpose.
check("the mode WP3 ships is warn (DEFAULTS)",
      DEFAULTS["hooks"]["spec_gate_commit_mode"] == "warn")
check("the dispatch a config without the key gets carries DEFAULTS' mode",
      f"\nMODE={DEFAULTS['hooks']['spec_gate_commit_mode']} " in TEMPLATES[
          "git_hook_dispatch"](resolve_config(load_yaml(CFG_BASE))[0]))
# [critic 1a] No scope key: a config that still names one changes nothing.
_scoped = resolve_config(load_yaml(
    CFG + "  spec_gate_commit_scope: all\n"))[0]
check("hooks.spec_gate_commit_scope is not a key: dispatch and the shim are "
      "byte-identical with it set to 'all'",
      TEMPLATES["git_hook_dispatch"](_scoped)
      == TEMPLATES["git_hook_dispatch"](cfg)
      and TEMPLATES["git_hook_shim"](_scoped) == SHIM)
body = disp[0]["body"] if disp else ""
first_cmd = [ln for ln in body.splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")][:1]
check("dispatch: its first command is the agent-only scope check",
      first_cmd == ['[ "${CLAUDECODE:-}" = "1" ] || exit 0'], first_cmd)
_cmds = [ln.strip() for ln in body.splitlines()
         if ln.strip() and not ln.lstrip().startswith("#")]
check("dispatch: no set -e / set -u (an internal error must not read as "
      "a refusal)", not any(c.startswith("set ") for c in _cmds), _cmds[:5])
check("shim: marker on line 2", SHIM.splitlines()[1].startswith(
    "# " + GIT_HOOK_MARKER))
shim_first = [ln for ln in SHIM.splitlines()
              if ln.strip() and not ln.lstrip().startswith("#")][:1]
check("shim: its first command is the agent-only scope check",
      shim_first == ['[ "${CLAUDECODE:-}" = "1" ] || exit 0'], shim_first)
check("shim: POSIX sh, not bash", SHIM.startswith("#!/bin/sh\n"))
r = run(["sh", "-n"], ROOT, stdin=SHIM)
check("shim parses under /bin/sh -n", r.returncode == 0, r.stderr)
r = run(["bash", "-n"], ROOT, stdin=body)
check("dispatch parses under bash -n", r.returncode == 0, r.stderr)

# --------------------------------------------------------------------------
print("\n# Fresh install, re-install, commits")
proj = new_repo()
r = install(proj)
check("install into a git repo exits 0", r.returncode == 0, r.stderr)
for name in ("pre-commit", "pre-merge-commit"):
    p = hook_path(proj, name)
    check(f"{name} shim written, executable",
          os.path.isfile(p) and read(p) == SHIM
          and os.stat(p).st_mode & 0o777 == 0o755)
rows = manifest_rows(proj)
check("manifest records both shims as kind git_hook, non-critical",
      sorted(f["path"] for f in rows) == [".git/hooks/pre-commit",
                                          ".git/hooks/pre-merge-commit"]
      and all(f["tier"] == "non-critical" for f in rows))
check("no warning about git hooks on a clean install",
      "git hook" not in r.stderr, r.stderr)
before = read(hook_path(proj, "pre-commit"))
r = install(proj)
check("re-install exits 0 and reports the shims unchanged",
      r.returncode == 0 and "ok   .git/hooks/pre-commit" in r.stdout
      and read(hook_path(proj, "pre-commit")) == before, r.stdout[-800:])
harness_commit(proj)
h0 = head(proj)
r = commit_file(proj, "src/app.py")
check("warn mode: agent `git add && git commit` of an unlisted file lands",
      r.returncode == 0 and head(proj) != h0, r.stderr)
check("warn mode: the check's reason and the warn line reach stderr",
      "src/app.py" in r.stderr and WARN in r.stderr, r.stderr)
h1 = head(proj)
r = commit_file(proj, "src/human.py", agent=False)
check("a human commit runs nothing: lands with empty stderr",
      r.returncode == 0 and head(proj) != h1 and r.stderr == "", r.stderr)

print("\n# Block mode (hooks.spec_gate_commit_mode: block), every commit form")
set_mode(proj, "block")
git(proj, "add", "-A")
git(proj, "commit", "-q", "-m", "mode")      # human: unchecked
h2 = head(proj)
r = commit_file(proj, "src/bad.py")
check("block: agent add&&commit of an unlisted file is refused, HEAD "
      "unmoved", r.returncode != 0 and head(proj) == h2
      and REFUSED in r.stderr, r.stderr)
git(proj, "reset", "-q")
with open(os.path.join(proj, "src", "app.py"), "a") as fh:
    fh.write("more\n")
r = git(proj, "commit", "-q", "-am", "am", agent=True)
check("block: agent `git commit -am` touching an unlisted file is refused",
      r.returncode != 0 and head(proj) == h2, r.stderr)
git(proj, "checkout", "-q", "--", "src/app.py")
tdir = os.path.join(proj, ".claude", "specs", "demo", "tasks")
os.makedirs(tdir)
with open(os.path.join(tdir, "T1.md"), "w") as fh:
    fh.write("Files:\n- src/ok.py\n")
git(proj, "add", "-A")
git(proj, "commit", "-q", "-m", "task")
h3 = head(proj)
r = commit_file(proj, "src/ok.py")
check("block: a listed file is allowed", r.returncode == 0
      and head(proj) != h3, r.stderr)
# [WP3 fix1, operator decision 2026-10-06 (1)] pre-merge-commit checks the
# merge's OWN changes (paths where the result differs from every parent;
# [WP3 fix2 MR-1] since fix round 2, from git's automatic merge result). The
# commits it brings in are not checked again: an agent's were checked when
# they were made, and a person's, like the "human" commits below, never are
# (re-review RR-1).
with open(os.path.join(proj, "src", "shared.py"), "w") as fh:
    fh.write("1\n2\n3\n4\n5\n")
git(proj, "add", "src/shared.py")
git(proj, "commit", "-q", "-m", "shared")       # human: unchecked
git(proj, "checkout", "-q", "-b", "side")
commit_file(proj, "src/side.py", agent=False)
with open(os.path.join(proj, "src", "shared.py"), "w") as fh:
    fh.write("1\n2\n3\n4\n50\n")
git(proj, "commit", "-q", "-am", "side shared")
git(proj, "checkout", "-q", "main")
h4 = head(proj)
r = git(proj, "merge", "--no-ff", "-q", "-m", "m", "side", agent=True)
check("block: an agent `git merge --no-ff` whose result equals a parent on "
      "every unlisted path (the branch's own src/side.py) lands",
      r.returncode == 0 and head(proj) != h4, r.stderr)
git(proj, "reset", "-q", "--hard", h4)
with open(os.path.join(proj, "src", "shared.py"), "w") as fh:
    fh.write("10\n2\n3\n4\n5\n")
git(proj, "commit", "-q", "-am", "main shared")
h4 = head(proj)
# [WP3 fix2 MR-1] Both sides changed src/shared.py in different lines and git
# merged it on its own: that is not the merge's own change (it was refused
# under the every-parent rule, as "a conflict resolution").
r = git(proj, "merge", "--no-ff", "-q", "-m", "m", "side", agent=True)
check("block: an agent merge of a file both sides changed, which git merged "
      "on its own (src/shared.py), lands through pre-merge-commit (MR-1)",
      r.returncode == 0 and head(proj) != h4 and "spec check" not in r.stderr,
      r.stderr)
git(proj, "reset", "-q", "--hard", h4)
with open(os.path.join(proj, "src", "shared.py"), "w") as fh:
    fh.write("1\n2\n3\n4\n500\n")
git(proj, "commit", "-q", "-am", "main shared 2")
h4 = head(proj)
# The same line on both sides: a conflict, which `-X theirs` resolves
# without stopping, so pre-merge-commit runs on the agent's resolution.
r = git(proj, "merge", "--no-ff", "-q", "-X", "theirs", "-m", "m", "side",
        agent=True)
check("block: an agent merge whose conflict `-X theirs` resolved "
      "(src/shared.py) is refused by pre-merge-commit, which names only "
      "that file", r.returncode != 0 and head(proj) == h4
      and "spec check (pre-merge-commit): refused" in r.stderr
      and "  src/shared.py\n" in r.stderr and "src/side.py" not in r.stderr,
      r.stderr)
check("... and its remedy never says to unstage (that drops the other "
      "side's change): fix the task file, or git merge --abort and ask",
      "This is a merge" in r.stderr and "git merge --abort" in r.stderr
      and "restore --staged" not in r.stderr, r.stderr)
git(proj, "merge", "--abort")
r = git(proj, "merge", "--no-ff", "-q", "-X", "theirs", "-m", "m", "side")
check("block: the same merge by a human lands", r.returncode == 0
      and head(proj) != h4, r.stderr)

# A hook manager (husky, lefthook) calls dispatch directly, without the
# shim, so dispatch must scope itself.
r = run(["sh", "-c", "echo x > src/mgr.py && git add src/mgr.py && "
         "bash .claude/githooks/dispatch pre-commit"], proj)
check("dispatch called directly for a human (as a hook manager would): "
      "exit 0, silent", r.returncode == 0 and r.stderr == "", r.stderr)
r = run(["bash", ".claude/githooks/dispatch", "pre-commit"], proj, AGENT_ENV)
check("... and for an agent it refuses (exit 1)", r.returncode == 1
      and REFUSED in r.stderr, r.stderr)
git(proj, "reset", "-q")
os.unlink(os.path.join(proj, "src", "mgr.py"))

print("\n# Linked worktree (implementer isolation)")
wt = os.path.join(proj, ".claude", "worktrees", "agent-1")
git(proj, "worktree", "add", "-q", wt, "-b", "worktree-agent-1")
hw = head(wt)
r = commit_file(wt, "src/wt.py")
check("the common-dir shim fires in a linked worktree and refuses there",
      r.returncode != 0 and head(wt) == hw and REFUSED in r.stderr, r.stderr)
git(wt, "reset", "-q")
with open(os.path.join(wt, ".claude", "specs", "demo", "tasks", "T1.md"),
          "a") as fh:
    fh.write("- src/wt.py\n")
git(wt, "add", "-A")
r = git(wt, "commit", "-q", "-m", "wt", agent=True)
check("... and passes once the worktree's own task file lists the file",
      r.returncode == 0 and head(wt) != hw, r.stderr)

# --------------------------------------------------------------------------
print("\n# Worktree branched before the harness was committed")
proj = new_repo()
with open(os.path.join(proj, "README"), "w") as fh:
    fh.write("seed\n")
git(proj, "add", "README")
git(proj, "commit", "-q", "-m", "seed")
install(proj)                       # harness installed, NOT committed
wt = os.path.join(os.path.dirname(proj), "wt-early")
git(proj, "worktree", "add", "-q", wt, "-b", "early")
check("the worktree has no .claude/ of its own",
      not os.path.exists(os.path.join(wt, ".claude")))
r = commit_file(wt, "src/early.py")
check("the shim runs the MAIN checkout's dispatch there",
      "spec check (pre-commit)" in r.stderr
      and "cannot run .claude/githooks/dispatch" not in r.stderr, r.stderr)

print("\n# Ownership: edited shim, --force, uninstall")
proj = new_repo()
install(proj)
with open(hook_path(proj, "pre-commit"), "a") as fh:
    fh.write("# my line\n")
r = install(proj)
check("an edited shim is kept, rc 0, with a stderr warning",
      r.returncode == 0 and read(hook_path(proj, "pre-commit")).endswith(
          "# my line\n") and "pre-commit kept your local edits" in r.stderr,
      r.stderr)
r = install(proj)
check("... and stays kept on the next run (sticky)",
      read(hook_path(proj, "pre-commit")).endswith("# my line\n"))
r = install(proj, CFG, "--force")
check("--force overwrites an edited shim and saves a backup",
      read(hook_path(proj, "pre-commit")) == SHIM
      and "installer-backups" in r.stdout, r.stdout[-600:])
with open(hook_path(proj, "pre-merge-commit"), "a") as fh:
    fh.write("# mine\n")
r = run([sys.executable, BIN, "-C", proj, "--uninstall"], proj)
check("uninstall removes the unedited shim",
      not os.path.exists(hook_path(proj, "pre-commit")))
check("uninstall keeps the edited shim",
      os.path.exists(hook_path(proj, "pre-merge-commit")))

print("\n# Never clobber: foreign hook, symlink, core.hooksPath")
proj = new_repo()
theirs = "#!/bin/sh\necho theirs >&2\nexit 0\n"
with open(hook_path(proj, "pre-commit"), "w") as fh:
    fh.write(theirs)
os.chmod(hook_path(proj, "pre-commit"), 0o755)
r = install(proj)
check("a foreign pre-commit is left byte-identical",
      read(hook_path(proj, "pre-commit")) == theirs)
check("... pre-merge-commit is still installed",
      read(hook_path(proj, "pre-merge-commit")) == SHIM)
check("... rc 0 and a warning naming the hook and the dispatch command",
      r.returncode == 0 and ".git/hooks/pre-commit already exists" in r.stderr
      and ".claude/githooks/dispatch pre-commit" in r.stderr, r.stderr)
check("... the foreign hook gets no manifest row",
      [f["path"] for f in manifest_rows(proj)] ==
      [".git/hooks/pre-merge-commit"])
install(proj, CFG, "--force")
check("--force does not overwrite a foreign hook",
      read(hook_path(proj, "pre-commit")) == theirs)
run([sys.executable, BIN, "-C", proj, "--uninstall"], proj)
check("uninstall leaves the foreign hook",
      read(hook_path(proj, "pre-commit")) == theirs)

proj = new_repo()
shared = os.path.join(os.path.dirname(proj), "shared-hook")
with open(shared, "w") as fh:
    fh.write("#!/bin/sh\n# " + GIT_HOOK_MARKER + " v1\nexit 0\n")
os.symlink(shared, hook_path(proj, "pre-commit"))
before = read(shared)
r = install(proj, CFG, "--force")
check("a symlinked hook is never written through, even with --force",
      os.path.islink(hook_path(proj, "pre-commit"))
      and read(shared) == before, r.stdout[-400:])

proj = new_repo()
git(proj, "config", "core.hooksPath", ".husky/_")
r = install(proj)
check("core.hooksPath set: no shim written, rc 0",
      r.returncode == 0 and not os.path.exists(hook_path(proj, "pre-commit")))
check("... and the warning names core.hooksPath and the dispatch command",
      "core.hooksPath is set to .husky/_" in r.stderr
      and ".claude/githooks/dispatch pre-commit" in r.stderr, r.stderr)
check("... and the installer never changed core.hooksPath",
      git(proj, "config", "--get", "core.hooksPath").stdout.strip()
      == ".husky/_")

print("\n# pre-commit framework kept our shim as pre-commit.legacy")
proj = new_repo()
install(proj)
os.rename(hook_path(proj, "pre-commit"), hook_path(proj, "pre-commit.legacy"))
with open(hook_path(proj, "pre-commit"), "w") as fh:
    # Stands in for the framework's hook, which runs pre-commit.legacy.
    fh.write("#!/bin/sh\n# File generated by pre-commit: "
             "https://pre-commit.com\n"
             'exec "$(dirname "$0")/pre-commit.legacy" "$@"\n')
os.chmod(hook_path(proj, "pre-commit"), 0o755)
harness_commit(proj)
r = commit_file(proj, "src/legacy.py")
check("run as pre-commit.legacy, the shim still runs the pre-commit check",
      r.returncode == 0 and WARN in r.stderr, r.stderr)
r = install(proj)
check("re-install manages the shim at pre-commit.legacy, without a warning",
      "ok   .git/hooks/pre-commit.legacy" in r.stdout
      and "pre-commit already exists" not in r.stderr, r.stdout[-600:])
run([sys.executable, BIN, "-C", proj, "--uninstall"], proj)
check("uninstall removes pre-commit.legacy and keeps the framework's hook",
      not os.path.exists(hook_path(proj, "pre-commit.legacy"))
      and os.path.exists(hook_path(proj, "pre-commit")))

# --------------------------------------------------------------------------
print("\n# No repository yet; a project inside a larger repository")
proj = new_repo(git_init=False)
r = install(proj)
check("no .git: rc 0, stdout names `git init` and re-running",
      r.returncode == 0 and "not inside a git repository" in r.stdout
      and "git init" in r.stdout, r.stdout[-600:])
check("... and says nothing on stderr (no commit to check yet; a VCS-less "
      "project is a valid Phase 0 state)", "git" not in r.stderr, r.stderr)
check("... and nothing was created under .git",
      not os.path.exists(os.path.join(proj, ".git")))
git(proj, "init", "-q", "-b", "main")
r = install(proj)
check("after `git init`, a re-install adds both shims",
      read(hook_path(proj, "pre-commit")) == SHIM
      and read(hook_path(proj, "pre-merge-commit")) == SHIM, r.stdout[-400:])

outer = new_repo()
inner = os.path.join(outer, "pkg")
os.mkdir(inner)
r = install(inner)
check("project below the repository top: no shim, rc 0, warning",
      r.returncode == 0
      and not os.path.exists(hook_path(outer, "pre-commit"))
      and "inside the git repository" in r.stderr, r.stderr)

print("\n# GIT_DIR in the installer's own environment is ignored")
proj = new_repo()
decoy = new_repo()
cfgp = os.path.join(os.path.dirname(proj), "c.yaml")
with open(cfgp, "w") as fh:
    fh.write(CFG)
r = run([sys.executable, BIN, "-c", cfgp, "-C", proj], proj,
        dict(BASE_ENV, GIT_DIR=os.path.join(decoy, ".git")))
check("install with GIT_DIR pointing elsewhere still targets -C's repo",
      os.path.exists(hook_path(proj, "pre-commit"))
      and not os.path.exists(hook_path(decoy, "pre-commit")), r.stderr)

print("\n# Toggle off retires the shims")
proj = new_repo()
install(proj)
r = install(proj, CFG_OFF)
check("hooks.spec_gate_commit: false removes both unedited shims",
      not os.path.exists(hook_path(proj, "pre-commit"))
      and not os.path.exists(hook_path(proj, "pre-merge-commit"))
      and not os.path.exists(os.path.join(proj, GIT_HOOK_DISPATCH)),
      r.stdout[-600:])
install(proj)
with open(hook_path(proj, "pre-commit"), "a") as fh:
    fh.write("# mine\n")
r = install(proj, CFG_OFF)
check("... but keeps an edited one and says so",
      os.path.exists(hook_path(proj, "pre-commit"))
      and "you have edited" in r.stderr, r.stderr)

# --------------------------------------------------------------------------
# [WP3 critic 1n] Pins for single-variable mutants that survived the
# verifiers' runs (d2-githooks X1-X4, X24, X25, X32-X34): each row below
# fails with its guard removed.
print("\n# --dry-run writes nothing")
proj = new_repo()
r = install(proj, CFG, "--dry-run")
check("--dry-run on a fresh repository: no shim written, though it says it "
      "would create them", not os.path.exists(hook_path(proj, "pre-commit"))
      and not os.path.exists(hook_path(proj, "pre-merge-commit"))
      and "CREATE .git/hooks/pre-commit" in r.stdout, r.stdout[-600:])
install(proj)
r = install(proj, CFG_OFF, "--dry-run")
check("--dry-run with the gate turned off: both shims stay",
      read(hook_path(proj, "pre-commit")) == SHIM
      and read(hook_path(proj, "pre-merge-commit")) == SHIM
      and "REMOVE (dry run) .git/hooks/pre-commit" in r.stdout,
      r.stdout[-600:])

print("\n# Toggle off keeps an edit an earlier run recorded")
with open(hook_path(proj, "pre-commit"), "a") as fh:
    fh.write("# mine\n")
install(proj)              # SKIP: the manifest now records the EDITED bytes
r = install(proj, CFG_OFF)
check("a shim whose edit an earlier SKIP recorded is kept when the gate "
      "is turned off", (read(hook_path(proj, "pre-commit")) or "").endswith(
          "# mine\n") and "you have edited" in r.stderr, r.stderr)

print("\n# --adopt records an edited shim as installer-owned")
proj = new_repo()
install(proj)
with open(hook_path(proj, "pre-commit"), "a") as fh:
    fh.write("# stale\n")
r = install(proj, CFG, "--adopt")
check("--adopt: ADOPT line, nothing written",
      "ADOPT  .git/hooks/pre-commit" in r.stdout
      and read(hook_path(proj, "pre-commit")).endswith("# stale\n"),
      r.stdout[-600:])
install(proj)
check("... so the next ordinary run updates it",
      read(hook_path(proj, "pre-commit")) == SHIM)

print("\n# A hooks directory that is a symlink is never written through")
proj = new_repo()
shared = os.path.join(os.path.dirname(proj), "shared-hooks")
shutil.rmtree(os.path.join(proj, ".git", "hooks"))
os.mkdir(shared)
os.symlink(shared, os.path.join(proj, ".git", "hooks"))
r = install(proj)
check("symlinked hooks directory: nothing written into it, rc 0, warning",
      r.returncode == 0 and os.listdir(shared) == []
      and "hooks directory is a symlink" in r.stderr, r.stderr)

print("\n# No hooks directory at all (git init --template=)")
proj = new_repo(git_init=False)
git(proj, "init", "-q", "--template=", "-b", "main")
had = os.path.isdir(os.path.join(proj, ".git", "hooks"))
install(proj)
check("the hooks directory is created, then both shims",
      not had and read(hook_path(proj, "pre-commit")) == SHIM
      and read(hook_path(proj, "pre-merge-commit")) == SHIM, had)

print("\n# Rows kept while the hooks directory is unreachable")
proj = new_repo()
install(proj)
git(proj, "config", "core.hooksPath", ".husky")
r = install(proj)
git(proj, "config", "--unset", "core.hooksPath")
run([sys.executable, BIN, "-C", proj, "--uninstall"], proj)
check("core.hooksPath set later, re-install, unset, uninstall: the shims "
      "an earlier run wrote are still removed",
      not os.path.exists(hook_path(proj, "pre-commit"))
      and not os.path.exists(hook_path(proj, "pre-merge-commit")))

print("\n# A hooks directory that cannot be written (critic 1h)")
if hasattr(os, "geteuid") and os.geteuid() == 0:
    print("  SKIP  running as root: a mode-555 directory stays writable")
else:
    proj = new_repo()
    hd = os.path.join(proj, ".git", "hooks")
    for f in os.listdir(hd):
        os.unlink(os.path.join(hd, f))
    os.chmod(hd, 0o555)
    try:
        r = install(proj)
    finally:
        os.chmod(hd, 0o755)
    check("unwritable hooks directory: rc 0, no traceback, the manifest is "
          "written", r.returncode == 0 and "Traceback" not in r.stderr
          and os.path.isfile(os.path.join(proj, ".claude",
                                          ".installer-manifest.json")),
          r.stderr[-800:])
    check("... a stderr warning per shim names it and the remedy, and no "
          "manifest row claims it", ".git/hooks/pre-commit could not be "
          "written" in r.stderr and ".git/hooks/pre-merge-commit could not "
          "be written" in r.stderr and "hooks directory writable" in r.stderr
          and manifest_rows(proj) == [], r.stderr[-800:])
    check("... no temporary file left behind", os.listdir(hd) == [],
          os.listdir(hd))
    r = install(proj)
    check("... and once it is writable, a re-install adds both shims",
          read(hook_path(proj, "pre-commit")) == SHIM
          and read(hook_path(proj, "pre-merge-commit")) == SHIM, r.stderr)

print("\n# Edited dispatch, spec-check.sh, merge-back.sh: a stderr warning")
# [WP3 critic 1i] They hold config (the mode, the prefixes, the gate
# list), so a kept edit means a config change does not reach them.
proj = new_repo()
install(proj)
for rel in (GIT_HOOK_DISPATCH, SPEC_CHECK_PATH, MERGE_BACK_SCRIPT):
    with open(os.path.join(proj, rel), "a") as fh:
        fh.write("# my tweak\n")
r = install(proj, CFG_BLOCK)
for rel, what in ((GIT_HOOK_DISPATCH, "hooks.spec_gate_commit_mode"),
                  (SPEC_CHECK_PATH, "hooks.spec_gate_commit_prefixes"),
                  (MERGE_BACK_SCRIPT, "which commit gates it runs")):
    check(f"edited {rel}: kept, rc 0, and stderr says the config change "
          f"({what}) does not reach it", r.returncode == 0
          and read(os.path.join(proj, rel)).endswith("# my tweak\n")
          and f"warning: {rel} kept your local edits" in r.stderr
          and f"a config change it embeds ({what}) does NOT reach it"
          in r.stderr, r.stderr[-1200:])
check("... and the edited dispatch kept its old mode (the reason to warn)",
      "\nMODE=warn " in read(os.path.join(proj, GIT_HOOK_DISPATCH)))

# --------------------------------------------------------------------------
print("\n# The check cannot run: block refuses (fail-closed), warn allows")
# [WP3 critic 1c, operator ruling 2026-10-05] In block mode a check that
# could not run REFUSES and says it is not a spec refusal (PRD:799-800); in
# warn mode it lets the commit through with the reason. A person's commit
# is never checked. A missing dispatch or no bash stays fail-open (below).
proj = new_repo()
install(proj, CFG_BLOCK)
harness_commit(proj)
sgc = os.path.join(proj, SPEC_CHECK_PATH)   # [d2-check] the check itself
saved = read(sgc)
os.unlink(sgc)
h = head(proj)
r = commit_file(proj, "src/f1.py")
check("block, check missing: refused, HEAD unmoved, names the missing file "
      "and says it is not a spec refusal",
      r.returncode != 0 and head(proj) == h and "is missing" in r.stderr
      and REFUSED in r.stderr and NOT_SPEC in r.stderr
      and "hooks.spec_gate_commit: false" in r.stderr, r.stderr)
git(proj, "reset", "-q")
r = commit_file(proj, "src/f1h.py", agent=False)
check("block, check missing, a person's commit: lands, silent",
      r.returncode == 0 and head(proj) != h and r.stderr == "", r.stderr)
with open(sgc, "w") as fh:
    fh.write("#!/usr/bin/env bash\necho boom >&2\nexit 5\n")
h = head(proj)
r = commit_file(proj, "src/f2.py")
check("block, check exits 5 (not 0, not 2): refused, 'exited 5', not a "
      "spec refusal", r.returncode != 0 and head(proj) == h
      and "exited 5" in r.stderr and NOT_SPEC in r.stderr, r.stderr)
git(proj, "reset", "-q")
set_mode(proj, "warn")
h = head(proj)
r = commit_file(proj, "src/f2w.py")
check("warn, check exits 5: commit allowed, says the check did not run",
      r.returncode == 0 and head(proj) != h and "exited 5" in r.stderr
      and "the check did not run; commit allowed" in r.stderr, r.stderr)
os.unlink(sgc)
h = head(proj)
r = commit_file(proj, "src/f2m.py")
check("warn, check missing: commit allowed with the reason",
      r.returncode == 0 and head(proj) != h and "is missing" in r.stderr,
      r.stderr)
set_mode(proj, "block")
# [WP3 fix1 SC-3, F2] A spec refusal is exit 2 WITH the paths on stdout;
# bash's own exit 2 (a script it cannot parse) has none. [WP3 fix2 CRIT-1,
# MR-3] And a verdict ends stdout with the check's end line.
with open(sgc, "w") as fh:
    fh.write("#!/usr/bin/env bash\necho src/f3.py\n"
             "echo 'Commit blocked: x' >&2\necho '%s'\nexit 2\n"
             % SPEC_CHECK_END)
h = head(proj)
r = commit_file(proj, "src/f3.py")
check("check exits 2 with its file list, block mode: refused as a spec "
      "refusal", r.returncode != 0 and head(proj) == h
      and NOT_SPEC not in r.stderr and REFUSED in r.stderr, r.stderr)
# [WP3 fix1 SC-6] Neutral: the check's own message may list candidates,
# say no task file exists, or offer git merge --abort.
check("... and dispatch's line defers to the message above, naming no "
      "remedy of its own", "refused. Do what the message above says. Do "
      "not bypass this check with --no-verify." in r.stderr
      and "Add the files to the task file" not in r.stderr, r.stderr)
git(proj, "reset", "-q")
with open(sgc, "w") as fh:
    fh.write("#!/usr/bin/env bash\necho 'Commit blocked: x' >&2\nexit 2\n")
h = head(proj)
r = commit_file(proj, "src/f3n.py")
check("check exits 2 with NO file list, block mode: could not run (bash's "
      "own status), not a spec refusal", r.returncode != 0
      and head(proj) == h and "exited 2 without its end line" in r.stderr
      and NOT_SPEC in r.stderr, r.stderr)
git(proj, "reset", "-q")
# [WP3 fix2 CRIT-1, MR-3] The paths, but no end line: the check stopped
# before a verdict (bash parsed only part of it). Not a spec refusal; and
# exit 0 with no end line is not a pass.
for code, label in ((2, "with its file list but NO end line"),
                    (0, "with NO end line")):
    with open(sgc, "w") as fh:
        fh.write("#!/usr/bin/env bash\necho src/f3e.py\nexit %d\n" % code)
    for mode in ("block", "warn"):
        set_mode(proj, mode)
        h = head(proj)
        r = commit_file(proj, f"src/f3e{code}{mode}.py")
        if mode == "block":
            ok = (r.returncode != 0 and head(proj) == h
                  and f"exited {code} without its end line" in r.stderr
                  and NOT_SPEC in r.stderr)
        else:
            ok = (r.returncode == 0 and head(proj) != h
                  and f"exited {code} without its end line" in r.stderr
                  and "the check did not run; commit allowed" in r.stderr)
        check(f"{mode}: check exits {code} {label}: could not run, never a "
              f"spec refusal or a pass [WP3 fix2 MR-3]", ok, r.stderr)
        git(proj, "reset", "-q")
set_mode(proj, "block")
# [WP3 fix2 CRIT-1, MR-3] No `bash -n` guard: bash exits 2 on what it
# cannot parse (no end line), or reports the error and runs on, which the
# check turns into exit 3. The third is MR-3's: bash before 5.2 does not
# parse inside $(...) under -n, and the check ran on to "covered".
# [WP3 fix3 EM-1] ere_esc is bash now (no $(...)), so the broken
# substitution is written around its result.
for k, (label, old, new) in enumerate((
        ("an unclosed quote", "PREFIXES='src/ lib/ app/ test/ tests/'",
         "PREFIXES='src/ lib/ app/ test/ tests/ pkg/"),
        ("an unclosed array", "PREFIXES='src/ lib/ app/ test/ tests/'",
         "PREFIXES=(src/ lib/"),
        ("a syntax error inside $(...)",
         'ere_esc "$f"; fe="$ERE"; ere_esc "$b"; be="$ERE"',
         'ere_esc "$f"; fe="$(printf %s "$ERE" |)"; ere_esc "$b"; '
         'be="$ERE"'))):
    assert old in saved
    with open(sgc, "w") as fh:
        fh.write(saved.replace(old, new, 1))
    for mode in ("block", "warn"):
        set_mode(proj, mode)
        h = head(proj)
        r = commit_file(proj, f"src/f8{mode}{k}.py")
        cnr = ("without its end line" in r.stderr
               or "exited 3, so the check" in r.stderr
               or "exited 3, so the check did not run" in r.stderr)
        if mode == "block":
            ok = (r.returncode != 0 and head(proj) == h and cnr
                  and NOT_SPEC in r.stderr)
        else:
            ok = (r.returncode == 0 and head(proj) != h and cnr
                  and "the check did not run; commit allowed" in r.stderr)
        check(f"{mode}: spec-check.sh with {label} (a hand edit gone wrong) "
              f"could not run, and says so; never a spec refusal", ok,
              r.stderr)
        git(proj, "reset", "-q")
set_mode(proj, "block")
with open(sgc, "w") as fh:
    fh.write(saved)
dp = os.path.join(proj, GIT_HOOK_DISPATCH)
dsaved = read(dp)
with open(dp, "w") as fh:     # a parse error the run actually reaches
    fh.write(dsaved.replace("\nMODE=", "\nif then fi\nMODE=", 1))
h = head(proj)
r = commit_file(proj, "src/f4.py")
check("dispatch with a syntax error: shim lets the commit through and says "
      "so", r.returncode == 0 and head(proj) != h
      and "internal error rather than a refusal" in r.stderr, r.stderr)
os.unlink(dp)
h = head(proj)
r = commit_file(proj, "src/f5.py")
check("dispatch missing, agent: commit allowed with a message",
      r.returncode == 0 and head(proj) != h
      and "cannot run .claude/githooks/dispatch" in r.stderr, r.stderr)
r = commit_file(proj, "src/f6.py", agent=False)
check("dispatch missing, human: silent", r.returncode == 0
      and r.stderr == "", r.stderr)
with open(dp, "w") as fh:
    fh.write(dsaved)
os.chmod(dp, 0o644)
h = head(proj)
r = commit_file(proj, "src/f7.py")
check("dispatch without its exec bit still runs (the shim calls bash)",
      r.returncode != 0 and head(proj) == h and REFUSED in r.stderr, r.stderr)
git(proj, "reset", "-q")

# --------------------------------------------------------------------------
print("\n# The remedy follows the commit's form, and following it lands")
# [WP3 fix1 SC-2] In block mode the plain-commit remedy looped: a pathspec
# commit records only the paths it names (a staged task file outside them
# read as "not in the index"), `commit -a` re-stages what is unstaged, and
# `git restore --staged` fails on an unborn branch. Each row follows the
# refusal's own words.
proj = new_repo()
install(proj, CFG_BLOCK)
T1 = ".claude/specs/demo/tasks/T1.md"
os.makedirs(os.path.join(proj, os.path.dirname(T1)))
with open(os.path.join(proj, T1), "w") as fh:
    fh.write("---\nstatus: in-progress\n---\nFiles:\n- src/a.py\n")
for rel in ("src/a.py", "src/c.py", "src/d.py"):
    os.makedirs(os.path.join(proj, "src"), exist_ok=True)
    with open(os.path.join(proj, rel), "w") as fh:
        fh.write("v1\n")
harness_commit(proj)                          # a person's: unchecked
with open(os.path.join(proj, "src/c.py"), "w") as fh:
    fh.write("v2\n")
h = head(proj)
r = git(proj, "commit", "-q", "-m", "c", "--", "src/c.py", agent=True)
check("pathspec commit of an unlisted file: refused; the remedy names the "
      "task file in the same command, not `git add`",
      r.returncode != 0 and head(proj) == h
      and "commit again with that file named in the same command (git "
      "commit <paths> <task file>)" in r.stderr
      and "stage that file (git add)" not in r.stderr, r.stderr)
with open(os.path.join(proj, T1), "a") as fh:
    fh.write("- src/c.py\n")
git(proj, "add", T1)
r = git(proj, "commit", "-q", "-m", "c", "--", "src/c.py", agent=True)
check("... the task file staged but not named: still refused, and it is "
      "listed as not recorded by THIS commit, never as 'the index does not "
      "have them'", r.returncode != 0 and head(proj) == h
      and "Not counted, because this commit does not record them" in r.stderr
      and "the index does not have them" not in r.stderr
      and f"  {T1}\n" in r.stderr, r.stderr)
r = git(proj, "commit", "-q", "-m", "c", "--", "src/c.py", T1, agent=True)
check("... and naming the task file in the same command, as the remedy "
      "says, lands", r.returncode == 0 and head(proj) != h, r.stderr)
for rel in ("src/a.py", "src/d.py"):
    with open(os.path.join(proj, rel), "w") as fh:
        fh.write("v3\n")
h = head(proj)
r = git(proj, "commit", "-q", "-am", "ad", agent=True)
check("commit -a with an unlisted tracked file: refused; no unstage advice "
      "(commit -a re-stages it), commit the task's paths by name instead",
      r.returncode != 0 and head(proj) == h
      and "restore --staged" not in r.stderr
      and "commit the task's paths by name instead (git commit -- "
      "<paths>)" in r.stderr, r.stderr)
r = git(proj, "commit", "-q", "-m", "a", "--", "src/a.py", agent=True)
check("... and committing the task's path by name, as it says, lands",
      r.returncode == 0 and head(proj) != h, r.stderr)
git(proj, "checkout", "-q", "--", "src/d.py")

proj = new_repo()
install(proj, CFG_BLOCK)
os.makedirs(os.path.join(proj, "src"))
with open(os.path.join(proj, "src/x.py"), "w") as fh:
    fh.write("x\n")
git(proj, "add", "-A")
r = git(proj, "commit", "-q", "-m", "first", agent=True)
check("the first commit (unborn HEAD) with an unlisted file: refused; the "
      "unstage advice is `git rm --cached`, since `git restore --staged` "
      "fails there", r.returncode != 0
      and "unstage it (git rm --cached <path>; this is the first commit)"
      in r.stderr and "restore --staged" not in r.stderr, r.stderr)
r1 = git(proj, "rm", "-q", "--cached", "src/x.py")
r = git(proj, "commit", "-q", "-m", "first", agent=True)
check("... and following it (git rm --cached, then commit) lands",
      r1.returncode == 0 and r.returncode == 0 and head(proj) != "", r.stderr)

# --------------------------------------------------------------------------
# [WP3 fix1] Review findings on the installer and the shim (INST-1, INST-3,
# INST-4, INST-6, TP-08). Each row fails with its guard removed.
from installer import _digest                              # noqa: E402


def install_env(proj, env, cfg=CFG, *extra):
    cfgp = os.path.join(proj, "..", os.path.basename(proj) + ".yaml")
    with open(cfgp, "w") as fh:
        fh.write(cfg)
    return run([sys.executable, BIN, "-c", os.path.abspath(cfgp), "-C", proj,
                *extra], proj, env)


def write_hook(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(body)
    os.chmod(path, 0o755)


def remedy_lines(stderr):
    """The backticked commands a hooks-path warning tells the operator to
    put in each hook, keyed by hook name."""
    return {n: c for n, c in re.findall(
        r"the (pre-commit|pre-merge-commit) hook in \S+ run `([^`]+)`",
        stderr)}


print("\n# [TP-08] core.hooksPath set to the default hooks directory")
for val in (".git/hooks", "ABS"):
    proj = new_repo()
    git(proj, "config", "core.hooksPath",
        os.path.join(proj, ".git", "hooks") if val == "ABS" else val)
    r = install(proj)
    check(f"core.hooksPath = {'<abs>/' if val == 'ABS' else ''}.git/hooks: "
          f"both shims are written, and no hooks-path warning (IN01)",
          read(hook_path(proj, "pre-commit")) == SHIM
          and read(hook_path(proj, "pre-merge-commit")) == SHIM
          and "core.hooksPath is set" not in r.stderr, r.stderr[-400:])

print("\n# [TP-08] A shim that lost its exec bit is repaired")
proj = new_repo()
install(proj)
os.chmod(hook_path(proj, "pre-commit"), 0o644)
install(proj)
check("chmod 644 on a shim, then re-install: 0755 again (git skips a hook "
      "that is not executable) (IN02)",
      os.stat(hook_path(proj, "pre-commit")).st_mode & 0o777 == 0o755)

print("\n# [TP-08] A failed shim upgrade keeps the row --uninstall needs")
if hasattr(os, "geteuid") and os.geteuid() == 0:
    print("  SKIP  running as root: a mode-555 directory stays writable")
else:
    proj = new_repo()
    install(proj)
    # An earlier installer's shim: marked, other bytes, its digest recorded.
    old = SHIM.replace(GIT_HOOK_MARKER + " v1", GIT_HOOK_MARKER + " v0")
    assert old != SHIM and GIT_HOOK_MARKER in old
    mp = os.path.join(proj, ".claude", ".installer-manifest.json")
    m = json.load(open(mp))
    for name in ("pre-commit", "pre-merge-commit"):
        write_hook(hook_path(proj, name), old)
    for f in m["files"]:
        if f.get("kind") == "git_hook":
            f["digest"] = _digest(old)
    with open(mp, "w") as fh:
        json.dump(m, fh)
    hd = os.path.join(proj, ".git", "hooks")
    os.chmod(hd, 0o555)
    try:
        r = install(proj)
    finally:
        os.chmod(hd, 0o755)
    check("(precondition) the upgrade could not write the shims",
          "could not be written" in r.stderr
          and read(hook_path(proj, "pre-commit")) == old, r.stderr[-400:])
    check("... the old shims keep their manifest rows (IG02)",
          sorted(f["path"] for f in manifest_rows(proj))
          == [".git/hooks/pre-commit", ".git/hooks/pre-merge-commit"])
    run([sys.executable, BIN, "-C", proj, "--uninstall"], proj)
    check("... so --uninstall still removes them",
          not os.path.exists(hook_path(proj, "pre-commit"))
          and not os.path.exists(hook_path(proj, "pre-merge-commit")))

print("\n# [TP-08] Which tool wrote a foreign hook is named")
for tool, body in (("lefthook", "#!/bin/sh\n# lefthook generated\n"
                    "lefthook run pre-commit \"$@\"\n"),
                   ("husky", "#!/bin/sh\n. \"$(dirname -- \"$0\")/_/"
                    "husky.sh\"\nnpx lint-staged\n")):
    proj = new_repo()
    write_hook(hook_path(proj, "pre-commit"), body)
    r = install(proj)
    ok = f".git/hooks/pre-commit already exists, written by {tool}" in r.stderr
    # [WP3 fix3 HD-1] The lefthook line is guarded, as every remedy is.
    if tool == "lefthook":
        ok = ok and ("With lefthook, add a `pre-commit` command that runs "
                     "`if [ -f .claude/githooks/dispatch ]; then bash "
                     ".claude/githooks/dispatch pre-commit || exit 1; fi` to "
                     "lefthook.yml" in r.stderr)
    check(f"a {tool} hook: the warning names {tool}"
          + (" and gives the lefthook.yml line (IN03)" if tool == "lefthook"
             else " (IG03)"), ok, r.stderr[-600:])

print("\n# [INST-3] A hook that runs dispatch itself is not warned about")
proj = new_repo()
os.mkdir(os.path.join(proj, ".husky"))
git(proj, "config", "core.hooksPath", ".husky")
r = install(proj)
lines = remedy_lines(r.stderr)
# [WP3 fix3 HD-1] Each line is guarded now (it was plain here).
check("(precondition) core.hooksPath .husky: a warning with one guarded line "
      "per hook", sorted(lines) == ["pre-commit", "pre-merge-commit"]
      and all(c.startswith("if [ -f .claude/githooks/dispatch ]; then ")
              for c in lines.values()), r.stderr[-600:])
write_hook(os.path.join(proj, ".husky", "pre-commit"),
           "#!/bin/sh\n" + lines.get("pre-commit", "") + " || exit 1\n")
r = install(proj)
check("only pre-commit runs it: the re-install warns about pre-merge-commit "
      "alone", sorted(remedy_lines(r.stderr)) == ["pre-merge-commit"],
      r.stderr[-600:])
write_hook(os.path.join(proj, ".husky", "pre-merge-commit"),
           "#!/bin/sh\n" + lines.get("pre-merge-commit", "") + " || exit 1\n")
r = install(proj)
# [WP3 fix2 IT-1, RG-2] Superseded: "nothing to install" came from the hook's
# TEXT, and a line that never runs (after husky 9's `. h`, after an exec, in
# a comment) read the same. Now the re-install says what it can know.
check("both mention it, as the warning said: the re-install gives no plain "
      "remedy again and no 'nothing to install'; it says the hooks mention "
      "the line, that it cannot tell whether git runs it, and how to "
      "confirm (IT-1)",
      remedy_lines(r.stderr) == {}
      and ".husky/pre-commit mentions `.claude/githooks/dispatch pre-commit`"
      in r.stderr and "cannot tell whether git runs that line" in r.stderr
      and "it should print `spec check (pre-commit):`" in r.stderr
      and "nothing to install" not in r.stdout, r.stderr[-600:])
harness_commit(proj)
r = commit_file(proj, "src/husky.py")
check("... and that hook does run the check (warn: the commit lands with "
      "the warn line)", r.returncode == 0 and WARN in r.stderr, r.stderr)

proj = new_repo()
write_hook(hook_path(proj, "pre-commit"),
           "#!/bin/sh\n# my own hook\n.claude/githooks/dispatch pre-commit "
           "|| exit 1\n")
r = install(proj)
check("a hand-written .git/hooks/pre-commit that mentions dispatch: left "
      "alone; the warning says it mentions the line and how to confirm it "
      "runs, not 'have that hook run' (IT-1); pre-merge-commit gets the shim",
      ".git/hooks/pre-commit already exists" in r.stderr
      and ".git/hooks/pre-commit mentions `.claude/githooks/dispatch "
      "pre-commit`" in r.stderr and "have that hook run" not in r.stderr
      and "it runs .claude/githooks/dispatch" not in r.stdout
      and read(hook_path(proj, "pre-merge-commit")) == SHIM, r.stderr[-400:])
# [WP3 fix2 RG-2] A line in a comment is a mention, never a note that the
# hook runs the check; and [IT-2] git skips a hook that is not executable.
proj = new_repo()
write_hook(hook_path(proj, "pre-commit"),
           "#!/bin/sh\n# .claude/githooks/dispatch pre-commit\nexit 0\n")
r = install(proj)
check("a hook whose dispatch line is commented out: a warning that it only "
      "mentions the line, no stdout note that it runs it (RG-2)",
      ".git/hooks/pre-commit mentions" in r.stderr
      and "it runs .claude/githooks/dispatch" not in r.stdout,
      (r.stdout[-300:], r.stderr[-400:]))
proj = new_repo()
write_hook(hook_path(proj, "pre-commit"),
           "#!/bin/sh\n.claude/githooks/dispatch pre-commit || exit 1\n")
os.chmod(hook_path(proj, "pre-commit"), 0o644)
r = install(proj)
check("a hand-written hook that is not executable: the warning says git "
      "skips it and to chmod +x it (IT-2, RG-2)",
      "It is not executable, so git skips it: chmod +x .git/hooks/pre-commit"
      in r.stderr and "it runs .claude/githooks/dispatch" not in r.stdout,
      r.stderr[-400:])
proj = new_repo()
os.mkdir(os.path.join(proj, ".githooks"))
git(proj, "config", "core.hooksPath", ".githooks")
for n_ in ("pre-commit", "pre-merge-commit"):
    write_hook(os.path.join(proj, ".githooks", n_),
               f"#!/bin/sh\n.claude/githooks/dispatch {n_} || exit 1\n")
    os.chmod(os.path.join(proj, ".githooks", n_), 0o644)
r = install(proj)
check("core.hooksPath hooks that are not executable: 'not executable, so "
      "git skips them: chmod +x', never 'nothing to install' (IT-2)",
      ".githooks/pre-commit and .githooks/pre-merge-commit are not "
      "executable, so git skips them: chmod +x" in r.stderr
      and "nothing to install" not in r.stdout, r.stderr[-500:])
for n_ in ("pre-commit", "pre-merge-commit"):
    write_hook(os.path.join(proj, ".githooks", n_), SHIM)
r = install(proj)
check("core.hooksPath holding bootstrap-install's own shim, executable: "
      "'nothing to install' (the one test that is exact), no warning",
      "are bootstrap-install's shim; nothing to install" in r.stdout
      and "core.hooksPath is set" not in r.stderr, (r.stdout[-300:],
                                                    r.stderr[-300:]))
# [WP3 fix2 IT-1] husky 9: core.hooksPath is .husky/_, whose wrappers source
# `h`, which runs .husky/<hook> and exits; a line appended to a wrapper
# never runs, and husky rewrites the directory.
proj = new_repo()
os.makedirs(os.path.join(proj, ".husky", "_"))
with open(os.path.join(proj, ".husky", "_", "h"), "w") as fh:
    fh.write('#!/usr/bin/env sh\nn=$(basename "$0")\n'
             's=$(dirname "$(dirname "$0")")/$n\n[ ! -f "$s" ] && exit 0\n'
             'sh -e "$s" "$@"\nc=$?\nexit $c\n')
for n_ in ("pre-commit", "pre-merge-commit"):
    write_hook(os.path.join(proj, ".husky", "_", n_),
               '#!/usr/bin/env sh\n. "$(dirname "$0")/h"\n'
               f".claude/githooks/dispatch {n_} || exit 1\n")
git(proj, "config", "core.hooksPath", ".husky/_")
r = install(proj)
check("husky 9 with the line appended to its wrapper: no 'nothing to "
      "install'; the warning names .husky/pre-commit as the file husky runs "
      "(IT-1)", "nothing to install" not in r.stdout
      and "put the line in .husky/pre-commit and .husky/pre-merge-commit, "
      "which husky runs" in r.stderr
      and remedy_lines(r.stderr).get("pre-commit")
      == "if [ -f .claude/githooks/dispatch ]; then bash "
      ".claude/githooks/dispatch pre-commit || exit 1; fi"
      and "the pre-commit hook in .husky run" in r.stderr, r.stderr[-700:])
harness_commit(proj)
r = commit_file(proj, "src/h9.py")
check("(why) that wrapper line never runs: an agent commit of an unlisted "
      "file lands with no spec message", r.returncode == 0
      and "spec check" not in r.stderr, r.stderr)
for n_ in ("pre-commit", "pre-merge-commit"):
    with open(os.path.join(proj, ".husky", n_), "w") as fh:
        fh.write(f".claude/githooks/dispatch {n_} || exit 1\n")
r = commit_file(proj, "src/h9b.py")
check("... and in .husky/pre-commit, where the warning says, it does run "
      "(warn: the commit lands with the warn line)",
      r.returncode == 0 and WARN in r.stderr, r.stderr)
proj = new_repo()
write_hook(hook_path(proj, "pre-commit"),
           "#!/bin/sh\n# lefthook generated\nlefthook run pre-commit\n")
with open(os.path.join(proj, "lefthook.yml"), "w") as fh:
    fh.write("pre-commit:\n  commands:\n    spec:\n      run: "
             ".claude/githooks/dispatch pre-commit\n")
r = install(proj)
check("a lefthook hook whose lefthook.yml mentions dispatch: the warning "
      "names lefthook.yml as mentioning it and says how to confirm it runs "
      "(IT-1)",
      "already exists, written by lefthook" in r.stderr
      and "lefthook.yml mentions `.claude/githooks/dispatch pre-commit`"
      in r.stderr and "through lefthook.yml" not in r.stdout,
      r.stderr[-400:])

print("\n# [INST-6] A core.hooksPath every repository reads")
_GG = os.path.join(_HOME, "gitconfig-global-hookspath")
_GHOOKS = os.path.join(_HOME, "ghooks")
os.makedirs(_GHOOKS, exist_ok=True)
with open(_GG, "w") as fh:
    fh.write(f"[core]\n\thooksPath = {_GHOOKS}\n")
GENV = dict(BASE_ENV, GIT_CONFIG_GLOBAL=_GG)
GAGENT = dict(GENV, CLAUDECODE="1")
proj = new_repo()
r = install_env(proj, GENV)
glines = remedy_lines(r.stderr)
check("global core.hooksPath: the warning says every repository reads it, "
      "and each line is guarded",
      "in a git config every repository on this machine reads" in r.stderr
      and sorted(glines) == ["pre-commit", "pre-merge-commit"]
      and all(c.startswith("if [ -f .claude/githooks/dispatch ]; then ")
              for c in glines.values()), r.stderr[-800:])
for name, cmd in glines.items():
    write_hook(os.path.join(_GHOOKS, name), "#!/bin/sh\n" + cmd + "\n")
other = new_repo()
with open(os.path.join(other, "f.txt"), "w") as fh:
    fh.write("x\n")
r1 = run([GIT, "add", "f.txt"], other, GENV)
r2 = run([GIT, "commit", "-q", "-m", "x"], other, GENV)
r3 = run(["sh", "-c", "echo y > g.txt && git add g.txt && "
          "git commit -q -m y"], other, GAGENT)
check("... followed literally, a person's and an agent's commit in another "
      "repository (no dispatch there) still land",
      r2.returncode == 0 and r3.returncode == 0, r2.stderr + r3.stderr)
run([GIT, "checkout", "-q", "-b", "side"], other, GENV)
run(["sh", "-c", "echo s > s.txt && git add s.txt && git commit -q -m s"],
    other, GENV)
run([GIT, "checkout", "-q", "main"], other, GENV)
r = run([GIT, "merge", "--no-ff", "-q", "-m", "m", "side"], other, GENV)
check("... and so does a merge there (pre-merge-commit)", r.returncode == 0,
      r.stderr)
run([GIT, "add", "-A"], proj, GENV)
run([GIT, "commit", "-q", "-m", "harness"], proj, GENV)
r = run(["sh", "-c", "mkdir -p src && echo z > src/z.py && git add src/z.py "
         "&& git commit -q -m z"], proj, GAGENT)
check("... and in the project the same hook runs the check (warn line)",
      r.returncode == 0 and WARN in r.stderr, r.stderr)
r = install_env(proj, GENV)
check("... and a re-install no longer gives the guarded line again: it says "
      "the hooks there mention it and how to confirm (IT-1)",
      remedy_lines(r.stderr) == {} and "mentions `if [ -f" not in r.stderr
      and "cannot tell whether git runs that line" in r.stderr,
      r.stderr[-400:])
proj = new_repo()
git(proj, "config", "core.hooksPath", ".husky")
r = install(proj)
# [WP3 fix3 HD-1] Superseded: it kept the plain line, which refuses every
# commit where dispatch is missing; now only the every-repository text
# differs.
check("a repository's own core.hooksPath: not the every-repository text, "
      "and the same guarded line (HD-1)",
      "every repository on this machine" not in r.stderr
      and remedy_lines(r.stderr).get("pre-commit")
      == "if [ -f .claude/githooks/dispatch ]; then bash "
      ".claude/githooks/dispatch pre-commit || exit 1; fi", r.stderr[-600:])

print("\n# [INST-4] The shim on a branch from before the install")
proj = new_repo()
with open(os.path.join(proj, "a.txt"), "w") as fh:
    fh.write("a\n")
git(proj, "add", "a.txt")
git(proj, "commit", "-q", "-m", "a")
git(proj, "branch", "release-1")
install(proj)
harness_commit(proj)
git(proj, "checkout", "-q", "release-1")
r = commit_file(proj, "fix.txt")
check("an agent commit on a branch cut before the install lands, and the "
      "shim says this checkout has no .claude/githooks/",
      r.returncode == 0 and "this checkout has no .claude/githooks/"
      in r.stderr, r.stderr)
check("... and never tells anyone to install onto that branch",
      "bootstrap-install" not in r.stderr, r.stderr)
r = commit_file(proj, "fix2.txt", agent=False)
check("... a person's commit there is silent", r.returncode == 0
      and r.stderr == "", r.stderr)
proj = new_repo()
with open(os.path.join(proj, "a.txt"), "w") as fh:
    fh.write("a\n")
git(proj, "add", "a.txt")
git(proj, "commit", "-q", "-m", "a")
wt = os.path.join(os.path.dirname(proj), "wt-try")
git(proj, "worktree", "add", "-q", wt, "-b", "try")
install(wt)
r = commit_file(proj, "b.txt")
check("installed from a linked worktree: an agent commit in the main "
      "checkout gets the same line, not 'Re-run bootstrap-install'",
      r.returncode == 0 and "this checkout has no .claude/githooks/"
      in r.stderr and "Re-run" not in r.stderr, r.stderr)

print("\n# [INST-1] An edited .claude/.gitignore without /worktrees/")
GI = ".claude/.gitignore"
WT_WARN = "did not receive the line `/worktrees/`"
proj = new_repo()
install(proj)
with open(os.path.join(proj, GI)) as fh:
    gi = fh.read()
with open(os.path.join(proj, GI), "w") as fh:
    fh.write(gi.replace("/worktrees/\n", "") + "mine.tmp\n")
harness_commit(proj)
r = install(proj)
check("an edited .claude/.gitignore lacking /worktrees/: SKIP, rc 0, and a "
      "stderr warning naming the line and the gitlink it prevents",
      r.returncode == 0 and f"SKIP   {GI}" in r.stdout
      and WT_WARN in r.stderr and "160000 gitlink" in r.stderr,
      r.stderr[-600:])
wt = os.path.join(proj, ".claude", "worktrees", "agent-1")
git(proj, "worktree", "add", "-q", wt, "-b", "worktree-agent-1")
git(proj, "add", "-A")
staged = git(proj, "diff", "--cached", "--raw").stdout
check("(why) git add -A then stages the worktree as a 160000 gitlink",
      " 160000 " in staged and ".claude/worktrees/agent-1" in staged, staged)
git(proj, "reset", "-q")
with open(os.path.join(proj, GI), "a") as fh:
    fh.write("/worktrees/\n")
r = install(proj)
git(proj, "add", "-A")
check("following it (add the line): no warning, and git add -A stages "
      "nothing under .claude/worktrees/",
      WT_WARN not in r.stderr and ".claude/worktrees" not in git(
          proj, "diff", "--cached", "--name-only").stdout, r.stderr[-400:])
git(proj, "reset", "-q")
with open(os.path.join(proj, GI), "w") as fh:
    fh.write(gi.replace("/worktrees/\n", "") + "mine.tmp\n")
with open(os.path.join(proj, ".gitignore"), "a") as fh:
    fh.write("/.claude/worktrees/\n")
r = install(proj)
check("an edited copy, with the root .gitignore covering the worktrees: "
      "no warning", f"SKIP   {GI}" in r.stdout and WT_WARN not in r.stderr,
      r.stderr[-400:])
_apply = " ".join(open(os.path.join(
    ROOT, "plugin", "commands", "bootstrap-apply.md")).read().split())
check("bootstrap-apply.md names that warning among the lines to relay",
      "for a `.claude/.gitignore` the run leaves alone that lacks the "
      "`/worktrees/` line" in _apply)

# --------------------------------------------------------------------------
print("\n# [WP3 fix2] Through the real shim and dispatch: a stopped "
      "cherry-pick, and the merge remedy in warn mode")


def put(proj, rel, text):
    p = os.path.join(proj, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        fh.write(text)


TASK_OK = ".claude/specs/f/tasks/f-T01.md"
# [WP3 fix2 MR-2] A conflicted cherry-pick concluded with --continue fires
# pre-commit. The check used to read the whole picked commit (a teammate's
# src/billing/pay.py included) and say "unstage it": a partial pick under
# the teammate's message.
proj = new_repo()
install(proj, CFG_BLOCK)
harness_commit(proj)
put(proj, TASK_OK, "---\nstatus: in-progress\n---\nFiles:\n- src/ok.py\n")
put(proj, "src/app.py", "1\n2\n3\n4\n5\n")
git(proj, "add", "-A")
git(proj, "commit", "-q", "-m", "base")
git(proj, "checkout", "-q", "-b", "feature")
put(proj, "src/app.py", "1\n2\n30\n4\n5\n")
put(proj, "src/billing/pay.py", "p\n")
git(proj, "add", "-A")
git(proj, "commit", "-q", "-m", "teammate: billing")
git(proj, "checkout", "-q", "main")
put(proj, "src/app.py", "1\n2\n300\n4\n5\n")
git(proj, "commit", "-q", "-am", "mine")
git(proj, "cherry-pick", "feature", agent=True)
put(proj, "src/app.py", "1\n2\n3000\n4\n5\n")
git(proj, "add", "src/app.py")
h = head(proj)
r = run([GIT, "-c", "core.editor=true", "cherry-pick", "--continue"], proj,
        AGENT_ENV)
check("block: an agent's conflicted cherry-pick, concluded with --continue: "
      "refused on its resolution only (src/app.py, not the teammate's "
      "src/billing/pay.py), with no unstage advice (MR-2)",
      r.returncode != 0 and head(proj) == h and "  src/app.py\n" in r.stderr
      and "src/billing/pay.py" not in r.stderr
      and "This is a cherry-pick that stopped on conflicts" in r.stderr
      and "git cherry-pick --abort" in r.stderr
      and "restore --staged" not in r.stderr, r.stderr[-700:])
git(proj, "cherry-pick", "--abort")

# [WP3 fix2 IT-4] dispatch passes the mode to the check: in warn mode the
# merge commit goes through right after the message, so it offers no
# `git merge --abort` (which would then fail) and no "stop and ask".
proj = new_repo()
install(proj, CFG)
harness_commit(proj)
put(proj, TASK_OK, "---\nstatus: in-progress\n---\nFiles:\n- src/ok.py\n")
put(proj, "src/app.py", "base\n")
git(proj, "add", "-A")
git(proj, "commit", "-q", "-m", "base")
git(proj, "checkout", "-q", "-b", "side")
put(proj, "src/app.py", "side\n")
git(proj, "commit", "-q", "-am", "side")
git(proj, "checkout", "-q", "main")
put(proj, "src/app.py", "main\n")
git(proj, "commit", "-q", "-am", "main")
git(proj, "merge", "-q", "side", agent=True)
put(proj, "src/app.py", "resolved\n")
git(proj, "add", "src/app.py")
h = head(proj)
r = git(proj, "commit", "-q", "--no-edit", agent=True)
check("warn: an agent's conflict resolution in an unlisted file lands with "
      "the message, which offers no git merge --abort and no 'stop and ask' "
      "(the commit went through) (IT-4)",
      r.returncode == 0 and head(proj) != h and "This is a merge" in r.stderr
      and "  src/app.py\n" in r.stderr and "git merge --abort" not in r.stderr
      and WARN in r.stderr, r.stderr[-700:])

# --------------------------------------------------------------------------
# [WP3 fix3] Re-review 2 on the installer's remedies (HD-1, HD-2, HD-3,
# HD-5). Each row fails with its change reverted (the step report lists the
# mutants).
print("\n# [WP3 fix3] Every remedy's line is guarded, and the gate-off "
      "re-install names a line that is left (HD-1)")
import shlex                                               # noqa: E402

GUARDED = ("if [ -f .claude/githooks/dispatch ]; then bash "
           ".claude/githooks/dispatch {} || exit 1; fi")
FOREIGN_LINE = re.compile(r"have that hook run `([^`]+)`")
H9_H = ('#!/usr/bin/env sh\nn=$(basename "$0")\n'
        's=$(dirname "$(dirname "$0")")/$n\n[ ! -f "$s" ] && exit 0\n'
        'sh -e "$s" "$@"\nc=$?\nexit $c\n')


def append(path, line):
    with open(path, "a") as fh:
        fh.write(line + "\n")


def person_commit(proj, msg="person"):
    git(proj, "add", "-A")
    return git(proj, "commit", "-q", "-m", msg)


# (a) The documented off switch, after the foreign remedy was followed.
proj = new_repo()
write_hook(hook_path(proj, "pre-commit"), "#!/bin/sh\necho lint-ok\n")
r = install(proj, CFG_BLOCK)
m = FOREIGN_LINE.search(r.stderr)
check("(precondition) a hand-written .git/hooks/pre-commit: the warning gives "
      "the guarded line", m is not None
      and m.group(1) == GUARDED.format("pre-commit"), r.stderr[-500:])
append(hook_path(proj, "pre-commit"), m.group(1) if m else "")
harness_commit(proj)
r = commit_file(proj, "src/agent.py")
check("(precondition) followed, that line runs the check: block refuses an "
      "agent commit of an unlisted file", r.returncode != 0
      and REFUSED in r.stderr, r.stderr[-300:])
git(proj, "rm", "-q", "--cached", "src/agent.py")
r = install(proj, CFG_OFF)
check("hooks.spec_gate_commit: false and a re-install: dispatch is removed, "
      "and a warning names the hook that still mentions it and says to "
      "remove the line (HD-1)",
      not os.path.exists(os.path.join(proj, GIT_HOOK_DISPATCH))
      and ".git/hooks/pre-commit still mentions `.claude/githooks/dispatch "
      "pre-commit`, but the spec gate is off (hooks.spec_gate_commit: false): "
      "remove that line from .git/hooks/pre-commit." in r.stderr,
      r.stderr[-600:])
r = person_commit(proj, "gate off")
r2 = commit_file(proj, "src/after.py")
check("... and with the guarded line left in place, a person's commit (the "
      "one recording the gate-off change) and an agent commit both land "
      "(HD-1)", r.returncode == 0 and r2.returncode == 0,
      r.stderr[-300:] + r2.stderr[-300:])

# (b) A branch cut before the install, with the line in .git/hooks, which
# every branch and worktree shares.
proj = new_repo()
put(proj, "a.txt", "a\n")
git(proj, "add", "a.txt")
git(proj, "commit", "-q", "-m", "a")
git(proj, "branch", "old-feature")
git(proj, "branch", "old-wt")
write_hook(hook_path(proj, "pre-commit"), "#!/bin/sh\necho lint-ok\n")
r = install(proj, CFG_BLOCK)
m = FOREIGN_LINE.search(r.stderr)
append(hook_path(proj, "pre-commit"), m.group(1) if m else "")
harness_commit(proj)
git(proj, "checkout", "-q", "old-feature")
r1 = commit_file(proj, "fix.txt", agent=False)
r2 = commit_file(proj, "fix2.txt")
wt = os.path.join(os.path.dirname(proj), "wt-old")
git(proj, "worktree", "add", "-q", wt, "old-wt")
r3 = commit_file(wt, "fix3.txt", agent=False)
check("on a branch cut before the install, with the foreign remedy followed: "
      "a person's commit and an agent commit land, and so does a person's "
      "commit in a linked worktree on such a branch (HD-1)",
      r1.returncode == 0 and r2.returncode == 0 and r3.returncode == 0,
      r1.stderr[-200:] + r2.stderr[-200:] + r3.stderr[-200:])

# husky 9 (simulated: the wrappers source `h`, which runs .husky/<hook> with
# sh -e), the tracked files the remedy points at.
proj = new_repo()
os.makedirs(os.path.join(proj, ".husky", "_"))
put(proj, ".husky/_/h", H9_H)
for n_ in ("pre-commit", "pre-merge-commit"):
    write_hook(os.path.join(proj, ".husky", "_", n_),
               '#!/usr/bin/env sh\n. "$(dirname "$0")/h"\n')
git(proj, "config", "core.hooksPath", ".husky/_")
r = install(proj)
lines = remedy_lines(r.stderr)
check("(precondition) husky 9: a guarded line per hook, for .husky",
      lines == {n_: GUARDED.format(n_) for n_ in ("pre-commit",
                                                   "pre-merge-commit")}
      and "put the line in .husky/pre-commit and .husky/pre-merge-commit"
      in r.stderr, r.stderr[-600:])
put(proj, ".husky/pre-commit", lines.get("pre-commit", "") + "\n")
r = install(proj)
check("husky 9 with only .husky/pre-commit holding the line: the 'put the "
      "line in' sentence names .husky/pre-merge-commit alone (HD-2)",
      "put the line in .husky/pre-merge-commit, which husky runs" in r.stderr,
      r.stderr[-600:])
put(proj, ".husky/pre-merge-commit", lines.get("pre-merge-commit", "") + "\n")
r = install(proj)
check("... and with both holding it, no 'put the line in' sentence, only the "
      "note that they mention it (HD-2)",
      "put the line in" not in r.stderr
      and ".husky/pre-commit mentions" in r.stderr, r.stderr[-600:])
harness_commit(proj)
r = commit_file(proj, "src/h9.py")
check("(precondition) that line runs: an agent commit of an unlisted file "
      "lands with the warn line", r.returncode == 0 and WARN in r.stderr,
      r.stderr[-300:])
r = install(proj, CFG_OFF)
check("the gate-off re-install names .husky/pre-commit and "
      ".husky/pre-merge-commit as still mentioning the line (HD-1)",
      ".husky/pre-commit still mentions" in r.stderr
      and ".husky/pre-merge-commit still mentions" in r.stderr,
      r.stderr[-600:])
r = person_commit(proj, "gate off")
check("... and a person's commit then lands through husky (HD-1)",
      r.returncode == 0, r.stderr[-300:])

# A symlinked hook this installer did not write.
proj = new_repo()
write_hook(os.path.join(proj, "tools", "lint"), "#!/bin/sh\necho lint\n")
os.symlink(os.path.join("..", "..", "tools", "lint"),
           hook_path(proj, "pre-commit"))
r = install(proj)
m = FOREIGN_LINE.search(r.stderr)
check("a .git/hooks/pre-commit symlink to another hook: the warning gives the "
      "guarded line (HD-1)", "pre-commit is a symlink to" in r.stderr
      and m is not None and m.group(1) == GUARDED.format("pre-commit"),
      r.stderr[-500:])

# A core.hooksPath every repository reads keeps its lines: they serve the
# other repositories, and INST-6 always gave them the guard.
proj = new_repo()
r = install_env(proj, GENV, CFG_OFF)
check("with the gate off, the guarded lines in a global core.hooksPath "
      "directory are not called lines to remove (HD-1)",
      "still mentions" not in r.stderr
      and any(GUARDED.format("pre-commit") in (read(os.path.join(_GHOOKS, n_))
                                               or "")
              for n_ in ("pre-commit",)), r.stderr[-400:])

# A hook manager's config file that still mentions the line.
proj = new_repo()
write_hook(hook_path(proj, "pre-commit"),
           "#!/bin/sh\n# lefthook generated\nlefthook run pre-commit\n")
put(proj, "lefthook.yml", "pre-commit:\n  commands:\n    spec:\n      run: "
    + GUARDED.format("pre-commit") + "\n")
r = install(proj, CFG_OFF)
check("with the gate off, lefthook.yml that mentions the line is named, "
      "not the lefthook hook (HD-1)",
      "lefthook.yml still mentions `.claude/githooks/dispatch pre-commit`"
      in r.stderr and ".git/hooks/pre-commit still mentions" not in r.stderr,
      r.stderr[-400:])
# [WP3 fix4 INST3-2] The mention is one key of a manager's entry: removing
# only that line leaves an entry the tool refuses (lefthook 2.2.1 panics,
# pre-commit 4.6.2 says "Missing required key: entry"), so every commit
# fails. The text names the whole entry.
_flat = " ".join(r.stderr.split())
check("... and says to remove the whole lefthook command that runs it, not "
      "only the line (INST3-2)",
      "remove the whole lefthook command that runs it from lefthook.yml "
      "(each command's name with its `run:` key, not only the line)" in _flat
      and "remove that line from lefthook.yml" not in _flat, r.stderr[-600:])
proj = new_repo()
write_hook(hook_path(proj, "pre-commit"),
           "#!/usr/bin/env bash\n# File generated by pre-commit: "
           "https://pre-commit.com\nexec true\n")
put(proj, ".pre-commit-config.yaml",
    "repos:\n- repo: local\n  hooks:\n  - id: spec-check\n"
    "    name: spec check\n    entry: sh -c '[ ! -f .claude/githooks/"
    "dispatch ] || exec bash .claude/githooks/dispatch pre-commit'\n"
    "    language: system\n    pass_filenames: false\n")
r = install(proj, CFG_OFF)
_flat = " ".join(r.stderr.split())
check("with the gate off, .pre-commit-config.yaml that mentions the line is "
      "named, with the whole hook entry to remove, not only the line "
      "(INST3-2)",
      ".pre-commit-config.yaml still mentions `.claude/githooks/dispatch "
      "pre-commit`" in _flat
      and "remove the whole hook entry that runs it from "
      ".pre-commit-config.yaml (each `- id:` item with that `entry:`, not "
      "only the line)" in _flat
      and "remove that line from" not in _flat, r.stderr[-600:])

# The pre-commit framework runs `entry` without a shell: its guard is sh -c.
proj = new_repo()
write_hook(hook_path(proj, "pre-commit"),
           "#!/usr/bin/env bash\n# File generated by pre-commit: "
           "https://pre-commit.com\nexec true\n")
r = install(proj, CFG_BLOCK)
m = re.search(r"`entry: ([^`]+)`", r.stderr)
argv = shlex.split(m.group(1)) if m else ["false"]
harness_commit(proj)
put(proj, "src/u.py", "u\n")
git(proj, "add", "src/u.py")


def run_entry(env):
    """Run `entry` as the framework does, with no shell; a missing program
    is the framework's 'Executable ... not found', a failed hook."""
    try:
        p = run(argv, proj, env)
        return p.returncode, p.stderr
    except OSError as exc:
        return 127, str(exc)


rc1, err1 = run_entry(AGENT_ENV)
os.remove(os.path.join(proj, GIT_HOOK_DISPATCH))
rc2, err2 = run_entry(BASE_ENV)
check("the pre-commit framework's entry, run as the framework runs it: it "
      "runs dispatch where it exists (block refuses an unlisted agent file) "
      "and exits 0 where it does not (HD-1)",
      rc1 == 1 and REFUSED in err1 and rc2 == 0,
      (argv, rc1, err1[-200:], rc2, err2))

print("\n# [WP3 fix3] How to confirm a mentioned line runs (HD-2)")
# [WP3 fix4 INST3-3] The recipe names a file under the first configured
# prefix: a file outside hooks.spec_gate_commit_prefixes is not checked,
# so it prints nothing and the operator reads a working line as dead.
_pc = new_repo()
write_hook(hook_path(_pc, "pre-commit"),
           "#!/bin/sh\n" + GUARDED.format("pre-commit") + "\n")
r = install(_pc, CFG + "  spec_gate_commit_prefixes: [\"pkg/\", \"src/\"]\n")
_flat = " ".join(r.stderr.split())
check("the confirm recipe names a file under the first configured prefix, "
      "and says a file outside the prefixes is not checked (INST3-3)",
      "commit a file under pkg/ that no task file lists, such as "
      "`pkg/confirm.txt`, from a terminal with `CLAUDECODE=1 git commit`"
      in _flat and "A file outside hooks.spec_gate_commit_prefixes is not "
      "checked, so it prints nothing." in _flat
      and "If that commit lands (in warn mode it does), `git reset --soft "
      "HEAD~1` undoes it." in _flat, r.stderr[-900:])
harness_commit(_pc)
put(_pc, "pkg/confirm.txt", "c\n")
git(_pc, "add", "pkg/confirm.txt")
_cc = git(_pc, "commit", "-q", "-m", "confirm", agent=True)
_r0 = git(_pc, "reset", "-q", "--soft", "HEAD~1")
check("... and following it prints the check's line, and the reset undoes "
      "the commit (INST3-3)",
      _cc.returncode == 0 and "spec check (pre-commit):" in _cc.stderr
      and _r0.returncode == 0
      and git(_pc, "log", "-1", "--format=%s").stdout.strip() == "harness",
      (_cc.returncode, _cc.stderr[-400:]))
# [WP3 fix5 R4-2] A retrofit install: the check exempts what the legacy
# allowlist covers (a retrofit proposes `<dir>/**` for each source
# directory, so `src/**` is usual), and in rollout weeks 1 to 3 it only
# warns, with its own line. The recipe named `src/confirm.txt`, which
# printed nothing, and promised a line the warn week never prints.
RETRO_CFG = """mode: "retrofit"
project:
  name: r-svc
  archetype: service
secrets:
  enabled: false
deps:
  enabled: false
hooks:
  secrets_gate: false
  dependency_gate: false
  spec_gate_commit_mode: warn
commands:
  test: "true"
  lint: "true"
  format: "true"
retrofit:
  spec_strategy: "forward-only"
  legacy_allowlist:
{allow}  retrofit_active: false
  r08_committed: true
"""
_rc = new_repo()
write_hook(hook_path(_rc, "pre-commit"),
           "#!/bin/sh\n" + GUARDED.format("pre-commit") + "\n")
r = install(_rc, RETRO_CFG.format(allow="    - \"src/**\"\n"))
_flat = " ".join(r.stderr.split())
check("retrofit, legacy allowlist src/**: the recipe names a file under the "
      "first prefix the allowlist leaves checked (lib/), says an "
      "allowlisted file is not checked, and names the warn week's own line "
      "(R4-2)",
      r.returncode == 0
      and "commit a file under lib/ that no task file lists, such as "
      "`lib/confirm.txt`" in _flat and "src/confirm.txt" not in _flat
      and "it should print `spec check (pre-commit):` (in retrofit rollout "
      "weeks 1 to 3, .claude/hooks/rollout-schedule.md, where the check only "
      "warns, it prints `the spec check would refuse this commit:` instead)"
      in _flat and "so it prints nothing, nor is one the legacy allowlist "
      "covers." in _flat, r.stderr[-1200:])
harness_commit(_rc)
_wk = read(os.path.join(_rc, ".claude/hooks/rollout-schedule.md")) or ""
put(_rc, "lib/confirm.txt", "c\n")
git(_rc, "add", "lib/confirm.txt")
_cc = git(_rc, "commit", "-q", "-m", "confirm", agent=True)
_r0 = git(_rc, "reset", "-q", "--soft", "HEAD~1")
check("... and following it in the install's first week prints the warn "
      "week's line, and the reset undoes the commit (R4-2)",
      "ROLLOUT_WEEK: 1 " in _wk and _cc.returncode == 0
      and "the spec check would refuse this commit:" in _cc.stderr
      and "  lib/confirm.txt" in _cc.stderr and _r0.returncode == 0
      and git(_rc, "log", "-1", "--format=%s").stdout.strip() == "harness",
      (_cc.returncode, _cc.stderr[-400:]))
# The check reads the allowlist from spec-strategy.md, which a re-install
# keeps once the operator edits it ("locally modified"): the recipe reads
# it there too, not from the config.
_ss = os.path.join(_rc, ".claude/steering/spec-strategy.md")
put(_rc, ".claude/steering/spec-strategy.md", read(_ss).replace(
    "<!-- LEGACY_ALLOWLIST_BEGIN -->\nsrc/**\n",
    "<!-- LEGACY_ALLOWLIST_BEGIN -->\nsrc/**\nlib/**\n"))
r = install(_rc, RETRO_CFG.format(allow="    - \"src/**\"\n"))
_flat = " ".join(r.stderr.split())
put(_rc, "app/confirm.txt", "c\n")
git(_rc, "add", "app/confirm.txt")
_cc = git(_rc, "commit", "-q", "-m", "confirm", agent=True)
git(_rc, "reset", "-q", "--soft", "HEAD~1")
check("retrofit, re-installed after the operator added lib/** to "
      "spec-strategy.md's allowlist (kept as locally modified): the recipe "
      "names app/, which the check polices, and following it prints the "
      "warn week's line (R4-2)",
      "lib/**" in (read(_ss) or "")
      and "such as `app/confirm.txt`" in _flat
      and "the spec check would refuse this commit:" in _cc.stderr
      and "  app/confirm.txt" in _cc.stderr,
      (r.stderr[-800:], _cc.stderr[-300:]))
_rc = new_repo()
write_hook(hook_path(_rc, "pre-commit"),
           "#!/bin/sh\n" + GUARDED.format("pre-commit") + "\n")
r = install(_rc, RETRO_CFG.format(allow="".join(
    f"    - \"{d}/**\"\n" for d in ("src", "lib", "app", "test", "tests"))))
_flat = " ".join(r.stderr.split())
check("retrofit, an allowlist that covers every prefix: no recipe that "
      "prints nothing; it says no commit can confirm the line yet (R4-2)",
      r.returncode == 0 and "confirm.txt" not in _flat
      and "No commit can confirm the pre-commit line yet: "
      "retrofit.legacy_allowlist (.claude/steering/spec-strategy.md) covers "
      "every one of hooks.spec_gate_commit_prefixes" in _flat,
      r.stderr[-1200:])
# [WP3 fix6 RV5-MB-2] One probe name decided "covers every prefix": `*.txt`
# matched src/confirm.txt (a `case` glob's `*` crosses `/`), so the
# installer said no commit could confirm the line while src/confirm.py was
# still checked. It now tries several names under each prefix.
_rc = new_repo()
write_hook(hook_path(_rc, "pre-commit"),
           "#!/bin/sh\n" + GUARDED.format("pre-commit") + "\n")
r = install(_rc, RETRO_CFG.format(allow="    - \"*.txt\"\n"))
_flat = " ".join(r.stderr.split())
check("retrofit, legacy allowlist *.txt: no claim that it covers every "
      "prefix; the recipe names a file it leaves checked, `src/confirm.py` "
      "(RV5-MB-2)",
      r.returncode == 0 and "No commit can confirm" not in _flat
      and "commit a file under src/ that no task file lists, such as "
      "`src/confirm.py`" in _flat and "confirm.txt" not in _flat,
      r.stderr[-1200:])
harness_commit(_rc)
put(_rc, "src/confirm.py", "c\n")
git(_rc, "add", "src/confirm.py")
_cc = git(_rc, "commit", "-q", "-m", "confirm", agent=True)
git(_rc, "reset", "-q", "--soft", "HEAD~1")
check("... and following it prints the warn week's line (RV5-MB-2)",
      _cc.returncode == 0
      and "the spec check would refuse this commit:" in _cc.stderr
      and "  src/confirm.py" in _cc.stderr, (_cc.returncode, _cc.stderr[-400:]))
# Every name tried is covered, but no pattern covers a prefix itself: no
# example, and no claim that nothing can confirm the line.
_rc = new_repo()
write_hook(hook_path(_rc, "pre-commit"),
           "#!/bin/sh\n" + GUARDED.format("pre-commit") + "\n")
# (A line naming a prefix itself, with no `*`, covers no file under it.)
r = install(_rc, RETRO_CFG.format(
    allow="    - \"*confirm*\"\n    - \"*probe\"\n" + "".join(
        f"    - \"{d}/\"\n" for d in ("src", "lib", "app", "test", "tests"))))
_flat = " ".join(r.stderr.split())
check("retrofit, an allowlist that covers every name tried but no prefix: "
      "neither an example nor 'No commit can confirm'; it says to commit a "
      "file the allowlist does not cover (RV5-MB-2)",
      r.returncode == 0 and "No commit can confirm" not in _flat
      and "such as `" not in _flat
      and "To confirm the pre-commit line runs, commit a file under one of "
      "hooks.spec_gate_commit_prefixes that no task file lists and "
      "retrofit.legacy_allowlist (.claude/steering/spec-strategy.md) does "
      "not cover (it covers every name this installer tried), from a "
      "terminal with `CLAUDECODE=1 git commit`" in _flat, r.stderr[-1200:])
harness_commit(_rc)
put(_rc, "src/x.c", "c\n")
git(_rc, "add", "src/x.c")
_cc = git(_rc, "commit", "-q", "-m", "confirm", agent=True)
git(_rc, "reset", "-q", "--soft", "HEAD~1")
check("... and following it with a file the allowlist does not cover prints "
      "the warn week's line (RV5-MB-2)",
      _cc.returncode == 0
      and "the spec check would refuse this commit:" in _cc.stderr
      and "  src/x.c" in _cc.stderr, (_cc.returncode, _cc.stderr[-400:]))
# [WP3 fix6 RV5-MB-3] The installer read the block only where a newline
# came straight after BEGIN and END was present; the check's awk matches a
# marker anywhere on its line and reads to the end of the file without
# END. Trailing whitespace after BEGIN made the installer read an empty
# allowlist and name src/confirm.txt, which the check exempts.
for _label, _edit in (
        ("trailing whitespace after the BEGIN marker",
         lambda t: t.replace("<!-- LEGACY_ALLOWLIST_BEGIN -->\n",
                             "<!-- LEGACY_ALLOWLIST_BEGIN --> \n")),
        ("no END marker",
         lambda t: t.replace("<!-- LEGACY_ALLOWLIST_END -->\n", ""))):
    _rc = new_repo()
    write_hook(hook_path(_rc, "pre-commit"),
               "#!/bin/sh\n" + GUARDED.format("pre-commit") + "\n")
    install(_rc, RETRO_CFG.format(allow="    - \"src/**\"\n"))
    _ss = os.path.join(_rc, ".claude/steering/spec-strategy.md")
    _t0 = read(_ss) or ""
    put(_rc, ".claude/steering/spec-strategy.md", _edit(_t0))
    r = install(_rc, RETRO_CFG.format(allow="    - \"src/**\"\n"))
    _flat = " ".join(r.stderr.split())
    harness_commit(_rc)
    put(_rc, "src/confirm.txt", "c\n")
    git(_rc, "add", "src/confirm.txt")
    _cs = git(_rc, "commit", "-q", "-m", "exempt", agent=True)
    git(_rc, "reset", "-q", "--soft", "HEAD~1")
    git(_rc, "reset", "-q", "src/confirm.txt")
    put(_rc, "lib/confirm.txt", "c\n")
    git(_rc, "add", "lib/confirm.txt")
    _cc = git(_rc, "commit", "-q", "-m", "confirm", agent=True)
    git(_rc, "reset", "-q", "--soft", "HEAD~1")
    check(f"retrofit, spec-strategy.md with {_label}: the recipe reads the "
          f"allowlist as the check does (src/confirm.txt is exempt and prints "
          f"nothing), so it names lib/confirm.txt, whose commit prints the "
          f"warn week's line (RV5-MB-3)",
          _edit(_t0) != _t0 and (read(_ss) or "") == _edit(_t0)
          and "such as `lib/confirm.txt`" in _flat
          and "src/confirm.txt" not in _flat
          and _cs.returncode == 0 and "spec check" not in _cs.stderr
          and "the spec check would refuse this commit:" in _cc.stderr
          and "  lib/confirm.txt" in _cc.stderr,
          (r.stderr[-800:], _cs.stderr[-300:], _cc.stderr[-300:]))
proj = new_repo()
write_hook(hook_path(proj, "pre-commit"),
           "#!/bin/sh\n" + GUARDED.format("pre-commit") + "\n")
write_hook(hook_path(proj, "pre-merge-commit"),
           "#!/bin/sh\n" + GUARDED.format("pre-merge-commit") + "\n")
r = install(proj, CFG_BLOCK)
check("a hook that mentions the line: confirm from a terminal with "
      "`CLAUDECODE=1 git commit`, not through Claude Code (HD-2)",
      "from a terminal with `CLAUDECODE=1 git commit`" in r.stderr
      and "it should print `spec check (pre-commit):`" in r.stderr
      and "make an agent commit" not in r.stderr, r.stderr[-600:])
check("... and no recipe for pre-merge-commit, which no ordinary commit "
      "exercises (HD-2)",
      "No ordinary commit confirms the pre-merge-commit line" in r.stderr
      and "`spec check (pre-merge-commit):`" not in r.stderr,
      r.stderr[-600:])
harness_commit(proj)
put(proj, "src/z.py", "z\n")
git(proj, "add", "src/z.py")
fb = run(["bash", os.path.join(proj, ".claude/hooks/spec-gate-commit.sh")],
         proj, dict(AGENT_ENV, CLAUDE_PROJECT_DIR=proj),
         stdin=json.dumps({"hook_event_name": "PreToolUse",
                           "tool_name": "Bash",
                           "tool_input": {"command": "git commit -m z"}}))
r = run([GIT, "commit", "-q", "-m", "z"], proj, AGENT_ENV)
check("(why) block: through Claude Code the PreToolUse fallback refuses on "
      "the index first, so git never runs the hook; the terminal commit the "
      "warning names does print `spec check (pre-commit):`",
      fb.returncode == 2 and r.returncode != 0
      and "spec check (pre-commit):" in r.stderr, (fb.returncode,
                                                  r.stderr[-300:]))

print("\n# [WP3 fix3] A hook git skips that lacks the line gets the line "
      "too (HD-3)")
proj = new_repo()
os.mkdir(os.path.join(proj, ".githooks"))
git(proj, "config", "core.hooksPath", ".githooks")
write_hook(os.path.join(proj, ".githooks", "pre-commit"),
           "#!/bin/sh\necho 'old lint hook (disabled)'; exit 1\n")
os.chmod(os.path.join(proj, ".githooks", "pre-commit"), 0o644)
r = install(proj)
check("core.hooksPath: a non-executable hook that does not mention the line "
      "gets the line to add, and chmod +x only if its own commands should "
      "run (HD-3)",
      remedy_lines(r.stderr).get("pre-commit") == GUARDED.format("pre-commit")
      and ".githooks/pre-commit is not executable, so git skips it: put the "
      "line in it and chmod +x it only if its own commands should run too"
      in r.stderr
      and "skips it: chmod +x .githooks/pre-commit" not in r.stderr,
      r.stderr[-700:])
proj = new_repo()
write_hook(hook_path(proj, "pre-commit"), "#!/bin/sh\nexit 1\n")
os.chmod(hook_path(proj, "pre-commit"), 0o644)
r = install(proj)
m = FOREIGN_LINE.search(r.stderr)
check("the same for a non-executable .git/hooks/pre-commit, with the guarded "
      "line (HD-1, HD-3)",
      m is not None and m.group(1) == GUARDED.format("pre-commit")
      and "chmod +x it only if its own commands should run too" in r.stderr
      and "It is not executable, so git skips it: chmod +x" not in r.stderr,
      r.stderr[-600:])

print("\n# [WP3 fix3] An empty core.hooksPath, and a symlink to the shim "
      "(HD-5)")
proj = new_repo()
write_hook(hook_path(proj, "pre-commit"), "#!/bin/sh\necho HOOK-RAN >&2\n")
git(proj, "config", "core.hooksPath", "")
put(proj, "a.txt", "a\n")
r = commit_file(proj, "a.txt", agent=False)
check("(why) core.hooksPath set to an empty value: git runs no hook",
      r.returncode == 0 and "HOOK-RAN" not in r.stderr, r.stderr)
os.remove(hook_path(proj, "pre-commit"))
r = install(proj)
check("an empty core.hooksPath: no shim written, and a warning that it turns "
      "every hook off, not 'ok' (HD-5)",
      not os.path.exists(hook_path(proj, "pre-commit"))
      and "not installed (hooks-off" in r.stdout
      and "core.hooksPath is set to an empty value, which turns off every git "
      "hook in this repository" in r.stderr, (r.stdout[-300:],
                                              r.stderr[-400:]))
proj = new_repo()
os.makedirs(os.path.join(proj, "tools"))
write_hook(os.path.join(proj, "tools", "shim"), SHIM)
os.symlink(os.path.join("..", "..", "tools", "shim"),
           hook_path(proj, "pre-commit"))
r = install(proj)
check("a .git/hooks/pre-commit symlink to an exact copy of the shim: a note, "
      "no 'does not run from it' (HD-5)",
      "does not run from it" not in r.stderr
      and "which holds bootstrap-install's shim; left alone" in r.stdout,
      (r.stdout[-300:], r.stderr[-300:]))
harness_commit(proj)
r = commit_file(proj, "src/sym.py")
check("... and git does run it: an agent commit of an unlisted file lands "
      "with the warn line", r.returncode == 0 and WARN in r.stderr,
      r.stderr[-300:])

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

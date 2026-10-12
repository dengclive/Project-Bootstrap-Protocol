"""[WP3 / D2] The spec traceability check, .claude/githooks/spec-check.sh, and
its two fallbacks: spec-gate-commit.sh (PreToolUse, shell) and
_spec_gate_commit in gates.py (SDK).

What is pinned here, by behaviour on real installs and real git:
  * the rule: Files: blocks (exact path or a directory entry ending in "/"),
    the pre-WP3 mention rule for task files with no Files: block and for
    INDEX.md, the enforced prefixes from config;
  * task files are read from the INDEX, so an untracked or unstaged task
    file does not count, and the refusal says so by name;
  * the refusal names the task file to edit and never says "Run /spec-new";
  * exit 2 means "not traced" and nothing else (errors exit 3);
  * the git commit forms: a minimal pre-commit / pre-merge-commit hook runs
    the check on the REAL staged set, so add&&commit, commit -a, pathspec
    commits and merges are all seen;
  * the fallbacks: warn vs block, deferral to an installed git hook;
  * the SDK port gives the same rc and the same text as the shell check;
  * retrofit: the warn-week note only when the rule fails, the per-file
    legacy allowlist.
  * [WP3 build 01-d2] the critic's step-1 deltas: no fallback refusal
    outside a work tree (1b), block fails closed on a check error with a
    "not a spec refusal" text (1c), a staged task file is named first (1d),
    parallel in-progress tasks narrowed by what the change lists (D2 ii),
    the Edit-tool remedy (1e), mode-neutral warn text (1f), DEFAULTS as the
    mode's only default (1g), no head(1) in the retrofit variant (1k), every
    mode row sets its mode (1m), and pins for the surviving mutants (1n).

Run: python3 tests/test_spec_check.py
"""
import asyncio
import importlib.util
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "lib"))
import templates  # noqa: E402

BIN = os.path.join(ROOT, "bin", "bootstrap-install")
BASH = shutil.which("bash")
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


if not BASH or not GIT:
    print("SUITE SKIPPED: needs bash and git")
    sys.exit(0)

# The emitted gates.py imports the SDK; the gate logic does not need it.
_stub = types.ModuleType("claude_agent_sdk")


class _StubHookMatcher:
    def __init__(self, matcher=None, hooks=None, timeout=None):
        self.matcher, self.hooks, self.timeout = matcher, hooks or [], timeout


_stub.HookMatcher = _StubHookMatcher
sys.modules["claude_agent_sdk"] = _stub

BASE = """project:
  name: sc
  archetype: cli
secrets:
  enabled: false
deps:
  enabled: false
hooks:
  secrets_gate: false
  dependency_gate: false
{extra}commands:
  test: "true"
  lint: "true"
  format: "true"
  ci_local: "true"
workflow:
  implementer_isolation: "none"
"""
RETRO = """mode: "retrofit"
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
commands:
  test: "true"
  lint: "true"
  format: "true"
retrofit:
  spec_strategy: "forward-only"
  legacy_allowlist:
    - "src/legacy/**"
  retrofit_active: false
  r08_committed: true
"""

TMP = tempfile.mkdtemp(prefix="spec-check-")
# [WP3 critic 1j] Hermetic: git never searches above the scratch directory,
# so a TMPDIR inside some work tree (a dotfiles repository in $HOME) cannot
# turn the "outside a git work tree" rows into rows about that repository.
# Set for this process too: the SDK port runs git in-process.
CEILING = os.path.dirname(TMP)
os.environ["GIT_CEILING_DIRECTORIES"] = CEILING
# [WP3 fix1 TP-03] No developer git config reaches the rows: a global
# core.hooksPath (a hook manager) or commit.gpgsign turned this suite red.
# GIT_CONFIG_GLOBAL (git 2.32+) names an empty file; HOME and
# XDG_CONFIG_HOME cover older git. Set for this process too: the SDK port
# runs git in-process.
GCFG = os.path.join(TMP, "gitconfig-global")
open(GCFG, "w").close()
os.makedirs(os.path.join(TMP, "xdg"))
os.environ.update(GIT_CONFIG_GLOBAL=GCFG, GIT_CONFIG_NOSYSTEM="1", HOME=TMP,
                  XDG_CONFIG_HOME=os.path.join(TMP, "xdg"))
ENV = dict(os.environ)
for _k in [k for k in ENV if k.startswith(("CLAUDE", "GIT_"))]:
    del ENV[_k]
ENV.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           GIT_CONFIG_NOSYSTEM="1", HOME=TMP, TMPDIR=TMP,
           XDG_CONFIG_HOME=os.path.join(TMP, "xdg"), GIT_CONFIG_GLOBAL=GCFG,
           GIT_CEILING_DIRECTORIES=CEILING)


def sh(cmd, cwd, env=None, inp=None):
    p = subprocess.run(cmd, cwd=cwd, env=env or ENV, input=inp,
                       capture_output=True, text=True, shell=isinstance(cmd, str),
                       executable=BASH if isinstance(cmd, str) else None)
    return p.returncode, p.stdout, p.stderr


def install(name, cfg, init=()):
    d = os.path.join(TMP, "tpl-" + name)
    os.makedirs(d)
    sh([GIT, "init", "-q", "-b", "main", *init], d)
    cp = os.path.join(TMP, name + ".yaml")
    with open(cp, "w") as fh:
        fh.write(cfg)
    rc, out, err = sh([sys.executable, BIN, "-c", cp, "-C", d], d)
    if rc != 0:
        print(out[-2000:], err[-2000:])
        raise SystemExit(f"install {name} failed rc={rc}")
    return d


_n = [0]


def fresh(tpl):
    """A copy of an installed template with the harness committed."""
    _n[0] += 1
    d = os.path.join(TMP, f"r{_n[0]}")
    shutil.copytree(tpl, d, symlinks=True)
    # Rows here own their git hooks: an installer that writes the spec
    # check's shims (the git-hook lens) would otherwise make every
    # fallback row a deferral row.
    for h in ("pre-commit", "pre-merge-commit"):
        try:
            os.remove(os.path.join(d, ".git", "hooks", h))
        except FileNotFoundError:
            pass
    sh("git add -A && git commit -qm harness", d)
    return d


def write(d, rel, text):
    p = os.path.join(d, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="") as fh:
        fh.write(text)


def task(d, rel, files=None, status="in-progress", body="", stage=True):
    fm = f"---\nid: {Path(rel).stem}\nstatus: {status}\n---\n" if status else ""
    blk = ("Files:\n" + "".join(f"- {f}\n" for f in files)) if files is not None else ""
    write(d, rel, fm + body + blk)
    if stage:
        sh([GIT, "add", "-f", rel], d)


def stage(d, *paths):
    for p in paths:
        if not os.path.exists(os.path.join(d, p)):
            write(d, p, "x\n")
        sh([GIT, "add", "-f", "--", p], d)


# [WP3 fix2 CRIT-1, MR-3] Every verdict (exit 0 or 2) ends the check's
# stdout with its end line; chk() and chk_at() take it off, so the rows below
# read the paths alone, and record a verdict that lacked it. A row near the
# end requires that list to be empty.
END = templates.SPEC_CHECK_END
NO_END = []
# The git-hook shim the installer writes: the only hook the fallback defers
# to [WP3 fix2 IT-1].
SHIM = templates.TEMPLATES["git_hook_shim"]({})


def strip_end(rc, out, what):
    if rc in (0, 2):
        tail = END + "\n"
        if out.endswith(tail):
            return out[:-len(tail)]
        NO_END.append((what, rc, out[-200:]))
    return out


def chk(d, *args, env=None, inp=None):
    rc, out, err = sh([BASH, os.path.join(d, templates.SPEC_CHECK_PATH),
                       *args], d, env=env, inp=inp)
    return rc, strip_end(rc, out, (d, args)), err


T1 = ".claude/specs/f/tasks/f-T01.md"
T2 = ".claude/specs/f/tasks/f-T02.md"

# [WP3 critic 1m] Each fixture names its mode: no row depends on the
# DEFAULTS value, so changing that one line moves only the rows that pin it.
WARN = "  spec_gate_commit_mode: warn\n"
GF = install("gf", BASE.format(extra=WARN))
GB = install("gb", BASE.format(extra="  spec_gate_commit_mode: block\n"))
SDK = install("sdk", 'gate_substrate: "sdk-callable"\n' + BASE.format(
    extra=WARN))
PFX = install("pfx", BASE.format(extra=WARN + "  spec_gate_commit_prefixes:\n"
                                       "    - \"pkg/\"\n"
                                       "    - \"internal/api/\"\n"))
RF = install("rf", RETRO.replace("  dependency_gate: false\n",
                                 "  dependency_gate: false\n" + WARN))

spec = importlib.util.spec_from_file_location(
    "gates_sc", os.path.join(SDK, ".claude", "sdk_gates", "gates.py"))
gates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gates)


def sdk_check(d, prefixes=templates.SPEC_GATE_DEFAULT_PREFIXES, **kw):
    old = os.environ.get("CLAUDE_PROJECT_DIR")
    try:
        return asyncio.run(gates._spec_check(Path(d), tuple(prefixes), **kw))
    finally:
        if old is not None:
            os.environ["CLAUDE_PROJECT_DIR"] = old


def parity(label, d, *args):
    """The shell check and the SDK port: same rc, same message."""
    rc, out, err = chk(d, *args)
    src, smsg, smiss = sdk_check(d)
    check(f"parity: {label}: shell rc == SDK rc ({rc})", rc == src,
          f"shell={rc} sdk={src}")
    check(f"parity: {label}: same message",
          err.rstrip("\n") == smsg, f"\nshell:\n{err}\nsdk:\n{smsg}")
    return rc, out, err


try:
    # ================================================================== #
    print("\n== emission ==")
    body = open(os.path.join(GF, templates.SPEC_CHECK_PATH)).read()
    check("spec-check.sh is emitted, executable, and parses",
          os.access(os.path.join(GF, templates.SPEC_CHECK_PATH), os.X_OK)
          and sh([BASH, "-n", os.path.join(GF, templates.SPEC_CHECK_PATH)],
                 GF)[0] == 0)
    check("the default prefixes render as one single-quoted word",
          "PREFIXES='src/ lib/ app/ test/ tests/'" in body)
    # [WP3 fix2] An ERR trap is a `trap ... ERR` line: CHERRY_PICK_HEAD,
    # which the check now reads (MR-2), holds the letters "ERR".
    check("no `set -e`, `set -u` or ERR trap in the check (exit 2 is only a "
          "refusal)", "set -e" not in body and "set -u" not in body
          and not re.search(r"\btrap\b[^\n]*\bERR\b", body))
    check("no jq or python3 in the check",
          "jq " not in body and "python3" not in body)
    allbodies = body + open(os.path.join(
        GF, ".claude/hooks/spec-gate-commit.sh")).read()
    check("neither the check nor the fallback says 'Run /spec-new'",
          "Run /spec-new" not in allbodies)
    check("the check is not registered in settings.json (not a hook)",
          "spec-check.sh" not in open(
              os.path.join(GF, ".claude/settings.json")).read())
    gfb = open(os.path.join(GF, ".claude/hooks/spec-gate-commit.sh")).read()
    gbb = open(os.path.join(GB, ".claude/hooks/spec-gate-commit.sh")).read()
    check("the fallback carries the configured mode (warn, block)",
          "SPEC_GATE_MODE=warn" in gfb and "SPEC_GATE_MODE=block" in gbb)
    check("warn mode makes the fallback advisory (header posture 0); block "
          "keeps it fail-closed (posture 1)",
          "\nFAIL_CLOSED=0\n" in gfb and "\nFAIL_CLOSED=1\n" not in gfb
          and "\nFAIL_CLOSED=1\n" in gbb
          and "\nFAIL_CLOSED=0\n" not in gbb)
    pb = open(os.path.join(PFX, templates.SPEC_CHECK_PATH)).read()
    check("configured prefixes reach the check",
          "PREFIXES='pkg/ internal/api/'" in pb)
    st = open(os.path.join(PFX, ".claude/steering/structure.md")).read()
    check("structure.md names the configured prefixes and the key",
          "`pkg/` `internal/api/`" in st
          and "hooks.spec_gate_commit_prefixes" in st)
    rc_cfg = json.loads(json.dumps(gates.RESOLVED_CONFIG))
    check("RESOLVED_CONFIG carries the mode and the prefixes",
          rc_cfg.get("hooks") == {"spec_gate_commit_mode": "warn",
                                  "spec_gate_commit_prefixes":
                                  list(templates.SPEC_GATE_DEFAULT_PREFIXES)})
    # [WP3 critic 1g] DEFAULTS is the mode's ONLY default: with the key
    # unset, flipping that one value moves dispatch, the PreToolUse fallback
    # and the SDK module's RESOLVED_CONFIG together, in both directions.
    import defaults as _defaults
    from minyaml import load_yaml as _ly
    _was = _defaults.DEFAULTS["hooks"]["spec_gate_commit_mode"]
    _seen = {}
    try:
        for _m in ("block", "warn"):
            _defaults.DEFAULTS["hooks"]["spec_gate_commit_mode"] = _m
            _c, _e = _defaults.resolve_config(_ly(
                'gate_substrate: "sdk-callable"\n' + BASE.format(extra="")))
            _seen[_m] = (
                f"\nMODE={_m} " in templates.TEMPLATES["git_hook_dispatch"](_c),
                f"\nSPEC_GATE_MODE={_m} " in templates.TEMPLATES["hook"](
                    "spec-gate-commit", _c),
                f'"spec_gate_commit_mode": "{_m}"' in
                templates.TEMPLATES["sdk_gates"](_c), not _e)
    finally:
        _defaults.DEFAULTS["hooks"]["spec_gate_commit_mode"] = _was
    check("DEFAULTS alone sets the mode of dispatch, the fallback and the "
          "SDK module (flipped both ways, key unset)",
          all(all(v) for v in _seen.values()) and len(_seen) == 2, _seen)

    # ================================================================== #
    print("\n== the rule (greenfield, shell == SDK) ==")
    d = fresh(GF)
    rc, out, err = parity("harness only (nothing enforced)", d)
    check("harness commit passes", rc == 0 and out == "" and err == "")

    stage(d, "src/a.py")
    rc, out, err = parity("unlisted, no task file", d)
    check("unlisted src/a.py with no task file -> 2, stdout lists it",
          rc == 2 and out == "src/a.py\n", (rc, out))
    check("no-task remedy names /spec-decompose and the task path, not "
          "/spec-new", "/spec-decompose <slug>" in err
          and ".claude/specs/<slug>/tasks/<id>.md" in err
          and "/spec-new" not in err, err)

    task(d, T1, ["src/a.py"], stage=False)
    rc, out, err = parity("listed only in an UNTRACKED task file", d)
    check("an untracked task file does not count (index read) and is named",
          rc == 2 and "Not counted, because the index does not have them"
          in err and "  " + T1 in err, err)

    sh([GIT, "add", T1], d)
    rc, out, err = parity("listed in a staged task file", d)
    check("listed in a staged task file -> 0", rc == 0, err)

    sh("git commit -qm t1", d)
    stage(d, "src/b.py")
    with open(os.path.join(d, T1), "a") as fh:
        fh.write("- src/b.py\n")
    rc, out, err = parity("entry added but not staged", d)
    check("an unstaged edit to a task file does not count, and is named",
          rc == 2 and "src/b.py" in out and "  " + T1 in err, err)
    check("the refusal names the in-progress task and the exact lines",
          f"To trace them, edit {T1} (status: in-progress) with the Edit "
          f"tool: add these lines under its \"Files:\" line" in err
          and "\n- src/b.py\n" in err, err)
    sh([GIT, "add", T1], d)
    check("staging the task file clears it", chk(d)[0] == 0)

    print("\n-- directory entries and strict entries --")
    d = fresh(GF)
    task(d, T1, ["src/auth/"])
    stage(d, "src/auth/login.py", "src/auth/sub/x.py")
    rc, out, err = parity("directory entry src/auth/", d)
    check("src/auth/ covers src/auth/login.py and src/auth/sub/x.py",
          rc == 0, err)
    stage(d, "src/authz.py")
    rc, out, err = parity("src/auth/ vs src/authz.py", d)
    check("src/auth/ does not cover src/authz.py",
          rc == 2 and out == "src/authz.py\n", (rc, out))

    d = fresh(GF)
    task(d, T1, ["src/auth"])
    stage(d, "src/auth/login.py")
    rc, out, err = parity("entry without trailing slash", d)
    check("an entry without '/' is a file: src/auth does not cover "
          "src/auth/login.py", rc == 2, err)

    d = fresh(GF)
    task(d, T1, ["a.py", "./src/b.py", "`src/c.py`"])
    stage(d, "src/a.py", "src/b.py", "src/c.py")
    rc, out, err = parity("bare basename, ./ and backticks in a Files block",
                          d)
    check("in a Files block a bare name, ./path and `path` cover nothing",
          rc == 2 and out == "src/a.py\nsrc/b.py\nsrc/c.py\n", (rc, out))

    d = fresh(GF)
    task(d, T1, ["src/x.py"], body="Touches src/a.py too.\n")
    stage(d, "src/a.py")
    rc, out, err = parity("prose mention in a file WITH a Files block", d)
    check("a file with a Files block is held to it: prose does not count",
          rc == 2, err)

    print("\n-- the pre-WP3 format still passes --")
    d = fresh(GF)
    task(d, T1, None, body="Implement the parser in a.py and src/b.py.\n")
    stage(d, "src/pkg/a.py", "src/b.py")
    rc, out, err = parity("legacy task file (no Files block)", d)
    check("legacy file: a bare-name mention and a path mention cover "
          "(3d866f4 rule)", rc == 0, err)
    stage(d, "src/data.py")
    rc, out, err = parity("legacy word boundary", d)
    check("legacy rule keeps S-3: 'a.py' does not cover data.py",
          rc == 2 and out == "src/data.py\n", (rc, out))
    check("a legacy task file is named with the 'add a Files: line' wording",
          'add a line that is exactly "Files:"' in err, err)

    d = fresh(GF)
    task(d, T1, None, body="Touches other/__init__.py only.\n")
    stage(d, "src/pkg/__init__.py")
    rc, out, err = parity("legacy mention of the basename after a '/'", d)
    check("legacy rule: 'other/__init__.py' does not cover "
          "src/pkg/__init__.py (a '/' is not a left boundary)",
          rc == 2 and out == "src/pkg/__init__.py\n", (rc, out))

    d = fresh(GF)
    task(d, ".claude/specs/.draft/tasks/d-T01.md", ["src/a.py"])
    task(d, ".claude/specs/f/tasks/.f-T01.md", ["src/a.py"])
    stage(d, "src/a.py")
    rc, out, err = parity("task files under a dot-named slug or file", d)
    check("a task file under a dot-named slug, or dot-named itself, covers "
          "nothing", rc == 2 and out == "src/a.py\n", (rc, out))

    d = fresh(GF)
    write(d, ".claude/specs/INDEX.md", "| slug | status |\n| f | covers "
          "src/a.py |\n")
    stage(d, ".claude/specs/INDEX.md", "src/a.py")
    rc, out, err = parity("INDEX.md mention", d)
    check("a staged INDEX.md row naming the path covers it (PRD:767)",
          rc == 0, err)

    d = fresh(GF)
    task(d, T1, None, body="## Files\n- src/a.py\n")
    stage(d, "src/a.py")
    rc, out, err = parity("'## Files' heading", d)
    check("'## Files' is not a Files block, so the file is legacy and its "
          "mention covers", rc == 0, err)

    d = fresh(GF)
    write(d, T1, "---\r\nstatus: in-progress\r\n---\r\nFiles:\r\n"
          "- src/a.py\r\n")
    write(d, T2, "")
    sh([GIT, "add", "-f", T1, T2], d)
    stage(d, "src/a.py")
    rc, out, err = parity("CRLF task file next to an empty one", d)
    check("CRLF line ends are tolerated; an empty task file shifts nothing",
          rc == 0, err)

    print("\n-- which task file the refusal names --")
    # The task files are COMMITTED in these rows: a task file staged in the
    # same commit is named first (rule 2, rows below).
    d = fresh(GF)
    task(d, T1, ["src/x.py"])
    task(d, T2, ["src/y.py"])
    sh("git commit -qm tasks", d)
    stage(d, "src/a.py")
    rc, out, err = parity("two in-progress tasks", d)
    check("two in-progress tasks, nothing else of the change listed: both "
          "listed as candidates",
          rc == 2 and "Candidate task files (status: in-progress):" in err
          and "  " + T1 in err and "  " + T2 in err
          and "To trace them, edit the task file this change belongs to "
          "with the Edit tool" in err, err)
    # [D2 ii] Parallel tasks, one per worktree: the task whose Files: block
    # lists another file of this change is the one being worked on.
    stage(d, "src/y.py")
    rc, out, err = parity("two in-progress tasks, the change lists T2's file",
                          d)
    check("two in-progress tasks: the one whose Files: block lists another "
          "file of the change is named",
          rc == 2 and out == "src/a.py\n" and f"edit {T2} (status: "
          f"in-progress, and its Files: block lists other files of this "
          f"change) with the Edit tool" in err
          and "Candidate task files" not in err, err)
    stage(d, "src/x.py")
    rc, out, err = parity("two in-progress tasks, the change lists both", d)
    check("... and when the change lists files of both, both are candidates",
          rc == 2 and "Candidate task files (status: in-progress, each "
          "listing other files of this change):" in err
          and "  " + T1 in err and "  " + T2 in err, err)

    d = fresh(GF)
    task(d, T1, ["src/x.py"])
    task(d, T2, ["src/lib/"])
    task(d, ".claude/specs/f/tasks/f-T03.md", ["src/z.py"], status="planned")
    sh("git commit -qm tasks", d)
    wt = os.path.join(d, ".claude", "worktrees", "agent-2")
    sh(f"git worktree add -q -b wt2 '{wt}'", d)
    write(wt, "src/lib/util.py", "x\n")
    write(wt, "src/extra.py", "x\n")
    sh("git add src/lib/util.py src/extra.py", wt)
    rc, out, err = chk(wt)
    src_, smsg, _ = sdk_check(wt)
    check("in an implementer worktree with two in-progress tasks, the check "
          "names the worktree's task (its directory entry covers the rest of "
          "the change), shell == SDK",
          rc == 2 and out == "src/extra.py\n" and f"edit {T2} (status: "
          f"in-progress, and its Files: block lists" in err
          and src_ == 2 and smsg == err.rstrip("\n"), (err, smsg))

    d = fresh(GF)
    task(d, T1, ["src/x.py"], status="done")
    task(d, T2, ["src/y.py"])
    sh("git commit -qm tasks", d)
    task(d, T1, ["src/x.py"], status="done", body="Done.\n")
    stage(d, "src/a.py")
    rc, out, err = parity("a task file staged in this commit", d)
    check("a task file staged in the same commit is named first, even marked "
          "done, over the in-progress one (critic 1d)",
          rc == 2 and f"edit {T1} (staged in this commit) with the Edit tool"
          in err, err)
    task(d, T2, ["src/y.py"], body="More.\n")
    rc, out, err = parity("two task files staged in this commit", d)
    check("... two staged task files are the candidates",
          rc == 2 and "Candidate task files (staged in this commit):" in err
          and "  " + T1 in err and "  " + T2 in err, err)

    d = fresh(GF)
    task(d, T1, ["src/x.py"], status="planned")
    task(d, T2, None, status="done", body="old\n")
    sh("git commit -qm tasks", d)
    stage(d, "src/a.py")
    rc, out, err = parity("one open task with a Files block", d)
    check("no in-progress task: the only open task with a Files block is "
          "named", f"edit {T1} (the only open task with a Files: block)" in err,
          err)

    d = fresh(GF)
    task(d, T1, ["src/x.py"], status="done")
    sh("git commit -qm tasks", d)
    stage(d, "src/a.py")
    rc, out, err = parity("every task done", d)
    check("every task done: the no-open-task remedy names the Write tool",
          "No open task file exists" in err
          and "create one with the Write tool" in err
          and "by hand" not in err, err)

    d = fresh(GF)
    write(d, T1, '---\nstatus: "in-progress"\n---\nFiles:\n- src/x.py\n')
    sh([GIT, "add", "-f", T1], d)
    sh("git commit -qm t1", d)
    stage(d, "src/a.py")
    rc, out, err = parity("quoted status", d)
    check("a quoted status: \"in-progress\" is read",
          "(status: in-progress)" in err, err)
    check("the remedy: the Edit tool, and stop and ask when the edit is "
          "refused, never another way to write the file (critic 1e)",
          "with the Edit tool" in err and "If Claude Code refuses the edit, "
          "stop and ask; do not write the task file another way (a shell "
          "redirect or a script)." in err, err)

    print("\n-- the changed set --")
    d = fresh(GF)
    task(d, T1, ["src/a.py"])
    stage(d, "src/a.py")
    sh("git commit -qm a", d)
    sh([GIT, "mv", "src/a.py", "src/b.py"], d)
    with open(os.path.join(d, T1), "a") as fh:
        fh.write("- src/b.py\n")
    sh([GIT, "add", T1], d)
    rc, out, err = parity("rename, both sides listed", d)
    check("a rename is two paths; both listed -> 0", rc == 0, err)
    task(d, T1, ["src/b.py"])
    rc, out, err = parity("rename, old side unlisted", d)
    check("a rename whose old path is unlisted -> 2 naming the old path",
          rc == 2 and out == "src/a.py\n", (rc, out))

    d = fresh(GF)
    stage(d, "src/café.py")
    rc, out, err = parity("non-ASCII path, unlisted", d)
    check("non-ASCII src/café.py is policed (it escaped at 3d866f4)",
          rc == 2 and "café.py" in out, (rc, out))
    task(d, T1, ["src/café.py"])
    rc, out, err = parity("non-ASCII path, listed", d)
    check("non-ASCII path listed -> 0", rc == 0, err)

    d = fresh(GF)
    task(d, T1, ["src/my file.py"])
    stage(d, "src/my file.py")
    rc, out, err = parity("path with a space", d)
    check("a path with a space, listed -> 0", rc == 0, err)

    d = fresh(GF)
    stage(d, "pkg/m.py", "README.md", ".claude/notes.md")
    check("paths outside the prefixes are not policed", chk(d)[0] == 0)

    print("\n-- --files and --task (the wrappers' entry) --")
    d = fresh(GF)
    task(d, T1, ["src/a.py"])
    task(d, T2, ["src/b.py"], status="planned")
    sh("git commit -qm tasks", d)
    rc, out, err = chk(d, "--files", "src/a.py", "docs/x.md", "src/z.py")
    check("--files: only the enforced, unlisted path is refused",
          rc == 2 and out == "src/z.py\n", (rc, out, err))
    rc, out, err = chk(d, "--files", "-", inp="src/a.py\nsrc/b.py\n")
    check("--files - reads a newline list from stdin", rc == 0, (rc, err))
    rc, out, err = chk(d, "-z", "--files", "-", inp="src/a.py\0src/q.py\0")
    check("-z --files - reads a NUL list", rc == 2 and out == "src/q.py\n",
          (rc, out))
    rc, out, err = chk(d, "--task", T1, "--files", "src/b.py")
    check("--task: a path listed only in ANOTHER task is refused, naming "
          "the given task", rc == 2 and f"edit {T1} (the task given to this "
          f"check)" in err, err)
    src, smsg, _ = sdk_check(d, changed=["src/b.py"], task=T1)
    check("--task parity with the SDK port", src == 2
          and smsg == err.rstrip("\n"), smsg)
    rc, out, err = chk(d, "--task", ".claude/specs/f/tasks/nope.md",
                       "--files", "src/a.py")
    check("--task naming a file not in the index -> 3, not 2", rc == 3, err)
    # [critic 1n] Pins on --files / --task input handling (N07, N10-N12).
    write(d, ".claude/specs/INDEX.md", "| slug | note |\n| f | src/b.py |\n")
    sh([GIT, "add", "-f", ".claude/specs/INDEX.md"], d)
    rc, out, err = chk(d, "--files", "src/b.py")
    check("(control) INDEX.md's mention covers src/b.py without --task",
          rc == 0, err)
    rc, out, err = chk(d, "--task", T1, "--files", "src/b.py")
    src_, smsg, _ = sdk_check(d, changed=["src/b.py"], task=T1)
    check("--task: INDEX.md's mention does NOT cover (only that task file "
          "may; PRD:1528), shell == SDK", rc == 2 and out == "src/b.py\n"
          and src_ == 2, (rc, out, src_))
    rc, out, err = chk(d, "--files", "-", inp="src/a.py\nsrc/q.py")
    check("--files -: a last line with no newline is still read",
          rc == 2 and out == "src/q.py\n", (rc, out))
    rc, out, err = chk(d, "-z", "--files", "-", inp="src/a.py\0src/q.py")
    check("-z --files -: a last record with no NUL is still read",
          rc == 2 and out == "src/q.py\n", (rc, out))
    rc, out, err = chk(d, "--files", "./src/z.py", "./src/a.py")
    src_, smsg, _ = sdk_check(d, changed=["./src/z.py", "./src/a.py"])
    check("--files: a leading ./ is stripped, so ./src/z.py is policed and "
          "./src/a.py is covered, shell == SDK", rc == 2
          and out == "src/z.py\n" and src_ == 2
          and smsg == err.rstrip("\n"), (rc, out, err, smsg))

    print("\n-- errors exit 3, never 2 --")
    nogit = os.path.join(TMP, "nogit")
    os.makedirs(nogit)
    rc, out, err = sh([BASH, os.path.join(GF, templates.SPEC_CHECK_PATH),
                       "--files", "src/a.py"], nogit)
    check("outside a git work tree -> 3", rc == 3 and "git" in err, (rc, err))
    rc, out, err = chk(fresh(GF), "--bogus")
    check("an unknown argument -> 3", rc == 3, (rc, err))

    print("\n-- no jq, no python3 --")
    nb = os.path.join(TMP, "nobin")
    os.makedirs(nb)
    # Exactly what the check needs: no jq, no python3, and no tr, cat or
    # head (the retrofit suite's no-jq PATH has no tr).
    for tool in ("bash", "git", "awk", "sed", "grep", "mktemp", "rm",
                 "dirname", "mkdir", "date"):
        w = shutil.which(tool)
        if w:
            os.symlink(w, os.path.join(nb, tool))
    env2 = dict(ENV, PATH=nb)
    d = fresh(GF)
    task(d, T1, ["src/a.py"])
    stage(d, "src/a.py", "src/b.py")
    rc, out, err = chk(d, env=env2)
    check("with only bash git awk sed grep mktemp rm dirname mkdir date on "
          "PATH the check still decides (listed passes, unlisted refused)",
          rc == 2 and out == "src/b.py\n", (rc, out, err))

    print("\n-- prefixes from config --")
    d = fresh(PFX)
    stage(d, "src/a.py")
    check("custom prefixes: src/ is no longer policed", chk(d)[0] == 0)
    stage(d, "internal/api/h.go")
    rc, out, err = chk(d)
    check("custom prefixes: internal/api/h.go is policed",
          rc == 2 and out == "internal/api/h.go\n", (rc, out))
    rc2, msg2, _ = sdk_check(d, prefixes=("pkg/", "internal/api/"))
    check("custom prefixes: SDK port agrees", rc2 == 2
          and msg2 == err.rstrip("\n"))

    # ================================================================== #
    print("\n== the real staged set: git commit forms (minimal hook) ==")
    # A stand-in for the installer's shim + dispatch: block semantics, so a
    # refusal is visible as a failed commit. What is under test is that the
    # check sees what git is about to record, in each form. It names its
    # hook to the check as dispatch does (BOOTSTRAP_GIT_HOOK): inside
    # pre-merge-commit the merge's parents come from GITHEAD_<oid>.
    HOOK = ("#!/bin/sh\nBOOTSTRAP_GIT_HOOK=${0##*/} bash "
            ".claude/githooks/spec-check.sh --staged >/dev/null"
            "\nrc=$?\n[ \"$rc\" -eq 2 ] && exit 1\nexit 0\n")

    def hooked(tpl=GF):
        d = fresh(tpl)
        for h in ("pre-commit", "pre-merge-commit"):
            p = os.path.join(d, ".git", "hooks", h)
            with open(p, "w") as fh:
                fh.write(HOOK)
            os.chmod(p, 0o755)
        return d

    def head(d):
        return sh([GIT, "rev-parse", "HEAD"], d)[1].strip()

    d = hooked()
    h0 = head(d)
    write(d, "src/a.py", "x\n")
    rc, _, err = sh("git add src/a.py && git commit -qm a", d)
    check("add&&commit (one call), unlisted -> refused, HEAD unmoved",
          rc != 0 and head(d) == h0 and "src/a.py" in err, err)
    task(d, T1, ["src/a.py"], stage=False)
    rc, _, err = sh("git add -A && git commit -qm a", d)
    check("add -A && commit with the task file in the same add -> lands",
          rc == 0 and head(d) != h0, err)

    h1 = head(d)
    write(d, "src/a.py", "y\n")
    write(d, "src/b.py", "x\n")
    sh([GIT, "add", "src/b.py"], d)
    sh("git commit -qm b --no-verify", d)
    h1 = head(d)
    write(d, "src/b.py", "y\n")
    rc, _, err = sh("git commit -qam ab", d)
    check("commit -a with an unlisted tracked file -> refused",
          rc != 0 and head(d) == h1 and "src/b.py" in err, err)
    with open(os.path.join(d, T1), "a") as fh:
        fh.write("- src/b.py\n")
    rc, _, err = sh("git commit -qam ab", d)
    check("commit -a also stages the tracked task file's edit -> lands",
          rc == 0 and head(d) != h1, err)

    h2 = head(d)
    write(d, "src/c.py", "x\n")
    sh([GIT, "add", "src/c.py"], d)
    with open(os.path.join(d, T1), "a") as fh:
        fh.write("- src/c.py\n")
    sh([GIT, "add", T1], d)
    rc, _, err = sh("git commit -qm c -- src/c.py", d)
    check("pathspec commit: the task edit staged in the index but outside "
          "the pathspec is NOT recorded, so it does not count -> refused",
          rc != 0 and head(d) == h2, err)
    rc, _, err = sh(f"git commit -qm c -- src/c.py {T1}", d)
    check("pathspec commit naming the task file too -> lands",
          rc == 0 and head(d) != h2, err)

    print("\n-- merges --")
    # [WP3 fix1, operator decision 2026-10-06 (1)] A merge is checked on its
    # OWN changes: the paths where the merged result differs from every
    # parent ([WP3 fix2 MR-1] since fix round 2, from git's automatic merge
    # result). A branch's own file is not re-checked, so a merge of other
    # people's work never reads their files as untraced (review SC-1); an
    # agent's commits were checked when they were made, and a person's never
    # are (re-review RR-1).
    def shared_base(d, task_files):
        """T1 lists `task_files`; src/shared.py (5 lines, unlisted) is in
        the base, so both sides can change it in different lines."""
        task(d, T1, task_files)
        write(d, "src/shared.py", "1\n2\n3\n4\n5\n")
        sh("git add -A && git commit -qm base --no-verify", d)

    d = hooked()
    task(d, T1, ["src/m.py"])
    sh("git commit -qm t1", d)
    sh("git checkout -qb B1 && mkdir -p src && echo x > src/b1.py && git add src/b1.py && "
       "git commit -qm b1 --no-verify && git checkout -q main", d)
    h0 = head(d)
    rc, _, err = sh("git merge --no-ff -q -m m B1", d)
    check("merge --no-ff of a branch's own unlisted file -> lands: the "
          "merge's own changes are none (decision 2026-10-06 (1))",
          rc == 0 and head(d) != h0, err)

    # [WP3 fix2 MR-1] The merge's own changes are judged against git's
    # AUTOMATIC merge result: a file both sides changed in different lines,
    # which git merged on its own, is no one's resolution. The every-parent
    # rule refused it, with a remedy that called it one.
    d = hooked()
    shared_base(d, ["src/m.py"])
    sh("git checkout -qb S && sed -i.b 's/^5$/50/' src/shared.py && "
       "git commit -qam s --no-verify && git checkout -q main && "
       "sed -i.b 's/^1$/10/' src/shared.py && git commit -qam m --no-verify",
       d)
    h0 = head(d)
    rc, _, err = sh("git merge --no-ff -q -m m S", d)
    check("a merge where both sides changed an unlisted file in different "
          "lines, which git merged on its own -> lands: not the merge's own "
          "change (MR-1)", rc == 0 and head(d) != h0 and "spec check" not in err,
          err)
    # A conflict the agent resolves IS the merge's own change.
    d = hooked()
    shared_base(d, ["src/m.py"])
    sh("git checkout -qb S && sed -i.b 's/^5$/50/' src/shared.py && "
       "git commit -qam s --no-verify && git checkout -q main && "
       "sed -i.b 's/^5$/500/' src/shared.py && git commit -qam m --no-verify",
       d)
    h0 = head(d)
    sh("git merge -q S", d)
    write(d, "src/shared.py", "1\n2\n3\n4\n5000\n")
    sh([GIT, "add", "src/shared.py"], d)
    rc, _, err = sh("git commit -q --no-edit", d)
    check("a conflict resolved in an unlisted file -> refused by pre-commit, "
          "and named as a resolution",
          rc != 0 and head(d) == h0 and "src/shared.py" in err
          and "(a conflict resolution, or an edit made during the merge)"
          in err, err)
    check("... the refusal in a merge never says to unstage (that drops the "
          "other side's change); it offers git merge --abort, then stop and "
          "ask (review SC-1)",
          "This is a merge" in err and "git merge --abort" in err
          and "restore --staged" not in err and "rm --cached" not in err
          and "Do not unstage a file from it" in err, err)
    mh = os.path.exists(os.path.join(d, ".git", "MERGE_HEAD"))
    check("after the refusal the merge is left in progress (MERGE_HEAD), "
          "so 'edit, stage, commit' concludes it", mh)
    rc_m, _, err_m = chk(d)
    src_m, smsg_m, _ = sdk_check(d)
    check("while the merge is in progress the shell check and the SDK port "
          "read MERGE_HEAD alike: same rc and text, the merge's own path only",
          rc_m == 2 and src_m == 2 and smsg_m == err_m.rstrip("\n")
          and "src/shared.py" in err_m and "This is a merge" in smsg_m,
          (err_m, smsg_m))
    with open(os.path.join(d, T1), "a") as fh:
        fh.write("- src/shared.py\n")
    sh([GIT, "add", T1], d)
    rc, _, err = sh("git commit -qm m", d)
    check("editing and staging the task file then `git commit` (pre-commit) "
          "concludes the merge", rc == 0 and len(sh(
              [GIT, "rev-list", "--parents", "-n1", "HEAD"], d)[1].split())
          == 3, err)
    # [WP3 fix2 MR-1] A conflict resolved to one side's text is still a
    # resolution (the every-parent rule let it through: it equals a parent).
    d = hooked()
    shared_base(d, ["src/m.py"])
    sh("git checkout -qb S && sed -i.b 's/^5$/50/' src/shared.py && "
       "git commit -qam s --no-verify && git checkout -q main && "
       "sed -i.b 's/^5$/500/' src/shared.py && git commit -qam m --no-verify",
       d)
    sh("git merge -q S", d)
    sh("git checkout --theirs -- src/shared.py && git add src/shared.py", d)
    rc_t, out_t, err_t = chk(d)
    src_t, smsg_t, _ = sdk_check(d)
    check("a conflict resolved by taking the other side's text is kept (git "
          "left it conflicted), shell == SDK (MR-1)",
          rc_t == 2 and out_t == "src/shared.py\n" and src_t == 2
          and smsg_t == err_t.rstrip("\n"), (rc_t, out_t, err_t, smsg_t))
    # [WP3 fix2 MR-1] A path git left conflicted counts even where the index
    # equals the automatic result: a rename/rename conflict resolved by
    # keeping both names (the automatic tree holds both, so only the
    # conflicted list names src/c.py; the every-parent rule let it through,
    # since it equals the branch's file).
    d = hooked()
    task(d, T1, ["src/m.py"])
    write(d, "src/a.py", "".join(f"{i}\n" for i in range(1, 31)))
    sh("git add -A && git commit -qm base --no-verify", d)
    sh("git checkout -qb R && git mv src/a.py src/c.py && "
       "git commit -qm r --no-verify && git checkout -q main && "
       "git mv src/a.py src/b.py && git commit -qm m --no-verify", d)
    sh("git merge -q R", d)
    sh("git add src/b.py src/c.py && git rm -q --cached src/a.py", d)
    rc_r, out_r, err_r = chk(d)
    src_r, smsg_r, _ = sdk_check(d)
    check("a rename/rename conflict resolved by keeping both names: the "
          "conflicted src/c.py is kept though the index equals git's "
          "automatic result there; shell == SDK (MR-1)",
          rc_r == 2 and out_r == "src/c.py\n" and src_r == 2
          and smsg_r == err_r.rstrip("\n"), (rc_r, out_r, err_r, smsg_r))
    sh("git merge --abort", d)
    # [WP3 fix2 MR-1] git before 2.38 has no `merge-tree --write-tree`: the
    # every-parent rule, and the text says what it then holds. A PATH shim
    # answers `git version` and runs the real git for everything else.
    shim_dir = os.path.join(TMP, "oldgit")
    os.makedirs(shim_dir, exist_ok=True)
    with open(os.path.join(shim_dir, "git"), "w") as fh:
        fh.write('#!/bin/sh\nif [ "$1" = version ]; then echo "git version '
                 '2.37.9"; exit 0; fi\nexec %s "$@"\n' % shlex.quote(GIT))
    os.chmod(os.path.join(shim_dir, "git"), 0o755)
    old_path = dict(ENV, PATH=shim_dir + os.pathsep + ENV.get("PATH", ""))
    d = hooked()
    shared_base(d, ["src/m.py"])
    sh("git checkout -qb S && sed -i.b 's/^5$/50/' src/shared.py && "
       "git commit -qam s --no-verify && git checkout -q main && "
       "sed -i.b 's/^1$/10/' src/shared.py && git commit -qam m --no-verify",
       d)
    sh("git merge --no-ff --no-commit -q S", d)
    rc_a, out_a, _ = chk(d)
    rc_o, out_o, err_o = chk(d, env=old_path)
    _pp = os.environ["PATH"]
    os.environ["PATH"] = old_path["PATH"]
    try:
        src_o, smsg_o, _ = sdk_check(d)
    finally:
        os.environ["PATH"] = _pp
    check("git 2.37 (PATH shim): the every-parent rule, so the clean two-"
          "sided file is held, and the text says a file both sides changed "
          "is among them; shell == SDK; with this git the same merge passes",
          rc_a == 0 and rc_o == 2 and out_o == "src/shared.py\n"
          and "or a file both sides changed)" in err_o and src_o == 2
          and smsg_o == err_o.rstrip("\n"), (rc_a, rc_o, err_o, smsg_o))
    sh("git merge --abort", d)

    d = hooked()
    task(d, T1, ["src/b2.py", "src/m1.py"])
    sh("git commit -qm t1", d)
    sh("git checkout -qb B2 && mkdir -p src && echo x > src/b2.py && git add src/b2.py && "
       "git commit -qm b2 --no-verify && git checkout -q main && "
       "echo x > src/m1.py && git add src/m1.py && git commit -qm m1", d)
    # main's own unlisted change, committed with --no-verify, must not be
    # blamed on the merge: the hook sees only the merge's own changes.
    sh("echo x > src/zz.py && git add src/zz.py && git commit -qm zz "
       "--no-verify", d)
    h0 = head(d)
    rc, _, err = sh("git merge -q -m m B2", d)
    check("a default (diverged) merge: main's own unlisted src/zz.py is not "
          "blamed on it", rc == 0 and head(d) != h0, err)

    # The upstream merge of review SC-1: a teammate's files under src/,
    # pulled into an agent's diverged branch, are not the agent's to trace.
    d = hooked()
    task(d, T1, ["src/a.py"])
    write(d, "src/a.py", "a\n")
    sh("git add -A && git commit -qm base", d)
    sh(["git", "clone", "-q", "--bare", ".", "../origin-sc1.git"], d)
    sh("git remote add origin ../origin-sc1.git", d)
    mate = os.path.join(TMP, "mate-sc1")
    sh(["git", "clone", "-q", os.path.join(TMP, "origin-sc1.git"), mate],
       TMP)
    sh("mkdir -p src/billing && echo i > src/billing/invoice.py && "
       "echo t > src/billing/tax.py && git add -A && git commit -qm bill && "
       "git push -q origin main", mate)
    sh("echo a2 >> src/a.py && git commit -qam listed", d)
    h0 = head(d)
    rc, _, err = sh("git pull -q --no-rebase --no-edit origin main", d)
    check("an agent's merge of upstream work (git pull --no-rebase) lands, "
          "and the teammate's files are in it (review SC-1)",
          rc == 0 and head(d) != h0
          and os.path.isfile(os.path.join(d, "src/billing/invoice.py"))
          and "restore --staged" not in err, err)

    d = hooked()
    task(d, T1, ["src/m.py"])
    sh("git commit -qm t1", d)
    sh("git checkout -qb B3 && mkdir -p src && echo x > src/b3.py && git add src/b3.py && "
       "git commit -qm b3 --no-verify && git checkout -q main", d)
    h0 = head(d)
    rc, _, err = sh("git merge --no-ff --no-commit B3 && git commit -qm m",
                    d)
    check("merge --no-commit && commit of a branch's own file: pre-commit "
          "reads MERGE_HEAD and checks the merge's own changes -> lands",
          rc == 0 and head(d) != h0, err)
    h0 = head(d)
    sh("git checkout -qb B4 && echo y > src/b4.py && git add src/b4.py && "
       "git commit -qm b4 --no-verify && git checkout -q main", d)
    rc, _, err = sh("git merge --no-ff --no-commit B4 && echo e > src/extra.py "
                    "&& git add src/extra.py && git commit -qm m", d)
    check("an edit made during a merge (src/extra.py, in neither parent) "
          "is the merge's own change -> refused, and only it is named",
          rc != 0 and head(d) == h0 and "src/extra.py" in err
          and "src/b4.py" not in err, err)
    sh("git merge --abort", d)

    d = hooked()
    task(d, T1, ["src/other.py"])
    write(d, "src/app.py", "base\n")
    sh("git add -A && git commit -qm base --no-verify", d)
    sh("git checkout -qb C && echo branch > src/app.py && echo x > src/c.py "
       "&& git add -A && git commit -qm c --no-verify && git checkout -q main "
       "&& echo main > src/app.py && git commit -qam m --no-verify", d)
    h0 = head(d)
    rc, _, _ = sh("git merge -q C", d)
    write(d, "src/app.py", "resolved\n")
    sh([GIT, "add", "src/app.py"], d)
    rc, _, err = sh("git commit -q --no-edit", d)
    check("a conflict resolution commit: pre-commit refuses the unlisted "
          "resolution src/app.py, and not the branch's own src/c.py",
          rc != 0 and head(d) == h0 and "src/app.py" in err
          and "src/c.py" not in err, err)
    rc, _, err = sh("git merge --continue", d, env=dict(ENV, GIT_EDITOR=":"))
    check("git merge --continue fires pre-commit too -> refused",
          rc != 0 and head(d) == h0, err)

    print("\n-- other forms --")
    d = hooked()
    h0 = head(d)
    rc, _, err = sh("git commit -q --amend --no-edit", d)
    check("commit --amend with nothing new staged: empty staged set -> lands "
          "(an amend's own delta is not re-checked)", rc == 0, err)

    d = os.path.join(TMP, "unborn")
    shutil.copytree(GF, d, symlinks=True)
    for h in ("pre-commit", "pre-merge-commit"):
        p = os.path.join(d, ".git", "hooks", h)
        with open(p, "w") as fh:
            fh.write(HOOK)
        os.chmod(p, 0o755)
    write(d, "src/a.py", "x\n")
    rc, _, err = sh("git add -A && git commit -qm first", d)
    check("initial commit (unborn HEAD) with an unlisted src file -> refused",
          rc != 0, err)
    task(d, T1, ["src/a.py"], stage=False)
    rc, _, err = sh("git add -A && git commit -qm first", d)
    check("initial commit with the task file -> lands", rc == 0, err)

    d = hooked()
    task(d, T1, ["src/main.py"])
    sh("git commit -qm t1", d)
    wt = os.path.join(d, ".claude", "worktrees", "wt-1")
    sh(f"git worktree add -q -b wt1 '{wt}'", d)
    write(wt, "src/w.py", "x\n")
    rc, _, err = sh("git add src/w.py && git commit -qm w", wt)
    check("a linked worktree under .claude/worktrees: the common-dir hook "
          "reads the WORKTREE's index -> refused", rc != 0
          and "src/w.py" in err, err)
    with open(os.path.join(wt, T1), "a") as fh:
        fh.write("- src/w.py\n")
    rc, _, err = sh(f"git add {T1} && git commit -qm w", wt)
    check("the worktree's own task file edit clears it (not main's copy)",
          rc == 0, err)

    # ================================================================== #
    print("\n== the PreToolUse fallback (shell) and the SDK twin ==")

    def fallback(d, cmd="git commit -m x"):
        payload = json.dumps({"hook_event_name": "PreToolUse",
                              "tool_name": "Bash",
                              "tool_input": {"command": cmd}})
        return sh([BASH, os.path.join(d, ".claude/hooks/spec-gate-commit.sh")],
                  d, env=dict(ENV, CLAUDE_PROJECT_DIR=d), inp=payload)

    def sdk_gate(d, mode, cmd="git commit -m x"):
        os.environ["CLAUDE_PROJECT_DIR"] = d
        g = gates._GATE_FACTORIES["spec-gate-commit"](
            {"hooks": {"spec_gate_commit_mode": mode}})
        cwd = os.getcwd()
        try:
            os.chdir(d)
            return asyncio.run(g({"tool_input": {"command": cmd}}, "t", None))
        finally:
            os.chdir(cwd)

    def log_tail(d):
        p = os.path.join(d, ".claude", "logs", "hooks.log")
        return open(p).read().splitlines()[-1] if os.path.exists(p) else ""

    for tpl, mode in ((GF, "warn"), (GB, "block")):
        d = fresh(tpl)
        stage(d, "src/a.py")
        rc, out, err = fallback(d)
        res = sdk_gate(d, mode)
        _, msg, _ = chk(d)
        hso = res.get("hookSpecificOutput", {})
        if mode == "warn":
            ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] \
                if out.strip() else ""
            check("fallback, warn: exit 0, the check's text plus the mode "
                  "as additionalContext, with no 'for now' (critic 1f)",
                  rc == 0 and msg.rstrip("\n") in ctx
                  and "hooks.spec_gate_commit_mode is warn, so this commit "
                  "was allowed" in ctx and "for now" not in ctx,
                  (rc, out, err))
            check("SDK, warn: the same additionalContext, no deny",
                  hso.get("additionalContext") == ctx
                  and "permissionDecision" not in hso, res)
            check("fallback, warn: logs 'WARN unreferenced: src/a.py'",
                  log_tail(d).endswith(
                      "spec-gate-commit WARN unreferenced: src/a.py"), log_tail(d))
        else:
            check("fallback, block: exit 2, the check's text plus 'Commit "
                  "refused'", rc == 2 and msg.rstrip("\n") in err
                  and "Commit refused." in err, (rc, err))
            check("SDK, block: deny with the same reason",
                  hso.get("permissionDecision") == "deny"
                  and hso.get("permissionDecisionReason") == err.rstrip("\n"),
                  res)
            check("fallback, block: logs 'BLOCK unreferenced: src/a.py'",
                  log_tail(d).endswith(
                      "spec-gate-commit BLOCK unreferenced: src/a.py"), log_tail(d))
        # Deferral: an executable pre-commit that IS the installer's shim.
        # [WP3 fix2 IT-1] Byte for byte: a hook that merely carries the
        # marker (an edited shim; here one that exits at once) runs no
        # check, so the fallback must not go quiet for it.
        hp = os.path.join(d, ".git", "hooks", "pre-commit")
        with open(hp, "w") as fh:
            fh.write("#!/bin/sh\n# bootstrap-protocol:git-hook-shim v1\n"
                     "exit 0\n")
        os.chmod(hp, 0o755)
        rc_ed, out_ed, _ = fallback(d)
        res_ed = sdk_gate(d, mode)
        check(f"fallback and SDK, {mode}: an executable hook that carries "
              f"the shim marker but is not the shim (edited: it exits at "
              f"once) is not deferred to; the check runs (IT-1)",
              ((rc_ed == 2 and res_ed.get("hookSpecificOutput", {}).get(
                  "permissionDecision") == "deny") if mode == "block" else
               (out_ed.strip() != "" and res_ed != {})), (rc_ed, res_ed))
        with open(hp, "w") as fh:
            fh.write(SHIM)
        os.chmod(hp, 0o644)
        rc_nx, out_nx, _ = fallback(d)
        check(f"fallback, {mode}: a NON-executable shim is not "
              f"deferred to (git would not run it)",
              (rc_nx == 2) if mode == "block" else (out_nx.strip() != ""))
        os.chmod(hp, 0o755)
        rc, out, err = fallback(d)
        check(f"fallback, {mode}: defers to an installed git hook: exit 0, "
              f"silent, logged", rc == 0 and out == "" and err == ""
              and "deferred to the git pre-commit hook" in log_tail(d),
              (rc, out, err, log_tail(d)))
        check(f"SDK, {mode}: defers to an installed git hook",
              sdk_gate(d, mode) == {})

    # [WP3 critic 1n, N01/N14/X2/X5] The deferral needs the SHIM's marker:
    # a hook manager's own executable pre-commit (lefthook, husky) does not
    # run the check, so the fallback must not defer to it.
    for tpl, mode in ((GF, "warn"), (GB, "block")):
        d = fresh(tpl)
        stage(d, "src/a.py")
        hp = os.path.join(d, ".git", "hooks", "pre-commit")
        with open(hp, "w") as fh:
            fh.write("#!/bin/sh\n# lefthook's own hook\nexit 0\n")
        os.chmod(hp, 0o755)
        rc, out, err = fallback(d)
        res = sdk_gate(d, mode)
        hso = res.get("hookSpecificOutput", {})
        if mode == "block":
            ok = (rc == 2 and "Commit refused." in err
                  and hso.get("permissionDecision") == "deny")
        else:
            ok = (rc == 0 and "not listed" in out
                  and "not listed" in hso.get("additionalContext", ""))
        check(f"fallback and SDK, {mode}: an executable pre-commit WITHOUT "
              f"the shim marker is not deferred to; the check runs", ok,
              (rc, out[:200], err[:200], res))
    # [N02] Where git looks for hooks (--git-path hooks), not .git/hooks: a
    # marked shim left in .git/hooks while core.hooksPath points elsewhere
    # (husky) never runs, so it must not make the fallback defer.
    d = fresh(GB)
    stage(d, "src/a.py")
    hp = os.path.join(d, ".git", "hooks", "pre-commit")
    with open(hp, "w") as fh:
        fh.write(SHIM)
    os.chmod(hp, 0o755)
    os.makedirs(os.path.join(d, ".husky"))
    sh([GIT, "config", "core.hooksPath", ".husky"], d)
    rc, out, err = fallback(d)
    res = sdk_gate(d, "block")
    check("fallback and SDK, block: a marked shim in .git/hooks that git "
          "does not run (core.hooksPath elsewhere) is not deferred to",
          rc == 2 and res.get("hookSpecificOutput", {}).get(
              "permissionDecision") == "deny", (rc, err[:200], res))
    shutil.copy(hp, os.path.join(d, ".husky", "pre-commit"))
    rc, out, err = fallback(d)
    check("... and a marked shim where core.hooksPath points IS deferred to",
          rc == 0 and out == "" and err == "" and sdk_gate(d, "block") == {},
          (rc, out, err))

    d = fresh(GB)
    write(d, "src/a.py", "x\n")
    rc, out, err = fallback(d, "git add src/a.py && git commit -m x")
    check("fallback limit (documented): add&&commit with an empty index "
          "passes the PreToolUse fallback", rc == 0, (rc, err))

    # [WP3 critic 1b] No repository: nothing to check, on both substrates,
    # in BLOCK mode (PRD:474 lets a project run without git; at 3d866f4
    # these passed). Measured before the fix: rc 2 'BLOCKED (fail-closed):
    # spec-check.sh could not run (exit 3)', and an SDK deny.
    d = os.path.join(TMP, "nogit-block")
    shutil.copytree(GB, d, symlinks=True)
    shutil.rmtree(os.path.join(d, ".git"))
    os.makedirs(os.path.join(d, "svc"))
    # The rows below are vacuous if git finds some repository above TMP
    # (the SDK would then check that one's empty index and allow anyway).
    _inside = [subprocess.run([GIT, "rev-parse", "--is-inside-work-tree"],
                              cwd=d, env=e, capture_output=True).returncode
               for e in (os.environ, ENV)]
    check("(fixture) the no-repository copy is outside every work tree, for "
          "this process (the SDK runs git here) and for its children",
          all(rc != 0 for rc in _inside), _inside)
    for cmd in ("git init && git add -A && git commit -m init",
                "git -C svc commit -m x", "git commit -m x"):
        try:
            os.remove(os.path.join(d, ".claude", "logs", "hooks.log"))
        except FileNotFoundError:
            pass
        rc, out, err = fallback(d, cmd)
        res = sdk_gate(d, "block", cmd)
        check(f"no git work tree, block: {cmd!r} -> shell exit 0 and logged, "
              f"SDK allows", rc == 0 and err == "" and res == {}
              and log_tail(d).endswith("spec-gate-commit: not inside a git "
                                       "work tree; nothing to check"),
              (rc, err, res, log_tail(d)))

    # [WP3 critic 1c] A check that cannot run, in block mode: refused
    # (fail-closed), saying it is not a spec refusal; same words on both
    # substrates. A corrupt index makes the real check exit 3 on both.
    d = fresh(GB)
    stage(d, "src/a.py")
    with open(os.path.join(d, ".git", "index"), "wb") as fh:
        fh.write(b"DIRC\0\0\0\2garbage")
    rc, out, err = fallback(d)
    res = sdk_gate(d, "block")
    why = res.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    want = ("BLOCKED (fail-closed): the spec check could not run (exit 3), "
            "which is not a spec refusal: spec check: git diff --cached "
            "failed:")
    tail = ("Stop and tell the operator: hooks.spec_gate_commit: false and a "
            "re-install turn the check off.")
    check("block, the check cannot run (corrupt index): the fallback refuses "
          "with 'not a spec refusal' and the way to turn it off",
          rc == 2 and err.startswith(want) and tail in err, (rc, err))
    check("... and the SDK denies with the same words",
          why.startswith(want) and why.endswith(tail), why)

    d = fresh(GB)
    stage(d, "src/a.py")
    os.remove(os.path.join(d, templates.SPEC_CHECK_PATH))
    rc, out, err = fallback(d)
    check("fallback, block: a missing spec-check.sh fails closed (exit 2), "
          "not as a spec refusal",
          rc == 2 and "spec-check.sh is missing" in err
          and "not a spec refusal" in err, (rc, err))
    d = fresh(GF)
    stage(d, "src/a.py")
    os.remove(os.path.join(d, templates.SPEC_CHECK_PATH))
    rc, out, err = fallback(d)
    check("fallback, warn: a missing spec-check.sh is a notice, exit 0",
          rc == 0 and "could not run" in out, (rc, out))

    # ================================================================== #
    print("\n== retrofit ==")
    rb = open(os.path.join(RF, templates.SPEC_CHECK_PATH)).read()
    rgb = open(os.path.join(RF, ".claude/hooks/spec-gate-commit.sh")).read()
    check("retrofit check carries the allowlist and rollout reads",
          "LEGACY_ALLOWLIST_BEGIN" in rb and "ROLLOUT_WEEK" in rb)
    check("retrofit spec-gate-commit.sh no longer says 'would have blocked' "
          "without evaluating", "would have blocked" not in rgb)
    check("the greenfield check has no retrofit section",
          "LEGACY_ALLOWLIST_BEGIN" not in body)

    def week(d, n):
        p = os.path.join(d, ".claude", "hooks", "rollout-schedule.md")
        t = open(p).read()
        import re as _re
        open(p, "w").write(_re.sub(r"ROLLOUT_WEEK:\s*\d+",
                                   f"ROLLOUT_WEEK: {n}", t))

    d = fresh(RF)
    week(d, 1)
    task(d, T1, ["src/a.py"])
    stage(d, "src/a.py")
    rc, out, err = chk(d)
    check("retrofit week 1, LISTED file: exit 0 and SILENT (was 'would have "
          "blocked')", rc == 0 and err == "", (rc, err))
    d = fresh(RF)
    week(d, 1)
    stage(d, "README.md")
    rc, out, err = chk(d)
    check("retrofit week 1, docs-only commit: exit 0 and silent",
          rc == 0 and err == "", (rc, err))
    stage(d, "src/b.py")
    rc, out, err = chk(d)
    check("retrofit week 1, unlisted: exit 0 with the evaluated note",
          rc == 0 and err.startswith("(retrofit warn-only week 1; see "
                                     ".claude/hooks/rollout-schedule.md) "
                                     "the spec check would refuse")
          and "src/b.py" in err, (rc, err))
    rc, out, err = fallback(d)
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] \
        if out.strip() else ""
    check("retrofit fallback relays the warn-week note to the model",
          rc == 0 and "would refuse" in ctx, (rc, out))
    for wk in (2, 3):
        week(d, wk)
        rc, out, err = chk(d)
        check(f"retrofit week {wk} warns too (RETROFIT.md:1253-1254): exit 0 "
              f"with the note", rc == 0 and f"(retrofit warn-only week {wk};"
              in err, (rc, err))
    # [critic 1k] the week is read with bash alone: no head(1) on PATH.
    week(d, 1)
    nh = os.path.join(TMP, "nohead")
    os.makedirs(nh)
    for tool in ("bash", "git", "awk", "sed", "grep", "mktemp", "rm",
                 "dirname", "mkdir", "date"):
        w = shutil.which(tool)
        if w:
            os.symlink(w, os.path.join(nh, tool))
    rc, out, err = chk(d, env=dict(ENV, PATH=nh))
    check("retrofit week 1 with no head(1) on PATH: still week 1 (exit 0, "
          "the note), not the week-4 refusal", rc == 0
          and "(retrofit warn-only week 1;" in err, (rc, err))
    rs = os.path.join(d, ".claude", "hooks", "rollout-schedule.md")
    rs_text = open(rs).read()
    import re as _re
    open(rs, "w").write(_re.sub(r"ROLLOUT_WEEK:\s*\d+", "", rs_text))
    rc, out, err = chk(d)
    check("retrofit with no ROLLOUT_WEEK line: week 4, so an unlisted file "
          "-> 2 (every failed read falls toward enforce)",
          rc == 2 and out == "src/b.py\n", (rc, out))
    open(rs, "w").write(rs_text)
    week(d, 4)
    rc, out, err = chk(d)
    check("retrofit week 4, unlisted -> 2", rc == 2 and out == "src/b.py\n",
          (rc, out))
    # The allowlisted path must sit UNDER an enforced prefix, or the row
    # is vacuous (a mutant that restored all-or-nothing survived when it
    # used legacy/x.py, which no prefix polices).
    stage(d, "src/legacy/x.py")
    rc, out, err = chk(d)
    check("retrofit: an allowlisted path is exempt PER FILE (RETROFIT.md "
          "R8.A.3); only src/b.py is named", rc == 2 and out == "src/b.py\n",
          (rc, out))
    sh([GIT, "reset", "-q", "--", "src/b.py"], d)
    check("retrofit: an allowlisted-only commit -> 0", chk(d)[0] == 0)

    # [critic 1n, X3] The retrofit-active exemption is observable only where
    # a prefix polices something under .claude/ (with the default prefixes
    # nothing there is enforced, and the old row was vacuous).
    RFC = install("rfc", RETRO.replace(
        "  dependency_gate: false\n", "  dependency_gate: false\n" + WARN
        + "  spec_gate_commit_prefixes:\n    - \"src/\"\n"
        "    - \".claude/steering/\"\n"))
    d = fresh(RFC)
    week(d, 4)
    stage(d, ".claude/steering/x.md")
    rc, out, err = chk(d)
    check("(control) not retrofit-active: a policed .claude/steering/x.md "
          "is refused", rc == 2 and out == ".claude/steering/x.md\n",
          (rc, out))
    sp = os.path.join(d, ".claude", ".retrofit-state.json")
    st = json.load(open(sp))
    st["retrofit_active"] = True
    json.dump(st, open(sp, "w"), indent=2)
    check("retrofit-active, .claude/-only commit -> 0", chk(d)[0] == 0)
    stage(d, "src/b.py")
    rc, out, err = chk(d)
    check("retrofit-active, .claude/ plus src/ -> the exemption does not "
          "apply; both named", rc == 2
          and out == ".claude/steering/x.md\nsrc/b.py\n", (rc, out))

    # ================================================================== #
    # [WP3 fix1] The review's spec-check findings (fix round 1). Each row
    # below fails with its fix reverted; the reverts and mutants are listed
    # in the step report (f1-spec-check).
    print("\n== [WP3 fix1] review findings ==")

    def chk_at(d, cwd, *args, env=None, inp=None):
        """The check of project `d`, run from `cwd`."""
        rc, out, err = sh([BASH, os.path.join(d, templates.SPEC_CHECK_PATH),
                           *args], cwd, env=env, inp=inp)
        return rc, strip_end(rc, out, (d, cwd, args)), err

    def fallback_at(d, cwd, cmd="git commit -m x"):
        """The PreToolUse fallback of project `d`, run from `cwd` (a hook
        runs in the session's directory)."""
        payload = json.dumps({"hook_event_name": "PreToolUse",
                              "tool_name": "Bash",
                              "tool_input": {"command": cmd}})
        return sh([BASH, os.path.join(d, ".claude/hooks/spec-gate-commit.sh")],
                  cwd, env=dict(ENV, CLAUDE_PROJECT_DIR=d), inp=payload)

    def run_b(cmd, cwd, env=None):
        """Bytes out: a name that is not UTF-8 reaches the output as is."""
        p = subprocess.run(cmd, cwd=cwd, env=env or ENV, capture_output=True)
        return p.returncode, p.stdout, p.stderr

    def sdk_gate_cfg(d, cfg, cmd="git commit -m x"):
        os.environ["CLAUDE_PROJECT_DIR"] = d
        g = gates._GATE_FACTORIES["spec-gate-commit"](cfg)
        cwd = os.getcwd()
        try:
            os.chdir(d)
            return asyncio.run(g({"tool_input": {"command": cmd}}, "t", None))
        finally:
            os.chdir(cwd)

    print("\n-- run from a directory below the top (TP-05) --")
    d = fresh(GB)
    task(d, T1, ["src/a.py"])
    stage(d, "src/a.py")
    srcdir = os.path.join(d, "src")
    rc1, _, err1 = chk_at(d, srcdir, "--files", "src/a.py")
    rc2, _, err2 = chk_at(d, srcdir, "--staged")
    check("spec-check.sh run from src/: a listed file passes, with --files "
          "and --staged (paths are the project's, not the cwd's)",
          rc1 == 0 and rc2 == 0, (rc1, err1, rc2, err2))
    rc, out, err = fallback_at(d, srcdir)
    check("block, no git hook: the PreToolUse fallback run from src/ passes "
          "a listed file", rc == 0 and err == "", (rc, err))
    stage(d, "src/b.py")
    rc, out, err = fallback_at(d, srcdir)
    check("... and refuses an unlisted one, naming only it",
          rc == 2 and "  src/b.py\n" in err and "  src/a.py\n" not in err,
          (rc, err))

    print("\n-- a project below the repository top (operator decision "
          "2026-10-06 (2); SC-4, SDKP-2, INST-2, CR-7) --")

    def install_below(name, cfg, pkg):
        top = os.path.join(TMP, "mono-" + name)
        os.makedirs(os.path.join(top, pkg))
        sh([GIT, "init", "-q", "-b", "main"], top)
        write(top, "README", "r\n")
        cp = os.path.join(TMP, name + "-below.yaml")
        with open(cp, "w") as fh:
            fh.write(cfg)
        rc, out, err = sh([sys.executable, BIN, "-c", cp, "-C",
                           os.path.join(top, pkg)], top)
        if rc != 0:
            print(out[-2000:], err[-2000:])
            raise SystemExit(f"install below the top ({name}) failed rc={rc}")
        sh("git add -A && git commit -qm harness", top)
        return top, os.path.join(top, pkg)

    for pkg in ("app", "svc"):
        top, pj = install_below(pkg, BASE.format(
            extra="  spec_gate_commit_mode: block\n"), pkg)
        check(f"{pkg}/: (fixture) no git hook below the top, so the "
              f"fallback is the check",
              not os.path.exists(os.path.join(top, ".git/hooks/pre-commit")))
        task(pj, T1, ["src/a.py"])
        sh("git commit -qm t1", pj)
        stage(pj, "src/a.py")
        rc, out, err = chk(pj)
        src_, smsg, _ = sdk_check(pj)
        rcf, _, errf = fallback(pj)
        check(f"{pkg}/: a file the project's own task file lists passes on "
              f"the check, the SDK and the fallback (in app/ the build "
              f"refused it, a regression from 3d866f4: CR-7)",
              rc == 0 and src_ == 0 and rcf == 0, (err, smsg, errf))
        stage(pj, "src/zz.py")
        rc, out, err = parity(f"{pkg}/: an unlisted file", pj)
        check(f"{pkg}/: an unlisted file is refused (it was never seen in "
              f"svc/), named from the project directory, and the project's "
              f"task file is the one to edit",
              rc == 2 and out == "src/zz.py\n"
              and f"edit {T1} (status: in-progress)" in err
              and f"Paths here are from the project directory, {pkg}/ in "
              f"the repository." in err, err)
        rcf, _, errf = fallback(pj)
        why = sdk_gate(pj, "block").get("hookSpecificOutput", {}).get(
            "permissionDecisionReason", "")
        check(f"{pkg}/: the fallback refuses (block) and says no git hook "
              f"runs below the top, not 'Re-run bootstrap-install'; the SDK "
              f"denies with the same words",
              rcf == 2 and "this project is below the repository's top "
              "level" in errf and "Re-run bootstrap-install" not in errf
              and why == errf.rstrip("\n"), (errf, why))
        sh([GIT, "reset", "-q"], pj)
        write(top, "other/src/o.py", "o\n")
        write(top, "src/t.py", "t\n")
        sh([GIT, "add", "-f", "other/src/o.py", "src/t.py"], top)
        rc, out, err = chk(pj)
        src_, _, _ = sdk_check(pj)
        check(f"{pkg}/: paths outside the project (another package's src/, "
              f"the top's src/) are not this project's to police",
              rc == 0 and src_ == 0, (rc, err))
        sh([GIT, "reset", "-q"], top)
        rc, _, err = chk_at(pj, os.path.join(pj, "src"), "--files",
                            "src/a.py", "src/q.py")
        check(f"{pkg}/: --files from the project's src/ takes paths from the "
              f"project directory", rc == 2 and "  src/q.py\n" in err
              and "  src/a.py\n" not in err, (rc, err))

    # A package directory whose name holds a glob character: the project's
    # task files are found by a literal pathspec, not a glob.
    top, pj = install_below("glob", BASE.format(
        extra="  spec_gate_commit_mode: block\n"), "we[b]")
    task(pj, T1, ["src/a.py"])
    sh("git commit -qm t1", pj)
    stage(pj, "src/a.py")
    rc, out, err = chk(pj)
    src_, smsg, _ = sdk_check(pj)
    check("we[b]/: a package whose name holds '[' still reads its own task "
          "files (a literal pathspec): a listed file passes, shell and SDK",
          rc == 0 and src_ == 0, (rc, err, src_, smsg))

    print("\n-- the remedy follows a merge and the commit form (SC-1, SC-2) "
          "--")
    # The forms are told apart by GIT_INDEX_FILE, as git sets it for a hook
    # (end-to-end rows through the real shim: tests/test_git_hooks.py).
    d = fresh(GF)
    task(d, T1, ["src/a.py"])
    sh("git commit -qm t1", d)
    stage(d, "src/c.py")
    texts = {}
    for form, name in (("plain", "index"), ("all", "index.lock"),
                       ("paths", "next-index-77.lock")):
        # The index git would hand the hook, under the name it gives it.
        gif = os.path.join(d, ".git", name)
        if name != "index":
            shutil.copy(os.path.join(d, ".git", "index"), gif)
        rc, _, err = chk(d, env=dict(ENV, GIT_INDEX_FILE=gif))
        os.environ["GIT_INDEX_FILE"] = gif
        try:
            src_, smsg, _ = sdk_check(d)
        finally:
            del os.environ["GIT_INDEX_FILE"]
            if name != "index":
                os.remove(gif)
        texts[form] = (rc, err, src_, smsg)
    ok = all(v[0] == 2 and v[2] == 2 and v[3] == v[1].rstrip("\n")
             for v in texts.values())
    check("plain, -a and pathspec forms: shell == SDK, rc 2", ok,
          {k: (v[0], v[2]) for k, v in texts.items()})
    e_ = texts["plain"][1]
    check("plain commit: stage the task file and commit again; unstage with "
          "git restore --staged",
          "stage that file (git add) and commit again" in e_
          and "unstage it (git restore --staged <path>)" in e_, e_)
    e_ = texts["all"][1]
    check("commit -a / --include: no unstage advice (it changes nothing); "
          "commit the task's paths by name",
          "restore --staged" not in e_ and "commit the task's paths by name "
          "instead (git commit -- <paths>)" in e_, e_)
    e_ = texts["paths"][1]
    check("a commit that names paths: name the task file in the same command",
          "commit again with that file named in the same command (git commit "
          "<paths> <task file>)" in e_ and "stage that file (git add)" not in e_
          and "restore --staged" not in e_
          and "leave it out of the paths you name" in e_, e_)
    # Inside pre-merge-commit git has not written MERGE_HEAD; the merge's
    # other head comes as GITHEAD_<oid>, read only for that hook.
    d = fresh(GF)
    task(d, T1, ["src/m.py"])
    write(d, "src/shared.py", "1\n2\n3\n4\n5\n")
    sh("git add -A && git commit -qm base", d)
    sh("git checkout -qb S && echo b > src/b.py && sed -i.b 's/^5$/50/' "
       "src/shared.py && git add src/b.py && git commit -qam s && "
       "git checkout -q main && sed -i.b 's/^1$/10/' src/shared.py && "
       "git commit -qam m", d)
    _oid = sh([GIT, "rev-parse", "S"], d)[1].strip()
    sh("git merge --no-ff --no-commit S && echo e > src/extra.py && "
       "git add src/extra.py", d)
    for _f in ("MERGE_HEAD", "MERGE_MSG", "MERGE_MODE"):
        os.remove(os.path.join(d, ".git", _f))
    _menv = {"BOOTSTRAP_GIT_HOOK": "pre-merge-commit",
             "GITHEAD_" + _oid: "S"}
    rc, out, err = chk(d, env=dict(ENV, **_menv))
    os.environ.update(_menv)
    try:
        src_, smsg, _ = sdk_check(d)
    finally:
        for _k in _menv:
            del os.environ[_k]
    check("pre-merge-commit (GITHEAD_<oid>, no MERGE_HEAD yet): only the "
          "merge's own src/extra.py, not the branch's src/b.py nor the "
          "cleanly merged src/shared.py; shell == SDK",
          rc == 2 and out == "src/extra.py\n" and src_ == 2
          and smsg == err.rstrip("\n") and "This is a merge" in err,
          (out, err, smsg))
    rc, out, err = chk(d, env=dict(ENV, **{"GITHEAD_" + _oid: "S"}))
    check("... and GITHEAD_ alone, outside pre-merge-commit, is not read",
          rc == 2 and "src/b.py" in out, (rc, out))
    sh("git reset -q --hard", d)

    d = os.path.join(TMP, "unborn-text")
    shutil.copytree(GF, d, symlinks=True)
    task(d, T1, ["src/a.py"])
    stage(d, "src/c.py")
    rc, out, err = parity("unborn HEAD", d)
    check("unborn HEAD (the first commit): unstage with git rm --cached, "
          "since git restore --staged fails there",
          rc == 2 and "unstage it (git rm --cached <path>; this is the first "
          "commit)" in err and "restore --staged" not in err, err)

    print("\n-- a check that cannot run is not a spec refusal (SC-3, F2) --")
    # [WP3 fix2 CRIT-1, MR-3] The end line replaces the `bash -n` guard: a
    # verdict (0 or 2) without it is "could not run", and a verdict reached
    # after bash reported an error is exit 3. The reason differs by bash
    # version (bash exits 2 itself, or the check exits 3), so the rows read
    # "could not run" and "not a spec refusal", never "Commit refused".
    BROKEN = (("an unclosed quote", "PREFIXES='src/ lib/ app/ test/ tests/'",
               "PREFIXES='src/ lib/ app/ test/ tests/ pkg/"),
              ("an unclosed array", "PREFIXES='src/ lib/ app/ test/ tests/'",
               "PREFIXES=(src/ lib/"),
              # MR-3: bash before 5.2 does not parse inside $(...) under -n,
              # and at run time only that substitution fails: fe is empty,
              # the mention pattern matches every line, the file "covered".
              # [WP3 fix3 EM-1] ere_esc is bash now (no $(...)), so the
              # broken substitution is written around its result.
              ("a syntax error inside $(...)",
               'ere_esc "$f"; fe="$ERE"; ere_esc "$b"; be="$ERE"',
               'ere_esc "$f"; fe="$(printf %s "$ERE" |)"; ere_esc "$b"; '
               'be="$ERE"'))
    for label, old, new in BROKEN:
        for tpl, mode in ((GB, "block"), (GF, "warn")):
            d = fresh(tpl)
            task(d, T1, ["src/a.py"])
            sh("git commit -qm t1", d)
            p_ = os.path.join(d, templates.SPEC_CHECK_PATH)
            b_ = open(p_).read()
            assert old in b_, label
            with open(p_, "w") as fh:
                fh.write(b_.replace(old, new, 1))
            stage(d, "src/b.py")
            rc, out, err = fallback(d)
            if mode == "block":
                ok = (rc == 2 and "the spec check could not run (" in err
                      and "which is not a spec refusal" in err
                      and "Commit refused." not in err)
            else:
                ctx = json.loads(out)["hookSpecificOutput"][
                    "additionalContext"] if out.strip() else ""
                ok = rc == 0 and ("the spec check could not run (" in ctx
                                  and "so this commit was not checked" in ctx)
            check(f"fallback, {mode}: spec-check.sh with {label} could not "
                  f"run, not a spec refusal and not a pass", ok,
                  (rc, out[:300], err[:300]))
    d = fresh(GB)
    stage(d, "src/b.py")
    p_ = os.path.join(d, templates.SPEC_CHECK_PATH)
    with open(p_, "w") as fh:
        fh.write("#!/usr/bin/env bash\necho boom >&2\nexit 2\n")
    rc, out, err = fallback(d)
    check("fallback, block: exit 2 with no end line could not run (bash's "
          "own status), not a spec refusal",
          rc == 2 and "could not run (it exited 2 without its end line" in err
          and "Commit refused." not in err, (rc, err))
    with open(p_, "w") as fh:
        fh.write("#!/usr/bin/env bash\necho src/b.py\necho no >&2\nexit 2\n")
    rc, out, err = fallback(d)
    check("fallback, block: exit 2 with the paths but NO end line could not "
          "run (it stopped before a verdict) [WP3 fix2 MR-3]",
          rc == 2 and "could not run (it exited 2 without its end line" in err
          and "Commit refused." not in err, (rc, err))
    with open(p_, "w") as fh:
        fh.write("#!/usr/bin/env bash\necho src/b.py\necho no >&2\n"
                 "echo '%s'\nexit 2\n" % END)
    rc, out, err = fallback(d)
    check("... and exit 2 with the paths and the end line is a spec refusal",
          rc == 2 and "Commit refused." in err and END not in err, (rc, err))
    with open(p_, "w") as fh:
        fh.write("#!/usr/bin/env bash\nexit 0\n")
    rc, out, err = fallback(d)
    check("fallback, block: exit 0 with no end line could not run, not a "
          "pass [WP3 fix2 MR-3]",
          rc == 2 and "could not run (it exited 0 without its end line" in err,
          (rc, err))
    # [WP3 fix2 CRIT-1] A locale that is not installed: every bash start
    # prints a setlocale warning. The guard read it as "does not parse", so
    # a listed file was refused (block) and an unlisted one passed with no
    # spec message (warn).
    BADLOC = "xx_YY.UTF-8"
    _probe = sh([BASH, "-c", ":"], TMP, env=dict(ENV, LC_ALL=BADLOC))
    if "setlocale" in _probe[2]:
        for tpl, mode in ((GB, "block"), (GF, "warn")):
            d = fresh(tpl)
            task(d, T1, ["src/a.py"])
            sh("git commit -qm t1", d)
            stage(d, "src/a.py")
            locenv = dict(ENV, CLAUDE_PROJECT_DIR=d, LC_ALL=BADLOC)
            payload = json.dumps({"hook_event_name": "PreToolUse",
                                  "tool_name": "Bash",
                                  "tool_input": {"command": "git commit -m x"}})
            rc, out, err = sh([BASH, os.path.join(
                d, ".claude/hooks/spec-gate-commit.sh")], d, env=locenv,
                inp=payload)
            check(f"fallback, {mode}, LC_ALL names a locale that is not "
                  f"installed: a listed file passes (CRIT-1)",
                  rc == 0 and "could not run" not in out + err, (rc, out, err))
            stage(d, "src/b.py")
            rc, out, err = sh([BASH, os.path.join(
                d, ".claude/hooks/spec-gate-commit.sh")], d, env=locenv,
                inp=payload)
            ok = ((rc == 2 and "Commit refused." in err
                   and "  src/b.py" in err) if mode == "block" else
                  (rc == 0 and "src/b.py" in out and "not listed" in out))
            check(f"fallback, {mode}, the same locale: an unlisted file is a "
                  f"spec refusal or warning, not 'could not run' (CRIT-1)",
                  ok and "could not run" not in out + err, (rc, out, err))
            rc, out, err = sh([BASH, os.path.join(d, templates.SPEC_CHECK_PATH)],
                              d, env=locenv)
            check(f"spec-check.sh itself, {mode} fixture, the same locale: "
                  f"exit 2 with the end line (the warning is not a bash "
                  f"diagnostic of the check)",
                  rc == 2 and out.endswith(END + "\n"), (rc, out, err))
    else:
        # musl (Alpine) accepts any locale name and prints nothing.
        print("  SKIP  the uninstalled-locale rows: this libc prints no "
              "setlocale warning")

    print("\n-- --files: a path ending in '/' (F3) --")
    d = fresh(GF)
    task(d, T1, ["src/a.py"])
    sh("git commit -qm t1", d)
    for p_ in ("src/newdir/", "lib/", "src/x.py/"):
        rc, out, err = chk(d, "--files", p_)
        src_, smsg, _ = sdk_check(d, changed=[p_])
        check(f"--files {p_}: exit 3 (not a file path), never 'covered' by "
              f"an empty bare name; the SDK alike",
              rc == 3 and "pass file paths, not directories" in err
              and src_ == 3 and smsg == err.rstrip("\n"),
              (rc, err, src_, smsg))

    print("\n-- the directory hint states its limit (MT-2) --")
    d = fresh(GF)
    stage(d, "src/a.py")
    rc, out, err = parity("the directory hint", d)
    check("the refusal says a directory entry keeps covering after its task "
          "is done, and to use one only for names not known in advance",
          rc == 2 and 'A directory entry ending in "/" (for example '
          'src/gen/) covers every file below it, even after its task is '
          'done: use one only for files whose names cannot be known in '
          'advance, such as generated code, and otherwise list each file.'
          in err, err)

    print("\n-- thousands of task files: awk and grep in batches (F1) --")
    d = fresh(GF)
    _ob = os.path.join(d, ".claude/specs/old/tasks")
    os.makedirs(_ob)
    for i in range(2500):
        with open(os.path.join(_ob, f"old-T{i:05d}.md"), "w") as fh:
            fh.write("---\nstatus: done\n---\nOld work on old%05d.py.\n" % i)
    task(d, T1, ["src/a.py"])
    task(d, T2, None, body="Touches src/b.py.\n")
    sh("git add -f .claude/specs && git commit -qm old", d)
    stage(d, "src/a.py")

    def small_args(d, *a):
        # Linux sets ARG_MAX to a quarter of the stack limit, at least 128
        # KiB: 2,502 task paths are past it (one exec of them all hit E2BIG).
        return sh([BASH, "-c", 'ulimit -s 256 && exec "$0" "$@"', BASH,
                   os.path.join(d, templates.SPEC_CHECK_PATH), *a], d)
    rc, out, err = small_args(d)
    src_, _, _ = sdk_check(d)
    check("2,502 task files under a 128 KiB ARG_MAX: awk runs in batches, so "
          "a listed file passes (one exec of them all: exit 3, E2BIG); SDK "
          "alike", rc == 0 and src_ == 0, (rc, err[:300]))
    sh([GIT, "reset", "-q"], d)
    stage(d, "src/b.py")
    rc, out, err = small_args(d)
    src_, _, _ = sdk_check(d)
    check("... and grep reads 2,501 legacy files in batches: a mention in "
          "the last one still covers", rc == 0 and src_ == 0, (rc, err[:300]))

    print("\n-- the SDK reads task files as the shell does (SDKP-1) --")
    d = fresh(GB)
    sh([GIT, "config", "filter.up.smudge", "sed s/XSRC/src/"], d)
    sh([GIT, "config", "filter.up.clean", "cat"], d)
    write(d, ".gitattributes", ".claude/specs/**/*.md filter=up\n")
    sh([GIT, "add", ".gitattributes"], d)
    task(d, T1, ["XSRC/a.py"])
    stage(d, "src/a.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("(a) a smudge filter on the task files: both read the smudged "
          "text, so src/a.py is listed (the SDK read the raw blob)",
          rc == 0 and src_ == 0, (rc, err, src_, smsg))
    d = fresh(GB)
    write(d, ".gitattributes",
          ".claude/specs/**/*.md working-tree-encoding=UTF-16LE\n")
    sh([GIT, "add", ".gitattributes"], d)
    os.makedirs(os.path.dirname(os.path.join(d, T1)), exist_ok=True)
    with open(os.path.join(d, T1), "wb") as fh:
        fh.write("---\nstatus: in-progress\n---\nFiles:\n- src/a.py\n"
                 .encode("utf-16-le"))
    sh([GIT, "add", "-f", T1], d)
    stage(d, "src/a.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("(b) a working-tree-encoding on the task files: the same verdict "
          "on both (each reads the checked-out bytes)", rc == src_,
          (rc, err, src_, smsg))
    d = fresh(GB)
    task(d, T1, ["src/a.py"])
    sh("git update-index --add --cacheinfo "
       "160000,$(git rev-parse HEAD),.claude/specs/f/tasks/sub", d)
    stage(d, "src/a.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("(c) a gitlink under tasks/ reads as an empty file on both, so "
          "src/a.py listed elsewhere passes (the SDK could not run, exit 3)",
          rc == 0 and src_ == 0, (rc, err, src_, smsg))
    d = fresh(GB)
    os.makedirs(os.path.join(d, ".claude/specs/f/tasks"), exist_ok=True)
    _bn = b".claude/specs/f/tasks/t\xe2che.md"
    with open(os.path.join(os.fsencode(d), _bn), "wb") as fh:
        fh.write(b"---\nstatus: in-progress\n---\nFiles:\n- src/a.py\n")
    subprocess.run([GIT, "add", "-f", "--", _bn], cwd=d, env=ENV)
    stage(d, "src/a.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("(d) a task file whose name is not UTF-8 is read on both (src/a.py "
          "listed -> 0; the SDK could not run, exit 3)",
          rc == 0 and src_ == 0, (rc, err, src_, smsg))
    stage(d, "src/b.py")
    rc, ob, eb = run_b([BASH, os.path.join(d, templates.SPEC_CHECK_PATH)], d)
    src_, smsg, _ = sdk_check(d)
    check("... and the refusal names that task file, shell == SDK (bytes "
          "that are not UTF-8 shown as U+FFFD by the SDK)",
          rc == 2 and src_ == 2
          and eb.decode("utf-8", "replace").rstrip("\n") == smsg, (eb, smsg))

    print("\n-- the SDK fallback's own dimensions (TP-06) --")
    for tpl, mode in ((GF, "warn"), (GB, "block")):
        d = fresh(tpl)
        stage(d, "src/a.py")
        hp = os.path.join(d, ".git", "hooks", "pre-commit")
        with open(hp, "w") as fh:
            fh.write(SHIM)
        os.chmod(hp, 0o644)
        hso = sdk_gate(d, mode).get("hookSpecificOutput", {})
        ok = (hso.get("permissionDecision") == "deny" if mode == "block"
              else "not listed" in hso.get("additionalContext", ""))
        check(f"SDK, {mode}: a NON-executable shim is not deferred to "
              f"(git would not run it): the check runs", ok, hso)
    d = fresh(GF)
    stage(d, "pkg/x.go")
    for mode in ("warn", "block"):
        hso = sdk_gate_cfg(d, {"hooks": {
            "spec_gate_commit_mode": mode,
            "spec_gate_commit_prefixes": ["pkg/"]}}).get(
                "hookSpecificOutput", {})
        txt = (hso.get("additionalContext", "")
               + hso.get("permissionDecisionReason", ""))
        check(f"SDK, {mode}, no git hook: the configured prefixes are the "
              f"ones policed (pkg/x.go is reported)", "  pkg/x.go\n" in txt,
              hso)

    print("\n-- hooks.spec_gate_commit_prefixes is validated (TP-09) --")
    for bad in ('    - "./src/"\n', '    - "../x/"\n', '    - "src/../a/"\n',
                '    - "src/./a/"\n', None):
        extra = WARN + ("  spec_gate_commit_prefixes:\n" + bad if bad
                        else "  spec_gate_commit_prefixes: []\n")
        _c, _e = _defaults.resolve_config(_ly(BASE.format(extra=extra)))
        check(f"spec_gate_commit_prefixes {(bad or '[]').strip()} is "
              f"refused, naming the key",
              any("hooks.spec_gate_commit_prefixes" in str(x) for x in _e),
              _e)

    print("\n-- input normalisation, shell == SDK (TP-10) --")

    def one(body_, *paths):
        d = fresh(GF)
        write(d, T1, body_)
        sh([GIT, "add", "-f", T1], d)
        sh("git commit -qm t1", d)
        stage(d, *(paths or ("src/a.py",)))
        return d
    d = one("---\nstatus: 'in-progress'\n---\nFiles:\n- src/x.py\n")
    rc, out, err = parity("single-quoted status", d)
    check("status: 'in-progress' (single quotes) is read",
          rc == 2 and "(status: in-progress)" in err, err)
    d = one("---\nstatus: In-Progress\n---\nFiles:\n- src/x.py\n")
    rc, out, err = parity("status case", d)
    check("status: In-Progress is read whatever its case",
          rc == 2 and "(status: in-progress)" in err, err)
    d = one("---\nstatus: in-progress\n...\nTouches src/a.py.\nFiles:\n"
            "- src/x.py\n")
    rc, out, err = parity("frontmatter ending in '...'", d)
    check("a frontmatter ending in '...' ends there: the Files: block below "
          "is read, so a prose mention does not cover",
          rc == 2 and out == "src/a.py\n", (rc, out))
    d = one("---\nstatus: in-progress\n---\nFiles:\n- src/a.py  \n"
            "-   src/b.py\n", "src/a.py", "src/b.py")
    rc, out, err = parity("trailing and extra blanks on entries", d)
    check("an entry with trailing blanks, and one with blanks after '- ', "
          "read as the paths (a listed file is not refused for them)",
          rc == 0, err)
    d = one("---\nstatus: in-progress\n---\nMentions src/a.py.\nFiles: \n"
            "- src/x.py\n")
    rc, out, err = parity("'Files: ' with a trailing blank", d)
    check("'Files: ' with a trailing blank is a Files: block, so the file is "
          "held to it and a prose mention does not cover",
          rc == 2 and out == "src/a.py\n", (rc, out))
    d = one("---\nstatus: in-progress\n---\nFiles:\n- src/a.py\n")
    rc, out, err = chk(d, "--task", "./" + T1, "--files", "src/a.py")
    src_, smsg, _ = sdk_check(d, changed=["src/a.py"], task="./" + T1)
    check("--task ./<path>: the leading ./ is dropped, shell == SDK",
          rc == 0 and src_ == 0, (rc, err, src_, smsg))
    _tmps = (TMP, tempfile.gettempdir())

    def leftovers():
        return sorted(x for t in _tmps for x in os.listdir(t)
                      if x.startswith("spec-check."))
    _before = leftovers()
    d = fresh(GF)
    stage(d, "src/a.py")
    chk(d)
    sdk_check(d)
    task(d, T1, ["src/a.py"])
    chk(d)
    sdk_check(d)
    check("no spec-check.* temporary directory is left behind (shell, SDK)",
          leftovers() == _before, (_before, leftovers()))
    d = fresh(GF)
    task(d, T1, None, body="Rename the naïve.py helper.\n")
    stage(d, "src/ve.py")
    rc, out, err = chk(d, env=dict(ENV, LANG="C.UTF-8", LC_ALL="C.UTF-8"))
    src_, _, _ = sdk_check(d)
    check("under a UTF-8 host locale the shell matches bytes as the SDK "
          "does (spec-check.sh sets LC_ALL=C): the same rc", rc == src_,
          (rc, src_, err))
    d = fresh(RF)
    week(d, 4)
    _sp = os.path.join(d, ".claude/steering/spec-strategy.md")
    _t = open(_sp).read()
    with open(_sp, "w") as fh:
        fh.write(_t.replace("<!-- LEGACY_ALLOWLIST_BEGIN -->\n",
                            "<!-- LEGACY_ALLOWLIST_BEGIN -->\n"
                            "  src/old/**  \n", 1))
    stage(d, "src/old/y.py")
    rc, out, err = chk(d)
    check("retrofit week 4: an allowlist line with leading and trailing "
          "blanks still exempts its path", rc == 0 and out == "", (rc, out))

    print("\n-- crafted names and the naming order (TP-11) --")
    d = fresh(GF)
    _nm = "src/a\x1b[31mX.py"
    write(d, _nm, "x\n")
    sh([GIT, "add", "-f", "--", _nm], d)
    rc, ob, eb = run_b([BASH, os.path.join(d, templates.SPEC_CHECK_PATH)], d)
    src_, smsg, _ = sdk_check(d)
    check("a staged name holding ESC prints as '?', never as a raw ESC, on "
          "stdout and stderr (shell == SDK)",
          rc == 2 and b"\x1b" not in ob + eb and b"src/a?[31mX.py" in ob
          and src_ == 2 and "\x1b" not in smsg
          and eb.decode().rstrip("\n") == smsg, (ob, eb, smsg))
    d = fresh(GF)
    write(d, "src/a\n", "x\n")
    sh([GIT, "add", "-f", "--", "src/a\n"], d)
    rc, out, err = chk(d)
    src_, _, _ = sdk_check(d)
    check("a staged name ending in a newline is not covered by a mention of "
          "its stem (INDEX.md holds the word 'a'): exit 2 on both (CR-2)",
          rc == 2 and src_ == 2, (rc, err, src_))
    d = fresh(GF)
    task(d, T1, None, body="See src/a\nb.py here.\n")
    write(d, "src/a\nb.py", "x\n")
    sh([GIT, "add", "-f", "--", "src/a\nb.py"], d)
    rc, out, err = chk(d)
    src_, _, _ = sdk_check(d)
    check("a staged name holding a newline is not covered by a mention that "
          "spans two lines: exit 2 on both", rc == 2 and src_ == 2,
          (rc, err, src_))
    d = fresh(GF)
    task(d, T1, None, body="Touches src/aXpy only.\n")
    stage(d, "src/a.py")
    rc, out, err = parity("a near-miss mention", d)
    check("the mention rule escapes '.': src/aXpy does not mention src/a.py",
          rc == 2 and out == "src/a.py\n", (rc, out))
    d = fresh(GF)
    write(TMP, "evil-task.md", "---\nstatus: in-progress\n---\nFiles:\n"
          "- src/a.py\n")
    os.makedirs(os.path.dirname(os.path.join(d, T1)), exist_ok=True)
    os.symlink(os.path.join(TMP, "evil-task.md"), os.path.join(d, T1))
    sh([GIT, "add", "-f", T1], d)
    stage(d, "src/a.py")
    rc, out, err = parity("a task file committed as a symlink", d)
    check("a task file committed as a symlink is read as its link text "
          "(core.symlinks=false), never through the link: src/a.py is refused",
          rc == 2 and out == "src/a.py\n", (rc, out))
    d = fresh(GF)
    for i in range(9):
        task(d, f".claude/specs/f/tasks/f-T{i + 1:02d}.md", [f"src/t{i}.py"])
    sh("git commit -qm tasks", d)
    stage(d, "src/a.py")
    rc, out, err = parity("nine in-progress candidates", d)
    check("nine candidates: eight are listed, then '(and 1 more)'",
          rc == 2 and "  (and 1 more)\n" in err
          and err.count("\n  .claude/specs/f/tasks/f-T") == 8, err)
    d = fresh(GF)
    task(d, T1, ["src/x.py"], status="validated")
    task(d, T2, ["src/y.py"], status="planned")
    sh("git commit -qm tasks", d)
    stage(d, "src/a.py")
    rc, out, err = parity("a validated task and a planned one", d)
    check("a validated task is closed: the planned one is the only open task "
          "with a Files: block",
          f"edit {T2} (the only open task with a Files: block)" in err, err)
    d = fresh(GF)
    task(d, T1, ["src/x.py"], status="planned")
    task(d, T2, ["src/y.py"], status="planned")
    sh("git commit -qm tasks", d)
    stage(d, "src/a.py")
    rc, out, err = parity("two planned tasks with Files: blocks", d)
    check("two open tasks with Files: blocks are both candidates, and "
          "neither is 'the only open task'",
          "Candidate task files (open tasks):" in err
          and "the only open task" not in err, err)
    d = fresh(GF)
    with open(os.path.join(d, ".claude/specs/INDEX.md"), "a") as fh:
        fh.write("| f | src/a.py |\n")
    stage(d, "src/a.py")
    rc, out, err = parity("an unstaged INDEX.md edit", d)
    check("an unstaged INDEX.md edit does not count and is named under "
          "'Not counted'", rc == 2 and "  .claude/specs/INDEX.md\n" in err
          and "Not counted, because the index does not have them" in err, err)
    d = fresh(GF)
    task(d, ".claude/specs/f/tasks/sub/f-T09.md", ["src/a.py"])
    stage(d, "src/a.py")
    rc, out, err = parity("a file in a directory below tasks/", d)
    check("a file nested below tasks/ is not a task file: its Files: block "
          "covers nothing", rc == 2 and out == "src/a.py\n", (rc, out))
    d = fresh(GF)
    stage(d, *[f"src/long/{'x' * 60}{i:03d}.py" for i in range(80)])
    rc, out, err = fallback(d)
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] \
        if out.strip() else ""
    hso = sdk_gate(d, "warn").get("hookSpecificOutput", {})
    check("a warn message past 4000 bytes is cut at the same point, then "
          "'[truncated]', on both substrates",
          ctx.endswith("\n[truncated]")
          and hso.get("additionalContext") == ctx, (len(ctx), hso))

    print("\n-- the could-not-run texts are byte-equal (SDKP-5) --")
    d = fresh(GB)
    stage(d, "src/a.py")
    with open(os.path.join(d, ".git", "index"), "wb") as fh:
        fh.write(b"DIRC\0\0\0\2garbage")
    rc, out, err = fallback(d)
    why = sdk_gate(d, "block").get("hookSpecificOutput", {}).get(
        "permissionDecisionReason", "")
    check("block, corrupt index: the shell and the SDK refuse with the same "
          "whole text (the SDK kept git's newline before its 300-byte cut)",
          rc == 2 and why == err.rstrip("\n"), (err, why))

    # ================================================================== #
    # [WP3 fix1 INST-3] A hook the operator wrote that runs dispatch (the
    # installer's core.hooksPath / hand-written remedy) is deferred to like
    # the shim; where nothing is deferred to, the note says what holds
    # there, never "Re-run bootstrap-install" where a re-install adds none.
    print("\n-- the fallback and a hook that is not the shim (INST-3) --")
    RUNS = ("#!/bin/sh\n# my hook\n.claude/githooks/dispatch pre-commit "
            "|| exit 1\n")
    NOTE_DEFAULT = "Re-run bootstrap-install to add it."

    def put_hook(d, rel, body, mode=0o755):
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(body)
        os.chmod(p, mode)

    def both_block(d):
        rc, out, err = fallback(d)
        why = sdk_gate(d, "block").get("hookSpecificOutput", {}).get(
            "permissionDecisionReason", "")
        return rc, err, why

    # [WP3 fix2 IT-1, RG-2] Superseded: a hook whose TEXT holds the dispatch
    # line was deferred to, and husky 9's wrapper (the line after `. h`,
    # which exits first), the pre-commit framework's (after its exec) and a
    # commented-out line all then ran no check while the fallback went
    # quiet. The fallback defers to the installer's shim only (above); for
    # any other hook it runs the check and says so in its note.
    H9_WRAP = '#!/usr/bin/env sh\n. "$(dirname "$0")/h"'
    H9_H = ('#!/usr/bin/env sh\nn=$(basename "$0")\n'
            's=$(dirname "$(dirname "$0")")/$n\n[ ! -f "$s" ] && exit 0\n'
            'sh -e "$s" "$@"\nc=$?\nexit $c\n')
    PCF = ("#!/usr/bin/env bash\n# File generated by pre-commit: "
           "https://pre-commit.com\nexec true\n")
    SHAPES = (
        ("an executable .git/hooks/pre-commit that runs dispatch itself",
         ".git/hooks/pre-commit", RUNS, None),
        ("husky 9's .husky/_/pre-commit with the line appended after `. h`",
         ".husky/_/pre-commit", H9_WRAP + "\n.claude/githooks/dispatch "
         "pre-commit || exit 1\n", ".husky/_"),
        ("the pre-commit framework's hook with the line appended after its "
         "exec", ".git/hooks/pre-commit",
         PCF + ".claude/githooks/dispatch pre-commit || exit 1\n", None),
        ("a hook whose dispatch line is commented out",
         ".git/hooks/pre-commit",
         "#!/bin/sh\n# .claude/githooks/dispatch pre-commit\nexit 0\n",
         None))
    for label, rel, body, hpath in SHAPES:
        for tpl, mode in ((GF, "warn"), (GB, "block")):
            d = fresh(tpl)
            stage(d, "src/a.py")
            if hpath:
                put_hook(d, ".husky/_/h", H9_H, 0o644)
                sh([GIT, "config", "core.hooksPath", hpath], d)
            put_hook(d, rel, body)
            rc, out, err = fallback(d)
            res = sdk_gate(d, mode)
            hso = res.get("hookSpecificOutput", {})
            if mode == "block":
                ok = (rc == 2 and "Commit refused." in err
                      and templates.SPEC_FALLBACK_NOTE_FOREIGN in err
                      and hso.get("permissionDecisionReason")
                      == err.rstrip("\n"))
            else:
                ctx = json.loads(out)["hookSpecificOutput"][
                    "additionalContext"] if out.strip() else ""
                ok = (rc == 0 and "not listed" in ctx
                      and templates.SPEC_FALLBACK_NOTE_FOREIGN in ctx
                      and hso.get("additionalContext") == ctx)
            check(f"{mode}: {label} is NOT deferred to (its text cannot "
                  f"show the line runs): the check runs, with the foreign "
                  f"note, on both substrates (IT-1, RG-2)", ok,
                  (rc, out[:200], err[-300:], res))
    d = fresh(GB)
    stage(d, "src/a.py")
    put_hook(d, ".husky/_/h", H9_H, 0o644)
    put_hook(d, ".husky/_/pre-commit", H9_WRAP + "\n.claude/githooks/"
             "dispatch pre-commit || exit 1\n")
    sh([GIT, "config", "core.hooksPath", ".husky/_"], d)
    rc, _, err = sh("CLAUDECODE=1 git commit -qm unlisted", d)
    check("(why) husky 9's wrapper with the line appended runs no check: the "
          "agent commit of an unlisted file lands with no spec message",
          rc == 0 and "spec check" not in err, (rc, err[-300:]))
    # [WP3 fix2 IT-2] A hook git skips, the installer's shim included: the
    # note says it is not executable, on both substrates.
    for body_, what in ((RUNS, "a hand-written hook"), (SHIM, "the shim")):
        d = fresh(GB)
        stage(d, "src/a.py")
        put_hook(d, ".git/hooks/pre-commit", body_, 0o644)
        rc, err, why = both_block(d)
        check(f"block: {what} that is not executable: refused with the "
              f"not-executable note (git skips it), same words on the SDK "
              f"(IT-2)",
              rc == 2 and templates.SPEC_FALLBACK_NOTE_NOEXEC in err
              and templates.SPEC_FALLBACK_NOTE_FOREIGN not in err
              and why == err.rstrip("\n"), (err[-400:], why[-400:]))
    d = fresh(GB)
    stage(d, "src/a.py")
    os.makedirs(os.path.join(d, ".husky"))
    sh([GIT, "config", "core.hooksPath", ".husky"], d)
    put_hook(d, ".husky/pre-commit", RUNS)
    rc, err, why = both_block(d)
    check("block: core.hooksPath .husky whose pre-commit runs dispatch: not "
          "deferred to on either substrate (the commit then draws two "
          "messages, Z-30); the foreign note does not say the hook fails "
          "to run it", rc == 2 and templates.SPEC_FALLBACK_NOTE_FOREIGN in err
          and "does not itself run" not in err and why == err.rstrip("\n"),
          (rc, err[-300:]))
    os.remove(os.path.join(d, ".husky", "pre-commit"))
    rc, err, why = both_block(d)
    check("block: core.hooksPath set and no pre-commit hook there: refused "
          "with the hooks-path note, not 'Re-run bootstrap-install'; the SDK "
          "denies with the same words",
          rc == 2 and templates.SPEC_FALLBACK_NOTE_HOOKS_PATH in err
          and NOTE_DEFAULT not in err and why == err.rstrip("\n"),
          (err[-400:], why[-400:]))
    put_hook(d, ".husky/pre-commit", "#!/bin/sh\nnpx lint-staged\n")
    rc, err, why = both_block(d)
    check("block: a husky hook that does not run dispatch: refused with the "
          "foreign-hook note, same words on the SDK",
          rc == 2 and templates.SPEC_FALLBACK_NOTE_FOREIGN in err
          and NOTE_DEFAULT not in err and why == err.rstrip("\n"),
          (err[-400:], why[-400:]))
    d = fresh(GF)
    stage(d, "src/a.py")
    put_hook(d, ".git/hooks/pre-commit",
             "#!/bin/sh\n# lefthook generated\nlefthook run pre-commit\n")
    rc, out, err = fallback(d)
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] \
        if out.strip() else ""
    hso = sdk_gate(d, "warn").get("hookSpecificOutput", {})
    check("warn: a lefthook hook in .git/hooks: the foreign-hook note, the "
          "same additionalContext on the SDK",
          templates.SPEC_FALLBACK_NOTE_FOREIGN in ctx
          and NOTE_DEFAULT not in ctx and hso.get("additionalContext") == ctx,
          (ctx[-300:], hso))
    d = fresh(GB)
    stage(d, "src/a.py")
    rc, err, why = both_block(d)
    check("block: no hook and no core.hooksPath (a fresh clone): the note "
          "still says a re-install adds it, on both substrates",
          rc == 2 and NOTE_DEFAULT in err
          and templates.SPEC_FALLBACK_NOTE_FOREIGN not in err
          and templates.SPEC_FALLBACK_NOTE_HOOKS_PATH not in err
          and why == err.rstrip("\n"), (err[-300:], why[-300:]))
    # [WP3 fix3 HD-5] An empty core.hooksPath turns every git hook off; a
    # re-install alone adds none, so the note says so on both substrates.
    for tpl, mode in ((GB, "block"), (GF, "warn")):
        d = fresh(tpl)
        stage(d, "src/a.py")
        sh([GIT, "config", "core.hooksPath", ""], d)
        rc, out, err = fallback(d)
        res = sdk_gate(d, mode).get("hookSpecificOutput", {})
        if mode == "block":
            txt, ok = err, (rc == 2 and res.get("permissionDecisionReason")
                            == err.rstrip("\n"))
        else:
            txt = json.loads(out)["hookSpecificOutput"][
                "additionalContext"] if out.strip() else ""
            ok = rc == 0 and res.get("additionalContext") == txt
        check(f"{mode}: core.hooksPath set to an empty value: the hooks-off "
              f"note, not 'Re-run bootstrap-install' or the hooks-path note, "
              f"same words on the SDK (HD-5)",
              ok and templates.SPEC_FALLBACK_NOTE_HOOKS_OFF in txt
              and NOTE_DEFAULT not in txt
              and templates.SPEC_FALLBACK_NOTE_HOOKS_PATH not in txt,
              (rc, txt[-400:], res))
    check("the hooks-off note the SDK module carries is the shell's (HD-5)",
          gates._SPEC_FALLBACK_NOTE_HOOKS_OFF
          == templates.SPEC_FALLBACK_NOTE_HOOKS_OFF)
    check("the notes the SDK module carries are the ones the shell hook is "
          "emitted from",
          gates._SPEC_FALLBACK_NOTE_FOREIGN
          == templates.SPEC_FALLBACK_NOTE_FOREIGN
          and gates._SPEC_FALLBACK_NOTE_HOOKS_PATH
          == templates.SPEC_FALLBACK_NOTE_HOOKS_PATH
          and gates._SPEC_FALLBACK_NOTE_NOEXEC
          == templates.SPEC_FALLBACK_NOTE_NOEXEC)
    check("the shim identity the SDK module carries is the shim's, and the "
          "shell fallback carries its blob ids [WP3 fix2 IT-1]",
          gates._SPEC_SHIM_SHA256 == templates.GIT_HOOK_SHIM_SHA256
          and "|".join(templates.GIT_HOOK_SHIM_IDS) in open(os.path.join(
              GF, ".claude/hooks/spec-gate-commit.sh")).read())

    # ================================================================== #
    # [WP3 fix2] The re-review's spec-check findings (fix round 2). Each row
    # below fails with its fix reverted; the reverts and mutants are listed
    # in the step report (g1-check).
    print("\n== [WP3 fix2] re-review findings ==")

    def read_(p):
        try:
            with open(p) as fh:
                return fh.read()
        except OSError:
            return None

    def nested(name, mode, pkg, top_install=True):
        """A repository with its own install at the top (when top_install)
        and another in `pkg`: both committed."""
        top = os.path.join(TMP, "nest-" + name)
        os.makedirs(os.path.join(top, pkg))
        sh([GIT, "init", "-q", "-b", "main"], top)
        write(top, "README", "r\n")
        cp = os.path.join(TMP, name + "-nest.yaml")
        with open(cp, "w") as fh:
            fh.write(BASE.format(extra=f"  spec_gate_commit_mode: {mode}\n"))
        for where in ((top,) if top_install else ()) + (
                os.path.join(top, pkg),):
            rc, out, err = sh([sys.executable, BIN, "-c", cp, "-C", where],
                              top)
            if rc != 0:
                raise SystemExit(f"install {where} failed rc={rc}: {err[-500:]}")
        sh("git add -A && git commit -qm harness", top)
        return top, os.path.join(top, pkg)

    print("\n-- below the top, the fallback never defers (IT-5, MR-4) --")
    for pkg in ("app", "svc"):
        for mode in ("block", "warn"):
            top, pj = nested(f"{pkg}-{mode}", mode, pkg)
            check(f"(fixture) {pkg}/, {mode}: the top's install wrote the "
                  f"shim git runs", read_(os.path.join(
                      top, ".git/hooks/pre-commit")) == SHIM)
            task(pj, T1, ["src/x.py"])
            sh("git commit -qm t1", pj)
            stage(pj, "src/unlisted.py")
            rc, out, err = fallback(pj)
            res = sdk_gate(pj, mode)
            hso = res.get("hookSpecificOutput", {})
            if mode == "block":
                ok = (rc == 2 and "  src/unlisted.py\n" in err
                      and "below the repository's top level" in err
                      and hso.get("permissionDecisionReason")
                      == err.rstrip("\n"))
            else:
                ctx = json.loads(out)["hookSpecificOutput"][
                    "additionalContext"] if out.strip() else ""
                ok = (rc == 0 and "src/unlisted.py" in ctx
                      and "below the repository's top level" in ctx
                      and hso.get("additionalContext") == ctx)
            check(f"{pkg}/, {mode}, a nested install: the package's fallback "
                  f"does not defer to the top's shim (it runs the top's "
                  f"check); it checks the package, on both substrates", ok,
                  (rc, out[:200], err[-300:], res))
            if mode == "block":
                sh([GIT, "reset", "-q"], pj)
                stage(top, "src/top.py")
                rc_t, _, _ = fallback(top)
                check(f"{pkg}/: (control) at the top, the top's own fallback "
                      f"still defers to the shim", rc_t == 0
                      and "deferred to the git pre-commit hook" in log_tail(top),
                      log_tail(top))
    # MR-4 (c): no top install; a hook manager wired to ANOTHER package.
    top, pj = nested("hp-svc", "block", "svc", top_install=False)
    os.makedirs(os.path.join(top, ".husky"))
    sh([GIT, "config", "core.hooksPath", ".husky"], top)
    write(top, ".husky/pre-commit",
          "#!/bin/sh\napp/.claude/githooks/dispatch pre-commit || exit 1\n")
    os.chmod(os.path.join(top, ".husky/pre-commit"), 0o755)
    task(pj, T1, ["src/x.py"])
    sh("git commit -qm t1", pj)
    stage(pj, "src/y.py")
    rc, out, err = fallback(pj)
    res = sdk_gate(pj, "block")
    check("svc/, block, core.hooksPath runs another package's dispatch: svc's "
          "fallback does not defer; it refuses svc's unlisted file, on both "
          "substrates (MR-4)", rc == 2 and "  src/y.py\n" in err
          and res.get("hookSpecificOutput", {}).get("permissionDecision")
          == "deny", (rc, err[-300:], res))

    print("\n-- a merge concluded with --continue below the top (MR-6) --")
    top, pj = install_below("mr6", BASE.format(
        extra="  spec_gate_commit_mode: block\n"), "app")
    task(pj, T1, ["src/x.py"])
    sh("git commit -qm t1", pj)
    sh("git checkout -qb side && mkdir -p src && echo s > src/s.py && "
       "git add src/s.py && git commit -qm s && git checkout -q main && "
       "mkdir -p src && echo m > src/m.py && git add src/m.py && "
       "git commit -qm m", pj)
    sh("git merge --no-ff --no-commit -q side && echo evil > src/evil.py && "
       "git add src/evil.py", pj)
    check("(fixture) the merge is in progress, with src/evil.py staged",
          os.path.isfile(os.path.join(top, ".git", "MERGE_HEAD"))
          and "app/src/evil.py" in sh([GIT, "diff", "--cached",
                                       "--name-only"], pj)[1])
    for cmd in ("git merge --continue", "git -c core.editor=true merge "
                "--continue", "git commit --no-edit"):
        rc, out, err = fallback(pj, cmd)
        res = sdk_gate(pj, "block", cmd)
        check(f"below the top, block: `{cmd}` concluding a merge with an "
              f"unlisted edit made during it: refused on both substrates, "
              f"naming only src/evil.py (MR-6)",
              rc == 2 and "  src/evil.py\n" in err and "src/s.py" not in err
              and "This is a merge" in err
              and res.get("hookSpecificOutput", {}).get(
                  "permissionDecisionReason") == err.rstrip("\n"),
              (rc, err[-300:], res))
    rc, out, err = fallback(pj, "git merge --abort")
    check("... and `git merge --abort` is not a commit: not checked",
          rc == 0 and err == "" and sdk_gate(pj, "block",
                                              "git merge --abort") == {},
          (rc, err))
    sh("git merge --abort", pj)
    # [WP3 fix2 IT-4] The fallback passes its mode to the check: in warn
    # mode the command commits anyway, so the merge text offers no abort.
    top, pj = install_below("mr6w", BASE.format(extra=WARN), "app")
    task(pj, T1, ["src/x.py"])
    sh("git commit -qm t1", pj)
    sh("git checkout -qb side && mkdir -p src && echo s > src/s.py && "
       "git add src/s.py && git commit -qm s && git checkout -q main", pj)
    sh("git merge --no-ff --no-commit -q side && mkdir -p src && "
       "echo evil > src/evil.py && git add src/evil.py", pj)
    rc, out, err = fallback(pj, "git commit --no-edit")
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] \
        if out.strip() else ""
    hso = sdk_gate(pj, "warn", "git commit --no-edit").get(
        "hookSpecificOutput", {})
    check("below the top, warn: the merge text the fallback relays offers no "
          "git merge --abort (the commit goes through); the SDK says the "
          "same (IT-4)",
          rc == 0 and "This is a merge" in ctx and "src/evil.py" in ctx
          and "git merge --abort" not in ctx
          and hso.get("additionalContext") == ctx, (rc, ctx[-400:], hso))
    sh("git merge --abort", pj)

    print("\n-- an unmerged task file (MR-5) --")
    top, pj = install_below("mr5", BASE.format(
        extra="  spec_gate_commit_mode: block\n"), "app")
    task(pj, T1, ["src/x.py"])
    write(pj, "src/x.py", "base\n")
    sh("git add -A && git commit -qm t1", pj)
    sh("git checkout -qb side && echo side > src/x.py && "
       f"echo '- src/y.py' >> {T1} && git commit -qam side && "
       "git checkout -q main && echo main > src/x.py && "
       f"echo '- src/z.py' >> {T1} && git commit -qam main", pj)
    sh("git merge -q side", pj)
    check("(fixture) the task file and src/x.py are unmerged",
          sorted(set(sh([GIT, "diff", "--name-only", "--diff-filter=U"],
                        pj)[1].split())) == ["app/" + T1, "app/src/x.py"])
    write(pj, "src/x.py", "resolved\n")
    write(pj, T1, open(os.path.join(pj, T1)).read().replace(
        "<<<<<<< HEAD\n", "").replace("=======\n", "").split(">>>>>>>")[0])
    rc, out, err = chk(pj)
    src_, smsg, _ = sdk_check(pj)
    check("a conflicted task file: a verdict (exit 2), not 'could not run' "
          "(checkout-index refused the unmerged entry): the task file is "
          "named under 'Not counted', shell == SDK (MR-5)",
          rc == 2 and "checkout-index" not in err
          and "Not counted, because the index does not have them" in err
          and f"  {T1}\n" in err.split("Not counted")[1]
          and src_ == 2 and smsg == err.rstrip("\n"), (rc, err, smsg))
    rc, out, err = fallback(pj, "git add -A && git commit --no-edit")
    check("... and the fallback (block) refuses it as a spec refusal whose "
          "remedy is to stage the file, not 'Stop and tell the operator'",
          rc == 2 and "Commit refused." in err and "could not run" not in err,
          (rc, err[-400:]))
    sh("git add -A && git commit -q --no-edit --no-verify", pj)
    # The INDEX.md variant (re-review MR-5 verifier 1): a correctly traced
    # merge whose only unmerged spec file is INDEX.md passes.
    top, pj = install_below("mr5i", BASE.format(
        extra="  spec_gate_commit_mode: block\n"), "app")
    task(pj, T1, ["src/x.py"])
    write(pj, "src/x.py", "base\n")
    sh("git add -A && git commit -qm t1", pj)
    _ix = ".claude/specs/INDEX.md"
    sh(f"git checkout -qb side && echo side > src/x.py && echo '| s |' >> "
       f"{_ix} && git commit -qam side && git checkout -q main && echo main "
       f"> src/x.py && echo '| m |' >> {_ix} && git commit -qam main", pj)
    sh("git merge -q side", pj)
    write(pj, "src/x.py", "resolved\n")
    sh([GIT, "add", "src/x.py"], pj)
    rc, out, err = chk(pj)
    src_, _, _ = sdk_check(pj)
    check("an unmerged INDEX.md, the merge's own src/x.py listed by a task "
          "file: passes on both substrates, not 'could not run' (MR-5)",
          rc == 0 and src_ == 0, (rc, err, src_))
    sh("git merge --abort", pj)

    print("\n-- the mention rule below the top (MR-7) --")
    top, pj = install_below("mr7", BASE.format(
        extra="  spec_gate_commit_mode: block\n"), "app")
    task(pj, T1, None, body="Implement the parser in "
         "app/src/parser/core.py.\n")
    sh("git commit -qm legacy", pj)
    stage(pj, "src/parser/core.py")
    rc, out, err = chk(pj)
    src_, _, _ = sdk_check(pj)
    check("app/: an older task file (no Files: block) that names the path "
          "from the repository top, as 3d866f4 compared it, still covers it "
          "on both substrates (MR-7)", rc == 0 and src_ == 0, (rc, err))
    stage(pj, "src/parser/other.py")
    rc, out, err = chk(pj)
    src_, _, _ = sdk_check(pj)
    check("... and an unmentioned file there is still refused",
          rc == 2 and out == "src/parser/other.py\n" and src_ == 2, (rc, out))

    print("\n-- a stopped cherry-pick or revert (MR-2) --")
    PICK_TXT = {"pick": ("This is a cherry-pick that stopped on conflicts",
                         "git cherry-pick --abort"),
                "revert": ("This is a revert that stopped on conflicts",
                           "git revert --abort")}
    for kind in ("pick", "revert"):
        d = fresh(GB)
        task(d, T1, ["src/ok.py"])
        write(d, "src/app.py", "1\n2\n3\n4\n5\n")
        sh("git add -A && git commit -qm base", d)
        if kind == "pick":
            sh("git checkout -qb feature", d)
            write(d, "src/app.py", "1\n2\n30\n4\n5\n")
            write(d, "src/billing/pay.py", "p\n")
            sh("git add -A && git commit -qm teammate && git checkout -q main",
               d)
            write(d, "src/app.py", "1\n2\n300\n4\n5\n")
            sh("git commit -qam mine && git cherry-pick feature", d)
            seqf = "CHERRY_PICK_HEAD"
        else:
            write(d, "src/app.py", "1\n2\n30\n4\n5\n")
            write(d, "src/r1.py", "r\n")
            sh("git add -A && git commit -qm teammate", d)
            write(d, "src/app.py", "1\n2\n300\n4\n5\n")
            sh("git commit -qam mine && git revert --no-edit HEAD~1", d)
            seqf = "REVERT_HEAD"
        check(f"(fixture) the {kind} stopped on conflicts ({seqf})",
              os.path.isfile(os.path.join(d, ".git", seqf)))
        write(d, "src/app.py", "1\n2\n3\n4\n5\nresolved\n")
        sh([GIT, "add", "src/app.py"], d)
        rc, out, err = chk(d)
        src_, smsg, _ = sdk_check(d)
        other = "src/billing/pay.py" if kind == "pick" else "src/r1.py"
        check(f"a {kind} stopped on conflicts: only its resolution "
              f"(src/app.py) is checked, not the {other} git applied on its "
              f"own; no unstage advice; shell == SDK (MR-2)",
              rc == 2 and out == "src/app.py\n" and other not in err
              and PICK_TXT[kind][0] in err and PICK_TXT[kind][1] in err
              and "restore --staged" not in err and src_ == 2
              and smsg == err.rstrip("\n"), (rc, out, err, smsg))
        _pp = os.environ["PATH"]
        os.environ["PATH"] = old_path["PATH"]
        try:
            rc_o, out_o, err_o = chk(d, env=dict(old_path))
            src_o, smsg_o, _ = sdk_check(d)
        finally:
            os.environ["PATH"] = _pp
        check(f"... with git 2.37 (no merge-tree --merge-base): the whole "
              f"{kind}, said so, still no unstage advice; shell == SDK",
              rc_o == 2 and other in err_o and "older than 2.40" in err_o
              and "restore --staged" not in err_o and src_o == 2
              and smsg_o == err_o.rstrip("\n"), (rc_o, err_o, smsg_o))
        sh("git cherry-pick --abort" if kind == "pick"
           else "git revert --abort", d)

    print("\n-- the merge remedy follows the mode and merge-back (IT-4) --")
    d = hooked()
    shared_base(d, ["src/m.py"])
    sh("git checkout -qb S && echo b > src/b.py && git add src/b.py && "
       "git commit -qm s --no-verify && git checkout -q main && "
       "echo m > src/mm.py && git add src/mm.py && "
       "git commit -qm m --no-verify", d)
    sh("git merge --no-ff --no-commit -q S && echo e > src/extra.py && "
       "git add src/extra.py", d)
    texts = {}
    for label, env_ in (("block", {"BOOTSTRAP_SPEC_MODE": "block"}),
                        ("warn", {"BOOTSTRAP_SPEC_MODE": "warn"}),
                        ("merge-back", {"BOOTSTRAP_SPEC_MODE": "block",
                                        "BOOTSTRAP_MERGE_BACK": "1"})):
        rc, out, err = chk(d, env=dict(ENV, **env_))
        os.environ.update(env_)
        try:
            src_, smsg, _ = sdk_check(d)
        finally:
            for k_ in env_:
                del os.environ[k_]
        texts[label] = (rc, err, src_ == 2 and smsg == err.rstrip("\n"))
    e_ = texts["block"][1]
    check("block, a hand merge: fix the task file or git merge --abort, then "
          "stop and ask; shell == SDK", texts["block"][0] == 2
          and texts["block"][2] and "git merge --abort, then stop and ask"
          in e_ and "stage that file (git add) and commit again" in e_, e_)
    e_ = texts["warn"][1]
    check("warn: the merge commit goes through, so no git merge --abort and "
          "no 'stop and ask' in the merge sentence; shell == SDK (IT-4)",
          texts["warn"][0] == 2 and texts["warn"][2]
          and "git merge --abort" not in e_ and "This is a merge" in e_
          and "Do not unstage" not in e_, e_)
    e_ = texts["merge-back"][1]
    check("inside merge-back: no 'commit again' and no git merge --abort; "
          "merge-back's Remedy says who fixes it; shell == SDK (IT-4)",
          texts["merge-back"][0] == 2 and texts["merge-back"][2]
          and "git merge --abort" not in e_ and "commit again" not in e_
          and "as merge-back's Remedy below says" in e_
          and "merge-back's Remedy, below, says who makes the fix" in e_, e_)
    sh("git merge --abort", d)

    # ================================================================== #
    # [WP3 fix3] The second re-review's spec-check findings (fix round 3).
    # Each row below fails with its fix reverted; the reverts and mutants
    # are listed in the step report (h1-check).
    print("\n== [WP3 fix3] re-review 2 findings ==")
    AGENT = dict(ENV, CLAUDECODE="1", GIT_EDITOR=":")

    def shimmed(tpl):
        """A fresh copy whose git hooks are the installer's own shim: the
        path an agent commit takes (shim, dispatch, check)."""
        d = fresh(tpl)
        for h in ("pre-commit", "pre-merge-commit"):
            p = os.path.join(d, ".git", "hooks", h)
            with open(p, "w") as fh:
                fh.write(SHIM)
            os.chmod(p, 0o755)
        return d

    def fallback_env(d, env, cmd="git commit -m x"):
        payload = json.dumps({"hook_event_name": "PreToolUse",
                              "tool_name": "Bash",
                              "tool_input": {"command": cmd}})
        return sh([BASH, os.path.join(d, ".claude/hooks/spec-gate-commit.sh")],
                  d, env=dict(env, CLAUDE_PROJECT_DIR=d), inp=payload)

    def ctx_of(out):
        return json.loads(out)["hookSpecificOutput"]["additionalContext"] \
            if out.strip() else ""

    def parents(d):
        return len(sh([GIT, "rev-list", "--parents", "-n1", "HEAD"],
                      d)[1].split()) - 1

    print("\n-- a broken or killed sed or grep (EM-1) --")
    # The mention rule escaped each path with `printf | sed`, unchecked: a
    # sed that was killed, or present and broken, made every path covered
    # (exit 0 with the end line). It escapes in bash now, so sed plays no
    # part; grep's status is read as 0 mentioned, 1 not, else could not run.
    TOOLS = {
        "a broken sed": ("sed", "#!/bin/sh\necho 'sed: error while loading "
                         "shared libraries: libacl.so.1: cannot open shared "
                         "object file' >&2\nexit 127\n"),
        "a killed sed": ("sed", "#!/bin/sh\nkill -9 $$\n"),
        "a broken grep": ("grep", "#!/bin/sh\necho 'grep: error while "
                          "loading shared libraries: libpcre2-8.so.0: cannot "
                          "open shared object file' >&2\nexit 127\n"),
        "a killed grep": ("grep", "#!/bin/sh\nkill -9 $$\n"),
    }
    for label, (tool, text) in TOOLS.items():
        sd_ = os.path.join(TMP, "tool-" + label.replace(" ", "-"))
        os.makedirs(sd_)
        with open(os.path.join(sd_, tool), "w") as fh:
            fh.write(text)
        os.chmod(os.path.join(sd_, tool), 0o755)
        tenv = dict(ENV, PATH=sd_ + os.pathsep + ENV.get("PATH", ""))
        for tpl, mode in ((GB, "block"), (GF, "warn")):
            def setup(d):
                # T2 has no Files: block and mentions src/m.py (the mention
                # rule); INDEX.md is in the harness commit.
                task(d, T1, ["src/a.py"])
                task(d, T2, None, body="Implements src/m.py.\n")
                sh("git commit -qm tasks", d)
                # sed: an unlisted file. grep: one only a mention covers.
                stage(d, "src/b.py" if tool == "sed" else "src/m.py")
            d = shimmed(tpl)
            setup(d)
            h0 = head(d)
            rc, _, err = sh("git commit -qm x", d, env=dict(tenv,
                                                           CLAUDECODE="1"))
            if tool == "sed":
                ok = ("  src/b.py\n" in err and "could not run" not in err
                      and (rc != 0 and head(d) == h0 if mode == "block" else
                           rc == 0 and head(d) != h0
                           and "hooks.spec_gate_commit_mode is warn" in err))
                what = "a spec refusal" if mode == "block" else "a spec warning"
            else:
                ok = ("grep could not search the task files" in err
                      and (rc != 0 and head(d) == h0
                           and templates.SPEC_CHECK_NOT_RUN in err
                           if mode == "block" else
                           rc == 0 and "so the check did not run; commit "
                           "allowed" in err))
                what = ("refused as could not run" if mode == "block" else
                        "allowed with that reason")
            check(f"{mode}, {label} on PATH, an agent commit through the git "
                  f"hook: {what}, never a silent pass (EM-1)", ok,
                  (rc, err[-500:]))
            d = fresh(tpl)
            setup(d)
            rc, out, err = fallback_env(d, tenv)
            ctx = ctx_of(out) if rc == 0 else ""
            if tool == "sed":
                ok = (rc == 2 and "Commit refused." in err and "  src/b.py\n"
                      in err if mode == "block" else
                      rc == 0 and "src/b.py" in ctx
                      and "hooks.spec_gate_commit_mode is warn" in ctx)
            else:
                ok = (rc == 2 and "the spec check could not run (exit 3)" in err
                      and "grep could not search the task files" in err
                      and "Commit refused." not in err if mode == "block" else
                      rc == 0 and "the spec check could not run (exit 3), so "
                      "this commit was not checked" in ctx
                      and "grep could not search" in ctx)
            check(f"{mode}, {label} on PATH, the PreToolUse fallback (no git "
                  f"hook): {what} (EM-1)", ok, (rc, out[-300:], err[-300:]))
            if tool == "sed" and mode == "block":
                rc, out, err = chk(d, env=tenv)
                src_, smsg, _ = sdk_check(d)
                check(f"{label} on PATH: the check refuses src/b.py as the SDK "
                      f"twin (re.escape) does: same rc and text",
                      rc == 2 and out == "src/b.py\n" and src_ == 2
                      and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    # The escape itself, against the sed command it replaced, on names that
    # hold every ERE special character.
    scbody = open(os.path.join(GF, templates.SPEC_CHECK_PATH)).read()
    _esc = re.search(r"\nere_esc\(\)\{\n.*?\n\}\n", scbody, re.S)
    _esc = _esc.group(0) if _esc else "ere_esc(){ :; }\n"
    _names = ["src/a.py", "x[y]z", "a\\b", "(p)|q", "a*b+c?", "^$", "{1,2}",
              "sp ace", "t\tab", "café.py", "q\"u'o", "[]\\.*^$(){}?+|",
              "z" * 300]
    _prog = ("export LC_ALL=C\n" + _esc + 'for n in "$@"; do ere_esc "$n"; '
             "printf '%s\\000' \"$ERE\"; printf '%s' \"$n\" | "
             "sed 's/[][\\.*^$(){}?+|]/\\\\&/g'; printf '\\000'; done\n")
    rc, out, err = sh([BASH, "-c", _prog, "_", *_names], TMP)
    _pairs = out.split("\0")[:-1]
    check("ere_esc in bash escapes exactly what `sed 's/[][\\.*^$(){}?+|]/"
          "\\\\&/g'` escaped (EM-1)", rc == 0 and len(_pairs) == 2 * len(_names)
          and all(_pairs[i] == _pairs[i + 1] for i in range(0, len(_pairs), 2)),
          (rc, err, _pairs[:6]))
    _code = [ln for ln in scbody.splitlines()
             if not ln.lstrip().startswith("#")]
    check("the check needs no sed any more (no sed command in its code)",
          not [ln for ln in _code if re.search(r"(^|[|;&(]|\$\()\s*sed\b", ln)],
          [ln for ln in _code if "sed" in ln])

    print("\n-- a backslash in TMPDIR (MR2-2, EM-2) --")
    # awk escape-processed `-v L=$TMPD/q0`, so with any backslash in TMPDIR
    # the list q0 never matched FILENAME, nothing was kept, and a merge, an
    # octopus merge or a stopped pick passed. The lists are told apart by
    # ARGV now.
    BSDIRS = []
    for nm in ("back\\slash", "x\\ty"):
        p = os.path.join(TMP, nm)
        os.makedirs(p)
        BSDIRS.append(p)

    def bs_states():
        """(label, repo) in each state, with an unlisted src/evil.py staged
        inside it; T1 lists every other path the state changes."""
        out_ = []
        d = fresh(GB)
        task(d, T1, ["src/m.py", "src/app.py"])
        sh("git commit -qm t1 && mkdir -p src && git checkout -qb side && "
           "echo s > src/s.py && git add src/s.py && git commit -qm s && "
           "git checkout -q main && mkdir -p src && echo m > src/mm.py && "
           "git add src/mm.py && git commit -qm m && "
           "git merge --no-ff --no-commit -q side", d)
        stage(d, "src/evil.py")
        check("(fixture) the merge is in progress, one other parent",
              len(read_(os.path.join(d, ".git", "MERGE_HEAD")) or "")
              == 41)
        out_.append(("a merge (the merge-tree rule)", d))
        d = fresh(GB)
        task(d, T1, ["src/m.py"])
        sh("git commit -qm t1 && mkdir -p src && git checkout -qb s1 && "
           "echo 1 > src/s1.py && git add src/s1.py && git commit -qm s1 && "
           "git checkout -q main && git checkout -qb s2 && mkdir -p src && "
           "echo 2 > src/s2.py && git add src/s2.py && git commit -qm s2 && "
           "git checkout -q main "
           "&& git merge --no-commit -q s1 s2", d)
        stage(d, "src/evil.py")
        check("(fixture) the octopus merge is in progress, two other "
              "parents", len((read_(os.path.join(d, ".git", "MERGE_HEAD"))
                              or "").split()) == 2)
        out_.append(("an octopus merge (the every-parent rule)", d))
        d = fresh(GB)
        task(d, T1, ["src/app.py"])
        write(d, "src/app.py", "1\n2\n3\n")
        sh("git add -A && git commit -qm base && git checkout -qb f", d)
        write(d, "src/app.py", "1\n20\n3\n")
        sh("git commit -qam f && git checkout -q main", d)
        write(d, "src/app.py", "1\n200\n3\n")
        sh("git commit -qam mine && git cherry-pick f", d)
        write(d, "src/app.py", "1\n2000\n3\n")
        sh([GIT, "add", "src/app.py"], d)
        stage(d, "src/evil.py")
        check("(fixture) the cherry-pick stopped (CHERRY_PICK_HEAD)",
              os.path.isfile(os.path.join(d, ".git", "CHERRY_PICK_HEAD")))
        out_.append(("a stopped cherry-pick (merge-tree --merge-base)", d))
        return out_

    for label, d in bs_states():
        rc0, out0, _ = chk(d)
        src_, smsg, _ = sdk_check(d)
        check(f"(control) {label}, a plain TMPDIR: only src/evil.py, shell "
              f"== SDK", rc0 == 2 and out0 == "src/evil.py\n" and src_ == 2,
              (rc0, out0, src_))
        for bsd in BSDIRS:
            rc, out, err = chk(d, env=dict(ENV, TMPDIR=bsd))
            check(f"{label}, TMPDIR {os.path.basename(bsd)!r}: src/evil.py is "
                  f"refused, as with a plain TMPDIR (MR2-2)",
                  rc == 2 and out == "src/evil.py\n"
                  and err.rstrip("\n") == smsg, (rc, out, err[-300:]))
    d = shimmed(GB)
    task(d, T1, ["src/m.py"])
    sh("git commit -qm t1 && mkdir -p src && git checkout -qb side && "
       "echo s > src/s.py && git add src/s.py && git commit -qm s && "
       "git checkout -q main && git merge --no-ff --no-commit -q side", d)
    stage(d, "src/evil.py")
    check("(fixture) the merge is in progress",
          os.path.isfile(os.path.join(d, ".git", "MERGE_HEAD")))
    h0 = head(d)
    rc, _, err = sh("git commit -q --no-edit", d,
                    env=dict(AGENT, TMPDIR=BSDIRS[0]))
    check("block, TMPDIR with a backslash: an agent's merge commit with an "
          "unlisted edit made inside it is refused through the git hook "
          "(MR2-2)", rc != 0 and head(d) == h0 and "  src/evil.py\n" in err,
          (rc, err[-300:]))
    sh("git merge --abort", d)

    print("\n-- a TMPDIR with room for part of the work (CRIT2-1) --")
    # The changed list and the merge's kept lists were written by bash's
    # printf in a loop, unchecked: with room for git's list but not for
    # bash's copy, the copy came out short and the check passed. Each row
    # tries every amount of free space from none to more than the check
    # needs (so the size that holds RAW only is among them), and where a
    # list is created by a redirect, every count of free inodes with little
    # space (a redirect that fails while bash's own message is lost too). A
    # pass is never right.
    US = shutil.which("unshare")
    MNT = os.path.join(TMP, "mnt")
    os.makedirs(MNT)
    SWEEP = (r'M="$1"; FREE="$2"; INO="$3"; shift 3; '
             r'o=size=64k; [ "$INO" = - ] || o="$o,nr_inodes=$INO"; '
             r'mount -t tmpfs -o "$o" tmpfs "$M" || exit 99; '
             r'n=$(( (16 - FREE) * 4096 )); '
             r'[ "$n" -gt 0 ] && head -c "$n" /dev/zero >"$M/fill"; '
             r'export TMPDIR="$M"; exec "$@"')
    _probe = (sh([US, "--user", "--map-root-user", "--mount", BASH, "-c",
                  SWEEP, "_", MNT, "1", "-", "true"], TMP)
              if US else (1, "", ""))
    if _probe[0] != 0:
        print("  SKIP  the full-TMPDIR rows: `unshare --user --map-root-user "
              "--mount` cannot mount a tmpfs here (%s)"
              % (_probe[2].strip()[:120] or "no unshare"))
    else:
        def sweep(cwd, argv, env, inp=None, inodes=False):
            cells = [(free, "-") for free in range(0, 13)]
            if inodes:
                cells += [(free, str(ino)) for ino in range(3, 11)
                          for free in range(0, 5)]
            res = []
            for free, ino in cells:
                rc, out, err = sh([US, "--user", "--map-root-user", "--mount",
                                   BASH, "-c", SWEEP, "_", MNT, str(free), ino,
                                   *argv], cwd, env=env, inp=inp)
                res.append(((free, ino), rc, out, err))
            return res

        def judged(res, what, want="src/evil.py\n"):
            """No cell gives a pass, or a refusal without its message; some
            give exit 3 (the check could not run); the most room gives the
            real refusal."""
            passes = [(c, rc) for c, rc, out, _ in res
                      if rc == 0 and out.endswith(END + "\n")]
            mute = [c for c, rc, _, err in res if rc == 2 and
                    "not listed in any task file's Files: block" not in err]
            nr = [c for c, rc, out, _ in res if rc == 3 and END not in out]
            last = res[12]
            check(f"full TMPDIR, {what}: no amount of free space"
                  f"{' or of free inodes' if len(res) > 13 else ''} makes "
                  f"the check pass or lose its message; where it cannot "
                  f"write, it exits 3 with no end line (CRIT2-1)",
                  not passes and not mute and nr and last[1] == 2
                  and last[2] == want + END + "\n",
                  (passes, mute, nr, [(c, rc) for c, rc, _, _ in res]))
        SC_ = templates.SPEC_CHECK_PATH
        d = fresh(GB)
        task(d, T1, ["src/listed.py"])
        sh("git commit -qm t1", d)
        stage(d, "src/evil.py")
        judged(sweep(d, [BASH, os.path.join(d, SC_), "--staged"], ENV,
                     inodes=True), "a plain commit")
        judged(sweep(d, [BASH, os.path.join(d, SC_), "--files", "src/a.py",
                         "src/evil.py"], ENV), "--files PATH...",
               want="src/a.py\nsrc/evil.py\n")
        judged(sweep(d, [BASH, os.path.join(d, SC_), "--files", "-"], ENV,
                     inp="src/evil.py\n", inodes=True), "--files - (lines)")
        judged(sweep(d, [BASH, os.path.join(d, SC_), "-z", "--files", "-"],
                     ENV, inp="src/evil.py\0", inodes=True),
               "-z --files - (NUL-separated)")
        d = fresh(GB)
        task(d, T1, ["src/m.py"])
        sh("git commit -qm t1 && mkdir -p src && git checkout -qb side && "
           "echo s > src/s.py && git add src/s.py && git commit -qm s && "
           "git checkout -q main && mkdir -p src && echo m > src/mm.py && "
           "git add src/mm.py && git commit -qm m && "
           "git merge --no-ff --no-commit -q side", d)
        stage(d, "src/evil.py")
        check("(fixture) the merge is in progress",
              os.path.isfile(os.path.join(d, ".git", "MERGE_HEAD")))
        judged(sweep(d, [BASH, os.path.join(d, SC_), "--staged"], ENV),
               "a merge with an edit made inside it (its kept list)")
        # The conflicted list: a rename/rename conflict resolved by keeping
        # both names is kept only through it (MR-1).
        d = fresh(GB)
        task(d, T1, ["src/m.py", "src/b.py"])
        write(d, "src/a.py", "".join(f"{i}\n" for i in range(1, 31)))
        sh("git add -A && git commit -qm base && git checkout -qb R && "
           "git mv src/a.py src/c.py && git commit -qm r && git checkout -q "
           "main && git mv src/a.py src/b.py && git commit -qm m && "
           "git merge -q R", d)
        sh("git add src/b.py src/c.py && git rm -q --cached src/a.py", d)
        judged(sweep(d, [BASH, os.path.join(d, SC_), "--staged"], ENV),
               "a rename/rename merge (its conflicted list)",
               want="src/c.py\n")
        payload = json.dumps({"hook_event_name": "PreToolUse",
                              "tool_name": "Bash",
                              "tool_input": {"command": "git commit -m x"}})
        for mode in ("block", "warn"):
            top, pj = install_below("full-" + mode, BASE.format(
                extra=f"  spec_gate_commit_mode: {mode}\n"), "app")
            task(pj, T1, ["src/listed.py"])
            sh("git commit -qm t1", pj)
            stage(pj, "src/evil.py")
            # A path outside the project, listed last: the loop that keeps
            # the project's paths skips it, so a write that failed before it
            # is not the loop's last status.
            write(top, "zz/outside.txt", "o\n")
            sh([GIT, "add", "zz/outside.txt"], top)
            res = sweep(pj, [BASH, os.path.join(
                pj, ".claude/hooks/spec-gate-commit.sh")],
                dict(ENV, CLAUDE_PROJECT_DIR=pj), inp=payload)
            if mode == "block":
                # A spec refusal names the file, even when the check's full
                # message could not be kept in TMPDIR (the fallback keeps it
                # there); otherwise the check could not run.
                bad = [(c, rc, err[-160:]) for c, rc, _, err in res
                       if rc != 2 or not (("Commit refused." in err
                                           and "src/evil.py" in err)
                                          or "could not run" in err)]
                check("full TMPDIR, block, below the top (the fallback is the "
                      "only check): refused at every amount of free space, "
                      "naming src/evil.py or saying the check could not run; "
                      "never allowed (CRIT2-1)", not bad
                      and "Commit refused." in res[-1][3]
                      and any("could not run" in err for _, _, _, err in res),
                      bad)
            else:
                bad = [(c, rc, out[-160:]) for c, rc, out, _ in res
                       if rc != 0 or not ("src/evil.py" in ctx_of(out)
                                          or "could not run" in ctx_of(out))]
                check("full TMPDIR, warn, below the top: allowed at every "
                      "amount of free space, never silently: the warning "
                      "names src/evil.py, or says the check could not run "
                      "(CRIT2-1)", not bad, bad)

    print("\n-- a merge of unrelated histories (MR2-1) --")
    # merge-tree refuses unrelated histories unless told: the check could not
    # run on an import, and in block mode the merge was refused.
    def unrelated(tpl):
        d = shimmed(tpl)
        task(d, T1, ["src/listed.py"])
        sh("git commit -qm t1 && git checkout -q --orphan other && "
           "git rm -rqf . && mkdir -p lib vendor && echo i > lib/imported.py "
           "&& echo v > vendor/v.txt && git add lib/imported.py vendor/v.txt "
           "&& git commit -qm import && git checkout -q main", d)
        return d
    d = unrelated(GB)
    h0 = head(d)
    rc, _, err = sh("git merge --allow-unrelated-histories --no-edit -q other",
                    d, env=AGENT)
    check("block, an agent's merge of an unrelated history (an import of "
          "lib/imported.py): lands, with no spec message (MR2-1)",
          rc == 0 and head(d) != h0 and parents(d) == 2
          and "spec check" not in err, (rc, err[-400:]))
    d = unrelated(GB)
    sh("git merge --allow-unrelated-histories --no-commit -q other", d)
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("... in progress (--no-commit), clean: exit 0 on the check and the "
          "SDK twin, not 3 ('refusing to merge unrelated histories')",
          rc == 0 and src_ == 0, (rc, err, src_, smsg))
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("... with an unlisted src/evil.py staged inside it: only that file, "
          "shell == SDK", rc == 2 and out == "src/evil.py\n" and src_ == 2
          and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    h0 = head(d)
    rc, _, err = sh("git commit -q --no-edit", d, env=AGENT)
    check("... and the agent's commit of it is refused through the git hook",
          rc != 0 and head(d) == h0 and "  src/evil.py\n" in err
          and "lib/imported.py" not in err, (rc, err[-300:]))

    print("\n-- a picked or reverted merge commit, a root commit (MR2-4) --")
    d = shimmed(GB)
    task(d, T1, ["src/ok.py"])
    write(d, "src/shared.py", "a\nb\nc\n")
    sh("git add -A && git commit -qm base && git checkout -qb side", d)
    write(d, "src/shared.py", "a\nside\nc\n")
    write(d, "src/teammate.py", "t\n")
    sh("git add -A && git commit -qm side && git checkout -q main && "
       "git merge --no-ff -q -m M side", d)
    write(d, "src/shared.py", "a\nmain2\nc\n")
    sh("git commit -qam main2", d)
    sh("git revert -m 1 --no-edit HEAD~1", d, env=AGENT)
    check("(fixture) the revert -m 1 of merge M stopped on conflicts",
          os.path.isfile(os.path.join(d, ".git", "REVERT_HEAD")))
    write(d, "src/shared.py", "a\nresolved\nc\n")
    sh([GIT, "add", "src/shared.py"], d)
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    WHOLE_MERGE = ("its commit is a merge or has no parent, so the resolution "
                   "cannot be told from the rest of the change: this is all "
                   "of it")
    check("a revert -m 1 of a merge, stopped: the whole change, with the true "
          "reason (not 'this git, older than 2.40'), shell == SDK (MR2-4)",
          rc == 2 and out == "src/shared.py\nsrc/teammate.py\n"
          and WHOLE_MERGE in err and "older than 2.40" not in err
          and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    h0 = head(d)
    rc, _, err = sh("git revert --continue", d, env=AGENT)
    check("... concluded with git revert --continue: refused through the git "
          "hook with that reason, no unstage advice",
          rc != 0 and head(d) == h0 and WHOLE_MERGE in err
          and "older than 2.40" not in err and "restore --staged" not in err,
          (rc, err[-400:]))
    sh("git revert --abort", d)
    d = fresh(GB)
    task(d, T1, ["src/ok.py"])
    write(d, "src/shared.py", "a\nb\n")
    sh("git add -A && git commit -qm base && git checkout -q --orphan root && "
       "git rm -rqf . && mkdir -p src && printf 'a\\nroot\\n' > src/shared.py "
       "&& echo r > src/r.py && git add src/shared.py src/r.py && "
       "git commit -qm root && git checkout -q main && git cherry-pick root",
       d)
    write(d, "src/shared.py", "a\nresolved\n")
    sh([GIT, "add", "src/shared.py"], d)
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a cherry-pick of a root commit, stopped: the whole change, with "
          "the same true reason, shell == SDK (MR2-4)",
          rc == 2 and "  src/r.py\n" in err and WHOLE_MERGE in err
          and "older than 2.40" not in err and src_ == 2
          and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    sh("git cherry-pick --abort", d)

    print("\n-- a git commit while a rebase or git am is stopped (MR2-3) --")
    # [WP3 fix4 RR3-CHK-1, fix5 R4-3] The rebase remedy, true at every stop:
    # a conflict or edit stop names the commit it replays (REBASE_HEAD), and
    # says how to see its files; an exec or break stop names none.
    REBASE_KEEP = ("It replays the commit REBASE_HEAD names (git show --stat "
                   "REBASE_HEAD lists its files). Until that commit is made "
                   "(it is made if git rev-parse HEAD REBASE_HEAD prints one "
                   "object name twice), do not unstage a file it changed: "
                   "that drops part of that commit. Any other file can be unstaged (git restore "
                   "--staged <path>), and so can any file once that commit is "
                   "made.")
    REBASE_ANY = "Any file here can be unstaged (git restore --staged <path>)."
    REBASE_NONE = ("(git names no commit it is replaying here, as at an exec "
                   "or break stop, so this is all of the change)")
    # A rebase or `git am` that stops fires no hook on --continue, but a
    # `git commit` made during the stop fires pre-commit. It took the plain
    # rule: the whole replayed commit, a teammate's file included, with
    # "unstage it"; following that, the rebase completed without the file.
    def teammate(d, listed):
        task(d, T1, listed)
        write(d, "src/shared.py", "a\nb\nc\n")
        sh("git add -A && git commit -qm base && git checkout -qb feature", d)
        write(d, "src/shared.py", "a\nfeature\nc\n")
        write(d, "src/teammate.py", "t\n")
        sh("git add -A && git commit -qm 'teammate: feature X' && "
           "git checkout -q main", d)
        write(d, "src/shared.py", "a\nmain\nc\n")
        sh("git commit -qam mine", d)

    d = shimmed(GB)
    teammate(d, ["src/ok.py"])
    sh("git checkout -q feature && git rebase -q main", d, env=AGENT)
    check("(fixture) the rebase stopped (rebase-merge/, REBASE_HEAD)",
          os.path.isdir(os.path.join(d, ".git", "rebase-merge"))
          and os.path.isfile(os.path.join(d, ".git", "REBASE_HEAD")))
    write(d, "src/shared.py", "a\nresolved\nc\n")
    sh([GIT, "add", "src/shared.py"], d)
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a rebase stopped on conflicts: judged as a stopped pick, so only "
          "its resolution (src/shared.py), not the teammate's file git "
          "applied; never unstage a file the replayed commit changed; git "
          "rebase --abort; shell == SDK (MR2-3, RR3-CHK-1)",
          rc == 2 and out == "src/shared.py\n"
          and "This is a rebase that stopped" in err
          and "git rebase --abort" in err and REBASE_KEEP in err
          and "unstage it (git restore --staged" not in err
          and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    h0 = head(d)
    rc, _, err = sh("git commit -q --no-edit", d, env=AGENT)
    check("... and the agent's git commit during the stop is refused through "
          "the git hook on that file alone",
          rc != 0 and head(d) == h0 and "  src/shared.py\n" in err
          and "src/teammate.py" not in err, (rc, err[-400:]))
    sh("git rebase --abort", d)
    d = shimmed(GB)
    teammate(d, ["src/ok.py", "src/shared.py"])
    sh("git checkout -q feature && git rebase -q main", d, env=AGENT)
    write(d, "src/shared.py", "a\nresolved\nc\n")
    sh([GIT, "add", "src/shared.py"], d)
    rc, _, err = sh("git commit -q --no-edit && git rebase --continue", d,
                    env=AGENT)
    rc2, files, _ = sh([GIT, "ls-tree", "-r", "--name-only", "HEAD", "src"], d)
    check("a rebase whose resolution is listed: the agent's git commit lands "
          "(the teammate's file is not the agent's), and the rebase completes "
          "with it (MR2-3)", rc == 0 and "src/teammate.py" in files.split()
          and not os.path.isdir(os.path.join(d, ".git", "rebase-merge")),
          (rc, err[-400:], files))

    d = shimmed(GB)
    teammate(d, ["src/ok.py"])
    _mbox = os.path.join(TMP, "teammate.mbox")
    sh(f"git format-patch -1 --stdout feature > '{_mbox}' && "
       f"git am -q -3 '{_mbox}'", d, env=AGENT)
    check("(fixture) git am -3 stopped (rebase-apply/, no REBASE_HEAD)",
          os.path.isfile(os.path.join(d, ".git", "rebase-apply", "applying"))
          and not os.path.exists(os.path.join(d, ".git", "REBASE_HEAD")))
    write(d, "src/shared.py", "a\nresolved\nc\n")
    sh([GIT, "add", "src/shared.py"], d)
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("git am -3 stopped: the whole patch is checked, with a true reason; "
          "no unstage advice; git am --abort; shell == SDK (MR2-3)",
          rc == 2 and out == "src/shared.py\nsrc/teammate.py\n"
          and "This is a git am that stopped" in err
          and "git am applies a patch, not a commit" in err
          and "git am --abort" in err and "restore --staged" not in err
          and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    h0 = head(d)
    rc, _, err = sh("git commit -q -m x", d, env=AGENT)
    check("... and the agent's git commit during the stop is refused through "
          "the git hook with that text", rc != 0 and head(d) == h0
          and "git am --abort" in err and "restore --staged" not in err,
          (rc, err[-400:]))
    sh("git am --abort", d)
    # The apply backend (rebase-apply/, REBASE_HEAD) is a rebase too; a
    # rebase stopped at `break` names no commit (no REBASE_HEAD).
    d = fresh(GB)
    teammate(d, ["src/ok.py"])
    sh("git checkout -q feature && git rebase --apply -q main", d)
    check("(fixture) git rebase --apply stopped (rebase-apply/rebasing, "
          "REBASE_HEAD)", os.path.isfile(os.path.join(
              d, ".git", "rebase-apply", "rebasing"))
          and os.path.isfile(os.path.join(d, ".git", "REBASE_HEAD")))
    write(d, "src/shared.py", "a\nresolved\nc\n")
    sh([GIT, "add", "src/shared.py"], d)
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("git rebase --apply stopped: judged as a stopped pick too (only "
          "src/shared.py), git rebase --abort; shell == SDK (MR2-3)",
          rc == 2 and out == "src/shared.py\n"
          and "This is a rebase that stopped" in err
          and "git rebase --abort" in err and REBASE_KEEP in err and src_ == 2
          and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    sh("git rebase --abort", d)
    d = fresh(GB)
    teammate(d, ["src/ok.py"])
    sh("GIT_SEQUENCE_EDITOR=\"sed -i.b '1a break'\" git rebase -q -i HEAD~1",
       d)
    check("(fixture) a rebase stopped at break (rebase-merge/, no "
          "REBASE_HEAD)", os.path.isdir(os.path.join(d, ".git",
                                                    "rebase-merge"))
          and not os.path.exists(os.path.join(d, ".git", "REBASE_HEAD")))
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a rebase stopped at break, with an edit staged: the whole change, "
          "said so (no commit named), with no claim that a resolution or a "
          "replayed commit is in it; any file there can be unstaged; "
          "shell == SDK (MR2-3, RR3-CHK-1, R4-3)",
          rc == 2 and out == "src/evil.py\n"
          and REBASE_NONE in err and "resolution" not in err
          and "drops part of" not in err
          and REBASE_ANY in err and "REBASE_HEAD" not in err
          and "git rebase --abort" in err
          and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    sh("git reset -q && git rebase --abort", d)
    # [WP3 fix4 RR3-CHK-1] The edit and exec stops replay nothing past HEAD
    # either: the verdict is unchanged (the agent's file is refused), and
    # the text no longer says unstaging it drops part of a replayed commit.
    d = fresh(GB)
    teammate(d, ["src/ok.py"])
    sh("GIT_SEQUENCE_EDITOR=\"sed -i.b '1s/^pick/edit/'\" "
       "git rebase -q -i HEAD~1", d)
    check("(fixture) a rebase stopped at edit (rebase-merge/amend, "
          "REBASE_HEAD)", os.path.isfile(os.path.join(
              d, ".git", "rebase-merge", "amend"))
          and os.path.isfile(os.path.join(d, ".git", "REBASE_HEAD")))
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a rebase stopped at edit, with a new file staged: still refused; "
          "the text names REBASE_HEAD and says git has made it at an edit "
          "stop; no 'Do not unstage a file from it'; shell == SDK "
          "(RR3-CHK-1, R4-3)",
          rc == 2 and out == "src/evil.py\n"
          and "This is a rebase that stopped" in err
          and "an edit made while it was stopped" in err
          and REBASE_KEEP in err
          and "Do not unstage a file from it" not in err
          and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    sh("git reset -q && git rebase --abort", d)
    d = fresh(GB)
    teammate(d, ["src/ok.py"])
    sh("GIT_SEQUENCE_EDITOR=: git rebase -q -i -x false HEAD~1", d)
    check("(fixture) a rebase stopped at a failed exec (rebase-merge/, no "
          "REBASE_HEAD)", os.path.isdir(os.path.join(d, ".git",
                                                    "rebase-merge"))
          and not os.path.exists(os.path.join(d, ".git", "REBASE_HEAD")))
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a rebase stopped at exec, with a new file staged: still refused, "
          "with no claim that a resolution or a replayed commit is in it; a "
          "file added there can be unstaged; shell == SDK (RR3-CHK-1, R4-3)",
          rc == 2 and out == "src/evil.py\n" and REBASE_NONE in err
          and "resolution" not in err
          and "Do not unstage a file from it" not in err
          and "drops part of" not in err
          and REBASE_ANY in err and "REBASE_HEAD" not in err
          and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    sh("git reset -q && git rebase --abort", d)

    print("\n-- a reftable repository: the stop heads are refs, not files "
          "(R4-1, CRIT7-1) --")
    # [WP3 fix5 R4-1, CRIT7-1] A reftable repository (git 2.45 or later)
    # keeps REBASE_HEAD, CHERRY_PICK_HEAD and REVERT_HEAD in the ref store,
    # with no file at --git-path. Read as files, a stopped rebase said git
    # names no commit and allowed unstaging any other file, and a stopped
    # cherry-pick or revert took the plain rule ("unstage it"): following
    # either dropped the replayed or picked commit's change (measured, git
    # 2.56). Each row also follows the printed remedy to the end.
    _rtp = os.path.join(TMP, "rtprobe")
    os.makedirs(_rtp)
    GBR = None
    if sh([GIT, "init", "-q", "--ref-format=reftable"], _rtp)[0] != 0:
        print("  SKIP  the reftable rows: this git cannot init "
              "--ref-format=reftable (git 2.45 or later)")
    else:
        GBR = install("gbr", BASE.format(
            extra="  spec_gate_commit_mode: block\n"),
            init=("--ref-format=reftable",))

        def rt_head(d, name):
            return (not os.path.exists(os.path.join(d, ".git", name))
                    and sh([GIT, "rev-parse", "-q", "--verify", name],
                           d)[0] == 0)

        d = fresh(GBR)
        teammate(d, ["src/ok.py"])
        sh("git checkout -q feature && git rebase -q main", d, env=AGENT)
        check("(fixture) reftable: the rebase stopped, REBASE_HEAD is a ref "
              "with no file",
              sh([GIT, "rev-parse", "--show-ref-format"], d)[1] ==
              "reftable\n" and os.path.isdir(os.path.join(
                  d, ".git", "rebase-merge")) and rt_head(d, "REBASE_HEAD"))
        write(d, "src/shared.py", "a\nresolved\nc\n")
        sh([GIT, "add", "src/shared.py"], d)
        stage(d, "src/extra.py")
        rc, out, err = chk(d)
        src_, smsg, _ = sdk_check(d)
        check("reftable, a rebase stopped on conflicts: judged as a stopped "
              "pick (the resolution and the agent's own file, not the "
              "teammate's), and the text names REBASE_HEAD, not 'git names no "
              "commit'; shell == SDK (R4-1)",
              rc == 2 and out == "src/extra.py\nsrc/shared.py\n"
              and REBASE_KEEP in err and REBASE_NONE not in err
              and "src/teammate.py" not in err
              and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
        _, st, _ = sh("git show --stat --format= REBASE_HEAD", d)
        sh("git restore --staged src/extra.py && rm src/extra.py", d)
        task(d, T1, ["src/ok.py", "src/shared.py"])
        rc1, _, _ = chk(d)
        rc2, _, e2 = sh("git rebase --continue", d, env=AGENT)
        _, tm, _ = sh("git show HEAD:src/teammate.py", d)
        check("... and following it (unstage the file git show --stat "
              "REBASE_HEAD does not list, list the resolution, git rebase "
              "--continue) keeps the replayed commit's teammate file (R4-1)",
              "src/teammate.py" in st and "src/extra.py" not in st
              and rc1 == 0 and rc2 == 0 and tm == "t\n"
              and not os.path.isdir(os.path.join(d, ".git", "rebase-merge")),
              (st, rc1, rc2, e2[-300:], tm))

        for kind in ("pick", "revert"):
            d = fresh(GBR)
            task(d, T1, ["src/ok.py"])
            write(d, "src/app.py", "1\n2\n3\n4\n5\n")
            sh("git add -A && git commit -qm base", d)
            if kind == "pick":
                sh("git checkout -qb feature", d)
                write(d, "src/app.py", "1\n2\n30\n4\n5\n")
                write(d, "src/billing/pay.py", "p\n")
                sh("git add -A && git commit -qm teammate && "
                   "git checkout -q main", d)
                write(d, "src/app.py", "1\n2\n300\n4\n5\n")
                sh("git commit -qam mine && git cherry-pick feature", d)
                seqf, other = "CHERRY_PICK_HEAD", "src/billing/pay.py"
            else:
                write(d, "src/app.py", "1\n2\n30\n4\n5\n")
                write(d, "src/r1.py", "r\n")
                sh("git add -A && git commit -qm teammate", d)
                write(d, "src/app.py", "1\n2\n300\n4\n5\n")
                sh("git commit -qam mine && git revert --no-edit HEAD~1", d)
                seqf, other = "REVERT_HEAD", "src/r1.py"
            check(f"(fixture) reftable: the {kind} stopped on conflicts, "
                  f"{seqf} is a ref with no file", rt_head(d, seqf))
            write(d, "src/app.py", "1\n2\n3\n4\n5\nresolved\n")
            sh([GIT, "add", "src/app.py"], d)
            rc, out, err = chk(d)
            src_, smsg, _ = sdk_check(d)
            check(f"reftable, a {kind} stopped on conflicts: only its "
                  f"resolution (src/app.py), not {other}; its own text, no "
                  f"unstage advice; shell == SDK (CRIT7-1)",
                  rc == 2 and out == "src/app.py\n" and other not in err
                  and PICK_TXT[kind][0] in err and PICK_TXT[kind][1] in err
                  and "Do not unstage a file from it" in err
                  and "restore --staged" not in err and src_ == 2
                  and smsg == err.rstrip("\n"), (rc, out, err, smsg))
            task(d, T1, ["src/ok.py", "src/app.py"])
            rc1, _, _ = chk(d)
            verb = "cherry-pick" if kind == "pick" else "revert"
            rc2, _, e2 = sh(f"git {verb} --continue", d, env=AGENT)
            _, files, _ = sh([GIT, "ls-tree", "-r", "--name-only", "HEAD",
                              "src"], d)
            kept = (other in files.split()) if kind == "pick" \
                else (other not in files.split())
            check(f"... and following it (list the resolution, git {verb} "
                  f"--continue) keeps the {kind}'s change to {other} "
                  f"(CRIT7-1)", rc1 == 0 and rc2 == 0 and kept
                  and not rt_head(d, seqf), (rc1, rc2, e2[-300:], files))

        d = fresh(GBR)
        teammate(d, ["src/ok.py"])
        sh("GIT_SEQUENCE_EDITOR=\"sed -i.b '1s/^pick/edit/'\" "
           "git rebase -q -i HEAD~1", d)
        stage(d, "src/evil.py")
        rc, out, err = chk(d)
        src_, smsg, _ = sdk_check(d)
        check("reftable, a rebase stopped at edit (REBASE_HEAD a ref): the "
              "same text as on the files backend; shell == SDK (R4-1, R4-3)",
              rt_head(d, "REBASE_HEAD") and rc == 2
              and out == "src/evil.py\n" and REBASE_KEEP in err
              and "an edit made while it was stopped" in err
              and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
        sh("git reset -q && git rebase --abort", d)
        d = fresh(GBR)
        teammate(d, ["src/ok.py"])
        sh("GIT_SEQUENCE_EDITOR=\"sed -i.b '1a break'\" git rebase -q -i "
           "HEAD~1", d)
        stage(d, "src/evil.py")
        rc, out, err = chk(d)
        src_, smsg, _ = sdk_check(d)
        check("reftable, a rebase stopped at break: no REBASE_HEAD ref "
              "either, so 'git names no commit' and any file can be "
              "unstaged; shell == SDK (R4-1)",
              sh([GIT, "rev-parse", "-q", "--verify", "REBASE_HEAD"], d)[0]
              != 0 and rc == 2 and out == "src/evil.py\n"
              and REBASE_NONE in err and REBASE_ANY in err
              and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
        sh("git reset -q && git rebase --abort", d)

    # [WP3 fix5 R4-1] A head is read only where its name resolves to itself:
    # a branch called CHERRY_PICK_HEAD, REVERT_HEAD or REBASE_HEAD (git
    # allows them, and rev-parse --verify finds them) is not a stop.
    d = fresh(GB)
    task(d, T1, ["src/ok.py"])
    sh("git commit -qm t1 && git branch CHERRY_PICK_HEAD && "
       "git branch REVERT_HEAD", d)
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a plain commit in a repository with branches named "
          "CHERRY_PICK_HEAD and REVERT_HEAD: the plain rule and its "
          "unstage remedy, not a stopped cherry-pick; shell == SDK (R4-1)",
          rc == 2 and out == "src/evil.py\n" and "cherry-pick" not in err
          and "revert" not in err and "This is" not in err
          and "unstage it (git restore --staged <path>)" in err
          and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    sh([GIT, "reset", "-q"], d)
    d = fresh(GB)
    teammate(d, ["src/ok.py"])
    sh("git branch REBASE_HEAD main && GIT_SEQUENCE_EDITOR=\"sed -i.b '1a "
       "break'\" git rebase -q -i HEAD~1", d)
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a rebase stopped at break, with a branch named REBASE_HEAD: still "
          "no commit named; shell == SDK (R4-1)",
          rc == 2 and out == "src/evil.py\n" and REBASE_NONE in err
          and REBASE_ANY in err and src_ == 2
          and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    sh("git reset -q && git rebase --abort", d)
    # [WP3 fix5 R4-1] A CHERRY_PICK_HEAD file that names no object is no
    # cherry-pick to git (a git commit then lands, measured on 2.56), and
    # is none to the check either; read as a file it stopped the check
    # with "is not an object name" (exit 3).
    d = fresh(GB)
    task(d, T1, ["src/ok.py"])
    sh("git commit -qm t1", d)
    write(d, ".git/CHERRY_PICK_HEAD", "garbage\n")
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a CHERRY_PICK_HEAD file that names no object: the plain rule, as "
          "git itself reads it; shell == SDK (R4-1)",
          rc == 2 and out == "src/evil.py\n" and "cherry-pick" not in err
          and "not an object name" not in err and src_ == 2
          and smsg == err.rstrip("\n"), (rc, out, err, smsg))

    # [WP3 fix6 RV5-SC-1] A branch or tag with a head's name, beside a real
    # stop: rev-parse --symbolic-full-name failed as ambiguous, so a stopped
    # rebase read as one that names no commit ("Any file here can be
    # unstaged") and a stopped cherry-pick took the plain rule; following
    # the rebase text dropped the teammate's file. On both backends: the
    # file itself, else (reftable) show-ref --verify, names no branch or tag.
    def named_refs(d, name, at="main"):
        sh(f"git branch {name} {at} && git tag {name} {at}", d)

    def has_named(d, name):
        return all(sh([GIT, "show-ref", "--verify", "-q", r], d)[0] == 0
                   for r in (f"refs/heads/{name}", f"refs/tags/{name}"))

    for tpl, fmt in ((GB, "files"), (GBR, "reftable")):
        if tpl is None:
            print("  SKIP  the reftable half of the same-named branch and tag "
                  "rows: this git cannot init --ref-format=reftable (git "
                  "2.45 or later)")
            continue
        d = fresh(tpl)
        teammate(d, ["src/ok.py"])
        named_refs(d, "REBASE_HEAD")
        sh("git checkout -q feature && git rebase -q main", d, env=AGENT)
        check(f"(fixture) {fmt}: the rebase stopped on conflicts, with a "
              f"branch and a tag named REBASE_HEAD",
              os.path.isdir(os.path.join(d, ".git", "rebase-merge"))
              and has_named(d, "REBASE_HEAD")
              # (git before 2.45 has no --show-ref-format: files only.)
              and (sh([GIT, "rev-parse", "--show-ref-format"], d)[1]
                   == "reftable\n") == (fmt == "reftable"))
        write(d, "src/shared.py", "a\nresolved\nc\n")
        sh([GIT, "add", "src/shared.py"], d)
        rc, out, err = chk(d)
        src_, smsg, _ = sdk_check(d)
        check(f"{fmt}, a rebase stopped on conflicts beside a branch and a tag "
              f"named REBASE_HEAD: still judged as a stopped pick (only the "
              f"resolution), with the REBASE_HEAD text, not 'git names no "
              f"commit'; shell == SDK (RV5-SC-1)",
              rc == 2 and out == "src/shared.py\n" and REBASE_KEEP in err
              and REBASE_NONE not in err and REBASE_ANY not in err
              and "src/teammate.py" not in err
              and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
        task(d, T1, ["src/ok.py", "src/shared.py"])
        rc1, _, _ = chk(d)
        rc2, _, e2 = sh("git rebase --continue", d, env=AGENT)
        _, tm, _ = sh("git show feature:src/teammate.py", d)
        check(f"... and following it ({fmt}: list the resolution, git rebase "
              f"--continue) keeps the teammate's file (RV5-SC-1)",
              rc1 == 0 and rc2 == 0 and tm == "t\n"
              and not os.path.isdir(os.path.join(d, ".git", "rebase-merge")),
              (rc1, rc2, e2[-300:], tm))
        for kind in ("pick", "revert"):
            d = fresh(tpl)
            task(d, T1, ["src/ok.py"])
            write(d, "src/app.py", "1\n2\n3\n4\n5\n")
            sh("git add -A && git commit -qm base", d)
            if kind == "pick":
                sh("git checkout -qb feature", d)
                write(d, "src/app.py", "1\n2\n30\n4\n5\n")
                write(d, "src/billing/pay.py", "p\n")
                sh("git add -A && git commit -qm teammate && "
                   "git checkout -q main", d)
                write(d, "src/app.py", "1\n2\n300\n4\n5\n")
                sh("git commit -qam mine", d)
                seqf, other = "CHERRY_PICK_HEAD", "src/billing/pay.py"
                named_refs(d, seqf)
                sh("git cherry-pick feature", d)
            else:
                write(d, "src/app.py", "1\n2\n30\n4\n5\n")
                write(d, "src/r1.py", "r\n")
                sh("git add -A && git commit -qm teammate", d)
                write(d, "src/app.py", "1\n2\n300\n4\n5\n")
                sh("git commit -qam mine", d)
                seqf, other = "REVERT_HEAD", "src/r1.py"
                named_refs(d, seqf)
                sh("git revert --no-edit HEAD~1", d)
            write(d, "src/app.py", "1\n2\n3\n4\n5\nresolved\n")
            sh([GIT, "add", "src/app.py"], d)
            rc, out, err = chk(d)
            src_, smsg, _ = sdk_check(d)
            check(f"{fmt}, a {kind} stopped on conflicts beside a branch and a "
                  f"tag named {seqf}: still judged as a stopped {kind} (only "
                  f"src/app.py, not {other}), with its own text, not the "
                  f"plain rule; shell == SDK (RV5-SC-1)",
                  has_named(d, seqf) and rc == 2 and out == "src/app.py\n"
                  and other not in err and PICK_TXT[kind][0] in err
                  and "Do not unstage a file from it" in err
                  and "restore --staged" not in err
                  and src_ == 2 and smsg == err.rstrip("\n"),
                  (rc, out, err, smsg))
        d = fresh(tpl)
        task(d, T1, ["src/ok.py"])
        sh("git commit -qm t1", d)
        for name in ("CHERRY_PICK_HEAD", "REVERT_HEAD", "REBASE_HEAD"):
            named_refs(d, name)
        stage(d, "src/evil.py")
        rc, out, err = chk(d)
        src_, smsg, _ = sdk_check(d)
        check(f"{fmt}, no stop, with a branch and a tag named for each head: "
              f"the plain rule and its unstage remedy; shell == SDK (RV5-SC-1)",
              all(has_named(d, n) for n in ("CHERRY_PICK_HEAD", "REVERT_HEAD",
                                            "REBASE_HEAD"))
              and rc == 2 and out == "src/evil.py\n" and "This is" not in err
              and "unstage it (git restore --staged <path>)" in err
              and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
        sh([GIT, "reset", "-q"], d)

        # [WP3 fix6 RV5-SC-2] "at an edit stop git has made it already" was
        # false at an edit line whose pick conflicted: git's status says
        # "edit", and HEAD is still the commit before it, so unstaging the
        # replayed commit's file dropped it. The text now gives a check, and
        # it is true there: git rev-parse prints two names.
        d = fresh(tpl)
        teammate(d, ["src/ok.py"])
        sh("git checkout -q feature && GIT_SEQUENCE_EDITOR=\"sed -i.b "
           "'1s/^pick/edit/'\" git rebase -q -i main", d)
        _, hr, _ = sh("git rev-parse HEAD REBASE_HEAD", d)
        _, st3, _ = sh("git status", d)
        check(f"(fixture) {fmt}: a rebase stopped at an edit line whose pick "
              f"conflicted (git status says edit; rev-parse HEAD REBASE_HEAD "
              f"prints two names)",
              os.path.isdir(os.path.join(d, ".git", "rebase-merge"))
              and "   edit " in st3 and len(set(hr.split())) == 2
              and len(hr.split()) == 2, (hr, st3[:300]))
        write(d, "src/shared.py", "a\nresolved\nc\n")
        sh([GIT, "add", "src/shared.py"], d)
        stage(d, "src/extra.py")
        rc, out, err = chk(d)
        src_, smsg, _ = sdk_check(d)
        check(f"{fmt}, a rebase stopped at an edit line whose pick conflicted: "
              f"the resolution and the agent's file, with the text that says "
              f"how to tell whether the commit is made; shell == SDK "
              f"(RV5-SC-2)",
              rc == 2 and out == "src/extra.py\nsrc/shared.py\n"
              and REBASE_KEEP in err and "src/teammate.py" not in err
              and "at an edit stop" not in err
              and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
        _, st, _ = sh("git show --stat --format= REBASE_HEAD", d)
        sh("git restore --staged src/extra.py && rm src/extra.py", d)
        task(d, T1, ["src/ok.py", "src/shared.py"])
        rc1, _, _ = chk(d)
        rcs = [sh("git rebase --continue", d, env=AGENT)[0]]
        while os.path.isdir(os.path.join(d, ".git", "rebase-merge")) \
                and len(rcs) < 4:
            rcs.append(sh("git rebase --continue", d, env=AGENT)[0])
        _, tm, _ = sh("git show feature:src/teammate.py", d)
        check(f"... and following it ({fmt}: two names, so not made; unstage "
              f"only what git show --stat REBASE_HEAD does not list, list the "
              f"resolution, git rebase --continue) keeps the replayed "
              f"commit's teammate file (RV5-SC-2)",
              "src/teammate.py" in st and rc1 == 0 and rcs[-1] == 0
              and tm == "t\n"
              and not os.path.isdir(os.path.join(d, ".git", "rebase-merge")),
              (st, rc1, rcs, tm))
        d = fresh(tpl)
        teammate(d, ["src/ok.py"])
        sh("GIT_SEQUENCE_EDITOR=\"sed -i.b '1s/^pick/edit/'\" "
           "git rebase -q -i HEAD~1", d)
        _, hr, _ = sh("git rev-parse HEAD REBASE_HEAD", d)
        check(f"{fmt}, a clean edit stop: rev-parse HEAD REBASE_HEAD prints "
              f"one object name twice, so the text's check says the commit is "
              f"made (RV5-SC-2)",
              len(hr.split()) == 2 and len(set(hr.split())) == 1
              and os.path.isfile(os.path.join(d, ".git", "rebase-merge",
                                              "amend")), hr)
        sh("git rebase --abort", d)

    # [WP3 fix6 RV5-SC-1] The file is read itself, not by name lookup: with
    # a branch called CHERRY_PICK_HEAD, a file that names no object made
    # rev-parse --verify find the branch. Git reads the file (the commit
    # lands as a plain one, measured), and so does the check. And a file
    # git reads as a cherry-pick (a symbolic ref; git then takes the
    # picked commit's author and removes the file, measured) is one.
    d = fresh(GB)
    task(d, T1, ["src/ok.py"])
    sh("git commit -qm t1 && git branch CHERRY_PICK_HEAD", d)
    write(d, ".git/CHERRY_PICK_HEAD", "garbage\n")
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a CHERRY_PICK_HEAD file that names no object, beside a branch so "
          "named: the plain rule; shell == SDK (RV5-SC-1)",
          rc == 2 and out == "src/evil.py\n" and "cherry-pick" not in err
          and "not an object name" not in err and src_ == 2
          and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    d = fresh(GB)
    task(d, T1, ["src/ok.py"])
    sh("git commit -qm t1", d)
    write(d, ".git/CHERRY_PICK_HEAD", "main\n")
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a CHERRY_PICK_HEAD file that holds a branch name, not an object "
          "name: the plain rule, as git reads it (its commit lands as a plain "
          "one, measured); shell == SDK (RV5-SC-1)",
          rc == 2 and out == "src/evil.py\n" and "cherry-pick" not in err
          and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    d = fresh(GB)
    task(d, T1, ["src/ok.py"])
    write(d, "src/app.py", "1\n")
    sh("git add -A && git commit -qm t1 && git checkout -qb feature && "
       "echo p > src/pay.py && git add src/pay.py && git commit -qm tm && "
       "git checkout -q main", d)
    write(d, ".git/CHERRY_PICK_HEAD", "ref: refs/heads/feature\n")
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a CHERRY_PICK_HEAD file that is a symbolic ref to a commit: a "
          "stopped cherry-pick, as git reads it; shell == SDK (RV5-SC-1)",
          rc == 2 and out == "src/evil.py\n"
          and PICK_TXT["pick"][0] in err and src_ == 2
          and smsg == err.rstrip("\n"), (rc, out, err, smsg))
    d = fresh(GB)
    task(d, T1, ["src/ok.py"])
    sh("git commit -qm t1", d)
    write(d, ".git/CHERRY_PICK_HEAD", "1234567890" * 4 + "\n")
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a CHERRY_PICK_HEAD file that names no commit in the repository: "
          "no cherry-pick (git refuses the commit itself); shell == SDK "
          "(RV5-SC-1)",
          rc == 2 and out == "src/evil.py\n" and "cherry-pick" not in err
          and src_ == 2 and smsg == err.rstrip("\n"), (rc, out, err, smsg))

    print("\n-- git revert --no-commit (MR2-5) --")
    d = fresh(GB)
    task(d, T1, ["src/ok.py"])
    sh("git commit -qm t1 && mkdir -p src && echo t > src/t1.py && "
       "git add src/t1.py && git commit -qm A && git revert -n HEAD", d)
    check("(fixture) a clean revert --no-commit leaves REVERT_HEAD",
          os.path.isfile(os.path.join(d, ".git", "REVERT_HEAD")))
    stage(d, "src/evil.py")
    rc, out, err = chk(d)
    src_, smsg, _ = sdk_check(d)
    check("a revert run with --no-commit is named so, not only 'stopped on "
          "conflicts'; the edit made in it is the change checked; shell == "
          "SDK (MR2-5)", rc == 2 and out == "src/evil.py\n"
          and "This is a revert that stopped on conflicts or ran with "
          "--no-commit" in err and src_ == 2 and smsg == err.rstrip("\n"),
          (rc, out, err, smsg))

    print("\n-- a retrofit warn week with spec_gate_commit_mode block "
          "(MR2-6) --")
    for wk in (2, 4):
        d = fresh(RF)
        week(d, wk)
        task(d, T1, ["src/ok.py"])
        write(d, "src/shared.py", "a\nb\n")
        sh("git add -A && git commit -qm base && git checkout -qb S", d)
        write(d, "src/shared.py", "a\nside\n")
        sh("git commit -qam s && git checkout -q main", d)
        write(d, "src/shared.py", "a\nmain\n")
        sh("git commit -qam m && git merge -q S", d)
        write(d, "src/shared.py", "a\nresolved\n")
        sh([GIT, "add", "src/shared.py"], d)
        rc, out, err = chk(d, env=dict(ENV, BOOTSTRAP_SPEC_MODE="block"))
        if wk == 2:
            check("retrofit week 2, block, a merge's resolution: the commit "
                  "goes through (exit 0), so the text offers no git merge "
                  "--abort and no 'Do not unstage' (MR2-6)",
                  rc == 0 and "(retrofit warn-only week 2;" in err
                  and "This is a merge" in err
                  and "git merge --abort" not in err
                  and "Do not unstage" not in err, (rc, err[-500:]))
        else:
            check("(control) retrofit week 4, block: refused, with the abort",
                  rc == 2 and "git merge --abort, then stop and ask" in err,
                  (rc, err[-300:]))
        sh("git merge --abort", d)

    print("\n-- a project below the top, its check run by a git hook in a "
          "linked worktree (CRIT2-2) --")
    # git runs a hook in a linked worktree with GIT_DIR set; the check read
    # the project's prefix with it set, got "", and passed the package's
    # files (their paths from the top match no prefix).
    top, pj = install_below("wtpfx", BASE.format(
        extra="  spec_gate_commit_mode: block\n"), "packages/web")
    task(pj, T1, ["src/listed.py"])
    sh("git commit -qm t1", pj)
    write(top, ".git/hooks/pre-commit", "#!/bin/sh\nexec bash "
          "packages/web/.claude/githooks/dispatch pre-commit\n")
    os.chmod(os.path.join(top, ".git/hooks/pre-commit"), 0o755)
    stage(pj, "src/evil.py")
    h0 = head(top)
    rc, _, err = sh("git commit -qm bad", top, env=AGENT)
    check("(control) packages/web/: the hook-run check refuses its unlisted "
          "file in the main checkout", rc != 0 and head(top) == h0
          and "  src/evil.py\n" in err, (rc, err[-300:]))
    sh([GIT, "reset", "-q"], top)
    wt = os.path.join(TMP, "wtpfx-wt")
    sh(f"git worktree add -q -b wtb '{wt}'", top)
    stage(os.path.join(wt, "packages/web"), "src/evil.py")
    h0 = head(wt)
    rc, _, err = sh("git commit -qm bad-wt", wt, env=AGENT)
    check("packages/web/, in a linked worktree (git sets GIT_DIR): the same "
          "refusal, from the project directory (CRIT2-2)",
          rc != 0 and head(wt) == h0 and "  src/evil.py\n" in err
          and "Paths here are from the project directory, packages/web/" in err,
          (rc, err[-400:]))

    # [WP3 fix2 CRIT-1, MR-3] Every verdict above (exit 0 or 2) ended stdout
    # with the end line: the contract dispatch and the fallback rely on.
    check("every verdict of the check in this suite (exit 0 or 2) printed "
          "its end line last on stdout", not NO_END, NO_END[:5])

finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

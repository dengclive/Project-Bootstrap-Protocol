#!/usr/bin/env python3
"""Self-contained test suite. Run: python3 tests/test_installer.py"""
import hashlib
import os
import shutil
import subprocess
import sys
import warnings
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

from defaults import resolve_config            # noqa: E402
from installer import build_plan               # noqa: E402
from minyaml import load_yaml                   # noqa: E402
import templates as _tmpl                       # noqa: E402

BIN = os.path.join(ROOT, "bin", "bootstrap-install")
passed = failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")


def cfg_from(yaml_text):
    raw = load_yaml(yaml_text)
    cfg, errs = resolve_config(raw)
    return cfg, errs


SERVICE = """
project:
  name: demo
  archetype: service
"""

FULL = """
project:
  name: demo
  archetype: ai-agent
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: true
principles:
  tdd_policy: required
commands:
  test: pytest
  lint: ruff check .
  format: ruff format .
"""


def plan_digest(cfg):
    plan = build_plan(cfg)
    h = hashlib.sha256()
    for a in plan:
        h.update(a["path"].encode())
        h.update(a["body"].encode())
        h.update(str(a["mode"]).encode())
    return h.hexdigest()


# 1. YAML subset parser
y = load_yaml(SERVICE)
check("yaml: nested map", y["project"]["name"] == "demo")
y2 = load_yaml("a:\n  b: [1, 2, 3]\n  c:\n    - x\n    - {k: v}\n")
check("yaml: inline list", y2["a"]["b"] == [1, 2, 3])
check("yaml: block list of map", y2["a"]["c"][1] == {"k": "v"})

# 2. Determinism: same config => identical plan digest, twice
c1, _ = cfg_from(SERVICE)
c2, _ = cfg_from(SERVICE)
check("determinism: identical digests", plan_digest(c1) == plan_digest(c2))

# 3. Skip policy invariant
_, errs = cfg_from("""
project:
  name: x
  archetype: cli
autonomous_modes:
  queue_mode_enabled: true
""")
check("skip-policy: queue requires loop|goal", any("queue_mode" in e
                                                    for e in errs))

# 4. Conditional hooks
cf, e = cfg_from(FULL)
check("config: full validates", e == [])
hk = cf["_resolved_hooks"]
check("hook: eval-gate for ai-agent", "eval-gate" in hk)
check("hook: tdd-gate when required", "tdd-gate" in hk)
check("hook: loop-cooperation when loop/goal",
      "drift-detector-loop-cooperation" in hk)
check("hook: iteration-summary when goal",
      "iteration-summary-enforcement" in hk)
cs, _ = cfg_from(SERVICE)
check("hook: no eval-gate for service",
      "eval-gate" not in cs["_resolved_hooks"])
check("hook: no tdd-gate when encouraged",
      "tdd-gate" not in cs["_resolved_hooks"])

# 5. Principle starter set fills by archetype
check("principles: service starter filled",
      "Clear errors over silent fallbacks" in cs["principles"]["ranked"])

# 6. End-to-end: write, idempotent re-run, uninstall
tmp = tempfile.mkdtemp()
try:
    shutil.copy(os.path.join(ROOT, "bootstrap.config.yaml"),
                os.path.join(tmp, "bootstrap.config.yaml"))
    r1 = subprocess.run([sys.executable, BIN, "-C", tmp],
                        capture_output=True, text=True)
    check("e2e: first run ok", r1.returncode == 0 and "create=" in r1.stdout)
    r2 = subprocess.run([sys.executable, BIN, "-C", tmp],
                        capture_output=True, text=True)
    check("e2e: idempotent (0 writes on rerun)",
          "create=0 update=0" in r2.stdout)
    # settings.json valid
    import json
    json.load(open(os.path.join(tmp, ".claude", "settings.json")))
    check("e2e: settings.json valid", True)
    # all hooks pass bash -n
    hooks_dir = os.path.join(tmp, ".claude", "hooks")
    bad = [f for f in os.listdir(hooks_dir) if f.endswith(".sh") and
           subprocess.run(["bash", "-n", os.path.join(hooks_dir, f)]
                          ).returncode != 0]
    check("e2e: all hooks valid bash", bad == [])
    r3 = subprocess.run([sys.executable, BIN, "-C", tmp, "--uninstall"],
                        capture_output=True, text=True)
    check("e2e: uninstall ok", r3.returncode == 0 and
          not os.path.exists(os.path.join(tmp, ".claude", "steering")))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------------------
# 7. Regression tests for review findings (must stay fixed)
# ---------------------------------------------------------------------------
import json as _json


def _install(yaml_text, extra=None):
    d = tempfile.mkdtemp()
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(yaml_text)
    subprocess.run([sys.executable, BIN, "-C", d],
                   capture_output=True, text=True)
    return d


def _run_hook(path, payload, env=None):
    """Run an emitted hook against the fixture that emitted it.

    Both the project dir and the CWD are pinned to that fixture, because the
    emitted hooks resolve runtime paths two different ways and BOTH leak to the
    parent repo if left unset:

      * files, via `${CLAUDE_PROJECT_DIR:-.}` — unset, this resolved to `.`,
        the test runner's CWD, i.e. the bootstrap repo itself. Every hook run
        appended to the REPO's .claude/logs/hooks.log; that is how a 1500-line
        log accumulated in the working tree and eventually got committed.
      * git state, via the process CWD — `git` finds its repository from CWD,
        not from CLAUDE_PROJECT_DIR. No hook exercised here shells out to git
        today (only secrets-gate and dependency-gate are executed; the
        git-using spec-gate-commit / test-gate / ci-mirror appear only in
        wiring assertions), but the sibling suite had exactly this bug read
        the real repo's index, so pin it here before a future test trips it.

    Caller-supplied env still wins — the no-jq harness overrides PATH this way.
    """
    proj = os.path.dirname(os.path.dirname(os.path.dirname(path)))
    e = dict(os.environ)
    e["CLAUDE_PROJECT_DIR"] = proj
    if env:
        e.update(env)
    r = subprocess.run(["bash", path], input=_json.dumps(payload),
                        capture_output=True, text=True, env=e, cwd=proj)
    return r.returncode


SEC_CFG = """project:
  name: r
  archetype: service
deps:
  approved: ["requests", "flask"]
secrets:
  never_read_paths: [".env*", "secrets/**", "*.key"]
commands:
  test: "true"
  lint: "true"
  format: "true"
"""

d = _install(SEC_CFG)
try:
    sg = os.path.join(d, ".claude", "hooks", "secrets-gate.sh")
    dg = os.path.join(d, ".claude", "hooks", "dependency-gate.sh")
    # Force the no-jq code path via a PATH with no jq:
    nojq = tempfile.mkdtemp()
    for b in ("bash", "cat", "python3", "basename", "dirname", "date",
              "mkdir", "printf", "grep", "sed", "find", "mktemp", "rm",
              "env", "uname"):
        src = shutil.which(b)
        if src:
            os.symlink(src, os.path.join(nojq, b))
    nojq_env = {"PATH": nojq}

    # S-1: secrets gate must BLOCK even with jq absent (was a silent bypass)
    check("S-1: secrets-gate blocks .env without jq",
          _run_hook(sg, {"tool_input": {"file_path": "/x/.env"}},
                    nojq_env) == 2)
    check("S-1: secrets-gate blocks secrets/** without jq",
          _run_hook(sg, {"tool_input": {"file_path": "secrets/db.yml"}},
                    nojq_env) == 2)
    check("S-1: secrets-gate allows benign path without jq",
          _run_hook(sg, {"tool_input": {"file_path": "src/main.py"}},
                    nojq_env) == 0)
    # S-1: no eval() anywhere in generated hooks
    allsh = ""
    for f in os.listdir(os.path.join(d, ".claude", "hooks")):
        if f.endswith(".sh"):
            allsh += open(os.path.join(d, ".claude", "hooks", f)).read()
    check("S-1: no eval() in any generated hook", 'eval("d"' not in allsh
          and "eval(" not in allsh)

    # T-1: secrets-gate must not fail open on realistic dotenv NAMES that do
    # not start with the pattern (config.env), nor on uppercase extensions,
    # and must still block under the restricted no-jq/no-tr PATH (a pure-bash
    # matcher: a missing external binary must never let a secret read pass).
    check("T-1: secrets-gate blocks config.env (suffix dotenv, no-jq)",
          _run_hook(sg, {"tool_input": {"file_path": "config.env"}},
                    nojq_env) == 2)
    check("T-1: secrets-gate blocks prod.env nested (no-jq)",
          _run_hook(sg, {"tool_input":
                         {"file_path": "backend/prod.env"}}, nojq_env) == 2)
    check("T-1: secrets-gate blocks uppercase .KEY (case-insensitive)",
          _run_hook(sg, {"tool_input": {"file_path": "app.KEY"}},
                    nojq_env) == 2)
    check("T-1: secrets-gate blocks .ENV (case-insensitive, no-jq)",
          _run_hook(sg, {"tool_input": {"file_path": ".ENV"}},
                    nojq_env) == 2)
    check("T-1: secrets-gate still allows benign env-substring names",
          _run_hook(sg, {"tool_input":
                         {"file_path": "environment.md"}}, nojq_env) == 0
          and _run_hook(sg, {"tool_input":
                             {"file_path": "src/prevent.py"}},
                        nojq_env) == 0)
    check("T-1: secrets-gate blocks shell-meta path ending .env (no-jq)",
          _run_hook(sg, {"tool_input":
                         {"file_path": "$(touch /tmp/pwn).env"}},
                    nojq_env) == 2)
    check("T-1: secrets-gate did not execute injected command",
          not os.path.exists("/tmp/pwn"))

    # S-2: dependency gate token parsing
    check("S-2: --upgrade flag not treated as package",
          _run_hook(dg, {"tool_input":
                         {"command": "pip install --upgrade flask"}}) == 0)
    # [upstream P1-3] POSTURE REVERSED. Consuming the filename and allowing
    # meant every package inside reqs.txt was installed unchecked - the gate
    # was strictly decorative for the most common Python install form. A file
    # the gate cannot read is not grounds to allow.
    check("S-2: -r requirements.txt is unverifiable -> blocked (P1-3)",
          _run_hook(dg, {"tool_input":
                         {"command": "pip install -r reqs.txt"}}) == 2)
    check("S-2: unapproved second package is caught",
          _run_hook(dg, {"tool_input":
                         {"command": "pip install requests evil"}}) == 2)
    check("S-2: version specifier stripped",
          _run_hook(dg, {"tool_input":
                         {"command": "pip install requests==2.0"}}) == 0)
finally:
    shutil.rmtree(d, ignore_errors=True)

# S-5: malicious config values must not corrupt hook syntax.
#
# [round-4 D12] STRENGTHENED, and the change of verdict is the point. S-5
# asserted only that a hostile value could not break bash SYNTAX - true,
# because the heredoc is quoted - and that is why this test stayed green for
# five rounds while `PAT_EOF` as a pattern terminated the heredoc, executed
# everything after it on every hook invocation, and silently truncated the
# guarded pattern list. "The hooks still parse" was never the property worth
# having. These values are now REFUSED at resolve_config, so the assertion is
# that the install fails and says which field.
_s5 = subprocess.run(
    [sys.executable, BIN, "-C", tempfile.mkdtemp(), "-c", "/dev/stdin"],
    input="""project:
  name: r
  archetype: cli
deps:
  approved: ["good", "ok)", "a|b", "x;rm -rf"]
secrets:
  never_read_paths: [".env*", "weird) ; echo PWNED"]
commands:
  test: "pytest && echo X"
""", capture_output=True, text=True)
check("S-5: a config carrying shell metacharacters is now REFUSED",
      _s5.returncode != 0)
check("S-5: the refusal names both offending fields",
      "deps.approved" in _s5.stderr
      and "secrets.never_read_paths" in _s5.stderr)

# The original property S-5 existed for - a legal but awkward value cannot
# corrupt hook syntax - still holds, now over values the validator admits.
d = _install("""project:
  name: r
  archetype: cli
deps:
  approved: ["good", "@scope/pkg", "a.b_c", "pip[extra]"]
secrets:
  never_read_paths: [".env*", "cfg[0-9].key", "**/*.jks"]
commands:
  test: "pytest -k 'not slow' && echo X"
""")
try:
    hd = os.path.join(d, ".claude", "hooks")
    bad = [f for f in os.listdir(hd) if f.endswith(".sh") and
           subprocess.run(["bash", "-n", os.path.join(hd, f)]).returncode]
    check("S-5: awkward-but-legal config -> all hooks still valid bash",
          bad == [])
finally:
    shutil.rmtree(d, ignore_errors=True)

# F-1: state file carries Bootstrap-Protocol-v2-0-0.md-required fields
d = _install("""project:
  name: r
  archetype: ai-agent
  prd_tier: full
  cicd_opt_out: true
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: true
""")
try:
    st = _json.load(open(os.path.join(d, ".claude",
                                      ".bootstrap-state.json")))
    req = ("archetype", "prd_path", "prd_tier", "cicd_opt_out",
           "loop_mode_enabled", "goal_supervised_mode_enabled",
           "queue_mode_enabled", "loop_in_flight", "goal_in_flight",
           "queue_runs_history", "skippable_phase_decisions")
    check("F-1: state file has all required fields",
          all(k in st for k in req))
    check("F-1: state flags reflect config",
          st["queue_mode_enabled"] is True and
          st["archetype"] == "ai-agent" and st["cicd_opt_out"] is True)
    # F-2: auto.sh does not hang on stdin and cleans its sentinel
    auto = os.path.join(d, ".claude", "auto.sh")
    r = subprocess.run(["bash", auto], stdin=subprocess.DEVNULL,
                        capture_output=True, text=True, timeout=8)
    # The property is "does not hang on stdin" - the timeout= above is what
    # tests it; reaching this line at all means it terminated. rc == 0 was
    # incidental and became wrong on 2026-07-30, when the skeleton stopped
    # claiming terminal success for a run that dispatched nothing.
    #
    # [2026-07-31] The 2026-07-30 rewrite of this line was
    # `r.returncode is not None`, which cannot fail: subprocess.run always
    # sets returncode to an int on return, so the check could only ever be
    # counted as a pass. Two costs, both measured. It removed this file's
    # ONLY pin on the exit contract - a complete revert of all three wrappers
    # to `exit 0` left test_installer's 350 checks green. And at be9f31c this
    # same check was a LIVE red on a flock-less host (auto.sh exits 1 at the
    # flock guard), so the rewrite converted a real host-portability signal
    # into a permanent green. Assert the refusal code AND the refusal reason:
    # `== 1` alone is satisfied by the flock guard too, which is a different
    # refusal for a different cause and would hide the same regression.
    check("F-2: auto.sh terminates (does not hang on stdin)",
          r.returncode is not None)
    check("F-2: auto.sh refuses non-zero rather than claiming success",
          r.returncode == 1)
    check("F-2: ...and refuses because it is a skeleton, not for some "
          "other reason", "skeleton" in r.stderr.lower())
    check("F-2: auto.sh cleans .run-active sentinel",
          not os.path.exists(os.path.join(d, ".claude", "queue",
                                          ".run-active")))
finally:
    shutil.rmtree(d, ignore_errors=True)

# Y-1: tab-indented YAML is rejected, not silently mis-parsed
try:
    load_yaml("project:\n\tname: x\n")
    check("Y-1: tab indentation rejected", False)
except ValueError as ex:
    check("Y-1: tab indentation rejected", "tab" in str(ex).lower())

# --------------------------------------------------------------------------- #
# Y-2: an inline list or map NESTED in another one is parsed, never returned
# as its source text. It was: `principles: {ranked: ["A", "B"]}` gave ranked
# the STRING '["A", "B"]', which principles.md rendered one character per
# principle with rc=0, and the mcp example bootstrap.config.yaml documents
# (`servers: [{name: ..., command: ...}]`) gave a list of strings that
# crashed build_plan with AttributeError at templates.py `_tools`.
# --------------------------------------------------------------------------- #
import minyaml as _my                           # noqa: E402


def _yaml_err(text):
    """The exception load_yaml raises for `text`, or None if it parses."""
    try:
        load_yaml(text)
    except Exception as exc:                    # noqa: BLE001
        return exc
    return None


check("Y-2: an inline list inside an inline map is a list",
      load_yaml('principles: {tdd_policy: required, '
                'ranked: ["A over B", "C"]}')["principles"]["ranked"]
      == ["A over B", "C"])
check("Y-2: nesting parses to depth 3 in both directions",
      load_yaml("a: {b: [{c: [1, 2]}, [x, {d: e}]]}")
      == {"a": {"b": [{"c": [1, 2]}, ["x", {"d": "e"}]]}})
check("Y-2: a nested inline list in a block list item is a list",
      load_yaml("x:\n  - {name: a, args: [1, 2]}\n")
      == {"x": [{"name": "a", "args": [1, 2]}]})

# PIN THE THING, NOT ITS NAME: parse the example bootstrap.config.yaml itself
# documents in its `mcp:` comments, not a copy of it.
with open(os.path.join(ROOT, "bootstrap.config.yaml")) as _fh:
    _mcp_ex = {ln.split(":", 1)[0].strip(): ln.split("#", 1)[1].strip()
               for ln in _fh if ln.lstrip().startswith(("servers:",
                                                        "rejected:"))}
check("Y-2: the shipped config still documents both mcp examples",
      sorted(_mcp_ex) == ["rejected", "servers"]
      and all(v.startswith("[{") for v in _mcp_ex.values()))
_mcp_doc = ("project:\n  name: demo\n  archetype: service\nmcp:\n"
            f"  servers: {_mcp_ex.get('servers', '[]')}\n"
            f"  rejected: {_mcp_ex.get('rejected', '[]')}\n")
_mcp_raw = load_yaml(_mcp_doc)["mcp"]
check("Y-2: the documented mcp example parses to lists of maps",
      all(isinstance(v, list) and v and all(isinstance(e, dict) for e in v)
          for v in _mcp_raw.values()))
try:
    _mcp_cfg, _mcp_errs = resolve_config(load_yaml(_mcp_doc))
    _mcp_tools = {a["path"]: a["body"] for a in build_plan(_mcp_cfg)}[
        ".claude/steering/tools.md"]
except Exception as _exc:                       # noqa: BLE001
    _mcp_errs, _mcp_tools = [repr(_exc)], ""
check("Y-2: the documented mcp example installs and lists the server",
      not _mcp_errs and "- **github** - `npx -y "
      "@modelcontextprotocol/server-github`" in _mcp_tools
      and "- linear: specs are source of truth" in _mcp_tools)

_pr_cfg, _pr_errs = cfg_from('project: {name: demo, archetype: cli}\n'
                             'principles: {ranked: ["A over B", "C"]}\n')
_pr_md = {a["path"]: a["body"] for a in build_plan(_pr_cfg)}[
    ".claude/steering/principles.md"] if not _pr_errs else ""
check("Y-2: inline-map principles render as two principles, not one "
      "per character",
      "1. A over B\n2. C\n\n" in _pr_md and "\n3. " not in _pr_md)

# Refusals: a flow value that is not closed on its own line, or whose
# brackets do not match, used to be silently truncated or mis-split.
for _lbl, _doc, _line in (
        ("an unclosed inline list", "x: 1\na: [1, 2\n", 2),
        ("an unclosed inline map", "x: 1\na: {b: 1\n", 2),
        ("text after an inline list", "a: [1, 2] junk\n", 1),
        ("a mismatched bracket", "x: 1\ny: 2\na: [1, {b: 2]]\n", 3),
        ("an extra closing bracket", "a: [1], 2]\n", 1)):
    _e = _yaml_err(_doc)
    check(f"Y-2: {_lbl} is refused, not silently mis-parsed",
          isinstance(_e, ValueError))
    check(f"Y-3: {_lbl} is refused with its line ({_line})",
          getattr(_e, "line", None) == _line)

# Controls: quoted text keeps its brackets and commas; empty spellings hold.
check("Y-2 control: quoted brackets and commas stay one string",
      load_yaml('a: ["[ -f x ] && y", "x, y"]\n')
      == {"a": ["[ -f x ] && y", "x, y"]})
check("Y-2 control: empty inline list/map spellings are unchanged",
      load_yaml("a: []\nb: {}\nc: [ ]\nd:\n  - []\n  - {}\n")
      == {"a": [], "b": {}, "c": [], "d": [[], {}]})

# --------------------------------------------------------------------------- #
# Y-3: a config the parser refuses names its FILE and LINE and exits 2 from
# every CLI path that loads it.
# --------------------------------------------------------------------------- #
_ye = getattr(_my, "YAMLError", None)
check("Y-3: YAMLError exists and is a ValueError (old callers still catch)",
      isinstance(_ye, type) and issubclass(_ye, ValueError))
for _lbl, _doc, _line in (
        ("over-indented key", "project:\n  name: x\n   shell: bash\n", 3),
        ("line with no key", "project:\n  name: x\njust text\n", 3),
        ("block list of maps", "mcp:\n  servers:\n    - name: g\n"
                               "      command: c\n", 4),
        ("multi-line string", "secrets:\n  rotation_policy: >-\n"
                              "    folded\n", 2),
        ("tab indentation", "project:\n\tname: x\n", 2)):
    _e = _yaml_err(_doc)
    check(f"Y-3: {_lbl} is refused with its line ({_line})",
          getattr(_e, "line", None) == _line
          and str(_e).startswith(f"line {_line}: "))

_yd = tempfile.mkdtemp()
try:
    _bad = os.path.join(_yd, "bad.yaml")
    with open(_bad, "w") as _fh:
        _fh.write("project:\n  name: demo\n  archetype: cli\n"
                  "principles:\n  ranked: [a, b\n")
    os.mkdir(os.path.join(_yd, "adir.yaml"))
    for _flag in ([], ["--dry-run"], ["--print-config"]):
        _r = subprocess.run([sys.executable, BIN, "-C", _yd, "-c", _bad]
                            + _flag, capture_output=True, text=True)
        _lbl = _flag[0] if _flag else "install"
        check(f"Y-3: {_lbl}: unparseable config -> rc=2, file:line, "
              f"no traceback",
              _r.returncode == 2 and f"{_bad}:5:" in _r.stderr
              and "Traceback" not in _r.stderr)
        _r = subprocess.run([sys.executable, BIN, "-C", _yd, "-c",
                             os.path.join(_yd, "adir.yaml")] + _flag,
                            capture_output=True, text=True)
        check(f"Y-3: {_lbl}: unreadable config -> rc=2, no traceback",
              _r.returncode == 2 and "cannot read config" in _r.stderr
              and "Traceback" not in _r.stderr)
    check("Y-3: a refused config writes nothing",
          not os.path.exists(os.path.join(_yd, ".claude")))
finally:
    shutil.rmtree(_yd, ignore_errors=True)

# --------------------------------------------------------------------------- #
# Y-4: a section or list of the wrong SHAPE is a validation error, not a
# crash in resolve_config/build_plan and not a principle per character.
# --------------------------------------------------------------------------- #
from defaults import DEFAULTS as _DEFAULTS     # noqa: E402


def _resolve_or_crash(raw):
    try:
        cfg, errs = resolve_config(raw)
        if not errs:
            build_plan(cfg)
        return errs
    except Exception as exc:                    # noqa: BLE001
        return exc


_base = {"project": {"name": "d", "archetype": "cli"}}
for _sect in _DEFAULTS:
    for _v in (None, "x", [1]):
        _r = _resolve_or_crash({**_base, _sect: _v})
        check(f"Y-4: {_sect}: {_v!r} is a validation error, not a crash",
              isinstance(_r, list)
              and any(e.startswith(f"{_sect} must be a mapping")
                      for e in _r))
for _sect, _key, _v in (("principles", "ranked", "A over B"),
                        ("principles", "tiebreakers", "x"),
                        ("principles", "ranked", [["a", "b"]]),
                        ("mcp", "servers", ["github"]),
                        ("mcp", "rejected", "linear"),
                        ("secrets", "never_read_paths", [["a"]])):
    _r = _resolve_or_crash({**_base, _sect: {_key: _v}})
    check(f"Y-4: {_sect}.{_key}: {_v!r} is a validation error",
          isinstance(_r, list) and any(e.startswith(f"{_sect}.{_key}")
                                       for e in _r))
for _sect, _key in (("principles", "tiebreakers"), ("mcp", "servers"),
                    ("mcp", "rejected")):
    _r = _resolve_or_crash({**_base, _sect: {_key: None}})
    check(f"Y-4: {_sect}.{_key}: null means empty, not a crash", _r == [])
_r = _resolve_or_crash({"mode": "retrofit", **_base, "retrofit": "x"})
check("Y-4: retrofit: a scalar retrofit section is a validation error",
      isinstance(_r, list)
      and any(e.startswith("retrofit must be a mapping") for e in _r))
_r = _resolve_or_crash({"project": {"name": "d", "archetype": "bogus"},
                        "principles": {"ranked": "A over B"}})
check("Y-4: a list-shape error batches with the other validation errors",
      isinstance(_r, list)
      and any(e.startswith("principles.ranked") for e in _r)
      and any(e.startswith("project.archetype") for e in _r))
# Controls: the spellings that installed before still install, unchanged.
_ctl, _ctl_e = cfg_from("project:\n  name: d\n  archetype: cli\n"
                        "principles:\n  ranked:\n  tiebreakers: []\n"
                        "mcp:\n  servers:\n")
check("Y-4 control: empty `ranked:` still means the starter set",
      not _ctl_e and _ctl["principles"]["ranked"]
      and not _ctl["mcp"]["servers"])

# Y-5: an apostrophe does not swallow a comma. It was: `[Don't guess, B]`
# opened a quote at the apostrophe that never closed, so the comma was
# swallowed and two principles became one, with rc=0.
check("Y-5: an apostrophe in an inline list item does not merge items",
      load_yaml("a: [Don't guess, B, users' data]\n")
      == {"a": ["Don't guess", "B", "users' data"]})
check("Y-5: an apostrophe in an inline map value does not eat later keys",
      load_yaml("p: {name: Bob's app, archetype: cli}\n")
      == {"p": {"name": "Bob's app", "archetype": "cli"}})
check("Y-5 control: a quoted value after a space keeps its comma",
      load_yaml("c: {test: pytest -k \"a, b\", lint: pytest -k 'c, d'}\n")
      == {"c": {"test": 'pytest -k "a, b"', "lint": "pytest -k 'c, d'"}})
# [review correctness/F6] The comment stripper used the old rule, so the same
# apostrophe hid a trailing `# comment` (the shipped config writes them).
def _y5(text):
    try:
        return load_yaml(text)
    except ValueError as exc:
        return exc


check("Y-5: an apostrophe does not hide a trailing comment after a list",
      _y5("p:\n  ranked: [Don't guess, B]  # note\n")
      == {"p": {"ranked": ["Don't guess", "B"]}})
check("Y-5: an apostrophe does not pull a trailing comment into a scalar",
      _y5("project:\n  name: Don't panic  # note\n")
      == {"project": {"name": "Don't panic"}})
check("Y-5 control: a `#` inside a quoted value is still not a comment",
      _y5("c:\n  test: \"pytest -k 'x # y'\"  # note\n")
      == {"c": {"test": "pytest -k 'x # y'"}})
# [fix round 2, review fix-correctness/F2] Round 1's rule (a quote opens only
# where a value can start) regressed a quote after `=` or a letter that
# encloses `#`: `--grep="#smoke"` lost `#smoke"` and the install exited 2
# blaming an unbalanced quote. 24cd8a3 and PyYAML both keep these whole.
def _check_d(name, cond, detail):
    """check(), printing `detail` under a failing row."""
    check(name, cond)
    if not cond:
        print(f"        {detail}")


for _y5_text, _y5_want in (
        ('commands:\n  test: npm test -- --grep="#smoke"\n',
         {"commands": {"test": 'npm test -- --grep="#smoke"'}}),
        ("commands:\n  lint: ruff check --exclude='#scratch'\n",
         {"commands": {"lint": "ruff check --exclude='#scratch'"}}),
        ('commands:\n  test: pytest -k"#x"\n',
         {"commands": {"test": 'pytest -k"#x"'}}),
        ('commands:\n  test: echo x="#1"  # note\n',
         {"commands": {"test": 'echo x="#1"'}}),
        ("commands:\n  test: echo it's a#b\n",
         {"commands": {"test": "echo it's a#b"}}),
        ("project:\n  name: Don't#x\n", {"project": {"name": "Don't#x"}})):
    _check_d(f"Y-5 (24cd8a3 parse kept): "
             f"{_y5_text.splitlines()[-1].strip()}",
             _y5(_y5_text) == _y5_want, repr(_y5(_y5_text)))


# The whole class, not the six lines above: on every line where 24cd8a3's
# rule (every quote toggles) ends with its quotes closed, the comment
# stripper cuts exactly where 24cd8a3 did. It differs only on a line that
# 24cd8a3 left inside an unclosed quote, which is the apostrophe case above.
def _strip_24cd8a3(line):
    """lib/minyaml.py's _strip_comment at 24cd8a3, verbatim."""
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            q = ch
        elif ch == "#":
            return line[:i]
    return line


def _closed_24cd8a3(line):
    q = None
    for ch in line:
        if q:
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            q = ch
        elif ch == "#":
            return True
    return q is None


import itertools as _it                          # noqa: E402
from minyaml import _strip_comment as _strip_now  # noqa: E402
_y5_n, _y5_diff = 0, []
for _y5_len in range(7):
    for _y5_t in _it.product("a '\"#=", repeat=_y5_len):
        _y5_s = "".join(_y5_t)
        if _closed_24cd8a3(_y5_s):
            _y5_n += 1
            if _strip_now(_y5_s) != _strip_24cd8a3(_y5_s):
                _y5_diff.append(_y5_s)
_check_d(f"Y-5: on all {_y5_n} closed-quote lines up to 6 chars, the "
         f"comment stripper cuts where 24cd8a3 did",
         _y5_n > 1000 and not _y5_diff,
         f"{len(_y5_diff)} differ: {_y5_diff[:5]!r}")

# [fix round 3, review RV4-1] Round 1's rule for inline lists and maps (a
# quote opens only where a value can start) opened a run at the quote of
# ` 'em` that never closed, so `[Don't use 'em, B]` became one principle
# with rc=0; 24cd8a3 and PyYAML both read two. It also split a quoted comma
# glued to the text before it, which 24cd8a3 kept whole: `--exclude='a,b'`
# became `--exclude='a` plus a stray key `b'`.
for _y5_text, _y5_want in (
        ("p:\n  ranked: [Don't use 'em, B]\n",
         {"p": {"ranked": ["Don't use 'em", "B"]}}),
        ("p:\n  ranked: [Don't use 'em, B]  # note\n",
         {"p": {"ranked": ["Don't use 'em", "B"]}}),
        ("p:\n  ranked: [Don't use 'em, 'B']\n",
         {"p": {"ranked": ["Don't use 'em", "B"]}}),
        ("k: [a' ',]\n", {"k": ["a' '"]}),
        ("c:\n  - {name: lint, command: ruff --exclude='a,b'}\n",
         {"c": [{"name": "lint", "command": "ruff --exclude='a,b'"}]}),
        ('c:\n  - {name: t, command: pytest -k"a, b"}\n',
         {"c": [{"name": "t", "command": 'pytest -k"a, b"'}]}),
        ('c:\n  - {name: t, command: echo x="1,2"}\n',
         {"c": [{"name": "t", "command": 'echo x="1,2"'}]}),
        ("k: [cut -d ',', b]\n", {"k": ["cut -d ','", "b"]})):
    _check_d(f"Y-5 (24cd8a3 split kept): "
             f"{_y5_text.splitlines()[-1].strip()}",
             _y5(_y5_text) == _y5_want, repr(_y5(_y5_text)))
# The regression the changelog discloses: a single-quoted comma glued to a
# letter splits, which 24cd8a3 kept whole. Review measured keeping it whole
# and rejected that: it merged `[users', '.env']` and refused
# `[{name: users'}, '.env']`, both of which PyYAML reads. The row above is
# the workaround the changelog gives.
_check_d("Y-5: a glued single-quoted comma splits, as disclosed",
         _y5("k: [cut -d',', b]\n") == {"k": ["cut -d'", "'", "b"]},
         repr(_y5("k: [cut -d',', b]\n")))
# 24cd8a3 paired two apostrophes across a comma and merged the items. A
# single-quote pair with a letter or digit immediately outside it, before
# the first quote or after the second, no longer spans a comma.
for _y5_text, _y5_want in (
        ("p:\n  ranked: [users' data, B, it's fine]\n",
         {"p": {"ranked": ["users' data", "B", "it's fine"]}}),
        ("p:\n  ranked: [use 'em, B, it's fine]\n",
         {"p": {"ranked": ["use 'em", "B", "it's fine"]}}),
        ("k: [o'clock, it's]\n", {"k": ["o'clock", "it's"]}),
        ("k: [users', 'B']\n", {"k": ["users'", "B"]})):
    _check_d(f"Y-5: an apostrophe pair does not span a comma: "
             f"{_y5_text.splitlines()[-1].strip()}",
             _y5(_y5_text) == _y5_want, repr(_y5(_y5_text)))
# [fix round 3 review, pin-strength lens] One row per dimension of that rule,
# each turned red by a one-token slip in it: the letter test reads the
# character next to the quote, not the start of the string; a digit and a
# non-ASCII letter count; a double quote with no partner is literal too; a
# comma immediately inside either quote counts. PyYAML reads each row the
# same way, and 24cd8a3 merged each one but the last, which pins the
# partner search.
for _y5_text, _y5_want in (
        ("p:\n  ranked: [Protect users' data, Respect admins' time]\n",
         {"p": {"ranked": ["Protect users' data", "Respect admins' time"]}}),
        ("p: {first: users' data, second: admins' time}\n",
         {"p": {"first": "users' data", "second": "admins' time"}}),
        ("p:\n  ranked: [Keep '90s compat, Drop '00s hacks]\n",
         {"p": {"ranked": ["Keep '90s compat", "Drop '00s hacks"]}}),
        ("p:\n  ranked: [a 10' pole, a 20' pole]\n",
         {"p": {"ranked": ["a 10' pole", "a 20' pole"]}}),
        ("p:\n  ranked: [м'ясо, п'ять]\n",
         {"p": {"ranked": ["м'ясо", "п'ять"]}}),
        ('p:\n  ranked: [Use 12" screens, B]\n',
         {"p": {"ranked": ['Use 12" screens', "B"]}}),
        ('p: {name: 2" pipe, archetype: cli}\n',
         {"p": {"name": '2" pipe', "archetype": "cli"}}),
        ("p:\n  ranked: [Protect users', admins' time]\n",
         {"p": {"ranked": ["Protect users'", "admins' time"]}}),
        ("p:\n  ranked: [it's,'B']\n", {"p": {"ranked": ["it's", "B"]}}),
        ("k: [5'10, 6' tall]\n", {"k": ["5'10", "6' tall"]}),
        ("k: [5', 6']\n", {"k": ["5'", "6'"]}),
        ("p:\n  ranked: [it''s ok, users' data]\n",
         {"p": {"ranked": ["it''s ok", "users' data"]}})):
    _check_d(f"Y-5 (one rule dimension): "
             f"{_y5_text.splitlines()[-1].strip()}",
             _y5(_y5_text) == _y5_want, repr(_y5(_y5_text)))
# A bracket that does not match inside an item is refused, not read as text
# (WP1 g4; the same review found neither check pinned). So is a nest too
# deep for the parser's stack, inline or by indentation: RecursionError is
# not a ValueError, so it escaped as a traceback.
for _lbl, _doc, _line in (
        ("a mismatched bracket inside an item", "x: 1\nk: [a[}, b]\n", 2),
        ("an unclosed bracket inside a map value",
         "c:\n  - {name: t, command: grep a[, b: c}\n", 2),
        ("an inline list nested 600 deep",
         "x: 1\nk: " + "[" * 600 + "]" * 600 + "\n", 2),
        ("a block map nested 600 deep",
         "x: 1\n" + "".join("  " * _d + f"k{_d}:\n" for _d in range(600))
         + "  " * 600 + "z: 1\n", None)):
    _e = _yaml_err(_doc)
    _check_d(f"Y-3: {_lbl} is refused"
             + (f" with its line ({_line})" if _line else " with a line"),
             isinstance(_e, _my.YAMLError)
             and (_e.line == _line if _line else bool(_e.line)), repr(_e))


# The whole class, as for the stripper: on every string over `a1 '",=` up to
# 6 chars where 24cd8a3's quotes all close and no single-quote pair is one
# the rule above reads as apostrophes, _split_top splits exactly where
# 24cd8a3 did. That drops exactly the strings the rule acts on, so a second
# row pins the splitter's output on those by digest: a change to the rule
# moves it, as a change to an emitted file moves a golden.
def _split_24cd8a3(s, sep):
    """lib/minyaml.py's _split_top at 24cd8a3, verbatim."""
    out, depth, buf, q = [], 0, [], None
    for ch in s:
        if q:
            buf.append(ch)
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            q = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            buf.append(ch)
        elif ch == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return out


def _split_kept_24cd8a3(s):
    q, start = None, 0
    for i, ch in enumerate(s):
        if q:
            if ch == q:
                if q == "'" and "," in s[start + 1:i] \
                        and (s[start - 1:start].isalnum()
                             or s[i + 1:i + 2].isalnum()):
                    return False
                q = None
        elif ch in ("'", '"'):
            q, start = ch, i
    return q is None


import hashlib as _hl                         # noqa: E402
from minyaml import _split_top as _split_now  # noqa: E402
_y5_n, _y5_diff, _y5_rest, _y5_h = 0, [], 0, _hl.sha256()
for _y5_len in range(7):
    for _y5_t in _it.product("a1 '\",=", repeat=_y5_len):
        _y5_s = "".join(_y5_t)
        if _split_kept_24cd8a3(_y5_s):
            _y5_n += 1
            if _split_now(_y5_s, ",") != _split_24cd8a3(_y5_s, ","):
                _y5_diff.append(_y5_s)
        else:
            _y5_rest += 1
            _y5_h.update(repr((_y5_s, _split_now(_y5_s, ","))).encode())
_check_d(f"Y-5: on all {_y5_n} kept-quote strings over `a1 '\",=` up to 6 "
         f"chars, the inline-list splitter splits where 24cd8a3 did",
         _y5_n > 1000 and not _y5_diff,
         f"{len(_y5_diff)} differ: {_y5_diff[:5]!r}")
# [fix round 3 review] The splitter's output on the other strings, where the
# rule departs from 24cd8a3. Measured when this row was added; re-derive it
# only for a deliberate rule change, as for a golden.
_Y5_REST_SHA256 = (
    "fbfba69278a115e08248e14fb6ed79a4b4a40c9c1f3e584561a42e89884752f0")
_check_d(f"Y-5: on the {_y5_rest} strings the class row drops, the "
         f"inline-list splitter's output matches its pinned digest",
         _y5_rest > 1000 and _y5_h.hexdigest() == _Y5_REST_SHA256,
         f"digest {_y5_h.hexdigest()}")

# [review correctness/F3] Since D3, secrets.enabled and deps.enabled each
# switch a security gate off when false. Read by truthiness, a blank
# `enabled:` (minyaml reads {}), null or 0 switched the gate off silently,
# and a typo or a quoted "no" left it on. A value that is not true or false
# is now a config error: exit 2, file:line.
print("\n-- D3: the policy switches take true or false only --")
_ps_tmp = tempfile.mkdtemp()
try:
    _ps_cfg = os.path.join(_ps_tmp, "c.yaml")
    for _sect, _val, _shown in (("deps", "flase", "'flase'"),
                                ("deps", "", "{}"),
                                ("deps", "null", "None"),
                                ("deps", "0", "0"),
                                ("secrets", "flase", "'flase'"),
                                ("secrets", '"no"', "'no'")):
        with open(_ps_cfg, "w") as _fh:
            _fh.write(f"project:\n  name: w\n  archetype: cli\n"
                      f"{_sect}:\n  enabled: {_val}\n")
        _r = subprocess.run([sys.executable, BIN, "-c", _ps_cfg, "-C",
                             _ps_tmp, "--print-config"],
                            capture_output=True, text=True)
        check(f"D3: {_sect}.enabled: {_val or '(blank)'} -> rc=2 naming "
              f"file:line and the value",
              _r.returncode == 2
              and f"error: {_ps_cfg}:5: {_sect}.enabled must be true or "
                  f"false; got {_shown}" in _r.stderr
              and "Traceback" not in _r.stderr)
    for _val in ("true", "false"):
        with open(_ps_cfg, "w") as _fh:
            _fh.write(f"project:\n  name: w\n  archetype: cli\n"
                      f"deps:\n  enabled: {_val}\nsecrets:\n"
                      f"  enabled: {_val}\n")
        _r = subprocess.run([sys.executable, BIN, "-c", _ps_cfg, "-C",
                             _ps_tmp, "--print-config"],
                            capture_output=True, text=True)
        check(f"D3 control: enabled: {_val} on both switches -> rc=0",
              _r.returncode == 0)
finally:
    shutil.rmtree(_ps_tmp, ignore_errors=True)
# [fix round 2, review fix-correctness/F3] The fail-safe matters only for a
# FALSY non-boolean: `flase` is truthy, so a row fed only `flase` stayed
# green with the fail-safe deleted. Each row goes red if resolve_config stops
# forcing the switch back to true.
for _sect, _gate in (("deps", "dependency-gate"), ("secrets", "secrets-gate")):
    for _val in (None, 0, {}, "", "flase"):
        _ps_c, _ps_e = resolve_config(
            {"project": {"name": "w", "archetype": "cli"},
             _sect: {"enabled": _val}})
        _check_d(f"D3: resolve_config refuses {_sect}.enabled: {_val!r} "
                 f"and, for a caller that ignores errors, keeps {_gate} on",
                 any(e.startswith(f"{_sect}.enabled must be true or false")
                     for e in _ps_e)
                 and _ps_c.get(_sect, {}).get("enabled") is True
                 and _gate in _ps_c.get("_resolved_hooks", ()),
                 f"errs={_ps_e} {_sect}={_ps_c.get(_sect)} "
                 f"hooks={_ps_c.get('_resolved_hooks')}")

# C-1: user-set falsy values survive _deep_default (latent-bug guard)
cc, _ = cfg_from("""project:
  name: x
  archetype: cli
hooks:
  test_gate: false
  drift_tool_call_threshold: 0
""")
check("C-1: user false survives defaulting",
      cc["hooks"]["test_gate"] is False and
      "test-gate" not in cc["_resolved_hooks"])
check("C-1: user 0 survives defaulting",
      cc["hooks"]["drift_tool_call_threshold"] == 0)

# ---------------------------------------------------------------------------
# 8. Review round 4 - lifecycle, per-archetype matrix, autonomous wrappers
# ---------------------------------------------------------------------------

# L-1: apply -> hand-edit a generated file -> uninstall must PRESERVE the
# edit (no intervening re-apply). Pre-fix this silently deleted it because
# the manifest still held the original installer digest.
d = tempfile.mkdtemp()
try:
    shutil.copy(os.path.join(ROOT, "bootstrap.config.yaml"),
                os.path.join(d, "bootstrap.config.yaml"))
    subprocess.run([sys.executable, BIN, "-C", d],
                   capture_output=True, text=True)
    prod = os.path.join(d, ".claude", "steering", "product.md")
    with open(prod, "a") as fh:
        fh.write("\nPRECIOUS OPERATOR WORK\n")
    r = subprocess.run([sys.executable, BIN, "-C", d, "--uninstall"],
                        capture_output=True, text=True)
    keep_ok = (os.path.exists(prod) and
               "PRECIOUS OPERATOR WORK" in open(prod).read())
    check("L-1: uninstall preserves hand-edited generated file", keep_ok)
    check("L-1: uninstall summary reports kept count",
          "kept=" in r.stdout and "kept=0" not in r.stdout)
    # L-3: an UNMODIFIED generated CLAUDE.md is correctly removed, and the
    # message no longer falsely claims it was left for inspection.
    check("L-3: unmodified CLAUDE.md removed by uninstall",
          not os.path.exists(os.path.join(d, "CLAUDE.md")))
    check("L-3: uninstall message no longer claims CLAUDE.md kept",
          "CLAUDE.md and manifest left" not in r.stdout)
    # L-2: re-apply after uninstall must NOT clobber the preserved edit
    # without --force.
    r2 = subprocess.run([sys.executable, BIN, "-C", d],
                        capture_output=True, text=True)
    survived = "PRECIOUS OPERATOR WORK" in open(prod).read()
    check("L-2: re-apply after uninstall does not clobber operator edit",
          survived and "SKIP" in r2.stdout)
    # --force still overrides on re-apply
    r3 = subprocess.run([sys.executable, BIN, "-C", d, "--force"],
                        capture_output=True, text=True)
    check("L-2: --force still overrides a locally-modified file",
          "PRECIOUS OPERATOR WORK" not in open(prod).read())
finally:
    shutil.rmtree(d, ignore_errors=True)

# L-1b: clean uninstall (no edits) still removes EXACTLY the generated tree.
d = tempfile.mkdtemp()
try:
    shutil.copy(os.path.join(ROOT, "bootstrap.config.yaml"),
                os.path.join(d, "bootstrap.config.yaml"))
    subprocess.run([sys.executable, BIN, "-C", d],
                   capture_output=True, text=True)
    subprocess.run([sys.executable, BIN, "-C", d, "--uninstall"],
                   capture_output=True, text=True)
    leftovers = []
    for base, _, files in os.walk(d):
        for f in files:
            if f in ("bootstrap.config.yaml", ".installer-manifest.json",
                     ".bootstrap-state.json"):
                continue
            leftovers.append(os.path.join(base, f))
    check("L-1b: clean uninstall removes all generated content files",
          leftovers == [])
finally:
    shutil.rmtree(d, ignore_errors=True)

# W-1: loop/goal wrappers + configs are GENERATED whenever the mode is
# opted in (Phase 9.5/9.6) - independent of queue mode - and are valid bash.
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write("""project:
  name: w1
  archetype: service
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
""")
    subprocess.run([sys.executable, BIN, "-C", d],
                   capture_output=True, text=True)
    cl = os.path.join(d, ".claude")
    for fn in ("loop.sh", "loop-config.md", "goal-loop.sh",
               "goal-config.md"):
        check(f"W-1: {fn} generated on mode opt-in (no queue)",
              os.path.exists(os.path.join(cl, fn)))
    for sh in ("loop.sh", "goal-loop.sh"):
        p = os.path.join(cl, sh)
        check(f"W-1: {sh} is valid bash (-n)",
              subprocess.run(["bash", "-n", p]).returncode == 0)
        check(f"W-1: {sh} is executable",
              os.access(p, os.X_OK))
        # R-8 (IC-6) wrapper shape: worktree routing is NATIVE. The
        # skeleton instructs `claude -p --worktree` and never hand-rolls
        # `git worktree add`; the retained claim/sentinel pieces carry
        # their why-native-does-not-cover-this documentation (AC-8-3).
        body = open(p).read()
        check(f"AC-8-1: {sh} routes via native --worktree",
              "--worktree" in body)
        # The forbidden thing is an executable `git worktree add` command;
        # doc/comment lines may mention the phrase (they warn against it).
        # Inspect NON-COMMENT lines only - robust to any wording.
        code = "\n".join(ln for ln in body.splitlines()
                         if not ln.lstrip().startswith("#"))
        check(f"AC-8-1: {sh} has no hand-rolled `git worktree add`",
              "git worktree add" not in code)
        check(f"AC-8-3: {sh} documents the retained claim/sentinel case",
              "RETAINED under native worktrees" in body)
    # Fail-safe: no task-id -> usage exit 2, no hang.
    r = subprocess.run(["bash", os.path.join(cl, "loop.sh")],
                       stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=8)
    check("W-1: loop.sh exits 2 on missing task-id (no hang)",
          r.returncode == 2)
    # Fail-safe: .halt sentinel honored before any work.
    os.makedirs(os.path.join(cl, "queue"), exist_ok=True)
    open(os.path.join(cl, "queue", ".halt"), "w").close()
    r = subprocess.run(["bash", os.path.join(cl, "loop.sh"), "tX"],
                       stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=8)
    check("W-1: loop.sh refuses when .halt present",
          r.returncode == 1 and "alt" in (r.stdout + r.stderr))
    os.remove(os.path.join(cl, "queue", ".halt"))
    # Fail-safe: missing task file -> refuse (never assume eligibility).
    r = subprocess.run(["bash", os.path.join(cl, "loop.sh"), "nope"],
                       stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=8)
    check("W-1: loop.sh refuses unknown task (fail safe)",
          r.returncode == 1)
    # Eligible task: claims sentinel, refuses to dispatch agent work,
    # cleans its own sentinel on exit (does NOT run unattended).
    td = os.path.join(cl, "specs", "s1", "tasks")
    os.makedirs(td, exist_ok=True)
    open(os.path.join(td, "t1.md"), "w").write("loop_eligible: true\n")
    r = subprocess.run(["bash", os.path.join(cl, "loop.sh"), "t1"],
                       stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=8)
    check("W-1: loop.sh skeleton dispatches no agent work",
          "No agent work was dispatched" in r.stderr)
    check("W-1: loop.sh cleans its active sentinel on exit",
          not os.path.exists(os.path.join(cl, "sessions",
                                          ".loop-active-t1")))
    # Double-claim: a pre-existing active sentinel blocks a second wrapper.
    os.makedirs(os.path.join(cl, "sessions"), exist_ok=True)
    open(os.path.join(cl, "sessions", ".loop-active-t1"), "w").write("999\n")
    r = subprocess.run(["bash", os.path.join(cl, "loop.sh"), "t1"],
                       stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=8)
    check("W-1: loop.sh refuses when task already claimed",
          r.returncode == 1 and
          os.path.exists(os.path.join(cl, "sessions",
                                      ".loop-active-t1")))
finally:
    shutil.rmtree(d, ignore_errors=True)

# W-1b: queue=>loop|goal holds at the FILE level - auto.sh and the wrapper
# it dispatches both exist together.
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write("""project:
  name: w1b
  archetype: service
autonomous_modes:
  loop_mode_enabled: true
  queue_mode_enabled: true
""")
    subprocess.run([sys.executable, BIN, "-C", d],
                   capture_output=True, text=True)
    cl = os.path.join(d, ".claude")
    check("W-1b: queue mode ships auto.sh AND loop.sh together",
          os.path.exists(os.path.join(cl, "auto.sh")) and
          os.path.exists(os.path.join(cl, "loop.sh")))
finally:
    shutil.rmtree(d, ignore_errors=True)

# G-1: generated .gitignore covers .bootstrap-state.json and the
# per-iteration scratch sentinels (Bootstrap-Protocol-v2-0-0.md line 825 / state-naming).
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write("""project:
  name: g1
  archetype: service
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: true
""")
    subprocess.run([sys.executable, BIN, "-C", d],
                   capture_output=True, text=True)
    gi = open(os.path.join(d, ".claude", ".gitignore")).read()
    for pat in (".bootstrap-state.json", ".installer-manifest.json",
                "sessions/.iteration-summary-*",
                "sessions/.evaluator-feedback-*",
                "sessions/.loop-complete-*", "sessions/.loop-halt-*",
                "queue/.run-active"):
        check(f"G-1: .gitignore lists {pat}", pat in gi)
    # Operator-facing audit records stay COMMITTED (not ignored).
    check("G-1: .gitignore does NOT ignore backlog.md",
          "backlog.md" not in gi)
    # GR2-03a (v2.4.0 fold): the assumption ledger lands in .claude/steering/,
    # which the emitted .claude/.gitignore never ignores -> committed by
    # construction (steering docs are the operator-facing calibration record).
    check("GR2-03a: .gitignore does NOT ignore steering/ (ledger committed)",
          "steering" not in gi)
finally:
    shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
# GR2-03a (v2.4.0 fold): assumption-ledger.md is an UNCONDITIONAL steering
# artifact. Snapshot-based (+1 vs the v2.2.0 plan; no brittle absolute
# literal here — the absolute count is pinned by test_greenfield_golden.py).
# ---------------------------------------------------------------------------
_LEDGER_PATH = ".claude/steering/assumption-ledger.md"
for _fix_name, _fix in (("service", SERVICE), ("full", FULL)):
    _c, _ = cfg_from(_fix)
    _plan = build_plan(_c)
    _ledger_actions = [a for a in _plan if a["path"] == _LEDGER_PATH]
    check(f"GR2-03a[{_fix_name}]: assumption-ledger.md emitted exactly once",
          len(_ledger_actions) == 1)
    # NB (review fix): a "+1 vs the v2.2.0 plan" check used to live here,
    # filtering the ledger out of THIS plan and comparing lengths. That is a
    # partition of one list by complementary predicates, so the delta equals
    # the ledger-occurrence count by construction — arithmetically identical
    # to the check above and unable to fail independently of it. No pre-fold
    # plan was ever built, so the baseline delta it advertised was never
    # enforced. The absolute count IS pinned, by EXPECTED_ACTION_COUNTS in
    # test_greenfield_golden.py (56 / 68), which is where a genuine "+1"
    # regression surfaces.
    if _ledger_actions:
        _body = _ledger_actions[0]["body"]
        # Interpolated (not hardcoded) default drift thresholds 50/120/3.
        check(f"GR2-03a[{_fix_name}]: ledger interpolates drift thresholds",
              "50 tool calls / 120 min / 3 file reads" in _body)
        # Links to the v2.4.0 doc, not restating it as a second authority.
        check(f"GR2-03a[{_fix_name}]: ledger cites Bootstrap-Protocol-v2-4-0",
              "Bootstrap-Protocol-v2-4-0.md" in _body)

# Determinism: the seeded ledger body carries no timestamp/randomness, so two
# independent resolves produce byte-identical bodies (and the whole plan digest
# still matches, per the existing determinism test).
_cl1, _ = cfg_from(SERVICE)
_cl2, _ = cfg_from(SERVICE)
_b1 = [a for a in build_plan(_cl1) if a["path"] == _LEDGER_PATH][0]["body"]
_b2 = [a for a in build_plan(_cl2) if a["path"] == _LEDGER_PATH][0]["body"]
check("GR2-03a: ledger body deterministic across resolves", _b1 == _b2)

# Interpolation is real, not decorative: a customized drift threshold flows
# into the ledger body (so it never becomes a stale second authority).
_cc, _ = cfg_from("""project:
  name: custom
  archetype: service
hooks:
  drift_tool_call_threshold: 77
""")
_cbody = [a for a in build_plan(_cc)
          if a["path"] == _LEDGER_PATH][0]["body"]
check("GR2-03a: customized drift threshold flows into the ledger",
      "77 tool calls" in _cbody)

# v2.4.0 spec-doc existence (RC-03 class): the assumption-ledger / telemetry
# bodies and GR2-01/02 prose added by this fold cite Bootstrap-Protocol-v2-4-0
# — the cited docs must exist at repo root so the citations are not dangling.
for _doc in ("Bootstrap-Protocol-v2-4-0.md",
             "Bootstrap-Protocol-Companion-v2-4-0.md"):
    check(f"v2.4.0: cited spec doc exists at repo root: {_doc}",
          os.path.isfile(os.path.join(ROOT, _doc)))

# ---------------------------------------------------------------------------
# GR2-01 (v2.4.0 fold): progress.md is prose-only (no new emitted file). The
# read-first note is in CLAUDE.md; the failed-approaches do-not-retry
# instruction is in the implementer agent body but NOT the reviewer; the
# canonical progress.md template lives in exactly one emitted body
# (.claude/specs/INDEX.md).
# ---------------------------------------------------------------------------
_gc, _ = cfg_from(FULL)
_gplan = build_plan(_gc)


def _body_of(plan, path):
    for a in plan:
        if a["path"] == path:
            return a["body"]
    return None


_claude = _body_of(_gplan, "CLAUDE.md")
_index = _body_of(_gplan, ".claude/specs/INDEX.md")
_impl = _body_of(_gplan, ".claude/agents/implementer.md")
_rev = _body_of(_gplan, ".claude/agents/reviewer.md")

check("GR2-01: CLAUDE.md reading list reads progress.md first at priming",
      _claude is not None and "progress.md" in _claude
      and "first" in _claude.lower())
check("GR2-01: implementer body present in FULL plan", _impl is not None)
check("GR2-01: reviewer body present in FULL plan", _rev is not None)
check("GR2-01: implementer consults Failed approaches / do-not-retry",
      _impl is not None and "Failed approaches" in _impl
      and "do-not-retry" in _impl)
check("GR2-01: reviewer body does NOT gain the failed-approaches text "
      "(stays part of the deterministic gate)",
      _rev is not None and "do-not-retry" not in _rev
      and "Failed approaches" not in _rev)

# Canonical template home (review revision): the template lives in its OWN
# installer-owned file, not inside the operator-edited INDEX.md roster. That
# separation is what makes it deliverable on upgrade: INDEX.md is skipped by
# the hand-edit guard on every real install (Phase 7.6 step 5 directs editing
# it), so normative content parked there could never reach an existing
# workspace, and --force delivered it only by destroying the roster.
_PROGRESS_TPL = ".claude/specs/progress-template.md"
_tpl = _body_of(_gplan, _PROGRESS_TPL)
check("GR2-01: progress-template.md is emitted", _tpl is not None)
check("GR2-01: template carries the Failed-approaches header",
      _tpl is not None and "## Failed approaches" in _tpl)
check("GR2-01: template carries the do-not-retry flag wording",
      _tpl is not None and "do-not-retry: yes" in _tpl)
for _lt in ("decisions.md", "learnings/", "<timestamp>-checkpoint.md"):
    check(f"GR2-01: template links {_lt}", _tpl is not None and _lt in _tpl)
check("GR2-01: template declares itself installer-owned",
      _tpl is not None and "Installer-owned" in _tpl)
# INDEX.md keeps the roster and POINTS at the template rather than embedding
# it, so the two ownership domains stay separate.
check("GR2-01: INDEX.md points at the template file",
      _index is not None and "progress-template.md" in _index)
check("GR2-01: INDEX.md no longer embeds the template body",
      _index is not None and "# Progress — <slug>" not in _index)
check("GR2-01: INDEX.md still carries the spec roster",
      _index is not None and "| slug | status |" in _index)
# No second emitted body duplicates the full template (uniqueness of the
# home). The template's distinctive title line appears in exactly one body.
_dupe = [a["path"] for a in _gplan
         if a["body"] and "# Progress — <slug>" in a["body"]]
check("GR2-01: progress.md template embedded in exactly one emitted body "
      "(.claude/specs/progress-template.md)",
      _dupe == [_PROGRESS_TPL])
# The pointers in CLAUDE.md and the implementer body must name the file that
# actually carries the template — a stale pointer here is the dangling-
# reference class this revision exists to close.
check("GR2-01: CLAUDE.md points at the template file",
      _claude is not None and "progress-template.md" in _claude)
check("GR2-01: implementer points at the template file",
      _impl is not None and "progress-template.md" in _impl)

# ---------------------------------------------------------------------------
# X-33 (issue #33): the checkpoint/resume SKILL.md bodies carry normative
# rules, not just the one-line description. Checkpoint: the filename stamp
# comes from the CLOCK (date -u +%Y-%m-%dT%H%MZ), never model memory -
# model-supplied stamps have run ahead of true UTC on real installs, and a
# wrong stamp poisons every consumer that sorts checkpoints by name.
# Resume: "most recent" resolves by file MTIME (ls -t), never filename
# sort; an explicitly named checkpoint always wins; a supersession banner
# is followed forward. The paired commands/*.md stay thin pointers (the
# frontmatter desc is the routing key shared by both surfaces - any desc
# edit moves the command files in the golden diff too). All pinned
# substrings are single rendered lines, immune to the ~79-col body wraps.
# ---------------------------------------------------------------------------
_ckpt33 = _body_of(_gplan, ".claude/skills/checkpoint/SKILL.md")
_res33 = _body_of(_gplan, ".claude/skills/resume/SKILL.md")
check("X-33: checkpoint skill emitted", _ckpt33 is not None)
check("X-33: resume skill emitted", _res33 is not None)
check("X-33: checkpoint stamps from the clock (exact command)",
      _ckpt33 is not None and "date -u +%Y-%m-%dT%H%MZ" in _ckpt33)
check("X-33: checkpoint says WHY (stamps ran ahead of true UTC; name-sort "
      "consumers poisoned)",
      _ckpt33 is not None and "ahead of true UTC" in _ckpt33
      and "sorts" in _ckpt33)
check("X-33: resume resolves most-recent by file MTIME, with the exact "
      "ls -t pipeline",
      _res33 is not None and "by file MTIME" in _res33
      and "ls -t .claude/sessions/*-checkpoint.md | head -1" in _res33)
check("X-33: resume forbids filename sort",
      _res33 is not None and "filename sort" in _res33)
check("X-33: explicitly named checkpoint always wins",
      _res33 is not None
      and "explicitly named checkpoint always wins" in _res33)
check("X-33: resume follows a supersession banner forward",
      _res33 is not None and "supersession banner" in _res33)
# Silent-fallback tripwire: _SKILL_BODIES.get(name, desc) reverts a
# typo'd key to the one-liner - the frontmatter desc must ALSO stay
# byte-identical (routing key, shared with commands/*.md).
check("X-33: checkpoint frontmatter description unchanged",
      _ckpt33 is not None and
      "description: Write a structured session synopsis to "
      ".claude/sessions/<timestamp>-checkpoint.md." in _ckpt33)
check("X-33: resume frontmatter description unchanged",
      _res33 is not None and
      "description: Load the most recent checkpoint (or a chosen one)."
      in _res33)
_ckpt33_cmd = _body_of(_gplan, ".claude/commands/checkpoint.md")
_res33_cmd = _body_of(_gplan, ".claude/commands/resume.md")
check("X-33: commands stay thin pointers, no rule duplication",
      _ckpt33_cmd is not None
      and "Invoke the `checkpoint` skill." in _ckpt33_cmd
      and "date -u" not in _ckpt33_cmd
      and _res33_cmd is not None
      and "Invoke the `resume` skill." in _res33_cmd
      and "ls -t" not in _res33_cmd)
check("X-33: commands keep the explicit-only note",
      _ckpt33_cmd is not None and "Explicit-only" in _ckpt33_cmd
      and _res33_cmd is not None and "Explicit-only" in _res33_cmd)

# ---------------------------------------------------------------------------
# GR2-02 (v2.4.0 fold): trajectory retention is a comment-contract in the
# shared per-task wrapper skeleton (loop.sh + goal-loop.sh), no new file.
# Two non-overlapping markers (AR-01 class): the retention item via the path
# literal `.claude/logs/trajectory-`, and the loop-final summary via a
# distinct `Trajectory:` line inside the documented loop-final structure
# block.
# ---------------------------------------------------------------------------
for _rel in (".claude/loop.sh", ".claude/goal-loop.sh"):
    _w = _body_of(_gplan, _rel)
    check(f"GR2-02[{_rel}]: wrapper present in FULL plan", _w is not None)
    check(f"GR2-02[{_rel}]: retention item names trajectory log path",
          _w is not None and ".claude/logs/trajectory-" in _w)
    check(f"GR2-02[{_rel}]: retention self-check fails loud when disabled",
          _w is not None and "MUST FAIL LOUD" in _w
          and "retention disabled" in _w)
    # The loop-final structure block carries its own required Trajectory line.
    _blk_start = _w.find("[loop-final-$TASK_ID.md structure") if _w else -1
    _blk = _w[_blk_start:_blk_start + 700] if _blk_start >= 0 else ""
    check(f"GR2-02[{_rel}]: loop-final structure block documents a Trajectory "
          "line", "Trajectory:" in _blk)
    # No new file was added by GR2-02 (comment-contract only).
# goal-loop.sh keeps its judge-parity clause; loop.sh must not gain it (GR2-02
# touched the shared skeleton, not the mode-specific injected values).
_loopw = _body_of(_gplan, ".claude/loop.sh")
check("GR2-02: loop.sh did not gain the judge-parity clause",
      _loopw is not None and "judge retry-once" not in _loopw)

# ---------------------------------------------------------------------------
# TEL-01 (v2.4.0 fold): opt-in telemetry doc, flag-gated. Off by default
# (invisible); on-path adds one committed steering file whose
# OTEL_RESOURCE_ATTRIBUTES line is substituted. No wire, gate, or gitignore
# change.
# ---------------------------------------------------------------------------
from templates import PROTOCOL_VERSION as _PV            # noqa: E402
_TEL_PATH = ".claude/steering/telemetry.md"


def _otel_line(body):
    for _l in body.splitlines():
        if _l.startswith("export OTEL_RESOURCE_ATTRIBUTES="):
            return _l
    return ""


# OFF (default): no telemetry.md; determinism digest stable.
_coff, _ = cfg_from(SERVICE)
_plan_off = build_plan(_coff)
check("TEL-01[off]: no telemetry.md on the default (flag-absent) path",
      all(a["path"] != _TEL_PATH for a in _plan_off))
check("TEL-01[off]: determinism digest stable with flag absent",
      plan_digest(_coff) == plan_digest(cfg_from(SERVICE)[0]))

# ON: +1 file, committed, OTEL line substituted.
_TEL_ON = """project:
  name: telon
  archetype: ai-agent
telemetry_export_enabled: true
"""
_con, _errs_on = cfg_from(_TEL_ON)
check("TEL-01[on]: config with the flag resolves cleanly", _errs_on == [])
check("TEL-01[on]: flag survives resolution", _con.get(
    "telemetry_export_enabled") is True)
_plan_on = build_plan(_con)
_tel_actions = [a for a in _plan_on if a["path"] == _TEL_PATH]
check("TEL-01[on]: telemetry.md emitted exactly once", len(_tel_actions) == 1)
_off_same, _ = cfg_from(_TEL_ON.replace(
    "telemetry_export_enabled: true", "telemetry_export_enabled: false"))
check("TEL-01[on]: plan count +1 vs the same config flag-off",
      len(_plan_on) - len(build_plan(_off_same)) == 1)
_gi_on = _body_of(_plan_on, ".claude/.gitignore")
check("TEL-01[on]: telemetry.md committed (steering not gitignored)",
      _gi_on is not None and "telemetry" not in _gi_on)

if _tel_actions:
    _tbody = _tel_actions[0]["body"]
    _ol = _otel_line(_tbody)
    # Scope placeholder-absence to the export line ONLY (AR-01: the comment
    # two lines above it legitimately keeps the literal placeholder names).
    check("TEL-01[on]: OTEL line has no <protocol_version> literal",
          "<protocol_version>" not in _ol)
    check("TEL-01[on]: OTEL line has no <archetype> literal",
          "<archetype>" not in _ol)
    check("TEL-01[on]: OTEL line carries the substituted version",
          f"bootstrap.protocol_version={_PV}" in _ol)
    check("TEL-01[on]: OTEL line carries the substituted archetype",
          "bootstrap.archetype=ai-agent" in _ol)
    # The explanatory comment DOES still carry the literals (must not be
    # substituted) — proves the substitution was scoped, not global.
    check("TEL-01[on]: explanatory comment keeps the literal placeholders",
          "<protocol_version>" in _tbody and "<archetype>" in _tbody)
    # TAR-02 secrets posture: the pasteable auth-token vector (name WITH '=')
    # must be absent; the bare name in the warning sentence must remain.
    check("TEL-01 TAR-02: no OTEL_EXPORTER_OTLP_HEADERS= vector in the body",
          "OTEL_EXPORTER_OTLP_HEADERS=" not in _tbody)
    check("TEL-01 TAR-02: body warns via gitignored settings.local.json",
          "settings.local.json" in _tbody)
    # No wire: the body opens no socket / names no maintainer endpoint.
    check("TEL-01: body is documentation only (no phone-home)",
          "Not a phone-home" in _tbody)

# State flag + TAR-01 version pairing on a real install.
_d = _install(_TEL_ON)
try:
    _state = _json.load(open(os.path.join(_d, ".claude",
                                          ".bootstrap-state.json")))
    check("TEL-01: fresh install with flag true writes state flag true",
          _state.get("telemetry_export_enabled") is True)
    _tf = os.path.join(_d, ".claude", "steering", "telemetry.md")
    check("TEL-01: telemetry.md written to disk on opt-in", os.path.exists(_tf))
    _disk_ol = _otel_line(open(_tf).read())
    check("TEL-01 TAR-01: OTEL version == state bootstrap_protocol_version",
          f"bootstrap.protocol_version={_state['bootstrap_protocol_version']}"
          in _disk_ol)
finally:
    shutil.rmtree(_d, ignore_errors=True)

# Default install: state flag false, no telemetry.md on disk.
_d0 = _install(SERVICE)
try:
    _s0 = _json.load(open(os.path.join(_d0, ".claude",
                                       ".bootstrap-state.json")))
    check("TEL-01: default install writes state flag false",
          _s0.get("telemetry_export_enabled") is False)
    check("TEL-01: default install emits no telemetry.md",
          not os.path.exists(os.path.join(_d0, ".claude", "steering",
                                          "telemetry.md")))
finally:
    shutil.rmtree(_d0, ignore_errors=True)

# Retrofit passthrough: the flat top-level flag survives the retrofit branch
# and the overlay still emits telemetry.md; flag-off retrofit plan unchanged.
_RETRO_TEL = """mode: "retrofit"
project:
  name: r-tel
  archetype: service
telemetry_export_enabled: true
secrets:
  enabled: true
deps:
  enabled: true
  approved: []
commands:
  test: "true"
  lint: "true"
  format: "true"
retrofit:
  spec_strategy: "forward-only"
  legacy_allowlist:
    - "src/**"
    - "tests/**"
  retrofit_active: true
  r08_committed: true
"""
_rc, _rerrs = cfg_from(_RETRO_TEL)
check("TEL-01 retrofit: flag survives resolve with errs == []",
      _rerrs == [] and _rc.get("telemetry_export_enabled") is True)
check("TEL-01 retrofit: plan includes telemetry.md (overlay wraps full plan)",
      any(a["path"] == _TEL_PATH for a in build_plan(_rc)))
_rc_off, _ = cfg_from(_RETRO_TEL.replace(
    "telemetry_export_enabled: true\n", ""))
check("TEL-01 retrofit: flag-absent retrofit plan has no telemetry.md",
      all(a["path"] != _TEL_PATH for a in build_plan(_rc_off)))

# ---------------------------------------------------------------------------
# TEL-01 flag normalization (review finding: raw truthiness inverted opt-outs).
# minyaml coerces only bare true/false, so every other YAML boolean spelling
# reaches the installer as a NON-EMPTY STRING. Under raw truthiness `off`/`no`/
# quoted "false" all read as ENABLED — an explicit privacy opt-out silently
# inverted into an opt-in, with the state flag stamped true to match. The
# normalizer resolves the accepted spellings and FAILS LOUD on anything else
# rather than guessing what an unrecognized value meant.
# ---------------------------------------------------------------------------
from installer import telemetry_enabled            # noqa: E402

for _spell in ("false", "no", "off", "0", '"false"', "'no'", "FALSE", " off "):
    _cf, _ce = cfg_from(f"""project:
  name: t
  archetype: service
telemetry_export_enabled: {_spell}
""")
    check(f"TEL-01 norm: {_spell!r} resolves to disabled",
          _ce == [] and telemetry_enabled(_cf) is False)
    check(f"TEL-01 norm: {_spell!r} emits no telemetry.md",
          all(a["path"] != _TEL_PATH for a in build_plan(_cf)))

for _spell in ("true", "yes", "on", "1", '"true"', "TRUE"):
    _ct, _cte = cfg_from(f"""project:
  name: t
  archetype: service
telemetry_export_enabled: {_spell}
""")
    check(f"TEL-01 norm: {_spell!r} resolves to enabled",
          _cte == [] and telemetry_enabled(_ct) is True)
    check(f"TEL-01 norm: {_spell!r} emits telemetry.md",
          any(a["path"] == _TEL_PATH for a in build_plan(_ct)))

check("TEL-01 norm: absent key defaults to disabled",
      telemetry_enabled(cfg_from(SERVICE)[0]) is False)

# Fail loud, not silent: an unrecognized value is never guessed either way.
for _junk in ("maybe", "enabled", "2", "tru"):
    _cj, _ = cfg_from(f"""project:
  name: t
  archetype: service
telemetry_export_enabled: {_junk}
""")
    try:
        telemetry_enabled(_cj)
        check(f"TEL-01 norm: {_junk!r} rejected fail-loud", False)
    except ValueError as _e:
        check(f"TEL-01 norm: {_junk!r} rejected fail-loud",
              "telemetry_export_enabled" in str(_e))

# The state stamp routes through the same normalizer, so the emitted doc and
# the persisted flag cannot disagree on a non-canonical spelling.
_d_norm = _install("""project:
  name: tnorm
  archetype: service
telemetry_export_enabled: off
""")
try:
    _sn = _json.load(open(os.path.join(_d_norm, ".claude",
                                       ".bootstrap-state.json")))
    check("TEL-01 norm: 'off' install writes state flag false",
          _sn.get("telemetry_export_enabled") is False)
    check("TEL-01 norm: 'off' install emits no telemetry.md",
          not os.path.exists(os.path.join(_d_norm, ".claude", "steering",
                                          "telemetry.md")))
finally:
    shutil.rmtree(_d_norm, ignore_errors=True)

# ---------------------------------------------------------------------------
# Upgrade-path protection (review finding: untracked files at newly planned
# paths were silently overwritten). The manifest-unknown case is exactly the
# 2.2.0 -> 2.4.0 upgrade: GR2-03a and TEL-01 add planned paths that a
# doc-first operator may already have hand-created. Overwriting content the
# installer never authored contradicts the promise the emitted ledger header
# makes ("will not overwrite local edits without --force").
# ---------------------------------------------------------------------------
_LEDGER_REL = os.path.join(".claude", "steering", "assumption-ledger.md")
_SENTINEL = "CUSTOM ROW: our fork calibrates against a different tier\n"

_d_up = tempfile.mkdtemp()
try:
    open(os.path.join(_d_up, "bootstrap.config.yaml"), "w").write(SERVICE)
    os.makedirs(os.path.join(_d_up, ".claude", "steering"), exist_ok=True)
    open(os.path.join(_d_up, _LEDGER_REL), "w").write(_SENTINEL)
    _r_up = subprocess.run([sys.executable, BIN, "-C", _d_up],
                           capture_output=True, text=True)
    _after = open(os.path.join(_d_up, _LEDGER_REL)).read()
    check("upgrade: hand-created file at a newly planned path is preserved",
          _after == _SENTINEL)
    check("upgrade: the skip is reported, not silent",
          "SKIP" in _r_up.stdout and "assumption-ledger.md" in _r_up.stdout)
    # [round-6 F6] This tree has no manifest, so "pre-existing and not
    # installer-generated" — which this used to print — is a claim about
    # authorship the installer cannot support: the manifest is gitignored, so
    # a clone of an INSTALLED tree looks identical to this one. The reason now
    # says what is actually known. "pre-existing and not installer-generated"
    # is still used where a manifest exists and simply does not list the path.
    check("upgrade: skip reason says what is actually known",
          "no installer manifest" in _r_up.stdout)
    # Sticky across runs: a skip records the OPERATOR's digest, which must not
    # read as "we wrote that" on the next run and fall through to overwrite.
    subprocess.run([sys.executable, BIN, "-C", _d_up],
                   capture_output=True, text=True)
    check("upgrade: still preserved on a second run (skip is sticky)",
          open(os.path.join(_d_up, _LEDGER_REL)).read() == _SENTINEL)
    # --force remains the documented escape hatch.
    subprocess.run([sys.executable, BIN, "-C", _d_up, "--force"],
                   capture_output=True, text=True)
    check("upgrade: --force still overwrites deliberately",
          open(os.path.join(_d_up, _LEDGER_REL)).read() != _SENTINEL)
finally:
    shutil.rmtree(_d_up, ignore_errors=True)

# ---------------------------------------------------------------------------
# TEL-01 credential posture (review finding: the emitted telemetry.md calls
# .claude/settings.local.json "(gitignored)" and steers OTLP auth headers into
# it, but no emitted gitignore covered that file). Claude Code auto-ignores it
# only when Claude Code itself creates it, while the doc says to write it
# BEFORE first launch — so a hand-created file holding
# OTEL_EXPORTER_OTLP_HEADERS tokens was committable by `git add .claude`. The
# rule now makes the doc's claim true on both greenfield and retrofit.
# ---------------------------------------------------------------------------
for _lbl, _c_gi in (("greenfield", cfg_from(SERVICE)[0]),
                    ("retrofit", _rc)):
    _gi_body = _body_of(build_plan(_c_gi), ".claude/.gitignore")
    check(f"TEL-01 TAR-02[{_lbl}]: .gitignore covers settings.local.json",
          _gi_body is not None and
          "settings.local.json" in _gi_body.splitlines())

# The doc must not restate drift thresholds: the assumption ledger interpolates
# them from cfg["hooks"], so a hardcoded pair in a co-emitted steering doc is
# the "stale second authority" GR2-03a exists to prevent (they disagreed on any
# customized config). telemetry.md now points at the ledger instead.
_tel_custom, _ = cfg_from("""project:
  name: t
  archetype: service
telemetry_export_enabled: true
hooks:
  drift_tool_call_threshold: 77
""")
_tel_b = _body_of(build_plan(_tel_custom), _TEL_PATH)
_led_b = _body_of(build_plan(_tel_custom), ".claude/steering/assumption-ledger.md")
check("TEL-01: telemetry.md states no hardcoded drift thresholds",
      _tel_b is not None and "50/120/3" not in _tel_b)
check("TEL-01: telemetry.md defers to the ledger for threshold values",
      _tel_b is not None and "assumption-ledger.md" in _tel_b)
check("GR2-03a: the ledger still carries the customized value",
      _led_b is not None and "77 tool calls" in _led_b)
check("TEL-01: no co-emitted doc contradicts the ledger's thresholds",
      _tel_b is not None and "50 tool calls" not in _tel_b)

# The trajectory retention contract must not claim a purge nothing performs:
# the 7-day state policy covers .claude/sessions/, not .claude/logs/.
check("GR2-02: telemetry.md does not claim trajectories are 7-day-purged",
      _tel_b is not None and "7-day-purged" not in _tel_b)
_loop_b = _body_of(build_plan(cfg_from(FULL)[0]), ".claude/loop.sh")
if _loop_b is not None:
    check("GR2-02: wrapper does not assert an inherited trajectory purge",
          "purged with the\n# 7-day state-retention policy" not in _loop_b)
    check("GR2-02: wrapper binds pruning as an operator duty",
          "PRUNING IS PART OF THIS CONTRACT" in _loop_b)

# ---------------------------------------------------------------------------
# TEL-01 frozen-source equivalence (review finding: the ~77-line telemetry body
# exists twice — once as the frozen root telemetry.md, once as the template
# f-string — with the byte-verification done ONCE by hand at fold time and
# pinned by nothing. A later correction to either copy would silently strand
# the other, and no golden covers it because both fixtures leave the flag off.)
# This asserts the actual contract: byte-identical modulo the ONE substituted
# OTEL_RESOURCE_ATTRIBUTES line.
# ---------------------------------------------------------------------------
_FROZEN_TEL = os.path.join(ROOT, "telemetry.md")
check("TEL-01 freeze: the frozen source telemetry.md exists",
      os.path.exists(_FROZEN_TEL))
if os.path.exists(_FROZEN_TEL) and _tel_b is not None:
    _frozen_lines = open(_FROZEN_TEL).read().splitlines()
    _emitted_lines = _tel_b.splitlines()
    check("TEL-01 freeze: emitted body has the same line count as the source",
          len(_frozen_lines) == len(_emitted_lines))
    _differing = [i for i, (a, b) in
                  enumerate(zip(_frozen_lines, _emitted_lines)) if a != b]
    check("TEL-01 freeze: exactly one line differs from the frozen source",
          len(_differing) == 1)
    if len(_differing) == 1:
        _dl = _emitted_lines[_differing[0]]
        check("TEL-01 freeze: the one differing line IS the OTEL export line",
              _dl.startswith("export OTEL_RESOURCE_ATTRIBUTES="))
        check("TEL-01 freeze: the frozen source keeps the placeholders",
              "<protocol_version>" in _frozen_lines[_differing[0]])

# Per-archetype apply matrix: eval-gate only for ai-agent; conditional
# files present; settings.json wires every resolved hook to the right
# event+matcher with no orphans.
import json as _j4
_EXPECT = {
    "spec-gate-entry": ("UserPromptSubmit", None),
    "spec-gate-commit": ("PreToolUse", "Bash"),
    # [upstream P0-2/P2-4] Widened primary matcher; the Bash registration is
    # separate and asserted below against templates.HOOK_EXTRA_EVENTS.
    "secrets-gate": ("PreToolUse", "Read|Write|Edit|NotebookEdit|Grep|Glob"),
    "test-gate": ("PreToolUse", "Bash"),
    "format-lint-gate": ("PostToolUse", "Write|Edit"),
    "ci-mirror": ("PreToolUse", "Bash"),
    "cost-log": ("Stop", None),
    "dependency-gate": ("PreToolUse", "Bash"),
    "tdd-gate": ("PreToolUse", "Write"),
    "eval-gate": ("PreToolUse", "Bash"),
    "drift-detector": ("PostToolUse", None),
    "task-done-alarm": ("SubagentStop", None),
    "decision-required-alarm": ("Notification", None),
    "drift-detector-loop-cooperation": ("PostToolUse", None),
    "iteration-summary-enforcement": ("Stop", None),
}
for arch in ("cli", "library", "service", "fullstack", "mobile",
             "data-ml", "ai-agent", "platform", "other"):
    d = tempfile.mkdtemp()
    try:
        open(os.path.join(d, "bootstrap.config.yaml"), "w").write(
            f"project:\n  name: m\n  archetype: {arch}\n")
        subprocess.run([sys.executable, BIN, "-C", d],
                       capture_output=True, text=True)
        cl = os.path.join(d, ".claude")
        eg = os.path.exists(os.path.join(cl, "hooks", "eval-gate.sh"))
        check(f"matrix[{arch}]: eval-gate iff ai-agent",
              eg == (arch == "ai-agent"))
        for cond in ("ci-cd.md", "secrets.md", "deps.md"):
            check(f"matrix[{arch}]: steering/{cond} present",
                  os.path.exists(os.path.join(cl, "steering", cond)))
        st = _j4.load(open(os.path.join(cl, "settings.json")))
        # [upstream P0-2] A hook may now hold MORE than one registration:
        # secrets-gate guards Read|Write|Edit|NotebookEdit|Grep|Glob AND
        # Bash, because every never-read path was otherwise reachable through
        # a shell command. Collect a SET of registrations per hook and assert
        # the primary one is among them, rather than assuming exactly one.
        wired = {}
        for ev, groups in st["hooks"].items():
            for g in groups:
                for hk in g["hooks"]:
                    nm = hk["command"].split("/")[-1].replace(".sh", "")
                    wired.setdefault(nm, set()).add((ev, g.get("matcher")))
        hooks = [f[:-3] for f in os.listdir(os.path.join(cl, "hooks"))
                 if f.endswith(".sh")]
        bad = [h for h in hooks
               if h in _EXPECT and _EXPECT[h] not in wired.get(h, set())]
        # [round-2 review] This check was VACUOUS, and it guarded the P0-2
        # fix's actual production wiring. `extra` was built with a filter
        # that admitted a hook only when it ALREADY carried a registration
        # beyond the primary one, so a DROPPED extra removed the key
        # entirely and `all()` ran over `{}`. Confirmed by mutation:
        # changing templates.py's `registrations = [HOOK_EVENT_MAP[hk]] +
        # HOOK_EXTRA_EVENTS.get(hk, [])` to drop the second term deletes
        # secrets-gate's PreToolUse(Bash) entry from every emitted
        # settings.json - the shell gate is then never invoked on shell
        # commands at all, i.e. upstream P0-2 (`cat .env` unguarded)
        # restored at the harness layer - and the entire suite stayed green
        # except the three golden byte-digests.
        #
        # Assert the EXACT registration set for every hook instead, so
        # presence and absence both fail. Every other guard in the repo
        # (test_sdk_gates equality, the differential) compares table to
        # table or drives hook scripts directly, bypassing this wiring
        # layer, so this is the only place a dropped registration can be
        # caught.
        want_reg = {h: {_EXPECT[h]}
                    | {tuple(e) for e in _tmpl.HOOK_EXTRA_EVENTS.get(h, [])}
                    for h in hooks if h in _EXPECT}
        wrong = {h: {"emitted": sorted(wired.get(h, set())),
                     "declared": sorted(w)}
                 for h, w in want_reg.items() if wired.get(h, set()) != w}
        check(f"matrix[{arch}]: every hook's registration set is exactly "
              f"its primary matcher plus its declared HOOK_EXTRA_EVENTS "
              f"{wrong if wrong else ''}", wrong == {})
        missing = [h for h in hooks if h not in wired]
        orphan = [k for k in wired if k not in hooks]
        check(f"matrix[{arch}]: every hook wired correctly in settings",
              bad == [] and missing == [] and orphan == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

# W-1c: full loop+goal+queue config still produces a clean, idempotent,
# all-valid-bash tree (the round-3 "remaining limitation" surface).
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write("""project:
  name: w1c
  archetype: ai-agent
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: true
principles:
  tdd_policy: required
""")
    subprocess.run([sys.executable, BIN, "-C", d],
                   capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, BIN, "-C", d],
                        capture_output=True, text=True)
    check("W-1c: full autonomous config is idempotent",
          "create=0 update=0" in r2.stdout)
    cl = os.path.join(d, ".claude")
    scripts = [os.path.join(cl, s) for s in
               ("loop.sh", "goal-loop.sh", "auto.sh")]
    scripts += [os.path.join(cl, "hooks", f)
                for f in os.listdir(os.path.join(cl, "hooks"))
                if f.endswith(".sh")]
    bad = [s for s in scripts
           if subprocess.run(["bash", "-n", s]).returncode != 0]
    check("W-1c: every generated script is valid bash", bad == [])
finally:
    shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
# R-0 (spec bootstrap-v2): protocol version identity (AC-A0-1..3).
# [R-9/AC-9-5] Deliberately re-pinned 2.0.0 -> 2.1.0 at the Milestone-B
# release-identity bump; [R6, 2.2.0] re-pinned 2.1.0 -> 2.2.0 at the
# usage-limit bump; [v2.4.0 code fold, GR2-EX/TEL-EX step 0] re-pinned
# 2.2.0 -> 2.4.0 (single fold, no intermediate 2.3.0 code release; the
# 2.3.0 GR2 doc fold and 2.4.0 TEL-01 doc fold land together in code);
# [upstream fixes, 2.6.0] re-pinned 2.5.0 -> 2.6.0. Classified MINOR, not
# PATCH: the emitted gates change BEHAVIOR, not just bytes - test-gate and
# ci-mirror were async and therefore could not block at all, and now do; a
# parser outage now fails closed where it used to allow.
# [issues #29-#33, 2.7.1] re-pinned 2.6.1 -> 2.7.1. MINOR on BOTH counts this
# time: two config keys exist that did not (commands.execute_in_cwd,
# workflow.implementer_isolation), AND the emitted gates change behavior -
# measured against a pristine v2.6.1 install, 240/270 dependency-gate and
# 21/20 secrets-gate payloads that 2.6.1 ALLOWED now deny, five of them live
# RCEs. The protocol document keeps its v2-6-0 filename: the filename tracks
# doc folds, not code releases (2.1.0 was likewise a code MINOR served by the
# v2-0-0 document). Not a seam event by
# SEAM-CONTRACT §8.4 ("changes that touch only gate internals or dispatch
# policy do not bump seam_version"): no §7.2 tier membership, §7.4 sentinel,
# CLI flag, result/stream table, or `binds` entry moved.
# [DS-01, 2.5.0] re-pinned 2.4.0 -> 2.5.0 at the design-steering fold (Step 7
# version bump; PROTOCOL_VERSION is stamped into settings.json _generatedBy,
# state, and the manifest — see the golden re-baseline for the emitted-byte
# proof). (tests/test_ic_gate.py owns the mirror assertions.)
# ---------------------------------------------------------------------------
import installer as _installer_mod          # noqa: E402
import templates as _templates_mod          # noqa: E402

check("AC-A0-1: installer.PROTOCOL_VERSION is 2.8.0",
      _installer_mod.PROTOCOL_VERSION == "2.8.0")
check("AC-A0-1: templates.PROTOCOL_VERSION is 2.8.0",
      _templates_mod.PROTOCOL_VERSION == "2.8.0")
check("AC-A0-1: RETROFIT_PROTOCOL_VERSION untouched (1.6.2)",
      _installer_mod.RETROFIT_PROTOCOL_VERSION == "1.6.2")
# The two constants are declared independently in installer.py and
# templates.py; pin them to EACH OTHER as well as to the literal, so a
# half-applied bump fails here rather than emitting a body stamped with one
# version while state records the other.
check("AC-A0-1: installer and templates PROTOCOL_VERSION agree",
      _installer_mod.PROTOCOL_VERSION == _templates_mod.PROTOCOL_VERSION)

# Review finding: plugin/plugin.json was the ONE release-identity surface no
# test read. Forgetting it fails nothing and ships a stale manifest — which
# has happened twice: v2.0.0 shipped "1.0.0" (fixed later by review item
# PR5-04/05), and the v2.2.0 bump omitted it again (caught only in review).
# Both misses happened despite the changelog recording plugin.json as part of
# the release set, so the convention alone is not the control.
_PLUGIN_JSON = os.path.join(ROOT, "plugin", "plugin.json")
check("AC-A0-1: plugin/plugin.json exists", os.path.exists(_PLUGIN_JSON))
if os.path.exists(_PLUGIN_JSON):
    _pj = _json.load(open(_PLUGIN_JSON))
    check("AC-A0-1: plugin.json version tracks PROTOCOL_VERSION",
          _pj.get("version") == _installer_mod.PROTOCOL_VERSION)
    # The description carries the version in prose too ("v2.4.0"), which the
    # 2.2.0 bump also had to hand-edit; pin it so prose and field cannot skew.
    check("AC-A0-1: plugin.json description names the current version",
          f"v{_installer_mod.PROTOCOL_VERSION}" in _pj.get("description", ""))

# [v2.7.4] plugin.json was pinned to PROTOCOL_VERSION; the README release line
# and the PRD version header were not, and both went stale — the README at
# v2.6.0 for three releases, the PRD at 2.7.0 for three more. Each was fixed by
# hand and by memory, twice. Pin them the same way plugin.json is pinned, so the
# next bump fails here instead of shipping a tag whose own documents disagree.
_PV = _installer_mod.PROTOCOL_VERSION
_readme = open(os.path.join(ROOT, "README.md")).read()
check("AC-A0-1: README release line tracks PROTOCOL_VERSION",
      f"Current release: v{_PV}." in _readme)
check("AC-A0-1: README pin target tracks PROTOCOL_VERSION",
      f"pin the annotated git tag `v{_PV}`" in _readme)
_prd = open(os.path.join(ROOT, "Bootstrap-Protocol-v2-8-0.md")).read()
check("AC-A0-1: PRD **Version:** header tracks PROTOCOL_VERSION",
      f"**Version:** {_PV}" in _prd)
_comp = open(os.path.join(ROOT,
                          "Bootstrap-Protocol-Companion-v2-8-0.md")).read()
check("AC-A0-1: Companion version line tracks the PRD",
      f"matches Bootstrap-Protocol-v2-8-0.md {_PV}." in _comp)

d = _install(FULL)
try:
    state = _json.load(open(os.path.join(d, ".claude",
                                         ".bootstrap-state.json")))
    check("AC-A0-2: fresh install writes bootstrap_protocol_version 2.8.0",
          state.get("bootstrap_protocol_version") == "2.8.0")
    settings = _json.load(open(os.path.join(d, ".claude", "settings.json")))
    check("AC-A0-3: settings.json _generatedBy reads protocol 2.8.0",
          settings.get("_generatedBy")
          == "bootstrap-installer (protocol 2.8.0)")
    manifest = _json.load(open(os.path.join(d, ".claude",
                                            ".installer-manifest.json")))
    check("AC-A0-3: manifest records protocol_version 2.8.0",
          manifest.get("protocol_version") == "2.8.0")
finally:
    shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
# R-6 (spec bootstrap-v2): model remap on subagent frontmatter — assertion,
# not assumed diff (AC-6-1..AC-6-5). Aliases resolve platform-side (managed
# drift per the Companion guardrail); this locks the emitted assignments to
# the Model Assignment Strategy table.
# ---------------------------------------------------------------------------
from templates import TEMPLATES as _T                 # noqa: E402

cfg_full, _errs = cfg_from(FULL)
assert _errs == []
plan_full = build_plan(cfg_full)
bodies = {a["path"]: a["body"] for a in plan_full}

agents = {p: b for p, b in bodies.items()
          if p.startswith(".claude/agents/")}
check("AC-6-1: three subagents emitted", len(agents) == 3)
check("AC-6-1: every emitted subagent carries an explicit model: field",
      all("\nmodel: " in b for b in agents.values()))
check("AC-6-2: implementer model is sonnet",
      "\nmodel: sonnet\n" in agents[".claude/agents/implementer.md"])
check("AC-6-2: reviewer model is opus",
      "\nmodel: opus\n" in agents[".claude/agents/reviewer.md"])
check("AC-6-2: integrator model is explicitly inherit",
      "\nmodel: inherit\n" in agents[".claude/agents/integrator.md"])
check("AC-6-2: goal-config judge default is haiku "
      "(Phase 9.6 normative key evaluator_model)",
      "evaluator_model: haiku" in bodies[".claude/goal-config.md"])
check("AC-6-2: auto-config summary-synthesis default is haiku",
      "summary_synthesis_model: haiku" in bodies[".claude/auto-config.md"]
      and "summary_synthesis_enabled" in bodies[".claude/auto-config.md"])
check("AC-6-3: no emitted file references Fable",
      all("fable" not in b.lower() for b in bodies.values()))
# AC-6-5 (owner-reworded): effort: is ALREADY emitted and IS a documented
# subagent-frontmatter key (verified against code.claude.com/docs/en/
# sub-agents 2026-07-17: "Effort level when this subagent is active...
# low|medium|high|xhigh|max"). Assert the emitted value matches the
# Companion table (reviewer = high) and greenfield/retrofit stay consistent.
check("AC-6-5: greenfield reviewer emits effort: high",
      "\neffort: high\n" in agents[".claude/agents/reviewer.md"])
_rf_reviewer = _T["retrofit_reviewer_agent"](
    {"workflow": {"reviewer_model": "opus"}})
check("AC-6-5: retrofit reviewer consistent (model: opus + effort: high)",
      "\nmodel: opus\n" in _rf_reviewer
      and "\neffort: high\n" in _rf_reviewer)
check("AC-6-5: effort: appears only on the reviewer (table has no other "
      "effort annotation)",
      all("\neffort:" not in agents[p] for p in agents
          if p != ".claude/agents/reviewer.md"))

# ---------------------------------------------------------------------------
# DS-01 (v2.5.0): opt-in design-steering doc + optional advisory skill/command,
# flag-gated. Off by default (invisible — proven byte-identical by
# test_greenfield_golden.py). Mirrors the TEL-01 block above. The interactive
# OFFER is archetype-gated (tested in test_interview.py); the FLAG is not (an
# operator hand-setting it on any archetype still emits) — asserted here.
# ---------------------------------------------------------------------------
import io as _io                                            # noqa: E402
from installer import (design_steering_enabled,            # noqa: E402
                       design_review_skill_enabled)
_DS_DOC = ".claude/steering/design.md"
_DS_SKILL = ".claude/skills/design-review/SKILL.md"
_DS_CMD = ".claude/commands/design-review.md"
_DS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_frozen(rel):
    with _io.open(os.path.join(_DS_ROOT, rel), "r", encoding="utf-8",
                  newline="") as _fh:
        return _fh.read()


# OFF (default): no design artifacts; determinism digest stable.
_ds_off, _ = cfg_from(SERVICE)
_ds_plan_off = build_plan(_ds_off)
check("DS-01[off]: no design.md on the default (flag-absent) path",
      all(a["path"] != _DS_DOC for a in _ds_plan_off))
check("DS-01[off]: no design-review skill/command on the default path",
      all(a["path"] not in (_DS_SKILL, _DS_CMD) for a in _ds_plan_off))
check("DS-01[off]: determinism digest stable with flag absent",
      plan_digest(_ds_off) == plan_digest(cfg_from(SERVICE)[0]))

# ON (doc only): +1 file, committed; skill declined => no skill/command.
_DS_DOC_ONLY = """project:
  name: dson
  archetype: fullstack
  prd_tier: standard
design_steering_enabled: true
"""
_ds_con, _ds_errs = cfg_from(_DS_DOC_ONLY)
check("DS-01[on]: config with the flag resolves cleanly", _ds_errs == [])
check("DS-01[on]: flag survives resolution",
      _ds_con.get("design_steering_enabled") is True)
_ds_plan_on = build_plan(_ds_con)
_ds_doc_actions = [a for a in _ds_plan_on if a["path"] == _DS_DOC]
check("DS-01[on doc-only]: design.md emitted exactly once",
      len(_ds_doc_actions) == 1)
check("DS-01[on doc-only]: skill declined => no SKILL.md, no command",
      all(a["path"] not in (_DS_SKILL, _DS_CMD) for a in _ds_plan_on))
_ds_off_same, _ = cfg_from(_DS_DOC_ONLY.replace(
    "design_steering_enabled: true", "design_steering_enabled: false"))
check("DS-01[on doc-only]: plan count +1 vs the same config flag-off",
      len(_ds_plan_on) - len(build_plan(_ds_off_same)) == 1)
_ds_gi = _body_of(_ds_plan_on, ".claude/.gitignore")
check("DS-01[on]: design.md committed (steering not gitignored)",
      _ds_gi is not None and "design.md" not in _ds_gi)
if _ds_doc_actions:
    check("DS-01[on]: emitted design.md is byte-identical to the frozen body",
          _ds_doc_actions[0]["body"] == _read_frozen("docs/design.md"))
    _dbody = _ds_doc_actions[0]["body"]
    # DELTA-01 / accessibility-invariant fidelity guards (not paraphrase).
    check("DS-01[on]: design.md carries invariant 8 (accessibility floor)",
          "8. **Accessible by default**" in _dbody)
    check("DS-01[on]: design.md defers ranking to principles.md (compose-fork)",
          "principles.md" in _dbody
          and "do not treat this doc as a second" in _dbody)
    # Project-specifics is a HUMAN-REQUIRED placeholder, never guessed.
    check("DS-01[on]: design.md Project-specifics stays a bracket placeholder",
          "[e.g. Tailwind + design tokens]" in _dbody)

# ON + skill: SKILL.md + command emitted exactly once each.
_DS_FULL = """project:
  name: dsfull
  archetype: fullstack
  prd_tier: standard
design_steering_enabled: true
design_review_skill_enabled: true
"""
_dsf_con, _ = cfg_from(_DS_FULL)
_dsf_plan = build_plan(_dsf_con)
check("DS-01[on+skill]: SKILL.md emitted exactly once",
      len([a for a in _dsf_plan if a["path"] == _DS_SKILL]) == 1)
check("DS-01[on+skill]: /design-review command emitted exactly once",
      len([a for a in _dsf_plan if a["path"] == _DS_CMD]) == 1)
check("DS-01[on+skill]: plan count +3 vs the fully flag-off config",
      len(_dsf_plan) - len(build_plan(_ds_off_same)) == 3)
_dsf_skill = _body_of(_dsf_plan, _DS_SKILL)
_dsf_cmd = _body_of(_dsf_plan, _DS_CMD)
check("DS-01[on+skill]: SKILL.md byte-identical to the frozen body",
      _dsf_skill == _read_frozen("docs/SKILL.md"))
check("DS-01[on+skill]: command byte-identical to the frozen body",
      _dsf_cmd == _read_frozen("docs/design-review.md"))
check("DS-01[on+skill]: skill is advisory (flags, not a deterministic gate)",
      _dsf_skill is not None and "Advisory design pass" in _dsf_skill
      and "it flags issues" in _dsf_skill
      and "Not** a deterministic gate" in _dsf_skill)
# [DELTA-03] The PRD (Phase 7) and Companion (migration §) require the skill to
# carry an explicit honest-scope clause labelling its ceiling: a design-time
# floor / advisory flag, NOT a compliance control and no substitute for legal
# review. The original DR-2-final frozen body omitted it; guard so it cannot
# silently drop from the emitted artifact again.
check("DS-01[on+skill]: skill carries the DELTA-03 honest-scope clause",
      _dsf_skill is not None
      and "not a compliance control" in _dsf_skill
      and "no substitute for legal review" in _dsf_skill
      and "EU Digital Fairness Act" in _dsf_skill)

# Skill is a SKILL, never a hook: absent from every hook body + settings.json.
_ds_hooks = [a for a in _dsf_plan if a["kind"] == "hook"]
check("DS-01: design-review absent from every emitted hook body",
      all("design-review" not in a["body"] and "design_review" not in a["body"]
          for a in _ds_hooks))
_ds_settings = _body_of(_dsf_plan, ".claude/settings.json")
check("DS-01: design-review absent from settings.json (no PreToolUse wiring)",
      _ds_settings is not None and "design-review" not in _ds_settings
      and "design_review" not in _ds_settings)

# ARCHETYPE GATE vs FLAG: the interactive offer is archetype-gated, but the
# FLAG is not — a non-user-facing archetype (data-ml) that hand-sets the flag
# STILL emits. build_plan must do NO archetype check on the flag.
_DS_DATAML = """project:
  name: dsdml
  archetype: data-ml
  prd_tier: standard
design_steering_enabled: true
"""
_dml_con, _dml_errs = cfg_from(_DS_DATAML)
check("DS-01[gate]: data-ml + hand-set flag resolves cleanly (flag accepted)",
      _dml_errs == [])
_dml_plan = build_plan(_dml_con)
check("DS-01[gate]: data-ml + hand-set flag STILL emits design.md "
      "(offer gated, flag not)",
      any(a["path"] == _DS_DOC for a in _dml_plan))

# Skill flag WITHOUT the primary => no skill (gated on design_steering_enabled).
_ds_skill_only, _ = cfg_from("""project:
  name: dsso
  archetype: fullstack
  prd_tier: standard
design_review_skill_enabled: true
""")
check("DS-01: skill flag alone (steering off) emits neither doc nor skill",
      all(a["path"] not in (_DS_DOC, _DS_SKILL, _DS_CMD)
          for a in build_plan(_ds_skill_only)))

# Normalizer fail-loud on garbage (twin of telemetry_enabled).
try:
    design_steering_enabled({"design_steering_enabled": "maybe"})
    check("DS-01: normalizer fails loud on an unrecognized value", False)
except ValueError:
    check("DS-01: normalizer fails loud on an unrecognized value", True)
check("DS-01: normalizer accepts YAML boolean spellings (off -> False)",
      design_steering_enabled({"design_steering_enabled": "off"}) is False)
check("DS-01: normalizer defaults absent key to False (forward-compat read)",
      design_steering_enabled({}) is False
      and design_review_skill_enabled({}) is False)

# State: fresh install writes both flags true; default install writes false.
_dsd = _install(_DS_FULL)
try:
    _dss = _json.load(open(os.path.join(_dsd, ".claude",
                                        ".bootstrap-state.json")))
    check("DS-01: fresh install writes design_steering_enabled true",
          _dss.get("design_steering_enabled") is True)
    check("DS-01: fresh install writes design_review_skill_enabled true",
          _dss.get("design_review_skill_enabled") is True)
    check("DS-01: design.md written to disk on opt-in",
          os.path.exists(os.path.join(_dsd, ".claude", "steering",
                                      "design.md")))
    check("DS-01: SKILL.md + command written to disk on skill opt-in",
          os.path.exists(os.path.join(
              _dsd, ".claude", "skills", "design-review", "SKILL.md"))
          and os.path.exists(os.path.join(
              _dsd, ".claude", "commands", "design-review.md")))
finally:
    shutil.rmtree(_dsd, ignore_errors=True)

_dsd0 = _install(SERVICE)
try:
    _dss0 = _json.load(open(os.path.join(_dsd0, ".claude",
                                         ".bootstrap-state.json")))
    check("DS-01: default install writes design_steering_enabled false",
          _dss0.get("design_steering_enabled") is False)
    check("DS-01: default install writes design_review_skill_enabled false",
          _dss0.get("design_review_skill_enabled") is False)
    check("DS-01: default install emits no design.md",
          not os.path.exists(os.path.join(_dsd0, ".claude", "steering",
                                          "design.md")))
finally:
    shutil.rmtree(_dsd0, ignore_errors=True)

# DS-01 skill-flag gating on the primary (review BUG-1 + BUG-2 regression).
# The skill state field is gated on design_steering_enabled via `and`, so:
#  (a) steering OFF + skill TRUE must record skill FALSE (state cannot claim a
#      skill was installed when build_plan emitted none), and
#  (b) steering OFF + a GARBAGE skill value must NOT crash the install after
#      apply_plan has written files — the `and` short-circuits and the skill
#      normalizer is never evaluated, mirroring build_plan (which never reaches
#      it when steering is off).
_DS_SKILL_ON_STEER_OFF = """project:
  name: dssoff
  archetype: service
  prd_tier: standard
design_steering_enabled: false
design_review_skill_enabled: true
"""
_dsg = _install(_DS_SKILL_ON_STEER_OFF)
try:
    _dsgs = _json.load(open(os.path.join(_dsg, ".claude",
                                         ".bootstrap-state.json")))
    check("DS-01[gate]: steering off + skill true records skill FALSE "
          "(state matches emission)",
          _dsgs.get("design_review_skill_enabled") is False)
    check("DS-01[gate]: steering off + skill true emits no SKILL.md on disk",
          not os.path.exists(os.path.join(
              _dsg, ".claude", "skills", "design-review", "SKILL.md")))
finally:
    shutil.rmtree(_dsg, ignore_errors=True)

# Garbage skill value with steering OFF must be inert: the real installer
# must exit 0 (no crash, no partial install) and write a complete state file
# with the skill flag False. We run bin/bootstrap-install directly and assert
# on the RETURN CODE (a subprocess crash does not propagate as a Python
# exception to this parent, so we must observe the exit code, not merely infer
# a crash from a missing state file — which would false-pass if _write_state
# were ever reordered to write state before evaluating the skill normalizer).
_DS_SKILL_GARBAGE = _DS_SKILL_ON_STEER_OFF.replace(
    "design_review_skill_enabled: true", "design_review_skill_enabled: maybe")
_dsg2 = tempfile.mkdtemp()
try:
    open(os.path.join(_dsg2, "bootstrap.config.yaml"), "w").write(
        _DS_SKILL_GARBAGE)
    _dsg2_proc = subprocess.run([sys.executable, BIN, "-C", _dsg2],
                                capture_output=True, text=True)
    check("DS-01[gate]: garbage skill value with steering off exits 0 "
          "(no crash / no partial install)",
          _dsg2_proc.returncode == 0)
    _dsg2_state = os.path.join(_dsg2, ".claude", ".bootstrap-state.json")
    _dsg2_ok = (os.path.exists(_dsg2_state)
                and _json.load(open(_dsg2_state)).get(
                    "design_review_skill_enabled") is False)
    check("DS-01[gate]: garbage skill value with steering off records skill "
          "False in a complete state file", _dsg2_ok)
finally:
    shutil.rmtree(_dsg2, ignore_errors=True)

# (steering ON, skill OFF) — the default "opt into the doc, decline the skill"
# path, which is the (T,F) corner the other state tests miss. State must record
# skill False (not the primary's True) and emit design.md but no SKILL.md. This
# is the case that most directly exercises the `and`-gating: dropping the skill
# term from the _write_state field records True here (state/emission disagree).
_DS_DOC_NO_SKILL = """project:
  name: dsdns
  archetype: fullstack
  prd_tier: standard
design_steering_enabled: true
design_review_skill_enabled: false
"""
_dsn = _install(_DS_DOC_NO_SKILL)
try:
    _dsns = _json.load(open(os.path.join(_dsn, ".claude",
                                         ".bootstrap-state.json")))
    check("DS-01[gate]: steering on + skill off records steering True, "
          "skill False",
          _dsns.get("design_steering_enabled") is True
          and _dsns.get("design_review_skill_enabled") is False)
    check("DS-01[gate]: steering on + skill off emits design.md but no SKILL.md",
          os.path.exists(os.path.join(_dsn, ".claude", "steering", "design.md"))
          and not os.path.exists(os.path.join(
              _dsn, ".claude", "skills", "design-review", "SKILL.md")))
finally:
    shutil.rmtree(_dsn, ignore_errors=True)


# --------------------------------------------------------------------------- #
# v2.5.0 release-review fixes (F1/F2/F3, 2026-07-27) — regression pins.
# Freeze-exception no. 16; full record in tests/test_greenfield_golden.py.
# --------------------------------------------------------------------------- #
_rr_cfg, _ = cfg_from(FULL)
_rr_plan = build_plan(_rr_cfg)
_rr_cost = _body_of(_rr_plan, ".claude/hooks/cost-log.sh")
# F3: the jq-less Python fallback must render booleans like `jq -r` —
# lowercase — or every [ "$(jget ...)" = "true" ] guard (notably the 6.D
# stop_hook_active loop guard) fails open on installs without jq.
# [upstream P3] Refined: `true` still renders lowercase (F3's point), but
# FALSE now renders EMPTY, because jq's `.x // empty` treats false as absent.
# The two parsers must be the same function or the next boolean guard added
# diverges by substrate.
check("RR-F3: jget fallback renders true lowercase, false empty (jq parity)",
      'sys.stdout.write("true" if cur else "")' in _rr_cost)
check("RR-F3: jget fallback special-cases bool before str()",
      "isinstance(cur, bool)" in _rr_cost)
# F2/A-5: iteration-summary-enforcement is wired as an unconditional Stop
# hook; it must no-op outside a goal iteration or every ordinary session end
# on a goal-enabled install errors rc=1.
_rr_iter = _body_of(_rr_plan,
                    ".claude/hooks/iteration-summary-enforcement.sh")
check("RR-F2: iteration-summary hook gates on .goal-active-*",
      'if ! ls "$S"/.goal-active-* >/dev/null 2>&1; then' in _rr_iter)
check("RR-F2: the gate precedes the summary demand",
      0 < _rr_iter.find(".goal-active-*")
      < _rr_iter.find("iteration-summary missing"))
# The demand must BLOCK. 6.D: exit 1 is "hook error, tool proceeds", and on a
# Stop hook exit 2 means "do not stop" - so the gate spent its whole life
# exiting 1 for the one violation it exists to catch. Pinned here as well as
# behaviorally in tests/test_wrapper_behavior.py, because the ordering check
# above would happily pass over an inert gate.
check("RR-F2: the summary demand exits 2, not 1",
      "\n  exit 2\n" in _rr_iter[_rr_iter.find("iteration-summary missing"):])
# ...and the block is bounded: exit 2 on Stop means "do not stop", so a turn
# that cannot produce a summary would spin forever without this.
#
# [2026-07-31] This was `_rr_iter.find("stop_hook_active") < _rr_iter.find(
# "iteration-summary missing")` with no lower guard, and `str.find` returns
# -1 when the token is ABSENT. -1 is less than any positive index, so the
# check passed when the bound had been deleted outright -- the one condition
# it exists to detect. The sibling check two lines above kept its `0 <` guard;
# this one was written without it. Anchor the lower bound, and assert the
# bound is a USABILITY probe rather than a presence test: `have_jq || have_py`
# is satisfied by a jq that exists and does not run, which is how the bound
# was defeated on a broken-parser host (rc=2 on every Stop).
# Anchored on the EXECUTABLE guard, not the bare token. `stop_hook_active`
# also appears several times in the comment block explaining the bound, so a
# token search finds the comment and passes with the guard deleted outright -
# which is what a mutation run demonstrated, on the first repair of this very
# check. A check that is satisfied by the prose describing the control is the
# same defect class as one satisfied by -1.
_GUARD = '''if [ "$(jget '.stop_hook_active')" = "true" ]; then'''
_i_bound = _rr_iter.find(_GUARD)
check("RR-F2: the demand is bounded by stop_hook_active",
      0 < _i_bound < _rr_iter.find("iteration-summary missing"))
# Anchored on the EXECUTABLE form, not the bare token: the hook's own comment
# quotes the superseded `have_jq || have_py` while explaining why it was
# wrong, and a substring test would read that comment as the code.
check("RR-F2: the bound tests parser USABILITY, not mere presence",
      "if parser_ok; then" in _rr_iter
      and "if have_jq || have_py; then" not in _rr_iter)
# F1: emitted artifacts must not advertise tier-3 enforcement nothing
# implements (nothing emitted writes .drift-tier3-* or denies at tier 3).
_rr_audio = _body_of(_rr_plan, ".claude/hooks/audio-alerts.config")
check("RR-F1: audio config records drift_tier3_enforced=false",
      "drift_tier3_enforced=false" in _rr_audio
      and "drift_tier3_enforced=true" not in _rr_audio)
check("RR-F1: audio config carries the honest-scope header",
      "HONEST SCOPE" in _rr_audio and "BAKED" in _rr_audio)
check("RR-F1: drift-detector body admits tier-1-only scope",
      "TIER-1 TOOL-CALL COUNTER ONLY" in
      _body_of(_rr_plan, ".claude/hooks/drift-detector.sh"))

# ---------------------------------------------------------------------------
# [round-4 D12] CONFIG INJECTION IS A CLASS, not one field.
#
# Four fields reach executable shell and none was validated. Established by
# execution: a marker planted in every string field, the emitted plan searched
# for it. Each case below is the reproduction, and each control is a value an
# ordinary project really uses - the point of the control set is that closing
# the class must not cost anyone a legitimate config.
# ---------------------------------------------------------------------------
_D12_BASE = {"project": {"name": "d12", "archetype": "ai-agent"}}


def _d12(overlay):
    raw = {"project": dict(_D12_BASE["project"])}
    for k, v in overlay.items():
        raw.setdefault(k, {}).update(v) if isinstance(v, dict) else None
        if not isinstance(v, dict):
            raw[k] = v
    _c, _e = resolve_config(raw)
    return _c, _e


# sink 1: secrets.never_read_paths -> mapfile -t PATS <<'PAT_EOF'
_c, _e = _d12({"secrets": {"never_read_paths":
                           [".env*", "PAT_EOF", "$(id -un > /tmp/PWNED)",
                            "secrets/**", "*.pem", "*.key"]}})
check("D12-1: never_read_paths carrying the heredoc sentinel is refused",
      any("PAT_EOF" in e for e in _e))
_c, _e = _d12({"secrets": {"never_read_paths": [".env*", "`id`"]}})
check("D12-1: never_read_paths carrying a backtick is refused", bool(_e))
_c, _e = _d12({"secrets": {"never_read_paths": [".env*", "a\nb"]}})
check("D12-1: never_read_paths carrying a newline is refused", bool(_e))

# sink 2: deps.approved -> mapfile -t APPROVED <<'APPROVED_EOF'. Worse than
# sink 1: the mapfile sits ABOVE every early exit, so a poisoned entry bricks
# dependency-gate to rc=2 on EVERY PreToolUse call, not just on installs.
_c, _e = _d12({"deps": {"approved": ["requests", "APPROVED_EOF", "$(id)"]}})
check("D12-2: deps.approved carrying the heredoc sentinel is refused",
      any("APPROVED_EOF" in e for e in _e))
_c, _e = _d12({"deps": {"approved": ["requests; rm -rf /"]}})
check("D12-2: deps.approved carrying a shell separator is refused", bool(_e))
# minyaml has no nested flow mappings, so `deps: {approved: [...]}` parses to
# the STRING '["..."]' and "\n".join() then emitted one CHARACTER per line.
# Unlisted in the brief; found while reproducing D12 and caught by the type
# check rather than by a rule written for it.
_c, _e = _d12({"deps": {"approved": '["requests"]'}})
check("D12-2: deps.approved as a string (flow-style YAML) is refused",
      bool(_e))

# sink 3: hooks.drift_* -> [ "$n" -ge <raw, unquoted> ], on every PostToolUse.
# The P0-1 arithmetic-injection RCE re-entering through config.
_c, _e = _d12({"hooks": {"drift_tool_call_threshold": "$(touch /tmp/PWNED)"}})
check("D12-3: a non-numeric drift threshold is refused", bool(_e))
_c, _e = _d12({"hooks": {"drift_tool_call_threshold": True}})
check("D12-3: a bool drift threshold is refused (int subclass in Python)",
      bool(_e))
_c, _e = _d12({"hooks": {"drift_session_duration_minutes": "5; id"}})
check("D12-3: every drift threshold is checked, not just the tool-call one",
      bool(_e))

# sink 4: commands.* are MEANT to be shell. The defect is that an unbalanced
# quote emits a hook bash cannot parse, so every commit is refused with a
# syntax error and no diagnosis.
_c, _e = _d12({"commands": {"test": "echo 'oops"}})
check("D12-4: commands.test with an unbalanced quote is refused", bool(_e))
_c, _e = _d12({"commands": {"lint": 'ruff check "'}})
check("D12-4: commands.lint with an unbalanced quote is refused", bool(_e))
_c, _e = _d12({"commands": {"ci_local": "make ci \\"}})
check("D12-4: commands.ci_local with a trailing backslash is refused",
      bool(_e))
_c, _e = _d12({"commands": {"test": "echo a\necho b"}})
check("D12-4: commands.test with a newline is refused", bool(_e))

# Controls: closing the class must cost nothing real.
for _lbl, _ov in (
        ("default config", {}),
        ("scoped + dotted + dashed package names",
         {"deps": {"approved": ["@scope/pkg", "req-uests", "a.b_c",
                                "github.com/x/y", "pip[extra]"]}}),
        ("glob patterns incl. a character class",
         {"secrets": {"never_read_paths": [".env*", "secrets/**", "*.pem",
                                           "cfg[0-9].key", "**/*.jks"]}}),
        # Both NEGATED-class spellings. `_norm_pat` on the SDK side converts
        # `[^` INTO `[!` because fnmatch reads `[^` as a POSITIVE class
        # containing `^` - so the fnmatch-native form is a pattern this suite
        # already supports, and the first cut of the D12 validator rejected
        # it. `!` is also a legal filename character.
        ("negated classes and a bang in a filename",
         {"secrets": {"never_read_paths": ["[^.]env", "[!.]env",
                                           "client!.key"]}}),
        ("quoted and nested-quoted test commands",
         {"commands": {"test": "pytest -k 'not slow'",
                       "lint": 'ruff check . && echo "ok"',
                       "ci_local": "make ci"}}),
        ("legitimate thresholds", {"hooks": {"drift_tool_call_threshold": 200,
                                             "drift_file_read_threshold": 1}}),
):
    _c, _e = _d12(_ov)
    check(f"D12 control: {_lbl} still validates", not _e)

# The emitted hooks must PARSE for every value the validator lets through.
# The pre-existing `bash -n` check runs on the default config only, which is
# exactly why sink 4 survived: the hostile value never reached an emitted
# hook in any test.
_c, _e = _d12({"commands": {"test": "pytest -k 'not slow'",
                            "lint": 'ruff check . && echo "ok"',
                            "ci_local": "make ci"},
               "deps": {"approved": ["@scope/pkg", "a.b_c"]},
               "secrets": {"never_read_paths": [".env*", "cfg[0-9].key"]},
               "principles": {"tdd_policy": "required"}})
assert not _e, _e
_d12_tmp = tempfile.mkdtemp()
try:
    _bad = []
    for _a in build_plan(_c):
        _p = _a["path"] if isinstance(_a, dict) else _a.path
        _b = _a["body"] if isinstance(_a, dict) else _a.body
        if not _p.endswith(".sh") or not isinstance(_b, str):
            continue
        _f = os.path.join(_d12_tmp, os.path.basename(_p))
        with open(_f, "w") as _fh:
            _fh.write(_b)
        if subprocess.run(["bash", "-n", _f],
                          capture_output=True).returncode != 0:
            _bad.append(_p)
    check("D12: every emitted hook parses (bash -n) on a quote-heavy config",
          _bad == [], )
finally:
    shutil.rmtree(_d12_tmp, ignore_errors=True)

# ---------------------------------------------------------------------------
# [round-4 D18] CONFIG-SHAPED VACUITY. Ordinary never_read_paths spellings
# turned secrets-gate OFF, installing rc=0 with no warning. No technique the
# round-4 brief endorses can see this: both substrates agree, it reproduces at
# every commit, and a composition sweep varies COMMAND shape while this varies
# CONFIG shape. Normalized rather than rejected - `**/secrets/**` is not a
# wrong thing to write.
# ---------------------------------------------------------------------------
for _lbl, _given, _want in (
        ("**/ prefix also guards the root", ["**/secrets/**", "**/.env*"],
         ["secrets/**", ".env*"]),
        ("./ prefix is stripped", ["./secrets/**", "./.env*"],
         ["secrets/**", ".env*"]),
        ("a trailing slash names the subtree", ["secrets/"], ["secrets/**"]),
        ("a bare directory name names the subtree", ["secrets"],
         ["secrets/**"]),
):
    _c, _e = _d12({"secrets": {"never_read_paths": list(_given)}})
    _got = _c["secrets"]["never_read_paths"]
    check(f"D18: {_lbl}",
          not _e and all(w in _got for w in _want)
          and all(g in _got for g in _given))
    check(f"D18: {_lbl} is reported, not silent",
          any("never_read_paths" in n for n in _c.get("_config_notices", [])))

# The DEFAULT list must pass through byte-identical, or every golden digest
# and every prior invariant moves for a defect none of them has.
_c, _e = _d12({})
check("D18: the default never_read_paths list is unchanged",
      _c["secrets"]["never_read_paths"]
      == [".env*", "secrets/**", "*.pem", "*.key"]
      and _c.get("_config_notices") == [])

# --------------------------------------------------------------------------- #
# [WP1 D3] deps.enabled is the dependency gate's master switch, the way
# secrets.enabled is the secrets gate's. The secrets row is the reference
# arm: it is green before D3, so a red below is D3's and not the harness's.
# --------------------------------------------------------------------------- #
print("\n-- D3: deps.enabled false removes the dependency gate --")
_D3 = "project:\n  name: x\n  archetype: cli\n"
_c_ref, _ = cfg_from(_D3 + "secrets:\n  enabled: false\n"
                     "hooks:\n  secrets_gate: true\n")
check("D3 reference: secrets.enabled false beats hooks.secrets_gate true",
      "secrets-gate" not in _c_ref["_resolved_hooks"])
_c_on, _ = cfg_from(_D3)
check("D3: the default config keeps dependency-gate",
      "dependency-gate" in _c_on["_resolved_hooks"])
_c_off, _e_off = cfg_from(_D3 + "deps:\n  enabled: false\n")
check("D3: deps.enabled false drops dependency-gate",
      not _e_off and "dependency-gate" not in _c_off["_resolved_hooks"])
_c_tru, _ = cfg_from(_D3 + "deps:\n  enabled: false\n"
                     "hooks:\n  dependency_gate: true\n")
check("D3: hooks.dependency_gate true does not re-arm it",
      "dependency-gate" not in _c_tru["_resolved_hooks"])
_p_off = {a["path"]: a["body"] for a in build_plan(_c_off)}
check("D3: the plan emits neither dependency-gate.sh nor deps.md",
      ".claude/hooks/dependency-gate.sh" not in _p_off
      and ".claude/steering/deps.md" not in _p_off)
check("D3: settings.json does not wire dependency-gate",
      "dependency-gate" not in _p_off[".claude/settings.json"])
_gates_line = [ln for ln in _tmpl.TEMPLATES["sdk_gates"](_c_off).splitlines()
               if ln.startswith("GATES = ")]
check("D3: gates.py GATES does not carry dependency-gate",
      len(_gates_line) == 1 and '"dependency-gate"' not in _gates_line[0])

# --------------------------------------------------------------------------- #
# [I-10] The installer prints _command_warnings. resolve_config computed them
# and nothing printed them; bootstrap-apply.md told the AI to surface them
# from --dry-run output that never carried them.
# --------------------------------------------------------------------------- #
print("\n-- I-10: the installer prints _command_warnings --")
_w_tmp = tempfile.mkdtemp()
try:
    _w_cfg = os.path.join(_w_tmp, "c.yaml")

    def _w_run(text):
        with open(_w_cfg, "w") as _fh:
            _fh.write(text)
        return subprocess.run([sys.executable, BIN, "-c", _w_cfg, "-C",
                               _w_tmp, "--dry-run"],
                              capture_output=True, text=True)
    _r = _w_run("project:\n  name: w\n  archetype: cli\n")
    check("I-10: --dry-run with empty commands still exits 0",
          _r.returncode == 0)
    for _n in ("test", "lint", "format"):
        check(f"I-10: --dry-run warns that commands.{_n} is empty",
              f"warning: commands.{_n} is empty" in _r.stderr)
    # I-6(a) is deferred to WP2: format-lint-gate is byte-identical and an
    # empty lint runs `true` in silence, so no line may promise a TODO.
    check("I-10: the lint warning says the gate checks nothing, and no line "
          "claims format-lint-gate prints a TODO",
          "warning: commands.lint is empty: format-lint-gate checks nothing"
          in _r.stderr and "TODO after" not in _r.stderr
          and "prints a TODO" not in _r.stderr)
    _r = _w_run('project:\n  name: w\n  archetype: cli\ncommands:\n'
                '  test: "true"\n  lint: "true"\n  format: "true"\n')
    check("I-10: no command warning when every command is set",
          "warning: commands." not in _r.stderr)
    _r = _w_run("project:\n  name: w\n  archetype: cli\n"
                "hooks:\n  test_gate: false\n")
    check("I-10: the warning does not claim a hook the config turned off",
          "warning: commands.test is empty" in _r.stderr
          and "test-gate blocks" not in _r.stderr)
finally:
    shutil.rmtree(_w_tmp, ignore_errors=True)

# --------------------------------------------------------------------------- #
# [I-6] tech.md says which hook runs which command. It claimed every TODO
# cell made "the corresponding gate" fail loudly; only Test had such a gate.
# --------------------------------------------------------------------------- #
print("\n-- I-6: tech.md states what the hooks do with each command --")
_c_emp, _ = cfg_from("project:\n  name: t\n  archetype: cli\n")
_tech_emp = _tmpl.TEMPLATES["tech"](_c_emp)
check("I-6: tech.md no longer claims every TODO cell fails loudly",
      "fail loudly" not in _tech_emp)
check("I-6: tech.md says no hook runs Format or Typecheck",
      "No hook runs Format or Typecheck." in _tech_emp)
check("I-6: tech.md says an empty Lint checks nothing (the hook runs `true`)",
      "`format-lint-gate` runs Lint after every edit and never blocks. "
      "While its cell says TODO it checks nothing and prints nothing."
      in _tech_emp and "TODO notice" not in _tech_emp)
_c_tg, _ = cfg_from("project:\n  name: t\n  archetype: cli\n"
                    "hooks:\n  test_gate: false\n")
check("I-6: tech.md does not describe a test-gate the config turned off",
      "`test-gate`" not in _tmpl.TEMPLATES["tech"](_c_tg))
# [review rulings/F5] tech.md is where an adopter reads per-hook behaviour, so
# it states the exit-5 allowance whenever test-gate carries the exit-5 arm
# (the same NO_TESTS_RC5_RE predicate), and only then.
_RC5_LINE = "A run that collects no tests (exit 5) is allowed, with a notice."
_c_py, _ = cfg_from('project:\n  name: t\n  archetype: cli\n'
                    'commands:\n  test: "pytest -q"\n')
check("I-6: tech.md states the exit-5 allowance for a pytest test command",
      _RC5_LINE in _tmpl.TEMPLATES["tech"](_c_py))
_c_js, _ = cfg_from('project:\n  name: t\n  archetype: cli\n'
                    'commands:\n  test: "npx jest"\n')
check("I-6: tech.md states no exit-5 allowance for jest (control)",
      _RC5_LINE not in _tmpl.TEMPLATES["tech"](_c_js)
      and "no tests" not in _tmpl.TEMPLATES["tech"](_c_emp))

# ---------------------------------------------------------------------------
# WP1 (rest): the rename-to-disable warning, MCP `purpose`
# ---------------------------------------------------------------------------
print("\n-- WP1: re-install over a settings.json renamed to disable hooks --")
_d = tempfile.mkdtemp()
try:
    open(os.path.join(_d, "bootstrap.config.yaml"), "w").write(SERVICE)
    _r0 = subprocess.run([sys.executable, BIN, "-C", _d],
                         capture_output=True, text=True)
    _s = os.path.join(_d, ".claude", "settings.json")
    check("RENAME-0: a plain re-install prints no rename warning (control)",
          _r0.returncode == 0 and "settings.json.disabled" not in _r0.stderr)
    os.rename(_s, _s + ".disabled")
    _rd = subprocess.run([sys.executable, BIN, "-C", _d, "--dry-run"],
                         capture_output=True, text=True)
    check("RENAME-1: --dry-run warns that it would re-enable the hooks",
          _rd.returncode == 0
          and "warning: .claude/settings.json.disabled exists" in _rd.stderr
          and "would create" in _rd.stderr and not os.path.exists(_s))
    _r1 = subprocess.run([sys.executable, BIN, "-C", _d],
                         capture_output=True, text=True)
    check("RENAME-2: the re-install that recreates settings.json says so on "
          "stderr and still exits 0",
          _r1.returncode == 0 and os.path.exists(_s)
          and "warning: .claude/settings.json.disabled exists" in _r1.stderr
          and "turns every hook back on" in _r1.stderr)
    _r2 = subprocess.run([sys.executable, BIN, "-C", _d],
                         capture_output=True, text=True)
    check("RENAME-3: with settings.json present again, no rename warning "
          "(control)",
          _r2.returncode == 0 and "settings.json.disabled" not in _r2.stderr)
finally:
    shutil.rmtree(_d, ignore_errors=True)

print("\n-- WP1: tools.md records what each MCP server is for --")
_mc, _me = cfg_from(SERVICE + """mcp:
  servers:
    - {name: github, command: "npx -y gh-mcp", purpose: "PR and issue access"}
    - {name: ctx, command: "npx -y ctx-mcp"}
""")
_tools_md = _tmpl.TEMPLATES["tools"](_mc)
check("MCP-1: a server's purpose is rendered in tools.md",
      _me == [] and "- **github** - `npx -y gh-mcp` - PR and issue access"
      in _tools_md)
check("MCP-2: a server with no purpose says so instead of looking complete",
      "- **ctx** - `npx -y ctx-mcp` - TODO: purpose not recorded" in _tools_md)
_mc0, _ = cfg_from(SERVICE)
check("MCP-3: no servers still renders the minimal-start line (control)",
      "_(none - minimal start, by design)_" in _tmpl.TEMPLATES["tools"](_mc0))

# --------------------------------------------------------------------------- #
# Every lib module compiles CLEAN — no SyntaxWarning
# --------------------------------------------------------------------------- #
# WHY THIS EXISTS, because the failure mode is genuinely sneaky: CPython emits
# `SyntaxWarning: invalid escape sequence` only when it COMPILES the source.
# Once a `__pycache__/*.pyc` exists the module loads from bytecode and the
# warning never fires again — so a developer's suite runs green over a warning
# that CI, which always compiles fresh, prints to stderr on every run. Two
# suites here assert an installer run "writes nothing to stderr"; a warning
# leaking into that stream fails them, and it did (5 checks, PR #35), while the
# same tree was green locally.
#
# The escapes that caused it (`\.` and a backslash-backtick inside emitted
# shell COMMENT text) were harmless to the emitted bytes — Python keeps an
# unrecognised escape verbatim — which is exactly why nothing behavioural
# caught them. In a future Python they become a SyntaxError, so this is also
# forward-cover, not only tidiness.
print("\n-- lib modules compile without SyntaxWarning --")
_LIB = os.path.join(ROOT, "lib")
for _mod in sorted(f for f in os.listdir(_LIB) if f.endswith(".py")):
    with warnings.catch_warnings(record=True) as _w:
        warnings.simplefilter("always")
        try:
            compile(open(os.path.join(_LIB, _mod), encoding="utf-8").read(),
                    _mod, "exec")
            _syn = [str(x.message) for x in _w
                    if issubclass(x.category, SyntaxWarning)]
        except SyntaxError as _e:          # pragma: no cover - would be loud
            _syn = [f"SyntaxError: {_e}"]
    if _syn:                                # this suite's check() is (name, cond)
        print(f"        {_mod}: {_syn}")
    check(f"lib/{_mod} compiles with no SyntaxWarning", not _syn)

# ---------------------------------------------------------------------------
# [WP1] Test commands whose "no tests" the test gate cannot see are named at
# install time. Advisory: rc stays 0 and the gate is unchanged.
# ---------------------------------------------------------------------------
print("\n-- [WP1] install-time notes: test commands the gate cannot read --")
_NPM_INIT_PKG = {"name": "x", "version": "1.0.0", "scripts": {
    "test": 'echo "Error: no test specified" && exit 1'}}


def _notes_for(test_cmd, pkg=None):
    d = tempfile.mkdtemp()
    try:
        with open(os.path.join(d, "c.yaml"), "w") as fh:
            fh.write('project:\n  name: x\n  archetype: service\n'
                     f'commands:\n  test: {_json.dumps(test_cmd)}\n')
        if pkg is not None:
            with open(os.path.join(d, "package.json"), "w") as fh:
                _json.dump(pkg, fh)
        r = subprocess.run([sys.executable, BIN, "-c", "c.yaml", "-C", d],
                           capture_output=True, text=True)
        return r.returncode, [ln for ln in r.stderr.splitlines()
                              if ln.startswith("warning: ")
                              and " is empty: " not in ln]
    finally:
        shutil.rmtree(d, ignore_errors=True)


_rc, _n = _notes_for("npm test", _NPM_INIT_PKG)
check("npm's placeholder test script is named at install time",
      any("npm's placeholder" in n for n in _n))
check("and the install still exits 0", _rc == 0)
_rc, _n = _notes_for("npm test", {"scripts": {"test": "node --test"}})
check("a real npm test script draws no note", _n == [])
_rc, _n = _notes_for("npx jest")
check("jest without --passWithNoTests is named", any("jest" in n for n in _n))
_rc, _n = _notes_for("vitest run --passWithNoTests")
check("vitest with --passWithNoTests draws no note", _n == [])
_rc, _n = _notes_for("pytest -q")
check("pytest draws no note (the gate reads its exit 5 itself)", _n == [])

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

#!/usr/bin/env python3
"""R-7 (IC-5) - the SDK gate module, per seam §9 VERBATIM.

Spec: .claude/specs/bootstrap-v2/requirements.md (AC-7-1..AC-7-6).
- Single public builder build_hooks(config) -> {"PreToolUse": [...], ...}
- No I/O at import time; refusals use the structured PreToolUse deny
  shape; reason strings semantically equal the shell gates' messages.
- The claude_agent_sdk import is stubbed: these tests exercise the
  emitted module's logic, not the SDK.

Run: python3 tests/test_sdk_gates.py
"""
import ast
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


# ---- stub claude_agent_sdk BEFORE importing the emitted module ---------- #
class _StubHookMatcher:
    def __init__(self, matcher=None, hooks=None, timeout=None):
        self.matcher = matcher
        self.hooks = hooks or []
        self.timeout = timeout


_stub = types.ModuleType("claude_agent_sdk")
_stub.HookMatcher = _StubHookMatcher
sys.modules["claude_agent_sdk"] = _stub

from minyaml import load_yaml            # noqa: E402
from defaults import resolve_config      # noqa: E402
import templates                         # noqa: E402
from sdk_gates_template import SDK_GATES  # noqa: E402

FULL = """project:
  name: sdkgates
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
secrets:
  never_read_paths:
    - ".env*"
    - "*.pem"
    - "secrets/**"
deps:
  approved:
    - requests
    - numpy
"""

cfg, _errs = resolve_config(load_yaml(FULL))
assert not _errs, _errs
body = templates.TEMPLATES["sdk_gates"](cfg)

# ---- emitted source is valid Python ------------------------------------- #
try:
    ast.parse(body)
    check("emitted gates.py parses as Python", True)
except SyntaxError as e:
    check("emitted gates.py parses as Python", False, str(e))
    print("cannot continue against unparseable emission")
    sys.exit(1)

# ---- AC-7-4: import under an import-side-effect probe -------------------- #
# Any file/subprocess/socket I/O at import time must trip the probe. The
# import machinery itself uses io.open_code, which the probe leaves alone.
workdir = tempfile.mkdtemp()
mod_path = os.path.join(workdir, "gates.py")
with open(mod_path, "w") as fh:
    fh.write(body)

_probe_hits = []
import builtins  # noqa: E402
_real_open = builtins.open
_real_run = subprocess.run


def _probed_open(*a, **k):
    _probe_hits.append(("open", a[:1]))
    return _real_open(*a, **k)


def _probed_run(*a, **k):
    _probe_hits.append(("subprocess.run", a[:1]))
    return _real_run(*a, **k)


builtins.open = _probed_open
subprocess.run = _probed_run
try:
    spec = importlib.util.spec_from_file_location("emitted_gates", mod_path)
    gates_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates_mod)
finally:
    builtins.open = _real_open
    subprocess.run = _real_run

check("AC-7-4: no I/O side effects at import time",
      _probe_hits == [], repr(_probe_hits))
check("AC-7-4: no consumer-core path imports the emitted module",
      not any("sdk_gates.gates" in p or "from gates import" in p
              for f in ("installer.py", "interview.py", "defaults.py",
                        "templates.py")
              for p in [open(os.path.join(ROOT, "lib", f)).read()]))

# ---- seam §9 public-surface shape ---------------------------------------- #
public = [n for n in dir(gates_mod)
          if not n.startswith("_") and callable(getattr(gates_mod, n))
          and getattr(getattr(gates_mod, n), "__module__", "")
          == "emitted_gates"]
check("seam §9: exactly one public callable, build_hooks",
      public == ["build_hooks"], repr(public))
check("seam §9: __all__ is exactly ['build_hooks']",
      getattr(gates_mod, "__all__", None) == ["build_hooks"])

hooks_map = gates_mod.build_hooks(gates_mod.RESOLVED_CONFIG)
check("build_hooks returns PreToolUse + PostToolUse mapping",
      set(hooks_map) == {"PreToolUse", "PostToolUse"}, repr(set(hooks_map)))
n_matchers = sum(len(v) for v in hooks_map.values())
check("one HookMatcher per enabled gate",
      n_matchers == len(gates_mod.GATES),
      f"{n_matchers} matchers vs {gates_mod.GATES}")

# fail-loud on malformed config, never a smaller gate set
try:
    gates_mod.build_hooks({"commands": {}})
    check("build_hooks raises on missing config keys", False, "no raise")
except KeyError:
    check("build_hooks raises on missing config keys", True)

# matcher table stays in sync with the shell suite's event map
sdk_side = {name: gates_mod._GATE_MATCHERS[name] for name in SDK_GATES}
shell_side = {name: templates.HOOK_EVENT_MAP[name] for name in SDK_GATES}
check("gate event/matcher table == HOOK_EVENT_MAP subset",
      sdk_side == shell_side,
      repr({k: (sdk_side[k], shell_side[k]) for k in SDK_GATES
            if sdk_side[k] != shell_side[k]}))


def _gate(name):
    fact = gates_mod._GATE_FACTORIES[name]
    return fact(gates_mod.RESOLVED_CONFIG)


def run_gate(name, input_data):
    return asyncio.run(_gate(name)(input_data, "tu-1", None))


def deny_reason(result):
    return (result.get("hookSpecificOutput") or {}).get(
        "permissionDecisionReason", "")


def is_deny(result):
    hso = result.get("hookSpecificOutput") or {}
    return (hso.get("permissionDecision") == "deny"
            and hso.get("hookEventName") == "PreToolUse")


# ---- AC-7-1: known-bad denies with the right reason; known-good allows --- #
proj = tempfile.mkdtemp()
os.environ["CLAUDE_PROJECT_DIR"] = proj

# secrets-gate
r = run_gate("secrets-gate",
             {"tool_input": {"file_path": "config/prod.env"}})
check("AC-7-1 secrets: suffix-form .env* blocked (T-1 semantics)",
      is_deny(r) and deny_reason(r)
      == "BLOCKED: config/prod.env matches never-read pattern .env*",
      repr(r))
r = run_gate("secrets-gate", {"tool_input": {"file_path": "secrets/k.txt"}})
check("AC-7-1 secrets: directory glob secrets/** blocked", is_deny(r))
r = run_gate("secrets-gate", {"tool_input": {"file_path": "CERT.PEM"}})
check("AC-7-1 secrets: case-insensitive *.pem blocked", is_deny(r))
r = run_gate("secrets-gate", {"tool_input": {"file_path": "src/main.py"}})
check("AC-7-1 secrets: benign path allowed with {}", r == {})
r = run_gate("secrets-gate", {"tool_input": {}})
check("AC-7-1 secrets: no path -> allow (shell parity)", r == {})

# dependency-gate
r = run_gate("dependency-gate",
             {"tool_input": {"command": "pip install requests leftpad"}})
check("AC-7-1 deps: unapproved package denied with shell-parity reason",
      is_deny(r) and deny_reason(r).startswith(
          "Dependency gate: not in deps.md approved list: leftpad"),
      repr(r))
r = run_gate("dependency-gate",
             {"tool_input": {"command": "pip install requests numpy"}})
check("AC-7-1 deps: approved packages allowed", r == {})
r = run_gate("dependency-gate",
             {"tool_input": {"command":
                             "pip install -r requirements.txt"}})
check("AC-7-1 deps: value-flag consumes next token (S-2)", r == {})
r = run_gate("dependency-gate", {"tool_input": {"command": "ls -la"}})
check("AC-7-1 deps: non-install command allowed", r == {})

# tdd-gate (inside a real project dir)
os.makedirs(os.path.join(proj, "src"), exist_ok=True)
os.makedirs(os.path.join(proj, "tests"), exist_ok=True)
srcfile = os.path.join(proj, "src", "widget.py")
open(srcfile, "w").write("x = 1\n")
r = run_gate("tdd-gate", {"tool_input": {"file_path": "src/widget.py"}})
check("AC-7-1 tdd: no newer matching test -> deny with shell reason",
      is_deny(r) and deny_reason(r)
      == "TDD gate: write a failing test for widget before src/widget.py.",
      repr(r))
time.sleep(0.05)
open(os.path.join(proj, "tests", "test_widget.py"), "w").write("t = 1\n")
os.utime(os.path.join(proj, "tests", "test_widget.py"))
r = run_gate("tdd-gate", {"tool_input": {"file_path": "src/widget.py"}})
check("AC-7-1 tdd: newer matching test -> allow", r == {})
r = run_gate("tdd-gate", {"tool_input": {"file_path": "docs/readme.md"}})
check("AC-7-1 tdd: non-source path allowed", r == {})

# spec-gate-commit (real git repo)
subprocess.run(["git", "init", "-q"], cwd=proj, check=True)
subprocess.run(["git", "-C", proj, "config", "user.email", "t@t"],
               check=True)
subprocess.run(["git", "-C", proj, "config", "user.name", "t"], check=True)
open(os.path.join(proj, "newfile.py"), "w").write("pass\n")
subprocess.run(["git", "-C", proj, "add", "newfile.py"], check=True)
os.chdir(proj)
r = run_gate("spec-gate-commit",
             {"tool_input": {"command": "git commit -m x"}})
check("AC-7-1 spec-commit: no spec corpus -> deny with shell reason",
      is_deny(r) and deny_reason(r).startswith(
          "Commit blocked: no active spec/task files exist yet."),
      repr(r))
os.makedirs(os.path.join(proj, ".claude", "specs"), exist_ok=True)
open(os.path.join(proj, ".claude", "specs", "INDEX.md"), "w").write(
    "no mention\n")
r = run_gate("spec-gate-commit",
             {"tool_input": {"command": "git commit -m x"}})
check("AC-7-1 spec-commit: unreferenced staged file -> deny naming it",
      is_deny(r) and deny_reason(r).startswith(
          "Commit blocked: files not referenced by any active spec: "
          "newfile.py"),
      repr(r))
open(os.path.join(proj, ".claude", "specs", "INDEX.md"), "a").write(
    "covers newfile.py here\n")
r = run_gate("spec-gate-commit",
             {"tool_input": {"command": "git commit -m x"}})
check("AC-7-1 spec-commit: referenced staged file -> allow", r == {})
r = run_gate("spec-gate-commit", {"tool_input": {"command": "ls"}})
check("AC-7-1 spec-commit: non-commit command allowed", r == {})

# eval-gate
subprocess.run(["git", "-C", proj, "add", "-A"], check=True)
subprocess.run(["git", "-C", proj, "commit", "-qm", "c1"], check=True)
open(os.path.join(proj, "prompts.md"), "w").write("p\n")
subprocess.run(["git", "-C", proj, "add", "prompts.md"], check=True)
subprocess.run(["git", "-C", proj, "commit", "-qm", "c2"], check=True)
r = run_gate("eval-gate", {"tool_input": {"command": "git push"}})
check("AC-7-1 eval: prompt diff without eval pass -> deny, shell reason",
      is_deny(r) and deny_reason(r)
      == "Eval gate: run evals before pushing prompt changes.", repr(r))
open(os.path.join(proj, ".claude", ".last-eval-pass"), "w").write("ok\n")
r = run_gate("eval-gate", {"tool_input": {"command": "git push"}})
check("AC-7-1 eval: with eval pass -> allow", r == {})

# test-gate (fresh mark => runs commands.test = "true")
r = run_gate("test-gate", {"tool_input": {"command": "git commit -m x"}})
check("AC-7-1 test: passing commands.test -> allow + mark written",
      r == {} and os.path.isfile(
          os.path.join(proj, ".claude", ".last-test-pass")))

# ---- AC-7-2: empty commands.test still fails loud ------------------------ #
cfg_empty = dict(gates_mod.RESOLVED_CONFIG)
cfg_empty["commands"] = {"test": "", "lint": "", "format": ""}
os.remove(os.path.join(proj, ".claude", ".last-test-pass"))
gate = gates_mod._GATE_FACTORIES["test-gate"](cfg_empty)
r = asyncio.run(gate({"tool_input": {"command": "git commit -m x"}},
                     "tu-1", None))
check("AC-7-2: empty commands.test denies with the TODO reason",
      is_deny(r) and "TODO: commands.test unset" in deny_reason(r)
      and "Commit blocked: tests failing." in deny_reason(r), repr(r))

# format-lint-gate: never denies (PostToolUse feedback only)
gate = gates_mod._GATE_FACTORIES["format-lint-gate"](
    {"commands": {"format": "false", "lint": ""},
     "secrets": {"never_read_paths": []}, "deps": {"approved": []}})
r = asyncio.run(gate({"tool_input": {}}, "tu-1", None))
check("format-lint: failing format -> systemMessage, never a deny",
      "hookSpecificOutput" not in r
      and r.get("systemMessage") == "format reported issues", repr(r))

# ---- Code-review fix regressions ---------------------------------------- #
# tdd-gate: ABSOLUTE file_path (what Claude Code actually sends) must be
# normalized and still enforce, not silently pass.
r = run_gate("tdd-gate",
             {"tool_input": {"file_path": os.path.join(proj, "src",
                                                       "brandnew.py")}})
check("fix: tdd-gate enforces on ABSOLUTE file_path (deny, not no-op)",
      is_deny(r), repr(r))

# dependency-gate: scoped @pkg and tab / `python -m pip` invocations
r = run_gate("dependency-gate",
             {"tool_input": {"command": "npm install @evil/backdoor"}})
check("fix: dependency-gate blocks unapproved @scoped npm package",
      is_deny(r) and "@evil/backdoor" in deny_reason(r), repr(r))
r = run_gate("dependency-gate",
             {"tool_input": {"command": "pip install\tleftpad"}})
check("fix: dependency-gate blocks tab-separated install", is_deny(r))
r = run_gate("dependency-gate",
             {"tool_input": {"command": "python -m pip install leftpad"}})
check("fix: dependency-gate blocks `python -m pip install`", is_deny(r))

# secrets-gate: bash negated class [^...] must OVER-match (deny-list bias)
gate = gates_mod._GATE_FACTORIES["secrets-gate"](
    {"secrets": {"never_read_paths": ["[^.]env"]},
     "deps": {"approved": []}, "commands": {}})
r = asyncio.run(gate({"tool_input": {"file_path": "aenv"}}, "t", None))
check("fix: secrets negated-class [^.]env over-matches 'aenv' (deny)",
      is_deny(r), repr(r))

os.chdir(HERE)
del os.environ["CLAUDE_PROJECT_DIR"]
shutil.rmtree(proj, ignore_errors=True)
shutil.rmtree(workdir, ignore_errors=True)

# ---- fix: bool/None config values render VALID Python (no NameError) ----- #
_, cfg_bool_e = resolve_config(load_yaml(
    "project:\n  name: b\n  archetype: service\n"
    "commands:\n  test: true\n  lint: false\n"
    "secrets:\n  never_read_paths: [true, \".env\"]\n"))
assert not cfg_bool_e, cfg_bool_e
cfg_bool, _ = resolve_config(load_yaml(
    "project:\n  name: b\n  archetype: service\n"
    "commands:\n  test: true\n  lint: false\n"
    "secrets:\n  never_read_paths: [true, \".env\"]\n"))
body_bool = templates.TEMPLATES["sdk_gates"](cfg_bool)
try:
    g2 = {}
    exec(compile(body_bool, "g2", "exec"), g2)   # NameError if true/null leak
    check("fix: bool/None config renders valid Python (no true/null leak)",
          g2["RESOLVED_CONFIG"]["commands"]["test"] == "True")
except NameError as e:
    check("fix: bool/None config renders valid Python", False, str(e))

# ---- fix: build_hooks membership follows the passed config --------------- #
# Render from a SUBSET config (service, no tdd/eval) so the emission-time
# GATES is a strict subset of all 7 - only then can "enlarge" distinguish
# the fix (reads config) from the old code (frozen GATES).
cfg_sub, _e = resolve_config(load_yaml(
    "project:\n  name: sub\n  archetype: service\n"
    "commands:\n  test: \"true\"\n  lint: \"true\"\n"))
assert not _e, _e
body_sub = templates.TEMPLATES["sdk_gates"](cfg_sub)
g_sub = {}
exec(compile(body_sub, "gsub", "exec"), g_sub)
n_emitted = len(g_sub["GATES"])
check("fix: subset fixture emits FEWER than 7 gates (precondition)",
      0 < n_emitted < 7, f"GATES={g_sub['GATES']}")
# Enlarge: pass a config warranting all 7 -> build_hooks must exceed the
# emission snapshot (proves membership tracks config, not frozen GATES).
big = dict(g_sub["RESOLVED_CONFIG"])
big["_resolved_hooks"] = list(g_sub["_GATE_FACTORIES"])   # all 7
hm_big = g_sub["build_hooks"](big)
check("fix: build_hooks ENLARGES membership beyond emission GATES",
      sum(len(v) for v in hm_big.values()) == 7 and n_emitted < 7)
small = dict(g_sub["RESOLVED_CONFIG"])
small["_resolved_hooks"] = ["secrets-gate"]
check("fix: build_hooks shrinks membership from config (1 gate)",
      sum(len(v) for v in g_sub["build_hooks"](small).values()) == 1)
# B1: an EMPTY _resolved_hooks must NOT silently disable all gates -
# it falls back to the emission GATES (a security substrate never builds
# zero gates from a stray []).
empty = dict(g_sub["RESOLVED_CONFIG"])
empty["_resolved_hooks"] = []
check("fix: empty _resolved_hooks falls back to GATES (not zero)",
      sum(len(v) for v in g_sub["build_hooks"](empty).values())
      == n_emitted)

# ---- B3/B4: versioned pip + cross-line verb-merge -------------------------#
gdep = gates_mod._GATE_FACTORIES["dependency-gate"](
    {"deps": {"approved": ["requests"]},
     "secrets": {"never_read_paths": []}, "commands": {}})
def _dep(c):
    return asyncio.run(gdep({"tool_input": {"command": c}}, "t", None))
check("fix: dependency-gate blocks versioned `pip3.11 install`",
      is_deny(_dep("pip3.11 install evil")), repr(_dep("pip3.11 install evil")))
check("fix: dependency-gate does NOT merge a verb split across lines",
      _dep("echo npm\ninstall foo") == {}, repr(_dep("echo npm\ninstall foo")))

# ---- B2: worktree comment renders as valid, un-mangled guidance ---------- #
wbody = templates.TEMPLATES["loop_sh"](cfg)
check("fix: worktree guidance one-liner is intact (not backslash-collapsed)",
      "|| echo '.claude/worktrees/' >>" in wbody
      and " \\\n" not in wbody.split("info/exclude", 1)[0][-200:])

# ---- AC-7-5: reason literals appear in the emitted SHELL gate bodies ----- #
# (message parity, modulo the documented interpolation sites: the {target}/
# {pat}/{stem}-style values and the shell's two-line stderr splits)
parity = {
    "secrets-gate": "matches never-read pattern",
    "spec-gate-commit": "Commit blocked: files not referenced by any "
                        "active spec:",
    "dependency-gate": "Dependency gate: not in deps.md approved list:",
    "test-gate": "Commit blocked: tests failing.",
    "tdd-gate": "TDD gate: write a failing test for",
    "eval-gate": "Eval gate: run evals before pushing prompt",
    "format-lint-gate": "format reported issues",
}
for hk, needle in parity.items():
    shell_body = templates.TEMPLATES["hook"](hk, cfg) or ""
    check(f"AC-7-5 parity [{hk}]: reason literal in shell body",
          needle in shell_body.replace("\\\n", " ").replace(" \\", " "),
          repr(needle))
# the second-line guidance strings are relayed too
for hk, needle in {
    "spec-gate-commit": "Run /spec-new or add them to a tasks/*.md file.",
    "dependency-gate":
        "Approve in-session and update .claude/steering/deps.md.",
}.items():
    check(f"AC-7-5 parity [{hk}]: guidance line in shell body",
          needle in (templates.TEMPLATES["hook"](hk, cfg) or ""))

# ---- AC-7-3 + AC-7-6: emission shape and manifest tier ------------------- #
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(FULL)
    rr = subprocess.run([sys.executable, BIN, "-C", d],
                        capture_output=True, text=True)
    check("install with SDK gates succeeds", rr.returncode == 0, rr.stderr)
    gp = os.path.join(d, ".claude", "sdk_gates", "gates.py")
    check("gates.py emitted at the seam §9 path", os.path.isfile(gp))
    manifest = json.load(open(os.path.join(d, ".claude",
                                           ".installer-manifest.json")))
    entry = next((f for f in manifest["files"]
                  if f["path"] == ".claude/sdk_gates/gates.py"), None)
    check("AC-7-6: manifest tier is security-critical with a digest",
          entry is not None and entry.get("tier") == "security-critical"
          and "digest" in entry, repr(entry))
    settings = json.load(open(os.path.join(d, ".claude", "settings.json")))
    shell_hooks = os.listdir(os.path.join(d, ".claude", "hooks"))
    check("AC-7-3: full shell suite still emitted alongside (SEV-1 path)",
          "secrets-gate.sh" in shell_hooks
          and "iteration-summary-enforcement.sh" in shell_hooks)
    check("AC-7-3: settings.json still wires the shell suite",
          any("secrets-gate.sh" in json.dumps(settings)
              for _ in [0]))
finally:
    shutil.rmtree(d, ignore_errors=True)

# ---- retrofit: overlay drops the module ---------------------------------- #
# Valid retrofit config per the B5 scaffold-but-defer + R0.8 rules (same
# shape as tests/test_retrofit.py fixtures).
RETRO = """mode: "retrofit"
project:
  name: r-sdk
  archetype: service
secrets:
  enabled: true
deps:
  enabled: true
  approved: []
commands:
  test: "true"
  lint: "true"
retrofit:
  spec_strategy: "forward-only"
  legacy_allowlist:
    - "src/**"
  retrofit_active: true
  r08_committed: true
"""
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(RETRO)
    rr = subprocess.run([sys.executable, BIN, "-C", d],
                        capture_output=True, text=True)
    check("retrofit: install succeeds", rr.returncode == 0, rr.stderr)
    check("retrofit: gates.py NOT emitted (shell-era track, overlay drop)",
          not os.path.exists(os.path.join(d, ".claude", "sdk_gates")))
    cfgr, _rerrs = resolve_config(load_yaml(RETRO))
    check("retrofit: fixture config resolves cleanly", _rerrs == [],
          repr(_rerrs))
    import installer as _inst
    paths = {a["path"] for a in _inst.build_plan(cfgr)}
    check("retrofit: gates.py NOT in retrofit plan",
          ".claude/sdk_gates/gates.py" not in paths)
    check("retrofit: greenfield plan still HAS gates.py (drop is "
          "retrofit-scoped)",
          ".claude/sdk_gates/gates.py"
          in {a["path"] for a in _inst.build_plan(cfg)})
finally:
    shutil.rmtree(d, ignore_errors=True)

# ---- fix (eval-gate): whole outgoing @{u}..HEAD range, not just HEAD~1 ---- #
# A prompt change buried 2 commits back (behind a later non-prompt commit)
# must still gate a push. The old HEAD~1-only check missed it; this proves
# the @{u}..HEAD range fix. Requires an upstream, so set one up.
ev = tempfile.mkdtemp()
bare = tempfile.mkdtemp()
try:
    def _git(*a, cwd=ev):
        subprocess.run(["git", *a], cwd=cwd, check=True,
                       capture_output=True, text=True)
    subprocess.run(["git", "init", "--bare", "-q", bare], check=True,
                   capture_output=True)
    _git("init", "-q")
    _git("config", "user.email", "t@t"); _git("config", "user.name", "t")
    open(os.path.join(ev, "readme.md"), "w").write("x\n")
    _git("add", "-A"); _git("commit", "-qm", "base")
    _git("remote", "add", "origin", bare)
    _git("push", "-q", "-u", "origin", "HEAD")
    # commit 1 (2 back after the next): a PROMPT change
    open(os.path.join(ev, "prompts.md"), "w").write("system prompt\n")
    _git("add", "-A"); _git("commit", "-qm", "prompt change")
    # commit 2 (newest): unrelated code, so HEAD~1 alone would miss prompts
    open(os.path.join(ev, "code.txt"), "w").write("y\n")
    _git("add", "-A"); _git("commit", "-qm", "code fix")
    os.environ["CLAUDE_PROJECT_DIR"] = ev
    egate = gates_mod._GATE_FACTORIES["eval-gate"](gates_mod.RESOLVED_CONFIG)
    rr = asyncio.run(egate({"tool_input": {"command": "git push"}},
                           "t", None))
    check("fix: eval-gate gates a prompt change buried 2 commits back",
          is_deny(rr), repr(rr))
    del os.environ["CLAUDE_PROJECT_DIR"]
finally:
    shutil.rmtree(ev, ignore_errors=True)
    shutil.rmtree(bare, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

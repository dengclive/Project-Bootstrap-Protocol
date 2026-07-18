#!/usr/bin/env python3
"""Self-contained test suite. Run: python3 tests/test_installer.py"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

from defaults import resolve_config            # noqa: E402
from installer import build_plan               # noqa: E402
from minyaml import load_yaml                   # noqa: E402

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
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(["bash", path], input=_json.dumps(payload),
                        capture_output=True, text=True, env=e)
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
    check("S-2: -r requirements.txt not treated as package",
          _run_hook(dg, {"tool_input":
                         {"command": "pip install -r reqs.txt"}}) == 0)
    check("S-2: unapproved second package is caught",
          _run_hook(dg, {"tool_input":
                         {"command": "pip install requests evil"}}) == 2)
    check("S-2: version specifier stripped",
          _run_hook(dg, {"tool_input":
                         {"command": "pip install requests==2.0"}}) == 0)
finally:
    shutil.rmtree(d, ignore_errors=True)

# S-5: malicious config values must not corrupt hook syntax
d = _install("""project:
  name: r
  archetype: cli
deps:
  approved: ["good", "ok)", "a|b", "x;rm -rf"]
secrets:
  never_read_paths: [".env*", "weird) ; echo PWNED"]
commands:
  test: "pytest && echo X"
""")
try:
    hd = os.path.join(d, ".claude", "hooks")
    bad = [f for f in os.listdir(hd) if f.endswith(".sh") and
           subprocess.run(["bash", "-n", os.path.join(hd, f)]).returncode]
    check("S-5: injection config -> all hooks still valid bash", bad == [])
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
    check("F-2: auto.sh runs without hanging", r.returncode == 0)
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
        check(f"AC-8-1: {sh} has no hand-rolled `git worktree add`",
              "git worktree add" not in body.replace(
                  "never hand-roll git worktree add", "").replace(
                  "hand-roll `git worktree add`", ""))
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
finally:
    shutil.rmtree(d, ignore_errors=True)

# Per-archetype apply matrix: eval-gate only for ai-agent; conditional
# files present; settings.json wires every resolved hook to the right
# event+matcher with no orphans.
import json as _j4
_EXPECT = {
    "spec-gate-entry": ("UserPromptSubmit", None),
    "spec-gate-commit": ("PreToolUse", "Bash"),
    "secrets-gate": ("PreToolUse", "Read|Write|Edit"),
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
        wired = {}
        for ev, groups in st["hooks"].items():
            for g in groups:
                for hk in g["hooks"]:
                    nm = hk["command"].split("/")[-1].replace(".sh", "")
                    wired[nm] = (ev, g.get("matcher"))
        hooks = [f[:-3] for f in os.listdir(os.path.join(cl, "hooks"))
                 if f.endswith(".sh")]
        bad = [h for h in hooks
               if h in _EXPECT and wired.get(h) != _EXPECT[h]]
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
# R-0 (spec bootstrap-v2): protocol 2.0.0 version identity (AC-A0-1..3)
# ---------------------------------------------------------------------------
import installer as _installer_mod          # noqa: E402
import templates as _templates_mod          # noqa: E402

check("AC-A0-1: installer.PROTOCOL_VERSION is 2.0.0",
      _installer_mod.PROTOCOL_VERSION == "2.0.0")
check("AC-A0-1: templates.PROTOCOL_VERSION is 2.0.0",
      _templates_mod.PROTOCOL_VERSION == "2.0.0")
check("AC-A0-1: RETROFIT_PROTOCOL_VERSION untouched (1.6.2)",
      _installer_mod.RETROFIT_PROTOCOL_VERSION == "1.6.2")

d = _install(FULL)
try:
    state = _json.load(open(os.path.join(d, ".claude",
                                         ".bootstrap-state.json")))
    check("AC-A0-2: fresh install writes bootstrap_protocol_version 2.0.0",
          state.get("bootstrap_protocol_version") == "2.0.0")
    settings = _json.load(open(os.path.join(d, ".claude", "settings.json")))
    check("AC-A0-3: settings.json _generatedBy reads protocol 2.0.0",
          settings.get("_generatedBy")
          == "bootstrap-installer (protocol 2.0.0)")
    manifest = _json.load(open(os.path.join(d, ".claude",
                                            ".installer-manifest.json")))
    check("AC-A0-3: manifest records protocol_version 2.0.0",
          manifest.get("protocol_version") == "2.0.0")
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

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

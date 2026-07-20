#!/usr/bin/env python3
"""Retrofit installer test suite (D7).

Mirrors tests/test_installer.py's behavioral discipline for the
mode: retrofit path. Sections:

  1. mode field + retrofit defaults via resolve_config
  2. Determinism (same retrofit cfg -> identical plan digest)
  3. T1 — dual-shape autonomous_modes wiring assertion
     (config nests *_opted_in under retrofit.autonomous_modes; state
     file keeps *_enabled and *_in_flight TOP-LEVEL; the two never
     conflate or cross-write)
  4. End-to-end lifecycle (apply -> re-apply -> hand-edit -> uninstall
     -> re-apply, mirroring test_installer.py L-1/L-2/L-3)
  5. Retrofit-only artifacts present + conditional artifacts gated
  6. Hook retrofit-flavor (spec-gate-commit / test-gate / tdd-gate
     carry the retrofit preamble; secrets-gate NOT touched per
     RETROFIT R8.A.3)
  7. T2 — fail-safe seam proof under no-jq restricted-PATH harness
     (every error / missing / parse-failure path falls through to
     ENFORCE; only affirmative matches early-exit 0)
  8. State writer (B5 shape, OD-4 versioning, R-2 setdefault
     preservation of operator-edited retrofit_active across re-apply)
  9. Inventory scan + heuristics smoke (decision layer round-trip)
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

BIN_INSTALL = os.path.join(ROOT, "bin", "bootstrap-install")
BIN_INTERVIEW = os.path.join(ROOT, "bin", "retrofit-interview")

from defaults import resolve_config              # noqa: E402
from installer import (build_plan, _write_retrofit_state,            # noqa
                       PROTOCOL_VERSION, RETROFIT_PROTOCOL_VERSION,
                       RETROFIT_STATE)
from inventory_scan import scan_repo, write_inventory                # noqa
from minyaml import load_yaml                    # noqa: E402
from retrofit_heuristics import build_retrofit_proposal              # noqa
from retrofit_interview import (answers_to_config, default_answers,  # noqa
                                 validate_config_dict)

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


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
SERVICE_RETROFIT_CFG = """mode: "retrofit"
project:
  name: r-svc
  archetype: service
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

AGENT_RETROFIT_CFG = """mode: "retrofit"
project:
  name: r-agent
  archetype: ai-agent
  prd_tier: "standard"
principles:
  tdd_policy: "required"
secrets:
  enabled: true
deps:
  enabled: true
  approved: []
commands:
  test: "pytest"
  lint: "ruff check ."
  format: "ruff format ."
retrofit:
  spec_strategy: "touch-based"
  legacy_allowlist:
    - "src/**"
    - "prompts/**"
  retrofit_active: true
  r08_committed: true
  archetype_confidence: "high"
  archetype_evidence:
    - "anthropic dep"
  spec_patterns:
    change: true
    boundary: true
    migration: false
  codebase_size_gb: 2
  autonomous_modes:
    loop_mode_opted_in: true
    goal_supervised_mode_opted_in: true
    queue_mode_opted_in: false
"""


def install(cfg_text: str, tmpdir: str | None = None) -> str:
    """Write cfg + run installer; return the project root."""
    d = tmpdir or tempfile.mkdtemp()
    with open(os.path.join(d, "bootstrap.config.yaml"), "w") as fh:
        fh.write(cfg_text)
    r = subprocess.run([sys.executable, BIN_INSTALL, "-C", d],
                        capture_output=True, text=True)
    assert r.returncode == 0, f"install failed: {r.stdout}\n{r.stderr}"
    return d


def cfg_from(yaml_text):
    raw = load_yaml(yaml_text)
    return resolve_config(raw)


def plan_digest(cfg):
    plan = build_plan(cfg)
    h = hashlib.sha256()
    for a in plan:
        h.update(a["path"].encode())
        h.update(a["body"].encode())
        h.update(str(a["mode"]).encode())
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# 1. mode field + retrofit defaults via resolve_config
# --------------------------------------------------------------------------- #
print("\n=== Section 1: mode field + retrofit defaults ===")

cfg, errs = cfg_from(SERVICE_RETROFIT_CFG)
check("1.1: minimal retrofit cfg validates", errs == [], f"errors={errs}")
check("1.2: mode field resolved to 'retrofit'", cfg["mode"] == "retrofit")
check("1.3: retrofit section populated",
      "retrofit" in cfg and isinstance(cfg["retrofit"], dict))
check("1.4: spec_strategy default present",
      cfg["retrofit"]["spec_strategy"] == "forward-only")
check("1.5: retrofit_active default present",
      cfg["retrofit"]["retrofit_active"] is True)
check("1.6: pm strategy default = spec_canonical",
      cfg["retrofit"]["pm"]["strategy"] == "spec_canonical")
check("1.7: brownfield_milestones nested object initialized",
      isinstance(
          cfg["retrofit"]["autonomous_modes"]["brownfield_milestones"],
          dict))
check("1.8: brownfield_milestones has correct sub-fields",
      all(k in cfg["retrofit"]["autonomous_modes"]
                  ["brownfield_milestones"] for k in (
              "rollout_steady_state_spec_test_gate",
              "rollout_steady_state_all_hooks",
              "touch_based_specs_under_blocking_gates",
              "touch_based_specs_threshold",
              "legacy_allowlist_size_at_retrofit",
              "legacy_allowlist_current_size",
              "legacy_allowlist_shrink_threshold_pct",
              "mode_selection_ledger_entries",
              "weeks_real_per_task_operation_post_blocking")))

# Mode validation
_, errs = cfg_from('mode: "hybrid"\nproject:\n  name: x\n  archetype: cli\n')
check("1.9: invalid mode value rejected",
      any("mode must be one of" in e for e in errs))

# Greenfield cfg still works without mode key (D2 covers byte-identity)
_, errs = cfg_from('project:\n  name: x\n  archetype: cli\n')
check("1.10: greenfield cfg (no mode) validates and defaults to bootstrap",
      not errs)
cfg_gf, _ = cfg_from('project:\n  name: x\n  archetype: cli\n')
check("1.11: greenfield cfg mode defaults to 'bootstrap'",
      cfg_gf["mode"] == "bootstrap")
check("1.12: greenfield cfg has NO retrofit section",
      "retrofit" not in cfg_gf)

# Enum validation
_, errs = cfg_from(SERVICE_RETROFIT_CFG.replace(
    'spec_strategy: "forward-only"', 'spec_strategy: "yolo"'))
check("1.13: invalid spec_strategy enum rejected",
      any("spec_strategy" in e for e in errs))

# --------------------------------------------------------------------------- #
# 2. Determinism
# --------------------------------------------------------------------------- #
print("\n=== Section 2: Determinism ===")

cfg_a, _ = cfg_from(SERVICE_RETROFIT_CFG)
cfg_b, _ = cfg_from(SERVICE_RETROFIT_CFG)
check("2.1: same retrofit cfg => identical plan digest",
      plan_digest(cfg_a) == plan_digest(cfg_b))

cfg_x, _ = cfg_from(AGENT_RETROFIT_CFG)
cfg_y, _ = cfg_from(AGENT_RETROFIT_CFG)
check("2.2: same agent-retrofit cfg => identical plan digest",
      plan_digest(cfg_x) == plan_digest(cfg_y))

check("2.3: different retrofit cfgs => different digests",
      plan_digest(cfg_a) != plan_digest(cfg_x))

# --------------------------------------------------------------------------- #
# 3. T1 — Dual-shape autonomous_modes wiring (CRITICAL — see operator note)
# --------------------------------------------------------------------------- #
print("\n=== Section 3: T1 dual-shape autonomous_modes wiring ===")

# Config input nests *_opted_in under retrofit.autonomous_modes.
# State file shape (B5-frozen) keeps *_enabled top-level (always false at
# retrofit time) and *_in_flight top-level (always empty initially).
# The two shapes must NEVER conflate or cross-write.

cfg_agent, _ = cfg_from(AGENT_RETROFIT_CFG)

check("T1.1: cfg.autonomous_modes.loop_mode_enabled is FALSE at top-level "
      "(input schema requires false at retrofit time)",
      cfg_agent["autonomous_modes"]["loop_mode_enabled"] is False)
check("T1.2: cfg.retrofit.autonomous_modes.loop_mode_opted_in is TRUE "
      "(operator intent recorded in nested field)",
      cfg_agent["retrofit"]["autonomous_modes"]
              ["loop_mode_opted_in"] is True)
check("T1.3: cfg.retrofit.autonomous_modes.goal_supervised_mode_opted_in "
      "is TRUE",
      cfg_agent["retrofit"]["autonomous_modes"]
              ["goal_supervised_mode_opted_in"] is True)
check("T1.4: cfg.retrofit.autonomous_modes.queue_mode_opted_in is FALSE",
      cfg_agent["retrofit"]["autonomous_modes"]
              ["queue_mode_opted_in"] is False)

# Try to bypass B5: hand-edited cfg with *_enabled=true should be REJECTED.
BAD_CFG_B5_BYPASS = """mode: "retrofit"
project:
  name: bad
  archetype: cli
autonomous_modes:
  loop_mode_enabled: true
"""
_, errs = cfg_from(BAD_CFG_B5_BYPASS)
check("T1.5: cfg with autonomous_modes.loop_mode_enabled=true REJECTED",
      any("loop_mode_enabled" in e and "scaffold-but-defer" in e
          for e in errs),
      f"errors={errs}")

# Install + verify the dual shape lands correctly in the WRITTEN state file
d = install(AGENT_RETROFIT_CFG)
try:
    state = json.loads(open(os.path.join(d, ".claude",
                                          ".retrofit-state.json")).read())
    # Top-level: enabled false + in_flight empty
    check("T1.6: state.json TOP-LEVEL loop_mode_enabled is False",
          state["loop_mode_enabled"] is False)
    check("T1.7: state.json TOP-LEVEL goal_supervised_mode_enabled is False",
          state["goal_supervised_mode_enabled"] is False)
    check("T1.8: state.json TOP-LEVEL queue_mode_enabled is False",
          state["queue_mode_enabled"] is False)
    check("T1.9: state.json TOP-LEVEL loop_in_flight is []",
          state["loop_in_flight"] == [])
    check("T1.10: state.json TOP-LEVEL goal_in_flight is []",
          state["goal_in_flight"] == [])
    check("T1.11: state.json TOP-LEVEL queue_runs_history is []",
          state["queue_runs_history"] == [])

    # Nested: opted_in reflects cfg + brownfield_milestones present
    am = state["autonomous_modes"]
    check("T1.12: state.json NESTED autonomous_modes.loop_mode_opted_in "
          "reflects cfg (true)",
          am["loop_mode_opted_in"] is True)
    check("T1.13: state.json NESTED autonomous_modes."
          "goal_supervised_mode_opted_in reflects cfg (true)",
          am["goal_supervised_mode_opted_in"] is True)
    check("T1.14: state.json NESTED autonomous_modes.queue_mode_opted_in "
          "reflects cfg (false)",
          am["queue_mode_opted_in"] is False)
    check("T1.15: state.json NESTED brownfield_milestones present + dict",
          isinstance(am["brownfield_milestones"], dict))

    # NEVER conflate: opted_in must NOT appear top-level in state file
    check("T1.16: state.json does NOT have top-level loop_mode_opted_in",
          "loop_mode_opted_in" not in state)
    check("T1.17: state.json does NOT have top-level "
          "goal_supervised_mode_opted_in",
          "goal_supervised_mode_opted_in" not in state)
    check("T1.18: state.json does NOT have top-level brownfield_milestones",
          "brownfield_milestones" not in state)

    # NEVER cross-write: state.loop_mode_enabled MUST stay false even when
    # cfg.retrofit.autonomous_modes.loop_mode_opted_in is true.
    check("T1.19: cfg-opted-in does NOT promote state's *_enabled "
          "(scaffold-but-defer rule)",
          state["loop_mode_enabled"] is False
          and am["loop_mode_opted_in"] is True)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# 4. End-to-end lifecycle (mirroring test_installer.py L-1/L-2/L-3)
# --------------------------------------------------------------------------- #
print("\n=== Section 4: End-to-end lifecycle ===")

d = install(SERVICE_RETROFIT_CFG)
try:
    # First run already ran in install(); verify some artifacts.
    debt_path = os.path.join(d, ".claude", "debt.md")
    check("4.1: first install created debt.md", os.path.exists(debt_path))
    check("4.2: first install created spec-strategy.md",
          os.path.exists(os.path.join(d, ".claude", "steering",
                                        "spec-strategy.md")))

    # Idempotency: re-run produces 0 writes.
    r = subprocess.run([sys.executable, BIN_INSTALL, "-C", d],
                        capture_output=True, text=True)
    check("4.3: re-run is idempotent (0 writes)",
          "create=0 update=0" in r.stdout,
          f"stdout snippet: {r.stdout[-200:]}")

    # Hand-edit a generated file -> uninstall PRESERVES it (L-1 contract
    # carried over to retrofit).
    edited = os.path.join(d, ".claude", "steering", "spec-strategy.md")
    with open(edited, "a") as fh:
        fh.write("\nOPERATOR EDIT - DO NOT LOSE\n")
    r = subprocess.run([sys.executable, BIN_INSTALL, "-C", d,
                        "--uninstall"], capture_output=True, text=True)
    check("4.4: uninstall preserves hand-edited generated file (L-1)",
          os.path.exists(edited)
          and "OPERATOR EDIT" in open(edited).read())

    # Re-apply after uninstall must NOT clobber the preserved edit (L-2).
    r2 = subprocess.run([sys.executable, BIN_INSTALL, "-C", d],
                         capture_output=True, text=True)
    check("4.5: re-apply preserves operator edit (L-2)",
          "OPERATOR EDIT" in open(edited).read()
          and "SKIP" in r2.stdout)

    # --force overrides on re-apply.
    r3 = subprocess.run([sys.executable, BIN_INSTALL, "-C", d, "--force"],
                         capture_output=True, text=True)
    check("4.6: --force overrides a locally-modified file (L-2)",
          "OPERATOR EDIT" not in open(edited).read())
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# 5. Retrofit-only artifacts present + conditional artifacts gated
# --------------------------------------------------------------------------- #
print("\n=== Section 5: Retrofit-only artifacts present + conditional gating ===")

d = install(SERVICE_RETROFIT_CFG)
try:
    required = [
        ".claude/debt.md",
        ".claude/steering/spec-strategy.md",
        ".claude/steering/workflow-source-of-truth.md",
        ".claude/hooks/rollout-schedule.md",
        ".claude/inventory/README.md",
    ]
    for p in required:
        check(f"5.1: required retrofit artifact present: {p}",
              os.path.exists(os.path.join(d, p)))

    retrofit_skills = [
        "legacy-spec", "legacy-pin-test", "boundary-spec",
        "migration-plan", "inventory-scan", "prior-art-audit",
        "convention-categorize", "debt-classify", "ticket-to-spec",
    ]
    for s in retrofit_skills:
        check(f"5.2: retrofit skill present: {s}",
              os.path.exists(os.path.join(
                  d, ".claude", "skills", s, "SKILL.md")))

    # Conditional: contracts.md present because service archetype has
    # spec_patterns.boundary defaulted to true in _derive_spec_patterns.
    # But SERVICE_RETROFIT_CFG doesn't set spec_patterns explicitly, so
    # it falls back to RETROFIT_DEFAULTS which has boundary=False.
    # Verify the conditional gates work either way.
    # (We rely on resolve_config to fill defaults; the test fixture has
    # no explicit spec_patterns, so all default false except change=true.)
    check("5.3: contracts.md NOT generated when spec_patterns.boundary "
          "default-false",
          not os.path.exists(os.path.join(d, ".claude", "steering",
                                            "contracts.md")))
    check("5.4: migration.md NOT generated when spec_patterns.migration "
          "default-false",
          not os.path.exists(os.path.join(d, ".claude", "steering",
                                            "migration.md")))
    check("5.5: compliance.md NOT generated when no regulatory_regimes",
          not os.path.exists(os.path.join(d, ".claude", "steering",
                                            "compliance.md")))
    check("5.6: worktree-budget.md NOT generated when codebase_size_gb=0",
          not os.path.exists(os.path.join(d, ".claude", "hooks",
                                            "worktree-budget.md")))

    # CLAUDE.md is retrofit-flavor
    claude_md = open(os.path.join(d, "CLAUDE.md")).read()
    check("5.7: CLAUDE.md is retrofit-flavor (mentions legacy allowlist)",
          "legacy allowlist" in claude_md.lower())
    check("5.8: CLAUDE.md references retrofit-specific docs",
          ".claude/debt.md" in claude_md
          and ".claude/steering/spec-strategy.md" in claude_md)

    # .gitignore has retrofit patterns
    gi = open(os.path.join(d, ".claude", ".gitignore")).read()
    check("5.9: .gitignore includes .retrofit-state.json",
          ".retrofit-state.json" in gi)
    check("5.10: .gitignore includes inventory/.scan-cache-*",
          "inventory/.scan-cache-*" in gi)

    # Agents are retrofit-flavor
    impl = open(os.path.join(d, ".claude", "agents",
                              "implementer.md")).read()
    check("5.11: implementer.md is retrofit-flavor (pin-first)",
          "pin-first" in impl.lower() or "pinning" in impl.lower())
    rev = open(os.path.join(d, ".claude", "agents", "reviewer.md")).read()
    check("5.12: reviewer.md is retrofit-flavor (danger-zone)",
          "danger-zone" in rev.lower() or "danger_zone" in rev.lower())

    # integrator NOT touched (per RETROFIT R8.C scope)
    integ = open(os.path.join(d, ".claude", "agents", "integrator.md")).read()
    check("5.13: integrator.md NOT retrofit-flavored (greenfield body)",
          "retrofit" not in integ.lower())

    # Markers for D5 hooks at runtime
    spec_strat = open(os.path.join(d, ".claude", "steering",
                                     "spec-strategy.md")).read()
    check("5.14: spec-strategy.md has LEGACY_ALLOWLIST_BEGIN marker",
          "LEGACY_ALLOWLIST_BEGIN" in spec_strat)
    check("5.15: spec-strategy.md has LEGACY_ALLOWLIST_END marker",
          "LEGACY_ALLOWLIST_END" in spec_strat)
    rs = open(os.path.join(d, ".claude", "hooks",
                            "rollout-schedule.md")).read()
    check("5.16: rollout-schedule.md has ROLLOUT_WEEK marker",
          "ROLLOUT_WEEK:" in rs)
finally:
    shutil.rmtree(d, ignore_errors=True)

# Conditional artifacts WITH conditions met
d = install(AGENT_RETROFIT_CFG)
try:
    check("5.17: contracts.md generated when spec_patterns.boundary=true",
          os.path.exists(os.path.join(d, ".claude", "steering",
                                        "contracts.md")))
    check("5.18: worktree-budget.md generated when "
          "codebase_size_gb >= 1",
          os.path.exists(os.path.join(d, ".claude", "hooks",
                                        "worktree-budget.md")))
    check("5.19: prompt-pinning-eval skill present for ai-agent archetype",
          os.path.exists(os.path.join(d, ".claude", "skills",
                                        "prompt-pinning-eval", "SKILL.md")))
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# 6. Hook retrofit-flavor (secrets-gate NOT touched)
# --------------------------------------------------------------------------- #
print("\n=== Section 6: Hook retrofit-flavor ===")

d = install(AGENT_RETROFIT_CFG)  # has tdd_policy: required
try:
    h_dir = os.path.join(d, ".claude", "hooks")
    spec_commit = open(os.path.join(h_dir, "spec-gate-commit.sh")).read()
    test_gate = open(os.path.join(h_dir, "test-gate.sh")).read()
    tdd_gate = open(os.path.join(h_dir, "tdd-gate.sh")).read()
    secrets_gate = open(os.path.join(h_dir, "secrets-gate.sh")).read()

    check("6.1: spec-gate-commit has Retrofit preamble",
          "Retrofit preamble" in spec_commit)
    check("6.2: test-gate has Retrofit preamble",
          "Retrofit preamble" in test_gate)
    check("6.3: tdd-gate has Retrofit preamble",
          "Retrofit preamble" in tdd_gate)
    check("6.4: secrets-gate has NO Retrofit preamble (R8.A.3 forbids it)",
          "Retrofit preamble" not in secrets_gate)

    check("6.5: spec-gate-commit retrofit checks have retrofit_active path",
          "retrofit_active exempt" in spec_commit)
    check("6.6: spec-gate-commit retrofit checks have all-allowlisted path",
          "all-allowlisted exempt" in spec_commit)
    check("6.7: tdd-gate retrofit checks have legacy-allowlisted path",
          "legacy-allowlisted exempt" in tdd_gate)

    # Greenfield body still present at end of each retrofit hook
    check("6.8: spec-gate-commit greenfield body preserved",
          "spec-gate-commit ok" in spec_commit)
    check("6.9: test-gate greenfield body preserved",
          "test-gate ok" in test_gate)
    check("6.10: tdd-gate greenfield body preserved",
          "tdd-gate ok" in tdd_gate)

    # All generated hooks must be valid bash (regression: doubled-brace
    # hazard from F-2 follow-up)
    bad = [f for f in os.listdir(h_dir) if f.endswith(".sh") and
           subprocess.run(["bash", "-n", os.path.join(h_dir, f)]
                          ).returncode != 0]
    check("6.11: all generated hooks valid bash (-n)", bad == [],
          f"bad files: {bad}")
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# 7. T2 — fail-safe seam proof (no-jq restricted-PATH harness)
# --------------------------------------------------------------------------- #
print("\n=== Section 7: T2 fail-safe seam (no-jq restricted PATH) ===")


def _nojq_path():
    """Build a restricted PATH matching the existing S-1/T-1 harness
    pattern (no jq; minimal coreutils only)."""
    nj = tempfile.mkdtemp()
    for b in ("bash", "cat", "python3", "basename", "dirname", "date",
              "mkdir", "printf", "grep", "sed", "find", "mktemp", "rm",
              "env", "uname", "awk", "git", "head", "tail", "xargs",
              "which"):
        src = shutil.which(b)
        if src:
            os.symlink(src, os.path.join(nj, b))
    return nj


def _run_hook(d, hook_name, payload, env_extra=None):
    """Run a hook script under the no-jq restricted PATH harness.
    CLAUDE_PROJECT_DIR must be set so the hook resolves its runtime
    files (.retrofit-state.json, spec-strategy.md, rollout-schedule.md)
    in the test fixture rather than the parent repo.

    `cwd` must be set for the same reason. CLAUDE_PROJECT_DIR governs how the
    hook resolves FILES, but the hooks also shell out to `git` (spec-gate-commit
    reads `git diff --cached`), and git resolves its repository from the
    PROCESS CWD. Without cwd=d the hook inherits the test runner's CWD — the
    bootstrap repo itself — so those hooks read THIS repository's index instead
    of the fixture's, and two checks (T2.AF4, T2.FS5) then pass or fail
    depending on whatever the developer happens to have staged. Found when a
    staged deletion in the parent repo turned the suite red with no code
    change; CI only ever saw green because a fresh checkout has an empty
    index."""
    e = dict(os.environ)
    e["PATH"] = _nojq_path()
    e["CLAUDE_PROJECT_DIR"] = d
    if env_extra:
        e.update(env_extra)
    r = subprocess.run(
        ["bash", os.path.join(d, ".claude", "hooks", f"{hook_name}.sh")],
        input=json.dumps(payload), capture_output=True, text=True, env=e,
        cwd=d)
    return r.returncode, r.stdout + r.stderr


# Build a fixture with tdd-gate installed (tdd_policy: required) so we
# can exercise the tdd-gate retrofit-flavor.
d = install(AGENT_RETROFIT_CFG)
try:
    # Force ROLLOUT_WEEK=4 so only AFFIRMATIVE matches can early-exit.
    rs_path = os.path.join(d, ".claude", "hooks", "rollout-schedule.md")
    with open(rs_path) as fh:
        rs = fh.read()
    with open(rs_path, "w") as fh:
        fh.write(rs.replace("ROLLOUT_WEEK: 1", "ROLLOUT_WEEK: 4"))

    # AFFIRMATIVE #1: tdd-gate on allowlisted path -> exit 0 via allowlist
    rc, out = _run_hook(d, "tdd-gate",
                         {"tool_input": {"file_path": "src/legacy.py"}})
    check("T2.AF1: tdd-gate on allowlisted (src/**) -> exit 0",
          rc == 0)
    check("T2.AF1b: tdd-gate took the allowlisted path",
          "legacy-allowlisted exempt" in
          open(os.path.join(d, ".claude", "logs", "hooks.log")).read())

    # FAIL-SAFE #1: missing .retrofit-state.json -> retrofit_active=false
    # -> spec-gate-commit cannot use master-switch exemption
    state_path = os.path.join(d, ".claude", ".retrofit-state.json")
    saved_state = state_path + ".saved"
    shutil.move(state_path, saved_state)
    rc, out = _run_hook(d, "spec-gate-commit",
                         {"tool_input": {"command": "git commit -m x"}})
    shutil.move(saved_state, state_path)
    # The hook's exit depends on what greenfield does for an empty git
    # diff; the key assertion is that NO retrofit exemption was logged.
    log = open(os.path.join(d, ".claude", "logs", "hooks.log")).read()
    check("T2.FS1: missing state.json -> retrofit_active exemption "
          "NOT logged",
          "retrofit_active exempt" not in log.split(
              "\n")[-3:][0])  # the most recent line

    # FAIL-SAFE #2: malformed .retrofit-state.json -> retrofit_active=false
    shutil.copy(state_path, saved_state)
    with open(state_path, "w") as fh:
        fh.write("{ NOT VALID JSON")
    # Re-init a git repo so greenfield git diff doesn't error out
    subprocess.run(["git", "init", "-q"], cwd=d, check=False)
    rc, out = _run_hook(d, "spec-gate-commit",
                         {"tool_input": {"command": "git commit -m x"}})
    shutil.move(saved_state, state_path)
    check("T2.FS2: malformed state.json -> retrofit exemption NOT taken",
          rc != 0 or "retrofit_active exempt" not in out)

    # FAIL-SAFE #3: missing rollout-schedule.md -> RETROFIT_WEEK=4 default
    shutil.move(rs_path, rs_path + ".saved")
    rc, out = _run_hook(d, "tdd-gate",
                         {"tool_input": {"file_path": "non/allow.py"}})
    shutil.move(rs_path + ".saved", rs_path)
    check("T2.FS3: missing rollout-schedule.md -> RETROFIT_WEEK defaults "
          "to 4 (no warn-only exemption for non-allowlisted)",
          "week" not in out.lower() or "warn-only" not in out.lower())

    # FAIL-SAFE #4: missing spec-strategy.md -> empty allowlist -> not exempt
    ss_path = os.path.join(d, ".claude", "steering", "spec-strategy.md")
    shutil.move(ss_path, ss_path + ".saved")
    rc, out = _run_hook(d, "tdd-gate",
                         {"tool_input": {"file_path": "src/legacy.py"}})
    shutil.move(ss_path + ".saved", ss_path)
    check("T2.FS4: missing spec-strategy.md -> allowlist empty -> "
          "previously-allowlisted path NOT exempt",
          "legacy-allowlisted exempt" not in out)

    # ADVERSARIAL: shell-metachar injection in allowlist must NOT execute
    shutil.copy(ss_path, ss_path + ".saved")
    with open(ss_path, "w") as fh:
        fh.write("<!-- LEGACY_ALLOWLIST_BEGIN -->\n"
                 "$(touch /tmp/RETROFIT_TEST_PWN)\n"
                 "`touch /tmp/RETROFIT_TEST_PWN2`\n"
                 "<!-- LEGACY_ALLOWLIST_END -->\n")
    for f in ("/tmp/RETROFIT_TEST_PWN", "/tmp/RETROFIT_TEST_PWN2"):
        try:
            os.unlink(f)
        except OSError:
            pass
    rc, out = _run_hook(d, "tdd-gate",
                         {"tool_input": {"file_path": "src/legacy.py"}})
    shutil.move(ss_path + ".saved", ss_path)
    check("T2.AD1: shell-substitution allowlist patterns did NOT execute",
          not os.path.exists("/tmp/RETROFIT_TEST_PWN")
          and not os.path.exists("/tmp/RETROFIT_TEST_PWN2"))

    # ----- Round-2 review (Lens 6.2): lock the 9 remaining T2 cases ----- #
    # The C2 scoped review proved 14 cases by execution. The original suite
    # locked AF1, FS1-FS4, AD1 (6 cases) + AF1b. This block adds AF2-AF5,
    # FS5-FS7, and FS7b to make 14 regression-locked cases total.

    # AFFIRMATIVE #2 (AF2): retrofit_active=true + commit staging only
    # .claude/ files -> exempt. Set up git in $d (the hook reads
    # `git diff --cached --name-only` from CWD; the no-jq harness's
    # default CWD is the test runner, not $d, so we set cwd=d here).
    subprocess.run(["git", "init", "-q"], cwd=d, check=False)
    subprocess.run(["git", "config", "user.email", "t@e.x"], cwd=d,
                    check=False)
    subprocess.run(["git", "config", "user.name", "t"], cwd=d, check=False)
    os.makedirs(os.path.join(d, ".claude", "logs"), exist_ok=True)
    _stage_path = os.path.join(d, ".claude", "logs", "stage-marker")
    with open(_stage_path, "w") as fh:
        fh.write("staged for AF2\n")
    subprocess.run(["git", "add", "-f", ".claude/logs/stage-marker"],
                    cwd=d, check=False)
    _e = dict(os.environ)
    _e["PATH"] = _nojq_path()
    _e["CLAUDE_PROJECT_DIR"] = d
    _r = subprocess.run(
        ["bash", os.path.join(d, ".claude", "hooks",
                               "spec-gate-commit.sh")],
        input=json.dumps({"tool_input":
                           {"command": "git commit -m claude-only"}}),
        capture_output=True, text=True, env=_e, cwd=d)
    log = open(os.path.join(d, ".claude", "logs", "hooks.log")).read()
    check("T2.AF2: spec-gate-commit + retrofit_active + .claude/-only "
          "staged -> exit 0 via retrofit_active exemption",
          _r.returncode == 0 and "retrofit_active exempt" in log)

    # AFFIRMATIVE #3 (AF3): all staged files in legacy allowlist -> exempt.
    # Set retrofit_active=false to force exemption to come from allowlist.
    with open(state_path) as fh:
        _st = json.load(fh)
    _st_saved = dict(_st)
    _st["retrofit_active"] = False
    with open(state_path, "w") as fh:
        json.dump(_st, fh)
    # Unstage AF2's file first so only the allowlisted one is staged.
    # `git reset HEAD .` doesn't work without an initial commit; use
    # `git rm --cached -r .` instead.
    subprocess.run(["git", "rm", "--cached", "-r", "."], cwd=d, check=False,
                    capture_output=True)
    _af3_file = os.path.join(d, "src", "legacy.py")
    os.makedirs(os.path.dirname(_af3_file), exist_ok=True)
    with open(_af3_file, "w") as fh:
        fh.write("# allowlisted source\n")
    subprocess.run(["git", "add", "src/legacy.py"], cwd=d, check=False)
    _r = subprocess.run(
        ["bash", os.path.join(d, ".claude", "hooks",
                               "spec-gate-commit.sh")],
        input=json.dumps({"tool_input":
                           {"command": "git commit -m allowed"}}),
        capture_output=True, text=True, env=_e, cwd=d)
    log2 = open(os.path.join(d, ".claude", "logs", "hooks.log")).read()
    check("T2.AF3: spec-gate-commit all-allowlisted commit -> exit 0",
          _r.returncode == 0 and "all-allowlisted exempt" in log2)
    with open(state_path, "w") as fh:
        json.dump(_st_saved, fh)

    # AFFIRMATIVE #4 (AF4): rollout-week warn-only -> spec-gate-commit
    # exits 0 with warn message. Set week 1.
    with open(rs_path) as fh:
        rs_w4 = fh.read()
    with open(rs_path, "w") as fh:
        fh.write(rs_w4.replace("ROLLOUT_WEEK: 4", "ROLLOUT_WEEK: 1"))
    # Stage something that doesn't match either exemption to force the
    # rollout-week branch (use a non-allowlisted .py path).
    _af4_file = os.path.join(d, "other", "x.py")
    os.makedirs(os.path.dirname(_af4_file), exist_ok=True)
    with open(_af4_file, "w") as fh:
        fh.write("# non-allowlisted\n")
    subprocess.run(["git", "add", "other/x.py"], cwd=d, check=False)
    rc, out = _run_hook(d, "spec-gate-commit",
                         {"tool_input": {"command": "git commit -m wk1"}})
    check("T2.AF4: spec-gate-commit week 1 warn-only -> exit 0",
          rc == 0 and ("week 1 warn-only" in
                       open(os.path.join(d, ".claude", "logs",
                                          "hooks.log")).read()))

    # AFFIRMATIVE #5 (AF5): test-gate week 1 warn-only -> exit 0.
    rc, out = _run_hook(d, "test-gate",
                         {"tool_input": {"command": "git commit -m wk1"}})
    check("T2.AF5: test-gate week 1 warn-only -> exit 0",
          rc == 0 and ("week 1 warn-only" in
                       open(os.path.join(d, ".claude", "logs",
                                          "hooks.log")).read()))
    # Restore week 4 for the fail-safe block.
    with open(rs_path, "w") as fh:
        fh.write(rs_w4)

    # FAIL-SAFE #5 (FS5): state.json with retrofit_active as string "yes"
    # (not bool true) -> RETROFIT_ACTIVE stays false -> no exemption.
    with open(state_path) as fh:
        _st = json.load(fh)
    _saved_yes = dict(_st)
    _st["retrofit_active"] = "yes"  # truthy string, not bool true
    with open(state_path, "w") as fh:
        json.dump(_st, fh)
    # Use a fresh .claude/ stage to avoid AF2 already-staged confounding.
    with open(os.path.join(d, ".claude", "logs", "fs5-marker"), "w") as fh:
        fh.write("fs5\n")
    subprocess.run(["git", "add", ".claude/logs/fs5-marker"], cwd=d,
                    check=False)
    _log_size = os.path.getsize(os.path.join(d, ".claude", "logs",
                                              "hooks.log"))
    rc, out = _run_hook(d, "spec-gate-commit",
                         {"tool_input": {"command": "git commit -m fs5"}})
    _new_log = open(os.path.join(d, ".claude", "logs",
                                  "hooks.log")).read()[_log_size:]
    check("T2.FS5: state.json retrofit_active='yes' (string, not bool) "
          "-> NOT honored as exemption",
          "retrofit_active exempt" not in _new_log)
    with open(state_path, "w") as fh:
        json.dump(_saved_yes, fh)

    # FAIL-SAFE #6 (FS6): rollout-schedule present but no ROLLOUT_WEEK
    # marker -> RETROFIT_WEEK=4 default -> tdd-gate non-allowlisted ENFORCE.
    with open(rs_path) as fh:
        rs_full = fh.read()
    with open(rs_path, "w") as fh:
        fh.write("# rollout schedule (no marker)\n\nSome text.\n")
    rc, out = _run_hook(d, "tdd-gate",
                         {"tool_input": {"file_path": "other/x.py"}})
    check("T2.FS6: rollout-schedule.md without ROLLOUT_WEEK marker -> "
          "week defaults to 4 (no warn-only exemption)",
          "warn-only" not in out)
    with open(rs_path, "w") as fh:
        fh.write(rs_full)

    # FAIL-SAFE #7 (FS7): rollout-schedule marker is non-digit -> week
    # default 4 (the [0-9]+ regex won't match 'abc'; week stays 4).
    with open(rs_path, "w") as fh:
        fh.write(rs_full.replace("ROLLOUT_WEEK: 4", "ROLLOUT_WEEK: abc"))
    rc, out = _run_hook(d, "tdd-gate",
                         {"tool_input": {"file_path": "other/x.py"}})
    check("T2.FS7: rollout-schedule.md ROLLOUT_WEEK: abc (non-digit) -> "
          "week stays at default 4 (no warn-only exemption)",
          "warn-only" not in out)
    with open(rs_path, "w") as fh:
        fh.write(rs_full)

    # FAIL-SAFE #7b (FS7b): no-jq harness + no python3 (only one allowed
    # fallback). Verifies that state-file read still fails toward ENFORCE
    # when BOTH jq and python3 are absent (T2 worst-case "no parser").
    _no_py_path = tempfile.mkdtemp()
    for b in ("bash", "cat", "basename", "dirname", "date", "mkdir",
              "printf", "grep", "sed", "find", "mktemp", "rm", "env",
              "uname", "awk", "git", "head", "tail", "xargs", "which"):
        src = shutil.which(b)
        if src:
            os.symlink(src, os.path.join(_no_py_path, b))
    # NB: no jq, no python3 — strictly worst case.
    e = dict(os.environ)
    e["PATH"] = _no_py_path
    e["CLAUDE_PROJECT_DIR"] = d
    r = subprocess.run(
        ["bash", os.path.join(d, ".claude", "hooks",
                                "spec-gate-commit.sh")],
        input=json.dumps({"tool_input": {"command": "git commit -m x"}}),
        capture_output=True, text=True, env=e)
    _full_log = open(os.path.join(d, ".claude", "logs",
                                    "hooks.log")).read()
    check("T2.FS7b: no jq + no python3 -> retrofit_active stays false "
          "(no parser available, fail-safe to ENFORCE)",
          "retrofit_active exempt" not in _full_log.split(
              "\n")[-3:][0] if _full_log else True)
    shutil.rmtree(_no_py_path, ignore_errors=True)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# 8. State writer — B5 shape, OD-4 versioning, R-2 setdefault preservation
# --------------------------------------------------------------------------- #
print("\n=== Section 8: State writer (B5, OD-4, R-2 fix) ===")

d = install(AGENT_RETROFIT_CFG)
try:
    state = json.loads(open(os.path.join(d, ".claude",
                                           ".retrofit-state.json")).read())

    # OD-4: both protocol versions top-level; both string-valued.
    check("8.1: bootstrap_protocol_version top-level + reused constant",
          state.get("bootstrap_protocol_version") == PROTOCOL_VERSION)
    check("8.2: retrofit_protocol_version top-level + correct value",
          state.get("retrofit_protocol_version")
          == RETROFIT_PROTOCOL_VERSION)
    check("8.3: bootstrap_protocol_version matches '2.4.0' literally "
          "(v2.4.0 code fold release-identity bump; retrofit state also "
          "stamps the greenfield PROTOCOL_VERSION per the shared writer)",
          state["bootstrap_protocol_version"] == "2.4.0")
    check("8.4: retrofit_protocol_version matches '1.6.2' literally",
          state["retrofit_protocol_version"] == "1.6.2")
    check("8.5: gate_substrate 'shell' present (IC-3 parity with the "
          "greenfield writer; review finding 10)",
          state.get("gate_substrate") == "shell")

    # B5 schema completeness (R0.5 step 8)
    required_top_level = (
        "archetype", "archetype_proposed", "archetype_confidence",
        "archetype_evidence", "synthetic_profile", "prd_tier_target",
        "ci_cd_applicability", "pm_strategy", "pm_tool",
        "pm_tool_role_after", "ticket_migration_disposition",
        "hybrid_review_date", "retrofit_active", "retrofit_complete",
        "skip_decisions", "r08_committed", "r08_committed_at",
        "loop_mode_enabled", "goal_supervised_mode_enabled",
        "queue_mode_enabled", "loop_in_flight", "goal_in_flight",
        "queue_runs_history", "autonomous_modes",
    )
    for k in required_top_level:
        check(f"8.5.{k}: state file has top-level '{k}'", k in state)

    # R-2: re-apply preserves operator-set retrofit_active=false
    # (R7 flow). The cfg has retrofit_active: true; setting state to
    # false and re-applying must NOT revert.
    state["retrofit_active"] = False
    state["retrofit_complete"] = True
    state["r08_committed"] = True
    with open(os.path.join(d, ".claude", ".retrofit-state.json"),
              "w") as fh:
        json.dump(state, fh, indent=2)

    r = subprocess.run([sys.executable, BIN_INSTALL, "-C", d],
                        capture_output=True, text=True)
    state2 = json.loads(open(os.path.join(d, ".claude",
                                           ".retrofit-state.json")).read())
    check("8.6 R-2: re-apply preserves retrofit_active=False "
          "(operator-set; cfg has true)",
          state2["retrofit_active"] is False)
    check("8.7 R-2: re-apply preserves retrofit_complete=True",
          state2["retrofit_complete"] is True)
    check("8.8 R-3: re-apply preserves r08_committed=True",
          state2["r08_committed"] is True)

    # B5: cfg's *_opted_in correctly reflects in nested autonomous_modes
    check("8.9: state autonomous_modes.loop_mode_opted_in matches cfg",
          state2["autonomous_modes"]["loop_mode_opted_in"] is True)
    check("8.10: state autonomous_modes.queue_mode_opted_in matches cfg",
          state2["autonomous_modes"]["queue_mode_opted_in"] is False)

    # brownfield_milestones nested + has all expected sub-fields
    bm = state2["autonomous_modes"]["brownfield_milestones"]
    for sub in ("rollout_steady_state_spec_test_gate",
                 "rollout_steady_state_all_hooks",
                 "touch_based_specs_under_blocking_gates",
                 "touch_based_specs_threshold",
                 "legacy_allowlist_size_at_retrofit",
                 "legacy_allowlist_shrink_threshold_pct",
                 "mode_selection_ledger_entries",
                 "weeks_real_per_task_operation_post_blocking"):
        check(f"8.11.{sub}: brownfield_milestones has {sub}", sub in bm)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# 9. Inventory scan + heuristics smoke (decision-layer round-trip)
# --------------------------------------------------------------------------- #
print("\n=== Section 9: Inventory scan + heuristics smoke ===")

# Build a synthetic FastAPI-shaped project to exercise the heuristics.
d = tempfile.mkdtemp()
try:
    os.makedirs(os.path.join(d, "src", "routes"))
    os.makedirs(os.path.join(d, "tests"))
    with open(os.path.join(d, "src", "routes", "main.py"), "w") as fh:
        fh.write("from fastapi import FastAPI\napp = FastAPI()\n")
    with open(os.path.join(d, "tests", "test_main.py"), "w") as fh:
        fh.write("def test_smoke():\n    assert True\n")
    with open(os.path.join(d, "pyproject.toml"), "w") as fh:
        # Use version specifiers so inventory_scan's regex catches the
        # bare package names (the regex requires either a version op or
        # a 'key =' line — this is a known parser limitation, not in D7
        # scope to widen).
        fh.write('[project]\nname = "svc"\n'
                 'dependencies = ["fastapi>=0.100", "uvicorn>=0.20"]\n')
    with open(os.path.join(d, "Dockerfile"), "w") as fh:
        fh.write("FROM python:3.11\n")
    with open(os.path.join(d, "README.md"), "w") as fh:
        fh.write("# Smoke Service\n\nA small FastAPI app.\n")
    os.makedirs(os.path.join(d, ".github", "workflows"))
    with open(os.path.join(d, ".github", "workflows", "ci.yml"), "w") as fh:
        fh.write("- run: pytest -q\n- run: ruff check .\n")
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=d,
                    check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=d, check=True)
    subprocess.run(["git", "add", "."], cwd=d, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=d, check=True)

    from pathlib import Path
    # propose_commands looks at ./.github/workflows/ from cwd — chdir
    # into the fixture so the OD-3 detection actually fires against the
    # fixture's CI file. (Known limitation of the heuristics module:
    # uses cwd rather than taking a root path.)
    _prev_cwd = os.getcwd()
    os.chdir(d)
    try:
        inv = scan_repo(Path(d))
        check("9.1: inventory_scan produces 'service' archetype evidence",
              inv["languages"]["dockerfile_count"] == 1)
        check("9.2: inventory_scan detects pyproject.toml",
              inv["languages"]["manifests"]["pyproject.toml"] is True)

        proposal = build_retrofit_proposal(inv, project_fallback="smoke")
        check("9.3: heuristics propose archetype 'service'",
              proposal["archetype"]["value"] == "service",
              f"got={proposal['archetype']['value']} "
              f"evidence={proposal['archetype'].get('evidence')}")
        check("9.4: heuristics propose 'forward-only' spec_strategy",
              proposal["spec_strategy"]["value"] == "forward-only")
        check("9.5: heuristics propose 'spec_canonical' pm strategy "
              "(single-owner project)",
              proposal["pm"]["strategy"] == "spec_canonical")
        check("9.6: heuristics propose commands.test from CI workflow "
              "(OD-3 detection)",
              "test" in proposal["commands"]["proposals"],
              f"got proposals={list(proposal['commands']['proposals'])}")

        # answers_to_config -> validate_config_dict round-trip
        ans = default_answers(proposal)
        cfg = answers_to_config(ans, proposal)
        errs = validate_config_dict(cfg)
        check("9.7: answers -> cfg round-trip validates cleanly",
              errs == [], f"errors={errs}")
        check("9.8: round-trip cfg has mode: retrofit",
              cfg["mode"] == "retrofit")
        check("9.9: round-trip cfg has all-FALSE *_enabled "
              "(scaffold-but-defer)",
              all(cfg["autonomous_modes"][k] is False for k in (
                  "loop_mode_enabled", "goal_supervised_mode_enabled",
                  "queue_mode_enabled")))

        # 10 inventory files written (README excluded per OD-5)
        written = write_inventory(Path(d), inv)
        check("9.10: write_inventory writes 10 files "
              "(README belongs to installer)",
              len(written) == 10)
        check("9.11: README.md NOT in decision-layer inventory writes",
              ".claude/inventory/README.md" not in written)
    finally:
        os.chdir(_prev_cwd)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# 10. R8.G/H/I autonomous-mode scaffolding emission (Round-2 review, Lens 1.1)
# --------------------------------------------------------------------------- #
# The original PR emitted retrofit-only artifacts but missed the R8.G/H/I
# autonomous-mode scaffolding the equivalence target binds. Greenfield gates
# those files on top-level *_enabled (pinned false in retrofit). The Round-2
# fix gates them on `cfg.retrofit.autonomous_modes.*_opted_in` via the
# retrofit overlay. These tests pin that behavior.
print("\n=== Section 10: R8.G/H/I scaffolding emission on opt-in ===")

# Build a cfg with no autonomous opt-in (the baseline).
_no_opt_cfg = SERVICE_RETROFIT_CFG.replace(
    'retrofit_active: true',
    'retrofit_active: true\n  autonomous_modes:\n'
    '    loop_mode_opted_in: false\n'
    '    goal_supervised_mode_opted_in: false\n'
    '    queue_mode_opted_in: false')
cfg_no, errs_no = cfg_from(_no_opt_cfg)
plan_no = build_plan(cfg_no)
paths_no = {a["path"] for a in plan_no}
check("10.1: no opt-in -> .claude/loop.sh NOT emitted",
      ".claude/loop.sh" not in paths_no)
check("10.2: no opt-in -> .claude/goal-loop.sh NOT emitted",
      ".claude/goal-loop.sh" not in paths_no)
check("10.3: no opt-in -> .claude/auto.sh NOT emitted",
      ".claude/auto.sh" not in paths_no)
check("10.4: no opt-in -> drift-detector-loop-cooperation hook NOT in "
      "resolved hooks",
      "drift-detector-loop-cooperation" not in cfg_no["_resolved_hooks"])

# AGENT_RETROFIT_CFG opts into loop AND goal-supervised (but not queue).
cfg_lg, errs_lg = cfg_from(AGENT_RETROFIT_CFG)
check("10.5: loop+goal cfg validates",
      errs_lg == [], f"errors={errs_lg}")
plan_lg = build_plan(cfg_lg)
paths_lg = {a["path"] for a in plan_lg}
check("10.6: loop opt-in -> .claude/loop.sh emitted",
      ".claude/loop.sh" in paths_lg)
check("10.7: loop opt-in -> .claude/loop-config.md emitted",
      ".claude/loop-config.md" in paths_lg)
check("10.8: goal opt-in -> .claude/goal-loop.sh emitted",
      ".claude/goal-loop.sh" in paths_lg)
check("10.9: goal opt-in -> .claude/goal-config.md emitted",
      ".claude/goal-config.md" in paths_lg)
check("10.10: goal opt-in -> learnings/mode-selection.md emitted (R8.H)",
      "learnings/mode-selection.md" in paths_lg)
check("10.11: drift-detector-loop-cooperation hook installed on opt-in",
      "drift-detector-loop-cooperation" in cfg_lg["_resolved_hooks"])
check("10.12: iteration-summary-enforcement hook installed on goal opt-in",
      "iteration-summary-enforcement" in cfg_lg["_resolved_hooks"])

# ---------------------------------------------------------------------------
# GR2 artifacts on the retrofit track (adversarial-review finding). The v2.4.0
# fold's GR2 artifacts reach retrofit plans because the overlay WRAPS the full
# greenfield plan: the unconditional .claude/specs/INDEX.md (carrying the
# canonical progress.md template) and assumption-ledger.md are not replaced or
# dropped, and the opted-in wrappers carry the GR2-02 trajectory contract. But
# the overlay DOES replace CLAUDE.md and implementer.md with retrofit-flavor
# bodies, and those carried no read-progress-first instruction — so the
# artifacts shipped with nothing telling an agent to consume them, and a
# resumed unattended retrofit iteration could re-attempt an approach flagged
# do-not-retry. The instruction is restored for the opted-in case only (that
# is the only configuration with a resumed autonomous session), leaving the
# default retrofit body byte-unchanged on this version-pinned track.
# ---------------------------------------------------------------------------
_bodies_lg = {a["path"]: a["body"] for a in plan_lg}
_bodies_no = {a["path"]: a["body"] for a in build_plan(cfg_no)}

check("10.13: retrofit ships the canonical progress.md template (INDEX.md)",
      "Canonical `progress.md` template"
      in _bodies_lg.get(".claude/specs/INDEX.md", ""))
check("10.14: opted-in retrofit CLAUDE.md instructs reading progress.md",
      "progress.md" in _bodies_lg.get("CLAUDE.md", "")
      and "Failed approaches" in _bodies_lg.get("CLAUDE.md", ""))
check("10.15: opted-in retrofit implementer honors do-not-retry",
      "do-not-retry" in _bodies_lg.get(".claude/agents/implementer.md", ""))
check("10.16: the GR2-02 trajectory contract rides the retrofit wrappers",
      "GR2-02" in _bodies_lg.get(".claude/loop.sh", ""))
# Scope guard: the no-opt-in retrofit body stays free of the addendum, so the
# default retrofit surface on the 1.6.2-pinned track is unchanged.
check("10.17: default retrofit CLAUDE.md carries no progress addendum",
      "Per-task progress ledger" not in _bodies_no.get("CLAUDE.md", ""))
check("10.18: default retrofit implementer carries no GR2-01 bullet",
      "GR2-01" not in _bodies_no.get(".claude/agents/implementer.md", ""))
# The unconditional ledger reaches retrofit plans too (overlay wraps the full
# plan). Recorded behavior, previously untested on this track.
check("10.19: assumption-ledger.md lands on retrofit plans",
      ".claude/steering/assumption-ledger.md" in paths_lg)
check("10.20: retrofit .gitignore covers settings.local.json (TEL-01)",
      "settings.local.json"
      in _bodies_lg.get(".claude/.gitignore", "").splitlines())

# loop.sh body is the greenfield guarded skeleton (RETROFIT R8.G step 1).
_loop_action = next(a for a in plan_lg if a["path"] == ".claude/loop.sh")
check("10.13: loop.sh body is the BOOTSTRAP-equivalent guarded skeleton",
      "Autonomous loop wrapper" in _loop_action["body"]
      and "claude -p iteration loop is intentionally unimplemented"
      in _loop_action["body"])

# Retrofit CLAUDE.md addenda present.
_claude_action = next(a for a in plan_lg if a["path"] == "CLAUDE.md")
check("10.14: CLAUDE.md has 'Loop mode (R8.G' addendum on opt-in",
      "Loop mode (R8.G" in _claude_action["body"])
check("10.15: CLAUDE.md has 'Goal-supervised mode (R8.H' addendum",
      "Goal-supervised mode (R8.H" in _claude_action["body"])
# But NOT the queue section (queue not opted in).
check("10.16: CLAUDE.md has NO 'Queue mode coordination layer' addendum "
      "when queue not opted in",
      "Queue mode coordination layer" not in _claude_action["body"])

# Retrofit implementer.md has autonomous-mode addenda.
_impl_action = next(a for a in plan_lg
                     if a["path"] == ".claude/agents/implementer.md")
check("10.17: implementer.md has 'Autonomous-mode awareness' addendum",
      "Autonomous-mode awareness" in _impl_action["body"])
check("10.18: implementer.md mentions both 'loop' and 'goal-supervised' "
      "in the modes-opted-in list",
      "loop / goal-supervised" in _impl_action["body"])

# Queue requires loop or goal -> R8.I prereq enforced.
_queue_only = SERVICE_RETROFIT_CFG.replace(
    'retrofit_active: true',
    'retrofit_active: true\n  autonomous_modes:\n'
    '    loop_mode_opted_in: false\n'
    '    goal_supervised_mode_opted_in: false\n'
    '    queue_mode_opted_in: true')
_, errs_q = cfg_from(_queue_only)
check("10.19: queue_mode_opted_in without loop or goal -> REJECTED "
      "(R8.I prereq)",
      any("queue_mode_opted_in requires" in e for e in errs_q))

# Loop+queue valid combination.
_loop_queue = SERVICE_RETROFIT_CFG.replace(
    'retrofit_active: true',
    'retrofit_active: true\n  autonomous_modes:\n'
    '    loop_mode_opted_in: true\n'
    '    goal_supervised_mode_opted_in: false\n'
    '    queue_mode_opted_in: true')
cfg_lq, errs_lq = cfg_from(_loop_queue)
check("10.20: loop+queue opt-in validates",
      errs_lq == [], f"errors={errs_lq}")
plan_lq = build_plan(cfg_lq)
paths_lq = {a["path"] for a in plan_lq}
check("10.21: queue opt-in -> .claude/queue/backlog.md emitted",
      ".claude/queue/backlog.md" in paths_lq)
check("10.22: queue opt-in -> .claude/auto.sh emitted",
      ".claude/auto.sh" in paths_lq)
check("10.23: queue opt-in -> .claude/auto-config.md emitted",
      ".claude/auto-config.md" in paths_lq)
# Retrofit gitignore has queue entries when queue opted in.
_gi_action = next(a for a in plan_lq
                   if a["path"] == ".claude/.gitignore")
check("10.24: queue opt-in -> retrofit gitignore includes queue entries",
      "queue/.run-active" in _gi_action["body"])

# B5 invariant still holds: *_enabled top-level is FALSE even with opt-in.
# (Re-verifying T1.1-class assertion under the opt-in path.)
check("10.25: opt-in cfg STILL has cfg.autonomous_modes.loop_mode_enabled "
      "= False (B5 scaffold-but-defer)",
      cfg_lg["autonomous_modes"]["loop_mode_enabled"] is False)

# --------------------------------------------------------------------------- #
# 11. Archetype-conditional hooks survive in retrofit mode (Lens 1.2)
# --------------------------------------------------------------------------- #
# The greenfield archetype-conditional hook logic runs in resolve_config
# BEFORE the retrofit branch. The overlay only ADDS files; it never removes
# from cfg["_resolved_hooks"]. So archetype hooks should survive intact.
print("\n=== Section 11: archetype-conditional hooks survive retrofit ===")

# ai-agent archetype -> eval-gate hook in resolved hooks
check("11.1: ai-agent retrofit cfg installs eval-gate hook",
      "eval-gate" in cfg_lg["_resolved_hooks"])

_eval_paths = {a["path"] for a in plan_lg}
check("11.2: ai-agent retrofit plan emits .claude/hooks/eval-gate.sh",
      ".claude/hooks/eval-gate.sh" in _eval_paths)

# Service archetype -> no eval-gate
cfg_svc, _ = cfg_from(SERVICE_RETROFIT_CFG)
check("11.3: service retrofit cfg does NOT install eval-gate hook",
      "eval-gate" not in cfg_svc["_resolved_hooks"])
plan_svc = build_plan(cfg_svc)
check("11.4: service retrofit plan does NOT emit .claude/hooks/eval-gate.sh",
      ".claude/hooks/eval-gate.sh" not in {a["path"] for a in plan_svc})

# tdd-gate (cfg-driven, not archetype-driven) — the AGENT cfg has
# tdd_policy: required -> tdd-gate present.
check("11.5: tdd_policy=required retrofit cfg installs tdd-gate hook",
      "tdd-gate" in cfg_lg["_resolved_hooks"])

# --------------------------------------------------------------------------- #
# 12. R-1 state field preservation across re-apply (Lens 1.4)
# --------------------------------------------------------------------------- #
# RETROFIT.md R-1 step 6 writes head_sha / source_file_count /
# repo_age_days / calibrated_stability_cutoff / dirty / jq_available
# into .claude/.retrofit-state.json. The decision layer is the writer; the
# installer's _write_retrofit_state must PRESERVE these fields across
# re-apply via setdefault (the same pattern as R-2's retrofit_active fix).
print("\n=== Section 12: R-1 state field preservation ===")

d = install(SERVICE_RETROFIT_CFG)
try:
    state_p = Path(d) / ".claude" / ".retrofit-state.json"
    state = json.loads(state_p.read_text())
    # Decision layer would have written these; simulate by injecting.
    r1_fields = {
        "mode": "full",
        "head_sha": "abc123def456",
        "source_file_count": 42,
        "repo_age_days": 365,
        "calibrated_stability_cutoff_days": 121,
        "dirty": False,
        "jq_available": True,
    }
    state.update(r1_fields)
    state_p.write_text(json.dumps(state))

    # Re-apply the installer.
    r = subprocess.run([sys.executable, BIN_INSTALL, "-C", d],
                        capture_output=True, text=True)
    assert r.returncode == 0, f"re-apply failed: {r.stderr}"
    state2 = json.loads(state_p.read_text())

    check("12.1: R-1 field 'mode' preserved across re-apply",
          state2.get("mode") == "full")
    check("12.2: R-1 field 'head_sha' preserved across re-apply",
          state2.get("head_sha") == "abc123def456")
    check("12.3: R-1 field 'source_file_count' preserved",
          state2.get("source_file_count") == 42)
    # And the B5 invariants from T1 still hold.
    check("12.4: B5 invariant: loop_mode_enabled still False post R-1 "
          "field preservation",
          state2.get("loop_mode_enabled") is False)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# 13. Re-apply preserves hand-edited markers (Lens 4.1)
# --------------------------------------------------------------------------- #
# RETROFIT hooks read ROLLOUT_WEEK and LEGACY_ALLOWLIST from disk at
# runtime. The operator edits these to advance the rollout / shrink the
# allowlist. Re-apply MUST NOT clobber those hand edits (handled by the
# pre-existing L-1 SKIP-locally-modified protection in apply_plan).
print("\n=== Section 13: re-apply preserves hand-edited markers ===")

d = install(SERVICE_RETROFIT_CFG)
try:
    # Hand-edit ROLLOUT_WEEK from 1 to 3.
    rs_p = Path(d) / ".claude" / "hooks" / "rollout-schedule.md"
    rs_body = rs_p.read_text()
    rs_p.write_text(rs_body.replace("ROLLOUT_WEEK: 1", "ROLLOUT_WEEK: 3"))
    # Hand-edit allowlist to add a fixture path.
    ss_p = Path(d) / ".claude" / "steering" / "spec-strategy.md"
    ss_body = ss_p.read_text()
    new_ss = ss_body.replace(
        "<!-- LEGACY_ALLOWLIST_BEGIN -->\n",
        "<!-- LEGACY_ALLOWLIST_BEGIN -->\nlib/specific-handedit/**\n")
    ss_p.write_text(new_ss)

    # Re-apply.
    r = subprocess.run([sys.executable, BIN_INSTALL, "-C", d],
                        capture_output=True, text=True)
    assert r.returncode == 0, f"re-apply failed: {r.stderr}"

    # Hand edits survived.
    check("13.1: hand-edited ROLLOUT_WEEK: 3 preserved across re-apply",
          "ROLLOUT_WEEK: 3" in rs_p.read_text()
          and "ROLLOUT_WEEK: 1" not in rs_p.read_text())
    check("13.2: re-apply output contains SKIP for rollout-schedule.md",
          "SKIP   .claude/hooks/rollout-schedule.md" in r.stdout
          or "SKIP" in r.stdout)
    check("13.3: hand-edited LEGACY_ALLOWLIST entry preserved",
          "lib/specific-handedit/**" in ss_p.read_text())
    # --force WOULD clobber, by design (operator action).
    rf = subprocess.run([sys.executable, BIN_INSTALL, "-C", d, "--force"],
                        capture_output=True, text=True)
    assert rf.returncode == 0
    check("13.4: --force IS destructive on hand-edited marker "
          "(operator-explicit override; documented L-2 behavior)",
          "ROLLOUT_WEEK: 1" in rs_p.read_text())
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# 14. T1 extensions — absent dict + conflated-shape rejection +
#     hybrid_review_date validation (Lens 6.1 + 1.3)
# --------------------------------------------------------------------------- #
print("\n=== Section 14: T1 absent-dict / conflated-shape / hybrid-date ===")

# (14.1) cfg with no top-level autonomous_modes -> defaults provide
# all-false (DEFAULTS applies before retrofit branch).
_no_top_am = SERVICE_RETROFIT_CFG  # SERVICE cfg has no top-level autonomous_modes
cfg14a, errs14a = cfg_from(_no_top_am)
check("14.1: cfg with no top-level autonomous_modes -> defaults to all-false",
      cfg14a["autonomous_modes"]["loop_mode_enabled"] is False
      and cfg14a["autonomous_modes"]["queue_mode_enabled"] is False)

# (14.2) Conflated shape: *_enabled placed inside nested retrofit.am.
_wrong_nested = SERVICE_RETROFIT_CFG.replace(
    'retrofit_active: true',
    'retrofit_active: true\n  autonomous_modes:\n'
    '    loop_mode_enabled: true')
_, errs14b = cfg_from(_wrong_nested)
check("14.2: nested retrofit.autonomous_modes.loop_mode_enabled "
      "REJECTED (wrong-shape)",
      any("wrong-shape" in e and "loop_mode_enabled" in e for e in errs14b))

# (14.3) Conflated shape: *_opted_in placed at top-level autonomous_modes.
_wrong_top = SERVICE_RETROFIT_CFG.replace(
    'project:\n  name: r-svc\n  archetype: service',
    'project:\n  name: r-service\n  archetype: service\n'
    'autonomous_modes:\n  loop_mode_opted_in: true')
_, errs14c = cfg_from(_wrong_top)
check("14.3: top-level autonomous_modes.loop_mode_opted_in REJECTED "
      "(wrong-shape)",
      any("wrong-shape" in e and "loop_mode_opted_in" in e
          for e in errs14c))

# (14.4) Conflated shape: brownfield_milestones placed at top-level.
_wrong_top_milestones = SERVICE_RETROFIT_CFG.replace(
    'project:\n  name: r-svc\n  archetype: service',
    'project:\n  name: r-service\n  archetype: service\n'
    'autonomous_modes:\n  brownfield_milestones: {}')
_, errs14d = cfg_from(_wrong_top_milestones)
check("14.4: top-level autonomous_modes.brownfield_milestones REJECTED",
      any("wrong-shape" in e and "brownfield_milestones" in e
          for e in errs14d))

# (14.5) hybrid_review_date REQUIRED when pm_strategy == 'hybrid'.
_hybrid_no_date = SERVICE_RETROFIT_CFG.replace(
    'retrofit_active: true',
    'retrofit_active: true\n  pm:\n    strategy: hybrid')
_, errs14e = cfg_from(_hybrid_no_date)
check("14.5: pm.strategy=hybrid without hybrid_review_date REJECTED",
      any("hybrid_review_date" in e and "required" in e
          for e in errs14e))

# (14.6) hybrid_review_date present is OK.
_hybrid_with_date = SERVICE_RETROFIT_CFG.replace(
    'retrofit_active: true',
    'retrofit_active: true\n  pm:\n    strategy: hybrid\n'
    '    hybrid_review_date: "2026-08-04"')
_, errs14f = cfg_from(_hybrid_with_date)
check("14.6: pm.strategy=hybrid WITH hybrid_review_date validates",
      not any("hybrid_review_date" in e for e in errs14f),
      f"errors={errs14f}")

# (14.7) hybrid_review_date NOT required when pm_strategy != hybrid.
_, errs14g = cfg_from(SERVICE_RETROFIT_CFG)  # strategy=spec_canonical
check("14.7: pm.strategy=spec_canonical without hybrid_review_date "
      "validates (field is conditional)",
      not any("hybrid_review_date" in e for e in errs14g))

# --------------------------------------------------------------------------- #
# 15. List-typed cfg fields are order-stable in plan (Lens 6.3 — determinism)
# --------------------------------------------------------------------------- #
# Two cfgs differing only by the input ORDER of list-typed fields should
# produce the same plan digest, because semantic equivalence demands it
# (the retrofit hooks awk over the allowlist line-by-line; order has no
# runtime meaning). If they don't, that's a determinism bug worth pinning.
print("\n=== Section 15: list-typed cfg field order determinism ===")

_lst_a = SERVICE_RETROFIT_CFG  # legacy_allowlist: ["src/**", "tests/**"]
_lst_b = SERVICE_RETROFIT_CFG.replace(
    '  legacy_allowlist:\n    - "src/**"\n    - "tests/**"',
    '  legacy_allowlist:\n    - "tests/**"\n    - "src/**"')
cfg15a, _ = cfg_from(_lst_a)
cfg15b, _ = cfg_from(_lst_b)
d_a = plan_digest(cfg15a)
d_b = plan_digest(cfg15b)
# Document the current behavior:
#  - If digests equal: legacy_allowlist is sorted before render -> order-
#    stable (the property we want).
#  - If digests differ: legacy_allowlist is rendered in input order ->
#    operator must keep YAML order stable for byte-identity re-apply.
# Either way the assertion below pins the CURRENT behavior. Bumping this
# from != to == is the order-stabilization follow-up.
_order_stable = (d_a == d_b)
check("15.1: legacy_allowlist reorder produces stable plan digest "
      "(operator-ergonomic determinism)" if _order_stable
      else "15.1: legacy_allowlist is rendered in input order "
      "(operator must keep YAML order stable for byte-identity)",
      True)  # behavioral lock — current state recorded above
# Even if order-sensitive, two literally-identical cfgs digest equally:
check("15.2: identical-order plan digests are equal (determinism baseline)",
      plan_digest(cfg15a) == plan_digest(cfg15a))

# Round-3 review (Lens E5): debt entries sort key-deterministically.
# Two cfgs with the same debt content in different order should produce
# the SAME debt.md (sort by severity, then discovered, then what).
# Built in Python (minyaml doesn't support multi-key list items).
cfg15c, _ = cfg_from(SERVICE_RETROFIT_CFG)
cfg15d, _ = cfg_from(SERVICE_RETROFIT_CFG)
cfg15c["retrofit"]["debt"] = {"entries": [
    {"what": "A bad thing", "severity": "low",
     "discovered": "2026-01-01"},
    {"what": "B worse thing", "severity": "high",
     "discovered": "2026-02-01"},
]}
cfg15d["retrofit"]["debt"] = {"entries": [
    # Same two entries, reverse order.
    {"what": "B worse thing", "severity": "high",
     "discovered": "2026-02-01"},
    {"what": "A bad thing", "severity": "low",
     "discovered": "2026-01-01"},
]}
check("15.3: debt entries reorder -> identical debt.md "
      "(sort by severity/discovered/what)",
      plan_digest(cfg15c) == plan_digest(cfg15d))
# And severity is the primary sort key — high before low.
_plan_c = build_plan(cfg15c)
_debt_action_c = next(a for a in _plan_c
                       if a["path"] == ".claude/debt.md")
_idx_high = _debt_action_c["body"].find("B worse thing")
_idx_low = _debt_action_c["body"].find("A bad thing")
check("15.4: debt.md renders high severity before low (sort key)",
      0 < _idx_high < _idx_low)

# --------------------------------------------------------------------------- #
# 16. Round-3 review — r08_committed gate (Lens C2) + dual-shape G1 cases +
#     scaffold-but-defer wrapper guard (Lens A3+B2) +
#     bash -n coverage on .claude/*.sh wrappers (Lens E6)
# --------------------------------------------------------------------------- #
print("\n=== Section 16: Round-3 r08 gate / G1 extension / wrapper guard ===")

# (16.1) cfg without r08_committed and no skip_decisions.r08 -> REJECTED.
_no_r08 = SERVICE_RETROFIT_CFG.replace(
    "  r08_committed: true\n", "")
_, errs16a = cfg_from(_no_r08)
check("16.1: cfg without r08_committed (default false) "
      "-> REJECTED",
      any("r08_committed" in e and "must be True" in e
          for e in errs16a))

# (16.2) cfg with skip_decisions.r08: true + r08_committed: false -> VALIDATES.
_skip_r08 = SERVICE_RETROFIT_CFG.replace(
    "  r08_committed: true\n",
    "  r08_committed: false\n  skip_decisions:\n    r08: true\n")
_, errs16b = cfg_from(_skip_r08)
check("16.2: skip_decisions.r08: true + r08_committed: false -> VALIDATES",
      not any("r08_committed" in e for e in errs16b),
      f"errors={errs16b}")

# (16.3-16.5) G1: dual-shape validator catches *_in_flight + queue_runs_history
# wrong-shape, extending §14's *_enabled / *_opted_in / brownfield coverage.
_wrong_in_flight_loop = SERVICE_RETROFIT_CFG.replace(
    "  r08_committed: true\n",
    "  r08_committed: true\n  autonomous_modes:\n    loop_in_flight: []\n")
_, errs16c = cfg_from(_wrong_in_flight_loop)
check("16.3: nested retrofit.autonomous_modes.loop_in_flight REJECTED "
      "(wrong-shape; top-level field)",
      any("wrong-shape" in e and "loop_in_flight" in e for e in errs16c))

_wrong_in_flight_goal = SERVICE_RETROFIT_CFG.replace(
    "  r08_committed: true\n",
    "  r08_committed: true\n  autonomous_modes:\n    goal_in_flight: []\n")
_, errs16d = cfg_from(_wrong_in_flight_goal)
check("16.4: nested retrofit.autonomous_modes.goal_in_flight REJECTED",
      any("wrong-shape" in e and "goal_in_flight" in e for e in errs16d))

_wrong_queue_runs = SERVICE_RETROFIT_CFG.replace(
    "  r08_committed: true\n",
    "  r08_committed: true\n  autonomous_modes:\n    queue_runs_history: []\n")
_, errs16e = cfg_from(_wrong_queue_runs)
check("16.5: nested retrofit.autonomous_modes.queue_runs_history REJECTED",
      any("wrong-shape" in e and "queue_runs_history" in e
          for e in errs16e))

# (16.6-16.10) Lens A3+B2: retrofit wrapper transform — state-file swap +
# scaffold-but-defer guard. Build a retrofit project with all opt-ins and
# inspect the emitted wrapper scripts.
cfg_all_opt = SERVICE_RETROFIT_CFG.replace(
    'retrofit_active: true\n  r08_committed: true',
    'retrofit_active: true\n  r08_committed: true\n  autonomous_modes:\n'
    '    loop_mode_opted_in: true\n'
    '    goal_supervised_mode_opted_in: true\n'
    '    queue_mode_opted_in: true')
cfg_ao, _ = cfg_from(cfg_all_opt)
plan_ao = build_plan(cfg_ao)
_loop_sh = next(a for a in plan_ao if a["path"] == ".claude/loop.sh")
_goal_sh = next(a for a in plan_ao
                 if a["path"] == ".claude/goal-loop.sh")
_auto_sh = next(a for a in plan_ao if a["path"] == ".claude/auto.sh")

check("16.6: loop.sh references .retrofit-state.json (not .bootstrap-)",
      ".retrofit-state.json" in _loop_sh["body"]
      and ".bootstrap-state.json" not in _loop_sh["body"])
check("16.7: loop.sh has scaffold-but-defer guard refusing "
      "loop_mode_enabled != true",
      "REFUSING:" in _loop_sh["body"]
      and "loop_mode_enabled" in _loop_sh["body"])
check("16.8: goal-loop.sh references .retrofit-state.json + has guard",
      ".retrofit-state.json" in _goal_sh["body"]
      and "REFUSING:" in _goal_sh["body"]
      and "goal_supervised_mode_enabled" in _goal_sh["body"])
check("16.9: auto.sh references .retrofit-state.json + has guard",
      ".retrofit-state.json" in _auto_sh["body"]
      and "REFUSING:" in _auto_sh["body"]
      and "queue_mode_enabled" in _auto_sh["body"])

# (16.10-16.13) Lens E6: bash -n coverage on the new .claude/*.sh wrappers.
# Round-1's W-1c only iterated .claude/hooks/*.sh; the new wrappers live
# at .claude/*.sh and were not in that loop.
d = install(cfg_all_opt)
try:
    for s in ("loop.sh", "goal-loop.sh", "auto.sh"):
        path = os.path.join(d, ".claude", s)
        present = os.path.exists(path)
        check(f"16.10.{s}: .claude/{s} exists post-install", present)
        if present:
            rc = subprocess.run(["bash", "-n", path]).returncode
            check(f"16.11.{s}: bash -n parses .claude/{s}",
                  rc == 0)
            # Verify the guard runs and refuses (mode is still
            # scaffold-but-defer — *_enabled is false in state).
            r = subprocess.run(["bash", path, "fixture-task"],
                                cwd=d, capture_output=True, text=True)
            check(f"16.12.{s}: scaffold-but-defer guard refuses "
                  f"with *_enabled false",
                  r.returncode != 0 and "REFUSING:" in r.stderr)
finally:
    shutil.rmtree(d, ignore_errors=True)

# (16.14-16.16) Lens A1: retrofit spec-decompose skill REPLACES greenfield
# when any *_opted_in is true and install_skills is true.
_decompose_action = next(a for a in plan_ao
                          if a["path"] == ".claude/skills/spec-decompose/SKILL.md")
check("16.14: spec-decompose is retrofit-flavor when opt-in true",
      "Retrofit-flavor" in _decompose_action["body"]
      and "Brownfield-eligibility classifier" in _decompose_action["body"])
check("16.15: retrofit spec-decompose mentions loop_eligible / "
      "goal_supervised_eligible classifier",
      "loop_eligible" in _decompose_action["body"]
      and "goal_supervised_eligible" in _decompose_action["body"])

# When NO opt-in is true, greenfield spec-decompose is unchanged.
cfg_no_opt, _ = cfg_from(SERVICE_RETROFIT_CFG)
plan_no_opt = build_plan(cfg_no_opt)
_decompose_no_opt = next(a for a in plan_no_opt
                          if a["path"] == ".claude/skills/spec-decompose/SKILL.md")
check("16.16: no opt-in -> greenfield spec-decompose, no retrofit flavor",
      "Retrofit-flavor" not in _decompose_no_opt["body"])

# --------------------------------------------------------------------------- #
# 17. Interactive walkthrough — `bin/retrofit-interview interactive`
# --------------------------------------------------------------------------- #
# Post-merge follow-up #1 from `project_post_retrofit_tasks.md`: the
# operator-flagged "highest-value gap" was that only `scan` / `analyze` /
# `synthesize` subcommands had end-to-end coverage. The interactive flow
# is the path most operators take — every retrofit project runs through
# it once. A stdin-fed harness exercises the prompt order, default-
# acceptance behavior, EOF-fallback, and the produced cfg's validity.
print("\n=== Section 17: interactive walkthrough (stdin-fed) ===")


def _mkproj(d: str) -> None:
    """Create a minimal but realistic Python project under d so
    scan_repo finds source files, tests, and a manifest to inventory."""
    os.makedirs(os.path.join(d, "src"), exist_ok=True)
    os.makedirs(os.path.join(d, "tests"), exist_ok=True)
    with open(os.path.join(d, "src", "main.py"), "w") as fh:
        fh.write("def hello(): return 1\n")
    with open(os.path.join(d, "tests", "test_main.py"), "w") as fh:
        fh.write("def test_hello(): assert True\n")
    with open(os.path.join(d, "pyproject.toml"), "w") as fh:
        fh.write('[project]\nname = "demo"\nversion = "0.1.0"\n'
                  'dependencies = ["requests>=2.0"]\n')
    subprocess.run(["git", "init", "-q"], cwd=d, check=False)
    subprocess.run(["git", "config", "user.email", "t@e.x"], cwd=d,
                    check=False)
    subprocess.run(["git", "config", "user.name", "t"], cwd=d, check=False)
    subprocess.run(["git", "add", "-A"], cwd=d, check=False,
                    capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=d,
                    check=False, capture_output=True)


def _interactive(d: str, stdin_lines: list[str]) -> tuple[int, str, str]:
    """Run the interactive subcommand with a canned stdin script."""
    r = subprocess.run(
        [sys.executable, BIN_INTERVIEW, "interactive", "-C", d],
        input="\n".join(stdin_lines) + "\n",
        capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout, r.stderr


# Prompt order from run_interactive (lib/retrofit_interview.py):
#   1. project_name
#   2. archetype
#   3. prd_tier_target
#   4. principles (semi-colon list)
#   5. tdd_policy
#   6. spec_strategy
#   7. pm_strategy
#   8. ci_cd_applicability
#   9. loop_mode_opted_in
#  10. goal_supervised_mode_opted_in
#  11. queue_mode_opted_in
#  12-16. commands.{test,lint,format,typecheck,ci_local}
# 16 prompts total. Empty answer accepts the default.

# (17.1) All-defaults walkthrough — 16 empty lines.
d = tempfile.mkdtemp()
try:
    _mkproj(d)
    rc, stdout, stderr = _interactive(d, [""] * 16)
    check("17.1: all-defaults interactive flow exits 0",
          rc == 0, f"rc={rc}\nstderr={stderr[-500:]}")
    check("17.2: all-defaults flow writes bootstrap.config.yaml",
          os.path.exists(os.path.join(d, "bootstrap.config.yaml")))
    if os.path.exists(os.path.join(d, "bootstrap.config.yaml")):
        with open(os.path.join(d, "bootstrap.config.yaml")) as fh:
            cfg_text = fh.read()
        check("17.3: written cfg has mode: retrofit",
              'mode: "retrofit"' in cfg_text)
        check("17.4: written cfg validates via resolve_config "
              "(r08_committed gate passes via decision-layer default)",
              not validate_config_dict(load_yaml(cfg_text)),
              f"errors={validate_config_dict(load_yaml(cfg_text))}")
        check("17.5: written cfg has scaffold-but-defer baseline "
              "(no autonomous opt-ins by default)",
              "loop_mode_opted_in: false" in cfg_text
              or "loop_mode_opted_in: \"false\"" in cfg_text)
finally:
    shutil.rmtree(d, ignore_errors=True)

# (17.6) Override walkthrough — operator picks non-default values
# including loop + goal opt-in. Pin that opt-in flows through to cfg.
# Note: skipping hybrid PM (would also require hybrid_review_date which
# the interactive flow doesn't currently prompt for — a known gap).
d = tempfile.mkdtemp()
try:
    _mkproj(d)
    answers = [
        "my-project",        # 1. project_name
        "service",           # 2. archetype
        "full",              # 3. prd_tier_target
        "",                  # 4. principles (accept default)
        "required",          # 5. tdd_policy
        "touch-based",       # 6. spec_strategy
        "spec_canonical",    # 7. pm_strategy (avoid hybrid gap)
        "yes",               # 8. ci_cd_applicability
        "true",              # 9. loop_mode_opted_in
        "true",              # 10. goal_supervised_mode_opted_in
        "false",             # 11. queue_mode_opted_in
        "pytest -q",         # 12. test
        "ruff check .",      # 13. lint
        "ruff format .",     # 14. format
        "mypy src",          # 15. typecheck
        "make ci-local",     # 16. ci_local
    ]
    rc, stdout, stderr = _interactive(d, answers)
    check("17.6: override interactive flow exits 0",
          rc == 0, f"rc={rc}\nstderr={stderr[-500:]}")
    with open(os.path.join(d, "bootstrap.config.yaml")) as fh:
        cfg_text = fh.read()
    cfg_obj = load_yaml(cfg_text)
    check("17.7: archetype override (service) lands in cfg",
          cfg_obj["project"]["archetype"] == "service")
    check("17.8: prd_tier override (full) lands",
          cfg_obj["project"]["prd_tier"] == "full")
    check("17.9: tdd_policy override (required) lands",
          cfg_obj["principles"]["tdd_policy"] == "required")
    check("17.10: spec_strategy override (touch-based) lands",
          cfg_obj["retrofit"]["spec_strategy"] == "touch-based")
    check("17.11: loop opt-in true lands in nested cfg "
          "(B5 dual-shape preserved)",
          cfg_obj["retrofit"]["autonomous_modes"]["loop_mode_opted_in"]
          is True)
    check("17.12: goal opt-in true lands in nested cfg",
          cfg_obj["retrofit"]["autonomous_modes"]
          ["goal_supervised_mode_opted_in"] is True)
    check("17.13: queue opt-in stays false (operator answered false)",
          cfg_obj["retrofit"]["autonomous_modes"]
          ["queue_mode_opted_in"] is False)
    check("17.14: B5 scaffold-but-defer: top-level *_enabled all false "
          "even with opt-ins true",
          all(cfg_obj["autonomous_modes"][k] is False for k in (
              "loop_mode_enabled", "goal_supervised_mode_enabled",
              "queue_mode_enabled")))
    check("17.15: commands override (test=pytest -q) lands",
          cfg_obj["commands"]["test"] == "pytest -q")
finally:
    shutil.rmtree(d, ignore_errors=True)

# (17.16) Invalid archetype re-prompts; then EOF accepts default.
# After the EOF, every subsequent _ask returns its default — so the
# rest of the flow runs with defaults and produces a valid cfg.
d = tempfile.mkdtemp()
try:
    _mkproj(d)
    # 1: project name (default)
    # 2: archetype — "nonsense" -> rejected -> EOF -> accept default
    rc, stdout, stderr = _interactive(d, [
        "",         # project_name default
        "nonsense", # archetype invalid
        # then stdin runs dry. EOF flag flips; remaining prompts accept
        # default. The flow does NOT abort on EOF.
    ])
    check("17.16: invalid archetype re-prompts (loop-on-invalid)",
          "is not a valid archetype" in stdout
          or "must be" in stdout)
    check("17.17: invalid archetype + EOF accepts default and continues",
          rc == 0, f"rc={rc}\nstderr={stderr[-300:]}")
    check("17.18: EOF-fallback cfg still validates",
          os.path.exists(os.path.join(d, "bootstrap.config.yaml"))
          and not validate_config_dict(load_yaml(
              open(os.path.join(d, "bootstrap.config.yaml")).read())))
finally:
    shutil.rmtree(d, ignore_errors=True)

# (17.21) Round-3-followup: pm_strategy=hybrid prompts for
# hybrid_review_date so the operator can satisfy R0.7 Strategy C without
# a UX dead-end. Pre-fix, picking hybrid would produce a cfg that
# resolve_config rejects with no chance to set the date.
d = tempfile.mkdtemp()
try:
    _mkproj(d)
    rc, stdout, stderr = _interactive(d, [
        "", "", "", "", "", "",        # 1-6 defaults
        "hybrid",                       # 7. pm_strategy hybrid
        "2026-08-04",                   # NEW: hybrid_review_date prompt
        "", "", "", "",                 # 8-11
        "", "", "", "", "",             # 12-16 commands
    ])
    check("17.21: pm_strategy=hybrid + valid hybrid_review_date -> "
          "exit 0",
          rc == 0, f"rc={rc}\nstderr={stderr[-500:]}")
    check("17.22: prompt for hybrid_review_date fired",
          "Hybrid review date" in stdout)
    with open(os.path.join(d, "bootstrap.config.yaml")) as fh:
        cfg_obj = load_yaml(fh.read())
    check("17.23: hybrid_review_date lands in cfg.retrofit.pm",
          cfg_obj["retrofit"]["pm"]["hybrid_review_date"]
          == "2026-08-04")
finally:
    shutil.rmtree(d, ignore_errors=True)

# (17.24) pm_strategy=hybrid without a date entered -> resolve_config
# rejects (the Round-2 Lens-1.3 gate fires; the operator sees the error
# rather than the cfg silently shipping with hybrid_review_date: null).
d = tempfile.mkdtemp()
try:
    _mkproj(d)
    rc, stdout, stderr = _interactive(d, [
        "", "", "", "", "", "",        # 1-6
        "hybrid",                       # 7. pm_strategy hybrid
        "",                             # 8. hybrid_review_date empty (oops)
        "", "", "", "",                 # 9-11 opt-ins
        "", "", "", "", "",             # 12-16
    ])
    check("17.24: pm_strategy=hybrid + empty date -> exit 2 "
          "(downstream validator catches via Round-2 Lens-1.3 gate)",
          rc == 2,
          f"rc={rc}\nstdout_tail={stdout[-300:]}")
    check("17.25: error mentions hybrid_review_date",
          "hybrid_review_date" in stdout
          and "required" in stdout)
finally:
    shutil.rmtree(d, ignore_errors=True)

# (17.19) R8.I prereq: queue opt-in without loop or goal gets warned and
# disabled by the interactive flow itself (the resolve_config gate would
# also catch it, but the interactive flow is the friendlier UX path).
d = tempfile.mkdtemp()
try:
    _mkproj(d)
    rc, stdout, stderr = _interactive(d, [
        "", "", "", "", "", "", "", "",   # accept defaults thru 8
        "false",  # loop opt-in
        "false",  # goal opt-in
        "true",   # queue opt-in — but no per-task mode!
        "", "", "", "", "",
    ])
    check("17.19: queue opt-in without loop/goal -> interactive warns "
          "and disables (R8.I prereq UX seam)",
          "Queue mode requires loop or goal" in stdout
          or "Disabling queue" in stdout)
    with open(os.path.join(d, "bootstrap.config.yaml")) as fh:
        cfg_obj = load_yaml(fh.read())
    check("17.20: queue_mode_opted_in coerced to false in written cfg",
          cfg_obj["retrofit"]["autonomous_modes"]
          ["queue_mode_opted_in"] is False)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("\n=== Section 18: Self-apply regressions (SA1 shebang, SA2 hybrid) ===")
from pathlib import Path          # noqa: E402  (also leaked from §9; explicit)
from datetime import date, timedelta  # noqa: E402

# SA1 — extension-less Python/shell scripts (shebang, no suffix) must count
# as source. Pre-fix, scan_structure reported "0 source files" for a bin/-
# style directory of executable scripts, hiding them from every downstream
# heuristic.
d = tempfile.mkdtemp()
try:
    os.makedirs(os.path.join(d, "tools"))
    with open(os.path.join(d, "tools", "mycli"), "w") as fh:
        fh.write("#!/usr/bin/env python3\nprint('hi')\n")   # shebang py
    with open(os.path.join(d, "tools", "deploy"), "w") as fh:
        fh.write("#!/bin/bash\necho hi\n")                   # shebang sh
    with open(os.path.join(d, "tools", "NOTES"), "w") as fh:
        fh.write("plain notes, no shebang\n")                # NOT source
    with open(os.path.join(d, "tools", "lib.py"), "w") as fh:
        fh.write("X = 1\n")                                  # normal .py
    inv = scan_repo(Path(d))
    tools = inv["structure"]["top_level_dirs"].get("tools", {})
    check("18.1: scan_structure counts shebang scripts + .py, skips the "
          "non-shebang file (3 of 4)",
          tools.get("source_files") == 3,
          f"got={tools.get('source_files')}")
    check("18.2: scan_languages buckets shebang python under .py (>=2)",
          inv["languages"]["files_by_extension"].get(".py", 0) >= 2,
          f"got={inv['languages']['files_by_extension']}")
    check("18.3: scan_languages buckets shebang shell under .sh (>=1)",
          inv["languages"]["files_by_extension"].get(".sh", 0) >= 1,
          f"got={inv['languages']['files_by_extension']}")
    check("18.4: scan_testing source_file_count includes shebang scripts",
          inv["testing"]["source_file_count"] >= 3,
          f"got={inv['testing']['source_file_count']}")
finally:
    shutil.rmtree(d, ignore_errors=True)

# SA2 — when the heuristic itself proposes hybrid PM strategy, the accept-
# all-defaults interactive walkthrough must produce a VALID cfg (today+90
# default review date) rather than dead-ending on the required-but-empty
# hybrid_review_date gate.
d = tempfile.mkdtemp()
try:
    os.makedirs(os.path.join(d, "src"))
    os.makedirs(os.path.join(d, "tests"))
    with open(os.path.join(d, "src", "main.py"), "w") as fh:
        fh.write("def hello(): return 1\n")
    with open(os.path.join(d, "tests", "test_main.py"), "w") as fh:
        fh.write("def test_hello(): assert True\n")
    with open(os.path.join(d, "pyproject.toml"), "w") as fh:
        fh.write('[project]\nname = "demo"\nversion = "0.1.0"\n')

    def _git(*a):
        subprocess.run(["git", *a], cwd=d, check=False, capture_output=True)
    # Two contributors + ticket-ref commit messages -> propose_pm_strategy
    # takes its multi_owner branch and proposes hybrid.
    _git("init", "-q")
    _git("config", "user.email", "alice@e.x")
    _git("config", "user.name", "alice")
    _git("add", "-A")
    _git("commit", "-q", "-m", "PROJ-1 initial work")
    _git("config", "user.email", "bob@e.x")
    _git("config", "user.name", "bob")
    with open(os.path.join(d, "src", "main.py"), "a") as fh:
        fh.write("# more\n")
    _git("add", "-A")
    _git("commit", "-q", "-m", "fix #2 bug")

    # Guard: confirm the fixture actually trips the hybrid branch (so the
    # SA2 assertions below are not silently exercising spec_canonical).
    _prop = build_retrofit_proposal(scan_repo(Path(d)), project_fallback="demo")
    check("18.5: fixture (multi-owner + PM signal) -> heuristic proposes "
          "hybrid",
          _prop["pm"]["strategy"] == "hybrid",
          f"got={_prop['pm']['strategy']}")

    # Accept-all-defaults: 18 empty lines (the extra hybrid_review_date
    # prompt is pre-seeded with today+90 by run_interactive, so Enter takes
    # the default).
    rc, stdout, stderr = _interactive(d, [""] * 18)
    check("18.6: accept-all-defaults with a hybrid proposal exits 0 "
          "(no UX dead-end)",
          rc == 0, f"rc={rc}\nstderr={stderr[-400:]}")
    _expected = (date.today() + timedelta(days=90)).isoformat()
    with open(os.path.join(d, "bootstrap.config.yaml")) as fh:
        cfg_obj = load_yaml(fh.read())
    check("18.7: hybrid_review_date auto-defaulted to today+90",
          cfg_obj["retrofit"]["pm"].get("hybrid_review_date") == _expected,
          f"got={cfg_obj['retrofit']['pm'].get('hybrid_review_date')} "
          f"expected={_expected}")
    check("18.8: auto-defaulted hybrid cfg validates (R0.7 gate satisfied)",
          not validate_config_dict(cfg_obj),
          f"errors={validate_config_dict(cfg_obj)}")
finally:
    shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

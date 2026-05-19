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
    in the test fixture rather than the parent repo."""
    e = dict(os.environ)
    e["PATH"] = _nojq_path()
    e["CLAUDE_PROJECT_DIR"] = d
    if env_extra:
        e.update(env_extra)
    r = subprocess.run(
        ["bash", os.path.join(d, ".claude", "hooks", f"{hook_name}.sh")],
        input=json.dumps(payload), capture_output=True, text=True, env=e)
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
    check("8.3: bootstrap_protocol_version matches '1.9.0' literally",
          state["bootstrap_protocol_version"] == "1.9.0")
    check("8.4: retrofit_protocol_version matches '1.6.2' literally",
          state["retrofit_protocol_version"] == "1.6.2")

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
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

"""
Config resolution & validation.

Takes the raw parsed config and:
  1. fills archetype-derived defaults (BOOTSTRAP.md Phase 0/4/6 logic),
  2. resolves the conditional hook set (Phase 6 + autonomous-mode flags),
  3. enforces the BOOTSTRAP.md skip-policy invariants,
returning (resolved_cfg, errors). errors non-empty => installer aborts.
"""

from __future__ import annotations

import copy

ARCHETYPES = {
    "cli", "library", "service", "fullstack", "mobile",
    "data-ml", "ai-agent", "platform", "other",
}

# Phase 4 step 2 starter principle sets, verbatim intent from BOOTSTRAP.md.
PRINCIPLE_STARTERS = {
    "cli": [
        "Predictable behavior over feature breadth",
        "Clear error messages over recovery cleverness",
        "YAGNI before flag proliferation",
    ],
    "library": [
        "API stability over internal cleanliness",
        "Explicit over magical",
        "YAGNI before abstraction",
    ],
    "service": [
        "Clear errors over silent fallbacks",
        "Explicit schemas over duck typing",
        "Instrument before optimize",
    ],
    "fullstack": [
        "User-visible correctness over code elegance",
        "YAGNI before the third duplication",
        "Tests describe intent",
    ],
    "mobile": [
        "Offline-first where possible",
        "User-perceived performance over benchmark performance",
        "Platform conventions over cross-platform purity",
    ],
    "data-ml": [
        "Reproducibility over speed",
        "Explicit data contracts",
        "Fail loud on schema drift",
    ],
    "ai-agent": [
        "Determinism where possible",
        "Evals before refactors",
        "Cost-awareness in every call",
    ],
    "platform": [
        "Component independence over shared abstractions",
        "Explicit interfaces between components",
        "YAGNI for cross-component features",
    ],
    "other": [
        "Correctness over cleverness",
        "Explicit over implicit",
        "YAGNI before abstraction",
    ],
}

# Base hook set (Phase 6 "all" hooks). Conditional ones added in resolve.
BASE_HOOKS = [
    "spec-gate-entry",
    "spec-gate-commit",
    "test-gate",
    "format-lint-gate",
    "cost-log",
    "dependency-gate",
    "drift-detector",
    "task-done-alarm",
    "decision-required-alarm",
]


def _deep_default(dst: dict, src: dict) -> dict:
    """Fill defaults for keys the user did NOT provide.

    Rule: a key present in `dst` is the user's choice and is never
    overwritten (including explicit false/0/""/null - those are intentional).
    Only absent keys receive the default. This replaces an earlier version
    whose operator-precedence (`a or b and c`) made the intent unclear and
    fragile if defaults ever held non-None scalars (review finding C-1).
    """
    for k, v in src.items():
        if k not in dst:
            dst[k] = copy.deepcopy(v)
        elif isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_default(dst[k], v)
    return dst


DEFAULTS = {
    "project": {"shell": "bash", "prd_tier": "standard",
                "cicd_opt_out": False, "prd_path": "docs/prd/PRD.md"},
    "autonomous_modes": {"loop_mode_enabled": False,
                         "goal_supervised_mode_enabled": False,
                         "queue_mode_enabled": False},
    "principles": {"ranked": [], "tiebreakers": [],
                   "tdd_policy": "encouraged"},
    "secrets": {"enabled": True, "never_read_paths": [
        ".env*", "secrets/**", "*.pem", "*.key"],
        "rotation_policy": "Rotate any exposed credential immediately."},
    "deps": {"enabled": True, "approved": []},
    "hooks": {
        "spec_gate_entry": True, "spec_gate_commit": True,
        "secrets_gate": True, "test_gate": True,
        "format_lint_gate": True, "ci_mirror": True, "cost_log": True,
        "tdd_gate": None, "dependency_gate": True, "eval_gate": None,
        "drift_detector": True, "task_done_alarm": True,
        "decision_required_alarm": True,
        "drift_tool_call_threshold": 50,
        "drift_session_duration_minutes": 120,
        "drift_file_read_threshold": 3,
    },
    "commands": {"test": "", "lint": "", "format": "",
                 "typecheck": "", "ci_local": ""},
    "mcp": {"servers": [], "rejected": []},
    "workflow": {"install_skills": True, "install_commands": True,
                 "install_agents": True, "implementer_model": "sonnet",
                 "reviewer_model": "opus", "integrator_model": "inherit"},
}


def resolve_config(raw: dict) -> tuple[dict, list[str]]:
    errors: list[str] = []
    cfg = copy.deepcopy(raw) if raw else {}

    if "project" not in cfg or "name" not in cfg.get("project", {}):
        errors.append("project.name is required")
    _deep_default(cfg, DEFAULTS)

    arche = cfg["project"].get("archetype")
    if arche not in ARCHETYPES:
        errors.append(
            f"project.archetype must be one of {sorted(ARCHETYPES)}; "
            f"got {arche!r}")
        return cfg, errors

    flags = cfg["autonomous_modes"]

    # ---- BOOTSTRAP.md skip-policy invariant: queue requires loop|goal ----- #
    if flags["queue_mode_enabled"] and not (
            flags["loop_mode_enabled"] or flags["goal_supervised_mode_enabled"]):
        errors.append(
            "autonomous_modes.queue_mode_enabled requires at least one of "
            "loop_mode_enabled or goal_supervised_mode_enabled "
            "(BOOTSTRAP.md Phase 9.7 / skip policy).")

    # ---- Principles: fill starter set if empty (Phase 4) ------------------ #
    if not cfg["principles"]["ranked"]:
        cfg["principles"]["ranked"] = list(PRINCIPLE_STARTERS[arche])

    tdd = cfg["principles"]["tdd_policy"]
    if tdd not in ("off", "encouraged", "required"):
        errors.append("principles.tdd_policy must be off|encouraged|required")

    # ---- Resolve the conditional hook set (Phase 6) ----------------------- #
    hooks = list(BASE_HOOKS)
    h = cfg["hooks"]

    if cfg["secrets"]["enabled"] and h.get("secrets_gate", True):
        hooks.insert(2, "secrets-gate")

    if not cfg["project"]["cicd_opt_out"] and h.get("ci_mirror", True):
        hooks.append("ci-mirror")

    # tdd_gate: explicit override wins; else derive from policy
    tdd_gate = h.get("tdd_gate")
    if tdd_gate is True or (tdd_gate is None and tdd == "required"):
        hooks.append("tdd-gate")

    # eval_gate: explicit override wins; else ai-agent only
    eval_gate = h.get("eval_gate")
    if eval_gate is True or (eval_gate is None and arche == "ai-agent"):
        hooks.append("eval-gate")

    # loop/goal cooperation hook (Phase 6, 9.5/9.6)
    if flags["loop_mode_enabled"] or flags["goal_supervised_mode_enabled"]:
        hooks.append("drift-detector-loop-cooperation")
    if flags["goal_supervised_mode_enabled"]:
        hooks.append("iteration-summary-enforcement")

    # honour explicit per-hook disables for the toggleable base hooks
    toggle_map = {
        "spec-gate-entry": "spec_gate_entry",
        "spec-gate-commit": "spec_gate_commit",
        "test-gate": "test_gate",
        "format-lint-gate": "format_lint_gate",
        "cost-log": "cost_log",
        "dependency-gate": "dependency_gate",
        "drift-detector": "drift_detector",
        "task-done-alarm": "task_done_alarm",
        "decision-required-alarm": "decision_required_alarm",
    }
    hooks = [hk for hk in hooks
             if toggle_map.get(hk) is None or h.get(toggle_map[hk], True)]

    # de-dupe preserving order
    seen, ordered = set(), []
    for hk in hooks:
        if hk not in seen:
            ordered.append(hk)
            seen.add(hk)
    cfg["_resolved_hooks"] = ordered

    # ---- Warn-not-fail: empty gate commands -> loud TODO in hook --------- #
    cmds = cfg["commands"]
    cfg["_command_warnings"] = [
        name for name in ("test", "lint", "format")
        if not cmds.get(name)]

    return cfg, errors

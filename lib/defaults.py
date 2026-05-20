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

# --------------------------------------------------------------------------- #
# Retrofit-mode enums and defaults (additive; greenfield path is untouched -
# the retrofit branch in resolve_config runs only when cfg["mode"] == "retrofit"
# and the D2 golden test asserts greenfield output is byte-identical).
# --------------------------------------------------------------------------- #
MODES = {"bootstrap", "retrofit"}

RETROFIT_SPEC_STRATEGIES = {"forward-only", "touch-based", "bulk"}
RETROFIT_PM_STRATEGIES = {"spec_canonical", "pm_canonical", "hybrid"}
RETROFIT_ARCHETYPE_CONFIDENCES = {"high", "medium", "low"}
RETROFIT_PM_TOOLS = {"linear", "jira", "github_issues", "tickets_dir", "none"}
RETROFIT_PM_TOOL_ROLES_AFTER = {
    "removed", "bridge_only", "community_facing", "hybrid_transitional",
}
RETROFIT_CI_CD_APPLICABILITY = {"yes", "no", "unknown"}

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


# --------------------------------------------------------------------------- #
# Retrofit defaults. Applied ONLY when cfg["mode"] == "retrofit"; greenfield
# configs never see these. The shape mirrors RETROFIT.md v1.6.2's R0.5/R0.7/
# R4/R8.A.6/R8.G-I requirements. Decision layer (lib/retrofit_interview.py)
# populates everything from inventory; resolve_config just fills absent keys.
# --------------------------------------------------------------------------- #
RETROFIT_DEFAULTS = {
    "state_path": ".claude/inventory",
    "archetype_confidence": "low",
    "archetype_evidence": [],
    "synthetic_profile": {},
    "prd_tier_target": "standard",
    "ci_cd_applicability": "unknown",
    "spec_strategy": "forward-only",
    "legacy_allowlist": [],
    "retrofit_active": True,
    "spec_patterns": {
        "change": True, "boundary": False, "migration": False,
    },
    "pm": {
        "strategy": "spec_canonical",
        "tool": "none",
        "tool_role_after": "removed",
        "ticket_migration": {
            "convert_now": [], "defer": [], "close": [],
        },
        "hybrid_review_date": None,
    },
    "regulatory_regimes": [],
    "codebase_size_gb": 0,
    "autonomous_modes": {
        "loop_mode_opted_in": False,
        "goal_supervised_mode_opted_in": False,
        "queue_mode_opted_in": False,
        "brownfield_milestones": {
            "rollout_steady_state_spec_test_gate": False,
            "rollout_steady_state_all_hooks": False,
            "touch_based_specs_under_blocking_gates": 0,
            "touch_based_specs_threshold": 10,
            "legacy_allowlist_size_at_retrofit": None,
            "legacy_allowlist_current_size": None,
            "legacy_allowlist_shrink_threshold_pct": 25,
            "mode_selection_ledger_entries": 0,
            "weeks_real_per_task_operation_post_blocking": 0,
        },
    },
    "debt": {"entries": []},
    "inventory_summary": {
        "has_prior_claude": False,
        "has_root_claude_md": False,
        "danger_zone_count": 0,
        "no_test_module_count": 0,
    },
}


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

    # mode: default "bootstrap" preserves byte-identity of every existing
    # config (greenfield-as-of-pre-retrofit-installer cfgs implicitly carry
    # this default). Retrofit configs declare mode: "retrofit" and trigger
    # the retrofit branch below.
    mode = cfg.get("mode", "bootstrap")
    if mode not in MODES:
        errors.append(f"mode must be one of {sorted(MODES)}; got {mode!r}")
        return cfg, errors
    cfg["mode"] = mode

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

    # ---- Retrofit-mode: fill defaults + validate retrofit invariants ----- #
    # Runs only when mode == "retrofit". Greenfield path is byte-identical
    # because (a) nothing above this point reads cfg["retrofit"], (b) the
    # `mode` field is the only addition to greenfield cfg and is not read
    # by any template fn (verified by D2 golden test).
    if mode == "retrofit":
        cfg.setdefault("retrofit", {})
        _deep_default(cfg["retrofit"], RETROFIT_DEFAULTS)
        r = cfg["retrofit"]

        if r["spec_strategy"] not in RETROFIT_SPEC_STRATEGIES:
            errors.append(
                f"retrofit.spec_strategy must be one of "
                f"{sorted(RETROFIT_SPEC_STRATEGIES)}; got "
                f"{r['spec_strategy']!r}")
        if r["pm"]["strategy"] not in RETROFIT_PM_STRATEGIES:
            errors.append(
                f"retrofit.pm.strategy must be one of "
                f"{sorted(RETROFIT_PM_STRATEGIES)}; got "
                f"{r['pm']['strategy']!r}")
        if r["pm"]["tool"] not in RETROFIT_PM_TOOLS:
            errors.append(
                f"retrofit.pm.tool must be one of "
                f"{sorted(RETROFIT_PM_TOOLS)}; got {r['pm']['tool']!r}")
        if r["pm"]["tool_role_after"] not in RETROFIT_PM_TOOL_ROLES_AFTER:
            errors.append(
                f"retrofit.pm.tool_role_after must be one of "
                f"{sorted(RETROFIT_PM_TOOL_ROLES_AFTER)}; got "
                f"{r['pm']['tool_role_after']!r}")
        if r["ci_cd_applicability"] not in RETROFIT_CI_CD_APPLICABILITY:
            errors.append(
                f"retrofit.ci_cd_applicability must be one of "
                f"{sorted(RETROFIT_CI_CD_APPLICABILITY)}; got "
                f"{r['ci_cd_applicability']!r}")
        if r["archetype_confidence"] not in RETROFIT_ARCHETYPE_CONFIDENCES:
            errors.append(
                f"retrofit.archetype_confidence must be one of "
                f"{sorted(RETROFIT_ARCHETYPE_CONFIDENCES)}; got "
                f"{r['archetype_confidence']!r}")

        # B5: the runtime *_enabled flags MUST be false at retrofit time
        # regardless of operator opt-in. The wizard scaffolds but defers.
        # Enforced here because the installer cannot trust a hand-edited cfg
        # to honour the rule on its own. (Opt-in intent lives in
        # cfg["retrofit"]["autonomous_modes"]["*_opted_in"]; enable flags
        # live in cfg["autonomous_modes"] and must stay false.)
        for flag in ("loop_mode_enabled", "goal_supervised_mode_enabled",
                     "queue_mode_enabled"):
            if cfg["autonomous_modes"].get(flag):
                errors.append(
                    f"autonomous_modes.{flag} must be false at retrofit "
                    f"time (RETROFIT v1.6.2 scaffold-but-defer rule). "
                    f"Record opt-in intent in "
                    f"retrofit.autonomous_modes.{flag.replace('_enabled', '_opted_in')} "
                    f"instead; the operator flips *_enabled post-retrofit "
                    f"after the brownfield trust milestone is green.")

        # Round-2 review, Lens 5.1 — structural dual-shape validator. A
        # contributor adding a new field to the wrong half of the schema
        # (e.g. *_enabled nested under retrofit, or *_opted_in /
        # brownfield_milestones top-level) is the failure mode T1 pins
        # in tests; this validator pins it at runtime too. The contract
        # is the inverse of the B5 split.
        _rf_am = r.get("autonomous_modes", {})
        _top_am = cfg.get("autonomous_modes", {})
        _wrong_in_nested = [
            k for k in ("loop_mode_enabled",
                        "goal_supervised_mode_enabled",
                        "queue_mode_enabled",
                        "loop_in_flight", "goal_in_flight",
                        "queue_runs_history")
            if k in _rf_am]
        _wrong_in_top = [
            k for k in ("loop_mode_opted_in",
                        "goal_supervised_mode_opted_in",
                        "queue_mode_opted_in", "brownfield_milestones")
            if k in _top_am]
        for k in _wrong_in_nested:
            errors.append(
                f"retrofit.autonomous_modes.{k} is wrong-shape: "
                f"{k!r} belongs at top-level autonomous_modes (B5 "
                f"dual-shape contract). Nested location is for "
                f"*_opted_in / brownfield_milestones only.")
        for k in _wrong_in_top:
            errors.append(
                f"autonomous_modes.{k} is wrong-shape: {k!r} belongs "
                f"nested under retrofit.autonomous_modes (B5 dual-"
                f"shape contract). Top-level is for *_enabled / "
                f"*_in_flight / queue_runs_history only.")

        # Round-2 review, Lens 1.1 — R8.I prereq parallel to greenfield's
        # queue_mode_enabled requires loop or goal_supervised_mode_enabled
        # (defaults.py line 232 above). Retrofit's opt-in path needs the
        # same gate or queue scaffolding has nothing to dispatch.
        if _rf_am.get("queue_mode_opted_in") and not (
                _rf_am.get("loop_mode_opted_in")
                or _rf_am.get("goal_supervised_mode_opted_in")):
            errors.append(
                "retrofit.autonomous_modes.queue_mode_opted_in requires "
                "at least one of loop_mode_opted_in or "
                "goal_supervised_mode_opted_in (RETROFIT R8.I "
                "prereq — queue dispatches per-task wrappers; with "
                "none scaffolded there is nothing to dispatch).")

        # Round-2 review, Lens 1.1 — wire the drift-detector loop-
        # cooperation hook on opt-in (the greenfield gate at line ~268
        # reads *_enabled, which is pinned false at retrofit time).
        # Same hook serves R8.G and R8.H per RETROFIT.md R8.G step 1.
        if (_rf_am.get("loop_mode_opted_in")
                or _rf_am.get("goal_supervised_mode_opted_in")):
            if "drift-detector-loop-cooperation" not in cfg["_resolved_hooks"]:
                cfg["_resolved_hooks"].append(
                    "drift-detector-loop-cooperation")
        if _rf_am.get("goal_supervised_mode_opted_in"):
            if "iteration-summary-enforcement" not in cfg["_resolved_hooks"]:
                cfg["_resolved_hooks"].append("iteration-summary-enforcement")

        # Round-2 review, Lens 1.3 — R0.7 hybrid_review_date is
        # conditional-required when pm_strategy == "hybrid". RETROFIT.md
        # R0.7 schema says it is null if not Strategy C, present if so.
        # An ISO-format date string is required; basic non-empty check.
        if r["pm"]["strategy"] == "hybrid":
            hrd = r["pm"].get("hybrid_review_date")
            if not hrd or not isinstance(hrd, str):
                errors.append(
                    "retrofit.pm.hybrid_review_date is required when "
                    "retrofit.pm.strategy == 'hybrid' (RETROFIT R0.7 "
                    "Strategy C — the operator-set review date for "
                    "the hybrid arrangement). Set it to an ISO date "
                    "string (YYYY-MM-DD).")

        # Warn-not-fail: migration spec pattern without a non-empty legacy
        # allowlist usually means nothing to strangle.
        cfg["_retrofit_warnings"] = []
        if r["spec_patterns"]["migration"] and not r["legacy_allowlist"]:
            cfg["_retrofit_warnings"].append(
                "retrofit.spec_patterns.migration is true but "
                "retrofit.legacy_allowlist is empty - migration specs "
                "usually presuppose legacy code to strangle. Confirm.")

    return cfg, errors

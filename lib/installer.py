#!/usr/bin/env python3
"""
Deterministic Bootstrap Protocol installer.

Reads a bootstrap.config.yaml (the frozen output of the Bootstrap-Protocol-v2-0-0.md wizard's
decision phases) and emits the complete .claude/ tree. Properties:

  * Deterministic   - identical config in => identical tree out.
  * Idempotent      - re-running never duplicates or corrupts; it converges.
  * Inspectable     - --dry-run prints the plan; --diff shows what would change.
  * Reversible      - every write is recorded in a manifest for clean removal.

This module is intentionally dependency-free (stdlib only) so it can run in any
Claude Code environment without a pip step. A tiny YAML subset parser is
included for the same reason.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

from minyaml import load_yaml          # local stdlib-only YAML subset
from templates import TEMPLATES, HOOK_EVENT_MAP  # all file bodies live here
from defaults import resolve_config    # archetype defaults + validation

MANIFEST = ".claude/.installer-manifest.json"
STATE = ".claude/.bootstrap-state.json"
RETROFIT_STATE = ".claude/.retrofit-state.json"
PROTOCOL_VERSION = "2.7.0"
RETROFIT_PROTOCOL_VERSION = "1.6.2"
# Seam binds floor (SEAM-CONTRACT v2.0.0, claude_code_runtime; unchanged
# against the official changelog 2026-07-18): below 2.1.210 a PreToolUse
# hook timeout is misreported as a user rejection instead of failing
# closed. AC-9-4: startup logs the detected CLI version and warns loudly
# below this floor (or when undetectable); the install itself proceeds -
# the floor binds DISPATCH, not emission.
RUNTIME_FLOOR = "2.1.210"
INSTALLER_VERSION = "1.1.0"

# Exit code for "files were written, but this install does not ENFORCE".
# Distinct from 2 (config validation refused; nothing was written) because the
# operator's next move differs: 2 means fix the config, 3 means the tree on
# disk is live but the gates in it are not wired. 0 is reserved for an install
# whose enforcement was verified.
EXIT_UNENFORCED = 3


# TEL-01 (v2.4.0 fold): `telemetry_export_enabled` is a top-level flag that
# post-dates the frozen defaults.py schema, so resolve_config neither coerces
# nor validates it. minyaml converts only bare `true`/`false` to bool - every
# other YAML-1.1 boolean spelling (`off`, `no`, `"false"`) arrives as a
# NON-EMPTY STRING, and raw truthiness would read those as ENABLED, silently
# inverting an operator's explicit opt-out. Normalize once, here, and fail loud
# on anything unrecognized rather than guessing: a privacy opt-in must never be
# decided by a typo. Both consumers (build_plan's gate and _write_state's
# stamp) route through this, so the emitted doc and the state flag cannot
# disagree.
_TELEMETRY_TRUE = {"true", "yes", "on", "1"}
_TELEMETRY_FALSE = {"false", "no", "off", "0", ""}


def telemetry_enabled(cfg: dict) -> bool:
    """Resolve the TEL-01 opt-in flag to a bool, fail-loud on garbage."""
    raw = cfg.get("telemetry_export_enabled", False)
    if isinstance(raw, bool):
        return raw
    # NB: bool is a subclass of int, so this arm is reached only by a real
    # integer - minyaml renders bare 0/1 as ints, not strings.
    if isinstance(raw, int) and raw in (0, 1):
        return bool(raw)
    if isinstance(raw, str):
        token = raw.strip().strip('"').strip("'").lower()
        if token in _TELEMETRY_TRUE:
            return True
        if token in _TELEMETRY_FALSE:
            return False
    raise ValueError(
        f"telemetry_export_enabled: unrecognized value {raw!r}. Use true or "
        "false (yes/no/on/off/1/0 are accepted). This flag is an opt-in for "
        "an observability export, so the installer refuses to guess what an "
        "unrecognized value meant.")


# DS-01 (v2.5.0): twin of _TELEMETRY_TRUE/_FALSE at installer.py:58. Parallel
# token sets (NOT a shared _BOOL_TRUE/_FALSE): there is no shared bool-token set
# in this repo, and refactoring telemetry's tokens into one would touch the
# telemetry normalizer the full_autonomous golden fixture exercises and risk
# perturbing its digest. Parallel keeps the diff minimal and the golden honest.
_DESIGN_TRUE = {"true", "yes", "on", "1"}
_DESIGN_FALSE = {"false", "no", "off", "0", ""}


def design_steering_enabled(cfg: dict) -> bool:
    """Resolve the DS-01 opt-in flag to a bool, fail-loud on garbage.
    Twin of telemetry_enabled (installer.py:62)."""
    raw = cfg.get("design_steering_enabled", False)
    if isinstance(raw, bool):
        return raw
    # NB: bool is a subclass of int, so this arm is reached only by a real
    # integer - minyaml renders bare 0/1 as ints, not strings.
    if isinstance(raw, int) and raw in (0, 1):
        return bool(raw)
    if isinstance(raw, str):
        token = raw.strip().strip('"').strip("'").lower()
        if token in _DESIGN_TRUE:
            return True
        if token in _DESIGN_FALSE:
            return False
    raise ValueError(
        f"design_steering_enabled: unrecognized value {raw!r}. Use true or "
        "false (yes/no/on/off/1/0 are accepted). This flag is an opt-in for a "
        "design-steering doc, so the installer refuses to guess what an "
        "unrecognized value meant.")


def design_review_skill_enabled(cfg: dict) -> bool:
    """Resolve the DS-01 optional-skill flag to a bool, fail-loud on garbage.
    Twin of telemetry_enabled (installer.py:62); a SECOND decision gated on the
    primary being on (Phase 0 step 6: 'yes to the doc' does not silently install
    the skill). The build_plan gate only consults this when design steering is
    already enabled, so an operator who leaves it absent gets no skill."""
    raw = cfg.get("design_review_skill_enabled", False)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int) and raw in (0, 1):
        return bool(raw)
    if isinstance(raw, str):
        token = raw.strip().strip('"').strip("'").lower()
        if token in _DESIGN_TRUE:
            return True
        if token in _DESIGN_FALSE:
            return False
    raise ValueError(
        f"design_review_skill_enabled: unrecognized value {raw!r}. Use true or "
        "false (yes/no/on/off/1/0 are accepted). This flag is an opt-in for the "
        "advisory design-review skill, so the installer refuses to guess what "
        "an unrecognized value meant.")


# --------------------------------------------------------------------------- #
# Plan construction
# --------------------------------------------------------------------------- #
def build_plan(cfg: dict) -> list[dict]:
    """Return an ordered list of file actions derived purely from cfg.

    Each action: {path, body, mode, kind}. No I/O happens here - the plan is
    a pure function of the config, which is what makes the installer
    deterministic and unit-testable.
    """
    # Forcing function on the emission path: refuse to build a plan while
    # the seam SS7.2 tier sets and HOOK_EVENT_MAP disagree (see the
    # docstring for why this is here, not at import).
    _assert_tier_partition()
    plan: list[dict] = []

    def add(path: str, body: str, *, mode: int = 0o644, kind: str = "file"):
        plan.append({"path": path, "body": body, "mode": mode, "kind": kind})

    arche = cfg["project"]["archetype"]
    flags = cfg["autonomous_modes"]

    # ---- Steering docs (Phases 1-5, 2.5, 2.7) ----------------------------- #
    add(".claude/steering/product.md", TEMPLATES["product"](cfg))
    add(".claude/steering/tech.md", TEMPLATES["tech"](cfg))
    if cfg["deps"]["enabled"]:
        add(".claude/steering/deps.md", TEMPLATES["deps"](cfg))
    if cfg["secrets"]["enabled"]:
        add(".claude/steering/secrets.md", TEMPLATES["secrets"](cfg))
    add(".claude/steering/structure.md", TEMPLATES["structure"](cfg))
    add(".claude/steering/principles.md", TEMPLATES["principles"](cfg))
    if not cfg["project"]["cicd_opt_out"]:
        add(".claude/steering/ci-cd.md", TEMPLATES["cicd"](cfg))
    else:
        add(".claude/steering/ci-cd.md", TEMPLATES["cicd_optout"](cfg))
    add(".claude/steering/tools.md", TEMPLATES["tools"](cfg))
    # GR2-03a (v2.4.0 fold): the assumption ledger is an UNCONDITIONAL steering
    # artifact seeded at bootstrap — lands in .claude/steering/ (never
    # gitignored, so committed by construction). Pure function of cfg; +1 file
    # on every fixture. The surfacing behavior is deferred (see changelog).
    add(".claude/steering/assumption-ledger.md",
        TEMPLATES["assumption_ledger"](cfg))
    # TEL-01 (v2.4.0 fold): opt-in observability doc, emitted ONLY when the
    # operator opted in (Phase 0 decision). Lands in .claude/steering/ (never
    # gitignored -> committed by construction; no gitignore edit). Off by
    # default: the default plan is byte-identical to the pre-TEL-01 baseline.
    # telemetry_enabled() reads defensively (a config lacking the key never
    # KeyErrors) and normalizes YAML boolean spellings fail-loud.
    if telemetry_enabled(cfg):
        add(".claude/steering/telemetry.md", TEMPLATES["telemetry"](cfg))

    # DS-01 (v2.5.0): opt-in design-steering doc, emitted ONLY when the operator
    # opted in (Phase 0 step 6). Lands in .claude/steering/ (never gitignored ->
    # committed by construction, no gitignore edit). Off by default: the default
    # plan is byte-identical to the pre-DS-01 baseline. design_steering_enabled()
    # reads defensively (a config lacking the key never KeyErrors). The optional
    # advisory design-review skill is a SECOND decision, gated on the primary:
    # emitted as a direct add() (NOT via _skills/_commands, which key off
    # workflow.install_skills) so it is governed only by the design flags. The
    # /design-review command is emitted alongside the skill (never alone).
    if design_steering_enabled(cfg):
        add(".claude/steering/design.md", TEMPLATES["design"](cfg))
        if design_review_skill_enabled(cfg):
            add(".claude/skills/design-review/SKILL.md",
                TEMPLATES["design_review_skill"](cfg))
            add(".claude/commands/design-review.md",
                TEMPLATES["design_review_command"](cfg))

    # ---- Hooks (Phase 6) -------------------------------------------------- #
    hook_set = cfg["_resolved_hooks"]            # filled by resolve_config
    for hook_name in hook_set:
        body = TEMPLATES["hook"](hook_name, cfg)
        if body is None:
            continue
        add(f".claude/hooks/{hook_name}.sh", body, mode=0o755, kind="hook")

    add(".claude/hooks/audio-alerts.config", TEMPLATES["audio_config"](cfg))
    add(".claude/settings.json", TEMPLATES["settings_json"](cfg), kind="settings")

    # ---- IC-5 SDK gate module (Milestone B, seam §9) ---------------------- #
    # Emitted alongside the shell suite (which remains the SEV-1 manual
    # path, seam §7.5). Security-critical tier via its own kind (AC-7-6);
    # the retrofit overlay DROPS this entry (retrofit stays shell-era).
    add(".claude/sdk_gates/gates.py", TEMPLATES["sdk_gates"](cfg),
        kind="sdk_gates")

    # ---- Skills, commands, agents (Phase 7) ------------------------------- #
    if cfg["workflow"]["install_skills"]:
        for skill, body in TEMPLATES["skills"](cfg).items():
            add(f".claude/skills/{skill}/SKILL.md", body)
    if cfg["workflow"]["install_commands"]:
        for cmd, body in TEMPLATES["commands"](cfg).items():
            add(f".claude/commands/{cmd}.md", body)
    if cfg["workflow"]["install_agents"]:
        for agent, body in TEMPLATES["agents"](cfg).items():
            add(f".claude/agents/{agent}.md", body)

    # ---- Per-task autonomous wrappers (Phase 9.5 / 9.6) ------------------- #
    # Bootstrap-Protocol-v2-0-0.md Phase 9.5 "What the wizard generates when loop mode is
    # opted in" and Phase 9.6 (goal-supervised) mandate these whenever the
    # *mode* is opted in - independent of queue mode. auto.sh dispatches
    # them, so they must exist for the queue=>loop|goal invariant to hold at
    # the file level, not just logically in resolve_config.
    if flags["loop_mode_enabled"]:
        add(".claude/loop.sh", TEMPLATES["loop_sh"](cfg), mode=0o755)
        add(".claude/loop-config.md", TEMPLATES["loop_config"](cfg))
    if flags["goal_supervised_mode_enabled"]:
        add(".claude/goal-loop.sh", TEMPLATES["goal_loop_sh"](cfg),
            mode=0o755)
        add(".claude/goal-config.md", TEMPLATES["goal_config"](cfg))

    # ---- Queue scaffolding (Phase 9.7) ------------------------------------ #
    if flags["queue_mode_enabled"]:
        add(".claude/queue/backlog.md", TEMPLATES["backlog"](cfg))
        add(".claude/auto-config.md", TEMPLATES["auto_config"](cfg))
        add(".claude/auto.sh", TEMPLATES["auto_sh"](cfg), mode=0o755)

    # ---- Root CLAUDE.md (Phase 8) ----------------------------------------- #
    add("CLAUDE.md", TEMPLATES["claude_md"](cfg))

    # ---- Specs index (Phase 7.6) ------------------------------------------ #
    add(".claude/specs/INDEX.md", TEMPLATES["specs_index"](cfg))
    # GR2-01 (review revision): the canonical progress.md template is emitted
    # as its own INSTALLER-OWNED file rather than embedded in INDEX.md. INDEX.md
    # is the operator-edited spec roster, so the hand-edit guard skips it on
    # every real install — which meant normative content parked inside it could
    # never reach an upgraded workspace, and forcing it through destroyed the
    # roster. Separate file, separate ownership: this one updates cleanly.
    add(".claude/specs/progress-template.md",
        TEMPLATES["progress_template"](cfg))

    # ---- gitignore fragment ----------------------------------------------- #
    add(".claude/.gitignore", TEMPLATES["gitignore"](cfg))

    # ---- IC-2 root-sentinel gitignore managed block [SR-17 decision (a)] -- #
    # The root sentinels /.halt and /.halt-hard only act on the autonomous
    # wrappers, so the PROJECT-ROOT .gitignore block is emitted exactly when
    # at least one wrapper is. This is a deliberate write surface outside
    # .claude/, surfaced in --dry-run / the Phase 0.5 preview via this plan
    # entry; apply_plan gives kind "gitignore_root" merge semantics (create
    # whole file when absent; otherwise manage only the marker-delimited
    # block and never touch or digest-track operator content).
    if (flags["loop_mode_enabled"] or flags["goal_supervised_mode_enabled"]
            or flags["queue_mode_enabled"]):
        add(".gitignore", TEMPLATES["gitignore_root"](cfg),
            kind="gitignore_root")

    # ---- Retrofit overlay (single mode-gated branch, per C1) ------------- #
    # Net AST change in build_plan: this conditional + the helper call.
    # Greenfield cfgs never reach this branch; D2 golden test confirms
    # greenfield output is byte-identical post-edit.
    if cfg.get("mode") == "retrofit":
        plan = _apply_retrofit_overlay(plan, cfg)

    return plan


def _retrofit_wrapper_transform(body: str, enabled_key: str) -> str:
    """Round-3 review (Lens A3 + B2): transform a greenfield autonomous-mode
    wrapper for retrofit-mode use.

    Two transforms, both required for the scaffold-but-defer invariant:

    1. **State filename swap (A3).** Greenfield wrappers reference
       `.bootstrap-state.json`; in retrofit projects the runtime state
       file is `.claude/.retrofit-state.json` (same B5 top-level shape,
       different filename). Without this swap the wrapper would read
       (or fail to find) the wrong file when the operator post-milestone
       flips *_enabled.

    2. **Scaffold-but-defer guard (B2).** RETROFIT R8.G/H/I require
       the wrappers to be present-but-inert at retrofit time; they
       may only run after the operator manually sets *_enabled: true
       post-milestone. We insert a guard that reads the *_enabled
       flag from .retrofit-state.json and refuses to run if absent
       or false. This ALSO solves the opt-out-after-opt-in orphan
       case: a wrapper left on disk after opt-out has *_enabled
       still false → guard refuses → wrapper is inert.

    The transform composes; greenfield body is otherwise unchanged.
    """
    body = body.replace("$PROJ/.claude/.bootstrap-state.json",
                         "$PROJ/.claude/.retrofit-state.json")
    guard = (
        '# Retrofit scaffold-but-defer guard (RETROFIT R8.G/H/I).\n'
        f'# Refuse to run unless {enabled_key}: true in .retrofit-state.json.\n'
        f'# Until the brownfield milestone is met, this script is inert.\n'
        '_RF_STATE="$PROJ/.claude/.retrofit-state.json"\n'
        'if [ ! -r "$_RF_STATE" ]; then\n'
        '  echo "REFUSING: .retrofit-state.json missing; scaffold-but-defer rule." >&2\n'
        '  exit 1\n'
        'fi\n'
        f'if ! grep -q \'"{enabled_key}":[[:space:]]*true\' "$_RF_STATE"; then\n'
        f'  echo "REFUSING: {enabled_key} is not true in .retrofit-state.json." >&2\n'
        '  echo "This is a scaffold-but-defer skeleton (R8.G/H/I). Flip the flag" >&2\n'
        '  echo "post-milestone; the wizard never enables modes at retrofit time." >&2\n'
        '  exit 1\n'
        'fi\n'
    )
    # Insert the guard immediately after the LOG line so PROJ is already
    # defined (set -u would otherwise trip on $PROJ before assignment).
    # The LOG=... line is identical across all three wrappers (per
    # _per_task_wrapper + _auto_sh greenfield templates); the log()
    # function definition that immediately follows differs by escape
    # depth (per_task_wrapper is inside .format() so its backslashes
    # are doubled, auto_sh is not), so we anchor on LOG=... instead.
    anchor = 'LOG="$PROJ/.claude/logs/hooks.log"'
    if anchor in body:
        body = body.replace(anchor, anchor + "\n" + guard, 1)
    else:
        # Defensive fallback (should be unreachable): prepend after the
        # first PROJ assignment so $PROJ is at least defined.
        proj_anchor = 'PROJ="${CLAUDE_PROJECT_DIR:'
        idx = body.find(proj_anchor)
        if idx >= 0:
            line_end = body.find("\n", idx) + 1
            body = body[:line_end] + guard + body[line_end:]
        else:
            # Final fallback: prepend after set -euo pipefail.
            body = body.replace("set -euo pipefail\n",
                                 "set -euo pipefail\n" + guard, 1)
    return body


def _apply_retrofit_overlay(plan: list[dict], cfg: dict) -> list[dict]:
    """Retrofit-mode overlay: REPLACE specific greenfield entries with
    retrofit-flavor bodies (CLAUDE.md, .gitignore, implementer.md,
    reviewer.md) and APPEND retrofit-only artifacts (debt.md, spec-
    strategy.md, workflow-source-of-truth.md, rollout-schedule.md, the
    conditional steering docs, the inventory README pointer, retrofit
    skills + commands, conditional worktree-budget).

    The retrofit-flavor template functions live in lib/templates.py
    behind their own `_retrofit_*` names; this function is the single
    dispatch site per C1. No greenfield template fn is touched."""
    r = cfg["retrofit"]

    # Build a path -> action map for in-place replacement.
    by_path = {a["path"]: a for a in plan}

    # ---- Milestone B (IC-5): DROP the SDK gate module ------------------- #
    # The SDK substrate is greenfield-2.1.0 surface; the retrofit track
    # stays at RETROFIT_PROTOCOL_VERSION (shell-era), and Tessera's seam
    # excludes retrofit entirely (seam §3.2, IG-10). The overlay - the
    # single retrofit dispatch site per C1 - removes the entry rather
    # than emitting an artifact the retrofit contract never declared.
    by_path.pop(".claude/sdk_gates/gates.py", None)

    def replace(path: str, body: str, *, mode: int = 0o644,
                 kind: str = "file"):
        action = {"path": path, "body": body, "mode": mode, "kind": kind}
        by_path[path] = action

    def append(path: str, body: str, *, mode: int = 0o644,
                kind: str = "file"):
        # Only append if not already present (idempotent overlay).
        if path not in by_path:
            by_path[path] = {"path": path, "body": body, "mode": mode,
                              "kind": kind}

    # REPLACE: greenfield-emitted files that need retrofit-flavor bodies.
    replace("CLAUDE.md", TEMPLATES["retrofit_claude_md"](cfg))
    replace(".claude/.gitignore", TEMPLATES["retrofit_gitignore"](cfg))
    if cfg["workflow"]["install_agents"]:
        replace(".claude/agents/implementer.md",
                TEMPLATES["retrofit_implementer_agent"](cfg))
        replace(".claude/agents/reviewer.md",
                TEMPLATES["retrofit_reviewer_agent"](cfg))

    # APPEND: retrofit-only artifacts.
    append(".claude/debt.md", TEMPLATES["retrofit_debt"](cfg))
    append(".claude/steering/spec-strategy.md",
           TEMPLATES["retrofit_spec_strategy"](cfg))
    append(".claude/steering/workflow-source-of-truth.md",
           TEMPLATES["retrofit_workflow_sot"](cfg))
    append(".claude/hooks/rollout-schedule.md",
           TEMPLATES["retrofit_rollout_schedule"](cfg))
    # Per OD-5: installer emits the inventory README; decision layer
    # writes the other 10 inventory files.
    append(".claude/inventory/README.md",
           TEMPLATES["retrofit_inventory_readme"](cfg))

    # CONDITIONAL retrofit-only artifacts.
    if r["spec_patterns"]["boundary"]:
        append(".claude/steering/contracts.md",
               TEMPLATES["retrofit_contracts"](cfg))
    if r["spec_patterns"]["migration"]:
        append(".claude/steering/migration.md",
               TEMPLATES["retrofit_migration"](cfg))
    if r["regulatory_regimes"]:
        append(".claude/steering/compliance.md",
               TEMPLATES["retrofit_compliance"](cfg))
    if r["codebase_size_gb"] and r["codebase_size_gb"] >= 1:
        append(".claude/hooks/worktree-budget.md",
               TEMPLATES["retrofit_worktree_budget"](cfg))

    # APPEND retrofit skills + commands (as new files; greenfield's _skills
    # / _commands are untouched).
    if cfg["workflow"]["install_skills"]:
        for skill, body in TEMPLATES["retrofit_skills"](cfg).items():
            append(f".claude/skills/{skill}/SKILL.md", body)
    if cfg["workflow"]["install_commands"]:
        for cmd, body in TEMPLATES["retrofit_commands"](cfg).items():
            append(f".claude/commands/{cmd}.md", body)

    # ---- R8.G/H/I autonomous-mode scaffolding (Round-2 review, Lens 1.1). #
    # The greenfield gating in build_plan emits these files when top-level
    # *_enabled is true; in retrofit mode *_enabled is pinned false (B5),
    # so the greenfield branch skips them. RETROFIT.md R8.G/H/I requires
    # the scaffolding to be present-but-default-disabled when the operator
    # opted in at R0.5 step 7, so the deterministic-installer contract
    # holds and no second tool invocation is needed post-milestone.
    #
    # The scaffolding bodies are the same guarded fail-safe skeletons the
    # greenfield installer ships (RETROFIT.md R8.G step 1: "Generated as
    # a guarded fail-safe skeleton exactly as BOOTSTRAP ships it"). The
    # claude -p iteration loop is operator-completed per the trust ramp.
    am = r.get("autonomous_modes", {})
    loop_in = bool(am.get("loop_mode_opted_in"))
    goal_in = bool(am.get("goal_supervised_mode_opted_in"))
    queue_in = bool(am.get("queue_mode_opted_in"))

    if loop_in:
        # R8.G — Autonomous Loop Mode
        append(".claude/loop.sh",
               _retrofit_wrapper_transform(TEMPLATES["loop_sh"](cfg),
                                            "loop_mode_enabled"),
               mode=0o755)
        append(".claude/loop-config.md", TEMPLATES["loop_config"](cfg))
    if goal_in:
        # R8.H — Goal-Supervised Mode
        append(".claude/goal-loop.sh",
               _retrofit_wrapper_transform(TEMPLATES["goal_loop_sh"](cfg),
                                            "goal_supervised_mode_enabled"),
               mode=0o755)
        append(".claude/goal-config.md", TEMPLATES["goal_config"](cfg))
        # R8.H step 1 calibration ledger (retrofit-specific seed).
        append("learnings/mode-selection.md",
               TEMPLATES["retrofit_mode_selection_ledger"](cfg))
    if queue_in:
        # R8.I — Autonomous Queue Mode. The R8.I-requires-loop-or-goal
        # gate is enforced upstream in resolve_config's retrofit branch
        # (mirroring the existing top-level *_enabled gate in defaults).
        append(".claude/queue/backlog.md", TEMPLATES["backlog"](cfg))
        append(".claude/auto-config.md", TEMPLATES["auto_config"](cfg))
        append(".claude/auto.sh",
               _retrofit_wrapper_transform(TEMPLATES["auto_sh"](cfg),
                                            "queue_mode_enabled"),
               mode=0o755)

    # ---- IC-2 root-sentinel gitignore managed block (review finding 2) -- #
    # The R8.G/H/I wrappers scaffolded above honour the root /.halt and
    # /.halt-hard sentinels, so the project-root .gitignore managed block
    # must ship whenever any of them does. The greenfield gate in
    # build_plan reads the top-level *_enabled flags, which B5 pins false
    # in retrofit mode - so the overlay (the single retrofit dispatch site
    # per C1) appends the same action for the opt-in case.
    if loop_in or goal_in or queue_in:
        append(".gitignore", TEMPLATES["gitignore_root"](cfg),
               kind="gitignore_root")

    # ---- R3.1 (Lens A1): retrofit-flavor spec-decompose skill ----------- #
    # The retrofit implementer.md prose tells the operator the spec-decompose
    # classifier marks danger-zone / legacy-allowlist files not-eligible by
    # default. Without this template, the classifier doesn't exist; the
    # implementer would skip pin-first discipline trusting a phantom layer.
    # Replace the greenfield SKILL.md whenever any autonomous-mode opt-in
    # is true (it adds the brownfield-eligibility rule to greenfield's
    # 5-criterion test).
    if (loop_in or goal_in or queue_in) \
            and cfg["workflow"]["install_skills"]:
        replace(".claude/skills/spec-decompose/SKILL.md",
                TEMPLATES["retrofit_spec_decompose"](cfg))

    # Rebuild the plan in a deterministic order: original greenfield
    # entries first (in their existing order, with replacements in place),
    # then new retrofit entries (sorted by path for determinism). This
    # preserves apply_plan's per-file ordering for greenfield-shared
    # paths and gives retrofit-only paths a stable position.
    out = []
    seen: set = set()
    for a in plan:
        if a["path"] in by_path:       # overlay-dropped paths are skipped
            out.append(by_path[a["path"]])
        seen.add(a["path"])
    for path in sorted(by_path):
        if path not in seen:
            out.append(by_path[path])
    return out


# --------------------------------------------------------------------------- #
# Apply / diff
# --------------------------------------------------------------------------- #
# IC-7 (seam SS7.2): machine-readable hand-edit tiers. Membership is
# CONTRACT-LEVEL - adding or removing a hook from the security-critical set
# is a seam_version event, never a quiet edit. These lists are the shell-era
# baseline, not a frozen ceiling: the Milestone-B substrate release extends
# the security-critical set with .claude/sdk_gates/gates.py under the seam
# MAJOR (seam SS9). spec-gate-entry is DELIBERATELY non-critical (warn-tier
# by the protocol's own entry-warn/commit-block split).
TIER_SECURITY = "security-critical"
TIER_AUTONOMY = "autonomy-critical"
TIER_NON = "non-critical"
SECURITY_CRITICAL_HOOKS = frozenset({
    "secrets-gate", "spec-gate-commit", "dependency-gate", "test-gate",
    "eval-gate", "tdd-gate", "format-lint-gate",
})
AUTONOMY_CRITICAL_HOOKS = frozenset({
    "drift-detector-loop-cooperation", "iteration-summary-enforcement",
})
# Explicit warn/observability tier. Membership here is a DELIBERATE
# non-critical decision, not a default: the forcing function below refuses
# to import while any emitted hook is missing from all three sets.
NON_CRITICAL_HOOKS = frozenset({
    "spec-gate-entry", "ci-mirror", "cost-log", "drift-detector",
    "task-done-alarm", "decision-required-alarm",
})


def _assert_tier_partition() -> None:
    """Forcing function: the tier sets and templates.HOOK_EVENT_MAP must
    partition exactly. A hook added to (or renamed in) the event map
    without a tier decision here, a tier entry naming no emitted hook, or
    a hook claimed by two tiers each fail loudly - never silently
    defaulting to non-critical. Called at the head of build_plan (every
    emission path), NOT at import: an import-time raise would take down
    `--ic-checks` (whose IC-7 entry exists precisely to REPORT this
    violation as JSON) and `--uninstall`/`--print-config` (which emit
    nothing), turning the diagnostic and the recovery path into casualties
    of the very state they must survive."""
    emitted = set(HOOK_EVENT_MAP)
    tiers = (SECURITY_CRITICAL_HOOKS, AUTONOMY_CRITICAL_HOOKS,
             NON_CRITICAL_HOOKS)
    classified = frozenset().union(*tiers)
    problems = []
    if emitted - classified:
        problems.append(f"emitted hooks with no tier decision: "
                        f"{sorted(emitted - classified)}")
    if classified - emitted:
        problems.append(f"tier entries naming no emitted hook: "
                        f"{sorted(classified - emitted)}")
    if sum(map(len, tiers)) != len(classified):
        problems.append("a hook is claimed by more than one tier")
    if problems:
        raise RuntimeError(
            "hook-tier partition violated (seam SS7.2 linkage): "
            + "; ".join(problems))


def _hook_tier(action: dict) -> str:
    """Tier for a plan action per seam SS7.2. settings.json is a member of
    the security-critical set; every other non-hook manifest entry is
    non-critical (a digest mismatch there is a legitimate L-1 hand-edit)."""
    if action["kind"] == "settings":
        return TIER_SECURITY
    if action["kind"] == "sdk_gates":
        # Seam §9: under the SDK substrate this one file carries every
        # gate; it joins the security-critical set in the same release
        # that emits it (a seam_version event, landed with the substrate-
        # release seam bump - never a silent extension).
        return TIER_SECURITY
    if action["kind"] == "hook":
        name = Path(action["path"]).name
        if name.endswith(".sh"):
            name = name[:-3]
        if name in SECURITY_CRITICAL_HOOKS:
            return TIER_SECURITY
        if name in AUTONOMY_CRITICAL_HOOKS:
            return TIER_AUTONOMY
    return TIER_NON


def _digest(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# --force safety net
# --------------------------------------------------------------------------- #
# Backups are NOT manifest-tracked and `--uninstall` never touches them: they
# are the operator's recovery material, not an installer artifact. They are
# also not covered by the emitted `.claude/.gitignore` - adding a line there
# would move every golden digest, which is a re-baseline decision rather than
# a drive-by, so the directory name is deliberately obvious and the run prints
# where it is.
BACKUP_DIR = ".claude/.installer-backups"


def _is_operator_content(known: dict | None, on_disk: str) -> bool:
    """Is the file on disk something the installer did not author?

    Three ways, all of which mean "overwriting this destroys someone's work":
      1. UNTRACKED - the manifest has never recorded this path, yet a
         differing file is there, so we did not write it. This is the upgrade
         case (a version that adds a planned path meeting a workspace where
         the operator hand-created that artifact).
      2. EDITED SINCE - digest drift against what we wrote.
      3. ALREADY SKIPPED ONCE - a skip records the OPERATOR's digest, which on
         the next run would otherwise read as "we wrote that" and fall through
         to overwrite, protecting the edit exactly once.
    A co-owned entry (settings.json merge, gitignore block) carries no
    whole-file `digest`, so it lands here too - correctly, since most of that
    file is theirs.
    """
    return (known is None
            or known.get("digest") != on_disk
            or known.get("state") == "skipped-local-edit")


def _backup_root(root: Path, manifest: dict) -> Path:
    """One directory per run, named for the run. Filesystem-safe (no colons)
    so the same tree works on Windows."""
    stamp = manifest["generated_at"].split(".")[0].split("+")[0]
    return root / BACKUP_DIR / (stamp.replace(":", "").replace("-", "") + "Z")


def _save_forced_copy(bak_root: Path, root: Path, rel: str, text: str,
                      *, dry: bool) -> str:
    """Copy the operator's version aside before --force overwrites it.
    Returns the project-relative backup path (for the message)."""
    dest = bak_root / rel
    # Two --force runs inside the same second share a directory (the name is
    # the run timestamp). Never let the second overwrite the first one's
    # copy: a backup that can be silently clobbered is not a backup. The
    # uniquifier runs in --dry-run too, so the previewed path is the one a
    # real run would use.
    n = 1
    while dest.exists():
        dest = bak_root / f"{rel}.{n}"
        n += 1
    if not dry:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
    return str(dest.relative_to(root))


def _skip_reason(untracked: bool, no_manifest: bool) -> str:
    """Why a planned path was left alone — said accurately.

    [round-6 F6] "pre-existing and not installer-generated" is a claim about
    provenance, and on a tree with NO manifest at all the installer has no
    basis for it: the manifest is gitignored, so a fresh clone carries every
    file this installer wrote and no record that it wrote them. Telling the
    operator their stale artifact is content they authored is what made
    `--force` — whose warning says it destroys what you put there — read as
    the wrong move when it was the only one on offer.
    """
    if not untracked:
        return "locally modified"
    if no_manifest:
        return ("this tree has no installer manifest, so this run cannot "
                "tell your work from an earlier install's")
    return "pre-existing and not installer-generated"


def _classify(root: Path, action: dict) -> str:
    target = root / action["path"]
    if not target.exists():
        return "create"
    if target.read_text() == action["body"]:
        return "unchanged"
    return "update"


def apply_plan(root: Path, plan: list[dict], cfg: dict, *,
               dry: bool, force: bool, adopt: bool = False) -> dict:
    manifest = {
        "installer_version": INSTALLER_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }
    summary = {"create": 0, "update": 0, "unchanged": 0, "skipped": 0,
               "removed": 0,
               # [round-6 F6] Files --adopt claimed without writing.
               "adopted": 0,
               # Whether this tree had NO manifest at all, which changes what
               # a skip is allowed to claim about provenance (_skip_reason)
               # and which remedy the run should point at.
               "no_manifest": False,
               # Paths whose tier is security-critical and which this run
               # DECLINED to write. `_hook_tier` already computes that tier
               # and the manifest already records it; before this key existed
               # nothing read it back, so a run that installed no enforcement
               # printed one SKIP line among ~60 on stdout and exited 0.
               "skipped_security": [],
               # Project-relative paths of operator content --force displaced.
               # [round-7] Planned paths that were a SYMLINK and are now a
               # regular file. A mid-transcript line is not a signal - a skip
               # buried on stdout line 29 of 60 is exactly how the original
               # unenforced-tree defect went unnoticed - so these are also
               # summarised at the end of the run.
               "symlinks_replaced": [],
               "backups": []}

    prev = _load_manifest(root)
    summary["no_manifest"] = prev is None
    prev_files = {f["path"]: f for f in prev.get("files", [])} if prev else {}
    planned_paths = {a["path"] for a in plan}
    bak_root = _backup_root(root, manifest)

    for action in plan:
        # IC-2 [SR-17 decision (a)]: the project-root .gitignore is co-owned
        # with the operator - managed-block merge semantics, never the
        # whole-file overwrite/skip logic below.
        if action["kind"] == "gitignore_root":
            _apply_root_gitignore(root, action, manifest, summary, dry=dry)
            continue

        # settings.json is co-owned the same way: the installer owns the
        # `hooks` key, the operator owns everything else. Whole-file
        # overwrite/skip is wrong for it in both directions.
        if action["kind"] == "settings":
            _apply_settings_json(root, action, manifest, summary, prev_files,
                                 bak_root, dry=dry, force=force)
            # settings.json is co-owned, so it MERGES rather than skipping and
            # never reaches the state --adopt exists to break out of.
            continue

        verdict = _classify(root, action)
        target = root / action["path"]

        # Don't clobber operator content unless --force, but DO overwrite files
        # we generated last time (tracked in the manifest). Three ways a file
        # at a planned path can be operator-owned:
        #
        #  1. UNTRACKED (known is None). The manifest has never recorded this
        #     path, yet a differing file is already on disk - so the installer
        #     did not write it. This is the upgrade case: a version that adds a
        #     new planned path (GR2-03a's assumption-ledger.md, TEL-01's
        #     telemetry.md) meeting a workspace where the operator hand-created
        #     that artifact from the doc-first protocol release. Overwriting
        #     silently would destroy content the installer never authored, and
        #     the emitted ledger's own header promises it will not.
        #  2. EDITED SINCE (digest drift against what we wrote).
        #  3. ALREADY SKIPPED ONCE. A skip records the OPERATOR's digest, which
        #     on the next run would otherwise read as "we wrote that" and fall
        #     through to overwrite - protecting the edit exactly once and
        #     clobbering it on the following run. The state marker keeps
        #     operator ownership sticky until they --force or revert (a revert
        #     to our bytes classifies "unchanged" and never reaches here).
        note = ""
        if verdict == "update":
            known = prev_files.get(action["path"])
            disk_text = target.read_text()
            on_disk = _digest(disk_text)
            untracked = known is None
            if _is_operator_content(known, on_disk):
                if force:
                    # --force is the documented escape hatch, so it proceeds -
                    # but it is destroying content the installer did not
                    # author, and doing that irrecoverably is not a property
                    # any of the four in the module docstring claims.
                    saved = _save_forced_copy(bak_root, root, action["path"],
                                              disk_text, dry=dry)
                    summary["backups"].append(saved)
                    note = f"  (forced; previous version saved to {saved})"
                elif adopt:
                    # [round-6 F6] The non-destructive escape. The manifest is
                    # gitignored, so a clone carries the whole tree and none
                    # of its provenance; every file this installer wrote then
                    # reads as the operator's, and a config change makes the
                    # skip permanent at rc=3 with --force the only way out -
                    # while --force's own warning tells them they are
                    # destroying work that, here, is a stale artifact of an
                    # earlier install. --adopt lets them say so. It records
                    # the file as ours and WRITES NOTHING; the next ordinary
                    # run sees a matching digest and updates it normally.
                    summary["adopted"] += 1
                    print(f"  ADOPT  {action['path']}  (recorded as "
                          f"installer-owned; nothing written)")
                    manifest["files"].append(
                        {"path": action["path"], "digest": on_disk,
                         "mode": oct(action["mode"]), "kind": action["kind"],
                         "tier": _hook_tier(action)})
                    continue
                else:
                    summary["skipped"] += 1
                    reason = _skip_reason(untracked, prev is None)
                    print(f"  SKIP   {action['path']}  ({reason}; "
                          f"use --force to overwrite)")
                    tier = _hook_tier(action)
                    if tier == TIER_SECURITY:
                        summary["skipped_security"].append(
                            {"path": action["path"], "reason": reason})
                    manifest["files"].append(
                        {"path": action["path"], "digest": on_disk,
                         "state": "skipped-local-edit",
                         "tier": tier})
                    continue

        summary[verdict] += 1
        tag = {"create": "CREATE", "update": "UPDATE",
               "unchanged": "  ok  "}[verdict]

        # [round-7] A planned path may be a SYMLINK the operator put there -
        # steering docs or hooks kept in a shared dotfiles repo, say. The write
        # below is `os.replace`, so it swaps the LINK for a regular file rather
        # than writing through it: the link target keeps its bytes but silently
        # stops being used, at rc=0, with no backup and no mention. Not writing
        # through is the right half (it is what `settings.json` declines in
        # order to avoid, one project's `$CLAUDE_PROJECT_DIR/...` reaching every
        # project that shares the file). Saying nothing is the wrong half.
        #
        # Reported rather than declined: whether a symlink at a planned path
        # should BLOCK the install is a per-kind judgement the owner has taken
        # for `settings.json` only, and inventing it here for every path would
        # decide it by drive-by. Announce it, record it, let them choose.
        link_to = None
        if verdict != "unchanged" and target.is_symlink():
            link_to = os.readlink(target)
            summary["symlinks_replaced"].append(
                {"path": action["path"], "target": link_to})
            note += (f"  ({'is' if dry else 'was'} a symlink to {link_to}; "
                     f"{'would be' if dry else 'has been'} replaced by a "
                     f"regular file, so that path "
                     f"{'would no longer be' if dry else 'is no longer'} "
                     f"used)")

        print(f"  {tag} {action['path']}{note}")

        if not dry and verdict != "unchanged":
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_text(action["body"])
            tmp.chmod(action["mode"])
            os.replace(tmp, target)        # atomic rename
        elif not dry and verdict == "unchanged":
            # still normalise mode (e.g. exec bit) in case it drifted
            if stat.S_IMODE(target.stat().st_mode) != action["mode"]:
                target.chmod(action["mode"])

        row = {
            "path": action["path"],
            "digest": _digest(action["body"]),
            "mode": oct(action["mode"]),
            "kind": action["kind"],
            "tier": _hook_tier(action),
        }
        if link_to is not None:
            # Recorded so the operator can find what the run displaced after
            # the transcript is gone. `--uninstall` deletes the regular file we
            # wrote and does NOT restore the link: re-linking is theirs to do,
            # and this is the only place that still names the old target.
            row["replaced_symlink"] = link_to
        manifest["files"].append(row)

    # Stale-file cleanup: a re-apply whose plan no longer includes a path
    # this installer previously created removes it from disk (the retrofit
    # overlay dropping .claude/sdk_gates/gates.py is the first such case).
    # Without this the dropped file lingers on disk while leaving the
    # manifest - digest surveillance on a security-critical file is
    # silently lost and --uninstall (manifest-driven) can never reach it.
    # A hand-edited stale file (digest drift) is preserved and reported,
    # never silently deleted (L-1 contract); the co-owned root .gitignore
    # is managed by its own block logic and never file-deleted here.
    # --dry-run PREVIEWS the removals (prints + counts them) without
    # unlinking, so the preview is faithful for exactly the destructive
    # case this cleanup introduced.
    for path, known in prev_files.items():
        if path in planned_paths or known.get("kind") == "gitignore_root":
            continue
        target = root / path
        if not target.exists():
            continue
        try:
            on_disk = _digest(target.read_text())
        except OSError:
            on_disk = None
        if on_disk is not None and known.get("digest") == on_disk \
                and known.get("state") != "skipped-local-edit":
            if not dry:
                target.unlink()
            summary["removed"] += 1
            tag = "REMOVE (dry run)" if dry else "REMOVE"
            print(f"  {tag} {path}  (dropped from plan on re-apply)")
        else:
            print(f"  KEEP   {path}  (dropped from plan but locally "
                  f"modified; left in place)", file=sys.stderr)

    # If the SDK gate module is not being emitted this run (retrofit
    # overlay drop, or a shell reconfigure) but a greenfield state file
    # still advertises "sdk-callable", reconcile it to "shell": the module
    # that field refers to is gone, and a consumer keying dispatch off the
    # state must not believe the SDK substrate is active.
    if not dry and ".claude/sdk_gates/gates.py" not in planned_paths:
        _reconcile_orphaned_substrate(root)

    if not dry:
        # D6 / C1: single cfg["mode"] dispatch at the state-write site.
        # _write_state is AST-byte-identical; _write_retrofit_state is a
        # sibling. Greenfield path is point-equivalent to the prior code.
        if cfg.get("mode") == "retrofit":
            _write_retrofit_state(root, cfg, manifest)
        else:
            _write_state(root, cfg, manifest)
        (root / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")

    return summary


# --------------------------------------------------------------------------- #
# .claude/settings.json - co-owned, managed by key rather than by file
# --------------------------------------------------------------------------- #
# The TOP-LEVEL keys templates._settings_json emits that this installer owns
# OUTRIGHT. Everything else belongs to the operator and is preserved
# byte-for-byte.
#
# `hooks` and `permissions.deny` are deliberately NOT here. Both are shared:
# an operator may register hooks of their own and write deny rules of their
# own, so we contribute ENTRIES to each and own only what we actually ADDED -
# tracked per-install in the manifest (`owned_hooks`, `owned_deny`,
# `displaced_keys`) so a later run can retire ours without touching theirs.
# Owning `hooks` wholesale would silently delete an operator's own hook, which
# is the same class of harm this whole change exists to remove.
#
# Two corrections from round 6, both of that same class: ownership of a hook
# is per SITE (event, matcher, command), because the operator may register one
# of our scripts somewhere we do not; and a deny rule or owned key the
# operator wrote FIRST is never claimed, because claiming it meant deleting it
# later on their behalf.
#
# tests/test_wiring_verification.py asserts that every top-level key our own
# emission produces is claimed here or is one of the two shared keys, so a key
# added to _settings_json without a co-ownership decision fails loudly instead
# of silently becoming operator-owned and never updated again.
_SETTINGS_OWNED_KEYS = ("$schema", "_generatedBy", "_note_mcp")
_SETTINGS_SHARED_KEYS = ("hooks", "permissions")


def _settings_unmergeable_reason(theirs: dict) -> str | None:
    """Why the operator's settings.json cannot accept our entries, or None if
    it can.

    We refuse exactly the shapes where merging would mean destroying or
    inventing meaning for operator content: a `permissions` that is not an
    object, a `permissions.deny` that is not a list, a `hooks` that is not an
    object, or an event whose value is not a list of groups. Declining and
    saying so beats either alternative.

    The REASON is returned rather than a bool because every refusal used to be
    reported as a `permissions` problem - including files carrying no
    `permissions` key at all (round-6 F4). A misdirected diagnosis costs real
    work here: the only remedy the message offers is --force, which replaces
    the whole file.
    """
    perms = theirs.get("permissions")
    if perms is not None and not isinstance(perms, dict):
        return (f"existing settings.json has a `permissions` key that is a "
                f"{type(perms).__name__}, not an object")
    if isinstance(perms, dict):
        # `deny` is the one key we WRITE INTO. A non-list there cannot be
        # unioned, and coercing it to [] would silently delete an operator's
        # rule - the exact failure this whole change exists to remove, so it
        # is a refusal, not a coercion.
        deny = perms.get("deny")
        if deny is not None and not isinstance(deny, list):
            return (f"existing settings.json has a `permissions.deny` that is "
                    f"a {type(deny).__name__}, not a list")
    hooks = theirs.get("hooks")
    if hooks is None:
        return None
    if not isinstance(hooks, dict):
        return (f"existing settings.json has a `hooks` key that is a "
                f"{type(hooks).__name__}, not an object")
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            return (f"existing settings.json has `hooks.{event}` as a "
                    f"{type(groups).__name__}, not a list of hook groups")
    return None


def _settings_mergeable(theirs: dict) -> bool:
    """Can the operator's settings.json accept our entries without guessing?"""
    return _settings_unmergeable_reason(theirs) is None


def _hook_sites(hooks: dict) -> list[list]:
    """Every registration SITE in a well-formed `hooks` mapping (ours), as
    `[event, matcher, command]`. A missing `matcher` key reads as None, which
    is how our own no-matcher groups are emitted.

    Ownership is per SITE, not per command. The same script may legitimately
    be registered by US under the matcher we emit AND by the OPERATOR under
    one we do not - keying on the command alone deleted the operator's
    registration of our own `secrets-gate.sh` under `SessionStart` and under
    `PreToolUse`/`WebFetch`, at rc=0, beneath a line reading "operator
    settings untouched" (round-6 F2). Lists rather than tuples because this
    round-trips through the manifest as JSON.
    """
    out: list[list] = []
    for event, groups in hooks.items():
        for grp in groups:
            matcher = grp.get("matcher")
            for entry in grp.get("hooks", []):
                cmd = entry.get("command")
                if isinstance(cmd, str):
                    out.append([event, matcher, cmd])
    return out


def _split_owned_hooks(prev_owned: list) -> tuple[set, set]:
    """Read a manifest `owned_hooks` in either shape: the site triples this
    version records, or the bare command strings written before ownership
    became site-keyed. Returns (sites, legacy commands).

    The manifest is a file on the operator's disk and may have been
    hand-edited, so every element is type-checked before it reaches a set: a
    record carrying an unhashable matcher used to raise TypeError out of
    `apply_plan` and abort the install mid-tree. A record that does not
    describe a site we could recognise is ignored, which degrades to "we own
    nothing there" - the same conservative direction as a missing manifest.
    """
    sites, legacy = set(), set()
    for item in prev_owned or []:
        if isinstance(item, str):
            legacy.add(item)
        elif (isinstance(item, (list, tuple)) and len(item) == 3
                and isinstance(item[0], str) and isinstance(item[2], str)
                and (item[1] is None or isinstance(item[1], str))):
            sites.add(tuple(item))
    return sites, legacy


def _is_ours_here(event: str, matcher, entry, sites: set,
                  legacy_cmds: set) -> bool:
    """Is this registration entry one the installer placed?

    Every argument but `event` comes from the operator's settings.json and may
    be any JSON at all. A `matcher` that is a list or an object is
    UNHASHABLE, and building `(event, matcher, command)` against a set raised
    TypeError straight out of `apply_plan`: the install aborted after 22 of 58
    files with every hook script on disk and none of them registered, and
    `--uninstall` aborted outright so the tree could not be removed at all.
    `_split_owned_hooks` already type-checks this same triple arriving from the
    manifest - this is the other end of it, arriving from their file.

    We only ever emit a string `command` under a string-or-absent `matcher`,
    so a site we cannot key is by construction not ours: it is left alone,
    which is what `_merge_hooks` already promises for anything it cannot
    parse. The legacy command match is deliberately NOT gated on the matcher -
    a pre-site manifest names a bare command and cannot say where we put it.
    """
    if not isinstance(entry, dict):
        return False
    cmd = entry.get("command")
    if not isinstance(cmd, str):
        return False
    if cmd in legacy_cmds:
        return True
    if matcher is not None and not isinstance(matcher, str):
        return False
    return (event, matcher, cmd) in sites


def _settings_contribution(ours: dict) -> tuple[list, list]:
    """What this emission contributes to a co-owned settings.json:
    (deny rules, hook registration sites).

    Recorded in the manifest on EVERY write path, including the wholesale
    one. Without it, the first merge after a wholesale write has no record of
    which registrations were ours and treats all of them as the operator's -
    so a hook dropped from the plan stays registered forever, pointing at a
    file the same run deletes.
    """
    deny = list((ours.get("permissions") or {}).get("deny") or [])
    return deny, _hook_sites(ours.get("hooks") or {})


# Our own `_generatedBy` carries the protocol version, so it CHANGES between
# releases. An equality test against this run's emission would read the
# previous version's value as the operator's and hand it back at
# `--uninstall`, which is installer residue. Match the generator name instead.
_GENERATED_BY_MARKER = "bootstrap-installer"


def _carried_displaced(known: dict | None) -> dict | None:
    """A displaced-keys record from a previous run, or None when there is none
    to carry.

    Absence and `{}` are different answers and the difference is load-bearing:
    `{}` is a decision some earlier run made ("they had none of these keys"),
    absence means no run has decided yet and one must be DERIVED.
    """
    if known is not None and "displaced_keys" in known:
        return dict(known["displaced_keys"] or {})
    return None


def _is_our_own_value(key: str, value, ours: dict) -> bool:
    """Is this top-level value our own output rather than the operator's?"""
    if value == ours.get(key):
        return True
    # `_generatedBy` is version-stamped, so an earlier install's value differs
    # from this run's and would otherwise be claimed as the operator's.
    return (key == "_generatedBy" and isinstance(value, str)
            and value.startswith(_GENERATED_BY_MARKER))


def _displaced_owned_keys(ours: dict, theirs: dict,
                          known: dict | None) -> dict:
    """The operator's values for the top-level keys we take over, recorded so
    `--uninstall` hands them back instead of deleting them.

    Decided ONCE, on the first run that writes this path, and carried forward
    unchanged after that: on every later run `theirs` already holds OUR value,
    so re-deriving it unconditionally would record our own emission as the
    operator's.

    Deriving is therefore only correct for a file this installer has NEVER
    written, which is why every write path now records a value - see
    `_tracked` and `_decline` in `_apply_settings_json`. The previous version
    instead used "the manifest row carries a whole-file digest" as a proxy for
    "we owned it wholesale, so nothing was displaced". That proxy was false in
    precisely the cases it fired: this function is reached only from the MERGE
    branch, and the merge branch is reached only when the file on disk is NOT
    ours wholesale. A decline records the OPERATOR's digest under
    `skipped-local-edit`, so a settings.json we had refused to touch read back
    as one we owned outright - every top-level key in it was dropped from the
    record and then DELETED by `--uninstall`, which is the round-6 F1 harm
    coming back through the door round 6 opened.

    What remains is the genuinely record-less case: a manifest lost with a
    fresh clone, or one written before this key existed. There the value is
    derived, excluding any key still holding our own output, which is
    indistinguishable from our previous write. The residual runs toward
    dropping one key of theirs, never toward leaving one of ours behind.
    """
    carried = _carried_displaced(known)
    if carried is not None:
        return carried
    return {k: theirs[k] for k in _SETTINGS_OWNED_KEYS
            if k in theirs and not _is_our_own_value(k, theirs[k], ours)}


def _merge_hooks(ours: dict, theirs: dict,
                 prev_owned: list) -> tuple[dict, list]:
    """Merge hook registrations by SITE identity - (event, matcher, command) -
    rather than by replacing the `hooks` key. Returns (merged, the sites this
    run contributed).

    Groups and entries we cannot parse are passed through untouched: an
    operator's malformed-to-us registration is still theirs, and dropping it
    would be the data loss this function exists to avoid.

    Keying on the COMMAND alone was round-6 F2: it dropped every registration
    of our scripts anywhere in the file and re-added them only at the sites we
    emit, so an operator who had deliberately widened one of our gates lost
    that widening silently. Residual, and narrow: a registration the operator
    wrote at exactly the site we emit is indistinguishable from ours and is
    still treated as ours.
    """
    ours_sites = _hook_sites(ours)
    prev_sites, legacy_cmds = _split_owned_hooks(prev_owned)
    ours_cmds = {c for _, _, c in ours_sites}
    drop_sites = prev_sites | {tuple(s) for s in ours_sites}
    # A manifest written before ownership became site-keyed names a bare
    # command and cannot say where we put it. Retire one only when our
    # emission no longer carries it at all - its file is deleted this run, so
    # a surviving registration would dangle at rc=127. While we still emit it,
    # site matching covers our own copy and a registration anywhere else is
    # the operator's.
    drop_cmds = {c for c in legacy_cmds if c not in ours_cmds}

    merged: dict = {}
    for event, groups in theirs.items():
        kept_groups = []
        for grp in groups:
            if not isinstance(grp, dict) \
                    or not isinstance(grp.get("hooks"), list):
                kept_groups.append(grp)            # opaque; leave it alone
                continue
            matcher = grp.get("matcher")
            kept = [e for e in grp["hooks"]
                    if not _is_ours_here(event, matcher, e,
                                         drop_sites, drop_cmds)]
            if kept:
                kept_groups.append(dict(grp, hooks=kept))
        if kept_groups:
            merged[event] = kept_groups

    for event, groups in ours.items():
        bucket = merged.setdefault(event, [])
        for grp in groups:
            match = next((g for g in bucket
                          if isinstance(g, dict)
                          and g.get("matcher") == grp.get("matcher")
                          and isinstance(g.get("hooks"), list)), None)
            if match is None:
                bucket.append(dict(grp, hooks=list(grp["hooks"])))
            else:
                match["hooks"].extend(grp["hooks"])
    return merged, ours_sites


def _merge_settings(ours: dict, theirs: dict, prev_owned_deny: list,
                    prev_owned_hooks: list) -> tuple[dict, list, list]:
    """Overlay the installer's contribution onto the operator's `theirs`.
    Returns (merged, deny rules ADDED by this run, hook sites contributed).

    Ordering is chosen for IDEMPOTENCE: keys already present keep their
    position (dict assignment does not move them) and ours append only when
    absent, so merging our output into itself is a fixed point and a re-apply
    reports `ok` rather than churning the digest every run.

    `permissions.deny` is a union, never an overwrite - a deny rule is
    strictly restrictive, so contributing one can never fail open. Rules we
    contributed on a PREVIOUS run are dropped before the union, which is what
    lets a shrinking `never_read_paths` actually shrink. When the manifest is
    absent (a fresh clone) `prev_owned_deny` is empty and the union simply
    keeps everything - the degradation is a stale, visible deny rule, never a
    missing one.

    What is reported as CONTRIBUTED excludes anything already in their file:
    ownership is what this run ADDED, not what it emitted, so a rule or a
    registration the operator wrote first is never retired on our behalf.
    """
    merged = dict(theirs)
    for key in _SETTINGS_OWNED_KEYS:
        if key in ours:
            merged[key] = ours[key]
        else:
            merged.pop(key, None)

    their_hooks = theirs.get("hooks")
    merged_hooks, owned_hooks = _merge_hooks(
        ours.get("hooks") or {},
        their_hooks if isinstance(their_hooks, dict) else {},
        prev_owned_hooks)
    if merged_hooks:
        merged["hooks"] = merged_hooks
    else:
        merged.pop("hooks", None)

    ours_perms = ours.get("permissions") or {}
    ours_deny = list(ours_perms.get("deny") or [])

    their_perms = theirs.get("permissions")
    new_perms = dict(their_perms) if isinstance(their_perms, dict) else {}
    their_deny = new_perms.get("deny")
    their_deny = their_deny if isinstance(their_deny, list) else []

    # Rules we contributed on a PREVIOUS run are ours to retire. Everything
    # else already in their list is THEIRS - including rules this emission
    # happens to produce as well. Claiming those was round-6 F1: an operator's
    # own `Read(.env*)` was recorded as ours and then deleted, both by
    # --uninstall and by the next run that narrowed never_read_paths, at rc=0
    # beneath "operator settings untouched".
    theirs_own = [r for r in their_deny if r not in prev_owned_deny]
    owned_deny = [r for r in ours_deny if r not in theirs_own]

    # Their rules keep their positions and ours append after: a rule we both
    # carry stays where THEY put it, so an install followed by an uninstall
    # returns the file byte-for-byte rather than merely set-equal. In the
    # no-collision case this is the same list the union always produced.
    deny = theirs_own + owned_deny
    if deny:
        new_perms["deny"] = deny
    else:
        new_perms.pop("deny", None)
    if new_perms:
        merged["permissions"] = new_perms
    else:
        merged.pop("permissions", None)
    return merged, owned_deny, owned_hooks


def _apply_settings_json(root: Path, action: dict, manifest: dict,
                         summary: dict, prev_files: dict, bak_root: Path, *,
                         dry: bool, force: bool) -> None:
    """Install the hook wiring WITHOUT clobbering an operator's settings.

    settings.json is co-owned in exactly the way the project-root .gitignore
    is, and for the same reason - so it gets the same treatment, by key
    instead of by marker block. The whole-file skip it used to receive was
    uniquely destructive here: this is the ONLY registration site for the
    shell substrate, so declining to write it disabled every gate at once
    while the hook bodies stayed on disk and still exited 2 when invoked by
    hand. A skipped doc costs you that doc; a skipped settings.json cost you
    the entire enforcement layer, silently, at rc=0.

    Cases, in order:
      * absent            - write our body verbatim (byte-identical to the
                            pre-merge installer, so goldens do not move).
      * already ours      - nothing to do.
      * --force           - replace wholesale; the documented escape hatch
                            for a file too broken to merge.
      * ours, unmodified  - plain overwrite, as before.
      * anything else     - MERGE our keys in, preserve theirs.
      * unmergeable       - decline and say so loudly (see EXIT_UNENFORCED).
    """
    target = root / action["path"]
    body = action["body"]
    ours = json.loads(body)          # our own emission; always valid JSON

    def _write(text: str) -> None:
        # Co-ownership extends to metadata: preserve the operator's mode on a
        # file that already exists (mirrors _apply_root_gitignore).
        mode = (stat.S_IMODE(target.stat().st_mode) if target.exists()
                else action["mode"])
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(text)
        tmp.chmod(mode)
        os.replace(tmp, target)

    _own_deny, _own_hooks = _settings_contribution(ours)
    known = prev_files.get(action["path"])
    carried = _carried_displaced(known)

    def _tracked(displaced: dict) -> dict:
        """The manifest row for a path we write WHOLESALE.

        `displaced_keys` is recorded here too, not only on the merge: a row
        carrying no record at all is exactly what tells a later run to DERIVE
        one, and deriving is only correct on a file this installer has never
        written. Without it, `--force` (or any wholesale write) over an
        operator's file, followed by an operator edit, re-entered the merge
        with nothing to carry and re-derived from a file that was by then
        mostly ours - dropping their keys, which `--uninstall` then deleted.
        """
        return {
            "path": action["path"],
            "digest": _digest(body),
            "mode": oct(action["mode"]),
            "kind": action["kind"],
            # Recorded even when we own the whole file, so the FIRST merge
            # after a wholesale write knows which registrations were ours to
            # retire.
            "owned_deny": _own_deny,
            "owned_hooks": _own_hooks,
            "displaced_keys": displaced,
            "tier": TIER_SECURITY,
        }

    def _decline(why: str, digest: str) -> None:
        summary["skipped"] += 1
        print(f"  SKIP   {action['path']}  ({why}; use --force to overwrite)")
        summary["skipped_security"].append(
            {"path": action["path"], "reason": why})
        row = {"path": action["path"], "digest": digest,
               "state": "skipped-local-edit", "kind": action["kind"],
               "tier": TIER_SECURITY}
        # Carry a record forward, but never INVENT one. This run wrote
        # nothing, so on a first-run decline nothing has been displaced yet
        # and the next mergeable run must derive from a file that is still
        # wholly theirs. Recording `{}` here instead claimed the opposite and
        # cost the operator every top-level key they owned.
        if carried is not None:
            row["displaced_keys"] = carried
        manifest["files"].append(row)

    # [round-6 F5] A symlinked settings.json has no good automatic answer, so
    # it gets neither guess. Replacing it (what this did) destroys the link
    # and orphans its target. Writing THROUGH it is worse: a settings.json
    # shared between projects would gain `$CLAUDE_PROJECT_DIR/...` hook
    # commands that resolve per-project, so every OTHER project sharing that
    # file runs scripts it does not have and gets rc=127 on every matching
    # tool call. Decline, name the target, and let the operator choose.
    # Checked before `exists()`, which follows the link.
    if target.is_symlink() and not force:
        try:
            here = _digest(target.read_text())
        except OSError:                      # dangling link; nothing to hash
            here = ""
        _decline(f"existing settings.json is a symlink to "
                 f"{os.readlink(target)}, which this installer will neither "
                 f"orphan nor edit on behalf of every project sharing it",
                 here)
        return

    if not target.exists():
        summary["create"] += 1
        print(f"  CREATE {action['path']}")
        if not dry:
            _write(body)
        # There was no file, so this write displaced nothing - a decision, and
        # the honest one, rather than an absent record a later run would read
        # as licence to derive from our own emission.
        manifest["files"].append(_tracked({}))
        return

    text = target.read_text()
    if text == body:
        summary["unchanged"] += 1
        print(f"    ok   {action['path']}")
        manifest["files"].append(
            _tracked(carried if carried is not None else {}))
        return

    theirs_here = _is_operator_content(known, _digest(text))
    if not theirs_here or force:
        note = ""
        if theirs_here:
            # --force on a co-owned file is the most destructive thing this
            # installer does: everything outside our keys goes. Recoverably.
            saved = _save_forced_copy(bak_root, root, action["path"], text,
                                      dry=dry)
            summary["backups"].append(saved)
            note = f"  (forced; previous version saved to {saved})"
        summary["update"] += 1
        print(f"  UPDATE {action['path']}{note}")
        if not dry:
            _write(body)
        # Read what this wholesale write is about to displace while the file
        # is still on disk to read. An unparseable file yields {} - there are
        # no top-level keys to hand back from JSON we cannot load.
        displaced = carried
        if displaced is None:
            try:
                prior = json.loads(text)
            except ValueError:
                prior = None
            displaced = (_displaced_owned_keys(ours, prior, None)
                         if isinstance(prior, dict) else {})
        manifest["files"].append(_tracked(displaced))
        return

    try:
        theirs = json.loads(text)
    except ValueError as exc:
        _decline(f"existing settings.json is not valid JSON ({exc})",
                 _digest(text))
        return
    if not isinstance(theirs, dict):
        _decline(f"existing settings.json is a {type(theirs).__name__}, "
                 f"not an object", _digest(text))
        return
    why = _settings_unmergeable_reason(theirs)
    if why is not None:
        _decline(why, _digest(text))
        return

    merged, owned_deny, owned_hooks = _merge_settings(
        ours, theirs,
        (known or {}).get("owned_deny") or [],
        (known or {}).get("owned_hooks") or [])
    new_text = json.dumps(merged, indent=2) + "\n"

    co_owned = {
        "path": action["path"],
        "kind": action["kind"],
        "state": "settings-merged",
        "block_digest": _digest(body),
        "owned_deny": owned_deny,
        "owned_hooks": owned_hooks,
        # Their values for the keys we take over outright, so uninstall can
        # give them back rather than delete them.
        "displaced_keys": _displaced_owned_keys(ours, theirs, known),
        "tier": TIER_SECURITY,
    }
    if new_text == text:
        summary["unchanged"] += 1
        print(f"    ok   {action['path']}  (hook wiring current; operator "
              f"settings untouched)")
    else:
        summary["update"] += 1
        print(f"  UPDATE {action['path']}  (hook wiring merged; operator "
              f"settings untouched)")
        if not dry:
            _write(new_text)
    manifest["files"].append(co_owned)


def _uninstall_settings_merge(root: Path, entry: dict) -> str:
    """Reverse a merged settings.json: retire what this installer ADDED and
    keep everything the operator put there. -> "removed" | "stripped" |
    "kept". Removing the file only when nothing of theirs is left is what
    keeps `--uninstall` honest for a co-owned file; leaving our `hooks` key
    behind would point Claude Code at scripts uninstall just deleted."""
    target = root / entry["path"]
    try:
        cur = json.loads(target.read_text())
    except (OSError, ValueError):
        return "kept"
    if not isinstance(cur, dict):
        return "kept"

    # Keys we took over go BACK to the operator's value where they had one,
    # and are removed only where they did not. Assigning an existing key does
    # not move it, so their file keeps its ordering.
    displaced = entry.get("displaced_keys") or {}
    for key in _SETTINGS_OWNED_KEYS:
        if key in displaced:
            cur[key] = displaced[key]
        else:
            cur.pop(key, None)

    owned_sites, legacy_cmds = _split_owned_hooks(entry.get("owned_hooks"))
    hooks = cur.get("hooks")
    if (owned_sites or legacy_cmds) and isinstance(hooks, dict):
        stripped: dict = {}
        for event, groups in hooks.items():
            if not isinstance(groups, list):
                stripped[event] = groups
                continue
            kept_groups = []
            for grp in groups:
                if not isinstance(grp, dict) \
                        or not isinstance(grp.get("hooks"), list):
                    kept_groups.append(grp)
                    continue
                matcher = grp.get("matcher")
                kept = [e for e in grp["hooks"]
                        if not _is_ours_here(event, matcher, e,
                                             owned_sites, legacy_cmds)]
                if kept:
                    kept_groups.append(dict(grp, hooks=kept))
            if kept_groups:
                stripped[event] = kept_groups
        if stripped:
            cur["hooks"] = stripped
        else:
            cur.pop("hooks", None)

    owned = entry.get("owned_deny") or []
    perms = cur.get("permissions")
    if isinstance(perms, dict):
        deny = [r for r in (perms.get("deny") or []) if r not in owned]
        if deny:
            perms["deny"] = deny
        else:
            perms.pop("deny", None)
        if not perms:
            cur.pop("permissions", None)

    if not cur:
        target.unlink()
        return "removed"
    target.write_text(json.dumps(cur, indent=2) + "\n")
    return "stripped"


# --------------------------------------------------------------------------- #
# Post-install wiring verification
# --------------------------------------------------------------------------- #
_CPD_PREFIX = "$CLAUDE_PROJECT_DIR/"


def _resolved_hook_path(command: str) -> str | None:
    """The project-relative path a hook command RUNS, or None when it does not
    name one we can resolve.

    A hook `command` is a SHELL COMMAND LINE, not a path: an operator's
    `$CLAUDE_PROJECT_DIR/.claude/hooks/fmt.sh --fix` runs a script that is
    right there on disk. Treating the whole string as a path reported a
    perfectly healthy install as unenforced and exited 3 (round-6 F3) - the
    cry-wolf failure, and `plugin/commands/bootstrap-apply.md` acts on that
    exit code, so the operator was told an install had failed when it had
    not. Only `$CLAUDE_PROJECT_DIR/…` resolves; anything else is the
    operator's business and is left alone rather than guessed at.

    Tokenised the way the shell would, which `shlex.split` alone does NOT do:
    `punctuation_chars` makes `;`, `|`, `&&` and redirections terminate a
    word, so `hook.sh; echo done` resolves to `hook.sh` rather than to a
    non-existent `hook.sh;`. `commenters` is cleared because `shlex` treats
    `#` as starting a comment while `sh` treats it as an ordinary character
    mid-word - enabling `punctuation_chars` without it merely moves the false
    alarm from `;` to `#`. Both verified token-for-token against `sh`.
    """
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        argv = list(lex)
    except ValueError:              # unbalanced quoting; theirs, and opaque
        return None
    if not argv or not argv[0].startswith(_CPD_PREFIX):
        return None
    return argv[0][len(_CPD_PREFIX):]


def _registered_commands(settings: dict) -> list[str]:
    """Every `command` string inside a settings.json `hooks` mapping.

    Tolerant by construction: this file may be operator-authored and carry
    any shape at all, so every level is isinstance-checked and nothing here
    raises. An unreadable shape yields no commands, which the caller reports
    as "nothing is registered" - the safe reading.
    """
    out: list[str] = []
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return out
    for groups in hooks.values():
        if not isinstance(groups, list):
            continue
        for grp in groups:
            if not isinstance(grp, dict):
                continue
            entries = grp.get("hooks")
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) \
                        and isinstance(entry.get("command"), str):
                    out.append(entry["command"])
    return out


def verify_wiring(root: Path, plan: list[dict]) -> list[str]:
    """Does the installed tree actually ENFORCE what the plan describes?

    Two directions, because review found one failure of each kind:

      forward   every hook in the plan is registered in the on-disk
                settings.json. settings.json is the ONLY registration site
                for the shell substrate, so when it is skipped every gate
                goes dead at once - while the hook bodies stay on disk and
                still exit 2 when invoked by hand, so hand-verification
                passes and the operator has no signal at all.
      backward  every hook command settings.json registers exists on disk.
                A re-apply that drops a hook from the plan deletes the file
                while a skipped settings.json keeps pointing at it; the
                harness then runs a missing script (rc=127) on every match,
                and rc=127 is neither allow nor block.

    Returns a list of human-readable problems; empty means coherent.

    Deliberately a PROPERTY rather than a check for the two known causes: it
    holds whatever the reason a registration is missing, including reasons
    that do not exist yet. Only commands under `$CLAUDE_PROJECT_DIR/` resolve
    to a path, so operator-authored entries naming anything else are left
    alone rather than guessed at.
    """
    problems: list[str] = []
    planned_hooks = sorted(a["path"] for a in plan if a["kind"] == "hook")
    settings_path = root / ".claude" / "settings.json"

    if not settings_path.exists():
        if planned_hooks:
            problems.append(
                f".claude/settings.json is absent, so none of the "
                f"{len(planned_hooks)} emitted hooks is registered.")
        return problems

    try:
        settings = json.loads(settings_path.read_text())
    except (OSError, ValueError) as exc:
        problems.append(
            f".claude/settings.json could not be read as JSON ({exc}). Hook "
            f"registration is unverifiable, and Claude Code will not load it "
            f"either.")
        return problems
    if not isinstance(settings, dict):
        problems.append(
            f".claude/settings.json is a {type(settings).__name__}, not an "
            f"object; no hook can be registered in it.")
        return problems

    registered = {p for p in map(_resolved_hook_path,
                                 _registered_commands(settings))
                  if p is not None}

    for hook_path in planned_hooks:
        if hook_path not in registered:
            problems.append(
                f"{hook_path} was emitted but is NOT registered in "
                f".claude/settings.json - nothing will dispatch it.")

    for rel in sorted(registered):
        if not (root / rel).exists():
            problems.append(
                f".claude/settings.json registers {rel}, which is not on "
                f"disk - the harness runs a missing script (rc=127) on every "
                f"matching tool call.")

    return problems


def _apply_root_gitignore(root: Path, action: dict, manifest: dict,
                          summary: dict, *, dry: bool) -> None:
    """IC-2 [SR-17 decision (a)] - manage the root-sentinel block in the
    PROJECT-ROOT .gitignore.

    Semantics (owner-decided, spec bootstrap-v2 R-4):
      * File absent (greenfield): create it containing exactly the managed
        block - fully deterministic, digest-tracked normally in the manifest
        (uninstall removes it iff unmodified, like any generated file).
      * File present and byte-identical to the block: still wholly
        installer-authored - normal digest tracking, no write.
      * File present with operator content: the installer owns ONLY the
        marker-delimited block. Append it once if absent; refresh it in
        place if it drifted; NEVER touch bytes outside the markers. The
        manifest entry carries state "managed-block-appended" with a
        block_digest but NO whole-file digest, so operator edits outside
        the block never fire hand-edit warnings and uninstall keeps the
        co-owned file.
      * Torn block (begin marker without end marker): fail loud, skip.
    """
    from templates import GITIGNORE_BLOCK_BEGIN, GITIGNORE_BLOCK_END

    target = root / action["path"]
    block = action["body"]

    def _atomic_write(text: str) -> None:
        # Co-ownership extends to metadata (review finding 7): when the
        # file already exists, preserve the operator's mode - the
        # installer owns only the marker block, never the permissions.
        # (The inode still changes; atomicity of the content write wins
        # over inode stability for a gitignore.)
        mode = (stat.S_IMODE(target.stat().st_mode) if target.exists()
                else action["mode"])
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(text)
        tmp.chmod(mode)
        os.replace(tmp, target)

    tracked = {
        "path": action["path"],
        "digest": _digest(block),
        "mode": oct(action["mode"]),
        "kind": action["kind"],
        "tier": TIER_NON,
    }
    co_owned = {
        "path": action["path"],
        "kind": action["kind"],
        "state": "managed-block-appended",
        "block_digest": _digest(block),
        "tier": TIER_NON,
    }

    if not target.exists():
        summary["create"] += 1
        print(f"  CREATE {action['path']}  "
              f"(project-root write: root-sentinel managed block)")
        if not dry:
            _atomic_write(block)
        manifest["files"].append(tracked)
        return

    text = target.read_text()
    if text == block:
        summary["unchanged"] += 1
        print(f"    ok   {action['path']}")
        manifest["files"].append(tracked)
        return

    if GITIGNORE_BLOCK_BEGIN in text:
        start = text.index(GITIGNORE_BLOCK_BEGIN)
        end = text.find(GITIGNORE_BLOCK_END, start)
        if end == -1:
            summary["skipped"] += 1
            print(f"  SKIP   {action['path']}  (managed block is torn - "
                  f"begin marker without end marker; repair it manually)")
            co_owned["state"] = "managed-block-torn"
            manifest["files"].append(co_owned)
            return
        end += len(GITIGNORE_BLOCK_END)
        if end < len(text) and text[end] == "\n":
            end += 1
        if text[start:end] == block:
            summary["unchanged"] += 1
            print(f"    ok   {action['path']}  (managed block current; "
                  f"operator content untouched)")
        else:
            summary["update"] += 1
            print(f"  UPDATE {action['path']}  (managed block refreshed; "
                  f"operator content untouched)")
            if not dry:
                _atomic_write(text[:start] + block + text[end:])
    else:
        summary["update"] += 1
        print(f"  UPDATE {action['path']}  (project-root write: managed "
              f"block appended; operator content untouched)")
        if not dry:
            sep = "" if text.endswith("\n") else "\n"
            _atomic_write(text + sep + block)
    manifest["files"].append(co_owned)


def _reconcile_orphaned_substrate(root: Path) -> None:
    """Downgrade a greenfield state file's gate_substrate to "shell" when
    the SDK gate module it refers to is no longer emitted (e.g. a
    greenfield sdk-callable install re-applied in retrofit mode, whose
    separate .retrofit-state.json never touches .bootstrap-state.json).
    Without this the state advertises "sdk-callable" while gates.py has
    been stale-deleted from disk - a silent enforcement gap."""
    sp = root / STATE
    if not sp.exists():
        return
    try:
        st = json.loads(sp.read_text())
    except Exception:
        return
    if st.get("gate_substrate") == "sdk-callable":
        st["gate_substrate"] = "shell"
        sp.write_text(json.dumps(st, indent=2) + "\n")
        print('WARNING: .bootstrap-state.json advertised gate_substrate '
              '"sdk-callable" but the SDK gate module is no longer emitted '
              'by this install; reconciled to "shell".', file=sys.stderr)


def _write_state(root: Path, cfg: dict, manifest: dict) -> None:
    """Write .claude/.bootstrap-state.json honouring the Bootstrap-Protocol-v2-0-0.md
    Phase 0 / Recovery-and-State schema (archetype, PRD path, CI/CD opt-out,
    the three autonomous-mode flags, the three tracking lists). Preserves any
    pre-existing keys (e.g. completed_phases written by a live wizard)."""
    proj = cfg.get("project", {})
    flags = cfg.get("autonomous_modes", {})
    state_path = root / STATE
    state: dict = {}
    raw = None
    if state_path.exists():
        try:
            raw = state_path.read_text()
        except Exception:
            raw = None
        if raw is not None:
            try:
                state = json.loads(raw)
            except Exception:
                state = {}
    # --- IC-3 migration (Companion "Migration notes"): any pre-2.0.0 state
    # file - INCLUDING one too corrupt to parse, exactly the case a backup
    # exists for - is backed up once before being rewritten. The backup is
    # the same single read the migration classified (byte-identical, no
    # second-read window).
    if raw and "gate_substrate" not in state:
        backup = state_path.with_name(state_path.name + ".pre-2.0.0")
        if not backup.exists():
            backup.write_text(raw)
    # R-9 enforcement AT THE WRITE (not just in main()): "sdk-callable" is
    # persisted only when the IC gate cleared it IN THIS PROCESS
    # (cfg["_ic_gate_cleared"], set by main() after run_ic_checks passes).
    # A programmatic caller (test, plugin, Tessera-as-library) that reaches
    # apply_plan without clearing the gate can never silently stamp an
    # ungated substrate - it downgrades to "shell" loudly. No recursion
    # with IC-3: that probe passes a shell-substrate fixture, so this
    # branch is inert for it.
    prior_substrate = state.get("gate_substrate")
    requested = cfg.get("gate_substrate", "shell")
    substrate = requested
    if requested == "sdk-callable" and not cfg.get("_ic_gate_cleared"):
        print("WARNING: gate_substrate: \"sdk-callable\" requested but the "
              "IC gate did not clear it in this process; refusing to "
              "persist an ungated substrate - writing \"shell\".",
              file=sys.stderr)
        substrate = "shell"
    if prior_substrate == "sdk-callable" and substrate != "sdk-callable":
        print(f"WARNING: gate_substrate downgraded "
              f"{prior_substrate!r} -> {substrate!r} on this re-apply; a "
              f"consumer keying dispatch off the state field falls back to "
              f"shell-era enforcement. Any emitted sdk_gates/ module "
              f"remains on disk.", file=sys.stderr)
    state.update({
        "bootstrap_protocol_version": PROTOCOL_VERSION,
        # IC-3: the installed enforcement substrate; see the enforcement
        # block just above for how "sdk-callable" is gated at the write.
        "gate_substrate": substrate,
        "installed_by": f"bootstrap-installer {INSTALLER_VERSION}",
        "installed_at": manifest["generated_at"],
        "deterministic_install": True,
        # --- Bootstrap-Protocol-v2-0-0.md Phase 0 required classification fields ---
        "archetype": proj.get("archetype"),
        "prd_path": proj.get("prd_path"),
        "prd_tier": proj.get("prd_tier"),
        "cicd_opt_out": bool(proj.get("cicd_opt_out", False)),
        # --- the three autonomous-mode opt-in flags (lines 107, 224) ---
        "loop_mode_enabled": bool(flags.get("loop_mode_enabled", False)),
        "goal_supervised_mode_enabled":
            bool(flags.get("goal_supervised_mode_enabled", False)),
        "queue_mode_enabled": bool(flags.get("queue_mode_enabled", False)),
        # TEL-01 (v2.4.0 fold): the Phase 0 opt-in decision, persisted
        # cfg-authoritatively (mirrors the mode-flag pattern above). The
        # flag-gated build_plan add keys off the same normalizer, so the
        # emitted telemetry.md and this state field can never disagree.
        "telemetry_export_enabled": telemetry_enabled(cfg),
        # DS-01 (v2.5.0): Phase 0 opt-in decisions, persisted cfg-authoritatively
        # (mirrors the mode-flag / telemetry pattern above). Forward-compat is
        # default-on-READ, NOT the IC-3 write-into-old-files mechanism:
        # design_steering_enabled() returns False for an absent key
        # (cfg.get(..., False)); nothing is written into old state files at read
        # time (same posture as telemetry_export_enabled / exit_reason). Retrofit
        # installs inherit the False default harmlessly: _write_retrofit_state
        # carries neither field, exactly as it carries no telemetry_export_enabled.
        "design_steering_enabled": design_steering_enabled(cfg),
        # The skill field is gated on the primary via `and`, so it records the
        # SAME condition build_plan emits SKILL.md under (the nested
        # `if design_steering_enabled: if design_review_skill_enabled:` at
        # build_plan) — the emitted skill/command and this state field can never
        # disagree. The `and` also short-circuits when steering is off, so the
        # skill normalizer is NOT evaluated then: a garbage design_review_skill_
        # enabled value on a steering-off install is inert (matching build_plan,
        # which never reaches it either) instead of crashing _write_state after
        # apply_plan has already written every file. When steering IS on, both
        # build_plan (gate) and this line evaluate the skill normalizer, so a
        # garbage value fails loud EARLY in build_plan, before any file is
        # written — the same fail-early property telemetry_enabled has.
        "design_review_skill_enabled": (design_steering_enabled(cfg)
                                        and design_review_skill_enabled(cfg)),
    })
    # --- the three tracking lists: initialise once, never clobber ---
    state.setdefault("loop_in_flight", [])
    state.setdefault("goal_in_flight", [])
    state.setdefault("queue_runs_history", [])
    state.setdefault("deferred_items", {})
    state.setdefault("skippable_phase_decisions", {})
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n")


def _write_retrofit_state(root: Path, cfg: dict, manifest: dict) -> None:
    """Write .claude/.retrofit-state.json in the B5-frozen shape from
    RETROFIT-COMPANION v1.6.2:

    TOP-LEVEL (matching BOOTSTRAP's .bootstrap-state.json shape, so any
    BOOTSTRAP runtime tooling that reads the state file post-retrofit
    finds the flags where BOOTSTRAP puts them):
      - the three *_enabled flags (loop_mode_enabled,
        goal_supervised_mode_enabled, queue_mode_enabled). These are
        PINNED FALSE at retrofit time regardless of operator opt-in
        (resolve_config's retrofit branch rejects any cfg that tries to
        flip them; this writer enforces the same rule even if a hand-
        edited cfg slipped past).
      - the three in-flight lists (loop_in_flight, goal_in_flight,
        queue_runs_history), initialized once, never clobbered.

    NESTED UNDER `autonomous_modes` (the only RETROFIT-novel fields,
    with no BOOTSTRAP counterpart):
      - *_opted_in intent flags
      - brownfield_milestones object

    Plus retrofit-specific top-level fields from RETROFIT.md
    R0.5/R0.7/R7: archetype + confidence + evidence, prd_tier_target,
    ci_cd_applicability, pm_strategy + tool + role + migration
    disposition, skip_decisions, retrofit_active, retrofit_complete,
    r08_committed. bootstrap_protocol_version reuses the same constant
    the greenfield writer uses (OD-4 condition); retrofit_protocol_
    version records the RETROFIT protocol revision targeted.

    Per C1: this is a SIBLING function. _write_state is NOT modified.
    The dispatch decision lives at the single cfg["mode"] branch at the
    apply_plan call site below.
    """
    r = cfg.get("retrofit", {})
    proj = cfg.get("project", {})
    flags = cfg.get("autonomous_modes", {})
    pm = r.get("pm", {})
    am = r.get("autonomous_modes", {})

    state_path = root / RETROFIT_STATE
    state: dict = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except Exception:
            state = {}

    # B5 rule: *_enabled MUST be false at retrofit time. The wizard
    # scaffolds but never enables; if a stale state file has them true,
    # do NOT clobber that runtime decision (an operator may have
    # post-retrofit flipped them after the brownfield milestone went
    # green). On first write only, initialize to false.
    state.setdefault("loop_mode_enabled", False)
    state.setdefault("goal_supervised_mode_enabled", False)
    state.setdefault("queue_mode_enabled", False)
    state.setdefault("loop_in_flight", [])
    state.setdefault("goal_in_flight", [])
    state.setdefault("queue_runs_history", [])
    # R-2 (D5+D6 review): retrofit_active is OPERATOR-RUNTIME state.
    # R7 sets it to false in state.json to mark retrofit complete; an
    # installer re-apply must not overwrite that runtime decision from
    # cfg. Same setdefault pattern as *_enabled: cfg's value is only the
    # FIRST-WRITE default. Subsequent applies preserve what's in state.
    state.setdefault("retrofit_active",
                     bool(r.get("retrofit_active", True)))
    state.setdefault("retrofit_complete", False)
    # R-3 (D5+D6 review): R0.8 Preview & Commitment fields. The decision
    # layer sets r08_committed=true after operator approval; the
    # installer initializes the slot but does not flip it. Once set by
    # the decision layer it persists across re-applies (setdefault).
    # Round-3 review (Lens C2): r08_committed is now a gated cfg field
    # (resolve_config rejects bootstrap-install runs where it isn't true
    # AND r0.8 wasn't skipped). Source the initial value from cfg; once
    # written to state, setdefault preserves operator-runtime decisions
    # across re-apply.
    state.setdefault("r08_committed",
                     bool(r.get("r08_committed", False)))
    state.setdefault("r08_committed_at", r.get("r08_committed_at"))

    # Versioning per OD-4: both fields, both top-level.
    state.update({
        "bootstrap_protocol_version": PROTOCOL_VERSION,
        # IC-3 parity with _write_state: retrofit installs ship the same
        # 2.0.0 wrapper bodies and the same shell gate suite, so the state
        # file carries the same substrate signal (the 2.1.0 ic_checks /
        # seam consumers key off this field; its absence would misclassify
        # a retrofit project as pre-2.0.0). "sdk-callable" is never
        # written here for the same reasons as the greenfield writer.
        "gate_substrate": "shell",
        "retrofit_protocol_version": RETROFIT_PROTOCOL_VERSION,
        "installed_by": f"bootstrap-installer {INSTALLER_VERSION}",
        "installed_at": manifest["generated_at"],
        "deterministic_install": True,
        # RETROFIT.md R0.5 step 8 schema:
        "archetype": proj.get("archetype"),
        "archetype_proposed": proj.get("archetype"),
        "archetype_confidence": r.get("archetype_confidence", "low"),
        "archetype_evidence": list(r.get("archetype_evidence", [])),
        "synthetic_profile": dict(r.get("synthetic_profile", {})),
        "prd_tier_target": r.get("prd_tier_target", proj.get("prd_tier")),
        "ci_cd_applicability": r.get("ci_cd_applicability", "unknown"),
        # RETROFIT.md R0.7 PM strategy fields:
        "pm_strategy": pm.get("strategy"),
        "pm_tool": pm.get("tool"),
        "pm_tool_role_after": pm.get("tool_role_after"),
        "ticket_migration_disposition":
            dict(pm.get("ticket_migration", {})),
        "hybrid_review_date": pm.get("hybrid_review_date"),
        # NOTE: retrofit_active and retrofit_complete are operator-runtime
        # state managed via setdefault above (R-2 fix). They are NOT
        # overwritten by re-apply — that would silently undo R7's
        # `retrofit_active: false` and any operator post-R7 edits.
        # RETROFIT.md R0.5 step 7 skippable decisions:
        "skip_decisions": dict(r.get("skip_decisions", {})),
    })

    # B5 nested fields: autonomous_modes.*_opted_in + brownfield_milestones.
    state["autonomous_modes"] = {
        "loop_mode_opted_in": bool(am.get("loop_mode_opted_in", False)),
        "goal_supervised_mode_opted_in":
            bool(am.get("goal_supervised_mode_opted_in", False)),
        "queue_mode_opted_in":
            bool(am.get("queue_mode_opted_in", False)),
        "brownfield_milestones":
            dict(am.get("brownfield_milestones", {})),
    }

    # R-1 (D5+D6 review): non-propagation of cfg["autonomous_modes"]
    # *_enabled flags is guaranteed BY CONSTRUCTION above (state.update
    # doesn't write those keys; setdefault preserves existing state.json
    # values; cfg's autonomous_modes is never read for the *_enabled
    # keys). resolve_config's retrofit branch is the SECOND seam (rejects
    # cfgs whose *_enabled flags claim true). Should it somehow leak
    # past both, surface it loudly here rather than silently — the
    # operator needs to know the cfg is malformed.
    bad_flags = [k for k in (
            "loop_mode_enabled", "goal_supervised_mode_enabled",
            "queue_mode_enabled") if flags.get(k, False)]
    if bad_flags:
        print(
            f"warning: retrofit cfg attempted to enable {bad_flags} "
            f"(scaffold-but-defer rule violated); state file's "
            f"*_enabled flags left at their preserved/false values. "
            f"resolve_config should reject this case — please file a "
            f"bug if you see this warning.", file=sys.stderr)

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n")


def _load_manifest(root: Path) -> dict | None:
    p = root / MANIFEST
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


def uninstall(root: Path) -> None:
    """Remove only files whose on-disk content still matches what the
    installer wrote; never destroy operator-modified work.

    The reversibility contract is "remove exactly what it created" — so a
    file is removed only when its current sha256 still equals the digest the
    manifest recorded for it. Any mismatch means the operator (or some other
    tool) changed the file after the installer wrote it, so it is *kept*,
    regardless of the manifest `state` label. This closes the data-loss path
    where `apply -> hand-edit a generated file -> uninstall` silently deleted
    the operator's edits because the manifest still carried the original
    digest (the `skipped-local-edit` label was only ever set by a *re-apply*
    between the edit and the uninstall, which most operators never do).
    """
    m = _load_manifest(root)
    if not m:
        print("No installer manifest found; nothing removed "
              "(any generated tree is left intact for manual cleanup).")
        return
    kept = removed = 0
    for f in reversed(m["files"]):
        target = root / f["path"]
        if not target.exists():
            continue
        # A merged settings.json carries no whole-file digest (the operator
        # owns most of it), so the generic rule below would KEEP it wholesale
        # - leaving our `hooks` key registering scripts this very run is
        # about to delete. Strip our keys instead.
        if f.get("state") == "settings-merged":
            outcome = _uninstall_settings_merge(root, f)
            if outcome == "removed":
                print(f"  REMOVE {f['path']}")
                removed += 1
            elif outcome == "stripped":
                print(f"  UPDATE {f['path']}  (hook wiring removed; "
                      f"operator settings kept)")
                removed += 1
            else:
                print(f"  KEEP   {f['path']}  (cannot verify; left in place)")
                kept += 1
            continue
        recorded = f.get("digest")
        try:
            on_disk = _digest(target.read_text())
        except Exception:
            # Unreadable / binary-ish: be conservative, keep it.
            print(f"  KEEP   {f['path']}  (cannot verify; left in place)")
            kept += 1
            continue
        # `skipped-local-edit` entries record the *modified* digest; a plain
        # generated entry records the *installer* digest. In both cases the
        # rule is identical: remove iff what is on disk is byte-for-byte what
        # the installer last produced for this path.
        if f.get("state") == "skipped-local-edit" or recorded != on_disk:
            print(f"  KEEP   {f['path']}  (locally modified)")
            kept += 1
            continue
        target.unlink()
        print(f"  REMOVE {f['path']}")
        removed += 1
    # prune now-empty .claude subdirs
    claude = root / ".claude"
    if claude.exists():
        for d in sorted((p for p in claude.rglob("*") if p.is_dir()),
                        reverse=True):
            try:
                d.rmdir()
            except OSError:
                pass
    print(f"Uninstall complete. removed={removed} kept={kept} "
          f"(modified files and the manifest/state are left for inspection).")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _substrate_gate(cfg: dict) -> tuple[bool, dict | None]:
    """R-9 IC gate (AC-9-1/9-2), side-effect-free on cfg. Returns
    (ok, results): (True, None) when the config doesn't request
    sdk-callable; (True, results) when it does and every IC-1..IC-7 check
    passes; (False, results) when it requests sdk-callable but a check
    fails. Callers that proceed set cfg["_ic_gate_cleared"] themselves so
    the write-side enforcement can persist the granted value."""
    if cfg.get("gate_substrate") != "sdk-callable":
        return True, None
    import ic_checks
    results = ic_checks.run_ic_checks()
    return ic_checks.all_passed(results), results


def _print_substrate_refusal(results: dict) -> None:
    print('Install REFUSED: gate_substrate: "sdk-callable" requested but '
          "the IC self-checks are not green:", file=sys.stderr)
    for ic, r in results.items():
        if not r["passed"]:
            print(f"  - {ic} ({r['title']}): {r['detail']}",
                  file=sys.stderr)
    print("The state file retains its current substrate. Fix the failing "
          "checks or request gate_substrate: shell.", file=sys.stderr)


def _runtime_floor_check() -> None:
    """AC-9-4: log the detected Claude Code CLI version; warn LOUDLY when
    it is below the seam binds floor (RUNTIME_FLOOR) or undetectable.
    Never fatal - the floor binds dispatch behavior (fail-closed
    PreToolUse timeouts), not emission - but never silent either."""
    import re
    import shutil
    import subprocess
    exe = shutil.which("claude")
    detected = None
    if exe:
        try:
            r = subprocess.run([exe, "--version"], capture_output=True,
                               text=True, timeout=15)
            # Scan BOTH streams (some wrappers print the version to stderr)
            # and ANCHOR the match so an update-notifier banner or node
            # version line elsewhere in the output can't be mistaken for
            # the CLI version. Priority: the version adjacent to the
            # "(Claude Code)" marker, else a version at the start of a
            # line (optionally 'v'-prefixed).
            out = (r.stdout or "") + "\n" + (r.stderr or "")
            # Anchor priority so an update-notifier banner or node-version
            # line can't be mistaken for the CLI version: (1) adjacent to
            # the "(Claude Code)" marker; (2) after a "version" keyword;
            # (3) a version at the start of a line.
            m = (re.search(r"(\d+)\.(\d+)\.(\d+)\s*\(Claude Code\)", out)
                 or re.search(r"(?i)version[^\d\n]*?(\d+)\.(\d+)\.(\d+)",
                              out)
                 or re.search(r"(?m)^\s*v?(\d+)\.(\d+)\.(\d+)\b", out))
            if m:
                detected = tuple(int(g) for g in m.groups())
        except Exception:
            detected = None
    floor = tuple(int(p) for p in RUNTIME_FLOOR.split("."))
    if detected is None:
        print(f"WARNING: Claude Code CLI version undetectable - the seam "
              f"runtime floor >= {RUNTIME_FLOOR} (fail-closed PreToolUse "
              f"timeouts) cannot be confirmed. Unattended dispatch below "
              f"the floor can stall on a gate-hook timeout.",
              file=sys.stderr)
        return
    ver = ".".join(map(str, detected))
    print(f"Claude Code runtime detected: {ver} "
          f"(seam floor >= {RUNTIME_FLOOR})")
    if detected < floor:
        print(f"WARNING: Claude Code {ver} is BELOW the seam runtime "
              f"floor {RUNTIME_FLOOR}: a PreToolUse gate-hook timeout is "
              f"misreported as a user rejection below the floor, stalling "
              f"unattended sessions. Upgrade before any autonomous "
              f"dispatch.", file=sys.stderr)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="bootstrap-install",
        description="Deterministically configure Claude Code from a "
                    "bootstrap.config.yaml.")
    ap.add_argument("-c", "--config", default="bootstrap.config.yaml")
    ap.add_argument("-C", "--dir", default=".",
                    help="Target project root (default: cwd)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show the plan; write nothing.")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite files even if locally modified.")
    ap.add_argument("--adopt", action="store_true",
                    help="Record files at planned paths as installer-owned "
                         "WITHOUT writing them. For a tree whose manifest "
                         "is gone (it is gitignored, so a fresh clone has "
                         "none) and whose files are an earlier install's "
                         "artifacts rather than your work. Nothing is "
                         "overwritten; re-run normally afterwards.")
    ap.add_argument("--uninstall", action="store_true",
                    help="Remove everything the installer created.")
    ap.add_argument("--print-config", action="store_true",
                    help="Print the fully-resolved config and exit.")
    ap.add_argument("--ic-checks", action="store_true",
                    help="Run the IC-1..IC-7 self-checks, print the "
                         "checklist as JSON, exit non-zero on any "
                         "failure (AC-9-3; asserted by the seam "
                         "protocol-compatibility job).")
    args = ap.parse_args(argv)

    root = Path(args.dir).resolve()

    # They mean opposite things - "overwrite what is there" versus "keep what
    # is there and claim it" - so a run asking for both is a mistake, and
    # silently letting one win is how an operator ends up with the
    # destructive one.
    if args.force and args.adopt:
        print("--force and --adopt are mutually exclusive: --force "
              "overwrites what is on disk, --adopt keeps it and records it "
              "as ours.", file=sys.stderr)
        return 2

    if args.ic_checks:
        import ic_checks
        results = ic_checks.run_ic_checks()
        print(json.dumps(results, indent=2))
        return 0 if ic_checks.all_passed(results) else 1

    if args.uninstall:
        uninstall(root)
        return 0

    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = root / cfg_path
    if not cfg_path.exists():
        print(f"error: config not found: {cfg_path}", file=sys.stderr)
        return 2

    raw = load_yaml(cfg_path.read_text())
    cfg, errors = resolve_config(raw)
    if errors:
        print("Config validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    # [round-4 D18] Spellings that were normalized rather than refused. These
    # are NOT errors - the install proceeds - but they must be visible: the
    # previous behavior was to emit a secrets-gate that guarded nothing, with
    # rc=0 and no output, which is the worst of the available options.
    for note in cfg.get("_config_notices", ()):
        print(f"note: {note}", file=sys.stderr)

    # The IC gate runs BEFORE --print-config returns too: interview.py
    # documents `--print-config` as the authoritative validation call and
    # the seam §8.2 job uses it, so its verdict must match the install's
    # (AC-9 consistency) - a config the install would refuse must not
    # validate clean here.
    ok, results = _substrate_gate(cfg)
    if not ok:
        _print_substrate_refusal(results)
        return 2

    if args.print_config:
        print(json.dumps(cfg, indent=2, default=str))
        return 0

    if results is not None:
        # sdk-callable requested and all IC checks passed: mark the config
        # gate-cleared so _write_state may persist "sdk-callable" (the
        # write-side enforcement refuses it otherwise, even for callers
        # that bypass this CLI path).
        cfg["_ic_gate_cleared"] = True
        print("IC gate: all IC-1..IC-7 self-checks passed - "
              'gate_substrate: "sdk-callable" granted.')

    plan = build_plan(cfg)
    print(f"Bootstrap installer {INSTALLER_VERSION} "
          f"(protocol {PROTOCOL_VERSION})")
    _runtime_floor_check()
    print(f"Archetype: {cfg['project']['archetype']}  |  "
          f"loop={cfg['autonomous_modes']['loop_mode_enabled']} "
          f"goal={cfg['autonomous_modes']['goal_supervised_mode_enabled']} "
          f"queue={cfg['autonomous_modes']['queue_mode_enabled']}")
    print(f"Target: {root}")
    print(f"{'DRY RUN - ' if args.dry_run else ''}{len(plan)} files planned\n")

    summary = apply_plan(root, plan, cfg, dry=args.dry_run,
                          force=args.force, adopt=args.adopt)
    print(f"\nDone. create={summary['create']} update={summary['update']} "
          f"unchanged={summary['unchanged']} skipped={summary['skipped']} "
          f"removed={summary['removed']}"
          + (f" adopted={summary['adopted']}" if summary["adopted"] else ""))
    if summary["adopted"]:
        print(f"\n--adopt recorded {summary['adopted']} file(s) as "
              f"installer-owned and wrote none of them. Re-run without "
              f"--adopt to bring them up to date.")
    if summary["backups"]:
        print(f"\n--force displaced {len(summary['backups'])} file(s) the "
              f"installer did not author. Previous versions:")
        for saved in summary["backups"]:
            print(f"  {saved}")
        print("Nothing else reads that directory; delete it when you are "
              "satisfied, or copy content back out of it.")
    if summary["symlinks_replaced"]:
        n = len(summary["symlinks_replaced"])
        if args.dry_run:
            print(f"\n{n} planned path(s) ARE SYMLINKS and would be replaced "
                  f"by regular files. The link target would keep its own "
                  f"content, but nothing would point at it any more:")
        else:
            print(f"\n{n} planned path(s) were SYMLINKS and are now regular "
                  f"files. The link target still holds its own content, but "
                  f"nothing points at it any more:")
        for s in summary["symlinks_replaced"]:
            print(f"  {s['path']}  ->  linked to {s['target']}")
        print("If that link is deliberate - a shared dotfiles repo, say - "
              "re-create it afterwards, or keep the file here and drop the "
              "link. `--uninstall` removes what was written and does not "
              "restore the link.")

    if args.dry_run:
        print("(dry run - no files written)")
        return 0

    # --- Did this run actually install enforcement? ----------------------- #
    # Two independent signals, both loud on stderr and both non-zero, because
    # the failure they describe is invisible in the stdout transcript above:
    # it looks exactly like a successful install.
    unenforced = False

    if summary["skipped_security"]:
        unenforced = True
        print("\nERROR: security-critical files were NOT written:",
              file=sys.stderr)
        for entry in summary["skipped_security"]:
            print(f"  - {entry['path']}  ({entry['reason']})",
                  file=sys.stderr)
        print("The install left the gates these files carry UNENFORCED. "
              "Reconcile them and re-run, or pass --force to overwrite "
              "(--force replaces the whole file, including anything you "
              "put there).", file=sys.stderr)
        # [round-6 F6] Without this, --force is the only remedy on offer, and
        # its warning describes destroying the operator's work - which on a
        # manifest-less tree is very often not what those files are.
        if summary["no_manifest"]:
            print("This tree has NO installer manifest. It is gitignored, so "
                  "a fresh clone carries every file this installer wrote and "
                  "no record that it wrote them, which is why they read as "
                  "yours. If they are an earlier install's artifacts rather "
                  "than your work, `--adopt` records them as ours and writes "
                  "nothing; re-run normally afterwards.", file=sys.stderr)

    problems = verify_wiring(root, plan)
    if problems:
        unenforced = True
        print("\nERROR: the installed tree does not enforce its own plan:",
              file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)

    if unenforced:
        print(f"\nExiting {EXIT_UNENFORCED}: files were written, but this "
              f"install does not enforce. Do not treat it as installed.",
              file=sys.stderr)
        return EXIT_UNENFORCED
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

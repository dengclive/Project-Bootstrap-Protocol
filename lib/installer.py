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
import re
import shlex
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from minyaml import key_line, load_yaml, YAMLError   # stdlib-only YAML subset
from templates import (  # all file bodies live here
    TEMPLATES, HOOK_EVENT_MAP, HOOK_EXTRA_EVENTS, HOOK_RETIRED_SITES,
    INDEX_COLUMNS, SPEC_START_CHAIN, SPEC_TASK_FILE, SPEC_VERSIONING_PATH,
    _worktrees_on, drop_spec_versioning_pointers, spec_versioning_skipped)
from defaults import policy_switch_errors, resolve_config   # + validation

MANIFEST = ".claude/.installer-manifest.json"
STATE = ".claude/.bootstrap-state.json"
RETROFIT_STATE = ".claude/.retrofit-state.json"
PROTOCOL_VERSION = "2.8.0"
RETROFIT_PROTOCOL_VERSION = "1.6.2"
# Seam binds floor (SEAM-CONTRACT v3.0.0, claude_code_runtime; unchanged
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

    # [WP3 / D2] The spec traceability check that spec-gate-commit.sh (the
    # PreToolUse fallback) and the git pre-commit / pre-merge-commit hooks
    # both run. Not a Claude Code hook: kind "file", so verify_wiring does
    # not look for a settings.json registration.
    if "spec-gate-commit" in hook_set:
        add(".claude/githooks/spec-check.sh", TEMPLATES["spec_check"](cfg),
            mode=0o755)
    # [WP3 / D2] The spec check's git-hook entry point, exactly where the
    # spec gate is. _apply_git_hooks writes the shims that call it into the
    # repository's hooks directory at apply time.
    if "spec-gate-commit" in hook_set:
        add(".claude/githooks/dispatch", TEMPLATES["git_hook_dispatch"](cfg),
            mode=0o755)

    add(".claude/hooks/audio-alerts.config", TEMPLATES["audio_config"](cfg))
    add(".claude/settings.json", TEMPLATES["settings_json"](cfg), kind="settings")

    # ---- IC-5 SDK gate module (Milestone B, seam §9) ---------------------- #
    # Emitted alongside the shell suite (which remains the SEV-1 manual
    # path, seam §7.5). Security-critical tier via its own kind (AC-7-6);
    # the retrofit overlay DROPS this entry (retrofit stays shell-era).
    #
    # [WP1 / D4 (a), owner decision 2026-09-27] Emitted ONLY for the SDK
    # substrate: when the config requests gate_substrate "sdk-callable".
    # Under "shell" (the default) nothing wires or imports it, so it was
    # 3,800 unwired lines that an adopter's formatter rewrote and that then
    # made every re-install exit 3. Keyed on the REQUEST, not the grant:
    # the CLI refuses a request the IC gate does not clear before
    # build_plan runs, and IC-5 itself renders this plan to check the
    # module. A shell re-apply over an sdk-callable tree drops the path, and
    # _reconcile_orphaned_substrate downgrades the state loudly.
    if cfg.get("gate_substrate") == "sdk-callable":
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

    # [WP3 / D6] The one script through which the main session lands an
    # implementer's worktree branch. Unconditional, like CLAUDE.md, which
    # points at it: its bytes are the same with worktree isolation on or
    # off (isolation off simply leaves nothing to land), so the isolation
    # decision still adds and removes no file. Kind "file", 0o755: not a
    # Claude Code hook, so not registered and not security-critical.
    add(".claude/merge-back.sh", TEMPLATES["merge_back_sh"](cfg), mode=0o755)

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
    # [WP3 versioning-index] The roster schema, as an installer-owned file
    # beside the operator-owned INDEX.md, for the GR2-01 reason above: an
    # upgrade can reach it, so an older roster can find its migration
    # recipe here. Phase 7.5's protocol document, and the Phase 7 step 5/6
    # READMEs. All unconditional, kind "file" (non-critical tier), so no
    # seam 7.2 membership change; the retrofit overlay passes them through
    # (RETROFIT.md R8.C/R8.D name the same artifacts), except that it drops
    # spec-versioning.md when the operator skipped R8.D.
    add(".claude/specs/README.md", TEMPLATES["specs_readme"](cfg))
    add(SPEC_VERSIONING_PATH, TEMPLATES["spec_versioning"](cfg))
    add(".claude/learnings/README.md", TEMPLATES["learnings_readme"](cfg))
    add(".claude/sessions/README.md", TEMPLATES["sessions_readme"](cfg))

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
    # [WP1 / D4 (a)] build_plan now emits gates.py only for
    # gate_substrate "sdk-callable", which resolve_config refuses in
    # retrofit mode, so this pop is a no-op on every reachable config. It
    # stays as the retrofit track's explicit statement of the drop.
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

    # ---- R8.D skip [WP3 versioning-index, critic 3d] -------------------- #
    # RETROFIT.md R0.8's manifest emits spec-versioning.md "(if not
    # skipped)", and R0.5 step 7 records the decision as
    # skip_decisions.R8_D_spec_versioning, a key nothing read before WP3
    # (the state file only copied it). Drop the file and reword every
    # pointer to it (templates._SPEC_VERSIONING_POINTERS), last, so the
    # bodies replaced above are reworded too. A re-apply after an earlier
    # run removes the dropped file through the stale-file cleanup, like any
    # opt-out.
    if spec_versioning_skipped(cfg):
        by_path.pop(SPEC_VERSIONING_PATH, None)
        for path, a in list(by_path.items()):
            if isinstance(a.get("body"), str):
                by_path[path] = dict(
                    a, body=drop_spec_versioning_pointers(a["body"]))

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
# is a seam_version event, never a quiet edit. The Milestone-B substrate
# release extended the security-critical set with .claude/sdk_gates/gates.py
# under the seam MAJOR (seam SS9). spec-gate-entry is DELIBERATELY
# non-critical (warn-tier by the protocol's own entry-warn/commit-block
# split).
#
# [WP1 / D4 (a), owner decision 2026-09-27] The security-critical set is the
# SECURITY gates only. spec-gate-commit, test-gate, eval-gate, tdd-gate and
# format-lint-gate are quality gates: an operator who tunes one (a prefix, a
# timeout, a test command) is making a legitimate L-1 hand-edit, so a
# re-install SKIPs it with a notice and exits 0 instead of reporting the
# install unenforced. settings.json and gates.py keep the strict tier (see
# _hook_tier). This removal is a seam_version event recorded in
# SEAM-CONTRACT SS7.2 / SS10 in the same change.
TIER_SECURITY = "security-critical"
TIER_AUTONOMY = "autonomy-critical"
TIER_NON = "non-critical"
SECURITY_CRITICAL_HOOKS = frozenset({
    "secrets-gate", "dependency-gate",
})
AUTONOMY_CRITICAL_HOOKS = frozenset({
    "drift-detector-loop-cooperation", "iteration-summary-enforcement",
})
# Explicit warn/observability/quality tier. Membership here is a DELIBERATE
# non-critical decision, not a default: the forcing function below refuses
# to import while any emitted hook is missing from all three sets.
NON_CRITICAL_HOOKS = frozenset({
    "spec-gate-entry", "ci-mirror", "cost-log", "drift-detector",
    "task-done-alarm", "decision-required-alarm",
    # [WP1 / D4 (a)] quality gates, re-tiered out of security-critical.
    "spec-gate-commit", "test-gate", "eval-gate", "tdd-gate",
    "format-lint-gate",
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
    non-critical (a digest mismatch there is a legitimate L-1 hand-edit).

    [WP1 / D4 (a)] settings.json stays security-critical on every install,
    including one with both security gates off. It is co-owned and MERGED
    (_apply_settings_json), so an ordinary operator edit never reaches the
    skip path; only a file the installer cannot merge (not JSON, not an
    object, a symlink, an unmergeable `hooks`/`permissions` shape) is
    declined. It is the one registration site for EVERY hook, quality
    gates included, so a declined settings.json is never an L-1 hand-edit
    to wave through."""
    if action["kind"] == "settings":
        return TIER_SECURITY
    if action["kind"] == "sdk_gates":
        # Seam §9: under the SDK substrate this one file carries every
        # gate; it joins the security-critical set in the same release
        # that emits it (a seam_version event, landed with the substrate-
        # release seam bump - never a silent extension). [WP1 / D4 (a)] It
        # is emitted only when gate_substrate is "sdk-callable" (build_plan)
        # and still carries secrets-gate and dependency-gate, so it keeps
        # the strict tier.
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
               # [WP1 / D4 (a)] Hook scripts this run left alone because
               # they differ from what the installer last wrote, or it has
               # no record of writing them. Not an enforcement failure (rc
               # stays 0), but a config change a hook body embeds (a test
               # command, a path list) did not reach it, and one SKIP line
               # among ~60 on stdout is not a signal - so main() lists
               # these on stderr at the end of the run. Each entry is
               # {"path", "untracked"}; untracked means the manifest has no
               # record of the file, so main() must not call it "your edits".
               # [WP3 critic 1i] Also the kind "file" scripts in
               # _CONFIG_BEARING_SCRIPTS, which embed config the same way.
               "skipped_hooks": [],
               # Project-relative paths of operator content --force displaced.
               # [round-7] Planned paths that were a SYMLINK and are now a
               # regular file. A mid-transcript line is not a signal - a skip
               # buried on stdout line 29 of 60 is exactly how the original
               # unenforced-tree defect went unnoticed - so these are also
               # summarised at the end of the run.
               "symlinks_replaced": [],
               # The `settings.json.disabled` this run's settings.json CREATE
               # sat beside, if any: the protocol's documented way to turn
               # hooks off (Bootstrap-Protocol-v2-8-0.md "To disable hooks",
               # RETROFIT.md R8.A A.1), which that CREATE silently undoes.
               "hooks_reenabled": None,
               # [WP1 fix 4] Security-gate scripts an earlier install wrote
               # that this plan drops ({"path", "removed"}); hook
               # registrations dropped at a site no manifest recorded as ours,
               # and ones kept there because their script is not ours
               # ((event, matcher, command)). main() says each on stderr.
               "dropped_security": [],
               "dropped_registrations": [],
               "kept_off_registrations": [],
               # [WP2 IU-3] Paths the stale-file cleanup removed (or, on
               # --dry-run, would remove), so main() can say which dropped
               # registration's script stays on disk with nothing wiring it.
               "removed_paths": [],
               # [WP3 versioning-index] Every path the hand-edit guard
               # skipped this run, so main() can say what a skipped
               # operator-owned file (INDEX.md) did not receive.
               "skipped_paths": [],
               "backups": [],
               # [WP3 / D2] Git hooks this run did not install, and why
               # ({"name", "path", "state", "detail", "rel"}); main() says
               # each on stderr. See _apply_git_hooks.
               "git_hooks": [],
               # [WP3 / D6] What main() says on stderr about a
               # worktree.baseRef in the operator's settings.json that is
               # not ours: "fresh", or null (see _worktree_note). rc stays
               # 0; any other value is declined, rc 3 (critic 5e). [WP3 /
               # model assignment] Also an ultracode opt-out that a value
               # this installer does not own overrides (_contributed_note).
               "settings_notes": []}

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
                                 bak_root, dry=dry, force=force, cfg=cfg)
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
                    summary["skipped_paths"].append(action["path"])
                    reason = _skip_reason(untracked, prev is None)
                    print(f"  SKIP   {action['path']}  ({reason}; "
                          f"use --force to overwrite)")
                    tier = _hook_tier(action)
                    if tier == TIER_SECURITY:
                        summary["skipped_security"].append(
                            {"path": action["path"], "reason": reason})
                    elif (action["kind"] == "hook"
                          or action["path"] in _CONFIG_BEARING_SCRIPTS):
                        summary["skipped_hooks"].append(
                            {"path": action["path"], "untracked": untracked})
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
        # [WP3 / D2] Git-hook shims are not plan actions; _apply_git_hooks
        # installs and retires them.
        if path in planned_paths or known.get("kind") in ("gitignore_root",
                                                          "git_hook"):
            continue
        target = root / path
        if not target.exists():
            continue
        try:
            on_disk = _digest(target.read_text())
        except (OSError, ValueError):     # unreadable, or not UTF-8: KEEP it
            on_disk = None
        removed = (on_disk is not None and known.get("digest") == on_disk
                   and known.get("state") != "skipped-local-edit")
        # [WP1 fix 4] A security gate that ran stops running at rc 0 (D3
        # made the policy switches the master switches, and a pre-WP1
        # config can carry a `false` that did not turn the gate off). The
        # REMOVE or KEEP line below is one among ~60, so main() says it too.
        # Keyed on the path, not the row's kind: a row an install skipped
        # (an edited or untracked gate) is written with no kind.
        if path.startswith(".claude/hooks/") and Path(path).name.removesuffix(
                ".sh") in SECURITY_CRITICAL_HOOKS:
            summary["dropped_security"].append(
                {"path": path, "removed": removed})
        if removed:
            if not dry:
                target.unlink()
            summary["removed"] += 1
            summary["removed_paths"].append(path)
            tag = "REMOVE (dry run)" if dry else "REMOVE"
            print(f"  {tag} {path}  (dropped from plan on re-apply)")
        else:
            print(f"  KEEP   {path}  (dropped from plan but locally "
                  f"modified; left in place)", file=sys.stderr)

    # [WP3 / D2] The spec check's git-hook shims: after the stale-file
    # cleanup (which skips their rows), before the manifest is written.
    _apply_git_hooks(root, plan, manifest, summary, prev_files, cfg=cfg,
                     dry=dry,
                     force=force, adopt=adopt)

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
# tests/test_settings_merge.py asserts that every top-level key our own
# emission produces is claimed here, shared or contributed (below), so a key
# added to _settings_json without a co-ownership decision fails loudly instead
# of silently becoming operator-owned and never updated again. [WP3 / model
# assignment: this named test_wiring_verification.py and "the two shared
# keys"; the row lives in test_settings_merge.py, and D6 added a third.]
_SETTINGS_OWNED_KEYS = ("$schema", "_generatedBy", "_note_mcp")
# [WP3 / D6] `worktree` is shared by SUB-KEY, like `permissions.deny` by rule:
# we contribute `worktree.baseRef` and own only what we added (manifest
# `owned_worktree`, {sub-key: the value we wrote}). Owning the whole object
# would delete an operator's `worktree.symlinkDirectories` and the rest, and
# popping it on a config that does not emit it would too (_merge_settings
# pops an owned key our emission lacks).
_SETTINGS_SHARED_KEYS = ("hooks", "permissions", "worktree")
# [WP3 / model assignment, operator decision 2026-10-05] Top-level keys we
# CONTRIBUTE only where the operator has none, and own only while they hold
# the value we wrote (manifest `contributed_keys`, {key: value we wrote}).
# An operator's own value, `true` or `false`, is never replaced, and a value
# of ours that the config no longer emits is removed. Owning `ultracode`
# outright (the model-assignment prototype, fx3) overwrote an operator's
# `false` with `true` beneath "operator settings untouched".
_SETTINGS_CONTRIBUTED_KEYS = ("ultracode",)


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
    # [WP3 / D6] We write one sub-key into `worktree`; a non-object there
    # cannot take it. Claude Code rejects such a file anyway.
    wt = theirs.get("worktree")
    if wt is not None and not isinstance(wt, dict):
        return (f"existing settings.json has a `worktree` key that is a "
                f"{type(wt).__name__}, not an object")
    # [WP3 critic 5e, operator ruling 2026-10-05 (Q15)] A baseRef Claude
    # Code rejects makes it ignore the WHOLE file, every hook and deny rule
    # included (WP3 scout facts-cc C1-invalid: "local", measured on
    # 2.1.289), so a merge that kept it would install gates that never run.
    # Declined like a non-object `worktree`: exit 3. A null is the one
    # value that only warns (operator ruling; _worktree_note).
    if isinstance(wt, dict) and "baseRef" in wt:
        from templates import WORKTREE_BASE_REFS
        ref = wt["baseRef"]
        if ref is not None and ref not in WORKTREE_BASE_REFS:
            return (f"existing settings.json sets worktree.baseRef to "
                    f"{json.dumps(ref)}, which Claude Code rejects, and it "
                    f"then ignores the whole file, every hook and deny rule "
                    f"included; set it to \"head\" or \"fresh\", or delete "
                    f"it, and re-run")
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


_QUOTED_CPD = '"$CLAUDE_PROJECT_DIR"/'


def _unquoted_spellings(sites) -> set:
    """[WP1] Each site we emit, spelled the way installers before WP1 spelled
    it: `$CLAUDE_PROJECT_DIR/...` with the placeholder unquoted.

    Without these, a re-install over a tree with no manifest - a fresh clone,
    since the manifest is gitignored - reads every earlier registration as
    the operator's (its command no longer equals ours) and keeps it beside
    ours, so every hook runs TWICE.
    Same site only (event, matcher), which is the residual `_merge_hooks`
    already accepts: a registration at exactly the site we emit is ours.
    """
    return {(ev, m, "$CLAUDE_PROJECT_DIR/" + c[len(_QUOTED_CPD):])
            for ev, m, c in sites if c.startswith(_QUOTED_CPD)}


def _merge_hooks(ours: dict, theirs: dict, prev_owned: list | None,
                 dropped: list | None = None, keep_off=None,
                 kept_off: list | None = None) -> tuple[dict, list]:
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

    [WP1 fix 4] The same residual covers a hook this run does NOT emit: a
    registration at exactly the site we would emit it at, in either
    spelling, is ours and is dropped. Without this, a tree whose manifest
    records no ownership (every fresh clone, since the manifest is
    gitignored, and every manifest older than `owned_hooks`) kept the
    registration of a hook the config turned off - D3's policy switches
    included - so it went on running, or dangled at exit 127 once its script
    was removed. Each such drop the manifest did not record is appended to
    `dropped`, so the caller can say it.

    Where the manifest DOES record ownership (`prev_owned` is a list of site
    triples, possibly empty; None means no record), a registration there that
    it does not record is the operator's unless its script says otherwise:
    `keep_off(command)` is true when that script is on disk and is neither
    what this installer renders for the hook nor the copy the manifest
    recorded, and then the registration is kept - an operator's own
    eval-gate.sh on an archetype that never installs one, say - and appended
    to `kept_off`. A missing script, or this config's render restored by git,
    is still dropped.
    """
    ours_sites = _hook_sites(ours)
    prev_sites, legacy_cmds = _split_owned_hooks(prev_owned)
    # A bare-command (pre-site) record cannot say where we put anything, so
    # it counts as no record here, as a missing one does.
    recorded = isinstance(prev_owned, list) and (bool(prev_sites)
                                                 or not legacy_cmds)
    ours_cmds = {c for _, _, c in ours_sites}
    off = {(ev, m, f"{_QUOTED_CPD}.claude/hooks/{hk}.sh")
           for hk in HOOK_EVENT_MAP
           if f"{_QUOTED_CPD}.claude/hooks/{hk}.sh" not in ours_cmds
           for ev, m in [HOOK_EVENT_MAP[hk]] + HOOK_EXTRA_EVENTS.get(hk, [])}
    off |= _unquoted_spellings(off)
    # [WP2] A site an EARLIER installer registered a hook at, and this one
    # never does (templates.HOOK_RETIRED_SITES), is ours in either spelling,
    # manifest or not, whether or not this run emits the hook.
    retired = {(ev, m, f"{_QUOTED_CPD}.claude/hooks/{hk}.sh")
               for hk, sites in HOOK_RETIRED_SITES.items()
               for ev, m in sites}
    retired |= _unquoted_spellings(retired)
    # [WP2 IU-2/IU-3] A retired site of a hook this run does NOT emit is
    # treated exactly like an off site: kept when the manifest records
    # ownership and the script is the operator's (keep_off), and otherwise
    # dropped and, when no manifest recorded it, reported in `dropped`. A
    # retired site of a hook this run still emits is a move, not a drop:
    # the hook runs at its new site, so that registration goes silently.
    retired_off = {(ev, m, f"{_QUOTED_CPD}.claude/hooks/{hk}.sh")
                   for hk, sites in HOOK_RETIRED_SITES.items()
                   if f"{_QUOTED_CPD}.claude/hooks/{hk}.sh" not in ours_cmds
                   for ev, m in sites}
    retired_off |= _unquoted_spellings(retired_off)
    unrecorded_off = (off | retired_off) - prev_sites
    drop_sites = (prev_sites | {tuple(s) for s in ours_sites}
                  | _unquoted_spellings(ours_sites) | off | retired)
    # A manifest written before ownership became site-keyed names a bare
    # command and cannot say where we put it. Retire one only when our
    # emission no longer carries it at all - its file is deleted this run, so
    # a surviving registration would dangle at rc=127. While we still emit it,
    # site matching covers our own copy and a registration anywhere else is
    # the operator's.
    # [WP1] "Still carries it" includes carrying it under the quoted spelling:
    # the script is not deleted, so the operator's registration of it at a
    # site of their own is theirs, exactly as before the spelling changed.
    carried = ours_cmds | {c for _, _, c in _unquoted_spellings(ours_sites)}
    drop_cmds = {c for c in legacy_cmds if c not in carried}

    merged: dict = {}
    for event, groups in theirs.items():
        kept_groups = []
        for grp in groups:
            if not isinstance(grp, dict) \
                    or not isinstance(grp.get("hooks"), list):
                kept_groups.append(grp)            # opaque; leave it alone
                continue
            matcher = grp.get("matcher")
            kept = []
            for e in grp["hooks"]:
                if not _is_ours_here(event, matcher, e,
                                     drop_sites, drop_cmds):
                    kept.append(e)
                    continue
                only_off = (_is_ours_here(event, matcher, e,
                                          unrecorded_off, set())
                            and not _is_ours_here(event, matcher, e,
                                                  drop_sites - unrecorded_off,
                                                  drop_cmds))
                if only_off and recorded and keep_off is not None \
                        and keep_off(e["command"]):
                    kept.append(e)
                    if kept_off is not None:
                        kept_off.append((event, matcher, e["command"]))
                elif only_off and dropped is not None:
                    dropped.append((event, matcher, e["command"]))
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


def _merge_worktree(ours_wt: dict, theirs_wt, prev_owned) -> tuple[dict, dict]:
    """[WP3 / D6] Merge the `worktree` object by sub-key. Returns (merged
    object, {sub-key: value} this run owns).

    A sub-key we wrote on a previous run, still holding the value we wrote,
    is ours to update or retire. Every other sub-key is the operator's and
    is kept as it is, even where we emit the same name: an operator's
    explicit `baseRef: "fresh"` stays, and so does a value they changed ours
    to (it stopped matching what we wrote, so they own it now). With no
    record (a fresh clone) everything already there reads as theirs; the
    residual is a stale `baseRef` left by --uninstall, never one deleted."""
    prev = prev_owned if isinstance(prev_owned, dict) else {}
    theirs_wt = theirs_wt if isinstance(theirs_wt, dict) else {}
    merged = {k: v for k, v in theirs_wt.items()
              if not (k in prev and v == prev[k])}
    owned = {}
    for k, v in (ours_wt or {}).items():
        if k in merged:
            continue
        merged[k] = v
        owned[k] = v
    return merged, owned


def _contributed(ours: dict) -> dict:
    """[WP3 / model assignment] The contributed top-level keys our emission
    carries, as {key: value}."""
    return {k: ours[k] for k in _SETTINGS_CONTRIBUTED_KEYS if k in ours}


def _same_value(a, b) -> bool:
    """Equal AND the same JSON type: an operator's `1` is not our `true`,
    though Python reads `1 == True`."""
    return type(a) is type(b) and a == b


def _merge_contributed(ours: dict, theirs: dict,
                       prev_owned) -> tuple[dict, dict]:
    """[WP3 / model assignment] Merge the contributed top-level keys
    (_SETTINGS_CONTRIBUTED_KEYS). Returns ({key: value} the merged file
    carries, {key: value} this run owns).

    A key we wrote on a previous run that still holds the value we wrote is
    ours to update or retire. Any other value is the operator's and stays,
    even one equal to ours. With no record (a fresh clone: the manifest is
    gitignored) an earlier install's `true` therefore reads as theirs, never
    one deleted; _contributed_note says so when the config turned it off."""
    prev = prev_owned if isinstance(prev_owned, dict) else {}
    kept = {k: theirs[k] for k in _SETTINGS_CONTRIBUTED_KEYS
            if k in theirs
            and not (k in prev and _same_value(theirs[k], prev[k]))}
    owned = {k: v for k, v in _contributed(ours).items() if k not in kept}
    return dict(kept, **owned), owned


def _contributed_note(merged: dict, ours: dict) -> str | None:
    """[WP3 / model assignment] What to tell the operator when the config
    turned ultracode off (our emission lacks the key) but the merged file
    still turns it on. Such a value is never ours (_merge_contributed drops
    ours when the emission lacks the key): it is theirs, or an earlier
    install's that no manifest records. None otherwise."""
    if ("ultracode" in ours or merged.get("ultracode") is not True):
        return None
    return (".claude/settings.json sets \"ultracode\": true, and no install "
            "record says this installer wrote it (yours, or an earlier "
            "install's in a checkout without the gitignored manifest), so "
            "it was kept although workflow.ultracode is false. Delete the "
            "key from .claude/settings.json to turn ultracode off for this "
            "project.")


def _worktree_note(wt) -> str | None:
    """[WP3 / D6] What to tell the operator about the `worktree.baseRef` of
    the merged settings.json `worktree` object `wt`, or None when it is
    ours ("head") or absent."""
    from templates import WORKTREE_BASE_REF, WORKTREE_BASE_REFS
    if not isinstance(wt, dict) or "baseRef" not in wt:
        return None
    value = wt["baseRef"]
    if value is None:
        # [WP3 critic 5e, operator ruling 2026-10-05] Kept, with a warning,
        # where any other value Claude Code rejects is declined (exit 3,
        # _settings_unmergeable_reason). An operator may write null to mean
        # "unset"; Claude Code does not read it that way (d6 rebuild
        # verifier: `claude doctor` on 2.1.289).
        return (".claude/settings.json sets worktree.baseRef to null, which "
                "Claude Code reports as an invalid value (`claude doctor`, "
                "2.1.289); a baseRef it rejects makes it ignore the WHOLE "
                "file, every hook and deny rule included (measured for "
                "\"local\"). Delete the key, or set it to \"head\" or "
                "\"fresh\".")
    if value in WORKTREE_BASE_REFS and value != WORKTREE_BASE_REF:
        return (f".claude/settings.json sets worktree.baseRef to "
                f"{json.dumps(value)} (yours, kept): implementer worktrees "
                f"start from origin's default branch, so a spec or task "
                f"committed here but not pushed is missing from them. "
                f"\"head\" starts them from this checkout's HEAD.")
    # "head", ours. Any other value never gets here: the merge declined it
    # (_settings_unmergeable_reason, exit 3).
    return None


def _merge_settings(ours: dict, theirs: dict, prev_owned_deny: list,
                    prev_owned_hooks: list | None,
                    dropped: list | None = None,
                    keep_off=None,
                    kept_off: list | None = None,
                    prev_owned_worktree: dict | None = None,
                    owned_worktree: dict | None = None,
                    prev_contributed: dict | None = None,
                    contributed: dict | None = None
                    ) -> tuple[dict, list, list]:
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
        prev_owned_hooks, dropped, keep_off, kept_off)
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

    # [WP3 / D6] `worktree`, by sub-key. `owned_worktree` is an OUT
    # parameter (the return shape is pinned by tests/test_settings_merge.py).
    new_wt, owned_wt = _merge_worktree(ours.get("worktree") or {},
                                       theirs.get("worktree"),
                                       prev_owned_worktree)
    if new_wt:
        merged["worktree"] = new_wt
    else:
        merged.pop("worktree", None)
    if owned_worktree is not None:
        owned_worktree.clear()
        owned_worktree.update(owned_wt)

    # [WP3 / model assignment] Contributed keys (`ultracode`): the
    # operator's value stays; ours is added only where they have none.
    # `contributed` is an OUT parameter, like `owned_worktree`.
    new_c, owned_c = _merge_contributed(ours, theirs, prev_contributed)
    for key in _SETTINGS_CONTRIBUTED_KEYS:
        if key in new_c:
            merged[key] = new_c[key]
        else:
            merged.pop(key, None)
    if contributed is not None:
        contributed.clear()
        contributed.update(owned_c)
    return merged, owned_deny, owned_hooks


# [WP3 critic 1i] Kind "file" scripts that carry config the way a hook body
# does, so a kept local edit gets the same stderr line as an edited hook
# (main(): "a config change it embeds ... does NOT reach it"). Each value
# names what it embeds. Two verifiers measured a stdout-only SKIP for an
# edited dispatch and spec-check.sh: a mode flip or a prefix change then
# silently never reached them.
_CONFIG_BEARING_SCRIPTS = {
    ".claude/githooks/dispatch": "hooks.spec_gate_commit_mode",
    ".claude/githooks/spec-check.sh": "hooks.spec_gate_commit_prefixes",
    ".claude/merge-back.sh": "which commit gates it runs",
}


def _apply_settings_json(root: Path, action: dict, manifest: dict,
                         summary: dict, prev_files: dict, bak_root: Path, *,
                         dry: bool, force: bool,
                         cfg: dict | None = None) -> None:
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
            # [WP3 / D6] What we wrote into `worktree`, as for deny rules.
            "owned_worktree": dict(ours.get("worktree") or {}),
            # [WP3 / model assignment] And the contributed keys we wrote.
            "contributed_keys": _contributed(ours),
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
        # [WP1 fix 4] The ownership record too: this run wrote nothing, so
        # what an earlier run recorded is still true. Dropping it made the
        # next run read the tree as having no record and drop the operator's
        # own registrations at a site of a hook this config does not install.
        for key in ("owned_deny", "owned_hooks", "owned_worktree",
                    "contributed_keys"):
            if isinstance(known, dict) and key in known:
                row[key] = known[key]
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
        disabled = target.with_name(target.name + ".disabled")
        if disabled.exists():
            summary["hooks_reenabled"] = str(disabled.relative_to(root))
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

    def _keep_off(cmd: str) -> bool:
        """[WP1 fix 4] Is the script this registration runs the operator's?
        Missing: no (the registration would dangle). The body this installer
        renders for that hook, or a copy the manifest recorded: no."""
        rel = _resolved_hook_path(cmd)
        if rel is None:
            return False
        try:
            raw = (root / rel).read_bytes()
        except OSError:
            return False
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:  # never a render of ours: all are UTF-8
            return True
        # Newlines read the way read_text() reads them, as the manifest digest
        # and _classify do: a CRLF checkout of our own render is still ours.
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        name = Path(rel).name.removesuffix(".sh")
        if cfg is not None and name in HOOK_EVENT_MAP:
            try:
                if text == TEMPLATES["hook"](name, cfg):
                    return False
            except Exception:       # a hook this config cannot render
                pass
        rec = prev_files.get(rel)
        return not (isinstance(rec, dict)
                    and rec.get("digest") == _digest(text))

    owned_worktree: dict = {}
    contributed: dict = {}
    merged, owned_deny, owned_hooks = _merge_settings(
        ours, theirs,
        (known or {}).get("owned_deny") or [],
        (known or {}).get("owned_hooks"),
        summary["dropped_registrations"], _keep_off,
        summary["kept_off_registrations"],
        (known or {}).get("owned_worktree"), owned_worktree,
        (known or {}).get("contributed_keys"), contributed)
    new_text = json.dumps(merged, indent=2) + "\n"
    # [WP3 / D6] An operator's own baseRef stays; say what it costs.
    _wt = merged.get("worktree")
    note = _worktree_note(_wt)
    if note:
        summary["settings_notes"].append(note)
    # [WP3 / model assignment] An opt-out that could not take effect.
    note = _contributed_note(merged, ours)
    if note:
        summary["settings_notes"].append(note)

    co_owned = {
        "path": action["path"],
        "kind": action["kind"],
        "state": "settings-merged",
        "block_digest": _digest(body),
        "owned_deny": owned_deny,
        "owned_hooks": owned_hooks,
        "owned_worktree": owned_worktree,
        "contributed_keys": contributed,
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

    # [WP3 / D6] `worktree` sub-keys we wrote, while they still hold the
    # value we wrote; the operator's stay.
    owned_wt = entry.get("owned_worktree")
    wt = cur.get("worktree")
    if isinstance(owned_wt, dict) and isinstance(wt, dict):
        for k, v in owned_wt.items():
            if k in wt and wt[k] == v:
                del wt[k]
        if not wt:
            cur.pop("worktree", None)

    # [WP3 / model assignment] A contributed key goes while it still holds
    # the value we wrote; the operator's own value stays.
    contrib = entry.get("contributed_keys")
    if isinstance(contrib, dict):
        for k, v in contrib.items():
            if (k in _SETTINGS_CONTRIBUTED_KEYS and k in cur
                    and _same_value(cur[k], v)):
                del cur[k]

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


# [WP1] What an UNQUOTED parameter expansion does to its value after it
# expands: default-IFS field splitting (space, tab, newline) and pathname
# expansion (`*`, `?`, `[`). A root with none of these expands to itself
# whether or not the placeholder is quoted, so only such a root can break a
# command that `_resolved_hook_path` resolves.
_SPLIT_OR_GLOB = frozenset(" \t\n*?[")
# The first word begins with the bare placeholder, outside any quotes. Empty
# quote pairs in front are skipped the way the shell skips them. Applied only
# to commands `_resolved_hook_path` resolves, whose first word, once its
# quotes are removed, starts with `$CLAUDE_PROJECT_DIR/`.
_UNQUOTED_CPD = re.compile(
    r"""[ \t]*(?:""|'')*\$CLAUDE_PROJECT_DIR(?![A-Za-z0-9_])""")


def _splits_in(root: Path, command: str) -> bool:
    """Would `sh -c` split or glob this hook command's script path in `root`?

    Claude Code runs a shell-form hook (one with no `args`) through `sh -c`
    with CLAUDE_PROJECT_DIR exported. `$CLAUDE_PROJECT_DIR/.claude/hooks/x.sh`
    in `/home/me/My Project` runs `/home/me/My`, which exits 127 - a
    NON-BLOCKING error, so the gate is off while nothing says so. The quoted
    spelling `"$CLAUDE_PROJECT_DIR"/...` expands to exactly one word in any
    root.
    """
    return (bool(_SPLIT_OR_GLOB & set(str(root)))
            and _UNQUOTED_CPD.match(command) is not None)


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


def unstartable_hooks(root: Path) -> list[str]:
    """[WP1] One message per settings.json hook command that begins with
    an unquoted $CLAUDE_PROJECT_DIR/ in a root that contains a space, tab,
    newline or glob character, which `sh -c` splits or expands. Reported
    per command, because a correct registration of
    the same script elsewhere does not rescue this one.

    Advisory, not a verify_wiring problem (owner ruling, WP1): every
    registration this installer writes is quoted, and a re-install replaces
    the unquoted spelling at each site it emits (_merge_hooks), so what is
    left is the operator's own registration. main() prints a `warning:` and
    the exit status is unchanged. Tolerant of any file shape, like
    _registered_commands: verify_wiring reports an unreadable settings.json.
    """
    try:
        settings = json.loads(
            (root / ".claude" / "settings.json").read_text())
    except (OSError, ValueError):
        return []
    if not isinstance(settings, dict):
        return []
    return [f".claude/settings.json runs `{cmd}` with $CLAUDE_PROJECT_DIR "
            f"unquoted, and this project's path contains a space, tab, "
            f"newline or glob character. Claude Code runs hooks with "
            f"`sh -c`, which splits or expands such a path, so this hook "
            f"may not run. Write the placeholder as "
            f"\"$CLAUDE_PROJECT_DIR\"."
            for cmd in sorted({c for c in _registered_commands(settings)
                               if _resolved_hook_path(c) is not None
                               and _splits_in(root, c)})]


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


# --------------------------------------------------------------------------- #
# [WP3 / D2] Git hooks for the spec check - installer-managed shims
# --------------------------------------------------------------------------- #
# The shims are the installer's first write into a repository's hooks
# directory. The rules, each from a measured failure of the alternatives:
#   * Write <git-common-dir>/hooks/{pre-commit,pre-merge-commit}. The
#     common directory is shared by every linked worktree, so one shim
#     fires in each implementer worktree. A RELATIVE core.hooksPath
#     resolves per worktree instead, and a worktree whose branch lacks the
#     directory runs no hook at all, silently.
#   * Never write over a hook this installer did not write (no marker),
#     with or without --force, and never rename one to chain it: hook
#     managers rename and re-run hooks too, and two tools chaining each
#     other's renamed files can recurse. Leave it, and say which line to
#     add to it.
#   * Never set core.hooksPath. When it is already set (husky does), git
#     ignores .git/hooks, so write nothing and say so.
#   * A shim this installer wrote follows the normal file rules: updated
#     while unedited, kept (and reported) once edited, --force backs it up
#     and overwrites it, --uninstall removes it only while unedited.
#   * No repository, or no git: write nothing, say so, and let a re-install
#     after `git init` add them. Nothing here changes the exit status: the
#     PreToolUse spec-gate-commit hook still runs, and these are quality
#     gates (seam SS7.2 non-critical tier).
_GIT_ENV_DROP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
                 "GIT_COMMON_DIR", "GIT_PREFIX", "GIT_OBJECT_DIRECTORY")


def _git_out(root: Path, *args: str):
    """(returncode, stdout) of `git -C root ARGS`, or None when git cannot
    be run. The caller's GIT_DIR and friends are dropped: an install run
    from inside a git hook would otherwise inspect that hook's repository."""
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV_DROP}
    try:
        r = subprocess.run(["git", "-C", str(root), *args], env=env,
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return r.returncode, r.stdout.rstrip("\n")


def _git_hooks_target(root: Path):
    """Where the shims go: (hooks_dir, rel, None), where rel is the project
    directory relative to the repository's top level ("." when equal).
    Otherwise (None, rel_or_None, (code, detail)) saying why not."""
    probe = _git_out(root, "rev-parse", "--is-inside-work-tree")
    if probe is None:
        return None, None, ("no-git-binary", "")
    if probe[0] != 0 or probe[1] != "true":
        return None, None, ("no-repo", "")
    loc = _git_out(root, "rev-parse", "--show-toplevel", "--git-common-dir",
                   "--show-prefix")
    if loc is None or loc[0] != 0:
        return None, None, ("no-repo", "")
    lines = loc[1].split("\n") + ["", "", ""]
    top, common, prefix = Path(lines[0]), Path(lines[1]), lines[2]
    if not common.is_absolute():
        common = root / common
    rel = prefix.rstrip("/") or "."
    if rel != ".":
        # A project inside a larger repository (a monorepo package, or a
        # directory under a home-directory repository): hooks there would
        # run for every commit in that repository. [WP3 fix1, operator
        # decision 2026-10-06 (2)] The spec check itself works there: it
        # polices the project's own paths against its own .claude/specs
        # (spec-check.sh and gates.py), through the PreToolUse fallback.
        return None, rel, ("not-top", str(top))
    hooks = Path(os.path.abspath(common)) / "hooks"
    hp = _git_out(root, "config", "--get", "core.hooksPath")
    if hp is not None and hp[0] == 0 and hp[1] == "":
        # [WP3 fix3 HD-5] Set to an empty value: git runs no hook at all
        # (measured on git 2.38.0, 2.49.1 and 2.55.0), so a shim in
        # .git/hooks would not run either.
        return None, rel, ("hooks-off", "")
    if hp is not None and hp[0] == 0 and hp[1].strip():
        val = os.path.expanduser(hp[1].strip())
        where = Path(val) if os.path.isabs(val) else top / val
        if os.path.realpath(where) != os.path.realpath(hooks):
            return None, rel, ("hooks-path", hp[1].strip())
    if hooks.is_symlink():
        return None, rel, ("hooks-dir-symlink", os.readlink(hooks))
    return hooks, rel, None


def _hook_manager_of(text) -> str | None:
    """Name the tool that wrote a foreign hook, when its file says so."""
    if text is None:
        return None
    low = text.lower()
    if "pre-commit.com" in low or "file generated by pre-commit" in low:
        return "the pre-commit framework"
    if "lefthook" in low:
        return "lefthook"
    if "husky" in low:
        return "husky"
    return None


# [WP3 fix1 INST-3] A hook this installer did not write that already runs
# the check: the operator followed the warning's remedy (a husky hook under
# core.hooksPath, a hand-written one), or a hook manager runs it from its
# own config file. [WP3 fix2 IT-1, IT-2, RG-2] Its TEXT cannot say so: a
# line after husky 9's `. h` (which ends in `exit`), after the pre-commit
# framework's `exec`, or in a comment never runs, and git skips a file that
# is not executable. Read that way, a re-install said "nothing to install"
# (and the PreToolUse fallback went quiet) while the check ran nowhere. So
# only this installer's own shim, byte for byte and executable, counts as
# running the check; a hook that mentions the line gets a warning that says
# so and how to confirm it, not the plain remedy it already follows.
_MANAGER_CONFIGS = {
    "lefthook": tuple(f"{dot}lefthook{local}.{ext}" for dot in ("", ".")
                      for local in ("", "-local")
                      for ext in ("yml", "yaml", "toml", "json")),
    "the pre-commit framework": (".pre-commit-config.yaml",),
}


def _mentions_dispatch(text, name: str) -> bool:
    """Does a hook file (or a hook manager's config) hold the text
    `.claude/githooks/dispatch <name>`. A mention only: see above."""
    from templates import GIT_HOOK_DISPATCH
    return text is not None and f"{GIT_HOOK_DISPATCH} {name}" in text


def _guarded_line(name: str) -> str:
    """[WP3 fix1 INST-6, fix3 HD-1] The line every remedy gives for hook
    `name`. The guard lets a commit through where there is no dispatch, as
    the installer's own shim does: on a branch cut before the install, in a
    repository that shares the hooks directory, and after the spec gate is
    turned off (hooks.spec_gate_commit: false and a re-install remove
    dispatch). Unguarded, the line exits 127 there and git refuses every
    commit, a person's too."""
    from templates import GIT_HOOK_DISPATCH as cmd
    return f"if [ -f {cmd} ]; then bash {cmd} {name} || exit 1; fi"


def _manager_mentions_dispatch(root: Path, manager, name: str) -> str | None:
    """The config file at the repository top in which `manager` mentions
    the check for `name`, if one does; else None."""
    names = _MANAGER_CONFIGS.get(manager)
    loc = _git_out(root, "rev-parse", "--show-toplevel") if names else None
    if not names or loc is None or loc[0] != 0 or not loc[1]:
        return None
    for fn in names:
        try:
            text = (Path(loc[1]) / fn).read_text(errors="replace")
        except (OSError, ValueError):
            continue
        if _mentions_dispatch(text, name):
            return fn
    return None


def _husky9_user_hook(where: Path, name: str):
    """husky 9 points core.hooksPath at <dir>/_ and writes there a wrapper
    per hook that sources `h`, which runs <dir>/<name> with sh and then
    exits: a line added to the wrapper never runs, and husky rewrites the
    directory. The file to edit is <dir>/<name>; None when `where` is not
    that layout."""
    if where.name != "_" or not (where / "h").is_file():
        return None
    try:
        wrapper = (where / name).read_text(errors="replace")
    except (OSError, ValueError):
        return None
    if not re.search(r'(?m)^\.\s.*/h"?\s*$', wrapper):
        return None
    return where.parent / name


def _hook_state(path: Path, name: str, shim: str) -> str:
    """[WP3 fix2 IT-1, IT-2, RG-2] What git would run as hook `name` at
    `path`: "absent"; "noexec" (git skips it, with a hint); "shim" (this
    installer's, byte for byte, executable: the only state that counts as
    running the check); "mentions" (it holds the dispatch line, which may
    or may not run); or "other". [WP3 fix3 HD-3] "noexec-other": git skips
    it and it does not hold the line, so it needs the line too."""
    if not os.path.lexists(path):
        return "absent"
    try:
        text = path.read_text(errors="replace")
    except (OSError, ValueError):
        text = None
    if not os.access(path, os.X_OK):
        return "noexec" if _mentions_dispatch(text, name) else "noexec-other"
    if text == shim:
        return "shim"
    return "mentions" if _mentions_dispatch(text, name) else "other"


def _gate_off_mentions(root: Path) -> dict:
    """[WP3 fix3 HD-1] With the spec gate off: {file: [hook names]} for each
    hook git runs here (husky 9's .husky/<hook> for its wrapper), or lefthook
    or pre-commit framework config at the repository top, that still
    mentions the dispatch line. None below the top, where no remedy gave
    one, and none in a core.hooksPath every repository reads. A shim this
    installer wrote is the retire step's (its marker)."""
    from templates import GIT_HOOK_MARKER, GIT_HOOK_NAMES
    hooks, _rel, why = _git_hooks_target(root)
    if why is not None and why[0] in ("no-git-binary", "no-repo", "not-top"):
        return {}
    if why is not None and why[0] == "hooks-path":
        # A directory every repository uses holds lines for the others too,
        # and INST-6 always gave it the guarded one: leave it out.
        where, shared = _hooks_path_where(root, why[1])
        hooks = None if shared else where
    loc = _git_out(root, "rev-parse", "--show-toplevel")
    top = Path(loc[1]) if loc is not None and loc[0] == 0 else root
    found: dict = {}
    for n in GIT_HOOK_NAMES:
        files = []
        if hooks is not None:
            user = _husky9_user_hook(hooks, n)
            files.append(user if user is not None else hooks / n)
        for m in _MANAGER_CONFIGS:
            fn = _manager_mentions_dispatch(root, m, n)
            if fn:
                files.append(top / fn)
        for f in files:
            try:
                text = f.read_text(errors="replace")
            except (OSError, ValueError):
                continue
            if GIT_HOOK_MARKER not in text and _mentions_dispatch(text, n):
                found.setdefault(f, []).append(n)
    return found


def _hooks_path_where(root: Path, value: str):
    """(directory, shared) for a core.hooksPath value: where git looks for
    hooks, and whether that setting comes from a config every repository
    on the machine reads (global, system, or a -c on the command line).
    [WP3 fix1 INST-6] A remedy for a shared directory must not run dispatch
    unguarded: that hook fires in every repository, and where dispatch does
    not exist it exits 127 and git refuses every commit, a person's too."""
    loc = _git_out(root, "rev-parse", "--show-toplevel")
    top = Path(loc[1]) if loc is not None and loc[0] == 0 else root
    val = os.path.expanduser(value)
    where = Path(val) if os.path.isabs(val) else top / val
    scope = _git_out(root, "config", "--show-scope", "--get",
                     "core.hooksPath")
    if scope is not None and scope[0] == 0 and scope[1]:
        return where, scope[1].split()[0] not in ("local", "worktree")
    # git before 2.26 has no --show-scope: shared unless the repository's
    # own config sets it.
    own = _git_out(root, "config", "--local", "--get", "core.hooksPath")
    return where, not (own is not None and own[0] == 0 and own[1].strip())


def _apply_git_hooks(root: Path, plan: list[dict], manifest: dict,
                     summary: dict, prev_files: dict, *, cfg: dict, dry: bool,
                     force: bool, adopt: bool) -> None:
    """[WP3 / D2] Install, update or retire the spec check's git-hook shims.
    The plan decides whether they should exist: they follow the
    .claude/githooks/dispatch action, which build_plan emits exactly when
    it emits spec-gate-commit."""
    from templates import GIT_HOOK_DISPATCH, GIT_HOOK_MARKER, GIT_HOOK_NAMES

    want = any(a["path"] == GIT_HOOK_DISPATCH for a in plan)
    prev_rows = {p: f for p, f in prev_files.items()
                 if f.get("kind") == "git_hook"}
    root_r = Path(os.path.abspath(root))

    def shown(p: Path) -> str:
        try:
            return str(Path(os.path.abspath(p)).relative_to(root_r))
        except ValueError:
            return str(Path(os.path.abspath(p)))

    def located(path: str) -> Path:
        return Path(path) if os.path.isabs(path) else root / path

    def read(p: Path):
        try:
            return p.read_text()
        except (OSError, ValueError):
            return None

    if not want:
        # The plan dropped the spec gate (hooks.spec_gate_commit: false):
        # retire each shim an earlier run wrote, while it is unedited.
        for path, known in prev_rows.items():
            target = located(path)
            if target.is_symlink() or not target.is_file():
                continue
            text = read(target)
            if (text is not None and known.get("digest") == _digest(text)
                    and known.get("state") != "skipped-local-edit"):
                if not dry:
                    target.unlink()
                summary["removed"] += 1
                summary["removed_paths"].append(path)
                tag = "REMOVE (dry run)" if dry else "REMOVE"
                print(f"  {tag} {path}  (git hook; the spec gate is off)")
            else:
                print(f"  KEEP   {path}  (git hook dropped from the plan "
                      f"but locally modified; left in place)",
                      file=sys.stderr)
                summary["git_hooks"].append(
                    {"name": Path(path).name, "path": path,
                     "state": "kept-edited", "detail": ""})
        # [WP3 fix3 HD-1] The re-install retires dispatch and its own
        # shims, never a line the operator added to another hook or to a
        # hook manager's config: name each one that still mentions it.
        for fn, names in _gate_off_mentions(root).items():
            summary["git_hooks"].append(
                {"name": names[0], "names": names, "path": shown(fn),
                 "state": "gate-off-mention", "detail": ""})
        return

    hooks, rel, why = _git_hooks_target(root)
    if hooks is None:
        code, detail = why
        entry = {"name": None, "path": None, "state": code,
                 "detail": detail, "rel": rel}
        if code == "hooks-path":
            # [WP3 fix1 INST-3, INST-6] Which of the hooks there already
            # run the check, and whether the directory is shared by every
            # repository (the remedy differs). [WP3 fix2 IT-1, IT-2, RG-2]
            # "Runs the check" is this installer's shim, byte for byte and
            # executable; a mention of the line is said as a mention.
            where, shared = _hooks_path_where(root, detail)
            entry["shared"] = shared
            shim = TEMPLATES["git_hook_shim"](cfg)
            states = {}
            for n in GIT_HOOK_NAMES:
                user = _husky9_user_hook(where, n)
                if user is not None:
                    # husky runs the user's file with sh: no exec bit needed.
                    st = ("mentions" if _mentions_dispatch(read(user), n)
                          else "other")
                    states[n] = (st, shown(user), "husky9")
                else:
                    states[n] = (_hook_state(where / n, n, shim),
                                 shown(where / n), "")
            entry["missing"] = [n for n in GIT_HOOK_NAMES
                                if states[n][0] != "shim"]
            entry["states"] = {n: states[n] for n in entry["missing"]}
            if not entry["missing"]:
                print(f"  note   git hooks pre-commit, pre-merge-commit: "
                      f"the hooks in core.hooksPath ({detail}) are "
                      f"bootstrap-install's shim; nothing to install")
                manifest["files"].extend(prev_rows.values())
                return
        summary["git_hooks"].append(entry)
        if code in ("no-repo", "no-git-binary"):
            # Stdout only: with no repository there is no commit to check
            # yet, and a VCS-less project is a valid Phase 0 state
            # (PRD:474), so this is not a `warning:` on every re-install.
            why_txt = ("this directory is not inside a git repository"
                       if code == "no-repo" else "git is not on PATH")
            print(f"  note   git hooks pre-commit, pre-merge-commit not "
                  f"installed: {why_txt}. After `git init`, re-run "
                  f"bootstrap-install to add them.")
        else:
            print(f"  note   git hooks pre-commit, pre-merge-commit not "
                  f"installed ({code}; see the warning below)")
        # Keep the rows of shims an earlier run wrote, so --uninstall can
        # still find them.
        manifest["files"].extend(prev_rows.values())
        return

    body = TEMPLATES["git_hook_shim"](cfg)

    def place(name: str, target: Path, via: str = "") -> str | None:
        """Create, update, keep or skip one shim. Returns None when done,
        else the text of a hook this installer did not write ("" when it
        could not be read)."""
        path = shown(target)
        known = prev_rows.get(path)
        row = {"path": path, "digest": _digest(body), "mode": oct(0o755),
               "kind": "git_hook", "tier": TIER_NON}
        note = via
        if not target.exists():
            verdict = "create"
        else:
            text = read(target)
            if text == body:
                verdict = "unchanged"
            elif text is None or GIT_HOOK_MARKER not in text:
                return text or ""
            else:
                on_disk = _digest(text)
                if not _is_operator_content(known, on_disk):
                    verdict = "update"
                elif force:
                    saved = _save_forced_copy(
                        _backup_root(root, manifest), root,
                        path if not os.path.isabs(path)
                        else "git-hooks/" + target.name, text, dry=dry)
                    summary["backups"].append(saved)
                    note += f"  (forced; previous version saved to {saved})"
                    verdict = "update"
                elif adopt:
                    summary["adopted"] += 1
                    print(f"  ADOPT  {path}  (recorded as installer-owned; "
                          f"nothing written)")
                    row["digest"] = on_disk
                    manifest["files"].append(row)
                    return None
                else:
                    summary["skipped"] += 1
                    reason = _skip_reason(known is None,
                                          summary["no_manifest"])
                    print(f"  SKIP   {path}  ({reason}; use --force to "
                          f"overwrite)")
                    summary["git_hooks"].append(
                        {"name": name, "path": path, "state": "edited",
                         "detail": reason, "rel": rel})
                    row.update(digest=on_disk, state="skipped-local-edit")
                    manifest["files"].append(row)
                    return None
        # [WP3 critic 1h] A hooks directory that cannot be written (a
        # root-owned .git/hooks after a container `git init`, a read-only
        # mount) is reported per shim, like every other shim this run did
        # not install. It used to raise out of apply_plan before the
        # manifest was written, on every later run too.
        tmp = target.with_name(target.name + ".bootstrap-tmp")
        try:
            if not dry and verdict != "unchanged":
                hooks.mkdir(parents=True, exist_ok=True)
                tmp.write_text(body)
                tmp.chmod(0o755)
                os.replace(tmp, target)
            elif not dry and stat.S_IMODE(target.stat().st_mode) != 0o755:
                target.chmod(0o755)
        except OSError as exc:
            try:
                tmp.unlink()
            except OSError:
                pass
            print(f"  SKIP   {path}  (git hook: could not write it: "
                  f"{exc.strerror or exc})")
            summary["git_hooks"].append(
                {"name": name, "path": path, "state": "write-failed",
                 "detail": exc.strerror or str(exc), "rel": rel})
            # The shim an earlier run wrote is still there: keep its row,
            # so --uninstall can find it.
            if known is not None and target.exists():
                manifest["files"].append(known)
            return None
        summary[verdict] += 1
        tag = {"create": "CREATE", "update": "UPDATE",
               "unchanged": "  ok  "}[verdict]
        print(f"  {tag} {path}  (git hook: runs {GIT_HOOK_DISPATCH} for "
              f"agent commits){note}")
        manifest["files"].append(row)
        return None

    for name in GIT_HOOK_NAMES:
        target = hooks / name
        path = shown(target)
        if target.is_symlink():
            # [WP3 fix3 HD-5] A symlink to an exact, executable copy of the
            # shim runs the check (git follows it, and both fallbacks defer
            # to it): no "does not run from it".
            if read(target) == body and os.access(target, os.X_OK):
                print(f"  note   {path}  (a symlink to {os.readlink(target)}, "
                      f"which holds bootstrap-install's shim; left alone)")
                continue
            summary["git_hooks"].append(
                {"name": name, "path": path, "state": "foreign-symlink",
                 "detail": os.readlink(target), "rel": rel})
            print(f"  SKIP   {path}  (a symlink this installer did not "
                  f"write; left alone)")
            continue
        foreign = place(name, target)
        if foreign is None:
            continue
        manager = _hook_manager_of(foreign)
        # [WP3 fix1 INST-3] It may already run the check: from its own
        # text, or from its manager's config file at the repository top.
        # [WP3 fix2 IT-1, IT-2, RG-2] A mention, which the warning names
        # as one; and git skips a hook that is not executable.
        noexec = not os.access(target, os.X_OK)
        via = (path if _mentions_dispatch(foreign, name)
               else _manager_mentions_dispatch(root, manager, name))
        # The pre-commit framework keeps a hook it replaces as
        # <name>.legacy and still runs it (measured, pre-commit 4.6.2).
        # When that file is a shim this installer wrote, keep managing it
        # there: the check still runs, and --uninstall can remove it.
        legacy = hooks / (name + ".legacy")
        if (manager == "the pre-commit framework" and legacy.is_file()
                and not legacy.is_symlink()
                and GIT_HOOK_MARKER in (read(legacy) or "")):
            print(f"  note   {path}  (written by the pre-commit framework, "
                  f"which runs this installer's hook as {name}.legacy)")
            if place(name, legacy, via="  (run by the pre-commit "
                                       "framework)") is None:
                continue
        summary["git_hooks"].append(
            {"name": name, "path": path, "state": "foreign",
             "detail": manager, "rel": rel, "via": via or "",
             "noexec": noexec})
        print(f"  SKIP   {path}  (an existing hook this installer did not "
              f"write; left alone)")


def _mention_note(ment, cmd: str, prefix: str = "src/") -> str:
    """[WP3 fix2 IT-1, RG-2] What a hook that MENTIONS the dispatch line
    gets: not "nothing to install", which a line that never runs made
    false, and not the plain remedy the operator already followed.
    `prefix`: the first of hooks.spec_gate_commit_prefixes."""
    files = " and ".join(f"{p} mentions `{cmd} {n}`" for n, p in ment)
    out = (f" {files}, but this installer cannot tell whether git runs that "
           f"line (a line after an `exit` or an `exec`, after husky 9's "
           f"`. h`, or in a comment never runs), so it does not count as "
           f"the check.")
    # [WP3 fix3 HD-2] Confirm from a terminal: through Claude Code the
    # PreToolUse fallback refuses on the index first in block mode, so git
    # never runs the hook. And no ordinary commit fires pre-merge-commit
    # with anything to check: a commit fires pre-commit, and a clean merge
    # has no changes of its own. [WP3 fix4 INST3-3] The file must be under
    # a policed prefix: one outside them prints nothing, line or no line.
    if any(n == "pre-commit" for n, _p in ment):
        out += (f" To confirm the pre-commit line runs, commit a file under "
                f"{prefix} that no task file lists, such as "
                f"`{prefix}confirm.txt`, from a terminal with `CLAUDECODE=1 "
                f"git commit` (through Claude Code, the PreToolUse hook can "
                f"refuse the commit before git runs its hooks): it should "
                f"print `spec check (pre-commit):`. A file outside "
                f"hooks.spec_gate_commit_prefixes is not checked, so it "
                f"prints nothing. If that commit lands (in warn mode it "
                f"does), `git reset --soft HEAD~1` undoes it.")
    if any(n == "pre-merge-commit" for n, _p in ment):
        out += (" No ordinary commit confirms the pre-merge-commit line: git "
                "runs that hook only for a merge it commits by itself, which "
                "normally has no changes of its own for the check to judge.")
    return out


# [WP3 fix3 HD-1] Said once with a guarded line, so nobody drops the guard.
_GUARD_WHY = (" The `if [ -f ... ]` guard lets a commit through where there "
              "is no dispatch: on a branch from before the install, and once "
              "the spec gate is turned off.")


def _noexec_other(paths) -> str:
    """[WP3 fix3 HD-3] For hooks git skips that do not hold the line: the
    line goes in too, and the exec bit only if their own commands should run
    (a hook can be left non-executable on purpose)."""
    it = "it" if len(paths) == 1 else "them"
    return (" " + " and ".join(paths) + (" is" if len(paths) == 1 else " are")
            + f" not executable, so git skips {it}: put the line in {it} and "
            f"chmod +x {it} only if {'its' if it == 'it' else 'their'} own "
            f"commands should run too; otherwise replace {it} with an "
            f"executable hook that holds only the line.")


def _git_hook_warnings(summary: dict, root: Path, dry: bool,
                       prefixes=None) -> list[str]:
    """[WP3 / D2] One stderr line per git hook this run did not install,
    with the remedy. The exit status does not change (see above).
    `prefixes`: hooks.spec_gate_commit_prefixes (the default's when None)."""
    from templates import (GIT_HOOK_DISPATCH, GIT_HOOK_NAMES,
                           SPEC_GATE_DEFAULT_PREFIXES)
    pfx = (list(prefixes) if prefixes else
           list(SPEC_GATE_DEFAULT_PREFIXES))[0]
    did = "would not add" if dry else "did not add"
    still = ("The PreToolUse spec-gate-commit hook still runs, but it misses "
             "`git add X && git commit` and `git commit -am`.")
    out = []
    for g in summary["git_hooks"]:
        rel = g.get("rel") or "."
        cmd = GIT_HOOK_DISPATCH
        state, detail, path = g["state"], g["detail"], g["path"]
        if state in ("no-git-binary", "no-repo"):
            continue        # said on stdout by _apply_git_hooks
        elif state == "hooks-path":
            # [WP3 fix1 INST-3] Only the hooks that do not run it yet.
            # [WP3 fix2 IT-1, IT-2, RG-2] Per hook, by what is there: none
            # or another hook (the line to add), one git skips (chmod +x),
            # one that mentions the line (it may not run: confirm it), and
            # husky 9's wrapper directory (edit the hook husky runs).
            names = g.get("missing") or list(GIT_HOOK_NAMES)
            states = g.get("states") or {}
            add, noexec, noexec_add, ment, h9 = [], [], [], [], []
            for n in names:
                st, shown_p, kind = states.get(n, ("absent", "", ""))
                where_n = (os.path.dirname(shown_p) if shown_p
                           else detail)
                if st == "noexec":
                    noexec.append(shown_p)
                elif st == "mentions":
                    ment.append((n, shown_p))
                else:
                    # [WP3 fix3 HD-3] One git skips that lacks the line
                    # needs the line as well as the exec bit. [HD-2] The
                    # husky 9 sentence names only the hooks still to edit.
                    add.append((n, where_n))
                    if st == "noexec-other":
                        noexec_add.append(shown_p)
                    if kind == "husky9":
                        h9.append((n, shown_p))
            # [WP3 fix1 INST-6, fix3 HD-1] Every remedy's line is guarded,
            # so it lets a commit through where there is no dispatch.
            line = " and ".join(f"the {n} hook in {w} run `{_guarded_line(n)}`"
                                for n, w in add)
            if g.get("shared"):
                # [WP3 fix1 INST-6] A directory every repository on the
                # machine uses.
                msg = (f"core.hooksPath is set to {detail} in a git config "
                       f"every repository on this machine reads, so git does "
                       f"not run hooks from .git/hooks and this run {did} the "
                       f"spec check's git hooks. {still} The hooks there run "
                       f"for every repository, so a line that runs {cmd} "
                       f"unguarded refuses every commit in a repository that "
                       f"has none.")
            else:
                msg = (f"core.hooksPath is set to {detail}, so git does not "
                       f"run hooks from .git/hooks and this run {did} the "
                       f"spec check's git hooks. {still}")
            if add:
                msg += (f" To add the check, have {line}."
                        + ("" if g.get("shared") else _GUARD_WHY))
            if h9:
                msg += (f" {detail} is husky 9's directory, which husky "
                        f"rewrites, and its hooks there end in `exit` before "
                        f"a line added after them: put the line in "
                        + " and ".join(p for _n, p in h9)
                        + ", which husky runs.")
            if noexec:
                msg += (f" " + " and ".join(noexec) + (" is" if len(noexec) == 1
                        else " are") + " not executable, so git skips "
                        + ("it" if len(noexec) == 1 else "them")
                        + ": chmod +x " + " ".join(noexec) + ".")
            if noexec_add:
                msg += _noexec_other(noexec_add)
            if ment:
                msg += _mention_note(ment, cmd, pfx)
            out.append(msg)
        elif state == "not-top":
            # [WP3 fix1, operator decision 2026-10-06 (2)] Say what works
            # there: the check is project-relative (spec-check.sh and
            # gates.py), so the PreToolUse hook polices this project's own
            # paths against its own task files.
            msg = (f"{root} is the directory {rel}/ inside the git "
                   f"repository at {detail}, so this run {did} the spec "
                   f"check's git hooks: they would run for every commit "
                   f"in that repository. The spec check still checks "
                   f"this project's own paths against its own task "
                   f"files through the PreToolUse spec-gate-commit "
                   f"hook, but that misses `git add X && git commit` "
                   f"and `git commit -am`.")
            # [WP3 fix2 IT-5, MR-4] A nested install: the top's git hook
            # runs for this project's commits too, with the top's rules
            # (backlog). This project's fallback no longer defers to it.
            if os.path.isfile(os.path.join(detail, GIT_HOOK_DISPATCH)):
                msg += (f" The repository top has its own install: its git "
                        f"hook also runs for this project's commits and "
                        f"checks the paths under its own "
                        f"hooks.spec_gate_commit_prefixes against its own "
                        f"task files, so narrow those prefixes there to "
                        f"leave {rel}/ to this project.")
            out.append(msg)
        elif state == "hooks-off":
            # [WP3 fix3 HD-5] Not unset: an empty value turns hooks off.
            out.append(f"core.hooksPath is set to an empty value, which "
                       f"turns off every git hook in this repository, so "
                       f"this run {did} the spec check's git hooks: git "
                       f"would not run them. {still} To add them, unset "
                       f"core.hooksPath (`git config --show-origin --get "
                       f"core.hooksPath` names the file that sets it) and "
                       f"re-run bootstrap-install.")
        elif state == "hooks-dir-symlink":
            out.append(f"The repository's hooks directory is a symlink to "
                       f"{detail}, so this run {did} the spec check's git "
                       f"hooks: writing through it would reach every "
                       f"repository that shares it. {still}")
        elif state == "foreign-symlink":
            out.append(f"{path} is a symlink to {detail}, which this "
                       f"installer did not write, so it was left alone and "
                       f"the spec check does not run from it. {still} To add "
                       f"the check, have that hook run "
                       f"`{_guarded_line(g['name'])}`.{_GUARD_WHY}")
        elif state == "foreign" and (g.get("via") or g.get("noexec")):
            # [WP3 fix2 IT-1, IT-2, RG-2] It mentions the line (in its own
            # text or its manager's config), or git skips it: say which,
            # not the plain remedy (INST-3), and never "it runs".
            who = f", written by {detail}" if detail else ""
            msg = (f"{path} already exists{who}, and this installer did not "
                   f"write it, so it was left alone. {still}")
            if g.get("via"):
                if g.get("noexec"):
                    msg += (f" It is not executable, so git skips it: "
                            f"chmod +x {path}.")
                msg += _mention_note([(g["name"], g["via"])], cmd, pfx)
            else:
                # [WP3 fix3 HD-1, HD-3] The guarded line, and the exec bit
                # only if the hook's own commands should run.
                msg += (f" To add the check, have that hook run "
                        f"`{_guarded_line(g['name'])}`.{_GUARD_WHY}"
                        + _noexec_other([path]))
            out.append(msg)
        elif state == "foreign":
            who = f", written by {detail}" if detail else ""
            hint = ""
            # [WP3 fix3 HD-1] Guarded entries too: the framework runs
            # `entry` without a shell, so its guard goes through sh -c.
            if detail == "the pre-commit framework":
                hint = (f" With the pre-commit framework, add a `repo: local` "
                        f"hook with `entry: sh -c '[ ! -f {cmd} ] || exec "
                        f"bash {cmd} {g['name']}'`, "
                        f"`language: system`, `pass_filenames: false`, "
                        f"`always_run: true` and `stages: [{g['name']}]`.")
            elif detail == "lefthook":
                hint = (f" With lefthook, add a `{g['name']}` command that "
                        f"runs `{_guarded_line(g['name'])}` to lefthook.yml.")
            out.append(f"{path} already exists{who}, and this installer did "
                       f"not write it, so it was left alone and the spec "
                       f"check does not run from it. {still} To add the "
                       f"check, have that hook run "
                       f"`{_guarded_line(g['name'])}`.{_GUARD_WHY}{hint}")
        elif state == "edited":
            kept = "keeps your local edits" if dry else "kept your local edits"
            out.append(f"{path} {kept}, so this run "
                       f"{'would not update' if dry else 'did not update'} "
                       f"it. Pass --force to overwrite (it saves the current "
                       f"file to .claude/.installer-backups/ first).")
        elif state == "write-failed":
            out.append(f"{path} could not be written ({detail}), so the "
                       f"spec check does not run from it. {still} Make the "
                       f"repository's hooks directory writable and re-run "
                       f"bootstrap-install.")
        elif state == "kept-edited":
            out.append(f"{path} is a git hook an earlier install wrote and "
                       f"you have edited, so this run left it in place "
                       f"although the spec gate is now off. Delete it if it "
                       f"should not run.")
        elif state == "gate-off-mention":
            # [WP3 fix3 HD-1] A line the operator added stays when the gate
            # goes off; unguarded, it refuses every commit once dispatch is
            # gone, and the off switch is what the block-mode text prescribes.
            names = g.get("names") or [g["name"]]
            lines = " and ".join(f"`{cmd} {n}`" for n in names)
            one = len(names) == 1
            what = f"{'that line' if one else 'those lines'} from {path}"
            # [WP3 fix4 INST3-2] In a hook manager's config the mention is
            # one key of an entry; the entry left without it breaks the
            # tool, which then refuses every commit too.
            base = Path(path).name
            if base in _MANAGER_CONFIGS["the pre-commit framework"]:
                what = (f"the whole hook {'entry' if one else 'entries'} that "
                        f"{'runs' if one else 'run'} it from {path} (each "
                        f"`- id:` item with that `entry:`, not only the line)")
            elif base in _MANAGER_CONFIGS["lefthook"]:
                what = (f"the whole lefthook "
                        f"{'command' if one else 'commands'} that "
                        f"{'runs' if one else 'run'} it from {path} (each "
                        f"command's name with its `run:` key, not only the "
                        f"line)")
            out.append(f"{path} still mentions {lines}, but the spec gate is "
                       f"off (hooks.spec_gate_commit: false): remove {what}. "
                       f"Once {cmd} is gone, a line that runs it "
                       f"without first checking that it exists refuses every "
                       f"commit, a person's too.")
    return out


def _below_top(root: Path):
    """(top, rel) when the project directory is below its repository's top
    level (a monorepo package): rel is its path from there, without the
    trailing "/". None at the top, outside a repository, or with no git."""
    loc = _git_out(root, "rev-parse", "--show-toplevel", "--show-prefix")
    if loc is None or loc[0] != 0:
        return None
    lines = loc[1].split("\n") + ["", ""]
    top, rel = lines[0], lines[1].rstrip("/")
    return (top, rel) if top and rel else None


# [WP3 fix1 MB-1, operator decision 2026-10-06 (2)] Measured on Claude Code
# 2.1.291 (wp3-fix1 f2-merge-back, live/runs/mono*.jsonl): for a project
# below the repository top, an agent with `isolation: worktree` gets its
# worktree at the TOP's .claude/worktrees/, starts at that worktree's top,
# and a `cd` does not persist between its Bash calls. Its PreToolUse gates
# run there, so the test gate ran `sh tests/run.sh` from the worktree's top
# and refused the commit (exit 127, test command not found). Making every
# cwd-bound gate find the project inside a worktree, on both substrates, is
# more than this round can carry, so that part falls back as the decision
# allows: `auto` resolves to none there (an explicit `worktree` is kept,
# with a warning), and merge-back, which works there, still lands a branch
# made by hand.
_BELOW_TOP_WT = ("Claude Code makes an implementer's worktree at "
                 "{top}/.claude/worktrees/ and starts it at that worktree's "
                 "top, where the gates run the test command from the wrong "
                 "directory: its `git commit` was refused, test command not "
                 "found (measured on Claude Code 2.1.291)")


def _below_top_isolation(root: Path, cfg: dict) -> None:
    """Resolve `workflow.implementer_isolation: auto` to none for a project
    below the repository top (see _BELOW_TOP_WT). Runs before build_plan,
    so every isolation-dependent file follows; an explicit value stands."""
    where = _below_top(root)
    if (where is not None and cfg.get("_implementer_isolation") == "worktree"
            and cfg.get("workflow", {}).get("implementer_isolation",
                                            "auto") == "auto"):
        cfg["_implementer_isolation"] = "none"
        cfg["_isolation_below_top"] = where[1]


def _below_top_notes(root: Path, cfg: dict) -> list[str]:
    """[WP3 fix1 MB-1, operator decision 2026-10-06 (2)] What works for a
    project below the repository top: merge-back runs its git steps at the
    top and the gates in the project; worktree isolation does not (see
    _BELOW_TOP_WT). One stderr line; rc unchanged."""
    where = _below_top(root)
    if where is None:
        return []
    top, rel = where
    lands = (f".claude/merge-back.sh works here: it runs its git steps (the "
             f"dirty check, the merge, the commit) at the repository top, "
             f"across the whole repository, and the gates in {rel}/.")
    head = (f"{root} is the directory {rel}/ inside the git repository at "
            f"{top}. " + _BELOW_TOP_WT.format(top=top))
    if cfg.get("_isolation_below_top"):
        return [head + ". So workflow.implementer_isolation `auto` resolved "
                "to none here: the implementer commits on the current "
                "branch, one task at a time, and there is nothing to merge "
                "back. " + lands + " It still lands a worktree branch made "
                "by hand."]
    if not _worktrees_on(cfg):
        return []
    msg = (head + ". workflow.implementer_isolation is set to worktree, so "
           "its commits will be refused there unless commands.test also "
           "works from the repository top; `auto` would resolve to none. "
           + lands)
    ign = _git_out(Path(top), "check-ignore", "-q", "--no-index",
                   ".claude/worktrees/agent-x/")
    if ign is None or ign[0] != 0:
        msg += (f" Add `/.claude/worktrees/` to {top}/.gitignore (or to "
                f".git/info/exclude): this project's .claude/.gitignore "
                f"does not cover them, so `git add -A` in the repository "
                f"would stage each worktree as an embedded repository.")
    return [msg]


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


# [WP1] The test script `npm init` writes (measured, npm 11.6.2).
_NPM_PLACEHOLDER_TEST = 'echo "Error: no test specified" && exit 1'


def _test_command_notes(root: Path, test_cmd: str) -> list[str]:
    """[WP1] Say at install time when the test gate will block a new
    project's commits for a reason the gate cannot see.

    The gate lets pytest's and unittest's exit 5 ("no tests collected")
    through, because that code means nothing else. jest and vitest exit 1
    when they find no tests, and npm's placeholder script exits 1 always -
    the code a red suite exits with - so the gate cannot tell them apart and
    blocks. Advisory only: the install and the gate are unchanged.
    """
    try:
        argv = shlex.split(test_cmd)
    except ValueError:
        return []
    while argv and re.match(r"[A-Za-z_][A-Za-z0-9_]*=", argv[0]):
        argv = argv[1:]
    if argv[:1] == ["npx"]:
        argv = argv[1:]
    notes = []
    prog = os.path.basename(argv[0]) if argv else ""
    if prog in ("jest", "vitest") and not any(
            a in ("--passWithNoTests", "--passWithNoTests=true")
            for a in argv):
        notes.append(
            f"commands.test runs {prog}, which exits 1 when it finds no "
            f"tests - the code a failing suite exits with - so the test gate "
            f"blocks every commit until the first test exists. Add "
            f"--passWithNoTests if an empty suite should pass.")
    if argv[:2] in (["npm", "test"], ["npm", "t"]) \
            or argv[:3] == ["npm", "run", "test"]:
        try:
            scripts = json.loads(
                (root / "package.json").read_text()).get("scripts")
        except (OSError, ValueError, AttributeError):
            scripts = None
        if isinstance(scripts, dict) \
                and scripts.get("test") == _NPM_PLACEHOLDER_TEST:
            notes.append(
                "package.json's test script is npm's placeholder, which "
                "always exits 1, so the test gate blocks every commit, the "
                "first one included, until it is replaced. `node --test` "
                "exits 0 on an empty suite.")
    return notes


def _runtime_floor_check() -> None:
    """AC-9-4: log the detected Claude Code CLI version; warn LOUDLY when
    it is below the seam binds floor (RUNTIME_FLOOR) or undetectable.
    Never fatal - the floor binds dispatch behavior (no unattended stall on
    a gate-hook timeout), not emission - but never silent either.
    [Corrected 2026-08-13, X-51: this said "fail-closed PreToolUse timeouts".
    No runtime provides that - a cancelled hook exits 124/137/143 and only
    exit 2 blocks, so a crossed timeout is a SKIPPED gate, not a refusal.]"""
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
              f"runtime floor >= {RUNTIME_FLOOR} cannot be confirmed. "
              f"Unattended dispatch below the floor can stall on a "
              f"gate-hook timeout. Note: no runtime makes a hook timeout "
              f"fail closed - a cancelled hook does not block.",
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


def _warn(msg: str) -> None:
    """[WP1] The one print site, and the one prefix, for the installer's
    advisory lines: an install that proceeds, and exits as it would have,
    but did or would do something the operator should hear about.
    plugin/commands/bootstrap-apply.md tells the AI to surface every
    `warning:` line verbatim, so a line printed any other way is one the
    operator may never be shown. Errors keep `error:`/`ERROR:`, and lines
    that predate WP1 keep their own prefixes."""
    print(f"warning: {msg}", file=sys.stderr)


def _index_schema_warning(root: Path, summary: dict,
                          dry: bool = False) -> str | None:
    """[WP3 versioning-index] INDEX.md is the operator's roster, so the
    hand-edit guard skips it and a re-install never delivers a new schema.
    That is correct, but the SKIP line alone does not say what was missed.
    When it was skipped and its roster header lacks columns the current
    schema has, return one message naming them and pointing at the
    migration recipe, or giving it when the README on disk lacks it;
    otherwise None. Reads the on-disk files only; writes nothing. Columns
    compare case-insensitively, with surrounding spaces ignored."""
    rel = ".claude/specs/INDEX.md"
    if rel not in summary.get("skipped_paths", ()):
        return None
    try:
        text = (root / rel).read_text(errors="replace")
    except OSError:
        return None
    header = None
    for line in text.splitlines():
        cells = [c.strip().lower() for c in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and cells and cells[0] == "slug":
            header = set(cells)
            break
    if header is None:
        what = "it has no roster table whose header starts with 'slug'"
    else:
        missing = [c for c in INDEX_COLUMNS if c not in header]
        if not missing:
            return None
        what = ("its table lacks the column(s) "
                + ", ".join(f"'{c}'" for c in missing))
    did = "would not update" if dry else "did not update"
    head = (f"{rel} keeps your rows, so this run {did} it, and {what}. "
            f"The spec skills fill only the columns your table has.")
    # [WP3 versioning-index, critic 3e] The recipe is in the installer's
    # README. When the README on disk is the adopter's own (skipped as
    # pre-existing or edited) and lacks it, the pointer led nowhere (the
    # conformance verifier's scenario h), so give the recipe here instead.
    # On --dry-run a missing README is one this run would create.
    readme = root / ".claude/specs/README.md"
    try:
        has_recipe = "## Migrating an older INDEX.md" in readme.read_text(
            errors="replace")
    except OSError:
        has_recipe = dry and not readme.exists()
    if has_recipe:
        return (f"{head} To add the current columns without losing a row, "
                f"follow \"Migrating an older INDEX.md\" in "
                f".claude/specs/README.md.")
    if header is None:
        fix = ("Start the roster table with this header row: "
               "| " + " | ".join(INDEX_COLUMNS) + " |.")
    else:
        fix = ("To add them without losing a row, append them to the "
               "header row in the order named here, then one '---' cell "
               "per added column to the separator row and one '-' cell "
               "per added column to every data row.")
    return (f"{head} .claude/specs/README.md is not the installer's, so it "
            f"has no migration recipe. {fix} To receive the installer's "
            f"README, which says what each column holds and how to refresh "
            f"them, move yours aside and re-install.")


def _worktrees_ignore_warning(root: Path, summary: dict,
                              dry: bool = False) -> str | None:
    """[WP3 fix1 INST-1] .claude/.gitignore is installer-owned, so an edited
    copy (or one in a fresh clone, with no manifest) is skipped, and the
    `/worktrees/` line WP3 added never reaches it. One SKIP line on stdout
    was all the run said. When the file was skipped and git does not ignore
    .claude/worktrees/ by any other rule (the root .gitignore,
    .git/info/exclude, a global excludes file), return one message naming
    the line and what its absence costs; otherwise None. Outside a
    repository there is nothing to stage, so None."""
    rel = ".claude/.gitignore"
    if rel not in summary.get("skipped_paths", ()):
        return None
    r = _git_out(root, "check-ignore", "-q", "--no-index",
                 ".claude/worktrees/agent-x/")
    if r is None or r[0] != 1:
        return None
    did = "would not receive" if dry else "did not receive"
    return (f"{rel} was left as it is (see its SKIP line), so it {did} the "
            f"line `/worktrees/`, and no other ignore rule covers "
            f".claude/worktrees/. While an implementer's worktree is there, "
            f"`git add -A` or `git add .claude/` stages it as an embedded "
            f"repository (a 160000 gitlink). Add the line `/worktrees/` to "
            f"{rel}.")


def _empty_command_warnings(cfg: dict) -> list[str]:
    """[I-10] One message per empty command in cfg["_command_warnings"].
    What it says depends on whether the hook that runs the command is in
    the resolved set, so a message never names a hook the config turned
    off."""
    hooks = cfg.get("_resolved_hooks", ())
    msgs = []
    for name in cfg.get("_command_warnings", ()):
        if name == "test" and "test-gate" in hooks \
                and cfg.get("mode") != "retrofit":
            why = "test-gate blocks every commit until it is set"
        elif name == "test":
            # ci-mirror still runs Test with test-gate off, and a retrofit
            # rollout has warn-only weeks, so say only that it is empty.
            why = None
        elif name == "lint" and "format-lint-gate" in hooks:
            why = "format-lint-gate checks nothing until it is set"
        elif name == "format":
            why = "no hook runs it; tech.md shows it as TODO"
        elif name == "eval":
            why = ("eval-gate falls back to .claude/.last-eval-pass, which "
                   "any Bash `touch` satisfies")
        else:
            why = "the hook that runs it is off"
        msgs.append(f"commands.{name} is empty"
                    + (f": {why}" if why else "")
                    + ". Set it in bootstrap.config.yaml and re-install.")
    return msgs



def next_steps(root: Path, cfg: dict, paths=None) -> list[str]:
    """[WP3 agents-handoff, item 10] The Phase 10 handoff's "next three
    things" (PRD:2158-2161; RETROFIT.md R7 step 8), printed after an install
    while the project has no task file yet, and empty once it has one, so a
    re-install of a project already doing spec work prints nothing new.

    The PRD names `/spec-new <first-feature>` as the next step; after D2
    that alone does not clear the spec commit gate (a requirements.md is not
    in its corpus; measured rc=2 at 3d866f4). The step that does is the task
    file /spec-decompose writes. So the lines name the whole entry chain,
    and say why code waits for the task file only where the gate is
    installed.

    [WP3 critic 4b] The lines run to a merged commit: commit the spec before
    dispatch (an implementer's worktree starts from the last commit, and the
    spec check reads task files from git), and land an approved worktree
    branch with .claude/merge-back.sh (D6). The first line names every
    path the plan writes outside .claude/ (CLAUDE.md, and the root
    .gitignore block when a wrapper is emitted), not .claude/ alone.
    `paths` is the plan's paths; None builds the plan from `cfg`."""
    specs = root / ".claude" / "specs"
    try:
        if any(specs.glob("*/tasks/*")):
            return []
    except OSError:
        pass
    if paths is None:
        paths = [a["path"] for a in build_plan(cfg)]
    # A file at the root by name, anything deeper by its top directory.
    top = sorted({p.split("/", 1)[0] + ("/" if "/" in p else "")
                  for p in paths if not p.startswith(".claude/")})
    lines = [
        "Commit what the install wrote: "
        + ", ".join([".claude/"] + top)
        + " (and docs/prd/, if you wrote a PRD).",
        f"Start real work with {SPEC_START_CHAIN}.",
    ]
    task = (f"/spec-decompose writes {SPEC_TASK_FILE} with a Files: list.")
    gate = "spec-gate-commit" in cfg.get("_resolved_hooks", ())
    if gate:
        task += (" The spec commit gate checks the files you commit against "
                 "those lists.")
        if cfg.get("mode") == "retrofit":
            # [WP3 critic 4b] Not "until their first change": the gates
            # exempt a listed path until its line is deleted from the list
            # (retrofit_is_allowlisted; spec-strategy.md "To REMOVE a
            # path"). A first change alone ends nothing.
            task += (" A file the legacy allowlist covers is exempt until "
                     "its line is deleted from that list "
                     "(.claude/steering/spec-strategy.md says when).")
    lines.append(task)
    # Each reason only where it holds: no spec check, no first reason; no
    # worktree, no second.
    why = ", and ".join(
        (["the spec check reads task files from git"] if gate else [])
        + (["the implementer's worktree starts from the last commit"]
           if _worktrees_on(cfg) else []))
    lines.append("To start a task, set status: in-progress in its task "
                 "file, then commit .claude/specs/<slug>/ and "
                 ".claude/specs/INDEX.md before you hand it to the "
                 "implementer agent" + (f": {why}." if why else "."))
    if _worktrees_on(cfg):
        lines.append("Pass the implementer's branch to the reviewer agent. "
                     "Once it answers VERDICT: approve, land the branch "
                     "with .claude/merge-back.sh <branch>; never merge it "
                     "by hand.")
    else:
        lines.append("Pass the commit the implementer started from to the "
                     "reviewer agent. The implementer commits on the "
                     "current branch, so there is nothing to merge back.")
    return lines


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

    # A config that cannot be read or parsed is the operator's to fix, so it
    # gets rc=2 - never a traceback. YAMLError is a ValueError; so is
    # UnicodeDecodeError.
    try:
        cfg_text = cfg_path.read_text()
        raw = load_yaml(cfg_text)
    except YAMLError as exc:
        where = f"{cfg_path}:{exc.line}" if exc.line else str(cfg_path)
        print(f"error: {where}: {exc.msg}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"error: cannot read config {cfg_path}: {exc}", file=sys.stderr)
        return 2
    # [WP1 D3] A policy switch that is not true or false is the operator's to
    # fix, and it decides whether a security gate exists, so it is refused
    # here with file:line, ahead of resolve_config's own (line-less) refusal.
    switch_errors = policy_switch_errors(raw)
    for (sect, key), msg in switch_errors:
        line = key_line(cfg_text, (sect, key))
        where = f"{cfg_path}:{line}" if line else str(cfg_path)
        print(f"error: {where}: {msg}", file=sys.stderr)
    if switch_errors:
        return 2
    cfg, errors = resolve_config(raw)
    if errors:
        print("Config validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2
    # [WP3 fix1 MB-1] Below the repository top, `auto` isolation resolves
    # to none (_below_top_isolation); the warning comes with the git-hook
    # ones below.
    _below_top_isolation(root, cfg)

    # [round-4 D18] Spellings that were normalized rather than refused. These
    # are NOT errors - the install proceeds - but they must be visible: the
    # previous behavior was to emit a secrets-gate that guarded nothing, with
    # rc=0 and no output, which is the worst of the available options.
    for note in cfg.get("_config_notices", ()):
        print(f"note: {note}", file=sys.stderr)
    # [I-10] resolve_config computed these and nothing printed them, so an
    # install with empty commands said nothing. Printed before --print-config
    # and --dry-run return, so both show them.
    # The test-command notes say the test gate blocks every commit, which
    # holds only where _empty_command_warnings says the same of an empty
    # test: test-gate installed, and not a retrofit (warn-only weeks).
    gate_blocks = ("test-gate" in cfg.get("_resolved_hooks", ())
                   and cfg.get("mode") != "retrofit")
    for msg in (_empty_command_warnings(cfg)
                + list(cfg.get("_retrofit_warnings", ()))
                + (_test_command_notes(root,
                                       cfg["commands"].get("test") or "")
                   if gate_blocks else [])):
        _warn(msg)

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

    # Not an error, and the exit status does not change: the new file is
    # the install the config asks for. But the operator switched hooks off
    # on purpose, and a CREATE line on stdout is all this used to say.
    if summary["hooks_reenabled"]:
        verb = "would create" if args.dry_run else "created"
        _warn(f"{summary['hooks_reenabled']} exists: hooks were disabled by "
              f"renaming .claude/settings.json. This run {verb} a new "
              f".claude/settings.json, which turns every hook back on. To "
              f"keep them all off, delete the new file after each install. "
              f"To turn off only some, set their `hooks:` keys to false in "
              f"the config and re-install.")

    # [WP1 / D4 (a)] One line per hook script this run left alone. rc stays
    # 0, but a config change the script embeds did not reach it, and its
    # SKIP line on stdout is one among ~60. Worded by why it was left alone,
    # as _skip_reason words the SKIP line: on a tree with no manifest (every
    # fresh clone, since the manifest is gitignored) the file is as likely an
    # earlier install's as the operator's, and --adopt is the remedy for that.
    would = "would not update" if args.dry_run else "did not update"
    force = ("pass --force to overwrite (it saves the current file to "
             ".claude/.installer-backups/ first)")
    idx_msg = _index_schema_warning(root, summary, dry=args.dry_run)
    if idx_msg:
        _warn(idx_msg)
    wt_msg = _worktrees_ignore_warning(root, summary, dry=args.dry_run)
    if wt_msg:
        _warn(wt_msg)
    for skipped in summary["skipped_hooks"]:
        path = skipped["path"]
        if path in _CONFIG_BEARING_SCRIPTS:
            embeds = (f"a config change it embeds "
                      f"({_CONFIG_BEARING_SCRIPTS[path]}) does NOT reach it.")
        else:
            embeds = ("a config change it embeds (a command, a path list) "
                      "does NOT reach it.")
        if skipped["untracked"] and summary["no_manifest"]:
            _warn(f"{path}: this tree has no installer manifest, so this run "
                  f"{would} it and cannot tell whether it is your work or an "
                  f"earlier install's: {embeds} If it is an earlier "
                  f"install's file, run with --adopt, which records it as "
                  f"the installer's and writes nothing, then re-install. If "
                  f"it is your work, merge the change by hand, or {force}.")
        elif skipped["untracked"]:
            _warn(f"{path} was not written by this installer, so this run "
                  f"{would} it: {embeds} Merge the change by hand, or "
                  f"{force}.")
        else:
            kept = ("keeps your local edits" if args.dry_run else
                    "kept your local edits")
            _warn(f"{path} {kept}, so this run {would} it: {embeds} Merge "
                  f"the change by hand, or {force}.")

    # [WP1 fix 4] A security gate an earlier install wired, which this plan
    # drops. rc stays 0: D3 makes the policy switch the master switch. But a
    # config written before WP1 can carry a `false` that did not turn the
    # gate off then (24cd8a3's retrofit heuristic proposed one for every
    # repository whose dependencies its scanner could not read, and its
    # greenfield one for PRD text its stdlib-only pattern matched), and a gate
    # that ran must not stop running on a stdout REMOVE line alone.
    for d in summary["dropped_security"]:
        name = Path(d["path"]).name.removesuffix(".sh")
        policy = "deps" if name == "dependency-gate" else "secrets"
        key = name.replace("-", "_")
        if not cfg[policy]["enabled"]:
            why = f"{policy}.enabled is false"
        elif not cfg["hooks"].get(key, True):
            why = f"hooks.{key} is {json.dumps(cfg['hooks'].get(key))}"
        else:
            why = "this config does not install it"
        if d["removed"]:
            did = "would remove" if args.dry_run else "removed"
            _warn(f"{d['path']}: {why}, so this run {did} the {name} an "
                  f"earlier install wrote.")
        else:
            _warn(f"{d['path']}: {why}, so this run no longer installs or "
                  f"registers the {name}. The file stays on disk: this run "
                  f"could not confirm it is a copy an earlier install wrote.")
    def _site_is(event, matcher, cmd):
        # [WP2 IU-2/IU-3] A retired site is not this installer's site for
        # the hook; it is where an earlier installer registered it.
        rel = _resolved_hook_path(cmd)
        hk = Path(rel).name.removesuffix(".sh") if rel else None
        if (event, matcher) in HOOK_RETIRED_SITES.get(hk, []):
            return ("a site where an earlier installer registered that hook, "
                    "which this config does not install")
        return "the installer's site for a hook this config does not install"

    for event, matcher, cmd in summary["dropped_registrations"]:
        where = f"{event} ({matcher})" if matcher else event
        did = "would drop" if args.dry_run else "dropped"
        _warn(f".claude/settings.json registered {cmd} under {where}, "
              f"{_site_is(event, matcher, cmd)}; this run {did} that "
              f"registration.")
    # [WP2 IU-3] The registration is gone but the script is not: the stale-
    # file cleanup removes only a copy the manifest records unedited, so on
    # a tree with no manifest (every fresh clone) the script stays on disk
    # unwired by us. Say so once per script. A security gate's own
    # line above already says its file stays.
    security = {d["path"] for d in summary["dropped_security"]}
    planned = {a["path"] for a in plan}
    left = []
    for _, _, cmd in summary["dropped_registrations"]:
        rel = _resolved_hook_path(cmd)
        if rel is None or rel in left or rel in security \
                or rel in planned or rel in summary["removed_paths"] \
                or not (root / rel).exists():
            continue
        left.append(rel)
    for rel in left:
        why = ("this tree has no installer manifest, so this run could not "
               "confirm it is a copy an earlier install wrote" if
               summary["no_manifest"] else
               "it is not the unedited copy the manifest records")
        _warn(f"{rel} stays on disk although this run "
              f"{'would drop' if args.dry_run else 'dropped'} its "
              f"registration: {why}. Delete it if that hook should not run.")
    for event, matcher, cmd in summary["kept_off_registrations"]:
        where = f"{event} ({matcher})" if matcher else event
        did = "would keep" if args.dry_run else "kept"
        _warn(f".claude/settings.json registers {cmd} under {where}, "
              f"{_site_is(event, matcher, cmd)}. Its "
              f"script is neither the copy this config would install nor one "
              f"the manifest records, so this run {did} the registration. "
              f"Remove it if that hook should not run.")

    # [WP3 / D2] Git hooks this run did not install. rc stays 0.
    for msg in _git_hook_warnings(
            summary, root, args.dry_run,
            cfg["hooks"].get("spec_gate_commit_prefixes")):
        _warn(msg)
    # [WP3 fix1 MB-1] A project below the repository top: where the
    # worktrees go, and what merge-back does there. rc stays 0.
    for msg in _below_top_notes(root, cfg):
        _warn(msg)
    # [WP3 / D6] An operator's worktree.baseRef that is "fresh" or null.
    # rc stays 0 (any other value was declined: exit 3 below). [WP3 / model
    # assignment] Also an ultracode opt-out a kept value overrides.
    for msg in summary["settings_notes"]:
        _warn(msg)

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

    for msg in unstartable_hooks(root):
        _warn(msg)

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

    # [WP3 critic 4b] The Phase 10 handoff, last, and only on an install
    # that is one: after the enforcement checks above, so an exit-3 run is
    # never told to commit .claude/ and start work, and never under
    # --adopt, which writes nothing (--dry-run returned above).
    steps = ([] if args.adopt else
             next_steps(root, cfg, [a["path"] for a in plan]))
    if steps:
        print("\nNext steps:")
        for n, line in enumerate(steps, 1):
            print(f"  {n}. {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

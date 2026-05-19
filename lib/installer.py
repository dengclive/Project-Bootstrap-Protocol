#!/usr/bin/env python3
"""
Deterministic Bootstrap Protocol installer.

Reads a bootstrap.config.yaml (the frozen output of the BOOTSTRAP.md wizard's
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
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

from minyaml import load_yaml          # local stdlib-only YAML subset
from templates import TEMPLATES        # all file bodies live here
from defaults import resolve_config    # archetype defaults + validation

MANIFEST = ".claude/.installer-manifest.json"
STATE = ".claude/.bootstrap-state.json"
PROTOCOL_VERSION = "1.9.0"
INSTALLER_VERSION = "1.0.0"


# --------------------------------------------------------------------------- #
# Plan construction
# --------------------------------------------------------------------------- #
def build_plan(cfg: dict) -> list[dict]:
    """Return an ordered list of file actions derived purely from cfg.

    Each action: {path, body, mode, kind}. No I/O happens here - the plan is
    a pure function of the config, which is what makes the installer
    deterministic and unit-testable.
    """
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

    # ---- Hooks (Phase 6) -------------------------------------------------- #
    hook_set = cfg["_resolved_hooks"]            # filled by resolve_config
    for hook_name in hook_set:
        body = TEMPLATES["hook"](hook_name, cfg)
        if body is None:
            continue
        add(f".claude/hooks/{hook_name}.sh", body, mode=0o755, kind="hook")

    add(".claude/hooks/audio-alerts.config", TEMPLATES["audio_config"](cfg))
    add(".claude/settings.json", TEMPLATES["settings_json"](cfg), kind="settings")

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
    # BOOTSTRAP.md Phase 9.5 "What the wizard generates when loop mode is
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

    # ---- gitignore fragment ----------------------------------------------- #
    add(".claude/.gitignore", TEMPLATES["gitignore"](cfg))

    # ---- Retrofit overlay (single mode-gated branch, per C1) ------------- #
    # Net AST change in build_plan: this conditional + the helper call.
    # Greenfield cfgs never reach this branch; D2 golden test confirms
    # greenfield output is byte-identical post-edit.
    if cfg.get("mode") == "retrofit":
        plan = _apply_retrofit_overlay(plan, cfg)

    return plan


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

    # Rebuild the plan in a deterministic order: original greenfield
    # entries first (in their existing order, with replacements in place),
    # then new retrofit entries (sorted by path for determinism). This
    # preserves apply_plan's per-file ordering for greenfield-shared
    # paths and gives retrofit-only paths a stable position.
    out = []
    seen: set = set()
    for a in plan:
        out.append(by_path[a["path"]])
        seen.add(a["path"])
    for path in sorted(by_path):
        if path not in seen:
            out.append(by_path[path])
    return out


# --------------------------------------------------------------------------- #
# Apply / diff
# --------------------------------------------------------------------------- #
def _digest(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def _classify(root: Path, action: dict) -> str:
    target = root / action["path"]
    if not target.exists():
        return "create"
    if target.read_text() == action["body"]:
        return "unchanged"
    return "update"


def apply_plan(root: Path, plan: list[dict], cfg: dict, *,
               dry: bool, force: bool) -> dict:
    manifest = {
        "installer_version": INSTALLER_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }
    summary = {"create": 0, "update": 0, "unchanged": 0, "skipped": 0}

    prev = _load_manifest(root)
    prev_files = {f["path"]: f for f in prev.get("files", [])} if prev else {}

    for action in plan:
        verdict = _classify(root, action)
        target = root / action["path"]

        # Don't clobber a file the operator hand-edited unless --force, but DO
        # overwrite files we generated last time (tracked in the manifest).
        if verdict == "update" and not force:
            known = prev_files.get(action["path"])
            on_disk = _digest(target.read_text())
            if known and known.get("digest") != on_disk:
                summary["skipped"] += 1
                print(f"  SKIP   {action['path']}  (locally modified; "
                      f"use --force to overwrite)")
                manifest["files"].append(
                    {"path": action["path"], "digest": on_disk,
                     "state": "skipped-local-edit"})
                continue

        summary[verdict] += 1
        tag = {"create": "CREATE", "update": "UPDATE",
               "unchanged": "  ok  "}[verdict]
        print(f"  {tag} {action['path']}")

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

        manifest["files"].append({
            "path": action["path"],
            "digest": _digest(action["body"]),
            "mode": oct(action["mode"]),
            "kind": action["kind"],
        })

    if not dry:
        _write_state(root, cfg, manifest)
        (root / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")

    return summary


def _write_state(root: Path, cfg: dict, manifest: dict) -> None:
    """Write .claude/.bootstrap-state.json honouring the BOOTSTRAP.md
    Phase 0 / Recovery-and-State schema (archetype, PRD path, CI/CD opt-out,
    the three autonomous-mode flags, the three tracking lists). Preserves any
    pre-existing keys (e.g. completed_phases written by a live wizard)."""
    proj = cfg.get("project", {})
    flags = cfg.get("autonomous_modes", {})
    state_path = root / STATE
    state: dict = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except Exception:
            state = {}
    state.update({
        "bootstrap_protocol_version": PROTOCOL_VERSION,
        "installed_by": f"bootstrap-installer {INSTALLER_VERSION}",
        "installed_at": manifest["generated_at"],
        "deterministic_install": True,
        # --- BOOTSTRAP.md Phase 0 required classification fields ---
        "archetype": proj.get("archetype"),
        "prd_path": proj.get("prd_path"),
        "prd_tier": proj.get("prd_tier"),
        "cicd_opt_out": bool(proj.get("cicd_opt_out", False)),
        # --- the three autonomous-mode opt-in flags (lines 107, 224) ---
        "loop_mode_enabled": bool(flags.get("loop_mode_enabled", False)),
        "goal_supervised_mode_enabled":
            bool(flags.get("goal_supervised_mode_enabled", False)),
        "queue_mode_enabled": bool(flags.get("queue_mode_enabled", False)),
    })
    # --- the three tracking lists: initialise once, never clobber ---
    state.setdefault("loop_in_flight", [])
    state.setdefault("goal_in_flight", [])
    state.setdefault("queue_runs_history", [])
    state.setdefault("deferred_items", {})
    state.setdefault("skippable_phase_decisions", {})
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
    ap.add_argument("--uninstall", action="store_true",
                    help="Remove everything the installer created.")
    ap.add_argument("--print-config", action="store_true",
                    help="Print the fully-resolved config and exit.")
    args = ap.parse_args(argv)

    root = Path(args.dir).resolve()

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

    if args.print_config:
        print(json.dumps(cfg, indent=2, default=str))
        return 0

    plan = build_plan(cfg)
    print(f"Bootstrap installer {INSTALLER_VERSION} "
          f"(protocol {PROTOCOL_VERSION})")
    print(f"Archetype: {cfg['project']['archetype']}  |  "
          f"loop={cfg['autonomous_modes']['loop_mode_enabled']} "
          f"goal={cfg['autonomous_modes']['goal_supervised_mode_enabled']} "
          f"queue={cfg['autonomous_modes']['queue_mode_enabled']}")
    print(f"Target: {root}")
    print(f"{'DRY RUN - ' if args.dry_run else ''}{len(plan)} files planned\n")

    summary = apply_plan(root, plan, cfg, dry=args.dry_run,
                          force=args.force)
    print(f"\nDone. create={summary['create']} update={summary['update']} "
          f"unchanged={summary['unchanged']} skipped={summary['skipped']}")
    if args.dry_run:
        print("(dry run - no files written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""
Retrofit decision-layer interview tool: codebase -> proposed
bootstrap.config.yaml (mode: retrofit).

Three subcommands, mirroring lib/interview.py's analyze/synthesize/
interactive front-ends, plus a `scan` subcommand that writes the R0
inventory artifacts (per OD-5: codebase-derived files live with the
decision layer).

  scan         repo -> .claude/inventory/*.md (R0)
  analyze      [scan first if not present] -> bootstrap.interview.md
                  (proposal + rationale + OPEN QUESTIONs + ANSWERS block)
  synthesize   bootstrap.interview.md -> bootstrap.config.yaml (mode: retrofit;
                  validated)
  interactive  repo -> live stdin Q&A -> bootstrap.config.yaml

Invariants (identical contract to greenfield):
  * Proposes, never silently decides. Ambiguity becomes OPEN QUESTION.
  * commands.test/lint/format proposed with confidence (OD-3); empty
    answers honor the loud-TODO gate contract.
  * The emitted cfg validates via `bootstrap-install --print-config`.
  * The proposal core (build_retrofit_proposal) is a pure function of
    InventoryData; identical inventory => identical proposal => identical
    interview file. The interactive front-end is non-deterministic by
    design (like the greenfield wizard).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import retrofit_heuristics as RH
import prd_heuristics as PH  # for ARCHETYPE_REQUIRED_TIER, TIER_ORDER, CONF_*
from configemit import emit
from defaults import (
    resolve_config, ARCHETYPES, RETROFIT_SPEC_STRATEGIES,
    RETROFIT_PM_STRATEGIES,
)
from inventory_scan import scan_repo, write_inventory
from minyaml import load_yaml

HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "bin" / "bootstrap-install"

INTERVIEW_DEFAULT = "bootstrap.interview.md"
CONFIG_DEFAULT = "bootstrap.config.yaml"
INVENTORY_DEFAULT = ".claude/inventory"

# Keys whose answers the human supplies in the ANSWERS block. Order matches
# the interview-file rendering order (and interactive prompt order).
ANSWER_KEYS = [
    "project_name",
    "archetype",
    "prd_tier_target",
    "principles_ranked",
    "tdd_policy",
    "secrets_enabled",
    "deps_enabled",
    "spec_strategy",
    "legacy_allowlist",
    "pm_strategy",
    "pm_tool",
    "pm_tool_role_after",
    "ci_cd_applicability",
    "loop_mode_opted_in",
    "goal_supervised_mode_opted_in",
    "queue_mode_opted_in",
    "commands_test",
    "commands_lint",
    "commands_format",
    "commands_typecheck",
    "commands_ci_local",
]

_LIST_KEYS = {"principles_ranked", "legacy_allowlist"}
_BOOL_KEYS = {
    "secrets_enabled", "deps_enabled",
    "loop_mode_opted_in", "goal_supervised_mode_opted_in",
    "queue_mode_opted_in",
}


# --------------------------------------------------------------------------- #
# Inventory loading
# --------------------------------------------------------------------------- #
def load_or_scan_inventory(repo_root: Path, *,
                            force_rescan: bool = False) -> dict:
    """Scan the repo and return the InventoryData dict. The inventory
    markdown files are a side-effect snapshot for operators (R0 mandates
    they're written); the cfg-emit side reads the structured dict."""
    return scan_repo(repo_root)


# --------------------------------------------------------------------------- #
# Default answers from proposal
# --------------------------------------------------------------------------- #
def default_answers(proposal: dict) -> dict:
    """The answer set if the human edits nothing."""
    p = proposal
    cmds = p["commands"]["proposals"]
    return {
        "project_name": p["project_name"]["value"],
        "archetype": p["archetype"]["value"],
        "prd_tier_target": p["prd_tier"]["value"],
        "principles_ranked": list(p["principles"]["ranked"]),
        "tdd_policy": p["principles"]["tdd_policy"]["value"],
        "secrets_enabled": p["secrets"]["enabled"],
        "deps_enabled": p["deps"]["enabled"],
        "spec_strategy": p["spec_strategy"]["value"],
        "legacy_allowlist": list(p["legacy_allowlist"]),
        "pm_strategy": p["pm"]["strategy"],
        "pm_tool": p["pm"]["tool"],
        "pm_tool_role_after": p["pm"]["tool_role_after"],
        "ci_cd_applicability": p["ci_cd_applicability"]["value"],
        "loop_mode_opted_in": p["autonomous_modes"]["loop_mode_opted_in"],
        "goal_supervised_mode_opted_in":
            p["autonomous_modes"]["goal_supervised_mode_opted_in"],
        "queue_mode_opted_in":
            p["autonomous_modes"]["queue_mode_opted_in"],
        # Commands: prefilled with the proposal if any, else empty (OD-3:
        # empty values are HUMAN-REQUIRED — fail-loud TODO gate applies).
        "commands_test": cmds.get("test", {}).get("value", ""),
        "commands_lint": cmds.get("lint", {}).get("value", ""),
        "commands_format": cmds.get("format", {}).get("value", ""),
        "commands_typecheck": "",  # never auto-proposed
        "commands_ci_local": "",   # never auto-proposed
    }


# --------------------------------------------------------------------------- #
# answers -> cfg dict
# --------------------------------------------------------------------------- #
def answers_to_config(ans: dict, proposal: dict) -> dict:
    """Assemble a mode: retrofit cfg dict. Per the schema delta in §2 of
    the design note, retrofit-specific state lives under cfg["retrofit"];
    greenfield-shared state lives at the same top-level keys it always has
    (project, autonomous_modes, principles, secrets, deps, commands, etc.)."""
    return {
        "mode": "retrofit",
        "project": {
            "name": ans["project_name"],
            "archetype": ans["archetype"],
            "shell": "bash",
            "prd_tier": ans["prd_tier_target"],
            "prd_path": "docs/prd/PRD.md",
            "cicd_opt_out": ans["ci_cd_applicability"] == "no",
        },
        # B5: *_enabled flags MUST be false at retrofit time. The opt-in
        # intent lives in cfg["retrofit"]["autonomous_modes"]["*_opted_in"];
        # resolve_config's retrofit branch enforces this on hand-edited
        # configs too.
        "autonomous_modes": {
            "loop_mode_enabled": False,
            "goal_supervised_mode_enabled": False,
            "queue_mode_enabled": False,
        },
        "principles": {
            "ranked": list(ans["principles_ranked"]),
            "tiebreakers": [],
            "tdd_policy": ans["tdd_policy"],
        },
        "secrets": {
            "enabled": bool(ans["secrets_enabled"]),
            "never_read_paths": [
                ".env*", "secrets/**", "*.pem", "*.key",
            ],
            "rotation_policy": (
                "Rotate any exposed credential immediately; never echo "
                "to output."),
        },
        "deps": {
            "enabled": bool(ans["deps_enabled"]),
            "approved": _initial_approved_list(proposal),
        },
        "commands": {
            "test": ans["commands_test"],
            "lint": ans["commands_lint"],
            "format": ans["commands_format"],
            "typecheck": ans["commands_typecheck"],
            "ci_local": ans["commands_ci_local"],
        },
        "retrofit": {
            "state_path": ".claude/inventory",
            "archetype_confidence":
                proposal["archetype"]["confidence"]
                if proposal["archetype"]["confidence"] in (
                    "high", "medium", "low") else "low",
            "archetype_evidence":
                list(proposal["archetype"].get("evidence", [])),
            "synthetic_profile": {},
            "prd_tier_target": ans["prd_tier_target"],
            "ci_cd_applicability": ans["ci_cd_applicability"],
            "spec_strategy": ans["spec_strategy"],
            "legacy_allowlist": list(ans["legacy_allowlist"]),
            "retrofit_active": True,
            "spec_patterns": _derive_spec_patterns(
                ans["archetype"], ans["spec_strategy"]),
            "pm": {
                "strategy": ans["pm_strategy"],
                "tool": ans["pm_tool"],
                "tool_role_after": ans["pm_tool_role_after"],
                "ticket_migration": {
                    "convert_now": [], "defer": [], "close": [],
                },
                "hybrid_review_date": None,
            },
            "regulatory_regimes": [],
            "codebase_size_gb": 0,
            "autonomous_modes": {
                "loop_mode_opted_in": bool(ans["loop_mode_opted_in"]),
                "goal_supervised_mode_opted_in":
                    bool(ans["goal_supervised_mode_opted_in"]),
                "queue_mode_opted_in": bool(ans["queue_mode_opted_in"]),
                "brownfield_milestones": {
                    "rollout_steady_state_spec_test_gate": False,
                    "rollout_steady_state_all_hooks": False,
                    "touch_based_specs_under_blocking_gates": 0,
                    "touch_based_specs_threshold": 10,
                    "legacy_allowlist_size_at_retrofit":
                        len(ans["legacy_allowlist"]),
                    "legacy_allowlist_current_size":
                        len(ans["legacy_allowlist"]),
                    "legacy_allowlist_shrink_threshold_pct": 25,
                    "mode_selection_ledger_entries": 0,
                    "weeks_real_per_task_operation_post_blocking": 0,
                },
            },
            "debt": {
                "entries": list(proposal["debt"]),
            },
            "inventory_summary": {
                "has_prior_claude":
                    proposal["_inventory_summary"]["has_prior_claude"],
                "has_root_claude_md":
                    proposal["_inventory_summary"]["has_root_claude_md"],
                "danger_zone_count": 0,
                "no_test_module_count":
                    proposal["_inventory_summary"]["no_test_module_count"],
            },
        },
    }


def _initial_approved_list(proposal: dict) -> list[str]:
    """For deps enabled, the initial approved list is the union of every
    declared dep across manifests (R5.5 step 1: 'use inventory as initial
    approved list'). Empty if deps disabled."""
    # We don't have inv reachable here; the proposal's debt fields are
    # already aggregated. For brevity and determinism we leave this empty;
    # operator populates from inventory/dependencies.md before R5.5.
    return []


def _derive_spec_patterns(archetype: str, spec_strategy: str) -> dict:
    """Per RETROFIT.md R4 step 3: change specs always; boundary specs for
    Service/API, Library/SDK, Full-stack, Platform; migration specs only
    if operator declares in-flight modernization (defaults False — operator
    upgrades in the ANSWERS block / interactive prompt)."""
    return {
        "change": True,
        "boundary": archetype in (
            "service", "library", "fullstack", "platform"),
        "migration": False,
    }


# --------------------------------------------------------------------------- #
# Validation (resolve_config + retrofit-only floor checks)
# --------------------------------------------------------------------------- #
def validate_config_dict(cfg: dict) -> list[str]:
    """Same shape as the greenfield interview's validate_config_dict:
    delegate to the shared resolve_config (which understands mode:
    retrofit since the D3 defaults.py extension), then layer the retrofit-
    only decision-layer floors that the installer cannot police mechanically
    (PRD tier floor per archetype, same as greenfield's F-3 fix)."""
    _, errors = resolve_config(cfg)
    errors = list(errors)
    proj = cfg.get("project", {}) if isinstance(cfg, dict) else {}
    arche = proj.get("archetype")
    tier = proj.get("prd_tier")
    if arche in PH.ARCHETYPE_REQUIRED_TIER and tier in PH.TIER_ORDER:
        floor = PH.ARCHETYPE_REQUIRED_TIER[arche]
        if PH.TIER_ORDER[tier] < PH.TIER_ORDER[floor]:
            errors.append(
                f"project.prd_tier '{tier}' is below the required floor "
                f"'{floor}' for archetype '{arche}' (RETROFIT.md R0.5 "
                f"step 6: a higher tier may be requested, never a lower "
                f"one). Raise prd_tier (and retrofit.prd_tier_target) to "
                f"at least '{floor}'.")
    return errors


def validate_with_installer(config_path: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(BIN), "-c", str(config_path),
         "-C", str(config_path.parent), "--print-config"],
        capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr)


# --------------------------------------------------------------------------- #
# Interview-file rendering (pass 1) and parsing (pass 2)
# --------------------------------------------------------------------------- #
_CONF_BADGE = {
    PH.CONF_HIGH: "HIGH",
    PH.CONF_MEDIUM: "MEDIUM",
    PH.CONF_LOW: "LOW",
    PH.CONF_OPEN: "OPEN — needs your decision",
}

ANSWERS_BEGIN = (
    "# ===== ANSWERS (edit values to the right of the colon) =====")
ANSWERS_END = "# ===== END ANSWERS ====="


def render_interview(proposal: dict, repo_root: Path) -> str:
    p = proposal
    ans = default_answers(p)
    L: list[str] = []
    w = L.append

    w("# Retrofit Interview — Proposal for Human Review")
    w("")
    w(f"Source codebase: `{repo_root}`")
    w("")
    w("This file is a **proposal**. Nothing has been written to "
      "`.claude/` (other than")
    w("the `.claude/inventory/*.md` audit files; per RETROFIT.md R0, "
      "those are produced")
    w("by the `scan` subcommand before this interview runs).")
    w("")
    w("Read each decision and its rationale. To accept a proposal, "
      "leave its line in")
    w("the ANSWERS block unchanged. To override, edit the value after "
      "the colon. Then run:")
    w("")
    w("    bin/retrofit-interview synthesize")
    w("")
    w("which emits `bootstrap.config.yaml` (with `mode: retrofit`) "
      "and validates it")
    w("with `bootstrap-install --print-config` before finishing.")
    w("")
    w("---")
    w("")
    inv = p["_inventory_summary"]
    w("## Inventory summary")
    w("")
    w(f"- **Source files:** {inv['source_file_count']}")
    w(f"- **Test files:** {inv['test_file_count']}")
    w(f"- **Modules without name-matching test:** "
      f"{inv['no_test_module_count']}")
    w(f"- **Total commits:** {inv['total_commits']}")
    w(f"- **Git mode:** "
      f"{'DEGRADED' if inv['degraded_git'] else 'full'}")
    w(f"- **Existing `.claude/`:** {inv['has_prior_claude']}")
    w(f"- **Root `CLAUDE.md` exists:** {inv['has_root_claude_md']}")
    w("")
    w("---")
    w("")

    def section(title, body_lines):
        w(f"## {title}")
        w("")
        for bl in body_lines:
            w(bl)
        w("")

    section("Project name", [
        f"**Proposed:** `{p['project_name']['value']}`  "
        f"_(confidence: {_CONF_BADGE[p['project_name']['confidence']]})_",
        "",
        p["project_name"]["rationale"],
    ])
    section("Archetype", [
        f"**Proposed:** `{p['archetype']['value']}`  "
        f"_(confidence: {_CONF_BADGE[p['archetype']['confidence']]})_",
        "",
        p["archetype"]["rationale"],
        "",
        ("_Code evidence cited:_ " +
         ", ".join(p["archetype"]["evidence"])
         if p["archetype"].get("evidence") else ""),
        ("_Alternatives considered:_ "
         + ", ".join(p["archetype"]["alternatives"])
         if p["archetype"].get("alternatives") else ""),
    ])
    section(f"PRD tier target (floor for this archetype: "
            f"`{p['prd_tier']['floor']}`)", [
        f"**Proposed:** `{p['prd_tier']['value']}`  "
        f"_(confidence: {_CONF_BADGE[p['prd_tier']['confidence']]})_",
        "",
        p["prd_tier"]["rationale"],
        "",
        "_You may raise the tier but not lower it below the floor "
        "(RETROFIT.md R0.5 step 6)._",
    ])

    pr = p["principles"]
    pl = [
        f"**Starter set ('{p['archetype']['value']}', from "
        f"lib/defaults.PRINCIPLE_STARTERS):**",
    ]
    for i, s in enumerate(pr["starter_set"], 1):
        pl.append(f"  {i}. {s}")
    pl += ["", pr["rationale"]]
    section("Principles", pl)

    section("TDD policy", [
        f"**Proposed:** `{pr['tdd_policy']['value']}`  "
        f"_(confidence: {_CONF_BADGE[pr['tdd_policy']['confidence']]})_",
        "",
        pr["tdd_policy"]["rationale"],
    ])
    section("Spec strategy", [
        f"**Proposed:** `{p['spec_strategy']['value']}`  "
        f"_(confidence: {_CONF_BADGE[p['spec_strategy']['confidence']]})_",
        "",
        p["spec_strategy"]["rationale"],
        "",
        f"_Options: {', '.join(sorted(RETROFIT_SPEC_STRATEGIES))}._",
    ])
    legacy_lines = ["**Proposed legacy allowlist:**"]
    for path in p["legacy_allowlist"]:
        legacy_lines.append(f"  - `{path}`")
    if not p["legacy_allowlist"]:
        legacy_lines.append("  _(empty)_")
    legacy_lines += [
        "",
        "Operator may ADD paths (broader exemption); removing a default "
        "path subjects it to spec gating immediately — usually undesirable "
        "in forward-only retrofit.",
    ]
    section("Legacy allowlist", legacy_lines)

    section("PM strategy (R0.7)", [
        f"**Proposed:** strategy `{p['pm']['strategy']}`, tool "
        f"`{p['pm']['tool']}`, role-after `{p['pm']['tool_role_after']}`  "
        f"_(confidence: {_CONF_BADGE[p['pm']['confidence']]})_",
        "",
        p["pm"]["rationale"],
        "",
        f"_Options: {', '.join(sorted(RETROFIT_PM_STRATEGIES))}._",
    ])
    section("CI/CD applicability", [
        f"**Proposed:** `{p['ci_cd_applicability']['value']}`  "
        f"_(confidence: "
        f"{_CONF_BADGE[p['ci_cd_applicability']['confidence']]})_",
        "",
        p["ci_cd_applicability"]["rationale"],
    ])
    am = p["autonomous_modes"]
    section("Autonomous-mode opt-in (scaffold-but-defer)", [
        "**Proposed:** all OFF  "
        f"_(confidence: {_CONF_BADGE[am['confidence']]})_",
        "",
        am["rationale"],
        "",
        "_Constraint: queue mode requires loop or goal mode (RETROFIT.md "
        "§\"Autonomous Modes in Retrofit\"). The wizard never **enables** "
        "a mode at retrofit time regardless._",
    ])

    cmd_p = p["commands"]
    cmd_lines = [
        f"**Proposed (per OD-3):** confidence "
        f"{_CONF_BADGE[cmd_p['confidence']]}",
        "",
        cmd_p["rationale"],
        "",
    ]
    if cmd_p["proposals"]:
        cmd_lines.append("Detected:")
        for cmd, info in cmd_p["proposals"].items():
            cmd_lines.append(
                f"  - **{cmd}**: `{info['value']}`  "
                f"_(confidence: {_CONF_BADGE[info['confidence']]}; "
                f"source: {info['source']})_")
        cmd_lines.append("")
    cmd_lines += [
        "Per OD-3 the HUMAN-REQUIRED fail-loud TODO-gate contract is "
        "preserved: any value you clear in the ANSWERS block becomes a "
        "loud-TODO gate at installer time.",
    ]
    section("Project commands", cmd_lines)

    if p["debt"]:
        section(f"Initial debt registry ({len(p['debt'])} entries)", [
            (f"- **{d['what']}** — severity {d['severity']}; "
             f"plan: {d['plan']}")
            for d in p["debt"]
        ])

    if p["open_questions"]:
        w("## ⚠ OPEN QUESTIONS — these were too ambiguous to propose")
        w("")
        w("The tool deliberately did **not** decide these. Resolve each "
          "by setting the corresponding ANSWERS line.")
        w("")
        for oq in p["open_questions"]:
            w(f"- **{oq['id']}** — {oq['prompt']}")
            if oq.get("options"):
                w(f"  Options: {', '.join(map(str, oq['options']))}")
            w(f"  Default if you do nothing: `{oq['default']}`")
        w("")

    w("---")
    w("")
    w(ANSWERS_BEGIN)
    w("# Booleans: true/false. Leave commands empty unless known.")
    w("# List values (principles_ranked, legacy_allowlist) use one item "
      "per `  - ` line")
    w("# so an item may safely contain commas.")
    for k in ANSWER_KEYS:
        v = ans[k]
        if isinstance(v, list):
            w(f"{k}:")
            for item in v:
                w(f"  - {item}")
        elif isinstance(v, bool):
            w(f"{k}: {str(v).lower()}")
        else:
            w(f"{k}: {v}")
    w(ANSWERS_END)
    w("")
    return "\n".join(L)


def parse_interview_answers(text: str) -> dict:
    lines = text.splitlines()
    try:
        i0 = lines.index(ANSWERS_BEGIN)
        i1 = lines.index(ANSWERS_END)
    except ValueError:
        raise ValueError(
            "interview file is missing the ANSWERS block; regenerate "
            "with `bin/retrofit-interview analyze`")

    raw: dict[str, str] = {}
    list_raw: dict[str, list[str]] = {}
    body = lines[i0 + 1:i1]
    cur_list_key: str | None = None
    for line in body:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") or stripped == "-":
            if cur_list_key is not None:
                item = stripped[1:].strip()
                if item:
                    list_raw.setdefault(cur_list_key, []).append(item)
            continue
        if ":" not in stripped:
            continue
        k, _, v = stripped.partition(":")
        k = k.strip()
        v = v.strip()
        if k in _LIST_KEYS and v == "":
            cur_list_key = k
            list_raw.setdefault(k, [])
        else:
            cur_list_key = None
            raw[k] = v

    out: dict = {}
    for k in ANSWER_KEYS:
        if k in _LIST_KEYS:
            if k in list_raw:
                out[k] = [x.strip() for x in list_raw[k] if x.strip()]
                continue
            if k in raw:
                out[k] = [x.strip() for x in raw[k].split(",")
                          if x.strip()]
                continue
            raise ValueError(f"ANSWERS block missing key: {k}")
        if k not in raw:
            raise ValueError(f"ANSWERS block missing key: {k}")
        val = raw[k]
        if k in _BOOL_KEYS:
            out[k] = val.strip().lower() in ("true", "1", "yes", "on")
        else:
            out[k] = val
    return out


# --------------------------------------------------------------------------- #
# Interactive front-end (mirror of greenfield's run_interactive)
# --------------------------------------------------------------------------- #
class _EOF:
    """Sticky end-of-input flag shared across prompts."""

    def __init__(self) -> None:
        self.hit = False


def _ask(prompt: str, default: str, *, instream, outstream,
         eof: "_EOF | None" = None) -> str:
    outstream.write(prompt + f"\n  [default: {default}] > ")
    outstream.flush()
    line = instream.readline()
    if line == "":
        if eof is not None:
            eof.hit = True
        return default
    line = line.strip()
    return line if line else default


def run_interactive(repo_root: Path, *, instream, outstream) -> dict:
    """Live stdin Q&A over the retrofit proposal core. Same 'show before
    writing' discipline as the greenfield interactive front-end."""
    outstream.write("\n=== Retrofit interview (interactive) ===\n")
    outstream.write("Scanning codebase ...\n")
    outstream.flush()
    inv = scan_repo(repo_root)
    write_inventory(repo_root, inv)
    outstream.write(f"  wrote {INVENTORY_DEFAULT}/*.md\n")
    p = RH.build_retrofit_proposal(
        inv, project_fallback=repo_root.name or "my-project")
    ans = default_answers(p)
    eof = _EOF()
    o = outstream.write

    o("\nEach decision below is a PROPOSAL with a rationale. Press Enter "
      "to accept,\nor type an override. Nothing is written until you "
      "confirm at the end.\n")

    def show(title, rationale):
        o(f"\n--- {title} ---\n{rationale}\n")

    show("Project name", p["project_name"]["rationale"])
    ans["project_name"] = _ask(
        "Project name", ans["project_name"],
        instream=instream, outstream=outstream, eof=eof)

    show(f"Archetype (confidence {p['archetype']['confidence']})",
         p["archetype"]["rationale"])
    while True:
        v = _ask(f"Archetype {sorted(ARCHETYPES)}", ans["archetype"],
                 instream=instream, outstream=outstream, eof=eof)
        if v in ARCHETYPES:
            ans["archetype"] = v
            break
        if eof.hit:
            ans["archetype"] = (ans["archetype"]
                                if ans["archetype"] in ARCHETYPES
                                else "other")
            o(f"  (end of input; accepting '{ans['archetype']}')\n")
            break
        o(f"  '{v}' is not a valid archetype; try again.\n")

    floor = PH.ARCHETYPE_REQUIRED_TIER.get(ans["archetype"], "standard")
    show(f"PRD tier target (floor '{floor}')", p["prd_tier"]["rationale"])
    while True:
        v = _ask("PRD tier micro|standard|full", ans["prd_tier_target"],
                 instream=instream, outstream=outstream, eof=eof)
        if v in PH.TIER_ORDER and PH.TIER_ORDER[v] >= PH.TIER_ORDER[floor]:
            ans["prd_tier_target"] = v
            break
        if eof.hit:
            cur = PH.TIER_ORDER.get(
                v if v in PH.TIER_ORDER else ans["prd_tier_target"], -1)
            chosen = v if cur >= PH.TIER_ORDER[floor] else floor
            ans["prd_tier_target"] = chosen
            o(f"  (end of input; clamping tier to floor "
              f"'{ans['prd_tier_target']}')\n")
            break
        o(f"  must be one of micro|standard|full and >= floor '{floor}'.\n")

    show("Principles", p["principles"]["rationale"])
    o("  Proposed ranked set:\n")
    for i, s in enumerate(ans["principles_ranked"], 1):
        o(f"    {i}. {s}\n")
    v = _ask("Principles (semicolon-separated, in rank order)",
             "; ".join(ans["principles_ranked"]),
             instream=instream, outstream=outstream, eof=eof)
    ans["principles_ranked"] = [x.strip() for x in v.split(";")
                                 if x.strip()]

    show("TDD policy", p["principles"]["tdd_policy"]["rationale"])
    while True:
        v = _ask("TDD policy off|encouraged|required", ans["tdd_policy"],
                 instream=instream, outstream=outstream, eof=eof)
        if v in ("off", "encouraged", "required"):
            ans["tdd_policy"] = v
            break
        if eof.hit:
            ans["tdd_policy"] = (ans["tdd_policy"]
                                 if ans["tdd_policy"] in
                                 ("off", "encouraged", "required")
                                 else "encouraged")
            o(f"  (end of input; accepting '{ans['tdd_policy']}')\n")
            break
        o("  must be off|encouraged|required.\n")

    show("Spec strategy", p["spec_strategy"]["rationale"])
    while True:
        v = _ask(f"Spec strategy {sorted(RETROFIT_SPEC_STRATEGIES)}",
                 ans["spec_strategy"],
                 instream=instream, outstream=outstream, eof=eof)
        if v in RETROFIT_SPEC_STRATEGIES:
            ans["spec_strategy"] = v
            break
        if eof.hit:
            ans["spec_strategy"] = "forward-only"
            o("  (end of input; accepting 'forward-only')\n")
            break
        o(f"  must be one of {sorted(RETROFIT_SPEC_STRATEGIES)}.\n")

    show("PM strategy (R0.7)", p["pm"]["rationale"])
    while True:
        v = _ask(f"PM strategy {sorted(RETROFIT_PM_STRATEGIES)}",
                 ans["pm_strategy"],
                 instream=instream, outstream=outstream, eof=eof)
        if v in RETROFIT_PM_STRATEGIES:
            ans["pm_strategy"] = v
            break
        if eof.hit:
            ans["pm_strategy"] = "spec_canonical"
            o("  (end of input; accepting 'spec_canonical')\n")
            break
        o(f"  must be one of {sorted(RETROFIT_PM_STRATEGIES)}.\n")

    show("CI/CD applicability", p["ci_cd_applicability"]["rationale"])
    while True:
        v = _ask("CI/CD applicability yes|no|unknown",
                 ans["ci_cd_applicability"],
                 instream=instream, outstream=outstream, eof=eof)
        if v in ("yes", "no", "unknown"):
            ans["ci_cd_applicability"] = v
            break
        if eof.hit:
            ans["ci_cd_applicability"] = (
                ans["ci_cd_applicability"]
                if ans["ci_cd_applicability"] in ("yes", "no", "unknown")
                else "unknown")
            o(f"  (end of input; accepting "
              f"'{ans['ci_cd_applicability']}')\n")
            break
        o("  must be yes|no|unknown.\n")

    show("Autonomous-mode opt-in (scaffold-but-defer)",
         p["autonomous_modes"]["rationale"])
    for mk, label in (("loop_mode_opted_in", "Loop mode (scaffold-only)"),
                      ("goal_supervised_mode_opted_in",
                       "Goal-supervised mode (scaffold-only)"),
                      ("queue_mode_opted_in",
                       "Queue mode (scaffold-only; requires loop or goal)")):
        v = _ask(f"{label} opt-in? true|false",
                 str(ans[mk]).lower(),
                 instream=instream, outstream=outstream, eof=eof)
        ans[mk] = v.lower() in ("true", "1", "yes", "on")
    if ans["queue_mode_opted_in"] and not (
            ans["loop_mode_opted_in"]
            or ans["goal_supervised_mode_opted_in"]):
        o("\n  ! Queue mode requires loop or goal mode. Disabling queue "
          "opt-in.\n")
        ans["queue_mode_opted_in"] = False

    o("\n--- Project commands ---\n"
      "Per OD-3 retrofit proposes commands with confidence; empty values "
      "trigger\nthe installer's fail-loud TODO-gate (intentional).\n")
    for ck, label in (("commands_test", "test"),
                      ("commands_lint", "lint"),
                      ("commands_format", "format"),
                      ("commands_typecheck", "typecheck"),
                      ("commands_ci_local", "ci_local")):
        ans[ck] = _ask(f"commands.{label}", ans[ck],
                        instream=instream, outstream=outstream, eof=eof)

    return ans, p


# --------------------------------------------------------------------------- #
# Orchestration helpers
# --------------------------------------------------------------------------- #
def _finalize(answers: dict, proposal: dict, out_path: Path, *,
              outstream) -> int:
    cfg = answers_to_config(answers, proposal)
    errs = validate_config_dict(cfg)
    if errs:
        outstream.write("\nConfig did NOT validate (resolve_config + "
                         "retrofit floor checks):\n")
        for e in errs:
            outstream.write(f"  - {e}\n")
        outstream.write("No file written. Resolve the above and re-run.\n")
        return 2

    header = ("GENERATED BY bin/retrofit-interview — a PROPOSAL reviewed "
              "by a human.\nEvery value here was shown with a rationale "
              "before acceptance.\nempty commands.* are intentional per "
              "OD-3: the installer emits loud-TODO gates.\nRe-run "
              "bin/bootstrap-install --dry-run to preview the .claude/ "
              "tree.")
    emit_warnings: list[str] = []
    out_path.write_text(emit(cfg, header=header, warnings=emit_warnings))
    for w_ in emit_warnings:
        outstream.write(f"\n  ! sanitized {w_}\n")

    rc, output = validate_with_installer(out_path)
    if rc != 0:
        outstream.write(
            "\nWrote config but `bootstrap-install --print-config` "
            f"REJECTED it:\n{output}\n"
            "This is a tool bug - the emitted draft must always validate. "
            "File left for inspection.\n")
        return 2
    outstream.write(
        f"\nWrote {out_path} and validated it with "
        f"`bootstrap-install --print-config` (OK).\n"
        "Review it, then run `bin/bootstrap-install --dry-run` to preview "
        "the harness.\n")
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="retrofit-interview",
        description=(
            "Decision-layer for the retrofit installer: read an existing "
            "codebase and PROPOSE a bootstrap.config.yaml (mode: "
            "retrofit) for human approval. Never decides silently; "
            "proposes project commands with confidence (OD-3); honors "
            "RETROFIT.md scaffold-but-defer for autonomous modes."))
    sub = ap.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scan",
                         help="codebase -> .claude/inventory/*.md (R0)")
    sc.add_argument("-C", "--dir", default=".",
                    help="Project root (default: cwd)")

    an = sub.add_parser("analyze",
                         help="[scan first] -> bootstrap.interview.md")
    an.add_argument("-C", "--dir", default=".")
    an.add_argument("-o", "--out", default=INTERVIEW_DEFAULT)

    sy = sub.add_parser("synthesize",
                         help="bootstrap.interview.md -> "
                              "bootstrap.config.yaml")
    sy.add_argument("-C", "--dir", default=".")
    sy.add_argument("-i", "--interview", default=INTERVIEW_DEFAULT)
    sy.add_argument("-o", "--out", default=CONFIG_DEFAULT)

    it = sub.add_parser("interactive",
                         help="codebase -> live stdin Q&A -> "
                              "bootstrap.config.yaml")
    it.add_argument("-C", "--dir", default=".")
    it.add_argument("-o", "--out", default=CONFIG_DEFAULT)

    args = ap.parse_args(argv)
    root = Path(args.dir).resolve()

    if args.cmd == "scan":
        inv = scan_repo(root)
        written = write_inventory(root, inv)
        print(f"Wrote {len(written)} inventory file(s) under "
              f"{INVENTORY_DEFAULT}/:")
        for p in sorted(written):
            print(f"  {p}")
        return 0

    if args.cmd == "analyze":
        inv = scan_repo(root)
        write_inventory(root, inv)
        proposal = RH.build_retrofit_proposal(
            inv, project_fallback=root.name or "my-project")
        out_p = root / args.out
        # Stash the proposal in a sibling JSON so synthesize can rebuild
        # answers_to_config inputs (we don't want to round-trip the whole
        # proposal through the interview markdown).
        stash = root / (args.out + ".proposal.json")
        stash.write_text(json.dumps(proposal, default=str, indent=2))
        out_p.write_text(render_interview(proposal, root))
        n_oq = len(proposal["open_questions"])
        print(f"Wrote {args.out} (proposal stashed at {stash.name}; "
              f"{n_oq} open question(s) need your decision).")
        print(f"Wrote {len(_inventory_paths())} inventory file(s) under "
              f"{INVENTORY_DEFAULT}/.")
        print("Edit the ANSWERS block, then run: "
              "bin/retrofit-interview synthesize")
        return 0

    if args.cmd == "synthesize":
        ip = root / args.interview
        if not ip.exists():
            print(f"error: interview file not found: {ip}",
                  file=sys.stderr)
            print("Run `bin/retrofit-interview analyze` first.",
                  file=sys.stderr)
            return 2
        stash = root / (args.interview + ".proposal.json")
        if not stash.exists():
            print(f"error: proposal stash not found: {stash}",
                  file=sys.stderr)
            print("Re-run `bin/retrofit-interview analyze`.",
                  file=sys.stderr)
            return 2
        try:
            answers = parse_interview_answers(ip.read_text())
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        proposal = json.loads(stash.read_text())
        return _finalize(answers, proposal, root / args.out,
                          outstream=sys.stdout)

    if args.cmd == "interactive":
        answers, proposal = run_interactive(
            root, instream=sys.stdin, outstream=sys.stdout)
        return _finalize(answers, proposal, root / args.out,
                          outstream=sys.stdout)

    return 2


def _inventory_paths() -> list[str]:
    """Just for the analyze summary message. README.md is excluded
    because the installer (not the decision layer) writes it (per OD-5)."""
    return [
        ".claude/inventory/structure.md",
        ".claude/inventory/languages.md",
        ".claude/inventory/dependencies.md",
        ".claude/inventory/testing.md",
        ".claude/inventory/git-history.md",
        ".claude/inventory/conventions.md",
        ".claude/inventory/product-signals.md",
        ".claude/inventory/pm-tooling-signals.md",
        ".claude/inventory/existing-claude.md",
        ".claude/inventory/baseline-metrics.md",
    ]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

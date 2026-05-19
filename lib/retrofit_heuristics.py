"""
Inventory -> retrofit-decision proposals (stdlib only, pure functions).

The retrofit counterpart of lib/prd_heuristics.py. Where greenfield reads
PRD prose and scores keywords, retrofit reads structured InventoryData
(from lib/inventory_scan.py) and scores code-evidence. Same proposer-
never-decider contract: every proposal carries a confidence and a
rationale; genuinely ambiguous calls become explicit OPEN QUESTIONs.

Same design rules as prd_heuristics:
  * PROPOSES, never silently decides. CONF_OPEN -> OPEN QUESTION.
  * PURE FUNCTION of inputs: identical InventoryData => identical proposal.
  * Imports archetype set + principle starters from lib/defaults.py.
  * NEVER guesses commands.test/lint/format without evidence; **does**
    propose them with confidence when evidence is present (OD-3 approval).
"""

from __future__ import annotations

import re
from typing import Any

from defaults import ARCHETYPES, PRINCIPLE_STARTERS
from prd_heuristics import (
    CONF_HIGH, CONF_MEDIUM, CONF_LOW, CONF_OPEN,
    ARCHETYPE_REQUIRED_TIER, TIER_ORDER,
)


# --------------------------------------------------------------------------- #
# Archetype scoring from inventory evidence
# --------------------------------------------------------------------------- #
def _has_dep(inv: dict, *names: str) -> bool:
    """True if any of the given package names appear in any manifest."""
    deps = inv["dependencies"]["by_manifest"]
    for _, pkgs in deps.items():
        lower_pkgs = {p.lower() for p in pkgs}
        for n in names:
            if n.lower() in lower_pkgs:
                return True
    return False


def _has_dir(inv: dict, *names: str) -> bool:
    return any(d in inv["structure"]["top_level_dirs"] for d in names)


def _has_file_ext(inv: dict, *exts: str) -> bool:
    files = inv["languages"]["files_by_extension"]
    return any(e in files for e in exts)


def _has_manifest(inv: dict, *names: str) -> bool:
    m = inv["languages"]["manifests"]
    return any(m.get(n) for n in names)


def _dockerfile_count(inv: dict) -> int:
    return inv["languages"]["dockerfile_count"]


def _signals_for(arche: str, inv: dict) -> list[tuple[str, int]]:
    """Per-archetype signal accumulator. Returns (label, weight) list of
    HITS so we can both score and explain."""
    hits: list[tuple[str, int]] = []
    if arche == "cli":
        if _has_dir(inv, "cmd"):
            hits.append(("cmd/ top-level directory", 3))
        if not _has_dep(inv, "flask", "fastapi", "express", "rails",
                        "django", "starlette"):
            if _has_manifest(inv, "pyproject.toml", "package.json",
                              "Cargo.toml", "go.mod"):
                hits.append(("manifest exists but no web framework dep", 2))
        if _dockerfile_count(inv) == 0:
            hits.append(("no Dockerfile", 1))
        if (inv["structure"]["top_level_files"]
                and any(f in ("main.go", "main.rs", "main.py", "cli.py")
                        for f in inv["structure"]["top_level_files"])):
            hits.append(("main.<lang> at top level", 2))
    elif arche == "library":
        py = inv["languages"]["manifests"].get("pyproject.toml")
        pkg = inv["languages"]["manifests"].get("package.json")
        if py:
            hits.append(("pyproject.toml present", 2))
        if pkg:
            hits.append(("package.json present", 2))
        if _dockerfile_count(inv) == 0:
            hits.append(("no Dockerfile (no deploy)", 2))
        t = inv["testing"]
        if t["source_file_count"] > 0 and (
                t["test_file_count"] / max(t["source_file_count"], 1) > 0.5):
            hits.append((
                f"high test:source ratio "
                f"({t['test_file_count']}/{t['source_file_count']})", 2))
    elif arche == "service":
        if _has_dep(inv, "flask", "fastapi", "express", "rails", "django",
                    "starlette", "koa", "hapi", "gin"):
            hits.append(("web framework dependency", 3))
        if _has_dir(inv, "routes", "handlers", "controllers", "api"):
            hits.append(("routes/handlers/controllers top-level dir", 2))
        if _dockerfile_count(inv) == 1:
            hits.append(("single Dockerfile", 2))
        if not _has_dir(inv, "frontend", "client", "templates", "ui",
                        "views"):
            hits.append(("no frontend/templates dir", 1))
    elif arche == "fullstack":
        web_dep = _has_dep(inv, "flask", "fastapi", "express", "rails",
                            "django", "next", "remix", "nuxt")
        front_dep = _has_dep(inv, "react", "vue", "svelte", "next",
                              "vite", "webpack", "remix")
        if web_dep and front_dep:
            hits.append(("web framework + frontend build dep", 3))
        if _has_dir(inv, "frontend", "client", "templates", "ui", "views"):
            hits.append(("frontend/templates dir", 2))
        if _dockerfile_count(inv) >= 1:
            hits.append(("Dockerfile(s) present", 1))
    elif arche == "mobile":
        if _has_dep(inv, "react-native", "flutter"):
            hits.append(("react-native or flutter dep", 3))
        if any(f in inv["structure"]["top_level_files"]
               for f in ("pubspec.yaml", "Package.swift", "build.gradle")):
            hits.append(("mobile manifest at top level", 3))
        if _has_dir(inv, "ios", "android"):
            hits.append(("ios/ or android/ dir", 3))
    elif arche == "data-ml":
        if _has_dep(inv, "airflow", "dagster", "prefect", "luigi",
                    "kedro"):
            hits.append(("orchestration framework dep", 3))
        if _has_dep(inv, "torch", "tensorflow", "scikit-learn", "xgboost",
                    "lightgbm", "transformers"):
            hits.append(("ML framework dep", 2))
        if _has_dir(inv, "notebooks", "models", "datasets", "pipelines"):
            hits.append(("ML-shaped top-level dir", 2))
        if _has_file_ext(inv, ".ipynb"):
            hits.append(("Jupyter notebooks present", 1))
    elif arche == "ai-agent":
        if _has_dep(inv, "anthropic", "openai", "openrouter", "langchain",
                    "llamaindex", "litellm"):
            hits.append(("LLM provider dep", 3))
        if _has_dir(inv, "prompts", "agents"):
            hits.append(("prompts/ or agents/ dir", 3))
        if _has_dep(inv, "evals", "promptfoo", "langfuse", "ragas"):
            hits.append(("eval / observability dep", 2))
    elif arche == "platform":
        if _dockerfile_count(inv) >= 2:
            hits.append(
                (f"{_dockerfile_count(inv)} Dockerfiles", 3))
        # multiple pyproject/package.json suggest multi-component
        if _has_dir(inv, "services", "components", "packages", "apps"):
            hits.append(
                ("services/components/packages/apps dir", 3))
    return hits


ARCHETYPE_NOTE_RETROFIT: dict[str, str] = {
    "cli": "Forward-only spec strategy almost always right; minimal CI.",
    "library": "Adds semver discipline; public API surface is the boundary.",
    "service": "Spec gate + test gate + CI mirror; OpenAPI boundary specs.",
    "fullstack": "Multi-runtime variation common at frontend/backend.",
    "mobile": "Store-deploy gates replace web deploy gates.",
    "data-ml": "Reproducibility + drift detection emphasis.",
    "ai-agent": "Prompt versioning + evals; eval gate active.",
    "platform": "Per-component categorization is the DEFAULT, not opt-in.",
    "other": "Synthetic profile via dimension interview.",
}


def propose_archetype(inv: dict) -> dict:
    """Score every archetype against inventory evidence; surface the
    confidence indicator (HIGH/MEDIUM/LOW/OPEN) per RETROFIT R0.5."""
    scores: dict[str, int] = {}
    rationales: dict[str, list[str]] = {}
    for arche in ARCHETYPES:
        if arche == "other":
            continue
        hits = _signals_for(arche, inv)
        scores[arche] = sum(w for _, w in hits)
        rationales[arche] = [label for label, _ in hits]

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    top, top_score = ranked[0]
    second, second_score = ranked[1]

    if top_score == 0:
        # No code-evidence signal — fall back to "other" with synthetic
        # profile per RETROFIT.md R0.5.
        return {
            "value": "other",
            "confidence": CONF_OPEN,
            "rationale": (
                "Inventory contained no recognizable archetype signals "
                "(no web framework, no mobile project markers, no LLM "
                "provider deps, no orchestration framework). Falling back "
                "to 'other' with a synthetic-profile interview per "
                "RETROFIT.md R0.5 'Other' path. Human must confirm."),
            "alternatives": [a for a, _ in ranked[:3]],
            "evidence": [],
            "open_question": {
                "id": "archetype",
                "prompt": (
                    "Inventory did not match any named archetype. Which "
                    "archetype best fits this project? (Or 'other' to run "
                    "the synthetic-profile interview.)"),
                "options": sorted(ARCHETYPES),
                "default": "other",
            },
        }

    margin = top_score - second_score
    if margin < 2 and second_score > 0:
        confidence = CONF_OPEN
        return {
            "value": top,
            "confidence": confidence,
            "rationale": (
                f"Archetype is contested: '{top}' (score {top_score}, "
                f"evidence: {', '.join(rationales[top])}) and '{second}' "
                f"(score {second_score}, evidence: "
                f"{', '.join(rationales[second])}) are within the 2-point "
                f"decision margin. RETROFIT.md requires classifying "
                f"before R8 so this is surfaced for an explicit human "
                f"choice rather than guessed."),
            "alternatives": [a for a, s in ranked[:3] if s > 0],
            "evidence": rationales[top],
            "open_question": {
                "id": "archetype",
                "prompt": (
                    f"Archetype is contested between '{top}' and "
                    f"'{second}'. Which fits?"),
                "options": [a for a, s in ranked if s > 0] or sorted(
                    ARCHETYPES),
                "default": top,
            },
        }

    confidence = CONF_HIGH if (top_score >= 4 and margin >= 3) else CONF_MEDIUM
    return {
        "value": top,
        "confidence": confidence,
        "rationale": (
            f"Inventory evidence clearly indicates '{top}' "
            f"(score {top_score} vs next-best '{second}' "
            f"{second_score}; evidence: {', '.join(rationales[top])}). "
            f"{ARCHETYPE_NOTE_RETROFIT[top]}"),
        "alternatives": [a for a, s in ranked[1:3] if s > 0],
        "evidence": rationales[top],
    }


# --------------------------------------------------------------------------- #
# PRD-tier target (mirror of greenfield, derived from archetype)
# --------------------------------------------------------------------------- #
def propose_prd_tier_target(inv: dict, archetype: str) -> dict:
    """Per RETROFIT.md R0.5 step 6: tier target = archetype's required
    tier; operator can request higher, never lower. Retrofit cannot
    infer upgrade signals from a PRD (there may not be one); the tier
    target is just the floor."""
    floor = ARCHETYPE_REQUIRED_TIER.get(archetype, "standard")
    return {
        "value": floor,
        "confidence": CONF_HIGH,
        "rationale": (
            f"Archetype '{archetype}' requires the '{floor}' PRD tier "
            f"(RETROFIT.md Project Archetypes table). R1 will surface a "
            f"gap if existing PRD content is below this tier."),
        "floor": floor,
    }


# --------------------------------------------------------------------------- #
# Spec strategy (R4)
# --------------------------------------------------------------------------- #
def propose_spec_strategy(inv: dict, archetype: str) -> dict:
    """Forward-only is the safe default per RETROFIT.md R4 step 2. We
    upgrade the recommendation to touch-based only if the project has
    obvious modernization signals (an active migration; large legacy
    base). Bulk backfill is never recommended automatically."""
    src_count = inv["testing"]["source_file_count"]
    no_test_count = inv["testing"]["no_test_module_count"]
    rationale = (
        "Forward-only is the safe default per RETROFIT.md R4 step 2: "
        "new features get specs; existing code is exempted via the legacy "
        "allowlist (which lists everything in the inventory's existing-"
        "source list) until first touched. Operator can upgrade to "
        "touch-based at R4 step 3 if frequent legacy modifications "
        "are expected.")
    if no_test_count > 50 and src_count > 100:
        rationale += (
            " (Note: this codebase has substantial untested legacy code "
            f"[{no_test_count} no-test modules]; touch-based is also "
            "reasonable and pairs well with pin-first discipline.)")
    return {
        "value": "forward-only",
        "confidence": CONF_HIGH,
        "rationale": rationale,
    }


# --------------------------------------------------------------------------- #
# Legacy allowlist (R4)
# --------------------------------------------------------------------------- #
def propose_legacy_allowlist(inv: dict) -> list[str]:
    """Default forward-only allowlist: every top-level source directory
    glob ('src/**', 'lib/**', etc.) plus every top-level source file.
    Operator can edit at R4 step 5. Operator chooses to ADD paths
    (NOT remove) — removing means subjecting those paths to spec gating
    immediately, which defeats forward-only retrofit."""
    out: list[str] = []
    for d, info in inv["structure"]["top_level_dirs"].items():
        if info["source_files"] > 0:
            out.append(f"{d}/**")
    for f in inv["structure"]["top_level_files"]:
        if any(f.endswith(ext) for ext in (".py", ".js", ".ts", ".rs",
                                            ".go", ".rb")):
            out.append(f)
    return sorted(set(out))


# --------------------------------------------------------------------------- #
# PM strategy (R0.7)
# --------------------------------------------------------------------------- #
def propose_pm_strategy(inv: dict, archetype: str) -> dict:
    """Strategy A (spec-canonical) by default for single-owner CLI/Library/
    Service; Strategy C (hybrid) for multi-owner / multi-component; Strategy
    B requires explicit operator preference."""
    pm = inv["pm_tooling_signals"]
    contributor_count = inv["git_history"].get("contributor_count", 0)
    has_pm_signal = bool(pm["in_repo_ticket_dirs"]
                          or pm["ci_integrations"]
                          or pm["commit_msg_ticket_ref_counts"])

    if not has_pm_signal:
        return {
            "strategy": "spec_canonical",
            "tool": "none",
            "tool_role_after": "removed",
            "confidence": CONF_HIGH,
            "rationale": (
                "No PM-tooling signals in inventory (no in-repo ticket "
                "directories, no CI integration with Linear/Jira/GitHub "
                "Issues, no ticket-reference patterns in commits). "
                "Strategy A (spec-canonical) is the natural default; "
                "specs in .claude/specs/ become the source of truth."),
        }

    # Some PM signal exists. Single owner -> A; multi-owner -> C; platform -> C
    multi_owner = contributor_count > 1
    is_platform = archetype == "platform"
    if multi_owner or is_platform:
        return {
            "strategy": "hybrid",
            "tool": _infer_pm_tool(pm),
            "tool_role_after": "hybrid_transitional",
            "confidence": CONF_MEDIUM,
            "rationale": (
                f"PM-tooling signals detected (in-repo tickets / CI "
                f"integration / commit ref patterns) plus "
                f"{contributor_count} contributors / "
                f"{'platform archetype' if is_platform else 'multi-owner'}. "
                f"Strategy C (hybrid) recommended: new initiatives get "
                f"specs; in-flight tickets stay in PM tool until closure; "
                f"90-day cutover review."),
            "open_question": {
                "id": "pm_strategy",
                "prompt": (
                    "PM-tooling signals + multi-owner detected. Strategy "
                    "A (spec-canonical), B (PM-canonical with spec "
                    "bridge), or C (hybrid with cutover)? Defaults to C."),
                "options": ["A", "B", "C"],
                "default": "C",
            },
        }
    return {
        "strategy": "spec_canonical",
        "tool": _infer_pm_tool(pm),
        "tool_role_after": "removed",
        "confidence": CONF_MEDIUM,
        "rationale": (
            "PM-tooling signals detected, but single-owner: Strategy A "
            "(spec-canonical) recommended. Archive existing tickets, "
            "convert open ones via ticket-to-spec post-retrofit, "
            "remove CI ticket-status updates."),
    }


def _infer_pm_tool(pm: dict) -> str:
    if pm["in_repo_ticket_dirs"]:
        return "tickets_dir"
    for ci in pm["ci_integrations"]:
        if ci["tool"] in ("linear", "jira", "github_issues"):
            return ci["tool"]
    return "none"


# --------------------------------------------------------------------------- #
# Commands proposal (OD-3: propose with confidence; HUMAN-REQUIRED on empty)
# --------------------------------------------------------------------------- #
def propose_commands(inv: dict) -> dict:
    """OD-3-approved: detect candidate commands from CI / manifest scripts /
    Makefile with HIGH/MED/LOW confidence. Operator accepts/edits in
    ANSWERS block; if cleared, the installer's fail-loud TODO-gate
    contract still applies (greenfield invariant preserved)."""
    proposals: dict[str, dict] = {}
    sources_found: list[str] = []

    # package.json scripts (HIGH-confidence — explicit declared command).
    if inv["languages"]["manifests"].get("package.json"):
        sources_found.append("package.json:scripts")
    # Makefile (HIGH-confidence for test/lint targets).
    if inv["languages"]["manifests"].get("Makefile"):
        sources_found.append("Makefile")

    # CI workflow scan (HIGH-confidence — what actually runs).
    # Lightweight: check for common test/lint invocations in workflow files.
    import os
    ci_dir = os.path.join(".", ".github", "workflows")
    ci_text = ""
    if os.path.isdir(ci_dir):
        for fn in os.listdir(ci_dir):
            try:
                with open(os.path.join(ci_dir, fn), errors="replace") as fh:
                    ci_text += fh.read()
            except OSError:
                pass

    def _propose(name: str, value: str, conf: str, src: str) -> None:
        if name not in proposals:
            proposals[name] = {
                "value": value, "confidence": conf, "source": src,
            }

    # Pattern: invoking test runner anywhere in CI
    if re.search(r"\bpytest(\s|$)", ci_text):
        _propose("test", "pytest -q", CONF_HIGH, "ci-workflow:pytest")
    elif re.search(r"\bnpm\s+test\b|\bnpm\s+run\s+test\b", ci_text):
        _propose("test", "npm test", CONF_HIGH, "ci-workflow:npm")
    elif re.search(r"\bgo\s+test\b", ci_text):
        _propose("test", "go test ./...", CONF_HIGH, "ci-workflow:go test")
    elif re.search(r"\bcargo\s+test\b", ci_text):
        _propose("test", "cargo test", CONF_HIGH, "ci-workflow:cargo test")

    if re.search(r"\bruff\s+check\b", ci_text):
        _propose("lint", "ruff check .", CONF_HIGH, "ci-workflow:ruff")
    elif re.search(r"\beslint\b", ci_text):
        _propose("lint", "eslint .", CONF_HIGH, "ci-workflow:eslint")
    elif re.search(r"\bclippy\b", ci_text):
        _propose("lint", "cargo clippy", CONF_HIGH, "ci-workflow:clippy")

    if re.search(r"\bruff\s+format\b|\bblack\b", ci_text):
        _propose("format",
                 "ruff format ." if "ruff format" in ci_text else "black .",
                 CONF_HIGH, "ci-workflow")
    elif re.search(r"\bprettier\b", ci_text):
        _propose("format", "prettier --check .", CONF_HIGH,
                 "ci-workflow:prettier")
    elif re.search(r"\bcargo\s+fmt\b", ci_text):
        _propose("format", "cargo fmt", CONF_HIGH, "ci-workflow:cargo fmt")

    # Manifest-script fallback (MEDIUM — declared but not proven to run).
    if "package.json" in inv["dependencies"]["by_manifest"] \
            or inv["languages"]["manifests"].get("package.json"):
        # Look in package.json for scripts section
        import json
        try:
            with open(os.path.join(".", "package.json")) as fh:
                doc = json.load(fh)
            scripts = doc.get("scripts", {}) or {}
            for cmd in ("test", "lint", "format"):
                if cmd in scripts and cmd not in proposals:
                    _propose(cmd, f"npm run {cmd}", CONF_MEDIUM,
                             "package.json:scripts")
        except (OSError, ValueError):
            pass

    # Low-confidence guesses from framework presence (LOW — heuristic).
    if "test" not in proposals and any(
            inv["languages"]["manifests"].get(m)
            for m in ("pyproject.toml", "setup.py")):
        if "pytest" in inv["testing"]["frameworks_detected"]:
            _propose("test", "pytest -q", CONF_LOW,
                     "pytest framework detected")

    if not proposals:
        rationale = (
            "No project commands detected in CI workflows, manifests, or "
            "framework presence. Per OD-3 the proposal stays empty and "
            "the installer's fail-loud TODO-gate contract applies. "
            "Operator fills the ANSWERS block with the actual commands.")
        confidence = CONF_OPEN
    else:
        rationale = (
            f"Detected from: {', '.join(sources_found) or 'CI workflows'}. "
            f"Per OD-3, retrofit proposes commands with confidence; HUMAN-"
            f"REQUIRED TODO-gate contract preserved if operator clears any. "
            f"Found: {', '.join(proposals.keys())}.")
        # Pick lowest confidence among proposals as overall.
        confs = [p["confidence"] for p in proposals.values()]
        order = [CONF_HIGH, CONF_MEDIUM, CONF_LOW, CONF_OPEN]
        confidence = max(confs, key=order.index)

    return {
        "proposals": proposals,
        "confidence": confidence,
        "rationale": rationale,
    }


# --------------------------------------------------------------------------- #
# Principles (R5; brownfield-default tdd: encouraged)
# --------------------------------------------------------------------------- #
def propose_principles_retrofit(inv: dict, archetype: str) -> dict:
    """Brownfield default tdd_policy is 'encouraged' (RETROFIT.md R5 step
    2: many existing modules have no tests; forcing TDD via hook would
    block edits). Principles starter set is the same as greenfield."""
    starters = list(PRINCIPLE_STARTERS[archetype])
    no_test_count = inv["testing"]["no_test_module_count"]
    rationale = (
        f"Starter set for '{archetype}' taken verbatim from "
        f"lib/defaults.PRINCIPLE_STARTERS. Brownfield TDD policy default "
        f"is 'encouraged' (RETROFIT.md R5 step 2): retrofit codebase has "
        f"{no_test_count} no-test modules; forcing TDD via hook would "
        f"block most edits. Operator may upgrade to 'required'.")
    return {
        "starter_set": starters,
        "proposed_additions": [],
        "ranked": list(starters),
        "tdd_policy": {
            "value": "encouraged",
            "confidence": CONF_MEDIUM if no_test_count > 0 else CONF_HIGH,
            "rationale": (
                "RETROFIT.md R5 step 2 brownfield default. Override to "
                "'required' only after the touch-based-backfill flow has "
                "produced tests for legacy modules."),
        },
        "confidence": CONF_HIGH,
        "rationale": rationale,
    }


# --------------------------------------------------------------------------- #
# Secrets / deps (largely same as greenfield)
# --------------------------------------------------------------------------- #
def propose_secrets_retrofit(inv: dict) -> dict:
    """Secrets enabled by default; brownfield can run a historical-leakage
    git scan (R5.5) — that's not done here (decision-layer scope), but the
    proposal records the policy enabled with conservative defaults."""
    return {
        "enabled": True,
        "confidence": CONF_HIGH,
        "rationale": (
            "Brownfield always-on default per RETROFIT.md R5.5: "
            "operator confirms paths against actual project layout. "
            "Historical secret-leakage git scan (R5.5 step 2) runs "
            "separately when git is available; any findings stop the "
            "protocol per RETROFIT 'Protocol rules for the AI'."),
    }


def propose_deps_retrofit(inv: dict) -> dict:
    """Deps policy enabled with the manifests' actual contents as the
    initial approved list (R5.5)."""
    deps = inv["dependencies"]["by_manifest"]
    has_any_deps = any(pkgs for pkgs in deps.values())
    if not has_any_deps:
        return {
            "enabled": False,
            "confidence": CONF_MEDIUM,
            "rationale": (
                "No declared dependencies found in any manifest. Likely "
                "stdlib-only project; RETROFIT.md Skip Policy allows "
                "skipping R5.5 dep-vetting in this case. Operator "
                "confirms."),
        }
    return {
        "enabled": True,
        "confidence": CONF_HIGH,
        "rationale": (
            f"Detected dependencies in "
            f"{len(deps)} manifest(s); initial approved list is the "
            f"union of what currently exists (R5.5: 'use inventory as "
            f"the initial approved list'). Operator curates."),
    }


# --------------------------------------------------------------------------- #
# Autonomous modes (always defer per RETROFIT v1.6.2 scaffold-but-defer)
# --------------------------------------------------------------------------- #
def propose_autonomous_modes_retrofit(inv: dict) -> dict:
    """RETROFIT v1.6.2 scaffold-but-defer: all opt-ins default OFF. The
    wizard NEVER enables a mode at retrofit time; the operator
    consciously opts INTO scaffold-and-defer (recording opt-in intent)
    or opts out (no scaffolding). Either way *_enabled stays false."""
    return {
        "loop_mode_opted_in": False,
        "goal_supervised_mode_opted_in": False,
        "queue_mode_opted_in": False,
        "confidence": CONF_HIGH,
        "rationale": (
            "RETROFIT.md R0.5 step 7 + §'Autonomous Modes in Retrofit': "
            "all three default OFF. Brownfield trust milestones (R8.G/H/I) "
            "must be met post-retrofit before any mode is enabled. "
            "Opting in now SCAFFOLDS the mode default-disabled with the "
            "milestone recorded; opting out skips scaffolding entirely. "
            "The wizard NEVER enables a mode at retrofit time."),
        "open_question": {
            "id": "autonomous_modes",
            "prompt": (
                "RETROFIT.md scaffold-but-defer: opt INTO scaffolding "
                "for loop / goal-supervised / queue (each independent; "
                "queue requires loop or goal). None enable at retrofit "
                "time. Defaults: all OFF."),
            "options": [
                "None (recommended)",
                "Loop scaffolding only",
                "Goal-supervised scaffolding only",
                "Loop + goal scaffolding",
                "Loop + goal + queue scaffolding",
            ],
            "default": "None (recommended)",
        },
    }


# --------------------------------------------------------------------------- #
# Project name (mirrors greenfield's H1 + Project:/Name: heuristics)
# --------------------------------------------------------------------------- #
def propose_project_name_retrofit(inv: dict, fallback: str) -> dict:
    inferred = inv["product_signals"]["inferred_project_name"]
    if inferred:
        # Strip markdown formatting like "**foo**"
        cleaned = re.sub(r"[*_`]", "", inferred).strip()
        return {
            "value": cleaned[:80],
            "confidence": CONF_LOW,
            "rationale": "Taken from README leading H1; confirm or rename.",
        }
    return {
        "value": fallback,
        "confidence": CONF_OPEN,
        "rationale": (
            "No README H1 detected. Using fallback placeholder; "
            "operator must set real project name."),
    }


# --------------------------------------------------------------------------- #
# CI/CD applicability (R0.5 step 5)
# --------------------------------------------------------------------------- #
def propose_ci_cd_applicability(inv: dict) -> dict:
    """RETROFIT.md R0.5 step 5: if inventory cited existing .github/
    workflows/ or similar, default 'yes' with operator confirm."""
    import os
    for path in (".github/workflows", ".gitlab-ci.yml", ".circleci",
                 "Jenkinsfile"):
        if os.path.exists(os.path.join(".", path)):
            return {
                "value": "yes",
                "confidence": CONF_HIGH,
                "rationale": (
                    f"Found existing CI configuration at `{path}`; "
                    f"R8.F ratifies what exists rather than designing "
                    f"from scratch."),
            }
    return {
        "value": "unknown",
        "confidence": CONF_OPEN,
        "rationale": (
            "No CI configuration files detected at standard locations. "
            "Operator confirms: 'yes' (will be added), 'no' (R8.F opt-"
            "out), or 'unknown' (defer)."),
        "open_question": {
            "id": "ci_cd_applicability",
            "prompt": (
                "No CI config detected. Does this project use CI/CD "
                "(or plan to)?"),
            "options": ["yes", "no"],
            "default": "no",
        },
    }


# --------------------------------------------------------------------------- #
# Debt aggregation (R3)
# --------------------------------------------------------------------------- #
def propose_debt_entries(inv: dict) -> list[dict]:
    """Aggregate the inventory's debt-shaped signals into R3 entries.
    Each entry: {what, where, severity, discovered, plan, status}."""
    entries: list[dict] = []
    t = inv["testing"]
    if t["no_test_module_count"] > 0:
        entries.append({
            "what": (
                f"{t['no_test_module_count']} modules have no "
                f"name-matching test"),
            "where": (
                "see inventory/testing.md no-test list"),
            "severity": "medium",
            "discovered": "retrofit R0 testing inventory",
            "plan": (
                "touch-based backfill: add tests via legacy-pin-test "
                "when modules are first modified"),
            "status": "open",
        })
    if inv["git_history"].get("working_tree_dirty"):
        entries.append({
            "what": "working tree was dirty at retrofit start",
            "where": "project root",
            "severity": "low",
            "discovered": "retrofit R-1 git status",
            "plan": (
                "operator commits/stashes before relying on the new hooks"),
            "status": "open",
        })
    if not inv["conventions"]["has_lint_config"]:
        entries.append({
            "what": "no lint configuration detected",
            "where": "project root",
            "severity": "medium",
            "discovered": "retrofit R0 conventions scan",
            "plan": (
                "add lint config; the format-lint-gate hook will fail "
                "loudly with a TODO until commands.lint is non-empty"),
            "status": "open",
        })
    return entries


# --------------------------------------------------------------------------- #
# Composite proposal entry point (orchestrated by retrofit_interview.py)
# --------------------------------------------------------------------------- #
def build_retrofit_proposal(inv: dict, *,
                             project_fallback: str = "my-project") -> dict:
    """Pure deterministic function of inventory; no clock, no I/O. Mirrors
    lib/interview.build_proposal but for retrofit."""
    name = propose_project_name_retrofit(inv, project_fallback)
    arche = propose_archetype(inv)
    tier = propose_prd_tier_target(inv, arche["value"])
    principles = propose_principles_retrofit(inv, arche["value"])
    spec_strategy = propose_spec_strategy(inv, arche["value"])
    legacy_allowlist = propose_legacy_allowlist(inv)
    pm = propose_pm_strategy(inv, arche["value"])
    commands = propose_commands(inv)
    secrets = propose_secrets_retrofit(inv)
    deps = propose_deps_retrofit(inv)
    autonomous = propose_autonomous_modes_retrofit(inv)
    ci_cd = propose_ci_cd_applicability(inv)
    debt = propose_debt_entries(inv)

    proposal: dict[str, Any] = {
        "project_name": name,
        "archetype": arche,
        "prd_tier": tier,
        "principles": principles,
        "spec_strategy": spec_strategy,
        "legacy_allowlist": legacy_allowlist,
        "pm": pm,
        "commands": commands,
        "secrets": secrets,
        "deps": deps,
        "autonomous_modes": autonomous,
        "ci_cd_applicability": ci_cd,
        "debt": debt,
        "_inventory_summary": {
            "source_file_count": inv["testing"]["source_file_count"],
            "test_file_count": inv["testing"]["test_file_count"],
            "no_test_module_count": inv["testing"]["no_test_module_count"],
            "total_commits": inv["git_history"].get("total_commits", 0),
            "degraded_git": inv["git_history"].get("degraded", False),
            "has_prior_claude": inv["existing_claude"]["has_existing_claude"],
            "has_root_claude_md": inv["existing_claude"]["has_root_claude_md"],
        },
    }
    proposal["open_questions"] = _derive_open_questions(proposal)
    return proposal


def _derive_open_questions(p: dict) -> list[dict]:
    oqs = []
    for key in ("archetype", "pm", "ci_cd_applicability",
                "autonomous_modes"):
        oq = p.get(key, {}).get("open_question")
        if oq:
            oqs.append(oq)
    if p["project_name"]["confidence"] == CONF_OPEN:
        oqs.append({
            "id": "project_name",
            "prompt": "No project name detected. What is it?",
            "options": [],
            "default": p["project_name"]["value"],
        })
    return oqs

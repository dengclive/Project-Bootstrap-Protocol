"""
Decision-layer interview tool: PRD -> proposed bootstrap.config.yaml.

Three front-ends, one core:

  analyze     PRD -> bootstrap.interview.md   (proposal + rationale + OPEN
                                                QUESTIONs + machine-readable
                                                ANSWERS block the human edits)
  synthesize  bootstrap.interview.md -> bootstrap.config.yaml  (validated)
  interactive PRD -> prompts on stdin -> bootstrap.config.yaml  (validated)

Invariants enforced everywhere:

  * Proposes, never silently decides. Ambiguity becomes an OPEN QUESTION.
  * commands.test/lint/format are NEVER guessed - emitted empty and flagged
    HUMAN-REQUIRED; the installer warns about each one it finds empty.
  * The emitted config is validated by shelling `bin/bootstrap-install
    --print-config`; the tool refuses to finish on validation failure.
  * The proposal core (build_proposal) is a pure function of PRD text:
    identical PRD => identical proposal => identical interview file. The
    interactive front-end is the only non-deterministic surface and is
    explicitly excluded from determinism guarantees (like the installer's
    timestamped metadata files).
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

import prd_heuristics as H
import llm_advisor as LLM
from configemit import emit
from defaults import DEFAULTS, resolve_config
from minyaml import load_yaml

HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "bin" / "bootstrap-install"

INTERVIEW_DEFAULT = "bootstrap.interview.md"
CONFIG_DEFAULT = "bootstrap.config.yaml"

# [WP1] The Phase 6 per-hook toggles the ANSWERS block exposes, in render
# order. Each name is a `hooks.<name>` key in bootstrap.config.yaml and the
# answer key is `hooks_<name>`. The set is exactly the toggle keys of
# DEFAULTS["hooks"] (the drift_* thresholds are numbers, not toggles) MINUS
# the two security gates, and a test pins that, so a toggle added to the
# installer cannot go unasked here. tdd_gate and eval_gate default to None in
# DEFAULTS ("derive it"), so they take a third value, `auto`.
#
# [D3 ruling] secrets_gate and dependency_gate are deliberately NOT offered:
# secrets_enabled and deps_enabled are the only interview switches for the
# two security gates. A hand-written `hooks.secrets_gate/dependency_gate:
# false` in bootstrap.config.yaml predates WP1 and resolve_config still
# honours it; the interview just never writes one.
SECURITY_HOOK_TOGGLES = frozenset({"secrets_gate", "dependency_gate"})
# The two answers that do switch them, and the gate each one switches. Both
# predate WP1, but since D3 false removes a gate, so an unreadable value is
# an error, not the "read as false" older boolean keys still get.
POLICY_ANSWER_KEYS = {"secrets_enabled": "the secrets gate",
                      "deps_enabled": "the dependency gate"}
HOOK_TOGGLES = (
    ("spec_gate_entry", "prints a notice when a prompt has no active spec"),
    ("spec_gate_commit", "blocks a commit of files no active spec names"),
    ("test_gate", "runs commands.test before a commit; blocks on failure"),
    ("format_lint_gate", "runs commands.lint after a Write or Edit"),
    ("ci_mirror", "runs commands.ci_local before a push; blocks on failure"),
    ("cost_log", "appends one line per session event to .claude/logs/"),
    ("tdd_gate", "tests-before-source gate; auto = on when tdd_policy is "
                 "required"),
    ("eval_gate", "eval-before-push gate; auto = on for the ai-agent "
                  "archetype"),
    ("drift_detector", "counts tool calls; prints a notice past the "
                       "threshold"),
    ("task_done_alarm", "prints a notice when a subagent finishes"),
    ("decision_required_alarm", "prints a notice when the session needs "
                                "you"),
)
HOOK_TOGGLE_NAMES = tuple(n for n, _ in HOOK_TOGGLES)
HOOK_TRISTATE = frozenset({"tdd_gate", "eval_gate"})
HOOK_ANSWER_KEYS = tuple(f"hooks_{n}" for n in HOOK_TOGGLE_NAMES)

# Keys whose answers the human supplies in the ANSWERS block. Each maps to a
# (section, builder) the synthesize step understands. Order is the order the
# interview file presents them and the order interactive mode prompts them.
ANSWER_KEYS = [
    "project_name",
    "archetype",
    "prd_tier",
    # [WP1] Phase 0 classification fields answers_to_config used to hard-code.
    "prd_path",
    "shell",
    "cicd_opt_out",
    "principles_ranked",
    # [WP1] Phase 4 step 5; answers_to_config used to hard-code [].
    "principles_tiebreakers",
    "tdd_policy",
    "secrets_enabled",
    "secrets_never_read_paths",
    "deps_enabled",
    "loop_mode_enabled",
    "goal_supervised_mode_enabled",
    "queue_mode_enabled",
    # TEL-01 (v2.4.0 fold): standalone top-level opt-in, NOT an autonomous
    # mode (independent of every autonomous mode). Default skip.
    "telemetry_export_enabled",
    # DS-01 (v2.5.0): twin top-level opt-ins (design doc + its optional skill),
    # independent of every autonomous mode. Default skip. The interactive OFFER
    # is archetype-gated; these keys and the flags are not.
    "design_steering_enabled",
    "design_review_skill_enabled",
    "commands_test",
    "commands_lint",
    "commands_format",
    "commands_typecheck",
    "commands_ci_local",
    # [W-1] Not a command, a FACT ABOUT the five above: do they honor the
    # directory they are invoked from? Defaults true (the pre-W-1 behavior);
    # false makes the installer drop `isolation: worktree` rather than emit a
    # gate that tests a tree the agent never wrote to.
    "commands_execute_in_cwd",
    # [WP1] Phase 6: one toggle per hook (see HOOK_TOGGLES).
    *HOOK_ANSWER_KEYS,
]


# --------------------------------------------------------------------------- #
# Pure proposal core
# --------------------------------------------------------------------------- #
def _deterministic_proposal(prd_text: str, project_fallback: str) -> dict:
    """The pure, deterministic proposal (no I/O, no clock). This is always
    computed; the LLM advisor only ever refines this structure."""
    arche = H.propose_archetype(prd_text)
    tier = H.propose_prd_tier(prd_text, arche["value"])
    principles = H.propose_principles(prd_text, arche["value"])
    tdd = H.propose_tdd_policy(prd_text)
    secrets = H.propose_secrets(prd_text)
    deps = H.propose_deps(prd_text)
    modes = H.propose_autonomous_modes(prd_text)
    name = H.propose_project_name(prd_text, project_fallback)
    return {
        "project_name": name,
        "archetype": arche,
        "prd_tier": tier,
        "principles": principles,
        "tdd_policy": tdd,
        "secrets": secrets,
        "deps": deps,
        "autonomous_modes": modes,
    }


def _derive_open_questions(p: dict) -> list[dict]:
    """Re-derive the OPEN QUESTION list from a (possibly refined) proposal.

    Done after any refinement so an advisor that lowered confidence to
    'open' still surfaces as an explicit human question - the model can
    never silently resolve ambiguity."""
    oqs = []
    for key in ("archetype", "secrets", "autonomous_modes"):
        oq = p.get(key, {}).get("open_question")
        if oq:
            oqs.append(oq)
    if p["project_name"]["confidence"] == H.CONF_OPEN:
        oqs.append({
            "id": "project_name",
            "prompt": "No project name found in the PRD. What is it?",
            "options": [],
            "default": p["project_name"]["value"],
        })
    return oqs


def build_proposal(prd_text: str, *, project_fallback: str = "my-project",
                   use_llm: bool = False) -> dict:
    """PRD text -> structured proposal.

    Default (use_llm=False): a pure deterministic function - identical PRD
    yields an identical proposal (digest-stable; covered by determinism
    tests).

    Opt-in (use_llm=True): the deterministic proposal is still computed first
    and then *refined* by the LLM advisor within bounds the deterministic
    layer validates. This path is intentionally non-deterministic (like the
    interactive front-end) and excluded from determinism guarantees; if no
    model is reachable it degrades loudly to the deterministic proposal with
    a visible notice.
    """
    det = _deterministic_proposal(prd_text, project_fallback)
    if use_llm:
        det = LLM.maybe_refine(prd_text, det, enabled=True)
    det["open_questions"] = _derive_open_questions(det)
    return det


def default_answers(proposal: dict, prd_path: str | None = None) -> dict:
    """The answer set if the human edits nothing - i.e. accept every
    proposal. Every value here is a conscious proposal with a rationale, so
    this still satisfies 'proposes, never silently decides': the human saw
    each one and chose not to override.

    [WP1] `prd_path` is the PRD this interview read, as the config records
    it (see _config_prd_path). Without one, the answer is the installer's
    default location, which is what every earlier version emitted."""
    p = proposal
    return {
        "project_name": p["project_name"]["value"],
        "archetype": p["archetype"]["value"],
        "prd_tier": p["prd_tier"]["value"],
        "prd_path": prd_path or DEFAULTS["project"]["prd_path"],
        "shell": DEFAULTS["project"]["shell"],
        "cicd_opt_out": DEFAULTS["project"]["cicd_opt_out"],
        "principles_ranked": list(p["principles"]["ranked"]),
        # Never guessed from the PRD: tiebreakers name principles in tension,
        # which is the operator's call (Phase 4 step 5).
        "principles_tiebreakers": [],
        "tdd_policy": p["tdd_policy"]["value"],
        "secrets_enabled": p["secrets"]["enabled"],
        "secrets_never_read_paths": [".env*", "secrets/**", "*.pem", "*.key"],
        "deps_enabled": p["deps"]["enabled"],
        "loop_mode_enabled": p["autonomous_modes"]["loop_mode_enabled"],
        "goal_supervised_mode_enabled":
            p["autonomous_modes"]["goal_supervised_mode_enabled"],
        "queue_mode_enabled": p["autonomous_modes"]["queue_mode_enabled"],
        # TEL-01 (v2.4.0 fold): default skip (opt-in only, independent of the
        # autonomous modes). The operator flips it in the ANSWERS block or the
        # interactive prompt.
        "telemetry_export_enabled": False,
        # DS-01 (v2.5.0): both default skip (opt-in only). The operator flips
        # design_steering_enabled in the ANSWERS block or the archetype-gated
        # interactive prompt; the skill is a second decision gated on the first.
        "design_steering_enabled": False,
        "design_review_skill_enabled": False,
        # NEVER guessed - emitted empty, flagged HUMAN-REQUIRED.
        "commands_test": "",
        "commands_lint": "",
        "commands_format": "",
        "commands_typecheck": "",
        "commands_ci_local": "",
        # [W-1] True is the pre-W-1 behavior and the common case (a plain
        # `pytest -q` does honor cwd). A PRD cannot tell us this any more than
        # it can tell us the commands themselves, so it is proposed, shown, and
        # overridable — never inferred from the PRD text.
        "commands_execute_in_cwd": True,
        # [WP1] The installer's own defaults: True, or None ("auto") for the
        # two derived gates.
        **{f"hooks_{n}": DEFAULTS["hooks"][n] for n in HOOK_TOGGLE_NAMES},
    }


# --------------------------------------------------------------------------- #
# answers -> config dict (then validated by resolve_config / --print-config)
# --------------------------------------------------------------------------- #
def answers_to_config(ans: dict) -> dict:
    """Assemble a config dict in the schema bootstrap.config.yaml uses.

    We deliberately emit only the fields a human decides; resolve_config
    fills the rest (drift thresholds, etc.) from DEFAULTS.

    [WP1] Every key added for WP1 is read with .get() and the value earlier
    versions hard-coded, so a hand-built or older answers dict still works.
    The `hooks:` block carries only the toggles that differ from DEFAULTS, so
    accepting every proposal emits no `hooks:` key at all.
    """
    paths = ans.get("secrets_never_read_paths") \
        or [".env*", "secrets/**", "*.pem", "*.key"]
    cfg = {
        "project": {
            "name": ans["project_name"],
            "archetype": ans["archetype"],
            "shell": ans.get("shell") or DEFAULTS["project"]["shell"],
            "prd_tier": ans["prd_tier"],
            "prd_path": ans.get("prd_path")
            or DEFAULTS["project"]["prd_path"],
            "cicd_opt_out": bool(ans.get("cicd_opt_out", False)),
        },
        "autonomous_modes": {
            "loop_mode_enabled": bool(ans["loop_mode_enabled"]),
            "goal_supervised_mode_enabled":
                bool(ans["goal_supervised_mode_enabled"]),
            "queue_mode_enabled": bool(ans["queue_mode_enabled"]),
        },
        # TEL-01 (v2.4.0 fold): standalone TOP-LEVEL boolean — deliberately NOT
        # nested under autonomous_modes (telemetry is independent of every
        # autonomous mode). build_plan's flag-gated add and _write_state both
        # key off this exact top-level path.
        "telemetry_export_enabled": bool(ans.get("telemetry_export_enabled",
                                                  False)),
        # DS-01 (v2.5.0): standalone TOP-LEVEL booleans — deliberately NOT nested
        # under autonomous_modes (design steering is independent of every
        # autonomous mode). build_plan's flag-gated add and _write_state both key
        # off these exact top-level paths.
        "design_steering_enabled": bool(ans.get("design_steering_enabled",
                                                 False)),
        "design_review_skill_enabled":
            bool(ans.get("design_review_skill_enabled", False)),
        "principles": {
            "ranked": list(ans["principles_ranked"]),
            "tiebreakers": list(ans.get("principles_tiebreakers") or []),
            "tdd_policy": ans["tdd_policy"],
        },
        "secrets": {
            "enabled": bool(ans["secrets_enabled"]),
            "never_read_paths": list(paths),
            "rotation_policy":
                "Rotate any exposed credential immediately; never echo to output.",
        },
        "deps": {"enabled": bool(ans["deps_enabled"]), "approved": []},
        "commands": {
            "test": ans["commands_test"],
            "lint": ans["commands_lint"],
            "format": ans["commands_format"],
            "typecheck": ans["commands_typecheck"],
            "ci_local": ans["commands_ci_local"],
            # [W-1] .get with a True default so a hand-trimmed answers dict
            # lands on the pre-W-1 behavior rather than KeyError-ing.
            "execute_in_cwd": bool(ans.get("commands_execute_in_cwd", True)),
        },
    }
    hooks = {}
    for name in HOOK_TOGGLE_NAMES:
        default = DEFAULTS["hooks"][name]
        value = ans.get(f"hooks_{name}", default)
        # [D3] HOOK_TOGGLE_NAMES has no security gate, so nothing here
        # writes `hooks.secrets_gate/dependency_gate`: secrets.enabled and
        # deps.enabled are their switches, applied in resolve_config.
        # Writing `false` for them whenever a policy was off made gate-off
        # STICKY - flipping the policy back to true in the config left both
        # gates off.
        if value != default:
            hooks[name] = value
    if hooks:
        cfg["hooks"] = hooks
    return cfg


def _config_prd_path(prd: Path, out: Path) -> str:
    """[WP1] The PRD path as bootstrap.config.yaml records it.

    The tool treats the directory it writes into as the project root, so
    a PRD under that directory is recorded relative to it:
    `docs/prd/PRD.md` in the README flow. A PRD outside it is recorded as
    given. Either way the ANSWERS block shows the value for review."""
    try:
        return prd.resolve().relative_to(out.resolve().parent).as_posix()
    except ValueError:
        return prd.as_posix()


def validate_config_dict(cfg: dict) -> list[str]:
    """Validate via the SAME resolve_config the installer uses, plus the
    decision-layer-only invariants the mechanical installer does not police.

    resolve_config (frozen, installer-shared) enforces archetype membership,
    the queue=>loop|goal skip-policy invariant, and the TDD enum. It does
    NOT enforce Bootstrap-Protocol-v2-0-0.md Phase 0 step 7 ("operator can request a higher
    PRD tier but not a lower one"): the archetype's required tier is a
    *decision-layer* contract, not a mechanical one, so a hand-edited
    interview file could otherwise set `prd_tier` below the archetype floor
    and still pass both gates (review finding F-3). We add that check here so
    the interview tool refuses to emit a sub-floor config, exactly as the
    interactive front-end already refuses interactively.
    """
    _, errors = resolve_config(cfg)
    errors = list(errors)
    proj = cfg.get("project", {}) if isinstance(cfg, dict) else {}
    arche = proj.get("archetype")
    tier = proj.get("prd_tier")
    if arche in H.ARCHETYPE_REQUIRED_TIER and tier in H.TIER_ORDER:
        floor = H.ARCHETYPE_REQUIRED_TIER[arche]
        if H.TIER_ORDER[tier] < H.TIER_ORDER[floor]:
            errors.append(
                f"project.prd_tier '{tier}' is below the required floor "
                f"'{floor}' for archetype '{arche}' (Bootstrap-Protocol-v2-0-0.md Phase 0 "
                f"step 7: a higher tier may be requested, never a lower "
                f"one). Raise prd_tier to at least '{floor}'.")
    return errors


def validate_with_installer(config_path: Path) -> tuple[int, str]:
    """Shell `bin/bootstrap-install --print-config` - the authoritative gate
    named in the session constraints. Returns (returncode, combined output)."""
    # [WP1] Absolute: the installer resolves a relative -c against -C, so
    # `-o sub/c.yaml` asked it for sub/sub/c.yaml and the tool reported its
    # own valid draft as rejected.
    config_path = config_path.resolve()
    proc = subprocess.run(
        [sys.executable, str(BIN), "-c", str(config_path),
         "-C", str(config_path.parent), "--print-config"],
        capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr)


# --------------------------------------------------------------------------- #
# Interview-file rendering (pass 1) and parsing (pass 2)
# --------------------------------------------------------------------------- #
_CONF_BADGE = {
    H.CONF_HIGH: "HIGH", H.CONF_MEDIUM: "MEDIUM",
    H.CONF_LOW: "LOW", H.CONF_OPEN: "OPEN — needs your decision",
}

ANSWERS_BEGIN = "# ===== ANSWERS (edit values to the right of the colon) ====="
ANSWERS_END = "# ===== END ANSWERS ====="

# TEL-01 (v2.4.0 fold): the telemetry section title, shared by the renderer and
# the parser. render_interview emits it unconditionally, so its PRESENCE in an
# interview file dates that file to v2.4.0-or-later - which is exactly the
# discriminator parse_interview_answers needs to tell "this file predates the
# flag" (default it, per the locked back-compat requirement) from "a v2.4.0
# file whose telemetry line was deleted or misspelled" (fail loud, per
# fail-loud-not-silent). Referenced in both places so the two cannot drift.
TELEMETRY_SECTION_TITLE = "Observability / telemetry export"
TELEMETRY_SECTION_MARKER = f"## {TELEMETRY_SECTION_TITLE}"

# DS-01 (v2.5.0): the design-steering section title/marker, twin of
# TELEMETRY_SECTION_MARKER (interview.py:286). render_interview emits the section
# UNCONDITIONALLY (like telemetry), so its PRESENCE dates an interview file to
# v2.5.0+ — the discriminator parse_interview_answers needs to tell "predates the
# flag" (default false) from "a v2.5.0 file whose design line was deleted or
# misspelled" (fail loud). The interactive OFFER is archetype-gated (see
# run_interactive), but the section, the ANSWERS keys, and the flag itself are
# NOT: an operator may hand-set design_steering_enabled: true on any archetype.
DESIGN_SECTION_TITLE = "Design steering"
DESIGN_SECTION_MARKER = f"## {DESIGN_SECTION_TITLE}"

# DS-01 (v2.5.0): the Phase 0 step 6 design-steering question, VERBATIM from the
# protocol doc (Bootstrap-Protocol-v2-5-0.md — the SOLE verbatim source; there is
# no INTERVIEW-WORDING.md in this repo, exactly as for TEL-01). One combined block
# covering BOTH the doc and the optional-skill offer (the protocol doc gives one
# block, not two separate strings). test_interview.py pins this byte-for-byte
# against the protocol doc so the code string and the doc can never drift.
DESIGN_STEERING_QUESTION = (
    """Generate a design steering doc? This writes `design.md` — a short, always-read reference for user-facing work: visual hierarchy, interaction cost, mobile reach, empty/loading states, accessibility floor, and an HONEST-USE-ONLY rule set for pricing and persuasion (no fake countdowns, no fictitious 'was' prices, no guilt-worded dismissals — the dark patterns regulators enforce against). It's guidance the implementer reads on every user-facing task, not a gate. I can also add an optional advisory review skill that checks changes against it at code-review time — it flags, it never blocks. Off by default; enable it now if this project has a user-facing surface, or add it any time later."""
)

# [W-1] The command-execution-location section, third of the same shape as
# TELEMETRY_SECTION_MARKER and DESIGN_SECTION_MARKER. Emitted unconditionally,
# so its PRESENCE dates an interview file to the version that added the key —
# the discriminator parse_interview_answers needs to tell "predates the key"
# (default true, which is exactly the pre-W-1 behavior) from "a current file
# whose line was deleted or misspelled" (fail loud). NOT folded into the
# existing "Project commands" section, because that title appears in older
# renders too and would date nothing.
COMMANDS_CWD_SECTION_TITLE = "Command execution location"
COMMANDS_CWD_SECTION_MARKER = f"## {COMMANDS_CWD_SECTION_TITLE}"

# [W-1] The Phase 2 question, VERBATIM from the protocol doc (the sole verbatim
# source, as for TEL-01 and DS-01). test_interview.py pins this byte-for-byte
# against the protocol doc so the code string and the doc cannot drift.
COMMANDS_CWD_QUESTION = (
    """Do your test, lint, format, typecheck and CI commands run in the directory they are invoked from? Answer yes for anything that runs locally (`pytest -q`, `npm test`, `make ci`) and for container invocations that follow the caller (`docker run -v "$(pwd)":/app ...`). Answer NO if a command reaches its code through a fixed mount — `docker compose exec`, `kubectl exec`, `ssh`, `vagrant ssh`, a devcontainer CLI — because those land in a tree the mount chose, not the one you were standing in. This matters because the implementer subagent works in its own git worktree: if the gates cannot follow it there, they compile and test the main checkout instead, and report green on code that was never built. Answering no makes the installer drop the worktree isolation rather than leave you with a gate that lies."""
)

# [WP1] Five more sections of the same shape as TELEMETRY_SECTION_MARKER, one
# per decision answers_to_config used to hard-code. Each is rendered
# unconditionally, so its marker dates the file: marker present and key
# missing means a deleted or misspelled line (fail loud); marker absent means
# the file predates the key, and the key takes the value earlier versions
# emitted, so an older file keeps meaning what it meant. Unlike the three
# older markers these are matched as WHOLE LINES, so a rationale that happens
# to contain the text cannot date a file.
PRD_PATH_SECTION_TITLE = "PRD location"
SHELL_SECTION_TITLE = "Shell"
CICD_SECTION_TITLE = "CI/CD applicability"
TIEBREAKERS_SECTION_TITLE = "Principle tiebreakers"
HOOKS_SECTION_TITLE = "Hooks"

# Phase 0 step 5, verbatim from the protocol doc. The answer is inverted:
# "no" means cicd_opt_out: true.
CICD_QUESTION = ("Does this project have CI/CD pipelines, or will it "
                 "(within 3 months)?")

# answer key -> (section title, value when the section is absent)
_WP1_KEY_SECTIONS = {
    "prd_path": (PRD_PATH_SECTION_TITLE, DEFAULTS["project"]["prd_path"]),
    "shell": (SHELL_SECTION_TITLE, DEFAULTS["project"]["shell"]),
    "cicd_opt_out": (CICD_SECTION_TITLE, DEFAULTS["project"]["cicd_opt_out"]),
    "principles_tiebreakers": (TIEBREAKERS_SECTION_TITLE, []),
    **{f"hooks_{n}": (HOOKS_SECTION_TITLE, DEFAULTS["hooks"][n])
       for n in HOOK_TOGGLE_NAMES},
}

_TRUE_WORDS = ("true", "1", "yes", "on")
_FALSE_WORDS = ("false", "0", "no", "off")

# SEAM-CONTRACT-v3-0-0.md §7.3 and §8.2 items 1, 2 and 10: an ANSWERS block
# written by Tessera may carry `source:` provenance markers and a
# `targets_seam_version` field, which synthesize accepts by ignoring. They
# stay ignored WITHOUT a warning, so that path's stderr is what it was.
_SEAM_IGNORED_KEYS = frozenset({"source", "targets_seam_version"})


def render_interview(proposal: dict, prd_path: str) -> str:
    p = proposal
    ans = default_answers(p, prd_path=prd_path)
    L: list[str] = []
    w = L.append

    w("# Bootstrap Interview — Proposal for Human Review")
    w("")
    w(f"Source PRD: `{prd_path}`")
    w("")
    w("This file is a **proposal**. Nothing has been written to `.claude/`. "
      "Read each")
    w("decision and its rationale. To accept a proposal, leave its line in "
      "the ANSWERS")
    w("block unchanged. To override, edit the value after the colon. Then run:")
    w("")
    w("    bin/bootstrap-interview synthesize")
    w("")
    w("which emits `bootstrap.config.yaml` and validates it with "
      "`bootstrap-install")
    w("--print-config` before finishing.")
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
        ("_Alternatives considered:_ "
         + ", ".join(p["archetype"]["alternatives"])
         if p["archetype"].get("alternatives") else ""),
    ])
    section(f"PRD tier (floor for this archetype: "
            f"`{p['prd_tier']['floor']}`)", [
        f"**Proposed:** `{p['prd_tier']['value']}`  "
        f"_(confidence: {_CONF_BADGE[p['prd_tier']['confidence']]})_",
        "",
        p["prd_tier"]["rationale"],
        "",
        "_You may raise the tier but not lower it below the floor "
        "(Bootstrap-Protocol-v2-0-0.md Phase 0)._",
    ])
    # [WP1] The three Phase 0 fields answers_to_config used to hard-code.
    section(PRD_PATH_SECTION_TITLE, [
        f"**Proposed:** `{ans['prd_path']}` (the PRD this interview read)",
        "",
        "Recorded as `project.prd_path`: product.md cites it and the state "
        "file stores it. The installer does not copy or move the PRD.",
    ])
    section(SHELL_SECTION_TITLE, [
        f"**Proposed:** `{ans['shell']}`",
        "",
        "Recorded as `project.shell` in tech.md. It does not change how the "
        "hooks run: every emitted hook is a bash script.",
    ])
    section(CICD_SECTION_TITLE, [
        "**Proposed:** `cicd_opt_out = false` (the project has CI/CD, or "
        "will)",
        "",
        f"\"{CICD_QUESTION}\" If the answer is no, set `cicd_opt_out: true`. "
        "ci-cd.md then records \"No CI/CD\" as the decision, and the "
        "ci-mirror hook is not installed.",
    ])

    pr = p["principles"]
    pl = [
        f"**Starter set ('{p['archetype']['value']}', from "
        f"lib/defaults.PRINCIPLE_STARTERS):**",
    ]
    for i, s in enumerate(pr["starter_set"], 1):
        pl.append(f"  {i}. {s}")
    if pr["proposed_additions"]:
        pl.append("")
        pl.append("**Proposed additions (PRD-justified — for your ranking):**")
        for a in pr["proposed_additions"]:
            pl.append(f"  - {a['principle']}  — _{a['rationale']}_")
    pl += ["", pr["rationale"]]
    section("Principles", pl)
    section(TIEBREAKERS_SECTION_TITLE, [
        "**Proposed:** none. The tool does not guess which principles are in "
        "tension; principles.md shows a placeholder until you add one.",
        "",
        "Add one `  - ` line per tiebreaker under `principles_tiebreakers`, "
        "for example `  - DRY vs YAGNI: prefer YAGNI until the third "
        "duplication` (Phase 4 step 5).",
    ])

    section("TDD policy", [
        f"**Proposed:** `{p['tdd_policy']['value']}`  "
        f"_(confidence: {_CONF_BADGE[p['tdd_policy']['confidence']]})_",
        "",
        p["tdd_policy"]["rationale"],
    ])
    section("Secrets policy", [
        f"**Proposed:** enabled = `{str(p['secrets']['enabled']).lower()}`  "
        f"_(confidence: {_CONF_BADGE[p['secrets']['confidence']]})_",
        "",
        p["secrets"]["rationale"],
    ])
    section("Dependency policy", [
        f"**Proposed:** enabled = `{str(p['deps']['enabled']).lower()}`  "
        f"_(confidence: {_CONF_BADGE[p['deps']['confidence']]})_",
        "",
        p["deps"]["rationale"],
    ])
    am = p["autonomous_modes"]
    section("Autonomous modes (scaffold-only)", [
        "**Proposed:** all OFF "
        f"_(confidence: {_CONF_BADGE[am['confidence']]})_",
        "",
        am["rationale"],
        "",
        "_These modes ship as UNIMPLEMENTED skeletons: enabling one emits a "
        "wrapper that dispatches nothing (exits 1) until you complete the "
        "dispatch loop (Bootstrap-Protocol-v2-0-0.md Phase 9.5/9.6/9.7)._",
        "",
        "_Constraint: queue mode requires loop or goal mode "
        "(Bootstrap-Protocol-v2-0-0.md Phase 9.7). The tool will not emit an invalid combo._",
    ])
    # TEL-01 (v2.4.0 fold): standalone opt-in decision, independent of every
    # autonomous mode. Question phrasing is the PRD's verbatim text
    # (Bootstrap-Protocol-v2-4-0.md, "Enable observability export?"). Set
    # telemetry_export_enabled in the ANSWERS block below.
    section(TELEMETRY_SECTION_TITLE, [
        "**Proposed:** `telemetry_export_enabled = false` (default skip; "
        "opt-in only, independent of every autonomous mode)",
        "",
        "\"Enable observability export? This writes a steering doc, "
        "`telemetry.md`, that documents Claude Code's own opt-in "
        "OpenTelemetry surface and points it at a backend you run. It's how "
        "you'd later see whether the gates, drift thresholds, and autonomous "
        "loops are behaving — gate fire rates, compaction behavior, "
        "infra-failure rates, and per-subagent token usage — as trends over "
        "time. Nothing is sent anywhere the protocol chooses: export goes "
        "only to the OTLP endpoint you configure, never to Anthropic and "
        "never to the Bootstrap maintainers, and prompts, tool arguments, "
        "file contents, and API bodies stay redacted unless you deliberately "
        "turn them on against your own backend. Off by default; you can "
        "enable it any time later.\"",
    ])
    # DS-01 (v2.5.0): emitted UNCONDITIONALLY (like the telemetry section) so the
    # DESIGN_SECTION_MARKER dates any v2.5.0+ interview file — the discriminator
    # parse_interview_answers uses to distinguish a pre-2.5.0 file (default the
    # flags false) from a v2.5.0 file whose design line was deleted (fail loud).
    # The offer is archetype-gated interactively, but the flag is accepted for
    # any archetype an operator hand-sets in the ANSWERS block below. Question
    # text is the protocol doc's verbatim Phase 0 step 6 string (single source).
    section(DESIGN_SECTION_TITLE, [
        "**Proposed:** `design_steering_enabled = false` (default skip; opt-in "
        "only, independent of every autonomous mode; the optional "
        "`design_review_skill_enabled` is a second decision, gated on this one)",
        "",
        f"\"{DESIGN_STEERING_QUESTION}\"",
    ])
    section("Project commands — HUMAN-REQUIRED (left empty by design)", [
        "`commands.test`, `commands.lint`, `commands.format`, "
        "`commands.typecheck`, `commands.ci_local`",
        "",
        "A PRD does not contain these. They are emitted **empty** (see "
        "README 'Honest limitations'). An empty test "
        "command makes `test-gate` block every commit; an empty lint "
        "command means `format-lint-gate` checks nothing; no hook runs "
        "format or typecheck. Fill them in the ANSWERS block only if you "
        "actually know them; otherwise leave empty and complete them before "
        "relying on the gates.",
    ])
    # [W-1] Emitted UNCONDITIONALLY (like telemetry and design), so
    # COMMANDS_CWD_SECTION_MARKER dates any interview file that carries it —
    # the discriminator parse_interview_answers uses to distinguish a file
    # predating the key (default true) from a current file whose line was
    # deleted (fail loud). Question text is the protocol doc's verbatim
    # Phase 2 string (single source).
    section(COMMANDS_CWD_SECTION_TITLE, [
        "**Proposed:** `commands_execute_in_cwd = true` (the common case, and "
        "the pre-existing behavior; set it false only for fixed-mount "
        "indirection)",
        "",
        f"\"{COMMANDS_CWD_QUESTION}\"",
    ])
    # [WP1] Phase 6: one toggle per hook (see HOOK_TOGGLES). Rendered
    # unconditionally so the marker dates the file (see _WP1_KEY_SECTIONS).
    hl = [
        "**Proposed:** the installer's standard set for this archetype and "
        "TDD policy.",
        "",
        "Each `hooks_<name>` line in the ANSWERS block switches one hook: "
        "`true` installs it and `false` leaves it out. `hooks_tdd_gate` and "
        "`hooks_eval_gate` also take `auto`. The secrets gate and the "
        "dependency gate have no line here: `secrets_enabled` and "
        "`deps_enabled` switch them, and false removes that policy's gate.",
        "",
    ]
    for name, desc in HOOK_TOGGLES:
        hl.append(f"- `hooks_{name}`: {desc}.")
    section(HOOKS_SECTION_TITLE, hl)

    if p["open_questions"]:
        w("## ⚠ OPEN QUESTIONS — these were too ambiguous to propose")
        w("")
        w("The tool deliberately did **not** decide these. Resolve each by "
          "setting the")
        w("corresponding ANSWERS line.")
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
    w("# List values (principles_ranked, principles_tiebreakers,")
    w("# secrets_never_read_paths) are written one item per line as")
    w("# '  - item' so an item may safely contain commas; edit/add/remove")
    w("# '  - ' lines under the key.")
    for k in ANSWER_KEYS:
        v = ans[k]
        if v is None:
            # [WP1] only the two tri-state hook toggles are ever None.
            w(f"{k}: auto")
        elif isinstance(v, list):
            # one item per indented '- ' line: no in-band delimiter, so a
            # principle containing a comma round-trips intact (finding R-3).
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


def parse_interview_answers(text: str, warnings: list | None = None) -> dict:
    """Extract the ANSWERS block back into a typed answers dict.

    [WP1] A line the parser cannot use is no longer dropped silently: an
    unknown key, a repeated key, a stray list item, a line with no colon and
    an unreadable pre-WP1 boolean each append one message to `warnings` (the
    same sink pattern as configemit.emit). The WP1 keys are strict instead:
    an unreadable value raises, since no older file can carry one.
    """
    sink: list = warnings if warnings is not None else []
    lines = text.splitlines()
    try:
        i0 = lines.index(ANSWERS_BEGIN)
        i1 = lines.index(ANSWERS_END)
    except ValueError:
        raise ValueError(
            "interview file is missing the ANSWERS block; regenerate with "
            "`bin/bootstrap-interview analyze`")
    bool_keys = {
        "secrets_enabled", "deps_enabled", "loop_mode_enabled",
        "goal_supervised_mode_enabled", "queue_mode_enabled",
        "telemetry_export_enabled",
        # DS-01 (v2.5.0): twin top-level opt-in flags.
        "design_steering_enabled", "design_review_skill_enabled",
        # [W-1] the command-execution-location fact.
        "commands_execute_in_cwd",
        # [WP1]
        "cicd_opt_out",
        *(f"hooks_{n}" for n in HOOK_TOGGLE_NAMES if n not in HOOK_TRISTATE),
    }
    tristate_keys = {f"hooks_{n}" for n in HOOK_TRISTATE}
    list_keys = {"principles_ranked", "secrets_never_read_paths",
                 "principles_tiebreakers"}
    known = set(ANSWER_KEYS)

    raw: dict[str, str] = {}
    raw_line: dict[str, int] = {}
    list_raw: dict[str, list[str]] = {}
    first_seen: dict[str, int] = {}
    body = lines[i0 + 1:i1]
    cur_list_key: str | None = None
    last_key: str | None = None
    for lineno, line in enumerate(body, start=i0 + 2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # A '- item' continuation line belongs to the most recent list key.
        if stripped.startswith("- ") or stripped == "-":
            if cur_list_key is not None:
                item = stripped[1:].strip()
                if item:
                    list_raw.setdefault(cur_list_key, []).append(item)
            else:
                if last_key is None:
                    why = "no key comes before it"
                elif last_key not in known:
                    why = f"it belongs to the unknown key '{last_key}'"
                elif last_key in list_keys:
                    why = (f"'{last_key}' already has a value on its own "
                           "line; put every item on a '  - ' line instead")
                else:
                    why = f"'{last_key}' takes a single value"
                sink.append(f"line {lineno}: list item {stripped!r} "
                            f"ignored: {why}.")
            continue
        if ":" not in stripped:
            sink.append(f"line {lineno}: {stripped!r} ignored: not a "
                        "'key: value' line.")
            continue
        k, _, v = stripped.partition(":")
        k = k.strip()
        v = v.strip()
        last_key = k
        if k in _SEAM_IGNORED_KEYS:
            cur_list_key = None
            continue
        if k not in known:
            cur_list_key = None
            msg = f"line {lineno}: unknown key '{k}' ignored."
            hint = difflib.get_close_matches(k, ANSWER_KEYS, n=1)
            if hint:
                msg += f" Did you mean '{hint[0]}'?"
            sink.append(msg)
            continue
        if k in first_seen:
            sink.append(
                f"line {lineno}: '{k}' appears again (first on line "
                f"{first_seen[k]}); "
                + ("the items under both are kept." if k in list_keys
                   else "this later value is the one used."))
        else:
            first_seen[k] = lineno
        if k in list_keys and v == "":
            # one-item-per-line form: items follow on '- ' lines.
            cur_list_key = k
            list_raw.setdefault(k, [])
        else:
            cur_list_key = None
            raw[k] = v
            raw_line[k] = lineno

    out: dict = {}
    for k in ANSWER_KEYS:
        if k in list_keys:
            if k in list_raw:
                # canonical one-per-line form (commas inside items preserved)
                out[k] = [x.strip() for x in list_raw[k] if x.strip()]
                continue
            if k in raw:
                if k == "principles_tiebreakers":
                    # [WP1] No legacy comma form to honour, and a tiebreaker
                    # sentence often has a comma: an inline value is ONE item.
                    out[k] = [raw[k]] if raw[k] else []
                    continue
                # legacy inline 'key: a, b, c' form (back-compat)
                out[k] = [x.strip() for x in raw[k].split(",") if x.strip()]
                continue
            if k in _WP1_KEY_SECTIONS:
                out[k] = _wp1_absent(k, lines)
                continue
            raise ValueError(f"ANSWERS block missing key: {k}")
        if k not in raw:
            if k in _WP1_KEY_SECTIONS:
                out[k] = _wp1_absent(k, lines)
                continue
            # TEL-01 (v2.4.0 fold): back-compat — a pre-2.4.0 ANSWERS block has
            # no telemetry line, and rejecting an otherwise-valid older
            # interview file is not acceptable. But an unconditional exemption
            # would also swallow a DELETED or MISSPELLED key in a freshly
            # rendered v2.4.0 file, silently resolving an opt-in the operator
            # believes they enabled to false. Discriminate on the telemetry
            # section marker, which only a v2.4.0+ render carries: present =>
            # the key belongs here and its absence is an error worth failing
            # loud on; absent => genuinely pre-2.4.0, default to skip.
            if k == "telemetry_export_enabled":
                if TELEMETRY_SECTION_MARKER not in text:
                    out[k] = False
                    continue
                raise ValueError(
                    "ANSWERS block missing key: telemetry_export_enabled. "
                    "This interview file carries the "
                    f"'{TELEMETRY_SECTION_TITLE}' section, so it was rendered "
                    "by v2.4.0 or later and the key was deleted or "
                    "misspelled rather than predating the flag. Restore "
                    "`telemetry_export_enabled: true` or `: false` — an "
                    "opt-in decision is never defaulted silently.")
            # DS-01 (v2.5.0): same section-marker discriminator as telemetry.
            # A pre-2.5.0 ANSWERS block carries no design section => default the
            # flag false (never reject a valid older file). A v2.5.0 file DOES
            # carry the marker, so a missing key there is a deleted/misspelled
            # opt-in and fails loud rather than resolving silently. Both design
            # keys share the one marker (the section renders both).
            if k in ("design_steering_enabled",
                     "design_review_skill_enabled"):
                if DESIGN_SECTION_MARKER not in text:
                    out[k] = False
                    continue
                raise ValueError(
                    f"ANSWERS block missing key: {k}. This interview file "
                    f"carries the '{DESIGN_SECTION_TITLE}' section, so it was "
                    "rendered by v2.5.0 or later and the key was deleted or "
                    "misspelled rather than predating the flag. Restore "
                    f"`{k}: true` or `: false` — an opt-in decision is never "
                    "defaulted silently.")
            # [W-1] Same section-marker discriminator. Note the defaulted value
            # here is TRUE, unlike the two opt-ins above: true reproduces the
            # behavior every pre-W-1 interview file was written under, so an
            # older file keeps meaning exactly what it meant. A CURRENT file
            # missing the line still fails loud — the value decides whether a
            # verification gate can see the code it is verifying.
            if k == "commands_execute_in_cwd":
                if COMMANDS_CWD_SECTION_MARKER not in text:
                    out[k] = True
                    continue
                raise ValueError(
                    f"ANSWERS block missing key: {k}. This interview file "
                    f"carries the '{COMMANDS_CWD_SECTION_TITLE}' section, so "
                    "the key was deleted or misspelled rather than predating "
                    f"it. Restore `{k}: true` or `: false` — it decides "
                    "whether the implementer gets `isolation: worktree`, and "
                    "guessing it wrong makes a gate pass on code it never "
                    "compiled.")
            raise ValueError(f"ANSWERS block missing key: {k}")
        val = raw[k]
        word = val.strip().lower()
        if k in tristate_keys:
            if word == "auto":
                out[k] = None
            elif word in _TRUE_WORDS or word in _FALSE_WORDS:
                out[k] = word in _TRUE_WORDS
            else:
                raise ValueError(
                    f"{k}: {val!r} is not auto, true or false.")
        elif k in bool_keys:
            if word not in _TRUE_WORDS and word not in _FALSE_WORDS:
                if k in _WP1_KEY_SECTIONS:
                    raise ValueError(f"{k}: {val!r} is not true or false.")
                if k in POLICY_ANSWER_KEYS:
                    # [WP1 D3] false removes a security gate, so a typo here
                    # is refused, never read as false.
                    raise ValueError(
                        f"line {raw_line[k]}: {k}: {val!r} is not true or "
                        f"false. It switches {POLICY_ANSWER_KEYS[k]}, and "
                        "false removes it, so a value that is neither is "
                        "refused rather than read as false.")
                # Pre-WP1 key: keep reading it as false, as every earlier
                # version did, but say so.
                sink.append(f"{k}: {val!r} is not true or false; read as "
                            "false.")
            out[k] = word in _TRUE_WORDS
        else:
            out[k] = val
    return out


def _wp1_absent(k: str, lines: list[str]):
    """[WP1] The value of a WP1 key the ANSWERS block lacks: the value earlier
    versions emitted if the file predates the key's section, else an error."""
    title, legacy = _WP1_KEY_SECTIONS[k]
    if f"## {title}" not in lines:
        return list(legacy) if isinstance(legacy, list) else legacy
    raise ValueError(
        f"ANSWERS block missing key: {k}. This interview file carries the "
        f"'{title}' section, so the key was deleted or misspelled rather "
        f"than predating it. Restore the `{k}:` line; the tool does not "
        "default a decision the file shows it asked.")


# --------------------------------------------------------------------------- #
# Interactive front-end (non-deterministic by design; same core)
# --------------------------------------------------------------------------- #
class _EOF:
    """Sticky end-of-input flag shared across prompts in one interview.

    Once stdin is exhausted, every subsequent `_ask` returns its default and
    sets `.hit`. Validated loops check this so they fall back to a known-good
    value instead of re-prompting an exhausted stream forever (review finding
    I-1: a validated loop whose proposed default is itself invalid - e.g. the
    PRD-tier default after an archetype override raises the floor above it -
    would otherwise spin infinitely on piped/scripted stdin).
    """

    def __init__(self) -> None:
        self.hit = False


def _ask(prompt: str, default: str, *, instream, outstream,
         eof: "_EOF | None" = None) -> str:
    outstream.write(prompt + f"\n  [default: {default}] > ")
    outstream.flush()
    line = instream.readline()
    if line == "":  # EOF
        if eof is not None:
            eof.hit = True
        return default
    line = line.strip()
    return line if line else default


def run_interactive(prd_text: str, *, instream, outstream,
                     project_fallback: str = "my-project",
                     use_llm: bool = False,
                     prd_path: str | None = None) -> dict:
    """Prompt the human one decision at a time over stdin; return answers.

    Equivalent to editing the questionnaire: every prompt shows the proposal
    and rationale; empty input accepts it. OPEN QUESTIONs are asked as
    sequential prompts (never batched). commands.* are explicitly NOT
    prompted as guessable - the human may optionally supply them, with the
    consequence of leaving them empty stated.
    """
    p = build_proposal(prd_text, project_fallback=project_fallback,
                        use_llm=use_llm)
    ans = default_answers(p, prd_path=prd_path)
    o = outstream.write
    eof = _EOF()  # shared sticky end-of-input flag (review finding I-1)

    o("\n=== Bootstrap interview (interactive) ===\n")
    o("Each decision below is a PROPOSAL with a rationale. Press Enter to "
      "accept it,\nor type an override. Nothing is written until you confirm "
      "at the end.\n\n")
    for n in p.get("_llm", {}).get("notices", []):
        o(f"  ! {n}\n")

    def show(title, rationale):
        o(f"\n--- {title} ---\n{rationale}\n")

    show("Project name", p["project_name"]["rationale"])
    ans["project_name"] = _ask("Project name", ans["project_name"],
                                instream=instream, outstream=outstream,
                                eof=eof)

    show("Archetype "
         f"(confidence {p['archetype']['confidence']})",
         p["archetype"]["rationale"])
    while True:
        v = _ask(f"Archetype {sorted(__import__('defaults').ARCHETYPES)}",
                 ans["archetype"], instream=instream, outstream=outstream,
                 eof=eof)
        if v in __import__("defaults").ARCHETYPES:
            ans["archetype"] = v
            break
        if eof.hit:
            # stdin exhausted: the proposed default is always a valid
            # archetype (prd_heuristics never proposes an out-of-set value),
            # so accept it rather than re-prompt a dead stream forever.
            ans["archetype"] = (ans["archetype"]
                                if ans["archetype"]
                                in __import__("defaults").ARCHETYPES
                                else "other")
            o(f"  (end of input; accepting '{ans['archetype']}')\n")
            break
        o(f"  '{v}' is not a valid archetype; try again.\n")

    # tier may have moved if archetype was overridden
    floor = H.ARCHETYPE_REQUIRED_TIER.get(ans["archetype"], "standard")
    show(f"PRD tier (floor '{floor}')", p["prd_tier"]["rationale"])
    while True:
        v = _ask("PRD tier micro|standard|full", ans["prd_tier"],
                 instream=instream, outstream=outstream, eof=eof)
        if v in H.TIER_ORDER and H.TIER_ORDER[v] >= H.TIER_ORDER[floor]:
            ans["prd_tier"] = v
            break
        if eof.hit:
            # stdin exhausted. The proposed default can be BELOW the floor
            # if the human overrode the archetype upward (review finding
            # I-1); clamp UP to the floor rather than spin forever. Never
            # below the floor (Bootstrap-Protocol-v2-0-0.md Phase 0: higher allowed, lower
            # never).
            cur = H.TIER_ORDER.get(v if v in H.TIER_ORDER
                                   else ans["prd_tier"], -1)
            chosen = v if cur >= H.TIER_ORDER[floor] else floor
            ans["prd_tier"] = chosen
            o(f"  (end of input; clamping PRD tier to floor "
              f"'{ans['prd_tier']}')\n")
            break
        o(f"  must be one of micro|standard|full and >= floor '{floor}'.\n")

    # [WP1] The Phase 0 fields answers_to_config used to hard-code.
    show(PRD_PATH_SECTION_TITLE,
         "Recorded as project.prd_path (product.md and the state file). "
         "Relative to the project root.")
    ans["prd_path"] = _ask("PRD path", ans["prd_path"], instream=instream,
                           outstream=outstream, eof=eof)
    show(SHELL_SECTION_TITLE,
         "Recorded in tech.md. Every emitted hook is a bash script "
         "whatever this says.")
    ans["shell"] = _ask("Shell", ans["shell"], instream=instream,
                        outstream=outstream, eof=eof)
    show(CICD_SECTION_TITLE,
         "If no, ci-cd.md records \"No CI/CD\" and the ci-mirror hook is not "
         "installed.")
    while True:
        v = _ask(f"{CICD_QUESTION} yes|no",
                 "no" if ans["cicd_opt_out"] else "yes",
                 instream=instream, outstream=outstream, eof=eof)
        word = v.strip().lower()
        if word in _TRUE_WORDS or word in _FALSE_WORDS:
            ans["cicd_opt_out"] = word in _FALSE_WORDS
            break
        if eof.hit:
            o("  (end of input; keeping the proposal)\n")
            break
        o("  must be yes or no.\n")

    show("Principles", p["principles"]["rationale"])
    o("  Proposed ranked set:\n")
    for i, s in enumerate(ans["principles_ranked"], 1):
        o(f"    {i}. {s}\n")
    v = _ask("Principles (comma-separated, in rank order)",
             "; ".join(ans["principles_ranked"]),
             instream=instream, outstream=outstream, eof=eof)
    ans["principles_ranked"] = [x.strip() for x in v.replace(";", ",").split(",")
                                if x.strip()]
    # [WP1] Phase 4 step 5. Split on ';' only: a tiebreaker sentence often
    # carries a comma ("DRY vs YAGNI: prefer YAGNI, until ...").
    show(TIEBREAKERS_SECTION_TITLE,
         "Optional. Name principles in tension and which wins, for example "
         "\"DRY vs YAGNI: prefer YAGNI until the third duplication\".")
    v = _ask("Tiebreakers (separate with ';', empty for none)",
             "; ".join(ans["principles_tiebreakers"]),
             instream=instream, outstream=outstream, eof=eof)
    ans["principles_tiebreakers"] = [x.strip() for x in v.split(";")
                                     if x.strip()]

    show("TDD policy", p["tdd_policy"]["rationale"])
    while True:
        v = _ask("TDD policy off|encouraged|required", ans["tdd_policy"],
                 instream=instream, outstream=outstream, eof=eof)
        if v in ("off", "encouraged", "required"):
            ans["tdd_policy"] = v
            break
        if eof.hit:
            # proposed TDD default is always one of the valid three.
            ans["tdd_policy"] = (ans["tdd_policy"]
                                 if ans["tdd_policy"]
                                 in ("off", "encouraged", "required")
                                 else "encouraged")
            o(f"  (end of input; accepting '{ans['tdd_policy']}')\n")
            break
        o("  must be off|encouraged|required.\n")

    def ask_policy(key, prompt):
        # [WP1 D3, review RR4] false removes a security gate, so a reply
        # that is not a clear yes or no is asked again, as the CI/CD prompt
        # does, instead of being read as false. The ANSWERS parser refuses
        # the same replies (POLICY_ANSWER_KEYS).
        while True:
            v = _ask(prompt, str(ans[key]).lower(), instream=instream,
                     outstream=outstream, eof=eof)
            word = v.strip().lower()
            if word in _TRUE_WORDS or word in _FALSE_WORDS:
                ans[key] = word in _TRUE_WORDS
                return
            if eof.hit:
                o("  (end of input; keeping the proposal)\n")
                return
            o(f"  must be true or false (yes or no); false removes "
              f"{POLICY_ANSWER_KEYS[key]}.\n")

    show("Secrets policy", p["secrets"]["rationale"])
    ask_policy("secrets_enabled", "Secrets enabled? true|false")
    v = _ask("Never-read globs (comma-separated)",
             ", ".join(ans["secrets_never_read_paths"]),
             instream=instream, outstream=outstream, eof=eof)
    ans["secrets_never_read_paths"] = [x.strip() for x in v.split(",")
                                       if x.strip()]

    show("Dependency policy", p["deps"]["rationale"])
    ask_policy("deps_enabled", "Deps policy enabled? true|false")

    show("Autonomous modes", p["autonomous_modes"]["rationale"])
    for mk, label in (("loop_mode_enabled", "Loop mode (scaffold-only)"),
                      ("goal_supervised_mode_enabled",
                       "Goal-supervised mode (scaffold-only)"),
                      ("queue_mode_enabled", "Queue mode (scaffold-only)")):
        v = _ask(f"{label} enabled? true|false",
                 str(ans[mk]).lower(),
                 instream=instream, outstream=outstream, eof=eof)
        ans[mk] = v.lower() in ("true", "1", "yes", "on")
    # Enforce the skip-policy invariant interactively rather than emit invalid.
    if ans["queue_mode_enabled"] and not (
            ans["loop_mode_enabled"] or ans["goal_supervised_mode_enabled"]):
        o("\n  ! Queue mode requires loop or goal mode (Bootstrap-Protocol-v2-0-0.md 9.7). "
          "Disabling queue mode.\n")
        ans["queue_mode_enabled"] = False

    # TEL-01 (v2.4.0 fold): standalone opt-in, independent of the autonomous
    # modes. Verbatim PRD question text (Bootstrap-Protocol-v2-4-0.md).
    show("Observability / telemetry export",
         "Enable observability export? This writes a steering doc, "
         "telemetry.md, that documents Claude Code's own opt-in OpenTelemetry "
         "surface and points it at a backend you run. It's how you'd later "
         "see whether the gates, drift thresholds, and autonomous loops are "
         "behaving — gate fire rates, compaction behavior, infra-failure "
         "rates, and per-subagent token usage — as trends over time. Nothing "
         "is sent anywhere the protocol chooses: export goes only to the OTLP "
         "endpoint you configure, never to Anthropic and never to the "
         "Bootstrap maintainers, and prompts, tool arguments, file contents, "
         "and API bodies stay redacted unless you deliberately turn them on "
         "against your own backend. Off by default; you can enable it any "
         "time later.")
    v = _ask("Telemetry export enabled? true|false",
             str(ans["telemetry_export_enabled"]).lower(),
             instream=instream, outstream=outstream, eof=eof)
    ans["telemetry_export_enabled"] = v.lower() in ("true", "1", "yes", "on")

    # DS-01 (v2.5.0): the archetype-GATED offer — the ONE site with no telemetry
    # twin. Telemetry is asked unconditionally; design steering is offered only
    # for user-facing archetypes. Excluded archetypes (cli, library, service,
    # data-ml) record false WITHOUT prompting (interview stays short). NB: the
    # flag is NOT gated — an operator hand-setting design_steering_enabled: true
    # in the ANSWERS block on any archetype still emits design.md (build_plan
    # does no archetype check); only this interactive prompt is gated. show()
    # takes (title, rationale) [verified :679]; _ask passes stream args BY
    # KEYWORD [verified :623]. ans["archetype"] is a validated archetype string
    # by this point. The rationale is the protocol doc's VERBATIM Phase 0 step 6
    # question (one combined block covering the doc + the skill offer), so no
    # separate verbatim follow-up string exists; the skill _ask uses a plain
    # functional prompt.
    _DESIGN_OFFER_ARCHETYPES = {"fullstack", "mobile", "ai-agent",
                                "platform", "other"}
    if ans["archetype"] in _DESIGN_OFFER_ARCHETYPES:
        show(DESIGN_SECTION_TITLE, DESIGN_STEERING_QUESTION)
        v = _ask("Generate design steering doc? true|false",
                 str(ans["design_steering_enabled"]).lower(),
                 instream=instream, outstream=outstream, eof=eof)
        ans["design_steering_enabled"] = v.lower() in ("true", "1", "yes", "on")
        if ans["design_steering_enabled"]:
            v2 = _ask("Add the optional advisory design-review skill? "
                      "true|false",
                      str(ans["design_review_skill_enabled"]).lower(),
                      instream=instream, outstream=outstream, eof=eof)
            ans["design_review_skill_enabled"] = \
                v2.lower() in ("true", "1", "yes", "on")
    # else: both flags stay at their False default, no prompt shown.

    o("\n--- Project commands (HUMAN-REQUIRED) ---\n"
      "A PRD cannot supply these. An empty test blocks every commit; an\n"
      "empty lint checks nothing. Leave empty unless you truly know them "
      "now.\n")
    for ck, label in (("commands_test", "test"), ("commands_lint", "lint"),
                      ("commands_format", "format"),
                      ("commands_typecheck", "typecheck"),
                      ("commands_ci_local", "ci_local")):
        ans[ck] = _ask(f"commands.{label}", ans[ck],
                       instream=instream, outstream=outstream, eof=eof)

    # [W-1] Asked UNCONDITIONALLY, right after the commands themselves — it is
    # a fact about those five answers and belongs next to them. Not
    # archetype-gated: fixed-mount dev environments show up under every
    # archetype, which is precisely why the pairing went unnoticed.
    show(COMMANDS_CWD_SECTION_TITLE, COMMANDS_CWD_QUESTION)
    v = _ask("Do these commands run in the directory they are invoked from? "
             "true|false",
             str(ans["commands_execute_in_cwd"]).lower(),
             instream=instream, outstream=outstream, eof=eof)
    ans["commands_execute_in_cwd"] = v.lower() in ("true", "1", "yes", "on")

    # [WP1] Phase 6. One prompt, not thirteen: name the hooks to leave out.
    # Forcing tdd_gate or eval_gate ON stays an ANSWERS-block edit; here they
    # keep `auto` unless named.
    show(HOOKS_SECTION_TITLE,
         "The installer's standard set is proposed. "
         "The secrets and dependency gates are not listed: "
         "secrets_enabled and deps_enabled switch them.\n"
         + "\n".join(f"  {n}: {d}" for n, d in HOOK_TOGGLES))
    while True:
        v = _ask("Hooks to leave out (comma-separated names, empty for none)",
                 "", instream=instream, outstream=outstream, eof=eof)
        names = [x.strip() for x in v.split(",") if x.strip()]
        bad = [x for x in names if x not in HOOK_TOGGLE_NAMES]
        if not bad:
            for x in names:
                ans[f"hooks_{x}"] = False
            break
        if eof.hit:
            o("  (end of input; keeping every proposed hook)\n")
            break
        o(f"  unknown hook name(s): {', '.join(bad)}.\n")

    return ans


# --------------------------------------------------------------------------- #
# Orchestration helpers
# --------------------------------------------------------------------------- #
def _finalize(answers: dict, out_path: Path, *, outstream) -> int:
    """answers -> config dict -> in-process validate -> write -> installer
    validate. Refuses to leave an invalid config in place."""
    cfg = answers_to_config(answers)
    errs = validate_config_dict(cfg)
    if errs:
        outstream.write("\nConfig did NOT validate (resolve_config):\n")
        for e in errs:
            outstream.write(f"  - {e}\n")
        outstream.write("No file written. Resolve the above and re-run.\n")
        return 2

    header = ("GENERATED BY bin/bootstrap-interview — a PROPOSAL reviewed by a "
              "human.\nEvery value here was shown with a rationale before "
              "acceptance.\nempty commands.test/lint/format are intentional: "
              "the installer warns about each one.\nRe-run "
              "bin/bootstrap-install --dry-run to preview the .claude/ tree.")
    emit_warnings: list[str] = []
    out_path.write_text(emit(cfg, header=header, warnings=emit_warnings))
    for w in emit_warnings:
        outstream.write(f"\n  ! sanitized {w}\n")

    rc, output = validate_with_installer(out_path)
    if rc != 0:
        outstream.write(
            "\nWrote config but `bootstrap-install --print-config` REJECTED "
            f"it:\n{output}\n"
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
        prog="bootstrap-interview",
        description="Decision-layer interview: read a PRD and PROPOSE a "
                    "bootstrap.config.yaml for human approval. Never decides "
                    "silently; never guesses project commands.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", help="PRD -> bootstrap.interview.md")
    a.add_argument("--prd", required=True)
    a.add_argument("-o", "--out", default=INTERVIEW_DEFAULT)
    a.add_argument("--llm", action="store_true",
                   help="OPT-IN: use a model to refine the proposal instead "
                        "of keyword heuristics (non-deterministic; degrades "
                        "loudly to heuristics if no model is reachable). Also "
                        "enabled by BOOTSTRAP_INTERVIEW_LLM=1.")

    s = sub.add_parser("synthesize",
                        help="bootstrap.interview.md -> bootstrap.config.yaml")
    s.add_argument("-i", "--interview", default=INTERVIEW_DEFAULT)
    s.add_argument("-o", "--out", default=CONFIG_DEFAULT)
    s.add_argument("--validate-only", action="store_true",
                   help="IC-1: parse the interview, run the resolve_config "
                        "invariants, report violations to stderr, and write "
                        "NO output file. Exit 0 = valid, non-zero = invalid.")

    it = sub.add_parser("interactive",
                        help="PRD -> live stdin Q&A -> bootstrap.config.yaml")
    it.add_argument("--prd", required=True)
    it.add_argument("-o", "--out", default=CONFIG_DEFAULT)
    it.add_argument("--llm", action="store_true",
                    help="OPT-IN: use a model to refine the proposals "
                         "(see `analyze --llm`).")

    args = ap.parse_args(argv)

    if args.cmd == "analyze":
        prd = Path(args.prd)
        if not prd.exists():
            print(f"error: PRD not found: {prd}", file=sys.stderr)
            return 2
        use_llm = LLM.llm_requested(getattr(args, "llm", False))
        proposal = build_proposal(
            prd.read_text(), project_fallback=prd.stem or "my-project",
            use_llm=use_llm)
        Path(args.out).write_text(render_interview(
            proposal, _config_prd_path(prd, Path(args.out))))
        for n in proposal.get("_llm", {}).get("notices", []):
            print(f"  ! {n}")
        n_oq = len(proposal["open_questions"])
        print(f"Wrote {args.out} "
              f"({n_oq} open question(s) need your decision).")
        print("Edit the ANSWERS block, then run: "
              "bin/bootstrap-interview synthesize")
        return 0

    if args.cmd == "synthesize":
        ip = Path(args.interview)
        if not ip.exists():
            print(f"error: interview file not found: {ip}", file=sys.stderr)
            print("Run `bin/bootstrap-interview analyze --prd <PRD>` first.",
                  file=sys.stderr)
            return 2
        parse_warnings: list[str] = []
        try:
            answers = parse_interview_answers(ip.read_text(),
                                              warnings=parse_warnings)
        except ValueError as e:
            print(f"error: {ip}: {e}", file=sys.stderr)
            return 2
        for pw in parse_warnings:
            print(f"warning: {ip}: {pw}", file=sys.stderr)
        if args.validate_only:
            # IC-1: validation only - no file is ever written on this path.
            cfg = answers_to_config(answers)
            errs = validate_config_dict(cfg)
            if errs:
                print("validate-only: config INVALID "
                      "(resolve_config invariant violations):", file=sys.stderr)
                for e in errs:
                    print(f"  - {e}", file=sys.stderr)
                return 2
            print("validate-only: config valid (no file written).")
            return 0
        return _finalize(answers, Path(args.out), outstream=sys.stdout)

    if args.cmd == "interactive":
        prd = Path(args.prd)
        if not prd.exists():
            print(f"error: PRD not found: {prd}", file=sys.stderr)
            return 2
        use_llm = LLM.llm_requested(getattr(args, "llm", False))
        answers = run_interactive(
            prd.read_text(), instream=sys.stdin, outstream=sys.stdout,
            project_fallback=prd.stem or "my-project", use_llm=use_llm,
            prd_path=_config_prd_path(prd, Path(args.out)))
        return _finalize(answers, Path(args.out), outstream=sys.stdout)

    return 2  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

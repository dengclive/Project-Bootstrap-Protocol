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
    HUMAN-REQUIRED, consistent with the installer's loud-TODO gates.
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
import json
import os
import subprocess
import sys
from pathlib import Path

import prd_heuristics as H
import llm_advisor as LLM
from configemit import emit
from defaults import resolve_config
from minyaml import load_yaml

HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "bin" / "bootstrap-install"

INTERVIEW_DEFAULT = "bootstrap.interview.md"
CONFIG_DEFAULT = "bootstrap.config.yaml"

# Keys whose answers the human supplies in the ANSWERS block. Each maps to a
# (section, builder) the synthesize step understands. Order is the order the
# interview file presents them and the order interactive mode prompts them.
ANSWER_KEYS = [
    "project_name",
    "archetype",
    "prd_tier",
    "principles_ranked",
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
    "commands_test",
    "commands_lint",
    "commands_format",
    "commands_typecheck",
    "commands_ci_local",
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


def default_answers(proposal: dict) -> dict:
    """The answer set if the human edits nothing - i.e. accept every
    proposal. Every value here is a conscious proposal with a rationale, so
    this still satisfies 'proposes, never silently decides': the human saw
    each one and chose not to override."""
    p = proposal
    return {
        "project_name": p["project_name"]["value"],
        "archetype": p["archetype"]["value"],
        "prd_tier": p["prd_tier"]["value"],
        "principles_ranked": list(p["principles"]["ranked"]),
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
        # NEVER guessed - emitted empty, flagged HUMAN-REQUIRED.
        "commands_test": "",
        "commands_lint": "",
        "commands_format": "",
        "commands_typecheck": "",
        "commands_ci_local": "",
    }


# --------------------------------------------------------------------------- #
# answers -> config dict (then validated by resolve_config / --print-config)
# --------------------------------------------------------------------------- #
def answers_to_config(ans: dict) -> dict:
    """Assemble a config dict in the schema bootstrap.config.yaml uses.

    We deliberately emit only the fields a human decides; resolve_config
    fills the rest (hook toggles, drift thresholds, etc.) from DEFAULTS.
    """
    paths = ans.get("secrets_never_read_paths") \
        or [".env*", "secrets/**", "*.pem", "*.key"]
    return {
        "project": {
            "name": ans["project_name"],
            "archetype": ans["archetype"],
            "shell": "bash",
            "prd_tier": ans["prd_tier"],
            "prd_path": "docs/prd/PRD.md",
            "cicd_opt_out": False,
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
        "principles": {
            "ranked": list(ans["principles_ranked"]),
            "tiebreakers": [],
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
        },
    }


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


def render_interview(proposal: dict, prd_path: str) -> str:
    p = proposal
    ans = default_answers(p)
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
    section("Autonomous modes", [
        "**Proposed:** all OFF "
        f"_(confidence: {_CONF_BADGE[am['confidence']]})_",
        "",
        am["rationale"],
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
    section("Project commands — HUMAN-REQUIRED (left empty by design)", [
        "`commands.test`, `commands.lint`, `commands.format`, "
        "`commands.typecheck`, `commands.ci_local`",
        "",
        "A PRD does not contain these. They are emitted **empty**. The "
        "installer turns empty gate commands into hooks that **fail loudly "
        "with a TODO** rather than silently passing — this is intentional "
        "(see README 'Honest limitations'). Fill them in the ANSWERS block "
        "only if you actually know them; otherwise leave empty and complete "
        "them before relying on the gates.",
    ])

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
    w("# List values (principles_ranked, secrets_never_read_paths) are")
    w("# written one item per line as '  - item' so an item may safely")
    w("# contain commas; edit/add/remove '  - ' lines under the key.")
    for k in ANSWER_KEYS:
        v = ans[k]
        if isinstance(v, list):
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


def parse_interview_answers(text: str) -> dict:
    """Extract the ANSWERS block back into a typed answers dict."""
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
    }
    list_keys = {"principles_ranked", "secrets_never_read_paths"}

    raw: dict[str, str] = {}
    list_raw: dict[str, list[str]] = {}
    body = lines[i0 + 1:i1]
    cur_list_key: str | None = None
    for line in body:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # A '- item' continuation line belongs to the most recent list key.
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
        if k in list_keys and v == "":
            # one-item-per-line form: items follow on '- ' lines.
            cur_list_key = k
            list_raw.setdefault(k, [])
        else:
            cur_list_key = None
            raw[k] = v

    out: dict = {}
    for k in ANSWER_KEYS:
        if k in list_keys:
            if k in list_raw:
                # canonical one-per-line form (commas inside items preserved)
                out[k] = [x.strip() for x in list_raw[k] if x.strip()]
                continue
            if k in raw:
                # legacy inline 'key: a, b, c' form (back-compat)
                out[k] = [x.strip() for x in raw[k].split(",") if x.strip()]
                continue
            raise ValueError(f"ANSWERS block missing key: {k}")
        if k not in raw:
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
            raise ValueError(f"ANSWERS block missing key: {k}")
        val = raw[k]
        if k in bool_keys:
            out[k] = val.strip().lower() in ("true", "1", "yes", "on")
        else:
            out[k] = val
    return out


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
                     use_llm: bool = False) -> dict:
    """Prompt the human one decision at a time over stdin; return answers.

    Equivalent to editing the questionnaire: every prompt shows the proposal
    and rationale; empty input accepts it. OPEN QUESTIONs are asked as
    sequential prompts (never batched). commands.* are explicitly NOT
    prompted as guessable - the human may optionally supply them with the
    loud-TODO consequence stated.
    """
    p = build_proposal(prd_text, project_fallback=project_fallback,
                        use_llm=use_llm)
    ans = default_answers(p)
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

    show("Principles", p["principles"]["rationale"])
    o("  Proposed ranked set:\n")
    for i, s in enumerate(ans["principles_ranked"], 1):
        o(f"    {i}. {s}\n")
    v = _ask("Principles (comma-separated, in rank order)",
             "; ".join(ans["principles_ranked"]),
             instream=instream, outstream=outstream, eof=eof)
    ans["principles_ranked"] = [x.strip() for x in v.replace(";", ",").split(",")
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

    show("Secrets policy", p["secrets"]["rationale"])
    v = _ask("Secrets enabled? true|false",
             str(ans["secrets_enabled"]).lower(),
             instream=instream, outstream=outstream, eof=eof)
    ans["secrets_enabled"] = v.lower() in ("true", "1", "yes", "on")
    v = _ask("Never-read globs (comma-separated)",
             ", ".join(ans["secrets_never_read_paths"]),
             instream=instream, outstream=outstream, eof=eof)
    ans["secrets_never_read_paths"] = [x.strip() for x in v.split(",")
                                       if x.strip()]

    show("Dependency policy", p["deps"]["rationale"])
    v = _ask("Deps policy enabled? true|false",
             str(ans["deps_enabled"]).lower(),
             instream=instream, outstream=outstream, eof=eof)
    ans["deps_enabled"] = v.lower() in ("true", "1", "yes", "on")

    show("Autonomous modes", p["autonomous_modes"]["rationale"])
    for mk, label in (("loop_mode_enabled", "Loop mode"),
                      ("goal_supervised_mode_enabled", "Goal-supervised mode"),
                      ("queue_mode_enabled", "Queue mode")):
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

    o("\n--- Project commands (HUMAN-REQUIRED) ---\n"
      "A PRD cannot supply these. Empty => the installer emits gates that "
      "FAIL LOUDLY\nwith a TODO (intentional). Leave empty unless you truly "
      "know them now.\n")
    for ck, label in (("commands_test", "test"), ("commands_lint", "lint"),
                      ("commands_format", "format"),
                      ("commands_typecheck", "typecheck"),
                      ("commands_ci_local", "ci_local")):
        ans[ck] = _ask(f"commands.{label}", ans[ck],
                       instream=instream, outstream=outstream, eof=eof)

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
              "acceptance.\nempty commands.* are intentional: the installer "
              "emits loud-TODO gates.\nRe-run bin/bootstrap-install --dry-run "
              "to preview the .claude/ tree.")
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
        Path(args.out).write_text(render_interview(proposal, str(prd)))
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
        try:
            answers = parse_interview_answers(ip.read_text())
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
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
            project_fallback=prd.stem or "my-project", use_llm=use_llm)
        return _finalize(answers, Path(args.out), outstream=sys.stdout)

    return 2  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

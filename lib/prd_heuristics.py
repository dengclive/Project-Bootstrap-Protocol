"""
Deterministic PRD -> decision heuristics (stdlib only, pure functions).

This module is the *judgement* core of the decision-layer interview tool. It
reads PRD text and proposes the non-mechanical decisions the installer needs:
archetype, PRD tier, principle deltas, secrets/deps posture, TDD policy, and
autonomous-mode recommendations.

Design rules (mirroring Bootstrap-Protocol-v2-0-0.md "Protocol rules for the AI" and the
session constraints):

  * It PROPOSES, never silently decides. Every proposal carries a rationale
    and a confidence; genuinely ambiguous calls are emitted as explicit
    OPEN QUESTIONs for the human, not resolved by coin-flip.
  * It is a PURE FUNCTION of its inputs: identical PRD text in => identical
    proposal out. No clocks, no randomness, no I/O. This is what lets the
    questionnaire front-end be determinism-tested like the installer.
  * It does NOT reinvent the archetype principle starter sets. It imports
    them from lib/defaults.py and only proposes *deltas*.
  * It NEVER guesses commands.test/lint/format - a PRD does not contain them.
    Those are surfaced as human-required, consistent with the installer's
    loud-failing empty-command gates.

The archetype table, PRD-tier definitions, and skip-policy invariant encoded
below are taken from the bundled Bootstrap-Protocol-v2-0-0.md (Project Archetypes table,
"PRD tiers" list, Skip Policy, Phase 0/4/9.5/9.6/9.7).
"""

from __future__ import annotations

import re

from defaults import ARCHETYPES, PRINCIPLE_STARTERS  # reuse, do not duplicate

# --------------------------------------------------------------------------- #
# Confidence levels (ordered).  "open" => surface as OPEN QUESTION, do not pick
# --------------------------------------------------------------------------- #
CONF_HIGH = "high"
CONF_MEDIUM = "medium"
CONF_LOW = "low"
CONF_OPEN = "open"


# --------------------------------------------------------------------------- #
# Archetype scoring
# --------------------------------------------------------------------------- #
# Keyword -> weight per archetype.  Weights are small integers; the winner must
# clear ARCHETYPE_MARGIN over the runner-up or the call becomes an OPEN
# QUESTION.  Keywords are matched on word boundaries, case-insensitively, so
# "service" does not fire on "serviceable" and PRD prose cannot be made to
# inject regex.
ARCHETYPE_KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "cli": [
        (r"command[- ]line", 3), (r"\bcli\b", 3), (r"\bterminal\b", 2),
        (r"single[- ]binary", 2), (r"\bbuild tool\b", 2),
        (r"dev(eloper)? utilit(y|ies)", 2), (r"\bsubcommand", 2),
        (r"\bstdin\b", 1), (r"\bstdout\b", 1), (r"\bflag\b", 1),
    ],
    "library": [
        (r"\blibrary\b", 3), (r"\bsdk\b", 3), (r"npm package", 3),
        (r"python (lib|package)", 3), (r"public api", 2),
        (r"\bsemver\b", 2), (r"shared module", 2), (r"importable", 1),
        (r"published to (pypi|npm|crates)", 2),
    ],
    "service": [
        (r"\bmicroservice\b", 3), (r"\brest api\b", 3), (r"\bgraphql\b", 2),
        (r"\bendpoint", 2), (r"\bworker\b", 2), (r"backend service", 3),
        (r"\bhttp api\b", 2), (r"request/response", 1), (r"\bgrpc\b", 2),
    ],
    "fullstack": [
        (r"full[- ]stack", 3), (r"web app", 3), (r"\bfrontend\b.*\bbackend\b", 3),
        (r"\bspa\b", 1), (r"\bui\b.*\bdatabase\b", 2),
        (r"react.*(api|server)", 2), (r"end users? log in", 1),
    ],
    "mobile": [
        (r"\bios\b", 3), (r"\bandroid\b", 3), (r"react native", 3),
        (r"\bflutter\b", 3), (r"app store", 2), (r"play store", 2),
        (r"mobile app", 3), (r"\bswiftui\b", 2),
    ],
    "data-ml": [
        (r"\betl\b", 3), (r"training pipeline", 3), (r"inference (service|pipeline)", 3),
        (r"machine learning", 2), (r"\bml model\b", 2), (r"data pipeline", 3),
        (r"\bdataset", 1), (r"feature store", 2), (r"model promotion", 2),
        (r"\blineage\b", 1),
    ],
    "ai-agent": [
        (r"\bllm\b", 3), (r"large language model", 3), (r"multi[- ]agent", 3),
        (r"\bprompt(s|ing|-driven)?\b", 2), (r"\bagent system\b", 3),
        (r"\bevals?\b", 2), (r"token cost", 2), (r"\brag\b", 2),
        (r"prompt versioning", 2),
    ],
    "platform": [
        (r"\bmonorepo\b", 3), (r"multiple deployable", 3),
        (r"multi[- ]component", 3), (r"cross[- ]team", 2),
        (r"per[- ]component", 2), (r"\bplatform\b", 2),
        (r"several services", 2),
    ],
}

# Required PRD tier per archetype, verbatim from Bootstrap-Protocol-v2-0-0.md Project
# Archetypes table.  "other" defaults to standard.
ARCHETYPE_REQUIRED_TIER: dict[str, str] = {
    "cli": "micro",
    "library": "standard",
    "service": "standard",
    "fullstack": "standard",
    "mobile": "standard",
    "data-ml": "standard",
    "ai-agent": "standard",
    "platform": "full",
    "other": "standard",
}

ARCHETYPE_NOTE: dict[str, str] = {
    "cli": "CI/CD simplifies to release flow only.",
    "library": "Adds semver and public API discipline; no deploy environments.",
    "service": "Skips frontend conventions.",
    "fullstack": "All phases run fully.",
    "mobile": "Web deploy gates replaced by app store flow.",
    "data-ml": "Auth replaced by data access controls.",
    "ai-agent": "Adds prompt versioning, evals, cost tracking.",
    "platform": "All phases, possibly run per component.",
    "other": "Phases adapt via dimension answers; synthetic archetype profile.",
}

TIER_ORDER = {"micro": 0, "standard": 1, "full": 2}
TIER_FROM_ORDER = {v: k for k, v in TIER_ORDER.items()}

ARCHETYPE_MARGIN = 2  # winner must beat runner-up by at least this much


def _norm(text: str) -> str:
    """Lowercase; collapse whitespace.  Pure, no regex compiled from PRD."""
    return re.sub(r"\s+", " ", text.lower())


def score_archetypes(prd_text: str) -> list[tuple[str, int]]:
    """Return [(archetype, score), ...] sorted high->low, deterministically.

    Ties broken by the fixed ARCHETYPES iteration order (sorted) so the
    output is stable regardless of dict ordering.
    """
    norm = _norm(prd_text)
    scores: dict[str, int] = {a: 0 for a in ARCHETYPE_KEYWORDS}
    for archetype, kws in ARCHETYPE_KEYWORDS.items():
        for pattern, weight in kws:
            # count non-overlapping word-boundary matches, capped so a single
            # repeated word cannot dominate the classification
            hits = len(re.findall(pattern, norm))
            if hits:
                scores[archetype] += weight * min(hits, 3)
    # stable sort: primary by -score, secondary by archetype name
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def propose_archetype(prd_text: str) -> dict:
    """Propose an archetype with rationale + confidence.

    Returns a dict:
      {value, confidence, rationale, alternatives:[...], open_question?:{...}}
    If the signal is weak or contested, confidence == CONF_OPEN and an
    open_question is attached enumerating the realistic options - the tool
    does NOT pick silently (Bootstrap-Protocol-v2-0-0.md: "Halt and ask if anything is
    ambiguous").
    """
    ranked = score_archetypes(prd_text)
    top, top_score = ranked[0]
    second, second_score = ranked[1]

    if top_score == 0:
        return {
            "value": "other",
            "confidence": CONF_OPEN,
            "rationale": (
                "No archetype keywords matched the PRD. The project may be a "
                "browser extension, game, firmware, plugin, or hybrid system "
                "- all of which map to 'other' with a synthetic profile in "
                "Bootstrap-Protocol-v2-0-0.md Phase 0. Human must confirm."),
            "alternatives": [a for a, _ in ranked[:3]],
            "open_question": {
                "id": "archetype",
                "prompt": (
                    "The PRD did not contain recognizable archetype signals. "
                    "Which Bootstrap-Protocol-v2-0-0.md archetype best fits this project?"),
                "options": sorted(ARCHETYPES),
                "default": "other",
            },
        }

    margin = top_score - second_score
    if margin < ARCHETYPE_MARGIN and second_score > 0:
        return {
            "value": top,
            "confidence": CONF_OPEN,
            "rationale": (
                f"Archetype is ambiguous: '{top}' (score {top_score}) and "
                f"'{second}' (score {second_score}) are within the "
                f"{ARCHETYPE_MARGIN}-point decision margin. Bootstrap-Protocol-v2-0-0.md "
                f"requires classifying before configuring, so this is "
                f"surfaced for an explicit human choice rather than guessed."),
            "alternatives": [a for a, s in ranked[:3] if s > 0],
            "open_question": {
                "id": "archetype",
                "prompt": (
                    f"Archetype is contested between '{top}' and '{second}'. "
                    f"Which fits? (See Bootstrap-Protocol-v2-0-0.md Project Archetypes table.)"),
                "options": [a for a, s in ranked if s > 0] or sorted(ARCHETYPES),
                "default": top,
            },
        }

    confidence = CONF_HIGH if (top_score >= 4 and margin >= 4) else CONF_MEDIUM
    return {
        "value": top,
        "confidence": confidence,
        "rationale": (
            f"PRD keyword scoring put '{top}' clearly ahead "
            f"(score {top_score} vs next-best '{second}' {second_score}). "
            f"{ARCHETYPE_NOTE[top]}"),
        "alternatives": [a for a, s in ranked[1:3] if s > 0],
    }


# --------------------------------------------------------------------------- #
# PRD tier
# --------------------------------------------------------------------------- #
# Signals that justify *upgrading* above the archetype-required tier. We never
# downgrade (Bootstrap-Protocol-v2-0-0.md Phase 0 step 7: "Operator can request a higher tier
# but not a lower one").
TIER_UPGRADE_SIGNALS = [
    (r"competitive (analysis|landscape)", "full", "competitive analysis"),
    (r"market (context|sizing|analysis)", "full", "market context"),
    (r"phased rollout", "full", "phased rollout"),
    (r"per[- ]component scoping", "full", "per-component scoping"),
    (r"cross[- ]team", "full", "cross-team dependencies"),
    (r"\bpersonas?\b", "standard", "named personas"),
    (r"user journey", "standard", "user journeys"),
    (r"\bnon[- ]goals?\b", "standard", "explicit non-goals"),
    (r"\bstakeholders?\b", "standard", "multiple stakeholders"),
    (r"\brisks?\b", "standard", "risk section"),
]


def propose_prd_tier(prd_text: str, archetype: str) -> dict:
    """Start at the archetype-required tier; upgrade (never downgrade) on
    multi-stakeholder / competitive / phased-rollout signals."""
    base = ARCHETYPE_REQUIRED_TIER.get(archetype, "standard")
    base_ord = TIER_ORDER[base]
    norm = _norm(prd_text)

    reached = base_ord
    reasons: list[str] = []
    for pattern, tier, label in TIER_UPGRADE_SIGNALS:
        if re.search(pattern, norm):
            t_ord = TIER_ORDER[tier]
            if t_ord > reached:
                reached = t_ord
            if t_ord >= base_ord:
                reasons.append(label)

    final = TIER_FROM_ORDER[reached]
    if final == base:
        rationale = (
            f"Archetype '{archetype}' requires the '{base}' PRD tier "
            f"(Bootstrap-Protocol-v2-0-0.md Project Archetypes table). No PRD signals "
            f"justified an upgrade.")
        conf = CONF_HIGH
    else:
        rationale = (
            f"Archetype '{archetype}' requires at least '{base}', but the "
            f"PRD shows {', '.join(sorted(set(reasons)))}, which Bootstrap-Protocol-v2-0-0.md "
            f"associates with the '{final}' tier. Upgraded (never "
            f"downgraded). The human may request an even higher tier.")
        conf = CONF_MEDIUM
    return {
        "value": final,
        "confidence": conf,
        "rationale": rationale,
        "floor": base,
    }


# --------------------------------------------------------------------------- #
# Principles - deltas from the archetype starter set (imported, not copied)
# --------------------------------------------------------------------------- #
# Strong PRD signals that justify *proposing an addition* to the starter set.
# We never drop a starter principle automatically; we only suggest adding.
PRINCIPLE_SIGNAL_ADDITIONS = [
    (r"reproducib", "Reproducibility over speed",
     "PRD emphasizes reproducibility"),
    (r"\bsecurity\b|\bthreat model\b|\bsecure by default\b",
     "Security over convenience", "PRD emphasizes security"),
    (r"\bprivacy\b|\bpii\b|\bgdpr\b|\bhipaa\b",
     "Privacy by default over data convenience", "PRD emphasizes privacy"),
    (r"\blatency\b|real[- ]time|sub[- ]second",
     "Latency budget is a correctness constraint",
     "PRD emphasizes real-time/latency"),
    (r"\bcost\b.*(budget|aware|track)|token cost",
     "Cost-awareness in every call", "PRD emphasizes cost"),
    (r"\baccessib|\bwcag\b|\ba11y\b",
     "Accessibility is not optional", "PRD emphasizes accessibility"),
    (r"regulat|complian|\baudit trail\b",
     "Auditability over implementation freedom",
     "PRD emphasizes regulatory compliance"),
]


def propose_principles(prd_text: str, archetype: str) -> dict:
    """Return the starter set (from defaults.PRINCIPLE_STARTERS) plus any
    PRD-justified *proposed additions*, each with its own rationale.

    The starter list is imported, never re-listed here, so if
    defaults.PRINCIPLE_STARTERS changes, this output changes with it.
    """
    starters = list(PRINCIPLE_STARTERS[archetype])
    norm = _norm(prd_text)
    additions: list[dict] = []
    for pattern, principle, why in PRINCIPLE_SIGNAL_ADDITIONS:
        if re.search(pattern, norm) and principle not in starters:
            if all(principle != a["principle"] for a in additions):
                additions.append({"principle": principle, "rationale": why})
    ranked = starters + [a["principle"] for a in additions]
    return {
        "starter_set": starters,
        "proposed_additions": additions,
        "ranked": ranked,
        "confidence": CONF_MEDIUM if additions else CONF_HIGH,
        "rationale": (
            f"Starter set for '{archetype}' taken verbatim from "
            f"lib/defaults.PRINCIPLE_STARTERS (Bootstrap-Protocol-v2-0-0.md Phase 4 step 2). "
            + (f"PRD signals justified proposing {len(additions)} addition(s); "
               f"these are proposals for human ranking, not silent edits."
               if additions else
               "No PRD signal justified a delta; starter set proposed as-is.")),
    }


# --------------------------------------------------------------------------- #
# TDD policy
# --------------------------------------------------------------------------- #
def propose_tdd_policy(prd_text: str) -> dict:
    norm = _norm(prd_text)
    if re.search(r"test[- ]driven|\btdd\b|tests? (must be )?written first", norm):
        return {
            "value": "required",
            "confidence": CONF_MEDIUM,
            "rationale": (
                "PRD explicitly references test-driven development. Proposing "
                "'required' (wires the TDD gate in Phase 6). Human confirms - "
                "this is a workflow commitment, not a PRD-derivable fact."),
        }
    if re.search(r"\bhigh test coverage\b|\bwell[- ]tested\b|quality bar", norm):
        return {
            "value": "encouraged",
            "confidence": CONF_LOW,
            "rationale": (
                "PRD signals a quality emphasis but does not mandate TDD. "
                "Proposing 'encouraged' (the Bootstrap-Protocol-v2-0-0.md/installer default). "
                "Human may escalate to 'required'."),
        }
    return {
        "value": "encouraged",
        "confidence": CONF_LOW,
        "rationale": (
            "No TDD signal in the PRD. Proposing the installer default "
            "'encouraged'. TDD policy is a human workflow decision "
            "(Bootstrap-Protocol-v2-0-0.md Phase 4 step 6), surfaced for confirmation."),
    }


# --------------------------------------------------------------------------- #
# Secrets & dependency posture
# --------------------------------------------------------------------------- #
def propose_secrets(prd_text: str) -> dict:
    norm = _norm(prd_text)
    handles = re.search(
        r"\bapi keys?\b|\bsecrets?\b|\bcredential|\btokens?\b|\bpassword|"
        r"\boauth\b|\b\.env\b|private key|service account", norm)
    if handles:
        return {
            "enabled": True,
            "confidence": CONF_MEDIUM,
            "rationale": (
                "PRD references credentials/secrets. Proposing secrets policy "
                "ENABLED with the installer's conservative default "
                "never-read globs (.env*, secrets/**, *.pem, *.key). The "
                "human must confirm the globs match this project's layout - "
                "the PRD does not contain paths."),
            "open_question": {
                "id": "secrets_paths",
                "prompt": (
                    "Confirm or extend the never-read secrets globs for this "
                    "project (PRD cannot supply real paths)."),
                "options": [
                    "Accept defaults (.env*, secrets/**, *.pem, *.key)",
                    "I will edit never_read_paths below",
                ],
                "default": "Accept defaults (.env*, secrets/**, *.pem, *.key)",
            },
        }
    return {
        "enabled": True,
        "confidence": CONF_LOW,
        "rationale": (
            "No explicit secrets signal, but Bootstrap-Protocol-v2-0-0.md Skip Policy keeps "
            "Phase 2.7 ON unless the project handles NO secrets at all. "
            "Proposing enabled with defaults; human may disable if truly "
            "secret-free."),
    }


def propose_deps(prd_text: str) -> dict:
    norm = _norm(prd_text)
    stdlib_only = re.search(
        r"\bstdlib[- ]only\b|no (external |third[- ]party )?dependenc|"
        r"zero dependenc|standard library only", norm)
    if stdlib_only:
        return {
            "enabled": False,
            "confidence": CONF_MEDIUM,
            "rationale": (
                "PRD states a stdlib-only / no-dependency posture. "
                "Bootstrap-Protocol-v2-0-0.md Skip Policy allows skipping Phase 2.5 when the "
                "archetype has no external deps. Proposing deps policy "
                "DISABLED; human confirms."),
        }
    return {
        "enabled": True,
        "confidence": CONF_LOW,
        "rationale": (
            "Dependency policy proposed ENABLED with an empty approved-list "
            "(installer default: the gate blocks anything not pre-approved). "
            "Human curates the approved list - the PRD rarely enumerates "
            "concrete packages and the tool will not invent them."),
    }


# --------------------------------------------------------------------------- #
# Autonomous modes - always conservative; queue can never imply an invalid cfg
# --------------------------------------------------------------------------- #
def propose_autonomous_modes(prd_text: str) -> dict:
    """All three default OFF, citing Bootstrap-Protocol-v2-0-0.md trust-ramp / defer guidance.

    Crucially, queue mode is never proposed True unless loop|goal is also
    proposed True, so a generated draft can never violate the
    resolve_config skip-policy invariant on this axis.
    """
    norm = _norm(prd_text)
    wants_autonomy = re.search(
        r"autonomous|unattended|overnight|self[- ]driving|run.*without "
        r"(a )?human|hands[- ]off", norm)
    rationale_common = (
        "Bootstrap-Protocol-v2-0-0.md Phase 0/9.5/9.6/9.7 set all autonomous modes to "
        "DEFAULT SKIP (opt-in) and recommend deferring them until the "
        "project has shipped operator-in-the-loop tasks (5-10 for loop, "
        "10-20 for goal-supervised, 4+ weeks before queue). The PRD is not "
        "evidence the trust ramp has happened.")
    if wants_autonomy:
        rationale = (
            "PRD expresses interest in autonomous/unattended operation, but "
            + rationale_common + " Proposing all three OFF with an OPEN "
            "QUESTION so the human consciously opts in if the trust ramp is "
            "already satisfied.")
        oq = {
            "id": "autonomous_modes",
            "prompt": (
                "The PRD mentions autonomous operation. Enable any autonomous "
                "modes now? (Bootstrap-Protocol-v2-0-0.md strongly recommends deferring; "
                "queue mode requires loop or goal mode.)"),
            "options": [
                "None now (recommended; defer per trust ramp)",
                "Loop mode only",
                "Goal-supervised mode only",
                "Loop + goal",
                "Loop + goal + queue",
            ],
            "default": "None now (recommended; defer per trust ramp)",
        }
    else:
        rationale = ("No autonomous-operation signal in the PRD. "
                     + rationale_common)
        oq = None
    out = {
        "loop_mode_enabled": False,
        "goal_supervised_mode_enabled": False,
        "queue_mode_enabled": False,
        "confidence": CONF_HIGH,
        "rationale": rationale,
    }
    if oq:
        out["open_question"] = oq
    return out


# --------------------------------------------------------------------------- #
# Project name / one-line description (best-effort, always human-confirmable)
# --------------------------------------------------------------------------- #
def propose_project_name(prd_text: str, fallback: str) -> dict:
    """Look for a leading markdown H1 or a 'Project:'/'Name:' line.

    Never authoritative - the human edits it. PRD text is treated as data,
    never compiled into a regex.
    """
    for line in prd_text.splitlines():
        s = line.strip()
        m = re.match(r"#\s+(.+)", s)
        if m:
            name = m.group(1).strip()
            return {"value": name, "confidence": CONF_LOW,
                    "rationale": "Taken from the PRD's leading H1 heading; "
                                 "confirm or rename."}
        m = re.match(r"(?:project|name)\s*[:\-]\s*(.+)", s, re.I)
        if m:
            return {"value": m.group(1).strip(), "confidence": CONF_LOW,
                    "rationale": "Taken from a 'Project:'/'Name:' line; "
                                 "confirm or rename."}
    return {"value": fallback, "confidence": CONF_OPEN,
            "rationale": "No title found in the PRD; using a placeholder. "
                         "Human must set the real project name."}

# Retrofit Gap Analysis

**Scope:** What it takes to make RETROFIT.md a true counterpart of BOOTSTRAP.md in `dengclive/Project-Bootstrap-Protocol`, and whether the repo's installer needs retrofit support.

**Inputs reviewed:** uploaded `RETROFIT.md` (v1.5.1), repo `README.md`, `BOOTSTRAP.md` (v1.9.0), repo file tree (`bin/`, `lib/`, `plugin/`, `tests/`, `examples/`, `bootstrap.config.yaml`).

---

## 1. Bottom line

The repo's install scripts are **not sufficient for retrofit** and **do need work** — but the work is *additive and architecture-preserving*, not a rewrite. There are two separate deliverables, and both are required:

1. **RETROFIT.md must be updated.** It is stale against the protocol it claims to be a companion to. It declares itself "companion to BOOTSTRAP.md v1.6.1"; the repo ships BOOTSTRAP.md **v1.9.0**. Three minor versions of protocol surface — most importantly the entire autonomous-mode family (Phase 9.5 loop, 9.6 goal-supervised, 9.7 queue) and the `BOOTSTRAP-COMPANION.md` split — do not exist anywhere in the retrofit protocol. A retrofit cannot reach "BOOTSTRAP equivalence" (its own stated success bar) against a BOOTSTRAP it has never heard of.

2. **The installer must be extended for retrofit.** Greenfield-only assumptions are baked into the decision layer (PRD→config) and the scaffolding layer has no templates for the brownfield-only artifacts RETROFIT.md mandates (inventory, debt registry, legacy allowlist, graduated hook rollout, retrofit state file, retrofit-specific skills). The existing installer is correct for what it does; it simply does not do retrofit.

The reason both are needed: RETROFIT.md's explicit success bar is **functional indistinguishability from BOOTSTRAP output for the six shared categories**, plus brownfield-only artifacts. "Functional indistinguishability" means the *same scaffolding* — so the existing deterministic installer is the right engine. But "plus brownfield-only artifacts" and "from code analysis, not from a PRD" are real new surfaces the current scripts do not implement.

---

## 2. Why the scripts are not enough (architecture mapping)

The repo's stated design is a deliberate **two-layer split** (from README):

| Layer | Greenfield tool | What it is |
|---|---|---|
| **Decision** | `bin/bootstrap-interview` | PRD → proposed `bootstrap.config.yaml`; needs a human; non-deterministic surfaces excluded from guarantees |
| **Scaffolding** | `bin/bootstrap-install` (`lib/installer.py`, `lib/templates.py`, `lib/defaults.py`) | config → `.claude/` tree; pure deterministic function of the config |

Retrofit maps onto this split cleanly, which is the key insight:

- **Retrofit's scaffolding is mostly the same scaffolding.** The six equivalence categories (Steering / Specs / Hooks / Model Assignment / Audio Alerts / Subagent Workflows) are, by RETROFIT.md's own design, identical in shape to greenfield output. So `lib/templates.py` and `lib/installer.py` are the right engine, *given a correct config*. This is why a parallel installer would be wrong — it would duplicate the adversarially-reviewed core (S-1…S-5, F-1/F-2, L-1…L-3, W-1, T-1, R-1…R-3 findings) for no benefit.

- **Retrofit's decision layer is fundamentally different.** `bootstrap-interview` derives the config *from a PRD*. Retrofit derives it *from code analysis* — RETROFIT.md Phases R0 (inventory), R0.5 (archetype-from-code-evidence with confidence levels), R2 (convention reckoning), R3 (debt). This is genuinely new and cannot be a tweak to the PRD heuristics in `lib/prd_heuristics.py`.

- **Retrofit emits artifacts the scaffolding layer has no templates for.** These are RETROFIT.md-mandated and have no greenfield equivalent, so `lib/templates.py` literally cannot produce them today.

---

## 3. Installer gaps (concrete)

### 3.1 Decision layer (new surface)

| Need | Greenfield equivalent | Status |
|---|---|---|
| Code-analysis → config proposal | `bin/bootstrap-interview` (PRD → config) | **Missing.** Needs a retrofit decision tool: inventory scan, archetype-from-evidence with HIGH/MEDIUM/LOW confidence, convention categorization (Canonical / Deprecated / Intentional Variation / Modernize), debt capture. |
| Archetype from code, not PRD | Phase 0 archetype from PRD | **Missing.** RETROFIT.md §"Project Archetypes (Retrofit Classification)" classifies from inventory signals; `lib/prd_heuristics.py` only reads PRD text. |
| Synthetic profile from inventory dimensions | `synthetic_profile` from Phase 0 dimension interview | **Partially reusable.** Shape is the same JSON object; the *population source* differs (inventory vs interview). |

### 3.2 Scaffolding layer (new templates)

Every item below is RETROFIT.md-required and absent from `lib/templates.py`:

- **`.claude/inventory/`** — `structure.md`, `languages.md`, `dependencies.md`, `testing.md`, `git-history.md`, `conventions.md`, `product-signals.md`, `baseline-metrics.md`, `tribal-knowledge.md`, `danger-zones.md`, `equivalence-validation.md`. One-time audit; greenfield has no analog.
- **`.claude/debt.md`** — known-issues registry; greenfield has nothing to register at bootstrap.
- **Legacy allowlist** — a transitional path list in `spec-strategy.md`, **wired into the spec gate / test gate / TDD gate hook bodies as an exemption list**. This is a real `templates.py` *and* hook-body change: the gates currently block unconditionally; retrofit needs them to skip allowlisted paths and to honor a "retrofit-active" master switch that R7 disables.
- **`spec-strategy.md`** — forward-only / touch-based / bulk-backfill decision. No greenfield equivalent.
- **`workflow-source-of-truth.md`** — PM-artifact reckoning (Strategy A/B/C). RETROFIT-only by construction.
- **Conditional steering** — `compliance.md` (regulatory detection), `contracts.md` (boundary specs), `migration.md` (in-flight strangler). Greenfield adds these post-bootstrap via milestones; retrofit emits them at retrofit time because the triggers have already fired.
- **Graduated hook rollout** — RETROFIT.md mandates a warn→block schedule + bypass-rate monitoring. The installed hooks block immediately. Needs a time-phased / mode-gated hook variant the greenfield installer never produces.
- **`.retrofit-state.json`** — parallel to `.bootstrap-state.json`, with a `skip_decisions` field and the retrofit phase ledger. `lib/installer.py`'s state writer knows only the bootstrap schema.
- **Retrofit-specific skills** — `inventory-scan`, `prior-art-audit`, `convention-categorize`, `legacy-spec`, `migration-plan`, `legacy-pin-test`, `boundary-spec`, plus archetype-specific (`prompt-pinning-eval`, `dataset-pin-test`). Each needs a template body and a model assignment. None exist in `lib/templates.py` / `lib/defaults.py`.

### 3.3 Behavioral / safety implications

The legacy-allowlist and graduated-rollout changes touch the **security-critical hook bodies** that rounds S-1/S-3/S-5/T-1 hardened. Any retrofit hook variant must pass the same `tests/test_installer.py` behavioral harness (no `eval`, quoted paths, exit-code convention, fail-loud on missing tooling, no fail-open). This is the highest-risk part of the installer work and should be gated behind the same adversarial-review discipline the README documents.

---

## 4. RETROFIT.md document gaps (vs BOOTSTRAP v1.9.0)

| Area | BOOTSTRAP v1.9.0 | RETROFIT.md v1.5.1 | Gap |
|---|---|---|---|
| Companion target | v1.9.0 | declares "companion to v1.6.1" | **3 minor versions stale** |
| Autonomous loop (Phase 9.5) | Full phase, opt-in, trust ramp | **Absent** | No retrofit guidance on whether/when a brownfield project may enable loop mode |
| Goal-supervised (Phase 9.6) | Full phase, judge model, calibration ledger | **Absent** | No retrofit equivalent |
| Queue mode (Phase 9.7) | Full phase, gated on 9.5/9.6, 4-week ramp | **Absent** | Brownfield has *stronger* reason for a longer ramp (ungated-habit developers) — substantive new protocol content, not a reference fix |
| `BOOTSTRAP-COMPANION.md` | Mental Model, Model Assignment, milestones, glossary moved out of BOOTSTRAP.md | RETROFIT.md still references monolithic BOOTSTRAP sections | Cross-references point at sections that no longer live where stated |
| Post-bootstrap milestones | New section: triggers that move greenfield into producing retrofit-style artifacts | RETROFIT v1.5.1 *anticipated* this ("As of BOOTSTRAP v1.6.0…") | Needs reconciliation against the *actual* v1.9.0 milestones text |
| State schema | `loop_in_flight`, `goal_in_flight`, `queue_runs_history`, three mode flags, `bootstrap_protocol_version: "1.9.0"` | `.retrofit-state.json` schema predates all of this | Retrofit state file must carry the autonomous-mode flags too, or retrofit projects can never enable those modes later |
| Concurrency rule | Combined-budget rule across modes; brownfield-specific 4-week extension already implied | **Absent** | Retrofit should *tighten* this for brownfield, not just copy it |

The autonomous-mode absence is the substantive one. It is not a find-and-replace. Retrofit has real, different decisions to make: a brownfield project's existing developers have *ungated habits* (RETROFIT.md already argues this for graduated hook rollout). The same reasoning says queue mode at retrofit time is more dangerous than at bootstrap time and should carry a longer or conditional trust ramp. That is new protocol text only the retrofit author can decide.

---

## 5. Recommended plan

Ordered, each step gated on the prior:

1. **This document** (gap analysis) — done; surfaces the autonomous-mode decisions for the operator.
2. **RETROFIT.md full rewrite to v1.9.0 parity** — re-anchor companion version; add R-phase equivalents for Phases 9.5/9.6/9.7 with brownfield-tightened trust ramps; reconcile against `BOOTSTRAP-COMPANION.md` split; extend `.retrofit-state.json` schema; add a changelog entry (v1.5.1 → v1.6.0 or v2.0.0 depending on whether the autonomous-mode addition is judged breaking). Recommend a **minor-or-major bump with changelog**, not a silent edit.
3. **Retrofit installer as an additive mode** on the existing two-layer architecture:
   - `bin/retrofit-interview` (or `bootstrap-interview --retrofit`) — code-analysis decision layer producing a retrofit-aware config.
   - `lib/templates.py` extension — brownfield artifact templates behind a `mode: retrofit` switch; greenfield path byte-identical and frozen.
   - Hook-body variants for legacy allowlist + graduated rollout, behind the same behavioral test harness.
   - `.retrofit-state.json` writer.
   - `tests/test_retrofit.py` mirroring the determinism / idempotency / non-destructive / reversible / fail-loud properties.
4. **Adversarial review pass** on the hook-body changes specifically (the S-/T-/L- class), since that is where retrofit touches security-critical frozen code.

### Open decisions for the operator (needed before step 2)

- **Autonomous modes in retrofit:** allow at retrofit time at all? If yes, what trust ramp — same as greenfield, or brownfield-extended (e.g., loop mode only after N touch-based specs have shipped under the new gates, queue mode only after the graduated rollout has fully reached "block")?
- **Version bump semantics:** is adding the autonomous-mode phases backward-compatible for existing v1.5.x retrofits (additive → minor) or does it change the equivalence target enough to be major?
- **Installer integration shape:** `--retrofit` flag on the existing binaries vs separate `retrofit-*` binaries. (Recommendation: flag, to keep one frozen scaffolding core.)

# Project Retrofit Protocol

**Version:** 1.6.2 — companion to BOOTSTRAP.md v1.9.0. Use this protocol to add `.claude/` workflow infrastructure to an existing project. For greenfield projects, use BOOTSTRAP.md instead.

**Companion reference:** as of BOOTSTRAP v1.7.0, BOOTSTRAP's Mental Model, Model Assignment Strategy, Post-bootstrap milestones, scope-exclusion list, Cheat Sheet, Glossary, Migration notes, and phase-numbering rationale live in `BOOTSTRAP-COMPANION.md`, not in `BOOTSTRAP.md` itself. Where this protocol says "see BOOTSTRAP §X" for one of those topics, read `BOOTSTRAP-COMPANION.md`. Where it references an executable phase (Phases 0–10), read `BOOTSTRAP.md`.

**Changelog:** see §"Changelog" in `RETROFIT-COMPANION.md` for v1.0–v1.6.2 history.

> **For the AI:** When the operator opens this file and asks you to retrofit, you run this protocol end-to-end. Phases R-1 through R7 are retrofit-specific. From R8 onward (formerly "BOOTSTRAP Phase 5+ with adjustments"), this protocol *embeds* the retrofit-specific changes inline rather than asking you to cross-reference BOOTSTRAP — every phase is documented here in self-contained form, with one deliberate exception: R8.D (Spec Versioning) has zero retrofit adjustment and is executed by-reference against BOOTSTRAP §7.5 rather than re-embedded, so the two cannot drift apart. R8.G/R8.H/R8.I cover the retrofit equivalents of BOOTSTRAP's three optional autonomous modes (Phases 9.5/9.6/9.7); they are **opt-in, default-disabled, and gated on retrofit-specific trust milestones that are strictly stricter than greenfield's** — see §"Autonomous Modes in Retrofit" for why. You still read BOOTSTRAP/BOOTSTRAP-COMPANION for context; this is the one you execute. Do not batch. Do not skip phases without explicit override. Confirm each artifact with the operator before moving on. **Do not fix technical debt during retrofit** — register it and move on.
>
> **For the operator:** This protocol adds spec-driven development infrastructure to an existing codebase. The goal is **minimum viable retrofit** — just enough `.claude/` structure to start using the workflow on new features, with a clean line between "legacy code" and "new spec-driven work." Existing technical debt is registered but not fixed. Expect 90–180 minutes for a small-to-medium project (under ~500 source files, single owner). Larger projects or those with substantial prior `.claude/` art take longer because more conversations are needed.
>
> **Before starting:** if you're running this in an environment that supports model selection (e.g., Claude Code), launch the wizard with the strongest reasoning model available — typically Opus 4.7. The retrofit wizard is judgment-heavy (especially R2 convention reckoning, which is the highest-leverage conversation in the entire protocol) and runs once per project. Subagent and skill model assignments are configured in the **Model Assignment Strategy** section below. If you intend to opt into any autonomous mode (R8.G loop / R8.H goal-supervised / R8.I queue), read §"Autonomous Modes in Retrofit" first — for a brownfield project these are deferred behind milestones, not enabled at retrofit time, and the wizard will scaffold but not activate them.

---

## When to use this protocol vs. BOOTSTRAP.md

| Situation | Use |
|---|---|
| New project, no code yet | BOOTSTRAP.md |
| New project, scaffolding only (less than ~50 files of mostly-generated code) | BOOTSTRAP.md |
| Existing project, you know the structure well, **under ~500 source files** (excluding docs, tickets, generated, and vendored dirs) | RETROFIT.md (this doc) |
| Existing project with **500–2000 source files** | RETROFIT.md, expect R2 convention reckoning to take 2–3x longer; consider running it across multiple sessions |
| Existing project with **>2000 source files** or multi-year history with lost institutional knowledge | Out of scope for this protocol version; field-test this protocol on a smaller project first, or do a precursor "interview phase" with the operator before R0 |
| Adding `.claude/` to a project that has had `.claude/` before | RETROFIT.md, with the "existing `.claude/`" branch in Phase R0 |

The defining question: **is there code already, and does it represent intentional design choices the operator wants to preserve?** If yes, retrofit. If the existing code is throwaway scaffolding, treat as greenfield.

**The "source files" qualifier matters.** A project might show 1,400 tracked files but have 800 of them in `tickets/` or `docs/` or generated migrations. Use `git ls-files | grep -vE '^(docs/|tickets/|tutorials/|generated/|\.venv/|node_modules/|vendor/|\.scratch/)' | wc -l` (adjust the exclude list per project) as the rough source-file count. The 500-file ceiling is for that count, not raw tracked files.

---

## Mental Model, Model Assignment, and Reference Material

**Moved to `RETROFIT-COMPANION.md` (v1.6.0 companion split).** The Mental Model (what success looks like, brownfield SDD discipline, failure modes, fixed-position concepts), the Model Assignment Strategy table, Portfolio Awareness, the Cheat Sheet, the Glossary, the scope-exclusion list (“What this protocol does not cover”), and the full Changelog now live in `RETROFIT-COMPANION.md`. This follows the same companion-split principle as BOOTSTRAP v1.7.0’s `BOOTSTRAP-COMPANION.md`: reference material the wizard consults moves out; execution-binding material stays. The exact section inventory is not a strict mirror — RETROFIT’s companion adds sections BOOTSTRAP’s has no counterpart for (Portfolio Awareness, the Changelog), handles a topic inline that BOOTSTRAP keeps as a standalone companion section (phase-numbering rationale, here in the R8 intro), and correctly has no counterpart for BOOTSTRAP-companion sections that describe machinery RETROFIT doesn’t have (state-file Migration notes) or artifacts brownfield produces at retrofit time rather than post-milestone (Post-bootstrap milestones — a justified architectural asymmetry, not a gap). Behavior is unchanged: every moved section is byte-identical to its prior location in `RETROFIT.md`; only the companion preamble is new. Consult the companion for those topics; execute this file. The sections that *bind execution* — §“Autonomous Modes in Retrofit”, §“BOOTSTRAP Equivalence Target”, and §“Validating Equivalence” — remain here because the wizard runs against them, exactly as BOOTSTRAP kept its equivalence-binding content in the executable file.

---

## Autonomous Modes in Retrofit

**New in v1.6.0 — the catch-up to BOOTSTRAP v1.7.0/v1.8.0/v1.9.0.** BOOTSTRAP Phases 9.5 (autonomous loop mode), 9.6 (goal-supervised mode), and 9.7 (autonomous queue mode) are optional unattended-execution layers. RETROFIT v1.6.0 adds their retrofit equivalents as **R8.G**, **R8.H**, and **R8.I**. The defining design decision — and the reason this is a minor version bump, not a reference fix — is the **trust-ramp posture for brownfield**.

### Why brownfield is different (the asymmetry that drives the whole section)

BOOTSTRAP's own greenfield trust ramp already recommends *deferring* these modes: loop mode until 5–10 operator-in-loop tasks have shipped, goal-supervised until 10–20, queue mode until at least 4 weeks of real per-task operation. The reasoning is that the project's conventions and test infrastructure must exist and be trustworthy before the agent runs unattended.

A retrofitted brownfield project has a *stronger* version of exactly this concern, and the protocol already commits to the principle. R8.A.6's graduated hook rollout (G14) exists precisely because **pre-existing developers have ungated commit habits** and the spec/test/lint gates cannot be trusted to actually hold until the warn→block schedule has fully landed. Until the legacy allowlist has meaningfully shrunk and the gates are blocking (not warning), an autonomous agent running unattended against this codebase is running against gates that *do not yet enforce*. That is the precise failure mode unattended execution amplifies by the number of tasks it dispatches.

Copying BOOTSTRAP's greenfield ramp verbatim would therefore contradict RETROFIT's own established reasoning. The brownfield ramp must be **strictly stricter than greenfield's** and gated on retrofit-specific milestones, not task counts alone.

### The posture: scaffold at retrofit, enable post-milestone

The retrofit **generates all opted-into autonomous-mode scaffolding** during R8.G/H/I (so the deterministic, idempotent installer contract is preserved and no second tool invocation is required later) but leaves every mode **default-disabled**, with enablement gated on the milestones below. This mirrors, structurally, how BOOTSTRAP v1.7.0's "Post-bootstrap milestones" section moves greenfield projects into producing artifacts they didn't produce at bootstrap — except retrofit's triggers are about *gate trustworthiness*, not *project maturity*.

| Mode | Retrofit equivalent | Greenfield ramp (BOOTSTRAP) | **Brownfield ramp (RETROFIT — strictly stricter)** |
|---|---|---|---|
| Loop (9.5) | **R8.G** | Defer until 5–10 operator-in-loop tasks | Defer until **(a)** R8.A.6 rollout has reached steady-state "block" for the spec gate **and** test gate, **and (b)** ≥10 touch-based specs have shipped *under those blocking gates* (not merely 10 tasks — 10 tasks that actually passed enforced gates), **and (c)** the legacy allowlist has shrunk by a project-set threshold (default ≥25% of its retrofit-time size) |
| Goal-supervised (9.6) | **R8.H** | Defer until 10–20 operator-in-loop tasks | All of R8.G's conditions, **plus** the goal-supervised calibration ledger (`learnings/mode-selection.md`) has ≥10 real brownfield entries so the recommendation rule is calibrated against this codebase's actual drift-prone areas, not greenfield assumptions |
| Queue (9.7) | **R8.I** | Defer until ≥4 weeks real per-task operation; requires 9.5 or 9.6 enabled | All of R8.G's conditions, **plus** R8.A.6 rollout has reached steady-state "block" for **every** hook (not just spec+test), **plus** ≥4 weeks of real operation on R8.G *or* R8.H *after* those gates began blocking, **plus** the standard BOOTSTRAP gate (queue requires loop or goal-supervised enabled). Rationale: queue mode multiplies every per-task failure by the task count; doing that while any gate is still in warn-mode is the worst case the ungated-habit risk produces. |

These milestones are recorded in `.claude/.retrofit-state.json` (see schema in R0.5 and R8.G/H/I) and surfaced in the R7 handoff as explicit "do not enable until X" instructions. The wizard never enables an autonomous mode at retrofit time even if the operator asks — it explains the milestone and records the opt-in intent for later.

### Equivalence implication

The autonomous modes are part of the Subagent Workflows equivalence category (they extend `spec-decompose`, `implementer`, `CLAUDE.md`, and add wrapper scripts). A retrofit that the operator opted into autonomous modes for reaches equivalence when the **scaffolding** is present and correct, default-disabled, with the brownfield milestones documented — *not* when the modes are running. A retrofit where the operator declined autonomous modes is equivalent by archetype-conditional inapplicability, exactly like a CLI tool legitimately lacking an eval gate. Either way the equivalence target is satisfiable; silently enabling a mode at retrofit time, or scaffolding it without the milestone gate, is the failure mode.

---

## BOOTSTRAP Equivalence Target

The success bar. A successful retrofit produces these six categories of output, equivalent to what BOOTSTRAP produces for a greenfield project of the same archetype.

R7 Handoff validates the project against this checklist. Items are either present (✓), present-with-INTENTIONAL-VARIATION (✓\*, documented in `tech.md`), or missing (retrofit incomplete).

### 1. Steering Documents (BOOTSTRAP Phases 1, 2, 2.5, 2.7, 3, 4, 5, 6.5 equivalent)

Required outputs in `.claude/steering/`:

- ✓ **`product.md`** — product description (what / who / why). Thin pointer if existing PRD covers archetype's tier. Tier matches archetype's required tier (Micro/Standard/Full per §"Project Archetypes"); below-tier content surfaces a `debt.md` entry.
- ✓ **`tech.md`** — stack, conventions, intentional variations, modernized conventions, do-not-touch list.
- ✓ **`principles.md`** — 3-5 ranked principles drawn from archetype's starter set (per §R5) + project-specific findings, plus tiebreakers and TDD policy decision.
- ✓ **`structure.md`** — current directory structure plus any planned moves.
- ✓ **`deps.md`** — approved dependency list with archetype-aware policy.
- ✓ **`secrets.md`** — handling rules + historical leakage scan results.
- ✓ **`ci-cd.md`** — CI/CD steering or explicit opt-out record.
- ✓ **`tools.md`** — tool/MCP allowlist.

Plus project-specific steering docs created via R5 step 3 (G5 from v1.1):
- ✓\* **`workflow.md`**, **`contracts.md`**, **`phase.md`**, **`roles.md`**, etc. — only if pre-existing CLAUDE.md or operator-evolved patterns warrant.
- ✓\* **`compliance.md`** — only if R0 step 10 (regulatory regime detection) flagged applicable frameworks.
- ✓\* **`migration.md`** — only if the project has an in-flight strangler-fig modernization (per G7).

Plus retrofit-specific steering docs created via R0.7 (v1.4):
- ✓ **`workflow-source-of-truth.md`** — mandatory for retrofit; records PM-artifact source-of-truth decision (Strategy A/B/C). RETROFIT-only artifact (BOOTSTRAP greenfield projects don't have pre-existing PM artifacts to reckon with).

### 2. Specs and Spec Workflow (BOOTSTRAP Phase 7 + 7.5 + 7.6 equivalent)

Required outputs:

- ✓ **`.claude/specs/INDEX.md`** — registry of all specs.
- ✓ **`spec-strategy.md`** in `.claude/steering/` — forward-only / touch-based / bulk backfill decision (per R4).
- ✓ **Legacy allowlist** — derived from inventory; the list of paths that don't yet require specs (transitional, shrinks over time).
- ✓ **Spec-driven workflow gates** — same as BOOTSTRAP: spec-new → spec-review → spec-decompose → plan-review → implement → code-review → spec-validate. The retrofit's `spec-strategy.md` decides which gates apply to which files.
- ✓ **Spec versioning protocol** (per R8.D / BOOTSTRAP §7.5) — applied to specs going forward and to any project-specific versioned steering docs (e.g., `phase.md`).
- ✓\* **Three brownfield SDD spec patterns** (per R4 + G8) — change specs always; dependency boundary specs for projects with integration points; migration specs for projects with in-flight modernization.

### 3. Hooks (BOOTSTRAP Phase 6 equivalent)

Required hooks per archetype (filtered per R8.A — see §R8.A.3 for the archetype-conditional matrix):

- ✓ **Always recommended (BOOTSTRAP Phase 6 `(all)`):** spec gate (entry+commit), secrets gate, test gate, format/lint, cost log, dependency gate, drift detector, task-done alarm, decision-required alarm.
  - ✓\* **Test gate — INTENTIONAL VARIATION (brownfield grandfather):** always installed; modules listed in `inventory/testing.md` as having no tests are exempted via the runtime grandfather list (new modules unaffected). A no-test-framework project records this as ✓\* in `tech.md`, **not** as a silently dropped hook. Skip the script body entirely only if no test framework exists at all (rare; `debt.md` entry).
  - **Dependency gate:** always recommended; skip only if R5.5 deps was skipped for a stdlib-only project (BOOTSTRAP's sole carve-out), not by archetype.
- ✓ **CI mirror:** recommended whenever CI exists (mirrors BOOTSTRAP's `(all *with CI*)`); skipped when R8.F is opt-out (no CI to mirror). This conditionality is BOOTSTRAP-faithful, not a re-tier.
- ✓ **TDD gate:** conditional exactly as BOOTSTRAP (only if R5 enabled TDD policy).
- ✓\* **Archetype-specific:** eval gate (AI/agent), public API stability gate (Library/SDK), cross-component contract gate (Platform), mobile store-deploy gate (Mobile).

Plus retrofit-specific hook discipline:

- ✓ **Hook rollout discipline** (per G14) — graduated warn→block schedule documented; bypass-rate monitoring enabled.
- ✓\* **Audit log hook** (per G20.3) — only if regulatory regime requires (SOC 2 / HIPAA / FedRAMP).
- ✓ **Legacy allowlist honored** — spec gate, test gate, TDD gate exempt files in the allowlist.
- ✓ **Retrofit-active allowlist disabled** — set when R7 disables retrofit-active mode.

### 4. Model Assignment (BOOTSTRAP §"Model Assignment Strategy" equivalent)

Required outputs:

- ✓ **Per-skill / per-subagent model declarations** — every skill and subagent has an explicit `model:` field per BOOTSTRAP's strategy.
- ✓ **Operator-defined override path** — operator can override per session via Claude Code `--model` or per-skill via the `model:` frontmatter.
- ✓ **Defaults match BOOTSTRAP** — bootstrap wizard = Opus 4.7, code-review = Opus 4.7, implementer = Sonnet 4.6, etc. (See `BOOTSTRAP-COMPANION.md` §"Model Assignment Strategy" for the canonical table — it moved out of `BOOTSTRAP.md` in the v1.7.0 companion split.)
- ✓\* **Retrofit-specific skills** — `legacy-spec`, `prior-art-audit`, `convention-categorize`, `migration-plan`, `inventory-scan` — model assignments per RETROFIT §"Model Assignment Strategy" extension.
- ✓ **Plus new v1.3 skills** — `legacy-pin-test` (Sonnet, per G6), `boundary-spec` (Sonnet, per G8), archetype-specific skills (per G15) with declared model assignments.

### 5. Audio Alerts (BOOTSTRAP §6.E equivalent)

Required outputs in `.claude/hooks/audio-alerts.config` + supporting hook scripts:

- ✓ **Three-category alarm system** — drift / task-done / decision-required, each with a distinct sound.
- ✓ **Hook wiring** — `Notification` event → decision-required; `SubagentStop` → task-done; drift-detector hook → drift sound.
- ✓ **Quiet mode + per-session override** — per BOOTSTRAP §6.E.
- ✓\* **Modernized prior-art audio** — if pre-existing project had a single-tone alarm convention, the R2 Modernize categorization preserves it (mapped to one of the three categories) and generates the other two via the standard flow.

### 6. Subagent Workflows (BOOTSTRAP Phase 7 equivalent — includes Skills and Commands)

Required outputs in `.claude/agents/`, `.claude/skills/`, `.claude/commands/`:

- ✓ **Standard subagents** — `implementer`, `reviewer`, `integrator`, plus any others BOOTSTRAP produces by default.
- ✓ **Standard skills** — full BOOTSTRAP set: `spec-new`, `spec-review`, `spec-decompose`, `plan-review`, `code-review`, `spec-validate`, `quiet`, `quiet-task-done`, plus archetype-conditional skills.
- ✓ **Standard commands** — `/checkpoint`, `/spec-new`, `/spec-decompose`, `/plan-review`, etc., per BOOTSTRAP.
- ✓ **Per-task workflow** — same gates BOOTSTRAP produces (spec-new → spec-review → spec-decompose → plan-review → implement → code-review → spec-validate).
- ✓ **Worktree isolation** — `implementer` subagent uses isolated worktrees per BOOTSTRAP. Worktree resource budgeting documented (per G16) for projects over 1GB.
- ✓\* **Project-evolved per-task workflow** — if pre-existing project has an evolved workflow (e.g., a multi-step ticket workflow with research-variant + workflow-compliance role), R2/R8.C may preserve it as INTENTIONAL VARIATION with documented rationale.
- ✓\* **Retrofit-specific subagents/skills** — as preserved from prior art (e.g., a `workflow-compliance` subagent if pre-existing).
- ✓\* **Autonomous-mode scaffolding** *(v1.6.0)* — if the operator opted into any autonomous mode, R8.G/R8.H/R8.I scaffolding is present, **default-disabled**, with brownfield trust milestones recorded in `.retrofit-state.json` and surfaced in R7. Equivalence is satisfied by correct *scaffolding* (loop/goal/queue wrappers, `spec-decompose` extensions, conditional `implementer` variants, drift-detector cooperation hook, CLAUDE.md addenda — all matching BOOTSTRAP Phases 9.5/9.6/9.7 shape), not by the modes being active. If the operator declined all autonomous modes, this row is ✗ (archetype-conditional / operator-declined), which is a valid non-failure per §"Validating Equivalence."

---

## Validating Equivalence

R7 Handoff produces an explicit equivalence checklist. Every checklist item in the six categories above is marked ✓, ✓\*, or missing. If any items are missing without justification — i.e., not justified by `.retrofit-state.json`'s `skip_decisions` field, by archetype-conditional inapplicability (e.g., eval gate for a CLI tool), by operator-declined autonomous modes (recorded as `autonomous_modes.loop_mode_opted_in` / `goal_supervised_mode_opted_in` / `queue_mode_opted_in` set to `false` in `.retrofit-state.json`), or by an INTENTIONAL VARIATION recorded in `tech.md` — the retrofit is incomplete and R7 returns to the relevant earlier phase.

The checklist becomes part of the R7 handoff artifact (`.claude/inventory/equivalence-validation.md`).

### Documented variations

The retrofit can produce a project that's not byte-for-byte identical to BOOTSTRAP's output, **provided** every divergence is recorded as INTENTIONAL VARIATION in `tech.md` with rationale. Examples that legitimately produce variations:

- A project's pre-existing N-step ticket workflow that the operator wants to preserve (variation in Subagent Workflows category).
- An operator-evolved audio alert sound that's culturally embedded; mapped to a BOOTSTRAP category but kept (variation in Audio Alerts category).
- A simpler model assignment for a specific skill where the project's risk profile justifies it (variation in Model Assignment).
- A non-standard steering doc layout justified by domain (variation in Steering Documents).

Variations require:

1. **Explicit operator acknowledgment** — recorded in `tech.md`'s Intentional Variations section.
2. **Rationale** — why this variation is correct for this project.
3. **Boundary** — what would invalidate the variation (e.g., "this 7-step workflow continues until/unless we add a second product, at which point we should reconsider").

---

## Project Archetypes (Retrofit Classification)

The protocol classifies your project in Phase R0.5 and uses the classification to decide which phases run, what questions get asked, what hooks are recommended, and what principles starter set applies. **Where BOOTSTRAP classifies from a PRD interview, RETROFIT classifies from code analysis** — the inventory built in R0 is the input, with operator confirmation rather than operator-driven discovery.

| Archetype | Code-evidence signals (what the inventory looks like) | Examples | Required PRD tier | Notes |
|---|---|---|---|---|
| **CLI tool** | Single binary or top-level entrypoint script; no web framework deps; minimal/no DB; few or no Dockerfiles; structure dominated by `cmd/` or `src/` with command modules | dev utilities, build tools, single-binary scripts | Micro | CI/CD simplifies to release flow only; spec-strategy default forward-only is almost always right |
| **Library / SDK** | `[project]` table in pyproject.toml or proper `package.json` with `main`/`types`; tests-to-source ratio high (>0.5); no Dockerfile / no deploy scripts; public API surface in `__init__.py` / `index.ts` | npm package, Python lib, internal shared module | Standard | Adds semver and public API discipline; no deploy environments; R5.5 deps-policy emphasizes runtime vs dev split |
| **Service / API** | One web framework dep (FastAPI/Express/Rails/etc); `routes/` or `handlers/`; one Dockerfile; deploy workflow in CI; no `templates/` | backend microservice, REST/GraphQL API, worker | Standard | Skips frontend conventions; R8.A wires service-typical hooks (test gate, lint, secrets, CI mirror) |
| **Full-stack app** | Web framework + `templates/` or `frontend/` or SPA build deps (vite, webpack, next); one or two deployable units | web app with frontend + backend + DB | Standard | All phases run fully; multi-runtime variation usually appears at the frontend/backend boundary |
| **Mobile app** | iOS/Android/Flutter/React Native project markers (Xcode workspace, Gradle, pubspec.yaml, app.json); store-deploy workflow files | iOS, Android, React Native, Flutter | Standard | Web deploy gates replaced by app store flow in R8.A; secrets handling adapted for mobile keystores |
| **Data / ML pipeline** | Notebook directories, training scripts, dataset path conventions, model artifact storage references; airflow/dagster/prefect deps; little or no auth; HTTP layer optional | ETL, training pipeline, inference service | Standard | Auth replaced by data access controls in R5.5; principles include reproducibility and drift detection; R0's stability cutoff treats notebooks differently |
| **AI / agent system** | LLM provider deps (anthropic, openai, openrouter); prompt files (`*.md`, `prompts/`, `agents/`); eval harness; cost-tracking dependencies; sometimes a memory backend (vector store, hindsight, etc.) | LLM-powered tool, multi-agent system, prompt-driven app | Standard | Adds prompt versioning, evals, cost tracking; R8.A includes eval gate; R5 principles include determinism boundaries |
| **Platform / multi-component** | Multiple Dockerfiles, multiple `[project]` tables, multiple deployable units (services, plugins, adapters); subsystem boundaries visible in directory structure; per-subsystem CI workflows | products with multiple deployable units, monorepo platforms | Full | All phases, possibly run per component; **R2 categorization is per-subsystem by default** (not opt-in like for other archetypes); reframes the multi-runtime variation question as "for each component" |
| **Other** | Doesn't match any signature above; mixed signals | browser extensions, games, firmware, plugins, hybrid systems | Standard (default) | R0.5 runs the dimension interview using inventory signals to build a synthetic profile |

**PRD tiers** (same as BOOTSTRAP — terminology is shared so operators move between protocols cleanly):

- **Micro PRD** — one page, ~10 minutes. Problem, primary user, success criterion, scope. For projects with a single owner and casual maintenance.
- **Standard PRD** — 3–5 pages, 30–60 minutes. Adds personas, user journeys, non-goals, dependencies, risks. For projects maintained for months with multiple stakeholders.
- **Full PRD** — multi-section, several hours. Adds market context, competitive analysis, phased rollout, metrics framework, per-component scoping. For platforms or anything with cross-team dependencies.

**For retrofit specifically:** the PRD tier sets a *target* for what `product.md` should reach, not a hard requirement. R1 may discover an existing PRD that meets or exceeds the target tier (in which case `product.md` is a thin pointer doc). R1 may discover sparse signals far below the target tier (in which case `product.md` is heavily inferred and the operator is recommended to author a proper PRD post-retrofit). Either is acceptable — what's not acceptable is silently producing a `product.md` *below* the archetype's required tier without surfacing the gap.

### How classification flows through the protocol

| Phase | What classification changes |
|---|---|
| **R1** | PRD strategy decision references the archetype's required tier. If existing PRD content < target tier, R1 surfaces the gap and recommends post-retrofit PRD work. |
| **R2** | Question sets are archetype-aware. Service/API gets observability questions; Library/SDK gets public-API stability questions; AI/agent gets prompt versioning questions. **Platform: per-subsystem categorization is default, not opt-in.** |
| **R3** | Debt severity rubric varies. AI/agent: prompt drift is high-severity. Service/API: missing test coverage on routes is medium-to-high. Library: backward-compat regressions are high-severity. |
| **R5** | Principles starter set varies by archetype. Examples: CLI → minimal flag-handling rules; Service/API → idempotency + graceful degradation; AI/agent → determinism boundaries + cost discipline; Platform → cross-component contract preservation. |
| **R5.5** | Deps-policy questions vary. CLI with stdlib only → may skip dep-vetting workflow entirely. Library → strict semver discipline. AI/agent → LLM provider lock-in question. Platform → per-manifest policies. |
| **R8.A** | Hook recommendations vary. CLI → no CI mirror needed if no CI. Service/API → spec gate + test gate + secrets + CI mirror. AI/agent → +eval gate + prompt-file watcher. Platform → per-subsystem hook configuration. |
| **R8.F (CI/CD)** | Conditional on CI/CD existence (per archetype). |
| **R8.G/H/I (autonomous modes)** | Opt-in regardless of archetype; default-skip. If opted in, scaffolded default-disabled and gated on the brownfield trust milestone (see §"Autonomous Modes in Retrofit"). Archetype affects only the per-task eligibility classifier defaults inside the scaffolding (e.g., AI/agent prompt files get prompt-pinning-eval gating), not whether the modes are offered. |

### "Other" archetype — synthetic profile from inventory dimensions

When R0.5 cannot match the inventory to one of the named archetypes, it builds a **synthetic archetype profile** from inventory dimensions. The profile is a structured object the AI writes into `.claude/.retrofit-state.json`:

```json
{
  "archetype": "other",
  "synthetic_profile": {
    "user_facing_surface": "tui|api|cli|gui|browser_ext|none",
    "deploy_targets": ["vps","app_store","desktop","embedded","none"],
    "language_runtime_count": 1,
    "primary_language": "rust",
    "deployable_unit_count": 2,
    "external_inference_deps": false,
    "external_storage_deps": ["local_fs"],
    "test_framework_present": true,
    "ci_present": true,
    "auth_present": false,
    "secrets_present": false,
    "closest_archetype": "cli_tool",
    "deviations_from_closest": [
      "has GUI shell (Tauri)",
      "uses sqlite for local persistence (not stdlib only)"
    ]
  }
}
```

Phases that ask archetype-conditional questions consult `synthetic_profile.closest_archetype` first, then check `deviations_from_closest` to decide whether to add or skip questions. Operator can override any field.

### Notes for the AI on classification confidence

When R0.5 proposes an archetype, it must also surface a **confidence indicator**:

- **HIGH** — code evidence matches multiple signals from one archetype's signature; operator confirmation is essentially formality.
- **MEDIUM** — code evidence matches the dominant archetype but with notable variation (e.g., a Service/API that *also* has substantial frontend templates suggesting Full-stack drift). Operator confirmation matters; consider Modernize discussions for the variation.
- **LOW** — code evidence is mixed or sparse. Default to running the synthetic-profile interview ("Other" path) rather than guess.

Confidence is recorded in `.retrofit-state.json` alongside the archetype. R2/R5 can consult it when deciding how much to push back on operator overrides — a HIGH-confidence classification with an operator override of a different archetype is a strong signal to slow down and surface the discrepancy in conventions.

### Per-Archetype Strangler & Spec Patterns (G15)

Each archetype has a characteristic shape for safe brownfield modernization. R2/R4/R5/R8.A reference this table when archetype-specific guidance is needed.

| Archetype | Strangler approach | Active spec patterns | Hook focus | Per-archetype skills |
|---|---|---|---|---|
| **CLI tool** | Rarely needed at this scale; incremental refactor sufficient | Change specs only | Standard set; consider commit-message + version-tag check | Standard set |
| **Library / SDK** | Re-export-then-deprecate: new module created; old module re-exports from new; eventually old removed | Change specs + dependency boundary specs (public API surface IS the boundary) | Standard set + public API stability gate (defined in R8.A.3); consider semver discipline gate, deprecation-warning checker | + `boundary-spec` for public API |
| **Service / API** | **Classic strangler fig** — façade/proxy in front, extract endpoints incrementally, dual-write during transition, anti-corruption layer (G19) for legacy contracts | Change specs + dependency boundary specs (OpenAPI) + migration specs | Standard set; consider boundary-contract validation hook (e.g., swagger-cli on contract files), database migration checker | + `boundary-spec`, `migration-plan` |
| **Full-stack app** | Service/API patterns for backend; route-by-route or component-by-component cutover for frontend | Change specs + frontend/backend contract specs + migration specs | Service/API hook focus + consider frontend lint, accessibility checker | + `boundary-spec`, `migration-plan` |
| **Mobile app** | Less applicable; "modernize alongside via flag-gated experiments" is more typical | Change specs + offline-mode behavior specs | Standard set + mobile store-deploy gate (defined in R8.A.3); consider version-bump checker, keystore safety, store metadata validation | Standard set |
| **Data / ML pipeline** | "Refactor pipeline stage by stage with idempotency guarantees" (less applicable than strangler fig proper) | Change specs + dataset-version specs + model-artifact specs | Standard set; consider notebook-output cleaner, reproducibility checker, data-lineage validator | + `dataset-pin-test` |
| **AI / agent system** | **Prompt-version routing** — new prompts go to a percentage of traffic, evaluated against a golden dataset, gradually rolled out (the routing layer IS the anti-corruption layer) | Change specs + prompt-version specs + eval-baseline specs (the *characterization eval* — analog of pinning tests for prompts) | Standard set + eval gate (defined in R8.A.3); consider prompt-version-bump checker, cost-budget hook | + `prompt-pinning-eval` (characterization eval generator) |
| **Platform / multi-component** | **Per-component cutover** — one component at a time fully retrofitted; others remain "not yet retrofitted" with explicit allowlisting | Change specs per component + dependency boundary specs for cross-component contracts + migration specs platform-wide | Standard set + cross-component contract gate (defined in R8.A.3); consider selective-build awareness, per-component CI mirror | + `boundary-spec` (per-component), `migration-plan` |
| **Other (synthetic profile)** | Consult `closest_archetype`'s pattern; document deviations | `closest_archetype` set + deviation-specific | `closest_archetype` set + deviation-specific | Standard set + deviation-specific |

**Notes:**

- **Anti-corruption layer (ACL)** *(G19, Evans / Fowler)* — the translation layer that prevents legacy concepts from leaking into the new domain model. Architecturally: the proxy in Service/API; the new module in Library/SDK; the prompt routing layer in AI/agent. Where a strangler-fig migration is in flight, an ACL is implicit.
- **Resource budgeting for parallel worktree workflows** *(G16)* — Augment Code 2026 reports that a 2GB codebase consumes ~10GB of disk in a 20-minute multi-worktree session. For codebases over 1GB, R8.C subagent definitions document the resource expectation; sequential worktrees may be preferable to parallel for very large codebases.
- **Production-traffic bootstrap** *(G18, GitHub SAML hardening case study)* — for Service/API and AI/agent archetypes that have production traffic, capturing sampled traffic as input to dependency boundary spec authoring is preferable to guessing from code. R0 step 11 surfaces this for applicable archetypes.

---

## Model Assignment Strategy & Portfolio Awareness

**Moved to `RETROFIT-COMPANION.md`.** The opinionated per-skill / per-subagent model table (including the v1.3+ retrofit-specific skills and the Pro-tier fallback) and the Portfolio Awareness guidance are reference material the wizard consults, not executes. See `RETROFIT-COMPANION.md` §“Model Assignment Strategy” and §“Portfolio Awareness”. The rule “always set `model:` explicitly on subagents” remains in §“Protocol rules for the AI” below because it is an execution rule.

---

## Phase R-1 — Prerequisite Check

**New in v1.1.** v1.0 said "no git = unsupported" but didn't define what "supported" actually means or what to do when the prerequisite isn't met. R-1 makes the check explicit and offers a degraded-mode path rather than a hard abort.

**Goal:** Verify the protocol's assumptions before any other work happens. Decide on full / degraded / abort.

**AI actions:**

1. **Filesystem and tooling check.** Verify:
   - AI has filesystem write access to the project root.
   - AI can read all of the existing codebase (no permission walls).
   - AI can execute shell commands (for git log analysis, dependency scans, etc.).
   - `jq` is available (most hooks parse JSON; fall back to Python's `json` module if not). If neither, flag — Phase R8 hook installation will work around it but lint output is uglier.

2. **Git state check.** Three branches:
   - **Full mode (default):** `.git/` is present, `git status` works, history is intact. All retrofit phases run normally.
   - **Degraded mode (no git, or partial git):** `.git/` is absent or `git log` fails. The operator can choose to proceed with degradation, or to `git init` first and re-run R-1. **What's lost in degraded mode:**
     - R0's `git-history.md` cannot be produced (no commits, no contributors, no hotspots).
     - R0's stability proxy (calibrated cutoff for "files unchanged for X period") cannot run; the inventory captures this as "stability signal unavailable."
     - R5.5's historical secret-leakage scan loses its highest-value mode (scanning git history for committed-then-removed credentials). Present-tree-only scan still works.
     - R2's Deprecated categorization is thinner — without `git blame` you can't tell if a "deprecated pattern" is recent code drift vs ancient legacy. Operator confirms by hand.
     - R8's spec-gate-commit hook still installs but the "blocked file is not in any active spec" check has no commit history to compare against — it operates on staged-vs-tree only.
   - **Abort:** the project doesn't have `.git/`, the operator doesn't want to `git init`, and degraded mode is unacceptable to them. Stop. Recommend the operator initialize git (or another VCS the AI can read) and return.

3. **Working tree state check.** Run `git status --short` (full mode only). If the working tree has uncommitted changes:
   - Show the operator the list. Ask: "These are uncommitted local edits. The retrofit treats HEAD as canonical and ignores working-tree changes. Proceed, or commit/stash first?" Do not silently treat WIP as canonical.
   - Note in `.claude/.retrofit-state.json` the SHA of HEAD that the retrofit is operating against, so any later question of "is this working tree drift" can be answered.

4. **Source-file count calibration.** Run a quick scope audit using a generic exclude list:
   ```
   git ls-files | grep -vE '^(docs/|tickets/|tutorials/|examples?/|samples?/|vendor/|node_modules/|\.venv/|venv/|env/|generated/|\.scratch/|build/|dist/|target/|out/)' | wc -l
   ```
   - Adjust the exclude list with the operator if their project has unusual conventions (e.g., a `research/` directory of non-source markdown).
   - **Source-file count under 500:** small-to-medium scope. Protocol fits cleanly.
   - **500–2000:** flag to operator. R2 convention reckoning will need 2–3x the time. Recommend running R2 across multiple sessions with `/checkpoint` between them. Continue.
   - **Over 2000:** stop. Out of scope for this protocol version. Recommend a pre-R0 interview phase with the operator to constrain scope before proceeding (e.g., "retrofit the auth subsystem first, expand later").

5. **Repo-age calibration.** Compute repo age:
   ```
   first_commit=$(git log --reverse --format='%ai' | head -1)
   age_days=$(( ( $(date +%s) - $(date -d "$first_commit" +%s) ) / 86400 ))
   ```
   - Note the age. The R0 inventory uses this to calibrate the stability cutoff: `stability_cutoff_days = min(365, age_days / 3)`. Document the calibration in `git-history.md`.
   - **Repo younger than 30 days:** the stability proxy is useless; mark it "not applicable" in the inventory and rely on operator judgment for "Do Not Touch" candidates.

6. Write `.claude/.retrofit-state.json` with: mode (full/degraded), HEAD SHA, source-file count, repo age in days, calibrated stability cutoff, working-tree dirty flag, jq availability flag. Subsequent phases read this.

**Exit criteria:** Mode decided. State file written. Operator has confirmed scope is in protocol bounds.

---

## Skip Policy

- **Required (cannot skip):** R-1, R0, R0.5, **R0.7** *(v1.4)*, R1, R2, R3, R4, R5, R5.5, R8.A (Hooks), R8.B (Tools/MCP), R8.C (Skills/Commands/Agents), R8.E (CLAUDE.md).
- **Required sub-steps within R0** *(v1.3+v1.4)*:
  - R0 step 8 (DORA baseline metrics) — mandatory; even "all unavailable" is a recorded result.
  - R0 step 10 (regulatory regime detection) — mandatory; takes 30 seconds for unregulated projects.
  - R0 step 11 (production traffic capture) — required only for Service/API and AI/agent archetypes; skipped silently for others.
  - **R0 step 12 (PM tooling indicator scan) — mandatory** *(v1.4)*; output feeds R0.7. Cannot skip — without it, R0.7 has no input.
- **Skippable on operator request (decided in R0.5 step 7):** R6 (Smoke test on existing module), **R0.8 (Preview & Commitment — operator may opt out if confident in scope)** *(v1.4)*, R8.D (Spec versioning — same skip rules as BOOTSTRAP 7.5), R7's "smoke test on new feature" sub-step.
- **Optional (recommended, may decline)** *(v1.3)*:
  - R0 step 9 (tribal knowledge interview) — strongly recommended for projects with prior maintainers; declinable if operator is sole contributor and prefers not to.
  - R5 step 3.5 (EARS notation guidance) — recommended not mandated; operator may choose alternative requirements syntax.
- **Required but archetype-conditional:**
  - **R5.5 dependency vetting** — skipped if the synthetic profile / archetype confirms the project has only stdlib dependencies (rare, but applies to some CLI tools and pure-stdlib scripts).
  - **R5.5 secrets handling** — skipped only if the synthetic profile / archetype confirms no secrets present anywhere (no env files, no auth, no API integrations). For most projects this is **not** skippable; the historical secret-leakage scan still runs in degraded mode.
  - **R8.F (CI/CD)** — required if the project has CI/CD, otherwise opt-out; if opt-out, produces a minimal `ci-cd.md` recording the decision plus the test command.
  - **R8.A eval gate hook** — recommended only for AI/agent system archetype; skipped silently for others.
  - **R8.A CI mirror hook** — recommended only if R8.F is not opt-out (no point mirroring CI that doesn't exist).
- **Required-when-applicable** *(v1.3)*:
  - **R5 step 3 → `contracts.md`** — required when R4 step 3 identified active dependency boundary spec patterns (typical for Service/API, Library/SDK, Full-stack, Platform).
  - **R5 step 3 → `migration.md`** — required when R4 step 3 identified active migration spec patterns (typical when in-flight modernization is detected).
  - **R5 step 3 → `compliance.md`** — required when R0 step 10 detected one or more applicable regulatory frameworks.
- **Opt-in, default-skip** *(v1.6.0 — autonomous modes)*:
  - **R8.G (Autonomous Loop Mode)** — opt-in only. If opted in, scaffolding is generated but default-disabled and gated on the R8.G brownfield milestone (see §"Autonomous Modes in Retrofit"). Default skip.
  - **R8.H (Goal-Supervised Mode)** — opt-in only; independent of R8.G. Same scaffold-but-defer treatment with the stricter R8.H milestone. Default skip.
  - **R8.I (Autonomous Queue Mode)** — opt-in only; **requires R8.G or R8.H to also be opted in** (same gate as BOOTSTRAP 9.7). Scaffold-but-defer with the strictest R8.I milestone. Default skip. The wizard refuses to scaffold queue mode if neither R8.G nor R8.H was opted into, and refuses to *enable* it at retrofit time regardless.

If the operator requests skipping a required phase, the AI states why the phase is required and asks for explicit override acknowledgment. Only then proceeds.

---

## Phase R0 — Inventory & Audit

**Goal:** Build a snapshot of what exists. This is the retrofit equivalent of "knowing your starting state" — without it, every subsequent phase is guessing.

**AI actions:**

1. **Existing `.claude/` check.** If `.claude/` exists, read `.bootstrap-state.json` and `.retrofit-state.json` if present. Four branches:
   - **Complete previous bootstrap (state file present, marked complete):** stop and ask: "This project already has a complete `.claude/`. Why retrofit? (Refresh / fix specific phase / start over)" Don't proceed without explicit reason.
   - **Incomplete bootstrap or retrofit:** offer to resume from where it stopped, or start over.
   - **No state file but `.claude/` exists with protocol-known directories** (`agents/`, `skills/`, `commands/`, `sessions/`, `hooks/`, `steering/`): treat as legacy partial setup; archive existing `.claude/` to `.claude.archived-<timestamp>/` before proceeding. **Read all archived contents during R0 step 6 (prior-art audit) — do not assume archived = noise.**
   - **No state file but `.claude/` exists with unknown directories** (e.g., `roles/`, `personas/`, custom subdirs): also archive, but flag explicitly that the archive contains non-protocol layouts. The R0 step 6 prior-art audit gives these elevated attention because they represent operator-invented conventions that may be candidates for portfolio standardization or local-canonical preservation.

2. **Portfolio scan (if applicable).** Ask: "Is this part of a portfolio of projects with shared conventions?" Three answers:
   - **Yes, here's the path:** read sibling project's `.claude/` directory. Sessions schema, hook structure, command names, agent definitions, audio alert config become **portfolio defaults** that this retrofit reuses unless overridden.
   - **Yes, but this is the first one being retrofitted:** treat this retrofit as establishing the portfolio reference. Note this in the inventory; R7 handoff will ask which conventions to canonicalize for portfolio.
   - **No / standalone:** skip portfolio integration entirely.

3. **Codebase scan.** Run a structured audit and write the results to `.claude/inventory/`. Cite the files you read for every conclusion:
   - **`structure.md`** — top-level directory tree, file count and LOC per top-level directory (using a source-eligible extensions filter), top-level files, notable absences (no package.json on a clearly Node-flavored project, etc.). For multi-component projects, identify each subsystem separately.
   - **`languages.md`** — language file-count breakdown, build/manifest files detected (with absences flagged), declared language version vs target-version-in-tooling discrepancies, Dockerfile count for multi-container architectures.
   - **`dependencies.md`** — manifest contents (one section per manifest file — there may be several in multi-component projects), pinned-vs-unpinned ratios, upper-bound presence/absence patterns, inline ticket-reference comments (these are often valuable convention evidence for R2). **Outdated-package scan:** if network access is available, run the package manager's outdated-check (`pip list --outdated`, `npm outdated`, etc.) and capture results. If no network, document the exact command for the operator to run locally and capture results in v1.1 of `deps.md` after R5.5.
   - **`testing.md`** — test framework(s), test file count, total test-function count (rough proxy via `^def test_` or equivalent), conftest/fixture files, name-matching coverage (% of source modules with a name-matching test file), coverage tool detection (or absence). For modules without name-matching tests, note them but qualify: "exercised level unknown — name-match is a strict proxy."
   - **`git-history.md`** — first/last commit dates, total commits, contributor count (collapse same-person multi-identity), top-25 hotspots by changes, files unchanged within the calibrated stability cutoff (`min(365 days, repo_age / 3)` — document the cutoff applied), files modified in last 7 days (active areas — bad first-spec candidates), branch state and merge artifacts. **Skipped in degraded mode** with a stub file noting why.
   - **`conventions.md`** — observed patterns and inconsistencies. The single most important file in the inventory. For each observed pattern, write evidence with raw counts and locations. Group as:
     - **Strongly canonical** (clean, single pattern, easy R2 calls) — examples: async-first routes, single test framework, single linter.
     - **Patterns with potential variation** (the meat of R2) — examples: type hint coverage that lags policy, multi-pattern error handling, function-length outliers.
     - **Multi-runtime / intentional variation candidates** — for projects with distinct subsystems (e.g., HTTP routes + background workers + protocol implementations + adapters), enumerate each subsystem and note where its conventions are likely to legitimately diverge from the others. **R2 directive: do not flatten this variation.**
     - **Existing tooling investment** — what conventions are already enforced via lint config, CI workflows, pre-commit, etc. R5/R8.F won't be a blank slate for these.
     - **Findings to surface to R2 explicitly** — a numbered list at the end with the questions R2 needs to resolve.

4. **Implicit-PRD scan (input to R1).** Look for product context in: README files, `docs/` (especially anything with "PRD," "spec," or "architecture" in the name), marketing or app-store text in the repo, top-level CLAUDE.md, CHANGELOG.md, top-level comments. Compile findings into `.claude/inventory/product-signals.md` with sections for: authoritative documents (with status — version, date, currency), reconstructed product summary (with citations), forward direction (if discernible from changelog or branch names), tech stack (with verification source), and convention sources baked into product/agent docs.

5. **Existing CLAUDE.md content scan (input to R8).** If a root `CLAUDE.md` exists, read it section by section. For each section, classify provisionally:
   - **Belongs in steering doc X** (e.g., a "Tech Stack" section in CLAUDE.md belongs in `tech.md`).
   - **Belongs in agent prompt Y** (e.g., review checklists in CLAUDE.md belong in `code-review` skill or a review-stage agent).
   - **Belongs in audio-alert/hook config** (e.g., an "operator attention cue" convention belongs in audio-alerts config and hook scripts).
   - **Deprecated** (no longer relevant — flag for `debt.md`).
   - **Keep in thin CLAUDE.md** (the core invariants and pointers — usually 3–5 sections at most).
   - Write the results to `.claude/inventory/claude-md-extraction-plan.md`. R8.E uses this as input.

6. **Prior-art audit.** If `.claude.archived-<timestamp>/` exists (from step 1), read every file in it. For each:
   - Note its purpose, the convention it codifies, and any cross-references to project docs.
   - Classify provisionally for R2: Canonical / Deprecated / Intentional Variation / Modernize / Replace.
   - Note it in `.claude/inventory/prior-art.md` with a paragraph per file. R2 uses this as input alongside `conventions.md`.

7. Show the operator the inventory. Ask: **approve / fill-in-gaps / start over**. The inventory is the single biggest leverage point for retrofit quality — don't rush past it.

8. **Baseline metrics capture (G9 — DORA-derived).** Capture pre-retrofit values for the metrics that retrofit success will be measured against. Without a baseline, the retrofit can't be evaluated for whether it produced the expected benefit (faster merges, fewer regressions, growing spec coverage).
   - **Lead time for changes** — median time from commit to deploy for the last 30 commits where deploy date is determinable (deploy CI runs, release tags, etc.). If untraceable, mark "unavailable, baseline = unknown."
   - **Change failure rate** — count of rollbacks, hotfixes, or "fix" / "revert" commits in the last 90 days as a proportion of all production-affecting changes.
   - **Test coverage** — current coverage percentage from existing tooling, if any. Mark "no coverage tooling" if absent.
   - **Lint conformance rate** — percentage of source files that pass current lint config without modification. Compute this as part of R0 step 4 (testing inventory).
   - **Spec coverage** — for retrofit, this starts at 0% (no specs exist yet). Recorded as the starting denominator.
   - Write `.claude/inventory/baseline-metrics.md`. R7 references this in the post-retrofit measurement schedule.
   - **DORA performance tier classification** *(per 2024 DORA report cited in research-findings.md)*: Elite (lead time < 1 hr, change failure < 2%) / High (< 1 day, < 4%) / Medium (1 day–1 week, 8-16%) / Low (> 1 month, > 32%). Surface to operator: "your project's current tier is X; retrofit aims to maintain or improve it, never to regress."

9. **Tribal knowledge interview (G17, optional but strongly recommended).** Five-question interview to capture knowledge that lives in operators' heads, not in files. Output: `.claude/inventory/tribal-knowledge.md`. Some answers become `debt.md` entries; some become "Do Not Touch" candidates in `tech.md`; some become escalation criteria in CLAUDE.md.
   1. **DO NOT TOUCH list** — "Which files would you tell a new contributor 'DO NOT touch without consulting [person]'?" Captures landmines.
   2. **Sleeping bugs** — "Which behavior is technically broken but everyone has agreed not to fix because users depend on it?" Captures backwards-compat constraints.
   3. **Magic configs** — "Which configuration value, if changed, would break something nobody currently understands?" Captures risk concentrations.
   4. **War stories** — "Which postmortem stories would you tell a new contributor on day one to prevent them repeating the lesson?" Captures the painful-but-instructive past.
   5. **3am calls** — "Which person would you call at 3am if a specific subsystem failed?" Captures bus-factor risks per-subsystem.
   - Recommend that war stories be encoded as **narrative tests** *(Jackson Bennett style)* — `test_no_database_migrations_during_business_hours_after_the_great_crash_of_2024()` carries the story directly in the test name and runs on every commit.

10. **Regulatory regime detection (G20.1 — lite, v1.3 scope, MANDATORY).** Determine which regulatory frameworks apply to the project. **This step is mandatory** even for projects with no applicable frameworks — without it, R5 step 3 doesn't know whether `compliance.md` is needed. For unregulated projects, this step takes ~30 seconds (seven quick "no" answers). The detection enables R5 to produce a `compliance.md` steering doc; R8.A may add regime-specific hooks (deferred to v1.4 for full enforcement, but the steering surfaces the constraints). Seven yes/no questions:
    1. Does the system process personal data of EU residents? *(GDPR — Article 25 Data Protection by Design and by Default applies, including to existing systems.)*
    2. Does the system process PHI / handle US healthcare data? *(HIPAA — four technical safeguard categories per §164.312: Access, Audit, Integrity, Transmission.)*
    3. Does the system process payment card data? *(PCI-DSS v4.0.1 — Requirement 6 covers software development.)*
    4. Is the system itself a medical device or part of one? If yes, what safety class — A, B, or C? *(IEC 62304 + ISO 13485 — software safety class drives all process rigor; traceability matrices required.)*
    5. Does the system serve US federal agencies? If yes, what FedRAMP impact level? *(FedRAMP — continuous monitoring + significant change documentation required.)*
    6. Is the AI/ML system FDA-regulated? *(FDA AI/ML PCCP — December 2024 final guidance covers predetermined change control plans.)*
    7. Is the project in or pursuing SOC 2 certification? *(SOC 2 Type II — 6-12 month continuous-control-operation evidence window.)*
    - Output: `.claude/inventory/regulatory-context.md` — captures answers, lists per-framework retrofit risks (operator can also mark "evaluating" or "not yet but soon" for in-flight certifications).
    - For projects with no applicable frameworks, this step takes ~30 seconds and `compliance.md` is not produced. For projects with one or more applicable frameworks, R5 step 3 produces `compliance.md`.

11. **Production traffic sample (G18, conditional).** Only for Service/API and AI/agent archetypes that have production traffic. Ask the operator: "Can you capture sampled production traffic for spec validation? (Yes / No / Unsure how to)"
    - **If yes:** the sample becomes input to R4's dependency boundary spec authoring. Operator captures and places at `.claude/inventory/traffic-sample.json` (or similar). Spec validation in R4/R5 verifies against this rather than guessing from code.
    - **If no:** R4 falls back to spec authoring from code only.
    - **If unsure:** suggest operator's API gateway, application logs, or analytics pipeline as candidate sources. Provide examples per archetype: nginx access logs for HTTP services; OpenTelemetry traces for instrumented systems; LLM provider response logs for AI/agent. This step takes minutes if a tool is in place; longer if not (don't block R0 on it — collect later if needed).

12. **PM tooling indicator scan (G21 — v1.4, MANDATORY).** Detect signals of project-management tooling in the codebase. R0.7 uses these signals as input. **This step is mandatory** because R0.7 needs to know what to ask about — without this scan, the AI may miss in-flight tickets, integration with Linear/Jira/GitHub Issues, or local ticket directories.
    - **In-repo ticket directories:** check for `tickets/`, `issues/`, `todos/`, `planning/`, `epics/`, `backlog/` at repo root. Capture file count and recency (last-modified within 30 days indicates active use).
    - **CI workflow integrations:** scan `.github/workflows/`, `.gitlab-ci.yml`, `.circleci/`, `Jenkinsfile` for references to Linear API, Jira API, GitHub Issues automation, or similar PM tool calls. Common patterns: `LINEAR_API_KEY`, `JIRA_TOKEN`, `gh issue create`, `linear/action-create-issue`.
    - **Commit message conventions:** sample the last 100 commits for ticket-reference patterns (`PROJ-123`, `#42`, `[TICKET-456]`, `Linear: ABC-789`). Capture which patterns appear and at what frequency.
    - **Repo-side issue tracker activity:** if running on a GitHub-hosted repo, note presence of open issues in the repo (the operator can confirm count). If GitHub MCP is available, count open vs closed.
    - **Project documentation cross-references:** grep README, CONTRIBUTING.md, docs/ for "linear.app", "atlassian.net", "github.com/.*/issues", "shortcut.com", "asana.com", "notion.so/.*tasks", "trello.com" — capture URLs found.
    - **PR template integration:** check `.github/pull_request_template.md` and similar for ticket-link conventions.
    - Output: `.claude/inventory/pm-tooling-signals.md` listing all signals found with counts and recency. This becomes R0.7's primary input.
    - **Note:** this step does NOT decide source-of-truth or transition path — that's R0.7's job. R0 step 12 only gathers evidence.

**Exit criteria:** `.claude/inventory/` populated with all expected audit files (six core + `prior-art.md` if archived `.claude/` existed + `claude-md-extraction-plan.md` if root CLAUDE.md existed + `baseline-metrics.md` (mandatory) + `regulatory-context.md` (mandatory) + `pm-tooling-signals.md` (mandatory) + `tribal-knowledge.md` if interview done + `traffic-sample.json` if production-traffic capture applies and operator provided sample). Operator has reviewed and either approved or filled in gaps the AI couldn't detect.

---

## Phase R0.5 — Classification

**New in v1.2.** Mirrors BOOTSTRAP §0 step 3–4 (archetype matching + synthetic profile for "Other"), but classifies from the R0 inventory rather than from a PRD interview. Sits here because the inventory is the input and R1+ behavior depends on the result.

**Goal:** Determine the project archetype, decide PRD tier target, capture archetype-conditional decisions early so downstream phases adapt without backtracking.

**AI actions:**

1. **Propose an archetype** based on inventory evidence. For each archetype in the matrix above (§"Project Archetypes"), score the project's match strength against the signature signals. Examples:
   - **CLI tool match check:** Does `inventory/structure.md` show a `cmd/` or single-entrypoint structure? Does `inventory/languages.md` show no web framework deps? Does `inventory/git-history.md` show a deploy workflow that's just release tags or none?
   - **Service/API match check:** Does `inventory/dependencies.md` show one web framework? Does `inventory/structure.md` show `routes/` or `handlers/`? One Dockerfile? CI workflow includes `deploy`?
   - **Platform / multi-component match check:** Does `inventory/structure.md` show multiple Dockerfiles? Multiple `[project]` tables? Multiple deployable units? Per-subsystem CI workflows in `.github/workflows/`?
   - **AI/agent system match check:** LLM provider deps in `inventory/dependencies.md`? Prompt files (`prompts/`, `agents/`, `*.md` with role definitions) in `inventory/structure.md`? Cost-tracking deps?

2. Output the archetype proposal with **confidence indicator** and **evidence cited**:
   ```
   Proposed archetype: Platform / multi-component
   Confidence: HIGH

   Evidence:
   - 5 distinct Dockerfiles (Dockerfile, Dockerfile.dashboard, adapters/slack/Dockerfile,
     adapters/telegram/Dockerfile, metrics-collector/Dockerfile) — see inventory/structure.md
   - 2 Python [project] tables (root absent intentionally; plugins/agenticfuse-compliance-hook
     has its own) — see inventory/languages.md
   - 14 GitHub Actions workflows with multiple deployment paths — see inventory/git-history.md
   - Multi-runtime evidence: app/fuse/, hermes/, hindsight/, openclaw/ references
     across 50+ source files — see inventory/conventions.md "Multi-runtime / intentional variation"
   ```

3. Show the proposal to the operator. **Three response paths:**
   - **Confirm:** archetype is correct → proceed to step 5.
   - **Override:** operator picks a different archetype from the matrix → record both proposed and chosen, surface any conventions in the inventory that don't match the chosen archetype as discussion items for R2 (high-confidence proposal + operator override = real signal worth surfacing).
   - **Other:** operator picks "Other" or AI's confidence is LOW → run dimension interview in step 4.

4. **Dimension interview (only for "Other" path):** ask the operator a structured set of dimensions, with the inventory pre-filling answers wherever possible. The operator confirms or corrects each. Build a `synthetic_profile` per the §"Project Archetypes" schema. Save to `.retrofit-state.json`.

5. **Decide CI/CD applicability** (after archetype is set in step 3 or 4):
   - For most archetypes: ask explicitly. If no, mark R8.F as **opt-out** (R8.F still produces a minimal `ci-cd.md` recording "no CI/CD" as an explicit decision plus the test command, but skips pipeline configuration).
   - **Inventory hint:** if `inventory/git-history.md` cited existing `.github/workflows/` or similar, default the answer to "yes" with operator confirm.

6. **Decide PRD tier target** (per the matrix's Required PRD tier column for the chosen archetype). Operator can request a higher tier but not a lower one. The tier sets the target for R1's `product.md`; R1 surfaces a gap if the existing PRD content is below the target.

7. **Surface skippable-phase decisions early** (mirrors BOOTSTRAP §0 step 6):
   - R8.D (Spec Versioning Protocol) — skippable for solo, short-lived projects regardless of archetype.
   - R6 (Smoke Test on Existing Module) — skippable on operator request.
   - **R0.8 (Preview & Commitment) — skippable on operator request** *(v1.4)*. Recommend running unless the operator has retrofitted before and is confident in scope.
   - R5.5 Secrets sub-section — skippable only if synthetic profile / archetype confirms no secrets.
   - **R8.G / R8.H / R8.I (autonomous modes) — opt-in, default-skip** *(v1.6.0)*. Surface the three independently (with the R8.I-requires-R8.G-or-R8.H gate). Use this verbatim framing: *"These add unattended execution. For a brownfield project they are NOT enabled at retrofit time even if you opt in now — the wizard scaffolds them default-disabled and records a brownfield trust milestone (gate-trustworthiness, not task count) that must be met before you turn them on. See §'Autonomous Modes in Retrofit'. Opt in to scaffold-now-enable-later, or skip to not scaffold at all."* Record the opt-in intent (not enablement) in `.retrofit-state.json`.
   For each skippable phase, ask: **run / skip / defer-decision**. Record decisions in `.retrofit-state.json`.

8. **Write classification to `.retrofit-state.json`.** Schema additions (extending the v1.1 R-1 state file):
   ```json
   {
     "archetype": "platform_multicomponent",
     "archetype_proposed": "platform_multicomponent",
     "archetype_confidence": "high",
     "archetype_evidence": [
       "5 distinct Dockerfiles",
       "2 Python [project] tables",
       "14 GitHub Actions workflows",
       "multi-runtime evidence across 50+ source files"
     ],
     "synthetic_profile": null,
     "prd_tier_target": "full",
     "ci_cd_applicability": "yes",
     "bootstrap_protocol_version": "1.9.0",
     "loop_mode_enabled": false,
     "goal_supervised_mode_enabled": false,
     "queue_mode_enabled": false,
     "loop_in_flight": [],
     "goal_in_flight": [],
     "queue_runs_history": [],
     "skip_decisions": {
       "R5_5_secrets": "run",
       "R6_smoke_test": "decide_later",
       "R8_D_spec_versioning": "decide_later"
     },
     "autonomous_modes": {
       "loop_mode_opted_in": false,
       "goal_supervised_mode_opted_in": false,
       "queue_mode_opted_in": false,
       "brownfield_milestones": {
         "rollout_steady_state_spec_test_gate": false,
         "rollout_steady_state_all_hooks": false,
         "touch_based_specs_under_blocking_gates": 0,
         "touch_based_specs_threshold": 10,
         "legacy_allowlist_size_at_retrofit": null,
         "legacy_allowlist_current_size": null,
         "legacy_allowlist_shrink_threshold_pct": 25,
         "mode_selection_ledger_entries": 0,
         "weeks_real_per_task_operation_post_blocking": 0
       }
     }
   }
   ```
   **State-schema shape (v1.6.0 decision — true BOOTSTRAP shape-equivalence).** The three `*_enabled` flags and the three per-mode tracking lists (`loop_in_flight`, `goal_in_flight`, `queue_runs_history`) are **top-level**, exactly matching BOOTSTRAP's `.bootstrap-state.json` (BOOTSTRAP "Recovery & State" + Phase 0 step 9, and BOOTSTRAP-COMPANION "Migration notes" which add these as top-level fields). Only the RETROFIT-novel fields — the three `*_opted_in` intent flags and `brownfield_milestones` — are nested under `autonomous_modes`, since they have no BOOTSTRAP counterpart. The installer's `bootstrap.config.yaml` *input* schema nests the enable flags under an `autonomous_modes` key (see `lib/defaults.py`); that is the config-input layer, not the runtime state file, and does not govern this shape. Rationale: the equivalence target's "scaffolding matches BOOTSTRAP Phases 9.5/9.6/9.7 shape" claim is measured against BOOTSTRAP's *runtime state file*, which uses top-level flags; any BOOTSTRAP-shared tooling that reads the state file post-retrofit (once the operator enables a mode) finds the flags where BOOTSTRAP puts them. The `*_opted_in` flags record operator intent at R0.5; the `*_enabled` flags remain `false` through retrofit completion and are only flipped post-retrofit when the corresponding `brownfield_milestones` are satisfied (see §"Autonomous Modes in Retrofit" and R8.G/H/I). `bootstrap_protocol_version` is recorded as the BOOTSTRAP version this retrofit targets for equivalence (`"1.9.0"` for RETROFIT v1.6.0).

9. Show and ask: **approve / edit / start over**.

**Exit criteria:** Archetype recorded in `.retrofit-state.json` (named or "Other" with synthetic profile). PRD tier target set. CI/CD applicability decided. Skippable-phase decisions surfaced (decided or deferred). Operator has approved.

---

## Phase R0.7 — PM Artifact Reckoning (`workflow-source-of-truth.md`)

**New in v1.4.** **Mandatory.** No BOOTSTRAP equivalent — BOOTSTRAP greenfield projects start with no project-management history; for retrofit, existing tickets/epics/issues must be reckoned with explicitly. Without this phase, the spec-driven workflow becomes a parallel artifact rather than the source of truth, and the equivalence target's "specs are the source of truth" claim fails.

**Goal:** Decide how existing project-management artifacts (Linear/Jira/GitHub Issues tickets, epics, in-repo `tickets/` directories, in-flight backlog work) relate to the new spec-driven workflow. Three strategies are offered; the operator chooses one with documented rationale. The decision drives R8.B's MCP installation, R8.C's skill set, and CLAUDE.md's escalation rules.

**Sits here because:** R0 step 12 has already gathered evidence; R0.5 has set the archetype (which informs which strategy is most natural — e.g., a multi-team Platform archetype probably can't fully archive Linear). R1+ behavior depends on the source-of-truth decision (e.g., R1's product.md framing changes if the operator wants spec-as-source).

**AI actions:**

1. **Read the inventory.** Specifically: `.claude/inventory/pm-tooling-signals.md` (R0 step 12), the archetype from `.retrofit-state.json` (R0.5), and the operator's portfolio context from R0 step 2.

2. **Summarize current state to the operator.** Cite specifics — don't generalize. Examples:
   - "I detected a `tickets/` directory with 47 markdown files, 12 modified in the last 30 days. Recent tickets reference patterns like `AGT-123` and `compliance-2024-q4-001`."
   - "Your CI workflow `.github/workflows/release.yml` calls the Linear API to update ticket status on merge."
   - "PR template links tickets to `linear.app/yourorg/issue/{id}`."
   - "Last 100 commits: 73 reference Linear tickets via `LIN-NNN` pattern; 8 reference GitHub issues via `#NNN`; 19 have no ticket reference."

3. **Surface the source-of-truth question explicitly.** The retrofit must produce a clear answer. State the question:

   > "Going forward, what's the source of truth for *work intent* — the description of what to build and why? The spec-driven workflow assumes specs in `.claude/specs/` are the source of truth. For retrofit, three strategies are available. Pick one:"

4. **Present the three strategies with concrete consequences:**

   **Strategy A — Spec-canonical (most BOOTSTRAP-equivalent).**
   - **Going forward:** every new piece of work begins with `/spec-new`. Specs in `.claude/specs/` are the source of truth.
   - **Existing tickets:** archived in `.claude/inventory/legacy-tickets/` (snapshot at retrofit time). Open tickets that represent ongoing work are queued for conversion to specs via the `ticket-to-spec` skill (skill is installed in R8.C; conversion runs post-retrofit, either as a one-shot batch the operator initiates or organically as tickets are picked up). Closed tickets are kept for historical reference but no further updates.
   - **PM tool integration:** Linear/Jira/GitHub Issues MCP NOT installed (or removed). The PM tool, if used at all going forward, becomes a public-facing communication channel (e.g., for community contributors), not the canonical work record.
   - **CI integrations:** any CI step that updates ticket status is removed or changed to update spec status.
   - **Tradeoffs:** maximum BOOTSTRAP equivalence; clean spec-source-of-truth claim; everyone on the team must adopt the new workflow. Best for solo/small-team projects without external stakeholders who depend on Linear/Jira views.

   **Strategy B — PM-canonical with spec bridge.**
   - **Going forward:** tickets in the existing PM tool remain the entry point for work intent. Specs are the *implementation contract* derived from a ticket. When a ticket is picked up post-retrofit, the operator can invoke the `ticket-to-spec` skill (if installed) to auto-generate a spec stub, then refines.
   - **Existing tickets:** stay where they are. Open tickets get a spec when worked; closed tickets are not converted.
   - **PM tool integration:** Linear/Jira/GitHub Issues MCP IS installed in R8.B. Specs reference back to ticket IDs in their frontmatter.
   - **CI integrations:** preserved as-is.
   - **`ticket-to-spec` skill:** OPTIONAL for Strategy B. The operator can choose to install it (recommended, since it removes manual translation work) or not (skip in R8.C). Not strictly required for the workflow to function.
   - **Tradeoffs:** operator's existing process disrupted minimally; spec-driven discipline applies only when an AI agent picks up work; the equivalence target's "specs are source of truth" claim is a documented INTENTIONAL VARIATION (see Validating Equivalence). Best for teams with non-AI-using collaborators or external stakeholders who track work in Linear/Jira.

   **Strategy C — Hybrid (cutover schedule).**
   - **Going forward:** specs become source of truth for *new initiatives* started after retrofit. Existing in-flight tickets continue in the PM tool until completed; new follow-up work for the same area uses specs.
   - **Existing tickets:** snapshot to `.claude/inventory/legacy-tickets/` at retrofit time. In-flight tickets remain canonical until closure. New work creates specs.
   - **`ticket-to-spec` skill:** installed in R8.C; used post-retrofit for any in-flight ticket the operator decides to convert mid-flight (rare but possible) and for new tickets that arrive through legacy channels but should be converted.
   - **PM tool integration:** MCP installed and used during the transition window (default 90 days). Operator decides at 90-day baseline review whether to fully migrate (Strategy A) or stay hybrid permanently (closer to Strategy B).
   - **CI integrations:** preserved during transition; revisited at 90 days.
   - **Tradeoffs:** lowest disruption; explicit transition path; requires the 90-day review to actually happen — without it, the hybrid persists by default and you've effectively chosen Strategy B without the documentation. Best for teams with active in-flight work who want to migrate to spec-canonical eventually.

5. **AI recommendation by archetype + team size** (operator may override). The AI checks `inventory/git-history.md` contributor count and the operator's portfolio context:
   - **CLI tool, Library/SDK, Service/API (single owner per git-history):** Strategy A by default.
   - **Service/API (multi-owner per git-history), Full-stack, Mobile, Data/ML (multi-owner):** Strategy C by default.
   - **AI/agent system:** Strategy A by default if git-history shows single contributor; Strategy C if multi-contributor. If git-history is unavailable (degraded mode), ask the operator: "single contributor or team?"
   - **Platform / multi-component:** Strategy C by default; Strategy A possible only if the operator has authority across all components (ask: "do you control all components, or are some maintained by others?").
   - **Other:** consult `closest_archetype` recommendation and ask the operator.
   - **Override criteria:** the operator can override the AI recommendation regardless of evidence — they know team dynamics the inventory can't see. The recommendation is a starting point, not a constraint.

6. **Discuss with the operator.** This is a real conversation — the operator may have constraints (e.g., "we have a contractor who only uses Linear") that override the archetype default. Surface these as INTENTIONAL VARIATION requirements: if the operator picks Strategy A but mentions external stakeholders, flag that this commits them to migrating those stakeholders too.

7. **For Strategies A and C: scan and propose ticket-to-spec migration list.**
   - List open tickets from `pm-tooling-signals.md` audit. For each, propose: (a) convert to spec now via `ticket-to-spec` skill, (b) defer (no work planned in next 30 days), or (c) close (already complete or no longer relevant).
   - Operator approves the proposed disposition. Convert-now tickets are queued for the `ticket-to-spec` skill (skill installed in R8.C; conversion runs post-retrofit). Defer tickets get a `debt.md` entry titled "Ticket-to-spec migration backlog". Close tickets are tracked by ID in the snapshot directory (see step 9.5).
   - **Default scope:** only open tickets. Closed/archived tickets are NOT migrated automatically; they're snapshotted only.
   - **Migration is not done in this phase** — it's queued. The actual `ticket-to-spec` runs are part of normal post-retrofit work or as a one-shot batch the operator initiates after R7. The retrofit produces the *plan*, not the executed migration.

8. **Write `.claude/steering/workflow-source-of-truth.md`** with:
   - The chosen strategy (A / B / C) and rationale.
   - The PM tool's current role and future role.
   - For Strategy A: archive location of legacy tickets; CI changes required.
   - For Strategy B: spec-frontmatter convention for linking back to tickets; INTENTIONAL VARIATION declaration in `tech.md`.
   - For Strategy C: cutover date (default = retrofit completion date); 90-day review schedule; criteria for "in-flight" vs "new" work.
   - Per-ticket disposition (for Strategies A and C): convert-now / defer / close, with operator approval recorded.

9. **Write `.claude/inventory/pm-artifacts.md`** — the audit snapshot of PM artifacts at retrofit time. References pm-tooling-signals.md and adds operator-confirmed counts. Frozen artifact (like other inventory files); not maintained going forward.

9.5 **Snapshot existing tickets to `.claude/inventory/legacy-tickets/` (Strategies A and C only).** Read existing tickets from the source identified in step 1 (in-repo `tickets/` directory, Linear API via MCP, Jira API via MCP, GitHub Issues via `gh` or MCP) and copy/export them to the snapshot directory. Subdirectories: `open/`, `closed/`. This is a frozen archive — at retrofit time, ticket state is captured for reference. Operator's choice to migrate, defer, or close (recorded in step 7) governs *what happens to specs*, not what's preserved here. For Strategy B, no snapshot is taken because tickets remain canonical in the PM tool.

10. **Update `.retrofit-state.json`** with:
    ```json
    {
      "pm_strategy": "spec_canonical | pm_canonical | hybrid",
      "pm_tool": "linear | jira | github_issues | tickets_dir | none",
      "pm_tool_role_after": "removed | bridge_only | community_facing | hybrid_transitional",
      "ticket_migration_disposition": {
        "convert_now": ["LIN-123", "LIN-456"],
        "defer": ["LIN-789"],
        "close": ["LIN-012"]
      },
      "hybrid_review_date": "2026-08-04"  // null if not Strategy C
    }
    ```

11. Show and ask: **approve / edit / start over**.

**Exit criteria:** `workflow-source-of-truth.md` exists with explicit strategy choice and rationale. `pm-artifacts.md` exists. State file updated. For Strategies A and C, ticket migration disposition recorded. Operator has confirmed. R8.B knows whether to install PM-tool MCP. R8.C knows whether to install `ticket-to-spec` skill.

---

## Phase R0.8 — Preview & Commitment

**New in v1.4.** Equivalent to BOOTSTRAP Phase 0.5. **Skippable on operator request** — if the operator is confident in the retrofit scope and wants to proceed without preview, they can opt out, but the protocol shows them what they're skipping.

**Goal:** Show the operator exactly what the retrofit will produce, so they can commit (or back out) before R1+ starts writing artifacts. The retrofit has substantial scope — for some projects, 30+ files across `.claude/`. Operators who realize mid-retrofit that they didn't want all of this end up with partial setups that are worse than no retrofit.

**Sits here because:** all preceding decisions (archetype, PRD tier, CI/CD applicability, skip decisions, regulatory regime, PM strategy) are known. R1+ starts producing real artifacts, so this is the last point at which an operator can adjust scope cheaply.

**AI actions:**

1. **Build the file manifest.** Based on the archetype, skip decisions, regulatory regime, PM strategy, and per-archetype hook/skill conditional matrix, list every file that will be created or modified. Group by phase that produces them:

   - **R0.7 (already produced before R0.8):** `.claude/steering/workflow-source-of-truth.md`, `.claude/inventory/pm-artifacts.md`, `.claude/inventory/legacy-tickets/` snapshot dir (if Strategy A or C). Surface these as already-produced rather than queued.
   - **R1:** `docs/prd/<name>.md` (if no canonical PRD), `.claude/steering/product.md`.
   - **R2:** `.claude/steering/tech.md`, `.claude/inventory/danger-zones.md`.
   - **R3:** `.claude/debt.md`.
   - **R4:** `.claude/steering/spec-strategy.md` (with legacy allowlist).
   - **R5:** `.claude/steering/principles.md`, `.claude/steering/structure.md`. Plus project-specific steering as applicable: `.claude/steering/contracts.md` (if boundary specs needed), `.claude/steering/migration.md` (if migration specs needed), `.claude/steering/compliance.md` (if regulatory regime applicable), `.claude/steering/phase.md`, `.claude/steering/workflow.md`, `.claude/steering/roles.md` (if extracted from CLAUDE.md or prior art).
   - **R5.5:** `.claude/steering/deps.md`, `.claude/steering/secrets.md`.
   - **R8.A:** `.claude/settings.json`, `.claude/hooks/*.sh` (count varies by archetype + skip decisions), `.claude/hooks/audio-alerts.config`, `.claude/hooks/rollout-schedule.md`, `.claude/hooks/worktree-budget.md` (if codebase > 1GB), sound files in `~/.claude/sounds/`.
   - **R8.B:** `.claude/steering/tools.md`. MCP server installations (count varies; PM-tool MCP installed only for Strategies B and C).
   - **R8.C:** `.claude/agents/{implementer,reviewer,integrator}.md`, `.claude/skills/{spec-new,spec-review,spec-decompose,plan-review,spec-validate,test-author,code-review,decision-log,pr-author,checkpoint,resume,ack-drift,quiet,quiet-task-done,legacy-spec,legacy-pin-test,boundary-spec,migration-plan,inventory-scan,prior-art-audit,convention-categorize,debt-classify}.md`, plus archetype-specific (`prompt-pinning-eval`, `dataset-pin-test`), plus `ticket-to-spec.md` (v1.4 — required for Strategies A and C, optional for B), plus `.claude/inventory/ticket-migration-queue.md` (if Strategy A or C). `.claude/commands/*.md` (count varies). `.claude/specs/INDEX.md`. README files for `learnings/`, `sessions/`.
   - **R8.D:** `.claude/steering/spec-versioning.md` (if not skipped).
   - **R8.E:** `CLAUDE.md` at repo root.
   - **R8.F:** `.claude/steering/ci-cd.md`.
   - **R7:** `.claude/inventory/equivalence-validation.md`.

2. **Estimate scope.**
   - **File count total:** sum of above (typically 35–55 files for a Service/API or AI/agent retrofit; 20–30 for CLI or Library; 60–80 for Platform).
   - **Token-budget impact estimate:** rough — how much steering + CLAUDE.md will consume on cold start. Estimate in ranges: "~5–8K tokens for steering + ~2–3K for CLAUDE.md" for Standard PRD; double for Full PRD. Order-of-magnitude correct, not precise.
   - **Remaining wizard time:** estimate based on archetype, source-file count, skip decisions. For a Service/API at 300 source files with no skips: ~90 minutes remaining. For Platform with multi-component R2: ~3 hours remaining.
   - **Disk impact:** `.claude/` directory size estimate (typically 50–200 KB), plus archived `.claude.archived-*/` if applicable, plus any sound files (~50 KB).

3. **Surface the per-strategy adjustments.** Make the operator's earlier choices visible:
   - "Archetype: Platform / multi-component → R2 runs per-subsystem, expect 2–3x time."
   - "Regulatory regime: HIPAA detected → `compliance.md` added, R8.A.8 stub list documented."
   - "PM strategy: Hybrid → `ticket-to-spec` skill installed; 12 tickets queued for migration."
   - "Skip decisions: R6 deferred → equivalence smoke test will be skipped; you can run it later via `/spec-new` against an existing module."

4. **Ask the commit question:**

   > **Proceed with the retrofit / Adjust scope / Cancel.**
   >
   > - **Proceed:** R1 begins now.
   > - **Adjust scope:** return to one of the prior decision points. Show the operator which:
   >   - **Archetype** → re-run R0.5 step 1-4 (proposal + override + dimension interview if Other).
   >   - **PRD tier target** → re-run R0.5 step 6.
   >   - **CI/CD applicability** → re-run R0.5 step 5.
   >   - **Skip decisions** (R6, R0.8 itself, R8.D, R5.5 secrets) → re-run R0.5 step 7.
   >   - **Regulatory regime** → re-run R0 step 10 (if operator realizes a framework was missed or incorrectly identified).
   >   - **PM strategy** → re-run R0.7.
   >   - **Production traffic** → re-run R0 step 11.
   > - **Cancel:** exit cleanly. State file is preserved so the retrofit can be resumed; no `.claude/` artifacts are written from this point forward.

5. **If proceed:** mark R0.8 complete in `.retrofit-state.json`. Set `r08_committed: true, r08_committed_at: <timestamp>`. The remaining phases run.

6. **If adjust scope:** route to the relevant earlier phase. Document the adjustment in state file. Re-run R0.8 after adjustment.

7. **If cancel:** clean exit. State file preserved. Inform operator they can resume by re-invoking the retrofit; the state file means R0/R0.5/R0.7 won't be re-run unnecessarily.

**Exit criteria:** Operator has seen the full file manifest + scope estimates and explicitly committed (or canceled cleanly, or adjusted and re-committed). State file shows `r08_committed: true`.

---

## Phase R1 — Product Archeology (`product.md`)

**Goal:** Reconstruct the implicit PRD from what exists, since a fresh PRD-authoring step doesn't fit retrofit.

**AI actions:**

1. Read `.claude/inventory/product-signals.md` and `.claude/.retrofit-state.json` (for archetype + `prd_tier_target` from R0.5).
2. Decide PRD strategy first, with archetype awareness:
   - **Existing canonical PRD found** (e.g., `docs/prd/<name>.md` or `docs/<product>-prd-vN.md` exists and is current per the inventory's currency check): `product.md` is a thin pointer doc. Don't compress an existing 1,500-line PRD into a steering doc; the steering doc says "the PRD is at `<path>` and is the source of truth," then summarizes the user/problem/metric in two pages. **Tier check:** verify the existing PRD covers at least the archetype's required tier. If existing PRD < target tier (e.g., archetype is Platform / Full PRD required, but the existing PRD is Standard-quality), surface the gap as an R3 debt entry: "PRD needs upgrade to Full tier — current content covers product vision but lacks per-component scoping or metrics framework."
   - **No PRD, but rich product signals** (README, architecture docs, marketing copy): `product.md` is the primary product document for now. **Tier check:** if the inferred content from signals can reasonably reach the target tier, do so in `product.md` directly. If not, flag a debt entry recommending post-retrofit PRD authoring at the appropriate tier.
   - **Sparse signals:** flag this as a retrofit risk. `product.md` will be heavily inferred. **Tier check:** explicitly tell the operator the gap between produced content (likely Micro at best) and target tier; recommend post-retrofit PRD authoring as a high-priority debt entry.
3. Propose answers to the standard product questions, **citing the source for each**. Question depth scales to PRD tier target:
   - **All tiers:** primary user persona; single most important problem solved; success metric.
   - **Standard or higher:** secondary personas; user journeys; non-goals; key dependencies; risks.
   - **Full only:** market context; competitive analysis; phased rollout; metrics framework; per-component scoping.
   Cite from README, marketing copy, onboarding docs, or existing PRD where present.
4. **Where the AI is inferring rather than citing**, mark explicitly: "INFERRED: this is my best guess from [source]; please confirm or correct." Inferences without flags are a retrofit failure mode.
5. Ask the operator to confirm, correct, or expand each answer. Pay special attention to inferences.
6. Optionally, ask whether the operator wants to also produce a forward-looking section: "Going forward, what do you want this product to become?" — different from "what is it today?". This becomes a `## Forward Direction` section in `product.md`.
7. Write `.claude/steering/product.md` with sections:
   - `## Today` — the reconstructed product description; depth scales to tier target.
   - `## Forward Direction` (optional) — where the operator wants to take it.
   - `## Source` — explicit pointer to the canonical PRD if one exists, or a note that `product.md` is the lightweight stand-in. **For Full PRD targets where existing content is below tier**, also include a `## PRD Upgrade Notes` section pointing to the relevant `debt.md` entry.
8. Show and ask: **approve / edit / start over**.

**Exit criteria:** `product.md` exists. Inferred sections are clearly marked. Tier gap (if any) is recorded as a debt entry. Operator has confirmed.

---

## Phase R2 — Convention Reckoning (`tech.md`)

**Goal:** Audit existing conventions and decide which become canonical going forward. **This is the most retrofit-specific phase and benefits from the most operator engagement. It is also the highest-leverage call in the entire protocol.** A bad call here ships flawed steering for the lifetime of the project.

**AI actions:**

1. Read `.claude/inventory/conventions.md`, `.claude/inventory/prior-art.md` (if it exists), and `.claude/.retrofit-state.json` (for archetype + synthetic profile from R0.5). All are R2 inputs.

2. **Enumerate distinct runtimes/subsystems first.** Behavior varies by archetype:
   - **Platform / multi-component:** per-subsystem categorization is the **default**, not opt-in. The inventory's multi-component evidence (multiple Dockerfiles, multiple `[project]` tables, multiple deployable units) tells the AI to enumerate components first and categorize per-component.
   - **Service/API, Full-stack app, Data/ML pipeline, AI/agent system:** per-subsystem categorization is **opt-in**, surfaced when the inventory flagged multi-runtime evidence. If the inventory shows single-runtime, skip this step.
   - **CLI tool, Library/SDK, Mobile app:** per-subsystem categorization is rarely needed — these archetypes are typically single-runtime by nature. Skip this step unless the inventory shows surprising structural variation.
   - **Other (synthetic profile):** consult the profile's `deployable_unit_count`. If >1, run per-subsystem; if 1, skip.

   The output of this step (when run): "subsystems are X, Y, Z; conventions A and B legitimately differ across them; convention C is shared across all of them." **Flattening multi-runtime variation is the failure mode the inventory flagged.**

3. For each observed pattern (or inconsistency), **propose a categorization**:
   - **CANONICAL** — this pattern stays. The AI should follow it for new code.
   - **DEPRECATED** — this pattern exists in legacy code but new code should use a different one. Flag for `debt.md`.
   - **INTENTIONAL VARIATION** — this is not inconsistency; different parts of the system genuinely need different patterns (e.g., FUSE-protocol envelope errors vs HTTP-route HTTPException). Document the rule for when each applies.
   - **MODERNIZE** *(new in v1.1)* — the existing pattern works; a protocol-introduced convention offers concrete benefits worth offering to the operator. Used for prior-art conventions that conflict with BOOTSTRAP-introduced standards. The choice is the *operator's*, not the AI's. Propose the trade-off explicitly: "your single-tone alarm convention works; the BOOTSTRAP three-category audio system distinguishes urgency you currently can't (drift / task-done / decision-required). Adopt fully? Adopt partially (keep your existing sound for one category, generate the others)? Reject (stay with single-tone)?"

4. Show the categorizations to the operator. **This is the conversation that makes retrofit valuable.** Each category needs a decision:
   - For DEPRECATED items, ask: "Migrate aggressively (track in debt.md and prioritize), opportunistically (fix when touching the code), or never (document and move on)?"
   - For INTENTIONAL VARIATION, ask: "What's the rule for when each variant applies?" Capture this rule explicitly in `tech.md`. For multi-runtime cases, the rule is usually "subsystem X uses pattern A; subsystem Y uses pattern B; subsystem Z uses pattern C — here's why each is appropriate."
   - For MODERNIZE items, ask: "Adopt / hybridize / reject?" Document the choice and the reason. Hybrid choices need explicit configuration (e.g., "keep the `paplay` sound for `decision-required`; generate `task-done` and `drift` sounds via the BOOTSTRAP §6.E flow").

5. **Archetype-aware question sets** for topics the inventory didn't cover. Skip questions whose answers are obvious from the inventory. Per-archetype:
   - **All archetypes:** logging format, observability tools, error reporting (Sentry / equivalent), naming conventions for files / functions / classes, async vs sync defaults.
   - **Service/API, Full-stack app, Platform:** request validation strategy (schema-first vs runtime-first), error response shape (problem-detail RFC 7807 vs custom), graceful degradation rules (fallback paths, NoOp patterns), idempotency conventions (Celery, webhooks, migrations).
   - **Library/SDK:** public API stability rules, deprecation policy, backward-compat testing, semver discipline (what counts as breaking).
   - **AI/agent system:** prompt versioning convention, eval harness + cost-tracking integration, determinism boundaries (where exact reproducibility matters vs where it doesn't), LLM provider abstraction (single provider locked-in vs multi-provider via OpenRouter / equivalent).
   - **Data/ML pipeline:** notebook-vs-pipeline separation, dataset versioning, model artifact storage, drift detection cadence, reproducibility guarantees.
   - **Mobile app:** keystore handling, OTA update strategy, offline-mode rules, store-deploy gating.
   - **CLI tool:** flag/argument conventions, exit code convention, output streams (stdout vs stderr discipline), config file resolution order.
   - **Platform / multi-component:** cross-component contract definitions (interface stability), per-component deployment unit rules, shared-vs-local conventions explicit per component.
   - **Other (synthetic profile):** consult `closest_archetype` + `deviations_from_closest`; ask `closest_archetype`'s question set, then add deviation-specific questions.

6. Ask the "do not touch" question. Default suggestions plus retrofit-specific defaults:
   - Any module flagged as "stable beyond the calibrated cutoff" in the inventory is a candidate for "do not touch" — touching stable code with no specs is high-risk.
   - Initial DB migration files and other inherently frozen artifacts (alembic versions, prisma migrations).
   - Pinned-contract files that downstream contracts depend on (e.g., schemas matching an external API surface).
   - **Archetype-specific defaults:** Service/API → auth modules + payment modules; Library/SDK → public API surface (`__init__.py`, `index.ts`); AI/agent → prompt files + eval harness; Platform → cross-component contract files.

7. **Documentation policy** — same as bootstrap, but for retrofit, explicitly ask: "Does existing documentation reflect current code, or has it drifted?" If drift, log a debt item.

8. Write `.claude/steering/tech.md` with sections:
   - `## Stack` — languages, frameworks, runtimes (mostly auto-populated from inventory).
   - `## Subsystems` — for multi-runtime projects, the enumeration with brief descriptions. Skipped for single-runtime projects.
   - `## Canonical Conventions` — the patterns that stay. Per-subsystem subsections if multi-runtime.
   - `## Intentional Variations` — places where different rules apply, with the rule explicit.
   - `## Modernized Conventions` *(new in v1.1)* — patterns where the operator chose to adopt a BOOTSTRAP-introduced standard over prior art. Record the prior pattern, the new pattern, and the migration path.
   - `## Documentation Policy` — same as bootstrap.
   - `## Do Not Touch` — never-modify list with reasons.
   - `## Migration Notes` — pointer to `debt.md` for deprecated patterns.

9. **Code health awareness (G10).** Compute a "danger zone" classification for source files based on the inventory data:
   - **Hotspot identifier** — files in the top 10% by change frequency (from `git log` activity).
   - **Complexity proxy** — files with functions over 100 lines OR files whose total source line count is in the top 10% (without code-complexity tooling, this is a sufficient proxy).
   - **Test coverage proxy** — files in the no-coverage list from `inventory/testing.md`.
   - **Danger zone = files with all three traits.** Capture as a list at `.claude/inventory/danger-zones.md`.
   - These files require **stricter R8.A reviewer behavior**: any change to a danger-zone file by the implementer subagent triggers reviewer mandate "no architecture change in the same PR as a behavior change" and requires an accompanying pinning test.
   - Per the Tornhill via Fowler 2026 finding: AI-modified unhealthy code carries ~30% higher defect risk. Danger zones make the risk concrete and actionable.

10. **Pin-first discipline declaration (G6).** Add to `tech.md`'s `## Canonical Conventions` section: *"For any modification to a file in `inventory/danger-zones.md` or in the legacy allowlist, the **pin → spec → modify** sequence applies. A `legacy-pin-test` is generated before the modification; the change spec describes the intended delta; the modification is verifiable against both."* This is a project-wide rule that R8.A can enforce via a pre-edit check.

11. Show and ask: **approve / edit / start over**.

**Exit criteria:** `tech.md` exists with all four categorizations resolved. Per-subsystem categorization captured for multi-runtime projects. Deprecated patterns logged for `debt.md` in Phase R3. Modernized conventions documented with operator's explicit choice. Danger zones identified. Pin-first discipline declared.

---

## Phase R3 — Technical Debt Registry (`debt.md`)

**Goal:** Capture every known issue we're not fixing during retrofit, so it's tracked rather than lost.

**AI actions:**

1. Aggregate debt sources:
   - DEPRECATED conventions from Phase R2.
   - Outdated/deprecated dependencies from `.claude/inventory/dependencies.md` (or deferred-scan stub if R-1 was network-isolated).
   - Modules with no test coverage from `.claude/inventory/testing.md`.
   - Documentation drift noted in Phase R2.
   - Working-tree dirty files at retrofit start (from R-1) — operator should reconcile before retrofit's hooks go live; logged here as a reminder.
   - Pre-existing CLAUDE.md sections classified as "Deprecated" in R0 step 5.
   - **Danger zones** *(v1.3)* from `.claude/inventory/danger-zones.md` (R2 step 8) — high-risk files without active mitigation plan; flag for stricter review discipline going forward.
   - **Tribal-knowledge findings** *(v1.3)* from `.claude/inventory/tribal-knowledge.md` (R0 step 9) — sleeping bugs and magic-config items typically become debt entries; DO NOT TOUCH items go to `tech.md` not debt; war stories may become narrative tests rather than debt.
   - **Regulatory-context gaps** *(v1.3)* from `.claude/inventory/regulatory-context.md` (R0 step 10) — gaps between current state and applicable framework requirements (e.g., SOC 2 audit-trail depth, HIPAA component coverage).
   - **DORA baseline tier** *(v1.3)* from `.claude/inventory/baseline-metrics.md` (R0 step 8) — if current DORA performance tier is Low or Medium, surface as a debt entry: "Current tier: X. Spec-driven workflow expected to improve over 90 days; revisit at next baseline review."
   - Any operator-known issues not captured above (ask).

2. For each item, capture:
   - **What** — the issue in one sentence.
   - **Where** — affected files or modules.
   - **Severity** — low / medium / high (operator decides).
   - **Discovered** — date and source (e.g., "retrofit, R2 convention scan").
   - **Migration plan** — empty if no decision yet, otherwise a one-line approach.
   - **Status** — `open` (default for all retrofit items).

3. Write `.claude/debt.md` with the registry. Format as a table or list — operator preference.

4. Add a section at the top: `## How to use this file`:
   - "Add new entries when issues are identified during regular work."
   - "Update Status to `in-progress` when work begins, `resolved` when done."
   - "Periodically review and re-prioritize."
   - "This file is project-local; not standardized across the portfolio."

5. **Explicit out-of-scope statement.** Add at the top: "This retrofit does not fix any of these items. Resolution is a separate, ongoing effort tracked here. Do not let this file's length discourage starting on new feature work."

6. Show and ask: **approve / edit / start over**.

**Exit criteria:** `debt.md` exists with all known issues from R-1 through R2 captured. Operator has confirmed completeness.

---

## Phase R4 — Spec Backfill Strategy

**Goal:** Decide how existing code relates to the spec-driven workflow going forward, and identify which of the three brownfield SDD spec patterns apply.

**AI actions:**

1. Explain the three spec-backfill strategies:
   - **Forward-only (recommended for minimum viable retrofit):** new features get specs; old code is "legacy" and untouched by spec gates. The simplest path. Cost: hooks like the spec gate need an "existing-code allowlist" so they don't block edits to legacy files.
   - **Bulk backfill:** generate one-paragraph specs for every existing module before starting new work. Expensive but produces a clean state. Cost: weeks of additional effort upfront. Out of scope for minimum viable retrofit.
   - **Touch-based backfill (recommended pragmatic compromise):** when modifying an existing module for the first time after retrofit, write a brief spec for it as part of that work. **Combined with the pin-first discipline from R2 (G6), the sequence becomes pin → spec → modify** for any legacy modification.

2. Recommend **forward-only** by default for minimum-viable retrofit, **touch-based with pin-first** as the recommended next-tier option for projects that expect frequent legacy modifications.

3. **Identify applicable brownfield SDD spec patterns (G8).** RETROFIT v1.3 distinguishes three spec patterns that may apply to the project. The combination depends on archetype + structure:

   - **Change specs (delta specifications)** — the modification of a single piece of behavior. **Always applicable.** RETROFIT v1.2's touch-based backfill maps to this. Every AI-assisted change must update the spec, not just the code (this discipline is enforced via R8.A's spec gate; see G14 rollout discipline).

   - **Dependency boundary specs (service contract specifications)** — formalize implicit contracts at integration points between legacy and modern systems, or between subsystems. Required components: machine-readable artifacts (OpenAPI for REST, JSON Schema for data, Avro/Protobuf for events) plus non-functional concerns (failure modes, SLOs, versioning).
     - **Apply if:** archetype is Service/API, Full-stack, Library/SDK, or Platform; or the project has cross-component / cross-subsystem integration points.
     - **Skip if:** archetype is CLI tool with no external integration; or Mobile app with single-binary scope.
     - Where applicable, R5 produces a `contracts.md` steering doc *(see G5 from v1.1)* that lists the project's integration points and their boundary specs.
     - **Bootstrap from production traffic where possible (G18):** if `inventory/traffic-sample.json` exists from R0 step 11, validate the boundary spec against captured traffic before ratifying. Per GitHub's SAML hardening case study: prod traffic is more reliable than docs.

   - **Migration specs (incremental modernization specifications)** — define target state + incremental steps + integration-layer (façade/proxy/ACL) design. Each step independently deployable.
     - **Apply if:** the project has an active modernization in progress (existing patterns being deprecated, new architecture being built alongside, etc.); or the operator anticipates one in the next 6 months.
     - **Skip if:** the project is in steady-state and no architectural change is anticipated.
     - Where applicable, R5 produces a `migration.md` steering doc *(see G5 from v1.1)* that captures the target state, incremental steps, and integration-layer design.

4. **Apply the per-archetype strangler pattern (G7 + G15).** Reference the table in §"Project Archetypes > Per-Archetype Strangler & Spec Patterns." For the project's archetype:
   - Document which strangler approach applies (proxy/façade for Service; re-export for Library; prompt-version routing for AI/agent; per-component cutover for Platform; etc.).
   - For Service/API and Platform archetypes specifically, note the **anti-corruption layer (ACL)** location (G19) — the translation layer that prevents legacy concepts from leaking into the new domain model. The ACL is implicit in the strangler approach but worth naming explicitly.

5. Whatever the operator picks, document the decision in `.claude/steering/spec-strategy.md` covering:
   - The chosen spec-backfill strategy (forward-only / touch-based / bulk) and why.
   - The legacy-allowlist file (if forward-only or touch-based) — list of paths or globs that are exempt from spec-gating until they have specs. Generated from the inventory's existing-files list, minus anything the operator wants to mark as "new from this point."
   - The promotion rule: how does a legacy file become a spec-covered file? (Default: when first modified after retrofit, run `/spec-new` for the module before editing. With pin-first discipline: `legacy-pin-test` runs first, then `/spec-new`.)
   - The active spec patterns from step 3 (change specs always; boundary specs and migration specs as applicable).
   - The strangler approach from step 4 if archetype warrants.
   - **The retrofit-active mode.** During the retrofit itself (before R7 handoff), the spec-gate-commit hook would block all `.claude/` writes — which would defeat the protocol. The retrofit-active allowlist explicitly permits writes under `.claude/` while the retrofit is in progress. R8.A wires this into the hook config; R7 turns it off when retrofit completes.

6. Show and ask: **approve / edit / start over**.

**Exit criteria:** `spec-strategy.md` exists with backfill strategy, applicable spec patterns, strangler approach, legacy allowlist, promotion rule, retrofit-active mode. R5 knows whether to produce `contracts.md` (boundary specs) and/or `migration.md` (migration specs).

---

## Phase R5 — Principles & Structure (Compressed)

**Goal:** Run BOOTSTRAP Phase 3 (`structure.md`) and Phase 4 (`principles.md`) with retrofit-specific adjustments. These compress into one phase because the inventory has already done most of the heavy lifting.

**AI actions:**

1. **Structure (`structure.md`):**
   - Use `.claude/inventory/structure.md` as the baseline. The directory tree is whatever exists.
   - Ask the operator about each top-level directory: "Is this where new code of this kind should still go?" (Y/N/move-to-X).
   - For any directory marked "move-to-X," log a debt item.
   - Write `.claude/steering/structure.md` with the *current* structure plus a `## Going Forward` section noting any planned moves.

2. **Principles (`principles.md`):**
   - Read archetype from `.claude/.retrofit-state.json`. Propose **3–5 principles** drawing from both the inventory's findings and the **archetype's starter set**:
     - **CLI tool starter:** flag/argument predictability; exit code discipline; output stream separation (stdout = data, stderr = diagnostics); no-args-shows-help convention.
     - **Library/SDK starter:** public API stability (semver discipline); no breaking changes without major bump; deprecation requires both a warning and a migration path; tests cover all public surface.
     - **Service/API starter:** idempotency at boundary handlers (webhooks, retries, migrations); graceful degradation for external deps (fallback paths, NoOp); request validation at system boundaries (no raw `request.json()` reads); error responses follow a consistent shape.
     - **Full-stack app starter:** Service/API starter + frontend/backend contract discipline (single source of truth for request/response shapes); separation of view logic from business logic.
     - **Mobile app starter:** offline-mode first (assume disconnected); keystore separation per environment; OTA discipline (what can ship without store review).
     - **Data/ML pipeline starter:** reproducibility (pinned deps + dataset versions); idempotent pipeline stages; drift detection on inputs and outputs; notebooks are throwaway, scripts are checked in.
     - **AI/agent system starter:** prompt versioning (every prompt change is a tracked version); cost discipline (cost-tracked at the call site); determinism boundaries explicit (where exact output matters vs where it doesn't); evals required for prompt changes.
     - **Platform / multi-component starter:** cross-component contract preservation (shared interfaces are versioned); per-component principles can override platform-wide principles where justified; platform-wide principles are the floor, not the ceiling.
     - **Other (synthetic profile):** combine `closest_archetype`'s starter set with deviation-specific additions.
   - Where the inventory found anti-pattern repetition, the corresponding principle should explicitly counter it (e.g., if `conventions.md` flagged "two functions over 100 lines, one over 300," the principle becomes "function length: extract when over 80 lines unless tested as a single unit").
   - For multi-runtime projects, principles can be per-subsystem if the operator wants. **For Platform archetype, per-subsystem is the default; for others, project-wide is the default and per-subsystem is opt-in.**
   - Ask the operator to add or override.
   - Define tiebreakers (same as bootstrap).
   - Decide TDD policy: for retrofit, default is **encouraged but not required** — many existing modules have no tests, and forcing TDD on legacy work via hook would block edits. Operator can override.
   - Where prior art included an explicit TDD policy (e.g., a pre-existing `roles/qa.md` with TDD instructions), surface it explicitly: "Your prior `qa.md` says tests are written before implementation as a checkpoint. Ratify, revise, or remove?"
   - Write `.claude/steering/principles.md`.

3. **Project-specific steering docs (G5 from v1.1, expanded in v1.3).** Read `.claude/inventory/claude-md-extraction-plan.md` if it exists, plus the v1.3-specific inputs from R0 (regulatory-context, traffic-sample) and R4 (active spec patterns, strangler approach). The extraction plan and these v1.3 inputs may identify content that doesn't fit the BOOTSTRAP-standard steering set (`product`, `tech`, `principles`, `structure`, `deps`, `secrets`, `ci-cd`, `tools`).

   **Project-specific steering doc candidates:**
   - `phase.md` — versioned phase constraints (Phase 1A vs 1B vs 2 — content that's both project-specific and time-bounded). Apply R8.D versioning.
   - `contracts.md` *(v1.3 — promoted from G5 example to first-class deliverable)* — cross-role / cross-subsystem interface definitions, integration-point boundary specs from R4 (G8). Required for projects where R4 step 3 identified active dependency boundary spec patterns. Format: machine-readable contract per integration point (OpenAPI for REST, JSON Schema for data, Avro/Protobuf for events) plus operator-readable summary. Validated against `traffic-sample.json` if available (G18).
   - `migration.md` *(v1.3 — new from G7 / G8)* — required for projects where R4 step 3 identified active migration spec patterns. Captures: target state vision, incremental steps (each independently deployable), integration-layer (façade/proxy/ACL) design, rollback paths per step, success criteria per phase.
   - `workflow.md` — project-evolved workflow definitions (e.g., a 7-step ticket workflow with research-variant) that don't reduce cleanly to BOOTSTRAP's per-task lifecycle. Operator-invented prior art often lives here. Documented as INTENTIONAL VARIATION in `tech.md` per equivalence target rules.
   - `roles.md` — if `.claude/roles/` is preserved as portfolio prior art (per R0 step 1's non-protocol-layout branch), the documentation of the role-ownership pattern can live here as a steering doc, distinct from the role *prompts* themselves.
   - `compliance.md` *(v1.3 — new from G20.1 / G20.2)* — required for projects where R0 step 10 identified applicable regulatory frameworks (SOC 2, HIPAA, PCI-DSS, ISO 13485 / IEC 62304, GDPR, FedRAMP, FDA AI/ML PCCP). Format: per-framework section with applicable controls, where existing compliance artifacts live (POA&M, DHF, SSP, records of processing, etc.), retrofit's relationship to them, audit-trail continuity rules, change-control regime declarations.

   These are **first-class outputs**, not exceptions. Treat them as a peer of `tech.md`/`principles.md` for the rest of the retrofit (R8.E.1 verifies they exist; R8.E.2 references them in the thin CLAUDE.md). For each project-specific doc, ask the operator: "approve / edit / merge into existing steering doc / start over." The "merge into existing" option matters — sometimes what looks like a separate doc is better as a section in `tech.md`.

3.5 **EARS notation recommendation (G12, optional).** When generating spec acceptance criteria — for both the change specs going forward and any backfill done here — recommend (don't mandate) EARS notation. Five patterns:
   - **Ubiquitous:** "The <system> shall <response>" (for properties always active)
   - **Event-driven:** "When <trigger>, the <system> shall <response>"
   - **State-driven:** "While <precondition>, the <system> shall <response>"
   - **Optional:** "Where <feature>, the <system> shall <response>"
   - **Unwanted behavior:** "If <trigger>, then the <system> shall <response>"

   EARS forces missing-information discovery — ambiguous requirements expose what isn't yet known. Reference the spec-related skills (`spec-new`, `legacy-spec`, `boundary-spec`) to optionally generate ACs in EARS notation. For requirements with 0-3 preconditions, EARS is appropriate; for more complex scenarios, fall back to tables/lists per QRA Corp guidance. Glossary records the patterns for operator reference.

4. Show and ask: **approve / edit / start over** for the full set (steps 1–3.5).

**Exit criteria:** `structure.md` and `principles.md` exist. Project-specific steering docs identified by R0 step 5 (extraction plan), R4 step 3 (spec patterns), and R0 step 10 (regulatory regimes) exist or have been explicitly merged into existing steering. Principles reflect the codebase's reality. EARS notation guidance is in place for new spec authoring.

---

## Phase R5.5 — Dependency & Secrets Steering

**Goal:** Run BOOTSTRAP Phase 2.5 (`deps.md`) and Phase 2.7 (`secrets.md`) — these need fewer adjustments for retrofit because they're already grounded in what exists.

**AI actions:**

1. **Dependencies (`deps.md`):**
   - **Skip check (archetype-conditional):** if R0.5 marked R5.5 deps as "skipped — stdlib only," produce a one-line `deps.md` that records the decision and skip the rest. Otherwise continue.
   - Use `.claude/inventory/dependencies.md` as the initial approved list.
   - Apply the same questions as BOOTSTRAP Phase 2.5 (approval policy, vetting criteria, who approves, pinning), with archetype-aware emphasis:
     - **CLI tool:** few deps usually; pin policy can be loose; recommend whatever the language ecosystem defaults to.
     - **Library/SDK:** **strict semver discipline on direct deps**; runtime-vs-dev split must be clean (consumers shouldn't inherit dev deps); upper bounds on major versions are typically appropriate.
     - **Service/API, Full-stack app:** lockfile recommended; runtime determinism matters for deploy reproducibility.
     - **AI/agent system:** **LLM provider lock-in is a design decision** — surface it explicitly. Single-provider (anthropic-py only) vs multi-provider (openrouter / openai-compatible) has downstream consequences for `tech.md`, `principles.md` ("LLM provider abstraction"), and prompt-versioning policy.
     - **Data/ML pipeline:** dataset / model artifact deps are first-class; ML framework version pinning is critical for reproducibility.
     - **Mobile app:** native bridge deps + JS deps may have separate manifests; surface both.
     - **Platform / multi-component:** **per-manifest policy** (each `requirements.txt` / `package.json` / `pyproject.toml` is its own approval scope). Do not merge them in `deps.md`.
     - **Other:** apply `closest_archetype` policy with deviation-specific overrides where relevant.
   - Where the inventory flagged outdated/deprecated dependencies (or where the outdated-scan was deferred for network reasons in R-1), the answer for "approval policy" needs to explicitly handle them: "These are approved despite being outdated; migration tracked in `debt.md`." If the scan was deferred, document the exact command for the operator to run locally and add a follow-up entry in `debt.md` to revisit `deps.md` once the scan results are available.
   - Where the inventory found inline ticket-reference comments alongside dependencies (a strong signal of intentional convention), ratify the practice in the `## Conventions` section of `deps.md`.
   - For multi-manifest projects (separate `requirements.txt` per service, plugin pyproject, etc.), `deps.md` has a section per manifest — don't merge them.

2. **Secrets (`secrets.md`):**
   - Apply the same questions as BOOTSTRAP Phase 2.7. Same skip rules.
   - **Historical secret leakage scan:**
     - **Full mode (git available):** scan git history for committed-then-removed credential patterns:
       ```
       git log --all -p -S 'API_KEY=' -S 'SECRET=' -S 'PRIVATE_KEY' \
         -S 'AWS_ACCESS_KEY' --pretty='%h %ai' 2>/dev/null
       git log --all --full-history -p -- '*.env' '*.pem' '*.key' 'credentials*'
       ```
     - **Degraded mode (no git):** scan present working tree only. Note in `secrets.md` that historical scan was unavailable.
     - If any secret is found (historical or present): alert the operator immediately and prominently. **Do not include the secret content in any output.** Recommend rotation regardless of current state. **This is the one retrofit finding that warrants stopping the protocol to address** — secrets exposure trumps protocol pacing.

3. Show and ask: **approve / edit / start over**.

**Exit criteria:** `deps.md` and `secrets.md` exist. Any historical secret leakage has been flagged. Outdated-deps scan completed or deferred with an explicit follow-up debt entry.

---

## Phase R6 — Equivalence Smoke Test (Optional)

**Goal:** Validate that the retrofit produced **BOOTSTRAP-equivalent workflow output**, not merely that the workflow runs. This is both the retrofit analog of BOOTSTRAP Phase 9 *and* the practical test of the equivalence target framing — does a real change through the new workflow produce artifacts that look like what BOOTSTRAP would produce?

**AI actions:**

1. Ask: "Pick a small change to an existing module to test the workflow. What's a low-risk modification you've been wanting to make?"
   - **Default recommendation:** a module from the inventory's "stable" list **and not** in `inventory/danger-zones.md` (per R2 G10). Testing the flow on a churn-heavy or danger-zone file is testing two things at once.
   - **Optional alternative:** a module from `inventory/danger-zones.md`, if the operator wants to also validate the danger-zone reviewer rules in step 6 below. This is the harder path but exercises more of the v1.3 discipline. Recommend the default unless the operator explicitly opts into the harder path.

2. **Pin first (G6)** if the module is in the legacy allowlist or in a danger zone. Run the `legacy-pin-test` skill (Sonnet) to generate a characterization test that captures current observable behavior. Operator confirms the test passes against the unchanged code. The pinning test will be the safety net for step 4's modification.

3. **Spec next.** If touch-based backfill is the strategy, run `/spec-new` for the module. Use `legacy-spec` (Sonnet — pattern work) for the change spec. Use `boundary-spec` (Sonnet) instead if the module IS an integration point. Generate AC in EARS notation per R5 step 3.5 if applicable.

4. Run `/spec-review`, `/spec-decompose`, `/plan-review`. Show the operator the artifacts.

5. **Stop before implementation** unless the operator explicitly opts into the second-stage smoke test (BOOTSTRAP Phase 9 analog: implement one task end-to-end through implementer → reviewer → spec-validate). The second stage is *optional but strongly recommended* because it validates the most failure-prone parts: subagent isolation, hook gating during retrofit-active mode, code review against legacy code, and pin-first → spec → modify discipline against the actual reviewer rules.

6. **Equivalence check** *(AI runs the check; operator reviews findings)*. The AI compares the artifacts produced against what BOOTSTRAP would produce for an analogous greenfield task and reports findings to the operator. Specifically check:
   - Does the spec format match BOOTSTRAP's spec format? (Same headings, same sections, same level of detail.)
   - Did the spec gate (R8.A) fire correctly — blocking the edit until the spec was committed?
   - Did the implementer subagent invoke worktree isolation per BOOTSTRAP?
   - Did the reviewer subagent produce a review artifact in the same format BOOTSTRAP produces?
   - Did the audio alerts fire on task-done and any decision-required events?
   - Were the right models used per the Model Assignment Strategy table?

   The AI presents findings to the operator categorized into three buckets: (a) **bugs** in the retrofit's R8 setup that need fixing; (b) **documented variations** that the operator deliberately chose, in which case verify the variation is recorded in `tech.md`; (c) **archetype-conditional differences** (e.g., a CLI tool that legitimately doesn't have the eval gate that an AI/agent project would). Operator confirms each bucket assignment.

7. If anything is off, return to the relevant phase (likely R4 or R8) and adjust. If documented variations are missing from `tech.md`, return to R2 to record them.

**Exit criteria:** Either smoke-test artifacts exist (stage 1 minimum, stage 2 ideally) and the equivalence check passes (or discrepancies are explicitly accepted as documented variations), or operator opted to skip.

---

## Phase R7 — Handoff

**AI actions:**

1. Summarize what was built. List every file created with a one-line description.

2. **Equivalence validation.** Walk through the BOOTSTRAP Equivalence Target checklist (six categories — Steering / Specs / Hooks / Model Assignment / Audio Alerts / Subagent Workflows). For each item:
   - **✓** if present and matches BOOTSTRAP's defaults.
   - **✓\*** if present with documented INTENTIONAL VARIATION in `tech.md`.
   - **✗ (archetype-conditional)** if legitimately not applicable (e.g., eval gate for a CLI tool, Mobile store-deploy gate for a Service/API).
   - **✗ (incomplete)** if missing without justification — the retrofit is not yet complete and needs to return to the relevant phase.

   Write the checklist to `.claude/inventory/equivalence-validation.md`. If any items are ✗ (incomplete), return to the relevant phase before continuing. The checklist is itself a deliverable — operators can re-run the validation in 30/60/90 days to verify the workflow continues to behave as expected.

3. Show the debt registry total: "X items registered, Y high-severity. This work is tracked but not in scope for retrofit completion."

4. **Schedule baseline measurement reviews (G9).** From `.claude/inventory/baseline-metrics.md`, schedule re-measurement at 30/60/90 days post-retrofit:
   - Lead time for changes — should hold or improve.
   - Change failure rate — should hold or improve.
   - Test coverage — should grow as touch-based backfill produces tests.
   - Lint conformance rate — should reach 100% as the lint gate enforces it.
   - Spec coverage — starts at 0%; growth rate is the retrofit's clearest success metric. Track per-sprint additions, not absolute coverage (per Augment Code 2026's brownfield SDD measurement guidance).
   - **Drift rate** — schema validation failures per sprint, contract test failures, spec revision frequency. Drift is the natural state that must be continuously governed.
   - DORA performance tier reassessment annually.

   Note in `tech.md`'s `## Migration Notes` section: "30/60/90-day baseline review scheduled."

5. **Disable retrofit-active mode.** Update `.claude/.retrofit-state.json` to mark retrofit complete. Set `retrofit_complete: true` and `retrofit_active: false`. The spec-gate-commit hook now operates normally — no more allowlisting `.claude/` writes for the retrofit itself.

6. **Portfolio canonicalization (if this is the first retrofit).** Ask: "Which conventions from this retrofit do you want to lift to portfolio defaults for future retrofits?" Suggested defaults: `.claude/sessions/` schema, `decisions.md` schema, hook structure, command names, agent role names, audio alert config. Project-local always: `principles.md`, `tech.md`, `structure.md`, `deps.md`, `secrets.md`, `ci-cd.md`, `debt.md`, `inventory/`. Document the chosen portfolio defaults somewhere the operator can find them when retrofitting the next project.

7. **For projects that opted into any autonomous mode (R8.G/H/I, v1.6.0):** state the scaffold-but-defer posture explicitly and record the gate:
   - "Autonomous mode scaffolding for [loop / goal-supervised / queue] is present but **disabled**. It is not safe to enable on a freshly-retrofitted brownfield project."
   - Print the per-mode brownfield milestone from `.retrofit-state.json.autonomous_modes.brownfield_milestones` as a checklist the operator can re-evaluate later: rollout-steady-state status, touch-based-specs-under-blocking-gates count vs threshold, legacy-allowlist shrink % vs threshold, (R8.H) mode-selection ledger entries, (R8.I) all-hooks-blocking + weeks-of-per-task-operation.
   - "To enable: satisfy the milestone, then manually set the corresponding `*_enabled` flag to true and re-confirm. The wizard will not do this for you. Re-running the equivalence validation (`inventory/equivalence-validation.md`) after enabling confirms the scaffolding is still BOOTSTRAP-shaped."
   - Recommend a calendar reminder tied to the R8.A.6 rollout schedule's steady-state date, since the earliest milestone component (gates blocking) is time-bounded by that schedule.

8. **Operator's immediate next steps:**
   - Commit `.claude/`, `docs/prd/` (if any was authored), and any updates to existing files (likely none).
   - Run `/spec-new <first-real-feature>` to start using the workflow.
   - Schedule a periodic review of `debt.md` (default suggestion: monthly) to track resolution and add new items.

9. **For projects with applicable regulatory frameworks (G20):** point the operator at `.claude/steering/compliance.md` and remind them:
   - The retrofit is itself a "significant change" / change-control event in most regulated regimes. It may need to be documented in the existing change-control system (POA&M for FedRAMP; DHF entry for medical device; ROC update for PCI; records of processing update for GDPR; etc.).
   - The new hooks introduced by this retrofit have audit-effectiveness windows starting today. SOC 2 Type II evidence should reflect the new control set going forward.
   - The retrofit's reviewer subagent providing pre-production code review may or may not satisfy the operator's regulatory regime's review requirements (e.g., PCI-DSS 6.2.3.1) — operator confirms with their auditor / QSA / notified body before relying on it.

10. **For projects on PM Strategy A or C (v1.4):** point the operator at `.claude/inventory/ticket-migration-queue.md` and `.claude/steering/workflow-source-of-truth.md`. Remind them:
   - The convert-now ticket list is queued. Run `ticket-to-spec <ticket-id>` for each, or invoke batch mode for all at once. Most operators do batch mode the day after retrofit completes when context is fresh.
   - For Strategy A: archive the legacy ticket tracker after all convert-now tickets are migrated. Update CI to remove ticket-status-update steps.
   - For Strategy C: the cutover date is recorded; the 90-day review will surface a "should we move to A or formalize as B?" decision. Calendar reminder recommended.
   - Specs created via `ticket-to-spec` start as stubs. Refine each before invoking `/spec-review`; treat the auto-generated spec as a strong first draft, not a finished artifact.

11. Note explicitly:
   - Steering docs are living. Update when conventions change. The Canonical / Deprecated / Intentional Variation / Modernized categorization in `tech.md` will need revisiting periodically.
   - Legacy allowlist shrinks over time as files get touch-based specs. When it's empty, retrofit is fully complete (no special handling needed for any file).
   - For portfolio standardization: if you retrofit another project, the AI in that project's R0 should read this project's `.claude/` for portfolio defaults.
   - **The retrofit does not fix technical debt.** That work is separate, tracked in `debt.md`, and outside the scope of this protocol.
   - The escalation list in `CLAUDE.md` is the contract — if the agent escalates outside it, that's a bug to fix in steering, not behavior to override in-session.
   - The equivalence validation checklist (`.claude/inventory/equivalence-validation.md`) is rerunnable. If you suspect drift from BOOTSTRAP-equivalence over time, re-run it.
   - **Autonomous modes, if scaffolded, stay OFF until their brownfield milestone is green.** *(v1.6.0)* The milestone is about gate trustworthiness on this codebase, not elapsed time alone. Enabling early is the documented failure mode, not an optimization.

**Exit criteria:** Equivalence validation passed (all six categories' items either ✓, ✓\*, or ✗-archetype-conditional — autonomous-mode scaffolding, if opted in, is ✓ when present-and-default-disabled-with-milestone-recorded; ✗-operator-declined is valid if not opted in). Operator confirms readiness to start real work on this project. Retrofit-active mode disabled. Baseline measurement reviews scheduled. Portfolio defaults documented if applicable. Compliance pointers communicated if applicable. **Ticket-migration queue communicated if Strategy A or C. Autonomous-mode milestones communicated if any mode opted into.**

---

# Phase R8 — Bootstrap-Equivalent Phases (Embedded Inline)

R8 covers the equivalents of BOOTSTRAP Phases 5, 6, 6.5, 7, 7.5, 8, plus the three optional autonomous modes (9.5, 9.6, 9.7), with retrofit-specific adjustments embedded inline. **In v1.0 this section was "go read BOOTSTRAP and apply these adjustments." In v1.1 it's all here, self-contained, so the AI executes from one document — with the single deliberate exception of R8.D (Spec Versioning), which has no retrofit adjustment and is run by-reference against BOOTSTRAP §7.5 to avoid maintaining a drift-prone verbatim copy.** Read BOOTSTRAP / BOOTSTRAP-COMPANION for context if needed; execute from here (and read BOOTSTRAP §7.5 directly when you reach R8.D).

The sub-phase ordering aligns with BOOTSTRAP's ordering (5 → 6 → 6.5 → 7 → 7.5 → 8 → 9.5 → 9.6 → 9.7) but is renamed R8.A through R8.I so the protocol's numbering is internally consistent. R8.G/R8.H/R8.I (the autonomous modes) are **opt-in and run only if the operator opted in at R0.5**; even then they *scaffold but do not enable* — see §"Autonomous Modes in Retrofit."

---

## R8.A — Hooks (`.claude/settings.json` and `.claude/hooks/`)

**Goal:** Install deterministic guardrails. **Equivalent to BOOTSTRAP Phase 6.**

### A.1 — Caveats (same as BOOTSTRAP §6.A)

- Hooks run per-tool-call, not per-task.
- Hooks may not have direct access to model token counts; cost log is session-end summary.
- Hooks can be disabled by renaming `.claude/settings.json` to `.disabled`.
- **Don't block file writes mid-plan.** Spec gate is split into entry-warn + commit-block per BOOTSTRAP §6.A. Secrets are the only mid-plan exception.
- **Use `async: true` for slow hooks** (>2 seconds).

### A.2 — Complementary built-ins (same as BOOTSTRAP §6.B)

- `claude --permission-mode auto`
- Permission allowlists
- Sandboxing (worth considering for `implementer` subagent)

### A.3 — Hook installation (retrofit-flavored)

**AI actions:**

1. Explain hooks vs skills. Mention complementary built-ins.

2. **Read archetype from `.claude/.retrofit-state.json`** to filter the recommended hook set. Some hooks are only meaningful for certain archetypes; surfacing irrelevant ones increases configuration noise without value.

3. Propose the archetype-filtered hook set with **retrofit-specific adjustments noted per hook**:

   **Always recommended (any archetype):**

   - **Spec gate (entry)** — `UserPromptSubmit` hook. Same as BOOTSTRAP. **Retrofit adjustment:** the warning is suppressed for files in the legacy allowlist from R4's `spec-strategy.md`.

   - **Spec gate (commit)** — `PreToolUse` on `Bash` matching `git commit`. **Retrofit adjustments:**
     - Honors the legacy allowlist (if a file in the diff is in `spec-strategy.md`'s allowlist, it's exempt from the active-spec check).
     - Honors the **retrofit-active allowlist** while `.claude/.retrofit-state.json` shows `retrofit_active: true`. This allows commits that touch only `.claude/` paths during the retrofit itself. R7 disables this when retrofit completes.
     - Both allowlists are read at hook runtime, not baked into the script — so updating `spec-strategy.md` doesn't require re-installing the hook.

   - **Secrets gate** — `PreToolUse` on Read/Write/Edit. Same as BOOTSTRAP. No retrofit adjustment — secrets are catastrophic regardless of legacy status. **Skip only if R0.5 confirmed no secrets in any form (rare).**

   - **Format/lint gate** — `PostToolUse` on Write/Edit. **Retrofit adjustment: warning mode for the first week.** Existing code may not pass current lint config. After a week, the operator can flip to blocking via `.claude/hooks/lint-mode` (`warn` or `block`). Default is `warn` for retrofit; `block` for greenfield.

   - **Cost log** — session-end summary. Same as BOOTSTRAP.

   - **Drift detector** — soft notice for tiers 1–2; **hard block for tier 3**. Same as BOOTSTRAP (tier-3 enforcement is standard as of the BOOTSTRAP v1.9.0 this protocol targets; see BOOTSTRAP Phase 6 §6.D/§6.E). One of three audio alert categories — see A.5.

   - **Task-done alarm** — `SubagentStop` hook. Same as BOOTSTRAP. One of three audio alert categories.

   - **Decision-required alarm** — `Notification` hook + state-file watcher. Same as BOOTSTRAP. Most urgent of three audio alert categories.

   - **Test gate** *(any archetype — BOOTSTRAP Phase 6 `(all)`)* — `PreToolUse` on git commit. **Retrofit adjustment: grandfather clause (✓\* INTENTIONAL VARIATION).** Modules listed as having no tests in `.claude/inventory/testing.md` are exempt from the test-required check (with a warning), read from inventory at hook runtime. New modules require tests as normal. A project with no test framework at all records the gate as ✓\* INTENTIONAL VARIATION in `tech.md` (grandfather) — **not** a silently dropped hook; only then is the script body itself omitted, with a `debt.md` entry. This is the sanctioned escape valve, not a re-tier.

   - **Dependency gate** *(any archetype — BOOTSTRAP Phase 6 `(all)`; skip only if R5.5 deps was skipped for a stdlib-only project, which is BOOTSTRAP's sole carve-out, not an archetype condition)* — `PreToolUse` on `Bash` calls matching package-install patterns. Same as BOOTSTRAP. References `deps.md`.

   **Recommended if archetype includes the relevant signal:**

   - **CI mirror** *(skip if R0.5 marked R8.F as opt-out)* — `PreToolUse` on git push. Same as BOOTSTRAP's `(all *with CI*)` tag — the conditionality is BOOTSTRAP-faithful, not a re-tier. No CI = no mirror; the hook would have nothing to do.

   - **TDD gate** *(only if R5 enabled TDD policy)* — `PreToolUse` on Write to a source file. Conditional exactly as BOOTSTRAP. **Retrofit adjustment:** exempts files in the legacy allowlist (forcing TDD on legacy edits would block almost everything).

   **Archetype-specific:**

   - **Eval gate** *(AI/agent system archetype only)* — `PreToolUse` on git push or merge commits touching prompt files. Same as BOOTSTRAP. **Skip silently for any other archetype** — irrelevant noise.

   - **Public API stability gate** *(Library/SDK archetype only — recommended, not required)* — `PreToolUse` on git commit, scans the diff for changes to public API surface (`__init__.py`, `index.ts`, `*.pyi`, etc.). Warns if a public-surface change isn't accompanied by a version bump. Operator approves the addition explicitly; not on by default.

   - **Cross-component contract gate** *(Platform / multi-component archetype only — recommended, not required)* — `PreToolUse` on git commit, scans the diff for changes to files identified in `contracts.md` (per G5). Warns when a contract changes without a corresponding update across all consumers. Surfaced for operator approval; not on by default.

   - **Mobile store-deploy gate** *(Mobile app archetype only)* — `PreToolUse` on relevant build/release commands. Confirms keystore handling, version bumps, and store metadata. Operator approves.

4. For each accepted hook, write the script under `.claude/hooks/<hook-name>.sh` (or `.py`). **Show the script content to the operator before writing it.**

5. Wire each hook into `.claude/settings.json` with the correct trigger event.

6. Test each hook by triggering it with a known-good and known-bad input. **Test the retrofit-active allowlist explicitly** — confirm a `.claude/` write commits cleanly while retrofit is active.

7. Show and ask: **approve / edit / start over**.

### A.4 — Hook security & correctness checklist (same as BOOTSTRAP §6.D)

Run through this for every hook script before showing it to the operator. See BOOTSTRAP §6.D for the full list (no eval, no curl|bash, paths quoted, variables validated, no hardcoded creds, network calls allowlisted, chmod 700, audit logging, exit codes 0/1/2, executable bit set, jq available, shell profile noise guarded, stop hook check `stop_hook_active`, matcher case-sensitive, correct event chosen, tested with `/hooks`).

### A.5 — Audio alert system (retrofit-flavored)

**Equivalent to BOOTSTRAP §6.E.** This is where retrofit's prior-art reckoning matters most.

#### Three categories at a glance (same as BOOTSTRAP)

| Category | Trigger | Urgency | Frequency | Acknowledgement |
|---|---|---|---|---|
| **Drift detector** | Context degradation proxies cross thresholds | **Soft for tiers 1–2 (advisory); hard for tier 3 (operator is blocked)** | Degrading: gentle → insistent → firm + enforced | Required for tiers 1–2 (action button or `/ack-drift`); **tier 3 cleared only by checkpoint + `/clear`** |
| **Task done** | Subagent completes (`SubagentStop` event) | Soft (informational) | Every completion | Not required |
| **Decision required** | AI hits an *urgent* escalation criterion (do-not-touch, secret, hook block, dependency, spec-wrong) | Hard (operator is blocked) | Once per escalation event | Implicit: resolved when operator responds |

#### Retrofit-specific prior-art reckoning

If the inventory's `prior-art.md` or `claude-md-extraction-plan.md` flagged an **existing audio convention** (e.g., a single `paplay` invocation in the existing CLAUDE.md, or a custom alert script in `.claude.archived-*/`), R2 will have categorized it. Three branches:

- **CANONICAL** — operator wants to keep prior art exactly as it is. The audio system installs around it: adopt the prior-art sound for `decision-required` (the closest match to a "stop and notice" alarm), generate `task-done` and `drift` sounds via the BOOTSTRAP §6.E flow, and merge the prior-art invocation into the new hook scripts.
- **MODERNIZE → adopt fully** — operator chose to replace prior-art with the full three-category system. Generate all five sounds, install all three hooks, archive the prior-art invocation in `.claude.archived-*/` for reference.
- **MODERNIZE → hybrid** — operator wants to keep one or more prior-art elements and modernize the rest. Configure `.claude/hooks/audio-alerts.config` per the operator's choices: each category can independently use a custom sound file path (prior-art) or a generated default.

#### Shared infrastructure (same as BOOTSTRAP §6.E)

- **Session identity:** session ID generated at first hook invocation, stored at `.claude/sessions/.session-<id>`. State files namespaced by session ID. Old state files (>7 days) purged.
- **OS-specific dispatch:** dunstify on Linux with action-supporting daemon; plain notify-send fallback; osascript on macOS; New-BurntToastNotification on Windows; in-chat fallback for headless/SSH.
- **Sound files:** `~/.claude/sounds/` with five WAVs (drift-gentle, drift-insistent, drift-firm, task-done, decision-required) — generated via sox/ffmpeg if available, or operator-supplied. Hooks robust to missing sound files.
- **Quiet mode:** `/quiet on`, `/quiet off`, `/quiet 2h`. **Decision-required and drift tier 3 both override quiet mode** — these are the two "blocking" alarm categories where audio plays even when quiet is active. Decision-required overrides because the agent is literally blocked; drift tier 3 overrides because operator self-override at saturated context is the failure mode the protocol exists to prevent. (Standard behavior as of BOOTSTRAP v1.9.0; first introduced in BOOTSTRAP v1.6.1, mirrored here since RETROFIT v1.5.1.)
- **Hook exit codes:** 0/1/2 per BOOTSTRAP convention.

#### Configuration file

`.claude/hooks/audio-alerts.config` per BOOTSTRAP Phase 6 §6.E (drift thresholds, audio enabled flags, notification daemon detection, quiet-mode override, state-retention days). The config includes `drift_tier3_enforced=true` (tier 3 hard-blocks tool calls until `/clear`) and `quiet_mode_overridden_by_drift_tier3=true` (tier 3 audio plays even when quiet mode is active) — standard as of the BOOTSTRAP v1.9.0 this protocol targets. For retrofit, both flags default to true; if prior-art reckoning surfaced a custom drift handler the operator wants to keep, document the divergence as INTENTIONAL VARIATION in `tech.md`.

For retrofit-MODERNIZE-hybrid choices, the per-category audio file paths in this config point at the prior-art files for kept categories and at generated defaults for modernized ones.

#### End-of-R8.A distinguishability test

Same as BOOTSTRAP: play all five sounds in sequence, ask operator if they're distinguishable from each other and from system sounds. If "swap files" or "regenerate," handle accordingly.

#### R8.A.6 — Hook Rollout Discipline (G14)

Pre-existing projects often have developers who've gotten used to fast, ungated commits. Introducing the full hook set on day one — especially the spec gate that blocks code changes without specs — produces immediate friction that drives bypass behavior. Per the MLOps Coding Course and GitGuardian practitioner guidance: **graduate the rollout warn → block per hook over 2-4 weeks**, monitor bypass rates, adjust accordingly.

**Default rollout schedule** (operator can override):

| Week | Status | What blocks | What warns |
|---|---|---|---|
| Week 1 | All hooks installed | Nothing (warn-only mode) | Everything that would block in steady state |
| Week 2 | Lint and format hooks block | Lint, format | Spec gate, test gate, TDD gate, eval gate |
| Week 3 | Test gate blocks | Lint, format, test | Spec gate, TDD gate, eval gate |
| Week 4+ | Steady state | All hooks | (none) |

Document the chosen schedule in `.claude/hooks/rollout-schedule.md`. The schedule is project-specific — a project with low pre-existing test coverage might extend Week 3 longer; a project with high spec discipline already might compress the schedule.

**Bypass-rate monitoring (G14):** Track `--no-verify` usage to detect unhealthy bypass patterns. Two implementation paths:

- **Local-developer signal (recommended for solo / small teams):** add a `pre-push` hook that increments a counter in `.claude/sessions/.bypass-count-<week>` whenever the hook detects the previous commit was made with `--no-verify`. The pre-push hook can examine `git log -1 --format=%B` for telltale signs (commit-time inconsistencies, missing CI markers) or rely on a wrapper that records `--no-verify` invocations explicitly. Surface counts in retrofit state.
- **Server-side signal (recommended for organizations with shared remote):** the pre-receive hook layer (see "Server-side enforcement layer" below) can log every push that bypassed pre-commit, attributable per author. More authoritative.

Per DevSecOps Now's reasonable-target heuristic: aim for **90%+ pass rate** on each hook; if bypass rates exceed 10% sustainedly, the hook is either too strict, buggy, or the rollout schedule needs adjustment. Don't tune by tightening; tune by understanding why bypasses happen. For solo-dev projects, this is informal — the operator self-monitors.

**Server-side enforcement layer (optional):** for organizations with GitHub/GitLab and the need for organization-wide enforcement (vs developer-local guardrails), a **pre-receive hook layer** on the server provides coercive enforcement that pre-commit hooks cannot. Document this option for the operator; out of scope for the retrofit itself but worth flagging.

#### R8.A.7 — Worktree Resource Budgeting (G16)

Per Augment Code 2026: a 2GB codebase consumes ~10GB of disk in a 20-minute multi-worktree session. For codebases over **1GB total source size**, document the resource expectation in `.claude/hooks/worktree-budget.md`:

- Expected disk usage per worktree session (~5x codebase size)
- Per-worktree database instance and Docker volume naming convention (per-worktree-uuid prefixes)
- For codebases over 5GB, recommend **sequential worktrees over parallel** unless operator has substantial disk headroom
- For codebases under 1GB, no special documentation needed; standard worktree isolation is fine

Boris Cherny (Anthropic, Claude Code lead, per InfoQ): the canonical pattern is "separate git checkouts for each local session" when working on large batch changes. Worktrees provide this without the overhead of full clones.

#### R8.A.8 — Regulated-industry hook stubs (G20.3 lite)

For projects where R0 step 10 detected applicable regulatory frameworks, document the hooks that *would* be added for full G20 coverage in v1.4. **In v1.3 these are documentation only — not enforced.** This is deliberate; the hook implementations need real-regulated-project validation before standardization.

Document in `.claude/steering/compliance.md`:

- **Audit log hook** *(SOC 2 / HIPAA / FedRAMP)* — would capture every Claude Code action with timestamp, user, tool, into long-term storage. Audit-window length: 6-12 months minimum. **In v1.3:** rely on Claude Code's built-in session logging plus operator's existing audit-log infrastructure.
- **PHI redaction hook** *(HIPAA)* — would scan prompt content for PHI patterns before sending to AI provider; block if found. **In v1.3:** rely on operator's existing data-classification practice; document the gap as a `debt.md` entry if PHI could appear in code/prompts.
- **Cardholder data redaction hook** *(PCI-DSS)* — would scan for PAN patterns. **In v1.3:** same as above for PHI redaction.
- **EOL dependency block** *(PCI-DSS Requirement 6)* — would prevent adoption of EOL packages. **In v1.3:** the deps.md already records EOL status; block at PR review rather than commit.
- **Cross-component safeguard uniformity check** *(HIPAA)* — would verify all PHI-touching components have access controls + audit logging + integrity + transmission security configured. **In v1.3:** documented in `compliance.md` as a periodic manual check.

**Exit criteria for R8.A:** `settings.json` exists, hook scripts are executable, spec gate (entry + commit), test gate, and audio alert categories tested. Retrofit-active allowlist tested explicitly. Operator has approved all hook scripts. Audio prior-art reckoning completed. Hook rollout schedule documented (R8.A.6). Worktree budget documented if codebase > 1GB (R8.A.7). Regulated-industry hook stubs documented in `compliance.md` if applicable (R8.A.8).

---

## R8.B — Tools & MCP Configuration

**Goal:** Decide which built-in features and MCP servers to enable. **Equivalent to BOOTSTRAP Phase 6.5.**

Same content as BOOTSTRAP §6.5: verify built-in features (tool search, worktree isolation, hooks, auto memory), recommend MCP servers per archetype and operator profile.

**Retrofit-specific recommendation:** add **Claude Context** (semantic codebase search) to the recommended MCP set if the source-file count is over ~200. For retrofit, the AI's ability to find relevant code without scanning everything every time is materially more valuable than for greenfield, where files don't exist yet.

For solo developers retrofitting their own codebase, the recommended kit becomes: **GitHub MCP + Claude Context** (no memory MCP at start — auto memory + structured artifacts cover it).

**PM-tool MCP installation (v1.4 — defer to R0.7 decision):** unlike BOOTSTRAP's open question of "is the project tracker your source of truth?", retrofit has already answered this in R0.7. Read `pm_strategy` from `.retrofit-state.json`:
- **`spec_canonical`:** PM-tool MCP NOT installed. Document in `tools.md` "Linear/Jira/GitHub Issues MCP NOT installed: per R0.7 source-of-truth decision, specs in `.claude/specs/` are canonical. PM tool, if used at all, is community-facing only."
- **`pm_canonical`:** PM-tool MCP installed (Linear MCP, Jira MCP, or GitHub MCP — depending on `pm_tool` field). Document the spec-frontmatter convention for back-linking specs to tickets.
- **`hybrid`:** PM-tool MCP installed for the transition window. Document the 90-day review checkpoint.

Memory MCP guidance, anti-patterns, and Tier 1/2/3 framing — same as BOOTSTRAP.

Write `.claude/steering/tools.md` with: built-ins relied upon, MCPs installed and rationale, MCPs considered and rejected with reason, "don't add" guardrail list. **Cross-reference `workflow-source-of-truth.md`** for PM-tool MCP rationale. Verify cold-start context budget under 20K tokens.

**Exit criteria:** `tools.md` exists. MCPs installed (per R0.7 PM strategy). Cold-start context budget acceptable.

---

## R8.C — Skills, Commands, Agents, and Workflow

**Goal:** Install the skill set and define the per-task workflow. **Equivalent to BOOTSTRAP Phase 7.**

### The per-task lifecycle

Same as BOOTSTRAP — 6 gates if TDD off, 7 if TDD on. Spec → review → decompose → plan-review → implement → code-review → spec-validate. `decision-log` runs throughout; `pr-author` runs after gate 7.

### Skills to create (under `.claude/skills/<skill-name>/`)

**BOOTSTRAP-derived (same as BOOTSTRAP §7):**

- `spec-new`, `spec-review`, `spec-decompose`, `plan-review`, `spec-validate`, `test-author` (if TDD on), `code-review`, `decision-log`, `pr-author`, `checkpoint`, `resume`, `ack-drift`, `quiet`, `quiet-task-done`.

**Retrofit-specific additions:**

- `legacy-spec` — generates a brief spec for a legacy module being modified for the first time. Used in touch-based backfill flow. Output is `.claude/specs/<module-slug>/requirements.md` documenting current behavior plus the change being made. **Model: Sonnet 4.6** — pattern work against existing code.
- `legacy-pin-test` *(v1.3, G6)* — generates a characterization test for a legacy module before modification. Reads the current code, generates pinning tests (input/output capture, golden-output comparisons, snapshot-style tests as appropriate to the language). Output is a test file under the project's standard test path. The test passes against unchanged code; failures during subsequent modification surface unintended behavior changes. **Model: Sonnet 4.6** — pattern work. Used by R2/R6/R8.A whenever code in `inventory/danger-zones.md` or in the legacy allowlist is about to be modified.
- `boundary-spec` *(v1.3, G8)* — generates a dependency boundary spec (machine-readable contract) for a service contract or public API surface. Output: `.claude/steering/contracts.md` entry + machine-readable artifact (OpenAPI YAML, JSON Schema, .proto, etc.). Validates against `inventory/traffic-sample.json` if available (G18). **Model: Sonnet 4.6** — pattern work translating existing code into machine-readable contract.
- `prompt-pinning-eval` *(v1.3, G15 AI/agent only)* — generates a characterization eval (golden-dataset baseline) for a prompt before modification. The AI/agent equivalent of a pinning test. Captures: input examples representative of production traffic, current prompt's output for each, evaluation rubric (correctness criteria). The eval becomes the regression-prevention baseline for prompt changes. **Model: Sonnet 4.6** — pattern work.
- `dataset-pin-test` *(v1.3, G15 Data/ML only)* — generates reproducibility-validation tests for a data pipeline stage. Captures: dataset version (with hash or version-control tag), env (Python version, framework versions, CUDA toolkit), random seed, expected output checksum. Test fails if any of these change unexpectedly. The data-pipeline equivalent of a pinning test. **Model: Sonnet 4.6** — pattern work.
- `migration-plan` (optional, install only if R5/R7 generated concrete migration plans for Deprecated patterns) — decomposes a deprecated pattern's removal into safe, reversible steps. **Model: Opus 4.7** — judgment work.
- `ticket-to-spec` *(v1.4, G21, install conditions: REQUIRED if R0.7's `pm_strategy` is `spec_canonical` or `hybrid`; OPTIONAL if `pm_strategy` is `pm_canonical` — operator opts in/out at R0.7 step 4 strategy presentation)* — converts an existing ticket (from Linear/Jira/GitHub Issues/in-repo `tickets/`) into a spec stub. Reads ticket title, description, acceptance criteria, comments. Generates `.claude/specs/<slug>/requirements.md` with: problem statement (from ticket description), acceptance criteria (in EARS notation per R5 step 3.5 if applicable, otherwise list form), original-ticket-link in frontmatter. Operator refines the auto-generated spec before approving. **Model: Sonnet 4.6** — pattern work translating ticket into spec format.
  - **Input handling:** for each PM tool, the skill knows the format. Linear: read via Linear MCP if installed, else operator pastes ticket markdown. Jira: read via Jira MCP if installed. GitHub Issues: read via `gh issue view <id>` or GitHub MCP. In-repo `tickets/`: read the markdown file directly.
  - **Frontmatter convention:** `original_ticket: linear/LIN-123` or `original_ticket: tickets/AGT-042.md`. Spec validation tooling can verify back-link integrity.
  - **Batch mode:** for the R0.7 convert-now list, the skill can be invoked with a ticket-list argument to produce all stubs at once. Operator reviews the batch output, refines, approves.
  - **Migration discipline:** the skill produces a *stub* — it does NOT close the original ticket. Closing the ticket is a deliberate operator action after the spec is finalized and the work is done.

**During R8.C, when `ticket-to-spec` is being installed:** read `.retrofit-state.json`'s `ticket_migration_disposition.convert_now` array and write `.claude/inventory/ticket-migration-queue.md` listing each ticket ID with its status (initially "pending"). Post-retrofit, when the operator runs `ticket-to-spec` for a ticket, the skill updates that file's status to "converted" with the resulting spec slug. This gives the operator a visible work queue and a record of conversions. For Strategy B (where ticket-to-spec is optional and on-demand), this queue file is not produced.

### Subagents to create (under `.claude/agents/`)

Same as BOOTSTRAP §7 step 3, with retrofit-specific behavioral additions for pin-first discipline (G6) and code health awareness (G10):

- **`implementer`** — `model: sonnet`, `isolation: worktree`. **Retrofit-specific instructions:**
  1. When the task touches a file in the legacy allowlist, the implementer's behavior is (1) read the file to understand current state, (2) run `/spec-new` for the module via `legacy-spec` skill (touch-based backfill), (3) the spec is brief — current behavior + change, (4) after modification, the file is removed from the legacy allowlist (it now has a spec).
  2. **Pin-first discipline (G6):** when the task touches a file in `inventory/danger-zones.md` (R2 G10) or in the legacy allowlist, the implementer ALSO runs `legacy-pin-test` before any modification. The pinning test must pass against current unchanged code; if not, the implementer pauses and surfaces "current behavior is different from what the test captures — operator review needed." Per Feathers' pinning test technique.
  3. **Worktree resource budgeting (G16):** for codebases over 1GB (per `.claude/hooks/worktree-budget.md`), the implementer can be configured for sequential rather than parallel worktrees. Default behavior unchanged for smaller codebases.
  4. **For AI/agent archetype:** when the task modifies a prompt file, the implementer runs `prompt-pinning-eval` first (analogous to `legacy-pin-test` for code) to capture current behavior on a golden dataset. The eval becomes the regression baseline.

- **`reviewer`** — `model: opus`, `effort: high`, `tools: Read, Grep, Glob, Bash` (no Edit/Write). **Retrofit-specific instructions:**
  1. When reviewing a diff against a legacy file, the review checks the change against the new spec, not against all current principles (legacy code may not conform — that's tracked in `debt.md`).
  2. **Danger-zone reviewer rule (G10):** when reviewing a diff against a file in `inventory/danger-zones.md`, enforce strictly: **no architectural change in the same PR as a behavior change**. If the diff combines both, the reviewer requests the operator split the PR. Per Tornhill via Fowler 2026: AI-modified unhealthy code carries 30% higher defect risk; combining architectural and behavioral changes in unhealthy zones is the riskiest pattern.
  3. **Pin-first verification (G6):** when reviewing a diff against a danger-zone or legacy-allowlist file, verify that an accompanying pinning test exists in the diff. If absent, the reviewer requests it before approval.

- **`integrator`** — `model: inherit`. Same as BOOTSTRAP.

### Other artifacts

- `.claude/specs/INDEX.md` — living task board with documented schema (same as BOOTSTRAP).
- `.claude/learnings/` — README explaining cross-feature insights convention.
- `.claude/sessions/` — README documenting checkpoint schema and audio alert state-file mechanisms.

### Gitignore block (retrofit-flavored)

Append to project `.gitignore`:

```
# Bootstrap state — local, do not commit
.claude/.bootstrap-state.json
.claude/.bootstrap-state.json.pre-1.7
.claude/.bootstrap-state.json.pre-1.8
.claude/.bootstrap-state.json.pre-1.9
.claude/.bootstrap-incomplete

# Retrofit state — local, do not commit
.claude/.retrofit-state.json
.claude/inventory/.scan-cache-*

# Session state files (audio alerts, drift, quiet mode)
.claude/sessions/.session-*
.claude/sessions/.drift-ack-*
.claude/sessions/.drift-state-*
.claude/sessions/.drift-tier3-*
.claude/sessions/.decision-pending-*
.claude/sessions/.quiet-*
.claude/sessions/.bypass-count-*

# Autonomous-mode state (only present if R8.G/H/I scaffolded; v1.6.0)
.claude/sessions/.loop-active-*
.claude/sessions/.loop-complete-*
.claude/sessions/.loop-halt-*
.claude/sessions/.goal-active-*
.claude/sessions/.iteration-summary-*
.claude/sessions/.evaluator-feedback-*
.claude/queue/.run-active
.claude/queue/.halt
.claude/queue/.resume

# Logs
.claude/logs/

# Archived prior `.claude/` (preserved during retrofit; do not commit historical state)
.claude.archived-*/
```

Operator-facing artifacts (`CLAUDE.md`, `.claude/steering/*.md`, `.claude/specs/`, `.claude/learnings/`, `.claude/agents/`, `.claude/hooks/`, `.claude/commands/`, `.claude/skills/`, `.claude/sessions/*-checkpoint.md`, `.claude/sessions/decisions-log-*.md`, `.claude/sessions/loop-final-*.md`, `.claude/inventory/*.md`, `.claude/debt.md`, and — when scaffolded — `.claude/queue/backlog.md`, `.claude/queue/run-summary-*.md`) are committed normally. Per-task loop artifacts (`decisions-log-*.md`, `loop-final-*.md`) use regular naming precisely because they are operator-facing audit records that belong in the repo, exactly as BOOTSTRAP Phase 7 step 7 specifies.

**Exit criteria:** All skill, command, agent files exist. INDEX, learnings, sessions directories initialized. Decision-log, checkpoint, drift-ack, quiet-mode conventions documented. Retrofit-specific skills and instructions installed. Gitignore block present.

---

## R8.D — Spec Versioning Protocol

**Goal:** Same as BOOTSTRAP Phase 7.5. Skippable for solo, short-lived projects.

No retrofit-specific adjustments. This is the one R8 sub-phase executed by-reference (see the carve-out in the "For the AI" note and the R8 intro): run BOOTSTRAP §7.5 as-is, reading its nine AI actions directly from `BOOTSTRAP.md`. It is deliberately not re-embedded here — spec versioning is identical to BOOTSTRAP's with no brownfield flavor, so a verbatim copy would add drift risk without adding content. Retrofit note: the same protocol applies to touch-based-backfilled legacy specs (they carry `version:` from first authoring) and to project-specific versioned steering docs such as `phase.md`.

**Exit criteria:** Versioning protocol documented in `.claude/steering/spec-versioning.md`. Skills and INDEX schema updated.

---

## R8.E — Root `CLAUDE.md` and Escalation Rules

**Goal:** Write the thin index that ties everything together. **Equivalent to BOOTSTRAP Phase 8 — but with substantial retrofit-specific work because pre-existing CLAUDE.md content needs to be migrated, not overwritten.**

### E.1 — Pre-existing CLAUDE.md migration (retrofit-only step)

If `.claude/inventory/claude-md-extraction-plan.md` exists from R0 step 5, execute it now. For each section of the existing CLAUDE.md classified in R0:

- **Belongs in steering doc X:** verify the content has been incorporated into the relevant steering doc during R2/R5/R5.5. If not, do it now. **G5:** "steering doc X" includes both the BOOTSTRAP-standard set (`product.md`, `tech.md`, `principles.md`, `structure.md`, `deps.md`, `secrets.md`, `ci-cd.md`, `tools.md`) AND project-specific docs created during R5 step 3 (e.g., `phase.md`, `contracts.md`, `workflow.md`, `roles.md`). Do not force project-specific content into ill-fitting standard slots — that's the failure mode G5 closes.
- **Belongs in agent prompt Y:** verify it's been incorporated into the relevant skill or subagent definition during R8.C. If not, do it now.
- **Belongs in audio-alert/hook config:** verify it's been wired into the audio alert system or relevant hook during R8.A. If not, do it now.
- **Deprecated:** confirm the relevant `debt.md` entry exists.
- **Keep in thin CLAUDE.md:** stage this content for E.2.

**Cross-cutting findings flagged by R0:** the extraction plan may have surfaced cross-cutting issues (e.g., the same Phase-tagged constraint repeated across 5+ files; a single concept duplicated between CLAUDE.md and prior-art agent prompts). E.1 reconciles these before E.2 — single source of truth per concept, with cross-references rather than duplicated content.

This is the retrofit step that BOOTSTRAP doesn't have. Pre-existing CLAUDE.md may be hundreds of lines of operationally-load-bearing content (workflow definitions, escalation rules, complexity tiers, attention cues). Slim-down without migration is content destruction.

### E.2 — Write the thin CLAUDE.md (same as BOOTSTRAP §8 with retrofit additions)

Write `CLAUDE.md` at repo root with:

- References to all created steering docs — both the BOOTSTRAP-standard set (`product`, `tech`, `deps`, `secrets`, `structure`, `principles`, `ci-cd`, `tools`, `spec-versioning`) AND any project-specific docs created in R5 step 3 (G5 — e.g., `phase.md`, `contracts.md`, `workflow.md`, `roles.md`).
- Reference to `specs/INDEX.md`, `learnings/`, and `sessions/`.
- **Retrofit-specific references:** `.claude/debt.md`, `.claude/inventory/`, `.claude/steering/spec-strategy.md`.
- The per-task workflow (gate count adapts to TDD policy).
- **Session hygiene reference:** `/checkpoint` before `/clear`, `/resume` to restore.
- The "Never" list pulled from `tech.md` "do not touch" + `secrets.md` never-read paths + universal rules.
- **Migrated content from E.1 classified as "Keep in thin CLAUDE.md."**
- **Explicit escalation criteria** — items marked **🔔** trigger the decision-required audio alarm:
  - **🔔** A "do not touch" file or never-read path needs modification or access.
  - Acceptance criteria are ambiguous after re-reading the spec.
  - Two reasonable approaches exist with materially different tradeoffs.
  - **🔔** A hook blocks the task and the fix isn't obvious within one attempt.
  - **🔔** A dependency needs to be added that isn't on the approved list in `deps.md`.
  - **🔔** A secret or credential is encountered in code or output.
  - **🔔** The implementation reveals the spec was wrong (triggers spec-versioning protocol).
  - The active spec version has changed since the task started.
  - The drift detector has fired Alert 3 (firm). **Tier 3 is enforced** (standard as of the BOOTSTRAP v1.9.0 this protocol targets): the agent writes `.claude/sessions/<timestamp>-checkpoint.md` with the standard synopsis schema, and is then hard-blocked from further tool calls until the operator runs `/clear`. The agent's responsibility is to produce a complete, useful checkpoint promptly; the operator's responsibility is to run `/clear` and `/resume`. `/ack-drift` does not dismiss tier 3.
  - **Retrofit-specific 🔔** Modifying a file in the legacy allowlist without first creating a spec via touch-based backfill.
  - **Retrofit-specific 🔔** *(v1.3)* Modifying a file in `inventory/danger-zones.md` without first generating a `legacy-pin-test` (or for AI/agent prompt files, a `prompt-pinning-eval`).
  - **Retrofit-specific (in-chat only)** A categorization in `tech.md` looks wrong in light of new evidence (the operator should review and possibly update R2 categorizations).

- When triggering the decision-required alarm, the agent writes to `.claude/sessions/.decision-pending-<session-id>` with: timestamp, escalation reason, what the agent was about to do, what input it needs.

Keep under **100 lines** — substantial retrofit content (extracted operational rules, complexity tiers, workflow definitions) goes in steering docs and skill files, not here. CLAUDE.md is the thin index, not the encyclopedia.

Show and ask: **approve / edit / start over**.

**Exit criteria:** `CLAUDE.md` exists, is thin (under 100 lines), pre-existing CLAUDE.md content has been migrated to appropriate locations, escalation criteria and audio markers are present, retrofit-specific references included.

---

## R8.F — CI/CD Steering (`ci-cd.md`)

**Goal:** Same as BOOTSTRAP Phase 5. **Conditionally required** — opt-out if no CI/CD.

**Retrofit adjustment:** scan for existing CI config files (`.github/workflows/`, `.gitlab-ci.yml`, `circle.yml`, `Jenkinsfile`, etc.) and propose them as the baseline. The operator confirms what already exists is canonical, then adjusts for any missing gates. R8.F is "ratify and document," not "design from scratch."

For projects with substantial existing CI investment (multiple workflows, environments configured, deployment pipelines running), `ci-cd.md` documents what exists. New gates from R5/R8.A may need to be added to existing pipelines — flag these as `debt.md` items for the operator to wire up.

**Exit criteria:** `ci-cd.md` exists. Agent-vs-human stopping point unambiguous. Existing CI workflows documented; missing gates flagged.

---

## R8.G — Autonomous Loop Mode (Optional, Opt-In, Scaffold-Only)

**Goal:** Generate the autonomous-loop scaffolding equivalent to BOOTSTRAP Phase 9.5, **default-disabled**, gated on the R8.G brownfield trust milestone. **Runs only if `autonomous_modes.loop_mode_opted_in` is true in `.retrofit-state.json`** (set at R0.5 step 7). If not opted in, skip this phase entirely and mark the Subagent Workflows equivalence row ✗ (operator-declined) — a valid non-failure.

**Why scaffold-but-defer (not enable):** see §"Autonomous Modes in Retrofit." A brownfield codebase's gates do not actually enforce until R8.A.6's graduated rollout has reached steady-state "block" and the legacy allowlist has shrunk; running an agent unattended against warn-only gates is the failure mode unattended execution amplifies. The deterministic-installer contract still wants the scaffolding produced once, now — so it is produced, but inert.

**AI actions:**

1. Generate, identically to BOOTSTRAP Phase 9.5's "what the wizard generates":
   - `.claude/loop.sh` — the per-task loop wrapper (race-safe claim protocol: `O_CREAT|O_EXCL` active sentinel, `flock` on the state file, sibling-sentinel cross-mode mutual-exclusion check; self-locates via `BASH_SOURCE`; honors the `.halt` sentinel). **Generated as a guarded fail-safe skeleton** exactly as BOOTSTRAP ships it — the `claude -p` iteration loop and the `loop_in_flight` state-list accounting are operator-completed per the trust ramp.
   - `.claude/loop-config.md` — the Phase 9.5 tunables.
   - The drift-detector loop-cooperation hook script (the same hook serves R8.G and R8.H; recognizes both `.loop-active-*` and `.goal-active-*` markers).
   - The loop-mode-aware `implementer` subagent variant body (tier-3 self-healing end-of-turn; decision-log protocol for non-urgent decisions; urgent-escalation `.loop-halt-<task-id>` write). The `reviewer` subagent is **not** modified — it remains part of the deterministic gate, exactly as BOOTSTRAP specifies.
   - The `spec-decompose` loop-eligibility classifier extension (the five-criterion test). **Retrofit adjustment:** the classifier additionally marks any task touching a file in the legacy allowlist or `inventory/danger-zones.md` as **not loop-eligible by default** until that file has a touch-based spec and (for danger zones) a pinning test — the ungated-habit risk plus an unpinned danger-zone file is not a combination an unattended loop should ever pick up. Operator can override per task with explicit acknowledgment.
   - The `.claude/sessions/` per-task loop state files convention (`.loop-active-<task-id>`, `.loop-complete-<task-id>`, `.loop-halt-<task-id>`, `decisions-log-<task-id>.md`, `loop-final-<task-id>.md`).
   - CLAUDE.md loop-mode conditional addendum (loads only on `.loop-active-<task-id>`).

2. **Set top-level `loop_mode_enabled: false`** in `.retrofit-state.json` regardless of operator eagerness. Write the R8.G brownfield milestone into the handoff (R7) as an explicit gate.

3. **Record the R8.G milestone** in `.retrofit-state.json.autonomous_modes.brownfield_milestones`. Loop mode may be enabled (by the operator, post-retrofit, manually flipping `loop_mode_enabled` and re-confirming) only when **all** of:
   - `rollout_steady_state_spec_test_gate: true` (R8.A.6 rollout reached blocking for spec gate AND test gate), and
   - `touch_based_specs_under_blocking_gates >= touch_based_specs_threshold` (default 10 — specs that shipped *after* the gates began blocking, not merely 10 tasks), and
   - `legacy_allowlist_current_size <= legacy_allowlist_size_at_retrofit * (1 - legacy_allowlist_shrink_threshold_pct/100)` (default: allowlist shrunk ≥25%).
   The wizard computes `legacy_allowlist_size_at_retrofit` now (from R4's `spec-strategy.md` allowlist) and writes it.

4. Show the operator the scaffolding and the milestone. Ask: **approve / edit / start over**. Make explicit: "This is generated but OFF. Do not enable until the milestone in R7's handoff is met. Enabling early runs the agent against gates that are not yet enforcing."

**Exit criteria:** Loop-mode scaffolding present and matches BOOTSTRAP Phase 9.5 shape. `loop_mode_enabled: false`. R8.G brownfield milestone recorded and `legacy_allowlist_size_at_retrofit` captured. Operator has seen the scaffold-but-defer posture and approved.

---

## R8.H — Goal-Supervised Mode (Optional, Opt-In, Scaffold-Only)

**Goal:** Generate the goal-supervised-mode scaffolding equivalent to BOOTSTRAP Phase 9.6, **default-disabled**, gated on the (stricter) R8.H brownfield milestone. **Runs only if `autonomous_modes.goal_supervised_mode_opted_in` is true.** Independent of R8.G — all four combinations (neither / loop / goal / both) are valid, same as BOOTSTRAP. If not opted in, skip and mark the equivalence row accordingly.

**AI actions:**

1. Generate, identically to BOOTSTRAP Phase 9.6's "what the wizard generates":
   - `.claude/goal-loop.sh` — guarded fail-safe skeleton (same race-safe claim protocol as `loop.sh`, parallel `goal_in_flight` accounting; `claude -p` loop operator-completed).
   - `.claude/goal-config.md` — Phase 9.6 tunables.
   - The iteration-summary enforcement hook script (checks `.iteration-summary-<task-id>-<iter-n>.md` presence and format-validity; three consecutive format failures = `goal-condition-suspect`-class halt). Runs the same R8.A.4 security & correctness checklist.
   - `learnings/mode-selection.md` — the calibration ledger. **Retrofit adjustment:** seed it with a header note that, for a brownfield project, the drift-prone-area column should be populated from `inventory/danger-zones.md` and `inventory/tribal-knowledge.md` rather than left empty — this codebase already *knows* its drift-prone areas, unlike greenfield.
   - The goal-supervised-mode-aware `implementer` subagent variant (shares R8.G's three behaviors plus iteration-summary discipline, evaluator-feedback reading, no self-verification shortcut). The two autonomous variants are mutually exclusive at runtime (a task is in exactly one mode's in-flight list). The `reviewer` is **not** modified.
   - The `spec-decompose` sixth-criterion classifier and recommendation rule. **Retrofit adjustment:** same legacy-allowlist/danger-zone exclusion as R8.G step 1 applies to goal-supervised eligibility too.
   - The `.claude/sessions/` per-task goal state files (`.goal-active-<task-id>`, `.iteration-summary-<task-id>-<iter-n>.md`, `.evaluator-feedback-<task-id>.md`; `decisions-log`/`loop-final` shared with R8.G).
   - CLAUDE.md goal-supervised conditional addendum.

2. **Set `goal_supervised_mode_enabled: false`.**

3. **Record the R8.H milestone:** all of R8.G's three conditions, **plus** `mode_selection_ledger_entries >= 10` (the calibration ledger has ≥10 real brownfield entries so the recommendation rule is calibrated against this codebase's actual drift-prone areas, not greenfield priors).

4. Show the operator the scaffolding and milestone. Ask: **approve / edit / start over**. Same scaffold-but-defer framing as R8.G.

**Exit criteria:** Goal-supervised scaffolding present and matches BOOTSTRAP Phase 9.6 shape. `goal_supervised_mode_enabled: false`. R8.H milestone recorded. Operator approved.

---

## R8.I — Autonomous Queue Mode (Optional, Opt-In, Scaffold-Only)

**Goal:** Generate the autonomous-queue scaffolding equivalent to BOOTSTRAP Phase 9.7, **default-disabled**, gated on the (strictest) R8.I brownfield milestone. **Runs only if `autonomous_modes.queue_mode_opted_in` is true AND at least one of `loop_mode_opted_in` / `goal_supervised_mode_opted_in` is true** — same hard gate as BOOTSTRAP 9.7. If queue was opted into without a per-task mode, the wizard refuses to scaffold it and surfaces the reason (queue dispatches per-task mechanisms; with none scaffolded there is nothing to dispatch), exactly as BOOTSTRAP Phase 0 step 6's refusal condition.

**AI actions:**

1. Generate, identically to BOOTSTRAP Phase 9.7's "what the wizard generates":
   - `.claude/auto.sh` — the runner (guarded fail-safe skeleton; contains **no agent context** — it dispatches the per-task wrappers and observes terminal states; the dispatch loop and `queue_runs_history` lifecycle are operator-completed).
   - `.claude/auto-config.md` — runner configuration (`max_concurrent_tasks` default 2, budgets, `consecutive_halt_threshold`, `pause_on_*`).
   - `.claude/queue/` directory with an empty `backlog.md` skeleton.
   - The `spec-decompose` queue-population step (priority, ready/operator-only/deferred section, `blocked_by` field). **Retrofit adjustment:** any task touching a legacy-allowlist or danger-zone file without a touch-based spec (+ pinning test for danger zones) is auto-placed in the **Operator-only** section (skipped by the runner, never auto-dispatched) until that precondition is cleared — the queue must not amplify the ungated-habit risk across tasks.
   - The `.claude/queue/.run-active` sentinel convention and the `exit_reason` enum handling.
   - The brief CLAUDE.md informational reference to queue mode as a coordination layer (no behavioral addendum — the runner does not load CLAUDE.md).

2. **Set `queue_mode_enabled: false`.**

3. **Record the R8.I milestone:** all of R8.G's three conditions, **plus** `rollout_steady_state_all_hooks: true` (R8.A.6 rollout reached blocking for *every* hook, not just spec+test), **plus** `weeks_real_per_task_operation_post_blocking >= 4` (≥4 weeks of real R8.G *or* R8.H operation *after* the gates began blocking), **plus** the standing BOOTSTRAP gate (R8.G or R8.H actually enabled — not merely scaffolded — at the time queue is enabled). Rationale, restated for the operator: queue mode multiplies every per-task failure by the task count; doing so while any gate is still in warn-mode, or before the per-task mechanism itself has a track record on *this* codebase under enforcing gates, is precisely the worst case the brownfield ungated-habit risk produces.

4. **Surface the trust ramp immediately** (mirrors BOOTSTRAP Phase 0 step 6's trust-ramp surfacing, brownfield-tightened): *"Autonomous queue mode is scaffolded but OFF. For a brownfield project it must not be enabled until: all hooks block (not warn), the legacy allowlist has shrunk past threshold, ≥10 touch-based specs shipped under blocking gates, and a per-task autonomous mode has run for ≥4 real weeks under those blocking gates. The R7 handoff records this as a hard gate. Do not run it overnight on week one. Do not run it at all until the milestone is green."*

5. Show the operator the scaffolding and milestone. Ask: **approve / edit / start over**.

**Exit criteria:** Queue scaffolding present and matches BOOTSTRAP Phase 9.7 shape (or correctly refused if no per-task mode opted in). `queue_mode_enabled: false`. R8.I strictest milestone recorded. Trust ramp surfaced. Operator approved.

---

## Protocol rules for the AI

- **Cite, don't assume.** When inferring product context, conventions, or stack details, cite the source files. Operator should be able to verify every inference.
- **Never silently overwrite an existing `.claude/`.** Always offer the archive path. **Always read the archive contents during R0** — non-protocol layouts (`roles/`, custom directories) are operator-invented prior art, not noise.
- **Treat the inventory as the source of truth for what exists.** If steering disagrees with inventory, the operator must reconcile explicitly.
- **Default to forward-only spec strategy.** Bulk backfill is out of scope; touch-based is fine if the operator wants it but adds workflow friction.
- **Do not fix technical debt during retrofit.** Capture it in `debt.md` and move on. The retrofit is for *infrastructure*, not *cleanup*.
- **Do not flatten multi-runtime variation.** R2 categorization is per-subsystem for projects with distinct runtimes. The output should be "subsystems are X/Y/Z; conventions A/B differ across them; convention C is shared" — not "the codebase has inconsistent conventions, here's the canonical one."
- **Honor portfolio defaults if available.** If a sibling project's `.claude/` exists and the operator confirmed portfolio mode in R0, reuse standardized conventions automatically. Don't make the operator re-decide things they decided once.
- **Flag historical secret leakage immediately and prominently.** This is the one retrofit finding that warrants stopping the protocol to address.
- **Be honest about the limits of inference.** If the AI doesn't have enough signal to reconstruct the implicit PRD or convention rules, say so and ask the operator. Bad inferences are worse than admitting uncertainty.
- **Be honest about degraded-mode limitations.** If R-1 selected degraded mode, the AI must annotate every phase output with what was lost (no git history, no historical secret scan, etc.) so the operator knows the inventory's coverage limits.
- **Always set `model:` explicitly on subagents.** Same reasoning as BOOTSTRAP — `inherit` silently uses the calling session's model, which is rarely what you want for review and audit subagents. The lone sanctioned exception is `integrator`, which deliberately mirrors BOOTSTRAP's `model: inherit` (mechanical merge/integration work where the calling session's model is acceptable); do not "correct" it, as that would diverge from BOOTSTRAP equivalence.
- **Never enable an autonomous mode at retrofit time.** *(v1.6.0)* R8.G/H/I scaffold but leave `*_enabled: false`. Even if the operator insists, explain the brownfield trust milestone and record opt-in intent only. Enabling unattended execution against gates that don't yet enforce (warn-mode hooks, un-shrunk legacy allowlist) is the failure mode the whole scaffold-but-defer posture exists to prevent. The milestone is satisfied post-retrofit, by the operator, deliberately — not by the wizard.
- **Use multi-choice tools where available.** If the environment provides interactive multi-choice prompts, use them for known options. Reserve free-form for things only the operator knows.

---

## Reference Material (Cheat Sheet, Glossary, Scope, Changelog)

**Moved to `RETROFIT-COMPANION.md`.** “What this protocol does not cover”, the Retrofit-Specific Cheat Sheet, the Glossary, and the full Changelog (v1.0–v1.6.0) are consulted, not executed. See `RETROFIT-COMPANION.md`.

# Project Retrofit Protocol — Companion Reference

**Companion to `RETROFIT.md` v1.6.2** (which is itself the brownfield counterpart of `BOOTSTRAP.md` v1.9.0). This file holds the reference material the retrofit wizard *consults* while running — it is not executed top-to-bottom. The executable protocol (phases R-1 through R8.I, Skip Policy, Equivalence Target, Project Archetypes, Protocol rules) lives in `RETROFIT.md`.

This companion was extracted in the v1.6.0 split, following the same companion-split principle as `BOOTSTRAP-COMPANION.md`’s extraction from `BOOTSTRAP.md` at BOOTSTRAP v1.7.0 — reference material the wizard consults moves out; execution-binding material stays in `RETROFIT.md`. The section inventory is not a strict mirror of BOOTSTRAP-COMPANION’s (it differs where RETROFIT has no counterpart, handles a topic inline, or has no equivalent machinery — see the note in RETROFIT.md’s "Mental Model, Model Assignment, and Reference Material" section). The extraction itself is mechanical: every section below is byte-identical to its prior location in `RETROFIT.md`; only this preamble is new. No protocol behavior changed in this split (the v1.6.0 phase additions predate it; see Changelog); v1.6.0 retrofits remain valid and need no re-run.

**Contents:** Mental Model · Model Assignment Strategy · Portfolio Awareness · What this protocol does not cover · Cheat Sheet · Glossary · Changelog.

---

## Mental Model

### What success looks like

**The success bar for retrofit is BOOTSTRAP equivalence on shared concerns, plus brownfield-specific artifacts that greenfield neither needs nor can produce.** A successfully retrofitted project's `.claude/` workspace should be **functionally indistinguishable** from what BOOTSTRAP would have produced for a greenfield project of the same archetype, **for the categories BOOTSTRAP covers**. Concretely, after a successful retrofit:

- The same six output categories must exist: **Steering docs, Specs, Hooks, Model Assignment, Audio Alerts, Subagent Workflows** (the latter implicitly including Skills and Commands).
- New code goes through the same spec-driven gates a BOOTSTRAP project would impose.
- Subagent definitions, hook configurations, and audio alert wiring match BOOTSTRAP's defaults.

The differences between a retrofitted project and a BOOTSTRAP'd-from-scratch one fall into two buckets — **transitional artifacts** (artifacts a brownfield retrofit produces that a greenfield bootstrap doesn't need) and **brownfield-discovery artifacts** (information that becomes determinable only because the project already exists and is operating):

**Transitional artifacts:**

1. **The product itself** — the existing code persists.
2. **`debt.md`** — known issues tracked but not fixed during retrofit.
3. **Legacy allowlist** — transitional file in `spec-strategy.md`; shrinks as files get touch-based specs.
4. **`.claude/inventory/`** — one-time historical audit of pre-retrofit state.
5. **PM-artifact transition decisions** *(v1.4)* — record of how existing tickets/epics relate to the new spec workflow.

**Brownfield-discovery artifacts (correctly RETROFIT-only):**

The retrofit's `compliance.md`, `contracts.md`, `migration.md`, baseline metrics in `inventory/`, hook rollout schedules, and tribal-knowledge captures are produced because brownfield projects can answer questions greenfield projects cannot yet answer:

- **`compliance.md`:** R0 step 10 detects regulatory frameworks from production realities — the system is processing data, has actual users, has an operating environment. Greenfield has not yet decided whether to accept EU users, whether to pursue SOC 2, whether to handle PHI. **Forcing greenfield to commit to regulatory posture at bootstrap time creates false-no answers** that are worse than absence; greenfield's correct path is to add `compliance.md` when regulatory obligations crystallize, not preemptively at project start.
- **`contracts.md`:** R4 detects integration points by reading existing code — the auth APIs, the consumed third-party services, the cross-component boundaries are facts on the ground. Greenfield knows planned integrations from PRD, but boundary specs are most useful when integrations actually solidify, which is post-bootstrap. BOOTSTRAP's `structure.md` covers the architecturally-known parts; running boundary specs for greenfield are a `spec-new`-time concern, not a bootstrap concern.
- **`migration.md`:** by definition only applies to in-flight modernization — there is no greenfield equivalent.
- **Baseline metrics (`inventory/baseline-metrics.md`):** brownfield has measurable lead time, change failure rate, test coverage, lint conformance, and DORA tier from existing git history and production deploys. Greenfield's values are all N/A or 0 — recording them establishes nothing actionable; the metrics become useful only after enough commits/deploys to compute trends.
- **Hook rollout discipline:** brownfield needs graduated warn→block because existing developers have ungated habits. Greenfield has no such habits to overcome — solo greenfield correctly skips the discipline; team greenfield can inherit it as a footnote in `principles.md` if useful.
- **Tribal knowledge interview:** the five questions (DO NOT TOUCH list, sleeping bugs, magic configs, war stories, 3am calls) all assume an existing system with prior maintainers. Greenfield has no such signals to capture.
- **Worktree resource budgeting:** brownfield knows its codebase size; greenfield doesn't yet. Greenfield's correct path is documenting the budget when the codebase actually crosses the size threshold, not preemptively.

**These asymmetries are architecturally justified, not BOOTSTRAP gaps.** Earlier versions of this protocol (v1.3, v1.4) framed them as "RETROFIT exceeds BOOTSTRAP coverage" with the implication that BOOTSTRAP should catch up. v1.5 corrected that framing: brownfield's information advantages are real but they're discovery advantages, not protocol advantages. **As of BOOTSTRAP v1.9.0** *(the version RETROFIT v1.6.0 targets)*, the **Post-bootstrap milestones** section lives in `BOOTSTRAP-COMPANION.md` (moved there by the v1.7.0 companion split) and documents the lifecycle triggers — first regulated user, first integration goes live, ~30 commits or first deploy, first additional contributor, codebase exceeds 1GB, first team handoff — that move greenfield projects into producing the same artifacts retrofit produces from day one. The asymmetries are correct *at bootstrap*, but resolve as the project matures past those thresholds. Greenfield operators consult `BOOTSTRAP-COMPANION.md`'s milestones section when triggers fire; retrofit operators inherit these artifacts at retrofit time because the triggers have already fired (the project already exists, has users, has an operating environment).

Plus any **INTENTIONAL VARIATION** tags in `tech.md` where the operator has explicitly accepted divergence from BOOTSTRAP's defaults. Variations are allowed but must be documented; silent divergence is a retrofit failure.

The BOOTSTRAP Equivalence Target section below enumerates the per-output checklist. R7 Handoff validates against it.

### How to get there

The retrofit follows the same artifact hierarchy as bootstrap:

```
PRD (docs/prd/<name>.md)              ← reconstructed from existing artifacts (or pointer to existing PRD)
  └── Steering docs (.claude/steering/)  ← describe what's there + what's canonical
        └── Specs (.claude/specs/<slug>/) ← only for new work; existing code is "legacy"
              └── Tasks (.claude/specs/<slug>/tasks/)
                    ├── decisions.md
                    └── changelog.md

Cross-cutting (retrofit-specific):
  .claude/inventory/        ← codebase audit results (R0)
  .claude/debt.md           ← known issues, won't-fix-now, tracked for later (R3)
  .claude/learnings/        ← cross-feature insights
  .claude/sessions/         ← checkpoints + audio-alert state files
  .claude/hooks/            ← gates, configured for retrofit (legacy allowlist)
  .claude.archived-<ts>/    ← archived prior `.claude/` (preserved during retrofit)
```

Three concepts unique to retrofit:

- **Inventory** = audit of what exists. Written once during retrofit, referenced by steering docs. Not maintained going forward (steering docs supersede it).
- **Debt registry** = explicit list of known issues we're not fixing now. Lives in `.claude/debt.md`. Updated as new debt is identified or items are resolved.
- **Categorization** = the R2 work of deciding, for each observed pattern, whether it's Canonical / Deprecated / Intentional Variation / **Modernize** (new in v1.1). This conversation is the highest-leverage step in the entire protocol.

The line that matters for retrofit: **"existing code" vs. "new code."** Existing code is **transitionally grandfathered** — held outside spec gates via the legacy allowlist while the retrofit completes and during R8.A.6's graduated hook rollout, then progressively gated as files are touched (and thus get specs via touch-based backfill, with pin-first discipline if they're danger-zone files). New code (anything modified or added after retrofit completes) goes through the full spec-driven workflow from day one. The legacy allowlist shrinks toward zero over the project's lifetime as files get touched and migrated.

### Brownfield SDD discipline

RETROFIT v1.3 introduces explicit brownfield-modernization discipline drawn from foundational practitioner literature. The protocol mentions these by name where applicable; the operator should recognize them.

- **Pin → Spec → Modify** *(Feathers' characterization tests / pinning tests)* — When new code modifies a legacy file, the safest sequence is: (1) write a *characterization test* that captures the file's current observable behavior, (2) write a *change spec* describing the intended delta, (3) make the modification verifiable against both. The pinning test isn't a correctness test; it documents what the system does today so unintended changes are caught. Used throughout R2, R4, R6.

- **Strangler Fig pattern** *(Fowler)* — Incremental displacement of legacy systems via a façade/proxy that routes traffic to either old or new behavior. Three properties: facade-first, incremental by design, value-continuous. The retrofit's `spec-strategy.md` choices implicitly select how strangler-fig-shaped the modernization is. Per-archetype patterns vary (proxy for Service/API, re-export for Library, prompt-version routing for AI/agent). See R4 and the per-archetype strangler patterns in §"Project Archetypes."

- **Three brownfield SDD spec patterns** *(Augment Code 2026, citing InfoQ + Thoughtworks)* — Brownfield SDD distinguishes three spec patterns: **Change specs** (delta of an intended modification — what RETROFIT v1.2 already produced via touch-based backfill), **Dependency boundary specs** (machine-readable contracts at integration points — OpenAPI, Protobuf, JSON Schema), **Migration specs** (multi-phase architectural change with target state, incremental steps, integration layer). Different scopes, different validity periods. R4 produces all three as relevant.

- **Code health awareness** *(Tornhill via Fowler)* — AI-assisted modification of unhealthy legacy code carries ~30% higher defect risk than equivalent modification of healthy code. The retrofit identifies "danger zone" files (high churn × high complexity × low test coverage) and applies stricter review discipline on changes to them. Captured in R0 inventory and enforced via R8.A reviewer behavior.

- **EARS notation** *(Mavin et al., IEEE RE'09)* — Requirements syntax with five patterns (Ubiquitous / Event-driven / State-driven / Optional / Unwanted behavior) plus Complex combinations. Used in modern SDD tools like Kiro for unambiguous, testable acceptance criteria. RETROFIT v1.3 recommends but doesn't mandate EARS for spec ACs.

- **SDD rigor levels** *(Böckeler/Fowler 2025)* — Three levels: **spec-first** (write spec, then implement; spec may be discarded), **spec-anchored** (spec persists for evolution and maintenance), **spec-as-source** (spec is the primary file; code is generated). RETROFIT implements **spec-anchored** SDD. Spec-as-source is out of scope (still-evolving industry experiment). Glossary records this for operator awareness.

### Failure modes to anticipate

Five common failure modes when applying SDD to brownfield code *(Augment Code 2026)*:

1. **Comprehensive specification is impractical at scale** — large codebases exceed review capacity. Mitigation: change specs scoped to the delta, not the whole system (R4).
2. **Tribal knowledge silos block specification authoring** — original architects departed. Mitigation: explicit tribal-knowledge interview in R0 (see G17 treatment in R0).
3. **Undocumented dependencies create specification blind spots** — accumulated over years. Mitigation: dependency boundary specs at integration points (R4 + R5).
4. **Implicit behavioral contracts resist formalization** — shared assumptions never written down. Mitigation: characterization tests pin them before they can be discussed.
5. **AI performance degrades in unhealthy code** — see code health awareness above.

These aren't unique-to-retrofit, but the retrofit explicitly addresses each.

### Fixed-position concepts

**Guidance vs enforcement** (from BOOTSTRAP, applies identically): CLAUDE.md is guidance, hooks are enforcement. For anything that *must* not happen (no commits to legacy without a spec, no reads of secret paths), use a hook. For style preferences, CLAUDE.md and steering are sufficient.

**Memory layers** (from BOOTSTRAP, applies identically): auto memory (Claude curates), CLAUDE.md (operator curates), `learnings/` (cross-feature insights). One additional retrofit consideration: existing projects may have prior memory artifacts (CLAUDE.md, ad-hoc notes, AGENT.md, agent prompts) that are *themselves* operator-curated memory — these need explicit migration in R8 rather than being treated as if they were newly written.

---

## Model Assignment Strategy

Same principles as `BOOTSTRAP-COMPANION.md` §"Model Assignment Strategy" (this section moved out of `BOOTSTRAP.md` in the v1.7.0 companion split), with retrofit-specific additions for skills that don't exist in greenfield work. Read the companion section for the full strategy framing, Pro vs Max tier handling, and `opusplan` shortcut. The table below assumes that context.

**The opinionated default for retrofit work — adopt unless you have reason not to:**

| Phase, skill, or subagent | Recommended model | Why |
|---|---|---|
| **The retrofit wizard itself** | Opus 4.7 (xhigh effort default) | Heavy judgment work — convention reckoning, prior-art categorization, debt classification, multi-runtime variation analysis. Single highest-stakes session in the protocol. Run with `claude --model opus`. |
| **`inventory-scan`** *(retrofit, R0)* | Sonnet 4.6 | Pattern work — file-tree walking, language detection, dependency parsing. Mechanical enough that Sonnet handles cleanly; Opus is overkill. |
| **`prior-art-audit`** *(retrofit, R0 step 1 + R8)* | Opus 4.7 | Reading existing `.claude/` agents, roles, CLAUDE.md sections, ad-hoc workflow documentation and judging "what is this trying to do, what should it become." Judgment-heavy. |
| **`convention-categorize`** *(retrofit, R2)* | Opus 4.7 | The single highest-leverage call in the protocol. Deciding Canonical / Deprecated / Intentional Variation / Modernize for each observed pattern. A bad call here ships flawed steering for the lifetime of the project. |
| **`debt-classify`** *(retrofit, R3)* | Sonnet 4.6 | Mechanical categorization against known templates (severity by impact, source citation). Operator-confirmed. |
| **`legacy-spec`** *(retrofit, used in R6 / R8 / touch-based backfill)* | Sonnet 4.6 | Generates a brief spec for a legacy module — pattern-based, against existing code as input. Sonnet is sufficient. |
| **`legacy-pin-test`** *(retrofit, v1.3, used in R2/R6/R8 before modifying legacy code)* | Sonnet 4.6 | Generates a characterization test that captures current observable behavior of a legacy module before modification. Pattern work — reads code, generates pinning tests. Per Feathers' technique. |
| **`boundary-spec`** *(retrofit, v1.3, used in R4/R5 for integration points)* | Sonnet 4.6 | Generates a dependency boundary spec (OpenAPI / Protobuf / JSON Schema) for a service contract or public API surface. Pattern work translating existing code into machine-readable contract. |
| **`prompt-pinning-eval`** *(retrofit, v1.3, AI/agent archetype only)* | Sonnet 4.6 | Generates a characterization eval (golden-dataset baseline) for a prompt before modification. The AI/agent equivalent of a pinning test. |
| **`dataset-pin-test`** *(retrofit, v1.3, Data/ML archetype only)* | Sonnet 4.6 | Generates reproducibility-validation tests for a data pipeline stage — dataset version, env, seed, output checksum. |
| **`ticket-to-spec`** *(retrofit, v1.4, conditional on R0.7 PM strategy)* | Sonnet 4.6 | Converts an existing ticket (Linear/Jira/GitHub Issues/in-repo `tickets/`) into a `requirements.md` spec stub with original-ticket frontmatter. Pattern work translating ticket format into spec format. |
| **`migration-plan`** *(retrofit, R5/R7 if operator wants concrete plans for Deprecated items)* | Opus 4.7 | Decomposing a deprecated pattern's removal into safe, reversible steps. Judgment work. |
| **`spec-new`, `spec-review`, `spec-decompose`, `plan-review`** | Opus 4.7 | Same as BOOTSTRAP. |
| **`reviewer` (subagent, invokes `code-review` skill)** | Opus 4.7 (effort: high) | Same as BOOTSTRAP. |
| **`implementer` (subagent)** | Sonnet 4.6 | Same as BOOTSTRAP. |
| **`test-author`, `spec-validate`, `pr-author`, `decision-log`, `checkpoint`, `resume`** | Sonnet 4.6 | Same as BOOTSTRAP. |
| **`ack-drift`, `quiet`, `quiet-task-done`** | Haiku 4.5 | Same as BOOTSTRAP — trivial state-file writes. |
| **Built-in `Explore`** | Haiku 4.5 (default) | Same as BOOTSTRAP. |
| **`integrator` (subagent)** | `inherit` | Same as BOOTSTRAP. |

**Always set `model:` explicitly.** Same reasoning as BOOTSTRAP — `inherit` silently uses the calling session's model, which is rarely what you want for review and audit subagents.

**Pro tier fallback (same as BOOTSTRAP):** if Opus access is metered/limited, treat the "Opus 4.7" rows as "best-available reasoning model" and fall back to Sonnet 4.6 (xhigh effort) for the high-stakes ones — `convention-categorize`, `prior-art-audit`, `code-review`. The strategy still works; it's just compressed across fewer tiers.

---

## Portfolio Awareness

If you're retrofitting one of several projects you maintain, certain conventions should be **standardized across your portfolio** so you can move between projects without re-orienting:

**Standardize across portfolio:**
- `.claude/sessions/` checkpoint format
- `decisions.md` and `changelog.md` schemas
- Hook script structure and exit-code conventions
- Slash command names (`/spec-new`, `/checkpoint`, `/resume`, `/ack-drift`, `/quiet`, `/quiet-task-done`)
- Subagent role names (`implementer`, `reviewer`, `integrator`)
- `INDEX.md` schema
- Audio alert system (BOOTSTRAP §6.E) — sound files, dispatch mechanism, quiet mode

**Keep project-local:**
- `principles.md` (project-specific rules)
- `tech.md` (stack and conventions)
- `structure.md` (directory layout)
- `deps.md` (per-project allowlist)
- `secrets.md` (per-project paths)
- `ci-cd.md` (per-project pipelines)
- `debt.md` (per-project debt)
- `inventory/` (per-project audit)
- Specs

**For the AI in R0:** if this is the operator's first retrofit, this project becomes the portfolio reference. Note that fact in the inventory and ask the operator at the end of R8 to confirm which conventions they want to lift to portfolio defaults for future retrofits. If a sibling project's `.claude/` is provided as a portfolio reference, read it during R0 and reuse its standardized conventions automatically; operator confirms or overrides per-item.

---

## What this protocol does not cover

- **Fixing the technical debt it identifies.** Out of scope by design. The registry is the deliverable, not the resolution.
- **Migration of very large existing codebases** (>2000 source files, multi-year history with lost institutional knowledge). The protocol assumes the operator can answer questions about the codebase. For larger projects, additional phases are needed (likely a multi-session interview phase before R0 to constrain scope, e.g., "retrofit the auth subsystem first").
- **Multi-team retrofit.** Same as BOOTSTRAP — single-operator. Team coordination on convention canonicalization is real and not addressed here.
- **Automated convention migration.** Marking a pattern as DEPRECATED in `tech.md` doesn't migrate the existing code. That's separate work.
- **Deprecation of `.claude/` itself.** If the operator decides retrofit was a mistake, no rollback protocol is provided beyond "delete `.claude/`, restore from `.claude.archived-*/` if desired, and revert the gitignore changes."
- **Network-isolated deep audits.** R-1 degraded mode handles "no git." Some scans (outdated-deps, supply-chain checks) genuinely require network. The protocol defers these explicitly with operator follow-up rather than pretending they ran.

---

## Cheat Sheet (Retrofit-Specific)

| Concept | What it means |
|---|---|
| **Equivalence target** *(v1.3)* | Six BOOTSTRAP outputs the retrofit must produce: Steering, Specs, Hooks, Model Assignment, Audio Alerts, Subagent Workflows. R7 validates against the checklist. |
| **Documented variation** *(v1.3)* | Operator-acknowledged divergence from BOOTSTRAP defaults, captured in `tech.md` with rationale + boundary. The escape valve from strict equivalence. |
| **Inventory** (`.claude/inventory/`) | Audit of what exists. Written once during retrofit, then frozen. |
| **Debt registry** (`.claude/debt.md`) | Known issues not fixed by retrofit. Updated continuously. |
| **Legacy allowlist** (`.claude/steering/spec-strategy.md`) | Files exempt from spec gating until they get specs. |
| **Retrofit-active allowlist** (`.claude/.retrofit-state.json`) | Permits `.claude/` writes during retrofit itself. Disabled at R7. |
| **Touch-based backfill** | Writing a spec for a legacy file the first time you modify it after retrofit. |
| **Pin-first discipline** *(v1.3, G6)* | When modifying a danger-zone or legacy-allowlist file: pin → spec → modify. The pinning test captures current behavior; the spec describes the intended delta. |
| **Characterization test / pinning test** *(v1.3)* | A test that documents what the system does today, not what it should do. Generated by `legacy-pin-test` skill. Per Feathers. |
| **Strangler fig pattern** *(v1.3, G7)* | Façade-first incremental displacement of legacy systems. Per-archetype variants in §"Project Archetypes." |
| **Three brownfield SDD spec patterns** *(v1.3, G8)* | Change specs (always) / Boundary specs (integration points) / Migration specs (in-flight modernization). |
| **Anti-corruption layer (ACL)** *(v1.3, G19)* | Translation layer preventing legacy concepts from leaking into new domain. Implicit in strangler-fig migrations. |
| **Danger zone** *(v1.3, G10)* | File with high churn × high complexity × low test coverage. Captured in `inventory/danger-zones.md`. Stricter reviewer rules apply. |
| **EARS notation** *(v1.3, G12)* | Requirements syntax with 5 patterns. Recommended (not mandated) for spec acceptance criteria. |
| **DORA baseline** *(v1.3, G9)* | Pre-retrofit measurements (lead time, change failure rate, test coverage, lint conformance, spec coverage starting at 0%). Captured in R0; reviewed at 30/60/90 days. |
| **Tribal knowledge** *(v1.3, G17)* | Knowledge that lives in operators' heads, not files. R0 step 9 interview captures it to `inventory/tribal-knowledge.md`. |
| **Regulatory regime** *(v1.3, G20)* | SOC 2 / HIPAA / PCI-DSS / IEC 62304 / GDPR / FedRAMP / FDA AI/ML PCCP. R0 step 10 detects applicable frameworks; R5 produces `compliance.md`. |
| **PM strategy** *(v1.4, G21)* | Source-of-truth decision in R0.7 — Strategy A (spec-canonical), B (PM-canonical), or C (hybrid). Drives R8.B MCP installation and R8.C `ticket-to-spec` skill. |
| **Ticket-to-spec migration** *(v1.4)* | Existing tickets converted to spec stubs via the `ticket-to-spec` skill (Sonnet). Open tickets with disposition convert-now/defer/close in R0.7 step 7. Migration is QUEUED in retrofit, EXECUTED post-retrofit. |
| **Workflow source-of-truth** *(v1.4)* | Steering doc at `.claude/steering/workflow-source-of-truth.md` recording R0.7 decision. |
| **Preview & Commitment** *(v1.4)* | R0.8 phase showing operator the full file manifest + scope estimates before R1+ runs. Mirrors BOOTSTRAP Phase 0.5. |
| **Canonical convention** | A pattern that stays. New code should follow it. |
| **Deprecated convention** | A pattern that exists but new code should avoid. Migration tracked in debt. |
| **Intentional variation** | Different rules for different contexts, by design (e.g., per-subsystem). Captured explicitly in `tech.md`. |
| **Modernized convention** *(v1.1)* | Prior-art convention that the operator chose to replace with a BOOTSTRAP-introduced standard. Captured in `tech.md`. |
| **Portfolio defaults** | Conventions reused from another `.claude/` directory you maintain. |
| **Calibrated stability cutoff** *(v1.1)* | `min(365 days, repo_age / 3)` — adapts the "files unchanged for X" stability proxy to the project's actual age. |
| **Source-file count** *(v1.1)* | `git ls-files \| grep -vE '^(docs/\|tickets/\|...)' \| wc -l` — the count that matters for scope, not raw tracked files. |
| **Degraded mode** *(v1.1)* | Retrofit running without `.git/`. Specific phases lose specific signals; documented per-phase. |
| **Archetype** *(v1.2)* | Project classification (CLI / Library / Service / Full-stack / Mobile / Data-ML / AI-agent / Platform / Other) decided in R0.5. Drives downstream behavior. |
| **PRD tier target** *(v1.2)* | Archetype-derived target (Micro / Standard / Full) that `product.md` should reach. Below-tier content gets a `debt.md` entry. |
| **Synthetic profile** *(v1.2)* | Structured archetype description for "Other" projects. Built from inventory dimensions; phases consult `closest_archetype` + deviations. |
| **Autonomous modes (scaffold-but-defer)** *(v1.6.0)* | R8.G (loop) / R8.H (goal-supervised) / R8.I (queue). Opt-in, default-skip. Scaffolded at retrofit but **default-disabled**; enablement gated on a brownfield trust milestone (gate-trustworthiness, not task count) that is strictly stricter than BOOTSTRAP's greenfield ramp. Never enabled by the wizard. |

| Workflow signal | What to do |
|---|---|
| First time touching a legacy file | Run `/spec-new` for the module (touch-based backfill) before editing |
| First time touching a danger-zone file | Pin → spec → modify: run `legacy-pin-test`, then `/spec-new`, then modify |
| Spec gate blocks work on legacy file | Check the allowlist; if file should be exempt, update `spec-strategy.md` |
| Test gate blocks legacy commit | If module is in no-test list, the grandfather clause should exempt it; if not, fix the hook |
| Lint gate fires on legacy code | First week is warning-mode (per R8.A.6 rollout schedule); after that, decide per-instance: fix now, log to debt, or exempt |
| Hook bypass rate over 10% | Investigate why; tune by understanding (per G14), don't tighten the hook |
| New convention being adopted | Update `tech.md`, log old convention to `debt.md` if widespread |
| Drift alert tier 1 (gentle chime) | Note it; finish current thought |
| Drift alert tier 2 (insistent chime) | Plan to checkpoint within 10 min |
| Drift alert tier 3 (firm chime, **enforced**) | Mandatory: agent writes `<timestamp>-checkpoint.md` (auto-blocked from other tool calls); operator runs `/clear` then `/resume`. `/ack-drift` does not dismiss tier 3. |
| Task-done chime | Subagent finished — review output when convenient |
| Decision-required alarm | Agent is blocked — respond now; check `.claude/sessions/.decision-pending-*` for details |
| Spec turns out to be wrong | Bump spec version (R8.D protocol) |
| Hook blocks me | Read the message; either fix the underlying issue or escalate per `CLAUDE.md` |
| Want to add a dependency | Confirm in-session; bootstrap updates `deps.md` |
| Need quiet for focus work | `/quiet 2h` mutes audio for 2 hours; visual notifications continue |
| Equivalence checklist has ✗ items | Return to relevant phase before R7 completes |
| 30/60/90-day baseline review | Re-measure metrics from `inventory/baseline-metrics.md`; track drift rate + spec coverage growth |
| New work item arrives in PM tool *(v1.4, Strategy A)* | Convert via `ticket-to-spec` then close ticket; operator does not implement directly from ticket |
| New work item arrives in PM tool *(v1.4, Strategy B)* | Auto-generate spec stub via `ticket-to-spec`; refine spec; implement; close ticket on completion |
| New work item arrives in PM tool *(v1.4, Strategy C, before cutover)* | Use existing PM-tool flow if in-flight area; create spec for new initiative |
| 90-day hybrid review *(v1.4, Strategy C)* | Re-evaluate: full migration to A, stay hybrid, or formalize as B with INTENTIONAL VARIATION |
| Autonomous mode scaffolded but you want to enable it *(v1.6.0)* | Check `.retrofit-state.json.autonomous_modes.brownfield_milestones`. Enable only when the per-mode milestone is fully green (R8.G: spec+test gates blocking, ≥10 touch-based specs under blocking gates, allowlist shrunk ≥25%; R8.H: + ≥10 mode-selection ledger entries; R8.I: + all hooks blocking + ≥4 weeks per-task operation). Then manually flip `*_enabled` and re-run equivalence validation. |
| Tempted to enable an autonomous mode early *(v1.6.0)* | Don't. The milestone is about gate trustworthiness on this codebase. Early enablement runs the agent against gates that don't yet enforce — the documented failure mode. |

| Task type | Recommended model |
|---|---|
| Retrofit wizard | Opus 4.7 |
| `inventory-scan`, `debt-classify`, `legacy-spec`, `legacy-pin-test`, `boundary-spec`, `prompt-pinning-eval`, `dataset-pin-test` | Sonnet 4.6 |
| `prior-art-audit`, `convention-categorize`, `migration-plan` | Opus 4.7 |
| `/spec-new`, `/spec-review`, `/spec-decompose`, `/plan-review`, `reviewer` subagent | Opus 4.7 |
| `implementer`, `test-author`, `/spec-validate`, `/pr-author`, `/checkpoint`, `/resume` | Sonnet 4.6 |
| Built-in `Explore`, `/ack-drift`, `/quiet`, `/quiet-task-done` | Haiku 4.5 |
| `integrator` subagent | Inherit |
| Don't want to configure each? | `claude --model opusplan` |

*Pro tier with limited Opus access:* fall back to Sonnet 4.6 for the Opus rows.

---

## Glossary (additions to BOOTSTRAP glossary)

**v1.6.0 additions:**

- **Autonomous modes (retrofit)** — R8.G (autonomous loop, ≈ BOOTSTRAP 9.5), R8.H (goal-supervised, ≈ 9.6), R8.I (autonomous queue, ≈ 9.7). Opt-in, default-skip. Retrofit scaffolds them but leaves them default-disabled.
- **Scaffold-but-defer** — the retrofit posture for autonomous modes: generate all scaffolding once (preserving the deterministic-installer contract) but set `*_enabled: false` and gate enablement on a post-retrofit brownfield milestone. The wizard never enables a mode at retrofit time.
- **Brownfield trust milestone** — the gate that must be green before an autonomous mode may be enabled on a retrofitted project. Unlike BOOTSTRAP's greenfield ramp (task-count-based), the brownfield milestone is **gate-trustworthiness-based**: R8.A.6 rollout reached blocking, ≥N touch-based specs shipped *under blocking gates*, legacy allowlist shrunk past threshold (plus, per mode, calibrated mode-selection ledger / all-hooks-blocking / weeks-of-operation). Strictly stricter than greenfield's, because pre-existing ungated developer habits mean the gates do not enforce until the rollout lands. Recorded in `.retrofit-state.json.autonomous_modes.brownfield_milestones`.
- **Ungated-habit risk** — the brownfield-specific risk (already the rationale for R8.A.6's graduated rollout) that pre-existing developers commit without passing the new gates, so the gates cannot be trusted to enforce until the warn→block schedule completes and the legacy allowlist shrinks. The reason autonomous modes are deferred behind the trust milestone rather than enabled at retrofit.

**v1.4 additions:**

- **PM artifact reckoning** — R0.7 phase deciding the source-of-truth path between specs and existing PM tooling. Three strategies: A (spec-canonical), B (PM-canonical with spec bridge), C (hybrid with cutover schedule).
- **Source-of-truth strategy** — operator-chosen path for new work intent post-retrofit. Recorded in `.claude/steering/workflow-source-of-truth.md`.
- **PM tool** — Linear, Jira, GitHub Issues, in-repo `tickets/` directories, or any equivalent project-management system holding work intent.
- **Ticket-to-spec migration** — converting an existing ticket into a `requirements.md` spec stub via the `ticket-to-spec` skill (Sonnet). Used in Strategies A and C for open tickets the operator wants to bring into the spec workflow.
- **Convert-now / defer / close (ticket disposition)** — per-ticket categorization in R0.7 step 7. Convert-now tickets get specs; defer goes to debt; close gets archived.
- **PM tooling indicator scan** — R0 step 12 detection of in-repo ticket directories, CI integrations with Linear/Jira, commit-message ticket references, etc. Output: `inventory/pm-tooling-signals.md`.
- **Preview & Commitment** — R0.8 phase showing the operator the full file manifest + token-budget estimate + remaining-time estimate before R1+ runs. Mirrors BOOTSTRAP Phase 0.5.
- **Hybrid cutover review** — Strategy C's 90-day checkpoint where the operator decides whether to fully migrate to Strategy A, stay hybrid, or formalize as Strategy B.

**v1.3 additions:**

- **Equivalence target** — Six BOOTSTRAP outputs (Steering / Specs / Hooks / Model Assignment / Audio Alerts / Subagent Workflows) the retrofit must produce. The success bar; R7 validates against it.
- **Documented variation** — Operator-acknowledged divergence from BOOTSTRAP defaults, captured in `tech.md`'s Intentional Variations section with rationale + boundary. Allowed by v1.3; required to be explicit.
- **Equivalence validation** — R7's checklist comparing retrofit output to BOOTSTRAP defaults. Each of 24 items in 6 categories is ✓, ✓\*, or ✗. Output: `.claude/inventory/equivalence-validation.md`. Rerunnable to detect drift.
- **Pin-first discipline** — Pin → Spec → Modify sequence for danger-zone or legacy-allowlist files. Per Feathers' characterization tests.
- **Characterization test (pinning test)** — A test capturing current observable behavior of a code unit, not asserting correctness. Run before modifying legacy code; captures changes the modification didn't intend. Generated by `legacy-pin-test` skill.
- **Strangler fig pattern** — Fowler's incremental-displacement pattern. Façade/proxy intercepts requests, routes to new system gradually until legacy can be retired. Per-archetype variants in §"Project Archetypes."
- **Three brownfield SDD spec patterns** — Per Augment Code 2026: (1) Change specs (delta of an intended modification), (2) Dependency boundary specs (machine-readable contracts at integration points), (3) Migration specs (multi-phase architectural change). Different scopes, different validity periods.
- **Change spec** — Spec covering the delta of a single modification. RETROFIT v1.2's touch-based backfill produces these.
- **Boundary spec** — Machine-readable contract at an integration point. OpenAPI for REST, JSON Schema for data, Avro/Protobuf for events. Generated by `boundary-spec` skill.
- **Migration spec** — Multi-phase architectural change spec with target state + incremental steps + integration-layer design. Each step independently deployable.
- **Anti-corruption layer (ACL)** — Translation layer preventing legacy concepts from leaking into new domain model. Per Evans (DDD) and Fowler. Implicit in strangler-fig migrations.
- **Danger zone** — File scoring high on churn × complexity × no-coverage. Captured in `inventory/danger-zones.md`. Stricter R8.A reviewer rules apply.
- **EARS notation** — Easy Approach to Requirements Syntax. Five patterns (Ubiquitous / Event-driven / State-driven / Optional / Unwanted behavior). Recommended for spec acceptance criteria. Per Mavin et al., IEEE RE'09.
- **SDD rigor levels** — Spec-first / Spec-anchored / Spec-as-source. RETROFIT implements spec-anchored. Per Böckeler/Fowler 2025.
- **Tribal knowledge** — Knowledge held by people, not files. Captured via R0 step 9 interview to `inventory/tribal-knowledge.md`.
- **Narrative test** — A test whose name carries a story (`test_no_database_migrations_during_business_hours_after_the_great_crash_of_2024`). Encodes tribal knowledge. Per Jackson Bennett.
- **DORA baseline** — Pre-retrofit measurements of lead time for changes, change failure rate, test coverage, lint conformance, spec coverage. Captured in `inventory/baseline-metrics.md`. Reviewed at 30/60/90 days.
- **DORA performance tier** — Elite / High / Medium / Low classification per 2024 DORA report. Captured at retrofit start; goal is to maintain or improve.
- **Drift rate** — Schema validation failures per sprint, contract test failures, spec revision frequency. The natural state that must be continuously governed (per InfoQ via Augment Code 2026).
- **Specification coverage growth** — Specs added per sprint. The brownfield SDD success metric.
- **Hook rollout discipline** — Graduated warn → block schedule for new hooks. Default 4-week schedule; bypass rate > 10% indicates trouble.
- **Production-traffic bootstrap** — Capturing sampled production traffic as input to boundary spec authoring (rather than guessing from code). Per GitHub SAML hardening case study.
- **Worktree resource budgeting** — Documentation of expected disk usage for parallel worktrees. ~5x codebase size. For codebases over 1GB, sequential may be preferable to parallel.
- **Regulatory regime** — Applicable compliance framework: SOC 2 / HIPAA / PCI-DSS / IEC 62304 + ISO 13485 / GDPR / FedRAMP / FDA AI/ML PCCP. Detected in R0 step 10. Drives `compliance.md` steering doc.
- **Audit-trail continuity** — Requirement that retrofit not destroy historical audit evidence. Archiving prior `.claude/` to `.claude.archived-*/` is consistent; deletion is not.
- **POA&M, DHF, SSP, PCCP, BAA, SOUP, Trust Service Criteria, QSA, 3PAO, Notified Body** — Regulatory artifacts/concepts referenced in `compliance.md`. Per-framework glossary in research-addendum.md.

**v1.0–v1.2 additions (carried forward):**

- **Inventory** — Audit of what exists in the codebase at retrofit time. Lives in `.claude/inventory/`. Written once, not maintained.
- **Debt registry** — `.claude/debt.md`. Known issues not fixed during retrofit. Updated as new debt is identified or resolved.
- **Legacy allowlist** — List of paths exempt from spec gating during forward-only or touch-based retrofit. Shrinks as files get touch-based specs.
- **Retrofit-active allowlist** *(v1.1)* — Permits writes under `.claude/` while the retrofit itself is in progress. Disabled at R7 handoff. Stored in `.claude/.retrofit-state.json`.
- **Touch-based backfill** — Strategy where existing files get specs the first time they're modified after retrofit, rather than all upfront.
- **Forward-only** — Strategy where existing files never get specs; only new features and modules do. Simplest retrofit path.
- **Canonical convention** — A pattern in `tech.md` that stays; new code follows it.
- **Deprecated convention** — A pattern in `tech.md` that exists in legacy code but new code should avoid. Tracked in `debt.md`.
- **Intentional variation** — Different conventions for different parts of the system, by design (not inconsistency). Often per-subsystem in multi-runtime projects.
- **Modernized convention** *(v1.1)* — Prior-art convention that the operator explicitly chose to replace with a BOOTSTRAP-introduced standard during R2 categorization. Recorded in `tech.md` with the prior pattern, the new pattern, and migration path.
- **Portfolio defaults** — Standardized conventions reused across multiple projects' `.claude/` directories.
- **Source-file count** *(v1.1)* — File count after excluding docs, tickets, generated code, vendored deps. The metric used for "small-to-medium" scope determination, not raw `git ls-files`.
- **Calibrated stability cutoff** *(v1.1)* — `min(365 days, repo_age / 3)`. The cutoff used by R0's "files unchanged for X" stability proxy. Adapts to repo age so young repos get a meaningful signal.
- **Degraded mode** *(v1.1)* — Retrofit running without `.git/` or other prerequisites. R-1 documents what's lost per-phase. Operator opts in explicitly; protocol does not silently degrade.
- **Audio alert system** — Three-category alarm system covering drift detection, task completion (`SubagentStop`), and decision required (urgent escalations). Configured in R8.A. For retrofit, prior-art audio conventions go through R2 categorization (Canonical / Modernize / Replace) before installation.
- **Archetype** *(v1.2)* — Project classification (CLI / Library / Service / Full-stack / Mobile / Data-ML / AI-agent / Platform / Other). Same vocabulary as BOOTSTRAP, classified from inventory artifacts in R0.5. Drives downstream behavior in R1, R2, R5, R5.5, R8.A. Recorded in `.retrofit-state.json`.
- **Synthetic profile** *(v1.2)* — Structured object built when an "Other" archetype is chosen, capturing the project's dimensions (user-facing surface, deploy targets, language runtimes, deployable units, presence of inference/storage/auth/secrets, closest-match archetype, deviations). Stored in `.retrofit-state.json` as `synthetic_profile`. Phases consult `closest_archetype` + deviations to decide question sets.
- **Archetype confidence** *(v1.2)* — HIGH / MEDIUM / LOW indicator on R0.5's archetype proposal, recorded in `.retrofit-state.json`. HIGH-confidence proposals override-d by the operator are surfaced for discussion in R2 (the discrepancy is signal worth attending to).
- **PRD tier target** *(v1.2)* — Archetype-derived target tier (Micro / Standard / Full) that R1's `product.md` should reach. If existing PRD content is below tier, R1 records the gap as a `debt.md` entry; protocol does not silently produce below-tier `product.md`.

---

## Changelog

### v1.6.2 (this revision)

**Adversarial-review fix pass (multi-lens round 4) — the two B2 sub-findings deferred from round 3, resolved against fully-fetched BOOTSTRAP.md Phase 7.5 + BOOTSTRAP-COMPANION.md Contents. No new protocol surface; corrective/clarifying only; v1.6.0/v1.6.1 retrofits remain valid.**

BOOTSTRAP source re-verified this round: `BOOTSTRAP.md` retrieved through mid-Phase-8 (Phase 7.5 body — all nine AI actions — fully within the retrieved prefix, well before the fixed truncation); `BOOTSTRAP-COMPANION.md` retrieved in full (complete Contents + every claimed section). FETCH MODE FULL-FOR-B2; both sub-findings were genuine cross-document verification, not internal-coherence-only. BOOTSTRAP.md Phases 9–10 + closing rules remained behind the fixed truncation as in rounds 2–3 (B4 still carried forward unrun, not inferred). No §3 carried-forward-closed item was contradicted by the fetch — no settled-item-reopened.

**Fixes applied (both execution-binding / execution-binding-adjacent, operator-signed-off):**

- **B2.1 [MED, INTERNAL not drift] — R8.D "Run BOOTSTRAP §7.5 as-is" breaks the self-containment contract.** Resolved via **option (b), explicit carve-out** (round 3's tentative lean was option (a) embed; re-derived from the now-visible Phase 7.5 body, which is substantive — nine AI actions — with zero retrofit flavor, making a verbatim embed a standing copy-drift liability of exactly the class that produced this project's defects across four rounds). Three RETROFIT.md edits: the "For the AI" blockquote and the R8 intro each gain a one-clause carve-out naming R8.D as the single deliberate by-reference exception with rationale; R8.D's body is rewritten to make the by-reference explicit and self-aware (points the executor at BOOTSTRAP.md's nine AI actions, states why it is not re-embedded, adds the retrofit note about touch-based-backfilled legacy specs and versioned steering docs like `phase.md`). The R8.A.4 "see BOOTSTRAP §6.D" pointer was investigated as a possible second instance and **dismissed [LOW, not fixed this round]** — it is followed by a complete, faithful inline enumeration of all sixteen §6.D checklist items, so a wizard can execute it from RETROFIT alone; reported separately per review discipline, explicitly not folded into the B2.1 fix.
- **B2.2 [MED] — "This split mirrors BOOTSTRAP v1.7.0's split and is mechanical" is overstated.** The "mechanical / byte-identical / no behavior changed" half is verified true and preserved verbatim; only the "mirrors the split [inventory]" half was the overstatement. Softened against the *actual* fetched BOOTSTRAP-COMPANION Contents: RETROFIT-COMPANION adds two sections BOOTSTRAP-COMPANION has no counterpart for (Portfolio Awareness; and a Changelog — confirmed this round that BOOTSTRAP companion-izes no changelog in the visible surface, resolving round 2's unverifiable point), and lacks four (standalone Post-bootstrap-milestones, Migration-notes, Phase-numbering-rationale, Ecosystem & complementary tooling). The Post-bootstrap-milestones absence is framed as a justified architectural asymmetry (correct-by-construction, not a gap) so the softened text does not reopen that round-3-dismissed item as drift. RETROFIT.md line 36 carries the full enumeration; the RETROFIT-COMPANION.md preamble is edited for consistency and points to the RETROFIT.md note rather than re-listing (single source of the enumeration, so the two cannot drift against each other).

**Net change v1.6.1 → v1.6.2:** five prose edits across two files (three in RETROFIT.md for B2.1: "For the AI" blockquote, R8 intro, R8.D body; one in RETROFIT.md for B2.2: the §"Mental Model, Model Assignment, and Reference Material" split claim; one in RETROFIT-COMPANION.md for B2.2: the preamble extraction claim) plus both headers and this changelog entry. No new phases, no new outputs, no state-schema change, no behavioral change to any R-phase — the edits correct an internal self-containment over-claim and soften an overstated parity claim. **Backward compatibility: clarifying.** v1.6.0/v1.6.1 retrofits remain valid and need no re-run; no `.retrofit-state.json` change. Patch bump per the additive/corrective-only discipline maintained since v1.1.

### v1.6.1

**Adversarial-review fix pass (multi-lens round 3) — BOOTSTRAP-drift corrections + one settled state-schema decision. No new protocol surface; additive/corrective only; v1.6.0 retrofits remain valid.**

BOOTSTRAP source fully re-verified this round: `BOOTSTRAP-COMPANION.md` retrieved in full (round 2's largest blind spot), `lib/defaults.py` retrieved for the state-schema decision. `BOOTSTRAP.md` Phases 9–10 + closing rules remained behind a fixed fetch truncation; the deep 9.5/9.6/9.7/10 body line-checks are carried forward, but the full Companion Glossary corroborated mode *shape* and surfaced no Critical/High risk there.

**Drift fixes applied (all source-verified against fetched BOOTSTRAP.md / BOOTSTRAP-COMPANION.md / `lib/defaults.py`):**

- **A1 [HIGH] — R8.C gitignore.** Added `.claude/.bootstrap-state.json.pre-1.7/.8/.9` (state-migration backups) and `.claude/queue/.resume` (operator runtime sentinel) to match BOOTSTRAP.md Phase 7 step 7 verbatim. RETROFIT-specific entries (`.retrofit-state.json`, `.scan-cache-*`, `.archived-*/`) confirmed justified brownfield-flavor, retained.
- **A2 [HIGH] — hook re-tiering.** **Test gate** and **dependency gate** restored to the "Always recommended" tier in both Equivalence Target §3 and R8.A.3, mirroring BOOTSTRAP.md Phase 6 step 2's `(all)` set (independently corroborated by `lib/defaults.py` `BASE_HOOKS`). The no-test-framework path is recast as an explicit ✓\* INTENTIONAL VARIATION (runtime grandfather clause), not a silent demotion. CI mirror and TDD gate left conditional — both are BOOTSTRAP-faithful-conditional (`(all *with CI*)` / TDD-policy-gated), not re-tiers.
- **A3 [MED] — audit-record commit boundary.** `decisions-log-*.md` and `loop-final-*.md` removed from the gitignore fence and added to the post-fence "committed normally" sentence (with `.claude/queue/backlog.md` / `run-summary-*.md`), restoring BOOTSTRAP.md Phase 7 step 7's commit-as-audit rule.
- **A4 [MED] — Equivalence Target phase attribution.** §1 Steering header corrected to "Phases 1, 2, 2.5, 2.7, 3, 4, 5, 6.5"; §2 Specs header corrected to "Phase 7 + 7.5 + 7.6" (was mis-anchored to "Phases 1, 2, 4" and "Phase 3").
- **A5 [LOW] — inert drift.** Deleted the `.claude/sessions/.plan-revisions-*` gitignore line; BOOTSTRAP.md Phase 6 §6.D declares the plan-revisions signal infeasible/out-of-scope and never produces the file. (`.bypass-count-*`, the real G14 sentinel, retained.)
- **A8 [COSMETIC, INTERNAL] — stale version strings.** The two disagreeing "out of scope for v1.3 / v1.4" >2000-source-file strings (scope table + R-1 step 4) unified to "out of scope for this protocol version."

**State-schema decision (B5 — execution-binding, operator-signed-off, option (a) true shape-equivalence):** the three autonomous-mode `*_enabled` flags and the three per-mode tracking lists (`loop_in_flight`, `goal_in_flight`, `queue_runs_history`) are now **top-level** in `.retrofit-state.json`, exactly matching BOOTSTRAP's `.bootstrap-state.json` (BOOTSTRAP "Recovery & State" + Phase 0 step 9 + BOOTSTRAP-COMPANION "Migration notes"). Only the RETROFIT-novel `*_opted_in` intent flags and `brownfield_milestones` remain nested under `autonomous_modes`. The installer's `bootstrap.config.yaml` *input* schema nests the enable flags (per `lib/defaults.py`); that is the config-input layer, distinct from the runtime state file, and does not govern this shape. Prose references reconciled throughout (R8.G step 2, §"Autonomous Modes in Retrofit", Validating Equivalence) so dotted-path vs bare-name usage is consistent: `*_enabled` bare/top-level, `autonomous_modes.*_opted_in` and `autonomous_modes.brownfield_milestones` nested.

**Still open after this revision (deferred to round 4):** B2.1 [MED] (R8.D "Run BOOTSTRAP §7.5 as-is" breaks the self-containment promise) and B2.2 [MED] (the "mirrors BOOTSTRAP's split, mechanical" parity claim is overstated against the now-visible BOOTSTRAP-COMPANION Contents). Both had proposed minimal fixes in the round-3 review record. **Resolved in v1.6.2** (see the v1.6.2 entry above): B2.1 via explicit carve-out (option b), B2.2 via inventory-precise softening.

**Net change v1.6.0 → v1.6.1:** corrective edits across the gitignore block, Equivalence Target §1–§3, R8.A.3 hook tiers, R0.5 step 8 state schema, and ~5 prose sites; one new top-level state-schema rationale paragraph; no new phases, no new outputs, no behavioral change to any R-phase. **Backward compatibility: corrective.** v1.6.0 retrofits remain valid; a v1.6.0 project regenerating `.retrofit-state.json` should move the three `*_enabled` flags and the three in-flight lists to top-level (a one-time, non-destructive edit — same shape BOOTSTRAP's own Migration notes specify). Patch bump per the additive/corrective-only discipline maintained since v1.1.

### v1.6.0

**Catch-up to BOOTSTRAP v1.7.0 + v1.8.0 + v1.9.0, and the first RETROFIT revision to add new phases since v1.4.** The companion target moves from BOOTSTRAP v1.6.1 to v1.9.0 — three minor versions, the most consequential being the autonomous-mode family (BOOTSTRAP Phases 9.5/9.6/9.7) and the `BOOTSTRAP-COMPANION.md` split (v1.7.0).

**New phases — R8.G / R8.H / R8.I (autonomous modes):**

- **R8.G — Autonomous Loop Mode** (opt-in, default-skip). Retrofit equivalent of BOOTSTRAP Phase 9.5. Generates loop scaffolding (`loop.sh`, `loop-config.md`, drift-cooperation hook, loop-aware `implementer` variant, `spec-decompose` loop-eligibility classifier, session state files, CLAUDE.md addendum) **default-disabled**, gated on the R8.G brownfield trust milestone.
- **R8.H — Goal-Supervised Mode** (opt-in, default-skip, independent of R8.G). Retrofit equivalent of BOOTSTRAP Phase 9.6. Generates goal-supervised scaffolding default-disabled, gated on the stricter R8.H milestone (R8.G's conditions plus a calibrated mode-selection ledger).
- **R8.I — Autonomous Queue Mode** (opt-in, default-skip, requires R8.G or R8.H — same gate as BOOTSTRAP 9.7). Generates queue scaffolding default-disabled, gated on the strictest R8.I milestone (all hooks blocking + ≥4 weeks per-task operation under blocking gates).

**The defining design decision — scaffold-but-defer with brownfield-tightened trust milestones:** new top-level §"Autonomous Modes in Retrofit" establishes why a retrofitted brownfield project must *not* enable these at retrofit time even when opted in. RETROFIT already commits (via R8.A.6's graduated hook rollout, G14) to the principle that pre-existing developers have ungated commit habits and the gates do not actually enforce until the warn→block schedule lands and the legacy allowlist shrinks. Running unattended execution against non-enforcing gates is precisely the failure mode unattended execution amplifies. Copying BOOTSTRAP's greenfield trust ramp verbatim would contradict RETROFIT's own established reasoning, so the brownfield ramp is **strictly stricter** and gated on gate-trustworthiness milestones (rollout steady-state, touch-based specs shipped *under blocking gates*, legacy-allowlist shrink %), not task counts alone. The deterministic-installer contract is preserved by generating all scaffolding once, now — but inert.

**Other amendments:**

- **Header** — version 1.5.1 → 1.6.0; companion reference BOOTSTRAP v1.6.1 → v1.9.0; new "Companion reference" note documenting the v1.7.0 `BOOTSTRAP-COMPANION.md` split (Mental Model, Model Assignment Strategy, Post-bootstrap milestones, Cheat Sheet, Glossary, Migration notes now live in the companion file).
- **AI/operator intro notes** — updated to reference R8.G/H/I and the scaffold-but-defer posture.
- **BOOTSTRAP Equivalence Target** — Subagent Workflows category gains an autonomous-mode-scaffolding row (✓ when present-and-default-disabled-with-milestone-recorded; ✗-operator-declined is a valid non-failure).
- **Skip Policy** — new "Opt-in, default-skip" tier for R8.G/H/I with the R8.I-requires-R8.G-or-R8.H gate.
- **R0.5 step 7** — surfaces the three autonomous-mode opt-ins with verbatim brownfield framing; **step 8 state schema** extended with `autonomous_modes` (opt-in flags, enabled flags pinned false, `brownfield_milestones` object). `bootstrap_protocol_version` recorded as `"1.9.0"`.
- **R8 intro** — phase list extended to 9.5/9.6/9.7 equivalents; ordering note updated to R8.A–R8.I.
- **R7 Handoff** — new step 7 communicating the per-mode brownfield milestone as a re-evaluable checklist and the "wizard will not enable this for you" rule; subsequent steps renumbered (8–11); exit criteria updated.
- **Protocol rules for the AI** — new rule: "Never enable an autonomous mode at retrofit time."
- **Version-pointer reconciliation** — active-body references to "BOOTSTRAP v1.6.0/v1.6.1" for tier-3 drift enforcement and quiet-mode override updated to "standard as of the BOOTSTRAP v1.9.0 this protocol targets" (these behaviors are no longer version-noteworthy; they're baseline). Model Assignment Strategy cross-references repointed to `BOOTSTRAP-COMPANION.md`. Historical changelog entries (v1.5.1 and earlier) left intact as an accurate record.

**Net change v1.5.1 → v1.6.0:** ~210 lines added (≈1888 → ≈2095): one new top-level section (~45 lines), three new phases (~110 lines), state-schema extension (~25 lines), equivalence/skip/handoff/rules updates (~30 lines). **Backward compatibility: additive.** v1.5.x retrofits remain valid — the autonomous modes are opt-in and default-disabled, and nothing in the existing six-category equivalence target changed shape; this extends it. Operators upgrading from v1.5.x need take no action unless they want autonomous modes, in which case they run R8.G/H/I retroactively (scaffold-only; the brownfield milestone then governs enablement). Per the additive-only discipline this protocol has maintained since v1.1, this is a minor bump.

### v1.5.1

**Catch-up to BOOTSTRAP v1.6.0 + v1.6.1.** No new RETROFIT phases; updates only where RETROFIT inherits or mirrors BOOTSTRAP behavior.

**v1.6.0 catch-up (BOOTSTRAP added the Post-bootstrap milestones section):**
- Mental Model "These asymmetries are architecturally justified" paragraph updated to reference BOOTSTRAP v1.6.0's Post-bootstrap milestones section directly. Earlier framing said "operator self-direction post-bootstrap"; now BOOTSTRAP itself documents the lifecycle triggers (first regulated user, first integration goes live, ~30 commits or first deploy, first additional contributor, codebase exceeds 1GB, first team handoff). The asymmetry-resolution narrative is now: greenfield doesn't produce these at bootstrap; greenfield consults BOOTSTRAP's milestones section when triggers fire; retrofit operators inherit them at retrofit time because the triggers have already fired by then.
- Companion-version reference in the header updated from "BOOTSTRAP.md v1.5.1" *(stale — that version was never shipped because the v1.5.1 patch brief got folded into v1.6.0)* to "BOOTSTRAP.md v1.6.1" *(current canonical)*.

**v1.6.1 catch-up (BOOTSTRAP promoted drift detector tier 3 from advisory to enforced):**
- **R8.A.5 audio alert table** — Drift detector row now reads "Soft for tiers 1–2 (advisory); hard for tier 3 (operator is blocked)" with "Required for tiers 1–2 (action button or `/ack-drift`); tier 3 cleared only by checkpoint + `/clear`".
- **R8.A.5 shared infrastructure block** — Quiet mode override expanded from "decision-required overrides quiet" to "decision-required and drift tier 3 both override quiet mode" (mirroring BOOTSTRAP's blocking-categories list).
- **R8.A.5 configuration file paragraph** — added new flags `drift_tier3_enforced=true` and `quiet_mode_overridden_by_drift_tier3=true` (default true for retrofit; INTENTIONAL VARIATION possible if prior-art reckoning surfaced a custom drift handler).
- **R8.A.3 hook description** — Drift detector entry updated from "soft notice" to "soft notice for tiers 1–2; hard block for tier 3".
- **R8.E CLAUDE.md escalation list** — Drift Alert 3 line updated from "fired Alert 3 (firm) without acknowledgement" to a full description of tier 3 enforcement (agent writes checkpoint, hard-blocked from other tool calls, operator runs `/clear` then `/resume`, `/ack-drift` does not dismiss tier 3).
- **Cheat sheet workflow-signals row** — "Drift alert tier 3" action now reads "Mandatory: agent writes checkpoint (auto-blocked from other tool calls); operator runs `/clear` then `/resume`. `/ack-drift` does not dismiss tier 3" instead of the previous casual "Stop, /checkpoint, /clear, /resume".
- **`.gitignore` block** — added `.claude/sessions/.drift-tier3-*` to the session state files block (the v1.6.1 sentinel file).

**Net change v1.5.0 → v1.5.1:** ~15 lines updated across 7 locations + this changelog entry. No structural changes; no new phases; no state-file schema changes; no migration required for v1.5.0 retrofits — but **existing v1.5.0 retrofits should regenerate their drift-detector hook script to pick up tier 3 enforcement** (operator action, not protocol re-run; same upgrade path BOOTSTRAP v1.6.0 → v1.6.1 documents in section 6.E).

**v1.5.1 architectural asymmetries with BOOTSTRAP** (unchanged from v1.5.0; framing now points at BOOTSTRAP v1.6.0's Post-bootstrap milestones section for the resolution):

- `workflow-source-of-truth.md` (R0.7 PM reckoning) — greenfield has no pre-existing PM artifacts.
- `compliance.md` — brownfield discovers regulatory posture from production reality; greenfield can't reliably commit at bootstrap; **BOOTSTRAP v1.6.0 documents the trigger** ("first regulated user or pursuing SOC 2") that moves greenfield into producing this artifact.
- `contracts.md` (in retrofit context) — brownfield reads existing integration points from code; greenfield discovers them as integrations settle; **BOOTSTRAP v1.6.0 documents the trigger** ("first public API release / first integration goes live").
- `migration.md` — by definition only applies to in-flight modernization.
- `inventory/baseline-metrics.md` (note: greenfield equivalent lives at `metrics/baseline-metrics.md` per BOOTSTRAP v1.6.0) — brownfield has measurable DORA values; greenfield trigger is "~30 commits or first production deploy."
- `inventory/tribal-knowledge.md` — captures prior-maintainer signal; greenfield trigger is "first team handoff."
- `hooks/rollout-schedule.md` — brownfield needs graduated rollout; greenfield trigger is "first additional contributor joins."
- `hooks/worktree-budget.md` — brownfield knows codebase size; greenfield trigger is "codebase exceeds 1GB."
- All `inventory/` files — historical audit of pre-retrofit state has no greenfield equivalent.
- `debt.md` — known issues from existing code; greenfield starts with none.
- Skills: `legacy-pin-test`, `legacy-spec`, `boundary-spec` (RETROFIT-flavored), `prompt-pinning-eval`, `dataset-pin-test`, `convention-categorize`, `prior-art-audit`, `inventory-scan`, `migration-plan`, `ticket-to-spec` — all serve brownfield-specific operations on existing artifacts.

### v1.5

**Asymmetry reframing.** v1.4 (and v1.3 before it) framed the differences between RETROFIT and BOOTSTRAP outputs as "RETROFIT may exceed BOOTSTRAP coverage" with the implication that a future BOOTSTRAP version should add `compliance.md`, `contracts.md`, baseline metrics, hook rollout discipline, etc., to "tighten the equivalence." During scoping for that BOOTSTRAP v1.6 update, the operator challenged the premise: was BOOTSTRAP actually missing these, or were they correctly RETROFIT-only? The honest answer: **correctly RETROFIT-only.**

**Why the previous framing was wrong.** Brownfield projects can answer questions greenfield projects cannot yet answer. Regulatory posture is determinable from production reality (the system processes data; it has users; it operates in an environment); for greenfield, asking the seven yes/no regulatory questions risks false-no answers ("we won't have EU users" → 18 months later, you do). Integration points are facts on the ground for brownfield (the auth APIs exist, the consumed services exist); greenfield knows planned integrations but boundary specs solidify post-bootstrap as integrations actually settle. DORA baseline metrics are computable for brownfield (lead time, change failure rate, test coverage, lint conformance, DORA tier all from existing git history and operations); for greenfield, all values are N/A or 0 — recording them establishes nothing actionable. Hook rollout discipline accommodates existing developer habits, which greenfield doesn't have. Tribal knowledge captures prior-maintainer signal that greenfield doesn't have. Worktree budgeting needs a known codebase size, which greenfield lacks at bootstrap.

**The right place for these in greenfield**, when applicable, is operator self-direction post-bootstrap — adding `compliance.md` when regulatory obligations crystallize, adding boundary specs as integrations settle, capturing baseline metrics when enough commits exist to compute them. Not bootstrap-time interview.

**Changes in this revision:**

- **Mental Model "What success looks like" rewritten.** The "Discovered-late content (RETROFIT may exceed BOOTSTRAP coverage)" subsection is replaced with "Brownfield-discovery artifacts (correctly RETROFIT-only)" enumerating each artifact and why greenfield correctly doesn't produce it.
- **v1.4 changelog footer "Known asymmetries with BOOTSTRAP"** updated to drop "pending BOOTSTRAP v1.6+ updates" language. The asymmetries are now correctly framed as architectural, not pending.
- **No protocol behavior changes.** No new R-phases, no new outputs, no new state-file fields. v1.4 retrofits remain valid; the framing-only update means v1.4 outputs are correctly produced by v1.5 logic — only the conceptual framing in Mental Model and the changelog footer change.
- **Companion BOOTSTRAP version reference** updated from v1.5.0 to v1.5.1. BOOTSTRAP v1.5.1 is a tiny patch adding EARS notation guidance to the `spec-new` skill description (the one v1.4 review item that genuinely applied to greenfield); see the BOOTSTRAP v1.5.1 patch brief for details.

**Net change v1.4 → v1.5:** ~30 lines updated in Mental Model + ~15 lines updated in changelog footer + ~50 lines added in this changelog entry = ~95 lines net change. The retrofit's behavior is identical; only the framing is corrected.

**v1.5 architectural asymmetries with BOOTSTRAP** (these are correct, not gaps):

- `workflow-source-of-truth.md` (R0.7 PM reckoning) — greenfield has no pre-existing PM artifacts.
- `compliance.md` — brownfield discovers regulatory posture from production reality; greenfield can't reliably commit at bootstrap.
- `contracts.md` (in retrofit context) — brownfield reads existing integration points from code; greenfield discovers them as integrations settle.
- `migration.md` — by definition only applies to in-flight modernization.
- `inventory/baseline-metrics.md` — brownfield has measurable DORA values; greenfield has N/A.
- `inventory/tribal-knowledge.md` — captures prior-maintainer signal that greenfield doesn't have.
- `hooks/rollout-schedule.md` — accommodates existing developer habits that greenfield doesn't have.
- `hooks/worktree-budget.md` — needs known codebase size that greenfield lacks at bootstrap.
- All `inventory/` files — historical audit of pre-retrofit state has no greenfield equivalent.
- `debt.md` — known issues from existing code; greenfield starts with none.
- Skills: `legacy-pin-test`, `legacy-spec`, `boundary-spec` (RETROFIT-flavored), `prompt-pinning-eval`, `dataset-pin-test`, `convention-categorize`, `prior-art-audit`, `inventory-scan`, `migration-plan`, `ticket-to-spec` — all serve brownfield-specific operations on existing artifacts.

### v1.4

**PM artifact reckoning + Preview & Commitment + ticket-to-spec migration.** Two new mandatory phases (R0.7, R0.8) plus one new R0 step (12). One new skill (`ticket-to-spec`). Driven by Phase 4 review identifying gaps in v1.3's BOOTSTRAP-equivalence claim.

**Phase 4 review (Round 1) findings F29-F38:**

- **F29 / F35 / F37 / F38 (PM-artifact transition gap, MUST FIX).** v1.3 had no path for handling existing tickets/epics/Linear/Jira/GitHub Issues backlogs when adopting spec-driven workflow. Resolved via:
  - **R0 step 12** *(new, mandatory)* — PM tooling indicator scan. Detects in-repo ticket directories, CI integrations, commit-message ticket references. Output: `inventory/pm-tooling-signals.md`.
  - **R0.7 phase** *(new, mandatory)* — PM Artifact Reckoning. Three strategies (A spec-canonical, B PM-canonical with spec bridge, C hybrid with cutover schedule). Per-archetype defaults. Per-ticket disposition for open tickets (convert-now / defer / close). Output: `.claude/steering/workflow-source-of-truth.md` + `.claude/inventory/pm-artifacts.md`.
  - **R8.B** *(modified)* — defers PM-tool MCP installation to R0.7's `pm_strategy` decision instead of asking fresh.
  - **R8.C** *(modified)* — adds `ticket-to-spec` skill (Sonnet) when `pm_strategy` is `spec_canonical` or `hybrid`. Converts ticket descriptions into spec stubs with original-ticket frontmatter.

- **F30 (Preview & Commitment gap, MUST FIX).** v1.3 had no equivalent of BOOTSTRAP Phase 0.5; operators committed to retrofit before seeing scope. Resolved via:
  - **R0.8 phase** *(new, skippable on operator request)* — Preview & Commitment. Lists every file to be created (35-80 typical), estimates token-budget impact, remaining wizard time, and disk impact. Surfaces all earlier-phase decisions for confirmation. Asks proceed/adjust/cancel.

- **F31 (stale version reference).** Fixed "v1.1" → "v1.3" in the scope table.

- **F32 / F33 (equivalence framing too strong, MUST FIX).** v1.3's "functionally indistinguishable" claim was inaccurate given that `compliance.md`, `contracts.md`, `migration.md` are RETROFIT-only artifacts. Mental Model in v1.4 clarified the framing as "equivalence with documented asymmetries" — RETROFIT may exceed BOOTSTRAP coverage in compliance/PM-transition dimensions because brownfield discovers these late while greenfield bakes them in. **(Update: v1.5 reframed this further — see v1.5 changelog entry. The asymmetries are architecturally correct, not gaps awaiting BOOTSTRAP catch-up.)**

- **F34 (grandfathered language too strong).** Mental Model now says "transitionally grandfathered" — legacy code is held outside spec gates via the legacy allowlist during retrofit and R8.A.6's graduated rollout, then progressively gated as files are touched.

- **F36 (R0 codebase scan didn't detect PM tooling).** Resolved by F29's R0 step 12.

**Net change v1.3 → v1.4:** ~210 lines added (1563 → ~1770). No backward-compatible breakage; v1.3 retrofits remain valid but **must be amended to add R0.7's `workflow-source-of-truth.md` and (for Strategy A or C) ticket-to-spec migration plan.** Operators upgrading from v1.3 should run R0 step 12 + R0.7 retroactively if their project has PM artifacts; otherwise no-op.

**v1.4 known asymmetries with BOOTSTRAP** *(framing corrected in v1.5 — see v1.5 entry above; these are now correctly understood as architectural asymmetries, not gaps awaiting BOOTSTRAP catch-up)***:**
- `workflow-source-of-truth.md` is RETROFIT-only (BOOTSTRAP greenfield projects don't have pre-existing PM artifacts).
- `compliance.md`, `contracts.md`, `migration.md` remain RETROFIT-only because brownfield can answer questions greenfield can't yet answer.

### v1.3

**Equivalence-target framing.** Reoriented the protocol around the explicit success bar: a successful retrofit produces six BOOTSTRAP-equivalent outputs (Steering / Specs / Hooks / Model Assignment / Audio Alerts / Subagent Workflows including Skills + Commands). Introduced new top-level §"BOOTSTRAP Equivalence Target" with per-output checklist and §"Validating Equivalence" with documented-variation rules.

**15 research-derived gap treatments applied:**

- **G6 — Pin-first discipline / characterization tests.** New `legacy-pin-test` skill (Sonnet). R2 declares pin-first rule. R8.A reviewer enforces. R6 smoke test pins before modifying. Per Feathers' technique.
- **G7 — Strangler Fig pattern.** Vocabulary added to Mental Model. Per-archetype patterns in §"Project Archetypes." `migration.md` steering doc candidate added to R5.
- **G8 — Three brownfield SDD spec patterns.** R4 explicitly identifies which apply per project. New `boundary-spec` skill. New `contracts.md` and `migration.md` steering docs. R8.A spec gate enforces "every change updates a spec" discipline.
- **G9 — DORA baseline measurement.** New R0 step 8 captures lead time, change failure rate, test coverage, lint conformance, spec coverage starting at 0%. R7 schedules 30/60/90-day reviews.
- **G10 — Code health awareness.** New R2 step 8 identifies "danger zones" (high churn × complexity × no-coverage). R8.A reviewer enforces stricter rules on danger-zone changes (no architecture+behavior in same PR).
- **G11 — Five brownfield SDD failure modes.** Added to Mental Model with mitigation pointers.
- **G12 — EARS notation.** R5 step 3.5 recommends (not mandates) EARS for spec acceptance criteria.
- **G13 — SDD rigor levels.** Mental Model declares spec-anchored (vs spec-first / spec-as-source). Glossary records.
- **G14 — Hook rollout discipline.** R8.A.6 gives default 4-week graduated warn→block schedule. Bypass-rate monitoring (10% threshold).
- **G15 — Per-archetype strangler/migration patterns.** New table in §"Project Archetypes" mapping each archetype to strangler approach + active spec patterns + hook focus + per-archetype skills. Three new archetype-specific skills: `prompt-pinning-eval` (AI/agent), `dataset-pin-test` (Data/ML), `boundary-spec` (Library/SDK + Service/API + Platform).
- **G16 — Worktree resource budgeting.** R8.A.7 documents ~5x codebase disk usage; sequential vs parallel guidance for codebases over 1GB.
- **G17 — Tribal knowledge interview.** New R0 step 9. Five questions. Output `inventory/tribal-knowledge.md`. Narrative tests recommended.
- **G18 — Production-traffic bootstrap.** New R0 step 11 (conditional, Service/API + AI/agent only). Sample feeds R4 boundary spec authoring.
- **G19 — Anti-corruption layer.** Documented in §"Project Archetypes" per-archetype patterns. Implicit in strangler-fig migrations.
- **G20 lite — Regulated-industry retrofit considerations.** New R0 step 10 detects applicable frameworks (7 yes/no questions covering SOC 2 / HIPAA / PCI-DSS / IEC 62304 / GDPR / FedRAMP / FDA AI/ML PCCP). New `compliance.md` steering doc generated by R5. R8.A.8 documents (does not enforce) regime-specific hooks deferred to v1.4. R7 communicates compliance pointers.

**Other amendments:**

- R6 reframed as Equivalence Smoke Test — validates BOOTSTRAP-shape output, not just workflow execution.
- R7 reframed as equivalence-validation handoff — produces `equivalence-validation.md` checklist artifact.
- Model Assignment Strategy table extended with v1.3 skills.
- Glossary substantially expanded.
- Cheat sheet updated with new workflow signals.

**Phase 3 review fixes (Round 1 + Round 2):**

- F1 — Header version updated to 1.3.0 (was 1.2.0). Inline-at-top changelog removed (duplicated bottom changelog); now points at this section.
- F2 — Fixed "Sonnet 4.7" → "Sonnet 4.6" typo in equivalence target.
- F3 — Fixed wrong file reference: equivalence skip-decision justifications live in `.retrofit-state.json`'s `skip_decisions` field (was incorrectly pointed at `compliance.md`).
- F4 — Clarified "all checklist items" language in Validating Equivalence (was "Each of the 6 categories' items" without count anchoring).
- F5 — Fixed wrong R0 step number for production traffic capture (was step 4, is step 11).
- F6 — Per-archetype hooks weakened from "X hook required" to "consider X" since some referenced hooks aren't in R8.A.3 catalog. Standard set + archetype-defined hooks called out explicitly.
- F7 — Removed AgenticFUSE-specific reference in equivalence target; replaced with generic "multi-step ticket workflow with research-variant + workflow-compliance role" example.
- F8/F9/F20 — R0 step 10 (regulatory regime detection) made mandatory (was unstated). Skip Policy expanded to cover all v1.3 conditional/optional steps. R0 exit criteria updated.
- F11/F23 — R7 step 7 reframed: "Operator's immediate next steps" instead of "the next three things" (since steps 8-9 follow).
- F13/F19 — R6 step 1 module-selection priority clarified (default = stable + non-danger-zone; opt-in = danger-zone). Step 6 ownership clarified (AI runs, operator reviews findings).
- F14 — R8.A.6 rollout schedule column renamed Phase → Week to avoid overloading Phase term.
- F15 — `hook-bypass-monitor` definition concretized into local-developer + server-side options instead of referencing an undefined hook.
- F17 — Subagent name in equivalence target fixed: `code-review` → `reviewer` (BOOTSTRAP convention is `reviewer` subagent invokes `code-review` skill).
- F18 — R8.E.2 escalation list gained v1.3 marker for danger-zone-without-pinning-test.
- F22 — R3 debt sources expanded to include v1.3 inventory outputs (danger-zones, tribal-knowledge, regulatory-context, baseline-metrics).

**Net change:** ~446 lines added (1099 → 1545). No backward-compatible breakage; v1.2 retrofits remain valid. Operators upgrading from v1.2 should re-run R0 steps 8-11 and propagate findings to downstream phases. Version bump from v1.2 → v1.3 reflects significant reorientation around equivalence-target framing while maintaining additive-only changes.

### v1.2

Archetype classification (9 archetypes mirroring BOOTSTRAP), new Phase R0.5, downstream propagation R1/R2/R5/R5.5/R8.A. State schema additions for archetype, archetype_confidence, synthetic_profile, prd_tier_target.

### v1.1

Project-agnosticism, Modernize R2 category, Phase R-1 prerequisite check, BOOTSTRAP v1.5 alignment. Calibrated stability cutoff. Audio alert prior-art reckoning. Source-file count calibration. Degraded mode.

### v1.0

Initial release. Six retrofit phases. Inventory + debt registry + legacy allowlist as core concepts. R8 as embedded summary of BOOTSTRAP equivalents.

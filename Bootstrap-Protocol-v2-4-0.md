# Project Bootstrap Protocol

**Version:** 2.4.0

> **v2.4.0 in-version corrections — TAR telemetry review (2026-07-20, applied per the in-version blocking-fix precedent, no version bump).** Eight findings from a delta adversarial review of the TEL-01 fold, applied without a version bump and marked `[TAR-nn]` at each edit site (identical discipline to the v2.2.0 AR2 round). **TAR-01 (blocking)** — the emitted `telemetry.md` seeded `bootstrap.protocol_version=2.4.0` as a static literal beside the `<archetype>` placeholder, so a naive `lib/templates.py` emission would ship a stale version on every future bump — a fail-silent in the observability layer; resolved by specifying emission-time substitution of both values from state (`bootstrap_protocol_version`) and config (archetype), preserving content-determinism (head note, Companion migration clause, and the `telemetry.md` seed all corrected to the placeholder convention). **TAR-02..06 (advisory, all in `telemetry.md`)** — folded now because the body is not yet wired into the frozen `lib/templates.py`, so these edits are free pre-freeze: TAR-02 removed a committed-file secret-paste vector (the doc steered `OTEL_EXPORTER_OTLP_HEADERS` toward the committed, security-critical `.claude/settings.json`, and no scanner exists to catch it) and corrected the project-vs-managed-settings conflation; TAR-03 named the identity attributes (`user.email`, `user.account_uuid`) that ride every export even at the redaction-clean default; TAR-04 completed the do-not-widen list (`OTEL_LOG_TOOL_CONTENT`, `OTEL_LOG_ASSISTANT_RESPONSES`) and flagged the assistant-response fallback gotcha; TAR-05 caveated that `permission_mode_changed`'s `trigger` attribute is absent on SDK/bridge-originated transitions; TAR-06 clarified that "never to Anthropic" describes the OTel export, not Anthropic's separate operational telemetry. **TAR-07 (Track-A)** — the Companion migration entry's "inert" forward-compat claim dropped its open-question citation; restored (the state-file-compat open question still governs the general posture, not pre-decided here). **TAR-08 (Track-A)** — the 22 Table-of-Contents phase anchors used shorthand slugs (`#phase-0`) that resolve nowhere on GitHub rendering (pre-existing, not a fold regression); repaired to the correct full slugs. Evidence for every finding verified against the live `code.claude.com/docs/en/monitoring-usage` monitoring reference (2026-07-20): all named events/metrics exist, carry the named attributes, and are at or below the seam runtime floor ≥ 2.1.210 — none beta-gated. **Seam impact: none** (documentation and a workspace-resident steering artifact only; no wire surface, no `binds` re-cut; Tessera pin unaffected). Advisory GR2-06 (native checkpointing) remains an open owner decision, unfolded.

> **v2.4.0 — operator-opt-in observability, MINOR (2026-07-20).** One additive recipe, applied changelog-first. No gate semantics change, no wire change, no state-schema change beyond one opt-in flag. **TEL-01 (operator-opt-in observability, add-and-document):** a new skippable Phase 0 decision `telemetry_export_enabled` (**default off**, opt-in, same shape as the 9.5/9.6/9.7 mode flags), recorded in `.bootstrap-state.json`. When enabled, the wizard emits `.claude/steering/telemetry.md` — an operator-facing steering doc (committed, under the existing "all steering docs committed" rule) that documents **Claude Code's native OpenTelemetry surface** (`CLAUDE_CODE_ENABLE_TELEMETRY` + the `OTEL_*` exporter variables) and names the redaction-clean events that map to Bootstrap mechanism health: `tool_decision` / `hook_execution_complete` (gate fire and error rates), `compaction` (drift-threshold validation), `api_error` / `api_retries_exhausted` (infra-failure and usage-limit behavior), `permission_mode_changed` (autonomy escalation), and `token.usage` by `agent.name` (subagent-multiplier evidence). It seeds an `OTEL_RESOURCE_ATTRIBUTES` line tagging `bootstrap.protocol_version` and `bootstrap.archetype` so an operator's own backend can slice mechanism health by both. **[TAR-01]** Both values are substituted at emission time — `bootstrap.protocol_version` from the state file's `bootstrap_protocol_version` and `bootstrap.archetype` from the resolved config — never shipped as static literals, so the emitted body stays a pure function of config+state (content-determinism preserved) and a re-run under a newer protocol re-stamps the line. **compose-do-not-fork:** this is documentation over the substrate's own opt-in telemetry, not new plumbing — the protocol opens no socket and emits nothing itself. The default emission recommends **only** the redaction-clean signal; it explicitly does not enable `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_DETAILS`, or `OTEL_LOG_RAW_API_BODIES`, which stay an operator's deliberate choice against their own backend. Export target is operator-owned; Claude Code sends this data only to the configured OTLP endpoint, never to Anthropic and never to the Bootstrap maintainers. Surfaced in Phase 0 step 6 (skippable-phase decisions), the Phase 0.5 preview, and the skip policy; recorded as a `.bootstrap-state.json` field; cross-referenced from the Assumption Ledger's subagent-token-multiplier row (re-validation evidence source) and the GR2-02 "OTel export is optional" lines (forward pointer to `telemetry.md`). **Rejected alternative (locked reason):** protocol-owned telemetry egress to the maintainers ("phone-home") — rejected on GAR-04 category-mismatch (fleet metrics), the wire-surface/exfiltration threat it would add to a local-first autonomy harness, and the complexity budget. Maintainer learning is served by operator-initiated sharing from the operator's own backend, not by any channel the protocol owns. **Seam impact: none.** The sole delta is a workspace-resident steering artifact plus one opt-in state field and wizard/doc text; no wire surface, no gate, no `binds` re-cut. The owed substrate-release seam re-cut (per the v2.2.0 head) is untouched and still owed; the Tessera pin is unaffected. See the Companion's Migration notes (v2.4.0 entry).

> **v2.3.0 — GR2 adoptable fold: progress artifact, trajectory retention, assumption ledger, MINOR (2026-07-20).** Three additive, GAR-corrected recipes from the GR-2 grade audit, applied changelog-first. No gate semantics change, no wire change, no state-schema change. **GR2-01 (per-task progress artifact, add-and-link):** a new committed artifact `.claude/specs/<slug>/progress.md` (Status / Completed / In flight / Failed approaches, each failed entry carrying a do-not-retry flag), created at task start and updated at every iteration boundary and interactive checkpoint. It **links** to `decisions.md`, `learnings/`, and the latest checkpoint and must not duplicate them (compose-do-not-fork applied to the protocol's own artifacts, per GAR-07); autonomous-mode priming reads it before the task brief so dead ends are not re-attempted. Edited in Phase 7 step 5 (artifact role), Phase 9.5 step 3 and the Phase 9.6 goal-loop priming (the read), the loop/goal implementer variant bodies and the Phase 8 `CLAUDE.md` reading list (the consume note), and the commit-policy enumeration. **GR2-02 (trajectory retention):** the deliverable-contract binding-comment enumeration gains a fourth item requiring the operator-completed loop to retain each iteration's stream JSON — already produced by the v2.2.0 `--output-format stream-json --verbose` dispatch — at `.claude/logs/trajectory-<task-id>-<iter-n>.jsonl` (gitignored under the existing `.claude/logs/` rule; pruning is part of the same operator obligation — corrected at the v2.4.0 code fold, since the 7-day state policy covers `.claude/sessions/` and no emitted artifact prunes `.claude/logs/`); `loop-final-<task-id>.md` gains a required `Trajectory` line linking the retained files, so an unattended run stays answerable after the fact. OTel GenAI span export is named optional, not required (GAR-04: fleet metrics excluded as category-mismatched). This is retention over an already-emitted stream, not new plumbing. **GR2-03a (assumption ledger):** a new normative artifact `.claude/steering/assumption-ledger.md` and a new `## Assumption Ledger` section, seeded at bootstrap with each harness behavior that exists to compensate for a model limitation (drift thresholds 50/120/3, interactive tier-3 hard reset, subagent token multipliers, max-iterations defaults) plus its calibrated model generation and a re-validation trigger; the wizard surfaces due entries on any pinned-model or runtime-floor change as a fail-loud, non-blocking notice. Cross-reference pointers added at the §6.E drift thresholds (corrected at the v2.4.0 code fold from §6.D, which is the hook security & correctness checklist), the Phase 7 token-multiplier note, and the Phase 9.5 max-iterations default. **Recorded, not adopted (Proposed-revisions appendix, GR-2 subsection):** GR2-03b (interactive tier-3 compaction path), GR2-04 (intent-class gate predicates — carries forward and supersedes G-1), GR2-05 (OS-level sandboxing in the emitted posture), and GR2-06 (native-checkpointing re-score) as OPEN QUESTIONs pending owner decision; GR2-07 (mid-step verification) recorded as a deferral with its locked constraints. Provenance: these recipes are post-adversarial-review — a GAR review (GAR-01..08) corrected the underlying grade doc's evidence first (the context-reset-obsolescence claim is Zylos's third-party analysis, not Anthropic; "context anxiety" is Cognition's term; Anthropic's Opus 4.6-era remedy for "context rot" is compaction; the checkpointing deferral lives in seam §9 / Tessera §8.8, not a Bootstrap section). The GAR-corrected grade transcript is not folded in verbatim — the complexity-budget discipline argues against importing a full self-review document; this note and the appendix subsection carry the lineage instead. **Seam impact: none.** All three adopted deltas are workspace-resident artifacts and comment-contract text; no wire surface, no gate, no `binds` re-cut. The owed substrate-release seam re-cut (per the v2.2.0 head) is untouched and still owed; the Tessera pin is unaffected. See the Companion's Migration notes (v2.3.0 entry).

> **v2.2.0 — usage-limit coping + gap-closure merge, MINOR (2026-07-20).** Two things in one bump. **(1) Renumber + rebase:** the usage-limit capability was briefly drafted as "v2.1.0" on 2026-07-20 before reconciliation revealed the implementation had already spent that identifier on the substrate-OPERATIVE release (finding RC-01); the capability lands here as 2.2.0, rebased onto the 2.1.0 reality. **(2) The capability:** reset-aware usage-limit handling bound into the per-task wrapper skeletons, consuming the Claude Agent SDK's `rate_limit_event` / `RateLimitInfo` stream contract. Per the RC-11 finding, the normative text binds the **emitted skeleton's comment contract** (what the operator-completed iteration loop must do), not a hypothetical complete wrapper: the skeleton's dispatch instruction gains `--output-format stream-json --verbose` alongside `--worktree`, and the binding comments require the loop to distinguish a `rejected` usage-limit rejection (reset-aware wait: honor `resets_at` + jitter, ceiling `usage_limit_max_wait_seconds`, halt with the new `exit_reason` `"usage-limit-reset-abandoned"` beyond it) from transient infrastructure failures (unchanged sleep-briefly-retry-once-then-halt). Three new config keys in `loop-config.md`/`goal-config.md`: `usage_limit_wait` (`reset-aware` | `off`, default `reset-aware`), `usage_limit_max_wait_seconds` (default `21600`), `usage_limit_wait_jitter_seconds` (default `60`). **Also merged in this bump (gap-closure, findings RC-05/06/07/12):** the wrapper deliverable contract is now normative (Phase 9.5 "Deliverable contract" — proposal B-1 ADOPTED, reading (b): guarded fail-safe skeletons); the emitted skeleton comments must enumerate the full `exit_reason` value set and the morning-after summary's required structure incl. the `Ended because` line; and Phase 9.6 blesses the previously-unenumerated emitted goal-config keys. Seam impact **[AR2-04 corrected]**: 2.2.0's own deltas (one `exit_reason` value, three config keys, `rate_limit_event` consumption) are additive and introduce no MAJOR trigger of their own — but they do **not** ship as a standalone seam MINOR, because the seam contract (v1.2.0) still `binds` `bootstrap_protocol: 2.0.0 @ 1fa5bb6…` exactly. Entering the wire requires the binds re-point that the seam itself pre-classifies as the substrate-release seam event — at least MINOR by §8.1a, and MAJOR because re-pointing drops the previously-satisfying 2.0.0. These 2.2.0 deltas ride inside that owed re-cut, which also owes a §5 stream-event row for `rate_limit_event` (wire shape per Phase 9.5; floors verified: CLI emission since ~v2.1.45–2.1.49 ≤ runtime floor 2.1.210; typed `RateLimitEvent` in `claude-agent-sdk` 0.1.49 ≤ SDK floor 0.1.60). Consumer re-validation happens at that re-cut. See the Companion's Migration notes (v2.2.0 entry).

> **v2.2.0 in-version corrections — AR2 adversarial review (2026-07-20, applied per the in-version blocking-fix precedent).** Six blocking findings applied without a version bump, marked `[AR2-nn]` at each edit site: **AR2-01** — the runner's response to an observed `usage-limit-reset-abandoned` halt was stated three mutually-contradictory ways (enum: queue-tier value; summary: run-ending render; Phase 9.7: "record and continue"); resolved to **terminal at the queue level** with graceful shutdown and propagation of the bucket/reset time, with its own termination-table row, counted toward neither halt threshold (continuing dispatches into an account-level cap manufactures a mislabeled `three-consecutive-halts` cascade). **AR2-02** — `usage_limit_wait: off` said both "immediate halt" and "better handled by the transient path" in one sentence; resolved to: `off` disables the branch and routes rejections to the transient path (pre-2.2.0 behavior). **AR2-03** — the comment contract named the Python SDK dataclass fields (`resets_at`/`rate_limit_type`) as stream fields; the raw `stream-json` wire nests camelCase keys (`rate_limit_info.resetsAt`/`.rateLimitType`) under top-level `type: "rate_limit_event"` (verified against the CLI's emitted JSON and the official SDK reference) — a shell loop implementing the contract verbatim would never trigger the branch; wire shape now stated, envelope-typed matching required (no substring grep), absent/past reset timestamp routed to the transient path. **AR2-04** — the "Seam impact: MINOR, no binds re-cut" claim understated the owed seam event; corrected (the deltas ride inside the owed substrate-release binds re-point, which is a seam MAJOR per §8.1a; floors verified current). **AR2-05** — the retry-watchdog note wrongly scoped `CLAUDE_CODE_RETRY_WATCHDOG=1` to `sdk-callable` installs; it is a substrate-independent CLI env var below the runtime floor. **AR2-09** — §3.1-style deferral register added (run-summary template emission; advisory eighth IC check) and the runner-tier key-less posture declared explicitly. Advisory findings AR2-06/07/08/10 recorded in the review report, not applied. Verification basis: doc-only review (repo zip unavailable this session); implementation claims inherited from the handoff's verified state.

> **v2.1.0 — SDK substrate OPERATIVE, retro-documented (implementation branch `version-2-1-0`; doc entry recorded 2026-07-20).** The implementation's Milestone B: `PROTOCOL_VERSION = "2.1.0"`, IC-1..IC-7 all satisfied and enforced by a live gate. The installer emits `.claude/sdk_gates/gates.py` (seam §9 verbatim; seven gates as `PreToolUse`/`PostToolUse` callables in the structured deny shape; security-critical tier) alongside the retained shell suite (the SEV-1 manual path), and writes `gate_substrate: "sdk-callable"` only when the config requests it AND every `lib/ic_checks.py` self-check passes — otherwise the install is refused loudly and the substrate stays `"shell"`. Native worktree routing (IC-6) resolved with a recorded caveat: `--worktree` is confirmed against official docs, but its introduction release is not verifiable from official release notes, so wrappers rely on the seam runtime floor ≥ 2.1.210, which subsumes it. Runtime floor confirmed against official changelogs 2026-07-18; `claude-agent-sdk` feature floor v0.1.60. This entry retro-documents in the protocol lineage what previously existed only as the implementation changelog and a marked annotation in the v2.0.0 document; no doc of this name shipped at the time. A 2.1.0 install stamps `bootstrap_protocol_version: "2.1.0"`.

> **v2.0.0 — breaking change (declared direction; implementation staged).** This major bump **declares the migration direction and its locked constraints**: enforcement and loop layers move onto the Claude Agent SDK (gates as `PreToolUse` callables; native permission modes; native worktree routing), plus the Fable 5 / Opus 4.8 / Sonnet 5 / Haiku 4.5 model remap. **Conformance note:** a v2.0.0 wizard still installs the shell-gate suite — the SDK-callable substrate becomes operative in a subsequent 2.x release once the reconciliation items below are resolved against the live script surface. **[2.1.0 update — substrate OPERATIVE]** Reconciled at protocol 2.1.0 (branch `version-2-1-0`): the installer emits `.claude/sdk_gates/gates.py` (seam §9 verbatim; security-critical tier) alongside the retained shell suite, and writes `gate_substrate: "sdk-callable"` only when the config requests it AND every `lib/ic_checks.py` IC-1..IC-7 self-check passes — otherwise the install is refused loudly and the substrate stays `"shell"`. The native-worktree item resolved with a recorded caveat: `--worktree` confirmed against official docs, introduction release unverifiable, subsumed by the seam runtime floor ≥ 2.1.210. To keep the version signal honest, the state file records the installed enforcement substrate independently of the document version via a `gate_substrate` field (`"shell"` on a 2.0.0 install; `"sdk-callable"` once granted at 2.1.0 per the OPERATIVE note above). Per the Tessera↔Bootstrap seam contract this bump is a MAJOR seam event: it forces a `binds` re-cut and consumer re-validation. **Migration from 1.x is not automatic** — see the Companion's Migration notes (v2.0.0 entry).

> **v2.0.1 — wording-only PATCH (2026-07-18).** Operator-facing wording and one template line; no gate, wire, capability, or Implementation Contract change. (1) The Phase 0 verbatim question strings for 9.6/9.7 are restyled to plain-writing form — content preserved; these are installer-conformance strings, so this bump is the versioned change that permits the new phrasing. (2) The morning-after summary's required structure gains an "Ended because" line: the stable run-level `exit_reason` code plus one plain sentence (the code is the machine key and is unchanged; the sentence is the operator render). (3) A non-normative "Grade-audit-derived" proposal subsection is appended to the Proposed-revisions appendix. IC-1..IC-7, `gate_substrate`, the emitted hook set, sentinel paths, and all wire/state field names are untouched. Commit-pinned consumers are unaffected; the standard pin-bump process applies only on optional adoption. See the Companion's Migration notes (v2.0.1 entry).

> **For the AI:** When the operator opens this file and asks you to bootstrap, you run this protocol end-to-end. You are conducting an interview, not writing a document. After each phase, write the artifact, confirm with the operator, then proceed. Do not batch. Do not skip phases (see the skip policy below). Do not generate application code in any phase before Phase 9. If your environment provides interactive multi-choice tools, use them; otherwise, ask in plain markdown.

> **v2.0.0 Implementation Contract (normative).** The following are REQUIREMENTS the implementation must satisfy before any wizard may write `gate_substrate: "sdk-callable"`. They exist because the spec deliberately leads the code (owner decision, 2026-07-17); each also resolves a reconciliation finding (IG-xx) from the main-branch gap analysis. **[2.1.0 status: ALL SATISFIED]** — every item below is implemented and enforced by `lib/ic_checks.py` at the install gate; the list is retained as the normative definition of what the gate checks. Until all pass on a given install, `gate_substrate` remains `"shell"`. **[AR2-09b] Deferred at 2.2.0 (post-2.2.0 bucket): an advisory eighth check asserting the wrapper comment-contract enumerations (Phase 9.5/9.7) at install time.** Cost of deferral: comment-contract drift on a hand-edited install goes undetected until operator review — bounded because repo CI golden fixtures and `test_usage_limit_contract` already assert the emissions at build time; the gap is install-time only, and the check would be advisory (never blocks `gate_substrate`).
> 1. **IC-1 (IG-01): `bootstrap-interview synthesize --validate-only`** — a true validate-only mode: parses the interview file, runs `resolve_config`, reports invariant violations, writes nothing, exit code reflects validity. Until shipped, callers use the interim path: `synthesize` to a temp output + `bootstrap-install --dry-run`/`--print-config`.
> 2. **IC-2 (IG-02): Project-root sentinels** — `<project-dir>/.halt` and NEW `<project-dir>/.halt-hard` honored by `auto.sh`/`loop.sh`/`goal-loop.sh` *in addition to* the existing `.claude/queue/.halt`/`.resume` (which remain for backward compatibility). Root `.halt` = graceful stop at next boundary; root `.halt-hard` = immediate wrapper exit, in-flight `claude -p` NOT signalled by the wrapper (killing processes is the caller's job — e.g. Tessera §12.3). Dual-honor is permanent, not transitional.
> 3. **IC-3 (D-01): `gate_substrate` state field** — the state-file writer emits `gate_substrate: "shell" | "sdk-callable"`; migration tooling adds it to 1.x state files as `"shell"`.
> 4. **IC-4 (IG-08): LLM advisor default model** — `BOOTSTRAP_INTERVIEW_LLM_MODEL` default bumped from the retired `claude-sonnet-4-20250514` to a current ID (`claude-sonnet-5` at time of writing); the advisor's deterministic-fallback-on-failure behavior is retained and tested.
> 5. **IC-5 (Phase 6 note): Gates as SDK `PreToolUse` callables** — each gate (secrets, spec-commit, dependency, test, tdd, eval, format-lint) re-expressed as a `HookMatcher` callable returning structured deny; shell hooks retained for session-lifecycle events the Python SDK lacks (`SessionStart`/`SessionEnd`) and as the documented SEV-1 manual path.
> 6. **IC-6 (Phase 6.5 note): Native worktree routing** — wrappers delegate worktree creation/claiming to Claude Code's native `--worktree` mechanism; the hand-rolled claim/sentinel dance is retired where the native mechanism covers it and retained only where it doesn't (documented per case).
> 7. **IC-7 (IG-03): Hook-tier declaration** — the emitted hook set and its three-tier hand-edit classification (security-critical / autonomy-critical / non-critical, per seam §7.2) are declared in a machine-readable form the installer emits (e.g. in the manifest), so downstream consumers read the tiers rather than hard-coding them.
> Verification: the seam's `protocol-compatibility` job gains an IC checklist assertion; `gate_substrate: "sdk-callable"` is refused by the installer unless IC-1..IC-7 self-checks pass.

> **Companion reference:** `Bootstrap-Protocol-Companion-v2-4-0.md` holds the Mental Model, Model Assignment Strategy, Post-bootstrap milestones, scope-exclusion list, Cheat Sheet, Glossary, Migration notes, and the rationale for phase numbering. Consult it when this file references those topics.

## Table of Contents

**Front matter**
- [Prerequisites](#prerequisites)
- [Project Archetypes](#project-archetypes)
- [Skip Policy](#skip-policy)
- [Recovery & State](#recovery--state)
- [Assumption Ledger](#assumption-ledger)

**Foundation (0 – 0.5)**
- [Phase 0 — Preflight & Classification](#phase-0--preflight--classification)
- [Phase 0.5 — Preview & Commitment](#phase-05--preview--commitment)

**Steering (1 – 5)**
- [Phase 1 — Product Steering (`product.md`)](#phase-1--product-steering-productmd)
- [Phase 2 — Technical Steering (`tech.md`)](#phase-2--technical-steering-techmd)
- [Phase 2.5 — Dependency Policy (`deps.md`)](#phase-25--dependency-policy-depsmd)
- [Phase 2.7 — Secrets & Sensitive Data Policy (`secrets.md`)](#phase-27--secrets--sensitive-data-policy-secretsmd)
- [Phase 3 — Structure Steering (`structure.md`)](#phase-3--structure-steering-structuremd)
- [Phase 4 — Principles Steering (`principles.md`)](#phase-4--principles-steering-principlesmd)
- [Phase 5 — CI/CD Steering (`ci-cd.md`)](#phase-5--cicd-steering-ci-cdmd)

**Enforcement (6 – 6.5)**
- [Phase 6 — Hooks (`.claude/settings.json` and `.claude/hooks/`)](#phase-6--hooks-claudesettingsjson-and-claudehooks)
- [Phase 6.5 — Tools & MCP Configuration](#phase-65--tools--mcp-configuration)

**Workflow & integration (7 – 10)**
- [Phase 7 — Skills, Commands, Agents, and Workflow](#phase-7--skills-commands-agents-and-workflow)
- [Phase 7.5 — Spec Versioning Protocol](#phase-75--spec-versioning-protocol)
- [Phase 7.6 — Spec roster derivation](#phase-76--spec-roster-derivation)
- [Phase 8 — Root `CLAUDE.md` and Escalation Rules](#phase-8--root-claudemd-and-escalation-rules)
- [Phase 9 — Smoke Test (Optional but Recommended)](#phase-9--smoke-test-optional-but-recommended)
- [Phase 9.5 — Autonomous Loop Mode (Optional)](#phase-95--autonomous-loop-mode-optional)
- [Phase 9.6 — Goal-Supervised Mode (Optional)](#phase-96--goal-supervised-mode-optional)
- [Phase 9.7 — Autonomous Queue Mode (Optional)](#phase-97--autonomous-queue-mode-optional)
- [Phase 10 — Handoff](#phase-10--handoff)

**Closing**
- [Protocol rules for the AI](#protocol-rules-for-the-ai)

---

<a id="prerequisites"></a>
## Prerequisites

Before starting, verify:

- [ ] AI has filesystem write access to the working directory.
- [ ] AI can read existing code if present (greenfield is fine; existing codebase is also fine).
- [ ] AI can execute shell commands to test hooks (or you can run them manually after).
- [ ] You have at least 90 minutes of focused time, plus PRD time if not yet written. Standard PRD projects typically run 90–240 minutes total wizard time; add 15–25 minutes if opting into Phase 9.5 (autonomous loop mode), 10–15 minutes if opting into Phase 9.6 (goal-supervised mode), and 15–20 minutes if opting into Phase 9.7 (autonomous queue mode). The three are independent — opting into all of them adds all three increments. Note that Phase 9.7 additionally requires at least one of Phase 9.5 or Phase 9.6 to be enabled (queue mode dispatches per-task mechanisms; with neither enabled, there is nothing to dispatch).

If any of these aren't met, stop and resolve them first. The protocol assumes them.

---

<a id="project-archetypes"></a>
## Project Archetypes

The protocol classifies your project in Phase 0 and uses the classification to decide which phases run and what questions get asked.

| Archetype | Examples | Required PRD tier | Notes |
|---|---|---|---|
| **CLI tool** | dev utilities, build tools, single-binary scripts | Micro | CI/CD simplifies to release flow only |
| **Library / SDK** | npm package, Python lib, internal shared module | Standard | Adds semver and public API discipline; no deploy environments |
| **Service / API** | backend microservice, REST/GraphQL API, worker | Standard | Skips frontend conventions |
| **Full-stack app** | web app with frontend + backend + DB | Standard | All phases run fully |
| **Mobile app** | iOS, Android, React Native, Flutter | Standard | Web deploy gates replaced by app store flow |
| **Data / ML pipeline** | ETL, training pipeline, inference service | Standard | Auth replaced by data access controls |
| **AI / agent system** | LLM-powered tool, multi-agent system, prompt-driven app | Standard | Adds prompt versioning, evals, cost tracking |
| **Platform / multi-component** | products with multiple deployable units, monorepo platforms | Full | All phases, possibly run per component |
| **Other** | browser extensions, games, firmware, plugins, hybrid systems, anything not above | Standard (default) | Phases adapt via dimension answers in Phase 0; the AI maps dimensions to a synthetic archetype profile |

**PRD tiers:**

- **Micro PRD** — one page, ~10 minutes. Problem, primary user, success criterion, scope. For projects with a single owner and casual maintenance.
- **Standard PRD** — 3–5 pages, 30–60 minutes. Adds personas, user journeys, non-goals, dependencies, risks. For projects maintained for months with multiple stakeholders.
- **Full PRD** — multi-section, several hours. Adds market context, competitive analysis, phased rollout, metrics framework, per-component scoping. For platforms or anything with cross-team dependencies.

The wizard cannot proceed without a PRD at the appropriate tier. If one doesn't exist, the wizard runs an interview to produce one before any `.claude/` files are written.

---

<a id="skip-policy"></a>
## Skip Policy

Some phases are non-negotiable. Some can be skipped on operator request.

- **Required (cannot skip):** 0, 0.5, 1, 2, 3, 6, 7, 8.
- **Required but archetype-conditional:** 2.5 (skipped if the archetype has no external deps, e.g., a script with stdlib only), 4 (always required, but starter set varies), 5 (CI/CD — required for projects with pipelines; opt-out path produces a minimal `ci-cd.md` recording "no CI/CD" if the operator confirms in Phase 0).
- **Skippable on explicit operator request:** 2.7 (Secrets — skippable only if the project handles no secrets at all), 6.5 (Tools & MCP — skippable if the operator wants only built-in features and no MCPs at all; not recommended), 7.5 (Spec versioning — skippable for solo, short-lived projects), 7.6 (Spec roster derivation — skippable for PRDs too rough to enumerate deliverables cleanly; on skip, INDEX.md retains its placeholder row and `/spec-new` invents slugs at call time), 9 (Smoke test), 9.5 (Autonomous loop mode — opt-in; default skip; recommended to defer to first 5–10 operator-in-loop tasks before enabling on a greenfield project), 9.6 (Goal-supervised mode — opt-in; default skip; independent of 9.5, can be enabled alone or alongside loop mode; recommended to defer to first 10–20 operator-in-loop tasks on a greenfield project so the classifier's sixth-criterion and recommendation rule can be calibrated against real evidence), 9.7 (Autonomous queue mode — opt-in; default skip; **requires at least one of Phase 9.5 or Phase 9.6 to be enabled** — the wizard refuses to set up queue mode otherwise; strongly recommended to defer to at least 4 weeks of real operating time on the per-task mechanisms before enabling, so the queue does not amplify per-task failure modes that have not yet been characterized). **Telemetry export (`telemetry_export_enabled`)** — opt-in; default skip; when enabled the wizard emits `.claude/steering/telemetry.md` documenting Claude Code's native opt-in OpenTelemetry surface pointed at an operator-owned backend (TEL-01). Independent of every autonomous mode; enabling it changes no gate, no wire, and no runtime behavior — it only writes a steering doc and records one state flag. The protocol never transmits anything itself.

If the operator requests skipping a required phase, the AI states why the phase is required and asks for explicit override acknowledgment ("I understand this means [specific consequence]"). Only then proceeds.

---

<a id="recovery-state"></a>
## Recovery & State

The protocol writes a state file at `.claude/.bootstrap-state.json` after each phase exit. It contains: archetype, completed phases, last phase started, PRD path, deferred items, synthetic profile (for "Other"), CI/CD opt-out flag, `bootstrap_protocol_version`, the three autonomous-mode opt-in flags (`loop_mode_enabled`, `goal_supervised_mode_enabled`, `queue_mode_enabled`), the `telemetry_export_enabled` opt-in flag (default `false`; when `true`, `.claude/steering/telemetry.md` is emitted — see the skip policy and Phase 0 step 6), and the three per-mode tracking lists:

- `loop_in_flight: [{task_id, iteration, started_at, worktree_path?}, ...]` — maintained by the loop wrapper. Empty when no loop is running; one entry per concurrent loop.
- `goal_in_flight: [{task_id, iteration, started_at, worktree_path?}, ...]` — parallel to `loop_in_flight`, maintained by `goal-loop.sh` under the same lock-and-rename protocol described below.
- `queue_runs_history: [{run_id, start_timestamp, end_timestamp, exit_reason, tasks_attempted, tasks_completed, tasks_halted, total_iterations, total_tokens_estimated}, ...]` — an append-only list of historical queue runs maintained by `auto.sh`. Appended on run start with the start timestamp and a placeholder end; updated in place on terminal exit.

A single task may appear in `loop_in_flight` *or* `goal_in_flight` but never both; the wrappers enforce this with a race-safe claim protocol (atomic `O_CREAT|O_EXCL` write of the per-task active sentinel, then a sibling-sentinel-and-list check under `flock` on the state file) — see Phase 9.5's "Race-safety summary" for the full mechanism. All read-modify-writes of `loop_in_flight`, `goal_in_flight`, and `queue_runs_history` are performed under `flock` on `.claude/.bootstrap-state.json` and committed via the tmpfile-then-rename idiom; this is the concrete meaning of "atomic update" everywhere it appears in this document. The queue runner does **not** duplicate `loop_in_flight` or `goal_in_flight` tracking — those continue to be maintained by the per-task wrappers, which `auto.sh` invokes. The runner's only new in-flight state is the file-level sentinel `.claude/queue/.run-active` (written via the same `O_CREAT|O_EXCL` idiom; not in the state file).

For state-file migration from older protocol versions, see `Bootstrap-Protocol-Companion-v2-4-0.md`'s **Migration notes** section.

**`exit_reason` enum:** the `exit_reason` field in each `queue_runs_history` entry takes one of the following values. Most correspond to a row of the Phase 9.7 termination-conditions table, but the correspondence is not one-to-one: the single SIGINT/SIGTERM/`.halt`-sentinel row maps to two values (`"signal-interrupt"` and `"manual-halt-sentinel"`); the table's "continue" rows and its pause row produce no `exit_reason` at all (see the note after this list); and `"infrastructure-failure-crash-recovery"` and `"operator-only-timeout"` are written by runner behaviors documented elsewhere in Phase 9.7 (the crash-recovery close-out of a dangling entry, and the paused-then-time-budget-elapsed outcome of the pause row) rather than by their own dedicated table row. The values:
- `"queue-empty"` — all ready-to-run tasks completed; nothing left to dispatch, nothing deferred (terminal success).
- `"deferred-only-remaining"` — all "Ready to run" candidates completed; only "Deferred" tasks remain with no operator-actionable predecessor. The queue made all the progress it could but the operator chose to defer the rest. Distinct from `"queue-empty"` so the morning-after summary surfaces the residue.
- `"urgent-escalation"` — a dispatched per-task wrapper halted with one of the five urgent escalation criteria. Non-configurable; the queue always halts.
- `"three-consecutive-halts"` — three consecutive non-urgent task-level halts within the run; diagnostic signal about the queue itself. Threshold configurable via `consecutive_halt_threshold`.
- `"time-budget-exhausted"` — operator-set wall-clock budget reached.
- `"token-budget-exhausted"` — operator-set token budget reached.
- `"task-budget-exhausted"` — operator-set task-count budget reached.
- `"signal-interrupt"` — SIGINT or SIGTERM received; graceful shutdown.
- `"manual-halt-sentinel"` — `.claude/queue/.halt` sentinel observed at a dispatch decision point.
- `"infrastructure-failure"` — two consecutive runner-level (not per-task) failures.
- `"infrastructure-failure-crash-recovery"` — written by the next runner invocation when it finds a dangling `queue_runs_history` entry from a previously crashed run; not produced by a live runner during its own lifetime.
- `"operator-only-timeout"` — the runner was paused with no dispatchable work remaining (all "Ready to run" tasks transitively blocked on operator action) and the time budget elapsed before the operator resumed.
- `"usage-limit-reset-abandoned"` — a dispatched per-task wrapper observed a `rejected` usage-limit `rate_limit_event` whose reset time implied a wait longer than the configured `usage_limit_max_wait_seconds` ceiling, and therefore declined to sleep and halted (see Phase 9.5 "Infrastructure-error handling"). Written by the per-task wrapper into its `loop-final-<task-id>.md`; **[AR2-01]** when the runner observes the halt it terminates the run (graceful shutdown, per the Phase 9.7 termination table) and propagates this value as the run's `exit_reason` — every remaining dispatch shares the same account cap, so continuing would only manufacture repeat rejections. Distinct from `"infrastructure-failure"` because nothing failed — the account simply hit a cap that resets at a known future time the operator should decide whether to wait for. The morning-after summary's `Ended because` line renders this code naming the limiting bucket and the reset time.

Successful per-task terminations (`max-iterations`, `goal-condition-suspect`, `terminal-success`) do not produce a queue-level `exit_reason` on their own — the runner continues to the next task unless `pause_on_*` is set for that termination class, or the three-consecutive-halts threshold is reached.

**Concurrency rule across autonomous modes.** When more than one autonomous mode is enabled, concurrency budgets apply to the *combined* sum across modes, not to each list independently. The two per-task lists (`loop_in_flight` and `goal_in_flight`) share a single budget; a task in either list counts the same. **Recommended starting concurrency: 2 across all autonomous modes combined for the first week of use**, expanding based on review throughput. Running more concurrent autonomous tasks than the operator can review in the resulting `decisions-log-<task-id>.md` and `loop-final-<task-id>.md` batch defeats the point — operators who can't keep up with review should reduce concurrency before reducing modes.

When queue mode is enabled, the runner has its own `max_concurrent_tasks` cap in `auto-config.md` (default 2). The runner counts its own active dispatches; the per-task wrappers count their own runs. Each dispatched task occupies one slot in either `loop_in_flight` or `goal_in_flight` per the per-task wrapper that runs it, so when the runner is the only dispatcher, the two counts agree by construction. The runner's `max_concurrent_tasks` should not be set higher than the combined-modes cap above. **Manual dispatch alongside an active queue run is the failure mode.** Operators manually invoking `loop.sh` or `goal-loop.sh` while `auto.sh` is running with `.run-active` present should count their manual dispatches against the same cap — the wrappers do not coordinate with the runner beyond the existing mutual-exclusion `loop_in_flight`/`goal_in_flight` duplicate-check, so this is an operator-respected convention, not a mechanical enforcement. For queue mode specifically, "first week" of the concurrency-2 starting recommendation extends to **first four weeks** given the higher unattended-time stakes.

**State file naming convention:** all bootstrap-internal state files use the dotfile convention (`.bootstrap-state.json`, `.bootstrap-incomplete`, `.drift-ack`, `.drift-state`). Operator-facing artifacts use regular naming (`CLAUDE.md`, `Bootstrap-Protocol-v2-4-0.md`, etc.). This makes hidden state easy to gitignore as a group.

**Confirmation tempo:** every phase ends with **approve / edit / start over**. Operators who want to move faster can say **"fast confirm"** at the start of the bootstrap; the AI will then accept terse confirmations like "ok," "go," "yes" without re-prompting. Operator can revert to detailed confirmation at any point. Critical phases (0, 0.5, 6, 7, 8) always require explicit approval regardless of fast-confirm setting because their artifacts are foundational.

**On resume:** the AI reads `.bootstrap-state.json`, summarizes what's done, asks where to continue. The operator can request "continue from last," "redo phase X," or "start over."

**To revisit a phase:** the operator says "go back to phase X." The AI loads the existing artifact, asks what to change, rewrites, and asks whether downstream phases need updating (e.g., changing principles in Phase 4 may require revisiting `code-review` skill in Phase 7).

**To bail out:** the operator says "stop bootstrap." The AI offers two options: (a) commit `.claude/` as a WIP branch with a `.bootstrap-incomplete` flag file noting where it stopped (parsed by future resume attempts), or (b) delete `.claude/` and `docs/prd/` and revert. The AI does not silently abandon partial state.

**To disable hooks:** if a hook misbehaves, hooks can be disabled by renaming `.claude/settings.json` to `.claude/settings.json.disabled` (or removing the relevant block). The AI mentions this in Phase 6.

---

<a id="assumption-ledger"></a>
## Assumption Ledger

Some of this protocol's defaults are not timeless — they exist to compensate for a specific model generation's limitations, and a better model can make them wrong (too conservative, or masking a regression). The **assumption ledger** makes that staleness class visible instead of leaving it re-litigated ad hoc. It is a normative artifact, `.claude/steering/assumption-ledger.md`, seeded at bootstrap and committed with the other steering docs.

Each row records four things: the **behavior**, the **model limitation it compensates for**, the **model generation it was calibrated against**, and a **re-validation trigger** (the event that should make someone re-check it). The seed rows are:

| Behavior | Compensates for | Calibrated against | Re-validation trigger |
|---|---|---|---|
| Drift thresholds (50 tool calls / 120 min / 3 file reads) | Context degradation ("context rot") within a long session | Current runtime-floor model tier | Any pinned-model or runtime-floor tier change |
| Interactive tier-3 hard reset (no acknowledge) | Operator self-override at saturated context being the failure mode | Current runtime-floor model tier | Any pinned-model tier change, or a shift in the substrate's native compaction behavior |
| Subagent token multipliers (~2–3x mixed-model) | Per-session context cost under the current price/tokenizer structure | Pre-remap estimate; re-derive on Sonnet 5 | Any price/tokenizer or model-tier change |
| Max-iterations default (10 per task) | Bounded blast radius when a task cannot converge | Current runtime-floor model tier | Any pinned-model tier change |

**The wizard surfaces due entries fail-loud, non-blocking.** When the operator changes a pinned model tier or the runtime floor moves (the same event that the v2.0.0 model remap represents, and that any later regenerate-config flow triggers), the wizard reads the ledger and surfaces every row whose re-validation trigger matches as a plain notice — it does not block the change, and it does not silently proceed. The point is only to make the calibration debt visible at the moment it becomes payable; the operator decides whether to re-tune.

**Where the re-validation evidence comes from.** A surfaced row asks a question the operator then has to answer with data. When telemetry export is opted into (TEL-01), `.claude/steering/telemetry.md` names the redaction-clean Claude Code events that supply that data: the **Subagent token multipliers** row is re-derived from `claude_code.token.usage` sliced by `agent.name` / `query_source`; the **Drift thresholds** row is checked against `claude_code.compaction` (`trigger`, `pre_tokens`, `post_tokens`). Without telemetry the operator re-tunes by hand as before — the ledger stands on its own; telemetry only turns "re-check this" into a query.

The ledger **links** to the sections that own each default (§6.E, *Drift detector specifics*, for drift thresholds; Phase 9.5 for max-iterations and the token-multiplier note) rather than restating their values as a second authority; the owning section stays the source of truth. Adding a row is the right move whenever a new default is introduced because a current model needs it — that is what keeps the staleness class from going invisible again.

---

<a id="phase-0"></a>
## Phase 0 — Preflight & Classification

**Goal:** Confirm what the operator has, audit the environment, classify the project (or capture dimensions for "Other"), decide the PRD tier, and preview what will be built.

**AI actions:**
1. **Environment audit (do this first):**
   - **Confirm working directory is the project root.** Look for indicators: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `README.md` at this level, or an existing `.git/`. If none of these are present at the current path but exist in a parent directory, **stop and ask** the operator: "Current directory looks like it's inside a project, not at the root. Bootstrap should run at the root. cd to <suggested-path>?" Do not proceed until the operator confirms.
   - Check if `.claude/` directory already exists. If yes, read `.claude/.bootstrap-state.json` if present. If state shows a previous incomplete or complete bootstrap, **stop and ask** the operator: "Existing `.claude/` found. Resume / overwrite (with backup) / cancel?" Never silently overwrite.
   - Check if `.git/` exists. If no, ask the operator whether to run `git init` first or proceed without version control. Many phases assume git (worktree isolation, hooks on commit, branch model). Without git, mark these phases as degraded and inform the operator. **If the operator chooses to run `git init`, the AI runs it, then re-audits the environment** before continuing — `.git/` existence affects later phase behavior.
   - Check if `docs/prd/` exists. If yes, list any PRDs found.
   - Detect language and framework if existing code is present. **Cite the files you read** to make the determination.
2. Ask the operator:
   - Project name and one-sentence description.
   - PRD status: *(have one / have notes / just an idea)*
   - If PRD exists, ask for the path and read it. Confirm the PRD reflects current intent — ask: "Has anything changed since this was written?"
3. Propose an archetype based on description + any existing code. Show the matrix above. Operator confirms or picks a different one.
4. **If operator picks "Other"** (or no listed archetype fits), run the dimension interview:
   - **Distribution:** binary download / package registry / hosted service / app store / browser store / embedded / other.
   - **Has user-facing UI?** *(yes — web / yes — native / yes — terminal / no — headless)*
   - **Has persistent state?** *(yes — owned DB / yes — external store / no — stateless)*
   - **Has authentication?** *(yes — user auth / yes — service auth / no)*
   - **Deployment model:** continuous deploy / release-tagged / submitted-for-review / installed-locally / embedded.
   - **Test surface:** unit + integration / unit only / behavior-based (E2E heavy) / eval-based (AI) / hardware-in-loop / other.
   - **Critical concerns** (multi-select): performance, security, reproducibility, privacy, cost, accessibility, regulatory compliance, real-time/latency.
   Build a **synthetic archetype profile** for this project. The profile is a structured object the AI writes into `.bootstrap-state.json` with this exact shape:
   ```json
   {
     "synthetic_profile": {
       "distribution": "binary_download",
       "ui": "terminal",
       "state": "stateless",
       "auth": "none",
       "deployment": "release_tagged",
       "test_surface": "unit_integration",
       "critical_concerns": ["performance", "reproducibility"],
       "closest_archetype": "cli_tool",
       "modifications": ["adds: library_semver_discipline"],
       "phase_overrides": {
         "phase_5_cicd": "release_only",
         "phase_6_hooks": ["spec_gate", "test_gate", "lint_gate", "drift_detector"]
       }
     }
   }
   ```
   Each subsequent phase reads this profile and adapts its questions accordingly. Show the operator the profile and proposed phase plan before proceeding.
5. **Decide CI/CD applicability** (after archetype is set in step 3 or step 4): ask explicitly: "Does this project have CI/CD pipelines, or will it (within 3 months)?" If no, mark Phase 5 as **opt-out** (Phase 5 will still produce a minimal `ci-cd.md` recording "no CI/CD" as an explicit decision plus the test command, but skip pipeline configuration). *Why ask now:* CI/CD applicability affects which hooks make sense in Phase 6 (the CI mirror hook is irrelevant without CI) and which questions Phase 5 asks, so deciding here lets later phases adapt without backtracking.
6. **Surface skippable-phase decisions.** For each phase marked skippable in the Skip Policy, ask the operator: "Run / skip / decide later?" The phases and their defaults:
   - **2.7 (Secrets)** — run unless the operator confirms no secrets at all.
   - **6.5 (Tools/MCP)** — run.
   - **7.5 (Spec Versioning)** — run unless solo + short-lived project.
   - **7.6 (Spec Roster Derivation)** — run unless the operator confirms the PRD is too rough to enumerate deliverables (the wizard does not skip on its own).
   - **9 (Smoke Test)** — ask at Phase 9.
   - **9.5 (Autonomous Loop Mode)** — **default skip** (opt-in only — for greenfield projects, the wizard recommends deferring this until 5–10 tasks have shipped operator-in-the-loop, so the project's conventions and test infrastructure exist before the agent runs unattended).
   - **9.6 (Goal-Supervised Mode)** — **default skip** (opt-in only — independent of 9.5; for greenfield projects, the wizard recommends deferring this until 10–20 tasks have shipped operator-in-the-loop so the sixth criterion and recommendation rule can be calibrated against real evidence).
   - **9.7 (Autonomous Queue Mode)** — **default skip** (opt-in only — requires at least one of 9.5 or 9.6 to be enabled, and strongly recommends at least 4 weeks of real operating time on the per-task mechanisms before enabling — queue mode amplifies every per-task failure mode by the number of tasks it runs unattended).
   - **Telemetry export (`telemetry_export_enabled`)** — **default skip** (opt-in only — independent of every autonomous mode; enabling it emits `.claude/steering/telemetry.md` and records one state flag, and changes no gate, wire, or runtime behavior).

   **Question phrasing for telemetry export (use verbatim):** *"Enable observability export? This writes a steering doc, `telemetry.md`, that documents Claude Code's own opt-in OpenTelemetry surface and points it at a backend you run. It's how you'd later see whether the gates, drift thresholds, and autonomous loops are behaving — gate fire rates, compaction behavior, infra-failure rates, and per-subagent token usage — as trends over time. Nothing is sent anywhere the protocol chooses: export goes only to the OTLP endpoint you configure, never to Anthropic and never to the Bootstrap maintainers, and prompts, tool arguments, file contents, and API bodies stay redacted unless you deliberately turn them on against your own backend. Off by default; you can enable it any time later."*

   **Decision independence and gating:** The 9.5 and 9.6 decisions are independent — all four combinations (neither / loop only / goal-supervised only / both) are valid. The 9.7 decision is gated on the other two — if both 9.5 and 9.6 are skipped, **do not offer 9.7** and explain that queue mode requires at least one per-task mechanism to dispatch.

   **Question phrasing for 9.6 (use verbatim):** *"Enable goal-supervised mode? This adds a small-model judge (Haiku by default) that checks the agent's work as an advisory signal, on top of the deterministic gates. It's a middle tier: more autonomy than operator-only, less than full loop mode. Use it for tasks you can state in one sentence but don't fully trust to tests — the blast radius is wider, rollback is harder, or 'done' has a judgment call the tests don't catch. Cost: a small per-iteration charge, in the noise. New failure mode: persistent evaluator-disagreement — the judge and the agent can keep disagreeing, and you review those cases when they fire."*

   **Question phrasing for 9.7 (use verbatim):** *"Enable autonomous queue mode? This runs your pre-classified tasks back-to-back, unattended, for as long as you set — minutes, hours, or days. The runner is just a coordinator with no agent context of its own: it dispatches the per-task wrappers you already have and watches how each one ends. Requires at least one per-task mechanism enabled (loop mode or goal-supervised mode). New failure mode: three-consecutive-halts queue termination — if three tasks halt in a row, the queue stops itself; that's a signal about the queue, not any one task. Recommended only after the per-task mechanisms have run for at least four weeks of real use."*

   **Refusal condition for 9.7:** If `loop_mode_enabled: false` AND `goal_supervised_mode_enabled: false`, do not offer queue mode; explain that queue mode requires at least one per-task mechanism.

   **Trust ramp surfacing on 9.7 opt-in:** If the operator opts into 9.7, immediately surface the trust ramp before continuing: *"Autonomous queue mode requires a multi-week trust ramp. The wizard generates the runner now, but do not run it overnight on the first week. The recommended sequence is in the Phase 10 handoff and Phase 9.7 documentation; review it before first use."*

   **State file recording:** Record decisions in `.bootstrap-state.json`. The 9.5 decision is also written as the top-level `loop_mode_enabled` flag; the 9.6 decision is written as `goal_supervised_mode_enabled`; the 9.7 decision is written as `queue_mode_enabled`; the telemetry decision is written as the top-level `telemetry_export_enabled` flag (default `false`); the 7.6 decision is recorded under `skippable_phase_decisions.phase_7_6_spec_roster`. These decisions feed Phase 0.5's preview so the operator sees the actual scope before committing.
7. Based on archetype (or synthetic profile), propose the required PRD tier. Operator can request a higher tier but not a lower one.
8. Branch on PRD status:
   - **Has PRD at correct tier** → proceed to Phase 0.5.
   - **Has PRD below required tier** → run a gap interview to upgrade it, write the upgraded PRD to `docs/prd/<name>.md`, then proceed to Phase 0.5.
   - **Has notes or just an idea** → run the appropriate-tier PRD interview, write `docs/prd/<name>.md`, get confirmation, then proceed to Phase 0.5.
9. Write `.claude/.bootstrap-state.json` with the classification, synthetic profile if applicable, CI/CD opt-out flag, skippable-phase decisions (including `loop_mode_enabled`, `goal_supervised_mode_enabled`, and `queue_mode_enabled`), `bootstrap_protocol_version: "2.0.1"` (always — this is the version of the protocol document being run), `gate_substrate: "shell"` (records the installed enforcement substrate independently of the document version — see the v2.0.0 conformance note; becomes `"sdk-callable"` only when the SDK gate migration is applied), `loop_in_flight: []` (initially empty; populated by `loop.sh` only when loop mode is opted into and a loop runs), `goal_in_flight: []` (initially empty; populated by `goal-loop.sh` only when goal-supervised mode is opted into and a loop runs), `queue_runs_history: []` (initially empty; appended to by `auto.sh` only when queue mode is opted into and a queue runs), and environment audit results.

**Exit criteria:** Environment audited (no surprise overwrite, working at project root, git status known, PRD currency confirmed). Archetype classified (or synthetic profile captured for "Other"). PRD exists at the required tier. CI/CD applicability and skippable-phase decisions made. State file written. Operator has confirmed all of the above.

---

<a id="phase-0-5"></a>
## Phase 0.5 — Preview & Commitment

**Goal:** Show the operator exactly what the bootstrap will produce, so they can commit (or back out) before any artifact is written.

**AI actions:**
1. Based on the archetype (or synthetic profile), CI/CD opt-out flag, and skippable-phase decisions (including `loop_mode_enabled`, `goal_supervised_mode_enabled`, and `queue_mode_enabled`), build a preview:
   - List every file that will be created (steering docs, hook scripts, skill files, agent definitions, command files, learnings/sessions/specs READMEs). **If loop mode is opted into,** the preview also lists `.claude/loop.sh`, `.claude/loop-config.md`, the drift-detector cooperation hook script, and notes that `spec-decompose`, `CLAUDE.md`, and the implementer subagent definition will gain loop-mode-aware additions (the reviewer subagent is **not** modified — it remains part of the deterministic gate). **If goal-supervised mode is opted into,** the preview additionally lists `.claude/goal-loop.sh`, `.claude/goal-config.md`, the iteration-summary enforcement hook script, `learnings/mode-selection.md` (the calibration ledger), and notes that `spec-decompose`, `CLAUDE.md`, and the implementer subagent definition will gain goal-supervised-mode-aware additions (the reviewer subagent is **not** modified — it remains part of the deterministic gate). If both modes are opted into, the drift-detector cooperation hook is generated once and recognizes both `.loop-active-*` and `.goal-active-*` markers. **If queue mode is opted into,** the preview additionally lists `.claude/auto.sh` (the runner), `.claude/auto-config.md` (runner configuration), the `.claude/queue/` directory with an empty `backlog.md` skeleton, and notes that `spec-decompose` will gain a queue-population step (priority, ready/operator-only/deferred section, `blocked_by` field) for each task confirmed by the operator. The runner contains **no agent context** — it is a bash orchestrator that invokes the per-task wrappers — so `CLAUDE.md` gains no new conditional behavioral addendum for queue mode (it gains only a brief informational reference to queue mode as a coordination layer; see Phase 8). **If telemetry export is opted into,** the preview additionally lists `.claude/steering/telemetry.md` (committed, operator-facing) and notes that it documents Claude Code's native opt-in OpenTelemetry surface pointed at an operator-owned backend; no hook, gate, wire, or runtime behavior changes, and the protocol transmits nothing itself.
   - **Rough estimate** of token-budget impact (loosely: how much context will steering + CLAUDE.md consume on cold start). The estimate is approximate — the AI hasn't written the files yet — but should be order-of-magnitude correct (e.g., "~5–8K tokens for steering + ~2–3K for CLAUDE.md"). The loop-mode CLAUDE.md addendum adds roughly 200–400 tokens to cold-start cost; the goal-supervised-mode CLAUDE.md addendum adds a similar 200–400 tokens. Both addenda load conditionally on the relevant sentinel and do not stack at runtime (a task is in at most one mode). The queue-mode reference in CLAUDE.md (if any) adds at most ~50 tokens; the runner itself does not load CLAUDE.md.
   - Estimate remaining wizard time based on archetype and active phases. Loop mode adds roughly 15–25 minutes for Phase 9.5 if opted into; goal-supervised mode adds roughly 10–15 minutes for Phase 9.6 if opted into; queue mode adds roughly 15–20 minutes for Phase 9.7 if opted into. Opting into all three adds all three increments.
2. Ask: **proceed / adjust scope / cancel.**
   - "Adjust scope" returns to Phase 0 to revisit skippable-phase decisions.
   - "Cancel" exits cleanly with no files written (other than the in-progress state file, which is removed).
3. If proceed, mark Phase 0.5 complete in state file.

**Exit criteria:** Operator has seen the preview and confirmed the scope of what will be built.

---

<a id="phase-1"></a>
## Phase 1 — Product Steering (`product.md`)

**Goal:** Distill the PRD into a steering doc every future subagent reads.

**AI actions:**
1. Read the PRD.
2. Confirm or correct with the operator:
   - Primary user persona.
   - Single most important problem this solves.
   - Success metric.
   - Out-of-scope list.
3. Write `.claude/steering/product.md`. Two pages maximum regardless of PRD size — this is a distillation, not a copy.
4. Show the file and ask: **approve / edit / start over**.

**Exit criteria:** `product.md` exists and is approved.

---

<a id="phase-2"></a>
## Phase 2 — Technical Steering (`tech.md`)

**Goal:** Lock in stack, conventions, and "do not touch" boundaries.

**Archetype-aware questions:**
- All archetypes: language, package manager, test framework, linter, formatter, logging, error handling, naming conventions, **documentation policy** (where docs live, who updates README, how changelogs work), "do not touch" list.
- **CLI tool:** binary distribution mechanism, version flagging, error exit codes.
- **Library / SDK:** semver discipline, public API surface, breaking change policy, supported runtime versions.
- **Service / API:** auth approach, rate limiting, request/response schema validation, observability (metrics, traces, error monitoring tool).
- **Full-stack app:** all of the service questions plus frontend stack, state management, styling approach, accessibility baseline, error monitoring tool.
- **Mobile app:** platform versions supported, build signing, native module policy, offline behavior, crash reporting tool.
- **Data / ML pipeline:** data access controls, dataset versioning, reproducibility (seeds, environment pinning), pipeline orchestration tool, lineage tracking.
- **AI / agent system:** model provider(s), prompt versioning, context budget per call, eval harness location, cost tracking mechanism, fallback behavior, prompt + output logging.
- **Other:** the AI uses the synthetic profile from Phase 0 to pick the most relevant subset of the above and asks accordingly.

**AI actions:**
1. If codebase exists, scan and propose detected stack. Cite the files you read. Ask operator to confirm.
2. If greenfield, ask archetype-appropriate questions only.
3. Always ask the "do not touch" question explicitly. Default suggestions vary by archetype (auth/payment/migrations for full-stack; public API surface for libraries; prompt files for AI systems; secrets handling and infrastructure-as-code for all).
4. Write `.claude/steering/tech.md` with explicit `## Do Not Touch` and `## Documentation Policy` sections.
5. Show and ask: **approve / edit / start over**.

**Exit criteria:** `tech.md` exists. The "do not touch" list is explicit and approved.

---

<a id="phase-2-5"></a>
## Phase 2.5 — Dependency Policy (`deps.md`)

**Goal:** Define what dependencies are allowed, who can add new ones, and how they're vetted. This is the policy the dependency hook in Phase 6 enforces against.

**Skipped if** the project has no external dependencies (rare — mostly applies to scripts using only the standard library).

**AI actions:**
1. If codebase exists, scan the manifest (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.) and propose the existing dependencies as the initial approved list.
2. Ask the operator:
   - **Approval policy:** allowlist (only listed deps allowed), denylist (most allowed except listed), or hybrid (allowlist for production, allowlist+confirm for dev)?
   - **Vetting criteria:** minimum maintenance signal (last commit, weekly downloads), license restrictions, security scan requirement, supply-chain considerations.
   - **Who approves new dependencies:** the operator in-session, a designated reviewer, automated checks only?
   - **Pinning strategy:** exact versions, caret ranges, or tilde ranges? Lockfile committed?
3. Write `.claude/steering/deps.md` with: the current approved list with version constraints, vetting criteria as a checklist, approval flow, and pinning/update cadence.
4. Show and ask: **approve / edit / start over**.

**Exit criteria:** `deps.md` exists with an explicit approved list and an approval flow. The dependency hook in Phase 6 will reference this file.

---

<a id="phase-2-7"></a>
## Phase 2.7 — Secrets & Sensitive Data Policy (`secrets.md`)

**Goal:** Define how secrets and sensitive data are handled, so the AI does not accidentally read, log, or commit them.

**Skipped only if** the project handles no secrets, no PII, and no sensitive data of any kind. Operator must explicitly confirm to skip.

**AI actions:**
1. Ask the operator:
   - **Where do secrets live in development?** *(`.env` file gitignored / OS keychain / dev secrets manager / 1Password / other)*
   - **Where do secrets live in production?** *(env vars / cloud secrets manager / vault / other)*
   - **Files the AI must never read:** typically `.env*`, `secrets/**`, `*.pem`, `*.key`, anything matching credential patterns.
   - **PII / sensitive data classification:** what data types (if any) require special handling?
   - **What does the AI do if it encounters a secret in code?** Default: stop, alert operator, do not include in any output, recommend rotation.
2. Write `.claude/steering/secrets.md` with: never-read paths, secret-detection patterns, AI behavior on encounter, rotation policy summary.
3. Add the never-read paths to the **secrets gate** hook (separate from spec gate per the v1.2.0 split). The secrets gate blocks Read/Write/Edit on these paths in Phase 6.
4. Show and ask: **approve / edit / start over**.

**Exit criteria:** `secrets.md` exists. Never-read paths are flagged for hook integration.

---

<a id="phase-3"></a>
## Phase 3 — Structure Steering (`structure.md`)

**Goal:** Define where things live so agents stop inventing file locations.

**AI actions:**
1. If codebase exists, propose existing structure as baseline.
2. If greenfield, propose a structure based on archetype + stack (or synthetic profile for "Other"). Common templates: Next.js monorepo, Django project, Python package with `src/` layout, Go module layout, Flutter app, browser extension MV3, etc.
3. Confirm with operator: shared code location, test location relative to source, monorepo vs polyrepo, generated files policy, where docs live.
4. Write `.claude/steering/structure.md` with directory tree and one-line description per top-level directory.
5. Show and ask: **approve / edit / start over**.

**Exit criteria:** `structure.md` exists and matches what's on disk (or what will be).

---

<a id="phase-4"></a>
## Phase 4 — Principles Steering (`principles.md`)

**Goal:** Define 3–5 ranked, project-specific coding principles that resolve real tradeoffs.

**AI actions:**
1. Explain to the operator that generic principles (DRY, SOLID, KISS, YAGNI) are noise without project-specific rules and ranking.
2. Propose a starter set based on archetype:
   - **CLI tool:** "Predictable behavior over feature breadth," "clear error messages over recovery cleverness," "YAGNI before flag proliferation."
   - **Library / SDK:** "API stability over internal cleanliness," "explicit over magical," "YAGNI before abstraction."
   - **Service / API:** "Clear errors over silent fallbacks," "explicit schemas over duck typing," "instrument before optimize."
   - **Full-stack app:** "User-visible correctness over code elegance," "YAGNI before the third duplication," "tests describe intent."
   - **Mobile app:** "Offline-first where possible," "user-perceived performance over benchmark performance," "platform conventions over cross-platform purity."
   - **Data / ML pipeline:** "Reproducibility over speed," "explicit data contracts," "fail loud on schema drift."
   - **AI / agent system:** "Determinism where possible," "evals before refactors," "cost-awareness in every call."
   - **Platform / multi-component:** "Component independence over shared abstractions," "explicit interfaces between components," "YAGNI for cross-component features."
   - **Other:** the AI proposes 3–5 principles derived from the synthetic profile's "critical concerns" multi-select.
3. For each principle, write a project-specific rule that translates it into action — what to *do* when the principle applies, not just the acronym.
4. Ask the operator to add or override.
5. **Define explicit tiebreakers** for principles in tension (e.g., "DRY vs YAGNI: prefer YAGNI until the third duplication").
6. Decide TDD policy: required, encouraged, or off. If required, a hook will enforce it in Phase 6.
7. Write `.claude/steering/principles.md` with the ranked list, project-specific rules, tiebreakers, and TDD decision.
8. Show and ask: **approve / edit / start over**.

**Exit criteria:** `principles.md` exists with 3–5 ranked, actionable rules and explicit tiebreakers.

---

<a id="phase-5"></a>
## Phase 5 — CI/CD Steering (`ci-cd.md`)

**Goal:** Define gates the agent cannot talk its way past.

**Archetype variations:**
- **CLI tool / Library:** simplified to release flow (tag → build → publish to registry), plus PR checks.
- **Service / Full-stack:** full pipeline with environments, deploy triggers, rollback.
- **Mobile:** build signing, beta channel, app store submission flow.
- **Data / ML:** data validation gates, model promotion gates, lineage tracking.
- **AI / agent system:** eval gates before prompt deploy, cost regression checks.
- **Platform / multi-component:** per-component pipelines plus a meta-pipeline for cross-component changes.
- **Other:** derived from the synthetic profile's deployment-model dimension.

**AI actions:**
1. **Check the CI/CD opt-out flag from Phase 0.** If opt-out is set, write a minimal `ci-cd.md` containing: "No CI/CD" as the chosen approach, the test command (so the agent can run it locally), and a placeholder for future addition. Skip steps 2–5 below and go straight to confirmation. Otherwise:
2. Ask archetype-appropriate questions (branch model and CI provider always; environments and deploy flow only when relevant).
3. Optionally include performance budgets / SLO regression gates in the pipeline definition for archetypes where it matters (Service, Full-stack, Mobile, Data/ML).
4. Write `.claude/steering/ci-cd.md`. Make explicit which step is the agent's stopping point — almost always PR open or PR merge, never deploy.
5. **CI config file generation.** If concrete CI config files (e.g., `.github/workflows/*.yml`, `.gitlab-ci.yml`, `bitbucket-pipelines.yml`) don't yet exist, the wizard's preferred path is to generate them in Phase 9 alongside the smoke test, because the smoke test's stage 1 output reveals concrete commands the CI pipeline can mirror. **However**, Phase 9 is skippable. Ask the operator: "Generate CI config files now, or defer to Phase 9?" If the operator chooses defer, record this under `deferred_items.ci_config_generation: "phase_9"` in `.bootstrap-state.json`. The Phase 9 entry handler will detect this; if Phase 9 is also skipped, the wizard surfaces a Phase 10 reminder to generate the CI config manually (or to re-invoke the wizard's Phase 5 setup later). The protocol does not silently lose the CI config generation — it is either done here, in Phase 9, or surfaced at handoff as a remaining task.
6. Show and ask: **approve / edit / start over**.

**Exit criteria:** `ci-cd.md` exists. The agent-vs-human line is unambiguous. CI config file generation is either done, explicitly deferred to Phase 9 (recorded in `deferred_items`), or — for CI/CD-opt-out projects — not applicable.

---

<a id="phase-6"></a>
## Phase 6 — Hooks (`.claude/settings.json` and `.claude/hooks/`)

**Goal:** Install deterministic guardrails.

> **[v2.0.0] Gate substrate migration to the Claude Agent SDK.** The protocol's gates (secrets-gate, spec-gate, eval-gate, tdd-gate, dependency-gate, test-gate, format-lint-gate) are the enforcement layer. In v2.0.0 the preferred substrate for these gates is the Agent SDK's `PreToolUse` hook returning a structured `{permissionDecision: "deny", permissionDecisionReason: <string>}`, expressed as a callable (`HookMatcher`) rather than a shell script wired through `settings.json` matchers. The decisive property, per the official permission-evaluation order: **a `PreToolUse` hook deny runs first and applies even under `bypassPermissions`** — a gate expressed this way cannot be widened by any permission mode, allowlist, or settings merge. This is strictly stronger than matcher-precedence-in-a-merged-settings-tree and deletes a class of shell failure modes (executable bit, shell-profile-noise JSON corruption, `jq` availability, PascalCase matcher gotchas). Migration constraints, locked now:
> - **Retain a minimal shell-hook surface.** The Python Agent SDK does **not** expose `SessionStart`/`SessionEnd` as callbacks (TypeScript-only); in Python these remain shell-command hooks loaded via `setting_sources=["project"]`. The migration is "move the *gates* to callables," not "delete all shell hooks."
> - **Use `PreToolUse`, not `canUseTool`, for must-run checks** — `canUseTool` can be silently shadowed by a bare allow rule or `bypassPermissions` (the SDK warns `CLAUDE_SDK_CAN_USE_TOOL_SHADOWED`). Gates that must run on every call go in `PreToolUse`.
> - **`bypassPermissions` / `acceptEdits` / `auto` are never the dispatch mode.** `bypassPermissions` is the SDK-era successor to the `--bare` prohibition; subagents inherit it non-overridably. Model-classified `auto` mode must never sit in front of a deterministic gate — a gate the *model decides* is not a gate.
> - **Don't put a required audit/flush only in a `Stop` hook** — `max_turns` can end the session before `Stop` fires. Pair with `PreCompact` (archive-before-compact) or a caller-side reconciliation.
> - **Pin a minimum Claude Code runtime** (≥ v2.1.210 for fail-closed `PreToolUse` timeout behavior; earlier versions stall an unattended session on hook timeout). This pin belongs in the seam `binds` set.
>
> **[RESOLVED at 2.1.0]** The reconciliation happened: each gate is re-expressed as an SDK callable in the emitted `.claude/sdk_gates/gates.py` (seam §9 verbatim), and the shell-hook phase below is **retained deliberately** — the shell suite remains emitted in full as the documented SEV-1 manual path and as the operative substrate on any install where the IC gate has not granted `"sdk-callable"`. The shell text below is therefore current normative content, not a staging artifact.

### 6.A — Caveats

- Hooks run per-tool-call, not per-task. Cross-call state (like "did this task modify a test file") requires the hook to read git state or a session-scoped marker file.
- Hooks may not have direct access to model token counts. The "cost log" is implemented as a session-end summary or via a wrapper around tool invocation, not a per-call hook in the strict sense. The AI will note this in the implementation.
- Hooks can be disabled by renaming `.claude/settings.json` to `.disabled` if one misbehaves. This is the recovery path.
- **Don't block file writes mid-plan.** Blocking `Write` or `Edit` during multi-step reasoning breaks Claude's ability to track where it is in a plan. Block at *commit* boundaries (between writes) or use `PostToolUse` for non-blocking validation. The spec gate below is split into entry-warn + commit-block specifically for this reason. The only exception is secrets — those should fail loudly even mid-plan.
- **Use `async: true` for slow hooks.** Hooks block tool execution by default. For checks that take more than a second or two (full lint suites, type-checkers on large codebases, security scans), set `async: true` in the hook config so they run in the background. Released January 2026.

### 6.B — Complementary built-ins worth knowing
- **`claude --permission-mode auto`** — runs with a classifier model reviewing commands before they execute. It blocks scope escalation, unknown infrastructure, and hostile-content-driven actions while letting routine work proceed without prompts. Use this when you want unattended execution for bounded tasks (e.g., "fix all lint errors") without pre-approving every step. Falls back to user prompts if the classifier repeatedly blocks actions, or aborts in non-interactive `-p` mode. **Precedence with hooks:** hooks run regardless of permission mode. If a hook returns exit 2 (block), the tool call is rejected even in auto mode. The classifier is a *supplementary* safety net; hooks are *primary* enforcement. Don't rely on auto mode in place of hooks for anything you care about.
- **Permission allowlists** — explicitly permit specific tool invocations you know are safe (`npm run lint`, `git commit`, etc.) so they don't trigger approval prompts. Configure in `.claude/settings.json` under permission rules. This complements hooks: allowlists reduce friction; hooks enforce policy.
- **Sandboxing** — OS-level isolation that restricts filesystem and network access. Lets Claude work more freely inside a defined boundary. Worth considering for the implementer subagent specifically, where unrestricted file access during implementation is unnecessary.

### 6.C — AI actions: hook installation

**AI actions:**
1. Explain hooks vs skills: hooks are enforced, skills are advisory. Mention the complementary built-ins above as alternatives or supplements where appropriate.
2. Propose the standard set, with archetype-specific additions (for "Other" archetype, hook selection is driven by the synthetic profile's `phase_overrides.phase_6_hooks` array set in Phase 0; the AI proposes those plus any defaults marked "all"):
   - **Spec gate** (all) — split into two hooks to avoid the "block file writes mid-plan" pitfall (blocking mid-plan breaks Claude's multi-step reasoning):
     - **Spec gate (entry)** — `UserPromptSubmit` hook. When the operator's prompt mentions writing/editing files, checks that an active spec exists for the target area. If not, *warns the operator* (does not block) and asks if they want to run `/spec-new` first. This is the friendly upstream check.
     - **Spec gate (commit)** — `PreToolUse` on `Bash` matching `git commit`. Blocks the commit if any file in the diff is not referenced by an active spec in `specs/INDEX.md` or any `tasks/*.md` file. This catches violations at the point where it's safe to block — between writes, not during them.
   - **Secrets gate** (all) — `PreToolUse` on Read/Write/Edit. Blocks any path in `secrets.md` never-read list. Distinct hook from the spec gate (not "split"); kept as its own item because secrets exposure is catastrophic and the model should fail loudly rather than continue. This *does* block mid-plan, which is the deliberate exception to the "don't block mid-plan" rule above.
   - **Test gate** (all) — `PreToolUse` on git commit. Blocks unless the project's test command has been run successfully since the last source-file edit (tracked via a marker file the test runner updates).
   - **Format/lint gate** (all) — `PostToolUse` on Write/Edit. Runs the configured formatter and linter; non-blocking feedback. Use `async: true` if the lint suite is slow (over 2 seconds typical).
   - **CI mirror** (all with CI) — `PreToolUse` on git push. Runs the same checks CI runs locally. Use `async: true` if checks are slow.
   - **Cost log** (all) — session-end summary, not per-call. Appends task ID, total token spend, tool call count to `.claude/logs/cost.jsonl`.
   - **TDD gate** (if Phase 4 enabled it) — `PreToolUse` on Write to a source file. Blocks unless a test file matching the source path was modified more recently (checked via filesystem mtime + git-tracked changes).
   - **Dependency gate** (all) — `PreToolUse` on `Bash` calls matching package-install patterns. Blocks unless the package is on the approved list in `.claude/steering/deps.md` or the operator confirms in-session (which then prompts an update to `deps.md`).
   - **Eval gate** (AI/agent systems) — `PreToolUse` on git push or merge commits touching prompt files. Blocks unless an eval has been run and passed since the prompt was last modified.
   - **Drift detector** (all) — soft notice for tiers 1–2 (does not block); **hard block for tier 3** (denies tool calls). Periodic check on session state: tool-call count since last checkpoint, session duration, repeated file reads. When thresholds cross, emits a desktop notification with an audio chime and an acknowledgement action. Frequency degrades: gentle (tier 1) → insistent (tier 2) → firm + enforced (tier 3). At tier 3 the detector writes a sentinel state file, instructs the agent to produce a `<timestamp>-checkpoint.md`, then hard-blocks every non-checkpoint tool call until the operator runs `/clear`. `/ack-drift` dismisses tiers 1–2 only; tier 3 cannot be acknowledged-and-continued by design. Triggers and thresholds are tunable in `.claude/hooks/audio-alerts.config`. One of three audio alert categories — see section 6.E.
   - **Task-done alarm** (all) — soft notice (does not block). `SubagentStop` hook. Fires when a subagent finishes (implementer commits a task, reviewer returns, integrator resolves). Plays a distinct ascending-tone audio cue and shows a desktop notification: "Task <id> complete. Ready for review." No acknowledgement required; informational. See section 6.E.
   - **Decision-required alarm** (all) — soft notice (does not block). `Notification` hook (Claude Code's built-in event for "input idle" / "permission needed") plus a state-file watcher for explicit escalations. Fires when the AI hits one of the *urgent* escalation criteria from `CLAUDE.md` (do-not-touch file modification, secret encountered, hook block with non-obvious fix, dependency not on approved list, spec turned out to be wrong) and writes to `.claude/sessions/.decision-pending-<session-id>`. Plays a distinct attention-grabbing audio cue and shows a persistent desktop notification (no auto-dismiss) — this is the most important alarm because the AI is literally blocked until the operator responds. Fires once per escalation event (not repeatedly while waiting). Other (non-urgent) escalation criteria — ambiguous criteria, two-approaches tradeoff, spec version drift — get in-chat output only. See section 6.E.
   - **Drift-detector loop cooperation** (only if `loop_mode_enabled` or `goal_supervised_mode_enabled` from Phase 0) — augments the existing tier-3 enforcement with a self-healing exit path. Without this hook, tier 3 hard-blocks until the operator runs `/clear`+`/resume`; with it, when the agent is running inside `loop.sh` *or* `goal-loop.sh`, the same tier-3 fire causes the agent to write the standard checkpoint and then end its turn (i.e., stop emitting tool calls). The wrapper sees `claude -p` exit, finds the tier-3 sentinel and the just-written checkpoint, and primes the next iteration with the new checkpoint instead of the original task brief. **Does not weaken tier 3 outside loop/goal-supervised mode** — the hook checks for `.claude/sessions/.loop-active-<task-id>` *or* `.claude/sessions/.goal-active-<task-id>` before changing behavior; absent either marker, tier 3 behaves exactly as documented in section 6.D. Generated only if Phase 9.5 or Phase 9.6 is opted into; the same hook serves both modes (the transformation behavior is identical). See Phase 9.5 and Phase 9.6 for the per-mode cooperation contracts.
   - **Iteration-summary enforcement** (only if `goal_supervised_mode_enabled` from Phase 0) — invoked by `goal-loop.sh` after `claude -p` exits, before judge invocation. Checks for the presence and format-validity of `.claude/sessions/.iteration-summary-<task-id>-<iter-n>.md` (the required structured format is specified in Phase 9.6). If the file is missing or malformed, the hook writes a structured error to the next iteration's priming context and increments a `summary_failure_count` counter; three consecutive format failures count as a `goal-condition-suspect`-class halt (parallel to the persistent-evaluator-disagreement halt). The hook runs the same security & correctness checklist as every other hook (no `eval`, quoted paths, exit codes, executable bit set, `jq` available where required). Generated only if Phase 9.6 is opted into.
3. For each accepted hook, write the script under `.claude/hooks/<hook-name>.sh` (or `.py`). **Show the script content to the operator before writing it** — these are security-relevant. Run the security checklist below before approval.
4. Wire each hook into `.claude/settings.json` with the correct trigger event.
5. Test each hook by triggering it with a known-good and known-bad input. Show the operator the block message format.
6. Show and ask: **approve / edit / start over**.

### 6.D — Hook security & correctness checklist

**Hook script security & correctness checklist** (the AI runs through this for every hook script before showing it to the operator):

*Security:*
- ✅ No `eval` or dynamic code execution from variables.
- ✅ No `curl | bash` or piped-execution patterns.
- ✅ All file paths are quoted to prevent space/special-character injection.
- ✅ All variables expanded from tool input are validated (type, length, character class) before use.
- ✅ No hardcoded credentials or tokens.
- ✅ Network calls (if any) go to allowlisted domains only, with timeouts.
- ✅ Hook script files have appropriate permissions (`chmod 700` on the hooks directory).
- ✅ Hooks log to `.claude/logs/hooks.log` for audit; logs do not include sensitive content.
- ✅ Exit codes follow convention (0 / 1 / 2 — see below).

*Correctness (real-world hook failure modes):*
- ✅ **Executable bit set** — `chmod +x .claude/hooks/<script>.sh`. Hooks fail silently if not executable.
- ✅ **`jq` available** — most hooks parse JSON input from Claude Code. Confirm `jq` is installed (`brew install jq` / `apt-get install jq`); fall back to Python's `json` module if not.
- ✅ **Shell profile noise guarded** — if the hook script sources `.bashrc` or `.zshrc` (directly or indirectly), and those profiles print "Welcome!" or other interactive output, the hook's JSON output gets corrupted. Either run hooks with a clean shell (`#!/usr/bin/env -i bash`) or wrap interactive output in profiles: `if [[ $- == *i* ]]; then echo "Welcome!"; fi`.
- ✅ **Stop hooks check `stop_hook_active`** — Stop and SubagentStop hooks can loop infinitely if they don't check this flag. First line of every Stop hook: `if [ "$(echo "$INPUT" | jq -r '.stop_hook_active')" = "true" ]; then exit 0; fi`.
- ✅ **Matcher case-sensitive** — tool name matchers in `settings.json` are case-sensitive. `Bash` matches; `bash` does not. Tool names are PascalCase.
- ✅ **Correct event chosen** — verify the chosen event fires under the conditions you expect. In particular, check against the current Claude Code hooks reference whether `PostToolUse` fires on tool failures (some versions deliver the failure in the response payload; others gate `PostToolUse` to success only and expose failures through a separate event). Don't put failure-handling logic in `PostToolUse` without confirming the version-specific behavior.
- ✅ **Concurrent-safe state reads/writes** — any hook that reads or modifies `.claude/.bootstrap-state.json`, a per-task active sentinel, or the queue file must use the same race-safe idioms the wrappers use: `O_CREAT|O_EXCL` for sentinel creation, `flock` plus tmpfile-then-rename for state-file updates. See Phase 9.5's "Race-safety summary" for the canonical mechanism. Hooks that violate this corrupt state in ways that surface as "the wrapper randomly forgot about a task."
- ✅ **Tested with `/hooks`** — after writing the script, run `/hooks` in Claude Code to verify the hook is loaded and matchers resolve correctly.

### 6.E — Audio alert system

The audio alert system covers three distinct alarm categories, each with its own sound, urgency level, and frequency policy. Shared infrastructure (notification dispatch, sound file management, mute/quiet mode, OS detection) lives here so the categories don't reinvent it independently.

**Three categories at a glance:**

| Category | Trigger | Urgency | Frequency | Acknowledgement |
|---|---|---|---|---|
| **Drift detector** | Context degradation proxies cross thresholds | Soft for tiers 1–2 (advisory); **hard for tier 3** (operator is blocked) | Degrading: gentle → insistent → firm + enforced | Required for tiers 1–2 (action button or `/ack-drift`); tier 3 cleared only by checkpoint + `/clear` |
| **Task done** | Subagent completes (`SubagentStop` event) | Soft (informational) | Every completion | Not required |
| **Decision required** | AI hits an *urgent* escalation criterion (do-not-touch, secret, hook block, dependency, spec-wrong) | Hard (operator is blocked) | Once per escalation event | Implicit: resolved when operator responds |

**Audio principles:**
- **Distinguishability beats novelty.** The three sounds must be unambiguously different from each other and from system sounds the operator hears regularly (Slack, email, calendar). Use short tonal melodies, not single beeps.
- **Recommended sound shapes:**
  - Drift gentle / insistent / firm — three escalating chimes (existing).
  - Task done — three notes ascending (resolution feeling: "completed, ready").
  - Decision required — three notes descending then ascending, slightly longer, slightly louder (attention feeling: "stop, look here").
- **Decision-required is the most attention-grabbing.** It uses a persistent notification (no auto-dismiss) because the AI is genuinely blocked. The other two auto-dismiss after a few seconds.

#### Shared infrastructure

**Session identity:** each session generates a session ID at first hook invocation, stored at `.claude/sessions/.session-<id>` with start timestamp. State files for all alert categories (`.drift-ack-<id>`, `.drift-state-<id>`, `.drift-tier3-<id>`, `.decision-pending-<id>`, `.quiet-<id>`) are namespaced by session ID. On `/clear` or new conversation start, a new session ID is generated and old state files older than 7 days are purged.

**OS-specific dispatch (configured per-OS by the AI):**
- **Linux with notification daemon supporting actions** (Hyprland with `dunst`, GNOME with `gnome-shell`, KDE with `plasma-workspace`): use **`dunstify`** (not vanilla `notify-send` — vanilla doesn't return action results) with action buttons + `paplay` or `pw-play` for audio.
- **Linux fallback** (no action-supporting daemon): plain `notify-send` notification + `paplay` audio + in-chat message asking operator to type `/ack-drift` (drift only).
- **macOS:** `osascript -e 'display notification ... with sound'` for the alert. Action acknowledgement via in-chat slash command (AppleScript dialogs block hook execution; in-chat is cleaner).
- **Windows:** PowerShell `New-BurntToastNotification` with action button + `[Console]::Beep`. Requires `BurntToast` module installed.
- **Headless / SSH / fallback:** in-chat message only. Operator types `/ack-drift` to acknowledge drift; decision-required uses in-chat persistent message until resolved.

The Phase 6 wizard detects the OS and notification daemon (e.g., `pgrep dunst` to confirm dunst is running) and generates the appropriate hook scripts. If detection fails, defaults to in-chat fallback for all categories.

**Sound files:** Phase 6 creates `~/.claude/sounds/` if it doesn't exist and either copies bundled defaults (if the bootstrap is run from a directory containing them) or generates simple tonal sequences with `sox` / `ffmpeg` if available. If neither is available, audio is disabled per category and the operator is told they can drop their own WAVs in later. Hooks are robust to missing sound files (log warning, continue without audio). The wizard generates these defaults:
- `~/.claude/sounds/drift-gentle.wav`
- `~/.claude/sounds/drift-insistent.wav`
- `~/.claude/sounds/drift-firm.wav`
- `~/.claude/sounds/task-done.wav`
- `~/.claude/sounds/decision-required.wav`

**Quiet mode (mute):** the operator can silence all audio cues without disabling the hooks themselves. Two mechanisms:
- `/quiet on` slash command — mutes audio for the session. `/quiet off` re-enables. Persists to `.claude/sessions/.quiet-<id>`.
- `~/.claude/quiet-until` file with an ISO-8601 timestamp — mutes audio until that time. Useful for "no audio for 2 hours of focus work." Created via `/quiet 2h` slash command.

When quiet mode is active, notifications still fire (visual only); only audio is suppressed. Decision-required alarms ignore quiet mode after their first attempt — if the AI is blocked, the operator needs to know, even if they asked for quiet.

**Hook exit codes (all hooks, not just audio alerts):**
- Exit 0: success, allow the tool call to proceed.
- Exit 1: error in the hook itself (logged, tool call proceeds — don't block on hook bugs).
- Exit 2: blocking decision; the tool call is rejected with the hook's stderr as the reason.
- All audio alert hooks always return exit 0 (soft notice).

#### Drift detector specifics

The drift detector is a soft notice hook for tiers 1–2 and an enforcing hook at tier 3. It runs on every tool call (hooks have no built-in timer; "periodic" means "checked every time a tool is invoked"). The goal is to flag context degradation early without becoming wallpaper, and to *force* a checkpoint when the situation has progressed past the point where continuing in the same session is responsible.

**Honest constraint:** Claude Code hooks **do not have direct access to context window utilization**. The detector uses **proxy signals only** (tool count, duration, repeated reads). Operator can run `/context` manually for actual utilization, but the hook cannot. The "70% threshold" mentioned in alerts is operator-facing language for the proxies, not a real percentage. Be straight about this in the script comments.

**Triggers (any one fires the alert, evaluated on every tool call):**
- Tool call count since last checkpoint exceeds threshold (default 50 calls).
- Session duration exceeds threshold (default 120 minutes of continuous work, measured from session start file timestamp).
- Same file read more than threshold times in current session (default 3 — suggests confusion or repeated exploration).

*Note:* an earlier version of this protocol listed "plan revisions" as a trigger. That signal is **not feasible** from a parent-session hook because subagents have isolated contexts and their plan changes don't surface to the parent. If plan-revision detection is desired, it must be implemented inside the implementer subagent's prompt as a self-reporting mechanism. Out of scope for default drift detector.

**Degrading frequency:**
- **Alert 1 (gentle):** soft chime, brief notification, message in chat: "Drift signals: [list specific triggers]. Consider `/checkpoint` and `/clear` when convenient."
- **Alert 2 (insistent, fires only if signals are still active and ≥10 minutes since Alert 1):** louder chime, persistent notification: "Drift indicators worsening. Recommend checkpoint now."
- **Alert 3 (firm + enforced, fires only if signals are still active and ≥15 minutes since Alert 2):** alarm-style chime, persistent notification (overrides quiet mode). **Tier 3 is enforced, not advisory.** It runs in two phases:
  - **Phase A — checkpoint demand:** the drift detector writes the sentinel state file `.claude/sessions/.drift-tier3-<session-id>` and denies the current tool call with stderr message: *"Tier 3 drift fired. Quality is likely degrading. Before continuing, write `.claude/sessions/<timestamp>-checkpoint.md` with the standard checkpoint synopsis (current task and spec ID, completed work this session, in-flight changes, files touched, key decisions, open questions, state of tests, next steps). After writing the checkpoint, the operator must run `/clear` to reset context, then `/resume`."* The agent's next action should be the checkpoint write. **Ordering matters: the operator should not run `/clear` until the agent has written the checkpoint, otherwise the checkpoint is lost.** The agent's responsibility is to produce the checkpoint promptly so the operator can clear with confidence.
  - **Phase B — hard block:** while the sentinel exists, every subsequent tool call is denied. The single exception is `Write` tool calls whose target path matches `.claude/sessions/*-checkpoint.md` — these are allowed so the agent can complete the checkpoint if Phase A's write was interrupted. All other tool calls receive deny + stderr message: *"Tier 3 drift active. Run `/clear` to reset, then `/resume` to continue."*
- **Sentinel cleanup:** the `.drift-tier3-<session-id>` file is removed automatically when the session ends (covered by the existing 7-day state purge) or when a new session starts post-`/clear` (different session ID). The operator can also remove it manually if they need to override (not recommended; the file is named with the session ID precisely so removing it is a deliberate, traceable act).
- **Acknowledgement is unavailable at tier 3.** `/ack-drift` returns: *"Tier 3 cannot be acknowledged. Write a checkpoint and run `/clear`."* This is by design — the protocol exists because operator self-override at saturated context is the failure mode.
- **Tier 3 inside an autonomous mode (only if Phase 9.5 or Phase 9.6 was opted into):** when the drift-detector loop-cooperation hook is installed and either `.claude/sessions/.loop-active-<task-id>` or `.claude/sessions/.goal-active-<task-id>` exists, tier 3 becomes a *self-healing context reset* rather than an *operator-required checkpoint*. Phase A is unchanged (sentinel written, agent instructed to write the checkpoint). Phase B is unchanged in semantics (hard-block on non-checkpoint tool calls), with the additional instruction that the loop-mode-aware or goal-supervised-mode-aware agent prompt directs the agent to **end its turn after the checkpoint write completes** — no further tool calls, no waiting for the operator. The wrapper (`loop.sh` or `goal-loop.sh`) sees `claude -p` exit, inspects sentinels, and — finding the tier-3 sentinel and a fresh checkpoint — primes the next iteration with the new checkpoint as context. The new session has a new session ID, so the old `.drift-tier3-<old-session-id>` sentinel no longer matches and tool calls flow normally in the fresh session. The operator still gets the checkpoint file for post-hoc review but does not need to be present for the reset. **Tier 3 enforcement is augmented, not weakened** — the operator-only path still works exactly as documented above outside autonomous modes, and inside either autonomous mode the same hard-block, the same checkpoint requirement, and the same blast-door semantics all apply. The only thing that changes is who runs `/clear`+`/resume`: the wrapper does, by starting a fresh session. Behavior is identical between loop mode and goal-supervised mode for the tier-3 cooperation path; the cooperation hook recognizes either marker.

**Acknowledgement mechanism (tiers 1–2 only):**
- Clicking the notification action button (Linux/Windows where supported) writes a timestamp to `.claude/sessions/.drift-ack-<session-id>`.
- Or the operator types `/ack-drift` (a slash command added in Phase 7) which writes the same.
- The drift detector reads this file at the start of each check; recent ack means skip until next session or until thresholds spike again significantly (default: re-fire if tool count grows by another 50% beyond the threshold).
- **Tier 3 cannot be acknowledged through this mechanism** — see Alert 3 above. `/ack-drift` invoked while the tier-3 sentinel exists returns an error message and writes nothing.

#### Task-done alarm specifics

Wired as a `SubagentStop` hook. Fires when any subagent (`implementer`, `reviewer`, `integrator`) finishes. Plays `task-done.wav` and shows a desktop notification: "Task <id> complete. Ready for review" (or analogous message based on which subagent finished). Auto-dismisses after a few seconds. No acknowledgement required.

**Filtering:** if a subagent fires repeatedly during a parallel decomposition (multiple implementers working concurrently), the hook batches alerts — at most one audio cue per 30 seconds, with the notification text aggregating ("3 tasks complete: 042, 043, 044"). This prevents alarm fatigue during heavy parallel work.

**Disable per session:** `/quiet-task-done` slash command suppresses task-done audio for the current session while leaving drift and decision-required active. Useful for marathon implementation sessions where every task completion is expected.

#### Decision-required alarm specifics

Wired as a `Notification` hook (Claude Code's built-in event for "input idle" / "permission needed") **plus** a state-file watcher. The state-file watcher is necessary because not every escalation is captured by the native `Notification` event — when the AI explicitly chooses to escalate per `CLAUDE.md`'s urgent escalation criteria, it writes to `.claude/sessions/.decision-pending-<session-id>` with: timestamp, escalation reason, what the AI was about to do, what input it needs.

A `PostToolUse` hook on `Write` watches for changes to that path and fires the alarm.

**Triggers (urgent escalations only):**
- A "do not touch" file or never-read path needs modification or access.
- A secret or credential is encountered in code or output.
- A hook blocks the task and the fix isn't obvious within one attempt.
- A dependency needs to be added that isn't on the approved list in `deps.md`.
- The implementation reveals the spec was wrong.

**Non-urgent escalations** — ambiguous acceptance criteria, two reasonable approaches with material tradeoffs, active spec version changed mid-task — get in-chat output only, no audio. The operator should attend to them but isn't blocked from doing other things.

**Frequency:** fires once per escalation event. The state file is removed when the operator responds (either by typing in chat or by clicking an "Acknowledge" notification action). If the same escalation criterion fires again later in the session, that's a new event and the alarm fires again.

**Persistence:** the notification does *not* auto-dismiss. The AI is genuinely blocked; the operator should see it whenever they return to the screen. Quiet mode is overridden after the first attempt — see "Quiet mode" above.

#### Threshold and configuration confirmation

Before generating any config files, the AI **shows the default thresholds** for the drift detector (50 tool calls, 120 minutes, 3 file reads) — recorded in the [Assumption Ledger](#assumption-ledger) as model-generation-calibrated defaults, re-validate on a model-tier change — and asks: "Use defaults, or customize?" Defaults are tuned for typical solo-developer sessions; operators with shorter or longer sessions may want adjustments.

**Configuration file** (`.claude/hooks/audio-alerts.config` — replaces the previous `drift-detector.config`):
```
# === Drift detector ===
drift_enabled=true
drift_tool_call_threshold=50
drift_session_duration_minutes=120
drift_file_read_threshold=3
drift_alert_1_delay_minutes=0
drift_alert_2_delay_minutes=10
drift_alert_3_delay_minutes=15
drift_tier3_enforced=true                      # tier 3 hard-blocks tool calls until /clear
quiet_mode_overridden_by_drift_tier3=true      # tier 3 audio plays even in quiet mode

# === Task done ===
task_done_enabled=true
task_done_batch_window_seconds=30

# === Decision required ===
decision_required_enabled=true
decision_required_persistent_notification=true

# === Audio ===
audio_enabled=true
audio_file_drift_gentle=~/.claude/sounds/drift-gentle.wav
audio_file_drift_insistent=~/.claude/sounds/drift-insistent.wav
audio_file_drift_firm=~/.claude/sounds/drift-firm.wav
audio_file_task_done=~/.claude/sounds/task-done.wav
audio_file_decision_required=~/.claude/sounds/decision-required.wav

# === Notifications ===
notification_enabled=true
notification_daemon=auto  # auto | dunst | notify-send | osascript | burnttoast | none

# === Quiet mode ===
quiet_mode_overridden_by_decision_required=true

# === State retention ===
purge_old_state_after_days=7
```

#### Testing all three audio cues

**End-of-Phase-6 test:** after all hooks are installed and the config file is generated, the wizard runs a 30-second audio cue test:
1. Plays drift-gentle, then drift-insistent, then drift-firm in sequence (with 2-second gaps).
2. Plays task-done.
3. Plays decision-required.
4. Asks the operator: **"Are these five sounds clearly distinguishable from each other and from system sounds you hear regularly? (yes / swap files / regenerate with different tones)"**
5. If "swap files" — operator can drop their own WAVs into `~/.claude/sounds/` and the test re-runs.
6. If "regenerate" — the wizard re-generates with different tonal patterns (different pitch ranges, different note counts) and re-tests.

This catches the "all my alarms sound the same" problem before real work starts.

**Per-hook tests:** the wizard also generates per-hook test scripts (`.claude/hooks/test-drift-detector.sh`, `.claude/hooks/test-task-done.sh`, `.claude/hooks/test-decision-required.sh`) that simulate the relevant trigger and let the operator verify each hook's full path (state-file write → notification → audio → acknowledgement) works end-to-end. The drift-detector test specifically exercises both the tier 1–2 advisory path and the tier 3 enforcement path: it simulates a tier-3 fire, confirms the sentinel is written, attempts a non-checkpoint tool call (which must be denied), attempts a checkpoint write (which must be allowed), then removes the sentinel and confirms tool calls flow again.

**Exit criteria:** `settings.json` exists, hook scripts are executable, spec gate and test gate are tested at minimum, all three audio alarm categories are tested via the end-of-phase distinguishability test, operator has seen and approved all hook scripts.

---

<a id="phase-6-5"></a>
## Phase 6.5 — Tools & MCP Configuration

**Goal:** Decide which built-in features and MCP servers to enable. The principle: **subagents and worktrees prevent drift; MCP tools are for capability gaps, not drift gaps.** Tool-hoarding is its own context drift problem — every MCP server costs context budget.

**AI actions:**

### Step 1: Verify built-in features are on

These are non-optional defaults in modern Claude Code. The AI checks each:

- **Tool search (deferred tool loading)** — should be enabled. Defers MCP tool definitions until needed; only tool names load at session start. Without this, even a few MCP servers can consume tens of thousands of tokens before any work begins. Verify with `/context` after Phase 10 — the "MCP tools" line should be small.
- **Worktree isolation for subagents** — will be wired into the agent definitions in Phase 7. Each subagent invocation gets its own git checkout; clean worktrees auto-clean. Phase 7 will set `isolation: worktree` in the `implementer` agent's frontmatter (and others where applicable). Mentioned here so the operator understands the drift-prevention strategy before MCP decisions.
  - **[v2.0.0] Native worktree routing.** Modern Claude Code has native worktree support (`claude --worktree`/`-w`; `isolation: "worktree"` subagents auto-route into a worktree with no manual git plumbing). Where earlier protocol versions hand-rolled worktree setup in the wrappers, prefer the native mechanism. **[RESOLVED at 2.1.0, with a recorded caveat]** Verified: the emitted wrappers contained no hand-rolled `git worktree add` (the iteration loop is operator-completed), so adoption reduced to routing the documented dispatch through native `claude -p --worktree "wt-$TASK_ID"`. The flag is confirmed against official docs (worktrees at `.claude/worktrees/<n>/`, `worktree.baseRef`, `.worktreeinclude`); its introduction release is not verifiable from official release notes, so wrappers rely on the binding seam runtime floor ≥ 2.1.210, which subsumes it. The claim/sentinel + cross-mode accounting block is retained — `--worktree` isolates the working directory only; per-task mutual exclusion and combined-concurrency accounting stay in the wrapper.
  - **[v2.0.0] Worktree is NOT a security boundary.** A git worktree separates working directories; it does not sandbox. Processes inside a worktree keep normal filesystem permissions and can reach neighboring worktrees, the main checkout, or `$HOME`. Treat worktree isolation as a *drift-prevention* mechanism, not a security one. For an actual isolation boundary, see Claude Code's native `/sandbox` runtime (deferred adoption; tracked as a Tessera v1.1 item). Keep worktree roots outside any directory holding non-reconstructible state.
- **Hooks (lifecycle gates)** — already installed in Phase 6. Note that hooks cover 12+ lifecycle events; only a subset are wired up. Adding more is incremental.
- **Auto memory** (Claude Code v2.1.59+) — on by default. Claude saves notes for itself based on operator corrections and recurring patterns. Stored per-project at `~/.claude/projects/<project>/memory/`, loaded at the start of every session alongside CLAUDE.md. **This is the default memory layer; for most solo operators it eliminates the need for a separate memory MCP.** Verify with `/memory` in a session. Toggle with `autoMemoryEnabled` in project settings or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. Auto memory is operator-curated implicitly (Claude decides what's worth saving based on whether it would be useful in a future conversation), complementing the explicitly-curated `decisions.md`, `learnings/`, and `sessions/` artifacts created in Phase 7.

### Step 2: Recommend MCP servers based on archetype and operator profile

The AI proposes a tool list and explains the tradeoff. **Default for a solo developer/operator is minimal — start with two or three MCPs and add only when a real pain point emerges.**

**Tier 1 — Recommended for solo developers (start here):**

- **GitHub MCP** (if using GitHub) — replaces copy-paste of issues, PRs, and repo metadata. High signal-to-context ratio. Earns its keep almost immediately.
- **Claude Context (semantic codebase search)** — recommended for any project over ~200 files. Stores the codebase in a vector DB and pulls only related code into context per request. Earns its place fastest on existing/large codebases; for greenfield projects the spec-driven workflow points to relevant files directly so the value is lower.

**A note on memory MCPs (changed from earlier guidance):**

Modern Claude Code includes **auto memory natively** (see Step 1). For most solo operators, the combination of (a) auto memory, (b) the explicitly-curated `decisions.md` / `learnings/` / `sessions/` artifacts from Phase 7, and (c) the `/checkpoint` and `/resume` workflow eliminates the need for a separate memory MCP at start. **The default recommendation is now: do not install a memory MCP initially.** Add one only if a specific pain point persists after a few weeks of real use — see Tier 2.

**Tier 2 — Add when the specific pain point appears:**

- **A memory MCP** — when auto memory + structured artifacts (`decisions.md`, `learnings/`, `sessions/`) prove insufficient after real use. Specific pain points that justify one:
  - **Cross-machine session continuity** — you switch between a desktop and a laptop frequently and want context to follow.
  - **Multi-month semantic recall** — you frequently need to find "what we decided about X three months ago" and the structured artifacts are too large to scan manually.
  - **Auto-capture of session activity** for later review — you want a queryable log of what Claude actually did across sessions.
  - Pick one, never multiple. Options:
    - **claude-mem** — auto-captures session activity, AI-compresses, injects context into future sessions. Most automated. Good fit when auto-capture is the pain point.
    - **MCP Memory Keeper** — SQLite-backed, simplest. Manual save commands. Good fit when you want explicit control.
    - **MCP Memory Service** — vector-store-backed, semantic recall. Good fit for multi-month recall pain.
- **Error monitoring MCP** (Sentry, Datadog, etc.) — when you find yourself copy-pasting stack traces and dashboards.
- **Database MCP** (Postgres, etc.) — when debugging requires data inspection across sessions.
- **Linear / Jira / project management MCP** — only if the project tracker is the source of truth for tickets. If specs in `.claude/specs/` are the source of truth, skip.

**Tier 3 — Don't add by default (common anti-patterns):**

- **Multiple overlapping memory MCPs** — pick one. Two memory tools means two conflicting notions of "what we decided."
- **A memory MCP installed before auto memory has been tried** — auto memory is native, free, and on by default. Adding a memory MCP without first using auto memory wastes context budget on a pain point you haven't confirmed exists. Wait at least two weeks of real use before deciding.
- **Memory MCPs that auto-generate `CLAUDE.md` files** — claude-mem and similar tools may write folder-level CLAUDE.md files. If installed, configure them to write to a different path (e.g., `.claude-mem/`) so they don't conflict with the deliberate, thin CLAUDE.md created in Phase 8. Alternatively, disable the auto-CLAUDE.md feature.
- **MCPs that wrap shell commands you already have** — `git`, `gh`, `docker`, `kubectl` work fine via Bash. An MCP wrapper is pure context overhead.
- **Sequential thinking / tree-of-thought MCPs** — modern Claude effort tiers cover this natively.
- **Browser automation MCPs** unless the project genuinely needs browser scraping/automation. They're heavy.

### Step 3: Solo developer reference profile

For a solo developer/operator working on a single project, the recommended starting kit:

- **Built-ins:** worktree-isolated subagents, tool search on, hooks installed (Phase 6), **auto memory enabled** (Claude Code v2.1.59+, on by default).
- **MCPs:** GitHub MCP + Claude Context (if codebase is over ~200 files; otherwise just GitHub MCP).
- **No memory MCP at start.** Auto memory + structured artifacts (`decisions.md`, `learnings/`, `sessions/`) cover the same ground for most solo workflows. Add a memory MCP from Tier 2 only if a specific pain point emerges after at least two weeks of real use.
- **That's it.** Two MCPs maximum at start (or one for greenfield small projects). Add more only when a recurring pain point identifies them.

This typically lands the cold-start MCP context cost under 10K tokens — leaving the bulk of the 200K window for actual work.

### Step 4: Optional power-user tooling

Surface these to the operator only if they ask or the profile suggests they'd benefit:

- **McPick** — CLI for toggling MCP servers per session. Worth it once you have 5+ MCPs installed and want to enable subsets per task.
- **Fork mode** (`CLAUDE_CODE_FORK_SUBAGENT=1`) — fork-based subagents reuse the parent's prompt cache. Cheaper than fresh subagents when the work needs the same project context. Use forks for tightly-coupled tasks; use fresh subagents for clean-context work like `/spec-review`.
- **Claude Managed Agents** (Anthropic beta) — fully managed harness as a REST API. Different model from self-hosted `.claude/`. If the operator is invested in the bootstrap approach, skip; if they want to outsource the harness, point them here.

### Step 5: Write `tools.md` and verify

1. Write `.claude/steering/tools.md` documenting:
   - Which built-in features are relied upon (worktree isolation, tool search).
   - Which MCP servers are installed and what each is for.
   - Which were considered and rejected, with the reason (e.g., "Linear MCP not installed: specs are the source of truth, not Linear").
   - The "don't add" list as a guardrail against tool creep.
2. Install the chosen MCP servers using `claude mcp add <name> <command>` (or the project's preferred config method).
3. After installation, run `/context` and show the operator the budget breakdown. Confirm cold-start cost is under 20K tokens for system tools + MCP tools combined (well under 10% of the 200K window).
4. Show and ask: **approve / edit / start over**.

**Exit criteria:** `tools.md` exists. MCP servers are installed and verified. Cold-start context budget measured and acceptable. Operator has seen the breakdown.

---

<a id="phase-7"></a>
## Phase 7 — Skills, Commands, Agents, and Workflow

**Goal:** Install the skill set and define the per-task workflow.

**The per-task lifecycle (6 gates if TDD off, 7 if TDD on):**

1. **Spec exists and is reviewed** — `/spec-review` passed.
2. **Plan is decomposed and approved** — `/spec-decompose` produces tasks; `/plan-review` confirms before any code.
3. **Task picked up by fresh subagent** — implementer reads steering + spec + task file. **Non-obvious decisions are logged continuously to `.claude/specs/<slug>/decisions.md` via the `decision-log` skill** as they're made (this is not a separate gate; it runs throughout implementation).
4. **Tests written first** *(only if TDD enabled)* — implementer writes failing tests before source.
5. **Implementation passes local gates** — lint, type-check, tests via hooks.
6. **Code review by reviewer subagent** — reads diff against spec and principles, returns issues or approval.
7. **Validation against acceptance criteria** — `/spec-validate` against `requirements.md`. After validation passes, `pr-author` skill generates the PR description (this is not a separate gate; it runs after gate 7).

**AI actions:**
1. Create skills (each is a `SKILL.md` file under `.claude/skills/<skill-name>/`). **Model assignment per skill:** skills are invoked from a session, so the model used is whatever the calling session is using. To enforce per-skill models, include a recommendation in the skill's frontmatter or body (e.g., "Recommended: invoke from an Opus session for spec-review") so the operator or calling agent picks the right model. The Model Assignment Strategy table in `Bootstrap-Protocol-Companion-v2-4-0.md` is the source of truth for which skill belongs on which model.
   - `spec-new` — converts a PRD section into `requirements.md`. Initializes `decisions.md` and `changelog.md` for the spec. **Acceptance criteria use EARS notation** (Mavin et al., IEEE RE'09) where the form fits — five patterns covering ubiquitous behaviors, event-driven responses, state-driven preconditions, optional features, and unwanted-behavior guards. EARS forces missing-information discovery: when an acceptance criterion doesn't fit any of the five patterns cleanly, that's a signal the requirement itself is ambiguous and worth restructuring. For requirements with 0–3 preconditions EARS is appropriate; for more complex scenarios fall back to tables or numbered lists.
   - `spec-review` — finds contradictions in a spec.
   - `spec-decompose` — turns spec into atomic tasks with parallelism map. Four concerns layered into one skill:

     **Vertical slicing (always required).** Produce vertical slices, not horizontal phases. A vertical slice crosses all relevant layers (DB + service + UI, or storage + logic + interface) and produces end-to-end functionality on completion. The default AI tendency is horizontal phasing (DB phase → API phase → frontend phase), which delays end-to-end feedback until the last phase and amplifies risk. Force vertical: each task should produce a working, testable thin slice through the system. The skill's instructions must include this constraint explicitly, with examples of bad horizontal decomposition vs good vertical decomposition.

     **Loop-eligibility classifier (only if `loop_mode_enabled` from Phase 0).** After producing the task list, the skill applies a five-criterion test to each task and tags candidates as loop-eligible. The five criteria are evaluated at decompose time: (1) acceptance criteria are unambiguous (EARS-formatted with no missing preconditions, not "should feel polished"); (2) novelty is low (standard CRUD on an existing model, not a new cryptographic protocol); (3) blast radius is bounded (single file or isolated module, not auth/payments/data integrity); (4) tests are authoritative (criteria can be verified by automated tests, not human "does this look right"); (5) rollback is cheap (single commit, easy revert, not a database migration or API contract change). Tasks scoring "yes" on all five are recommended loop-eligible; **the operator confirms or vetoes per task** (recommendations, not decisions). Output is written into the task definition: `loop_eligible: true|false` and (if true) `loop_max_iterations: <integer>` (default 10). When `loop_mode_enabled` is false, the classifier step is skipped to keep `spec-decompose` lean.

     **Goal-supervised-eligibility classifier and recommendation rule (only if `goal_supervised_mode_enabled` from Phase 0).** The skill additionally applies a *sixth* criterion: *Is the goal expressible in one sentence of natural language that a small model could verify from a diff and a test summary?* Examples — "Add a `created_at` timestamp column to the orders table, populated on insert, exposed in the GET /orders response" → yes; "Refactor the payment retry logic to be more resilient" → no (the predicate "more resilient" is not judge-able from a diff); "Change the 404 error response to include a structured `code` field with one of: `not_found`, `expired`, `forbidden_indirect`" → yes; "Improve the test suite's organization" → no. The sixth criterion combines with the existing five to produce four eligibility shapes: all five pass + sixth passes → **eligible for both**; all five pass + sixth fails → **loop-mode-eligible only**; some of five fail + sixth passes → **goal-supervised-eligible only** (the new middle tier — broader blast radius or harder rollback than loop mode accepts, but with a one-sentence verifiable goal); some of five fail + sixth fails → **operator-only**. The task definition gains `goal_supervised_eligible: true|false` and (if true) `goal_condition: "<one-sentence acceptance description>"`. The existing `loop_eligible` field remains unchanged.

     For *eligible-for-both* tasks, the recommendation rule is: prefer loop mode unless the task has at least one property that makes the judge specifically valuable. (a) The acceptance criteria have a semantic component that tests don't fully capture (e.g., "human-readable error message," "matches the documented contract in spirit," "preserves caller-visible behavior"). (b) The diff is expected to be small but spread across multiple files (≥3) — a known failure mode where the reviewer subagent's per-file pass misses cross-file semantic drift. (c) The task touches a public-facing surface (user-visible strings, API response shapes, error messages, CLI help text — a judge approximates "a human glance at the final output" better than deterministic gates do). (d) The task is in a domain `learnings/mode-selection.md` has flagged as drift-prone. If any of (a)–(d) match, the primary recommendation is goal-supervised; otherwise loop mode. The operator-facing UI surfaces both options with reasoning — for example: *"Goal-supervised recommended because: `[matched property]`. Loop mode would also work — pick goal-supervised if you want the judge to second-guess the tricky part — a semantic acceptance criterion, a multi-file diff, a user-visible surface, or a known-drift area. Pick loop mode if you trust the deterministic gates and want lower overhead."* The operator confirms or overrides per task — recommendations, not decisions. When `goal_supervised_mode_enabled` is false, the sixth criterion and recommendation rule are skipped.

     **Queue-population step (only if `queue_mode_enabled` from Phase 0).** After each task has been classified per the above (loop-eligible, goal-supervised-eligible, or operator-only) and the operator has confirmed the per-task mode, `spec-decompose` additionally asks the operator three queue-related questions per task: (i) **priority** (high / normal / low; default normal); (ii) **placement section** — "Ready to run" (default for loop-eligible and goal-supervised-eligible tasks), "Operator-only" (auto-selected if the classification is operator-only — operator-only tasks are **skipped by the runner** and never auto-dispatched; the runner continues with independently-ready tasks around them and pauses only when no dispatchable work remains, see Phase 9.7), or "Deferred" (for tasks the operator wants to defer indefinitely with a note); (iii) **dependencies** — a `blocked_by: [<task-id>, ...]` field listing any prior tasks this one depends on. The skill then appends the task to `.claude/queue/backlog.md` in the appropriate section, with priority, mode classification, and dependency edges recorded inline. The queue file is operator-authored in the sense that every entry is the result of operator confirmation; the skill does not invent tasks, reorder beyond dependency satisfaction, or change classifications. When `queue_mode_enabled` is false, the queue-population step is skipped and `.claude/queue/` is not created.
   - `plan-review` — reviews decomposition before implementation begins.
   - `spec-validate` — checks implementation against `requirements.md` (specifically against the spec version that was active when implementation began — see Phase 7.5).
   - `test-author` — tests-first workflow per task (only generated if TDD enabled).
   - `code-review` — reviews diff against spec and principles.
   - `decision-log` — records non-obvious choices (library picks, tradeoff resolutions, deviations from defaults) to `decisions.md` with timestamp, context, options considered, and rationale. Used continuously during implementation, not at a single gate.
   - `pr-author` — generates PR description with spec link, version, validation report, and decision-log summary. Used at end of task, not at a numbered gate.
   - `checkpoint` — generates a structured session synopsis and writes it to `.claude/sessions/<timestamp>-checkpoint.md`. Synopsis covers: current task and spec ID, completed work this session, in-flight changes (uncommitted), files touched, key decisions made, open questions, state of tests, next steps. Used explicitly by the operator before `/clear`. Updates `INDEX.md` to flag the checkpoint.
   - `resume` — reads checkpoints from `.claude/sessions/`. By default loads the most recent. If the operator passes a timestamp argument or says "list," shows available checkpoints and lets them pick. Loads the relevant steering + spec + decision log, summarizes context, and asks the operator to confirm before continuing. Used explicitly after `/clear` or in a new session.
   - `ack-drift` — writes an acknowledgement timestamp to `.claude/sessions/.drift-ack-<session-id>` to suppress further drift alerts in this session. Used when the operator has seen the alert and chooses to continue without checkpointing.
   - `quiet` — controls audio alert muting. `/quiet on` mutes all audio for the session; `/quiet off` re-enables. `/quiet 2h` (or any duration) mutes until that time elapses. Writes to `.claude/sessions/.quiet-<session-id>` or `~/.claude/quiet-until`. Visual notifications continue; only audio is suppressed. Decision-required alarms override quiet mode after their first attempt.
   - `quiet-task-done` — toggles task-done audio specifically while leaving drift and decision-required active. Useful for marathon implementation sessions where every task completion is expected.
2. Create slash commands wrapping each skill under `.claude/commands/`. The command file format follows whatever the AI tooling expects (typically markdown with frontmatter; the AI will use the existing convention). The `/checkpoint`, `/resume`, and `/ack-drift` commands are explicit-only — never auto-invoked by subagents or hooks.
3. Create subagent definitions under `.claude/agents/`. **Cost disclosure first:** subagent workflows use roughly 4-7x more tokens than single-agent sessions when *all subagents run on the same model* (each gets its own fresh context window — 1M on current Sonnet/Opus tiers, 200K on Haiku). With the mixed-model strategy from the "Model Assignment Strategy" section of `Bootstrap-Protocol-Companion-v2-4-0.md` (Sonnet implementer, Opus reviewer, inherit integrator), the effective multiplier drops to roughly 2-3x because the implementer — which runs most often and burns the most tokens — is on Sonnet. *(The 2-3x figure is a pre-remap estimate derived under the previous price/tokenizer structure; re-derive after instrumenting real usage on Sonnet 5. Recorded in the [Assumption Ledger](#assumption-ledger).)* For solo developers on Pro/Max plans with usage limits, the mixed-model approach is what makes this workflow viable. The trade-off is real but bounded: subagents preserve the parent session's context quality, which is the single biggest drift-prevention mechanism. Reach for them deliberately, not reflexively.

   **Built-in vs custom:** Claude Code ships with `Explore` (read-only codebase search), `Plan` (research before planning), and `General-purpose` (anything else). Use built-ins for *exploratory* work that doesn't modify code: "find all callers of this function," "summarize the auth module," "check whether we have a util for this." Use the **custom `implementer`** below for *modification* work because only the custom implementer has worktree isolation (parallel-edit safety) and reads our steering/spec/task artifacts. The rule: built-ins for read, custom implementer for write.
   - **Description-as-routing-key:** the `description` field is what Claude uses to decide when to delegate. Be specific about *trigger conditions*, not capabilities. "Reviews code for security issues before commits touching auth, payments, or user data" routes correctly; "security expert" does not. Each agent's description must specify *when* to invoke it, not just *what* it does.
   - `implementer` — picks up a task file, reads steering + spec + task, implements, commits, logs decisions. Configuration:
     - **`model: sonnet`** (per Model Assignment Strategy in `Bootstrap-Protocol-Companion-v2-4-0.md` — Sonnet handles execution against a clear spec efficiently).
     - **`isolation: worktree`** — each invocation gets its own git checkout; clean worktrees auto-clean on no-change exits.
     - Description: "Use when an approved spec task is ready for implementation. Reads task file at `.claude/specs/<slug>/tasks/<id>.md`."
   - `reviewer` — reads diff against spec, returns issues. Configuration:
     - **`model: opus`** + **`effort: high`** (per Model Assignment Strategy in `Bootstrap-Protocol-Companion-v2-4-0.md` — code review is judgment-heavy and a missed issue can ship).
     - **`tools: Read, Grep, Glob, Bash`** — read-only. **Exclude Edit and Write** so the reviewer cannot modify code (security boundary, not just convention).
     - No `worktree` needed since the agent is read-only.
     - Description: "Use after implementer commits a task. Reviews diff against the originating spec's acceptance criteria and `principles.md`."
   - `integrator` — handles merge conflicts between parallel tasks. Configuration:
     - **`model: inherit`** (per Model Assignment Strategy in `Bootstrap-Protocol-Companion-v2-4-0.md` — match main session because conflict complexity varies). If main session is on Haiku for some reason, override to `model: sonnet`.
     - Worktree isolation depends on conflict pattern; default to no isolation since integration touches multiple worktrees.
     - Description: "Use when two implementer worktrees have produced conflicting changes to overlapping files."
   The agent definitions follow the convention of the AI tooling (Claude Code uses YAML frontmatter + markdown body; the AI checks the project's existing conventions or current Claude Code docs and adapts). **Note:** subagents do not inherit the full default Claude Code system prompt — they get their own prompt plus basic environment details. Write each agent's prompt as self-contained instructions, not relying on default Claude Code behaviors.

   **Loop-mode-aware variant (only if `loop_mode_enabled` from Phase 0):** when loop mode is opted into, the wizard generates an additional variant body for the `implementer` definition, gated on whether `.claude/sessions/.loop-active-<task-id>` exists at session start. The variant differs from the default in three ways: (1) the implementer's prompt instructs it that on tier-3 fire it should write the standard checkpoint and then **end its turn** (no further tool calls; the wrapper handles the reset by starting a fresh session) instead of waiting for the operator; (2) the implementer's prompt adds the decision-log protocol — for non-urgent decisions that would normally surface to the operator (two reasonable approaches with tradeoffs, ambiguous-but-resolvable acceptance criterion), append an entry to `.claude/sessions/decisions-log-<task-id>.md` with question, options, choice, justification, and reversibility flag, then continue with the chosen option; (3) the implementer's prompt enumerates the urgent escalation criteria explicitly and instructs that on any of them, write `.claude/sessions/.loop-halt-<task-id>` alongside the existing `.decision-pending-<session-id>` and end the turn. The variant also instructs the implementer to consult the task's `progress.md` **Failed approaches** section during priming and not to re-attempt any dead end flagged do-not-retry. **The reviewer subagent is *not* modified for loop mode** — it continues its diff-vs-spec review the same way and writes the same approval signal. The reviewer is part of the deterministic gate; modifying it to be loop-aware would conflate the gate with the iteration mechanism and weaken both. See Phase 9.5 for the full cooperation contract.

   **Goal-supervised-mode-aware variant (only if `goal_supervised_mode_enabled` from Phase 0):** when goal-supervised mode is opted into, the wizard generates an additional variant body for the `implementer` definition, gated on whether `.claude/sessions/.goal-active-<task-id>` exists at session start. The two autonomous-mode variants (loop-mode and goal-supervised) are mutually exclusive at runtime because a task is in exactly one mode's in-flight list. The goal-supervised variant shares the loop-mode variant's three behaviors above (tier-3 self-healing, decision-log protocol for non-urgent decisions, urgent-escalation `.loop-halt-<task-id>` write) and adds three goal-supervised-specific behaviors: (1) **iteration-summary discipline** — at the end of each iteration, write `.claude/sessions/.iteration-summary-<task-id>-<iter-n>.md` in the structured format specified in Phase 9.6 (goal condition, completion-criteria status checklist, what changed this iteration, what still needs work, notes for the evaluator). Do not freeform; do not skip — the iteration-summary enforcement hook treats missing or malformed summaries as a `summary_failure_count` increment, and three consecutive failures halt the loop. (2) **Evaluator-feedback reading** — during priming, read the most recent two entries from `.claude/sessions/.evaluator-feedback-<task-id>.md` if it exists, and treat them as peer signals (the judge is advisory, not authoritative — if the judge's feedback is wrong, address it in the next iteration's summary; do not silently override). (3) **No self-verification shortcut** — writing `.claude/sessions/.loop-complete-<task-id>` is required for terminal success and is never inferred; the wrapper requires the sentinel even when the judge says yes and the deterministic gates pass. **The reviewer subagent is *not* modified for goal-supervised mode** — it continues to do its diff-vs-spec review the same way and writes the same approval signal. The reviewer is part of the deterministic gate; the judge is a separate signal; conflating them would weaken both. The variant also reads the task's `progress.md` **Failed approaches** during priming and does not re-attempt do-not-retry dead ends. See Phase 9.6 for the full cooperation contract.
4. Initialize `.claude/specs/INDEX.md` as the living task board with documented schema: spec slug, current version, status (`planned` / `draft` / `in-flight` / `complete` / `superseded`), in-flight task IDs, blocked tasks, last checkpoint reference. The board ships with a single placeholder row; if Phase 7.6 runs, that row is replaced by one `status: planned` row per deliverable derived from the PRD. If Phase 7.6 is skipped, the placeholder stays and `/spec-new` invents slugs at call time.
5. Initialize `.claude/learnings/` with a README explaining the convention (one file per learning, titled by topic, dated). **Note:** `learnings/` is for cross-feature insights; `decisions.md` is for within-feature choices; `sessions/` is for session-recovery state; **`progress.md` (below) is the within-task status + dead-ends ledger.** **Per-task progress artifact (`.claude/specs/<slug>/progress.md`):** created at task start and updated at every iteration boundary and at each interactive checkpoint write. Required sections: `Status` (one line), `Completed`, `In flight`, and `Failed approaches` (each entry records what was tried, why it failed, and a do-not-retry flag). It **links** to `decisions.md`, `learnings/`, and the latest checkpoint and MUST NOT duplicate their content — compose-do-not-fork applied to the protocol's own artifacts; a `progress.md` that inlines a `decisions.md` entry rather than linking it is a lint failure. Committed (operator-facing audit record).
6. Initialize `.claude/sessions/` with a README documenting the checkpoint schema and the audio alert state-file mechanisms. The directory holds: `<timestamp>-checkpoint.md` files, plus per-session state files for the audio alert system (`.drift-ack-<id>`, `.drift-state-<id>`, `.drift-tier3-<id>`, `.decision-pending-<id>`, `.quiet-<id>`, `.session-<id>`). When loop mode is opted into at Phase 9.5, this directory also holds per-task loop state: `decisions-log-<task-id>.md`, `loop-final-<task-id>.md`, `.loop-active-<task-id>`, `.loop-complete-<task-id>`, `.loop-halt-<task-id>` — see Phase 9.5 for definitions. When goal-supervised mode is opted into at Phase 9.6, this directory additionally holds per-task goal-supervised state: `.goal-active-<task-id>` (active marker), `.iteration-summary-<task-id>-<iter-n>.md` (the structured per-iteration summary the judge reads), `.evaluator-feedback-<task-id>.md` (accumulated judge `{verdict, reason}` responses). The `decisions-log-<task-id>.md` and `loop-final-<task-id>.md` files are shared with loop mode — same filename convention, same operator-facing audit purpose. See Phase 9.6 for definitions. When queue mode is opted into at Phase 9.7, queue-mode artifacts live in a sibling directory (`.claude/queue/`) rather than in `.claude/sessions/`, because they are queue-scoped (one set per queue run) rather than session-scoped (one set per session) — see Phase 9.7 for the directory layout. The queue runner does not write to `.claude/sessions/` directly; it dispatches the per-task wrappers, which continue to write their per-task artifacts into `.claude/sessions/` as before.
7. **Generate `.gitignore` entries for bootstrap state files.** Append to project `.gitignore` (or create one if absent) the following block, with a comment header so it's identifiable:
   ```
   # Bootstrap state — local, do not commit
   .claude/.bootstrap-state.json
   .claude/.bootstrap-state.json.pre-1.7
   .claude/.bootstrap-state.json.pre-1.8
   .claude/.bootstrap-state.json.pre-1.9
   .claude/.bootstrap-incomplete
   .claude/sessions/.session-*
   .claude/sessions/.drift-ack-*
   .claude/sessions/.drift-state-*
   .claude/sessions/.drift-tier3-*
   .claude/sessions/.decision-pending-*
   .claude/sessions/.quiet-*
   .claude/sessions/.loop-active-*
   .claude/sessions/.loop-complete-*
   .claude/sessions/.loop-halt-*
   .claude/sessions/.goal-active-*
   .claude/sessions/.iteration-summary-*
   .claude/sessions/.evaluator-feedback-*
   .claude/queue/.run-active
   .claude/queue/.halt
   .claude/queue/.resume
   .claude/logs/
   ```
   Operator-facing artifacts (`CLAUDE.md`, all `.claude/steering/*.md` (including `.claude/steering/assumption-ledger.md` and — when telemetry export is opted into — `.claude/steering/telemetry.md`), all `.claude/specs/` (including each spec's `progress.md`), all `.claude/learnings/`, `.claude/agents/`, `.claude/hooks/`, `.claude/commands/`, `.claude/skills/`, `.claude/sessions/*-checkpoint.md`, `.claude/sessions/decisions-log-*.md`, `.claude/sessions/loop-final-*.md`, and — when generated — `.claude/loop.sh`, `.claude/loop-config.md`, `.claude/goal-loop.sh`, `.claude/goal-config.md`, `.claude/auto.sh`, `.claude/auto-config.md`, `.claude/queue/backlog.md`, `.claude/queue/run-summary-*.md`) are committed normally. State files use the dotfile convention precisely so they can be gitignored as a group; per-task loop artifacts (`decisions-log-*.md`, `loop-final-*.md`) use regular naming because they are operator-facing audit records that belong in the repo. The `.iteration-summary-*` and `.evaluator-feedback-*` files are gitignored because they are per-iteration scratch state for the wrapper and the judge; the operator-facing post-hoc record is the `loop-final-*.md` summary, which aggregates the relevant signal. For queue mode: the queue file `backlog.md` and historical `run-summary-*.md` files are operator-facing audit records and are **committed**; only the runtime sentinels (`.run-active`, `.halt`, `.resume`) are gitignored.
8. Show all created files. Ask: **approve / edit / start over**.

**Exit criteria:** All skill, command, agent files exist with the correct format for the AI tooling. INDEX, learnings, and sessions directories initialized. The decision-log, checkpoint, drift-ack, and quiet-mode conventions are documented.

---

<a id="phase-7-5"></a>
## Phase 7.5 — Spec Versioning Protocol

**Goal:** Define what happens when requirements change mid-implementation, so spec edits don't silently invalidate work in flight.

**Skippable** for solo, short-lived projects where in-flight specs are unlikely to outlast a single session. Operator must explicitly request the skip.

**AI actions:**
1. Explain to the operator: specs change. The question is whether changes are tracked, or whether they happen silently and invalidate in-flight work without anyone noticing.
2. Establish the versioning convention:
   - Each `requirements.md` carries a `version:` field in its frontmatter (semver-like: `1.0.0`).
   - **Patch bumps** (`1.0.0` → `1.0.1`): clarifications, typo fixes, no semantic change. In-flight tasks continue.
   - **Minor bumps** (`1.0.0` → `1.1.0`): additive changes (new acceptance criteria, expanded scope) that don't contradict existing work. In-flight tasks continue but are flagged for re-validation.
   - **Major bumps** (`1.0.0` → `2.0.0`): breaking changes (removed criteria, altered behavior, scope cut). All in-flight tasks halt and require human review before resuming.
3. Define the change-log convention: every spec has a `changelog.md` alongside `requirements.md` with version, date, change summary, and impact on in-flight tasks.
4. Note that **`design.md` is internal and unversioned**. Only `requirements.md` is the contract. Design drift is OK; requirements drift requires versioning.
5. Update the `spec-validate` skill (already created in Phase 7) to record which spec version the implementation was validated against. PR descriptions include the version.
6. Update the `INDEX.md` schema to track the active spec version per feature and flag any in-flight tasks running against a now-superseded version.
7. Define the operator workflow for changing a spec mid-flight: open `requirements.md`, propose the change, classify the bump (patch/minor/major); if major, list affected in-flight tasks and require explicit acknowledgment before bumping; append to `changelog.md`; for minor/major, trigger re-validation of completed tasks.
8. Write `.claude/steering/spec-versioning.md` documenting the protocol so it's discoverable.
9. Show and ask: **approve / edit / start over**.

**Exit criteria:** Versioning protocol is documented. Skills and INDEX schema are updated to track versions.

---

<a id="phase-7-6"></a>
## Phase 7.6 — Spec roster derivation

**Goal:** Derive the spec roster from the PRD and write it into `specs/INDEX.md` as `status: planned` rows, so slug naming becomes a lookup against an existing roadmap rather than an invention each time `/spec-new` runs.

**Skippable:** Yes, for projects whose PRD is too rough to enumerate deliverables cleanly. The operator must request the skip explicitly — the wizard does not skip on its own. On skip, INDEX.md retains its placeholder row, and `/spec-new` invents slugs at call time. Disposition is recorded under `skippable_phase_decisions.phase_7_6_spec_roster` in `.bootstrap-state.json`.

**AI actions:**

1. Re-read the PRD loaded in Phase 0. Enumerate distinct deliverables — units of work each producing a coherent `requirements.md`. PRD goals, non-trivial sections, and explicit-deliverable callouts ("X is the predecessor task," "the first deliverable is Y") each become a candidate row. Trivial or scaffolding-only sections do not.

2. For each deliverable, derive a slug using the rule recorded in `.claude/steering/structure.md` under "Spec slug naming," priority order:
   (a) If the deliverable names a primary output file in the PRD or in `structure.md`, the slug is the kebab-cased stem of that filename (e.g., `docs/doc-grammar.md` → `doc-grammar`).
   (b) Otherwise the slug is the kebab-cased noun phrase from the deliverable's PRD name, with articles and connective words dropped and numbers preserved.
   (c) On collision, append the PRD section number (e.g., `grammar-86`).
   Write the rule in full into `structure.md`'s naming recap area as a new "Spec slug naming" subsection. Future file-creating tasks already read `structure.md`; that is where the rule lives. The canonical text to copy verbatim into `structure.md`:

   > ### Spec slug naming
   >
   > Slugs for `specs/INDEX.md` rows and `/spec-new` invocations are derived deterministically. Apply rules in order; first match wins:
   >
   > 1. **Primary output file.** If the deliverable names a primary output file in the PRD or in this `structure.md`, the slug is the kebab-cased stem of that filename. `docs/doc-grammar.md` → `doc-grammar`. `src/parameter-extractor.ts` → `parameter-extractor`. Path and extension are stripped; only the stem participates.
   >
   > 2. **PRD noun phrase.** If no primary output file is named, the slug is the kebab-cased noun phrase from the deliverable's PRD name, with articles (`a`, `an`, `the`) and connective words (`of`, `for`, `and`, `to`, `in`) dropped. Numbers are preserved literally. "The Parameter Extractor for v2" → `parameter-extractor-v2`.
   >
   > 3. **Collision suffix.** If a derived slug collides with an existing row in `specs/INDEX.md` (any status, including `superseded`), append the source PRD section number with a hyphen. Two `grammar` collisions, one from §8.6, become `grammar-86`. Re-collisions extend the suffix with the subsection (`grammar-86-2`).
   >
   > Slugs are immutable once a row reaches `status: in-flight`. Renames before that point are operator-driven during the Phase 7.6 review step and must re-pass the rules above. Do not invent slugs from memory or aesthetic preference — the rule exists so two operators starting from the same PRD produce the same roster.

3. Present the proposed roster to the operator as a markdown table with columns: `slug | source PRD section | one-line description | suggested first | depends on (slugs)`. Mark exactly one row `suggested first` using the PRD's own ordering signals ("predecessor task," "first deliverable," explicit precedence callouts). If the PRD names no precedence, ask the operator which deliverable comes first rather than guessing.

4. Operator approves the roster, edits it inline (rename slugs, remove rows, reorder, adjust dependency edges), or rejects the whole roster and takes the skip path. Inline edits are re-validated against the slug rule before acceptance.

5. On approval, replace the placeholder row in `specs/INDEX.md` with one row per derived deliverable, each `status: planned`, carrying the dependency edges from step 3. Other columns (`in-flight tasks`, `blocked tasks`, `last checkpoint`, `loop-eligible / total`) remain empty until `/spec-new` and `/spec-decompose` populate them.

6. Add `planned` to INDEX.md's status legend: "spec roster row; `requirements.md` not yet authored; awaits `/spec-new <slug>`."

**Exit criteria:** `specs/INDEX.md` contains one `status: planned` row per derived deliverable, or the operator explicitly skipped Phase 7.6. `.claude/steering/structure.md` contains the "Spec slug naming" subsection. `.bootstrap-state.json` records the disposition under `skippable_phase_decisions.phase_7_6_spec_roster`.

---

<a id="phase-8"></a>
## Phase 8 — Root `CLAUDE.md` and Escalation Rules

**Goal:** Write the thin index that ties everything together, plus explicit escalation criteria.

**AI actions:**
1. Write `CLAUDE.md` at repo root with:
   - References to all created steering docs (product, tech, deps, secrets, structure, principles, ci-cd, tools, spec-versioning — count varies based on which phases ran).
   - Reference to `specs/INDEX.md` (includes the planned-spec roster from Phase 7.6 if it ran), `learnings/`, and `sessions/` (with brief explanation of each). Note that each spec's `progress.md` (status + failed-approaches ledger) is read first at task/iteration priming, before the task brief, so a resumed or re-primed session does not re-attempt known dead ends.
   - The per-task workflow (gate count adapts to TDD policy).
   - **Session hygiene reference:** `/checkpoint` before `/clear`, `/resume` to restore. The drift detector will alert when context degrades — `/ack-drift` to suppress alerts if intentionally continuing.
   - **Loop-mode-active check (only if loop mode is enabled at Phase 9.5):** a top-of-file conditional instruction — "If `.claude/sessions/.loop-active-<task-id>` exists at session start, this session is running inside an autonomous loop. Load the loop-mode behavioral addendum below: (a) on tier-3 drift, write the standard checkpoint and end the turn (the wrapper handles the reset by starting a fresh session); (b) on non-urgent decisions, append to `decisions-log-<task-id>.md` and continue with a defensible default (minimizes blast radius if wrong, easiest to reverse); (c) on any urgent escalation criterion, write `.loop-halt-<task-id>` alongside `.decision-pending-<session-id>` and end the turn." If loop mode is not enabled at bootstrap, this section is omitted; if enabled later, the operator regenerates `CLAUDE.md` via the loop-mode setup or edits in place.
   - **Goal-supervised-mode-active check (only if goal-supervised mode is enabled at Phase 9.6):** a parallel top-of-file conditional instruction — "If `.claude/sessions/.goal-active-<task-id>` exists at session start, this session is running inside a goal-supervised loop. Load the goal-supervised-mode behavioral addendum below: (a) all three loop-mode behaviors above (tier-3 checkpoint-and-end, decision-log for non-urgent, `.loop-halt-<task-id>` for urgent escalation) apply unchanged; (b) **write the structured iteration summary** at iteration end in the required format (goal condition / completion-criteria status checklist / what changed this iteration / what still needs work / notes for the evaluator — full format in Phase 9.6); do not skip, do not freeform; (c) **read `.evaluator-feedback-<task-id>.md`** during priming (most recent two entries) and treat the judge's feedback as a peer signal — if the judge is wrong, address the disagreement explicitly in the next iteration's summary rather than silently overriding; (d) **self-verification (writing `.loop-complete-<task-id>`) is required** for terminal success and is never inferred, even when the judge says yes and the deterministic gates pass." The two addenda (loop-mode and goal-supervised) are mutually exclusive at runtime because a task is in exactly one mode's in-flight list — only one will be loaded in any single iteration. If goal-supervised mode is not enabled at bootstrap, this section is omitted; if enabled later, the operator regenerates `CLAUDE.md` via the goal-supervised-mode setup or edits in place.
   - **Queue-mode coordination-layer reference (only if queue mode is enabled at Phase 9.7):** a short "Running modes" reference section noting that queue mode is a coordination layer above the per-task mechanisms — *"This project has autonomous queue mode (`auto.sh`) enabled. The runner dispatches loop-mode and goal-supervised-mode tasks from `.claude/queue/backlog.md` in sequence. The runner itself does not load this CLAUDE.md; it invokes the per-task wrappers, which load it as in manual dispatch. The escalation criteria below behave identically whether the agent is running under manual dispatch or queue dispatch. See `.claude/queue/backlog.md` for the current queue and `.claude/queue/run-summary-*.md` for past runs."* This reference is **not a behavioral addendum** — there is no per-iteration sentinel for queue mode and no per-iteration behavioral change at the agent level. It exists only so an operator or agent reading `CLAUDE.md` can find their way to the queue artifacts. If queue mode is not enabled at bootstrap, this section is omitted; if enabled later, the operator regenerates `CLAUDE.md` via the queue-mode setup or edits in place.
   - The "Never" list pulled from `tech.md` "do not touch" + `secrets.md` never-read paths + universal rules (no test-rewriting, no skipping `/spec-review`, no commit without tests).
   - **Explicit escalation criteria** — when the agent must stop and ask the human. Items marked **🔔** trigger the decision-required audio alarm (urgent — agent is blocked); others get in-chat output only. **Inside an autonomous mode** (when `.claude/sessions/.loop-active-<task-id>` *or* `.claude/sessions/.goal-active-<task-id>` exists), the urgent items still hard-block but additionally cause the agent to write `.loop-halt-<task-id>` and end the turn so the wrapper can halt the loop; the non-urgent items are routed to `decisions-log-<task-id>.md` instead of producing chat output. Behavior is identical between loop mode and goal-supervised mode for these criteria — both modes share the same `.loop-halt-<task-id>` and `decisions-log-<task-id>.md` filename conventions, and the same urgent vs non-urgent routing:
     - **🔔** A "do not touch" file or never-read path needs modification or access.
     - Acceptance criteria are ambiguous after re-reading the spec. *(Inside an autonomous mode: routed to decision log if resolvable by a defensible default; otherwise treated as urgent.)*
     - Two reasonable approaches exist with materially different tradeoffs. *(Inside an autonomous mode: routed to decision log.)*
     - **🔔** A hook blocks the task and the fix isn't obvious within one attempt.
     - **🔔** A dependency needs to be added that isn't on the approved list in `deps.md`.
     - **🔔** A secret or credential is encountered in code or output.
     - **🔔** The implementation reveals the spec was wrong (triggers spec-versioning protocol).
     - The active spec version has changed since the task started.
     - The drift detector has fired Alert 3 (firm). Tier 3 is enforced: the agent writes `.claude/sessions/<timestamp>-checkpoint.md` (standard synopsis schema), and is then hard-blocked from further tool calls until the operator runs `/clear`. The agent's responsibility is to produce a complete, useful checkpoint; the operator's responsibility is to run `/clear` and `/resume`. *(Inside an autonomous mode: the agent writes the checkpoint and ends the turn; the wrapper starts a fresh session primed with the new checkpoint, no operator action needed — see Phase 9.5 for loop mode and Phase 9.6 for goal-supervised mode.)*
   - When triggering the decision-required alarm, the agent writes to `.claude/sessions/.decision-pending-<session-id>` with: timestamp, escalation reason, what the agent was about to do, what input it needs.
2. Keep it thin — roughly 80 lines max. Everything else loads on demand.
3. Show and ask: **approve / edit / start over**.

**Exit criteria:** `CLAUDE.md` exists, is thin, and includes escalation criteria and session hygiene references.

---

<a id="phase-9"></a>
## Phase 9 — Smoke Test (Optional but Recommended)

**Goal:** Validate the system end-to-end on a real feature before declaring bootstrap complete.

**AI actions:**
1. Ask: "Run the workflow as a smoke test? If Phase 7.6 ran, pick the planned spec marked `suggested first` from `specs/INDEX.md`; otherwise pick the smallest PRD feature directly."
2. If yes, run `/spec-new` → `/spec-review` → `/spec-decompose` → `/plan-review`. Show the operator the generated spec, review notes, task list, and plan-review feedback. Confirm the system produces sensible output.
3. **Offer a second-stage smoke test** — implement one task end-to-end. Ask: "Run a single task through the implementer subagent → reviewer subagent → spec-validate flow?" This is the only step in the wizard that produces real code, and it's *optional but strongly recommended* because it validates the most failure-prone part of the workflow (subagent isolation, hook gating, code review). If declined, note that the implementation flow is untested and the operator will discover any issues on their first real task.
4. **Loop-mode smoke (only if Phase 9.5 was opted into):** ask: "Run a third-stage smoke test that exercises loop mode end-to-end on the smallest loop-eligible task?" If yes, the wizard flags one task from the second-stage smoke as loop-eligible (or generates a tiny synthetic task if none from the smoke set qualifies — e.g., a doc fix or a single-file lint cleanup), invokes `loop.sh` against it, and verifies: wrapper starts, classifier flag honored, completion sentinel written and detected, decision log accessible, `loop-final-<task-id>.md` summary produced, and the wrapper exits cleanly. If a tier-3 fire is provoked (the wizard can stub one for the test), verify the self-healing restart path. If declined, note that loop mode is untested and the operator should run a manual smoke before relying on it.
5. **Goal-supervised-mode smoke (only if Phase 9.6 was opted into):** ask: "Run a fourth-stage smoke test that exercises goal-supervised mode end-to-end on a known-good trivial task?" If yes, the wizard flags or generates a goal-supervised-eligible task (a one-field schema addition with a structured goal condition, or similar — small enough that a single iteration likely completes it), invokes `goal-loop.sh` against it, and verifies: (a) the iteration-summary file is written in the required structured format; (b) the judge API call succeeds and returns a structured `{verdict, reason}` response; (c) the feedback file accumulates entries correctly across iterations; (d) the agent reads the feedback on the next iteration (evidenced by the next summary acknowledging the prior judge response, if a second iteration occurs); (e) the deterministic completion gate, judge verdict, and self-verification sentinel all agree at terminal completion; (f) `loop-final-<task-id>.md` is produced and the wrapper exits cleanly; (g) the iteration-summary enforcement hook fires correctly if a malformed-summary iteration is stubbed for the test; (h) the drift-detector cooperation hook recognizes the `.goal-active-<task-id>` marker if a tier-3 fire is provoked. If declined, note that goal-supervised mode is untested and the operator should run a manual smoke before relying on it. If both Phase 9.5 and Phase 9.6 were opted into, run both smokes — they are independent.
6. **Queue-mode smoke (only if Phase 9.7 was opted into):** ask: "Run a fifth-stage smoke test that exercises queue mode end-to-end on a small synthetic queue?" If yes, run the sub-smokes below in order. If declined, note that queue mode is untested and the operator should run a manual smoke before relying on the runner for real work, particularly before any unattended overnight use.

   **6.a — Basic two-task smoke.** Construct a small queue with 2 known-good trivial tasks (one loop-mode and one goal-supervised if both per-task modes are enabled; otherwise both tasks in whichever single mode is enabled). Set a tight time budget (15 minutes) and a task budget of 2. Invoke `auto.sh` against the queue and verify, in order:
     - (a) The runner starts cleanly, writes `.claude/queue/.run-active` with PID and start timestamp, appends an entry to `queue_runs_history`, and dispatches the first task.
     - (b) The first task's wrapper invocation works correctly (the per-task wrapper writes its own `.loop-active-*` or `.goal-active-*` sentinel and the runner does not interfere).
     - (c) The per-task wrapper terminates with a `loop-final-<task-id>.md`, the runner reads the termination classification, updates `backlog.md` (removes from "In flight," adds to "Completed this run"), and appends a one-block entry to the run-summary file.
     - (d) The runner dispatches the second task.
     - (e) The second task terminates successfully.
     - (f) The runner detects empty queue and exits terminal-success.
     - (g) The morning-after summary at `.claude/queue/run-summary-<timestamp>.md` is written and contains both tasks with their stats.
     - (h) `.claude/queue/.run-active` is removed and the `queue_runs_history` entry is updated with `end_timestamp` and `exit_reason: "queue-empty"`.

   **6.b — Budget-exhaustion smoke (optional).** Run a second pass with a tight time budget (1 minute) and a queue with 3+ tasks. The runner should finish any in-flight task to its next iteration boundary, refuse to dispatch new tasks, and exit terminal with `exit_reason: "time-budget-exhausted"`. If a small budget makes the smoke flaky on slow machines, the wizard adjusts.

   **6.c — Urgent-escalation-halts-queue smoke (optional, only if mechanically stubbable).** Only run if the AI can mechanically stub the condition — e.g., by writing a `.loop-halt-<task-id>` sentinel directly to simulate the urgent-escalation exit. Prepare a 3-task synthetic queue. Let the first task complete cleanly. Stub the second task's wrapper to write `.loop-halt-<task-id>` and a `loop-final-<task-id>.md` with `halt_reason: "urgent-escalation"`. Verify that the runner reads the halt, classifies it as urgent escalation, halts the queue immediately (does not dispatch the third task), records the halt in `run-summary` and in `queue_runs_history`, and exits with `exit_reason: "urgent-escalation"`. This sub-smoke confirms the non-configurable urgent-escalation rule works as designed; skip it if mechanical stubbing isn't feasible in the project's environment.

   **6.d — Skip-and-continue plus pause-resume smoke.** Prepare a 4-task synthetic queue:
     - task-A — loop-mode, no deps, normal priority.
     - task-B — operator-only, high priority, placed in the "Operator-only" section.
     - task-C — loop-mode, no deps, low priority.
     - task-D — loop-mode, `blocked_by: [task-B]`, normal priority, placed in "Ready to run".

     Invoke `auto.sh` and verify, in order:
     - (i) task-B is never dispatched and never causes a pause while task-A or task-C remain dispatchable.
     - (ii) task-D is recognized as transitively blocked on operator-only task-B and is skipped on every scan.
     - (iii) task-A and task-C both complete cleanly in priority order (high-priority task-B is correctly skipped past, not stalled-on).
     - (iv) task-B appears in the run-summary's "Did not run" section flagged as awaiting operator action, and task-D appears flagged as transitively blocked on task-B.
     - (v) Once task-A and task-C are done with no further dispatchable work and task-B still sitting in "Operator-only," the runner pauses (does not terminal-success and does not terminal-fail) and the run-summary records the pause reason.

     Then exercise the pause-resume cycle: the smoke harness simulates the operator hand-off by editing `backlog.md` to move task-B's line from "Operator-only" to "Completed this run," then writes `.claude/queue/.resume`. Verify:
     - (vi) The runner consumes `.resume` (deletes the sentinel), re-scans, finds task-D now ready (its blocker is completed), dispatches it, lets it complete, and exits terminal-success with `exit_reason: "queue-empty"`.

     This confirms the skip-and-continue semantics and the pause-resume cycle end-to-end.
7. If anything is off at any stage, return to the relevant phase and adjust.
8. **CI config generation (if deferred from Phase 5).** If `deferred_items.ci_config_generation` is set in `.bootstrap-state.json`, generate the CI config files now based on `ci-cd.md` and clear the flag. If Phase 9 itself is being skipped, this step is also skipped — Phase 10's handoff will surface the residual generation as a remaining task.

**Exit criteria:** Either smoke-test artifacts exist (stage 1 minimum, stage 2 ideally, stage 3 when loop mode is opted in, stage 4 when goal-supervised mode is opted in, stage 5 when queue mode is opted in) and look right, or operator opted to skip.

---

<a id="phase-9-5"></a>
## Phase 9.5 — Autonomous Loop Mode (Optional)

**Goal:** Install a first-class autonomous-iteration mode for individual tasks, while preserving every existing enforcement guarantee. **Default: skipped.** Operators who declined at Phase 0 reach this section and skip past it; the rest of this section applies only when `loop_mode_enabled` is true.

**What loop mode is:** an opt-in per-task execution mode where the agent iterates on a single task — completion check after each iteration, restart on failure with prior context primed — until completion criteria are met, max-iterations is hit, or an urgent escalation halts the run. Operators get hands-off execution on bounded tasks; the protocol's safety properties (tier 3 enforcement, urgent escalation, reviewer subagent, spec gate, integrator) are unchanged.

**What loop mode is not:**
- **Not a "let Claude do everything" mode.** Loop mode runs one task at a time. It does not run an entire spec, an entire feature, or a PRD. It does not run overnight on the whole project.
- **Not a quality maximizer.** The defensible-default criterion is conservative-with-easy-reversal, not best-possible. Operators who want maximum quality stay operator-in-the-loop.
- **Not a replacement for review.** The reviewer subagent still runs at task boundaries. The operator still reviews the decision log post-hoc. The integrator still merges. Loop mode reduces *operator presence during execution*, not *operator review of outcomes*.
- **Not a license to weaken escalation.** All five urgent escalation criteria are unchanged. Tier 3 enforcement is unchanged in semantics (augmented for self-healing restart inside the loop, not weakened).

### Design principles (the operator should understand these before opting in)

- **Per-task scoping, not per-spec or per-PRD.** The loop runs on a single task — the unit produced by `spec-decompose`. Tasks are vertical slices with clear acceptance criteria, bounded scope, and a built-in reviewer subagent gate. Looping at any larger granularity reproduces the production failure modes of unbounded Ralph (5000 lines of plausible-looking code, half wrong, none reviewed).
- **Opt-in per task, not per project.** At `spec-decompose` time, the classifier surfaces recommendations; the operator confirms or vetoes per-task. Default for any unclassified task: not loop-mode.
- **All existing enforcement guarantees survive loop mode.** Tier 3 drift still hard-blocks. All five urgent escalation criteria still hard-block. The reviewer subagent still runs. The integrator still merges. The spec gate still gates commits. Loop mode changes *what happens between* enforced gates; it does not weaken any gate.
- **Decisions are logged, not skipped.** Non-urgent decisions that would normally surface to the operator (two reasonable approaches with tradeoffs, ambiguous-but-resolvable acceptance criteria) get a defensible default chosen by the agent and a complete log entry. The operator reviews the log after the loop run, can override, and can re-loop with explicit overrides.
- **The loop is bounded.** Three independent termination conditions: completion criteria met, max-iterations hit, or unrecoverable escalation. There is no "run until I tell you to stop" mode.

### Architecture: the hierarchy

```
PRD
 └─ spec (one feature)
     └─ task (vertical slice, optionally loop-mode)
         └─ iteration N within the task's loop
             └─ reviewer subagent run (built-in gate)
```

Loop mode operates at the task level. Iterations within the loop are bash invocations of `claude -p` with structured priming. Each iteration ends with one of: completion (clean exit + completion sentinel), tier-3 enforcement (clean exit + tier-3 sentinel + fresh checkpoint; the wrapper re-primes — see "A note on exit semantics" below), or a hard-block escalation (clean exit + halt sentinel + operator alert; no restart).

### Architecture: the wrapper

A new optional script `.claude/loop.sh` (or a per-OS equivalent generated by the wizard — PowerShell on Windows, the same shell idiom on macOS/Linux) wraps `claude -p` with the loop. The wrapper:

1. **Verifies the task is loop-eligible.** Reads `.claude/specs/<spec-id>/tasks/<task-id>.md` and confirms `loop_eligible: true`. Refuses to run otherwise.
2. **Claims the task atomically (mutual-exclusion check).** This step must be race-safe — two simultaneous wrappers must not both succeed for the same task. The wrapper:
   1. Attempts to create `.claude/sessions/.loop-active-<task-id>` with `O_CREAT|O_EXCL` semantics (in bash: `set -C; printf '%s\n' "$$" > .claude/sessions/.loop-active-<task-id>`). If the file already exists, abort with a clear message: another loop is running for this task.
   2. Acquires an advisory lock on `.claude/.bootstrap-state.json` via `flock` (POSIX) or an equivalent `FileLock`/`Mutex` on Windows. Holds the lock for the read-modify-write below.
   3. **When goal-supervised mode is also enabled,** checks that the task is not in `goal_in_flight` *and* that `.claude/sessions/.goal-active-<task-id>` does not exist (the sentinel check covers the window where `goal-loop.sh` has claimed its sentinel but not yet updated the state file). If either is present, releases the lock, removes the just-written `.loop-active-<task-id>` sentinel, and aborts: the task is in goal-supervised mode.
   4. Appends an entry `{task_id, iteration: 0, started_at, worktree_path?}` to `loop_in_flight`, writes the state file via the tmpfile-then-rename idiom (write to `.claude/.bootstrap-state.json.tmp`, `fsync`, then `rename`), and releases the lock.
3. **Loads the priming context.** Concatenates, in order: the task's `progress.md` (the status + failed-approaches ledger, read before the task brief so prior dead ends are visible), the task's `requirements.md` slice, the task definition itself, the loop-completion criteria, the most recent checkpoint (if resuming), and the project's standard `CLAUDE.md`.
4. **Invokes `claude -p`** with the priming context and a structured exit protocol.
5. **Watches for exit conditions** — clean exit with completion sentinel, tier-3 sentinel present, urgent escalation marker (`.loop-halt-<task-id>`), or max-iterations reached.
6. **Restarts on continuable exits** (tier-3-driven checkpoint exit, ordinary iteration exit) by re-priming with the latest checkpoint. Increments the iteration counter (and updates the matching `loop_in_flight` entry — same lock-and-rename protocol as step 2.4).
7. **Halts on terminal exits** — completion, max-iterations, or urgent escalation. Halting writes a final summary to `.claude/sessions/loop-final-<task-id>.md`, removes `.loop-active-<task-id>`, **removes its own entry** from the `loop_in_flight` list (same lock-and-rename protocol), and returns control to the operator.

**Race-safety summary.** The protocol's three concurrency guarantees — (a) a task is in at most one autonomous mode at a time, (b) the `loop_in_flight` / `goal_in_flight` lists never lose entries under concurrent updates, (c) `auto.sh` does not double-start — are enforced as follows. (a) is enforced by the `O_CREAT|O_EXCL` sentinel write *plus* the sibling-sentinel-and-list check under `flock` (the two together close the time-of-check-to-time-of-use window that the list-only check leaves open). (b) is enforced by `flock` on `.claude/.bootstrap-state.json` around every read-modify-write, plus the tmpfile-then-rename write idiom for the file itself. (c) is enforced by `auto.sh`'s `O_CREAT|O_EXCL` write of `.claude/queue/.run-active` at startup (see Phase 9.7). All three are concrete shell idioms with portable equivalents on Windows; the wizard generates the OS-appropriate form when writing the wrapper scripts.

**Deliverable contract for the wrappers (normative; adopted from proposal B-1, reading (b), at 2.2.0 — matching the shipped implementation).** The wizard emits `loop.sh`, `goal-loop.sh`, and `auto.sh` as **guarded fail-safe skeletons**, not complete unattended loops. The unattended-execution core — the `claude -p` iteration loop, the `*_in_flight` accounting lifecycle steps marked operator-completed, and `auto.sh`'s dispatch loop — is explicitly completed by the operator before first unattended use, guided by the skeleton's binding comment contract. The skeleton itself MUST already implement, and fail closed on, these invariants: refuse on a missing or ineligible task; honor both sentinel sets (root `.halt`/`.halt-hard` and the queue-scoped legacy sentinels) at startup; perform the race-safe claim (`O_CREAT|O_EXCL` sentinel + `flock`ed list check), refusing side-effect-free when the claim fails or `flock` is unavailable; dispatch no unattended agent work of its own (a bare skeleton run is a loud no-op); and never signal an in-flight `claude -p` on hard-halt (killing processes is the caller's job). The **binding comment contract** is normative surface: the emitted comments MUST enumerate (1) the full `exit_reason` value set from Recovery & State with one-line trigger conditions, so an operator-completed dispatch loop implements the whole enum rather than the subset the skeleton exercises; (2) the morning-after summary's required structure, including the `Ended because` line (code + one plain sentence, with the per-code renders named in the template); and (3) the usage-limit vs transient-failure split below, including the dispatch-invocation requirements it depends on; and (4) the **trajectory-retention** requirement — the operator-completed loop MUST retain each iteration's stream JSON (already produced: the dispatch instruction carries `--output-format stream-json --verbose`) at `.claude/logs/trajectory-<task-id>-<iter-n>.jsonl`, gitignored under the existing `.claude/logs/` rule, so an unattended run remains answerable after the fact ("why did it do that at 3am?"); a skeleton whose self-check finds retention disabled MUST fail loud, not silently proceed. **Pruning these files is part of the same operator obligation and is not inherited:** the 7-day state policy covers session-ID-namespaced state under `.claude/sessions/` and does not reach `.claude/logs/`, so the operator-completed loop MUST prune retained trajectories on a stated retention window (7 days matches the state policy) rather than assuming an existing mechanism does it. [Corrected at the v2.4.0 code fold: the v2.3.0 text asserted these files were "purged with the 7-day state policy", which no emitted artifact implements — a committed doc must not describe retention it does not perform.] OTel GenAI span emission is an **optional** export layer over these same files, explicitly not required; when the operator opts into telemetry export (TEL-01), `.claude/steering/telemetry.md` documents how to configure it against an operator-owned backend. Wizard-time trust-ramp deferral is an operational gate on *completing and running* the skeleton, not a statement that the emitted artifact is unfinished by accident.

**Infrastructure-error handling.** If `claude -p` exits with a non-zero status code that is *not* one of the three expected exit reasons (completion, tier-3, halt), the wrapper must first decide **which kind of failure it is**, because a usage-limit rejection and a transient infrastructure failure want opposite responses. The two are distinguished by the stream, not guessed from the exit code.

*Reading the signal.* The emitted skeleton's binding comments require the operator-completed iteration loop to dispatch `claude -p` with `--output-format stream-json --verbose` (the skeleton's dispatch instruction names these flags alongside `--worktree`) and to tail the newline-delimited event stream. Claude Code emits a `rate_limit_event` whenever rate-limit status changes. **[AR2-03] On the wire** — which is what a shell loop parses — the event is a stream line whose **top-level `type` is `"rate_limit_event"`**, carrying a nested `rate_limit_info` object whose load-bearing keys are **camelCase**: `status` (`"allowed"` | `"allowed_warning"` | `"rejected"`), `resetsAt` (a Unix timestamp in seconds — the authoritative moment the limiting bucket refills; may be absent), and `rateLimitType` (`"five_hour"` | `"seven_day"` | `"seven_day_opus"` | `"seven_day_sonnet"` | `"overage"`). (The Python Agent SDK's `RateLimitInfo` dataclass exposes the same fields snake_cased as `resets_at` / `rate_limit_type` — those are the names an SDK consumer such as Tessera sees, **not** the raw stream keys; this document's prose uses the snake_case names when speaking of the fields abstractly.) The loop MUST match the event by its top-level `type` field — never by substring-searching the stream, since an assistant message can contain the literal text `rate_limit_event` inside a string. The wrapper records the most recent `rate_limit_event` it saw before the exit. (This is the same class of stream-contract dependency as `api_retry` and `ResultMessage.total_cost_usd` — consumed as-emitted, never forked. If a future Claude Code build stops emitting the event, the wrapper falls back to the transient-failure path below and says so in the final summary, per `fail-loud-not-silent`.)

*Usage-limit rejection → reset-aware wait.* (Bound on the operator-completed loop via the skeleton comment contract; "the wrapper" below names the completed loop.) If the last observed `rate_limit_event` has `status: "rejected"` and a reset timestamp in the future, the exit is a **usage-limit rejection**, not an infrastructure failure. **[AR2-03]** A `rejected` event whose reset timestamp is absent or already past does **not** qualify — it takes the transient path below. When `usage_limit_wait: reset-aware` (the default), the wrapper: (a) computes `wait = (resets_at − now) + jitter`, where jitter is a uniform random `0..usage_limit_wait_jitter_seconds` added on top — never subtracted — because `resets_at` is a server hint that can read a touch short on the window boundary, and a fleet of workers must not all wake in the same millisecond; (b) if `wait > usage_limit_max_wait_seconds`, the wrapper does **not** sleep — it halts with `loop-final-<task-id>.md` recording a queue-visible `usage-limit-reset-abandoned` cause and surfaces the reset time to the operator, because a multi-hour unattended sleep is an operator decision, not a wrapper default; (c) otherwise it sleeps `wait`, then re-probes the **same** iteration without incrementing the iteration counter. The reset-aware wait does **not** count against the transient-failure retry budget below — waiting for a known reset is not a failure, and conflating them was the pre-v2.1.0 bug that burned the single infra retry on a multi-hour cap. **Do not compute your own reset time.** Honor `resets_at` as a floor plus jitter; never hardcode "+5h" or "+7d" — the buckets do not reset on the clock you would guess (the `seven_day` window has been observed resetting on a backend cron decoupled from a literal seven days), so a client-side projection will silently stall or wake into a fresh rejection. Set `usage_limit_wait: off` to disable the usage-limit branch entirely: **[AR2-02]** with `off`, a rejection-bearing exit is not special-cased — it is handled by the transient path below (sleep briefly, retry once, then halt), exactly as every non-expected exit was pre-2.2.0. This is appropriate for API-key billing with no hard cap, where a "rejection" is a per-minute 429 that the transient retry absorbs.

*Transient infrastructure failure → sleep-briefly, retry once, then halt.* If the exit is **not** a usage-limit rejection — network error, 5xx, a 529 overload, or a non-zero exit with no `rejected` rate-limit event — the wrapper keeps the original posture: on the first such exit it sleeps briefly (default: 30 seconds) and retries the same iteration without incrementing the iteration counter; on a second *consecutive* transient failure it halts with `loop-final-<task-id>.md` noting the cause and surfaces the issue to the operator. This avoids both burning iterations on transient outages and quietly looping forever on a persistent issue.

All three thresholds — `usage_limit_wait`, `usage_limit_max_wait_seconds` (default `21600`), `usage_limit_wait_jitter_seconds` (default `60`) — plus the transient sleep interval and retry count are configurable in `.claude/loop-config.md`. **Watchdog note [AR2-05: substrate-independent]:** the operator-completed loop can additionally set `CLAUDE_CODE_RETRY_WATCHDOG=1` on the `claude` subprocess so the CLI itself retries capacity errors through longer outages. This is a plain CLI environment variable, available on **any** conformant install regardless of `gate_substrate` (its behavior is documented as of Claude Code v2.1.199, below the seam runtime floor ≥ 2.1.210); the previous scoping of this note to `"sdk-callable"` installs was incorrect. The watchdog handles *in-request* stalls and is complementary to — not a replacement for — this *between-iterations* reset-aware wait, which is the layer that knows about the queue and the operator ceiling.

### How a typical iteration ends

It helps to be explicit about how the loop actually behaves, because two related-but-different mechanisms get described in this section and operators sometimes conflate them.

**The outer loop is the Ralph-style iteration loop.** The wrapper invokes `claude -p`, the agent works on the task within that single session — writes code, runs tests, edits files, may commit — and then the iteration ends. The wrapper inspects what happened and decides whether to start another iteration or stop. **Most iterations do not involve tier 3 at all.** Tier 3 is a recovery path for when context degrades within a single iteration; it is one of several ways an iteration can end, not the main mechanism.

There are four ways a single iteration can end. The wrapper distinguishes them by what sentinels are present after `claude -p` exits:

| What happened in the iteration | Sentinel(s) written | Wrapper's next move |
|---|---|---|
| Agent self-verified all completion criteria | `.loop-complete-<task-id>` | **Terminal:** exit the loop, write `loop-final-<task-id>.md`, success |
| Agent hit an urgent escalation criterion | `.loop-halt-<task-id>` (plus `.decision-pending-<session-id>`) | **Terminal:** exit the loop, alert operator |
| Tier-3 drift fired mid-iteration | `.drift-tier3-<session-id>` + a fresh `<timestamp>-checkpoint.md` | **Continuable:** next iteration primed from the checkpoint instead of the original brief |
| Iteration just ended naturally (tests still failing, more work needed, or agent decided this round was done) | none of the above | **Continuable:** next iteration primed from the original brief plus the current diff |

The fourth row is the typical case once a loop is mid-run. The agent makes progress in iteration 1, doesn't quite get all tests green, ends its turn; iteration 2 starts a fresh session, primed with the brief and the current state of the code, and continues. Iteration 3 likewise. Tests finally pass, reviewer subagent approves, agent writes the completion sentinel — first row, terminal exit. The whole task may run end-to-end without tier 3 ever firing.

**Tier 3 (third row) is a context-saturation safety net, not the main mechanism.** It exists so that a particularly long or ugly iteration — one that would have produced bad code if it kept going — gets cut short, the agent's work-so-far synopsized into a checkpoint, and the next iteration gets a fresh session window. From the operator's perspective, tier 3 inside loop mode is invisible: the wrapper handles the reset that the operator-only baseline requires `/clear`+`/resume` for. From the agent's perspective, tier 3 inside loop mode is "write a checkpoint, then end the turn" — it does not get to call any tool other than the checkpoint write, because Phase B's hard-block is still in effect. The wrapper's next iteration is what unsticks things.

**The fresh-session-per-iteration property is what makes the whole design work.** Each iteration gets a clean context window, so context bloat from earlier iterations doesn't accumulate across the loop. Files-on-disk and git history persist (that's where iteration-N's work lives for iteration-N+1 to read); session-internal context does not. This is also why the design uses `claude -p` (one prompt per session) rather than an in-session-stop-hook pattern: in-session looping reuses the same context window and would let bloat accumulate; per-iteration fresh sessions avoid that by construction.

### Architecture: cooperation with parallel decomposition (multiple worktrees)

Loop mode and the protocol's existing parallel-decomposition mechanism (multiple implementer worktrees running concurrently against different tasks) are designed to compose:

- Each worktree runs its own loop independently. Sentinel and log paths are per-task (`<task-id>` is the disambiguator), so concurrent loops do not collide on `.loop-active-*`, `decisions-log-*`, or `loop-final-*`.
- The `loop_in_flight` list in `.bootstrap-state.json` holds one entry per concurrently running loop (single-loop runs are a one-element list). The wrapper appends its own entry atomically at start and removes it at terminal exit.
- The `task-done` audio batching window (Phase 6.E, default 30 seconds) covers the common case of multiple loops completing close together — the operator hears one batched cue, not a torrent.
- **Constraint:** running more concurrent loops than the operator can review in the resulting decision-log batch defeats the point. Recommended starting concurrency: 2 loops max for the first week of loop-mode use, then expand based on review throughput. **When goal-supervised mode is also enabled,** the 2-concurrency budget applies to `loop_in_flight` and `goal_in_flight` *combined*, not to each list independently — see Recovery & State for the cross-mode concurrency rule. **When queue mode is also enabled,** the queue runner dispatches per-task wrappers within the same combined-concurrency cap (each dispatched task occupies one slot in either `loop_in_flight` or `goal_in_flight` via the wrapper); the runner's own `max_concurrent_tasks` setting in `auto-config.md` should not be set higher than the cross-mode cap. See Phase 9.7 for the queue-mode coordination contract.

### Architecture: cooperation with tier 3

Inside loop mode, tier 3 enforcement is *augmented*, not replaced (this is also documented in section 6.E):

- Tier 3 fires → existing tier-3 behavior runs (sentinel written, agent writes checkpoint, hard-block on subsequent non-checkpoint tool calls).
- The loop-mode-aware agent prompt instructs the agent that, after writing the checkpoint, it should **end its turn** (stop emitting tool calls) instead of waiting for the operator to run `/clear`+`/resume`.
- The wrapper sees `claude -p` exit, inspects sentinels, finds the tier-3 sentinel and a fresh checkpoint, and primes the next iteration with the new checkpoint instead of the original task brief.
- A new session starts (fresh session ID → the old `.drift-tier3-<old-session-id>` sentinel no longer matches → tool calls flow normally in the new session).

This means tier 3 in loop mode becomes a *self-healing context reset* rather than an *operator-required checkpoint*. The operator still gets the checkpoint file for post-hoc review but doesn't need to be present for the reset.

**A note on exit semantics:** the agent does not "emit a status code" — it simply ends its turn. The wrapper relies on the *combination* of `claude -p` exiting and the presence/absence of sentinels (`.loop-complete-<task-id>`, `.drift-tier3-<old-session-id>`, `.loop-halt-<task-id>`) to decide what to do next. This avoids requiring the agent to make a tool call from inside Phase B's hard-block, which it cannot.

### Architecture: cooperation with urgent escalations

The five urgent escalation criteria from `CLAUDE.md` remain hard-blocks even in loop mode:

- Do-not-touch file modification needed
- Secret encountered
- Hook block with non-obvious fix
- Dependency not on approved list
- Spec turned out to be wrong

When any of these fire inside loop mode, the agent writes the existing `.decision-pending-<session-id>` file (v1.5.0 mechanism), writes an additional `.loop-halt-<task-id>` marker, and exits. The wrapper sees the halt marker and exits the loop entirely — no restart. The operator returns to a halted loop with the decision-pending file ready for action.

### The decision log (new mechanism for non-urgent decisions)

**Naming clarification.** Three similarly-named artifacts coexist:
- `.claude/specs/<slug>/decisions.md` — within-feature non-obvious choices, written by the `decision-log` skill at any point during a task.
- `.claude/sessions/decisions-log-<task-id>.md` — per-loop-run autonomous-decision audit record, written by the implementer subagent's loop-mode variant during a loop iteration. **This is what "the decision log" refers to in the rest of this section.**
- The `decision-log` *skill* (Phase 7) — writes only to `decisions.md`. The loop-mode variant of the implementer writes directly to `decisions-log-<task-id>.md` as an inline behavior, not via the skill.

For *non-urgent* decisions (the in-chat-only category) — which would otherwise produce a chat message and wait for operator response — loop mode introduces the decision-log pattern:

- Agent encounters a non-urgent decision (two reasonable approaches with tradeoffs, ambiguous-but-resolvable acceptance criterion, etc.)
- Instead of producing chat output and waiting, the agent writes an entry to `.claude/sessions/decisions-log-<task-id>.md`
- Each entry contains: timestamp, decision question, options considered, choice made, justification, reversibility flag (cheap-to-undo / expensive-to-undo / one-way)
- Agent picks the choice it considers most defensible and continues
- After the loop run completes (or halts), the operator reviews the log
- For any logged decision the operator disagrees with: they edit the relevant code/spec, set a flag, and re-loop the task — the loop's first iteration in the re-run reads the override and proceeds

The "defensible default" criterion is **not** "best quality" or "most robust." Those framings produce over-engineering bias. The criterion is:

> **Pick the option that minimizes blast radius if wrong, and that is easiest to reverse if the operator disagrees post-hoc.**

This biases the agent toward conservative, undo-friendly choices — which is what an autonomous loop should do.

### The loop-eligibility classifier (recap from Phase 7)

`spec-decompose` applies the five-criterion test to each task and tags candidates as loop-eligible. The five criteria:

1. **Are acceptance criteria unambiguous?** EARS-formatted criteria with no missing preconditions → yes. "Should feel polished" → no.
2. **Is novelty low?** Standard CRUD on an existing model → yes. New cryptographic protocol → no.
3. **Is blast radius bounded?** Single file, single function, isolated module → yes. Touches authentication or money or data integrity → no.
4. **Are tests authoritative?** Acceptance criteria can be verified by automated tests → yes. Requires human judgment ("does this look right?") → no.
5. **Is rollback cheap?** Single commit, one file, easy revert → yes. Database migration, API contract change → no.

Tasks that score "yes" on all five are recommended loop-eligible. **The operator confirms or vetoes per task** — recommendations, not decisions. Tasks that score "no" on any criterion are operator-only by default. The classifier output is written into the task definition: `loop_eligible: true|false` and (if true) `loop_max_iterations: <integer>` (default 10).

### Completion criteria

The loop's completion check, run after each iteration, has two parts: a **four-criterion deterministic gate** and a **self-verification sentinel** written by the agent.

The deterministic gate requires all four:

1. **Tests green.** Project test command exits 0.
2. **Spec validation passes.** `/spec-validate` returns approval.
3. **Reviewer subagent approves.** The reviewer's structured output indicates "approve" rather than "issues."
4. **Spec gate passes.** Files in the diff are referenced by the active task.

The self-verification sentinel is a separate signal: the agent writes `.claude/sessions/.loop-complete-<task-id>` after confirming all four gates pass. The wrapper exits successfully only when the sentinel is present *and* all four gates have passed; the sentinel is the agent's self-attestation and is never inferred. If a gate did not pass or the sentinel is missing, the wrapper restarts the loop with the failure context primed. How the wrapper establishes that the four gates passed differs by mode — see the next paragraph.

In loop mode the wrapper inspects the sentinel as its primary check and trusts the agent's self-attestation that the four gates pass; in goal-supervised mode (Phase 9.6) the wrapper checks the four gates independently in addition to requiring the sentinel and the judge verdict. This is one of the two strengthenings goal-supervised mode adds.

### Max-iterations safety

Default: 10 iterations per task. Configurable in `.claude/loop-config.md`; recorded in the [Assumption Ledger](#assumption-ledger) as a model-generation-calibrated default. On max-iterations:

- Wrapper writes `.claude/sessions/loop-final-<task-id>.md` with full iteration history
- Plays the decision-required audio cue (operator attention needed)
- Exits non-zero
- Operator returns to a halted loop, reviews the iteration history, and decides: restart with adjusted scope, manually complete the task, or revert

**Max-iterations is the *primary* safety net per Ralph community wisdom. Completion criteria are the *success* signal. Don't conflate them.** A loop that hits max-iterations is not a failure of the protocol; it is the protocol working as designed.

### What the wizard generates when loop mode is opted in

- **`.claude/loop.sh`** — the wrapper script. Generated from a template; the operator approves before write. Made executable (`chmod +x`).
- **`.claude/loop-config.md`** — operator-tunable settings: default `max_iterations`, completion-criteria checks, classifier thresholds, audio-cue overrides, the transient-failure sleep interval and retry count, and the three usage-limit-wait keys — `usage_limit_wait` (`reset-aware` | `off`, default `reset-aware`), `usage_limit_max_wait_seconds` (default `21600`), `usage_limit_wait_jitter_seconds` (default `60`) — that govern the reset-aware wait in Phase 9.5's infrastructure-error handling. Format mirrors `audio-alerts.config`. Committed to the repo.
- **`.claude/sessions/decisions-log-<task-id>.md`** — written per loop run by the agent; decision history. Committed (operator-facing audit record).
- **`.claude/sessions/loop-final-<task-id>.md`** — written on terminal exit by the wrapper; iteration summary. Committed (operator-facing audit record). Includes a required `Trajectory` line linking the retained per-iteration `.claude/logs/trajectory-<task-id>-<iter-n>.jsonl` files.
- **`.claude/sessions/.loop-active-<task-id>`** — sentinel written by the wrapper at start; signals to the agent and the drift-detector cooperation hook that loop-mode behavior is active. Gitignored.
- **`.claude/sessions/.loop-complete-<task-id>`** — sentinel written by the agent on self-verified completion. Gitignored.
- **`.claude/sessions/.loop-halt-<task-id>`** — sentinel written by the agent on urgent escalation. Gitignored.
- **`spec-decompose` skill** — augmented with the five-criterion classifier (Phase 7).
- **Task definition schema** — gains `loop_eligible: true|false` and `loop_max_iterations: <integer>` fields (Phase 7).
- **`CLAUDE.md`** — gains a top-of-file conditional instruction loading the loop-mode behavioral addendum when `.loop-active-<task-id>` exists (Phase 8).
- **Drift-detector cooperation hook** — generated alongside the existing drift detector in Phase 6 (gated on the presence of `.loop-active-<task-id>` *or*, when goal-supervised mode is also enabled, `.goal-active-<task-id>` to avoid changing tier-3 behavior outside autonomous modes). The same hook serves both modes; the transformation behavior is identical.
- **Implementer subagent prompt** — gains a loop-mode-aware variant block (Phase 7 step 3). The reviewer subagent is **not** modified — it remains part of the deterministic gate.

### Risks and known failure modes

The wizard surfaces these to the operator before generating loop-mode artifacts:

- **Operator over-trusts loop mode and stops reviewing decision logs.** Mitigation: the loop's final summary explicitly enumerates how many decisions were logged and how many were marked expensive-to-undo. If decisions exist, the summary leads with "N decisions made autonomously, M of which are expensive to reverse — review before merging."
- **The classifier mis-classifies a task as loop-eligible.** Mitigation: operator confirms per task at decomposition time; the classifier surfaces *recommendations*, not *decisions*.
- **Defensible-default heuristic produces cumulative drift.** Each individual decision is reasonable; the sum of 12 cautious choices is over-engineered or under-engineered code that no one specifically asked for. Mitigation: the decision log makes this auditable; the reviewer subagent (still running inside the loop) catches some cumulative drift via its diff-vs-spec review.
- **Token cost balloons.** Loop iterations re-prime context every time, so each iteration pays the priming cost fresh. Ten iterations × full priming = real money. Mitigation: the `loop_max_iterations` cap (default 10), classifier biases toward smaller tasks. A future protocol version may add explicit cost caps; the current protocol does not.
- **Loop mode masks deeper protocol problems.** If a task can't be completed without 8 decision-log entries, the spec was probably underspecified. Mitigation: the loop's final summary highlights this — "decision log has N entries; consider whether the spec needs more detail before similar tasks are decomposed."
- **Hooks running in tight loops trigger filesystem write storms.** Tier 3 sentinels, decision logs, completion sentinels — all writing to `.claude/sessions/` rapidly. Mitigation: the existing 7-day state purge handles cleanup; the actual write rate is bounded by tool-call rate.

### AI actions

1. **Confirm the operator wants to proceed.** Restate the design principles, the bounded scope (per-task only), and the risks above. Get explicit confirmation before generating any loop-mode artifacts.
2. **Generate `.claude/loop.sh`** from the wrapper template, adapted to the project's shell environment (detected at Phase 0). Show the script to the operator before writing — security-relevant per Phase 6's checklist. Run the same hook security & correctness checklist (no `eval`, quoted paths, exit codes, executable bit set, `jq` available where required).
3. **Generate `.claude/loop-config.md`** with default `max_iterations=10`, completion-criteria checklist, and classifier thresholds. Operator can edit before approval.
4. **Augment `spec-decompose`** to add the five-criterion classifier step (already specified in Phase 7; this phase wires it in).
5. **Augment `CLAUDE.md`** with the loop-mode-active conditional addendum (already specified in Phase 8; this phase wires it in).
6. **Augment the implementer subagent definition** with the loop-mode-aware variant block (already specified in Phase 7 step 3; this phase wires it in). Confirm the reviewer subagent is **not** modified.
7. **Generate the drift-detector cooperation hook** alongside the existing drift detector. The hook is a small shim that checks for `.loop-active-<task-id>` and, if present, transforms the standard tier-3 deny message into the loop-restart instruction; otherwise it falls through to the standard tier-3 behavior. Show the script to the operator before writing.
8. **Update `.gitignore`** with the loop-mode sentinel paths (already specified in Phase 7 step 7; verify they were included if Phase 7 ran before this phase, or add them now).
9. **Recommend the smoke test.** If Phase 9 was run, recommend the third-stage smoke test (the loop-mode smoke). If Phase 9 was skipped, strongly recommend running the loop-mode smoke before relying on the wrapper for real work.
10. **Update state file.** Confirm `bootstrap_protocol_version: "2.0.0"` is set (Phase 0 wrote it; this phase does not change it). Confirm `loop_mode_enabled: true` is set (from Phase 0). Verify `loop_in_flight: []` is present from Phase 0's initial write (the wrapper will append/remove entries during loop runs).
11. Show all created and modified files. Ask: **approve / edit / start over**.

**Exit criteria:** `loop.sh` and `loop-config.md` exist and are approved. The classifier is wired into `spec-decompose`. The CLAUDE.md addendum is in place. The implementer subagent's loop-mode variant is in place. The reviewer subagent is unchanged (verify). The drift-detector cooperation hook is generated and tested. The operator has seen the risks and confirmed proceeding.

---

<a id="phase-9-6"></a>
## Phase 9.6 — Goal-Supervised Mode (Optional)

**Goal:** Install a sibling autonomous-iteration mode alongside loop mode, adding a small-model judge (Haiku by default) as an *advisory* signal on top of the existing deterministic gates. Opens a middle tier between fully-autonomous loop mode and operator-only. **Default: skipped.** Operators who declined at Phase 0 reach this section and skip past it; the rest of this section applies only when `goal_supervised_mode_enabled` is true.

Phase 9.6 is **independent of Phase 9.5**. A project may enable goal-supervised mode without loop mode, or both together, or neither. All four combinations are valid; the wizard runs only the phases the operator opted into.

**What goal-supervised mode is:** an opt-in per-task execution mode where the agent iterates on a single task in fresh-session-per-iteration fashion (preserving the context-hygiene win), and where after each iteration the wrapper invokes a small-model judge with the goal condition, the current diff, the agent's structured iteration summary, and the test output. The judge returns `{verdict, reason}`. The judge's yes/no is one input among several — never sufficient on its own. Three independent signals must all agree before the loop exits successfully: the agent's self-verification sentinel (`.loop-complete-<task-id>`), the deterministic four-criterion gate (tests green, `/spec-validate` passes, reviewer subagent approves, spec gate passes), and the judge's verdict.

**What goal-supervised mode is not:**
- **Not a "let Claude do everything" mode.** Like loop mode, goal-supervised mode runs one task at a time. It does not run an entire spec, an entire feature, or a PRD.
- **Not a replacement for loop mode.** Loop mode handles tasks whose acceptance criteria are fully test-authoritative, blast radius is bounded, and rollback is cheap. Goal-supervised mode handles a different class of task: tasks with a semantic acceptance component, or tasks whose blast radius or rollback profile fails one of the loop-mode criteria but whose goal is one-sentence-expressible. The two modes are sibling tracks, not alternatives — classified per task.
- **Not a quality maximizer.** The judge is advisory; the deterministic gates are still the backstop. Operators who want maximum quality stay operator-in-the-loop.
- **Not a judge-as-sole-gate option.** Even with a `--trust-evaluator` flag (which is not part of this design), removing the deterministic four-criterion gate would create a path for completed-looking-but-wrong code to merge. The whole protocol's value is in stacking independent gates.
- **Not a license to weaken escalation.** All five urgent escalation criteria are unchanged. Tier 3 enforcement is unchanged in semantics (the same self-healing restart augmentation from Phase 9.5 applies inside `goal-loop.sh` for fresh-session-per-iteration runs).
- **Not a route to model escalation on max-iterations.** A loop that hits max-iterations is a signal about the spec, not about the model. Escalating to Sonnet → Opus on iteration-cap-hit weakens the safety net (operator review point pushed back), worsens cost shape at exactly the wrong moment, and masks the protocol's "loop mode masks deeper problems" risk. The single defensible model-escalation pattern is `--investigate-disagreement`, opt-in and operator-initiated only (see "Completion logic" below).

### Design principles (the operator should understand these before opting in)

The five design principles from Phase 9.5 carry forward unchanged. Three new principles apply to goal-supervised mode:

- **The judge is advisory, not authoritative.** The deterministic four-criterion gate remains the gate. The judge's yes/no is one input among several, never sufficient on its own. This is the inverse of vanilla Claude Code `/goal`, where the judge's yes is the terminal condition.
- **The judge sees artifacts, not transcripts.** Because each iteration is a fresh session (preserving the context-hygiene win), there is no growing conversation for the judge to evaluate. The judge reads the persistent state — the git diff since loop start, the agent's structured iteration summary, the current test output — and renders a verdict on the goal condition. This is more reliable than evaluating in-session conversational text, which is the failure mode of in-session goal-tracking mechanisms.
- **Goal-supervised mode is a third tier, not a replacement.** Three execution modes now exist: loop mode (full autonomous, deterministic-only), goal-supervised mode (autonomous with judge), and operator-only. They are classified per task and selected by the operator per task.

### Architecture

```
PRD
 └─ spec (one feature)
     └─ task (vertical slice)
         ├─ loop-mode-eligible    → .claude/loop.sh           (Phase 9.5)
         ├─ goal-supervised       → .claude/goal-loop.sh      (this phase)
         └─ operator-only         → standard interactive flow
```

`spec-decompose` (augmented in Phase 7) classifies each task against the six criteria, producing one of four eligibility shapes. The recommendation rule for eligible-for-both tasks is also wired into `spec-decompose`. The operator confirms or overrides per task — recommendations, not decisions.

### Completion logic

A goal-supervised iteration is **terminal (success)** only when **all three** of the following hold:

1. The agent has written `.claude/sessions/.loop-complete-<task-id>` (self-verification sentinel — same mechanism as loop mode).
2. The deterministic four-criterion gate passes: tests green, `/spec-validate` approves, reviewer subagent approves, spec gate passes.
3. The judge returns `verdict: "yes"`.

**Disagreement handling:**

- *Conditions 1 and 2 hold, judge says no.* The wrapper does not exit. Logs an `evaluator-disagreement` entry to `.claude/sessions/decisions-log-<task-id>.md` with fields: `iteration`, `disagreement_type: "judge_says_no_despite_gates_passing"`, `judge_reason`, `agent_summary_excerpt`. Continues to the next iteration with the judge's reason in the feedback file.
- *Condition 2 fails, judge says yes.* Wrapper does not exit. Logs an `evaluator-disagreement` entry with `disagreement_type: "judge_says_yes_despite_gates_failing"`. Continues to the next iteration with diagnostic information about which deterministic gate failed.
- *Condition 1 missing, conditions 2 and 3 hold.* Natural-iteration-end case — the agent didn't self-verify, but everything else looks complete. Wrapper does not exit (agent self-verification is required, never inferred). Primes the next iteration with explicit instruction that completion appears reached and to self-verify.

Disagreement entries are operator-facing audit records. The operator reviews them on completion or halt. **Persistent disagreement of the same type across 3+ consecutive iterations** triggers the `goal-condition-suspect` terminal halt (see Termination conditions).

**Targeted investigation (the one model-escalation exception).** A disagreement-investigation flag (`--investigate-disagreement`) may be set by the operator when re-running a halted goal-supervised loop. When set, the next iteration runs with the Opus model (overriding the project's standard model assignment) for that iteration only, with explicit priming about the disagreement to investigate. This is **opt-in only** and **operator-initiated only** — never automatic. It is the single defensible model-escalation pattern in goal-supervised mode.

### Termination conditions

Four ways a goal-supervised loop can terminate:

| Condition | Inherited from loop mode? | Wrapper action |
|---|---|---|
| Completion (all three completion checks pass) | Modified — adds judge verdict to the existing gate | Terminal success. Write `loop-final-<task-id>.md`. |
| Max-iterations reached | Yes, unchanged | Terminal. Default 10. **No model escalation.** Plays decision-required audio cue. |
| Urgent escalation criterion fires | Yes, unchanged | Terminal. Same five hard-block criteria. `.loop-halt-<task-id>` written. |
| Persistent evaluator-disagreement (3+ consecutive iterations, same disagreement type) | **New** | Terminal. Writes `loop-final-<task-id>.md` with `halt_reason: "goal-condition-suspect"`. Operator review required before re-run. |

The fourth condition is the goal-supervised-specific failure signal. It surfaces a specific class of problem: either the goal condition was poorly worded (so the judge keeps saying no for a reason the agent can't address), or the deterministic gates and the judge are stably disagreeing (so one of them is wrong about this task). Both cases need human attention — not bigger models, not more iterations. Threshold is configurable in `goal-config.md` (`evaluator_disagreement_threshold`, default 3).

### Iteration-summary discipline

Every iteration in goal-supervised mode ends with the agent writing `.claude/sessions/.iteration-summary-<task-id>-<iter-n>.md` in a fixed structured format. The summary is the judge's primary judging surface; freeform agent prose is intentionally not included in the judge's view.

**Required format:**

```markdown
# Iteration <N> summary — task <task-id>

## Goal condition
<verbatim copy of goal_condition from task definition>

## Completion criteria status
- [ ] Tests green: <one-sentence evidence, e.g. "all 47 tests pass, including 3 new ones for this task">
- [ ] /spec-validate passes: <one-sentence evidence>
- [ ] Reviewer subagent approves: <one-sentence evidence, or "not yet invoked">
- [ ] Spec gate passes: <one-sentence evidence>
- [ ] Self-verified complete: <yes/no, with one-sentence basis>

## What changed this iteration
<2-5 bullet points describing the diff at a semantic level — what behavior changed, not which files>

## What I believe still needs work
<bullet points, or "nothing — believe this is complete">

## Notes for the evaluator
<optional one paragraph; intended to surface anything the diff alone wouldn't show>
```

Enforcement is via the iteration-summary enforcement hook generated in Phase 6. If the file is missing or fails format validation, the wrapper logs the failure and primes the next iteration with an explicit format reminder. Three consecutive format failures count as a `goal-condition-suspect`-class halt.

The structured format does two things: (1) gives the judge concrete checkbox-evidence to evaluate against rather than freeform text, and (2) makes "the agent lied in its summary" detectable in post-hoc operator review by comparing the summary against the actual diff and test output.

### Evaluator-feedback mechanism

Each iteration's judge response is appended to `.claude/sessions/.evaluator-feedback-<task-id>.md`, one entry per iteration, in this format:

```markdown
## Iteration <N> — <yes|no>
<reason text from judge, typically 1-3 sentences>

---
```

The next iteration's priming context includes the **most recent two entries** (not the full history — that would defeat the context-hygiene win of fresh-session-per-iteration). Two entries is enough for the agent to see "the judge has been saying no about X, then no about Y" and adjust; more would re-introduce the context-bloat problem loop mode avoids. History depth is configurable in `goal-config.md` (`evaluator_feedback_history_depth`, default 2). The full file is preserved for operator post-hoc review.

### What the wizard generates when goal-supervised mode is opted in

- **`.claude/goal-loop.sh`** — the wrapper script. Generated from a template; the operator approves before write. Made executable (`chmod +x`). Supported flags include `--investigate-disagreement` (opt-in only; see Completion logic above). On startup, the wrapper verifies the task is `goal_supervised_eligible`, then performs the same race-safe claim sequence as `loop.sh` (see Phase 9.5's "Race-safety summary"): atomically writes `.claude/sessions/.goal-active-<task-id>` via `O_CREAT|O_EXCL`, acquires the `flock` on `.claude/.bootstrap-state.json`, confirms the task is not in `loop_in_flight` and `.claude/sessions/.loop-active-<task-id>` does not exist (aborting and removing the just-written goal-active sentinel if either is present), appends to `goal_in_flight`, writes the state file via tmpfile-then-rename, and releases the lock. It then primes context (the task's `progress.md` status + failed-approaches ledger read first, task `requirements.md` slice, task definition with `goal_condition`, deterministic completion-criteria checklist, most recent two evaluator-feedback entries, most recent checkpoint if resuming from tier-3, project `CLAUDE.md`), and invokes `claude -p`. After each `claude -p` exit: reads the iteration summary, invokes the judge API (Haiku by default), appends the response to the feedback file, inspects exit state (sentinels + judge verdict + deterministic four-criterion gate), and either continues with re-priming or halts per the termination conditions above. **On terminal exit** (completion, max-iterations, urgent escalation, or persistent evaluator-disagreement), the wrapper writes the final summary to `.claude/sessions/loop-final-<task-id>.md` (with elapsed/turns/tokens/evaluator-calls and a `halt_reason` field that distinguishes goal-condition-suspect halts from the other terminations), removes `.claude/sessions/.goal-active-<task-id>`, **removes its own entry** from the `goal_in_flight` list (same lock-and-rename protocol), and returns control to the operator. Transient judge-API failures trigger retry-once-then-halt with the cause recorded distinctly in the final summary — same posture as transient `claude -p` failures. A `rejected` usage-limit `rate_limit_event` on either the `claude -p` call or the judge call is **not** a transient failure: it takes the reset-aware wait path from Phase 9.5's infrastructure-error handling (honor `resets_at` + jitter, ceiling at `usage_limit_max_wait_seconds`, halt with `usage-limit-reset-abandoned` if the wait is too long), and does not consume the transient retry.
- **`.claude/goal-config.md`** — operator-tunable settings: `max_iterations` (default 10), `evaluator_model` (default `haiku`), `evaluator_disagreement_threshold` (default 3), `evaluator_feedback_history_depth` (default 2), judge-API-failure retry posture, completion-criteria checklist, classifier thresholds, audio-cue overrides, and the same three usage-limit-wait keys as `loop-config.md` (`usage_limit_wait` default `reset-aware`, `usage_limit_max_wait_seconds` default `21600`, `usage_limit_wait_jitter_seconds` default `60`) — `goal-loop.sh` performs the identical reset-aware wait as `loop.sh`, distinguishing a usage-limit rejection from a transient judge-API or `claude -p` failure. **Blessed emitted extras (2.2.0, closing implementation Finding 1):** the emission additionally carries `infra_retry_seconds` (default 30) and `infra_max_consecutive_failures` (default 2) — the transient-`claude -p` posture mirrored from `loop-config.md`; `summary_failure_halt_threshold` (default 3) — the named key for the malformed-summary classifier threshold; `require_completion_sentinel` (fixed `true` — the never-inferred self-verification rule as a visible, non-negotiable setting); and `investigate_disagreement` (default `false` — the `--investigate-disagreement` opt-in). The judge-API-failure retry posture is deliberately **key-less**: retry-once-then-halt is fixed behavior documented in emitted comments, not operator-tunable — a key would invite retry-harder responses to what Phase 9.6 defines as a diagnostic signal. Audio-cue overrides remain named in `audio-alerts.config`, not here. Format mirrors `loop-config.md`. Committed to the repo.
- **`.claude/sessions/decisions-log-<task-id>.md`** — written per loop run by the agent; decision history including `evaluator-disagreement` entries. Committed (operator-facing audit record). Shared filename convention with loop mode.
- **`.claude/sessions/loop-final-<task-id>.md`** — written on terminal exit by the wrapper; iteration summary including elapsed/turns/tokens/evaluator-calls. Committed (operator-facing audit record). Includes the required `Trajectory` line (see loop mode) linking the retained per-iteration trajectory files. Shared filename convention with loop mode; the `halt_reason` field distinguishes goal-condition-suspect halts from the existing termination conditions.
- **`.claude/sessions/.goal-active-<task-id>`** — sentinel written by the wrapper at start; signals to the agent and to the drift-detector cooperation hook that goal-supervised mode is active. Gitignored.
- **`.claude/sessions/.iteration-summary-<task-id>-<iter-n>.md`** — written by the agent at the end of each iteration in the required structured format. Read by the judge and by the iteration-summary enforcement hook. Gitignored (the operator-facing aggregate signal is in `loop-final-<task-id>.md`).
- **`.claude/sessions/.evaluator-feedback-<task-id>.md`** — written by the wrapper after each judge call; appends `{verdict, reason}` entries. Read by the agent during next-iteration priming (most recent two entries). Gitignored.
- **`.claude/sessions/.loop-complete-<task-id>`** — written by the agent on self-verified completion. Gitignored. Shared filename convention with loop mode.
- **`.claude/sessions/.loop-halt-<task-id>`** — written by the agent on urgent escalation. Gitignored. Shared filename convention with loop mode.
- **`spec-decompose` skill** — augmented with the sixth criterion and recommendation rule (Phase 7).
- **Task definition schema** — gains `goal_supervised_eligible: true|false` and (if true) `goal_condition: "<string>"` fields (Phase 7).
- **`CLAUDE.md`** — gains the goal-supervised-mode-active conditional addendum (Phase 8).
- **Drift-detector cooperation hook** — generated or augmented (Phase 6) to recognize `.goal-active-<task-id>` markers in addition to `.loop-active-<task-id>`. Same transformation behavior in both modes.
- **Iteration-summary enforcement hook** — generated alongside the drift-detector cooperation hook (Phase 6).
- **Implementer subagent prompt** — gains the `goal_supervised` variant block (Phase 7). The reviewer subagent is **not** modified — it remains part of the deterministic gate.
- **`learnings/mode-selection.md`** — initialized empty; the calibration ledger for the recommendation rule (see Calibration below).

### Calibration mechanism

`learnings/mode-selection.md` is the calibration ledger for the recommendation rule. Initialized empty at this phase. After each completed task in an autonomous mode, the operator records a single per-task assessment:

```markdown
## <task-id> — <mode-used> — <date>
**Recommendation:** <what classifier recommended>
**Chosen:** <what operator picked>
**Felt right?** <yes / no — too autonomous / no — too cautious / yes but the judge was noisy / yes but the gates were stricter than needed>
**Notes:** <optional one-line>
```

After ~20 entries, the operator may invoke a calibration-review skill that surfaces the accumulated answers, highlights any classifier-recommendation/operator-choice divergences and any "felt wrong" patterns, and proposes adjustments to the recommendation rule's flip-properties for this specific project. The operator approves, vetoes, or refines. This is the same posture as the existing `learnings/` mechanism: the protocol provides starting structure, the operator refines over time.

### Risks and known failure modes

The wizard surfaces these to the operator before generating goal-supervised-mode artifacts:

- **Judge false positives are the dangerous failure mode.** False negatives mean a few extra iterations; false positives mean the judge says done when the spec wasn't met. The deterministic four-criterion gate is the backstop — never weaken it.
- **Iteration-summary discipline is load-bearing.** If the agent writes sloppy summaries, the judge judges from incomplete information. The structured format helps; operator review of summaries during the first 10–20 tasks helps more.
- **Persistent evaluator-disagreement halts are diagnostic signals, not failures.** When the wrapper halts with `goal-condition-suspect`, the right response is to review the goal condition wording and the disagreement log — not to retry harder.
- **Calibration takes time.** The recommendation rule for eligible-for-both tasks is a starting prior, not a tested heuristic. Don't trust it blindly for the first 10–20 tasks; trust it once you've seen the pattern hold for your codebase.
- **Cost shape is judge-call per iteration.** Negligible compared to main-model spend, but real. Monitor in early use; `goal-config.md` can rate-limit if needed.
- **Hook-and-API write storms.** Same mitigation as loop mode (7-day state purge; tool-call-rate-bounded write rate). The judge API call adds one external call per iteration; rate-limit accordingly via `goal-config.md` if needed.
- **Operator over-trusts the judge and stops reviewing summaries.** Mitigation: the loop's final summary explicitly enumerates how many evaluator-disagreement entries occurred and how many iterations the judge spent on which feedback themes. The structured iteration-summary format also makes "agent-lied-in-summary" detectable in post-hoc review.

### AI actions

1. **Confirm the operator wants to proceed.** Restate the design principles (judge is advisory, judge sees artifacts not transcripts, third tier not replacement), the bounded scope (per-task only, fresh-session-per-iteration preserved), and the risks above. Get explicit confirmation before generating any goal-supervised-mode artifacts.
2. **Generate `.claude/goal-loop.sh`** from the wrapper template, adapted to the project's shell environment (detected at Phase 0). Show the script to the operator before writing — security-relevant per Phase 6's checklist. Run the same hook security & correctness checklist (no `eval`, quoted paths, exit codes, executable bit set, `jq` available where required, judge-API credentials read from environment not hardcoded).
3. **Generate `.claude/goal-config.md`** with defaults: `max_iterations=10`, `evaluator_model=haiku`, `evaluator_disagreement_threshold=3`, `evaluator_feedback_history_depth=2`, judge-API-failure retry-once-then-halt, `usage_limit_wait=reset-aware`, `usage_limit_max_wait_seconds=21600`, `usage_limit_wait_jitter_seconds=60`, completion-criteria checklist, classifier thresholds. Operator can edit before approval.
4. **Verify the iteration-summary enforcement hook is generated** (already specified in Phase 6; this phase wires it in for goal-supervised mode). If Phase 6 ran before this phase, confirm the hook is present and executable; if it was deferred, generate it now and run the security checklist.
5. **Augment `spec-decompose`** to add the sixth criterion and the recommendation rule (already specified in Phase 7; this phase wires them in). If Phase 7 ran before this phase, confirm the augmentation is present.
6. **Augment `CLAUDE.md`** with the goal-supervised-mode-active conditional addendum (already specified in Phase 8; this phase wires it in). If Phase 8 ran before this phase, confirm the addendum is present.
7. **Augment the implementer subagent** with the `goal_supervised` variant block (already specified in Phase 7; this phase wires it in). Confirm the reviewer subagent is **not** modified.
8. **Verify the drift-detector cooperation hook recognizes `.goal-active-*` markers** (already specified in Phase 6 — the hook serves both modes via parallel marker recognition). If Phase 6 ran with only `loop_mode_enabled: true` and goal-supervised mode is being opted into later, regenerate or amend the hook so it recognizes both markers.
9. **Update `.gitignore`** with the goal-supervised-mode sentinel paths (already specified in Phase 7 step 7; verify they were included if Phase 7 ran before this phase, or add them now).
10. **Initialize `learnings/mode-selection.md`** as an empty calibration file with a header explaining its purpose (operators record per-task-completion whether the chosen mode felt right, accumulating evidence for refining the recommendation rule over time).
11. **Recommend the smoke test.** If Phase 9 was run, recommend the goal-supervised-mode (fourth-stage) smoke. If Phase 9 was skipped, strongly recommend running the goal-supervised smoke before relying on the wrapper for real work.
12. **Update state file.** Confirm `bootstrap_protocol_version: "2.0.0"` is set (Phase 0 wrote it; this phase does not change it). Confirm `goal_supervised_mode_enabled: true` is set (from Phase 0). Verify `goal_in_flight: []` is present from Phase 0's initial write (the wrapper will append/remove entries during goal-supervised runs).
13. Show all created and modified files. Ask: **approve / edit / start over**.

**Exit criteria:** `goal-loop.sh` and `goal-config.md` exist and are approved. The sixth criterion and recommendation rule are wired into `spec-decompose`. The CLAUDE.md goal-supervised addendum is in place. The implementer subagent's `goal_supervised` variant is in place. The reviewer subagent is unchanged (verify). The iteration-summary enforcement hook is generated and tested. The drift-detector cooperation hook is augmented to recognize the `.goal-active-*` marker. `learnings/mode-selection.md` is initialized. The operator has seen the risks and confirmed proceeding.

---

<a id="phase-9-7"></a>
## Phase 9.7 — Autonomous Queue Mode (Optional)

**Goal:** Install a coordination layer above the per-task autonomous mechanisms — a runner that dispatches pre-classified tasks from a backlog file in sequence to the appropriate per-task wrapper, while preserving every per-task and existing enforcement guarantee. **Default: skipped.** **Gated on:** `queue_mode_enabled: true` in `.bootstrap-state.json`. If false, skip entirely. **Additionally gated on** at least one of `loop_mode_enabled` or `goal_supervised_mode_enabled` being true; if neither is, refuse to set up queue mode and explain why — the runner has nothing to dispatch with no per-task mechanism enabled.

**What queue mode is:** an opt-in *coordination* layer that pulls pre-classified tasks from `.claude/queue/backlog.md`, dispatches each to its appropriate per-task wrapper (`loop.sh` for loop-mode tasks, `goal-loop.sh` for goal-supervised tasks), waits for terminal exit, and either continues to the next task or halts based on a small set of queue-level termination conditions. The per-task mechanisms are unchanged. The runner runs **no Claude session of its own** — it is bash plus optional small-model calls only at the morning-after summary-synthesis step.

**What queue mode is not:**
- **Not a per-task mechanism.** Queue mode does not run tasks; it dispatches the existing per-task wrappers. Loop mode and goal-supervised mode continue to behave identically inside or outside a queue run.
- **Not a "broader loops" mode.** The temptation to make individual loops wider — higher iteration caps, broader goal conditions, agent-chosen next steps — must be resisted. The "for hours or days" property lives at the coordination layer, not inside any single task's loop. Every safety property of the per-task mechanisms depends on tasks staying small and bounded.
- **Not a license to skip operator review.** The morning-after summary makes review tractable; it does not replace it. Operators who find themselves reviewing less as autonomy increases have inverted the safety model.
- **Not a license to skip the trust ramp.** Queue mode amplifies every per-task failure mode by the number of tasks it runs unattended. A 5%-per-task failure rate over 20 overnight tasks produces 1 expected failure. Operators who run unattended overnight in the first week ship problems that supervised use would have caught.
- **Not configurable to override urgent escalations.** The "urgent escalations halt the queue" rule is non-negotiable. An operator who wants this configurable has misunderstood the safety model.
- **Not a task-generation mode.** The runner does not invent tasks, decompose features autonomously, or modify classifications. All tasks come from `spec-decompose` with operator confirmation.
- **Not an infinite-running mode.** Even with no explicit budgets set, the queue terminates when the backlog is empty. There is no "wait for new tasks and continue" mode; that invites the operator-walks-away-forever pattern.

### Design principles (the operator should understand these before opting in)

The principles from Phase 9.5 (per-task scoping, opt-in per task, enforcement guarantees survive, decisions logged not skipped, the loop is bounded) carry forward unchanged. The principles from Phase 9.6 (judge advisory not authoritative, judge sees artifacts not transcripts, third tier not replacement) also carry forward unchanged. Four new principles apply at the coordination layer:

- **The runner does not work; it dispatches.** The autonomous queue runner contains no agent context, no judge calls (except optional summary synthesis), and no completion logic. It is a bash orchestrator that invokes the existing per-task wrappers and observes their terminal state. The runner being "dumb" is the property that makes its trust ramp manageable — there is very little new code that can go wrong.
- **The queue is the unit of autonomy, not any single task.** A queue run's "for hours or days" property is emergent from running many bounded tasks back-to-back, not from any single loop running longer. The queue's termination conditions are independent of any task's termination conditions and are the operator's primary safety net at this layer.
- **Urgent escalations halt the queue, not just the task.** When any task within a queue run halts on one of the five urgent escalation criteria (do-not-touch file, secret encountered, hook block with no fix, unapproved dependency, spec proved wrong), the queue runner halts immediately. These always require human attention; the queue does not continue past them. **This rule is not configurable.**
- **The morning-after summary is load-bearing.** A queue run produces many artifacts. If the operator must read them all to understand what happened, the queue has not saved time — it has shifted time from dispatching to reviewing. The queue-level summary is the artifact the operator actually reads; per-task artifacts are linked, not foregrounded.

### Architecture: the two-axis structure

Queue mode introduces a second, orthogonal axis to the existing per-task autonomous-mechanism axis:

```
                    Per-task mechanism (HOW each task runs)
                    ────────────────────────────────────────
                    operator-only    loop mode    goal-supervised

Coordination
mechanism
(WHEN tasks run)
─────────────
manual dispatch     baseline         loop.sh      goal-loop.sh
(operator runs                       per task     per task
each task)

queue dispatch      paused*          auto.sh      auto.sh
(runner dispatches                   dispatches   dispatches
in sequence)                         loop.sh      goal-loop.sh
```

\* Operator-only tasks in the queue are skipped by the runner — never auto-dispatched (that would defeat the point of classifying them operator-only). The runner continues dispatching other independently-ready tasks around them. The operator handles the skipped task interactively, defers it, or removes it from the queue between or after runs. The runner only pauses when there is *no* independently-ready work left and at least one task is awaiting operator action.

A project may enable any combination of the per-task mechanisms and the coordination layer. Queue mode requires at least one per-task mechanism to be enabled — there must be something to dispatch. Beyond that, the modes compose freely: a single queue run may include some loop-mode tasks and some goal-supervised tasks mixed in any order, dispatched to the appropriate per-task wrapper based on each task's classification.

### Architecture: the runner

The runner lives at `.claude/auto.sh` (or a per-OS equivalent generated by the wizard — PowerShell on Windows, the same shell idiom on macOS/Linux). Same security-review posture as `loop.sh` and `goal-loop.sh` (no `eval`, quoted paths, exit codes, executable bit set, `jq` available, signal traps for SIGINT/SIGTERM).

The runner's main loop:

1. **Startup checks.** Confirm at least one per-task mechanism is enabled. Read `.claude/queue/backlog.md`. Verify queue file format is valid. Check for `.claude/queue/.run-active` from a prior run: if present, **read the PID recorded in the sentinel and test whether that process is still alive** (e.g., `kill -0 <pid>` on POSIX). If the PID is alive, refuse to start — a runner is already running, and starting a second one would dispatch tasks past the combined-concurrency cap without any single runner noticing (see Recovery & State for the cross-mode concurrency rule). If the PID is dead, the sentinel is stale from a crashed prior run — alert the operator with the recorded start timestamp and ask before clearing it and continuing. Sentinel-presence alone is not a sufficient check; PID-liveness is the actual signal. **Race protection for simultaneous invocations.** Two `auto.sh` processes started within the same second must not both pass this check. After the PID-liveness check decides the sentinel is absent or stale-and-cleared, the runner writes the new `.claude/queue/.run-active` via `O_CREAT|O_EXCL` semantics (in bash: `set -C; printf '%s\n%s\n' "$$" "$(date -Iseconds)" > .claude/queue/.run-active`, which fails if the file already exists). A failed `O_CREAT|O_EXCL` indicates a concurrent runner won the race — abort with a clear message and exit non-zero rather than overwriting.

   **Per-task recovery from stale "In flight" entries.** After clearing a stale `.run-active`, if `backlog.md`'s "In flight" section is non-empty, the prior runner crashed mid-dispatch and one or more per-task wrappers may have outlived it. For each task listed in "In flight": check whether its per-task active sentinel (`.loop-active-<task-id>` or `.goal-active-<task-id>`) exists and corresponds to a live wrapper process. If the wrapper is alive, refuse to start — the operator must let the in-flight task complete (or kill the wrapper) before restarting the runner. If the wrapper is dead but a final summary (`loop-final-<task-id>.md`) exists, treat the task as terminated and move it to "Completed this run" or "Halted this run" based on the recorded classification before entering the main loop. If the wrapper is dead with no final summary, the wrapper crashed too — alert the operator, move the task to "Halted this run" with a recovery note, and continue.

   **Close out dangling `queue_runs_history` entry.** If `queue_runs_history` in `.bootstrap-state.json` has a most-recent entry with `end_timestamp: null` (the placeholder written at run start), the prior runner crashed before its terminal-exit cleanup. Update that entry in place: set `end_timestamp` to the recorded `.run-active` start timestamp plus the elapsed wall-clock since (best-effort; the exact crash time is unknown), and set `exit_reason: "infrastructure-failure-crash-recovery"`. Do not append a new entry for the *current* run until the recovery is complete — the current run gets its own append after recovery finishes.

   **Dependency-graph validation.** Before entering the main loop, walk all tasks in "Ready to run" and build the `blocked_by` graph (treating tasks in "Operator-only" and "Deferred" as nodes with no outbound edges). Detect cycles by Tarjan's algorithm or equivalent. If any cycle is found, refuse to start and report the cycle to the operator — a cycle cannot be resolved by skip-and-continue, since each task in the cycle is blocked on another that is also waiting. Cycles are operator-introduced (`spec-decompose` does not produce them by construction); the runner does not attempt to break them.
2. **Write `.claude/queue/.run-active`** with the run's start timestamp, the operator-set budgets (time, tokens, tasks), and the runner's PID. Append a new entry to `queue_runs_history` in `.bootstrap-state.json`.
3. **Initialize the run-summary file** at `.claude/queue/run-summary-<timestamp>.md`. Empty template; the runner populates it incrementally as tasks complete.
4. **Main dispatch loop.** The runner's idle behavior is event-driven with a bounded periodic fallback. It does not busy-loop; it waits on events (per-task wrapper completion, signal, sentinel write) and re-scans the queue at each event or every `scan_interval_seconds` (default 30s, configurable in `auto-config.md`), whichever comes first. Each pass through the loop is one **dispatch decision point** — that is when operator edits to `backlog.md`, mid-run sentinel writes (`.halt`, `.resume`), and completed-task transitions are read.
   - **Scan candidates.** Read `backlog.md`. Walk all tasks in the "Ready to run" section in priority order (high before normal before low), then in queue-file order within a priority. For each candidate, evaluate ready-to-run eligibility (see "Ready-to-run determination" below). Operator-only tasks (in the "Operator-only" section) are **never candidates** — they are an inert parking lot, scanned only to compute transitive blockers.
   - **Skip-and-continue, not pause-and-block.** If a candidate is not yet ready because its `blocked_by` references a task that is still in flight, not yet completed, sitting in "Operator-only," or sitting in "Deferred," **skip it and try the next candidate**. A single operator-only task or a single blocking dependency at high priority must not stall lower-priority tasks that are independently ready. Priority is a **preference among ready candidates**, not a reservation against lower-priority work — if the highest-priority task in "Ready to run" is not dispatchable right now but a lower-priority one is, the runner dispatches the lower-priority task rather than stalling.
   - **Distinguish idle reasons.** After the scan, the runner is in exactly one of these states:
     - **Dispatchable candidate found** → check concurrency slot; if a slot is free, dispatch; if not, transition to *wait-on-slot-free*.
     - **No dispatchable candidate, tasks in flight, no operator action pending** → *wait-on-completion*. Block on per-task wrapper completion or the scan-interval timer, whichever comes first. Re-scan on either event.
     - **No dispatchable candidate, no tasks in flight, at least one task awaiting operator action** (operator-only task in the queue, or "Ready to run" task transitively blocked on one) → *pause for operator*. Write a pause message to the run-summary enumerating which tasks are awaiting which operator action, then block on `.resume` sentinel write, re-invocation of `auto.sh`, signal, or budget exhaustion.
     - **No dispatchable candidate, no tasks in flight, all remaining tasks are in "Deferred" with no operator-actionable predecessor** → exit terminal with `exit_reason: "deferred-only-remaining"` (not terminal-success — there is residue worth surfacing in the morning-after summary).
     - **Queue is fully drained** (nothing in "Ready to run," nothing in flight, nothing operator-actionable, nothing deferred) → exit terminal-success with `exit_reason: "queue-empty"`.
   - **Budget checks** are evaluated at the top of every scan and during *wait-on-completion* on every scan-interval tick. If any budget is exhausted, exit terminal with the corresponding `exit_reason`.
   - **Dispatch.** Invoke the appropriate per-task wrapper (`loop.sh` for loop-mode tasks, `goal-loop.sh` for goal-supervised tasks) in a new worktree or shell as appropriate. Record the task in the queue file's "In flight" section. Continue scanning for additional dispatchable candidates until concurrency is full or no more candidates remain.
   - **On per-task termination.** Read its `loop-final-<task-id>.md`. Classify the termination (success / max-iterations / goal-condition-suspect / urgent-escalation / other). Update the queue file (remove from "In flight"; add to "Completed this run" or "Halted this run"). Append a one-block entry to the run-summary file. **Re-scan the queue** — a completed task may unblock downstream candidates; a halted task transitively blocks its dependents (record them under "Did not run — blocked on halted predecessor" in the run-summary). Then check whether the termination should halt the queue at the queue level (see "Termination conditions" below). If yes, exit. If no, continue the main loop.
   - **Read-coherence within a scan.** A single scan reads `backlog.md` once at its start and treats that snapshot as authoritative for the duration of that scan. As tasks are dispatched within the scan, the runner tracks the dispatches in an in-memory delta against the snapshot so a single scan does not reconsider an already-dispatched task. Tasks that complete *during* a scan are observed at the next scan, not mid-scan. This avoids race-induced inconsistency within one dispatch decision; the bounded scan interval guarantees observations are never stale by more than `scan_interval_seconds`.
5. **On any terminal exit:**
   - Finalize the run-summary file with overall statistics and recommended morning actions.
   - Remove `.claude/queue/.run-active`.
   - Update `queue_runs_history` in `.bootstrap-state.json` with `end_timestamp` and `exit_reason`.
   - Play the appropriate audio cue (queue-complete, queue-halted, queue-needs-attention).
   - Exit. Return control to the operator.

**Infrastructure-error handling.** Same posture as the per-task wrappers. Transient wrapper-invocation failures (the wrapper itself failed to start, not a per-task failure) trigger a brief sleep + retry. Two consecutive infrastructure failures halt the runner with diagnostic output. **A per-task wrapper exiting on a usage-limit rejection is not a runner-level infrastructure failure** and must not be counted toward the two-consecutive threshold: a dispatched wrapper that performed its own reset-aware wait (Phase 9.5) and then either completed or halted with `usage-limit-reset-abandoned` has behaved correctly, not failed. **[AR2-01] When the runner observes a dispatched task halt with `usage-limit-reset-abandoned`, the run is terminal at the queue level:** the runner performs the same graceful shutdown as the signal row (waits for in-flight tasks to reach an iteration boundary, finalizes artifacts) and writes `exit_reason: "usage-limit-reset-abandoned"`, propagating the halting task's limiting bucket and reset time into the `Ended because` line. The halt is counted toward **neither** the three-consecutive-halts threshold **nor** the runner's infrastructure-failure threshold. Rationale: the cap is account-level — every task the runner would dispatch next shares it, so continuing dispatches into a known-rejected bucket manufactures a cascade of abandon halts that would terminate as `three-consecutive-halts`, whose documented semantics (a diagnostic about queue health) mislabel a healthy account simply at its cap, and would lose the reset time from the run summary. **[AR2-09c] The runner's own transient posture (brief sleep + retry; two consecutive runner-level failures → halt) is deliberately key-less** — `auto-config.md` carries budget keys but no runner-level `infra_*` keys, matching the judge-retry precedent: a runner-tier retry knob would invite retry-harder responses to what this phase defines as failures of the runner's own machinery. Only failures of the runner's *own* machinery — failing to launch a wrapper, failing to read or write the queue file, failing to acquire the state-file lock — count toward the runner's infrastructure-failure threshold.

**Signal handling.** The runner traps SIGINT and SIGTERM. On signal: wait for any in-flight per-task wrappers to reach their next iteration boundary (or hard-kill them with a configurable timeout), update the queue file to record the interrupt, finalize the run-summary, remove the run-active sentinel, exit cleanly.

**Manual halt.** Dropping a `.claude/queue/.halt` sentinel file causes the runner to halt at the next dispatch decision point. Useful for operators who want to stop the runner without sending a signal.

### Architecture: the queue file

The queue lives at `.claude/queue/backlog.md`. Operator-authored (every entry results from `spec-decompose` plus operator confirmation), persistent (committed to the repo), and editable between runs. Format:

```markdown
# Project backlog

## Queue policy
- max_concurrent_tasks: 2
- scan_interval_seconds: 30
- pause_on_max_iterations: false  # continue to next task; flag for review
- pause_on_goal_condition_suspect: false  # continue to next task; flag for review
- consecutive_halt_threshold: 3
# Non-configurable invariants (shown for transparency; not settings):
#   - Operator-only tasks are always skipped by the runner (never auto-dispatched).
#   - The runner always pauses (does not terminate) when only operator action could unblock further work.
#   - Urgent escalations (the five urgent-escalation criteria) always halt the queue terminally.

## Ready to run
- [ ] task-101 — Add created_at to orders — goal-supervised — priority: normal
- [ ] task-102 — Add updated_at to orders — goal-supervised — priority: normal — blocked_by: task-101
- [ ] task-103 — Refactor order-listing query — loop-mode — priority: low

## Operator-only (skipped by runner)
- [ ] task-104 — Auth provider migration — operator-only — priority: high

## In flight
<populated by runner at dispatch; cleared at terminal exit>

## Completed this run
<populated by runner at terminal-success exit; cleared at run start>

## Halted this run (needs review)
<populated by runner at non-success terminal exit; cleared at run start>

## Deferred
- [ ] task-105 — UI redesign — operator-only — priority: low — note: "waiting on design review"
```

Each task entry's fields come from the existing task definition (`loop_eligible`, `goal_supervised_eligible`, `goal_condition`, `blocked_by`, priority). The queue file is generated at decompose time (Phase 7) and updated by the runner during execution. Operators can edit it directly between runs to reorder priorities, add deferred-tag notes, or remove tasks. The runner reads the file at startup and refreshes its view periodically; mid-run edits are honored at the next dispatch decision point.

**Authority over queue policy values.** The `## Queue policy` block in `backlog.md` and the queue-policy fields in `.claude/auto-config.md` define the same settings. **`backlog.md` is authoritative** — the policy block in the queue file is the runtime source of truth for that queue. `auto-config.md` holds the *project-level defaults* that `spec-decompose` uses when initializing the policy block of a new `backlog.md`, and that the wizard uses when generating the initial skeleton; once the policy block exists in `backlog.md`, the runner reads from `backlog.md` and ignores divergences in `auto-config.md` until the operator re-syncs them. Operators changing a default mid-project should edit both, or edit `backlog.md` and accept that future skeleton regenerations will use the stale `auto-config.md` defaults until updated.

**Non-configurable invariants.** Three behaviors are not configurable and are not exposed as flags in `auto-config.md` or `backlog.md`'s policy block: (1) operator-only tasks are always skipped by the runner — never auto-dispatched — because auto-dispatching would defeat the classification; (2) the runner always pauses (rather than terminating) when the only thing that could unblock further work is operator action, because terminating would lose unfinished queue state; (3) urgent escalations (the five urgent-escalation criteria) always halt the queue terminally, because continuing past one would amplify a known-bad condition. The invariants are stated only in this section and as comments in the queue-policy block; the runner has no code path to disable them.

### Ready-to-run determination

A task is *ready to run* when **all** of the following hold:

- The task appears in the queue's "Ready to run" section (not "Deferred," not "Operator-only," not "In flight," not "Completed").
- All tasks listed in the task's `blocked_by` field have terminated successfully in the current or a prior queue run, or have been manually completed (the operator marks them "Completed" in the queue file by hand). A `blocked_by` reference to a task still in flight, a task in "Operator-only," or a task in "Deferred" leaves this task **not ready** — the runner skips it for now and tries the next candidate.
- The task's mode is enabled at the project level (loop-mode tasks require `loop_mode_enabled: true`; goal-supervised tasks require `goal_supervised_mode_enabled: true`).
- A concurrency slot is available.

If multiple tasks are ready, the runner dispatches in priority order (high before normal before low), and within a priority in queue-file order (top-to-bottom). Priority levels are operator-set at decompose time. **Priority is a preference, not a hard barrier** — if the highest-priority ready task cannot be dispatched right now (because it is blocked on a not-yet-completed predecessor, for instance) but a lower-priority task is independently ready, the runner dispatches the lower-priority task rather than stalling. The alternative — letting a single blocked high-priority task halt all lower-priority work — would defeat the queue's purpose.

**Operator-only tasks and tasks transitively blocked on them.** Operator-only tasks (in the "Operator-only" section) are never ready-to-run candidates; the runner walks past them entirely. Tasks in "Ready to run" whose `blocked_by` references an operator-only task (or transitively, a chain ending in one) are skipped on each scan — they're not dispatchable until the operator handles the predecessor. The runner records both classes in the run-summary's "Did not run" section so the operator can see at morning what's awaiting their action and what's downstream of it.

**The pause condition.** The runner pauses (rather than terminating) only when *all* of these hold simultaneously: no task in "Ready to run" is currently dispatchable, nothing is in flight, and at least one task is awaiting operator action (operator-only task in the queue, or "Ready to run" task transitively blocked on one). At that point the runner has nothing to do but wait. It writes a pause message to the run-summary enumerating what is awaiting which operator action, then waits for `.claude/queue/.resume`, a re-invocation of `auto.sh`, or budget exhaustion. If every remaining task is in "Deferred" with no operator-actionable predecessor, the runner exits with `exit_reason: "deferred-only-remaining"` (not terminal-success — the operator should see the residue in the morning-after summary and decide whether to undefer).

**Operator hand-off protocol.** When the runner is paused for operator action, the operator's resolution path for each pending task is:
- **Resolve an operator-only task by hand.** Run the task interactively (manually invoke `loop.sh`, `goal-loop.sh`, or just do the work). When done, edit `backlog.md` to **move the task line from the "Operator-only" section to the "Completed this run" section**, preserving the task ID. Downstream tasks with `blocked_by: [<this-task-id>, ...]` will become ready on the next scan.
- **Defer an operator-only task.** Move the task line from "Operator-only" to "Deferred"; add a `note:` field explaining why. Downstream tasks remain blocked until the operator either undefers or removes the task; the runner records them as transitively blocked on a deferred predecessor.
- **Remove an operator-only task.** Delete the task line from `backlog.md` entirely. The runner will, on the next scan, see downstream tasks' `blocked_by` referencing a now-missing task ID; treat such references as resolved (the predecessor is gone — there is nothing to wait for) and the downstream task becomes ready. This is a permissive interpretation chosen because the alternative (refusing to start any task whose `blocked_by` references a non-existent task) would treat a typo or a deletion as an unrecoverable error.
- **Resume the runner.** After any of the above, write `.claude/queue/.resume` to the queue directory (`touch .claude/queue/.resume`) or re-invoke `auto.sh`. The runner consumes the `.resume` sentinel (deletes it after observing) and immediately re-scans. The runner does not re-read `backlog.md` between scans except when triggered by `.resume`, a per-task completion, or the scan-interval timer — so the edit must precede the `.resume` write to be observed.

### Termination conditions

The queue runner has its own termination conditions, distinct from per-task termination conditions:

| Condition | Runner action |
|---|---|
| Queue empty — all tasks completed, nothing in flight, nothing deferred | Terminal success. `exit_reason: "queue-empty"`. |
| All "Ready to run" candidates completed; only "Deferred" tasks remain with no operator-actionable predecessor | Terminal. `exit_reason: "deferred-only-remaining"`. Distinct from `queue-empty` so the morning-after summary surfaces the residue. |
| Per-task wrapper halted with terminal-success | Continue to next task. |
| Per-task wrapper halted with max-iterations | Continue by default (configurable via `pause_on_max_iterations`). Log to "Halted this run" section. |
| Per-task wrapper halted with `goal-condition-suspect` | Continue by default (configurable via `pause_on_goal_condition_suspect`). Log to "Halted this run" section. |
| Per-task wrapper halted with **urgent escalation** (the five urgent-escalation criteria) | **Terminal at the queue level.** Always. Not configurable. The runner does not continue past urgent escalations. |
| Three consecutive task-level halts (of any non-urgent kind) within the run | Terminal. Diagnostic signal that something's wrong with the queue itself — wrong classifications, broken dependencies, environmental drift. Threshold configurable via `consecutive_halt_threshold` (default 3). |
| No dispatchable work remains; at least one task is awaiting operator action (operator-only task, or "Ready to run" task transitively blocked on one) | **Pause, not terminal.** Runner waits indefinitely (or until time budget exhausted) for operator action — handling the operator-only task, marking it complete, deferring, or removing it. While paused, the runner consumes no concurrency slots and continues to respect signal traps. |
| Operator-set time budget exhausted | Terminal. |
| Operator-set token budget exhausted | Terminal. |
| Operator-set task budget exhausted | Terminal. |
| SIGINT, SIGTERM, or `.claude/queue/.halt` sentinel | Terminal. Graceful shutdown — wait for in-flight tasks to reach an iteration boundary, finalize artifacts. |
| Infrastructure failure (two consecutive runner-level failures, not per-task) | Terminal with diagnostic output. |
| A dispatched per-task wrapper halted with `usage-limit-reset-abandoned` **[AR2-01]** | **Terminal.** Graceful shutdown (as the SIGINT/sentinel row). `exit_reason: "usage-limit-reset-abandoned"`, propagated from the task halt; the `Ended because` line names the limiting bucket and reset time. Counted toward neither the three-consecutive-halts threshold nor the infrastructure-failure threshold — see "Infrastructure-error handling" below. |

The urgent-escalation-halts-queue rule is non-negotiable and explicitly not configurable. The three-consecutive-halts rule is the queue-level equivalent of `goal-condition-suspect`: not a failure of the runner, but the runner working correctly and surfacing a higher-order problem.

### Concurrency

The runner can dispatch multiple tasks concurrently in separate worktrees, the same way Phase 9.5's parallel decomposition supports for loop mode. Constraints:

- **`max_concurrent_tasks` cap** in `auto-config.md`, default 2 to match existing parallel-decomposition guidance.
- The runner dispatches a new task whenever a slot frees up; it does not try to maximize utilization.
- Concurrent tasks may be in different modes (one loop-mode, one goal-supervised). The runner does not require homogeneity within a concurrency batch.
- **Dependency-respecting:** a task with `blocked_by: <task-id>` does not become ready-to-run until its blocker terminates successfully. The runner respects this strictly.
- **Worktree assignment:** the runner assigns a worktree per concurrent task, following the existing parallel-decomposition worktree mechanism. Worktree numbers cycle as slots free.

**Review-burden ceiling.** The runner does not enforce a review-burden ceiling, but the morning-after summary makes the cumulative review burden visible. Operators should not raise `max_concurrent_tasks` above the level at which they can review the resulting artifacts in their next session. The recommendation from loop-mode practice — "recommended starting concurrency: 2 for the first week of use, then expand based on review throughput" — applies here too, with "first week" replaced by "first four weeks" given the higher unattended-time stakes. See the Recovery & State section for the cross-mode concurrency rule when manual dispatch and queue dispatch are interleaved.

### The morning-after summary

The single most important operator-facing artifact of queue mode. Written to `.claude/queue/run-summary-<timestamp>.md`, populated incrementally during the run and finalized at terminal exit.

> **[AR2-09a] Deferred at 2.2.0 — no emitted run-summary template file (ships-with-TODO).** The required structure below is bound only through `auto.sh`'s comment contract; the wizard emits no standalone template artifact. Cost of deferral: an operator completing the runner can drift from the required structure with no emitted reference file to diff against — mitigated by the comment-contract enumeration and the `test_usage_limit_contract` string assertions. Revisit when the runner's dispatch loop itself is promoted from skeleton to emitted code.

Required structure:

```markdown
# Autonomous queue run — started <T>, ended <T>, elapsed <duration>
Ended because: `<exit_reason>` — <one plain sentence: what stopped the run and the immediate next step; for `urgent-escalation`, name the pending-decision note to open; for `usage-limit-reset-abandoned`, name the limiting bucket (`rate_limit_type`) and the reset time (`resets_at`) so the operator knows when re-running will make progress>

## Headline
<one-line summary: "N tasks attempted; X completed cleanly, Y halted for review, Z urgent escalations">

## Run statistics
- Total tasks attempted: N
- Completed cleanly: X
- Halted on max-iterations: A
- Halted on goal-condition-suspect: B
- Halted on urgent escalation: C
- Total iterations across all tasks: I
- Total tokens (main model + judge): T_main / T_judge
- Total decisions logged: D (E flagged expensive-to-undo)
- Total evaluator-disagreement entries: F
- Budgets consumed: time X% / tokens Y% / tasks Z%

## Completed cleanly (review before merging)
- task-101 — Add created_at to orders — 4 iterations — goal-supervised — [link to loop-final]
- task-103 — ...

## Halted — needs operator attention
- task-107 — Refactor auth middleware — max-iterations, 10 iterations — loop-mode
  Likely cause based on iteration history: <one-paragraph synthesis>
  [link to loop-final, decisions-log]
- task-110 — ...

## Did not run
- task-115 — Auth provider migration (operator-only) — skipped, awaiting operator
- task-116 — UI redesign (blocked_by: task-110, which halted) — blocked on halted predecessor
- task-117 — Add SSO config UI (blocked_by: task-115, operator-only) — transitively blocked on operator-only predecessor

## Decisions requiring operator review
Aggregated from all per-task decisions-log files in this run:
- task-103 / iteration 5: chose to introduce a new helper function rather than inline (cheap to undo)
- task-106 / iteration 2: chose snake_case for the new column name based on existing convention (expensive to undo if convention is wrong)
- ...

## Recommended morning actions
1. Review task-107 spec — likely ambiguity around session-vs-token boundary
2. Review the 1 expensive-to-undo decision in task-106
3. Decide whether to attempt task-110 manually or rewrite the goal condition
4. Resume queue after handling operator-only task-115
```

The "Likely cause based on iteration history" synthesis and the "Recommended morning actions" list may be produced by a small-model call at queue-termination time (Haiku, same as the goal-supervised judge), reading the per-task artifacts and synthesizing. This is the runner's one optional Claude-context use; if the operator prefers a no-synthesis posture, `auto-config.md` can disable it (`summary_synthesis_enabled: false`) and the summary surfaces the raw data only.

The summary is committed to the repo. It serves as the audit record of the queue run and the operator's primary review surface. Per-task reasoning/tool trajectories are not inlined here; each linked `loop-final-<task-id>.md` carries a `Trajectory` line to the retained `.claude/logs/trajectory-*` files, which is where an unattended run's step-by-step "why" lives (OTel export over the same files is optional; `.claude/steering/telemetry.md` documents it when telemetry export is opted in, per TEL-01). The `Ended because` line is dual-surface: the `exit_reason` code is the stable machine key (the enum in Recovery & State, unchanged), and the sentence is the operator render — a wording revision may change the sentence, never the code.

### Budgets — time, tokens, tasks

Operators set explicit budgets at runner invocation, in `auto-config.md`, or via command-line flags. The runner respects them strictly.

- **Time budget:** maximum wall-clock duration for the run. Default: unset (no time cap). Recommended for first runs: 1 hour. For overnight: 8-10 hours.
- **Token budget:** maximum cumulative tokens (main + judge) across all tasks in the run. Default: unset. Tracked via per-task summaries. The runner does not invoke any model with token-counting; it relies on the per-task wrappers reporting consumption. (Token tracking is approximate; the budget is a soft ceiling, not a hard one — the runner checks at task boundaries, not mid-task.)
- **Task budget:** maximum number of tasks to attempt in the run. Default: unset. Useful for small first runs.

When any budget is exhausted, the runner finishes the current in-flight tasks (does not start new ones), finalizes the summary with budget-exhaustion noted, and exits terminal.

**Cost discipline.** Multi-task queue runs are the protocol's highest-cost-shape operation. A 12-task overnight run with goal-supervised mode (judge call per iteration, average 6 iterations per task) is on the order of 72 judge calls plus the per-task main-model cost. The judge is cheap individually; the main-model cost is the dominant term and scales with task count and iteration count. Operators should set token or task budgets explicitly for the first several runs and review actual consumption before raising them.

### Trust ramp — recommended adoption sequence

The "for hours or days" property is the *aspiration*. Building up to actually trusting it is a multi-week process. The recommended ramp:

1. **Week 1: 30-minute supervised runs.** Operator at the keyboard, queue has 2-3 small ready tasks, all goal-supervised-mode-eligible. Operator watches the runner's behavior. Goal: confirm the runner correctly dispatches, observes terminal states, updates the queue file, and produces a useful summary.
2. **Week 2: 1-2 hour supervised runs.** Operator nearby but not watching continuously, queue has 4-6 tasks. Goal: confirm the runner handles a real backlog without operator intervention between tasks.
3. **Week 3: half-day runs with operator available.** Queue has 8-12 tasks with a mix of independent and dependency-chained work, including at least one operator-only task to confirm skip-and-continue. Operator available to respond to pauses or halts within an hour. Tight task and token budgets. Goal: confirm the runner's skip-and-continue (around operator-only and blocked tasks), pause-when-no-work-remains, and halt-on-urgent-escalation behaviors all work in practice.
4. **Week 4: short overnight runs.** Queue has a small backlog, time budget of 4 hours, token budget set conservatively. Operator reviews the morning-after summary thoroughly. Goal: confirm the morning-after review experience is actually useful and not overwhelming.
5. **Week 5+: full overnight or multi-day runs.** Only after the prior weeks have surfaced and resolved the surprises specific to this codebase and team.

This is the same posture as the loop-mode advice to stay operator-in-the-loop for the first 5–10 tasks and the goal-supervised-mode advice to do the same for the first 10–20 tasks, applied at the coordination layer.

The protocol explicitly does **not** support skipping the trust ramp. The wizard surfaces the recommended sequence at Phase 0 when the operator opts into queue mode, and Phase 10 repeats it in the handoff.

### Architecture: cooperation with per-task mechanisms

Queue mode does not modify the per-task mechanisms. The runner's interaction surface with each per-task wrapper is intentionally narrow:

- The runner reads `loop_eligible` and `goal_supervised_eligible` task-definition fields to decide which wrapper to dispatch to. It does not re-classify tasks.
- The runner invokes the wrapper as a subprocess with the task ID as argument. It does not inject context, override config, or change wrapper behavior.
- The runner waits for the wrapper to exit, then reads the wrapper's `loop-final-<task-id>.md` for the termination classification. It does not invoke any tool inside the wrapper's session.
- The runner respects the `.loop-active-<task-id>` / `.goal-active-<task-id>` sentinels written by the wrappers; it never writes those sentinels itself.
- The runner respects the existing `loop_in_flight` / `goal_in_flight` mutual-exclusion check — it dispatches one task per concurrency slot and does not attempt to bypass the wrappers' own duplicate-prevention logic.

This narrowness is what keeps the runner's trust ramp manageable. Adding new interactions between the runner and the per-task wrappers would require re-establishing trust in each interaction; the present design requires trust only in the small `auto.sh` orchestrator, not in any new wrapper behavior.

### Architecture: cooperation with urgent escalations

The five urgent escalation criteria from `CLAUDE.md` remain hard-blocks at the per-task level inside queue mode:

- Do-not-touch file modification needed
- Secret encountered
- Hook block with non-obvious fix
- Dependency not on approved list
- Spec turned out to be wrong

When any of these fire inside a per-task wrapper running under the queue, the wrapper writes `.loop-halt-<task-id>` and exits as it does in manual dispatch. The runner reads the halt classification from `loop-final-<task-id>.md` and **halts the queue immediately** — non-configurable. The operator returns to a halted queue with the per-task `decision-pending-<session-id>` ready for action, the `loop-final-<task-id>.md` recording what happened, and the run-summary noting the urgent escalation under "Halted — needs operator attention." The remaining tasks in the queue stay in "Ready to run" and the next queue invocation picks them up — modulo whatever the operator does about the escalation, which typically involves a steering-doc edit, a spec update, or a manual intervention.

This is the runner's hardest-to-violate rule and the principal safety property at the coordination layer. An operator who finds it restrictive should not enable queue mode.

### What the wizard generates when queue mode is opted in

- **`.claude/auto.sh`** — the runner script. Generated from a template; the operator approves before write. Made executable (`chmod +x`). Supports flags for budgets (`--time=<duration>`, `--tokens=<count>`, `--tasks=<count>`) and a manual-halt flag (`--halt-after-current`). On startup, the runner verifies at least one per-task mechanism is enabled, reads the queue, writes `.claude/queue/.run-active`, appends to `queue_runs_history`, and enters the main dispatch loop. On terminal exit, writes the final summary (the morning-after summary — format specified in "The morning-after summary" below), removes `.run-active`, updates `queue_runs_history`, plays the appropriate audio cue, and returns control.
- **`.claude/auto-config.md`** — operator-tunable settings (defaults shown):
  - `max_concurrent_tasks: 2`
  - `scan_interval_seconds: 30`
  - `pause_on_max_iterations: false`
  - `pause_on_goal_condition_suspect: false`
  - `consecutive_halt_threshold: 3`
  - `default_time_budget: unset`
  - `default_token_budget: unset`
  - `default_task_budget: unset`
  - `summary_synthesis_enabled: true`
  - `summary_synthesis_model: haiku`

  Format mirrors `loop-config.md` and `goal-config.md`. Committed to the repo.
- **`.claude/queue/`** — directory created with an empty `backlog.md` skeleton (section headers only; no tasks yet). The first tasks are added by `spec-decompose` at feature-implementation time.
- **`.claude/queue/backlog.md`** — the queue file. Skeleton at this phase; populated by `spec-decompose` thereafter. Committed.
- **`.claude/queue/run-summary-<timestamp>.md`** — written per queue run by the runner; iteration history and morning-after summary. Committed (operator-facing audit record).
- **`.claude/queue/.run-active`** — sentinel written by the runner at start; cleared at terminal exit. Gitignored.
- **`.claude/queue/.halt`** — sentinel written by the operator to request graceful halt. Gitignored.
- **`.claude/queue/.resume`** — sentinel written by the operator to resume after a pause. Gitignored.
- **`spec-decompose` skill** — augmented with the queue-population step (Phase 7).
- **`CLAUDE.md`** — gains the queue-mode coordination-layer reference section (Phase 8). No new conditional addendum (the runner does not load CLAUDE.md).
- **`.gitignore`** — gains queue-mode runtime-sentinel entries (Phase 7).

### Risks and known failure modes

The wizard surfaces these to the operator before generating queue-mode artifacts:

- **The queue runner amplifies every per-task failure mode by the number of tasks it runs.** A 5%-failure-rate per-task mechanism running 20 tasks overnight produces 1 expected failure. Multi-task autonomy requires per-task behavior to be well-understood first — hence the 4-week recommendation before opt-in.
- **The morning-after review burden is real even with a good summary.** The summary helps prioritize but does not eliminate the work. If the queue produces more decisions than the operator can review per session, the queue is over-decomposed or the specs were under-specified.
- **Environmental drift accumulates over long runs.** Dependencies might update, CI might change, flaky tests might appear unrelated to the task work. The three-consecutive-halts rule catches the worst, but subtle drift can pass through. Operators should run a cumulative-diff review after clean-completion queue runs even when every task technically succeeded.
- **Cost can balloon.** The runner's cost shape scales with task count and per-task iteration count. Operators should set explicit token or task budgets for the first many runs and review actual consumption before raising them.
- **The trust ramp is non-optional.** Operators who skip the ramp ship problems they could have caught with supervised use first. The protocol explicitly does not support skipping.
- **Urgent escalations halting the queue may feel restrictive.** It is not. It is the safety model. Operators uncomfortable with this rule should not enable queue mode.

### AI actions

1. **Confirm the operator wants to proceed.** Restate the design principles (the runner does not work it dispatches, the queue is the unit of autonomy not the loop, urgent escalations halt the queue, the morning-after summary is load-bearing), the trust-ramp expectations, and the risks above. Get explicit confirmation before generating any queue-mode artifacts.
2. **Generate `.claude/auto.sh`** from the runner template, adapted to the project's shell environment (detected at Phase 0). Show the script to the operator before writing — security-relevant per Phase 6's checklist. Run the same hook security & correctness checklist (no `eval`, quoted paths, exit codes, signal traps for SIGINT/SIGTERM, executable bit set, `jq` available where required, summary-synthesis-API credentials read from environment not hardcoded).
3. **Generate `.claude/auto-config.md`** with the defaults listed above. Operator can edit before approval. The file includes a brief comment block at the top enumerating the **non-configurable invariants** (operator-only tasks always skipped; runner always pauses rather than terminates when only operator action could unblock work; urgent escalations always halt the queue) so the operator sees the rules but understands they are stated, not set.
4. **Generate the queue scaffolding.** Create `.claude/queue/` directory with an empty `backlog.md` skeleton: the title `# Project backlog`, a `## Queue policy` section pre-populated with the same default values written to `auto-config.md` in step 3 (so the skeleton is immediately usable and the operator sees the defaults in context), then the remaining section headers (`## Ready to run`, `## Operator-only (skipped by runner)`, `## In flight`, `## Completed this run`, `## Halted this run (needs review)`, `## Deferred`), and a brief HTML comment near the top explaining that `Ready to run` / `Operator-only` / `Deferred` sections are populated by `spec-decompose`, while `In flight` / `Completed this run` / `Halted this run` are populated and reset by the runner. No tasks at this phase; `spec-decompose` adds them at feature-implementation time.
5. **Augment `spec-decompose`** to add the queue-population step (already specified in Phase 7; this phase wires it in). If Phase 7 ran before this phase, confirm the augmentation is present (priority prompt, section placement prompt, `blocked_by` prompt, queue-file append behavior).
6. **Update `CLAUDE.md`** with the queue-mode coordination-layer reference section (already specified in Phase 8; this phase wires it in). If Phase 8 ran before this phase, confirm the reference is present. Reaffirm to the operator that no new conditional addendum is needed — the runner does not load `CLAUDE.md`.
7. **Update `.gitignore`** with the queue-mode runtime sentinel paths (already specified in Phase 7; verify they were included if Phase 7 ran before this phase, or add them now). Confirm `backlog.md` and `run-summary-*.md` are *not* gitignored — they are operator-facing audit records.
8. **Recommend the smoke test.** If Phase 9 was run, recommend the queue-mode (fifth-stage) smoke. If Phase 9 was skipped, strongly recommend running the queue-mode smoke before relying on the runner for real work.
9. **Surface the trust ramp.** Show the operator the week-by-week ramp from the "Trust ramp" section above. Confirm they understand the ramp is not optional and the runner should not be used overnight in the first week. Note that this is the third trust-ramp guidance in the protocol (after the 5–10-task ramp for loop mode and the 10–20-task ramp for goal-supervised mode); the three are independent and additive — the operator should be calibrated on each layer before moving to the next.
10. **Update state file.** Confirm `bootstrap_protocol_version: "2.0.0"` is set (Phase 0 wrote it) and confirm `queue_mode_enabled: true` is set (from Phase 0). Verify `queue_runs_history: []` is present from Phase 0's initial write (the runner will append/update entries during queue runs).
11. Show all created and modified files. Ask: **approve / edit / start over**.

**Exit criteria:** `auto.sh` and `auto-config.md` exist and are approved. The `.claude/queue/` directory and skeleton `backlog.md` exist. The queue-population step is wired into `spec-decompose`. The `CLAUDE.md` queue-mode coordination-layer reference is in place. The `.gitignore` queue-mode entries are in place. The operator has seen the risks and the trust ramp and confirmed proceeding.

---

<a id="phase-10"></a>
## Phase 10 — Handoff

**AI actions:**
1. Summarize what was built. List every file created with a one-line description.
2. Update `.claude/.bootstrap-state.json` to mark bootstrap complete.
3. **Surface any remaining deferred items.** Read `deferred_items` from the state file. For each entry, tell the operator what was deferred, why, and how to complete it later. The most common entry is `ci_config_generation` (from Phase 5, when Phase 9 was also skipped); the wizard tells the operator how to invoke the wizard's Phase 5 setup separately, or to write the CI config by hand against `ci-cd.md`. Do not mark bootstrap complete with silent residue.
4. Tell the operator the next three things:
   - Commit `.claude/` and `docs/prd/` to the repo.
   - Run `/spec-new <first-feature>` to start real work.
   - Revisit steering docs after the first feature ships — they will need refinement.
5. Note explicitly:
   - Steering docs are living. Update when conventions change.
   - `learnings/` is for cross-feature memory. Add to it after each feature.
   - Hooks won't catch convention drift. Only humans will.
   - The escalation list in `CLAUDE.md` is the contract — if the agent escalates outside it, that's a bug to fix in steering, not behavior to override in-session.
   - For multi-developer teams: steering doc updates should go through PR review like any other code. The bootstrap is single-operator; ongoing maintenance is team practice.
   - **If loop mode was opted into:** start operator-in-the-loop for the first 5–10 tasks anyway. Use the time to develop a feel for how `spec-decompose` classifies your tasks (does it correctly identify the genuinely-bounded ones?) and how the reviewer subagent handles your code. Once you trust both, opt specific tasks into the loop. Each loop run produces a `loop-final-<task-id>.md` and a `decisions-log-<task-id>.md`; review both before merging, especially the decision log's expensive-to-undo entries. If a task hit max-iterations, treat that as protocol working as designed, not a failure: it tells you the spec needed more detail.
   - **If loop mode was not opted into:** you can enable it later by re-running the wizard's loop-mode setup separately. The wizard detects `loop_mode_enabled: false` in state and offers to flip it. Existing tasks are unaffected; the classifier only applies to future `spec-decompose` invocations.
   - **If goal-supervised mode was opted into:** start operator-in-the-loop for the first 10–20 tasks anyway. Use the time to develop a feel for how `spec-decompose` classifies your tasks (does the sixth criterion correctly identify goal-judge-able tasks?), how the recommendation rule behaves on eligible-for-both tasks (does it pick the mode you would have picked?), and how Haiku judges your codebase (are its "no" reasons useful, or noise?). Record per-task assessments in `learnings/mode-selection.md`. After 20 tasks, review the accumulated evidence and adjust the recommendation rule if needed. Once you trust the classifier and the judge, run goal-supervised mode on tasks where it's recommended. Each run produces `loop-final-<task-id>.md`, `decisions-log-<task-id>.md`, `.iteration-summary-<task-id>-*.md` files, and `.evaluator-feedback-<task-id>.md` — review all four artifact types before merging, especially the disagreement entries. If a task halted with `goal-condition-suspect`, treat that as the protocol working as designed: the goal condition or the judge needs human attention, not a bigger model or more iterations.
   - **If goal-supervised mode was not opted into:** you can enable it later by re-running the wizard's goal-supervised setup separately. The wizard detects `goal_supervised_mode_enabled: false` in state and offers to flip it. Existing tasks (loop-mode-eligible or operator-only) are unaffected; the sixth criterion only applies to future `spec-decompose` invocations.
   - **If both per-task modes are enabled:** the classifier handles routing per task. The operator's job is to confirm or veto recommendations, not to pre-decide which mode each feature uses. Resist the temptation to manually classify; the classifier exists precisely so the operator doesn't have to.
   - **If autonomous queue mode was opted into:** **do not run the queue overnight in the first week.** Follow the week-by-week trust ramp from Phase 9.7. The wizard's first dispatch should be a 30-minute supervised run with 2–3 small tasks while the operator watches. Each queue run produces a `run-summary-<timestamp>.md` — review it the morning after before merging anything. Pay particular attention to the "Decisions requiring operator review" and "Halted — needs operator attention" sections. If a run halts on three-consecutive-halts, treat that as the protocol working as designed: the queue itself has a higher-order problem (wrong classifications, broken dependencies, environmental drift) worth investigating before resuming. Queue runs that complete cleanly should still receive a cumulative-diff review — environmental drift over many tasks can produce a codebase state worse than the start even when every task technically succeeded. Edit `backlog.md` between runs to reorder priorities, defer tasks, or remove ones the operator decides against; the runner reads the queue fresh on each invocation.
   - **If autonomous queue mode was not opted into:** you can enable it later by re-running the wizard's queue-mode setup separately. The wizard detects `queue_mode_enabled: false` in state and offers to flip it. Requires at least one of `loop_mode_enabled` or `goal_supervised_mode_enabled` to be true; if neither is, the wizard refuses the upgrade and explains why. Existing task definitions are unaffected; the queue is populated by `spec-decompose` from the point of opt-in forward.
   - **For all projects with any autonomous mode (loop, goal-supervised, or queue):** the protocol's overall trust posture is: humans review what the agents did, the agents do not review themselves, and the gates exist to make review tractable, not to replace it. Adding more autonomy means investing in better review surfaces, not skipping review. Operators who find themselves reviewing less as autonomy increases have inverted the safety model. The three layers (per-task loop, per-task goal-supervised, queue-level coordination) each have their own trust ramp (5–10 tasks, 10–20 tasks, 4 weeks respectively); the ramps are independent and additive — calibrate each layer before adding the next.
   - Bootstrap doesn't end the protocol's relevance. As the project matures past certain thresholds (first regulated user, first integration goes live, ~30 commits, first additional contributor, codebase exceeds 1GB, first team handoff), additional artifacts become applicable. See the **Post-bootstrap milestones** section in `Bootstrap-Protocol-Companion-v2-4-0.md` for the full trigger table.

**Exit criteria:** Operator confirms readiness to start real work.

---

<a id="protocol-rules"></a>
## Protocol rules for the AI

- **Classify before configuring.** Phase 0's archetype decision (or synthetic profile) routes everything else.
- **Match PRD depth to archetype.** A CLI tool doesn't need a full PRD. A platform can't do without one.
- **Honor the skip policy.** Required phases cannot be skipped without explicit override acknowledgment from the operator. State the consequence before accepting the skip.
- **Never batch artifacts.** Write one, confirm, move on.
- **Always show before writing.** Propose content in chat, get sign-off, then write to disk. This applies double for hook scripts and agent definitions, which are security-relevant.
- **Detect, don't assume.** When a codebase exists, scan first. Cite the files you read. Don't ask questions whose answers are visible.
- **Ask one open-ended question at a time.** Use multi-select for known options. Reserve free-form for things only the operator knows.
- **Persist state.** Update `.bootstrap-state.json` after each phase exit. On resume, read it first.
- **If the operator gets impatient,** acknowledge it. Explain that time spent here saves multiples downstream. Offer to checkpoint and resume.
- **Halt and ask if anything is ambiguous.** Ambiguity in steering docs poisons every downstream session.
- **For "Other" archetype:** the synthetic profile from Phase 0 routes phase questions. If a phase has no relevant questions for the profile, note this and proceed; do not invent questions.

---

## Proposed revisions (round-4-review-derived, NOT yet adopted)

> **Status:** NON-NORMATIVE. Nothing in this section changes the protocol. These are structured proposals derived from an outside (round-4) review. Each item below may be a real weakness *or* a deliberate design decision by the protocol authors; the reviewer does not have access to author intent and must not overwrite it. The protocol body above was unchanged *as of the round-4 review (protocol version 1.9.0)*; the v2.0.0 modernization fold post-dates this review and did not adopt any proposal here. Adopting any item here is a deliberate, separately-versioned fork — it requires the human owner to answer the OPEN QUESTION and to make the edit explicitly. Do not treat any proposal here as in force.

### B-1 — The skeleton-vs-complete deliverable contract for the autonomous wrappers

> **STATUS: ADOPTED at 2.2.0, reading (b).** The normative text now lives in Phase 9.5 "Deliverable contract for the wrappers"; the shipped implementation already conformed (skeletons with the enumerated fail-safe invariants). This entry is retained for provenance only.

**Problem.** Phases 9.5, 9.6, and 9.7 specify what the wizard *generates* for `loop.sh`, `goal-loop.sh`, and `auto.sh` (the race-safe claim sequence, sentinel handling, in-flight list accounting, dispatch loop). Separately, the Skip Policy and the Phase 10 trust ramp instruct the operator **not to run those wrappers unattended for weeks** (5–10 tasks for loop, 10–20 for goal-supervised, 4 weeks for queue). The document specifies the *fully-realized* behavior and the *deferral*, but never states what the generated artifact is supposed to *be* during the interim — a complete-but-unrun script, or an intentionally-incomplete skeleton the operator finishes before first unattended use. The two readings are both consistent with the prose, and they imply very different conformance bars for any installer that emits these files.

**Why it matters.** This is the documented root cause of the round-4 W-1 finding: an installer reading "the wizard generates `loop.sh`/`goal-loop.sh`" as "emit a complete wrapper" versus "emit a guarded skeleton" produces materially different files, and the protocol is the frozen authority that conformance is measured against. As written, the protocol cannot adjudicate W-1 either way — both the "they must ship complete" and the "skeletons are conformant" positions can cite it. Every future review of the autonomous path inherits this ambiguity.

**Specific change I would make (if adopted).** Add one explicit subsection — e.g., "Deliverable contract for the wrappers" — to Phase 9.5 (referenced by 9.6 and 9.7) stating exactly one of: (a) the wizard emits a *complete* wrapper and the trust ramp is purely an operational gate on *running* an already-complete artifact; or (b) the wizard emits a *guarded fail-safe skeleton* whose unattended-execution loop (`claude -p` iteration, `*_in_flight` accounting lifecycle, PID-liveness double-start guard) is explicitly operator-completed before first unattended use, and the skeleton's required fail-safe invariants are enumerated (refuse on missing/ineligible task, honor `.halt`, perform the race-safe claim, dispatch no unattended agent work, fail closed on absent `flock`). The wording would name which functions are in-scope for the skeleton vs. the operator.

**Cost / what it could break.** Option (b) ratifies the round-4 W-1 fix's "guarded skeleton" reading and makes the existing installer conformant, but it weakens the apparent promise of Phases 9.5–9.7 ("the wizard generates the wrapper") into "generates a skeleton," which may understate what the authors intended the wizard to deliver. Option (a) keeps the stronger promise but makes every shipped-skeleton installer non-conformant by definition and converts the trust ramp into an operational-only control. Either choice retroactively re-grades prior review rounds that relied on the unstated reading. This is a behavioral spec change (it changes what a conformant installer must emit), which is why it is a proposal, not a Track-A fix.

**OPEN QUESTION for the human owner.** Did the authors intend the wizard to emit *complete* autonomous wrappers (trust ramp = operational gate only), or *guarded fail-safe skeletons* whose unattended-execution loop the operator completes before first unattended use? Whichever it is, may the deliverable contract be stated explicitly in Phase 9.5 — and if skeleton, what is the exhaustive list of fail-safe invariants the skeleton must satisfy to be conformant?

### B-2 — "Atomic update" relies on advisory `flock`, but the document also sanctions a bypass

**Problem.** The Recovery & State section defines "atomic update" as `flock` on `.claude/.bootstrap-state.json` plus tmpfile-then-rename, and the Race-safety summary builds the three concurrency guarantees on it. The same section, and the cross-mode concurrency rule, also explicitly sanction manual dispatch of `loop.sh`/`goal-loop.sh` alongside an active `auto.sh` run and resolve the resulting contention as "an operator-respected convention, not a mechanical enforcement." `flock` is advisory: a sanctioned manual dispatch that races the runner is exactly the case the advisory lock cannot mechanically prevent, so the race-safety guarantee and the sanctioned bypass coexist by design but are presented in adjacent paragraphs without the tension being named.

**Why it matters.** A reader (or an installer author hardening the wrappers) can come away believing the in-flight lists "never lose entries under concurrent updates" *unconditionally*, when the document's own concurrency rule introduces a sanctioned path where the guarantee holds only if the operator honors a convention. This is the kind of unstated coupling that produces a "the wrapper randomly forgot about a task" bug report that no one can reproduce, because the failing case is the sanctioned-but-unguarded one.

**Specific change I would make (if adopted).** In the Race-safety summary, add a single sentence scoping guarantee (b): the no-lost-entries property holds for all dispatchers that acquire the `flock` (the generated wrappers and runner do); manually-invoked dispatchers that bypass the lock are outside the mechanical guarantee and fall under the operator-respected-convention clause in the cross-mode concurrency rule. No mechanism change — just making the existing scope boundary explicit where the guarantee is stated, not only where the bypass is sanctioned.

**Cost / what it could break.** This is a documentation-scoping change in the body, so it cannot be a Track-A fix without owner sign-off: it could be read as *weakening* a guarantee the authors deliberately stated unconditionally (perhaps because they consider non-`flock` dispatch out of contract entirely and did not want to legitimize it by mentioning it next to the guarantee). Alternatively the coexistence is fully intended and calling it out is redundant. Either way it shifts how strong the concurrency guarantee reads.

**OPEN QUESTION for the human owner.** Is the no-lost-entries guarantee intended to be unconditional (and manual non-`flock` dispatch simply out of contract, not to be acknowledged at the guarantee site), or should the Race-safety summary explicitly scope the guarantee to lock-acquiring dispatchers and point to the operator-respected-convention clause for the sanctioned manual-dispatch case?

### B-3 — The concurrency budget is named "the failure mode" but defended only by convention

**Problem.** The cross-mode concurrency rule states plainly that "**Manual dispatch alongside an active queue run is the failure mode**," and then defends against it only with "an operator-respected convention, not a mechanical enforcement." The strongest warning in the concurrency model is attached to the weakest enforcement, and it appears once, in Recovery & State. The opt-in points that lead an operator toward this failure mode — the Phase 9.5/9.6/9.7 opt-in prompts, the Phase 0.5 preview, the Phase 10 handoff — do not repeat it at the moment of decision.

**Why it matters.** The document's own risk ranking says this is *the* failure mode of the combined autonomous system, yet an operator opting into queue mode in Phase 9.7 is never shown that sentence at opt-in time; they would only encounter it if they read Recovery & State. A warning that the document itself rates as the top failure mode arguably should be surfaced where the operator can act on it, not only in a reference section.

**Specific change I would make (if adopted).** Add a one-line pointer (not a re-statement — the document deliberately states invariants once) at each autonomous-mode opt-in confirmation and in the Phase 10 "any autonomous mode" note: a single sentence directing the operator to the cross-mode concurrency rule and naming manual-dispatch-during-a-queue-run as the top failure mode to avoid. No new requirement; a surfacing/cross-reference change only.

**Cost / what it could break.** The protocol has an explicit, stated style discipline — invariants are stated once and only once (e.g., the non-configurable invariants are "stated only in this section and as comments in the queue-policy block"). Adding repeated pointers, even as cross-references, cuts against that discipline and could be exactly what the authors chose to avoid; over-surfacing also dilutes the other once-stated warnings. Conversely, the authors may simply not have weighed surfacing against the single-statement rule for this particular item.

**OPEN QUESTION for the human owner.** Is the single-statement placement of the "manual dispatch is the failure mode" warning a deliberate application of the state-invariants-once discipline, or an oversight? If surfacing is wanted, is a bare cross-reference pointer (no re-statement) at the opt-in points acceptable under that discipline, or should it remain solely in Recovery & State?

### B-4 — No state-file forward/backward-compatibility rules in the authoritative document

**Problem.** `.bootstrap-state.json` is load-bearing across resume, the in-flight lists, `queue_runs_history`, the crash-recovery close-out, and the "enable a mode later" flows. The authoritative document specifies the *current* shape but defers all migration/compat behavior entirely to `Bootstrap-Protocol-Companion-v2-4-0.md`'s "Migration notes." There is no statement in Bootstrap-Protocol-v2-4-0.md of how a runner or wrapper must behave when it encounters a state file written by a different `bootstrap_protocol_version` (forward-compat: newer file, older tool; backward-compat: older file, newer tool) — e.g., unknown `exit_reason` values, missing `queue_runs_history`, absent mode flags.

**Why it matters.** The companion file is explicitly a non-authoritative reference ("Consult it when this file references those topics"). Anchoring the *only* compat rules in a non-authoritative file means there is no frozen contract for the single most state-sensitive file in the system. An installer or wrapper author has nothing in the authority document to conform to for the version-skew cases, even though crash-recovery and enable-later explicitly read and rewrite this file.

**Specific change I would make (if adopted).** Add a short "State-file compatibility" paragraph to Recovery & State stating the minimum contract: how a tool must treat an unrecognized `bootstrap_protocol_version`, unknown enum values in `exit_reason`, and missing optional lists (e.g., refuse vs. best-effort-upgrade vs. read-only), and explicitly designating which file (this one vs. the companion) is authoritative for the rules vs. the worked migration examples.

**Cost / what it could break.** Promoting compat rules into the authority document creates a new normative surface that future installers must conform to and that future review rounds will measure against — a real expansion of the spec's contract, not a clarification. The authors may have deliberately kept Bootstrap-Protocol-v2-4-0.md free of migration mechanics to keep it stable while the state schema evolves in the companion. Stating a minimum contract here could also conflict with whatever the companion already says, requiring reconciliation. This is a behavioral spec addition, hence a proposal only.

**OPEN QUESTION for the human owner.** Was deferring all state-file compat behavior to the (non-authoritative) companion deliberate — i.e., the authors want the authority document to carry *no* version-skew contract — or should Bootstrap-Protocol-v2-4-0.md carry at least a minimal normative compat statement, with the companion holding only the worked examples? If the latter, what is the intended posture on an unrecognized `bootstrap_protocol_version` (refuse / read-only / best-effort upgrade)?

### B-5 — Whether fail-loud-on-empty-gate-commands should be a first-class named invariant

**Problem.** The document treats two properties as named, load-bearing invariants that the installer and interview validate against: the skip policy (which phases are required/skippable) and the queue⇒loop|goal rule (queue mode requires at least one per-task mechanism). A third property of equal operational weight — that gates generated with empty `commands.test`/`lint`/`format` **fail loudly with a TODO rather than silently passing** — is stated only as prose in Phase 6 / honest-limitations and is exercised by tests, but is never elevated to the same first-class "invariant" status as the other two, even though a regression in it (a gate that silently passes on empty commands) is a silent-fail-open of exactly the class the security review rounds treated as critical.

**Why it matters.** First-class invariants get explicit, named enforcement and explicit review attention; prose properties get neither by default. The asymmetry means the skip policy and queue⇒loop|goal rule are systematically protected (validated by `resolve_config`, asserted by tests, named in the document) while the fail-loud-on-empty-gate property — arguably the most safety-relevant of the three — relies on the property being remembered as prose. Naming it as an invariant would put it on the same footing.

**Specific change I would make (if adopted).** In the section where the skip-policy and queue⇒loop|goal invariants are characterized as invariants, add the fail-loud-on-empty-gate-commands property to the named-invariant set (description only — it is already the documented behavior in Phase 6; this would not change behavior, only its status/visibility as a named invariant the document relies on). Note: this is *adjacent* to a Track-A "enumeration omits an invariant the document relies on elsewhere" defect, but is filed as a proposal because deciding what counts as a first-class invariant is an authorial judgment about the spec's invariant set, not a mechanical reconciliation — promoting it changes the document's stated contract surface and what future reviews must treat as invariant-grade.

**Cost / what it could break.** Elevating a property to named-invariant status raises the conformance bar: future installers and reviews must treat it as invariant-grade, and any tool that does not explicitly enforce it becomes non-conformant by the document's own framing. The authors may have deliberately scoped "invariant" to *config-resolution* properties (things `resolve_config` checks) and intentionally kept hook-emission behavior as prose; widening the term dilutes that scoping. If adopted it must be purely descriptive, or it crosses into behavioral change.

**OPEN QUESTION for the human owner.** Is "invariant" in this document deliberately scoped to config-resolution properties (so fail-loud-on-empty-gate is correctly prose, not an invariant), or should fail-loud-on-empty-gate-commands be named as a first-class invariant alongside the skip policy and the queue⇒loop|goal rule — and if so, confirm the addition is intended to be descriptive only, changing status and not behavior?

### B-6 — Whether a single consolidated mode×sentinel×list×writer×cleanup reference table would reduce cross-referential reading risk

**Problem.** The per-mode mechanics — which sentinel each mode writes (`.loop-active-<id>`, `.goal-active-<id>`, `.run-active`), which in-flight list it maintains (`loop_in_flight`, `goal_in_flight`, `queue_runs_history`), which component writes/cleans each, and the race-safe claim/cleanup sequence — are correct but distributed across Recovery & State, Phase 6.D, Phase 7 step 7, Phase 8, Phase 9.5 (wrapper + race-safety summary), Phase 9.6 (wrapper), and Phase 9.7 (runner + queue file). A reader verifying one mode's full lifecycle must assemble it from five-plus locations, and the round-4 W-1/G-1 findings both originated in the gap between distributed statements (file-level vs. logical-level guarantees; the gitignore enumeration vs. the dotfile-convention claim).

**Why it matters.** The protocol is the frozen reference four review rounds measured code against; cross-referential assembly is precisely where reviewers and installers diverge from each other and from intent. Two round-4 findings were rooted in distributed-statement gaps. A single consolidated table would not change any rule but would make divergence detectable by inspection rather than by cross-referencing seven sections.

**Specific change I would make (if adopted).** Add one read-only reference table (in Recovery & State, or as a clearly-marked non-normative appendix) with a row per mode and columns: active sentinel, in-flight list, writer component, cleanup trigger, race-safe-claim reference. Every cell would be a pointer to the already-authoritative prose, with the prose remaining the source of truth and the table explicitly labelled non-normative to avoid creating a second authority.

**Cost / what it could break.** A consolidated table is a *second representation* of facts the document deliberately states once each, in context. Even labelled non-normative, it creates a maintenance burden (every future mechanic change must update both the prose and the table) and a divergence risk (table and prose drifting apart is itself a new class of internal-consistency defect — the exact problem this document is sensitive to). The authors' single-statement discipline may be a deliberate rejection of exactly this kind of summary surface. There is also a placement question: in-body vs. appendix changes whether it reads as authoritative.

**OPEN QUESTION for the human owner.** Is the deliberately-distributed, stated-once-in-context presentation a chosen tradeoff (accepting cross-referential reading cost to avoid a second representation that can drift), or would a clearly non-normative consolidated reference table be welcome — and if so, in-body (Recovery & State) or as a marked appendix, and who owns keeping it in sync with the authoritative prose?

### B-7 — Which `exit_reason` is written when the time budget elapses during the operator-only pause

**Problem.** Three statements bear on the `exit_reason` a paused runner records when its *time* budget elapses before the operator resumes. The `exit_reason`-enum preamble (Recovery & State) attributes this case to `"operator-only-timeout"` and explicitly says it is "the paused-then-time-budget-elapsed outcome of the pause row." The Phase 9.7 termination-conditions table, read on its own, says the pause row "waits indefinitely (or until time budget exhausted)" and separately that "Operator-set time budget exhausted | Terminal" — which points a reader to `"time-budget-exhausted"`. The enum preamble does reconcile this (the pause case is `"operator-only-timeout"`, attributed to a runner behavior rather than its own table row), so this is **not** a false cross-reference and not a Track-A defect — but the disambiguation lives *only* in the enum preamble. A conformance-checker validating the runner against the Phase 9.7 termination table alone would reasonably write `"time-budget-exhausted"` for this case; one reading the enum would write `"operator-only-timeout"`. Two independent reviewers can each cite the document for a different answer.

**Why it matters.** This is the exact lens-3 condition the review methodology flags: a section that can be cited to support both sides of a conformance question. `exit_reason` is consumed by the morning-after summary, by crash-recovery close-out, and (per B-4) by any future state-file compat rules; a runner that writes the "wrong" one for the paused-timeout case is non-conformant under one reading and conformant under the other, and nothing in the table itself tells the implementer which. The enum preamble settles it, but only for a reader who reaches the enum; the table is the more natural conformance surface for the runner's terminal behavior.

**Specific change I would make (if adopted).** Add a parenthetical cross-reference on the two affected Phase 9.7 termination-table rows only — the pause row and the time-budget row — pointing to the `exit_reason`-enum preamble for the paused-then-time-budget-elapsed case (e.g., on the time-budget row: "*(if the budget elapses while the runner is paused for operator action, see the `exit_reason`-enum note in Recovery & State — that case records `operator-only-timeout`, not `time-budget-exhausted`)*"). No rule change; the enum preamble already decides the behavior. This is strictly a pointer added at the second citable site so the table cannot be read to contradict the enum. It is narrower than B-6 (which proposes a whole consolidated mode×sentinel table); B-7 is one cross-reference resolving one specific adjudication and does not introduce a second representation of anything.

**Cost / what it could break.** Same single-statement-discipline tension as B-3/B-6: the document deliberately states the enum/table relationship once, in the enum preamble, and adding a pointer on the table rows cuts against "stated once, in context." It also slightly privileges the enum over the table as the authority for this case, which the authors may or may not have intended (they may consider the enum preamble *the* authority for all `exit_reason` questions by design, making a table-side pointer redundant). If the authors intend the table to be self-contained for runner conformance, the fix might instead belong in the table; if they intend the enum to be the sole `exit_reason` authority, no change is wanted and the current placement is correct.

**OPEN QUESTION for the human owner.** Is the `exit_reason`-enum preamble intended to be the single authority that overrides the Phase 9.7 termination table for the paused-then-time-budget-elapsed case (so a table-side pointer is merely a convenience and may be declined under the single-statement discipline), or should the termination table itself be self-contained for runner conformance — in which case should the disambiguation move to / be duplicated on the table rather than pointed at from them?


### Grade-audit-derived proposals (2026-07, NOT yet adopted)

> **Status:** NON-NORMATIVE, under the same rule as this appendix's banner: nothing here changes the protocol, and adopting any item is a deliberate, separately-versioned decision by the human owner. Provenance differs from the B-series above: this subsection derives from the 2026-07 Tessera/Bootstrap grade audit (finding GR-06), not the round-4 review.

### G-1 — Whether the security-critical gates' predicates should be intent-classes rather than command/path matches

> **Carried forward and superseded by GR2-04 (2026-07-20, GAR-corrected).** The GR-2 audit re-derived this question with 2026 security-survey evidence and named intent classes (`filesystem_delete`, `network_outbound`, `lang_exec`); the live statement of this open question is **GR2-04** in the GR-2 subsection below. This G-1 entry is retained for provenance.

**Problem.** The gate layer's strength is bounded by its matching model. The gates and the permission allowlists match on command name and path, not intent. The same binary is benign or destructive depending on its arguments; a name/path check that passes does not mean the action is safe. This bounds how strong the v2.0.0 `PreToolUse`-deny guarantee actually is — the deny is unbypassable (correct, and strong), but only as precise as the predicate it evaluates.

**Why it matters.** The v2.0.0 gate-substrate migration makes the *enforcement point* unbypassable; it does not make the *predicate* intent-aware. An intent taxonomy (e.g. `filesystem_delete`, `network_outbound`, `lang_exec`) evaluated inside the deny hook is the reproducible layer current harness-security work is converging on.

**Specific change I would make (if adopted).** Evaluate expressing the security-critical gates' predicates as intent classes over the parsed tool call, not command-name matches — landing inside the existing `PreToolUse` `HookMatcher` so the unbypassable-deny property is retained.

**Cost / what it could break.** Intent classification is heavier than a suffix match and can misclassify; a wrong class is a new false-refuse (or false-permit) surface. Scoping it to the security-critical tier bounds the blast radius. It is strictly more machinery than the current model — adopt only if the precision gain is worth the classifier surface.

**OPEN QUESTION for the human owner.** Is command/path matching a deliberate simplicity choice, or an accepted limit worth replacing with intent-level predicates? The proposer cannot see author intent and must not overwrite it.

### GR-2 audit-derived proposals (2026-07-20, GAR-corrected, NOT yet adopted)

> **Status:** NON-NORMATIVE, under the same rule as this appendix's banner: nothing here changes the protocol, and adopting any item is a deliberate, separately-versioned decision by the human owner. **Provenance:** this subsection derives from the 2026-07-20 GR-2 grade audit of the Bootstrap Protocol against 2026 harness practice. The recipes are post-adversarial-review — a GAR review (findings GAR-01..08) corrected the underlying grade doc's evidence before these items were cut. Inherited corrections the owner should not re-litigate: the context-reset-obsolescence claim is **Zylos's third-party analysis, not an Anthropic statement**; "context anxiety" is **Cognition's term**; Anthropic's own Opus 4.6-era remedy for "context rot" is **compaction**; the native-checkpointing deferral lives in **SEAM-CONTRACT §9 (Tessera §8.8), not a Bootstrap section**; the tier-3 autonomous path **already self-heals** via the cooperation hook (§6.D). The GAR-corrected grade transcript itself is deliberately **not** folded into this document — the complexity-budget discipline argues against importing a full recursive self-review artifact; this provenance note carries the lineage. The three adoptable GR-2 recipes (GR2-01/02/03a) were folded normatively at v2.3.0; the items below are the ones that need an owner decision.

### GR2-03b — Interactive tier-3 compaction-first path `[GR2-03b — owner decision pending]`

**Proposal.** On an *interactive* tier-3 fire, offer a compaction-plus-checkpoint route (native runtime compaction + a standard checkpoint write) alongside the existing `/clear` hard reset; the hard reset remains the default and the fallback. Rationale (GAR-corrected): Anthropic's remedy for context rot is compaction, so a forced full reset is heavier than the modern first line. Autonomous tier-3 is out of scope — it already self-heals via the cooperation hook (§6.D).

**OPEN QUESTION for the human owner.** Tier 3's no-acknowledge design is deliberate — "operator self-override at saturated context is the failure mode" (§6.E, Alert 3). A compaction route is a partial override channel: does it reintroduce exactly the self-override the design excludes, or is runtime-managed compaction categorically different from operator acknowledgement? The security-asymmetry principle cuts toward keeping the bounded-loud hard reset; Anthropic's compaction direction cuts toward offering it. Both readings are defensible.

**Seam impact:** none (interactive path only). **Cost of deferral:** interactive operators pay a full reset where compaction might suffice — bounded annoyance, no safety cost. **Bucket: post-v2.3.**

### GR2-04 — Intent-class predicates for security-critical gates `[GR2-04 — owner decision pending]` (carries forward and supersedes G-1)

**Proposal.** Express the security-critical gate predicates as intent classes (`filesystem_delete`, `network_outbound`, `lang_exec`) over the parsed tool call, inside the existing `PreToolUse` `HookMatcher`, retaining the unbypassable-deny property. Scope to the security-critical tier to bound the false-refuse blast radius. Evidence status: verified-in-substance (2026 security surveys plus the PRD's own independent G-1 derivation); it lands as a proposal regardless per the G-1 precedent — the design is author-intent-sensitive and the PRD's own cost note stands: "strictly more machinery… adopt only if the precision gain is worth the classifier surface."

**OPEN QUESTION for the human owner.** G-1's guard applies: the proposer cannot see author intent on whether predicate precision outweighs classifier surface for this operator profile. Also: does GR2-05 (a second wall) reduce the urgency of this one, or vice versa — adopt one, both, or neither?

**Seam impact:** none if the gate-module API shape is unchanged (the SEAM-amendment-sdk-gate-module constraints hold); flag if class metadata enters the builder API. **Cost of deferral:** the predicate stays name/path — the single highest-value guardrail gap, but bounded by the unbypassable-deny point being correct. **Bucket: post-v2.3.**

### GR2-05 — OS-level sandboxing in the emitted posture `[GR2-05 — owner decision pending]`

**Proposal.** Move sandboxing from "worth knowing" to recommended-default for unattended `claude -p` dispatch. GAR-05-corrected bar: the 2026 consensus is microVM-default for LLM-generated code, with gVisor acceptable for compute-heavy/low-I/O; bubblewrap-tier is documented-insufficient (a Claude Code agent has escaped a bubblewrap denylist and disabled its own sandbox). Pragmatic emission: platform-conditional — Claude Code's native `/sandbox` runtime where available (already the actual-isolation pointer in §6.B's worktree note), gVisor+ guidance for Linux unattended tiers; never claim worktree isolation as containment.

**OPEN QUESTION for the human owner.** Effort is high and environment-dependent for a solo operator (laptop realities vs gVisor/microVM assumptions). Adopt as (a) a hard precondition for queue mode, (b) a recommended-default with a loud unsandboxed warning, or (c) keep advisory? The unattended-overnight profile argues ≥(b); the complexity budget argues against (a).

**Seam impact:** none for (b)/(c); (a) adds a dispatch precondition the consumer must honor — a SEAM §4 note would be required. **Cost of deferral:** a destructive action the GR2-04 predicate misses has no second wall; the two items are coupled. **Bucket: post-v2.3.**

### GR2-06 — Re-score the native-checkpointing deferral `[GR2-06 — owner decision pending]` (seam-gated)

**Proposal.** Adopt `enable_file_checkpointing` + rewind-to-last-safe-checkpoint-then-break as a loop-recovery path superior to retry-or-halt on a bad iteration; lock the caveat now — checkpointing tracks file-edit-tool changes only, **not bash-driven changes**, so it is a complement to, never a replacement for, git-at-milestones.

**OPEN QUESTION for the human owner.** The seam's locked constraint governs: new stream events or session flags (`--resume`, `--rewind-files`, checkpoint UUIDs) enter SEAM-CONTRACT §3/§5 under a `seam_version` bump — and the seam already owes the substrate-release re-cut (MAJOR, per the v2.2.0 changelog head). Ride this into that owed re-cut, or hold for the cut after? Riding is cheaper (one consumer re-validation); holding keeps the owed re-cut's scope minimal. Owner's call on re-cut scoping. **This item is out of scope for the Bootstrap-only v2.3.0 fold** — the seam re-cut is a separate session.

**Seam impact:** enum-extension + new stream events/flags = additive seam delta requiring the `seam_version` bump above. **Cost of deferral:** recovery stays retry-or-halt; a salvageable bad iteration costs a full halt. **Bucket: post-v2.3, coupled to the owed seam re-cut.**

### GR2-07 — Lightweight mid-step verification (deferred, constraints locked)

**Deferral with locked constraints (recorded per project discipline; no owner decision needed now):** any future mid-step check MUST be read-only advisory (it never blocks file writes mid-plan — the design reason the boundary discipline exists); MUST run inside the iteration budget, not extend it; and MUST route findings into the iteration summary / the GR2-01 `progress.md` artifact, not a new channel. **Cost of deferral:** a compounding wrong turn is caught at iteration end, not mid-iteration — bounded by max-iterations. Build: medium. **Bucket: post-v2.3.** Revisit after GR2-01/02 land (both reduce this item's marginal value by making wrong turns cheaper to diagnose).

# BOOTSTRAP Companion — Reference Material

**Version:** matches Bootstrap-Protocol-v2-5-0.md 2.5.0.

This file holds reference material that lives alongside the Bootstrap Protocol but is not part of the phase-by-phase wizard flow. Operators consult these sections as needed; the AI reads them when the wizard would otherwise reach for the omitted context.

**Contents:**
- Mental Model — artifact hierarchy and the 70/100 enforcement framing.
- Model Assignment Strategy — which model goes where, and why.
- Post-bootstrap milestones — lifecycle thresholds that trigger additional `.claude/` artifacts.
- What this protocol does not cover — deferred or out-of-scope topics.
- Ecosystem & complementary tooling — first-party Claude tools adjacent to this protocol, and the harness-coupling caveat. Non-normative.
- Phase numbering rationale — why some phases have half-integer numbers.
- Migration notes — one-time-upgrade behavior from older protocol versions.
- Cheat Sheet — daily commands, file/location reference, workflow signals, plus per-mode sub-sections: four-eligibility-shapes (Phase 9.6) and queue-mode pointers (Phase 9.7).
- Glossary — terms used throughout Bootstrap-Protocol-v2-5-0.md.

---

## Mental Model

Before the phases, the artifact hierarchy you'll see throughout:

```
PRD (docs/prd/<name>.md)              ← what we're building and why
  └── Steering docs (.claude/steering/)  ← what's true about this project always
        └── Specs (.claude/specs/<slug>/) ← what's true about this feature
              └── Tasks (.claude/specs/<slug>/tasks/)  ← atomic units of work
                    ├── decisions.md     ← non-obvious choices made during this feature
                    ├── changelog.md     ← spec version changes
                    ├── (optional) loop iteration N           ← only when loop mode is enabled
                    │     └── reviewer subagent run (built-in gate)
                    └── (optional) goal-supervised iteration N ← only when goal-supervised mode is enabled
                          ├── reviewer subagent run (built-in gate)
                          └── judge call (advisory, Haiku by default)

Cross-cutting:
  .claude/learnings/         ← cross-feature insights, post-mortems
     mode-selection.md       ← per-task mode-choice calibration ledger (only if goal-supervised mode enabled)
  .claude/sessions/          ← checkpoints for /clear and /resume; per-task run state when applicable
  .claude/hooks/             ← deterministic gates the model cannot violate
  .claude/loop.sh            ← per-task loop wrapper (optional, only if loop mode opted into at Phase 9.5)
  .claude/loop-config.md     ← operator-tunable loop settings (optional, paired with loop.sh)
  .claude/goal-loop.sh       ← per-task goal-supervised wrapper (optional, only if goal-supervised mode opted into at Phase 9.6)
  .claude/goal-config.md     ← operator-tunable goal-supervised settings (optional, paired with goal-loop.sh)
  .claude/auto.sh            ← queue runner (optional, only if queue mode opted into at Phase 9.7)
  .claude/auto-config.md     ← operator-tunable queue settings (optional, paired with auto.sh)
  .claude/queue/backlog.md   ← persistent task queue (optional, populated by spec-decompose; only if queue mode enabled)
  .claude/queue/run-summary-<timestamp>.md ← morning-after queue-run audit record (one per queue run)
```

Note that not all `.claude/` artifacts are produced at bootstrap. Some — `compliance.md`, `contracts.md`, `metrics/baseline-metrics.md`, `hooks/rollout-schedule.md`, `hooks/worktree-budget.md`, `inventory/tribal-knowledge.md` — apply when the project matures past specific lifecycle thresholds. See the **Post-bootstrap milestones** section for triggers and artifact descriptions. Other artifacts — `loop.sh`, `loop-config.md`, the loop-mode CLAUDE.md addendum — are produced at bootstrap *only if* the operator opts into loop mode at Phase 9.5; `goal-loop.sh`, `goal-config.md`, `learnings/mode-selection.md`, and the goal-supervised-mode CLAUDE.md addendum are produced *only if* the operator opts into goal-supervised mode at Phase 9.6; `auto.sh`, `auto-config.md`, and the `.claude/queue/` scaffolding are produced *only if* the operator opts into autonomous queue mode at Phase 9.7. See each phase for details.

Three concepts that govern everything:

- **Steering docs** = what's true about this project always. Read on every task. Answer "what stack, what conventions, what's off-limits." `design.md` (optional; produced only when `design_steering_enabled` — the UI/UX invariants and honest-use persuasion rules for user-facing work) sits with the other steering docs and is read on every user-facing task when present.
- **Specs** = what's true about this feature. Read only when working on it. Answer "what are we building and what does done look like." Decompose into **tasks** — atomic units sized to fit in half a fresh subagent's context window.
- **Hooks** = what the model cannot violate. Run outside the AI's control as deterministic gates.

The PRD sits upstream of all three. The protocol's job is to turn one PRD into the full set, in the right order, with operator confirmation at each step.

The reason this matters: AI quality degrades when context is bloated, ambiguous, or contradictory. Steering trims context; specs scope it; hooks enforce what context cannot. Spec-driven development with these artifacts is the pattern that holds up at production scale.

**Two-axis autonomy framing — read this once and refer back when the optional modes come up.** From v1.7 onward, the protocol layers optional autonomy on top of the operator-only baseline. By v1.9 there are two independent axes:

```
                    Per-task mechanism (HOW each task runs)
                    ────────────────────────────────────────
                    operator-only    loop mode      goal-supervised
                    (pre-v1.7        (v1.7,         (v1.8, autonomous
                    default)         autonomous,    with judge as
                                     deterministic  advisory signal)
                                     gates only)

Coordination
mechanism
(WHEN tasks run)
─────────────
manual dispatch     baseline         loop.sh        goal-loop.sh
(operator runs                       per task       per task
each task)

queue dispatch      paused*          auto.sh        auto.sh
(runner dispatches                   dispatches     dispatches
in sequence, v1.9)                   loop.sh        goal-loop.sh
```

\* Operator-only tasks in the queue are skipped by the runner — never auto-dispatched (that would defeat the point of classifying them operator-only). The runner continues dispatching other independently-ready tasks around them, and only pauses when no independently-ready work is left and at least one task is awaiting operator action. The operator handles the skipped task interactively, defers it, or removes it from the queue, then resumes.

The two axes are independent: a project can enable any combination. Loop mode without queue mode is the v1.7 design. Goal-supervised mode without queue mode is the v1.8 design. Queue mode requires at least one per-task mechanism to be enabled — the runner has nothing to dispatch with neither enabled. The single-axis lens (autonomy delegation: operator-only → loop → goal-supervised) is still valid as a mental shortcut for projects without queue mode; the two-axis lens is the precise picture once the coordination layer is in play.

Three rules of thumb across both axes:

- **The per-task mechanisms are about HOW a task runs.** Loop mode delegates execution within bounded deterministic gates. Goal-supervised mode adds an advisory judge on top of those gates for tasks with a semantic acceptance component the gates don't fully capture.
- **The coordination mechanism is about WHEN tasks run.** Queue mode does not run tasks; it dispatches the per-task mechanisms in sequence. The "for hours or days" property lives at the coordination layer, never inside any single task's loop.
- **Each layer has its own trust ramp, and the ramps are additive.** 5–10 supervised tasks before trusting loop mode unattended. 10–20 supervised tasks before trusting goal-supervised mode and its judge for this codebase. ~4 weeks of supervised per-task use before trusting queue mode overnight. Calibrate each layer before adding the next; skipping a ramp ships problems supervised use would have caught.

**Guidance vs enforcement — read this twice.** Field data puts CLAUDE.md instruction-following at roughly 70% in practice. For style preferences, that's acceptable. For rules like "don't push to main," "don't delete production data," or "don't modify auth without a spec," 70% compliance is a production incident waiting to happen. **CLAUDE.md is guidance, not enforcement.** Hooks close the gap to ~100% by running deterministic scripts that the model cannot override. The protocol is structured around this division: anything that *must* happen goes in a hook; anything that *should* happen goes in CLAUDE.md, skills, or steering docs. When designing a constraint, ask first: "if the model ignores this 30% of the time, is that catastrophic or annoying?" If catastrophic, it needs a hook.

**Memory layers — three of them, and they're different.** Modern Claude Code has *auto memory* (Claude curates implicitly, native, on by default) alongside *CLAUDE.md* (operator curates explicitly, loaded every session). Our protocol adds a third layer: *`learnings/`* (operator-curated cross-feature insights, loaded on demand). The division:
- **CLAUDE.md** — invariants and pointers to steering. Thin, deliberate, ~80 lines max. *What every session needs to know.*
- **Auto memory** — Claude's notes to itself based on your corrections. Picks up patterns automatically. *What Claude learns from working with you.*
- **`learnings/`** — explicit insights the operator wants persisted across features (post-mortems, "we tried X, it didn't work because Y"). *What humans want to remember intentionally.*

Plus session-scoped: `decisions.md` (within-feature choices, lives in the spec), `sessions/` (checkpoints for `/clear` and `/resume`). The rule of thumb: if it's about *the project*, CLAUDE.md or steering. If it's about *Claude's working style with you*, let auto memory handle it. If it's about *a lesson learned*, write it to `learnings/`.

---

## Model Assignment Strategy

Claude Code supports per-subagent model selection via the `model:` field in agent frontmatter (accepts `opus`, `sonnet`, `haiku`, or full model IDs like `claude-opus-4-8`). It also supports a session-wide subagent default via the `CLAUDE_CODE_SUBAGENT_MODEL` environment variable. Using these well saves significant cost without measurable quality loss — Sonnet 5 approaches Opus 4.8 on agentic coding tasks at roughly 60% of the input/output cost, while Opus 4.8 remains materially better on judgment-heavy work like spec review and architectural decomposition. Above Opus sits **Fable 5**, the most powerful model — reserved, not defaulted (see below).

> **[v2.0.0] Current lineup** (per-MTok standard rates; *confirm against platform.claude.com at implementation — Sonnet 5 pricing is official, the others are secondary-source-corroborated*): **Fable 5** $10/$50 (most powerful, Mythos-class, strictest cyber safeguards) · **Opus 4.8** $5/$25 (flagship reasoning) · **Sonnet 5** $3/$15, intro $2/$10 thru Aug 31 2026 (new default) · **Haiku 4.5** $1/$5 (fastest, cheapest). All except Haiku carry a 1M context window.

**TL;DR for new operators:** if this section is overwhelming, the safe minimum is to run `claude --model opusplan` for the bootstrap wizard (Opus 4.8 plan / Sonnet 5 exec) and let Claude Code's default model handle everything else. You'll get most of the benefit. Come back to the per-subagent table after you've shipped a few features and have a feel for where the rough edges are.

**The principle:** match model strength to *consequence-of-error × judgment-required*, not to role prestige. Opus for low-frequency, high-leverage *thinking* (specs, reviews, architecture). Sonnet 5 for high-frequency, lower-stakes *execution* (implementation against a clear spec). Haiku for read-only or trivial operations. **Fable 5 only where the task is both high-stakes AND beyond Opus's reliable ceiling** — a scalpel, never a default, never on the high-frequency implementer path.

**Plan and availability check (do this first):** the table below assumes you have access to Haiku, Sonnet, Opus, and (for the adversarial row) Fable. Verify before configuring:
- **Pro tier** defaults to Sonnet 5; Opus access is metered and may be limited. If on Pro and Opus access is constrained, treat the "Opus 4.8" rows as "best-available reasoning model" — fall back to Sonnet 5 (xhigh effort) for spec-review and code-review when Opus isn't available. The strategy still works; it's just compressed across fewer tiers.
- **Max / Team Premium** — the table works as-is, with `claude --model opus` selecting Opus 4.8.
- **Fable 5 availability is not guaranteed.** Fable/Mythos access has been export-control-restricted before, and Fable's cyber safeguards may refuse security-adjacent tasks. The adversarial row below therefore defines a mandatory **Fable 5 → Opus 4.8 fallback** on refusal *or* unavailability — never a hard dependency on Fable.
- **Aliases (`opus`, `sonnet`, `haiku`) auto-resolve to the latest version** for that tier. **[v2.0.0 — read this carefully.]** This convenience is also a silent-drift vector: the day Anthropic repoints an alias, `model: sonnet` changes model, cost, *and tokenizer* underneath you with no edit to this file (Sonnet 5's tokenizer emits ~1.0–1.35× the tokens of Sonnet 4.6 for the same input, moving any cost-denominated budget cap). The protocol's stance:
  - **At the Bootstrap subagent-frontmatter layer, aliases remain the convention** — `model: inherit` in particular is semantically required for the integrator and has no ID equivalent, and frontmatter is authored against tier intent, not snapshots.
  - **Drift is accepted and *managed*, not ignored:** record the alias→resolved-ID mapping observed at dispatch time in the audit log, so an alias repoint is *detected as drift* rather than discovered on the bill. (Tessera already logs the Claude Code version at startup; extend it to the resolved model ID per dispatch.)
  - **Where the caller owns the invocation (Tessera dispatch config, `machine.yaml`), pin exact snapshot IDs** (`claude-fable-5`, `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5-*`) — that layer can and should pin.
  - After any alias repoint, **re-baseline `max_cost_usd`** and per-dispatch cost expectations.

**The opinionated default — adopt unless you have reason not to:**

| Phase or skill | Recommended model | Why |
|---|---|---|
| **The bootstrap wizard itself** | Opus 4.8 (xhigh effort default) | Interview, classification, archetype mapping. One-time, judgment-heavy, sets every downstream artifact. Run with `claude --model opus`; xhigh effort is the default for Opus 4.8, no separate flag needed. |
| **`spec-new`** | Opus 4.8 | Translates intent into requirements + testable acceptance criteria. The spec is the contract for everything below. *(Fable 5 only as a logged exception for a genuinely novel/high-ambiguity green-field spec where Opus visibly struggles — deliberate, not default.)* |
| **`spec-review`** | Opus 4.8 | Pure judgment work — finding contradictions, ambiguity, missing edge cases. The single highest-leverage skill in the workflow. |
| **`spec-decompose`** | Opus 4.8 | Vertical slicing requires architectural reasoning. Bad decomposition infects every task. |
| **`plan-review`** | Opus 4.8 | Last gate before code is written. Catching issues here is 10x cheaper than catching them in code review. |
| **`code-review` (subagent)** | Opus 4.8 (effort: high) | Security implications, principle adherence, spec match. Worth Opus given a single missed issue can ship. **Not Fable:** review evaluates a diff against a *known spec* — a bounded search space where Opus's ceiling suffices. Contrast the adversarial row, which searches an open-ended space. |
| **Adversarial review / threat-modeling** (the security lens run after each major fold) *(PRD-process activity — not a wizard-generated subagent; listed here as the model-assignment reference)* | **Fable 5 (spot use) → Opus 4.8 fallback** (effort: high/max) | The candidate place Fable earns its 2× premium: security reasoning searches an *open-ended* space for attacks nobody enumerated, where frontier capability *plausibly* raises the found-threat count. **Mandatory fallback:** Fable's strictest-in-lineup cyber safeguards make this very task the one most likely to be *refused*, and Fable access has been export-control-pulled before — so on safeguard refusal OR unavailability, auto-fall-back to Opus 4.8, logging (model, lens, trigger, reason) so the coverage delta is auditable; the fallback resolves to a *pinned* Opus 4.8 ID. **Premise is a hypothesis, not an assumption:** run the first ~2 cycles dual-model (Fable + Opus on the same corpus) and keep Fable only if realized (post-refusal) coverage beats Opus enough to justify 2×. Periodic spend, never per-dispatch, never on the implementer path. |
| **`implementer` (subagent)** | Sonnet 5 | Spec is the contract; just execute. Sonnet 5 handles the vast majority of coding tasks and closes most of the gap to Opus. **The highest-frequency, highest-token role — the single biggest cost lever. Keep it off Opus/Fable.** |
| **`test-author` (subagent, if TDD)** | Sonnet 5 | Pattern-based test generation against existing acceptance criteria. |
| **`spec-validate`** | Sonnet 5 | Mechanical comparison: does this implementation satisfy the listed acceptance criteria? |
| **`pr-author`** | Sonnet 5 | Templated synthesis of existing artifacts (spec link + validation report + decision log). Candidate for Haiku 4.5 if templating proves reliable. |
| **`decision-log`** | Sonnet 5 | Recording, not deciding. The implementer makes the choice; this skill writes it down. |
| **`checkpoint`** | Sonnet 5 | Structured synopsis of session state. Pattern, not judgment. |
| **`resume`** | Sonnet 5 | Reads checkpoint, summarizes, asks operator to confirm. |
| **`ack-drift`** | Haiku 4.5 | Writes a timestamp file. Trivial. |
| **Built-in `Explore`** | Haiku 4.5 (default) | Read-only codebase search. Already configured this way by Claude Code. Also the right tier for any classification / routing / extraction (mode-classification, provenance tagging, trivial transforms) — high volume, low stakes; never send these to Opus/Fable (the classic overpay trap). |
| **`integrator` (subagent)** | `inherit` (floor Sonnet 5) | Merge conflict complexity varies. Match the main session model (assumes main session is Opus or Sonnet, not Haiku — if running main on Haiku, override with explicit `model: sonnet` for Sonnet 5). `inherit` is semantically required here and has no snapshot-ID equivalent. |
| **Goal-supervised judge** (only if `goal_supervised_mode_enabled`) | Haiku 4.5 | One advisory verdict per iteration on a structured iteration summary plus the diff. Cheap, parallel to deterministic gates, advisory only — never sufficient on its own. Configurable in `.claude/goal-config.md` via `evaluator_model`; raising to Sonnet is sometimes warranted for harder semantic acceptance criteria but rarely Opus (the deterministic gates are still the backstop). The single defensible model-escalation pattern is `--investigate-disagreement` on a halted run (one iteration on Opus 4.8, opt-in only — see Phase 9.6). |
| **Queue-mode summary synthesis** (only if `queue_mode_enabled` AND `summary_synthesis_enabled: true`) | Haiku 4.5 | One synthesis pass at queue-termination time over the per-task artifacts to produce the morning-after summary's "Likely cause based on iteration history" and "Recommended morning actions" sections. The runner itself contains no agent context — this is the runner's one optional Claude-context use. Configurable in `.claude/auto-config.md` via `summary_synthesis_model`; can be disabled entirely (`summary_synthesis_enabled: false`), in which case the summary surfaces raw data only. |

**Always set `model:` explicitly.** If you omit the field, Claude Code defaults to `inherit`, which silently uses whatever model the calling session is on. This is rarely what you want — a code-review subagent shouldn't run on whatever model happened to be active. The protocol requires explicit `model:` on every subagent definition for this reason. The wizard in Phase 7 enforces this.

**`opusplan` as a simpler alternative:** Claude Code supports `claude --model opusplan` which runs Opus during planning mode and Sonnet during execution. Roughly 80% of the benefit of full per-skill assignment with zero configuration. **What you lose with `opusplan`:** the `code-review` subagent runs on Sonnet (not Opus), so deep review is lighter; the `Explore` subagent doesn't drop to Haiku, so cheap operations cost more; per-skill tuning isn't available. For solo work where the spec quality is high, this is fine. For higher-stakes projects, full per-skill assignment is worth the configuration time.

**Cost reality check:** the Phase 7 cost disclosure ("subagents use 4-7x more tokens than single-agent sessions") assumes uniform Opus across all subagents. With the mixed-model split above, the effective multiplier is closer to 2-3x because the implementer subagent — which does the bulk of token-heavy work — runs on Sonnet. This is what makes the spec-driven workflow viable on usage-limited plans rather than burning through limits.

**Cost reality check for the autonomous modes.** The judge call in goal-supervised mode adds one Haiku-class call per iteration — negligible against the main-model spend in absolute terms, but real and worth tracking. A 10-iteration goal-supervised task adds ~10 judge calls. Queue mode multiplies by the task count: a 12-task overnight run averaging 6 iterations per task is ~72 judge calls if every task is goal-supervised — still small individually, but the main-model spend is the dominant term and scales linearly with both task count and iteration count. Set explicit token or task budgets for the first several queue runs and review actual consumption before raising them; `goal-config.md` and `auto-config.md` are the configuration surfaces. The optional summary-synthesis call in queue mode is one Haiku-class call per queue run regardless of task count — strictly negligible.

**Known limitation worth flagging:** there's a known issue where a parent agent spawning child agents via the `Agent()` tool may not honor the configured model — the AI chooses autonomously and tends toward Sonnet for `Explore`-style children regardless of configuration. If you need rigid enforcement, set `CLAUDE_CODE_SUBAGENT_MODEL` as an environment variable rather than relying on frontmatter alone. **Trade-off:** the env var sets a default for *all* subagents that use `inherit` — so it won't override explicit `model:` fields, but it will change the default for forgotten ones. For this protocol, this matters mainly if your custom subagents spawn further subagents — currently none do, so frontmatter is sufficient.

**Tuning over time:** start with the table above. Watch for these signals:
- **Early signal (after 2-3 features):** if `code-review` keeps surfacing issues `implementer` should have caught — your specs may be too loose, not your implementer model. Tighten specs first; only upgrade implementer to Opus if specs are genuinely tight and Sonnet still misses.
- **Mid-term signal (after ~10 features):** if Opus reviewers rarely surface real issues, the implementer is good enough that review is mostly ceremonial — downgrade reviewer to Sonnet.
- **Cost signal (anytime):** if you're routinely hitting usage limits, look at which subagents fire most often; downgrade those first. The implementer is usually the largest token consumer.

The defaults are a starting point, not a ceiling.

---

## Post-bootstrap milestones

The bootstrap protocol creates `.claude/` infrastructure based on what's knowable at project start. Some artifacts that brownfield projects need from day one (because their information already exists) become applicable to greenfield projects only when the project crosses specific thresholds.

This section documents those thresholds and the artifacts to produce when each fires. Consult this section when a milestone hits — none of these require action at bootstrap, and none of them appear in Phase 0.5's bootstrap-time file manifest.

### Trigger table

| Milestone | Artifact | Source for detailed pattern |
|---|---|---|
| First user or customer in a regulated category (EU resident → GDPR; PHI processing → HIPAA; payment card data → PCI-DSS; medical device → IEC 62304; US federal agency → FedRAMP; AI/ML in regulated context → FDA AI/ML PCCP); OR pursuing SOC 2 certification | `.claude/steering/compliance.md` — per-framework controls, where compliance artifacts live (POA&M / DHF / SSP / RoP / ROC), audit-trail rules, change-control regime declarations | RETROFIT v1.5.0 R0 step 10 (line 548) for the seven-question detection; R5 step 3 (line 1045) for the `compliance.md` format |
| First public API release; first external integration goes live; first cross-component contract solidifies (Platform archetypes) | `.claude/steering/contracts.md` — listed integration points with machine-readable contracts (OpenAPI / JSON Schema / Avro / Protobuf) plus operator-readable summary | RETROFIT v1.5.0 R5 step 3 (line 1041) for the `contracts.md` format |
| ~30 commits OR first production deploy (whichever comes first) | `.claude/metrics/baseline-metrics.md` — lead time, change failure rate, test coverage, lint conformance, spec coverage, DORA tier classification. Schedule 30/60/90-day review cadence going forward. | RETROFIT v1.5.0 R0 step 8 (line 531) for the metric definitions; R7 step 4 (line 1154) for the review cadence pattern |
| First additional contributor joins (project moves from solo to multi-developer) | `.claude/hooks/rollout-schedule.md` — graduated warn→block schedule (default 2-week ramp for new contributor onboarding) plus bypass-rate monitoring | RETROFIT v1.5.0 R8.A.6 (line 1324) for the rollout discipline pattern |
| Codebase total source size exceeds 1GB | `.claude/hooks/worktree-budget.md` — expected disk usage per worktree session (~5x codebase size), per-worktree DB and Docker volume conventions, sequential-vs-parallel guidance for codebases over 5GB | RETROFIT v1.5.0 R8.A.7 (line 1348) for the worktree budgeting pattern |
| First team handoff (new contributor who needs to ramp up on project history) | `.claude/inventory/tribal-knowledge.md` — DO NOT TOUCH list, sleeping bugs, magic configs, war stories, 3am-call routing per subsystem | RETROFIT v1.5.0 R0 step 9 (line 540) for the five-question interview |
| First ~20 completed tasks in any autonomous mode (only if `goal_supervised_mode_enabled`) | Mode-selection calibration review — operator reads accumulated entries in `.claude/learnings/mode-selection.md`, looks for divergences between classifier recommendations and operator choices and any "felt wrong" patterns, decides whether to adjust the recommendation rule's flip-properties for this codebase. The artifact already exists (initialized empty at Phase 9.6); the milestone is the review pass, not a new file. May be invoked via a calibration-review skill if the operator added one. | Bootstrap-Protocol-v2-5-0.md Phase 9.6 "Calibration mechanism" section for the per-task assessment format and the recommendation-rule-tuning posture |
| Queue-mode trust-ramp completion — ~4 weeks of supervised queue runs, progressing from 30-minute supervised runs to short overnight runs (only if `queue_mode_enabled`) | Trust-ramp completion check — operator reviews `queue_runs_history` in `.bootstrap-state.json` plus the accumulated `run-summary-<timestamp>.md` files, confirms the runner correctly dispatches per-task wrappers, observes terminal states, and produces useful summaries, and confirms the morning-after review experience is tractable and not overwhelming. No new artifact; the milestone gate is "ready to use queue mode for full overnight or multi-day runs." Before this gate, queue mode should be operated within the week-by-week ramp from Phase 9.7. | Bootstrap-Protocol-v2-5-0.md Phase 9.7 "Trust ramp — recommended adoption sequence" section for the week-by-week posture and the Phase 10 handoff for the broader review-as-autonomy-grows discipline |

### Why these are post-bootstrap, not bootstrap-time

Each artifact requires information that doesn't exist at bootstrap time:

- **Compliance posture** depends on actual users and customers; greenfield-time commitments to "we won't have EU users" or "we won't pursue SOC 2" age into liabilities.
- **Boundary specs** are most useful when integrations have actually solidified, not when they're hypothetical PRD line items.
- **DORA metrics** need git history and production deploys to compute meaningfully; before that they're all N/A or 0.
- **Hook rollout discipline** accommodates existing developer habits; solo greenfield has none to overcome.
- **Worktree budgeting** depends on actual codebase size; greenfield's growth trajectory is unpredictable at start.
- **Tribal knowledge** captures prior-maintainer signal; solo greenfield has no prior maintainers to interview.
- **Mode-selection calibration** requires accumulated per-task assessments comparing classifier recommendation against operator choice; at bootstrap time there are no completed tasks to assess. The recommendation rule's flip-properties are a starting prior, not a tested heuristic — review evidence builds over the first ~20 tasks.
- **Queue-mode trust-ramp completion** requires real operating time on the runner to characterize how it interacts with this codebase. The first weeks reveal which classifications are wrong, which dependencies break, and how much review the morning-after summary actually generates; only then can the operator decide whether full overnight or multi-day runs are appropriate.

### What to do when a milestone fires

Each artifact is RETROFIT-flavored in its current canonical form. To use it for a greenfield project that has matured:

1. Read the relevant RETROFIT v1.5.0 section (line numbers in the table above).
2. Adapt the pattern to your context — most of the structure transfers directly; the few brownfield-specific framings (e.g., "capture pre-retrofit state") become "capture current state."
3. Place the artifact under `.claude/` per the table above. New directories (`metrics/`, `inventory/`) can be created if not yet present; commit them to the repo.
4. If the milestone has long-term implications (e.g., `compliance.md` introduces audit-trail requirements), schedule the appropriate ongoing review or operational practice.

### Note for AI assistants reading this section

When an operator asks for help with a post-bootstrap artifact (e.g., "add HIPAA compliance to my project"), use this section as the entry point. Read the relevant RETROFIT v1.5.0 reference for the detailed pattern, then produce the artifact tailored to the project's current state. This is normal operator work post-bootstrap, not a special protocol mode — no state-file fields, no migration prompt, no phase number.

---

## What this protocol does not cover (deferred or out of scope)

- **Migration of large existing codebases** (>500 files, multi-year history). The protocol assumes the operator can hold the structure in their head. For larger codebases, a separate retrofit protocol is needed.
- **Multi-team coordination.** The bootstrap is single-operator. Team practices for ongoing steering-doc evolution are not specified beyond "treat it like code review."
- **Skill / agent file format details.** These vary by AI tooling and version. The AI should consult current docs or existing project conventions rather than rely on this document.
- **Specific hook implementation details** (exact regex patterns, exit codes, shell idioms). The protocol specifies what each hook does; the AI writes the implementation against the project's tooling.
- **Internationalization and localization.** Out of scope for the bootstrap; can be added per-project as a section in `tech.md`.
- **Telemetry, analytics, and event tracking policy.** Out of scope for the bootstrap; for projects that need it, treat as an extension to `secrets.md` (privacy concerns) and `tech.md` (technical implementation).
- **Database migration policy details.** Phase 2 marks migration files as "do not touch" by default but doesn't prescribe how migrations are written, reviewed, or deployed. Project-specific.
- **Accessibility audit and compliance frameworks** (WCAG, ADA). When `design_steering_enabled`, `design.md` carries an accessibility *invariant* — a design-time floor the implementer applies per change (keyboard/focus, contrast, target size, no color-only signalling). What stays out of scope is ongoing **audit** and formal conformance *certification*: the protocol has no process for continuous WCAG/ADA testing. The project's specific baseline lives in `tech.md` / `design.md`'s Project-specifics; certifying against it is a separate effort.
- **Performance benchmarking infrastructure.** Phase 5 mentions performance budgets in CI/CD but doesn't establish benchmarking practice.
- **On-call runbooks and incident response.** Out of scope; produce per-feature as needed.
- **Post-mortem template.** Recommended location: `learnings/post-mortems/`. Not generated by bootstrap.
- **Goal-supervised mode as a "let Claude do everything" mode.** Goal-supervised mode runs one task at a time, just like loop mode. Running an entire spec, feature, or PRD through goal-supervised mode is explicitly out of scope.
- **Goal-supervised mode as a replacement for loop mode.** The two modes are sibling tracks for different task classes — classified per task at decomposition time. A project doesn't pick "one or the other"; it picks per task, and the recommendation rule routes eligible-for-both tasks.
- **Goal-supervised mode as a quality maximizer.** The judge is advisory; the deterministic four-criterion gate is the backstop. Operators who want maximum quality stay operator-in-the-loop. Configuration paths that would remove the deterministic gate (e.g., a hypothetical `--trust-evaluator` flag) are explicitly out of scope.
- **Goal-supervised mode as a judge-as-sole-gate option.** Even with operator override, removing the deterministic four-criterion gate is not supported. The whole protocol's value is in stacking independent gates.
- **Model escalation on max-iterations.** A loop that hits max-iterations is a signal about the spec, not about the model. Escalating Sonnet → Opus on iteration-cap-hit weakens the safety net (pushes operator review back), worsens cost shape at exactly the wrong moment, and masks the "loop mode masks deeper problems" risk. The single defensible model-escalation pattern is `--investigate-disagreement` (opt-in, operator-initiated, one iteration on Opus); other escalation patterns are out of scope.
- **Queue mode as a per-task mechanism.** Queue mode does not run tasks; it dispatches the existing per-task wrappers. Loop mode and goal-supervised mode behave identically inside or outside a queue run. Re-implementing per-task logic inside the runner is explicitly out of scope.
- **Queue mode as a "broader loops" mode.** The temptation to make individual loops wider — higher iteration caps, broader goal conditions, agent-chosen next steps — must be resisted. The "for hours or days" property lives at the coordination layer, not inside any single task's loop. Configuration paths that would expand any per-task mechanism's scope when invoked under the queue are out of scope.
- **Queue mode as a license to skip operator review.** The morning-after summary makes review tractable; it does not replace it. Operators who find themselves reviewing less as autonomy grows have inverted the safety model.
- **Queue mode as a license to skip the trust ramp.** The protocol explicitly does not support skipping the multi-week ramp. Operators who run unattended overnight in the first week ship problems supervised use would have caught.
- **Queue-mode override of urgent escalations.** The "urgent escalations halt the queue" rule is non-configurable. Configuration paths that would let an operator continue past an urgent escalation criterion are out of scope.
- **Queue mode as a task-generation mode.** The runner does not invent tasks, decompose features autonomously, or modify classifications. All tasks come from `spec-decompose` with operator confirmation. Auto-decomposition inside the runner is out of scope.
- **Queue mode as an infinite-running mode.** Even with no explicit budgets, the queue terminates when the backlog is empty. A "wait for new tasks and continue" mode is explicitly out of scope; it invites the operator-walks-away-forever pattern.

---

## Ecosystem & complementary tooling

**Non-normative.** Nothing here changes the protocol or its conformance surface. This section orients an operator to first-party Claude tooling that sits *adjacent* to the bootstrap workflow, and names one portability caveat the protocol's design implies. It is reference framing — *what fits, what to track, what not to assume* — not an instruction to install anything. The protocol's own tool stance is canonical in Bootstrap-Protocol-v2-5-0.md Phase 6.5; this section does not restate or override it.

**The official Claude Code plugin marketplace.** Anthropic maintains a curated plugin directory (internal Anthropic-developed plugins plus vetted third-party ones), installable through Claude Code's own plugin system. This is directly relevant because the bootstrap installer *is itself* a Claude Code plugin (`plugin/plugin.json` plus the `bootstrap-interview` / `bootstrap-apply` commands), and the marketplace plugin structure — `.claude-plugin/plugin.json`, optional `.mcp.json`, `commands/`, `agents/`, `skills/` — is the same `.claude/` surface this protocol generates. The marketplace is the natural distribution path for this protocol and the right place to look for companions that do *not* conflict with the deliberately thin, hand-authored Phase 8 `CLAUDE.md`. The Phase 6.5 anti-pattern still applies: any plugin that auto-writes folder-level `CLAUDE.md` files must be reconfigured to a different path or have that feature disabled.

**The `ralph-wiggum` lineage (track for divergence, do not adopt).** Phase 9.5 already cites Anthropic's official `ralph-wiggum` plugin and Geoffrey Huntley's Ralph Loop pattern as the inspiration for loop mode. The relationship is deliberate *divergence*, not reuse: this protocol's loop mode is a safety-hardened reimplementation that uses fresh-session-per-iteration rather than a Stop-hook-in-session mechanism (which is what makes the self-healing tier-3 reset clean). Track the upstream pattern for ideas, but adopting it directly would reintroduce the in-session-bloat failure mode loop mode exists to avoid. This is a watch-relationship, not an integration.

**GitHub MCP and Claude Context (already Tier-1).** These are not new recommendations — Phase 6.5 already names GitHub MCP as Tier-1 for any project using GitHub and Claude Context (semantic codebase search) as Tier-1 for codebases over ~200 files. They are listed here only so the ecosystem picture is complete: of the broader tool landscape, these two are the ones the protocol already endorses at start, and they compose cleanly with the spec-driven workflow and the Phase 5 / spec-gate machinery. Everything else stays Tier-2 (add only on a confirmed pain point) per Phase 6.5.

**Inbound automation surfaces (compose, but mind the trust-ramp boundary).** Claude Code can be triggered from outside the terminal — tagging the agent on a GitHub PR/issue, and hosted "routines"/scheduled tasks that run on managed infrastructure independent of the operator's machine. These compose with this protocol (the protocol governs *what* gets built and *how* it is gated locally; the inbound surface governs *when* a run is triggered). The caveat: queue mode (Phase 9.7) is the protocol's own answer to "when do tasks run unattended," and its entire safety thesis is the multi-week trust ramp. Hosted/managed unattended execution moves that boundary onto infrastructure the trust ramp does not directly observe. An operator combining the two should understand they are two different answers to the same question and should not let an inbound automation surface short-circuit the Phase 9.7 ramp.

**Harness-coupling caveat (portability honesty).** This protocol is deliberately coupled to Claude Code's execution model: it generates `.claude/` hooks, `settings.json` event/matcher wiring, sentinel and `flock` idioms, and subagent definitions that assume Claude Code semantics. Other agentic-coding harnesses exist (some open-source, model-agnostic, self-hostable) and the ecosystem has visibly fragmented, but the generated artifacts are *not* portable to them without translation — the hook lifecycle, the `claude -p` per-iteration mechanism, and the drift-detector cooperation contract are Claude-Code-specific by construction. This is a stated scope boundary, not a defect: the protocol's enforcement guarantees depend on that specific harness's semantics. An operator evaluating harness portability should treat the entire `.claude/` output as Claude-Code-targeted and budget for a re-derivation, not a port, if they ever change harnesses.

---

## Phase numbering rationale

Phases are numbered 0 through 10 with some half-integers (2.5, 2.7, 6.5, 7.5, 7.6, 9.5, 9.6, 9.7). The half-integers are not version artifacts — they're semantic. Phases 1–5 are steering. Phase 6 is enforcement. Phase 7 is workflow. Phase 8 is integration. Half-integer phases are tightly related to their parent:

- **2.5 (deps)** and **2.7 (secrets)** are tech-adjacent steering.
- **6.5 (tools/MCP)** configures the runtime alongside hooks.
- **7.5 (spec versioning)** defines workflow rules for the skills installed in 7.
- **7.6 (spec roster derivation)** populates the INDEX initialized in 7 with `planned` rows derived from the PRD.
- **9.5 (autonomous loop mode)** layers an optional execution mode on top of the smoke-tested workflow from 9.
- **9.6 (goal-supervised mode)** layers a *sibling* optional execution mode alongside 9.5 — independently opt-in, independently generated, classified per task at decomposition time.
- **9.7 (autonomous queue mode)** layers an optional *coordination* mode *above* 9.5 and 9.6 — it does not run tasks itself but dispatches the per-task mechanisms from 9.5 and 9.6 in sequence, and requires at least one of those to be enabled.

The relationship between 9.5/9.6 and 9.7 is the two-axis structure detailed in Phase 9.7: per-task mechanism (HOW each task runs) is independent from coordination mechanism (WHEN tasks run). This grouping helps the AI route questions and helps the operator skip subgroups coherently.

---

## Migration notes

The protocol writes `bootstrap_protocol_version` to `.claude/.bootstrap-state.json`. A v2.0.0 wizard always writes `"2.0.0"` to this field on first run; the field records *which protocol document the state file is committing to*, independent of which autonomous-mode flags are enabled. **[v2.0.0]** The state file additionally records `gate_substrate` (`"shell"` | `"sdk-callable"`) — the installed enforcement substrate, tracked independently of the document version per the v2.0.0 conformance note. A v2.0.0 wizard writes `gate_substrate: "shell"` today; only a future 2.x release that applies the SDK gate migration writes `"sdk-callable"`.

**Migrating from 1.x to 2.0.0.** Non-destructive as always — the wizard backs up the original state file to `.bootstrap-state.json.pre-2.0.0` before writing. The 1.x→2.0.0 migration is **state-schema-only today**: it updates `bootstrap_protocol_version` to `"2.0.0"` and adds `gate_substrate: "shell"`. It does **not** change the installed gates — the shell suite remains operative, so a migrated 1.9.0 project behaves identically post-migration. The behavioral migration (shell gates → SDK `PreToolUse` callables, native worktree routing) is a *separate, future* 2.x step gated on the main-diff reconciliation flagged in the protocol header; when it ships, it will carry its own migration entry and flip `gate_substrate`. The v2.0.0 Model Assignment Strategy remap (Sonnet 5 / Opus 4.8 / Fable-with-fallback / Haiku 4.5) applies immediately on migration since assignments resolve through aliases and per-agent frontmatter, not the state file.

**Migrating from 2.0.0 to 2.0.1.** No migration. v2.0.1 is a wording-only PATCH: the Phase 0 verbatim question strings for 9.6/9.7 are restyled (installer-conformance strings — the bump is what permits the new phrasing), the morning-after summary's required structure gains an `Ended because` line (stable `exit_reason` code + plain sentence), and a non-normative grade-audit proposal subsection is appended. No state-schema change; a v2.0.1 wizard writes `bootstrap_protocol_version: "2.0.1"`. Gates, hooks, sentinels, wire/state field names, and IC-1..IC-7 are untouched; commit-pinned consumers are unaffected.

**Migrating from 2.0.x to 2.1.0 (substrate release).** State-schema-compatible. 2.1.0 is the implementation's Milestone B: the SDK gate module `.claude/sdk_gates/gates.py` is emitted on all installs, and `gate_substrate: "sdk-callable"` becomes grantable — written only when the config requests it and the `lib/ic_checks.py` IC-1..IC-7 gate passes; otherwise the install refuses loudly and existing state keeps `"shell"`. A 2.1.0 wizard writes `bootstrap_protocol_version: "2.1.0"`. Operators who never request the substrate see no behavioral change. Retrofit installs refuse `sdk-callable` (retrofit stays shell-era). This entry retro-documents the release; at the time it existed only in the implementation changelog.

**Migrating from 2.1.0 to 2.2.0 (usage-limit + gap closure).** State-schema-compatible; no destructive migration. 2.2.0 adds reset-aware usage-limit handling bound into the wrapper skeletons' comment contract, adopts the deliverable contract (B-1(b)), blesses the emitted goal-config extras, and requires the skeleton comments to enumerate the `exit_reason` enum and run-summary structure. A v2.2.0 wizard writes `bootstrap_protocol_version: "2.2.0"`. Two additive changes touch persisted data, both backward-compatible: (1) the `exit_reason` domain on `queue_runs_history` entries gains one value, `"usage-limit-reset-abandoned"` — written when the runner observes a dispatched task abandon a usage-limit wait and terminates the run (graceful shutdown; **[AR2-01]** terminal at the queue level, counted toward neither halt threshold). An older tool reading a newer state file will encounter an `exit_reason` it does not recognize, which is the forward-compat case the state-file-compat open question (Proposed-revisions B-4 in the protocol) already flags; a newer tool reading an older state file sees nothing new; (2) `loop-config.md` and `goal-config.md` gain three keys (`usage_limit_wait`, `usage_limit_max_wait_seconds`, `usage_limit_wait_jitter_seconds`). **Existing config files without these keys are valid** — the wrappers apply the documented defaults (`reset-aware`, `21600`, `60`) when a key is absent, so a project upgraded in place keeps working with no config edit and picks up reset-aware waiting automatically. To opt out and preserve exact pre-2.2.0 behavior, set `usage_limit_wait: off`: **[AR2-02]** with `off` the usage-limit branch is disabled and a rejection-bearing exit is handled by the ordinary transient path (sleep briefly, retry once, then halt) — not an immediate halt. Gates, hooks, sentinels, IC-1..IC-7, and `gate_substrate` are untouched. **[AR2-04]** Seam impact: these deltas introduce no MAJOR trigger of their own, but they do not ship as a standalone seam MINOR — the seam contract still `binds` `bootstrap_protocol: 2.0.0` by commit, so entering the wire rides inside the owed substrate-release `binds` re-point (a seam MAJOR per §8.1a, since it drops the previously-satisfying 2.0.0), which also owes a §5 stream-event row for `rate_limit_event`. Consumer re-validation happens at that re-cut. The behavioral change consumes the Claude Agent SDK's `rate_limit_event` / `RateLimitInfo` stream contract, which is available on the current shell substrate today (it is a stream-output contract on `claude -p`, not a gate-substrate feature), so it works identically on `"shell"` and `"sdk-callable"` substrates.

**Migrating from 2.2.0 to 2.3.0 (GR2 adoptable fold).** State-schema-compatible; no destructive migration; **no seam change, and the Tessera pin is unaffected**; the owed substrate-release seam re-cut is untouched and still owed. A v2.3.0 wizard writes `bootstrap_protocol_version: "2.3.0"`. **What a v2.2.0 workspace must add on upgrade — three additive artifacts/behaviors:** (1) a per-task `.claude/specs/<slug>/progress.md` (`Status` / `Completed` / `In flight` / `Failed approaches` with do-not-retry flags), created at task start, committed, that **links to** — never duplicates — `decisions.md`, `learnings/`, and the latest checkpoint, and is read first at autonomous-mode priming so dead ends are not re-attempted; (2) per-iteration trajectory retention at `.claude/logs/trajectory-<task-id>-<iter-n>.jsonl` (the stream JSON is already emitted by the v2.2.0 `--output-format stream-json --verbose` dispatch; gitignored under the existing `.claude/logs/` rule; pruning them on a stated retention window is part of the operator-completed loop's obligation — the 7-day state policy covers `.claude/sessions/`, not `.claude/logs/`), linked from a new required `Trajectory` line in `loop-final-<task-id>.md`; (3) a seeded `.claude/steering/assumption-ledger.md` recording which defaults are model-generation-calibrated (drift thresholds, tier-3 hard reset, token multipliers, max-iterations) and their re-validation triggers, surfaced fail-loud but non-blocking on any pinned-model or runtime-floor change. **What it may ignore — everything pending:** the Proposed-revisions GR-2 subsection (GR2-03b interactive compaction, GR2-04 intent-class predicates, GR2-05 sandboxing, GR2-06 native-checkpointing re-score, GR2-07 mid-step verification) is all owner-decision or deferred and requires no workspace change. **Nothing removed or renamed:** no state-file fields change; gates, hooks, sentinels, wire/state field names, IC-1..IC-7, and `gate_substrate` are untouched; commit-pinned consumers are unaffected. Existing workspaces that never add the three artifacts keep working unchanged — the artifacts are additive and operator-adopted. Seam impact: **none** (no wire surface).

**Migrating from 2.3.0 to 2.4.0 (operator-opt-in observability).** State-schema-compatible; no destructive migration; **no seam change, and the Tessera pin is unaffected**; the owed substrate-release seam re-cut is untouched and still owed. A v2.4.0 wizard writes `bootstrap_protocol_version: "2.4.0"`. **What to add on upgrade — one opt-in, off by default:** the state file gains a top-level `telemetry_export_enabled` flag (default `false`). A workspace that leaves it `false` behaves exactly as under 2.3.0 — nothing is emitted, nothing changes. If the operator sets it `true` (via the Phase 0 step 6 decision, or by re-running the wizard later), the wizard emits one committed steering doc, `.claude/steering/telemetry.md` (the `bootstrap.protocol_version` and `bootstrap.archetype` values in its `OTEL_RESOURCE_ATTRIBUTES` seed are stamped at emission from state and config, not static literals, so an in-place upgrade that re-runs the wizard refreshes them — **[TAR-01]**), that documents Claude Code's **native** opt-in OpenTelemetry surface (`CLAUDE_CODE_ENABLE_TELEMETRY` + the `OTEL_*` exporter variables) pointed at a backend the operator runs, and names the redaction-clean events that map to Bootstrap mechanism health (gate decisions, hook outcomes, compaction, API errors/retries, permission-mode changes, per-subagent token usage). **What it does not do:** it opens no socket, changes no gate, hook, sentinel, wire, or runtime behavior, and transmits nothing itself — export goes only to the operator-configured OTLP endpoint, never to Anthropic and never to the Bootstrap maintainers, with prompts/tool-arguments/file-contents/API-bodies redacted unless the operator deliberately enables the corresponding `OTEL_LOG_*` flags against their own backend. **What it may ignore:** the "phone-home" alternative (protocol-owned egress to the maintainers) was considered and **rejected** — recorded in the PRD head note and the adjacent-tooling framing — on GAR-04 category-mismatch, wire-surface/exfiltration threat, and complexity budget; there is nothing to install for it. An older tool reading a state file that carries `telemetry_export_enabled` treats the unknown field as inert (same forward-compat posture as the `exit_reason` addition; the state-file-compat open question in the protocol's Proposed-revisions still governs the general posture); a newer tool reading an older state file applies the `false` default. Gates, hooks, sentinels, IC-1..IC-7, and `gate_substrate` are untouched; commit-pinned consumers are unaffected. Seam impact: **none** (no wire surface).

**Migrating from 2.4.0 to 2.5.0 (design steering).** State-schema-compatible; no destructive migration; **no seam change, and the Tessera pin is unaffected**; the owed substrate-release seam re-cut is untouched and still owed. A v2.5.0 wizard writes `bootstrap_protocol_version: "2.5.0"`. **What to add on upgrade — one opt-in flag. Default `false`; opt-in** — a workspace that leaves it `false` and never adds `design.md` behaves exactly as under 2.4.0. If the operator sets it `true` (via the Phase 0 step 6 decision, or by re-running the wizard later), the wizard emits `design.md` and offers the optional skill. A newer tool reading an older state file **applies the `false` default** — the field's absence is not an error (same forward-compat posture as `telemetry_export_enabled` and the `exit_reason` addition; **not** the IC-3 write-into-old-files mechanism — nothing is written into old state files at read time). When enabled, the wizard emits `.claude/steering/design.md` (committed) and offers the optional advisory `design-review` skill. **What it does not do:** it opens no socket, changes no gate, hook, sentinel, wire, or runtime behavior; the `design-review` skill flags and never blocks. **Honest scope (DELTA-03):** that skill is a design-time floor and an advisory flag, not a compliance control — against LLM-generated UIs that can reproduce dark patterns at scale it *reduces but does not prevent* dark-pattern emission, and it is no substitute for legal review (FTC dark-patterns enforcement, EU Digital Fairness Act). Its real weight lives in `design.md`'s ranked honest-use prose; the skill is a second, non-blocking pass (Path C hook enforcement stays rejected). Existing workspaces that leave the flag at its default and never add `design.md` behave exactly as under 2.4.0. Gates, hooks, sentinels, IC-1..IC-7, and `gate_substrate` are untouched; commit-pinned consumers are unaffected. Seam impact: **none** (no wire surface).

When invoked against a state file written by an older protocol version, the wizard offers a one-time migration. Migrations are non-destructive — the wizard backs up the original state file to `.bootstrap-state.json.pre-<version>` before writing.

**Migration from v1.6.x** (state files written by v1.6.0 or v1.6.1):
- Add `bootstrap_protocol_version`, `loop_mode_enabled: false`, and `loop_in_flight: []` to the state file.
- Operators who never opt into loop mode during the migration see no behavioral change beyond the new fields existing.

**Migration from v1.7.x** (state files written by v1.7.x):
- Add `goal_supervised_mode_enabled: false` and `goal_in_flight: []` to preserve pre-v1.8 behavior.
- Existing tasks classified under v1.7 (with `loop_eligible` set but no `goal_supervised_eligible` field) are treated as loop-mode-eligible by default; the operator may re-classify by re-running `spec-decompose` if desired.

**Migration from v1.8.x** (state files written by v1.8.x):
- Add `queue_mode_enabled: false` and `queue_runs_history: []` to preserve pre-v1.9 behavior.
- Queue mode requires at least one of `loop_mode_enabled` or `goal_supervised_mode_enabled` to be true during the migration; if neither is, the wizard refuses the queue-mode opt-in and explains why.
- Existing task definitions do **not** need re-classification — `.claude/queue/backlog.md` is populated by `spec-decompose` from the point of opt-in forward; older tasks completed before queue mode was enabled simply do not appear in the queue.

Across all migrations: operators who never opt into the newer modes see no behavioral change beyond the new state-file fields existing. The fields exist but stay empty, and no new files (`loop.sh`, `goal-loop.sh`, `auto.sh`, etc.) are generated for modes that aren't opted into.

---

## Cheat Sheet

After bootstrap completes, these are the commands and conventions you'll use daily:

| Command | When to use |
|---|---|
| `/spec-new <slug>` | Start a new feature from a PRD section |
| `/spec-review <slug>` | Find contradictions before decomposing |
| `/spec-decompose <slug>` | Turn spec into atomic tasks |
| `/plan-review <slug>` | Approve task plan before implementation |
| `/spec-validate <slug>` | Check implementation against acceptance criteria |
| `/checkpoint` | Save session state before `/clear` |
| `/clear` | Reset working context (built-in) |
| `/resume [timestamp]` | Load most recent (or specified) checkpoint |
| `/ack-drift` | Suppress drift alerts for current session |
| `/quiet on` / `/quiet off` / `/quiet 2h` | Mute audio alerts (visual continues) |
| `/quiet-task-done` | Mute task-done audio specifically |
| `/context` | Show context window utilization (built-in) |
| `/pr-author <slug>` | Generate PR description with spec link + validation report |

| File / location | Purpose |
|---|---|
| `docs/prd/<name>.md` | Product requirements (source of truth for "what and why") |
| `.claude/steering/*.md` | Project invariants, read on every task (includes `assumption-ledger.md`) |
| `.claude/specs/<slug>/requirements.md` | Per-feature contract; versioned |
| `.claude/specs/<slug>/tasks/*.md` | Atomic task units |
| `.claude/specs/<slug>/decisions.md` | Within-feature non-obvious choices |
| `.claude/specs/<slug>/progress.md` | Per-task status + failed-approaches ledger (links, never duplicates) |
| `.claude/specs/<slug>/changelog.md` | Spec version history |
| `.claude/learnings/*.md` | Cross-feature insights |
| `.claude/sessions/*.md` | Session checkpoints |
| `.claude/logs/trajectory-*.jsonl` | Per-iteration reasoning/tool trajectory for unattended runs (gitignored; pruning is the operator-completed loop's duty — the 7-day state policy covers `.claude/sessions/`, not `.claude/logs/`) |
| `.claude/steering/telemetry.md` | Only when `telemetry_export_enabled` — how to point Claude Code's native opt-in OpenTelemetry at your own backend to watch mechanism health (committed; the protocol sends nothing itself) |
| `.claude/hooks/*.sh` | Deterministic gates |
| `.claude/agents/*.md` | Subagent definitions |
| `CLAUDE.md` | Thin index, loaded on every session |
| `.claude/steering/compliance.md` | Per-framework regulatory controls (created when regulatory obligations apply; see Post-bootstrap milestones) |
| `.claude/steering/contracts.md` | Integration-point boundary specs (created when external integrations go live) |
| `.claude/metrics/baseline-metrics.md` | Lead time, failure rate, coverage, DORA tier (created at ~30 commits or first deploy) |
| `.claude/hooks/rollout-schedule.md` | Graduated hook enforcement schedule (created when a second contributor joins) |
| `.claude/hooks/worktree-budget.md` | Disk and resource expectations (created when codebase exceeds 1GB) |
| `.claude/inventory/tribal-knowledge.md` | Project-history capture (created at first team handoff) |
| `.claude/loop.sh` | Autonomous-loop wrapper script (created only when loop mode opted into at Phase 9.5) |
| `.claude/loop-config.md` | Operator-tunable loop settings (created with `loop.sh`) |
| `.claude/sessions/decisions-log-<task-id>.md` | Per-run decision history written by the agent; shared by loop mode and goal-supervised mode (operator audit record; committed to repo) |
| `.claude/sessions/loop-final-<task-id>.md` | Per-run final summary written by the wrapper on terminal exit; shared by loop mode and goal-supervised mode; gains a `halt_reason` field under goal-supervised mode to distinguish goal-condition-suspect halts (committed to repo) |
| `.claude/goal-loop.sh` | Goal-supervised wrapper script (created only when goal-supervised mode opted into at Phase 9.6) |
| `.claude/goal-config.md` | Operator-tunable goal-supervised settings — `max_iterations`, `evaluator_model`, `evaluator_disagreement_threshold`, `evaluator_feedback_history_depth`, judge-API retry posture, `usage_limit_wait` / `usage_limit_max_wait_seconds` / `usage_limit_wait_jitter_seconds` (reset-aware usage-limit handling; same keys as `loop-config.md`), completion-criteria checklist, classifier thresholds, audio-cue overrides (created with `goal-loop.sh`) |
| `.claude/sessions/.iteration-summary-<task-id>-<iter-n>.md` | Structured per-iteration summary written by the agent; the judge's primary judging surface (gitignored; aggregate signal lives in `loop-final-<task-id>.md`) |
| `.claude/sessions/.evaluator-feedback-<task-id>.md` | Per-iteration judge verdicts appended by the wrapper; the next iteration's priming context includes the most recent two entries (gitignored; full file preserved for post-hoc review) |
| `.claude/learnings/mode-selection.md` | Per-task mode-choice calibration ledger (created at Phase 9.6, populated by the operator post-task; drives recommendation-rule tuning at the ~20-task milestone) |
| `.claude/auto.sh` | Queue runner script (created only when queue mode opted into at Phase 9.7) |
| `.claude/auto-config.md` | Operator-tunable queue settings — `max_concurrent_tasks`, pause-on flags, `consecutive_halt_threshold`, default budgets, `summary_synthesis_enabled`, `summary_synthesis_model` (created with `auto.sh`) |
| `.claude/queue/backlog.md` | Persistent operator-authored task queue; populated by `spec-decompose` per task, updated by the runner during dispatch (committed to repo) |
| `.claude/queue/run-summary-<timestamp>.md` | Morning-after queue-run summary; one per queue run; the operator's primary review surface (committed to repo) |
| `.claude/queue/.run-active` | Runtime sentinel written by the runner; cleared at terminal exit (gitignored) |
| `.claude/queue/.halt` / `.claude/queue/.resume` | Operator-written sentinels to graceful-halt or resume the runner (gitignored) |

| Workflow signal | What to do |
|---|---|
| Drift alert tier 1 (gentle chime) | Note it; finish current thought |
| Drift alert tier 2 (insistent chime) | Plan to checkpoint within 10 min |
| Drift alert tier 3 (firm chime, enforced) | Agent auto-writes checkpoint; tool calls hard-blocked. Run `/clear` then `/resume` (or, if inside loop mode, the wrapper handles the reset automatically) |
| Task-done chime (ascending tones) | Subagent finished — review output when convenient |
| Decision-required alarm (attention-grabbing) | Agent is blocked — respond now; check `.claude/sessions/.decision-pending-*` for details |
| Spec turns out to be wrong | Bump spec version (Phase 7.5 protocol) |
| Hook blocks me | Read the message; either fix the underlying issue or escalate per `CLAUDE.md` |
| Want to add a dependency | Confirm in-session; bootstrap updates `deps.md` |
| Need quiet for focus work | `/quiet 2h` mutes audio for 2 hours; visual notifications continue |
| Loop completed cleanly | Review `loop-final-<task-id>.md`; check `decisions-log-<task-id>.md` (focus on expensive-to-undo entries); merge if satisfied |
| Loop hit max-iterations | Loop halted; review iteration history in `loop-final-<task-id>.md`; decide: rescope, manual completion, or restart with adjusted scope |
| Loop halted on urgent escalation | Operator action required; check `.claude/sessions/.decision-pending-*` for the cause and `.loop-halt-<task-id>` for the trigger task |
| Decision log has entries | Review post-loop; override any unwanted choices and re-run the loop with the override flag set if needed |
| Goal-supervised run completed cleanly | Review `loop-final-<task-id>.md`, `decisions-log-<task-id>.md`, `.iteration-summary-<task-id>-*.md`, and `.evaluator-feedback-<task-id>.md`. Look especially at any `evaluator-disagreement` entries in the decision log — even on a clean completion, disagreements en route can flag spec ambiguity worth fixing |
| Goal-supervised run halted on `goal-condition-suspect` | The judge and the deterministic gates have stably disagreed for 3+ consecutive iterations (or 3 consecutive iteration-summary format failures). **Do not retry harder.** Review the goal condition wording, the disagreement entries in `decisions-log-<task-id>.md`, and the judge reasons in `.evaluator-feedback-<task-id>.md`. Likely fix: rewrite the goal condition, fix the spec, or re-classify the task as operator-only |
| Goal-supervised run had persistent evaluator-disagreement but completed | Common shape on tasks at the edge of the sixth criterion. Record an entry in `learnings/mode-selection.md` noting the friction; over time these inform recommendation-rule tuning |
| Want to investigate a goal-supervised disagreement deliberately | Re-run with `--investigate-disagreement`; one iteration runs on Opus with priming about the disagreement. Opt-in only — never automatic |
| Queue run completed cleanly | Read the morning-after summary (`.claude/queue/run-summary-<timestamp>.md`); review per-task artifacts the summary surfaces; do a cumulative-diff review across all tasks (environmental drift can produce a worse codebase state over many tasks even when each task succeeded) |
| Queue paused with no dispatchable work remaining | Runner is waiting because all "Ready to run" tasks are transitively blocked on operator-only predecessors. Handle the operator-only tasks interactively, defer them, or remove them from `backlog.md`. To resume: drop a `.claude/queue/.resume` sentinel (`touch .claude/queue/.resume`) or re-invoke `auto.sh`. The runner deletes `.resume` after observing and re-scans on next event |
| Queue halted on three-consecutive-halts | Diagnostic signal that something's wrong with the queue itself — wrong classifications, broken dependencies, or environmental drift. **Do not just re-run.** Read the run-summary's "Halted — needs operator attention" section, identify the pattern, and fix the underlying cause before resuming |
| Queue halted on urgent escalation | The queue stops at the first urgent escalation by design — non-configurable. Read `.claude/sessions/.decision-pending-*` and `loop-final-<task-id>.md` for the trigger task. Handle the escalation (typically a steering-doc edit, spec update, or manual intervention). Remaining tasks stay in "Ready to run" for the next queue invocation |
| Task or queue halted on `usage-limit-reset-abandoned` | Not a failure — the account hit a usage cap (5-hour or weekly) that resets at a known time, and the wait exceeded `usage_limit_max_wait_seconds` (default 6h). Read the `Ended because` line for the limiting bucket and reset time. Re-invoke after the reset, raise `usage_limit_max_wait_seconds` to let the wrapper sleep through it unattended, or switch to a higher plan tier / API-key billing if caps bind often. Nothing is lost: per-task worktrees retain whatever was committed before the wrapper stopped |
| Queue hit a budget (time/tokens/tasks) | Runner finishes in-flight tasks and exits. Review the morning-after summary, decide whether the budget was right, and adjust before re-invoking |
| Want to halt the queue gracefully without sending a signal | Drop a `.claude/queue/.halt` sentinel; the runner halts at the next dispatch decision point |
| Tempted to skip the trust ramp | Don't. The recommended sequence in Phase 9.7 is non-optional — operators who skip it ship problems supervised use would have caught |

| Task type | Recommended model |
|---|---|
| Bootstrap wizard | Opus 4.8 |
| `/spec-new`, `/spec-review`, `/spec-decompose`, `/plan-review` | Opus 4.8 |
| `code-review` subagent | Opus 4.8 (effort: high) |
| Adversarial review / threat-modeling *(PRD-process, not a generated subagent)* | Fable 5 → Opus 4.8 fallback (effort: high/max) |
| `implementer`, `test-author` subagents | Sonnet 5 |
| `/spec-validate`, `/pr-author`, `/checkpoint`, `/resume` | Sonnet 5 |
| Built-in `Explore`, `/ack-drift`, classification/routing | Haiku 4.5 |
| `integrator` subagent | Inherit (floor Sonnet 5; matches main session) |
| Goal-supervised judge (only if Phase 9.6 enabled) | Haiku 4.5 (configurable in `goal-config.md`) |
| Queue-mode summary synthesis (only if Phase 9.7 enabled and `summary_synthesis_enabled: true`) | Haiku 4.5 (configurable in `auto-config.md`; can be disabled) |
| Don't want to configure each? | `claude --model opusplan` (Opus 4.8 plan / Sonnet 5 exec) |

*If on Pro tier with limited Opus access:* fall back to Sonnet 5 (xhigh effort) for the Opus rows. See "Plan and availability check" in the Model Assignment Strategy section.

### Four eligibility shapes (only if Phase 9.6 enabled)

`spec-decompose` classifies each task against six criteria — the five loop-eligibility criteria from Phase 9.5 (unambiguous acceptance, low novelty, bounded blast radius, tests authoritative, cheap rollback) plus the sixth criterion from Phase 9.6 (goal expressible in one sentence a small model can verify from a diff and a test summary). The combinations produce four shapes:

| Shape | Five criteria | Sixth criterion | Default routing |
|---|---|---|---|
| **Eligible for both** | all pass | passes | Recommendation rule decides (see below); operator confirms |
| **Loop-mode-eligible only** | all pass | fails | Loop mode |
| **Goal-supervised-eligible only** | one or more fail | passes | Goal-supervised mode — the new middle tier; broader blast radius or harder rollback than loop mode accepts, but with a one-sentence verifiable goal |
| **Operator-only** | one or more fail | fails | Standard interactive flow |

**Recommendation rule for eligible-for-both tasks** (flip-properties — any one promotes the default from loop mode to goal-supervised):

- (a) The acceptance criteria have a semantic component that tests don't fully capture (e.g., "human-readable error message," "matches the documented contract in spirit," "preserves caller-visible behavior").
- (b) The diff is expected to be small but spread across multiple files (≥3) — a known failure mode where the reviewer subagent's per-file pass misses cross-file semantic drift.
- (c) The task touches a public-facing surface (user-visible strings, API response shapes, error messages, CLI help text — a judge approximates "a human glance at the final output" better than deterministic gates do).
- (d) The task is in a domain that `learnings/mode-selection.md` has flagged as drift-prone for this codebase.

If any of (a)–(d) match, the primary recommendation is goal-supervised; otherwise loop mode. The operator confirms or overrides per task — recommendations, not decisions. The flip-properties are a starting prior, not a tested heuristic; expect to refine them in `learnings/mode-selection.md` over the first ~20 tasks.

### Queue mode reference (only if Phase 9.7 enabled)

For queue mode's runtime specifics, `Bootstrap-Protocol-v2-5-0.md` is the canonical source. To avoid drift between the two files, the Companion does not repeat the queue file format, the runner's termination-conditions table, the trust-ramp sequence, or the morning-after summary template — they live in the protocol document and are read from there.

- **Queue file format** (`.claude/queue/backlog.md` skeleton, sections, queue-policy block, non-configurable invariants): Bootstrap-Protocol-v2-5-0.md Phase 9.7 → "Architecture: the queue file."
- **Runner termination conditions** (terminal-success, deferred-only-remaining, urgent-escalation, three-consecutive-halts, budget exhaustion, pause-not-terminal, signal/halt sentinel, infrastructure failure): Bootstrap-Protocol-v2-5-0.md Phase 9.7 → "Termination conditions."
- **Trust-ramp sequence** (week-by-week, 30-minute supervised → full overnight): Bootstrap-Protocol-v2-5-0.md Phase 9.7 → "Trust ramp — recommended adoption sequence." Repeated at Phase 10 handoff.
- **Morning-after summary template** (run-summary file structure, sections, optional small-model synthesis): Bootstrap-Protocol-v2-5-0.md Phase 9.7 → "The morning-after summary."

The Companion's job at this layer is the calibration / glossary / mental-model framing — *what queue mode is*, *why it is shaped this way*, *what it does not cover* — not a second copy of the runtime spec. If you are reaching for queue-mode runtime details and find yourself looking in the Companion, look at Bootstrap-Protocol-v2-5-0.md Phase 9.7 instead.

---

## Writing style & operator-output conventions (v2.0.1)

Two conventions, one rule each. They govern operator-facing prose only.

**Plain writing (interview and handoff prose).** Write so it lands on the first read: lead with the answer, short sentences, one idea per sentence, concrete nouns and exact claims. Plain is not vague — simplify the language, never the content. Open with an analogy if it helps, then restate it concretely; never leave the analogy standing as the spec. **Carve-out:** enum values, mode names, config identifiers, gating logic, and "use verbatim" strings are contract, not prose — restyling a verbatim string is a version-bumped protocol change, never a copyedit. **Context rule:** in the interactive interview, direct disagreement with the operator is good; in unattended artifacts there is no one to disagree with — there, disagreement means halting loudly with a reason. **Enforcement:** an advisory linter only (banned-decoration wordlist, >30-word sentence flag, acronym-defined-on-first-use), warn-only, never blocking — a false-positive-prone style gate would train operators to bypass gates, which the real security gates cannot afford.

**Dual-surface operator output (runner summaries, escalations, halts).** Every operator-facing outcome pairs a plain sentence (exact cause + concrete next action) with its stable machine key as secondary metadata — the morning-after summary's `Ended because` line is the pattern. Wording revisions may change the sentence, never the code or field names. **Locked field schemas** (distinct on purpose; never merge or rename): `.claude/specs/<slug>/decisions.md` — timestamp, context, options considered, rationale; `.claude/sessions/decisions-log-<task-id>.md` — question, options, choice, justification, reversibility flag. Clearer wording is ergonomics and auditability, not a security property — it strengthens no gate.

---

## Glossary

- **PRD** — Product Requirements Document. Upstream of steering. Answers what we're building and why.
- **Steering doc** — Project-wide invariants. Read on every task. Lives in `.claude/steering/`.
- **`design.md`** — optional steering doc (`.claude/steering/design.md`, produced when `design_steering_enabled`) carrying UI/UX invariants and HONEST-USE-ONLY persuasion/pricing rules for user-facing work. Read on every user-facing task; self-contained for agents. Its honest-use rules are highest **within design scope**; cross-domain ties resolve in `principles.md`, which remains the sole ranking surface (DELTA-01).
- **Spec** — Per-feature requirements + design. Lives in `.claude/specs/<slug>/`. Versioned.
- **Task** — Atomic unit of work derived from a spec via decomposition. Sized to fit in roughly half a fresh subagent's context window. Lives in `.claude/specs/<slug>/tasks/`.
- **Hook** — Deterministic gate that runs outside the AI's control. Lives in `.claude/hooks/`.
- **Skill** — Advisory instructions the AI loads when relevant. Lives in `.claude/skills/`.
- **EARS notation** — Easy Approach to Requirements Syntax (Mavin et al., IEEE RE'09). A constrained-natural-language pattern set for acceptance criteria. Five patterns: Ubiquitous, Event-driven, State-driven, Optional, Unwanted behavior. The protocol recommends (not mandates) EARS for acceptance criteria authored via `spec-new`. Falls back to tables for scenarios with more than ~3 preconditions.
- **Auto memory** — Claude Code's built-in cross-session memory (v2.1.59+). Stored per-project at `~/.claude/projects/<project>/memory/`. On by default. Distinct from CLAUDE.md (operator-written) and from memory MCPs (third-party). For most solo workflows, replaces the need for a memory MCP.
- **Model Assignment Strategy** — Per-skill and per-subagent assignment based on *consequence-of-error × judgment-required*. Opus 4.8 for judgment-heavy thinking (spec, review, architecture); Sonnet 5 for execution against a clear spec; Haiku 4.5 for read-only, classification, or trivial work; Fable 5 (with Opus 4.8 fallback) reserved for adversarial/threat-model passes only. See the Model Assignment Strategy section.
- **`opusplan` mode** — Claude Code shortcut (`claude --model opusplan`) that runs Opus 4.8 during planning mode and Sonnet 5 during execution. Roughly 80% of the benefit of full per-skill assignment with zero configuration.
- **Subagent** — Fresh AI context spawned for a specific task; preserves quality by avoiding context bloat. Optionally with `isolation: worktree` for filesystem isolation.
- **Worktree** — Git feature giving each subagent its own working directory on a separate branch. Prevents file conflicts during parallel work.
- **Wrapper** — A bash script that orchestrates one autonomous-mode run by invoking `claude -p` (per-task wrappers) or by dispatching other wrappers (the coordination-layer wrapper) and inspecting sentinels after each exit to decide what to do next. The per-task wrappers are `.claude/loop.sh` (loop mode) and `.claude/goal-loop.sh` (goal-supervised mode); each invokes `claude -p` once per iteration in fresh-session-per-iteration fashion. The coordination-layer wrapper is `.claude/auto.sh` (queue mode); it does not invoke `claude -p` directly — it dispatches the per-task wrappers as subprocesses, one per task, and observes their terminal states. All three contain no agent context of their own — they are bash orchestrators, not Claude sessions — which is what keeps the trust-ramp work bounded to small auditable scripts.
- **Sentinel** — A small marker file the wrapper or the agent writes to communicate state across the wrapper ↔ session boundary. Active markers (`.loop-active-<task-id>`, `.goal-active-<task-id>`, `.run-active`) say "a run is in progress." Completion markers (`.loop-complete-<task-id>`) say "the agent self-verified completion." Halt markers (`.loop-halt-<task-id>`) say "urgent escalation fired, stop the run." Operator-written sentinels (`.halt`, `.resume`) request graceful runner state changes. Most sentinels are gitignored; operator-facing audit records use regular filenames instead.
- **Checkpoint** — Structured synopsis of session state, written to `.claude/sessions/` before `/clear`. Enables clean session boundary.
- **Drift** — Quality degradation in a long session. Two kinds: **context bloat drift** (window full of noise) and **semantic drift** (model wandering off-spec). The drift detector flags both.
- **Tier 3** — The firmest level of the drift detector's three-tier escalation, an *enforcing* hook (the other two are advisory). Tier 1 is a gentle chime (finish current thought); tier 2 is an insistent chime (plan to checkpoint within ~10 min); tier 3 is a firm chime *plus* enforcement — the agent is hard-blocked from further tool calls until a checkpoint is written and `/clear` is run. Outside autonomous modes the operator runs `/clear`+`/resume` to restart; inside loop mode or goal-supervised mode the wrapper handles the reset automatically (see *Self-healing context reset*). The detector's thresholds and audio cues are configurable in `.claude/hooks/audio-alerts.config`; tier 3 alone cannot be acknowledged-and-continued.
- **Audio alert system** — Three-category alarm system covering drift detection (degrading frequency; tier 3 enforced), task completion (`SubagentStop` event), and decision required (urgent escalation criteria). Each category has a distinct sound; shared infrastructure (notification dispatch, sound files, quiet mode) lives in section 6.E. Tier 3 drift and decision-required both override quiet mode because both represent genuine blocks on the agent.
- **Decision-required alarm** — The most urgent of the three audio alerts. Fires when the AI hits an urgent escalation criterion (do-not-touch file, secret encountered, hook block, dependency not approved, spec wrong). Persistent notification (no auto-dismiss). Overrides quiet mode.
- **Quiet mode** — Suppresses audio alerts while keeping visual notifications. Activated via `/quiet on`, `/quiet 2h`, or similar. Decision-required alarms override quiet mode after first attempt.
- **Context bloat** — When the conversation window fills with file reads, tool outputs, and history that no longer serve the current task. Resolved by checkpoint + `/clear`, not by memory tools.
- **Synthetic archetype profile** — JSON object describing a project that doesn't fit a preset archetype. Built in Phase 0 from dimension answers; used by later phases to route questions.
- **TDD** — Test-Driven Development. Writing failing tests before source.
- **SDD** — Spec-Driven Development. The methodology this protocol bootstraps.
- **CI/CD** — Continuous Integration / Continuous Deployment. Automated build/test/deploy pipeline.
- **Post-bootstrap milestones** — Defined lifecycle thresholds (e.g., first regulated user, ~30 commits, first additional contributor) that trigger production of additional `.claude/` artifacts not produced at bootstrap. See the dedicated section.
- **MCP** — Model Context Protocol. Standard for connecting AI assistants to external tools and data sources.
- **Loop mode** — Optional autonomous-execution mode for individual tasks (added in v1.7). Opt-in per task at decomposition time. Preserves all existing enforcement guarantees (tier 3, urgent escalations, reviewer subagent, spec gate, integrator). Bounded by three independent termination conditions: completion criteria met, max-iterations hit, or unrecoverable escalation. The loop's completion check requires both the deterministic four-criterion gate and the agent's self-verification sentinel; in loop mode the wrapper treats the sentinel as its primary check and trusts the agent's self-attestation that the four gates passed (goal-supervised mode strengthens this by re-checking the gate independently — see that entry). The sentinel is never inferred. Configured via Phase 9.5; runs through `.claude/loop.sh`. Inspired by Geoffrey Huntley's Ralph Loop pattern and Anthropic's official `ralph-wiggum` plugin, but uses a fresh-session-per-iteration mechanism rather than a Stop-hook-in-session mechanism, which is what makes the self-healing tier-3 reset clean.
- **Loop-eligibility classifier** — Five-criterion test applied at `spec-decompose` time when loop mode is enabled: unambiguous acceptance criteria, low novelty, bounded blast radius, automated-test-verifiable, cheap rollback. Tasks scoring "yes" on all five are loop-mode candidates. The classifier produces *recommendations*; the operator confirms or vetoes per task.
- **Decision log** — Per-task record of non-urgent decisions made autonomously inside loop mode or goal-supervised mode. Lives at `.claude/sessions/decisions-log-<task-id>.md` (committed to repo); shared by both per-task autonomous modes (same filename convention, same operator-facing audit purpose). Each entry contains question, options, choice, justification, and reversibility flag (cheap-to-undo / expensive-to-undo / one-way). In goal-supervised mode, also accumulates `evaluator-disagreement` entries (see that term). Reviewed by operator post-run. **Distinct from `.claude/specs/<slug>/decisions.md`** (the per-spec within-feature decisions file written by the `decision-log` skill, which exists pre-v1.7 and is unchanged). The two artifacts complement each other; the per-run audit record is for autonomous choices made under the defensible-default criterion, while the per-spec file is for any non-obvious choice made during normal task execution.
- **Defensible default** — The decision criterion used by the implementer in loop mode and goal-supervised mode (both autonomous per-task modes). Not "best quality" or "most robust" (those framings produce over-engineering bias). Defined as: *minimizes blast radius if wrong; easiest to reverse if the operator disagrees post-hoc.* Biases the agent toward conservative, undo-friendly choices. Applied when a non-urgent decision arises during an autonomous run; the choice is recorded to the decision log with a reversibility flag so the operator can review and override.
- **Self-healing context reset** — Tier 3 drift behavior inside an autonomous mode (loop mode or goal-supervised mode). The agent writes the standard checkpoint and ends its turn; `claude -p` exits; the wrapper (`loop.sh` or `goal-loop.sh`) detects the tier-3 sentinel plus fresh checkpoint and starts a new session primed with the checkpoint. The new session has a new session ID, so the old `.drift-tier3-<old-session-id>` sentinel no longer matches and tool calls flow normally. Outside autonomous modes, tier 3 still requires operator-driven `/clear`+`/resume`. The drift-detector cooperation hook (generated only when at least one autonomous mode is opted into) recognizes both `.loop-active-*` and `.goal-active-*` markers; the transformation behavior is identical between the two modes.
- **Fresh-session-per-iteration** — The mechanism that makes autonomous-mode loops safe: each iteration is a separate `claude -p` invocation with its own session ID, primed with the current task brief plus the latest persistent state (diff, decision log, evaluator feedback, most recent checkpoint). Session-internal context does not accumulate across iterations — only files on disk and git history persist. This is what makes the self-healing tier-3 reset work cleanly (a new session ID invalidates the old sentinel) and what bounds context bloat within an autonomous run. Used by both `loop.sh` and `goal-loop.sh`. Distinct from in-session looping (the failure mode that earlier Ralph-style implementations had), in which the same session is asked to continue past tier-3 and accumulates bloat.
- **Goal-supervised mode** — Optional autonomous-execution mode added in v1.8, sibling to loop mode. Opt-in per task. Each iteration is fresh-session-per-iteration (preserving v1.7's context-hygiene win) and ends with the wrapper invoking a small-model judge with the goal condition, the current diff, the agent's structured iteration summary, and the test output. Three independent signals must all agree before terminal-success: the agent's self-verification sentinel, the deterministic four-criterion gate, and the judge's verdict. Goal-supervised mode adds **two** strengthenings over loop mode, not one: (1) the wrapper checks the deterministic four-criterion gate *independently* rather than trusting the agent's self-attestation that it passed (in loop mode the sentinel is the wrapper's primary check and the gate-pass is the agent's attestation), and (2) the judge verdict is required on top. Both still require the self-verification sentinel, which is never inferred. The completion-criteria mechanics are canonical in Bootstrap-Protocol-v2-5-0.md Phase 9.5 ("Completion criteria"); this entry summarizes, it does not restate them. Configured via Phase 9.6; runs through `.claude/goal-loop.sh`. Independent of loop mode — a project may enable either, both, or neither.
- **The sixth criterion** — The classifier criterion added in v1.8 that selects for goal-supervised eligibility: *Is the goal expressible in one sentence of natural language that a small model could verify from a diff and a test summary?* Combined with the five loop-eligibility criteria, produces four eligibility shapes (see "Eligibility shape" below).
- **Eligibility shape** — One of four classifications produced by `spec-decompose` when goal-supervised mode is enabled: *eligible for both* (all six criteria pass), *loop-mode-eligible only* (five pass, sixth fails), *goal-supervised-eligible only* (some of five fail, sixth passes — the new middle tier), or *operator-only* (some of five fail, sixth fails). The recommendation rule routes eligible-for-both tasks per four flip-properties (semantic acceptance component, multi-file diff, public-facing surface, known-drift domain).
- **The judge** — The small-model evaluator invoked once per iteration in goal-supervised mode. Haiku 4.5 by default (configurable in `goal-config.md`). Reads the agent's iteration summary, the goal condition, the diff, and the test output, and returns `{verdict: yes|no, reason: <one-to-three-sentences>}`. **Advisory, never authoritative** — the deterministic four-criterion gate remains the backstop. The judge sees artifacts, not transcripts, because each iteration is a fresh session.
- **Iteration summary** — The structured per-iteration artifact written by the agent at the end of each goal-supervised iteration, in a fixed format (goal condition / completion-criteria status / what changed this iteration / what still needs work / notes for the evaluator). Lives at `.claude/sessions/.iteration-summary-<task-id>-<iter-n>.md`. The judge's primary judging surface — freeform agent prose is intentionally not in the judge's view. Enforced by the iteration-summary enforcement hook; three consecutive format failures count as a `goal-condition-suspect`-class halt.
- **Evaluator feedback** — The accumulating per-iteration record of judge verdicts and reasons, appended by the wrapper to `.claude/sessions/.evaluator-feedback-<task-id>.md`. The next iteration's priming context includes the most recent two entries (configurable via `evaluator_feedback_history_depth` in `goal-config.md`); the full file is preserved for operator post-hoc review. Bounded depth preserves the context-hygiene win of fresh-session-per-iteration.
- **Evaluator-disagreement** — A decision-log entry type new in v1.8, written when the deterministic gates and the judge stably disagree (three sub-types: judge says no despite gates passing, judge says yes despite gates failing, agent didn't self-verify but everything else looks complete). Each entry records iteration, disagreement type, judge reason, and agent summary excerpt. Operator-facing audit record reviewed on completion or halt.
- **`goal-condition-suspect` halt** — The new fourth terminal condition for goal-supervised loops, triggered by persistent evaluator-disagreement (3+ consecutive iterations of the same disagreement type, configurable via `evaluator_disagreement_threshold`) or three consecutive iteration-summary format failures. **Not a failure — a diagnostic signal.** Either the goal condition was poorly worded, or the deterministic gates and the judge are stably disagreeing on this task. Both need human attention, not bigger models or more iterations. Recorded in `loop-final-<task-id>.md` via the `halt_reason` field.
- **`--investigate-disagreement` flag** — The single defensible model-escalation pattern in goal-supervised mode. Opt-in only, operator-initiated only — never automatic. When set on a halted run's re-invocation, the next iteration runs with Opus 4.8 (overriding the project's standard model assignment) for that iteration only, with explicit priming about the disagreement to investigate.
- **`learnings/mode-selection.md`** — The calibration ledger for the recommendation rule, initialized empty at Phase 9.6. After each completed autonomous-mode task, the operator records a single per-task assessment (recommendation / chosen / felt right? / notes). After ~20 entries, accumulated evidence drives recommendation-rule tuning — see Post-bootstrap milestones.
- **Autonomous queue mode** — Optional coordination layer added in v1.9, layered above the per-task autonomous mechanisms. Dispatches pre-classified tasks from a backlog file in sequence to the appropriate per-task wrapper (`loop.sh` for loop-mode tasks, `goal-loop.sh` for goal-supervised tasks), waits for terminal exit, continues or halts based on queue-level termination conditions. **Requires at least one per-task mechanism to be enabled** — the runner has nothing to dispatch otherwise. Configured via Phase 9.7; runs through `.claude/auto.sh`. Independent of the per-task mechanisms: a project may enable any combination.
- **The runner** — The autonomous-queue orchestrator at `.claude/auto.sh`. Bash plus optional small-model summary-synthesis call at queue-termination time. **Contains no agent context of its own** — does not run a Claude session, does not invoke the agent directly, does not modify task classifications. Invokes the existing per-task wrappers as subprocesses and observes their terminal states. The runner being "dumb" is the property that makes its trust ramp manageable — very little new code that can go wrong.
- **The queue** — The persistent task backlog at `.claude/queue/backlog.md`. Operator-authored (every entry results from `spec-decompose` plus operator confirmation), committed to the repo, editable between runs. Sections: queue policy, ready to run, operator-only, in flight, completed this run, halted this run, deferred. Tasks come with priority, mode classification, and optional `blocked_by` dependency edges.
- **Ready-to-run** — The queue state where a task is dispatchable. Requires: appearing in the "Ready to run" section, all `blocked_by` predecessors terminated successfully (a reference to a task in flight, in "Operator-only," or in "Deferred" leaves the task not-ready), mode enabled at the project level, a concurrency slot available. The runner walks candidates in priority order (high before normal before low) and within a priority in queue-file order, but **priority is a preference, not a reservation** — if the highest-priority ready task is blocked on a predecessor, the runner dispatches the next-priority independently-ready task rather than stalling. The "skip-and-continue" rule: not-yet-ready candidates are skipped on each scan; the runner pauses only when no candidate is dispatchable and at least one task is awaiting operator action.
- **The morning-after summary** — The single most important operator-facing artifact of a queue run, written to `.claude/queue/run-summary-<timestamp>.md` and populated incrementally. Contains a one-line headline, aggregate run statistics, completed-cleanly tasks, halted-needs-attention tasks (with likely-cause synthesis), did-not-run tasks, decisions requiring operator review (aggregated from per-task decision logs), and recommended morning actions. The synthesis sections are optionally produced by a small-model call at queue termination (Haiku by default). Committed to the repo as the run's audit record.
- **Three-consecutive-halts termination** — The queue-level diagnostic-signal terminal condition: three consecutive task-level halts of any non-urgent kind within the same run terminates the queue. Catches higher-order problems (wrong classifications, broken dependencies, environmental drift) before they propagate. Threshold configurable via `consecutive_halt_threshold` in `auto-config.md` (default 3). Like `goal-condition-suspect`, it is the protocol working as designed, not a failure of the runner.
- **Queue budgets** — Operator-set ceilings on a queue run, applied at task boundaries (not mid-task). Three independent budgets: time (wall-clock), tokens (cumulative main-model + judge), tasks (count attempted). Default: all unset. When any budget is exhausted, the runner finishes in-flight tasks (does not start new ones), finalizes the summary with budget-exhaustion noted, and exits terminal. Token tracking is approximate — the runner relies on per-task wrappers' reporting; the budget is a soft ceiling, not a hard one.
- **Trust ramp** — The protocol's posture toward each autonomous mode: calibrate against real evidence before granting more autonomy. Three independent ramps: 5–10 supervised tasks before relying on loop mode unattended; 10–20 supervised tasks before relying on goal-supervised mode and trusting its judge for this codebase; ~4 weeks of supervised per-task use before relying on queue mode for full overnight or multi-day runs. The ramps are independent and additive — calibrate each layer before adding the next. Explicitly not skippable; the wizard surfaces the expectations at Phase 0 opt-in and at Phase 10 handoff.

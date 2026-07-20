# Changelog — Bootstrap Protocol implementation

## 2.2.0 → 2.4.0 (v2.4.0 code fold — GR2-EX / TEL-EX; bring code up to the frozen v2.4.0 docs)

Single code fold; **no intermediate 2.3.0 code release**. The v2.3.0 GR2
doc fold and the v2.4.0 TEL-01 doc fold were both doc-first and landed no
code, so the real code delta is `2.2.0 → 2.4.0 = GR2-01 + GR2-02 +
GR2-03a + TEL-01`. Freeze exception recorded in the README review history
(GR2-EX / TEL-EX, W-1 precedent class: a mandated-artifact omission that
defeats a documented protocol invariant). Landed as five sequenced
commits so each golden re-baseline stays legible.

### Step 0 — Version identity (`2.2.0 → 2.4.0`)

- `PROTOCOL_VERSION` → `"2.4.0"` in `lib/installer.py` and
  `lib/templates.py`. `RETROFIT_PROTOCOL_VERSION` stays `"1.6.2"`;
  `RUNTIME_FLOOR` stays `"2.1.210"` (seam-owned, untouched per §8).
- `plugin/plugin.json` version + description bumped to v2.4.0 (release
  identity, precedent from the 2.2.0 bump).
- Version assertions updated to 2.4.0: `AC-A0-1..3` (`test_installer.py`),
  the `AC-9-5` mirrors (`test_ic_gate.py`), `AC-1-1/1-2` + corrupt-state
  (`test_gate_substrate.py`), and retrofit `8.3` (`test_retrofit.py`).
  New `test_ic_gate.py` tripwire asserts this changelog carries the
  `2.2.0 → 2.4.0` entry.

**FREEZE-EXCEPTION (golden re-baseline, step 0).** Per AC-A0-3 the
version rides emitted `_generatedBy` strings (`settings.json`, the
manifest), so **both golden fixtures' digests move at this step with
action counts unchanged**. Re-baselined `EXPECTED_DIGESTS` in
`tests/test_greenfield_golden.py`; `EXPECTED_ACTION_COUNTS` unchanged
(`default: 55`, `full_autonomous: 67`). Isolated into its own commit so
the stamp's byte movement does not entangle the four content deltas.

### Step 1 — GR2-03a assumption ledger (unconditional artifact)

- New `_assumption_ledger(cfg)` in `lib/templates.py` (registered as
  `"assumption_ledger"`), and an **unconditional** `build_plan` add of
  `.claude/steering/assumption-ledger.md` after `tools.md`. Lands in
  `.claude/steering/` (never gitignored) → committed by construction; **no
  gitignore edit**.
- Body is a faithful workspace rendering of the frozen `## Assumption
  Ledger` section (`Bootstrap-Protocol-v2-4-0.md`, anchor
  `#assumption-ledger`). The three drift-threshold numbers are
  **interpolated from `cfg["hooks"]`** (`drift_tool_call_threshold` /
  `drift_session_duration_minutes` / `drift_file_read_threshold`), not
  hardcoded — the drift-detector hook body reads the same keys, so the
  ledger can never become a stale second authority when an operator
  customizes the detector. Pure function of cfg (no timestamp/env);
  determinism proven by the digest test.
- **File count +1 on every fixture** (default 55→56, full_autonomous
  67→68). `test_installer.py` gains snapshot-based GR2-03a assertions
  (emitted-once, +1 delta, committed, interpolation real vs decorative,
  determinism); `test_greenfield_golden.py` re-baselined (both fixtures
  +1, digests moved, freeze-exception comment added).
- **DEFERRED (recorded, not shipped) — the GR2-03a *surfacing* behavior.**
  The frozen spec has two halves: the emitted artifact (shipped here) and
  a wizard behavior that "surfaces due entries on any pinned-model or
  runtime-floor change as a fail-loud, non-blocking notice." This fold
  delivers the **artifact only**. The surfacing is deferred with these
  **locked constraints**: it MUST be fail-loud and **non-blocking** (never
  blocks the model/runtime change); it MUST read the ledger's
  `Re-validation trigger` column and surface exactly the rows whose trigger
  matches the event; it MUST hang off the same event the v2.0.0 model
  remap / any later regenerate-config flow already represents (no new
  trigger surface); it MUST NOT silently proceed. Rationale: the emission
  is a pure `build_plan` artifact with zero runtime surface, whereas the
  surfacing is wizard-runtime logic wanting its own fixture and review;
  bundling would widen this fold's blast radius. The emitted ledger words
  the surfacing as protocol-specified with a "re-check by hand until it
  lands" note (honest framing — the operator doc must not claim unshipped
  behavior as current fact); when the surfacing ships, that one paragraph
  updates under the same freeze exception as the surfacing change.

### Step 2 — GR2-01 progress artifact (prose only, no new file)

`progress.md` is created at *task start* (when a slug exists), not at
install, so GR2-01 lands **no static file** and the plan count is
unchanged. Three prose edits in `lib/templates.py`:

- **`_claude_md`** reading list: read the task's
  `.claude/specs/<slug>/progress.md` (`Status` + `Failed approaches`)
  **first** at task/iteration priming, before the task brief, so a resumed
  session does not re-attempt a known dead end.
- **`_agents` implementer body**: consult the task's `progress.md` **Failed
  approaches** during priming (loop and goal-supervised modes) and never
  re-attempt a do-not-retry dead end. **The reviewer body is untouched** —
  it is the deterministic gate; loop-awareness there would conflate gate
  and iteration.
- **`_specs_index` (`.claude/specs/INDEX.md`)** — the single emitted home
  for the canonical `progress.md` reference template (Appendix B, with its
  corrected link targets `decisions.md` / `learnings/` /
  `sessions/<timestamp>-checkpoint.md`). Chosen over `/spec-new` because
  skills/commands are gated on `install_skills`/`install_commands` whereas
  INDEX.md is **unconditional**; the `_claude_md` note and implementer body
  LINK here rather than duplicating the template. Without this embedding
  GR2-01 would land the read-first prose with no emitted definition of the
  artifact's shape — the runtime creator would have to invent it, violating
  record-do-not-manufacture at runtime.
- **Commit-policy edit — no-op in code, recorded.** The PRD line-889
  committed-set enumeration lives only in the protocol document; **no
  emitted body carries a committed-set enumeration** (the only
  "operator-facing … committed" text in `lib/templates.py` is a Python
  source comment inside `_gitignore`, which is not emitted). `progress.md`
  is committed by construction because `.claude/specs/` is never
  gitignored. No new enumeration was invented to have something to edit.
- Count unchanged (56 / 68); golden re-baselined for the moved body bytes
  (freeze-exception). `test_installer.py` gains GR2-01 assertions
  (read-first note; implementer-has / reviewer-lacks the do-not-retry text;
  template section headers + three link targets present; template embedded
  in exactly one body).

### Step 3 — GR2-02 trajectory retention (comment-contract only, no new file)

Single edit surface: the shared `_per_task_wrapper(kind)` builder in
`lib/templates.py`, which covers **both** `loop.sh` and `goal-loop.sh`
(`_loop_sh` / `_goal_loop_sh` still only delegate). **`auto.sh` is not a
GR2-02 target** — it is the separate queue runner, not the
operator-completed loop; its `exit_reason` enum is untouched and adds no
value.

- **Fourth binding item** added to the wrapper's dispatch/deliverable
  comment block (beside the `--output-format stream-json --verbose`
  documentation): the operator-completed loop MUST retain each iteration's
  stream JSON at `.claude/logs/trajectory-<task-id>-<iter-n>.jsonl`
  (already gitignored under the existing `.claude/logs/` `logs/` rule — no
  gitignore change — and purged with the 7-day state policy). A skeleton
  self-check that finds retention disabled MUST **fail loud**.
- **`Trajectory` line** added to the documented `loop-final-<task-id>.md`
  structure block, linking the retained `.claude/logs/trajectory-*` files.
- **The "OTel span export is optional" sentence is PRD framing, not
  required emitted text** — the normative MUST-enumerate list (PRD line
  1098) is items (1)–(4); the OTel-optional sentence is document framing
  and is deliberately **not** added to the emitted comment (recorded so a
  later review does not read the omission as a miss).
- Count unchanged; **only the full_autonomous fixture's digest moves**
  (`loop.sh` + `goal-loop.sh`); the default fixture has no wrappers so its
  digest is untouched at this step. `test_installer.py` gains GR2-02
  assertions (retention path literal; fail-loud self-check; the loop-final
  `Trajectory:` line asserted *within* the structure block; loop.sh did not
  gain the judge-parity clause). `test_usage_limit_contract.py`'s
  auto.sh 13-value enum assertion stays green untouched.

### Step 4 — TEL-01 telemetry doc (opt-in, flag-gated)

- **`_telemetry(cfg)`** in `lib/templates.py` (registered `"telemetry"`)
  returns the **frozen `telemetry.md` body verbatim**. Exactly two values
  are stamped at emission, **scoped to the `OTEL_RESOURCE_ATTRIBUTES`
  line**: `<protocol_version>` ← `PROTOCOL_VERSION`, `<archetype>` ←
  `cfg["project"]["archetype"]`. The explanatory comment two lines above
  legitimately keeps the literal placeholder names, so the substitution is
  a scoped one-line build, not a global replace (AR-01 class). Fails loud
  (raises) if either value is missing — never emits a body whose OTEL line
  still carries a `<placeholder>`. Emitted body verified byte-identical to
  the uploaded `telemetry.md` (modulo the two substitutions).
- **`build_plan`** flag-gated add of `.claude/steering/telemetry.md` when
  `cfg.get("telemetry_export_enabled")`. Committed by construction
  (steering never gitignored); no gitignore edit. Read defensively.
- **`_write_state`** persists `telemetry_export_enabled` cfg-authoritatively
  (mirrors the mode-flag pattern); the flag-gated add and the state field
  key off the same cfg value, so emitted doc and state never disagree.
- **TAR-01 substitution-source deviation (recorded).** The frozen head
  note / Companion / body comment say the version is stamped "from
  `.bootstrap-state.json` (`bootstrap_protocol_version`)"; this
  implementation stamps the `PROTOCOL_VERSION` **constant**. Code-verified
  equivalent: both state writers stamp `bootstrap_protocol_version =
  PROTOCOL_VERSION` (`_write_state` and `_write_retrofit_state`), and
  `apply_plan` refreshes an unmodified `telemetry.md` on re-apply/upgrade
  (hand-edits preserved under L-1, the expected exception) — so the emitted
  constant equals the state-written value on every apply path. The
  regression lock is the TAR-01 pairing assertion (emitted OTEL version ==
  state `bootstrap_protocol_version` on the same apply).
- **Wizard wiring — `lib/interview.py`** [freeze exception]. TEL-01 is a
  skippable Phase 0 decision, wired as a **standalone top-level boolean**
  (NOT under `autonomous_modes` — telemetry is independent of every
  autonomous mode): added to `ANSWER_KEYS`, `default_answers` (default
  skip), `answers_to_config` (top-level key), `parse_interview_answers`
  `bool_keys`, the deterministic render (verbatim PRD "Enable observability
  export?" question), and the interactive front-end prompt. Back-compat: a
  pre-2.4.0 ANSWERS block lacking the line parses to `false` rather than
  erroring. Phase 0.5 preview needs no interview edit — the dry-run plan
  listing already includes `telemetry.md` once the flag-gated add lands.
- **Config flag — no `defaults.py` freeze exception.** `resolve_config`
  deep-copies `raw`, so the unknown top-level `telemetry_export_enabled`
  key passes through on both greenfield and retrofit; the retrofit branch
  rejects only the three nested `*_enabled` mode flags. Verified by the
  retrofit-passthrough assertion. (The retrofit **state schema** is not
  extended — out of scope, recorded; the flag-gated add still emits
  `telemetry.md` on a retrofit plan because the overlay wraps the full
  plan.)
- **Off by default = invisible.** Default plan count and determinism digest
  unchanged vs the post-GR2-03a baseline; **no golden move** (neither
  golden fixture opts in — the on-path is covered only in
  `test_installer.py`). On-path: +1 file, committed, substituted OTEL line.
  New assertions in `test_installer.py` (off/on/committed/OTEL-scoped/
  pairing/TAR-02-secrets/state-flag/retrofit-passthrough) and
  `test_interview.py` (default false, verbatim question, yes→true
  round-trip).

## 1.9.0 → 2.0.0 (Milestone A — doc-conformant; `gate_substrate` stays `"shell"`)

**Spec:** `.claude/specs/bootstrap-v2/requirements.md` rev-3 (owner-confirmed
2026-07-17). Milestone A implements R-0..R-6 (IC-1, IC-2, IC-3, IC-4, IC-7 +
the version identity and the model-remap assertion). The SDK substrate
(IC-5), native worktree routing (IC-6), and the IC gate ship as protocol
**2.1.0** in Milestone B [SR-04] — never under 2.0.0.

### R-0 — Version identity

- `PROTOCOL_VERSION` → `"2.0.0"` (`lib/installer.py`, `lib/templates.py`).
  `RETROFIT_PROTOCOL_VERSION` stays `"1.6.2"` (retrofit track untouched).
- Cross-references to the renamed protocol documents updated across `lib/`,
  `bin/`, `plugin/`, `tests/`, `README.md`
  (`BOOTSTRAP.md` → `Bootstrap-Protocol-v2-0-0.md`,
  `BOOTSTRAP-COMPANION.md` → `Bootstrap-Protocol-Companion-v2-0-0.md`).
  The v2.0.0 document's own convention is versioned self-naming (its
  line-149 naming rule), and its section anchors (6.D, Phases 9.5/9.7)
  survive, so emitted citations stay accurate.
- **Deliberately NOT updated:** the frozen RETROFIT-track documents
  (`RETROFIT.md`, `RETROFIT-COMPANION.md`, `RETROFIT-GAP-ANALYSIS.md`)
  still cite `BOOTSTRAP.md`; those references now dangle and are left for
  the retrofit track to reconcile (its docs are frozen at v1.6.2).
- `plugin/plugin.json` description bumped to v2.0.0;
  `tests/test_retrofit.py` literal version assertion 1.9.0 → 2.0.0.

**FREEZE-EXCEPTION (golden re-baseline #1).** Both fixtures re-baselined
for exactly two byte classes, verified by a HEAD-vs-worktree plan diff
with zero non-pairing residue:
1. `settings.json` `_generatedBy`: `protocol 1.9.0` → `protocol 2.0.0`;
2. protocol-document citations inside emitted hook/wrapper/config bodies:
   `BOOTSTRAP.md` → `Bootstrap-Protocol-v2-0-0.md`.
(default: 12 files; full_autonomous: 21 files.) Note: the spec's
task-decomposition guidance omitted R-0 from the re-baseline list, but
AC-A0-3's `_generatedBy` requirement necessarily perturbs the golden
surface — recorded here rather than silently absorbed.

### R-1 (IC-3) — `gate_substrate` state field

- `_write_state` emits `"gate_substrate": "shell"`.
- Non-destructive migration: a state file lacking the field (pre-2.0.0) is
  backed up once to `.bootstrap-state.json.pre-2.0.0` (Companion Migration
  notes) before being stamped; pre-existing keys are preserved.
- `"sdk-callable"` is unwritable in Milestone A (source-level tripwire in
  `tests/test_gate_substrate.py`; Milestone B replaces it with the
  `lib/ic_checks.py` gate). Outside the golden surface [SR-07].

### R-2 (IC-1) — `synthesize --validate-only`

- New flag on the `synthesize` subparser: parse interview → `resolve_config`
  invariants → violations to stderr → **no file written** → exit 0/2.
- The no-flag path is byte-identical to 1.9.0, proven against the HEAD code
  and locked as a mini-golden digest in `tests/test_validate_only.py`
  (AC-2-3 [SR-12]). This closes seam IG-01 (the §3.2 row upgrades when the
  seam re-pins to 2.0.0).

### R-3 (IC-4) — advisor default model

- `lib/llm_advisor.py` default: retired dated Sonnet-4 ID →
  **`claude-sonnet-5`** (verified 2026-07-17 against the live
  platform.claude.com models overview: it is the current Sonnet's Claude
  API ID *and* alias, a dateless pinned snapshot; no date suffix exists or
  may be appended). `BOOTSTRAP_INTERVIEW_LLM_MODEL` override retained.
- Proposes-never-decides and loud deterministic fallback proven unchanged
  (`tests/test_advisor_model.py`), including the never-send-commands
  invariant.

### R-4 (IC-2) — root-sentinel dual-honor (PERMANENT)

- `loop.sh`, `goal-loop.sh`, `auto.sh` additionally honor
  `<project>/.halt` (graceful stop at the next boundary) and NEW
  `<project>/.halt-hard` (immediate wrapper exit; the wrapper never signals
  an in-flight `claude -p` — killing processes is the caller's job).
  Legacy `.claude/queue/.halt`/`.resume` remain honored. Emitted comments
  bind the operator-completed iteration loops to re-check both sentinels
  at every iteration boundary. In `auto.sh` the checks run before the
  cleanup trap is installed so a halt refusal can never touch another
  run's `.run-active` sentinel.
- **Gitignore home [SR-17] — owner decision (a):** the installer manages a
  marker-delimited block (`# --- bootstrap-protocol managed: begin/end ---`)
  in the **project-root** `.gitignore` ignoring `/.halt` and `/.halt-hard`
  — a deliberate write surface outside `.claude/`, emitted as a visible
  plan action (kind `gitignore_root`, shown in `--dry-run` / Phase 0.5
  preview) only when at least one autonomous wrapper is emitted.
  Merge semantics: file absent → created (wholly-authored, digest-tracked
  normally); operator file → block appended once / refreshed in place,
  bytes outside the markers never touched, manifest entry
  `state: managed-block-appended` with a `block_digest` and **no**
  whole-file digest (operator edits outside the block never fire hand-edit
  warnings; uninstall keeps the co-owned file); torn block → loud SKIP.

**FREEZE-EXCEPTION (golden re-baseline #2, full_autonomous only).**
1. Three wrapper bodies gain the ROOT_HALT/ROOT_HALT_HARD guards;
2. One **added** action: project-root `.gitignore` (65 → 66 actions).
The default fixture is untouched by R-4 (its digest is the R-0 value).

### R-5 (IC-7) — machine-readable hook tiers

- Every manifest entry (and the `settings.json` entry) now carries
  `tier: security-critical | autonomy-critical | non-critical` per seam
  §7.2. Membership (contract-level; a change is a seam event):
  security-critical = secrets-gate, spec-gate-commit, dependency-gate,
  test-gate, eval-gate, tdd-gate, format-lint-gate, settings.json;
  autonomy-critical = drift-detector-loop-cooperation,
  iteration-summary-enforcement; all else non-critical;
  **spec-gate-entry deliberately non-critical** (warn-tier).
- Shell-era baseline, not a frozen ceiling: Milestone B adds
  `sdk_gates/gates.py` to the security set under the seam MAJOR [SR-02].
- No golden impact — the manifest is an `apply()`-time artifact [SR-07].

### R-6 — model remap: assertion, not assumed diff [SR-08]

- Asserted (not re-emitted): implementer `sonnet`, reviewer `opus`
  (+ `effort: high`), integrator explicitly `inherit`, goal judge
  `haiku`, no Fable subagent anywhere. Subagent frontmatter had **zero
  emission diff**, as the spec predicted — alias resolution is
  platform-side managed drift per the Companion guardrail.
- **AC-6-5 (docs verification, owner-reworded):** `effort:` IS a
  documented subagent-frontmatter key (code.claude.com/docs/en/sub-agents,
  verified 2026-07-17: overrides the session effort level; values
  low|medium|high|xhigh|max). The already-emitted `effort: high` on the
  reviewer (greenfield `templates.py` and the retrofit variant) is kept
  and now assertion-locked; greenfield/retrofit consistency asserted.

**FREEZE-EXCEPTION (golden re-baseline #3, full_autonomous only,
AC-6-4 only-if-diff case).** Exactly one file: `auto-config.md` gains the
Companion-mandated queue-summary-synthesis surface
(`summary_synthesis_enabled: true`, `summary_synthesis_model: haiku` —
Model Assignment Strategy table names `.claude/auto-config.md` as its
configuration surface; the 1.9.0 template omitted it).

### Finding 1 (PR #5 review) — goal-config keys vs Phase 9.6 (code moves)

Owner ruling: the discrepancy is code-vs-normative-spec — Phase 9.6
enumerates the goal-config surface with `evaluator_model` in the
`evaluator_*` family (Bootstrap-Protocol-v2-0-0.md:1336, :1382). Sweep of
the emitted `goal-config.md` against the full normative list:

| Phase 9.6 item | 1.9.0/2.0.0-A emission | Action |
|---|---|---|
| `max_iterations` (10) | ✓ present, correct | none |
| `evaluator_model` (haiku) | ✗ MISNAMED `judge_model` (value correct) | renamed; alias dual-read added |
| `evaluator_disagreement_threshold` (3) | ✗ MISSING (zero hits) | added |
| `evaluator_feedback_history_depth` (2) | ✗ MISSING (zero hits) | added |
| judge-API-failure retry posture (retry-once-then-halt) | ✗ missing; **doc names no config key** | documented in emitted comments; key naming needs an owner/spec decision. NOT to be conflated with `infra_retry_seconds`/`infra_max_consecutive_failures`: those configure the transient-`claude -p` infrastructure side (mirrored from `loop-config.md`, a mode with no judge at all); the judge-API posture is a distinct fixed retry-once-then-halt behavior ("same posture as" ≠ same keys, Phase 9.6) with genuinely no key in the emission |
| completion-criteria checklist | partial (`require_completion_sentinel: true`); no normative key names for the full checklist | kept; documented; naming needs spec decision |
| classifier thresholds | partial (`summary_failure_halt_threshold: 3` — the malformed-summary threshold); others unnamed in doc | kept; documented |
| audio-cue overrides | ✗ missing; no key names in doc | documented; naming needs spec decision |

Extras retained (not in the enumeration, protocol-consistent):
`infra_retry_seconds`, `infra_max_consecutive_failures` (transient
`claude -p` posture, mirrors loop-config), `investigate_disagreement`
(the Phase 9.6 `--investigate-disagreement` opt-in). `judge_model` was
the ONLY misnamed key found — no other aliases needed.

**Deprecated alias:** `goal-loop.sh` resolves `evaluator_model` from
`goal-config.md`; `judge_model` is honoured only when `evaluator_model`
is absent, with a loud stderr warning and a `hooks.log` entry. Exported
as `EVALUATOR_MODEL` for the operator-completed judge call.

**FREEZE-EXCEPTION (golden re-baseline #4, full_autonomous only).**
Exactly two files: `goal-config.md` (rename + two added keys +
documentation comments) and `goal-loop.sh` (alias resolution block).
`loop.sh` verified byte-identical. Tests:
`tests/test_goal_evaluator_keys.py` (13 checks).

**Migration note:** operators with a pre-2.0.0 `goal-config.md` keep a
working setup — the `judge_model` alias is honoured with a deprecation
warning until they rename the key; new emissions use `evaluator_model`.

### Finding 2 (PR #5 review) — `auto.sh` `.run-active` race safety (fixed)

Classified as a pre-existing conformance defect against Phase 9.7's
race-safety ("abort ... rather than overwriting",
Bootstrap-Protocol-v2-0-0.md:1455): the refuse-to-start path's EXIT trap
ran `rm -f "$RUN"` unguarded, deleting the *winner's* sentinel — which
would let a third invocation start a concurrent runner past the
combined-concurrency cap. Fixed in `auto.sh`:

1. **CLAIMED guard** exactly as the per-task wrappers: cleanup removes
   the sentinel only if this process claimed it.
2. **PID-liveness startup check** (Phase 9.7: "sentinel-presence alone is
   not a sufficient check"): `kill -0` plus a `/proc` fallback (so EPERM
   on another user's live process is not misread as dead). Unparseable
   sentinel → fail-safe refusal, untouched.
3. **Stale sentinel** (recorded PID dead): alert with the recorded start
   timestamp and ask before clearing; EOF/non-interactive defaults to No
   (side-effect-free refusal). Cleared-and-continue is logged.
4. **Re-verify before clear**: if the sentinel changed while waiting at
   the prompt, another runner claimed it — abort without touching it.
5. **O_CREAT|O_EXCL claim** (`set -C`), per the Phase 9.7 idiom the
   per-task wrappers already used; a failed claim aborts non-zero.

**FREEZE-EXCEPTION (golden re-baseline #5, full_autonomous only).**
Exactly one file: `auto.sh`. Tests: `tests/test_auto_run_sentinel.py`
(16 checks — live-PID refusal intact-sentinel, stale-cleared path,
race-loser intact-sentinel, normal-run self-cleanup, plus fail-safe
branches).

**Migration note:** `auto.sh` refusal is now **side-effect-free** — a
refusing invocation never deletes another run's `.run-active`.
Previously any existing sentinel caused refusal; now a live-PID sentinel
refuses, a stale one offers an operator-confirmed clear (non-interactive
invocations still refuse), so unattended behavior is unchanged except
that refusals no longer corrupt state.

### Migration note (operators)

Operators who never opt into the SDK substrate see **no behavioral change**
beyond: (1) the new `gate_substrate: "shell"` field (plus a one-time
`.bootstrap-state.json.pre-2.0.0` backup when upgrading a 1.x state file);
(2) the three autonomous wrappers additionally honoring the root sentinels
(inert unless you create `/.halt` or `/.halt-hard`); (3) for
autonomous-mode installs only, the managed root-`.gitignore` block keeping
those sentinels uncommittable. The shell gate suite is unchanged and
remains fully operative; fail-loud-on-empty-commands holds.

### PR5-04 hardening (adversarial review of PR #5)

Two hardening items on the Finding-2 startup sequence, verified against
the review's assertions (trap ordering was confirmed already correct —
`CLAIMED=0` precedes `trap cleanup EXIT`):

1. **Portable liveness probe:** `kill -0` + `/proc` fallback replaced by
   `ps -p` — immune to the EPERM misclassification (a live process under
   another user) and free of the Linux-only `/proc` dependence; a
   cannot-determine result still lands on refuse.
2. **tty-guarded prompt:** the stale-clear question is asked only when
   stdin is a terminal; a non-tty invocation auto-answers No *before any
   stdin read*, so an inherited open-but-silent pipe can never hang the
   runner (the F-2 hang class). `BOOTSTRAP_TEST_FORCE_PROMPT=1` is a
   documented TEST-ONLY override that forces the prompt path on a
   non-tty — it can only enable *asking* (the answer is still read from
   stdin, default No), never clearing.

**FREEZE-EXCEPTION (golden re-baseline no. 6, full_autonomous only).**
Exactly one file: `auto.sh`. Tests: `tests/test_auto_run_sentinel.py`
grows to 19 checks (adds the ps-p/tty-guard statics and the
non-tty-'y'-without-override case).

Also in this change: `plugin/plugin.json` bumps its own `version` field
`1.0.0` → `2.0.0` (the plugin is a distribution surface; its description
already declared protocol v2.0.0 — reviewer item PR5-05).

### Adversarial code review of the branch — fixes (four classes)

**Class 1 — `auto.sh` startup race safety & portability** (review findings
1, 4, 5, 6; all empirically reproduced by the verifiers before fixing):

1. **Dual-'y' race closed with a startup lock.** The whole
   check → operator-confirmed clear → O_CREAT|O_EXCL claim sequence now
   runs under `flock` on `queue/.run-active.lock`; a second invocation
   refuses instantly instead of racing the clear (previously two
   interactive operators could both pass re-verify and the loser's `rm`
   deleted the winner's fresh sentinel — reproduced). flock was already a
   hard requirement of the per-task wrappers; `auto.sh` now shares that
   posture (refuses if flock is unavailable). The re-verify stays as
   defense-in-depth against non-`auto.sh` sentinel writers. The lock file
   joins both gitignore fragments.
2. **Errexit-proof sentinel parsing.** `run_pid`/`run_start` helpers
   swallow sed failures (`|| true` inside the pipeline), so an unreadable
   sentinel or sentinel-as-directory reaches the loud fail-safe branches
   instead of dying silently via `set -euo pipefail` (previously rc 2/4
   with no message and a wrong infrastructure-failure exit reason).
3. **Three-state liveness.** `pid_alive` self-probes `ps -p $$` first; on
   platforms whose ps lacks `-p` (verified on BusyBox v1.37.0) it falls
   back to `kill -0`, whose success proves aliveness and whose failure is
   **cannot-determine → refuse** — never "dead". A live run's sentinel can
   no longer be offered for clearing on busybox-class systems.
4. **Prompt read time-bounded** (`read -t`, `BOOTSTRAP_PROMPT_TIMEOUT`
   default 60s): even a forced prompt on an open-but-silent pipe (the
   `BOOTSTRAP_TEST_FORCE_PROMPT` leak scenario, reproduced as an
   indefinite hang) now falls through to No at the bound.

**FREEZE-EXCEPTION (golden re-baseline no. 7, full_autonomous only).**
`auto.sh` + the queue-gated gitignore fragment line. Tests:
`tests/test_auto_run_sentinel.py` grows to 26 checks (dual-invocation
lock refusal, directory sentinel, broken-ps dead/live cases, hang bound).

**Class 2 — state-file migration & retrofit parity** (review findings 3,
10; plus the double-read TOCTOU noted by the verifiers):

1. **Corrupt-state backup.** The IC-3 migration now reads the pre-2.0.0
   state file ONCE and backs up those raw bytes even when the file is too
   corrupt to parse — previously a truncated state file skipped the
   backup and was clobbered (verifier-reproduced data loss). The
   single-read design also removes the parse-vs-backup second-read
   window, so the `.pre-2.0.0` backup is byte-identical to what the
   migration classified.
2. **Retrofit `gate_substrate` parity.** `_write_retrofit_state` now
   emits `gate_substrate: "shell"` alongside `bootstrap_protocol_version`
   — retrofit installs ship the same 2.0.0 wrappers and shell gate suite,
   and the 2.1.0 `ic_checks`/seam consumers key off the field.
   (Additive top-level key; B5 shape and the C1 sibling-function
   discipline preserved — `_write_state` untouched by this half.)

No golden impact (state files are `apply()`-time artifacts).
Tests: `tests/test_gate_substrate.py` → 15 checks (corrupt-file case);
`tests/test_retrofit.py` → 254 (8.5 parity assertion).

**Class 3 — gitignore surfaces** (review findings 2, 7, 8):

1. **Retrofit root-`.gitignore` emission.** `_apply_retrofit_overlay` (the
   single retrofit dispatch site per C1) now appends the `gitignore_root`
   managed-block action whenever any autonomous opt-in scaffolds a
   wrapper — the greenfield gate reads top-level `*_enabled` flags, which
   B5 pins false in retrofit mode, so retrofit projects previously got
   root-sentinel-honoring wrappers with committable sentinels (AC-4-5
   violated on that path; verifier-reproduced). No opt-ins → no root
   write, scope unchanged.
2. **Co-owned metadata preserved.** The managed-block append/refresh
   paths now keep the operator's existing file mode instead of resetting
   to 0644 (the inode still changes — content-write atomicity wins over
   inode stability for a gitignore).
3. **Migration backups never committable.** Both emitted `.claude/
   .gitignore` fragments gain the `.bootstrap-state.json.pre-*` pattern,
   covering the new `.pre-2.0.0` backup and every future one (the
   retrofit fragment's per-version entries stay for back-compat).

**FREEZE-EXCEPTION (golden re-baseline no. 8, BOTH fixtures, one file
each).** `.claude/.gitignore` gains the `pre-*` pattern — the first
default-fixture change since R-0; items 1 and 2 are overlay/apply-time,
outside the golden surface. Tests: `tests/test_root_sentinels.py` → 34
checks (retrofit emission + no-opt-in scope guard, mode preservation,
fragment pattern).

**Class 4 — goal-config value parsing** (review finding 9):

`goal-loop.sh` gains `goal_cfg_value()`: inline `# comment` stripped,
matching surrounding quotes removed, whitespace trimmed, sed failure
survived under errexit+pipefail — so an operator edit like
`evaluator_model: sonnet  # harder criteria` resolves to `sonnet`
instead of exporting the comment into the judge invocation verbatim
(probe-confirmed failure mode). The resolved value is logged
(`evaluator_model=<value>`) for observability; both the normative key
and the deprecated `judge_model` alias go through the same sanitizer.

**FREEZE-EXCEPTION (golden re-baseline no. 9, full_autonomous only,
goal-loop.sh).** Tests: `tests/test_goal_evaluator_keys.py` → 18 checks.

*Recorded, not fixed (out of review scope):* the per-task wrappers'
`log()` emits a literal `\n` (a `.format`-doubling quirk), so their
hooks.log entries share one physical line — `auto.sh`'s log() is
unaffected. Worth its own small freeze-exception later.

### Milestone B (reserved)

IC-5 (SDK `PreToolUse` callables per seam §9, Tessera-owned runner,
module-only emission), IC-6 (native worktree routing, flag/version to be
verified against official docs), `lib/ic_checks.py`, the runtime-floor
startup check (seam binds ≥ v2.1.210 for fail-closed PreToolUse timeout —
confirm the exact floor per the seam's own TODO), and the
`PROTOCOL_VERSION` → `"2.1.0"` bump land only after Milestone A review and
owner approval, and are recorded here as `2.0.0 → 2.1.0` when they do.

## 2.0.0 → 2.1.0 (Milestone B — SDK substrate; in progress)

**Seam:** `SEAM-CONTRACT-v1-2-0.md` (Milestone-A pin event: protocol
2.0.0 pinned by commit `1fa5bb6`). Branch `version-2-1-0`.

### B-pre — `_hook_tier` forcing function (entry precondition)

- `templates.HOOK_EVENT_MAP` hoisted to module level (emitted bytes
  unchanged; golden green pre-R-7); `installer.py` asserts at import that
  the seam §7.2 tier sets exactly partition the emitted hook set (new
  explicit `NON_CRITICAL_HOOKS`; unclassified/phantom/double-claimed
  names fail loud at every CLI entry point).

### Verify-first findings (2026-07-18, against official changelogs)

- **Claude Code runtime floor ≥ v2.1.210 CONFIRMED** (fail-closed
  PreToolUse hook timeout at 2.1.210; worktree-entry consent 2.1.206;
  exact-match hyphen matchers 2.1.195 — all subsumed by the floor). The
  seam's `[TODO: confirm]` on `claude_code_runtime` is resolvable
  seam-side with no value change. *Owner accepted 2026-07-18; the TODO
  drops as confirmed in the owner's seam patch.*
- **`claude-agent-sdk` feature floor = v0.1.60** (owner correction
  2026-07-18, re-verified at the tags). The basic §4.1 deny shape
  (`hookSpecificOutput` + `permissionDecision: "deny"` +
  `permissionDecisionReason`) exists from v0.1.2 tagged source, but the
  load-bearing dependencies land later: `dontAsk` absent from the SDK's
  `PermissionMode` until **0.1.51** (#719; the seam §3.1 mandated
  dispatch posture), and `setting_sources=[]` silently dropped until
  **0.1.60** (#822) — R-7's SessionStart/SessionEnd shell retention
  relies on `setting_sources=["project"]`. `additionalContext` on the
  PreToolUse output is 0.1.29 (subsumed). Floor = **0.1.60**, replacing
  the provisional ceiling-as-floor `>=0.2.114`. The `"defer"` decision
  value (0.1.74) is a FORWARD OPTION, deliberately not required. The
  seam patch is owner-side.
- **Native worktree flag `--worktree`/`-w` confirmed in official docs**
  (worktrees at `.claude/worktrees/<name>/`, branch `worktree-<name>`,
  `worktree.baseRef`, `.worktreeinclude`); its introduction version is
  NOT verifiable from official release notes (v2.1.49 is secondary-source
  only) — R-8 therefore relies on the binding ≥ 2.1.210 floor, which
  subsumes it, and pins no introduction version.

### R-7 (IC-5) — gates as SDK `PreToolUse` callables

- New emitter `lib/sdk_gates_template.py` — **[SR-11] the separate-module
  deviation is CONFIRMED at implementation** (Python-emitting-Python
  stays syntax-checkable outside templates.py's shell-heredoc
  conventions); registered as `TEMPLATES["sdk_gates"]`.
- Emits `.claude/sdk_gates/gates.py` per seam §9 VERBATIM: single public
  builder `build_hooks(config) -> {"PreToolUse": [HookMatcher...], ...}`,
  no I/O at import (probe-asserted), no network I/O, subprocess-only
  loading documented, refusals in the structured §4.1 deny shape with
  shell-parity reason strings (AC-7-5 fixtures assert each reason literal
  against the emitted shell bodies). Seven gates: secrets, spec-commit,
  dependency, test, tdd, eval (PreToolUse) + format-lint (PostToolUse,
  feedback-only, never denies — mirroring its warn-tier shell nature).
- Empty `commands.test` denies with the TODO reason (AC-7-2,
  fail-loud-on-empty-commands); the full shell suite remains emitted as
  the SEV-1 manual path (AC-7-3); `kind: "sdk_gates"` maps to the
  security-critical tier (AC-7-6) — the §7.2 membership addition the
  seam commits to at the substrate release, mirrored in
  `tests/test_hook_tiers.py`'s contract list deliberately.
- The retrofit overlay DROPS the module (retrofit stays shell-era
  `RETROFIT_PROTOCOL_VERSION`; Tessera's seam excludes retrofit, IG-10).
- Tests: `tests/test_sdk_gates.py` (49 checks, stubbed
  `claude_agent_sdk`).

**FREEZE-EXCEPTION (golden re-baseline no. 10, both fixtures).** Exactly
ONE new action each (54 → 55, 66 → 67): `.claude/sdk_gates/gates.py`.
Diff-verified vs HEAD: zero existing files changed, zero removed.

### R-8 (IC-6) — native worktree routing

- Baseline finding, recorded per the spec's verify-first note: the
  emitted wrappers contain **no hand-rolled `git worktree add`** — they
  are guarded skeletons whose iteration loop is operator-completed, so
  "replace hand-rolled creation with native" reduces to routing the
  documented dispatch through the native mechanism.
- `loop.sh` / `goal-loop.sh` skeletons now instruct the operator-
  completed loop to dispatch `claude -p --worktree "wt-$TASK_ID"`
  (Claude Code creates/reuses `.claude/worktrees/wt-<task-id>/`; a
  worktree is drift-prevention, NOT a security boundary) and forbid
  hand-rolling `git worktree add` (AC-8-1).
- The claim/sentinel + cross-mode accounting block is RETAINED with its
  why-native-does-not-cover-this documentation inline (AC-8-2/AC-8-3):
  `--worktree` isolates the working directory only; per-task mutual
  exclusion (O_CREAT|O_EXCL sentinel) and the combined-concurrency
  accounting (`loop_in_flight`/`goal_in_flight` under flock) stay in the
  wrapper.
- **Manual verification note (AC-8 "operator-only" shape):** native
  `--worktree`/`-w` behavior verified against the official worktrees
  docs on 2026-07-18 (worktrees at `.claude/worktrees/<name>/`, branch
  `worktree-<name>`, `worktree.baseRef`, `.worktreeinclude`); the flag's
  introduction release is not verifiable from official release notes
  (v2.1.49 is secondary-source only), so the wrappers rely on the
  binding seam runtime floor ≥ 2.1.210, which subsumes it. Live
  end-to-end wrapper dispatch remains operator-verified per the trust
  ramp (the skeleton refuses unattended use by design).
- Tests: `tests/test_installer.py` wrapper-shape assertions
  (`--worktree` present, no `git worktree add`, RETAINED-case doc
  present).

**FREEZE-EXCEPTION (golden re-baseline no. 11, full_autonomous only,
loop.sh + goal-loop.sh).** Diff-verified vs HEAD: exactly two files
changed, zero added, zero removed; default fixture byte-identical.

### R-9 — the IC gate + 2.1.0 release identity

- New `lib/ic_checks.py`: deterministic, self-contained IC-1..IC-7
  self-checks against the live emission surface (validate-only surface,
  wrapper sentinel dual-honor, state-writer behavioral probe, advisor
  default, SDK-gate module contract incl. single-public-builder AST
  check, native worktree routing, tier partition).
  `BOOTSTRAP_IC_FORCE_FAIL=<IC>` is a documented TEST-ONLY override that
  can only force REFUSING (the BOOTSTRAP_TEST_FORCE_PROMPT asymmetry).
- New config surface: top-level `gate_substrate: "shell" | "sdk-callable"`
  (default `"shell"`, byte-identity for existing configs; refused in
  retrofit mode). `"sdk-callable"` is a REQUEST: the installer refuses
  the install loudly — listing every failing check, writing nothing, an
  existing state file therefore retaining `"shell"` — unless all seven
  checks pass (AC-9-1); on green checks the state writer records the
  granted value (AC-9-2). The refusal applies under `--dry-run` too.
- `bootstrap-install --ic-checks` prints the checklist as JSON, exit
  non-zero on any failure — the CI-assertable form for the seam §8.2
  `protocol-compatibility` job (AC-9-3).
- AC-9-4 runtime-floor startup check: `_runtime_floor_check()` logs the
  detected Claude Code CLI version and warns LOUDLY below the seam floor
  ≥ 2.1.210 (confirmed against the official changelog 2026-07-18 —
  resolving the spec's "confirm the exact floor" note) or when
  undetectable; never fatal (the floor binds dispatch, not emission),
  never silent.
- Release identity (AC-9-5): `PROTOCOL_VERSION` → `"2.1.0"` in
  `lib/installer.py` + `lib/templates.py`; `INSTALLER_VERSION` → 1.1.0;
  `RETROFIT_PROTOCOL_VERSION` stays 1.6.2. The protocol document's
  conformance note gains the marked **[2.1.0 update — substrate
  OPERATIVE]** addition (incl. the recorded IC-6 caveat: `--worktree`
  confirmed in official docs, introduction release unverifiable,
  subsumed by the runtime floor).
- Deliberate test re-pins: `test_gate_substrate.py` AC-1-3 tripwire
  replaced with its promised Milestone-B form (sdk-callable writable
  ONLY via the ic_checks gate; writer never hardcodes it); version
  literals 2.0.0 → 2.1.0 in `test_installer.py` (AC-A0),
  `test_gate_substrate.py`, `test_retrofit.py` (8.3).
- Tests: `tests/test_ic_gate.py` (28 checks: gate refusal/grant/JSON
  checklist, config enum + retrofit exclusion, floor-warn via
  PATH-injected fake `claude`, release identity).

**FREEZE-EXCEPTION (golden re-baseline no. 12, both fixtures).** Exactly
ONE file each: settings.json `_generatedBy` "protocol 2.0.0" →
"protocol 2.1.0" (emitted doc citations untouched — the protocol document
keeps its versioned v2-0-0 self-name). Diff-verified vs HEAD: zero added,
zero removed, no other file changed.

### Code-review fix pass (max-effort adversarial review of R-7..R-9)

Correctness (emitted `sdk_gates/gates.py`):
- **NameError-proofing:** the emitted `RESOLVED_CONFIG` snapshot coerces
  leaf scalars to `str`, so a YAML-typed `commands.test: true` (bool/None)
  no longer renders `true`/`null` — undefined Python names that
  NameError'd the whole module at the consumer's import.
- **Gates run non-blocking:** every `subprocess.run` inside an async hook
  is now `asyncio.create_subprocess_*` via a shared `_run` helper — a
  blocking test/lint no longer freezes the consumer's single-threaded SDK
  event loop for up to the declared timeout.
- **tdd-gate** normalizes ABSOLUTE `file_path` (what Claude Code sends) to
  project-relative before the `src/|lib/` test — it was a silent no-op.
- **dependency-gate** handles `@scoped` npm packages, collapses whitespace
  (tab / multi-space), and recognizes `python[3] -m pip install` — closing
  fail-open bypasses.
- **secrets-gate** normalizes bash negated classes `[^…]` → fnmatch `[!…]`
  so the deny-list OVER-matches (the T-1 bias it claimed but violated);
  patterns are precomputed once per config.
- **test-gate** staleness scans `src/` AND `lib/` (parity with tdd's
  source definition); **eval-gate** inspects the whole `@{u}..HEAD` push
  range, not just the last commit; **spec-gate-commit** skips dot-dirs to
  match the shell corpus; **format-lint** merges stderr→stdout for the
  shell's chronological `2>&1 | tail`.
- **build_hooks** derives gate MEMBERSHIP from the passed config
  (`_resolved_hooks`, now carried in the snapshot), never a stale
  emission-time set.

IC gate (`lib/ic_checks.py`) + state transition:
- **IC-1/IC-4** are now BEHAVIORAL/attribute checks (drive
  `interview.main --validate-only`; assert the hoisted
  `llm_advisor.DEFAULT_ADVISOR_MODEL`) instead of source greps that
  green on a docstring; **IC-2** matches `"$ROOT_HALT"` (not the
  `ROOT_HALT_HARD` substring); **IC-6** inspects NON-COMMENT lines for a
  hand-rolled `git worktree add` (the strip-the-phrase match had become a
  shadow grammar — it broke on the very fix that documented the flag).
- `BOOTSTRAP_IC_FORCE_FAIL` RAISES on an unknown value (was a silent
  no-op into a real grant).
- The partition forcing function moved from import-time to `build_plan`,
  so a violation no longer crashes `--ic-checks` (whose IC-7 reports it)
  or `--uninstall`.
- The IC gate runs before `--print-config` returns (verdict consistency
  with the install), and `_write_state` ENFORCES the gate at the write
  (`_ic_gate_cleared` token) — no caller bypassing `main()` can stamp an
  ungated `sdk-callable`; a substrate downgrade on re-apply warns loudly.
- `resolve_config` validates `gate_substrate` before the archetype
  early-return (errors batch) and normalizes an invalid value to `shell`.

Lifecycle:
- `apply_plan` removes stale files dropped from the plan on re-apply (a
  retrofit-over-greenfield re-install no longer orphans
  `sdk_gates/gates.py` on disk while losing its manifest digest); the
  `.claude/.gitignore` ignores `sdk_gates/__pycache__/`; the wrapper's
  IC-6 comment documents the `.git/info/exclude` worktree-ignore (the
  committed-`.gitignore` fix would break `git worktree add`); the
  runtime-floor version parse is anchored (ignores update-notifier
  banners, scans stderr too); the conformance-note stale tail corrected.

Tests: +25 regression checks across `test_sdk_gates.py` (57) and
`test_ic_gate.py` (37). Full suite: 700 checks green / 13 files.

**FREEZE-EXCEPTION (golden re-baseline no. 13, both fixtures).** Emitted-
byte changes: `.claude/.gitignore` + `.claude/sdk_gates/gates.py` (both
fixtures); `.claude/loop.sh` + `.claude/goal-loop.sh` (full_autonomous).
Diff-verified vs the pre-fix head: zero files added, zero removed.

### Adversarial re-sweep — regressions the fix pass introduced

A second max-effort sweep over the fix commit found regressions the fixes
themselves created; all fixed here, each now with a non-tautological
regression test:
- **`build_hooks` empty-set trap:** an empty `_resolved_hooks` (`[]`) fell
  through to zero gates — a security substrate silently disabling all
  enforcement. Now a missing OR empty value falls back to the emission
  `GATES` (never the empty set).
- **`gates.py` orphan, sharpened:** the new stale-file cleanup deleted
  `gates.py` on a greenfield-sdk-callable → retrofit re-apply, but the
  retrofit state writer (a separate `.retrofit-state.json`) left
  `.bootstrap-state.json` still advertising `sdk-callable`.
  `_reconcile_orphaned_substrate` now downgrades it to `shell` loudly when
  the module is no longer emitted.
- **`--dry-run` now previews removals** (`REMOVE (dry run)` + counted) so
  the preview is faithful for the destructive re-apply case.
- **Dependency-gate:** versioned `pip3.11 install` matched (`pip[0-9.]*`);
  whitespace collapse no longer merges a verb split across NEWLINES
  (per-line scan) — that would false-block a commit whose message merely
  mentions an install verb.
- **tdd-gate `_proj()` resolves** to an absolute root so the
  absolute-path relativization is stable.
- **IC-1 is genuinely end-to-end:** it builds a real interview via
  `analyze` and drives `synthesize --validate-only` to the validate
  branch (the prior probe returned at file-not-found, before the branch —
  a vacuous check); **IC-5** defers to IC-7 instead of misattributing a
  partition break; runtime-floor parse also matches a `version`-keyword
  form.
- **Worktree comment de-mangled:** the `.git/info/exclude` example used a
  shell line-continuation backslash that Python collapsed inside the
  non-raw template string, corrupting the emitted one-liner; rewritten as
  a single line.

Also proven (previously untested): stale-file cleanup end-to-end (unlink
+ manifest-orphan removal + L-1 hand-edit preservation + state
reconcile), runtime-floor banner anchoring, `build_hooks` enlargement
from a genuine subset fixture, eval-gate `@{u}..HEAD` whole-range with an
upstream.

Tests: 706 checks green / 13 files (`test_sdk_gates.py` 63,
`test_ic_gate.py` 44). *(RC-08 correction, 2.2.0: this line previously
claimed 726 — a stale tally never matched to a measured run. The measured
total at the 2.1.0 tip is 706; corrected in place rather than carried
forward. No test was removed — the 726 figure was wrong when written.)*

**FREEZE-EXCEPTION (golden re-baseline no. 14, both fixtures).** Emitted-
byte changes: `.claude/sdk_gates/gates.py` (both); `.claude/loop.sh` +
`.claude/goal-loop.sh` (full_autonomous, worktree comment). Diff-verified
vs the prior head: zero files added, zero removed.

## 2.1.0 → 2.2.0 (usage-limit coping + gap-closure merge)

**Spec:** `Bootstrap-Protocol-v2-2-0.md` (AR2-corrected) +
`Bootstrap-Protocol-Companion-v2-2-0.md`. Reset-aware usage-limit handling
bound into the per-task wrapper skeletons' comment contract, consuming the
Claude Agent SDK's `rate_limit_event` / `RateLimitInfo` stream contract,
plus the gap-closure items (deliverable contract, `exit_reason` enum and
run-summary structure enumerated in emitted comments, blessed goal-config
extras already shipped at 2.1.0). Changelog-first; minimal-diff; fail-loud;
no drive-by refactors. Work items R1–R8 map 1:1 to the implementation
prompt.

Live-capture basis (Step 0): `claude -p "say ok" --output-format
stream-json --verbose` on CLI 2.1.215 confirmed the wire shape used
below — NDJSON lines with a top-level `type`, and a `rate_limit_event`
line carrying a nested `rate_limit_info` object with camelCase
`status` / `resetsAt` / `rateLimitType` (observed value `seven_day`,
`status: "allowed_warning"`). Confirms AR2-03.

### R1 — Three usage-limit-wait config keys

`usage_limit_wait` (`reset-aware` | `off`, default `reset-aware`),
`usage_limit_max_wait_seconds` (default `21600`), and
`usage_limit_wait_jitter_seconds` (default `60`) added to **both**
`loop-config.md` and `goal-config.md`, adjacent to the existing
`infra_retry_seconds` / `infra_max_consecutive_failures` pair, each with a
one-line comment (PRD Phase 9.5, §`.claude/loop-config.md` / Phase 9.6
`goal-config.md`). Existing config files without the keys stay valid — the
wrappers apply the documented defaults (Companion Migration notes).

### R2 — Dispatch flags on the documented invocation

The skeleton's documented `claude -p` dispatch instruction gains
`--output-format stream-json --verbose` alongside `--worktree` (flags
added, nothing removed) in the `[IC-6]` header and the closing dispatch
echo of `_per_task_wrapper`. The NDJSON stream these flags produce is what
the usage-limit branch tails (PRD Phase 9.5 "Infrastructure-error
handling").

### R3 — Per-task skeleton binding comments (usage-limit vs transient split)

New normative comment block in `_per_task_wrapper` (emitted into both
`loop.sh` and `goal-loop.sh`), wording per PRD Phase 9.5 (AR2-01/02/03/05
corrected): match `rate_limit_event` by the line's **top-level `type`**
(never substring); camelCase wire keys in nested `rate_limit_info`
(`status`, `resetsAt` Unix seconds may-be-absent, `rateLimitType` ∈
five_hour | seven_day | seven_day_opus | seven_day_sonnet | overage);
record the most recent event before exit; on a non-expected non-zero exit
a `rejected` + future `resetsAt` → usage-limit path, `rejected` +
absent/past `resetsAt` → transient path; `reset-aware` wait =
`(resetsAt − now) + jitter` (jitter uniform `0..usage_limit_wait_jitter_seconds`,
added only), ceiling `usage_limit_max_wait_seconds` → halt with
`usage-limit-reset-abandoned` into `loop-final-<task-id>.md` surfacing
bucket + reset time; otherwise sleep then re-probe the **same** iteration
without incrementing the counter; the wait does **not** consume the
transient retry; **never compute your own reset time** (honor `resetsAt`
as floor-plus-jitter, never hardcode +5h/+7d); `usage_limit_wait: off`
routes rejections to the transient path; fail-loud fallback if the build
stops emitting `rate_limit_event`; substrate-independent
`CLAUDE_CODE_RETRY_WATCHDOG=1` watchdog note (in-request retry,
complementary, not gated on `gate_substrate`).

### R4 — `goal-loop.sh` judge-parity comment

A `rejected` usage-limit `rate_limit_event` on **either** the `claude -p`
call **or** the judge call takes the same reset-aware wait path and does
**not** consume the judge retry-once (PRD `.claude/goal-loop.sh` /
`goal-config.md` descriptions). Injected only into `goal-loop.sh` via the
per-kind parity placeholder; `loop.sh` does not carry it.

### R5 — `auto.sh` skeleton comments (enum + run-summary + runner rule)

New comment block in `_auto_sh` enumerating **all 13** `exit_reason`
values with one-line triggers (Recovery & State enum, PRD lines 138–150);
the required run-summary structure incl. the `Ended because` line (code +
one plain sentence; `urgent-escalation` names the pending-decision note;
`usage-limit-reset-abandoned` names the limiting bucket `rate_limit_type`
and reset time `resets_at`); the AR2-01 terminal runner rule (an observed
`usage-limit-reset-abandoned` task halt is terminal-at-queue-level via
graceful shutdown, propagates the bucket/reset time, and counts toward
**neither** the three-consecutive-halts threshold **nor** the
infrastructure-failure threshold — the cap is account-level, so continuing
manufactures a mislabeled `three-consecutive-halts` cascade); and the
AR2-09c **key-less** runner posture (brief sleep + retry, two consecutive
runner-level failures → halt; `auto-config.md` keeps its budget keys and
gains no runner-level `infra_*` keys).

### R6 — Version identity + citation re-baseline (RC-03)

- `PROTOCOL_VERSION` → `"2.2.0"` (`lib/installer.py`, `lib/templates.py`).
  `INSTALLER_VERSION` stays `"1.1.0"`; `RETROFIT_PROTOCOL_VERSION` stays
  `"1.6.2"`. Test literals re-pinned. `plugin/plugin.json` version +
  description → 2.2.0 (review finding: the 2.1.0 release-identity commit
  `0ac36bd` established plugin.json as part of the release set; the
  implementation prompt's R6 omitted it).
- **RC-03 (decided: yes):** emitted protocol-document citations
  `Bootstrap-Protocol-v2-0-0.md` → `Bootstrap-Protocol-v2-2-0.md`, **scoped
  to the files this change already touches** — `loop.sh`, `goal-loop.sh`,
  `loop-config.md`, `goal-config.md`, `auto.sh`. The 11 emitted hook
  citations are **deliberately left at `v2-0-0`**: re-pointing them would
  change bytes in the *default* fixture (11 hook files) outside the named
  FREEZE-EXCEPTION set, violating the mandated "zero unintended byte
  changes outside the named set" gate. This is the same citation-lag
  posture as freeze-exception no. 12 (2.1.0 kept citations at v2-0-0). The
  citation bytes re-pointed here ride inside the no. 15 re-baseline below.
  *(Operator flag: this partial re-point is an intentional, gate-forced
  scope decision, not an omission — see the session report.)*

### R7 — New suite `tests/test_usage_limit_contract.py`

Standalone-suite style (own pass/fail counter, `sys.exit(1)` on any
failure). Emits both fixtures via `build_plan` and string-asserts the
config keys/defaults/co-location, the per-task skeleton contract strings
(both wrappers, plus the goal-only judge-parity sentence), the `auto.sh`
enum + render clause + runner rule, and the negative assertion that no
`usage_limit_*` key appears in `auto-config.md`.

### R8 — Eighth IC check: deferred (AR2-09b)

Not added. Recorded post-2.2.0 in the PRD with its cost-of-deferral line;
the golden fixtures + R7 cover the repo-side risk. AR2-09a (no emitted
run-summary template file) likewise stands — the structure is bound only
through `auto.sh`'s comment contract.

**Test count (measured, honest).** Pre-change: **706** checks / 13 files
(RC-08: the 2.1.0 section's "726" was a stale never-measured tally,
corrected above). Post-change: **802** checks / 14 files — the delta is
`tests/test_usage_limit_contract.py` (**95** checks after the review-pass
strengthening below) plus one new release-identity check in
`test_ic_gate.py` (44 → 45) and re-pinned version literals in existing
suites; the golden digests re-baseline (no. 15) but the action counts
(default 55 / full_autonomous 67) are unchanged.

**Adversarial-review fix pass (pre-merge, multi-lens).** Eight finder
angles + per-candidate verification over the working diff; six confirmed
findings fixed (zero emitted-byte impact — golden digests unchanged,
verified):
1. `plugin/plugin.json` bumped to 2.2.0 (see R6 above).
2. `test_ic_gate.py` gains the `2.1.0 → 2.2.0` changelog-entry tripwire
   (the convention the 2.1.0 release established but R6 didn't carry
   forward).
3. R5 enum assertions anchored to the emitted enum-block line shape
   (`"\n#   <value>  "`) plus a set-equality count guard parsed from the
   emitted block — mutation-verified: 7 of 13 enum literals were
   previously satisfiable by occurrences outside the enum block, and the
   old count guard compared the test's own list to a literal (tautology).
4. AR2-01 assertions anchored (`ar2-01,\n#  terminal.]`) and the
   counted-toward-neither rule asserted as one contiguous
   whitespace-normalized clause — mutation-verified against a
   semantics-inverting edit that the old fragment checks passed.
5. Six subsumed R1 bare-key checks collapsed into the key+default needles
   (the `test_goal_evaluator_keys.py` convention).
6. New RC-03 citation-integrity checks: the five re-pointed files cite
   `Bootstrap-Protocol-v2-2-0.md` with no stale `v2-0-0` residue, and both
   cited docs exist at the repo root (they are new files this release —
   an omitted `git add` would otherwise ship dangling citations with CI
   green). Two stale Python-side (non-emitted) `v2-0-0` comments in the
   touched `_auto_sh` / `_per_task_wrapper` regions re-pointed.
Round 2 (fresh-eyes pass over the fixed diff; three confirmed
spec-fidelity findings, all emitted-byte changes riding inside the no. 15
named set — `loop.sh`/`goal-loop.sh`/`auto.sh` only, default fixture
untouched, digest re-verified):
7. The usage-limit vs transient split now DEFINES the transient arm
   instead of only referencing it: a third classification arm (no
   `"rejected"` `rate_limit_event` at all — network error, 5xx, 529 —
   → transient path) and a transient-path paragraph naming
   `infra_retry_seconds` / `infra_max_consecutive_failures` and the
   same-iteration no-increment retry (Phase 9.5 transient paragraph; the
   deliverable contract requires the comments to enumerate the split, and
   half of it was previously implicit).
8. `auto.sh` enum one-liners restore two load-bearing qualifiers dropped
   from the Recovery & State wording: `three-consecutive-halts` is scoped
   "within the run", and `operator-only-timeout`'s blocking is
   "transitively" on operator action.
9. The suite now emits BOTH fixtures (its docstring/this-section claim was
   previously false): a default-fixture negative asserts no `usage_limit`
   text leaks into any non-autonomous emitted file and no wrappers are
   emitted; plus transient-arm and enum-qualifier assertions (85 → 95).
Report-only (deliberate non-fixes): the emitted wrapper `log()`/sentinel
`printf '%s\\n'` literal-backslash-n quirk is pre-existing at 2.1.0 and on
the recorded deferred-cleanup backlog — fixing it perturbs frozen emitted
bytes and belongs to its own freeze-exception, not this change.

**FREEZE-EXCEPTION (golden re-baseline no. 15).** Emitted-byte changes,
diff-verified vs the pre-change head (zero files added, zero removed):
- **`full_autonomous` fixture (6 files):** `loop.sh` and `goal-loop.sh`
  (R2 dispatch flags + R3 usage-limit comment block + R4 goal-parity
  comment on goal-loop.sh + RC-03 citation re-point); `loop-config.md` and
  `goal-config.md` (R1 three keys + RC-03 citation re-point); `auto.sh`
  (R5 enum/run-summary/runner comment block + RC-03 citation re-point);
  `settings.json` `_generatedBy` (R6, `protocol 2.1.0` → `protocol
  2.2.0`).
- **`default` fixture (1 file):** `settings.json` `_generatedBy` only
  (`protocol 2.1.0` → `protocol 2.2.0`). The default fixture emits no
  wrappers/config/runner, so R1–R5 and the RC-03 re-point do not reach it;
  its hook citations remain at `v2-0-0` by design (see R6).
Everything outside this named set is byte-identical to the pre-change head.

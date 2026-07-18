# Spec: Bootstrap Protocol v2.0.0 implementation

**Slug:** `bootstrap-v2` · **Target path in repo:** `.claude/specs/bootstrap-v2/requirements.md` · **Revision:** 3 *(rev-3, owner-confirmed 2026-07-17: decomposition R-0..R-9 ↔ IC-1..IC-7 confirmed as the implementation contract; AC-6-5 reworded to verify-existing (`effort: high` already emitted, `templates.py:769`/`:2075`); R-4 [SR-17] gitignore home decided: option (a) managed block.)*
**review_applied:** `SESSION-ADVERSARIAL-REVIEW.md` — SR-01, SR-02, SR-04, SR-07, SR-08, SR-11, SR-12, SR-13, SR-16, SR-17 applied inline (tagged).
**Upstream contract:** `Bootstrap-Protocol-v2-0-0.md` (Implementation Contract IC-1..IC-7), its Companion, `SEAM-CONTRACT-v1-2-0.md` **incl. its §9 SDK-gate-module entry** (folded 2026-07-17; runner ownership resolved Tessera-owned; v1.2.0 = Milestone-A pin event, `binds.bootstrap_protocol` = `2.0.0 @ 1fa5bb6`) [SR-01], `IMPLEMENTATION-GAP-ANALYSIS.md`.
**Baseline verified against:** live `main` tree, `PROTOCOL_VERSION = "1.9.0"`.

---

## Problem

The v2.0.0 document leads the code by owner decision (2026-07-17). The live tree is `1.9.0`. This spec decomposes the work that makes the tree conformant and flips the enforcement substrate, gated on the honest `gate_substrate` state signal. Two milestones with distinct release identities [SR-04]: **Milestone A ships as protocol 2.0.0** (`gate_substrate` stays `"shell"`); **Milestone B ships as protocol 2.1.0** — the 2.0.0 conformance note explicitly reserves the SDK-callable substrate for "a subsequent 2.x release," so Milestone B must not land under 2.0.0.

## Definition of done (whole spec)

1. Every IC below has a green test in `tests/`.
2. `tests/test_greenfield_golden.py` passes, with each intentional digest re-baseline recorded as a freeze-exception in `docs/changelog.md`. The golden surface covers `build_plan` output only; the manifest and state file are `apply()`-time artifacts outside it [SR-07].
3. The installer refuses to write `gate_substrate: "sdk-callable"` unless the IC-1..IC-7 self-checks all pass (`lib/ic_checks.py`).
4. `docs/changelog.md` carries a `1.9.0 → 2.0.0` entry (Milestone A) and a `2.0.0 → 2.1.0` entry (Milestone B), plus a migration note: operators who never opt into the SDK substrate see no behavioral change beyond the new `gate_substrate: "shell"` field.
5. No change to the result-parsing fields, sentinel names/locations, or hook-tier membership that the seam declares contract-level is made without being surfaced as a seam event. The SDK gate module is implemented **verbatim against the seam §9**; a deviation is a seam edit, not a code choice [SR-01].
6. Milestone B's release identity is **2.1.0** [SR-04].

## Invariants that must survive every task

- **`fail-loud-on-empty-commands`** — gates generated with empty `commands.test`/`lint`/`format` emit a TODO marker that fails loud, never silently pass. Holds in both shell and SDK-callable paths.
- **`compose-do-not-fork`** — no per-project gate-exception mechanism. The only sanctioned exception is the audited security-critical hand-edit flow.
- **Subprocess isolation** — the emitted SDK-gate module is loadable only by a *subprocess* dispatch runner, never imported into a consumer's core process (seam §2 non-import rule; Tessera AC-PROTO-001 class; locked in the seam §9).
- **`resolve_config` invariants unchanged** — `queue ⇒ loop | goal`; `prd_tier` enum (`micro|standard|full`); archetype enum. Verify, do not modify.

## Precondition for Milestone B [SR-01]

The **runner-ownership decision** is **resolved: Tessera-owned (consumer-owned)** (owner decision 2026-07-17, recorded in seam contract §9). R-7 implements verbatim against the locked seam §9 module contract: path `.claude/sdk_gates/gates.py`; single public builder `build_hooks(config: dict) -> dict[str, list[HookMatcher]]` (proposed shape, locked at the substrate-release seam bump); no I/O at import time; no network I/O ever; security-critical tier; subprocess-only loading. The dispatch runner is Tessera-owned and therefore Tessera-side code — the protocol emits the module only, never a runner entrypoint.

---

## Milestone A — protocol 2.0.0 (`gate_substrate` stays `"shell"`)

### R-0 — Version bump

**Change:** `PROTOCOL_VERSION` at `lib/installer.py:36` and `lib/templates.py:13` → `"2.0.0"`. `RETROFIT_PROTOCOL_VERSION` (`installer.py:37`) stays `"1.6.2"` unless the retrofit track independently requires it. Update every internal cross-ref and `_generatedBy` string. Land the `BOOTSTRAP.md`→`Bootstrap-Protocol-v2-0-0.md` and Companion renames in the same commit; delete the old filenames so cross-refs resolve.

**Acceptance criteria.** AC-A0-1: `grep -rn 'PROTOCOL_VERSION = "1.9.0"' lib/` returns zero. AC-A0-2: a fresh install writes `bootstrap_protocol_version: "2.0.0"` to the state file. AC-A0-3: `_generatedBy` strings in `settings.json` and the manifest read `protocol 2.0.0`.
**Eligibility shape:** eligible for both. **Test:** extend `tests/test_installer.py`.

### R-1 (IC-3) — `gate_substrate` state field

**Change:** in `lib/installer.py` `_write_state` (state dict ~L446), emit `"gate_substrate": "shell"`. Add a non-destructive migration that stamps `"shell"` onto any pre-2.0.0 state file read, backing up to `.bootstrap-state.json.pre-2.0.0` per the Companion Migration notes. Never write `"sdk-callable"` in Milestone A.

**Acceptance criteria.** AC-1-1: fresh install → state file has `gate_substrate: "shell"`. AC-1-2: installing over a 1.x state file lacking the field adds `"shell"` and writes the `.pre-2.0.0` backup. AC-1-3: the writer never emits `"sdk-callable"` while any IC self-check is unimplemented/failing. *(The state file is an `apply()`-time artifact outside the golden surface — behavioral coverage only [SR-07].)*
**Eligibility shape:** eligible for both. **Test:** `tests/test_gate_substrate.py`.

### R-2 (IC-1) — `synthesize --validate-only`

**Change:** add `--validate-only` to the `synthesize` subparser in `lib/interview.py` (today: `-i/--interview`, `-o/--out`). Behavior: parse interview → run `resolve_config` → report invariant violations to stderr → **write no output file** → exit code reflects validity (0 valid / non-zero invalid).

**Acceptance criteria.** AC-2-1: `--validate-only` on a valid interview exits 0 and writes no file (assert output path absent post-run). AC-2-2: on an interview violating a `resolve_config` invariant (e.g. `queue` without `loop|goal`), exits non-zero with the violation on stderr and writes nothing. AC-2-3 **[SR-12 reworded]**: absent the flag, `synthesize` behavior is byte-identical to 1.9.0 — asserted via `tests/test_interview.py` output-equality on a fixture interview; note `interview.py` is outside the golden test's surface (golden covers `build_plan` only), so the equality assertion lives here, not there.
**Eligibility shape:** eligible for both. **Test:** `tests/test_validate_only.py`.

### R-3 (IC-4) — advisor default model

**Change:** `lib/llm_advisor.py:85-86` default `"claude-sonnet-4-20250514"` (retired) → the current Sonnet 5 ID (verify exact string against `platform.claude.com` — expected `claude-sonnet-5`). Preserve proposes-never-decides and deterministic-fallback-on-any-failure.

**Acceptance criteria.** AC-3-1: default model resolves to a live ID (no retired string in source). AC-3-2: with `--llm` and an unreachable/failing model, the advisor falls back to deterministic heuristics **loudly** (a surfaced notice, not a silent swap) and still produces a valid proposal. AC-3-3: commands are never sent to the model (existing behavior; assert unchanged).
**Eligibility shape:** eligible for both. **Test:** `tests/test_advisor_model.py`.

### R-4 (IC-2) — root-sentinel dual-honor

**Change:** in the `auto.sh`/`loop.sh`/`goal-loop.sh` template bodies (`lib/templates.py`; today `RUN="$PROJ/.claude/queue/.run-active"`, `HALT="$PROJ/.claude/queue/.halt"`), additionally honor `<project-dir>/.halt` (graceful stop at next boundary) and NEW `<project-dir>/.halt-hard` (immediate wrapper exit; wrapper does **not** signal in-flight `claude -p` — killing is the caller's job). Existing `.claude/queue/.halt`/`.resume` remain. Dual-honor is **permanent**.

**[SR-17] Gitignore home — DECIDED: option (a) (owner decision 2026-07-17), with constraints.** The protocol's emitted ignore fragments are `.claude/`-scoped (verified: `queue/.halt`, `sessions/.loop-active-*`, …); the root sentinels sit outside that scope. The installer writes them to the **project-root** `.gitignore` — a new write surface outside `.claude/` — under these constraints: (1) **Greenfield** (no root `.gitignore` exists): the installer creates it containing a marker-delimited managed block (`# --- bootstrap-protocol managed: begin ---` … `# --- bootstrap-protocol managed: end ---`) with `/.halt` and `/.halt-hard` — fully deterministic, manifest-tracked normally. (2) **Existing `.gitignore`**: append the managed block idempotently (skip if the block is already present); do **NOT** whole-file digest-track a co-owned file — record it in the manifest with a distinct state (`state: managed-block-appended`) so operator edits outside the block never fire hand-edit warnings and re-installs never clobber operator content. (3) The write is surfaced in `--dry-run` output and the Phase 0.5 preview. (4) Rationale for the record: option (b) fails AC-4-5's not-committable-by-default clause as written — a documentation-grade control on a must-hold property; a committed sentinel hard-halts every clone and can trip `spec-gate-commit` with a spurious block.

**Acceptance criteria.** AC-4-1: with `<project-dir>/.halt` present, each of the three wrappers stops at its next boundary. AC-4-2: with `<project-dir>/.halt-hard` present, each wrapper exits immediately and does not send a signal to a running `claude -p` (assert no kill from the wrapper). AC-4-3: the pre-existing `.claude/queue/.halt`/`.resume` paths still work unchanged. AC-4-4: golden digests for the three wrapper bodies re-baselined and recorded as freeze-exceptions. AC-4-5 [SR-17]: the decision-(a) managed-block mechanism is implemented and the root sentinels are not committable by default under it. Two fixtures: **fresh repo** (block created, sentinels ignored) and **pre-existing `.gitignore` with operator content** (block appended once, operator lines untouched, second install is a no-op).
**Eligibility shape [SR-16]:** eligible for both per the six criteria; *separately*, the golden freeze-exception requires operator review at merge regardless of eligibility shape. **Test:** `tests/test_root_sentinels.py` + golden re-baseline.

### R-5 (IC-7) — machine-readable hook tiers

**Change:** in `lib/installer.py`, add a `tier` field to each hook's manifest entry **and to `settings.json`'s entry** (it is a member of the security-critical set), valued `security-critical` / `autonomy-critical` / `non-critical` per seam §7.2. Membership (verified against `_hook_body`): security-critical = `secrets-gate`, `spec-gate-commit`, `dependency-gate`, `test-gate`, `eval-gate`, `tdd-gate`, `format-lint-gate`, `settings.json`; autonomy-critical = `drift-detector-loop-cooperation`, `iteration-summary-enforcement`; all else non-critical; `spec-gate-entry` deliberately non-critical (warn-tier).

**[SR-02] Forward note:** these lists are the **shell-era baseline, not a frozen ceiling** — Milestone B extends the security-critical set with `sdk_gates/gates.py`, a §7.2 contract-level change landing with the Milestone-B seam MAJOR per seam §9. (The dispatch runner is Tessera-owned per the seam §9 decision — Tessera-side code, not a protocol-manifest entry — so it does not join this list.)

**Acceptance criteria.** AC-5-1: every hook manifest entry and the `settings.json` entry carry a valid `tier`. AC-5-2: membership matches the seam §7.2 lists exactly (assert the three sets). AC-5-3: a downstream reader can derive the security-critical set from the manifest without hard-coding it. *(Former AC-5-4 deleted [SR-07]: the manifest is constructed at `apply()` time and is outside the golden surface — golden cannot see this change, so a mandated re-baseline was a category error; coverage is behavioral, here and in `tests/test_installer.py`.)*
**Eligibility shape:** eligible for both. **Test:** `tests/test_hook_tiers.py`.

### R-6 — model remap on subagent frontmatter [SR-08 rewritten]

**Change — assertion, not assumed diff.** Verified against the live tree: `bootstrap.config.yaml` already emits `implementer_model: "sonnet"`, `reviewer_model: "opus"`, `integrator_model: "inherit"` — the remap's alias assignments **already match** the Model Assignment Strategy table. The remap's substance at the emission layer is platform-side alias *resolution* (aliases now resolve to Sonnet 5 / Opus 4.8 / Haiku 4.5), which is exactly the managed-drift design guardrail 3b accepts, and which produces **zero emission diff by design**. The work here is: (1) assert the emitted assignments match the table (including judge default `haiku` in `goal-config.md` and summary-synthesis default `haiku` in `auto-config.md`, per the Companion); (2) assert every emitted subagent carries an explicit `model:` field; (3) do not emit a Fable subagent.

**Acceptance criteria.** AC-6-1: every emitted subagent definition carries an explicit `model:` field (the integrator's is explicitly `inherit`). AC-6-2: assignments match the strategy table. AC-6-3: no emitted agent references Fable. AC-6-4 **(conditional, replaces the former unconditional re-baseline)**: *if* any emission diff occurs in satisfying AC-6-1/6-2, each changed file is individually justified and golden is re-baselined as a freeze-exception; if no diff occurs — the expected outcome — no re-baseline happens and none is manufactured. AC-6-5 **(VERIFY — reworded, owner decision 2026-07-17)**: (a) the `effort:` field is **already emitted** — `effort: high` on the reviewer at `templates.py:769` (greenfield) and `templates.py:2075` (retrofit variant); the criterion is verify-existing, not decide-whether-to-emit. (b) Docs-verification half retained: confirm against current official Claude Code docs that `effort:` is a recognized subagent-frontmatter key and record its documented semantics — emitted is not the same as supported; if the docs don't recognize it, **flag to the owner** rather than deleting the field. (c) Assert the emitted value matches the Companion's model table (reviewer = `high`) and that the greenfield and retrofit emissions stay consistent.
**Eligibility shape:** eligible for both. **Test:** membership assertions in `tests/test_installer.py`; golden only-if-diff.

---

## Milestone B — protocol 2.1.0 [SR-04] (`gate_substrate` becomes writable as `"sdk-callable"`)

### R-7 (IC-5) — gates as SDK `PreToolUse` callables

**Change:** emit the project-resident module **verbatim per the seam §9** [SR-01]: `.claude/sdk_gates/gates.py`, digest-tracked, exposing the single public builder `build_hooks(config: dict) -> dict[str, list[HookMatcher]]` (the amendment's proposed shape; any deviation is a seam edit first), no I/O at import time, no network I/O ever, subprocess-only loading. Each gate — secrets, spec-commit, dependency, test, tdd, eval, format-lint — becomes `async def(input_data, tool_use_id, context) -> dict`, returning on refusal `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": <reason>}}` and `{}` (allow-by-omission) otherwise. `HookMatcher(matcher="Bash"|"Read|Write|Edit"|"Write", hooks=[...], timeout=...)`. **Retain** shell hooks for `SessionStart`/`SessionEnd` (absent from the Python SDK `HookEvent`) via `setting_sources=["project"]`, and keep the full shell suite as the SEV-1 manual path.

**[SR-11] Template-module deviation, stated:** the emitter lives in `lib/sdk_gates_template.py`, a deliberate deviation from the single-`templates.py` convention — Python-emitting-Python benefits from syntax-checkable separation. Confirm or fold into `templates.py` at implementation; either outcome is a recorded decision, not an accident.

**Acceptance criteria.** AC-7-1: each gate returns a structured `deny` with the correct `permissionDecisionReason` on a known-bad input, and `{}` on a known-good input. AC-7-2: an empty-command gate (e.g. empty `commands.test`) still fails loud (deny with the TODO reason), never allow-by-omission. AC-7-3: `SessionStart`/`SessionEnd` remain shell hooks. AC-7-4: the module is importable by a standalone subprocess entrypoint and is *not* imported by any consumer-core path (mirrors AC-PROTO-001); the module performs no I/O at import time (assert via an import under a denied-I/O harness or an import-side-effect probe). AC-7-5 **[SR-13 reworded]**: for a shared fixture input, the rendered `permissionDecisionReason` equals the rendered shell-gate message text for the same input, modulo the documented interpolation sites; the fixture set covers every gate's deny path. AC-7-6 **[SR-02; FD-06 resolved]**: `sdk_gates/gates.py` carries `tier: security-critical` in the manifest; a digest mismatch on it refuses dispatch under the same audited-override flow as the shell security-critical set. *(The dispatch runner is Tessera-owned per the seam §9 decision — it is Tessera-side code outside the protocol manifest, so its integrity coverage is Tessera's, not this spec's; the protocol emits no runner entrypoint.)*
**Eligibility shape [SR-16]:** **operator-only** — security-critical enforcement code fails the bounded-blast-radius criterion regardless of the sixth criterion. **Test:** `tests/test_sdk_gates.py`.

### R-8 (IC-6) — native worktree routing

**Change:** verify the native flag name (`--worktree`/`-w`) and its minimum Claude Code version against official docs (do **not** assume `v2.1.49`). Replace hand-rolled worktree creation/claim in the wrappers with the native mechanism where it covers the case; retain the sentinel/claim dance only where native does not cover it — notably the cross-mode `loop_in_flight`/`goal_in_flight` combined-concurrency accounting in the state file. Document each retained case inline.

**Acceptance criteria.** AC-8-1: a loop/goal dispatch routes into a worktree via the native mechanism (no hand-rolled `git worktree add` where native applies). AC-8-2: cross-mode combined-concurrency accounting still holds under `flock` on the state file (the case native does not cover). AC-8-3: each retained hand-rolled path carries an inline comment stating why native does not cover it. AC-8-4: golden re-baselined for wrapper changes (freeze-exception).
**Eligibility shape:** operator-only (native-mechanism behavior is version-sensitive and not fully test-isolable). **Test:** `tests/test_installer.py` wrapper-shape assertions + a manual verification note in the changelog.

### R-9 — the IC gate + release identity [SR-04 extended]

**Change:** add `lib/ic_checks.py` verifying IC-1..IC-7 are all satisfied, and make the installer **refuse** to write `gate_substrate: "sdk-callable"` unless every self-check passes. The seam `protocol-compatibility` job asserts this checklist. **Release identity:** on Milestone-B completion, bump `PROTOCOL_VERSION` → `"2.1.0"`, update the protocol's conformance note to mark the SDK substrate operative, and write the `2.0.0 → 2.1.0` changelog entry — the 2.0.0 conformance note reserves the substrate for a subsequent 2.x release, so Milestone B never ships under 2.0.0.

**Acceptance criteria.** AC-9-1: with any IC self-check failing, an attempt to install with `gate_substrate: "sdk-callable"` is refused loudly and the state file retains `"shell"`. AC-9-2: with all IC self-checks passing, `"sdk-callable"` is written. AC-9-3: the checklist is exposed in a form the CI `protocol-compatibility` job can assert. AC-9-4: a runtime-floor startup check logs the detected Claude Code version and warns loudly below the seam `binds` floor (≥ 2.1.210 for fail-closed `PreToolUse` timeout; confirm the exact floor per the seam's own TODO). AC-9-5 [SR-04]: `PROTOCOL_VERSION` reads `"2.1.0"`, the conformance note marks the substrate operative, and the changelog entry exists.
**Eligibility shape:** operator-only (gates a security-critical state transition and a release identity). **Test:** `tests/test_ic_gate.py`.

---

## Task-decomposition guidance (for `spec-decompose`)

Milestone A tasks R-0..R-6 are independently landable; sequence R-0 first (version identity), then R-1..R-6 in any order. Milestone B is gated on Milestone A being green (the runner-ownership decision is already recorded in seam §9: Tessera-owned): R-7 → R-8 → R-9, with R-9 last (it depends on R-1..R-8 self-checks existing and carries the 2.1.0 bump). Golden re-baselines occur only where `build_plan` output actually changes — R-4 and R-8 definitely, R-7 for the new emission, R-6 only-if-diff; R-1/R-5 are `apply()`-time artifacts outside the golden surface [SR-07]. Every re-baseline carries a `docs/changelog.md` freeze-exception line.

# Changelog — Bootstrap Protocol implementation

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

### Flagged to the owner (not changed)

1. **`judge_model` vs `evaluator_model`:** the Companion's table says the
   goal-supervised judge is "configurable in `.claude/goal-config.md` via
   `evaluator_model`", but the emitted key is `judge_model` (value `haiku`
   matches). Renaming an operator-facing config key is a golden +
   config-surface change not enumerated in the spec — needs an owner call
   (rename the emitted key, or correct the Companion prose).
2. **Pre-existing `auto.sh` bug (not introduced here, not fixed):** when
   `auto.sh` refuses to start because another run's `.run-active` exists,
   its EXIT trap still runs `rm -f "$RUN"` unguarded — deleting the
   *active* run's sentinel. The per-task wrappers guard this with
   `CLAIMED=1`; `auto.sh` does not. The new halt checks were deliberately
   placed *before* the trap so they don't trigger it, but the underlying
   path remains. Recommend fixing under its own freeze-exception.

### Migration note (operators)

Operators who never opt into the SDK substrate see **no behavioral change**
beyond: (1) the new `gate_substrate: "shell"` field (plus a one-time
`.bootstrap-state.json.pre-2.0.0` backup when upgrading a 1.x state file);
(2) the three autonomous wrappers additionally honoring the root sentinels
(inert unless you create `/.halt` or `/.halt-hard`); (3) for
autonomous-mode installs only, the managed root-`.gitignore` block keeping
those sentinels uncommittable. The shell gate suite is unchanged and
remains fully operative; fail-loud-on-empty-commands holds.

### Milestone B (reserved)

IC-5 (SDK `PreToolUse` callables per seam §9, Tessera-owned runner,
module-only emission), IC-6 (native worktree routing, flag/version to be
verified against official docs), `lib/ic_checks.py`, the runtime-floor
startup check (seam binds ≥ v2.1.210 for fail-closed PreToolUse timeout —
confirm the exact floor per the seam's own TODO), and the
`PROTOCOL_VERSION` → `"2.1.0"` bump land only after Milestone A review and
owner approval, and are recorded here as `2.0.0 → 2.1.0` when they do.

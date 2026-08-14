# Handoff prompt — LIT r2 adoption fold (Claude Code session, full repo context)

Copy everything below the line into a Claude Code session opened at the root of the
Project-Bootstrap-Protocol repo. Attach (or place in the repo)
`Bootstrap-Protocol-Improvement-Proposal-LIT-2026-08-r2.md`.

---

## Role

You are the maintainer session executing an adoption fold of the LIT r2 proposal into
the Bootstrap Protocol. You have what the review and drafting sessions did not: the
full tree — installer, emitted templates, tests, changelog, backlog. Their document is
the input; the tree is the authority. If any claim in the proposal does not match the
live tree, stop and report the mismatch — do not force the edit.

**Process ruling (do not re-litigate):** this is a **doc fold with a small
emitted-template component**, executed under the repo's changelog-first fold
discipline (v2.3.0 / v2.4.0 / v2.7.0 precedent). It is NOT a product feature: do not
route it through the emitted `/spec-decompose` → loop-mode machinery, which classifies
codebase tasks, not PRD amendments. Plan it as per-item slices, approve-gated, in the
dependency order the proposal states.

## Inputs

- `Bootstrap-Protocol-Improvement-Proposal-LIT-2026-08-r2.md` — ten items
  (LIT-01..10) with adversarial-review resolutions PAR-01..12 already folded, six
  upheld rejections, and an r1→r2 delta table. Nine items are additive doc/steering
  text; **LIT-07 is the one behavioral change** (priming redaction + binding-comment
  contract amendment + migration step).
- The working PRD (filename `Bootstrap-Protocol-v2-8-0.md`, header **Version 2.7.4**
  as of 2026-08-11). The proposal names its targets against 2.7.4.

## Step 0 — Detect, don't assume (before any edit)

1. Read `PROTOCOL_VERSION` and the PRD header. **If the version has moved past
   2.7.4**, re-verify every "Affects" claim in the proposal against the live text
   before editing; rebase or flag anything that drifted. Do not silently apply stale
   section references.
2. Map the repo's fold workflow: `docs/changelog.md` convention, backlog item format,
   PR discipline, `tests/test_installer.py` version-surface assertions (PRD header,
   Companion mirror line, both README lines), content-determinism/digest tests, and
   where emitted templates live (wrapper skeletons, `loop-config.md`/`goal-config.md`
   comment blocks, `tools.md`, skill bodies, assumption-ledger seed).
3. Confirm the G-6 rule applies: **amend in place, Version bump, no new
   `v2-8-0` file** unless the changelog explicitly records a re-issue decision.

## Step 1 — Owner decisions (ask before planning; approve / edit / start over)

Two decisions are deliberately open in the proposal. Ask them first, one at a time:

1. **Tier 3 (LIT-06 golden harness → LIT-02 consolidation):** adopt in this fold, or
   record in the Proposed-revisions appendix as trigger-gated recipes (GR2 pattern)?
   Cost and trigger conditions are stated in the items.
2. **LIT-07:** include in this fold, or defer one cycle? It is the only item with a
   migration step (existing operator-completed wrappers must be edited to apply the
   priming filter) and the only one amending the B-1 binding comment contract.

Then confirm version treatment: **one MINOR fold, changelog-first** (behavior change
is still MINOR per the v2.7.0 precedent).

## Step 2 — Fold plan (show, then approve / edit / start over)

Produce a per-item plan in this order: Tier-1 batch (LIT-01, -04, -05, -10) →
LIT-03 → LIT-08 → LIT-09 → LIT-07 (its own slice, if adopted) → LIT-06 → LIT-02 (if
adopted). For **each** slice name:

- PRD sections edited (quote the anchor line you will edit under).
- Emitted templates / installer code touched, if any — expected for at least:
  `tools.md` template (LIT-04/05), calibration-review skill body (LIT-09),
  mode-selection entry template (LIT-08), assumption-ledger seed rows (LIT-01,
  LIT-07), wrapper-skeleton binding comments + config comment blocks (LIT-07),
  Phase 10 checklist / consolidation skill (LIT-02), golden-set scaffolding (LIT-06).
- Tests touched: determinism/digest re-baselines for changed emissions;
  `test_installer.py` version surfaces; any golden emitted-text assertions.
- Changelog entry text (drafted now — it is written **first** at implementation).
- Tag every PRD edit inline `[LIT-nn]` in the house style.

## Step 3 — Implement, changelog-first

1. Write the `docs/changelog.md` entry and the PRD release-header block first.
2. Apply PRD edits per slice; then emitted templates; then tests.
3. **LIT-07 specifics** (if adopted): (a) redact `loop_max_iterations` from the
   Phase 9.5 step-3 and Phase 9.6 priming enumerations; (b) add the **fifth**
   binding-comment-contract item (operator-completed loop filters the field from the
   primed slice); (c) insert the reworded priming sentence exactly as drafted —
   *"Don't ration or count iterations; the harness manages all budgets and will end
   the loop when appropriate."* — do not restore the r1 wording; (d) add the
   deliberate-absence comment block (W-1 pattern) to the `loop-config.md` and
   `goal-config.md` emissions; (e) add the migration note to the Companion's
   Migration notes and the changelog: **unedited legacy installs keep the old
   priming behavior** — the doc must say so; (f) seed the Assumption-Ledger row.
4. Bump `PROTOCOL_VERSION` and all four version surfaces together.

## Guardrails (hard)

- Touch nothing in: seam contract / `binds`, gate predicates, the `exit_reason` enum,
  the state schema, the task-definition schema (LIT-07 filters the primed *slice*;
  the field stays in the schema and the task file).
- Release criterion inherited from 2.7.0: diff the emitted artifacts against the
  previous release; for the gates, the **"previously denied, now allowed" set must be
  empty** — this fold should not move a single gate verdict. If it does, stop.
- Open proposals (B-2..B-7, GR2-03b/04/05/06/07) are untouched; note in the changelog
  that LIT-07 amends adopted-B-1 text (four → five enumerated comment items).
- Every phase-style checkpoint is **approve / edit / start over**; never batch past
  an unanswered gate. If any emitted-file edit would trip a digest guard on operator
  hand-edited files, surface it instead of overwriting.

## Output contract

End with: (1) the changelog entry as landed; (2) per-item table — LIT id → files
touched → tests re-baselined; (3) the list of items recorded-not-adopted (with
appendix location) if the owner deferred any; (4) the LIT-07 migration note verbatim,
if adopted; (5) anything from the proposal that failed the Step-0 tree check, with
what would settle it.

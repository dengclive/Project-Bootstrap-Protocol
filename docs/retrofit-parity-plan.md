# Retrofit → Bootstrap 2.4.0 parity — assessment & upgrade plan

**Status:** proposal, 2026-07-21 (`main @ 3c0a2de`). Investigated across the
retrofit anatomy, the 2.x feature surface, and the retrofit docs. Nothing here
is started.

---

## 1. Assessment (the direct answer)

The question was: *does the Retrofit PRD + implementation badly need updating like
the Bootstrap Protocol PRD did, or are the 2.0→2.4 implementations readily
available to retrofit?* Two-part answer:

### 1a. Retrofit **docs/PRD**: badly stale — worse than the Bootstrap doc was. **(Neglect.)**
- `RETROFIT.md` (the de-facto Retrofit PRD — there is no separate PRD),
  `RETROFIT-COMPANION.md`, and `RETROFIT-GAP-ANALYSIS.md` have been **frozen since
  2026-05-19** (PR #1). Every greenfield doc has been re-cut since (v2-0-0 →
  v2-2-0 → v2-4-0 + the seam).
- They declare **"v1.6.2 — companion to `BOOTSTRAP.md` v1.9.0"** (`RETROFIT.md:3`)
  and contain **zero** mentions of any 2.x concept — SDK substrate, usage-limit
  coping, GR2/TEL, assumption ledger, trajectory retention (grep count 0 for each).
- **Dangling references:** they cite `BOOTSTRAP.md` / `BOOTSTRAP-COMPANION.md`
  (renamed out of existence — only `Bootstrap-Protocol-v2-*.md` ship now).
  **Replace ALL of them: 8 lines in `RETROFIT.md` + 17 in `RETROFIT-COMPANION.md`
  match `BOOTSTRAP(-COMPANION)?\.md`** (scope the re-cut to both files, not just
  RETROFIT.md); the sharpest is `R8.D:1424`, which tells the
  executor to *read nine AI actions directly from `BOOTSTRAP.md`* — a file that no
  longer exists.
- `RETROFIT-GAP-ANALYSIS.md` is itself a historical artifact (baselined v1.5.1 vs
  v1.9.0; its "build the retrofit installer" step was already done by PR #1).

### 1b. Retrofit **code**: largely current — a mix of *intentional exclusion* and a *few real gaps*.
The code seam is disciplined and **not** running stale code: retrofit shares the
greenfield code and mutates output only through the `mode == "retrofit"` overlay
(`installer.py:218/684`, `templates.py:2146`), which writes
`bootstrap_protocol_version: 2.4.0` + `gate_substrate: "shell"` into retrofit
state **today**.

- **Reaches retrofit through the shared overlay** (so "readily available" — yes),
  in three distinct gating classes — do NOT flatten them to "opt-in-gated":
  - **Unconditional** (emitted on every retrofit install): GR2-03a
    `assumption-ledger.md` (`installer.py:120-125`) and GR2-01
    `progress-template.md` (`installer.py:189-195`).
  - **cfg-flag-gated:** the TEL-01 `telemetry.md` doc, on `telemetry_export_enabled`
    (`installer.py:126-128`); **size-gated:** the worktree-budget doc, on
    `codebase_size_gb >= 1` (`installer.py:359`).
  - **`*_opted_in` + scaffold-but-defer (inert until brownfield milestone, OD-4):**
    ONLY the autonomous `loop.sh`/`goal-loop.sh`/`auto.sh` wrappers
    (`installer.py:355-388`), which is where the **2.2.0 usage-limit coping** and
    **GR2-02 trajectory retention** ride. `--worktree` routing rides these same
    wrappers.
  All ride the *shared* greenfield template functions verbatim (retrofit does not
  fork them).
- **Intentionally EXCLUDED — contract-backed, NOT gaps:** the **SDK gate
  substrate** — retrofit is "the one path that drops `gates.py`" (seam §7.2 /
  check-8 line 236/312; refused at `defaults.py:244`); and **Tessera dispatch**
  (seam §3.2, IG-10 / NG12). Retrofit is shell-era `1.6.2` on purpose.
- **Genuine in-lane gaps — neglect within the retrofit lane:** TEL-01
  `telemetry_export_enabled` **state field is not written** by
  `_write_retrofit_state` (retrofit emits `telemetry.md` but no matching state
  field — backlog **C-2**); plus tracked items C-1 (GR2-03a surfacing, both
  tracks), D-7 (assumption-ledger drift row), G-F1 (version-mismatch check),
  F-1 (test-gate grandfather clause).

### 1c. Bottom line
The 2.4.0 **code is readily available** to retrofit for everything meant to reach
it; the retrofit track is not behind on code it's supposed to have. What *badly
needs updating* is the retrofit **documentation** (a full re-cut), plus a small,
already-tracked set of in-lane code gaps. **Parity is mostly a docs job +
targeted gap-closure — not a code rewrite, and explicitly NOT folding retrofit
into the SDK/Tessera surface** (the seam forbids that).

---

## 2. What "parity" means here (scope)

**In scope**
- Re-cut the three retrofit docs to the 2.4.0 era; kill the dangling
  `BOOTSTRAP.md` references; document what retrofit does / does not get from 2.x.
- Close the tracked in-lane code gaps (C-2 first).
- Decide the `RETROFIT_PROTOCOL_VERSION` bump.

**Out of scope (by design — do NOT do)**
- An SDK gate substrate for retrofit (contract carve-out; retrofit stays shell).
- Putting retrofit into Tessera's dispatch surface (seam §3.2 IG-10).
- Editing the frozen greenfield core (C1/D2/OD-1).

"Parity" therefore means **doc-era parity + in-lane feature-completeness**, not
identical output — retrofit's *separateness* is intentional and contract-backed.

---

## 3. Binding constraints (must hold throughout)

From `project_retrofit_installer.md` (PR #1 invariants) and the seam:
- **C1** — retrofit changes only via the overlay / `_write_retrofit_state`;
  `_write_state` stays AST-byte-identical. **D2** — greenfield golden 6/6 unchanged
  (the tripwire; `tests/test_greenfield_golden.py`). **OD-1** — only 4 permitted
  AST change-points in existing greenfield functions.
- **B5** state shape (`*_enabled`/`*_in_flight` top-level; `*_opted_in`/
  `brownfield_milestones` nested). **T2** — every retrofit-hook error path falls
  through to ENFORCE (14 locked cases). **OD-4** — scaffold-but-defer (never enable
  an autonomous mode at retrofit time). **R0.8** gate.
- **Golden safety confirmed for the *doc* work:** `lib/templates.py` does **not**
  reference `BOOTSTRAP.md` — the dangling refs live only in the root docs, so the
  Phase-1 doc re-cut does **not** touch emitted bytes / goldens. (Verify any
  byte-identity test on the retrofit docs themselves and update its baseline
  deliberately if one exists.)
- **BUT the version number is NOT doc-only:** `RETROFIT_PROTOCOL_VERSION`
  (`installer.py:37`) is a code constant written into the emitted
  `.retrofit-state.json` (`installer.py:992`) and hard-asserted by three tests
  (`test_ic_gate.py:222` AC-9-5, `test_installer.py:1141` AC-A0-1,
  `test_retrofit.py:902` check 8.4). Bumping it is a **code** change that alters
  retrofit-emitted bytes and those tests — it belongs in Phase 2 (with C-2), never
  in the Phase-1 doc re-cut.

---

## 4. Plan (phased)

### Phase 0 — Owner decisions (before any work)
1. **Version bump — and what earns it.** Under RETROFIT's own semver precedent, a
   doc re-cut / companion re-target **alone is a PATCH** (v1.5.1 was a catch-up
   patch, v1.6.2 a reference re-anchor patch; `RETROFIT.md:42` says a minor needs a
   behavioral change, "not a reference fix"). The **new state field C-2 is what
   earns a MINOR** (additive field → minor per the scheme). So: recommend
   **`1.6.2 → 1.7.0`, earned by C-2 and landing in Phase 2 with it** — do NOT
   attribute the minor to the doc re-cut (a patch on its own), and do NOT treat
   C-2 as an escalator "past" a minor (additive is exactly a minor, never a major).
   Because the version is a code constant with pinning tests (see §3), the bump is
   a Phase-2 **code** change, not a doc-header edit. *(Ignore the old
   `RETROFIT-GAP-ANALYSIS.md §5` minor-vs-major question — it was already resolved
   by shipping v1.6.0; it is a different decision.)*
2. **Confirm retrofit stays shell-era permanently** (recommended — it's
   contract-backed). Record the decision in the re-cut so it isn't re-litigated.
3. **Retire `RETROFIT-GAP-ANALYSIS.md`?** Recommend yes — replace with a short
   pointer to `docs/deferred-backlog.md` + this plan (it's a stale historical doc).

### Phase 1 — Retrofit doc re-cut (the main neglect item; highest value) — a PATCH
- Re-cut `RETROFIT.md` + `RETROFIT-COMPANION.md` to companion
  `Bootstrap-Protocol-v2-4-0.md` / `-Companion-v2-4-0.md`:
  - Replace **all** `BOOTSTRAP.md` / `BOOTSTRAP-COMPANION.md` refs across BOTH docs
    (§1a: 8 lines in RETROFIT.md + 17 in COMPANION) with the v2-4-0 names; fix the
    `R8.D:1424` "read 9 AI actions from BOOTSTRAP.md" carve-out to point at the real
    section in the current doc.
  - Add a **"2.x delta for the retrofit track"** section stating the §1b gating
    classes precisely: SDK substrate excluded (shell-era, seam carve-out);
    **GR2-01 / GR2-03a emitted unconditionally**; `telemetry.md` **cfg-flag-gated**;
    worktree-budget **size-gated**; **usage-limit coping + GR2-02 trajectory +
    `--worktree` routing ride the autonomous wrappers under `*_opted_in` +
    scaffold-defer**; TEL-01 doc emitted, state field pending (C-2). (Do NOT flatten
    these to "opt-in-gated" — that was the assessment error this review corrected.)
- Retire/replace `RETROFIT-GAP-ANALYSIS.md` per Phase 0.3.
- **Version stays `1.6.2` in this phase** — the bump is code (Phase 2), not a doc edit.
- **No emitted-byte / golden impact** — root docs only; `templates.py` has no
  `BOOTSTRAP.md` ref, and the version constant is untouched here.

### Phase 2 — Close in-lane code gaps (respecting C1/B5/T2/OD-4)
- **C-2 + version bump (priority, bundled — together they earn the minor)** —
  extend `_write_retrofit_state` (the C1 sibling, **NOT** `_write_state`) with
  `telemetry_export_enabled`, mirroring `installer.py:891`; **and** bump
  `RETROFIT_PROTOCOL_VERSION` `installer.py:37` → `1.7.0`. Both change the emitted
  `.retrofit-state.json`, so in the SAME change update the three version-pinning
  tests (`test_ic_gate.py:222` AC-9-5, `test_installer.py:1141` AC-A0-1,
  `test_retrofit.py:902` check 8.4 → `1.7.0`), extend `test_retrofit.py` for the new
  field, and set the RETROFIT doc headers to 1.7.0. Closes the clearest half-folded
  2.4.0 feature.
- Then, as capacity allows: **C-1** GR2-03a surfacing (both tracks), **D-7**
  assumption-ledger drift row when `hooks.drift_detector:false`, **G-F1** startup
  `bootstrap_protocol_version` mismatch check, **F-1** test-gate grandfather clause.
- Each: golden 6/6 must stay green; retrofit-only mutation via the overlay.

### Phase 3 — Test coverage / hardening (from the backlog)
- **E-2 cross-mode regression matrix** — retrofit-install fixture A, then run the
  greenfield suite against fixture B in-process; proves no global-state leakage
  (directly relevant to a growing retrofit lane). Plus **E-1** retrofit E2E CLI
  smoke and **E-3** `tests/smoke/` layout.
- **G-A4** mirror-assertion that the parallel retrofit templates
  (`_retrofit_claude_md`/implementer/reviewer) byte-mirror greenfield in fixed
  ranges; **G-B3** sort `legacy_allowlist` before emit; **G-A5** ledger counter.

### Verification (end-to-end)
- **Greenfield golden** `tests/test_greenfield_golden.py` **6/6 unchanged after
  every phase** (C1/D2) — retrofit work never perturbs greenfield goldens.
- **Retrofit-emitted state DOES change in Phase 2** (not Phase 1): the
  `retrofit_protocol_version` field → 1.7.0 and the new `telemetry_export_enabled`
  field. `bin/run-tests` is green **only after** updating the three version-pinning
  tests (AC-9-5, AC-A0-1, retrofit 8.4) and extending `test_retrofit.py` — the
  version bump falsifies those `"1.6.2"` literals until they are updated.
- **Phase 1 (docs)** touches no test and has no emitted-byte impact.
- e2e retrofit install idempotent; `--ic-checks` unaffected (retrofit no-op).
- Frozen-file diffs: none from Phase 1 (root docs); any deliberate baseline update
  recorded in `docs/changelog.md`.

---

## 5. Effort shape & sequencing

| Phase | Nature | Value | Risk |
|---|---|---|---|
| 0 | Owner decisions | unblocks the rest | none |
| 1 | Doc re-cut (root docs) | **highest** — this is what "badly needs updating" | low (no golden impact) |
| 2 | In-lane code gaps (C-2 first) | medium | low-med (C1/golden discipline) |
| 3 | Test coverage / hardening | medium (durability) | low |

The neglect the question is really about lives almost entirely in **Phase 1**.
Phases 2–3 are the already-tracked `docs/deferred-backlog.md` retrofit items
(C-2, C-1, D-7, E-1/2/3, F-1, G-*), pulled together here under one banner.

## 6. Cross-references
- Backlog: `docs/deferred-backlog.md` (C-1/C-2, D-1/D-7, E-1..3, F-1, G-A4/A5/B1/B3/D1/F1/F2).
- Invariants: memory `project_retrofit_installer.md` (C1/B5/T2/OD-1/OD-4/R0.8/D2).
- Contract carve-outs: `SEAM-CONTRACT-v2-0-0.md` §3.2 (IG-10), §7.2/§8.2 check-8 (gates.py drop).
- Anchors: `RETROFIT.md:3,5,1143,1162,1424`; `installer.py:37,218,291,313,891,903,991`;
  `templates.py:2019,2039,2146`; `defaults.py:214,244`.

# Post-merge follow-ups — Session Checkpoint

**Date:** 2026-05-21 (created) / 2026-05-22 (self-apply) / **2026-05-27 (refreshed)**
**Branch:** `fix/self-apply-sa1-sa2` (1 commit ahead of `main`, pushed)
**Main last commit:** `332590e` (synced with `origin/main`; PR #1 merged at `2bc915a`, PR #2 merged at `ce21d60`)
**Status:** PR #2 **MERGED**. PR #3 **OPEN** (SA1+SA2 fixes). 443/443 tests green on the fix branch. SA3 still pending (doc-only).

---

## TL;DR for next session

```bash
cd /home/dengc/Documents/Projects/Project-Bootstrap-Protocol
git checkout fix/self-apply-sa1-sa2
for t in tests/test_*.py; do python "$t"; done   # expect 6/118/66/253 = 443
gh pr view 3 --json state,reviewDecision         # check PR #3 status
git log --oneline main..HEAD                      # expect 1 commit: a8a7db7
```

If those match, state is intact. Pick up from "Active queue" or "If PR #3 needs revisions" below.

**Note on this file's history:** earlier revisions described PR #2 as open and named `interactive-walkthrough-test` as the working branch. Both are now stale — PR #2 merged, and the current working branch is `fix/self-apply-sa1-sa2`. This refresh supersedes those instructions.

---

## What landed since the 2026-05-19 checkpoint

| Date | Event | Commit / Ref |
|---|---|---|
| 2026-05-20 | Round-2 review applied (R8.G/H/I scaffolding + validators) | `db694c4` |
| 2026-05-20 | Round-3 review applied (spec-decompose, wrapper guards, r08 gate, debt sort) | `3c039a6` |
| 2026-05-20 | PR #1 merged | `2bc915a` |
| 2026-05-21 | PR #2 opened (interactive walkthrough test + hybrid_review_date prompt) | `b38769f` |
| 2026-05-22 | Self-apply step 1 against a `/tmp` clone — end-to-end retrofit validation on a real codebase | — |
| 2026-05-22 | Checkpoint pushed to origin/main | `6d278c0` |
| (≤2026-05-27) | **PR #2 merged** | `ce21d60` |
| (≤2026-05-27) | Checkpoint update: self-apply findings + SA1/SA2/SA3 recorded | `332590e` |
| **2026-05-27** | **PR #3 opened — SA1 + SA2 fixes** | `a8a7db7` |

PR #1 went through three adversarial review rounds (scoped C2 pre-PR, Round-2, Round-3): 10 commits, all rounds folded in.

---

## PR #3 OPEN — SA1 + SA2 self-apply fixes

**URL:** https://github.com/dengclive/Project-Bootstrap-Protocol/pull/3
**Branch:** `fix/self-apply-sa1-sa2` (`a8a7db7`, pushed, 1 commit ahead of `main`)
**Scope:** `lib/inventory_scan.py`, `lib/retrofit_interview.py`, `tests/test_retrofit.py` (3 files, +162/-5)

**SA1 — extension-less shebang scripts now count as source.**
`inventory_scan.py` keyed source detection on file suffix only, so `bin/` scripts with `#!/usr/bin/env python3` and no `.py` counted as 0 (self-apply showed "bin: 0 source files"). Added a shared `_source_ext()` predicate + `_shebang_ext()` (reads only first 256 bytes); wired into `scan_structure`, `scan_languages` (buckets under `.py`/`.sh`/…), `scan_testing`. On this repo `bin/` goes 0 → 3.

**SA2 — hybrid PM proposal no longer dead-ends accept-all-defaults.**
When the heuristic proposes `pm_strategy: hybrid`, `run_interactive` now seeds `hybrid_review_date = today + 90 days` (the "90-day cutover review" the rationale cites). Placed in `run_interactive`, **NOT** `default_answers`, so `render_interview` (analyze path) stays a clock-free deterministic function of the inventory — preserving the "identical inventory ⇒ identical interview file" contract. Operator-*switched* hybrid (overriding a non-hybrid proposal at the prompt) is intentionally NOT auto-dated, preserving the loud-fail safety net (test 17.24).

**Tests:** +8 Section-18 checks (18.1–18.8). `test_retrofit` 245 → 253; suite total 443. SA1 includes a non-shebang control file; SA2 fixture is guarded by an 18.5 "proposes hybrid" assertion before exercising the flow.

**Test gauntlet on PR #3:**
| Suite | Count |
|---|---|
| `tests/test_greenfield_golden.py` | 6 |
| `tests/test_installer.py` | 118 (frozen, zero-diff vs main) |
| `tests/test_interview.py` | 66 |
| `tests/test_retrofit.py` | 253 (was 245 on main; +8 §18) |
| **Total** | **443** |

Frozen files zero-diff vs main on all 5 (`lib/minyaml.py`, `bin/bootstrap-install`, `tests/test_installer.py`, `bootstrap.config.yaml`, `BOOTSTRAP.md`). Determinism (Section 2) + greenfield golden (D2 byte-identity 6/6) green.

---

## Self-apply step 1 — 2026-05-22 (history)

Cloned the repo to `/tmp/retrofit-self-apply` and ran the full retrofit flow end-to-end; working repo untouched throughout.

**What worked:** inventory scan (10 files), heuristics (archetype "library", contested vs "cli"), interactive walkthrough through all prompts (PR #2 `hybrid_review_date` fired when needed), 77-file install plan with correct B5 state shape, `spec-gate-commit` retrofit_active exemption on `.claude/`-only commit, rollout-week warn-only at week 1, `ROLLOUT_WEEK` runtime-read (D5), week-4 empty `commands.test` loud-TODO block (OD-3), R7 master-switch exemption stops firing when `retrofit_active: false`.

**Findings surfaced → now resolved/triaged:**
1. **SA1** — inventory misses extension-less `bin/` Python scripts. → **FIXED on PR #3.**
2. **SA2** — accept-all-defaults fails when heuristic proposes `hybrid` (no date default). → **FIXED on PR #3.**
3. **SA3** — post-R7 `.claude/` commits are spec-gated (working as designed); should be surfaced in R7 handoff text. → **STILL PENDING (doc-only).**

**Not validated by self-apply:** whether the produced `.claude/` actually guides useful AI behavior in a real dev session (empirical "Step 3", operator judgment).

---

## If PR #3 needs revisions

No review yet. If feedback comes, the PR #1 pattern applies: read the review, verify findings against actual code (some dissolve), triage by severity, fix blockers/high/medium in-scope, defer advisory with rationale. Standing lesson: re-read each fix's own diff before committing (C2 regressed on Round-1 because that step was skipped).

---

## Active queue (from `~/.claude/projects/.../memory/project_post_retrofit_tasks.md`)

Item #1 (interactive walkthrough) **MERGED** via PR #2. SA1/SA2 **fixed on PR #3**. Remaining:

- **SA3** — R7 handoff text: surface that post-`retrofit_active=false` `.claude/` commits are spec-gated like normal source (working as designed per spec; doc note in `_retrofit_claude_md`'s R7 completion section).
2. **E2E CLI smoke** — shell script invoking the installer `--dry-run` against real greenfield + retrofit example projects. Asserts apply summary non-empty + exit 0. Catches argparse-layer breakage the unit tests bypass.
3. **Cross-mode regression matrix** — install retrofit-mode onto fixture A, then run the greenfield 118-check suite against fixture B in the same process. Proves no global-state leakage.
4. **`bin/run-tests` / `make test`** — wrapper replacing the manual `for t in tests/test_*.py; do python "$t"; done` loop.
5. **CI configuration** — none exists. GitHub Actions workflow running the script-style suites + smoke layer on PR.
6. **`tests/smoke/` layout** — fixture repos + golden-tree diff against checked-in expected output.

**Lower-priority (from 2026-05-19 checkpoint):**
- test-gate grandfather clause (per-module exemption from `inventory/testing.md` no-test list)
- Widen `inventory_scan.py` pyproject regex (misses bare `fastapi` w/o version)
- Refactor `propose_commands` to take a root path instead of `os.getcwd()`

**Deferred from Round-3 adversarial review (v1.6.3 cleanup):**
A4 parallel templates docstring/test · A5 mode-selection drift-prone-area enforcement (R7 handoff) · B1 `--force` per-file scope · B3 legacy_allowlist sort-before-emit · D1 T2 AD class expansion · D2 FS5 disambig comment · F1 `bootstrap_protocol_version` runtime reader · F2 RETROFIT-COMPANION migration-path paragraph · G2 validator/B5 error-message coupling

**Deferred from Round-2 review (still defensible post-Round-3):**
4.2 `r08_committed` writer-side semantic · 5.2 Protocol-version lifecycle · 3.1 jq-garbage discrimination · 3.3 Two-seam true independence · 2.2 TEMPLATES dict cardinality arithmetic

---

## Architectural invariants — still in force

These bind ALL future `mode: retrofit` work on `main`. Breaking them silently re-opens failure modes the three review rounds closed.

- **C1:** Do NOT modify `_write_state` in `lib/installer.py`. Use sibling `_write_retrofit_state` + dispatch by `cfg["mode"]`. `_write_state` AST-byte-identical.
- **OD-1:** Exactly 4 permitted AST changes outside new definitions for `mode: retrofit` extensions: (a) `TEMPLATES["hook"] = _hook_dispatch`; (b) `build_plan` retrofit branch; (c) `apply_plan` state-write dispatch; (d) `resolve_config` retrofit block. Extending these is fine; creating new modification surfaces inside greenfield functions invites fragility.
- **B5:** `*_enabled` and `*_in_flight` are TOP-LEVEL in `.retrofit-state.json`; `*_opted_in` and `brownfield_milestones` are NESTED in cfg under `retrofit.autonomous_modes`. Never conflate. T1 tests (29 assertions) + Round-2 structural validator pin both directions.
- **T2:** Every error/missing-file/parse-failure path in `_hook_body_retrofit` must fall through to ENFORCE. 14 cases locked in §7 (AF1-AF5, FS1-FS7, FS7b, AD1).
- **OD-4 (scaffold-but-defer):** Wizard never enables autonomous modes at retrofit time. Round-3 added a runtime guard in each emitted wrapper (loop/goal/auto.sh) refusing to run unless `*_enabled: true` in state — covers never-enabled AND opt-out-orphan cases.
- **R0.8 gate:** `resolve_config` rejects retrofit cfg unless `r.r08_committed: true` OR `r.skip_decisions.r08: true`.
- **D2 byte-identity:** `tests/test_greenfield_golden.py` must stay 6/6.

Wrapper transform contract: `_retrofit_wrapper_transform` (in `lib/installer.py`) MUST do both (1) swap `.bootstrap-state.json` → `.retrofit-state.json` and (2) insert `REFUSING:` guard reading state. Anchor is the `LOG="$PROJ/.claude/logs/hooks.log"` line (identical across all three wrappers).

**SA2 addendum (PR #3):** the hybrid date auto-default lives ONLY in `run_interactive` (the explicitly non-deterministic front-end), never in `default_answers`/`build_retrofit_proposal`/`render_interview`. Moving it upstream would break the "identical inventory ⇒ identical interview file" determinism contract (`lib/retrofit_interview.py` docstring lines 22–25).

---

## How to verify state on resume

```bash
cd /home/dengc/Documents/Projects/Project-Bootstrap-Protocol
git checkout fix/self-apply-sa1-sa2

# 1. Branch is 1 commit ahead of main
git log --oneline main..HEAD | wc -l   # expect 1

# 2. Last commit is the SA1+SA2 work
git log -1 --oneline                    # expect a8a7db7 Fix SA1 ... + SA2 ...

# 3. All four suites pass
for t in tests/test_*.py; do python "$t" 2>&1 | tail -1; done
# expect: 6 passed / 118 passed / 66 passed / 253 passed

# 4. Frozen files zero-diff vs main
git diff main -- lib/minyaml.py bin/bootstrap-install tests/test_installer.py bootstrap.config.yaml BOOTSTRAP.md
# (empty)

# 5. PR #3 still open
gh pr view 3 --json state,title --jq '.state + ": " + .title'

# 6. (optional) SA1 spot-check on this repo
python -c "import sys; sys.path.insert(0,'lib'); from pathlib import Path; \
from inventory_scan import scan_structure; \
print(scan_structure(Path('.'))['top_level_dirs'].get('bin'))"   # expect source_files: 3
```

---

## Local repo state

- `main`: `332590e` (synced with `origin/main`)
- `fix/self-apply-sa1-sa2`: `a8a7db7` (synced with origin; 1 commit ahead of main) — **current working branch, PR #3**
- `interactive-walkthrough-test`: `b38769f` — **MERGED via PR #2 (`ce21d60`); safe to delete (local + origin) pending operator go-ahead**
- `retrofit-installer` (old): `3c039a6` local + `origin/retrofit-installer` — **MERGED via PR #1 (`2bc915a`); safe to delete pending operator go-ahead**
- Self-apply scratch: `/tmp/retrofit-self-apply` (ephemeral, not preserved across reboots)

**Branch cleanup offered, not yet done:** `interactive-walkthrough-test` and `retrofit-installer` are both fully merged and deletable on operator go-ahead.

---

## Memory store state (`~/.claude/projects/-home-dengc-Documents-Projects-Project-Bootstrap-Protocol/memory/`)

- `MEMORY.md` — index (4 entries)
- `test_harness.md` — tests are scripts (not pytest), run with `python tests/<file>.py`
- `project_retrofit_installer.md` — PR #1 merged at `2bc915a`; architectural invariants for `mode: retrofit` work on main
- `feedback_frozen_files.md` — 5 files stayed byte-identical across PR #1; post-merge norm
- `project_post_retrofit_tasks.md` — active follow-up queue; updated 2026-05-27 (item #1 merged via PR #2; SA1/SA2 on PR #3; SA3 + items #2–#6 open)

---

## Source references

- Prior checkpoint: `.claude/sessions/2026-05-19-retrofit-installer-checkpoint.md`
- Round-2 review doc: `~/Downloads/PR1-adversarial-review.md`
- Round-3 review doc: `~/Downloads/PR1-adversarial-review-r3.md`
- Spec: `RETROFIT.md` v1.6.2, `RETROFIT-COMPANION.md` v1.6.2 (committed in `145dcc2`)
- PR #1 (merged): https://github.com/dengclive/Project-Bootstrap-Protocol/pull/1
- PR #2 (merged): https://github.com/dengclive/Project-Bootstrap-Protocol/pull/2
- PR #3 (open): https://github.com/dengclive/Project-Bootstrap-Protocol/pull/3

# Post-merge follow-ups — Session Checkpoint

**Date:** 2026-05-21
**Branch:** `interactive-walkthrough-test` (1 commit ahead of `main`)
**Main last commit:** `2bc915a` (PR #1 merged 2026-05-20)
**Status:** PR #2 open, 435/435 tests green, one follow-up complete, queue intact.

---

## TL;DR for next session

```bash
cd /home/dengc/Documents/Projects/Project-Bootstrap-Protocol
git checkout interactive-walkthrough-test
for t in tests/test_*.py; do python "$t"; done   # expect 435 passed total
gh pr view 2 --json state,reviewDecision         # check PR #2 status
git log --oneline main..HEAD                      # expect 1 commit: b38769f
```

If those four commands match, state is intact. Pick up from "Active queue" below or "If PR #2 needs revisions" below.

---

## What landed since the 2026-05-19 checkpoint

| Date | Event | Commit / Ref |
|---|---|---|
| 2026-05-20 | Round-2 review applied (R8.G/H/I scaffolding + validators) | `db694c4` |
| 2026-05-20 | Round-3 review applied (spec-decompose, wrapper guards, r08 gate, debt sort) | `3c039a6` |
| 2026-05-20 | PR #1 merged | `2bc915a` |
| 2026-05-21 | PR #2 opened (interactive walkthrough test + hybrid_review_date prompt) | `b38769f` |

PR #1 went through three adversarial review rounds: scoped C2 (pre-PR), Round-2, Round-3. Final state: 10 commits, 410/410 tests, all rounds folded in.

---

## PR #2 open — interactive walkthrough test

**URL:** https://github.com/dengclive/Project-Bootstrap-Protocol/pull/2
**Branch:** `interactive-walkthrough-test`
**Commit:** `b38769f` — "Interactive walkthrough test + hybrid_review_date prompt"
**Scope:** `lib/retrofit_interview.py` (+29 lines), `tests/test_retrofit.py` (+243 lines)

**What's in it:**
- Section 17 added to `tests/test_retrofit.py` — 25 stdin-fed checks covering the full 16-prompt interactive walkthrough.
- Bug fix surfaced by the test: `hybrid_review_date` prompt added to `run_interactive` and sourced from `ans` in `answers_to_config`. Pre-fix, picking `pm_strategy: hybrid` was a UX dead-end (Round-2 Lens-1.3 gate would reject the cfg with no path to set the date).

**Test breakdown (Section 17):**

| Checks | What |
|---|---|
| 17.1-17.5 | All-defaults walkthrough → exit 0, cfg validates, scaffold-but-defer baseline |
| 17.6-17.15 | Override walkthrough → archetype/prd_tier/tdd_policy/spec_strategy/commands land; loop+goal opt-in nested; B5 preserved |
| 17.16-17.18 | Invalid-input loop + EOF fallback — flow accepts default and continues |
| 17.19-17.20 | R8.I prereq UX seam — queue opt-in without loop/goal warned and disabled |
| 17.21-17.23 | `pm_strategy: hybrid` + valid date → exit 0, prompt fires, date lands |
| 17.24-17.25 | `pm_strategy: hybrid` + empty date → exit 2, error mentions `hybrid_review_date` + "required" |

**Test gauntlet on PR #2:**
| Suite | Count |
|---|---|
| `tests/test_greenfield_golden.py` | 6 |
| `tests/test_installer.py` | 118 (frozen, zero-diff vs main) |
| `tests/test_interview.py` | 66 |
| `tests/test_retrofit.py` | 245 (was 220 on main; +25 §17) |
| **Total** | **435** |

Frozen files zero-diff vs main on all 5 (`lib/minyaml.py`, `bin/bootstrap-install`, `tests/test_installer.py`, `bootstrap.config.yaml`, `BOOTSTRAP.md`).

---

## If PR #2 needs revisions

The PR is fresh — no review yet. If review feedback comes:
- The pattern from PR #1 review rounds applies: read the review doc, verify findings against actual code (some may dissolve), triage by severity, fix blockers + high + medium that are in-scope, defer advisory with explicit rationale.
- The standing lesson: re-read each fix's own diff before committing. C2 introduced regressions on Round-1 because that step was skipped.

---

## Active queue (from `~/.claude/projects/.../memory/project_post_retrofit_tasks.md`)

Item #1 — interactive walkthrough test — is **in progress on PR #2**. Items #2-#6 remain:

2. **E2E CLI smoke** — shell script invoking `python -m installer --dry-run` against real greenfield + retrofit example projects. Asserts apply summary non-empty + exit 0. Catches argparse-layer breakage the unit tests bypass.
3. **Cross-mode regression matrix** — install retrofit-mode onto fixture A, then run greenfield 118-check suite against fixture B in same process. Proves no global-state leakage.
4. **`bin/run-tests` / `make test`** — wrapper replacing the manual `for t in tests/test_*.py; do python "$t"; done` loop.
5. **CI configuration** — none exists. GitHub Actions workflow running the script-style suites + smoke layer on PR.
6. **`tests/smoke/` layout** — fixture repos + golden-tree diff against checked-in expected output.

**Lower-priority items still pending from the 2026-05-19 checkpoint:**
- test-gate grandfather clause (per-module exemption from `inventory/testing.md` no-test list)
- Widen `inventory_scan.py` pyproject regex (misses bare `fastapi` w/o version)
- Refactor `propose_commands` to take a root path instead of `os.getcwd()`

**Deferred from Round-3 adversarial review (v1.6.3 cleanup):**
- A4 parallel templates docstring/test
- A5 mode-selection drift-prone-area enforcement (R7 handoff)
- B1 `--force` per-file scope
- B3 legacy_allowlist sort-before-emit
- D1 T2 AD class expansion
- D2 FS5 disambig comment
- F1 `bootstrap_protocol_version` runtime reader
- F2 RETROFIT-COMPANION migration-path paragraph
- G2 validator/B5 error-message coupling

**Deferred from Round-2 review (still defensible post-Round-3):**
- 4.2 `r08_committed` writer-side semantic (cfg-side gate works now)
- 5.2 Protocol-version lifecycle
- 3.1 jq-garbage discrimination
- 3.3 Two-seam true independence
- 2.2 TEMPLATES dict cardinality arithmetic

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

---

## How to verify state on resume

```bash
cd /home/dengc/Documents/Projects/Project-Bootstrap-Protocol
git checkout interactive-walkthrough-test

# 1. Branch is correct and 1 commit ahead of main
git log --oneline main..HEAD | wc -l   # expect 1

# 2. Last commit is the interactive walkthrough work
git log -1 --oneline                    # expect b38769f Interactive walkthrough test...

# 3. All four suites pass
for t in tests/test_*.py; do python "$t" 2>&1 | tail -2; done
# expect: 6 passed / 118 passed / 66 passed / 245 passed

# 4. Frozen files zero-diff vs main
git diff main -- lib/minyaml.py bin/bootstrap-install tests/test_installer.py bootstrap.config.yaml BOOTSTRAP.md
# (empty)

# 5. PR #2 still open
gh pr view 2 --json state,title --jq '.state + ": " + .title'
```

If all five check out, you're exactly where this session ended.

---

## Local repo state

- `main`: `2bc915a` (synced with `origin/main`)
- `interactive-walkthrough-test`: `b38769f` (synced with `origin/interactive-walkthrough-test`)
- `retrofit-installer` (old, merged): `3c039a6` local; `origin/retrofit-installer` also exists. Safe to delete (work landed on main via `2bc915a`); not deleted yet pending operator go-ahead.

---

## Memory store state (`~/.claude/projects/-home-dengc-Documents-Projects-Project-Bootstrap-Protocol/memory/`)

- `MEMORY.md` — index (4 entries)
- `test_harness.md` — tests are scripts (not pytest), run with `python tests/<file>.py`
- `project_retrofit_installer.md` — PR #1 merged at `2bc915a`; architectural invariants for `mode: retrofit` work on main
- `feedback_frozen_files.md` — 5 files stayed byte-identical across PR #1; post-merge norm
- `project_post_retrofit_tasks.md` — active follow-up queue (item #1 in flight on PR #2)

---

## Source references

- Prior checkpoint: `.claude/sessions/2026-05-19-retrofit-installer-checkpoint.md`
- Round-2 review doc: `~/Downloads/PR1-adversarial-review.md`
- Round-3 review doc: `~/Downloads/PR1-adversarial-review-r3.md`
- Spec: `RETROFIT.md` v1.6.2, `RETROFIT-COMPANION.md` v1.6.2 (committed in `145dcc2`)
- PR #1 (merged): https://github.com/dengclive/Project-Bootstrap-Protocol/pull/1
- PR #2 (open): https://github.com/dengclive/Project-Bootstrap-Protocol/pull/2

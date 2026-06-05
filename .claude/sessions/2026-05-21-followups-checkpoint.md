# Post-merge follow-ups — Session Checkpoint

**Date:** 2026-05-21 (created) / 2026-05-22 (self-apply) / 2026-05-27 (refresh) / **2026-06-05 (refreshed)**
**Branch:** `doc/sa3-r7-handoff-spec-gating` (1 commit ahead of `main` after SA3 commit; checkpoint + push handled together)
**Main last commit:** `3251aa2` (PR #3 merge; synced with `origin/main`)
**Status:** PR #1, PR #2, PR #3 all **MERGED**. SA3 in flight as PR #4. 447/447 tests green on the SA3 branch. Three merged feature branches deleted (local + origin).

---

## TL;DR for next session

```bash
cd /home/dengc/Documents/Projects/Project-Bootstrap-Protocol
git checkout doc/sa3-r7-handoff-spec-gating
for t in tests/test_*.py; do python "$t"; done   # expect 6/118/66/257 = 447
gh pr view 4 --json state,reviewDecision         # check PR #4 status
git log --oneline main..HEAD                      # expect SA3 commit(s)
```

If those match, state is intact. Pick up from "Active queue" below or "If PR #4 needs revisions."

**Note on prior revisions of this file:** earlier refreshes named `interactive-walkthrough-test` then `fix/self-apply-sa1-sa2` as the working branch. Both PRs (#2, #3) are merged and both branches were deleted on 2026-06-05. The current working branch is `doc/sa3-r7-handoff-spec-gating`; PR #4 covers SA3 + this checkpoint refresh.

---

## What landed since the 2026-05-19 checkpoint

| Date | Event | Commit / Ref |
|---|---|---|
| 2026-05-20 | PR #1 merged (retrofit installer; three review rounds folded in) | `2bc915a` |
| 2026-05-21 | PR #2 opened (interactive walkthrough test + hybrid_review_date prompt) | `b38769f` |
| 2026-05-22 | Self-apply step 1 against `/tmp` clone — end-to-end retrofit validation | — |
| 2026-05-22 | Checkpoint update pushed to origin/main | `6d278c0` |
| (≤2026-05-27) | PR #2 merged | `ce21d60` |
| (≤2026-05-27) | Checkpoint update: self-apply findings + SA1/SA2/SA3 recorded | `332590e` |
| 2026-05-27 | PR #3 opened — SA1 + SA2 fixes | `a8a7db7` |
| 2026-05-27 | Checkpoint refresh joined PR #3 | `38fc024` |
| **2026-05-28** | **PR #3 merged** | `3251aa2` |
| **2026-06-05** | Three merged branches deleted (local + origin): `fix/self-apply-sa1-sa2`, `interactive-walkthrough-test`, `retrofit-installer` | — |
| **2026-06-05** | **PR #4 opened — SA3 doc note (R7 handoff spec-gating)** | (this branch) |

---

## PR #4 OPEN — SA3 R7 handoff spec-gating doc note

**Branch:** `doc/sa3-r7-handoff-spec-gating` (off `main` at `3251aa2`)
**Scope:** `lib/templates.py` (R7 completion section in `_retrofit_claude_md`), `tests/test_retrofit.py` (+4 checks 5.8a–5.8d), this checkpoint refresh

**The finding (working as designed, but the surprise was real):**
The `spec-gate-commit` hook has an affirmative `.claude/`-only commit exemption that fires **only while `retrofit_active=true`** (`lib/templates.py:1312-1325`). Once R7 flips `retrofit_active=false`, that branch goes silent and `.claude/` files rejoin the normal source population — any commit touching them must be backed by an active spec or be on the legacy allowlist. Pre-SA3 the R7 completion text in CLAUDE.md only hinted at this with a parenthetical ("no more allowlisting `.claude/` writes for the retrofit itself"), surprising operators who wanted to tweak `CLAUDE.md` casually.

**The fix:**
- Expanded `_retrofit_claude_md`'s "Retrofit completion (R7)" section into a 3-bullet list naming the consequence ("the retrofit-time exemption for `.claude/`-only commits is GONE"), enumerating the artifact classes covered (CLAUDE.md, steering docs, hooks, skills, commands), framing it honestly ("steering is not a back-door"), and pointing at the forward workflow (`/spec-new` → per-task lifecycle; trivial wording fixes can use a patch-bump spec per Phase 7.5).
- Zero behavior change. Pure text in a template. Frozen files untouched.

**Test gauntlet on PR #4:**
| Suite | Count |
|---|---|
| `tests/test_greenfield_golden.py` | 6 |
| `tests/test_installer.py` | 118 (frozen, zero-diff vs main) |
| `tests/test_interview.py` | 66 |
| `tests/test_retrofit.py` | 257 (was 253 on main; +4 §5 SA3 checks 5.8a–5.8d) |
| **Total** | **447** |

Frozen files zero-diff vs main on all 5. Determinism (Section 2) + greenfield golden (D2 byte-identity 6/6) green.

---

## Self-apply findings — final triage

The 2026-05-22 `/tmp` clone retrofit produced three real findings; all three are now resolved or in flight:

1. **SA1** — inventory missed extension-less `bin/` Python scripts. → **MERGED via PR #3 (`3251aa2`).**
2. **SA2** — accept-all-defaults dead-ended when heuristic proposed `hybrid` (no date default). → **MERGED via PR #3 (`3251aa2`).**
3. **SA3** — R7 handoff text didn't surface post-`retrofit_active=false` `.claude/` spec-gating. → **PR #4 IN FLIGHT (this branch).**

**Not validated by self-apply:** whether the produced `.claude/` actually guides useful AI behavior in a real dev session (empirical "Step 3", operator judgment).

**Engineering bar:** DONE through SA1–SA3.
**Product bar:** still operator-discretion on a real project.

---

## If PR #4 needs revisions

No review yet. Same pattern as PR #1–#3: read the review, verify findings against actual code (some dissolve), triage by severity, defer advisory with rationale. SA3 is doc-only / pure text in a template, so revision cost should be minimal; the test assertions are anchored on stable phrases (`"GONE"`, `"back-door"`, `"/spec-new"`, `"Phase 7.5"`) so wording tweaks need at most a parallel test update.

---

## Active queue (from `~/.claude/projects/.../memory/project_post_retrofit_tasks.md`)

Item #1 (interactive walkthrough) merged via PR #2. SA1/SA2 merged via PR #3. SA3 in flight via PR #4. The remaining queue:

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

**SA3 addendum (PR #4):** the post-R7 spec-gating consequence MUST be surfaced in `_retrofit_claude_md`'s R7 completion section, not hidden in a parenthetical. The honest framing ("steering is not a back-door") is the contract: any future weakening of the post-R7 gate must be a deliberate spec change, not a quiet template edit. Test anchors in §5.8a–5.8d enforce the wording's key claims (`GONE`, artifact class list, `/spec-new`, Phase 7.5, `back-door`).

---

## How to verify state on resume

```bash
cd /home/dengc/Documents/Projects/Project-Bootstrap-Protocol
git checkout doc/sa3-r7-handoff-spec-gating

# 1. Branch ahead of main
git log --oneline main..HEAD | wc -l   # expect 1+ (SA3 commit, possibly + checkpoint)

# 2. All four suites pass
for t in tests/test_*.py; do python "$t" 2>&1 | tail -1; done
# expect: 6 passed / 118 passed / 66 passed / 257 passed

# 3. Frozen files zero-diff vs main
git diff main -- lib/minyaml.py bin/bootstrap-install tests/test_installer.py bootstrap.config.yaml BOOTSTRAP.md
# (empty)

# 4. PR #4 still open
gh pr view 4 --json state,title --jq '.state + ": " + .title'

# 5. Generated CLAUDE.md contains the new SA3 wording
python -c "
import sys; sys.path.insert(0,'lib')
from templates import _retrofit_claude_md
cfg = {'retrofit': {'autonomous_modes': {}}}
md = _retrofit_claude_md(cfg)
for key in ('GONE', 'back-door', '/spec-new', 'Phase 7.5'):
    assert key in md, key
print('SA3 anchors present')
"
```

---

## Local repo state

- `main`: `3251aa2` (synced with `origin/main`; PR #3 merge commit)
- `doc/sa3-r7-handoff-spec-gating`: **current working branch, PR #4**
- All other local + origin feature branches: **deleted** (`fix/self-apply-sa1-sa2`, `interactive-walkthrough-test`, `retrofit-installer`). History preserved by their PR merge commits.
- Self-apply scratch: `/tmp/retrofit-self-apply` (ephemeral, not preserved across reboots)

---

## Memory store state (`~/.claude/projects/-home-dengc-Documents-Projects-Project-Bootstrap-Protocol/memory/`)

- `MEMORY.md` — index (4 entries)
- `test_harness.md` — tests are scripts (not pytest), run with `python tests/<file>.py`
- `project_retrofit_installer.md` — PR #1 merged at `2bc915a`; architectural invariants for `mode: retrofit` work on main
- `feedback_frozen_files.md` — 5 files stayed byte-identical across PR #1; post-merge norm
- `project_post_retrofit_tasks.md` — active follow-up queue; updated 2026-05-28 (PR #2 merged, SA1/SA2 merged via PR #3); needs a 2026-06-05 bump for SA3-in-flight on PR #4 (todo this session)

---

## Source references

- Prior checkpoint: `.claude/sessions/2026-05-19-retrofit-installer-checkpoint.md`
- Round-2 review doc: `~/Downloads/PR1-adversarial-review.md`
- Round-3 review doc: `~/Downloads/PR1-adversarial-review-r3.md`
- Spec: `RETROFIT.md` v1.6.2, `RETROFIT-COMPANION.md` v1.6.2 (committed in `145dcc2`)
- PR #1 (merged): https://github.com/dengclive/Project-Bootstrap-Protocol/pull/1
- PR #2 (merged): https://github.com/dengclive/Project-Bootstrap-Protocol/pull/2
- PR #3 (merged): https://github.com/dengclive/Project-Bootstrap-Protocol/pull/3
- PR #4 (open): https://github.com/dengclive/Project-Bootstrap-Protocol/pull/4

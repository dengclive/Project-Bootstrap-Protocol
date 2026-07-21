# Deferred backlog — unified tracking

The single index of deferred / not-yet-fixed work. It consolidates items that
were previously scattered across `docs/changelog.md` ("Review findings recorded
but NOT fixed"), the `post-retrofit-tasks` memory, the milestone memory, and
per-session checkpoints. **This document is canonical going forward** — add new
deferrals here; the source lists remain as historical record.

**Snapshot:** `main @ 3c0a2de`, 2026-07-21 (after the 2.4.0 fold + closeout:
PR #8/#9/#10 merged, PR #4 closed). None of the items below block 2.4.0.

Status legend: `open` (actionable work) · `decision` (needs an owner call before
work) · `no-action` (reviewed, judged fine as-is; listed so it isn't re-derived)
· `done` (resolved; kept for provenance).

## A. Owner decisions (no code until decided)

| ID | Item | Notes |
|---|---|---|
| A-1 | Emitted-gate fail-open posture under a total parser outage | No `jq` AND no `python3` → git-commit gates + `secrets-gate` become inert pass-throughs. Leave inert vs. fail-closed. Golden-changing, RETROFIT-contract decision. `decision` |
| A-2 | Accept-or-schedule this deferred set | Formally treat as deferred-not-forgotten, or queue clusters. `decision` |
| A-3 | Shell-parity judgment call (Milestone B) | SDK gates stricter than the 2.0.0 shell gates on edge cases; parity is a follow-up PR if wanted. `decision` |
| A-4 | Trajectory pruning | `purge_old_state_after_days` has no consumer; auto-deletion unimplemented (new destructive behavior). `decision` |

## B. Seam follow-ups (from the 2.0.0 re-cut, PR #10)

| ID | Item | Notes |
|---|---|---|
| B-1 | `SATISFIES_SEAM_VERSION` constant | §8.1 says a protocol commit declares which `seam_version`(s) it satisfies; nothing in code declares it. Bootstrap-side gap. `open` |
| B-2 | `tessera_prd` floor re-cut | Awaits the absorbing Tessera version (P-5 window). Note: re-pinning `targets_seam_version` alone greens check-0 before any runner consumes `build_hooks`. `open` (blocked on Tessera roadmap) |
| B-3 | `claude_code_json_schema_range: TBD` | Open by design (Tessera-runbook referent); resolve when the matrix is known. `open` (blocked) |

## C. 2.2.0 / 2.4.0-fold deferred items

| ID | Item | Source |
|---|---|---|
| C-1 | GR2-03a surfacing notice — fail-loud, non-blocking on model/runtime change (constraints locked, not built) | changelog / milestone memory. `open` |
| C-2 | Retrofit telemetry state-schema — retrofit plans emit `telemetry.md` without a matching state field | changelog "recorded but NOT fixed". `open` |
| C-3 | Doc-citation normalization pass — pre-existing hook/wrapper citations at older versions (incl. `§6.D` refs) | changelog. `open` |
| C-4 | R8 — eighth IC check (AR2-09b): NOT added at 2.2.0 (golden fixtures + R7 cover the repo-side risk); a forward feature with a recorded cost-of-deferral | changelog `### R8 — Eighth IC check: deferred (AR2-09b)`; `ic_checks.py` has only IC-1..IC-7. `decision` |
| C-5 | AR2-09a — no standalone run-summary template file is emitted (the run-summary is inline in the wrappers) | `templates.py:1083` "[AR2-09a]"; milestone memory. `decision` |

## D. Sub-cap review findings (changelog "recorded but NOT fixed")

Small correctness/cleanup items below the reported cap. All `open`.

| ID | Item |
|---|---|
| D-1 | Progress template `../../learnings/` link → `.claude/learnings/`, but retrofit calibration ledger sits at repo-root `learnings/` (neither mode creates the dir) |
| D-2 | Duplicated ~110-word telemetry question text in `render_interview` vs `run_interactive` (drifted; test pins only one copy) |
| D-3 | `_body_of` helper defined *after* its call sites → two bare-`IndexError` lookups |
| D-4 | Two determinism checks strictly implied by the whole-plan digest check (redundant) |
| D-5 | Dead `not pv` arm in `_telemetry`'s guard (`PROTOCOL_VERSION` is a module literal) |
| D-6 | Redundant proposal rebuild in `test_interview.py` |
| D-7 | Assumption-ledger drift row cites drift-detector config even when `hooks.drift_detector: false` (untested config) |
| D-8 | Freeze-exception ledger numbering not continued by v2.4.0 blocks (format fixed, sequential numbering not) |
| D-9 | Per-task wrapper `log()` emits a literal `\n` (a `.format`-doubling quirk at `templates.py:1444`), so its `hooks.log` entries share one physical line — vs the correct single-backslash form in `auto.sh`/`loop.sh`. Worth its own small freeze-exception. (changelog ~L904, milestone memory) |

## E. Post-retrofit test-coverage queue

Source: `post-retrofit-tasks` memory. Landing structure: a `tests/smoke/` dir.

| ID | Item | Status |
|---|---|---|
| E-1 | E2E CLI smoke (#2) — dry-run vs real greenfield + retrofit fixtures; catches argparse-layer breakage the unit tests bypass | `open` |
| E-2 | Cross-mode regression matrix (#3) — retrofit-install fixture A, then run greenfield suite vs fixture B in-process; proves no global-state leakage | `open` |
| E-3 | `tests/smoke/` layout (#6) — landing dir for E-1/E-2 with golden-tree diff | `open` |
| — | `bin/run-tests` (#4) | `done` — PR #9 |
| — | CI (#5) | `done` — Milestone A (`ic-self-check.yml`) |
| — | Interactive walkthrough test (#1) | `done` — PR #2 |

## F. Lower-priority (2026-05-19 checkpoint + Milestone-B carry-over)

| ID | Item | Source |
|---|---|---|
| F-1 | test-gate grandfather clause — per-module exemption from the `inventory/testing.md` no-test list | 2026-05-19 checkpoint. `open` |
| F-2 | Widen `inventory_scan.py` pyproject regex — misses bare `fastapi` without a version | 2026-05-19 checkpoint. `open` |
| F-3 | Refactor `propose_commands` to take a root path instead of `os.getcwd()` | 2026-05-19 checkpoint. `open` |
| F-4 | Phase 9.6 unnamed config keys — spec decision for retry posture / completion-criteria checklist / audio-cue overrides (currently comments, no keys) | milestone memory / Milestone-B carry-over (NOT the 2026-05-19 checkpoint). `decision` |

## G. Retrofit adversarial-review deferrals (Round 3, v1.6.3)

Source: `post-retrofit-tasks` memory. All `open` unless noted.

| ID | Item |
|---|---|
| G-A4 | Parallel retrofit templates (`_retrofit_claude_md`/implementer/reviewer) not composed — add a mirror-assertion or "byte-mirrors greenfield" docstring |
| G-A5 | `mode_selection_ledger` milestone counter should count non-empty rows, not raw row count |
| G-B1 | `--force` is global; would need per-file scope (Round-3 wrapper guard mitigates the worst case) |
| G-B3 | `legacy_allowlist` rendered in input order — sort-before-emit is the clean follow-up |
| G-D1 | T2 AD class single-case — adversarial hardening (newline-injection, Unicode confusables, kilobyte allowlists) |
| G-D2 | FS5 semantic disambiguation comment (one-line cosmetic) |
| G-F1 | `bootstrap_protocol_version` is write-only telemetry — startup version-mismatch check is a v1.7.x conversation |
| G-F2 | Documented migration path when BOOTSTRAP bumps — RETROFIT-COMPANION change, not installer code |
| G-G2 | Validator/B5 error-message coupling → two-iteration fix cycles (one-line cosmetic) |

## H. Round-2 adversarial-review items — reviewed, no action

Recorded so they aren't re-derived; each judged defensible as-is. All `no-action`.

| ID | Item |
|---|---|
| H-4.2 | Installer seeds `r08_committed` via setdefault — initial-seed contract is defensible post C1+C2 fix |
| H-5.2 | Protocol-version lifecycle — `state.update` semantics are the operator-expected outcome |
| H-3.1 | jq-garbage discrimination — already T2-safe via strict `[ "$_val" = "true" ]` |
| H-3.3 | Two-seam independence — a third runtime seam would significantly grow the preamble |
| H-2.2 | TEMPLATES dict cardinality arithmetic in a commit message — pedantic |

## Priority reading

Highest-signal actionable clusters: **B** (seam follow-ups) and **E** (smoke /
cross-mode coverage). **A** and **F-4** are decisions only. **D** and **G** are
mostly small cleanups. **H** is effectively closed. B-2 and B-3 are blocked on
the Tessera roadmap, not on us.

# Retrofit Installer — Session Checkpoint

**Date:** 2026-05-19
**Branch:** `retrofit-installer` (8 commits ahead of `main`)
**Status:** All 8 deliverables complete + C2 scoped adversarial review applied. 332/332 tests green. Ready for PR.

---

## TL;DR for next session

```bash
cd /home/dengc/Documents/Projects/Project-Bootstrap-Protocol
git checkout retrofit-installer
python -m pytest tests/ -q          # expect 332 passed
git log --oneline main..HEAD        # expect 8 commits, last = 1cb6aef
git diff --stat main...HEAD         # expect 12 files, +7107/-3
```

If those three commands match, state is intact. Pick up from "Pending / deferred work" below.

---

## Source kickoff doc

`~/Downloads/retrofit/CLAUDE-CODE-KICKOFF-RETROFIT-INSTALLER.md`

Specified 8 ordered deliverables (D1–D7 + scoped C2 review) with HARD STOP after D1 for operator review of open decisions.

---

## Deliverables — all complete

| # | What | Commit | Notes |
|---|---|---|---|
| D1 | Design note + 7 open decisions surfaced | (pre-commit, operator-approved) | 7 ODs approved with binding conditions C1+C2 and required tests T1+T2 |
| D2 | Golden-output greenfield-invariance test (`tests/test_greenfield_golden.py`) | `35c6420` | 2 fixtures: `default` digest `fc139d43…a6f55` (54 actions), `full_autonomous` digest `78055b69…155c283` (65 actions). `GOLDEN_UPDATE=1` to regen |
| D3 | Retrofit decision layer (`lib/inventory_scan.py`, `lib/retrofit_heuristics.py`, `lib/retrofit_interview.py`, `bin/retrofit-interview`) | `694252c` | Scanner → heuristics → interview → validated `mode: retrofit` cfg |
| D4 | `lib/templates.py` retrofit overlay + `lib/installer.py` overlay branch | `089d76a` | 14 retrofit template fns + `_apply_retrofit_overlay(plan, cfg)` |
| D5 | Hook-body retrofit variants via `_hook_dispatch` wrapper | `507e5a0` | Three hooks: `spec-gate-commit`, `test-gate`, `tdd-gate`. `secrets-gate` NOT touched per R8.A.3 |
| D6 | `.retrofit-state.json` writer (B5-frozen shape) | `e8d68b2` | `_write_retrofit_state` sibling fn, single dispatch at call site |
| C2 | Scoped adversarial review (D5+D6 surface) — R-1/R-2/R-3 fixes + safety verifications | `e2e4514` | R-1 dead `pass` → loud warning; R-2 setdefault for retrofit_active; R-3 r08_committed schema; case-pattern hostile-input safety proven |
| D7 | `tests/test_retrofit.py` — 142-check behavioral suite | `1cb6aef` | 9 sections incl. T1 (19 dual-shape wiring asserts) + T2 (5 fail-safe seam checks under no-jq harness) |

---

## Test gauntlet — 332 / 332

| Suite | Count | Purpose |
|---|---|---|
| `tests/test_greenfield_golden.py` | 6 | D2 byte-identity: greenfield plan digest never changes |
| `tests/test_installer.py` | 118 | Pre-existing — FROZEN, zero diff |
| `tests/test_interview.py` | 66 | Pre-existing — FROZEN |
| `tests/test_retrofit.py` | 142 | D7 retrofit behavior, including T1 + T2 |
| **Total** | **332** | |

Run: `python -m pytest tests/ -q`

---

## Frozen-file audit — zero diff against `main`

```
lib/minyaml.py
bin/bootstrap-install
tests/test_installer.py
bootstrap.config.yaml
BOOTSTRAP.md
```

Verify: `git diff main -- lib/minyaml.py bin/bootstrap-install tests/test_installer.py bootstrap.config.yaml BOOTSTRAP.md` → empty.

## C1 audit — exactly 4 AST changes outside new definitions

OD-1 bundled freeze exception permits these and no more:

1. `lib/templates.py` — `TEMPLATES["hook"] = _hook_dispatch` (was `_hook_body`)
2. `lib/installer.py` — single `if cfg.get("mode") == "retrofit":` branch in `build_plan` calling `_apply_retrofit_overlay`
3. `lib/installer.py` — state-write dispatch line: `(_write_retrofit_state if cfg.get("mode") == "retrofit" else _write_state)(...)`
4. `lib/defaults.py` — retrofit validation block in `resolve_config` (rejects autonomous_modes.*_enabled=true at retrofit time per B5)

`_hook_body`, `_HOOK_HEADER`, and `_write_state` remain AST-byte-identical.

---

## File map

**New files:**
- `tests/test_greenfield_golden.py` (D2, 198 lines)
- `lib/inventory_scan.py` (D3, 669 lines)
- `lib/retrofit_heuristics.py` (D3, 791 lines)
- `lib/retrofit_interview.py` (D3, 940 lines)
- `bin/retrofit-interview` (D3, 27 lines)
- `tests/test_retrofit.py` (D7, 814 lines)
- `RETROFIT.md` v1.6.2 (pre-D1)
- `RETROFIT-COMPANION.md` v1.6.2 (pre-D1)
- `RETROFIT-GAP-ANALYSIS.md` (pre-D1)

**Modified (additive only, frozen contracts preserved):**
- `lib/defaults.py` (+148): MODES enum, RETROFIT_DEFAULTS, retrofit validation in resolve_config
- `lib/templates.py` (+1022, -2): _RETROFIT_PREAMBLE, _hook_body_retrofit, _hook_dispatch, 14 retrofit templates, 15 TEMPLATES entries
- `lib/installer.py` (+243, -1): _apply_retrofit_overlay, RETROFIT_STATE, RETROFIT_PROTOCOL_VERSION, _write_retrofit_state, dispatch

---

## Decisions on record (for context preservation across sessions)

### Open Decisions (all approved ✓)

- **OD-1** Bundled freeze exception (4 AST changes ENUMERATED above; no others)
- **OD-2** mode field at top level of cfg (not nested under retrofit)
- **OD-3** Auto-detect build/test/lint commands from CI/manifests/Makefile
- **OD-4** Scaffold-but-defer: wizard NEVER enables autonomous modes at retrofit time
- **OD-5** Inventory artifacts written by decision layer; installer emits only static `inventory/README.md` pointer
- **OD-6** Legacy-allowlist parsed at hook runtime from LEGACY_ALLOWLIST_BEGIN/END markers
- **OD-7** ROLLOUT_WEEK: N marker drives graduated warn→block schedule

### Binding conditions

- **C1 (architectural):** Do NOT modify `_write_state`. Add `_write_retrofit_state` as sibling fn, dispatch by `cfg["mode"]` at call site. `_write_state` AST-byte-identical. **Status: enforced and audited.**
- **C2 (process):** Scoped adversarial review after D6 covering D5+D6 surface as one unit, BEFORE D7. **Status: executed; R-1/R-2/R-3 fixed in `e2e4514`.**

### Required tests

- **T1:** `tests/test_retrofit.py` must assert nested config opt-in fields and top-level state-file enabled/in-flight fields are wired correctly and never conflated/cross-written. **Status: Section 8 of test_retrofit.py, 19 explicit assertions.**
- **T2:** Scoped review must prove via execution that the ONLY path to the retrofit preamble's early `exit 0` is an affirmative allowlist / retrofit-active match. Must run under no-`jq` restricted-PATH harness. **Status: Section 9 (AF1–AF5), all paths under restricted PATH proven to fall through to ENFORCE.**

### Key architectural invariants (do NOT break)

- **Two-layer split:** Decision Layer (interview, free to evolve) + Scaffolding Layer (installer, deterministic, byte-identical for greenfield)
- **B5-frozen state shape:** `*_enabled` and `*_in_flight` TOP-LEVEL in state file; `*_opted_in` and `brownfield_milestones` NESTED in cfg under `retrofit.autonomous_modes`. Never conflate.
- **T2 fail-safe seam:** every error/missing/parse-failure path in `_hook_body_retrofit` MUST fall through to ENFORCE (greenfield logic). No early `exit 0` except via affirmative match.
- **Scaffold-but-defer:** retrofit wizard scaffolds R0–R10 stubs but never enables autonomous modes; promotion happens later via brownfield milestone gate.

---

## Pending / deferred work

Listed in priority order. Pick one or batch:

1. **Push branch + open PR.** `git push -u origin retrofit-installer && gh pr create --title "Add retrofit mode" --body "..."` — body should cite this checkpoint.
2. **test-gate grandfather clause.** D5 deferred: per-module exemption from `inventory/testing.md` no-test list. Lets retrofit projects opt specific legacy modules out of test-gate enforcement without disabling globally.
3. **Interactive front-end full walkthrough test.** `bin/retrofit-interview interactive` exists but only `scan`/`analyze`/`synthesize` subcommands have end-to-end coverage. Wrap an `expect`-style or stdin-fed test around the full interactive flow.
4. **Widen `inventory_scan.py` pyproject parser.** Current regex matches `fastapi>=0.100` but skips bare `fastapi`. Causes dep underdetection on minimal pyproject.toml files.
5. **`propose_commands` should take a root path.** Currently uses `os.getcwd()`, forcing tests to `os.chdir`. Refactor to `propose_commands(root: Path)` and update callers.

---

## How to verify state on resume

```bash
cd /home/dengc/Documents/Projects/Project-Bootstrap-Protocol
git checkout retrofit-installer

# 1. Branch is correct and ahead of main by exactly 8 commits
git log --oneline main..HEAD | wc -l   # 8

# 2. Last commit is D7
git log -1 --oneline                    # 1cb6aef D7: tests/test_retrofit.py ...

# 3. Tests pass
python -m pytest tests/ -q              # 332 passed

# 4. Frozen files have zero diff
git diff main -- lib/minyaml.py bin/bootstrap-install tests/test_installer.py bootstrap.config.yaml BOOTSTRAP.md
# (no output)

# 5. C1 audit — only 4 AST changes outside new definitions
git diff main -- lib/templates.py lib/installer.py lib/defaults.py | grep -E '^[+-][^+-]' | grep -v '^[+-]\s*#' | less
```

If all five check out, you are exactly where this session ended.

---

## Source references

- Full transcript: `/home/dengc/.claude/projects/-home-dengc-Documents-Projects-Project-Bootstrap-Protocol/0273282c-a702-4112-8fdb-eb81113eed40.jsonl`
- Kickoff doc: `~/Downloads/retrofit/CLAUDE-CODE-KICKOFF-RETROFIT-INSTALLER.md`
- Retrofit spec docs: `RETROFIT.md`, `RETROFIT-COMPANION.md`, `RETROFIT-GAP-ANALYSIS.md` (committed in `145dcc2`)

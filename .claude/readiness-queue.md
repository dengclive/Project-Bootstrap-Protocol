# Readiness queue

Worked by `.claude/readiness-runbook.md`. **Internal automation, not protocol
surface.** Ordered by the runbook's §1 rule: **A before B before C — never take
a C item while an A item is ready.**

The goal is not "empty this list". It is to move `docs/production-readiness.md`
§1 off **"not production ready"**. Items are labelled with what they actually
buy.

---

## A — moves the verdict

*(`c1-license` closed 2026-08-14 — PR #75, merge `de13e71`. See Done.)*

*(`sdk-pipe-trigger-redos` closed 2026-08-19 — PR #81, merge `897d427`.
See Done. The two items directly below are the work STRIPPED out of it.)*

- **[blocked] c2-autonomous-dispatch** · `DECISION` · eligible: **no** · **E3 on
  sight** · scope undecidable until the question below is answered
  **THE SECOND OF THE VERDICT'S TWO REMAINING LEGS, AND UNTIL 2026-08-20 IT HAD
  NO WORK ORDER AT ALL** — it is named in `docs/production-readiness.md` §1 and
  in this file's own closing paragraph as a standing blocker, and nothing in any
  tier proposed to do anything about it. **The queue could not reach "production
  ready" no matter how faithfully it was worked.** That gap is the reason this
  row exists.
  **RE-DERIVED ON `main` @ `e3f2f57`, DRIVEN END TO END PAST THE ELIGIBILITY
  GUARDS with a `loop_eligible: true` task under `.claude/specs/s1/tasks/`, a
  stub `claude` first on `PATH`:**
  * `auto.sh` → rc=1, *"Queue runner skeleton installed. Implement the dispatch
    loop per Bootstrap-Protocol-v2-2-0.md Phase 9.7 before any unattended use."*
  * `loop.sh` and `goal-loop.sh` → rc=1, *"No agent work was dispatched."*, both
    naming the call they would make (`claude -p --worktree "wt-T-100"
    --output-format stream-json --verbose`).
  * **No real `claude` invocation was recorded by the stub.** The feature is
    absent, not merely guarded.
  **HALF OF THE RECORDED FINDING IS STALE AND THE STALE HALF IS THE DANGEROUS
  ONE — IT WAS FIXED.** `docs/production-readiness.md`'s C-2 row (measured at
  `e47d827`) says the wrappers *"announce that refusal on stderr while exiting 0
  and recording a terminal-SUCCESS `exit_reason`"*, i.e. under `nohup` or cron a
  skeleton that did nothing was indistinguishable from a clean overnight run.
  **That is no longer true: all three exit 1**, and
  `tests/test_wrapper_behavior.py` pins it as a PROPERTY (*"a wrapper that
  dispatched nothing must not exit 0, and must not record a success code"*).
  **What survives is only "dispatches nothing".** Re-measure before quoting the
  C-2 row; do not copy it.
  **WHY THIS IS A DECISION AND NOT A FIX.** Two resolutions are legitimate and
  they are not the same project:
  **(a) IMPLEMENT the dispatch loop** — per Phase 9.7. Large, security-sensitive
  (it runs `claude -p` unattended in the ADOPTER's tree), and **in direct tension
  with this repo's own trust ramp: R1 is literally *"`/loop` with a fixed prompt
  — unattended iteration on one scoped task"*, and `bin/trust-ramp check --rung
  R1` returns DENIED.** Shipping adopters a capability this project has not
  earned for itself needs to be an explicit choice, not a default.
  **(b) STOP CLAIMING IT** — make the emitted surface and the PRD honest about
  autonomous modes being unimplemented skeletons, and drop them from the
  readiness question. Cheap, and it moves the leg by removing the claim rather
  than by building the feature. **Not covered by `t1-honest-labelling`**, which
  scopes to security promises in `secrets.md` and flat reassurances, not to the
  autonomous-mode claim.
  **THE ONE QUESTION, which is the whole item:** *does the project SHIP
  autonomous dispatch, or does it stop advertising it?* Tier it, size it, or
  close it — a decision, not a fix, exactly as `a6-spec-gate-predicate` is.
  **IF (a) IS CHOSEN, this is what any plan must carry, derived not guessed:**
  `tests/test_wrapper_behavior.py` is deliberately written to SURVIVE a fix — its
  checks assert the property, not the skeleton — **except one**:
  `check("no wrapper dispatched a real `claude` call", not
  os.path.exists(STUB_LOG))`. That single check flips the moment dispatch works,
  and it is the correct place to re-state what "dispatched safely" means. The
  other 64 checks in that file should still pass; if they do not, the fix is
  wrong, not the pins.


- **[ready] prefix-run-cost-residuals** · `CODE` · eligible: **yes** · full
  ceremony · scope TBD at plan time
  **THE COST CLASSES THAT SURVIVE `sdk-pipe-trigger-redos`. FILED HERE BECAUSE
  THE BACKLOG ROWS THAT DESCRIBED THEM WERE STRIPPED FROM PR #81 FOR BEING
  WRONG — DO NOT RECOVER THEM FROM `git show`; RE-MEASURE.** PR #81 closes the
  token-count axis on `prefix_run` and nothing else. **At least four superlinear
  shapes reach that regex or its neighbours and are untouched by it**, all with
  ZERO jump bytes and all far under `_CMD_MAXLEN` 81920, so `_cost_guard` is
  structurally blind to every one. **Two of the four were mislabelled by me in
  the stripped rows and the mislabelling ran in the direction that OVERSTATES
  severity**, which is why re-measuring is mandatory:
  * **wrapper × spaced-brace product** — `A=1/env ` matches the assignment arm
    AND the path-prefixed wrapper arm at once, reopening the split at every
    token. ~2.1 KB, > 200 s before / ~53 s after. Not a regression.
  * **length axis, glued braces** — ~19 KB, ~21-22 s on BOTH trees, and **the
    emitted `dependency-gate.sh` is quadratic here too** (~1.9 s at 9.6 KB →
    ~7.2 s at 19 KB), so **the shell is NOT the safe substrate on this axis**.
    That refutes the premise the whole item was planned on.
  * **redirect arm, self-ambiguous** — `[0-9]*[<>]+ *[^ ]+ +` lets `[<>]+` and
    `[^ ]+` consume the same characters, so `2>>o ` has two parses ending at
    the same offset: ~2x per added token at ~110 B. **MEASURED allow/allow on
    the bare payload — it is NOT the shell-DENY/SDK-BYPASS the stripped row
    claimed.** With an install tail it is deny/deny, 135 B, ~5.4 s SDK against
    ~0.03 s shell.
  * **`_GIT_VERB_TMPL`'s own flag star** `(?:\s+-[Cc]\s+\S+|\s+-\S+)*` — a
    `-C` token is consumable by BOTH arms: the SAME multi-absorbing-arm defect
    PR #81 removes from `prefix_run`, spliced next to it and left in place.
    Measured on the emitted object: 0.073 s at 107 B → **23.5 s at 143 B**,
    ~1.62x per token; the same shape with a non-`-C` flag is 0.0005 s at 9 KB,
    so the cost is the arm overlap alone. **MEASURED allow/allow**: the
    exponential fires only when `_git_verb` FAILS, i.e. exactly when the gate
    would allow anyway, so it is a CPU burn on an allow path, not a bypassed
    deny — but `spec-gate-commit` and `eval-gate` carry **no `_GATE_TIMEOUTS`
    entry at all**, so what a cancelled hook does there is undetermined and
    worth establishing.
  **METHOD THIS ITEM MUST CARRY, derived the expensive way on PR #81:** state
  the VERDICT PAIR you measured, not the one the shape suggests — three
  separate rows were written as `shell-DENY / SDK-BYPASS` without anyone
  running the payload through both substrates and reading the exit codes.


- **[ready] x37-class-b** · `CODE` · eligible: **yes** · full ceremony
  · scope `lib/cmdpos.py`, `lib/templates.py`, `lib/sdk_gates_template.py`,
  `tests/test_substrate_differential.py`, `tests/test_composition.py`,
  `tests/test_greenfield_golden.py`, `tests/test_retrofit.py`,
  `docs/deferred-backlog.md`
  **ATTEMPT 1 BUILT AND WITHDRAWN 2026-08-14 — STILL OPEN. Read the X-37 row
  before re-planning; it carries what 100 agents proved.** Branch
  `fix/x37-class-b`, PR #77, NOT merged, kept as evidence. It made 54 rows go
  allow/allow → deny/deny with the fence intact and the suite at 25/9,739/0,
  and the step-7 review still killed it: the rule is ~cubic in
  substitution-opener count, a dimension `_cost_guard` does not bound, so a
  cap-legal `$(`-dense payload crosses the emitted 60 s timeout — and a killed
  hook fails OPEN, turning the approved-list and D20 denies into ALLOWS. A
  larger hole than the one it closed. Second blocker: the body scan `[^)]`
  cannot cross a `)`, so one nested `$()` before the downloader defeated all
  six arms. The two are in TENSION.
  **THE ROW'S OWN INSTRUCTION IS THE THING TO STOP FOLLOWING:** "model it
  beside `cmdpos.pipe_to_shell_regex`" is the wrong architecture. Attempt 2
  should use the walk that already exists — `_cs_subst_scan` / `_subst_inners`
  / `_lift_subs`, bounded by `_SUBST_BUDGET` / `_SUBST_MAXLEN` — to ask which
  substitutions carry a downloader at a command position, plus a CHEAP anchored
  test for whether the substitution sits at an execution position.
  **Scope is wider than this row said** (the four files above were missing, and
  `tests/test_retrofit.py`'s digests go red without it — a step-5 E4 waiting to
  happen). Freeze exception **71 is drafted but UNUSED**; attempt 2 reuses it.
  **Also carried:** `interpreter_word` not `INVOKERS` (or `${SHELL} -c "$(dl)"`
  matches nothing) · the code letter is admissible anywhere in a bundle
  (`bash -cx`) · `bash < <(dl)`, `bash <<< "$(dl)"`, `bash /dev/stdin <<<`,
  `bash 0< <(dl)` are the same channel and absent from this row's shape list ·
  `bash -c -- "$(dl)"` needs a `--`-tolerant run · `ssh host "$(dl)"` denies on
  the merits · **measure cost with `$(`-DENSE padding, not plain text** — plain
  padding is linear and hides this entire class.
  Item 1b / Class B: download-then-run laundered through a command
  substitution (`bash -c "$(curl)"`, `eval`, bare/backtick/process-sub).
  Status cell, derived 2026-08-14: `` `open` — pre-existing, forbidden
  direction, release-relevant; the distinct half of item 1``. §8 holds item 1
  release-blocking until 1b/X-37 **and** B3 land; **B3 has landed**
  (`lib/templates.py:1700`), so this is the survivor and the only A-tier item
  that can be taken without a decision.
  Step 4 = a differential row that is red on the current tree. Freeze
  exception applies. **Never batched.**

## B — makes shipping-with-known-risk honest

- **[ready] t1-honest-labelling** · `EMITTED` · eligible: **partial**
  · scope `lib/templates.py`, `lib/sdk_gates_template.py`, emitted
  `secrets.md`, `docs/changelog.md`
  Qualify the emitted `secrets.md` promise (timeout/padding bypass); sweep
  emitted templates for flat reassurances — joined-file, case-insensitive, over
  `git ls-files` **and** emitted bodies **and** `gh pr view --json body`.
  The sweep-and-qualify half is eligible; the emit-or-not question is split out
  below. Freeze exception + citation rule apply.

- **[ready] t1-threat-model-emit** · `EMITTED` · eligible: **yes**
  **DECIDED 2026-08-14 by the operator: EMIT it into installs.** Unblocked.
  This fulfils the disclosure half of defer-and-disclose. Costs a freeze
  exception and a golden re-baseline (action counts WILL move — a file is
  added, so §4.1's count check is expected to change here and that is not
  **E5**; say so in the exception). Sequence AFTER `t1-honest-labelling` so the
  emitted text is already honest when it ships.

- **[ready] dw-p4-posture** · `DOC` · eligible: **yes** · batchable with C
  **DECIDED 2026-08-14 by the operator: DW-P4 STAYS ADVISORY — write it down.**
  Record the decision and close the standing question. Two `DOC` follow-ons
  ride along: DW policy §1's grant table still names the inert
  `~/.claude/settings.json` under `CLAUDE_CONFIG_DIR` (re-confirmed
  2026-08-14), and the DW-P4 breach count is stale against the ledger. Note
  honestly that advisory means the logged breach can recur.

- **[blocked] a6-spec-gate-predicate** · `DECISION` · eligible: **no** · T0
  `spec-gate-commit`'s predicate blocks the first code commit of every adopting
  project. Tier it, size it, or close it — a decision, not a fix.

## C — record hygiene · moves the verdict **not at all**

**Batch these.** One branch, one PR, one review, one checkpoint. They are
separate items only because they were discovered separately.

- **[ready] prefix-run-record-layer** · `DOC` · **batch with `x58-table-render`,
  they touch the same rows** · scope `lib/cmdpos.py`, `lib/sdk_gates_template.py`,
  `lib/templates.py`, `tests/test_issue_fixes.py`,
  `docs/agentic-harness-security-kb.md`, `docs/deferred-backlog.md`
  **THE RECORD WORK STRIPPED OUT OF PR #81 AT THE OPERATOR'S DIRECTION AFTER THE
  FIX LOOP DIVERGED (E2, 12 findings → 16).** Every item below is a real defect
  that was verified; they were removed because correcting them in the same PR
  kept introducing NEW false claims, not because they are wrong.
  * **The `#43 F1` cost rationale is falsified by PR #81 and still present
    tense in six places**, two of them shipped bytes: `lib/cmdpos.py`,
    `lib/sdk_gates_template.py` (emitted `gates.py`), `lib/templates.py`
    (emitted `dependency-gate.sh`), `tests/test_issue_fixes.py`. It describes
    `(flag|positional)*` and a two-path assignment that no longer exist.
  * **`lib/sdk_gates_template.py` says "`dependency-gate` is in no timeout
    table"** while the same file sets `"dependency-gate": 60.0`. **It is
    shipped bytes and it negates the mechanism of the fail-open PR #81
    closes.** Highest-value row here.
  * **`docs/agentic-harness-security-kb.md` teaches that "does it match" is
    safe under a greedy unbounded prefix**, including as a `- [ ]` reviewer
    checklist item. Cost makes that false: an arm ambiguous with itself is
    exponential on a FAILING match and the control times out instead of
    answering.
  * **X-58's line citations are stale by exactly +11 in ELEVEN places**, not
    the four anyone has noticed. The seven row citations each land on a REAL
    BUT DIFFERENT row (`:358` is X-32g, not X-36i), which reads as verified.
  * **`prefix_run`'s docstring arm list** describes the pre-2026-08-19
    structure. A minimal correction shipped with the fix; the fuller record
    (why the star was exponential, and that it is INTRA-arm rather than a race
    between arms) did not.
  **DO NOT WRITE A MECHANISM NARRATIVE WITHOUT REBUILDING IT.** The stripped
  version got the mechanism wrong twice — it said three arms raced when only
  ONE arm can even start on the measured payload.


- **[ready] x58-table-render** · `DOC` · scope `docs/deferred-backlog.md`
  Anchors drifted (header :333-334, blanks :360/:397). **Not mechanical** —
  deleting the blanks drops status cells from over-celled rows, which silently
  changes `count.py`'s answer. Validate the rule at 88 before *and* after.
- **[ready] priority-reading** · `DOC` · scope `docs/production-readiness.md`
  Names none of the twelve genuinely blocking rows; Snapshot header still
  `main @ 3c0a2de`, many merges stale.
- **[ready] x49-four-eras** · `DOC` · scope `docs/deferred-backlog.md`,
  `docs/changelog.md`
- **[ready] changelog-citation-anchor** · `TEST-CONTRACT` · **not batched**
  · scope `tests/test_doc_citations.py`, `.claude/dynamic-workflow-policy.md`
  Anchor the changelog citation to a heading instead of a line: it moved three
  times in one session (795 → 851 → 882 → 922; twelfth value, eleventh move).
  Step 4 needs a case proving the old form passed wrongly.

## Measurement residuals

- **[ready] x54-deny-shape** · `MEASUREMENT` · eligible: **yes**
  The gap the 2026-08-14 pass left in its own claim: same 80004 B / 4000 jumps
  padding, but a payload that **would otherwise DENY**, through the emitted
  60 s timeout. That *demonstrates* X-54's bypass rather than sizing it. The
  harness exists and takes `HC_HEADS`.
- **[ready] x55-rerun** · `MEASUREMENT` · eligible: **yes**
  `>240 s KILLED` not re-run; stated as owed in the KB.

## External — not ours to take

- **[blocked] sibling-lit07-migrations** · `EXTERNAL` · eligible: **no**
  AgenticRE and hermes-provisioning-refactor carry uncommitted LIT-07
  migrations. A reset there loses them silently. Surface at next contact.

## Residue — do not re-open

Changelog per-item entries for nos. 51–67 (absent by the entry's own words);
the nine historical fail-closed sites (historical record); the PR-attribution
defect (fixed, `fc37aaa`); the `count.py` rule (fixed).

## Done

**`sdk-pipe-trigger-redos` PR #81 `897d427` — the SDK prefix-run ReDoS, and a
fix loop that DIVERGED and was stripped rather than continued.** `prefix_run()`
was a star whose wrapper arm was ambiguous with itself, so a FAILING match was
exponential: `curl … | ` + `env `×22 + `zzz ; pip install evilpkg` is **134 bytes
with zero jump bytes** and cost the emitted `dependency-gate` **77.56 s CPU**
against the 60 s it declares — a cancelled hook exits 124/137/143 and only exit 2
blocks, so the command proceeded unadjudicated while the shell denied it in
0.03 s. `_cost_guard` measures length and jump density and could see neither
term. Fixed by allowing **at most one absorbing arm**. Suite 9,729 → **9,763**;
differential 4,161 → **4,178**; composition 130 → **147**. Freeze exception
**72**, five digests, action counts unchanged at 57/69/59 and 79/93.

**THE LANGUAGE IS UNCHANGED AND THAT IS DECIDED, NOT SAMPLED** — an exact
ERE→NFA→product-BFS equivalence procedure explored the full product graph in
BOTH dialects with zero accept-disagreements, two-sided calibrated against
deliberately broken variants, corroborated by three engines and 648 real command
shapes through both emitted substrates of both trees. Post-merge I ran the
security KB's own release check: **the full 17,268-case corpus through both
trees, previously-denied-now-allowed = 0**, and zero changes in the other
direction too — which also confirms the corpus is blind to this class, so that
result is evidence of NO REGRESSION and is **not** evidence the fix works. The
four cost rows are that evidence.

**THE PART WORTH REMEMBERING IS THE FAILURE.** Step 7 returned 12 findings; the
commit fixing them returned **16**, six about claims that commit introduced. The
item halted at **E2** and the operator directed a strip to the mechanically
verified core. **Every defect in both rounds was in PROSE** — the regex had a
decider, the gates 9,763 assertions, the digests pins; the claims had nothing.
**Two backlog rows were mislabelled `shell-DENY / SDK-BYPASS` when their payloads
measure allow/allow**, both overstating severity, because nobody ran the payload
through both substrates and read the exit codes.

**THE VERDICT DID NOT MOVE** and `docs/production-readiness.md` is untouched by
design: it does not rest on this item (0 mentions), and a fail-open that shrinks
from 134 bytes to ~2 KB is still a fail-open. **The cost class is NOT closed** —
the token-count axis is. Residuals filed as `prefix-run-cost-residuals` (A) and
`prefix-run-record-layer` (C). **One known defect shipped and is disclosed:** this
change makes the `#43 F1` rationale stale in four files, two of them emitted
bytes; it is the first row of `prefix-run-record-layer`.


**`b1b-fence-pins` PR #79 `88b2c42` — the item-1b false-positive fence, which
did not exist.** Every pinned row in the repo putting a command or process
substitution at an EXECUTION position was one of the six Class-B KNOWN-OPEN rows
X-37 exists to FLIP to `deny`; nothing asserted such a substitution may still be
ALLOWED, so a rule keyed on position alone was invisible to the corpus. 45 rows
in four behaviourally-derived groups (`_B1B_FENCE_EXEC` 26 / `_B1B_FENCE_PATH` 4
/ `_B1B_FENCE_DATA` 8 / `_B1B_FENCE_DL` 7) + 12 contract checks. Suite
9,672 -> 9,729; differential 4,104 -> 4,161. No `lib/` change, no rule, no
digest movement, **no freeze exception**. **X-37 is NOT advanced** — this makes
the next attempt falsifiable. Merged by the loop on explicit operator direction
in-session (9b carve-out; the operator was on remote control and could not
reach `gh`).

**`c1-license` PR #75 `de13e71` — readiness C-1 CLOSED, Apache-2.0; the first
finding this cycle FIXED rather than re-measured** · `x54-headclass-measurement`
PR #70 `9450b7d` (exc. 69) · `prd-filename-v280`
PR #72 `54ebc4b` (exc. 70) · ledger entries 27/28 PRs #69 `f9c2bb2`, #71
`03dd309` · post-v2.8.0 record PR #68 `6143427` · **the harness itself**
(runbook + this queue + `context-check.py`) PR #73 `358ac9b`, **merged by the
operator — the first merge in this run the loop did not perform itself**, which
is exactly what 9b now requires.

## Owed

*(Nothing. The PR #72 ledger entry that was owed here is discharged as entry
29; the harness work is entry 30. Ledger at 30, pin moved in the same commit.)*

**Verdict status, so the scoreboard is not lost between sessions:**
`docs/production-readiness.md` §1 still reads **NOT PRODUCTION READY** — and
that is the correct outcome, not a failure of the item. **C-1 is CLOSED** (PR
#75, `de13e71`): the first readiness finding this cycle to be *fixed* rather
than re-measured, and `git ls-files | grep -icE 'licen[cs]e'` now returns 1.
§1 rests on **three** negative legs and one is gone. Still standing:
**X-37** (Class B — a remote payload still runs) and **C-2** (the autonomous
wrappers dispatch nothing). *"C-1 alone settles it either way"* meant
independently sufficient, never sole ground.

**[2026-08-20] `sdk-pipe-trigger-redos` is CLOSED** (PR #81, merge `897d427`;
closeout #82) and the paragraph that used to stand here — *"the next item is
`sdk-pipe-trigger-redos`, not `x37-class-b`"*, and *"`x37-class-b` is the only
remaining A-tier row"* — is superseded rather than deleted, because both were
true when written. **A now holds THREE rows**: `c2-autonomous-dispatch`
(blocked on a decision), `prefix-run-cost-residuals` and `x37-class-b`.
**AND THE SCOREBOARD IS BLOCKED ON A DECISION, NOT ON WORK:** of the verdict's
two remaining legs, X-37 has a work order and C-2 has only a question. Clearing
every buildable row in A would still leave §1 at *not production ready*.
**`x37-class-b`** stays ready and now has a fence under it (PR #79).

**On `x37-class-b`:** It is the only remaining A-tier
row, it is `CODE`, and it gets full ceremony. **Attempt 1 (2026-08-14) was
built, measured and WITHDRAWN as a net security regression — see the entry above
and the X-37 row. Nothing about the verdict changed, and X-37 is still `open`.**
The lesson the next session should not have to rediscover: a verdict corpus of
4,163 rows was fully green over a rule that was bypassable by one nested `$()`
and that turned existing denies into allows under padding. **A green corpus
proves the corpus did not move, not that the gate is sound** — the third time
this repo has logged that shape.

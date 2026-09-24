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

- **[done 2026-08-27] c2-autonomous-dispatch** · resolved via **(b) STOP
  ADVERTISING** · PR #96, merge `75eef0a`. Operator chose resolution (b): the
  protocol does not ship autonomous dispatch; it ships guarded skeletons, now
  disclosed as unimplemented at every surface that presents them as operable
  (emitted `CLAUDE.md` queue section, greenfield interview `scaffold-only`, PRD
  Phase 9.5/9.6/9.7 **SHIPS UNIMPLEMENTED** banners), and the C-2 readiness leg
  is **retired by disclosure** in `docs/production-readiness.md` (new dated
  layer). **THE VERDICT DID NOT MOVE:** `main` stays NOT PRODUCTION READY on the
  security legs alone (X-37, cost-class fail-opens). EMITTED class; freeze
  exception 76; action counts stable 57/69/59 (E5 clear); suite 25/9,831/0;
  citations 38/0 (C4 = option (i), PRD banners below the pins). Ledger entry 43.
  **The original DECISION row is preserved below for the record** (the two
  resolutions and why it was a decision, not a fix).

- **[was blocked, now resolved — see above] c2-autonomous-dispatch (original DECISION row)** · `DECISION`
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


- **[ready] pipe-rule-url-pipe-cubic** · `CODE` · eligible: **yes** · full
  ceremony · **taken 2026-08-23, worked to step 4, CLOSED OUT WITH NO FIX —
  PR #90, merge `36fef02`. The defect STANDS and this row stays in A; only the
  candidate died. Start from the refutation below.**
  **ATTEMPT 2 NARROWED IT — PR #116, merge `696d699`. Read the 2026-09-24
  layer directly below first, then the attempt-1 refutation.**
  **[2026-09-24 LAYER — ATTEMPT 2 NARROWED THE AXIS AND DID NOT CLOSE IT; THIS
  ROW STAYS IN A.]** All timings in this layer are wall-clock.
  * **What landed.** The five `_PIPE_TO_SHELL.search` call sites in the SDK's
    `_scan_install_line` now call `_pipe_to_shell`: per `[^;&]` segment, the
    earliest downloader END, then the anchored `_PIPE_TAIL` once per pipe after
    it. Same yes/no answer, without the downloader-START factor. The shell ERE
    is byte-identical. Freeze exception 81. Mutation gate PASS 18/18 on
    `eb3dde6`. CI green on `main` at `696d699` (run 35886935267). Filed payload,
    whole SDK gate, 8,445 B: 15.805 s on `ba6330b`, 0.127 s after; the table is
    in `docs/changelog.md`'s entry for this change.
  * **What stays open.** Each tail probe still re-reads the whitespace-free run
    after its pipe, so a pipe-dense run is quadratic: `http|` × 16,362 in a
    heredoc (81,855 B) takes 68.4 s and 69.2 s on the fix and still denies,
    after the 60 s ceiling. That is `pipe-run-glued-pipe-axis`. Pipes are now
    tried left to right where the regex tried them right to left, so the
    quadratic moved between two mirror shapes (interpreter last, interpreter
    first).
  * **Correction: PR #92 did not make this axis linear.** Re-measured on
    `ba6330b`, after #92: 2.001 / 6.787 / 15.805 s at 4,245 / 6,345 / 8,445 B,
    exponent about 3. See the `[REFUTED …]` note in this row.
  * **Correction: "THE AXIS IS SDK-ONLY" was measured only up to 10,545 B.** At
    the caps: the jump-free filed shape at 81,898 B takes 53.3 s on the shell on
    both `ba6330b` and `696d699` and denies (re-measured 2026-09-24). The
    jump-dense filed spelling at 43,032 B / 8,190 jumps takes 61.7 s and 62.3 s
    on the shell (measured 2026-09-23), but not through this rule: 55.1 s
    without a downloader, 58.4 s without a pipe. That is X-55's quote-dense
    class. It is not filed as a row in this closeout (operator scope).
  * **Stale citations.** `lib/sdk_gates_template.py:3124-3129`, cited in this
    row and in `cost-guard-raw-string-soundness`, predates #116. The five call
    sites are in `_scan_install_line` and now call `_pipe_to_shell` on the same
    five derived strings. Name the code, not the line.
  * **Out of scope, held by the operator.** The pre-merge review reported
    pre-existing findings outside this item. They are not filed here.
  * Ledger entry 48, `pipe-rule-url-pipe-cubic-2` (attempt 2).
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
    [pre-#116 line numbers; see this row's 2026-09-24 layer]
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
  above. Remove the arm overlap and this axis is linear; [REFUTED
  2026-09-23: re-measured on `ba6330b`, after #92, the axis is still cubic; see
  the 2026-09-24 layer at the top of this row] a cap bolted on top of a
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
  **[2026-09-24] RE-MEASURED AFTER PR #116, AND THE HALVING IS NOT THIS
  AXIS.** SDK dependency-gate, CPU, 20,480 B, each figure one run: with a
  one-start prefix `curl u `, `ba6330b` 9.996 / 10.032 s and `696d699`
  10.083 / 9.999 s (1.00×); with this row's two-start prefix
  `curl http://e/i.sh `, `ba6330b` 19.902 s and `696d699` 10.131 s. The halving
  is the second downloader start (`http` inside the URL) that #116 removed, not
  a change to this axis. The 341.645 s cap figure above predates #92 and #116
  and was not re-measured.


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

- **[ready] x54-wrapper-cost-residual-fallback-head-loop** · `CODE` · eligible: **yes**
  **FILED 2026-09-11 at step 10 by `x54-arg-scanner-quadratic-and-fork`, found by
  its step-3 review.** A PRESERVED COPY of the hot site the completer fix removed
  survives in the SAME emitted hook: the unguarded fallback head loop still does a
  per-token `_cand` append followed by a per-token `HEAD` rescan — the coupled
  O(n²) pair `docs/deferred-backlog.md`'s X-54 row measured at 96.0 s → 47.8 →
  31.3 → 4.5 in its own ablation. Byte-unchanged across `8c2fc35 → 8cc107f →
  HEAD`. **Unreached on the shapes measured so far** because the primary loop
  finds the head first; it runs if a completer member is ever MISSED, which
  `lib/cmdpos.py` records as having already happened once. Name the code, not the
  line.

- **[ready] xp-write-growing-string-append** · `CODE` · eligible: **yes**
  **FILED 2026-09-11 at step 10 by `x54-arg-scanner-quadratic-and-fork`.** A
  second growing-string append of the B4 / X-50 / X-52 shape, OUTSIDE the argument
  scanner and in the same emitted hook: `_XP_WRITES="$_XP_WRITES $_XP_K "` in both
  `_xp_write` and `_xp_cap`, single-level with no `_CS_WIN` flush, driven five
  times per token inside the D20 stage walk and later substring-scanned inside
  another loop. **Reachable by a cap-legal `curl http://x | tee f1 f2 … fN`**, i.e.
  a shape the X-54 payloads never touched — cell D of that item's ablation says
  nothing about it. NOT MEASURED YET: measure before assuming it crosses.

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
  [pre-#116 line numbers: the five call sites are in `_scan_install_line`, and
  since PR #116 they call `_pipe_to_shell` on these same strings]
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

- **[ready] protocol-doc-snapshot-retire** · `EMITTED` · eligible: **yes**
  · full ceremony · **freeze exception required — next free number is 80**
  · scope `Bootstrap-Protocol-v2-{0,2,4,5}-0.md`,
  `Bootstrap-Protocol-Companion-v2-{0,2,4,5}-0.md`, `lib/`, `tests/`,
  `docs/changelog.md`
  **FILED 2026-09-22 by operator decision, taken with the blast radius already
  measured. The decision is: DELETE all eight pre-2.8.0 PRD/Companion files and
  REPOINT every citation, including the v2-0-0 hook citations that freeze
  exception 15 deliberately froze — which this item therefore RETIRES, and must
  say so at every surface that records it.** Git history keeps the content; the
  files were introduced by `git mv`-preserving commits and `git log --follow`
  still reaches the 2.0.0-era ones. **No protocol doc has ever been deleted in
  this repo's history** (`git log --diff-filter=D -- 'Bootstrap-Protocol-*.md'`
  is empty), so this is unprecedented and wants its plan reviewed before step 4.
  **WHY IT IS `EMITTED` AND NOT `DOC`:** `lib/templates.py` cites these files by
  name inside bodies that ship. `lib/templates.py:3150` sits in
  `_assumption_ledger`, which `lib/installer.py:188` writes to
  `.claude/steering/assumption-ledger.md` in EVERY fixture; `:7299` is a runtime
  `echo` in the emitted `auto.sh` telling the operator to
  "Implement the dispatch loop per Bootstrap-Protocol-v2-2-0.md Phase 9.7".
  Repointing those moves emitted bytes → **five aggregate golden digests
  re-baseline** (three in `test_greenfield_golden.py`, two in `test_retrofit.py`).
  Action counts do NOT move — no path is added or removed — so a moved count is
  **E5**, not an expected consequence.
  **THE CITATION CENSUS, counted by command 2026-09-22 (call sites, not files):**
  65 protocol-doc filename citations in `lib/` + `bin/` — v2-0-0 **41**,
  v2-2-0 **13**, v2-4-0 **7**, v2-5-0 **4**, and only **6** to the live v2-8-0.
  The 41 v2-0-0 ones spread over seven files, `lib/prd_heuristics.py` alone
  carrying 19.
  **WHAT BREAKS, PER FILE — two suites CRASH rather than fail, and a crash
  prints no count at all:**
  * `v2-0-0.md` → **CRASH** `test_ic_gate.py:248` (unguarded `open().read()`,
    asserts `"[2.1.0 update — substrate OPERATIVE]"`) and **CRASH**
    `test_doc_citations.py` (`FROZEN_V200` at `:77`, read at `:186`).
  * `v2-5-0.md` → **CRASH** `test_interview.py:584`, killing all 109 checks.
  * `v2-2-0.md` + its Companion → `test_usage_limit_contract.py:274-277` FAIL
    (`os.path.isfile`). `v2-4-0.md` + its Companion → `test_installer.py:667-670`
    FAIL, same shape.
  * `Companion-v2-0-0.md` and `Companion-v2-5-0.md` → **nothing.** No test, no
    `lib/`, no `bin/`, no glob, no digest. The only two that are free.
  **THE CASCADE THE FIRST PASS WILL MISS.** Deleting `v2-0-0.md` *and* dropping
  the two `FROZEN_V200` rows to stop the crash then fails
  `test_doc_citations.py` **Section 4**, whose `SCAN` over `git ls-files`
  demands a table row for every live `…md:NNN`. Two live `v2-0-0.md:1336`
  citations sit at `test_goal_evaluator_keys.py:4` and
  `test_greenfield_golden.py:482` and are in neither `HISTORICAL` nor
  `HISTORICAL_LINE_MARKERS`. **So deleting one file needs edits in four.**
  **ALREADY SETTLED, SO THE NEXT SESSION DOES NOT RE-DERIVE IT:**
  * **The DS-01 drift guard CAN be re-pointed without loss.** `test_interview.py`
    extracts the design-steering question byte-for-byte from `v2-5-0.md` as a
    drift guard on `lib/interview.py`, which calls that doc "the SOLE verbatim
    source". Measured: the question line occurs **exactly once** in BOTH
    `v2-5-0.md` and `v2-8-0.md`, both extractions are **690 chars and
    byte-identical**, and both equal `IV.DESIGN_STEERING_QUESTION`. Re-point to
    `v2-8-0.md` and the guard survives intact. **Do not delete the guard.**
  * **The cited SECTIONS survive in the live PRD**, so repointing is semantically
    sound and not merely dangling-avoidance: Phase 9.7 ×20, Phase 9.5 ×37,
    "Recovery & State" ×17, `exit_reason` ×32 all present in `v2-8-0.md`.
  * **Golden digests do NOT hash the docs.** Both digest functions hash only the
    emitted plan's actions; the docs move a digest ONLY via `lib/templates.py`.
  * **Runbook §0's glob is safe.** `Bootstrap-Protocol-*.md` still expands (the
    v2-8-0 pair survives) and the assertion is "must print nothing", so removing
    files can only shrink the search set. Coverage narrows; nothing breaks.
  **SUITE COUNTS WILL MOVE** — roughly a dozen assertions disappear — so every
  prose "9,977" goes stale in the same commit. The "25 suites" claims do NOT
  move: no test file is added or removed.
  **CHEAPEST FEEDBACK LOOP, measured:** `test_doc_citations` 0.10 s catches every
  citation defect; the full rename/delete set is
  `doc_citations + usage_limit_contract + worktree_command_compat + interview +
  ic_gate + greenfield_golden + retrofit + installer` ≈ **14.2 s**, versus 276 s
  for `bin/run-tests`.
  **NOT IN SCOPE, decided the same day:** the PRD keeps `**Version:** 2.8.0` and
  its filename. A version bump is a *separate* axis — it would move
  `lib/installer.py:37`, `lib/templates.py:18`, `plugin/plugin.json`, two README
  lines and both doc headers together, and it is not what retiring a snapshot
  requires.

- **[ready] x54-wrapper-emitted-comments-stale** · `EMITTED` · eligible: **yes**
  **FILED 2026-09-14 at step 10 by `x54-wrapper-cost`, found by its step-8.3
  review.** The shared-header comments shipped in all 13 emitted hooks describe
  the walk from BEFORE this fix: `_cs_isinv`'s seed comment says it reads
  `$_CS_TAIL` (it now seeds `$_CS_INVPEND`), and the exhaustion comments name
  only the `_seen=1` entrance (there are two — the `_seen=0` head-transparent
  tail this item added rows for). The new `_CS_INVPEND` block also omits the
  54.33 s jump-shape and calls the length half the "adjacent-run class" where
  the jump half is adjacent runs too. Left in `x54-wrapper-cost` deliberately: a
  comment fix in `lib/templates.py` re-baselines FIVE golden digests
  (greenfield default/full_autonomous/design_steering + retrofit service/agent)
  and needs its own freeze exception, so it must not ride a cost PR. Name the
  code, not the line.

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

- **[ready] hook-deny-fixture-test-gate-ci-mirror** · `TEST-CONTRACT` · eligible: **yes**
  **FILED 2026-09-14 by `x54-wrapper-cost`, named by its step-7 completeness
  critic.** Every fixture in the shared-header cost/verdict tests sets
  `commands.test`/`ci_local` to `true`, so `test-gate` and `ci-mirror` never
  DENY, and no row ever observed either hook's verdict on the quoted-flag shapes
  on the whitespace-dropping candidate — only `dependency-gate` and
  `spec-gate-commit` (FAIL_CLOSED) were exercised. Add a fixture with `false`
  so those two `PreToolUse`/`Bash` hooks can deny, then a ROW-0-style verdict
  row for each. Small, no emission moves.

- **[ready] mutation-expect-differential-rows** · `TEST-CONTRACT` · eligible: **yes**
  **FILED 2026-09-14 by `x54-wrapper-cost`, named by its step-7 critic.** The
  five quoted-run rows `b8b15df` added to
  `tests/test_substrate_differential.py` read `2/0/2` on the whitespace-dropping
  candidate — they DO catch it — but no mutation set names that suite in any
  `expect`, so the gate never scores them. Add `test_substrate_differential.py`
  to `array-pend-drops-ws`'s `expect` (or a note that the suite is deliberately
  outside the gate). Belt-and-suspenders: `array-pend-drops-ws` is already caught
  in two suites; this makes the differential's coverage gate-visible.

- **[ready] e8-detector-counts-its-own-string** · `MEASUREMENT` · eligible: **yes**
  **FILED 2026-09-11 by `x54-arg-scanner-quadratic-and-fork`.** The runbook §6
  E8 detector is `grep -c '"model_refusal_fallback"'` over the session
  transcript, and it counts **its own command** plus the runbook's §4 text —
  which every session is REQUIRED to read. The S0 baseline command lands in the
  transcript AFTER the baseline is taken, so the delta is guaranteed ≥1 at the
  first check of every session, before any fan-out. Measured this session: **14
  literal occurrences, 0 real events.** The delta fix already applied once did
  not close this. **The sound test is the record's own shape** — `type ==
  "system"` and `subtype == "model_refusal_fallback"` — calibrated here against a
  known-positive session (`339bedbb`) so the negative is not vacuous.

- **[ready] e8-detector-blind-on-sidechains** · `MEASUREMENT` · eligible: **yes**
  **FILED 2026-09-22 by `prefix-run-language-guard`. This is the FALSE-NEGATIVE
  half; `e8-detector-counts-its-own-string` above is the false-POSITIVE half, and
  they are different defects.** Runbook §6 says E8 reads the **top-level**
  transcript because §4 shows that is the only place a
  `model_refusal_fallback` is recorded. The premise is refuted in the direction
  that matters: **a sidechain reroutes with NO event at all**, so a fan-out lens
  that latches degrades **silently and undetectably** — §4 already records
  **0 of 14** events on a sidechain against **8,907** Fable sidechain turns in
  this repo. A clean E8 delta therefore says nothing whatever about the agents,
  only about the driver. **And `model_refusal_no_fallback` is invisible to the §6
  grep entirely**, which matches only the `_fallback` spelling. The census that
  does work is per-file `message.model` over the workflow's own agent
  transcripts; this item used it and should not have had to invent it.

- **[ready] mutation-gate-wall-clock-unbudgetable** · `MEASUREMENT`
  · eligible: **yes**
  **FILED 2026-09-22 by `prefix-run-language-guard`.** The gate is a **blocking
  measurement of unbounded duration**: **6,412 s** at 53 entries on an idle box,
  and it grows with the set. Three consequences were paid inside one item.
  (1) **It cannot live inside a subagent** — a REV 5 gate agent started the run,
  correctly refused to end its turn, and died at `signal 15` when its lifetime
  expired. Only the top level outlives it, via a background task.
  (2) **It cannot run beside a fan-out** — a contended wall-clock red inside its
  private checkout can flip the control to CONTROL-FAIL and void the whole run.
  (3) **Any prose fix restarts it.** Two runs were started and stopped in one
  session because an edit landed after they began; the third ran on the tree that
  shipped. Nothing in the runbook budgets for this, and §2's ceremony sizing does
  not mention it.

- **[ready] prefix-run-per-dimension-mutation-coverage** · `TEST-CONTRACT`
  · eligible: **yes**
  **FILED 2026-09-22 at step 10 by `prefix-run-language-guard`, promised in that
  item's PR body and C3 commit message.** A mutation pins only the narrowing its
  own `find`/`replace` makes. **"Gated" is a per-construct word; fail-opens are
  per-dimension** — a set can pass 52/52 while a DIFFERENT member of a construct
  it calls covered walks through. Two are measured and were re-measured on the
  real emitted hooks during that item's live-PR review: the `_DIALECT` head class
  narrowed to exclude **digits** (`9x/env pip install evil`) and the fd class
  `[0-9]` narrowed to drop **`3`** (`3>x pip install evil`) each flip deny →
  **ALLOW** on both substrates with every verdict row of
  `tests/test_substrate_differential.py` green. Neither is a hole in the shipped
  tree; both are dimensions nothing would catch a regression in.
  **WHAT THE DESIGN HAS TO CLEAR, measured rather than assumed:**
  * **One mutation per dimension does not scale.** The gate is **6,412 s** at 53
    entries and grows with the set. See
    `mutation-gate-wall-clock-unbudgetable`.
  * **A row loop generated from the tuple under test cannot pin that tuple's
    members** — the loop shrinks with it. A sweep must iterate a FIXED literal
    alphabet or member list.
  * **Sizing, regex-level and NOT a hook verdict:** excluding one printable
    ASCII character from the `_DIALECT` head class and asking whether
    `curl u | <c>x/sh` still matches, **89 of the 94** printable non-space
    characters flip it (all but `$`, backtick, `(`, `{`, `|`; `(`/`{` are already
    excluded). The shipped `[head_upper]` row can catch the exclusion of `A`
    only.
  * **NOT MEASURED AT ALL:** the arm C `(_asg|_red)` alt-drop at `lib/cmdpos.py`
    :804, and the consumers' own constructs — `runners_regex`,
    `install_head_tail`, `redirect_norm`.

- **[ready] doc-citations-need-anchor-text** · `TEST-CONTRACT` · eligible: **yes**
  **FILED 2026-09-11 by `x54-arg-scanner-quadratic-and-fork`.**
  `tests/test_doc_citations.py` pins citations by LINE NUMBER, and
  `docs/changelog.md` is append-at-top, so every changelog entry breaks every
  citation into it. Inside that ONE item the policy doc's citation drifted three
  times: **1275 → 1333 → 1335 → 1344**. The suite caught it each time, which is
  the harness working — but the format guarantees the churn. Anchor-text
  citations would end it. This is the repo's own "name the code, not the line"
  rule, applied to a surface that has not learned it.

- **[done 2026-08-26] x54-deny-shape** · `MEASUREMENT` · PR #94, merge `69395f1` · on `f4cc8c8`, emitted
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

**`prefix-run-language-guard` PR #113 `adec611` — the three guards PR #92 proved
necessary and then stripped, each landed with a red row of its own and a mutation
set that proves it load-bearing.** Closed 2026-09-22. **No freeze exception** —
the change emits no byte, moves no golden digest, and needs none. Graded
**`harmful`** — see the ledger; a status claim that the act of opening the PR
falsified reached origin in the PR body and was caught by this item's own step-7
review of the LIVE PR, before merge.

**ONLY ONE THIRD OF IT IS CODE, AND THAT THIRD IS THREE LINES.** `lib/cmdpos.py`
+3: `not_words()` materializes `words` with `tuple()` and raises `ValueError` at
build time on any word failing `w.isascii() and w.isalnum()`. A raise, not an
assert, so `python -O` cannot strip it. Measured on the parent tree with the word
`a[b`: bash `[[ =~ ]]` returns **2** — which the emitted hooks read as a
NON-match — and Python's `re.compile` raises. `ALL_PREFIXES` is the only word set
passed in and all **20** entries pass, so the emitted regex is byte-identical and
no golden digest moves. **Guards 1 and 3 needed no code at all**: what they
lacked was a check that could go red, and that is the other two commits.

**THE RED CAME FIRST AND IS PASTED INTO THE COMMIT.** `tests/test_composition.py`
+77 and `tests/test_substrate_differential.py` +481 land the Guard 2 predicate
rows and the verdict rows for the command-position language that `prefix_run()`
and `interpreter_word()` build. `python3 tests/test_composition.py` on that
commit is **157 passed, 6 failed** — exactly the six predicate rows — and
**163 / 0** on the next.

**THE GATE BOUNDS REMOVABILITY, NOT ENUMERATION, AND THE RECORD SAYS SO IN THOSE
WORDS.** `.claude/mutations/prefix-run-language-guard.json` (+509) carries **52
bypasses and 1 control**, registered by `sha256` in `_REQUIRED_SETS`
(`tests/test_trust_ramp.py` +30). **MERGE GATE: PASS — 52/52 bypasses turn a
NAMED check red; 1 control escaped as required**, SET-SHA256 `fd60c5a4…`, rc 0 in
**6,412 s**, zero ESCAPED / INCONCLUSIVE / PARTIAL / ROTTED. It ran at tree
`f1547686`, which **is** `d66f4b1`'s root tree, so the run binds the exact bytes
that merged — a content-addressed chain, not a four-day-old proxy.

**PER-DIMENSION COVERAGE IS OPEN, AND SHIPPED OPEN BY OPERATOR DECISION.** A
mutation pins only the narrowing its own `find`/`replace` makes; other members,
alternatives and bounds of the same construct are NOT pinned. Two escapes are
measured and disclosed in the PR body, and both were re-measured end-to-end
during the live-PR review on the real emitted hooks: the `_DIALECT` head class
narrowed to exclude **digits** (`9x/env pip install evil`) and the glued-redirect
fd class `[0-9]` narrowed to drop **`3`** (`3>x pip install evil`) each flip
deny → **ALLOW** on BOTH substrates with every verdict row of
`tests/test_substrate_differential.py` green. **Neither is introduced here** —
both are unpinned dimensions of guards `main` already carried, so what is open is
the COVERAGE, not a live hole in the shipped tree. Filed as
`prefix-run-per-dimension-mutation-coverage`.

**THE VERDICT DID NOT MOVE.** `main` stays **NOT PRODUCTION READY** on leg (a).
This item makes the command-position language claim *checkable* — it was not
before, and the row this entry replaces recorded a one-word mutation
(`not_words(ALL_PREFIXES + ("foo",), _seg)`) flipping an install deny → ALLOW on
both substrates while **9,826 of 9,831 checks stayed green**. But a boundary is
not proven by making its absence visible. Leg (a) still stands on **`x37-class-b`**
and **`install-tail-path-scan-quadratic`**, neither touched here. **A holds 8
`[ready]` rows** after this closure — counted from the section, not from memory.

**THE ROW THIS REPLACES NAMED 3 OF 5 SCOPE GLOBS** (`lib/cmdpos.py`,
`tests/test_composition.py`, `tests/test_substrate_differential.py`), omitting
`.claude/mutations/prefix-run-language-guard.json` and `tests/test_trust_ramp.py`
— a round-5 MINOR, discharged here rather than carried: the shipped scope is
those **five** files, `git diff --name-only 0e6108c..d66f4b1`, **+1,100 / -0**.

**RESIDUALS FILED:** `prefix-run-per-dimension-mutation-coverage`,
`e8-detector-blind-on-sidechains` and `mutation-gate-wall-clock-unbudgetable`
(all under Measurement residuals, below). **Record-only, noted not filed:** the
merged `#104` and `#105` carry commits attributed to **Opus 4.8** against runbook
§4's "Opus 5 drives every step" — true of those items, not of this one, and not
this item's to fix.

**`x54-wrapper-cost` PR #104 `93af8c6` — the invoker walk resumes instead of
restarting per quoted run.** Closed 2026-09-14. Freeze exception **79**. Graded
**`harmful`** — see the ledger (a stale mutation-count reached origin and was
caught by the item's own step-8.3 review before merge). Closes the **wrapper**
member of the X-54 cost class; with the completer (77) and argument-scanner (78)
members already closed, **all three X-54 members are now closed** — but the CLASS
is not, and the leg is not proven, by closing members of it.

**THE STEP-8 STORY IS THE COVERAGE STEP 7 PROVED MISSING.** The first-round PR
excluded two edits from its mutation set as "unreachable" / "no shape found";
step 7 refuted both and re-derivation confirmed a third cost blind spot. All
three are bypasses now: `scan-restart-no-pend` (`_cs_scan`'s separator branch
fires at recursion depth over the un-scrubbed `_CS_EXTRA`) and `reset-no-pend`
(the `$'..'`-resolved second `cmd_segments` scan reuses a stale resume point)
each flip a cap-legal DENY→ALLOW → ROW 0 `0h`/`0i`/`0j`; `other-arm-restarts`
restores the quadratic on decider padding (`sudo`+2,642×`'a'` → killed at 60 s)
which the `'{'`-padded rows 1/3 cannot see → decider-padded ROW 6. Mutation set
`.claude/mutations/x54-wrapper-cost.json` **9 → 12 bypasses**, SET-SHA256
`ae0d97d3`, **MERGE GATE: PASS 12/12 + control**, re-run on the merged-fix bytes
(`f102b4a`). A single-property runtime pin (ROW 5, suffix-of-tail) catches the
position drops; the `_CS_INVSEEN` ways (0c/0g) are ROW 0's — complementary nets.

**THE VERDICT DID NOT MOVE.** `main` stays **NOT PRODUCTION READY** on leg (a).
The X-54 wrapper member closed, but leg (a) still stands on **X-37 Class B** and
**`install-tail-path-scan-quadratic`** (both separate, neither an X-54 member),
and a class is not closed by closing its members. `docs/production-readiness.md`
gains a dated layer saying exactly that. **NOT CLOSED at X-55's recorded size:**
the jump shape at 80,022 B denies in 54.33 s (1.10× under the ceiling); the
adjacent-run/length half is open and the fix costs there.

**RESIDUALS FILED:** `x54-wrapper-emitted-comments-stale` (C, below),
`hook-deny-fixture-test-gate-ci-mirror` and `mutation-expect-differential-rows`
(Measurement residuals, below). Two one-line edits stay OUT of the set as
findings, not proofs — `lazy-pend-dropped` and `ops-append-pend-unguarded`, no
shape found. Record-only: `088c8c4`'s message says "Seven sites"; the emitted
delta touches nine.

**`x54-arg-scanner-quadratic-and-fork` PR #102 `01976cc` — three per-token costs
out of the argument scanner.** Closed 2026-09-11. Freeze exception **78**. Graded
**`harmful`** — see the ledger. Closes the **argument-scanner** member of the
X-54 cost class; the **wrapper** member is now the only one of the three left.

**THE QUEUE ROW NAMED TWO SITES AND THERE WERE THREE.** The third — `is_approved`
scanning the project's whole approved list per token, with no early exit on a
miss — was found by the step-3 review, and it is the one that scales with a
variable the OPERATOR sets in `deps.md` rather than one the attacker supplies.
Against the suite's one-package fixture an O(K) scan and an O(1) lookup are
indistinguishable, so the item's first measurement concluded the two named sites
were the whole defect and was **wrong**: with only those two fixed, a
200-package `deps.md` still crossed the ceiling at every contention factor this
repo has recorded. **A row that varies only the attacker's input cannot see a
cost whose second factor is the adopter's own configuration** — that is the
reusable half of this item.

**THREE TEST ROWS, BECAUSE TWO WERE NOT ENOUGH.** Row 5 re-based from `rc == 124`
to `rc == 2`; row 6 added at an 800-package fixture, the only row that sees the
`is_approved` site; row 7 a RATIO against a no-head control, the only row that
sees the fork and the append — reverting either alone leaves 43.3 s / 26.2 s,
INSIDE the ceiling and invisible to any rc. Mutation set
`.claude/mutations/x54-arg-scanner-quadratic-and-fork.json`, **MERGE GATE: PASS
5/5 + 1 control escaped**, re-run on the merged bytes.

**THE VERDICT DID NOT MOVE.** `main` stays NOT PRODUCTION READY on leg (a). This
closes one of the two X-54 members that were open; the leg needs
`x54-wrapper-cost` and `install-tail-path-scan-quadratic` as well, and X-37 Class
B is untouched. `docs/production-readiness.md` gains a dated layer saying exactly
that.

**RESIDUALS FILED:** `x54-wrapper-cost-residual-fallback-head-loop` and
`xp-write-growing-string-append` (both above), plus two harness defects in
**Measurement residuals**.

**`x54-completer-cost` PR #98 `8cc107f` — the install-head loop stops evaluating
`HEAD` once per completer.** Closed 2026-08-31. Freeze exception **77**. Never a
queue row: it was taken directly off the **X-54** backlog row, which is why its
two surviving members had to be filed as rows above rather than found there.
**Eight commits** (`git rev-list --count 8c2fc35..5b2b6ca`; the sentence below names eight shas), and the shape of them is the record: `b9df507` step-4 red,
`dc268d0` the fix, `ef99fbc` a step-8 correction that DIVERGED (23 findings →
32), `521724a` the operator-ruled STRIP, `56421e9` a solo re-review, `e6a1a03`
and `fd4c90e` and `5b2b6ca` the three fan-out rounds. **The verdict did NOT
move** — `docs/production-readiness.md` untouched, `main` stays NOT PRODUCTION
READY on leg (a); X-37 unaffected. What moved is the X-54 row's status cell:
the **completer** member is closed, the **wrapper** and **argument-scanner**
members remain and now have rows.
**Measured on the emitted hooks**, this tree vs `origin/main`, idle, serial:
completer `x`×40,951 **106.51 s KILLED → 5.12 s DENY**, non-completer control at
the identical byte count 4.55 → 4.50 s. 11,000 differential commands 0 diffs;
190,494-case census 0 violations; action counts unchanged at 57/69/59 and 79/93.
**AND THE SUITE CAN SEE THIS CLASS NOW:** `tests/test_issue_fixes.py` applies
the production 60 s ceiling by CANCELLATION for the first time in this repo
(`subprocess timeout=60` -> rc 124). The ceiling was already BOUNDED before this
item: the parent `8c2fc35` asserts elapsed time on the emitted hook at
`tests/test_issue_fixes.py:4108-4119` and `:4172-4181`, and a SIGALRM cap at
`tests/test_substrate_differential.py:4198-4240`. What is new is enforcing it.
**Graded `harmful`** — see the ledger entry. Four rounds of false prose reached
origin, and so did a FAIL-OPEN: closing the head-LESS completer padding opened a
head-BEARING one on the same loop (`pip install evil ` + `x `×34,000 — rc 2 in
57.65 s on `8c2fc35`, rc 124 on `8cc107f`). Round 3 reported it as a BLOCKER; a
1–1 refuter tie was scored as refuted and it was dropped. **A head-bearing fail-open remains open on `main`; PR #99 (unmerged) narrows but
does not close it, and the residue is tracked as `x54-arg-scanner-quadratic-and-fork`.
See PR #99,
which was under adversarial review when this was written** — until it lands, `main`
carries a fail-open this item introduced.

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

**[2026-09-24]** `pipe-rule-url-pipe-cubic` attempt 2 merged as a NARROWING,
**PR #116, merge `696d699`**, and its row stays in A; see the row's 2026-09-24
layer. **THE VERDICT DID NOT MOVE.** `docs/production-readiness.md` is untouched
by this closeout (runbook step 10 amends it only when the verdict moves), and
`main` stays **NOT PRODUCTION READY** on leg (a). **COUNTED OFF THE SECTION
BULLETS, NOT FROM MEMORY: A = 8 `[ready]`, B = 8 `[ready]` + 1 `[blocked]`,
C = 7 `[ready]`, measurement residuals = 9 `[ready]`.** This closeout adds and
removes no row.

**[2026-08-31]** `x54-completer-cost` closed, **PR #98, merge `8cc107f`** —
**and it introduced a fail-open that is not yet fixed on `main`.** Closing the
head-LESS completer padding opened a head-BEARING one on the same loop; PR #99
(`fix/x54-head-bearing-fail-open`) NARROWS but does not close it; the residue is
tracked as `x54-arg-scanner-quadratic-and-fork`. State of that PR at the time of
writing: under adversarial review.
`x54-head-bearing-fail-open` is therefore live work, not a filed residual.
**THE VERDICT DID NOT MOVE.** `docs/production-readiness.md` is untouched by this
work and `main` stays **NOT PRODUCTION READY**. It is not X-37, and the leg it
does touch — leg (a), the emitted gates as a security boundary — it only
narrows: the X-54 row's **completer** member is closed, its **wrapper** and
**argument-scanner** members are not.
**COUNTED OFF THE SECTION HEADERS JUST NOW, NOT FROM MEMORY: A = 9, B = 9,
C = 5, measurement residuals = 2.** A gained the two rows this work exposed
(`x54-arg-scanner-quadratic-and-fork`, `x54-wrapper-cost`) and lost none —
`x54-completer-cost` was never a queue row, so nothing moved to Done from A.
**TWO EARLIER LAYERS IN THIS SECTION ARE NOW SUPERSEDED, NOT WRONG WHEN
WRITTEN:** every layer that says the verdict has **two** remaining legs predates
2026-08-26, when C-2 was retired by disclosure (PR #96, merge `75eef0a`); there
is **one** security leg now. And the **"A holds 8"** paragraph below predates
both that retirement and `prefix-run-assignment-wrapper-overlap`'s closure, so
its list names two rows that are no longer open. Read the count in this layer.
**`docs/production-readiness.md` is 13 commits behind its last edit (`6aefb6b`,
2026-08-26) and no row covers that** — `priority-reading` (C) owns only its
stale Snapshot header. That is a smaller gap than the 70 the 2026-08-25 layer
records, because the C-2 retirement re-based the document; it is not closed.

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

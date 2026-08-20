# PLAN — `prefix-run-cost-residuals` · rev 1 · 2026-08-20 local `+0800`

**Class `CODE`.** Full ceremony: step-3 review before step 4, adversarial
fan-out at step 7, ledger entry, checkpoint.

> **LAYERED DOCUMENT.** Corrections are APPENDED as new revisions. Never edit a
> revision in place; the LAST revision governs. Untracked by design
> (`.claude/readiness-runbook.md:101`).

---

## 0. S0 PREFLIGHT, RECORDED

```
tracked-dirty   []                     clean
unpushed        []                     none
suite           25 suites / 9,763 checks / 0 failed
trust-ramp      R1 DENIED, earned rung R0
E8 baseline     0 refusal-fallback events at S0
context gate    7.8% of the conservative 900k window, exit 0
branch          fix/prefix-run-cost-residuals, from origin/main @ e3f2f57
```

**S0.2 IS NOT CLEAN AND THIS IS THE DEVIATION TO READ FIRST.** Two PRs from this
runbook are open: **#77** (`fix/x37-class-b`, the documented EVIDENCE-ONLY
exception, never to merge) and **#83** (`governance/c2-work-order`, filed last
session, awaiting the operator's 9b review). The runbook's S0.2 says *no open
PRs from this runbook*. Proceeding anyway, deliberately, on two grounds:
#83 touches `.claude/readiness-queue.md` **only** — no overlap with this item's
scope — and this branch is cut from `origin/main`, which does not contain #83's
commit, so nothing stacks. **#83 still needs an operator merge and this item
does not substitute for it.**

---

## 1. THE DEFECT, QUOTED FROM THE TREE

`lib/cmdpos.py:676-693`, the body of `prefix_run()` as it ships at `e3f2f57`:

```python
676    # the four arms that do not carry the wrapper word list
677    nonabs = ("([({] *"
678              + "|[0-9]*[<>]+ *" + nonspace + "+" + space
679              + "|[A-Za-z_][A-Za-z0-9_]*[+]?=" + nonspace + "*" + space
680              + "|(" + alt(KEYWORDS) + ")" + space + ")")
684    wrapper = ("((" + nonspace + "*/)?(" + alt(ALL_PREFIXES) + ")"
685               + "|(" + alt(NAMED_GROUP_HEADS) + "))")
691    return (nonabs + "*"
692            + "(" + wrapper + space + "(" + nonspace + "+" + space + ")*"
693            + "([({] *)*)?")
```

Two of those lines are **internally ambiguous** — they accept the same input
along more than one parse — and on a FAILING match a backtracking engine walks
every parse:

* **`:678`, the redirect arm.** `[0-9]*[<>]+ *` + `nonspace+` lets `[<>]+` and
  the target run consume the same `<`/`>` characters. `2>>o ` has two parses
  ending at the same offset, so n such tokens cost ~2^n.
* **`:692-693`, the trailing group.** `(nonspace+ space)*` and `([({] *)*` both
  match `{ `, so the boundary between them can fall at any of m+1 places in a
  spaced-brace run; and `nonabs*` at `:691` can hand off to the wrapper at any
  of k token boundaries, because `A=1/env ` matches the assignment arm **and**
  the path-prefixed wrapper arm at once. Cost is the product, ~k·m².

`lib/sdk_gates_template.py:1635-1636` carries a third instance of the same
defect class, spliced next to the one PR #81 removed:

```python
1635  _GIT_VERB_TMPL = (r"(?:^|[;&|()`\\n])\\s*" + _CMD_PFX_RE + r"(?:\\S*/)?git"
1636                    r"(?:\\s+-[Cc]\\s+\\S+|\\s+-\\S+)*\\s+%s(?:\\s|$)")
```

A `-C` token is consumable by BOTH arms of that star — as a flag with an
argument, or as a bare flag — so a run of them has Fibonacci-many parses,
~1.62 per added token.

---

## 2. RE-MEASURED, NOT RECOVERED

The queue row orders a re-measurement because two of the four stripped
descriptions were wrong. Harness:
`scratchpad/cost/remeasure.py`, run against a fresh probe install of `e3f2f57`.
Emitted artifacts on both substrates; SDK is min-of-3 `process_time` through
`_GATE_FACTORIES`, shell is min-of-3 wall clock of the real hook subprocess.

**Calibration, all three legs, printed by the harness itself:** a known
catastrophic regex is reported as capped (the instrument can go red); benign
payloads answer in 0.000 s SDK / ~0.02 s shell; and PR #81's own landed cost row
(`env `×27) answers in 0.001 s, so the harness agrees with the suite on a case
whose answer is already known.

| # | class | payload | bytes | jump | SDK | shell | verdicts |
|---|---|---|---|---|---|---|---|
| 1 | wrapper × spaced-brace | `A=1/env `×64 + `{ `×800 | 2158 | 0 | **> 45 s capped** | 0.193 s | deny / deny |
| 2 | length axis, glued braces | `{`×19200 | 19247 | 0 | **21.07 s** | **7.23 s** | deny / deny |
| 3 | redirect arm | `2>>o `×24 | 141 | 0 | **> 45 s capped** | 0.031 s | allow / allow |
| 3b | redirect arm + install tail | `2>>o `×22 + tail | 156 | 0 | **32.60 s** | 0.032 s | deny / deny |
| 4 | `_GIT_VERB_TMPL` flag star | `git ` + `-C `×32 + `zzz` | 103 | 0 | **1.29 s** | 0.015 s | allow / allow |

Growth, measured rather than asserted: class 1 is 0.815 → 6.44 → capped
(~cubic); class 2 is 1.33 → 5.29 → 21.07, ×4 per doubling on the SDK and
0.52 → 1.89 → 7.23, ×3.8 per doubling on the **shell** (both quadratic); class 3
is 1.53 → 6.14 → 24.45 → capped, ~2× per token; class 4 is 0.004 → 0.028 →
0.188 → 1.29, ~1.62× per token, against a same-length `-x ` control that is
**0.000 s at every size** — so the cost is the arm overlap alone.

**Every payload is invisible to `_cost_guard`**, checked against the EMITTED
constants rather than a copy: all are far under `_CMD_MAXLEN` 81920 and carry
**zero** `_JUMP_BYTES` (`()"'` + backtick + `$`; `{` is not among them).

### 2a. Two corrections to the queue row, both measured

* **Class 3's bare payload is `allow / allow`, as the queue says — and that
  makes it WORSE, not better.** At 141 bytes it burns the SDK's entire 60 s
  budget on a command both substrates permit. With an install tail it is
  `deny / deny` at 156 bytes and 32.6 s, i.e. a deny that arrives after the
  hook has been cancelled.
* **Class 2 is NOT brace-specific on the shell side.** Shell controls at 9,600
  characters: `a`×9600 glued 0.331 s, `{`×9600 glued 1.859 s, `{ `×4800 spaced
  0.929 s, and **`x `×4800 ordinary spaced words 3.253 s** — the most expensive
  of the four. The shell's cost is its walker being superlinear in token count,
  which is X-36l's known property, not a brace class.

### 2b. WHERE THE TIME GOES — attributed per compiled pattern

`scratchpad/cost/attribute.py` wraps `re.compile` before the emitted module
loads, so **patterns compiled at call time are counted too** — the carrier class
a module-attribute scan misses, and the method error this repo made twice.

| class | share | carrier |
|---|---|---|
| 1 | 71% + 29% | `_PIPE_TO_SHELL`, then `_INSTALL_HEAD` |
| 2 | 84% + 16% | same two |
| 3 | 89% + 11% | same two |
| 4 | **99.9%** | `_GIT_VERB_TMPL % "commit"`, compiled per call |

**All four are `prefix_run()`.** Classes 1-3 are the shared `_CMD_PFX_RE`
embedded in the two dependency-gate anchors; class 4 is the same prefix run plus
the flag star. `cProfile` puts 97-99 % of every class inside
`re.Pattern.search`/`match` — **the walker is not the cost on the SDK side**,
which corrects the "quadratic tokenizer" framing the class-2 row was written on.

---

## 3. SCOPE

**In scope**
* `lib/cmdpos.py` — `prefix_run()`, and the docstring claims that justify it.
* `lib/sdk_gates_template.py` — `_GIT_VERB_TMPL` only.
* `tests/test_substrate_differential.py` — the step-4 cost rows and the
  language guard.
* `tests/test_composition.py` — language rows if the review asks for them.
* Golden/retrofit digest pins ONLY as a consequence, with a freeze exception.

**Out of scope, and named so the fan-out does not have to guess**
* The emitted prose sweep (§6). Filed, not fixed here.
* `_cost_guard`'s feature set. Widening it is a separate design item.
* Class 2. §5 says why.

---

## 4. THE CANDIDATES

Both are **exactly language-preserving disambiguations**: same accepted set,
one parse instead of many.

**B — the trailing brace run.** `:693` `([({] *)*` → `[({]*`. Spaced braces are
already consumed by the word run at `:692`; only the final space-free brace
sequence needs the dedicated arm. Removing ` *` from it makes the boundary
between the two runs forced.

**A' — the redirect arm.** `:678` `[0-9]*[<>]+ *` + `nonspace+` + `space` →
`[0-9]*([<>]` + `nonspace+` + `|[<>]+ +` + `nonspace+` + `)` + `space`. The two
cases are disjoint on whether a space separates the operator run from its
target, and in the no-space case exactly one leading `<`/`>` is taken, which is
what removes the choice.

**C — the flag star**, `lib/sdk_gates_template.py:1636`:
`(?:\s+-[Cc]\s+\S+|\s+-\S+)*` → `(?:\s+-[Cc]\s+[^-\s]\S*|\s+-\S+)*`. When a
`-C`'s argument itself starts with `-`, the two-iteration parse through the
second arm accepts the same string, so restricting the first arm removes a
duplicate parse rather than a string.

---

## 5. WHAT THIS PLAN DOES **NOT** DO

**CLASS 2 SURVIVES AND NO CANDIDATE HERE TOUCHES IT.** Measured: B leaves
`{`×9600 at 0.892 s against the shipped 0.888 s. Its mechanism is different and
is now identified: `nonabs*` can end the prefix run at each of n glued braces,
and at every one of those positions the interpreter alternation's
`\S*[$`]\S*` arm scans to the end of the token — n positions × O(n) each. That
is not an ambiguity that can be factored out; it is a genuine set of endpoints
against a genuine tail scan. **It needs a bound, not a rewrite**, and a bound is
a language change that must be validated against the corpus distribution before
anyone proposes a number.

**The shell is not the safe substrate on class 2** — 7.23 s at 19 KB, quadratic,
so ~130 s extrapolated at 81,900 B, which is *under* `_CMD_MAXLEN`.

---

## 6. FILED, NOT FIXED — THE X-51 RETRACTION HAS A THIRD MISS, IN EMITTED BYTES

A joined-line, case-insensitive sweep over `git ls-files` **and** a fresh probe
install finds the retracted sentence *"a PreToolUse timeout fails CLOSED"* still
live, in USE and not as a quoted correction, in **13 emitted shell hooks and
`gates.py`** — every customer tree — from three source sites in `lib/`
(`lib/templates.py`'s shared `_blen` prelude, `lib/sdk_gates_template.py`'s
`_GATE_EXTRA_MATCHERS` timeout comment and its `_budget_len` paragraph), plus
`lib/templates.py:6546` and `lib/cmdpos.py`'s own docstring.

`SEAM-CONTRACT-v2-0-0.md:40` states the opposite and states it as measured:
**"NO RUNTIME DELIVERS FAIL-CLOSED TIMEOUTS."** `tests/test_greenfield_golden.py`
records freeze exception 67 and its amendment as the sweep that finished the
job. **It did not.** This matters to this item specifically: the emitted text
tells a maintainer that a gate crossing its timeout is a refusal, which is the
exact reading under which every row in §2 is a nuisance rather than a bypass.

`lib/cmdpos.py`'s instance is in scope because it is the rationale for the code
being changed. The rest is an `EMITTED` change with its own freeze exception and
is **not** batched into this `CODE` item.

---

## 7. WHAT WOULD FALSIFY THIS PLAN

1. **A' or B is not language-equivalent.** Decided by exhaustive enumeration
   over token sequences, two-sided calibrated against two deliberately broken
   variants that MUST show divergences. If either candidate diverges anywhere,
   it is withdrawn — C5 flipped three live RCE rows deny→allow on exactly this
   kind of "obvious" narrowing.
2. **The cost does not move on the EMITTED artifact.** Every number above is
   measured on the emitted objects; a candidate that only improves a hand-built
   regex is measuring a different program.
3. **A benign shape regresses.** Any row in the differential, composition or
   golden suites going red.
4. **The suite cannot see the change.** If deleting the fix leaves every check
   green, step 4 has not been done — that was true of C9 and is the reason the
   language guard is mandatory before step 5.

---

## 8. OWNER DECISIONS REQUIRED

**None blocking.** Step 3's review discharges plan approval (runbook §5.1).
Two things the operator alone can settle, neither of which blocks step 4:
PR #83's merge (§0), and whether the §6 emitted-prose miss is taken as its own
item now or queued.

---
---

# PLAN — rev 2 · after LENS 4 of the step-3 review · 2026-08-20 local `+0800`

**This layer GOVERNS where it contradicts rev 1.** Rev 1 is kept unedited.

## R2.1 THREE CORRECTIONS TO REV 1, ALL MINE

1. **§0's justification for proceeding past S0.2 was FALSE.** Rev 1 said #83
   *"touches `.claude/readiness-queue.md` only — no overlap with this item's
   scope"*. **Step 10 of this item writes that same file.** The overlap is not
   absent, it is guaranteed, and it lands at step 10. The true position: the
   operator directed this attempt in-session, which is the same authority the
   9b carve-out rests on; the collision is resolved by ORDERING — either #83
   merges before step 10, or this branch rebases onto it before the queue row
   is written. **Re-check S0.2 at step 9a and say which happened.** Rev 1 §8's
   "None blocking" contradicted rev 1 §0 and is withdrawn: the deviation is
   real, it is recorded here, and the operator's direction is what carries it.
2. **§6's file count was unlabelled.** "13 emitted shell hooks and `gates.py`"
   is the count on an **ai-agent probe with all seven SDK gates**
   (`archetype: ai-agent`, `tdd_policy: required`, eval-gate on). A probe built
   from this repo's own `bootstrap.config.yaml` emits a different hook set and
   gives 12 files. **The span count is the stable number: 15 USE spans**, one
   per emitted shell hook plus two in `gates.py`. A count is a claim about a
   configuration and must name it.
3. **`_COST_ROWS` cannot carry these rows** (rev 1 implied it could). That loop
   hardcodes `dependency-gate`, asserts `deny`, and asserts the shell denies the
   same string. Classes 3-bare and 4 are **allow/allow** and class 4 is on
   `spec-gate-commit`, so three checks would pass for the wrong reason. Step 4
   adds a SECOND block. See R2.4.

## R2.2 NEW EVIDENCE SINCE REV 1 — the candidate is built and measured

A candidate tree carrying **A' + B** is at `scratchpad/cand/tree`; the diff is
three lines in `lib/cmdpos.py`.

* **Full suite on the candidate tree: `9,758 passed / 5 failed`, and all five
  are `plan digest byte-identical`** — 3 in `test_greenfield_golden.py`, 2 in
  `test_retrofit.py`. `test_substrate_differential.py` **4,178 / 0** and
  `test_composition.py` **147 / 0**. No behavioural failure anywhere.
* **BYTE SURGERY: 14 of 14 emitted code artifacts reproduce byte-exactly from
  the two substitutions alone** — all 13 emitted shell hooks and
  `.claude/sdk_gates/gates.py`. Only `.installer-manifest.json` and
  `.bootstrap-state.json` differ otherwise, which is the digest story.
* **Bash-substrate parity, in real bash, not in Python's engine:** 85,873
  candidate strings through `[[ =~ ]]`, **0 divergences** for A', B and A'B.
  Calibrated: a variant with the brace arm deleted diverges on **1,869**.
* **Candidate C, re-derived independently of the lens:** 14,762 `git` strings,
  **0 divergences**, calibration (drop arm 1) diverges on **2,578**. Cost at
  `-C `×40 goes **> 20 s → 0.0000 s**; ×36 is 8.80 → 0.0000.
* **End to end on the EMITTED artifacts, shipped vs candidate:**

| class | SDK shipped | SDK candidate | shell shipped | shell candidate |
|---|---|---|---|---|
| 1 | **> 45 s capped** | **0.168 s** deny | 0.206 s deny | 0.204 s deny |
| 2 | 21.72 s deny | 21.99 s deny | 7.26 s deny | 7.50 s deny |

  **Read the class-1 row correctly: `capped` is not a verdict.** The shipped
  SDK never produced one inside the cap; the candidate produces `deny`. Nothing
  moved from deny to allow. Class 2 is unchanged in both directions, as rev 1 §5
  predicted, and that is the honest result rather than a rounding of it.

## R2.3 A FINDING REV 1 DID NOT HAVE, AND IT IS THE BIGGEST ONE

**`lib/cmdpos.py:241-262` decides "NO COUNT FENCE" on the retracted premise.**
The paragraph reasons that crossing the 60 s ceiling is *"a REFUSAL"*, that
`FAIL_CLOSED=1` *"turns [a kill] into a DENY"*, and that *"Direction is
fail-CLOSED, and nothing realistic is affected"* — then concludes that omitting
a count fence *"is a decision rather than an omission"*.

**Under X-51's live measurement the direction is fail-OPEN**, so crossing the
ceiling is a bypass, and "nothing realistic is affected" is not the question the
decision turns on. **The design decision that leaves this item's cost class open
rests on a sentence this repo retracted on 2026-08-13.** Re-opening it is an
owner decision, not a prose edit — filed, not taken here.

Same file, further live spans: `:258`, `:1342`, `:1440`, and `:1463`.

## R2.4 STEP 4, SPECIFIED — file, shape, and the calibration it needs

`tests/test_substrate_differential.py`, a NEW block after `:4283`, reusing
`_sdk_cost`, `_COST_BOUND` (10.0 s), `_COST_JUMP`. Drafted in
`scratchpad/step4-draft.py`. Four cost rows, each carrying its
`_cost_guard`-invisibility pin, its SDK time, its verdict, and a shell control
asserted at the verdict **actually measured** rather than at `deny`:

| row | gate | payload | today | want |
|---|---|---|---|---|
| class 1 | dependency-gate | `A=1/env `×64 + `{ `×800 | capped | deny/deny |
| class 3 | dependency-gate | `2>>o `×24 bare | capped | **allow/allow** |
| class 3b | dependency-gate | `2>>o `×22 + tail | 32.6 s | deny/deny |
| class 4 | **spec-gate-commit** | `git ` + `-C `×40 | **> 22 s** | allow/allow |

**Class 4 must be sized past the bound.** At `-C `×32 it is 1.29 s, i.e. GREEN
today, which would not be a step-4 row at all. Measured sizing on the shipped
tree: ×32 → 1.33 s, ×36 → 9.23 s, ×40 → capped.

**The language guard, 15 rows, all measured deny/deny on the shipped tree
today**: the 12 in `scratchpad/step4-draft.py` plus three SPACED-BRACE rows.

**Why the spaced-brace rows are not optional — re-derived, not taken on trust.**
B moves all spaced-brace absorption onto the word run. With the word run
deleted, the SHIPPED regex still accepts `env { `, `env { { ` and
`sudo { { { ` through the trailing arm; the candidate does not. So the existing
`test_composition.py` guard — which enumerates MULTI-WRAPPER rows — no longer
covers what a future bound on that run would delete. Extend the guard **and its
`_bounded` calibration**.

**And a deletion calibration for the cost block itself**, which has none today:
revert the fix in-process and require the row to cap.

## R2.5 WHAT REV 2 STILL DOES NOT CLAIM

Class 2 is untouched. The equivalence evidence is exhaustive-over-a-bounded-
space plus real-bash differential, **not a decision procedure** — the ERE→NFA
product-BFS decider from the previous item was not preserved and would have to
be rebuilt. Three lenses are still running; their findings get rev 3.

---
---

# PLAN — rev 3 · after LENS 1 · 2026-08-20 local `+0800`

**Governs where it contradicts rev 1 and rev 2.**

Lens 1 re-derived every quotation and every number and found no wrong number in
rev 1's tables: quotations verbatim at the stated lines, all five rows within
2-20 % on a re-run, byte and jump counts exact, and all four growth series
reproduced. The derivation counts were checked independently — the redirect arm
is `2^(n+1)-1` derivations (ratio → 2.000), the flag star is exactly Fibonacci
(ratio → φ = 1.618), and the trailing group measures `k·m²` with a constant of
~1.08. **Its findings are about the HARNESS, and one of them is the exact defect
class this item exists to punish.**

## R3.1 THE CALIBRATION ROW PRINTED A NUMBER IT DID NOT MEASURE

`remeasure.py`'s POSITIVE control armed a **5 s** alarm and then formatted the
row through a helper that hardcodes `CAP * 1.5`, so it announced:

```
POSITIVE  (a+)+$ vs a*30+b ..............  >  45 s*
```

`(a+)+$` against `a`×30 + `b` costs **~40 s CPU** on this box (40.06 s
re-derived independently here; lens 1 measured 37.5 s on an idle one). **It
never crosses 45 s.** The row asserted a threshold crossing that does not
happen, in the one place in the harness whose whole job is to prove the
instrument is honest. Fixed: the alarm is 90 s and the printed number is the
measured one. Rev 1 §2's prose did not repeat the wrong number, so the plan text
was clean and the harness output was not — which is why harness output must be
read, not trusted, before it becomes the step-4 record.

## R3.2 A VERDICT PAIR REV 1 PUBLISHED AS MEASURED WAS INFERRED

Rev 1's table gave class 3 (`2>>o `×24, 141 B) as **allow / allow**. The harness
printed `capped` for that row — **`capped` is not a verdict** — and the
`allow / allow` was extrapolated from n=18/20/22. **This is the queue row's own
method rule, broken in the document that quotes it.**

Now measured, uncapped:

| payload | bytes | SDK | SDK verdict | shell verdict |
|---|---|---|---|---|
| `2>>o `×22 | 131 | **29.72 s CPU** | allow | allow |
| `2>>o `×24 | 141 | **110.22 s CPU** | allow | allow |

The inference was correct. It is now a measurement, and the number is worse than
the capped row suggested: **110 s of CPU on a 141-byte command, against a
dependency-gate that declares 60 s.**

## R3.3 TWO METHOD LINES TO STATE PRECISELY

* **The SDK cap is WALL clock (`ITIMER_REAL`) while the reported column is
  `process_time`.** On a loaded box the two diverge and a row can cap without
  its CPU time reaching the bound. Observed here: a class-2 comparison run
  concurrently with two review lenses reported the CANDIDATE as capped and the
  shipped tree as 25 s — a load artefact, not a regression. **That row is
  discarded and re-measured on a quiet box; it is not quoted anywhere.**
* **"min-of-3" is min-of-1** for any row whose first repetition exceeds the 30 s
  cap. True of the capped rows and of the 32.6 s row. Say
  *min-of-3, or min-of-1 for rows over 30 s.*

## R3.4 SMALLER CORRECTIONS TO REV 1

* **§1's code block elides `:681-683` and `:686-690` without marking it.** The
  elided comment is the pin candidate B must clear. Mark the elision.
* **The `k·m²` derivation sentence is short one factor.** `k` splits × `m+1`
  boundaries is `k·m`; the second factor of `m` is the brace run's own free
  stopping point. The stated answer `k·m²` is right; the one-line reason was not.
* **§2a's mechanism sentence for class 2 is contradicted by its own data.**
  `{ `×4800 and `x `×4800 have the **same token count** and differ by **3.4×**,
  so "superlinear in token count" cannot be the term. The measured claim is
  stronger: braces are ~3.4× cheaper per token than ordinary words, which
  supports "not a brace class" better than the mechanism sentence did.
* **§2b understates its own result** — the regex share is 99.5-100 %, not
  97-99 %, and `localise.py` profiles classes 1-3 only, so "every class" is 3 of
  4. Also: `attribute.py`'s shim intercepts `compile/search/match/sub` and
  **not** `split/findall/finditer/fullmatch/subn`. The emitted module uses
  `re.split` ×4 (linear character-class splits) and no `finditer` at all, and the
  shares sum to 99.8-100 %, so the gap is immaterial here — but it is a gap, and
  the next reader must not inherit it as a proven-complete shim.
* **`remeasure.log` on disk records `HEAD 0248ea1`, not `e3f2f57`.** It was run
  before the branch was cut. The delta is `.claude/readiness-queue.md` only, so
  the emitted artifacts are identical, and lens 1's independent re-run at
  `e3f2f57` reproduces every number.
* **Candidate C's edit site is inside a NON-RAW `'''...'''` block**
  (`lib/sdk_gates_template.py:102-3706`), so the source spelling must be
  DOUBLED: `[^-\\s]\\S*`. Done and verified against the emitted probe, which
  renders `(?:\s+-[Cc]\s+[^-\s]\S*|\s+-\S+)*`.

## R3.5 CANDIDATE C, END TO END ON THE EMITTED ARTIFACTS

A second candidate tree carrying **A' + B + C** gives an **identical suite
result to A'+B: 9,758 / 5, the same five digest pins, byte-for-byte the same
failure set.** C adds no behavioural change.

| class | SDK shipped | SDK A'B+C | shell shipped | shell A'B+C | verdicts |
|---|---|---|---|---|---|
| 1 | > 45 s capped | **0.184 s** | 0.210 s | 0.222 s | deny / deny |
| 3 bare | > 45 s capped (110.22 s uncapped) | **0.000 s** | 0.034 s | 0.034 s | allow / allow |
| 3b | 36.15 s | **0.001 s** | 0.033 s | 0.034 s | deny / deny |
| 4 | > 45 s capped | **0.000 s** | 0.017 s | 0.015 s | allow / allow |
| benign install | 0.000 s | 0.000 s | 0.023 s | 0.022 s | allow / allow |
| benign 6 KB assignments | 0.001 s | 0.001 s | 0.032 s | 0.035 s | deny / deny |

**Class 2 is deliberately absent from this table** — see R3.3.

## R3.6 THE DELETION CALIBRATION THE COST BLOCK HAS NEVER HAD

Lens 4 asked for one and there is a clean way to build it that still measures
the emitted object: take `_PIPE_TO_SHELL.pattern` **off the emitted module**,
apply the substitution in REVERSE, recompile, and require the reverted pattern
to be dramatically slower. Prototyped:

| payload | emitted | reverted | ratio |
|---|---|---|---|
| `2>>o `×18 | 0.0000 s | 0.3095 s | **12,077×** |
| `A=1/env `×24 + `{ `×300 | 0.0039 s | 0.4564 s | **118×** |

Cheap enough for the suite (~0.8 s), and it cannot pass if someone reverts the
fix: the reverse substitution then finds nothing to replace and the row's own
`rev != pat` assertion fails first.

---
---

# PLAN — rev 4 · STEP-3 REVIEW COMPLETE · 2026-08-20 local `+0800`

**Four lenses ran. This layer GOVERNS. Step 3 is discharged and with it the R0
plan-approval gate (runbook §5.1).**

## R4.1 CANDIDATE C IS WITHDRAWN. IT WAS A DENY→ALLOW BYPASS.

`git -C - commit` — a `-C` whose argument is the single character `-`.

```
shipped   _GIT_VERB_TMPL % "commit"   on " git -C - commit -m x "  -> MATCH
C         same with [^-\s]\S*                                      -> None
```

`_git_verb` returning False means `if not _git_verb(cmd, "commit"): return {}` —
**the gate does not apply.** Three gates go quiet: `_spec_gate_commit`,
`_test_gate`, and `_eval_gate` on `push`. **Deny becomes allow, which is the one
direction this repo forbids.**

**It is not a theoretical string.** Re-derived here, not taken from the lens:

```
mkdir -- - && git init -q -- - && cd - && git commit --allow-empty -m bypass
70cc20c bypass
```

`git -C -` really does chdir into a directory named `-` and really does commit.

**My §4 argument proved the wrong lemma.** It said a `-C` argument starting with
`-` is accepted anyway by two iterations of the bare-flag arm. True for length
≥ 2, **false for length 1**: `\s+-\S+` requires at least one character after the
`-`, so a lone `-` has no fallback parse.

**AND MY OWN CHECK CLEARED IT.** Rev 2 §R2.2 recorded *"candidate C, re-derived
independently: 14,762 strings, 0 divergences."* That run's token set was
`[" -C x", " -C", " -c", " -x", " -C -x", " x", " commit", " -C commit",
"\t-C"]` — **no lone `-` argument anywhere, so the harness could not spell the
counterexample.** It is the same void-alphabet failure that voided `proto.py`
v1 earlier in this same session, committed a second time, four hours after
writing the lesson down. Re-run with a widened set that CAN spell it: C shows
**641 divergences**, first `git -C - commit`.

**And 9,763 checks cannot see it.** With C applied,
`test_substrate_differential.py` 4,178/0, `test_composition.py` 147/0,
`test_hook_behavior.py` 384/0 — all green with the bypass live. The corpus has
`git -C /repo push` and `git -C . commit`; nothing pins a `-C` argument
beginning with `-`.

## R4.2 THE REPLACEMENT — C+, PROVEN, SAME COST WIN

```
py   (?:\s+-[Cc]\s+(?:[^-\s]\S*|-)|\s+-\S+)*
ere  ( +-[Cc] +([^- ][^ ]*|-)| +-[^ ]+)*
```

The lone `-` has exactly one parse under the shipped star, so admitting it back
costs no ambiguity. Re-derived here over the widened alphabet: **0 divergences**,
against C's 641 in the same run. Cost unchanged from C: `-C `×32 `1.23 s →
0.0000`, ×36 `8.45 → 0.0000`, ×40 `> 25 s → 0.0000`.

## R4.3 SCOPE CORRECTION: THE FLAG STAR IS WRITTEN TWICE, AND REV 1 NAMED ONE

Both lenses found it independently. `lib/templates.py:2825`:

```
local _re="^ *${CMD_PFX}([^ ]*/)?$2( +-[Cc] +[^ ]+| +-[^ ]+)* +$3( |\$)"
```

against `lib/sdk_gates_template.py:1636`'s `(?:\s+-[Cc]\s+\S+|\s+-\S+)*`.
Unlike `CMD_PFX`, `_PIPE_RE` and `HEAD` — all rendered from `cmdpos` — **the
flag star has no `cmdpos` renderer.** It is the two-independent-encodings shape
that `prefix_run()` exists to abolish, quoted in rev 1 §1's own defect note.
Landing C+ on the SDK alone makes the shell deny what the SDK allows.

**`lib/templates.py` joins the scope. Both copies change in one commit, or
neither does.**

Carrier census, which rev 1 also had wrong: `_GIT_VERB_TMPL` is **two** compiled
patterns (`% "commit"` and `% "push"`) reached from **three** gates
(`spec-gate-commit`, `test-gate`, `eval-gate`), both compiled at CALL time. Only
`test-gate` declares a timeout.

## R4.4 A' AND B ARE PROVEN, NOT BOUNDED-CHECKED

Lens 3 built an exact decision procedure — Thompson NFA, on-the-fly product
determinization, BFS, over a 77-character representative alphabet provably
refining every class in the patterns, with the NFA compiler cross-checked
against Python's own `re` before each decision. **Unbounded in string length.**

```
_CMD_PFX_RE +B      EQUIVALENT      _CMD_PFX_RE +A'    EQUIVALENT
_CMD_PFX_RE +A'B    EQUIVALENT      +CAL-1 (must differ) NOT EQUIVALENT  'env ('
git body +C  (must differ) NOT EQUIVALENT  'git -C - commit'
git body +C+        EQUIVALENT
```

Both dialects, including the bash ERE instantiation. Corroborated by ~215 M
enumerated strings with four broken controls firing.

**Implementation hazard to carry into step 5:** A''s middle separator must be the
**literal** ` +`, never the `space` parameter. Spelling it `\s+` is EQUIVALENT in
ERE and **NOT** equivalent in Python (witness `<\t0 `), i.e. a Python-only
widening invisible to the shell — the dialect-drift shape `_py`'s X-36j comment
already records once. Same for candidate C+'s inner ` +`.

## R4.5 CLASS 2 — A CANDIDATE EXISTS, AND I COULD NOT REPRODUCE ITS HEADLINE

Lens 2 proposed guarding the trailing group with `(?![({])` and reported
**24.154 s → 0.038 s (636×)** at `{`×19200 through the emitted dependency-gate.

**I could not reproduce that.** Patching both prefix-run splices in a copy of the
emitted `gates.py` and driving the real closure:

| payload | shipped | candidate D |
|---|---|---|
| `{`×4800 | 1.334 s | 1.135 s |
| `{`×9600 | 5.303 s | 4.478 s |
| `{`×19200 | **21.017 s** | **17.709 s** |

**~16 %, not 636×.** Language equivalence I *did* reproduce: 0 divergences over
8,820 strings with a broken control firing at 2,818. Its stated MECHANISM I also
could not reproduce — dropping `(?:\S*/)?` from the emitted `_PIPE_TO_SHELL`
leaves the class quadratic (×4.0 per doubling, 29 % cheaper), where the lens
reported linear.

**The disagreement is recorded, not smoothed.** Either way class 2 stays open in
this item, for a reason that does not depend on whose number is right:
`(?![({])` is **not POSIX ERE**, so `prefix_run()` — one source, two dialects —
cannot carry it without a new mechanism. That is a design decision, not an edit.

## R4.6 A COST CLASS NEITHER THE PLAN NOR THE QUEUE HAD

`_PIPE_TO_SHELL`/`_PIPE_RE` open with
`(?:curl|wget|…|http|https|…)[^;&]*[|] *`. Every `http` in the string is an
unanchored start where the alternation matches, and `[^;&]*` then scans to the
end: n starts × O(n). Lens 2 measured it on both substrates, with controls:

| payload | bytes | SDK | shell | verdicts |
|---|---|---|---|---|
| `http `×6400 | 32,005 | 1.335 s | 5.842 s | allow / allow |
| `http `×12800 | 64,005 | **5.284 s** | **22.885 s** | allow / allow |
| control `zzzz `×6400 | 32,005 | 0.033 s | 0.871 s | allow / allow |

×3.9 SDK and ×3.7 shell per doubling — **quadratic on both**. Reachable by an
ordinary command: `wget` with 2,000 real URLs, 60,895 bytes, 0 jump bytes, shell
**4.364 s**. Extrapolated to 81,900 B it is ~8 s benign and ~37 s adversarial —
**under** the 60 s ceiling, so it is a latency finding, **not a bypass**, and it
is filed as such.

## R4.7 GATES WITH NO CEILING ON EITHER SUBSTRATE

`spec-gate-commit` and `eval-gate` appear in neither `_GATE_TIMEOUTS` nor
`templates.TIMEOUTS`, and both reach the flag star. Lens 2 measured
`spec-gate-commit` on `git ` + `-C `×40 at **79.9 s** — 127 bytes, 0 jump bytes,
crossing the platform default on a gate with **no declared ceiling on either
substrate**. Rev 2 sized the step-4 row at ×40 for the right reason without
saying that.

## R4.8 STEP 4, FINAL

Everything in R2.4 and R3.6, plus:

* **`git -C - commit` and `git -C - push` as pinned verdict rows.** Nothing in
  9,763 checks sees them today, and they are what would have caught C.
* The class-4 cost row moves to the **C+** spelling and stays at `-C `×40.
* The cost block's deletion calibration gains a third pair for C+.

## R4.9 WHAT THE REVIEW CHANGED, IN ONE LINE EACH

| lens | outcome |
|---|---|
| 1 | every number reproduces; four harness-labelling defects, one of them a printed number that was never measured |
| 2 | scope was 3 carriers of 19; the flag star has a hand-written shell twin; a new quadratic class on both substrates |
| 3 | **candidate C refuted as a live bypass**; A' and B proven unbounded; a proven repair supplied |
| 4 | step-4 spec was unactionable; the S0.2 justification was false; the `NO COUNT FENCE` decision rests on a retracted premise |

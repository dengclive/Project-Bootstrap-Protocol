# PLAN — `sdk-pipe-trigger-redos` — the SDK prefix-run ReDoS

**Session** 2026-08-17 · **Branch** `fix/sdk-pipe-trigger-redos` off `origin/main` @ `ab09a9a`
**Class** `CODE` — gate logic, `lib/`, emitted bodies. **Full ceremony. Never batched.**
Runbook `.claude/readiness-runbook.md` §3; step 3 is the review that approves this.

**A LIVE FAIL-OPEN ON `main`, IN THE SDK-MORE-PERMISSIVE DIRECTION.** It is the
top A-tier item, above `x37-class-b`, because it is reachable today in 133 bytes
of ordinary words.

---

## 1. THE DEFECT, QUOTED FROM THE TREE

**(a) The construct.** `lib/cmdpos.py:665-677`, `prefix_run()`:

```python
return (
    "((" + nonspace + "*/)?(" + alt(ALL_PREFIXES) + ")("
    + space + "-" + nonspace + "*|"
    + space + "[^- ]" + nonspace + "*)*" + space
    ...
    ")*"
)
```

An outer `(...)*` over an alternation whose first arm carries its own inner
`(...)*`, and **both consume the same `space`+word units**. Given *n* prefix
words, the number of distinct partitions is 2^(n-1). On a **failing** overall
match the engine explores all of them.

**(b) The design says so, and says the opposite of what is true —
`lib/cmdpos.py:633-637`:**

> *"UNBOUNDED after a wrapper word, deliberately … and for why unbounded
> consumption cannot fail open in a REGEX (the engine backtracks; the allowance
> is gated on a wrapper word, so an ordinary command cannot drift into command
> position)."*

**That sentence is true of CORRECTNESS and false of COST.** The backtracking it
relies on for soundness is the exponential. This is the root cause and the
sentence must be amended, not merely worked around.

**(c) It is exponential, base exactly 2.** Measured this session on the emitted
compiled objects, failing payload `"env " × n + "zzz"`:

| | n=14 | n=18 | n=20 | n=22 | n=24 |
|---|---|---|---|---|---|
| `_INSTALL_HEAD` | 0.013 s | 0.204 s | 0.824 s | 3.289 s | 13.160 s |
| `_PIPE_TO_SHELL` | 0.016 s | 0.254 s | 1.016 s | 4.116 s | 16.405 s |

Ratio per added token across n=14..20 on `_PIPE_TO_SHELL`: 1.99, 1.99, 2.00,
1.99, 2.00, 2.00.

**(d) It is reachable, and it needs nothing exotic.** `"env " × n +
"zzz ; pip install evilpkg"`, end to end through the emitted `gates.py`:

```
n=24  121 B  0 jumps   13.20 s
n=25  125 B  0 jumps   26.44 s
n=26  129 B  0 jumps   51.62 s
n=27  133 B  0 jumps  102.32 s   <- past the 60 s ceiling
```

**No downloader, no pipe, no substitution.** `_GATE_TIMEOUTS` declares
`dependency-gate: 60.0`, and the emitted file states the consequence itself
(X-51 correction, 2026-08-13): *"A hook cancelled at its declared timeout exits
124/137/143; only exit 2 blocks; the call PROCEEDS. Crossing the ceiling is a
BYPASS, not a refusal."* So the `pip install evilpkg` is never adjudicated.

**(e) The shell is unaffected and that is the forbidden direction.** bash's ERE
engine does not backtrack; the same string denies in **0.03 s**, flat. So this
is **shell-DENY / SDK-BYPASS**.

**(f) `_cost_guard` cannot see it.** It measures LENGTH (`_CMD_MAXLEN` 81920)
and DENSITY (`_CMD_MAXJUMP` 8191). The payload is 133 bytes with **zero** jump
bytes. The axis is **token count at fixed length** and nothing in the tree
measures it.

**Two emitted regexes carry the prefix run and both blow up:**
`_PIPE_TO_SHELL` (`gates.py:145`) and `_INSTALL_HEAD` (`:1801`, composed as
`^\s*` + `_PREFIX` + `_INSTALL_TAIL` where `_PREFIX` = `_CMD_PFX_RE` = the
prefix run). `_ANCHOR` has **no emitted call site**. *(This corrects ledger
entry 34, which claimed only `_PIPE_TO_SHELL` — see the correction commit.)*

`_PIPE_TO_SHELL` is additionally searched **five times per command**
(`lib/sdk_gates_template.py:3125-3129`: raw, unquoted, redirect-normalised,
unquoted-redirect-normalised, parked), so a failing search costs 5×.

---

## 2. TWO CANDIDATES ARE ALREADY DEAD — MEASURED, NOT ARGUED

Recorded so step 3 does not spend a round rediscovering them.

* **Atomic-group the whole prefix run** — `(?>` prefix_run `)`. Kills the cost
  outright (0.0000 s at n=2000) and turns **17 of 29 live denies into ALLOWS**:
  `env python3 -m code`, `sudo sh -c 'x'`, `timeout 5 bash -c 'x'`,
  `nice -n 5 python3 -m http.server`, … Every casualty is a **trailing-argument**
  form, because a greedy-atomic prefix run cannot give the interpreter word back.
* **Atomic-group arm 1's inner positional run** — breaks **11 of 31**, including
  `env python3`, `sudo sh`, `/usr/bin/env python3`.

**AND THE NEAR-MISS IS THE METHOD LESSON.** A first 31-row corpus — every row
ending *at* the interpreter — reported the whole-run variant **clean, zero
divergences**. The trailing-argument rows are what expose it. That is the third
false green in this session. **Any candidate must be measured against the full
4,161-row differential and both emitted substrates, never a hand corpus.**

---

## 3. THE MECHANISM — THREE LIVE CANDIDATES, CHOSEN BY MEASUREMENT

**This plan deliberately does not pick one.** Two of my own instincts have
already been disproven by measurement here, so the choice belongs to step 3's
prototype lens, against the criteria in §6.

**C1 — BOUND THE OUTER REPETITION, AND DENY ON OVERFLOW.**
`(...)*` → `(...){0,N}`, capping the search at 2^N. Alone this is a **fail-open**
above N, so it must be paired with a cheap, non-backtracking overflow test that
**denies** a prefix run longer than N as unmodellable — the deny-list bias
`interpreter_word`'s second arm already uses for `${SHELL}`
(`lib/cmdpos.py:705-718`). Needs: the **benign maximum** prefix-run length,
derived rather than guessed. Expressible in both dialects.

**C2 — DISAMBIGUATE: the inner positional run may not consume a word that is
itself a prefix-run head.** Removes the 2^n partitions at the source, because
each prefix word then has exactly one parse. Requires a negative lookahead,
which Python has and **POSIX ERE does not** — so the shell keeps today's
spelling and the two substrates carry different *sources* for one rule. That is
the very thing `prefix_run` exists to prevent (`lib/cmdpos.py:616-621`:
*"Two encodings of one rule is the defect; one function is the fix"*), so C2 is
admissible **only** if the two are proven to accept the same language over the
full differential — and the plan says plainly that this is the weakest point of
C2, not a detail.

**C3 — REPLACE THE SDK's PREFIX-RUN MATCH WITH A LINEAR TOKEN WALK.** Exact and
linear; the SDK already tokenises. But it is a second encoding of command
position by construction, and the shell would keep the regex. Heaviest blast
radius, and the one most likely to move verdicts. Listed because it is the only
candidate that removes the class rather than bounding it.

**REJECTED WITHOUT PROTOTYPING, with the reason stated:** adding a **token-count
term to `_cost_guard`**. The blowup begins at ~22 tokens, far below any benign
cap — a cap low enough to help would refuse ordinary commands. X-52 removed a
token term for a related reason; this is not a revival of it.

---

## 4. SCOPE GLOBS — anything outside is **E4**

```
lib/cmdpos.py                          prefix_run + the :633-637 comment that is wrong
lib/sdk_gates_template.py              the SDK rendering / consumption
lib/templates.py                       ONLY if the shell spelling must move with it
tests/test_substrate_differential.py   step-4 rows + the cost row
tests/test_composition.py              the parity / no-hand-copy pin
tests/test_greenfield_golden.py        freeze exception + greenfield digests
tests/test_retrofit.py                 freeze exception + RETROFIT digests
docs/deferred-backlog.md               file the finding as a numbered row
docs/changelog.md                      entry
.claude/readiness-queue.md             step 10
.claude/trust-ramp.md                  step 10b
.claude/dynamic-workflow-policy.md     its two `docs/changelog.md:922` citations
                                       move if an entry is prepended
```

**A freeze exception IS required** — the emitted bodies move. Number to be taken
at step 5, not assumed.

---

## 5. STEP 4 — THE FAILING CHECK

`CODE` → a check that is **red on the current tree**, run before `lib/` is
touched, red output pasted into the commit.

**The corpus cannot see this defect**, and saying so is part of the plan: at
n=27 the SDK still returns `deny`, just 102 s late, so `shell == sdk == deny`
holds and every differential row passes. **The failing check must therefore be a
COST check**, and it is the first one this suite would carry.

Proposed: adjudicate `"env " × 27 + "zzz ; pip install evilpkg"` through the
emitted `gates.py` and assert it completes **well inside** the declared 60 s
`dependency-gate` timeout — a generous bound (≈10 s) so the check is robust on a
loaded box while still being red at 102 s today. Paired with the same payload on
the emitted shell hook, which is flat at 0.03 s and is the control.

**Every row must be measured before it enters the corpus** — the discipline that
caught the executing fence row in PR #79.

---

## 6. THE COST GATE, STATED BEFORE ANY CODE EXISTS

> The chosen mechanism must be **polynomial** in token count — exponential in
> any parameter is rejected outright — and the emitted `gates.py` **and** the
> emitted shell hook must each adjudicate every cap-legal payload in **≤ 15 s**,
> measured on **three axes**: token count at fixed length, plain length to
> `_CMD_MAXLEN` (81920 B), and jump density to `_CMD_MAXJUMP` (8191).

Today's `_PIPE_TO_SHELL`/`_INSTALL_HEAD` fail axis 1 at n=27. The shell passes
all three today and must still pass them after.

---

## 7. WHAT WOULD FALSIFY THIS PLAN

1. **Any verdict moves.** The full 4,161-row differential must be unchanged.
   Both dead candidates failed exactly here, and a 31-row corpus said otherwise.
2. **A substrate split** — shell-deny/SDK-allow or the reverse.
3. **The benign maximum prefix-run length turns out to be near N** (C1), leaving
   no safe cap.
4. **C2's language-equivalence claim is false** — the lookahead changes which
   strings match, not merely how many paths are explored.
5. **Action counts move** (greenfield 57/69/59, retrofit 79/93) → **E5**.
6. **The fix moves the shell's cost.** The shell is currently flat and correct;
   a change that slows it to buy the SDK is a bad trade and must be caught.
7. **The cost check is flaky** on a loaded box, making the suite unreliable —
   in which case the check needs a different instrument, not a looser bound.

---

## 8. OWNER DECISIONS

**None blocks steps 4–5.** One is worth flagging: if the chosen candidate is
**C2**, the two substrates carry different regex *sources* for one rule for the
first time. That is a deliberate, disclosable departure from
`lib/cmdpos.py:616-621`, and the operator may prefer C1's bounded-and-deny even
at the cost of a new over-refusal class. **It ships as pinned corpus rows either
way, so the choice is legible in the corpus rather than argued in prose.**

---

## 9. HOW THIS PLAN ASKS TO BE REVIEWED

The prototype lens is not optional. Three separate times this session a
read-only reading passed something a five-minute measurement killed: the
executing fence row, the vacuous contract check, and both atomic-group
candidates. So step 3 must:

* **build C1, C2 and C3** in a copy of the tree, install, and run the **full
  differential on both emitted substrates** — not a hand corpus;
* **measure all three cost axes on both substrates**, and report the growth
  exponent across ≥ 4 sizes rather than a single number;
* **attack the fence directly** — generate ordinary developer commands with long
  prefix runs (`sudo -u root env FOO=1 nice -n 5 timeout 5 …`) and report every
  one that changes verdict;
* **derive the benign maximum prefix-run length** from real command shapes, since
  C1 cannot be sized without it;
* and **check my numbers**, including the corrected blast radius — the last
  version of that claim was false and reached `main`.

---
---

# APPENDED 2026-08-17 — STEP-3 REVIEW RAN. **VERDICT: NOT APPROVED.**

**Nothing above this line is edited.** Where it disagrees with this layer, **this
layer governs.** 11 agents: three sequential build-and-measure prototypes (C1,
C2, C3), two attack lenses, six refuters. **41 findings, 5 confirmed blocking,
1 killed, 35 reported unverified.** Step 4 must not begin.

## A. THE BLAST RADIUS WAS WRONG A SECOND TIME — AND I RE-DERIVED IT MYSELF

§1 says *"TWO emitted regexes carry the prefix run"* and *"`_ANCHOR` has no
emitted call site"*. **Both wrong.** There are **THREE** carriers, and `_ANCHOR`
does not exist in the emitted module **at all**:

```
_CMD_PFX_RE                                                    gates.py:79   <- the prefix run
_PIPE_TO_SHELL   = re.compile(... _CMD_PFX_RE ...)             gates.py:145
_INSTALL_HEAD    = re.compile(r"^\s*" + _PREFIX + _INSTALL_TAIL)  :1801
_GIT_VERB_TMPL   = r"(?:^|[;&|()`\n])\s*" + _CMD_PFX_RE + ...     :1739   <- THE THIRD
                   compiled per call as `pat = _GIT_VERB_TMPL % verb`
```

My scan looked only at module-level **compiled** `re.Pattern` objects, so a
**template composed and compiled at call time** was invisible to it.

**And the third one is the widest.** Measured, `"env " × n + "zzz"`:
`_GIT_VERB_TMPL % "commit"` is 0.0064 / 0.1032 / 0.4135 / 1.6492 / **6.6510 s**
at n = 14 / 18 / 20 / 22 / 24 — the same base-2 shape. `_git_verb` is the FIRST
statement of **spec-gate-commit, test-gate and eval-gate**, so one 121-byte
payload of ordinary words costs **four gates**, not one:

```
dependency-gate  12.867 s      eval-gate         7.757 s
spec-gate-commit  7.805 s      test-gate         7.787 s
```

**This is the second blast-radius claim of mine to be wrong in one session** —
ledger entry 35 graded the first `harmful`. The difference is that this one was
caught **before** it reached `main`: the correction commit `2c5ae87` sits on this
branch, unpushed, and must be amended before it goes anywhere.

## B. THE COST IS NOT DRIVEN BY THE QUANTITY §3 ASKED FOR

§3 tells step 3 to derive *"the benign maximum prefix-run LENGTH"*. **That is the
wrong quantity, and a fence built on it cannot work.** Measured end to end on the
emitted dependency gate:

| shape | bytes | tokens | wall |
|---|---|---|---|
| 1 wrapper + 800 assignments | 3207 | 802 | **0.20 s** |
| 4 wrappers × 16 assignments | 275 | 69 | 0.57 s |
| 6 wrappers × 16 assignments | 411 | 103 | **> 95 s** |
| 8 wrappers × 16 assignments | 547 | 137 | **> 95 s** |
| 27 bare wrappers | 111 | 28 | **> 95 s** |

**802 tokens is flat and 103 tokens is over 95 seconds.** Cost is driven by the
**interleaving** — a product of wrapper arms by the positionals each can absorb —
not by any count or length. So no cap on length, byte count or token count can
separate the benign case from the attack, and §3's C1 sizing question was
unanswerable as posed.

## C. ALL THREE CANDIDATES ARE DAMAGED

* **C1 (bound + deny on overflow) — the cap half is a verified executing
  fail-open, and the plan describes it wrongly.** `(...)*` → `(...){0,N}` does
  **not** cap the search at 2^N as §3 claims; it converts the exponential into a
  **polynomial of degree N** (≈ n^8.4 at N=8), which still crosses 60 s inside
  `_CMD_MAXLEN` — it buys ~37 bytes of headroom. Worse, at exactly **N+1
  non-absorbing arms** it flips real commands from deny to allow on **both**
  substrates: `V0=1 … V8=1 pip install evilpkg` parses under `bash -n` and
  **really runs pip**. Unfixable by raising N, because N+1 assignments is always
  a legal command.
* **C2 (negative lookahead) — reported not to kill the exponential at all**, and
  it would still give the two substrates different sources for one rule.
  *(Reported, not independently re-derived by me.)*
* **C3 (linear token walk) — reported to leave a quadratic in the pipe path and
  to add a third encoding of command position.** *(Same caveat.)*

## D. THE ACCEPTANCE TEST IN §7 DOES NOT WORK

§7 falsifier 1 makes *"the full 4,161-row differential unchanged"* the bar. **The
corpus is blind to this entire class.** I classified every string literal in
`tests/test_substrate_differential.py` by prefix-run arm-start count:

```
{0: 3502, 1: 228, 2: 12, 3: 3, 4: 10, 5: 2}      max = 5
```

So **any cap N ≥ 6 leaves the whole differential green** while carrying the
executing fail-open in §C. A green differential is not evidence here — the fourth
time this session that sentence has had to be written, and the reason the fence
item (PR #79) existed at all.

## E. WHAT THE NEXT REVISION MUST DO

1. **Re-derive the carrier set from the emitted artifacts by pattern content,
   including templates compiled at call time** — not by scanning for compiled
   objects. State the gate list, not just the regex list.
2. **Drop "benign maximum length" entirely.** The quantity that matters is the
   interleaving/parse count, and §B shows a 3207-byte 802-token command is flat
   while a 411-byte 103-token one is not.
3. **Replace the acceptance test.** The differential cannot see this; the fence
   must be new rows at ≥ N+1 non-absorbing arms **on both substrates**, pinned
   **before** any N is chosen, plus a deterministic cost instrument rather than
   the wall-clock bound §5 proposes.
4. **Treat C1's cap as dead unless the overflow deny fires on the identical
   count** — and note that the overflow-test-alone variant was reported to create
   a shell/SDK split of its own.
5. **Amend `2c5ae87` before it is pushed.** Its queue row and ledger entry 35 both
   say "TWO"; the answer is three carriers and four gates.

**The verdict does not move and nothing is implemented.** `x37-class-b` remains
behind this item, and this item is now known to be wider than it was filed as.

---
---

# REV 2 — APPENDED 2026-08-17. RE-PLANNED FROM THE INTERLEAVING INSIGHT.

**Nothing above is edited. This layer governs.** Rev 1's three candidates
(C1 cap, C2 lookahead, C3 token walk) are **withdrawn**, for the reasons the
step-3 review measured. Rev 2 proposes **one** mechanism, arrived at from the
insight itself rather than from a repair of a failed candidate.

## A. THE INSIGHT, STATED PRECISELY

Rev 1 said the cost is 2^(n-1) in prefix tokens. **That is wrong, and the right
statement is what makes the fix obvious.** Of `prefix_run`'s six arms, only two
are **ABSORBING** — the wrapper arm and the named-group arm carry an inner
`(...)*` that can swallow following words. The other four (`[({]`, redirect,
assignment, keyword) consume exactly one unit and are unambiguous.

**The cost is a PRODUCT over absorbing arms** of (1 + the words each could
absorb) — not a function of length or token count. Measured end to end:

| shape | bytes | tokens | wall |
|---|---|---|---|
| 1 wrapper + 800 assignments | 3207 | 802 | **0.20 s** |
| 6 wrappers × 16 assignments | 411 | 103 | **> 95 s** |

One absorbing arm is a single choice point — linear, and flat at 802 tokens.
Six absorbing arms is 17^6. **That is why no cap on length, bytes or tokens can
work**, and it is also the shape of the cure.

## B. C5 — ALLOW AT MOST ONE ABSORBING GROUP

Once *any* wrapper appears, its inner run can absorb everything up to the
interpreter, so every later absorbing arm is **redundant**, not merely
expensive. Replace the repeated alternation with:

```
prefix_run  ≡  NONABS*  ( WRAPPER space (nonspace+ space)* )?
```

Built from the same `cmdpos` tuples — `ALL_PREFIXES`, `NAMED_GROUP_HEADS`,
`KEYWORDS` — with **no new word list**. Crucially it uses **no lookahead and no
atomic group**, so it is plain POSIX ERE and **both substrates keep ONE shared
source**. That dissolves C2's fatal objection (`lib/cmdpos.py:616-621`, *"Two
encodings of one rule is the defect"*) rather than trading against it.

## C. WHAT IS MEASURED, AND WHAT IS NOT

**Measured by me, this session, on the emitted artifacts:**

* **The full differential is unchanged: `4161 passed, 0 failed`**, both
  substrates.
* **Full suite: 9724 passed, 5 failed** — and the 5 are *only* the golden and
  retrofit **digest** pins, which any emitted-body change moves. **Action counts
  are STABLE** — greenfield 57 / 69 / 59 and retrofit — so this is **not E5**; a
  freeze exception covers it.
* **The cost is cured across all four affected gates**, and the shell is
  untouched:

| payload | bytes | dep | eval | spec-commit | test | shell |
|---|---|---|---|---|---|---|
| 27 bare wrappers | 133 | 0.001 s | 0.001 s | 0.001 s | 0.000 s | 0.025 s |
| 40 bare wrappers | 185 | 0.001 s | 0.000 s | 0.000 s | 0.000 s | 0.025 s |
| 6 wrap × 16 assign | 433 | 0.002 s | 0.001 s | 0.000 s | 0.001 s | 0.033 s |
| 8 wrap × 16 assign | 569 | 0.003 s | 0.001 s | 0.001 s | 0.001 s | 0.036 s |
| 1 wrap + 800 assign | 3229 | 0.010 s | 0.003 s | 0.003 s | 0.003 s | 0.095 s |

Every one of these was **> 95 s** before. The benign case got *faster*.

* **Language equivalence on a generated corpus: 7,110 rows, 0 divergences**
  (6,000 random over a 38-word alphabet + all 1-, 2- and 3-word combinations
  over a 10-word focused alphabet).

**NOT established, and this is the part that decides the item:**

1. **The differential CANNOT see this class.** Its arm-start histogram is
   `{0: 3502, 1: 228, 2: 12, 3: 3, 4: 10, 5: 2}` — **max 5**. So `4161/0` proves
   no *pinned* verdict moved; it proves nothing about prefix runs longer than 5,
   which is exactly where C5 changes the parse.
2. **The 7,110-row corpus is mine**, generated from a word list I chose, so it
   can share my blind spots. Four times this session a corpus of mine returned a
   false green.
3. **C5's equivalence is a CLAIM about all inputs**, argued informally in §B
   ("later absorbing arms are redundant"). It has not been proven, only sampled.

## D. WHAT WOULD FALSIFY REV 2

1. **Any string where C5 and the shipped `prefix_run` accept differently**,
   especially with ≥ 2 wrappers and a trailing argument — the region the corpus
   cannot see and where rev 1's atomic candidates died.
2. **A verdict split between the patched SDK and the patched shell.**
3. Action counts move → **E5**.
4. The shell gets slower (it currently gets faster).
5. A payload still crossing any gate's ceiling after C5.
6. `_GIT_VERB_TMPL`, `_INSTALL_HEAD` or `_PIPE_TO_SHELL` turning out **not** to
   be the complete carrier set — it has been wrong twice already, and the method
   that got it wrong was scanning for module-level compiled patterns.

## E. SCOPE — CORRECTED

Rev 1 §4 said `lib/templates.py` was needed *"ONLY if the shell spelling must
move"*. **It moves.** C5 changes the shared source, so both emitted substrates
change and **a freeze exception is required** (number taken at step 5). Add
`docs/deferred-backlog.md` for a numbered row, and the four affected gates must
be named in it: dependency-gate, eval-gate, spec-gate-commit, test-gate.

## F. STEP 4 — THE FAILING CHECK

Rev 1 §5's wall-clock check stands, with a correction: it must cover **the
carrier set, not one consumer**. The corpus is blind to this class, so the check
is necessarily a cost check — but the payload must be the **interleaving** shape
(`("env " + "A=1 "×16) × 6`, 411 B), not the bare-wrapper shape, because the
interleaving one is smaller per second of damage and exercises the product
directly. Red now at > 95 s; green after at ~0.002 s.

## G. HOW REV 2 ASKS TO BE REVIEWED

The one question that matters is **§C's unestablished claim**: is C5's language
identical to the shipped `prefix_run` for prefix runs longer than the corpus
contains? A lens must attack that directly — exhaustive enumeration over a small
alphabet at depths 4–8, differential acceptance against the shipped regex, both
dialects — rather than re-running the differential, which is already green and
already known to be blind.

---
---

# REV 3 — APPENDED 2026-08-17. C5 IS DEAD; C8 IS THE CANDIDATE.

**Nothing above is edited. This layer governs.** The rev-2 review ran (9 agents;
2 refuters died on a usage limit and their findings are unverified). **14
findings, 3 confirmed, 1 killed.** Everything below I re-derived myself.

## A. C5 WAS BROKEN, AND IT WAS MY FIFTH FALSE GREEN

C5 **silently narrowed the language**: it deleted the `[({]` arm *after* a
wrapper word with **zero trailing spaces**. Shipped puts `|[({] *` inside the
outer `(...)*`, so that arm can be last and consume no space; C5 reached it only
*before* the wrapper, and its post-wrapper tail `(nonspace+ space)*` requires
every chunk to end in a space. So `WRAPPER…[({]INTERPRETER` was unreachable.

**All losses were deny→allow, and three are live RCE.** Verified by me under GNU
bash — `cat p.sh | { time (sh); }`, `| ( time (sh) )`, `| if time (sh); then :;
fi` all **executed**. (`{`-glued does *not* execute: `{` is only a reserved word
as a separate token, while `(` is a metacharacter. That refinement is the
refuter's and it holds.)

**Why my corpus missed it:** every `(`/`{` in my 7,110-row alphabet was a
separate spaced token. The failing shape needs them **glued**. The corpus was
**structurally incapable** of expressing the defect — reseeding or enlarging it
could never have found it. Rev 2 §C also aimed the falsifier at the wrong region:
I said "prefix runs longer than 5"; the minimum breaking run is **two** arm
starts.

## B. C6 FIXED THE LANGUAGE AND BROKE THE COST

The review's prescribed repair — append the whole `nonabs*` — restores every lost
string, but its assignment/redirect/keyword arms then **compete with the
wrapper's own word run** over the same tokens. Measured on the benign
single-wrapper case:

| | shipped | C6 |
|---|---|---|
| 1 wrapper + 800 assignments (3207 B) | 0.208 s | **20.55 s** |
| 1 wrapper + 1600 assignments (6407 B) | 0.815 s | **> 25 s** |

The finding rated this *minor* and said C6 stays "strictly faster than shipped at
the 3.2 kB benchmark". **My measurement says 100× slower.** C6 is dead.

## C. C8 — APPEND ONLY THE ARM C5 ACTUALLY LOST

```
prefix_run  ≡  NONABS*  ( WRAPPER space (nonspace+ space)* )?  ( [({] * )*
```

`[({] *` consumes no word, so it **cannot compete** with the wrapper's word run —
and it is the only arm whose text can end with zero trailing spaces, i.e. the
only one C5 lost. Still plain POSIX ERE: **one shared source, both substrates.**

**Measured, all by me:**

* **Language: 349,520 comparisons, 0 divergences** — over an alphabet with
  **glued** `{`/`(` and `2>>o` redirects, five tails, depths 1–4, against the
  real pipe composite.
* **THE HARNESS IS CALIBRATED, and the first one was not.** My initial
  enumeration reported *0 divergences for C5* — because it used `.search()` with
  a prefix run that can match empty, so the engine found the interpreter at a
  later offset and the prefix run was never load-bearing. **An instrument that
  cannot fail on a known-bad input is not evidence.** The anchored harness
  detects C5's defect (13,872 divergences, all deny→allow, all the glued class)
  and reports 0 for C8.
* Full differential **4161 / 0**. Full suite **9724 / 5**, the 5 being only
  golden and retrofit **digest** pins; action counts stable.
* Cost: the wrapper product cured (> 25 s → 0.0001–0.0022 s) **and the benign
  long run is FASTER than shipped** (0.435 s vs 0.815 s at 6407 B).

## D. A FOURTH COST CLASS EXISTS AND C8 DOES NOT FIX IT

Rev 2 §A said the four non-absorbing arms "consume exactly one unit and are
unambiguous". **False.** The redirect arm `[0-9]*[<>]+ *\S+\s+` is exponential
**by itself**, no wrapper involved — `[0-9]*`, `[<>]+` and `\S+` all overlap over
the same characters. Measured on shipped, `"2>>o " × k + "zzz"`:

```
k=10  53 B  0.003 s     k=18  93 B  0.832 s     k=24 123 B  > 40 s
k=14  73 B  0.053 s     k=22 113 B 13.348 s
```

and `bash -c "$(python3 -c "print('2>>o '*30 + 'zzz ; echo PWNED_LEGAL')")"`
prints `PWNED_LEGAL`, rc=0 — legal bash.

**I tried to fix it in the same change and backed it out.** Pinning the target's
first character out of the redirect class (`[^<> ]`) flips the pinned
**KNOWN-SPLIT** row `X-36x carrier <<<` from shell=deny to shell=allow — and that
row's own text says a change there is "either a fix (delete the row) or a
regression (do not re-point it)". **It is pre-existing and byte-identical in
shipped and C8, so it is a separate item, not a rider on this one.**

## E. SCOPE — CORRECTED AGAIN

**14 emitted artifacts change bytes, not four:** all **13** shell hooks plus
`gates.py`, because the shared header is embedded in every hook. Derived by
installing both trees and comparing artifact by artifact.

**`ci-mirror.sh` is among them and is SHELL-ONLY with no SDK twin** — so a
verdict change there is invisible to the differential's `shell == sdk`
comparison. It needs its own check, and rev 2 §E did not mention it.

## F. WHAT REV 3 STILL DOES NOT ESTABLISH

* The enumeration is depth ≤ 4 over 16 chunks. It is calibrated, which the last
  one was not, but it is not a proof.
* `ci-mirror` verdicts under C8 are **unmeasured**.
* The two refuters that died on a usage limit leave findings L3-1 and L3-2
  unverified.
* The redirect class (§D) remains **open** and must be filed, with its
  measurement, before this item closes.

---
---

# REV 4 — APPENDED 2026-08-18. C8 IS DEAD; C9 IS THE CANDIDATE.

**Nothing above is edited. This layer governs.** The C8 step-3 review ran but
**only 1 of 5 agents completed** — the equivalence lens; the ci-mirror, cost and
record lenses and one refuter all died on a usage limit. **So this layer rests on
one lens plus my own re-derivation, and three review dimensions are still
unrun.**

## A. THE EQUIVALENCE LENS CLEARED C8's LANGUAGE — AND IT CALIBRATED ITSELF

Worth recording because it is the discipline that was missing two rounds ago:

* **Mode A** (`re.fullmatch` on the prefix run — the mode the earlier blind
  harness got wrong): **9,480,715 comparisons**, 78-token alphabet with every arm
  both glued and spaced plus tab/newline, depths 0–8 exhaustive then sampled plus
  10 and 12 → **0 divergences, both directions**. Calibrated: the same harness
  reports **195,845** loss divergences on C5.
* **Mode B** (all three real emitted composites): **10,797,454 comparisons → 0**.
  Calibrated: C5 → 181,027, spread across all three.
* **Mode C** (dialect): GNU `grep -E` 966,006 → 0; **real bash** `[[ =~ ]]`
  26,163 → 0. Calibrated: C5 → 2,878 and 456.
* allow→deny (over-refusal) direction: **0 in every mode.**

## B. BUT C8 INTRODUCED A NEW FAIL-OPEN, FROM THE ARM I ADDED

The trailing `([({] *)*` and `nonabs*`'s own `[({] *` arm can **each own any
prefix of a glued brace run**, and the boundary between them is free. On a
*failing* match that is ~n^2.9. Re-derived by me, failing match, `{`×k:

| k | bytes | shipped | C5 | **C8** |
|---|---|---|---|---|
| 400 | 425 | 0.002 s | 0.002 s | 0.220 s |
| 800 | 825 | 0.007 s | 0.007 s | 1.529 s |
| 1600 | 1625 | 0.026 s | 0.025 s | 11.608 s |
| 2400 | 2425 | 0.060 s | 0.057 s | **> 30 s** |

**`{` is not in `_JUMP_BYTES = ()\"'`$`, so `_cost_guard` is blind**, and the
payload is under the length cap. The lens measured it crossing the
dependency-gate's 60 s timeout at ~2.8 KB end to end — a live fail-open, in the
same class the item exists to close, **introduced by my own repair**.

## C. C9 — MOVE THE TRAILING BRACE STAR INSIDE THE WRAPPER GROUP

```
prefix_run  ≡  NONABS*  ( WRAPPER space (nonspace+ space)* ( [({] * )* )?
```

The wrapper becomes a **fixed pivot**: with no wrapper only `nonabs*` owns
braces, so a brace run has exactly **one** owner and the free boundary is gone.
Still plain POSIX ERE — one shared source, both substrates.

**Measured by me, all axes:**

| | shipped | C9 |
|---|---|---|
| glued `{`×2400 (the C8 cliff) | 0.063 s | **0.059 s** |
| 27 bare wrappers | > 25 s | **0.0001 s** |
| 8 wrappers × 16 assignments | > 25 s | **0.0024 s** |
| benign 1 wrapper + 1600 assignments (6407 B) | 0.807 s | **0.371 s** |

* **Language: 349,520 comparisons, 0 divergences**, on the harness calibrated to
  detect C5 (13,872 divergences there). All 8 strings C5 lost are restored, 0
  mismatches against shipped.
* **Full differential 4161 / 0.** Full suite **9724 / 5**, the 5 being only the
  golden and retrofit **digest** pins; action counts stable.

## D. WHAT IS STILL UNRUN — DO NOT READ THIS LAYER AS AN APPROVAL

1. **Three of four review lenses never ran.** `ci-mirror` verdicts (shell-only,
   no SDK twin, structurally invisible to the differential's `shell == sdk`
   check), the full cost sweep across every gate against its own ceiling, and the
   record-accuracy pass — all still owed.
2. **C9 has had no adversarial review at all.** It is two hours old and its only
   scrutiny is mine. Every previous candidate in this item looked clean to me at
   this exact stage: the atomic groups, C5, C6 and C8 each passed everything I
   measured before a lens found the hole. **C9 is the fifth.**
3. My enumeration for C9 is depth ≤ 4 over 16 chunks; the lens ran depth 12 over
   78 tokens for C8. C9 has not had that treatment.
4. The redirect-arm exponential (§rev3 D) remains **open** and unfiled.

**The honest state: C9 is the best-measured candidate so far and is not
approved.** It needs the three dead lenses re-run against it, not against C8.

## REV 4a — the cost table, re-derived from the EMITTED objects (finding L1-F3)

**My rev-4 table mixed two constructions and one of them is a regex the emitter
never compiles.** `c9_check.py` built `prefix_run + interpreter_word`
**unanchored**; the artifact compiles `_PIPE_TO_SHELL` (downloader-anchored),
`_INSTALL_HEAD` (`^`-anchored) and `_GIT_VERB_TMPL % verb`. On brace shapes the
two disagree by ~400×. The "27 bare wrappers > 25 s" row came from the hand-built
regex; the "`{`×2400 = 0.059 s" row came from the emitted one. **Same class of
error as ledger entry 35 — measure the artifact, not a sibling of it.**

Re-measured on the emitted objects only, base vs C9:

| payload | bytes | `_PIPE_TO_SHELL` base → C9 | `_INSTALL_HEAD` base → C9 |
|---|---|---|---|
| bare wrappers ×27 | 132 | **> 30 s → 0.000 s** | > 30 s → 0.000 s |
| bare wrappers ×40 | 184 | **> 30 s → 0.000 s** | > 30 s → 0.000 s |
| 8 wrappers × 16 assign | 568 | **> 30 s → 0.000 s** | > 30 s → 0.000 s |
| glued braces ×2400 | 2425 | 0.063 → 0.059 s | 0.057 → 0.056 s |
| wrapper + glued ×2400 | 2429 | 0.062 → 0.050 s | 0.057 → 0.051 s |
| benign 1 wrap + 1600 assign | 6428 | **0.822 → 0.001 s** | 0.792 → 0.001 s |

End to end through the real SDK gate — the thing the 60 s ceiling actually
applies to:

| payload | bytes | base | C9 |
|---|---|---|---|
| bare wrappers ×27 | 132 | **> 95 s** | 0.002 s |
| bare wrappers ×40 | 184 | **> 95 s** | 0.001 s |
| 8 wrappers × 16 assign | 568 | **> 95 s** | 0.005 s |
| benign 1 wrap + 1600 assign | 6428 | 8.830 s | **0.047 s** |
| glued braces ×2400 | 2425 | 0.887 s | **1.131 s** |
| wrapper + glued ×2400 | 2429 | 1.099 s | 0.780 s |

**ONE ROW WHERE C9 IS SLOWER, recorded rather than dropped:** glued braces ×2400
end to end, 0.887 → 1.131 s, a 1.27× regression. It is ~1 s against a 60 s
ceiling and it does not grow like the C8 cliff (which was > 30 s at the same
size), but rev 4's blanket "faster than shipped" is **wrong as stated** and is
corrected here: C9 is dramatically faster on the wrapper product and on benign
long runs, level on the brace shapes at the regex level, and marginally slower on
one brace shape end to end.

## REV 4b — WHAT THE EQUIVALENCE LENS RETURNED (1 of 6 agents; the rest died on a usage limit)

It did not sample — it **decided**. An ERE/Python parser → Thompson NFA → lazy
product BFS, i.e. an exact equivalence procedure over **all strings**:

* parser validated against Python's own `re` on 60,000 random strings, 0 mismatches;
* **two-sided calibration**: shipped vs C5 **diverges** in both dialects (minimal
  witness `env (`), shipped vs C8 **equivalent** — C8 is language-correct and
  cost-broken, so the instrument is not a trivial everything-differs detector;
* **verdict: shipped vs C9 EQUIVALENT in both dialects, product graph fully
  explored** (9,295 ERE / 10,231 PY states, zero accept-disagreements).

Corroborated by two independent instruments: character-level exhaustive to length
9 over a 9-char alphabet (**435,848,050 strings**; C5 → 3,672 divergences, C9 →
0) and the three real emitted composites under Python `re`, `grep -E` and real
bash (5,626,214 / 1,569,678 / 1,046,606 comparisons; C5 → 550,987 / 253,617 /
237,041, C9 → **0**).

Also refuted by the lens, each worth keeping: language equality **is** sufficient
here because every use site is boolean (no `.group`/`.span`/`.start`/`.end` on
any of the three composites, and the shell side is `[[ =~ ]]` only); the 7→9
capturing-group change is inert (`BASH_REMATCH` has no live index read anywhere
in a generated install); **byte surgery** shows 14 of the 16 differing emitted
files are reproduced byte-exactly by substituting the prefix-run string alone,
the other two being the manifest and state JSON; and the shell-vs-SDK split
**set** is unchanged (590,579 rows, symmetric difference **0**, where C5 shifts
20,006).

**Still unrun: ci-mirror, the full cost sweep, and record accuracy** — those three
lenses and two refuters died on the usage limit and are being re-run.

## REV 4c — the record lens (re-derived by me). SCOPE WIDENS TWICE.

**L4-6 — the false claim I scoped is a POINTER; its target is unscoped.**
Plan §4 sends the fix at `lib/cmdpos.py:633-637`. That line only *refers* to the
ARITY section. The canonical statement is **`lib/cmdpos.py:81-97`**, verbatim:

> *"Unbounded consumption cannot make the MATCH fail open, and the reason is
> worth stating because it is not obvious: regex matching answers 'does there
> EXIST a parse', so a greedy prefix that swallows the command word simply
> backtracks. … The last line is the whole safety argument for MATCHING."*

**It is correct about MATCHING and silent about COST — and the cost of deciding
is the fail-open.** Correcting the pointer and leaving the target would make the
falsehood *canonical*. **Scope must become `:81-97, :627-631, :633-637`.**

**And `:627-631` stops describing the function under C9.** It reads *"The arms,
in order: a wrapper word … a NAMED GROUP head … a brace group or subshell; a
redirection; a `VAR=value` assignment; a shell keyword"* — one flat six-arm star.
Under C9 the four non-absorbing arms come **first** as `nonabs*` and the
wrapper/named-group arm is a single **optional trailing group** carrying the word
run and the brace star.

**THE NEW INVARIANT NOTHING IN THE TREE RECORDS, and this is the durable point:**
C9 permits **at most one wrapper arm at the star level**. Multi-wrapper runs
(`sudo env time bash`) survive *only* because the word run `(nonspace+ space)*`
re-absorbs the later wrappers as plain words. **A future editor who bounds that
word run — an obvious-looking cost tightening — would silently delete them.**
That invariant must be written at `:627-631`, or the next person removes it
without knowing.

**L4-7 — the backlog row for the redirect residual will NOT RENDER where it
naturally goes, and X-58's own citations have rotted.** Measured on the current
file: section X carries header+delimiter pairs at **`:314-315` and `:332-333`**,
and blank lines at **`:360`, `:397`, `:411`, `:413`**. GFM ends a table at the
first blank, so everything after `:360` is literal pipe text. **X-58 (line 410)
itself says the pair is at `:321-322` and the blanks at `:349`/`:386` — all three
citations are stale**, and a row appended after X-58 lands in the dead region
past `:397`.

So the redirect residual must be inserted **before the `:360` blank**, or given a
fresh header+delimiter pair, and X-58's citations corrected in the same edit.
**A rendering-defect row that does not render, citing lines that have moved, is
the exact shape X-58 exists to complain about.**

**L4-5 / L1-F3 — already answered in rev 4a.** The lens's own emitted-object
figure for the benign run is **1.372 s → 0.0015 s** (a ~900× gap, not the 2.2×
rev 4 recorded from the hand-built regex). Its correction stands: *"the direction
of every claim survives; only the numbers need re-sourcing"* — and it adds one
method point rev 4a should carry: **report min-of-N `process_time`, not a single
`time.time()` read**, because the box has been at load average 22 and the
absolutes move ~2× with it.

**STILL OWED AFTER THREE ATTEMPTS:** the **cost** and **ci-mirror** lenses have
now died on a usage limit three times running, and **no refuter has ever run on
this item**. Every finding above is single-sourced and re-derived by me, not
independently refuted.

## REV 4d — the two BLOCKING findings I had never seen, both re-derived by me

The notifications only ever surfaced 4 of the 15 findings this review produced.
All 15 are now extracted from the journal to
`preserved/c9-review-ALL-RESULTS.md`. **Two were blocking.**

### L4-1 — HALF WRONG, HALF IMPORTANT

It claims rev 4 §C's evidence ("349,520 comparisons, 0 divergences, C5 →
13,872") is *"not reproducible from anything in the workspace"*. **That is
false — and I re-ran it to check.** `enum2.py` / `enum_c9.py` exist, are
anchored, and print exactly:

```
C5     compared=349520  divergences=13872  deny->allow=13872
C9     compared=349520  divergences=0      deny->allow=0
harness calibrated: YES -- it detects the known defect
```

The lens searched and missed them. **The numbers stand.**

**But its real point lands, and it is worse than a citation error.** The
workspace also contained `c5_enum_calib.py` — a file with *"calib"* in its
name — which prints `compared: 177480  DIVERGENCES: 0` **on the known-broken
C5**. And `c9_check.py`, the artifact behind "all 8 strings C5 lost are
restored", uses the same bare `.search()` and therefore printed
`shipped=True C5=True C9=True` on every row — i.e. **it showed C5 losing
nothing**. Both are traps for the next session.

**Acted on:** five `.search()`-based harnesses are renamed
`BROKEN-search-based-*.py` with a header explaining the defect. `enum2.py` /
`enum_c9.py` (anchored, self-calibrating) are the sound ones. **The rev-3 §C
sentence "all 8 strings C5 lost are restored" must be struck** — it came from a
harness that cannot see the loss; the restoration is real but its evidence is
`enum_c9.py`, not `c9_check.py`.

The lens's own independent re-derivation corroborates C9 across three
instruments (2,146,320 comparisons, each red on C5 first): Mode A `fullmatch`
C5 → 25,161 / C8 → 0 / C9 → 0; Mode B anchored `.match` on three real tails
C5 → 765 / C9 → 0; ERE via `grep -E` C5 → 522 / C9 → 0.

### L4-2 — CONFIRMED. C9 DOES NOT MEET THIS PLAN'S OWN §6 GATE.

§6 says *"≤ 15 s at every cap-legal payload"*. Measured by me end to end through
the emitted SDK `dependency-gate`, `curl … | ` + `{`×k + `\nzzz`, CPU seconds:

| k | bytes | jump bytes | shipped | C9 |
|---|---|---|---|---|
| 2400 | 2425 | 0 | 0.35 s | 0.34 s |
| 4800 | 4825 | 0 | 1.39 s | 1.33 s |
| 9600 | 9625 | 0 | 5.47 s | 5.30 s |
| **19200** | **19225** | **0** | **21.72 s** | **21.26 s** ← past §6's 15 s |

**Zero jump bytes and 19 KB is far under `_CMD_MAXLEN` 81920, so `_cost_guard`
is blind** (`_JUMP_BYTES = ()"'` + backtick + `$`; `{` is not a member).

**It is NOT a C9 regression** — C9 tracks shipped within noise, and the lens
measured only ~5 % of the time inside `_PIPE_TO_SHELL`; the quadratic is in the
surrounding machinery. But **§6 as written is not met**, and no lens has ever
measured the **LENGTH** axis. *(The lens reported 56.5 / 61.0 s at 19 KB against
my 21.7 / 21.3 s — it was running at load average 22. Direction agrees, absolutes
do not; report min-of-N `process_time`.)*

**Required before this item closes — pick one, in writing:** (a) re-scope §6 to
say the ceiling is asserted on the **token-count axis only**, and that the length
axis is a separate pre-existing unfixed class; or (b) file that class as its own
numbered `docs/deferred-backlog.md` row with the table above — the same treatment
rev 3 §D demands for the redirect residual. **Step 4 passing must not be read as
"the cost class is closed": it closes the token-count axis and leaves a 19 KB,
zero-jump-byte payload that takes the SDK gate past this plan's ceiling.**

### ALSO FROM THAT LENS, NOT YET ACTED ON

**L1-F1 (major).** **No test in the suite distinguishes C9 from C5.** Both trees
give byte-identical `9724 passed / 5 failed`, the same five digest pins — so the
only thing that changes when the trailing `([({] *)*` is deleted is a **digest**.
The lens's end-to-end verdict differential flips **13 of 36 rows deny→allow on
C5 and 0 of 36 on C9**. Existing brace controls only pin a brace at position 0
(`{npx evil install`); **nothing pins a brace glued AFTER a wrapper**. It lists
eight rows measured deny/deny on shipped and C9 and allow/allow on C5 — those are
the step-4 language guard, and they must land **before** step 4, not after.

**L1-F2 (major).** The change is 24 lines with **zero comment**, and the
docstring above it still describes the six-arm flat star that C9 is not. Neither
load-bearing token — the trailing `([({] *)*`, nor its placement **inside** the
wrapper group — is defended anywhere in the file.

**STILL OWED: the cost and ci-mirror lenses (four failed attempts), and NO
REFUTER HAS EVER RUN on this item.** L4-1 shows why that matters: it is a
blocking finding that is half wrong, and a refuter would have caught that.

---
---

# REV 5 — APPENDED 2026-08-19. **THE OWNER DECISION IS TAKEN. §6 IS RE-SCOPED.**

**Operator ruling, in session, 2026-08-19 local:** *"ship C9 as a measured
improvement with three residuals filed."*

That discharges the §4 gate the checkpoint stopped at and selects rev 4d L4-2
option **(a) AND (b)** — both, not either, because the checkpoint's §5 requires
the re-scope in writing *and* the classes filed as numbered rows.

## A. **§6 IS RE-SCOPED. THIS SUPERSEDES §6 AS WRITTEN.**

Rev 1 §6 asserted *"≤ 15 s at every cap-legal payload … on THREE axes"*. **That
ceiling is asserted by this item on AXIS 1 ONLY — token count at fixed length.**

* **Axis 1 — token count at fixed length: CLOSED by C9**, and pinned by the
  step-4 cost row. Re-measured 2026-08-19 on the emitted artifacts, min-of-3
  `process_time`, `dependency-gate` closure, cap 30 s:

  | payload | bytes | shipped SDK | C9 SDK | shell (both) |
  |---|---|---|---|---|
  | `curl … \| ` + `env `×22 + `zzz ; pip install evilpkg` | 134 | **> 30 s (capped)** | **0.0005 s** | 0.03 s deny |
  | `curl … \| ` + `env `×27 + same tail | 154 | **> 30 s (capped)** | **0.0009 s** | 0.03 s deny |
  | `curl … \| ` + (`env ` + `A=1 `×16)×4 + same tail | 318 | **3.8921 s** | **0.0011 s** | 0.04 s deny |
  | `curl … \| ` + (`env ` + `A=1 `×16)×6 + same tail | 454 | **> 30 s (capped)** | **0.0016 s** | 0.05 s deny |
  | `curl … \| ` + (`env ` + `A=1 `×16)×8 + same tail | 590 | **> 30 s (capped)** | **0.0020 s** | 0.06 s deny |

  Every row denies on the shell on **both** trees, so every row is the
  shell-DENY / SDK-BYPASS pair this item exists to close.

* **Axis 2 — plain length to `_CMD_MAXLEN`: NOT CLOSED, and not a C9
  regression.** Filed below as residual **R2**.
* **Axis 3 — jump density to `_CMD_MAXJUMP`: NOT MEASURED BY THIS ITEM** and not
  claimed either way. It was never the reported axis and no lens has run it.

**Step 4 passing MUST NOT be read as "the cost class is closed."** It closes
axis 1 and leaves the three residuals below reachable.

## B. THE THREE RESIDUALS, AS THEY WILL BE FILED

Numbered rows in `docs/deferred-backlog.md`, numbers taken at step 5, inserted
**before the `:360` blank** per rev 4c L4-7, with X-58's stale citations
corrected in the same edit.

| # | class | payload | shipped | C9 | jump bytes |
|---|---|---|---|---|---|
| **R1** | wrapper × spaced-brace product | `curl … \| ` + `A=1/env `×64 + `{ `×800, 2136 B | > 180 s | 53.35 s | **0** |
| **R2** | length axis, glued braces | `{`×19200, 19225 B | 21.72 s | 21.26 s | **0** |
| **R3** | redirect arm | `"2>>o "`×22, 113 B | 13.35 s | 13.35 s | **0** |

Each row must carry, in the row itself: that `_cost_guard` is blind to it (`{`
is not in `_JUMP_BYTES`, every payload far under `_CMD_MAXLEN` 81920); that C9
is equal or better and none is a C9 regression; and — for **R2** — that **the
shell is NOT the safe substrate on this axis**, the emitted `dependency-gate.sh`
being quadratic in glued `{` (6.88 s at 19,204 B, 29.73 s at 40,004 B,
extrapolating to ~126 s at 81,900 B, past the 60 s timeout, byte-identical in
shipped and C9).

## C. STEP 4 — WHAT LANDS, AND WHY IT IS TWO CHECKS AND NOT ONE

**1. The COST row — `tests/test_substrate_differential.py`. THIS is the failing
check.** Red on the current tree, green after. Measured above.

**2. The LANGUAGE guard — `tests/test_composition.py`. This one is GREEN now by
construction, and that is not a defect in it.** Per rev 4d L1-F1 **no test in
the suite distinguishes C9 from C5**: both trees give byte-identical
`9724 passed / 5 failed`, so the only thing protecting the trailing
`([({] *)*` is a **digest**, and a digest pin is not a guard. The guard's
calibration is that it is **RED ON C5** — re-derived 2026-08-19, all 8 rows,
both substrates:

```
shipped  deny/deny x8      c9  deny/deny x8      c5  allow/allow x8
```

Three of the eight are verified live RCE. A guard that cannot fail on a
known-bad input is not evidence — so this one was run against C5 before it was
written, not after.

## D. WHAT THIS LAYER DOES NOT AUTHORISE

It does not authorise a closeout sentence saying the cost class is closed, the
ReDoS class is closed, or that C9 makes the SDK safe on the length axis. The
verdict in `docs/production-readiness.md` §1 does **not** move on this item:
**a fail-open that shrinks from 134 bytes to ~2 KB is still a fail-open.**

---
---

# REV 5a — APPENDED 2026-08-19. STEP 7 RAN. **12 FINDINGS, ZERO REFUTED — AND "ZERO REFUTED" MEANS THE REFUTERS DIED, NOT THAT THE FINDINGS FELL.**

**Read the workflow's own summary with suspicion; I did, and it was wrong.** It
reported `survivors: []` and put all 12 findings in a `refuted` bucket. **Every
one of those buckets carried an EMPTY `why_refuters_killed_it`.** All 25 refuters
failed on a session usage limit, so my aggregator's `survives` test saw zero
verdicts and defaulted every finding to "refuted". **Nothing was refuted. Twelve
findings stand unchallenged.** A harness that reports the opposite of the truth
when its agents die is the same class of instrument defect as the five
`.search()` harnesses this item already quarantined.

Ran: 4 lenses, **3 returned** (correctness, record-accuracy,
overcorrection/missed-sites). **`counts-pins-units` never ran** — it died with
the refuters, so THE COUNTS LENS IS STILL OWED and this item has still never had
a refuter, across six attempts now.

**The one thing that DID get independent corroboration is the code.** The
correctness lens built its own ERE→NFA→product-BFS equivalence decider,
calibrated two-sided on four deliberately broken variants, and ran it on both
parameterizations the tree actually renders (bash ERE 9,107 product states; SDK
Python 9,911): **zero accept-disagreements**, corroborated by three engines and
by 648 real command shapes through both emitted substrates of both trees with 0
diffs. It also verified the SIGALRM harness does interrupt CPython's regex
engine and leaks no timer. **The fix is correct. Every finding below is about
what the tree SAYS about it.**

## A. THE FOUR CORRECTIONS I OWE, ALL RE-DERIVED BY ME

1. **THE MECHANISM I WROTE INTO THE ARITY SECTION IS WRONG.** I wrote *"THREE
   arms could absorb the same token."* The exponential is **INTRA-arm**. Split
   the shipped regex's top-level alternatives and match them against
   `env env env zzz`: **arm 1 consumes `env env env `, arms 2 and 3 return
   `None`** — only ONE arm can even start on the measured payload. Keep arm 1
   alone under a star and the identical rate reproduces: 0.0049 / 0.0185 /
   0.0735 / 0.2956 s at n=14/16/18/20 against the six-arm 0.0074 / 0.0298 /
   0.1120 / 0.4476 — **both exactly 2.00x per token**. Each `env ` is either a
   new star iteration or an ordinary word inside the previous iteration's word
   run: 2^(k-1) splits from one arm. **This matters because it is the diagnosis
   a future editor inherits** — "different arms competing" licenses
   re-introducing a single self-ambiguous arm under a star, which is exactly
   candidate C8.

2. **THE COMMENT DEFENDING `nonabs` IS FALSE ON BOTH HALVES, AND MY OWN X-59 AND
   X-61 ROWS REFUTE IT IN THE SAME COMMIT.** I wrote *"The four arms that cannot
   absorb a wrapper word … that star is safe because no two of them can consume
   the same token."*
   * *"cannot absorb a wrapper word"* — `A=1/env ` matches the assignment arm
     **and** the path-prefixed wrapper arm, both `True`. On the NEW prefix_run
     that shape is quadratic: 0.0026 / 0.0102 / 0.0412 s at n=200/400/800
     against 0.0000 / 0.0001 / 0.0001 for the `env ` control. **That is X-59.**
   * *"that star is safe"* — first-character disjointness is an **inter**-arm
     argument and the redirection arm is ambiguous **with itself**: `2>>o `
     parses as `('2','>>','','o',' ')` **and** `('2','>','','>o',' ')`, same end
     offset. `nonabs*` alone with a failing tail: 0.0043 / 0.0174 / 0.0697 /
     0.2790 / 1.1166 s at n=14..22, **4.00x per +2 tokens at 110 bytes**. **That
     is X-61.** The file a future editor reads before touching `nonabs*` was
     telling them it is already safe.

3. **A FOURTH SUPERLINEAR CLASS EXISTS AND I FILED THREE.** `_GIT_VERB_TMPL`
   carries `(?:\s+-[Cc]\s+\S+|\s+-\S+)*` — a two-arm star in which a `-C` token
   is consumable by **both** arms. **The same multi-absorbing-arm defect this
   item exists to fix, one splice away in the same composite.** Measured by me
   on the emitted object, `git ` + `-C ` xn + `zzz ; pip install evilpkg`:
   **0.073 s at 107 B, 0.501 s at 119 B, 3.447 s at 131 B, 8.975 s at 137 B,
   23.515 s at 143 B** — ~1.62x per token, **ZERO jump bytes**. Two-sided
   calibrated: the same shape with `-x ` is **0.0005 s at 9,029 B**, so the cost
   is the arm overlap and nothing else. Reachable from `_git_verb` at emitted
   `gates.py:1635` (spec-gate-commit), `:3364` (test-gate), `:3397` (eval-gate),
   and **`_GATE_TIMEOUTS` carries no entry for spec-gate-commit or eval-gate at
   all**. Byte-identical on main and HEAD, so **not a regression** — the same
   status X-59/X-60/X-61 hold. **Files as X-62, and "three" becomes "four"
   everywhere I wrote it.**

4. **"ALL 13 SHELL HOOKS" IS A NUMBER OF THE WRONG THING, AND THIS REPO ALREADY
   PINNED THAT EXACT SENTENCE.** `tests/test_greenfield_golden.py:1880-1890`
   reads, in the tree I was editing: *"'13 emitted `.sh` hooks' IS NOT A FIXTURE
   COUNT AND NO FIXTURE HAS ONE. 13 is the hook count of the REVIEW PROBE
   install … whose artifact counts are 11 / 15 / 11 … a number that is real, but
   of the wrong thing."* I put 13 into a changelog paragraph sitting **directly
   beside the freeze-exception 72 digest re-baselines, which ARE statements about
   those fixtures**. The blast-radius numbers must be stated per fixture, and the
   "other eight" that never call `git_verb` is fixture-dependent too.

## B. SCOPE IS WIDENED, WITH THE REASON, AND THE E4 IS DISCLOSED NOT HIDDEN

**Added to the globs:**
* **`tests/test_issue_fixes.py`** and **`docs/agentic-harness-security-kb.md`** —
  both carry, in **present tense**, the rationale this change **falsified**. The
  `#43 F1` rationale (*"an assignment is consumable by BOTH the wrapper arm's
  positional branch and the outer assignment arm"*) describes a spelling that no
  longer exists: the word run is now `(?:\S+\s+)*` and the assignment arm sits
  in `nonabs*` **before** the pivot. It survives in six places, two of them
  **shipped bytes in customer trees**. The KB is worse — it teaches the exact
  lemma this item corrects, **including as a `- [ ]` reviewer checklist item**,
  so after this PR the tree would hold two contradictory statements and the one
  in the checklist would be the false one. **Leaving a falsehood I created is not
  narrower scope, it is an undisclosed defect.**
* `lib/sdk_gates_template.py` and `lib/templates.py` were already declared and
  are now actually touched; **the emitted bodies move again and the same freeze
  exception 72 covers the re-baseline.**

**AND A PRE-EXISTING E4 IS DISCLOSED RATHER THAN QUIETLY ABSORBED.** The PR body
says *"Scope: 7 files, all inside the declared globs, no E4."* **Both halves are
false.** `git diff --name-only origin/main...HEAD` is **11 files**; 7 is the
count of my step-5 commit alone, presented as the PR's. The PR carries `c5734cb`
— a governance commit from a **previous** session, already on the branch when I
took the item — and it touches **`tests/test_trust_ramp.py`, which is not in the
globs**. By the plan's own rule that is an E4. It is not mine and it is not new,
but **the PR body is the document a human merges on**, and this file's own ledger
grades a false count in one `harmful`. The body cannot be edited (#67/#68
precedent); it is retracted in a PR comment and corrected here.

## C. WHAT DOES **NOT** CHANGE

**No line of the fix moves.** The correctness lens's verdict stands and I did not
find a reason to doubt it. `prefix_run()` is untouched by rev 5a; every edit
below it is a comment, a document, a backlog row, or a test.

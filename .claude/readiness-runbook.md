# Readiness runbook — burn down `docs/production-readiness.md`

**Internal automation. NOT protocol surface. NOT a Bootstrap Protocol
feature.** Companion file: `.claude/readiness-queue.md`.

Its single purpose: move `docs/production-readiness.md` §1 off **"not
production ready"** in as few sessions as possible. Every rule below earns its
place by protecting that goal or by preventing a rework loop that has already
cost this repo a session.

---

## 0. THE NON-DRIFT INVARIANT — CHECK THIS BEFORE ANYTHING ELSE

This runbook must never become part of the product. Structurally it already
is not, and that was verified on 2026-08-14, not assumed:

* Emission comes **only** from strings in `lib/templates.py` — the installer
  never reads this repo's own `.claude/`. (`grep` for a read of `.claude/` in
  `lib/installer.py` returns nothing.)
* **No protocol surface references these files** — not
  `Bootstrap-Protocol-v2-8-0.md`, not the Companion, not `SEAM-CONTRACT`, not
  `lib/`, not `bin/`.
* The golden suite passes **unchanged** with both files present: they move no
  emitted artifact and no digest.
* Precedent: `bin/trust-ramp` is already classified in its own suite as *"repo
  governance rather than protocol surface: it emits nothing, is not imported
  by `lib/`, and touches no golden digest."* These files are the same kind.

**Re-verify after any change to this runbook:**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_greenfield_golden.py   # must stay 13/0
grep -rln "readiness-runbook\|readiness-queue\|context-check" lib/ bin/ Bootstrap-Protocol-*.md SEAM-CONTRACT-*.md
# ^ must print nothing
```
The three harness files are `readiness-runbook.md`, `readiness-queue.md` and
`context-check.py`. `context-check.py` reads only the session transcript, imports
nothing from `lib/`, and is emitted nowhere.

**Three things this runbook may never do:** add a file under `lib/` or `bin/`;
add a golden digest or freeze exception *of its own*; be cited from a protocol
document. If an item seems to require one of those, it is a product change
wearing a harness costume — stop and flag it (**E5**).

---

## 1. WHAT ACTUALLY MOVES THE VERDICT

Ordering by tier prose wastes sessions. The readiness document's verdict rests
on specific legs, and only work under **A** moves it:

**A — moves the verdict.** Nothing else can.
* **C-1, no LICENSE.** §1 says the verdict *"cannot have moved"* while a
  second tagged, adoptable release ships with no legal grant. ~1 h of work,
  blocked on one decision: *which licence*.
* **X-37 (item 1b / Class B).** Derived 2026-08-14, still ``open`` —
  *"pre-existing, forbidden direction, release-relevant; the distinct half of
  item 1."* §8 calls item 1 release-blocking until both 1b/X-37 and B3 land;
  **B3 has landed** (`lib/templates.py:1700`), so X-37 is the survivor.

**B — makes shipping-with-known-risk honest.** Does not flip the verdict;
turns negligence into disclosure.
* The T1 emitted-artifact labelling pass, and emitting `threat-model.md`.

**C — record hygiene.** Moves the verdict **not at all**. Real work, but doing
it first is motion, not progress: X-58 table rendering, `## Priority reading`,
X-49, the changelog-citation anchor.

**Ordering rule: never take a C item while an A item is ready.** If every A
item is blocked on a decision, say so and take B — do not quietly slide to C
and report progress.

---

## 2. CEREMONY IS SCALED TO BLAST RADIUS — THIS IS THE SPEED LEVER

Uniform four-lens review on a table-rendering fix is the main way this goes
slowly. Scale it:

| Class | What it touches | Review | Ledger entry | Checkpoint |
|---|---|---|---|---|
| `CODE` | gate logic, `lib/`, emitted bodies | **full**: 4 lenses + refuters, ultracode | yes | yes |
| `EMITTED` | comment/text inside emitted templates | **full** (freeze exception is why) | yes | yes |
| `MEASUREMENT` | harnesses, numbers entering the record | 2 lenses (counts + overclaim) | yes | yes |
| `DOC` | repo docs, no emission | **step 3 plan review: 2 lenses (mandatory, it discharges approval). Step 7 post-PR: 1 lens**, or none if the step-4 check is mechanical and green | fold into next entry | only if session ends |
| `TEST-CONTRACT` | a suite's own contract | 2 lenses | yes | yes |
| `DECISION` / `EXTERNAL` | — | — | — | **E3 on sight** |

**Batching is allowed and encouraged for `DOC`.** Several C-tier doc items may
share one branch, one PR, one review and one checkpoint. They are only
separate items because they were discovered separately. `CODE` and `EMITTED`
items are **never** batched with anything.

---

## 3. THE LOOP

**S0 — preflight** (skip nothing; a red tree makes every later claim void)
1. `git status --short --untracked-files=no` empty → else **E6**. (Tracked
   cleanliness: session plans under `.claude/sessions/` are untracked by
   design and must not fail preflight. Untracked files are still *inspected* —
   an unexpected one is E6 — they simply do not auto-fail the check.)
2. `git fetch`; no unpushed commits; no open PRs from this runbook
3. `./bin/run-tests` → 25 suites / 0 failed → else **E7**
4. `bin/trust-ramp check --rung R1` → record the answer (see §5)
5. Take the top item from `.claude/readiness-queue.md` that is `eligible: yes`,
   honouring the A-before-C rule. `eligible: no` → **E3**.

**CONTEXT GATE — run at EVERY step boundary, not once**
```bash
PYTHONDONTWRITEBYTECODE=1 python3 .claude/context-check.py   # exit 1 = E9
```
Exit 1 means **do not start the next step**: checkpoint, flag, hand off. The
number is exact — it is the last assistant turn's
`input + cache_creation + cache_read`, which is what the model was actually
charged to read. The window is assumed **conservatively at 900k** (derived: the
highest occupancy ever observed here is 890,012 with zero compaction, ruling out
the 200k/400k/500k constants; 900k is the smaller of the two survivors), so the
flag fires early under either. **A late flag costs a session; an early one costs
nothing.** `claude-hud` shows the same thing passively and turns red at 85% —
that is the display, this is the gate.

**1 — branch** from `origin/main`: `<type>/<item-id>`.

**2 — plan** (Opus 5): quote the defect from the tree with `file:line` — never
from the queue's prose; declare **scope globs**; declare class; list the owner
decisions it needs (non-empty → **E3**); state what would falsify the plan.

**3 — plan review: EVERY CLASS, NO EXCEPTIONS.** Does the defect exist as
quoted; is the scope complete; is the class right; what will bite later.
Read-only lenses, sized per §2 (a `DOC` item gets 2; `CODE`/`EMITTED` get more).

**It used to say "`CODE`/`EMITTED` only, skip for `DOC`". That is withdrawn**,
because step 3 now carries the approval function (§5): if review is what
substitutes for operator sign-off, then a class that skips review would proceed
with neither, which is strictly less scrutiny than before the rule changed. The
first item to hit this was `c1-license` — A-tier and `DOC`.

**4 — the failing check first.** "TDD" here means *a mechanical check that
fails now and passes after*:
* `CODE` → a differential/behaviour row that is red on the current tree
* `EMITTED` → a golden or `test_hook_behavior` pin
* `MEASUREMENT` → the harness, run once to produce the **red** number, stamped
  with `git rev-parse HEAD`
* `DOC` → a `test_doc_citations` row, or a counting rule **validated against a
  known value** (`count.py` must reproduce 88 at `v2.7.4` before you trust it)
* `TEST-CONTRACT` → plus a case proving the OLD form passed wrongly

**Paste the failing output into the commit.** A check that never failed proves
nothing.

**5 — implement**: smallest diff that turns it green. Read the diff before
committing (R0). Suite 25/0. Outside scope globs → **E4**.

**6 — PR.** The body is an immutable claim surface. Two sessions have been
graded `harmful` for a false claim in one. Assert no count or provenance not
derived this session; **never certify the diff's quality before the review has
run**; cite the artifact you actually measured, not a sibling of it; state what
the change does *not* do.

**7 — adversarial fan-out**, sized per §2. Standing lenses: correctness ·
counts/pins/units (*a number of the wrong thing is still wrong*) · record
accuracy · overcorrection and missed sites (MENTION vs USE; sweep joined-line,
case-insensitive, over `git ls-files` **and** emitted bodies **and**
`gh pr view --json body`). Reviewers read-only; DW-P1 (emit nothing), DW-P4 (no
fan-out in front of a gated tree), DW-A1 (**re-derive every finding yourself
before acting** — two verifiers once disagreed 2-vs-14 on a count), DW-A2 (one
run, one entry).

**8 — fix loop, bounded at 5**
```
i=0
while confirmed and i<5: i+=1; fix → ./bin/run-tests → re-review THE FIX
if confirmed: E2      # flag, do not merge
if findings(i) >= findings(i-1): stop now   # divergence, not progress
```
8.3 re-reviews the fix, not just the suite: the ledger grades one session
`harmful` *for a rate* — three correction commits each adding new false claims.

**9a — post merge-readiness evidence, then STOP.** CI green **on the PR head
sha**, 0 confirmed findings, suite 25/0, tree clean, `git diff origin/main...`
summarised. **`#50 T8` used to be named here as a wall-clock flake to
tolerate — one red a re-run, two an E7. That row is DELETED** (2026-08-21):
it bounded a linear reduction at exactly its linear ratio, on a single
un-repeated sample, and **this sentence is what took an unrelated item to E7
over it**. It was 6 of the 14 CI failures this repo has ever had, the only red
check in all six, once on `main`. **No check in the suite is now known to flake
on an idle box, so a red CI run is worth investigating rather than
re-running.**

That is narrower than "flake-free" and deliberately so. Wall-clock assertions
remain, and the closest one — the `_el50 < 30.0` trio a few lines below the
deleted row — measures **3.2 / 4.2 s idle but 14.6 / 19.3 s pinned to two
contended cores** (measured 2026-08-21), i.e. headroom of 9.5x/7.1x falling to
**2.0x/1.6x** under exactly the conditions that killed T8. It has not flaked;
it is not immune, and it is the next candidate if one does.
**E7's threshold in §6 is unchanged at two reds on one head** — a single red is
still not an E-code, it is now worth investigating rather than re-running.
Then flag the operator and **wait**.

**9b — the operator reviews the diff and merges.** This is not a courtesy step
and it is not conditional on the rung: the ledger states the human diff review
before merge is the one thing that does **not** change at any rung. An
agent-performed merge is outside every rung's grant, so the runbook does not
perform one. *(Merges the operator explicitly directs in-session are that
review; the prohibition is on the loop merging by itself.)*

**10 — update `.claude/readiness-queue.md`**: item → `done` with PR and merge
sha; file any residual the work exposed as a new item. **State whether the
readiness verdict moved.** If it did, amend `docs/production-readiness.md` in
the same PR — that is the entire point of the exercise.

**10b — ledger entry** per §2, with the pin moved in the same commit. Grade by
the file's vocabulary: `harmful` if anything wrong reached **origin**, not
merely `main`.

**11 — checkpoint** `.claude/checkpoints/checkpoint-<UTC>-<slug>.md`, stamped
from the clock, superseding its predecessor (never edit an older one), ending
with the exact resume line.

**12–13 — handoff.** `/clear` is operator-typed and cannot be self-invoked;
`CronCreate` jobs are in-memory and die with the session, so nothing carries
the loop across a context clear. End by printing exactly:
```
NEXT SESSION — copy these two lines:
/clear
Load .claude/checkpoints/<file> and start item <id>.
```

---

## 4. MODEL ASSIGNMENT

**Never give Fable 5 a step that reads this repo's security substrate.**
Derived 2026-08-14: **14 of 14** `model_refusal_fallback` events on this
machine are `originalModel: claude-fable-5`, category `cyber`, **all in this
repo**, and the reroute **latches for the whole session** — a Fable agent that
trips it silently stops being the model you assigned, mid-run, without failing.
The target is server-chosen and has already flipped here (8 → Opus 4.8,
6 → Opus 5). The substrate is `lib/templates.py`, `lib/sdk_gates_template.py`,
`lib/cmdpos.py`, emitted hooks, the cost harnesses, and **any backlog or queue
row quoting a payload — which includes `.claude/readiness-queue.md` and this
runbook**, both of which every session is required to read. i.e. essentially
everything here.

* **Opus 5** drives every step: plan, tests, implement, PR, merge, record.
* **Ultracode** on steps 3, 7, 8 only — the ones whose value is
  exhaustiveness. Waste on 1, 6, 9.
* **Fable 5: DO NOT USE IN THIS RUNBOOK. An earlier draft carved out "narrow
  payload-free lenses"; that carve-out is withdrawn, on two derived grounds.**
  1. **The detector does not work where the lenses run.** Fan-out lenses are
     *sidechains*, and **0 of 14** refusal-fallback events were recorded on a
     sidechain — while Fable has **8,907 sidechain turns in this repo** against
     3,149 top-level. So the event is plentiful top-level and absent on
     sidechains: a lens that latches degrades **silently and undetectably**.
     E8 cannot see the only case the carve-out created.
  2. **The carve-out was empty anyway.** Every category it named resolves to a
     payload-bearing file — and `.claude/readiness-queue.md` itself quotes
     `bash -c "$(curl)"`, so *reading the queue* can trip the classifier.
  An unverifiable reviewer is worth less than no reviewer in a repo whose whole
  discipline is that findings are claims until rebuilt.
* **Haiku 4.5** for pure extraction (collect grep output, reformat a table).
  Never for a verdict.

---

## 5. AUTONOMY LIMIT

`bin/trust-ramp check --rung R1` returns **DENIED** (derived 2026-08-14: 28
entries, **0/8 consecutive clean**, 9 `harmful` in the trailing 10). R1 is
named *"Loop (fixed prompt, unattended iteration)"* — the exact thing this
runbook automates.

**An earlier draft of this runbook said "unattended within an item, operator
between items." That was wrong, and the ledger says so in its own table:**

> **R0** | Supervised per-task | *Plan approved before work starts; diff
> reviewed before every commit*

> Note what does **not** change across the rungs: *the diff is reviewed by a
> human before it merges, at every rung.* — PRD §10, *"adding more autonomy
> means investing in better review surfaces, not skipping review."*

So R0 grants **three** operator gates, not one, and the third is invariant at
*every* rung including R3 — no amount of ramp progress removes it:

1. **Plan approved before work starts** — **OPERATOR RULING 2026-08-14: an
   APPLIED PLAN REVIEW (step 3) satisfies this; a separate sign-off is not
   required.** The gate is not waived, it is *discharged by review* — so step 3
   is now mandatory for every class (see above), and "no review was run" means
   the plan is NOT approved and step 4 must not begin.
   Questions the review cannot answer — facts only the operator holds, such as
   the legal copyright holder — remain **E3** and are still asked; a review
   cannot derive them from the tree.
2. **Diff reviewed before every commit** — before step 5 commits.
3. **Diff reviewed by a human before it merges** — step 9b. **Never automated,
   at any rung.**

What earning R1 would buy is *unattended iteration inside a scoped task*, not
self-merge. **Do not "fix" this by editing the ledger** — the pin and
`trust-ramp check` both detect it.

---

## 6. ESCAPE HATCHES

Any E-code **halts the item immediately** — no skipping ahead, no next item.

| Code | Trigger | Action |
|---|---|---|
| **E1** | a step's exit criterion unmet after its retry budget | halt |
| **E2** | fix loop hit 5, or diverged | halt, do **not** merge |
| **E3** | owner decision required | halt, ask the **one specific question** |
| **E4** | diff outside the scope globs | halt, include `git diff` |
| **E5** | governance refusal: action counts moved on a "comment-only" change; or the item would add to `lib/`/`bin/` (§0) | halt |
| **E6** | tree dirty with changes this session did not make | **PRESERVE, do not revert**; copy to scratchpad; halt |
| **E7** | suite red at S0, or CI red twice on one head | halt |
| **E8** | a refusal-fallback fired in the **top-level** session (the only place it is recorded — see §4) | later verdicts suspect; halt. Detect with the command below |
| **E9** | `context-check.py` exits 1 (>=80% of the conservative window), or the item otherwise cannot finish | checkpoint early, hand off mid-item — **this is the one E-code that is expected in normal operation, not a defect** |

**E8's detector.** It reads the **top-level** transcript, which §4 shows is the
only place the event is recorded. **It is a DELTA against a baseline taken at
S0, not a raw count** — a session that opened on Fable 5 and was rerouted
*before* the operator switched models carries a permanent event in its file,
and a count-based trigger would then fire at every step boundary forever. That
is not hypothetical: it happened on 2026-08-14, and the raw-count version of
this detector false-fired on the very session that wrote it.

```bash
# at S0, once:
echo $(grep -c '"model_refusal_fallback"' \
  "$CLAUDE_CONFIG_DIR/projects/-home-dengc-Documents-Projects-Project-Bootstrap-Protocol/$CLAUDE_CODE_SESSION_ID.jsonl") \
  > /tmp/e8-baseline
# after every fan-out:
NOW=$(grep -c '"model_refusal_fallback"' \
  "$CLAUDE_CONFIG_DIR/projects/-home-dengc-Documents-Projects-Project-Bootstrap-Protocol/$CLAUDE_CODE_SESSION_ID.jsonl")
[ "$NOW" -gt "$(cat /tmp/e8-baseline)" ] && echo "E8 — fallback fired during this run" || echo "clear"
```

**On any E-code, all three:** write
`.claude/checkpoints/STOP-<item>-<UTC>.md` (code, evidence, what was done, what
is uncommitted, **the single question that unblocks it**); send a
`PushNotification` leading with the code and item; leave the branch and PR
exactly as they are — **a halted item is evidence, not mess.**

**E6 has a worked example.** On 2026-08-14 this session found two protocol docs
renamed-and-uncommitted in a tree it had just found dirty after a merge, never
present in any commit. It preserved them to the scratchpad and restored the
tracked names rather than commit what it had not made. They were the operator's
deliberate rename. Preserving beat deleting; asking beat guessing — and
reverting first was still wrong, which is why E6 says **halt**, not restore.

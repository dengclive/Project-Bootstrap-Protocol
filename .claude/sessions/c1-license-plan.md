# PLAN — `c1-license` (readiness C-1) · awaiting operator approval

Runbook step 2. **R0 requires this plan to be approved before step 4 begins.**
Branch `docs/c1-license` off `origin/main` @ `45a368d`. Class `DOC`, A-tier,
not batched.

---

## 1. The defect, quoted from the tree

`git ls-files | grep -icE 'licen[cs]e'` → **0**, re-derived on this branch.

`docs/production-readiness.md:377` — *"**There is no LICENSE at the tag**, so
there is no legal grant to adopt at all. **STILL TRUE @ e47d827** — and none at
`main` either."*

`docs/production-readiness.md:345-346` — *"C-1 alone settles it either way."*

## 2. What this item does NOT do — state it before the work, not after

**Closing C-1 does not flip the verdict.** §1 lists three negative legs, and
C-1 is one:

1. the emitted gates cannot be relied on as a security boundary — **X-37
   (Class B) is still `open`**, remote payload still runs;
2. the autonomous-mode wrappers dispatch nothing (C-2);
3. no LICENSE (C-1) ← *this item only*.

"C-1 alone settles it either way" means C-1 is **independently sufficient** for
"not ready", not that it is the only ground. After this item the verdict stays
**not production ready** on legs 1 and 2. **An amendment that reads as though
the verdict softened would be an overclaim** — the exact failure this repo
graded `harmful` twice this week.

The deliverable is therefore **the amended record**, not the LICENSE file.

## 2b. THE SWEEP — 5 genuine sites, and a trap that would have wrecked the diff

Joined-line, case-insensitive, over `git ls-files` (the workflow that was to do
this was stopped, so it was run inline instead).

**THE TRAP: `C-1` IS AMBIGUOUS ACROSS FOUR NAMESPACES IN THIS TREE.** A naive
`grep -lF 'C-1'` over `git ls-files` returns **27 files**; the genuine count is
**5**. (An earlier draft said 28 — that number came from the *working tree*,
which counts this untracked plan file. Stated method must match stated number.)
It matches as a substring of **`IC-1`** (Implementation Contract check, **72
occurrences** over tracked files — an earlier draft said "~40", understated) and
**`AC-1-1`**; and there are two *other* real `C-1`s — backlog
cluster-C's `C-1` (**GR2-03a surfacing notice**, `docs/deferred-backlog.md`) and
a README/`test_installer.py` review finding `C-1` (**`_deep_default`
operator-precedence**). **Rewriting any of those would be a self-inflicted
defect in emitted-adjacent code.** This is the same collision the repo already
documents for readiness-`C-3` vs cluster-C `C-3`; the disambiguation rule
applies here and the diff must use licence-specific anchors, never bare `C-1`.

Counts below are `grep -icE 'licen[cs]e'` (matching LINES) over `git ls-files`,
with occurrences where they differ. **An earlier draft of this table gave 12 / 2
/ 3 / 2 / 1, which no stated method reproduces** — those were match counts from
a different ad-hoc regex. A number is of something; the method is now named.

| file | lines / occ | class | action |
|---|---|---|---|
| `docs/production-readiness.md` | 8 / 10 | **USE** | the deliverable — §1 leg, RE-BASE "C-1 alone settles it"; the SUBJECT NOTE gets a MARKER not a correction (see §6) |
| `.claude/readiness-queue.md` | 4 | **USE** | step 10 + the NOTICE prescription (Q2) |
| `.claude/readiness-runbook.md` | 3 | **USE** | §1 A-tier text; the count rose from 2 because of this session's own step-3 edit |
| `docs/deferred-backlog.md` | 2 | **USE** | T0 tier line + the `C-1` T0 paragraph |
| `.claude/trust-ramp.md` | 1 / 2 | **MENTION** | **DO NOT TOUCH** — dated ledger entry |

**17 tracked files match `licen[cs]e` in total; 12 are the ordinary verb**
("not a license to weaken escalation" in the PRD ×5 and Companions ×5,
`lib/installer.py:1426`, `docs/round-4-intended-relaxations.md:167`). That is
why "no existing licence declaration to contradict" holds.

**A discrepancy the sweep surfaced:** `docs/deferred-backlog.md` sizes this at
**"~30 minutes"**; the queue says **~1 h**. Reconcile in the same commit rather
than leaving two numbers.

**What this sweep could NOT see, stated rather than certified away:** PR bodies
(`gh pr view --json body`) were not swept — the runbook requires that surface
and it is the one that defeated four sweeps in the X-52 sessions. Do it before
step 6. Emitted bodies are covered transitively (`lib/templates.py` is tracked
and returned no licence hits, consistent with no emitted artifact carrying a
copyright string).

## 3. Scope globs

```
LICENSE                        (new)
NOTICE                         (new — see Q2)
README.md                      (licence statement)
plugin/plugin.json             (add "license": "Apache-2.0")
docs/production-readiness.md   (§1 leg, SUBJECT NOTE marker, RE-BASE leg count)
tests/test_doc_citations.py    (the step-4 check + docstring)
docs/deferred-backlog.md       (T0 tier line + C-1 paragraph; NOT cluster-C's C-1)
.claude/readiness-queue.md     (step 10)
.claude/readiness-runbook.md   (§1 A-tier text; ALSO step 3 + §5, already
                               edited this session for the operator's
                               approval ruling — outside the glob as first
                               declared, disclosed rather than hidden)
```
Anything outside these → **E4**.

## 4. Blast radius — derived, and it is nil

* `plugin.json` is **not emitted**: `build_plan` returns 57 actions and none
  matches `plugin`, `LICENSE` or `NOTICE`.
* No emitted body carries a copyright or licence string today.
* Therefore: **no golden digest moves, no freeze exception, no re-baseline.**
  If a golden moves, something is wrong with the plan → **E5**.
* No existing licence declaration anywhere in the tree to contradict
  (word-bounded sweep; the naive one false-positives on `MIT` inside
  "e**mit**ted").

## 5. Step 4 — the failing check, written first

**CORRECTED — `tests/test_root_sentinels.py` is the WRONG HOME and the plan
said so on a false premise.** It is an installer-behaviour suite: it installs
into `tempfile.mkdtemp()` and asserts on *emitted* output, never consults the
repo tree, has no `tracked` variable and no `re` import at module scope.

The check goes in **`tests/test_doc_citations.py`**, which already runs
`git ls-files` into `tracked` at `:265` behind a vacuity guard at `:269`. A new
final section, with the suite's docstring widened from citations to
repo-document invariants — a topical stretch, stated rather than hidden.

**Why not a new suite:** `bin/run-tests` auto-discovers `tests/test_*.py`, so
`tests/test_repo_shape.py` would silently take the count 25 → 26 and make every
"25 suites" claim in the changelog, queue, runbook and checkpoints stale at
once. The count is prose-only, not mechanically pinned — which makes it a sweep,
and sweeps are this repo's failure mode. Not worth it for two checks.

```python
check("a LICENSE file exists — readiness C-1",
      any(re.fullmatch(r'LICENSE(\.[A-Za-z]+)?', p) for p in tracked))
check("the licence is the one the operator chose (Apache-2.0)",
      'Apache License' in license_text and 'Version 2.0' in license_text)
```

It must **FAIL on this tree before the LICENSE is added**, and its failing
output is pasted into the commit. A check that never failed proves nothing.

## 6. Steps 5–11

5. Add `LICENSE` (verbatim canonical Apache-2.0 text, fetched from
   apache.org — not typed from memory), `NOTICE`, README statement,
   `plugin.json` licence field.
6. **Amend `docs/production-readiness.md`** — the actual deliverable: mark the
   C-1 leg closed **with the date and the commit**, and state plainly that the
   verdict stands on the remaining legs.
   **CORRECTED: the SUBJECT NOTE's `→ 0` does NOT become false.** It is
   explicitly "Re-derived on `0d4d5af` today" — a measurement of an immutable
   tag, which adding a LICENSE on a branch cannot falsify. The document's own
   layering rule (*"nothing that was measured is deleted when it stops being
   current"*) means it takes a **dated marker**, not a correction. What goes
   stale is the present-tense inference drawn from it, not the number.
   **RECONCILE TWO-vs-THREE LEGS IN THE SAME COMMIT:** §1 lists three negative
   legs, but RE-BASE `:102` says "one of the verdict's **two** supporting legs"
   and `.claude/readiness-queue.md:25` says "**two** legs". Three live sites, two
   different counts. Do not add a fourth reading.
7. Suite 25/0. PR. Review: 1 lens (DOC class) — a completeness sweep for
   dependent sites, since an incomplete sweep is this repo's signature failure.
8. **9a: post evidence and STOP. The operator merges (9b).**
9. Step 10: queue → done, and record whether the verdict moved (**it does
   not**). Step 10b: ledger entry. Step 11: checkpoint.

## 7. What would falsify this plan

* A golden digest moves → the licence reaches emitted output; stop (**E5**).
* The sweep finds a site asserting "no licence" that is **historical record**
  rather than a live claim → it must be left alone, not rewritten.
* `test_root_sentinels.py` turns out to be emitted or golden-pinned → move the
  check elsewhere.

---

## 8. TWO QUESTIONS FOR THE OPERATOR — both must be answered before step 5

**Q1 — the copyright line.** Apache-2.0's appendix requires
`Copyright [yyyy] [name of copyright owner]`. Derived: the sole human
contributor is **Deng Clive** (226 + 61 + 6 commits across three git
identities, all the same person). `plugin.json` says
`"author": "Project Bootstrap Protocol"` — a project name, not a legal person.
Getting this wrong in a legal file is worse than leaving it out.
→ **`Copyright 2026 Deng Clive`, or a different holder?**

**Q2 — NOTICE.** Apache-2.0 does not *require* a NOTICE file; it requires that
one be propagated **if it exists**. Adding it creates a permanent obligation on
every downstream redistributor.
→ **LICENSE only, or LICENSE + NOTICE?** (Recommendation: LICENSE only. This
project has no third-party attributions to carry, and a near-empty NOTICE
creates a propagation obligation on every downstream redistributor for no
benefit.)
**NOTE: this OVERTURNS existing queue text.** `.claude/readiness-queue.md:19-20`
already prescribes "the `NOTICE` attribution file the licence's
patent/attribution mechanism expects" — which also misstates the mechanism, as
NOTICE is not what carries the patent grant (§3 does). If LICENSE-only stands,
that queue text is corrected in the same commit.

## 9. A GOVERNANCE QUESTION THIS ITEM SURFACED — not blocking, but say it now

**DW-R6, verbatim:** *"No agent commits to `main`, tags, pushes, merges a PR,
or edits a remote. Those are operator actions on the release path."*

That rule already prohibited agent merges **before** the runbook was written —
so my original step 9 contradicted written policy, not merely the rung table's
invariant. It also means the branch **pushes** I performed earlier in this
session (PRs #68–#74) are outside DW-R6's letter, even though the operator
directed each merge.

The runbook's 9a/9b split now matches DW-R6 for merges. It does **not** yet
match it for pushes. Two coherent resolutions:
* **(a)** the loop stops at "commit locally", and the operator pushes and
  merges — strictest, matches DW-R6 exactly; or
* **(b)** DW-R6 is amended to permit an agent to push a *branch* (never `main`,
  never a merge, never a tag) under an operator-approved plan, which is what
  actually happened here.

**This wants a decision, not a drive-by.** Recommend (b) with the amendment
written down, but it is the operator's call and is filed as a queue item rather
than assumed.

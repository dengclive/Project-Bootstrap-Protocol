# Changelog — Bootstrap Protocol implementation

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
`Bootstrap-Protocol-v2-6-0.md:283` already says *"successful per-task
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
`Bootstrap-Protocol-Companion-v2-6-0.md`.

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

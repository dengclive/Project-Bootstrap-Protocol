# Dynamic-workflow policy — allowable use of the `Workflow` tool on this repository

**Derives from** `docs/dynamic-workflow-assessment.md` (verdict: *adopt-narrowed,
development tooling only, never emitted*), which decided IF and WHERE. This
document decides **HOW**, and binds only maintainer-side use.

**Not protocol surface.** Like `.claude/trust-ramp.md` beside it, this governs
how much autonomy the agent is granted *on this repo*: it emits nothing, is not
imported by `lib/` or `bin/`, appears in no installer plan, and touches no
golden digest. `Bootstrap-Protocol-v2-6-0.md:209-212` excludes
`.claude/trust-ramp.md` by name and states the criteria for doing so — *"It
emits nothing, no installer plan references it, and it is not part of any
conformance surface"*. It defines no class and does not name this file; the
claim here is that this file meets the same three criteria, which is an
argument from the stated criteria, not a citation.

**Disambiguation — read this before grepping.** The `workflow:` block in
`bootstrap.config.yaml:113` (`install_skills`, `implementer_model`,
`implementer_isolation`, …) is the **emitted subagent** namespace and has
nothing to do with this document. "Dynamic workflow" here means Claude Code's
`Workflow` tool — JS scripts calling `agent()` / `parallel()` / `pipeline()`.
Nothing in this policy reads, writes, or implies a config key.

---

## Pre-flight — the whole document as a checklist

Run this before writing a workflow script. Every line links to the rule that
owns it; if all ten pass, author the script.

| # | Check | Rule |
|---|---|---|
| 1 | No `hooks` entry in `.claude/settings.json`, `.claude/settings.local.json`, or `~/.claude/settings.json`; `.claude/hooks/` still empty | §1 |
| 2 | The task qualifies under **one** limb: independent *samples*, or independent *sites*. Wanting it sooner is neither | §2 |
| 3 | It is one of the four uses. If it isn't, stop — the list is closed | DW-U1–U4 |
| 4 | Nothing will be emitted, and no `lib/` or `bin/` file changes | DW-P1, DW-P3 |
| 5 | Writing stages are width 1 **or** worktree-isolated — counting the index and refs, not just tracked files | DW-R1 |
| 6 | No test execution inside any fan-out stage, by any entry point | DW-R2 |
| 7 | `PYTHONDONTWRITEBYTECODE=1` set for any agent that imports a repo module; scratch goes to the session scratchpad | DW-R3, DW-R4 |
| 8 | No agent commits, tags, pushes, or merges | DW-R6 |
| 9 | Width is stated in the plan with its reason, and bounded by what you will read | §5 |
| 10 | The current rung's requirements apply **unchanged** — fan-out unlocks nothing. At R0: plan approved before work starts, diff reviewed before every commit | DW-G1 |

After: count the `null` returns, ratify every finding yourself before it becomes
a claim in the record (DW-A1), and log **one** ledger entry (DW-A2).

---

## 0. Evidence labels

Rules below cite **CONFIRMED** (executed or read at a located line) or
**ASSESSED** (established in `docs/dynamic-workflow-assessment.md`, which
labelled its own evidence). Two further labels appear exactly once each and are
the only claims not resting on one of those:

- **UNMEASURED** — DW-R2's second motivation. The mechanism is confirmed; the
  failure it predicts was not measured. The rule is written conservatively
  rather than dropped, and §8 records what would settle it.
- **HARNESS-DOCUMENTED** — DW-P6's nesting claim. A property of the `Workflow`
  tool, asserted by the tool and verifiable only by running it. Nothing in this
  repository confirms it and it may change without notice, so no rule depends
  on it.

Anything else is an argument from the cited criteria, not a citation, and says
so where it appears.

---

## 1. The grant, stated once

A maintainer session may use the `Workflow` tool for work **on this
repository**, for the four uses enumerated in §2, subject to §3–§5.

The grant rests on one fact and dies with it: **no `PreToolUse` hook is
registered against this working tree, from any settings source.** That is the
property §3.4 of the assessment turns on, and it is strictly stronger than "this
repo has no install of its own" — a hook needs no install to be registered.

CONFIRMED at write time, and this is the whole check:

| source | state |
|---|---|
| `.claude/hooks/*.sh` | matches zero files |
| `.claude/settings.json` | does not exist |
| `.claude/settings.local.json` | exists; contains `permissions` only, no `hooks` key |
| `~/.claude/settings.json` (user scope) | exists; zero `hooks` occurrences |

`bin/trust-ramp:14` states the no-install half in as many words. **Re-run all
four rows before relying on the grant** — the first two alone cannot see a hook
registered from either settings file, and settings files change without an
install ever happening.

**The grant is suspended** the moment any row above changes, until §3–§5 are
re-derived against a gated tree. Self-installation is one way that happens and
not the likeliest: the ledger format in `.claude/trust-ramp.md:96` contemplates
self-install, but a single hand-added `hooks` entry in a settings file is
cheaper and invisible to the no-install check.

---

## 2. Permitted uses — a closed allowlist

Four uses. Anything not on this list is not permitted by default; adding a
fifth is an amendment under §8, not a judgement call at authoring time.

The admission test for all four is the same, and it is the discriminator the
assessment landed on (§6):

> **Does the task need independence, or convergence?**
> Convergence — improving *one* artifact over iterations — is the goal loop's
> job and the goal loop does it better, because
> `evaluator_feedback_history_depth: 2` deliberately primes each iteration with
> the last two. Independence is the one thing iterating a single agent
> structurally cannot produce.
>
> **Independence has two limbs, and a use must qualify under exactly one:**
>
> - **Independence of samples** (DW-U1, DW-U2, DW-U3) — *N observers that have
>   not seen each other*. Justified by **variance reduction on an open-ended
>   search**. If you can state the goal as "make this one thing better," use
>   `/loop` or the goal loop; if you can only state it as "find what I have not
>   thought of," fan out.
> - **Independence of sites** (DW-U4) — *N edits that do not interact*.
>   Justified by **throughput**, not variance. This limb is narrower than it
>   sounds and DW-U4 states its own disqualifier: if site B's correct edit
>   depends on how site A was resolved, the sites are not independent and the
>   work is one task for one agent.
>
> A task that qualifies under neither limb is not a permitted use, however
> convenient fan-out would be. Wanting results *sooner* is not independence of
> either kind.

### DW-U1 — Adversarial review fan-out

N agents independently attacking a design, a plan, or a diff for flaws and edge
cases, each blind to the others' findings.

**Why fan-out.** A sequential reviewer inherits its own earlier framing; a
second pass by the same agent re-reads the same file with the same priors. The
failure this repo has actually paid for is *correlated blind spots*, not
insufficient iterations: `docs/changelog.md:795` (the 2.7.1 → 2.7.2 section)
records that **"a judge that only scores designs inherits their shared blind
spot,"** and issue #54 needed four independent blocks, each catching what the
previous stage had stated as measured fact.

*Locator note.* `docs/dynamic-workflow-assessment.md:321` attributes this to
"the X-36q record". The sentence is **not** in `docs/deferred-backlog.md` —
`grep -c "shared blind spot"` there returns 0, and the X-36q row is about the
invoker-word reduction's five consumers. Its tracked home is
`docs/changelog.md:795`; it also appears at
`.claude/checkpoints/checkpoint-20260806-083157-main.md:118`, which is
gitignored (`.gitignore:11`) and therefore not citable. Cite the changelog.

**Required shape.** Reviewers are read-only (§4). Diverse lenses beat redundant
ones — give each agent a distinct angle (correctness, security, cost,
does-it-reproduce) rather than N copies of one prompt. Findings are claims, not
verdicts; §6 governs what happens to them.

### DW-U2 — Judge panels

N independent scorings of a solution, or N independent proposals scored against
each other.

**Why fan-out, and how it differs from DW-U1.** DW-U1 searches for defects;
DW-U2 reduces the variance of a *judgement*. The emitted goal loop already ships
a judge — CONFIRMED from the emitted `goal-config.md`: `evaluator_model: haiku`,
`evaluator_disagreement_threshold: 3` — and the Companion (`:150`) is explicit
that it is *"advisory only — never sufficient on its own."* A panel does not
change that status. It narrows the error bar on an advisory number; it does not
promote the number to a gate.

**Required shape.** An odd panel size, so a majority exists. Each judge scores
without seeing the others' scores. **A panel that agrees unanimously and quickly
is evidence of a shared prior, not of correctness** — that is the exact failure
DW-U2 exists to detect, so record the spread, not only the verdict.

### DW-U3 — Corpus sweeps

Repository-wide scans: probing a grammar for spellings a walker misses, sweeping
a config space, enumerating a class of construct across all consumers.

**Why fan-out.** Breadth, not depth. This is the shape that has repeatedly found
what a targeted read did not: the X-36v/w arc turned on the fact that
`prefix_run` already denied two spellings, so **six live ones hid behind them** —
and the lesson recorded in that checkpoint is *"enumerate the class from the
GRAMMAR, not from what already denies."* A sweep is how you enumerate from the
grammar.

**Required shape.** Read-only, or writing exclusively into the session
scratchpad (§4). A sweep that mutates the tree is a DW-U4, not a DW-U3, and
inherits DW-U4's rules.

### DW-U4 — Migration pipelines

Large-scale mechanical change: one transformation applied across many sites.

**Why fan-out.** Throughput on independent, individually-verifiable edits.

**This is the only permitted use that writes**, and it therefore carries the
most restriction: DW-R1 (isolation), DW-R2 (the suite), and the whole of §5 and
§6 bind hardest here. A migration whose sites are *not* independent — where
site B's correct edit depends on how site A was resolved — is not a migration
pipeline. It is one task, and it belongs to one agent.

---

## 3. Prohibitions — closed, each bound to its finding

### DW-P1 — Nothing is ever emitted. *(assessment B-1, B-2, B-3, §7)*

No workflow orchestration — no script, no runner, no wrapper, no
`.claude/` artifact describing one — enters an installer plan, a target project,
or the seam. This is the verdict itself, and it is not negotiable at authoring
time.

Three findings hold it: concurrency converts ordinary commands into fail-closed
refusals (`git add` at 5,000–7,000 paths is **allowed at N=1, refused at
N=16**, same command, same config, same install); the `Workflow` cap
`min(16, cores-2)` reads no config while the protocol's cap is *derived* from a
safety precondition (CONFIRMED `lib/templates.py:5526` `_concurrency_default`:
2 with worktree isolation, 1 without, "concurrent tasks would edit the same
working tree"); and fan-out agents have no unit of accounting — no `task_id`, no
`O_CREAT|O_EXCL` sentinel, no entry in `loop_in_flight` or `goal_in_flight`.

An **emitted orchestrator** would additionally change §7.2 security-critical
hook-set membership, which `SEAM-CONTRACT-v2-0-0.md:330` makes a `seam_version`
bump trigger, and §9 has already recorded a Bootstrap-emitted runner as
*considered-and-declined*. Proposing one is not an in-version change; it is an
owner-side pin event reopening a settled decision.

### DW-P2 — Fan-out is not an autonomous mode.

It does not join 9.5 / 9.6 / 9.7, is not selectable in the interview, and is not
described to an operator as something they may do to their project. A steering
doc telling an operator to fan out in front of the emitted gate suite is a doc
that walks them into §3.4.

### DW-P3 — `lib/` and `bin/` never learn this exists.

No module under `lib/` and no script under `bin/` may import, invoke, or branch
on a workflow. Emission stays what the assessment confirmed it to be: *"a
single-process, single-threaded pure function of config; no workflow runs during
`build_plan`."* This is the same posture `bin/trust-ramp` holds and for the same
reason — it is what keeps the golden digests meaningful.

**`bin/` is in scope, not an afterthought.** `bin/bootstrap-install` and
`bin/bootstrap-interview` are the CLI entry points the seam contract's §3.2
table is written about (`SEAM-CONTRACT-v2-0-0.md:136-138`). A workflow reachable
from either is orchestration on the wire, whatever the module boundary says, and
a rule scoped to `lib/` alone would read as covered while leaving them open.

Two rows of that table are **struck through** — `bootstrap-install --force`
(`:139`) and `retrofit-interview` (`:140`, *"NOT a permitted Tessera entry point
at this pin"*). Do not read a strikethrough as out of scope here: it removes a
row from *Tessera's permitted invocation set*, not from this repository's
executable surface. §7's tripwire therefore scans **all five** `bin/` scripts
plus `lib/` and `plugin/`, which is wider than §3.2 and deliberately so.

### DW-P4 — No fan-out in front of a gated tree, including a fixture.

§1's grant is about *this repository's* tree. The suites build **real installs
with real emitted hooks** into fixtures — CONFIRMED by `bin/run-tests`' own
pollution message: *"Emitted hooks resolve paths via
`${CLAUDE_PROJECT_DIR:-.}` — pin `CLAUDE_PROJECT_DIR` (and cwd) to the fixture
when running one."* A fleet driving commands through a fixture's hooks re-enters
the gate tax the grant claims exemption from. **The exemption is a property of
this tree, not of the word "internal."**

**BREACHED ONCE, 2026-07-30ish, LOGGED AS AN EXCEPTION — ruled 2026-08-12.**
The X-36y adversarial review fanned out agents that drove commands through
fixture hooks, 53 invocations. The artifact it produced was sound and landed
(21d82e3); the METHOD was prohibited. Ruled a violation, recorded here, **no
amendment**: permitting it would be a fifth permitted use under §8 and would
have to be argued past `bin/run-tests`' own pollution detector, which is the
concrete basis for this rule rather than an analogy.

**THE COMPLIANT SHAPE, NOW PRESCRIBED RATHER THAN FOLKLORE.** Every review since
that breach has used it, and it is not a limitation — PR #64's review used it to
find a reproduced, merge-blocking bypass in a fix that the whole suite called
green:

* **Fan out READ-ONLY lenses over the DIFF.** No agent runs a gate, installs a
  project, executes an emitted hook, or runs a suite. Say this in the prompt;
  agents will otherwise reach for execution to settle a question.
* **An agent that cannot answer without executing says so** and marks the
  finding as needing execution. It does not execute.
* **The ORCHESTRATOR reproduces every candidate serially, at width 1**, before
  acting on it. This is DW-A1's ratification and it is where fan-out's cost
  actually lands (§6 is the throttle).
* **Budget the ratification, not the fan-out.** Dedupe across lenses BEFORE
  spending verification, and report anything past the cap as explicitly
  unverified rather than dropping it.

### DW-P5 — A workflow never decides a merge.

Fan-out produces claims. A human ratifies them. This is the standing rule for
`lib/` changes — adversarial review is the gate, not a post-merge formality —
and fan-out does not relax it, it *strains* it, because N agents produce claims
faster than one human ratifies them. §6 is the throttle.

### DW-P6 — No nested spawning.

One level only.

**HARNESS-DOCUMENTED, not repo-confirmed:** the `Workflow` tool states that
nesting is one level and that a `workflow()` call inside a child throws. That is
a property of the harness, verifiable only by running it; nothing in this
repository asserts it, and it may change without notice. Treat it as a
convenience, not a guarantee — **DW-P6 binds regardless of whether the tool
enforces it.**

**Do not cite `Companion:161` as licensing one level.** The Companion reasons
from *"your custom subagents spawn further subagents — **currently none do**"*,
and the assessment (§2, `docs/dynamic-workflow-assessment.md:96-101`) reads that
sentence as **already falsified by any workflow use at all**: a workflow script
*is* subagents spawning subagents. So :161 is not a support for this rule; it is
a premise this policy has already spent. DW-P6 keeps the spend to one level and
records the debt — every model-enforcement conclusion downstream of :161 is
written against a negation that no longer holds here.

---

## 4. Operating rules — the tree, the suite, the scratch

**This section is the part the verdict's headline does not cover.** "No gates
here" answers B-1. It does not answer **B-4**, which the assessment classifies as
*blocking maintainer use at scale* — and maintainer use is precisely what this
document grants.

### DW-R1 — One writer to the repository. Always.

Any stage that mutates **anything under the repo root — tracked files,
untracked files, ignored files, the git index, `HEAD`, refs, or stash** — runs
at **width 1**, or every agent in it gets `isolation: worktree`. There is no
third option.

**The trigger is not "edits a tracked file."** The shared mutable resource is
the whole repository state, and the index and refs are the parts with no
merge semantics at all: `git add` and `git commit` take `.git/index.lock`, so N
concurrent add-only agents do not produce N commits — they produce one winner
and N−1 lock failures, and the one that lands carries whatever the others had
already staged. An add-only migration is still N writers.

The protocol's own cap is derived from exactly this precondition
(`_concurrency_default`), and re-arming it at fleet scale is backlog **W-1**
multiplied: worktree isolation × command contract failed *open, silently* once
already.

**If you take the worktree option, know where they land.** Claude Code creates
`.claude/worktrees/wt-<task-id>/` **inside this repo root**
(`lib/templates.py:6166`). `.gitignore` does **not** cover that path; this
clone's `.git/info/exclude` does (`**/.claude/worktrees/`), and that file is
per-clone and uncommitted. **On a fresh clone the worktrees are visible to
`tree_state()`** and DW-R2's detector reports every one of them. Add the exclude
before fanning out on a clone you did not configure.

### DW-R2 — Test execution runs serially, by any entry point.

**The rule names the activity, not the wrapper.** `bin/run-tests` is the obvious
form, but the repo's documented way to run one suite is `python3
tests/<file>.py` directly, and a DW-U4 pipeline whose per-site verification step
runs a suite is the likeliest way this rule gets broken by someone following it.
No test execution — via `bin/run-tests`, via a direct `python3 tests/…`
invocation, or via any script that ends up doing either — belongs inside
`parallel()` / `pipeline()`, and none may run while any other agent writes
anywhere under the repo root.

**Motivation one — the pollution detector is unsound under concurrency
(ASSESSED, confirmed by executing its own logic).** CONFIRMED mechanism:
`tree_state()` (`bin/run-tests:89`) takes a **whole-repo**
`git status --porcelain --ignored --untracked-files=all` snapshot; `main()`
takes one at `:162` and one at `:237` and reports the **symmetric difference**
as pollution at `:250`. It is a global before/after diff over one shared mutable
resource, with no synchronisation and no attribution — sound **only under a
single serialised writer**. A fleet falsifies it in both directions at once: a
concurrent agent's legitimate file is reported as pollution with no pid, suite
name, or agent id attached; a file created and deleted inside the window is
invisible. **A green pollution check then means nothing, which is worse than a
red one.**

Note `--ignored`: even a write to a *gitignored* path (`.claude/logs/`,
`__pycache__/`) trips it. "It's gitignored" is not an exemption.

**Motivation two — the suite carries wall-clock deadlines calibrated under a
serial runner.** CONFIRMED present: `timeout=8` subprocess calls throughout
`tests/test_installer.py` (`:358`, `:516`, `:524`, `:531`, `:541`, `:552`), a
10-second polling deadline at `tests/test_auto_run_sentinel.py:265`, and
`timeout=30` at `tests/test_retrofit.py:1651`. The assessment measured CPU
contention at **2.4–3.1×** under fan-out. **UNMEASURED:** whether any of these
actually flips. The mechanism is B-1's — contention converting latency into
failure — landing this time on the maintainer's side of the line, and a spurious
red suite is expensive enough that the conservative rule is cheaper than the
measurement.

**`--no-tree-check` is not the remedy.** It exists (`bin/run-tests:147`) and it
is the honest flag when you already know the check cannot hold. But reaching for
it to make a fleet quiet is the documented operator response to a flaky gate —
disable it — which is the failure mode the assessment calls blocking. Serialize
instead.

### DW-R3 — Scratch lives outside the repo, and `PYTHONDONTWRITEBYTECODE=1` is not optional.

Every probe script, sweep output, and intermediate artifact goes to the session
scratchpad, never the repo tree. Follows directly from DW-R2's `--ignored`
snapshot. This is already how the X-36v/w and gate-tax harnesses were built, and
those harnesses are the reason the numbers in the assessment are reproducible.

**Any agent that imports a repo module must run with
`PYTHONDONTWRITEBYTECODE=1` set**, or must `rm -rf` the resulting
`__pycache__/` before the next suite run. Importing `lib/` writes
`lib/__pycache__/*.pyc` beside the source — an *unavoidable side effect of
reading*, which is why it defeats every intuition about what "read-only" means.
See DW-R4.

### DW-R4 — Read-only is the default shape. It is not a pollution exemption.

DW-U1, DW-U2, and DW-U3 are read-only, and you should reach for a writing
fan-out (DW-U4) only when the work is genuinely N independent edits.

**But a read-only fleet CAN pollute this tree, and this rule previously claimed
otherwise.** The claim was falsified by the adversarial review of this very
document: a lens instructed to be read-only imported `lib/` to check a citation,
which wrote six `.pyc` files into `lib/__pycache__/`. Four of the six lenses
found the error independently; one of them produced the evidence by committing
it.

The mechanism was already recorded — `docs/dynamic-workflow-assessment.md:425`
is the checkpoint note *"`bin/run-tests`' pollution detector fires on a
concurrent agent importing `lib/`"* — and this document dropped it while
carrying the rest of §8. That is the "a rule encoded in one place reads as
covered" failure, committed in the act of writing the rule against it.

So, precisely:

- Read-only agents **cannot** race a writer for file *content* and **cannot**
  trip DW-R1.
- Read-only agents **can** trip DW-R2, by importing a module, by running a
  script that imports one, or by anything else that writes a cache beside the
  source. `.pytest_cache/` arrives the same way.
- The remedy is DW-R3's env var, not a weaker reading of "read-only."

### DW-R5 — Never `git add -A`.

Standing repo rule, and a fleet makes it sharper: `.claude/logs/hooks.log` and
any agent's stray file are exactly what a bulk add sweeps in.

### DW-R6 — A workflow never publishes.

No agent commits to `main`, tags, pushes, merges a PR, or edits a remote. Those
are operator actions on the release path, which is
`branch → PR → adversarial review → merge → tag the merge commit`, and the
standing rule is that nothing commits to `main` directly.

DW-P5 forbids a workflow *deciding* a merge; this forbids it *performing* one,
which is a different act and was not otherwise covered. A DW-U4 pipeline that
commits per-site is the natural shape that walks into this — stage the edits,
let the operator commit.

---

## 5. Width — bounded by review, not by cores

The tool's cap is `min(16, cores-2)` — CONFIRMED as 10 on the 12-core host the
assessment measured — and **it reads no config.** That number is a machine
property. It is not a permission.

**The binding constraint is review capacity.** The PRD's own justification for
its concurrency budget is not machine capacity: `Bootstrap-Protocol-v2-6-0.md:423`
budgets 2 across all autonomous modes *"expanding based on review throughput"*,
and warns that *"running more concurrent autonomous tasks than the operator can
review … defeats the point."* The **number** does not transfer to fan-out — the
assessment establishes that it was written about a different noun, a tracked and
locked task slot. The **justification** transfers exactly.

So:

- **Read-only fan-out (DW-U1/U2/U3): width is bounded by what you will actually
  read.** Sixteen findings you skim is worse than five you verify, because
  skimmed findings enter the record with the authority of having been "reviewed."
- **Writing fan-out (DW-U4): width is bounded by the diff you will actually
  review before merge**, per `.claude/trust-ramp.md` — *the diff is reviewed by
  a human before it merges, at every rung.*
- **State the width and the reason in the plan**, before launching. A width
  chosen because the machine allows it is the failure this section exists to
  prevent.
- **Log what you truncate.** If a sweep is capped at top-N or a stage is not
  retried, say so in the output. A silent cap reads as "covered everything."
- **Agents die. Say so.** `agent()` returns `null` on a terminal API error after
  retries, and a filtered-out `null` is a lens that silently did not run. Count
  the nulls and report them beside the findings; N−1 lenses reported as N is the
  same defect as a silent cap. (The emitted `exit_reason` enum has no member for
  this — assessment gap **G-4** — but that enum governs emitted runs, and a
  maintainer's fan-out writes no state file. Here the obligation is only to say
  it out loud.)

**Cost is not assessed and this document does not bound it.** The assessment
(§14) declines to cost fan-out and points at the Assumption Ledger's *"Subagent
token multipliers (~2–3× mixed-model)"* row, which carries an explicit
re-validation trigger and is calibrated for the current mixed-model split, not
for a fleet. Width bounded by review capacity is a **safety** bound, not a
spend bound; they are not the same number and this section only sets the first.

---

## 6. Accounting — ratification, and the trust ramp

### DW-A1 — Findings are claims until a human rebuilds them.

This is where fan-out's cost actually lands, and this repo has the scar tissue
to price it. Two standing rules apply to *every* agent-produced finding and bind
harder when N agents produce them at once:

- **"Bounded" is usually a property of the fragment, not the class.** Rebuild
  the payload as a complete command before believing a bounded claim. X-36v
  called its keyword half bounded because `then bash -c '…'` is a syntax error;
  inside `if true; then bash -c '…'; fi` it runs.
- **Measure execution with a file marker, never captured stdout.** Four
  constructs were recorded as bounded from a probe where `while false` never
  entered its body, `coproc` is asynchronous and the parent exited first, and
  `select` read EOF. All four run.

**A fan-out multiplies claims without multiplying ratification.** Budget the
ratification, not the fan-out.

### DW-A2 — One workflow run is one ledger entry.

For `bin/trust-ramp log`: a workflow run produces **one** entry, because it
produces one reviewable outcome — one verdict, or one diff. Its `--notes` should
record the width and the shape.

A wrong finding that reached the tree is `harmful`, exactly as it would be from
a single agent. Fan-out earns no leniency for having been outvoted internally.

**Scope, stated so it cannot be mis-cited.** This settles the *maintainer-side*
question only, and it is settleable here because this repo's ledger is
repo-local and non-protocol-surface.

It does **not** answer assessment gap **G-1** (trust-ramp semantics for a fleet:
inherit / floor / ineligible), which is an owner decision of cluster-A class and
remains open. G-1's scope is *"before any adoption **beyond dev tooling**"*
(`docs/dynamic-workflow-assessment.md:295`, §10 header at `:465`) — **not**
"emitted installs" specifically, which is narrower than what the assessment
reserved. This policy binds dev tooling only, i.e. it operates inside the space
G-1 leaves open rather than pre-empting it. Do not cite DW-A2 as G-1's answer.

### DW-G1 — How a fan-out interacts with the ramp is OPEN. Owner decision.

**Named, not answered.** An earlier revision of this document decided it —
*"fan-out is not rung-gated; write authority is"* — on the reasoning that the
rungs govern unattended iteration and a supervised fan-out is not unattended.
That reasoning survived adversarial challenge on the narrow question of
*authority*: assessment gap **G-1** reserves its decision to the owner only
*"before any adoption beyond dev tooling"* (`:295`, §10 header `:465`), and this
policy binds dev tooling only, so deciding it here was inside the space G-1
leaves open.

**Authority is not the same as being right.** The ramp is the owner's
instrument, its currency is operator review capacity, and fan-out changes the
ratio of work to review — the one quantity the ramp exists to bound. That makes
the question the same *class* as G-1 even though it is not G-1's scope, so this
document names it and declines to settle it.

**The question, stated so it can be answered:** does a fan-out at rung R
(a) inherit R's grant unchanged, (b) require a higher rung than the same work
done by one agent, or (c) constitute a distinct autonomy surface the ramp does
not currently model at all?

**Interim posture, deliberately conservative — fan-out is ramp-NEUTRAL.**
Until the owner answers, a fan-out **neither unlocks nor requires** anything on
the ramp. It is a tool used *inside* the current rung's grant, not an extension
of it:

- Every requirement of the current rung applies to a fan-out unchanged. At
  **R0** (`.claude/trust-ramp.md`, current rung at time of writing) that is a
  plan approved before work starts and the diff reviewed before every commit.
  §5's "state the width and the reason in the plan" sits inside the plan R0
  already requires approved.
- **A fan-out does not by itself confer unattended operation.** If the work
  would need R1+ done by one agent — unattended iteration on a scoped task — it
  needs R1+ done by sixteen. Width is not a substitute for a rung.
- The ramp's invariant is untouched at every rung: the diff is reviewed by a
  human before it merges.

This posture grants strictly less than the withdrawn clause did. That is the
point: an interim rule should be the one that is cheap to loosen once the owner
decides, not the one that is expensive to take back.

---

## 7. Enforcement — what is tested, and what is not

**Testable, and tested: DW-P1 and DW-P3.** "Nothing is emitted" is a mechanical
invariant over `build_plan` output, pinned by
`tests/test_dynamic_workflow_policy.py`. It is a tripwire the golden digests do
not provide: re-baselining a digest is a routine act — `docs/changelog.md`
records golden re-baselines as freeze exceptions no. 30, 31, 33, 34, 35 and 40 —
so a future well-meant addition lands **green through the goldens** and red only
against a named invariant. `tests/test_trust_ramp.py` is the precedent:
repo-local, non-protocol-surface tooling in `.claude/` carries a suite here.

**The predicate must be specific, and the test must prove it is not vacuous.**
A naive substring match on `workflow` fails immediately: `lib/templates.py`
carries 14 legitimate occurrences — the `workflow.*` config namespace this
document's header disambiguates (`workflow.implementer_isolation` resolved into
emitted prose) and ordinary English (*"Tests-first workflow per task"*). So the
predicate never matches the bare word.

**A workflow does not have to be JavaScript, and the JS-only version of this
predicate was its central defect.** The likeliest regression shape *in this
repository* is a shell dispatch loop, because `lib/templates.py` already emits
`claude -p` sixteen times — every one a single serial dispatch. What separates a
fan-out from those is **concurrency**, so the predicate carries five
shell-concurrency patterns (backgrounded dispatch, backgrounded loop body, bare
`wait`, `xargs -P`, GNU `parallel`) alongside the tool's API surface, its two
module forms, its dispatch-config parameters, and `Promise.all(` — which fans
out with no tool API at all. Matching is case-insensitive, because emitted prose
writes "Fan-out" at the head of a sentence far more often than lowercase. All
five shell patterns match **zero live bytes** across the emitted tree, `lib/`,
`bin/` and `plugin/`: they add detection, not false-positive risk.

Following this repo's own idiom (deny-capability asserted first, as the X-36v/w
sweep did), the suite **plants a synthetic violation for every signal** and
asserts each fires before asserting the real tree is clean — and asserts the
converse, that the legitimate `workflow.*` config namespace does *not* trip it.
Coverage is itself asserted: a signal cannot enter the predicate without a plant
proving it fires. The fixtures are likewise checked to be four *distinct*
emission paths, so a `build_plan` that silently collapsed them to one could not
leave the scan green. A tripwire that has never been shown to fire is not a
tripwire, and a scan that reads nothing passes every test.

**Not mechanically enforceable: everything else.** §2's admission test, §4's
operating rules, and §5's width discipline are **authoring-time discipline**.
There is no hook in this repository to enforce them — that is the same fact §1's
grant rests on, and it cuts both ways. This document is the enforcement
mechanism; it works only if it is read before the script is written.

---

## 8. What reopens this

- **Any row of §1's table changing.** A `hooks` entry appearing in
  `.claude/settings.json`, `.claude/settings.local.json`, or
  `~/.claude/settings.json`; a file appearing in `.claude/hooks/`; or this
  repository gaining an install of its own. Any one of those suspends the grant
  and makes §3.4 of the assessment apply to this tree. **Re-run the table, do
  not assume the no-install shorthand.**
- **Any proposal to emit orchestration.** Blocked on B-1 and gaps G-1 / G-3, and
  it is a seam event plus an owner-side pin event (§7 of the assessment). Not an
  authoring decision.
- **The owner answering DW-G1.** Whichever of (a) inherit / (b) higher rung /
  (c) unmodelled surface is chosen, DW-G1's interim ramp-neutral posture is
  replaced by it and §6 is rewritten to match. This is the one open question
  the document carries, and it is deliberately cheap to close: the interim
  posture grants less than any of the three answers is likely to, so closing it
  loosens rather than retracts.
- **A fifth permitted use.** Amend §2 explicitly; state the admission test it
  passes.
- **`bin/run-tests` gaining per-writer attribution or a scoped fixture**
  (assessment gap G-5). That would relax DW-R2's first motivation — not its
  second.
- **Measuring the DW-R2 timeout question.** If the suite's wall-clock deadlines
  are shown to hold under contention, that motivation weakens; DW-R2 still
  stands on the pollution detector alone.

---

## 9. Provenance

| Document | Role |
|---|---|
| `docs/dynamic-workflow-assessment.md` | The verdict and every measurement. Decides IF and WHERE; this decides HOW. |
| `.claude/trust-ramp.md` | Sibling governance doc; the placement and "not protocol surface" precedent. DW-A2 binds to its ledger; **DW-G1 is the open question about its rungs.** |
| `docs/agentic-harness-security-kb.md` | §4.7 is W-1, which DW-R1 exists to avoid re-arming. |
| `SEAM-CONTRACT-v2-0-0.md` §8.4, §9 | The bump triggers DW-P1 avoids, and the declined-runner decision it would reopen. |
| `Bootstrap-Protocol-v2-6-0.md` `:209-212`, `:423` | The not-protocol-surface exclusion, and the review-throughput justification §5 inherits. |
| `Bootstrap-Protocol-Companion-v2-6-0.md` `:150`, `:161` | Judge-is-advisory; subagents-do-not-spawn-subagents (DW-P6). |

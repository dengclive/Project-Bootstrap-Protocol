# Dynamic workflows (the `Workflow` tool) — compatibility assessment

**Date:** 2026-08-06 · **Tree:** `afc24a2` (main, protocol 2.7.3) ·
**Normative sources read:** `Bootstrap-Protocol-v2-6-0.md`,
`Bootstrap-Protocol-Companion-v2-6-0.md`, `SEAM-CONTRACT-v2-0-0.md`.
**Question:** does Claude Code's dynamic-workflow feature — JS scripts calling
`agent()`/`parallel()`/`pipeline()`/`phase()`, JSON-schema structured output,
per-agent model/effort/isolation overrides, concurrency capped at
`min(16, cores-2)`, 1000-agent lifetime cap — belong in the Bootstrap Protocol,
and if so where.

**This step decides IF and WHERE. It does not design the feature.**

**HOW is decided in `.claude/dynamic-workflow-policy.md`** — the maintainer-side
policy this assessment's verdict authorises: the closed list of permitted uses,
the prohibitions, and the operating rules that make §8's finding (the pollution
detector) survivable in practice. Its DW-P1/DW-P3 clauses are pinned by
`tests/test_dynamic_workflow_policy.py`. That document is likewise not protocol
surface and emits nothing.

---

## 0. Evidence labels

Every claim below is **CONFIRMED** (executed in this session, command and
numbers shown) or **CITED** (read from a file, located by line). Anything
neither is marked **HYPOTHESIS** and carries no weight in the verdict.

Two channels were read and deliberately **not** relied on, per their standing
classification: `docs/IMPLEMENTATION-PROMPT-v2_5_0-rippled.md` (known lossy —
it is what dropped DELTA-03; its only `parallel` hits are about parallel *token
sets* in code, not agents) and `docs/VALIDATION-v2.5.0-against-implementation.md`
(a claim to verify, not evidence; zero concurrency hits).

A green suite is an entry condition, not evidence. The suite is green at 23
suites / 9349 checks; that fact appears nowhere in the reasoning below.

---

## 1. VERDICT — **adopt-narrowed: development tooling only, never emitted**

This is the third answer, not a softened yes.

**Permitted:** the `Workflow` tool as a maintainer-side instrument for work *on
this repository* — adversarial review fan-out, corpus sweeps, migration
pipelines, judge panels. Nothing about that use enters an emitted tree, the
seam, or a target project. **Those four uses are the closed allowlist in
`.claude/dynamic-workflow-policy.md` §2 (DW-U1–DW-U4); the conditions on them
are that document's §3–§5.** In particular the grant is conditioned on this
repo having no registered `PreToolUse` hook from *any* settings source — a
stronger and more fragile property than "no install of its own."

**Refused, on a measured blocking finding:** emitting workflow orchestration
into a target project's `.claude/`, or admitting fan-out as an autonomous mode
alongside 9.5/9.6/9.7. Finding §3 below shows concurrency at N=16 converts
ordinary commands into fail-closed refusals in the emitted gate suite. That is
not a tuning problem; it is the gate suite's cost model meeting a concurrency
model that answers to nothing in the config.

**Why dev-tooling use is materially different, not a loophole.** CONFIRMED:
this repository carries **no install of its own** — `ls .claude/hooks/*.sh`
returns 0 files and `.claude/settings.json` does not exist. `bin/trust-ramp:14`
says so in as many words ("this repo has no install of its own"). Fan-out here
is not exposed to the gate tax at all, because there are no gates. The moment
the same feature is emitted into a project that *does* have the 13 hooks wired,
§3 applies in full.

---

## 2. Q1 — Does the PRD's autonomy model admit concurrent agents?

**Not silent, and not written for one agent at a time — but the concurrency it
admits is a different object than fan-out.** CITED.

The PRD admits concurrency at **task** granularity, with a budget, an accounting
structure, and a derived cap:

- `Bootstrap-Protocol-v2-6-0.md:423` — *"**Concurrency rule across autonomous
  modes.** … concurrency budgets apply to the **combined** sum across modes …
  **Recommended starting concurrency: 2 across all autonomous modes combined for
  the first week of use**, expanding based on review throughput."*
- `:341` — the queue runner's own `max_concurrent_tasks` cap, *"default 2 … The
  runner's `max_concurrent_tasks` should not be set higher than the
  combined-modes cap above."*
- `:314-318` — `loop_in_flight` / `goal_in_flight`, *"one entry per concurrent
  loop"*, with every read-modify-write *"performed under `flock` on
  `.claude/.bootstrap-state.json` and committed via the tmpfile-then-rename
  idiom"*, and a race-safe claim protocol using `O_CREAT|O_EXCL`.

So every concurrent unit the protocol recognises is: **budgeted (2), tracked in
a state list, claimed under a lock, and reviewable afterwards** — the budget's
stated justification is review throughput, not machine capacity.

Three facts make fan-out a different object:

1. **Nested spawning is explicitly noted as not happening.**
   `Bootstrap-Protocol-Companion-v2-6-0.md:161` — *"For this protocol, this
   matters mainly if your custom subagents spawn further subagents — **currently
   none do**, so frontmatter is sufficient."* A workflow script *is* subagents
   spawning subagents. The Companion's model-enforcement reasoning is written
   against the negation of that.
2. **The cap is derived from a safety precondition, not chosen.** CONFIRMED at
   `lib/templates.py:5526` `_concurrency_default(cfg)`: `max_concurrent_tasks:
   2` when `_worktrees_on(cfg)`, else `1` with the reason emitted in-file
   (*"the implementer runs WITHOUT `isolation: worktree` … concurrent tasks
   would edit the same working tree"*). The `Workflow` tool's cap is
   `min(16, cores-2)` — CONFIRMED as 10 on this 12-core host — and reads no
   config at all.
3. **The unit of accounting is a task, not an agent.** A workflow's agents are
   not tasks; they have no `task_id`, claim no sentinel, appear in neither
   in-flight list, and are invisible to the mutual-exclusion protocol.

**Conclusion:** the PRD does not forbid concurrency, and inferring permission
would still be wrong — what it permits is *2 tracked, locked, reviewable task
slots*. Fan-out proposes 10–16 untracked, unlocked, unreviewed agent slots. The
guarantees do not transfer; they were written about a different noun.

---

## 3. Q2 — THE GATE TAX (blocking finding)

**CONFIRMED by measurement on a real install. Concurrency converts latency into
refusal for ordinary commands.**

### 3.1 Method

Real install from this tree; real emitted hooks; N real concurrent invocations.
Two facts shape the measurement and both are CONFIRMED from
`lib/templates.py`:

- `TIMEOUTS = {'test-gate': 600, 'ci-mirror': 900, 'secrets-gate': 60,
  'dependency-gate': 60, 'format-lint-gate': 120}` — dependency-gate is 60 s and
  `FAIL_CLOSED=1`, so exceeding it is a **refusal**, not a slow allow.
- `HOOK_EVENT_MAP` puts **five** hooks on `PreToolUse`/`Bash`
  (`spec-gate-commit`, `test-gate`, `ci-mirror`, `dependency-gate`,
  `eval-gate`) and `secrets-gate` on six file tools
  (`Read|Write|Edit|NotebookEdit|Grep|Glob`).

The second fact matters and is easy to miss: **one Bash tool call pays five
tokenizer passes, not one.** Every figure below is the cost of one Bash call.

### 3.2 Solo cost (N=1)

| payload | 1 hook | 5 hooks = one Bash call |
|---|---|---|
| `npm test` | 0.02 s | 0.08 s |
| `git add` 200 paths | 0.06 s | 0.15 s |
| 1k assignment tokens | 1.17 s | 3.13 s |
| 2k assignment tokens | 4.41 s | 11.61 s |
| 4k assignment tokens | 16.72 s | **43.79 s** |

Superlinearity is confirmed (~3.7× per doubling). The brief's cited
0.9/3.6/14.6/56 s figures are the *single-hook* series; the number an agent
actually experiences is ~2.7× that.

### 3.3 Concurrency (median of N concurrent Bash calls)

| payload | N=1 | N=4 | N=8 | N=16 | N=16 vs N=1 |
|---|---|---|---|---|---|
| `npm test` | 0.08 | 0.07 | 0.08 | 0.13 | 1.52× |
| `git add` 200 | 0.16 | 0.16 | 0.17 | 0.26 | 1.63× |
| assign 1k | 3.14 | 3.23 | 4.01 | 6.97 | 2.22× |
| assign 2k | 11.62 | 12.24 | 15.48 | 27.73 | 2.39× |
| assign 4k | 43.63 | 46.09 | **60.48** | **107.50** | 2.46× |

`assign 4k` is **allowed at N=1 and N=4, refused at N=8 and N=16.** But that
payload is adversary-shaped — `docs/agentic-harness-security-kb.md` §7 already
names it (*"an anchored command-position regex went cubic on `WRAPPER` + a long
assignment run, ~66 s inside a hook"*). Adversary-shaped input flipping is
interesting, not decisive.

### 3.4 The decisive result: ORDINARY commands flip

`git add <N paths>` — a bulk format, a generated-code refresh, a vendored
dependency bump. Nothing adversarial about it.

| command | bytes | N=1 | N=16 | verdict |
|---|---|---|---|---|
| `git add` 1,000 paths | 18.9 KB | 1.33 s | 3.20 s | allowed at both |
| `git add` 4,000 paths | 78.9 KB | 16.45 s | 47.27 s | allowed at both |
| **`git add` 5,000 paths** | 98.9 KB | **25.44 s** | **72.38 s** | **allowed solo, REFUSED at N=16** |
| **`git add` 5,500 paths** | 108.9 KB | **30.68 s** | **89.29 s** | **allowed solo, REFUSED at N=16** |
| **`git add` 6,000 paths** | 118.9 KB | **36.29 s** | **109.77 s** | **allowed solo, REFUSED at N=16** |
| **`git add` 7,000 paths** | 138.9 KB | **49.19 s** | **143.16 s** | **allowed solo, REFUSED at N=16** |
| `git add` 8,000 paths | 158.9 KB | 63.95 s | 196.11 s | refused at both (pre-existing) |

Also measured, same shape: `grep -l` over 5,000 files 7.21 → 19.70 s (2.73×);
`npx prettier --write` 3,000 files 5.07 → 10.85 s (2.14×); 1,500 shell
assignments 11.33 → 26.99 s (2.38×).

### 3.5 Stated plainly

**Yes. Concurrency can push an ordinary command past the ceiling and convert
latency into a refusal.** For `git add` in the 5,000–7,000-path range, the same
command, on the same install, with the same config, is **allowed when one agent
runs it and refused when sixteen do.**

The mechanism is not exotic: the contention factor is a modest 2.4–3.1× (CPU
contention on 12 cores), and the gate's superlinear cost curve is steep enough
that a 2.4× multiplier moves the refusal threshold down by roughly 40% of
payload size. Concurrency does not create a new defect; it **enlarges the set of
commands the existing defect refuses**, and it does so silently.

**Why this is blocking rather than a tuning note.** A gate's verdict is supposed
to be a function of the command. This project has spent four releases making two
substrates agree on that function — the entire `test_substrate_differential.py`
apparatus (3,926 checks) exists so that one command yields one verdict.
Fan-out makes the verdict a function of **ambient fleet size**, a variable
neither substrate can see, no test can pin, and no operator can reproduce. A
refusal that depends on how many siblings happened to be running is
indistinguishable from a flaky gate, and the documented operator response to a
flaky gate is to disable it.

Ranked against the KB's own checklist, this trips two entries directly: *"A
control's worst-case cost is measured on adversary-shaped input, and every
blocking control has an explicit timeout with an explicit posture"* — the
posture exists but was costed for one agent — and *"No control is marked
async/background/non-blocking unless it is purely informational."*

---

## 4. Q3 — Determinism

**A workflow config is a plan input if and only if it changes emission. The
existing `workflow.*` namespace already contains both kinds.** CONFIRMED.

Measured on whole-plan digests of a real install (`.bootstrap-state.json` and
`.installer-manifest.json` excluded — they are written outside the plan and are
not hashed, which is the error freeze-exception no. 17 made):

- baseline plan digest `4e015687dfca9fb2`, 59 files.
- adding an **unknown top-level key** (`workflow_fanout_enabled: true`) →
  digest `4e015687dfca9fb2`, 59 files — **byte-identical**. Unknown keys are
  inert; the forward-compat posture holds.
- setting an **existing** `workflow.implementer_isolation: none` → digest
  `5d0773edb430a7a6`, and three bodies move:
  `.claude/agents/implementer.md`, `.claude/agents/integrator.md`,
  `.claude/steering/tech.md`.

So the answer for the emitted artifacts specifically:

- A knob that only governs **how the maintainer's own session fans out** emits
  nothing and is a runtime knob. It need not be deterministic because it is not
  in the plan.
- A knob that emits **anything** — a steering doc, a wrapper, a CLAUDE.md
  addendum, an agent frontmatter field — is a plan input, must be a pure
  function of config, and is frozen by the golden digests in
  `tests/test_greenfield_golden.py`.

There is no third category. The failure mode to avoid is a knob that *feels*
like runtime but leaks into an artifact — e.g. writing the chosen fan-out width
into `auto-config.md`. That would make the emitted tree depend on a machine's
core count, breaking content-determinism in a way the golden test would catch
only on a differently-sized machine.

**Fan-out itself does not break determinism.** Emission is a single-process,
single-threaded pure function of config; no workflow runs during
`build_plan`. The risk is entirely in what a fan-out *config surface* would
emit, and that is controllable.

---

## 5. Q4 — The trust ramp and a fleet

**UNSPECIFIED. This is a spec gap to name, not a default to invent.** CITED.

The ramp is explicitly **not protocol surface**.
`Bootstrap-Protocol-v2-6-0.md:209-212`: *"**Not protocol surface, deliberately
excluded:** this repository's own `.claude/trust-ramp.md` governs how much
autonomy the agent is granted *on the protocol repo itself*. It emits nothing,
no installer plan references it, and it is not part of any conformance
surface."* `bin/trust-ramp` says the same in its own docstring and is
deliberately un-imported by `lib/`.

What the protocol *does* ship is ramp **prose**, keyed to operator-in-loop task
counts: Phase 9.5 after *"first 5–10 operator-in-loop tasks"*, 9.6 after
*"10–20"*, 9.7 after *"at least 4 weeks of real operating time"*
(`:303`, `:434`). The repo-local `bin/trust-ramp` mechanises this as rungs
R0→R3 with `min_entries` / `consec_clean` / `harmful_window` / `min_days`
gates.

Every one of those thresholds counts **tasks with reviewed outcomes**. There is
no subagent in the model at all. So:

- Does a subagent **inherit** the parent's tier? Not stated anywhere.
- Does it **start at the floor**? Not stated anywhere.
- Is there any rung whose gate a fleet could satisfy? No — the ledger's unit is
  a task an operator reviewed, and 16 agents produce one task's worth of
  reviewable outcome, or none.

**The gap, named precisely:** the ramp's currency is *operator review capacity*,
and its explicit justification is the same (PRD `:339`: *"Running more
concurrent autonomous tasks than the operator can review … defeats the point"*).
Fan-out multiplies work per unit of review, which is the one quantity the ramp
is denominated in. Before any adoption beyond dev tooling, someone must decide
whether a fleet counts as one ledger entry, N entries, or is ineligible — and
that is an owner decision of the same class as cluster A, not something an
implementation should pick.

---

## 6. Q5 — Does the goal loop subsume this?

**For everything the emitted product does: yes, and fan-out does not earn its
complexity. For maintainer-side review: no, and the difference is
independence.** CITED + CONFIRMED.

The emitted goal loop already runs propose-then-evaluate with a cheap judge.
CONFIRMED from the emitted `goal-config.md`: `evaluator_model: haiku`,
`evaluator_disagreement_threshold: 3`, `evaluator_feedback_history_depth: 2`,
`max_iterations: 10`, `summary_failure_halt_threshold: 3`. The judge is
advisory and parallel to the deterministic gates — Companion `:150`: *"One
advisory verdict per iteration … Cheap, parallel to deterministic gates,
advisory only — never sufficient on its own."*

**What iterating one agent cannot do:** produce *independent* samples.
`evaluator_feedback_history_depth: 2` means iteration N is primed with
iterations N−1 and N−2's feedback. That is exactly right for **convergence** —
each iteration should learn from the last — and exactly wrong for **coverage of
an open-ended space**, where correlated priors are the failure mode. This
project has already paid for that distinction: the X-36q record notes *"a judge
that only SCORES designs inherits their shared blind spot,"* and #54 needed
four independent blocks, each catching what the previous stage stated as
measured fact.

So fan-out adds one thing the loop structurally cannot: **N samples that have
not seen each other.** Variance reduction on an open-ended search.

**But that value lands on a maintainer activity, and the protocol has already
drawn the line there.** Companion `:139` classifies adversarial review as
*"(PRD-process activity — **not a wizard-generated subagent**; listed here as
the model-assignment reference)"* — and prescribes *"Periodic spend, never
per-dispatch, never on the implementer path."* The one place fan-out is worth
its cost is the one place the protocol already says is not emitted surface.

For the emitted product's actual job — gate one agent's work against a spec —
fan-out adds nothing the loop lacks and costs the finding in §3. **It does not
earn its complexity in the emitted tree.**

---

## 7. Q6 — Seam impact

**Development-time use: no seam event. Emitted orchestration: a seam bump AND a
threat-model precondition.** CITED.

`SEAM-CONTRACT-v2-0-0.md` §8.4 lists seven triggers: a new CLI entry point or
contract-level flag; a §4.1 result-parsing field; a §5 stream event; §7.4 shared
sentinel names/locations/scope; **§7.2 security-critical hook set membership**;
§7.3 provenance markers / synthesize-file contract; the §8.1a `binds` set. It
closes: *"Changes that touch only gate internals or dispatch policy do **not**
bump `seam_version` — by definition they are not the wire."*

Against that list:

- **Maintainer tooling** — a workflow script run by a human on this repo. Emits
  nothing, adds no file to any plan, changes no tier. **Zero triggers fire. Not
  a seam event.**
- **An emitted steering doc** (the TEL-01/DS-01 shape) — precedent is explicit:
  both v2.4.0 and v2.5.0 record *"Seam impact: **none**"* for exactly that
  shape, because a new non-critical workspace artifact is not on the wire.
- **An emitted orchestrator** (a `workflow.sh`, a runner, anything executable
  that dispatches agents) — this is the case that bites. It would be a second
  security-critical or autonomy-critical executable, changing **§7.2
  membership**, which §9 states is *"contract-level, [so] that addition is a
  `seam_version` event and lands with the substrate-release seam bump — it is
  *not* a silent extension."*

Two further constraints make emitted orchestration harder than a bump:

1. **§9 pre-classifies execution substrates and refuses them.** *"Routines /
   cloud ingress substrate. Classified as ingress-trigger-only, **never an
   execution substrate**. If ever reclassified, it is a `seam_version` change
   **and requires a threat-model entry finalized before the contract admits
   it**."* A workflow engine that dispatches agents is an execution substrate by
   any reading. The contract already says the answer to that class is: not
   without a finished threat model, first.
2. **§9 runner ownership is a settled owner decision.** *"**Runner ownership —
   DECIDED: consumer-owned (Tessera-owned) runner (owner decision,
   2026-07-17).** … the protocol's emission stays module-only (the protocol does
   *not* emit a runner entrypoint) … keeps the protocol's executable-emission
   surface from growing. The rejected alternative (a Bootstrap-emitted runner …
   a second security-critical executable) is recorded as
   considered-and-declined."*

**A Bootstrap-emitted workflow runner is the already-rejected alternative under
a new name.** Adopting it is not an in-version change; it is an owner-side pin
event that reopens a decision recorded as declined.

---

## 8. Q7 — The pollution detector under sixteen agents

**It stops being sound. CONFIRMED by executing its own logic.**

CONFIRMED mechanism (`bin/run-tests`): `tree_state()` takes a **whole-repo**
`git status --porcelain --ignored --untracked-files=all` snapshot; `main()`
takes one before the suite list and one after, and reports the **symmetric
difference** as *"WORKING TREE POLLUTED by the test run."* CONFIRMED shape: 3
`tree_state()` call sites, 2 `run_one(` call sites, **0** references to
`ThreadPool` / `ProcessPool` / `multiprocessing` / `concurrent.futures` — the
runner itself is strictly serial.

Executed against the real function:

1. **False positive.** With a concurrent non-suite writer creating one file
   during the window, the symmetric difference is
   `['?? CONCURRENT_AGENT_ARTIFACT.tmp']` and the detector prints *"WORKING TREE
   POLLUTED by the test run"* — attributing another agent's legitimate write to
   the suite. Attribution carried: **none** — no pid, no suite name, no agent
   id. With 16 agents doing ordinary work in the repo, this fires on every run.
2. **False negative.** A writer whose file is created and removed inside the
   window yields symmetric difference **empty** — invisible. Concurrency makes
   this the common case, not the corner case: a fleet's scratch files routinely
   outlive neither snapshot.

**Soundness, stated precisely:** the detector is a global before/after diff over
one shared mutable resource with no synchronisation and no attribution. It is
sound **only under a single serialised writer**. That assumption is currently
true — the runner is serial and the repo has one operator. Sixteen agents
falsify it in both directions at once: it accuses the innocent and misses the
transient. The failure is not that it gets noisier; it is that **a green
pollution check stops meaning anything**, which is worse than a red one.

The checkpoint-recorded workaround — *"`bin/run-tests`' pollution detector fires
on a concurrent agent importing `lib/` — serialize"* — is the correct response
at N=1 and does not scale: serialising a fleet is the negation of the fleet.

---

## 9. Blocking findings

**B-1 (fatal for emission). Concurrency converts ordinary commands into
fail-closed refusals.** `git add` with 5,000–7,000 paths is allowed at N=1 and
refused at N=16 — same command, same config, same install (§3.4). The gate
verdict becomes a function of ambient fleet size, which no test can pin and no
operator can reproduce. Any adoption that puts a fleet in front of the emitted
gate suite inherits this.

**B-2 (fatal for emission). The concurrency cap would answer to nothing.** The
protocol's cap is *derived* from a safety precondition — CONFIRMED
`_concurrency_default(cfg)`: 2 with worktree isolation, 1 without, because
*"concurrent tasks would edit the same working tree."* The workflow cap is
`min(16, cores-2)` and reads no config. Emitting fan-out re-arms W-1 at fleet
scale: `docs/agentic-harness-security-kb.md` §4.7 records that pair
(worktree isolation × command contract) failing open silently, and its own
corollary is *"`max_concurrent_tasks` drops to 1 … instead of a doc note nobody
reads."* Sixteen agents in a tree that was deliberately capped at one is that
finding, multiplied.

**B-3 (blocks emission until answered). The unit of accounting does not
exist.** Workflow agents have no `task_id`, claim no `O_CREAT|O_EXCL` sentinel,
appear in neither `loop_in_flight` nor `goal_in_flight`, and are invisible to
the mutual-exclusion protocol (§2). The 13-value `exit_reason` enum — CONFIRMED
emitted at `lib/templates.py:5616`, with the emitted comment *"The
operator-completed dispatch loop MUST implement the WHOLE enum"* — has no value
for a fan-out worker that died. `agent()` returning `null` on terminal API
error after retries has nowhere to be recorded.

**B-4 (blocks maintainer use at scale, not at all scales). The pollution
detector is unsound under concurrency** (§8), in both directions.

---

## 10. Spec gaps to fill (before anything beyond dev tooling)

**G-1 — Trust-ramp semantics for a fleet.** Inherit / floor / ineligible is
unspecified (§5). The ramp is denominated in operator-reviewed task outcomes;
fan-out changes the ratio of work to review, which is the quantity the ramp
exists to bound. **Owner decision, cluster-A class.**

**G-2 — Concurrency accounting for non-task agents.** Either fan-out agents
enter the existing budget (and then something must claim, lock, and release on
their behalf) or the PRD must say explicitly that they are outside it and why
that is safe. Silence here is what B-3 is.

**G-3 — Gate-cost posture under concurrency.** The emitted `TIMEOUTS` were
costed for one agent. If more than one is ever contemplated in front of them,
the timeouts need either a stated concurrency assumption or a per-N derivation.
Note the honest constraint: raising the timeout trades a false refusal for a
slower true one, and the KB's rule is that a length/count fence inside a
security predicate is a fail-open guard — so this is not a one-line fix.

**G-4 — `exit_reason` vocabulary for worker-level failure.** The enum is closed
and complete for runs; it has no member for a dispatched *worker* dying.

**G-5 — Detector attribution.** For maintainer use at any real width, the
pollution check needs per-writer attribution or a scoped fixture, not a
whole-repo diff.

**G-6 — PRD/implementation version skew (found incidentally, worth recording).**
The highest PRD in the root is `v2-6-0`; `PROTOCOL_VERSION` is `2.7.3`. Any
delta written against the PRD needs to state which document it amends.

> **CLOSED 2026-08-08.** Two halves, both answered.
>
> **The version half** — the PRD's `**Version:**` field read 2.7.0 while
> `PROTOCOL_VERSION` was 2.7.3. Fixed at v2.7.4 and now *pinned*:
> `tests/test_installer.py` asserts the PRD header, the Companion mirror line,
> and both README lines track `PROTOCOL_VERSION`, so the skew cannot recur.
>
> **The filename half** — answered by a convention that already existed and
> that this gap was written without noticing: the PRD's own filename note
> (search `Filename note`) states the filename records **when the pair was
> cut**, not what it describes. It now also carries the decidable trigger it
> lacked — *since 2.7.0 releases amend in place; a new pair is cut only by an
> explicit re-issue recorded in the changelog* — together with the history that
> contradicts the tidier version of the rule (three of the five root pairs were
> cut by code commits, and the v2.3.0 "fold" produced no file). So G-6's
> operative clause is satisfiable: **a delta amends the pair whose
> `**Version:**` equals `PROTOCOL_VERSION`**, and `tests/test_installer.py`
> pins that value across the PRD header, the Companion mirror line and both
> README lines. README carries the same statement.
>
> **Renaming was considered in two shapes and declined in both**: rename to
> `v2-7-4` (would contradict the shipped fold convention, and must then recur
> every release), and a stable unversioned filename (same objection, plus it
> invalidates the *path* of every historical citation rather than just its
> line). Both cost an emitted-body move: the PRD filename ships inside
> `.claude/hooks/iteration-summary-enforcement.sh`.
>
> **The larger half G-6 did not name** was line-citation rot — citations into
> the PRD were correct when written and silently invalidated by later edits
> (one target moved 654 → 670 → 713 → 739 → 759 across five releases). Closed
> by `tests/test_doc_citations.py`, which derives each cited line from a
> uniqueness-checked anchor instead of trusting a stored integer.

---

## 11. Seam impact — summary

| adoption shape | §8.4 triggers | classification |
|---|---|---|
| maintainer tooling, nothing emitted | none | **not a seam event** |
| an emitted steering/config doc, off by default | none (TEL-01/DS-01 precedent: *"Seam impact: none"*) | in-version MINOR |
| an emitted orchestrator / runner | **§7.2 membership** | seam bump **+ owner-side pin event**, and reopens a decision recorded as declined (§7) |

For the recommended verdict — dev tooling only — **seam impact is none, and no
pin moves.**

---

## 12. PRD sections a delta would touch

Recorded so the scope is visible even though the verdict does not spend it. A
future adopt-narrowed delta touching emitted surface would edit:

- **Recovery & State** (`:310-341`) — the concurrency rule, the two in-flight
  lists, the `exit_reason` enum. This is where B-3/G-2/G-4 land.
- **Phase 0 step 6** (`:434-450`) — the skippable-decision block, if a flag is
  added; the verbatim question phrasing convention applies.
- **Phase 0.5 preview** (`:471`) — every opt-in that emits a file lists it here.
- **Phase 6.5 / Phase 7** (`:922-991`) — subagent definitions, worktree
  isolation, the model-assignment table, and the Companion's `:161`
  subagents-spawning-subagents note, which a fan-out feature falsifies.
- **Phase 9.5 / 9.6 / 9.7** (`:303`) — the ramp prose and the mode-gating rule
  (9.7 requires 9.5 or 9.6), if fan-out were ever a mode.
- **Assumption Ledger** (`:368`) — the *"Subagent token multipliers (~2–3×
  mixed-model)"* row is calibrated for the current mixed-model split; a fleet
  changes its basis and the row carries an explicit re-validation trigger.
- **Companion Migration notes** — a new opt-in flag needs its entry.
- **`SEAM-CONTRACT-v2-0-0.md` §9** — only if orchestration is ever emitted.

---

## 13. If it were ever adopted narrowly: the TEL-01/DS-01 twin

Not a design — the shape the config surface would have to take, recorded because
it is the shape this project has shipped twice and knows how to freeze.

**The twin's mechanics, CONFIRMED.** `telemetry_enabled(cfg)` /
`design_steering_enabled(cfg)` (`lib/installer.py:72`, `:101`) read defensively
— an absent key never raises — and the emission is guarded:

```python
if telemetry_enabled(cfg):
    add(".claude/steering/telemetry.md", TEMPLATES["telemetry"](cfg))
if design_steering_enabled(cfg):
    add(".claude/steering/design.md", TEMPLATES["design"](cfg))
```

with the invariant stated in-comment: *"Off by default: the default plan is
byte-identical to the pre-TEL-01 baseline."* CONFIRMED independently in §4: an
unknown top-level key leaves the plan digest unchanged.

A `workflow_orchestration_enabled` twin would therefore be:

- a **top-level** flag, default `false`, read defensively, YAML-boolean
  normalised fail-loud;
- recorded in `.bootstrap-state.json`, inert to older readers (same
  forward-compat posture as `telemetry_export_enabled` and `exit_reason`);
- when `false`: **zero** plan actions, byte-identical digest, counts stable at
  57 / 69 / 59;
- when `true`: emitting **documentation only** — a steering doc describing how
  an operator may use the harness's own workflow feature against their project,
  in the same *compose-do-not-fork* posture TEL-01 takes toward OpenTelemetry
  (*"documentation over the substrate's own opt-in telemetry, not new plumbing —
  the protocol opens no socket and emits nothing itself"*);
- emitting **no executable**, which is what keeps §7.2 membership and therefore
  the seam untouched.

**And even that stays blocked on B-1 and G-1/G-3.** A steering doc that tells an
operator to fan out in front of the emitted gate suite is a doc that walks them
into §3.4. The documentation shape is safe only once the gate-cost posture has
an answer; it is recorded here as the *shape*, not as a recommendation to build
it now.

---

## 14. What was not assessed

- Whether the `Workflow` tool's own scripts are safe to author (a maintainer
  practice question, not a protocol one).
- Cost. The Assumption Ledger's 2–3× subagent multiplier row is the right place
  and it explicitly asks for re-derivation from `token.usage` by `agent.name`;
  no such data exists here.
- Retrofit mode. `mode: retrofit` is out of scope by owner decision (backlog
  J-21) and untested by construction; nothing above was measured against it.
- Any claim about behaviour on a machine with a different core count. Every
  concurrency figure is from a 12-core host where the tool's own cap resolves to
  10; N=16 was driven deliberately above that cap to measure the stated ceiling.

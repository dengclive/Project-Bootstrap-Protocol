# Bootstrap Protocol — Deterministic Installer + Plugin

> **Current release: v2.8.0.** `PROTOCOL_VERSION = 2.8.0`. **External consumers
> pin the annotated git tag `v2.8.0`** — pinning a moving `main` is pinning a
> branch, not a release. This line was stale at `v2.6.0` through three releases
> (2.6.1, 2.7.0, 2.7.1) and is now part of the release checklist.
> *Correction (WP4, 2026-10-14):* to follow [Getting started](#getting-started),
> use a clone of `main`. The `v2.8.0` tag predates that route: at the tag, the
> installer prints no `Next steps:` block, and the protocol document has its
> old file name (see "Why a filename need not match the version" below).
>
> The normative spec is still `Bootstrap-Protocol-v2-8-0.md` +
> `Bootstrap-Protocol-Companion-v2-8-0.md`: **2.6.1 through 2.7.4 are gate
> corrections, with one exception — 2.7.0 added two configuration keys
> (`commands.execute_in_cwd`, `workflow.implementer_isolation`), which is why it
> is the MINOR in the run and why the PRD carries a v2.7.0 block. No other
> release in that range adds operator-facing surface a PRD would describe.**
> 2.8.0 is the LIT literature fold — nine additive doc/steering items plus one
> priming-contract change ([LIT-07]) — amended into the same pair in place,
> with a v2.8.0 block at the PRD head and a migration note in the Companion.
> **Why a filename need not match the version:** the filename
> records **when the pair was cut**, not what it describes. Through 2.6.0 a new
> pair was cut at each MAJOR/MINOR; **since 2.7.0 releases amend the pair in
> place**, and a new one is cut only by an explicit re-issue decision recorded
> in `docs/changelog.md`. This pair was cut as `v2-6-0` and renamed `v2-8-0`
> on 2026-08-14 (freeze exception 70), a few hours after the `v2.8.0` tag, so
> at that tag its files still carry the `v2-6-0` name. **The normative pair is
> the one whose `**Version:**` equals `PROTOCOL_VERSION`** — and
> `tests/test_installer.py` pins this file, the PRD header and the Companion
> mirror line to that one value, so they cannot drift apart. The full rule,
> with the history that contradicts the tidy version of it, is in the PRD's
> own filename note.
>
> Older PRD/Companion pairs are retained as historical record — with
> one exception worth knowing: `Bootstrap-Protocol-v2-5-0.md` carries seven
> corrections applied *in place* on 2026-07-28, each marked at its edit site,
> made before a 2.6.0 document existed to hold them. They are native text in the
> v2-8-0 pair now.
>
> Release record: `docs/changelog.md` (newest entry first). Known deferrals:
> `docs/deferred-backlog.md` — cluster **X-36** is the live one (rows `a`–`t`);
> clusters **J**, **K** and **L** are the v2.6.0 upstream-fix and review residue;
> cluster I is the v2.5.0 release-review set.
>
> **2.6.0 was corrective, not additive — and every release through 2.7.4 was too**
> (2.7.0's two configuration keys excepted); **2.8.0 is the first additive
> release since** (the LIT fold above).
> Every 2.x release before it was an opt-in flag defaulting to `false`, so an
> operator who left it alone saw nothing change. This one has no such flag:
> gates that were silently inert begin to block, `dependency-gate` starts catching
> package-install channels it used to walk past (`cargo add`, `uv add`, `go get`,
> `curl … | sh`, `npx`/`uvx`/`pnpm dlx`), and a parser outage now fails
> closed instead of allowing. Upgrading an existing install is **not** a no-op.
> Read the Companion's Migration notes ("2.5.0 → 2.6.0") before re-running the
> installer — it closes a confirmed RCE, it will surface real test and
> CI failures that 2.5.0 was reporting to nobody, and it rewrites
> `.claude/steering/deps.md`, which you must merge by hand if you have edited it.

## Getting started

You bootstrap a project by giving Claude the protocol document. Claude runs
the protocol with you, one phase at a time, and runs this repository's tools
for the parts they automate: `bin/bootstrap-interview` proposes the
decisions and writes `bootstrap.config.yaml`, and `bin/bootstrap-install`
writes the `.claude/` tree from it. The install writes the steering docs as
stubs, and Claude then fills them in with you.

### Before you begin

- Claude Code.
- Python 3. The tools use only the standard library; CI tests them on
  Python 3.12.
- Your project, in a git repository.
- A clone of this repository at `main` (see the correction in the banner).

### Bootstrap a new project

1. Clone this repository. These steps write the clone's path as `$T`, for
   example `T=~/src/Project-Bootstrap-Protocol`.
2. At your project's root, start Claude Code with access to the clone:
   `claude --add-dir "$T"`.
3. Ask Claude: "Read `$T/Bootstrap-Protocol-v2-8-0.md` and bootstrap this
   project." The protocol tells Claude which tool to run at each step.
4. In Phases 0 and 0.5, Claude runs
   `python3 "$T/bin/bootstrap-interview" analyze --prd <your PRD>`, takes you
   through its proposals one question at a time, and records your answers in
   the ANSWERS block of `bootstrap.interview.md`. It then runs
   `python3 "$T/bin/bootstrap-interview" synthesize`, which writes
   `bootstrap.config.yaml`, and shows you the plan from
   `python3 "$T/bin/bootstrap-install" --dry-run`. To answer the questions
   live instead, see [Answer the interview live](#answer-the-interview-live).
5. When you approve the plan, Claude runs
   `python3 "$T/bin/bootstrap-install"`. The install writes the hooks,
   `settings.json`, the skills, commands and agents, the steering docs, a
   thin `CLAUDE.md` and the state file, and ends with a `Next steps:` block.
6. Claude runs Phases 1 to 8 on the installed files. The install writes
   `product.md`, `tech.md`, `structure.md` and `ci-cd.md` under
   `.claude/steering/` as stubs, and `Next steps:` names each stub the
   install still owns. Claude fills them in with you and shows you each
   file.
7. Claude offers the Phase 9 smoke test, then the Phase 10 handoff. The last
   line of `Next steps:` says how to record the smoke test and mark the
   bootstrap complete in `.claude/.bootstrap-state.json`: record it, or ask
   Claude to.

If a hand edit leaves `.claude/.bootstrap-state.json` unparsable, the next
install keeps a copy of it as
`.claude/.bootstrap-state.json.pre-unparsed-<UTC stamp>`, prints a
`warning:` line that names the copy, and carries on without the keys it
couldn't read. Restore them from the copy.

### Retrofit an existing project

If your project already has code that you want to keep, run `RETROFIT.md`
instead, with `bin/retrofit-interview` in place of `bin/bootstrap-interview`.

**[Dated note 2026-10-16.]** The retrofit route is disabled until its
backlog rows are built (backlog row Z-72). `bin/bootstrap-install` refuses a
retrofit config, and refuses every run but `--uninstall` on a project that
already has `.claude/.retrofit-state.json`; `bin/retrofit-interview` refuses
every command. Don't run the greenfield route over an existing codebase in
its place: ask the maintainers instead. The steps below describe the route
as it will work once it's re-enabled.

1. Start Claude Code at your project's root, as in steps 1 and 2 above, and
   ask Claude: "Read `$T/RETROFIT.md` and retrofit this project."
2. Claude does R-1 first, then R0 step 1. When that step archives an
   existing `.claude/` to `.claude.archived-<timestamp>/`, Claude leaves
   `settings.json`, `settings.local.json` and the `.retrofit-state.json`
   that R-1 wrote in place: the installer merges its hook wiring into your
   `settings.json`, it never writes `settings.local.json`, and R0.5 extends
   R-1's state file.
3. Claude runs `python3 "$T/bin/retrofit-interview" analyze`, which scans
   the code, writes first cuts of the inventory under `.claude/inventory/`
   (the files of R0 steps 3, 4 and 12, and step 8's metrics as stubs), and
   writes its proposals and open questions to `bootstrap.interview.md`.
   Claude checks each first cut against its step's list in `RETROFIT.md`
   and completes it: for example, step 3's convention groups, the
   dependencies of every manifest but the root `pyproject.toml`,
   `requirements.txt`, `package.json` and `Cargo.toml`, step 4's product
   summary, step 8's metrics, and step 12's documentation, PR-template and
   issue-tracker checks. Claude also does the R0 steps that `analyze`
   doesn't (2, 5, 6, 7, 9, 10 and 11) from `RETROFIT.md`, among them step
   5's extraction plan for your `CLAUDE.md` and the mandatory step 10.
   Claude resolves the proposals with you one question at a time, then
   runs `python3 "$T/bin/retrofit-interview" synthesize`, which writes
   `bootstrap.config.yaml`.
4. Claude shows you the plan from `bootstrap-install --dry-run` and, when you
   approve it, runs `bootstrap-install`.
5. If the install skipped a root `CLAUDE.md` that already existed, Claude
   moves that file aside and re-runs `bootstrap-install`: it creates only
   `CLAUDE.md`, and Claude merges your old file into it, as R8.E.1 says.
6. Claude runs R1 to R5.5 on the installed files, and R8.F for `ci-cd.md`,
   which fills in the steering stubs with you. Then come the R6 smoke test
   and the R7 handoff, whose step 5 marks the retrofit complete in
   `.claude/.retrofit-state.json`.

### Approve Claude's writes under `.claude/`

Run the route in an interactive session. Claude writes the steering docs and
the state file under `.claude/`, which Claude Code protects. In an
interactive session, in Claude Code's default permission mode, Claude Code
asks you to approve each of those writes, so expect to approve the steering
docs one at a time. Under `claude -p`, Claude Code denies Claude's Write and
Edit tools there, even when your allow rules permit them (measured on Claude
Code 2.1.283 and 2.1.289), and the protocol tells Claude to stop and tell
you rather than write the file another way. The same holds for the decision
record that the `escalate` skill writes under `.claude/sessions/`. How a
headless run gets that permission is decision D5, which is open.

### Re-install after a change

To change a decision later, such as a command, a principle or a hook, edit
`bootstrap.config.yaml` and re-run the installer. Commit
`bootstrap.config.yaml`, because a clone needs it to re-install. Without
`--force`, the installer never overwrites a file that you or Claude edited:
the re-install prints a `SKIP` line for it and keeps your version, so that
file doesn't get the change. A file that exists before the first install is
kept the same way, so install before you fill in the docs.

To take the installer's current version of one skipped file, move that file
aside and re-install: the install re-creates only that file. Then merge your
edits back from the moved copy by hand. This works in a fresh clone too,
which has no installer manifest because git ignores it. Don't use `--adopt`
for this: it records every skipped file as the installer's, so the next
install replaces each steering doc you or Claude filled in, with no backup.
`--force` isn't limited to one file either: it replaces every file that you
or Claude edited. To see which files it would replace, run
`bootstrap-install --force --dry-run`: it lists each one, says where its
current version would be saved to under `.claude/.installer-backups/`, and
writes nothing.

### Answer the interview live

`bootstrap-interview interactive` asks the same questions one at a time and
reads your answers from the keyboard. Run it yourself, in a terminal:

```bash
python3 "$T/bin/bootstrap-interview" interactive --prd <your PRD>
```

Claude doesn't run it for you: in Claude's Bash tool it has no terminal, and
it refuses. It exits 2 and writes no config when stdin is closed, when stdin
ends before the first answer, or when stdin isn't a terminal and no answer
arrives within `BOOTSTRAP_PROMPT_TIMEOUT` seconds (default 30). If you
answer through a stdin that isn't a terminal, such as `ssh` or
`docker run -i` without `-t`, set `BOOTSTRAP_PROMPT_TIMEOUT` to a larger
number of seconds to give yourself time for the first answer. With such a
stdin, the tool prints nothing until it reads the first byte: type the first
answer (the project name) and press Enter to start it. Input that ends
partway, after the first answer, takes the proposed default for every later
question: the tool prints a `warning:` line, and the config's header names
the values that took their defaults. `retrofit-interview interactive` works
the same way, once the retrofit route is re-enabled; for now it refuses (see
[Retrofit an existing project](#retrofit-an-existing-project)).

### The plugin

`plugin/` wraps the interview and the install as a Claude Code plugin with
two commands. Its manifest is `plugin/.claude-plugin/plugin.json`, and Claude
Code prefixes each command with the plugin's name:

- `/bootstrap-protocol:bootstrap-interview` writes `bootstrap.config.yaml`.
  If you don't have a PRD at the required tier, Claude writes one with you
  first.
- `/bootstrap-protocol:bootstrap-apply` previews the install and, when you
  approve it, runs it.

The commands run the plugin's own copies of the tools, under
`plugin/toolchain/`: `bin/bootstrap-install`, `bin/bootstrap-interview`,
every `lib/*.py` module, and the protocol document as `protocol.md`. They
don't run the checkout's `bin/`, so a copy of `plugin/` works on its own.
After the install, `Next steps:` sends Claude to Phases 1 to 8 of that
`protocol.md` to fill in the steering stubs. The plugin has no retrofit
command, and it doesn't copy `bin/retrofit-interview`; for an existing
codebase, follow [Retrofit an existing project](#retrofit-an-existing-project),
where a dated note says the route is disabled for now.

This repository has no marketplace file (`marketplace.json`) yet, so load
the plugin from a clone:

```bash
claude --plugin-dir "$T/plugin"
```

The copies under `plugin/toolchain/` are byte-identical to their sources.
`tests/test_wp4_plugin_toolchain.py` checks each copy's bytes and exec bit
against its source, so it stands in for a review of `plugin/toolchain/`:
reviewing `bin/` and `lib/` reviews the copies. After you edit
`bin/bootstrap-install`, `bin/bootstrap-interview`, a `lib/` module or the
protocol document, re-sync the copies and stage them:

```bash
python3 tests/test_wp4_plugin_toolchain.py --sync
git add -A plugin/toolchain
```

## The question this repository answers

This answers the question (as originally posed against the v2-0-0 document —
the two-layer split below is unchanged through v2.6.0): *"Can Bootstrap-Protocol-v2-0-0.md be a Claude Code plugin, or
deterministic code that configures Claude Code with all the hooks, commands,
etc.?"*

**Both — but they do different jobs, and the split is the whole point.**

## The two layers

The protocol document, `Bootstrap-Protocol-v2-8-0.md`, mixes two
fundamentally different things:

| Layer | Examples | Can it be deterministic? |
|---|---|---|
| **Decisions** | archetype, PRD tier, principles & ranking, secrets paths, TDD policy, MCP choices, autonomous-mode opt-ins | **No** — needs a human. This is an interview. |
| **Scaffolding** | hook scripts, `settings.json` wiring, skill/command/agent files, queue scaffolding, `.gitignore`, state file | **Yes — 100%.** Pure function of the decisions. |

A plugin alone can't conduct the interview (plugins package static assets;
they don't branch on archetype). A single deterministic script can't *make*
the decisions. So the right design **separates them**:

```
bootstrap-interview    ──>   bootstrap.config.yaml   ──>   bootstrap-install
   (decision layer,            (the frozen,                 (mechanical layer,
    needs a human)              reproducible input)          deterministic)
```

The interview's only output is a config file. The installer turns that config
into the entire `.claude/` tree — every *content* file byte-for-byte
reproducible (see Properties below for the metadata caveat). Four steering
docs in that tree are stubs, which Claude fills in with you by following the
protocol (see [Getting started](#getting-started)).

## The decision-layer tool (`bin/bootstrap-interview`)

The interview half is itself two things: *judgement* (which only a human can
sign off) and *the mechanics of eliciting and recording it*. `bootstrap-interview`
automates the mechanics while keeping the human firmly in the loop. It reads a
PRD and **proposes** a complete, valid `bootstrap.config.yaml` — with a written
rationale and a confidence for every non-obvious choice — for a human to review
and edit before it is ever used.

It **proposes, never silently decides.** Where the PRD is ambiguous (contested
archetype, no recognizable signal) it surfaces an explicit OPEN QUESTION rather
than guessing. It maps PRD content to archetype and PRD tier using the
Bootstrap-Protocol-v2-8-0.md Project Archetypes table and PRD-tier definitions, and it reuses
the archetype principle starter sets from `lib/defaults.py` verbatim
(`PRINCIPLE_STARTERS` is imported, not re-listed) — the interview only proposes
*deltas* from those defaults. It **never guesses** `commands.test/lint/format`
(a PRD does not contain them); they are emitted empty and flagged
HUMAN-REQUIRED, and the installer warns about each one it finds empty. Every
draft it emits is validated by shelling `bootstrap-install --print-config`
(the same `resolve_config` the installer uses, enforcing the skip-policy
invariants such as queue⇒loop|goal); the tool refuses to finish if validation
fails.

Two front-ends over one pure proposal core:

- **`analyze` + `synthesize`** — the deterministic, reviewable two-pass flow.
  `analyze` writes a single `bootstrap.interview.md`: every decision shown with
  its rationale, OPEN QUESTIONs called out, and a machine-readable ANSWERS
  block the human edits. `synthesize` merges the (possibly edited) answers and
  emits the validated config. Identical PRD ⇒ identical interview file;
  identical interview file ⇒ identical config (digest-stable, like the
  installer).
- **`interactive`** — a live one-question-at-a-time stdin Q&A over the same
  core, honoring Bootstrap-Protocol-v2-8-0.md's "show before writing" and "one open-ended
  question at a time": each prompt shows the proposal and rationale, Enter
  accepts it, nothing is written until the config validates. With no answer
  to read, it exits 2 and writes no config; input that ends early takes the
  remaining defaults and says so (see
  [Answer the interview live](#answer-the-interview-live)). This front-end is
  intentionally the only non-deterministic surface (like a live wizard) and is
  excluded from the determinism guarantees; the test suite proves it produces
  the same config as the questionnaire for the same answers.

### Optional LLM-assisted proposals (non-default)

By default the *judgement* calls (archetype, PRD tier, principle deltas, TDD
policy, secrets/deps posture) use deterministic keyword heuristics. Passing
`--llm` to `analyze` or `interactive` (or setting `BOOTSTRAP_INTERVIEW_LLM=1`)
instead asks a model to make those calls. The model selection and key come
from the environment (`ANTHROPIC_API_KEY`, optional
`BOOTSTRAP_INTERVIEW_LLM_MODEL`); the `anthropic` SDK is an *optional* import,
never a hard dependency.

This mode cannot weaken the safety properties, by construction:

- The deterministic proposal is **always computed first**; the model only
  *refines* fields on it within bounds the deterministic layer already
  validates. It never builds the proposal from scratch.
- Every model adjustment is bounds-checked: an invalid archetype, a PRD tier
  below the archetype floor, or an invalid TDD value is **rejected** and the
  deterministic value kept, with a visible notice. The model can only move a
  field to another *valid* value with a rationale.
- It **proposes, never decides**: anything the model marks low/`open`
  confidence — or any malformed response — degrades to an OPEN QUESTION or to
  the deterministic value. The model cannot silently resolve ambiguity.
- It **degrades loudly**: with no key/SDK or on any call/parse failure it
  returns the deterministic proposal unchanged plus a notice. It never
  fabricates a model response and never blocks.
- `commands.test/lint/format` are never sent to or read from the model;
  principle starter sets still come from `lib/defaults.PRINCIPLE_STARTERS`
  (the model proposes only PRD-justified additions/ranking).
- The emitted config still passes `bootstrap-install --print-config` exactly
  as in the deterministic path.

Like `interactive`, this path is non-deterministic and excluded from the
determinism guarantees; the deterministic default remains digest-stable.

## What you get

```
bootstrap-installer/
  bin/bootstrap-install        # entry point (stdlib Python, no pip)
  bin/bootstrap-interview      # decision-layer entry point (PRD -> config)
  lib/installer.py             # plan/apply/uninstall engine
  lib/defaults.py              # archetype defaults + skip-policy validation
  lib/templates.py             # every file body as a pure fn of config
  lib/minyaml.py               # stdlib-only YAML-subset parser
  lib/interview.py             # analyze / synthesize / interactive front-ends
  lib/prd_heuristics.py        # deterministic PRD -> decision proposals
  lib/configemit.py            # dict -> minyaml-safe YAML emitter
  bootstrap.config.yaml        # the schema, fully commented
  examples/sample-prd.md       # runnable PRD fixture for the interview
  plugin/                      # Claude Code plugin wrapper
    .claude-plugin/plugin.json # the plugin manifest
    commands/bootstrap-interview.md
    commands/bootstrap-apply.md
    toolchain/                 # copies of the tools, lib/ and the protocol
  tests/test_installer.py      # installer suite: determinism, idempotency, etc.
  tests/test_interview.py      # decision-layer suite
```

## Properties

- **Deterministic (content)** — identical config ⇒ identical *content*
  tree, byte-for-byte. No timestamps or randomness in any emitted file
  body; proven by a digest test across independent runs. The two
  bookkeeping files — `.installer-manifest.json` and
  `.bootstrap-state.json` — intentionally record an install timestamp and
  are therefore *not* byte-stable; they are metadata, excluded from the
  plan, and never participate in the idempotency comparison.
- **Idempotent** — re-running converges; a second run writes 0 files.
- **Non-destructive** — files you hand-edit are detected (via a manifest of
  digests) and skipped, not clobbered. `--force` overrides, and copies
  anything it displaces to `.claude/.installer-backups/<run>/` first, naming
  the location in its output; `--force --dry-run` says where each copy would
  be saved and saves nothing. A `--force` that destroys nothing writes no
  backup and says nothing. `--adopt` records every file the run would skip
  as installer-owned and writes none of them, so the next install replaces
  each of them, a steering doc you or Claude filled in included, with no
  backup. The manifest is gitignored, so a fresh clone has none, and an
  install there keeps every file it would change. To refresh one of them,
  move it aside and re-install (see
  [Re-install after a change](#re-install-after-a-change)).
- **Co-owned where it has to be** — the project-root `.gitignore` and
  `.claude/settings.json` are shared with you, so they are merged rather than
  skipped: the installer owns its managed block / its hook registrations and
  its `never_read_paths` deny rules, and leaves your `permissions.allow`,
  `model`, `env` and any hooks of your own untouched. Skipping `settings.json`
  wholesale would be silently catastrophic — it is the only registration site
  for the shell gates, so a skip disabled all of them at once. A *symlinked*
  `settings.json` is declined rather than merged: replacing it would orphan
  its target, and writing through it would push project-specific hook paths
  into a file your other projects share.
  *Addition (WP3, 2026-10-05):* with `workflow.ultracode: true`, the
  default, the installer also adds `"ultracode": true` to `settings.json`
  and records that it did. A value you set there yourself, `true` or
  `false`, is never replaced (short of `--force`), and with
  `workflow.ultracode: false` the installer removes only a value it added.
  Ultracode is one switch for the whole main session, Sonnet sessions
  included, never for a subagent: the session is told to use the Workflow
  tool on every substantive task with token cost no constraint, so sessions
  cost more. The emitted loop wrappers say to pass
  `--settings '{"ultracode": false}'` on unattended `claude -p` calls.
  Re-running an interview's `synthesize` keeps a `workflow.ultracode` you
  set in `bootstrap.config.yaml`. The Companion's model assignment
  amendment has the details.
- **Reversible** — `--uninstall` removes exactly what it created, including
  un-registering its hooks from a co-owned `settings.json` while leaving the
  rest of that file alone.
- **Loud when it did not enforce** — an install that could not write a
  security-critical file, or whose tree does not dispatch its own plan, exits
  **3** with the reason on stderr. Exit 0 means enforcement was verified.
- **Waits for a running loop** — before its first write, an install locks
  `.claude/.bootstrap-state.json.lock` (and, on a retrofit,
  `.claude/.retrofit-state.json.lock`). If a loop wrapper or another install
  holds the lock for 30 seconds, the install exits **4** and writes at most
  an empty lock file; re-run it once the other process has finished.
- **Inspectable** — `--dry-run` prints the full plan; nothing is written blind.
- **Faithful to Bootstrap-Protocol-v2-8-0.md** — encodes the skip-policy invariants
  (e.g. queue mode requires loop or goal mode), the archetype principle
  starter sets, the conditional hook set (eval-gate only for ai-agent,
  tdd-gate only when TDD is required, loop-cooperation hooks only when an
  autonomous mode is on, etc.).

## Usage

Standalone:

```bash
# 1. produce the config — either hand-write it from the schema, or use the
#    decision-layer tool to propose one from a PRD:

#    a) deterministic two-pass (reviewable questionnaire):
python3 bin/bootstrap-interview analyze --prd docs/prd/PRD.md
#       ...edit the ANSWERS block in bootstrap.interview.md...
python3 bin/bootstrap-interview synthesize

#    b) or a live interactive interview:
python3 bin/bootstrap-interview interactive --prd docs/prd/PRD.md

# 2. preview
python3 bin/bootstrap-install --dry-run

# 3. apply
python3 bin/bootstrap-install

# later: edit config, re-apply (converges, keeps your local edits)
python3 bin/bootstrap-install

# clean removal
python3 bin/bootstrap-install --uninstall
```

As a Claude Code plugin: run `/bootstrap-protocol:bootstrap-interview`,
which produces the config, then `/bootstrap-protocol:bootstrap-apply`, which
runs the deterministic installer. [The plugin](#the-plugin) says how to load
it.

## Honest limitations

- The wizard's *judgement* (good principles, sensible secrets globs, the right
  MCP set) still needs a human. `bootstrap-interview` automates eliciting and
  recording the decisions and proposes defaults with rationale, but it is a
  *proposer*: a human reviews and edits every draft before it is used. It does
  not replace the interview's judgement.
- `commands.test/lint/format` cannot be guessed — a PRD does not contain them.
  The interview leaves them empty and flags them HUMAN-REQUIRED. If one is
  still empty at install time, the installer prints a `warning:` line for it.
  An empty test command makes `test-gate` block every commit. An empty lint
  command means `format-lint-gate` checks nothing and prints nothing. No hook
  runs the format or typecheck command.
- `auto.sh` is scaffolded as a guarded skeleton. The full Phase 9.7 dispatch
  loop is intentionally left for the operator to complete before unattended
  use, matching Bootstrap-Protocol-v2-8-0.md's own trust-ramp guidance.
- The emitted skill/command/agent bodies are faithful stubs (frontmatter +
  intent). They are correct and load, but the deep prompt engineering for
  each skill is a separate effort from the structural scaffolding.
  *Correction (WP3, 2026-10-05):* `spec-new`, `spec-review`,
  `spec-decompose`, `plan-review`, `spec-validate`, `decision-log` and
  `test-author` now carry working bodies: EARS acceptance criteria with
  `version: 1.0.0` frontmatter, task files with a `Files:` list the spec
  check reads, a parallelism map in `plan.md`, validation at the task's
  `spec_version` recorded in `validation.md`, a fixed decision entry
  format, and a commit step before any implementer is dispatched. With
  loop or goal mode on, `spec-decompose` also teaches the `loop_eligible`
  and `goal_supervised_eligible` fields, which the v2.5.0 bullet below
  predates. Every skill with a Companion row carries its model line, and
  `test-author` has a command. `code-review` and `pr-author` remain stubs;
  the reviewer agent carries the code review. The spec skills write under
  `.claude/specs/`, which Claude Code protects: under `claude -p` its Write
  and Edit tools are denied there (decision D5 is open), so smoke stages
  1-2 run end to end only in an interactive session.
- **The stub posture extends further than skills (v2.5.0 release review):**
  the emitted **drift/alarm layer is a tier-1 tool-call notice only** —
  tier-2/tier-3 escalation, the tier-3 hard block and its `.drift-tier3-*`
  sentinel, audio dispatch, and the duration/file-read triggers described in
  the PRD's §6.E are **not implemented** by the emitted hooks, and
  `audio-alerts.config` says so (`drift_tier3_enforced=false`; thresholds are
  baked at install time). Likewise the **agent-side autonomous cooperation
  contract is not emitted**: `CLAUDE.md` carries no loop/goal behavioral
  addenda, the implementer agent has no mode-variant blocks, and the
  greenfield `spec-decompose` stub does not teach the
  `loop_eligible`/`goal_supervised_eligible` fields the wrappers hard-require
  (the wrappers fail closed — they refuse rather than run). Backlog I-1/I-2
  track both; complete them (or work operator-in-the-loop, where none of
  this binds) before relying on the autonomous modes.
  *Correction (WP2, 2026-10-03):* the drift detector now implements all
  three tier-1 triggers — tool calls, minutes, and repeated reads of one
  file, each counted since the last checkpoint (or the session start). Its
  notice reaches the model once per arming, and a checkpoint re-arms it.
  `/ack-drift` also re-arms it: each threshold becomes the larger of the
  threshold and that signal's value at the ack, plus half the configured
  threshold, rounded up. Tier 2, tier 3, the `.drift-tier3-*` sentinel and
  audio dispatch are still not implemented.
  *Correction (WP3, 2026-10-05):* the greenfield `spec-decompose` now
  teaches the five eligibility criteria and the `loop_eligible` field when
  loop mode is on, the sixth criterion and `goal_supervised_eligible` when
  goal mode is on, and the queue sections when queue mode is on. `CLAUDE.md`
  still carries no loop or goal addenda, and the implementer still has no
  mode-variant blocks (backlog I-2, WP6).
- **Claude Code shows the model one block reason per tool call.** When two
  hooks exit 2 on the same tool call, the model receives one reason and the
  others are dropped. With prompt changes and failing tests in one
  `git push`, ci-mirror and eval-gate both block, and the model may see
  only eval-gate's reason: it fixes the evals, pushes again, and only then
  learns that CI fails. When eval-gate blocks a push because the eval
  command failed or is missing, its message says that ci-mirror may also
  block. The push itself stays blocked either way.
- **Worktree isolation only isolates what follows the working directory
  (W-1, issue #29).** The gates run your configured command bare — no `cd` —
  which is what lets a plain `pytest -q` follow the `implementer` subagent
  into its worktree. A command that reaches its code through a *fixed mount*
  (`docker compose exec`, `kubectl exec`, `ssh`, `vagrant ssh`, a devcontainer
  CLI) does not follow it: it runs against the main checkout, so the gate can
  report green on code the agent never built. Answer the interview's **command
  execution location** question honestly — `commands.execute_in_cwd: false`
  makes the installer drop `isolation: worktree` and start
  `max_concurrent_tasks` at 1 rather than leave you with a gate that lies.
  Override with `workflow.implementer_isolation` (`auto` | `worktree` |
  `none`); **do not hand-edit the emitted `implementer.md`**, which trips the
  digest guard and freezes that file against upstream fixes. To check your own
  environment: from inside `.claude/worktrees/<n>/`, run your test command's
  transport with `pwd` substituted (`docker compose exec -T app pwd`).
- **The spec commit check runs from git hooks, and ships in warn mode (WP3,
  2026-10-05).** The installer writes `pre-commit` and `pre-merge-commit`
  shims into the repository's hooks directory (`.git/hooks`, shared by every
  worktree). They run `.claude/githooks/dispatch`, which runs
  `.claude/githooks/spec-check.sh` on the staged files of agent commits only
  (`CLAUDECODE=1`); your own commits are never checked. A changed file under
  `hooks.spec_gate_commit_prefixes` must be listed in some task file's
  `Files:` block. With `hooks.spec_gate_commit_mode: warn`, the default, an
  agent commit of an unlisted file goes through with the check's message;
  `block` refuses it. The installer never writes over a hook it did not
  write: with husky (`core.hooksPath`), lefthook or the pre-commit framework,
  it leaves the hook alone and prints a `warning:` line saying what to add,
  `if [ -f .claude/githooks/dispatch ]; then bash
  .claude/githooks/dispatch pre-commit || exit 1; fi` (and the same for
  `pre-merge-commit`): the guard lets a commit through on a branch from
  before the install and once the check is turned off. It cannot tell
  whether a line you added runs (one after an `exit` or an `exec`, or in a
  comment, never does), so it keeps warning on each re-install and says how
  to confirm it: commit a file under one of
  `hooks.spec_gate_commit_prefixes` that no task file lists from a terminal
  with `CLAUDECODE=1 git commit`, which should print `spec check` (a file
  outside them, or one a retrofit install's legacy allowlist covers, is not
  checked, so it prints nothing; the warning names a file the check
  covers, asks for one when the allowlist covers every file name it tries,
  or says that no commit can confirm the line yet). With husky 9,
  put the line in `.husky/pre-commit`, not in `.husky/_`, which husky
  rewrites.
  `.git/hooks` is not versioned, so a fresh clone has no shim until you
  re-run the installer; until then the `PreToolUse` spec-gate-commit hook
  checks the index before each `git commit` and, when it finds an unlisted
  file, says that the git hook is missing. Renaming `settings.json` does not
  turn the check off: set `hooks.spec_gate_commit: false` and re-install,
  which removes the shims the installer wrote and names any hook in this
  repository's hooks directory (husky 9's `.husky/<hook>`), and any lefthook
  or pre-commit framework config at the top, that still mentions
  `.claude/githooks/dispatch`, for you to remove; a `core.hooksPath` that
  every repository reads is left out. A commit that concludes a
  merge is checked only on the merge's own changes: conflict resolutions
  and edits made during the merge, judged against git's automatic merge
  result. The commits it brings in are not checked again, and your own
  commits never are, so merging a teammate's branch can bring in a file no
  task file lists (backlog Z-29). In a project below the repository top (a
  monorepo package), the installer writes no git hook, because one would run
  for every commit in the repository; there the `PreToolUse` hook checks the
  project's own paths against its own task files, and misses
  `git add X && git commit` and `git commit -am`. If the repository top
  has an install of its own, its git hook also checks the project's commits
  against the top's prefixes and task files; the project's install says
  so, and says to narrow the top's prefixes, when the top was installed
  first or when the project is re-installed (backlog Z-50). *Upgrading:* an
  install made before WP3 refused an agent commit of a file no spec named;
  re-installing with the same config makes that commit go through with a
  warning, and the install does not say so. Set
  `hooks.spec_gate_commit_mode: block` before you re-install to keep
  refusing it (backlog Z-28).
- **Implementer branches land through `.claude/merge-back.sh` (WP3,
  2026-10-05).** With worktree isolation, the implementer commits on its
  worktree branch. After the reviewer approves, the main session runs
  `.claude/merge-back.sh <branch>`: it refuses a main checkout whose tracked
  files have uncommitted changes, merges with `--no-ff --no-commit`, runs
  the spec check (on the merge's own changes) and the test gate on the
  merged result, commits, and removes the worktree and the branch. Its last
  line, `merge-back: <STATUS>`, says what happened, so do not cut its
  output with `head`: a reader that stops early ends the run with no last
  line and can leave the merge in progress (`--continue <branch>` then
  concludes it); on a conflict it hands
  the merge to the integrator agent, and `--continue <branch>` finishes it.
  Do not merge implementer branches by hand: an agent's hand-typed
  `git merge` that makes a merge commit runs the spec check but not the
  test gate, and one that fast-forwards, as it does when your branch has
  not moved since the implementer's branch point, runs no hook at all
  (backlog Z-29, Z-33). merge-back runs your tests inside one Bash call; if
  that call outlasts the Bash timeout, Claude Code moves it to the
  background, where, by Claude Code's own message, it is stopped after 30
  minutes (not measured), and a headless
  `claude -p` session must wait for it in the same turn (backlog Z-45). In
  a project below the repository top, merge-back runs its git steps at the
  top, across the whole repository, and the gates in the project; there
  implementer isolation `auto` resolves to `none`, because Claude Code
  makes the worktree at the repository top, where the gates do not find
  the project (backlog Z-44). The installer also writes
  `"worktree": {"baseRef": "head"}` into
  `settings.json`, so worktrees start from your local `HEAD` and see a spec
  you committed but did not push. It keeps your own `"fresh"` or `null` with
  a warning, and declines (exit 3) any other `baseRef`, because Claude Code
  then ignores the whole file. `.claude/.gitignore` ignores `/worktrees/`;
  if you edited that file, a re-install keeps your copy and warns when it
  lacks the line and nothing else ignores the worktrees.

## Tests

The suites are standalone scripts that call `sys.exit()`. Run the whole set
through the runner — this is what CI runs, so local and CI cannot drift:

```bash
bin/run-tests            # all suites, per-suite table, non-zero if any fails
bin/run-tests -q         # totals only (suppress per-check output)
bin/run-tests -k retrofit  # only suites whose filename contains "retrofit"
```

**Do not use `for t in tests/test_*.py; do python3 "$t"; done`.** The loop's
exit status is whatever the *last* suite returned, so a suite that fails in
the middle scrolls past and the run still looks green. Summing the printed
"N passed" lines has the mirror-image blind spot: a suite that dies on an
unhandled exception prints no summary at all, so its checks silently vanish
from the total instead of registering as a failure. The runner reports both,
and (when git is available) fails the run if a suite writes into the working
tree instead of its fixture (emitted hooks resolve paths via
`${CLAUDE_PROJECT_DIR:-.}`, so an unpinned hook invocation logs into *this
repo* — that is how a 1500-line `.claude/logs/hooks.log` once accumulated here
and got committed). The check snapshots `git status` with `--ignored
--untracked-files=all`, so it sees writes into gitignored paths — including
`.claude/logs/` itself — and into already-untracked directories, not just new
tracked changes. Outside a git checkout the check is reported as skipped rather
than passed silently.

Individual suites still run directly when you want one in isolation.
**[Dated note 2026-10-16.]** While the retrofit route is disabled (backlog row
Z-72), run one through `bin/run-tests -k <name>` instead: the runner opens the
route for the retrofit fixtures, and some suites, `test_retrofit.py` among
them, fail when run directly.

```bash
python3 tests/test_installer.py           # plan, e2e, AC-A0, R-6, GR2/TEL-01
python3 tests/test_interview.py           # parser round-trips, TEL-01 wizard
python3 tests/test_retrofit.py            # retrofit track
python3 tests/test_greenfield_golden.py   # golden digests (GOLDEN_UPDATE=1 to re-baseline)
python3 tests/test_gate_substrate.py      # IC-3 state field + migration
python3 tests/test_validate_only.py       # IC-1 --validate-only
python3 tests/test_advisor_model.py       # IC-4 advisor default + fallback
python3 tests/test_root_sentinels.py      # IC-2 dual-honor + root gitignore
python3 tests/test_hook_tiers.py          # IC-7 manifest tiers
python3 tests/test_goal_evaluator_keys.py # Phase 9.6 goal-config keys
python3 tests/test_auto_run_sentinel.py   # Phase 9.7 .run-active race safety
python3 tests/test_ic_gate.py             # IC-1..IC-7 gate + changelog tripwire
python3 tests/test_sdk_gates.py           # IC-5 SDK gate module
python3 tests/test_usage_limit_contract.py # 2.2.0 usage-limit comment contract
python3 tests/test_worktree_command_compat.py # W-1 isolation vs. command cwd
python3 tests/test_issue_fixes.py         # X-30..X-33 (issues #30-#33)
```

Per-suite check counts are deliberately not listed here — they move with
almost every change and the stale numbers were never load-bearing. Run
`bin/run-tests` for the current table.

## Review history

> **Note (2026-07-17):** entries below predate the 2.0.0 rename
> (`BOOTSTRAP.md` -> `Bootstrap-Protocol-v2-0-0.md`); historical
> filenames are preserved as written, per the same archival principle
> applied to the frozen RETROFIT-track documents.

A multi-lens, multi-round review was performed (correctness, security,
determinism, BOOTSTRAP.md fidelity). Findings fixed and now covered by
regression tests:

- **S-1 (Critical)** — the shared hook preamble used `eval()` (a direct
  BOOTSTRAP.md §6.D violation) and re-read already-consumed stdin, so on any
  machine without `jq` the secrets/spec/dependency/test gates silently
  allowed everything. Preamble rewritten: no `eval`, input passed via the
  environment with explicit key traversal.
- **S-2 (High)** — `dependency-gate` parsed only the first token via a
  fragile `sed`; flags and multi-package installs defeated it. Rewritten to
  iterate tokens, skip flags (including value-taking ones like `-r`), strip
  version specifiers.
- **S-5 (High)** — config values were interpolated unescaped into shell
  `case` patterns; a stray `)` produced a broken security hook. Values now
  emitted via quoted heredoc lists, never into shell syntax.
- **F-1 (High)** — generated state file lacked BOOTSTRAP.md-required fields
  (archetype, PRD path, CI/CD opt-out, the three autonomous-mode flags),
  breaking the Phase 10 "enable later" flow. Config is now threaded into
  the state writer.
- **F-2 (Medium, + follow-up)** — `auto.sh` inherited hook stdin
  boilerplate (hung when run from a terminal) and assumed the invocation
  cwd was the project root. It now self-locates from `BASH_SOURCE` and has
  a BOOTSTRAP.md-aligned exit-reason trap.
- **C-1 (Medium)** — `_deep_default` had an operator-precedence defect
  (latent); rewritten with explicit intent.
- **Y-1 (Medium)** — `minyaml` silently mis-parsed tab indentation; now
  raises.
- **S-3 (Medium)** — spec-gate-commit used loose substring matching; now
  word-boundary anchored.
- **D-2 (cosmetic)** — the byte-for-byte determinism claim is now scoped
  accurately to content files (metadata carries an install timestamp).

Investigated and dismissed as non-issues: C-2, C-3, S-4, D-1, D-3.

### Decision-layer tool (`bootstrap-interview`) review

The same multi-lens review (correctness, security, BOOTSTRAP.md fidelity,
schema-validity) was run on the new decision-layer tool. Findings:

- **R-1 (Medium)** — `configemit` mapped config-parser-unsafe characters
  (`"`, `\`) in PRD-derived strings to safe substitutes *silently*,
  contradicting the package's fail-loud ethos. The emitter now collects a
  warning per sanitized value (with its config path) and `synthesize` /
  `interactive` surface them to the human, who is reviewing the config
  anyway. Regression-tested.

Verified during review (covered by `tests/test_interview.py`): PRD text is
only ever a regex *target*, never compiled as a pattern (no ReDoS-by-PRD);
the interview→installer validation boundary uses an argv list, not a shell,
so hostile PRD filenames cannot inject; ambiguous archetypes and missing
PRD signal become OPEN QUESTIONs rather than silent picks; the queue⇒loop|goal
invariant cannot be violated by a generated draft (the interactive front-end
self-corrects, and any hand-edited invalid combo is rejected by the same
`resolve_config` the installer uses, with no file written); the principle
starter sets are imported from `lib/defaults.py`, so a change there changes
the interview output (asserted by test); and the questionnaire and
interactive front-ends produce byte-identical configs for identical answers.

The optional LLM-assisted mode (`--llm`, non-default) was reviewed under the
same lenses. It is constructed so it cannot weaken any safety property: the
deterministic proposal is always computed first and only *refined* within
resolve_config-valid bounds; invalid/out-of-range model output (bad archetype,
sub-floor tier, bad TDD) is rejected with a visible notice; low/`open`
model confidence still becomes an OPEN QUESTION; absence of a key/SDK or any
call/parse failure degrades loudly to the deterministic proposal (never
fabricated, never blocking); the PRD is fenced in the prompt as untrusted
data; and `commands.*` are never sent to or read from the model. All of the
above is covered by `tests/test_interview.py` using an injected fake
responder, so the wiring is tested without network or credentials.

### Decision-layer tool — independent adversarial re-review (round 2)

An independent adversarial reviewer re-examined the decision-layer surface
with no priors, seam-first (PRD → heuristics/LLM → proposal → interview file
→ parse → config dict → emit → minyaml → resolve_config → installer). Four
findings; all fixed and regression-tested. Only `lib/configemit.py`,
`lib/interview.py`, and `tests/test_interview.py` were touched — every
"frozen" file (`installer.py`, `defaults.py`, `templates.py`, `minyaml.py`,
`bin/bootstrap-install`, `tests/test_installer.py`, `BOOTSTRAP.md`) and the
committed `bootstrap.config.yaml` (108 lines) remain byte-identical to the
upload.

- **R-2 (High)** — `configemit` quoted strings but did nothing about
  embedded control characters. `minyaml` is line-oriented and splits the
  document *before* quote handling, so any `\n`, `\r`, or `\t` in a
  PRD/model-derived scalar produced a config `minyaml` could not parse —
  emitted **silently** (no warning), violating both configemit's own
  round-trip contract and the R-1 "sanitization is observable, not silent"
  property. Reachable through the supported `--llm` path: a model-proposed
  principle containing a newline flows into `principles_ranked` → the
  config; the in-process `validate_config_dict` gate did not catch it (only
  the post-write subprocess did). Fixed: `_q` now folds every ASCII control
  char (incl. `\n`/`\r`/`\t`) to a single space and records a per-value
  warning with its config path, exactly like the R-1 quote/backslash case.
  Clean strings stay warning-free; Unicode is preserved. Regression-tested
  (every control char round-trips + is observable; LLM-path variant).
- **I-1 (High)** — `run_interactive`'s `_ask` returns the proposed default
  on EOF; a validated `while True` loop whose default is itself invalid then
  re-prompted an exhausted stream forever. Concretely reachable: overriding
  the archetype to one with a higher required tier (e.g. `platform`, floor
  `full`) leaves the proposed tier default (`standard`) below the new floor,
  so scripted/piped stdin hung indefinitely. The existing suite passed only
  because the sample PRD's default tier already equalled its floor — the
  bug was masked by happy-path fixtures. Fixed: a sticky `_EOF` sentinel is
  shared across prompts; on EOF each validated loop falls back to a
  guaranteed-valid value (archetype/TDD accept the always-valid proposed
  default; the tier loop clamps **up** to the floor, never below, per
  BOOTSTRAP.md Phase 0 step 7). Regression-tested (previously-hanging
  scenarios now terminate; all-defaults and queue-self-correct unchanged).
  *Correction (WP4, 2026-10-14):* `interactive` no longer takes every
  default from input it can't use. It exits 2 and writes no config when
  stdin is closed, when stdin ends before the first answer, or when stdin
  isn't a terminal and no answer arrives within `BOOTSTRAP_PROMPT_TIMEOUT`
  seconds (default 30). Input that ends after the first answer still takes
  the fallbacks above, and now says so: a `warning:` line, and a config
  header that names the values that took their defaults.
- **F-3 (Medium)** — the `analyze`→`synthesize` path did not enforce the
  archetype's required PRD-tier floor. `resolve_config` (frozen,
  installer-shared) validates archetype membership, the queue⇒loop|goal
  invariant, and the TDD enum, but the tier floor is a *decision-layer*
  contract it never policed, so a hand-edited interview file could set
  `prd_tier` below the floor and pass both gates and be written —
  contradicting the round-1 claim that hand-edited invalid combos are
  rejected. Fixed without touching the frozen installer: the interview
  tool's own `validate_config_dict` now adds the BOOTSTRAP.md Phase 0
  step 7 floor check on top of `resolve_config`, so a sub-floor config is
  refused with no file written, mirroring what the interactive front-end
  already enforced. Legitimate upgrades and at-floor configs still pass.
  Regression-tested.
- **R-3 (Medium)** — `render_interview` wrote list answers comma-joined and
  `parse_interview_answers` split on `,`, so a principle containing a comma
  (reachable via LLM `principle_additions` or a human ANSWERS edit — both
  supported) was silently split into multiple principles, breaking the
  documented "identical interview file ⇒ identical config" round-trip.
  Fixed: list answers are now written one item per `  - item` line (no
  in-band delimiter), parsed symmetrically, with the legacy inline
  `key: a, b` form still accepted for back-compat. Regression-tested
  (comma-containing principle/name round-trip; legacy form; empty list).

Re-reviewed the fixes' own diffs (round-1 lesson: an R-1 fix touched three
functions; a cleanup glob deleted a committed file). The R-2 fix is confined
to `configemit._q`; the I-1/F-3/R-3 fixes touch only `interview.py`
(`_ask`/`_EOF`, the three validated loops, `validate_config_dict`,
`render_interview`/`parse_interview_answers`) and their symmetry was verified
end-to-end (a comma+control-char LLM principle now survives the whole
`analyze --llm → synthesize → emit → minyaml → resolve_config` path intact —
the exact cross-finding interaction). The patched tarball was rebuilt from a
**pristine** extract with only the three changed files overlaid, so no test
detritus (`__pycache__`, `.claude/logs`) leaked into the package. Full
holistic regression from the clean extract: `tests/test_installer.py`
34/34, `tests/test_interview.py` 66/66 (46 prior + 20 new), the default
pipeline (analyze→synthesize→`bootstrap-install --dry-run`, 54 files), and
the `--llm` path with an injected fake responder all pass; all frozen files
and the committed config verified byte-identical to the upload.

Verified and not changed: PRD text is still only a regex *target*, never a
compiled pattern (no ReDoS-by-PRD), confirmed against regex-metacharacter
PRDs; the archetype→required-tier table and principle starter sets remain
verbatim-faithful to BOOTSTRAP.md / `lib/defaults.py`; ambiguous/contested
archetype signal still degrades to an OPEN QUESTION; the proposal core is
deterministic across `PYTHONHASHSEED`; the `--llm` prompt still fences the
PRD as untrusted data, never sends/reads `commands.*`, never leaks the API
key, and degrades loudly (never blocking, never fabricating) when no model
is reachable — which is the path that actually runs here.

### Behavioral integration review (round 3) — generated hooks executed

Round 2 verified the config *plumbing*; it did not execute the generated
hooks. Round 3 added a behavioral harness that materializes each hook and
runs it against known-good and hostile inputs under the **no-`jq` Python
fallback path** (the environment the prior S-1 finding lived in). One
security finding in the frozen `lib/templates.py`; fixed (with a documented
freeze exception) and regression-tested in `tests/test_installer.py`.

- **T-1 (High)** — the generated `secrets-gate` matched each never-read
  pattern only as a shell `case` **prefix** glob, so `.env*` blocked `.env`,
  `.env.production`, and `*/​.env` but **not** the extremely common
  `<name>.env` form (`config.env`, `prod.env`, `staging.env`) — a fail-open
  in the one hook BOOTSTRAP.md §6.D requires to fail loudly. Matching was
  also case-sensitive, so `app.KEY` / `.ENV` slipped. Pre-existing in the
  frozen template (the installer's own default `never_read_paths`); the
  existing S-1 test only ever exercised the canonical `/x/.env`, so the
  happy-path fixture masked it. Repro: generate the default config, run the
  secrets-gate hook with `file_path=config.env` → exit 0 (read allowed).
  Fixed by widening the deny-list only: each pattern is also matched with an
  implicit leading `*` (suffix form) and under bash `nocasematch`. The fix
  only ever blocks *more*; no path blocked before is now allowed (verified:
  canonical secrets still block, benign `environment.md`/`prevent.py` still
  allowed). **Freeze exception rationale:** `templates.py` is in the
  "unchanged" set, but a known secret-exposure fail-open in the catastrophic
  gate is exactly the class the prior session itself patched (S-1/S-3/S-5);
  shipping it knowingly under a freeze label would be the wrong call. Only
  the `secrets-gate` branch changed; the other ~20 hook bodies and every
  other frozen file (incl. `BOOTSTRAP.md`, `defaults.py`, `installer.py`,
  the committed config) remain byte-identical to the upload.
- **T-1 follow-up (caught by re-review of the fix's own diff)** — the first
  T-1 patch used `tr` for lowercasing; under the test's restricted no-`jq`
  PATH `tr` is absent, so the hook exited 127, which under the hook
  exit-code convention (`1` = internal error, tool proceeds) is itself a
  fail-open. The installer suite's S-1 tests caught this immediately
  (3 regressions). Re-fixed with pure-bash `shopt -s nocasematch` (no
  external binary can make it fail open). This is the second consecutive
  round where re-reviewing a fix's diff caught a fix-introduced regression
  before delivery.

Behavioral coverage now in `tests/test_installer.py` (executed, not just
planned): secrets-gate blocks `.env`, nested `.env`, `secrets/**`, `*.pem`,
`*.key`, `config.env`, uppercase `.KEY`/`.ENV`, and shell-metacharacter
paths ending `.env`, all under the no-`jq` PATH, while still allowing
`environment.md`/`prevent.py`; dependency-gate token parsing
(multi-package, flags, version specifiers, injection-y names);
test-gate fail-loud on empty `commands.test`, allow on pass, block on fail;
spec-gate-commit blocks unreferenced staged files; tdd-gate blocks a source
write with no newer test; format-lint-gate never blocks; the shared header
survives an unset `CLAUDE_PROJECT_DIR` and malformed/empty/`null` JSON
stdin without crashing or failing open.

**Remaining limitations (honest scope).** The behavioral harness covers the
security-critical PreToolUse/commit gates; it does not yet exercise the
full apply→idempotency→uninstall→`--force` lifecycle against a written tree,
the autonomous-mode wrappers (`auto.sh`/`loop.sh`/`goal-loop.sh` — shipped
as guarded skeletons per the protocol), or `settings.json` event-wiring
correctness end-to-end. Those remain the highest-value next review surface
before unattended production use.

### Independent adversarial re-review (round 4) — lifecycle, archetype matrix, autonomous wrappers

An independent reviewer with no priors built the behavioral harnesses
round 3 deferred: the full apply → re-apply → hand-edit → uninstall →
re-apply lifecycle against a written tree, a 9-archetype apply matrix with
end-to-end `settings.json` wiring assertions, and behavioral execution of
the autonomous-mode wrappers. Six findings; all fixed and regression-tested
in `tests/test_installer.py` (41 → 118 checks). Only `lib/installer.py` and
`lib/templates.py` were touched (with the documented freeze exceptions
below); every other frozen file and the committed `bootstrap.config.yaml`
(108 lines) remain byte-identical to the upload.

- **L-1 (Critical)** — `uninstall()` deleted every manifest path whose
  `state` was not `skipped-local-edit`, comparing nothing against on-disk
  content. The ordinary workflow *apply → hand-edit a generated file →
  uninstall* (no intervening re-apply) **silently destroyed the operator's
  edits**, because the `skipped-local-edit` label is only ever written by a
  *re-apply* between the edit and the uninstall — a step most operators
  never perform. This directly violated the README "Reversible — removes
  exactly what it created" and "leaves operator files" guarantees, and the
  prior happy-path uninstall test (which only ever uninstalled an unedited
  tree) masked it. Fixed in `installer.py` (freeze exception — a silent
  operator-data-loss defect in the reversibility contract is exactly the
  class prior sessions patched under freeze, cf. T-1/S-*): uninstall now
  removes a file **only if its current sha256 still equals the digest the
  manifest recorded**; any mismatch is kept regardless of the `state`
  label. Regression-tested (hand-edit survives uninstall; clean uninstall
  still removes exactly the generated tree).
- **L-2 (Critical)** — re-applying after an uninstall clobbered operator
  edits without `--force`, because the prior manifest still carried the
  original installer digest. Subsumed by the L-1 fix: the modified file is
  now preserved by uninstall and the intact manifest digest drives the
  correct SKIP on re-apply. Regression-tested (edit survives the whole
  apply → uninstall → re-apply cycle; `--force` still overrides).
- **L-3 (Critical, same fix)** — uninstall printed *"CLAUDE.md and manifest
  left for inspection"* while actually deleting `CLAUDE.md`. An *unmodified*
  generated `CLAUDE.md` is correctly removed (it is a generated artifact);
  the message was simply false. Replaced with an accurate
  `removed=/kept=` summary. Regression-tested.
- **W-1 (Critical)** — `loop.sh`, `loop-config.md`, `goal-loop.sh`, and
  `goal-config.md` were **never generated by any template or `build_plan`
  branch**. BOOTSTRAP.md Phase 9.5/9.6 "What the wizard generates" mandate
  all four whenever the respective *mode* is opted in. The consequences:
  (a) `auto.sh` dispatched per-task wrappers that did not exist, breaking
  the queue⇒loop|goal invariant *at the file level* (it held only
  logically, in `resolve_config`); (b) opting into loop or goal mode
  *without* queue produced no wrapper at all. The round-3 history's claim
  that these "ship as guarded skeletons per the protocol" was inaccurate —
  they did not ship. Fixed in `templates.py` (freeze exception, same class
  as T-1: a mandated-artifact omission that defeats a documented protocol
  invariant): added `loop.sh`/`goal-loop.sh` as **guarded fail-safe
  skeletons** modelled on the proven `auto.sh` skeleton — they perform the
  BOOTSTRAP.md Phase 9.5 step-2 race-safe claim (O_CREAT|O_EXCL active
  sentinel, `flock` on the state file, sibling-sentinel cross-mode
  mutual-exclusion check), self-locate via `BASH_SOURCE`, honour the
  `.halt` sentinel, refuse on missing/ineligible task, and **dispatch no
  unattended agent work** (the `claude -p` loop and the `*_in_flight`
  list-append + tmpfile-rename are the operator-completed steps, exactly
  as `auto.sh` leaves its dispatch loop). `loop-config.md`/`goal-config.md`
  emitted with the Phase 9.5/9.6 tunables. Wired into `build_plan` gated
  on the mode flags, independent of queue mode. Regression-tested (all
  four generated on mode opt-in with no queue; both scripts valid `bash
  -n` and executable; fail-safe on no-task-id / `.halt` / unknown task /
  already-claimed; sentinel cleaned on exit; queue mode ships `auto.sh`
  and `loop.sh` together; flock-absent restricted-PATH path fails safe
  with exit 1, not 0/127 — the exact T-1-follow-up regression class).
- **G-1 (Medium)** — the generated `.claude/.gitignore` listed
  `.installer-manifest.json` but omitted `.bootstrap-state.json` and the
  per-iteration scratch sentinels, contradicting BOOTSTRAP.md's "state
  files use the dotfile convention precisely so they can be gitignored as
  a group" and the line-825 enumeration. Committing the timestamped,
  in-flight-list-bearing state file produces spurious diffs and merge
  conflicts on every install. Fixed in `_gitignore`: added
  `.bootstrap-state.json` (+ `.lock`, `.bootstrap-incomplete`) and
  `sessions/.iteration-summary-*`, `.evaluator-feedback-*`,
  `.loop-complete-*`, `.loop-halt-*`, while keeping operator-facing audit
  records (`backlog.md`, `run-summary-*`, `loop-final-*`,
  `decisions-log-*`) committed. Regression-tested.
- **M-1 (Low, folded into L-1)** — uninstall with a corrupt/missing
  manifest printed "nothing to remove" while a full orphaned tree
  remained. Re-worded to state the tree is left intact for manual
  cleanup. (Fail-safe direction was already correct — it never deletes
  blind.)

Re-reviewed the fixes' own diffs (the standing two-rounds-running lesson):
the `installer.py` change is two minimal additions (wrapper emission in
`build_plan`; the rewritten `uninstall`) with no other function touched;
the `templates.py` change is five new functions plus a `_gitignore`
rewrite, with the security-critical `_hook_body`, `_settings_json`,
`_HOOK_HEADER`, and `_auto_sh` confirmed byte-identical at the AST level.
The Python-`.format()`-into-shell skeleton (the doubled-brace hazard that
has produced fix-introduced regressions before) was checked by `bash -n`
on every generated wrapper and by an explicit flock-absent restricted-PATH
run that confirms exit 1 (fail safe), not 0 or 127. The patched tarball
was rebuilt from a **pristine** extract with only the two changed library
files and the extended test suite overlaid — no `__pycache__`/`.claude`
test detritus. Full holistic regression from the clean extract:
`tests/test_installer.py` 118/118 (41 prior + 77 new), `tests/test_interview.py`
66/66 (unchanged), the default pipeline, and the 9-archetype apply matrix
with end-to-end settings-wiring assertions all pass; all frozen files and
the committed config verified byte-identical to the upload.

Verified and not changed: `settings.json` event/matcher wiring is correct
end-to-end for every archetype and for the full loop+goal+queue config
(the "_settings_json correctness gap" flagged for this round is **not** a
defect — every resolved hook maps to the right trigger with the right
matcher, multi-hook same-event coalescing is valid, no orphan entries);
determinism of the content tree, the metadata-exclusion claim, atomic
rename (no `.tmp` residue, dotfile `with_suffix` safe), and partial-state
resume all hold; PRD/config-string injection into JSON/markdown is not
exploitable (`project.name` never reaches `settings.json`; steering-doc
interpolation is inert prose already covered by R-1/R-2 sanitisation);
`auto.sh` remains a correct guarded skeleton (the presence-only
`.run-active` check is a documented skeleton simplification that fails in
the safe direction — refuse-to-start — pending the operator-completed
PID-liveness check from Phase 9.7).

**Production-readiness judgment.** *Certified:* the **deterministic,
operator-in-loop path** — author/generate `bootstrap.config.yaml`, `apply`,
re-`apply`, hand-edit, `--uninstall`, re-`apply` — across all nine
archetypes and all autonomous-mode flag combinations. The lifecycle is
idempotent, non-destructive (the L-1/L-2/L-3 data-loss class is closed and
regression-locked), reversible, and faithful to the BOOTSTRAP.md
conditional hook/file/wiring rules. *Not certified:* the
**unattended/autonomous execution path**. The per-task agent loops
(`loop.sh`/`goal-loop.sh`) and the `auto.sh` dispatch loop now ship as
correct, fail-safe, contract-honouring skeletons — but the `claude -p`
iteration loops, the `*_in_flight` state-list accounting, the
`queue_runs_history` lifecycle, and the PID-liveness double-start guard
are intentionally operator-completed per BOOTSTRAP.md's own trust ramp.
Unattended overnight use remains out of scope by construction and must not
be certified until those loops are implemented and smoke-tested per
Phase 9 stages 4–6.

### v2.6.0 (gate enforcement & security fixes) + seven adversarial-review rounds

**Upstream report (PR #18, 22 commits; PR #19 merged into the same line).**
Source was not a code read — it was a **six-lens adversarial review of a real
v2.5.0 install** that *executed* the emitted hooks against crafted payloads
(`docs/bootstrap-protocol-upstream-bugs-2026-07-28.md`). Static review of the
same files had found neither the RCE nor the dead gates, and a fully green
1016-check suite coexisted with both.

**P0 — security.** `drift-detector` incremented its counter with
`n=$(( $(cat "$ST") + 1 ))`; bash runs command substitution *inside* arithmetic
evaluation and the state file is gitignored and agent-writable, so
`PATH[$(touch /tmp/PWNED)]` executed on the next `PostToolUse` — a clean path
from "the agent writes a file" to arbitrary code execution, bypassing every
`PreToolUse` `Bash` gate. `secrets-gate` was registered only on
`Read|Write|Edit`, leaving every never-read path reachable through `cat .env`
while `secrets.md` told the operator otherwise. Three fail-open paths (a 128 KiB
env-var ceiling, a parser-absent `case` fall-through, `set -e` deaths at exit 1
= "tool proceeds") now fail **closed** — which decides backlog **A-1**.

**P1 — gates that did not do what the operator was told.** `test-gate`,
`ci-mirror` and `format-lint-gate` shipped `async: true`; an async hook's exit
code cannot block and its stderr is suppressed, so `test-gate` printed "Commit
blocked: tests failing" and the commit went through. **The normative document
was wrong too, not just the emission** — v2.5.0 recommended `async: true` for
the CI mirror, a gate whose whole purpose is to exit 2. `spec-gate-commit`
blocked every possible first commit, twice over. `dependency-gate` failed open
on real installs and fired on prose.

**A new class of test.** `tests/test_hook_behavior.py` **executes** the emitted
hooks against a crafted-payload matrix and asserts exit codes — verified to fail
before the fixes (10 failures on pre-fix templates, 0 after). Every other suite
asserts emission determinism, which by construction cannot catch any of this.
Suite 1016 → **1828 checks across 20 suites**.

**Seven consecutive adversarial rounds, and the standing lesson.** Each fix
batch shipped a defect into the class it was fixing; every one was caught by an
independent round and **none** by the green suite. Round 7 alone found an
unhashable `matcher` that aborted install at 22 of 58 files with no manifest and
no gates registered, and a `displaced_keys` proxy that deleted the operator's
`settings.json` keys on any declined write. Treat three green instruments as
absence of evidence: the corpus and the sweep build into empty directories and
never enter the merge, decline, restore or migrate branches where every one of
these defects has lived.

### v2.5.0 (DS-01 design steering) + release-review fixes

**DS-01 (PRs #13–#16).** Opt-in `design_steering_enabled` (+ gated
`design_review_skill_enabled`), a TEL-01 twin with one net-new mechanism: the
archetype-gated interactive offer (the flag itself is accepted on any
archetype — DELTA-02). Emits committed `.claude/steering/design.md` and the
optional advisory `design-review` skill + command (frozen bodies byte-verbatim
from `docs/{design,SKILL,design-review}.md`; DELTA-03 honest-scope clause
included per PR #16). Off-by-default byte-identity is golden-proven; the skill
state flag is `and`-gated on the primary so state can never disagree with
emission.

**Release-review fixes (2026-07-27, freeze-exception no. 16).** A final
holistic adversarial review — spec-tracing the PRD/Companion plus scratch
installs that *executed* the emitted hooks — produced three emitted-byte
fixes before tagging: the `jget` jq-less fallback now renders booleans like
`jq -r` (the `stop_hook_active` guards were failing open without jq);
`iteration-summary-enforcement` gates on a live `.goal-active-*` marker
(it errored on every ordinary session end of goal-enabled installs); and the
drift/alarm layer's emitted files now state their real (tier-1-only) scope —
see "Honest limitations" above and `docs/deferred-backlog.md` cluster I for
everything the review recorded rather than fixed.

### v2.4.0 code fold (GR2-EX / TEL-EX) — mandated-artifact emissions the frozen templates omit

**GR2-EX / TEL-EX (v2.4.0 code fold).** `lib/templates.py`,
`lib/installer.py`, and (for the TEL-01 Phase 0 decision) `lib/interview.py`
are in the frozen set, but the frozen v2.4.0 documents mandate three
additive workspace artifacts (GR2-03a `assumption-ledger.md`, GR2-01
`progress.md` references, GR2-02 trajectory-retention contract) and one
opt-in artifact (TEL-01 `telemetry.md`) that the v2.2.0 code does not emit —
exactly the class **W-1** patched under freeze (a mandated-artifact omission
that defeats a documented protocol invariant). The code baseline was v2.2.0;
the v2.3.0 GR2 doc fold and the v2.4.0 TEL-01 doc fold were both doc-first
and landed no code, so the real code delta was
`2.2.0 → 2.4.0 = GR2-01 + GR2-02 + GR2-03a + TEL-01` plus the version stamp.
Changes are confined to: the new `_assumption_ledger` / `_telemetry` template
functions and their `TEMPLATES` registrations; the GR2-01 prose in
`_claude_md` / `_agents` plus the single-body embedding of the canonical
`progress.md` template in `.claude/specs/INDEX.md`; the GR2-02
comment-contract in the shared `_per_task_wrapper` skeleton (covers `loop.sh`
and `goal-loop.sh`; `auto.sh` untouched, its `exit_reason` enum unchanged);
in `installer.py` the two `build_plan` steering adds (one unconditional, one
flag-gated) plus the one `_write_state` field; in `interview.py` the single
`telemetry_export_enabled` Phase 0 decision (parse + render + interactive
prompt, standalone top-level boolean); the version stamp
(`PROTOCOL_VERSION` 2.2.0 → 2.4.0, `plugin.json`); and the deliberate golden
re-baselines in `tests/test_greenfield_golden.py` (`EXPECTED_DIGESTS` /
`EXPECTED_ACTION_COUNTS`, both fixtures, one per step) and the
`test_validate_only.py` mini-golden (emitted config gains
`telemetry_export_enabled: false`). Every other frozen file and every other
hook/template body remains **byte-identical** to the upload — verified by the
determinism digest on the default-off path and by the per-file golden
diagnostic. No wire surface, no gate, no sentinel, no seam name/location
changed (**seam impact: none**). Re-reviewed the fixes' own diffs (the
standing two-rounds-running lesson): `_telemetry`'s emitted body is verified
byte-identical to the frozen `telemetry.md` modulo the two scoped
`OTEL_RESOURCE_ATTRIBUTES` substitutions; the `.format()`-into-shell wrapper
skeleton was re-checked with `bash -n` on every generated wrapper. Full
suite green from a pristine run: 14 suites, 866 checks (`test_installer.py`
141 → 197, `test_interview.py` 66 → 73, `test_ic_gate.py` 45 → 46,
`test_greenfield_golden.py` 6/6 re-baselined, `test_usage_limit_contract.py`
95/95 with the auto.sh enum untouched). **Deferred, recorded not shipped:**
the GR2-03a *surfacing* behavior (fail-loud non-blocking notice on
model/runtime change) carries locked constraints and is out of this fold; the
retrofit state schema is not extended for the telemetry flag (the flag-gated
`build_plan` add still emits `telemetry.md` on a retrofit plan). Also
recorded as a known, deliberately-untouched inconsistency: pre-existing
emitted hook/wrapper bodies still cite `Bootstrap-Protocol-v2-0-0.md` /
`-v2-2-0.md` (a future doc-reference-normalization pass) — only **new** text
this fold added cites `-v2-4-0.md`.

**Adversarial review of this fold (steps 6–8).** The open PR was reviewed
multi-lens (ten independent finder angles, one refutation-seeking verifier
per candidate, then a gap sweep); fifteen findings were confirmed and all
are fixed in-branch. The two most serious were **upgrade-path** defects
that only appear when the new installer runs over an existing 2.2.0
workspace, which is why the fold's own greenfield-heavy suite missed them:
`apply_plan`'s hand-edit guard only protected *manifest-tracked* paths, so
a file an operator hand-created at one of this fold's **newly planned**
paths (`assumption-ledger.md`, `telemetry.md` — the doc-first v2.3.0
migration note tells them to) was overwritten with no warning; and the
GR2-01 template's only emitted home is `.claude/specs/INDEX.md`, the one
file the wizard directs operators to rewrite, so an upgraded install could
not receive the template without `--force` destroying its spec roster. A
third, **TEL-01 flag truthiness**, inverted explicit privacy opt-outs
(`off` / `no` / `"false"` all read as ENABLED). One security fix:
`telemetry.md` steers OTLP **auth headers** into
`.claude/settings.local.json` and calls it "(gitignored)" while no emitted
gitignore covered it — now it does, so the claim is true rather than
softened. Three findings originated in the **frozen sources** and were
corrected pre-release on the TAR-02..06 precedent (this PR has not merged),
with the emitted copies moved in lockstep and a new equivalence pin
asserting the two telemetry copies differ on exactly the one substituted
line. Full details, including the findings deliberately **not** fixed, are
in `docs/changelog.md` steps 6–8. Suite: 866 → **945 checks**, 14 suites
green; goldens re-baselined three times, diff-verified before each update.
The GR2-01 template moved out of the operator-edited `INDEX.md` into its own
installer-owned `.claude/specs/progress-template.md` so upgrades can actually
receive it, which is the review's one file-count change (56 → 57, 68 → 69).

## License

Copyright 2026 Deng Clive

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this project except in compliance with the License. You may obtain a copy
of the License at <https://www.apache.org/licenses/LICENSE-2.0>, and a verbatim
copy ships in [`LICENSE`](LICENSE).

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

**Applies to this repository, and to what it emits.** The installer writes
scaffolding into your project; that output is yours, and this License does not
attach conditions to the projects you configure with it.

**No NOTICE file, deliberately.** Apache-2.0 does not require one — it requires
that an existing NOTICE be propagated by every downstream redistributor. This
project vendors no third-party code and carries no attributions, so shipping a
near-empty NOTICE would create a permanent obligation for no benefit.

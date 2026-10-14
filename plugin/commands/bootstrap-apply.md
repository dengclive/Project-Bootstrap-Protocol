---
description: Apply bootstrap.config.yaml deterministically (creates the full .claude/ harness). Runs the installer; no interview.
---

# /bootstrap-protocol:bootstrap-apply

Run the **deterministic installer** against the `bootstrap.config.yaml` in the
project root. This is the mechanical layer — it makes no decisions, asks no
questions, and produces a byte-for-byte reproducible `.claude/` tree from the
config.

## What to do

1. Confirm `bootstrap.config.yaml` exists in the project root. If it does not,
   tell the operator to run `/bootstrap-protocol:bootstrap-interview` first
   (that command is the decision layer; it produces the config this command
   consumes).

2. Show the plan first (never write blind):

   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/../bin/bootstrap-install --dry-run
   ```

3. Summarize the plan for the operator: archetype, autonomous-mode flags,
   number of files, and anything in the "skipped (locally modified)" set.
   Surface every `warning:` line the dry run prints on stderr, verbatim.
   Each one is advisory and leaves the exit code alone. For example, the
   dry run prints one for each empty test, lint or format command; for a
   test command whose "no tests yet" the test gate cannot tell from a
   failing suite; for each hook script the run leaves alone rather than
   update, so a config change will not reach it (on a tree with no
   installer manifest the line names `--adopt`), and likewise for an
   edited `.claude/githooks/dispatch`, `.claude/githooks/spec-check.sh` or
   `.claude/merge-back.sh`; for a `.claude/.gitignore` the run leaves alone
   that lacks the `/worktrees/` line, when no other ignore rule covers
   `.claude/worktrees/`; for each git hook of the spec check the run
   would not install (a hook another tool wrote, `core.hooksPath`, a
   project below the repository top), saying why and what to do instead;
   for a project below the repository top, why worktree isolation
   `auto` resolves to none there (or what an explicit `worktree` costs)
   and what `.claude/merge-back.sh` does there; for each security gate an
   earlier install wired that the run would remove, because the config
   turns it off; when `workflow.ultracode` is false but `settings.json`
   still sets `"ultracode": true` with a value the installer did not
   write, which it keeps; and when the run would
   re-create a `settings.json` that was renamed to `settings.json.disabled`
   to turn hooks off.

4. On operator approval, apply:

   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/../bin/bootstrap-install
   ```

5. **Check the exit code before reporting anything.** Exit 3 means files were
   written but the install does NOT enforce — a security-critical file was
   skipped, or a hook is emitted-but-unregistered / registered-but-absent.
   The stdout counts look like a success in that case, so read stderr and
   surface it verbatim; do not tell the operator the install succeeded.
   (Exit 2 is a config refusal — nothing was written; an unparseable
   config names its file and line. Exit 0 is the only outcome
   whose enforcement was verified.) On exit 0, still surface every
   `warning:` line on stderr, verbatim: the apply repeats the dry run's,
   and names each of the operator's own hook commands that begins
   with an unquoted `$CLAUDE_PROJECT_DIR` in a project path that
   contains a space, tab, newline or glob character.

6. Report the create/update/unchanged/skipped counts. Remind the operator
   that local edits to generated files are preserved unless `--force` is
   passed, and that `--uninstall` cleanly reverses the install.

7. Relay the `Next steps:` block the installer prints last, verbatim. It
   is the Phase 10 handoff: it names the whole entry chain (`/spec-new`,
   `/spec-review`, `/spec-decompose`, `/plan-review`), not `/spec-new`
   alone, because the spec commit gate checks commits against the task
   file `/spec-decompose` writes, not against `requirements.md`. It then
   says to commit the spec before an implementer is dispatched and, with
   worktree isolation, to land an approved branch with
   `.claude/merge-back.sh <branch>`. The installer prints the block only
   on exit 0, never under `--dry-run` or `--adopt`, and only while the
   project has no task file under `.claude/specs/*/tasks/`.

## Why this is split from the interview

The Bootstrap Protocol has two layers. The **interview** (archetype, PRD tier,
principles, secrets paths, TDD policy, MCP choices) genuinely needs a human and
lives in `/bootstrap-protocol:bootstrap-interview`. The **scaffolding** (hook
scripts, settings.json wiring, skill/command/agent files, queue scaffolding,
state file) is fully determined by those answers and lives here. Keeping them
separate makes the mechanical half reproducible, diffable, and reversible —
properties an interactive wizard cannot offer.

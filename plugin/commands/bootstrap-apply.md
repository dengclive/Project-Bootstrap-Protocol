---
description: Apply bootstrap.config.yaml deterministically (creates the full .claude/ harness). Runs the installer; no interview.
---

# /bootstrap-apply

Run the **deterministic installer** against the `bootstrap.config.yaml` in the
project root. This is the mechanical layer — it makes no decisions, asks no
questions, and produces a byte-for-byte reproducible `.claude/` tree from the
config.

## What to do

1. Confirm `bootstrap.config.yaml` exists in the project root. If it does not,
   tell the operator to run `/bootstrap-interview` first (that command is the
   decision layer; it produces the config this command consumes).

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
   installer manifest the line names `--adopt`); and when the run would
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
   and adds one for each of the operator's own hook registrations that
   begin with an unquoted `$CLAUDE_PROJECT_DIR` in a project path that
   contains a space, tab, newline or glob character.

6. Report the create/update/unchanged/skipped counts. Remind the operator
   that local edits to generated files are preserved unless `--force` is
   passed, and that `--uninstall` cleanly reverses the install.

## Why this is split from the interview

The Bootstrap Protocol has two layers. The **interview** (archetype, PRD tier,
principles, secrets paths, TDD policy, MCP choices) genuinely needs a human and
lives in `/bootstrap-interview`. The **scaffolding** (hook scripts,
settings.json wiring, skill/command/agent files, queue scaffolding, state
file) is fully determined by those answers and lives here. Keeping them
separate makes the mechanical half reproducible, diffable, and reversible —
properties an interactive wizard cannot offer.

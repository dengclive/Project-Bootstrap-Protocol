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
   Surface any `_command_warnings` (empty test/lint/format commands produce
   loud TODO markers in the hooks).

4. On operator approval, apply:

   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/../bin/bootstrap-install
   ```

5. Report the create/update/unchanged/skipped counts. Remind the operator
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

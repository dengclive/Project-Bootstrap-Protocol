---
description: Conduct the Bootstrap Protocol interview and emit bootstrap.config.yaml (the decision layer; no files are scaffolded here).
---

# /bootstrap-interview

Conduct the **decision layer** of the Project Bootstrap Protocol. The only
output is a validated `bootstrap.config.yaml`. You do **not** create any
`.claude/` files here — that is `/bootstrap-apply`'s job, and keeping it
separate is what makes the scaffolding reproducible.

There is now a tool that does the mechanical part of this for you:
`bin/bootstrap-interview`. It reads a PRD and **proposes** a complete, valid
config with a written rationale for every non-obvious choice, for the operator
to review and edit. It proposes, never silently decides; it never guesses the
project's test/lint/format commands; and it validates its own output with
`bootstrap-install --print-config`.

## Preferred path: drive the tool

1. Confirm a PRD exists (ask the operator for its path; if there is none, the
   PRD must be written first — that is genuine human judgement the tool does
   not attempt).

2. Run the deterministic two-pass flow so the operator can review every
   proposed decision before anything is committed:

   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/../bin/bootstrap-interview analyze \
     --prd <PRD-PATH>
   ```

   This writes `bootstrap.interview.md` — proposals, rationale, confidence,
   and any **OPEN QUESTIONs** the PRD was too ambiguous to resolve. Walk the
   operator through it one decision at a time (do not batch). Pay special
   attention to OPEN QUESTIONs and to the HUMAN-REQUIRED commands block.

3. Help the operator edit the ANSWERS block (accept = leave unchanged;
   override = edit the value). Then:

   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/../bin/bootstrap-interview synthesize
   ```

   This emits `bootstrap.config.yaml` and validates it. If validation fails,
   resolve it with the operator and re-run — never hand off an invalid config.

   For an operator who prefers a live Q&A instead of editing a file, use
   `bootstrap-interview interactive --prd <PRD-PATH>` — same proposals, asked
   one question at a time over the terminal.

## Fallback: conduct it by hand

If the tool cannot run (no PRD, or the operator wants to drive every decision
conversationally), conduct the interview phases from `Bootstrap-Protocol-v2-0-0.md` that
produce *decisions* (not files):

- **Phase 0** — classify the project (archetype, shell, PRD tier, CI/CD
  opt-out) and capture the three autonomous-mode opt-in flags. Enforce the
  skip policy: queue mode requires loop or goal mode.
- **Phase 2.5 / 2.7** — dependency approved-list and secrets never-read paths.
- **Phase 4** — ranked principles, tiebreakers, TDD policy. Offer the
  archetype starter set; let the operator override.
- **Phase 2 / 5** — the project's test / lint / format / typecheck / CI
  commands. These cannot be guessed; if the operator does not know them yet,
  record empty strings and warn that the corresponding gates will fail loudly
  until filled.
- **Phase 6.5** — MCP servers to install and ones explicitly rejected (with
  reasons).

Ask one open-ended question at a time. Use multi-select for known option sets.
Do not batch. Show each section's resulting YAML fragment and confirm before
moving on.

## Output and validation

Whichever path was used, the config must validate:

```
python3 ${CLAUDE_PLUGIN_ROOT}/../bin/bootstrap-install --print-config
```

If validation reports errors, fix them with the operator before finishing.

## Handoff

Tell the operator the config is ready and that running `/bootstrap-apply`
will scaffold the entire harness deterministically — and that re-running it
later after editing the config converges the tree without clobbering their
local edits to generated files.

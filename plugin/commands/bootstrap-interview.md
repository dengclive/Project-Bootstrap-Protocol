---
description: Conduct the Bootstrap Protocol interview and emit bootstrap.config.yaml (the decision layer; no files are scaffolded here).
---

# /bootstrap-protocol:bootstrap-interview

Conduct the **decision layer** of the Project Bootstrap Protocol. The
output is a validated `bootstrap.config.yaml`, plus a PRD at
`docs/prd/<name>.md` when the operator doesn't have one at the required tier
yet. You do **not** create any `.claude/` files here — that is
`/bootstrap-protocol:bootstrap-apply`'s job, and keeping it separate is what
makes the scaffolding reproducible.

The protocol document is at `${CLAUDE_PLUGIN_ROOT}/toolchain/protocol.md`.
The phases and steps this command names are the phases and steps in it.

There is now a tool that does the mechanical part of this for you:
`bin/bootstrap-interview`. It reads a PRD and **proposes** a complete, valid
config with a written rationale for every non-obvious choice, for the operator
to review and edit. It proposes, never silently decides; it never guesses the
project's test/lint/format commands; and it validates its own output with
`bootstrap-install --print-config`.

## Preferred path: drive the tool

1. Get a PRD at the required tier. Ask the operator for its path, and read
   it. The tool reads a PRD but doesn't write one. You write it with the
   operator, as Phase 0 step 8 of the protocol says:

   - **No PRD**, because the operator has notes or just an idea: propose the
     archetype and its required PRD tier (Phase 0 steps 3 and 7). Run the
     PRD interview at that tier, write `docs/prd/<name>.md`, and get the
     operator's confirmation before you go on.
   - **A PRD below the required tier**: run a gap interview, and write the
     upgraded PRD to `docs/prd/<name>.md`.
   - **A PRD at the required tier**: go on to step 2.

   The protocol's Project Archetypes section lists each archetype's required
   tier and what each tier holds. Ask one question at a time. Don't batch.

2. Run the deterministic two-pass flow so the operator can review every
   proposed decision before anything is committed:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/toolchain/bin/bootstrap-interview" analyze \
     --prd <PRD-PATH>
   ```

   This writes `bootstrap.interview.md` — proposals, rationale, confidence,
   and any **OPEN QUESTIONs** the PRD was too ambiguous to resolve. Walk the
   operator through it one decision at a time (do not batch). Pay special
   attention to OPEN QUESTIONs and to the HUMAN-REQUIRED commands block.

3. Help the operator edit the ANSWERS block (accept = leave unchanged;
   override = edit the value). Then:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/toolchain/bin/bootstrap-interview" synthesize
   ```

   This emits `bootstrap.config.yaml` and validates it. If validation fails,
   resolve it with the operator and re-run — never hand off an invalid config.

   For an operator who prefers a live Q&A to editing a file, give them this
   command to run in a terminal of their own: the same proposals, asked one
   question at a time. Don't run it yourself: it reads the answers from the
   keyboard. With no terminal it refuses and writes no config, and input
   that ends early takes the proposed default for every later question and
   says so.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/toolchain/bin/bootstrap-interview" interactive --prd <PRD-PATH>
   ```

## Fallback: conduct it by hand

If the tool can't run, or the operator wants to drive every decision
conversationally, get the PRD as step 1 says, and then conduct these
interview phases of the protocol. They produce *decisions*, not files:

- **Phase 0** — classify the project (archetype, shell, PRD tier, CI/CD
  opt-out) and capture the three autonomous-mode opt-in flags. Enforce the
  skip policy: queue mode requires loop or goal mode.
- **Phase 2.5 / 2.7** — dependency approved-list and secrets never-read paths.
- **Phase 4** — ranked principles, tiebreakers, TDD policy. Offer the
  archetype starter set; let the operator override.
- **Phase 2 / 5** — the project's test / lint / format / typecheck / CI
  commands. These cannot be guessed; if the operator does not know them yet,
  record empty strings and say what that does until they are filled: an
  empty test command makes
  `test-gate` block every commit, an empty lint command means
  `format-lint-gate` checks nothing, and no hook runs format or typecheck.
- **Phase 6.5** — MCP servers to install, each with its `purpose` (what it
  is for), and ones explicitly rejected (with reasons).

Ask one open-ended question at a time. Use multi-select for known option sets.
Do not batch. Show each section's resulting YAML fragment and confirm before
moving on.

## Output and validation

Whichever path was used, the config must validate:

```
python3 "${CLAUDE_PLUGIN_ROOT}/toolchain/bin/bootstrap-install" --print-config
```

If validation reports errors, fix them with the operator before finishing.

## Handoff

Tell the operator the config is ready and that running
`/bootstrap-protocol:bootstrap-apply` will scaffold the entire harness
deterministically — and that re-running it later after editing the config
converges the tree without clobbering their local edits to generated files.

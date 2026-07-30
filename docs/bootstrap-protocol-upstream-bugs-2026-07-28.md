# Upstream bug report — Bootstrap Protocol v2.5.0

**Hand this file to the `Project-Bootstrap-Protocol` repository as the task brief.**

---

## Context for the receiving agent

You are working in `~/Documents/Projects/Project-Bootstrap-Protocol` (the
Bootstrap Protocol: a wizard + deterministic installer that configures Claude Code
harnesses). Everything below was found by a **6-lens adversarial review of a real
v2.5.0 install** — a greenfield `fullstack` project, all autonomous modes off,
design steering + telemetry on, `gate_substrate: "shell"`.

**Provenance discipline:** findings marked **CONFIRMED** were verified by
*executing* the emitted hooks with crafted payloads and observing exit codes, not
by reading. Findings marked **STATIC** were not executed. Reproduce before fixing —
and if a repro does not reproduce, say so rather than patching blind.

**Scope boundary — read this before starting.** The review also found ~40 defects
in *that project's own hand-authored steering documents*. Those are **not** your
problem and are already fixed downstream. Everything in this file is a defect in
**protocol-owned emitted artifacts** (`lib/templates.py`, `lib/sdk_gates_template.py`,
`lib/installer.py`) or in the **normative protocol document**.

**The install under review had `jq` present**, so the jq-less fallback path was
exercised only by deliberately stripping `PATH`. Findings 7 and 8 concern that path.

---

## Priority 0 — Security

### P0-1. Arbitrary command execution via the drift-state file — **CONFIRMED**

**Where:** emitted `.claude/hooks/drift-detector.sh`, the counter increment
(template source in `lib/templates.py`, `_hook_body`, `drift-detector` branch):

```bash
n=$(( $(cat "$ST" 2>/dev/null || echo 0) + 1 ))
```

**Why it is exploitable.** Bash performs command substitution *inside arithmetic
evaluation*, including within array subscripts. The state file
`.claude/sessions/.drift-state-<sid>` is gitignored and writable by any ordinary
`Write` tool call.

**Repro (confirmed):** write `PATH[$(touch /tmp/PWNED)]` into
`.claude/sessions/.drift-state-default`, then trigger any PostToolUse event.
`touch` executes. *(`a[$(...)]` alone is stopped by `set -u`; any **already-set**
variable name such as `PATH` works.)*

**Why it matters structurally:** this is a clean path from "the agent writes a
file" — an operation no gate blocks — to "arbitrary command executes", bypassing
every `PreToolUse` `Bash` gate in the suite. The harness's entire threat model
assumes command execution is gated.

**Fix:**
```bash
n=$(cat "$ST" 2>/dev/null || echo 0)
case "$n" in ''|*[!0-9]*) n=0 ;; esac
n=$((n + 1))
```

**Audit obligation:** grep every emitted hook for `$(( ... $(cat ...) ... ))` and
any other arithmetic over unvalidated file or JSON input. Fix the class, not the
instance.

### P0-2. `secrets-gate` is not wired to `Bash` — **CONFIRMED**

**Where:** emitted `.claude/settings.json` — `secrets-gate` is registered only
under the `"Read|Write|Edit"` matcher. The `Bash` matcher block contains no
secrets check.

**Consequence:** every never-read path is readable via a shell command.
`cat .env`, `grep -r . secrets/`, `base64 id_rsa`, `git diff -- '*.pem'` are all
unguarded. `Grep`, `Glob`, and `WebFetch(file://)` are likewise unmatched. The
policy constrains one access route out of several, while `secrets.md` tells the
operator these paths are blocked.

**Fix:** add a command-scanning secrets check to the `Bash` matcher. Note the hook
currently reads only `.tool_input.file_path`, so the Bash-side check needs new
logic (scan the command string for never-read patterns). Recommend additionally
emitting a `permissions.deny` list as defence in depth.

### P0-3. Parsing gates fail **open** under three conditions — **CONFIRMED**

All three make a *security* gate silently allow.

**(a) jq-less payloads >128 KiB.** The shared `jget` fallback passes the entire
stdin JSON to python through an environment variable
(`INPUT="$INPUT" python3 - ...`). Linux caps a single env var at 128 KiB; beyond
it, exec fails with `Argument list too long` (rc 126) and `|| true` swallows it.
Confirmed: with `jq` removed from `PATH`, a `Write` payload of
`{"file_path":"/h/.env","content":"A"*3000000}` → **exit 0 (allowed)**; the same
payload with `jq` present → exit 2 (blocked). A large `Write` to `.env` is
precisely the case that matters.

*Note:* the header comment credits env-passing as the fix for an earlier
already-consumed-stdin bug. It traded one silent failure for another. Pass via a
temp file or a dedicated fd instead.

**(b) Neither `jq` nor `python3` on PATH.** Both branches end in `|| true`, so
`jget` returns empty and every gate's `case` falls through. Confirmed: exit 0, no
message.
**Fix:** if no parser is available, `exit 2` with a loud reason. A security
substrate must never degrade to allow.

**(c) Environment failures exit 1 instead of 2.** `secrets-gate`'s `mkdir -p` of
the log directory and its `mktemp` both die under `set -e`, yielding exit 1 =
"hook error, tool proceeds". Confirmed: with an unwritable `CLAUDE_PROJECT_DIR`, a
read of `/h/.env` returns exit 1 — the read the gate exists to stop.
**Fix:** `trap 'exit 2' ERR` in `secrets-gate`, or make logging non-fatal and
inline the pattern list as a bash array rather than a temp file.

---

## Priority 1 — Gates that do not do what the operator is told they do

### P1-1. `async: true` makes `exit 2` a no-op — the gates are dead — **CONFIRMED**

**Where:** emitted `.claude/settings.json` marks `test-gate`, `ci-mirror`, and
`format-lint-gate` as `"async": true`. **An async hook's exit code cannot block a
tool call.**

**Confirmed:** a Bash call whose command text contained `git push` caused
`ci-mirror` to fire and take its `exit 2` path (no `ci-mirror ok` line in
`hooks.log`) — **and the tool call completed and returned output**. In the same
session the *synchronous* `dependency-gate` demonstrably blocked a real call,
proving exit 2 works and the async flag is the sole cause. Async hook stderr is
also suppressed by default, so the block is **silent**.

**Consequence:** the emitted `test-gate.sh` prints `Commit blocked: tests failing.`
and nothing is blocked. The protocol's per-task lifecycle presents "implementation
passes local gates" as gate 5 of 6. For `test-gate` and `ci-mirror`, that gate does
not exist.

**This is also a defect in the normative document**, not only the emission: the
protocol text recommending `async: true` for the CI mirror (≈ line 534 of
`Bootstrap-Protocol-v2-5-0.md`) is self-contradictory — a hook that exits 2 to
block cannot be async.

**Fix:** remove `async` from `test-gate` and `ci-mirror`; give them explicit
`"timeout"` values instead (e.g. 600 s / 900 s). **Fix P1-3 first** — making these
synchronous while they still substring-match turns a silent annoyance into a
multi-minute stall on innocuous commands. `format-lint-gate` is PostToolUse and
advisory by design; async is arguably correct there, but see P2-6.

### P1-2. `spec-gate-commit` blocks every possible first commit — **CONFIRMED**

**Predicate (determined empirically):** a staged path passes only if its full path
**or** its bare basename appears literally in `.claude/specs/INDEX.md` or a
`.claude/specs/*/tasks/*` file, preceded by a character outside
`[[:alnum:]_./-]` and followed by one outside `[[:alnum:]_-]`. Because the leading
boundary class excludes `/`, **a basename mentioned as part of a longer path never
matches by basename.**

**Confirmed blocked (exit 2):** `src/engine.gleam`, `gleam.toml`, `README.md`,
`.claude/specs/INDEX.md` *(the gate blocks its own index)*, and
`progress-template.md` *(even though `INDEX.md` contains
`` `.claude/specs/progress-template.md` `` — the path-prefix boundary defeats it)*.

**Two distinct failures:**
1. **The bootstrap commit itself is impossible.** Harness files can never be
   referenced by a spec — they *are* the spec infrastructure. Every adopting
   project hits this on its very first commit.
2. **The first *code* commit is impossible.** `spec-decompose` deliberately
   produces tasks and behaviors, not filenames, so no `.gleam` path is ever in the
   corpus. Passing requires transcribing every filename into `tasks/*.md`, which
   is both busywork and a corpus-polluting incentive.

**Plus two implementation bugs:**
- **Unescaped ERE interpolation.** Filenames are interpolated into
  `grep -rqE "...($f|$b)..."`. Confirmed: `src/a+b.gleam`, listed *verbatim* in a
  task file, was reported unreferenced because `+` is a quantifier. Any path with
  `+ ( ) [ ] { } ?` false-blocks. **Fix:** `grep -qF` with a manual boundary check,
  or escape the pattern. *(`lib/sdk_gates_template.py` uses `re.escape` and is
  correct — the shell and SDK disagree here.)*
- **Unquoted `$corpus`.** It is a space-joined string. Confirmed: a spec directory
  named `my spec` word-splits and blocks a file that *is* referenced. Spec slugs
  come from `/spec-new`, so an operator-typed name with a space bricks all commits.
  **Fix:** collect into a bash array; pass `"${corpus[@]}"`.

**Design question for the maintainer, not just a patch:** what should this gate's
predicate actually be? The error text says "Run `/spec-new`", implying it means to
police *implementation* files. Scoping it to `src/` and `test/` (configurable)
would preserve the intent and eliminate both structural failures.

### P1-3. `dependency-gate`: fails open on real installs, fires on prose — **CONFIRMED**

**Fails open** (each confirmed exit 0):
- **`gleam add <anything>`** — and `cargo add`, `mix deps.get`, `rebar3 get-deps`,
  `pipx install`, `curl … | sh`. Only npm/pip/yarn/pnpm verbs are matched. For a
  Gleam project this means the gate guards ecosystems the project does not use and
  ignores the one it does.
- **Scoped npm packages.** `name_only="${tok%%[<>=@~ ]*}"` blanks `@evil/backdoor`
  because `@` is the *first* character, and the empty-guard then `continue`s.
  `npm install @evil/backdoor` → exit 0. *(`lib/sdk_gates_template.py`'s
  `_pkg_name` handles this correctly — another shell/SDK divergence.)*
- **Token laundering.** The three strips are applied unconditionally in sequence:
  ```bash
  rest="${CMD#*install }"; rest="${rest#*add }"; rest="${rest#*i }"
  ```
  `pip install pytest-mpi gleeunit` → exit 0: the `i ` in `pytest-mpi ` truncates
  `rest` to the approved `gleeunit`, and `pytest-mpi` is never inspected. **Any**
  unapproved package can be laundered by appending an approved one after a token
  ending in `i`. **Fix:** select the strip by which verb matched; never chain.
- **Whitespace.** `npm  install evil` (two spaces) and tab separators → exit 0.
- **`-r requirements.txt`** — the flag-skip consumes the filename, then nothing is
  checked.

**False positives** (each confirmed exit 2 on legitimate work):
- **Bare `npm install`** and **`cd sidecar && npm install`** — routine lockfile
  restore — blocked, and the "package" is reported as `npm install`.
- **Any command merely mentioning an install phrase**: `grep -r "npm install" docs/`,
  `echo`, `printf` into a docs file. This blocked the *reviewing agent's own tool
  call* mid-review because its harness text contained the string; the review had to
  be rewritten with concatenated verbs to proceed.
- **Unquoted `$rest`** word-splits *and* glob-expands against the cwd: `pip install *`
  reported `not in deps.md approved list: src`. A crafted filename could turn an
  over-match into an under-match. **Fix:** `set -f`, or `read -ra` into an array.

### P1-4. Command matching is substring-based across four gates — **CONFIRMED**

`spec-gate-commit`, `test-gate`, `ci-mirror`, and `dependency-gate` all match a
fixed-spacing literal substring of the command.

| command | exit |
|---|---|
| `git commit -m x` | 2 (blocked) |
| `git  commit -m x` *(two spaces)* | **0** |
| `git\tcommit -m x` | **0** |
| `git --no-pager commit -m x` | **0** |
| `git -C /repo commit -m x` | **0** |

**Refuted as bypasses** (still blocked — substring matching catches them):
`env git commit`, `sh -c "git commit"`, heredocs, `git add . && git commit`,
`true; git commit`.

Conversely, `git commit`/`git push` appearing **anywhere** — including inside a
shell comment, a quoted string, or a `grep` pattern — triggers the gate. Confirmed:
the probe `true # probe2 git commit and git push in one command` fired both.
Once a toolchain is installed that means a full `build && test` on innocuous
commands. Combined with P1-1's fix this becomes a multi-minute stall — **the
archetypal "operator disables the gate" trainer.**

**Fix:** normalize whitespace (`tr -s '[:space:]' ' '`) and anchor to command
position, e.g. `(^|[;&|]) *(env +)?git( +-[^ ]+| +-C +[^ ]+)* +commit`.
`lib/sdk_gates_template.py`'s `"git commit" not in cmd` has the identical
weakness — the two substrates agree only in being wrong.

---

## Priority 2 — Correctness and self-consistency

### P2-1. `gates.py` and the shell suite return opposite verdicts — **CONFIRMED**
Driving the SDK closures directly with a stubbed `claude_agent_sdk`, five
dependency cases the shell **allows** the SDK **denies** (`npm  install evil`,
`npm install @evil/backdoor`, `pip install pytest-mpi gleeunit`, `pipx install`,
tab-separated). Worse for commits: `gates.py` gives `test-gate` a 600 s timeout on
a **synchronous** PreToolUse hook, so with the project's test command unavailable
the SDK path denies **every** commit while the shell path (async) denies none.
Whichever substrate is live changes project behavior completely.
**This needs a decision, not just a patch:** which substrate is canonical, and
should the emitted pair be required to agree? At minimum, port the SDK's verb/token
logic back into the shell so the shell is a weaker-but-consistent subset.

### P2-2. `gates.py` claims parity it does not have — **STATIC**
Its docstring says "parity with the installed shell suite". It carries 5 gates; the
shell suite has 11. `ci-mirror` is absent entirely (so `git push` is ungated under
SDK dispatch), along with `drift-detector`, `cost-log`, both alarms, and
`spec-gate-entry`. Either implement parity or correct the claim.

### P2-3. `sdk_gates/gates.py` is emitted but referenced by nothing — **CONFIRMED**
`grep -c sdk_gates .claude/settings.json` → 0. On a `gate_substrate: "shell"`
install it enforces nothing. That may be intended, but it is not stated, and a
reader reasonably assumes an emitted gate module is live. Document the condition
under which it becomes active.

### P2-4. `secrets-gate` over- and under-matches — **CONFIRMED**
- **Over:** patterns get an implicit leading `*`, so `.env*` becomes `*.env*`.
  `src/my.envelope.gleam` → exit 2; `docs/dev.environment.md` → exit 2;
  `src/grid_rsa.gleam` → exit 2; `docs/no-secrets/plan.md` → exit 2. Deny-list
  over-match is the right *bias*, but a hard block mid-plan with no override path
  is exactly what gets `secrets-gate` deleted. **Fix:** anchor the `.env*` family
  to a path-segment boundary (`*/.env*`); keep the implicit `*` for extension
  patterns (`*.pem`, `*.key`).
- **Under:** `~/.aws/credentials`, `~/.netrc`, `~/.git-credentials`,
  `credentials.json`, `docker-compose.prod.yml` → exit 0. No project-boundary or
  traversal check (`../../etc/passwd`, `/etc/shadow` → exit 0). And **file
  *content* is never inspected** — a `Write` whose body is a secret passes.
- **`NotebookEdit`** is matched by the `Read|Write|Edit` substring but supplies
  `notebook_path`, which the hook never reads → exit 0, logged "no path". A gate
  that reports success while checking nothing.

### P2-5. `test-gate` fails open permanently, and reports a false cause — **CONFIRMED**
- `find src -type f -newer "$MARK"` uses a **relative** path while `MARK` uses
  `$PROJ`. In a project with no `src/` (or when the hook's cwd differs), `find`
  fails silently → once `.claude/.last-test-pass` exists, **every commit passes
  with no test run, forever**.
- `test/` is never watched, so editing only tests never invalidates the marker.
- With the test command unavailable it prints `Commit blocked: tests failing.`
  Tests are not failing; the toolchain is missing. Distinguish 127 from a real
  failure.
- `gates.py` additionally checks `lib/` where the shell does not — a third
  divergence.

### P2-6. `format-lint-gate` runs a **mutating** formatter — **CONFIRMED**
It invokes the configured `format` command (not `format --check`) after **every**
`Write|Edit`, with no file-type filter (it runs on `.md` too). On a project whose
`commands.format` is `gleam format`, that reformats files the agent never touched,
project-wide, on every edit — and because it is async its output may never reach
the model. Use the **lint/check** command here, or scope it to the edited path.

### P2-7. The drift counter never resets and is keyed wrong — **CONFIRMED**
The emitted hook derives the session id from `CLAUDE_SESSION_ID`, which **Claude
Code does not export** — the session id arrives in the stdin JSON as `.session_id`.
The live state file was therefore `.drift-state-default`: a single counter shared
by **all sessions, forever**. It stood at 274 against a threshold of 50, so the
tier-1 notice fires on every tool call permanently — and since PostToolUse stderr
on exit 0 is not surfaced, it is simultaneously permanent noise and invisible. The
drift detector, a headline feature, currently carries no signal.
**Fix:** read `.session_id` from the payload, falling back to the env var; implement
the `purge_old_state_after_days` policy that `audio-alerts.config` advertises.

### P2-8. `spec-gate-entry` is dead code — **CONFIRMED**
Its warning is guarded by `[ ! -s "$INDEX" ]`, but `INDEX.md` is always emitted
non-empty, so the condition can never be true. The gate never fires.

---

## Priority 3 — Disclosure accuracy

- **`audio-alerts.config` sets `audio_enabled=true`, but no emitted hook invokes any
  audio player** (`grep -lEi 'paplay|aplay|afplay|ffplay|mpv|sox'` over the hooks →
  no matches). `drift-detector.sh` assigns `CFG` and never reads it, so editing
  `drift_tool_call_threshold` has no effect. The file's header is honest about the
  limitation; the `=true` value and the tunables are not. **CONFIRMED**
- **`cost-log.jsonl` records no cost** — entries are `{"event":"session_end","ts":…}`.
  Either record cost or rename the artifact. **CONFIRMED**
- **`.decision-pending-<sid>` is created and never cleared** by any emitted hook.
  **CONFIRMED**
- **`hooks.log` has no rotation or size cap**, and `secrets-gate` logs absolute
  paths (including paths outside the project) on both allow and block. No content or
  credential values are logged, and it is gitignored — so this is a disclosure gap,
  not a leak. Implement the advertised 7-day purge. **CONFIRMED**
- **jq `//` treats `false` as absent; the python fallback does not.** No current hook
  is affected (both fail the `= "true"` test), but the fallback is not the identity
  the header claims, and the next boolean guard added will diverge. **STATIC**

---

## What "fixed" must mean — acceptance criteria

1. **Every P0 and P1 finding has a regression test**, and the test **fails before
   the fix**. Note these are a *new test class* for this repo: the existing suite
   largely asserts **emission determinism** (does the installer write the expected
   bytes), which cannot catch any bug in this report. What is needed is
   **behavioral** testing — pipe a crafted payload into the emitted hook, assert the
   exit code. A `test_hook_behavior.py` that runs the emitted hooks against a payload
   matrix would have caught most of this file.
2. **Golden fixtures regenerate**, and the diff is reviewed rather than accepted
   wholesale — several fixes change emitted hook bodies and `settings.json`.
3. **The normative document is fixed too, not only the emission** — at minimum the
   `async: true` recommendation (P1-1), which is wrong in the protocol text itself.
4. **The shell suite and `gates.py` are reconciled**, or their divergence is
   documented as deliberate with a stated rule for which is authoritative.
5. **Version classification is decided explicitly.** Removing `async` changes gate
   *behavior*, not just emitted bytes — decide whether that is PATCH, MINOR, or a
   seam event under this repo's own rules, and record the reasoning. There is
   precedent for emitted-artifact fixes landing as a freeze-exception (`fb06ee2`,
   v2.5.0's F1/F2/F3), but none of those changed whether a gate blocks.
6. **A tagged release.** Downstream consumers pin annotated tags; `main` is not a
   release.
7. **Recommended:** re-run the two executing lenses (hook security, gate behavior)
   against a fresh install of the fixed version before tagging. Static review of
   these same files found neither P0-1 nor P1-1.

## Suggested sequencing

**P0-1 alone may warrant an immediate patch release** ahead of the rest — it is an
RCE in a tagged, publicly consumable artifact, and its fix is three lines with no
behavioral surface.

Then, in order: **P1-3 and P1-4 before P1-1.** Making `test-gate` and `ci-mirror`
synchronous while they still substring-match would convert a silent no-op into a
multi-minute stall on innocuous commands — a worse operator experience than the bug,
and the fastest route to someone disabling the suite entirely.

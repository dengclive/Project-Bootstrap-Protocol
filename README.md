# Bootstrap Protocol — Deterministic Installer + Plugin

This answers the question: *"Can BOOTSTRAP.md be a Claude Code plugin, or
deterministic code that configures Claude Code with all the hooks, commands,
etc.?"*

**Both — but they do different jobs, and the split is the whole point.**

## The two layers

`BOOTSTRAP.md` mixes two fundamentally different things:

| Layer | Examples | Can it be deterministic? |
|---|---|---|
| **Decisions** | archetype, PRD tier, principles & ranking, secrets paths, TDD policy, MCP choices, autonomous-mode opt-ins | **No** — needs a human. This is an interview. |
| **Scaffolding** | hook scripts, `settings.json` wiring, skill/command/agent files, queue scaffolding, `.gitignore`, state file | **Yes — 100%.** Pure function of the decisions. |

A plugin alone can't conduct the interview (plugins package static assets;
they don't branch on archetype). A single deterministic script can't *make*
the decisions. So the right design **separates them**:

```
/bootstrap-interview   ──>   bootstrap.config.yaml   ──>   bootstrap-install
   (decision layer,            (the frozen,                 (mechanical layer,
    needs a human)              reproducible input)          deterministic)
```

The interview's only output is a config file. The installer turns that config
into the entire `.claude/` tree — every *content* file byte-for-byte
reproducible (see Properties below for the metadata caveat).

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
BOOTSTRAP.md Project Archetypes table and PRD-tier definitions, and it reuses
the archetype principle starter sets from `lib/defaults.py` verbatim
(`PRINCIPLE_STARTERS` is imported, not re-listed) — the interview only proposes
*deltas* from those defaults. It **never guesses** `commands.test/lint/format`
(a PRD does not contain them); they are emitted empty and flagged
HUMAN-REQUIRED, consistent with the installer's loud-failing TODO gates. Every
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
  core, honoring BOOTSTRAP.md's "show before writing" and "one open-ended
  question at a time": each prompt shows the proposal and rationale, Enter
  accepts it, nothing is written until the config validates. This front-end is
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
    plugin.json
    commands/bootstrap-interview.md
    commands/bootstrap-apply.md
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
  digests) and skipped, not clobbered. `--force` overrides.
- **Reversible** — `--uninstall` removes exactly what it created.
- **Inspectable** — `--dry-run` prints the full plan; nothing is written blind.
- **Faithful to BOOTSTRAP.md** — encodes the skip-policy invariants
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

As a Claude Code plugin: install `plugin/`, then run `/bootstrap-interview`
(produces the config interactively) followed by `/bootstrap-apply` (runs the
deterministic installer).

## Honest limitations

- The wizard's *judgement* (good principles, sensible secrets globs, the right
  MCP set) still needs a human. `bootstrap-interview` automates eliciting and
  recording the decisions and proposes defaults with rationale, but it is a
  *proposer*: a human reviews and edits every draft before it is used. It does
  not replace the interview's judgement.
- `commands.test/lint/format` cannot be guessed — a PRD does not contain them.
  The interview leaves them empty and flags them HUMAN-REQUIRED; if left empty
  the installer emits gates that **fail loudly** with a TODO rather than
  silently passing — by design.
- `auto.sh` is scaffolded as a guarded skeleton. The full Phase 9.7 dispatch
  loop is intentionally left for the operator to complete before unattended
  use, matching BOOTSTRAP.md's own trust-ramp guidance.
- The emitted skill/command/agent bodies are faithful stubs (frontmatter +
  intent). They are correct and load, but the deep prompt engineering for
  each skill is a separate effort from the structural scaffolding.

## Tests

```bash
python3 tests/test_installer.py     # 34 passed, 0 failed
python3 tests/test_interview.py     # 46 passed, 0 failed
```

## Review history

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

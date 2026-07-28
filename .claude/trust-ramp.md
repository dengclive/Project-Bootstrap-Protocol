# Trust ramp — graded autonomy for work on this repository

<!-- STATE -->
current_rung: R0
rung_entered: 2026-07-28
attestations:
<!-- /STATE -->

Managed by `bin/trust-ramp`. Committed. **Not protocol surface** — this governs
how much autonomy the agent is granted *on this repo*; it emits nothing, is not
imported by `lib/`, and does not appear in any installer plan or golden digest.

## Why this exists

`Bootstrap-Protocol-v2-5-0.md` ships the trust-ramp posture in prose and repeats
it in four places (PRD §9.5/§9.6/§9.7, the Companion, the Phase 0 opt-in
surfacing, the Phase 10 handoff). What it does not ship is any mechanism that

- records where an operator actually is on the ramp,
- refuses a promotion that the evidence has not earned,
- covers the supervised rung at the bottom — the ramp's prose begins at "before
  trusting loop mode", so rung zero is unnamed and unmeasured, or
- moves backwards. The protocol has three ramps and no reverse gear.

The one artifact that comes close — `learnings/mode-selection.md`, the
calibration ledger — is emitted **only by the retrofit overlay**
(`lib/installer.py:477`), despite PRD §9.6 step 10, that phase's exit criteria,
and the Phase 0.5 preview all requiring it for greenfield goal-mode installs.
Tracked as backlog **I-15**. This repo has no install of its own regardless.

## What the rungs unlock

The rungs bind to **Claude Code's own autonomy surface**, not to the protocol's
`.claude/loop.sh` wrappers — there is no install here to enable. The thresholds
below are still the protocol's; only the thing being unlocked differs.

| Rung | Autonomy granted | What still requires a human |
|---|---|---|
| **R0** | Supervised per-task | Plan approved before work starts; diff reviewed before every commit |
| **R1** | `/loop` with a fixed prompt — unattended iteration on one scoped task | Diff reviewed before merge; the loop's stopping decision reviewed |
| **R2** | `/loop` plus a goal condition the agent self-checks each iteration | Diff reviewed before merge; goal-condition wording reviewed periodically |
| **R3** | Scheduled / queue-shaped runs across multiple tasks | Morning-after review of every run, cumulative-diff review across tasks |

Note what does **not** change across the rungs: the diff is reviewed by a human
before it merges, at every rung. Per PRD §10 — *"adding more autonomy means
investing in better review surfaces, not skipping review."*

## Gates

Thresholds take the top of each band the protocol states, so the gate is the
conservative reading of its own guidance.

| Transition | Gate | Protocol source |
|---|---|---|
| R0 → R1 | 10 tasks logged at R0 · 8 consecutive clean · no harmful in trailing 10 | §9.5 "5–10 tasks" |
| R1 → R2 | 20 tasks at R1 · 15 consecutive clean · no harmful in trailing 20 · attestation `goal-condition-review` | §9.6 "10–20 tasks" |
| R2 → R3 | 20 tasks at R2 · 15 consecutive clean · no harmful in trailing 20 · 28 days at R2 · attestation `subramp-9-7` | §9.7 "~4 weeks" + week-by-week sub-ramp |

Two rules are what make this graded rather than a counter:

- **A blank `**Outcome:**` is a hard parse error**, not a skipped entry. Without
  it the ramp would measure logging diligence rather than evidence.
- **Demotion is automatic.** A `harmful` outcome drops one rung and resets
  `rung_entered`, so the trailing window is re-earned rather than aged out.

`bin/trust-ramp check` re-derives the declared rung from the logged entries, so
promoting by hand-editing the state block above fails loudly.

## Outcome vocabulary

| Value | Meaning |
|---|---|
| `clean` | Landed as intended. Normal review only — no course correction. |
| `corrected` | The operator had to correct course, but nothing wrong reached the tree. Resets the clean streak; does not demote. |
| `harmful` | Something wrong got past review, **or** the operator intervened to prevent it. Demotes one rung. |

**Known limitation:** these are operator-self-reported. The ledger gates against
forgetting and against drift, not against an operator who writes `clean` ten
times. Nothing available in this repo can do better without executing the
emitted artifacts — which is the same coverage hole that blocks the v2.5.0 tag.

## Usage

```
bin/trust-ramp status
bin/trust-ramp log --task ds-02-review --outcome clean --notes "…"
bin/trust-ramp attest goal-condition-review
bin/trust-ramp promote
bin/trust-ramp check --rung R2     # exit 1 if R2 is not earned
```

## Ledger

Append-only; `bin/trust-ramp log` writes these. Unknown `**Field:**` lines are
preserved rather than rejected, so if this repo ever self-installs, the
protocol's own `learnings/mode-selection.md` block (`Recommendation:` /
`Chosen:` / `Felt right?:`) merges in without a format change.

<!-- entries below -->

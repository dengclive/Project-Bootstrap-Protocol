# Validation — v2.5.0 design-steering redline against the real v2.4.0 implementation

**Run:** 2026-07-21, against `Project-Bootstrap-Protocol-main.zip` (the actual
engine: `lib/`, `bin/`, `plugin/`, `tests/`).
**Validated:** the applied v2.5.0 doc edits (protocol §§1–8, Companion §9) — are
they *implementable* against this code, and does the doc's model match the code's
reality?

**Verdict:** the feature is implementable as a clean additive opt-in, modelled
exactly on the `telemetry_export_enabled` (TEL-01) precedent, which is wired
end-to-end in this codebase and is the correct template. **Two doc-vs-code
mismatches must be reconciled in the implementation** (neither is a doc bug that
needs re-editing; both are places where the code is more specific than the doc,
and the implementation must follow the code). One test-harness fact
(golden-digest determinism) is the load-bearing correctness gate.

---

## 1 · The precedent is real and complete — copy it exactly

`telemetry_export_enabled` is wired through four layers. Every design-steering
change has a line-anchored sibling to model on:

| Layer | File | Telemetry anchor | What design steering needs |
|---|---|---|---|
| Interview key list | `lib/interview.py:64` | `"telemetry_export_enabled"` in `_KEYS` | add `"design_steering_enabled"` |
| Interview default | `lib/interview.py:164` | `"telemetry_export_enabled": False` | add `"design_steering_enabled": False` |
| answers→config | `lib/interview.py:201–204` | top-level bool, NOT nested | same top-level placement |
| ANSWERS fail-loud | `lib/interview.py:530–540` | section-marker discriminated missing-key error | same pattern, new marker |
| Interactive prompt | `lib/interview.py:721–737` | `show(...)` + `_ask(...)` | new `show()` — **but conditional on archetype** |
| Normalizer | `lib/installer.py:62–82` | `telemetry_enabled(cfg)` fail-loud bool | add `design_steering_enabled(cfg)` twin |
| build_plan gate | `lib/installer.py:132–133` | `if telemetry_enabled(cfg): add(...telemetry.md...)` | `if design_steering_enabled(cfg): add(...design.md...)` + optional skill/command |
| State write | `lib/installer.py:891` | `"telemetry_export_enabled": telemetry_enabled(cfg)` | add twin, same normalizer |
| Template body | `lib/templates.py:361–379` | `_telemetry(cfg)` frozen body, fail-loud | add `_design(cfg)` |
| TEMPLATES registry | `lib/templates.py:3170–3171` | `"telemetry": _telemetry` | add `"design": _design` (+ skill/command entries) |
| Tests | `tests/test_installer.py:720–830` | on/off/determinism/state | mirror block for design |

Because the emission gate is flag-driven and lands in `.claude/steering/`
(committed by construction, no gitignore edit — `installer.py:127`), the
off-by-default plan stays byte-identical to the pre-feature baseline. This is the
mechanical guarantee the redline's "seam impact: none" claim rests on, and the
code makes it true.

---

## 2 · Mismatch A — `platform` is a first-class archetype in code, not a synthetic-profile case

**The redline says** (protocol §6, and the note under it): *"Phase 2's list has
no Platform bullet … route Platform + Other through the synthetic profile."* That
is true of the **document's** Phase 2 prose.

**The code says otherwise.** `lib/defaults.py:16–17`:

```python
"cli", "library", "service", "fullstack", "mobile",
"data-ml", "ai-agent", "platform", "other",
```

`platform` is a validated enum value (`defaults.py:252–255` raises on anything
outside `ARCHETYPES`). So at implementation time there is **no synthetic-profile
indirection to hang Platform on** — the interview has a concrete `archetype ==
"platform"` branch available.

**Reconciliation (implementation follows code):** the offer-gate is an explicit
user-facing set, not a "has-a-bullet" test:

```python
_DESIGN_OFFER_ARCHETYPES = {"fullstack", "mobile", "ai-agent", "platform", "other"}
# excluded (non-user-facing): "cli", "library", "service", "data-ml"
```

The doc's synthetic-profile framing for "Other" still holds (Other genuinely uses
the synthetic profile), but Platform is offered **directly** on its enum value.
This does not require a doc re-edit — the doc's §6 note already says the design
line "attaches to Full-stack/Mobile/AI directly and to Platform+Other through the
Other clause"; the code simply lets Platform attach directly too, which is
strictly cleaner. Note this as an intended doc/code divergence in the fold record.

**Open question for the implementer** (flag, don't guess): is a headless
`service` ever user-facing enough to offer design steering (admin panel / docs
site)? The redline's interview wording says a *headless* Service/API does **not**
get asked. Recommend: keep `service` out of the auto-offer set; if a service has
a UI the operator re-runs the wizard or picks `fullstack`/`platform`. Do not
silently include `service`.

---

## 3 · Mismatch B — the conditional offer is the one genuinely new mechanism

Telemetry is offered **unconditionally** (archetype-independent — `interview.py`
asks every project). Design steering is offered **only for user-facing
archetypes**. That archetype-gated *offer* has **no existing precedent to copy**
and is therefore the highest-risk part of the change:

- The interactive `show()`/`_ask()` block (modelled on `interview.py:721–737`)
  must be wrapped in `if ans["archetype"] in _DESIGN_OFFER_ARCHETYPES:`.
- For excluded archetypes the flag must be **recorded `false` without prompting**
  (interview stays short) — this is the "don't surface a decision that can't
  apply" rule from `INTERVIEW-WORDING.md`.
- The **non-interactive** path (ANSWERS block / synthesized interview) must still
  accept `design_steering_enabled: true` even for a non-user-facing archetype if
  an operator hand-sets it — the *offer* is gated, the *flag* is not. Do not add
  archetype validation that rejects the flag; only the interactive prompt is
  gated. (This mirrors how telemetry's ANSWERS path is archetype-blind.)

This asymmetry (gated offer, ungated flag) is subtle and is exactly where a
reviewer should push hardest.

---

## 4 · The load-bearing correctness gate — golden determinism

`tests/test_greenfield_golden.py` locks `build_plan` output to per-file digests
and **fails first** on any byte change to greenfield output. Because design
steering is off by default:

- **The existing golden digests MUST NOT change.** If they do, the feature is not
  truly additive/off-by-default — it leaked into the default plan. This is the
  single strongest proof the "seam impact: none" claim holds in code.
- A **new flag-on fixture** gets its own new digests (a deliberate golden
  addition, per the file's `GOLDEN_UPDATE=1` protocol), asserting design.md (and,
  when the skill is accepted, the skill + command stub) emit exactly once.

Any implementation that changes the default-path digest is wrong regardless of
what else it does right.

---

## 5 · Other code facts that touch this change

- **`data-ml` gets no design line** — confirmed correct against both doc and code
  (it's in the excluded set). The redline's Data/ML trap survives into code.
- **Emission determinism (TAR-01 discipline):** `_telemetry` stamps values from
  state/config at emission, never static literals (`templates.py:361–379` fails
  loud on a missing value). `_design`'s body is mostly static invariants +
  honest-use prose; the **only** emission-time variable is the operator-filled
  Project-specifics block, which should be emitted as an explicit HUMAN-REQUIRED
  placeholder (mirror the `commands_*` empty-string→TODO-marker contract at
  `interview.py:166–170`), not guessed.
- **Filename-literal ripple in code:** `grep -rn "Companion-v2-4-0\|Protocol-v2-4-0"
  lib/ bin/ tests/ plugin/` returns **zero** — the engine does not embed the doc
  filenames, so the doc-rename ripple (25 sites in the two docs) has **no code
  counterpart**. The version on the wire comes from `bootstrap_protocol_version`
  in state, stamped at emission (TAR-01), so bumping the protocol version string
  is a config/state concern, not a literal in `templates.py`. Confirm the version
  constant (wherever `2.4.0` is the current-version default) is bumped to `2.5.0`
  — see the implementation prompt's step on `defaults.py` / config version.
- **The `design-review` skill is a skill, not a hook.** `templates.py:278–589`
  (`_hook_body`) is the hook dispatch; the skill must NOT be added there. Skills
  are emitted separately; the skill flags and never blocks (Path C rejected). A
  reviewer should confirm no `_hook_body` entry, no `settings.json` hook wiring,
  and no `PreToolUse`/`PostToolUse` registration for design-review.

---

## 6 · Bottom line for the implementation

The redline is faithfully implementable. Follow the code where it's more specific
than the doc (Platform is a real archetype; the offer is archetype-gated but the
flag is not). Prove off-by-default with the golden test. The only net-new logic is
the archetype-gated offer helper; everything else is a line-for-line TEL-01 twin.

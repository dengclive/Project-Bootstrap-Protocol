# Implementation Prompt — Bootstrap Protocol v2.5.0 (`design_steering_enabled`)

**You are implementing DS-01 (design steering) in the real engine**
(`Project-Bootstrap-Protocol-main`: `lib/`, `bin/`, `tests/`, `plugin/`). The two
protocol **documents** are already at v2.5.0 (the redline is applied). Your job is
the **code**: wire the opt-in flag through interview → config → emission → state →
tests, exactly as `telemetry_export_enabled` (TEL-01) is wired, plus the one
genuinely new piece (an archetype-gated *offer*).

**Read `VALIDATION-v2.5.0-against-implementation.md` first.** It is the map: the
four-layer TEL-01 anchor table, the two doc-vs-code reconciliations, and the
golden-determinism exit gate. Do not re-derive the wiring — copy the precedent.

---

## The one sentence that governs everything

**Design steering is off by default, and the default install plan must stay
byte-identical to the pre-feature baseline** — proven by
`tests/test_greenfield_golden.py` digests **not changing**. If a default-path
digest changes, you have leaked the feature into the default and the
implementation is wrong, full stop.

---

## Locked decisions (do not relitigate)

1. **Pure opt-in: default `false`, off everywhere.** The wizard *offers* it during
   the Phase 0 interview only for user-facing archetypes; the operator enables it.
   No "default on", no "opt-out". (The only legitimate opt-out string in the repo
   is the pre-existing `cicd_opt_out` — leave it alone.)
2. **The offer is archetype-gated; the flag is not.** The interactive prompt is
   shown only for `{fullstack, mobile, ai-agent, platform, other}`. But the
   ANSWERS-block / synthesized path accepts `design_steering_enabled: true` for
   any archetype an operator hand-sets — do not add archetype validation that
   rejects the flag. (Rationale: `VALIDATION §3`.)
3. **`platform` is a real archetype enum value** (`defaults.py:16–17`), offered
   **directly**, not through a synthetic-profile indirection. `service`, `cli`,
   `library`, `data-ml` are **excluded** from the auto-offer. (Rationale:
   `VALIDATION §2`.)
4. **`design-review` is a skill, never a hook.** It flags, never blocks (Path C is
   rejected). It must NOT appear in `_hook_body` (`templates.py:278–589`) or in
   any `settings.json` / `PreToolUse` / `PostToolUse` wiring.
5. **The three emitted artifacts are frozen (DR-2-final, with one owner-approved
   post-DR-2 revision — DELTA-01):** `design.md`,
   `.claude/skills/design-review/SKILL.md`, `.claude/commands/design-review.md`.
   You are wiring *how the wizard offers and emits* them, not authoring them.
   Their bodies are supplied (see "Artifact bodies" below); emit them verbatim
   except the operator-filled Project-specifics placeholder.
   **DELTA-01 (v2.5.0 delta review, owner-approved):** the `design.md` body's
   persuasion-section header was changed from "(ranked highest)" to "(highest
   within this doc)" and a sentence was appended pointing cross-domain ties to
   `principles.md` as the sole ranking surface. This closes the compose-vs-fork
   soft joint at the artifact (not just the protocol prose). **The attached
   `design.md` already contains this revision — emit it as-is. The flag-on golden
   fixture digests MUST be generated against this revised body**, or they lock in
   the pre-DELTA-01 bytes. This does not touch the default path (design steering
   is off by default), so the existing greenfield digests are unaffected.
6. **Interview wording is verbatim** and must match the protocol doc's Phase 0
   step 6 design-steering string **identically**. The protocol doc is the **sole**
   verbatim source — there is no `INTERVIEW-WORDING.md` in this repo (TEL-01 has
   none either). If you tighten any wording, update the protocol doc and the code
   string in the same commit.

---

## Do this, in order

Work bottom-up (normalizer → config → emission → state → interview → tests) so
each layer's dependency exists before the layer that calls it. Keep every edit a
line-for-line TEL-01 twin; cite the TEL-01 anchor in each new comment (`# DS-01
(v2.5.0): twin of TEL-01 at <file>:<line>`).

### Step 1 — `lib/installer.py`: the normalizer (twin of `telemetry_enabled`)

Model on `telemetry_enabled(cfg)` at `installer.py:62–82`. Add:

```python
def design_steering_enabled(cfg: dict) -> bool:
    """Resolve the DS-01 opt-in flag to a bool, fail-loud on garbage.
    Twin of telemetry_enabled (installer.py:62)."""
    raw = cfg.get("design_steering_enabled", False)
    # ... identical bool / int(0,1) / str-token normalization ...
    raise ValueError(
        f"design_steering_enabled: unrecognized value {raw!r}. Use true or "
        "false (yes/no/on/off/1/0 are accepted). This flag is an opt-in for a "
        "design-steering doc, so the installer refuses to guess.")
```

Add parallel `_DESIGN_TRUE/_FALSE` token sets modelled on `_TELEMETRY_TRUE/_FALSE`
(`installer.py:58`). **There is NO shared `_BOOL_TRUE/_FALSE` set in this repo
(verified: grep returns nothing) — do NOT create one by refactoring telemetry's
tokens.** Refactoring `_TELEMETRY_TRUE/_FALSE` touches the telemetry normalizer,
which the full_autonomous golden fixture exercises, and risks perturbing the
telemetry digest. Just parallel them to keep the diff minimal and the golden test
honest.

### Step 2 — `lib/installer.py`: `build_plan` flag-gated add (twin of `:132–133`)

Immediately after the telemetry add (`installer.py:132–133`), add:

```python
    # DS-01 (v2.5.0): opt-in design-steering doc, emitted ONLY when the operator
    # opted in. Lands in .claude/steering/ (committed by construction, no
    # gitignore edit). Off by default: default plan byte-identical to baseline.
    if design_steering_enabled(cfg):
        add(".claude/steering/design.md", TEMPLATES["design"](cfg))
        if design_review_skill_enabled(cfg):        # see Step 2b
            add(".claude/skills/design-review/SKILL.md",
                TEMPLATES["design_review_skill"](cfg))
            add(".claude/commands/design-review.md",
                TEMPLATES["design_review_command"](cfg))
```

**Step 2b — the optional skill is a *second* decision.** Per the protocol doc's
Phase 0 step 6 wording the skill is a separate yes/no so "yes to the doc" doesn't
silently install the
skill. Add a second flag `design_review_skill_enabled` (default `false`), gated on
the primary being on. It follows the same normalizer pattern. **Decision to
confirm with owner:** whether the skill flag is a distinct persisted state field
or a sub-key. Recommend a distinct top-level bool `design_review_skill_enabled`
for symmetry with the flat flag namespace; flag if the owner prefers nesting.

### Step 3 — `lib/templates.py`: the three template bodies + registry

- Add `_design(cfg)` modelled on `_telemetry` (`templates.py:361–379`): frozen
  body, **fail-loud on any missing stamped value**. The only emission-time
  variable is the operator-filled **Project-specifics** block — emit it as an
  explicit HUMAN-REQUIRED placeholder (mirror the `commands_*`
  empty-string→TODO-marker contract), never guessed. Static invariants +
  honest-use prose are verbatim from the supplied `design.md` body.
- Add `_design_review_skill(cfg)` and `_design_review_command(cfg)` — verbatim
  from the supplied `SKILL.md` / command stub. These carry no emission-time
  literal at all (fully static); assert that in a comment so a future TAR review
  knows determinism is trivially preserved.
- Register in the `TEMPLATES` dict (`templates.py:3170–3171`, after `"telemetry"`):
  ```python
  "design": _design,
  "design_review_skill": _design_review_skill,
  "design_review_command": _design_review_command,
  ```

### Step 4 — `lib/installer.py`: `_write_state` field (twin of `:891`)

In `_write_state` (`installer.py:817–892`), after the telemetry field, add:

```python
        # DS-01 (v2.5.0): Phase 0 opt-in decision, persisted cfg-authoritatively.
        # The flag-gated build_plan add keys off the same normalizer, so the
        # emitted design.md and this state field can never disagree.
        "design_steering_enabled": design_steering_enabled(cfg),
        "design_review_skill_enabled": design_review_skill_enabled(cfg),
```

**Forward-compat (default-on-read, NOT IC-3):** the normalizer already returns
`False` when the key is absent (`cfg.get(..., False)`). Nothing is written into
old state files at read time. This is the `telemetry_export_enabled` /
`exit_reason` posture, **not** the IC-3 `gate_substrate` write-into-old-files
mechanism. Do not cite IC-3 as precedent anywhere.

Confirm `_write_retrofit_state` (the sibling at `installer.py:932+`) gets the same
two fields if retrofit installs are meant to carry the flag (they inherit the
false default harmlessly if not; match whatever telemetry does — telemetry is in
`_write_state` only, so parity means design goes there too, and retrofit inherits
the default). **Flag if unsure rather than guessing.**

### Step 5 — `lib/interview.py`: the four telemetry-twin sites

1. **Key list** (`interview.py:64`): add `"design_steering_enabled"` and
   `"design_review_skill_enabled"` after `telemetry_export_enabled`.
2. **Defaults** (`interview.py:164`): add both `: False`.
3. **answers→config** (`interview.py:201–204`): add both as **top-level** bools
   (NOT nested under autonomous_modes), keyed off `ans.get(..., False)`.
4. **ANSWERS fail-loud** (`interview.py:530–540`): add a section-marker–
   discriminated missing-key branch for each, using a new
   `DESIGN_SECTION_MARKER` / `DESIGN_SECTION_TITLE` constant pair (twin of
   `TELEMETRY_SECTION_MARKER` at `interview.py:286`). A pre-2.5.0 ANSWERS block
   without the design section defaults the flag to `false`; a v2.5.0+ block that
   carries the section but is missing the key fails loud (a deleted/misspelled
   opt-in is never silently resolved).

### Step 6 — `lib/interview.py`: the archetype-gated interactive prompt (THE NEW PART)

This is the only site with no telemetry twin. After the telemetry `show()/_ask()`
block (`interview.py:721–737`):

```python
    # DS-01 (v2.5.0): archetype-GATED offer. Telemetry is asked unconditionally;
    # design steering is asked only for user-facing archetypes. Excluded
    # archetypes record false without prompting (interview stays short).
    # NB: both _ask calls pass stream args BY KEYWORD, exactly like the
    # telemetry twin at interview.py:735 (instream=/outstream=/eof=). Do not
    # use bare positional args — _ask's signature (interview.py:569) requires
    # the keywords. Verify show()'s arity against the telemetry block at :721
    # before pasting.
    _DESIGN_OFFER_ARCHETYPES = {"fullstack", "mobile", "ai-agent",
                                "platform", "other"}
    if ans["archetype"] in _DESIGN_OFFER_ARCHETYPES:
        show("Design steering", "<VERBATIM primary question from the protocol "
             "doc Phase 0 step 6 'Generate a design steering doc?' block — the "
             "SOLE verbatim source; see note below>")
        v = _ask("Generate design steering doc? true|false",
                 str(ans["design_steering_enabled"]).lower(),
                 instream=instream, outstream=outstream, eof=eof)
        ans["design_steering_enabled"] = v.lower() in ("true","1","yes","on")
        if ans["design_steering_enabled"]:
            show("Design-review skill", "<VERBATIM follow-up question from the "
                 "same protocol-doc block>")
            v2 = _ask("Add advisory design-review skill? true|false",
                      str(ans["design_review_skill_enabled"]).lower(),
                      instream=instream, outstream=outstream, eof=eof)
            ans["design_review_skill_enabled"] = \
                v2.lower() in ("true","1","yes","on")
    # else: both flags stay at their False default, no prompt shown.
```

Paste the **exact** verbatim strings from the protocol doc's Phase 0 step 6
design-steering block (primary + follow-up). **There is no `INTERVIEW-WORDING.md`
in this repo** — the protocol doc is the single source of truth for the wording
(this mirrors TEL-01, whose verbatim string also lives only in the protocol doc +
code, with no separate wording file). Do not paraphrase. A diff between the pasted
code string and the protocol-doc string must be empty. *(If an external
`INTERVIEW-WORDING.md` governance copy exists outside this repo, sync it post-hoc
— it is not a blocker for this execution, which can only diff against the
protocol doc it has.)*

### Step 7 — version bump

Find the current-version constant the engine stamps into
`bootstrap_protocol_version` (search `lib/` and `bootstrap.config.yaml` for the
`2.4.0` **default/current** value — NOT historical references). Bump the current
value to `2.5.0`. Do **not** global-replace `2.4.0`: changelog/migration history
must stay. `grep -rn "2\.4\.0" lib/ bin/ bootstrap.config.yaml` and change only
the one(s) that are the *current* protocol version, leaving historical strings.

### Step 8 — tests (mirror `test_installer.py:720–830`, add golden fixture)

Add a `# DS-01 (v2.5.0)` block mirroring the telemetry tests:

- **[off/default]** no `design.md`; **golden digest unchanged** (the critical
  assertion — the default plan is byte-identical to baseline).
- **[on]** `design.md` emitted exactly once; committed (steering not gitignored);
  state field `true`.
- **[on + skill]** SKILL.md + command stub emitted exactly once each; state
  `design_review_skill_enabled: true`.
- **[on, doc-only]** primary on but skill declined → design.md only, no skill/cmd.
- **[archetype gate]** for a non-user-facing archetype (`cli`, `library`,
  `service`, `data-ml`) the *interactive* interview does **not** prompt and records
  `false`; but an ANSWERS block that hand-sets `design_steering_enabled: true` on
  `data-ml` **still emits** (offer gated, flag not).
- **[fail-loud]** a v2.5.0-rendered ANSWERS block carrying the design section but
  missing the key raises; a pre-2.5.0 block without the section defaults false.
- **`tests/test_greenfield_golden.py`:** add a **new flag-on fixture** with its
  own digests (via `GOLDEN_UPDATE=1`), and **verify the existing greenfield
  digests are untouched.** If any existing digest changed, stop — the feature
  leaked into the default path.
- **[interview verbatim]** assert the interview prompt string equals the protocol
  doc's Phase 0 step 6 primary question (guards against drift).

### Step 9 — plugin / commands surface

Check `plugin/commands/` and `plugin/plugin.json`. **Verified fact:** `plugin.json`
uses a directory pointer (`"commands": "./commands"`), NOT static per-command
enumeration — so `/design-review` is discovered from the directory and needs **no
manifest edit**. Emit the `/design-review` command file **conditionally** (only
when the skill is emitted). Confirm it's advisory-only in any description string.
Do not add a static manifest entry (there is no static command list to add to).

---

## Exit criteria (all must pass — "edits are in" is NOT the bar)

1. `python3 tests/test_greenfield_golden.py` — **existing digests unchanged**;
   new flag-on fixture digests stable across two runs (determinism).
2. `python3 tests/test_installer.py` — all prior checks still pass + new DS-01
   checks pass.
3. `python3 tests/test_interview.py` — telemetry checks still pass + new design
   checks pass; the verbatim-string assertion passes.
4. `bin/bootstrap-install --dry-run --print-config` on a fullstack fixture with
   the flag on lists `design.md` (+ skill/cmd if accepted); with the flag off,
   lists neither and the printed plan matches baseline.
5. `grep -rn "design-review" lib/` shows **no** `_hook_body` / `settings.json` /
   `PreToolUse` coupling (skill is advisory, not a hook).
6. Interview prompt string `diff` against the protocol doc's Phase 0 step 6
   design-steering question is empty (the protocol doc is the sole verbatim
   source; there is no `INTERVIEW-WORDING.md` in this repo).
7. Version constant is `2.5.0`; historical `2.4.0` references intact.
8. **Fresh-bootstrap smoke:** one real `bin/bootstrap-interview` +
   `bin/bootstrap-install` run on a fullstack test project; confirm the wizard
   offers design.md, emits it on accept, emits the skill+command on the second
   yes, and records both state flags.

## Scope boundaries — do NOT

- Do not author or alter the three artifact bodies (DR-2-final); emit them.
- Do not turn honest-use rules into a hook (Path C rejected).
- Do not add archetype *validation* that rejects the flag — only the *offer* is
  gated.
- Do not refactor `telemetry_enabled` or the shared bool-token sets in a way that
  perturbs the telemetry golden digests.
- Do not global-sed `2.4.0`.

## Artifact bodies

Attach the frozen `design.md`, `SKILL.md`, and `.claude/commands/design-review.md`
from the project (DR-2-final; `design.md` carries the owner-approved DELTA-01
revision — see Locked decision 5). The attached `design.md` is the **post-DELTA-01**
version: its persuasion header reads "(highest within this doc)" and the section
appends a `principles.md`-defers-to sentence. Confirm the attached body matches
that before generating any fixture. If the three bodies are not attached to your
session, **stop and request them** — do not reconstruct them from the doc summary,
and do not proceed with a placeholder body, because the golden fixture digests
would then lock in the wrong bytes (and a pre-DELTA-01 `design.md` would lock in
the un-hardened header).

---

## One-line summary

Wire `design_steering_enabled` (+ the optional `design_review_skill_enabled`) as a
line-for-line TEL-01 twin across `interview.py` / `installer.py` / `templates.py` /
state / tests; the only net-new logic is the archetype-gated interactive offer;
prove off-by-default by leaving `test_greenfield_golden.py`'s existing digests
untouched; keep the skill advisory (never a hook); finish with the fresh-bootstrap
smoke.

# Implementation Gap Analysis — Bootstrap Protocol `main` vs. the Staged Document Set

**Date:** 2026-07-17
**Input:** `Project-Bootstrap-Protocol-main.zip` (the real repo: `lib/`, `bin/`, `plugin/`, `tests/`, protocol docs). Zip timestamps ≈ May 28 2026; user confirms it is somewhat dated.
**Compared against:** `Tessera-PRD-v0-5-0.md`, `SEAM-CONTRACT-v1-0-0.md`, `Bootstrap-Protocol-v2-0-0.md`/Companion, and the modernization tracker.
**Method:** Every claim below is grep/read-verified against source (P-1). Findings are IG-xx, ordered by consequence. Classification: **SEAM-BREAKING** (a seam pin is factually wrong against the code) / **PRD-GAP** (the PRD asserts something the code contradicts or omits) / **UNMODELED** (real surface none of our documents cover) / **CONFIRMED** (our claim verified true — listed so the fold record shows what was checked, not just what failed).

---

## Part 1 — SEAM-BREAKING findings (the contract's declared wire is wrong)

### IG-01 — `synthesize --validate-only` DOES NOT EXIST. Neither does `--prd` on synthesize.
**Code:** `lib/interview.py:728–731` — `synthesize` takes exactly `-i/--interview` and `-o/--out`. No `--validate-only` anywhere in `lib/` or `bin/` (grep: zero hits).
**What we claimed:** Seam §3.2 lists `bootstrap-interview synthesize --validate-only` as a permitted entry point "with documented fallback when unavailable." Tessera's H01 fix (§10.3 step 5) *depends* on shelling out to `synthesize --validate-only`; §10.4 likewise.
**Impact:** The "fallback when validate-only mode unavailable" isn't a fallback — it's the only path. Today, dry-validation of frontmatter/config compatibility must be achieved by `synthesize` to a throwaway output + `bootstrap-install --print-config` or `--dry-run` (both of which DO exist: `installer.py:692–698`).
**Fix:** Seam §3.2 row corrected: `--validate-only` marked **not-implemented-at-pin; validation path = synthesize→tmp + install --dry-run/--print-config**, with `--validate-only` recorded as a requested upstream feature. Tessera §10.3/§10.4 step wording updated to the real path. AC-PROTO-014's job must test the path that exists.

### IG-02 — Sentinel locations are wrong in the seam: the code uses `.claude/queue/.halt` and `.claude/sessions/.loop-active-*`, NOT `<project-dir>/.halt`.
**Code:** `templates.py:852` `RUN="$PROJ/.claude/queue/.run-active"`; `:939` `HALT="$PROJ/.claude/queue/.halt"`; gitignore fragments list `queue/.halt`, `queue/.resume`, `sessions/.loop-active-*`, `sessions/.goal-active-*`. Zero occurrences of a project-root `.halt` in `lib/`.
**What we claimed:** Seam §7.4 declares shared sentinels at `<project-dir>/.halt`, `<project-dir>/.halt-hard`, `<project-dir>/.run-active`, and Tessera §12.2 builds its whole kill-switch sharing story on those paths ("Tessera and the protocol's bash skeletons honor the same per-project sentinels"). AC-PROTO-007's assertion touches `.halt` at project root.
**Impact:** As pinned, **Tessera's shared-kill-switch guarantee is false against main**: dropping `<project-dir>/.halt` would halt Tessera but the protocol's `auto.sh` watches `.claude/queue/.halt`. The SEV-1 "run the skeleton by hand, halt via shared sentinel" story doesn't work. There is also no `.halt-hard` in the code at all — hard-kill is a Tessera-only concept end-to-end.
**Fix (decision required — two honest options):** (a) **Adopt the code's paths**: seam §7.4 re-pins shared sentinels to `.claude/queue/.halt` (+ `.resume`, `.run-active` under `queue/`), Tessera §12.2 watches/writes both its own root sentinels *and* the protocol's queue-scoped ones, AC-PROTO-007 re-targeted; or (b) **Upstream change**: protocol adds root-sentinel support (a 2.x item). Until (b) ships, (a) is the only truthful pin. Recommend (a) now + (b) as a logged upstream request. Either way this is a seam MAJOR-relevant correction (§7.4 names are contract-level).

### IG-03 — The security-critical hook set in seam §7.2 doesn't match the emitted filenames, and two gate-adjacent hooks are missing from it.
**Code:** `_hook_body` dispatch (`templates.py:278–589`) emits exactly: `spec-gate-entry`, `spec-gate-commit`, `secrets-gate`, `test-gate`, `format-lint-gate`, `ci-mirror`, `cost-log`, `dependency-gate`, `tdd-gate`, `eval-gate`, `drift-detector`, `task-done-alarm`, `decision-required-alarm`, `drift-detector-loop-cooperation`, `iteration-summary-enforcement`.
**What we claimed:** Seam §7.2's security-critical set: `hooks/secrets-gate*`, `hooks/spec-gate-commit*`, `hooks/dependency-gate*`, `hooks/test-gate*`, `hooks/eval-gate*`, `hooks/tdd-gate*`, `hooks/format-lint-gate*`, `settings.json`.
**Gaps:** (1) `spec-gate-entry` exists in code but is absent from the security-critical set — defensible (entry is warn-tier, commit is block-tier per the protocol's own split) but must be *stated as deliberate*, not silent. (2) `drift-detector-loop-cooperation` and `iteration-summary-enforcement` are enforcement-relevant in autonomous modes (loop-cooperation implements tier-3 hard-block; summary-enforcement gates goal-mode halts) and are in no tier of our hand-edit policy. (3) `ci-mirror` and `cost-log` correctly non-critical — confirmed.
**Fix:** Seam §7.2 updated to the emitted name list verbatim, with a three-tier statement: security-critical (as before + explicit rationale for excluding `spec-gate-entry`), **autonomy-critical** (new tier: `drift-detector-loop-cooperation`, `iteration-summary-enforcement` — hand-edits refuse *autonomous* dispatch only), and non-critical. Tessera §9.8's split gains the middle tier.

### IG-04 — AC-PROTO-015's provenance markers (`source:` field) are NOT accepted-by-implementation — they're simply unimplemented, which is weaker than what the PRD asserts.
**Code:** zero occurrences of provenance handling in `lib/interview.py` (grep for the four marker values: empty).
**What we claimed:** Tessera §9.6/AC-PROTO-015: "The `synthesize` subprocess accepts the file without error (the field is ignored by current protocol validation)."
**Impact:** Likely still *true* behaviorally (the ANSWERS-block parser probably ignores unknown per-answer fields) — but it is an untested inference, and AC-PROTO-015 asserts acceptance as fact. The forward-compat framing survives; the "current validation ignores it" claim needs a test, not an assumption.
**Fix:** No PRD text change needed; AC-PROTO-015's assertion is *already* the test that would catch it — but the compatibility job must actually run against this pin before the AC can be marked satisfiable. Flagged as verify-at-CI, not verify-by-reading.

---

## Part 2 — PRD-GAP findings

### IG-05 — `resolve_config` invariants: partially confirmed, tier-floor claim unverified.
**Code:** `defaults.py:233` archetype enum enforced (`cli|library|service|fullstack|mobile|data-ml|ai-agent|platform|other` — note **`data-ml`**, **`platform`**, **`other`** are in the enum; Tessera's §0.1/§6 discourse assumes the archetype set but AC-PROTO-014's invariant list says "tier floors" are checked — no tier-floor enforcement was found in `defaults.py` (only `prd_tier` as a passthrough enum `micro|standard|full` in the config comment). `:239–243` queue⇒loop|goal confirmed, including a *second* independent enforcement in the retrofit branch (`:401–408`) and a file-level enforcement in the installer (wrappers emitted whenever the mode flag is on, so the invariant holds "at the file level, not just logically" — `installer.py:101` comment).
**Fix:** AC-PROTO-014's invariant list corrects "tier floors" to "prd_tier enum" unless a floor rule is found elsewhere at rebase; the queue invariant's *dual enforcement* (config-level + file-level) is worth citing in §9.7 as a strength.

### IG-06 — The config schema has surfaces Tessera's synthesized-interview path must populate that our documents never enumerate.
**Code:** `bootstrap.config.yaml` — notably: `project.shell` (affects hook shebangs), `commands.{test,lint,format,typecheck,ci_local}` with the **fail-loud-on-empty contract implemented as TODO-marker hooks** ("Empty strings produce a TODO marker in the hook so it fails loud rather than silently passing"), `hooks.*` per-hook force-disable toggles + three drift thresholds, `mcp.rejected` (rejected-with-reason list), `secrets.rotation_policy`, `workflow.{implementer,reviewer,integrator}_model`.
**What we claimed:** Tessera §10.2/§10.4.1 models the commands.* confirmation and machine-config synthesis, but: (1) `mcp.rejected` — Tessera's machine config has MCP servers but no rejected-with-reason ledger; (2) `workflow.*_model` — **this is where the model remap actually lands on the wire**: Tessera's synthesized config must write `implementer_model: "sonnet"` etc. (aliases, per the frontmatter convention) — none of our fold edits stated that the §10.2 `model_pins` (pinned IDs, Tessera layer) and `workflow.*_model` (aliases, config wire) are *two different fields at two layers*, which is exactly the TR-03 layer-split made concrete; (3) `project.shell` — unmodeled in machine.yaml.
**Fix:** Tessera §10.2 machine.yaml gains `mcp_rejected` passthrough + `shell` detection; §9.6's synthesized-config enumeration explicitly maps `model_pins` (Tessera) → `workflow.*_model` (wire, aliases) with the audit-logged resolution bridging them. This closes the remap's last unwired hop.

### IG-07 — `--force`, `--print-config`, and the uninstall flag exist and are unpinned.
**Code:** `installer.py:689–698`: `-c`, `-C`, `--dry-run`, `--force`, `--uninstall`, `--print-config`.
**What we claimed:** Seam §3.2 pins `bootstrap-install`, `--dry-run`, `--uninstall`. `--print-config` (the validation workhorse per IG-01) and `--force` are undeclared.
**Fix:** Seam §3.2 adds `--print-config` (needed by the IG-01 validation path) and explicitly *prohibits* `--force` in Tessera's automated path (force-overwrite defeats the hand-edit preservation contract §7.2 depends on; human-CLI use only).

### IG-08 — LLM advisor defaults to a RETIRED model ID.
**Code:** `llm_advisor.py:85–86`: `BOOTSTRAP_INTERVIEW_LLM_MODEL` defaults to `"claude-sonnet-4-20250514"` — retired June 15 2026; API calls to it now fail.
**Impact:** Any Tessera flow that enables `--llm` on `analyze` (we don't today — confirmed none of our paths pass `--llm`) would error. Still: the pin bump compatibility job should assert the advisor's default resolves, or Tessera's runbook must document exporting the env var. Also note the advisor's design is exemplary for our purposes: proposes-never-decides, deterministic-fallback-on-any-failure, commands never sent to the model — worth citing in §9.6 as the pattern Tessera's own LLM refinement already mirrors.
**Fix:** Upstream issue (bump default to a current ID); Tessera runbook note (set `BOOTSTRAP_INTERVIEW_LLM_MODEL=claude-sonnet-5` if ever enabling `--llm`); compatibility job gains a "advisor default model resolves OR --llm unused" check.

### IG-09 — Test suite is thinner than the PRD's confidence implies.
**Code:** `grep -c "def test"`: `test_retrofit.py: 3`, all others **0** matched by that pattern (they may use classes/other conventions — but `test_greenfield_golden.py` at 7.4KB with zero `def test` hits warrants a look; likely golden-file comparison driven differently).
**Impact:** AC-PROTO-014's compatibility suite leans on upstream determinism claims ("byte-for-byte identical tree") that the golden test may or may not cover at the granularity Tessera assumes.
**Fix:** At pin-bump time, run the actual test suite and record what it covers in the runbook compatibility matrix; Tessera's own AC-PROTO-002 fixture (fake manifest, N files, sha256 stability) remains the load-bearing check on our side — correctly so.

---

## Part 3 — UNMODELED surface

### IG-10 — The RETROFIT protocol: a full second track (v1.6.2) our documents never mention.
**Code:** `RETROFIT.md` (184KB), `RETROFIT-COMPANION.md`, `RETROFIT-GAP-ANALYSIS.md`, `lib/retrofit_interview.py`, `lib/retrofit_heuristics.py`, `lib/inventory_scan.py`, `bin/retrofit-interview`, `RETROFIT_PROTOCOL_VERSION = "1.6.2"` (`installer.py:37`), a `mode: "retrofit"` config branch with its own overlay (`installer.py`: `_apply_retrofit_overlay`), retrofit-specific hook bodies (`_hook_body_retrofit`, AST-verified against greenfield), stricter-than-greenfield autonomous-mode trust gates, and dual enforcement of the queue invariant in the retrofit branch.
**Impact:** Every Tessera flow assumes greenfield: J4 scaffolds from a certified PRD into a fresh project. **Importing an existing codebase into Tessera** (a plainly foreseeable v1.x user story) would want the retrofit track — and Tessera's PRD neither supports nor explicitly excludes it. Unstated scope is the exact ambiguity the certification thesis exists to kill.
**Fix (recommend the honest minimum):** Tessera v0.5.x adds an explicit **non-goal**: "NG12 — Retrofit-mode projects (Bootstrap's RETROFIT.md track) are out of scope for v1; Tessera projects are greenfield-scaffolded only. Deferred with constraints locked: if adopted, retrofit enters via the same synthesize→install seam (`mode: retrofit` in the emitted config), inherits the stricter autonomous-mode trust gates, and requires its own §17 threat entries (existing-code prompt-injection surface) before the seam admits it." Seam §3.2 notes `retrofit-interview` exists and is **not** a permitted Tessera entry point at this pin.

### IG-11 — The plugin packaging (`plugin/plugin.json`, `/bootstrap-interview`, `/bootstrap-apply` commands) is real and unpinned.
The Companion mentioned the plugin in passing; the seam doesn't model it. Tessera invokes via `bin/` subprocess — correct and confirmed — but the plugin's existence means a user's *interactive* Claude Code session inside a Tessera-managed project could invoke `/bootstrap-apply` and mutate the `.claude/` tree outside Tessera's audit. **Fix:** Tessera §17 gains a note under the OS-user trust boundary (T7/T12 family): plugin-driven re-installs are operator hand-edits at the manifest layer — already governed by §9.8's digest split — cite it so the path is visibly covered, not accidentally covered.

### IG-12 — `minyaml.py`: the protocol has a dependency-free YAML subset parser, not PyYAML.
Emitted/parsed YAML is a deliberate subset. Tessera's canonical-serialization discipline (§6.3.1, M06) writes the synthesized interview/config with its own dumpers — if Tessera emits YAML features outside minyaml's subset (anchors, multiline folding, flow mappings), `synthesize`/`install` will mis-parse or reject. **Fix:** §9.6 gains a constraint: the synthesized `bootstrap.interview.md` ANSWERS block and any YAML Tessera writes for the protocol MUST stay within the minyaml subset (plain scalars, simple lists/maps); the compatibility job round-trips a Tessera-emitted config through `--print-config` to prove parse fidelity.

---

## Part 4 — CONFIRMED (verified true, recorded per the fold discipline)

- **Version identity:** main IS 1.9.0 (`PROTOCOL_VERSION = "1.9.0"`), and main's `BOOTSTRAP.md`/Companion are byte-size-identical to our project-knowledge copies — our source documents were faithful. The `binds` `[TODO: exact commit]` can now bind to this snapshot (zip lacks `.git`, so the *hash* still needs the live repo — but the content identity is established).
- **Subprocess-only seam shape:** `bin/` entry points are thin wrappers over `lib/`; the two-layer decision/mechanical split matches AC-PROTO-001's model exactly.
- **queue⇒loop|goal:** enforced at config level (`defaults.py:239`), retrofit level (`:401`), and file level (`installer.py:101`). Stronger than we claimed.
- **Wrappers are emitted conditionally per mode flags** exactly as §9 models; `auto.sh` is "a terminal-invoked runner, NOT a stdin-fed hook" (F-2 fix comment) — matches the Companion's wrapper framing.
- **Manifest + state file:** `.claude/.installer-manifest.json` and `.claude/.bootstrap-state.json` at the documented paths; state carries `bootstrap_protocol_version` — the D-01 `gate_substrate` field slots in cleanly here as an upstream 2.x addition.
- **Agent frontmatter:** emits `model: {alias}` + `isolation: worktree` for the implementer — TR-03(b)'s alias-at-frontmatter decision confirmed correct; the manual worktree plumbing (C-1's "may be hand-rolling") is real: the wrappers do their own claim/sentinel dance, so the native `--worktree` migration remains a genuine 2.x simplification.
- **Fail-loud-on-empty-commands:** implemented as documented (empty command → TODO-marker hook that fails loud).
- **`--dry-run` / `--uninstall` / `--print-config`:** all real (`--print-config` newly pinned per IG-07).

---

## Part 5 — Where each fix lands (fold routing)

| ID | Class | Target | Bucket |
|---|---|---|---|
| IG-01 | SEAM-BREAKING | Seam §3.2 + Tessera §10.3/§10.4 + AC-PROTO-014 | blocks-cert (H01 path is fictional as written) |
| IG-02 | SEAM-BREAKING | Seam §7.4 + Tessera §12.2 + AC-PROTO-007; upstream request logged | blocks-cert (kill-switch sharing claim false) |
| IG-03 | SEAM-BREAKING | Seam §7.2 three-tier + Tessera §9.8 | blocks-cert |
| IG-04 | PRD-GAP | AC-PROTO-015 verify-at-CI note | folds-with-TODO |
| IG-05 | PRD-GAP | AC-PROTO-014 invariant wording | folds-with-TODO |
| IG-06 | PRD-GAP | Tessera §10.2 + §9.6 (model_pins→workflow.*_model mapping; mcp_rejected; shell) | blocks-cert (remap's last hop unwired) |
| IG-07 | PRD-GAP | Seam §3.2 (+`--print-config`, prohibit `--force`) | folds-with-TODO |
| IG-08 | PRD-GAP | Runbook + upstream issue + compat check | post-fold |
| IG-09 | PRD-GAP | Runbook compatibility matrix note | post-fold |
| IG-10 | UNMODELED | Tessera NG12 + seam §3.2 note | blocks-cert (scope must be stated) |
| IG-11 | UNMODELED | Tessera §17 note citing §9.8 coverage | folds-with-TODO |
| IG-12 | UNMODELED | Tessera §9.6 minyaml-subset constraint + compat round-trip | blocks-cert (silent mis-parse risk) |

**Net:** the dated implementation *validates the architecture* — the seam shape, the subprocess isolation, the fail-loud contracts, and the alias-layer decision all check out against real code. What it falsifies is five specific pins (validate-only, sentinel paths, hook-set membership, tier-floors, and the unstated retrofit scope) plus one unwired hop in the model remap. Six items are blocks-cert; all are anchor-scoped edits. The v0.4.1 rebase and this reconciliation should land as one pass, since both touch §9.x/AC-PROTO-* and doing them separately invites a second collision.

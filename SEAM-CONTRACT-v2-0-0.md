-----

artifact_name: tessera-bootstrap-seam-contract
seam_version: 2.0.0
status: draft
authored_by: Deng Clive
consumed_by:
  - tessera (PRD; pins a seam_version)
  - project-bootstrap-protocol (emits conformant to a seam_version)
governing_principle: compose-do-not-fork
non_authoritative_note: This artifact declares the wire only. It contains no gate engineering (Bootstrap-owned) and no dispatch policy (Tessera-owned).
binds:
  # The compatibility set. This block is the single authoritative statement of
  # "these documents are in sync." Sync is a verified relationship declared here,
  # NOT a coincidence of matching version numbers. CI (§8.2) asserts each pinned
  # document's declared version resolves inside its range below. A change to this
  # block is at least a MINOR seam bump; a range that drops a previously-satisfying
  # version is a MAJOR bump (§8.4).
  #
  # [seam 1.0.0 MAJOR re-cut] Triggered by (a) Bootstrap Protocol 2.0.0 (breaking:
  # gate substrate → Agent SDK; native worktree; model remap) and (b) the B-5
  # result-parsing field-semantics change (§4.1). Both invalidate prior consumer
  # assumptions, so every range below was re-validated and re-cut.
  #
  # [seam 2.0.0 MAJOR re-cut] The substrate-release re-cut the 1.x line always owed
  # (§9 "When implemented"; the v1.2.0 changelog names it the owed MAJOR). Triggered
  # by re-pointing `bootstrap_protocol` from the shell-conformant `2.0.0 @ 1fa5bb6`
  # to `2.4.0 @ 251f82f`. That re-point DROPS a previously-satisfying version
  # (2.0.0 is an EXACT commit pin, not a widened range — the owner did NOT pre-widen
  # at the 2.0.0 pin), which is a MAJOR by §8.4. Bundled into the same MAJOR, per the
  # §9 choreography: the SDK gate substrate ENTERED THE WIRE at protocol 2.1.0
  # (IC-5, gate_substrate "sdk-callable"), so the §9 deferred surface is now live —
  # the `build_hooks` builder API joins §3 (new §3.3) and `.claude/sdk_gates/gates.py`
  # joins the §7.2 security-critical set. 2.1.0→2.2.0→2.4.0 added no further
  # seam-visible surface (verified: 2.4.0's new files land in §7.2 non-critical),
  # so one re-point straight to 2.4.0 needs no intermediate pins.
  tessera_prd: ">=0.5.0,<0.6.0"           # [D-03; carried at seam 2.0.0] Floor = first Tessera version that ABSORBS the seam-1.0.0 fold (targets_seam_version + §12.4 estimate semantics). RANGE UNCHANGED at seam 2.0.0: the Tessera version that absorbs the substrate re-cut (targets_seam_version: 2.0.0 + a runner consuming build_hooks per §3.3) is a Tessera-roadmap fact not yet pinnable here, so the floor is carried forward rather than invented. Until that Tessera fold lands, this binds set is KNOWINGLY UNSATISFIED and CI check 0 SHOULD fail — specifically on the `targets_seam_version` half (Tessera targets seam 1.2.0 ≠ 2.0.0). The version-in-range half still PASSES: the range is carried forward unchanged, so the declared consumer (0.5.x) stays inside it — consistent with "floor carried forward, not invented" (a red range-half here would be the bug). Note check 0 does NOT mechanically verify substrate absorption (a runner actually consuming `build_hooks` per §3.3); so once Tessera flips `targets_seam_version` to 2.0.0 the tessera_prd portion of check 0 goes fully green even before such a runner exists. The out-of-sync signal is therefore carried by the sync half only until the owner re-cuts this floor to the absorbing Tessera version (≥0.6.x), at which point the range half becomes the enforcing half (P-5).
  bootstrap_protocol: "2.4.0 @ 251f82ff4795a2c7e50fe62baf8b37ef4cc2f99c"  # [2.0.0 substrate re-cut] Protocol 2.4.0 = merge commit of PR #8 on main (short: 251f82f). Supersedes `2.0.0 @ 1fa5bb6` (dropped — MAJOR). Check-0 asserts COMMIT identity across the four sites (this bind, Tessera pyproject.toml, PRD frontmatter target_protocol_pin, PRD §9.7 prose), all of which must be re-pointed to this SHA in the consumer's re-pin pass. 2.4.0 carries the SDK substrate (2.1.0) live; the shell substrate remains selectable (gate_substrate "shell"), so both §7.2 gate carriers coexist.
  claude_agent_sdk: ">=0.1.60"            # [v1.2.0 in-version correction, 2026-07-17] Feature-justified floor, replacing the v1.0.0 PROVISIONAL ceiling-as-floor (>=0.2.114, D-07). 0.1.60 is the earliest release where all load-bearing dependencies hold simultaneously: the PreToolUse `permissionDecision: "deny"` shape (§4.1) is mature, `dontAsk` is present in PermissionMode types (§3.1 posture; landed 0.1.51, #719), and `setting_sources=[]` is honored rather than silently dropped (R-7 SessionStart/SessionEnd retention relies on `setting_sources=["project"]`; fixed 0.1.60, #822). `ResultMessage.total_cost_usd` is present since the 0.0.13 rename. Forward option (NOT required): the `"defer"` PreToolUse decision lands at 0.1.74 — raise the floor there only if a future gate design consumes deferred tool use. Verified against the official `anthropics/claude-agent-sdk-python` changelog at the release tags.
  claude_code_runtime: ">=2.1.210"        # [v1.0.0; confirmed v1.2.0 2026-07-17] min runtime for fail-closed PreToolUse timeout (§B-14) + worktree-entry consent ≥2.1.206 + hyphen matchers ≥2.1.195; 2.1.210 is the binding floor. CONFIRMED against the official Claude Code changelog: the fail-closed PreToolUse hook-timeout fix lands at exactly 2.1.210 (a below-floor timeout is misreported to the model as a user rejection); the two subsumed floors verified in place. The IC-6 native-worktree flag introduction version is not officially pinnable but is subsumed by this floor.
  claude_code_json_schema_range: ">=TBD,<TBD"  # [D-04 renamed from claude_code] The §8.3 compatibility-matrix referent: which CLI JSON-schema/field-name matrix rows apply. Distinct from claude_code_runtime (the installed-CLI behavioral floor above). Resolve against the runbook matrix.
binds_note: >
  Directionality (see §2): the seam contract BINDS (declares which consumer version
  ranges satisfy it); each PRD PINS (declares the single seam_version it targets via
  its own targets_seam_version field). On disagreement, CI fails and this artifact is
  authoritative about the RELATIONSHIP only — never about either endpoint's internals.
  [v1.0.0] The Bootstrap pin moved from a placeholder commit-SHA to the 2.0.0 document
  version. [v1.2.0] The exact commit is now bound (`1fa5bb6`, the Milestone-A pin
  event) — the v1.0.0-era TODO is closed and check-0 asserts commit identity.
  [v2.0.0] The Bootstrap bind is re-pointed to `2.4.0 @ 251f82f` (substrate re-cut),
  dropping the previously-satisfying `2.0.0 @ 1fa5bb6` — a MAJOR. The relationship
  is now KNOWINGLY UNSATISFIED on the Tessera side until Tessera re-pins to
  `targets_seam_version: 2.0.0` and absorbs the §3.3/§7.2 substrate surface (P-5).

-----

# Tessera ↔ Bootstrap Protocol — Seam Contract (v2.0.0)

> *The wire, not either endpoint.*

## 0. Purpose and status of this document

This is the single authoritative definition of the interface between Tessera and the Bootstrap Protocol. Both project PRDs are **consumers** of this artifact:

- The **Tessera PRD** pins a `seam_version` and describes its behavior in terms of what this contract declares. Where Tessera's PRD previously restated the invocation surface, the JSON output schema, stream-event semantics, or protocol-pin mechanics, it should reference the corresponding section here instead.
- The **Bootstrap Protocol** emits artifacts and JSON conformant to a `seam_version`, and declares which `seam_version`(s) a given protocol commit satisfies.

**This document owns the interface and nothing behind it.** It does not specify how gates are engineered (that is Bootstrap-internal), nor how dispatch decisions are made (that is Tessera-internal). If a change is proposed that touches gate *behavior* or dispatch *policy* without changing the wire, it does not belong here.

**Why this artifact exists.** The seam was previously described on both sides, with nothing mechanically forcing the two descriptions to agree. That is the drift class Tessera already names elsewhere (stamp-drift; the recurring DR-03 heading-staleness regression). Promoting the seam from a shared assumption maintained by attention to a declared object maintained by CI is the structural expression of `compose-do-not-fork`: a fork becomes a visible violation of *this* document, not a quiet edit on one side.

## 1. Scope

### 1.1 In scope (this contract is authoritative)

1. The **invocation surface** Tessera is permitted to touch on the Bootstrap Protocol and on Claude Code (§3).
2. The **result-parsing contract**: the exact JSON fields Tessera reads from Claude Code headless output (§4).
3. **Stream-event semantics**: which events Tessera consumes and what each means (§5).
4. **Gate-emission-as-consumed**: what a Bootstrap gate refusal looks like on the wire, so that "consume as-emitted" has a concrete referent (§6).
5. **Workspace-artifact contract**: the `.claude/` files and sentinels whose names, locations, and digest semantics both layers depend on (§7).
6. **Protocol-pin compatibility**: how a Tessera version pins a protocol version and what a compatibility break means (§8).

### 1.2 Out of scope (owned by one side, not this contract)

- Gate **engineering** — how `secrets-gate`, `spec-gate`, `eval-gate`, `tdd-gate`, etc. are built and what they check internally. Bootstrap-owned.
- Dispatch **policy** — when Tessera dispatches, budget accounting, kill-switch UX, certification stamp scheme. Tessera-owned.
- Claude Code's **own** contract with its child processes (e.g., cleanup of Bash-tool subprocesses). Neither party owns this; it is Claude Code's, and both sides defer to it.

## 2. Direction of authority and the non-import rule

The seam is crossed in exactly one legal way: **subprocess invocation**. Tessera never imports Bootstrap modules into its own process. This is the load-bearing isolation property that lets the protocol be upgraded without Tessera-side import-compatibility breakage, and it is a contract-level guarantee, not a Tessera implementation detail.

- Tessera → Bootstrap: shell-out to the protocol CLI (`bootstrap-interview …`, `bootstrap-install …`) as a subprocess. In-process `resolve_config` or any `import bootstrap` / `from lib.installer` / `from lib.interview` is a **contract violation**.
- Tessera → Claude Code: shell-out to `claude -p` as a subprocess.
- Bootstrap → Tessera: no direct call. Bootstrap communicates only by (a) exit codes and captured stdout/stderr from its CLI, and (b) the on-disk artifacts it writes under `.claude/`.

Rationale is fixed here so neither PRD has to relitigate it: the subprocess boundary is what makes the two projects independently versionable. Collapsing it (for performance or convenience) is the canonical example of forking the seam.

## 3. Invocation surface

### 3.1 Claude Code dispatch invocation

Tessera dispatches a task by spawning `claude -p` as a subprocess in the project's working directory.

**Permitted / required:**

- `claude -p` — headless (print) invocation. The per-iteration mechanism.
- `--output-format json` — structured output. Tessera's result-parsing contract (§4) depends on this.
- `--json-schema <schema>` — structured-output schema pin, where used.
- An explicit approved **tool allowlist** passed per dispatch. The v1 default allowlist **excludes `Bash`** (threat-surface reduction). This exclusion is a seam guarantee because it bounds what a dispatched subprocess can do; it is stated here, not left to Tessera-internal convention.
- **[seam 1.0.0 errata, logged (TF-01)] Per-dispatch cap flags: `max_budget_usd` and `max_turns`** (CLI `--max-budget-usd` / SDK `ClaudeAgentOptions` equivalents). Tessera MAY pass these per dispatch; both are gate-*strengthening* — they can only bound a dispatch, never widen it, so their presence adds no attack surface. `max_budget_usd` is set from the remaining §12.4 `max_cost_usd` headroom (conservatively rounded down); `max_turns` from Tessera's `dispatch_max_turns` per-project config (nullable; null = SDK default). Recall the §5 caveat: hitting `max_turns` can suppress `Stop`-class hooks, so cap-hit reconciliation is caller-side. *Errata rationale: these flags were introduced by the Tessera v0.5.0 absorption fold without seam declaration (fold-review TF-01, pattern P-7); added here as an in-version errata because seam 1.0.0 is `status: draft` with no adopted consumers — logged per the §31.5.8-precedent discipline rather than silently amended.*

**Forbidden:**

- `--bare` is **NOT used, ever.** `--bare` bypasses the hook suite, and the hook suite *is* the Bootstrap Protocol's enforcement layer. Using `--bare` would silently void every gate guarantee this contract exists to preserve.
- **[seam 1.0.0] The generalized prohibition (SDK era).** When the dispatch runs via the Claude Agent SDK rather than raw `claude -p`, the `--bare` line generalizes to a **config-construction invariant**: the dispatch is **`permissionMode: "dontAsk"`**, and **never `bypassPermissions`, `acceptEdits`, or `auto`** as the dispatch mode. Rationale, fixed here so neither PRD relitigates it:
  - `bypassPermissions` is the SDK-era successor to `--bare`: it auto-approves every tool, `allowed_tools` does not constrain it, and **subagents inherit it non-overridably** — a single parent-level `bypassPermissions` grants full autonomous system access to every subagent. (Gate hooks still run under it, so gates aren't *voided*, but the posture violates human-approval-before-autonomous-action.)
  - `auto` mode is **model-classified** approval — a gate the model decides is not a deterministic gate; it must never sit in front of a Bootstrap gate.
  - `dontAsk` is the correct fail-closed headless posture: anything not pre-approved is denied, and `canUseTool` is never silently relied upon.
- **Gate hooks must be present.** Whatever constructs the dispatch (CLI flags or `ClaudeAgentOptions`) MUST carry the Bootstrap gate hooks as `PreToolUse` denies. A `PreToolUse` deny runs first in the permission-evaluation order and **applies even under `bypassPermissions`** — this is the mechanical guarantee that "consume gates as-emitted" (§6) rests on. Removing the gate hooks is the SDK-era equivalent of `--bare` and is equally prohibited.

**Runtime floor:**

- **[seam 1.0.0] Minimum Claude Code runtime ≥ v2.1.210** (pinned in `binds`). Below this, a `PreToolUse` gate-hook timeout is reported to the model as a user rejection and an unattended session stalls; at ≥ v2.1.210 the timeout fails closed (tool call blocked, model gets a timeout error). Worktree-entry consent (≥ v2.1.206) and exact-match hyphen matchers (≥ v2.1.195) are subsumed by this floor.

**Session isolation:**

- Queue-mode dispatches start each task with a **fresh context window**. No `--continue`, no `--session-id` carrying a prior session across tasks. Each task's first turn is a fixed system prompt + task content, not a growing continuation.

### 3.2 Bootstrap Protocol CLI invocation

Tessera invokes the protocol only through these subprocess entry points:

| Command | Purpose | Notes |
|---|---|---|
| `bootstrap-interview synthesize` | Produce `bootstrap.config.yaml` and install intent from a pre-populated interview file | Invoked with a complete ANSWERS block; never interactively. See §7.3. |
| `bootstrap-interview synthesize --validate-only` | **[1.2.0 row-upgrade, A-pin] IMPLEMENTED at the 2.0.0 pin (IC-1, `1fa5bb6`)** — parses the interview, runs `resolve_config`, reports invariant violations to stderr, writes no output file, exit code reflects validity (0 valid / non-zero invalid). | Replaces the 1.1.0 interim path (synthesize→tmp + `--dry-run`/`--print-config` — both remain real and permitted). Consumers upgrade §10.3/§10.4-class validation flows to the single call; Tessera does so in the same 1.2.0 re-pin pass. *(1.1.0 history: this row was a pin-correction — the flag was fictional at the 1.9.0 pin, IG-01.)* |
| `bootstrap-install --print-config` | **[1.1.0, IG-07]** Resolve + echo the effective config without installing. | The validation workhorse for the interim path above. |
| ~~`bootstrap-install --force`~~ | **[1.1.0, IG-07] PROHIBITED in Tessera's automated path.** | Exists in the CLI; force-overwrite defeats the §7.2 hand-edit preservation contract. Human-CLI use only. |
| ~~`retrofit-interview`~~ | **[1.1.0, IG-10] NOT a permitted Tessera entry point at this pin.** | The Retrofit track (v1.6.2) exists on main; Tessera scope excludes it (Tessera NG12). |
| `bootstrap-install` | Install the `.claude/` workspace tree | Non-zero exit ⇒ loud failure, captured stdout/stderr. |
| `bootstrap-install --dry-run` | Produce a tree for hook-set verification without committing changes | Used by the compatibility job (§8). |
| `bootstrap-install --uninstall` | Remove/roll back an install | Recovery path per protocol runbook. |

**Never invoked by any default Tessera code path:** `bootstrap-interview analyze`, `bootstrap-interview interactive`. These remain available to a human as CLI escape hatches but are not part of Tessera's automated seam. A future addition of a new *automated* entry point is a `seam_version` change (§8).

### 3.3 SDK gate-module builder API

**[seam 2.0.0 — the §9 deferred surface, now live.]** At the substrate release (protocol 2.1.0, IC-5), the `gate_substrate: "sdk-callable"` enforcement path is carried by a protocol-emitted, project-resident Python module at `.claude/sdk_gates/gates.py`. Its public builder is a **seam surface** — Tessera's own subprocess dispatch runner (§9 "Runner ownership — Tessera-owned") imports it *inside the dispatch subprocess only* (§2 non-import rule; never in Tessera's core process) to construct the Agent SDK hook configuration.

**Locked builder signature (resolved at this bump from the §9 proposal):**

- `build_hooks(config: dict) -> dict` — the module's **sole public builder**; `__all__` exports only `build_hooks` (the module also defines two module-level constants, `GATES` and `RESOLVED_CONFIG`, carried for the SEV-1 `build_hooks(RESOLVED_CONFIG)` path; every callable other than `build_hooks` is underscore-private). Takes the resolved project config (the dict the protocol resolves from `bootstrap.config.yaml`) and returns the Agent SDK hooks mapping, shape `{"PreToolUse": [HookMatcher(...), ...], "PostToolUse": [...]}` (event name → list of `claude_agent_sdk.HookMatcher`).
- *Signature resolution note:* §9 v1.1.0 **proposed** `build_hooks(config: dict) -> dict[str, list[HookMatcher]]` and stated "any deviation is a seam-visible edit to this entry." The shipped module (protocol 2.1.0+, `lib/sdk_gates_template.py`) declares the return annotation as the bare `dict`; the runtime return **shape** is identical to the proposal and is documented in the emitted module header. This bump therefore locks the seam to the shipped reality — symbol name `build_hooks`, parameter `config: dict`, return `dict` whose contents are the event→`HookMatcher`-list mapping — recording the annotation narrowing as a resolved deviation, not an outstanding one.
- **Coverage.** `build_hooks` wires the seven **security-critical** gates enabled for the resolved config, across two events: **six `PreToolUse` denies** (`secrets-gate`, `spec-gate-commit`, `dependency-gate`, `test-gate`, `eval-gate`, `tdd-gate` — mapping to `Read|Write|Edit`/`Bash`/`Write` matchers) plus **`format-lint-gate` as a `PostToolUse` advisory** (matcher `Write|Edit`, non-blocking — it returns a `systemMessage`, never a deny; the "deny shape" guarantee below applies only to the six blocking gates). It does **not** carry the autonomy-critical hooks (`drift-detector-loop-cooperation`, `iteration-summary-enforcement`) or the observability/alarm hooks (`ci-mirror`, `cost-log`, `drift-detector`, the `*-alarm` hooks); those remain shell-emitted regardless of substrate (§7.2).

**Behavioral guarantees carried onto the wire (from §9):** no I/O at import time; no network I/O ever; refusals return the structured `PreToolUse` deny shape (§4.1 / §6.2) with reason strings semantically equivalent to the shell gates'. Loading the module into any consumer core process is a contract violation; it is loaded only inside the subprocess dispatch runner, which remains the seam crossing.

**Emission vs activation.** `.claude/sdk_gates/gates.py` is emitted by **every greenfield install** and is manifest-tracked security-critical — its presence is **not** conditional on `gate_substrate`; the shell `hooks/*` scripts and `gates.py` **coexist** in a greenfield tree, both manifest-tracked and security-critical. (The retrofit overlay is the one path that drops `gates.py`.) `gate_substrate` is a **state-file declaration** (`.bootstrap-state.json`; `"shell"` by default, `"sdk-callable"` grantable only behind the IC gate), **not** a re-wiring switch — the protocol's emitted `settings.json` **always** wires the shell `hooks/*` scripts as its `PreToolUse`/`PostToolUse` hooks, and never references `gates.py`, regardless of `gate_substrate` (verified: `_settings_json` has no `gate_substrate` branch). So the two carriers activate on **different runners**: the protocol's own `settings.json` gates cover a direct/human `claude` run, while the SDK carrier activates only when **Tessera's dispatch runner imports `build_hooks`** inside the subprocess (line above). `gate_substrate` records which substrate Tessera is entitled to dispatch under; it is never an emit-XOR, and it does not change any protocol-emitted bytes.

## 4. Result-parsing contract (Claude Code headless JSON)

Tessera reads the following fields from `claude -p --output-format json` output. **Field names are pinned to the declared Claude Code compatibility range** (§8.3); the runbook's compatibility matrix records the exact key per supported version.

### 4.1 Pinned field names

| Contract field | Meaning | Pin note |
|---|---|---|
| `total_cost_usd` (on the SDK `ResultMessage`) | Final per-dispatch cost. **[seam 1.0.0 MAJOR change]** Was `cost_usd` (raw `--output-format json` key); now read from the Agent SDK's `ResultMessage.total_cost_usd`, present on **both success and error** results. **This field is a client-side ESTIMATE, not authoritative billing** — the SDK computes it from a bundled price table. Per Anthropic's docs it must not drive financial decisions or user billing. Tessera's budget caps consume it as a **safety governor, not a bill**; authoritative figures (if ever needed) come from the Usage and Cost API. **This is why the change is MAJOR:** Tessera §12.4 previously treated the field as the authoritative per-dispatch value; that consumption must be re-validated (`cost_estimated` framing retained/strengthened), and `binds` was re-cut. |
| `permission_denials` / structured `PreToolUse` deny output | Denial records emitted when the model attempted an action a hook/permission refused. **[seam 1.0.0]** Under the SDK, a refusal surfaces as a structured `{permissionDecision: "deny", permissionDecisionReason: <string>}` (+ optional `systemMessage` to the user). | Consumed per §4.3; drives a **non-failing** notice, scoped to the hook-supplied reason string. Tessera relays the reason faithfully; it does not reinterpret it. |

Any additional field Tessera consumes in a future `seam_version` must be added to this table with its pin note. A field Tessera reads that is *not* in this table is a contract gap and a CI failure (§8.2).

### 4.2 Cost semantics and the absence case

- When a dispatch completes normally, `total_cost_usd` is present on the `ResultMessage` (as a client-side estimate — §4.1).
- When a dispatch is killed before a final `ResultMessage` (hard kill, timeout, OOM, etc.), the value may be **absent**. The contract's only obligation is to make the absence detectable; how Tessera compensates (its wall-time conservative-estimate fallback and the `cost_estimated` flag) is **Tessera-owned policy**, deliberately not specified here. Note the SDK provides `total_cost_usd` on **error** results too, so many killed-mid-run cases still yield a (partial, estimated) value.

### 4.3 `permission_denials` consumption

- The array, when present, is surfaced by Tessera as a **non-failing notice** in the dispatch view.
- Tessera's surfacing is **scoped to the hook-supplied reason string** — Tessera does not reinterpret, re-rank, or synthesize denial semantics beyond what the hook emitted. This keeps the gate's voice authoritative and Tessera a faithful relay.

## 5. Stream-event semantics

Tessera consumes the Claude Code JSON event stream (captured to `dispatches/<dispatch-id>/output.jsonl`). The following events have contract-level meaning:

| Event | Consumed meaning | Tessera obligation |
|---|---|---|
| `system/init` | Session start; carries `plugin_errors`. | If `plugin_errors` is non-empty, surface it. A plugin/hook load error means the enforcement layer may be degraded — this is fail-loud territory, not a warning to swallow. |
| `api_retry` | Claude Code is retrying an upstream API call. | Informational; may inform rate-limit-aware handling. Not a failure by itself. |
| **`PreCompact`** (hook event) **[seam 1.0.0]** | Fires before the SDK compacts (summarizes) conversation context. | Archive/flush the full transcript before summarization, so nothing observable is silently lost to compaction. Available in both Python and TS SDKs. This is the native hook point the shell skeletons lacked. |

**[seam 1.0.0] `max_turns` caveat.** `Stop`/`SessionEnd`-class hooks may **not fire** if the session ends by hitting `max_turns`. Therefore a *required* audit/flush obligation MUST NOT live only in a `Stop` hook — pair it with `PreCompact` or a Tessera-side reconciliation on dispatch completion. The observability guarantee is contract-level; the specific placement is the consuming side's responsibility, but this failure mode is called out so it isn't rediscovered in production.

**`plugin_errors` is the seam's early-warning line.** Because the hook suite is the enforcement layer, a plugin/hook that failed to load is a silent-gate-bypass risk. The contract requires that a non-empty `plugin_errors` on `system/init` is observable to Tessera; Tessera's exact response (warn vs. refuse) is its own policy, but the *observability* is a contract obligation.

Events not listed here may exist in the stream; Tessera ignores unknown events without error (forward-compatibility), but MUST NOT depend on an unlisted event's semantics until it is added to this table under a new `seam_version`.

## 6. Gate-emission-as-consumed

"Consume gates as-emitted" needs a concrete referent, given here. This section describes the **shape** of a refusal as Tessera sees it — not the gate's internal logic.

### 6.1 The core rule: no per-project gate exceptions

Bootstrap gates are consumed exactly as emitted. **Tessera cannot grant a per-project exception to a gate** (e.g., a secrets-gate override) without forking the protocol, which violates this contract. The security asymmetry principle applies: a bounded-loud refusal is preferred over an unbounded-silent override hole. If a gate refuses, the dispatch does not proceed; Tessera surfaces the refusal, it does not suppress it.

The **one** permitted exception mechanism is not a gate override at all: it is the operator-acknowledged **security-critical hand-edit** flow (§7.2), which is a change to a *manifest-tracked file's digest*, audited and loud — not a runtime gate bypass.

### 6.2 Refusal shape

A gate refusal surfaces to Tessera as a non-zero result on the relevant subprocess path, with the gate's reason available as an emitted string. Tessera's obligations:

- Relay the gate's reason string faithfully (do not paraphrase away its meaning).
- Do not advance the dispatch state past the refusal.
- Audit-log the refusal.

The enumerated refusal *reason codes* on Tessera's side (e.g., `protocol-version-drift`, `halt-sentinel-present`, `commands-confirmation-pending`) are Tessera-owned and live in the Tessera PRD's state-machine table; they are not duplicated here. This contract only guarantees that a gate refusal is *observable and non-suppressible*.

## 7. Workspace-artifact contract

The `.claude/` tree and a small set of sentinels are a shared surface. Names, locations, and digest semantics below are contract-level; either side changing them is a `seam_version` change.

### 7.1 Manifest and digest integrity

- The protocol writes `.installer-manifest.json` (digest-based) and `.bootstrap-state.json` (which records `bootstrap_protocol_version`).
- Every manifest-tracked file has an installer digest. Tessera **never modifies** any file whose path appears in the manifest (its own writes stay outside the manifest set).
- A file whose on-disk digest differs from its manifest digest is a **hand-edit**, handled per §7.2.

### 7.2 Hand-edit classes (shared semantics)

The protocol's L-1 contract permits operator hand-edits and preserves them across re-install. The seam distinguishes two classes:

**[1.1.0 pin-correction, IG-03]** The emitted hook set at the 1.9.0 pin (verbatim from `_hook_body`): `spec-gate-entry`, `spec-gate-commit`, `secrets-gate`, `test-gate`, `format-lint-gate`, `ci-mirror`, `cost-log`, `dependency-gate`, `tdd-gate`, `eval-gate`, `drift-detector`, `task-done-alarm`, `decision-required-alarm`, `drift-detector-loop-cooperation`, `iteration-summary-enforcement`. Three tiers:

- **Security-critical set** — `hooks/secrets-gate*`, `hooks/spec-gate-commit*`, `hooks/dependency-gate*`, `hooks/test-gate*`, `hooks/eval-gate*`, `hooks/tdd-gate*`, `hooks/format-lint-gate*`, `settings.json`, and **[seam 2.0.0] `sdk_gates/gates.py`**. *`spec-gate-entry` is deliberately excluded: it is warn-tier by the protocol's own entry-warn/commit-block split; the block-tier `spec-gate-commit` is the critical one.* **[seam 2.0.0] `sdk_gates/gates.py` membership:** a greenfield install emits `.claude/sdk_gates/gates.py` **alongside** the shell `hooks/*` scripts (both manifest-tracked, both security-critical — presence is NOT conditional on `gate_substrate`; see §3.3 "Emission vs activation"). `gates.py` carries the seven security-critical gates above (six as `PreToolUse` denies + `format-lint-gate` as a `PostToolUse` advisory; see §3.3 "Coverage"), so a hand-edit there rewrites those gates' enforcement — hence the strictest tier. It does NOT carry the autonomy-critical hooks (below) or the observability/alarm hooks, which stay in their shell scripts regardless of the active substrate. Check 8 (§8.2) asserts the greenfield set (shell hooks + `gates.py`); the retrofit overlay, which drops `gates.py`, is the one exception.
- **[1.1.0] Autonomy-critical set (new middle tier)** — `hooks/drift-detector-loop-cooperation*` (implements the tier-3 hard-block inside autonomous modes) and `hooks/iteration-summary-enforcement*` (gates goal-mode halts). A digest mismatch here refuses **autonomous** dispatch only; interactive dispatch proceeds with a warning. A digest mismatch on any of these means dispatch is **refused** until the edit is reverted or an explicit, audited per-project override is set (recording pre- and post-edit digests and an acknowledgement timestamp).
- **Non-security set** — any other manifest-tracked file. A digest mismatch is permitted and recorded as a legitimate operator hand-edit per the protocol's L-1 contract.

The membership of the security-critical set is a **contract-level list**: adding or removing a hook from it is a `seam_version` change, because it changes what "consume as-emitted" protects.

### 7.3 Synthesized interview file and provenance markers

- Tessera writes a `bootstrap.interview.md` with a **complete ANSWERS block** (no OPEN QUESTION markers) before invoking `synthesize`. The protocol's interview UI is never shown.
- Each answer carries a `source:` provenance marker, one of: `human-confirmed`, `inherited-machine-default`, `heuristic-suggested`, `PRD-derived`.
- **Forward-compatibility seam:** current protocol validation *ignores* the `source:` field. A future protocol version that validates or rejects it would break synthesize. The compatibility job (§8) exercises the pre-populated synthesize path *including* provenance markers on every pin bump; if a future version tightens preamble validation to reject the field, the pin bump fails and the two projects' authors coordinate before bumping. This is the explicit acknowledgement, fixed here rather than in either PRD alone.

### 7.4 Shared sentinels

**[1.1.0 pin-correction, IG-02] The 1.0.0 table was fictional against the 1.9.0 code.** *(Historical: at the 1.9.0 pin, root-level shared sentinels did not exist in the protocol and `.halt-hard` did not exist at all.)* **[1.2.0 row-upgrade, A-pin] IC-2 landed at the 2.0.0 pin (`1fa5bb6`): root sentinels are now protocol-honored shared surface with permanent dual-honor of the queue-scoped sentinels. The table below reflects the 2.0.0 pin.** The root sentinels' non-committability is installer-managed via a marker-delimited block in the project-root `.gitignore` (autonomous installs; operator content outside the block is never touched).

| Sentinel | Location (as emitted at the 2.0.0 pin, `1fa5bb6`) | Owner/honored by | Meaning |
|---|---|---|---|
| `.halt` | `<project-dir>/.claude/queue/` | Protocol `auto.sh` (queue runner) | Graceful queue stop. **Dual-honor is permanent:** the queue-scoped path remains honored alongside the root sentinels; Tessera continues to write/watch both. |
| `.resume` | `<project-dir>/.claude/queue/` | Protocol `auto.sh` | Operator resume request. |
| `.run-active` | `<project-dir>/.claude/queue/` | Protocol `auto.sh` + Tessera (observes) | A queue run is active. |
| `.loop-active-<task-id>` / `.goal-active-<task-id>` | `<project-dir>/.claude/sessions/` | Per-task wrappers | A per-task loop is active. |
| `.halt` (project root) | `<project-dir>/` | **Shared from the 2.0.0 pin (IC-2):** protocol wrappers (`auto.sh`/`loop.sh`/`goal-loop.sh`) + Tessera | Graceful stop at the next boundary. |
| `.halt-hard` (project root) | `<project-dir>/` | **Shared from the 2.0.0 pin (IC-2):** protocol wrappers + Tessera | Immediate wrapper exit. The wrapper never signals in-flight `claude -p` — killing processes remains the caller's job (Tessera's §12 machinery on its dispatches). |

- Both layers honor the shared **per-project** sentinels. A user running the protocol's `auto.sh`/`loop.sh`/`goal-loop.sh` directly can halt that project via the shared per-project sentinel.
- **Global** sentinels (`~/.tessera/.halt`, `~/.tessera/.halt-hard`) and the per-project **budget** sentinel (`.halt-budget`) are **Tessera-only** — the protocol's bash skeletons are single-project-scoped and have no global concept. These are listed here to mark the boundary: they are explicitly *not* part of the shared surface, and the protocol is not expected to honor them.

Sentinel filenames and locations are contract-level. On startup, on-disk sentinels are authoritative (Tessera's SQLite mirror is rebuilt to match) — but that reconciliation is Tessera-internal; the contract only fixes the names and the per-project sharing scope.

### 7.5 Protocol skeletons are not the production path

`.claude/auto.sh`, `loop.sh`, `goal-loop.sh` are protocol-emitted skeletons. Tessera does **not** treat them as its production dispatch path; it dispatches `claude -p` directly under its own kill-switch coverage. The skeletons remain valid for direct human use (e.g., SEV-1 incident response when Tessera is down) via the shared per-project sentinels. This division is contract-level so neither side assumes the other is driving the loop.

## 8. Protocol-pin compatibility

### 8.1 The pin

Tessera pins to a specific Bootstrap Protocol commit hash, declared in Tessera's dependency manifest. A given Tessera release declares both a protocol pin and a `seam_version` it targets. A protocol commit declares which `seam_version`(s) it satisfies. The pin bumps only after the compatibility job (§8.2) passes.

### 8.1a The `binds` compatibility set (synchronization ledger)

The frontmatter `binds:` block is the **single authoritative statement that the foundational documents are in sync**. Synchronization is a *declared, verified relationship* — not a coincidence of matching version numbers. The three documents (Tessera PRD, Bootstrap Protocol, seam contract) version independently and are never expected to share a number; `binds` is where their agreement is recorded.

**Directional rule — the seam binds, the PRDs pin:**

- The **seam contract binds**: `binds` declares the version *ranges* of each consumer that satisfy this `seam_version`.
- Each **PRD pins**: each consuming document carries a `targets_seam_version:` field naming the single `seam_version` it was written against.
- **On disagreement, CI fails** (§8.2, check 0), and this artifact is authoritative about the *relationship only* — never about either endpoint's internals. This is the single tie-breaker for any version dispute: it is resolved at the seam, never by editing two documents into cosmetic agreement.

**Consistency invariant:** a consumer's `targets_seam_version` MUST equal this artifact's `seam_version`, AND that consumer's own declared version MUST fall inside its `binds` range. Both halves are required; satisfying one without the other is an out-of-sync state and a CI failure.

**Bump coupling:**

- Editing a `binds` range is **at least a MINOR** seam bump (the compatibility set changed).
- A `binds` edit that *drops* a previously-satisfying version (narrows a range such that a document that used to be in-sync no longer is) is a **MAJOR** seam bump — it is a breaking change to the relationship, and forces every consumer to re-validate and re-cut its pin.
- A seam MAJOR always forces a `binds` re-cut and re-validation of all pins; a Tessera or Bootstrap bump that does not cross the seam does not.

### 8.2 The compatibility job (contract-mandated)

A CI job — canonically `protocol-compatibility` — runs on **every protocol version bump** and **every Tessera release**, and is **required for merge**. It verifies the seam declared in this document:

0. **`binds` resolution (the sync assertion) [rewritten at seam 1.0.0 for the re-cut key set (D-04)].** Each consumer's declared version resolves inside its `binds` range (§8.1a), AND each consumer's `targets_seam_version` equals this artifact's `seam_version`. Both halves must hold; a failure here is the designed out-of-sync signal (P-5) — a deliberately-failing check 0 during a consumer-fold window is the *honest* state, and a passing check 0 immediately after a MAJOR is itself suspicious. Concretely, for every key in `binds`:
   - `tessera_prd`: parse `prd_version`, assert it satisfies the range; assert `targets_seam_version == seam_version`.
   - `bootstrap_protocol`: **two-phase assertion — phase two operative since 1.2.0.** The key binds `2.4.0 @ 251f82ff4795a2c7e50fe62baf8b37ef4cc2f99c` **[re-pointed at seam 2.0.0; was `2.0.0 @ 1fa5bb6`]**: assert **commit identity** (the pinned commit is the one named, agreeing across the four sites listed at the bind) *in addition to* the document version (the pinned commit's protocol document declares 2.4.0). State which phase applies in the CI job's output. *(Phase one — document-version-only, while the commit was `[TODO]` — applied through 1.1.0 and is retained here as the fallback semantics for any future re-pin window where a version is named before its commit exists.)*
   - `claude_agent_sdk`: assert the installed `claude-agent-sdk` package version satisfies the floor.
   - `claude_code_runtime`: assert the installed Claude Code CLI version satisfies the behavioral floor (fail-closed hook timeouts, worktree consent, matcher semantics).
   - `claude_code_json_schema_range`: assert the installed CLI version falls in a row of the §8.3 runbook compatibility matrix that this seam's §4.1 field pins were validated against.
   A key present in `binds` but not asserted here is a contract gap and itself a CI failure — this list MUST be updated in the same edit as any `binds` re-cut.
1. `bootstrap-interview synthesize` accepts Tessera's PRD frontmatter shape (`archetype`, `prd_tier`, `principles_ranked`), **including the `targets_seam_version` field** (TF-05: same forward-compat class as the §7.3 provenance markers — a future protocol version that rejects unknown frontmatter fields breaks the pin bump, and this check is what catches it).
2. The pre-populated synthesize path is accepted **including `source:` provenance markers** (§7.3).
3. `bootstrap-install --dry-run` produces a tree whose hook set matches Tessera's expectation for the declared archetype.
4. The shared sentinel filenames and locations (§7.4) are unchanged.
5. `resolve_config` invariants are unchanged: `queue ⇒ loop | goal` (enforced at config, retrofit, and file levels — verified against `defaults.py`/`installer.py`); archetype enum (`cli|library|service|fullstack|mobile|data-ml|ai-agent|platform|other`) — **enforced** (`resolve_config` rejects an out-of-enum archetype). `prd_tier` value set (`micro|standard|full`) **[seam 2.0.0, re-verified at this rebase — the "[re-verify at rebase]" flag is now resolved]**: this is a **documented value set, NOT a `resolve_config`-enforced enum** — empirically, `prd_tier: <bogus>` resolves with no error (`defaults.py` carries a `"standard"` default and `prd_heuristics.py` a `TIER_ORDER` for *proposing* a tier, but neither validates the field at resolve time; the "tier floors" claim corrected at 1.1.0 was likewise unbacked). Check 5 therefore asserts the archetype enum as a hard invariant and treats `prd_tier` as advisory; hardening it to a rejected-on-invalid enum is a Bootstrap-side change gated by the `defaults.py` freeze and is NOT assumed here.
6. The result-parsing field pins (§4.1) resolve against the declared Claude Code compatibility range.
7. The stream events (§5) resolve with their declared meaning.
8. The security-critical AND autonomy-critical hook sets (§7.2) are present and match the contract lists. **[seam 2.0.0]** A greenfield install carries BOTH the shell `hooks/*` scripts AND `.claude/sdk_gates/gates.py` — assert both present, manifest-tracked, and in the security-critical tier (their presence does not vary with `gate_substrate`; that field selects only the active carrier, §3.3). The autonomy-critical hooks (`drift-detector-loop-cooperation`, `iteration-summary-enforcement`) are always shell-emitted; assert those too. The one exception is the retrofit overlay, which drops `gates.py`; a retrofit install asserts the shell set without it.
9. **[1.1.0, IG-12] minyaml round-trip:** a Tessera-emitted config passes `bootstrap-install --print-config` with byte-stable field values — proving Tessera's canonical dumpers stay within the protocol's `minyaml.py` subset (plain scalars, simple lists/maps; no anchors, flow mappings, or folded scalars).
10. **[1.1.0, IG-04] Provenance-marker acceptance is tested, not assumed:** the pre-populated synthesize path with `source:` markers runs against the pinned code (marker handling is unimplemented upstream; acceptance-by-ignoring must be demonstrated at CI).

Any failure blocks the pin bump. A passing bump records a changelog entry noting the version transition and any adaptation required.

### 8.3 Claude Code compatibility range

Tessera's dispatch depends on `claude -p`'s CLI surface and JSON output schema. A startup version-detection check logs the installed Claude Code version; known-incompatible versions produce a startup warning. The compatibility matrix (which JSON key names and event names apply per Claude Code version) lives in the runbook and is updated on each Claude Code release. The field-name pins in §4.1 are resolved against this matrix.

### 8.4 What a `seam_version` bump is

Increment `seam_version` when any of the following changes:

- A new automated CLI entry point Tessera invokes (§3.2), or a change to invocation flags that are contract-level (`--bare` exclusion, `--output-format json`, the fresh-context guarantee).
- A field added to or changed in the result-parsing table (§4.1).
- An event added to or changed in the stream-event table (§5).
- A change to the shared sentinel names/locations/scope (§7.4).
- A change to the security-critical hook set membership (§7.2).
- A change to the provenance-marker set or the synthesize-file contract (§7.3).
- A change to the `binds` compatibility set (§8.1a): at least MINOR, or MAJOR if it drops a previously-satisfying version.

Changes that touch only gate internals or dispatch policy do **not** bump `seam_version` — by definition they are not the wire.

## 9. Deferred surface (constraints locked now)

Per project discipline, deferred interface surface has its constraints locked at deferral time, not left as TBD.

- **Ingress API surface (Tessera §15.1, v1.1).** When an inbound ingress trigger is added, it enters the seam as an *invocation source*, not a new gate bypass. Locked constraints: an ingress trigger MUST NOT dispatch unless the project separately opts in via `ingress_may_dispatch: true` (default `false`); ingress-originated dispatches are subject to every §6 gate and §7 sentinel exactly as human-originated dispatches are; provenance of an ingress-originated action is discriminated by the authoritative SQLite dispatch record, **not** by spoofable heuristics. When implemented, this becomes a `seam_version` bump adding an entry to §3.
- **Native checkpointing (Tessera §8.8, v1.1).** Deferred to avoid entangling the context-management surface with the dispatch seam. When added, any new stream events or session flags it introduces enter §3/§5 under a `seam_version` bump.
- **Routines / cloud ingress substrate.** Classified as ingress-trigger-only, never an execution substrate. If ever reclassified, it is a `seam_version` change *and* requires a threat-model entry finalized before the contract admits it.
- **SDK gate module — ✅ LANDED AT SEAM 2.0.0 (was deferred through 1.x).** *(The producing side's implementation plan called this "Milestone B"; non-normative.)* The SDK-callable gate substrate landed at **protocol 2.1.0** (IC-5, `gate_substrate: "sdk-callable"`) and is carried live by the `2.4.0 @ 251f82f` bind. The builder API is now a live wire surface at **§3.3**, and `.claude/sdk_gates/gates.py` is now in the **§7.2 security-critical set** — both entered the wire in this seam-2.0.0 MAJOR, exactly as the "When implemented" note below anticipated. The locked constraints below are **retained as the authoritative specification of that now-live surface** (they did not change on landing; §3.3 records the one signature-annotation resolution):
  - **Location & integrity.** The module lives at `.claude/sdk_gates/gates.py`, is manifest-tracked with an installer digest, and joins the **security-critical** hand-edit tier (§7.2) in the same release that emits it. Because §7.2 membership is contract-level, that addition is a `seam_version` event and lands with the substrate-release seam bump — it is *not* a silent extension. Under the `"sdk-callable"` substrate this one file carries the seven security-critical gates (§3.3 "Coverage": six `PreToolUse` denies + `format-lint-gate` `PostToolUse` advisory — not the autonomy-critical or observability hooks, which stay shell-emitted); its hand-edit consequence is accordingly the strictest tier, never non-critical.
  - **API surface — LOCKED at seam 2.0.0; see §3.3.** The module exposes **exactly one public builder**. The v1.1.0 proposal was `build_hooks(config: dict) -> dict[str, list[HookMatcher]]`; the shipped module declares `build_hooks(config: dict) -> dict` with the identical runtime return shape. §3.3 records this annotation narrowing as the resolved deviation and is the authoritative statement of the locked signature.
  - **Behavioral constraints.** No I/O at import time; no network I/O ever; refusals return the structured `PreToolUse` deny shape (§4.1 / §6.2) with reason strings semantically equivalent to the shell gates' messages, since §6.2 obliges consumers to relay them faithfully.
  - **Process boundary.** Loading this module into any consumer's **core process is a contract violation** (the §2 non-import rule; Tessera's AC-PROTO-001 class). The module is loaded only inside a **subprocess** dispatch runner. The subprocess boundary — not the module — remains the seam crossing.
  - **Runner ownership — DECIDED: consumer-owned (Tessera-owned) runner (owner decision, 2026-07-17).** Tessera ships its own subprocess dispatch runner; the module's builder API (above) **is** the §3 surface directly, and the protocol's emission stays module-only (the protocol does *not* emit a runner entrypoint). Rationale, fixed here so neither PRD relitigates it: this mirrors the existing §7.5 division — protocol skeletons are never the production dispatch path; Tessera drives dispatch under its own kill-switch coverage — and keeps the protocol's executable-emission surface from growing. The rejected alternative (a Bootstrap-emitted runner, which would have added a new §3.2 CLI row and a second security-critical executable) is recorded as considered-and-declined.
  - **When implemented — DONE at seam 2.0.0.** Entering the wire was a `seam_version` bump adding the builder API to §3 (now §3.3) and `sdk_gates/gates.py` to the §7.2 security-critical set. Per the pin choreography, both landed inside this **substrate-release seam MAJOR**: the `binds.bootstrap_protocol` re-point from the shell-conformant `2.0.0 @ 1fa5bb6` to `2.4.0 @ 251f82f` drops a previously-satisfying version (§8.1a; the 2.0.0 pin was an exact commit, not pre-widened), so the bump is MAJOR, not MINOR.

## 10. Changelog

- **v2.0.0 (MAJOR — substrate-release re-cut, 2026-07-21)** — The re-cut the 1.x line always owed (§9 "When implemented"; named as the owed MAJOR in the v1.2.0 entry and the Bootstrap v2.2.0 changelog head). **File renamed** `SEAM-CONTRACT-v1-2-0.md` → `SEAM-CONTRACT-v2-0-0.md` per the versioned self-naming convention (references updated in `.claude/specs/bootstrap-v2/requirements.md`, `docs/changelog.md`, `lib/installer.py`). **`binds.bootstrap_protocol` re-pointed** `2.0.0 @ 1fa5bb6` → `2.4.0 @ 251f82f` (PR #8 merge commit). Because the 2.0.0 bind was an EXACT commit pin (not a widened range, and the owner did not pre-widen at the 2.0.0 pin), the re-point **drops a previously-satisfying version → MAJOR** (§8.4). **SDK gate substrate entered the wire:** it landed at protocol 2.1.0 (IC-5, `gate_substrate: "sdk-callable"`) and is carried live by the 2.4.0 bind, so the §9 deferred surface is now live — the `build_hooks(config) -> dict` builder API joins **§3 as new §3.3**, and `.claude/sdk_gates/gates.py` joins the **§7.2 security-critical set** (it is emitted in every greenfield tree ALONGSIDE the shell hooks — both security-critical; `gate_substrate` is a state-file declaration, not a re-wiring switch — settings.json always wires the shell gates; the SDK carrier activates only via Tessera's runner importing `build_hooks`, per §3.3 "Emission vs activation" — and it carries the seven security-critical gates, six `PreToolUse` denies + `format-lint-gate` `PostToolUse` advisory, not the autonomy-critical or observability hooks). §8.2 updated in the same edit (check-0 `bootstrap_protocol` bullet re-pointed to the 2.4.0 SHA; check-8 asserts the greenfield shell+`gates.py` set, retrofit dropping `gates.py`). **Signature resolution:** §9's v1.1.0 proposal `-> dict[str, list[HookMatcher]]` is reconciled to the shipped `-> dict` (identical runtime shape) and locked in §3.3 — the deviation §9 flagged is now resolved, not outstanding. **Check-5 flag resolved:** the "[re-verify at rebase]" `prd_tier` note is closed — the enum is a documented value set, NOT `resolve_config`-enforced (empirically verified; only the archetype enum is enforced). **Intermediate versions carry no seam surface:** 2.1.0→2.2.0→2.4.0 added no field/sentinel/tier/invocation change (2.4.0's new files land §7.2 non-critical), so one re-point straight to 2.4.0 needs no intermediate pins. **Consumers must set `targets_seam_version: 2.0.0`** and re-point `bootstrap_protocol` to `251f82f` across all four check-0 sites. **`tessera_prd` range carried forward unchanged** (`>=0.5.0,<0.6.0`): the Tessera version that absorbs the substrate re-cut is a Tessera-roadmap fact not yet pinnable, so the floor is not invented — the relationship is KNOWINGLY UNSATISFIED (P-5) until Tessera folds: check 0 fails on the `targets_seam_version` half (1.2.0≠2.0.0) while the carried-forward range half still PASSES (0.5.x remains in `>=0.5.0,<0.6.0`). Consequence worth flagging: re-pinning `targets_seam_version` alone greens the tessera_prd check even before any runner consumes `build_hooks` — check 0 does not mechanically assert substrate absorption, so that remains a consumer obligation until the owner re-cuts the `tessera_prd` floor to the absorbing version. **`claude_code_json_schema_range` remains `>=TBD,<TBD`** (open by design, Tessera-runbook referent — carried, not resolved). Open Bootstrap-side follow-up (not in this re-cut): the §8.1 "a protocol commit declares which `seam_version`(s) it satisfies" is still declared nowhere in code (a `SATISFIES_SEAM_VERSION` constant would close it).
- **v1.2.0 (MINOR — Milestone-A pin event, 2026-07-17)** — Protocol 2.0.0 pinned by commit: `binds.bootstrap_protocol` = `2.0.0 @ 1fa5bb615e5f5102bb4108b79c944c635d6a3167` (merge of PR #5 into Bootstrap `main`), upgrading §8.2 check-0 from document-version identity to **commit identity** across the four agreement sites (this bind, Tessera `pyproject.toml`, PRD frontmatter `target_protocol_pin`, PRD §9.7). Row upgrades (both §8.4 triggers, planned by the BR-01 choreography): §3.2 `synthesize --validate-only` upgraded to real (IC-1); §7.4 root sentinels (`.halt`/`.halt-hard`) upgraded from Tessera-only to protocol-honored **shared surface** with permanent dual-honor of queue-scoped sentinels (IC-2), non-committability installer-managed via the root-`.gitignore` marker block. Also observable from 2.0.0: the state file gains `gate_substrate` (`"shell"` at this pin; `"sdk-callable"` installer-refused until the IC gate exists) — normative consumption lands via Tessera AC-PROTO-016 (BR-03). Classified MINOR: the commit qualification completes a previously-TODO pin (no adopted version dropped); the row upgrades add capability without removing any. Consumers re-pin `targets_seam_version: 1.2.0` — Tessera does so in the same pass, upgrading its §10.3/§10.4 validation flow to the single-call form. *(In-version correction, same day: the title heading, the `binds_note` commit-TODO line, and the §8.2 check-0 `bootstrap_protocol` bullet were swept to describe the landed pin rather than the pre-pin state — a descriptive correction per the DR-03 heading/prose-staleness discipline, not a wire change, so it rides inside 1.2.0 with no bump.)* *(Second in-version correction, same day — TODO closures from the Milestone-B verify-first pass: `claude_agent_sdk` floor resolved from the provisional `>=0.2.114` ceiling-as-floor to the feature-justified `>=0.1.60` (earliest release with mature PreToolUse deny shape + `dontAsk` in PermissionMode + honored `setting_sources=[]`; verified at the SDK changelog tags), and the `claude_code_runtime: >=2.1.210` floor confirmed against the official Claude Code changelog. Both were `[TODO: confirm/replace]` completions — resolving a provisional value to its verified value tightens the floor but adds no new binds key and changes no field/sentinel/tier, so it is not a §8.4 trigger and rides inside 1.2.0. The `claude_code_json_schema_range` TODO remains open by design — it is a Tessera-runbook matrix referent, out of this artifact's resolution scope.)*
- **v1.1.0 (MINOR — reality-corrections + additions)** — Main-branch reconciliation (`IMPLEMENTATION-GAP-ANALYSIS.md`). Pin-corrections of fictional 1.0.0 declarations: §3.2 `--validate-only` does not exist at the 1.9.0 pin (IG-01; real path = synthesize→tmp + `--dry-run`/`--print-config`); §7.4 sentinel paths corrected to the emitted `.claude/queue/`-scoped reality, root sentinels marked Tessera-only-until-IC-2, `.halt-hard` marked nonexistent in the protocol (IG-02); §7.2 hook set corrected to the 15 emitted names + new autonomy-critical tier (IG-03); check 5 tier-floor claim corrected (IG-05). Additions: `--print-config` pinned, `--force` prohibited, `retrofit-interview` explicitly not-permitted (IG-07/IG-10); checks 9–10 (minyaml round-trip, provenance-acceptance-at-CI). Classified MINOR, not MAJOR: nothing that ever existed is dropped — a consumer of a fictional pin cannot be broken by its correction; the only behavioral consumer obligation added is Tessera's dual-honor of queue-scoped sentinels, which Tessera v0.5.0 absorbs in the same pass. Consumers re-pin `targets_seam_version: 1.1.0`.
  - *In-version addendum (2026-07-17):* §9 gains the **SDK-gate-module deferred-surface entry** with locked constraints (location/integrity incl. the security-critical tier commitment, single-builder API proposal, no-import-time-I/O, subprocess-only loading). **Runner ownership DECIDED: consumer-owned (Tessera-owned)** — the protocol emits the gate module only, never a runner; the builder API is the §3 surface directly (mirrors §7.5; keeps the protocol's executable-emission surface from growing). Prompted by session adversarial review SR-01/SR-02: the substrate is contract surface and must be constraint-locked at deferral time per this document's own §9 discipline. Recorded as an in-version addendum (not a bump) because the addition is **deferred-surface-only** — §9 is not a §8.4 bump trigger, no wire surface or consumer obligation changes — and the seam is `status: draft`; the one declared consumer (Tessera PRD v0.5.0, `targets_seam_version: 1.1.0`) consumes nothing this entry touches, so its pin is unaffected — acknowledged explicitly rather than assumed. (The TF-01 §3.1-errata precedent is analogous in mechanism, but its "no adopted consumers" condition no longer holds at 1.1.0 and is not relied on; that errata was likewise recorded in-body, not as a second changelog entry — this addendum follows that placement.) `seam_version` remains `1.1.0`; the wire additions (§3 builder API, §7.2 tier membership) are explicitly deferred to the substrate-release seam MAJOR and do not enter the contract now.

- **v1.0.0 (MAJOR)** — Modernization fold. Triggered by two MAJOR events: (a) Bootstrap Protocol bumped to **2.0.0** (breaking — gate-substrate migration to the Claude Agent SDK *declared with locked constraints; implementation staged behind the main-diff reconciliation, per the protocol's conformance note* — plus native worktree direction and the model remap, which applies immediately), and (b) the §4.1 result-parsing field change from `cost_usd` (authoritative) to `ResultMessage.total_cost_usd` (**client-side estimate**), which invalidates Tessera §12.4's prior consumption. Both force a `binds` re-cut and consumer re-validation. Changes: §3.1 generalized the `--bare` prohibition to a config-construction invariant (dispatch mode `dontAsk`; `bypassPermissions`/`acceptEdits`/`auto` prohibited; gate hooks must be present as `PreToolUse` denies) and added a ≥ v2.1.210 runtime floor; §4.1 field-pin + estimate-semantics change; §5 added `PreCompact` and the `max_turns`-suppresses-Stop caveat. `binds` re-cut: `bootstrap_protocol` → `2.0.0` (TODO: exact commit), added `claude_agent_sdk` and `claude_code_runtime` pins, `tessera_prd` widened to `<0.6.0` for the fold window. Staged from `TESSERA-BOOTSTRAP-MODERNIZATION-TRACKER.md` (adversarial-reviewed). **Consumers must set `targets_seam_version: 1.0.0`.**
- **v0.1.0** — Initial extraction. Seam lifted out of the Tessera and Bootstrap descriptions into a standalone versioned contract. Sections 3–8 populated from the current Tessera PRD's emission surface (invocation, result-parsing pins, stream events, gate-as-consumed, workspace artifacts, protocol-pin/compatibility job). Deferred surface (§9) carries locked constraints for the ingress API, native checkpointing, and Routines. Frontmatter `binds` compatibility set added as the synchronization ledger, with §8.1a defining the directional pin rule (seam binds, PRDs pin) and §8.2 check 0 asserting the set resolves in CI. `binds` values are placeholders (`PIN-COMMIT-SHA`, `TBD` Claude Code range) pending reconciliation against Bootstrap main and the runbook compatibility matrix.

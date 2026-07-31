#!/usr/bin/env python3
"""Golden-output greenfield-invariance test (Deliverable 2).

Locks build_plan's content-tree output on fixture greenfield configs to a
stable digest. Any change that perturbs greenfield output - intended or not -
fails this test FIRST, before tests/test_installer.py's behavioral suite has
a chance to mask the regression behind an end-to-end success.

This gates the retrofit-installer work: a retrofit-mode extension that
accidentally changes a single byte of any greenfield-cfg-driven file fails
here. Pair with tests/test_installer.py (118 behavioral checks; this adds
byte-identity over and above those).

Run: python3 tests/test_greenfield_golden.py
Update (deliberate): GOLDEN_UPDATE=1 python3 tests/test_greenfield_golden.py
  prints new digests for paste into EXPECTED_DIGESTS / EXPECTED_ACTION_COUNTS.

Updating a digest is a freeze-exception decision. The diagnostic on failure
prints per-file digests so the regression is locatable to a single template.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

from defaults import resolve_config           # noqa: E402
from installer import build_plan              # noqa: E402
from minyaml import load_yaml                 # noqa: E402

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        if detail:
            print(detail)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
# Fixture A: the committed default bootstrap.config.yaml. The canonical
# greenfield baseline - every retrofit-installer change must keep this
# byte-identical.
with open(os.path.join(ROOT, "bootstrap.config.yaml")) as _fh:
    FIXTURE_DEFAULT = _fh.read()

# Fixture B: full autonomous ai-agent config with TDD required. Exercises
# every conditional template path the default does not: eval-gate, tdd-gate,
# loop.sh + loop-config.md, goal-loop.sh + goal-config.md, auto.sh +
# auto-config.md + queue/backlog.md, drift-detector-loop-cooperation,
# iteration-summary-enforcement, test-author skill. Retrofit-time freeze
# exceptions that perturb any optional surface get caught here.
FIXTURE_FULL_AUTONOMOUS = """project:
  name: golden
  archetype: ai-agent
  prd_tier: full
  cicd_opt_out: false
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: true
principles:
  tdd_policy: required
commands:
  test: "pytest -q"
  lint: "ruff check ."
  format: "ruff format ."
  typecheck: "mypy ."
  ci_local: "make ci"
"""

# Fixture C: DS-01 (v2.5.0) design steering ON with the optional advisory skill.
# Exercises the three flag-gated additions the default and full_autonomous
# fixtures never reach (both leave design_steering_enabled off, which is exactly
# why their digests prove off-by-default byte-identity):
#   .claude/steering/design.md
#   .claude/skills/design-review/SKILL.md
#   .claude/commands/design-review.md
# This fixture PINS the flag-on bytes so the three frozen artifact bodies (and
# their emission) cannot drift silently. Its digest is a deliberate golden
# ADDITION (GOLDEN_UPDATE protocol), NOT a re-baseline of an existing fixture.
FIXTURE_DESIGN_STEERING = """project:
  name: golden-design
  archetype: fullstack
  prd_tier: standard
  cicd_opt_out: false
design_steering_enabled: true
design_review_skill_enabled: true
principles:
  tdd_policy: "off"
commands:
  test: ""
  lint: ""
  format: ""
  typecheck: ""
  ci_local: ""
"""


# --------------------------------------------------------------------------- #
# Digest
# --------------------------------------------------------------------------- #
def plan_actions(yaml_text):
    raw = load_yaml(yaml_text)
    cfg, errs = resolve_config(raw)
    assert not errs, f"fixture must validate; got errors: {errs}"
    return cfg, build_plan(cfg)


def plan_digest_full(plan):
    """SHA-256 over (path, body, mode, kind) for every action, in plan
    order. Stricter than tests/test_installer.py's plan_digest (which omits
    `kind`) because retrofit-time additions could introduce new `kind`
    values and we want those to register here too."""
    h = hashlib.sha256()
    for a in plan:
        h.update(b"|PATH|")
        h.update(a["path"].encode())
        h.update(b"|BODY|")
        h.update(a["body"].encode())
        h.update(b"|MODE|")
        h.update(str(a["mode"]).encode())
        h.update(b"|KIND|")
        h.update(a["kind"].encode())
    return h.hexdigest()


def per_file_digests(plan):
    """Per-action digest for diagnostic output when the aggregate fails.
    Returns [(path, body_sha[:16], mode_octal, kind), ...]."""
    out = []
    for a in plan:
        body_d = hashlib.sha256(a["body"].encode()).hexdigest()[:16]
        out.append((a["path"], body_d, oct(a["mode"]), a["kind"]))
    return out


# --------------------------------------------------------------------------- #
# Expected (regenerate with GOLDEN_UPDATE=1)
# --------------------------------------------------------------------------- #
EXPECTED_DIGESTS = {
    # [2.0.0 R-0 freeze-exception] Re-baselined from the 1.9.0 digests for
    # exactly two byte classes (verified by HEAD-vs-worktree plan diff):
    #   1. settings.json `_generatedBy`: "protocol 1.9.0" -> "protocol 2.0.0"
    #   2. protocol-document citations in emitted hook/wrapper/config bodies:
    #      "BOOTSTRAP.md" -> "Bootstrap-Protocol-v2-0-0.md" (doc rename)
    # default: 12 files changed; full_autonomous: 21 files changed.
    #
    # [2.0.0 R-4 freeze-exception] full_autonomous re-baselined again for
    # IC-2 root-sentinel dual-honor (verified by plan diff; default fixture
    # untouched by R-4 - its digest is the R-0 value):
    #   1. loop.sh / goal-loop.sh / auto.sh gain the ROOT_HALT /
    #      ROOT_HALT_HARD guards (permanent dual-honor; wrapper never
    #      signals in-flight claude -p).
    #   2. ONE new action: project-root ".gitignore" managed block
    #      (kind gitignore_root, SR-17 decision (a)) - hence 65 -> 66.
    #
    # [2.0.0 R-6/AC-6-4 freeze-exception] full_autonomous re-baselined for
    # exactly one file: auto-config.md gains the Companion-mandated
    # queue-summary-synthesis surface (summary_synthesis_enabled: true,
    # summary_synthesis_model: haiku - Model Assignment Strategy table).
    # This is the AC-6-4 "only-if-diff" case: the subagent frontmatter
    # itself was assertion-only, zero diff, as the spec predicted.
    #
    # [2.0.0 Finding-1 freeze-exception (PR #5 review)] full_autonomous
    # re-baselined for the Phase 9.6 goal-config conformance fix - exactly
    # two files (loop.sh verified byte-identical):
    #   1. goal-config.md: judge_model -> evaluator_model (normative key,
    #      Bootstrap-Protocol-v2-0-0.md:1336); adds the missing
    #      evaluator_disagreement_threshold: 3 and
    #      evaluator_feedback_history_depth: 2; documents the
    #      unnamed-key Phase 9.6 items in comments.
    #   2. goal-loop.sh: dual-reads judge_model as a DEPRECATED alias,
    #      honoured only when evaluator_model is absent, loudly.
    #
    # [2.0.0 Finding-2 freeze-exception (PR #5 review)] full_autonomous
    # re-baselined for the Phase 9.7 .run-active race-safety fix - exactly
    # one file, auto.sh: CLAIMED guard (a refusing loser never deletes the
    # winner's sentinel), PID-liveness startup check (kill -0 + /proc),
    # operator-confirmed stale clearing with re-verify-before-clear, and
    # the O_CREAT|O_EXCL claim ("abort ... rather than overwriting").
    #
    # [2.0.0 freeze-exception no. 6 (PR5-04 hardening)] full_autonomous
    # re-baselined for exactly one file, auto.sh:
    #   1. liveness probe kill -0 + /proc -> portable `ps -p` (EPERM-immune,
    #      no Linux-only /proc dependence; cannot-determine still refuses);
    #   2. stale-clear prompt tty-guarded ([ -t 0 ]): non-tty auto-answers
    #      No BEFORE any stdin read (F-2 hang class closed);
    #      BOOTSTRAP_TEST_FORCE_PROMPT=1 is a documented TEST-ONLY override
    #      that can enable asking, never clearing.
    #
    # [2.0.0 freeze-exception no. 7 (adversarial-review fixes, auto.sh
    # race class)] full_autonomous re-baselined for two files:
    #   1. auto.sh: startup check-clear-claim now under flock (dual-'y'
    #      race closed); three-state pid_alive (ps -p self-probe, kill -0
    #      fallback, cannot-determine refuses); errexit-proof run_pid/
    #      run_start helpers; prompt read time-bounded
    #      (BOOTSTRAP_PROMPT_TIMEOUT, default 60s).
    #   2. .claude/.gitignore fragment: + queue/.run-active.lock
    #      (queue-gated, so the default fixture is unchanged).
    #
    # [2.0.0 freeze-exception no. 8 (adversarial-review fixes, gitignore
    # class)] BOTH fixtures re-baselined for exactly one file each:
    # .claude/.gitignore gains the ".bootstrap-state.json.pre-*" pattern
    # so migration backups (e.g. .pre-2.0.0) are never committable. (The
    # retrofit-mode root-.gitignore emission and the co-owned mode
    # preservation in the same commit are apply()/overlay-time - outside
    # this surface.)
    #
    # [2.0.0 freeze-exception no. 9 (adversarial-review fixes, goal-config
    # parse class)] full_autonomous re-baselined for exactly one file,
    # goal-loop.sh: goal_cfg_value() sanitizes operator-shaped edits
    # (inline comment, matching quotes, surrounding whitespace) before
    # exporting EVALUATOR_MODEL, survives sed failure under
    # errexit+pipefail, and logs the resolved value for observability.
    # [2.1.0 freeze-exception no. 10 (R-7/IC-5, SDK gate module)] BOTH
    # fixtures re-baselined for exactly ONE new action each - hence
    # 54 -> 55 and 66 -> 67: .claude/sdk_gates/gates.py (kind sdk_gates,
    # security-critical tier, seam §9). Diff-verified vs HEAD: zero
    # existing files changed, zero removed, in both fixtures.
    # [2.1.0 freeze-exception no. 11 (R-8/IC-6, native worktree routing)]
    # full_autonomous only, exactly TWO files (default fixture emits no
    # wrappers - verified unchanged): loop.sh / goal-loop.sh gain the
    # IC-6 native-routing instruction (claude -p --worktree, never
    # hand-rolled `git worktree add`) and the RETAINED-case documentation
    # on the claim/sentinel + cross-mode accounting block. Diff-verified
    # vs HEAD: zero added, zero removed.
    # [2.1.0 freeze-exception no. 12 (R-9/AC-9-5, release identity)] BOTH
    # fixtures re-baselined for exactly ONE file each: settings.json
    # `_generatedBy` "protocol 2.0.0" -> "protocol 2.1.0". Emitted doc
    # citations are untouched (the protocol document keeps its versioned
    # v2-0-0 self-name; 2.1.0 is code-side release identity). Diff-
    # verified vs HEAD: zero added, zero removed, no other file changed.
    #
    # [2.1.0 freeze-exception no. 13 (code-review fix pass)] Emitted-byte
    # changes from the adversarial-review fixes, diff-verified vs the
    # pre-fix head (zero files added/removed):
    #   default: .claude/.gitignore (+ sdk_gates/__pycache__ ignore) and
    #     .claude/sdk_gates/gates.py (async subprocess; tdd absolute-path
    #     normalization; scoped-pkg/verb dependency parsing; secrets
    #     negated-class over-match; str-coerced snapshot; build_hooks
    #     membership from config; skip-dot-dir corpus).
    #   full_autonomous: the above + loop.sh/goal-loop.sh (IC-6 worktree
    #     .git/info/exclude guidance; reworded dispatch echo).
    #
    # [2.1.0 freeze-exception no. 14 (re-sweep regression fixes)] Emitted-
    # byte changes from fixing regressions the no. 13 fixes introduced,
    # diff-verified vs the prior head (zero files added/removed):
    #   default: .claude/sdk_gates/gates.py (empty-_resolved_hooks
    #     fallback; pip[0-9.]* versioned-pip; per-line dependency scan;
    #     _proj().resolve()).
    #   full_autonomous: the above + loop.sh/goal-loop.sh (worktree
    #     .git/info/exclude comment de-mangled — the backslash line-
    #     continuation was collapsing the example).
    # [2.2.0 freeze-exception no. 15 (usage-limit coping + gap closure)]
    # Emitted-byte changes, diff-verified vs the pre-change head (zero files
    # added, zero removed; action counts unchanged at 55 / 67):
    #   default: settings.json `_generatedBy` "protocol 2.1.0" ->
    #     "protocol 2.2.0" (R6) — the ONLY default-fixture change; the 11
    #     emitted hook citations stay at v2-0-0 by design (RC-03 scoped to
    #     the touched files, so re-pointing hooks would break the "no bytes
    #     outside the named set" gate — same lag as no. 12).
    #   full_autonomous: the above settings.json bump + five files —
    #     loop.sh / goal-loop.sh (R2 dispatch flags --output-format
    #     stream-json --verbose; R3 usage-limit vs transient comment block;
    #     R4 judge-parity comment on goal-loop.sh only; RC-03 citation
    #     re-point v2-0-0 -> v2-2-0), loop-config.md / goal-config.md (R1
    #     three usage_limit_* keys; RC-03 re-point), auto.sh (R5 exit_reason
    #     enum + run-summary + AR2-01 runner rule + AR2-09c key-less posture;
    #     RC-03 re-point).
    # [v2.4.0 code fold — step 0 version stamp] settings.json `_generatedBy`
    # "protocol 2.2.0" -> "protocol 2.4.0" (PROTOCOL_VERSION bump). The ONLY
    # default-fixture change; zero files added/removed; count stable at 55.
    # PROTOCOL_VERSION is interpolated into exactly one emitted body
    # (templates.py _settings_json `_generatedBy`); the 11 emitted hook
    # citations and wrapper doc-filename citations stay at their existing
    # versions by design (byte-change surface kept minimal, per the fold's
    # "every other body byte-identical" claim).
    # [v2.4.0 code fold — GR2-03a] +1 unconditional file
    # .claude/steering/assumption-ledger.md (count 55 -> 56). No other body
    # moves; the added path is the only per-file digest change.
    # [v2.4.0 code fold — GR2-01] prose-only, count unchanged (56). Body
    # bytes move for CLAUDE.md (progress.md read-first note),
    # .claude/specs/INDEX.md (canonical progress.md template embedded), AND
    # .claude/agents/implementer.md (failed-approaches do-not-retry priming
    # instruction — added UNCONDITIONALLY in _agents, so it moves in BOTH
    # fixtures, not only full_autonomous). [Corrected post-review: the
    # original entry enumerated two movers where a main-vs-branch plan diff
    # shows three, so the aggregate re-baseline was absorbing a byte change
    # this record never named. Verified by diffing per-path bodies across
    # main and the branch for the default fixture.]
    # [v2.4.0 review-fix re-baseline] Emitted-byte changes from the
    # adversarial-review fixes, diff-verified vs the pre-fix head (zero files
    # added/removed; count stable at 56):
    #   .claude/steering/assumption-ledger.md — drift-threshold source-of-truth
    #     citation §6.D -> §6.E (§6.D is the hook security & correctness
    #     checklist; the thresholds live under §6.E "Audio alert system",
    #     *Drift detector specifics*), and the max-iterations pointer to
    #     .claude/loop-config.md is now phrased conditionally (that file is
    #     emitted only under loop mode, so the unconditional ledger was
    #     pointing a default install at a path absent from its own tree).
    #   .claude/specs/INDEX.md — the canonical progress.md template drops the
    #     protocol-doc coordinates ("PRD lines 806/1168", "PRD Phase 7 step 6,
    #     §6.D"): in an emitted project "PRD" denotes the operator's own
    #     product doc, so those resolved against the wrong document.
    # [v2.4.0 review-fix re-baseline, part 2 — frozen-source corrections]
    # Diff-verified vs the part-1 head; zero files added/removed, count 56:
    #   .claude/.gitignore — `settings.local.json` added. The emitted
    #     telemetry.md steers OTLP endpoint AND auth-header settings into that
    #     file and calls it "(gitignored)", but nothing ignored it: Claude Code
    #     auto-ignores it only when Claude Code itself creates it, while the
    #     doc says to write it BEFORE first launch. A hand-created file holding
    #     OTEL_EXPORTER_OTLP_HEADERS tokens was therefore committable by
    #     `git add .claude`, with the same paragraph conceding nothing scans
    #     for pasted secrets. The rule makes the doc's claim true rather than
    #     softening the doc. (Retrofit fragment gets the same entry; not a
    #     golden fixture.)
    # telemetry.md itself is NOT in either fixture (both leave the flag off),
    # so its threshold/purge corrections produce no golden movement — the
    # "off by default = invisible" property still holds. Those are covered by
    # test_installer.py's TEL-01 blocks, including a new frozen-source
    # equivalence pin.
    # [v2.4.0 review-fix re-baseline, part 3 — GR2-01 template ownership]
    # FIRST COUNT CHANGE OF THE REVIEW: 56 -> 57 (67 -> 69 for full). +1 file,
    # zero removed, three bodies move. Diff-verified vs the part-2 head:
    #   ADDED .claude/specs/progress-template.md — the canonical progress.md
    #     template, relocated out of INDEX.md into its own installer-owned
    #     file. INDEX.md is the operator-edited spec ROSTER (Phase 7.6 step 5
    #     directs replacing the placeholder row), so the hand-edit guard skips
    #     it on every real install: normative content parked inside it could
    #     never reach an upgraded workspace, while CLAUDE.md and the
    #     implementer body were updated to point at a section that would never
    #     arrive. Delivering it required --force, which destroys the roster.
    #     Separate file = separate ownership; it now updates cleanly.
    #   .claude/specs/INDEX.md — template body removed, replaced by a pointer
    #     plus an explicit "this file is yours to edit" note.
    #   CLAUDE.md, .claude/agents/implementer.md — pointers re-aimed at
    #     progress-template.md (a stale pointer here is the dangling-reference
    #     class this revision closes).
    # [v2.5.0 DS-01 — version stamp] settings.json `_generatedBy`
    # "protocol 2.4.0" -> "protocol 2.5.0" (PROTOCOL_VERSION bump, Step 7). The
    # ONLY default-fixture change; zero files added/removed; count stable at 57.
    # PROVEN by per-file diff (PV 2.4.0 vs 2.5.0): exactly ONE body moved,
    # .claude/settings.json. The design_steering feature itself contributes ZERO
    # to this fixture — design_steering_enabled is off here, so its build_plan
    # add is skipped; the pre-bump feature-complete tree already matched the old
    # digest (off-by-default byte-identity, verified before the bump).
    # [v2.5.0 freeze-exception no. 16] see the design_steering column for the
    # full record; default moves for byte classes 1 and 3 (12 files).
    # [freeze-exception no. 17 — upstream security/behavior fixes, 2026-07-28]
    # Source: docs/bootstrap-protocol-upstream-bugs-2026-07-28.md, a 6-lens
    # adversarial review that EXECUTED the emitted hooks against a real
    # v2.5.0 install. Re-baselined for these byte classes, all three fixtures
    # (**14** files on `default`; no steering doc, skill, command or agent
    # body moves, so every frozen twin stays byte-identical):
    #
    # [COUNT CORRECTED 2026-07-28, lens B finding 12.] This record said "16
    # files on `default`". The class enumeration was complete and honest; the
    # count was measured against the wrong thing. plan_digest_full hashes
    # PLAN ACTIONS, and `.bootstrap-state.json` and `.installer-manifest.json`
    # are written OUTSIDE the plan - so they are not in the digest this
    # record annotates, even though byte class 5 correctly names them as
    # places the version stamp lands. Measured inside the digest: 14 on
    # `default`, 18 on `full_autonomous` (16 and 20 on disk). 16 was the
    # figure from freeze-exception no. 16's `full_autonomous` row, copied
    # across. A count in a freeze record must state what the digest covers.
    #   1. Shared _HOOK_HEADER (touches EVERY hook): the jq-less fallback
    #      receives stdin on its own stdin instead of a 128 KiB-capped env
    #      var [P0-3a]; FAIL_CLOSED + hook_fail + an ERR trap so a blocking
    #      gate with no parser exits 2 rather than falling through to allow
    #      [P0-3b]; logging made non-fatal so an unwritable project dir
    #      cannot turn a block into exit 1 = tool-proceeds [P0-3c]; hooks.log
    #      rotation at 1 MiB [P3]; norm_cmd/cmd_has_verb/git_verb helpers
    #      [P1-4]; jq-parity for `false` -> empty [P3].
    #   2. drift-detector: the arithmetic RCE - `n=$(( $(cat "$ST") + 1 ))`
    #      executed command substitution from an agent-writable state file
    #      [P0-1] - plus session id read from the payload, not the unexported
    #      CLAUDE_SESSION_ID [P2-7].
    #   3. settings.json: `async: true` removed from test-gate/ci-mirror/
    #      format-lint-gate (an async hook CANNOT block) in favour of explicit
    #      timeouts [P1-1]; secrets-gate matcher widened and given a second
    #      Bash registration [P0-2/P2-4]; permissions.deny added [P0-2].
    #   4. Gate bodies: dependency-gate rewritten [P1-3]; spec-gate-commit
    #      scoped to implementation paths with ERE-escaped, array-quoted
    #      corpus [P1-2]; test-gate absolute find + 127 vs failure [P2-5]
    #      (the BYTES moved; lens B finding 3 later showed the 127-vs-failure
    #      EFFECT was unreachable behind the ERR trap - a byte-class record
    #      that asserts delivered behaviour inherits the obligation to be
    #      right about it, so this is noted rather than left standing);
    #      format-lint-gate no longer runs a MUTATING formatter [P2-6];
    #      spec-gate-entry predicate made reachable [P2-8]; secrets-gate
    #      dot-segment matching + multi-surface candidates [P0-2/P2-4].
    #   5. PROTOCOL_VERSION 2.5.0 -> 2.6.0 (stamped into settings.json
    #      _generatedBy, the state file and the manifest). MINOR, not
    #      PATCH: gate BEHAVIOR changes. Not a seam event by §8.4.
    #   6. Disclosure: audio_enabled true -> false, cost.jsonl renamed
    #      session-events.jsonl, .decision-pending swept on a 7-day window
    #      [P3]. sdk_gates/gates.py reconciled to the shell [P2-1/2/3].
    # [freeze-exception no. 18 - dependency-gate regression fix, 2026-07-28]
    # Source: docs/lens-b-execution-findings-2026-07-28.md findings 1 and 2.
    # The v2.6.0 P1-3 rewrite introduced three defects in the gate it was
    # fixing, and a differential sweep (same corpus through the 0ec72d0^ and
    # 0ec72d0 hook bodies) confirmed TEN commands that v2.5.0 blocked and
    # v2.6.0 allowed. Exactly TWO emitted files move, on all three fixtures:
    #   .claude/hooks/dependency-gate.sh  and  .claude/sdk_gates/gates.py
    # No shared header, no other gate, no settings.json, no steering doc,
    # skill, command or agent body - so every frozen twin stays byte-identical
    # and no §7.4 sentinel carrier or §7.5 skeleton moves. Verified by
    # differential install, not asserted.
    #
    # NO PROTOCOL_VERSION BUMP. This change crosses the "changes whether a
    # gate blocks" line that the upstream report names as the bar for a bump
    # (acceptance criterion 5) - but 2.6.0 is UNRELEASED: the only tag in the
    # repo is v2.5.0 (2026-07-27, an ancestor of HEAD). The defect never
    # shipped under a version number, so it is fixed in place rather than
    # bumped past. A bump is owed when 2.6.0 is actually tagged.
    #
    # What moved, and why:
    #   1a. The argument-extraction sed's leading `.*` was greedy, anchoring
    #       on the LAST install verb on the line, so an earlier install in a
    #       chain was never inspected. Replaced by segment-first scanning:
    #       the line is split on newlines and `;&|` (pure bash, no external
    #       binary) and each segment is judged on its own, making the verdict
    #       the OR over segments.
    #   1b. The lockfile-restore guard asked whether the COMMAND LINE ended
    #       in a bare verb, not whether THIS invocation had no arguments, so
    #       a trailing `&& npm install`, `; cargo add` or `# npm install`
    #       blanked the package list entirely. Now a per-segment fact.
    #   1c. The command-position anchor admitted only a literal `env `, so
    #       `sudo pip install`, `FOO=1 npm install`, `uv pip install` and
    #       `/usr/bin/pip install` all fell outside it. Anchor now admits
    #       env/sudo with their own flags, VAR=value runs, and a tool path.
    #   2.  `python -m pip install` (the form the Python ecosystem documents
    #       as canonical) and `pip[0-9.]*` added to the head pattern - the
    #       SDK already carried both, so this is a port to the canonical
    #       substrate, not a new rule.
    # The `curl … | sh` check still runs on the WHOLE command before
    # segmenting, because that pattern deliberately reads across a pipe.
    # ACCEPTED TRADE-OFF, recorded not buried: a separator inside a quoted
    # string now starts a new segment, so `git commit -m "fix; npm install
    # evil"` blocks. Deny-list bias is over-match; the alternative (skipping
    # odd-quote segments) fixes it in the FAIL-OPEN direction and was
    # declined. See docs/deferred-backlog.md J-7.
    #
    # [freeze-exception no. 19 - two-lens adversarial-review fixes,
    # 2026-07-28] Sources: docs/lens-a-execution-findings-2026-07-28.md
    # (F1-F10) and docs/lens-b-execution-findings-2026-07-28.md (1-15), two
    # independent adversarial reviews of v2.6.0 that EXECUTED the emitted
    # hooks. ONE re-baseline for the whole batch, deliberately: F1, F2, F5
    # and lens B finding 3 all live in the shared _HOOK_HEADER, so any one of
    # them alone would re-baseline every hook and burn an exception - and
    # `0ec72d0` introduced F1/F2/F5 WHILE fixing the previous round, which is
    # the hazard being avoided.
    #
    # MEASURED AGAINST PLAN ACTIONS - what plan_digest_full actually hashes -
    # not against the installed tree, which is the error freeze-exception
    # no. 17's count made (see the correction in its block above). Verified
    # by a HEAD-vs-worktree plan-body diff, all three fixtures:
    #   default          12 bodies move, 57 actions (unchanged), 0 added/removed
    #   full_autonomous  17 bodies move, 69 actions (unchanged), 0 added/removed
    #   design_steering  12 bodies move, 59 actions (unchanged), 0 added/removed
    # The `default` twelve: the eleven emitted hooks (every one of them, via
    # the shared header) plus sdk_gates/gates.py. full_autonomous adds the
    # four mode-gated hooks (tdd-gate, eval-gate,
    # drift-detector-loop-cooperation, iteration-summary-enforcement) AND
    # settings.json - the latter ONLY there, because the new
    # Write/Edit(.claude/.last-eval-pass) denies are emitted only when
    # eval-gate is (ai-agent archetype). No steering doc, skill, command,
    # agent body, wrapper skeleton or spec template moves on any fixture
    # (42 and 44 frozen-twin artifacts diffed, 0 moved), so every §7.5
    # skeleton and §7.4 sentinel carrier stays byte-identical and the
    # not-a-seam-event verdict is re-confirmed by measurement.
    #
    # Byte classes:
    #   1. Shared _HOOK_HEADER, so EVERY hook body moves:
    #      * norm_cmd / cmd_has_verb are pure bash now - no `tr`, no
    #        `grep -qE`. Both sat in `set -e`-exempt contexts (a command
    #        substitution and an `if` condition), so removing either binary
    #        from PATH turned every command gate into a SILENT no-op: rc=0,
    #        no message, no hook_fail [lens A F5].
    #      * Parsing is line-oriented. `tr -s '[:space:]' ' '` turned a
    #        newline into a space while the anchor class was `[;&|(]`, so any
    #        verb on a second line was unreachable: `git add -A\\ngit commit`
    #        exited 0 on spec-gate-commit, test-gate and ci-mirror
    #        [lens A F2].
    #      * New shared `cmd_segments` - the ONE segmentation mechanism.
    #        dependency-gate's local copy is gone.
    #      * The command-position prefix admits env/sudo with flags,
    #        VAR=value runs and a tool path.
    #      * _rotate_log guards on [ -f "$LOG" ]: a fresh install has no
    #        hooks.log, and redirections apply left to right, so every hook
    #        wrote a shell error to stderr on its first run
    #        [lens A F10 / lens B 15].
    #   2. secrets-gate: a quote-aware Bash tokenizer replacing `read -ra`
    #      plus a one-deep quote strip. That was wrong in BOTH directions -
    #      it saw one line only [lens A F1] and split quoted arguments into
    #      per-word path candidates [lens B 4] - so the two are fixed
    #      together or not at all. Also: shell operators delimit candidates
    #      (`cat .env; ls` yielded `.env;`), the bare directory form matches
    #      [lens A F6], and the ONE deliberate relaxation in the batch, the
    #      dotenv TEMPLATE basenames.
    #   3. test-gate: the pass marker is REMOVED, not repaired. It was
    #      gitignored, agent-writable and protected by no gate, so `touch
    #      .claude/.last-test-pass` disabled the gate [lens A F4]. The rc
    #      dispatch is also reachable for the first time - `set +e` does not
    #      disarm an ERR trap, so every failing suite reported "unexpected
    #      hook error" and the whole P2-5 fix was dead code [lens B 3].
    #   4. dependency-gate: generic value-taking flags (a flag consumes its
    #      value only when the value is value-SHAPED, so a short flag cannot
    #      swallow a package name) [lens A F9]; npx/uvx/dlx/exec arrival
    #      channels and package-index overrides NEWLY BLOCKED [lens A F3
    #      residue].
    #   5. eval-gate: anchored to command position like the other four -
    #      the shell's was left substring-matched while the SDK's was
    #      anchored [lens B 8].
    #   6. settings.json (full_autonomous only): Write/Edit denies for
    #      .claude/.last-eval-pass.
    #   7. sdk_gates/gates.py: the Bash-surface secrets closure and its
    #      _GATE_EXTRA_MATCHERS registration [lens A F7], the
    #      ENFORCED_PREFIXES port [lens B 8], and every dependency/test-gate
    #      change above, mirrored.
    #
    # NO PROTOCOL_VERSION BUMP - same reasoning as no. 18, restated because
    # this batch changes whether gates block in BOTH directions: 2.6.0 is
    # unreleased (the only tag is v2.5.0, 2026-07-27, an ancestor of HEAD),
    # so the defects never shipped under a version number and are fixed in
    # place. The §8.4 trigger walk is recorded in docs/changelog.md.
    #
    # [freeze-exception no. 20 - round-2 review of the no. 19 batch,
    # 2026-07-29] Three independent lenses were run at the no. 19 HANDOFF
    # PROMPT before it was handed off; two of them went past the prompt to
    # the commit and found that no. 19 had shipped a fail-open and a
    # false-positive of its own. That makes THREE consecutive fix commits
    # that introduced a defect into the class they were fixing. Exactly FOUR
    # emitted files move, identically on all three fixtures - action counts
    # unchanged at 57/69/59, zero added, zero removed, zero frozen twins
    # moved (verified by a body diff against 311bd67, not asserted):
    #   .claude/hooks/dependency-gate.sh, .claude/hooks/secrets-gate.sh,
    #   .claude/sdk_gates/gates.py, .claude/settings.json
    # settings.json moves on ALL THREE this time (unlike no. 19, where it
    # moved on full_autonomous only) because the new secrets-gate timeout is
    # unconditional while the eval-marker denies were archetype-gated.
    #
    #   1. dependency-gate FAIL-OPEN. no. 19's "a flag consumes its value
    #      only when the value is value-SHAPED" inversion counted `[0-9]*`
    #      and `*=*` as value-shaped, so a package name starting with a
    #      digit (`7zip-bin`, `0x`, `2to3`) or carrying a version pin
    #      (`evil==1.0`) was swallowed after any of ~60 flags and installed
    #      unapproved. no. 19's commit message claimed a short flag "can
    #      never swallow a package name" - true only of `evil`, its one
    #      witness. Value-shape is now a URL, a `:spec:`, a path, a
    #      key=value with NO version-comparison operator, or a bare
    #      digits-and-dots version.
    #   2. secrets-gate FALSE POSITIVE. no. 19's fix for lens A F6 (a bare
    #      directory name should match its own `dir/**` pattern) applied to
    #      every candidate, so any token equal to a never-read directory
    #      stem blocked: `grep secrets README.md`, `git commit -m secrets`,
    #      `echo secrets`. That is lens B finding 4's failure mode - the one
    #      no. 19 existed to fix - returning through a different door, in
    #      the gate with no override path. The arm is now scoped to
    #      STRUCTURED path parameters, where a bare directory name is
    #      unambiguously a path. Cost: the bare stem is allowed again on the
    #      Bash surface (docs/deferred-backlog.md J-14).
    #   3. sdk_gates/gates.py: the unbalanced-quote fallback kept the quote
    #      glued to the token, so `cat "secrets/prod.yaml` was ALLOWED on
    #      the SDK while the shell blocked it - a fail-open in the fallback
    #      whose own comment promised "a parse failure must not become an
    #      allow". Plus real reason strings for dependency-gate's three
    #      non-package refusals, which had all been rendering as
    #      "not in deps.md approved list: <sentinel>" with advice that
    #      cannot work (SEAM-CONTRACT §3.3 semantic equivalence).
    #   4. settings.json: secrets-gate gains an explicit 60 s timeout. It
    #      was the ONLY PreToolUse gate with no bound while being the one
    #      that runs on every Bash call, and its tokenizer is superlinear
    #      (0.29/1.38/6.01 s at 100/500/2000 lines). A PreToolUse timeout
    #      fails closed, so this bounds it in the safe direction.
    # [freeze-exception no. 21 - round-2 review batch 2, the quoted-run rule,
    # 2026-07-29] Source: the round-2 Fable 5 review of the no. 20 batch, 18
    # findings, every one reproduced by executing both substrates. Exactly
    # TWO emitted files move, identically on all three fixtures - action
    # counts unchanged, zero added, zero removed, zero frozen twins moved
    # (verified by a body diff of a parent-vs-head install at 0fba4d2, not
    # asserted):
    #   .claude/hooks/secrets-gate.sh  and  .claude/sdk_gates/gates.py
    # No shared header, no other gate, no settings.json, no steering doc,
    # skill, command or agent body. Narrower than no. 20 on purpose: the
    # tokenizer work is separable from the ten independent fixes, which are
    # deliberately NOT in this exception.
    #
    #   1. THE QUOTED-RUN RULE, resolved structurally [F-870 + F-891]. These
    #      two are one decision, not two patches, and no. 20's own header
    #      comment says so ("repairing either alone yields a tokenizer that
    #      is confidently wrong in the other direction") - it was still
    #      wrong, because it looked for the discriminator in the RUN. There
    #      isn't one there: `sh -c 'cat secrets/prod.yaml'` and
    #      `git commit -m "fix the .env loader"` are the same shape. The
    #      discriminator is WHO THE COMMAND IS. A shell invoker's argument
    #      is a command line and is re-tokenized; everyone else's quoted run
    #      stays one opaque candidate. Both substrates carry the same two
    #      sets (_SHELL_INVOKERS / _CMD_PREFIXES).
    #      F-870 was the fail-open half: joining the run into one candidate
    #      hid every directory-anchored pattern behind any wrapper, so
    #      `bash -lc "grep -r . secrets/"` - the literal string
    #      test_substrate_differential asserts as deny UNWRAPPED - passed on
    #      BOTH substrates. F-891 was the false-positive half: quote state
    #      reset at every newline, so a subject+body commit message and a
    #      `gh pr create --body` were re-parsed as unquoted prose and denied
    #      by the gate with no override path. One scan now carries quote
    #      state across newlines, which is what the shell does.
    #      Verified parent-vs-head: EXACTLY two verdicts move, both intended.
    #   2. F-937, the prerequisite. `basename` was a fork PER CANDIDATE, and
    #      no. 19's all-lines fix had just multiplied candidates by line
    #      count. Measured on the emitted gate: 22.9 s for a benign 2000-line
    #      command (~77 KB), crossing no. 20's own new 60 s bound at ~5000
    #      lines - and a PreToolUse timeout fails CLOSED, so the cost landed
    #      as a hard block on benign input, not as latency. Replaced with
    #      pure parameter expansion: same input now 1.5 s, and 194 KB
    #      completes in 3.8 s. This had to land BEFORE item 1, which raises
    #      the candidate count.
    #   3. SDK reconciliation, same commit, deliberately not deferred. The
    #      shell fix alone made F-870 read shell=deny/sdk=allow - a NEW
    #      divergence in the direction sdk_gates_template's binding rule
    #      forbids, i.e. exactly the mistake the previous three batches made.
    #      The ledger added in batch 1 caught it before it could ship. The
    #      SDK now segments quote-aware BEFORE shlex, which also fixes a
    #      divergence the review found separately: _SH_OPS.split was applied
    #      to quoted tokens, so `git commit -m "refactor (parse .env)
    #      handling"` was denied on the SDK and allowed by the shell.
    #
    # NO PROTOCOL_VERSION BUMP, same reasoning as no. 18 and no. 20: 2.6.0 is
    # unreleased (v2.5.0 remains the only tag), so gate-behavior defects are
    # fixed in place rather than bumped past. A bump is owed at 2.6.0's tag.
    #
    # ACCEPTED, recorded not buried: a nested quote inside an invoker's
    # argument keeps its quote character on the word, so
    # `ssh h "git commit -m '.env'"` over-matches. Over-match on a command
    # that runs a shell remotely is the cheap direction; the prose case is
    # the frequent one and is protected. docs/deferred-backlog.md J-15.
    #
    # [freeze-exception no. 22 - round-2 review batch 2b, the shared
    # segmenter, 2026-07-29] Source: the same round-2 review. THIRTEEN
    # emitted files move - all twelve hooks plus sdk_gates/gates.py - because
    # [COUNT CORRECTED round-4, 2026-07-29: no fixture emits twelve hooks.
    #  The `default` and `design_steering` fixtures emit 11,
    #  `full_autonomous` 15, so a shared-header change moves 13 and 17 files
    #  respectively (hooks + sdk_gates/gates.py). Measured, not counted from
    #  memory.]
    # the change is in the shared _HOOK_HEADER. Verified by parent-vs-head
    # install against 9952741, not asserted: NO settings.json, no steering
    # doc, no skill, command or agent body, no CLAUDE.md, no frozen twin,
    # action counts unchanged at 57/69/59. This is the wide-blast-radius
    # kind of exception, taken deliberately in ONE batch for the same reason
    # no. 19 was: F-401 and F-435 both live in the header, so splitting them
    # would burn two exceptions over the same bytes.
    #
    #   1. cmd_segments is QUOTE-AWARE [F-435]. It was not, and the same
    #      property was fail-CLOSED for dependency-gate (backlog J-7,
    #      accepted and written down) and fail-OPEN for cmd_has_verb (never
    #      written down): a separator inside a quoted `git -c` option value
    #      tore the option run in half, so `git -c user.email="$(id -un)@h.com"
    #      commit` left the verb off command position and test-gate,
    #      spec-gate-commit and ci-mirror all exited 0. Only one half of one
    #      property had been recorded.
    #      This RETIRES J-7 rather than trading it: a `;` inside a quoted
    #      argument is not a separator to the shell either, so
    #      `git commit -m "fix; npm install evil"` correctly reaches
    #      dependency-gate as one segment. Hiding an install inside quotes
    #      does not run it; the unquoted spelling still blocks. Walked
    #      run-at-a-time, not character-at-a-time - a per-character bash loop
    #      is O(n^2) under substring expansion, and F-937 is what that costs.
    #   2. CMD_PFX widened [F-401]. `>/dev/null pip install evil`,
    #      `2>/dev/null …`, `time …`, `nohup …`, `{ pip install evil; }` and
    #      `if true; then pip install evil; fi` each evaded the anchor with
    #      ONE token while a bare `pip install evil` was denied. A
    #      redirection, a brace group and a shell keyword do not change WHICH
    #      program runs, so they join env/sudo as prefixes rather than
    #      becoming new segment types. A backtick DOES run its contents and
    #      is now a separator, closing the asymmetry where
    #      `echo $(pip install leftpad)` blocked and the backtick spelling
    #      did not.
    #   3. sdk_gates/gates.py re-synced [F-381]. The shell's cmd_has_verb was
    #      rewritten by the round-2 review and _GIT_VERB_TMPL left at the v2.6.0
    #      form, so the SDK allowed what the shell blocked on five command
    #      shapes across three gates. `git show 4cc9742` proves the anchors
    #      AGREED at the parent - the divergence was created by the batch
    #      that rewrote one side. The verb anchor and the install anchor now
    #      share one _CMD_PFX_RE so they cannot drift apart that way again,
    #      and dependency-gate's segmentation moved off a bare regex onto the
    #      same quote-aware walk.
    #
    # NO PROTOCOL_VERSION BUMP - same reasoning as no. 18/20/21: 2.6.0 is
    # unreleased, v2.5.0 remains the only tag.
    #
    # [freeze-exception no. 23 - round-2 review batch 3, the independent
    # fixes, 2026-07-29] Source: the same round-2 review. THIRTEEN emitted
    # files move again (all twelve hooks plus sdk_gates/gates.py) because
    # [COUNT CORRECTED round-4, 2026-07-29: no fixture emits twelve hooks.
    #  The `default` and `design_steering` fixtures emit 11,
    #  `full_autonomous` 15, so a shared-header change moves 13 and 17 files
    #  respectively (hooks + sdk_gates/gates.py). Measured, not counted from
    #  memory.]
    # item 1 is in the shared _HOOK_HEADER. Verified parent-vs-head against
    # edac7c7: no settings.json, no steering doc, skill, command or agent
    # body, no CLAUDE.md, no frozen twin; action counts unchanged.
    #
    #   1. F-301, the shared-header payload read. `INPUT="$(cat || true)"`
    #      forked `cat` in the ONE place every hook runs, so a single
    #      missing binary disabled all eleven at once IN THE DIRECTION THAT
    #      ALLOWS. Confirmed: with a PATH holding jq/python3/grep/sed/tr/git
    #      but not `cat`, secrets-gate on `cat .env` and dependency-gate on
    #      `npm install evil` both returned rc=0 - empty INPUT, jq succeeds
    #      on empty input so hook_fail never fires, every jget empty, every
    #      gate falls through, no error, no log line. Strictly a better
    #      lever than the `tr`/`grep` the previous batch removed. Now a
    #      builtin `read -r -d ''`, plus an explicit empty-payload refusal.
    #   2. F-947, dotenv exemption scope. It `continue`d the TARGET loop,
    #      skipping EVERY pattern rather than the dotfile family it is
    #      scoped to, so `secrets/.env.example` was unguarded - and
    #      `secrets/**` is exactly the pattern it must not override. The
    #      comment's "exact basenames only" was true of the basename test
    #      and silent about the control-flow scope, which was the bug.
    #   3. F-1420, eval-gate, TWO fail-opens in one `if` condition (exempt
    #      from set -e and the ERR trap): `grep` off PATH -> 127 -> "no
    #      prompt files changed" -> push allowed; and `grep -q` SIGPIPEing
    #      git under pipefail -> 141 -> same, for any diff over the ~64 KiB
    #      pipe buffer. Pure bash now, and a git failure is a refusal. Also
    #      fixed in passing: a ROOT commit has no HEAD~1, so the very first
    #      push of a repo - the one introducing every prompt file it has -
    #      was the one push this gate never inspected.
    #   4. F-788, `Grep{pattern:...}` is a search REGEX and sat in the phase
    #      where a bare directory name counts as a path, so
    #      `Grep pattern="secrets"` was hard-blocked: searching your own
    #      codebase for the word was impossible, in the gate with no
    #      override path. Own phase, dir_ok=0 - still matched, since
    #      `pattern:"*.pem"` returns matching file contents.
    #   5. F-1357, index overrides. The CLI spelling was SKIPPED as an
    #      ordinary flag value while the environment-variable spelling of
    #      the identical attack was denied from the same reason string in
    #      the same file. NEWLY BLOCKED on both substrates:
    #      --index-url/-i/--extra-index-url/--find-links/--registry/--index/
    #      --git/--repo. `-f` is deliberately excluded (pip's --find-links
    #      but npm's --force). A legitimate internal index belongs in the
    #      project's package-manager config, which is what the refusal says.
    #   6. F-1313, `^[0-9.]+$` still swallowed single-character numeric
    #      package names; `0`, `1` and `2` are all real npm packages. A bare
    #      version needs a DOT now. Third consecutive round for this
    #      predicate.
    #   7. F-1393, the shell tdd-gate was anchored on `src/`/`lib/` while
    #      Claude Code passes ABSOLUTE paths, so it matched nothing and
    #      silently allowed every write - while the SDK twin normalized and
    #      denied, its comment naming the bug verbatim and fixing only its
    #      own side. Both now strip the project root and a leading `./`.
    #   8. F-2923, the retrofit warn-only preamble matched a raw SUBSTRING
    #      while the body it wraps is anchored, so the two disagreed in both
    #      directions during the weeks the schedule promises are warn-only:
    #      `git  commit` (two spaces) and `git -C . commit` skipped the
    #      exemption and hit the ENFORCING body, and `echo "git commit"`
    #      fired the warn-only message on a command the body ignores. Uses
    #      the same anchor as the body now.
    #
    # NEWLY BLOCKED, stated plainly because this is the class the changelog
    # got wrong three rounds running: items 5 and 6 deny commands that were
    # allowed at edac7c7, and item 3 denies a push whose diff cannot be
    # read. Items 2, 7 and 8 also newly deny. The only NEWLY ALLOWED
    # behaviour in this batch is item 4 (`Grep pattern="<dirname>"`).
    #
    # [freeze-exception no. 24 - ROUND-3 review remediation, 2026-07-29]
    # Source: three independent adversarial lenses run against `ff435f5`,
    # ~22,000 verdict evaluations between them, 25 findings. THIRTEEN
    # emitted files move (all twelve hooks plus sdk_gates/gates.py) because
    # [COUNT CORRECTED round-4, 2026-07-29: no fixture emits twelve hooks.
    #  The `default` and `design_steering` fixtures emit 11,
    #  `full_autonomous` 15, so a shared-header change moves 13 and 17 files
    #  respectively (hooks + sdk_gates/gates.py). Measured, not counted from
    #  memory.]
    # most of this is in the shared header. Verified parent-vs-head against
    # ff435f5: no settings.json, no steering doc, skill, command or agent
    # body, no CLAUDE.md, no frozen twin.
    #
    # This exception exists because the PREVIOUS batch shipped defects into
    # the classes it was fixing, and said so nowhere. Stated plainly:
    #
    #   1. FAIL-OPEN I INTRODUCED [A1/B-F1]. Retiring backlog J-7 made
    #      quoted separators non-splitting on the reasoning that "hiding an
    #      install inside quotes does not run it". True for prose, FALSE for
    #      a shell invoker: `sh -c 'true; pip install evil'` runs, and was
    #      allowed from edac7c7 onward. The invoker rule had been added to
    #      secrets-gate in the same batch and not to cmd_segments, so the
    #      two segmenters disagreed in the dangerous direction. cmd_segments
    #      now re-segments an invoker's quoted argument (_cs_isinv).
    #   2. FAIL-OPEN I INTRODUCED [A2]. The invoker re-tokenization used
    #      `read -ra`, which is LINE-oriented, so a multi-line invoker
    #      argument was truncated at the first newline. The intersection of
    #      the two features that batch shipped together, and the corpus had
    #      no row combining them.
    #   3. F-435 WAS NOT ACTUALLY CLOSED [A5]. cmd_segments walked quoted
    #      runs but then split the buffer on every newline - including ones
    #      inside quoted runs, because the segment break was itself spelled
    #      with a newline. The break is now \001 and whitespace inside a
    #      quoted run is \002, so a run stays one token; quotes are dropped,
    #      which also lets `"pip" install evil` reach the matcher.
    #   4. UNSATISFIABLE GATE [C1/C2]. tdd-gate required a test NEWER than
    #      the target, and `-newer` needs the target to exist - so creating
    #      any new source file was refused after the operator had already
    #      written the test, and the only escape was `touch` via Bash, i.e.
    #      routing around the gate. It also searched a hard-coded `tests/`.
    #      The rule is now the one the message states: a matching test must
    #      EXIST, found anywhere in the tree.
    #   5. CI BLOCKED [A6/B-F3/C6]. eval-gate's `*.md` predicate made every
    #      markdown file a prompt file. Survivable on a two-commit diff,
    #      catastrophic once the root-commit branch fed it the whole tree: a
    #      shallow clone (actions/checkout defaults to depth 1) has no
    #      HEAD~1, took that branch, matched README.md, and refused every CI
    #      push. Narrowed to paths that actually name a prompt.
    #   6. BLOCK THAT MISSED THE HOSTILE SPELLING [A3/C3/C4]. The index-flag
    #      deny list matched `--index-url URL` and missed `--index-url=URL`
    #      and `-f URL` - the spellings an attacker uses, and every one of
    #      pip/npm/yarn/cargo accepts them. Enumerating flag NAMES is what
    #      left the hole; the rule is now the VALUE carrying a scheme.
    #   7. UNACTIONABLE REFUSAL [A4/C10]. "a bare version needs a dot"
    #      refused `pip install --timeout 60 requests` with "not in deps.md
    #      approved list: 60". The discriminator is the FLAG: a long flag
    #      names one thing, a one-letter flag differs by ecosystem.
    #   8. WRAPPER GAPS [A7/C9]. `timeout 5 sh -c` allowed while
    #      `nohup sh -c` denied. Wrappers that carry their own operand are
    #      now scanned past, bounded.
    #
    # NEWLY ALLOWED, derived from an executed parent-vs-head sweep and not
    # from intent: `pip install --timeout 60 requests` and its dotless-value
    # siblings; creating a new source file when its test exists (tdd-gate);
    # `git push` when the only markdown changed is not a prompt file.
    # NEWLY BLOCKED: everything in items 1, 2, 3, 6, 8.
    #
    # ---- CORRECTION, 2026-07-29 (round-4). THE PARAGRAPH ABOVE IS FALSE. --
    #
    # It says its newly-allowed inventory was "derived from an executed
    # parent-vs-head sweep and not from intent". It was not. A round-4 sweep
    # of 7464 compositions x 3 installs (22,392 hook invocations) over
    # 0fba4d2, ff435f5 and b1782ec found **1,740 shapes that 0fba4d2 blocks
    # and b1782ec allows**. Only 576 of those were introduced by b1782ec (384
    # dependency-gate + 192 test-gate). NONE of them appears in the three
    # items listed above.
    #
    # The other **1,164 came from the round-2 series fac2897..ff435f5** (768
    # dependency-gate + 384 test-gate + 12 secrets-gate) and appear in NO
    # freeze-exception, changelog entry or backlog row - including
    # exception 23 below, which makes the same "from an executed parent-vs-head
    # comparison" claim. Hand-verified sample: `sudo -u root sh -c 'echo hi;
    # pip install evilpkg'` is rc=2 at 0fba4d2, rc=0 at ff435f5, rc=0 at
    # b1782ec.
    #
    # FIVE consecutive newly-allowed inventories in this file were written
    # from intent and all five were wrong. The round-4 exception (no. 25)
    # states its inventory from a committed, re-runnable sweep -
    # `tests/composition_sweep.py` - and the sweep is now in the suite.
    #
    # The file-count claim below ("THIRTEEN emitted files ... all twelve
    # hooks") is also wrong and is corrected in exception 25: NO fixture
    # emits twelve hooks. Measured 2026-07-29: `default` 11, `design_steering`
    # 11, `full_autonomous` 15.
    #
    # ======================================================================
    # [freeze-exception no. 25 - ROUND-4 remediation, 2026-07-29]
    # ======================================================================
    # Source: the round-4 fix brief, itself written by the implementer of
    # b1782ec and then adversarially reviewed by three independent lenses.
    # SCOPE: greenfield only (owner decision, 2026-07-29). `mode: retrofit`
    # is tracked, not fixed; D14 stays open as backlog K-1, and
    # tests/test_retrofit.py (263 checks) was a TRIPWIRE this round, not a
    # target. It stayed green.
    #
    # FILES THAT MOVE - measured by a HEAD-vs-worktree plan diff, per fixture,
    # not counted from memory:
    #     default           13 of 57   (11 hooks + sdk_gates/gates.py
    #                                   + steering/deps.md)
    #     design_steering   13 of 59   (same named set)
    #     full_autonomous   17 of 69   (15 hooks + the same two)
    # ZERO files added, ZERO removed, so all three action counts are
    # unchanged (57/69/59). NO settings.json, no CLAUDE.md, no skill, command
    # or agent body, no frozen twin. `steering/deps.md` moves for D13 and is
    # the only non-hook, non-gates.py body in the set.
    #
    # WHY (each item is a defect this batch's predecessors shipped):
    #
    #   1. SIX COMMAND-POSITION ENCODINGS, FIVE PREFIX SETS [D1/D2/D3/D7/D9].
    #      `_cs_isinv`, `CMD_PFX`, `_sg_push` and the dead `_CS_INVOKERS` on
    #      the shell; `_segment_candidates`, `_expand_invoker_args`,
    #      `_CMD_PREFIXES` and `_CMD_PFX_RE` on the SDK. They disagreed about
    #      which words are transparent, whether a prefix may consume an
    #      operand, and whether VAR=value runs are skipped. All six now derive
    #      from lib/cmdpos.py. The walkers lost their bound (`< 3` in one,
    #      `< 4` in another; `timeout -k 1 -s KILL 5 sh -c` needs five); the
    #      anchors gained positionals, which is what D9 needed -
    #      `sudo -u root pip install evilpkg` was rc=0 on BOTH substrates at
    #      ALL THREE commits, so neither a differential nor a parent sweep
    #      could see it.
    #   2. THE SDK'S VERB GATES NEVER EXPANDED AN INVOKER [D1, SDK half].
    #      `_git_verb` did not call `_expand_invoker_args` - only
    #      `_scan_install_line` did - so `sh -c 'git commit -m x'` was
    #      shell=deny / SDK=allow across test-gate, spec-gate-commit AND
    #      eval-gate simultaneously.
    #   3. NEITHER QUOTE SCANNER HANDLED BACKSLASHES [D5]. This is D5's actual
    #      root cause; an earlier diagnosis blamed recursion depth and a
    #      reviewer built depth-3 recursion over mis-parsed input. Two of
    #      D5's three reproductions still allowed, and it EXECUTES.
    #   4. NESTED QUOTES INSIDE AN INVOKER ARGUMENT WERE A FAIL-OPEN [D8].
    #      `bash -c "cat 'secrets/prod.yaml'"` READ THE FILE while
    #      `bash -c "cat secrets/prod.yaml"` denied. The re-tokenization was
    #      a whitespace split, not a parse. Backlog J-15 recorded this
    #      INVERTED, as an over-match "in the cheap direction".
    #   5. THE EMITTED gates.py NO LONGER COMPILED CLEAN [D10]. A bare `\\S`
    #      in a docstring. Under `-W error::SyntaxWarning` the import fails
    #      and EVERY SDK gate is disabled at once. Nothing compiled the
    #      emitted artifact, so the golden digest re-baselined over it.
    #   6. CONFIG INJECTION, FOUR SINKS [D12]. `never_read_paths` and
    #      `deps.approved` reach quoted heredocs whose sentinel they can
    #      forge; `hooks.drift_*` is interpolated UNQUOTED into a shell test
    #      that runs on every tool call; `commands.*` can emit a hook bash
    #      cannot parse. All validate at `resolve_config` now.
    #   7. CONFIG-SHAPED VACUITY [D18]. `["**/secrets/**"]`, `["./secrets/**"]`,
    #      `["secrets/"]` and `["secrets"]` each produced a secrets-gate that
    #      guarded NOTHING, rc=0 and silent. Normalized, not rejected.
    #   8. ADVISORY HOOKS BLOCKED [D17]. Six, not four: the empty-payload
    #      `hook_fail` sits above each body's `FAIL_CLOSED=0`.
    #   9. tdd-gate WAS NEAR-VACUOUS [D11]: case-sensitive `find`, and it
    #      pruned only `.git`, so `.claude/commands/spec-new.md` satisfied
    #      `src/new.py` on a pristine install.
    #  10. THE ARRIVAL-CHANNEL PATTERNS WERE A HAND-WRITTEN SUBSET [D16/D20]
    #      of sets that already existed, plus D19: `Grep{glob}` returned
    #      matching file CONTENTS and was inspected by neither substrate.
    #
    # NEWLY ALLOWED - enumerated BEFORE the parsers were touched, in
    # docs/round-4-intended-relaxations.md, and verified by the committed
    # sweep rather than asserted:
    #     R-1  eval-gate: a docs-only `git push`            (SDK: deny->allow)
    #     R-2  tdd-gate: a source file whose test exists under a conventional
    #          name (`PaymentTest.java`, `OrderSpec.scala`, `foo.test.ts`)
    #                                                     (shell: deny->allow)
    #     R-3  `script pip install evil` / `su pip install evil` - NEITHER
    #          runs its positional operand              (shell: deny->allow)
    #     R-4  the six advisory hooks stop exiting 2 on an empty payload
    # Everything else moves in the DENY direction.
    #
    # EVIDENCE, re-runnable, not asserted:
    #   tests/composition_sweep.py            17,268 compositions x both
    #                                         substrates: 0 not denied
    #   tests/composition_sweep.py --rev 0fba4d2 --rev b1782ec
    #                                         0 newly allowed outside R-1..R-4
    #   .claude/checkpoints/regression-invariant-corpus.py
    #                                         LIVE 77 -> 2, REGRESSION 0
    #
    # NO PROTOCOL_VERSION BUMP - 2.6.0 is still unreleased.
    #
    # [freeze-exception no. 26 - jget parser-usability fail-open, 2026-07-31]
    # ALL THREE fixtures move together, because the change is one function in
    # the shared `_HOOK_HEADER`: every emitted hook body carries it. Verified
    # per-file against `main` by body digest before re-baselining:
    #   default          11 bodies move, 57 actions (stable), 0 added/removed
    #   full_autonomous  15 bodies move, 69 actions (stable), 0 added/removed
    #   design_steering  11 bodies move, 59 actions (stable), 0 added/removed
    # EVERY moved body is under .claude/hooks/. Nothing outside the hook set
    # moved - checked explicitly, because "the shared header changed" is
    # exactly the shape that hides an unrelated edit. `sdk_gates/gates.py`
    # deliberately did NOT move: the SDK substrate parses JSON in-process and
    # has no external-parser selector, so it never had this defect.
    #
    # THE DEFECT. `jget` chose its parser with `if have_jq ... elif have_py`,
    # binding the choice to `command -v` PRESENCE, then swallowed the parser's
    # failure with `|| true`. A jq that exists but does not run - a pyenv/asdf
    # /mise shim, a broken `libonig.so.5` link, a non-executable file of the
    # right name - therefore made jget return EMPTY, every parsing gate fall
    # through its `case` to ALLOW, and the `elif` guaranteed the working
    # python3 on the same PATH was never tried. Executed on the emitted
    # artifact at `main`, jq exiting 127 with python3 present:
    #   secrets-gate    `cat .env`           rc=0   (must be 2)
    #   dependency-gate `npm install evil`   rc=0   (must be 2)
    # Both silent; hooks.log recorded only the misleading "no path". This is
    # upstream P0-3b's fail-open reopened through the SELECTOR rather than
    # through absence - P0-3b closed "no parser at all" and this is "a parser
    # that does not work", which a presence test reports as success.
    #
    # [freeze-exception no. 31, 2026-07-31] THE PROTOCOL_VERSION BUMP,
    # 2.6.0 -> 2.6.1, all three fixtures. This pays the debt recorded by
    # exceptions no. 18, 20, 21, 23 and 25, each of which declined to bump on
    # the stated grounds that "2.6.0 is unreleased, v2.5.0 remains the only
    # tag" and that "a bump is owed when 2.6.0 is actually tagged". v2.6.0 WAS
    # tagged on 2026-07-30 (f6bded0), so the debt came due - and it matters
    # concretely: the v2.6.0 tag as published FAILS OPEN. Executed against an
    # install from f6bded0 with a broken-but-present jq, secrets-gate on
    # `cat .env` and dependency-gate on `npm install evil` both return rc=0
    # (P0-3d); on this tree both return rc=2. Tagging the fixes without a bump
    # would have stamped bootstrap_protocol_version "2.6.0" into installs made
    # from a v2.6.1 tag - a version claim the artifact denies, which is the
    # §4.5 class three PRs were just spent removing.
    # VERIFIED PER-FILE BEFORE RE-BASELINING: exactly ONE body moves per
    # fixture - .claude/settings.json - action counts stable at 57 / 69 / 59,
    # 0 added, 0 removed, and the ONLY differing line is `_generatedBy`:
    #   "bootstrap-installer (protocol 2.6.0)" -> "(protocol 2.6.1)"
    # No hook, wrapper, skill, command or agent body moves; no gate behaviour
    # changes. plugin/plugin.json's version and description track the constant
    # and were bumped with it (pinned by tests/test_installer.py AC-A0-1).
    # [freeze-exception no. 30, 2026-07-31] full_autonomous ONLY, and NOT
    # comment-only - this one changes emitted behaviour. O-3/P-9 decided: a
    # REFUSAL IS NOT A RUN OUTCOME. The wrappers reported refusals using the
    # termination vocabulary - the auto.sh skeleton as `infrastructure-
    # failure`, and the per-task wrappers as `goal-condition-suspect` for a
    # missing task file, an ineligible task and an already-claimed task
    # (executed: `loop.sh T-1` logged "exit reason=goal-condition-suspect"
    # for a task that did not exist, on a wrapper with no goal at all).
    # Each now sets REFUSAL and the exit line reads "REFUSED: <cause>",
    # claiming no enum value. The 13-value enum is deliberately NOT extended
    # (it is queue-level contract surface describing why a RUN ended), so
    # tests/test_usage_limit_contract.py's exactly-13 pin is untouched and
    # still passes. `manual-halt-sentinel` is deliberately RETAINED as a
    # reason: a halt sentinel genuinely was observed, so that one names a
    # real cause. VERIFIED PER-FILE BEFORE RE-BASELINING: exactly three
    # bodies move - auto.sh, loop.sh, goal-loop.sh - action count stable at
    # 69, 0 added, 0 removed, and `default` + `design_steering` are BYTE-
    # IDENTICAL (they emit no wrappers), which is why only one digest moves.
    # [freeze-exception no. 29, 2026-07-31] COMMENT-ONLY re-baseline of all
    # three fixtures. Retired the phantom version labels `v2.6.1`/`v2.6.2`,
    # which named releases that never existed: git blame resolves them to the
    # two-lens batch (4cc9742, 311bd67) and the round-2 review (0fba4d2 and
    # its remediation), and ALL of those commits are ancestors of the v2.6.0
    # tag - so every change they described shipped INSIDE v2.6.0. Twelve of
    # the 33 were EMITTED, so an operator on a 2.6.0 install read "the v2.6.2
    # optimization pass" inside secrets-gate.sh and would go looking for an
    # upgrade that cannot exist. Labels now name the batch. VERIFIED PER-FILE
    # BEFORE RE-BASELINING: exactly THREE bodies move on each fixture -
    # dependency-gate.sh (6 lines), secrets-gate.sh (8), sdk_gates/gates.py
    # (10) - action counts stable at 57 / 69 / 59, 0 added, 0 removed, every
    # differing line a comment, and nothing else in the emitted tree differs.
    # gates.py DOES move here, unlike no. 28: five of the labels lived in
    # lib/sdk_gates_template.py.
    # [freeze-exception no. 28, 2026-07-31] COMMENT-ONLY re-baseline of all
    # three fixtures, for TWO corrections to the jget comment block.
    # (1) It explained the fix with a wrong account of `set -o pipefail` - it
    # claimed pipefail is what makes the pipeline's status the parser's. It is
    # not: the parser is the LAST command, so that is already true by plain
    # POSIX (executed: parser exits 127 -> substitution rc=127 with pipefail
    # OFF). What pipefail actually adds is the reverse - a failed producer
    # also fails the pipeline.
    # (2) It named pyenv as a source of a `jq` shim. pyenv is a Python version
    # manager and would shim jq only via a pip console script; asdf and mise
    # are the managers that carry jq as a first-class tool (`asdf-jq`, mise
    # registry `aqua:jqlang/jq`). Verified 2026-07-31 against a live mise.
    # The mechanism was right, the example was not.
    # VERIFIED PER-FILE BEFORE RE-BASELINING:
    # 11 / 15 / 11 bodies move, action counts stable at 57 / 69 / 59, 0 added,
    # 0 removed, every moved body under .claude/hooks/, and every differing
    # line in every moved body is a COMMENT line. sdk_gates/gates.py is
    # byte-identical - the SDK parses in-process and never had this defect.
    # No behaviour changes; the suite is unchanged at 1905 checks.
    # THE FIX. Try each parser in turn; accept its output only if it exited
    # clean - the parser is last in the pipeline, so its status is already the
    # pipeline's; `set -o pipefail` additionally surfaces a failed printf.
    # Both unusable is now the same condition as neither installed: hook_fail,
    # fail-closed for a blocking gate and a logged degrade for an advisory
    # one. Pinned by tests/test_hook_behavior.py "P0-3b(ii)", demonstrated to
    # fail (5 checks) against the pre-fix header.
    "default":
        "511ec0cd94c4d3f6b47617328c5ecc3f6379ab548e3d9cf6efada5991c8fde96",
    #   Adversarial-review round-2 additions inside the same exception
    #   (pre-commit, same named set): loop.sh/goal-loop.sh gain the
    #   transient-path definition (no-rejected-event arm + infra_* knobs,
    #   Phase 9.5 transient paragraph); auto.sh enum restores the
    #   "within the run" / "transitively" qualifiers.
    #   [v2.4.0 code fold — step 0 version stamp] same settings.json
    #   `_generatedBy` "protocol 2.2.0" -> "protocol 2.4.0"; the ONLY
    #   full_autonomous change at this step (count stable at 67).
    #   [v2.4.0 code fold — GR2-03a] +1 unconditional file
    #   .claude/steering/assumption-ledger.md (count 67 -> 68).
    #   [v2.4.0 code fold — GR2-01] prose-only, count unchanged (68). Body
    #   bytes move for CLAUDE.md, .claude/specs/INDEX.md, and the implementer
    #   agent body (failed-approaches do-not-retry priming instruction).
    #   [v2.4.0 code fold — GR2-02] comment-contract only, count unchanged
    #   (68). Body bytes move for loop.sh + goal-loop.sh only (shared
    #   _per_task_wrapper skeleton: trajectory-retention binding item +
    #   loop-final Trajectory line). auto.sh is UNTOUCHED — default fixture
    #   has no wrappers, so its digest does not move at this step.
    #   [v2.4.0 review-fix re-baseline] Emitted-byte changes from the
    #   adversarial-review fixes, diff-verified vs the pre-fix head (zero files
    #   added/removed; count stable at 68): the two default-fixture bodies
    #   above (assumption-ledger.md, specs/INDEX.md) PLUS the two wrappers —
    #     loop.sh / goal-loop.sh — three comment-contract citation fixes in the
    #     shared _per_task_wrapper skeleton: (a) the trajectory-retention item
    #     now cites Phase 9.5 unconditionally (its single normative home; the
    #     interpolated {phase} made goal-loop.sh cite a "Phase 9.6 Deliverable
    #     contract for the wrappers" heading that does not exist), (b) the
    #     loop-final block now interpolates {phase} (9.5/9.6) instead of the
    #     hardcoded 9.7, which is queue mode — a phase a loop-only project
    #     never enabled, and not where loop-final is defined, and (c) the block
    #     now names the actual destination .claude/sessions/loop-final-
    #     $TASK_ID.md and states the gitignore posture accurately (only the
    #     .claude/sessions/ DOTFILE sentinels are ignored) instead of citing
    #     .claude/specs/, which is not where the audit record belongs.
    #   auto.sh remains UNTOUCHED (its 13-value exit_reason enum unchanged).
    #   [v2.4.0 review-fix re-baseline, part 2 — frozen-source corrections]
    #   The .claude/.gitignore `settings.local.json` entry above, PLUS
    #   loop.sh / goal-loop.sh: the trajectory-retention contract no longer
    #   ASSERTS that retained stream JSON "is purged with the 7-day
    #   state-retention policy". That policy covers session-ID-namespaced
    #   state under .claude/sessions/ and does not reach .claude/logs/; no
    #   emitted hook, wrapper, or auto.sh consumes purge_old_state_after_days,
    #   so nothing prunes trajectory files at all. Since the same contract
    #   makes retention MANDATORY, the files accumulate without bound while
    #   the committed telemetry.md told a privacy reviewer they expire.
    #   Pruning is now stated as part of the operator obligation the contract
    #   already binds. auto.sh still UNTOUCHED.
    #   [v2.4.0 review-fix re-baseline, part 3 — GR2-01 template ownership]
    #   Same +1 file and same three body moves as the default column
    #   (68 -> 69); the split is archetype- and mode-independent.
    #   [v2.5.0 DS-01 — version stamp] same settings.json `_generatedBy`
    #   "protocol 2.4.0" -> "protocol 2.5.0"; the ONLY full_autonomous change at
    #   this step (count stable at 69). full_autonomous leaves
    #   design_steering_enabled off, so DS-01 adds nothing here either.
    #   [v2.5.0 freeze-exception no. 16] see the design_steering column for
    #   the full record; full_autonomous moves for all three byte classes
    #   (16 files: the 12 shared ones + tdd-gate, eval-gate,
    #   drift-detector-loop-cooperation, iteration-summary-enforcement).
    # [freeze-exception no. 17] same named set as `default` above.
    # [freeze-exception no. 18] same two files as `default` above
    # (dependency-gate.sh + sdk_gates/gates.py); the four extra hooks this
    # fixture carries are untouched.
    # [freeze-exception no. 27 - autonomous-mode exit contract, 2026-07-30]
    # full_autonomous ONLY. The `default` fixture emits no wrappers and no
    # autonomous hooks; its digest above is the no.-26 value (the shared
    # `jget` header fix), NOT the no.-18 value an earlier draft of this note
    # claimed - no. 18 left 29a670d0..., and b5d7f71 moved it again at no.
    # 25. A provenance line that names the wrong predecessor is how a future
    # re-baseline gets justified against a tree that never existed.
    #
    # Numbered 27, not 19: 19 was spent at :455 (two-lens adversarial-review
    # batch, 2026-07-28) and the highest number already used is 26. The
    # duplicate was caught by the adversarial round on this branch; backlog
    # D-8 records that this ledger's numbering has drifted before.
    #
    # Action count stable at 69: zero added, zero removed. Exactly FIVE files
    # move relative to the rebase parent, diff-verified by per-file body
    # digest AND read byte by byte:
    #   1. auto.sh - the skeleton refusal path stopped exiting 0 with a
    #      terminal-SUCCESS exit_reason (queue-empty) for a run that
    #      dispatched nothing. The 13-value enum is deliberately unchanged;
    #      the wrapper keeps its pessimistic default and exits 1.
    #   2. loop.sh and 3. goal-loop.sh - the same exit-contract change
    #      (max-iterations), PLUS TWO MORE CHANGED LINES EACH that an
    #      earlier draft of this note omitted: the D-9 `log()` printf escape
    #      and the I-8 `O_CREAT|O_EXCL` claim-sentinel escape, both fixed
    #      here because they are in the same emitted bytes. Their backlog
    #      rows are marked `done` and point at this exception; a note that
    #      described these two files as carrying one change each would have
    #      left the escape fixes byte-pinned by nothing and explained by
    #      nothing.
    #   4. iteration-summary-enforcement.sh - the summary demand exits 2
    #      (blocks) rather than 1 ("tool proceeds"), bounded by a
    #      stop_hook_active guard so a Stop hook cannot spin.
    #   5. drift-detector-loop-cooperation.sh - `ls A B` split into two
    #      tested globs, so the tier-3 branch fires in a SINGLE active mode.
    # Behaviour pinned by tests/test_wrapper_behavior.py, demonstrated to
    # fail (11 checks) against the pre-fix templates.
    #
    # THE BOUND'S PARSER TEST, twice corrected. The first cut read
    # stop_hook_active with a bare `[ "$(jget ...)" = true ]`; jget routes a
    # missing parser through hook_fail, whose `exit 2` dies with the COMMAND
    # SUBSTITUTION rather than the script, so on a parserless host the guard
    # read empty and the hook blocked every Stop forever. That was replaced
    # with an explicit `have_jq || have_py` test degrading to ALLOW. The
    # adversarial round then showed THAT was still presence, not usability:
    # with a broken-but-present jq the bound read empty and the hook blocked
    # every Stop (executed: PRE rc=1, POST rc=2). Fixed at the root in
    # freeze-exception no. 26 - `jget` now falls back on FAILURE, not only on
    # absence - and the local guard is a parser SELF-TEST rather than a
    # presence test, so both layers agree.
    "full_autonomous":
        "1f9f12dc7fd6dbb2c88e1f9cef917643d39377365f7278162f2c7b065815f653",
    # [v2.5.0 DS-01 — new flag-on fixture] Deliberate golden ADDITION (not a
    # re-baseline): a fullstack config with design_steering_enabled: true AND
    # design_review_skill_enabled: true. Pins the three flag-gated artifact
    # bodies byte-for-byte (.claude/steering/design.md, .claude/skills/
    # design-review/SKILL.md, .claude/commands/design-review.md — the frozen
    # DR-2-final bodies) so they cannot drift silently. Verified: flag-on vs
    # flag-off delta on the same fixture is EXACTLY these 3 files, none removed.
    #
    # [DR2-04 freeze-exception] Re-baselined for exactly one byte class in the
    # design.md body (verified by plan diff; default and full_autonomous
    # digests are UNCHANGED, and all three action counts are unchanged at
    # 57/69/59 - no artifact added or removed):
    #   1. [DR-01] guide pointer corrected, docs/design/uiux-guide.docx ->
    #      docs/UIUX-Design-Guide.md. The old path named a directory, basename
    #      and extension that never existed in this repo, so invariant 8's
    #      citation trail terminated nowhere.
    #   2. [DR2-02] invariant 8's baseline parenthetical disambiguated: under
    #      WCAG 2.2, target size at AA is 24x24 CSS px, while the widely-quoted
    #      44x44 is SC 2.5.5 at AAA. The prior wording ("WCAG 2.2 AA
    #      target-size and contrast ratios") invited the AAA figure to be read
    #      as the AA requirement.
    #   3. [DELTA-03 freeze-exception] the design-review SKILL.md body gains the
    #      honest-scope clause the PRD (Phase 7) and Companion (migration §)
    #      specify but the original DR-2-final frozen body omitted: "design-time
    #      floor / advisory flag, NOT a compliance control; no substitute for
    #      legal review (FTC, EU Digital Fairness Act); reduces-but-does-not-
    #      prevent dark-pattern emission at scale." Byte-synced into
    #      lib/templates.py _design_review_skill; asserted present by
    #      test_installer DS-01[on+skill]. Moves ONLY this fixture (the skill is
    #      emitted only under design_review_skill_enabled).
    # Only the flag-on fixture moves because design_steering_enabled is
    # default-off (installer.py:93, interview.py:173), per DELTA-01.
    #
    # [v2.5.0 freeze-exception no. 16 (release-review fixes F1/F2/F3,
    # 2026-07-27)] ALL THREE fixtures re-baselined. Diff-verified vs the
    # pre-fix HEAD (scratch HEAD-vs-worktree plan diff, all four plan shapes
    # incl. a retrofit probe): zero files added, zero removed, counts stable
    # at 57/69/59; the changed set is EXACTLY every emitted hook plus
    # audio-alerts.config (12 files default/design_steering, 16
    # full_autonomous — the four goal/loop-gated hooks add there). Three
    # byte classes:
    #   1. [F3] _HOOK_HEADER jget Python fallback renders booleans
    #      lowercase like `jq -r` ("true"/"false", not str(True)="True").
    #      Without this, every [ "$(jget ...)" = "true" ] guard — notably
    #      the 6.D stop_hook_active loop guard in cost-log and
    #      task-done-alarm — silently failed on jq-less installs. Touches
    #      every hook body (shared header). Runtime-verified in a scratch
    #      install with jq removed from PATH: guarded Stop appends nothing,
    #      normal Stop appends one line.
    #   2. [F2/A-5] iteration-summary-enforcement gains a .goal-active-*
    #      gate: it is wired as an unconditional Stop hook, so on any
    #      goal-enabled install every ORDINARY interactive session end
    #      errored rc=1 demanding a summary no non-goal session writes.
    #      Runtime-verified: no marker rc=0; marker without summary rc=1;
    #      marker with summary rc=0. Residual stale-glob match is backlog
    #      I-13.
    #   3. [F1] honest-scope corrections: audio-alerts.config header states
    #      the emitted hooks implement the tier-1 notice only and that
    #      thresholds are baked at install time; drift_tier3_enforced
    #      true -> false (nothing emitted writes .drift-tier3-* or denies at
    #      tier 3 — the old value advertised enforcement that does not
    #      exist); drift-detector and drift-detector-loop-cooperation
    #      comments corrected to say so (backlog I-1).
    # [freeze-exception no. 17] same named set; the three design
    # artifacts themselves are UNCHANGED (frozen twins intact).
    # [freeze-exception no. 18] same two files as `default` above; the three
    # design artifacts themselves are UNCHANGED (frozen twins intact).
    # [freeze-exception no. 26] see the note on `default` above; this fixture
    # moves 11 hook bodies for the same one-function shared-header change.
    "design_steering":
        "7e0872e972b13884443222eccffbd8a556319020cebea994db88925d6d8793c2",
}

EXPECTED_ACTION_COUNTS = {
    # [v2.4.0 code fold — GR2-03a] both fixtures +1 for the unconditional
    # assumption-ledger.md steering artifact (55 -> 56, 67 -> 68).
    # [v2.4.0 review fix — GR2-01 template ownership] both fixtures +1 again
    # for the unconditional .claude/specs/progress-template.md, split out of
    # the operator-edited INDEX.md so it is deliverable on upgrade
    # (56 -> 57, 68 -> 69).
    # [v2.5.0 DS-01] default/full_autonomous counts UNCHANGED (57/69): the
    # version bump moves one body (settings.json), adds no file; design steering
    # is off in both. The flag-on design_steering fixture is 59 = a 56-file
    # fullstack baseline + the 3 design artifacts.
    "default": 57,
    "full_autonomous": 69,
    "design_steering": 59,
}


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def run_fixture(label, yaml_text):
    _, plan = plan_actions(yaml_text)
    actual_digest = plan_digest_full(plan)
    actual_count = len(plan)

    if os.environ.get("GOLDEN_UPDATE") == "1":
        print(f"\n--- GOLDEN_UPDATE: {label} ---")
        print(f'  EXPECTED_DIGESTS["{label}"] = "{actual_digest}"')
        print(f'  EXPECTED_ACTION_COUNTS["{label}"] = {actual_count}')
        return

    expected = EXPECTED_DIGESTS[label]
    if expected == "<<TO_BE_FILLED>>":
        check(f"golden[{label}]: digest initialized",
              False,
              "    Run `GOLDEN_UPDATE=1 python3 tests/"
              "test_greenfield_golden.py` and paste the printed digest "
              "into EXPECTED_DIGESTS / EXPECTED_ACTION_COUNTS.")
        return

    detail = ""
    if actual_digest != expected:
        files = per_file_digests(plan)
        detail = ("    Greenfield plan changed. Per-file digests "
                  "(body_sha16  mode  kind      path):\n")
        for p, b, m, k in files:
            detail += f"      {b}  {m}  {k:8s}  {p}\n"
        detail += (
            f"    Expected aggregate digest: {expected}\n"
            f"    Actual   aggregate digest: {actual_digest}\n"
            f"    If this greenfield change is INTENTIONAL, re-run with "
            f"GOLDEN_UPDATE=1 and update EXPECTED_DIGESTS. Treat the "
            f"update as a freeze-exception decision.")
    check(f"golden[{label}]: plan digest byte-identical",
          actual_digest == expected, detail)

    expected_count = EXPECTED_ACTION_COUNTS[label]
    check(f"golden[{label}]: action count stable ({expected_count})",
          actual_count == expected_count,
          (f"    Expected {expected_count} actions, got {actual_count}. "
           f"build_plan added or removed files relative to baseline."))


run_fixture("default", FIXTURE_DEFAULT)
run_fixture("full_autonomous", FIXTURE_FULL_AUTONOMOUS)
run_fixture("design_steering", FIXTURE_DESIGN_STEERING)

# Determinism: same fixture digests identically across two construction
# passes in the same process. Guards against non-determinism creeping into
# any new template function (e.g. dict-order accident in Python <3.7-era
# patterns, or a hidden time/uuid read).
if os.environ.get("GOLDEN_UPDATE") != "1":
    for label, fixt in [("default", FIXTURE_DEFAULT),
                        ("full_autonomous", FIXTURE_FULL_AUTONOMOUS),
                        ("design_steering", FIXTURE_DESIGN_STEERING)]:
        _, p1 = plan_actions(fixt)
        _, p2 = plan_actions(fixt)
        check(f"determinism[{label}]: two passes produce identical digests",
              plan_digest_full(p1) == plan_digest_full(p2))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

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
    "default": "d8b4bdab48f31c17a54530f49c26935a4a86bcbffc1b356ae3df3260b3f6a7ff",
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
    "full_autonomous":
        "99784eb9bafd017e0cd0fa7a7c5f229d9b5b4cbdc80ba66a722abd093dcdd753",
}

EXPECTED_ACTION_COUNTS = {
    # [v2.4.0 code fold — GR2-03a] both fixtures +1 for the unconditional
    # assumption-ledger.md steering artifact (55 -> 56, 67 -> 68).
    # [v2.4.0 review fix — GR2-01 template ownership] both fixtures +1 again
    # for the unconditional .claude/specs/progress-template.md, split out of
    # the operator-edited INDEX.md so it is deliverable on upgrade
    # (56 -> 57, 68 -> 69).
    "default": 57,
    "full_autonomous": 69,
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

# Determinism: same fixture digests identically across two construction
# passes in the same process. Guards against non-determinism creeping into
# any new template function (e.g. dict-order accident in Python <3.7-era
# patterns, or a hidden time/uuid read).
if os.environ.get("GOLDEN_UPDATE") != "1":
    for label, fixt in [("default", FIXTURE_DEFAULT),
                        ("full_autonomous", FIXTURE_FULL_AUTONOMOUS)]:
        _, p1 = plan_actions(fixt)
        _, p2 = plan_actions(fixt)
        check(f"determinism[{label}]: two passes produce identical digests",
              plan_digest_full(p1) == plan_digest_full(p2))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

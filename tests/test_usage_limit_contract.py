#!/usr/bin/env python3
"""Usage-limit comment-contract suite (protocol 2.2.0, work item R7).

Standalone script — own pass/fail counter, exits non-zero on any failure.
NOT pytest. Run: python3 tests/test_usage_limit_contract.py

Emits the greenfield fixtures through build_plan and string-asserts the
normative surface the 2.2.0 usage-limit capability binds:

  * R1 — the three usage_limit_* config keys + defaults in loop-config.md
    and goal-config.md, co-located with the infra_* pair.
  * R2/R3 — the per-task skeleton (loop.sh / goal-loop.sh) dispatch flags
    and the usage-limit-vs-transient comment contract (Phase 9.5,
    AR2-corrected).
  * R4 — goal-loop.sh's judge-parity sentence.
  * R5 — auto.sh's exit_reason enum, run-summary render clause, AR2-01
    terminal runner rule, and AR2-09c key-less posture.
  * Negative — no usage_limit_* key leaks into auto-config.md.

These are comment contracts: the PRD (Bootstrap-Protocol-v2-2-0.md Phase 9.5
"Infrastructure-error handling", Recovery & State exit_reason enum, Phase 9.7)
treats the emitted comment wording as normative surface, so it is asserted
here rather than left to a byte-digest alone.
"""
import os
import re
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
            print(f"        {detail}")


# --------------------------------------------------------------------------- #
# Fixture (full_autonomous — the only fixture that emits the wrappers, the
# config files, and the runner). Mirrors tests/test_greenfield_golden.py's
# Fixture B.
# --------------------------------------------------------------------------- #
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


def emit(yaml_text):
    """Return {emitted-path: body} for every action in the plan."""
    cfg, errs = resolve_config(load_yaml(yaml_text))
    assert not errs, f"fixture must validate; got errors: {errs}"
    return {a["path"]: a["body"] for a in build_plan(cfg)}


FILES = emit(FIXTURE_FULL_AUTONOMOUS)


def body(rel):
    path = f".claude/{rel}"
    assert path in FILES, f"expected emitted file missing: {path}"
    return FILES[path]


def has(name, rel, needle):
    b = body(rel)
    check(name, needle in b,
          f"expected {needle!r} in {rel}")


def has_ci(name, rel, needle):
    """Case-insensitive substring (for prose sentences)."""
    b = body(rel).lower()
    check(name, needle.lower() in b,
          f"expected (case-insensitive) {needle!r} in {rel}")


LOOP_CFG = "loop-config.md"
GOAL_CFG = "goal-config.md"

# --------------------------------------------------------------------------- #
# R1 — config keys + defaults, co-located with the infra_* pair.
# --------------------------------------------------------------------------- #
for rel in (LOOP_CFG, GOAL_CFG):
    # Key+default in a single needle (the test_goal_evaluator_keys.py
    # convention) - a bare-key check would be a strict substring of these
    # and could never fail independently.
    has(f"R1[{rel}]: usage_limit_wait default reset-aware", rel,
        "usage_limit_wait: reset-aware")
    has(f"R1[{rel}]: usage_limit_max_wait_seconds default 21600", rel,
        "usage_limit_max_wait_seconds: 21600")
    has(f"R1[{rel}]: usage_limit_wait_jitter_seconds default 60", rel,
        "usage_limit_wait_jitter_seconds: 60")
    # Same block as infra_retry_seconds: the three keys sit immediately
    # after the infra_* pair with no intervening blank line / comment.
    has(f"R1[{rel}]: keys co-located with infra_retry_seconds block", rel,
        "infra_max_consecutive_failures: 2\n"
        "usage_limit_wait: reset-aware")
    check(f"R1[{rel}]: infra_retry_seconds present in the same block",
          "infra_retry_seconds:" in body(rel))

# --------------------------------------------------------------------------- #
# R2/R3 — per-task skeletons (loop.sh AND goal-loop.sh).
# --------------------------------------------------------------------------- #
for rel in ("loop.sh", "goal-loop.sh"):
    # R2 dispatch flags (added; --worktree retained).
    has(f"R2[{rel}]: --output-format stream-json --verbose", rel,
        "--output-format stream-json --verbose")
    has(f"R2[{rel}]: --worktree retained", rel, "--worktree")
    # R3 wire contract.
    has(f"R3[{rel}]: rate_limit_event named", rel, "rate_limit_event")
    has(f"R3[{rel}]: nested rate_limit_info object", rel, "rate_limit_info")
    has(f"R3[{rel}]: camelCase resetsAt wire key", rel, "resetsAt")
    has(f"R3[{rel}]: camelCase rateLimitType wire key", rel, "rateLimitType")
    has(f'R3[{rel}]: quoted "rejected" status', rel, '"rejected"')
    has(f"R3[{rel}]: usage-limit-reset-abandoned halt cause", rel,
        "usage-limit-reset-abandoned")
    has(f"R3[{rel}]: usage_limit_max_wait_seconds ceiling", rel,
        "usage_limit_max_wait_seconds")
    has_ci(f"R3[{rel}]: match by top-level `type` field", rel,
           "top-level `type`")
    has_ci(f"R3[{rel}]: does-not-consume-the-transient-retry", rel,
           "does not consume the transient retry")
    has_ci(f"R3[{rel}]: never-compute-your-own-reset", rel,
           "never compute your own reset time")
    has_ci(f"R3[{rel}]: fail-loud fallback clause", rel,
           "fall back to the transient path")
    has_ci(f"R3[{rel}]: fallback keyed on stopped emission", rel,
           "stops emitting")
    has(f"R3[{rel}]: CLAUDE_CODE_RETRY_WATCHDOG=1 watchdog note", rel,
        "CLAUDE_CODE_RETRY_WATCHDOG=1")
    has(f"R3[{rel}]: off routes to transient (key)", rel,
        "usage_limit_wait: off")
    has_ci(f"R3[{rel}]: off routes to transient (path)", rel,
           "takes the transient path")
    # The transient arm of the split is defined, not just referenced
    # (Phase 9.5 transient paragraph): the no-rejected-event classification
    # arm and the infra_* knobs the loop must consume.
    has_ci(f"R3[{rel}]: no-rejected-event arm routes to transient", rel,
           'no "rejected" rate_limit_event at all')
    has(f"R3[{rel}]: transient sleep knob named", rel, "infra_retry_seconds")
    has(f"R3[{rel}]: transient halt knob named", rel,
        "infra_max_consecutive_failures")

# goal-loop.sh judge-parity (R4); loop.sh must NOT carry it.
has_ci("R4[goal-loop.sh]: judge-parity path applies to the judge call",
       "goal-loop.sh", "judge call")
has_ci("R4[goal-loop.sh]: judge call takes the SAME reset-aware wait",
       "goal-loop.sh", "same reset-aware wait")
has_ci("R4[goal-loop.sh]: does not consume the judge retry-once",
       "goal-loop.sh", "does not consume the judge retry-once")
check("R4[loop.sh]: judge-parity clause absent from loop.sh (loop has no "
      "judge call)",
      "judge retry-once" not in body("loop.sh"))

# --------------------------------------------------------------------------- #
# R5 — auto.sh runner comment contract.
# --------------------------------------------------------------------------- #
AUTO = "auto.sh"
EXIT_REASONS = [
    "queue-empty",
    "deferred-only-remaining",
    "urgent-escalation",
    "three-consecutive-halts",
    "time-budget-exhausted",
    "token-budget-exhausted",
    "task-budget-exhausted",
    "signal-interrupt",
    "manual-halt-sentinel",
    "infrastructure-failure",
    "infrastructure-failure-crash-recovery",
    "operator-only-timeout",
    "usage-limit-reset-abandoned",
]
for reason in EXIT_REASONS:
    # Anchored to the enum block's line shape ("#   <reason>  <trigger>"),
    # not a free-floating substring - several literals (queue-empty,
    # infrastructure-failure, ...) also occur elsewhere in auto.sh, so an
    # unanchored match could not detect a deleted enum line.
    has(f"R5[auto.sh]: exit_reason enum lists {reason}", AUTO,
        "\n#   " + reason + "  ")
# Count guard against the EMITTED enum block (not the test's own list):
# extract the block between its header and the next section header, parse
# the "#   <value>  " lines, and require exact set equality.
_auto_body = body(AUTO)
_i0 = _auto_body.find("[exit_reason enum")
_i1 = _auto_body.find("[Morning-after")
check("R5[auto.sh]: enum block markers present and ordered",
      0 <= _i0 < _i1)
_enum_block = _auto_body[_i0:_i1] if 0 <= _i0 < _i1 else ""
_enum_keys = set(re.findall(r"^#   (\S+)\s{2,}", _enum_block, re.M))
check("R5[auto.sh]: enum block lists exactly the 13 exit_reason values",
      _enum_keys == set(EXIT_REASONS),
      f"emitted enum block keys: {sorted(_enum_keys)}")
# Load-bearing trigger qualifiers the enum-line-shape anchors cannot see
# (Recovery & State wording): halt-count scope and transitive blocking.
has_ci("R5[auto.sh]: three-consecutive-halts scoped within the run",
       AUTO, "within the run")
has_ci("R5[auto.sh]: operator-only-timeout blocking is transitive",
       AUTO, "transitively blocked on operator action")

has("R5[auto.sh]: Ended because line", AUTO, "Ended because")
has("R5[auto.sh]: render clause names rate_limit_type", AUTO,
    "rate_limit_type")
has("R5[auto.sh]: render clause names resets_at", AUTO, "resets_at")
# AR2-01 terminal runner rule - anchored to its own header, not a
# free-floating "terminal" (which also appears in "(terminal success)",
# "terminal exit", and "interactive terminal" elsewhere in auto.sh).
has_ci("R5[auto.sh]: abandon halt is terminal (AR2-01)", AUTO,
       "ar2-01,\n#  terminal.]")
has("R5[auto.sh]: AR2-01 marker", AUTO, "AR2-01")
has_ci("R5[auto.sh]: not record-and-continue", AUTO,
       '"record and continue"')
# Counted-toward-neither: one contiguous normative clause (PRD termination-
# table wording), asserted with comment-continuation wraps ("\n#  ...")
# normalized to spaces so scattered fragments cannot satisfy it.
_flat_auto = re.sub(r"\n#\s*", " ", body(AUTO).lower())
check("R5[auto.sh]: AR2-01 counted-toward-neither clause (contiguous)",
      "counts the halt toward neither the three-consecutive-halts threshold"
      " nor the infrastructure-failure threshold." in _flat_auto)
# AR2-09c key-less posture.
has_ci("R5[auto.sh]: runner posture is key-less", AUTO, "key-less")
has_ci("R5[auto.sh]: no runner-level infra_* keys", AUTO,
       "no runner-level infra_* keys")

# --------------------------------------------------------------------------- #
# Negative — no usage_limit_* key leaks into auto-config.md (AR2-09c: the
# runner tier is deliberately key-less).
# --------------------------------------------------------------------------- #
check("neg: auto-config.md carries no usage_limit_* key",
      "usage_limit" not in body("auto-config.md"),
      "auto-config.md must stay key-less for the usage-limit tier")

# --------------------------------------------------------------------------- #
# RC-03 citation integrity - the five re-pointed files cite the 2.2.0 doc
# and carry no stale v2-0-0 citation; the cited documents exist at the repo
# root (emitted skeletons tell operators to read them, so a missing doc is
# a release-integrity break, not a doc nit). Hook citations deliberately
# stay at v2-0-0 (freeze-exception no. 15) and are NOT asserted here.
# --------------------------------------------------------------------------- #
for rel in ("loop.sh", "goal-loop.sh", LOOP_CFG, GOAL_CFG, "auto.sh"):
    has(f"RC-03[{rel}]: cites Bootstrap-Protocol-v2-2-0.md", rel,
        "Bootstrap-Protocol-v2-2-0.md")
    check(f"RC-03[{rel}]: no stale v2-0-0 citation",
          "v2-0-0" not in body(rel))
for _doc in ("Bootstrap-Protocol-v2-2-0.md",
             "Bootstrap-Protocol-Companion-v2-2-0.md"):
    check(f"RC-03: cited spec doc exists at repo root: {_doc}",
          os.path.isfile(os.path.join(ROOT, _doc)))

# --------------------------------------------------------------------------- #
# Negative — the default (non-autonomous) fixture emits no usage-limit
# surface at all: no wrappers, no configs, and no usage_limit text leaking
# into any emitted file (hooks, settings, steering, ...).
# --------------------------------------------------------------------------- #
with open(os.path.join(ROOT, "bootstrap.config.yaml")) as _fh:
    _DEFAULT_FILES = emit(_fh.read())
_leaks = sorted(p for p, b in _DEFAULT_FILES.items() if "usage_limit" in b)
check("neg[default]: no usage_limit text in any default-fixture file",
      not _leaks, f"leaked into: {_leaks}")
check("neg[default]: default fixture emits no per-task wrappers",
      not any(p.endswith(("loop.sh", "goal-loop.sh", "auto.sh"))
              for p in _DEFAULT_FILES))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

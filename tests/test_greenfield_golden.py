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
    "default": "fc139d43688b67a3f78ae1e7de8fdf8e65a1d2aa2a3403dfdee6b4591a1a6f55",
    "full_autonomous":
        "78055b69b256d0f2929cbb251e6a0867be2ea826f7ae0f4b719526dc4155c283",
}

EXPECTED_ACTION_COUNTS = {
    "default": 54,
    "full_autonomous": 65,
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

#!/usr/bin/env python3
"""DW-P1 / DW-P3 tripwire — no workflow orchestration ever reaches emitted output.

Pins the one mechanically-enforceable clause of `.claude/dynamic-workflow-policy.md`:

  DW-P1  Nothing is ever emitted. No workflow script, runner, wrapper, or
         `.claude/` artifact describing one enters an installer plan.
  DW-P3  `lib/` and `bin/` never learn this exists — no module or script may
         import, invoke, or branch on a workflow.

WHY THIS EXISTS SEPARATELY FROM tests/test_greenfield_golden.py. The golden
digests would also move if orchestration were emitted — but re-baselining a
digest is a routine act (docs/changelog.md records golden re-baselines as
freeze exceptions no. 30, 31, 33, 34, 35 and 40). A future well-meant addition
therefore lands GREEN through the goldens, because re-baselining is the
documented response to a moved digest. A named invariant is a tripwire; a digest
is a diff. This file is the tripwire.

PREDICATE SPECIFICITY. A substring match on `workflow` is useless here:
lib/templates.py carries 14 legitimate occurrences — the `workflow.*` CONFIG
namespace (`workflow.implementer_isolation`, resolved into emitted prose) and
ordinary English ("Tests-first workflow per task"). That namespace governs
emitted subagent isolation and has nothing to do with the `Workflow` TOOL. So
the tokens below are the tool's own API surface and script preamble, never the
bare word. Section 0 proves they actually fire; section 3 proves the scan is
looking at real content rather than passing vacuously.

Run: python3 tests/test_dynamic_workflow_policy.py

NOTE: run with PYTHONDONTWRITEBYTECODE=1, or delete lib/__pycache__ afterwards.
Importing lib/ writes bytecode beside the source, which bin/run-tests' pollution
detector reports (policy DW-R3/DW-R4 — the rule this repo learned by tripping).
"""
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
# The predicate
# --------------------------------------------------------------------------- #
# Every token is either part of the Workflow tool's API surface, its mandatory
# script preamble, or a string that only a fan-out feature would emit. Bare
# `agent(` / `phase(` / `parallel(` are deliberately EXCLUDED: emitted prose
# could plausibly write "the agent(s)" and produce a false positive, which would
# train a future maintainer to weaken this file. The `await ` prefix makes them
# unambiguously JavaScript.
ORCHESTRATION_TOKENS = [
    "export const meta",       # mandatory preamble of every workflow script
    "subagent_type",
    "run_in_background",
    "await agent(",
    "await parallel(",
    "await pipeline(",
    ".claude/workflows",
    "min(16, cores",           # the tool's concurrency cap, which reads no config
    "dynamic-workflow-policy",  # the policy itself is maintainer-side, never emitted
    "fan-out",                 # DW-P2: never described to an operator as available
    "fanout",
]

# Paths that would carry orchestration if it were ever emitted.
ORCHESTRATION_PATH_MARKERS = [".claude/workflows", ".workflow.js", "workflow.sh"]


def scan(text):
    """Return the orchestration tokens present in `text`."""
    return [t for t in ORCHESTRATION_TOKENS if t in text]


# --------------------------------------------------------------------------- #
# Fixtures — every emission path, not only the default one
# --------------------------------------------------------------------------- #
with open(os.path.join(ROOT, "bootstrap.config.yaml")) as _fh:
    FIXTURE_DEFAULT = _fh.read()

# Mirrors tests/test_greenfield_golden.py fixture B: exercises every conditional
# template the default never reaches (all three autonomous modes, tdd required).
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

# Mirrors fixture C: the DS-01 flag-gated additions.
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

# Retrofit is out of scope for the POLICY by owner decision (backlog J-21), but
# it is not out of scope for DW-P1: `mode: retrofit` is an emission path, and
# "nothing is ever emitted" has to hold on every path or it holds on none.
FIXTURE_RETROFIT = """mode: "retrofit"
project:
  name: r-svc
  archetype: service
secrets:
  enabled: true
deps:
  enabled: true
  approved: []
commands:
  test: "true"
  lint: "true"
  format: "true"
retrofit:
  spec_strategy: "forward-only"
  legacy_allowlist:
    - "src/**"
    - "tests/**"
  retrofit_active: true
  r08_committed: true
"""

FIXTURES = [
    ("default", FIXTURE_DEFAULT),
    ("full_autonomous", FIXTURE_FULL_AUTONOMOUS),
    ("design_steering", FIXTURE_DESIGN_STEERING),
    ("retrofit_service", FIXTURE_RETROFIT),
]


def plan_for(yaml_text):
    cfg, errs = resolve_config(load_yaml(yaml_text))
    assert not errs, f"fixture must validate; got errors: {errs}"
    return build_plan(cfg)


PLANS = [(label, plan_for(text)) for label, text in FIXTURES]


# --------------------------------------------------------------------------- #
# 0. Deny capability FIRST — a tripwire never shown to fire is not a tripwire
# --------------------------------------------------------------------------- #
# This section exists because of a finding from this policy's own adversarial
# review: "the tripwire has no predicate." A clean scan proves nothing unless the
# scanner is known to catch the thing it is scanning for. Same discipline as the
# X-36v/w sweep, which asserted deny-capability before measuring allow/deny.
print("\n=== Section 0: the predicate catches a planted violation ===")

PLANTED = [
    ("workflow script preamble",
     "export const meta = {\n  name: 'emit-fanout',\n}\n"),
    ("an await agent() call",
     "const r = await agent('review this', {schema: S})\n"),
    ("a pipeline fan-out",
     "const rs = await pipeline(items, s1, s2)\n"),
    ("an emitted operator instruction to fan out",
     "Run a fan-out across your task queue for faster review.\n"),
    ("the tool's uncapped concurrency default",
     "Concurrency is min(16, cores-2) and reads no config.\n"),
    ("a reference to the maintainer-side policy",
     "See .claude/dynamic-workflow-policy.md for fan-out rules.\n"),
]
for label, payload in PLANTED:
    hits = scan(payload)
    check(f"planted violation is detected: {label}",
          len(hits) > 0,
          f"    predicate returned no hits for payload: {payload!r}")

# And the converse: the LEGITIMATE workflow.* config namespace must NOT trip it.
# If it did, this file would fail on a clean tree and get weakened or deleted.
LEGITIMATE = [
    ("workflow.* config key in emitted prose",
     "`workflow.implementer_isolation` resolved to `none`.\n"),
    ("ordinary English use of the word",
     "description: Tests-first workflow per task.\n"),
    ("emitted worktree isolation",
     "isolation: worktree\n"),
]
for label, payload in LEGITIMATE:
    hits = scan(payload)
    check(f"legitimate emission does NOT trip the predicate: {label}",
          hits == [],
          f"    false positive on {payload!r} -> {hits}")


# --------------------------------------------------------------------------- #
# 1. DW-P1 — no emitted BODY carries orchestration, on any path
# --------------------------------------------------------------------------- #
print("\n=== Section 1: DW-P1, no orchestration in any emitted body ===")

for label, plan in PLANS:
    offenders = []
    for a in plan:
        hits = scan(a["body"])
        if hits:
            offenders.append((a["path"], hits))
    check(f"{label}: no emitted body carries an orchestration token",
          offenders == [],
          "\n".join(f"    {p}: {h}" for p, h in offenders))


# --------------------------------------------------------------------------- #
# 2. DW-P1 — no emitted PATH is an orchestration artifact
# --------------------------------------------------------------------------- #
print("\n=== Section 2: DW-P1, no orchestration path emitted ===")

for label, plan in PLANS:
    bad = [a["path"] for a in plan
           if any(m in a["path"] for m in ORCHESTRATION_PATH_MARKERS)]
    check(f"{label}: no plan action writes an orchestration path",
          bad == [], f"    {bad}")

    js = [a["path"] for a in plan if a["path"].endswith(".js")]
    check(f"{label}: no plan action emits a .js file",
          js == [], f"    {js}")


# --------------------------------------------------------------------------- #
# 3. Non-vacuity — prove the scan is reading real content
# --------------------------------------------------------------------------- #
# A predicate that matches nothing passes section 1 trivially, including on an
# empty plan. These assertions fail loudly if the fixtures stop producing content
# or if build_plan's action shape changes underneath this file.
print("\n=== Section 3: the scan is not vacuous ===")

for label, plan in PLANS:
    check(f"{label}: plan is non-empty", len(plan) > 10, f"    {len(plan)} actions")
    total = sum(len(a["body"]) for a in plan)
    check(f"{label}: emitted bodies carry real content (>50 KB)",
          total > 50_000, f"    {total} bytes")

# The legitimate workflow.* namespace must still be emitting. If this stops being
# true, the emission surface changed shape and section 1's clean result may be
# clean for the wrong reason.
default_plan = dict(PLANS)["default"]
worktree_hits = [a["path"] for a in default_plan if "worktree" in a["body"]]
check("default: the legitimate workflow.* isolation surface is still emitted",
      len(worktree_hits) > 0,
      "    no emitted body mentions 'worktree' — emission shape changed; "
      "re-verify that section 1 is clean for the right reason")


# --------------------------------------------------------------------------- #
# 4. DW-P3 — lib/ and bin/ carry no orchestration
# --------------------------------------------------------------------------- #
# Scoped to BOTH, per the policy: bin/bootstrap-install, bin/bootstrap-interview
# and bin/retrofit-interview are the CLI entry points the seam contract's 3.2 is
# written about. A rule scoped to lib/ alone reads as covered while leaving them
# open — which is exactly the "a rule encoded in one consumer reads as covered"
# failure this repo has paid for.
print("\n=== Section 4: DW-P3, lib/ and bin/ never learn this exists ===")

SOURCE_DIRS = [("lib", os.path.join(ROOT, "lib")), ("bin", os.path.join(ROOT, "bin"))]

for label, d in SOURCE_DIRS:
    offenders = []
    for name in sorted(os.listdir(d)):
        path = os.path.join(d, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        # The policy filename is allowed to appear nowhere in lib/ or bin/;
        # the whole point of DW-P3 is that neither knows it exists.
        hits = scan(text)
        if hits:
            offenders.append((name, hits))
    check(f"{label}/: no source file references workflow orchestration",
          offenders == [],
          "\n".join(f"    {n}: {h}" for n, h in offenders))

    js = [n for n in os.listdir(d) if n.endswith(".js")]
    check(f"{label}/: contains no .js file", js == [], f"    {js}")


# --------------------------------------------------------------------------- #
# 5. The policy document itself is maintainer-side only
# --------------------------------------------------------------------------- #
print("\n=== Section 5: the policy is not protocol surface ===")

POLICY = os.path.join(ROOT, ".claude", "dynamic-workflow-policy.md")
check("the policy file exists where the tests expect it",
      os.path.isfile(POLICY), f"    missing: {POLICY}")

for label, plan in PLANS:
    emitted = [a["path"] for a in plan if "dynamic-workflow-policy" in a["path"]]
    check(f"{label}: the policy document is never emitted",
          emitted == [], f"    {emitted}")

# It must also touch no golden digest — i.e. it is not read by the installer.
# Covered structurally by section 4 (lib/ never references it), asserted here
# against the policy's own header claim so the two cannot drift apart.
with open(POLICY, encoding="utf-8") as fh:
    policy_text = fh.read()
check("the policy still claims to be non-protocol-surface",
      "Not protocol surface" in policy_text,
      "    the header claim was removed; DW-P1/DW-P3's justification changed "
      "and this suite's scope should be re-derived")


# --------------------------------------------------------------------------- #
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

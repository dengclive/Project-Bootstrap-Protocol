#!/usr/bin/env python3
"""Finding 1 (owner review of PR #5) — goal-config.md keys vs Phase 9.6.

The normative Phase 9.6 enumeration (Bootstrap-Protocol-v2-0-0.md:1336,
:1382) names `evaluator_model` (default haiku), `evaluator_disagreement_
threshold` (default 3), and `evaluator_feedback_history_depth` (default 2).
The 1.9.0 emission misnamed the first as `judge_model` and omitted the
other two. Per the spec-leads-code ruling: the emitted key is renamed,
the missing doc-named keys are added, and goal-loop.sh dual-reads
`judge_model` as a DEPRECATED alias honoured only when `evaluator_model`
is absent, with a loud warning.

Run: python3 tests/test_goal_evaluator_keys.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

BIN = os.path.join(ROOT, "bin", "bootstrap-install")

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


FULL = """project:
  name: evalkeys
  archetype: ai-agent
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: true
principles:
  tdd_policy: required
commands:
  test: "true"
  lint: "true"
"""

d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(FULL)
    r = subprocess.run([sys.executable, BIN, "-C", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    gc_path = os.path.join(d, ".claude", "goal-config.md")
    gc = open(gc_path).read()

    # --- Emission sweep against the Phase 9.6 normative list ----------- #
    check("9.6: evaluator_model: haiku emitted (normative name + default)",
          "evaluator_model: haiku" in gc)
    check("9.6: judge_model no longer emitted",
          "\njudge_model:" not in gc)
    check("9.6: evaluator_disagreement_threshold: 3 emitted",
          "evaluator_disagreement_threshold: 3" in gc)
    check("9.6: evaluator_feedback_history_depth: 2 emitted",
          "evaluator_feedback_history_depth: 2" in gc)
    check("9.6: max_iterations: 10 emitted", "max_iterations: 10" in gc)
    check("9.6: unnamed-key items documented in the emitted file "
          "(retry posture / checklist / audio-cue overrides)",
          "retry-once-then-halt" in gc and "audio-cue overrides" in gc)

    goal_sh = os.path.join(d, ".claude", "goal-loop.sh")
    loop_sh = os.path.join(d, ".claude", "loop.sh")
    check("scope: loop.sh carries no judge-model resolution",
          "EVALUATOR_MODEL" not in open(loop_sh).read())
    check("scope: goal-loop.sh resolves evaluator_model with judge_model "
          "as deprecated alias",
          "evaluator_model" in open(goal_sh).read()
          and "judge_model" in open(goal_sh).read())

    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = d

    def run_goal():
        # "t1" has no task file, so the wrapper exits at the eligibility
        # guard - AFTER config resolution, which is what we observe here.
        return subprocess.run(["bash", goal_sh, "t1"], capture_output=True,
                              text=True, env=env)

    # (1) Normative key present (the emitted default) -> no warning.
    r = run_goal()
    check("alias: no deprecation warning when evaluator_model is present",
          "DEPRECATED" not in r.stderr, r.stderr)

    # (2) Legacy config with judge_model only -> alias honoured, LOUD.
    open(gc_path, "w").write("# legacy\nmax_iterations: 10\n"
                             "judge_model: sonnet\n")
    r = run_goal()
    check("alias: judge_model-only config triggers loud deprecation",
          "DEPRECATED" in r.stderr and "evaluator_model" in r.stderr,
          r.stderr)
    log = open(os.path.join(d, ".claude", "logs", "hooks.log")).read()
    check("alias: deprecated-alias use is logged",
          "deprecated judge_model alias honoured" in log)

    # (3) Both keys present -> evaluator_model wins, alias ignored, silent.
    open(gc_path, "w").write("evaluator_model: haiku\n"
                             "judge_model: sonnet\n")
    r = run_goal()
    check("alias: honoured ONLY when evaluator_model is absent",
          "DEPRECATED" not in r.stderr, r.stderr)

    # (4) Neither key -> silent fallback to the Phase 9.6 default (haiku),
    # no spurious deprecation noise.
    open(gc_path, "w").write("max_iterations: 10\n")
    r = run_goal()
    check("alias: absent both keys -> no deprecation warning",
          "DEPRECATED" not in r.stderr, r.stderr)
finally:
    shutil.rmtree(d, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

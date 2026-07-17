#!/usr/bin/env python3
"""R-3 (IC-4) — LLM advisor default model + loud deterministic fallback.

Spec: .claude/specs/bootstrap-v2/requirements.md (AC-3-1..AC-3-3).
The advisor is proposes-never-decides with deterministic-fallback-on-any-
failure; these tests pin the new default model ID and prove the fallback
stays loud and the proposal stays valid when the model is unreachable or
returns garbage.

Run: python3 tests/test_advisor_model.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

import llm_advisor                                    # noqa: E402
from interview import build_proposal                  # noqa: E402

BIN = os.path.join(ROOT, "bin", "bootstrap-interview")

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


PRD = "# Demo Service\nA REST API service for managing widgets.\n"

# --------------------------------------------------------------------------- #
# AC-3-1: the default resolves to a live ID; the retired string is gone.
# "claude-sonnet-5" is the current Sonnet's Claude API ID and alias (a
# dateless pinned snapshot), verified against the platform.claude.com models
# overview on 2026-07-17. "claude-sonnet-4-20250514" is retired.
# --------------------------------------------------------------------------- #
src = open(os.path.join(ROOT, "lib", "llm_advisor.py")).read()
check("AC-3-1: retired claude-sonnet-4-20250514 absent from source",
      "claude-sonnet-4-20250514" not in src)
check("AC-3-1: default is claude-sonnet-5",
      '"claude-sonnet-5"' in src)
check("AC-3-1: BOOTSTRAP_INTERVIEW_LLM_MODEL override retained",
      "BOOTSTRAP_INTERVIEW_LLM_MODEL" in src)

# --------------------------------------------------------------------------- #
# AC-3-2a: --llm with NO reachable model -> loud fallback, valid proposal
# --------------------------------------------------------------------------- #
saved_env = {k: os.environ.pop(k, None)
             for k in ("ANTHROPIC_API_KEY", "BOOTSTRAP_INTERVIEW_LLM_FAKE",
                       "BOOTSTRAP_INTERVIEW_LLM")}
try:
    det = build_proposal(PRD, project_fallback="demo", use_llm=False)
    out = llm_advisor.maybe_refine(PRD, det, enabled=True)
    check("AC-3-2a: unreachable model -> used=False",
          out.get("_llm", {}).get("used") is False)
    notices = out.get("_llm", {}).get("notices", [])
    check("AC-3-2a: fallback is LOUD (visible notice present)",
          any("Fell back to the deterministic heuristics" in n
              for n in notices), repr(notices))
    check("AC-3-2a: proposal fields intact (deterministic values kept)",
          out["archetype"]["value"] == det["archetype"]["value"]
          and out["prd_tier"]["value"] == det["prd_tier"]["value"])

    # AC-3-2b: model reachable but returns garbage -> same loud fallback
    os.environ["BOOTSTRAP_INTERVIEW_LLM_FAKE"] = "this is not json at all"
    out2 = llm_advisor.maybe_refine(PRD, det, enabled=True)
    check("AC-3-2b: failing model -> used=False",
          out2.get("_llm", {}).get("used") is False)
    notices2 = out2.get("_llm", {}).get("notices", [])
    check("AC-3-2b: failure notice is loud and explains the fallback",
          any("call/parse failed" in n
              and "Fell back to the deterministic heuristics" in n
              for n in notices2), repr(notices2))
    check("AC-3-2b: proposal still valid and deterministic-valued",
          out2["archetype"]["value"] == det["archetype"]["value"])
    del os.environ["BOOTSTRAP_INTERVIEW_LLM_FAKE"]

    # AC-3-2c: end-to-end CLI — analyze --llm with a garbage responder still
    # exits 0, writes the interview file, and surfaces the notice on stdout.
    d = tempfile.mkdtemp()
    try:
        open(os.path.join(d, "PRD.md"), "w").write(PRD)
        env = dict(os.environ)
        env["BOOTSTRAP_INTERVIEW_LLM_FAKE"] = "garbage {{{ not json"
        r = subprocess.run(
            [sys.executable, BIN, "analyze", "--prd", "PRD.md",
             "-o", "iv.md", "--llm"],
            cwd=d, capture_output=True, text=True, env=env)
        check("AC-3-2c: analyze --llm with failing model exits 0",
              r.returncode == 0, r.stderr)
        check("AC-3-2c: interview file still written",
              os.path.exists(os.path.join(d, "iv.md")))
        check("AC-3-2c: fallback notice surfaced to the operator",
              "Fell back to the deterministic heuristics" in r.stdout,
              repr(r.stdout))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --------------------------------------------------------------------- #
    # AC-3-3: commands are never sent to the model (existing behavior,
    # asserted unchanged): the prompt contains no commands surface and
    # explicitly rules it out; command-shaped keys in a model response are
    # ignored by the merge.
    # --------------------------------------------------------------------- #
    prompt = llm_advisor._build_prompt(PRD, det)
    check("AC-3-3: prompt declares commands out of scope",
          "Do NOT propose test/lint/format commands" in prompt)
    check("AC-3-3: no commands_* field appears in the prompt",
          all(k not in prompt for k in
              ("commands_test", "commands_lint", "commands_format",
               "commands_typecheck", "commands_ci_local")))
    os.environ["BOOTSTRAP_INTERVIEW_LLM_FAKE"] = (
        '{"archetype":{"value":"service","confidence":"high",'
        '"rationale":"x"},"commands":{"test":"rm -rf /"},'
        '"commands_test":"evil"}')
    out3 = llm_advisor.maybe_refine(PRD, det, enabled=True)
    check("AC-3-3: command-shaped keys in model output are ignored",
          "commands" not in out3 and "commands_test" not in out3)
    del os.environ["BOOTSTRAP_INTERVIEW_LLM_FAKE"]
finally:
    for k, v in saved_env.items():
        if v is not None:
            os.environ[k] = v

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

#!/usr/bin/env python3
"""Self-contained test suite for the decision-layer interview tool.

Run: python3 tests/test_interview.py

Mirrors tests/test_installer.py's harness (check(name, cond), final tally,
exit code). Covers the session constraints explicitly:
  * proposes / never silently decides (ambiguity -> OPEN QUESTION)
  * archetype + PRD-tier mapping from Bootstrap-Protocol-v2-0-0.md tables
  * tier upgrade-not-downgrade
  * principles SOURCED from defaults (not duplicated)
  * commands.* always emitted empty + flagged
  * emitted config round-trips minyaml AND passes --print-config
  * queue-mode invariant can never be violated by a generated draft
  * determinism of the proposal core
  * analyze/synthesize vs interactive equivalence
"""
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

import prd_heuristics as H            # noqa: E402
from configemit import emit           # noqa: E402
from defaults import (PRINCIPLE_STARTERS,   # noqa: E402
                      resolve_config)
from minyaml import load_yaml          # noqa: E402
import interview as IV                 # noqa: E402

BIN = os.path.join(ROOT, "bin", "bootstrap-interview")
INSTALL_BIN = os.path.join(ROOT, "bin", "bootstrap-install")
SAMPLE = os.path.join(ROOT, "examples", "sample-prd.md")
passed = failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")


SAMPLE_TEXT = open(SAMPLE).read()

# --------------------------------------------------------------------------- #
# Archetype mapping
# --------------------------------------------------------------------------- #
a = H.propose_archetype(SAMPLE_TEXT)
check("archetype: sample PRD -> service", a["value"] == "service")
check("archetype: confident on clear PRD", a["confidence"] in ("high", "medium"))

cli_prd = "A command-line tool. CLI with subcommands, reads stdin, writes stdout."
check("archetype: CLI PRD -> cli",
      H.propose_archetype(cli_prd)["value"] == "cli")

ml = "An ETL data pipeline for a training pipeline producing an ML model."
check("archetype: ML PRD -> data-ml",
      H.propose_archetype(ml)["value"] == "data-ml")

ambiguous = "A system. It does things. Users use it."
amb = H.propose_archetype(ambiguous)
check("archetype: ambiguous -> OPEN QUESTION (not silently decided)",
      amb["confidence"] == H.CONF_OPEN and "open_question" in amb)

contested = ("A python library and SDK published to pypi, that also runs as a "
             "backend microservice with rest api endpoints and a worker.")
con = H.propose_archetype(contested)
check("archetype: contested within margin -> OPEN QUESTION",
      con["confidence"] == H.CONF_OPEN)

# --------------------------------------------------------------------------- #
# PRD tier: floor from archetype, upgrade-not-downgrade
# --------------------------------------------------------------------------- #
t_cli = H.propose_prd_tier("a simple cli", "cli")
check("tier: cli floor is micro", t_cli["value"] == "micro")

t_cli_up = H.propose_prd_tier(
    "a cli with personas, user journeys, non-goals and risks", "cli")
check("tier: cli upgraded to standard on multi-stakeholder signals",
      t_cli_up["value"] == "standard")

t_plat = H.propose_prd_tier("a platform", "platform")
check("tier: platform floor is full", t_plat["value"] == "full")

t_no_down = H.propose_prd_tier("trivial one pager", "service")
check("tier: never downgraded below archetype floor",
      H.TIER_ORDER[t_no_down["value"]] >= H.TIER_ORDER["standard"])

t_full = H.propose_prd_tier(
    "service with competitive analysis and phased rollout", "service")
check("tier: full signals upgrade service above floor",
      t_full["value"] == "full")

# --------------------------------------------------------------------------- #
# Principles sourced from defaults, not duplicated
# --------------------------------------------------------------------------- #
pr = H.propose_principles(SAMPLE_TEXT, "service")
check("principles: starter set IS defaults.PRINCIPLE_STARTERS['service']",
      pr["starter_set"] == list(PRINCIPLE_STARTERS["service"]))
check("principles: PRD security+latency signals proposed as additions",
      any("Security" in x["principle"] for x in pr["proposed_additions"]) and
      any("Latency" in x["principle"] for x in pr["proposed_additions"]))
check("principles: additions are appended, starter order preserved",
      pr["ranked"][:3] == list(PRINCIPLE_STARTERS["service"]))

# sentinel: if defaults changes, interview output changes with it
_orig = PRINCIPLE_STARTERS["cli"]
check("principles: cli set mirrors defaults exactly",
      H.propose_principles("x", "cli")["starter_set"] == list(_orig))

# --------------------------------------------------------------------------- #
# commands.* never guessed
# --------------------------------------------------------------------------- #
prop = IV.build_proposal(SAMPLE_TEXT)
ans = IV.default_answers(prop)
check("commands: all five emitted empty by default",
      all(ans[k] == "" for k in
          ("commands_test", "commands_lint", "commands_format",
           "commands_typecheck", "commands_ci_local")))
cfg = IV.answers_to_config(ans)
check("commands: config commands block all empty strings",
      all(v == "" for v in cfg["commands"].values()))

# --------------------------------------------------------------------------- #
# Emitted config: round-trips minyaml AND validates via resolve_config
# --------------------------------------------------------------------------- #
yaml_text = emit(cfg)
reparsed = load_yaml(yaml_text)
check("emit: round-trips through minyaml (parser contract holds)",
      reparsed["project"]["archetype"] == "service" and
      reparsed["principles"]["ranked"][0] ==
      "Clear errors over silent fallbacks")
_, errs = resolve_config(reparsed)
check("emit: re-parsed config passes resolve_config", errs == [])

# emitter immune to PRD-injected YAML metacharacters
nasty = ('# Project: evil: value\n\n## Problem\n'
         'A service api endpoint worker with: colons #hashes "quotes" '
         'and: more: colons.\n')
np = IV.build_proposal(nasty)
na = IV.default_answers(np)
nc = IV.answers_to_config(na)
nyaml = emit(nc)
try:
    rp = load_yaml(nyaml)
    ok = isinstance(rp, dict) and "project" in rp
except Exception:
    ok = False
check("emit: PRD metacharacters do not break the parse", ok)

# R-1: sanitization must be observable, not silent
_w: list = []
emit({"project": {"name": 'a"b\\c'}}, warnings=_w)
check("R-1: emit reports sanitized values via warnings sink",
      any("project.name" in x for x in _w))
_w2: list = []
emit({"project": {"name": "clean-name"}}, warnings=_w2)
check("R-1: clean values produce no spurious warnings", _w2 == [])

# --------------------------------------------------------------------------- #
# Queue-mode invariant can never be violated by a generated draft
# --------------------------------------------------------------------------- #
modes = H.propose_autonomous_modes(
    "fully autonomous unattended overnight self-driving system")
check("modes: queue never proposed without loop|goal",
      not modes["queue_mode_enabled"] or
      modes["loop_mode_enabled"] or modes["goal_supervised_mode_enabled"])
check("modes: autonomy interest still defaults all OFF + OPEN QUESTION",
      modes["loop_mode_enabled"] is False and
      "open_question" in modes)

# even a maliciously-crafted answers dict can't emit an invalid queue combo
bad_ans = dict(ans)
bad_ans["queue_mode_enabled"] = True
bad_cfg = IV.answers_to_config(bad_ans)
_, bad_errs = resolve_config(bad_cfg)
check("modes: queue+no-loop/goal answers -> resolve_config rejects (gate works)",
      any("queue_mode" in e for e in bad_errs))

# --------------------------------------------------------------------------- #
# Determinism of the proposal core
# --------------------------------------------------------------------------- #
p1 = IV.build_proposal(SAMPLE_TEXT)
p2 = IV.build_proposal(SAMPLE_TEXT)
check("determinism: identical PRD -> identical proposal",
      IV.render_interview(p1, "x") == IV.render_interview(p2, "x"))

# --------------------------------------------------------------------------- #
# Interview file round-trip: render -> parse -> finalize
# --------------------------------------------------------------------------- #
rendered = IV.render_interview(prop, SAMPLE)
parsed = IV.parse_interview_answers(rendered)
check("interview: render -> parse recovers all answer keys",
      set(parsed.keys()) == set(IV.ANSWER_KEYS))
check("interview: parsed defaults equal default_answers",
      parsed["archetype"] == ans["archetype"] and
      parsed["principles_ranked"] == ans["principles_ranked"])

missing = rendered.replace(IV.ANSWERS_END, "")
try:
    IV.parse_interview_answers(missing)
    check("interview: missing ANSWERS block raises", False)
except ValueError:
    check("interview: missing ANSWERS block raises", True)

# --------------------------------------------------------------------------- #
# analyze/synthesize vs interactive equivalence (same core, two front-ends)
# --------------------------------------------------------------------------- #
with tempfile.TemporaryDirectory() as d:
    prd = os.path.join(d, "p.md")
    open(prd, "w").write(SAMPLE_TEXT)

    r1 = subprocess.run([sys.executable, BIN, "analyze", "--prd", prd,
                          "-o", os.path.join(d, "iv.md")],
                         capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, BIN, "synthesize",
                          "-i", os.path.join(d, "iv.md"),
                          "-o", os.path.join(d, "q.yaml")],
                         capture_output=True, text=True, cwd=d)
    check("e2e: analyze exits 0", r1.returncode == 0)
    check("e2e: synthesize exits 0 and validates",
          r2.returncode == 0 and "print-config" in r2.stdout)

    # interactive with all-default (empty) answers over scripted stdin
    stdin_all_defaults = "\n" * 40
    r3 = subprocess.run([sys.executable, BIN, "interactive", "--prd", prd,
                          "-o", os.path.join(d, "i.yaml")],
                         input=stdin_all_defaults,
                         capture_output=True, text=True, cwd=d)
    check("e2e: interactive (all defaults) exits 0 and validates",
          r3.returncode == 0 and "print-config" in r3.stdout)

    q_yaml = open(os.path.join(d, "q.yaml")).read()
    i_yaml = open(os.path.join(d, "i.yaml")).read()
    check("e2e: questionnaire-default == interactive-default config",
          q_yaml == i_yaml)

    # the emitted config actually drives the installer
    r4 = subprocess.run([sys.executable, INSTALL_BIN, "-c",
                          os.path.join(d, "q.yaml"), "-C", d, "--dry-run"],
                         capture_output=True, text=True)
    check("e2e: generated config drives installer (dry-run ok)",
          r4.returncode == 0 and "files planned" in r4.stdout)

    # interactive guard: queue without loop/goal must self-correct, not emit invalid
    qonly = ("\n" * 9) + "false\nfalse\ntrue\n" + ("\n" * 6)
    r5 = subprocess.run([sys.executable, BIN, "interactive", "--prd", prd,
                          "-o", os.path.join(d, "g.yaml")],
                         input=qonly, capture_output=True, text=True, cwd=d)
    g_yaml = open(os.path.join(d, "g.yaml")).read()
    check("e2e: interactive queue-without-loop self-corrects to valid config",
          r5.returncode == 0 and "queue_mode_enabled: false" in g_yaml)

# --------------------------------------------------------------------------- #
# Optional LLM advisor (non-default) - opt-in, loud fallback, bounded refine
# --------------------------------------------------------------------------- #
import llm_advisor as LLM  # noqa: E402

# default path is unaffected and still deterministic
det_a = IV.build_proposal(SAMPLE_TEXT)
det_b = IV.build_proposal(SAMPLE_TEXT)
check("llm: default (use_llm=False) unchanged + deterministic",
      "_llm" not in det_a and
      IV.render_interview(det_a, "x") == IV.render_interview(det_b, "x"))

# requested but no model reachable -> loud fallback, deterministic content
os.environ.pop("BOOTSTRAP_INTERVIEW_LLM_FAKE", None)
os.environ.pop("ANTHROPIC_API_KEY", None)
fb = IV.build_proposal(SAMPLE_TEXT, use_llm=True)
check("llm: no model -> loud fallback notice",
      fb["_llm"]["used"] is False and
      any("Fell back" in n for n in fb["_llm"]["notices"]))
check("llm: fallback keeps deterministic archetype",
      fb["archetype"]["value"] == det_a["archetype"]["value"])

# fake responder -> refinement applied within bounds
os.environ["BOOTSTRAP_INTERVIEW_LLM_FAKE"] = json.dumps({
    "archetype": {"value": "ai-agent", "confidence": "high",
                  "rationale": "agent orchestrator"},
    "prd_tier": {"value": "full", "confidence": "medium", "rationale": "x"},
    "tdd_policy": {"value": "required", "confidence": "high", "rationale": "x"},
    "principle_additions": [{"principle": "Evals gate prompt changes",
                             "rationale": "agent"}],
    "secrets_enabled": {"value": True, "confidence": "high", "rationale": "x"},
    "deps_enabled": {"value": True, "confidence": "low", "rationale": "x"},
})
ref = IV.build_proposal(SAMPLE_TEXT, use_llm=True)
check("llm: refinement applies archetype/tier/tdd",
      ref["archetype"]["value"] == "ai-agent" and
      ref["prd_tier"]["value"] == "full" and
      ref["tdd_policy"]["value"] == "required")
check("llm: principle additions kept, starter set still from defaults",
      ref["principles"]["starter_set"] == list(PRINCIPLE_STARTERS["service"])
      and any("Evals gate" in a["principle"]
              for a in ref["principles"]["proposed_additions"]))

# malicious / invalid model output is bounds-rejected; floor held
os.environ["BOOTSTRAP_INTERVIEW_LLM_FAKE"] = json.dumps({
    "archetype": {"value": "WORLD_DOMINATION", "confidence": "high"},
    "prd_tier": {"value": "micro", "confidence": "high"},   # below floor
    "tdd_policy": {"value": "bogus", "confidence": "high"},
    "principle_additions": "not a list",
    "secrets_enabled": {"value": "yesplease"},
    "deps_enabled": {},
})
bad = IV.build_proposal(SAMPLE_TEXT, use_llm=True)
check("llm: invalid archetype rejected -> deterministic kept",
      bad["archetype"]["value"] == det_a["archetype"]["value"])
check("llm: tier downgrade below floor rejected",
      LLM.H.TIER_ORDER[bad["prd_tier"]["value"]]
      >= LLM.H.TIER_ORDER[det_a["prd_tier"]["floor"]])
check("llm: invalid tdd rejected -> deterministic kept",
      bad["tdd_policy"]["value"] == det_a["tdd_policy"]["value"])

# a refined proposal still produces a config that validates, commands empty
ans_ref = IV.default_answers(ref)
cfg_ref = IV.answers_to_config(ans_ref)
_, errs_ref = resolve_config(cfg_ref)
check("llm: refined proposal still yields a valid config", errs_ref == [])
check("llm: commands.* never populated by the model",
      all(v == "" for v in cfg_ref["commands"].values()))

# low-confidence model output still becomes an OPEN QUESTION (no silent decide)
os.environ["BOOTSTRAP_INTERVIEW_LLM_FAKE"] = json.dumps({
    "archetype": {"value": "platform", "confidence": "open",
                  "rationale": "genuinely unsure"},
    "prd_tier": {"value": "full", "confidence": "low", "rationale": "x"},
    "tdd_policy": {"value": "encouraged", "confidence": "low"},
    "principle_additions": [], "secrets_enabled": {"value": True},
    "deps_enabled": {"value": True},
})
oq = IV.build_proposal(SAMPLE_TEXT, use_llm=True)
check("llm: model 'open' confidence -> explicit OPEN QUESTION",
      any(q["id"] == "archetype" for q in oq["open_questions"]))
os.environ.pop("BOOTSTRAP_INTERVIEW_LLM_FAKE", None)

# --------------------------------------------------------------------------- #
# Regression: review round 2 findings (R-2, I-1, F-3, R-3)
# --------------------------------------------------------------------------- #
import io as _io  # noqa: E402

# R-2 (High): configemit must NOT silently emit control chars that minyaml
# cannot parse. Every control char round-trips (folded + observably warned);
# clean strings stay warning-free; reachable via the bounds-checked LLM path.
for _label, _s in (("newline", "line1\nline2"), ("cr", "a\rb"),
                    ("tab", "a\tb"), ("nul", "a\x00b"),
                    ("mixed", "a\n\t \r b")):
    _w = []
    _y = emit({"project": {"name": _s, "archetype": "cli"}}, warnings=_w)
    try:
        _rp = load_yaml(_y)
        _ok = isinstance(_rp.get("project", {}).get("name"), str)
    except Exception:
        _ok = False
    check(f"R-2: control char ({_label}) round-trips through minyaml", _ok)
    check(f"R-2: control char ({_label}) sanitization is observable",
          len(_w) == 1 and "project.name" in _w[0])
_wc = []
emit({"project": {"name": "clean-name", "archetype": "cli"},
      "principles": {"ranked": ["Clear errors over silent fallbacks"]}},
     warnings=_wc)
check("R-2: clean values still produce no spurious warnings", _wc == [])

os.environ["BOOTSTRAP_INTERVIEW_LLM_FAKE"] = json.dumps({
    "archetype": {"value": "cli", "confidence": "high", "rationale": "x"},
    "prd_tier": {"value": "micro", "confidence": "high", "rationale": "x"},
    "tdd_policy": {"value": "off", "confidence": "high", "rationale": "x"},
    "principle_additions": [{"principle": "Bad\nprinciple\twith ctrl",
                             "rationale": "y"}],
    "secrets_enabled": {"value": True, "confidence": "high", "rationale": "x"},
    "deps_enabled": {"value": True, "confidence": "high", "rationale": "x"},
})
_pllm = IV.build_proposal("a cli tool with subcommands stdin stdout flag",
                          use_llm=True)
_allm = IV.default_answers(_pllm)
_cllm = IV.answers_to_config(_allm)
_wllm = []
_yllm = emit(_cllm, warnings=_wllm)
try:
    load_yaml(_yllm)
    _llm_ok = True
except Exception:
    _llm_ok = False
check("R-2: LLM-proposed control-char principle still yields parseable config",
      _llm_ok and len(_wllm) >= 1)
os.environ.pop("BOOTSTRAP_INTERVIEW_LLM_FAKE", None)

# I-1 (High): run_interactive must terminate on EOF even when a validated
# loop's proposed default is invalid (archetype override raises the tier
# floor above the proposed default tier). Previously infinite-looped.
_script = _io.StringIO("\nplatform\n")  # name accept, archetype=platform, EOF
_out = _io.StringIO()
_ai1 = IV.run_interactive(SAMPLE_TEXT, instream=_script, outstream=_out,
                          project_fallback="p")
check("I-1: interactive terminates on EOF after floor-raising override",
      _ai1["archetype"] == "platform" and _ai1["prd_tier"] == "full")
_, _ei1 = resolve_config(IV.answers_to_config(_ai1))
check("I-1: EOF-clamped tier yields a valid config", _ei1 == [])
_ai1b = IV.run_interactive(SAMPLE_TEXT, instream=_io.StringIO("\nbogus\n"),
                           outstream=_io.StringIO(), project_fallback="p")
check("I-1: invalid archetype then EOF accepts proposed default (no hang)",
      _ai1b["archetype"] in H.ARCHETYPE_REQUIRED_TIER)

# F-3 (Medium): a hand-edited interview file with prd_tier below the
# archetype floor must be REJECTED by the interview tool's validation (the
# installer's resolve_config alone does not enforce the floor).
_bad_cfg = IV.answers_to_config({
    "project_name": "x", "archetype": "service", "prd_tier": "micro",
    "principles_ranked": ["a"], "tdd_policy": "off",
    "secrets_enabled": False, "secrets_never_read_paths": [],
    "deps_enabled": False, "loop_mode_enabled": False,
    "goal_supervised_mode_enabled": False, "queue_mode_enabled": False,
    "commands_test": "", "commands_lint": "", "commands_format": "",
    "commands_typecheck": "", "commands_ci_local": ""})
check("F-3: sub-floor prd_tier rejected by validate_config_dict",
      any("below the required floor" in e
          for e in IV.validate_config_dict(_bad_cfg)))
_ok_cfg = dict(_bad_cfg)
_ok_cfg["project"] = dict(_bad_cfg["project"], prd_tier="full")
check("F-3: legitimate tier upgrade still passes",
      IV.validate_config_dict(_ok_cfg) == [])

# R-3 (Medium): a principle (or name) containing a comma must round-trip
# through render_interview -> parse_interview_answers intact, and the legacy
# inline 'key: a, b' form must still parse for back-compat.
_pr3 = IV.build_proposal("a service rest api worker endpoint")
_pr3["principles"]["ranked"] = ["Clarity, brevity, rigor", "Second"]
_pr3["project_name"] = {"value": "Name, with comma", "confidence": "low",
                        "rationale": "r"}
_rt = IV.parse_interview_answers(IV.render_interview(_pr3, "x"))
check("R-3: comma-containing principle survives render->parse",
      _rt["principles_ranked"] == ["Clarity, brevity, rigor", "Second"])
check("R-3: comma-containing project name survives render->parse",
      _rt["project_name"] == "Name, with comma")
_legacy = "\n".join([
    IV.ANSWERS_BEGIN, "project_name: legacy", "archetype: service",
    "prd_tier: standard", "principles_ranked: A one, B two, C three",
    "tdd_policy: encouraged", "secrets_enabled: true",
    "secrets_never_read_paths: .env*, secrets/**", "deps_enabled: true",
    "loop_mode_enabled: false", "goal_supervised_mode_enabled: false",
    "queue_mode_enabled: false", "commands_test: ", "commands_lint: ",
    "commands_format: ", "commands_typecheck: ", "commands_ci_local: ",
    IV.ANSWERS_END])
_lp = IV.parse_interview_answers(_legacy)
check("R-3: legacy inline list form still parses (back-compat)",
      _lp["principles_ranked"] == ["A one", "B two", "C three"] and
      _lp["secrets_never_read_paths"] == [".env*", "secrets/**"])

# --------------------------------------------------------------------------- #
# TEL-01 (v2.4.0 fold): telemetry_export_enabled is a standalone top-level
# opt-in wired through the wizard, default skip.
# --------------------------------------------------------------------------- #
_tp = IV.build_proposal("a service rest api worker endpoint")
_tans = IV.default_answers(_tp)
check("TEL-01: default answer skips telemetry (false)",
      _tans["telemetry_export_enabled"] is False)
# Default emitted config carries the top-level flag = false (mirrors how
# queue_mode_enabled: false is emitted).
_tcfg = IV.answers_to_config(_tans)
check("TEL-01: default emitted config has top-level "
      "telemetry_export_enabled: false",
      _tcfg.get("telemetry_export_enabled") is False)
check("TEL-01: telemetry flag is NOT nested under autonomous_modes",
      "telemetry_export_enabled" not in _tcfg["autonomous_modes"])
# The default-emitted YAML string carries the flag (surfaces in the ANSWERS
# block the operator edits).
_trender = IV.render_interview(_tp, "x")
check("TEL-01: ANSWERS block emits telemetry_export_enabled: false",
      "telemetry_export_enabled: false" in _trender)
# Verbatim PRD question phrasing present in the render (not paraphrased).
check("TEL-01: render carries the verbatim 'Enable observability export?' "
      "question", "Enable observability export?" in _trender)
# Answering yes yields a true config flag (answers layer).
_tp2 = IV.build_proposal("a service rest api worker endpoint")
_ans2 = IV.default_answers(_tp2)
_ans2["telemetry_export_enabled"] = True
_ans2_cfg = IV.answers_to_config(_ans2)
check("TEL-01: answering yes yields top-level telemetry_export_enabled: true",
      _ans2_cfg.get("telemetry_export_enabled") is True)
# And a hand-edited ANSWERS block with the flag true parses back to true.
_yes_block = IV.render_interview(_tp2, "x").replace(
    "telemetry_export_enabled: false", "telemetry_export_enabled: true")
check("TEL-01: telemetry_export_enabled: true round-trips through parse",
      IV.parse_interview_answers(_yes_block)["telemetry_export_enabled"]
      is True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
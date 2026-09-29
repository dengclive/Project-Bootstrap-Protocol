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
# [W-1] Names the five COMMAND keys rather than sweeping .values(): the block
# also carries `execute_in_cwd`, a boolean fact ABOUT the commands, and a
# whole-block sweep would either fail on it or (worse, if someone "fixed" it by
# loosening the predicate) stop pinning that the commands are empty at all.
_CMD_KEYS = ("test", "lint", "format", "typecheck", "ci_local")
check("commands: config commands block all empty strings",
      all(cfg["commands"][k] == "" for k in _CMD_KEYS))
check("commands: execute_in_cwd defaults true (pre-W-1 behavior)",
      cfg["commands"]["execute_in_cwd"] is True)

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
      all(cfg_ref["commands"][k] == "" for k in _CMD_KEYS))
check("llm: execute_in_cwd never flipped by the model",
      cfg_ref["commands"]["execute_in_cwd"] is True)

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

# [WP1 D3] The interview route. deps_enabled false in the ANSWERS block must
# take the dependency gate out, as secrets_enabled false takes the secrets
# gate out; before D3 only a hand-added hooks.dependency_gate: false did.
_d3_cfg, _d3_err = resolve_config(_ok_cfg)
check("D3: interview secrets_enabled false -> no secrets-gate (reference)",
      _d3_err == [] and "secrets-gate" not in _d3_cfg["_resolved_hooks"])
check("D3: interview deps_enabled false -> no dependency-gate",
      _d3_err == [] and "dependency-gate" not in _d3_cfg["_resolved_hooks"])

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

# --------------------------------------------------------------------------- #
# TEL-01 back-compat discriminator (review finding: the missing-key exemption
# was unconditional, so a DELETED or MISSPELLED key in a freshly rendered
# v2.4.0 file silently resolved an opt-in to false — the operator believes
# telemetry is on, no telemetry.md is emitted, nothing says why). The telemetry
# SECTION marker only a v2.4.0+ render carries is the discriminator: present =>
# fail loud; absent => genuinely pre-2.4.0, keep defaulting to skip.
# --------------------------------------------------------------------------- #
check("TEL-01 back-compat: the render carries the section marker",
      IV.TELEMETRY_SECTION_MARKER in _trender)

# (a) A v2.4.0 file with the answer line DELETED must fail loud.
_deleted = "\n".join(l for l in _trender.splitlines()
                     if not l.strip().startswith("telemetry_export_enabled:"))
try:
    IV.parse_interview_answers(_deleted)
    check("TEL-01 back-compat: deleted key in a v2.4.0 file fails loud", False)
except ValueError as _e:
    check("TEL-01 back-compat: deleted key in a v2.4.0 file fails loud",
          "telemetry_export_enabled" in str(_e))

# (b) A MISSPELLED key is the same class (unknown keys are dropped silently).
_typo = _trender.replace("telemetry_export_enabled: false",
                         "telemetry_export_enabld: true")
try:
    IV.parse_interview_answers(_typo)
    check("TEL-01 back-compat: misspelled key fails loud", False)
except ValueError as _e:
    check("TEL-01 back-compat: misspelled key fails loud",
          "telemetry_export_enabled" in str(_e))

# (c) A genuinely pre-2.4.0 file (no telemetry section, no key) still parses,
#     defaulting to skip — the locked back-compat requirement is preserved.
_pre240 = "\n".join(
    l for l in _deleted.splitlines()
    if IV.TELEMETRY_SECTION_TITLE not in l
    and "Enable observability export?" not in l
    and "telemetry_export_enabled = false" not in l)
check("TEL-01 back-compat: the pre-2.4.0 fixture has no section marker",
      IV.TELEMETRY_SECTION_MARKER not in _pre240)
_pre_parsed = IV.parse_interview_answers(_pre240)
check("TEL-01 back-compat: pre-2.4.0 file still parses (no exception)",
      isinstance(_pre_parsed, dict))
check("TEL-01 back-compat: pre-2.4.0 file defaults telemetry to skip",
      _pre_parsed["telemetry_export_enabled"] is False)
check("TEL-01 back-compat: pre-2.4.0 file keeps every other answer intact",
      _pre_parsed["project_name"] == _tans["project_name"])

# (d) Every other missing key stays loud regardless of the marker (the
#     exemption is scoped to the one key, not a general softening).
_no_queue = "\n".join(l for l in _trender.splitlines()
                      if not l.strip().startswith("queue_mode_enabled:"))
try:
    IV.parse_interview_answers(_no_queue)
    check("TEL-01 back-compat: other missing keys still fail loud", False)
except ValueError as _e:
    check("TEL-01 back-compat: other missing keys still fail loud",
          "queue_mode_enabled" in str(_e))

# --------------------------------------------------------------------------- #
# DS-01 (v2.5.0): design_steering_enabled (+ optional design_review_skill_
# enabled) — a top-level opt-in wired like telemetry, PLUS an archetype-gated
# interactive offer (the one net-new mechanism). Default skip.
# --------------------------------------------------------------------------- #
_dp = IV.build_proposal("a full-stack web app with a dashboard for users")
_dans = IV.default_answers(_dp)
check("DS-01: default answers skip design steering (false)",
      _dans["design_steering_enabled"] is False
      and _dans["design_review_skill_enabled"] is False)
_dcfg = IV.answers_to_config(_dans)
check("DS-01: default emitted config has top-level design_steering_enabled: "
      "false", _dcfg.get("design_steering_enabled") is False
      and _dcfg.get("design_review_skill_enabled") is False)
check("DS-01: design flags are NOT nested under autonomous_modes",
      "design_steering_enabled" not in _dcfg["autonomous_modes"]
      and "design_review_skill_enabled" not in _dcfg["autonomous_modes"])

# VERBATIM assertion (guards drift): the code constant equals the protocol
# doc's Phase 0 step 6 design-steering question, byte-for-byte.
with io.open(os.path.join(ROOT, "Bootstrap-Protocol-v2-5-0.md"),
             "r", encoding="utf-8", newline="") as _pfh:
    _doc_lines = _pfh.read().split("\n")
_qline = [l for l in _doc_lines
          if "Question phrasing for design steering (use verbatim)" in l]
check("DS-01 verbatim: protocol doc has exactly one design-steering question "
      "line", len(_qline) == 1)
if _qline:
    _doc_q = _qline[0][_qline[0].index('*"') + 2: _qline[0].rindex('"*')]
    check("DS-01 verbatim: code DESIGN_STEERING_QUESTION == protocol doc "
          "(byte-identical, no paraphrase)",
          IV.DESIGN_STEERING_QUESTION == _doc_q)

# Render carries the section marker + the verbatim question + both keys.
_drender = IV.render_interview(_dp, "x")
check("DS-01: render carries the design section marker",
      IV.DESIGN_SECTION_MARKER in _drender)
check("DS-01: render carries the verbatim question (not paraphrased)",
      IV.DESIGN_STEERING_QUESTION in _drender)
check("DS-01: ANSWERS block emits both design flags false",
      "design_steering_enabled: false" in _drender
      and "design_review_skill_enabled: false" in _drender)

# Hand-set true round-trips through parse.
_dyes = _drender.replace("design_steering_enabled: false",
                         "design_steering_enabled: true").replace(
                         "design_review_skill_enabled: false",
                         "design_review_skill_enabled: true")
_dparsed = IV.parse_interview_answers(_dyes)
check("DS-01: hand-set design flags true round-trip through parse",
      _dparsed["design_steering_enabled"] is True
      and _dparsed["design_review_skill_enabled"] is True)

# Fail-loud discriminator (same design as telemetry).
# (a) v2.5.0 file with the primary key DELETED must fail loud.
_ddel = "\n".join(l for l in _drender.splitlines()
                  if not l.strip().startswith("design_steering_enabled:"))
try:
    IV.parse_interview_answers(_ddel)
    check("DS-01 back-compat: deleted key in a v2.5.0 file fails loud", False)
except ValueError as _e:
    check("DS-01 back-compat: deleted key in a v2.5.0 file fails loud",
          "design_steering_enabled" in str(_e))
# (b) A genuinely pre-2.5.0 file (no design section, no keys) parses,
#     defaulting both flags to skip.
_pre250 = "\n".join(
    l for l in _ddel.splitlines()
    if IV.DESIGN_SECTION_TITLE not in l
    and IV.DESIGN_STEERING_QUESTION not in l
    and "design_steering_enabled = false" not in l
    and not l.strip().startswith("design_review_skill_enabled:"))
check("DS-01 back-compat: the pre-2.5.0 fixture has no design section marker",
      IV.DESIGN_SECTION_MARKER not in _pre250)
_predp = IV.parse_interview_answers(_pre250)
check("DS-01 back-compat: pre-2.5.0 file parses, design flags default false",
      _predp["design_steering_enabled"] is False
      and _predp["design_review_skill_enabled"] is False)


class _Responder:
    """A prompt-aware stdin stub (robust to prompt ordering): answers the
    archetype + design prompts by inspecting the CURRENT prompt just written,
    and accepts the default (empty line) for everything else. A call cap
    prevents any accidental infinite validated-loop from hanging the test.

    Anchoring: `_ask` writes `{question}\\n  [default: X] > ` and then reads, so
    the current question is the last line BEFORE the final `[default:` marker.
    Matching on that single line (not a fixed-size tail slice) isolates each
    prompt — otherwise the just-answered design prompt still sits in the window
    when the skill prompt fires and would shadow it (feeding the design answer
    to the skill question), and the archetype prompt would leak into the tier
    prompt."""

    def __init__(self, out, archetype, design, skill):
        self.out, self.arche = out, archetype
        self.design, self.skill = design, skill
        self.n = 0

    def _current_prompt(self):
        before = self.out.getvalue().rsplit("[default:", 1)[0]
        return before.rstrip("\n ").rsplit("\n", 1)[-1]

    def readline(self):
        self.n += 1
        if self.n > 60:
            return ""  # safety EOF
        prompt = self._current_prompt()
        if "Archetype [" in prompt:
            return self.arche + "\n"
        if "advisory design-review skill?" in prompt:
            return self.skill + "\n"
        if "Generate design steering doc?" in prompt:
            return self.design + "\n"
        return "\n"


# Interactive: fullstack IS offered; accepting true+true records both flags.
_fs_out = _io.StringIO()
_fs_ans = IV.run_interactive(
    "a full-stack web app with a user dashboard",
    instream=_Responder(_fs_out, "fullstack", "true", "true"),
    outstream=_fs_out, project_fallback="p")
check("DS-01 interactive: fullstack is OFFERED design steering",
      IV.DESIGN_SECTION_MARKER.replace("## ", "--- ") in _fs_out.getvalue()
      or "--- Design steering ---" in _fs_out.getvalue())
check("DS-01 interactive: fullstack accept records both flags true",
      _fs_ans["design_steering_enabled"] is True
      and _fs_ans["design_review_skill_enabled"] is True)

# Interactive: design=YES, skill=NO — the skill prompt MUST receive its own
# answer, not the design answer. This guards the _Responder anchoring AND the
# run_interactive skill wiring: with design and skill DIFFERENT, a stub that
# shadowed the skill prompt (or code that read the wrong variable) records
# skill True and fails here.
_dn_out = _io.StringIO()
_dn_ans = IV.run_interactive(
    "a full-stack web app with a user dashboard",
    instream=_Responder(_dn_out, "fullstack", "true", "false"),
    outstream=_dn_out, project_fallback="p")
check("DS-01 interactive: design=yes skill=no records steering True, skill False",
      _dn_ans["design_steering_enabled"] is True
      and _dn_ans["design_review_skill_enabled"] is False)

# Interactive: DECLINE design steering (offered archetype, design=false) — the
# nested skill prompt MUST NOT be shown (guards the `if design_steering_enabled:`
# gate false-branch). skill is fed "true" but must never be read.
_dd_out = _io.StringIO()
_dd_ans = IV.run_interactive(
    "a full-stack web app with a user dashboard",
    instream=_Responder(_dd_out, "fullstack", "false", "true"),
    outstream=_dd_out, project_fallback="p")
check("DS-01 interactive: declining design does NOT show the skill prompt",
      "advisory design-review skill?" not in _dd_out.getvalue())
check("DS-01 interactive: declining design records both flags false",
      _dd_ans["design_steering_enabled"] is False
      and _dd_ans["design_review_skill_enabled"] is False)

# Interactive OFFER gating across EVERY archetype (mutation guard: dropping any
# offered archetype from _DESIGN_OFFER_ARCHETYPES, or adding any excluded one,
# must be caught). The expected set here is the SPEC (independent of the
# production constant). design/skill are declined so the loop only probes offer
# visibility, not acceptance.
_OFFERED_SPEC = {"fullstack", "mobile", "ai-agent", "platform", "other"}
for _arch in sorted(__import__("defaults").ARCHETYPES):
    _ao = _io.StringIO()
    IV.run_interactive("a project with some surface",
                       instream=_Responder(_ao, _arch, "false", "false"),
                       outstream=_ao, project_fallback="p")
    _offered = "--- Design steering ---" in _ao.getvalue()
    check(f"DS-01 interactive: archetype '{_arch}' offered == "
          f"{_arch in _OFFERED_SPEC}",
          _offered == (_arch in _OFFERED_SPEC))


# --------------------------------------------------------------------------- #
# WP1: the interview can express a gates-off install. Per-hook toggles,
# cicd_opt_out, the real prd_path, shell and tiebreakers reach the config, and
# a line the parser cannot use produces a warning instead of vanishing. Rows
# are written so each fails on its own on a tree without the feature (no
# AttributeError or TypeError takes the rest of the suite down with it).
# --------------------------------------------------------------------------- #
from defaults import DEFAULTS  # noqa: E402


def _wp1(fn):
    """(ok, value): run fn, turning any exception into a failed row."""
    try:
        return True, fn()
    except Exception as e:  # noqa: BLE001 - a missing feature is a red row
        return False, e


def _resolved(cfg):
    rc, errs = resolve_config(cfg)
    return rc["_resolved_hooks"] if not errs else errs


def _wired(project_dir):
    s = json.load(open(os.path.join(project_dir, ".claude", "settings.json")))
    return {h["command"].rsplit("/", 1)[-1]
            for ev in s["hooks"].values() for m in ev for h in m["hooks"]}


_wp = IV.build_proposal(SAMPLE_TEXT)
_wr = IV.render_interview(_wp, "docs/prd/PRD.md")

# The toggle set is exactly the installer's: every non-numeric hooks.* key,
# minus the two security gates (D3 ruling: secrets_enabled and deps_enabled
# are the only interview switches for them).
_SECURITY_TOGGLES = {"secrets_gate", "dependency_gate"}
_toggle_spec = {k for k, v in DEFAULTS["hooks"].items()
                if v is None or isinstance(v, bool)} - _SECURITY_TOGGLES
check("WP1: HOOK_TOGGLES == the toggle keys of DEFAULTS['hooks'] minus the "
      "two security gates",
      {n for n, _ in getattr(IV, "HOOK_TOGGLES", ())} == _toggle_spec)
check("WP1: every toggle has an ANSWERS line in a fresh render",
      all(f"\nhooks_{k}: " in _wr for k in _toggle_spec))
# [D3 ruling, review rulings/F2] The interview offers no second switch for
# the security gates: no ANSWERS line, no answer key, no interactive name.
check("D3: a fresh render has no hooks_secrets_gate/hooks_dependency_gate "
      "line",
      all(f"hooks_{k}" not in _wr for k in _SECURITY_TOGGLES))
check("D3: neither security toggle is an ANSWERS key",
      not ({f"hooks_{k}" for k in _SECURITY_TOGGLES} & set(IV.ANSWER_KEYS)))
_wsec = []
_ok, _pa = _wp1(lambda: IV.parse_interview_answers(
    _wr.replace(IV.ANSWERS_END,
                "hooks_secrets_gate: false\n" + IV.ANSWERS_END),
    warnings=_wsec))
check("D3: a hand-added hooks_secrets_gate: false is an unknown key that "
      "leaves the secrets gate on",
      _ok and any("unknown key 'hooks_secrets_gate'" in x for x in _wsec)
      and "secrets-gate" in _resolved(IV.answers_to_config(_pa)))

# A fresh render parses back to exactly the default answers, every key typed.
_ok, _pa = _wp1(lambda: IV.parse_interview_answers(_wr)
                == IV.default_answers(_wp, prd_path="docs/prd/PRD.md"))
check("WP1: a fresh render round-trips to default_answers exactly",
      _ok and _pa is True)

# Accepting every proposal emits no hooks: block (default install unchanged).
_dcfg0 = IV.answers_to_config(IV.default_answers(_wp))
check("WP1: default answers emit no hooks: key", "hooks" not in _dcfg0)
check("WP1: default answers still resolve both security gates",
      {"secrets-gate", "dependency-gate"} <= set(_resolved(_dcfg0)))

# D3 at the decision layer: deps_enabled false removes the dependency gate.
_off = dict(IV.default_answers(_wp), secrets_enabled=False,
            deps_enabled=False)
_offcfg = IV.answers_to_config(_off)
# [D3 ruling] secrets.enabled and deps.enabled are the only switches, applied
# in resolve_config. The interview writes no hooks.* line for them: a forced
# `hooks.secrets_gate/dependency_gate: false` kept both gates off after the
# operator flipped the policies back to true (the sticky row below).
check("WP1: deps/secrets off -> no hooks key in the config",
      "hooks" not in _offcfg)
check("WP1: deps/secrets off -> neither security gate resolves",
      not ({"secrets-gate", "dependency-gate"} & set(_resolved(_offcfg))))
_flip = json.loads(json.dumps(_offcfg))
_flip["secrets"]["enabled"] = True
_flip["deps"]["enabled"] = True
check("WP1: gate-off is not sticky: re-enabling both policies in the config "
      "brings both gates back",
      {"secrets-gate", "dependency-gate"} <= set(_resolved(_flip)))

# A per-hook toggle edited in the ANSWERS block reaches the resolved set.
_ok, _pa = _wp1(lambda: IV.parse_interview_answers(_wr.replace(
    "hooks_spec_gate_commit: true", "hooks_spec_gate_commit: false")))
check("WP1: hooks_spec_gate_commit: false removes spec-gate-commit",
      _ok and "spec-gate-commit" not in _resolved(IV.answers_to_config(_pa)))
_ok, _pa = _wp1(lambda: IV.parse_interview_answers(_wr.replace(
    "hooks_tdd_gate: auto", "hooks_tdd_gate: true")))
check("WP1: hooks_tdd_gate: true forces tdd-gate under tdd encouraged",
      _ok and _pa["tdd_policy"] == "encouraged"
      and "tdd-gate" in _resolved(IV.answers_to_config(_pa)))
_ok, _pa = _wp1(lambda: IV.parse_interview_answers(_wr))
check("WP1: hooks_tdd_gate: auto parses to None (derive from policy)",
      _ok and _pa.get("hooks_tdd_gate", "missing") is None)

# cicd_opt_out, shell and tiebreakers reach the config.
_ok, _pa = _wp1(lambda: IV.parse_interview_answers(
    _wr.replace("cicd_opt_out: false", "cicd_opt_out: true")
    .replace("shell: bash", "shell: zsh")
    .replace("principles_tiebreakers:",
             "principles_tiebreakers:\n  - DRY vs YAGNI: prefer YAGNI, "
             "until the third duplication")))
_pc = IV.answers_to_config(_pa) if _ok else {}
check("WP1: cicd_opt_out: true reaches the config and drops ci-mirror",
      _pc.get("project", {}).get("cicd_opt_out") is True
      and "ci-mirror" not in _resolved(_pc))
check("WP1: shell: zsh reaches project.shell",
      _pc.get("project", {}).get("shell") == "zsh")
check("WP1: a tiebreaker with a colon and a comma survives as one item",
      _pc.get("principles", {}).get("tiebreakers")
      == ["DRY vs YAGNI: prefer YAGNI, until the third duplication"])
_ok, _pa = _wp1(lambda: IV.parse_interview_answers(_wr.replace(
    "principles_tiebreakers:", "principles_tiebreakers: A vs B, prefer A")))
check("WP1: an inline tiebreaker is one item, not split at the comma",
      _ok and _pa.get("principles_tiebreakers") == ["A vs B, prefer A"])

# prd_path: the PRD the interview read, relative to the output directory.
_cpp = getattr(IV, "_config_prd_path", None)
with tempfile.TemporaryDirectory() as _d:
    _out = os.path.join(_d, "iv.md")
    check("WP1: an absolute PRD path under the project is made relative",
          _cpp is not None and _cpp(__import__("pathlib").Path(
              os.path.join(_d, "docs", "prd", "x.md")),
              __import__("pathlib").Path(_out)) == "docs/prd/x.md")
    check("WP1: a PRD outside the project is recorded as given",
          _cpp is not None and _cpp(__import__("pathlib").Path(
              "/elsewhere/prd.md"), __import__("pathlib").Path(_out))
          == "/elsewhere/prd.md")

# Warnings instead of silent drops.
_ok, _ = _wp1(lambda: IV.parse_interview_answers(_wr, warnings=[]))
_w0 = []
if _ok:
    IV.parse_interview_answers(_wr, warnings=_w0)
check("WP1: a fresh render parses with no warnings", _ok and _w0 == [])
_add = _wr.replace(IV.ANSWERS_END,
                   "tiebreakers: prefer A\n  - orphan item\n"
                   "just some words\n"
                   "tdd_policy: required\n" + IV.ANSWERS_END)
_wadd = []
_ok, _pa = _wp1(lambda: IV.parse_interview_answers(_add, warnings=_wadd))
check("WP1: an unknown key warns and suggests the real key",
      _ok and any("unknown key 'tiebreakers'" in x
                  and "principles_tiebreakers" in x for x in _wadd))
check("WP1: a list item under an unknown key warns",
      _ok and any("orphan item" in x for x in _wadd))
check("WP1: a line with no colon warns",
      _ok and any("just some words" in x for x in _wadd))
check("WP1: a repeated key warns and the later value is used",
      _ok and any("'tdd_policy' appears again" in x for x in _wadd)
      and _pa["tdd_policy"] == "required")
_ws = []
_ok, _pa = _wp1(lambda: IV.parse_interview_answers(
    _wr.replace("archetype: service",
                "archetype: service\nsource: PRD-derived")
    .replace(IV.ANSWERS_END, "targets_seam_version: 2.0.0\n"
             + IV.ANSWERS_END), warnings=_ws))
check("WP1: seam provenance lines (source:, targets_seam_version:) are "
      "ignored without a warning",
      _ok and _ws == []
      and _pa == IV.parse_interview_answers(_wr))
_wb = []
_ok, _pa = _wp1(lambda: IV.parse_interview_answers(
    _wr.replace("loop_mode_enabled: false", "loop_mode_enabled: flase"),
    warnings=_wb))
check("WP1: an unreadable pre-WP1 boolean warns and still reads false",
      _ok and _pa["loop_mode_enabled"] is False
      and any("loop_mode_enabled" in x for x in _wb))
_ok, _e = _wp1(lambda: IV.parse_interview_answers(
    _wr.replace("hooks_test_gate: true", "hooks_test_gate: ture")))
check("WP1: an unreadable WP1 boolean is an error, not a guess",
      not _ok and "hooks_test_gate" in str(_e))
# [review correctness/F3] Since D3, deps_enabled/secrets_enabled false removes
# a security gate, so their typo is an error with its line, not "read as
# false" with a warning (the route that dropped the dependency gate).
for _pk in ("deps_enabled", "secrets_enabled"):
    _ok, _e = _wp1(lambda: IV.parse_interview_answers(
        _wr.replace(f"{_pk}: true", f"{_pk}: flase")))
    _pk_line = next(i for i, l in enumerate(_wr.splitlines(), 1)
                    if l.startswith(f"{_pk}: "))
    check(f"D3: an unreadable {_pk} is an error naming its line, not false",
          not _ok and f"line {_pk_line}: {_pk}: 'flase'" in str(_e))
with tempfile.TemporaryDirectory() as _d:
    open(os.path.join(_d, "iv.md"), "w").write(
        _wr.replace("deps_enabled: true", "deps_enabled: flase"))
    _r = subprocess.run([sys.executable, BIN, "synthesize", "-i", "iv.md",
                         "-o", "c.yaml"], cwd=_d, capture_output=True,
                        text=True)
    check("D3 e2e: synthesize refuses deps_enabled: flase with rc 2, naming "
          "the file and line, and writes no config",
          _r.returncode == 2 and "error: iv.md: line " in _r.stderr
          and "deps_enabled: 'flase'" in _r.stderr
          and not os.path.exists(os.path.join(_d, "c.yaml")))

# Section-marker discriminator: deleted key fails loud; older file defaults.
_ok, _e = _wp1(lambda: IV.parse_interview_answers("\n".join(
    l for l in _wr.splitlines()
    if not l.startswith("hooks_test_gate:"))))
check("WP1: a deleted hooks_ line in a current file fails loud",
      not _ok and "hooks_test_gate" in str(_e))
_wp1_titles = ("PRD location", "Shell", "CI/CD applicability",
               "Principle tiebreakers", "Hooks")
_old_lines, _skip = [], False
for _l in _wr.splitlines():
    if _l.startswith("## "):
        _skip = _l[3:] in _wp1_titles
    if _l.startswith("---"):
        _skip = False
    if _skip or _l.split(":", 1)[0] in (
            "prd_path", "shell", "cicd_opt_out", "principles_tiebreakers") \
            or _l.startswith("hooks_"):
        continue
    _old_lines.append(_l)
_old = "\n".join(_old_lines)
_ok, _pa = _wp1(lambda: IV.parse_interview_answers(_old))
check("WP1: a pre-WP1 file (no WP1 sections) still parses",
      _ok and _pa.get("prd_path") == "docs/prd/PRD.md"
      and _pa.get("hooks_test_gate") is True)
check("WP1: a pre-WP1 file synthesizes today's config",
      _ok and IV.answers_to_config(_pa) == _dcfg0)

# End to end: analyze -> edit -> synthesize -> REAL install.
with tempfile.TemporaryDirectory() as _d:
    os.makedirs(os.path.join(_d, "specs"))
    open(os.path.join(_d, "specs", "prd.md"), "w").write(SAMPLE_TEXT)
    subprocess.run(["git", "init", "-q", _d], check=True)
    _r = subprocess.run([sys.executable, BIN, "analyze", "--prd",
                         "specs/prd.md"], cwd=_d, capture_output=True,
                        text=True)
    _iv = os.path.join(_d, "bootstrap.interview.md")
    _t = open(_iv).read()
    open(_iv, "w").write(
        _t.replace("secrets_enabled: true", "secrets_enabled: false")
        .replace("deps_enabled: true", "deps_enabled: false"))
    _r2 = subprocess.run([sys.executable, BIN, "synthesize"], cwd=_d,
                         capture_output=True, text=True)
    _r3 = subprocess.run([sys.executable, INSTALL_BIN, "-c",
                          os.path.join(_d, "bootstrap.config.yaml"),
                          "-C", _d], capture_output=True, text=True)
    check("WP1 e2e: gates-off answers synthesize and install (rc 0, 0)",
          _r2.returncode == 0 and _r3.returncode == 0)
    check("WP1 e2e: no warnings for a clean edit", _r2.stderr == "")
    _hooks_dir = os.path.join(_d, ".claude", "hooks")
    check("WP1 e2e: neither security gate script is emitted",
          not os.path.exists(os.path.join(_hooks_dir, "secrets-gate.sh"))
          and not os.path.exists(os.path.join(_hooks_dir,
                                              "dependency-gate.sh")))
    check("WP1 e2e: neither security gate is wired in settings.json",
          _r3.returncode == 0 and not ({"secrets-gate.sh",
                                        "dependency-gate.sh"}
                                       & _wired(_d)))
    check("WP1 e2e: every other default hook is still wired",
          _r3.returncode == 0 and _wired(_d)
          == {h + ".sh" for h in _resolved(_dcfg0)}
          - {"secrets-gate.sh", "dependency-gate.sh"})
    check("WP1 e2e: the config records the PRD the interview read",
          'prd_path: "specs/prd.md"'
          in open(os.path.join(_d, "bootstrap.config.yaml")).read())
    # [review records/R5] The installer warns about an empty test, lint or
    # format command, not typecheck or ci_local; the header says only that.
    _hdr = open(os.path.join(_d, "bootstrap.config.yaml")).read()
    check("R5: the synthesized header scopes its warning claim to "
          "commands.test/lint/format",
          "# empty commands.test/lint/format are intentional: the installer "
          "warns about each one." in _hdr and "empty commands.* are" not in _hdr)

with tempfile.TemporaryDirectory() as _d:
    open(os.path.join(_d, "p.md"), "w").write(SAMPLE_TEXT)
    open(os.path.join(_d, "iv.md"), "w").write(_wr.replace(
        IV.ANSWERS_END, "cicd_opt_outt: true\n" + IV.ANSWERS_END))
    _r = subprocess.run([sys.executable, BIN, "synthesize", "-i", "iv.md",
                         "-o", "c.yaml"], cwd=_d, capture_output=True,
                        text=True)
    check("WP1 e2e: synthesize prints the unknown-key warning on stderr",
          _r.returncode == 0 and "unknown key 'cicd_opt_outt'" in _r.stderr
          and "cicd_opt_out" in _r.stderr)

# [WP1] `synthesize -o <relative path in a subdirectory>` validated its own
# draft against the wrong file: validate_with_installer passed -c as given
# with -C set to its parent, and the installer resolves a relative -c
# against -C, so it looked for sub/sub/c.yaml and reported a valid draft as
# REJECTED with rc=2.
with tempfile.TemporaryDirectory() as _d:
    open(os.path.join(_d, "p.md"), "w").write(SAMPLE_TEXT)
    os.makedirs(os.path.join(_d, "sub"))
    subprocess.run([sys.executable, BIN, "analyze", "--prd", "p.md", "-o",
                    "iv.md"], cwd=_d, capture_output=True, text=True)
    _r = subprocess.run([sys.executable, BIN, "synthesize", "-i", "iv.md",
                         "-o", os.path.join("sub", "c.yaml")], cwd=_d,
                        capture_output=True, text=True)
    check("WP1: synthesize -o sub/c.yaml validates the file it wrote (rc 0)",
          _r.returncode == 0 and "REJECTED" not in _r.stdout
          and os.path.isfile(os.path.join(_d, "sub", "c.yaml")))


class _KeyedResponder:
    """Answers by prompt substring; Enter for everything else."""

    def __init__(self, out, answers):
        self.out, self.answers, self.n = out, answers, 0

    def readline(self):
        self.n += 1
        if self.n > 80:
            return ""
        before = self.out.getvalue().rsplit("[default:", 1)[0]
        prompt = before.rstrip("\n ").rsplit("\n", 1)[-1]
        for key, val in self.answers.items():
            if key in prompt:
                return val + "\n"
        return "\n"


_io_out = _io.StringIO()
_ok, _ia = _wp1(lambda: IV.run_interactive(
    SAMPLE_TEXT, outstream=_io_out, project_fallback="p",
    instream=_KeyedResponder(_io_out, {
        "Secrets enabled?": "false", "Deps policy enabled?": "false",
        "CI/CD pipelines": "no", "Shell": "zsh",
        "Tiebreakers": "A vs B, prefer A; C vs D",
        "Hooks to leave out": "spec_gate_commit"})))
_icfg = IV.answers_to_config(_ia) if _ok else {}
check("WP1 interactive: gates-off answers resolve neither security gate",
      _ok and not ({"secrets-gate", "dependency-gate"}
                   & set(_resolved(_icfg))))
check("WP1 interactive: CI/CD 'no' sets cicd_opt_out, shell zsh recorded",
      _icfg.get("project", {}).get("cicd_opt_out") is True
      and _icfg.get("project", {}).get("shell") == "zsh")
check("WP1 interactive: tiebreakers split on ';' only",
      _icfg.get("principles", {}).get("tiebreakers")
      == ["A vs B, prefer A", "C vs D"])
check("WP1 interactive: a named hook is left out",
      "spec-gate-commit" not in _resolved(_icfg) if _ok else False)

# [D3 ruling, review rulings/F2] The leave-out prompt does not accept the
# security gates: with both policies on, naming them changes nothing.
_sg_out = _io.StringIO()
_ok, _sga = _wp1(lambda: IV.run_interactive(
    SAMPLE_TEXT, outstream=_sg_out, project_fallback="p",
    instream=_KeyedResponder(_sg_out, {
        "Hooks to leave out": "secrets_gate, dependency_gate"})))
check("D3 interactive: secrets_gate/dependency_gate are unknown names to "
      "the leave-out prompt",
      _ok and "unknown hook name(s): secrets_gate, dependency_gate"
      in _sg_out.getvalue())
check("D3 interactive: naming them leaves both security gates on",
      _ok and {"secrets-gate", "dependency-gate"}
      <= set(_resolved(IV.answers_to_config(_sga))))


# [fix round 2, review RR4] The secrets and deps prompts read anything but
# true/1/yes/on as false, so a typo removed a security gate with no message.
# They now ask again, like the CI/CD prompt.
class _SeqResponder(_KeyedResponder):
    """Each matching prompt takes the next of its replies; Enter after."""

    def readline(self):
        self.n += 1
        if self.n > 80:
            return ""
        before = self.out.getvalue().rsplit("[default:", 1)[0]
        prompt = before.rstrip("\n ").rsplit("\n", 1)[-1]
        for key, vals in self.answers.items():
            if key in prompt and vals:
                return vals.pop(0) + "\n"
        return "\n"


_pp_default = IV.default_answers(IV.build_proposal(SAMPLE_TEXT,
                                                   project_fallback="p"))
for _pk, _pprompt, _pgate in (
        ("secrets_enabled", "Secrets enabled?", "secrets-gate"),
        ("deps_enabled", "Deps policy enabled?", "dependency-gate")):
    _pp_out = _io.StringIO()
    _ok, _ppa = _wp1(lambda: IV.run_interactive(
        SAMPLE_TEXT, outstream=_pp_out, project_fallback="p",
        instream=_SeqResponder(_pp_out, {_pprompt: ["flase", ""]})))
    _pp_text = _pp_out.getvalue()
    check(f"RR4 interactive: a typo at the {_pk} prompt is asked again, "
          f"not read as false",
          _ok and _pp_default[_pk] is True
          and _pp_text.count(_pprompt) == 2
          and "must be true or false" in _pp_text
          and _ppa[_pk] is True
          and _pgate in _resolved(IV.answers_to_config(_ppa)))
    if not (_ok and _ppa.get(_pk) is True):
        print(f"        proposed={_pp_default[_pk]} "
              f"asked={_pp_text.count(_pprompt)} "
              f"got={_ppa.get(_pk) if _ok else _ppa}")
    _pp_out = _io.StringIO()
    _ok, _ppa = _wp1(lambda: IV.run_interactive(
        SAMPLE_TEXT, outstream=_pp_out, project_fallback="p",
        instream=_SeqResponder(_pp_out, {_pprompt: ["flase", "no"]})))
    check(f"RR4 interactive control: after the re-ask, 'no' at the {_pk} "
          f"prompt still removes {_pgate}",
          _ok and _ppa[_pk] is False
          and _pgate not in _resolved(IV.answers_to_config(_ppa)))

# [I-6(b)/I-10, review rulings/F1 and rulings/F4] No live source repeats the
# false claim that an empty command makes a loud-TODO gate. Only an empty
# test does (test-gate); an empty lint runs `true` in format-lint-gate. Three
# sites survived the first pass: the retrofit debt entry (emitted into
# .claude/debt.md), the retrofit commands rationale and the prd_heuristics
# docstring. The spec invariant that states the claim keeps its text and
# gains a dated correction layer instead.
import re as _re  # noqa: E402
_LOUD_TODO = _re.compile(r"loud(ly)?[- ]TODO|loud(ly)? with a TODO|"
                         r"loud-failing|TODO-gate|fail-loud TODO", _re.I)
_loud_hits = []
for _base in ("lib", "bin", os.path.join("plugin", "commands")):
    for _fn in sorted(os.listdir(os.path.join(ROOT, _base))):
        _fp = os.path.join(ROOT, _base, _fn)
        if os.path.isfile(_fp) and not _fn.endswith(".pyc"):
            for _n, _ln in enumerate(open(_fp, encoding="utf-8",
                                          errors="replace"), 1):
                if _LOUD_TODO.search(_ln):
                    _loud_hits.append(f"{_base}/{_fn}:{_n}")
for _fn in ("README.md", "bootstrap.config.yaml"):
    for _n, _ln in enumerate(open(os.path.join(ROOT, _fn),
                                  encoding="utf-8"), 1):
        if _LOUD_TODO.search(_ln):
            _loud_hits.append(f"{_fn}:{_n}")
check("I-6(b): no live source claims a loud-TODO gate for empty commands "
      f"(hits: {_loud_hits})", _loud_hits == [])
_spec_inv = [l for l in open(os.path.join(
    ROOT, ".claude", "specs", "bootstrap-v2", "requirements.md"),
    encoding="utf-8") if l.startswith("- **`fail-loud-on-empty-commands`**")]
check("I-6(b): the spec's fail-loud-on-empty-commands invariant carries its "
      "WP1 correction layer",
      len(_spec_inv) == 1 and "[Corrected 2026-09-28, WP1.]" in _spec_inv[0])

# Repair of the queue self-correct row above (r5): its positional stdin put
# the 'true' on the telemetry prompt, so the self-correct path never ran.
_q_out = _io.StringIO()
_qa = IV.run_interactive(
    SAMPLE_TEXT, outstream=_q_out, project_fallback="p",
    instream=_KeyedResponder(_q_out, {"Queue mode": "true"}))
check("interactive: queue without loop/goal really self-corrects",
      "Disabling queue mode" in _q_out.getvalue()
      and _qa["queue_mode_enabled"] is False)


print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
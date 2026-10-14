#!/usr/bin/env python3
"""WP3 skills: the spec skill bodies, model lines, test-author command and
frontmatter that parses.

What these checks pin, and why each matters:

  1. FRONTMATTER IS YAML. design-review shipped a multi-line plain scalar
     holding "Advisory: flags"; Claude Code 2.1.289 logged "failed to parse
     and was ignored" and listed the skill with no description, so its
     routing key never reached the model (measured). pr-author and three
     retrofit files carried ": " inside a one-line plain scalar, which a
     strict YAML parser rejects. The check below is a conservative subset of
     YAML that needs no PyYAML, and it fails on all of those 3d866f4 forms.
  2. THE Files SYNTAX THE SKILL TEACHES IS THE SYNTAX THE CHECK READS. The
     task template is extracted from the EMITTED spec-decompose body, filled
     in, staged, and run through the EMITTED .claude/githooks/spec-check.sh,
     the parser of record (critic files contract): this file keeps no parser
     of its own. If the check's parser changes, this fails until the skill
     text changes with it. The tdd-gate stem example the body teaches is run
     through the EMITTED tdd-gate.sh the same way.
  3. Body contracts other WP3 pieces rely on: version 1.0.0 frontmatter,
     EARS, permanent AC IDs, the task schema, the status writers, the commit
     steps, the roster refresh, the classifier fields the wrappers grep for,
     the clock rule, the per-skill model lines. Gate sentences follow the
     resolved hook set, so each is pinned both ways (wired and not wired).

Run: python3 tests/test_skill_bodies.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))

from defaults import resolve_config  # noqa: E402
from installer import build_plan  # noqa: E402
from minyaml import load_yaml  # noqa: E402
import templates  # noqa: E402

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


def cfg_from(text):
    cfg, errs = resolve_config(load_yaml(text))
    assert not errs, errs
    return cfg


def bodies(cfg):
    return {a["path"]: a["body"] for a in build_plan(cfg)}


def flat(text):
    """Whitespace-normalized text, so a phrase check survives re-wrapping."""
    return re.sub(r"\s+", " ", text or "")


def has(text, phrase):
    return flat(phrase) in flat(text)


BASE = """project:
  name: sk
  archetype: cli
principles:
  tdd_policy: {tdd}
commands:
  test: "true"
  lint: "true"
  format: "true"
"""
LOOP_GOAL = BASE + """autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: {goal}
  queue_mode_enabled: false
"""
GOAL_ONLY = BASE + """autonomous_modes:
  loop_mode_enabled: false
  goal_supervised_mode_enabled: true
  queue_mode_enabled: false
"""
LOOP_QUEUE = BASE + """autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: false
  queue_mode_enabled: true
"""
DESIGN = BASE + """design_steering_enabled: true
design_review_skill_enabled: true
"""
# [WP3 skills, critic 2g] Gate sentences follow cfg["_resolved_hooks"] and
# hooks.spec_gate_commit_mode, so the fixtures below move each one alone.
BLOCK = BASE + """hooks:
  spec_gate_commit_mode: "block"
  spec_gate_commit_prefixes: ["src/", "pkg/api/"]
"""
GATES_OFF = BASE + """hooks:
  spec_gate_commit: false
  tdd_gate: false
  test_gate: false
"""
TDD_GATE_ON = BASE + """hooks:
  tdd_gate: true
"""
RETRO = """mode: "retrofit"
project:
  name: rsk
  archetype: service
principles:
  tdd_policy: "required"
commands:
  test: "true"
  lint: "true"
  format: "true"
{hooks}retrofit:
  spec_strategy: "touch-based"
  legacy_allowlist:
    - "src/**"
  retrofit_active: true
  r08_committed: true
  autonomous_modes:
    loop_mode_opted_in: {loop}
    goal_supervised_mode_opted_in: {goal}
    queue_mode_opted_in: {queue}
"""
RETRO_LOOP = RETRO.format(hooks="", loop="true", goal="false", queue="false")
RETRO_LOOP_QUEUE = RETRO.format(hooks='hooks:\n  spec_gate_commit_mode: '
                                '"block"\n', loop="true", goal="false",
                                queue="true")
RETRO_GOAL_ONLY = RETRO.format(hooks="", loop="false", goal="true",
                               queue="false")


# --------------------------------------------------------------------------- #
# 1. Frontmatter: a strict YAML subset, no PyYAML needed
# --------------------------------------------------------------------------- #
_INDICATORS = set("[]{}&*!|>'\"%@`#,?:-")


def fm_errors(text):
    """Problems with the frontmatter of a skill, command or agent file.

    Accepts: `key: value` lines at column 0, comment lines, a value that is
    a complete double-quoted string, and a block scalar (`>-`, `|`) followed
    by indented lines. Rejects what bit us: a continuation line under a
    plain scalar, and ": " or " #" inside a plain scalar.
    """
    if not text.startswith("---\n"):
        return ["no opening ---"]
    end = text.find("\n---\n", 4)
    if end < 0:
        return ["no closing ---"]
    errs, block = [], False
    for ln in text[4:end].split("\n"):
        if ln.startswith("#") or not ln.strip():
            continue
        if ln[0] in " \t":
            if not block:
                errs.append(f"continuation under a plain scalar: {ln!r}")
            continue
        block = False
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*): ?(.*)$", ln)
        if not m:
            errs.append(f"not key: value: {ln!r}")
            continue
        v = m.group(2)
        if v in (">", ">-", "|", "|-"):
            block = True
        elif v.startswith('"'):
            if not (len(v) >= 2 and v.endswith('"')):
                errs.append(f"unterminated or multi-line quoted value: {ln!r}")
        elif v and (v[0] in _INDICATORS or ": " in v or " #" in v):
            errs.append(f"plain scalar needs quoting: {ln!r}")
    return errs


print("\n== frontmatter parses (strict subset) ==")
# Fail-before rows: the 3d866f4 spellings must be REJECTED by this checker,
# or a green run below proves nothing.
_OLD_DR = ("---\nname: design-review\ndescription: Use when a task changes a "
           "user-facing surface — screens, components,\n  onboarding, empty/"
           "loading states, pricing, paywalls, or user-visible copy.\n  Checks "
           "the diff against .claude/steering/design.md. Advisory: flags, never"
           "\n  blocks. Interactive sessions only. Recommended: invoke from an "
           "Opus session.\n---\n\n# design-review\n")
_OLD_PR = ("---\nname: pr-author\ndescription: Generate a PR description: spec "
           "link, version, validation report, decision-log summary.\n---\n")
check("checker rejects the 3d866f4 design-review frontmatter",
      bool(fm_errors(_OLD_DR)), fm_errors(_OLD_DR))
check("checker rejects the 3d866f4 pr-author frontmatter",
      bool(fm_errors(_OLD_PR)), fm_errors(_OLD_PR))
check("checker accepts a block scalar and a quoted value",
      not fm_errors('---\nname: x\ndescription: >-\n  a: b\n  c\n'
                    'argument-hint: "<slug>"\n---\n'))

_FIXTURES = {
    "tdd-required": cfg_from(BASE.format(tdd='"required"')),
    "tdd-off": cfg_from(BASE.format(tdd='"off"')),
    "loop+goal": cfg_from(LOOP_GOAL.format(tdd='"required"', goal="true")),
    "loop+queue": cfg_from(LOOP_QUEUE.format(tdd='"required"')),
    "design": cfg_from(DESIGN.format(tdd='"encouraged"')),
    "block": cfg_from(BLOCK.format(tdd='"required"')),
    "gates-off": cfg_from(GATES_OFF.format(tdd='"required"')),
    "tdd-gate-on": cfg_from(TDD_GATE_ON.format(tdd='"encouraged"')),
    "retrofit-loop": cfg_from(RETRO_LOOP),
    "retrofit-loop+queue": cfg_from(RETRO_LOOP_QUEUE),
    "retrofit-goal": cfg_from(RETRO_GOAL_ONLY),
}
_PLANS = {k: bodies(c) for k, c in _FIXTURES.items()}
for label, plan in _PLANS.items():
    paths = [p for p in plan
             if re.match(r"^\.claude/(skills/[^/]+/SKILL\.md|commands/[^/]+\.md"
                         r"|agents/[^/]+\.md)$", p)]
    bad = {p: fm_errors(plan[p]) for p in paths if fm_errors(plan[p])}
    check(f"[{label}] every skill, command and agent frontmatter parses "
          f"({len(paths)} files)", not bad, repr(bad)[:600])
    nodesc = [p for p in paths
              if "\ndescription: " not in plan[p].split("\n---\n")[0]]
    check(f"[{label}] every one has a description", not nodesc, nodesc)


# --------------------------------------------------------------------------- #
# 2. Model lines and the test-author command
# --------------------------------------------------------------------------- #
print("\n== model lines and the test-author command ==")
_g = _PLANS["tdd-required"]


def skill(plan, name):
    return plan.get(f".claude/skills/{name}/SKILL.md")


# [WP3 model assignment] The operator's decision of 2026-10-05, which the
# Companion's Model Assignment Strategy table carries as a dated amendment:
# Fable only on spec-review and plan-review, with Opus as the fallback;
# code-review at xhigh effort (like the reviewer agent); the other rows as
# the Companion table has them. Tiers, never versions.
_FABLE = ("a Fable session (Opus if Fable is unavailable or Claude Code "
          "switches the model).")
_EXPECT = {
    "spec-new": "an Opus session.", "spec-review": _FABLE,
    "spec-decompose": "an Opus session.", "plan-review": _FABLE,
    "code-review": "an Opus session, at xhigh effort.",
    "spec-validate": "a Sonnet session.", "pr-author": "a Sonnet session.",
    "decision-log": "a Sonnet session.", "checkpoint": "a Sonnet session.",
    "resume": "a Sonnet session.", "ack-drift": "a Haiku session.",
    "test-author": "a Sonnet session.",
}
for name, tail in _EXPECT.items():
    b = skill(_g, name) or ""
    check(f"{name}: carries its model line ({tail[:-1]})",
          f"\n> Recommended: invoke from {tail}\n" in b)
# [WP4 / ruling 7 (c)] escalate has no Companion row either, and a model line
# would need one: a new line in a layered doc (review ESC-5).
for name in ("quiet", "quiet-task-done", "escalate"):
    check(f"{name}: no model line (no Companion row)",
          "Recommended:" not in (skill(_g, name) or "x Recommended:"))
_fable_hits = sorted(p for p, v in _g.items() if "fable" in v.lower())
check("Fable appears in exactly two emitted files: the spec-review and "
      "plan-review skills", _fable_hits == [
          ".claude/skills/plan-review/SKILL.md",
          ".claude/skills/spec-review/SKILL.md"], _fable_hits)
check("... and only in their recommendation line",
      all(v.lower().count("fable") == 2 and
          "> Recommended: invoke from " + _FABLE in v
          for p, v in _g.items() if p in _fable_hits))
# [WP3 model assignment] The Companion's Model Assignment Strategy table is
# the source of truth for which skill runs on which model (PRD Phase 7 step
# 1), so its dated amendment table must agree with every emitted line and
# with _EXPECT. Compared by TIER, never by version: the lines name tiers.
_COMP = open(os.path.join(ROOT, "Bootstrap-Protocol-Companion-v2-8-0.md")
             ).read()
_AMEND_HDR = "| Skill or agent | Recommended model (amended 2026-10-05) |"
_TIERS = ("Fable", "Opus", "Sonnet", "Haiku")


def _tier(text):
    """The first tier word in `text` (Fable, Opus, Sonnet or Haiku)."""
    hits = sorted((text.find(t), t) for t in _TIERS if t in text)
    return hits[0][1] if hits else None


_skill_rows, _agent_rows = {}, {}
if _COMP.count(_AMEND_HDR) == 1:
    for _ln in _COMP.split(_AMEND_HDR, 1)[1].splitlines()[2:]:
        if not _ln.startswith("|"):
            break
        _cells = [c.strip() for c in _ln.strip().strip("|").split("|")]
        _m = re.fullmatch(r"`([a-z-]+)`", _cells[0])
        _a = re.fullmatch(r"`([a-z-]+)` agent", _cells[0])
        if _m:
            _skill_rows[_m.group(1)] = _cells[1]
        elif _a:
            _agent_rows[_a.group(1)] = _cells[1]
check("Companion: the dated model amendment table is there, once",
      _COMP.count(_AMEND_HDR) == 1)
check("Companion amendment: its skill rows are exactly the skills with a "
      "model line", set(_skill_rows) == set(_EXPECT),
      sorted(set(_skill_rows) ^ set(_EXPECT)))
for name, tail in _EXPECT.items():
    _line = next((ln for ln in (skill(_g, name) or "").splitlines()
                  if ln.startswith("> Recommended: invoke from ")), "")
    _want = _tier(_skill_rows.get(name, ""))
    check(f"{name}: the emitted line's tier is the Companion's ({_want})",
          _want is not None and _tier(_line) == _want == _tier(tail),
          f"{_line!r} vs {_skill_rows.get(name)!r}")
for name in ("spec-review", "plan-review"):
    check(f"Companion {name}: Opus is the fallback, as the line says",
          "Opus 5.5 if Fable is unavailable or Claude Code switches the "
          "model" in _skill_rows.get(name, ""))
check("Companion code-review: xhigh effort, as the line says",
      "at xhigh effort" in _skill_rows.get("code-review", ""))
_rev = _g.get(".claude/agents/reviewer.md", "")
_imp = _g.get(".claude/agents/implementer.md", "")
check("Companion reviewer agent row: effort: xhigh, as emitted",
      "`effort: xhigh`" in _agent_rows.get("reviewer", "")
      and templates.REVIEWER_EFFORT == "xhigh"
      and "\neffort: xhigh\n" in _rev.split("\n---\n")[0])
check("Companion implementer agent row: no effort line, as emitted",
      "no `effort:` line" in _agent_rows.get("implementer", "")
      and _tier(_agent_rows.get("implementer", "")) == "Sonnet"
      and "\neffort:" not in _imp.split("\n---\n")[0]
      and "\nmodel: sonnet\n" in _imp.split("\n---\n")[0])

# The dated notes the operator decision names (2026-10-05), appended, not
# rewritten: each says what the code now does.
_PRD = open(os.path.join(ROOT, "Bootstrap-Protocol-v2-8-0.md")).read()
_RC = open(os.path.join(ROOT, "RETROFIT-COMPANION.md")).read()
_RM = open(os.path.join(ROOT, "RETROFIT.md")).read()
_README = open(os.path.join(ROOT, "README.md")).read()
_REQ = open(os.path.join(ROOT, ".claude/specs/bootstrap-v2/requirements.md")
            ).read()
_NOTES = (
    ("Companion :117: 'a scalpel, never a default' amended for the two "
     "review rows", _COMP,
     "Two rows now name Fable by default: the `spec-review` and "
     "`plan-review` recommendation lines recommend a Fable 5.1 session"),
    ("Companion wizard row: the 'xhigh is the default' claim amended", _COMP,
     "no longer true. Opus 5.5 defaults to `medium` effort, so run "
     "`claude --model opus --effort xhigh`"),
    ("Companion: aliases track the newest on first-party only", _COMP,
     "On Bedrock, Vertex and Foundry, `sonnet` resolves to Sonnet 4.5"),
    ("Companion: the ANTHROPIC_DEFAULT_*_MODEL pins", _COMP,
     "`ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL` or "
     "`ANTHROPIC_DEFAULT_HAIKU_MODEL`"),
    ("Companion: ultracode also applies to Sonnet sessions", _COMP,
     "It is on for Fable 5.1, Opus 5.5 and Sonnet 5.5 sessions, so a "
     "Sonnet main session gets it too, and off on Haiku 4.5"),
    ("Companion: ultracode's cost", _COMP,
     "Expect more agents and more tokens per task"),
    ("Companion: ultracode's opt-out", _COMP,
     "set `workflow.ultracode: false` and re-run the installer"),
    ("Companion: workflow agents set agentType or model for mechanical "
     "stages", _COMP, "Set the model for mechanical stages"),
    ("Companion: ... naming agentType and model", _COMP,
     "`agentType: 'implementer'` runs a stage as the implementer agent"),
    ("Companion: Fable costs 2.5x Opus, not 2x", _COMP,
     "Fable 5.1 costs 2.5× Opus 5.5, not 2×"),
    ("Companion cheat sheet: amended", _COMP,
     "Read this table as amended at the end of the Model Assignment "
     "Strategy section"),
    ("PRD Phase 7 step 1: a skill's model: switches only on a typed slash "
     "command (verifier correction)", _PRD,
     "switch the model and effort for the whole turn when the user types "
     "the skill's slash command"),
    ("PRD Phase 7 step 1: ... not through the Skill tool", _PRD,
     "When the model invokes the skill through the Skill tool, they did "
     "not switch it"),
    ("PRD reviewer: effort xhigh", _PRD,
     "The emitted reviewer now carries **`effort: xhigh`**"),
    ("PRD implementer: no effort line", _PRD,
     "No `effort:` line (operator decision): the implementer inherits the "
     "session's effort"),
    ("PRD IC-4: claude-sonnet-5-5", _PRD,
     "The default is now `claude-sonnet-5-5`, and IC-4 asserts that value"),
    ("retrofit Companion: Opus 4.7 / Sonnet 4.6 re-dated in the section",
     _RC, "read Opus 4.7 as Opus 5.5 and Sonnet 4.6 as Sonnet 5.5, here and "
     "in the cheat sheet below"),
    ("retrofit Companion: ... and at the cheat sheet", _RC,
     "**[Amended 2026-10-05, WP3.]** On first-party, read Opus 4.7 as Opus "
     "5.5 and Sonnet 4.6 as Sonnet 5.5;"),
    ("retrofit Companion: its skills' model: key switches only on a typed "
     "slash command", _RC,
     "such a key switches the model and effort for the whole turn when you "
     "type the skill's slash command"),
    ("retrofit Companion: reviewer xhigh", _RC,
     "| Opus 4.7 (effort: high) | Same as BOOTSTRAP. *[Amended 2026-10-05, "
     "WP3: `effort: xhigh`.]* |"),
    ("RETROFIT.md reviewer: effort xhigh", _RM,
     "The emitted reviewer carries `effort: xhigh` (operator decision), as "
     "in greenfield."),
    ("README: the ultracode key, its cost and Sonnet", _README,
     "with `workflow.ultracode: true`, the\n  default, the installer also "
     "adds `\"ultracode\": true`"),
    ("requirements.md AC-6-3 and AC-6-5 amended", _REQ,
     "AC-6-5 (c): the reviewer is `xhigh`, not `high`, in both emissions"),
)
for _label, _doc, _needle in _NOTES:
    check(f"[WP3 model notes] {_label}", _needle in _doc, _needle[:80])
check("no skill gains a model: frontmatter key (it would SWITCH models)",
      not any(re.search(r"^model:", v.split("\n---\n")[0], re.M)
              for p, v in _g.items()
              if p.startswith(".claude/skills/") and "/retrofit" not in p
              and p.split("/")[2] in dict(templates._SKILL_LIST)))
# Claude Code offers the hint as autocomplete; the values are literal here so
# a dropped renderer line and a changed map both show.
_HINTS = {"spec-new": "<slug>", "spec-review": "<slug>",
          "spec-decompose": "<slug>", "plan-review": "<slug>",
          "spec-validate": "<slug> [task-id] [current]",
          "pr-author": "<slug>", "test-author": "<task-id>"}
for name, hint in _HINTS.items():
    check(f"{name}: argument-hint \"{hint}\" in its frontmatter",
          f'\nargument-hint: "{hint}"\n'
          in (skill(_g, name) or "").split("\n---\n")[0])

_ta_cmd = _g.get(".claude/commands/test-author.md")
check("tdd required: commands/test-author.md is emitted", _ta_cmd is not None)
check("test-author command is a thin pointer sharing the skill description",
      _ta_cmd is not None and "Invoke the `test-author` skill." in _ta_cmd
      and "description: Tests-first workflow per task." in _ta_cmd
      and "description: Tests-first workflow per task."
      in (skill(_g, "test-author") or ""))
check("tdd off: neither test-author skill nor command",
      ".claude/commands/test-author.md" not in _PLANS["tdd-off"]
      and skill(_PLANS["tdd-off"], "test-author") is None)
check("tdd encouraged: test-author command emitted with the skill",
      ".claude/commands/test-author.md" in _PLANS["design"]
      and skill(_PLANS["design"], "test-author") is not None)


# --------------------------------------------------------------------------- #
# 3. Body contracts
# --------------------------------------------------------------------------- #
_COMMIT = ("Commit `.claude/specs/<slug>/` and `.claude/specs/INDEX.md` "
           "before any implementer is dispatched: an implementer's worktree "
           "starts from the last commit")
_REFUSED_WRITE = ("If Claude Code refuses a write, stop and ask; do not "
                  "write the file another way (a shell redirect or a script).")
_REFRESH = ("the task columns of the spec's row in `.claude/specs/INDEX.md` "
            "(`in-flight tasks`, `blocked tasks`, `in-flight against "
            "superseded?`, `loop-eligible / total`) from the task files, as "
            "`.claude/specs/README.md` describes.")

print("\n== spec-new ==")
_sn = skill(_g, "spec-new") or ""
check("spec-new: requirements.md starts at version: 1.0.0 (PRD 7.5)",
      "\nversion: 1.0.0\n" in _sn)
for pat in ("The <system> shall <response>.",
            "When <trigger>, the <system> shall <response>.",
            "While <state>, the <system> shall <response>.",
            "Where <feature is included>, the <system> shall",
            "If <unwanted condition>, then the <system> shall"):
    check(f"spec-new: EARS pattern present: {pat[:30]}", pat in _sn)
check("spec-new: 0-3 preconditions rule and the fallback",
      "With 0-3 preconditions" in _sn
      and "decision table or a numbered list" in _sn)
check("spec-new: a criterion that fits no pattern is an ambiguity signal",
      "fits no pattern is ambiguous" in _sn)
check("spec-new: AC IDs are permanent", "IDs are permanent" in _sn)
check("spec-new: seeds decisions.md and changelog.md",
      "# Decisions: <slug>" in _sn and "# Changelog: <slug>" in _sn
      and "| version | date | change summary | impact on in-flight tasks |"
      in _sn)
check("spec-new: dates from the clock", "date -u +%Y-%m-%d" in _sn)
check("spec-new: never overwrites an existing spec",
      has(_sn, "this skill never overwrites a spec"))
check("spec-new: slug from the INDEX row or structure.md rules",
      "planned` row" in _sn and "Spec slug naming" in _sn)
# The version-tracking contract shared with the roster (PRD 7.5 step 6):
# verifier mutant X3 (conformance) and X3 (rebuild).
check("spec-new: sets the row to draft at active version 1.0.0",
      has(_sn, "Set the status to `draft` and `active version` to `1.0.0`."))
check("spec-new: fills only the columns the roster has",
      has(_sn, "Fill only the columns the table has and leave the others "
               "as they are"))
check("spec-new: commits the spec and the roster before any dispatch "
      "(critic 2c)", has(_sn, _COMMIT))
check("spec-new: next step is /spec-review",
      has(_sn, "Next step: `/spec-review <slug>`."))
# [WP4 / ruling 1 (a)] Each spec starts on its own branch, in both modes:
# from the default branch, once the slug is resolved (the branch is named
# from it), and before the first write, so the spec's commit and its tasks'
# merges land on the spec branch.
for _label, _body in (("greenfield", _sn),
                      ("retrofit", skill(_PLANS["retrofit-loop"],
                                         "spec-new") or "")):
    _br = _body.find("## 2. Start the spec's branch")
    check(f"spec-new ({_label}): starts the spec's branch from the default "
          f"branch, after the slug and before the first write",
          has(_body, "If you are on the default branch, or on another "
                     "spec's branch (`spec/*`), create this spec's branch "
                     "from the default branch and switch to it: `git switch "
                     "-c spec/<slug> <default>`")
          and -1 < _body.find("## 1. Resolve the slug") < _br
          < _body.find("## 4. Write `requirements.md`"),
          _body[_br:_br + 400] if _br >= 0 else _body[:400])
    # [WP4 fix round 1 / NF1] After a spec's pull request the agent is
    # still on that spec's branch. "Otherwise stay on the current branch"
    # put the next spec, and every later one, on it.
    check(f"spec-new ({_label}): on another spec's branch (spec/*), the new "
          f"spec branches from the default branch, not from that spec; only "
          f"a branch the operator chose keeps it, and the step says how to "
          f"find the default branch's name",
          has(_body, "or on another spec's branch (`spec/*`)")
          and has(_body, "`git switch -c spec/<slug> <default>`")
          and has(_body, "`git symbolic-ref --short refs/remotes/origin/HEAD` "
                         "prints it after `origin/`")
          and has(_body, "On any other branch, one the operator chose, stay "
                         "on it.")
          and not has(_body, "Otherwise stay on the current branch."),
          _body[_br:_br + 700] if _br >= 0 else _body[:400])

print("\n== spec-decompose ==")
_sd = skill(_g, "spec-decompose") or ""
check("spec-decompose: bad horizontal and good vertical examples (PRD 7)",
      "Bad (horizontal)" in _sd and "Good (vertical)" in _sd)
check("spec-decompose: task file path and globally unique ID",
      "id: <slug>-T01" in _sd and "unique across all specs" in _sd)
# [critic files contract item 7] The status writers: one rule fixes the
# roster's derived columns, the spec_version freeze, the merge-back
# conflict and the check's refusal naming.
for phrase in ("The main session sets `in-progress` in the main checkout "
               "before it dispatches the task, and commits that with the "
               "spec.",
               "The main session sets `done` once the task's work has landed",
               "`/spec-validate` sets `validated` on a pass.",
               "The implementer never edits `status`."):
    check(f"spec-decompose: status writer: {phrase[:48]}...",
          has(_sd, phrase))
check("spec-decompose: spec_version is frozen once work begins, except a "
      "halted-major resume or an explicit re-validation (versioning delta 3)",
      has(_sd, "After that it changes only when the operator resumes a task "
               "that a major bump halted, or when `/spec-validate <slug> "
               "<task-id> current` re-validates the task at the current "
               "version"))
check("spec-decompose: a `Files:` line list in the body, with the forms that "
      "cover nothing named", "\nFiles:\n- src/<path>\n- tests/<path>\n" in _sd
      and has(_sd, "a line that is exactly `Files:` in the body, below the "
                   "frontmatter")
      and "`./src/auth/login.py`" in _sd and "a bare `login.py`" in _sd
      and has(_sd, "an absolute path, a glob, backticks, a link, or a note "
                   "after the path such as `(new)`"))
check("spec-decompose: what ends the list (blank line, indented or star "
      "bullet)", has(_sd, "a blank line, an indented `  - ` or a `* ` "
                          "bullet ends it"))
check("spec-decompose: tests are listed too", "tests included" in _sd)
check("spec-decompose: a directory entry covers the files under it",
      has(_sd, "A directory entry (a path ending in `/`) covers every file "
               "under it"))
# Refuted claim (critic): "the gate can read any path in a task file as
# listed" is false under spec-check.sh for a file that has a Files: block.
check("spec-decompose: the stale 'mention elsewhere' line is gone, and only "
      "the list counts", "can read any path in a task file" not in _sd
      and has(_sd, "Only the list counts: a path named anywhere else in the "
                   "task file covers nothing."))
check("spec-decompose: a missing file is added with the Edit tool; a refused "
      "edit means stop and ask", has(_sd, "add it to this list with the Edit "
                                          "tool and commit the task file "
                                          "with the change. If Claude Code "
                                          "refuses the edit, stop and ask."))
check("spec-decompose: parallelism map in plan.md, disjoint per wave",
      ".claude/specs/<slug>/plan.md" in _sd
      and has(_sd, "their Files lists must not overlap"))
check("spec-decompose: roster refresh per .claude/specs/README.md "
      "(versioning delta 1)", has(_sd, "Refresh " + _REFRESH)
      and "Change nothing else" not in _sd)
check("spec-decompose: commits the tasks and the roster before any dispatch "
      "(critic 2c)", has(_sd, _COMMIT))
check("spec-decompose: next step is /plan-review (rebuild mutant X7)",
      has(_sd, "Next step: `/plan-review <slug>`."))
check("spec-decompose: lean when no autonomous mode is on (PRD 7)",
      "loop_eligible" not in _sd and "goal_condition" not in _sd)

print("\n== gate sentences follow the resolved hooks (critic 2g) ==")
_CHECK = "The spec check reads this list."
_sd_block = skill(_PLANS["block"], "spec-decompose") or ""
_sd_off = skill(_PLANS["gates-off"], "spec-decompose") or ""
check("spec check wired, warn mode: the commit goes through with a warning",
      _CHECK in _sd and has(_sd, "or the commit goes through with a warning "
                                 "(`hooks.spec_gate_commit_mode` is `warn`)")
      and "the commit is refused" not in _sd)
check("spec check wired, warn mode: names the configured default prefixes",
      has(_sd, "under one of `src/`, `lib/`, `app/`, `test/`, `tests/`, "
               "some task file's `Files:` list must name it"))
check("spec check in block mode: the commit is refused, no warn wording",
      has(_sd_block, "or the commit is refused.")
      and "goes through with a warning" not in _sd_block)
check("block fixture: the prefixes come from hooks.spec_gate_commit_prefixes",
      has(_sd_block, "under one of `src/`, `pkg/api/`, some task file's"))
check("spec check off: no sentence claims a check; says none is wired",
      _CHECK not in _sd_off and "the commit is refused" not in _sd_off
      and has(_sd_off, "No spec check is wired in this project "
                       "(`hooks.spec_gate_commit` is off)"))
check("the check reads task files from git, not the working tree",
      has(_sd, "The check reads task files from git, not from your working "
               "tree."))
_STEM = ("`src/todo/cli.py` needs `tests/test_cli.py` (or `cli.test.ts`, "
         "`CliTest.java`, `cli_test.go`), not only a feature-named test")
_ta = skill(_g, "test-author") or ""
_ta_off = skill(_PLANS["gates-off"], "test-author") or ""
_ta_enc = skill(_PLANS["design"], "test-author") or ""
_ta_on = skill(_PLANS["tdd-gate-on"], "test-author") or ""
_sd_enc = skill(_PLANS["design"], "spec-decompose") or ""
_sd_on = skill(_PLANS["tdd-gate-on"], "spec-decompose") or ""
check("tdd-gate wired (required): the stem rule in spec-decompose and "
      "test-author (critic files contract item 4)",
      has(_sd, _STEM) and has(_ta, _STEM))
check("tdd-gate wired by hooks.tdd_gate under encouraged: stem rule present",
      has(_sd_on, _STEM) and has(_ta_on, _STEM) and "tdd-gate" in _ta_on)
check("required + hooks.tdd_gate false: no stem rule, no tdd-gate sentence",
      not has(_sd_off, _STEM) and "tdd-gate" not in _ta_off
      and "tdd-gate" not in _sd_off)
check("encouraged with no tdd-gate: no stem rule, no tdd-gate sentence",
      not has(_sd_enc, _STEM) and "tdd-gate" not in _ta_enc)
check("test-author: the test-gate sentence only when test-gate is wired",
      has(_ta, "the test gate refuses a commit while tests fail")
      and "test gate" not in _ta_off
      and has(_ta_off, "commit the tests with the source that makes them "
                       "pass, never on their own"))
check("test-author: no commit while tests fail", "Do not commit yet" in _ta
      and "Do not commit yet" in _ta_off)
check("greenfield: no retrofit rollout-week clause",
      "rollout warn-only week" not in _sd_block + _sd + _ta)

print("\n== test-author ==")
check("test-author: tests only at listed paths (rebuild mutant X8, "
      "conformance X4)", has(_ta, "3. Put tests only at paths the task's "
                                  "`Files:` list names."))
check("test-author: a missing test path is added with the Edit tool, stop "
      "and ask if refused", has(_ta, "add it to the list first, with the "
                                     "Edit tool; if Claude Code refuses the "
                                     "edit, stop and ask."))
check("test-author: runs in the implementer's checkout, never ahead of it "
      "in main (critic 2f)",
      has(_ta, "Run this in the checkout where the task is implemented: the "
               "implementer's worktree when it has one, never the main "
               "checkout ahead of the implementer.")
      and has(_ta, "commit the tests and the source together, in that same "
                   "checkout."))

print("\n== autonomous modes ==")
_lg = skill(_PLANS["loop+goal"], "spec-decompose") or ""
_wrapper_re = re.compile(r"^[ \t]*loop_eligible:[ \t]*true[ \t]*$", re.M)
check("loop mode: five criteria and a loop_eligible line the wrapper's grep "
      "matches", "five criteria" in _lg and bool(_wrapper_re.search(_lg)))
check("loop mode: loop_max_iterations default 10",
      "loop_max_iterations: 10" in _lg)
# The wrappers match `^[[:space:]]*loop_eligible:[[:space:]]*true[[:space:]]*$`
# (lib/templates.py _per_task_wrapper), so a trailing comment on the flag
# line reads as NOT eligible. Both the greenfield text and the retrofit
# override paragraph must say so.
check("loop mode: nothing may follow the flag value (wrapper exact match)",
      "not even a\ncomment" in _lg)
check("greenfield loop mode: 'is on'", "Loop mode is on." in _lg)
check("goal mode: sixth criterion and goal_condition",
      "sixth question" in _lg and "goal_condition:" in _lg
      and re.search(r"^goal_supervised_eligible: true$", _lg, re.M))
_go = bodies(cfg_from(GOAL_ONLY.format(tdd='"off"')))
_go_sd = skill(_go, "spec-decompose") or ""
check("goal only: the five criteria are present (the sixth combines with "
      "them), the loop fields are not",
      "five criteria" in _go_sd and "loop_max_iterations" not in _go_sd)
_lq = skill(_PLANS["loop+queue"], "spec-decompose") or ""
check("greenfield queue mode: the queue block is emitted (rebuild mutant X1)",
      has(_lq, "Queue mode is on. This skill does not write "
               "`.claude/queue/backlog.md`")
      and "Queue mode" not in _lg)
# [WP3 fix1 MT-3] The backlog the same install emits agrees with the skill:
# it said its sections were "populated by spec-decompose".
_bl = _PLANS["loop+queue"].get(".claude/queue/backlog.md", "")
check("queue mode: backlog.md says the operator adds the tasks from the list "
      "/spec-decompose prints, not that spec-decompose populates it (MT-3)",
      has(_bl, "Ready to run / Operator-only / Deferred: the operator adds "
               "tasks here from the list /spec-decompose prints")
      and "populated by spec-decompose" not in _bl, _bl[:300])

print("\n== retrofit spec-decompose composes the same body ==")
_rsd = skill(_PLANS["retrofit-loop"], "spec-decompose") or ""
_rq = skill(_PLANS["retrofit-loop+queue"], "spec-decompose") or ""
_rgo = skill(_PLANS["retrofit-goal"], "spec-decompose") or ""
check("retrofit: flavour heading and classifier kept (16.14/16.15 anchors)",
      "Retrofit-flavor" in _rsd and "Brownfield-eligibility classifier"
      in _rsd and "goal_supervised_eligible" in _rsd)
check("retrofit: carries the greenfield head, Files rules and map verbatim",
      templates._SPEC_DECOMPOSE_HEAD in _rsd
      and templates._spec_decompose_core(_FIXTURES["retrofit-loop"]) in _rsd
      and templates._SPEC_DECOMPOSE_MAP in _rsd)
check("retrofit: the same Files bullets as greenfield",
      templates._SPEC_DECOMPOSE_FILES.split("@@STEM@@\n")[1] in _rsd
      and templates._SPEC_DECOMPOSE_FILES.split("@@STEM@@\n")[1] in _sd)
# [critic 2j] In retrofit the runtime *_enabled flags stay false and the
# wrappers refuse to run: the modes are opted in, not on.
check("retrofit: loop classifier keyed on the opt-in, worded 'opted in'",
      has(_rsd, "Loop mode is opted in. Its wrapper refuses to run until the "
                "operator sets `loop_mode_enabled` to true")
      and "Loop mode is on." not in _rsd)
check("retrofit queue opt-in: the queue block is emitted, opted in "
      "(rebuild mutant X4)", has(_rq, "Queue mode is opted in.")
      and has(_rq, "This skill does not write `.claude/queue/backlog.md`"))
check("retrofit queue opt-in: no contradictory backlog text (critic 2j)",
      "are placed in the **Operator-only** section" not in _rq
      and has(_rq, "belongs in the **Operator-only** section of "
                   "`.claude/queue/backlog.md`")
      and has(_rq, "Name that section for it when you list the tasks for the "
                   "operator."))
check("retrofit goal-only opt-in: the sixth criterion, opted in (rebuild "
      "mutant X5)", "sixth question" in _rgo
      and has(_rgo, "Goal-supervised mode is opted in.")
      and "loop_max_iterations" not in _rgo)
check("retrofit: brownfield layer sits before the roster step",
      0 < _rsd.find("Brownfield-eligibility") < _rsd.find("## Roster"))
check("retrofit: override rationale goes on its own line",
      "Put the rationale on its own line" in _rsd)
check("retrofit: the allowlist is exempt from the check but still listed",
      has(_rsd, "Files on the legacy allowlist "
                "(`.claude/steering/spec-strategy.md`) are exempt from the "
                "check, but list them too")
      and "legacy allowlist" not in _sd)
check("retrofit block mode: the check sentence names the rollout warn weeks",
      has(_rq, "or the commit is refused (in a retrofit rollout warn-only "
               "week it warns instead)."))
_strat = _PLANS["retrofit-loop"].get(".claude/steering/spec-strategy.md", "")
_promo = _strat[_strat.find("## Promotion rule"):
                _strat.find("## Retrofit-active master switch")]
check("retrofit promotion rule names /spec-decompose and the task file's "
      "Files: list (cverify scope-and-records)",
      "/spec-new" in _promo and "/spec-decompose <slug>" in _promo
      and has(_promo, "`Files:` list "
                      "(`.claude/specs/<slug>/tasks/<slug>-T<NN>.md`)")
      and _promo.find("/spec-new") < _promo.find("/spec-decompose")
      < _promo.find("Make the modification"), _promo)
# [WP3 fix1 MT-4] The allowlist exempts a file until no line of it matches
# (retrofit_is_allowlisted, spec-check.sh's retrofit arm); the last step
# said "the spec gates now enforce" with the line still in place.
check("retrofit promotion rule: the last step says the gates check the file "
      "only once no allowlist line matches it, and to delete or narrow that "
      "line (MT-4)",
      "the spec gates now enforce" not in _promo
      and has(_promo, "check this file only once no line of the legacy "
                      "allowlist below matches it: delete or narrow that "
                      "line"), _promo)

print("\n== spec-validate and decision-log ==")
_sv = skill(_g, "spec-validate") or ""
check("spec-validate: validates at the task's spec_version",
      "spec_version" in _sv and "A minor bump apart" in _sv
      and "A major bump apart: stop." in _sv)
check("spec-validate: records the version it validated against",
      "Spec version validated against:" in _sv
      and "validated_version:" in _sv)
check("spec-validate: report goes to validation.md, stamped from the clock",
      ".claude/specs/<slug>/validation.md" in _sv
      and "date -u +%Y-%m-%dT%H:%MZ" in _sv)
check("spec-validate: a whole-spec pass sets INDEX complete (rebuild "
      "mutant X6)", has(_sv, "set the spec's status in "
                             "`.claude/specs/INDEX.md` to `complete`."))
check("spec-validate: refreshes the roster row (versioning delta 2)",
      has(_sv, "Then refresh " + _REFRESH))
check("spec-validate: commits validation.md, the task and INDEX.md "
      "(critic 2c)", has(_sv, "Commit `validation.md`, the task files you "
                              "changed and `.claude/specs/INDEX.md` together"))
check("spec-validate: runs in the main checkout after the work landed",
      has(_sv, "Run this in the main checkout, after the task's work has "
               "landed."))
check("spec-validate: `current` re-validates at the current version and "
      "re-points spec_version (closes the step-9 dead end)",
      has(_sv, "With `current` (a re-validation after a bump")
      and has(_sv, "With `current`, also set its `spec_version` to that "
                   "version.")
      and has(_sv, "After \"pass, re-validate against <version>\", it is "
                   "`/spec-validate <slug> <task-id> current`."))
check("spec-validate: next step after a pass is /pr-author",
      has(_sv, "After a pass, the next step is `/pr-author <slug>`."))
_dl = skill(_g, "decision-log") or ""
for field in ("- Context:", "- Options considered:", "- Decision:",
              "- Rationale:"):
    check(f"decision-log: entry field {field}", field in _dl)
check("decision-log: timestamp from the clock, append-only",
      "date -u +%Y-%m-%dT%H:%MZ" in _dl and "Never edit or delete" in _dl)
check("decision-log: writes decisions.md, never a decisions-log-<id> file",
      ".claude/specs/<slug>/decisions.md" in _dl
      and "decisions-log-" not in _dl)

print("\n== spec-review and plan-review bodies ==")
_pr = skill(_g, "plan-review") or ""
check("plan-review: checks coverage on Covers: lines and the Files: form",
      "`Covers:`" in _pr and "exactly\n   `Files:`" in _pr
      and "share no file" in _pr
      and has(_pr, "no absolute path, no backticks, no link, no note after "
                   "the path"))
check("plan-review: start a task by setting in-progress in the main "
      "checkout, then commit before dispatch (critic 2c, 2d)",
      has(_pr, "To start a task, set its `status` to `in-progress` in the "
               "main checkout, with the Edit tool (the implementer never "
               "edits it).") and has(_pr, _COMMIT))
_sr = skill(_g, "spec-review") or ""
check("spec-review: reports, never edits, and ends with ready or revise",
      "do not edit the spec" in _sr and "`ready`" in _sr and "`revise`" in _sr)

print("\n== one write path: the Write and Edit tools ==")
# Headless runs wrote .claude/specs/ files through shell heredocs as their
# first move (one wrote with 0 denials after a `cd`); the tools are the path
# Claude Code's protected-path prompt covers, so D5, not command shape,
# decides whether a headless write lands. A refused write is never routed
# around (operator ruling 2026-10-05; live-run label EDITED_TASK_VIA_SCRIPT).
for name in ("spec-new", "spec-decompose", "spec-validate", "decision-log"):
    b = skill(_g, name) or ""
    check(f"{name}: writes through the Write and Edit tools, not redirection",
          has(b, "Write and change these files with the Write and Edit "
                 "tools, not with shell redirection"))
    check(f"{name}: a refused write means stop and ask, no other route",
          has(b, _REFUSED_WRITE))
check("retrofit spec-decompose carries the same write rule",
      has(_rsd, _REFUSED_WRITE))

print("\n== no accidental argument substitution ==")
# Claude Code replaces $ARGUMENTS and $<digit> in a skill body.
for label, plan in _PLANS.items():
    hits = {p: re.findall(r"\$(?:ARGUMENTS|[0-9])", v) for p, v in plan.items()
            if p.startswith(".claude/skills/")}
    hits = {p: h for p, h in hits.items() if h}
    check(f"[{label}] no $ARGUMENTS or $<digit> in any skill body", not hits,
          hits)


# --------------------------------------------------------------------------- #
# 4. The taught Files syntax against the EMITTED check, and the taught stem
#    rule against the EMITTED tdd-gate
# --------------------------------------------------------------------------- #
print("\n== the Files list the skill teaches clears the emitted check ==")
if not (shutil.which("bash") and shutil.which("git")):
    print("  SKIP  bash or git missing")
else:
    m = re.search(r"## Task file.*?```markdown\n(.*?)```", _sd, re.S)
    check("task template extracted from the emitted body", m is not None)
    tmpl = m.group(1) if m else ""
    tmp = tempfile.mkdtemp(prefix="skill-bodies-")
    try:
        proj = os.path.join(tmp, "proj")
        for a in build_plan(_FIXTURES["tdd-required"]):
            fp = os.path.join(proj, *a["path"].split("/"))
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write(a["body"])
            os.chmod(fp, a["mode"])
        # The fixture repository sits under TMPDIR, which may itself be in a
        # git work tree: stop git's discovery at tmp (critic 1j).
        env = dict(os.environ, CLAUDE_PROJECT_DIR=proj,
                   GIT_CEILING_DIRECTORIES=tmp,
                   GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        env.pop("CLAUDECODE", None)

        def git(*args):
            return subprocess.run(["git", *args], cwd=proj, env=env,
                                  capture_output=True, text=True)

        git("init", "-q")
        check("fixture repository is its own work tree",
              git("rev-parse", "--show-toplevel").stdout.strip()
              == os.path.realpath(proj))
        tdir = os.path.join(proj, ".claude", "specs", "demo", "tasks")
        os.makedirs(tdir)

        def fill(files_block):
            return (tmpl.replace("<slug>", "demo")
                    .replace("- src/<path>\n- tests/<path>\n", files_block))

        def gate_rc(files_block, staged):
            """spec-check.sh --staged, with the task file staged too: D2's
            check of record reads task files from the index."""
            task = fill(files_block)
            with open(os.path.join(tdir, "demo-T01.md"), "w") as fh:
                fh.write(task)
            git("reset", "-q")
            fp = os.path.join(proj, *staged.split("/"))
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "w") as fh:
                fh.write("x\n")
            git("add", "--", staged)
            git("add", "-f", "--", os.path.relpath(
                os.path.join(tdir, "demo-T01.md"), proj))
            r = subprocess.run(
                ["bash", os.path.join(proj, ".claude", "githooks",
                                      "spec-check.sh"), "--staged"],
                cwd=proj, env=env, capture_output=True, text=True,
                timeout=60)
            git("reset", "-q")
            os.remove(fp)
            return r.returncode

        _taught = "- src/app/core.py\n- tests/test_core.py\n"
        check("taught form: a listed source file clears the check (rc 0)",
              gate_rc(_taught, "src/app/core.py") == 0)
        check("taught form: a listed test file clears the check (rc 0)",
              gate_rc(_taught, "tests/test_core.py") == 0)
        check("taught form: an unlisted file is still refused (rc 2)",
              gate_rc(_taught, "src/app/other.py") == 2)
        check("forbidden form `./src/...` does NOT clear it (rc 2), so the "
              "skill's ban is load-bearing",
              gate_rc("- ./src/app/core.py\n", "src/app/core.py") == 2)
        check("forbidden form, a link target, does NOT clear it (rc 2)",
              gate_rc("- [core](../../../../src/app/core.py)\n",
                      "src/app/core.py") == 2)
        check("forbidden form, a note after the path, does NOT clear it (rc 2)",
              gate_rc("- src/app/core.py (new)\n", "src/app/core.py") == 2)
        check("an indented list is no list: it does NOT clear (rc 2)",
              gate_rc("  - src/app/core.py\n", "src/app/core.py") == 2)
        check("prose outside the list covers nothing (rc 2): 'only the list "
              "counts'", gate_rc("- src/app/core.py\n\nNotes: may later touch "
                                 "src/app/other.py.\n",
                                 "src/app/other.py") == 2)
        check("a directory entry clears a file under it (rc 0): D2's "
              "directory arm, which the skill teaches",
              gate_rc("- src/app/\n", "src/app/core.py") == 0)

        # The stem example the body teaches, end to end: the listed pair
        # clears the check, and the stem-named test satisfies the emitted
        # tdd-gate where the feature-named one does not.
        sm = re.search(r"`(src/[^`]+)`\s+needs\s+`(tests/[^`]+)`", _sd)
        fm_ = re.search(r"feature-named test such as\s+`(tests/[^`]+)`", _sd)
        check("stem example extracted from the emitted body",
              sm is not None and fm_ is not None)
        if sm and fm_:
            src, stem_t, feat_t = sm.group(1), sm.group(2), fm_.group(1)
            pair = f"- {src}\n- {stem_t}\n"
            check("stem example: both listed paths clear the check (rc 0)",
                  gate_rc(pair, src) == 0 and gate_rc(pair, stem_t) == 0)

            def tdd_rc():
                payload = {"tool_name": "Write",
                           "hook_event_name": "PreToolUse",
                           "tool_input": {"file_path": src, "content": "x"}}
                hk = {k: v for k, v in env.items()
                      if not k.startswith("CLAUDE")}
                hk["CLAUDE_PROJECT_DIR"] = proj
                return subprocess.run(
                    ["bash", os.path.join(proj, ".claude", "hooks",
                                          "tdd-gate.sh")],
                    input=json.dumps(payload), cwd=proj, env=hk,
                    capture_output=True, text=True, timeout=60).returncode

            def put(rel, present):
                fp = os.path.join(proj, *rel.split("/"))
                if present:
                    os.makedirs(os.path.dirname(fp), exist_ok=True)
                    with open(fp, "w") as fh:
                        fh.write("def test_x():\n    pass\n")
                elif os.path.exists(fp):
                    os.remove(fp)

            put(feat_t, True)
            put(stem_t, False)
            check("stem example: a feature-named test alone does NOT satisfy "
                  "the emitted tdd-gate (rc 2), which is why the rule exists",
                  tdd_rc() == 2)
            put(stem_t, True)
            check("stem example: the stem-named test the body names satisfies "
                  "the emitted tdd-gate (rc 0)", tdd_rc() == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

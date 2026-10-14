#!/usr/bin/env python3
"""[WP4 / g1] The CLAUDE.md the installer writes, against PRD Phase 8.

Behavioural rows for the Phase 8 items WP4 builds into the greenfield
CLAUDE.md: the steering index, the specs, learnings and sessions references,
the TDD-adaptive lifecycle (one paragraph, ending at ci-cd.md's stop), session
hygiene, the Never list and the gates-off escalations. Then the retrofit
CLAUDE.md's urgent list, which shares the greenfield items (X3), and the
80-line budget over the g1 config matrix.

The decision record is not here. Ruling 7 (c) moved it from a printf block in
CLAUDE.md to the `/escalate` skill, so its rows live in
tests/test_wp4_escalate.py. The prototype's six decision-record rows were
deleted, not reworded: two went red with the block gone, and four sat behind
`if cmd and BASH:` and would have stopped running with no FAIL.

Run: python3 tests/test_wp4_claude_md.py
"""
import ast
import itertools
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

from defaults import resolve_config            # noqa: E402
from installer import build_plan               # noqa: E402
from minyaml import load_yaml                  # noqa: E402

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
            print(f"        {str(detail)[:600]}")


def cfg_text(tdd="encouraged", sec=True, deps=True, design=False, tel=False,
             modes=False, drift=True, tdd_gate=None, cicd_opt_out=False,
             arch="service", skills=True, commands=True):
    t = (f"project:\n  name: g1\n  archetype: {arch}\n"
         f"  cicd_opt_out: {str(cicd_opt_out).lower()}\n"
         f"principles:\n  tdd_policy: \"{tdd}\"\n"
         f"secrets:\n  enabled: {str(sec).lower()}\n"
         f"deps:\n  enabled: {str(deps).lower()}\n"
         f"design_steering_enabled: {str(design).lower()}\n"
         f"telemetry_export_enabled: {str(tel).lower()}\n"
         f"autonomous_modes:\n"
         f"  loop_mode_enabled: {str(modes).lower()}\n"
         f"  goal_supervised_mode_enabled: {str(modes).lower()}\n"
         f"  queue_mode_enabled: {str(modes).lower()}\n"
         f"hooks:\n  drift_detector: {str(drift).lower()}\n")
    if tdd_gate is not None:
        t += f"  tdd_gate: {str(tdd_gate).lower()}\n"
    if not (skills and commands):
        t += (f"workflow:\n  install_skills: {str(skills).lower()}\n"
              f"  install_commands: {str(commands).lower()}\n")
    return t + 'commands:\n  test: "pytest -q"\n  lint: "ruff check ."\n'


def plan_of(text):
    cfg, errs = resolve_config(load_yaml(text))
    assert not errs, errs
    return cfg, {a["path"]: a for a in build_plan(cfg)}


def md_of(plan):
    return plan["CLAUDE.md"]["body"]


def section(md, heading):
    """The text under `## <heading...>` up to the next `## ` heading."""
    m = re.search(r"^## " + re.escape(heading) + r".*?$(.*?)(?=^## |\Z)", md,
                  re.M | re.S)
    return m.group(1) if m else ""


def flat(s):
    return " ".join(s.split())


CONFIGS = {
    "default-like": cfg_text(),
    "gates off": cfg_text(sec=False, deps=False),
    "deps off only": cfg_text(deps=False),
    "secrets off only": cfg_text(sec=False),
    "design on": cfg_text(arch="fullstack", design=True),
    "telemetry on": cfg_text(tel=True),
    "ci/cd opted out": cfg_text(cicd_opt_out=True),
    "all modes, tdd required": cfg_text(tdd="required", modes=True),
    # [WP4 fix round 1 / C3] workflow.install_skills and install_commands.
    "skills off": cfg_text(skills=False),
    "commands off": cfg_text(commands=False),
}
PLANS = {k: plan_of(v) for k, v in CONFIGS.items()}

# --------------------------------------------------------------------------- #
print("\n=== Steering index (PRD Phase 8: references to all created steering "
      "docs) ===")
for label, (cfg, plan) in PLANS.items():
    md = md_of(plan)
    idx = section(md, "Index")
    emitted = {p.rsplit("/", 1)[1] for p in plan
               if p.startswith(".claude/steering/")}
    steer = idx[:idx.find("- `.claude/specs/")] if idx else ""
    named = set(re.findall(r"`([a-z0-9-]+\.md)`", steer))
    check(f"{label}: CLAUDE.md names exactly the {len(emitted)} steering docs "
          f"the plan writes", named == emitted,
          {"missing": sorted(emitted - named),
           "dangling": sorted(named - emitted)})

# --------------------------------------------------------------------------- #
print("\n=== Specs, learnings and sessions references ===")
for label in ("default-like", "gates off"):
    md = md_of(PLANS[label][1])
    idx = section(md, "Index")
    for ref, readme in ((".claude/specs/INDEX.md", ".claude/specs/README.md"),
                        (".claude/learnings/", ".claude/learnings/README.md"),
                        (".claude/sessions/", ".claude/sessions/README.md")):
        check(f"{label}: the index names `{ref}`, and the plan writes "
              f"{readme}", f"`{ref}`" in idx and readme in PLANS[label][1])

# --------------------------------------------------------------------------- #
print("\n=== No reference to a steering file the install did not write ===")
for label, (cfg, plan) in PLANS.items():
    md = md_of(plan)
    named = set(re.findall(r"`(?:\.claude/steering/)?([a-z0-9-]+\.md)`", md))
    steering_names = {"product.md", "tech.md", "deps.md", "secrets.md",
                      "structure.md", "principles.md", "ci-cd.md", "tools.md",
                      "spec-versioning.md", "design.md", "telemetry.md",
                      "assumption-ledger.md"}
    dangling = sorted(n for n in named & steering_names
                      if f".claude/steering/{n}" not in plan)
    check(f"{label}: every steering doc CLAUDE.md names is in the plan",
          not dangling, dangling)

# --------------------------------------------------------------------------- #
print("\n=== Gates off: the escalations follow the policies ===")
for label, (cfg, plan) in PLANS.items():
    md = md_of(plan)
    urgent = section(md, "Urgent escalations")
    nums = [int(n) for n in re.findall(r"^(\d+)\. ", urgent, re.M)]
    check(f"{label}: urgent items are numbered 1..{len(nums)}",
          nums == list(range(1, len(nums) + 1)) and nums, nums)
    check(f"{label}: every urgent item carries the bell",
          nums and len(re.findall(r"^\d+\. \*\*🔔\*\* ", urgent, re.M))
          == len(nums))
    deps_on, sec_on = cfg["deps"]["enabled"], cfg["secrets"]["enabled"]
    check(f"{label}: a deps.md escalation exactly when deps.md is written",
          ("`deps.md`" in urgent) == deps_on
          and (".claude/steering/deps.md" in plan) == deps_on)
    check(f"{label}: never-read wording exactly when secrets.md is written",
          ("never-read" in md) == sec_on and ("secrets.md" in md) == sec_on)

# --------------------------------------------------------------------------- #
print("\n=== Session hygiene (a Phase 8 exit criterion) ===")
for label, (cfg, plan) in PLANS.items():
    md = flat(md_of(plan))
    if not cfg["workflow"]["install_skills"]:
        continue
    check(f"{label}: /checkpoint before /clear, /resume after",
          "`/checkpoint` before `/clear`" in md and "`/resume`" in md)
_, _nodrift = plan_of(cfg_text(drift=False))
check("drift detector on: /ack-drift is named",
      "`/ack-drift`" in md_of(PLANS["default-like"][1]))
check("drift detector off: neither the detector nor /ack-drift is named",
      "drift detector" not in md_of(_nodrift)
      and "/ack-drift" not in md_of(_nodrift))

# [WP4 fix round 1 / C3] Each slash command CLAUDE.md names is a skill the
# install writes (its command, where written, only invokes the skill), so
# with the skills off CLAUDE.md names none; /clear is Claude Code's own.
for label, (cfg, plan) in PLANS.items():
    md = md_of(plan)
    named = sorted(set(re.findall(r"`(/[a-z][\w-]*)", md)) - {"/clear"})
    absent = [n for n in named
              if f".claude/skills/{n[1:]}/SKILL.md" not in plan]
    check(f"{label}: every slash command CLAUDE.md names is a skill this "
          f"install writes ({len(named)} named)",
          not absent and (bool(named) == cfg["workflow"]["install_skills"]),
          {"named": named, "absent": absent})
check("skills off: CLAUDE.md has no session-hygiene line and no /escalate "
      "line, and its blank lines stay single",
      "Session hygiene" not in md_of(PLANS["skills off"][1])
      and "/escalate" not in md_of(PLANS["skills off"][1])
      and "\n\n\n" not in md_of(PLANS["skills off"][1]),
      md_of(PLANS["skills off"][1])[-1200:])
check("commands off, skills on: CLAUDE.md is the default-like one, byte for "
      "byte", md_of(PLANS["commands off"][1])
      == md_of(PLANS["default-like"][1]))

# --------------------------------------------------------------------------- #
print("\n=== The Never list ===")
for label, (cfg, plan) in PLANS.items():
    nv = flat(section(md_of(plan), "Never"))
    # [V3] "Commit code without its tests.": the prototype's "Commit without
    # tests." also read as a ban on committing a doc or a config change.
    check(f"{label}: the three universal rules",
          "Rewrite or delete a test to make it pass." in nv
          and ("Implement a spec that has not passed `/spec-review`." in nv
               if cfg["workflow"]["install_skills"] else
               "Implement a spec that has not passed spec review." in nv)
          and "Commit code without its tests." in nv, nv)
    check(f"{label}: Do Not Touch points at tech.md; never-read at "
          f"secrets.md only when it is written",
          "Do Not Touch path (`tech.md`)" in nv
          and ("`secrets.md`" in nv) == cfg["secrets"]["enabled"], nv)

# --------------------------------------------------------------------------- #
print("\n=== TDD-adaptive lifecycle (PRD Phase 7: 6 gates off, 7 on) ===")
SUFFIX = ("-> code-review (the reviewer agent) -> merge-back -> spec-validate "
          "-> pr-author -> stop as `ci-cd.md` says.")
lc = {}
for tdd, gate in itertools.product(("off", "encouraged", "required"),
                                   (None, True, False)):
    _, p = plan_of(cfg_text(tdd=tdd, tdd_gate=gate))
    wf = flat(section(md_of(p), "Workflow"))
    lc[(tdd, gate)] = wf[:wf.find("At task/iteration priming")]
    # [V3] ONE lifecycle paragraph, and it carries both the TDD step and
    # g2's pointer: a merge that keeps both sides of the g1/g2 conflict
    # emits two lifecycles and passed every row before this.
    paras = [flat(x) for x in md_of(p).split("\n\n")
             if x.startswith("Per-task lifecycle:")]
    check(f"tdd {tdd}, hooks.tdd_gate {gate}: one lifecycle, ending at "
          f"ci-cd.md's stop",
          md_of(p).count("Per-task lifecycle:") == 1 and len(paras) == 1
          and SUFFIX in paras[0], paras)
check("off, encouraged and required give three different lifecycles",
      len({lc[("off", None)], lc[("encouraged", None)],
           lc[("required", None)]}) == 3)
check("off: no tests-first step", "failing test first"
      not in lc[("off", None)])
check("encouraged: tests first is preferred and unenforced",
      "failing test first, preferred" in lc[("encouraged", None)]
      and "no gate enforces the order" in lc[("encouraged", None)])
check("required: the tdd-gate is named as the enforcement",
      "failing test first;" in lc[("required", None)]
      and "the tdd-gate refuses a source write" in lc[("required", None)])
check("required with hooks.tdd_gate false: says no hook enforces it",
      "no hook enforces the order" in lc[("required", False)]
      and "tdd-gate" not in lc[("required", False)])
check("encouraged with hooks.tdd_gate true: names the forced gate",
      "the tdd-gate refuses" in lc[("encouraged", True)])
check("the tests-first step stays the implementer's: test-author is not a "
      "main-session step before dispatch (WP3 critic 2f)",
      all("test-author" not in v for v in lc.values()))

# --------------------------------------------------------------------------- #
print("\n=== Retrofit: the urgent list follows the same switches (X3) ===")
# Verify V1: the retrofit CLAUDE.md named deps.md and never-read with both
# policies off, on every one of 260 configs each. Its items 1-5 are now
# greenfield's own (one helper; a second hand-kept copy had already drifted),
# then retrofit's two. The archetype never changes the retrofit body, so the
# rows are 2 fixture shapes x 4 switch combinations, not an archetype loop.


def _retrofit_fixture(name):
    """A retrofit golden fixture's config text, read by ast from
    tests/test_retrofit.py (as tests/test_merge_back.py reads them)."""
    path = os.path.join(HERE, "test_retrofit.py")
    for node in ast.parse(open(path).read()).body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and getattr(node.targets[0], "id", None) == name):
            return eval(compile(ast.Expression(node.value), path, "eval"))
    raise LookupError(name)


def urgent_items(md):
    """[(number, flattened text)] for each urgent item, its continuation
    lines joined."""
    items = []
    for ln in section(md, "Urgent escalations").split("\n"):
        m = re.match(r"^(\d+)\. (.*)$", ln)
        if m:
            items.append([int(m.group(1)), m.group(2)])
        elif ln.startswith("   ") and items:
            items[-1][1] += " " + ln.strip()
        elif items and not ln.strip():
            break
    return [(n, flat(t)) for n, t in items]


def switched(text, sec, deps):
    """`text` with its secrets and deps policies set to `sec` and `deps`."""
    for key, on in (("secrets", sec), ("deps", deps)):
        assert f"{key}:\n  enabled: true\n" in text, key
        text = text.replace(f"{key}:\n  enabled: true\n",
                            f"{key}:\n  enabled: {str(on).lower()}\n")
    return text


RETRO_ONLY = ("**🔔** Modifying a file in the legacy allowlist WITHOUT first "
              "creating a spec via touch-based backfill.",
              "**🔔** Modifying a file in `inventory/danger-zones.md` WITHOUT "
              "first generating a `legacy-pin-test` (or for AI/agent prompt "
              "files, a `prompt-pinning-eval`).")
for shape in ("SERVICE_RETROFIT_CFG", "AGENT_RETROFIT_CFG"):
    for sec, deps in itertools.product((True, False), (True, False)):
        _, rp = plan_of(switched(_retrofit_fixture(shape), sec, deps))
        _, gp = plan_of(cfg_text(sec=sec, deps=deps))
        r_md = md_of(rp)
        r_urgent = section(r_md, "Urgent escalations")
        r_items, g_items = urgent_items(r_md), urgent_items(md_of(gp))
        problems = []
        if [n for n, _ in r_items] != list(range(1, len(r_items) + 1)):
            problems.append(("numbering", [n for n, _ in r_items]))
        if not all(t.startswith("**🔔** ") for _, t in r_items):
            problems.append("an item without the bell")
        if (("`deps.md`" in r_urgent) != deps
                or (".claude/steering/deps.md" in rp) != deps):
            problems.append("deps.md named or written against the switch")
        if (("never-read" in r_md) != sec
                or (".claude/steering/secrets.md" in rp) != sec):
            problems.append("never-read wording or secrets.md against it")
        if [t for _, t in r_items] != [t for _, t in g_items] + list(
                RETRO_ONLY):
            problems.append(("not greenfield's items, then retrofit's two",
                             [t for _, t in r_items]))
        check(f"retrofit {shape.split('_')[0].lower()}, secrets "
              f"{'on' if sec else 'off'}, deps {'on' if deps else 'off'}: "
              f"greenfield's items then retrofit's two, numbered, belled, "
              f"naming only written files",
              not problems, problems)
# R8.D skipped: the spec-versioning pointer is still rewritten in the shared
# item, renumbered to 4 with deps off (_SPEC_VERSIONING_POINTERS).
_, _skip = plan_of(switched(_retrofit_fixture("SERVICE_RETROFIT_CFG"),
                            True, False)
                   + "  skip_decisions:\n    R8_D_spec_versioning: \"skip\"\n")
_skip_md = md_of(_skip)
check("retrofit, deps off, R8.D skipped: item 4 drops the spec-versioning "
      "pointer, and nothing names the file the install dropped",
      "4. **🔔** Implementation reveals the spec was wrong.\n" in _skip_md
      and "spec-versioning" not in _skip_md
      and ".claude/steering/spec-versioning.md" not in _skip
      and [n for n, _ in urgent_items(_skip_md)] == list(range(1, 7)),
      section(_skip_md, "Urgent escalations"))

# --------------------------------------------------------------------------- #
print("\n=== Thin: CLAUDE.md within budget (PRD Phase 8 step 2) ===")
# The golden fixtures' cap is 80 (tests/test_merge_back.py). Over this
# matrix the plan's budget is 76: the measured worst is 70, and the queue
# section is the only optional block that adds lines.
worst = 0
for tdd, sec, deps, design, tel, modes in itertools.product(
        ("off", "encouraged", "required"), (True, False), (True, False),
        (True, False), (True, False), (True, False)):
    _, p = plan_of(cfg_text(tdd=tdd, sec=sec, deps=deps, design=design,
                            tel=tel, modes=modes, arch="fullstack"))
    worst = max(worst, md_of(p).count("\n"))
check(f"CLAUDE.md is at most 76 lines over 96 configs (worst {worst})",
      worst <= 76, worst)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

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
import hashlib
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
             arch="service", skills=True, commands=True, alarm=True):
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
    if not alarm:
        t += "  decision_required_alarm: false\n"
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
    # [WP4 fix round 3 / LP-13] No /escalate and no alarm: nothing writes
    # the decision record.
    "skills and alarm off": cfg_text(skills=False, alarm=False),
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
# [WP4 fix round 2 / MS-3, D2] The same for every other .md that WP4 wrote
# or changed. The sessions README's /ack-drift, /checkpoint, /quiet and
# /resume rows predate WP4 (backlog Z-66), so they are left out here.
WP4_MD = {".claude/steering/tech.md": (), ".claude/steering/ci-cd.md": (),
          ".claude/steering/assumption-ledger.md": (),
          ".claude/sessions/README.md": ("/ack-drift", "/checkpoint",
                                         "/quiet", "/resume"),
          ".claude/skills/spec-new/SKILL.md": (),
          ".claude/skills/escalate/SKILL.md": (),
          ".claude/commands/escalate.md": ()}
for label, (cfg, plan) in PLANS.items():
    absent = {}
    for path, pre in WP4_MD.items():
        if path not in plan:
            continue
        named = (set(re.findall(r"`(/[a-z][\w-]*)", plan[path]["body"]))
                 - {"/clear"} - set(pre))
        missing = sorted(n for n in named
                         if f".claude/skills/{n[1:]}/SKILL.md" not in plan)
        if missing:
            absent[path] = missing
    check(f"{label}: every slash command the other .md files WP4 wrote or "
          f"changed name is a skill this install writes", not absent, absent)
_off = PLANS["skills off"][1]
check("skills off: ci-cd.md's stop names no /pr-author, the ledger has no "
      "skill-body substitution row, and the sessions README says only the "
      "alarm writes the decision record",
      "a description that links to the spec" in flat(
          _off[".claude/steering/ci-cd.md"]["body"])
      and "/pr-author" not in _off[".claude/steering/ci-cd.md"]["body"]
      and "Skill-body substitution" not in
      _off[".claude/steering/assumption-ledger.md"]["body"]
      and "| `.decision-pending-<id>` | the decision-required alarm creates "
          "it, refreshes its mtime and deletes it after 7 days |"
      in _off[".claude/sessions/README.md"]["body"],
      [ln for ln in _off[".claude/sessions/README.md"]["body"].splitlines()
       if "decision-pending" in ln])
_both = PLANS["skills and alarm off"][1][".claude/sessions/README.md"]["body"]
check("skills and alarm off: the sessions README's decision-record row says "
      "nothing in this install writes it",
      "| `.decision-pending-<id>` | nothing in this install writes it |"
      in _both, [ln for ln in _both.splitlines() if "decision-pending" in ln])
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
print("\n=== The implementer and the urgent list (fix round 7 / Z-69) ===")
# [WP4 fix round 7 / Z-69, operator ruling 2026-10-15] In the live walk an
# implementer committed a 🔔 item and reported it afterwards. Its body now
# says the urgent list binds it: stop, commit nothing for the item, and name
# it first in the report; the main session records it with /escalate where
# the skills are installed. [WP4 fix round 8 / LC7-2] The stop and the Do
# Not Touch sentence are checked too.
URGENT_IMPL = ("Read the urgent list in `CLAUDE.md` (the 🔔 items) before "
               "you start: it binds you as it binds the main session.")


def urgent_impl_ok(cfg, plan):
    body = plan[".claude/agents/implementer.md"]["body"]
    imp, skills = flat(body), cfg["workflow"]["install_skills"]
    return ("\n## Urgent items (🔔)\n" in body and URGENT_IMPL in imp
            and "do not make that change, and commit nothing for it." in imp
            and "Stop and report it:" in imp
            and "A Do Not Touch path in `tech.md` is one of them." in imp
            and "start your report with a line that names the 🔔 item" in imp
            and ("/escalate" in imp) == skills
            and ("records it with `/escalate` and asks the operator." in imp
                 if skills else
                 "the main session stops and asks the operator." in imp))


for label, (cfg, plan) in PLANS.items():
    check(f"{label}: implementer.md binds the implementer to the urgent "
          f"list: stop, commit nothing for the item, name it first in the "
          f"report" + (", recorded with /escalate"
                       if cfg["workflow"]["install_skills"]
                       else ", with no /escalate to name"),
          urgent_impl_ok(cfg, plan),
          section(plan[".claude/agents/implementer.md"]["body"],
                  "Urgent items"))
for _fx in ("SERVICE_RETROFIT_CFG", "AGENT_RETROFIT_CFG"):
    _rc, _rp = plan_of(_retrofit_fixture(_fx))
    check(f"retrofit {_fx}: implementer.md carries the same urgent section",
          urgent_impl_ok(_rc, _rp),
          section(_rp[".claude/agents/implementer.md"]["body"],
                  "Urgent items"))

# --------------------------------------------------------------------------- #
print("\n=== Tidy-up: commands, landing steps, no operator passages "
      "(build plan section 15) ===")
# [claude-md-tidy-up] Rows a-e went red on 19cd75f; f-h are guards, green
# there by design.


def with_commands(text, **cmds):
    """`text` with its commands block replaced by `cmds` (key: value)."""
    head = text[:text.index("commands:\n")]
    return head + "commands:\n" + "".join(
        f"  {k}: {v}\n" for k, v in cmds.items())


def code_spans(line):
    """The contents of each CommonMark code span on `line` (spec 0.31.2,
    section 6.1): a run of n backticks opens, the next run of exactly n
    closes, and one space is stripped from each end when both ends have one
    and the content is not all spaces."""
    out, i = [], 0
    while True:
        m = re.compile(r"`+").search(line, i)
        if not m:
            return out
        n = len(m.group(0))
        for c in re.compile(r"`+").finditer(line, m.end()):
            if len(c.group(0)) == n:
                s = line[m.end():c.start()]
                if (len(s) >= 2 and s[0] == " " and s[-1] == " "
                        and s.strip(" ")):
                    s = s[1:-1]
                out.append(s)
                i = c.end()
                break
        else:
            return out


def command_bullets(md):
    """{label: rest of line} for each `- <Label>: ...` bullet under
    `## Commands`."""
    return dict(re.findall(r"^- (\w+): (.*)$", section(md, "Commands"),
                           re.M))


# a. The commands section, first, with test, lint and format.
_, p = plan_of(cfg_text())
md = md_of(p)
cb = command_bullets(md)
check("a: `## Commands` is the first section, right after the H1",
      md.split("\n## ", 1)[-1].startswith("Commands"), md[:300])
check("a: it lists Test, Lint and Format, in that order, and nothing else",
      list(cb) == ["Test", "Lint", "Format"], cb)
check("a: a set command is shown as configured",
      cb.get("Test") == "`pytest -q`" and cb.get("Lint") == "`ruff check .`",
      cb)
check("a: an empty command says where to set it and that a re-install "
      "applies it",
      cb.get("Format") == "not set (`commands.format` in "
      "`bootstrap.config.yaml`; re-install)", cb)
check("a: the heading names tech.md, where agents read the commands",
      re.search(r"^## Commands \(keep in step with `tech\.md`\)$", md, re.M)
      is not None, md[:300])
_, p = plan_of(with_commands(cfg_text(), test='"make test"',
                             lint='"make lint"', format='"make fmt"',
                             typecheck='"mypy ."', ci_local='"make ci"',
                             eval='"make eval"'))
check("a: typecheck, ci_local and eval are not listed",
      list(command_bullets(md_of(p))) == ["Test", "Lint", "Format"]
      and len(re.findall(r"^- ", section(md_of(p), "Commands"), re.M)) == 3,
      section(md_of(p), "Commands"))
check("a: with all six set, the section is the three bullets and nothing "
      "else, and no typecheck, ci_local or eval value is in CLAUDE.md",
      section(md_of(p), "Commands") == "\n\n- Test: `make test`\n"
      "- Lint: `make lint`\n- Format: `make fmt`\n\n"
      and not any(v in md_of(p) for v in ("mypy .", "make ci", "make eval")),
      section(md_of(p), "Commands"))
_, p = plan_of(with_commands(cfg_text(), test='"make test"',
                             typecheck='"mypy ."', eval='"make eval"'))
check("a: with only test, typecheck and eval set, the three bullets are "
      "listed and no typecheck or eval value is in CLAUDE.md",
      not any(v in md_of(p) for v in ("mypy .", "make eval"))
      and list(command_bullets(md_of(p))) == ["Test", "Lint", "Format"]
      and len(section(md_of(p), "Commands").strip().split("\n")) == 3,
      section(md_of(p), "Commands"))
_, p = plan_of(with_commands(cfg_text(), typecheck='"mypy ."',
                             ci_local='"make ci"', eval='"make eval"'))
check("a: with test, lint and format unset, the section is the three "
      "not-set bullets, and no typecheck, ci_local or eval value is in "
      "CLAUDE.md",
      section(md_of(p), "Commands") == "\n\n" + "".join(
          f"- {k.title()}: not set (`commands.{k}` in "
          "`bootstrap.config.yaml`; re-install)\n"
          for k in ("test", "lint", "format")) + "\n"
      and not any(v in md_of(p) for v in ("mypy .", "make ci", "make eval")),
      section(md_of(p), "Commands"))

# b. Any value resolve_config accepts round-trips as one code span.
for val in ("a | b", "echo `date`", "a ``b`` c", "`x`", "`x", "x`",
            "printf '%s' \"$1\"", "pytest @args.txt", "``",
            "cat < in.txt", "pytest -k 'a  b'", "pytest tests/test_*.py",
            "make test 2>&1", "pytest -k a_b"):
    q = '"' + val.replace("\\", "\\\\").replace('"', '\\"') + '"'
    cfg, errs = resolve_config(load_yaml(with_commands(cfg_text(), test=q)))
    if errs:
        check(f"b: {val!r} is accepted by resolve_config", False, errs)
        continue
    got = cfg["commands"]["test"]
    line = command_bullets(md_of({a["path"]: a for a in build_plan(cfg)}))
    spans = code_spans(line.get("Test", ""))
    check(f"b: Test {val!r} renders as exactly one code span holding it",
          spans == [got], (line.get("Test"), spans))

# c. The start-and-land steps, as a numbered list (greenfield only).
def _ind(s):
    return len(s) - len(s.lstrip(" "))


def with_hooks(text, **hooks):
    """`text` with `hooks` (key: bool) added to its hooks block."""
    return text.replace("hooks:\n", "hooks:\n" + "".join(
        f"  {k}: {str(v).lower()}\n" for k, v in hooks.items()), 1)


_LAND_CFGS = {
    "tests": cfg_text(),
    "spec": with_hooks(cfg_text(), test_gate=False),
    "none": with_hooks(cfg_text(), test_gate=False, spec_gate_commit=False),
}
for gate, text in _LAND_CFGS.items():
    cfg, p = plan_of(text)
    wf = section(md_of(p), "Workflow")
    steps = re.findall(r"^(\d+)\. ", wf, re.M)
    check(f"c ({gate}): three numbered steps", steps == ["1", "2", "3"],
          wf)
    fw = flat(wf)
    check(f"c ({gate}): step 1 starts the task, step 2 lands it",
          "1. Starting a task: on a spec branch, set `status: in-progress` "
          "in its task file, commit `.claude/specs/<slug>/` and "
          "`.claude/specs/INDEX.md`, then dispatch it." in fw
          and "2. Landing it: after `VERDICT: approve`, run "
          "`.claude/merge-back.sh <branch>` (Bash timeout 600000 ms), never "
          "a hand `git merge`." in fw, fw)
    from templates import _LANDING_GATES
    check(f"c ({gate}): step 2 carries the gate sentence merge-back runs",
          _LANDING_GATES[gate] in fw, fw)
    check(f"c ({gate}): with no worktree branch, done once approved and "
          f"step 3 skipped",
          "No worktree branch: set `done` once approved, and skip step 3."
          in fw, fw)
    w = fw.find("3. Wait for the script's last line in this turn")
    check(f"c ({gate}): step 3 waits for the script's last line in this "
          f"turn, then acts on that line",
          w >= 0 and "3. Wait for the script's last line in this turn, even "
          "in the background, and commit nothing until then: ending the turn "
          "can stop it. Act on that line:" in fw, fw)
    outs = ("- If the branch merged, set `status: done` and commit it.",
            "- On CONFLICT, invoke the integrator with its brief, then rerun "
            "with `--continue <branch>` and repeat this step.",
            "- Otherwise, do what it names.")
    check(f"c ({gate}): the three outcomes follow the wait, in order",
          all(o in fw for o in outs)
          and w < fw.find(outs[0]) < fw.find(outs[1]) < fw.find(outs[2]),
          fw)
    check(f"c ({gate}): never 'await its notification' (WP3 fix1 CR-1)",
          "await its notification" not in fw, fw)
    # Nested under step 3 (its content column is 3), not a list of their
    # own: flat() above cannot see indentation. Step 3's own continuation
    # lines sit at column 3, an outcome's at column 5.
    _s3 = wf[wf.find("\n3. ") + 1:].split("\n\n", 1)[0].split("\n")[1:]
    _outs = [ln for ln in _s3 if ln.lstrip().startswith("- ")]
    _col, _bad = 3, []
    for ln in _s3:
        if ln.lstrip().startswith("- "):
            _col = 5
            if _ind(ln) != 3:
                _bad.append(ln)
        elif _ind(ln) != _col:
            _bad.append(ln)
    check(f"c ({gate}): the outcomes are nested in step 3, each continuation "
          f"hung under its text",
          len(_outs) == 3 and not _bad, _bad or _s3)

# d. The operator-addressed passages are gone.
for label, (cfg, plan) in PLANS.items():
    fm = flat(md_of(plan))
    check(f"d ({label}): no 'Thin by design', no contract paragraph",
          "Thin by design" not in fm
          and "escalation list is the contract" not in fm
          and "fix steering" not in fm
          and "override in-session" not in fm, fm[:400])

# e. The queue section: wrapped, true for an adopter, the C-2 words kept.
cfg, p = PLANS["all modes, tdd required"]
qs = section(md_of(p), "Queue mode coordination layer")
fq = flat(qs)
check("e: the queue section keeps the C-2 disclosure words",
      "`.claude/auto.sh` is an UNIMPLEMENTED skeleton: as shipped it "
      "dispatches nothing and exits 1." in fq, fq)
from templates import PROTOCOL_DOC
check("e: it names the protocol in a code span and points at the "
      "assumption ledger for where that file lives",
      f"`{PROTOCOL_DOC}`" in fq and "`assumption-ledger.md`" in fq
      and f"({PROTOCOL_DOC} " not in fq, fq)
check("e: every line of it is at most 78 characters",
      qs.strip() and max(len(x) for x in qs.split("\n")) <= 78,
      max(qs.split("\n"), key=len))

# f. (guard) A wrapped line that starts with a block starter (a list marker,
# a heading, a blockquote, a setext underline or a code fence) turns
# paragraph text into that block. Any of them is intended after a blank line
# or a heading. A list marker is also intended as a sibling of the item above
# it (same or shallower indent), or under step 3's "Act on that line:", the
# one intended list introduction (a wrap can end any line with a colon). Row
# g's matrix runs it too, since the PLANS configs carry only the tests gate.
_LIST = re.compile(r"^\s*(\d+[.)] |[-+*] )")
_MARK = re.compile(r"^\s*(\d+[.)] |[-+*] |#{1,6}( |$)|>|(-+|=+)\s*$"
                   r"|`{3,}|~{3,})")


def _bad_starts(md):
    lines = md.split("\n")
    return [ln for prev, ln in zip(lines, lines[1:])
            if _MARK.match(ln)
            and not (not prev.strip() or prev.startswith("#")
                     or (_LIST.match(ln)
                         and (_ind(ln) < _ind(prev)
                              or (_LIST.match(prev)
                                  and _ind(ln) == _ind(prev))
                              or prev.rstrip().endswith(
                                  "Act on that line:"))))]


_F_CASES = (("   - a\n> b", ["> b"]), ("1. a\n## b", ["## b"]),
            ("- a\n  1) b", ["  1) b"]),
            ("   fails:\n   1) the tests", ["   1) the tests"]),
            ("   the command line:\n   - b", ["   - b"]),
            ("   Act on that line:\n   > b", ["   > b"]),
            ("   Act on that line:\n   - If", []))
check("f: the indent, sibling and colon exemptions cover list markers only, "
      "the sibling one only at the same indent, and the colon one only "
      "under its intended line",
      all(_bad_starts(x) == want for x, want in _F_CASES),
      [(x, _bad_starts(x)) for x, want in _F_CASES if _bad_starts(x) != want])
for label, (cfg, plan) in PLANS.items():
    bad = _bad_starts(md_of(plan))
    check(f"f ({label}): no wrapped line starts with a block starter", not bad,
          bad)

# h. (guard) The retrofit CLAUDE.md is byte-identical to 19cd75f's:
# retrofit is backlogged (build plan section 15, the operator's directive).
_RETRO_SHA = {
    ("AGENT_RETROFIT_CFG", True, True):
        "2299535a987cf8586e4a270e641c6a0f7434932944f251076e73004b3a5de339",
    ("AGENT_RETROFIT_CFG", True, False):
        "3cd3dcf1eb17cf2137a3f9ade968c44f3109e9e5a59748a146a9656f9f75a30f",
    ("AGENT_RETROFIT_CFG", False, True):
        "0808db825171073c9d75e106724b29919c4e12d716e3a3c694ae01642dc6c31e",
    ("AGENT_RETROFIT_CFG", False, False):
        "f9581eac35c37b72d8e460d091fbfab0f1cd31cc10899df28ae010833e585fa8",
    ("SERVICE_RETROFIT_CFG", True, True):
        "1882aa7d33a16f35543e760023ac520326783febaad0c500b948e02d0d3a9120",
    ("SERVICE_RETROFIT_CFG", True, False):
        "611ec8aa0ca4704ee3309e0b83764cc7f8cc07bf1daa777684183cad8b64fd5f",
    ("SERVICE_RETROFIT_CFG", False, True):
        "8443e290399ac13ffd445a7d5477fb99ded3e08b4bd012867ca8fb0d24de4596",
    ("SERVICE_RETROFIT_CFG", False, False):
        "5d6ee8c0c0fd57c2a0cbb9982c1277d2addfaaa6aebbb31aa9924197dab1477e",
}
for (_fx, _sec, _deps), _want in _RETRO_SHA.items():
    _, _rp = plan_of(switched(_retrofit_fixture(_fx), _sec, _deps))
    _got = hashlib.sha256(_rp["CLAUDE.md"]["body"].encode()).hexdigest()
    check(f"h: retrofit {_fx} (secrets {_sec}, deps {_deps}): CLAUDE.md is "
          f"byte-identical to 19cd75f's", _got == _want, _got)

# --------------------------------------------------------------------------- #
print("\n=== Thin: CLAUDE.md within budget (PRD Phase 8 step 2) ===")
# g. (guard) The cap is the golden fixtures' (tests/test_merge_back.py) and
# the PRD's "roughly 80 lines max" (operator ruling 2026-10-28). The matrix
# varies the commit gates too, since they choose step 2's gate sentence.
worst = n = 0
fbad = []
for tdd, sec, deps, design, tel, modes, tg, sg in itertools.product(
        ("off", "encouraged", "required"), (True, False), (True, False),
        (True, False), (True, False), (True, False), (True, False),
        (True, False)):
    text = cfg_text(tdd=tdd, sec=sec, deps=deps, design=design, tel=tel,
                    modes=modes, arch="fullstack")
    text = text.replace("hooks:\n", f"hooks:\n  test_gate: {str(tg).lower()}"
                        f"\n  spec_gate_commit: {str(sg).lower()}\n", 1)
    _, p = plan_of(with_commands(text, test='"pytest -q"',
                                 lint='"ruff check ."',
                                 format='"ruff format ."'))
    worst = max(worst, md_of(p).count("\n"))
    fbad += [((tdd, sec, deps, design, tel, modes, tg, sg), ln)
             for ln in _bad_starts(md_of(p))]
    n += 1
check(f"g: CLAUDE.md is at most 80 lines over {n} configs (worst {worst})",
      worst <= 80, worst)
check(f"f: no wrapped line starts with a block starter over the {n} "
      "configs", not fbad, fbad[:3])

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

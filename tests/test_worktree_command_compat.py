#!/usr/bin/env python3
"""W-1 — worktree isolation vs. where the gate commands execute.

Issue #29. Two protocol features that do not automatically compose:

  * Worktree isolation is core drift-prevention machinery (Phase 6.5 states
    the principle, Phase 7 sets `isolation: worktree` on `implementer`, and
    `integrator` exists solely to reconcile conflicting worktrees).
  * Phase 2 collects test/lint/build commands with no constraint on WHERE
    they execute.

The emitted gate runs the configured command bare - no `cd`, no
`$CLAUDE_PROJECT_DIR` - which is correct: a plain `pytest -q` inherits the
hook process's cwd, and inside a worktree that cwd IS the worktree. Plain
commands compose fine. FIXED-MOUNT INDIRECTION is what breaks: `docker
compose exec -T app pytest` lands in a container whose bind mount points at
the main checkout, so the command always runs against `/app` regardless of
cwd. An implementer working in `.claude/worktrees/<n>/` then has its gate
compile and test the MAIN checkout - the gate passes, and the code the agent
wrote was never built. A fail-open in a verification control.

These checks pin the fix in BOTH directions, because both directions can
regress: the default must keep behaving exactly as it did (or every existing
install silently changes), and the no-cwd path must actually drop the
isolation rather than merely warn about it.

Run: python3 tests/test_worktree_command_compat.py
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

from defaults import resolve_config              # noqa: E402
from installer import build_plan                 # noqa: E402
from minyaml import load_yaml                    # noqa: E402
from templates import TEMPLATES                  # noqa: E402
import interview as IV                           # noqa: E402
import retrofit_interview as RIV                 # noqa: E402

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


def cfg_for(**over):
    """A resolved greenfield cfg with every autonomous mode on, so the
    wrapper/queue surfaces are reachable."""
    raw = {
        "project": {"name": "w1-demo", "archetype": "service"},
        "autonomous_modes": {"loop_mode_enabled": True,
                             "goal_supervised_mode_enabled": True,
                             "queue_mode_enabled": True},
        "commands": {"test": "pytest -q", "lint": "ruff check .",
                     "format": "ruff format ."},
    }
    for k, v in over.items():
        if isinstance(v, dict):
            raw.setdefault(k, {}).update(v)
        else:
            raw[k] = v
    cfg, errs = resolve_config(raw)
    return cfg, errs


def bodies(cfg):
    return {a["path"]: a["body"] for a in build_plan(cfg)}


def frontmatter(body):
    """The YAML block between the first two `---` lines."""
    parts = body.split("---\n")
    return parts[1] if len(parts) > 2 else ""


IMPL = ".claude/agents/implementer.md"


# --------------------------------------------------------------------------- #
# 1. Resolution: the derivation table, every cell
# --------------------------------------------------------------------------- #
print("\n== resolution ==")

_c, _e = cfg_for()
check("default (execute_in_cwd unset) resolves to worktree",
      not _e and _c["_implementer_isolation"] == "worktree", str(_e))
check("default emits NO notice (the status quo is not newsworthy)",
      _c["_config_notices"] == [], str(_c["_config_notices"]))
check("default commands.execute_in_cwd is True",
      _c["commands"]["execute_in_cwd"] is True)
check("default workflow.implementer_isolation is 'auto'",
      _c["workflow"]["implementer_isolation"] == "auto")

_c, _e = cfg_for(commands={"execute_in_cwd": False})
check("auto + execute_in_cwd false resolves to none",
      not _e and _c["_implementer_isolation"] == "none", str(_e))
check("auto + false explains itself in a notice",
      any("execute_in_cwd is false" in n for n in _c["_config_notices"]),
      str(_c["_config_notices"]))

_c, _e = cfg_for(commands={"execute_in_cwd": False},
                 workflow={"implementer_isolation": "worktree"})
check("forced worktree overrides a false commands answer",
      not _e and _c["_implementer_isolation"] == "worktree", str(_e))
check("forced worktree over a false answer warns it can report green on "
      "uncompiled code",
      any("never compiled" in n for n in _c["_config_notices"]),
      str(_c["_config_notices"]))

_c, _e = cfg_for(workflow={"implementer_isolation": "none"})
check("forced none overrides a true commands answer",
      not _e and _c["_implementer_isolation"] == "none", str(_e))
check("forced none over a true answer warns about the shared tree",
      any("share one working tree" in n for n in _c["_config_notices"]),
      str(_c["_config_notices"]))

_c, _e = cfg_for(workflow={"implementer_isolation": "wt"})
check("an unknown implementer_isolation value is an ERROR",
      any("implementer_isolation must be one of" in e for e in _e), str(_e))
check("an unknown value still resolves to the safe status quo",
      _c["_implementer_isolation"] == "worktree")

# The truthiness trap: minyaml gives a bool for unquoted true/false, but a
# QUOTED "false" arrives as a non-empty string, which is truthy. Reading that
# as "yes, cwd is honored" would re-arm the exact fail-open the key closes.
_c, _e = cfg_for(commands={"execute_in_cwd": "false"})
check("a QUOTED \"false\" is an ERROR, not silently truthy",
      any("execute_in_cwd must be a boolean" in e for e in _e), str(_e))

# Same, through the real YAML parser rather than a hand-built dict.
_quoted = load_yaml('project:\n  name: q\n  archetype: service\n'
                    'commands:\n  execute_in_cwd: "false"\n')
_, _qe = resolve_config(_quoted)
check("quoted false is caught through minyaml too (not just dict fixtures)",
      any("execute_in_cwd must be a boolean" in e for e in _qe), str(_qe))
_unquoted = load_yaml('project:\n  name: q\n  archetype: service\n'
                      'commands:\n  execute_in_cwd: false\n')
_uc, _ue = resolve_config(_unquoted)
check("unquoted false parses as a bool and resolves to none",
      not _ue and _uc["_implementer_isolation"] == "none", str(_ue))


# --------------------------------------------------------------------------- #
# 2. Emission: worktrees ON (the default; must not have moved)
# --------------------------------------------------------------------------- #
print("\n== emission: isolation on ==")

on_cfg, _ = cfg_for()
on = bodies(on_cfg)
_fm = frontmatter(on[IMPL])
check("ON: implementer frontmatter carries `isolation: worktree`",
      "isolation: worktree\n" in _fm, _fm)
check("ON: frontmatter still carries name/model/description",
      all(k in _fm for k in ("name: implementer", "model: ", "description: ")))
check("ON: body states the requirement the setting rests on",
      "Worktree isolation — the requirement it rests on" in on[IMPL])
check("ON: body names fixed-mount indirection explicitly",
      "docker compose exec" in on[IMPL] and "kubectl exec" in on[IMPL])
check("ON: body gives the operator a probe rather than an assertion",
      "Probe it:" in on[IMPL])
check("ON: queue concurrency stays at the usual 2",
      "max_concurrent_tasks: 2" in on[".claude/queue/backlog.md"]
      and "max_concurrent_tasks: 2" in on[".claude/auto-config.md"])
check("ON: wrappers still route via native --worktree",
      "--worktree" in on[".claude/loop.sh"]
      and "--worktree" in on[".claude/goal-loop.sh"])
check("ON: wrappers warn that the routing assumes cwd is honored",
      "ASSUMES THE GATE COMMANDS FOLLOW cwd" in on[".claude/loop.sh"]
      and "ASSUMES THE GATE COMMANDS FOLLOW cwd" in on[".claude/goal-loop.sh"])
check("ON: integrator is not marked unreachable",
      "Not reachable" not in on[".claude/agents/integrator.md"])
check("ON: tech.md records the execution-location answer",
      "commands.execute_in_cwd: true" in on[".claude/steering/tech.md"])


# --------------------------------------------------------------------------- #
# 3. Emission: worktrees OFF (the fix)
# --------------------------------------------------------------------------- #
print("\n== emission: isolation off ==")

off_cfg, _ = cfg_for(commands={"execute_in_cwd": False})
off = bodies(off_cfg)
_fm = frontmatter(off[IMPL])
check("OFF: implementer frontmatter has NO isolation key at all",
      "isolation:" not in _fm, _fm)
check("OFF: frontmatter is otherwise intact (name/model/description)",
      all(k in _fm for k in ("name: implementer", "model: ", "description: ")))
# The omission must be self-explaining, or the next operator reads it as an
# oversight and "fixes" it straight back into the fail-open.
check("OFF: body records the absence as a DECISION, not an oversight",
      "Worktree isolation is OFF — deliberately" in off[IMPL]
      and "not an oversight" in off[IMPL])
check("OFF: body points at the config key, not at hand-editing the file",
      "workflow.implementer_isolation: worktree" in off[IMPL]
      and "never by hand-editing this file" in off[IMPL])
check("OFF: body warns the hand-edit route freezes the file against "
      "upstream fixes",
      "digest guard" in off[IMPL])
check("OFF: queue concurrency drops to 1 in BOTH queue surfaces",
      "max_concurrent_tasks: 1" in off[".claude/queue/backlog.md"]
      and "max_concurrent_tasks: 1" in off[".claude/auto-config.md"])
check("OFF: the concurrency drop explains itself in-file",
      "concurrent tasks would edit the same working tree"
      in off[".claude/auto-config.md"])
check("OFF: integrator says it is unreachable in this configuration",
      "Not reachable in this project's configuration"
      in off[".claude/agents/integrator.md"])
check("OFF: tech.md records the execution-location answer",
      "commands.execute_in_cwd: false" in off[".claude/steering/tech.md"]
      and "WITHOUT `isolation: worktree`" in off[".claude/steering/tech.md"])

# The wrappers are the OTHER dispatch site with the same fail-open: they tell
# the operator how to write the `claude -p` call. Telling them to pass
# --worktree here would hand them the defect the config just avoided.
for _w in (".claude/loop.sh", ".claude/goal-loop.sh"):
    _b = off[_w]
    check(f"OFF: {_w} tells the operator to dispatch WITHOUT --worktree",
          "Worktree routing is DISABLED" in _b
          and "Dispatch\n# WITHOUT --worktree" in _b, _b[:0])
    check(f"OFF: {_w} stderr hint matches the header (no --worktree)",
          'dispatch WITHOUT --worktree' in _b
          and 'claude -p --worktree' not in _b)
    check(f"OFF: {_w} still keeps the NDJSON stream flags "
          "(usage-limit handling depends on them)",
          "--output-format stream-json --verbose" in _b)
    # IC-6's contract is "no hand-rolled git worktree add", which holds
    # whether or not worktrees are in use.
    _code = "\n".join(l for l in _b.splitlines()
                      if not l.lstrip().startswith("#"))
    check(f"OFF: {_w} still hand-rolls no `git worktree add`",
          "git worktree add" not in _code)

# Nothing outside the four intended surfaces may move between ON and OFF.
_moved = sorted(p for p in on if on[p] != off.get(p))
check("OFF: the blast radius is exactly the intended surfaces",
      _moved == sorted([IMPL, ".claude/agents/integrator.md",
                        ".claude/auto-config.md", ".claude/queue/backlog.md",
                        ".claude/loop.sh", ".claude/goal-loop.sh",
                        ".claude/steering/tech.md"]), str(_moved))
check("OFF: no file is added or removed by the isolation decision",
      sorted(on) == sorted(off))

# Gate bodies are deliberately untouched: running the command bare is the
# CORRECT design (it is what lets a plain command follow cwd at all). The fix
# is upstream of the gate, not inside it.
check("OFF: no gate hook body changes (the bare-command design is correct)",
      all(on[p] == off[p] for p in on if p.startswith(".claude/hooks/")))


# --------------------------------------------------------------------------- #
# 4. Retrofit mode gets the same treatment
# --------------------------------------------------------------------------- #
print("\n== retrofit mode ==")

_rraw = {
    "project": {"name": "w1-retro", "archetype": "service"},
    "mode": "retrofit",
    # R0.8 gate: retrofit refuses to write artifacts until the operator has
    # committed at R0.8 (or explicitly skipped it). Unrelated to W-1, but the
    # cfg does not validate without it.
    "retrofit": {"r08_committed": True},
    "commands": {"test": "make test", "execute_in_cwd": False},
}
rcfg, rerrs = resolve_config(_rraw)
check("retrofit: resolves the isolation the same way",
      not rerrs and rcfg["_implementer_isolation"] == "none", str(rerrs))
rb = bodies(rcfg)
_fm = frontmatter(rb[IMPL])
check("retrofit: implementer frontmatter has no isolation key",
      "isolation:" not in _fm, _fm)
check("retrofit: implementer body carries the OFF explanation",
      "Worktree isolation is OFF — deliberately" in rb[IMPL])
check("retrofit: retrofit-specific instructions survive alongside it",
      "Pin-first discipline (G6)" in rb[IMPL]
      and "legacy allowlist" in rb[IMPL])
# The note is an `##` heading; dropping it between numbered items 4 and 5
# breaks the retrofit body's list. It belongs after the autonomous section.
_rauto = dict(_rraw)
_rauto["retrofit"] = dict(_rraw["retrofit"],
                          autonomous_modes={"loop_mode_opted_in": True,
                                            "goal_supervised_mode_opted_in":
                                            True})
_rac, _rae = resolve_config(_rauto)
_rab = bodies(_rac)[IMPL]
check("retrofit: the numbered instruction list stays contiguous 1..5",
      [m.group(0) for m in re.finditer(r"^\d+\. ", _rab, re.M)]
      == ["1. ", "2. ", "3. ", "4. ", "5. "],
      str(re.findall(r"^\d+\. ", _rab, re.M)))
check("retrofit: the isolation note comes after the autonomous section",
      _rab.index("Autonomous-mode awareness")
      < _rab.index("Worktree isolation is OFF"))
check("retrofit: the worktree-budget item is marked moot when isolation is "
      "off (no self-contradiction in one file)",
      "**Moot in this configuration**" in _rab)

_rraw["commands"]["execute_in_cwd"] = True
rcfg_on, _ = resolve_config(_rraw)
check("retrofit: true answer keeps `isolation: worktree`",
      "isolation: worktree\n" in frontmatter(bodies(rcfg_on)[IMPL]))


# --------------------------------------------------------------------------- #
# 5. Interview front-ends carry the question and round-trip the answer
# --------------------------------------------------------------------------- #
print("\n== interview front-ends ==")

_p = IV.build_proposal("# Demo\nA REST API service for widgets.\n")
_render = IV.render_interview(_p, "PRD.md")
check("greenfield: render carries the section marker",
      IV.COMMANDS_CWD_SECTION_MARKER in _render)
check("greenfield: render carries the verbatim question",
      IV.COMMANDS_CWD_QUESTION in _render)
check("greenfield: ANSWERS block defaults the key true",
      "commands_execute_in_cwd: true" in _render)
_parsed = IV.parse_interview_answers(_render)
check("greenfield: default round-trips as True",
      _parsed["commands_execute_in_cwd"] is True)
_no = _render.replace("commands_execute_in_cwd: true",
                      "commands_execute_in_cwd: false")
check("greenfield: a hand-set false round-trips",
      IV.parse_interview_answers(_no)["commands_execute_in_cwd"] is False)
_ccfg = IV.answers_to_config(IV.parse_interview_answers(_no))
check("greenfield: false reaches commands.execute_in_cwd in the config",
      _ccfg["commands"]["execute_in_cwd"] is False)
_rc, _re = resolve_config(_ccfg)
check("greenfield: that config resolves to none with no errors",
      not _re and _rc["_implementer_isolation"] == "none", str(_re))

# Back-compat: an interview file written before the key existed carries no
# section marker, so it must default to True - which is exactly what it meant
# when it was written. A CURRENT file missing the line is a deletion and must
# fail loud instead.
_old = "\n".join(l for l in _render.split("\n")
                 if "commands_execute_in_cwd" not in l
                 and IV.COMMANDS_CWD_SECTION_TITLE not in l)
check("greenfield back-compat: a pre-key file defaults to True",
      IV.parse_interview_answers(_old)["commands_execute_in_cwd"] is True)
_deleted = "\n".join(l for l in _render.split("\n")
                     if "commands_execute_in_cwd:" not in l)
try:
    IV.parse_interview_answers(_deleted)
    _raised = ""
except ValueError as e:
    _raised = str(e)
check("greenfield: deleting the line from a CURRENT file fails loud",
      "commands_execute_in_cwd" in _raised, _raised)

check("retrofit front-end: has the same section marker constant",
      RIV.COMMANDS_CWD_SECTION_MARKER == "## Command execution location")
check("retrofit front-end: key is in ANSWER_KEYS and typed bool",
      "commands_execute_in_cwd" in RIV.ANSWER_KEYS
      and "commands_execute_in_cwd" in RIV._BOOL_KEYS)


# --------------------------------------------------------------------------- #
# 6. Verbatim pin: the code question == the protocol doc's Phase 2 question
# --------------------------------------------------------------------------- #
print("\n== verbatim pin ==")

with open(os.path.join(ROOT, "Bootstrap-Protocol-v2-6-0.md"),
          encoding="utf-8", newline="") as fh:
    _doc = fh.read().split("\n")
_ql = [l for l in _doc
       if "Question phrasing for command execution location (use verbatim)"
       in l]
check("protocol doc has exactly one command-execution question line",
      len(_ql) == 1, str(len(_ql)))
if _ql:
    _dq = _ql[0][_ql[0].index('*"') + 2: _ql[0].rindex('"*')]
    check("code COMMANDS_CWD_QUESTION == protocol doc (byte-identical)",
          IV.COMMANDS_CWD_QUESTION == _dq,
          f"code={IV.COMMANDS_CWD_QUESTION[:80]!r}\n        doc={_dq[:80]!r}")


# --------------------------------------------------------------------------- #
# 7. End-to-end: a real install refuses nothing and surfaces the note
# --------------------------------------------------------------------------- #
print("\n== end-to-end install ==")

BIN = os.path.join(ROOT, "bin", "bootstrap-install")
_CFG = """project:
  name: w1-e2e
  archetype: service
commands:
  test: "pytest -q"
  lint: "ruff check ."
  format: "ruff format ."
  execute_in_cwd: false
"""
d = tempfile.mkdtemp()
try:
    subprocess.run(["git", "init", "-q", d], check=True)
    with open(os.path.join(d, "cfg.yaml"), "w") as fh:
        fh.write(_CFG)
    r = subprocess.run([sys.executable, BIN, "--config", "cfg.yaml"],
                       cwd=d, capture_output=True, text=True)
    check("e2e: install exits 0 with execute_in_cwd false",
          r.returncode == 0, r.stderr[-600:])
    check("e2e: the operator is TOLD the isolation was dropped",
          "note:" in r.stderr and "execute_in_cwd is false" in r.stderr,
          r.stderr[-600:])
    _impl = os.path.join(d, ".claude", "agents", "implementer.md")
    _body = open(_impl).read()
    check("e2e: the installed implementer.md has no isolation key",
          "isolation:" not in frontmatter(_body), frontmatter(_body))
    check("e2e: the installed implementer.md explains why",
          "Worktree isolation is OFF" in _body)
finally:
    subprocess.run(["rm", "-rf", d])

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

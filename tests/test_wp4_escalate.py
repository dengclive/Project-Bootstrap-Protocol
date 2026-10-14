#!/usr/bin/env python3
"""[WP4 / ruling 7 (c)] The escalate skill: the decision record PRD Phase 8
asks for when the agent stops for an urgent escalation (:1299, backlog
X-30a).

CLAUDE.md marks each urgent escalation with a bell and, after the list, says
to run `/escalate` before stopping for one. The skill writes four fields,
the keys X-30 pinned, to `.claude/sessions/.decision-pending-<session id>`:
the file decision-required-alarm.sh already creates, keeps and sweeps.

What is checked here:
  1. Both files in every golden fixture, and in a retrofit install.
  2. The body: the record path with both substitution tokens, the four keys
     in order, the clock command, the shared write rule, and a read-first
     append through the Edit tool.
  3. The description holds no ": " (a plain YAML scalar may not).
  4. CLAUDE.md's bell-scoped line, the sessions README row and the
     assumption ledger's substitution row.
  5. The binding (verify X14): with a sample session id and project dir
     substituted, the record path is the file the EMITTED alarm creates for
     that id, fired the way tests/test_issue_fixes.py's X-30 section fires
     it; a fire leaves a 0-byte file there, and a four-key record survives a
     fire byte for byte.

Not measurable here: whether a model invokes the skill at a bell stop,
appends without rewriting, or what a worktree implementer's substitution
gives. The live walk covers the first two.

Run: python3 tests/test_wp4_escalate.py
"""
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

from defaults import resolve_config            # noqa: E402
from installer import build_plan               # noqa: E402
from minyaml import load_yaml                  # noqa: E402
import templates                               # noqa: E402

BASH = shutil.which("bash")
SKILL = ".claude/skills/escalate/SKILL.md"
COMMAND = ".claude/commands/escalate.md"
ALARM = ".claude/hooks/decision-required-alarm.sh"
LINE = "Before you stop for a 🔔 item, run `/escalate` to record why."
TOKEN_PATH = ("${CLAUDE_PROJECT_DIR}/.claude/sessions/.decision-pending-"
              "${CLAUDE_SESSION_ID}")

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


def plan_of(text):
    cfg, errs = resolve_config(load_yaml(text))
    assert not errs, errs
    return {a["path"]: a for a in build_plan(cfg)}


def golden_fixture_texts():
    """The seven golden fixtures' config texts, read by ast (never by
    running the suites), as tests/test_merge_back.py reads them."""
    env = {"FIXTURE_DEFAULT": open(os.path.join(
        ROOT, "bootstrap.config.yaml")).read()}
    for f, names in (("test_greenfield_golden.py",
                      ("FIXTURE_FULL_AUTONOMOUS", "FIXTURE_DESIGN_STEERING",
                       "FIXTURE_SDK_CALLABLE", "FIXTURE_GATES_OFF")),
                     ("test_retrofit.py",
                      ("SERVICE_RETROFIT_CFG", "AGENT_RETROFIT_CFG"))):
        path = os.path.join(HERE, f)
        for node in ast.parse(open(path).read()).body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id in names):
                env[node.targets[0].id] = eval(compile(
                    ast.Expression(node.value), path, "eval"), dict(env))
    return env


def description(text):
    """The frontmatter's `description:` value, or None."""
    m = re.search(r"^description: (.*)$", text.split("\n---\n", 1)[0], re.M)
    return m.group(1) if m else None


_FX = golden_fixture_texts()
PLANS = {name: plan_of(text) for name, text in sorted(_FX.items())}
GREENFIELD = [n for n in PLANS if n.startswith("FIXTURE_")]
DEFAULT = PLANS["FIXTURE_DEFAULT"]

# --------------------------------------------------------------------------- #
print("\n=== 1. Both files in every fixture ===")
check("the seven golden fixtures were read", len(PLANS) == 7, sorted(PLANS))
for name, plan in PLANS.items():
    check(f"{name}: plans {SKILL} and {COMMAND}",
          SKILL in plan and COMMAND in plan
          and plan[SKILL]["kind"] == plan[COMMAND]["kind"] == "file",
          sorted(p for p in plan if "escalate" in p))
_rs = PLANS["SERVICE_RETROFIT_CFG"]
check("retrofit: the overlay keeps _skills()'s escalate, byte for byte the "
      "greenfield SKILL.md, and its command",
      SKILL in _rs and COMMAND in _rs
      and _rs[SKILL]["body"] == DEFAULT[SKILL]["body"]
      and _rs[COMMAND]["body"] == DEFAULT[COMMAND]["body"],
      sorted(p for p in _rs if "escalate" in p))

# --------------------------------------------------------------------------- #
print("\n=== 2. The body ===")
body = DEFAULT.get(SKILL, {}).get("body", "")
flat = " ".join(body.split())
check("the record path names both substitution tokens, unsubstituted",
      f"`{TOKEN_PATH}`" in body, body[:400])
check("a path that still shows `${` stops the skill (the guard quotes only "
      "`${`, so Claude Code leaves it alone)",
      "If the path still shows a `${`, stop and tell the operator the "
      "record could not be written." in flat)
_keys = re.findall(r"^\s+(timestamp|reason|about-to|needs): ", body, re.M)
check("the record is X-30's four keys, in order",
      _keys == ["timestamp", "reason", "about-to", "needs"], _keys)
check("the timestamp comes from the clock",
      "`date -u +%Y-%m-%dT%H:%M:%SZ`" in body)
check("the shared write rule (_WRITE_RULE), by reference",
      templates._WRITE_RULE in body)
check("read first with the Read tool, append with the Edit tool through "
      "old_string",
      "Read the file with the Read tool first." in flat
      and "append with the Edit tool" in flat
      and "old_string is the file's last record" in flat
      and "Never use the Write tool on a file that holds a record." in flat,
      flat[:900])
check("the reply carries the four fields, and no earlier record is edited",
      "end your turn with the four fields in your reply" in flat
      and body.rstrip().endswith("Never edit or delete an earlier record."))

# --------------------------------------------------------------------------- #
print("\n=== 3. The description ===")
for path in (SKILL, COMMAND):
    d = description(DEFAULT.get(path, {}).get("body", ""))
    check(f"{path}: a plain description with no \": \"",
          d is not None and ": " not in d and d.startswith(
              "Use before you stop for an urgent escalation marked 🔔"), d)

# --------------------------------------------------------------------------- #
print("\n=== 4. Where the install points at it ===")
_missing = []
for name in GREENFIELD:
    md = PLANS[name]["CLAUDE.md"]["body"]
    urgent = md.split("## Urgent escalations", 1)[-1].split("\n## ", 1)[0]
    last = max((m.end() for m in re.finditer(r"^\d+\. \*\*🔔\*\* .*$", urgent,
                                             re.M)), default=-1)
    if not (md.count(LINE) == 1 and -1 < last < urgent.find(LINE)):
        _missing.append(name)
check(f"greenfield CLAUDE.md: one bell-scoped `/escalate` line, after the "
      f"urgent list ({len(GREENFIELD)} fixtures)",
      not _missing and len(GREENFIELD) == 5, _missing)
_readme = DEFAULT[".claude/sessions/README.md"]["body"]
check("sessions README: `/escalate` writes the record; the alarm creates, "
      "refreshes and sweeps it",
      "| `.decision-pending-<id>` | `/escalate` writes it; the "
      "decision-required alarm creates it, refreshes its mtime and deletes "
      "it after 7 days |" in _readme)
# [WP4 fix round 1 / C9] With hooks.decision_required_alarm false nothing
# creates or sweeps the file, so neither text says the alarm does.
_cfg_text = _FX["FIXTURE_DEFAULT"]
assert "  decision_required_alarm: true\n" in _cfg_text
_noalarm = plan_of(_cfg_text.replace("  decision_required_alarm: true\n",
                                     "  decision_required_alarm: false\n"))
_na_skill = _noalarm.get(SKILL, {}).get("body", "")
_na_readme = _noalarm[".claude/sessions/README.md"]["body"]
check("alarm off: no alarm script, and neither the skill nor the sessions "
      "README says the alarm creates or sweeps the record file",
      ALARM not in _noalarm and _na_skill
      and "decision-required alarm" not in _na_skill
      and "| `.decision-pending-<id>` | `/escalate` writes it |" in _na_readme
      and "decision-required alarm creates" not in _na_readme,
      (_na_skill[:900], [ln for ln in _na_readme.splitlines()
                         if "decision-pending" in ln]))
check("alarm off: step 5 still reads first and creates a missing file with "
      "the Write tool; alarm on, the skill is unchanged",
      "5. Read the file with the Read tool first. If it does not exist, "
      "create it with the Write tool." in " ".join(_na_skill.split())
      and "the decision-required alarm creates it on any permission prompt"
      in " ".join(body.split()), _na_skill[:900])
_ledger = DEFAULT[".claude/steering/assumption-ledger.md"]["body"]
_row = next((ln for ln in _ledger.splitlines()
             if ln.startswith("| Skill-body substitution")), "")
check("assumption ledger: a skill-body substitution row, measured on "
      "2.1.288, re-validated on a Claude Code upgrade",
      "`${CLAUDE_SESSION_ID}`" in _row and "`${CLAUDE_PROJECT_DIR}`" in _row
      and "2.1.288" in _row and _row.endswith("| Any Claude Code upgrade |"),
      _row)

# --------------------------------------------------------------------------- #
print("\n=== 5. The binding (X14): the record path is the alarm's file ===")
SID = "4f6a2c1e-8b3d-4e5f-9a7b-1c2d3e4f5a6b"   # a Claude Code session id form
FOUR_FIELDS = ("timestamp: 2026-10-14T09:12:09Z\n"
               "reason: a Do Not Touch path needs a change (src/billing/)\n"
               "about-to: edit src/billing/rates.py for AC-3\n"
               "needs: the operator's approval to change it\n")
if not BASH:
    check("bash is on PATH (the binding rows fire the emitted alarm)", False)
else:
    tmp = tempfile.mkdtemp(prefix="wp4-escalate-")
    try:
        proj = os.path.join(tmp, "proj")
        hooks = os.path.join(proj, ".claude", "hooks")
        sessions = os.path.join(proj, ".claude", "sessions")
        os.makedirs(hooks)
        alarm = os.path.join(hooks, "decision-required-alarm.sh")
        with open(alarm, "w", encoding="utf-8") as fh:
            fh.write(DEFAULT[ALARM]["body"])
        m = re.search(r"`(\$\{CLAUDE_PROJECT_DIR\}/[^`\s]*"
                      r"\$\{CLAUDE_SESSION_ID\})`", body)
        record = (m.group(1).replace("${CLAUDE_PROJECT_DIR}", proj)
                  .replace("${CLAUDE_SESSION_ID}", SID) if m else None)

        def fire(sid):
            """Fire the emitted alarm as test_issue_fixes.py's X-30
            alarm_fire does: a Notification payload on stdin, and
            CLAUDE_PROJECT_DIR set to the project."""
            e = dict(os.environ)
            e["CLAUDE_PROJECT_DIR"] = proj
            return subprocess.run(
                [BASH, alarm], input=json.dumps(
                    {"session_id": sid, "message": "need input"}),
                capture_output=True, text=True, env=e, cwd=proj)

        before = (set(os.listdir(sessions)) if os.path.isdir(sessions)
                  else set())
        r = fire(SID)
        made = sorted(os.path.join(sessions, f)
                      for f in set(os.listdir(sessions)) - before)
        check("binding: with the id and dir substituted, the record path is "
              "the one file the emitted alarm creates for that session",
              r.returncode == 0 and record is not None
              and made == [record], (r.returncode, record, made,
                                     r.stderr[-300:]))
        check("a fire with no file leaves a 0-byte file at that path",
              record is not None and os.path.isfile(record)
              and os.path.getsize(record) == 0)
        if record is not None:
            with open(record, "w", encoding="utf-8") as fh:
                fh.write(FOUR_FIELDS)
        r2 = fire(SID)
        got = (open(record, encoding="utf-8").read()
               if record is not None and os.path.isfile(record) else None)
        check("a four-key record survives a fire byte for byte",
              r2.returncode == 0 and got == FOUR_FIELDS,
              (r2.returncode, got))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

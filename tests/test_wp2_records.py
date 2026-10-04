#!/usr/bin/env python3
"""[WP2 review RC-2, RC-3, RC-6] WP2's records say what the code does.

Each row DERIVES the fact from the code (or runs the emitted hook), then
checks the record that states it. A record that drifts from the code fails
here, not in the next review.

  - RC-3: decision-required-alarm's `Notification` matcher and its retired
    match-all site. The PRD's two "input idle" lines must carry a dated WP2
    correction naming the matcher HOOK_EVENT_MAP actually registers.
  - RC-2: the drift ack rule. The emitted hook sets each threshold to
    max(threshold, signal at the ack) + ceil(configured / 2), and restarts
    the duration and read counters at a checkpoint. The hook is run to show
    both (including an ack BEFORE the threshold, the case "+50% of each
    threshold" cannot tell apart); then no record may carry the refuted
    "+50% of each threshold" wording, and each must state the rule.
  - RC-6: lib/defaults.py's empty-command comment named a `true` run that
    format-lint-gate no longer emits.
  - TD-2, TD-3, TD-4, RR-UP-1, RR-UP-2, RC-1: the tracked records (the
    changelog's WP2 entry, the backlog's WP2 rows in section Z, and the seam
    contract's dated WP2 appends) say what the shipped code does.

Run: python3 tests/test_wp2_records.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import templates  # noqa: E402

INSTALL = os.path.join(ROOT, "bin", "bootstrap-install")
BASH = shutil.which("bash")
PRD = os.path.join(ROOT, "Bootstrap-Protocol-v2-8-0.md")

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


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def anchored_line(lines, prefix):
    """The ONE line starting with prefix, or None (zero or several)."""
    hits = [ln for ln in lines if ln.startswith(prefix)]
    return hits[0] if len(hits) == 1 else None


# --------------------------------------------------------------------------- #
# RC-3: decision-required-alarm's matcher, as the PRD records it
# --------------------------------------------------------------------------- #
_ev, _matcher = templates.HOOK_EVENT_MAP["decision-required-alarm"]
check("RC-3: decision-required-alarm is a Notification hook with a matcher",
      _ev == "Notification" and bool(_matcher), repr((_ev, _matcher)))
check("RC-3: its match-all Notification site is retired",
      ("Notification", None)
      in templates.HOOK_RETIRED_SITES.get("decision-required-alarm", []),
      repr(templates.HOOK_RETIRED_SITES.get("decision-required-alarm")))
_prd_lines = read("Bootstrap-Protocol-v2-8-0.md").split("\n")
for _label, _prefix in (
        ("phase-7 hook list",
         '   - **Decision-required alarm** (all) — soft notice (does not '
         'block). `Notification` hook (Claude Code\'s built-in event for '
         '"input idle"'),
        ("6.E wiring",
         'Wired as a `Notification` hook (Claude Code\'s built-in event for '
         '"input idle"')):
    _ln = anchored_line(_prd_lines, _prefix)
    check(f"RC-3: the PRD's {_label} line is unique", _ln is not None)
    _ln = _ln or ""
    _tail = _ln.split("**[Corrected 2026-10-03, WP2.]**", 1)
    check(f"RC-3: the PRD's {_label} line carries a dated WP2 correction "
          f"naming the registered matcher and the retired site",
          len(_tail) == 2 and f"`{_matcher}`" in _tail[1]
          and "idle_prompt" in _tail[1]
          and "HOOK_RETIRED_SITES" in _tail[1], _ln[-400:])


# --------------------------------------------------------------------------- #
# RC-2: the drift ack rule, run, then read in every record
# --------------------------------------------------------------------------- #
TC, FR = 4, 3
TMP = tempfile.mkdtemp(prefix="wp2-records-")
try:
    if not BASH:
        print("bash not found; the drift rows cannot run")
        failed += 1
    else:
        PROJ = os.path.join(TMP, "proj")
        os.makedirs(PROJ)
        cfg = os.path.join(TMP, "config.yaml")
        with open(cfg, "w", encoding="utf-8") as fh:
            fh.write(f"""project:
  name: "records"
  archetype: "fullstack"
  shell: "bash"
  prd_tier: "standard"
  cicd_opt_out: false
commands:
  test: "true"
  lint: "true"
  format: "true"
  ci_local: "true"
hooks:
  drift_tool_call_threshold: {TC}
  drift_session_duration_minutes: 120
  drift_file_read_threshold: {FR}
""")
        r = subprocess.run([sys.executable, INSTALL, "-c", cfg, "-C", PROJ],
                           capture_output=True, text=True)
        check("drift fixture installs", r.returncode == 0, r.stderr[-800:])
        S = os.path.join(PROJ, ".claude", "sessions")
        os.makedirs(S, exist_ok=True)
        HOOK = os.path.join(PROJ, ".claude", "hooks", "drift-detector.sh")
        env = dict(os.environ, CLAUDE_PROJECT_DIR=PROJ)

        def drift(sid, tool="Bash", **ti):
            p = subprocess.run(
                [BASH, HOOK], input=json.dumps(
                    {"session_id": sid, "tool_name": tool,
                     "tool_input": ti or {"command": "ls"}}),
                capture_output=True, text=True, env=env, cwd=PROJ,
                timeout=60)
            return p.returncode, p.stdout

        def ack(sid):
            with open(os.path.join(S, ".drift-ack-" + sid), "w") as fh:
                fh.write("1\n")

        def fires(sid, calls, ack_before=()):
            out = []
            for i in range(1, calls + 1):
                if i in ack_before:
                    ack(sid)
                rc, o = drift(sid)
                if rc != 0:
                    return f"rc={rc} at call {i}"
                if o.strip():
                    out.append(i)
            return out

        half = (TC + 1) // 2
        # Ack BEFORE the threshold: max(4, 2) + 2 = 6. "+50% of each
        # threshold" would also say 6 here, but "signal + 50%" would say 4.
        got = fires("r-early", 9, ack_before=(2,))
        check("RC-2: an ack below the threshold re-arms at "
              "max(threshold, signal) + ceil(threshold/2)",
              got == [max(TC, 2) + half], got)
        # Ack AFTER the fire, at call 7: max(4, 7) + 2 = 9, where "+50% of
        # each threshold" (4 + 2 = 6) would have fired at once.
        got = fires("r-late", 12, ack_before=(7,))
        check("RC-2: an ack above the threshold re-arms at "
              "max(threshold, signal) + ceil(threshold/2), not at "
              "threshold * 1.5",
              got == [TC, max(TC, 7) + half], got)

        # Reads restart at a checkpoint: FR reads, a checkpoint, one more.
        sid = "r-reads"
        for _ in range(FR):
            drift(sid, "Read", file_path="/x/a.py")
        drift(sid, "Write", file_path=os.path.join(
            S, "2026-10-03T1200Z-checkpoint.md"), content="x")
        rc, o = drift(sid, "Read", file_path="/x/a.py")
        check("RC-2: the read counter restarts at a checkpoint",
              rc == 0 and "a.py read" not in o, o[:300])
        # Duration restarts at a checkpoint: a session started 200 min ago.
        sid = "r-dur"
        with open(os.path.join(S, ".session-" + sid), "w") as fh:
            fh.write(f"{int(time.time()) - 200 * 60}\n")
        rc, o = drift(sid)
        check("RC-2: duration counts from the session start file",
              rc == 0 and "minutes since" in o, o[:300])
        drift(sid, "Write", file_path=".claude/sessions/z-checkpoint.md",
              content="x")
        with open(os.path.join(S, ".drift-state-" + sid)) as fh:
            st = fh.read().split()
        check("RC-2: duration restarts at a checkpoint (base = the "
              "checkpoint, not the session start)",
              len(st) == 6 and int(st[2]) >= int(time.time()) - 60, st)
finally:
    shutil.rmtree(TMP, ignore_errors=True)

_REFUTED = "+50% of each threshold"
_RULE = "value at the ack, plus half the configured threshold"
# lib/templates.py holds the emitted audio-alerts.config CORRECTION text.
for _rel in ("Bootstrap-Protocol-v2-8-0.md", "README.md", "lib/templates.py"):
    # Flattened first: a comment wraps the phrase across a `# ` line break.
    _flat = " ".join(read(_rel).replace("#", " ").split())
    check(f"RC-2: {_rel} no longer says '{_REFUTED}'",
          _REFUTED not in _flat, _rel)
    check(f"RC-2: {_rel} states the ack rule ('...{_RULE}')",
          _RULE in _flat, _rel)


# --------------------------------------------------------------------------- #
# RC-6: defaults.py's empty-command comment
# --------------------------------------------------------------------------- #
_d = read("lib/defaults.py")
_i = _d.find("# ---- Warn-not-fail: empty commands")
_block = _d[_i:_d.find('cmds = cfg["commands"]', _i)] if _i >= 0 else ""
check("RC-6: the empty-command comment block is found", bool(_block))
check("RC-6: it no longer says format-lint-gate runs `true`",
      "`true`" not in _block, _block)
check("RC-6: it names the notice format-lint-gate prints instead",
      "LINT_UNSET_NOTICE" in _block, _block)

# --------------------------------------------------------------------------- #
# RR-UP-2: the HOOK_EVENT_MAP comment claims only what the matcher covers
# --------------------------------------------------------------------------- #
# The hooks reference's Notification types that wait on the operator but are
# NOT in the matcher (fetched 2026-10-04; recorded as a residual).
_UNMATCHED_WAITS = ("elicitation_url_dialog", "agent_needs_input",
                    "quota_auto_resume_stale")
_t = read("lib/templates.py")
_j = _t.find('    "decision-required-alarm": ("Notification",')
_k = _t.rfind('\n    "task-done-alarm":', 0, _j)
_cmt = " ".join(_t[_k:_j].replace("#", " ").split()) if 0 <= _k < _j else ""
check("RR-UP-2: the decision-required-alarm comment block is found",
      bool(_cmt))
check("RR-UP-2: it no longer says the matcher takes every notification "
      "the operator must act on",
      "Only the notifications" not in _cmt, _cmt)
check("RR-UP-2: it names each type the matcher registers",
      all(m in _cmt for m in _matcher.split("|")), _cmt)
check("RR-UP-2: it names the operator-wait types the matcher omits",
      all(u in _cmt and u not in _matcher.split("|")
          for u in _UNMATCHED_WAITS), _cmt)


# --------------------------------------------------------------------------- #
# TD-2, TD-3, TD-4, RR-UP-1, RR-UP-2: the tracked records
# --------------------------------------------------------------------------- #
# These rows read the records step 9 wrote from the (gitignored) pending
# draft: the changelog's WP2 entry and the backlog's WP2 rows in section Z.
# Both files are tracked, so the rows run everywhere, CI included
# (RR-UP-1 pins the c642731 test list, because CI's checkout is shallow).
import fnmatch  # noqa: E402
import re  # noqa: E402
import sdk_gates_template as _sg  # noqa: E402


def _flat(text):
    # Table cells escape a literal `|` as `\|`; read it back as `|`.
    return " ".join(text.replace("\\|", "|").split())


def _cut(flat, start, end):
    i = flat.find(start)
    j = flat.find(end, i + len(start)) if i >= 0 else -1
    return flat[i:j] if 0 <= i < j else ""


_cl = _cut(_flat(read("docs/changelog.md")),
           "## Post-2.8.0 — hooks that reach the model (WP2)",
           "## Post-2.8.0 — a clean gates-off install (WP1)")
_bl = _flat(read("docs/deferred-backlog.md"))
check("records: the changelog's WP2 entry is found", bool(_cl))

# TD-2: the changelog tdd-gate bullet names the shipped set exactly.
_tdd = _cut(_cl, "- **tdd-gate (build-plan blocker 5).**",
            "**The timeout split")
_js = _sg._TDD_JS_EXTS
_named = [g for g in _sg.TDD_TEST_BASENAMES
          if not g.startswith(("*.test.", "*.spec."))]
_named += [g for g in _sg.TDD_TEST_DIRS
           if g not in ("[Tt]est", "[Tt]ests")]
_named += ["[Tt]est", "[Tt]ests", "testFixtures", "*.test.E",
           "*.spec.E"] + [f"`{e}`" for e in _js]
check("TD-2: the changelog tdd-gate bullet is found", bool(_tdd))
check("TD-2: it names every TDD_TEST_* rule",
      all(n in _tdd for n in _named),
      [n for n in _named if n not in _tdd])
check("TD-2: the JS/TS extension list in the record is the shipped one",
      len(_js) == 8 and set(_sg.TDD_TEST_BASENAMES) >= {
          f"*.{k}.{e}" for k in ("test", "spec") for e in _js})
check("TD-2: it no longer claims bare `*.test.*` / `*.spec.*` are "
      "exempt", "`*.test.*`" not in _tdd and "`*.spec.*`" not in _tdd,
      _tdd[:300])
_carve = ("*.spec.json", "*.spec.yaml", "*.test.py")
check("TD-2: each carve-out it names as gated IS gated by the set",
      all(c in _tdd and not any(
          fnmatch.fnmatchcase(c.replace("*", "qz"), g)
          for g in _sg.TDD_TEST_BASENAMES) for c in _carve))

# TD-2: the §8.4 walk's sentinel row names every per-session entry the
# drift hooks write (derived from the emitted bodies).
_names = set(re.findall(r'\$S/(\.(?:drift-[a-z]+|session))-\$', _t))
_seam = _cut(_cl, "| Shared sentinel names/locations/scope (§7.4) |",
             "| §7.2 security-critical")
check("TD-2: drift hooks write at least five per-session entries",
      len(_names) >= 5, sorted(_names))
check("TD-2: the seam sentinel row names each of them",
      bool(_seam) and all(f"`{n}-<sid>`" in _seam for n in _names),
      [n for n in sorted(_names) if f"`{n}-<sid>`" not in _seam])

# RR-UP-1: every test file new since c642731 is named in the entry. The
# c642731 list is pinned here, not read with `git ls-tree c642731`: CI's
# checkout is shallow and does not have that commit. New files are taken
# from `git ls-files`, so an untracked local test file does not count.
_OLD_TESTS = {
    "test_advisor_model.py", "test_auto_run_sentinel.py",
    "test_composition.py", "test_doc_citations.py",
    "test_dynamic_workflow_policy.py", "test_gate_substrate.py",
    "test_goal_evaluator_keys.py", "test_greenfield_golden.py",
    "test_hook_behavior.py", "test_hook_tiers.py", "test_ic_gate.py",
    "test_installer.py", "test_interview.py", "test_issue_fixes.py",
    "test_retrofit.py", "test_root_sentinels.py", "test_sdk_gates.py",
    "test_settings_merge.py", "test_substrate_differential.py",
    "test_trust_ramp.py", "test_usage_limit_contract.py",
    "test_validate_only.py", "test_wiring_verification.py",
    "test_worktree_command_compat.py", "test_wrapper_behavior.py",
}
_tracked = subprocess.run(
    ["git", "-C", ROOT, "ls-files", "tests/"],
    capture_output=True, text=True).stdout.split()
_new = sorted(f for f in _tracked
              if os.path.basename(f).startswith("test_")
              and f.endswith(".py") and f.count("/") == 1
              and os.path.basename(f) not in _OLD_TESTS)
_tests = _cl[_cl.find("**Tests.**"):] if "**Tests.**" in _cl else ""
check("RR-UP-1: git lists the tests and the new test files exist",
      len(_tracked) > 25 and len(_new) >= 7, (len(_tracked), _new))
check("RR-UP-1: the changelog entry names every new test file",
      bool(_tests) and all(f"`{f}`" in _tests for f in _new),
      [f for f in _new if f"`{f}`" not in _tests])

# TD-3 / TD-4: each residual example is classified as the record says,
# by the shipped _tdd_is_test_path (its source, cut from the template;
# tests/test_substrate_differential.py runs the same examples through
# both full gates).
_src = read("lib/sdk_gates_template.py")
_m = re.search(r"\ndef _tdd_is_test_path\(rel\):\n.*?\n\n\n", _src, re.S)
_ns = {"fnmatch": fnmatch,
       "_TDD_TEST_BASENAMES": _sg.TDD_TEST_BASENAMES,
       "_TDD_TEST_DIRS": _sg.TDD_TEST_DIRS,
       "_TDD_TEST_SOURCE_SETS": _sg.TDD_TEST_SOURCE_SETS}
check("TD-3/TD-4: the shipped _tdd_is_test_path is found", bool(_m))
if _m:
    exec(_m.group(0), _ns)
_exempt = _ns.get("_tdd_is_test_path", lambda rel: None)

for _rid, _head, _end, _want in (
        ("TD-3", "| Z-15 | tdd-gate over-exemption (re-review TD-3)",
         "| Z-16 |", True),
        ("TD-4", "| Z-16 | tdd-gate under-exemption (re-review TD-4)",
         "| Z-17 |", False)):
    _row = _cut(_bl, _head, _end)
    _ex = [p for p in re.findall(r"`((?:src|lib)/[^`]+)`", _row)
           if p != "src/core.py" and not p.endswith("/")]
    check(f"{_rid}: the backlog residual row is recorded with examples",
          len(_ex) >= 7, _ex)
    check(f"{_rid}: each example is {'exempt' if _want else 'gated'} "
          f"under the shipped set",
          all(_exempt(p) is _want for p in _ex),
          [p for p in _ex if _exempt(p) is not _want])

# RC-1: the §8.4 walk's §7.3 row FIRES for the new ANSWERS key, and the
# seam's §7.3 WP1 bullet carries the dated WP2 append naming it. The key is
# derived from both interviews' key lists.
import interview as _iv  # noqa: E402
import retrofit_interview as _riv  # noqa: E402
_newkeys = [k for k in ("commands_eval",)
            if k in _iv.ANSWER_KEYS and k in _riv.ANSWER_KEYS]
_r73 = _cut(_cl, "| §7.3 provenance markers / synthesize-file contract |",
            "| `binds` set")
check("RC-1: both interviews carry the commands_eval ANSWERS key",
      _newkeys == ["commands_eval"])
check("RC-1: the walk's §7.3 row reads Fires and names the key",
      _r73.startswith("| §7.3 provenance markers / synthesize-file "
                      "contract | **Fires** |")
      and all(f"`{k}`" in _r73 for k in _newkeys), _r73[:200])
_seam73 = anchored_line(read("SEAM-CONTRACT-v3-0-0.md").split("\n"),
                        "- **[seam 3.0.0, WP1] The synthesize-file contract "
                        "changed — a §8.4 trigger.**") or ""
_wp2 = _seam73.split("WP2 / D9 — a §8.4 trigger (§7.3)", 1)
check("RC-1: the seam's §7.3 bullet carries the dated WP2 append",
      len(_wp2) == 2 and all(f"`{k}`" in _wp2[1] for k in _newkeys),
      _seam73[-300:])

# RR-UP-2: the matcher residual names every unmatched operator-wait type.
_mrow = _cut(_bl, "| Z-17 | decision-required-alarm matcher coverage",
             "| Z-18 |")
check("RR-UP-2: the backlog matcher residual row is recorded",
      bool(_mrow) and f"`{_matcher}`" in _mrow)
# The sentence that names the omitted types, not the full type list.
_omit = _cut(_mrow, "wait on the operator and do not fire the alarm",
             "Options:")
check("RR-UP-2: it names each operator-wait type the matcher omits",
      bool(_omit) and all(f"`{u}`" in _omit for u in _UNMATCHED_WAITS)
      and not any(f"`{m}`" in _omit for m in _matcher.split("|")),
      _omit[:300])

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

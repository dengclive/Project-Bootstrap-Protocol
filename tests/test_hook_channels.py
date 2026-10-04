#!/usr/bin/env python3
"""[WP2 channels] Every advisory hook's message reaches its reader.

Claude Code sends a hook's exit-0 stderr to its debug log and nowhere else,
so spec-gate-entry, format-lint-gate, drift-detector-loop-cooperation, the
two alarms and iteration-summary-enforcement's degrade notice reached nobody.
Each now prints ONE JSON object on stdout, on the field its event delivers
to the intended reader:

  - additionalContext (the model): spec-gate-entry (UserPromptSubmit),
    format-lint-gate on a FAILING lint (PostToolUse), loop cooperation
    (PostToolUse, once per tier-3 sentinel per session);
  - terminalSequence (the operator's terminal, OSC 9): task-done-alarm
    (SubagentStop) and decision-required-alarm (Notification, which now
    matches only permission_prompt|elicitation_dialog);
  - systemMessage (the user): format-lint-gate with commands.lint empty
    (I-6(a)) and iteration-summary-enforcement's parser degrade (Stop, where
    additionalContext would continue the turn; rows in
    test_wrapper_behavior).

spec-gate-entry's keyword match is case-insensitive without the locale
(two-member brackets); the tr_TR.UTF-8 row is the only pin on that, so a
shape pin backs it up where the locale cannot be built.

Shell == SDK for format-lint-gate is pinned in
tests/test_substrate_differential.py; the retrofit warn-only lines in
tests/test_retrofit.py.

Run: python3 tests/test_hook_channels.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

import templates  # noqa: E402
from installer import _merge_hooks  # noqa: E402
from sdk_gates_template import (LINT_CONTEXT_MAX,  # noqa: E402
                                LINT_UNSET_NOTICE)

INSTALL = os.path.join(ROOT, "bin", "bootstrap-install")
BASH = shutil.which("bash")

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


def _obj(out):
    """The ONE JSON object on stdout, or None (a regression reads FAIL)."""
    try:
        d = json.loads(out)
    except (ValueError, TypeError):
        return None
    return d if isinstance(d, dict) else None


def _ctx(out, event):
    d = _obj(out) or {}
    h = d.get("hookSpecificOutput") or {}
    if list(d) != ["hookSpecificOutput"] or h.get("hookEventName") != event:
        return None
    return h.get("additionalContext")


# --------------------------------------------------------------------------- #
print("\n== [WP2] the printf'd JSON constants are safe inside printf '...' ==")
# Each is emitted as `printf '%s\n' '<json>'`: a ' would end the quoted word.
# The %s format keeps a % inert today, but the helpers refuse it too, so a
# constant can move into a FORMAT position without becoming a directive.
_consts = {n: v for n, v in vars(templates).items()
           if n.endswith("_JSON") and isinstance(v, str)}
for _n in ("_SPEC_ENTRY_JSON", "_LOOP_COOP_JSON", "_TASK_DONE_JSON",
           "_DECISION_JSON", "_ITER_DEGRADE_JSON", "_LINT_UNSET_JSON"):
    check(f"templates.{_n} exists", _n in _consts)
for _n, _v in sorted(_consts.items()):
    check(f"templates.{_n} holds no ' and no %",
          "'" not in _v and "%" not in _v, _v[:120])
    check(f"templates.{_n} is one JSON object", _obj(_v) is not None, _v[:120])
check("_LINT_UNSET_JSON carries the shared LINT_UNSET_NOTICE",
      _obj(templates._LINT_UNSET_JSON) == {"systemMessage": LINT_UNSET_NOTICE})
for _bad in ("it's", "100%"):
    try:
        templates._sysmsg_json(_bad)
        _ok = False
    except AssertionError:
        _ok = True
    check(f"_sysmsg_json refuses {_bad!r}", _ok)

print("\n== [WP2] spec-gate-entry's keyword arm ==")
check("the case arm is the four keywords as two-member brackets",
      templates._SPEC_KW_CASE ==
      "*[Ww][Rr][Ii][Tt][Ee]*|*[Ee][Dd][Ii][Tt]*|*[Cc][Rr][Ee][Aa][Tt][Ee]*|"
      "*[Ii][Mm][Pp][Ll][Ee][Mm][Ee][Nn][Tt]*", templates._SPEC_KW_CASE)
for _bad in (("Write",), ("wr1te",), ("é",)):
    try:
        templates._ci_case_globs(_bad)
        _ok = False
    except AssertionError:
        _ok = True
    check(f"_ci_case_globs refuses {_bad[0]!r} (not lowercase ASCII)", _ok)

if not BASH:
    print("bash not found; the behavioural rows cannot run")
    print(f"\n{passed} passed, {failed + 1} failed")
    sys.exit(1)

TMP = tempfile.mkdtemp(prefix="hook-channels-")
LINT_SH = os.path.join(TMP, "lint.sh")
LINT_OUT = os.path.join(TMP, "lint.out")
BASE = """project:
  name: "channels"
  archetype: "ai-agent"
  shell: "bash"
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: false
commands:
  test: "true"
"""


def _install(name, lint_line):
    proj = os.path.join(TMP, name)
    os.makedirs(proj)
    cfg = os.path.join(TMP, name + ".yaml")
    with open(cfg, "w", encoding="utf-8") as fh:
        fh.write(BASE + lint_line)
    r = subprocess.run([sys.executable, INSTALL, "-c", cfg, "-C", proj],
                       capture_output=True, text=True)
    check(f"the {name} tree installs", r.returncode == 0,
          (r.stdout + r.stderr)[-300:])
    return proj


def run(proj, hook, payload, env=None, path=None):
    e = dict(os.environ)
    e["CLAUDE_PROJECT_DIR"] = proj
    if path:
        e["PATH"] = path
    if env:
        e.update(env)
    if not isinstance(payload, (str, bytes)):
        payload = json.dumps(payload)
    if isinstance(payload, str):
        payload = payload.encode()
    p = subprocess.run([BASH, os.path.join(proj, ".claude", "hooks",
                                           hook + ".sh")],
                       input=payload, capture_output=True, env=e, cwd=proj)
    return (p.returncode, p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


# A PATH with neither jq nor python3 (a symlink farm: `command -v` cannot be
# fooled by shadowing). The JSON these hooks WRITE needs neither.
_NOPARSER = os.path.join(TMP, "noparser")
os.makedirs(_NOPARSER)
for _b in ("bash", "cat", "date", "mkdir", "dirname", "basename", "mktemp",
           "grep", "rm", "sed", "tr", "find", "git", "sort", "head", "tail",
           "wc", "env", "sh", "touch", "cut", "awk", "xargs", "ls", "mv"):
    _w = shutil.which(_b)
    if _w:
        os.symlink(_w, os.path.join(_NOPARSER, _b))

try:
    P = _install("lint", f'  lint: "sh {LINT_SH}"\n')
    P_EMPTY = _install("nolint", "")
    P_BLANK = _install("blanklint", '  lint: "   "\n')
    POST = {"session_id": "s", "hook_event_name": "PostToolUse",
            "tool_name": "Edit", "tool_input": {"file_path": "x.py"}}

    # ----------------------------------------------------------------------- #
    print("\n== spec-gate-entry: case-insensitive, to the model ==")
    _want = templates.SPEC_ENTRY_NOTICE
    for _p in ("Implement the parser", "IMPLEMENT the parser", "Write a test",
               "WRITE it", "Edit the config", "EDIT", "Create the module",
               "CREATE", "wRiTe", "first line\nNow Implement it"):
        for _loc in ("C", "C.UTF-8"):
            rc, out, err = run(P, "spec-gate-entry", {"prompt": _p},
                               env={"LC_ALL": _loc})
            check(f"spec-gate-entry fires on {_p!r} under {_loc}",
                  rc == 0 and _ctx(out, "UserPromptSubmit") == _want
                  and err == "", repr((rc, out[:200], err[:200])))
    rc, out, err = run(P, "spec-gate-entry", {"prompt": "please write it"})
    check("spec-gate-entry still fires on a lowercase keyword",
          rc == 0 and _ctx(out, "UserPromptSubmit") == _want,
          repr((rc, out[:200])))
    rc, out, err = run(P, "spec-gate-entry", {"prompt": "Summarize the README"})
    check("spec-gate-entry is silent on a prompt with no keyword",
          rc == 0 and out == "" and err == "", repr((rc, out, err)))
    # The LOCALE row: under tr_TR.UTF-8 `shopt -s nocasematch` and `${P,,}`
    # fold `I` through the locale, so either "fix" stays silent on
    # "IMPLEMENT". Built privately (LOCPATH) when localedef can.
    _loc = os.path.join(TMP, "locales")
    os.makedirs(_loc)
    _ld = shutil.which("localedef")
    _ok = bool(_ld) and subprocess.run(
        [_ld, "-i", "tr_TR", "-f", "UTF-8",
         os.path.join(_loc, "tr_TR.UTF-8")],
        capture_output=True).returncode in (0, 1) \
        and os.path.isdir(os.path.join(_loc, "tr_TR.UTF-8"))
    if _ok:
        for _p in ("IMPLEMENT it", "WRITE it", "EDIT it", "Implement it"):
            rc, out, err = run(P, "spec-gate-entry", {"prompt": _p},
                               env={"LOCPATH": _loc, "LC_ALL": "tr_TR.UTF-8"})
            check(f"spec-gate-entry fires on {_p!r} under tr_TR.UTF-8",
                  rc == 0 and _ctx(out, "UserPromptSubmit") == _want,
                  repr((rc, out[:200], err[:200])))
    else:
        print("  NOTE  tr_TR.UTF-8 not buildable here; the locale rows did "
              "not run (the shape pin below still did)")
    # Shape pin, the backup where the locale cannot be built: no fold that
    # goes through the locale, anywhere in the emitted hook.
    _sge = open(os.path.join(P, ".claude", "hooks", "spec-gate-entry.sh"),
                encoding="utf-8").read()
    _code = "\n".join(ln for ln in _sge.splitlines()
                      if not ln.lstrip().startswith("#"))
    check("spec-gate-entry's code has no nocasematch, ${x,,} or ${x^^}",
          "nocasematch" not in _code and ",," not in _code
          and "^^" not in _code)
    check("spec-gate-entry's case line is the bracket arm",
          ("  " + templates._SPEC_KW_CASE + ")") in _code.splitlines())

    # ----------------------------------------------------------------------- #
    print("\n== format-lint-gate: a failing lint reaches the model ==")

    def lint(data, rc, path=None, proj=None):
        with open(LINT_OUT, "wb") as fh:
            fh.write(data)
        with open(LINT_SH, "w", encoding="utf-8") as fh:
            fh.write(f"cat '{LINT_OUT}'; exit {rc}\n")
        return run(proj or P, "format-lint-gate", POST, path=path)

    _nasty = (b'a.py:1: E1 "q" \\ \t\x1b[31mred\x1b[0m \x01\x1f '
              b'\xc3\xa9 100% it\'s\r\n')
    rc, out, err = lint(_nasty, 1)
    _c = _ctx(out, "PostToolUse")
    check("failing lint -> ONE PostToolUse additionalContext object, rc 0, "
          "no stderr", rc == 0 and err == "" and _c is not None,
          repr((rc, out[:300], err[:200])))
    check("the message names the exit code and the tail length",
          (_c or "").startswith("Lint (commands.lint) failed with exit 1 "
                                "after this edit. Last 20 lines:\n"),
          repr((_c or "")[:120]))
    check("quotes, backslash, ESC, C0, %, ' and UTF-8 survive byte-for-byte",
          (_c or "").endswith(_nasty.decode().rstrip("\n")), repr(_c))
    rc, out, err = lint(b"All checks passed!\n", 0)
    check("passing lint says nothing (no context on every edit)",
          rc == 0 and out == "" and err == "", repr((rc, out, err)))
    rc, out, err = lint(b"", 4)
    _c = _ctx(out, "PostToolUse") or ""
    check("a silent failure still reports its exit code and '(no output)'",
          "failed with exit 4" in _c and _c.endswith("\n(no output)"),
          repr(_c))
    rc, out, err = lint(b"".join(b"line %d\n" % i for i in range(30)), 1)
    _c = _ctx(out, "PostToolUse") or ""
    check("only the last 20 lines",
          "\nline 10\n" in _c and "line 9\n" not in _c
          and _c.endswith("line 29"), repr(_c[-200:]))
    rc, out, err = lint(("é" * 20000).encode(), 1)
    _c = _ctx(out, "PostToolUse")
    check("over the cap: cut at LINT_CONTEXT_MAX bytes + [truncated], "
          "under 10,000 characters, still valid JSON",
          _c is not None and _c.endswith("\n[truncated]")
          and len(_c) < 10000
          and len(_c[:-len("\n[truncated]")].encode("utf-8", "replace"))
          <= LINT_CONTEXT_MAX + 3, repr((len(_c or ""), out[:120])))
    # jq-less AND python3-less: the hook never reads the payload, and its
    # JSON is written in pure bash, so it still reaches the model.
    rc, out, err = lint(b'E9 "x"\n', 2, path=_NOPARSER)
    check("no jq, no python3 on PATH: the failing lint still arrives as "
          "valid JSON", rc == 0 and _ctx(out, "PostToolUse") ==
          'Lint (commands.lint) failed with exit 2 after this edit. '
          'Last 20 lines:\nE9 "x"', repr((rc, out[:200], err[:200])))
    rc, out, err = lint(b"fine\n", 0, path=_NOPARSER)
    check("no jq, no python3 on PATH: a passing lint is still silent",
          rc == 0 and out == "", repr((rc, out[:200], err[:200])))

    print("\n== format-lint-gate: an empty lint says so (I-6(a)) ==")
    _NOSID = {"CLAUDE_SESSION_ID": ""}   # the runner's own id must not leak

    def _lint_marks(proj):
        d = os.path.join(proj, ".claude", "sessions")
        if os.path.isdir(d):
            for n in os.listdir(d):
                if n.startswith(".lint-unset-"):
                    os.remove(os.path.join(d, n))
        return d

    for _name, _proj in (("empty", P_EMPTY), ("blank", P_BLANK)):
        for _path in (None, _NOPARSER):
            _lint_marks(_proj)
            rc, out, err = run(_proj, "format-lint-gate", POST, path=_path,
                               env=_NOSID)
            check(f"{_name} lint{' (no parser)' if _path else ''}: one "
                  "systemMessage, for the user, nothing for the model",
                  rc == 0 and err == "" and _obj(out) ==
                  {"systemMessage": LINT_UNSET_NOTICE},
                  repr((rc, out[:200], err[:200])))

    # [WP2 re-review RS-3] Once per session: the default config ships with
    # lint empty, and the notice rode on every Write and Edit.
    print("\n== format-lint-gate: the empty-lint notice, once per session ==")
    _SD = _lint_marks(P_EMPTY)

    def _post(sid, path=None, env=None):
        return run(P_EMPTY, "format-lint-gate", dict(POST, session_id=sid),
                   path=path, env=dict(_NOSID, **(env or {})))

    _r = [_post("rs-a") for _ in range(3)]
    check("one session: the notice on the first edit, silence on the next two",
          [x[0] for x in _r] == [0, 0, 0] and all(x[2] == "" for x in _r)
          and _obj(_r[0][1]) == {"systemMessage": LINT_UNSET_NOTICE}
          and _r[1][1] == "" and _r[2][1] == "", repr(_r)[:400])
    rc, out, err = _post("rs-b")
    check("a new session id shows the notice again",
          rc == 0 and _obj(out) == {"systemMessage": LINT_UNSET_NOTICE},
          repr((rc, out[:200], err[:200])))
    _vic = os.path.join(TMP, "lint-victim")
    with open(_vic, "w", encoding="utf-8") as fh:
        fh.write("keep\n")
    os.symlink(_vic, os.path.join(_SD, ".lint-unset-rs-l"))
    rc, out, err = _post("rs-l")
    _mk = os.path.join(_SD, ".lint-unset-rs-l")
    check("a symlinked marker is removed, not written through, and does not "
          "silence the notice", rc == 0
          and _obj(out) == {"systemMessage": LINT_UNSET_NOTICE}
          and open(_vic, encoding="utf-8").read() == "keep\n"
          and os.path.isfile(_mk) and not os.path.islink(_mk),
          repr((rc, out[:200], err[:200])))
    rc, out, err = _post("../rs-x")
    check("an unsafe session id falls back to the 'default' marker",
          rc == 0 and _obj(out) == {"systemMessage": LINT_UNSET_NOTICE}
          and os.path.isfile(os.path.join(_SD, ".lint-unset-default"))
          and not any("rs-x" in n for n in os.listdir(_SD)),
          sorted(os.listdir(_SD)))
    _r = [_post("rs-np", path=_NOPARSER, env={"CLAUDE_SESSION_ID": "rs-env"})
          for _ in range(2)]
    check("no parser: the marker is keyed on CLAUDE_SESSION_ID, once",
          _obj(_r[0][1]) == {"systemMessage": LINT_UNSET_NOTICE}
          and _r[1][1] == "" and all(x[0] == 0 and x[2] == "" for x in _r)
          and os.path.isfile(os.path.join(_SD, ".lint-unset-rs-env")),
          repr(_r)[:400])
    for _n, _days in ((".lint-unset-rs-old", 9), (".lint-unset-rs-new", 1)):
        _p = os.path.join(_SD, _n)
        open(_p, "w").close()
        _t = time.time() - _days * 86400
        os.utime(_p, (_t, _t))
    _post("rs-c")
    with open(os.path.join(P_EMPTY, ".claude", ".gitignore"),
              encoding="utf-8") as fh:
        _gi = fh.read().splitlines()
    check("the marker is gitignored with the other session state",
          "sessions/.lint-unset-*" in _gi, _gi[:12])
    check("writing a marker purges markers older than 7 days, and only those",
          not os.path.exists(os.path.join(_SD, ".lint-unset-rs-old"))
          and os.path.exists(os.path.join(_SD, ".lint-unset-rs-new")),
          sorted(os.listdir(_SD)))

    # ----------------------------------------------------------------------- #
    print("\n== drift-detector-loop-cooperation: once per tier-3 sentinel ==")
    S = os.path.join(P, ".claude", "sessions")
    os.makedirs(S, exist_ok=True)
    _WANT_COOP = json.loads(templates._LOOP_COOP_JSON)

    def coop(sid="s1", path=None):
        rc, out, err = run(P, "drift-detector-loop-cooperation",
                           {"session_id": sid,
                            "hook_event_name": "PostToolUse",
                            "tool_name": "Edit"}, path=path)
        return rc, _obj(out) == _WANT_COOP, out, err

    def touch(name, t):
        p = os.path.join(S, name)
        with open(p, "a", encoding="utf-8"):
            pass
        os.utime(p, (t, t))

    _now = time.time()
    touch(".loop-active-T-1", _now - 100)
    touch(".drift-tier3-T-1", _now - 100)
    rc, fired, out, err = coop()
    check("first call with a tier-3 sentinel: the instruction, as "
          "additionalContext, rc 0, no stderr",
          rc == 0 and fired and err == "", repr((rc, out[:200], err[:200])))
    rc, fired, out, err = coop()
    check("second call, same sentinel, same session: silent (fire-once)",
          rc == 0 and out == "", repr((rc, out[:200])))
    rc, fired, out, err = coop("s2")
    check("another session: fires once for it too", rc == 0 and fired,
          repr(out[:200]))
    os.utime(os.path.join(S, ".drift-coop-s1"), (_now - 50, _now - 50))
    touch(".drift-tier3-T-1", _now)
    rc, fired, out, err = coop()
    check("a NEWER tier-3 sentinel re-arms it: fires again", fired,
          repr(out[:200]))
    rc, fired, out, err = coop()
    check("...and then is silent again", out == "", repr(out[:200]))
    rc, fired, out, err = coop("../evil")
    check("a path-hostile session id collapses to 'default'",
          fired and os.path.exists(os.path.join(S, ".drift-coop-default"))
          and not os.path.exists(os.path.join(P, ".claude", "evil")),
          sorted(os.listdir(S)))
    os.remove(os.path.join(S, ".drift-coop-default"))
    rc, fired, out, err = coop(path=_NOPARSER)
    check("no jq, no python3: still fires (under the 'default' marker)",
          rc == 0 and fired, repr((rc, out[:200], err[:200])))
    rc, fired, out, err = coop(path=_NOPARSER)
    check("no jq, no python3: and only once", rc == 0 and out == "",
          repr((rc, out[:200], err[:200])))
    touch(".drift-coop-old", _now - 9 * 86400)
    coop("s3")
    check("markers older than 7 days are swept",
          not os.path.exists(os.path.join(S, ".drift-coop-old")))

    # ----------------------------------------------------------------------- #
    print("\n== the alarms: OSC 9 terminalSequence for the operator ==")
    rc, out, err = run(P, "task-done-alarm",
                       {"session_id": "s", "hook_event_name": "SubagentStop",
                        "stop_hook_active": False})
    check("task-done-alarm: ONE terminalSequence, OSC 9 ... BEL, no stderr",
          rc == 0 and err == "" and _obj(out) == {
              "terminalSequence":
              "\x1b]9;Claude Code: task complete. Ready for review.\x07"},
          repr((rc, out, err)))
    rc, out, err = run(P, "task-done-alarm",
                       {"session_id": "s", "stop_hook_active": True})
    check("task-done-alarm: silent when stop_hook_active",
          rc == 0 and out == "" and err == "", repr((rc, out, err)))
    _st = json.load(open(os.path.join(P, ".claude", "settings.json")))
    _notif = [(g.get("matcher"), h["command"])
              for g in _st["hooks"].get("Notification", [])
              for h in g["hooks"]]
    check("decision-required-alarm is registered for permission_prompt and "
          "elicitation_dialog only",
          [m for m, c in _notif if c.endswith("/decision-required-alarm.sh")]
          == ["permission_prompt|elicitation_dialog"], repr(_notif))
    _q = '"$CLAUDE_PROJECT_DIR"/.claude/hooks/decision-required-alarm.sh'
    for _cmd in (_q, "$CLAUDE_PROJECT_DIR/.claude/hooks/"
                 "decision-required-alarm.sh"):
        _ours = {"Notification": [{"matcher":
                                   "permission_prompt|elicitation_dialog",
                                   "hooks": [{"type": "command",
                                              "command": _q}]}]}
        _theirs = {"Notification": [{"hooks": [{"type": "command",
                                                "command": _cmd}]}]}
        _m, _ = _merge_hooks(_ours, _theirs, None, [])
        check(f"re-install with no manifest drops the old match-all "
              f"Notification site ({_cmd[:22]})",
              [g.get("matcher") for g in _m["Notification"]]
              == ["permission_prompt|elicitation_dialog"], json.dumps(_m))
    _theirs = {"Notification": [{"hooks": [{"type": "command",
                                            "command": "notify-send hi"}]}]}
    _m, _ = _merge_hooks({}, _theirs, None, [])
    check("an operator's own match-all Notification hook is kept (control)",
          _m == _theirs, json.dumps(_m))
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

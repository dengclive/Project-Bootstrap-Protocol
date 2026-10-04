#!/usr/bin/env python3
"""[WP2] Shared plumbing: one definition of each constant, two substrates.

lib/sdk_gates_template.py defines LINT_CONTEXT_MAX, RUNNER_TAIL_LINES and
TDD_TEST_BASENAMES / TDD_TEST_DIRS / TDD_TEST_SOURCE_SETS once. The emitted
gates.py renders them into its prelude, and lib/templates.py imports them to
emit the shell hooks. These rows pin that both copies are the one definition
(the WP1 NO_TESTS_RC5_RE pattern), and that the install-time JSON helpers and
the ONE bash JSON-string encoder produce what a JSON parser reads back.

Run: python3 tests/test_shared_plumbing.py
"""
import fnmatch
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

import sdk_gates_template as sgt  # noqa: E402
import templates  # noqa: E402

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


# ---------------------------------------------------------------------------
print("\n== [WP2] the constants' values ==")
check("LINT_CONTEXT_MAX is 9,000 bytes, under the 10,000-character cap",
      sgt.LINT_CONTEXT_MAX == 9000, repr(sgt.LINT_CONTEXT_MAX))
check("RUNNER_TAIL_LINES is 100 (operator decision 2026-10-03)",
      sgt.RUNNER_TAIL_LINES == 100, repr(sgt.RUNNER_TAIL_LINES))
_JS = ("js", "jsx", "ts", "tsx", "mjs", "cjs", "mts", "cts")
check("TDD_TEST_BASENAMES is each ecosystem's test naming rule "
      "(operator decision 2026-10-03, WP2 design tdd-test-paths)",
      sgt.TDD_TEST_BASENAMES == (
          ("test_*.*", "*_test.*", "conftest.py", "__init__.py",
           "*_spec.rb", "tests.rs")
          + tuple("*.test." + e for e in _JS)
          + tuple("*.spec." + e for e in _JS)),
      repr(sgt.TDD_TEST_BASENAMES))
check("TDD_TEST_DIRS is the design's test-directory set",
      sgt.TDD_TEST_DIRS == ("[Tt]est", "[Tt]ests", "__tests__", "__mocks__",
                            "__snapshots__", "__fixtures__", "testdata",
                            "*.Test", "*.*Tests"), repr(sgt.TDD_TEST_DIRS))
check("TDD_TEST_SOURCE_SETS is the Gradle/KMP *Test sets and testFixtures",
      sgt.TDD_TEST_SOURCE_SETS == ("[abcdefghijklmnopqrstuvwxyz]*Test",
                                   "testFixtures"),
      repr(sgt.TDD_TEST_SOURCE_SETS))

# ---------------------------------------------------------------------------
print("\n== [WP2] lib/templates.py imports the one definition ==")
for _n in ("LINT_CONTEXT_MAX", "RUNNER_TAIL_LINES", "TDD_TEST_BASENAMES",
           "TDD_TEST_DIRS", "TDD_TEST_SOURCE_SETS", "LINT_TAIL_LINES",
           "LINT_UNSET_NOTICE"):
    check(f"templates.{_n} IS sdk_gates_template.{_n}",
          getattr(templates, _n, None) is getattr(sgt, _n))
check("the shell basename arm is '|'.join(TDD_TEST_BASENAMES)",
      templates._TDD_BASENAME_ARM == "|".join(sgt.TDD_TEST_BASENAMES),
      templates._TDD_BASENAME_ARM)
check("the shell directory arm is '|'.join(TDD_TEST_DIRS)",
      templates._TDD_DIR_ARM == "|".join(sgt.TDD_TEST_DIRS),
      templates._TDD_DIR_ARM)
check("the shell source-set arm is '|'.join(TDD_TEST_SOURCE_SETS)",
      templates._TDD_SOURCE_SET_ARM == "|".join(sgt.TDD_TEST_SOURCE_SETS),
      templates._TDD_SOURCE_SET_ARM)


# ---------------------------------------------------------------------------
print("\n== [WP2] gates.py renders the same constants ==")
_stub = types.ModuleType("claude_agent_sdk")


class _StubHookMatcher:
    def __init__(self, matcher=None, hooks=None, timeout=None):
        self.matcher, self.hooks, self.timeout = matcher, hooks or [], timeout


_stub.HookMatcher = _StubHookMatcher
sys.modules["claude_agent_sdk"] = _stub

TMP = tempfile.mkdtemp(prefix="shared-plumbing-")
try:
    PROJ = os.path.join(TMP, "proj")
    os.makedirs(PROJ)
    _cfg = os.path.join(TMP, "config.yaml")
    with open(_cfg, "w", encoding="utf-8") as fh:
        fh.write('gate_substrate: "sdk-callable"\n'
                 'project:\n  name: "plumbing"\n  archetype: "ai-agent"\n'
                 '  shell: "bash"\n'
                 'principles:\n  tdd_policy: required\n'
                 'commands:\n  test: "true"\n  lint: "true"\n')
    _r = subprocess.run([sys.executable, INSTALL, "-c", _cfg, "-C", PROJ],
                        capture_output=True, text=True)
    check("the sdk-callable fixture installs", _r.returncode == 0,
          (_r.stdout + _r.stderr)[-300:])
    _gp = os.path.join(PROJ, ".claude", "sdk_gates", "gates.py")
    _src = open(_gp, encoding="utf-8").read() if os.path.exists(_gp) else ""
    _sp = importlib.util.spec_from_file_location("plumbing_gates", _gp)
    _mod = importlib.util.module_from_spec(_sp)
    try:
        _sp.loader.exec_module(_mod)
    except Exception as e:  # noqa: BLE001 - reported as a FAIL row
        check("the emitted gates.py imports", False, repr(e))
    for _n in ("LINT_CONTEXT_MAX", "RUNNER_TAIL_LINES", "TDD_TEST_BASENAMES",
               "TDD_TEST_DIRS", "TDD_TEST_SOURCE_SETS",
               # [WP2 channels] format-lint-gate's tail length and I-6(a)
               "LINT_TAIL_LINES", "LINT_UNSET_NOTICE"):
        check(f"gates.py _{_n} == sdk_gates_template.{_n}",
              getattr(_mod, "_" + _n, None) == getattr(sgt, _n),
              repr(getattr(_mod, "_" + _n, None)))
        check(f"gates.py assigns _{_n} exactly once",
              _src.count(f"\n_{_n} = ") == 1, str(_src.count(f"\n_{_n} = ")))
finally:
    shutil.rmtree(TMP, ignore_errors=True)


# ---------------------------------------------------------------------------
print("\n== [WP2] install-time JSON helpers ==")
_j = templates._ctx_json("PostToolUse", 'say "hi"\tnow')
check("_ctx_json round-trips to hookSpecificOutput.additionalContext",
      json.loads(_j) == {"hookSpecificOutput": {
          "hookEventName": "PostToolUse",
          "additionalContext": 'say "hi"\tnow'}}, _j)
_j = templates._osc9_json("task complete")
check("_osc9_json wraps the text in an OSC 9 terminalSequence",
      json.loads(_j) == {"terminalSequence": "\x1b]9;task complete\x07"}, _j)
for _bad in ("it's", "100%"):
    for _f, _args in ((templates._ctx_json, ("PostToolUse", _bad)),
                      (templates._osc9_json, (_bad,))):
        try:
            _f(*_args)
            _ok = False
        except AssertionError:
            _ok = True
        check(f"{_f.__name__} refuses {_bad!r} (printf '...' safety)", _ok)


# ---------------------------------------------------------------------------
print("\n== [WP2] _SHELL_JSON_STR, the one bash encoder ==")


def _enc(data, cap, locale="C.UTF-8"):
    """Run _json_str on `data` (bytes) in bash; (rc, stdout bytes)."""
    prog = (templates._SHELL_JSON_STR
            + 'LC_ALL="$3"; _json_str "$1" "$2"; printf "|%s" "$LC_ALL"\n')
    p = subprocess.run([BASH, "-c", prog, "enc", data, str(cap), locale],
                       capture_output=True, timeout=60)
    return p.returncode, p.stdout


def _dec(out):
    body, _, lc = out.rpartition(b"|")
    try:
        return json.loads(body.decode("utf-8")), lc.decode()
    except ValueError:
        return None, lc.decode()


if not BASH:
    check("bash is on PATH (the encoder rows need it)", False)
else:
    _corpus = [
        ("plain ASCII", b"Lint failed: 3 errors"),
        ("quote and backslash", b'say "x" \\ and \\n literally'),
        ("newline, CR and tab", b"a\nb\r\nc\td"),
        ("every other C0 byte", bytes(range(1, 32))),
        ("DEL and printable punctuation", b"\x7f & | ' % $ ` ; ~"),
        ("UTF-8 passes through", "café ☃ \U0001F600".encode()),
        ("empty", b""),
    ]
    for _label, _data in _corpus:
        for _loc in ("C.UTF-8", "C"):
            _rc, _out = _enc(_data, 9000, _loc)
            _got, _lc = _dec(_out)
            check(f"encoder: {_label} round-trips (LC_ALL={_loc})",
                  _rc == 0 and _got == _data.decode("utf-8"), repr(_out[:120]))
        # Byte for byte what Python's json.dumps writes, short escapes for
        # \t \n \r too, except that the encoder spells 0x08 and 0x0c as
        # \u0008 and \u000c where json.dumps writes \b and \f (the same
        # string to any JSON parser).
        _want = (json.dumps(_data.decode("utf-8"), ensure_ascii=False)
                 .replace("\\b", "\\u0008").replace("\\f", "\\u000c"))
        check(f"encoder: {_label} is byte-identical to json.dumps",
              _out.rpartition(b"|")[0] == _want.encode("utf-8"),
              repr(_out[:120]))
    _rc, _out = _enc(b"x" * 50, 10)
    _got, _ = _dec(_out)
    check("encoder: input over the cap is cut to MAXBYTES + \\n[truncated]",
          _got == "x" * 10 + "\n[truncated]", repr(_out))
    _rc, _out = _enc(b"x" * 10, 10)
    _got, _ = _dec(_out)
    check("encoder: input AT the cap is not marked truncated",
          _got == "x" * 10, repr(_out))
    # The cap counts BYTES under any locale: 5 snowmen are 15 bytes.
    _rc, _out = _enc("☃".encode() * 5, 6)
    _got, _ = _dec(_out)
    check("encoder: the cap is in bytes, not characters, in a UTF-8 locale",
          _got == "☃" * 2 + "\n[truncated]", repr(_out))
    _rc, _out = _enc(b"a\x01", 9000, "C.UTF-8")
    _, _lc = _dec(_out)
    check("encoder: the caller's LC_ALL is restored on return",
          _lc == "C.UTF-8", repr(_out))


# ---------------------------------------------------------------------------
# The arms the shell tdd-gate will be emitted with match exactly what the
# SDK's per-component fnmatchcase matches, on one corpus of components.
print("\n== [WP2] TDD globs: shell `case` == fnmatchcase ==")
_names = ["test_foo.py", "foo_test.go", "foo_test.py", "foo.test.ts",
          "foo.spec.js", "__init__.py", "latest.py", "Contest.java",
          "attestation.ts", "test.py", "foo.py", "testing", "tests",
          "__tests__", "test", "Tests", "Test", "spec", "foo.spec",
          "_test.", "test_.x", "a.test.b.c",
          # [WP2 design tdd-test-paths] the ecosystem set, and its edges.
          "conftest.py", "qzconftest.py", "foo_spec.rb", "foo_spec.py",
          "tests.rs", "test.rs", "foo.test.mts", "foo.spec.cts",
          "api.spec.json", "foo.test.py", "__mocks__", "__snapshots__",
          "__fixtures__", "testdata", "Foo.Test", "Foo.Tests",
          "Foo.UnitTests", "FooTests", "TEST", "androidTest",
          "integrationTest", "Test", "AndroidTest", "testFixtures",
          "testfixtures", "jvmTest", "ÄTest", "aTest", "main"]
if BASH:
    for _label, _arm, _globs in (
            ("basename", templates._TDD_BASENAME_ARM,
             sgt.TDD_TEST_BASENAMES),
            ("directory", templates._TDD_DIR_ARM, sgt.TDD_TEST_DIRS),
            ("source set", templates._TDD_SOURCE_SET_ARM,
             sgt.TDD_TEST_SOURCE_SETS)):
        _prog = ('for x in "$@"; do case "$x" in ' + _arm
                 + ') echo 1 ;; *) echo 0 ;; esac; done')
        _p = subprocess.run([BASH, "-c", _prog, "tdd"] + _names,
                            capture_output=True, text=True, timeout=60)
        _sh = _p.stdout.split()
        _py = ["1" if any(fnmatch.fnmatchcase(n, g) for g in _globs) else "0"
               for n in _names]
        check(f"TDD {_label} arm: shell case == fnmatchcase on "
              f"{len(_names)} names", _sh == _py,
              repr([n for n, a, b in zip(_names, _sh, _py) if a != b]))


# ---------------------------------------------------------------------------
# [WP2 review SDK-P5] The shell tdd-gate's _tdd_normpath is the SDK's
# os.path.normpath, on every spelling the seeded corpus can build from `.`,
# `..`, empty and real segments, relative and absolute.
print("\n== [WP2] tdd-gate _tdd_normpath == posixpath.normpath ==")
if BASH:
    import posixpath
    import random
    _fn = templates._TDD_NORM_SH.split("\n_tdd_normpath \"${CLAUDE")[0]
    _rng = random.Random(20261003)
    _paths = ["", ".", "..", "/", "//", "///", "/..", "//..", "a/..",
              "../a/..", "a/../..", "src/tests/../x.py", "src/./test/x.py",
              "./src/x.py", "src/x.py/", "src//tests/x.py", "//src/x",
              "///src/x", "/p/src/../../p/src/x.py", "a/b/../../../c"]
    for _ in range(300):
        _segs = [_rng.choice(("", ".", "..", "src", "tests", "a", "b.py"))
                 for _ in range(_rng.randint(1, 6))]
        _paths.append(_rng.choice(("", "/", "//", "./"))
                      + "/".join(_segs))
    _prog = (_fn + '\nfor x in "$@"; do _tdd_normpath "$x"; '
             'printf \'%s\\n\' "$_tdd_n"; done')
    _p = subprocess.run([BASH, "-c", "set -euo pipefail\n" + _prog, "n"]
                        + _paths, capture_output=True, text=True, timeout=60)
    _sh = _p.stdout.split("\n")[:-1]
    _py = [posixpath.normpath(x) for x in _paths]
    check(f"_tdd_normpath == posixpath.normpath on {len(_paths)} paths "
          "(under set -euo pipefail)",
          _p.returncode == 0 and _sh == _py,
          repr((_p.returncode, _p.stderr[-200:],
                [(x, a, b) for x, a, b in zip(_paths, _sh, _py)
                 if a != b][:5])))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

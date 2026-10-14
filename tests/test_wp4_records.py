#!/usr/bin/env python3
"""[WP4] WP4's records say what WP4 built (build plan step 3, commit 9).

The records are the tracked ones WP4's last commit writes: the changelog's
WP4 entry, the seam contract's dated WP4 notes, the backlog's WP4 rows and
layers, and the dated layer on the readiness queue's
protocol-doc-snapshot-retire row.

  1. Freeze exception 85. Its seven action counts and seven digests are
     pinned below as LITERALS, the values commit 4's re-baseline set. This
     suite never reads the golden suites' EXPECTED_* tables: a row that
     reads a live table moves with the next re-baseline and turns red while
     its record stays true (X2; review freeze F10). The changelog's table
     and paragraph must carry each count and each digest prefix, and the
     paragraph keeps the eight frozen sources before its first blank line,
     where tests/test_wp3_records.py's RC-3 reads them.
  2. The suite list. Every tests/test_wp4_*.py on disk is named in the
     entry's Tests paragraph, each name there exists, and the count in words
     matches. tests/plugin_toolchain_map.py is a helper module, not a suite.
  3. The seam notes. The seam keeps 379 lines (same-line appends only).
     Each note is found on its anchored line and checked against the code:
     the held-lock exit code and wait (installer.EXIT_LOCKED,
     installer._LOCK_WAIT_S), the parse-guard copy, the interviews' refusal
     (both CLIs run with an empty stdin), the state keys and lock files of a
     real install, and the section 8.4 walk's non-critical escalate files.
  4. The backlog rows and layers WP4 files, and the queue row's layer.
  5. The changelog's other WP4 records: the lock measurements, the upgrade
     note, the section 8.4 walk and what WP4 does not do.

Run: python3 tests/test_wp4_records.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, HERE)

import installer  # noqa: E402
import interview  # noqa: E402
import plugin_toolchain_map as PTM  # noqa: E402
import templates  # noqa: E402
from defaults import resolve_config  # noqa: E402
from minyaml import load_yaml  # noqa: E402

INSTALL = os.path.join(ROOT, "bin", "bootstrap-install")
GIT = shutil.which("git")

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


def flat(text):
    return " ".join(text.replace("\\|", "|").split())


def cut(text, start, end):
    i = text.find(start)
    j = text.find(end, i + len(start)) if i >= 0 else -1
    return text[i:j] if 0 <= i < j else ""


def anchored_line(text, prefix):
    """The ONE line starting with prefix, or "" (zero or several)."""
    hits = [ln for ln in text.split("\n") if ln.startswith(prefix)]
    return hits[0] if len(hits) == 1 else ""


def after(text, marker):
    """The part of text after its one marker, or "" without exactly one."""
    parts = text.split(marker)
    return parts[1] if len(parts) == 2 else ""


def row(table_text, rid):
    """The backlog row `| <rid> | ... |`, or ""."""
    return anchored_line(table_text, f"| {rid} | ")


CL_ALL = read("docs/changelog.md")
_CL_RAW = cut(CL_ALL,
              "## Post-2.8.0 — CLAUDE.md, steering and the entry path (WP4)",
              "## Post-2.8.0 — a spec workflow that reaches a merged commit "
              "(WP3)")
CL = flat(_CL_RAW)

# --------------------------------------------------------------------------- #
# 1. Freeze exception 85
# --------------------------------------------------------------------------- #
print("\n=== 1. Freeze exception 85 ===")
check("the changelog's WP4 entry is found, above the WP3 entry", bool(CL))

# Pinned as data: the values commit 4 (9ba6699) wrote into
# EXPECTED_ACTION_COUNTS and EXPECTED_DIGESTS (tests/test_greenfield_golden.py)
# and EXPECTED_RETROFIT_COUNTS and EXPECTED_RETROFIT_DIGESTS
# (tests/test_retrofit.py). Never read from those tables (freeze F10).
_COUNTS = {"default": 66, "full_autonomous": 78, "design_steering": 67,
           "sdk_callable": 67, "gates_off": 59, "retrofit service": 89,
           "retrofit agent": 103}
_DIGESTS = {
    "default":
        "6cc855432be851669bef4763586e4b16ca223b74a3f05f596f292cd106dd5ffb",
    "full_autonomous":
        "43cf6a9981579054104d4cd8d29b065a6fe7a16d64663fcd289ed9dc12f59aef",
    "design_steering":
        "7ca1bd01a7f7c39c46dc89724e9a92144c151d570766a8db000dc48e89894311",
    "sdk_callable":
        "77dcd1b05f85552f01acb7b2f1267b34d1592d99e4b6198c53ff20b83acbd938",
    "gates_off":
        "b4b60ac30ce0e12b4ed90e8a7e1b1283d56d675e025406d16af05e50b3de8e4a",
    "retrofit service":
        "52f49a5790d0b486de37cefb9c368771d588731335aa3d5d5b20779c80fc4c35",
    "retrofit agent":
        "2fc9e993ec238914fbfe106c3cabca4fc58a274f89ebc9c49bc1e8230ab53551",
}
_FIXTURES = r"(default|full_autonomous|design_steering|sdk_callable|" \
            r"gates_off|retrofit service|retrofit agent)"

_FRZ_RAW = cut(_CL_RAW, "**Freeze exception 85.**", "**Tests.**")
_FRZ = flat(_FRZ_RAW)
check("the entry has a Freeze exception 85 section before its Tests "
      "paragraph", bool(_FRZ))
# RC-3 (tests/test_wp3_records.py) reads a later exception's paragraph up to
# its first blank line, so the eight frozen sources must stay above it.
_first = _FRZ_RAW.split("\n\n")[0] if _FRZ_RAW else ""
_SOURCES = ("lib/templates.py", "lib/installer.py", "lib/interview.py",
            "lib/retrofit_interview.py", "lib/defaults.py",
            "lib/llm_advisor.py", "lib/prd_heuristics.py",
            "tests/test_installer.py")
check("the paragraph names the eight frozen sources before its first blank "
      "line (RC-3 reads that far)",
      all(f"`{s}`" in _first for s in _SOURCES),
      [s for s in _SOURCES if f"`{s}`" not in _first])

_ROWS = {m.group(1): (int(m.group(2)), int(m.group(3)), int(m.group(4)),
                      m.group(5))
         for m in re.finditer(
             r"^\| " + _FIXTURES + r" \| (\d+) → (\d+) \| \+(\d+) / 0 \| "
             r"`([0-9a-f]{8})\.\.\.` \|", _FRZ_RAW, re.M)}
check("the table has a row for each of the seven fixtures",
      set(_ROWS) == set(_COUNTS), sorted(set(_COUNTS) ^ set(_ROWS)))
for _fx in sorted(_COUNTS):
    _old, _new, _add, _pre = _ROWS.get(_fx, (None, None, None, None))
    check(f"{_fx}: {_COUNTS[_fx]} actions, as exception 85 set them, and "
          f"+{_add} is the difference",
          _new == _COUNTS[_fx] and _old is not None and _new - _old == _add,
          (_fx, _old, _new, _add))
    check(f"{_fx}: the table's digest prefix is exception 85's "
          f"({_DIGESTS[_fx][:8]})", _pre == _DIGESTS[_fx][:8], (_fx, _pre))
_named = {("retrofit " + k if k in ("service", "agent") else k): v
          for k, v in re.findall(
              r"(default|full_autonomous|design_steering|sdk_callable|"
              r"gates_off|service|agent) `([0-9a-f]{8})\.\.\.`",
              flat(_first))}
check("the paragraph itself names the seven digest prefixes, as exception "
      "85 set them",
      _named == {k: v[:8] for k, v in _DIGESTS.items()},
      {k: (_named.get(k), v[:8]) for k, v in _DIGESTS.items()})
check("every count moved by +2, the escalate skill and command (a gates_off "
      "row is a golden addition, measured on its config at 0845862)",
      all(r[2] == 2 for r in _ROWS.values()) and len(_ROWS) == 7
      and "golden addition" in _FRZ)
check("the paragraph says no hook body moves and names the suite that pins "
      "them", "`tests/test_wp4_must_not_change.py`" in _FRZ
      and "`_HOOK_HEADER`" in _FRZ)

# --------------------------------------------------------------------------- #
# 2. The suite list
# --------------------------------------------------------------------------- #
print("\n=== 2. The suite list ===")
_TESTS = cut(_CL_RAW, "**Tests.**", "\n\n")
_named_suites = set(re.findall(r"`tests/(test_wp4_[a-z_]+\.py)`", _TESTS))
_on_disk = {f for f in os.listdir(HERE)
            if f.startswith("test_wp4_") and f.endswith(".py")}
check("the Tests paragraph names every tests/test_wp4_*.py on disk",
      bool(_TESTS) and _on_disk <= _named_suites,
      sorted(_on_disk - _named_suites))
check("every tests/test_wp4_*.py it names exists",
      _named_suites <= _on_disk, sorted(_named_suites - _on_disk))
_WORDS = {7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten"}
check(f"it says how many ({len(_on_disk)}), in words",
      f"{_WORDS.get(len(_on_disk), len(_on_disk))} new suites" in _TESTS,
      _TESTS[:200])
check("it names tests/plugin_toolchain_map.py as a helper module, not a "
      "suite, and run-tests cannot discover it (no test_ prefix)",
      "`tests/plugin_toolchain_map.py` is a helper module, not a suite"
      in flat(_TESTS)
      and os.path.isfile(os.path.join(HERE, "plugin_toolchain_map.py"))
      and not "plugin_toolchain_map.py".startswith("test_"))

# --------------------------------------------------------------------------- #
# 3. The seam notes
# --------------------------------------------------------------------------- #
print("\n=== 3. The seam notes ===")
SEAM = read("SEAM-CONTRACT-v3-0-0.md")
check("the seam keeps 379 lines (same-line appends only)",
      SEAM.count("\n") == 379, SEAM.count("\n"))

_s32 = after(anchored_line(SEAM, "| `bootstrap-install` | Install the "
                                 "`.claude/` workspace tree |"),
             "**[seam 3.0.0 in-version note, 2026-10-14, WP4")
check("section 3.2: the bootstrap-install row carries the WP4 note",
      bool(_s32))
_src = read("lib/installer.py")
# Adjacent string literals joined, so a message split over source lines
# reads as main() prints it.
_src_joined = re.sub(r'"\s*\n\s*f?"', "", _src)
_held = ("is held by another process (a loop wrapper or another install); "
         "nothing was written. Re-run when it is free.")
check(f"section 3.2 (10): the held-lock exit code is installer.EXIT_LOCKED "
      f"({getattr(installer, 'EXIT_LOCKED', None)}), after "
      f"installer._LOCK_WAIT_S ({getattr(installer, '_LOCK_WAIT_S', None)} s)"
      f", with the message main() prints",
      f"A new exit code, **{installer.EXIT_LOCKED}**" in _s32
      and f"for {installer._LOCK_WAIT_S} s" in _s32
      and _held in _s32 and _held in _src_joined, _s32[:400])
check("section 3.2 (11): the parse guard's warning names its copy, "
      "`<state>.pre-unparsed-<UTC stamp>`, as _keep_unparsed names it",
      "`<state>.pre-unparsed-<UTC stamp>`" in _s32
      and ".pre-unparsed-{stamp}" in _src, _s32[:400])
check("section 3.2 (11): the kept-file warnings name what each kept file "
      "lacks (the sections _steering_warnings checks)",
      all(h in _s32 for h in ("`## Do Not Touch`", "`## Documentation "
                              "Policy`", "`## Never`"))
      and all(h in _src for h in ('"## Do Not Touch"',
                                  '"## Documentation Policy"',
                                  '"## Never"')))
check("section 3.2 (11): the no-manifest remedy is per file, and the note "
      "says not to use --adopt, as _no_manifest_remedy does",
      "move the file aside and re-install" in _s32
      and "not to use `--adopt`" in _s32
      and "Don't use --adopt for this" in _src)

# The interviews' refusal, run: both CLIs with an empty stdin.
_TMP = tempfile.mkdtemp(prefix="wp4-records-")
_ENV = {k: v for k, v in os.environ.items()
        if not k.startswith(("CLAUDE", "GIT_"))}
_ENV.update(HOME=_TMP, XDG_CONFIG_HOME=os.path.join(_TMP, ".config"),
            GIT_CEILING_DIRECTORIES=_TMP, GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
_refused = {}
for _tool in ("bootstrap-interview", "retrofit-interview"):
    _d = os.path.join(_TMP, _tool)
    os.makedirs(_d)
    _args = [sys.executable, os.path.join(ROOT, "bin", _tool),
             "interactive", "-o", os.path.join(_d, "out.yaml")]
    if _tool == "bootstrap-interview":
        _args[3:3] = ["--prd", os.path.join(ROOT, "examples",
                                            "sample-prd.md")]
    _r = subprocess.run(_args, stdin=subprocess.DEVNULL, capture_output=True,
                        text=True, cwd=_d, env=_ENV, timeout=120)
    _refused[_tool] = (_r.returncode, "no config written" in _r.stderr,
                       os.path.exists(os.path.join(_d, "out.yaml")))
_s162 = after(anchored_line(SEAM, "**Never invoked by any default Tessera "
                                  "code path:**"),
              "**[In-version note, 2026-10-14, WP4 / 8c.]**")
check("section 3.2: both interviews, run with an empty stdin, exit 2 and "
      "write no config", all(v == (2, True, False)
                             for v in _refused.values()), _refused)
check("section 3.2: the interactive line's WP4 note says so: exit 2, no "
      "config written, BOOTSTRAP_PROMPT_TIMEOUT with its default",
      "exit **2**" in _s162 and "no config written" in _s162
      and "`BOOTSTRAP_PROMPT_TIMEOUT`" in _s162 and "default 30" in _s162
      and '"BOOTSTRAP_PROMPT_TIMEOUT", "30"' in read("lib/interview.py")
      and all(t in _s162 for t in ("`bootstrap-interview interactive`",
                                   "`retrofit-interview interactive`")),
      _s162[:400])
check("section 3.2: the refusal text the note quotes is the code's",
      "no config written" in interview._closed_refusal("x"))

# Section 7.1, against a real install of the gates-off fixture.
_s71 = after(anchored_line(SEAM, "- The protocol writes "
                                 "`.installer-manifest.json`"),
             "**[In-version note, 2026-10-14, WP4.]**")
check("section 7.1: the manifest line carries the WP4 note", bool(_s71))
_P = os.path.join(_TMP, "p")
os.makedirs(_P)
_state, _lock_kept, _ignored = {}, None, None
if GIT:
    subprocess.run([GIT, "init", "-q", _P], env=_ENV, check=True)
_cfg = os.path.join(_TMP, "gates-off.yaml")
with open(_cfg, "w", encoding="utf-8") as _fh:
    _fh.write('project: {name: "demo", archetype: "fullstack", '
              'shell: "bash"}\nprinciples: {tdd_policy: encouraged}\n'
              'secrets: {enabled: false}\ndeps: {enabled: false}\n'
              'hooks: {secrets_gate: false, dependency_gate: false, '
              'spec_gate_commit: false}\ncommands: {test: "true", '
              'lint: "true", format: "true", ci_local: "true"}\n'
              'workflow: {implementer_isolation: "none"}\n')
_ri = subprocess.run([sys.executable, INSTALL, "-c", _cfg, "-C", _P],
                     capture_output=True, text=True, env=_ENV, timeout=300)
try:
    with open(os.path.join(_P, ".claude", ".bootstrap-state.json"),
              encoding="utf-8") as _fh:
        _state = json.load(_fh)
except (OSError, ValueError):
    pass
_lock = os.path.join(_P, ".claude", ".bootstrap-state.json.lock")
_lock_made = os.path.exists(_lock)
if GIT:
    # `check-ignore -q` takes one path per call.
    _ignored = all(subprocess.run(
        [GIT, "-C", _P, "check-ignore", "-q", rel], env=_ENV).returncode == 0
        for rel in (".claude/.bootstrap-state.json.lock",
                    ".claude/.bootstrap-state.json.pre-unparsed-x"))
_ru = subprocess.run([sys.executable, INSTALL, "-c", _cfg, "-C", _P,
                      "--uninstall"], capture_output=True, text=True,
                     env=_ENV, timeout=300)
_lock_kept = os.path.exists(_lock)
_pd = _state.get("protocol_doc")
check("a real install: rc 0, protocol_doc is an absolute path to a file "
      "(or null), and a fresh state file has bootstrap_complete false",
      _ri.returncode == 0 and (_pd is None or (os.path.isabs(_pd)
                                               and os.path.isfile(_pd)))
      and _state.get("bootstrap_complete") is False,
      (_ri.returncode, _pd, _state.get("bootstrap_complete"),
       _ri.stderr[-300:]))
check("a real install leaves .bootstrap-state.json.lock, git ignores it "
      "and a .pre-unparsed- copy, and --uninstall leaves the lock",
      _lock_made and _ignored in (True, None) and _ru.returncode == 0
      and _lock_kept, (_lock_made, _ignored, _ru.returncode, _lock_kept))
check("section 7.1: the note names protocol_doc (an absolute path, or "
      "null), bootstrap_complete, both lock files and the .pre-unparsed- "
      "copies, and says --uninstall leaves the locks",
      all(w in _s71 for w in ("`protocol_doc`", "`null`", "absolute path",
                              "`bootstrap_complete`",
                              "`.claude/.bootstrap-state.json.lock`",
                              "`.claude/.retrofit-state.json.lock`",
                              "`<state>.pre-unparsed-<UTC stamp>`",
                              "`--uninstall` leaves them")),
      _s71[:400])
shutil.rmtree(_TMP, ignore_errors=True)

# Section 8.4, walked.
_s84 = after(anchored_line(SEAM, "Changes that touch only gate internals or "
                                 "dispatch policy do **not** bump"),
             "**[In-version note, 2026-10-14, WP4: the §8.4 walk.]**")
_cfg_d, _ = resolve_config(load_yaml(read("bootstrap.config.yaml")))
_plan_d = {a["path"]: a for a in installer.build_plan(_cfg_d)}
_esc = (".claude/skills/escalate/SKILL.md", ".claude/commands/escalate.md")
check("section 8.4: the escalate skill and command are non-critical file "
      "actions (no section 7.2 member is added)",
      all(p in _plan_d and _plan_d[p]["kind"] == "file"
          and installer._hook_tier(_plan_d[p]) == installer.TIER_NON
          for p in _esc))
check("section 8.4: the walk's note is there: no trigger fires, no bump, "
      "and it says why", "no trigger fires" in _s84
      and "no `seam_version` bump" in _s84 and "additive" in _s84
      and "non-critical" in _s84, _s84[:300])

# --------------------------------------------------------------------------- #
# 4. The backlog and the queue
# --------------------------------------------------------------------------- #
print("\n=== 4. The backlog and the queue ===")
BL = read("docs/deferred-backlog.md")
_NEW = ("Z-58", "Z-59", "Z-60", "Z-61", "Z-62", "Z-63", "Z-64")
_rows = {r: row(BL, r) for r in _NEW + ("X-30a", "Z-40", "M-2")}
check("the backlog has rows Z-58 to Z-64", all(_rows[r] for r in _NEW),
      [r for r, v in _rows.items() if not v])
check("Z-58 is D1 (b), a decision row, and lists the inventory rows it "
      "leaves open, the plugin path's environment audit among them",
      "D1 (b)" in _rows["Z-58"] and "`decision`" in _rows["Z-58"]
      and all(w in _rows["Z-58"] for w in (
          "`steering-authoring-route`", "`wizard-entry-point`",
          "`p2-w1-line-survives-ai-authoring`", "`environment-audit`",
          "`/bootstrap-protocol:bootstrap-interview`")))
check("Z-59 is CI config generation, out (ruling 8, 8d)",
      "CI config generation" in _rows["Z-59"] and "8d" in _rows["Z-59"])
check("Z-60 is the interviews' hint paths (ruling 8, 8e), and the hints "
      "still print bin/ paths",
      "8e" in _rows["Z-60"]
      and "`bin/bootstrap-install --dry-run`" in _rows["Z-60"]
      and "bin/bootstrap-install --dry-run" in read("lib/interview.py"))
check("Z-61 is retrofit Phase 8 parity (ruling 4 (a)) and Z-62 the retrofit "
      "configs over 80 lines",
      "ruling 4 (a)" in _rows["Z-61"] and "parity" in _rows["Z-61"]
      and "83 or 84 lines" in _rows["Z-62"])
check("Z-63 is a RETROFIT.md copy and retrofit-interview in the plugin "
      "before publishing, and the map still copies neither",
      "`RETROFIT.md`" in _rows["Z-63"]
      and "`bin/retrofit-interview`" in _rows["Z-63"]
      and not any("RETROFIT" in c or "retrofit-interview" in c
                  for c in PTM.copy_map()))
# Z-64, against README.md: every bin/ tool and lib/ module the What you get
# tree leaves out is named in the row (vacuous once the README names them
# all, which is when the row needs a done layer), and the two sentences it
# quotes are still there.
_readme = read("README.md")
_tree = cut(_readme, "## What you get", "## Properties")
try:
    _tracked = subprocess.run([GIT, "ls-files", "bin", "lib"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.split() if GIT else []
except subprocess.CalledProcessError:
    _tracked = []
_left_out = [p for p in _tracked if (p.startswith("bin/")
                                     or p.endswith(".py"))
             and p not in _tree]
check(f"Z-64 names each bin/ tool and lib/ module What you get leaves out "
      f"({len(_left_out)} on this tree)",
      len(_tracked) > 10 and all(f"`{p}`" in _rows["Z-64"]
                                 for p in _left_out),
      [p for p in _left_out if f"`{p}`" not in _rows["Z-64"]])
check("Z-64 quotes the empty-lint sentence, and the Usage block's "
      "`python3 bin/` commands, as README.md has them",
      "An empty lint command means `format-lint-gate` checks nothing and "
      "prints nothing" in _rows["Z-64"]
      and "An empty lint\n  command means `format-lint-gate` checks nothing "
      "and prints nothing" in _readme
      and "`python3 bin/...`" in _rows["Z-64"]
      and "\npython3 bin/bootstrap-install --dry-run\n" in _readme)
_lay = "Layer 2026-10-14, WP4"
check("X-30a, Z-40 and M-2 carry a dated WP4 layer, and M-2 is done",
      all(_lay in _rows[r] for r in ("X-30a", "Z-40"))
      and "**done — WP4" in _rows["M-2"])
_al = {a["path"]: a["body"] for a in installer.build_plan(_cfg_d)}
check("M-2: the emitted audio-alerts.config cites the current protocol, and "
      "drift-detector.sh cites no v2-5-0 file",
      templates.PROTOCOL_DOC in _al[".claude/hooks/audio-alerts.config"]
      and "Bootstrap-Protocol-v2-5-0.md" not in
      _al[".claude/hooks/audio-alerts.config"]
      and "Bootstrap-Protocol-v2-5-0.md" not in
      _al[".claude/hooks/drift-detector.sh"])
check("the backlog's section Z has the WP4 layer naming Z-58 to Z-64",
      "**Layer 2026-10-14, WP4 (branch `feat/wp4-claude-md-steering-entry`)"
      ".**" in BL and "Z-58 to Z-64 are WP4 residue" in BL)

Q = read(".claude/readiness-queue.md")
_qrow = cut(Q, "- **[ready] protocol-doc-snapshot-retire**",
            "\n\n- **[")
_qlay = flat(after(_qrow, "**[Layer 2026-10-14, WP4"))
check("the protocol-doc-snapshot-retire row has a dated WP4 layer",
      bool(_qlay))
check("the layer names the _HOOK_HEADER conflict, which the code still has "
      "(its 6.D line cites the 2.0.0 file)",
      "`_HOOK_HEADER`" in _qlay and "6.D" in _qlay
      and "Bootstrap-Protocol-v2-0-0.md 6.D" in templates._HOOK_HEADER)
check("the layer names the moved manifest, which exists, and the old path, "
      "which does not",
      "`plugin/.claude-plugin/plugin.json`" in _qlay
      and os.path.isfile(os.path.join(ROOT, "plugin", ".claude-plugin",
                                      "plugin.json"))
      and not os.path.exists(os.path.join(ROOT, "plugin", "plugin.json")))
check("the layer adds plugin/toolchain/** to the scope globs and the "
      "identity suite, with the map's --sync command, to the feedback loop",
      "`plugin/toolchain/**`" in _qlay
      and "`tests/test_wp4_plugin_toolchain.py`" in _qlay
      and f"`{PTM.SYNC}`" in _qlay and f"`{PTM.STAGE}`" in _qlay)

# --------------------------------------------------------------------------- #
# 5. The changelog's other WP4 records
# --------------------------------------------------------------------------- #
print("\n=== 5. The other changelog records ===")
_sec = "[WP4 8b] an install waits for a wrapper's state update"
check("the lock measurements name the test_wrapper_behavior section that "
      "holds them, which exists (ED17: counts go here, not in the protocol)",
      "**The install lock, measured.**" in CL and _sec in CL
      and _sec in read("tests/test_wrapper_behavior.py"))
_up = cut(CL, "**Upgrading an install made before WP4.**", "**")
check("the upgrade note gives the per-file remedy and warns off --adopt",
      "move it aside" in _up and "re-install" in _up and "--adopt" in _up,
      _up[:300])
check("the entry walks section 8.4 and says what WP4 does not do, naming "
      "each new backlog row",
      "**Seam — the §8.4 trigger walk.**" in CL
      and "**What WP4 does not do.**" in CL
      and all(f"({r}" in CL or f" {r}," in CL or f" {r})" in CL
              for r in _NEW))
check("the plugin paragraph names the one map and the maintainer's --sync "
      "and stage commands, as tests/plugin_toolchain_map.py spells them",
      "`tests/plugin_toolchain_map.py` is the one map" in CL
      and f"`{PTM.SYNC}`" in CL and f"`{PTM.STAGE}`" in CL)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

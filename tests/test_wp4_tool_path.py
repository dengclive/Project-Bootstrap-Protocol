#!/usr/bin/env python3
"""[WP4] The tool path: what the installer and the interviews record and
say (design group g5; review items 8b and 8c; ruling 12 (a)).

1. Protocol filenames. Every protocol or Companion file name in an emitted
   body is the current pair (PROTOCOL_DOC, PROTOCOL_COMPANION), except the
   `6.D checklist` line of the shared hook header: it sits in
   secrets-gate.sh and dependency-gate.sh too, which the pivot does not
   touch, so it stays with the queued protocol-doc-snapshot-retire item.
   The interview's operator-facing text names the current file (g5-1b).
2. The assumption ledger's links resolve, and the state file records where
   the protocol document is, as `protocol_doc` (g5-2b): the document next
   to the installer that ran, a plugin copy's `protocol.md` (X6), or null.
3. Mark the bootstrap complete (g5-3). A fresh install records
   `bootstrap_complete: false`; a re-install keeps what the AI or the
   operator set, and never adds the key to a state file that predates it.
4. Next steps (g5-4, X4). While this install still owns a steering stub, a
   line before the smoke test names it and says where the docs are filled.
   The smoke test comes before real work, and the last line says how to
   record it and mark the bootstrap complete.
5. One lock (8b). A real apply holds the state files' sibling locks from
   before its first write to after the manifest write. A lock that another
   process holds exits EXIT_LOCKED with nothing written; a lock file that
   no one holds never blocks; --dry-run takes no lock; --uninstall leaves
   the lock files.
6. The parse guard (ruling 12 (a)). A state file that does not parse as a
   JSON object is copied aside under a name the emitted .gitignore covers,
   a warning names the copy, and the run carries on with an empty state.
7. The interactive interviews (8c). With no terminal and no answer, both
   refuse with rc 2 before anything is written (retrofit's inventory
   included); a full pipe runs with no delay; input that ends early warns,
   and the config header names the values that took their defaults.
8. `--force --dry-run` says where the backups would be saved (DOC-2).
9. The README (commit 8, rewritten from the design critic's rows). Getting
   started comes first, after the banner, and the introduction keeps its
   own heading (X1); the banner's dated correction sends readers to `main`,
   and the tag it names predates the route; no old protocol file name. Each
   claim the new text makes is paired with the code where a row can check
   it: the route's tools and flags, the steering stubs and the Next steps
   lines (g3-1), the parse-guard copy, the `.claude/` approval sentence
   (X9), the per-file remedy measured in a fresh clone and no --adopt or
   --force advice (KEEP-1, NF-1), the conditional --force --dry-run
   (DOC-2), the retrofit route and RETROFIT.md's note, the plugin's
   manifest, prefixed commands, toolchain copies and sync commands (read
   from tests/plugin_toolchain_map.py), the interviews' refusal and
   BOOTSTRAP_PROMPT_TIMEOUT, the held-lock exit code, and the dated
   correction on the I-1 history entry.

Doc rows (commit 6): the protocol's filename note, and RETROFIT.md and
RETROFIT-COMPANION.md naming the current protocol file, in section 1; g3's
two EOF TRUTH rows, inverted and paired with the For-the-AI notes that now
say the interviews refuse, in section 7. tests/test_wp4_protocol_notes.py
pins every other dated WP4 note and the docs' line counts, and keeps
"accepts every" out of the README above its review history.

The interleave measurements with a loop wrapper are in
tests/test_wrapper_behavior.py, behind its flock skip.

Run: python3 tests/test_wp4_tool_path.py
"""
import hashlib
import json
import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
try:
    import pty
except ImportError:                    # pragma: no cover - not POSIX
    pty = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
LIB = os.path.join(ROOT, "lib")
sys.path.insert(0, LIB)

import installer                                  # noqa: E402
import interview as IV                            # noqa: E402
import llm_advisor as LLM                         # noqa: E402
import templates                                  # noqa: E402
from defaults import resolve_config               # noqa: E402
from installer import build_plan                  # noqa: E402
from minyaml import load_yaml                     # noqa: E402

sys.path.insert(0, HERE)
import plugin_toolchain_map as PTM                # noqa: E402

INSTALL =os.path.join(ROOT, "bin", "bootstrap-install")
INTERVIEW = os.path.join(ROOT, "bin", "bootstrap-interview")
RETRO_INTERVIEW = os.path.join(ROOT, "bin", "retrofit-interview")
SAMPLE_PRD = os.path.join(ROOT, "examples", "sample-prd.md")
GIT = shutil.which("git")
BASH = shutil.which("bash")
try:
    import fcntl
except ImportError:                    # pragma: no cover - not POSIX
    fcntl = None

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
            print(f"        {str(detail)[:1500]}")


def fixture(src_file, var):
    text = open(os.path.join(HERE, src_file)).read()
    return re.search(var + r' = """(.*?)"""', text, re.S).group(1)


DEFAULT = open(os.path.join(ROOT, "bootstrap.config.yaml")).read()
GATES_OFF = fixture("test_greenfield_golden.py", "FIXTURE_GATES_OFF")
RETRO = fixture("test_retrofit.py", "SERVICE_RETROFIT_CFG")
FIXTURES = {
    "default": DEFAULT,
    "full_autonomous": fixture("test_greenfield_golden.py",
                               "FIXTURE_FULL_AUTONOMOUS"),
    "design_steering": fixture("test_greenfield_golden.py",
                               "FIXTURE_DESIGN_STEERING"),
    "sdk_callable": 'gate_substrate: "sdk-callable"\n' + DEFAULT,
    "gates_off": GATES_OFF,
    "retrofit_service": RETRO,
    "retrofit_agent": fixture("test_retrofit.py", "AGENT_RETROFIT_CFG"),
}
PLANS = {}
for _n, _y in FIXTURES.items():
    _cfg, _errs = resolve_config(load_yaml(_y))
    assert not _errs, (_n, _errs)
    PLANS[_n] = (_cfg, build_plan(_cfg))

NAME_RE = re.compile(r"Bootstrap-Protocol-(?:Companion-)?v\d+-\d+-\d+\.md")
# getattr so the suite runs (and reports) on a tree without the constants.
PROTOCOL_DOC = getattr(templates, "PROTOCOL_DOC",
                       "Bootstrap-Protocol-v2-8-0.md")
PROTOCOL_COMPANION = getattr(templates, "PROTOCOL_COMPANION",
                             "Bootstrap-Protocol-Companion-v2-8-0.md")
CURRENT = {PROTOCOL_DOC, PROTOCOL_COMPANION}
DOC_PATH = os.path.join(os.path.realpath(ROOT), PROTOCOL_DOC)
# The shared hook header's citation, frozen by the pivot (see the docstring).
HEADER_LINE = ("# Security/correctness (Bootstrap-Protocol-v2-0-0.md 6.D "
               "checklist):")
STATE = ".claude/.bootstrap-state.json"
RSTATE = ".claude/.retrofit-state.json"
STUBS = tuple(".claude/steering/" + n for n in
              ("product.md", "tech.md", "structure.md", "ci-cd.md"))
EXIT_LOCKED = getattr(installer, "EXIT_LOCKED", None)
# Runs the installer in a child process with the lock wait patched to 1 s,
# the way the tests patch the module constant.
PATCHED_MAIN = ("import sys; sys.path.insert(0, sys.argv[1]); "
                "import installer; installer._LOCK_WAIT_S = 1; "
                "raise SystemExit(installer.main(sys.argv[2:]))")
LOCK_HELD = ("error: {} is held by another process (a loop wrapper or "
             "another install); nothing was written. Re-run when it is "
             "free.")
HINT = "Run it in a terminal of your own, or use analyze and synthesize."
# The dated-note tags commit 6 appends to the layered docs (ED1).
CORRECTED = "**[Corrected 2026-10-14, WP4.]**"
ROUTE_NOTE = "**[Amended 2026-10-14, WP4 / D1.]**"
TMP = tempfile.mkdtemp(prefix="wp4-tool-")


def run(argv, **kw):
    kw.setdefault("timeout", 300)
    return subprocess.run(argv, capture_output=True, text=True, **kw)


def project(name, git=True):
    d = os.path.join(TMP, name)
    os.makedirs(d)
    if git and GIT:
        subprocess.run([GIT, "init", "-q", d], check=True)
    return d


def install(proj, cfg_text=None, *extra):
    cfg = os.path.join(proj, "bootstrap.config.yaml")
    if cfg_text is not None:
        with open(cfg, "w") as fh:
            fh.write(cfg_text)
    return run([sys.executable, INSTALL, "-c", cfg, "-C", proj, *extra])


def read(proj, rel):
    try:
        with open(os.path.join(proj, rel)) as fh:
            return fh.read()
    except OSError:
        return None


def state_of(proj, rel=STATE):
    try:
        with open(os.path.join(proj, rel)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def steps_of(out):
    """The numbered Next steps lines, without their numbers."""
    i = out.find("\nNext steps:\n")
    if i < 0:
        return []
    return [re.sub(r"^  \d+\. ", "", ln)
            for ln in out[i:].strip("\n").splitlines()[1:]]


def stub_line(lines):
    return next((ln for ln in lines if "fill in the steering docs" in ln), "")


def snapshot(proj):
    """Every file's sha256 under the project, .git/hooks included and the
    rest of .git left out: what an install could write."""
    out = {}
    for base, dirs, files in os.walk(proj):
        rel_base = os.path.relpath(base, proj)
        if rel_base == ".git":
            dirs[:] = [x for x in dirs if x == "hooks"]
            continue
        for f in files:
            p = os.path.join(base, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, proj)] = hashlib.sha256(
                    fh.read()).hexdigest()
    return out


def ignored(proj, rel):
    r = run([GIT, "-C", proj, "check-ignore", "-q", rel])
    return r.returncode == 0


def warnings_of(r):
    return [ln for ln in r.stderr.splitlines() if ln.startswith("warning: ")]


README = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()


def flat(text):
    return " ".join(text.split())


def md_headings(text):
    """(level, title, line index) of each ATX heading outside fenced code."""
    out, fence = [], False
    for i, ln in enumerate(text.split("\n")):
        if ln.startswith("```"):
            fence = not fence
            continue
        m = None if fence else re.match(r"(#{1,6}) (.+)$", ln)
        if m:
            out.append((len(m.group(1)), m.group(2).strip(), i))
    return out


def md_section(text, title):
    """The lines under the one heading `title`, up to the next heading of
    its level or higher; "" unless that heading is there exactly once."""
    lines = text.split("\n")
    heads = md_headings(text)
    hits = [(lv, i) for lv, t, i in heads if t == title]
    if len(hits) != 1:
        return ""
    lv, i = hits[0]
    end = next((j for lv2, _, j in heads if j > i and lv2 <= lv), len(lines))
    return "\n".join(lines[i + 1:end])


def slug(title):
    """GitHub's anchor for a heading (duplicate suffixes left out)."""
    return re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")


def sentences(text):
    return re.split(r"(?<=\.)\s+", flat(text))


try:
    # ----------------------------------------------------------------------- #
    # 1. The current pair, and no other name in an emitted body
    # ----------------------------------------------------------------------- #
    print("== 1. protocol filenames ==")
    check("templates defines PROTOCOL_DOC and PROTOCOL_COMPANION",
          hasattr(templates, "PROTOCOL_DOC")
          and hasattr(templates, "PROTOCOL_COMPANION"))
    _doc = os.path.join(ROOT, PROTOCOL_DOC)
    _comp = os.path.join(ROOT, PROTOCOL_COMPANION)
    check("PROTOCOL_DOC names a file at the repository root",
          os.path.isfile(_doc), PROTOCOL_DOC)
    check("PROTOCOL_COMPANION names a file at the repository root",
          os.path.isfile(_comp), PROTOCOL_COMPANION)
    if os.path.isfile(_doc) and os.path.isfile(_comp):
        check("PROTOCOL_DOC's header carries PROTOCOL_VERSION",
              f"**Version:** {templates.PROTOCOL_VERSION}"
              in open(_doc).read(4000))
        check("PROTOCOL_COMPANION mirrors PROTOCOL_DOC and PROTOCOL_VERSION",
              f"matches {PROTOCOL_DOC} {templates.PROTOCOL_VERSION}."
              in open(_comp).read(4000))

    stale, header_sites = [], []
    for _n, (_cfg, _plan) in PLANS.items():
        for _a in _plan:
            for _i, _ln in enumerate(_a["body"].splitlines(), 1):
                for _m in NAME_RE.finditer(_ln):
                    if _m.group(0) in CURRENT:
                        continue
                    if _ln == HEADER_LINE:
                        header_sites.append((_n, _a["path"], _i))
                    else:
                        stale.append(f"{_n}:{_a['path']}:{_i}: "
                                     f"{_ln.strip()[:120]}")
    check("no emitted body names an old protocol or Companion file",
          not stale, "\n        ".join(stale[:40])
          + f"\n        ({len(stale)} sites)")
    check("the only old name left is the hook header's 6.D line, on line 5 "
          "of a hook", header_sites and all(
              p.startswith(".claude/hooks/") and p.endswith(".sh") and i == 5
              for _, p, i in header_sites), header_sites[:5])
    check("the hook header line is still in secrets-gate.sh and "
          "dependency-gate.sh, unchanged (the pivot leaves both alone)",
          any(p == ".claude/hooks/secrets-gate.sh"
              for _, p, _ in header_sites)
          and any(p == ".claude/hooks/dependency-gate.sh"
                  for _, p, _ in header_sites))

    # [g5-1b] The interview's operator-facing text: analyze writes
    # bootstrap.interview.md into the project, and its rationales and open
    # questions cite the protocol. Each PRD below reaches other branches of
    # lib/prd_heuristics.py; the phrases are the non-vacuity check that they
    # were reached.
    _prds = {
        "autonomous web app": "# Queue tool\n\nA web app with a dashboard "
                              "and an autonomous agent that runs "
                              "overnight.\n",
        "no signals": "# Thing\n\nIt does stuff.\n",
        "contested": "# Tool\n\nA command-line tool and a microservice.\n",
        "upgraded": "# Tool\n\nA command-line tool for admins. Personas: the "
                    "on-call admin. It keeps a high test coverage bar and "
                    "has no external dependencies.\n",
    }
    _rendered = ""
    _names = set()
    for _label, _text in _prds.items():
        _r = IV.render_interview(IV.build_proposal(_text), "docs/prd/x.md")
        _rendered += _r
        _found = set(NAME_RE.findall(_r))
        _names |= _found
        check(f"[g5-1b] the interview for a PRD ({_label}) names only the "
              f"current protocol file", _found <= {PROTOCOL_DOC},
              sorted(_found))
    _phrases = ("Human must confirm", "decision margin", "Upgraded (never",
                "No PRD signals", "Phase 4 step 2", "quality emphasis",
                "No TDD signal", "Skip Policy keeps",
                "Skip Policy allows skipping Phase 2.5",
                "strongly recommends deferring", "Phase 0/9.5/9.6/9.7")
    check("[g5-1b] those PRDs reach the heuristics' cited branches "
          "(non-vacuity)", all(p in _rendered for p in _phrases)
          and PROTOCOL_DOC in _names,
          [p for p in _phrases if p not in _rendered])
    _tmp = tempfile.mkdtemp(prefix="wp4g5-", dir=TMP)
    _prd = os.path.join(_tmp, "prd.md")
    with open(_prd, "w") as fh:
        fh.write(_prds["autonomous web app"])
    _out = os.path.join(_tmp, "bootstrap.interview.md")
    _r = run([sys.executable, INTERVIEW, "analyze", "--prd", _prd, "-o",
              _out], timeout=120)
    _iv = open(_out).read() if os.path.exists(_out) else ""
    _found = set(NAME_RE.findall(_iv))
    check("[g5-1b] interview analyze runs, and bootstrap.interview.md names "
          "only the current protocol file",
          _r.returncode == 0 and _found == {PROTOCOL_DOC},
          (_r.returncode, sorted(_found), _r.stderr[-300:]))
    _qcfg, _qerr = resolve_config(load_yaml(
        "project:\n  name: q\n  archetype: cli\n"
        "autonomous_modes:\n  queue_mode_enabled: true\n"))
    check("[g5-1b] resolve_config's queue-mode refusal cites the current "
          "protocol file", any(PROTOCOL_DOC in e for e in _qerr)
          and not any(set(NAME_RE.findall(e)) - {PROTOCOL_DOC}
                      for e in _qerr), _qerr)
    _tier = IV.validate_config_dict(load_yaml(
        "project:\n  name: t\n  archetype: fullstack\n  prd_tier: micro\n"))
    check("[g5-1b] the interview's PRD-tier floor message cites the current "
          "protocol file", any(PROTOCOL_DOC in e for e in _tier)
          and not any(set(NAME_RE.findall(e)) - {PROTOCOL_DOC}
                      for e in _tier), _tier)
    _det = IV.build_proposal(_prds["no signals"])
    _merged = LLM._merge(_det, {"archetype": {"value": "cli",
                                              "confidence": "open"}}, [])
    _oq = _merged["archetype"].get("open_question", {}).get("prompt", "")
    check("[g5-1b] the LLM advisor's open archetype question cites the "
          "current protocol file", PROTOCOL_DOC in _oq
          and set(NAME_RE.findall(_oq)) == {PROTOCOL_DOC}, _oq)

    # [g5-1c, commit 6] The layered docs name the current file in dated
    # notes appended to an existing line, so no cited line number moves.
    _prd_lines = (open(_doc, encoding="utf-8").read().split("\n")
                  if os.path.isfile(_doc) else [])
    _rename = [ln for ln in _prd_lines
               if "Since 2026-08-14 this file is named `v2-8-0`" in ln]
    check("[g5-1c] the protocol's filename note carries a dated note on the "
          "v2-8-0 rename", len(_rename) == 1
          and _rename[0].startswith("> code MINOR (two new configuration "
                                    "keys) served by this one. "
                                    + CORRECTED), _rename)
    _line3 = {}
    for _f in ("RETROFIT.md", "RETROFIT-COMPANION.md"):
        with open(os.path.join(ROOT, _f), encoding="utf-8") as fh:
            _l3 = fh.read().split("\n")[2]
        _line3[_f] = _l3[_l3.find(CORRECTED):] if CORRECTED in _l3 else ""
    check("[g5-1c] RETROFIT.md and RETROFIT-COMPANION.md map BOOTSTRAP.md to "
          "the current pair in a dated note on line 3",
          all(n and "`BOOTSTRAP.md`" in n and f"`{PROTOCOL_DOC}`" in n
              and f"`{PROTOCOL_COMPANION}`" in n for n in _line3.values()),
          _line3)

    # ----------------------------------------------------------------------- #
    # 2. The assumption ledger's links resolve; protocol_doc
    # ----------------------------------------------------------------------- #
    print("\n== 2. assumption ledger links and protocol_doc ==")
    LEDGER = ".claude/steering/assumption-ledger.md"
    _prd_text = open(_doc).read() if os.path.isfile(_doc) else ""
    for _n, (_cfg, _plan) in PLANS.items():
        _body = next(a["body"] for a in _plan if a["path"] == LEDGER)
        _src = _body[_body.find("## Source of truth"):]
        _state = RSTATE if _cfg.get("mode") == "retrofit" else STATE
        check(f"[{_n}] the source-of-truth section names the current "
              f"document", f"`{PROTOCOL_DOC}`" in _src, _src[:400])
        check(f"[{_n}] it says the document is not in this project and "
              f"where the install recorded it",
              "not with this project" in _src and "`protocol_doc`" in _src
              and f"`{_state}`" in _src, _src[:600])
        check(f"[{_n}] the token-multiplier row points at Phase 7 step 3",
              "**Subagent token multipliers** — Phase 7 step 3" in _src, _src)
        check(f"[{_n}] no row points the token-multiplier note at Phase 9.5",
              "Max-iterations and the subagent token-multiplier note"
              not in _src)
        check(f"[{_n}] 'the project changelog' no longer stands for the "
              f"toolchain's changelog",
              "see the project changelog" not in _body
              and "see `docs/changelog.md` in the Bootstrap Protocol "
                  "toolchain" in " ".join(_body.split()))
    for _anchor in ('### 6.E — Audio alert system',
                    '#### Drift detector specifics',
                    '### Max-iterations safety', '## Phase 9.5 ',
                    '3. Create subagent definitions under `.claude/agents/`. '
                    '**Cost disclosure first:**',
                    '5. Initialize `.claude/learnings/`'):
        check(f"the cited section exists in {PROTOCOL_DOC}: {_anchor[:48]}",
              _anchor in _prd_text)
    check("LIT-01 is stated at Phase 7 step 5 of the current document",
          any(ln.startswith("5. Initialize `.claude/learnings/`")
              and "LIT-01" in ln for ln in _prd_text.splitlines()))

    P = project("p")
    R = install(P, GATES_OFF)
    st = state_of(P)
    check("install exits 0", R.returncode == 0, R.stderr[-600:])
    check("[g5-2b] the state file records protocol_doc: the current "
          "document next to this installer",
          st.get("protocol_doc") == DOC_PATH, st.get("protocol_doc"))
    RP = project("rp")
    _rr = install(RP, RETRO)
    check("[g5-2b] a retrofit install records protocol_doc in "
          ".retrofit-state.json",
          _rr.returncode == 0
          and state_of(RP, RSTATE).get("protocol_doc") == DOC_PATH,
          (_rr.returncode, state_of(RP, RSTATE).get("protocol_doc"),
           _rr.stderr[-400:]))

    # [X6] A plugin copy carries the document as toolchain/protocol.md,
    # beside toolchain/lib. A copy of lib/ stands in for it here.
    TC = os.path.join(TMP, "toolchain")
    shutil.copytree(LIB, os.path.join(TC, "lib"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    _probe = ("import sys; sys.path.insert(0, sys.argv[1]); "
              "import installer; print(installer._protocol_doc_path())")

    def _doc_in_copy():
        r = run([sys.executable, "-c", _probe, os.path.join(TC, "lib")])
        return r.stdout.strip() if r.returncode == 0 else r.stderr[-200:]

    _none = _doc_in_copy()
    with open(os.path.join(TC, "protocol.md"), "w") as fh:
        fh.write("# copy\n")
    _plugin = _doc_in_copy()
    shutil.copy(_doc, os.path.join(TC, PROTOCOL_DOC))
    _both = _doc_in_copy()
    os.remove(os.path.join(TC, PROTOCOL_DOC))
    os.remove(os.path.join(TC, "protocol.md"))
    check("[X6] with no protocol document beside the toolchain, "
          "protocol_doc is null", _none == "None", _none)
    check("[X6] a plugin copy's toolchain/protocol.md is the recorded path",
          _plugin == os.path.join(os.path.realpath(TC), "protocol.md"),
          _plugin)
    check("[X6] the repository's own file wins when both are there",
          _both == os.path.join(os.path.realpath(TC), PROTOCOL_DOC), _both)

    # ----------------------------------------------------------------------- #
    # 3. Mark the bootstrap complete
    # ----------------------------------------------------------------------- #
    print("\n== 3. bootstrap complete ==")
    st_path = os.path.join(P, STATE)
    check("a fresh install records bootstrap_complete: false",
          st.get("bootstrap_complete") is False, st)
    st["bootstrap_complete"] = True
    st["bootstrap_completed_at"] = "2026-10-14T00:00:00Z"
    st["completed_phases"] = ["0", "0.5", "1", "9", "10"]
    st["skippable_phase_decisions"] = {"phase_9_smoke_test": "run"}
    with open(st_path, "w") as fh:
        json.dump(st, fh, indent=2)
    R2 = install(P)
    st2 = state_of(P)
    check("a re-install keeps bootstrap_complete, its time, "
          "completed_phases and the Phase 9 decision",
          R2.returncode == 0 and st2.get("bootstrap_complete") is True
          and st2.get("bootstrap_completed_at") == "2026-10-14T00:00:00Z"
          and st2.get("completed_phases") == ["0", "0.5", "1", "9", "10"]
          and st2.get("skippable_phase_decisions")
          == {"phase_9_smoke_test": "run"}, st2)
    # [WP4 fix round 1 / NF2] What the state file records is not offered
    # again: Claude relays the block and offers what it says.
    _ns2 = steps_of(R2.stdout)
    check("[NF2] once the state file records the Phase 9 decision and "
          "bootstrap_complete, Next steps offers neither the smoke test nor "
          "the completion line",
          R2.returncode == 0 and _ns2
          and not any("Smoke-test" in ln for ln in _ns2)
          and not any("record it, or ask Claude to" in ln for ln in _ns2)
          and any(templates.SPEC_START_CHAIN in ln for ln in _ns2),
          "\n".join(_ns2))
    # A state file written before the key existed: a re-install must not
    # claim that the bootstrap is incomplete.
    st2.pop("bootstrap_complete", None)
    with open(st_path, "w") as fh:
        json.dump(st2, fh, indent=2)
    R3 = install(P)
    st3 = state_of(P)
    check("a re-install over a state file without the key does not add it",
          R3.returncode == 0 and "bootstrap_complete" not in st3
          and st3.get("protocol_doc") == DOC_PATH, st3)
    check("the retrofit state file gets no bootstrap_complete (R7 marks "
          "retrofit_complete instead)",
          "bootstrap_complete" not in state_of(RP, RSTATE)
          and state_of(RP, RSTATE).get("retrofit_complete") is False)
    # [WP4 fix round 1 / C2] Git ignores the state file, so a re-install in
    # a fresh clone creates it too; false there would call a finished
    # project incomplete. Seeded only on a first install: no manifest, and
    # none of the plan's .claude/ files there but settings.json.
    if GIT:
        _gc = ["-c", "user.email=t@e.x", "-c", "user.name=t"]
        FS = project("finished")
        install(FS, GATES_OFF)
        _fs = state_of(FS)
        _fs["bootstrap_complete"] = True
        with open(os.path.join(FS, STATE), "w") as fh:
            json.dump(_fs, fh, indent=2)
        run([GIT, "-C", FS, "add", "-A"])
        run([GIT, "-C", FS, *_gc, "commit", "-q", "-m", "done"],
            env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"})
        FC = os.path.join(TMP, "finished-clone")
        run([GIT, "clone", "-q", FS, FC])
        _fc_bare = not os.path.exists(os.path.join(FC, STATE))
        _rfc = install(FC)
        check("[C2] a fresh clone of a finished project (no state file, no "
              "manifest): the re-install leaves bootstrap_complete absent, "
              "not false",
              _fc_bare and _rfc.returncode == 0
              and os.path.exists(os.path.join(FC, STATE))
              and "bootstrap_complete" not in state_of(FC), state_of(FC))
    else:                          # pragma: no cover
        print("  SKIP  git not found: the fresh-clone row (NOT measured)")
    OS = project("own-settings")
    os.makedirs(os.path.join(OS, ".claude"))
    with open(os.path.join(OS, ".claude", "settings.json"), "w") as fh:
        fh.write('{"env": {"MINE": "1"}}\n')
    _ros = install(OS, GATES_OFF)
    check("[C2] a first install over the project's own .claude/settings.json "
          "still seeds bootstrap_complete: false",
          _ros.returncode == 0 and state_of(OS).get("bootstrap_complete")
          is False, (_ros.returncode, state_of(OS)))

    # ----------------------------------------------------------------------- #
    # 4. Next steps: the stubs line, the smoke test, the completion line
    # ----------------------------------------------------------------------- #
    print("\n== 4. Next steps ==")
    ns = steps_of(R.stdout)
    line = stub_line(ns)
    smoke = next((i for i, ln in enumerate(ns) if "Smoke-test" in ln), -1)
    check("[X4] a fresh install names all four steering stubs, in a line "
          "before the smoke test",
          all(s in line for s in STUBS) and -1 < ns.index(line) < smoke
          if line else False, "\n".join(ns))
    check("[X4] it says where they are filled: Phases 1 to 8 of the protocol "
          "at the recorded protocol_doc path",
          f"(Phases 1 to 8 of {DOC_PATH})" in line
          and line.startswith("Before the smoke test, fill in the steering "
                              "docs with the operator")
          and line.endswith("are still the installer's stubs."), line)
    chain = next((i for i, ln in enumerate(ns)
                  if templates.SPEC_START_CHAIN in ln), -1)
    check("the Next steps block offers the Phase 9 smoke test before the "
          "chain, which it reuses",
          -1 < smoke < chain and "Phase 9" in ns[smoke], "\n".join(ns))
    check("it names the suggested-first row and /spec-validate",
          smoke > -1 and "suggested first" in ns[smoke]
          and "/spec-validate" in ns[smoke], ns[smoke] if smoke > -1 else ns)
    last = ns[-1] if ns else ""
    check("the last step: record it, or ask Claude to, in the state file",
          "record it, or ask Claude to" in last
          and ".claude/.bootstrap-state.json" in last, last)
    check("it names phase_9_smoke_test, the deferred_items to review, and "
          "bootstrap_complete, in that order",
          -1 < last.find("phase_9_smoke_test") < last.find("deferred_items")
          < last.find("bootstrap_complete"), last)

    Q = project("q")
    install(Q, GATES_OFF)
    with open(os.path.join(Q, STUBS[0]), "a") as fh:
        fh.write("\nFilled by Claude with the operator.\n")
    _q1 = stub_line(steps_of(install(Q).stdout))
    _q2 = stub_line(steps_of(install(Q).stdout))
    check("[X4] re-install after Claude filled product.md: it is not called "
          "a stub, and the other three are",
          STUBS[0] not in _q1 and all(s in _q1 for s in STUBS[1:]), _q1)
    check("[X4] a second re-install (the manifest now records the skip): "
          "product.md is still not called a stub",
          STUBS[0] not in _q2 and all(s in _q2 for s in STUBS[1:]), _q2)
    for _s in STUBS[1:]:
        with open(os.path.join(Q, _s), "a") as fh:
            fh.write("\nFilled.\n")
    _q3 = install(Q)
    check("[X4] with all four filled, there is no stubs line, and the smoke "
          "test is still offered",
          _q3.returncode == 0 and stub_line(steps_of(_q3.stdout)) == ""
          and any("Smoke-test" in ln for ln in steps_of(_q3.stdout)),
          _q3.stdout[-800:])

    _rns = steps_of(_rr.stdout)
    _rline = stub_line(_rns)
    check("[X4] retrofit: the stubs line cites RETROFIT.md R1 to R5.5 and "
          "R8.F, before the R6 smoke test",
          "(RETROFIT.md R1 to R5.5, and R8.F for ci-cd.md)" in _rline
          and all(s in _rline for s in STUBS)
          and -1 < _rns.index(_rline)
          < next((i for i, ln in enumerate(_rns) if "R6" in ln), -1)
          if _rline else False, "\n".join(_rns))
    _rlast = _rns[-1] if _rns else ""
    check("retrofit: the last step is R7 step 5, retrofit_complete in "
          ".claude/.retrofit-state.json, recorded or asked for",
          "R7" in _rlast and "step 5" in _rlast
          and "retrofit_complete" in _rlast
          and ".claude/.retrofit-state.json" in _rlast
          and "record it, or ask Claude to" in _rlast
          and not any("Phase 9" in ln for ln in _rns), "\n".join(_rns))
    # [WP4 fix round 1 / NF3] A clone re-installs from the config, so line
    # 1 has it committed too (a clone without it: "config not found").
    check("[NF3] line 1 says to commit bootstrap.config.yaml, which a clone "
          "needs to re-install, in both modes",
          all(ln and ln[0].startswith("Commit what the install wrote: ")
              and ln[0].endswith("Commit bootstrap.config.yaml with them: a "
                                 "clone needs it to re-install.")
              for ln in (ns, _rns)), (ns[:1], _rns[:1]))
    # [WP4 fix round 1 / NF2] Retrofit: R6's skip drops the smoke test, and
    # retrofit_complete drops the completion line too.
    _rst = state_of(RP, RSTATE)
    _rst["retrofit_complete"] = True
    _rst["retrofit_active"] = False
    with open(os.path.join(RP, RSTATE), "w") as fh:
        json.dump(_rst, fh, indent=2)
    _rdone = steps_of(install(RP).stdout)
    _rskip = steps_of(install(project("rp-r6skip"), RETRO.replace(
        "  r08_committed: true\n", "  r08_committed: true\n"
        "  skip_decisions:\n    R6_smoke_test: skip\n")).stdout)
    check("[NF2] retrofit: with retrofit_complete true, Next steps offers "
          "neither R6 nor the R7 completion line",
          _rdone and not any("R6" in ln for ln in _rdone)
          and not any("record it, or ask Claude to" in ln for ln in _rdone),
          "\n".join(_rdone))
    check("[NF2] retrofit: with R6 skipped in the config, no smoke-test line, "
          "and the completion line stays",
          _rskip and not any("Smoke-test" in ln for ln in _rskip)
          and "record it, or ask Claude to" in _rskip[-1],
          "\n".join(_rskip))

    # With no protocol document beside the toolchain, protocol_doc is null
    # and the stubs line names the document by its bare file name.
    N = project("n")
    with open(os.path.join(N, "bootstrap.config.yaml"), "w") as fh:
        fh.write(GATES_OFF)
    _rn = run([sys.executable, "-c",
               "import sys; sys.path.insert(0, sys.argv[1]); "
               "import installer; "
               "raise SystemExit(installer.main(sys.argv[2:]))",
               os.path.join(TC, "lib"), "-C", N])
    _nline = stub_line(steps_of(_rn.stdout))
    check("[X4] protocol_doc null: recorded as null, and the stubs line "
          "names the bare PROTOCOL_DOC",
          _rn.returncode == 0 and "protocol_doc" in state_of(N)
          and state_of(N)["protocol_doc"] is None
          and f"(Phases 1 to 8 of {PROTOCOL_DOC})" in _nline,
          (_rn.returncode, state_of(N).get("protocol_doc"), _nline,
           _rn.stderr[-300:]))

    # ----------------------------------------------------------------------- #
    # 5. One lock (8b)
    # ----------------------------------------------------------------------- #
    print("\n== 5. one install lock ==")
    check("EXIT_LOCKED is its own exit code (not 0, 1, 2 or 3), and the "
          "wait is 30 s", EXIT_LOCKED is not None
          and EXIT_LOCKED not in (0, 1, 2, 3)
          and getattr(installer, "_LOCK_WAIT_S", None) == 30,
          (EXIT_LOCKED, getattr(installer, "_LOCK_WAIT_S", None)))

    def held(proj, *rels):
        """Hold each lock from this process, as a loop wrapper would."""
        fhs = []
        for rel in rels:
            p = os.path.join(proj, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            fh = open(p, "a")
            fcntl.flock(fh, fcntl.LOCK_EX)
            fhs.append(fh)
        return fhs

    def patched_install(proj, *extra):
        t = time.monotonic()
        r = run([sys.executable, "-c", PATCHED_MAIN, LIB, "-c",
                 os.path.join(proj, "bootstrap.config.yaml"), "-C", proj,
                 *extra], timeout=120)
        return r, time.monotonic() - t

    if fcntl is None:              # pragma: no cover - not POSIX
        print("  SKIP  no fcntl on this platform: the installer takes no "
              "lock there (NOT measured)")
    else:
        L = project("lock")
        install(L, GATES_OFF)
        with open(os.path.join(L, "bootstrap.config.yaml"), "w") as fh:
            fh.write(GATES_OFF.replace('test: "true"', 'test: "pytest -q"'))
        _before = snapshot(L)
        _fhs = held(L, STATE + ".lock")
        try:
            _r, _el = patched_install(L)
            _after = snapshot(L)
            _rd, _eld = patched_install(L, "--dry-run")
        finally:
            for _fh in _fhs:
                _fh.close()
        check("a held .bootstrap-state.json.lock: exit EXIT_LOCKED, with "
              "the lock named", _r.returncode == EXIT_LOCKED
              and LOCK_HELD.format(STATE + ".lock") in _r.stderr,
              (_r.returncode, _r.stderr[-500:]))
        check("it gives up after the patched wait (about 1 s), not at once",
              1.0 <= _el < 15, f"{_el:.2f} s")
        check("nothing was written: every file, the git hooks included, is "
              "as it was", _after == _before,
              sorted(set(_after.items()) ^ set(_before.items()))[:6])
        check("--dry-run takes no lock: with the lock held it exits 0 "
              "without waiting", _rd.returncode == 0 and _eld < 15
              and "held by another process" not in _rd.stderr,
              (_rd.returncode, f"{_eld:.2f} s", _rd.stderr[-300:]))
        # Every earlier install left its lock file; nobody holds it.
        _t = time.monotonic()
        _rl = install(L)
        check("a lock file that no process holds never blocks: the install "
              "runs at once with the default 30 s wait",
              _rl.returncode == 0 and time.monotonic() - _t < 25
              and os.path.exists(os.path.join(L, STATE + ".lock")),
              (_rl.returncode, _rl.stderr[-300:]))
        check("the state file and the manifest were written under the lock "
              "(the config change reached the test gate)",
              "pytest -q" in (read(L, ".claude/hooks/test-gate.sh") or ""))

        RL = project("rlock")
        install(RL, RETRO)
        check("retrofit: a real install leaves both lock files, which the "
              "emitted .claude/.gitignore covers",
              all(os.path.exists(os.path.join(RL, rel + ".lock"))
                  and (not GIT or ignored(RL, rel + ".lock"))
                  for rel in (STATE, RSTATE)))
        _rbefore = snapshot(RL)
        _fhs = held(RL, RSTATE + ".lock")
        try:
            _r2, _ = patched_install(RL)
        finally:
            for _fh in _fhs:
                _fh.close()
        check("retrofit: a held .retrofit-state.json.lock exits "
              "EXIT_LOCKED and writes nothing",
              _r2.returncode == EXIT_LOCKED
              and LOCK_HELD.format(RSTATE + ".lock") in _r2.stderr
              and snapshot(RL) == _rbefore,
              (_r2.returncode, _r2.stderr[-400:]))
        _fhs = held(RL, STATE + ".lock", RSTATE + ".lock")
        try:
            _r3, _ = patched_install(RL)
        finally:
            for _fh in _fhs:
                _fh.close()
        check("retrofit takes .bootstrap-state.json.lock first: with both "
              "held, that is the one named",
              _r3.returncode == EXIT_LOCKED
              and LOCK_HELD.format(STATE + ".lock") in _r3.stderr
              and RSTATE + ".lock" not in _r3.stderr,
              (_r3.returncode, _r3.stderr[-400:]))

    # P's lock file came from its own installs; this test never opened it.
    if fcntl is not None:
        _ru = install(P, None, "--uninstall")
        check("--uninstall leaves the lock file an install took",
              _ru.returncode == 0
              and os.path.exists(os.path.join(P, STATE + ".lock")),
              _ru.stdout[-300:])

    # ----------------------------------------------------------------------- #
    # 6. The parse guard (ruling 12 (a))
    # ----------------------------------------------------------------------- #
    print("\n== 6. a state file that does not parse ==")

    def copies(proj, rel):
        d, base = os.path.split(os.path.join(proj, rel))
        return sorted(f for f in os.listdir(d)
                      if f.startswith(base + ".pre-unparsed-"))

    def break_state(proj, rel, extra):
        s = state_of(proj, rel)
        s.update(extra)
        text = json.dumps(s, indent=2)
        text = text[:text.rindex("}")] + ",}\n"     # a trailing comma
        with open(os.path.join(proj, rel), "w") as fh:
            fh.write(text)
        return text

    G = project("guard")
    install(G, GATES_OFF)
    _bad1 = break_state(G, STATE, {"bootstrap_complete": True,
                                   "completed_phases": ["0", "1"]})
    _g1 = install(G)
    _c1 = copies(G, STATE)
    _w1 = [w for w in warnings_of(_g1) if "pre-unparsed" in w]
    check("re-install over a state file with a trailing comma exits 0",
          _g1.returncode == 0, _g1.stderr[-500:])
    check("it keeps one copy, named <state>.pre-unparsed-<UTC stamp>, "
          "byte for byte the broken file",
          len(_c1) == 1
          and re.fullmatch(r"\.bootstrap-state\.json\.pre-unparsed-"
                           r"\d{8}T\d{6}Z", _c1[0])
          and read(G, ".claude/" + _c1[0]) == _bad1, _c1)
    check("one warning: line names the copy and says the dropped keys can "
          "be restored from it",
          len(_w1) == 1 and _c1 and f".claude/{_c1[0]}" in _w1[0]
          and "dropped" in _w1[0] and "restore" in _w1[0], _w1)
    check("the warning names only the timestamped copy, not IC-3's "
          ".pre-2.0.0 backup", _w1 and ".pre-2.0.0" not in _w1[0], _w1)
    _g1st = state_of(G)
    check("bootstrap_complete is absent (not false) after a parse failure, "
          "and the config's keys are written again",
          "bootstrap_complete" not in _g1st
          and "completed_phases" not in _g1st
          and _g1st.get("archetype") == "fullstack"
          and _g1st.get("protocol_doc") == DOC_PATH, _g1st)
    check("git ignores the copy (the greenfield .gitignore's "
          "`.bootstrap-state.json.pre-*` line)",
          bool(GIT) and _c1 and ignored(G, ".claude/" + _c1[0]), _c1)
    _bad2 = break_state(G, STATE, {"note": "second typo"})
    _g2 = install(G)
    _c2 = copies(G, STATE)
    _new = sorted(set(_c2) - set(_c1))
    check("a second failure keeps a second, distinct copy, and the first "
          "is untouched",
          _g2.returncode == 0 and len(_c2) == 2 and len(_new) == 1
          and read(G, ".claude/" + _new[0]) == _bad2
          and read(G, ".claude/" + _c1[0]) == _bad1, _c2)
    _n = len(copies(G, STATE))
    with open(os.path.join(G, STATE), "w") as fh:
        fh.write("[]\n")
    _g3 = install(G)
    check("a state file that parses but holds no object (a JSON list) is "
          "kept and warned about too, not a traceback",
          _g3.returncode == 0 and len(copies(G, STATE)) == _n + 1
          and "Traceback" not in _g3.stderr
          and len([w for w in warnings_of(_g3) if "pre-unparsed" in w]) == 1
          and state_of(G).get("archetype") == "fullstack",
          (_g3.returncode, _g3.stderr[-500:]))
    _n = len(copies(G, STATE))
    with open(os.path.join(G, STATE), "w") as fh:
        fh.write("")
    _g4 = install(G)
    check("an empty state file holds no key, so it gets no copy and no "
          "warning", _g4.returncode == 0 and len(copies(G, STATE)) == _n
          and not [w for w in warnings_of(_g4) if "pre-unparsed" in w],
          warnings_of(_g4))

    RG = project("rguard")
    install(RG, RETRO)
    _rbad = break_state(RG, RSTATE, {"retrofit_complete": True,
                                     "retrofit_active": False})
    _rg = install(RG)
    _rc = copies(RG, RSTATE)
    _rw = [w for w in warnings_of(_rg) if "pre-unparsed" in w]
    check("retrofit: the same guard keeps a copy of .retrofit-state.json "
          "and names it", _rg.returncode == 0 and len(_rc) == 1
          and read(RG, ".claude/" + _rc[0]) == _rbad
          and len(_rw) == 1 and f".claude/{_rc[0]}" in _rw[0],
          (_rc, _rw, _rg.stderr[-400:]))
    check("retrofit: git ignores the copy (the retrofit .gitignore's "
          "`.retrofit-state.json.pre-*` line)",
          bool(GIT) and _rc and ignored(RG, ".claude/" + _rc[0]), _rc)
    # [WP4 fix round 1 / C1] The rewrite resets keys both files hold, not
    # only the ones the old file alone held, and the warning says so.
    _rgst = state_of(RG, RSTATE)
    _gw = [w for w in warnings_of(_g1) if "pre-unparsed" in w]
    check("[C1] the warning says the new file holds only the config's values "
          "and empty defaults, so keys were dropped or reset, and names the "
          "operator's runtime keys, in each mode; retrofit_active and "
          "retrofit_complete were in fact reset",
          _gw and _rw
          and all("holds only the config's values and empty defaults, so "
                  "every key the old one held was dropped or reset" in w[0]
                  for w in (_gw, _rw))
          and all(f"`{k}`" in _gw[0] for k in (
              "bootstrap_complete", "completed_phases",
              "skippable_phase_decisions", "deferred_items"))
          and "`retrofit_active` and `retrofit_complete`" in _rw[0]
          and _rgst.get("retrofit_active") is True
          and _rgst.get("retrofit_complete") is False,
          (_gw, _rw, {k: _rgst.get(k) for k in ("retrofit_active",
                                                 "retrofit_complete")}))

    # ----------------------------------------------------------------------- #
    # 7. The interactive interviews (8c)
    # ----------------------------------------------------------------------- #
    print("\n== 7. interactive with no terminal ==")

    def retro_project(name):
        """A small committed repository for retrofit-interview to scan, as
        tests/test_retrofit.py's _mkproj makes one."""
        d = project(name)
        os.makedirs(os.path.join(d, "src"))
        with open(os.path.join(d, "src", "main.py"), "w") as fh:
            fh.write("def hello():\n    return 1\n")
        with open(os.path.join(d, "pyproject.toml"), "w") as fh:
            fh.write('[project]\nname = "demo"\nversion = "0.1.0"\n')
        if GIT:
            run([GIT, "-C", d, "add", "-A"])
            run([GIT, "-C", d, "-c", "user.email=t@e.x", "-c", "user.name=t",
                 "commit", "-q", "-m", "init"])
        return d

    def tools(name):
        """(tool, argv, project dir, config path) for both interviews."""
        g = project(name + "-g", git=False)
        r = retro_project(name + "-r")
        return (("bootstrap-interview",
                 [sys.executable, INTERVIEW, "interactive", "--prd",
                  SAMPLE_PRD, "-o", os.path.join(g, "c.yaml")],
                 g, os.path.join(g, "c.yaml")),
                ("retrofit-interview",
                 [sys.executable, RETRO_INTERVIEW, "interactive", "-C", r,
                  "-o", "c.yaml"], r, os.path.join(r, "c.yaml")))

    def env_t(t):
        return dict(os.environ, BOOTSTRAP_PROMPT_TIMEOUT=str(t))

    def no_inventory(d):
        return not os.path.exists(os.path.join(d, ".claude", "inventory"))

    for tool, argv, d, cfg in (tools("closed") if BASH else ()):
        r = run([BASH, "-c", 'exec "$0" "$@" <&-'] + argv, timeout=60)
        check(f"[{tool}] stdin closed (fd 0): rc 2, the refusal, no config "
              f"and no inventory", r.returncode == 2
              and f"error: {tool} interactive: stdin is empty or closed; "
                  f"no config written. {HINT}" in r.stderr
              and not os.path.exists(cfg) and no_inventory(d),
              (r.returncode, r.stderr[-400:]))
    if not BASH:                   # pragma: no cover
        print("  SKIP  bash not found: the closed-fd rows (NOT measured)")
    _eof = {}
    for tool, argv, d, cfg in tools("devnull"):
        r = run(argv, stdin=subprocess.DEVNULL, timeout=60)
        _eof[tool] = (r, d, cfg)
        check(f"[{tool}] stdin is /dev/null (the Bash tool's, with no "
              f"redirect): rc 2, no config and no inventory",
              r.returncode == 2
              and f"error: {tool} interactive: stdin is empty or closed; "
                  f"no config written. {HINT}" in r.stderr
              and not os.path.exists(cfg) and no_inventory(d),
              (r.returncode, r.stderr[-400:]))

    # [g3 EOF TRUTH rows, inverted; review scope F4, DOC-1] g3's records
    # pinned "interactive at end of input writes a config of defaults with
    # rc 0", the reason its route notes kept Claude off the command. Since
    # 8c both interviews refuse. Each /dev/null run above (stdin at end of
    # file) is paired here with the For-the-AI note that now says so: the
    # protocol's (its line 283) and RETROFIT.md's (its line 9).
    def for_the_ai_note(rel, verb):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            hits = [ln for ln in fh.read().split("\n") if ln.startswith(
                "> **For the AI:** When the operator opens this file and "
                "asks you to " + verb)]
        ln = hits[0] if len(hits) == 1 else ""
        return ln[ln.find(ROUTE_NOTE):] if ROUTE_NOTE in ln else ""

    for tool, rel, verb, says in (
            ("bootstrap-interview", PROTOCOL_DOC, "bootstrap",
             "with no terminal, it writes no config and exits 2"),
            ("retrofit-interview", "RETROFIT.md", "retrofit",
             "with no terminal, it writes no config and no inventory and "
             "exits 2")):
        r, d, cfg = _eof.get(tool, (None, TMP, os.path.join(TMP, "-")))
        note = for_the_ai_note(rel, verb)
        check(f"[g3 EOF TRUTH, inverted] {tool} interactive with stdin at "
              f"end of file exits 2 and writes no config"
              + (" and no .claude/inventory/" if verb == "retrofit" else "")
              + f", as {rel}'s For-the-AI note says",
              r is not None and r.returncode == 2 and not os.path.exists(cfg)
              and no_inventory(d)
              and f"Don't run `{tool} interactive` yourself" in note
              and says in note
              and "input that ends early takes the remaining defaults and "
                  "says so" in note
              and "accepts every" not in note.lower(),
              (r and r.returncode, note[:600]))
    _silent, _partial = {}, {}            # read again by section 9
    for tool, argv, d, cfg in tools("silent"):
        t0 = time.monotonic()
        p = subprocess.Popen(argv, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, env=env_t(1))
        try:
            p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
        el = time.monotonic() - t0
        p.stdin.close()
        err = p.stderr.read()
        p.stdout.close()
        p.stderr.close()
        _silent[tool] = (p.returncode, err, not os.path.exists(cfg))
        check(f"[{tool}] an open pipe that never answers, "
              f"BOOTSTRAP_PROMPT_TIMEOUT=1: rc 2 in about 1 s, no config, "
              f"no inventory", p.returncode == 2 and 1.0 <= el < 10
              and f"error: {tool} interactive: no answer arrived within 1 s "
                  f"and stdin is not a terminal; no config written. {HINT}"
              in err and not os.path.exists(cfg) and no_inventory(d),
              (p.returncode, f"{el:.2f} s", err[-400:]))
    for tool, argv, d, cfg in tools("full"):
        t0 = time.monotonic()
        r = run(argv, input="\n" * 80, env=env_t(60), timeout=120)
        el = time.monotonic() - t0
        body = open(cfg).read() if os.path.exists(cfg) else ""
        check(f"[{tool}] a closed pipe with every answer: rc 0 at once (well "
              f"inside a 60 s limit), no warning, the usual header",
              r.returncode == 0 and el < 30 and not warnings_of(r)
              and "took their proposed default" not in body
              and body.startswith(f"# GENERATED BY bin/{tool}"),
              (r.returncode, f"{el:.2f} s", r.stderr[-300:]))
    for tool, argv, d, cfg in tools("partial"):
        r = run(argv, input="\n" * 3, timeout=120)
        body = open(cfg).read() if os.path.exists(cfg) else ""
        head = " ".join(ln[1:].strip() for ln in body.splitlines()
                        if ln.startswith("#"))
        m = re.search(r"took their proposed default without being "
                      r"answered: (.*?)\.(?: |$)", head)
        named = [k.strip() for k in m.group(1).split(",")] if m else []
        first = ("prd_path" if tool == "bootstrap-interview"
                 else "principles_ranked")
        _partial[tool] = (r.returncode, warnings_of(r), named)
        check(f"[{tool}] input that ends after 3 answers: rc 0, and one "
              f"warning: line says so",
              r.returncode == 0
              and f"warning: {tool} interactive: input ended after 3 "
                  f"answer(s); every later question took its proposed "
                  f"default without being answered." in r.stderr,
              (r.returncode, r.stderr[-400:]))
        check(f"[{tool}] the config header names the values that took "
              f"their defaults: the 4th question's on, none of the 3 "
              f"answered", named[:1] == [first] and "commands_test" in named
              and not {"project_name", "archetype"} & set(named)
              and "input ended after 3 answer(s)" in head.lower()
              and "Every value here was shown" not in head, head)

    # [WP4 fix round 1 / C4] In a terminal. A tty's end of input is not
    # sticky: after Ctrl-D the next read waits for more, so Ctrl-D at the
    # first prompt wrote a config, and Ctrl-D later gave a warning and a
    # header that named answers the operator then typed. Each row types on a
    # pseudo-terminal, as a person at a keyboard does.
    def named_defaults(body):
        head = " ".join(ln[1:].strip() for ln in body.splitlines()
                        if ln.startswith("#"))
        m = re.search(r"took their proposed default without being "
                      r"answered: (.*?)\.(?: |$)", head)
        return [k.strip() for k in m.group(1).split(",")] if m else []

    def on_pty(argv, keys):
        """Run `argv` with a pseudo-terminal for stdin and stdout. `keys`
        maps a prompt's number (1-based) to the bytes typed at it; every
        other prompt gets Enter. Returns (rc, stderr, prompts seen)."""
        m, s = pty.openpty()
        p = subprocess.Popen(argv, stdin=s, stdout=s, stderr=subprocess.PIPE,
                             close_fds=True)
        os.close(s)
        buf, seen, t0 = b"", 0, time.monotonic()
        while time.monotonic() - t0 < 120:
            r, _, _ = select.select([m], [], [], 0.1)
            if r:
                try:
                    buf += os.read(m, 65536)
                except OSError:          # the child closed the terminal
                    r = None
            while seen < buf.count(b"] > "):
                seen += 1
                try:
                    os.write(m, keys.get(seen, b"\r"))
                except OSError:
                    pass
            if p.poll() is not None and not r:
                break
        if p.poll() is None:
            p.kill()
        err = p.communicate()[1].decode(errors="replace")
        os.close(m)
        return p.returncode, err, seen

    if pty is None:                # pragma: no cover - not POSIX
        print("  SKIP  pty not available: the terminal rows (NOT measured)")
    for tool, argv, d, cfg in (tools("tty1") if pty else ()):
        rc, err, seen = on_pty(argv, {1: b"\x04"})
        check(f"[{tool}] in a terminal, Ctrl-D at the first prompt: rc 2, "
              f"the zero-answer refusal, no config",
              rc == 2
              and f"error: {tool} interactive: stdin is empty or closed; "
                  f"no config written. {HINT}" in err
              and not os.path.exists(cfg), (rc, seen, err[-400:]))
    for (tool, argv, d, cfg), (_t, pargv, _pd, pcfg) in (
            zip(tools("tty2"), tools("pipe1")) if pty else ()):
        rc, err, seen = on_pty(argv, {2: b"\x04", 3: b"an override\r"})
        body = open(cfg).read() if os.path.exists(cfg) else ""
        pr = run(pargv, input="\n", timeout=120)
        pbody = open(pcfg).read() if os.path.exists(pcfg) else ""
        check(f"[{tool}] in a terminal, Ctrl-D at the second prompt ends the "
              f"input: nothing typed later is read, the warning counts one "
              f"answer, and the header names every later question's key, as "
              f"a pipe that ends after one answer does",
              rc == 0 and pr.returncode == 0
              and f"warning: {tool} interactive: input ended after 1 "
                  f"answer(s);" in err
              and "an override" not in body
              and len(named_defaults(body)) > 1
              and named_defaults(body) == named_defaults(pbody),
              (rc, seen, err[-300:], named_defaults(body),
               named_defaults(pbody)))

    # [WP4 fix round 1 / C5] BOOTSTRAP_PROMPT_TIMEOUT values that parse as
    # floats but select() cannot take (negative, infinite, NaN; 1e400 reads
    # as infinity) skipped the refusal, so a silent pipe hung. They take the
    # default now. All run at once: each waits out the default 30 s.
    _odd = ("-1", "inf", "nan", "1e400")
    _procs = []
    for val in _odd:
        for tool, argv, d, cfg in tools("odd" + val.replace(".", "")):
            _procs.append((val, tool, cfg, time.monotonic(), subprocess.Popen(
                argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE, text=True, env=env_t(val))))
    for val, tool, cfg, t0, p in _procs:
        try:
            p.wait(timeout=max(1, 50 - (time.monotonic() - t0)))
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
        el = time.monotonic() - t0
        p.stdin.close()
        err = p.stderr.read()
        p.stderr.close()
        check(f"[{tool}] BOOTSTRAP_PROMPT_TIMEOUT={val}, a pipe that never "
              f"answers: rc 2 after the default 30 s, no config",
              p.returncode == 2 and 29 <= el < 50
              and "no answer arrived within 30 s" in err
              and not os.path.exists(cfg),
              (p.returncode, f"{el:.2f} s", err[-300:]))

    # The wait each value asks select() for, without waiting: "abc" and ""
    # still fall back to 30, "0" still refuses at once, and a huge value is
    # capped where select() can still wait.
    class _SilentPipe:
        def isatty(self):
            return False

        def fileno(self):
            return 0

    _asked = {}

    def _record(rlist, wlist, xlist, timeout):
        _asked[_val] = timeout
        return [], [], []

    _saved = (IV.select.select, sys.stdin,
              os.environ.get("BOOTSTRAP_PROMPT_TIMEOUT"))
    try:
        IV.select.select, sys.stdin = _record, _SilentPipe()
        for _val in ("abc", "", "0", "-1", "inf", "nan", "1e400", "1e12"):
            os.environ["BOOTSTRAP_PROMPT_TIMEOUT"] = _val
            IV._stdin_refusal("bootstrap-interview")
    finally:
        IV.select.select, sys.stdin = _saved[0], _saved[1]
        if _saved[2] is None:
            os.environ.pop("BOOTSTRAP_PROMPT_TIMEOUT", None)
        else:
            os.environ["BOOTSTRAP_PROMPT_TIMEOUT"] = _saved[2]
    _cap = getattr(IV, "_MAX_PROMPT_WAIT", None)
    check("the wait select() is given: 'abc', '' and the four odd values "
          "30 s, '0' none, and 1e12 capped below select()'s limit",
          all(_asked.get(v) == 30.0 for v in ("abc", "", "-1", "inf", "nan",
                                              "1e400"))
          and _asked.get("0") == 0.0 and _cap is not None
          and _asked.get("1e12") == _cap == 2.0 ** 31 - 1, _asked)

    # ----------------------------------------------------------------------- #
    # 8. --force --dry-run says what would be saved (DOC-2)
    # ----------------------------------------------------------------------- #
    print("\n== 8. --force --dry-run ==")
    D = project("force")
    install(D, GATES_OFF)
    with open(os.path.join(D, STUBS[0]), "a") as fh:
        fh.write("\nAn edit.\n")
    _fd = install(D, None, "--force", "--dry-run")
    check("--force --dry-run: the UPDATE line says where the previous "
          "version would be saved, in the conditional",
          _fd.returncode == 0
          and f"UPDATE {STUBS[0]}  (forced; previous version would be saved "
              f"to .claude/.installer-backups/" in _fd.stdout
          and "previous version saved to" not in _fd.stdout,
          _fd.stdout[-600:])
    check("--force --dry-run: the summary says --force would displace it, "
          "and nothing was saved",
          "--force would displace 1 file(s)" in _fd.stdout
          and "--force displaced" not in _fd.stdout
          and not os.path.exists(os.path.join(D, ".claude",
                                              ".installer-backups")),
          _fd.stdout[-600:])
    _ff = install(D, None, "--force")
    check("--force on its own still says what it saved, in the past tense",
          _ff.returncode == 0 and "previous version saved to" in _ff.stdout
          and "--force displaced 1 file(s)" in _ff.stdout
          and os.path.isdir(os.path.join(D, ".claude",
                                         ".installer-backups")),
          _ff.stdout[-600:])

    # ----------------------------------------------------------------------- #
    # 9. The README (commit 8)
    # ----------------------------------------------------------------------- #
    print("\n== 9. the README ==")
    # The live text is everything above the review history; a history entry
    # may quote what was true when it was written.
    _cut = README.find("\n## Review history\n")
    RM = README[:_cut] if _cut >= 0 else README
    RMF = flat(RM)
    _lines = README.split("\n")
    _heads = md_headings(RM)
    _h2 = [t for lv, t, _ in _heads if lv == 2]
    _gs = next((i for lv, t, i in _heads if t == "Getting started"), -1)
    _intro = next((i for i, ln in enumerate(_lines)
                   if ln.startswith("This answers the question")), -1)
    _above = [h for h in _heads if h[2] < _intro]
    _two = next((i for lv, t, i in _heads if t == "The two layers"), -1)
    check("[X1] '## Getting started' is the first section, right after the "
          "banner; the introduction follows it under its own '## ' heading, "
          "before '## The two layers'",
          _h2[:1] == ["Getting started"]
          and all(ln.startswith(">") for ln in _lines[1:_gs] if ln.strip())
          and -1 < _gs < _intro < _two and _above
          and _above[-1][0] == 2 and _above[-1][1] != "Getting started",
          (_h2[:3], _gs, _intro, _above[-1:] if _above else None))
    _slugs = {slug(t) for _, t, _ in md_headings(README)}
    _links = re.findall(r"\]\(#([^)]+)\)", README)
    check("every #anchor link in the README names a heading, and the README "
          "links Getting started",
          _links and "getting-started" in _links
          and all(a in _slugs for a in _links),
          sorted(set(a for a in _links if a not in _slugs)))

    # [Plan item 8; D1 (c)] The banner keeps the pin it had (AC-A0-1 in
    # tests/test_installer.py pins those words) and a dated correction
    # sends readers of Getting started to `main`.
    _banner = "\n".join(_lines[:_gs]) if _gs > 0 else ""
    _corr = next((ln for ln in _banner.split("\n")
                  if "*Correction (WP4, 2026-10-14):*" in ln), "")
    _bflat = flat(_banner.replace("\n>", "\n"))
    _tag = re.search(r"The `(v\d+\.\d+\.\d+)` tag predates that route",
                     _bflat)
    _pv = templates.PROTOCOL_VERSION
    check("[banner] the release and pin lines stay, and a dated correction "
          "inside the banner says Getting started needs a clone of `main`, "
          "because the release tag predates the route",
          _corr.startswith("> ") and f"Current release: v{_pv}." in _banner
          and f"pin the annotated git tag `v{_pv}`" in _banner
          and "*Correction (WP4, 2026-10-14):* to follow [Getting started]"
              "(#getting-started), use a clone of `main`." in _bflat
          and _tag is not None and _tag.group(1) == f"v{_pv}", _bflat[:900])
    _tagname = _tag.group(1) if _tag else f"v{_pv}"
    _have_tag = GIT and run([GIT, "-C", ROOT, "rev-parse", "-q", "--verify",
                             f"refs/tags/{_tagname}^{{commit}}"]
                            ).returncode == 0
    if _have_tag:
        _tag_inst = run([GIT, "-C", ROOT, "show",
                         f"{_tagname}:lib/installer.py"])
        _tag_doc = run([GIT, "-C", ROOT, "cat-file", "-e",
                        f"{_tagname}:{PROTOCOL_DOC}"])
        check(f"[banner, TRUTH] at the {_tagname} tag the installer prints "
              f"no Next steps block and {PROTOCOL_DOC} does not exist, as "
              f"the correction says",
              _tag_inst.returncode == 0
              and "Next steps:" not in _tag_inst.stdout
              and _tag_doc.returncode != 0,
              (_tag_inst.returncode, _tag_doc.returncode))
    else:
        print(f"  SKIP  [banner, TRUTH] no {_tagname} tag in this clone (a "
              f"shallow CI checkout fetches none): NOT measured")
    _HIST = ("carries seven",
             "Can Bootstrap-Protocol-v2-0-0.md be a Claude Code plugin")
    _old = [f"README.md:{i}: {ln.strip()[:90]}"
            for i, ln in enumerate(RM.split("\n"), 1)
            if set(NAME_RE.findall(ln)) - CURRENT
            and not any(h in ln for h in _HIST)]
    check("[g5-1c] above its review history the README names no old "
          "protocol file, except where two lines quote history", not _old,
          "\n        ".join(_old))
    check("[g5-1c] the banner no longer says the current file name is "
          "v2-6-0, and dates the rename as the protocol's filename note does",
          "Why the filename says `v2-6-0`" not in RM
          and "\n> v2-6-0 pair now." not in RM
          and "This pair was cut as `v2-6-0` and renamed `v2-8-0` on "
              "2026-08-14" in _bflat
          and "Since 2026-08-14 this file is named `v2-8-0`" in _prd_text,
          _bflat[:300])

    # [D1 (c), g3-1] The new-project route, in order, against the tools.
    _new = flat(md_section(README, "Bootstrap a new project"))
    _order = [f"Read `$T/{PROTOCOL_DOC}` and bootstrap this project.",
              '`python3 "$T/bin/bootstrap-interview" analyze --prd <your '
              'PRD>`', "the ANSWERS block of `bootstrap.interview.md`",
              '`python3 "$T/bin/bootstrap-interview" synthesize`',
              '`python3 "$T/bin/bootstrap-install" --dry-run`',
              'Claude runs `python3 "$T/bin/bootstrap-install"`',
              "Claude runs Phases 1 to 8", "Phase 9 smoke test"]
    _pos = [_new.find(p) for p in _order]
    check("[D1 (c)] Getting started's new-project steps name the current "
          "protocol, analyze, the ANSWERS block, synthesize, the dry run, "
          "the install, Phases 1 to 8 and the smoke test, in that order",
          -1 not in _pos and _pos == sorted(_pos),
          [p for p, at in zip(_order, _pos) if at < 0] or _pos)
    _h_iv = run([sys.executable, INTERVIEW, "--help"]).stdout
    _h_an = run([sys.executable, INTERVIEW, "analyze", "--help"]).stdout
    _h_ia = run([sys.executable, INTERVIEW, "interactive", "--help"]).stdout
    _h_in = run([sys.executable, INSTALL, "--help"]).stdout
    _h_ri = run([sys.executable, RETRO_INTERVIEW, "--help"]).stdout
    check("[D1 (c), TRUTH] every subcommand and flag the README's routes "
          "name is one the tools accept",
          all(c in _h_iv for c in ("analyze", "synthesize", "interactive"))
          and "--prd" in _h_an and "--prd" in _h_ia
          and all(f in _h_in for f in ("--dry-run", "--force", "--adopt"))
          and all(c in _h_ri for c in ("analyze", "synthesize",
                                       "interactive")),
          (_h_iv[:200], _h_in[:200]))
    check("[g3-1] the route says the install writes the four steering docs "
          "as stubs and Next steps names each one still a stub; a fresh "
          "install's stubs line names the same four",
          all(f"`{os.path.basename(s)}`" in _new for s in STUBS)
          and "under `.claude/steering/` as stubs, and `Next steps:` names "
              "each one that is still a stub" in _new
          and all(s in line for s in STUBS), (_new[:300], line))
    check("[g5-4] the route's last step says what the install's last Next "
          "steps line says: record it, or ask Claude to, in the state file",
          "`.claude/.bootstrap-state.json`: record it, or ask Claude to."
          in _new and "record it, or ask Claude to" in last
          and ".claude/.bootstrap-state.json" in last, last)
    check("[ruling 12 (a)] the README names the parse guard's copy as the "
          "guard writes it, and the warning that names it",
          "`.claude/.bootstrap-state.json.pre-unparsed-<UTC stamp>`" in RMF
          and "prints a `warning:` line that names the copy" in RMF
          and "Restore them from the copy." in RMF
          and bool(_c1) and re.fullmatch(
              r"\.bootstrap-state\.json\.pre-unparsed-\d{8}T\d{6}Z", _c1[0])
          and bool(_w1) and "restore" in _w1[0], (_c1, _w1))

    # [X9, build F5] Approvals under .claude/, and claude -p.
    _ap = flat(md_section(README, "Approve Claude's writes under `.claude/`"))
    _esc = next((a["body"] for a in PLANS["default"][1]
                 if a["path"] == ".claude/skills/escalate/SKILL.md"), "")
    check("[X9] Claude Code asks for each write under .claude/ in an "
          "interactive session, denies Write and Edit there under claude -p, "
          "and D5 is open; the protocol's route note says the same",
          all(p in _ap for p in (
              "Run the route in an interactive session.",
              "asks you to approve each of those writes, so expect to "
              "approve the steering docs one at a time",
              "Under `claude -p`, Claude Code denies Claude's Write and Edit "
              "tools there", "decision D5, which is open"))
          and "as it does under `claude -p` until D5 is decided" in _prd_text,
          _ap[:600])
    check("[build F5] the README puts the escalate record under the same "
          "rule, and the skill writes it under .claude/sessions/",
          "the `escalate` skill writes under `.claude/sessions/`" in _ap
          and "/.claude/sessions/.decision-pending-" in _esc, _ap[-300:])

    # [KEEP-1, NF-1, DOC-2] One skipped file: the per-file remedy, measured
    # in a real fresh clone (git ignores the manifest and the state file).
    _ri = flat(md_section(README, "Re-install after a change"))
    check("[NF3] the README says to commit bootstrap.config.yaml, because "
          "a clone needs it to re-install, as Next steps line 1 does",
          "Commit `bootstrap.config.yaml`, because a clone needs it to "
          "re-install." in _ri
          and "Commit bootstrap.config.yaml with them: a clone needs it to "
              "re-install." in (ns[0] if ns else ""), _ri[:500])
    check("[KEEP-1] the README gives the per-file remedy and says why not "
          "--adopt", all(p in _ri for p in (
              "move that file aside and re-install: the install re-creates "
              "only that file", "This works in a fresh clone too",
              "Don't use `--adopt` for this: it records every skipped file "
              "as the installer's, so the next install replaces each "
              "steering doc you or Claude filled in, with no backup.")),
          _ri[:700])
    _adopt = [s for s in sentences(RM) if "--adopt" in s]
    check("[KEEP-1, NF-1] no --adopt advice above the review history: each "
          "sentence that names --adopt says what it costs (no backup)",
          _adopt and all("with no backup" in s for s in _adopt)
          and not any(p in RMF for p in (
              "Re-run normally afterwards", "--adopt` and a re-install",
              "--adopt then", "run with `--adopt`", "with --adopt and")),
          [s for s in _adopt if "with no backup" not in s])
    _force = [s for s in sentences(RM)
              if re.search(r"(?:^|\s)(?:[Rr]uns?|[Uu]ses?|[Pp]ass(?:es)?)\s[^.]*?"
                           r"`(?:bootstrap-install\s+)?--force`", s)
              and "--dry-run" not in s and not s.startswith("Don't")]
    check("no --force advice above the review history", not _force
          and not any(p in RMF for p in (
              "run `bootstrap-install --force`", "run it again with "
              "`--force`", "with `--force` before")), _force)
    _fdry = [s for s in sentences(RM) if "--force --dry-run" in s]
    check("[DOC-2] each README sentence about --force --dry-run speaks in "
          "the conditional, as the installer now prints it",
          _fdry and all("would" in s for s in _fdry)
          and "would be saved to" in _ri
          and "previous version would be saved to" in _fd.stdout
          and "--force would displace" in _fd.stdout,
          _fdry)

    if GIT:
        _gc = ["-c", "user.email=t@e.x", "-c", "user.name=t"]
        K = project("clone-src")
        install(K, GATES_OFF)
        with open(os.path.join(K, STUBS[0]), "a") as fh:
            fh.write("\nFilled by Claude with the operator.\n")
        with open(os.path.join(K, STUBS[3]), "a") as fh:
            fh.write("\nA stale line an earlier install wrote.\n")
        run([GIT, "-C", K, "add", "-A"])
        # A person's commit: the installed spec check reads only agent
        # commits (CLAUDECODE=1), so leave that out of the environment.
        run([GIT, "-C", K, *_gc, "commit", "-q", "-m", "filled"],
            env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"})
        _filled = read(K, STUBS[0])
        _plan_ci = next(a["body"] for a in PLANS["gates_off"][1]
                        if a["path"] == STUBS[3])
        _plan_pr = next(a["body"] for a in PLANS["gates_off"][1]
                        if a["path"] == STUBS[0])

        def fresh_clone(name):
            d = os.path.join(TMP, name)
            run([GIT, "clone", "-q", K, d])
            return d

        K2 = fresh_clone("clone-move")
        _k_bare = not os.path.exists(os.path.join(
            K2, ".claude", ".installer-manifest.json"))
        _k_first = install(K2)
        os.rename(os.path.join(K2, STUBS[3]),
                  os.path.join(K2, STUBS[3] + ".mine"))
        _k_move = install(K2)
        check("[KEEP-1, TRUTH] fresh clone (no manifest): moving one stale "
              "file aside and re-installing re-creates only that file and "
              "keeps the filled doc",
              _k_bare and f"SKIP   {STUBS[3]}" in _k_first.stdout
              and _k_move.returncode == 0
              and f"CREATE {STUBS[3]}" in _k_move.stdout
              and "Done. create=1 " in _k_move.stdout
              and read(K2, STUBS[3]) == _plan_ci
              and read(K2, STUBS[0]) == _filled,
              (_k_first.stdout[-500:], _k_move.stdout[-500:]))
        K3 = fresh_clone("clone-adopt")
        _k_adopt = install(K3, None, "--adopt")
        _k_after = install(K3)
        check("[KEEP-1, TRUTH] fresh clone: --adopt and then a re-install "
              "replace the filled doc, with no backup, as the README warns",
              _k_adopt.returncode == 0 and f"ADOPT  {STUBS[0]}"
              in _k_adopt.stdout and _k_after.returncode == 0
              and read(K3, STUBS[0]) == _plan_pr != _filled
              and not os.path.exists(os.path.join(K3, ".claude",
                                                  ".installer-backups")),
              (_k_adopt.stdout[-400:], _k_after.stdout[-400:]))
    else:                          # pragma: no cover
        print("  SKIP  git not found: the fresh-clone rows (NOT measured)")

    # [Plan item 5] The retrofit route, as RETROFIT.md's :9 note gives it.
    _rt = flat(md_section(README, "Retrofit an existing project"))
    with open(os.path.join(ROOT, "RETROFIT.md"), encoding="utf-8") as fh:
        _r9 = fh.read().split("\n")[8]
    _both = ("`.claude.archived-<timestamp>/`", "`settings.local.json`",
             "that file aside", "it creates only `CLAUDE.md`", "R8.E.1",
             "R8.F for `ci-cd.md`")
    check("[item 5] the README's retrofit route has the archive step, the "
          "move-aside route for CLAUDE.md and R8.F, as RETROFIT.md's line 9 "
          "note does, and no --force",
          all(p in _rt and p in _r9 for p in _both)
          and all(p in _rt for p in (
              "Read `$T/RETROFIT.md` and retrofit this project.",
              "Claude does R-1 first, then R0 step 1.",
              '`python3 "$T/bin/retrofit-interview" analyze`',
              '`python3 "$T/bin/retrofit-interview" synthesize`',
              "R1 to R5.5", "R6 smoke test", "R7 handoff"))
          and "--force" not in _rt,
          [p for p in _both if p not in _rt or p not in _r9] or _rt[:500])
    # [WP4 fix round 1 / R1] The route does R-1 first, and analyze does only
    # part of R0: measured here on a project with a root CLAUDE.md and an
    # archived .claude/, the files it writes are steps 3, 4, 8 and 12 and
    # step 1's report, and none of the files R0 steps 5, 6, 9, 10 and 11
    # write; RETROFIT.md's line 9 note and the README send those steps to
    # the document.
    AZ = retro_project("analyze-scope")
    with open(os.path.join(AZ, "CLAUDE.md"), "w") as fh:
        fh.write("# Our rules\n\nKeep these.\n")
    os.makedirs(os.path.join(AZ, ".claude.archived-20261014T000000Z"))
    with open(os.path.join(AZ, ".claude.archived-20261014T000000Z",
                           "notes.md"), "w") as fh:
        fh.write("An old convention.\n")
    _az = run([sys.executable, RETRO_INTERVIEW, "analyze", "-C", AZ])
    _inv_dir = os.path.join(AZ, ".claude", "inventory")
    _inv = sorted(os.listdir(_inv_dir)) if os.path.isdir(_inv_dir) else []
    _steps = {"structure.md", "languages.md", "dependencies.md", "testing.md",
              "git-history.md", "conventions.md", "product-signals.md",
              "pm-tooling-signals.md", "existing-claude.md",
              "baseline-metrics.md"}
    _not = {"claude-md-extraction-plan.md", "prior-art.md",
            "regulatory-context.md", "tribal-knowledge.md",
            "traffic-sample.json"}
    _note_route = _r9[_r9.find(ROUTE_NOTE):]
    check("[R1] analyze writes R0 steps 3, 4, 8 and 12 and step 1's report, "
          "and none of what steps 5, 6, 9, 10 and 11 write; the README and "
          "RETROFIT.md's note send R-1 first and those steps to the document",
          _az.returncode == 0 and set(_inv) == _steps and not _not & set(_inv)
          and "Do R-1 first, then R0 step 1." in _note_route
          and "It does not do R0 steps 2, 5, 6, 7, 9, 10 or 11: do those "
              "from this document, among them step 5's "
              "`claude-md-extraction-plan.md`, which R8.E.1 uses, and the "
              "mandatory step 10." in _note_route
          and "Claude does the R0 steps that `analyze` doesn't (2, 5, 6, 7, "
              "9, 10 and 11) from `RETROFIT.md`" in _rt
          and "the mandatory step 10" in _rt,
          (_az.returncode, _inv, _az.stderr[-300:]))
    RC = project("rclaude")
    with open(os.path.join(RC, "CLAUDE.md"), "w") as fh:
        fh.write("# Our rules\n\nKeep these.\n")
    _rc1 = install(RC, RETRO)
    _rc_kept = read(RC, "CLAUDE.md")
    os.rename(os.path.join(RC, "CLAUDE.md"),
              os.path.join(RC, "CLAUDE.md.ours"))
    _rc2 = install(RC)
    check("[item 5, TRUTH] retrofit: a root CLAUDE.md that was there is "
          "skipped and kept; moved aside, a re-install creates only CLAUDE.md",
          _rc1.returncode == 0 and "SKIP   CLAUDE.md" in _rc1.stdout
          and _rc_kept == "# Our rules\n\nKeep these.\n"
          and _rc2.returncode == 0 and "CREATE CLAUDE.md" in _rc2.stdout
          and "Done. create=1 " in _rc2.stdout,
          (_rc1.stdout[-300:], _rc2.stdout[-400:]))

    # [Plan item 6] The plugin paragraph.
    _pl = md_section(README, "The plugin")
    _plf = flat(_pl)
    _manifest = os.path.join(ROOT, "plugin", ".claude-plugin", "plugin.json")
    check("[g4-1a] the README names the manifest where Claude Code reads it, "
          "which exists, and no plugin/plugin.json",
          "`plugin/.claude-plugin/plugin.json`" in _plf
          and os.path.isfile(_manifest)
          and not re.search(r"(?<![\w.-])plugin/plugin\.json", RM),
          re.findall(r".{30}plugin/plugin\.json", RM))
    _wyg = md_section(README, "What you get")
    check("[g4-1a] What you get lists .claude-plugin/plugin.json and "
          "toolchain/ under plugin/",
          "\n    .claude-plugin/plugin.json" in _wyg
          and "\n    toolchain/" in _wyg
          and not re.search(r"^\s+plugin\.json", _wyg, re.M), _wyg[-500:])
    with open(_manifest, encoding="utf-8") as fh:
        _pname = json.load(fh)["name"]
    _stems = sorted(f[:-3] for f in os.listdir(os.path.join(
        ROOT, "plugin", "commands")) if f.endswith(".md"))
    _want = {f"/{_pname}:{s}" for s in _stems}
    _named = set(re.findall(r"`(/[\w-]+:[\w-]+)`", RM))
    _bare = re.findall(r"(?<![\w:/-])/bootstrap-(?:interview|apply)\b", RM)
    check("[g4-1a, ruling 10] the README names each plugin command with the "
          "manifest's name as its prefix, both in The plugin, and no bare "
          "command name", _named == _want
          and all(f"`{c}`" in _plf for c in _want) and not _bare,
          (sorted(_named), sorted(_want), _bare))
    _cmd_py = [ln.strip() for f in _stems for ln in open(os.path.join(
        ROOT, "plugin", "commands", f + ".md"), encoding="utf-8")
        if "python3" in ln and "/bin/" in ln]
    _kinds = {("bin" if c.startswith(f"{PTM.TOOLCHAIN}/bin/") else
               "lib" if c.startswith(f"{PTM.TOOLCHAIN}/lib/") else c)
              for c in PTM.copy_map()}
    check("[ruling 2 (b)] the README says the commands run the copies under "
          "plugin/toolchain/ (the two tools, every lib/*.py, protocol.md), "
          "not the checkout's bin/; the commands and the map agree",
          all(f"`bin/{t}`" in _plf for t in PTM.BIN_TOOLS)
          and "`plugin/toolchain/`" in _plf and "every `lib/*.py` module" in
          _plf and "`protocol.md`" in _plf
          and "They don't run the checkout's `bin/`" in _plf
          and _kinds == {"bin", "lib", f"{PTM.TOOLCHAIN}/protocol.md"}
          and _cmd_py and all('"${CLAUDE_PLUGIN_ROOT}/toolchain/bin/' in ln
                              and "/../bin" not in ln for ln in _cmd_py),
          (_kinds, _cmd_py))
    _tc_bin = sorted(c for c in PTM.copy_map()
                     if c.startswith(f"{PTM.TOOLCHAIN}/bin/"))
    check("[review build F14] the README says the plugin has no retrofit "
          "command and no copy of bin/retrofit-interview: the map copies "
          "only the two tools to toolchain/bin/, and no command names "
          "retrofit-interview",
          "The plugin has no retrofit command, and it doesn't copy "
          "`bin/retrofit-interview`" in _plf
          and _tc_bin == sorted(f"{PTM.TOOLCHAIN}/bin/{t}"
                                for t in PTM.BIN_TOOLS)
          and not any("retrofit" in c for c in _tc_bin)
          and not any("retrofit" in s for s in _stems)
          and not any("retrofit-interview" in open(os.path.join(
              ROOT, "plugin", "commands", s + ".md"),
              encoding="utf-8").read() for s in _stems), (_tc_bin, _stems))
    _mk = run([GIT, "-C", ROOT, "ls-files"]).stdout if GIT else ""
    check("[ruling 2 (b)] no marketplace file, as the README says, which "
          "loads the plugin with --plugin-dir instead",
          "no marketplace file (`marketplace.json`) yet" in _plf
          and 'claude --plugin-dir "$T/plugin"' in _pl
          and bool(_mk) and "marketplace.json" not in _mk, _plf[-500:])
    _blocks = re.findall(r"```\w*\n(.*?)```", _pl, re.S)
    check("[COPY-3] the identity suite stands in for review of "
          "plugin/toolchain/, and the README's two re-sync commands are the "
          "ones the suite prints (tests/plugin_toolchain_map.py)",
          "`tests/test_wp4_plugin_toolchain.py` checks each copy's bytes and "
          "exec bit against its source, so it stands in for a review of "
          "`plugin/toolchain/`" in _plf
          and os.path.isfile(os.path.join(HERE,
                                          "test_wp4_plugin_toolchain.py"))
          and any(b.strip("\n").split("\n") == [PTM.SYNC, PTM.STAGE]
                  for b in _blocks), _blocks)
    # The stubs line a plugin copy prints names the copy's protocol.md.
    shutil.copy(_doc, os.path.join(TC, "protocol.md"))
    try:
        PC = project("plugin-copy")
        with open(os.path.join(PC, "bootstrap.config.yaml"), "w") as fh:
            fh.write(GATES_OFF)
        _pc = run([sys.executable, "-c",
                   "import sys; sys.path.insert(0, sys.argv[1]); "
                   "import installer; "
                   "raise SystemExit(installer.main(sys.argv[2:]))",
                   os.path.join(TC, "lib"), "-C", PC])
    finally:
        os.remove(os.path.join(TC, "protocol.md"))
    _pcl = stub_line(steps_of(_pc.stdout))
    check("[X6] from a plugin copy, Next steps sends Claude to Phases 1 to "
          "8 of the copy's protocol.md, as the README says",
          "`Next steps:` sends Claude to Phases 1 to 8 of that "
          "`protocol.md`" in _plf and _pc.returncode == 0
          and "(Phases 1 to 8 of "
              + os.path.join(os.path.realpath(TC), "protocol.md") + ")"
          in _pcl, (_pc.returncode, _pcl, _pc.stderr[-300:]))

    # [Plan item 7; 8c] The interviews' refusal and BOOTSTRAP_PROMPT_TIMEOUT.
    _lv = flat(md_section(README, "Answer the interview live"))
    _dflt = re.search(r"`BOOTSTRAP_PROMPT_TIMEOUT` seconds \(default "
                      r"(\d+)\)", _lv)

    class _Pipe:
        """A stdin that is not a terminal and has a descriptor."""
        def isatty(self):
            return False

        def fileno(self):
            return 0

    _waits = []

    def _no_answer(rlist, wlist, xlist, timeout):
        _waits.append(timeout)
        return [], [], []

    _real = (IV.select.select, sys.stdin,
             os.environ.get("BOOTSTRAP_PROMPT_TIMEOUT"))
    try:
        IV.select.select, sys.stdin = _no_answer, _Pipe()
        os.environ.pop("BOOTSTRAP_PROMPT_TIMEOUT", None)
        _msg_default = IV._stdin_refusal("bootstrap-interview") or ""
        os.environ["BOOTSTRAP_PROMPT_TIMEOUT"] = "7"
        _msg_env = IV._stdin_refusal("bootstrap-interview") or ""
    finally:
        IV.select.select, sys.stdin = _real[0], _real[1]
        if _real[2] is None:
            os.environ.pop("BOOTSTRAP_PROMPT_TIMEOUT", None)
        else:
            os.environ["BOOTSTRAP_PROMPT_TIMEOUT"] = _real[2]
    check("[8c, IV-1] the README's variable and default are the ones the "
          "interviews read: unset, the wait is 30 s; set to 7, it is 7 s",
          _dflt is not None and _waits == [float(_dflt.group(1)), 7.0]
          and f"within {_dflt.group(1)} s" in _msg_default
          and "within 7 s" in _msg_env, (_waits, _msg_default, _msg_env))
    check("[8c] the README's refusal cases and exit code are the code's: "
          "rc 2 and 'no config written' for both interviews, at end of "
          "input and with no answer in time",
          all(p in _lv for p in (
              "It exits 2 and writes no config when stdin is closed, when "
              "stdin ends before the first answer, or when stdin isn't a "
              "terminal and no answer arrives within",
              "Claude doesn't run it for you",
              "`retrofit-interview interactive` works the same way"))
          and "no config written" in IV._closed_refusal("x")
          and "no config written" in _msg_default
          and len(_eof) == 2 and all(r.returncode == 2
                                     for r, _, _ in _eof.values())
          and len(_silent) == 2 and all(rc == 2 and none
                                        for rc, _, none in _silent.values()),
          (_lv[:400], {t: v[0] for t, v in _silent.items()}))
    # [WP4 fix round 1 / R2] The refusal check waits for the first byte
    # before the banner, so on a non-terminal stdin nothing shows until the
    # first answer arrives; the README says to type it blind.
    _pb = subprocess.Popen([sys.executable, INTERVIEW, "interactive", "--prd",
                            SAMPLE_PRD, "-o", os.path.join(TMP, "blind.yaml")],
                           stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, env=env_t(60))
    _early = select.select([_pb.stdout], [], [], 1.5)[0]
    _pout = _pb.communicate(input=b"\n" * 80, timeout=120)[0]
    check("[R2] the README says a non-terminal stdin shows nothing until the "
          "first answer, and to type the project name and press Enter; "
          "measured: no output in 1.5 s, then the banner",
          "the tool prints nothing until it reads the first byte" in _lv
          and "type the first answer (the project name) and press Enter"
          in _lv and not _early and _pb.returncode == 0
          and b"=== Bootstrap interview (interactive) ===" in _pout,
          (_lv[-600:], bool(_early), _pb.returncode))
    check("[8c] input that ends after the first answer: the README's warning "
          "and header claims hold for both interviews",
          "the tool prints a `warning:` line, and the config's header names "
          "the values that took their defaults" in _lv
          and len(_partial) == 2 and all(
              rc == 0 and len(w) == 1 and named
              for rc, w, named in _partial.values()), _partial)
    _bullet = next((b for b in README.split("\n\n")
                    if b.startswith("- **`interactive`**")
                    or "\n- **`interactive`**" in b), "")
    _bullet = flat(_bullet[_bullet.find("- **`interactive`**"):])
    check("[8c] the decision-layer section's interactive bullet names the "
          "refusal and links the live-interview section",
          "nothing is written until the config validates" in _bullet
          and "With no answer to read, it exits 2 and writes no config"
          in _bullet and "[Answer the interview live]"
                         "(#answer-the-interview-live)" in _bullet, _bullet)
    _hist = README[_cut:] if _cut >= 0 else ""
    _i1 = _hist[_hist.find("- **I-1 (High)**"):]
    _i1 = flat(_i1[:_i1.find("\n- **", 1)])
    check("[scope F4] the I-1 history entry keeps its text and carries a "
          "dated correction: the refusal, the variable, and partial input "
          "that still takes the fallbacks with a warning",
          _i1.startswith("- **I-1 (High)** — `run_interactive`'s `_ask` "
                         "returns the proposed default on EOF")
          and "*Correction (WP4, 2026-10-14):*" in _i1
          and all(p in _i1.split("*Correction (WP4, 2026-10-14):*")[-1]
                  for p in ("exits 2 and writes no config",
                            "`BOOTSTRAP_PROMPT_TIMEOUT`", "`warning:`",
                            "still takes the fallbacks above")), _i1[-700:])

    # [8b] The held-lock exit code.
    check("[8b] the README's held-lock sentence has the code's exit code, "
          "wait and lock files",
          f"holds the lock for {getattr(installer, '_LOCK_WAIT_S', None)} "
          f"seconds, the install exits **{EXIT_LOCKED}** and writes nothing"
          in RMF and f"`{STATE}.lock`" in RMF and f"`{RSTATE}.lock`" in RMF,
          re.findall(r"Waits for a running loop.{0,400}", RMF))
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

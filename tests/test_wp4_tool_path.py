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

Doc rows (commit 6): the protocol's filename note, and RETROFIT.md and
RETROFIT-COMPANION.md naming the current protocol file, in section 1; g3's
two EOF TRUTH rows, inverted and paired with the For-the-AI notes that now
say the interviews refuse, in section 7. tests/test_wp4_protocol_notes.py
pins every other dated WP4 note and the docs' line counts.

The interleave measurements with a loop wrapper are in
tests/test_wrapper_behavior.py, behind its flock skip.

Run: python3 tests/test_wp4_tool_path.py
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

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

INSTALL = os.path.join(ROOT, "bin", "bootstrap-install")
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
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

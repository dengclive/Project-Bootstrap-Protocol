#!/usr/bin/env python3
"""[WP4] The dated notes in the layered docs (build plan step 3, commit 6).

WP4 corrects the protocol, its Companion, RETROFIT.md and
RETROFIT-COMPANION.md with notes appended to the END of an existing line,
never a new line, because those line numbers are cited (the emitted
iteration-summary citation, tests/test_doc_citations.py, the policy doc).
Each note says "Corrected" where the old text was wrong and "Amended" where
it adds (ED1).

  A. Version literals. Every `bootstrap_protocol_version: "X.Y.Z"` literal
     in the protocol body either equals PROTOCOL_VERSION or sits on a line
     whose WP4 correction points at the **Version:** line. A real install
     over a state file that holds a stale value re-stamps PROTOCOL_VERSION
     and keeps the other keys, which is what the Phase 0 note says.
  B. State-lock idiom. The protocol notes name the sibling lock, scope the
     idiom to scripts (the AI edits the state file with the Edit tool while
     no wrapper or install runs), and the emitted wrappers and .gitignore
     agree. The :402 note's claim is measured here: a deterministic
     three-writer interleaving loses an entry when the lock is on the state
     file and keeps every entry when it is on the sibling `.lock` (Python
     writers with fcntl.flock; no fcntl counts as a failure, not a pass),
     and `exec 9>` on the state file empties it. The measurements of an
     install interleaved with a wrapper live in
     tests/test_wrapper_behavior.py ("[WP4 8b] an install waits for a
     wrapper's state update"), and the held-lock rows in
     tests/test_wp4_tool_path.py section 5; this suite does not repeat them.
  C. One row per note group: each note is found on its line by an anchor
     phrase from the line's original text, then checked by its content, so
     a note that moves or goes away fails. Where a note states what the
     install does, the row derives that from build_plan too.
  D. The five line counts, exact.
  E. Two scoped text guards: no shipped doc or emitted source names
     CLAUDE_CODE_SESSION_ID (ruling 7 (c) replaced that printf with the
     escalate skill), and no live doc says "accepts every" (the interviews
     refuse instead, since 8c), README.md above its review history
     included (commit 8).

Run: python3 tests/test_wp4_protocol_notes.py
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import templates                                  # noqa: E402
from defaults import resolve_config               # noqa: E402
from installer import PROTOCOL_VERSION, build_plan  # noqa: E402
from minyaml import load_yaml                     # noqa: E402

INSTALL = os.path.join(ROOT, "bin", "bootstrap-install")
PRD = templates.PROTOCOL_DOC
COMP = templates.PROTOCOL_COMPANION
RETRO = "RETROFIT.md"
RCOMP = "RETROFIT-COMPANION.md"
SEAM = "SEAM-CONTRACT-v3-0-0.md"
NOTE = "**[Corrected 2026-10-14, WP4.]**"
AMEND = "**[Amended 2026-10-14, WP4.]**"
D1 = "**[Amended 2026-10-14, WP4 / D1.]**"
R7C = "**[Amended 2026-10-14, WP4 / ruling 7 (c).]**"
# Any WP4 tag; the text before the first one is the line's original text.
WP4_TAG = re.compile(r"\*\*\[(?:Amended|Corrected) 2026-10-14, WP4[ .]")

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


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


DOCS = {rel: read(rel) for rel in (PRD, COMP, RETRO, RCOMP, SEAM)}
LINES = {rel: text.split("\n") for rel, text in DOCS.items()}
PRD_TEXT = DOCS[PRD]


def line_starting(prefix):
    hits = [ln for ln in LINES[PRD] if ln.startswith(prefix)]
    return hits[0] if len(hits) == 1 else ""


def site(doc, anchor):
    """(line number, line) of the one line whose ORIGINAL text, the part
    before any WP4 note, holds `anchor`; (None, "") unless exactly one."""
    hits = [(i, ln) for i, ln in enumerate(LINES[doc], 1)
            if anchor in WP4_TAG.split(ln, 1)[0]]
    return hits[0] if len(hits) == 1 else (None, "")


def note_on(doc, line_no, anchor, tag, phrases):
    """Why the note is wrong, or "": the anchor's line is `line_no`, it
    carries `tag` after its original text, and the note holds each phrase."""
    n, ln = site(doc, anchor)
    if n is None:
        return f"{doc}: anchor {anchor[:50]!r} is not on exactly one line"
    if n != line_no:
        return f"{doc}: anchor {anchor[:50]!r} is on :{n}, not :{line_no}"
    head = WP4_TAG.split(ln, 1)[0]
    if tag not in ln or ln.index(tag) < len(head):
        return f"{doc}:{n} carries no {tag}"
    tail = ln[ln.index(tag):]
    missing = [p for p in phrases if p not in tail]
    return f"{doc}:{n} note lacks {missing}" if missing else ""


def group(name, rows):
    """One row per note group; the detail names each failing site."""
    bad = [why for why in (note_on(*r) for r in rows) if why]
    check(name, not bad, "\n        ".join(bad))


def fixture(src_file, var):
    with open(os.path.join(HERE, src_file), encoding="utf-8") as fh:
        text = fh.read()
    return re.search(var + r' = """(.*?)"""', text, re.S).group(1)


def plan_of(yaml_text):
    cfg, errs = resolve_config(load_yaml(yaml_text))
    assert not errs, errs
    return {a["path"]: a["body"] for a in build_plan(cfg)}


# --------------------------------------------------------------------------- #
print("\n=== A. Version literals ===")
# The body runs from the Table of Contents to the non-normative appendix.
_start = next(i for i, ln in enumerate(LINES[PRD])
              if ln == "## Table of Contents")
_end = next(i for i, ln in enumerate(LINES[PRD])
            if ln.startswith("## Proposed revisions"))
_lit = re.compile(r'bootstrap_protocol_version:? *"(\d+\.\d+\.\d+)"')
_rows = [(i + 1, m.group(1), ln)
         for i, ln in enumerate(LINES[PRD][_start:_end], _start)
         for m in _lit.finditer(ln)]
check("the body states four version literals (the scan reaches them)",
      len(_rows) == 4, repr([(n, v) for n, v, _ in _rows]))
_stale = [(n, v) for n, v, ln in _rows
          if v != PROTOCOL_VERSION
          and not (NOTE in ln and "**Version:**" in ln[ln.index(NOTE):])]
check(f"every body literal equals {PROTOCOL_VERSION} or carries the WP4 "
      "note that points at the **Version:** line", not _stale, repr(_stale))
check("the header **Version:** line equals PROTOCOL_VERSION",
      f"**Version:** {PROTOCOL_VERSION}" in PRD_TEXT)
_p0 = line_starting("9. Write `.claude/.bootstrap-state.json` with the "
                    "classification")
check("Phase 0 step 9 note: the installer re-stamps and keeps other keys, "
      "and keeps an unparsable file aside",
      NOTE in _p0 and "replaces any other value in the field" in _p0
      and "`completed_phases` and `deferred_items`, keep the values you wrote"
      in _p0 and ".bootstrap-state.json.pre-unparsed-<UTC stamp>" in _p0,
      _p0[-500:])
for prefix in ('10. **Update state file.** Confirm `bootstrap_protocol_version'
               ': "2.0.0"` is set (Phase 0 wrote it; this phase',
               '12. **Update state file.**',
               '10. **Update state file.** Confirm `bootstrap_protocol_version'
               ': "2.0.0"` is set (Phase 0 wrote it) and'):
    ln = line_starting(prefix)
    check(f"confirm-step note names the Migration notes: {prefix[:24]!r}",
          NOTE in ln and "Companion's Migration notes" in ln, ln[-300:])

# Derive the Phase 0 note's claim from a real install. (The parse guard's
# copy and warning are tests/test_wp4_tool_path.py section 6.)
_tmp = tempfile.mkdtemp(prefix="wp4-notes-state-")
try:
    proj = os.path.join(_tmp, "p")
    os.makedirs(os.path.join(proj, ".claude"))
    if shutil.which("git"):
        subprocess.run(["git", "init", "-q", proj], check=True)
    seeded = {"bootstrap_protocol_version": "2.0.1", "gate_substrate": "shell",
              "completed_phases": [0], "last_phase_started": 1,
              "deferred_items": {"ci_config_generation": "phase_9"}}
    with open(os.path.join(proj, ".claude", ".bootstrap-state.json"), "w",
              encoding="utf-8") as fh:
        json.dump(seeded, fh)
    r = subprocess.run([sys.executable, INSTALL, "-c",
                        os.path.join(ROOT, "bootstrap.config.yaml"),
                        "-C", proj], capture_output=True, text=True,
                       timeout=300)
    with open(os.path.join(proj, ".claude", ".bootstrap-state.json"),
              encoding="utf-8") as fh:
        st = json.load(fh)
    check("install over a stale '2.0.1' state file exits 0", r.returncode == 0,
          r.stderr[-300:])
    check(f"the install re-stamps bootstrap_protocol_version "
          f"{PROTOCOL_VERSION}",
          st.get("bootstrap_protocol_version") == PROTOCOL_VERSION,
          repr(st.get("bootstrap_protocol_version")))
    check("the install keeps the keys the AI wrote",
          st.get("completed_phases") == [0]
          and st.get("last_phase_started") == 1
          and st.get("deferred_items") == {"ci_config_generation": "phase_9"},
          repr({k: st.get(k) for k in seeded}))
    # [WP4 fix round 2 / CR-1] A first install seeds bootstrap_complete
    # false over the state file Phase 0 wrote, as the :404 note says: on
    # the documented route that file is there before the first install.
    check("on a first install over the state file Phase 0 wrote, it seeds "
          "bootstrap_complete: false (the :404 note)",
          st.get("bootstrap_complete") is False, repr(st.get(
              "bootstrap_complete")))
finally:
    shutil.rmtree(_tmp, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("\n=== B. State-lock idiom ===")
_canon = line_starting("A single task may appear in `loop_in_flight` *or* "
                       "`goal_in_flight` but never both")
check("Recovery & State note: names the sibling lock and the empty-file "
      "hazard", NOTE in _canon
      and "take `flock` on `.claude/.bootstrap-state.json.lock`" in _canon
      and "`exec 9>.claude/.bootstrap-state.json` empties the file" in _canon,
      _canon[-600:])
_tail = _canon[_canon.index(NOTE):] if NOTE in _canon else ""
check("Recovery & State note: the idiom is for scripts; the AI edits the "
      "state file with the Edit tool only while no wrapper or install runs "
      "(review DOC-3)",
      "The idiom is for scripts." in _tail
      and "The Edit tool takes no lock, so edit the state file with it only "
          "while no loop wrapper or install is running." in _tail,
      _tail[-300:])
check("ED17: the protocol note quotes no lock measurement (counts go in the "
      "changelog)", _tail and not re.search(r"\d+ of \d+ runs", _tail)
      and "Measured" not in _tail, _tail[:300])
for prefix in ("- ✅ **Concurrent-safe state reads/writes**",
               "   2. Acquires an advisory lock on "
               "`.claude/.bootstrap-state.json` via `flock`",
               "**Race-safety summary.**",
               "- **`.claude/goal-loop.sh`** — the wrapper script."):
    ln = line_starting(prefix)
    check(f"site note points at the sibling lock: {prefix[:30]!r}",
          NOTE in ln and "`.claude/.bootstrap-state.json.lock`" in ln
          and "Recovery & State" in ln[ln.index(NOTE):] if NOTE in ln
          else False, ln[-300:])

# The note says "as the emitted wrappers ... do": derive it from the plan.
FULL = """project:
  name: g6
  archetype: ai-agent
  prd_tier: full
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: true
commands:
  test: "pytest -q"
  lint: "ruff check ."
"""
_full = plan_of(FULL)
for w in (".claude/loop.sh", ".claude/goal-loop.sh"):
    body = _full.get(w, "")
    check(f"{w} locks the sibling $STATE.lock, never the state file",
          'exec 9>"$STATE.lock"' in body
          and not re.search(r'exec 9[<>]+"\$STATE"', body), w)
check("the emitted .gitignore covers the sibling lock file",
      ".bootstrap-state.json.lock" in _full.get(".claude/.gitignore", ""))

# The measurement behind the :402 note (and the four site notes that defer
# to it): a deterministic interleaving of three writers, with ONE variable,
# the lock path. Ported from the WP4 critic's bash prototype to Python, so
# it needs neither flock(1) nor jq. Marker files order the steps, so no step
# depends on timing:
#   A locks, reads, waits until B has OPENED the lock path, renames,
#     releases.
#   B opened the path before A's rename; C opens it after A's release.
#   B and C each try the lock without blocking (LOCK_NB); one that cannot
#     get it marks itself WAITING, then blocks. Each reads, then holds its
#     write until the other has read or is waiting.
# A lock that excludes makes one of B and C wait. A lock on the state file
# does not: B holds the lock on the file A renamed away, C takes the lock on
# the new one, both read A's state, and the later rename drops the other's
# entry. Every wait is bounded: a writer that waits WRITER_WAIT_S for a
# marker exits 3, and the parent kills each writer's process group after
# INTERLEAVE_TIMEOUT_S, so a broken interleaving fails instead of hanging.
WRITER_WAIT_S = 10
INTERLEAVE_TIMEOUT_S = 30
INTERLEAVE_WRITER = r'''
import fcntl, json, os, sys, time
state, lock, me, d, wait_s = sys.argv[1:6]


def mark(name):
    open(os.path.join(d, name), "w").close()


def wait_any(*names):
    end = time.monotonic() + float(wait_s)
    while not any(os.path.exists(os.path.join(d, n)) for n in names):
        if time.monotonic() > end:
            mark(me + ".timeout")
            sys.exit(3)
        time.sleep(0.01)


def take(fd):
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        mark(me + ".waiting")
        fcntl.flock(fd, fcntl.LOCK_EX)


def add():
    with open(state, encoding="utf-8") as fh:
        s = json.load(fh)
    s["loop_in_flight"].append(me)
    return json.dumps(s)


def commit(text):
    tmp = state + ".tmp." + me
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    os.replace(tmp, state)


if me == "A":
    fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    new = add()
    mark("A.locked")
    wait_any("B.opened")
    commit(new)
    fcntl.flock(fd, fcntl.LOCK_UN)
    mark("A.released")
elif me == "B":
    wait_any("A.locked")
    fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o644)
    mark("B.opened")
    wait_any("A.released")
    take(fd)
    new = add()
    mark("B.read")
    wait_any("C.read", "C.waiting")
    commit(new)
    fcntl.flock(fd, fcntl.LOCK_UN)
else:
    wait_any("A.released")
    fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o644)
    take(fd)
    new = add()
    mark("C.read")
    wait_any("B.read", "B.waiting")
    commit(new)
    fcntl.flock(fd, fcntl.LOCK_UN)
'''


def interleave(lock_on_state):
    """Run writers A, B and C over one state file, the lock on the state
    file itself or on its sibling `.lock`. Returns a dict: `entries`, the
    sorted loop_in_flight (None if the file does not parse), `rcs`, each
    writer's exit code (None if killed), and `why`, the timeouts seen."""
    d = tempfile.mkdtemp(prefix="wp4-notes-lock-")
    procs, why = [], []
    try:
        state = os.path.join(d, ".bootstrap-state.json")
        with open(state, "w", encoding="utf-8") as fh:
            json.dump({"bootstrap_protocol_version": PROTOCOL_VERSION,
                       "loop_in_flight": []}, fh)
        lock = state if lock_on_state else state + ".lock"
        for w in ("A", "B", "C"):
            procs.append(subprocess.Popen(
                [sys.executable, "-c", INTERLEAVE_WRITER, state, lock, w, d,
                 str(WRITER_WAIT_S)], start_new_session=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        deadline = time.monotonic() + INTERLEAVE_TIMEOUT_S
        for p in procs:
            try:
                p.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                why.append(f"killed after {INTERLEAVE_TIMEOUT_S} s")
                break
        for p in procs:
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.wait()
        why += sorted(f for f in os.listdir(d) if f.endswith(".timeout"))
        try:
            with open(state, encoding="utf-8") as fh:
                entries = sorted(json.load(fh)["loop_in_flight"])
        except (OSError, ValueError, KeyError):
            entries = None
        return {"entries": entries, "why": why,
                "rcs": [p.returncode for p in procs]}
    finally:
        shutil.rmtree(d, ignore_errors=True)


try:
    import fcntl
except ImportError:                    # pragma: no cover - not POSIX
    fcntl = None
if fcntl is None:                      # pragma: no cover - not POSIX
    print("  NOT measured: no fcntl on this platform, so the lock "
          "interleaving cannot run")
    check("the :402 lock claim is measured (fcntl is available)", False)
else:
    _on_state = interleave(True)
    check("lock on the state file + rename loses an entry (deny capability: "
          "the interleaving reaches the race)",
          _on_state["rcs"] == [0, 0, 0] and not _on_state["why"]
          and _on_state["entries"] is not None
          and len(_on_state["entries"]) == 2 and "A" in _on_state["entries"],
          _on_state)
    _on_sibling = interleave(False)
    check("lock on the sibling .lock + rename keeps every entry",
          _on_sibling["rcs"] == [0, 0, 0] and not _on_sibling["why"]
          and _on_sibling["entries"] == ["A", "B", "C"], _on_sibling)

# The note's hazard: the shell form that opens the state file to lock it
# truncates it first.
BASH = shutil.which("bash")
if not BASH:
    check("bash is on PATH (the `exec 9>` hazard row runs the shell form)",
          False)
else:
    _d = tempfile.mkdtemp(prefix="wp4-notes-trunc-")
    try:
        _st = os.path.join(_d, ".bootstrap-state.json")
        with open(_st, "w", encoding="utf-8") as fh:
            fh.write('{"loop_in_flight": ["t1"]}\n')
        _before = os.path.getsize(_st)
        _r = subprocess.run([BASH, "-c", 'exec 9>"$1"', "t", _st],
                            capture_output=True, text=True, timeout=30)
        check("`exec 9>` on a non-empty state file empties it (the :402 "
              "note's hazard)", _r.returncode == 0 and _before > 0
              and os.path.getsize(_st) == 0,
              (_r.returncode, _before, os.path.getsize(_st), _r.stderr))
    finally:
        shutil.rmtree(_d, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("\n=== C. The notes, group by group ===")
DEFAULT = read("bootstrap.config.yaml")
GATES_OFF = fixture("test_greenfield_golden.py", "FIXTURE_GATES_OFF")
RETRO_AGENT = fixture("test_retrofit.py", "AGENT_RETROFIT_CFG")
RETRO_SVC = fixture("test_retrofit.py", "SERVICE_RETROFIT_CFG")
_gf = plan_of(DEFAULT)
_ra = plan_of(RETRO_AGENT)
_rs = plan_of(RETRO_SVC)
CODE_ID = "CLAUDE_CODE_SESSION_ID"

group("[filename] the protocol's filename note and both RETROFIT files name "
      "the current pair", [
          (PRD, 82, "> code MINOR (two new configuration keys) served by "
           "this one.", NOTE,
           ["Since 2026-08-14 this file is named `v2-8-0`", "PR #72",
            "freeze exception 70", "`Bootstrap-Protocol-v2-6-0.md`"]),
          (RETRO, 3, "**Version:** 1.6.2 — companion to BOOTSTRAP.md "
           "v1.9.0.", NOTE,
           ["`BOOTSTRAP.md` and `BOOTSTRAP-COMPANION.md`", f"`{PRD}`",
            f"`{COMP}`", "until protocol 2.0.0 renamed them"]),
          (RCOMP, 3, "**Companion to `RETROFIT.md` v1.6.2**", NOTE,
           ["`BOOTSTRAP.md` and `BOOTSTRAP-COMPANION.md` are now",
            f"`{PRD}`", f"`{COMP}`"]),
      ])

_AI = "> **For the AI:** When the operator opens this file and asks you to"
group("[route, D1] the protocol and RETROFIT.md route the AI through the "
      "tools, and the operator's approval of the dry-run plan covers the "
      "install (ruling 6 (a))", [
          (PRD, 283, _AI + " bootstrap", D1,
           ["`bootstrap-interview analyze --prd <PRD path>`",
            "`bootstrap-interview synthesize`",
            "`bootstrap-install --dry-run` as the preview",
            "that approval covers every file in the plan",
            "the installer keeps your keys, except those it sets itself",
            "`protocol_doc`",
            "`product.md`, `tech.md`, `structure.md` and `ci-cd.md` are "
            "stubs", "`Next steps:` block names each stub this install still "
            "owns", "`bin/retrofit-interview`"]),
          (PRD, 781, "3. For each accepted hook, write the script under", D1,
           ["has already written each accepted hook and wired it into "
            "`.claude/settings.json`", "show the operator each script it "
            "wrote and run the checklist below on it"]),
          (PRD, 2191, "- **Never batch artifacts.**", D1,
           ["approval of the `bootstrap-install --dry-run` plan covers the "
            "files the installer writes"]),
          (PRD, 2192, "- **Always show before writing.**", D1,
           ["the plan lists files, not their contents",
            "each hook script and agent definition the installer wrote, in "
            "its own phase", "change `bootstrap.config.yaml` and "
            "re-install"]),
          (RETRO, 9, _AI + " retrofit", D1,
           ["Do R-1 first, then R0 step 1.",
            "`.claude.archived-<timestamp>/`",
            "except `settings.json`, `settings.local.json` and the "
            "`.retrofit-state.json` R-1 wrote", "`retrofit-interview analyze`",
            "writes automated first cuts of the R0 inventory",
            "Check each first cut against its step's list in this document",
            "Do R0 steps 2, 5, 6, 7, 9, 10 and 11 from this document",
            "step 5's `claude-md-extraction-plan.md`, which R8.E.1 uses",
            "the mandatory step 10",
            "`retrofit-interview synthesize`",
            "`bootstrap-install --dry-run` as the preview",
            "move that file aside, then re-run `bootstrap-install`",
            "it creates only `CLAUDE.md`", "R8.E.1",
            "Don't use `--force` for this: it replaces every skipped file",
            "`--force --dry-run` lists them", "R8.F for `ci-cd.md`"]),
      ])
_r9 = site(RETRO, _AI + " retrofit")[1]
check("[route, X12] RETROFIT.md's note gives no --force advice for "
      "CLAUDE.md, and the For-the-AI line keeps its original text",
      "run it again with `--force`" not in _r9
      and "before any other edit" not in _r9
      and _r9.startswith(_AI + " retrofit, you run this protocol "
                         "end-to-end."), _r9[-400:])

group("[interview, 8c] both route notes say the interactive interview "
      "refuses with no terminal (no 'accepts every')", [
          (PRD, 283, _AI + " bootstrap", D1,
           ["Don't run `bootstrap-interview interactive` yourself",
            "with no terminal, it writes no config and exits 2",
            "input that ends early takes the remaining defaults and says "
            "so"]),
          (RETRO, 9, _AI + " retrofit", D1,
           ["Don't run `retrofit-interview interactive` yourself",
            "with no terminal, it writes no config and no inventory and "
            "exits 2", "input that ends early takes the remaining defaults "
            "and says so"]),
      ])

group("[writes, X9] both route notes send writes under .claude/ through the "
      "Write and Edit tools and stop on a refusal", [
          (PRD, 283, _AI + " bootstrap", D1,
           ["with the Write and Edit tools, not with a shell redirect or a "
            "script", "approval prompt for `.claude/` applies",
            "as it does under `claude -p` until D5 is decided, stop and tell "
            "the operator", "don't write the file another way"]),
          (RETRO, 9, _AI + " retrofit", D1,
           ["with the Write and Edit tools", "approval prompt for "
            "`.claude/` applies", "as it does under `claude -p` until D5 is "
            "decided, stop and tell the operator"]),
      ])

group("[state keys] bootstrap_complete, protocol_doc and the Phase 9 "
      "decision are named where the protocol writes them", [
          (PRD, 404, "For state-file migration from older protocol "
           "versions", AMEND,
           ["`completed_phases`", "`last_phase_started`",
            "`bootstrap_complete`", "on a first install",
            "whether or not you wrote the state file first",
            "A state file can lack it, for example one an earlier install "
            "wrote before the key existed",
            "read that as unknown, not as incomplete", "`protocol_doc`",
            "`toolchain/protocol.md`", "`null`"]),
          (PRD, 1313, "1. Ask: \"Run the workflow as a smoke test?", AMEND,
           ["`skippable_phase_decisions.phase_9_smoke_test`",
            "`\"run\"` or `\"skip\"`", "`phase_7_6_spec_roster`",
            "`Next steps:` block"]),
          (PRD, 2158, "2. Update `.claude/.bootstrap-state.json` to mark "
           "bootstrap complete.", AMEND,
           ["Set `bootstrap_complete: true` after step 3",
            "with the Edit tool, while no loop wrapper or install is "
            "running"]),
      ])

group("[ledger, g5-2b] the ledger note corrects the token-multiplier "
      "section", [
          (PRD, 461, "The ledger **links** to the sections that own each "
           "default", NOTE,
           ["Phase 7 step 3 (the cost disclosure), not at Phase 9.5",
            "`protocol_doc`"]),
      ])
_ledger = _gf[".claude/steering/assumption-ledger.md"]
check("[ledger] the emitted ledger does what the note says: the cost "
      "disclosure row, and protocol_doc",
      "**Subagent token multipliers** — Phase 7 step 3" in _ledger
      and "`protocol_doc`" in _ledger
      and "not with this project" in _ledger)

group("[steering, g2] tech.md's two scaffolds and ci-cd.md's one stop, in "
      "both protocols", [
          (PRD, 613, "5. Write `.claude/steering/tech.md` with explicit",
           AMEND, ["already has both sections", "`TODO:` paragraph",
                   "never a path", "warns when the Test row does not "
                   "name `commands.test`"]),
          (RETRO, 804, "8. Write `.claude/steering/tech.md` with sections:",
           AMEND, ["`## Do Not Touch` and `## Documentation Policy`",
                   "`TODO:` paragraph", "steps 6 and 7", "never a path",
                   "step 7's drift question"]),
          (PRD, 725, "4. Write `.claude/steering/ci-cd.md`. Make explicit",
           AMEND, ["Name one stopping point, not two",
                   "stops after it opens a pull request, and a person "
                   "merges it", "stop as `ci-cd.md` says"]),
          (PRD, 729, "**Exit criteria:** `ci-cd.md` exists. The "
           "agent-vs-human line is unambiguous.", AMEND,
           ["opt-out `ci-cd.md`", "stops after its last commit for the "
            "task, and a person pushes"]),
          (RETRO, 1491, "**Exit criteria:** `ci-cd.md` exists. "
           "Agent-vs-human stopping point unambiguous.", AMEND,
           ["names one stop", "stops after it opens a pull request, and a "
            "person merges it", "stops after its last commit for the task, "
            "and a person pushes"]),
      ])
_stop = _gf[".claude/steering/ci-cd.md"]
check("[steering] the emitted ci-cd.md and CLAUDE.md say what the notes "
      "quote", "The agent stops after it opens a pull request." in _stop
      and "A person\nreviews the pull request and merges it." in _stop
      and "stop as `ci-cd.md` says." in _gf["CLAUDE.md"]
      and "stop as `ci-cd.md` says." in _rs["CLAUDE.md"], _stop[-500:])

group("[CI, g6-c] CI config generation stays the AI's", [
          (PRD, 726, "5. **CI config file generation.**", AMEND,
           ["The installer writes no CI config file and never changes one",
            "Phase 9 step 8",
            "`deferred_items.ci_config_generation` as you wrote it"]),
      ])
_ci = sorted(p for p in _gf if p.startswith((".github/", ".gitlab-ci",
                                             "bitbucket-pipelines")))
check("[CI] the default plan writes no CI config file (the :726 note)",
      not _ci, _ci)

group("[escalate, ruling 7 (c)] every escalate note names the skill and "
      "says where the record can land", [
          (PRD, 1137, "   - `ack-drift` — writes an acknowledgement", R7C,
           ["`escalate`", "`/escalate`",
            "`.claude/sessions/.decision-pending-<session-id>`",
            "With `workflow.install_skills` on (the default)",
            "with the skills off it writes no skill, and the `/escalate` "
            "command, like every command, then only names its missing skill "
            "(backlog Z-66)"]),
          (PRD, 1299, "   - When triggering the decision-required alarm, "
           "the agent writes to", R7C,
           ["`/escalate`", "`timestamp:` (from the clock), `reason:`, "
            "`about-to:` and `needs:`", "appends a later record",
            "Inside an implementer worktree"]),
          (PRD, 1303, "**Exit criteria:** `CLAUDE.md` exists, is thin",
           AMEND, ["`/escalate`", "with `workflow.install_skills` on (the "
                   "default), session hygiene", "With it off, it has "
                   "neither"]),
          (RETRO, 150, "- ✓ **Standard skills** — full BOOTSTRAP set:",
           R7C, ["`escalate`", "no line that points at it"]),
          (RETRO, 1330, "- `spec-new`, `spec-review`, `spec-decompose`, "
           "`plan-review`, `spec-validate`, `test-author`", R7C,
           ["`escalate`", "does not name it yet", "is unmeasured"]),
          (RETRO, 1450, "Write `CLAUDE.md` at repo root with:", AMEND,
           ["`escalate`", "no line that points at it", "is unmeasured",
            "With `workflow.install_skills` on (the default)",
            "With it off, the install writes no skill, and the `/escalate` "
            "command, like every command, then only names its missing skill "
            "(backlog Z-66)."]),
      ])
_D5 = ("so the record lands only where Claude Code allows writes under "
       "`.claude/`; under `claude -p` the write is refused until D5 is "
       "decided.")
group("[escalate, build F5] each escalate note says the record lands only "
      "where Claude Code allows writes under .claude/, and not under "
      "claude -p until D5", [
          (PRD, 1137, "   - `ack-drift` — writes an acknowledgement", R7C,
           [_D5]),
          (PRD, 1299, "   - When triggering the decision-required alarm, "
           "the agent writes to", R7C,
           [_D5, "An unattended run therefore still ends with no record."]),
          (PRD, 1303, "**Exit criteria:** `CLAUDE.md` exists, is thin",
           AMEND, [_D5]),
          (RETRO, 150, "- ✓ **Standard skills** — full BOOTSTRAP set:",
           R7C, [_D5]),
          (RETRO, 1330, "- `spec-new`, `spec-review`, `spec-decompose`, "
           "`plan-review`, `spec-validate`, `test-author`", R7C, [_D5]),
          (RETRO, 1450, "Write `CLAUDE.md` at repo root with:", AMEND,
           [_D5]),
      ])
_esc_sites = [site(PRD, a)[1] for a in (
    "   - `ack-drift` — writes an acknowledgement",
    "   - When triggering the decision-required alarm, the agent writes to",
    "**Exit criteria:** `CLAUDE.md` exists, is thin")] + [
    site(RETRO, a)[1] for a in (
        "- ✓ **Standard skills** — full BOOTSTRAP set:",
        "Write `CLAUDE.md` at repo root with:")]
check("[escalate, scope F3 / build N3] no escalate note carries the printf "
      "command or the Bash-tool variable it needed",
      all(ln and "printf" not in ln and CODE_ID not in ln
          for ln in _esc_sites), [ln[-200:] for ln in _esc_sites if not ln])

# What the escalate notes say the install does, derived from the plans.
_skill = _gf.get(".claude/skills/escalate/SKILL.md", "")
_keys = re.findall(r"^\s+(timestamp|reason|about-to|needs):", _skill, re.M)
_n1299 = site(PRD, "   - When triggering the decision-required alarm, the "
                   "agent writes to")[1]
check("[escalate] the skill writes the record path and the four keys, in "
      "the order the :1299 note gives",
      ".claude/sessions/.decision-pending-${CLAUDE_SESSION_ID}" in _skill
      and _keys == ["timestamp", "reason", "about-to", "needs"]
      and "date -u +%Y-%m-%dT%H:%M:%SZ" in _skill, (_keys, _skill[:300]))
_m = re.search(r"Skill-body substitution of .*?\| Claude Code ([\d.]+) "
               r"\(measured", _ledger)
check("[escalate] the :1299 note's measured version is the ledger's "
      "substitution row",
      bool(_m) and f"(measured on Claude Code {_m.group(1)})" in _n1299,
      (_m and _m.group(1), _n1299[-600:]))
_pointer = [ln for ln in _gf["CLAUDE.md"].splitlines() if "/escalate" in ln]
_n1303 = site(PRD, "**Exit criteria:** `CLAUDE.md` exists, is thin")[1]
check("[escalate] the :1303 note quotes the greenfield CLAUDE.md's "
      "/escalate line exactly",
      len(_pointer) == 1 and f"\"{_pointer[0]}\"" in _n1303,
      (_pointer, _n1303[-900:]))
check("[escalate] both retrofit fixtures emit the skill and no CLAUDE.md "
      "line names it, as the RETROFIT.md notes say",
      all(".claude/skills/escalate/SKILL.md" in p
          and ".claude/commands/escalate.md" in p
          and "/escalate" not in p["CLAUDE.md"] for p in (_ra, _rs))
      and _ra["CLAUDE.md"].count("\n") == 80,
      [p["CLAUDE.md"].count("\n") for p in (_ra, _rs)])

group("[CLAUDE.md, g1 and X3] what the installer's CLAUDE.md carries, in "
      "both modes", [
          (PRD, 1303, "**Exit criteria:** `CLAUDE.md` exists, is thin",
           AMEND, ["`deps.enabled: false`", "`secrets.enabled: false`",
                   "failing-test-first step", "the one stop `ci-cd.md` "
                   "states", "Never list", "only on a permission or "
                   "elicitation prompt", "the drift Alert 3 item",
                   "RETROFIT.md R8.E.2"]),
          (RETRO, 1450, "Write `CLAUDE.md` at repo root with:", AMEND,
           ["`deps.enabled: false`", "`secrets.enabled: false`",
            "starts each spec on a spec branch", "`spec/<slug>`",
            "pulled first when it tracks a remote branch, and asks the "
            "operator where the base is unclear",
            "the one stop `ci-cd.md` states"]),
      ])
_gfoff = plan_of(GATES_OFF)["CLAUDE.md"]
check("[CLAUDE.md] with the gates off, the greenfield CLAUDE.md names no "
      "deps.md, secrets.md or never-read path (the :1303 note; the full "
      "matrix is tests/test_wp4_claude_md.py)",
      "deps.md" not in _gfoff and "secrets.md" not in _gfoff
      and "never-read" not in _gfoff)
check("[CLAUDE.md] both modes start a task on a spec branch, and /spec-new "
      "creates spec/<slug> (the R8.E.2 note: no retrofit-only limit)",
      all("Starting a task: on a spec branch," in p["CLAUDE.md"]
          and "git switch -c spec/<slug>" in
          p.get(".claude/skills/spec-new/SKILL.md", "")
          for p in (_gf, _ra, _rs)))

group("[plugin] the Companion's plugin paragraph names the moved manifest, "
      "the prefixed commands and no marketplace", [
          (COMP, 292, "**The official Claude Code plugin marketplace.**",
           NOTE, ["`plugin/.claude-plugin/plugin.json`",
                  "`author` is an object", "`plugin/toolchain/`",
                  "`/bootstrap-protocol:bootstrap-interview`",
                  "`/bootstrap-protocol:bootstrap-apply`",
                  "not a plugin marketplace yet",
                  "`claude --plugin-dir <checkout>/plugin`"]),
      ])
_manifest = os.path.join(ROOT, "plugin", ".claude-plugin", "plugin.json")
with open(_manifest, encoding="utf-8") as fh:
    _pj = json.load(fh)
_heads = []
for _f in sorted(os.listdir(os.path.join(ROOT, "plugin", "commands"))):
    with open(os.path.join(ROOT, "plugin", "commands", _f),
              encoding="utf-8") as fh:
        _heads += [ln for ln in fh.read().splitlines() if ln.startswith("# /")]
check("[plugin] the tree matches the note: the manifest is only under "
      ".claude-plugin/, its author is an object, the commands carry the "
      "plugin prefix, and there is no marketplace file",
      not os.path.exists(os.path.join(ROOT, "plugin", "plugin.json"))
      and isinstance(_pj.get("author"), dict)
      and sorted(_heads) == [f"# /{_pj['name']}:bootstrap-apply",
                             f"# /{_pj['name']}:bootstrap-interview"]
      and not os.path.exists(os.path.join(ROOT, ".claude-plugin",
                                          "marketplace.json")),
      (_pj.get("author"), _heads))

# --------------------------------------------------------------------------- #
print("\n=== D. Line counts ===")
# Same-line appends only: a new line moves every citation below it.
for rel, want in ((PRD, 2349), (COMP, 582), (RETRO, 1598), (RCOMP, 566),
                  (SEAM, 379)):
    have = DOCS[rel].count("\n")
    check(f"{rel} has exactly {want:,} lines", have == want, have)

# --------------------------------------------------------------------------- #
print("\n=== E. Scoped text guards ===")


def scope_files(rels):
    """Each named file, and every file under each named directory."""
    out = []
    for rel in rels:
        path = os.path.join(ROOT, rel)
        if os.path.isdir(path):
            for base, dirs, files in os.walk(path):
                dirs[:] = sorted(d for d in dirs if d != "__pycache__")
                out += [os.path.relpath(os.path.join(base, f), ROOT)
                        for f in sorted(files)]
        else:
            out.append(rel)
    return out


def hits(rels, pattern):
    found = []
    for rel in scope_files(rels):
        try:
            text = read(rel)
        except (OSError, UnicodeDecodeError):
            continue
        found += [f"{rel}:{i}" for i, ln in enumerate(text.split("\n"), 1)
                  if pattern.search(ln)]
    return found


# Scoped on purpose (review scope F3): .claude/context-check.py and
# .claude/readiness-runbook.md name the variable legitimately.
_ID_SCOPE = (PRD, COMP, RETRO, RCOMP, "README.md", "plugin",
             "lib/templates.py")
_id_hits = hits(_ID_SCOPE, re.compile(CODE_ID))
check("no shipped doc or emitted source names CLAUDE_CODE_SESSION_ID "
      f"({len(scope_files(_ID_SCOPE))} files scanned)",
      not _id_hits and len(scope_files(_ID_SCOPE)) >= 9, _id_hits)
_AE = re.compile(r"accepts\s+every", re.I)
_AE_SCOPE = (PRD, COMP, RETRO, RCOMP, "plugin")
_ae_hits = hits(_AE_SCOPE, _AE)
# README.md counts above its review history only: a history entry may quote
# what an interview did when the entry was written. Flattened, so a phrase
# wrapped across two lines is found too.
_readme = read("README.md")
_rh = _readme.find("\n## Review history\n")
_readme_live = _readme[:_rh] if _rh >= 0 else _readme
_ae_hits += [f"README.md (above its review history): {m.group(0)!r}"
             for m in _AE.finditer(" ".join(_readme_live.split()))]
check("no live doc says 'accepts every' (the interviews refuse instead) "
      f"({len(scope_files(_AE_SCOPE))} files scanned, and README.md above "
      f"its review history)",
      not _ae_hits and len(scope_files(_AE_SCOPE)) >= 7 and _rh > 0,
      _ae_hits or _rh)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

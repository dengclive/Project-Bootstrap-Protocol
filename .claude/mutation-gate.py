#!/usr/bin/env python3
"""mutation-gate - prove a guard is RED under mutation, mechanically.

Internal automation. NOT protocol surface. NOT a Bootstrap Protocol feature.
It emits nothing, is imported by nothing under `lib/`, moves no golden digest,
and is cited from no protocol document (`.claude/readiness-runbook.md` §0).

WHY THIS EXISTS. A source-text pin asserts that a string is present. It cannot
assert that removing the BEHAVIOUR turns the suite red, and this repo has now
paid for that difference five times against one loop: `_cnext=16` ->
`_cnext=1600000` passed a pin that CONTAINED it; `break` -> `:` left every
pinned string intact; `; continue` on the completer-mark line left all four
pinned strings BYTE-IDENTICAL; and a `; break` after the probe stops the loop
TOO SOON, which the trace-count row cannot see because stopping early looks
exactly like stopping right. The merge gate is therefore not "the pins are
green" but "each known one-line bypass has been shown to turn a NAMED check
red". This script is that gate, run rather than remembered.

WHERE IT MEASURES. In a PRIVATE `git worktree` at HEAD, created per run and
deleted after. Your working tree is never written to and never read for the
result, so the gate cannot be disturbed by, and cannot disturb, anything else
you are doing. It also does not need to police what you are doing: an earlier
design mutated product source in the shared tree and grew ~250 lines of
dirty-tree refusals, an O_EXCL lock with an owner pid, a backup, a
hash-verified restore on four exit paths, `--recover`, and a per-suite
whole-tree scan. Four consecutive review rounds found new accident-class
defects in that machinery and nowhere else. The isolation replaces all of it.

WHAT IT REFUSES TO DO. The failure mode of a mutation harness is to apply
nothing, run a suite, watch it go red for some unrelated reason, and report
"all caught". Every guard below exists because "all caught" is the answer this
script would give if it were broken:

  1. THE TARGET MUST BE COMMITTED. The checkout is taken at HEAD, so
     uncommitted edits to the guard are not what gets measured, and silently
     reporting on different bytes than the ones you are looking at is the
     false-green class this harness exists to prevent. This is the ONLY
     question asked about your working tree; every other file may be dirty.
  2. BASELINE MUST BE GREEN, AND MUST RUN CHECKS. If a suite is already red,
     every mutation is "caught" and the report is vacuous; if it reports
     0 checks (a skip), it witnesses nothing. Measured, printed, required.
  3. THE ANCHOR MUST MATCH EXACTLY ONCE. Zero matches means the mutation has
     ROTTED against the guard it protects -- the single highest-value signal
     this script produces, and the one a prose mutation list cannot give. More
     than one means the edit is ambiguous. Either is an ERROR, never "caught".
  4. A DECLARED CHECK NAME MUST IDENTIFY ONE CHECK. `want` is matched as a
     substring, so a short or generic string would score RED@check against
     whatever happens to fail. A behavioural suite needs exactly one match; a
     digest suite needs at least one, since a digest moves for any byte.
  5. THE BYTES MUST ACTUALLY CHANGE. The post-write SHA-256 is compared to the
     pre-write one. A no-op rewrite reports MUTATION-NOOP, not "caught".
  6. RED IS NOT ENOUGH -- IT MUST BE RED AT THE NAMED CHECK. A mutation that
     makes the suite crash, or that trips an unrelated check (a golden digest
     moves for EVERY edit to `lib/templates.py`), is scored RED-WRONG-REASON,
     which is a failure of the gate, not a pass.
  7. A CONTROL IS JUDGED OVER THE SET'S BEHAVIOURAL SUITES, not the ones it
     names, and a crash or a zero-check suite is not an escape. A control that
     picks its own jury is the oldest defect this file has had.
  8. A DIGEST IS NOT A GUARD. When only an opaque golden digest moves, a freeze
     re-baseline carries the mutation through: DIGEST-ONLY, never a pass.
  9. THE BOTTOM LINE MAY NOT CONTRADICT THE EXIT CODE, and a -k subset or a
     set with no control may not read as a merge-gate result.

Usage:
  .claude/mutation-gate.py .claude/mutations/<set>.json [-k NAME] [--dry-run]
  .claude/mutation-gate.py .claude/mutations/<set>.json --anchors-only
      Anti-rot only: re-binds every anchor against the target in YOUR working
      tree. No checkout, no suite, sub-second, and it does not care how dirty
      the tree is -- that is what makes it usable in S0 preflight mid-work.
"""
import argparse
import atexit
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import shutil
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SUMMARY_RE = re.compile(r"(\d+)\s+passed,\s+(\d+)\s+failed")
FAIL_RE = re.compile(r"^\s*FAIL\s+(.*)$", re.M)
CHECK_RE = re.compile(r"^\s*(?:PASS|FAIL)\s+(.*)$", re.M)

# Module state so the atexit/signal restorer can reach it without a global
# object graph. `_ORIGINAL` is the authority; nothing else may write the target.
# Module state. `_ORIGINAL` is the authority for the private checkout's copy of
# the target; nothing else may write it.
_TARGET = None        # path INSIDE the private checkout
_ORIGINAL = None      # bytes
WORK = None           # the private checkout; None until main() makes one
_WORK_PARENT = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make_private_checkout():
    """A throwaway `git worktree` at HEAD. Returns its path, or None.

    [2026-09-09 round-9] THIS IS THE WHOLE DESIGN. The gate used to mutate
    PRODUCT SOURCE in the working tree you are sitting in, and then spent ~250
    lines trying to police that shared tree: a dirty-tree refusal, a live-run
    check, an O_EXCL lock with an owner pid, a backup, a hash-verified restore
    on four exit paths, `--recover`, and a per-suite whole-tree scan. Four
    consecutive review rounds found new accident-class defects in that
    machinery and nowhere else -- two gates racing, a dry run deleting a live
    run's lock, `--recover` rewriting a file a live run was measuring, the
    operator alarm and the gate disabling each other, an editor swapfile
    reddening CI. Measuring in a directory other writers share is the defect.
    A private checkout deletes the question instead of answering it: nothing
    else can touch this tree, so there is nothing to lock, restore or detect.
    """
    global WORK, _WORK_PARENT
    _WORK_PARENT = tempfile.mkdtemp(prefix="mutation-gate-")
    WORK = os.path.join(_WORK_PARENT, "w")     # must not exist yet
    r = subprocess.run(["git", "worktree", "add", "--detach", "--quiet",
                        WORK, "HEAD"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"REFUSING: could not create a private checkout: "
              f"{r.stderr.strip()}", file=sys.stderr)
        WORK = None
        return None
    return WORK


def drop_private_checkout():
    """Remove the checkout. Safe to call repeatedly, and safe to fail.

    Nothing here can damage the operator's tree: the worst case is a stray
    directory under the system temp dir and a stale `git worktree` entry, which
    `git worktree prune` collects. That is the point of the design -- cleanup
    is best-effort rather than load-bearing.
    """
    global WORK
    if WORK:
        subprocess.run(["git", "worktree", "remove", "--force", WORK],
                       cwd=ROOT, capture_output=True)
        WORK = None
    if _WORK_PARENT:
        shutil.rmtree(_WORK_PARENT, ignore_errors=True)


def reset_target():
    """Put the private copy of the target back for the next mutation.

    Unlike the old `restore()`, nothing here is load-bearing: this file lives
    in a throwaway checkout, so a failure costs the run and nothing else.
    """
    with open(_TARGET, "wb") as fh:
        fh.write(_ORIGINAL)


def _on_signal(signum, _frame):
    print(f"\n[mutation-gate] signal {signum} - dropping the private checkout",
          file=sys.stderr)
    drop_private_checkout()
    # 128+n is the shell's convention for death by signal; keep it visible.
    os._exit(128 + signum)


def target_is_dirty(rel):
    """Is the ONE file the mutations describe uncommitted? None if git fails.

    This is the only thing the gate asks about your working tree, and it asks
    for a provenance reason rather than a safety one: the checkout is taken at
    HEAD, so uncommitted edits to the guard are NOT what gets measured. Every
    other file may be as dirty as you like.
    """
    try:
        r = subprocess.run(["git", "status", "--porcelain", "--", rel],
                           cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return [ln for ln in r.stdout.splitlines() if ln.strip()]



def run_suite(suite):
    """Run one standalone suite directly.

    Returns (passed, failed, crashed, fail_names, seconds, all_check_names). `crashed` means the
    suite printed no summary line, or exited non-zero with no failing check --
    red, but NOT evidence that a check caught anything.
    """
    path = os.path.join(WORK, "tests", suite)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # A stray module beside a script shadows the stdlib; keep the child honest.
    env["PYTHONSAFEPATH"] = "1"
    t0 = time.monotonic()
    r = subprocess.run([sys.executable, path], cwd=WORK, capture_output=True,
                       text=True, env=env)
    dt = time.monotonic() - t0
    out = r.stdout + r.stderr
    hits = SUMMARY_RE.findall(out)
    if not hits:
        return (0, 0, True, [], dt, [])
    p, f = int(hits[-1][0]), int(hits[-1][1])
    return (p, f, r.returncode != 0 and f == 0, FAIL_RE.findall(out), dt,
            CHECK_RE.findall(out))


def main(argv):
    global _TARGET, _ORIGINAL
    ap = argparse.ArgumentParser(prog="mutation-gate")
    ap.add_argument("mutation_set", help="path to a mutation-set JSON file")
    ap.add_argument("-k", dest="only", help="run only mutations whose id "
                                            "contains this substring")
    ap.add_argument("--dry-run", action="store_true",
                    help="check anchors and baseline; apply nothing")
    ap.add_argument("--anchors-only", action="store_true",
                    help="check only that every anchor still matches exactly "
                         "once; runs no suite. Sub-second, so it can run in S0 "
                         "preflight -- this is the anti-rot check")
    args = ap.parse_args(argv)
    if args.anchors_only:
        args.dry_run = True   # --anchors-only is --dry-run minus the baseline

    # [2026-09-09 round-7] Hash the bytes we PARSE, once, here. The provenance
    # stamp used to be computed by RE-READING the file after the run -- and
    # GUARD 1 deliberately permits an UNCOMMITTED set (runbook step 4b has you
    # author it before committing), for which GUARD 10 is structurally blind:
    # the porcelain line stays `?? <path>` whatever the bytes become. MEASURED:
    # one editor save 34 s into a 126 s run left the table stamped with a sha
    # that did NOT produce it, under the printed words "the SET-SHA256 below is
    # what actually ran", at MERGE GATE: PASS rc 0. The stamp exists so a pasted
    # table cannot be attributed to a set it did not come from, and that was the
    # one thing it could not do.
    with open(args.mutation_set, "rb") as fh:
        _set_bytes = fh.read()
    set_sha = sha(_set_bytes)
    spec = json.loads(_set_bytes.decode("utf-8"))
    _TARGET = os.path.join(ROOT, spec["target"])
    guard = spec.get("guard", os.path.basename(args.mutation_set))
    n_total = len(spec["mutations"])
    muts = [m for m in spec["mutations"]
            if not args.only or args.only in m["id"]]
    # `expect` maps a suite to the check-name substring that must go red there,
    # or to null for "this suite is expected NOT to see it". Naming the null
    # cells is what turns the report into a COVERAGE table rather than a
    # pass/fail light: it records which guard is load-bearing for which bypass.
    suites = sorted({s for m in muts for s in m["expect"]})

    print(f"mutation-gate: {guard}")
    print(f"  target  {spec['target']}")
    print(f"  set     {args.mutation_set}  ({len(muts)} mutations)")
    print(f"  suites  {', '.join(suites)}\n")

    # ---- ANCHORS-ONLY: no checkout, no suite, no isolation needed. -------
    # It applies nothing and runs nothing; it re-binds every `find` against the
    # target you are LOOKING AT, which is what makes it useful mid-work in S0
    # preflight. A dirty tree is fine here, by design.
    if args.anchors_only:
        _live = os.path.join(ROOT, spec["target"])
        try:
            with open(_live, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            print(f"REFUSING: cannot read {spec['target']}: {exc}",
                  file=sys.stderr)
            return 2
        rows, rc = [], 0
        print("ANCHORS ONLY - no checkout, no suite run, nothing applied\n")
        for m in muts:
            n = text.count(m["find"])
            if n != 1:
                rows.append({"id": m["id"],
                             "verdict": "ROTTED" if n == 0 else "AMBIGUOUS",
                             "detail": f"anchor matched {n} times; the mutation "
                                       f"no longer describes the guard"})
                rc = 1
                print(f"  {m['id']:<26} ANCHOR {n}x -> {rows[-1]['verdict']}")
            else:
                rows.append({"id": m["id"], "verdict": "ANCHOR-OK", "detail": ""})
                print(f"  {m['id']:<26} anchor 1x")
        print("\n" + "=" * 96)
        print(f"SET-SHA256 {set_sha[:32]}  {os.path.basename(args.mutation_set)}")
        _bad = [r for r in rows if r["verdict"] != "ANCHOR-OK"]
        print(f"ANCHORS: {len(rows) - len(_bad)}/{len(rows)} still bind against "
              f"the WORKING tree. NOT a merge-gate result - nothing was applied.")
        for r in _bad:
            print(f"  {r['id']:<26} {r['verdict']:<18} {r['detail']}")
        return rc

    # ---- GUARD 1: THE TARGET MUST BE COMMITTED. --------------------------
    # The only question the gate asks about your working tree, and it asks for
    # a PROVENANCE reason, not a safety one: the checkout below is taken at
    # HEAD, so uncommitted edits to the guard are not what gets measured. A
    # silent "you tested something other than what you are looking at" is the
    # false-green class this whole harness exists to prevent. Every OTHER file
    # in your tree may be dirty -- that is the point of the private checkout.
    _td = target_is_dirty(spec["target"])
    if _td is None:
        print("REFUSING: could not read git status for "
              f"{spec['target']}.", file=sys.stderr)
        return 2
    if _td:
        print(f"REFUSING: {spec['target']} has uncommitted changes:",
              file=sys.stderr)
        for ln in _td:
            print("   ", ln, file=sys.stderr)
        print("  This gate measures HEAD in a private checkout, so those edits "
              "would NOT be what it reports on. Commit them first.\n  (Every "
              "other file in your tree may be dirty; only this one matters.)",
              file=sys.stderr)
        return 2

    # ---- THE PRIVATE CHECKOUT. -------------------------------------------
    _head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True)
    if make_private_checkout() is None:
        return 2
    atexit.register(drop_private_checkout)
    _TARGET = os.path.join(WORK, spec["target"])
    with open(_TARGET, "rb") as fh:
        _ORIGINAL = fh.read()
    orig_sha = sha(_ORIGINAL)
    print(f"  measuring {_head.stdout.strip()} in a private checkout "
          f"(target sha256 {orig_sha[:16]}); your working tree is untouched\n")

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    rows = []
    rc = 0
    try:
        # ---- GUARD 3: the baseline MUST be green, per suite. ----
        # `--anchors-only` skips it deliberately: that mode makes no claim about
        # redness, so it needs no green baseline, and skipping it is what keeps
        # the anti-rot check sub-second and therefore runnable in S0 preflight.
        baseline_checks = {}
        for s in [] if args.anchors_only else suites:
            if s == suites[0]:
                print("BASELINE (unmutated) - every mutation is vacuously "
                      "'caught' if this is red")
            p, f, crashed, _names, dt, _all = run_suite(s)
            baseline_checks[s] = _all
            vacuous = not crashed and p + f == 0
            state = ("CRASHED" if crashed else
                     "VACUOUS (0 checks)" if vacuous else
                     ("GREEN" if f == 0 else "RED"))
            print(f"  {s:<28} {p:>4} passed, {f:>3} failed  {dt:>5.1f}s  {state}")
            if vacuous:
                # [2026-09-09 round-4] A suite that SKIPS reports "0 passed, 0
                # failed" and exits 0. That read GREEN here and then counted as
                # a suite the control "escaped" -- an escape from a jury that
                # never sat. MEASURED with test_wrapper_behavior.py under a
                # flock-less PATH: CONTROL-OK, MERGE GATE: PASS, rc 0.
                print("\nREFUSING: baseline suite ran 0 checks (skipped?). It "
                      "cannot witness anything, so no row scored against it "
                      "would mean anything.", file=sys.stderr)
                return 2
            if crashed or f:
                print("\nREFUSING: baseline is not green. Every mutation would "
                      "'turn it red' and the report would mean nothing.",
                      file=sys.stderr)
                return 2
        print()

        # ---- GUARD 4b: a declared check name must IDENTIFY ONE CHECK. ----
        # [2026-09-09 round-6] `want` is matched as a SUBSTRING of failing check
        # names, so a short or generic string scores RED@check against whatever
        # happens to fail. MEASURED at 8f93fd4: want "s" made a row labelled
        # `stops-too-soon-break` score CAUGHT against an unrelated check. A
        # declared expectation that does not pick out exactly one check in the
        # suite's own baseline is not an expectation.
        if not args.dry_run:
            _bad_want = []
            _dsq = set(spec.get("digest_suites", []))
            for _m in muts:
                for _s, _w in sorted(_m["expect"].items()):
                    if _w is None:
                        continue
                    _n = sum(1 for _c in baseline_checks.get(_s, []) if _w in _c)
                    # A DIGEST suite moves for any byte of an emitted file, so
                    # naming one check there is meaningless by construction --
                    # and GUARD 9 already refuses to count a digest-only catch.
                    # Require only that the name matches something real.
                    _need = ">=1" if _s in _dsq else "exactly 1"
                    if (_n < 1) if _s in _dsq else (_n != 1):
                        _bad_want.append(f"{_m['id']}/{_s}: {_w!r} matches "
                                         f"{_n} checks, need {_need}")
            if _bad_want:
                print("REFUSING: a declared check name does not identify "
                      "exactly one check in that suite's baseline:",
                      file=sys.stderr)
                for _b in _bad_want:
                    print("   ", _b, file=sys.stderr)
                return 2

        if args.dry_run:
            print("ANCHORS ONLY - no suite run, nothing applied\n"
                  if args.anchors_only else
                  "DRY RUN - anchors only, nothing applied\n")

        for m in muts:
            text = _ORIGINAL.decode("utf-8")
            find, repl = m["find"], m["replace"]
            n = text.count(find)
            row = {"id": m["id"], "verdict": None, "detail": ""}

            # ---- GUARD 4: the anchor must match exactly once. ----
            if n != 1:
                row["verdict"] = "ROTTED" if n == 0 else "AMBIGUOUS"
                row["detail"] = (f"anchor matched {n} times; the mutation no "
                                 f"longer describes the guard")
                rows.append(row)
                rc = 1
                print(f"  {m['id']:<26} ANCHOR {n}x -> {row['verdict']}")
                continue
            if args.dry_run:
                row["verdict"] = "ANCHOR-OK"
                rows.append(row)
                print(f"  {m['id']:<26} anchor 1x")
                continue

            mutated = text.replace(find, repl, 1).encode("utf-8")

            # ---- GUARD 5: the bytes must actually change. ----
            if sha(mutated) == orig_sha:
                row["verdict"] = "MUTATION-NOOP"
                row["detail"] = "find == replace; nothing was changed"
                rows.append(row)
                rc = 1
                print(f"  {m['id']:<26} NOOP")
                continue

            with open(_TARGET, "wb") as fh:
                fh.write(mutated)
            with open(_TARGET, "rb") as fh:
                on_disk = fh.read()
            if sha(on_disk) != sha(mutated):
                reset_target()
                row["verdict"] = "WRITE-FAILED"
                rows.append(row)
                rc = 1
                continue
            print(f"  {m['id']:<26} applied; sha256 {sha(on_disk)[:16]} "
                  f"(was {orig_sha[:16]})")

            caught_by, surprises, went_red, went_crashed = [], [], [], []
            dsuites_pre = set(spec.get("digest_suites", []))
            # [2026-09-09 re-review fix A] A CONTROL IS JUDGED OVER THE SET'S
            # BEHAVIOURAL SUITES, NOT OVER THE ONES IT NAMES. The blocker-1 fix
            # judged it over `m["expect"]`, which left the same defect standing
            # one JSON line away: `"expect": {}` runs no suite, records no
            # redness, and reads as "escaped, as required". MEASURED on 756c95e:
            # `probe-defanged` -- a real guard removal this very set proves both
            # suites catch -- marked `"control": true` with an empty expect
            # scored CONTROL-OK and the run printed MERGE GATE: PASS, rc 0.
            # A control's claim is about THIS SET's suites. It does not get to
            # pick its own jury. `suites` is the union the baseline proved green,
            # so judging over it keeps GUARD 3's invariant intact.
            is_ctl = bool(m.get("control"))
            ctl_suites = [s for s in suites if s not in dsuites_pre]
            plan = ([(s, None) for s in ctl_suites] if is_ctl
                    else sorted(m["expect"].items()))
            for s, want in plan:
                p, f, crashed, names, dt, _all = run_suite(s)
                hit = [x for x in names if want and want in x]
                if crashed:
                    state = "CRASHED"
                elif p + f == 0:
                    state = "VACUOUS (0 checks)"
                elif f == 0:
                    state = "green (blind, as declared)" if want is None \
                        else "GREEN"
                elif hit:
                    state = "RED@check"
                elif want is None and s in dsuites_pre:
                    # A digest moves for any byte of an emitted file. Saying
                    # "wrong reason" here would train the reader to ignore the
                    # label on the rows where it matters.
                    state = "digest moved (expected; emitted file)"
                else:
                    state = "RED-WRONG-REASON"
                print(f"      {s:<28} {p:>4}/{f:<3} {dt:>5.1f}s  {state}"
                      + (f"  <- {hit[0].strip()[:58]}" if hit else ""))
                # [2026-09-08 review blocker 1] Record RAW redness, independent of
                # `expect`. A control declares every suite null, so `caught_by`
                # is empty for it BY CONSTRUCTION and judging a control on
                # `caught_by` made CONTROL-OK unconditional -- the control could
                # never fail, which is the exact defect this gate exists to find.
                if f and not crashed:
                    went_red.append(s)
                # [2026-09-09 re-review fix B] A CRASH IS NOT AN ESCAPE. The
                # blocker-1 fix recorded redness only when `f and not crashed`,
                # so a control that CRASHED every suite recorded nothing and
                # scored CONTROL-OK. MEASURED on 756c95e: a control replacing
                # `def _bash_case_words(words):` with a SyntaxError ran both
                # suites to `0/0 CRASHED` and the gate reported "escaped, as
                # required: the suites are not red-for-everything", MERGE GATE:
                # PASS, rc 0 -- of suites that executed no checks at all.
                # A crash is also invisible below: the blind-cell branch needs
                # `f`, and a crash reports f == 0, so nothing flagged it.
                if crashed or (p + f == 0):
                    went_crashed.append(s)
                    surprises.append(f"{s} ran 0 checks (crashed or skipped), "
                                     f"so this row is evidence of nothing")
                if state == "RED@check":
                    caught_by.append(s)
                elif want is None and f and s not in dsuites_pre:
                    # Declared blind, went red anyway: the coverage table is
                    # stale, or the mutation is broader than it claims.
                    surprises.append(f"{s} went red though declared blind")
                elif want is not None and not crashed and p + f:
                    # A crashed cell already recorded a better-worded surprise
                    # just above; do not report it twice.
                    surprises.append(f"{s}: {state}, wanted {want!r}")

            # ---- GUARD 6: red at the NAMED check, or it does not count. ----
            # ---- GUARD 8: a CONTROL must ESCAPE. -------------------------
            # A harness that reports "all caught" is only meaningful if
            # something can still get through it. A control is a one-line edit
            # to the same file that these suites are known NOT to see; if it
            # ever reports CAUGHT, the suites have become red-for-everything
            # and every other row above is vacuous.
            # A digest moves for ANY edit to an emitted file, so a control is
            # judged on the BEHAVIOURAL suites only -- otherwise no control
            # could ever be written for `lib/templates.py`.
            dsuites = set(spec.get("digest_suites", []))
            real_catch = [s for s in caught_by if s not in dsuites]
            # Judge the control on RAW redness in the behavioural suites.
            ctl_red = [s for s in went_red if s not in dsuites]
            ctl_crashed = [s for s in went_crashed if s not in dsuites]
            if is_ctl:
                real_catch = ctl_red
                if not ctl_suites:
                    # No behavioural suite to escape from: the set names only
                    # digest suites, so nothing could ever demonstrate that
                    # these suites are not red-for-everything.
                    row["verdict"] = "CONTROL-VACUOUS"
                    row["detail"] = ("this set names no behavioural (non-digest) "
                                     "suite, so the control proves nothing")
                    rc = 1
                elif ctl_crashed:
                    # A crash is not an escape: the suite executed no checks.
                    row["verdict"] = "CONTROL-CRASHED"
                    row["detail"] = (
                        f"{', '.join(ctl_crashed)} crashed - 0 checks ran, so "
                        f"nothing was demonstrated about them")
                    rc = 1
                elif real_catch:
                    row["verdict"] = "CONTROL-FAILED"
                    row["detail"] = (
                        f"went red in {', '.join(real_catch)} - either this "
                        f"control is not inert, or these suites are red for ANY "
                        f"edit; the printed per-suite states say which")
                    rc = 1
                else:
                    row["verdict"] = "CONTROL-OK"
                    row["detail"] = (
                        f"escaped {len(ctl_suites)} behavioural suite(s) "
                        f"({', '.join(ctl_suites)}): they are not "
                        f"red-for-everything")
                rows.append(row)
                reset_target()
                continue
            # ---- GUARD 9: a digest is not a guard. -----------------------
            # `.claude/readiness-queue.md:257` records the reason: when the only
            # thing that goes red is an opaque golden digest, a deliberate
            # freeze re-baseline carries the mutation through. That is a catch
            # on paper and no catch in practice, so it gets its own verdict and
            # does not count as a pass.
            if caught_by and not real_catch:
                row["verdict"] = "DIGEST-ONLY"
                row["detail"] = (f"only {', '.join(caught_by)} went red, and a "
                                 f"freeze re-baseline carries this through")
                rc = 1
                rows.append(row)
                reset_target()
                continue
            row["verdict"] = "CAUGHT" if caught_by else "ESCAPED"
            row["detail"] = (", ".join(caught_by) if caught_by
                             else "no suite went red at the named check")
            if surprises:
                row["detail"] += "  [!] " + "; ".join(surprises)
                rc = 1
            if not caught_by:
                rc = 1
            rows.append(row)
            reset_target()
    finally:
        drop_private_checkout()

    print("\n" + "=" * 96)
    # [critique fix 3] Provenance, so a pasted table cannot be attributed to a
    # set it did not come from, and a silent filter cannot hide behind "all caught".
    print(f"SET-SHA256 {set_sha[:32]}  {os.path.basename(args.mutation_set)}")
    print(f"MUTATIONS: {len(rows)}/{n_total} ran"
          + (f" ({n_total - len(rows)} filtered by -k {args.only!r})" if args.only else ""))
    print(f"{'mutation':<26} {'verdict':<18} caught by / why not")
    print("-" * 96)
    for r in rows:
        print(f"{r['id']:<26} {r['verdict']:<18} {r['detail']}")
    print("-" * 96)
    bad = [r for r in rows
           if r["verdict"] not in ("CAUGHT", "ANCHOR-OK", "CONTROL-OK")]
    if rc == 3:
        # [2026-09-09 round-4 fix] A FAILED RESTORE OUTRANKS EVERY OTHER
        # HEADLINE, and it must be tested FIRST. 1895c4a put this test at the
        # bottom of the chain, where it was reachable only when every row had
        # an accepted verdict. Measured: with one bad row the headline was the
        # coverage sentence and the unrestored tree was never named; under -k
        # or a no-control set the PARTIAL/INCONCLUSIVE branches additionally
        # reassigned rc = 1, so even `$?` lost the failed restore. The shipped
        # int-word set always has a bad row, so on it a failed restore could
        # never be announced at all.
        print("MERGE GATE: FAIL - THE TARGET WAS NOT RESTORED (rc=3). The "
              "working tree may still carry a mutation, which outranks every "
              "other result here. Fix that FIRST; nothing above is a merge-gate "
              "result until the target matches HEAD.")
    elif args.dry_run:
        # A dry run applied nothing, so it can say the anchors still bind and
        # NOTHING ELSE. Printing a PASS here would be the exact defect this
        # script exists to catch: a report that reads green without a run.
        print(f"DRY RUN: {len(rows) - len(bad)}/{len(rows)} anchors still bind. "
              f"NOT a merge-gate result - no mutation was applied.")
    elif bad:
        print(f"MERGE GATE: FAIL - {len(bad)} of {len(rows)} mutations are not "
              f"provably caught")
    else:
        caught = [r for r in rows if r["verdict"] == "CAUGHT"]
        ctl = [r for r in rows if r["verdict"] == "CONTROL-OK"]
        if args.only:
            # [critique fix 3] A -k run exercised a SUBSET. Reporting PASS from
            # a subset is precisely the "agrees with itself" failure this gate
            # exists to stop, and it is the shape a person reaches for under
            # time pressure at the context gate.
            print(f"PARTIAL: {len(caught)} of the set's {n_total} mutations ran "
                  f"(-k {args.only!r}). NOT a merge-gate result - re-run the "
                  f"whole set before merging.")
            rc = 1
        elif not ctl:
            # No control means nothing demonstrated that these suites CAN stay
            # green. "All caught" from a set with no control is the report a
            # broken harness gives, so it is not allowed to read as a pass.
            print("MERGE GATE: INCONCLUSIVE - this set has no negative "
                  "control, so nothing proved the suites are not simply red "
                  'for any edit. Add one `"control": true` mutation.')
            rc = 1
        elif not caught:
            # [critique fix 3] A set of controls only, or a set whose real
            # mutations were all filtered out, must not read green.
            print("MERGE GATE: INCONCLUSIVE - no real (non-control) mutation "
                  "was exercised, so nothing was proved removable-and-caught.")
            rc = 1
        elif rc:
            # [2026-09-09 re-review fix C] THE BOTTOM LINE MUST NOT CONTRADICT
            # THE EXIT CODE. `bad` is computed from verdicts alone, so a row
            # that is CAUGHT but carries a `[!]` surprise set rc=1 while this
            # block still printed PASS. MEASURED on 756c95e: a declared
            # expectation that never fired printed
            # "MERGE GATE: PASS ... 1 control(s) escaped as required" and
            # returned 1. A human reads the last line; only a script reads $?.
            # rc 3 cannot reach here: it is tested at the TOP of this chain.
            print(f"MERGE GATE: FAIL - every row has an accepted verdict, but "
                  f"the run raised rc={rc}: see the [!] notes above. A declared "
                  f"expectation did not fire, or a suite ran no checks, so the "
                  f"coverage table is wrong even though each bypass was caught.")
        else:
            print(f"MERGE GATE: PASS - {len(caught)}/{len(caught)} bypasses "
                  f"turn a NAMED check red; {len(ctl)} control(s) escaped as "
                  f"required")
    print("your working tree was never modified; the private checkout is gone")
    return rc


if __name__ == "__main__":
    # [2026-09-09 round-7] RUN WITH sys.path[0] REMOVED. A script's own
    # directory leads sys.path, so a module beside this one shadows the stdlib.
    # MEASURED: a sourceless, gitignored `.claude/subprocess.pyc` fabricated
    # every suite result -- "MERGE GATE: PASS - 4/4 bypasses turn a NAMED check
    # red" at rc 0 in 0.14 s instead of ~2 min, with git status empty, the
    # gate's own sha256 still matching its pin, and CI fully green. Re-exec
    # under -P so the real stdlib wins; the child suites get PYTHONSAFEPATH=1
    # from run_suite for the same reason (-P alone left tests/subprocess.pyc
    # able to do it). This is sabotage-class, not drift, but the fix is six
    # lines and the failure is total.
    if not sys.flags.safe_path:
        os.execv(sys.executable,
                 [sys.executable, "-P", os.path.abspath(__file__)] + sys.argv[1:])
    sys.exit(main(sys.argv[1:]))

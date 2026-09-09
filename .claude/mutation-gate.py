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

WHAT IT REFUSES TO DO. The failure mode of a mutation harness is to apply
nothing, run a suite, watch it go red for some unrelated reason, and report
"all caught". Every guard below exists because "all caught" is the answer this
script would give if it were broken:

  1. DIRTY TREE -> refuse. A pre-existing edit to the target is
     indistinguishable from a mutation, and restoring would destroy it.
  2. LEFTOVER BACKUP -> refuse. A previous run died hard; the tree may still
     carry a mutation. Recovery is the operator's call, not this script's.
  3. BASELINE MUST BE GREEN. If the suite is already red, every mutation is
     "caught" and the report is vacuous. Measured, printed, and required.
  4. THE ANCHOR MUST MATCH EXACTLY ONCE. Zero matches means the mutation has
     ROTTED against the guard it protects -- the single highest-value signal
     this script produces, and the one a prose mutation list cannot give. More
     than one means the edit is ambiguous. Either is an ERROR, never "caught".
  5. THE BYTES MUST ACTUALLY CHANGE. The post-write SHA-256 is compared to the
     pre-write one. A no-op rewrite reports MUTATION-NOOP, not "caught".
  6. RED IS NOT ENOUGH -- IT MUST BE RED AT THE NAMED CHECK. A mutation that
     makes the suite crash, or that trips an unrelated check (a golden digest
     moves for EVERY edit to `lib/templates.py`), is scored RED-WRONG-REASON,
     which is a failure of the gate, not a pass.
  7. RESTORE IS VERIFIED BY HASH, on every path: normal, exception, SIGINT,
     SIGTERM. A restore that did not restore is reported and exits non-zero.
  8. EVERY ROW IS VERIFIED AGAINST THE BYTES THIS RUN WROTE. The target is
     re-read after each suite; if it changed, the row is INTERFERED and the run
     fails. This does not depend on the lock below being correct.
  9. ONE RUN AT A TIME, PER TARGET. The backup is created O_EXCL before the
     baseline and held for the run, so a second gate against the same target
     refuses instead of interleaving writes. Without it two runs score rows on
     each other's bytes and an inert set can report "all caught".

Usage:
  .claude/mutation-gate.py .claude/mutations/<set>.json [-k NAME] [--dry-run]
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
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SUMMARY_RE = re.compile(r"(\d+)\s+passed,\s+(\d+)\s+failed")
FAIL_RE = re.compile(r"^\s*FAIL\s+(.*)$", re.M)
CHECK_RE = re.compile(r"^\s*(?:PASS|FAIL)\s+(.*)$", re.M)

# Module state so the atexit/signal restorer can reach it without a global
# object graph. `_ORIGINAL` is the authority; nothing else may write the target.
_TARGET = None
_ORIGINAL = None      # bytes
_BAK = None
_LOCK = None          # holds the owning PID; see GUARD 1b
_OWN_LOCK = False     # True only after THIS process wins the O_EXCL claim


def _lock_owner(path):
    """-> (pid, state) where state is "running", "dead" or "corrupt".

    A pid <= 0 is CORRUPT, not dead: os.kill would read it as a process GROUP
    and report every such lock as running. An unreadable or empty lock is also
    corrupt rather than dead -- the claim writes the pid immediately after the
    O_EXCL create, so an empty lock is a torn write, not a finished run.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read().strip()
        pid = int(raw)
    except (OSError, ValueError):
        return (None, "corrupt")
    if pid <= 0:
        return (pid, "corrupt")
    try:
        os.kill(pid, 0)          # signal 0 tests existence, sends nothing
    except ProcessLookupError:
        return (pid, "dead")
    except PermissionError:
        return (pid, "running")  # someone else's process: alive, not ours
    return (pid, "running")


def _stale_note(pid, state):
    return (f"owner pid {pid} is {state}"
            if state != "corrupt" else
            f"the lock is CORRUPT (contents {pid!r})")


HARNESS_BAK_DIR = os.path.join(ROOT, ".claude", "mutation-gate-backups")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def restore(reason="normal", release=False):
    """Put the target back and prove it by hash. Safe to call repeatedly.

    `release` drops the backup, which is ALSO this run's lock (see GUARD 1b).
    Between mutations we restore but keep the lock; only the terminal paths
    (finally, atexit, signal) release it.
    """
    if _TARGET is None or _ORIGINAL is None:
        return True
    try:
        with open(_TARGET, "rb") as fh:
            now = fh.read()
        if now != _ORIGINAL:
            with open(_TARGET, "wb") as fh:
                fh.write(_ORIGINAL)
        with open(_TARGET, "rb") as fh:
            back = fh.read()
    except OSError as exc:
        print(f"\nRESTORE FAILED ({reason}): {exc}\n"
              f"  The original bytes are in {_BAK}. Restore by hand.",
              file=sys.stderr)
        return False
    if sha(back) != sha(_ORIGINAL):
        print(f"\nRESTORE FAILED ({reason}): {_TARGET} does not hash to the "
              f"original.\n  The original bytes are in {_BAK}.", file=sys.stderr)
        return False
    # [2026-09-09 round-4 blocker] ONLY RELEASE A LOCK WE CLAIMED. --dry-run and
    # --anchors-only never claim one, but they still registered this restorer at
    # exit, so they DELETED A LIVE RUN'S lock and backup and handed the target
    # to a second gate. MEASURED: a plain --anchors-only (0.05 s) stripped a
    # running gate of both files in 2 of 3 trials, and another real run then
    # claimed the freed lock and mutated lib/templates.py concurrently -- the
    # exact false-PASS class GUARD 1b exists to close, reopened by the guard.
    if release and _OWN_LOCK:
        for _p in (_BAK, _LOCK):
            if _p and os.path.exists(_p):
                try:
                    os.unlink(_p)
                except OSError:
                    pass
    return True


def _on_signal(signum, _frame):
    print(f"\n[mutation-gate] signal {signum} - restoring {_TARGET}",
          file=sys.stderr)
    restore(f"signal {signum}", release=True)
    # 128+n is the shell's convention for death by signal; keep it visible.
    os._exit(128 + signum)


def tree_lines(paths=None):
    """Sorted porcelain status for the WHOLE tree (or the given paths).

    [2026-09-09 round-6] The gate used to check only the target and the suite
    FILES. But the suites import the rest of lib/, so a foreign write to any
    other file changes what they measure. MEASURED at 8f93fd4: a concurrent
    one-line edit to lib/cmdpos.py turned an INERT comment mutation into
    CAUGHT and the run printed MERGE GATE: PASS at rc 0, with the target
    byte-identical throughout and no INTERFERED row. The unit of isolation is
    the REPO, not the file.
    """
    cmd = ["git", "status", "--porcelain"] + (["--"] + list(paths) if paths else [])
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return sorted(ln for ln in r.stdout.splitlines() if ln.strip())


def run_suite(suite):
    """Run one standalone suite directly.

    Returns (passed, failed, crashed, fail_names, seconds, all_check_names). `crashed` means the
    suite printed no summary line, or exited non-zero with no failing check --
    red, but NOT evidence that a check caught anything.
    """
    path = os.path.join(ROOT, "tests", suite)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    t0 = time.monotonic()
    r = subprocess.run([sys.executable, path], cwd=ROOT, capture_output=True,
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
    global _TARGET, _ORIGINAL, _BAK, _LOCK, _OWN_LOCK
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
    ap.add_argument("--recover", action="store_true",
                    help="restore the target from a backup left by a run that "
                         "died on SIGKILL, then delete the backup")
    args = ap.parse_args(argv)
    if args.anchors_only:
        args.dry_run = True   # --anchors-only is --dry-run minus the baseline

    with open(args.mutation_set, encoding="utf-8") as fh:
        spec = json.load(fh)
    _TARGET = os.path.join(ROOT, spec["target"])
    # [critique fix 5] The backup must NOT sit beside the target: the target is
    # PRODUCT source under lib/, and no harness artifact may persist there --
    # a crashed run would leave lib/*.mutation-gate.bak in the product tree and
    # a `git add -A` would ship it. Keep it in the harness dir instead, named
    # after the target so a recovery cannot cross-apply between sets.
    _BAK = os.path.join(HARNESS_BAK_DIR,
                        spec["target"].replace(os.sep, "__") + ".mutation-gate.bak")
    # [2026-09-09 round-6] ONE LOCK FOR THE REPO, not one per target. Two gates
    # on DIFFERENT targets were not mutually excluded even though their suites
    # read the same product files, so each measured rows against the other's
    # mutation.
    _LOCK = os.path.join(HARNESS_BAK_DIR, "mutation-gate.lock")
    os.makedirs(HARNESS_BAK_DIR, exist_ok=True)
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

    # SIGKILL cannot be trapped, so guard 7 cannot cover it. What survives is
    # the backup file, and `--recover` is the only sanctioned way to consume it.
    # It restores ONLY when the backup matches the target's committed content,
    # so it can never be used to launder an unrelated edit into the tree.
    if args.recover:
        # [2026-09-09 round-4] REFUSE AGAINST A LIVE RUN. MEASURED: with a gate
        # run in flight, --recover recognised its in-flight mutation as "one of
        # this set's declared mutations", rewrote the target MID-MEASUREMENT,
        # deleted the lock -- destroying the mutual exclusion GUARD 1b exists
        # to provide -- and exited 0. The live run's verdict went PASS -> FAIL.
        _stale_lock = False
        if os.path.exists(_LOCK):
            _pid, _state = _lock_owner(_LOCK)
            if _state == "running":
                print(f"REFUSING to recover: mutation-gate pid {_pid} is "
                      f"RUNNING and holds {spec['target']}. Recovering now "
                      f"would rewrite the file it is measuring. Wait for it.",
                      file=sys.stderr)
                return 2
            _stale_lock = True
            print(f"note: stale lock ({_stale_note(_pid, _state)}); continuing")
        if not os.path.exists(_BAK):
            # [2026-09-09 round-4] CLEAR THE STALE LOCK HERE. A crash between
            # the claim and the backup write, or an operator following GUARD 2's
            # old advice to "delete the backup", leaves a lock with NO backup --
            # and this early return used to exit 0 without touching it, so every
            # later run refused forever. MEASURED: SIGKILL -> GUARD 2 -> delete
            # the backup as instructed -> GUARD 1b -> --recover rc 0 "nothing to
            # recover" -> next run rc 2, repeating indefinitely. --recover is the
            # sanctioned way out, so it must actually be one.
            if _stale_lock:
                os.unlink(_LOCK)
                print(f"cleared the stale lock; {_BAK} does not exist, so the "
                      f"target was never left mutated. Nothing else to do.")
                return 0
            print(f"nothing to recover: {_BAK} does not exist")
            return 0
        with open(_BAK, "rb") as fh:
            bak = fh.read()
        try:
            r = subprocess.run(["git", "show", f"HEAD:{spec['target']}"],
                               cwd=ROOT, capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            r = None
        if r is None or r.returncode != 0:
            print("REFUSING to recover: cannot read the committed version of "
                  f"{spec['target']}.", file=sys.stderr)
            return 2
        # [2026-09-08 review blocker 2] REFUSE IF THE CURRENT FILE IS NOT A
        # RECOGNISED GATE MUTATION. The first version compared only backup vs
        # HEAD and then overwrote, so pointing --recover at a target carrying
        # real uncommitted work DESTROYED it -- and the runbook's own E6
        # carve-out routes a dirty target here. Recovery is only safe when the
        # current bytes are HEAD plus exactly one mutation this set declares.
        with open(_TARGET, "rb") as fh:
            cur = fh.read()
        if cur != r.stdout:
            head_txt = r.stdout.decode("utf-8", "replace")
            cur_txt = cur.decode("utf-8", "replace")
            known = False
            for m in spec["mutations"]:
                if head_txt.count(m["find"]) == 1 and \
                        head_txt.replace(m["find"], m["replace"], 1) == cur_txt:
                    known = True
                    print(f"recognised in-place mutation {m['id']!r}")
                    break
            if not known:
                print("REFUSING to recover: the target differs from HEAD and the "
                      "difference is NOT one of this set's declared mutations. "
                      "That is uncommitted work, not a crashed gate run. Inspect "
                      "`git diff` and resolve it by hand; --recover will not "
                      "overwrite it.", file=sys.stderr)
                return 1
        if sha(bak) != sha(r.stdout):
            print("REFUSING to recover: the backup does not match "
                  f"HEAD:{spec['target']}. The dead run started from an "
                  "uncommitted tree, so restoring it is not this script's call.",
                  file=sys.stderr)
            return 2
        with open(_TARGET, "wb") as fh:
            fh.write(bak)
        os.unlink(_BAK)
        if os.path.exists(_LOCK):
            os.unlink(_LOCK)
        print(f"recovered {spec['target']} to sha256 {sha(bak)[:16]}; "
              f"backup and stale lock deleted")
        return 0

    # ---- GUARD 1a: IS ANOTHER RUN LIVE? ---------------------------------
    # [2026-09-09 round-4] This must precede GUARD 2. GUARD 2 only sees "a
    # backup exists" and says "a previous run died ... restore by hand, then
    # delete the backup" -- advice that, aimed at a HEALTHY RUNNING gate,
    # destroys its safety net. MEASURED at 674798a: a live run (pid alive, lock
    # held, later MERGE GATE: PASS rc 0) made both a second run and
    # --anchors-only refuse with "a previous run died".
    if os.path.exists(_LOCK):
        _pid, _state = _lock_owner(_LOCK)
        if _state == "running":
            print(f"REFUSING: mutation-gate pid {_pid} is RUNNING and holds "
                  f"{spec['target']}. This is not a crash; wait for it to "
                  f"finish. (Even --dry-run and --anchors-only refuse here: the "
                  f"target is mutated right now, so any anchor result would be "
                  f"about the mutation, not the guard.)", file=sys.stderr)
            return 2
        print(f"REFUSING: a stale lock is present ({_stale_note(_pid, _state)}), "
              f"so a previous run died holding {spec['target']}.\n  Run "
              f"`{os.path.relpath(__file__, ROOT)} {args.mutation_set} --recover`"
              f" -- it restores the target if a backup survived, and clears the "
              f"lock either way.", file=sys.stderr)
        return 2

    # ---- GUARD 2: a leftover backup means a previous run died mutated. ----
    if os.path.exists(_BAK):
        print(f"REFUSING: {_BAK} exists with no lock beside it. A previous run "
              f"died while the target was mutated.\n  Compare it with "
              f"{spec['target']} and restore by "
              f"hand, then delete the backup.", file=sys.stderr)
        return 2

    # ---- GUARD 1: refuse on a dirty target or a dirty suite. ----
    # The mutation SET may legitimately be uncommitted: runbook step 4b has you
    # author it before it is committed. Everything else must be clean, because
    # the suites read the whole tree.
    _setrel = os.path.relpath(os.path.abspath(args.mutation_set), ROOT)
    dirty = tree_lines()
    if dirty is not None:
        _set_dirty = [ln for ln in dirty if ln[3:].strip().strip('"') == _setrel]
        dirty = [ln for ln in dirty if ln not in _set_dirty]
        if _set_dirty:
            print(f"  note: the mutation set is uncommitted ({_setrel}); the "
                  f"SET-SHA256 below is what actually ran")
    if dirty is None:
        print("REFUSING: could not read git status. This script rewrites a "
              "tracked file; without a clean-tree proof it will not run.",
              file=sys.stderr)
        return 2
    if dirty:
        print("REFUSING: the working tree is dirty. The suites read the whole "
              "tree, so ANY uncommitted file can change what they measure:",
              file=sys.stderr)
        for ln in dirty:
            print("   ", ln, file=sys.stderr)
        print("  A pre-existing edit is indistinguishable from a mutation, and "
              "restoring would destroy it. Commit or stash first.",
              file=sys.stderr)
        return 2

    # The tree as GUARD 1 accepted it. GUARD 10 requires every later scan to
    # equal this, plus the target we mutated ourselves and nothing else.
    _clean_tree = list(dirty) + list(_set_dirty)
    _tgtrel = spec["target"]
    with open(_TARGET, "rb") as fh:
        _ORIGINAL = fh.read()
    orig_sha = sha(_ORIGINAL)
    print(f"  clean tree; target sha256 {orig_sha[:16]}\n")

    # ---- GUARD 1b: CLAIM THE TARGET FOR THE WHOLE RUN. ------------------
    # [2026-09-09 round-4 blocker] Nothing used to claim the target, and GUARD 2
    # only sampled once at startup. Two gates run at once therefore scored rows
    # on EACH OTHER'S bytes. MEASURED across two independent reviewers: 7 of 8
    # aligned trials produced a WRONG table, and a sham set whose only mutation
    # is an inert comment printed "MERGE GATE: PASS" at rc 0 because the OTHER
    # run's real mutation was on disk when the suite ran. That is a false PASS
    # needing no dishonesty -- just two runs, or one run and a stale background
    # job. An earlier review called this "unproven" after seeing identical
    # tables from two runs of the SAME set; that was the one shape that hides it.
    # The backup doubles as the lock: created O_EXCL here, held to the end, so a
    # second run loses the race and hits this same guard instead of interleaving.
    if not args.dry_run:
        try:
            _fd = os.open(_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            _pid, _alive = _lock_owner(_LOCK)
            print(f"REFUSING: {_LOCK} exists (owner pid {_pid}, "
                  f"{'RUNNING' if _alive else 'dead'}). "
                  + (f"Another mutation-gate run holds {spec['target']} right "
                     "now; wait for it." if _alive else
                     "That run died. Compare the backup with the target and "
                     "resolve by hand, or use --recover."), file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"REFUSING: cannot claim {_LOCK}: {exc}", file=sys.stderr)
            return 2
        # Write the pid before anything can observe the file, then mark
        # ownership: only a process that got HERE may ever release the lock.
        os.write(_fd, str(os.getpid()).encode())
        os.close(_fd)
        _OWN_LOCK = True
        with open(_BAK, "wb") as fh:
            fh.write(_ORIGINAL)

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)
    atexit.register(lambda: restore("atexit", release=True))

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

            # The backup was written once under GUARD 1b and is this run's
            # lock; do not truncate and rewrite it per mutation.
            with open(_TARGET, "wb") as fh:
                fh.write(mutated)
            with open(_TARGET, "rb") as fh:
                on_disk = fh.read()
            if sha(on_disk) != sha(mutated):
                restore("write-verify")
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
            interfered = []
            for s, want in plan:
                p, f, crashed, names, dt, _all = run_suite(s)
                # ---- GUARD 10: THE ROW MUST BE ABOUT THE BYTES WE WROTE. ----
                # [2026-09-09] The lock (GUARD 1b) tries to PREVENT a second
                # writer; this VERIFIES the result regardless of whether the
                # lock worked. Three separate blockers in this file have come
                # from rows scored on somebody else's bytes -- two gates racing,
                # a dry run deleting a live lock, --recover rewriting a target
                # mid-measurement -- and each time the lock was patched and a
                # new hole appeared. This check does not depend on the lock
                # being correct: the gate knows exactly what it wrote, so it
                # reads the file back and refuses to score a suite that ran
                # against anything else. It also catches what no lock can -- a
                # human editing the target by hand while the gate runs.
                try:
                    with open(_TARGET, "rb") as _fh:
                        _now = _fh.read()
                except OSError:
                    _now = None
                _why = None
                if _now != mutated:
                    _why = "the target changed under this run"
                else:
                    # ...and NOTHING ELSE in the tree may have moved either.
                    _tl = tree_lines()
                    if _tl is None:
                        _why = "git status unreadable, so the tree is unverified"
                    else:
                        _foreign = [ln for ln in _tl
                                    if ln not in _clean_tree
                                    and ln[3:].strip().strip('"') != _tgtrel]
                        if _foreign:
                            _why = (f"another file changed under this run: "
                                    f"{'; '.join(x.strip() for x in _foreign[:3])}")
                if _why:
                    interfered.append(s)
                    print(f"      {s:<28} {'':>8}  {dt:>5.1f}s  "
                          f"INTERFERED - {_why}")
                    continue
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
            if interfered:
                row["verdict"] = "INTERFERED"
                row["detail"] = (
                    f"the target changed under {', '.join(interfered)} - another "
                    f"writer touched it mid-run, so nothing here is evidence")
                rc = 1
                rows.append(row)
                if not restore("between mutations"):
                    rc = 3
                    break
                continue
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
                if not restore("between mutations"):
                    rc = 3
                    break
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
                if not restore("between mutations"):
                    rc = 3
                    break
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

            # ---- GUARD 7: restore, verified by hash, before the next one. ----
            if not restore("between mutations"):
                # [2026-09-09 round-4] Was `return 3`, which left main before
                # the summary: MEASURED with chmod 0444 mid-run, the run gave
                # rc 3 and printed NO table, NO SET-SHA256 and NOT the rc-3
                # headline -- only three stderr lines. Break to the summary so
                # the loudest outcome this script has is stated where the
                # operator is already reading.
                rc = 3
                break
    finally:
        if not restore("finally", release=True):
            rc = 3

    print("\n" + "=" * 96)
    # [critique fix 3] Provenance, so a pasted table cannot be attributed to a
    # set it did not come from, and a silent filter cannot hide behind "all caught".
    with open(args.mutation_set, "rb") as _fh:
        print(f"SET-SHA256 {sha(_fh.read())[:32]}  {os.path.basename(args.mutation_set)}")
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
    with open(_TARGET, "rb") as fh:
        print(f"target restored: sha256 {sha(fh.read())[:16]} "
              f"(original {orig_sha[:16]})")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

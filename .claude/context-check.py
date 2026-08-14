#!/usr/bin/env python3
"""Context-window occupancy for the CURRENT session. Internal automation for
`.claude/readiness-runbook.md` step boundaries — NOT protocol surface, not
emitted, imports nothing from lib/.

WHY THIS EXISTS. The runbook hands one item per session and ends with an
operator `/clear`. The failure it prevents is running out of context in the
middle of step 5, where there is no clean handoff. So: measure at step
boundaries and flag EARLY, while a checkpoint can still be written.

WHERE THE NUMERATOR COMES FROM, and it is exact rather than estimated.
Claude Code writes a `usage` block per assistant message into the session
transcript. Occupancy at that turn is

    input_tokens + cache_creation_input_tokens + cache_read_input_tokens

i.e. everything the model was actually charged to read. The last such block is
the current occupancy. Transcript BYTES are not a proxy for this and must not
be used: tool output that was pruned still sits in the file.

WHERE THE DENOMINATOR COMES FROM, and why it is deliberately pessimistic.
The authoritative value is handed to the STATUSLINE by Claude Code as
`context_window.context_window_size` — it is not written into the transcript,
so this script cannot read it. Derived empirically instead (2026-08-14): the
highest occupancy ever observed across every transcript on this machine is
890,012 tokens **with zero compaction events**, which rules out the 200k/400k/
500k constants in the CLI binary and leaves 900k or 1M. We take 900k, the
SMALLER survivor, so the flag fires early under either. A late flag is the
failure mode that costs a session; an early one costs nothing.

If Claude Code ever reports the true size (or the model changes), override:
    CONTEXT_WINDOW=1000000 python3 .claude/context-check.py

EXIT CODES:  0 = healthy   1 = at/over threshold (runbook E9)   2 = unusable
"""
import glob
import json
import os
import sys

WINDOW = int(os.environ.get("CONTEXT_WINDOW", "900000"))
THRESHOLD = float(os.environ.get("CONTEXT_THRESHOLD", "0.80"))
PROJECT_SLUG = os.environ.get(
    "CLAUDE_PROJECT_SLUG",
    "-home-dengc-Documents-Projects-Project-Bootstrap-Protocol")


def transcript_dir():
    root = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return os.path.join(root, "projects", PROJECT_SLUG)


def newest_transcript():
    """Prefer the EXACT session. `CLAUDE_CODE_SESSION_ID` is exported into the
    tool environment, so the right transcript can be named rather than guessed
    — which matters when two sessions are open on this repo and the mtime
    heuristic would silently measure the other one's context."""
    d = transcript_dir()
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if sid:
        exact = os.path.join(d, sid + ".jsonl")
        if os.path.exists(exact):
            return exact
    files = glob.glob(os.path.join(d, "*.jsonl"))
    return max(files, key=os.path.getmtime) if files else None


def occupancy(path):
    """Last usage block wins. Returns (tokens, messages_seen)."""
    last, seen = None, 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"usage"' not in line:
                continue
            try:
                msg = json.loads(line).get("message") or {}
            except ValueError:
                continue
            use = msg.get("usage")
            if use:
                last, seen = use, seen + 1
    if not last:
        return None, seen
    return (last.get("input_tokens", 0)
            + last.get("cache_creation_input_tokens", 0)
            + last.get("cache_read_input_tokens", 0)), seen


def main():
    path = newest_transcript()
    if not path:
        print(f"context: UNUSABLE — no transcript under {transcript_dir()}")
        return 2
    tokens, seen = occupancy(path)
    if tokens is None:
        print(f"context: UNUSABLE — no usage block in {os.path.basename(path)}")
        return 2

    pct = tokens / WINDOW
    bar_n = int(pct * 20)
    bar = "#" * min(bar_n, 20) + "." * max(0, 20 - bar_n)
    state = ("OVER THRESHOLD" if pct >= THRESHOLD
             else "warn" if pct >= 0.70 else "healthy")
    print(f"context: [{bar}] {pct*100:5.1f}%  "
          f"{tokens:,} / {WINDOW:,} tokens  ({state})")
    print(f"         session {os.path.basename(path)[:8]}, "
          f"{seen} assistant turns, window assumed CONSERVATIVELY")

    if pct >= THRESHOLD:
        print()
        print("  E9 — CHECKPOINT NOW, DO NOT START ANOTHER STEP.")
        print("  1. finish or abandon the current step cleanly")
        print("  2. write the checkpoint + STOP file if mid-item")
        print("  3. flag the operator, then hand off with:")
        print("       /clear")
        print("       Load .claude/checkpoints/<file> and continue <item>.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

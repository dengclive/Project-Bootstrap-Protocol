#!/usr/bin/env python3
"""Citation tripwire — a `<doc>.md:NNN` citation must still point at its target.

WHY THIS EXISTS. Line citations into a LIVING document rot silently, and this
repo cites the PRD by line from prose, from tests, and from one EMITTED hook
body. Traced for a single target (`exit 2 blocks, but exit 1 is …`):

    v2.6.0 :654   v2.6.1 :670   v2.7.0 :713   v2.7.4 :739   :759 at this
    file's creation (2026-08-08)   :799 at 2.8.0 — a bare number, so the
    section-4 scan cannot police this trace; it is narrative, not a pin

Every one of those citations was CORRECT when written. They are **unversioned,
not wrong** — which is why no review caught them: each was verified once, and
the next edit to the target document invalidated it. The v2.7.4 release moved
the PRD by +26 lines; the commit that added this file moved it a further +20 and
invalidated the numbers fixed earlier in that same commit. Hand-fixing is
worthless without a tripwire; this is the tripwire.

THE PREDICATE: DERIVE, DO NOT ASSERT. The obvious design — store (line, expected
substring) and check the line still contains the substring — produces FALSE
PASSES, the dangerous direction, whenever the substring is not unique. It is
routinely not: `Iteration-summary enforcement` occurs twice in the PRD and
`goal-condition-suspect` thirteen times, so a rotted citation that happens to
land on another occurrence reads as healthy.

So instead each row stores an ANCHOR, never a line, and the test:
  1. asserts the anchor occurs EXACTLY ONCE in the cited document  <- closes the
     false-pass hole, and fails loudly if a doc edit duplicates an anchor;
  2. DERIVES the line from it;
  3. asserts the integer written in the citing file equals the derived line.
The maintained number lives in exactly one place — the citing file — and this
suite tells you what it should be.

SCOPE, stated rather than implied.
  IN:  explicit `Bootstrap-Protocol*.md:NNN` / `:NNN-MMM` citations in LIVE
       files, including the one that is EMITTED (lib/templates.py), where the
       filename and the `:NNN` are on DIFFERENT LINES.
  OUT: (a) HISTORICAL records — `docs/changelog.md` and closed backlog rows
       date-stamp their citations, and renumbering them to today's lines would
       corrupt the record by asserting a line that did not exist on that date;
       (b) bare `:NNN` continuations that name no file (the assessment's
       `- :341 —` list form), which cannot be resolved without prose context.
  Both exclusions are enforced by name below, not left to a regex accident.

Run: python3 tests/test_doc_citations.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

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
            print(detail)


# --------------------------------------------------------------------------- #
# The citation table — ANCHORS, never line numbers
# --------------------------------------------------------------------------- #
PRD = "Bootstrap-Protocol-v2-8-0.md"
COMPANION = "Bootstrap-Protocol-Companion-v2-8-0.md"
# Frozen: last touched long before the 2.7.x line. Cannot rot, but a wrong
# citation into it would be wrong permanently, so it is cheap to pin.
FROZEN_V200 = "Bootstrap-Protocol-v2-0-0.md"
# CITED as well as historical-as-a-CITER: `.claude/dynamic-workflow-policy.md`
# quotes it by line, and this branch's own 66-line prepend rotted that citation.
CHANGELOG = "docs/changelog.md"

# (citing file, cited doc, anchor). The anchor must be unique in the cited doc;
# section 1 enforces that. `Iteration-summary enforcement` alone is NOT unique
# (:740 and :1664) — hence the longer form.
CITATIONS = [
    (".claude/dynamic-workflow-policy.md", PRD,
     "**Not protocol surface, deliberately excluded:**",
     "is not part of any conformance surface."),
    (".claude/dynamic-workflow-policy.md", PRD,
     "**Concurrency rule across autonomous modes.**"),
    ("docs/dynamic-workflow-assessment.md", PRD,
     "**Not protocol surface, deliberately excluded:**",
     "is not part of any conformance surface."),
    ("docs/dynamic-workflow-assessment.md", PRD,
     "**Concurrency rule across autonomous modes.**"),
    ("tests/test_wrapper_behavior.py", PRD,
     "exit 2 blocks, but exit 1 is",
     "**Fails closed when the parser does not WORK"),
    ("docs/deferred-backlog.md", PRD,
     "**Iteration-summary enforcement** (only if"),
    # EMITTED. This one ships inside .claude/hooks/iteration-summary-enforcement.sh
    # (fixture B / full_autonomous), so correcting it moves a golden digest. It is
    # also the citation a naive scanner misses, because the filename ends one line
    # and `:NNN` begins the next.
    ("lib/templates.py", PRD,
     "exit 2 blocks, but exit 1 is",
     "**Fails closed when the parser does not WORK"),
    # The Companion is the other half of the living pair — it rots the same way.
    # Both of these were found by section 3's completeness scan, not by hand.
    (".claude/dynamic-workflow-policy.md", COMPANION,
     "| **Goal-supervised judge** (only if"),
    ("docs/dynamic-workflow-assessment.md", COMPANION,
     "**Known limitation worth flagging:**"),
    # Citations into a FROZEN document cannot rot — but a wrong one is wrong
    # forever, and verifying it costs nothing. Both tests cite the same line.
    ("tests/test_goal_evaluator_keys.py", FROZEN_V200,
     "**`.claude/goal-config.md`** — operator-tunable settings"),
    ("tests/test_greenfield_golden.py", FROZEN_V200,
     "**`.claude/goal-config.md`** — operator-tunable settings"),
    (".claude/dynamic-workflow-policy.md", CHANGELOG,
     "**A judge that only scores designs inherits their shared blind"),
]

# Normalise: rows may be 3-tuples (single line) or 4-tuples (a range).
CITATIONS = [(r + (None,))[:4] for r in CITATIONS]

# Files whose citations are deliberately NOT maintained (see SCOPE above).
HISTORICAL = {
    "docs/changelog.md",
    # Dated execution-findings records — the date is in the filename. Their
    # citations were correct on that date; renumbering them would corrupt the
    # record by asserting lines that did not exist when the findings were made.
    "docs/lens-a-execution-findings-2026-07-28.md",
    "docs/lens-b-execution-findings-2026-07-28.md",
}
# Rows inside otherwise-live files that are dated/closed records.
HISTORICAL_LINE_MARKERS = {
    # Keyed on (citing file, CITED DOC, line). Keying on (file, line) alone
    # would suppress that same number cited into a different document.
    ("docs/deferred-backlog.md", "Bootstrap-Protocol-v2-8-0.md", 283),
}


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# 0. Deny capability FIRST — prove the predicate fires before trusting a pass
# --------------------------------------------------------------------------- #
print("\n=== Section 0: the predicate catches a rotted citation ===")


def derive_line(doc_text, anchor):
    """Return (line_number, occurrences). 1-indexed, as citations are."""
    lines = doc_text.splitlines()
    hits = [i + 1 for i, ln in enumerate(lines) if anchor in ln]
    return (hits[0] if hits else None), len(hits)


_FAKE = "alpha\nbravo\nTARGET LINE\ndelta\n"
_l, _n = derive_line(_FAKE, "TARGET LINE")
check("derive_line finds a unique anchor at the right line", _l == 3 and _n == 1,
      f"    got line={_l} occurrences={_n}")

_l2, _n2 = derive_line("TARGET LINE\nx\nTARGET LINE\n", "TARGET LINE")
check("derive_line reports a DUPLICATED anchor (the false-pass hole)", _n2 == 2,
      f"    occurrences={_n2}; a duplicated anchor must be visible, not silently "
      f"resolved to the first hit")

_l3, _n3 = derive_line(_FAKE, "NOT PRESENT")
check("derive_line reports a MISSING anchor", _l3 is None and _n3 == 0)

# A rotted citation: the citing text says :99 while the anchor derives to :3.
check("a stale line number is detected", 99 != _l,
      "    predicate would not have caught a stale citation")


# --------------------------------------------------------------------------- #
# 1. Every anchor is unique in its cited document
# --------------------------------------------------------------------------- #
print("\n=== Section 1: anchors are unique (no false passes) ===")

for citing, doc, anchor, end in CITATIONS:
    _, n = derive_line(read(doc), anchor)
    check(f"anchor unique in {doc}: {anchor[:46]!r}", n == 1,
          f"    occurs {n} times — a non-unique anchor can mask a rotted "
          f"citation by landing on another occurrence. Lengthen the anchor.")


# --------------------------------------------------------------------------- #
# 2 + 3. SET EQUALITY per (citing file, cited doc) — every citation, not one
# --------------------------------------------------------------------------- #
# The first version of this section asked `derived_line in numbers_found`. That
# is MEMBERSHIP, and membership is satisfied by any ONE correct citation: a
# second, rotted citation to the same document from the same file passed
# unnoticed. The review of this file proved it with three mutations, and two
# real instances were live at the time — `.claude/dynamic-workflow-policy.md`
# cited PRD :133-136 and :339 in its provenance table while the very same file's
# prose had already been corrected to :171-174 and :385.
#
# So: collect EVERY number this file cites into that doc (both ends of a range),
# collect EVERY line the table derives for that pair, and require the two SETS
# to be equal. A stale number is then an unmatched element, not a near-miss.
print("\n=== Sections 2+3: every cited number resolves, and nothing is uncited ===")

CITE = r"`?\s*(?:\n\s*#?\s*)?`?:(\d+)(?:-(\d+))?"


def cited_numbers(citing_text, doc, citing_rel):
    """Every line number `citing_text` cites into `doc`, range ends included.

    Numbers listed in HISTORICAL_LINE_MARKERS are dropped: they are dated
    records whose citation was correct on its date, and renumbering them to
    today's lines would corrupt the record.
    """
    out = set()
    for m in re.finditer(re.escape(doc) + CITE, citing_text):
        for g in (m.group(1), m.group(2)):
            if g and (citing_rel, doc, int(g)) not in HISTORICAL_LINE_MARKERS:
                out.add(int(g))
    return out


pairs = {}
for citing, doc, anchor, end in CITATIONS:
    pairs.setdefault((citing, doc), []).append((anchor, end))

for (citing, doc), rows in sorted(pairs.items()):
    doc_text = read(doc)
    derived = set()
    ok = True
    for anchor, end in rows:
        line, n = derive_line(doc_text, anchor)
        if n != 1:
            ok = False
            continue
        derived.add(line)
        if end is not None:
            eline, en = derive_line(doc_text, end)
            check(f"{citing}: range-end anchor unique in {doc}", en == 1,
                  f"    end anchor {end[:40]!r} occurs {en} times")
            if en == 1:
                derived.add(eline)
    if not ok:
        continue
    found = cited_numbers(read(citing), doc, citing)
    check(f"{citing} -> {doc}: cited numbers == derived lines",
          found == derived,
          f"    cites   {sorted(found)}\n    derives {sorted(derived)}\n"
          f"    stale (cited, not derived): {sorted(found - derived)}\n"
          f"    missing (derived, not cited): {sorted(derived - found)}")


# --------------------------------------------------------------------------- #
# 4. Completeness — no live citation escapes the table
# --------------------------------------------------------------------------- #
print("\n=== Section 4: the table covers every live citation ===")

SCAN = re.compile(
    r"((?:Bootstrap-Protocol(?:-Companion)?-v\d+-\d+-\d+|docs/changelog)\.md)" + CITE)

try:
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.split()
except (subprocess.CalledProcessError, FileNotFoundError):
    tracked = []
check("git ls-files returned a file list", len(tracked) > 20,
      f"    got {len(tracked)} files; section 4 cannot run vacuously")

SELF = os.path.relpath(os.path.abspath(__file__), ROOT)
covered = {(c, d) for c, d, _, _ in CITATIONS}
uncovered = []
for rel in tracked:
    if rel == SELF or rel in HISTORICAL:
        continue
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            text = fh.read()
    except (UnicodeDecodeError, OSError, IsADirectoryError):
        continue
    for m in SCAN.finditer(text):
        doc, num = m.group(1), int(m.group(2))
        if (rel, doc, num) in HISTORICAL_LINE_MARKERS:
            continue
        if (rel, doc) not in covered:
            uncovered.append((rel, doc, num))

check("every live citation has a table row", uncovered == [],
      "\n".join(f"    {r} cites {d}:{n} with no CITATIONS row" for r, d, n in uncovered)
      + "\n    A citation with no row is a citation nothing checks.")

total_found = 0
for rel in tracked:
    if rel == SELF:
        continue
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            total_found += len(SCAN.findall(fh.read()))
    except (UnicodeDecodeError, OSError, IsADirectoryError):
        continue
check("the scan is not vacuous (it finds citations)", total_found >= len(CITATIONS),
      f"    scan found {total_found}, table has {len(CITATIONS)}")

_tpl = read("lib/templates.py")
check("the scan matches the line-split EMITTED citation",
      any(m.group(1) == PRD for m in SCAN.finditer(_tpl)),
      "    lib/templates.py's citation spans a newline and a `#` continuation")


print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

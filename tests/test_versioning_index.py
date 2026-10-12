#!/usr/bin/env python3
"""[WP3 versioning-index] Phase 7.5 and the INDEX.md schema.

Pins, behaviourally where a behaviour exists:
  * the four new artifacts (.claude/specs/README.md, .claude/steering/
    spec-versioning.md, .claude/learnings/README.md, .claude/sessions/
    README.md) in greenfield and retrofit, non-critical tier;
  * the INDEX.md roster schema: PRD columns, the pre-WP3 four first (an
    older roster upgrades by appending), the status legend, one source;
  * INDEX.md adds no file-name reference to the spec commit gate's corpus
    (run through the EMITTED gate);
  * the protocol text the PRD requires in each artifact, and the claims the
    sessions README makes about the emitted hooks (gitignored, purged,
    not implemented) against the emitted files themselves;
  * the installer's warning for a skipped roster that lacks columns.
  * [WP3 critic 3b-3f] the checkpoint's commit of its roster edit (the
    emitted commands, run in a real repository); a bump reopening a
    `complete` spec and step 9's `current` re-validation; the retrofit
    R8.D skip (no spec-versioning.md, and no emitted pointer to it); the
    sessions README's X-33 rule 3; the warning's inline recipe when the
    README on disk is the adopter's own; and one row per normative clause
    the rebuild verifier's mutants X1-X3, X5, X7, X10, X13, X17 and X18
    deleted or inverted with every row still green. Clause rows compare
    whitespace-normalized text, so a reflow keeps them green and a
    changed word does not.

Run: python3 tests/test_versioning_index.py
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import installer  # noqa: E402
import templates  # noqa: E402
from defaults import resolve_config  # noqa: E402
from minyaml import load_yaml  # noqa: E402

BIN_INSTALL = os.path.join(ROOT, "bin", "bootstrap-install")
# [WP3 critic 1j] With TMPDIR inside a git work tree, the CLI installs below
# would find that repository and write its git hooks there. Inherited by
# every subprocess this suite starts.
os.environ["GIT_CEILING_DIRECTORIES"] = tempfile.gettempdir()
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


def plan_for(yaml_text):
    cfg, errs = resolve_config(load_yaml(yaml_text))
    assert not errs, errs
    return cfg, installer.build_plan(cfg)


def body(plan, path):
    for a in plan:
        if a["path"] == path:
            return a["body"]
    return None


def _norm(text):
    """Whitespace-normalized, for clause rows that must survive a reflow."""
    return re.sub(r"\s+", " ", text or "")


def has(text, clause):
    return _norm(clause) in _norm(text)


# Read through getattr so this file FAILS (rather than crashes) on a tree
# without the change, which is how its fail-before rows were counted.
COLS = tuple(getattr(templates, "INDEX_COLUMNS", ()))
REFRESH = getattr(templates, "INDEX_REFRESH_RULE", "\0missing")
CHANGELOG = getattr(templates, "CHANGELOG_HEADER", "\0missing")
MD_ROW = getattr(templates, "_md_row",
                 lambda cells: "| " + " | ".join(cells) + " |")
WARN = getattr(installer, "_index_schema_warning",
               lambda *a, **k: "\0missing")


with open(os.path.join(ROOT, "bootstrap.config.yaml")) as _fh:
    CFG_DEFAULT = _fh.read()
CFG_FULL = """project:
  name: vi
  archetype: ai-agent
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: true
principles:
  tdd_policy: required
commands:
  test: "pytest -q"
  lint: ""
  format: ""
"""
CFG_RETRO = """mode: "retrofit"
project:
  name: r-svc
  archetype: service
secrets:
  enabled: true
deps:
  enabled: true
  approved: []
commands:
  test: "true"
  lint: "true"
  format: "true"
retrofit:
  spec_strategy: "forward-only"
  legacy_allowlist:
    - "src/**"
  retrofit_active: true
  r08_committed: true
"""

NEW = (".claude/specs/README.md", ".claude/steering/spec-versioning.md",
       ".claude/learnings/README.md", ".claude/sessions/README.md")
IDX = ".claude/specs/INDEX.md"

_g_cfg, _g = plan_for(CFG_DEFAULT)
_f_cfg, _f = plan_for(CFG_FULL)
_r_cfg, _r = plan_for(CFG_RETRO)

# --------------------------------------------------------------------------- #
print("\n== 1. the new artifacts: emitted in both modes, non-critical ==")
for label, plan in (("greenfield default", _g), ("greenfield full", _f),
                    ("retrofit", _r)):
    acts = {a["path"]: a for a in plan}
    for p in NEW:
        a = acts.get(p)
        check(f"{label}: {p} emitted as kind file, mode 0644",
              a is not None and a["kind"] == "file" and a["mode"] == 0o644)
        check(f"{label}: {p} is non-critical tier (no seam 7.2 change)",
              a is not None
              and installer._hook_tier(a) == installer.TIER_NON,
              a and installer._hook_tier(a))
for p in NEW:
    check(f"retrofit passes {p} through unchanged",
          body(_r, p) == body(_g, p) and body(_g, p) is not None)
check("the new artifacts do not depend on the config (identical bodies "
      "in the default and the full-autonomous plan)",
      all(body(_g, p) is not None and body(_g, p) == body(_f, p)
          for p in NEW))
check("no new artifact embeds the progress.md template (GR2-01 uniqueness)",
      all("# Progress — <slug>" not in (body(_g, p) or "") for p in NEW))

# --------------------------------------------------------------------------- #
print("\n== 2. INDEX.md: the roster schema ==")
_idx = body(_g, IDX) or ""
_rows = [ln for ln in _idx.splitlines() if ln.startswith("|")]
_cells = [[c.strip() for c in ln.strip().strip("|").split("|")]
          for ln in _rows]
check("INDEX.md header is INDEX_COLUMNS, in order",
      _cells and tuple(_cells[0]) == COLS, _cells[:1])
_PRD = ("slug", "status", "active version", "in-flight against superseded?",
        "in-flight tasks", "blocked tasks", "last checkpoint",
        "loop-eligible / total", "depends on")
for col in _PRD:
    check(f"INDEX.md has the PRD column {col!r}",
          col in COLS)
check("the pre-WP3 four columns come first, in their old order, so an "
      "older roster upgrades by appending",
      COLS[:4] == ("slug", "status", "active version",
                                      "in-flight against superseded?"))
check("one separator row and one placeholder row, each as wide as the "
      "header",
      len(_cells) == 3
      and all(len(r) == len(COLS) for r in _cells)
      and set("".join(_cells[1])) <= {"-"}
      and _cells[2][:2] == ["_placeholder_", "planned"]
      and set(_cells[2][2:]) == {"-"}, _cells)
_legend = [ln for ln in _idx.splitlines() if re.match(r"- `[a-z-]+`: ", ln)]
check("INDEX.md legend names the five PRD statuses, in order",
      [re.match(r"- `([a-z-]+)`", ln).group(1) for ln in _legend]
      == ["planned", "draft", "in-flight", "complete", "superseded"], _legend)
check("the planned legend entry carries the PRD 7.6 step 6 meaning",
      any("spec roster row" in ln and "not yet authored" in ln
          and "awaits `/spec-new <slug>`" in ln for ln in _legend))
# [critic 3c] complete means validated at the ACTIVE version, so a minor
# or major bump reopens the spec (the conformance verifier: `complete`
# survived a bump that invalidated it).
check("the in-flight legend entry covers a spec a minor or major bump "
      "reopened",
      any(has(ln, "or a minor or major bump reopened a `complete` spec, and "
                  "the spec is not yet validated as a whole at the active "
                  "version.") for ln in _legend), _legend)
_readme = body(_g, ".claude/specs/README.md") or ""
check("INDEX.md and the specs README carry the same legend lines",
      _legend and all(ln in _readme.splitlines() for ln in _legend))
check("GR2-01 still: INDEX.md carries the roster and points at the "
      "progress template",
      "| slug | status |" in _idx and "progress-template.md" in _idx)
check("INDEX.md points at the schema README and the versioning doc",
      ".claude/specs/README.md" in _idx
      and ".claude/steering/spec-versioning.md" in _idx)
check("INDEX.md keeps the ownership sentence",
      "The installer will not overwrite your rows." in _idx)

# The gate's corpus: INDEX.md is read whole and a staged file counts as
# referenced when its bare basename appears with these boundaries
# (spec-gate-commit, lib/templates.py; the SDK twin mirrors them). A
# basename WITH an extension is the hazardous kind (README.md,
# requirements.md ...). Only the two pre-WP3 tokens may appear.
_ext = set(re.findall(r"(?:^|[^A-Za-z0-9_./-])([A-Za-z0-9_-]+\.[A-Za-z0-9_.-]*"
                      r"[A-Za-z0-9])(?=[^A-Za-z0-9_-]|$)", _idx, re.M))
check("INDEX.md names no file by bare basename except the pre-WP3 "
      "`progress.md` (and the `7.6` phase number)",
      _ext <= {"progress.md", "7.6"}, sorted(_ext))

# --------------------------------------------------------------------------- #
print("\n== 3. the specs README: the normative half of the schema ==")
for col in COLS:
    check(f"README documents column {col!r} with what it holds and who "
          f"writes it",
          re.search(r"^\| `" + re.escape(col) + r"` \| [^|]+ \| [^|]+ \|$",
                    _readme, re.M) is not None)
check("README states the task-column refresh rule from the task files",
      REFRESH in _readme
      and "status` is `in-progress` or `done`" in _readme)
# [critic 3f] One row per refresh-rule clause the live models executed to
# compute the row (rebuild verifier X1-X3 deleted or inverted each with
# every row green).
check("refresh rule: a patch difference does not count as superseded (X1)",
      has(_readme, "written with that version: `<slug>-T02 (1.0.0)`. A "
                   "patch difference does not count."))
check("refresh rule: an in-flight task a major version behind is blocked "
      "(X2)",
      has(_readme, "plus every in-flight id whose `spec_version` is a major "
                   "version behind `active version` (a major bump halts "
                   "it)."))
check("refresh rule: a blocker clears at `done`, not only at `validated` "
      "(X3)",
      has(_readme, "whose `blocked_by` names a task that is not yet `done` "
                   "or `validated`"))
check("refresh rule: a refresh never moves a `complete` row; only a minor "
      "or major bump reopens it (critic 3c)",
      has(_readme, "set the row's `status` to `in-flight`, unless the row "
                   "is `complete`: only a whole-spec `/spec-validate` pass "
                   "sets `complete`, and only a minor or major version bump "
                   "sets a `complete` row back to `in-flight`."))
check("README: each roster edit is committed (X10)",
      has(_readme, "Commit each roster edit, so the main checkout stays "
                   "clean."))
check("README: the implementer never edits the roster or a task's status "
      "(status writers, critic files contract item 7)",
      has(_readme, "An implementer never edits the roster or a task's "
                   "`status`; the main session refreshes the row after the "
                   "merge-back.")
      and "changes only its own task file" not in _readme)
check("README: the roster is never edited inside an implementer worktree",
      "never inside an implementer\nworktree (a path under "
      "`.claude/worktrees/`)" in _readme)
check("README: the task files are the source of truth",
      "The task files are the source of\ntruth" in _readme)
_mig = _readme[_readme.find("## Migrating an older INDEX.md"):] \
    if "## Migrating an older INDEX.md" in _readme else ""
check("README migration names the four old columns and the six new ones",
      len(COLS) == 10 and all(f"`{c}`" in _mig for c in COLS))
check("README reserves `suggested first` in notes (Phase 9 step 1 reads it)",
      "`suggested first`" in _readme and "exactly one row" in _readme)
check("README banner says what the digest guard does (no 'replaced on "
      "re-apply' claim)",
      "once you edit it, re-installs\n> leave it alone" in _readme
      and "replaced" not in _readme.split("\n## ")[0])

# --------------------------------------------------------------------------- #
print("\n== 4. spec-versioning.md: the Phase 7.5 protocol ==")
_sv = body(_g, ".claude/steering/spec-versioning.md") or ""
check("version: frontmatter in semver, starting at 1.0.0",
      "`version:` line in its frontmatter" in _sv and "`1.0.0`" in _sv)
for bump, effect in (("patch", "| continue |"),
                     ("minor", "| continue, flagged for re-validation |"),
                     ("major", "| halt until a human reviews them |")):
    check(f"bump rule {bump}: in-flight tasks {effect.strip('| ')}",
          re.search(r"^\| " + bump + r" \|.*" + re.escape(effect) + "$",
                    _sv, re.M) is not None)
check("changelog columns are CHANGELOG_HEADER (version, date, change "
      "summary, impact on in-flight tasks)",
      CHANGELOG == "| version | date | change summary "
      "| impact on in-flight tasks |" and CHANGELOG in _sv)
check("changelog dates come from the clock", "`date -u +%Y-%m-%d`" in _sv)
check("design.md is internal and unversioned; only requirements.md is "
      "the contract",
      "internal and unversioned" in _sv and "is the contract" in _sv)
check("the mid-flight workflow: classify, explicit acknowledgment on a "
      "major, changelog row, re-validate on minor or major",
      "Classify the bump" in _sv and "explicit\n   acknowledgment" in _sv
      and "Append a row to `changelog.md`" in _sv
      and has(_sv, "For a minor or major bump (for a major one, after the "
                   "operator's review), re-validate the completed tasks at "
                   "the new version"))
# [critic 3f] Clause rows the rebuild verifier's X5, X7 and X18 showed
# missing.
check("an ambiguous bump takes the higher level (X5)",
      has(_sv, "When a change could be either of two levels, use the "
               "higher one."))
check("a major bump without the operator's acknowledgment stops (X7)",
      has(_sv, "get the operator's explicit acknowledgment before you bump. "
               "Without it, stop."))
check("AC IDs are permanent; a removed criterion is marked, not deleted "
      "(X18)",
      has(_sv, "Acceptance-criterion IDs (`AC-<n>`) are permanent. A removed "
               "criterion keeps its line, marked `(removed in <version>)`"))
# [critic 3c] A bump of a complete spec reopens it, and step 9 re-points
# spec_version through spec-validate's `current` arm. Before, step 9 ran
# `/spec-validate <slug> <task id>`, which checks at the task's own version
# (minor gap) or stops (major gap): a dead end (rebuild verifier).
check("step 7: a minor or major bump of a complete spec sets it back to "
      "in-flight",
      has(_sv, "After a minor or major bump of a `complete` spec, set its "
               "`status` back to `in-flight`"))
check("step 9: re-validation runs the `current` arm, which re-points "
      "spec_version, then the whole spec",
      has(_sv, "`/spec-validate <slug> <task-id> current` for each task "
               "that is `done` or `validated`. Each pass sets that task's "
               "`spec_version` to the new version. Then `/spec-validate "
               "<slug>` checks the whole spec, and its pass sets the row to "
               "`complete`.")
      and "`/spec-validate <slug> <task id>` for" not in _sv)
check("spec_version's exceptions name the `current` re-validation",
      has(_sv, "or when `/spec-validate <slug> <task-id> current` passes "
               "the task at the current version (step 9 below)."))
_svs = body(_g, ".claude/skills/spec-validate/SKILL.md") or ""
check("step 9's command is one the emitted spec-validate takes: its "
      "argument hint has [current], and its `current` arm re-points "
      "spec_version",
      'argument-hint: "<slug> [task-id] [current]"' in _svs
      and has(_svs, "With `current`, also set its `spec_version` to that "
                    "version."), _svs[:300])
check("one commit per version, because spec-validate reads old versions "
      "from git", "one\n   commit per version" in _sv)
check("the task side: spec_version, and spec-validate records the version",
      "`spec_version:`" in _sv
      and "records the version it validated against" in _sv)
check("INDEX tracking: active version and in-flight against superseded",
      "`active version`" in _sv and "`in-flight against superseded?`" in _sv)

# --------------------------------------------------------------------------- #
print("\n== 5. learnings README: convention, routing, LIT-03, LIT-01 ==")
_lr = body(_g, ".claude/learnings/README.md") or ""
check("convention: one file per learning, titled by topic, dated",
      "One file per learning, titled by topic, dated." in _lr)
for art in (".claude/learnings/", ".claude/specs/<slug>/decisions.md",
            ".claude/specs/<slug>/progress.md", ".claude/sessions/"):
    check(f"routing table row for {art}", f"| `{art}` |" in _lr)
check("LIT-03: verbatim artifacts for strong consumers, distilled for weak",
      "[LIT-03]" in _lr and "Verbatim artifacts" in _lr
      and "Distilled artifacts" in _lr and "consumer strength" in _lr)
check("LIT-01: the preservation invariant, closing sentence verbatim",
      "[LIT-01]" in _lr and "Condensation may drop\nprose; it may never "
      "drop a fact, a flag, or a citation." in _lr)

# --------------------------------------------------------------------------- #
print("\n== 6. sessions README: checkpoint schema, X-33, state files ==")
_sr = body(_g, ".claude/sessions/README.md") or ""
check("X-33: every producer reads the stamp from the clock (exact command)",
      "by every producer, without\nexception" in _sr
      and "`date -u +%Y-%m-%dT%H%MZ`" in _sr)
check("X-33: resume selects by modification time (the skill's pipeline)",
      "ls -t .claude/sessions/*-checkpoint.md" in _sr)
# [critic 3e] X-33 rule 3, which backlog X-30c asks the README to carry:
# only a checkpoint picked by modification time follows a supersession
# banner; a named one is loaded as it is (rule 1).
_res = body(_g, ".claude/skills/resume/SKILL.md") or ""
check("X-33 rule 3: a checkpoint picked by modification time follows its "
      "supersession banner forward; a named one does not",
      has(_sr, "A checkpoint you name is loaded as it is. One picked by "
               "modification time is cross-checked: if it carries a "
               "supersession banner, `/resume` follows the banner forward to "
               "the checkpoint that supersedes it.")
      and "supersession banner" in _res and "follow it forward" in _res)
# [critic 3f] X13: the banner that says what a re-install does to the file.
_BANNER = getattr(templates, "_GENERATED_BANNER", "\0missing")
for _p in (".claude/specs/README.md", ".claude/learnings/README.md",
           ".claude/sessions/README.md"):
    check(f"{_p} carries the generated-file banner (X13)",
          _BANNER in (body(_g, _p) or ""))
_ck = body(_g, ".claude/skills/checkpoint/SKILL.md")
_m = re.search(r"Synopsis sections: (.*?)\.\n", _ck, re.S)
_skill_secs = [s.strip().lower() for s in
               re.sub(r"\s+", " ", _m.group(1)).split(",")] if _m else []
_readme_secs = [re.sub(r"\s+", " ", s).strip().rstrip(".").lower() for s in
                re.findall(r"^\d\. (.*)$", _sr.split("## State files")[0],
                           re.M)]
check("the README's checkpoint sections are the checkpoint skill's list",
      _skill_secs and _readme_secs == _skill_secs,
      f"skill={_skill_secs} readme={_readme_secs}")

_dot = sorted(set(re.findall(r"`(\.[a-z0-9-]+?-)<", _sr)))
for label, plan in (("greenfield", _f), ("retrofit", _r)):
    gi = body(plan, ".claude/.gitignore")
    pats = [ln.strip()[len("sessions/"):].rstrip("*")
            for ln in gi.splitlines() if ln.strip().startswith("sessions/.")]
    unc = [d for d in _dot if not any(d.startswith(p) for p in pats)]
    check(f"{label}: every dotfile the README lists is gitignored, as it "
          f"says ({len(_dot)} names)", _dot and not unc, unc)
_hooks = {a["path"]: a["body"] for a in _f if a["path"].endswith(".sh")}
check("the README's 7-day purge claim holds: drift detector",
      re.search(r"-name '\.drift-state-\*'.*?-mtime \+7",
                _hooks.get(".claude/hooks/drift-detector.sh", ""), re.S)
      is not None)
check("the README's 7-day purge claim holds: decision-required alarm",
      "-name '.decision-pending-*' -mtime +7" in
      _hooks.get(".claude/hooks/decision-required-alarm.sh", ""))
check("the README's 7-day purge claim holds: the lint notice",
      "-name '.lint-unset-*' -mtime +7" in
      _hooks.get(".claude/hooks/format-lint-gate.sh", ""))
check("the README's 'not implemented yet' claims hold: no emitted script "
      "reads or writes .quiet-*, and tier 3 is not enforced",
      all(".quiet-" not in b for b in _hooks.values())
      and "drift_tier3_enforced=false"
      in body(_f, ".claude/hooks/audio-alerts.config"))

# --------------------------------------------------------------------------- #
print("\n== 7. the edits to existing artifacts ==")
check("checkpoint flags the `last checkpoint` column, not from a worktree",
      has(_ck, "set the `last checkpoint` cell of each spec row this "
               "session worked on to the new file's name")
      and has(_ck, "Skip this flag and its commit inside an implementer "
                   "worktree (a path under `.claude/worktrees/`), where "
                   "parallel tasks would conflict on the row"))
# [critic 3b] An uncommitted roster edit made the D6 merge-back refuse the
# main checkout (conformance verifier: rc 3, then rc 0 once committed).
check("checkpoint commits the roster edit with the checkpoint and nothing "
      "else, and says why",
      has(_ck, "Commit that edit with the checkpoint and nothing else, so "
               "your in-flight changes stay uncommitted:")
      and has(_ck, "An uncommitted roster edit makes `.claude/merge-back.sh` "
                   "refuse the main checkout.")
      and has(_ck, "If a gate refuses the commit (the test gate does while "
                   "tests fail), tell the operator the two files are "
                   "uncommitted."))

# The emitted commands, run as written in a real repository where work is in
# flight: the commit takes exactly the checkpoint and the roster, leaves the
# staged work staged, and leaves no tracked roster change behind.
_cmds = [ln.strip() for ln in _ck.splitlines()
         if re.match(r"^    git (add|commit) ", ln)]
_ckf = ".claude/sessions/2026-10-05T1200Z-checkpoint.md"
_genv = {k: v for k, v in os.environ.items()
         if k != "CLAUDECODE" and not k.startswith("GIT_")}
_genv.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
             GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
             GIT_CONFIG_NOSYSTEM="1", HOME=tempfile.gettempdir(),
             GIT_CEILING_DIRECTORIES=tempfile.gettempdir(),
             # [WP3 fix1 TP-03] No developer git config (a global
             # commit.gpgsign failed this row): an empty global file.
             GIT_CONFIG_GLOBAL=os.devnull,
             XDG_CONFIG_HOME=os.path.join(tempfile.gettempdir(),
                                          "no-xdg-config"))
with tempfile.TemporaryDirectory() as _t:
    def _git(*a):
        return subprocess.run(["git", "-C", _t, *a], capture_output=True,
                              text=True, env=_genv)
    _git("init", "-q")
    os.makedirs(os.path.join(_t, ".claude", "specs"))
    os.makedirs(os.path.join(_t, ".claude", "sessions"))
    os.makedirs(os.path.join(_t, "src"))
    with open(os.path.join(_t, IDX), "w") as fh:
        fh.write(_idx)
    with open(os.path.join(_t, "src", "a.py"), "w") as fh:
        fh.write("a = 1\n")
    _git("add", "-A")
    _git("commit", "-qm", "base")
    with open(os.path.join(_t, "src", "a.py"), "w") as fh:
        fh.write("a = 2\n")                       # work in flight, staged
    _git("add", "src/a.py")
    with open(os.path.join(_t, _ckf), "w") as fh:
        fh.write("# checkpoint\n")
    with open(os.path.join(_t, IDX), "a") as fh:
        fh.write("| due | in-flight | 1.0.0 | - | - | due-T01 | - | "
                 "2026-10-05T1200Z-checkpoint.md | 0 / 1 | - |\n")
    _rcs = [subprocess.run(["bash", "-c", c.replace("<checkpoint>", _ckf)
                            .replace("<message>", "checkpoint")],
                           cwd=_t, capture_output=True, text=True,
                           env=_genv).returncode for c in _cmds]
    _head = _git("show", "--name-only", "--format=", "HEAD").stdout.split()
    _staged = _git("diff", "--cached", "--name-only").stdout.split()
    _dirty = _git("status", "--porcelain", "--untracked-files=no").stdout
    check("the checkpoint's emitted commit commands, run as written, commit "
          "exactly the checkpoint and the roster, and leave the work in "
          "flight staged",
          len(_cmds) == 2 and _rcs == [0, 0]
          and sorted(_head) == sorted([_ckf, IDX])
          and _staged == ["src/a.py"]
          and _dirty.splitlines() == ["M  src/a.py"],
          f"cmds={_cmds} rcs={_rcs} head={_head} staged={_staged} "
          f"dirty={_dirty!r}")
check("checkpoint keeps its X-33 routing key and clock rule",
      "description: Write a structured session synopsis to "
      ".claude/sessions/<timestamp>-checkpoint.md." in _ck
      and "date -u +%Y-%m-%dT%H%MZ" in _ck)
for label, plan in (("greenfield", _g), ("retrofit", _r)):
    cm = body(plan, "CLAUDE.md")
    check(f"{label} CLAUDE.md: the wrong-spec escalation names "
          f"spec-versioning.md (PRD Phase 8)",
          re.search(r"Implementation reveals the spec was wrong \(follow\n"
                    r"   `\.claude/steering/spec-versioning\.md`\)\.", cm)
          is not None)
_st = body(_g, ".claude/steering/structure.md")
for phrase in ("(any status, including `superseded`)", "`grammar-86-2`",
               "Slugs are immutable once a row reaches `status: in-flight`.",
               "`src/parameter-extractor.ts` → `parameter-extractor`"):
    check(f"structure.md carries the canonical slug text: {phrase[:40]}",
          phrase in _st)

# --------------------------------------------------------------------------- #
print("\n== 8. the emitted spec gate: INDEX.md adds no file reference ==")
_GATE_CFG = CFG_DEFAULT.replace("spec_gate_commit: false",
                                "spec_gate_commit: true")


def _install(d, cfg_text, *extra):
    with open(os.path.join(d, "bootstrap.config.yaml"), "w") as fh:
        fh.write(cfg_text)
    return subprocess.run([sys.executable, BIN_INSTALL, "-C", d, *extra],
                          capture_output=True, text=True)


_tmp = tempfile.mkdtemp()
try:
    d = os.path.join(_tmp, "gate")
    os.makedirs(d)
    subprocess.run(["git", "init", "-q", d], check=True)
    r = _install(d, _GATE_CFG)
    gate = os.path.join(d, ".claude", "hooks", "spec-gate-commit.sh")
    check("fixture install has the spec gate", r.returncode == 0
          and os.path.isfile(gate), r.stderr[-300:])
    env = dict(os.environ, CLAUDE_PROJECT_DIR=d)
    pay = json.dumps({"tool_name": "Bash",
                      "tool_input": {"command": "git commit -m x"}})
    for f in ("src/README.md", "src/requirements.md", "src/changelog.md",
              "src/decisions.md", "src/INDEX.md", "src/spec-versioning.md",
              "tests/test_app.py", "lib/checkpoint.py"):
        full = os.path.join(d, f)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write("x\n")
        subprocess.run(["git", "-C", d, "reset", "-q"], check=True)
        subprocess.run(["git", "-C", d, "add", "-f", "--", f], check=True)
        # [critic r3] the check of record, not the deferring fallback.
        g = subprocess.run(["bash", os.path.join(d, ".claude", "githooks",
                                                 "spec-check.sh"), "--staged"],
                           capture_output=True, text=True, env=env, cwd=d)
        check(f"the emitted INDEX.md does not clear staged {f} (rc 2)",
              g.returncode == 2, f"rc={g.returncode} {g.stderr[-200:]}")
        subprocess.run(["git", "-C", d, "reset", "-q"], check=True)
        os.remove(full)
finally:
    shutil.rmtree(_tmp)

# --------------------------------------------------------------------------- #
print("\n== 9. an older roster: the installer says what it did not get ==")
_OLD_HEADER = ("| slug | status | active version | "
               "in-flight against superseded? |")


_OUR_README = body(_g, ".claude/specs/README.md")
_OWN_README = "# Our specs\n\nWe keep our own notes here.\n"
_POINTER = "\"Migrating an older INDEX.md\" in .claude/specs/README.md"


def _warning_for(index_text, dry=False, readme=_OUR_README):
    """The warning for a skipped INDEX.md; `readme` is the README on disk
    (None: absent)."""
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        (root / ".claude" / "specs").mkdir(parents=True)
        (root / IDX).write_text(index_text)
        if readme is not None:
            (root / ".claude/specs/README.md").write_text(readme)
        summary = {"skipped_paths": [IDX]}
        return WARN(root, summary, dry=dry)


_w = _warning_for(_OLD_HEADER + "\n|---|---|---|---|\n| a | draft | 1.0.0 | no |\n")
check("a skipped pre-WP3 roster gets one warning naming the six missing "
      "columns and the migration recipe",
      _w is not None
      and all(f"'{c}'" in _w for c in COLS[4:])
      and all(f"'{c}'" not in _w for c in COLS[:4])
      and "\"Migrating an older INDEX.md\" in .claude/specs/README.md" in _w,
      _w)
check("its wording on --dry-run says 'would not update'",
      "would not update" in (_warning_for(_OLD_HEADER + "\n", dry=True) or ""))
check("a skipped roster with every column gets no warning",
      _warning_for(MD_ROW(COLS) + "\n") is None)
check("column names compare case-insensitively",
      _warning_for(MD_ROW(c.upper() for c in
                                     COLS) + "\n") is None)
check("a roster with no 'slug' table is told so",
      "no roster table" in (_warning_for("# Specs\n\nnone\n") or ""))
# [critic 3f] X17: only a table whose FIRST header cell is `slug` is the
# roster; a table that merely has a slug column somewhere is not.
check("a table whose first header cell is not 'slug' is not the roster "
      "(X17)",
      "no roster table" in (_warning_for(
          "| id | slug | status |\n|---|---|---|\n| 1 | a | draft |\n")
          or ""))

# [critic 3e] The README on disk is the adopter's own (pre-existing or
# edited, so skipped) and has no recipe: the conformance verifier's scenario
# h pointed at a recipe that was not there. The warning now carries it.
_OLDROSTER = _OLD_HEADER + "\n|---|---|---|---|\n| a | draft | 1.0.0 | no |\n"
_wi = _warning_for(_OLDROSTER, readme=_OWN_README) or ""
check("the adopter's own README: the warning gives the recipe inline, "
      "naming the missing columns in order, and points nowhere",
      _POINTER not in _wi
      and ".claude/specs/README.md is not the installer's, so it has no "
          "migration recipe." in _wi
      and "append them to the header row in the order named here, then "
          "one '---' cell per added column to the separator row and one "
          "'-' cell per added column to every data row." in _wi
      and "move yours aside and re-install" in _wi
      and _wi.find("'depends on'") < _wi.find("'notes'"), _wi)
check("no README on disk after a real run: the recipe inline too",
      _POINTER not in (_warning_for(_OLDROSTER, readme=None) or "x")
      and "is not the installer's" in (_warning_for(_OLDROSTER, readme=None)
                                       or ""))
check("--dry-run with no README yet: points at the README this run would "
      "create",
      _POINTER in (_warning_for(_OLDROSTER, dry=True, readme=None) or ""))
check("--dry-run with the adopter's own README: the recipe inline",
      _POINTER not in (_warning_for(_OLDROSTER, dry=True,
                                    readme=_OWN_README) or "x")
      and "would not update" in (_warning_for(_OLDROSTER, dry=True,
                                              readme=_OWN_README) or ""))
check("an edited README that kept the recipe: still the pointer",
      _POINTER in (_warning_for(_OLDROSTER,
                                readme="# Mine\n\n" + _OUR_README) or ""))
_wn = _warning_for("# Specs\n\nnone\n", readme=_OWN_README) or ""
check("no roster table and the adopter's own README: the warning gives the "
      "full current header row",
      "Start the roster table with this header row: " + MD_ROW(COLS) + "."
      in _wn and _POINTER not in _wn, _wn)
with tempfile.TemporaryDirectory() as t:
    check("no warning when INDEX.md was not skipped",
          WARN(Path(t), {"skipped_paths": []}) is None)

# End to end through the CLI: the stderr channel, rc 0, rows untouched.
_tmp = tempfile.mkdtemp()
try:
    d = os.path.join(_tmp, "up")
    os.makedirs(d)
    r1 = _install(d, CFG_DEFAULT)
    check("fresh install: no INDEX warning",
          r1.returncode == 0 and "INDEX.md keeps your rows" not in r1.stderr,
          r1.stderr[-300:])
    p = os.path.join(d, IDX)
    old = (_OLD_HEADER + "\n|---|---|---|---|\n"
           "| due-dates | draft | 1.0.0 | no |\n")
    with open(p, "w") as fh:
        fh.write(old)
    r2 = _install(d, CFG_DEFAULT)
    check("re-install over an edited pre-WP3 roster: rc 0, SKIP on stdout, "
          "one warning on stderr",
          r2.returncode == 0 and "SKIP   .claude/specs/INDEX.md" in r2.stdout
          and r2.stderr.count("warning: .claude/specs/INDEX.md keeps your "
                              "rows, so this run did not update it") == 1,
          r2.stderr[-400:])
    check("the roster bytes are untouched", open(p).read() == old)
    check("with the installer's README on disk, the warning points at its "
          "recipe", _POINTER in r2.stderr, r2.stderr[-400:])
    # Scenario h: the adopter's own README, edited, so it is skipped.
    with open(os.path.join(d, ".claude/specs/README.md"), "w") as fh:
        fh.write(_OWN_README)
    r3 = _install(d, CFG_DEFAULT)
    check("re-install with the adopter's own README too: rc 0, one warning, "
          "with the recipe inline",
          r3.returncode == 0
          and "SKIP   .claude/specs/README.md" in r3.stdout
          and r3.stderr.count("warning: .claude/specs/INDEX.md keeps your "
                              "rows") == 1
          and _POINTER not in r3.stderr
          and "append them to the header row" in r3.stderr,
          r3.stderr[-600:])
finally:
    shutil.rmtree(_tmp)

# --------------------------------------------------------------------------- #
print("\n== 10. the retrofit R8.D skip (critic 3d) ==")
# RETROFIT.md R0.5 step 7 records the operator's R8.D decision as
# skip_decisions.R8_D_spec_versioning, and the R0.8 manifest emits
# spec-versioning.md "(if not skipped)". Before WP3 nothing read the key: a
# skipped retrofit still got the file (conformance verifier, scenario j).
SV = ".claude/steering/spec-versioning.md"
_SKIPPED = getattr(templates, "spec_versioning_skipped", lambda c: None)
_POINTERS = getattr(templates, "_SPEC_VERSIONING_POINTERS", ())


def _retro(decision=None, optin=False):
    sd = ("" if decision is None else
          f"  skip_decisions:\n    R8_D_spec_versioning: \"{decision}\"\n")
    am = ("  autonomous_modes:\n    loop_mode_opted_in: true\n"
          if optin else "")
    return CFG_RETRO + sd + am


_rs_cfg, _rs = plan_for(_retro("skip"))
_rso_cfg, _rso = plan_for(_retro("skip", optin=True))
_rr_cfg, _rr = plan_for(_retro("run", optin=True))
_rs_paths = {a["path"] for a in _rs}
check("skip: the predicate reads the recorded decision",
      _SKIPPED(_rs_cfg) is True and _SKIPPED(_r_cfg) is False)
check("skip: no spec-versioning.md in the plan", SV not in _rs_paths
      and SV not in {a["path"] for a in _rso})
for label, plan in (("skip", _rs), ("skip + loop opt-in", _rso)):
    left = [a["path"] for a in plan
            if "spec-versioning" in (a.get("body") or "")]
    check(f"{label}: no emitted file points at spec-versioning.md", not left,
          left)
check("skip: every other path is the same as an install that runs R8.D",
      _rs_paths == {a["path"] for a in _r} - {SV})
_rs_md = body(_rs, "CLAUDE.md") or ""
check("skip: CLAUDE.md escalation 5 drops the pointer, not the escalation",
      "5. **🔔** Implementation reveals the spec was wrong.\n" in _rs_md,
      _rs_md[_rs_md.find("5. **"):][:120])
check("skip: INDEX.md keeps its schema pointer and drops the version one",
      ("writes each: `.claude/specs/README.md`.\n\n"
       in (body(_rs, IDX) or ""))
      and "Version rules" not in (body(_rs, IDX) or ""))
for skill_name, clause in (
        ("spec-new", "Changing a spec is a version bump.\n"),
        ("spec-validate", "- With `current` (a re-validation after a bump): "
                          "check against the current"),
        ("spec-decompose",
         "re-validates the task at the current\nversion.\n")):
    check(f"skip: {skill_name} reads its clause without the pointer",
          clause in (body(_rso, f".claude/skills/{skill_name}/SKILL.md")
                     or ""))
check("skip: the specs README's layout drops the pointer",
      "its frontmatter.\n" in (body(_rs, ".claude/specs/README.md") or ""))
for label, text in (("run", _retro("run")),
                    ("decide_later", _retro("decide_later")),
                    ("no decision recorded", _retro())):
    c, plan = plan_for(text)
    check(f"{label}: spec-versioning.md is emitted and CLAUDE.md points at it",
          SV in {a["path"] for a in plan}
          and "`.claude/steering/spec-versioning.md`" in body(plan,
                                                             "CLAUDE.md"))


def _skipped_or_error(c):
    try:
        return _SKIPPED(c)
    except Exception as e:  # a crash is a failed row, not a stopped suite
        return repr(e)


_gf_pred = _skipped_or_error({"mode": "greenfield", "retrofit": {
    "skip_decisions": {"R8_D_spec_versioning": "skip"}}})
_list_pred = _skipped_or_error({"mode": "retrofit", "retrofit": {
    "skip_decisions": ["R8_D_spec_versioning"]}})
check("the predicate: greenfield is never skipped, and a skip_decisions "
      "that is not a mapping is not a skip",
      _gf_pred is False and _list_pred is False, (_gf_pred, _list_pred))
# Each reworded clause is live: it is in an install that runs R8.D, so the
# table cannot go stale without the no-pointer rows above failing.
_run_bodies = [a["body"] for a in _rr] + [a["body"] for a in _r]
_stale = [ptr for ptr, _ in _POINTERS
          if not any(ptr in b for b in _run_bodies)]
check("every pointer the skip rewords is in an install that runs R8.D",
      len(_POINTERS) == 6 and not _stale, _stale)

# End to end: an install that ran R8.D, then the operator's skip.
_tmp = tempfile.mkdtemp()
try:
    d = os.path.join(_tmp, "r8d")
    os.makedirs(d)
    r1 = _install(d, _retro("run"))
    r2 = _install(d, _retro("skip"))
    st = {}
    try:
        with open(os.path.join(d, ".claude", ".retrofit-state.json")) as fh:
            st = json.load(fh)
    except (OSError, ValueError):
        pass
    with open(os.path.join(d, "CLAUDE.md")) as fh:
        cm = fh.read()
    check("re-install with the skip removes the unedited spec-versioning.md "
          "and rewords CLAUDE.md",
          r1.returncode == 0 and r2.returncode == 0
          and os.path.isfile(os.path.join(d, ".claude", "steering",
                                          "spec-versioning.md")) is False
          and f"REMOVE {SV}" in r2.stdout
          and "spec-versioning" not in cm,
          (r1.stderr[-300:], r2.stdout[-600:], r2.stderr[-300:]))
    check("the state file records the decision the install honoured",
          st.get("skip_decisions", {}).get("R8_D_spec_versioning") == "skip",
          st.get("skip_decisions"))
finally:
    shutil.rmtree(_tmp)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

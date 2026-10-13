#!/usr/bin/env python3
"""[WP3 records] WP3's records say what the code does.

Each row DERIVES the fact from the code (a resolved config, an emitted plan,
a real install, a parsed golden table) and then checks the record that
states it, so a record that drifts from the code fails here, not in the next
review. The records are the tracked ones WP3 wrote: the changelog's WP3
entry, the backlog's WP3 layers and rows Z-28 to Z-57, the seam contract's
dated WP3 notes, the PRD, Companion, RETROFIT.md and README notes, the
readiness layer on A-6, and the commented keys in bootstrap.config.yaml.

  - the mode WP3 ships (warn), its posture (FAIL_CLOSED 0, block renders 1),
    and the advisory-hook count the PRD note states;
  - the freeze-exception 84 table: counts and digest prefixes against the
    golden suites' own tables, the added paths against the emitted plan;
  - the seam notes: the git_hook manifest rows, owned_worktree and
    contributed_keys from a real install, exit 3 for an invalid
    worktree.baseRef, the exit-2 config refusals, RESOLVED_CONFIG["hooks"],
    and the ultracode flag the dispatch command in the loop wrappers
    carries;
  - the section 8.4 walk's section 7.2 and 7.3 rows;
  - the backlog rows the operator named, and the flip's blast radius;
  - RR-UP-1: every test file WP3 added is named in its changelog entry.

Run: python3 tests/test_wp3_records.py
"""
import ast
import hashlib
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

import defaults  # noqa: E402
import installer  # noqa: E402
import interview  # noqa: E402
import retrofit_interview  # noqa: E402
import sdk_gates_template  # noqa: E402
import templates  # noqa: E402
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
    # Table cells escape a literal `|` as `\|`; read it back as `|`.
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


def assigned_literal(rel, name):
    """The literal assigned to a module-level NAME in a test file, read
    with ast so the file is not run."""
    tree = ast.parse(read(rel))
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == name):
            try:
                return ast.literal_eval(node.value)
            except ValueError:
                return None
    return None


def plan_for(yaml_text, **hooks):
    raw = load_yaml(yaml_text)
    for k, v in hooks.items():
        raw.setdefault("hooks", {})[k] = v
    cfg, errs = defaults.resolve_config(raw)
    assert not errs, errs
    return cfg, {a["path"]: a for a in installer.build_plan(cfg)}


def posture(body):
    m = re.search(r"^FAIL_CLOSED=(\d)", body or "", re.M)
    return m.group(1) if m else None


FIXTURE_DEFAULT = read("bootstrap.config.yaml")
FIXTURE_SDK = 'gate_substrate: "sdk-callable"\n' + FIXTURE_DEFAULT
FIXTURE_DESIGN = assigned_literal("tests/test_greenfield_golden.py",
                                  "FIXTURE_DESIGN_STEERING")
FIXTURE_FULL = assigned_literal("tests/test_greenfield_golden.py",
                                "FIXTURE_FULL_AUTONOMOUS")
MODE = defaults.DEFAULTS["hooks"]["spec_gate_commit_mode"]
PREFIXES = defaults.DEFAULTS["hooks"]["spec_gate_commit_prefixes"]
SGC = ".claude/hooks/spec-gate-commit.sh"

_cfg_default, P_DEFAULT = plan_for(FIXTURE_DEFAULT)

# --------------------------------------------------------------------------- #
# 1. The changelog's WP3 entry
# --------------------------------------------------------------------------- #
print("\n=== 1. The changelog's WP3 entry ===")
_CL_RAW = cut(read("docs/changelog.md"),
              "## Post-2.8.0 — a spec workflow that reaches a merged commit "
              "(WP3)",
              "## Post-2.8.0 — hooks that reach the model (WP2)")
CL = flat(_CL_RAW)
check("the changelog's WP3 entry is found, above the WP2 entry", bool(CL))
check("no version bump: PROTOCOL_VERSION is still 2.8.0 in both modules, "
      "and the entry says freeze exception 84",
      installer.PROTOCOL_VERSION == templates.PROTOCOL_VERSION == "2.8.0"
      and "**No version bump** (fix, not surface; freeze exception **84**)"
      in CL)

# The mode WP3 ships. A flip changes DEFAULTS and needs its own record
# (backlog Z-28), so this row goes red with it.
check("the mode WP3 ships is DEFAULTS' (warn), and the entry says it ships "
      "warn and does not flip",
      MODE == "warn" and "**The check ships in warn mode, and why.**" in CL
      and "WP3 ships warn and does not flip" in CL, MODE)

_p_warn = posture(P_DEFAULT[SGC]["body"])
_, _P_BLOCK = plan_for(FIXTURE_DEFAULT, spec_gate_commit_mode="block")
_p_block = posture(_P_BLOCK[SGC]["body"])
check("spec-gate-commit's posture is 0 in warn mode and 1 in block mode",
      (_p_warn, _p_block) == ("0", "1"), (_p_warn, _p_block))
check("the entry states that posture: FAIL_CLOSED goes from 1 to 0, block "
      "renders 1",
      "`FAIL_CLOSED` goes from 1 to 0" in CL
      and "(block mode renders 1)" in CL)

# The freeze-exception 84 table, against the golden suites' own tables.
_COUNTS = dict(assigned_literal("tests/test_greenfield_golden.py",
                                "EXPECTED_ACTION_COUNTS") or {})
_rc = assigned_literal("tests/test_retrofit.py",
                       "EXPECTED_RETROFIT_COUNTS") or {}
_COUNTS.update({"retrofit " + k: v for k, v in _rc.items()})
_DIGESTS = dict(assigned_literal("tests/test_greenfield_golden.py",
                                 "EXPECTED_DIGESTS") or {})
_rd = assigned_literal("tests/test_retrofit.py",
                       "EXPECTED_RETROFIT_DIGESTS") or {}
_DIGESTS.update({"retrofit " + k: v for k, v in _rd.items()})
_ROWS = {m.group(1): (int(m.group(2)), int(m.group(3)), int(m.group(4)))
         for m in re.finditer(
             r"^\| (default|full_autonomous|design_steering|sdk_callable|"
             r"retrofit service|retrofit agent) \| (\d+) → (\d+) \| "
             r"\+(\d+) / 0 \|", _CL_RAW, re.M)}
check("the freeze table has a row for each of the six fixtures, and the "
      "golden tables have six counts",
      len(_ROWS) == 6 and set(_ROWS) == set(_COUNTS), (_ROWS, _COUNTS))
for _fx, (_old, _new, _add) in sorted(_ROWS.items()):
    check(f"freeze table, {_fx}: {_new} actions as the golden suite pins, "
          f"and +{_add} is the difference",
          _COUNTS.get(_fx) == _new and _new - _old == _add,
          (_fx, _old, _new, _add, _COUNTS.get(_fx)))
_FRZ = cut(CL, "**Freeze exception 84.**", "**Tests.**")
_named = dict(re.findall(r"(default|full_autonomous|design_steering|"
                         r"sdk_callable|service|agent) `([0-9a-f]{8})\.\.\.`",
                         _FRZ))
_named = {("retrofit " + k if k in ("service", "agent") else k): v
          for k, v in _named.items()}
check("the entry names a digest prefix for each of the six fixtures, as "
      "the golden suites pin them",
      len(_named) == 6 and all(
          _DIGESTS.get(k, "")[:8] == v for k, v in _named.items()),
      {k: (v, _DIGESTS.get(k, "")[:8]) for k, v in _named.items()})

_ADDED_TXT = cut(CL, "The eight added paths are", "The default's 25 moved bodies")
_ADDED = re.findall(r"`(\.claude/[^`]+)`", _ADDED_TXT)
check("the entry lists eight added paths", len(set(_ADDED)) == 8, _ADDED)
check("each is a non-critical file action in the default fixture's plan",
      all(p in P_DEFAULT and P_DEFAULT[p]["kind"] == "file"
          and installer._hook_tier(P_DEFAULT[p]) == installer.TIER_NON
          for p in _ADDED),
      [p for p in _ADDED if p not in P_DEFAULT])
_, _P_DESIGN = plan_for(FIXTURE_DESIGN or "")
check("design_steering (tdd_policy off) lacks the test-author command, as "
      "the entry says, and has the other seven",
      ".claude/commands/test-author.md" not in _P_DESIGN
      and all(p in _P_DESIGN for p in _ADDED
              if p != ".claude/commands/test-author.md")
      and "`.claude/commands/test-author.md` (not in design_steering)"
      in _ADDED_TXT)

# The section 8.4 walk.
_WALK = cut(CL, "| §8.4 trigger | Fires? | Why |", "**What WP3 does not do.**")
_WALK_RAW = cut(_CL_RAW, "| §8.4 trigger | Fires? | Why |",
                "**What WP3 does not do.**")
# One row per line; the separator row (|---|) does not match.
_fires = [m.group(1).strip() for m in
          re.finditer(r"^\| [^|]+ \| ([^|]+) \|", _WALK_RAW, re.M)][1:]
check("the walk has seven rows, and none fires (the seam's section 10 note "
      "says no trigger fires)",
      len(_fires) == 7
      and all(f in ("No", "No (not edited)") for f in _fires), _fires)
_NEWKEYS = ("spec_gate_commit_mode", "spec_gate_commit_prefixes",
            "ultracode")
_ANS = set(interview.ANSWER_KEYS) | set(retrofit_interview.ANSWER_KEYS)
check("section 7.3: no new config key is an ANSWERS key in either "
      "interview",
      not [k for k in _ANS if any(n in k for n in _NEWKEYS)],
      [k for k in _ANS if any(n in k for n in _NEWKEYS)])
_r73 = cut(_WALK, "| §7.3 provenance markers / synthesize-file contract |",
           "| `binds` set")
check("section 7.3: the walk's row reads No and names the three config keys",
      _r73.startswith("| §7.3 provenance markers / synthesize-file contract "
                      "| No |")
      and all(f"`{p}.{k}`" in _r73 for p, k in (
          ("hooks", "spec_gate_commit_mode"),
          ("hooks", "spec_gate_commit_prefixes"),
          ("workflow", "ultracode"))), _r73[:200])

# --------------------------------------------------------------------------- #
# 2. A real install: the manifest, settings.json and the stdout the seam
#    notes describe
# --------------------------------------------------------------------------- #
print("\n=== 2. A real install (seam sections 3.2, 7.1, 7.2) ===")
TMP = tempfile.mkdtemp(prefix="wp3-records-")
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("CLAUDE", "GIT_"))}
ENV["GIT_CEILING_DIRECTORIES"] = TMP
ENV.update(HOME=TMP, XDG_CONFIG_HOME=os.path.join(TMP, ".config"))
CFG = os.path.join(TMP, "config.yaml")
with open(CFG, "w", encoding="utf-8") as fh:
    fh.write('project:\n  name: "records"\n  archetype: "cli"\n'
             'commands:\n  test: "true"\n  lint: "true"\n  format: "true"\n')


def project(name, settings=None):
    d = os.path.join(TMP, name)
    os.makedirs(d)
    if GIT:
        subprocess.run([GIT, "init", "-q", d], env=ENV, check=True)
    if settings is not None:
        os.makedirs(os.path.join(d, ".claude"))
        with open(os.path.join(d, ".claude", "settings.json"), "w") as fh:
            fh.write(settings)
    r = subprocess.run([sys.executable, INSTALL, "-c", CFG, "-C", d],
                       capture_output=True, text=True, env=ENV, timeout=300)
    return d, r


try:
    check("git is on PATH (the install rows need a repository)", bool(GIT))
    D, R = project("p")
    check("the install exits 0", R.returncode == 0, R.stderr[-600:])
    try:
        with open(os.path.join(D, installer.MANIFEST)) as fh:
            MAN = {f["path"]: f for f in json.load(fh)["files"]}
    except (OSError, ValueError, KeyError):
        MAN = {}
    _hooks = {p: f for p, f in MAN.items() if f.get("kind") == "git_hook"}
    check("section 7.1/7.2: one git_hook row per shim, each non-critical",
          sorted(os.path.basename(p) for p in _hooks)
          == sorted(templates.GIT_HOOK_NAMES)
          and all(f.get("tier") == installer.TIER_NON
                  for f in _hooks.values()), _hooks)
    check("section 7.2: the new script actions are non-critical, "
          "settings.json stays security-critical",
          all(MAN.get(p, {}).get("tier") == installer.TIER_NON
              for p in (templates.GIT_HOOK_DISPATCH, templates.SPEC_CHECK_PATH,
                        templates.MERGE_BACK_SCRIPT))
          and MAN.get(".claude/settings.json", {}).get("tier")
          == installer.TIER_SECURITY)
    _srow = MAN.get(".claude/settings.json", {})
    check("section 7.1: the settings.json row records owned_worktree and "
          "contributed_keys as the seam note states them",
          _srow.get("owned_worktree") == {"baseRef":
                                          templates.WORKTREE_BASE_REF}
          and _srow.get("contributed_keys") == {"ultracode": True}
          and installer._SETTINGS_CONTRIBUTED_KEYS == ("ultracode",),
          (_srow.get("owned_worktree"), _srow.get("contributed_keys")))
    try:
        with open(os.path.join(D, ".claude", "settings.json")) as fh:
            SETTINGS = json.load(fh)
    except (OSError, ValueError):
        SETTINGS = {}
    check("Z-42: the emitted settings.json sets no switchModelsOnFlag, model "
          "or effortLevel; it sets ultracode and worktree.baseRef head",
          not ({"switchModelsOnFlag", "model", "effortLevel"} & set(SETTINGS))
          and SETTINGS.get("ultracode") is True
          and SETTINGS.get("worktree") == {"baseRef": "head"}, SETTINGS)
    _out = R.stdout.rstrip("\n").split("\n")
    _ns = [i for i, ln in enumerate(_out) if ln == "Next steps:"]
    check("section 3.2 (7): stdout ends with the Next steps: block",
          len(_ns) == 1 and all(ln.startswith("  ") for ln in
                                _out[_ns[0] + 1:]) if _ns else False,
          _out[-8:])

    # Exit 3 for a baseRef Claude Code rejects; null is kept with a warning.
    D3, R3 = project("p3", '{"worktree": {"baseRef": "local"}}\n')
    with open(os.path.join(D3, ".claude", "settings.json")) as fh:
        _kept = fh.read()
    check("section 3.2 (5): an invalid worktree.baseRef is declined, exit 3, "
          "the file left as it was",
          R3.returncode == 3
          and _kept == '{"worktree": {"baseRef": "local"}}\n',
          (R3.returncode, R3.stderr[-400:]))
    DN, RN = project("pn", '{"worktree": {"baseRef": null}}\n')
    check("section 3.2 (4): a null baseRef is kept, exit 0, with a warning",
          RN.returncode == 0 and "worktree.baseRef to null" in RN.stderr,
          (RN.returncode, RN.stderr[-400:]))
finally:
    shutil.rmtree(TMP, ignore_errors=True)

check("the accepted baseRef values are head and fresh (null warns)",
      tuple(sorted(templates.WORKTREE_BASE_REFS)) == ("fresh", "head")
      and all(installer._settings_unmergeable_reason(
          {"worktree": {"baseRef": v}}) is None for v in ("head", "fresh",
                                                         None))
      and installer._settings_unmergeable_reason(
          {"worktree": {"baseRef": "local"}}) is not None)

# --------------------------------------------------------------------------- #
# 3. The seam contract's WP3 notes
# --------------------------------------------------------------------------- #
print("\n=== 3. The seam notes ===")
SEAM = read("SEAM-CONTRACT-v3-0-0.md")
_s32 = after(anchored_line(SEAM, "| `bootstrap-install` | Install the "
                                 "`.claude/` workspace tree |"),
             "**[seam 3.0.0 in-version note, 2026-10-05, WP3")
check("section 3.2: the bootstrap-install row carries the WP3 note",
      bool(_s32))
check("section 3.2: it names exit 3 for a baseRef other than head, fresh "
      "or null",
      "exit-3" in _s32 and "`worktree.baseRef` other than `\"head\"`, "
      "`\"fresh\"` or `null`" in _s32, _s32[:300])
_bad = {"spec_gate_commit_mode": ("hooks", "blok"),
        "spec_gate_commit_prefixes": ("hooks", ["src"]),
        "ultracode": ("workflow", "false")}
for _k, (_sec, _v) in _bad.items():
    _raw = load_yaml(FIXTURE_DEFAULT)
    _raw.setdefault(_sec, {})[_k] = _v
    _, _errs = defaults.resolve_config(_raw)
    check(f"section 3.2 (6): an invalid {_sec}.{_k} is refused, and the note "
          f"names it",
          any(f"{_sec}.{_k}" in e for e in _errs)
          and f"`{_sec}.{_k}`" in _s32, _errs)
check("section 3.2 (8): the note says where the shims go",
      "`<git-common-dir>/hooks`" in _s32
      and all(f"`{n}`" in _s32 for n in templates.GIT_HOOK_NAMES))

_RES = {}
_mod = sdk_gates_template.sdk_gates_module(plan_for(FIXTURE_SDK)[0])
_m = re.search(r"^RESOLVED_CONFIG = (\{.*?^\})$", _mod, re.M | re.S)
if _m:
    _RES = json.loads(_m.group(1))
_s33 = after(anchored_line(SEAM, "- `build_hooks(config: dict) -> dict`"),
             "**[In-version note, 2026-10-05, WP3 / D2.]**")
check("section 3.3: RESOLVED_CONFIG's hooks object is exactly the two keys "
      "the note names",
      set(_RES.get("hooks", {})) == {"spec_gate_commit_mode",
                                     "spec_gate_commit_prefixes"}
      and "`spec_gate_commit_mode`" in _s33
      and "`spec_gate_commit_prefixes`" in _s33, _RES.get("hooks"))
_cov = after(anchored_line(SEAM, "- **Coverage.**"),
             "**[In-version note, 2026-10-05, WP3 / D2")
check("section 3.3: the Coverage note gives the warn-mode return shape",
      "\"additionalContext\": <message>}}` with no `permissionDecision`"
      in _cov)

_flag = "--settings '{\"ultracode\": false}'"
_, _P_FULL = plan_for(FIXTURE_FULL or "")
_s31 = after(anchored_line(SEAM, "- `claude -p` — headless (print) "
                                 "invocation."),
             "**[In-version note, 2026-10-05, WP3 / model assignment.]**")
check("section 3.1: the note names the flag, which the dispatch command "
      "in the emitted loop wrappers carries",
      f"`{_flag}`" in _s31
      and all(_flag in _P_FULL.get(w, {}).get("body", "")
              for w in (".claude/loop.sh", ".claude/goal-loop.sh")))
for _sec, _prefix, _marker in (
        ("4.3", "- The array, when present, is surfaced by Tessera",
         "**[In-version note, 2026-10-05, WP3 / D2.]**"),
        ("6.2", "A gate refusal surfaces to Tessera as a non-zero result",
         "**[In-version note, 2026-10-05, WP3 / D2.]**"),
        ("7.1", "- The protocol writes `.installer-manifest.json`",
         "**[In-version note, 2026-10-05, WP3.]**")):
    check(f"section {_sec}: the dated WP3 note is there",
          bool(after(anchored_line(SEAM, _prefix), _marker)))
_s10 = after(anchored_line(SEAM, "- **v3.0.0 (MAJOR — the WP1 re-cut; "
                                 "SUSPENDED, 2026-09-28)**"),
             "*(In-version note, 2026-10-05 — WP3,")
check("section 10: the v3.0.0 entry carries the WP3 note: no trigger, "
      "contract SUSPENDED", "no trigger fires" in _s10
      and "stays SUSPENDED" in _s10)

# --------------------------------------------------------------------------- #
# 4. The PRD, Companion, RETROFIT.md and README notes
# --------------------------------------------------------------------------- #
print("\n=== 4. The protocol notes ===")
PRD = read("Bootstrap-Protocol-v2-8-0.md")
_n767 = after(anchored_line(PRD, "     - **Spec gate (commit)**"),
              "**[Amended 2026-10-05, WP3 / D2.]**")
check("PRD 6.C commit gate: the note names the check of record, the agent "
      "scope, the prefixes key and each default prefix",
      f"`{templates.SPEC_CHECK_PATH}`" in _n767 and "`CLAUDECODE=1`" in _n767
      and "`hooks.spec_gate_commit_prefixes`" in _n767
      and all(f"`{p}`" in _n767 for p in PREFIXES)
      and all(f"`{n}`" in _n767 for n in templates.GIT_HOOK_NAMES),
      _n767[:300])
check("PRD 6.C commit gate: the note's shipped mode is DEFAULTS'",
      f"WP3 ships `{MODE}`" in _n767, MODE)
check("PRD 6.C: the warn-mode note at the entry-warn/commit-block line",
      "With `hooks.spec_gate_commit_mode: warn`, the default" in after(
          anchored_line(PRD, "- **Don't block file writes mid-plan.**"),
          "**[Amended 2026-10-05, WP3 / D2.]**"))
_adv = sorted(p for p, a in P_DEFAULT.items()
              if a["kind"] == "hook" and posture(a["body"]) == "0")
_n800 = after(anchored_line(PRD, "- ✅ **Fails closed when the parser does "
                                 "not WORK"),
              "**[Amended 2026-10-05, WP3 / D2.]**")
check("PRD hook checklist: 7 advisory hooks in the default install, "
      "spec-gate-commit among them, as the note says",
      len(_adv) == 7 and SGC in _adv
      and "a seventh advisory hook in the default install" in _n800, _adv)
_raw = load_yaml(FIXTURE_DEFAULT)
_raw.setdefault("autonomous_modes", {})["loop_mode_enabled"] = True
_cl, _el = defaults.resolve_config(_raw)
_lp = {a["path"]: a for a in installer.build_plan(_cl)} if not _el else {}
check("PRD hook checklist: drift-detector-loop-cooperation declares "
      "FAIL_CLOSED=0 too, as the note's parenthesis says",
      posture(_lp.get(".claude/hooks/drift-detector-loop-cooperation.sh",
                      {}).get("body")) == "0"
      and "`drift-detector-loop-cooperation` also declares `FAIL_CLOSED=0`"
      in _n800)
_, _P_OFF = plan_for(FIXTURE_DEFAULT, spec_gate_commit=False)
check("PRD recovery: hooks.spec_gate_commit: false drops dispatch (so the "
      "shims go), and the note names that switch",
      templates.GIT_HOOK_DISPATCH not in _P_OFF
      and templates.GIT_HOOK_DISPATCH in P_DEFAULT
      and "`hooks.spec_gate_commit: false`" in after(
          anchored_line(PRD, "**To disable hooks:**"),
          "**[Amended 2026-10-05, WP3 / D2.]**"))

COMP = read("Bootstrap-Protocol-Companion-v2-8-0.md")
_ta = P_DEFAULT.get(".claude/commands/test-author.md", {}).get("body", "")
check("Companion: test-author is a skill plus a thin command, not an agent",
      "Invoke the `test-author` skill." in _ta
      and ".claude/skills/test-author/SKILL.md" in P_DEFAULT
      and ".claude/agents/test-author.md" not in P_DEFAULT
      and "ships as a skill plus a thin `/test-author` command" in
      anchored_line(COMP, "| **`test-author` (subagent, if TDD)**"))

RETRO = read("RETROFIT.md")
check("RETROFIT.md R8.D: the skip is honoured exactly for the key the note "
      "names",
      templates.spec_versioning_skipped(
          {"mode": "retrofit",
           "retrofit": {"skip_decisions": {"R8_D_spec_versioning": "skip"}}})
      and not templates.spec_versioning_skipped(
          {"mode": "retrofit", "retrofit": {
              "skip_decisions": {"R8_D_spec_versioning": "decide_later"}}})
      and "`retrofit.skip_decisions.R8_D_spec_versioning: skip`" in after(
          anchored_line(RETRO, "   - **R8.D:** `.claude/steering/"
                               "spec-versioning.md` (if not skipped)."),
          "**[Corrected 2026-10-05, WP3.]**"))
check("RETROFIT.md rollout table: the week 4+ note's shipped mode is "
      "DEFAULTS'",
      f"WP3 ships `{MODE}`" in anchored_line(RETRO, "| Week 4+ |"))

README = read("README.md")
_hint = installer._git_hook_warnings(
    {"git_hooks": [{"name": "pre-commit", "path": ".git/hooks/pre-commit",
                    "state": "foreign", "detail": None, "rel": "."}]},
    "/p", False)
# [WP3 fix3 HD-1] The line is the guarded one now; the README wraps it.
_hline = re.findall(r"have that hook run `([^`]+)`", _hint[0] if _hint else "")
check("README: the git-hook bullet's line to add is what the installer's "
      "warning says (the guarded line, HD-1)",
      _hline and f"{templates.GIT_HOOK_DISPATCH} pre-commit" in _hline[0]
      and _hline[0].startswith("if [ -f ")
      and f"`{_hline[0]}`" in flat(README), _hint)
check("README: the merge-back bullet's baseRef is the one the installer "
      "writes", f'`"worktree": {{"baseRef": "{templates.WORKTREE_BASE_REF}"}}`'
      in README)
check("readiness: the A-6 entries carry the WP3 layer",
      "**[Layer 2026-10-05, WP3 (branch `feat/wp3-spec-workflow`, not yet "
      "merged): decided by D2" in read("docs/production-readiness.md"))

# The config fixture: the new keys as COMMENTED lines only, at DEFAULTS'
# values (bootstrap.config.yaml is golden fixture A's input).
_live = load_yaml(FIXTURE_DEFAULT)
check("bootstrap.config.yaml sets none of the three new keys",
      not ({"spec_gate_commit_mode", "spec_gate_commit_prefixes"}
           & set(_live.get("hooks", {})))
      and "ultracode" not in _live.get("workflow", {}))
for _sec, _key, _want in (("hooks", "spec_gate_commit_mode", MODE),
                          ("hooks", "spec_gate_commit_prefixes", PREFIXES),
                          ("workflow", "ultracode",
                           defaults.DEFAULTS["workflow"]["ultracode"])):
    _ln = anchored_line(FIXTURE_DEFAULT, f"  # {_key}: ")
    _val = None
    if _ln:
        try:
            _val = load_yaml(f"{_sec}:\n  " + _ln[len("  # "):] + "\n"
                             )[_sec][_key]
        except Exception as exc:  # noqa: BLE001 - a parse error is a FAIL
            _val = exc
    check(f"bootstrap.config.yaml: the commented {_sec}.{_key} line, "
          f"uncommented, is DEFAULTS' value", _val == _want, (_ln, _val))

# --------------------------------------------------------------------------- #
# 5. The backlog's WP3 rows
# --------------------------------------------------------------------------- #
print("\n=== 5. The backlog ===")
BL = read("docs/deferred-backlog.md")
# [WP3 fix1] Z-44 to Z-49 are fix round 1's deferrals (f5-records).
# [WP3 fix2] Z-50 and Z-51 are fix round 2's (g4-records).
# [WP3 fix3] Z-52 and Z-53 are fix round 3's (h4-records).
# [WP3 fix4] Z-54 to Z-56 are fix round 4's (i2-records).
# [WP3 fix5] Z-57 is fix round 5's (j2-records).
_ids = [f"Z-{n}" for n in range(28, 58)]
_rows = {i: anchored_line(BL, f"| {i} |") for i in _ids}
check(f"rows Z-28 to {_ids[-1]} exist, once each",
      all(_rows.values()), [i for i, r in _rows.items() if not r])
_deferred = cut(CL, "**What WP3 does not do.**", "**Freeze exception 84.**")
check(f"the entry's Deferred paragraph names exactly Z-28 to {_ids[-1]} "
      "(and the held Z-21), and its range ends at the last row",
      set(re.findall(r"Z-\d+", _deferred)) == set(_ids) | {"Z-21"}
      # [WP3 fix3] The range's end too: a stale "Z-28 to Z-51" passed the
      # set check while Z-52 and Z-53 were named in the list (mutant R23).
      and f"rows Z-28 to {_ids[-1]} (layer" in _deferred,
      sorted(set(re.findall(r"Z-\d+", _deferred))))
check("the backlog's WP3 layer paragraph is there and names the range",
      f"Z-28 to {_ids[-1]} are WP3 residue" in anchored_line(
          BL, "**Layer 2026-10-05, WP3 (branch `feat/wp3-spec-workflow`).**"))
for _rid, _what, _needles in (
        ("Z-28", "the deferred D2 flip",
         ["`hooks.spec_gate_commit_mode: warn`", "D5", "tests/live/README.md",
          "freeze exception"]),
        ("Z-29", "the two-call --no-verify gap",
         ["`git commit --no-verify`", "push time"]),
        ("Z-30", "silent loss of the git hook",
         ["fresh clone", "`git init`", "husky", "lefthook"]),
        ("Z-31", "worktree task-file edits under D5",
         ["worktree subagents", "`decision` — D5"]),
        ("Z-32", "retiring the legacy mention rule",
         ["no `Files:` block", "`INDEX.md`"]),
        ("Z-33", "tests on hand merges", ["pre-merge-commit", "test gate"]),
        ("Z-34", "the .gitattributes union",
         ["`specs/*/decisions.md merge=union`"]),
        ("Z-35", "pr-author and code-review bodies",
         ["`code-review`", "`pr-author`"]),
        ("Z-36", "the retrofit spec producers' contract",
         ["`legacy-spec`", "`boundary-spec`", "`ticket-to-spec`"]),
        ("Z-41", "the unmeasured platforms",
         ["macOS", "Git for Windows", "2.24"])):
    _r = _rows.get(_rid, "")
    check(f"{_rid} records {_what}", all(n in _r for n in _needles),
          [n for n in _needles if n not in _r])

# Z-28's blast radius, derived: what the flip moves.
_moved = sorted(p for p in P_DEFAULT
                if P_DEFAULT[p]["body"] != _P_BLOCK.get(p, {}).get("body"))
_, _P_SDKW = plan_for(FIXTURE_SDK)
_, _P_SDKB = plan_for(FIXTURE_SDK, spec_gate_commit_mode="block")
_moved_sdk = sorted(p for p in _P_SDKW
                    if _P_SDKW[p]["body"] != _P_SDKB.get(p, {}).get("body"))
check("Z-28: the flip moves dispatch, spec-gate-commit.sh and the "
      "spec-decompose skill, plus gates.py in sdk_callable, as the row says",
      _moved == sorted([templates.GIT_HOOK_DISPATCH, SGC,
                        ".claude/skills/spec-decompose/SKILL.md"])
      and _moved_sdk == sorted(_moved + [".claude/sdk_gates/gates.py"])
      and all(n in _rows["Z-28"] for n in (
          "`.claude/githooks/dispatch`", "`spec-gate-commit.sh`",
          "`skills/spec-decompose/SKILL.md`", "`gates.py`")),
      (_moved, _moved_sdk))
_j2 = anchored_line(BL, "| J-2 |")
check("J-2's done layer names the shipped default prefixes",
      list(PREFIXES) == list(templates.SPEC_GATE_DEFAULT_PREFIXES)
      and all(f"`{p}`" in after(_j2, "**done — WP3") for p in PREFIXES))

# --------------------------------------------------------------------------- #
# 5b. [WP3 fix1] The dated layers fix round 1 appended (review MU-1, MU-3,
#     MT-3), each against the code or the emitted file it describes.
# --------------------------------------------------------------------------- #
print("\n=== 5b. Fix round 1 layers ===")
_FIX1 = "**[Amended 2026-10-06, WP3 fix round 1"
_wt = after(anchored_line(PRD, "  - **[v2.0.0] Native worktree routing.**"),
            _FIX1 + ", review MU-3.]**")
_ins = json.loads(P_DEFAULT[".claude/settings.json"]["body"])
# [WP3 fix2 RR-3] The wrappers are skeletons: the flag is in the dispatch
# command they give the operator to complete (a comment and a stderr hint),
# and no line of theirs runs `claude -p`.
_wrap_runs = [ln for w in (".claude/loop.sh", ".claude/goal-loop.sh")
              for ln in _P_FULL.get(w, {}).get("body", "").split("\n")
              if re.match(r"\s*(exec\s+)?claude\s+-p\b", ln)]
check("MU-3: PRD :1018 says the installer writes ultracode on by default "
      "and names the flag, which the dispatch command the emitted wrappers "
      "give the operator carries (no wrapper line runs claude -p)",
      defaults.DEFAULTS["workflow"]["ultracode"] is True
      and _ins.get("ultracode") is True
      and '`"ultracode": true`' in _wt and "`workflow.ultracode`" in _wt
      and f"`{_flag}`" in _wt and not _wrap_runs
      and all(_flag in _P_FULL.get(w, {}).get("body", "")
              for w in (".claude/loop.sh", ".claude/goal-loop.sh")), _wt)
_s95 = after(anchored_line(PRD, "4. **Invokes `claude -p`**"),
             _FIX1 + ", review MU-3.]**")
check("MU-3: Phase 9.5 step 4 (Invokes `claude -p`) carries the flag too",
      f"`{_flag}`" in _s95)
check("RR-3: neither MU-3 layer says the wrappers' dispatch lines carry the "
      "flag; both say the wrappers dispatch nothing",
      "dispatch lines do" not in _wt and "dispatch line carries" not in _s95
      and all("the wrappers dispatch nothing" in t for t in (_wt, _s95)),
      (_wt[-300:], _s95[-300:]))
_fb = after(anchored_line(COMP, "- **Fable.** This amends"),
            "**[Corrected 2026-10-06, WP3 fix round 1, review MU-1.]**")
check("MU-1: the Fable bullet's correction says the main-session switch "
      "lasts the session until /model or a new session, a subagent's one "
      "response, and that the target is not fixed",
      all(w in _fb for w in (
          "for the rest of the session", "`/model`",
          "`claude --model opus`",
          "A subagent's switch covers only that response.",
          "The target is not fixed")), _fb)
_bl97 = _P_FULL.get(".claude/queue/backlog.md", {}).get("body", "")
_s97 = after(anchored_line(PRD, "4. **Generate the queue scaffolding.**"),
             _FIX1 + ".]**")
check("MT-3: Phase 9.7 step 4's layer quotes what the emitted backlog.md "
      "comment says, and the comment says it",
      "the operator adds tasks to `Ready to run`, `Operator-only` and "
      "`Deferred` from the list `/spec-decompose` prints" in _s97
      and "the operator adds tasks here\n     from the list /spec-decompose "
      "prints" in _bl97 and "populated by spec-decompose" not in _bl97,
      (_s97, _bl97[:300]))
check("MT-3: the Companion's backlog.md row carries the same layer",
      "The emitted `spec-decompose` does not write this file" in after(
          anchored_line(COMP, "| `.claude/queue/backlog.md` |"),
          _FIX1 + ".]**"))

# --------------------------------------------------------------------------- #
# 5c. [WP3 fix1, f5-records] The records fix round 1 corrected (review RC-1
#     to RC-7, F3 to F6, MU-5 to MU-7, SDKP-1, SDKP-4, the critic's upgrade
#     observation, and operator decisions 2026-10-06 (1) and (2)). Each row
#     first derives the fact from git, a real install or the emitted hooks,
#     then checks the records that state it.
# --------------------------------------------------------------------------- #
print("\n=== 5c. Fix round 1 records ===")

# RC-3. Every frozen source whose bytes differ from 3d866f4's is named in
# freeze exception 84's list, or in a later freeze exception. The digests
# are pinned as data: CI's checkout is shallow, so no git walk reaches
# 3d866f4. The build's list missed docs/SKILL.md, a frozen body.
_FROZEN_AT_BASE = {
    "bin/bootstrap-install":
        "a4e6dbd4d816b5f98d8abeda5494287289ed50bf591f1630387020403934ce69",
    "bin/bootstrap-interview":
        "b8bd32ec745223dc78512e0573ec4a56d864956f48810cb8b34dc32c1c3b7d99",
    "bin/retrofit-interview":
        "6e78a48625782f0213f3dda346a2253854e853ce29f494535eba612596e5fa6c",
    "bin/run-tests":
        "b6486be9ac56891b715fe690623496865d68f35ff9f63f45a3048665ab757f06",
    "bin/trust-ramp":
        "80bf53ea857d10ac66b77d14638756f3e7b256b6034fea906f7bb673cf4eb2a7",
    "bootstrap.config.yaml":
        "5082ece5fe38e61fb15a3dc8acbe030bf3a80f8928a75f22b232eb9ad2d2c667",
    "docs/SKILL.md":
        "c0f98130543b9f2bd0d2af2810f1819f03fa64c75343b01323c01d03026c594a",
    "docs/design-review.md":
        "989df603221a69dec98247a3d24b1aface872d07ff1c6533be9170af8f4ea4a1",
    "docs/design.md":
        "3b04e0b53ca57ed02641fb741e4aa1426c8cefebc74c67d3b3cbf21aaacb103b",
    "lib/cmdpos.py":
        "d716990c9759afc1d003297d9685f7c8dc8970c44114dc3b55da63a54daa1404",
    "lib/configemit.py":
        "1621fbf526a5597e6c137f5f05597b8c7768d4c90ab2ae647dfd5a93eb4cd97f",
    "lib/defaults.py":
        "90e8e7fd1c8cd0a28b00e5576d059477c621b911565d1fd2dbf71ce66f8c6a60",
    "lib/ic_checks.py":
        "a2bdcb660d09bad35d5e7a8b26ab8326fdc6efaf3d3843f2ace1adb942756aa2",
    "lib/installer.py":
        "40644a194e0b421dc724c37f89c233d6f49117a2b50c98d751a9a6046f619cab",
    "lib/interview.py":
        "b3ff62db8b1b716d738d6be051fd72ec5cc9ddcbf69a6fa33cc8483dffb42ffd",
    "lib/inventory_scan.py":
        "702d974b9f9ce42faf408a7a5d678d20c260f1075968c4a35473ff826119321a",
    "lib/llm_advisor.py":
        "0eb385f49faa891de4546b02dff80f1c771d62fa542f2a60dedeacf712e6ced9",
    "lib/minyaml.py":
        "21c7cacd5896cf582b0d98d02f070a4a404014edff8ade322a7e4508d81bf89d",
    "lib/prd_heuristics.py":
        "4e2ee4e15b167df65419cbdf122e9323c49917a1937ec872a2d2271688c337ea",
    "lib/retrofit_heuristics.py":
        "bca1e38cebb696ef9b6dade9ccb8e358aac88213bfa80b28458ec3999199b24a",
    "lib/retrofit_interview.py":
        "c9a1c172cc4c87409306d44f7e66b6ef2406182270c52c44987fa5b34edd7f03",
    "lib/sdk_gates_template.py":
        "1b6801cb7559e4e8d40169e79213b6a3ffead9676f09f4d4cf40031dd798447a",
    "lib/templates.py":
        "70bb2131b3523f8ff4d490a9a50542c7e9baf9492748910340850e2dce4931f4",
    "tests/test_installer.py":
        "62518882965a4db3bfa9b607384427237800fdc0434712c45f18fbdeb8b93f42",
}


def _sha(rel):
    try:
        with open(os.path.join(ROOT, rel), "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


_moved_src = sorted(f for f, h in _FROZEN_AT_BASE.items() if _sha(f) != h)
_CL_ALL = read("docs/changelog.md")
# Exception 84's list, plus any later exception's paragraph (forward-
# compatible: a later package that moves a frozen source names it there).
_frz_txt = flat(cut(_CL_RAW, "**Freeze exception 84.**",
                    "and the six moving digests"))
for _m in re.finditer(r"\*\*Freeze exception (\d+)\.\*\*", _CL_ALL):
    if int(_m.group(1)) > 84:
        _frz_txt += " " + flat(_CL_ALL[_m.start():_CL_ALL.find(
            "\n\n", _m.start())])
check("RC-3: docs/SKILL.md, a frozen body test_installer pins, moved since "
      "3d866f4 (the case the build's list missed)",
      "docs/SKILL.md" in _moved_src and "_read_frozen(\"docs/SKILL.md\")"
      in read("tests/test_installer.py"), _moved_src)
check("RC-3: freeze exception 84 names every frozen source whose bytes "
      "differ from 3d866f4's (or a later exception does)",
      bool(_frz_txt) and all(f"`{f}`" in _frz_txt for f in _moved_src),
      [f for f in _moved_src if f"`{f}`" not in _frz_txt])

# A hermetic git for the rows below (review TP-03: no host config).
T5 = tempfile.mkdtemp(prefix="wp3-records-5c-")
E5 = {k: v for k, v in os.environ.items()
      if not k.startswith(("CLAUDE", "GIT_"))}
E5.update(HOME=T5, XDG_CONFIG_HOME=os.path.join(T5, ".config"),
          GIT_CEILING_DIRECTORIES=T5, GIT_CONFIG_NOSYSTEM="1",
          GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
          GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
os.makedirs(os.path.join(T5, ".config", "git"))
with open(os.path.join(T5, ".config", "git", "config"), "w") as _fh:
    _fh.write("[init]\n\tdefaultBranch = main\n[commit]\n\tgpgsign = false\n"
              "[maintenance]\n\tauto = false\n[gc]\n\tauto = 0\n"
              "[advice]\n\tdetachedHead = false\n")
AGENT = dict(E5, CLAUDECODE="1")
CFG5 = os.path.join(T5, "config.yaml")
with open(CFG5, "w", encoding="utf-8") as _fh:
    _fh.write('project:\n  name: "records5"\n  archetype: "cli"\n'
              'commands:\n  test: "true"\n  lint: "true"\n  format: "true"\n')


def g5(d, *args, env=None):
    return subprocess.run([GIT, "-C", d, *args], capture_output=True,
                          text=True, env=env or E5, timeout=120)


def put(d, rel, body):
    p = os.path.join(d, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(body)


def install5(d):
    return subprocess.run([sys.executable, INSTALL, "-c", CFG5, "-C", d],
                          capture_output=True, text=True, env=E5,
                          timeout=300)


def fallback5(d, cmd="git commit -m x"):
    """The PreToolUse fallback, as Claude Code runs it: cwd and
    CLAUDE_PROJECT_DIR are the project."""
    payload = json.dumps({"hook_event_name": "PreToolUse",
                          "tool_name": "Bash", "tool_input": {"command": cmd}})
    return subprocess.run(["bash", os.path.join(d, SGC)], cwd=d,
                          input=payload, capture_output=True, text=True,
                          env=dict(E5, CLAUDE_PROJECT_DIR=d), timeout=120)


_TASK = ("---\nid: demo-T01\nspec: demo\nspec_version: 1.0.0\n"
         "status: in-progress\nblocked_by: []\n---\n\nSlice: x\n\n"
         "Files:\n- src/ok.py\n")

try:
    check("(5c) git is on PATH", bool(GIT))

    # RC-1, F6. Which git routes run the commit hooks at all: measured on
    # git itself, with hooks that only log their own name.
    R5 = os.path.join(T5, "routes")
    g5(T5, "init", "-q", R5)
    for _h in ("pre-commit", "pre-merge-commit"):
        put(R5, f".git/hooks/{_h}",
            f'#!/bin/sh\necho {_h} >> "$(git rev-parse --git-dir)/hooklog"\n')
        os.chmod(os.path.join(R5, ".git", "hooks", _h), 0o755)
    _LOG = os.path.join(R5, ".git", "hooklog")

    def fired(*cmd):
        """Run one git command; return (rc, the hooks it fired)."""
        open(_LOG, "w").close()
        r = g5(R5, *cmd)
        with open(_LOG) as fh:
            return r.returncode, fh.read().split()

    def commit5(d, rel, msg):
        put(d, rel, msg + "\n")
        g5(d, "add", rel)
        return g5(d, "commit", "-q", "-m", msg).returncode

    put(R5, "a", "a\n")
    g5(R5, "add", "a")
    _routes = {"plain commit": fired("commit", "-q", "-m", "a")}
    g5(R5, "checkout", "-q", "-b", "ff")
    commit5(R5, "b", "b")
    g5(R5, "checkout", "-q", "main")
    _routes["fast-forward merge"] = fired("merge", "-q", "ff")
    g5(R5, "checkout", "-q", "-b", "side")
    commit5(R5, "c", "c")
    g5(R5, "checkout", "-q", "main")
    commit5(R5, "d", "d")
    _routes["merge commit"] = fired("merge", "-q", "--no-edit", "side")
    g5(R5, "checkout", "-q", "-b", "pick", "main~1")
    commit5(R5, "e", "e")
    _pick = g5(R5, "rev-parse", "HEAD").stdout.strip()
    g5(R5, "checkout", "-q", "main")
    _routes["cherry-pick"] = fired("cherry-pick", _pick)
    _routes["revert"] = fired("revert", "--no-edit", "HEAD")
    g5(R5, "checkout", "-q", "-b", "rb", "main~2")
    commit5(R5, "f", "f")
    _routes["rebase"] = fired("rebase", "-q", "main")
    g5(R5, "checkout", "-q", "main")
    _pd = os.path.join(T5, "patches")
    g5(R5, "format-patch", "-q", "-1", "rb", "-o", _pd)
    _routes["git am"] = fired("am", "-q", *sorted(
        os.path.join(_pd, f) for f in os.listdir(_pd)))
    # [WP3 fix2 MR-9] Two more routes that make a commit and run no hook:
    # git stash, and git commit-tree (plumbing).
    put(R5, "a", "stash me\n")
    _routes["git stash"] = fired("stash", "-q")
    _tree5 = g5(R5, "write-tree").stdout.strip()
    _routes["git commit-tree"] = fired("commit-tree", "-m", "ct", "-p",
                                       "HEAD", _tree5)
    # [WP3 fix2 MR-2] A cherry-pick that stops on conflicts fires pre-commit
    # when --continue concludes it (only a clean one fires nothing).
    g5(R5, "checkout", "-q", "-b", "cpside", "main")
    commit5(R5, "k", "side")
    g5(R5, "checkout", "-q", "main")
    commit5(R5, "k", "main")
    _routes["conflicted cherry-pick"] = fired(
        "cherry-pick", g5(R5, "rev-parse", "cpside").stdout.strip())
    put(R5, "k", "resolved\n")
    g5(R5, "add", "k")
    open(_LOG, "w").close()
    _cont = g5(R5, "cherry-pick", "--continue",
               env=dict(E5, GIT_EDITOR="true"))
    with open(_LOG) as _fh:
        _routes["cherry-pick --continue"] = (_cont.returncode,
                                             _fh.read().split())
    check("RC-1: (control) a plain commit fires pre-commit, and a merge "
          "commit fires pre-merge-commit",
          _routes["plain commit"] == (0, ["pre-commit"])
          and _routes["merge commit"] == (0, ["pre-merge-commit"]), _routes)
    _silent = ("fast-forward merge", "cherry-pick", "revert", "rebase",
               "git am")
    check("RC-1, F6: a fast-forward merge, cherry-pick, revert, rebase and "
          "git am land (rc 0) and fire neither hook",
          all(_routes[k] == (0, []) for k in _silent), _routes)
    _z29 = _rows.get("Z-29", "")
    check("RC-1, F6: Z-29 names each of those routes and the option that "
          "covers them",
          all(w in _z29 for w in ("fast-forward", "`cherry-pick`",
                                  "`revert`", "`rebase`", "`git am`",
                                  "push time")), _z29[:300])
    _dont = cut(CL, "**What WP3 does not do.**", "**Freeze exception 84.**")
    check("RC-1, F6: the changelog's 'What WP3 does not do' names them too",
          all(w in _dont for w in ("fast-forward", "`cherry-pick`",
                                   "`revert`", "`rebase`", "`git am`")),
          _dont[:300])
    check("MR-9: git stash and git commit-tree make a commit (rc 0) and fire "
          "neither hook; Z-29's layer, the changelog and the PRD :767 note "
          "name both",
          _routes["git stash"] == (0, [])
          and _routes["git commit-tree"] == (0, [])
          and all(w in t for w in ("`git stash`", "`git commit-tree`")
                  for t in (after(_z29, "re-review RR-1, MR-9"), _dont,
                            _n767)), _routes)
    check("MR-2: a cherry-pick that stops on conflicts fires no hook, and "
          "--continue then fires pre-commit; Z-29's layer says so, and the "
          "changelog's list says 'a clean `cherry-pick`'",
          _routes["conflicted cherry-pick"][0] != 0
          and _routes["conflicted cherry-pick"][1] == []
          and _routes["cherry-pick --continue"] == (0, ["pre-commit"])
          and "concluded with `--continue` or `git commit`, it fires "
          "pre-commit" in _z29
          and "a clean `cherry-pick`" in _dont, _routes)
    _mb = flat(cut(README, "- **Implementer branches land through "
                           "`.claude/merge-back.sh`", "## Tests"))
    check("RC-1: the README merge-back bullet no longer says every hand "
          "merge runs the spec check: one that fast-forwards runs no hook",
          "one that fast-forwards" in _mb and "runs no hook at all" in _mb
          and "`git merge` runs the spec check but not the test gate"
          not in _mb, _mb[:400])

    # A real install, default config: warn mode.
    P5 = os.path.join(T5, "p")
    g5(T5, "init", "-q", P5)
    _r1 = install5(P5)
    check("(5c) the install exits 0 and ends with the Next steps: block",
          _r1.returncode == 0 and "Next steps:" in _r1.stdout, _r1.stderr[-400:])
    # The critic's upgrade observation: the run says nothing about the
    # commit mode, so an upgrade from a refusing install is silent too.
    check("upgrade: a default install says nothing about the commit mode, so "
          "the records disclose it: the changelog, the README and Z-28 (e)",
          MODE == "warn" and "spec_gate_commit_mode" not in _r1.stderr
          and "**Upgrading an install made before WP3.**" in CL
          and "`hooks.spec_gate_commit_mode: block` before you re-install"
          in CL and "*Upgrading:*" in README
          and "(e) until the flip, a re-install over an install made before "
          "WP3 turns a refusing commit gate into a warning one"
          in _rows.get("Z-28", ""))

    # RC-2 (INST-8). With a task file, a re-install prints no Next steps.
    put(P5, ".claude/specs/demo/tasks/demo-T01.md", _TASK)
    _r2 = install5(P5)
    check("RC-2: with a task file, a re-install exits 0 with no Next steps: "
          "block", _r2.returncode == 0 and "Next steps:" not in _r2.stdout,
          _r2.stdout[-300:])
    _ns = "while the project has no task file"
    _walk32 = cut(_WALK, "| New automated CLI entry point", "| Field added")
    _item10 = cut(CL, "- **10. The Phase 10 handoff.**", "- **The interviews.**")
    check("RC-2: seam note (7), changelog item 10 and the walk's section 3.2 "
          "row each state that condition",
          _ns in _s32 and _ns in _item10 and _ns in _walk32,
          (_ns in _s32, _ns in _item10, _ns in _walk32))

    g5(P5, "add", "-A")
    g5(P5, "commit", "-q", "-m", "harness and the task")

    # Z-37 (c), F3. A --files path that ends in "/" is refused, exit 3.
    _r3 = subprocess.run(["bash", os.path.join(P5, templates.SPEC_CHECK_PATH),
                          "--files", "src/x/"], cwd=P5, capture_output=True,
                         text=True, env=E5, timeout=120)
    check("F3: spec-check.sh --files src/x/ exits 3, and Z-37 (c) says so",
          _r3.returncode == 3 and "ends in" in _r3.stderr
          and "a `--files` path that ends in `/` is refused with exit 3"
          in _rows.get("Z-37", ""), (_r3.returncode, _r3.stderr[-200:]))

    # Operator decision 2026-10-06 (1): a merge is checked only on its own
    # changes, through the real shims (warn mode prints what it finds).
    g5(P5, "checkout", "-q", "-b", "feat")
    # [WP3 fix2 RR-1] A person's commit (no CLAUDECODE): the shims are
    # installed, and src/unlisted.py is under a prefix and listed nowhere.
    put(P5, "src/unlisted.py", "person-on-feat\n")
    g5(P5, "add", "src/unlisted.py")
    _pc = g5(P5, "commit", "-q", "-m", "person-on-feat")
    g5(P5, "checkout", "-q", "main")
    commit5(P5, "NOTES.md", "person-on-main")
    _m1 = g5(P5, "merge", "--no-edit", "feat", env=AGENT)
    check("merge rule: a person's commit of an unlisted file lands with no "
          "check at all, and an agent merge of that branch, whose result "
          "equals a parent on every path, lands with no spec message: the "
          "rule lets the person's file in unchecked (re-review RR-1)",
          _pc.returncode == 0 and "spec check" not in _pc.stderr
          and _m1.returncode == 0 and "spec check" not in _m1.stderr
          and len(g5(P5, "rev-list", "--parents", "-1", "HEAD")
                  .stdout.split()) == 3, (_pc.stderr[-300:],
                                         _m1.stderr[-400:]))
    g5(P5, "checkout", "-q", "-b", "feat2")
    commit5(P5, "src/b.py", "person-on-feat2")
    g5(P5, "checkout", "-q", "main")
    commit5(P5, "NOTES2.md", "person-again")
    g5(P5, "merge", "-q", "--no-ff", "--no-commit", "feat2", env=AGENT)
    put(P5, "src/b.py", "edited inside the merge\n")
    g5(P5, "add", "src/b.py")
    _m2 = g5(P5, "commit", "--no-edit", env=AGENT)
    # [WP3 fix2 IT-4] This install is in warn mode: the merge commit goes
    # through right after the message, so it offers no git merge --abort.
    check("merge rule: an edit made inside the merge is the merge's own "
          "change, so the spec check names it, and in a merge it never says "
          "to unstage a file, nor, in warn mode, to run git merge --abort",
          "src/b.py" in _m2.stderr and "src/unlisted.py" not in _m2.stderr
          and "git restore --staged" not in _m2.stderr
          and "This is a merge" in _m2.stderr
          and "git merge --abort" not in _m2.stderr, _m2.stderr[-600:])
    _COV = after(anchored_line(SEAM, "- **Coverage.**"),
                 "**[In-version note, 2026-10-05, WP3 / D2")
    check("merge rule: the PRD :767 note, the changelog, the seam's Coverage "
          "note and the README each state it",
          "the merge's own changes" in _n767
          and "**Merges (operator decision 2026-10-06).**" in CL
          and "covers only the merge's own changes" in _COV
          and "checked only on the merge's own changes" in flat(README))

    # RC-7 (a). Without the shims the fallback names the missing hook only
    # when it has a finding.
    for _h in templates.GIT_HOOK_NAMES:
        os.remove(os.path.join(P5, ".git", "hooks", _h))
    put(P5, "README2.md", "docs\n")
    g5(P5, "add", "README2.md")
    _f1 = fallback5(P5)
    g5(P5, "reset", "-q")
    put(P5, "src/a.py", "a\n")
    g5(P5, "add", "src/a.py")
    _f2 = fallback5(P5)
    g5(P5, "reset", "-q")
    _gh = flat(cut(README, "- **The spec commit check runs from git hooks",
                   "- **Implementer branches land through"))
    check("RC-7 (a): a docs-only commit gets no output from the fallback, an "
          "unlisted src/ file gets the missing-hook note, and the README "
          "says 'when it finds an unlisted file'",
          _f1.returncode == 0 and not _f1.stdout.strip()
          and "not installed in this clone" in _f2.stdout
          and "when it finds an unlisted file, says that the git hook is "
          "missing" in _gh, (_f1.stdout[:200], _f2.stdout[:200]))

    # Operator decision 2026-10-06 (2): a project below the repository top,
    # named like a prefix (app/, the case the build broke; review CR-7).
    MONO = os.path.join(T5, "mono")
    APP = os.path.join(MONO, "app")
    os.makedirs(APP)
    g5(MONO, "init", "-q")
    _rm = install5(APP)
    put(APP, ".claude/specs/demo/tasks/demo-T01.md", _TASK)
    g5(MONO, "add", "-A")
    g5(MONO, "commit", "-q", "-m", "harness")
    put(APP, "src/ok.py", "ok\n")
    g5(MONO, "add", "app/src/ok.py")
    _fo = fallback5(APP)
    g5(MONO, "reset", "-q")
    put(APP, "src/u.py", "u\n")
    g5(MONO, "add", "app/src/u.py")
    _fu = fallback5(APP)
    g5(MONO, "reset", "-q")
    _imp = open(os.path.join(APP, ".claude", "agents", "implementer.md")
                ).read()
    check("below the top: exit 0, no git hook written, and auto isolation "
          "resolved to none, with a warning",
          _rm.returncode == 0
          and not os.path.exists(os.path.join(MONO, ".git", "hooks",
                                              "pre-commit"))
          and "\nisolation:" not in _imp.split("\n---\n")[0]
          and "\nisolation: worktree" in P_DEFAULT[
              ".claude/agents/implementer.md"]["body"].split("\n---\n")[0]
          and "resolved to none" in _rm.stderr, _rm.stderr[-500:])
    check("below the top: the fallback passes a file the project's own task "
          "file lists, and names an unlisted one by its project path",
          _fo.returncode == 0 and not _fo.stdout.strip()
          and "src/u.py" in _fu.stdout and "app/src/u.py" not in _fu.stdout
          and "below the repository's top level" in _fu.stdout,
          (_fo.stdout[:300], _fu.stdout[:300]))
    _s32_9 = after(_s32, "(9) Since fix round 1")
    check("below the top: the PRD :767 note, the changelog, the seam "
          "(Coverage and section 3.2 (9)) and the README say what works "
          "there",
          "the check is project-relative" in _n767
          and "**A project below the repository top (operator decision "
          "2026-10-06).**" in CL
          and "project-relative" in _COV
          and "resolves to `none`" in _s32_9
          and "In a project below the repository top" in flat(README))

    # [WP3 fix2, re-review IT-5, MR-4; backlog Z-50] A nested install: the
    # repository top is installed too. The project's fallback passes its
    # listed file, and the top's git hook checks the same commit against the
    # top's prefixes (`app/` covers it) and task files (none): in warn mode
    # it names the path; in block mode it refuses (Z-50, measured).
    _rt = install5(MONO)
    _rp = install5(APP)
    put(APP, "src/ok.py", "ok\n")
    g5(MONO, "add", "app/src/ok.py")
    _fn = fallback5(APP)
    _cn = g5(APP, "commit", "-q", "-m", "agent, listed", env=AGENT)
    _z50 = _rows.get("Z-50", "")
    check("Z-50: in a nested install the project's fallback passes its listed "
          "file, the top's git hook names it all the same, the project's "
          "install says so, and Z-50 and the README record it",
          _rt.returncode == 0 and _rp.returncode == 0
          and _fn.returncode == 0 and not _fn.stdout.strip()
          and _cn.returncode == 0 and "spec check" in _cn.stderr
          and "app/src/ok.py" in _cn.stderr
          and "The repository top has its own install" in _rp.stderr
          and "the top's prefix `app/` covers the path" in _z50
          and "(rc 1," in _z50 and "(backlog Z-50)" in flat(README),
          (_fn.stdout[:200], _cn.stderr[-300:], _rp.stderr[-300:]))
finally:
    shutil.rmtree(T5, ignore_errors=True)

# SDKP-1, SDKP-4: Z-38 (c) is superseded because the rendered gates.py
# reads task files the shell's way; (a) is about the hook's working
# directory, worktree or not, and (d) is a case of it.
_spec_fn = ""
try:
    _t = ast.parse(_mod)
    for _n in _t.body:
        if isinstance(_n, ast.AsyncFunctionDef) and _n.name == "_spec_check":
            _spec_fn = ast.get_source_segment(_mod, _n)
except SyntaxError:
    pass
_z38 = _rows.get("Z-38", "")
check("SDKP-1: gates.py's _spec_check reads task files with checkout-index, "
      "not cat-file, and Z-38 (c) says it is superseded",
      "checkout-index" in _spec_fn and "cat-file" not in _spec_fn
      and "(c) Superseded in fix round 1" in _z38, _z38[:200])
check("SDKP-4: Z-38 (a) is about the hook's working directory, in a "
      "worktree or not, and (d) is a case of (a)",
      "in a worktree or not" in _z38 and "it is a case of (a)" in _z38)

# RC-4. The interactive smoke run is the operator's, before the merge; no
# record of it exists in or out of the repository when this entry is
# written, so the entry must not read as if it does (the #113 class).
_smoke = cut(CL, "**Smoke stages 1-2.**", "**Review and fix round 1")
check("RC-4: the smoke paragraph states the interactive run as the "
      "operator's step before the merge, not as a record that exists",
      "The operator's interactive run is a session record" not in _smoke
      and "before WP3 merges" in _smoke
      and "This entry does not depend on its outcome" in _smoke, _smoke)

# INST-5. synthesize keeps the config-only keys of a config it replaces; the
# seam's section 7.3 note and the walk's section 7.3 row name exactly them.
import configemit  # noqa: E402
_new5 = {}
_kept5 = configemit.carry_config_only(
    _new5, {"workflow": {"ultracode": False}, "mcp": {"x": 1},
            "hooks": {"spec_gate_commit_mode": "block", "test_gate": False}})
_s73 = after(anchored_line(SEAM, "- **[seam 3.0.0, WP1] The synthesize-file "
                                 "contract changed"),
             "**[In-version note, 2026-10-06, WP3 fix round 1")
_drift = [k for k in configemit.CONFIG_ONLY_HOOK_KEYS if k.startswith("drift_")]
check("INST-5: synthesize keeps workflow, mcp and the hooks settings that "
      "are not toggles, and the seam's section 7.3 note names exactly those",
      _kept5 == ["workflow.ultracode", "mcp.x", "hooks.spec_gate_commit_mode"]
      and "test_gate" not in _new5.get("hooks", {})
      and all(f"`{s}`" in _s73 for s in configemit.CONFIG_ONLY_SECTIONS)
      and all(f"`{k}`" in _s73 for k in configemit.CONFIG_ONLY_HOOK_KEYS
              if k not in _drift)
      and len(_drift) == 3 and "three `drift_*` thresholds" in _s73
      and "`synthesize` keeps the config-only keys" in _r73, (_kept5, _s73[:200]))

# RC-6, MU-5, MU-6, MU-7: wording the review found misleading.
check("RC-6: RETROFIT.md's week-4 note says block blocks and warn only "
      "warns",
      "blocks (`block`) or only warns (`warn`, the default WP3 ships)"
      in RETRO)
_models = {m.group(1) for a in P_DEFAULT.values() if a["kind"] == "file"
           for m in re.finditer(r"^model: (\S+)$",
                                a["body"].split("\n---\n")[0], re.M)}
check("MU-5: no emitted model: value is fable, and the Companion no longer "
      "says the emitted files keep a fable alias",
      _models and "fable" not in _models
      and "none uses `fable`" in COMP
      and "The emitted files keep the aliases `fable`" not in COMP, _models)
check("MU-5: off first-party, only sonnet (and opus on Foundry) is older, "
      "in the Companion and the retrofit Companion",
      "on Bedrock, Vertex and Foundry they resolve to older models"
      not in COMP and "Off first-party they resolve to older models"
      not in read("RETROFIT-COMPANION.md")
      and "and on Foundry `opus` does too" in COMP
      and "and on Foundry `opus` does too" in read("RETROFIT-COMPANION.md"))
check("MU-6: the Companion's half-price note is limited to input and output",
      "Sonnet 5.5 costs half of Opus 5.5 for input and output tokens" in COMP)
check("MU-7: Z-42 says ultracode was measured too",
      "(`ultracode` and `effortLevel` measured" in _rows.get("Z-42", ""))

# --------------------------------------------------------------------------- #
# 5d. [WP3 fix2, g4-records] The records fix round 2 corrected (re-review
#     RR-1 to RR-6, and every WP3 record brought into line with fix round
#     2's code). Each row first derives the fact from the emitted files, the
#     installer or a shell, then checks the records that state it.
# --------------------------------------------------------------------------- #
print("\n=== 5d. Fix round 2 records ===")


def code_lines(body):
    """The lines of an emitted script that are not comments."""
    return [ln for ln in (body or "").split("\n")
            if ln.strip() and not ln.lstrip().startswith("#")]


_SC = P_DEFAULT[templates.SPEC_CHECK_PATH]["body"]
_DP = P_DEFAULT[templates.GIT_HOOK_DISPATCH]["body"]
_SG = P_DEFAULT[SGC]["body"]
_MB = P_DEFAULT[templates.MERGE_BACK_SCRIPT]["body"]
_CLF = flat(_CL_RAW)
_RDM = flat(README)
_MERGES = cut(CL, "**Merges (operator decision 2026-10-06).**",
              "**Where it runs.**")
_WHERE = cut(CL, "**Where it runs.**", "**A project below the repository top")
_FALLB = cut(CL, "**The PreToolUse hook becomes the fallback.**", "**Mode.**")
_MODE = cut(CL, "**Mode.**", "**Retrofit.**")
_ITEM9 = cut(CL, "- **9. Merge-back (D6).**", "- **10. The Phase 10 handoff.**")
_HARN = cut(CL, "- **The live-run harness.**", "**The check ships in warn mode")
_n800b = after(anchored_line(PRD, "- ✅ **Fails closed when the parser does "
                                  "not WORK"),
               "**[Amended 2026-10-05, WP3 / D2.]**")

# RR-1 (and MR-9). The reason fix round 1 gave for the merge rule is false
# for a person's commits (derived in 5c: one lands with no check, and the
# merge lets it in). A record may quote it only to say so.
_false = "commits were checked when they were made"
_quoted = ("\"each side's commits were checked when they were made\", which "
           "is false")
check("RR-1: no record states \"each side's commits were checked when they "
      "were made\" as the merge rule's reason (the changelog and Z-29 quote "
      "it only as false), and neither substrate's emitted check says it",
      CL.count(_false) == CL.count(_quoted) == 1
      and _rows["Z-29"].count(_false) == _rows["Z-29"].count(_quoted) == 1
      and all(_false not in t for t in (_RDM, _n767, flat(_cov), _SC, _mod)),
      (CL.count(_false), CL.count(_quoted)))
check("RR-1: the changelog, the README and the PRD :767 note give the real "
      "scope: a person's commits are never checked, so a merge can bring in "
      "a file no task file lists",
      "a person's commits are never checked" in _MERGES
      and "a merge can bring in a file no task file lists" in _MERGES
      and "your own commits never are" in _RDM
      and "can bring in a file no task file lists" in _RDM
      and "a person's are never checked" in _n767
      and "a merge can bring in a file no task file lists" in _n767)
check("RR-1: the build's refusal of a teammate's pull is stated for block "
      "mode, where SC-1 measured it (warn mode lets it through)",
      "in block mode an agent's `git pull --no-rebase`" in _MERGES
      and MODE == "warn")

# MR-1, MR-2, MR-5. The merge rule against git's automatic merge result,
# and a stopped cherry-pick or revert, on both substrates.
_sc_code = "\n".join(code_lines(_SC))
check("MR-1, MR-2: both substrates judge a merge against git merge-tree's "
      "automatic result and read CHERRY_PICK_HEAD and REVERT_HEAD, and the "
      "changelog, the PRD :767 note, the seam's Coverage note and the README "
      "say so",
      "merge-tree --write-tree" in _sc_code and "merge-tree" in _mod
      and all(h in _sc_code and h in _mod
              for h in ("CHERRY_PICK_HEAD", "REVERT_HEAD"))
      and all("automatic merge result" in t
              for t in (_MERGES, _n767, flat(_cov), _RDM))
      and "`CHERRY_PICK_HEAD`" in _MERGES
      and all("cherry-pick or revert that stopped on conflicts" in t
              for t in (_n767, flat(_cov))))
check("MR-5: the check reads stage-0 task files only (ls-files --stage), "
      "and the changelog says an unmerged task file is not counted",
      "ls-files -z --stage" in _sc_code
      and "A task file left unmerged by a conflict is not counted" in _MERGES)

# IT-1, IT-5, MR-4, RG-2. The fallback defers to the installer's own shim
# alone, by its git blob id (shell) or SHA-256 (SDK), at the top only.
_sg_code = "\n".join(code_lines(_SG))
check("IT-1, IT-5: the fallback defers only to the shim's own bytes (its "
      "blob ids, its SHA-256), only at the repository top, and greps no "
      "hook for the dispatch line",
      all(i in _SG for i in templates.GIT_HOOK_SHIM_IDS)
      and "git hash-object --no-filters" in _sg_code
      and '[ -z "$_sgpfx" ]' in _sg_code
      and ".claude/githooks/dispatch pre-commit'" not in _sg_code
      and templates.GIT_HOOK_SHIM_SHA256 in _mod
      and "_SPEC_RUNS_DISPATCH" not in _mod)
_old_defer = ("or when the active pre-commit hook's own text runs",
              "or a pre-commit hook that runs `.claude/githooks/dispatch "
              "pre-commit`, is installed",
              "(it defers to either)")
check("IT-1, IT-5: the changelog, the PRD :767 note and the seam's Coverage "
      "note say so, and none says the fallback defers to a hook whose text "
      "runs dispatch",
      "byte for byte" in _FALLB and "byte for byte and executable" in _n767
      and "byte for byte and executable" in flat(_cov)
      and not any(w in t for w in _old_defer
                  for t in (_FALLB, _n767, flat(_cov))))

# IT-1, IT-2, RG-2. The installer's warning for a hook that only names the
# line, and for one git skips.
_w_ment = installer._git_hook_warnings(
    {"git_hooks": [{"name": "pre-commit", "path": ".git/hooks/pre-commit",
                    "state": "foreign", "detail": None, "rel": ".",
                    "via": ".git/hooks/pre-commit", "noexec": False}]},
    "/p", False)
_w_noex = installer._git_hook_warnings(
    {"git_hooks": [{"name": "pre-commit", "path": ".git/hooks/pre-commit",
                    "state": "foreign", "detail": None, "rel": ".",
                    "via": "", "noexec": True}]}, "/p", False)
_walk32b = cut(_WALK, "| New automated CLI entry point", "| Field added")
check("IT-1, IT-2: a hook that names the dispatch line gets a warning (the "
      "installer cannot tell whether it runs), one git skips gets chmod +x, "
      "and seam (4) and (7), the changelog, the walk's section 3.2 row and "
      "the README say so",
      len(_w_ment) == 1 and "cannot tell whether git runs that line"
      in _w_ment[0] and len(_w_noex) == 1
      and "not executable, so git skips it" in _w_noex[0]
      and "cannot tell whether that line runs" in _s32
      and "per hook git skips because it is not executable" in _s32
      # [WP3 fix3 RR2-3] Fix round 2 ran 2026-10-06 to 2026-10-07.
      and "fix round 2 (2026-10-06 to 2026-10-07) withdrew it" in _s32
      and "cannot tell whether that line runs" in _WHERE
      and "a hook in place that names the dispatch line" in _walk32b
      and "a hook already runs the check" not in _walk32b
      and "It cannot tell whether a line you added runs" in _RDM,
      (_w_ment, _w_noex))

# MR-6. The fallback acts on the --continue forms too.
check("MR-6: both fallbacks act on git merge/cherry-pick/revert --continue, "
      "and the changelog, the PRD :767 note and the seam's Coverage note "
      "name it",
      "(merge|cherry-pick|revert) +--continue" in _SG
      and "(?:merge|cherry-pick|revert)" in _mod
      and all("`git merge --continue`" in t
              for t in (_FALLB, _n767, flat(_cov))))

# CRIT-1, MR-3. The end line replaces the `bash -n` guard.
check("CRIT-1, MR-3: the check ends every verdict with its end line, "
      "dispatch requires it, no emitted line runs bash -n, and the "
      "changelog and the PRD hook-checklist note say so",
      f"printf '%s\\n' \"$SC_END\"" in _SC
      and templates.SPEC_CHECK_END in _DP and templates.SPEC_CHECK_END in _SG
      and not any("bash -n" in ln for ln in code_lines(_DP) + code_lines(_SG))
      and f"`{templates.SPEC_CHECK_END}`" in CL
      and f"`{templates.SPEC_CHECK_END}`" in _n800b
      and "does not parse (`bash -n`)" not in _n800b
      and "cannot parse (`bash -n`)" not in _MODE,
      _n800b[-400:])

# RR-4. bash runs on past a syntax error inside a compound assignment: the
# reason the end line exists (Z-37 (g)).
_rr4 = subprocess.run(["bash", "-c", "A=(x y\necho mid\nf(){ echo f; }\n"
                       "echo end\n"], capture_output=True, text=True,
                      timeout=60)
check("RR-4: this bash runs on past a syntax error inside a compound "
      "assignment (rc 0, the last line ran), and Z-37 says so",
      _rr4.returncode == 0 and _rr4.stdout.split()[-1:] == ["end"]
      and "syntax error" in _rr4.stderr
      and "runs on past a syntax error in a compound assignment"
      in _rows["Z-37"], (_rr4.returncode, _rr4.stdout, _rr4.stderr[-200:]))

# RG-1, MBR-1 to MBR-3, CRIT-2. merge-back's signal handling and lock read.
_mb_code = code_lines(_MB)
check("RG-1, MBR-1 to MBR-3, CRIT-2: merge-back runs no setsid, runs its "
      "gates under set -m, ignores further signals, bounds the stop at 10 s "
      "and reads a worktree's locked file, and changelog item 9 says so",
      not any("setsid" in ln for ln in _mb_code)
      and any(ln.strip() == "set -m" for ln in _mb_code)
      # [WP3 fix3 MBS-1] PIPE too, inside on_signal only.
      and any(ln.strip() == "trap '' INT TERM HUP PIPE" for ln in _mb_code)
      and "Stopping the gates (up to 10 s)" in _MB
      and "rev-parse --absolute-git-dir" in _MB
      and "under `set -m`" in _ITEM9 and "up to 10 s" in _ITEM9
      and "KILL after 3 s" not in _ITEM9
      and all(f"re-review {i}" in _ITEM9 for i in ("RG-1", "MBR-3",
                                                     "CRIT-2")))
check("Z-39: fix round 2's layers record the 10 s stop, the 12.1 s stop "
      "without --init on bash 3.2 and 5.1, and (l)",
      all(w in _rows["Z-39"] for w in ("waits up to 10 s", "12.1 s",
                                       "bash 5.1.16", "(l) When the "
                                       "worktree is locked")))

# HF-1 to HF-4, MR-1 in the harness; HF-5 to HF-9.
_HSRC = read("tests/live/d2_block_flip.py")
_LRD = flat(read("tests/live/README.md"))
check("harness: the changelog's harness item records fix round 2, the "
      "harness judges a merge against merge-tree's result, and the live "
      "README says so",
      "Fix round 2 (re-review HF-1 to HF-4, MR-1)" in _HARN
      and '"merge-tree", "--write-tree"' in _HSRC
      and "*Added 2026-10-07 (WP3 fix2, MR-1):*" in _LRD
      and "from every parent, as the `pre-merge-commit` hook checks them"
      in _LRD)
check("HF-9: the live README and the harness no longer say the emitted loop "
      "wrappers run claude -p",
      "the emitted loop wrappers run an unattended" not in _LRD
      and "as the emitted loop wrappers run an unattended" not in flat(_HSRC)
      and "the wrappers are skeletons that dispatch nothing" in _LRD)

# RR-2. The review's verifiers, and which rows fix round 1 corrected.
_fr1 = cut(CL, "**Review and fix round 1 (2026-10-06).**",
           "**Re-review and fix round 2")
check("RR-2: fix round 1's paragraph says the critic's MINOR had no "
      "verifiers and names the rows it corrected, Z-28 to Z-30 and Z-37 to "
      "Z-42",
      "each of the lenses' 53 MAJOR and MINOR findings" in _fr1
      and "the critic's MINOR (CR-1) had no verifiers" in _fr1
      and "Z-28 to Z-30 and Z-37 to Z-42" in _fr1
      and "corrections to Z-28 to Z-43" not in _fr1, _fr1[-300:])
check("the changelog records the re-review and fix round 2, the critic's "
      "two unverified findings included",
      "**Re-review and fix round 2 (2026-10-06 to 2026-10-07).**" in CL
      and "3 MAJOR, 21 MINOR and 27 INFO" in CL
      and "the critic's MAJOR (CRIT-1) and MINOR (CRIT-2) had no verifiers"
      in CL)

# RR-5. Two 3d866f4 lines of RETROFIT.md, pinned as data (CI's checkout is
# shallow): the WP3 notes follow them, so each old line is a prefix (a
# table row: minus its closing " |").
_RETRO_BASE = (
    "| Week 4+ | Steady state | All hooks | (none)",
    "- **`reviewer`** — `model: opus`, `effort: high`, `tools: Read, Grep, "
    "Glob, Bash` (no Edit/Write). **Retrofit-specific instructions:**")
check("RR-5: the two RETROFIT.md lines the build edited mid-line keep their "
      "3d866f4 bytes, with the WP3 note after them",
      all(sum(ln.startswith(b + " ") for ln in RETRO.split("\n")) == 1
          for b in _RETRO_BASE)
      and "WP3 ships `warn`" in anchored_line(RETRO, _RETRO_BASE[0])
      and "`effort: xhigh`" in anchored_line(RETRO, _RETRO_BASE[1]))

# RR-6. The 30-minute stop is Claude Code's message, not a measurement.
check("RR-6: the README qualifies the 30-minute stop as Claude Code's own "
      "message, not measured, as Z-45 does",
      "by Claude Code's own message, it is stopped after 30 minutes (not "
      "measured)" in _RDM
      and "where it is stopped after 30 minutes" not in _RDM
      and "(not measured at that scale)" in _rows["Z-45"])
# MBR-6, the records half: what the re-review measured about CR-1 at the
# final wording (one live run, not repeatable in CI), and the script half
# filed in Z-51.
_z45b = after(_rows["Z-45"], "**Layer 2026-10-07 (WP3 fix round 2, "
                             "re-review MBR-6).**")
check("MBR-6: Z-45's layer says a live Monitor kept the -p session alive, "
      "the same-turn instruction held in 1 of 2 runs, and a --continue keeps "
      "the resolved merge; Z-51 (f) files the script half",
      "such as a live Monitor, keeps the session alive" in _z45b
      and "held in 1 of the 2 measured runs" in _z45b
      and "keeps the resolved merge in progress" in _z45b
      and "(f) MBR-6, the script half" in _rows["Z-51"], _z45b[:300])

# IT-7. The Companion's census: 17 switches, 11 + 6, each kept.
_fb7 = after(anchored_line(COMP, "- **Fable.** This amends"),
             "**[Corrected 2026-10-06, WP3 fix round 1, review MU-1.]**")
_m7 = re.search(r"each of the (\d+) main-session switches found there kept "
                r"its session on the model it switched to, Opus 4\.8 after "
                r"(\d+) and Opus 5 after (\d+)", _fb7)
check("IT-7: the Companion no longer says every main-session switch kept "
      "the session on Opus 4.8, and its counts add up (and match the six "
      "Opus 5 switches it names)",
      "each main-session switch kept the session on Opus 4.8" not in _fb7
      and bool(_m7) and int(_m7.group(1)) == int(_m7.group(2))
      + int(_m7.group(3)) and int(_m7.group(3)) == 6
      and "went to Opus 5 six times" in _fb7, _fb7[:400])

# Completeness. Every re-review finding is fixed and named in a record, or
# filed in the backlog. The IDs are pinned as data (the review record is
# outside the repository); RG-0-verified, RR-7 and CRIT-4 are pass records
# with nothing to fix. "X-1 to X-4" names X-2 and X-3 too.
_RE_IDS = ([f"IT-{n}" for n in range(1, 9)] + [f"MR-{n}" for n in range(1, 10)]
           + [f"HF-{n}" for n in range(1, 10)]
           + [f"RG-{n}" for n in range(1, 5)] + [f"RR-{n}" for n in range(1, 7)]
           + [f"MBR-{n}" for n in range(1, 10)]
           + [f"CRIT-{n}" for n in range(1, 4)])
_WP3_BL = " ".join(_rows[i] for i in _ids)
_rec_text = " ".join((CL, _WP3_BL, flat(COMP), _LRD))
_named_ids = set()
for _m in re.finditer(r"\b(IT|MR|HF|RG|RR|MBR|CRIT)-(\d+)(?: to (?:\1-)?(\d+))?",
                      _rec_text):
    _lo = int(_m.group(2))
    _hi = int(_m.group(3)) if _m.group(3) else _lo
    _named_ids.update(f"{_m.group(1)}-{k}" for k in range(_lo, _hi + 1))
check("every re-review finding (51, less 3 pass records) is named in the "
      "changelog's WP3 entry, a WP3 backlog row, the Companion or the live "
      "README",
      len(_RE_IDS) == 48 and not [i for i in _RE_IDS if i not in _named_ids],
      [i for i in _RE_IDS if i not in _named_ids])

# --------------------------------------------------------------------------- #
# 5e. [WP3 fix3, h4-records] The records fix round 3 corrected (re-review 2,
#     wp3-rereview2-wf_08e8d18b-090.json, 2026-10-12), and every WP3 record
#     brought into line with fix round 3's code. Each row first derives the
#     fact from git, a real install or the emitted files, then checks the
#     records that state it.
# --------------------------------------------------------------------------- #
print("\n=== 5e. Fix round 3 records ===")
_BL_LAYER = anchored_line(BL, "**Layer 2026-10-05, WP3 (branch "
                              "`feat/wp3-spec-workflow`).**")
_BELOW = cut(CL, "**A project below the repository top",
             "**The PreToolUse hook becomes the fallback.**")
_ITEM1 = cut(CL, "- **1. The spec check (D2).**", "**Merges (operator decision")
_COV3 = flat(_cov)
_S32F = flat(_s32)
_INST_SRC = read("lib/installer.py")
_TESTS3 = CL[CL.find("**Tests.**"):] if "**Tests.**" in CL else ""
# merge-back's header comment, as prose.
_mb_hdr = " ".join(ln.lstrip("#").strip() for ln in _MB.split("\n")
                   if ln.startswith("#"))

# RR2-3. The re-review 1 record was written 2026-10-06, and fix round 2 ran
# from 2026-10-06 to 2026-10-07 (both records are outside the repository,
# so the dates are pinned as data). No WP3 record gives that round one date.
_one_date = ("fix round 2 (2026-10-07)", "Fix round 2 of 2026-10-07",
             "**Re-review and fix round 2 (2026-10-07).**",
             "fix rounds of 2026-10-06 and 2026-10-07")
check("RR2-3: the re-review 1 record is dated 2026-10-06 in the backlog's "
      "WP3 layer and in Z-51, fix round 2 is given as 2026-10-06 to "
      "2026-10-07, no WP3 record gives it one date, and re-review 2 is cited "
      "with its date",
      "(`wp3-rereview1-wf_4855029b-81e.json`, 2026-10-06)" in _BL_LAYER
      and "(WP3 re-review, 2026-10-06;" in _rows["Z-51"]
      and "**Re-review and fix round 2 (2026-10-06 to 2026-10-07).**" in CL
      and "fix round 2 (2026-10-06 to 2026-10-07)" in _BL_LAYER
      and not [w for w in _one_date
               for t in (CL, flat(SEAM), _BL_LAYER) if w in t]
      and "(`wp3-rereview2-wf_08e8d18b-090.json`, 2026-10-12)" in _BL_LAYER
      and "**Re-review 2 and fix round 3 (2026-10-12).**" in CL,
      [w for w in _one_date for t in (CL, flat(SEAM), _BL_LAYER) if w in t])

# Re-review 2's findings, pinned as data (the record is outside the
# repository): the paragraph's counts are what the list adds up to.
_RR2_MINOR = ["EM-1", "MR2-1", "MR2-2", "MR2-3", "MR2-4", "HD-1", "MBS-1",
              "MBS-2", "MBS-3", "RR2-1", "RR2-2", "CRIT2-1"]
_RR2_INFO = ["EM-2", "MR2-5", "MR2-6", "HD-2", "HD-3", "HD-4", "HD-5",
             "MBS-4", "MBS-5", "MBS-6", "RR2-3", "RR2-4", "RR2-5", "RR2-6",
             "CRIT2-2", "CRIT2-3", "CRIT2-4", "CRIT2-5"]
_RR2_PASS = ["EM-0", "HD-0-verified", "MBS-0", "RR2-0-verified", "CRIT2-0"]
_rr2p = cut(CL, "**Re-review 2 and fix round 3 (2026-10-12).**",
            "**Seam — the §8.4 trigger walk.**")
_lens_minor = [i for i in _RR2_MINOR if not i.startswith("CRIT2-")]
check("re-review 2: the changelog's paragraph gives the counts the pinned "
      "finding list adds up to, and says the critic's MINOR had no "
      "verifiers",
      f"no MAJOR, {len(_RR2_MINOR)} MINOR and "
      f"{len(_RR2_INFO) + len(_RR2_PASS)} INFO findings; {len(_RR2_PASS)} "
      f"of the INFO ones record what held" in _rr2p
      and f"each of the lenses' {len(_lens_minor)} MINOR findings" in _rr2p
      and "the critic's MINOR (CRIT2-1) had no verifiers" in _rr2p
      and "wp3-rereview2-wf_08e8d18b-090.json" in _rr2p
      and "new rows Z-52 and Z-53" in _rr2p, _rr2p[:400])
_named2 = set()
for _m in re.finditer(r"\b(EM|MR2|HD|MBS|RR2|CRIT2)-(\d+)"
                      r"(?: to (?:\1-)?(\d+))?", _rec_text):
    _lo = int(_m.group(2))
    _hi = int(_m.group(3)) if _m.group(3) else _lo
    _named2.update(f"{_m.group(1)}-{k}" for k in range(_lo, _hi + 1))
_RR2_IDS = _RR2_MINOR + _RR2_INFO
check("every re-review 2 finding (35, less 5 pass records) is named in the "
      "changelog's WP3 entry, a WP3 backlog row, the Companion or the live "
      "README",
      len(_RR2_IDS) == 30 and not [i for i in _RR2_IDS if i not in _named2],
      [i for i in _RR2_IDS if i not in _named2])

# A hermetic git and installer for the rows below (review TP-03).
T6 = tempfile.mkdtemp(prefix="wp3-records-5e-")
E6 = dict(E5, HOME=T6, XDG_CONFIG_HOME=os.path.join(T6, ".config"),
          GIT_CEILING_DIRECTORIES=T6, GIT_EDITOR="true")
os.makedirs(os.path.join(T6, ".config", "git"))
with open(os.path.join(T6, ".config", "git", "config"), "w") as _fh:
    _fh.write("[init]\n\tdefaultBranch = main\n[commit]\n\tgpgsign = false\n"
              "[maintenance]\n\tauto = false\n[gc]\n\tauto = 0\n"
              "[advice]\n\tdetachedHead = false\n")
_CFG6 = {}
for _k, _extra in (("warn", ""),
                   ("off", "hooks:\n  spec_gate_commit: false\n"),
                   ("block", "hooks:\n  spec_gate_commit_mode: block\n")):
    _CFG6[_k] = os.path.join(T6, f"{_k}.yaml")
    with open(_CFG6[_k], "w", encoding="utf-8") as _fh:
        _fh.write('project:\n  name: "records6"\n  archetype: "cli"\n'
                  'commands:\n  test: "true"\n  lint: "true"\n'
                  '  format: "true"\n' + _extra)


def g6(d, *args, env=None):
    return subprocess.run([GIT, "-C", d, *args], capture_output=True,
                          text=True, env=env or E6, timeout=120)


def put6(d, rel, body, mode=None):
    put(d, rel, body)
    if mode is not None:
        os.chmod(os.path.join(d, rel), mode)


def install6(d, cfg="warn"):
    return subprocess.run([sys.executable, INSTALL, "-c", _CFG6[cfg], "-C", d],
                          capture_output=True, text=True, env=E6, timeout=300)


def notes6(r):
    return [ln for ln in r.stdout.split("\n") if ln.startswith("  note ")]


def repo6(name):
    d = os.path.join(T6, name)
    g6(T6, "init", "-q", d)
    return d


try:
    check("(5e) git is on PATH", bool(GIT))

    # RR2-5, HD-5. The installer's stdout notes, each from a real install:
    # the pre-commit framework's .legacy hook, a symlink to a copy of the
    # shim, and an empty core.hooksPath (with its warning, no shim, and a
    # git that then runs no hook at all).
    L6 = repo6("legacy")
    install6(L6)
    _hk = os.path.join(L6, ".git", "hooks")
    os.rename(os.path.join(_hk, "pre-commit"),
              os.path.join(_hk, "pre-commit.legacy"))
    put6(L6, ".git/hooks/pre-commit", "#!/usr/bin/env bash\n# File generated "
         "by pre-commit: https://pre-commit.com\nexit 0\n", 0o755)
    _n_leg = notes6(install6(L6))
    S6 = repo6("symlink")
    install6(S6)
    _copy = os.path.join(T6, "shim-copy")
    shutil.copy(os.path.join(S6, ".git", "hooks", "pre-commit"), _copy)
    os.chmod(_copy, 0o755)
    os.remove(os.path.join(S6, ".git", "hooks", "pre-commit"))
    os.symlink(_copy, os.path.join(S6, ".git", "hooks", "pre-commit"))
    _r_sym = install6(S6)
    H6 = repo6("hooks-off")
    put6(H6, ".git/hooks/pre-commit",
         '#!/bin/sh\ntouch "$(git rev-parse --git-dir)/ran"\n', 0o755)
    g6(H6, "config", "core.hooksPath", "")
    put6(H6, "x", "x\n")
    g6(H6, "add", "x")
    _c_off = g6(H6, "commit", "-q", "-m", "x")
    _ran = os.path.exists(os.path.join(H6, ".git", "ran"))
    os.remove(os.path.join(H6, ".git", "hooks", "pre-commit"))
    _r_off = install6(H6)
    check("HD-5: with core.hooksPath set to an empty value git runs no hook, "
          "and the install writes no shim, says so on stdout and warns to "
          "unset it",
          _c_off.returncode == 0 and not _ran
          and not os.path.exists(os.path.join(H6, ".git", "hooks",
                                              "pre-commit"))
          and "  note   git hooks pre-commit, pre-merge-commit not installed "
          "(hooks-off; see the warning below)" in notes6(_r_off)
          and "core.hooksPath is set to an empty value, which turns off "
          "every git hook" in _r_off.stderr, (_ran, notes6(_r_off)))
    check("RR2-5, HD-5: the pre-commit framework's .legacy hook and a "
          "symlink to a copy of the shim each get a stdout note, the symlink "
          "no warning",
          any("which runs this installer's hook as pre-commit.legacy)" in n
              for n in _n_leg)
          and any("which holds bootstrap-install's shim; left alone)" in n
                  for n in notes6(_r_sym))
          and "does not run from it" not in _r_sym.stderr,
          (_n_leg, notes6(_r_sym)))
    # The installer prints five kinds of stdout note; the walk's section 3.2
    # row and seam section 3.2 (7) name each (RR2-5: two lists lacked one).
    _n_src = len(re.findall(r'print\(f"  note   ', _INST_SRC))
    _walk_notes = ("stdout `note` lines (no repository",
                   "the hooks in `core.hooksPath` are the installer's own "
                   "shim", "runs this installer's hook as `pre-commit.legacy`",
                   "a hook that is a symlink to an exact copy of the shim",
                   "which hooks were not installed")
    _seam_notes = ("a stdout `note` says the git hooks were not installed",
                   "a stdout `note` says there is nothing to install",
                   "runs this installer's hook as `pre-commit.legacy`",
                   "a symlink to an exact copy of the installer's shim",
                   "says which hooks were not installed")
    check("RR2-5: the installer has five stdout notes, and the walk's "
          "section 3.2 row and seam section 3.2 (7) name each",
          _n_src == 5 and all(w in _walk32b for w in _walk_notes)
          and all(w in _S32F for w in _seam_notes),
          (_n_src, [w for w in _walk_notes if w not in _walk32b],
           [w for w in _seam_notes if w not in _S32F]))
    check("HD-5: the changelog, the walk and seam section 3.2 (4) record the "
          "empty core.hooksPath state, and the fallback note list has it",
          "An empty `core.hooksPath`, which turns every git hook off, is a "
          "state of its own" in _WHERE
          and "it is set to an empty value, which turns hooks off" in _FALLB
          and "an empty `core.hooksPath`" in _walk32b
          and "`core.hooksPath` is set to an empty value" in _S32F
          and "`core.hooksPath` is set to an empty value" in _COV3)

    # HD-1. Every remedy's line is guarded: a repository-local
    # core.hooksPath, a hook another tool wrote, a symlink, and the hook
    # managers' hints. Followed, the guarded line lets a person's commit
    # through once the gate is off, and the gate-off re-install names it.
    _gpc = installer._guarded_line("pre-commit")
    HP6 = repo6("hooks-path")
    g6(HP6, "config", "core.hooksPath", ".githooks")
    _r_hp = install6(HP6)
    _w_sym = installer._git_hook_warnings(
        {"git_hooks": [{"name": "pre-commit", "path": ".git/hooks/pre-commit",
                        "state": "foreign-symlink", "detail": "../x",
                        "rel": "."}]}, "/p", False)
    _w_pcf = installer._git_hook_warnings(
        {"git_hooks": [{"name": "pre-commit", "path": ".git/hooks/pre-commit",
                        "state": "foreign", "detail": "the pre-commit "
                        "framework", "rel": ".", "via": "",
                        "noexec": False}]}, "/p", False)
    _w_lh = installer._git_hook_warnings(
        {"git_hooks": [{"name": "pre-commit", "path": ".git/hooks/pre-commit",
                        "state": "foreign", "detail": "lefthook", "rel": ".",
                        "via": "", "noexec": False}]}, "/p", False)
    F6 = repo6("foreign")
    put6(F6, ".git/hooks/pre-commit", "#!/bin/sh\necho lint-ok\n", 0o755)
    _r_f1 = install6(F6)
    put6(F6, ".git/hooks/pre-commit",
         "#!/bin/sh\necho lint-ok\n" + _gpc + "\n", 0o755)
    _r_f2 = install6(F6, "off")
    put6(F6, "README.md", "a person's\n")
    g6(F6, "add", "README.md")
    _pc_g = g6(F6, "commit", "-q", "-m", "a person's commit")
    put6(F6, ".git/hooks/pre-commit", "#!/bin/sh\necho lint-ok\n"
         ".claude/githooks/dispatch pre-commit || exit 1\n", 0o755)
    put6(F6, "README.md", "a person's, again\n")
    g6(F6, "add", "README.md")
    _pc_u = g6(F6, "commit", "-q", "-m", "a person's commit, unguarded")
    check("HD-1: every remedy gives the guarded line (a repository-local "
          "core.hooksPath, a foreign hook, a symlink, lefthook), and the "
          "pre-commit framework's entry runs it through sh -c",
          f"`{_gpc}`" in _r_hp.stderr
          and "every repository on this machine" not in _r_hp.stderr
          and f"`{_gpc}`" in _r_f1.stderr
          and _w_sym and f"`{_gpc}`" in _w_sym[0]
          and _w_lh and f"`{_gpc}`" in _w_lh[0]
          and _w_pcf and "`entry: sh -c '[ ! -f .claude/githooks/dispatch ] "
          "|| exec bash .claude/githooks/dispatch pre-commit'`" in _w_pcf[0],
          (_r_hp.stderr[-300:], _w_pcf))
    check("HD-1: turned off, the re-install removes dispatch and names the "
          "hook that still mentions it; the guarded line lets a person's "
          "commit through, where the plain one refuses it",
          not os.path.exists(os.path.join(F6, templates.GIT_HOOK_DISPATCH))
          and ".git/hooks/pre-commit still mentions "
          "`.claude/githooks/dispatch pre-commit`" in _r_f2.stderr
          and _pc_g.returncode == 0 and _pc_u.returncode != 0,
          (_r_f2.stderr[-300:], _pc_g.returncode, _pc_u.returncode))
    check("HD-1: the changelog, seam section 3.2 (4) and Z-48's layer say "
          "every remedy's line is guarded and the gate-off re-install names "
          "what still mentions dispatch",
          "Since fix round 3 every remedy gives that guarded line" in _WHERE
          and "still mentions the dispatch line, for the operator to remove"
          in _WHERE
          and "every remedy's line is the guarded one" in _S32F
          and "(a) is superseded: every remedy's line is now the guarded one"
          in _rows["Z-48"])
    # [WP3 fix4 REC3-1] The README and seam (4) said "any hook or hook
    # manager file"; the scan leaves out a core.hooksPath every repository
    # reads, as the changelog says.
    check("REC3-1: the README and seam section 3.2 (4) name what the gate-off "
          "scan covers, and that a core.hooksPath every repository reads is "
          "left out, as the changelog does",
          "names any hook in this repository's hooks directory (husky 9's "
          "`.husky/<hook>`), and any lefthook or pre-commit framework config "
          "at the top, that still mentions `.claude/githooks/dispatch`, for "
          "you to remove; a `core.hooksPath` that every repository reads is "
          "left out." in flat(README)
          and "names any hook or hook manager file" not in flat(README)
          and "one per hook in the repository's hooks directory (husky 9's "
          "`.husky/<hook>`) and per lefthook or pre-commit framework config "
          "at the repository top that still mentions the dispatch line, for "
          "the operator to remove (a `core.hooksPath` that every repository "
          "reads is left out)." in _S32F
          and "a `core.hooksPath` that every repository reads is left out"
          in _WHERE)

    # HD-2, HD-3. The confirm recipe and a hook git skips.
    _mn_pc = installer._mention_note([("pre-commit", ".git/hooks/pre-commit")],
                                     templates.GIT_HOOK_DISPATCH)
    _mn_pmc = installer._mention_note(
        [("pre-merge-commit", ".git/hooks/pre-merge-commit")],
        templates.GIT_HOOK_DISPATCH)
    check("HD-2, HD-3: the confirm recipe is a terminal CLAUDECODE=1 git "
          "commit, pre-merge-commit has none, a hook git skips that lacks "
          "the line gets it with chmod +x only if, and the changelog says so",
          "`CLAUDECODE=1 git commit`" in _mn_pc
          and "make an agent commit" not in _mn_pc
          and "No ordinary commit confirms the pre-merge-commit line"
          in _mn_pmc and "spec check (pre-merge-commit)" not in _mn_pmc
          and len(_w_noex) == 1 and f"`{_gpc}`" in _w_noex[0]
          and "chmod +x it only if its own commands should run too"
          in _w_noex[0]
          and "(re-review 2 HD-2)" in _WHERE and "(re-review 2 HD-3)" in _WHERE
          and "`CLAUDECODE=1 git commit`" in _RDM, (_mn_pc, _w_noex))

    # HD-4. Installed package-first, the top's install says nothing, and
    # the package's warning gets the sentence only on its next re-install.
    M6 = os.path.join(T6, "mono")
    A6 = os.path.join(M6, "app")
    os.makedirs(A6)
    g6(M6, "init", "-q")
    _ra1 = install6(A6)
    _rt6 = install6(M6)
    _ra2 = install6(A6)
    _top_own = "The repository top has its own install"
    check("HD-4: package first, the top's install prints nothing about the "
          "package and the package's warning lacks the sentence until it is "
          "re-installed; the changelog, Z-50 and the README say so",
          _ra1.returncode == _rt6.returncode == _ra2.returncode == 0
          and _top_own not in _ra1.stderr and "app" not in _rt6.stderr
          and _top_own in _ra2.stderr
          and "when the top was installed first, or on the project's next "
          "re-install" in _BELOW
          and "**Narrowed 2026-10-12 (WP3 fix round 3, re-review 2 HD-4).**"
          in _rows["Z-50"]
          and "when the top was installed first" in _RDM,
          (_ra1.stderr[-200:], _rt6.stderr[-200:]))

    # MR2-3 (CRIT2-4), MR2-5, MR2-1. What git does, measured with hooks that
    # only log their own name.
    R6 = repo6("routes")
    for _h in ("pre-commit", "pre-merge-commit"):
        put6(R6, f".git/hooks/{_h}", f'#!/bin/sh\necho {_h} >> '
             f'"$(git rev-parse --git-dir)/hooklog"\n', 0o755)
    _LOG6 = os.path.join(R6, ".git", "hooklog")

    def fired6(*cmd):
        open(_LOG6, "w").close()
        r = g6(R6, *cmd)
        with open(_LOG6) as fh:
            return r.returncode, fh.read().split()

    def gpath6(name):
        return os.path.join(R6, g6(R6, "rev-parse", "--git-path",
                                   name).stdout.strip())

    put6(R6, "k", "a\nb\nc\n")
    g6(R6, "add", "k")
    g6(R6, "commit", "-q", "-m", "base")
    g6(R6, "checkout", "-q", "-b", "feature")
    put6(R6, "k", "a\nFEATURE\nc\n")
    put6(R6, "teammate.txt", "teammate\n")
    g6(R6, "add", "-A")
    g6(R6, "commit", "-q", "-m", "teammate: feature X")
    _feat = g6(R6, "rev-parse", "HEAD").stdout.strip()
    g6(R6, "checkout", "-q", "main")
    put6(R6, "k", "a\nMAIN\nc\n")
    g6(R6, "commit", "-q", "-a", "-m", "main")
    g6(R6, "checkout", "-q", "feature")
    _rb = g6(R6, "rebase", "main")
    _rb_state = (os.path.isfile(gpath6("REBASE_HEAD")),
                 os.path.isdir(gpath6("rebase-merge")))
    put6(R6, "k", "a\nRESOLVED\nc\n")
    g6(R6, "add", "k")
    _rb_commit = fired6("commit", "--no-edit")
    g6(R6, "rebase", "--continue")
    g6(R6, "reset", "-q", "--hard", _feat)
    g6(R6, "rebase", "main")
    put6(R6, "k", "a\nRESOLVED\nc\n")
    g6(R6, "add", "k")
    _rb_cont = fired6("rebase", "--continue")
    _pd6 = os.path.join(T6, "patches")
    g6(R6, "format-patch", "-q", "-1", _feat, "-o", _pd6)
    g6(R6, "checkout", "-q", "-b", "am-branch", "main")
    _am = g6(R6, "am", "-3", *sorted(os.path.join(_pd6, f)
                                     for f in os.listdir(_pd6)))
    _am_state = (os.path.isfile(os.path.join(gpath6("rebase-apply"),
                                             "applying")),
                 os.path.isfile(gpath6("REBASE_HEAD")))
    put6(R6, "k", "a\nRESOLVED\nc\n")
    g6(R6, "add", "k")
    _am_commit = fired6("commit", "-m", "resolved during git am")
    g6(R6, "am", "--abort")
    check("MR2-3, CRIT2-4: a git commit made while a rebase or git am is "
          "stopped fires pre-commit; a conflicted rebase --continue fires "
          "none; git am leaves rebase-apply/applying and no REBASE_HEAD",
          _rb.returncode != 0 and _rb_state == (True, True)
          and _rb_commit == (0, ["pre-commit"]) and _rb_cont == (0, [])
          and _am.returncode != 0 and _am_state == (True, False)
          and _am_commit == (0, ["pre-commit"]),
          (_rb_state, _rb_commit, _rb_cont, _am_state, _am_commit))
    check("MR2-3: both substrates read rebase-merge/ and rebase-apply/, judge "
          "a rebase that names its commit as a stopped pick and name the "
          "rebase's and am's own abort",
          all(w in _sc_code and w in _mod
              for w in ("rebase-merge", "rebase-apply", "applying",
                        "REBASE_HEAD", "git rebase --abort",
                        "git am --abort")))
    check("MR2-3: the changelog's merge item, its 'does not do' list, Z-29's "
          "layer, the PRD :767 note and the seam's Coverage note say so, and "
          "the no-unstage sentence covers rebase and am",
          "A `git commit` made while a rebase or `git am` is stopped fires "
          "pre-commit too, though their own `--continue` fires no hook"
          in _MERGES and "(`REBASE_HEAD`) is judged as a stopped pick"
          in _MERGES
          # [WP3 fix4 RR3-CHK-1] A rebase's refusal names what can be
          # unstaged; the sentence keeps `git am` (5f).
          and "In a merge, a stopped pick, or a commit made while `git am` is "
          "stopped, the refusal never says to unstage a file" in flat(_MERGES)
          and "In a merge or a stopped pick the refusal never says" not in CL
          and "a `git commit` made while a rebase or `git am` is stopped does "
          "fire pre-commit" in _dont
          and "**Layer 2026-10-12 (WP3 fix round 3, re-review 2 MR2-3, "
          "MR2-5, CRIT2-4).**" in _rows["Z-29"]
          and "`git rebase --continue` then completed without it"
          in _rows["Z-29"]
          and "a commit made while a rebase is stopped" in _n767
          and "a commit made while a rebase or `git am` is stopped" in _COV3)

    g6(R6, "checkout", "-q", "main")
    put6(R6, "t1", "1\n")
    g6(R6, "add", "t1")
    g6(R6, "commit", "-q", "-m", "A")
    _ca = g6(R6, "rev-parse", "HEAD").stdout.strip()
    put6(R6, "t2", "2\n")
    g6(R6, "add", "t2")
    g6(R6, "commit", "-q", "-m", "B")
    _cb = g6(R6, "rev-parse", "HEAD").stdout.strip()
    _rv = g6(R6, "revert", "--no-commit", _ca, _cb)
    try:
        with open(gpath6("REVERT_HEAD")) as _fh:
            _rvh = _fh.read().strip()
    except OSError:
        _rvh = ""
    g6(R6, "revert", "--abort")
    check("MR2-5: a clean git revert --no-commit of two commits leaves "
          "REVERT_HEAD naming the last only; both substrates' text says 'or "
          "ran with --no-commit', and the changelog and Z-29 record the rest",
          _rv.returncode == 0 and _rvh == _cb != _ca
          and "a revert that stopped on conflicts or ran with --no-commit"
          in _SC and re.search(r'"a revert that stopped on conflicts or '
                               r'ran with "\s*"--no-commit"', _mod)
          and "`git revert --no-commit` leaves `REVERT_HEAD` even when it "
          "applied cleanly" in _MERGES
          and "`REVERT_HEAD` naming B only" in _rows["Z-29"], (_rv.stderr,))

    g6(R6, "checkout", "-q", "--orphan", "other")
    g6(R6, "rm", "-rfq", ".")
    put6(R6, "vendor.txt", "v\n")
    g6(R6, "add", "vendor.txt")
    g6(R6, "commit", "-q", "-m", "other")
    g6(R6, "checkout", "-q", "main")
    _mt0 = g6(R6, "merge-tree", "--write-tree", "--name-only", "HEAD",
              "other")
    _mt1 = g6(R6, "merge-tree", "--write-tree", "--name-only",
              "--allow-unrelated-histories", "HEAD", "other")
    check("MR2-1: merge-tree refuses unrelated histories unless told to "
          "allow them; both substrates tell it, and the changelog, the PRD "
          ":767 note and the seam's Coverage note record the merge rule for "
          "them",
          _mt0.returncode not in (0, 1) and _mt1.returncode == 0
          and "--allow-unrelated-histories" in _sc_code
          and '"--allow-unrelated-histories"' in _mod
          and "a merge of unrelated histories, such as an import, is judged "
          "the same way" in _MERGES
          and "A merge of unrelated histories is judged like any other merge"
          in _n767
          and "a merge of unrelated histories is judged the same way"
          in _COV3, (_mt0.returncode, _mt1.returncode))

    # EM-1, MR2-2. In block mode, a broken sed changes nothing (the check
    # runs none), a broken grep is a check that could not run, and a
    # backslash in TMPDIR still finds an edit made inside a merge.
    B6 = repo6("block")
    install6(B6, "block")
    put6(B6, ".claude/specs/demo/tasks/demo-T01.md", _TASK)
    g6(B6, "add", "-A")
    g6(B6, "commit", "-q", "-m", "harness and the task")
    put6(B6, "src/evil.py", "e\n")
    g6(B6, "add", "src/evil.py")
    _shim_sed = os.path.join(T6, "shim-sed")
    put6(_shim_sed, "sed", "#!/bin/sh\necho 'sed: error while loading shared "
         "libraries: libacl.so.1' >&2\nexit 127\n", 0o755)
    _shim_grep = os.path.join(T6, "shim-grep")
    put6(_shim_grep, "grep", "#!/bin/sh\nexit 2\n", 0o755)
    _sc6 = os.path.join(B6, templates.SPEC_CHECK_PATH)

    def check6(**env):
        return subprocess.run(["bash", _sc6, "--staged"], cwd=B6,
                              capture_output=True, text=True,
                              env=dict(E6, **env), timeout=120)

    _r_sed = check6(PATH=_shim_sed + os.pathsep + E6.get("PATH", ""))
    _r_grep = check6(PATH=_shim_grep + os.pathsep + E6.get("PATH", ""))
    g6(B6, "reset", "-q")
    g6(B6, "checkout", "-q", "-b", "side")
    put6(B6, "README.x", "side\n")
    g6(B6, "add", "README.x")
    g6(B6, "commit", "-q", "-m", "side")
    g6(B6, "checkout", "-q", "main")
    put6(B6, "README.m", "main\n")
    g6(B6, "add", "README.m")
    g6(B6, "commit", "-q", "-m", "main")
    _mg6 = g6(B6, "merge", "--no-commit", "--no-ff", "side")
    put6(B6, "src/evil.py", "e\n")
    g6(B6, "add", "src/evil.py")
    _bs = os.path.join(T6, "back\\slash")
    os.makedirs(_bs)
    _r_bs = check6(TMPDIR=_bs)
    g6(B6, "merge", "--abort")
    _sc_lines = _r_sed.stdout.rstrip("\n").split("\n")
    check("EM-1, MR2-2: with a broken sed the check still refuses the "
          "unlisted file, a broken grep makes it exit 3 with no end line, and "
          "a backslash in TMPDIR still finds the edit made inside a merge",
          _r_sed.returncode == 2 and _sc_lines[-2:] == [
              "src/evil.py", templates.SPEC_CHECK_END]
          and _r_grep.returncode == 3
          and templates.SPEC_CHECK_END not in _r_grep.stdout
          and _mg6.returncode == 0 and _r_bs.returncode == 2
          and "src/evil.py" in _r_bs.stdout.split("\n"),
          (_r_sed.returncode, _sc_lines[-2:], _r_grep.returncode,
           _r_bs.returncode, _r_bs.stdout[-200:]))
finally:
    shutil.rmtree(T6, ignore_errors=True)

# EM-1, CRIT2-1, MR2-2, CRIT2-2: the emitted check, and the records.
check("EM-1, CRIT2-1, MR2-2, CRIT2-2: the emitted check runs no sed, dies "
      "on a grep status other than 0 or 1 and on a failed write, compares "
      "awk's lists by ARGV, keeps its message out of TMPDIR, and reads the "
      "prefix with git's variables cleared",
      not any(re.search(r"\bsed\b", ln) for ln in code_lines(_SC))
      and 'die "grep could not search the task files' in _SC
      and _sc_code.count('|| die "cannot write') >= 4
      and "-v L=" not in _sc_code
      and _sc_code.count("FILENAME != ARGV[ARGC - 1]") == 2
      and '_m="$(_msg)"' in _SC and '>"$TMPD/msg"' not in _SC
      and "unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE" in _SC
      and "the check's full message was lost" in _SG)
_TPL_FLAT = " ".join(ln.lstrip("#").strip()
                     for ln in read("lib/templates.py").split("\n")
                     if ln.startswith("#"))
check("EM-1, CRIT2-1: the check's source comment no longer says every "
      "internal failure goes through die(), and names the busybox awk gap",
      "every internal failure that could change the verdict is routed "
      "through die()" in _TPL_FLAT
      and "so every internal failure is routed through die()"
      not in _TPL_FLAT and "busybox awk exits 0" in _TPL_FLAT)
check("EM-1, CRIT2-1, MR2-2, CRIT2-2: the changelog's item 1, its fallback "
      "and below-top items record them, and Z-53 files the busybox gap",
      "needs no jq, python3 or sed" in _ITEM1
      and "(re-review 2 EM-1)" in _ITEM1 and "(CRIT2-1)" in _ITEM1
      and "(MR2-2, the same defect as EM-2)" in _ITEM1
      and "(backlog Z-53)" in _ITEM1
      and "(re-review 2 CRIT2-1)" in _FALLB
      and "(re-review 2 CRIT2-2)" in _BELOW
      and "BusyBox 1.37" in _rows["Z-53"] and "`$TMPD/keep`" in _rows["Z-53"]
      and _rows["Z-53"].endswith("| `open` · T4 |"))

# MR2-4, MR2-6: the whole change's own reason on any git; no abort clause
# in a retrofit warn week.
_rsvc = assigned_literal("tests/test_retrofit.py", "SERVICE_RETROFIT_CFG")
_, _P_SVC = plan_for(_rsvc or "")
_SC_R = _P_SVC.get(templates.SPEC_CHECK_PATH, {}).get("body", "")
check("MR2-4: both substrates give the 'older than 2.40' reason only for "
      "an older git, and a picked merge or root commit its own; the "
      "changelog, Z-41's layer and the PRD :767 note say so",
      "*:old) _what='this git, older than 2.40" in _SC
      and "its commit is a merge or has no parent" in _SC
      and 'elif rule == "old":' in _mod
      and "its commit is a merge or has no parent" in _mod
      and "a picked or reverted merge commit (`-m`) or root commit is "
      "checked whole on any git" in _MERGES
      and "(MR2-4)" in _rows["Z-41"]
      and "a picked or reverted merge commit or root commit, are checked "
      "whole on any git" in _n767)
check("MR2-6: the retrofit check offers no abort in a warn week, and the "
      "changelog says so",
      bool(_SC_R) and '[ "${BOOTSTRAP_SPEC_MODE:-}" != warn ] && '
      '[ "$R_WARN_WEEK" != 1 ]' in _SC_R
      and "in a retrofit warn week (re-review 2 MR2-6)" in _MERGES)
check("CRIT2-3, CRIT2-5: Z-41's layer settles the Windows TMPDIR question "
      "and the 2.38 flag, and the changelog names EM-2 as MR2-2's defect",
      "The Windows question CRIT2-3 raised" in _rows["Z-41"]
      and "works on git 2.38.0" in _rows["Z-41"]
      and "the critic's corrections (CRIT2-3 to CRIT2-5)" in _rr2p)

# MBS-1 to MBS-4, MBS-6: merge-back's stop.
_top_traps = [ln.strip() for ln in _mb_code if ln.startswith("trap ")]
check("MBS-1: PIPE is ignored inside on_signal only (no top-level trap "
      "names it, so the gates do not inherit it)",
      any(ln.strip() == "trap '' INT TERM HUP PIPE" for ln in _mb_code)
      and _top_traps and not any("PIPE" in ln for ln in _top_traps),
      _top_traps)
check("MBS-2 to MBS-4, MBS-6: merge-back names the abort's way out, its "
      "header and note name when the merge stays in progress and what a "
      "SIGKILL leaves, and the CLEANUP line says may be left",
      'abort_ours || abort_failed "ERROR interrupted while the gates ran, '
      'and the merge could not be aborted"' in _MB
      and "when a Ctrl-C or a session's end interrupts the hooks git runs "
      "before it writes the merge commit (pre-commit, commit-msg;" in _mb_hdr
      and "it also leaves the running gate going" in _mb_hdr
      and "bootstrap-merge-back.out.* and .in.*" in _mb_hdr
      and "except after --continue, when a gate changed a file the merge "
      "brought in, or when stopped in the hooks git runs before it writes "
      "the merge commit (pre-commit, commit-msg)" in _MB
      and "so the worktree or the branch may be left" in _MB
      and "interrupted before the worktree and the branch were removed"
      not in _MB)
_z39c = after(_rows["Z-39"], "**Layer 2026-10-12 (WP3 fix round 3, "
                             "re-review 2 MBS-1 to MBS-4, MBS-6).**")
check("MBS-1 to MBS-6: changelog item 9 names each, Z-39's layer records "
      "(m), (n), (o) and (h), Z-45's layer and Z-51's layer say the note "
      "now names its exceptions, and the Tests paragraph names MBS-5",
      all(f"re-review 2 {i}" in _ITEM9
          for i in ("MBS-1", "MBS-2", "MBS-3", "MBS-4", "MBS-6"))
      and all(w in _z39c for w in ("(m) Fixed: the stop also ignores SIGPIPE",
                                   "(n) Fixed", "(o) Disclosed, not fixed",
                                   "(h) extended"))
      and "the note is unchanged\" and Z-51 (f)'s first half no longer hold"
      in _rows["Z-45"]
      and "(f)'s first half is fixed" in _rows["Z-51"]
      and "(re-review 2 MBS-5)" in _TESTS3, _z39c[:300])

# RR2-1, RR2-2, RR2-4: the harness and its records.
_skill_ln = [ln for ln in _HSRC.split("\n")
             if 'c.get("name") == "Skill"' in ln]
check("RR2-2: a Skill mark counts only outside a sidechain, and the window "
      "takes the latest mark by time; the changelog and Z-28's layer say so",
      len(_skill_ln) == 1 and 'not e.get("isSidechain")' in _skill_ln[0]
      and "before(m, at) and (last is None or before(last[0], m))" in _HSRC
      and "(re-review 2 RR2-2, CRIT2-5)" in _HARN
      and "RR2-2 is fixed" in _rows["Z-28"])
check("RR2-1, RR2-4: the harness logs no ref updates (the snapshot runs "
      "after the session), so the changelog, Z-28 (d) and the live README "
      "narrow the HF-4 claim to the harness's own landing; the README no "
      "longer ties the headless case to the wrappers",
      "reference-transaction" not in _HSRC
      and "(not when the session lands the branch itself, re-review 2 "
      "RR2-1)" in _HARN
      and "holds for the harness's own landing only" in _rows["Z-28"]
      and "`reference-transaction` hook" in _rows["Z-28"]
      and "*Narrowed 2026-10-12 (WP3 fix3, RR2-1):*" in _LRD
      and "run without `--settings '{\"ultracode\": false}'`" in _LRD
      and "started outside the loop wrappers runs with ultracode on"
      not in _LRD and "(RR2-4)" in _rows["Z-28"])

# Z-52 (subtree merges) and the seam's section 10 note.
check("Z-52: the subtree merge row says what was measured and is tiered",
      "`git subtree pull -P lib/vendor` was refused on "
      "`lib/vendor/core/new.py`" in _rows["Z-52"]
      and _rows["Z-52"].endswith("| `open` · T4 |"))
check("section 10: the seam's WP3 note records fix round 3, and the walk "
      "says fix rounds 1, 2 and 3 each re-walked it",
      "Fix round 3 (2026-10-12) extends them in place" in _s10
      # [WP3 fix4] Fix round 4 re-walked it too (5f). [WP3 fix5] And
      # fix round 5 (5g). [WP3 fix6] And fix round 6 (5h).
      and "Fix rounds 1 to 8 each re-walked the triggers" in flat(CL))

# --------------------------------------------------------------------------- #
# 5f. [WP3 fix4, i2-records] The records fix round 4 corrected (re-review 3,
#     wp3-rereview3-wf_19364a7b-fff+wf_d6aa9f2c-21d.json, 2026-10-13), and
#     every WP3 record brought into line with fix round 4's emitted text.
#     Each row first derives the fact from the emitted files, the installer
#     or a shell, then checks the records that state it.
# --------------------------------------------------------------------------- #
print("\n=== 5f. Fix round 4 records ===")
_rr3p = cut(CL, "**Re-review 3 and fix round 4 (2026-10-13).**",
            "**Seam — the §8.4 trigger walk.**")
_BL_LAYER4 = anchored_line(BL, "**Layer 2026-10-05, WP3 (branch "
                               "`feat/wp3-spec-workflow`).**")

# Re-review 3's findings, pinned as data (the record is outside the
# repository): the paragraph's counts are what the list adds up to. MB3-4
# is the lens's INFO grade of the critic's MINOR CRIT3-1.
_RR3_MINOR = ["RR3-CHK-1", "RR3-CHK-2", "MB3-1", "INST3-1", "INST3-2",
              "INST3-3", "CRIT3-1"]
_RR3_INFO = ["RR3-CHK-3", "RR3-CHK-4", "MB3-2", "MB3-3", "MB3-4", "MB3-5",
             "INST3-4", "INST3-5", "INST3-6", "REC3-1"]
_RR3_PASS = ["RR3-CHK-0", "REC3-0", "CRIT3-0"]
_lens3 = [i for i in _RR3_MINOR if not i.startswith("CRIT3-")]
check("re-review 3: the changelog's paragraph gives the counts the pinned "
      "finding list adds up to, cites the record with both runs, and the "
      "entry's header counts four fix rounds",
      f"no MAJOR, {len(_RR3_MINOR)} MINOR and "
      f"{len(_RR3_INFO) + len(_RR3_PASS)} INFO findings; {len(_RR3_PASS)} "
      f"of the INFO ones record what held" in _rr3p
      and f"each of the lenses' {len(_lens3)} MINOR findings" in _rr3p
      and "the critic's MINOR had no verifiers" in _rr3p
      and "wp3-rereview3-wf_19364a7b-fff+wf_d6aa9f2c-21d.json" in _rr3p
      and "re-run alone as `wf_d6aa9f2c-21d`" in _rr3p
      and "(new rows Z-54 to Z-56)" in _rr3p
      # [WP3 fix5] The header counts five now (5g). [WP3 fix6] Six (5h).
      and "the build of 2026-10-05 and seven review fix rounds" in CL
      and "(`wp3-rereview3-wf_19364a7b-fff+wf_d6aa9f2c-21d.json`, "
      "2026-10-13)" in _BL_LAYER4
      and "Z-54 to Z-56 are fix round 4's (2026-10-13)" in _BL_LAYER4,
      _rr3p[:400])
_named3 = set(re.findall(r"\b(?:RR3-CHK|MB3|INST3|REC3|CRIT3)-\d+",
                         " ".join((CL, _WP3_BL))))
_RR3_IDS = _RR3_MINOR + _RR3_INFO
check("every re-review 3 finding (20, less 3 pass records) is named in the "
      "changelog's WP3 entry or a WP3 backlog row",
      len(_RR3_IDS) == 17 and not [i for i in _RR3_IDS if i not in _named3],
      [i for i in _RR3_IDS if i not in _named3])

# RR3-CHK-1: the rebase refusal, on both substrates, and the records.
# [WP3 fix5 R4-3] The code's sentence names REBASE_HEAD and how to see its
# files, and says git has made it at an edit stop; a stop that names no
# commit lets any file be unstaged.
_rb_say = ("It replays the commit REBASE_HEAD names (git show --stat "
           "REBASE_HEAD lists its files). Until that commit is made (it is "
           "made if git rev-parse HEAD REBASE_HEAD prints one object name "
           "twice), do not unstage a file it changed: that drops ", "part of that commit",
           " Any other file can be unstaged (git restore --staged <path>), "
           "and so can any file once that commit is made.",
           " Any file here can be unstaged (git restore --staged <path>).")
# The SDK's text is adjacent string literals: join them.
_mod_src = re.sub(r'"\s*\n\s*"', "", _mod)
check("RR3-CHK-1: both substrates tell a stopped rebase what can be "
      "unstaged, keep the no-unstage sentence for git am, and no longer "
      "speak of a resolution where git names no commit; the changelog says "
      "so and its no-unstage sentence leaves the rebase out",
      all(w in _SC and w in _mod_src for w in _rb_say)
      and "Do not unstage a file from it: that drops $_drop." in _SC
      and "git names no commit it is replaying here, as at an exec or break "
      "stop, so this is all of the change" in _SC
      and "git names no commit it is replaying here, as at an exec or break "
      "stop, so this is all of the change" in _mod_src
      and "git names no commit it is replaying here, so the resolution"
      not in _SC + _mod_src
      # [WP3 fix5 R4-3] The edit, exec and break example is gone (5g).
      and "and since fix round 4 that any other file can be unstaged"
      in _MERGES
      and "(re-review 3 RR3-CHK-1)" in _MERGES
      and "or a commit made while a rebase or `git am` is stopped, the "
      "refusal never says" not in _MERGES)

# MB3-1: merge-back's list keeps 20 lines and counts the rest (run in a
# shell), and its way to drop the merge is `git checkout -- :/`.
_list_ln = [ln for ln in _MB.split("\n") if ln.startswith("list(){")]
_lr = subprocess.run(
    ["bash", "-c", (_list_ln[0] if _list_ln else "list(){ :; }")
     + '\nlist "$(seq 1 25)"'], capture_output=True, text=True, timeout=30)
_lo = _lr.stdout.split("\n")
_z39d = after(_rows["Z-39"], "**Layer 2026-10-13 (WP3 fix round 4, "
                             "re-review 3 MB3-1, CRIT3-1, MB3-4).**")
check("MB3-1: merge-back lists at most 20 files and then how many more, "
      "drops a merge with `git checkout -- :/`, and where a merge can hold "
      "unmerged entries with `git restore --ignore-unmerged` (fix round 5 "
      "R4-4); item 9, Z-39's and Z-51's layers say so",
      len(_list_ln) == 1 and _lo[:21] == [f"    {k}" for k in range(1, 21)]
      + ["    ... and 5 more"]
      and _MB.count("git checkout -- :/ (it discards every unstaged change, "
                    "the files above included), then git merge --abort") == 2
      and _MB.count("git checkout -- <the files above>") == 0
      and _MB.count("To drop the merge: git restore --ignore-unmerged "
                    "--worktree -- :/ (it discards every unstaged change, "
                    "the files above included), then git merge --abort") == 1
      and "a merge of $BR is already in progress here. To keep the changes "
      "above" in _MB
      and "list at most 20 files, then how many more" in _ITEM9
      and "(re-review 3 MB3-1)" in _ITEM9
      and "(n) extended:" in _z39d and "\"path is unmerged\"" in _z39d
      and "**Layer 2026-10-13 (WP3 fix round 4, re-review 3 MB3-1).** (g) in "
      "part" in _rows["Z-51"], (_lr.stdout[-200:], _lr.stderr[-200:]))

# CRIT3-1, MB3-4: narrowed, not fixed. No top-level trap names PIPE (the
# MBS-1 row above); the header and the note no longer promise a last line
# whatever the reader does, and the records say so.
check("CRIT3-1, MB3-4: merge-back's header and note say a reader that "
      "stops early (`| head`) leaves no last line, nothing says the last "
      "line is always merge-back's, and item 9, the README and Z-39 (p) "
      "record it as disclosed with the trap as the option",
      "The last line of output is `merge-back: <STATUS> ...`, unless the "
      "reader stops early" in _mb_hdr
      and "last line of output is always" not in _mb_hdr
      and "which is always" not in _MB
      and "Do not cut this output with head: a reader that stops early ends "
      "this run with no last line" in _MB
      and "Its last line, unless a reader that stops early ends it first "
      "(below), is `merge-back: <STATUS>`" in _ITEM9
      and "(re-review 3 CRIT3-1, MB3-4; backlog Z-39 (p))" in _ITEM9
      and "so do not cut its output with `head`: a reader that stops early "
      "ends the run with no last line" in _RDM
      and "(p) Disclosed, not fixed: a reader that stops early" in _z39d
      and "a top-level no-op `trap : PIPE` (not `trap '' PIPE`" in _z39d
      and "(p) is T4." in _z39d, _z39d[:300])

# INST3-2, INST3-3: the installer's texts, derived by calling it.
_mn4 = installer._mention_note([("pre-commit", ".husky/pre-commit")],
                               ".claude/githooks/dispatch",
                               ("pkg/", "confirm.txt"))
_off4 = installer._git_hook_warnings(
    {"git_hooks": [{"state": "gate-off-mention", "detail": "", "path": _p,
                    "name": "pre-commit"}
                   for _p in (".pre-commit-config.yaml", "lefthook.yml",
                              ".git/hooks/pre-commit")]},
    installer.Path(T6), False)
check("INST3-2, INST3-3: the confirm recipe names a file under the first "
      "prefix and says a file outside them prints nothing; gate-off says to "
      "remove a hook manager's whole entry; the changelog and README say so",
      "commit a file under pkg/ that no task file lists, such as "
      "`pkg/confirm.txt`" in _mn4
      and "A file outside hooks.spec_gate_commit_prefixes is not checked, "
      "so it prints nothing." in _mn4
      and len(_off4) == 3
      and "remove the whole hook entry that runs it from "
      ".pre-commit-config.yaml (each `- id:` item with that `entry:`, not "
      "only the line)." in _off4[0]
      and "remove the whole lefthook command that runs it from lefthook.yml "
      "(each command's name with its `run:` key, not only the line)."
      in _off4[1]
      and "remove that line from .git/hooks/pre-commit." in _off4[2]
      and "the whole hook entry or command that runs the line, not only "
      "the line" in _WHERE and "(re-review 3 INST3-2)" in _WHERE
      and "Since fix round 4 the commit it names is of a file under the "
      "first of `hooks.spec_gate_commit_prefixes`" in _WHERE
      and "(re-review 3 INST3-3)" in _WHERE
      and "commit a file under one of `hooks.spec_gate_commit_prefixes` "
      "that no task file lists from a terminal" in _RDM
      # [WP3 fix5 R4-2] The README adds the legacy allowlist (5g).
      and "(a file outside them, or one a retrofit install's legacy "
      "allowlist covers, is not checked, so it prints nothing;" in _RDM,
      _mn4[-500:])

# The new rows, each tiered; Z-56 names every INFO finding fix round 4 did
# not take, one letter each.
_z56_ids = ["RR3-CHK-3", "RR3-CHK-4", "MB3-2", "MB3-5", "INST3-4", "INST3-5",
            "INST3-6"]
# [WP3 fix5] Z-54 is done by fix round 5 (5g); Z-55 and Z-56 stay open.
check("Z-54 to Z-56: reftable, the shared hook files and the INFO findings "
      "fix round 4 did not take, Z-55 and Z-56 `open` · T4, and the "
      "changelog's Deferred paragraph names them",
      all(_rows[i].endswith("| `open` · T4 |") for i in ("Z-55", "Z-56"))
      and "(fix round 4; re-review 3 RR3-CHK-2)" in _rows["Z-54"]
      and "`git rev-parse -q --verify REBASE_HEAD`" in _rows["Z-54"]
      and "(fix round 4; re-review 3 INST3-1)" in _rows["Z-55"]
      and all(f"({c}) {i}:" in _rows["Z-56"]
              for c, i in zip("abcdefg", _z56_ids))
      and "reftable repositories (Z-54, done in fix round 5)" in _deferred
      and "fix round 4 did not take (Z-56)" in _deferred,
      [i for i in ("Z-55", "Z-56") if not _rows[i].endswith(
          "| `open` · T4 |")])

# The seam's section 10 note, the freeze table's re-measure and the Tests
# paragraph's date follow fix round 4.
# [WP3 fix5] The freeze table and the Tests counts are re-dated to fix
# round 5 (5g).
check("fix round 4: the seam's section 10 note records the section 3.2 (4) "
      "correction and no new line",
      "Fix round 4 (2026-10-13) corrects the §3.2 (4) note in place" in _s10
      and "it adds no `warning:` or `note` line" in _s10)

# --------------------------------------------------------------------------- #
# 5g. [WP3 fix5, j2-records] The records fix round 5 corrected (step 7,
#     wp3-step7-wf_f7600f06-a5c.json, 2026-10-13), and every WP3 record
#     brought into line with fix round 5's code. Each row first derives the
#     fact from the emitted files, the installer, git or CI's own files,
#     then checks the records that state it.
# --------------------------------------------------------------------------- #
print("\n=== 5g. Fix round 5 records ===")
_s7p = cut(CL, "**Step 7 and fix round 5 (2026-10-13).**",
           "**Seam — the §8.4 trigger walk.**")
_BL_LAYER5 = anchored_line(BL, "**Layer 2026-10-05, WP3 (branch "
                               "`feat/wp3-spec-workflow`).**")

# Step 7's findings, pinned as data (the record is outside the repository):
# each lens's list, the critic's, and how many things each said held. The
# paragraph's counts are what the lists add up to.
_S7_LENS = {"BODY-1": "MINOR", "BODY-2": "MINOR", "BODY-3": "MINOR",
            "BODY-4": "INFO", "BODY-5": "INFO",
            "R4-1": "MAJOR", "R4-2": "MINOR", "R4-3": "MINOR",
            "R4-4": "MINOR",
            "CI-1": "MINOR", "CI-2": "MINOR", "CI-3": "INFO", "CI-4": "INFO"}
_S7_CRIT = {"CRIT7-1": "MAJOR", "CRIT7-2": "INFO", "CRIT7-3": "INFO",
            "CRIT7-4": "INFO"}
_S7_HELD = (11, 11, 6, 4)
_s7all = dict(_S7_LENS, **_S7_CRIT)


def _n7(sev, d=_s7all):
    return sum(1 for v in d.values() if v == sev)


check("step 7: the changelog's paragraph gives the counts the pinned "
      "finding lists add up to, cites the record and fix round 5's run, "
      "and the header, the walk and the backlog layer count fix round 5",
      f"reported {_n7('MAJOR')} MAJOR, {_n7('MINOR')} MINOR and "
      f"{_n7('INFO')} INFO findings; the lenses and the critic also listed "
      f"{sum(_S7_HELD)} things that held" in _s7p
      and f"each of the lenses' {_n7('MAJOR', _S7_LENS) + _n7('MINOR', _S7_LENS)}"
      " MAJOR and MINOR findings" in _s7p
      and "the critic's MAJOR (CRIT7-1) had no verifiers" in _s7p
      and "`.claude/sessions/prd-minus-security/wp3-step7-wf_f7600f06-a5c.json`"
      in _s7p
      and "fix round 5 ran as `wf_a43c552f-e98`" in _s7p
      and "filed as Z-57 (new row)" in _s7p
      # [WP3 fix6] The header and the walk count fix round 6 too (5h).
      and "the build of 2026-10-05 and seven review fix rounds" in CL
      and "\"Step 7 and fix round 5\"," in CL
      and "Fix rounds 1 to 8 each re-walked the triggers" in CL
      and "(`wp3-step7-wf_f7600f06-a5c.json`, 2026-10-13)" in _BL_LAYER5
      and "Z-57 is fix round 5's (2026-10-13)" in _BL_LAYER5
      and "fix round 5 closed Z-54" in _BL_LAYER5, _s7p[:400])

# Every finding is named: a range "X-1 to X-5" names each member.
_s7txt = " ".join((CL, _WP3_BL, _rows["Z-57"]))
_named7 = set(re.findall(r"\b(?:BODY|R4|CI|CRIT7)-\d+", _s7txt))
for _m in re.finditer(r"\b(BODY|R4|CI|CRIT7)-(\d+) to \1-(\d+)", _s7txt):
    _named7 |= {f"{_m.group(1)}-{k}"
                for k in range(int(_m.group(2)), int(_m.group(3)) + 1)}
check("every step 7 finding (17) is named in the changelog's WP3 entry or a "
      "WP3 backlog row",
      len(_s7all) == 17 and not [i for i in _s7all if i not in _named7],
      [i for i in _s7all if i not in _named7])

# R4-1, CRIT7-1: both substrates read the three heads as refs, through a
# name that must resolve to itself; no head is read as a file any more.
# Git's own behaviour, where this git can make a reftable repository: a
# stopped cherry-pick there has the ref and no file at --git-path.
T7 = tempfile.mkdtemp(prefix="wp3-records-5g-")
E7 = dict(E5, HOME=T7, XDG_CONFIG_HOME=os.path.join(T7, ".config"),
          GIT_CEILING_DIRECTORIES=T7)
os.makedirs(os.path.join(T7, ".config", "git"))
with open(os.path.join(T7, ".config", "git", "config"), "w") as _fh:
    _fh.write("[init]\n\tdefaultBranch = main\n[commit]\n\tgpgsign = false\n"
              "[advice]\n\tdetachedHead = false\n")
_rt = os.path.join(T7, "rt")
os.makedirs(_rt)
_rt_ok = g5(_rt, "init", "-q", "--ref-format=reftable", env=E7).returncode == 0
_rt_fact = None
if _rt_ok:
    put(_rt, "f", "base\n")
    g5(_rt, "add", "f", env=E7)
    g5(_rt, "commit", "-qm", "base", env=E7)
    g5(_rt, "checkout", "-qb", "feat", env=E7)
    put(_rt, "f", "feat\n")
    g5(_rt, "commit", "-qam", "feat", env=E7)
    g5(_rt, "checkout", "-q", "main", env=E7)
    put(_rt, "f", "main\n")
    g5(_rt, "commit", "-qam", "main", env=E7)
    _cp = g5(_rt, "cherry-pick", "feat", env=E7)
    _gp = g5(_rt, "rev-parse", "--git-path", "CHERRY_PICK_HEAD",
             env=E7).stdout.strip()
    _rt_fact = (_cp.returncode != 0
                and g5(_rt, "rev-parse", "-q", "--verify", "CHERRY_PICK_HEAD",
                       env=E7).returncode == 0
                and not os.path.isfile(os.path.join(_rt, _gp)))
else:
    print("  SKIP  the reftable half of the next row: this git cannot init "
          "--ref-format=reftable (git 2.45 or later)")
shutil.rmtree(T7, ignore_errors=True)
_seq_sh = [ln for ln in code_lines(_SC) if "rev-parse" in ln
           and ("--git-path \"${_s#*:}\"" in ln or "--git-path REBASE_HEAD"
                in ln)]
check("R4-1, CRIT7-1: spec-check.sh and the SDK read REBASE_HEAD, "
      "CHERRY_PICK_HEAD and REVERT_HEAD as refs, never by name lookup "
      "(a reftable repository keeps them with no file); item 1, the "
      "Deferred paragraph and Z-54's done layer say so",
      _rt_fact is not False
      # [WP3 fix6 RV5-SC-1] The file itself, else (reftable) the exact ref.
      and "SEQREF=\"$(git rev-parse -q --verify \"$l^{commit}\" 2>/dev/null)\""
      in _SC and "l=\"$(git show-ref --verify \"$1\" 2>/dev/null)\"" in _SC
      and not [ln for ln in code_lines(_SC) if "--symbolic-full-name" in ln]
      and "_seqref REBASE_HEAD && PICK=\"$SEQREF\"" in _SC
      and not _seq_sh
      and "await seq_ref(\"REBASE_HEAD\")" in _mod
      and "\"show-ref\", \"--verify\", name)" in _mod
      and "--symbolic-full-name" not in _mod
      and "git_path(\"REBASE_HEAD\")" not in _mod
      and "Since fix round 5 the check reads `REBASE_HEAD`, "
      "`CHERRY_PICK_HEAD` and `REVERT_HEAD` as refs" in _MERGES
      and "(step 7 R4-1, CRIT7-1; re-review 3 RR3-CHK-2; backlog Z-54)"
      in _MERGES
      and "`MERGE_HEAD` stays a file on reftable" in _MERGES
      and "reftable repositories (Z-54, done in fix round 5)" in _deferred
      and "| `done` (was `open` · T4) — **done by WP3 fix round 5, layer "
      "2026-10-13 (step 7 R4-1, CRIT7-1):**" in _rows["Z-54"]
      and "The check fails closed" not in _rows["Z-54"]
      and "`_seqref`" in _rows["Z-54"] and "`seq_ref`" in _rows["Z-54"],
      (_rt_fact, _seq_sh))

# R4-3: the rebase sentence (pinned with RR3-CHK-1 above) names the commit
# and how to list its files; item 1 says so.
check("R4-3: both substrates name REBASE_HEAD and `git show --stat "
      "REBASE_HEAD`, and say any file can be unstaged at a stop that names "
      "no commit; item 1 says so",
      all(w in _SC and w in _mod_src for w in _rb_say)
      and "If it replays a commit" not in _SC + _mod_src
      and "such as one added at an edit, exec or break stop" not in
      _SC + _mod_src
      and "names that commit and how to list its files (`git show --stat "
      "REBASE_HEAD`)" in _MERGES
      and "at an exec or break stop, which names no commit, says that any "
      "file can be unstaged (step 7 R4-3)" in _MERGES)

# R4-4: merge-back's "already in progress" way to drop the merge, as the
# script prints it, is the command item 9 and Z-39's layer give.
_inp = re.search(r"To drop the merge: (git restore [^\"]+?), then git merge "
                 r"--abort\"", _MB)
_inp_cmd = _inp.group(1).split(" (")[0] if _inp else "<none>"
_z39e = after(_rows["Z-39"], "**Layer 2026-10-13 (WP3 fix round 5, step 7 "
                             "R4-4).**")
check("R4-4: merge-back's in-progress remedy is `git restore "
      "--ignore-unmerged --worktree -- :/`, its list no longer claims git "
      "refuses the abort, and item 9, Z-39's and Z-51's layers give the "
      "same command",
      _inp_cmd == "git restore --ignore-unmerged --worktree -- :/"
      and "say \"Unstaged changes in the merge in progress:\"" in _MB
      and "in the merge in progress (git merge --abort refuses" not in _MB
      and "<the files above>" not in _MB
      and f"`{_inp_cmd}` (it discards every unstaged change, the listed "
      "files included), then `git merge --abort`" in _ITEM9
      and "(step 7 R4-4; `git restore` needs git 2.23" in _ITEM9
      and f"is now `{_inp_cmd}` (it discards every unstaged change, the "
      "files above included), then `git merge --abort`" in _z39e
      and "An unmerged path is still listed twice (Z-57 (c))." in _z39e
      and f"**Layer 2026-10-13 (WP3 fix round 5, step 7 R4-4).** (g) in part "
      f"again: the \"already in progress\" way to drop a merge is now "
      f"`{_inp_cmd}`" in _rows["Z-51"], _inp_cmd)

# R4-2: the installer's confirm recipe in a retrofit install, derived by
# calling it with a legacy allowlist that covers the first prefix, then
# every prefix; the warn week's line is the check's own.
_ra = installer._git_hook_warnings(
    {"git_hooks": [{"state": "foreign", "path": ".git/hooks/pre-commit",
                    "name": "pre-commit", "via": ".git/hooks/pre-commit",
                    "mentions": True, "detail": ""}]},
    installer.Path(ROOT), False, None, ["src/**"])
_rall = installer._git_hook_warnings(
    {"git_hooks": [{"state": "foreign", "path": ".git/hooks/pre-commit",
                    "name": "pre-commit", "via": ".git/hooks/pre-commit",
                    "mentions": True, "detail": ""}]},
    installer.Path(ROOT), False, None,
    [p + "**" for p in templates.SPEC_GATE_DEFAULT_PREFIXES])
_ra_t, _rall_t = " ".join(_ra), " ".join(_rall)
_wk = "the spec check would refuse this commit:"
check("R4-2: in a retrofit install the recipe names a prefix the legacy "
      "allowlist leaves checked and the warn week's own line, and says no "
      "commit can confirm the line when the allowlist covers every prefix; "
      "the changelog and README say so",
      f"commit a file under {templates.SPEC_GATE_DEFAULT_PREFIXES[1]} that "
      f"no task file lists" in _ra_t
      and f"prints `{_wk}` instead" in _ra_t
      and _wk in read("lib/templates.py")
      and "nor is one the legacy allowlist covers." in _ra_t
      and "No commit can confirm the pre-commit line yet" in _rall_t
      and "confirm.txt" not in _rall_t
      and "under the first prefix the legacy allowlist leaves checked"
      in _WHERE
      and f"(`{_wk}`)" in _WHERE and "(step 7 R4-2)" in _WHERE
      and "or says that no commit can confirm the line yet)" in _RDM,
      (_ra_t[-600:], _rall_t[-300:]))

# CI-1, CI-2: CI's own files. run-tests marks a suite skipped only by a
# `SUITE SKIPPED:` line, and test_spec_check's full-TMPDIR gate prints a
# plain SKIP line; the job's timeout is the workflow's. [2026-10-14] The
# timeout went from 15 to 30 minutes (Z-57 (a) done layer); the 696 s
# measurement keeps the 15-minute limit it was taken against.
_rt_src = read("bin/run-tests")
_sc_src = read("tests/test_spec_check.py")
_wf = re.search(r"^\s*timeout-minutes:\s*(\d+)\s*$",
                read(".github/workflows/ic-self-check.yml"), re.M)
_tmo = int(_wf.group(1)) * 60 if _wf else 0
_n_sc = re.search(r"`tests/test_spec_check\.py` \((\d+)\)", _TESTS3)
_n_sc = int(_n_sc.group(1)) if _n_sc else -1
check("CI-1, CI-2: run-tests counts only `SUITE SKIPPED:`, the full-TMPDIR "
      "gate prints a plain SKIP line, and the Tests paragraph and Z-57 say "
      "what CI skips, how much of the 15-minute timeout the suites took, "
      "and that the timeout is now 30 minutes",
      'SKIPPED_RE = re.compile(r"^SUITE SKIPPED:\\s*(.+)$", re.M)' in _rt_src
      and "print(\"  SKIP  the full-TMPDIR rows: `unshare --user "
      "--map-root-user \"" in _sc_src
      and f"of its 435 checks at `c1dfa5d` (run 38300475211)" in _TESTS3
      and f"it runs {_n_sc - 9} of {_n_sc} when `unshare` fails the same "
      "way (measured here, not on CI)" in _TESTS3
      and "(step 7 CI-1; backlog Z-57)" in _TESTS3
      and _tmo == 1800
      and "took 696 s of the job's `timeout-minutes: 15` "
      "(900 s), leaving 204 s (run 38300475211)" in _rows["Z-57"]
      and f"**[Layer 2026-10-14, (a) done.]** `timeout-minutes` is now "
      f"{_tmo // 60} ({_tmo:,} s)" in _rows["Z-57"]
      and "(b) CI-1:" in _rows["Z-57"]
      and _rows["Z-57"].endswith("| `open` · T4 |"), (_tmo, _n_sc))

# CI-4: test_git_hooks removes what it made.
_gh_src = read("tests/test_git_hooks.py")
check("CI-4: test_git_hooks registers an atexit cleanup, and the step 7 "
      "paragraph and Z-57 (e) say so",
      "import atexit" in _gh_src and "atexit.register(" in _gh_src
      and "left 58 directories in `TMPDIR` after each run and now leaves "
      "none (CI-4)" in _s7p
      and "(e) `tests/test_git_hooks.py`'s cleanup (CI-4)" in _rows["Z-57"])

# The seam's section 10 note: no note quotes a text fix round 5 changed.
check("fix round 5: the seam's section 10 note says it changes no note and "
      "adds no line, and no seam note quotes the texts it changed; the "
      "freeze table and the Tests counts are dated after it",
      "Fix round 5 (2026-10-13) changes no note" in _s10
      and "it adds no `warning:` or `note` line, flag or field" in _s10
      and not [w for w in ("REBASE_HEAD", "CHERRY_PICK_HEAD", "unstage",
                           "ignore-unmerged", "already in progress", _wk,
                           "confirm.txt") if w in SEAM]
      # [WP3 fix6] Re-measured and re-run after fix round 6 (5h). [WP3 fix7]
      # And after fix round 7 (5i). [WP3 fix 8] The counts after fix round 8,
      # which moves only gates.py, a body the table already counts.
      and "(re-measured on the fix round 7 tree; fix round 8 moves only "
      "`gates.py`, which the table already counts)" in flat(CL)
      and "run alone on 2026-10-13, after fix round 8" in _TESTS3
      and "re-run on the fix round 7 tree as a user that is not root"
      in _TESTS3)

# --------------------------------------------------------------------------- #
# 5h. [WP3 fix6, k2-records] The records fix round 6 corrected (the review of
#     fix round 5, wp3-fix5-wf_a43c552f-e98.json, 2026-10-13), and every WP3
#     record brought into line with fix round 6's code. Each row first
#     derives the fact from the emitted files, the installer or git, then
#     checks the records that state it.
# --------------------------------------------------------------------------- #
print("\n=== 5h. Fix round 6 records ===")
_r5p = cut(CL, "**Review of fix round 5 and fix round 6 (2026-10-13).**",
           "**Seam — the §8.4 trigger walk.**")

# The review's findings, pinned as data (the record is outside the
# repository): each lens's list, the critic's, and how many things each
# said held. No verifier ran in this review. CRIT5-2 grades RV5-MB-1 INFO;
# the counts are the lenses' own grades.
_R5_LENS = {"RV5-SC-1": "MINOR", "RV5-SC-2": "MINOR", "RV5-SC-3": "INFO",
            "RV5-MB-1": "MINOR", "RV5-MB-2": "MINOR", "RV5-MB-3": "INFO"}
_R5_CRIT = {"CRIT5-1": "INFO", "CRIT5-2": "INFO"}
_R5_HELD = (9, 8, 7)
_r5all = dict(_R5_LENS, **_R5_CRIT)


def _n5(sev, d=_r5all):
    return sum(1 for v in d.values() if v == sev)


check("review of fix round 5: the changelog's paragraph gives the counts the "
      "pinned finding lists add up to, cites the record and fix round 6's "
      "run, and the header, the walk and the backlog layer count fix round 6",
      _n5("MAJOR") == 0
      and f"reported no MAJOR, {_n5('MINOR')} MINOR and {_n5('INFO')} INFO "
      f"findings; the lenses and the critic also listed {sum(_R5_HELD)} "
      "things that held" in _r5p
      and "two lenses and a critic" in _r5p
      and "No verifier ran in this review" in _r5p
      and "the critic graded one lens MINOR (RV5-MB-1) INFO (CRIT5-2)" in _r5p
      and "`.claude/sessions/prd-minus-security/wp3-fix5-wf_a43c552f-e98.json`"
      in _r5p
      and "fix round 6 ran as `wf_6f9f8c5a-b8d`" in _r5p
      and "(new items (f) to (j))" in _r5p
      and "the build of 2026-10-05 and seven review fix rounds" in CL
      and "and four of 2026-10-13" in CL
      and "\"Review of fix round 5 and fix round 6\" and" in CL
      and "Fix rounds 1 to 8 each re-walked the triggers" in CL
      and "(`wp3-fix5-wf_a43c552f-e98.json`, 2026-10-13), added items (f) to "
      "(j) to Z-57, corrected Z-54's done layer in place, and appended a "
      "dated layer to Z-39" in _BL_LAYER5
      and "and the review of fix round 5 and its fix round 6," in _BL_LAYER5,
      _r5p[:400])

_r5txt = " ".join((CL, _WP3_BL))
_named5 = set(re.findall(r"\b(?:RV5-SC|RV5-MB|CRIT5)-\d+", _r5txt))
check("every finding of the review of fix round 5 (8) is named in the "
      "changelog's WP3 entry or a WP3 backlog row",
      len(_r5all) == 8 and not [i for i in _r5all if i not in _named5],
      [i for i in _r5all if i not in _named5])

# RV5-SC-1: git's own behaviour on the files backend. With a branch called
# CHERRY_PICK_HEAD beside a real cherry-pick stop, fix round 5's guard
# (--symbolic-full-name must print the name) misses the stop, and the
# emitted _seqref, run as spec-check.sh carries it, finds the picked commit.
T8 = tempfile.mkdtemp(prefix="wp3-records-5h-")
E8 = dict(E5, HOME=T8, XDG_CONFIG_HOME=os.path.join(T8, ".config"),
          GIT_CEILING_DIRECTORIES=T8)
os.makedirs(os.path.join(T8, ".config", "git"))
with open(os.path.join(T8, ".config", "git", "config"), "w") as _fh:
    _fh.write("[init]\n\tdefaultBranch = main\n[commit]\n\tgpgsign = false\n"
              "[advice]\n\tdetachedHead = false\n")


def _stop8(d, fmt=None, op="cherry-pick"):
    os.makedirs(d)
    _i = ["init", "-q"] + ([f"--ref-format={fmt}"] if fmt else [])
    if g5(d, *_i, env=E8).returncode != 0:
        return False
    put(d, "f", "base\n")
    g5(d, "add", "f", env=E8)
    g5(d, "commit", "-qm", "base", env=E8)
    g5(d, "checkout", "-qb", "feat", env=E8)
    put(d, "f", "feat\n")
    g5(d, "commit", "-qam", "feat", env=E8)
    g5(d, "checkout", "-q", "main", env=E8)
    put(d, "f", "main\n")
    g5(d, "commit", "-qam", "main", env=E8)
    if op == "revert":
        put(d, "f", "main2\n")
        g5(d, "commit", "-qam", "main2", env=E8)
        return g5(d, "revert", "--no-edit", "HEAD~1", env=E8).returncode != 0
    return g5(d, "cherry-pick", "feat", env=E8).returncode != 0


_sq = re.search(r"^_seqref\(\)\{\n.*?^\}\n", _SC, re.M | re.S)
_cpd = os.path.join(T8, "cp")
_sc1_fact = None
if _stop8(_cpd) and _sq:
    g5(_cpd, "branch", "CHERRY_PICK_HEAD", "main", env=E8)
    _feat = g5(_cpd, "rev-parse", "feat", env=E8).stdout.strip()
    _sym = g5(_cpd, "rev-parse", "-q", "--verify", "--symbolic-full-name",
              "CHERRY_PICK_HEAD", env=E8).stdout.strip()
    _gp = g5(_cpd, "rev-parse", "--git-path", "CHERRY_PICK_HEAD",
             env=E8).stdout.strip()
    _run = subprocess.run(
        ["bash", "-c", _sq.group(0) + "_seqref CHERRY_PICK_HEAD && "
         "printf '%s' \"$SEQREF\""], cwd=_cpd, capture_output=True,
        text=True, env=E8, timeout=60)
    _sc1_fact = (_sym != "CHERRY_PICK_HEAD"
                 and os.path.isfile(os.path.join(_cpd, _gp))
                 and _run.returncode == 0 and _run.stdout == _feat)
check("RV5-SC-1: beside a branch called CHERRY_PICK_HEAD, fix round 5's "
      "guard misses a real stop and the emitted _seqref finds it; item 1 and "
      "Z-54's done layer describe the reading that never looks the name up",
      _sc1_fact is True
      and "Since fix round 6 the check never looks the name up: a file at "
      "`--git-path` is read itself" in _MERGES
      and "(`git show-ref --verify`)" in _MERGES
      and "(review of fix round 5, RV5-SC-1)" in _MERGES
      and "only a name that resolves to itself" not in _MERGES
      and "so a branch called `REBASE_HEAD` is not one" not in CL
      and "as fix round 6 corrected it in place (review of fix round 5, "
      "RV5-SC-1)" in _rows["Z-54"]
      and "never look the name up" in _rows["Z-54"]
      and "`git show-ref --verify <name>`" in _rows["Z-54"]
      and "`git rev-parse --show-ref-format` prints `reftable`"
      in _rows["Z-54"]
      and "and take a name only when" not in _rows["Z-54"]
      and "a file with CRLF line endings, which git accepts, reads as no "
      "stop (Z-57 (i))" in _rows["Z-54"]
      # The rows the done layer names are in test_spec_check.
      and "(RV5-SC-1)\"" in read("tests/test_spec_check.py")
      and "Since fix round 6 it also has rows for a branch, a tag or both "
      "named for the head" in _rows["Z-54"], _sc1_fact)

# RV5-SC-2: the rebase text's check for a made commit, as both substrates
# print it, is the command item 1 gives; the edit-stop claim is gone.
_made = re.search(r"\(it is made if (git rev-parse HEAD REBASE_HEAD) prints "
                  r"one object name twice\)", _SC)
_made_cmd = _made.group(1) if _made else "<none>"
check("RV5-SC-2: both substrates say the commit is made when `git rev-parse "
      "HEAD REBASE_HEAD` prints one object name twice, and item 1 gives the "
      "same command and drops the edit-stop claim",
      _made is not None
      and f"(it is made if {_made_cmd} prints one object name twice)"
      in _mod_src
      and "at an edit stop git has made it" not in _SC + _mod_src
      and f"(`{_made_cmd}` prints one object name twice)" in _MERGES
      and "(review of fix round 5, RV5-SC-2)" in _MERGES
      and "(at an edit stop git has made it already)" not in CL, _made_cmd)

# RV5-MB-2, RV5-MB-3: the installer's confirm recipe, derived by calling it.
# `*.txt` covers the first probe name under every prefix, not the prefix;
# an allowlist that covers every probe name but no prefix gets the recipe
# that names no file. The allowlist is read as the check's awk reads it.
_hk8 = {"git_hooks": [{"state": "foreign", "path": ".git/hooks/pre-commit",
                       "name": "pre-commit", "via": ".git/hooks/pre-commit",
                       "mentions": True, "detail": ""}]}
_txt8 = " ".join(installer._git_hook_warnings(
    _hk8, installer.Path(ROOT), False, None, ["*.txt"]))
_nm8 = list(installer._CONFIRM_NAMES)
_any8 = " ".join(installer._git_hook_warnings(
    _hk8, installer.Path(ROOT), False, None,
    ["*/" + _nm8[0].split(".")[0] + "*"] + ["*/" + n for n in _nm8
                                           if "." not in n
                                           and not n.startswith("confirm")]))
_la8 = os.path.join(T8, "la")
put(_la8, ".claude/steering/spec-strategy.md",
    "x\n<!-- LEGACY_ALLOWLIST_BEGIN --> \n  src/**\t\n")
_la8_got = installer._legacy_allowlist(installer.Path(_la8), {})
_p0 = templates.SPEC_GATE_DEFAULT_PREFIXES[0]
check("RV5-MB-2, RV5-MB-3: with `*.txt` the recipe names a file the check "
      "still covers, an allowlist that covers every probe name but no prefix "
      "names none, the allowlist markers are read as the awk reads them, and "
      "the changelog and README say so",
      f"such as `{_p0}{_nm8[1]}`" in _txt8
      and "No commit can confirm the pre-commit line yet" not in _txt8
      and "(it covers every name this installer tried)" in _any8
      and "No commit can confirm the pre-commit line yet" not in _any8
      and "such as `" not in _any8.split("To confirm the pre-commit line")[-1]
      .split("A file outside")[0]
      and _la8_got == ["src/**"]
      and "tries " + ", ".join(f"`{n}`" for n in _nm8[:-1])
      + f" and `{_nm8[-1]}`" in _WHERE
      and "(review of fix round 5, RV5-MB-2)" in _WHERE
      and "anywhere on their line and to the end of the file when the end "
      "marker is missing" in _WHERE and "(RV5-MB-3)" in _WHERE
      and "asks for one when the allowlist covers every file name it tries"
      in _RDM, (_txt8[-500:], _any8[-500:], _la8_got))

# CRIT5-1: merge-back's in-progress check asks a reftable repository for the
# two heads; git keeps a stopped revert's REVERT_HEAD there with no file.
_rvd = os.path.join(T8, "rv")
_c51_fact = None
if _stop8(_rvd, fmt="reftable", op="revert"):
    _gp = g5(_rvd, "rev-parse", "--git-path", "REVERT_HEAD",
             env=E8).stdout.strip()
    _c51_fact = (g5(_rvd, "show-ref", "--verify", "REVERT_HEAD",
                    env=E8).returncode == 0
                 and not os.path.exists(os.path.join(_rvd, _gp)))
else:
    print("  SKIP  the reftable half of the next row: this git cannot init "
          "--ref-format=reftable (git 2.45 or later)")
_mbl = "\n".join(code_lines(_MB))
check("CRIT5-1: merge-back asks a reftable repository for CHERRY_PICK_HEAD "
      "and REVERT_HEAD with show-ref --verify, a file still refuses, and "
      "item 9, Z-39's layer and Z-57 (h) say so",
      _c51_fact is not False
      and "for _op in CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply "
      "BISECT_LOG; do" in _mbl
      and "[ -e \"$(git rev-parse --git-path \"$_op\")\" ] && _f=1" in _mbl
      and "[ \"$(git rev-parse --show-ref-format 2>/dev/null)\" = reftable ]"
      in _mbl
      and "git show-ref --verify \"$_op\" >/dev/null 2>&1 && _f=1" in _mbl
      and "since fix round 6, refuse (NOT-STARTED) while a cherry-pick or "
      "revert is stopped in a reftable repository" in _ITEM9
      and "(review of fix round 5, CRIT5-1; backlog Z-39 (q))" in _ITEM9
      and "**Layer 2026-10-13 (WP3 fix round 6, review of fix round 5 "
      "CRIT5-1).** (q) Fixed:" in _rows["Z-39"]
      and "asks `git show-ref --verify` for the head" in _rows["Z-39"]
      # [WP3 fix7 RV6-1, CRIT6-2] (h) names a cherry-pick too (5i).
      and "(h) Once a `git cherry-pick` or `git revert` of several commits "
      "stops on a conflict" in _rows["Z-57"], _c51_fact)
shutil.rmtree(T8, ignore_errors=True)

# RV5-SC-3, RV5-MB-1 and CRIT5-2, and what fix round 6 found, are filed in
# Z-57; the remedy item 9 gives is the one Z-57 (g) says loses the change.
_z57g = _rows["Z-57"].split("(g) ", 1)[-1].split(" (h) ", 1)[0]
check("Z-57 (f) to (j): the review's deferred findings and fix round 6's "
      "residuals are filed, the row stays open, and item 9 and the Deferred "
      "paragraph point at it",
      all(f"({k}) " in _rows["Z-57"] for k in "fghij")
      and "(f) RV5-SC-3:" in _rows["Z-57"]
      and "(g) RV5-MB-1, CRIT5-2:" in _rows["Z-57"]
      and f"`{_inp_cmd}` then `git merge --abort`" in _z57g
      and "and what fix rounds 5 to 8 left." in _rows["Z-57"]
      and "Added by fix round 6 (2026-10-13), from the review of fix round "
      "5:" in _rows["Z-57"]
      and _rows["Z-57"].endswith("| `open` · T4 |")
      and "(review of fix round 5, RV5-MB-1, CRIT5-2; backlog Z-57 (g))"
      in _ITEM9
      and "the rows CI skips and what fix rounds 5 to 8 left (Z-57)"
      in _deferred)

# The seam's section 10 note: no note quotes a text fix round 6 changed.
check("fix round 6: the seam's section 10 note says it changes no note and "
      "adds no line, and no seam note quotes the texts it changed",
      "Fix round 6 (2026-10-13) changes no note either" in _s10
      and "it adds no `warning:` or `note` line, flag or field." in _s10
      and not [w for w in ("show-ref", _made_cmd, "spec-check-probe",
                           "confirm.py", "every name this installer tried")
               if w in SEAM])

# --------------------------------------------------------------------------- #
# 5i. [WP3 fix7, l1] The records fix round 7 corrected (the review of fix
#     round 6, wp3-fix6-wf_6f9f8c5a-b8d.json, 2026-10-13), and every WP3
#     record brought into line with fix round 7's code. Each row first
#     derives the fact from the emitted files, the installer or git, then
#     checks the records that state it.
# --------------------------------------------------------------------------- #
print("\n=== 5i. Fix round 7 records ===")
_r6p = cut(CL, "**Review of fix round 6 and fix round 7 (2026-10-13).**",
           "**Seam — the §8.4 trigger walk.**")

# The review's findings, pinned as data (the record is outside the
# repository): the lens's list, the critic's, and how many things each said
# held. No verifier ran. CRIT6-2 reproduces RV6-1 at the same grade.
_R6_LENS = {"RV6-1": "MINOR", "RV6-2": "INFO", "RV6-3": "INFO"}
_R6_CRIT = {"CRIT6-1": "MINOR", "CRIT6-2": "MINOR"}
_R6_HELD = (10, 5)
_r6all = dict(_R6_LENS, **_R6_CRIT)


def _n6(sev, d=_r6all):
    return sum(1 for v in d.values() if v == sev)


check("review of fix round 6: the changelog's paragraph gives the counts the "
      "pinned finding lists add up to, cites the record and fix round 7's "
      "run, and the header, the walk and the backlog layer count fix round 7",
      _n6("MAJOR") == 0
      and f"reported no MAJOR, {_n6('MINOR')} MINOR and {_n6('INFO')} INFO "
      f"findings; the lens and the critic also listed {sum(_R6_HELD)} "
      "things that held" in _r6p
      and "a lens and a critic" in _r6p
      and "No verifier ran" in _r6p
      and "the critic reproduced the lens's RV6-1 and kept it MINOR "
      "(CRIT6-2)" in _r6p
      and "`.claude/sessions/prd-minus-security/wp3-fix6-wf_6f9f8c5a-b8d.json`"
      in _r6p
      and "fix round 7 ran as `wf_e5d3e1f5-29a`" in _r6p
      # The first run died on a network error; a restart finished it.
      and "died on a network error mid-step" in _r6p
      and "was finished by a restart, `wf_e16cfc37-d01`" in _r6p
      and "are filed as Z-57 (k) and (l)" in _r6p
      and "the build of 2026-10-05 and seven review fix rounds" in CL
      and "and four of 2026-10-13" in CL
      and "\"Review of fix round 6 and fix round 7\" below" in CL
      and "Fix rounds 1 to 8 each re-walked the triggers" in CL
      and "(`wp3-fix6-wf_6f9f8c5a-b8d.json`, 2026-10-13), added items (k) "
      "and (l) to Z-57, widened (h), and appended dated layers to Z-39 and "
      "Z-54" in _BL_LAYER5
      and "and the review of fix round 6 and its fix round 7." in _BL_LAYER5,
      _r6p[:400])

_r6txt = " ".join((CL, _WP3_BL))
_named6 = set(re.findall(r"\b(?:RV6|CRIT6)-\d+", _r6txt))
check("every finding of the review of fix round 6 (5) is named in the "
      "changelog's WP3 entry or a WP3 backlog row",
      len(_r6all) == 5 and not [i for i in _r6all if i not in _named6],
      [i for i in _r6all if i not in _named6])

T9 = tempfile.mkdtemp(prefix="wp3-records-5i-")
E9 = dict(E5, HOME=T9, XDG_CONFIG_HOME=os.path.join(T9, ".config"),
          GIT_CEILING_DIRECTORIES=T9)
os.makedirs(os.path.join(T9, ".config", "git"))
with open(os.path.join(T9, ".config", "git", "config"), "w") as _fh:
    _fh.write("[init]\n\tdefaultBranch = main\n[commit]\n\tgpgsign = false\n"
              "[advice]\n\tdetachedHead = false\n")


def _stray9(d, fmt):
    """A repository with a commit on a side branch, and a stray
    CHERRY_PICK_HEAD file naming it: no cherry-pick was run."""
    os.makedirs(d)
    if g5(d, "init", "-q", f"--ref-format={fmt}", env=E9).returncode != 0:
        return None
    put(d, "f", "base\n")
    g5(d, "add", "f", env=E9)
    g5(d, "commit", "-qm", "base", env=E9)
    g5(d, "checkout", "-qb", "feat", env=E9)
    put(d, "g", "feat\n")
    g5(d, "add", "g", env=E9)
    g5(d, "commit", "-qm", "feat", env=E9)
    g5(d, "checkout", "-q", "main", env=E9)
    feat = g5(d, "rev-parse", "feat", env=E9).stdout.strip()
    put(d, ".git/CHERRY_PICK_HEAD", feat + "\n")
    return feat


# CRIT6-1: the emitted _seqref, run as spec-check.sh carries it, reads by
# the ref backend: on reftable git ignores a stray head file (show-ref finds
# no head), and so does _seqref; on the files backend the file is the stop.
_sq9 = re.search(r"^_seqref\(\)\{\n.*?^\}\n", _SC, re.M | re.S)
_crit61 = {}
for _fmt in ("reftable", "files"):
    _d9 = os.path.join(T9, "sq-" + _fmt)
    _feat9 = _stray9(_d9, _fmt)
    if _feat9 is None or not _sq9:
        continue
    _run9 = subprocess.run(
        ["bash", "-c", _sq9.group(0) + "_seqref CHERRY_PICK_HEAD && "
         "printf '%s' \"$SEQREF\""], cwd=_d9, capture_output=True,
        text=True, env=E9, timeout=60)
    _git9 = g5(_d9, "show-ref", "--verify", "-q", "CHERRY_PICK_HEAD",
               env=E9).returncode == 0
    _crit61[_fmt] = (_git9, _run9.returncode == 0
                     and _run9.stdout == _feat9)
if "reftable" not in _crit61:
    print("  SKIP  the reftable half of the next row: this git cannot init "
          "--ref-format=reftable (git 2.45 or later)")
_sq_mod = _mod_src[_mod_src.find("async def seq_ref(name):"):]
_sq_mod = _sq_mod[:_sq_mod.find("\n    mpar, seq, rule, pick")]
check("CRIT6-1: the emitted _seqref ignores a stray head file on reftable, "
      "as git does, and reads it on the files backend; the SDK asks the "
      "backend first; item 1 and Z-54's layer say so",
      _crit61.get("reftable", (False, False)) == (False, False)
      and _crit61.get("files") == (True, True)
      and 0 <= _sq_mod.find("== \"reftable\":")
      < _sq_mod.find("f = await git_path(name)")
      and "Since fix round 7 the ref backend decides which read" in _MERGES
      and "(review of fix round 6, CRIT6-1)" in _MERGES
      and "**Layer 2026-10-13 (WP3 fix round 7, review of fix round 6 "
      "CRIT6-1).**" in _rows["Z-54"]
      and "On the files backend (since fix round 7, only there; see its "
      "layer)" in _rows["Z-54"]
      # The guard's mutants, measured: one direction is caught only on old
      # git, and Z-57 (j) says so.
      and "in `spec-check.sh` and the SDK a guard that always matches fails "
      "on git 2.40 and older" in _rows["Z-57"]
      and "git 2.41 to 2.44 not measured" in _rows["Z-57"]
      # The review of fix round 7 (RV7-3): the files-backend sentence of
      # Z-54's done layer no longer carries the reftable read.
      and "names no branch or tag. Fix round 5" not in _rows["Z-54"]
      and "(CRIT6-1)\"" in read("tests/test_spec_check.py"),
      (_crit61, _sq_mod[:300]))

# CRIT6-1 in merge-back: its in-progress loop, run with not_started
# stubbed, refuses a stray CHERRY_PICK_HEAD file on the files backend and
# not on reftable, where git cherry-pick --abort cannot clear it.
_mbloop = re.search(r"^_rt=0\n.*?^done\n", _MB, re.M | re.S)
_crit61mb = {}
for _fmt in ("reftable", "files"):
    _d9 = os.path.join(T9, "mb-" + _fmt)
    if _stray9(_d9, _fmt) is None or not _mbloop:
        continue
    _ab9 = g5(_d9, "cherry-pick", "--abort", env=E9).returncode
    put(_d9, ".git/CHERRY_PICK_HEAD",
        g5(_d9, "rev-parse", "feat", env=E9).stdout)
    _run9 = subprocess.run(
        ["bash", "-c", "not_started(){ printf '%s' \"$1\"; exit 3; }\n"
         + _mbloop.group(0) + "exit 0\n"], cwd=_d9, capture_output=True, text=True,
        env=E9, timeout=60)
    _crit61mb[_fmt] = (_ab9 == 0, _run9.returncode)
check("CRIT6-1: merge-back's in-progress loop ignores a stray head file on "
      "reftable (git cherry-pick --abort fails there) and still refuses it "
      "on the files backend; item 9 and Z-39's layer say so",
      _crit61mb.get("reftable", (False, 0)) == (False, 0)
      and _crit61mb.get("files") == (True, 3)
      and "Since fix round 7 it reads the two heads by the ref backend"
      in _ITEM9 and "(review of fix round 6, CRIT6-1)" in _ITEM9
      and "**Layer 2026-10-13 (WP3 fix round 7, review of fix round 6 "
      "CRIT6-1, RV6-1, CRIT6-2).** (q) corrected:" in _rows["Z-39"]
      and "(CRIT6-1)\"" in read("tests/test_merge_back.py"), _crit61mb)

# RV6-1, CRIT6-2: git's state once the conflicted step of a cherry-pick of
# several commits is concluded with git commit: no CHERRY_PICK_HEAD, but the
# sequencer stays. The records name a cherry-pick beside a revert.
_d9 = os.path.join(T9, "seq")
os.makedirs(_d9)
_seq9 = None
if g5(_d9, "init", "-q", env=E9).returncode == 0:
    put(_d9, "f", "base\n")
    g5(_d9, "add", "f", env=E9)
    g5(_d9, "commit", "-qm", "base", env=E9)
    g5(_d9, "checkout", "-qb", "side", env=E9)
    put(_d9, "f", "side\n")
    g5(_d9, "commit", "-qam", "s1", env=E9)
    put(_d9, "g", "s2\n")
    g5(_d9, "add", "g", env=E9)
    g5(_d9, "commit", "-qm", "s2", env=E9)
    g5(_d9, "checkout", "-q", "main", env=E9)
    put(_d9, "f", "main\n")
    g5(_d9, "commit", "-qam", "m1", env=E9)
    _cp9 = g5(_d9, "cherry-pick", "side~1", "side", env=E9).returncode
    put(_d9, "f", "resolved\n")
    g5(_d9, "add", "f", env=E9)
    _cm9 = g5(_d9, "commit", "-q", "--no-edit", env=E9).returncode
    _sp9 = g5(_d9, "rev-parse", "--git-path", "sequencer",
              env=E9).stdout.strip()
    _seq9 = (_cp9 != 0 and _cm9 == 0
             and g5(_d9, "rev-parse", "-q", "--verify", "CHERRY_PICK_HEAD",
                    env=E9).returncode != 0
             and os.path.isdir(os.path.join(_d9, _sp9)))
check("RV6-1, CRIT6-2: once the conflicted step of a cherry-pick of several "
      "commits is committed, no head is left and the sequencer is; item 9, "
      "the fix round 6 review paragraph, Z-57 (h) and Z-39's aside say so",
      _seq9 is True
      and "Once a cherry-pick or revert of several commits has had its "
      "conflicted step concluded with `git commit`" in _ITEM9
      and "(review of fix round 6, RV6-1, CRIT6-2; Z-57 (h))" in _ITEM9
      and "Once a revert of several commits" not in _ITEM9
      and "once a step of a cherry-pick or revert of several commits is "
      "committed" in _r5p
      and "(h) Once a `git cherry-pick` or `git revert` of several commits"
      in _rows["Z-57"]
      and "refuses by itself while a `CHERRY_PICK_HEAD` that names a commit "
      "exists" in _rows["Z-39"]
      and "safe only because `git merge` refuses by itself)." not in
      _rows["Z-39"], _seq9)

# The review of fix round 7: RV7-1 is filed as Z-57 (m), with the way out;
# the changelog names it.
check("RV7-1, CRIT7R-1: Z-57 (m) records merge-back's refusal on a head "
      "file that names no commit, and the changelog's fix round 7 paragraph "
      "names it",
      "(m) RV7-1, CRIT7R-1:" in _rows["Z-57"]
      and 'rm "$(git rev-parse --git-path CHERRY_PICK_HEAD)"' in _rows["Z-57"]
      and "is filed as\nZ-57 (m)" in read("docs/changelog.md")
      # RV7-2: Z-39's two git-merge sentences hold only for a head that
      # names a commit, and now say so.
      and "holds only while a `CHERRY_PICK_HEAD` that names a commit exists."
      in _rows["Z-39"]
      and "only for a `CHERRY_PICK_HEAD` file that names a commit, not for a "
      "`REVERT_HEAD` one" in _rows["Z-39"])

# RV6-2, RV6-3: no code change; the installer's own behaviour, derived by
# calling it, is what Z-57 (k) and (l) and the changelog say.
_star9 = " ".join(installer._git_hook_warnings(
    _hk8, installer.Path(ROOT), False, None, ["*?"]))
_lcr9 = os.path.join(T9, "lcr")
_B9, _E9 = "<!-- LEGACY_ALLOWLIST_BEGIN -->", "<!-- LEGACY_ALLOWLIST_END -->"
put(_lcr9, ".claude/steering/spec-strategy.md", f"{_B9}\ra/**\rb\n{_E9}\n")
_lcr_py = installer._legacy_allowlist(installer.Path(_lcr9), {})
_awk9 = re.search(r"\$\((awk '[^']*') \"\$R_STRAT\"",
                  templates._SPEC_CHECK_RETROFIT)
_lcr_awk = subprocess.run(
    ["bash", "-c", _awk9.group(1) + " \"$1\"", "x",
     os.path.join(_lcr9, ".claude/steering/spec-strategy.md")],
    capture_output=True, text=True, env=dict(E9, LC_ALL="C"),
    timeout=60).stdout if _awk9 else None
check("RV6-2, RV6-3: `*?` gets the recipe that names no file though it "
      "exempts every file, a lone-CR allowlist gives the installer patterns "
      "and the check's awk none; Z-57 (k) and (l) and the changelog say so",
      "(it covers every name this installer tried)" in _star9
      and "No commit can confirm the pre-commit line yet" not in _star9
      and _lcr_py == ["a/**", "b"] and _lcr_awk == ""
      and "(k) RV6-2:" in _rows["Z-57"] and "(l) RV6-3:" in _rows["Z-57"]
      and "is sufficient, not necessary" in _rows["Z-57"]
      and "Added by fix round 7 (2026-10-13), from the review of fix round "
      "6:" in _rows["Z-57"]
      and "It still reads two hand-mangled files differently from the check"
      in _WHERE and "(review of fix round 6, RV6-3; backlog Z-57 (l))"
      in _WHERE, (_star9[-300:], _lcr_py, _lcr_awk))
shutil.rmtree(T9, ignore_errors=True)

# The seam's section 10 note: no note quotes what fix round 7 changed.
check("fix round 7: the seam's section 10 note says it changes no note and "
      "no printed text, and no seam note quotes the reads it changed",
      "Fix round 7 (2026-10-13) changes no note either" in _s10
      and "it changes no printed text and adds no `warning:` or `note` "
      "line, flag or field." in _s10
      and not [w for w in ("show-ref", "show-ref-format", "_seqref")
               if w in SEAM])

# --------------------------------------------------------------------------- #
# 6. RR-UP-1: every test file WP3 added is named in its changelog entry
# --------------------------------------------------------------------------- #
print("\n=== 6. RR-UP-1 ===")
# The suites at 3d866f4, WP3's base, pinned as data: CI's checkout is
# shallow, so no git walk can recover them.
_BASE = {
    "test_advisor_model.py", "test_auto_run_sentinel.py",
    "test_block_logging.py", "test_command_embedding.py",
    "test_composition.py", "test_doc_citations.py",
    "test_dynamic_workflow_policy.py", "test_eval_gate.py",
    "test_gate_substrate.py", "test_goal_evaluator_keys.py",
    "test_greenfield_golden.py", "test_hook_behavior.py",
    "test_hook_channels.py", "test_hook_tiers.py", "test_ic_gate.py",
    "test_installer.py", "test_interview.py", "test_issue_fixes.py",
    "test_retrofit.py", "test_root_sentinels.py", "test_runner_output.py",
    "test_sdk_gates.py", "test_settings_merge.py", "test_shared_plumbing.py",
    "test_substrate_differential.py", "test_trust_ramp.py",
    "test_usage_limit_contract.py", "test_validate_only.py",
    "test_wiring_verification.py", "test_worktree_command_compat.py",
    "test_wp2_records.py", "test_wrapper_behavior.py"}
_WP3_NEW = {
    "test_git_hooks.py", "test_spec_check.py", "test_skill_bodies.py",
    "test_versioning_index.py", "test_wp3_agents_handoff.py",
    "test_smoke_stages.py", "test_merge_back.py", "test_live_run_records.py",
    "test_wp3_records.py"}
_TESTS = _CL_RAW[_CL_RAW.find("**Tests.**"):] if "**Tests.**" in _CL_RAW \
    else ""
_on_disk = {f for f in os.listdir(HERE)
            if f.startswith("test_") and f.endswith(".py")}
check("RR-UP-1: every WP3 test file exists", _WP3_NEW <= _on_disk,
      sorted(_WP3_NEW - _on_disk))
check("RR-UP-1: the entry's Tests paragraph names each in backticks",
      bool(_TESTS) and all(f"`tests/{f}`" in _TESTS for f in _WP3_NEW),
      sorted(f for f in _WP3_NEW if f"`tests/{f}`" not in _TESTS))
check("RR-UP-1: it says how many (nine)",
      "Nine new files" in _TESTS and len(_WP3_NEW) == 9)
# Derived, and forward-compatible: a suite added after 3d866f4 must be named
# by WP3's entry or by a later one, which sits above it.
_later = read("docs/changelog.md").split(
    "## Post-2.8.0 — hooks that reach the model (WP2)")[0]
_unnamed = sorted(f for f in _on_disk - _BASE if f not in _later)
check("RR-UP-1: every suite on disk since 3d866f4 is named in the changelog "
      "at or above WP3's entry", not _unnamed, _unnamed)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

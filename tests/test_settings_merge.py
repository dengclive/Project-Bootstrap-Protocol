#!/usr/bin/env python3
"""Self-contained test suite. Run: python3 tests/test_settings_merge.py

`.claude/settings.json` is CO-OWNED: the installer contributes hook
registrations and the `never_read_paths` deny rules; the operator owns
everything else (`permissions.allow`, `model`, `env`, `statusLine`, and hooks
of their own). It used to get whole-file skip semantics, which was uniquely
destructive because it is the ONLY registration site for the shell substrate -
declining to write it disabled every gate at once, silently, at rc=0.

It now gets the same treatment the co-owned project-root `.gitignore` already
had, by KEY instead of by marker block. What that has to guarantee:

  * a fresh install is byte-identical to before (goldens must not move)
  * operator content survives install AND uninstall
  * an operator's OWN hook registration survives - ownership is per-ENTRY,
    not per-key, or the fix just relocates the data loss it removes
  * re-applying converges (`ok`, not a digest that churns every run)
  * a contribution we retire actually goes away
  * a shape we cannot merge is declined, never guessed at
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "lib"))

from installer import (                          # noqa: E402
    _SETTINGS_OWNED_KEYS, _SETTINGS_SHARED_KEYS, _is_ours_here, _merge_hooks,
    _merge_settings, _settings_mergeable, _resolved_hook_path,
    _SETTINGS_CONTRIBUTED_KEYS, build_plan,
)
from defaults import resolve_config               # noqa: E402
from minyaml import load_yaml                     # noqa: E402

BIN = os.path.join(ROOT, "bin", "bootstrap-install")

# [WP3 critic 1j] Hermetic: git never searches above the temp directory. The
# installer now looks for the repository a project sits in (the spec check's
# git hooks), and with TMPDIR inside some work tree (a dotfiles repository in
# $HOME) every fixture would read as a directory inside that repository and
# draw a stderr warning. Inherited by every subprocess this suite starts.
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


SERVICE = """
project:
  name: demo
  archetype: service
principles:
  tdd_policy: required
commands:
  test: "true"
  lint: "true"
  format: "true"
secrets:
  enabled: true
  never_read_paths: [".env*", "secrets/**", "*.pem"]
"""


def install(root, cfg_text=SERVICE, argv=()):
    cfg = os.path.join(root, "cfg.yaml")
    with open(cfg, "w") as fh:
        fh.write(cfg_text)
    return subprocess.run([sys.executable, BIN, "-c", cfg, "-C", root, *argv],
                          capture_output=True, text=True)


def uninstall(root):
    return subprocess.run([sys.executable, BIN, "-C", root, "--uninstall"],
                          capture_output=True, text=True)


def seed(root, settings):
    os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
    with open(os.path.join(root, ".claude", "settings.json"), "w") as fh:
        fh.write(settings if isinstance(settings, str)
                 else json.dumps(settings, indent=2) + "\n")


def stderr_sans_floor(text):
    """stderr with the AC-9-4 runtime-floor advisory removed.

    `_runtime_floor_check` writes to stderr when the Claude Code CLI is absent
    from PATH or below RUNTIME_FLOOR - deliberately, and documented as "never
    silent". It is a property of the MACHINE, not of the install, so a bare
    `stderr == ""` holds on a developer box with the CLI and fails on CI,
    which has none. Assert on what is left, which is what this check always
    meant: the INSTALLER reported nothing of its own.
    """
    return "\n".join(ln for ln in text.splitlines()
                     if not ln.startswith("WARNING: Claude Code ")).strip()


def read(root):
    with open(os.path.join(root, ".claude", "settings.json")) as fh:
        return json.load(fh)


def commands_in(settings):
    out = []
    for groups in (settings.get("hooks") or {}).values():
        for grp in groups:
            for entry in grp.get("hooks", []):
                out.append(entry["command"])
    return out


# =========================================================================== #
# The forcing function: every key we emit must have an ownership decision
# =========================================================================== #
print("\n-- ownership is declared, not inferred --")

_d = tempfile.mkdtemp()
try:
    install(_d)
    emitted = set(read(_d))
    # [WP3 / model assignment] A contributed key (`ultracode`) is the third
    # decision: added only where the operator has none, never owned.
    unclaimed = (emitted - set(_SETTINGS_OWNED_KEYS)
                 - set(_SETTINGS_SHARED_KEYS)
                 - set(_SETTINGS_CONTRIBUTED_KEYS))
    check("every top-level key we emit is owned, shared or contributed, "
          "none unclaimed",
          not unclaimed,
          f"unclaimed: {sorted(unclaimed)} - add it to _SETTINGS_OWNED_KEYS "
          f"or teach _merge_settings to share it")
    check("[WP3] the three decisions are disjoint",
          not (set(_SETTINGS_OWNED_KEYS) & set(_SETTINGS_SHARED_KEYS))
          and not (set(_SETTINGS_CONTRIBUTED_KEYS)
                   & (set(_SETTINGS_OWNED_KEYS) | set(_SETTINGS_SHARED_KEYS))))
finally:
    shutil.rmtree(_d, ignore_errors=True)


# =========================================================================== #
# End-to-end merge behaviour
# =========================================================================== #
print("\n-- merge preserves operator content --")

OPERATOR = {
    "permissions": {"allow": ["Bash(npm run test:*)"], "deny": ["Bash(rm:*)"]},
    "model": "opus",
    "env": {"MY_KEY": "1"},
    "statusLine": {"type": "command", "command": "mine"},
}

_d = tempfile.mkdtemp()
try:
    seed(_d, OPERATOR)
    r = install(_d)
    got = read(_d)
    check("merging exits 0", r.returncode == 0, f"rc={r.returncode}")
    check("operator permissions.allow survives",
          got["permissions"]["allow"] == ["Bash(npm run test:*)"])
    check("operator deny rule survives",
          "Bash(rm:*)" in got["permissions"]["deny"])
    check("operator model/env/statusLine survive",
          got.get("model") == "opus" and got.get("env") == {"MY_KEY": "1"}
          and got.get("statusLine") == {"type": "command", "command": "mine"})
    check("our deny rules were unioned in, not substituted",
          "Read(.env*)" in got["permissions"]["deny"]
          and "Bash(rm:*)" in got["permissions"]["deny"])
    check("hook registrations are present after the merge",
          any("secrets-gate.sh" in c for c in commands_in(got)))

    # Idempotence: the merge must be a fixed point or every run churns.
    before = json.dumps(got, sort_keys=True)
    r2 = install(_d)
    check("re-apply reports the wiring as current",
          "hook wiring current" in r2.stdout, r2.stdout[-300:])
    check("re-apply is byte-stable",
          json.dumps(read(_d), sort_keys=True) == before)
    r3 = install(_d)
    check("a third apply is still stable",
          json.dumps(read(_d), sort_keys=True) == before)

    # Uninstall must give the operator their file back.
    uninstall(_d)
    back = read(_d)
    check("uninstall restores the operator's file exactly",
          back == OPERATOR, json.dumps(back, indent=1))
finally:
    shutil.rmtree(_d, ignore_errors=True)

print("\n-- an operator's OWN hook is not collateral --")

MINE = "$CLAUDE_PROJECT_DIR/.claude/hooks/mine.sh"
OWN_HOOK = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
    {"type": "command", "command": MINE}]}]}, "model": "opus"}

_d = tempfile.mkdtemp()
try:
    seed(_d, OWN_HOOK)
    os.makedirs(os.path.join(_d, ".claude", "hooks"), exist_ok=True)
    with open(os.path.join(_d, ".claude", "hooks", "mine.sh"), "w") as fh:
        fh.write("#!/bin/sh\nexit 0\n")
    r = install(_d)
    got = read(_d)
    check("installing alongside an operator hook exits 0", r.returncode == 0,
          f"rc={r.returncode} stderr={r.stderr[-300:]}")
    check("the operator's own hook is still registered",
          MINE in commands_in(got), str(commands_in(got)))
    check("ours are registered in the same matcher group",
          any("secrets-gate.sh" in c for c in commands_in(got)))
    before = json.dumps(got, sort_keys=True)
    install(_d)
    check("operator-hook merge is idempotent too",
          json.dumps(read(_d), sort_keys=True) == before)
    uninstall(_d)
    check("uninstall strips ours and leaves the operator's hook",
          read(_d) == OWN_HOOK, json.dumps(read(_d), indent=1))
finally:
    shutil.rmtree(_d, ignore_errors=True)

print("\n-- retiring a contribution --")

_d = tempfile.mkdtemp()
try:
    seed(_d, {"permissions": {"deny": ["Bash(rm:*)"]}})
    install(_d)
    check("all three never_read_paths produced deny rules",
          all(f"Read({p})" in read(_d)["permissions"]["deny"]
              for p in (".env*", "secrets/**", "*.pem")))
    # Shrink the config: the rules we contributed for the dropped paths must
    # go, and the operator's must stay.
    install(_d, cfg_text=SERVICE.replace(
        'never_read_paths: [".env*", "secrets/**", "*.pem"]',
        'never_read_paths: [".env*"]'))
    deny = read(_d)["permissions"]["deny"]
    check("a retired deny rule is actually removed",
          "Read(*.pem)" not in deny and "Read(secrets/**)" not in deny,
          str(deny))
    check("the still-configured rule stays", "Read(.env*)" in deny)
    check("the operator's own deny rule is untouched", "Bash(rm:*)" in deny)

    # Same for a retired hook: tdd-gate leaves the plan when tdd_policy is off.
    install(_d, cfg_text=SERVICE.replace("tdd_policy: required",
                                         "tdd_policy: off"))
    check("a retired hook is de-registered",
          not any("tdd-gate" in c for c in commands_in(read(_d))))
finally:
    shutil.rmtree(_d, ignore_errors=True)

print("\n-- shapes we refuse rather than guess at --")

for label, shape in (
        ("not JSON", "nope {{\n"),
        ("a JSON list", "[]\n"),
        ("permissions is a string", '{"permissions": "x"}\n'),
        ("hooks is a string", '{"hooks": "x"}\n'),
        ("an event is not a list", '{"hooks": {"PreToolUse": "x"}}\n'),
):
    _d = tempfile.mkdtemp()
    try:
        seed(_d, shape)
        r = install(_d)
        kept = open(os.path.join(_d, ".claude", "settings.json")).read()
        check(f"declined and non-zero: {label}", r.returncode == 3,
              f"rc={r.returncode}")
        check(f"operator file untouched: {label}", kept == shape)
    finally:
        shutil.rmtree(_d, ignore_errors=True)

# A fresh install must stay byte-identical to the pre-merge installer, or the
# golden freeze surface moves for a change that emits nothing new.
_a, _b = tempfile.mkdtemp(), tempfile.mkdtemp()
try:
    install(_a)
    install(_b)
    check("two fresh installs are byte-identical",
          open(os.path.join(_a, ".claude", "settings.json")).read()
          == open(os.path.join(_b, ".claude", "settings.json")).read())
    _entry = next(f for f in json.load(open(os.path.join(
        _a, ".claude", ".installer-manifest.json")))["files"]
        if f["path"] == ".claude/settings.json")
    check("a fresh install carries a whole-file digest in the manifest "
          "(so uninstall removes it)",
          _entry.get("digest") and _entry.get("state") is None)
    # Regression: the WHOLESALE write must also record what it contributed.
    # Without it the first merge afterwards has no record of which
    # registrations were ours, so a hook dropped from the plan stays
    # registered forever while the same run deletes the file it names.
    # owned_hooks entries are SITES - [event, matcher, command] - not bare
    # commands; see _hook_sites (round-6 F2).
    check("a wholesale write still records owned_hooks / owned_deny",
          any("secrets-gate.sh" in site[2]
              for site in _entry.get("owned_hooks", []))
          and any(r.startswith("Read(") for r in _entry.get("owned_deny", [])),
          json.dumps({k: _entry.get(k)
                      for k in ("owned_hooks", "owned_deny")})[:300])
finally:
    shutil.rmtree(_a, ignore_errors=True)
    shutil.rmtree(_b, ignore_errors=True)


# =========================================================================== #
# Units
# =========================================================================== #
print("\n-- units --")

check("_settings_mergeable accepts an absent permissions/hooks",
      _settings_mergeable({"model": "opus"}))
check("_settings_mergeable rejects a non-object permissions",
      not _settings_mergeable({"permissions": []}))
check("_settings_mergeable rejects a non-object hooks",
      not _settings_mergeable({"hooks": 3}))
check("_settings_mergeable rejects a non-list event",
      not _settings_mergeable({"hooks": {"PreToolUse": {}}}))

OURS_H = {"PreToolUse": [{"matcher": "Bash", "hooks": [
    {"type": "command", "command": "ours-a"}]}]}

_m, _own = _merge_hooks(OURS_H, {}, [])
check("_merge_hooks on an empty operator map yields ours",
      _m == OURS_H and _own == [["PreToolUse", "Bash", "ours-a"]], str(_own))

_theirs = {"PreToolUse": [{"matcher": "Bash", "hooks": [
    {"type": "command", "command": "theirs"}]}]}
_m, _own = _merge_hooks(OURS_H, _theirs, [])
check("_merge_hooks appends into a matching matcher group",
      [e["command"] for e in _m["PreToolUse"][0]["hooks"]]
      == ["theirs", "ours-a"], str(_m))

_m2, _ = _merge_hooks(OURS_H, _m, ["ours-a"])
check("_merge_hooks is a fixed point", _m2 == _m, str(_m2))

_stale = {"PreToolUse": [{"matcher": "Bash", "hooks": [
    {"type": "command", "command": "theirs"},
    {"type": "command", "command": "retired"}]}]}
_m3, _ = _merge_hooks(OURS_H, _stale, ["retired"])
check("_merge_hooks retires a previously-owned command",
      [e["command"] for e in _m3["PreToolUse"][0]["hooks"]]
      == ["theirs", "ours-a"], str(_m3))

_opaque = {"PreToolUse": [{"weird": True}, 7]}
_m4, _ = _merge_hooks({}, _opaque, [])
check("_merge_hooks passes opaque operator groups through untouched",
      _m4 == _opaque, str(_m4))

_merged, _d1, _h1 = _merge_settings(
    {"$schema": "s", "hooks": OURS_H,
     "permissions": {"deny": ["Read(.env*)"]}},
    {"permissions": {"allow": ["A"], "deny": ["Bash(rm:*)"]}, "model": "opus"},
    [], [])
check("_merge_settings keeps operator keys and unions deny",
      _merged["model"] == "opus"
      and _merged["permissions"]["allow"] == ["A"]
      and _merged["permissions"]["deny"] == ["Bash(rm:*)", "Read(.env*)"],
      json.dumps(_merged))
check("_merge_settings reports what it contributed",
      _d1 == ["Read(.env*)"]
      and _h1 == [["PreToolUse", "Bash", "ours-a"]], f"{_d1} {_h1}")

_gone, _, _ = _merge_settings(
    {}, {"permissions": {"deny": ["Read(*.pem)"]}}, ["Read(*.pem)"], [])
check("_merge_settings drops a permissions block left empty by retirement",
      "permissions" not in _gone, json.dumps(_gone))


# =========================================================================== #
# --force is destructive by design; it must not be IRRECOVERABLE
# =========================================================================== #
print("\n-- --force keeps a copy of what it displaced --")

from installer import BACKUP_DIR, _is_operator_content   # noqa: E402


def backups(root):
    d = os.path.join(root, *BACKUP_DIR.split("/"))
    out = []
    for base, _dirs, files in os.walk(d):
        out.extend(os.path.join(base, f) for f in files)
    return out


UNMERGEABLE = '{"permissions": "not-an-object", "model": "opus"}\n'

_d = tempfile.mkdtemp()
try:
    seed(_d, UNMERGEABLE)
    install(_d)                                   # declines; rc=3
    r = install(_d, argv=("--force",))
    saved = backups(_d)
    check("--force over an unmergeable settings.json exits 0",
          r.returncode == 0, f"rc={r.returncode}")
    check("--force wrote exactly one backup", len(saved) == 1, str(saved))
    check("the backup is byte-identical to what was displaced",
          saved and open(saved[0]).read() == UNMERGEABLE)
    check("the run says where the backup is",
          BACKUP_DIR in r.stdout and "displaced" in r.stdout,
          r.stdout[-400:])
    check("--force still writes nothing to stderr",
          stderr_sans_floor(r.stderr) == "", repr(r.stderr[-300:]))
    check("the forced write actually took effect",
          "hooks" in read(_d))
finally:
    shutil.rmtree(_d, ignore_errors=True)

_d = tempfile.mkdtemp()
try:
    install(_d)
    hook = os.path.join(_d, ".claude", "hooks", "secrets-gate.sh")
    with open(hook, "a") as fh:
        fh.write("# operator note\n")
    r = install(_d, argv=("--force",))
    saved = [p for p in backups(_d) if p.endswith("secrets-gate.sh")]
    check("--force over a hand-edited hook backs it up", len(saved) == 1,
          str(backups(_d)))
    check("the operator's edit is recoverable from the backup",
          saved and "# operator note" in open(saved[0]).read())
    check("the hook on disk is now ours again",
          "# operator note" not in open(hook).read())
finally:
    shutil.rmtree(_d, ignore_errors=True)

# A --force that destroys nothing must not litter or cry wolf: the whole
# signal is worthless if every forced re-apply produces a backup directory.
_d = tempfile.mkdtemp()
try:
    install(_d)
    r = install(_d, argv=("--force",))
    check("--force with nothing of theirs to lose writes no backup",
          backups(_d) == [], str(backups(_d)))
    check("--force with nothing to lose says nothing about backups",
          "displaced" not in r.stdout)
finally:
    shutil.rmtree(_d, ignore_errors=True)

_d = tempfile.mkdtemp()
try:
    seed(_d, UNMERGEABLE)
    r = install(_d, argv=("--force", "--dry-run"))
    check("--force --dry-run writes no backup to disk",
          backups(_d) == [], str(backups(_d)))
    check("--force --dry-run still previews the backup path",
          "previous version would be saved to" in r.stdout, r.stdout[-300:])
    check("--force --dry-run leaves the operator file alone",
          open(os.path.join(_d, ".claude", "settings.json")).read()
          == UNMERGEABLE)
finally:
    shutil.rmtree(_d, ignore_errors=True)

# Backups are the operator's recovery material, not an installer artifact.
_d = tempfile.mkdtemp()
try:
    seed(_d, UNMERGEABLE)
    install(_d)
    install(_d, argv=("--force",))
    n = len(backups(_d))
    uninstall(_d)
    check("--uninstall does not delete the backups it made", len(backups(_d)) == n,
          f"{n} -> {len(backups(_d))}")
    check("backups are not manifest-tracked",
          not any(BACKUP_DIR in f["path"]
                  for f in json.load(open(os.path.join(
                      _d, ".claude", ".installer-manifest.json")))["files"]))
finally:
    shutil.rmtree(_d, ignore_errors=True)

# Two forced runs in the same second share a backup directory; the second
# must not silently clobber the first one's copy.
_d = tempfile.mkdtemp()
try:
    seed(_d, '{"permissions": "bad", "v": 1}\n')
    install(_d, argv=("--force",))
    seed(_d, '{"permissions": "bad", "v": 2}\n')
    install(_d, argv=("--force",))
    bodies = [open(p).read() for p in backups(_d)]
    check("a second --force in the same second does not clobber the first",
          any('"v": 1' in b for b in bodies)
          and any('"v": 2' in b for b in bodies), str(bodies))
finally:
    shutil.rmtree(_d, ignore_errors=True)

# `permissions.deny` is the one key we WRITE INTO, so a non-list there must be
# refused rather than coerced - coercing silently deleted an operator's rule.
for _label, _shape in (("deny is a string",
                        '{"permissions": {"allow": ["Bash(x)"],'
                        ' "deny": "Bash(rm:*)"}}\n'),
                       ("deny is an object",
                        '{"permissions": {"deny": {"a": 1}}}\n')):
    _d = tempfile.mkdtemp()
    try:
        seed(_d, _shape)
        r = install(_d)
        kept = open(os.path.join(_d, ".claude", "settings.json")).read()
        check(f"declined rather than coerced: {_label}", r.returncode == 3,
              f"rc={r.returncode}")
        check(f"operator rule survives: {_label}", kept == _shape, kept)
    finally:
        shutil.rmtree(_d, ignore_errors=True)

check("_settings_mergeable rejects a non-list permissions.deny",
      not _settings_mergeable({"permissions": {"deny": "x"}}))
check("_settings_mergeable accepts an absent permissions.deny",
      _settings_mergeable({"permissions": {"allow": ["a"]}}))

check("_is_operator_content: untracked path", _is_operator_content(None, "d"))
check("_is_operator_content: digest drift",
      _is_operator_content({"digest": "old"}, "new"))
check("_is_operator_content: sticky skip",
      _is_operator_content({"digest": "d", "state": "skipped-local-edit"}, "d"))
check("_is_operator_content: our own untouched file is NOT theirs",
      not _is_operator_content({"digest": "d"}, "d"))
check("_is_operator_content: a co-owned entry (no whole-file digest) is theirs",
      _is_operator_content({"state": "settings-merged",
                            "block_digest": "b"}, "d"))

# =========================================================================== #
# Round-6 regressions: operator content that OVERLAPS ours
# =========================================================================== #
# Every fixture above this point picks operator content DISJOINT from what the
# installer emits - deny rules like `Bash(rm:*)` that we never produce, hook
# commands like `mine` that name no script of ours. Three live defects lived
# in the overlap, invisible to a suite that never creates one. These tests
# exist to keep that overlap covered.
print("\n-- operator content that collides with ours is still THEIRS --")

# F1. A rule we emit is one a security-conscious operator writes themselves.
# Recording it as ours meant deleting it on their behalf: once at --uninstall,
# and once on any re-apply that narrowed never_read_paths - rc=0, under a line
# reading "operator settings untouched".
NARROW = SERVICE.replace('[".env*", "secrets/**", "*.pem"]', '["secrets/**"]')
_d = tempfile.mkdtemp()
try:
    theirs = {"permissions": {"deny": ["Read(.env*)", "Read(vault/**)"]}}
    seed(_d, theirs)
    install(_d)
    deny = read(_d)["permissions"]["deny"]
    check("their rule that we also emit survives the merge",
          "Read(.env*)" in deny, str(deny))
    check("and keeps its position, ahead of everything we added",
          deny[:2] == ["Read(.env*)", "Read(vault/**)"], str(deny))

    install(_d, cfg_text=NARROW)          # .env* no longer configured
    deny = read(_d)["permissions"]["deny"]
    check("re-applying a narrowed config does not delete their rule",
          "Read(.env*)" in deny, str(deny))
    check("but does retire the ones we really did contribute",
          "Edit(.env*)" not in deny and "Write(.env*)" not in deny, str(deny))

    uninstall(_d)
    check("uninstall hands back a colliding deny rule, not a subset of it",
          read(_d) == theirs, json.dumps(read(_d)))
finally:
    shutil.rmtree(_d, ignore_errors=True)

# F1, second key. The keys we own OUTRIGHT are ones an operator may already
# have set - `$schema` most of all. Overwriting is fine; deleting on the way
# out is not.
_d = tempfile.mkdtemp()
try:
    theirs = {"$schema": "https://example.com/team.schema.json",
              "model": "opus"}
    seed(_d, theirs)
    install(_d)
    check("we take over $schema while installed",
          read(_d)["$schema"].startswith("https://json.schemastore.org/"))
    uninstall(_d)
    check("uninstall RESTORES their $schema rather than deleting it",
          read(_d) == theirs, json.dumps(read(_d)))
finally:
    shutil.rmtree(_d, ignore_errors=True)

# ...and the mirror of it. When there is no record to carry - a manifest lost
# with a fresh clone, or one written before displaced_keys existed - the
# operator's values are re-derived from a file that ALREADY HOLDS OURS. Taking
# that at face value leaves `_generatedBy: bootstrap-installer` sitting in
# their settings.json after an uninstall that claimed to remove everything it
# created.
_d = tempfile.mkdtemp()
try:
    seed(_d, {"model": "opus"})
    install(_d)
    os.remove(os.path.join(_d, ".claude", ".installer-manifest.json"))
    install(_d)                       # re-derives with no record to carry
    uninstall(_d)
    left = read(_d)
    check("uninstall leaves none of OUR owned keys behind",
          not any(k in left for k in _SETTINGS_OWNED_KEYS), json.dumps(left))
    check("and still keeps the operator's own keys",
          left.get("model") == "opus", json.dumps(left))
finally:
    shutil.rmtree(_d, ignore_errors=True)

# F2. Ownership of a hook is per SITE, not per command. An operator may
# deliberately widen one of our gates by registering our script at an event or
# matcher we do not emit; command-keyed ownership deleted that silently.
_d = tempfile.mkdtemp()
try:
    ours_cmd = '"$CLAUDE_PROJECT_DIR"/.claude/hooks/secrets-gate.sh'
    theirs = {"hooks": {
        "PreToolUse": [{"matcher": "WebFetch", "hooks": [
            {"type": "command", "command": ours_cmd}]}],
        "SessionStart": [{"hooks": [
            {"type": "command", "command": ours_cmd}]}]}}
    seed(_d, theirs)
    r = install(_d)
    got = read(_d)
    matchers = [g.get("matcher") for g in got["hooks"]["PreToolUse"]]
    check("their registration of OUR script at their own event survives",
          got["hooks"].get("SessionStart") == theirs["hooks"]["SessionStart"],
          json.dumps(got["hooks"].get("SessionStart")))
    check("and at their own matcher under an event we do emit",
          "WebFetch" in matchers, str(matchers))
    check("while ours is still registered where we put it",
          "Bash" in matchers and ours_cmd in commands_in(got), str(matchers))
    check("a merge that preserves their sites still exits 0",
          r.returncode == 0, r.stderr[-300:])

    uninstall(_d)
    check("uninstall retires only our site and hands their file back",
          read(_d) == theirs, json.dumps(read(_d)))
finally:
    shutil.rmtree(_d, ignore_errors=True)

# F4. Every refusal used to be reported as a `permissions` problem, including
# for files carrying no `permissions` key at all. The only remedy the message
# offers is --force, which replaces the whole file, so a misdirected diagnosis
# costs the operator real content.
# The manifest is a file on the operator's disk. A record that does not
# describe a site we recognise must degrade to "we own nothing there", never
# abort the install: an unhashable matcher raised TypeError out of apply_plan
# and left the tree half-written.
_d = tempfile.mkdtemp()
try:
    seed(_d, {"model": "opus"})
    install(_d)
    _mf = os.path.join(_d, ".claude", ".installer-manifest.json")
    with open(_mf) as fh:
        _m = json.load(fh)
    for _f in _m["files"]:
        if _f["path"].endswith("settings.json"):
            _f["owned_hooks"] = [["PreToolUse", [], "x"], 7, ["a", "b"],
                                 ["PreToolUse", None, "keep-me"]]
    with open(_mf, "w") as fh:
        json.dump(_m, fh)
    _r = install(_d)
    check("a hand-edited owned_hooks record does not abort the install",
          _r.returncode == 0, _r.stderr[-300:])
    check("and the tree still enforces afterwards",
          "ERROR" not in _r.stderr, _r.stderr[-200:])
finally:
    shutil.rmtree(_d, ignore_errors=True)

# [round-6 F5] A symlinked settings.json gets neither guess. Replacing it
# orphans its target; writing THROUGH it would put `$CLAUDE_PROJECT_DIR/...`
# hook commands into a file other projects share, where they resolve
# per-project and exit 127 on every matching call.
print("\n-- a symlinked settings.json is declined, not resolved --")
_d = tempfile.mkdtemp()
_ext = tempfile.mkdtemp()
try:
    _shared = os.path.join(_ext, "team.json")
    with open(_shared, "w") as fh:
        fh.write('{"model":"opus","permissions":{"deny":["Read(x/**)"]}}\n')
    _before = open(_shared).read()
    os.makedirs(os.path.join(_d, ".claude"), exist_ok=True)
    os.symlink(_shared, os.path.join(_d, ".claude", "settings.json"))
    _r = install(_d)
    _link = os.path.join(_d, ".claude", "settings.json")
    check("a symlinked settings.json is declined, not written",
          os.path.islink(_link), _r.stdout[-300:])
    check("the SKIP names the link target",
          _shared in _r.stdout, _r.stdout[-300:])
    check("the file behind the link is untouched",
          open(_shared).read() == _before)
    check("and the run reports itself unenforced", _r.returncode == 3,
          f"rc={_r.returncode}")
    _rf = install(_d, argv=("--force",))
    check("--force is still the documented way through",
          not os.path.islink(_link) and _rf.returncode == 0,
          _rf.stdout[-200:])
finally:
    shutil.rmtree(_d, ignore_errors=True)
    shutil.rmtree(_ext, ignore_errors=True)


# [round-6 F6] The manifest is gitignored, so a clone carries the whole tree
# and none of its provenance. Every file this installer wrote then reads as
# the operator's, and a config change makes the skip permanent at rc=3 with
# --force -- whose warning says it destroys what you put there -- the only way
# out. --adopt is the non-destructive one.
print("\n-- --adopt breaks a manifest-less tree out of a permanent rc=3 --")
# The transition has to actually CHANGE a security-critical file, or there is
# nothing for the manifest's absence to misjudge. eval_gate moves gates.py.
# [WP1 / D4 (a)] gates.py is emitted only for the SDK substrate, and
# eval-gate.sh is no longer security-critical, so request the substrate
# to keep a security-critical file in the transition.
_HOOKS_ON = (SERVICE + 'gate_substrate: "sdk-callable"\n'
             + "hooks: {cost_log: true, eval_gate: true}\n")
_HOOKS_OFF = (SERVICE + 'gate_substrate: "sdk-callable"\n'
              + "hooks: {cost_log: false, eval_gate: false}\n")
_d = tempfile.mkdtemp()
try:
    install(_d, cfg_text=_HOOKS_ON)
    _gates = os.path.join(_d, ".claude", "sdk_gates", "gates.py")
    _stale = open(_gates).read()
    os.remove(os.path.join(_d, ".claude", ".installer-manifest.json"))

    _r = install(_d, cfg_text=_HOOKS_OFF)
    check("with no manifest, a security-critical file is skipped at rc=3",
          _r.returncode == 3, f"rc={_r.returncode}")
    check("the reason does not claim the file is the operator's work",
          "no installer manifest" in _r.stdout, _r.stdout[-400:])
    check("and stderr gives the per-file remedy, not --adopt advice",
          "move it aside and re-install" in _r.stderr
          and "Don't use --adopt for this" in _r.stderr, _r.stderr[-300:])

    _a = install(_d, cfg_text=_HOOKS_OFF, argv=("--adopt",))
    check("--adopt exits 0", _a.returncode == 0, _a.stderr[-300:])
    check("--adopt writes NOTHING at the adopted path",
          open(_gates).read() == _stale)
    check("--adopt says what it did", "ADOPT" in _a.stdout, _a.stdout[-300:])

    _b = install(_d, cfg_text=_HOOKS_OFF)
    check("the ordinary re-run afterwards exits 0", _b.returncode == 0,
          _b.stderr[-300:])
    check("and brings the adopted file up to date",
          open(_gates).read() != _stale)
    check("the tree is no longer stuck",
          install(_d, cfg_text=_HOOKS_OFF).returncode == 0)
finally:
    shutil.rmtree(_d, ignore_errors=True)

_d = tempfile.mkdtemp()
try:
    seed(_d, {"model": "opus"})
    _x = install(_d, argv=("--force", "--adopt"))
    check("--force and --adopt together is refused, not silently ordered",
          _x.returncode == 2 and "mutually exclusive" in _x.stderr,
          f"rc={_x.returncode} {_x.stderr[-200:]}")
finally:
    shutil.rmtree(_d, ignore_errors=True)


print("\n-- a refusal names the key that actually caused it --")
for _shape, _want in (
        ({"permissions": "bad"}, "`permissions` key"),
        ({"permissions": {"deny": "Read(x)"}}, "`permissions.deny`"),
        ({"hooks": "nope"}, "`hooks` key"),
        ({"hooks": {"PreToolUse": {"a": 1}}}, "`hooks.PreToolUse`")):
    _d = tempfile.mkdtemp()
    try:
        seed(_d, _shape)
        _r = install(_d)
        _line = next((ln for ln in _r.stdout.splitlines()
                      if "SKIP" in ln and "settings.json" in ln), "")
        check(f"decline names {_want}", _want in _line,
              _line or _r.stdout[-200:])
        check(f"decline for {_want} still exits 3", _r.returncode == 3)
    finally:
        shutil.rmtree(_d, ignore_errors=True)


# =========================================================================== #
# A group we cannot KEY is not a group we may crash on
# =========================================================================== #
# Ownership is keyed on (event, matcher, command), and that tuple is hashed
# against a set. Two of its three elements come out of the OPERATOR's file,
# which may carry any JSON at all: a list or object `matcher` is unhashable
# and raised TypeError straight out of apply_plan. The install aborted after
# 22 of 58 files - every hook script on disk, none of them registered - and
# `--uninstall` aborted outright, so the tree could not be removed at all.
# `_split_owned_hooks` type-checks this same triple coming from the manifest;
# nothing checked it coming from their file. Every fixture in this suite used
# a string matcher, so nothing caught it.
print("\n-- an unkeyable operator group is passed through, never crashed on --")

for _label, _grp in (
        ("list matcher",   {"matcher": ["Write", "Edit"],
                            "hooks": [{"type": "command",
                                       "command": "my-audit.sh"}]}),
        ("object matcher", {"matcher": {"tool": "Write"},
                            "hooks": [{"type": "command",
                                       "command": "my-audit.sh"}]}),
        ("list command",   {"matcher": "Write",
                            "hooks": [{"type": "command",
                                       "command": ["a", "b"]}]})):
    _d = tempfile.mkdtemp()
    try:
        seed(_d, {"hooks": {"PreToolUse": [_grp]}})
        _r = install(_d)
        check(f"{_label}: install completes instead of aborting",
              _r.returncode == 0, f"rc={_r.returncode} {_r.stderr[-300:]}")
        if _r.returncode == 0:
            _s = read(_d)
            # Their ENTRY, not their whole group: a group whose matcher is one
            # we also emit legitimately gains our hook alongside theirs.
            check(f"{_label}: the operator's registration survives the merge",
                  any(g.get("matcher") == _grp["matcher"]
                      and _grp["hooks"][0] in g.get("hooks", [])
                      for g in _s["hooks"]["PreToolUse"]),
                  json.dumps(_s["hooks"]["PreToolUse"])[:300])
            check(f"{_label}: our own wiring still lands",
                  len([c for c in commands_in(_s)
                       if isinstance(c, str)
                       and _resolved_hook_path(c) is not None]) == 13)
    finally:
        shutil.rmtree(_d, ignore_errors=True)

_d = tempfile.mkdtemp()
try:
    seed(_d, {"model": "opus"})
    install(_d)
    # The operator adds the unkeyable group AFTER a healthy install, which is
    # what made this reachable without ever having seen a failed one.
    _s = read(_d)
    _s["hooks"]["PostToolUse"].append(
        {"matcher": ["Write", "Edit"],
         "hooks": [{"type": "command", "command": "my-audit.sh"}]})
    seed(_d, _s)
    _r = uninstall(_d)
    check("uninstall completes with an unkeyable group in their file",
          _r.returncode == 0, f"rc={_r.returncode} {_r.stderr[-300:]}")
    _after = read(_d)
    check("uninstall keeps the unkeyable group and their other settings",
          _after.get("model") == "opus"
          and _after["hooks"]["PostToolUse"][0]["matcher"] == ["Write", "Edit"],
          json.dumps(_after))
    check("uninstall still retires OUR registrations",
          not [c for c in commands_in(_after)
               if isinstance(c, str) and _resolved_hook_path(c) is not None])
finally:
    shutil.rmtree(_d, ignore_errors=True)

print("\n-- _is_ours_here: keyable or not, the answer is a bool --")
_site = ("PreToolUse", "Bash", "x.sh")
check("a site we emit is ours",
      _is_ours_here("PreToolUse", "Bash", {"command": "x.sh"}, {_site}, set()))
check("the same command at another matcher is theirs",
      not _is_ours_here("PreToolUse", "Read", {"command": "x.sh"},
                        {_site}, set()))
check("an unhashable matcher answers False rather than raising",
      not _is_ours_here("PreToolUse", ["Bash"], {"command": "x.sh"},
                        {_site}, set()))
check("an unhashable command answers False rather than raising",
      not _is_ours_here("PreToolUse", "Bash", {"command": ["x.sh"]},
                        {_site}, set()))
check("a legacy command matches at ANY matcher, including unkeyable ones",
      _is_ours_here("PreToolUse", ["Bash"], {"command": "x.sh"},
                    set(), {"x.sh"}))


# =========================================================================== #
# displaced_keys is recorded by every path that WRITES
# =========================================================================== #
# `_displaced_owned_keys` used to read "the manifest row carries a whole-file
# digest" as "we owned this file wholesale, so it displaced nothing". That
# proxy was false in exactly the cases it fired: the function is reached only
# from the merge branch, and the merge branch is reached only when the file on
# disk is NOT ours wholesale. A decline records the OPERATOR's digest under
# `skipped-local-edit` - so a settings.json the installer had REFUSED to touch
# read back as one it owned outright, every top-level key of theirs was
# dropped from the record, and `--uninstall` then deleted them. Nothing in
# this suite merged a tree whose previous run had declined.
def settings_entry(root):
    with open(os.path.join(root, ".claude",
                           ".installer-manifest.json")) as fh:
        return next(f for f in json.load(fh)["files"]
                    if f["path"].endswith("settings.json"))


THEIRS = {"$schema": "https://example.com/mine.json",
          "_generatedBy": "our-internal-tooling", "model": "opus"}

print("\n-- a run that wrote nothing decides nothing --")
_d = tempfile.mkdtemp()
try:
    seed(_d, '{"$schema":')                       # invalid JSON -> decline
    check("a first-run decline exits 3", install(_d).returncode == 3)
    check("a first-run decline records NO displaced_keys (absence, not {})",
          "displaced_keys" not in settings_entry(_d),
          json.dumps(settings_entry(_d)))
finally:
    shutil.rmtree(_d, ignore_errors=True)

def seed_broken(root):
    seed(root, '{"$schema":')                      # unparseable -> decline


def seed_symlink(root):
    shared = os.path.join(root, "shared.json")
    with open(shared, "w") as fh:
        fh.write(json.dumps(THEIRS) + "\n")
    os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
    os.symlink("../shared.json",
               os.path.join(root, ".claude", "settings.json"))


print("\n-- their keys survive a decline, a symlink and a --force --")
for _label, _setup, _argv in (
        ("after an invalid-JSON decline", seed_broken, ()),
        ("after a symlink decline", seed_symlink, ()),
        ("after a --force wholesale write",
         lambda d: seed(d, THEIRS), ("--force",))):
    _d = tempfile.mkdtemp()
    try:
        _setup(_d)
        install(_d, argv=_argv)                    # run 1: decline or force
        if os.path.islink(os.path.join(_d, ".claude", "settings.json")):
            os.unlink(os.path.join(_d, ".claude", "settings.json"))
        if _argv:
            _cur = read(_d)                        # they edit our forced copy
            _cur["model"] = "opus"
            seed(_d, _cur)
        else:
            seed(_d, THEIRS)                       # they fix the file
        _r = install(_d)                           # run 2: merge
        check(f"{_label}: merge succeeds", _r.returncode == 0,
              _r.stderr[-200:])
        check(f"{_label}: their keys are recorded as displaced",
              settings_entry(_d).get("displaced_keys") ==
              {"$schema": THEIRS["$schema"],
               "_generatedBy": THEIRS["_generatedBy"]},
              json.dumps(settings_entry(_d).get("displaced_keys")))
        uninstall(_d)
        _after = read(_d)
        check(f"{_label}: uninstall HANDS BACK their keys",
              _after.get("$schema") == THEIRS["$schema"]
              and _after.get("_generatedBy") == THEIRS["_generatedBy"],
              json.dumps(_after))
    finally:
        shutil.rmtree(_d, ignore_errors=True)

print("\n-- and the other direction: we leave nothing of ours behind --")
_d = tempfile.mkdtemp()
try:
    install(_d)                                    # we CREATE the file
    check("a file we created displaced nothing",
          settings_entry(_d).get("displaced_keys") == {},
          json.dumps(settings_entry(_d).get("displaced_keys")))
    _cur = read(_d)
    _cur["model"] = "opus"
    seed(_d, _cur)
    install(_d)
    uninstall(_d)
    _after = read(_d)
    check("uninstall leaves no installer key behind in a file we created",
          not [k for k in _SETTINGS_OWNED_KEYS if k in _after],
          json.dumps(_after))
finally:
    shutil.rmtree(_d, ignore_errors=True)

_d = tempfile.mkdtemp()
try:
    install(_d)
    os.unlink(os.path.join(_d, ".claude", ".installer-manifest.json"))
    _cur = read(_d)                                # a fresh clone, older stamp
    _cur["_generatedBy"] = "bootstrap-installer (protocol 2.5.0)"
    _cur["model"] = "opus"
    seed(_d, _cur)
    install(_d)
    check("an EARLIER install's version-stamped _generatedBy is not claimed "
          "as theirs",
          settings_entry(_d).get("displaced_keys") == {},
          json.dumps(settings_entry(_d).get("displaced_keys")))
    uninstall(_d)
    check("so uninstall leaves no stale _generatedBy residue",
          "_generatedBy" not in read(_d), json.dumps(read(_d)))
finally:
    shutil.rmtree(_d, ignore_errors=True)


# [WP1] The hook command's placeholder became `"$CLAUDE_PROJECT_DIR"`. A
# re-install over a tree whose manifest is gone (a fresh clone: the manifest
# is gitignored) has no record of which registrations were ours, and the old
# unquoted spelling no longer equals ours - so every earlier registration was
# kept as the operator's, beside ours, and every hook ran TWICE.
print("\n-- [WP1] the unquoted spelling at our own site is ours --")
_d = tempfile.mkdtemp()
try:
    install(_d)
    _s = read(_d)
    for _grps in _s["hooks"].values():
        for _g in _grps:
            for _e in _g["hooks"]:
                _e["command"] = _e["command"].replace(
                    '"$CLAUDE_PROJECT_DIR"/', "$CLAUDE_PROJECT_DIR/")
    _s["model"] = "opus"                 # theirs, so the file must MERGE
    seed(_d, _s)
    os.remove(os.path.join(_d, ".claude", ".installer-manifest.json"))
    _before = len(commands_in(_s))
    _r = install(_d)
    _after = read(_d)
    _cmds = commands_in(_after)
    _sites = [(ev, g.get("matcher"), e["command"])
              for ev, grps in _after["hooks"].items()
              for g in grps for e in g["hooks"]]
    check("a manifest-less re-install does not register any hook twice",
          len(_cmds) == _before and len(set(_sites)) == len(_sites),
          f"{_before} before, {len(_cmds)} after")
    check("and leaves no unquoted spelling of ours behind",
          not [c for c in _cmds if c.startswith("$CLAUDE_PROJECT_DIR/")],
          str(_cmds[:3]))
    check("while the operator's own key survives",
          _after.get("model") == "opus")
finally:
    shutil.rmtree(_d, ignore_errors=True)

# A manifest written before ownership was site-keyed names bare commands, and
# a bare command is retired EVERYWHERE only when we no longer carry it. We
# still carry the script, under the quoted spelling, so the operator's own
# registration of it at a site we never emit must survive.
_OLD = "$CLAUDE_PROJECT_DIR/.claude/hooks/test-gate.sh"
_NEW = '"$CLAUDE_PROJECT_DIR"/.claude/hooks/test-gate.sh'
_merged, _ = _merge_hooks(
    {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": _NEW}]}]},
    {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": _OLD}]}],
     "SessionStart": [{"hooks": [{"type": "command", "command": _OLD}]}]},
    [_OLD])
check("pre-site manifest: the unquoted spelling at OUR site is replaced",
      [e["command"] for g in _merged["PreToolUse"] for e in g["hooks"]]
      == [_NEW], json.dumps(_merged["PreToolUse"]))
check("pre-site manifest: their registration at THEIR site survives",
      _merged.get("SessionStart") == [{"hooks": [
          {"type": "command", "command": _OLD}]}],
      json.dumps(_merged.get("SessionStart")))

# =========================================================================== #
# [WP3 / model assignment] ultracode: on by default, contributed only where
# the operator has no value, removed only while it is still ours
# =========================================================================== #
# Operator decision 2026-10-05: ultracode is ON by default for adopters,
# with an opt-out (workflow.ultracode: false). The model-assignment
# prototype routed it through the owned-key path and overwrote an
# operator's own `false` (fx3); these rows pin the contributed-key path.
print("\n-- [WP3] ultracode: contributed where absent, never displacing --")

UC_OFF = SERVICE + "workflow:\n  ultracode: false\n"
_UC_NOTE = "no install record says this installer wrote it"


def manifest_row(root):
    with open(os.path.join(root, ".claude", ".installer-manifest.json")) as fh:
        m = json.load(fh)
    return next(f for f in m["files"] if f["path"] == ".claude/settings.json")


def _uc_case(label, fn):
    d = tempfile.mkdtemp()
    try:
        fn(d)
    except Exception as exc:          # a crash is a FAIL row, not a traceback
        check(f"{label} (raised {type(exc).__name__}: {exc})", False)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _fresh_default(d):
    r = install(d)
    check("[WP3] fresh install, default config: settings.json sets "
          "\"ultracode\": true, recorded as contributed",
          r.returncode == 0 and read(d).get("ultracode") is True
          and manifest_row(d).get("contributed_keys") == {"ultracode": True},
          r.stdout[-300:] + r.stderr[-300:])
    r = install(d)
    check("[WP3] re-install converges (ok, not an update)",
          r.returncode == 0 and "ok   .claude/settings.json" in r.stdout,
          r.stdout[-400:])
    r = install(d, UC_OFF)
    check("[WP3] the opt-out removes our own value from a file we wrote "
          "wholesale",
          r.returncode == 0 and "ultracode" not in read(d)
          and manifest_row(d).get("contributed_keys") == {},
          json.dumps(read(d))[:300])


def _fresh_off(d):
    r = install(d, UC_OFF)
    check("[WP3] workflow.ultracode: false: no ultracode key at all, and no "
          "note",
          r.returncode == 0 and "ultracode" not in read(d)
          and manifest_row(d).get("contributed_keys") == {}
          and "ultracode" not in r.stderr, r.stderr[-300:])


def _merged_flip(d):
    seed(d, {"model": "sonnet"})
    r = install(d)
    s1 = read(d)
    check("[WP3] merge: ours is added beside the operator's keys and "
          "recorded, with no opt-out note",
          r.returncode == 0 and s1.get("ultracode") is True
          and s1.get("model") == "sonnet"
          and manifest_row(d).get("contributed_keys") == {"ultracode": True}
          and _UC_NOTE not in r.stderr,
          json.dumps(s1)[:300] + r.stderr[-300:])
    r = install(d)
    check("[WP3] merge: a re-install is a fixed point",
          r.returncode == 0 and "ok   .claude/settings.json" in r.stdout
          and read(d) == s1, r.stdout[-300:])
    r = install(d, UC_OFF)
    s2 = read(d)
    check("[WP3] merge: the opt-out removes our value, keeps theirs, says "
          "nothing",
          r.returncode == 0 and "ultracode" not in s2
          and s2.get("model") == "sonnet" and _UC_NOTE not in r.stderr,
          json.dumps(s2)[:300] + r.stderr[-300:])
    install(d)
    r = uninstall(d)
    s3 = read(d) if os.path.exists(
        os.path.join(d, ".claude", "settings.json")) else {}
    check("[WP3] uninstall removes our ultracode and keeps theirs",
          "ultracode" not in s3 and s3.get("model") == "sonnet", str(s3))


def _theirs_false(d):
    seed(d, {"ultracode": False, "model": "sonnet"})
    r = install(d)
    check("[WP3] an operator's own \"ultracode\": false is never displaced "
          "(default config on)",
          r.returncode == 0 and read(d).get("ultracode") is False
          and manifest_row(d).get("contributed_keys") == {}
          and not manifest_row(d).get("displaced_keys")
          and "ultracode" not in r.stderr,
          json.dumps(read(d))[:300] + r.stderr[-300:])
    r = uninstall(d)
    check("[WP3] ... and uninstall leaves it",
          read(d).get("ultracode") is False, json.dumps(read(d))[:300])


def _theirs_true(d):
    seed(d, {"ultracode": True, "model": "sonnet"})
    r = install(d)
    check("[WP3] an operator's own \"ultracode\": true is kept, not claimed, "
          "and the config agrees, so no note",
          read(d).get("ultracode") is True
          and manifest_row(d).get("contributed_keys") == {}
          and _UC_NOTE not in r.stderr, r.stderr[-300:])
    uninstall(d)
    check("[WP3] ... so uninstall leaves it",
          read(d).get("ultracode") is True, json.dumps(read(d))[:300])
    seed(d, {"ultracode": True, "model": "sonnet"})
    r = install(d, UC_OFF)
    check("[WP3] opt-out with a value we do not own: kept, rc 0, and a "
          "warning naming the fix",
          r.returncode == 0 and read(d).get("ultracode") is True
          and _UC_NOTE in r.stderr
          and "Delete the key from .claude/settings.json" in r.stderr,
          r.stderr[-500:])


def _taken_over(d):
    seed(d, {"model": "sonnet"})
    install(d)
    s = read(d)
    s["ultracode"] = False
    seed(d, s)
    r = install(d)
    check("[WP3] an operator who changes OUR value takes it over: kept, no "
          "longer recorded as ours",
          r.returncode == 0 and read(d).get("ultracode") is False
          and manifest_row(d).get("contributed_keys") == {}, r.stderr[-300:])


def _changed_then_uninstalled(d):
    seed(d, {"model": "sonnet"})
    install(d)
    s = read(d)
    s["ultracode"] = False
    seed(d, s)
    uninstall(d)
    check("[WP3] uninstall keeps a value the operator changed from ours "
          "since the last install",
          read(d).get("ultracode") is False and read(d).get("model")
          == "sonnet", json.dumps(read(d))[:300])


def _wt_changed_then_uninstalled(d):
    # [WP3 fix1 TP-08 (d), UC05] The worktree.baseRef we merged into the
    # operator's file, changed by them since the last install: uninstall
    # keeps their value, as it keeps an ultracode they changed.
    seed(d, {"model": "sonnet"})
    install(d)
    s = read(d)
    check("[WP3] (precondition) the merged worktree.baseRef is recorded as "
          "ours", s.get("worktree") == {"baseRef": "head"}
          and manifest_row(d).get("owned_worktree") == {"baseRef": "head"},
          json.dumps(s)[:300])
    s["worktree"]["baseRef"] = "fresh"
    seed(d, s)
    uninstall(d)
    check("[WP3] uninstall keeps a worktree.baseRef the operator changed "
          "from ours since the last install",
          read(d).get("worktree") == {"baseRef": "fresh"}
          and read(d).get("model") == "sonnet", json.dumps(read(d))[:300])


def _fresh_clone(d):
    seed(d, {"model": "sonnet"})
    install(d)
    os.remove(os.path.join(d, ".claude", ".installer-manifest.json"))
    r = install(d, UC_OFF)
    check("[WP3] a fresh clone (no manifest) cannot tell ours from theirs: "
          "the value stays and the opt-out says so",
          r.returncode == 0 and read(d).get("ultracode") is True
          and _UC_NOTE in r.stderr, r.stderr[-500:])


def _decline_carries(d):
    seed(d, {"model": "sonnet"})
    install(d)
    good = read(d)
    seed(d, "{ not json")
    r = install(d)
    check("[WP3] a declined run keeps the contributed record",
          r.returncode == 3
          and manifest_row(d).get("contributed_keys") == {"ultracode": True},
          str(manifest_row(d))[:300])
    seed(d, good)
    r = install(d, UC_OFF)
    check("[WP3] ... so the next run still retires our value",
          r.returncode == 0 and "ultracode" not in read(d)
          and _UC_NOTE not in r.stderr, json.dumps(read(d))[:300])


for _label, _fn in (("fresh default", _fresh_default),
                    ("fresh off", _fresh_off),
                    ("merged flip", _merged_flip),
                    ("theirs false", _theirs_false),
                    ("theirs true", _theirs_true),
                    ("taken over", _taken_over),
                    ("changed, then uninstalled", _changed_then_uninstalled),
                    ("baseRef changed, then uninstalled",
                     _wt_changed_then_uninstalled),
                    ("fresh clone", _fresh_clone),
                    ("decline carries", _decline_carries)):
    _uc_case(f"[WP3] ultracode case: {_label}", _fn)

# Unit: the merge is type-strict, so an operator's `1` is never read as the
# `true` we wrote (Python has 1 == True).
_m, _, _ = _merge_settings({"ultracode": True}, {"ultracode": 1}, [], None,
                           prev_contributed={"ultracode": True},
                           contributed=(_c := {}))
check("[WP3] unit: an operator's 1 is not our true (kept, not owned)",
      _m.get("ultracode") == 1 and type(_m.get("ultracode")) is int
      and _c == {}, f"{_m} {_c}")
_m, _, _ = _merge_settings({}, {"ultracode": True, "model": "x"}, [], None,
                           prev_contributed={"ultracode": True},
                           contributed=(_c := {}))
check("[WP3] unit: ours, recorded, config off: removed",
      "ultracode" not in _m and _m.get("model") == "x" and _c == {}, str(_m))

# A quoted "false" is a truthy string: refused, and read as off.
_cfg, _errs = resolve_config(load_yaml(SERVICE + 'workflow:\n  ultracode: "false"\n'))
check("[WP3] workflow.ultracode: \"false\" (quoted) is refused, and read as "
      "off",
      any("workflow.ultracode must be true or false" in e for e in _errs)
      and _cfg["workflow"]["ultracode"] is False, str(_errs))
_d = tempfile.mkdtemp()
try:
    _r = install(_d, SERVICE + "workflow:\n  ultracode: 1\n")
    check("[WP3] ... and the installer refuses such a config",
          _r.returncode != 0 and not os.path.exists(
              os.path.join(_d, ".claude", "settings.json"))
          and "workflow.ultracode must be true or false"
          in _r.stdout + _r.stderr, (_r.stdout + _r.stderr)[-300:])
finally:
    shutil.rmtree(_d, ignore_errors=True)


def _plan(cfg_text):
    cfg, errs = resolve_config(load_yaml(cfg_text))
    assert not errs, errs
    return {a["path"]: a["body"] for a in build_plan(cfg)}


_on, _off = _plan(SERVICE), _plan(UC_OFF)
_LOOPS_PRE = SERVICE + ("autonomous_modes:\n  loop_mode_enabled: true\n"
                        "  goal_supervised_mode_enabled: true\n"
                        "  queue_mode_enabled: true\n")
_tech_on = _on[".claude/steering/tech.md"]
_tech_off = _off[".claude/steering/tech.md"]
check("[WP3] tech.md, on: says on, what it costs, Sonnet too, and how to "
      "turn it off",
      "**Ultracode:** on (`workflow.ultracode: true`)" in _tech_on
      and "main session, Sonnet sessions included (Haiku ignores it)"
      in _tech_on
      and "never for a subagent" in _tech_on
      and "token cost no constraint, so sessions cost more" in _tech_on
      and "It leaves effort where it was" in _tech_on
      and "`workflow.ultracode: false` and a re-install" in _tech_on
      and "--settings '{\"ultracode\": false}'" in _tech_on, _tech_on[-900:])
check("[WP3] tech.md, off: says off, and how to turn it on for a session",
      "**Ultracode:** off (`workflow.ultracode: false`)" in _tech_off
      and "`claude --effort ultracode`" in _tech_off
      and "**Ultracode:** on" not in _tech_off, _tech_off[-400:])
check("[WP3] the opt-out moves exactly settings.json and tech.md",
      sorted(p for p in _on if _on[p] != _off.get(p))
      == [".claude/settings.json", ".claude/steering/tech.md"]
      and sorted(_on) == sorted(_off))

# Operator decision 2026-10-05: never emit switchModelsOnFlag. On Claude
# Code 2.1.289 a type-invalid value of it (or of `model`) made Claude Code
# skip the WHOLE project settings.json silently, every hook and deny rule
# included (measured), and its documented type differs from the binary's.
# `model` and effort stay the operator's (README, co-ownership).
_unstable = {"switchModelsOnFlag", "model", "effortLevel", "modelSettings"}
check("[WP3] tripwire: the emitted settings.json sets no model, effort or "
      "switchModelsOnFlag key",
      not any(_unstable & set(json.loads(_p[".claude/settings.json"]))
              for _p in (_on, _off, _plan(_LOOPS_PRE))))

with open(os.path.join(ROOT, "plugin", "commands", "bootstrap-apply.md")) as _fh:
    _apply_md = _fh.read()
check("[WP3] bootstrap-apply.md names the kept-ultracode warning class",
      "when `workflow.ultracode` is false but `settings.json`\n   still sets "
      "`\"ultracode\": true` with a value the installer did not\n   write"
      in _apply_md)

# Unattended `claude -p` turns it off, in both wrappers and both routing
# variants (worktree on and off), in the header and the stderr hint.
_LOOPS = SERVICE + ("autonomous_modes:\n  loop_mode_enabled: true\n"
                    "  goal_supervised_mode_enabled: true\n")
for _iso, _txt in (("worktree", _LOOPS),
                   ("no worktree",
                    _LOOPS + "workflow:\n  implementer_isolation: none\n")):
    _p = _plan(_txt)
    for _w in (".claude/loop.sh", ".claude/goal-loop.sh"):
        _b = _p[_w]
        _disp = [ln for ln in _b.splitlines()
                 if ln.startswith("#   claude -p ")]
        check(f"[WP3] {_w} ({_iso}): the dispatch line passes --settings "
              f"'{{\"ultracode\": false}}'",
              len(_disp) == 1
              and "--settings '{\"ultracode\": false}'" in _disp[0], _disp)
        check(f"[WP3] {_w} ({_iso}): the header says why, judge call "
              f"included",
              "keeps\n# ultracode off for an unattended run" in _b
              and "(in goal-loop.sh, the judge call too)" in _b
              and "# The flag outranks the settings files (measured over "
              "the project file,\n# Claude Code 2.1.289)." in _b)
        _hint = [ln for ln in _b.splitlines() if ln.startswith("echo ")
                 and "ultracode" in ln]
        check(f"[WP3] {_w} ({_iso}): the stderr hint passes it too",
              len(_hint) == 1
              and "--settings '{\\\"ultracode\\\": false}'" in _hint[0],
              _hint)
        _f = tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False)
        _f.write(_b)
        _f.close()
        _rc = subprocess.run(["bash", "-n", _f.name]).returncode
        os.unlink(_f.name)
        check(f"[WP3] {_w} ({_iso}): still valid bash (-n)", _rc == 0)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

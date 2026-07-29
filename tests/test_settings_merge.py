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
    _SETTINGS_OWNED_KEYS, _SETTINGS_SHARED_KEYS, _merge_hooks,
    _merge_settings, _settings_mergeable,
)

BIN = os.path.join(ROOT, "bin", "bootstrap-install")
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
    unclaimed = emitted - set(_SETTINGS_OWNED_KEYS) - set(_SETTINGS_SHARED_KEYS)
    check("every top-level key we emit is owned or shared, none unclaimed",
          not unclaimed,
          f"unclaimed: {sorted(unclaimed)} - add it to _SETTINGS_OWNED_KEYS "
          f"or teach _merge_settings to share it")
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
    check("a wholesale write still records owned_hooks / owned_deny",
          any("secrets-gate.sh" in c for c in _entry.get("owned_hooks", []))
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
      _m == OURS_H and _own == ["ours-a"])

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
      _d1 == ["Read(.env*)"] and _h1 == ["ours-a"])

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
    check("--force still writes nothing to stderr", r.stderr == "")
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
          "previous version saved to" in r.stdout, r.stdout[-300:])
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

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

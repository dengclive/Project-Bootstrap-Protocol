#!/usr/bin/env python3
"""Self-contained test suite. Run: python3 tests/test_wiring_verification.py

Covers the two post-install enforcement signals:

  * `verify_wiring()` - does the tree on disk actually dispatch what the plan
    describes, in BOTH directions (emitted-but-unregistered, and
    registered-but-absent).
  * `summary["skipped_security"]` + EXIT_UNENFORCED - a run that declined to
    write a security-critical file must say so on stderr and must not exit 0.

Why these exist: a review found that installing into a project that already
had a `.claude/settings.json` wrote all 11 hooks, registered NONE of them
(settings.json is the only registration site), and exited 0 with an empty
stderr and one SKIP line buried mid-transcript. The installer already computed
`tier == "security-critical"` for that action and wrote it into the manifest;
nothing read it back. Separately, a re-apply that drops a hook from the plan
DELETES the file while a skipped settings.json keeps registering it, so the
harness runs a missing script (rc=127) on every matching call.
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

from pathlib import Path                        # noqa: E402
from installer import (                          # noqa: E402
    EXIT_UNENFORCED, verify_wiring, _registered_commands,
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
"""

RETROFIT = """
mode: "retrofit"
project:
  name: demo
  archetype: service
principles:
  tdd_policy: required
commands:
  test: "true"
retrofit:
  spec_strategy: forward-only
  r08_committed: true
"""


def install(root, cfg_text=SERVICE, argv=()):
    """Run the real CLI. -> CompletedProcess."""
    cfg = os.path.join(root, "cfg.yaml")
    with open(cfg, "w") as fh:
        fh.write(cfg_text)
    return subprocess.run([sys.executable, BIN, "-c", cfg, "-C", root, *argv],
                          capture_output=True, text=True)


def plan_for(cfg_text=SERVICE):
    from defaults import resolve_config
    from installer import build_plan
    from minyaml import load_yaml
    cfg, errs = resolve_config(load_yaml(cfg_text))
    assert not errs, errs
    return build_plan(cfg)


# =========================================================================== #
# End-to-end: the exit-code contract
# =========================================================================== #
print("\n-- exit-code contract --")

_d = tempfile.mkdtemp()
try:
    r = install(_d)
    check("clean greenfield install still exits 0", r.returncode == 0,
          f"rc={r.returncode} stderr={r.stderr[-300:]}")
    check("clean greenfield install writes nothing to stderr",
          r.stderr == "", repr(r.stderr[-300:]))
finally:
    shutil.rmtree(_d, ignore_errors=True)

# A MERGEABLE pre-existing settings.json is no longer skipped - the installer
# merges its hook wiring in (tests/test_settings_merge.py covers the merge
# itself), so this case must NOT trip the enforcement contract.
_d = tempfile.mkdtemp()
try:
    os.makedirs(os.path.join(_d, ".claude"))
    with open(os.path.join(_d, ".claude", "settings.json"), "w") as fh:
        fh.write('{"permissions": {"allow": ["Bash(npm run test:*)"]}}\n')
    r = install(_d)
    check("a mergeable pre-existing settings.json exits 0",
          r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[-300:]}")
    check("a mergeable pre-existing settings.json writes nothing to stderr",
          r.stderr == "", repr(r.stderr[-300:]))
    check("enforcement is verifiably present after the merge",
          verify_wiring(Path(_d), plan_for()) == [],
          str(verify_wiring(Path(_d), plan_for())))
finally:
    shutil.rmtree(_d, ignore_errors=True)

# An UNMERGEABLE settings.json is where the contract still bites: we decline
# rather than guess at operator content, so nothing gets registered.
_d = tempfile.mkdtemp()
try:
    os.makedirs(os.path.join(_d, ".claude"))
    original = '{"permissions": "not-an-object"}\n'
    with open(os.path.join(_d, ".claude", "settings.json"), "w") as fh:
        fh.write(original)
    r = install(_d)
    check("an unmergeable settings.json does not exit 0",
          r.returncode == EXIT_UNENFORCED, f"rc={r.returncode}")
    check("the refusal is on STDERR and names the reason",
          "settings.json" in r.stderr and "permissions" in r.stderr
          and "security-critical" in r.stderr, repr(r.stderr[:400]))
    check("the unregistered hooks are each named on stderr",
          "secrets-gate.sh was emitted but is NOT registered" in r.stderr)
    check("an unmergeable operator file is left untouched",
          open(os.path.join(_d, ".claude", "settings.json")).read()
          == original)
    # --force is the documented escape hatch and must return to a clean 0.
    r2 = install(_d, argv=("--force",))
    check("--force restores enforcement and exits 0", r2.returncode == 0,
          f"rc={r2.returncode} stderr={r2.stderr[-300:]}")
    check("--force run writes nothing to stderr", r2.stderr == "")
finally:
    shutil.rmtree(_d, ignore_errors=True)

# --dry-run writes nothing, so it must not claim the tree is unenforced.
_d = tempfile.mkdtemp()
try:
    os.makedirs(os.path.join(_d, ".claude"))
    with open(os.path.join(_d, ".claude", "settings.json"), "w") as fh:
        fh.write("{}\n")
    r = install(_d, argv=("--dry-run",))
    check("--dry-run over an unenforced tree still exits 0",
          r.returncode == 0, f"rc={r.returncode}")
    check("--dry-run writes nothing to stderr", r.stderr == "")
finally:
    shutil.rmtree(_d, ignore_errors=True)

# A pre-placed stub at a hook path: the TIER signal catches this one; the
# wiring check structurally cannot, because the hook is registered and does
# exist. Both signals are needed, and this pins the division of labour.
_d = tempfile.mkdtemp()
try:
    os.makedirs(os.path.join(_d, ".claude", "hooks"))
    for name in ("secrets-gate", "dependency-gate"):
        with open(os.path.join(_d, ".claude", "hooks", f"{name}.sh"),
                  "w") as fh:
            fh.write("#!/usr/bin/env bash\nexit 0\n")
    r = install(_d)
    check("a stub at a security-critical hook path does not exit 0",
          r.returncode == EXIT_UNENFORCED, f"rc={r.returncode}")
    check("both stubbed hooks are named on stderr",
          "secrets-gate.sh" in r.stderr and "dependency-gate.sh" in r.stderr)
    check("the wiring check alone does NOT see a stubbed body "
          "(it is registered and present)",
          verify_wiring(Path(_d), plan_for()) == [],
          str(verify_wiring(Path(_d), plan_for())))
finally:
    shutil.rmtree(_d, ignore_errors=True)

# Removal and registration used to be non-transactional: dropping a hook from
# the plan deleted the file while a SKIPPED settings.json kept registering it,
# so the harness ran a missing script on every match. The merge de-registers
# in the same pass, so the dangling reference can no longer arise - this pins
# that, and the backward direction of verify_wiring is unit-tested below.
_d = tempfile.mkdtemp()
try:
    install(_d)
    sp = os.path.join(_d, ".claude", "settings.json")
    s = json.load(open(sp))
    s.setdefault("permissions", {}).setdefault("allow", []).append("Bash(ls)")
    json.dump(s, open(sp, "w"), indent=2)          # ordinary operator edit
    r = install(_d, cfg_text=SERVICE.replace("tdd_policy: required",
                                             "tdd_policy: off"))
    after = open(sp).read()
    check("dropping a hook after an operator edit no longer dangles",
          r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[-400:]}")
    check("tdd-gate.sh really was removed from disk",
          not os.path.exists(os.path.join(_d, ".claude", "hooks",
                                          "tdd-gate.sh")))
    check("the dropped hook was de-registered in the same pass",
          "tdd-gate" not in after)
    check("the operator's edit survived the de-registration",
          "Bash(ls)" in after)
finally:
    shutil.rmtree(_d, ignore_errors=True)

# Retrofit shares apply_plan, so it must behave identically both ways.
_d = tempfile.mkdtemp()
try:
    r = install(_d, cfg_text=RETROFIT)
    check("clean retrofit install exits 0", r.returncode == 0,
          f"rc={r.returncode} stderr={r.stderr[-300:]}")
finally:
    shutil.rmtree(_d, ignore_errors=True)

_d = tempfile.mkdtemp()
try:
    os.makedirs(os.path.join(_d, ".claude"))
    with open(os.path.join(_d, ".claude", "settings.json"), "w") as fh:
        fh.write('{"model": "opus"}\n')
    r = install(_d, cfg_text=RETROFIT)
    check("retrofit over a pre-existing settings.json merges and exits 0",
          r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[-300:]}")
    check("retrofit preserves the operator's key",
          json.load(open(os.path.join(_d, ".claude",
                                      "settings.json"))).get("model")
          == "opus")
finally:
    shutil.rmtree(_d, ignore_errors=True)


# =========================================================================== #
# verify_wiring() as a unit - shape robustness on an operator-authored file
# =========================================================================== #
print("\n-- verify_wiring() shapes --")

HOOK = ".claude/hooks/secrets-gate.sh"
PLAN = [{"path": HOOK, "body": "", "mode": 0o755, "kind": "hook"},
        {"path": ".claude/settings.json", "body": "", "mode": 0o644,
         "kind": "settings"}]


def tree(settings, hooks=(HOOK,)):
    """Materialise a minimal tree; returns the root. Caller removes it."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, ".claude", "hooks"), exist_ok=True)
    for h in hooks:
        p = os.path.join(d, *h.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write("#!/usr/bin/env bash\n")
    if settings is not None:
        with open(os.path.join(d, ".claude", "settings.json"), "w") as fh:
            fh.write(settings if isinstance(settings, str)
                     else json.dumps(settings))
    return d


def wiring(settings, hooks=(HOOK,), plan=None):
    d = tree(settings, hooks)
    try:
        return verify_wiring(Path(d), PLAN if plan is None else plan)
    finally:
        shutil.rmtree(d, ignore_errors=True)


GOOD = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
    {"type": "command",
     "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/secrets-gate.sh"}]}]}}

check("a coherent tree reports no problems", wiring(GOOD) == [])

check("an emitted hook that is registered nowhere is reported",
      any("NOT registered" in p for p in wiring({"hooks": {}})))

check("a registered hook that is absent from disk is reported",
      any("not on disk" in p for p in wiring(GOOD, hooks=())))

check("an absent settings.json is reported",
      any("absent" in p for p in wiring(None)))

check("a settings.json that is not JSON is reported, not raised",
      any("could not be read as JSON" in p for p in wiring("not json {{")))

check("a settings.json that is a JSON list is reported, not raised",
      any("is a list, not an object" in p for p in wiring("[]")))

# An operator may register their own hooks. A command we cannot resolve to a
# path under the project is left alone rather than guessed at.
_own = {"hooks": {"PreToolUse": [{"hooks": [
    {"type": "command", "command": "/usr/local/bin/my-guard"},
    {"type": "command", "command": "echo hi"},
    {"type": "command",
     "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/secrets-gate.sh"}]}]}}
check("commands outside $CLAUDE_PROJECT_DIR are not flagged as missing",
      wiring(_own) == [], str(wiring(_own)))

# Round-6 F3. A hook `command` is a SHELL COMMAND LINE, not a path. Taking the
# whole string as one reported a healthy install as unenforced and exited 3 -
# and plugin/commands/bootstrap-apply.md acts on that exit code, so operators
# were told a good install had failed. The detector is only worth having if it
# is quiet when nothing is wrong.
def _beside_ours(command):
    """Our own registration, plus one of the operator's alongside it - the
    shape a real merged settings.json has."""
    merged = json.loads(json.dumps(GOOD))
    merged["hooks"]["PostToolUse"] = [{"matcher": "Write", "hooks": [
        {"type": "command", "command": command}]}]
    return merged


_BOTH = (HOOK, ".claude/hooks/fmt.sh")
_argv = _beside_ours("$CLAUDE_PROJECT_DIR/.claude/hooks/fmt.sh --fix")
check("an operator hook that takes ARGUMENTS is not a false alarm",
      wiring(_argv, hooks=_BOTH) == [], str(wiring(_argv, hooks=_BOTH)))

_quoted = _beside_ours("$CLAUDE_PROJECT_DIR/.claude/hooks/fmt.sh 'a b.txt'")
check("quoted arguments resolve to the same path",
      wiring(_quoted, hooks=_BOTH) == [], str(wiring(_quoted, hooks=_BOTH)))

# ...and the detector must still fire when the script really is missing.
_gone = _beside_ours("$CLAUDE_PROJECT_DIR/.claude/hooks/gone.sh --fix")
_p = wiring(_gone)
check("a missing script is still reported when the command has arguments",
      any("not on disk" in p for p in _p), str(_p))
check("and it is named by PATH, without the arguments",
      any(".claude/hooks/gone.sh," in p for p in _p), str(_p))

# The resolver must tokenise the way the SHELL does, not the way shlex.split
# does. Each of these runs a script that exists; resolving the whole word (or
# stopping at the wrong character) reports a healthy tree as broken.
for _label, _suffix in (
        ("semicolon", "; echo done"),
        ("and-list", " && echo done"),
        ("pipeline", " | tee log"),
        ("redirect", " 2>/dev/null"),
        ("hash in the filename", "#x"),
        ("plain argument", " --fix"),
        ("quoted argument", " 'a b.txt'")):
    _name = ".claude/hooks/fmt.sh" + ("#x" if "hash" in _label else "")
    _cmd = "$CLAUDE_PROJECT_DIR/.claude/hooks/fmt.sh" + _suffix
    _s = _beside_ours(_cmd)
    check(f"resolver follows the shell: {_label}",
          wiring(_s, hooks=(HOOK, _name)) == [],
          str(wiring(_s, hooks=(HOOK, _name))))

check("an unparseable command line is left alone, not reported",
      wiring({"hooks": {"Stop": [{"hooks": [
          {"type": "command",
           "command": '$CLAUDE_PROJECT_DIR/x.sh "unbalanced'}]}]}},
             plan=[]) == [])

# Malformed nesting must degrade to "nothing registered", never raise.
for label, shape in (
        ("hooks is a list", {"hooks": []}),
        ("event maps to a string", {"hooks": {"PreToolUse": "x"}}),
        ("group is not a dict", {"hooks": {"PreToolUse": [7]}}),
        ("group.hooks is a dict", {"hooks": {"PreToolUse": [{"hooks": {}}]}}),
        ("entry is not a dict", {"hooks": {"PreToolUse": [{"hooks": [1]}]}}),
        ("command is not a string",
         {"hooks": {"PreToolUse": [{"hooks": [{"command": 3}]}]}}),
        ("no hooks key at all", {"model": "opus"}),
):
    try:
        out = wiring(shape)
        ok = any("NOT registered" in p for p in out)
    except Exception as e:                       # noqa: BLE001
        ok = False
        out = f"RAISED {e!r}"
    check(f"malformed settings degrades safely: {label}", ok, str(out))

check("_registered_commands returns [] for a shapeless mapping",
      _registered_commands({"hooks": {"X": [{"hooks": [{}]}]}}) == [])

# A plan with no hooks has nothing to verify, even with no settings.json.
check("a plan carrying no hooks reports nothing",
      verify_wiring(Path(tempfile.gettempdir()), []) == [])

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

#!/usr/bin/env python3
"""R-9 - the IC gate + 2.1.0 release identity.

Spec: .claude/specs/bootstrap-v2/requirements.md (AC-9-1..AC-9-5).
- lib/ic_checks.py verifies IC-1..IC-7; the installer refuses to write
  gate_substrate: "sdk-callable" unless every check passes.
- BOOTSTRAP_IC_FORCE_FAIL=<IC> is the documented TEST-ONLY override; per
  the BOOTSTRAP_TEST_FORCE_PROMPT asymmetry it can only force REFUSING.

Run: python3 tests/test_ic_gate.py
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

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


BASE = """project:
  name: icgate
  archetype: ai-agent
autonomous_modes:
  loop_mode_enabled: true
  goal_supervised_mode_enabled: true
  queue_mode_enabled: true
principles:
  tdd_policy: required
commands:
  test: "true"
  lint: "true"
"""
SDK = BASE + 'gate_substrate: "sdk-callable"\n'

ALL_ICS = ["IC-1", "IC-2", "IC-3", "IC-4", "IC-5", "IC-6", "IC-7"]

# ---- module-level API ----------------------------------------------------- #
import ic_checks  # noqa: E402

results = ic_checks.run_ic_checks()
check("run_ic_checks returns the seven ICs in order",
      list(results) == ALL_ICS, repr(list(results)))
check("all IC self-checks pass on the live tree",
      ic_checks.all_passed(results),
      repr({k: v for k, v in results.items() if not v["passed"]}))
check("each result carries title/passed/detail",
      all({"title", "passed", "detail"} <= set(r) for r in
          results.values()))

os.environ["BOOTSTRAP_IC_FORCE_FAIL"] = "IC-5"
forced = ic_checks.run_ic_checks()
del os.environ["BOOTSTRAP_IC_FORCE_FAIL"]
check("FORCE_FAIL forces exactly the named check to fail",
      not forced["IC-5"]["passed"]
      and all(forced[ic]["passed"] for ic in ALL_ICS if ic != "IC-5"))
check("FORCE_FAIL detail says it can only force refusing",
      "can only force refusing" in forced["IC-5"]["detail"])

# ---- AC-9-3: --ic-checks CLI (CI-assertable form) ------------------------- #
r = subprocess.run([sys.executable, BIN, "--ic-checks"],
                   capture_output=True, text=True)
check("AC-9-3: --ic-checks exits 0 when green", r.returncode == 0,
      r.stderr)
try:
    payload = json.loads(r.stdout)
    check("AC-9-3: --ic-checks prints the JSON checklist",
          list(payload) == ALL_ICS
          and all(payload[ic]["passed"] for ic in ALL_ICS))
except json.JSONDecodeError as e:
    check("AC-9-3: --ic-checks prints the JSON checklist", False, str(e))

r = subprocess.run([sys.executable, BIN, "--ic-checks"],
                   capture_output=True, text=True,
                   env={**os.environ, "BOOTSTRAP_IC_FORCE_FAIL": "IC-2"})
check("AC-9-3: --ic-checks exits non-zero on any failure",
      r.returncode == 1)

# ---- AC-9-2: green checks => "sdk-callable" written ----------------------- #
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(SDK)
    r = subprocess.run([sys.executable, BIN, "-C", d],
                       capture_output=True, text=True)
    check("AC-9-2: sdk-callable install succeeds when checks green",
          r.returncode == 0, r.stderr)
    check("AC-9-2: grant is announced loudly",
          "IC gate: all IC-1..IC-7 self-checks passed" in r.stdout)
    state = json.load(open(os.path.join(d, ".claude",
                                        ".bootstrap-state.json")))
    check('AC-9-2: state records gate_substrate "sdk-callable"',
          state.get("gate_substrate") == "sdk-callable")
    check("AC-9-5: state records protocol 2.4.0",
          state.get("bootstrap_protocol_version") == "2.4.0")
finally:
    shutil.rmtree(d, ignore_errors=True)

# ---- AC-9-1: failing check => loud refusal, state retains "shell" --------- #
d = tempfile.mkdtemp()
try:
    # First a shell install so a state file exists to "retain".
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(BASE)
    r = subprocess.run([sys.executable, BIN, "-C", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    state_path = os.path.join(d, ".claude", ".bootstrap-state.json")
    assert json.load(open(state_path))["gate_substrate"] == "shell"

    # Now request sdk-callable with a forced IC failure.
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(SDK)
    r = subprocess.run([sys.executable, BIN, "-C", d],
                       capture_output=True, text=True,
                       env={**os.environ,
                            "BOOTSTRAP_IC_FORCE_FAIL": "IC-6"})
    check("AC-9-1: refused with non-zero exit", r.returncode == 2,
          f"rc={r.returncode}")
    check("AC-9-1: refusal is loud and names the failing check",
          "Install REFUSED" in r.stderr and "IC-6" in r.stderr, r.stderr)
    state = json.load(open(state_path))
    check('AC-9-1: state file retains "shell"',
          state.get("gate_substrate") == "shell")

    # Same refusal applies under --dry-run (no misleading previews).
    r = subprocess.run([sys.executable, BIN, "-C", d, "--dry-run"],
                       capture_output=True, text=True,
                       env={**os.environ,
                            "BOOTSTRAP_IC_FORCE_FAIL": "IC-6"})
    check("AC-9-1: --dry-run refuses identically", r.returncode == 2)
finally:
    shutil.rmtree(d, ignore_errors=True)

# ---- config validation: enum + retrofit exclusion ------------------------- #
from minyaml import load_yaml      # noqa: E402
from defaults import resolve_config  # noqa: E402

_, errs = resolve_config(load_yaml(BASE + "gate_substrate: bogus\n"))
check("config: bogus gate_substrate rejected",
      any("gate_substrate" in e for e in errs), repr(errs))
RETRO_SDK = """mode: "retrofit"
project:
  name: r-ic
  archetype: service
gate_substrate: "sdk-callable"
retrofit:
  spec_strategy: "forward-only"
  retrofit_active: true
  r08_committed: true
"""
_, errs = resolve_config(load_yaml(RETRO_SDK))
check("config: sdk-callable refused in retrofit mode",
      any("retrofit" in e and "sdk-callable" in e for e in errs),
      repr(errs))
_, errs = resolve_config(load_yaml(BASE))
check("config: default stays shell with no errors", errs == [])

# ---- AC-9-4: runtime-floor startup check ---------------------------------- #
def install_with_fake_claude(version_output):
    """Run a shell install with a PATH-injected fake `claude`."""
    d = tempfile.mkdtemp()
    fake = tempfile.mkdtemp()
    try:
        if version_output is not None:
            p = os.path.join(fake, "claude")
            with open(p, "w") as fh:
                fh.write(f"#!/bin/sh\necho '{version_output}'\n")
            os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
        open(os.path.join(d, "bootstrap.config.yaml"), "w").write(BASE)
        env = {**os.environ,
               "PATH": fake + os.pathsep + os.environ.get("PATH", "")}
        if version_output is None:
            # Empty PATH prefix + a PATH without any real claude: build a
            # minimal PATH holding just python's dir so `which claude`
            # misses. (The installer itself is invoked by absolute path.)
            env["PATH"] = fake
        return subprocess.run([sys.executable, BIN, "-C", d],
                              capture_output=True, text=True, env=env)
    finally:
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(fake, ignore_errors=True)


r = install_with_fake_claude("2.1.214 (Claude Code)")
check("AC-9-4: detected version >= floor is logged, no warning",
      "Claude Code runtime detected: 2.1.214" in r.stdout
      and "BELOW the seam runtime floor" not in r.stderr, r.stderr)
r = install_with_fake_claude("2.1.100 (Claude Code)")
check("AC-9-4: version below floor warns loudly",
      "BELOW the seam runtime floor 2.1.210" in r.stderr, r.stderr)
r = install_with_fake_claude(None)
check("AC-9-4: undetectable CLI warns loudly (never silent)",
      "undetectable" in r.stderr, r.stderr)

# ---- AC-9-5: release identity --------------------------------------------- #
import installer   # noqa: E402
import templates   # noqa: E402

check("AC-9-5: installer PROTOCOL_VERSION is 2.4.0",
      installer.PROTOCOL_VERSION == "2.4.0")
check("AC-9-5: templates PROTOCOL_VERSION is 2.4.0",
      templates.PROTOCOL_VERSION == "2.4.0")
check("AC-9-5: RETROFIT_PROTOCOL_VERSION untouched (1.6.2)",
      installer.RETROFIT_PROTOCOL_VERSION == "1.6.2")
check("AC-9-5: seam runtime floor constant is 2.1.210",
      installer.RUNTIME_FLOOR == "2.1.210")
changelog = open(os.path.join(ROOT, "docs", "changelog.md")).read()
check("AC-9-5: changelog carries the 2.0.0 -> 2.1.0 entry",
      "2.0.0 → 2.1.0" in changelog)
check("R6 (2.2.0): changelog carries the 2.1.0 -> 2.2.0 entry",
      "2.1.0 → 2.2.0" in changelog)
check("v2.4.0 fold: changelog carries the 2.2.0 -> 2.4.0 entry",
      "2.2.0 → 2.4.0" in changelog)
conformance = open(os.path.join(
    ROOT, "Bootstrap-Protocol-v2-0-0.md")).read()
check("AC-9-5: conformance note marks the substrate operative",
      "[2.1.0 update — substrate OPERATIVE]" in conformance)

# ---- Code-review fix regressions ---------------------------------------- #
# FORCE_FAIL typo/unknown value must RAISE (never silently no-op into a
# real grant - the safety-critical direction).
try:
    ic_checks.run_ic_checks.__wrapped__  # noqa: B018 (attr probe only)
except AttributeError:
    pass
for bad in ("IC5", "ic-2", "IC-8"):
    os.environ["BOOTSTRAP_IC_FORCE_FAIL"] = bad
    try:
        ic_checks.run_ic_checks()
        check(f"fix: FORCE_FAIL={bad!r} unknown value raises", False,
              "no raise")
    except ValueError:
        check(f"fix: FORCE_FAIL={bad!r} unknown value raises", True)
    finally:
        del os.environ["BOOTSTRAP_IC_FORCE_FAIL"]
# Whitespace is tolerated (stripped to a valid name), not an error.
os.environ["BOOTSTRAP_IC_FORCE_FAIL"] = "IC-2 "
try:
    check("fix: FORCE_FAIL whitespace stripped to a valid force",
          not ic_checks.run_ic_checks()["IC-2"]["passed"])
finally:
    del os.environ["BOOTSTRAP_IC_FORCE_FAIL"]

# --print-config must run the IC gate: an sdk-callable config the install
# would refuse must not validate clean here (verdict consistency).
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(SDK)
    r = subprocess.run([sys.executable, BIN, "-C", d, "--print-config"],
                       capture_output=True, text=True,
                       env={**os.environ, "BOOTSTRAP_IC_FORCE_FAIL": "IC-6"})
    check("fix: --print-config refuses an sdk-callable config on IC fail",
          r.returncode == 2 and "Install REFUSED" in r.stderr, r.stderr)
    r = subprocess.run([sys.executable, BIN, "-C", d, "--print-config"],
                       capture_output=True, text=True)
    check("fix: --print-config succeeds when the IC gate is green",
          r.returncode == 0 and '"gate_substrate"' in r.stdout)
finally:
    shutil.rmtree(d, ignore_errors=True)

# Downgrade warning: an existing sdk-callable state re-applied with a
# shell config warns loudly (and downgrades).
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(SDK)
    assert subprocess.run([sys.executable, BIN, "-C", d],
                          capture_output=True, text=True).returncode == 0
    sp = os.path.join(d, ".claude", ".bootstrap-state.json")
    assert json.load(open(sp))["gate_substrate"] == "sdk-callable"
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(BASE)
    r = subprocess.run([sys.executable, BIN, "-C", d],
                       capture_output=True, text=True)
    check("fix: substrate downgrade on re-apply warns loudly",
          "downgraded" in r.stderr and r.returncode == 0, r.stderr)
    check("fix: downgrade actually writes shell",
          json.load(open(sp))["gate_substrate"] == "shell")
finally:
    shutil.rmtree(d, ignore_errors=True)

# Write-side enforcement: a programmatic caller reaching apply_plan with an
# sdk-callable cfg but no gate-clear must NOT persist sdk-callable.
d = tempfile.mkdtemp()
try:
    import installer as _inst
    cfg_sdk, _e = resolve_config(load_yaml(SDK))
    assert not _e, _e
    plan = _inst.build_plan(cfg_sdk)
    _inst.apply_plan(Path(d), plan, cfg_sdk, dry=False, force=False)
    st = json.load(open(os.path.join(d, ".claude",
                                     ".bootstrap-state.json")))
    check("fix: ungated apply_plan cannot persist sdk-callable",
          st["gate_substrate"] == "shell")
finally:
    shutil.rmtree(d, ignore_errors=True)

# Stale-file cleanup coverage (retrofit-over-greenfield): gates.py is
# unlinked from disk, leaves the manifest, the state is reconciled to
# shell, and a hand-edited stale file is PRESERVED (L-1).
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(SDK)
    subprocess.run([sys.executable, BIN, "-C", d],
                   capture_output=True, text=True)
    gp = os.path.join(d, ".claude", "sdk_gates", "gates.py")
    assert os.path.isfile(gp), "greenfield should emit gates.py"
    # Hand-edit a droppable non-security file to prove L-1 preservation.
    handedit = os.path.join(d, ".claude", "loop-config.md")
    open(handedit, "a").write("\n# operator note\n")
    RETRO = """mode: "retrofit"
project:
  name: x
  archetype: ai-agent
secrets:
  enabled: true
deps:
  enabled: true
  approved: []
commands: {test: "true", lint: "true"}
retrofit:
  spec_strategy: forward-only
  legacy_allowlist: ["src/**"]
  retrofit_active: true
  r08_committed: true
"""
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(RETRO)
    r = subprocess.run([sys.executable, BIN, "-C", d],
                       capture_output=True, text=True)
    check("fix: stale gates.py unlinked from disk on retrofit re-apply",
          not os.path.isfile(gp))
    man = json.load(open(os.path.join(d, ".claude",
                                      ".installer-manifest.json")))
    check("fix: gates.py leaves the manifest (no orphan)",
          not any("sdk_gates" in f["path"] for f in man["files"]))
    check("fix: removed count reported", "removed=" in r.stdout
          and "removed=0" not in r.stdout)
    st = json.load(open(os.path.join(d, ".claude",
                                     ".bootstrap-state.json")))
    check("fix: orphaned sdk-callable state reconciled to shell",
          st["gate_substrate"] == "shell")
    check("fix: hand-edited dropped file PRESERVED (L-1)",
          os.path.isfile(handedit)
          and "operator note" in open(handedit).read())
    # --dry-run previews the removal without deleting.
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(SDK)
    subprocess.run([sys.executable, BIN, "-C", d],
                   capture_output=True, text=True)   # restore greenfield
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(RETRO)
    r = subprocess.run([sys.executable, BIN, "-C", d, "--dry-run"],
                       capture_output=True, text=True)
    check("fix: --dry-run PREVIEWS the removal, does not delete",
          "REMOVE (dry run)" in r.stdout
          and os.path.isfile(gp))
finally:
    shutil.rmtree(d, ignore_errors=True)

# AC-9-4 anchoring: a banner-preamble version must not fool the parse.
r = install_with_fake_claude("Update available 9.9.9 -> 10.0.0\n"
                             "2.1.100 (Claude Code)")
check("fix: runtime-floor parse ignores an update-banner version",
      "Claude Code runtime detected: 2.1.100" in r.stdout
      and "BELOW the seam runtime floor" in r.stderr, r.stdout + r.stderr)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

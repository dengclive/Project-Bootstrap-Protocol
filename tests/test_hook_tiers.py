#!/usr/bin/env python3
"""R-5 (IC-7) — machine-readable hook tiers in the installer manifest.

Spec: .claude/specs/bootstrap-v2/requirements.md (AC-5-1..AC-5-3).
Tier membership is the seam SS7.2 contract-level list (shell-era baseline):
  security-critical : secrets-gate, spec-gate-commit, dependency-gate,
                      test-gate, eval-gate, tdd-gate, format-lint-gate,
                      settings.json
  autonomy-critical : drift-detector-loop-cooperation,
                      iteration-summary-enforcement
  non-critical      : everything else; spec-gate-entry DELIBERATELY so.
The manifest is an apply()-time artifact outside the golden surface [SR-07]
- coverage here is behavioral only.

Run: python3 tests/test_hook_tiers.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

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


FULL = """project:
  name: tiers
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

# The seam SS7.2 lists, restated here as the CONTRACT the manifest must
# match (AC-5-2). A change here is a seam event, not a test tweak.
SEAM_SECURITY = {
    ".claude/hooks/secrets-gate.sh", ".claude/hooks/spec-gate-commit.sh",
    ".claude/hooks/dependency-gate.sh", ".claude/hooks/test-gate.sh",
    ".claude/hooks/eval-gate.sh", ".claude/hooks/tdd-gate.sh",
    ".claude/hooks/format-lint-gate.sh", ".claude/settings.json",
}
SEAM_AUTONOMY = {
    ".claude/hooks/drift-detector-loop-cooperation.sh",
    ".claude/hooks/iteration-summary-enforcement.sh",
}
VALID_TIERS = {"security-critical", "autonomy-critical", "non-critical"}

d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(FULL)
    r = subprocess.run([sys.executable, BIN, "-C", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    manifest = json.load(open(os.path.join(d, ".claude",
                                           ".installer-manifest.json")))
    files = manifest["files"]

    # AC-5-1: every entry carries a valid tier (hooks, settings, and all
    # other manifest-tracked files - absent-means-guess is not allowed).
    missing = [f["path"] for f in files if f.get("tier") not in VALID_TIERS]
    check("AC-5-1: every manifest entry carries a valid tier",
          missing == [], repr(missing))

    # AC-5-3 mechanism: derive the sets FROM the manifest, no hard-coding.
    derived_sec = {f["path"] for f in files
                   if f.get("tier") == "security-critical"}
    derived_aut = {f["path"] for f in files
                   if f.get("tier") == "autonomy-critical"}

    # AC-5-2: membership matches the seam SS7.2 lists exactly.
    check("AC-5-2: security-critical set matches seam SS7.2 exactly",
          derived_sec == SEAM_SECURITY,
          f"extra={derived_sec - SEAM_SECURITY} "
          f"missing={SEAM_SECURITY - derived_sec}")
    check("AC-5-2: autonomy-critical set matches seam SS7.2 exactly",
          derived_aut == SEAM_AUTONOMY,
          f"extra={derived_aut - SEAM_AUTONOMY} "
          f"missing={SEAM_AUTONOMY - derived_aut}")
    check("AC-5-2: settings.json is in the security-critical set",
          ".claude/settings.json" in derived_sec)
    entry = next(f for f in files
                 if f["path"] == ".claude/hooks/spec-gate-entry.sh")
    check("AC-5-2: spec-gate-entry is DELIBERATELY non-critical (warn-tier)",
          entry.get("tier") == "non-critical")

    # AC-5-3: a downstream reader can act on the derived set without
    # hard-coding names - every derived security path is a real emitted
    # file with a digest to verify against.
    check("AC-5-3: every derived security-critical entry is digest-tracked",
          all("digest" in f for f in files
              if f.get("tier") == "security-critical"))
    check("AC-5-3: derived sets are disjoint",
          not (derived_sec & derived_aut))
finally:
    shutil.rmtree(d, ignore_errors=True)

# Non-autonomous config: the autonomy-critical hooks are not emitted, and
# the security set is the subset of SS7.2 members actually present.
d = tempfile.mkdtemp()
try:
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(
        "project:\n  name: plain\n  archetype: service\n")
    subprocess.run([sys.executable, BIN, "-C", d],
                   capture_output=True, text=True)
    manifest = json.load(open(os.path.join(d, ".claude",
                                           ".installer-manifest.json")))
    files = manifest["files"]
    derived_sec = {f["path"] for f in files
                   if f.get("tier") == "security-critical"}
    present = {f["path"] for f in files}
    check("subset: security set == SS7.2 members present in this install",
          derived_sec == (SEAM_SECURITY & present),
          repr(derived_sec ^ (SEAM_SECURITY & present)))
    check("subset: no autonomy-critical entries without autonomous modes",
          not any(f.get("tier") == "autonomy-critical" for f in files))
finally:
    shutil.rmtree(d, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

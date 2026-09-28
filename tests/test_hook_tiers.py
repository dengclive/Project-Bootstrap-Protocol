#!/usr/bin/env python3
"""R-5 (IC-7) — machine-readable hook tiers in the installer manifest.

Spec: .claude/specs/bootstrap-v2/requirements.md (AC-5-1..AC-5-3).
Tier membership is the seam SS7.2 contract-level list (shell-era baseline):
  security-critical : secrets-gate, dependency-gate, settings.json,
                      sdk_gates/gates.py (when emitted)
  autonomy-critical : drift-detector-loop-cooperation,
                      iteration-summary-enforcement
  non-critical      : everything else; spec-gate-entry DELIBERATELY so,
                      and [WP1 / D4 (a), 2026-09-27] the quality gates
                      spec-gate-commit, test-gate, eval-gate, tdd-gate and
                      format-lint-gate.
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


FULL = """gate_substrate: "sdk-callable"
project:
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
    # [WP1 / D4 (a), owner decision 2026-09-27] spec-gate-commit, test-gate,
    # eval-gate, tdd-gate and format-lint-gate LEFT this set (seam SS7.2
    # removal, a seam_version event). They are asserted non-critical below.
    ".claude/hooks/secrets-gate.sh", ".claude/hooks/dependency-gate.sh",
    ".claude/settings.json",
    # Milestone B (seam §9): the SDK gate module joins the security-
    # critical set IN THE SAME RELEASE that emits it - a seam_version
    # event landing with the substrate-release seam bump, recorded here
    # deliberately (this is a contract edit, not a test tweak).
    ".claude/sdk_gates/gates.py",
}
RETIERED = {
    ".claude/hooks/spec-gate-commit.sh", ".claude/hooks/test-gate.sh",
    ".claude/hooks/eval-gate.sh", ".claude/hooks/tdd-gate.sh",
    ".claude/hooks/format-lint-gate.sh",
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
    _tiers = {f["path"]: f.get("tier") for f in files}
    check("D4: every re-tiered quality gate is emitted by this fixture",
          RETIERED <= set(_tiers), repr(RETIERED - set(_tiers)))
    check("D4: the re-tiered quality gates are non-critical",
          all(_tiers.get(p) == "non-critical" for p in RETIERED),
          repr({p: _tiers.get(p) for p in RETIERED}))

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

# [WP1 / D4 (a)] A hand edit to a re-tiered quality gate SURVIVES a
# re-install: SKIP notice, edit preserved, rc=0 (before the re-tier, rc=3
# "this install does not enforce"). The security gates keep rc=3 - the
# control rows, so an over-broad demotion cannot pass this block.
BIN_CFG = FULL.replace('gate_substrate: "sdk-callable"\n', "", 1)
d0 = tempfile.mkdtemp()
try:
    open(os.path.join(d0, "bootstrap.config.yaml"), "w").write(BIN_CFG)
    r = subprocess.run([sys.executable, BIN, "-C", d0],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for rel in sorted(RETIERED) + [".claude/hooks/secrets-gate.sh",
                                   ".claude/hooks/dependency-gate.sh"]:
        d = tempfile.mkdtemp()
        try:
            shutil.rmtree(d)
            shutil.copytree(d0, d, symlinks=True)
            path = os.path.join(d, rel)
            open(path, "a").write("# local tweak\n")
            r = subprocess.run([sys.executable, BIN, "-C", d],
                               capture_output=True, text=True)
            kept = open(path).read().endswith("# local tweak\n")
            name = os.path.basename(rel)
            skipped = f"SKIP   {rel}" in r.stdout
            if rel in RETIERED:
                check(f"D4: hand-edited {name} survives re-install at rc=0",
                      r.returncode == 0 and kept and skipped,
                      f"rc={r.returncode} kept={kept} skipped={skipped} "
                      f"{r.stderr[-300:]}")
                check(f"D4: the kept {name} gets a warning: line on stderr",
                      f"warning: {rel} kept your local edits" in r.stderr,
                      r.stderr[-400:])
            else:
                check(f"D4 control: hand-edited {name} still exits 3",
                      r.returncode == 3 and kept and skipped
                      and rel in r.stderr,
                      f"rc={r.returncode} kept={kept} skipped={skipped}")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    # [WP1, review correctness/F4 + tests/F2] The same skip on a tree with
    # NO manifest - every fresh clone, since the manifest is gitignored. The
    # file is as likely an earlier install's as the operator's, so the
    # warning must not call it "your local edits", and must offer --adopt,
    # which the pre-re-tier rc=3 path printed and the first WP1 cut dropped.
    d = tempfile.mkdtemp()
    try:
        shutil.rmtree(d)
        shutil.copytree(d0, d, symlinks=True)
        os.remove(os.path.join(d, ".claude", ".installer-manifest.json"))
        rel = ".claude/hooks/test-gate.sh"
        open(os.path.join(d, rel), "a").write("# earlier install's bytes\n")
        r = subprocess.run([sys.executable, BIN, "-C", d],
                           capture_output=True, text=True)
        check("D4 no-manifest: the skipped test-gate.sh exits 0 (precondition)",
              r.returncode == 0 and f"SKIP   {rel}" in r.stdout,
              f"rc={r.returncode} {r.stderr[-300:]}")
        check("D4 no-manifest: the warning does not claim the file holds "
              "your local edits",
              f"warning: {rel}" in r.stderr
              and "kept your local edits" not in r.stderr, r.stderr[-500:])
        check("D4 no-manifest: the warning names the missing manifest and "
              "offers --adopt",
              "no installer manifest" in r.stderr and "--adopt" in r.stderr,
              r.stderr[-500:])
        ra = subprocess.run([sys.executable, BIN, "-C", d, "--adopt"],
                            capture_output=True, text=True)
        rb = subprocess.run([sys.executable, BIN, "-C", d],
                            capture_output=True, text=True)
        check("D4 no-manifest: --adopt then a re-install brings test-gate.sh "
              "up to date",
              ra.returncode == 0 and rb.returncode == 0
              and "earlier install's bytes" not in open(
                  os.path.join(d, rel)).read(),
              f"adopt rc={ra.returncode} reinstall rc={rb.returncode}")
    finally:
        shutil.rmtree(d, ignore_errors=True)
finally:
    shutil.rmtree(d0, ignore_errors=True)

# Forcing function (Milestone-B entry precondition): the tier sets and
# templates.HOOK_EVENT_MAP partition exactly, asserted at installer import.
import installer  # noqa: E402  (import-time assertion already survived)
import templates  # noqa: E402

classified = (installer.SECURITY_CRITICAL_HOOKS
              | installer.AUTONOMY_CRITICAL_HOOKS
              | installer.NON_CRITICAL_HOOKS)
check("forcing: tier sets exactly cover templates.HOOK_EVENT_MAP",
      classified == set(templates.HOOK_EVENT_MAP),
      f"unclassified={set(templates.HOOK_EVENT_MAP) - classified} "
      f"phantom={classified - set(templates.HOOK_EVENT_MAP)}")
check("forcing: tiers are pairwise disjoint",
      len(installer.SECURITY_CRITICAL_HOOKS)
      + len(installer.AUTONOMY_CRITICAL_HOOKS)
      + len(installer.NON_CRITICAL_HOOKS) == len(classified))

# The assertion actually trips: an unclassified emitted hook raises.
try:
    templates.HOOK_EVENT_MAP["totally-new-hook"] = ("Stop", None)
    try:
        installer._assert_tier_partition()
        check("forcing: unclassified emitted hook raises at import-check",
              False, "no exception raised")
    except RuntimeError as e:
        check("forcing: unclassified emitted hook raises at import-check",
              "totally-new-hook" in str(e), str(e))
finally:
    del templates.HOOK_EVENT_MAP["totally-new-hook"]

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

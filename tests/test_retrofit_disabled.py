#!/usr/bin/env python3
"""[retrofit-disable, 2026-10-16] The retrofit route is disabled by operator
directive (backlog row Z-72) until its backlog rows are built.

Pins the refusal at every edge: bin/bootstrap-install (and the plugin copy) on a
retrofit config, on a config with a `retrofit:` section, and on any config over
an existing retrofit install (`.claude/.retrofit-state.json`; only --uninstall
stays open); retrofit-interview through bin/, the module and the plugin module;
installer.apply_plan called in-process; and the runners that open the route for
the other suites (bin/run-tests, .claude/mutation-gate.py).

Red-first friendly: it imports no name that b2e146a lacks, so on that tree every
row runs and fails by name. The override is hard-coded and removed from this
process and every child, so the suite measures the shipped default even under
bin/run-tests. PYTHONSAFEPATH is removed too: the mutation gate sets it, and
under it `python3 lib/retrofit_interview.py` cannot import its siblings.
Rows marked CONTRAST pass before and after the change.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ENV_NAME = "BOOTSTRAP_ENABLE_RETROFIT"

P = F = 0


def check(name, ok, detail=""):
    global P, F
    if ok:
        P += 1
        print(f"  PASS  {name}")
    else:
        F += 1
        print(f"  FAIL  {name}  {detail}"[:600])


os.environ.pop(ENV_NAME, None)
os.environ.pop("PYTHONSAFEPATH", None)
ENV = dict(os.environ)
TMP = tempfile.mkdtemp(prefix="rf-disabled-")
RF_CFG = """mode: "retrofit"
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
NO_R08 = RF_CFG.replace("  r08_committed: true\n", "")
BAD_SWITCH = RF_CFG.replace("secrets:\n  enabled: true",
                            'secrets:\n  enabled: "yes"')
GF_CFG = 'project:\n  name: "gf"\n  archetype: "cli"\n'
BI = os.path.join(ROOT, "bin", "bootstrap-install")
PBI = os.path.join(ROOT, "plugin", "toolchain", "bin", "bootstrap-install")
RI = os.path.join(ROOT, "bin", "retrofit-interview")
RIM = os.path.join(ROOT, "lib", "retrofit_interview.py")
PRIM = os.path.join(ROOT, "plugin", "toolchain", "lib",
                    "retrofit_interview.py")
MARK = "Z-72"


def run(tool, args, cwd, env=ENV):
    return subprocess.run([sys.executable, tool, *args], cwd=cwd, env=env,
                          stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=300)


def project(name, cfg):
    d = os.path.join(TMP, name)
    os.makedirs(d)
    subprocess.run(["git", "init", "-q", d], check=True)
    with open(os.path.join(d, "bootstrap.config.yaml"), "w") as fh:
        fh.write(cfg)
    return d


def install_retrofit(name):
    """A committed retrofit install, made with the override set."""
    d = project(name, RF_CFG)
    os.makedirs(os.path.join(d, "src"))
    with open(os.path.join(d, "src", "app.py"), "w") as fh:
        fh.write("print('legacy')\n")
    r = run(BI, ["-C", d], d, env=dict(ENV, **{ENV_NAME: "1"}))
    assert r.returncode == 0, r.stderr[-400:]
    subprocess.run(["git", "-C", d, "add", "-A"], check=True)
    subprocess.run(["git", "-C", d, "-c", "user.email=t@t", "-c",
                    "user.name=t", "commit", "-qm", "rf"], check=True)
    return d


def git_dirty(d):
    return subprocess.run(["git", "-C", d, "status", "--porcelain"],
                          capture_output=True, text=True).stdout.strip()


def tree(d):
    return sorted(x for x in os.listdir(d) if x != ".git")


def refused(r, d, cfg_kept=True):
    return (r.returncode == 2 and MARK in r.stderr
            and "ask the operator" in r.stderr
            and tree(d) == (["bootstrap.config.yaml"] if cfg_kept else []))


try:
    for label, tool in (("bin", BI), ("plugin", PBI)):
        for extra in ([], ["--dry-run"], ["--print-config"]):
            tag = extra[0] if extra else "install"
            d = project(f"rf-{label}-{tag}", RF_CFG)
            r = run(tool, ["-C", d, *extra], d)
            check(f"R1 {label} bootstrap-install {tag}: retrofit refused",
                  refused(r, d), f"rc={r.returncode} {r.stderr[-300:]}")
    d = project("order-r08", NO_R08)
    r = run(BI, ["-C", d], d)
    check("R2 refusal precedes the r08_committed error",
          refused(r, d) and "r08_committed" not in r.stderr,
          f"rc={r.returncode} {r.stderr[-300:]}")
    d = project("order-switch", BAD_SWITCH)
    r = run(BI, ["-C", d], d)
    check("R3 refusal precedes the policy-switch error",
          refused(r, d) and "must be true or false" not in r.stderr,
          f"rc={r.returncode} {r.stderr[-300:]}")
    near = RF_CFG.replace('mode: "retrofit"', 'mode: "retrofitx"')
    near = near[:near.index("retrofit:\n")]   # no section: R11 refuses one
    d = project("near-miss", near)
    r = run(BI, ["-C", d, "--print-config"], d)
    check("R4 CONTRAST a non-retrofit mode gets the mode error, not the refusal",
          r.returncode == 2 and MARK not in r.stderr
          and "mode must be one of" in r.stderr, r.stderr[-300:])
    for label, tool in (("bin", RI), ("module", RIM), ("plugin-module", PRIM)):
        for sub in (["scan"], ["analyze"], ["synthesize"], ["interactive"],
                    ["--help"], [], ["nosuchcmd"]):
            name = sub[0].strip("-") if sub else "noargs"
            d = os.path.join(TMP, f"ri-{label}-{name}")
            os.makedirs(d)
            args = [*sub, "-C", d] if sub and sub[0] in (
                "scan", "analyze", "synthesize", "interactive") else sub
            r = run(tool, args, d)
            check(f"R5 retrofit-interview {label} {name}: refused",
                  refused(r, d, cfg_kept=False),
                  f"rc={r.returncode} {r.stderr[-300:]}")
    # R11 a `retrofit:` section is refused however the mode line reads
    for tag, cfg in (
            ("mode-absent", RF_CFG.replace('mode: "retrofit"\n', "")),
            ("mode-cased", RF_CFG.replace('mode: "retrofit"', 'Mode: "retrofit"')),
            ("bom", "\ufeff" + RF_CFG)):
        d = project(f"rkey-{tag}", cfg)
        r = run(BI, ["-C", d, "--dry-run"], d)
        check(f"R11 retrofit section, {tag}: refused", refused(r, d),
              f"rc={r.returncode} {r.stderr[-300:]}")
    # R12 an existing retrofit install is frozen: only --uninstall runs
    for tag, cfg, extra in (("greenfield", GF_CFG, []),
                            ("greenfield", GF_CFG, ["--dry-run"]),
                            ("greenfield", GF_CFG, ["--adopt"]),
                            ("greenfield", GF_CFG, ["--print-config"]),
                            ("retrofit", RF_CFG, [])):
        d = install_retrofit(f"frozen-{tag}-{'-'.join(extra) or 'install'}")
        with open(os.path.join(d, "bootstrap.config.yaml"), "w") as fh:
            fh.write(cfg)
        subprocess.run(["git", "-C", d, "add", "-A"], check=True)
        subprocess.run(["git", "-C", d, "-c", "user.email=t@t", "-c",
                        "user.name=t", "commit", "-qm", "cfg"],
                       capture_output=True)
        r = run(BI, ["-C", d, *extra], d)
        check(f"R12 existing retrofit install, {tag} config "
              f"{' '.join(extra) or 'install'}: refused, tree unchanged",
              r.returncode == 2 and MARK in r.stderr
              and "ask the operator" in r.stderr and git_dirty(d) == "",
              f"rc={r.returncode} dirty={git_dirty(d)[:200]} "
              f"{r.stderr[-300:]}")
    d = install_retrofit("frozen-uninstall")
    r = run(BI, ["-C", d, "--uninstall"], d)
    check("R13 CONTRAST --uninstall still runs on a retrofit install",
          r.returncode == 0 and MARK not in r.stderr, r.stderr[-300:])
    # R14 the write-side guard: apply_plan called in-process
    d = project("inproc", RF_CFG)
    code = (
        "import sys; sys.path.insert(0, %r)\n"
        "from pathlib import Path\nimport installer, defaults, minyaml\n"
        "raw = minyaml.load_yaml(open(%r).read())\n"
        "cfg, errs = defaults.resolve_config(raw)\n"
        "assert not errs, errs\n"
        "plan = installer.build_plan(cfg)\n"
        "try:\n"
        "    installer.apply_plan(Path(%r), plan, cfg, dry=False, force=False)\n"
        "except Exception as exc:\n"
        "    print('RAISED', exc, file=sys.stderr); sys.exit(3)\n"
        % (os.path.join(ROOT, "lib"),
           os.path.join(d, "bootstrap.config.yaml"), d))
    r = subprocess.run([sys.executable, "-c", code], cwd=d, env=ENV,
                       capture_output=True, text=True, timeout=300)
    check("R14 apply_plan refuses a retrofit plan in-process, writes nothing",
          r.returncode == 3 and MARK in r.stderr
          and tree(d) == ["bootstrap.config.yaml"],
          f"rc={r.returncode} tree={tree(d)[:5]} {r.stderr[-300:]}")
    # R15 the two runners open the route for the other suites
    for rel in ("bin/run-tests", ".claude/mutation-gate.py"):
        with open(os.path.join(ROOT, rel)) as fh:
            src = fh.read()
        check(f"R15 {rel} sets the override for the suites it runs",
              f'env["{ENV_NAME}"] = "1"' in src)
    d = project("gf", GF_CFG)
    r = run(BI, ["-C", d], d)
    check("R6 CONTRAST greenfield still installs, rc=0",
          r.returncode == 0 and MARK not in r.stderr
          and os.path.exists(os.path.join(d, "CLAUDE.md")), r.stderr[-300:])
    for val, opens in (("1", True), ("true", False), ("0", False),
                       ("", False), (" 1", False), ("yes", False)):
        d = project(f"hatch-{val.strip() or 'empty'}-{len(val)}", RF_CFG)
        r = run(BI, ["-C", d], d, env=dict(ENV, **{ENV_NAME: val}))
        if opens:
            ok = (r.returncode == 0 and MARK not in r.stderr
                  and os.path.exists(os.path.join(d, "CLAUDE.md")))
        else:
            ok = refused(r, d)
        check(f"R7 hatch {val!r}: {'opens (CONTRAST)' if opens else 'stays closed'}",
              ok, f"rc={r.returncode} {r.stderr[-300:]}")
    d = project("msg", RF_CFG)
    r = run(BI, ["-C", d], d)
    err = r.stderr
    check("R8 message names Z-72 and says ask the operator",
          MARK in err and "Stop and ask the operator" in err, err[-300:])
    check("R9 message never names the override",
          r.returncode == 2 and ENV_NAME not in err, err[-300:])
    check("R10 message does not steer to a greenfield install",
          r.returncode == 2 and "mode: bootstrap" not in err
          and "drop" not in err.lower(), err[-300:])
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{P} passed, {F} failed")
sys.exit(1 if F else 0)

#!/usr/bin/env python3
"""[retrofit-disable, 2026-10-16] The retrofit route is disabled by operator
directive (backlog row Z-72) until its backlog rows are built.

Pins the refusal at every edge: bin/bootstrap-install (and the plugin copy) on a
retrofit config, on a config with a `retrofit:` section, and on any config in a
retrofit project (defaults.RETROFIT_MARKERS: the state file, or a signed file
only a retrofit install writes; only --uninstall stays open, and it moves the
state file aside); bootstrap-interview there; retrofit-interview through bin/,
the module and the plugin module;
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
BI_INT = os.path.join(ROOT, "bin", "bootstrap-interview")
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
    if r.returncode != 0:
        check(f"FIXTURE {name}: retrofit install with the override", False,
              f"rc={r.returncode} {r.stderr[-300:]}")
        return None
    subprocess.run(["git", "-C", d, "add", "-A"], check=True)
    subprocess.run(["git", "-C", d, "-c", "user.email=t@t", "-c",
                    "user.name=t", "commit", "-qm", "rf"], check=True)
    return d


def git_dirty(d):
    return subprocess.run(["git", "-C", d, "status", "--porcelain"],
                          capture_output=True, text=True).stdout.strip()


def tree(d):
    return sorted(x for x in os.listdir(d) if x != ".git")


MSG = ("the retrofit route is disabled (directive of 2026-10-14) until its "
       "backlog rows are built; row Z-72 of docs/deferred-backlog.md in the "
       "Bootstrap Protocol repository records it. Stop and ask the operator, "
       "and do not work around this refusal.")


def commit_cfg(d, cfg):
    with open(os.path.join(d, "bootstrap.config.yaml"), "w") as fh:
        fh.write(cfg)
    subprocess.run(["git", "-C", d, "add", "-A"], check=True)
    subprocess.run(["git", "-C", d, "-c", "user.email=t@t", "-c",
                    "user.name=t", "commit", "-qm", "cfg"],
                   capture_output=True)


def frozen(r, d):
    return (r.returncode == 2 and MARK in r.stderr
            and "ask the operator" in r.stderr and git_dirty(d) == "")


def refused(r, d, cfg_kept=True):
    return (r.returncode == 2 and MARK in r.stderr
            and "ask the operator" in r.stderr
            and tree(d) == (["bootstrap.config.yaml"] if cfg_kept else []))


try:
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
    for label, tool in (("bin", BI), ("plugin", PBI)):
        for extra in ([], ["--dry-run"], ["--print-config"], ["--force"],
                      ["--adopt"]):
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
        d = os.path.join(TMP, f"ri-{label}-gitrepo-dir")
        os.makedirs(d)
        subprocess.run(["git", "init", "-q", d], check=True)
        r = run(tool, ["scan", "--dir", d], d)
        check(f"R5 retrofit-interview {label} scan --dir in a git repo: "
              f"refused", refused(r, d, cfg_kept=False),
              f"rc={r.returncode} {r.stderr[-300:]}")
    # R11 a `retrofit:` section is refused however the mode line reads
    for tag, cfg in (
            ("mode-absent", RF_CFG.replace('mode: "retrofit"\n', "")),
            ("mode-cased", RF_CFG.replace('mode: "retrofit"', 'Mode: "retrofit"')),
            ("bom", "\ufeff" + RF_CFG),
            ("mode-bootstrap", RF_CFG.replace('mode: "retrofit"',
                                              'mode: "bootstrap"')),
            ("quoted-keys", RF_CFG.replace('mode:', '"mode":')
             .replace("\nretrofit:", '\n"retrofit":')),
            ("single-quoted-keys", RF_CFG.replace('mode:', "'mode':")
             .replace("\nretrofit:", "\n'retrofit':")),
            ("bom-quoted-mode-only", '\ufeff"mode": "retrofit"\n'
             + RF_CFG[RF_CFG.index("project:"):RF_CFG.index("retrofit:\n")])):
        d = project(f"rkey-{tag}", cfg)
        r = run(BI, ["-C", d, "--dry-run"], d)
        check(f"R11 retrofit section, {tag}: refused", refused(r, d),
              f"rc={r.returncode} {r.stderr[-300:]}")
    # R12 a retrofit project is frozen: only --uninstall runs
    for tag, cfg, extra in (("greenfield", GF_CFG, []),
                            ("greenfield", GF_CFG, ["--dry-run"]),
                            ("greenfield", GF_CFG, ["--adopt"]),
                            ("greenfield", GF_CFG, ["--force"]),
                            ("greenfield", GF_CFG, ["--print-config"]),
                            ("retrofit", RF_CFG, [])):
        d = install_retrofit(f"frozen-{tag}-{'-'.join(extra) or 'install'}")
        if d is None:
            continue
        commit_cfg(d, cfg)
        r = run(BI, ["-C", d, *extra], d)
        check(f"R12 existing retrofit install, {tag} config "
              f"{' '.join(extra) or 'install'}: refused, tree unchanged",
              frozen(r, d), f"rc={r.returncode} dirty={git_dirty(d)[:200]} "
              f"{r.stderr[-300:]}")
    # R12b a clone: the gitignored state file is absent, the markers are not
    d = install_retrofit("frozen-clone")
    if d is not None:
        os.remove(os.path.join(d, ".claude", ".retrofit-state.json"))
        commit_cfg(d, GF_CFG)
        r = run(BI, ["-C", d], d)
        check("R12b a clone of a retrofit project (no state file): refused",
              frozen(r, d), f"rc={r.returncode} dirty={git_dirty(d)[:200]} "
              f"{r.stderr[-300:]}")
    # R12c each marker freezes on its own: the state file by its path, the
    # others by the retrofit template's signature in their first lines.
    # R12d the same paths without the signature (a greenfield project's own
    # files) freeze nothing.
    SIG = "> Generated by retrofit-installer from bootstrap.config.yaml."
    for rel, signed in ((".claude/.retrofit-state.json", "{}\n"),
                        (".claude/hooks/rollout-schedule.md",
                         f"# Hook rollout schedule\n\n{SIG}\n"),
                        (".claude/inventory/README.md",
                         "# .claude/inventory/ — codebase audit (R0)\n"),
                        (".claude/steering/spec-strategy.md",
                         f"# Spec backfill strategy (R4)\n\n{SIG}\n"),
                        (".claude/debt.md",
                         f"# Technical debt registry (R3)\n\n{SIG}\n")):
        for tag, body in (("signed", signed), ("unsigned", "# Our notes\n")):
            if tag == "unsigned" and rel.endswith(".retrofit-state.json"):
                continue
            d = project(f"marker-{tag}-" + rel.replace("/", "_"), GF_CFG)
            os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
            with open(os.path.join(d, rel), "w") as fh:
                fh.write(body)
            r = run(BI, ["-C", d, "--dry-run"], d)
            if tag == "signed":
                check(f"R12c marker {rel} alone freezes the tree and is named",
                      r.returncode == 2 and MARK in r.stderr
                      and rel in r.stderr, f"rc={r.returncode} {r.stderr[-300:]}")
            else:
                check(f"R12d {rel} without the signature "
                      f"freezes nothing",
                      r.returncode == 0 and MARK not in r.stderr,
                      f"rc={r.returncode} {r.stderr[-300:]}")
    # R12e a run from a subdirectory of a retrofit project is caught too
    d = install_retrofit("frozen-subdir")
    if d is not None:
        sd = os.path.join(d, "src")
        with open(os.path.join(sd, "bootstrap.config.yaml"), "w") as fh:
            fh.write(GF_CFG)
        r = run(BI, ["-C", sd], sd)
        check("R12e a greenfield install from a subdirectory of a retrofit "
              "project: refused",
              r.returncode == 2 and MARK in r.stderr
              and not os.path.exists(os.path.join(sd, ".claude")),
              f"rc={r.returncode} {r.stderr[-300:]}")
    # R12f a clone has no manifest: --uninstall removes nothing and the
    # tree stays frozen (releasing it is the operator's call)
    d = install_retrofit("frozen-orig")
    if d is not None:
        c = os.path.join(TMP, "frozen-clone2")
        subprocess.run(["git", "clone", "-q", d, c], check=True)
        r = run(BI, ["-C", c, "--uninstall"], c)
        with open(os.path.join(c, "bootstrap.config.yaml"), "w") as fh:
            fh.write(GF_CFG)
        r2 = run(BI, ["-C", c], c)
        check("R12f a clone: --uninstall removes nothing, the tree stays "
              "frozen",
              r.returncode == 0 and "No installer manifest found" in r.stdout
              and r2.returncode == 2 and MARK in r2.stderr,
              f"rc={r.returncode}/{r2.returncode} {r2.stderr[-300:]}")
    d = install_retrofit("frozen-uninstall")
    if d is not None:
        r = run(BI, ["-C", d, "--uninstall"], d)
        check("R13 CONTRAST --uninstall still runs on a retrofit install",
              r.returncode == 0 and MARK not in r.stderr, r.stderr[-300:])
        with open(os.path.join(d, "bootstrap.config.yaml"), "w") as fh:
            fh.write(GF_CFG)
        r = run(BI, ["-C", d], d)
        check("R13b after a clean --uninstall the tree is released: a "
              "greenfield install runs",
              r.returncode == 0 and MARK not in r.stderr, r.stderr[-300:])
    d = install_retrofit("frozen-uninstall-edited")
    if d is not None:
        with open(os.path.join(d, ".claude", "steering",
                               "spec-strategy.md"), "a") as fh:
            fh.write("operator notes\n")
        r = run(BI, ["-C", d, "--uninstall"], d)
        with open(os.path.join(d, "bootstrap.config.yaml"), "w") as fh:
            fh.write(GF_CFG)
        r = run(BI, ["-C", d], d)
        check("R13c an edited marker that --uninstall kept still freezes, "
              "and is named",
              r.returncode == 2 and MARK in r.stderr
              and "spec-strategy.md" in r.stderr, r.stderr[-300:])
    # R13e a dangling symlink at the state path is moved aside too, so a
    # clean uninstall still releases the tree
    d = install_retrofit("frozen-uninstall-dangling")
    if d is not None:
        sp = os.path.join(d, ".claude", ".retrofit-state.json")
        os.remove(sp)
        os.symlink("gone.json", sp)
        r = run(BI, ["-C", d, "--uninstall"], d)
        with open(os.path.join(d, "bootstrap.config.yaml"), "w") as fh:
            fh.write(GF_CFG)
        r2 = run(BI, ["-C", d, "--dry-run"], d)
        check("R13e a dangling-symlink state file is moved aside and the tree "
              "released",
              r.returncode == 0 and not os.path.lexists(sp)
              and os.path.lexists(sp + ".pre-uninstall")
              and r2.returncode == 0 and MARK not in r2.stderr,
              f"rc={r.returncode}/{r2.returncode} {r2.stderr[-300:]}")
    # R13f with no manifest, --uninstall still moves the state file aside
    d = install_retrofit("frozen-uninstall-nomanifest")
    if d is not None:
        os.remove(os.path.join(d, ".claude", ".installer-manifest.json"))
        sp = os.path.join(d, ".claude", ".retrofit-state.json")
        r = run(BI, ["-C", d, "--uninstall"], d)
        check("R13f no manifest: --uninstall still moves the state file aside "
              "and says where",
              r.returncode == 0 and "No installer manifest found" in r.stdout
              and not os.path.lexists(sp)
              and os.path.exists(sp + ".pre-uninstall")
              and ".retrofit-state.json.pre-uninstall" in r.stdout,
              f"rc={r.returncode} {r.stdout[-300:]}")
    # R12g a retrofit project below the git top level: a run from its
    # subdirectory is caught (the walk's middle entries)
    top = os.path.join(TMP, "mono")
    os.makedirs(top)
    subprocess.run(["git", "init", "-q", top], check=True)
    svc = os.path.join(top, "svc")
    os.makedirs(os.path.join(svc, "src"))
    with open(os.path.join(svc, "bootstrap.config.yaml"), "w") as fh:
        fh.write(RF_CFG)
    r = run(BI, ["-C", svc], svc, env=dict(ENV, **{ENV_NAME: "1"}))
    sd = os.path.join(svc, "src")
    with open(os.path.join(sd, "bootstrap.config.yaml"), "w") as fh:
        fh.write(GF_CFG)
    r2 = run(BI, ["-C", sd], sd)
    check("R12g a retrofit project below the git top: a greenfield install "
          "from its subdirectory is refused",
          r.returncode == 0 and r2.returncode == 2 and MARK in r2.stderr
          and not os.path.exists(os.path.join(sd, ".claude")),
          f"rc={r.returncode}/{r2.returncode} {r2.stderr[-300:]}")
    deep = os.path.join(svc, "src", "a", "b", "c")
    os.makedirs(deep)
    with open(os.path.join(deep, "bootstrap.config.yaml"), "w") as fh:
        fh.write(GF_CFG)
    r3 = run(BI, ["-C", deep, "--dry-run"], deep)
    check("R12h the same, four levels below the retrofit project",
          r3.returncode == 2 and MARK in r3.stderr,
          f"rc={r3.returncode} {r3.stderr[-300:]}")
    # R13g a second uninstall keeps the first backup, and a dangling symlink
    # at the backup name is not overwritten either
    d = install_retrofit("frozen-uninstall-twice")
    if d is not None:
        import json as _json
        sp = os.path.join(d, ".claude", ".retrofit-state.json")
        on = dict(ENV, **{ENV_NAME: "1"})
        st = _json.load(open(sp)); st["probe_round"] = 1
        _json.dump(st, open(sp, "w"))
        run(BI, ["-C", d, "--uninstall"], d)
        os.symlink("gone.json", sp + ".pre-uninstall-2")
        run(BI, ["-C", d], d, env=on)
        st = _json.load(open(sp)); st["probe_round"] = 2
        _json.dump(st, open(sp, "w"))
        r = run(BI, ["-C", d, "--uninstall"], d)
        b1, b3 = sp + ".pre-uninstall", sp + ".pre-uninstall-3"
        ok = (r.returncode == 0 and os.path.exists(b1) and os.path.exists(b3)
              and _json.load(open(b1)).get("probe_round") == 1
              and _json.load(open(b3)).get("probe_round") == 2
              and os.path.islink(sp + ".pre-uninstall-2")
              and ".pre-uninstall-3" in r.stdout)
        check("R13g a second --uninstall keeps the first backup and skips a "
              "dangling symlink at the next name", ok,
              f"rc={r.returncode} {r.stdout[-300:]}")
    # R13d uninstall keeps the operator's retrofit state in a backup
    d = install_retrofit("frozen-uninstall-state")
    if d is not None:
        sp = os.path.join(d, ".claude", ".retrofit-state.json")
        import json as _json
        st = _json.load(open(sp))
        st["retrofit_complete"] = True
        _json.dump(st, open(sp, "w"))
        with open(os.path.join(d, "CLAUDE.md"), "a") as fh:
            fh.write("operator line\n")
        r = run(BI, ["-C", d, "--uninstall"], d)
        bp = sp + ".pre-uninstall"
        ok = (r.returncode == 0 and not os.path.exists(sp)
              and os.path.exists(bp)
              and _json.load(open(bp)).get("retrofit_complete") is True
              and ".retrofit-state.json.pre-uninstall" in r.stdout)
        check("R13d --uninstall moves the retrofit state to a .pre-uninstall "
              "copy, data intact, and says where", ok,
              f"rc={r.returncode} {r.stdout[-300:]}")
    # R16 bootstrap-interview synthesize in a retrofit project writes nothing
    d = install_retrofit("frozen-synth")
    if d is not None:
        with open(os.path.join(d, "PRD.md"), "w") as fh:
            fh.write("# Demo Service\nA REST API service for widgets.\n")
        r = run(BI_INT, ["analyze", "--prd", "PRD.md", "-o", "iv.md"], d)
        before = open(os.path.join(d, "bootstrap.config.yaml"), "rb").read()
        r = run(BI_INT, ["synthesize", "-i", "iv.md", "-o",
                         "bootstrap.config.yaml"], d)
        after = open(os.path.join(d, "bootstrap.config.yaml"), "rb").read()
        out = r.stdout + r.stderr
        check("R16 bootstrap-interview synthesize in a retrofit project: "
              "refused, config unchanged",
              r.returncode == 2 and MARK in out and before == after,
              f"rc={r.returncode} same={before == after} {out[-300:]}")
    # R16b interactive in a retrofit project writes nothing
    d = install_retrofit("frozen-interactive")
    if d is not None:
        with open(os.path.join(d, "PRD.md"), "w") as fh:
            fh.write("# Demo Service\nA REST API service for widgets.\n")
        before = open(os.path.join(d, "bootstrap.config.yaml"), "rb").read()
        r = subprocess.run([sys.executable, BI_INT, "interactive", "--prd",
                            "PRD.md", "-o", "bootstrap.config.yaml"],
                           cwd=d, env=dict(ENV, BOOTSTRAP_PROMPT_TIMEOUT="5"),
                           input="demo\n" + "\n" * 80, capture_output=True,
                           text=True, timeout=300)
        after = open(os.path.join(d, "bootstrap.config.yaml"), "rb").read()
        out = r.stdout + r.stderr
        check("R16b bootstrap-interview interactive in a retrofit project: "
              "refused, config unchanged",
              r.returncode == 2 and MARK in out and before == after,
              f"rc={r.returncode} same={before == after} {out[-300:]}")
    # R16c synthesize over a retrofit config where nothing is installed
    for tag, cfg in (("mode", RF_CFG),
                     ("section-only", RF_CFG.replace('mode: "retrofit"\n', "")),
                     ("quoted-mode", RF_CFG.replace("mode:", '"mode":'))):
        d = project(f"synth-nomarker-{tag}", cfg)
        with open(os.path.join(d, "PRD.md"), "w") as fh:
            fh.write("# Demo Service\nA REST API service for widgets.\n")
        run(BI_INT, ["analyze", "--prd", "PRD.md", "-o", "iv.md"], d)
        before = open(os.path.join(d, "bootstrap.config.yaml"), "rb").read()
        r = run(BI_INT, ["synthesize", "-i", "iv.md", "-o",
                         "bootstrap.config.yaml"], d)
        after = open(os.path.join(d, "bootstrap.config.yaml"), "rb").read()
        out = r.stdout + r.stderr
        check(f"R16c synthesize over a retrofit config ({tag}), nothing "
              f"installed: refused, config unchanged",
              r.returncode == 2 and MARK in out and before == after,
              f"rc={r.returncode} same={before == after} {out[-300:]}")
    # R14 the write-side guard: apply_plan called in-process
    for force, adopt in ((False, False), (True, False), (False, True)):
      d = project(f"inproc-f{int(force)}-a{int(adopt)}", RF_CFG)
      code = (
        "import sys; sys.path.insert(0, %r)\n"
        "from pathlib import Path\nimport installer, defaults, minyaml\n"
        "raw = minyaml.load_yaml(open(%r).read())\n"
        "cfg, errs = defaults.resolve_config(raw)\n"
        "assert not errs, errs\n"
        "plan = installer.build_plan(cfg)\n"
        "try:\n"
        "    installer.apply_plan(Path(%r), plan, cfg, dry=False, force=%r,"
        " adopt=%r)\n"
        "except Exception as exc:\n"
        "    print('RAISED', exc, file=sys.stderr); sys.exit(3)\n"
        % (os.path.join(ROOT, "lib"),
           os.path.join(d, "bootstrap.config.yaml"), d, force, adopt))
      r = subprocess.run([sys.executable, "-c", code], cwd=d, env=ENV,
                         capture_output=True, text=True, timeout=300)
      check(f"R14 apply_plan refuses a retrofit plan in-process "
            f"(force={force}, adopt={adopt}), writes nothing",
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
    d = project("msg", RF_CFG)
    r = run(BI, ["-C", d], d)
    err = r.stderr
    check("R8 message names Z-72 and says ask the operator",
          MARK in err and "Stop and ask the operator" in err, err[-300:])
    check("R9 message never names the override",
          r.returncode == 2 and ENV_NAME not in err, err[-300:])
    check("R10 message does not steer to a greenfield install",
          r.returncode == 2 and "mode: bootstrap" not in err
          and not any(w in err.lower() for w in (
              "drop", "greenfield", "override", "environment")), err[-300:])
    check("R10b message says not to work around the refusal",
          r.returncode == 2 and "do not work around this refusal" in err,
          err[-300:])
    check("R10c message is exactly the reviewed text",
          r.returncode == 2 and MSG in err, err[-300:])
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{P} passed, {F} failed")
sys.exit(1 if F else 0)

#!/usr/bin/env python3
"""COMPOSITION SWEEP — the cross product that actually finds this class.

    wrapper x wrapper-FLAG x wrapper-operand x invoker x quoting x
    separator x verb

run through BOTH substrates, at GATE level, and diffed against any ancestor
commit.

WHY THIS AND NOT FUZZING
------------------------
Payload-content fuzzing returned nothing across three review rounds. Round 3's
lens A swept 2202 generated commands and found nothing, then found two
fail-opens by hand, because the generated corpus contained no multi-line quoted
runs. Composition found fifteen divergences in one pass.

The previously-proposed remedy - a differential against `bash` word-splitting
(backlog J-20) - would NOT have caught D1 or D2: both tokenizers agree with
bash about word-splitting and disagree about command POSITION, which is
downstream of it.

WHAT THE ROUND-4 VERSION ADDS, AND WHY EACH AXIS IS LOAD-BEARING
----------------------------------------------------------------
* **A wrapper-FLAG axis, in SHORT and LONG spellings.** A reviewer implemented
  exact flag arity and measured 16 of 27 real spellings regressing from deny
  to allow - `sudo -R /`, `sudo --chroot /`, `env --chdir /tmp`,
  `nice --adjustment 5`, `ionice --classdata 4`, `flock --timeout 10`,
  `stdbuf --output 0`, `proxychains --file c`, `doas -a pam` - mostly LONG
  forms of flags whose short form was in the table. Without this axis the
  sweep cannot see that class at all.
* **A backslash-escape axis.** `sh -c pip\\ install\\ evil` has no quoted run,
  so every quoting axis built from `'` and `"` is blind to it. It is one of
  D5's three reproductions and it EXECUTES.
* **BOTH SUBSTRATES.** The previous version ran shell hooks only, so a shape
  the SDK allowed and the shell denied was invisible to it - which is exactly
  half of D1 (`_git_verb` never called the invoker expander).
* **ABSOLUTE verdicts as well as diffs.** A parent-vs-head sweep cannot see a
  hole older than every commit it compares. `ci-mirror` reported ZERO newly
  allowed at b1782ec not because it was sound but because `timeout 5 sh -c
  'git push'` was rc=0 at all three commits. That is the D9 class.

USAGE
-----
    # absolute: every composition must deny on both substrates
    python3 tests/composition_sweep.py

    # differential: nothing newly allowed against these ancestors
    python3 tests/composition_sweep.py --rev 0fba4d2 --rev b1782ec

Each --rev is materialised as a `git worktree` under a temp dir and installed
with its own `bin/bootstrap-install`, so the comparison is between EMITTED
ARTIFACTS, not between source diffs.

`tests/test_composition.py` runs a bounded subset of this generator inside the
normal suite; the full product is too slow for every commit and is meant to be
run deliberately, before a release or after a tokenizer change.
"""
import argparse
import asyncio
import importlib.util
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

CONFIG = """project:
  name: "sweep"
  archetype: "ai-agent"
  shell: "bash"
principles:
  tdd_policy: required
secrets:
  enabled: true
  never_read_paths:
    - ".env*"
    - "secrets/**"
    - "*.pem"
    - "*.key"
deps:
  enabled: true
  approved: ["requests", "flask", "gleeunit"]
commands:
  test: "false"
  lint: "true"
  format: "true"
  ci_local: "false"
"""

# ---- the axes ------------------------------------------------------------ #
#
# Each is deliberately small; the PRODUCT is what finds things.

# (wrapper word, flag spellings). The flag column is the round-4 addition and
# pairs a SHORT form with the LONG form of the same flag wherever one exists,
# because the long forms are where the measured arity regression lived.
WRAPPERS = [
    ("", [""]),
    ("sudo", ["", "-u root", "-R /", "--chroot /", "-i"]),
    ("doas", ["", "-u root", "-a pam"]),
    ("env", ["", "-i", "A=1 B=2", "--chdir /tmp"]),
    ("nice", ["", "-n 5", "--adjustment 5"]),
    ("ionice", ["", "-c 2", "--classdata 4"]),
    ("timeout", ["5", "-k 1 -s KILL 5", "--preserve-status 5"]),
    ("flock", ["/tmp/l", "-w 10 -x /tmp/l", "--timeout 10 /tmp/l"]),
    ("stdbuf", ["-o0", "--output 0"]),
    ("proxychains", ["", "-q", "--file c"]),
    ("chroot", ["/"]),
    ("setsid", [""]),
    ("nohup", [""]),
    ("time", ["", "-p"]),
    ("command", ["", "-p"]),
    ("unbuffer", ["", "-p"]),
    ("watch", ["", "-n 1"]),
    ("xargs", ["", "-n1"]),
]

INVOKERS = ["", "sh -c", "bash -c", "dash -c", "zsh -c", "bash -lc", "eval",
            "busybox sh -c"]

BODIES = {
    "pip": ("dependency-gate", "pip install evilpkg"),
    "npm": ("dependency-gate", "npm install evilpkg"),
    "git-commit": ("test-gate", "git commit -m x"),
    "git-push": ("ci-mirror", "git push"),
    "cat-secret": ("secrets-gate", "cat secrets/prod.yaml"),
    "cat-env": ("secrets-gate", "cat .env"),
}

LEADS = ["", "echo hi; ", "echo hi\n", "true && "]

# `bslash` is the round-4 addition: the invoker argument is held together by
# backslash-escaped spaces instead of quotes, so there is no quoted run at all.
QUOTINGS = ["'", '"', "bslash"]

SHELL_ONLY = {"ci-mirror"}


def _quote(inv_arg, style):
    if style == "bslash":
        return inv_arg.replace(" ", "\\ ")
    return style + inv_arg + style


def generate():
    """(gate, command) pairs. Deduplicated, order-stable."""
    seen = set()
    for (wrap, flags), inv, (_, (gate, body)), lead in itertools.product(
            WRAPPERS, INVOKERS, BODIES.items(), LEADS):
        for flag in flags:
            head = " ".join(x for x in (wrap, flag) if x)
            head = (head + " ") if head else ""
            if not inv:
                if lead and not head:
                    continue          # a bare lead is not a composition
                cmds = [head + lead + body]
            else:
                arg = lead + body
                for style in QUOTINGS:
                    if style != "bslash" and style in arg:
                        continue
                    # The backslash style joins the argument into ONE shell
                    # word, which is only a faithful composition when the
                    # argument is a single command. With a lead the separator
                    # stays unescaped, so bash splits the line and the tail
                    # becomes one un-runnable word - a shape that neither
                    # substrate should have to block and that would make the
                    # absolute assertion below dishonest. D5's actual
                    # reproduction is the no-lead form, `sh -c pip\ install\
                    # evil`, and that is what this generates.
                    if style == "bslash" and lead:
                        continue
                    cmds = [head + inv + " " + _quote(arg, style)]
                    for c in cmds:
                        k = (gate, c)
                        if k not in seen:
                            seen.add(k)
                            yield k
                continue
            for c in cmds:
                k = (gate, c)
                if k not in seen:
                    seen.add(k)
                    yield k


# ---- installs and verdicts ----------------------------------------------- #

class _StubHookMatcher:
    def __init__(self, matcher=None, hooks=None, timeout=None):
        self.matcher, self.hooks, self.timeout = matcher, hooks or [], timeout


def install(rev, tmp):
    """Materialise `rev` (or the working tree) and install from it."""
    if rev == "WORKTREE":
        src = ROOT
    else:
        src = os.path.join(tmp, f"wt-{rev}")
        r = subprocess.run(["git", "-C", ROOT, "worktree", "add", "-q",
                            "--detach", src, rev], capture_output=True,
                           text=True)
        if r.returncode != 0:
            raise SystemExit(f"worktree {rev} failed: {r.stderr}")
    proj = os.path.join(tmp, f"proj-{rev}")
    os.makedirs(proj, exist_ok=True)
    cfg = os.path.join(tmp, "config.yaml")
    if not os.path.exists(cfg):
        with open(cfg, "w") as fh:
            fh.write(CONFIG)
    r = subprocess.run([sys.executable,
                        os.path.join(src, "bin", "bootstrap-install"),
                        "-c", cfg, "-C", proj], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"install at {rev} failed:\n{r.stdout[-1200:]}"
                         f"{r.stderr[-1200:]}")
    subprocess.run(["git", "-C", proj, "init", "-q"], capture_output=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", proj, "config", k, v],
                       capture_output=True)
    with open(os.path.join(proj, "readme.txt"), "w") as fh:
        fh.write("x\n")
    subprocess.run(["git", "-C", proj, "add", "readme.txt"],
                   capture_output=True)
    subprocess.run(["git", "-C", proj, "commit", "-qm", "base"],
                   capture_output=True)
    return proj


_MODS = {}


def sdk_module(proj):
    if proj not in _MODS:
        gp = os.path.join(proj, ".claude", "sdk_gates", "gates.py")
        stub = types.ModuleType("claude_agent_sdk")
        stub.HookMatcher = _StubHookMatcher
        sys.modules["claude_agent_sdk"] = stub
        spec = importlib.util.spec_from_file_location(
            "sweep_gates_" + os.path.basename(proj), gp)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODS[proj] = mod
    return _MODS[proj]


def verdict_shell(proj, gate, cmd):
    e = dict(os.environ)
    e["CLAUDE_PROJECT_DIR"] = proj
    p = subprocess.run(
        ["bash", os.path.join(proj, ".claude", "hooks", f"{gate}.sh")],
        input=json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": cmd}}),
        capture_output=True, text=True, env=e, cwd=proj)
    return {0: "allow", 2: "deny"}.get(p.returncode, f"rc{p.returncode}")


def verdict_sdk(proj, gate, cmd):
    if gate in SHELL_ONLY:
        return "n/a"
    mod = sdk_module(proj)
    if gate not in mod._GATE_FACTORIES:
        return "n/a"
    prev = os.environ.get("CLAUDE_PROJECT_DIR")
    cwd = os.getcwd()
    os.environ["CLAUDE_PROJECT_DIR"] = proj
    try:
        os.chdir(proj)
        res = asyncio.run(mod._GATE_FACTORIES[gate](mod.RESOLVED_CONFIG)(
            {"tool_name": "Bash", "tool_input": {"command": cmd}},
            "tu-1", None))
    finally:
        os.chdir(cwd)
        if prev is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = prev
    hso = (res or {}).get("hookSpecificOutput") or {}
    return "deny" if hso.get("permissionDecision") == "deny" else "allow"


def verdicts(proj, gate, cmd):
    return verdict_shell(proj, gate, cmd), verdict_sdk(proj, gate, cmd)


# ---- the intended-relaxation list ---------------------------------------- #
#
# docs/round-4-intended-relaxations.md is the authority; this is the machine-
# checkable projection of it. A shape that is newly allowed and NOT matched
# here is a regression. Written BEFORE the round-4 parsers were touched.
def is_intended_relaxation(gate, cmd):
    """Only R-3 is encoded here, and that is COMPLETE for this generator, not
    a partial transcription. The other relaxations are unreachable by it:

      R-1  eval-gate  - not in BODIES; needs a git history, not a command
      R-2  tdd-gate   - not in BODIES; a Write payload, not a Bash one
      R-4  advisory hooks on an EMPTY payload - not a command at all
      R-4b `ssh h "git commit -m '.env'"` - `ssh` is in neither WRAPPERS nor
           INVOKERS here, so no composition produces it

    If you add `ssh` to the axes, or add eval-gate/tdd-gate to BODIES, this
    function has to grow with them - otherwise the sweep will report an
    enumerated relaxation as a regression, and the temptation will be to widen
    the allowlist to match the measurement, which is the one thing
    docs/round-4-intended-relaxations.md forbids.
    """
    head = cmd.split()
    if not head:
        return False
    # R-3: `script`/`su` take a POSITIONAL and do not run it. `script pip
    # install evil` names a typescript file `pip`; `su pip install evil`
    # switches to the user `pip`. Neither runs pip.
    if head[0] in ("script", "su") and " -c " not in cmd:
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", action="append", default=[],
                    help="ancestor commit to compare against; repeatable. "
                         "With none, runs the ABSOLUTE check instead.")
    ap.add_argument("--limit", type=int, default=0,
                    help="evenly-spaced sample of N cases across the whole "
                         "product (NOT the first N -- the first N are all "
                         "one wrapper, which is how a sampled sweep misses "
                         "this class)")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="composition-sweep-")
    try:
        projs = {"WORKTREE": install("WORKTREE", tmp)}
        for r in args.rev:
            projs[r] = install(r, tmp)

        cases = list(generate())
        if args.limit and args.limit < len(cases):
            stride = len(cases) / float(args.limit)
            cases = [cases[int(i * stride)] for i in range(args.limit)]
        print(f"{len(cases)} cases x {len(projs)} installs, both substrates",
              file=sys.stderr)

        if not args.rev:
            # ABSOLUTE: every composition of a wrapper, an invoker and a
            # gated verb must deny on BOTH substrates. This is the half a
            # parent-vs-head sweep is structurally blind to.
            bad = []
            for gate, cmd in cases:
                sh, sdk = verdicts(projs["WORKTREE"], gate, cmd)
                ok_sh = sh == "deny"
                ok_sdk = sdk in ("deny", "n/a")
                if is_intended_relaxation(gate, cmd):
                    continue
                if not (ok_sh and ok_sdk):
                    bad.append((gate, cmd, sh, sdk))
            print(f"\n== compositions NOT denied on both substrates: "
                  f"{len(bad)} of {len(cases)} ==")
            for gate, cmd, sh, sdk in bad[:60]:
                print(f"  [{gate}] shell={sh} sdk={sdk}  {cmd!r}")
            if len(bad) > 60:
                print(f"  ... and {len(bad) - 60} more")
            return 1 if bad else 0

        newly = []
        for gate, cmd in cases:
            head = verdicts(projs["WORKTREE"], gate, cmd)
            olds = {r: verdicts(projs[r], gate, cmd) for r in args.rev}
            for i, substrate in enumerate(("shell", "sdk")):
                if head[i] != "allow":
                    continue
                if any(v[i] == "deny" for v in olds.values()):
                    if is_intended_relaxation(gate, cmd):
                        continue
                    newly.append((gate, substrate, cmd, olds, head))

        print(f"\n== NEWLY ALLOWED in the working tree: {len(newly)} ==")
        by_gate = {}
        for gate, substrate, cmd, olds, head in newly:
            by_gate.setdefault((gate, substrate), []).append(cmd)
            desc = " ".join(f"{r}={v}" for r, v in olds.items())
            print(f"  [{gate}/{substrate}] {desc} HEAD={head}  {cmd!r}")
        print("\n-- by gate/substrate --")
        for k, rows in sorted(by_gate.items()):
            print(f"  {k[0]:20} {k[1]:6} {len(rows)}")
        if newly:
            print("\nDefinition of done: this number is ZERO against every "
                  "listed ancestor, except the enumerated intended "
                  "relaxations in docs/round-4-intended-relaxations.md.")
        return 1 if newly else 0
    finally:
        for r in args.rev:
            subprocess.run(["git", "-C", ROOT, "worktree", "remove", "--force",
                            os.path.join(tmp, f"wt-{r}")],
                           capture_output=True)
        if args.keep:
            print(f"\nkept: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

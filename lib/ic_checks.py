"""R-9 - the IC gate: IC-1..IC-7 self-checks (Bootstrap-Protocol-v2-0-0.md
Implementation Contract) gating `gate_substrate: "sdk-callable"`.

The installer REFUSES to write "sdk-callable" unless every check here
passes (AC-9-1/9-2); `bootstrap-install --ic-checks` prints the checklist
as JSON for the seam §8.2 `protocol-compatibility` job (AC-9-3).

Checks are deterministic and self-contained: they interrogate the live
emission surface (rendered templates / build_plan output / module
contracts), never the network. Fail-loud discipline: a check that cannot
determine its answer FAILS, it never guesses.

TEST-ONLY override: BOOTSTRAP_IC_FORCE_FAIL=<check-name> forces the named
check to fail. Mirroring the BOOTSTRAP_TEST_FORCE_PROMPT asymmetry, the
override can only force REFUSING (a failure), never passing.
"""
from __future__ import annotations

import ast
import json
import os
import tempfile
from pathlib import Path

# Rendered against this fixture: full-autonomous exercises every wrapper
# and gate surface the checks interrogate.
_FIXTURE = {
    "project": {"name": "ic-check", "archetype": "ai-agent",
                "prd_tier": "full"},
    "autonomous_modes": {"loop_mode_enabled": True,
                         "goal_supervised_mode_enabled": True,
                         "queue_mode_enabled": True},
    "principles": {"tdd_policy": "required"},
    "commands": {"test": "true", "lint": "true"},
}


def _resolved_fixture():
    from defaults import resolve_config
    import copy
    cfg, errs = resolve_config(copy.deepcopy(_FIXTURE))
    if errs:
        raise RuntimeError(f"IC fixture must resolve cleanly: {errs}")
    return cfg


def _ic1_validate_only() -> tuple[bool, str]:
    """IC-1: `bootstrap-interview synthesize --validate-only` is real -
    verified BEHAVIORALLY (a source grep would false-green on the flag
    surviving in a docstring while the wiring is gone). Drives
    interview.main and asserts the flag reaches the synthesize handler
    (an unwired flag argparse-errors with SystemExit) and writes no
    output file."""
    import contextlib
    import io
    import interview
    with tempfile.TemporaryDirectory() as d:
        missing = os.path.join(d, "no-such-interview.md")
        out = os.path.join(d, "should-not-be-written.yaml")
        buf = io.StringIO()
        try:
            with contextlib.redirect_stderr(buf), \
                    contextlib.redirect_stdout(buf):
                rc = interview.main(
                    ["synthesize", "-i", missing, "-o", out,
                     "--validate-only"])
        except SystemExit:
            # argparse rejected the flag -> not wired to the handler.
            return False, ("--validate-only is not a wired synthesize "
                           "flag (argparse rejected it)")
        if not isinstance(rc, int):
            return False, f"synthesize handler returned {rc!r}, not an exit code"
        if os.path.exists(out):
            return False, "--validate-only wrote an output file (must not)"
    return True, ("synthesize --validate-only is wired and writes no "
                  "output file")


def _ic2_root_sentinels() -> tuple[bool, str]:
    """IC-2: root .halt/.halt-hard dual-honor in every wrapper. The
    graceful-halt token is matched as `"$ROOT_HALT"` (quoted var use) -
    NOT the bare `ROOT_HALT`, which is a substring of ROOT_HALT_HARD and
    would pass vacuously whenever only the hard-halt guard survives."""
    from templates import TEMPLATES
    cfg = _resolved_fixture()
    missing = []
    for key in ("auto_sh", "loop_sh", "goal_loop_sh"):
        body = TEMPLATES[key](cfg)
        if ('"$ROOT_HALT_HARD"' not in body
                or '"$ROOT_HALT"' not in body
                or "queue/.halt" not in body):
            missing.append(key)
    return (not missing,
            "all wrappers dual-honor root + queue sentinels" if not missing
            else f"wrappers missing sentinel honor: {missing}")


def _ic3_gate_substrate_field() -> tuple[bool, str]:
    """IC-3: the state writer emits gate_substrate (behavioral probe)."""
    import installer
    cfg = _resolved_fixture()
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        installer._write_state(
            root, cfg, {"generated_at": "1970-01-01T00:00:00Z"})
        state = json.loads(
            (root / ".claude" / ".bootstrap-state.json").read_text())
    val = state.get("gate_substrate")
    ok = val in ("shell", "sdk-callable")
    return ok, (f"state writer emits gate_substrate={val!r}" if ok else
                f"gate_substrate absent/invalid in state: {val!r}")


def _ic4_advisor_default() -> tuple[bool, str]:
    """IC-4: LLM advisor default model is the current ID - asserted by
    ATTRIBUTE on the hoisted constant (not a source grep, which greens on
    the literal appearing in any comment/changelog line)."""
    import llm_advisor
    model = getattr(llm_advisor, "DEFAULT_ADVISOR_MODEL", None)
    env = getattr(llm_advisor, "MODEL_ENV", None)
    ok = model == "claude-sonnet-5" and env == "BOOTSTRAP_INTERVIEW_LLM_MODEL"
    return ok, (f"advisor default is {model!r} (env-overridable via {env})"
                if ok else
                f"advisor default is {model!r}, MODEL_ENV={env!r}")


def _ic5_sdk_gates() -> tuple[bool, str]:
    """IC-5: the SDK gate module is emitted per seam §9 (single public
    builder, parseable Python, security-critical tier)."""
    import installer
    cfg = _resolved_fixture()
    plan = installer.build_plan(cfg)
    entry = next((a for a in plan
                  if a["path"] == ".claude/sdk_gates/gates.py"), None)
    if entry is None:
        return False, ".claude/sdk_gates/gates.py not in the plan"
    if installer._hook_tier(entry) != installer.TIER_SECURITY:
        return False, "gates.py is not security-critical tier"
    try:
        tree = ast.parse(entry["body"])
    except SyntaxError as e:
        return False, f"emitted gates.py does not parse: {e}"
    public_fns = [n.name for n in tree.body
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and not n.name.startswith("_")]
    if public_fns != ["build_hooks"]:
        return False, f"public surface is {public_fns}, not [build_hooks]"
    return True, ("gates.py emitted, parses, single public builder "
                  "build_hooks, security-critical tier")


def _ic6_native_worktree() -> tuple[bool, str]:
    """IC-6: wrappers route via native --worktree with no hand-rolled
    `git worktree add`. The forbidden thing is an executable
    `git worktree add` COMMAND, so the check inspects only NON-COMMENT
    shell lines - documentation may mention the phrase freely (it does,
    to warn against it). This replaces the brittle strip-the-known-phrase
    match that turned the check into a shadow grammar of allowed
    sentences."""
    from templates import TEMPLATES
    cfg = _resolved_fixture()
    bad = []
    for key in ("loop_sh", "goal_loop_sh"):
        body = TEMPLATES[key](cfg)
        code = "\n".join(ln for ln in body.splitlines()
                         if not ln.lstrip().startswith("#"))
        if "--worktree" not in body or "git worktree add" in code:
            bad.append(key)
    return (not bad,
            "wrappers route via native --worktree" if not bad
            else f"wrappers not natively routed: {bad}")


def _ic7_hook_tiers() -> tuple[bool, str]:
    """IC-7: machine-readable tiers + the partition forcing function."""
    import installer
    try:
        installer._assert_tier_partition()
    except RuntimeError as e:
        return False, f"tier partition violated: {e}"
    probe = installer._hook_tier(
        {"kind": "hook", "path": ".claude/hooks/secrets-gate.sh"})
    ok = probe == installer.TIER_SECURITY
    return ok, ("tier partition holds; manifest tiers derivable" if ok
                else f"secrets-gate classified {probe!r}")


_CHECKS = (
    ("IC-1", "synthesize --validate-only", _ic1_validate_only),
    ("IC-2", "root-sentinel dual-honor", _ic2_root_sentinels),
    ("IC-3", "gate_substrate state field", _ic3_gate_substrate_field),
    ("IC-4", "advisor default model", _ic4_advisor_default),
    ("IC-5", "SDK gate module (seam §9)", _ic5_sdk_gates),
    ("IC-6", "native worktree routing", _ic6_native_worktree),
    ("IC-7", "machine-readable hook tiers", _ic7_hook_tiers),
)


def run_ic_checks() -> dict:
    """Run every IC self-check. Returns an ordered mapping
    {ic: {"title", "passed", "detail"}}. A check that raises is a
    FAILURE with the exception as detail (fail-loud, never guess)."""
    forced = os.environ.get("BOOTSTRAP_IC_FORCE_FAIL", "").strip()
    valid_ics = {ic for ic, _, _ in _CHECKS}
    if forced and forced not in valid_ics:
        # Fail-loud/never-guess: an unrecognized override (typo like
        # "IC5"/"ic-2", or a stale name) must NOT silently no-op into a
        # real grant - that is the safety-critical direction the
        # can-only-force-refusing asymmetry exists to make unreachable.
        raise ValueError(
            f"BOOTSTRAP_IC_FORCE_FAIL={forced!r} names no known check; "
            f"expected one of {sorted(valid_ics)}")
    out: dict = {}
    for ic, title, fn in _CHECKS:
        try:
            passed, detail = fn()
        except Exception as e:          # noqa: BLE001 - fail-loud contract
            passed, detail = False, f"check raised: {e!r}"
        if forced == ic:
            passed = False
            detail = (f"forced failure via BOOTSTRAP_IC_FORCE_FAIL "
                      f"(TEST-ONLY; can only force refusing) - was: "
                      f"{detail}")
        out[ic] = {"title": title, "passed": passed, "detail": detail}
    return out


def all_passed(results: dict) -> bool:
    return all(r["passed"] for r in results.values())

"""
Config resolution & validation.

Takes the raw parsed config and:
  1. fills archetype-derived defaults (Bootstrap-Protocol-v2-0-0.md Phase 0/4/6 logic),
  2. resolves the conditional hook set (Phase 6 + autonomous-mode flags),
  3. enforces the Bootstrap-Protocol-v2-0-0.md skip-policy invariants,
returning (resolved_cfg, errors). errors non-empty => installer aborts.
"""

from __future__ import annotations

import copy

# ---- [round-4 D12/D18] CONFIG IS AN ATTACK SURFACE -------------------------
#
# Four fields reach EXECUTABLE shell in an emitted hook, and none of them was
# validated anywhere. Established by execution, not by reading: a marker was
# planted in every string field of a resolved config and the emitted plan was
# searched for it. The markdown-only fields (project.name, project.prd_path,
# project.shell, principles.ranked, principles.tiebreakers,
# secrets.rotation_policy) came back clean; these did not.
#
#   secrets.never_read_paths  -> mapfile -t PATS <<'PAT_EOF'      (templates
#   deps.approved             -> mapfile -t APPROVED <<'APPROVED_EOF'   .py)
#   hooks.drift_*             -> [ "$n" -ge <value> ]         (drift-detector)
#   commands.test/lint/ci_local -> ( <value> )      (test-gate, format-lint-
#                                                    gate, ci-mirror)
#
# The heredocs are QUOTED, so a pattern is normally inert. What is not inert
# is a pattern that IS the sentinel: it terminates the heredoc early, so
# (a) every later pattern becomes top-level shell in the hook - executed on
# EVERY invocation, a persistent primitive, not a one-shot - and (b) the
# array is silently TRUNCATED, so the patterns that were supposed to be
# guarded stop being guarded with no warning and rc=0 from the installer.
# deps.approved is worse: its mapfile sits above every early exit, so a
# poisoned entry bricks dependency-gate to rc=2 on EVERY PreToolUse call.
#
# The drift thresholds are the original P0-1 arithmetic-injection RCE
# re-entering through config: numeric fields with no type check, interpolated
# raw and unquoted. The file's own comment twelve lines above the sink claims
# that class was closed - for the STATE FILE, which was the only input anyone
# thought was untrusted.
#
# Two properties make this the cheapest fix available: it is one choke point
# (everything flows through resolve_config), and these fields have no
# validation today, so ADDING some cannot weaken a behavior that exists.
#
# The SDK substrate is immune - it embeds config through json.dumps, so every
# pattern survives intact - which is the proof that rejecting here costs
# nothing real: the SDK already shows what these configs are supposed to mean.

# C0 controls and DEL. A newline forges heredoc lines; the rest have no
# business in a glob, a package name or a threshold.
_CTRL = frozenset(chr(c) for c in list(range(0, 32)) + [127])

# Shell metacharacters that no path glob and no package name needs. Glob
# syntax (* ? [ ] { }) is deliberately ABSENT - `.env*` and `secrets/**` are
# the documented spellings - and so are the ordinary name characters
# (. - _ / @ + = ~ : ^ ,). This is a deny list of the characters that change
# what a shell DOES, kept narrow enough that no legitimate value trips it.
#
# `!` IS NOT HERE, and its absence is deliberate. The first cut of this list
# included it and rejected two legitimate values:
#   [!.]env      the POSIX/fnmatch negated class - and `_norm_pat` on the SDK
#                side converts `[^` INTO `[!` precisely because fnmatch reads
#                `[^` as a positive class containing `^`. So the fnmatch-native
#                spelling of a pattern this suite already supports was refused.
#   client!.key  `!` is a legal filename character.
# It is also harmless: history expansion does not run in a non-interactive
# shell, and nothing expands inside a QUOTED heredoc. Rejecting it bought
# nothing and cost two real configs - the false-positive direction this
# codebase keeps paying for.
_SHELL_META = frozenset("`$;&|<>()\"'\\*?")

# `*` and `?` ARE legal in a never-read glob, so the glob fields subtract
# them back out. Package names never need them.
_GLOB_OK = frozenset("*?[]")

# The heredoc sentinels the emitted hooks use. A value equal to one of these
# terminates its heredoc; a value merely CONTAINING one is rejected too,
# because the emitted body may gain a differently-indented heredoc later and
# a near-miss here is not worth the argument.
_HEREDOC_SENTINELS = ("PAT_EOF", "APPROVED_EOF")


def _bad_chars(value: str, allowed: frozenset) -> str:
    """The offending characters in `value`, in first-seen order, as a
    printable string. Empty when the value is clean."""
    seen, out = set(), []
    for ch in value:
        if ch in seen:
            continue
        if ch in _CTRL or (ch in _SHELL_META and ch not in allowed):
            seen.add(ch)
            out.append(repr(ch))
    return ", ".join(out)


def _quotes_balanced(cmd: str) -> bool:
    """Does `cmd` end outside every quote, with no dangling escape?

    Bash's own rule, which is the one that matters: inside `'...'` nothing
    escapes; inside `"..."` a backslash escapes; outside, a backslash escapes.
    An unbalanced quote here emits a hook bash cannot PARSE, so every commit
    is refused with a syntax error and no diagnosis - the operator sees a
    broken gate, not a broken config value.
    """
    state, esc = None, False
    for ch in cmd:
        if esc:
            esc = False
            continue
        if state == "'":
            if ch == "'":
                state = None
        elif state == '"':
            if ch == "\\":
                esc = True
            elif ch == '"':
                state = None
        elif ch == "\\":
            esc = True
        elif ch in ("'", '"'):
            state = ch
    return state is None and not esc


def _normalize_never_read(patterns: list) -> tuple[list, list]:
    """[round-4 D18] Make the ordinary spellings mean what they obviously
    mean, and say so. Returns (expanded_patterns, notices).

    This is not a parsing bug and no technique the round-4 brief endorses can
    see it: both substrates agree, it reproduces at every commit, and a
    composition sweep varies COMMAND shape while this varies CONFIG shape.
    Measured at b1782ec, all installing rc=0 with no warning:

        ["**/secrets/**", "**/.env*"]  -> root-level `.env` and
                                          `secrets/prod.yaml` ALLOW
        ["./secrets/**", "./.env*"]    -> fully vacuous
        ["secrets/"]                   -> fully vacuous
        ["secrets"]                    -> fully vacuous

    The last is not in the brief and is the most natural spelling of all.
    A leading `**/` is how everyone writes "anywhere", and it is exactly what
    disables root-level protection, because `**` collapses to `*` for `case`
    and `*/secrets/*` cannot match a path with nothing before `secrets`.

    NORMALIZE rather than reject. Rejecting `**/secrets/**` makes the
    operator fight the tool over a spelling that is not wrong, and a gate an
    operator is fighting is a gate an operator deletes - the pressure this
    codebase keeps citing. Every rule below only ADDS patterns, never removes
    or rewrites one, so the block set can only widen: the same deny-list-bias
    argument the implicit leading `*` already rests on.

    The DEFAULT list is byte-identical through this function - `.env*`,
    `secrets/**`, `*.pem`, `*.key` all carry a glob and none carries a `./`,
    a `**/` or a trailing `/` - so no existing install, fixture or golden
    digest moves. Only configs that are silently vacuous today change.
    """
    out, notices, seen = [], [], set()

    def add(p):
        if p and p not in seen:
            seen.add(p)
            out.append(p)

    for pat in patterns:
        if not isinstance(pat, str) or not pat:
            add(pat)
            continue
        add(pat)                       # what the operator wrote always stays
        root = pat
        while root.startswith("./"):
            root = root[2:]
        while root.startswith("**/"):
            root = root[3:]
        if root != pat and root:
            add(root)
            notices.append(
                f"secrets.never_read_paths: {pat!r} does not match a "
                f"root-level path ('**' collapses to '*' and '*/…' needs a "
                f"leading directory). Also guarding {root!r}.")
        for cand in (pat, root):
            if not cand:
                continue
            if cand.endswith("/"):
                sub = cand + "**"
            elif not (set(cand) & _GLOB_OK):
                sub = cand.rstrip("/") + "/**"
            else:
                continue
            if sub not in seen:
                add(sub)
                notices.append(
                    f"secrets.never_read_paths: {cand!r} names a directory "
                    f"but matches no path under it. Also guarding {sub!r}.")
    return out, notices


def _validate_shell_reaching(cfg: dict, errors: list) -> list:
    """Validate every config field that reaches executable shell. Returns the
    list of operator notices (non-fatal); appends to `errors` for the fatal
    ones. Runs for BOTH modes: the retrofit hook bodies wrap the greenfield
    ones, so every sink below is reachable from either."""
    notices: list[str] = []

    # ---- the two quoted-heredoc list fields ------------------------------
    for field, values, allowed in (
            ("secrets.never_read_paths",
             cfg.get("secrets", {}).get("never_read_paths"), _GLOB_OK),
            ("deps.approved",
             cfg.get("deps", {}).get("approved"), frozenset())):
        if values is None:
            continue
        if not isinstance(values, list):
            errors.append(f"{field} must be a list of strings; got "
                          f"{type(values).__name__}")
            continue
        for i, v in enumerate(values):
            where = f"{field}[{i}]"
            if not isinstance(v, str):
                errors.append(f"{where} must be a string; got "
                              f"{type(v).__name__} ({v!r})")
                continue
            for sentinel in _HEREDOC_SENTINELS:
                if sentinel in v:
                    errors.append(
                        f"{where} contains the heredoc sentinel {sentinel!r} "
                        f"({v!r}). That value terminates the emitted "
                        f"heredoc: every entry after it becomes shell code "
                        f"the hook EXECUTES, and the list itself is silently "
                        f"truncated so the remaining entries stop guarding "
                        f"anything.")
                    break
            bad = _bad_chars(v, allowed)
            if bad:
                errors.append(
                    f"{where} contains characters that are not valid here: "
                    f"{bad} (in {v!r}). This value is written VERBATIM into an "
                    f"emitted shell hook and is never expanded, so `$HOME` and "
                    f"`$(...)` cannot mean what they look like - write the "
                    f"literal path, or a glob.")

    # ---- the numeric drift thresholds ------------------------------------
    # Interpolated raw and UNQUOTED into `[ "$n" -ge <value> ]`, which runs on
    # every PostToolUse event, so a value of `$(...)` is command execution -
    # the P0-1 arithmetic-injection class arriving through config instead of
    # through the state file. bool is excluded explicitly: it is an int
    # subclass in Python and `True` would render as `True`, not as a number.
    h = cfg.get("hooks", {})
    for key, lo in (("drift_tool_call_threshold", 1),
                    ("drift_session_duration_minutes", 1),
                    ("drift_file_read_threshold", 1)):
        if key not in h:
            continue
        v = h[key]
        if isinstance(v, bool) or not isinstance(v, int):
            errors.append(
                f"hooks.{key} must be an integer; got "
                f"{type(v).__name__} ({v!r}). It is interpolated unquoted "
                f"into a shell test that runs on every tool call.")
        elif v < lo:
            errors.append(f"hooks.{key} must be >= {lo}; got {v!r}")

    # ---- the command fields ----------------------------------------------
    # These are MEANT to be shell, so execution is by design and there is
    # nothing to reject on that count. The defect is narrower: an unbalanced
    # quote emits a hook bash cannot parse, so every commit is refused with a
    # syntax error and no diagnosis. A newline breaks the single-line
    # `echo "Running test gate: <cmd>"` the same way.
    for key in ("test", "lint", "format", "typecheck", "ci_local"):
        v = cfg.get("commands", {}).get(key)
        if v in (None, ""):
            continue
        if not isinstance(v, str):
            errors.append(f"commands.{key} must be a string; got "
                          f"{type(v).__name__} ({v!r})")
            continue
        ctrl = sorted({repr(ch) for ch in v if ch in _CTRL and ch != "\t"})
        if ctrl:
            errors.append(
                f"commands.{key} contains {', '.join(ctrl)}; it is emitted "
                f"on one line of a shell hook. Put a multi-line command in a "
                f"script and call the script.")
        elif not _quotes_balanced(v):
            errors.append(
                f"commands.{key} has an unbalanced quote or a trailing "
                f"backslash ({v!r}). The emitted hook would not PARSE, so "
                f"every gated action is refused with a bash syntax error and "
                f"no explanation of why.")

    # ---- [W-1] commands.execute_in_cwd must be a real boolean ------------
    # minyaml yields a Python bool for unquoted true/false; a quoted "false"
    # arrives as the string "false", which is truthy. Silently reading that as
    # "yes, cwd is honored" re-arms the exact fail-open this key exists to
    # close, so the type is checked rather than coerced.
    eic = cfg.get("commands", {}).get("execute_in_cwd", True)
    if not isinstance(eic, bool):
        errors.append(
            f"commands.execute_in_cwd must be a boolean (unquoted true or "
            f"false); got {type(eic).__name__} ({eic!r}). It decides whether "
            f"the implementer agent is emitted with `isolation: worktree`, "
            f"and a quoted \"false\" would read as true.")

    # ---- [D18] never_read_paths spellings that guard nothing -------------
    sec = cfg.get("secrets", {})
    if isinstance(sec.get("never_read_paths"), list):
        expanded, d18_notices = _normalize_never_read(sec["never_read_paths"])
        sec["never_read_paths"] = expanded
        notices.extend(d18_notices)
    return notices


ARCHETYPES = {
    "cli", "library", "service", "fullstack", "mobile",
    "data-ml", "ai-agent", "platform", "other",
}

# [W-1] workflow.implementer_isolation — the operator's lever over the
# `isolation:` line in the emitted implementer agent. Before this key the value
# was hardcoded, so an operator whose commands do not honor cwd could only
# hand-edit `implementer.md` — which trips the digest hand-edit guard and makes
# that file SKIP forever, keeping their fix and losing every upstream fix.
#   auto      derive from commands.execute_in_cwd (worktree when true, none
#             when false). The default: the protocol decides, and the decision
#             follows the one fact that determines whether it is sound.
#   worktree  force the isolation on regardless of the commands answer.
#   none      force it off regardless.
IMPLEMENTER_ISOLATIONS = {"auto", "worktree", "none"}


def _resolve_implementer_isolation(cfg: dict, errors: list) -> None:
    """[W-1] Decide the implementer's `isolation:` line and say why.

    Worktree isolation and the Phase 2 command contract are two protocol
    features that do not automatically compose. The emitted gates run the
    configured command bare — no `cd`, no `$CLAUDE_PROJECT_DIR` — which is
    correct: a plain `pytest -q` inherits the hook process's cwd, and inside a
    worktree that cwd IS the worktree, so plain commands compose fine.

    What breaks is FIXED-MOUNT INDIRECTION. `docker compose exec -T app pytest`
    lands inside a container whose bind mount points at the main checkout, so
    cwd is irrelevant — the command always runs against `/app`. Same shape for
    `kubectl exec`, `ssh`, `vagrant ssh`, and devcontainer CLIs. (`docker run
    -v "$(pwd)":/app` DOES follow cwd and is fine; the fixed mount is the
    problem.) An implementer working in `.claude/worktrees/<n>/` then has its
    gate compile and test the MAIN checkout: the gate passes, and the code the
    agent actually wrote was never built. That is a fail-open in a verification
    control — the same class as P0-3d, and reachable with nothing more exotic
    than a containerized dev environment.

    So the default resolution (`auto`) drops `isolation: worktree` when the
    operator declares the commands do not honor cwd. Losing the isolation costs
    parallelism and is LOUD when it bites (two implementers touching one tree
    collide visibly); keeping it costs a green gate on uncompiled code and is
    SILENT. Trading a silent fail-open for a visible constraint is the same
    call A-1 made.

    Sets `cfg["_implementer_isolation"]` to "worktree" or "none" and, for the
    non-default paths, appends an install-time note to `_config_notices`.
    """
    w = cfg.get("workflow", {})
    requested = w.get("implementer_isolation", "auto")
    if requested not in IMPLEMENTER_ISOLATIONS:
        errors.append(
            f"workflow.implementer_isolation must be one of "
            f"{sorted(IMPLEMENTER_ISOLATIONS)}; got {requested!r}")
        # Resolve to the safe status quo so downstream templates still render
        # while the installer refuses on the error above.
        cfg["_implementer_isolation"] = "worktree"
        return

    honors_cwd = cfg.get("commands", {}).get("execute_in_cwd", True)
    honors_cwd = honors_cwd if isinstance(honors_cwd, bool) else True
    notices = cfg.setdefault("_config_notices", [])

    if requested == "auto":
        resolved = "worktree" if honors_cwd else "none"
        if not honors_cwd:
            notices.append(
                "commands.execute_in_cwd is false, so the implementer agent "
                "is emitted WITHOUT `isolation: worktree` and the queue's "
                "max_concurrent_tasks starts at 1. Commands that ignore cwd "
                "(docker compose exec, kubectl exec, ssh) would otherwise run "
                "the gate against the main checkout while the agent worked in "
                "a worktree — a gate passing on code it never built. Set "
                "workflow.implementer_isolation: worktree to override.")
    else:
        resolved = requested
        if requested == "worktree" and not honors_cwd:
            notices.append(
                "workflow.implementer_isolation is FORCED to 'worktree' while "
                "commands.execute_in_cwd is false. The implementer will work "
                "in .claude/worktrees/<n>/ while its test/lint gates run "
                "wherever the fixed mount points — so a gate can report green "
                "on code it never compiled. Only sound if each worktree gets "
                "its own mount (e.g. a per-worktree compose project). "
                "Verify with: docker compose exec -T <svc> pwd")
        elif requested == "none" and honors_cwd:
            notices.append(
                "workflow.implementer_isolation is FORCED to 'none' though "
                "commands.execute_in_cwd is true. Parallel implementer tasks "
                "will share one working tree; keep max_concurrent_tasks at 1 "
                "unless you have another isolation mechanism.")

    cfg["_implementer_isolation"] = resolved


# Phase 4 step 2 starter principle sets, verbatim intent from Bootstrap-Protocol-v2-0-0.md.
PRINCIPLE_STARTERS = {
    "cli": [
        "Predictable behavior over feature breadth",
        "Clear error messages over recovery cleverness",
        "YAGNI before flag proliferation",
    ],
    "library": [
        "API stability over internal cleanliness",
        "Explicit over magical",
        "YAGNI before abstraction",
    ],
    "service": [
        "Clear errors over silent fallbacks",
        "Explicit schemas over duck typing",
        "Instrument before optimize",
    ],
    "fullstack": [
        "User-visible correctness over code elegance",
        "YAGNI before the third duplication",
        "Tests describe intent",
    ],
    "mobile": [
        "Offline-first where possible",
        "User-perceived performance over benchmark performance",
        "Platform conventions over cross-platform purity",
    ],
    "data-ml": [
        "Reproducibility over speed",
        "Explicit data contracts",
        "Fail loud on schema drift",
    ],
    "ai-agent": [
        "Determinism where possible",
        "Evals before refactors",
        "Cost-awareness in every call",
    ],
    "platform": [
        "Component independence over shared abstractions",
        "Explicit interfaces between components",
        "YAGNI for cross-component features",
    ],
    "other": [
        "Correctness over cleverness",
        "Explicit over implicit",
        "YAGNI before abstraction",
    ],
}

# --------------------------------------------------------------------------- #
# Retrofit-mode enums and defaults (additive; greenfield path is untouched -
# the retrofit branch in resolve_config runs only when cfg["mode"] == "retrofit"
# and the D2 golden test asserts greenfield output is byte-identical).
# --------------------------------------------------------------------------- #
MODES = {"bootstrap", "retrofit"}

RETROFIT_SPEC_STRATEGIES = {"forward-only", "touch-based", "bulk"}
RETROFIT_PM_STRATEGIES = {"spec_canonical", "pm_canonical", "hybrid"}
RETROFIT_ARCHETYPE_CONFIDENCES = {"high", "medium", "low"}
RETROFIT_PM_TOOLS = {"linear", "jira", "github_issues", "tickets_dir", "none"}
RETROFIT_PM_TOOL_ROLES_AFTER = {
    "removed", "bridge_only", "community_facing", "hybrid_transitional",
}
RETROFIT_CI_CD_APPLICABILITY = {"yes", "no", "unknown"}

# Base hook set (Phase 6 "all" hooks). Conditional ones added in resolve.
BASE_HOOKS = [
    "spec-gate-entry",
    "spec-gate-commit",
    "test-gate",
    "format-lint-gate",
    "cost-log",
    "dependency-gate",
    "drift-detector",
    "task-done-alarm",
    "decision-required-alarm",
]


def _deep_default(dst: dict, src: dict) -> dict:
    """Fill defaults for keys the user did NOT provide.

    Rule: a key present in `dst` is the user's choice and is never
    overwritten (including explicit false/0/""/null - those are intentional).
    Only absent keys receive the default. This replaces an earlier version
    whose operator-precedence (`a or b and c`) made the intent unclear and
    fragile if defaults ever held non-None scalars (review finding C-1).
    """
    for k, v in src.items():
        if k not in dst:
            dst[k] = copy.deepcopy(v)
        elif isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_default(dst[k], v)
    return dst


# --------------------------------------------------------------------------- #
# Retrofit defaults. Applied ONLY when cfg["mode"] == "retrofit"; greenfield
# configs never see these. The shape mirrors RETROFIT.md v1.6.2's R0.5/R0.7/
# R4/R8.A.6/R8.G-I requirements. Decision layer (lib/retrofit_interview.py)
# populates everything from inventory; resolve_config just fills absent keys.
# --------------------------------------------------------------------------- #
RETROFIT_DEFAULTS = {
    "state_path": ".claude/inventory",
    "archetype_confidence": "low",
    "archetype_evidence": [],
    "synthetic_profile": {},
    "prd_tier_target": "standard",
    "ci_cd_applicability": "unknown",
    "spec_strategy": "forward-only",
    "legacy_allowlist": [],
    "retrofit_active": True,
    # Round-3 review (Lens C2): R0.8 commit gate. Default false; wizard
    # sets true after the operator approves the R0.8 preview. The
    # installer refuses to write artifacts unless this is true OR
    # skip_decisions.r08 is true (operator opted out of R0.8 at R0.5
    # step 7). RETROFIT.md R0.8 step 7: "no .claude/ artifacts are
    # written from this point forward" after cancel.
    "r08_committed": False,
    "r08_committed_at": None,
    "spec_patterns": {
        "change": True, "boundary": False, "migration": False,
    },
    "pm": {
        "strategy": "spec_canonical",
        "tool": "none",
        "tool_role_after": "removed",
        "ticket_migration": {
            "convert_now": [], "defer": [], "close": [],
        },
        "hybrid_review_date": None,
    },
    "regulatory_regimes": [],
    "codebase_size_gb": 0,
    "autonomous_modes": {
        "loop_mode_opted_in": False,
        "goal_supervised_mode_opted_in": False,
        "queue_mode_opted_in": False,
        "brownfield_milestones": {
            "rollout_steady_state_spec_test_gate": False,
            "rollout_steady_state_all_hooks": False,
            "touch_based_specs_under_blocking_gates": 0,
            "touch_based_specs_threshold": 10,
            "legacy_allowlist_size_at_retrofit": None,
            "legacy_allowlist_current_size": None,
            "legacy_allowlist_shrink_threshold_pct": 25,
            "mode_selection_ledger_entries": 0,
            "weeks_real_per_task_operation_post_blocking": 0,
        },
    },
    "debt": {"entries": []},
    "inventory_summary": {
        "has_prior_claude": False,
        "has_root_claude_md": False,
        "danger_zone_count": 0,
        "no_test_module_count": 0,
    },
}


DEFAULTS = {
    "project": {"shell": "bash", "prd_tier": "standard",
                "cicd_opt_out": False, "prd_path": "docs/prd/PRD.md"},
    "autonomous_modes": {"loop_mode_enabled": False,
                         "goal_supervised_mode_enabled": False,
                         "queue_mode_enabled": False},
    "principles": {"ranked": [], "tiebreakers": [],
                   "tdd_policy": "encouraged"},
    "secrets": {"enabled": True, "never_read_paths": [
        ".env*", "secrets/**", "*.pem", "*.key"],
        "rotation_policy": "Rotate any exposed credential immediately."},
    "deps": {"enabled": True, "approved": []},
    "hooks": {
        "spec_gate_entry": True, "spec_gate_commit": True,
        "secrets_gate": True, "test_gate": True,
        "format_lint_gate": True, "ci_mirror": True, "cost_log": True,
        "tdd_gate": None, "dependency_gate": True, "eval_gate": None,
        "drift_detector": True, "task_done_alarm": True,
        "decision_required_alarm": True,
        "drift_tool_call_threshold": 50,
        "drift_session_duration_minutes": 120,
        "drift_file_read_threshold": 3,
    },
    "commands": {"test": "", "lint": "", "format": "",
                 "typecheck": "", "ci_local": "",
                 # [W-1] Do the five commands above honor the working directory
                 # they are invoked from? True for anything that runs locally
                 # (`pytest -q`, `npm test`) and for cwd-following container
                 # invocations (`docker run -v "$(pwd)":/app ...`). FALSE for
                 # fixed-mount indirection — `docker compose exec`, `kubectl
                 # exec`, `ssh`, `vagrant ssh`, devcontainer CLIs — where the
                 # command lands in a tree chosen by the mount, not by cwd.
                 "execute_in_cwd": True},
    "mcp": {"servers": [], "rejected": []},
    "workflow": {"install_skills": True, "install_commands": True,
                 "install_agents": True, "implementer_model": "sonnet",
                 "reviewer_model": "opus", "integrator_model": "inherit",
                 "implementer_isolation": "auto"},
}


def resolve_config(raw: dict) -> tuple[dict, list[str]]:
    errors: list[str] = []
    cfg = copy.deepcopy(raw) if raw else {}

    if "project" not in cfg or "name" not in cfg.get("project", {}):
        errors.append("project.name is required")
    _deep_default(cfg, DEFAULTS)

    # mode: default "bootstrap" preserves byte-identity of every existing
    # config (greenfield-as-of-pre-retrofit-installer cfgs implicitly carry
    # this default). Retrofit configs declare mode: "retrofit" and trigger
    # the retrofit branch below.
    mode = cfg.get("mode", "bootstrap")
    if mode not in MODES:
        errors.append(f"mode must be one of {sorted(MODES)}; got {mode!r}")
        return cfg, errors
    cfg["mode"] = mode

    # ---- R-9: requested enforcement substrate (Milestone B) --------------- #
    # Validated BEFORE the archetype early-return so its errors batch with
    # every other validation (surfacing on the first run, not one fix-cycle
    # later). Top-level scalar, default "shell" (byte-identity for every
    # existing config). "sdk-callable" is a REQUEST: the installer grants
    # it only when every IC-1..IC-7 self-check passes (lib/ic_checks.py),
    # else the install is refused loudly (AC-9-1). An invalid value is
    # normalized to "shell" (fail-safe: a downstream that ignores the
    # errors list must never inherit an arbitrary security-relevant value).
    substrate = cfg.get("gate_substrate", "shell")
    if substrate not in ("shell", "sdk-callable"):
        errors.append('gate_substrate must be "shell" or "sdk-callable"; '
                      f"got {substrate!r}")
        substrate = "shell"
    elif substrate == "sdk-callable" and mode == "retrofit":
        errors.append(
            "gate_substrate: sdk-callable is not available in retrofit "
            "mode - the retrofit track is shell-era "
            "(RETROFIT_PROTOCOL_VERSION) and the overlay drops the SDK "
            "gate module.")
    cfg["gate_substrate"] = substrate

    arche = cfg["project"].get("archetype")
    if arche not in ARCHETYPES:
        errors.append(
            f"project.archetype must be one of {sorted(ARCHETYPES)}; "
            f"got {arche!r}")
        return cfg, errors

    flags = cfg["autonomous_modes"]

    # ---- Bootstrap-Protocol-v2-0-0.md skip-policy invariant: queue requires loop|goal ----- #
    if flags["queue_mode_enabled"] and not (
            flags["loop_mode_enabled"] or flags["goal_supervised_mode_enabled"]):
        errors.append(
            "autonomous_modes.queue_mode_enabled requires at least one of "
            "loop_mode_enabled or goal_supervised_mode_enabled "
            "(Bootstrap-Protocol-v2-0-0.md Phase 9.7 / skip policy).")

    # ---- Principles: fill starter set if empty (Phase 4) ------------------ #
    if not cfg["principles"]["ranked"]:
        cfg["principles"]["ranked"] = list(PRINCIPLE_STARTERS[arche])

    tdd = cfg["principles"]["tdd_policy"]
    if tdd not in ("off", "encouraged", "required"):
        errors.append("principles.tdd_policy must be off|encouraged|required")

    # ---- Resolve the conditional hook set (Phase 6) ----------------------- #
    hooks = list(BASE_HOOKS)
    h = cfg["hooks"]

    if cfg["secrets"]["enabled"] and h.get("secrets_gate", True):
        hooks.insert(2, "secrets-gate")

    if not cfg["project"]["cicd_opt_out"] and h.get("ci_mirror", True):
        hooks.append("ci-mirror")

    # tdd_gate: explicit override wins; else derive from policy
    tdd_gate = h.get("tdd_gate")
    if tdd_gate is True or (tdd_gate is None and tdd == "required"):
        hooks.append("tdd-gate")

    # eval_gate: explicit override wins; else ai-agent only
    eval_gate = h.get("eval_gate")
    if eval_gate is True or (eval_gate is None and arche == "ai-agent"):
        hooks.append("eval-gate")

    # loop/goal cooperation hook (Phase 6, 9.5/9.6)
    if flags["loop_mode_enabled"] or flags["goal_supervised_mode_enabled"]:
        hooks.append("drift-detector-loop-cooperation")
    if flags["goal_supervised_mode_enabled"]:
        hooks.append("iteration-summary-enforcement")

    # honour explicit per-hook disables for the toggleable base hooks
    toggle_map = {
        "spec-gate-entry": "spec_gate_entry",
        "spec-gate-commit": "spec_gate_commit",
        "test-gate": "test_gate",
        "format-lint-gate": "format_lint_gate",
        "cost-log": "cost_log",
        "dependency-gate": "dependency_gate",
        "drift-detector": "drift_detector",
        "task-done-alarm": "task_done_alarm",
        "decision-required-alarm": "decision_required_alarm",
    }
    hooks = [hk for hk in hooks
             if toggle_map.get(hk) is None or h.get(toggle_map[hk], True)]

    # de-dupe preserving order
    seen, ordered = set(), []
    for hk in hooks:
        if hk not in seen:
            ordered.append(hk)
            seen.add(hk)
    cfg["_resolved_hooks"] = ordered

    # ---- Warn-not-fail: empty gate commands -> loud TODO in hook --------- #
    cmds = cfg["commands"]
    cfg["_command_warnings"] = [
        name for name in ("test", "lint", "format")
        if not cmds.get(name)]

    # ---- [round-4 D12/D18] the shell-reaching fields --------------------- #
    # Placed here, ahead of the retrofit branch, so it covers BOTH modes: the
    # retrofit hook bodies prefix a preamble onto the greenfield bodies, so
    # every sink is reachable from either. Fatal problems go to `errors` (the
    # installer refuses); spelling problems normalize and report.
    cfg["_config_notices"] = _validate_shell_reaching(cfg, errors)

    # ---- [W-1] worktree isolation vs. where the gate commands execute ---- #
    # Placed ahead of the retrofit branch: both modes emit an `implementer`
    # agent whose `isolation:` line is decided here, and both read the same
    # `commands` block, so the derivation must cover both.
    _resolve_implementer_isolation(cfg, errors)

    # ---- Retrofit-mode: fill defaults + validate retrofit invariants ----- #
    # Runs only when mode == "retrofit". Greenfield path is byte-identical
    # because (a) nothing above this point reads cfg["retrofit"], (b) the
    # `mode` field is the only addition to greenfield cfg and is not read
    # by any template fn (verified by D2 golden test).
    if mode == "retrofit":
        cfg.setdefault("retrofit", {})
        _deep_default(cfg["retrofit"], RETROFIT_DEFAULTS)
        r = cfg["retrofit"]

        if r["spec_strategy"] not in RETROFIT_SPEC_STRATEGIES:
            errors.append(
                f"retrofit.spec_strategy must be one of "
                f"{sorted(RETROFIT_SPEC_STRATEGIES)}; got "
                f"{r['spec_strategy']!r}")
        if r["pm"]["strategy"] not in RETROFIT_PM_STRATEGIES:
            errors.append(
                f"retrofit.pm.strategy must be one of "
                f"{sorted(RETROFIT_PM_STRATEGIES)}; got "
                f"{r['pm']['strategy']!r}")
        if r["pm"]["tool"] not in RETROFIT_PM_TOOLS:
            errors.append(
                f"retrofit.pm.tool must be one of "
                f"{sorted(RETROFIT_PM_TOOLS)}; got {r['pm']['tool']!r}")
        if r["pm"]["tool_role_after"] not in RETROFIT_PM_TOOL_ROLES_AFTER:
            errors.append(
                f"retrofit.pm.tool_role_after must be one of "
                f"{sorted(RETROFIT_PM_TOOL_ROLES_AFTER)}; got "
                f"{r['pm']['tool_role_after']!r}")
        if r["ci_cd_applicability"] not in RETROFIT_CI_CD_APPLICABILITY:
            errors.append(
                f"retrofit.ci_cd_applicability must be one of "
                f"{sorted(RETROFIT_CI_CD_APPLICABILITY)}; got "
                f"{r['ci_cd_applicability']!r}")
        if r["archetype_confidence"] not in RETROFIT_ARCHETYPE_CONFIDENCES:
            errors.append(
                f"retrofit.archetype_confidence must be one of "
                f"{sorted(RETROFIT_ARCHETYPE_CONFIDENCES)}; got "
                f"{r['archetype_confidence']!r}")

        # B5: the runtime *_enabled flags MUST be false at retrofit time
        # regardless of operator opt-in. The wizard scaffolds but defers.
        # Enforced here because the installer cannot trust a hand-edited cfg
        # to honour the rule on its own. (Opt-in intent lives in
        # cfg["retrofit"]["autonomous_modes"]["*_opted_in"]; enable flags
        # live in cfg["autonomous_modes"] and must stay false.)
        for flag in ("loop_mode_enabled", "goal_supervised_mode_enabled",
                     "queue_mode_enabled"):
            if cfg["autonomous_modes"].get(flag):
                errors.append(
                    f"autonomous_modes.{flag} must be false at retrofit "
                    f"time (RETROFIT v1.6.2 scaffold-but-defer rule). "
                    f"Record opt-in intent in "
                    f"retrofit.autonomous_modes.{flag.replace('_enabled', '_opted_in')} "
                    f"instead; the operator flips *_enabled post-retrofit "
                    f"after the brownfield trust milestone is green.")

        # Round-2 review, Lens 5.1 — structural dual-shape validator. A
        # contributor adding a new field to the wrong half of the schema
        # (e.g. *_enabled nested under retrofit, or *_opted_in /
        # brownfield_milestones top-level) is the failure mode T1 pins
        # in tests; this validator pins it at runtime too. The contract
        # is the inverse of the B5 split.
        _rf_am = r.get("autonomous_modes", {})
        _top_am = cfg.get("autonomous_modes", {})
        _wrong_in_nested = [
            k for k in ("loop_mode_enabled",
                        "goal_supervised_mode_enabled",
                        "queue_mode_enabled",
                        "loop_in_flight", "goal_in_flight",
                        "queue_runs_history")
            if k in _rf_am]
        _wrong_in_top = [
            k for k in ("loop_mode_opted_in",
                        "goal_supervised_mode_opted_in",
                        "queue_mode_opted_in", "brownfield_milestones")
            if k in _top_am]
        for k in _wrong_in_nested:
            errors.append(
                f"retrofit.autonomous_modes.{k} is wrong-shape: "
                f"{k!r} belongs at top-level autonomous_modes (B5 "
                f"dual-shape contract). Nested location is for "
                f"*_opted_in / brownfield_milestones only.")
        for k in _wrong_in_top:
            errors.append(
                f"autonomous_modes.{k} is wrong-shape: {k!r} belongs "
                f"nested under retrofit.autonomous_modes (B5 dual-"
                f"shape contract). Top-level is for *_enabled / "
                f"*_in_flight / queue_runs_history only.")

        # Round-2 review, Lens 1.1 — R8.I prereq parallel to greenfield's
        # queue_mode_enabled requires loop or goal_supervised_mode_enabled
        # (defaults.py line 232 above). Retrofit's opt-in path needs the
        # same gate or queue scaffolding has nothing to dispatch.
        if _rf_am.get("queue_mode_opted_in") and not (
                _rf_am.get("loop_mode_opted_in")
                or _rf_am.get("goal_supervised_mode_opted_in")):
            errors.append(
                "retrofit.autonomous_modes.queue_mode_opted_in requires "
                "at least one of loop_mode_opted_in or "
                "goal_supervised_mode_opted_in (RETROFIT R8.I "
                "prereq — queue dispatches per-task wrappers; with "
                "none scaffolded there is nothing to dispatch).")

        # Round-2 review, Lens 1.1 — wire the drift-detector loop-
        # cooperation hook on opt-in (the greenfield gate at line ~268
        # reads *_enabled, which is pinned false at retrofit time).
        # Same hook serves R8.G and R8.H per RETROFIT.md R8.G step 1.
        if (_rf_am.get("loop_mode_opted_in")
                or _rf_am.get("goal_supervised_mode_opted_in")):
            if "drift-detector-loop-cooperation" not in cfg["_resolved_hooks"]:
                cfg["_resolved_hooks"].append(
                    "drift-detector-loop-cooperation")
        if _rf_am.get("goal_supervised_mode_opted_in"):
            if "iteration-summary-enforcement" not in cfg["_resolved_hooks"]:
                cfg["_resolved_hooks"].append("iteration-summary-enforcement")

        # Round-3 review (Lens C2) — R0.8 commit gate. The spec at
        # RETROFIT.md R0.8 step 7 forbids any .claude/ artifact write
        # after operator cancel. The wizard sets cfg.retrofit.r08_committed
        # = true after R0.5/R0.7/R0.8 reach proceed; the installer
        # rejects an unconfirmed cfg here. skip_decisions.r08 is the
        # explicit operator opt-out at R0.5 step 7 (RETROFIT R0.5
        # skippable-decisions row).
        if not r.get("skip_decisions", {}).get("r08"):
            if r.get("r08_committed") is not True:
                errors.append(
                    "retrofit.r08_committed must be True before "
                    "bootstrap-install may write artifacts "
                    "(RETROFIT R0.8 step 7 — cancel preserves "
                    "state but writes no .claude/ artifacts). "
                    "Either set retrofit.r08_committed: true (the "
                    "wizard does this at R0.8 proceed) or set "
                    "retrofit.skip_decisions.r08: true (the "
                    "operator opted out of R0.8 at R0.5 step 7).")

        # Round-2 review, Lens 1.3 — R0.7 hybrid_review_date is
        # conditional-required when pm_strategy == "hybrid". RETROFIT.md
        # R0.7 schema says it is null if not Strategy C, present if so.
        # An ISO-format date string is required; basic non-empty check.
        if r["pm"]["strategy"] == "hybrid":
            hrd = r["pm"].get("hybrid_review_date")
            if not hrd or not isinstance(hrd, str):
                errors.append(
                    "retrofit.pm.hybrid_review_date is required when "
                    "retrofit.pm.strategy == 'hybrid' (RETROFIT R0.7 "
                    "Strategy C — the operator-set review date for "
                    "the hybrid arrangement). Set it to an ISO date "
                    "string (YYYY-MM-DD).")

        # Warn-not-fail: migration spec pattern without a non-empty legacy
        # allowlist usually means nothing to strangle.
        cfg["_retrofit_warnings"] = []
        if r["spec_patterns"]["migration"] and not r["legacy_allowlist"]:
            cfg["_retrofit_warnings"].append(
                "retrofit.spec_patterns.migration is true but "
                "retrofit.legacy_allowlist is empty - migration specs "
                "usually presuppose legacy code to strangle. Confirm.")

    return cfg, errors

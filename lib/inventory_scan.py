"""
Codebase inventory scanner for retrofit (RETROFIT.md v1.6.2 Phase R0).

Produces a structured InventoryData dict by walking the repo and rendering
.claude/inventory/*.md from it. Decision-layer-only: the installer never
runs this (per OD-5: codebase-derived artifacts live with the decision
layer to preserve installer determinism).

Design rules:
  * Pure functions of the repo state at scan time. No network. No mutation
    outside .claude/inventory/.
  * Degraded mode: when git or a tool is absent the scanner records what
    was lost in the corresponding markdown file rather than failing.
  * Conservative file walking: respect a built-in exclude list (vendored,
    docs, generated, .venv, etc.) matching RETROFIT.md R-1 step 4.

Stdlib only - same dependency-free contract as the rest of the package.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


# Paths excluded from "source file" counts and most scans (RETROFIT.md R-1
# step 4 default exclude list; operator can extend at scan time).
DEFAULT_EXCLUDE_DIRS = {
    "docs", "tickets", "tutorials", "examples", "example", "samples",
    "sample", "vendor", "node_modules", ".venv", "venv", "env",
    "generated", ".scratch", "build", "dist", "target", "out",
    ".git", ".claude", ".claude.archived", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", ".nox", "coverage",
    ".idea", ".vscode",
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".rb", ".go", ".rs",
    ".java", ".kt", ".swift", ".m", ".mm", ".c", ".cc", ".cpp",
    ".h", ".hpp", ".cs", ".php", ".scala", ".clj", ".ex", ".exs",
    ".erl", ".hs", ".ml", ".dart", ".sh", ".bash", ".zsh",
}

TEST_FILE_PATTERNS = [
    re.compile(r"(^|/)test_[^/]+\.py$"),
    re.compile(r"(^|/)[^/]+_test\.py$"),
    re.compile(r"(^|/)tests?/[^/]+\.py$"),
    re.compile(r"\.test\.(jsx?|tsx?)$"),
    re.compile(r"\.spec\.(jsx?|tsx?)$"),
    re.compile(r"_test\.go$"),
    re.compile(r"_test\.rs$"),
    re.compile(r"(^|/)test/[^/]+\.(java|kt|scala)$"),
]


def _is_excluded(rel_path: str) -> bool:
    parts = rel_path.split(os.sep)
    return any(p in DEFAULT_EXCLUDE_DIRS or p.startswith(".claude.archived")
               for p in parts)


def _walk_source(root: Path):
    """Yield (rel_path, abs_path) for every source-eligible file, honoring
    DEFAULT_EXCLUDE_DIRS. Deterministic order (sorted)."""
    out = []
    root_str = str(root)
    for base, dirs, files in os.walk(root_str):
        dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDE_DIRS
                   and not d.startswith(".claude.archived")]
        for fn in files:
            abs_p = os.path.join(base, fn)
            rel = os.path.relpath(abs_p, root_str)
            if _is_excluded(rel):
                continue
            out.append((rel, abs_p))
    return sorted(out)


def _read_safely(abs_path: str, max_bytes: int = 200_000) -> str:
    try:
        with open(abs_path, "rb") as fh:
            raw = fh.read(max_bytes)
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _has_tool(name: str) -> bool:
    return subprocess.run(["which", name],
                           capture_output=True).returncode == 0


# --------------------------------------------------------------------------- #
# Per-dimension scanners
# --------------------------------------------------------------------------- #
def scan_structure(root: Path) -> dict:
    """Top-level directory inventory: dir name, file count, LOC proxy."""
    top: dict[str, dict] = {}
    files_at_root = []
    for entry in sorted(os.listdir(root)):
        abs_p = root / entry
        if entry in DEFAULT_EXCLUDE_DIRS or entry.startswith(
                ".claude.archived"):
            continue
        if abs_p.is_dir():
            count = 0
            loc = 0
            for base, dirs, files in os.walk(abs_p):
                dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDE_DIRS]
                for fn in files:
                    if Path(fn).suffix in SOURCE_EXTENSIONS:
                        count += 1
                        try:
                            with open(os.path.join(base, fn),
                                       errors="replace") as fh:
                                loc += sum(1 for _ in fh)
                        except OSError:
                            pass
            top[entry] = {"source_files": count, "loc_proxy": loc}
        elif abs_p.is_file():
            files_at_root.append(entry)
    return {"top_level_dirs": top, "top_level_files": files_at_root}


def scan_languages(root: Path) -> dict:
    """File-count breakdown by extension; manifest-file detection."""
    by_ext: dict[str, int] = {}
    manifests = {
        "pyproject.toml": False, "setup.py": False, "setup.cfg": False,
        "requirements.txt": False, "Pipfile": False, "poetry.lock": False,
        "package.json": False, "package-lock.json": False, "yarn.lock": False,
        "pnpm-lock.yaml": False, "Cargo.toml": False, "go.mod": False,
        "Gemfile": False, "build.gradle": False, "pom.xml": False,
        "Makefile": False, "Dockerfile": False,
    }
    dockerfile_count = 0
    for rel, abs_p in _walk_source(root):
        ext = Path(rel).suffix
        if ext:
            by_ext[ext] = by_ext.get(ext, 0) + 1
        name = os.path.basename(rel)
        if name in manifests:
            manifests[name] = True
        if name == "Dockerfile" or name.startswith("Dockerfile."):
            dockerfile_count += 1
    return {
        "files_by_extension": dict(sorted(
            by_ext.items(), key=lambda kv: -kv[1])),
        "manifests": manifests,
        "dockerfile_count": dockerfile_count,
    }


def scan_dependencies(root: Path) -> dict:
    """Detect declared deps from manifests (no resolution; no network)."""
    deps: dict[str, list[str]] = {}
    inline_ticket_refs = 0
    ticket_re = re.compile(r"\b[A-Z]{2,}-\d+\b|#\d+")

    def _add(manifest_label: str, names: list[str]) -> None:
        if names:
            deps[manifest_label] = sorted(set(names))

    py_proj = root / "pyproject.toml"
    if py_proj.exists():
        txt = _read_safely(str(py_proj))
        names = re.findall(r"\"([A-Za-z0-9_.\-]+)\s*[<>=~^!]", txt)
        names += re.findall(r"^\s*([A-Za-z0-9_.\-]+)\s*=", txt, re.M)
        inline_ticket_refs += len(ticket_re.findall(txt))
        _add("pyproject.toml", names[:200])

    reqs = root / "requirements.txt"
    if reqs.exists():
        txt = _read_safely(str(reqs))
        names = []
        for line in txt.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            names.append(re.split(r"[<>=~!\[]", line, 1)[0].strip())
        inline_ticket_refs += len(ticket_re.findall(txt))
        _add("requirements.txt", names[:200])

    pkg = root / "package.json"
    if pkg.exists():
        try:
            doc = json.loads(_read_safely(str(pkg), 1_000_000))
            for section in ("dependencies", "devDependencies",
                            "peerDependencies"):
                if isinstance(doc.get(section), dict):
                    _add(f"package.json:{section}", list(doc[section].keys()))
        except (json.JSONDecodeError, ValueError):
            pass

    cargo = root / "Cargo.toml"
    if cargo.exists():
        txt = _read_safely(str(cargo))
        names = re.findall(r"^\s*([a-zA-Z0-9_\-]+)\s*=", txt, re.M)
        _add("Cargo.toml", names[:200])

    return {
        "by_manifest": deps,
        "inline_ticket_refs_count": inline_ticket_refs,
    }


def scan_testing(root: Path) -> dict:
    """Test framework detection + name-match coverage proxy."""
    test_files = []
    source_files = []
    source_modules: set[str] = set()
    for rel, _ in _walk_source(root):
        if any(p.search(rel) for p in TEST_FILE_PATTERNS):
            test_files.append(rel)
        elif Path(rel).suffix in SOURCE_EXTENSIONS:
            source_files.append(rel)
            stem = Path(rel).stem
            if stem and not stem.startswith("__"):
                source_modules.add(stem)

    # name-match coverage proxy
    test_stems = {Path(t).stem.replace("test_", "").replace("_test", "")
                  for t in test_files}
    matched = sum(1 for m in source_modules if m in test_stems)
    name_match_pct = (matched / len(source_modules) * 100
                      if source_modules else 0.0)

    no_test_modules = sorted(m for m in source_modules if m not in test_stems)

    # framework hints
    frameworks = []
    if any(f.endswith(".py") for f in test_files):
        if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
            txt = _read_safely(str(root / "pyproject.toml")) \
                if (root / "pyproject.toml").exists() else ""
            if "[tool.pytest" in txt or (root / "pytest.ini").exists():
                frameworks.append("pytest")
            elif "unittest" in txt:
                frameworks.append("unittest")
    if any(".test." in f or ".spec." in f for f in test_files):
        frameworks.append("jest_or_vitest")
    if any(f.endswith("_test.go") for f in test_files):
        frameworks.append("go test")
    if any(f.endswith("_test.rs") for f in test_files):
        frameworks.append("cargo test")

    return {
        "test_file_count": len(test_files),
        "source_file_count": len(source_files),
        "name_match_coverage_pct": round(name_match_pct, 1),
        "no_test_modules": no_test_modules[:200],
        "no_test_module_count": len(no_test_modules),
        "frameworks_detected": sorted(set(frameworks)),
    }


def scan_git_history(root: Path) -> dict:
    """git log / blame summary. Returns degraded={} if no git."""
    if not (root / ".git").exists():
        return {"degraded": True, "reason": "no .git/ in project root"}
    if not _has_tool("git"):
        return {"degraded": True, "reason": "git not on PATH"}

    def _git(args: list[str], timeout: int = 10) -> str:
        try:
            r = subprocess.run(["git"] + args, cwd=str(root),
                                capture_output=True, text=True,
                                timeout=timeout)
            return r.stdout.strip() if r.returncode == 0 else ""
        except (subprocess.TimeoutExpired, OSError):
            return ""

    head_sha = _git(["rev-parse", "HEAD"])
    first_commit = _git(["log", "--reverse", "--format=%ai", "--max-parents=0"])
    last_commit = _git(["log", "-1", "--format=%ai"])
    total_commits = _git(["rev-list", "--count", "HEAD"])
    contributors = _git(["shortlog", "-sn", "HEAD"]).splitlines()
    hotspots = _git(["log", "--name-only", "--format=", "-n", "500"])
    counts: dict[str, int] = {}
    for line in hotspots.splitlines():
        line = line.strip()
        if line and not _is_excluded(line):
            counts[line] = counts.get(line, 0) + 1
    top_hotspots = sorted(counts.items(), key=lambda kv: -kv[1])[:25]
    dirty = _git(["status", "--short"])
    return {
        "degraded": False,
        "head_sha": head_sha,
        "first_commit": first_commit.splitlines()[-1] if first_commit else "",
        "last_commit": last_commit,
        "total_commits": int(total_commits) if total_commits.isdigit() else 0,
        "contributor_count": len(contributors),
        "top_hotspots": top_hotspots,
        "working_tree_dirty": bool(dirty),
        "calibrated_stability_cutoff_days": 365,
    }


def scan_conventions(root: Path) -> dict:
    """Conventions audit (lightweight, deterministic). Captures lint config
    presence, async-pattern dominance hints, type-hint coverage proxy."""
    has_lint_config = any(
        (root / fn).exists() for fn in
        (".ruff.toml", "ruff.toml", ".flake8", ".eslintrc",
         ".eslintrc.json", ".eslintrc.yaml", ".eslintrc.yml",
         "tslint.json", "biome.json")
    )
    has_format_config = any(
        (root / fn).exists() for fn in
        (".prettierrc", ".prettierrc.json", ".prettierrc.yaml",
         "rustfmt.toml", ".rustfmt.toml")
    )
    pyproject = _read_safely(str(root / "pyproject.toml"))
    has_lint_config = has_lint_config or "[tool.ruff" in pyproject \
        or "[tool.flake8" in pyproject
    has_format_config = has_format_config or "[tool.black" in pyproject \
        or "[tool.ruff.format" in pyproject

    # Async pattern hint: count async fn declarations vs total fn declarations
    async_count = sync_count = 0
    for rel, abs_p in _walk_source(root):
        if Path(rel).suffix not in SOURCE_EXTENSIONS:
            continue
        txt = _read_safely(abs_p, 100_000)
        if rel.endswith(".py"):
            async_count += len(re.findall(r"^async def ", txt, re.M))
            sync_count += len(re.findall(r"^def ", txt, re.M))
        elif rel.endswith((".js", ".ts", ".jsx", ".tsx")):
            async_count += len(re.findall(r"\basync\s+function\b", txt))
            async_count += len(re.findall(r"\basync\s+\(", txt))
            sync_count += len(re.findall(r"\bfunction\s+\w+\s*\(", txt))

    return {
        "has_lint_config": has_lint_config,
        "has_format_config": has_format_config,
        "async_function_count": async_count,
        "sync_function_count": sync_count,
    }


def scan_product_signals(root: Path) -> dict:
    """README + docs scan for product-context evidence."""
    candidates = ["README.md", "README.rst", "README.txt",
                  "docs/README.md", "docs/architecture.md",
                  "docs/PRD.md", "docs/prd.md"]
    found = []
    inferred_h1 = None
    for c in candidates:
        p = root / c
        if p.exists():
            txt = _read_safely(str(p))
            found.append({"path": c, "bytes": len(txt)})
            if not inferred_h1 and c.startswith("README"):
                for line in txt.splitlines():
                    m = re.match(r"#\s+(.+)", line.strip())
                    if m:
                        inferred_h1 = m.group(1).strip()
                        break
    # docs/prd/* glob
    prd_dir = root / "docs" / "prd"
    if prd_dir.exists() and prd_dir.is_dir():
        for fn in sorted(os.listdir(prd_dir)):
            found.append({"path": f"docs/prd/{fn}",
                          "bytes": (prd_dir / fn).stat().st_size
                          if (prd_dir / fn).is_file() else 0})
    return {"documents": found, "inferred_project_name": inferred_h1}


def scan_pm_tooling_signals(root: Path) -> dict:
    """R0 step 12 — PM tooling indicator scan."""
    in_repo_dirs = {}
    for d in ("tickets", "issues", "todos", "planning", "epics", "backlog"):
        p = root / d
        if p.exists() and p.is_dir():
            try:
                in_repo_dirs[d] = sum(1 for _ in p.rglob("*") if _.is_file())
            except OSError:
                in_repo_dirs[d] = 0

    ci_integrations = []
    for ci_dir in (".github/workflows", ".gitlab-ci.yml", ".circleci",
                   "Jenkinsfile"):
        p = root / ci_dir
        if p.exists():
            if p.is_dir():
                for fn in p.rglob("*"):
                    if fn.is_file():
                        txt = _read_safely(str(fn))
                        for pat, label in (
                                (r"LINEAR_API_KEY", "linear"),
                                (r"JIRA_TOKEN|JIRA_USER", "jira"),
                                (r"gh\s+issue|GITHUB_ISSUES", "github_issues"),
                                (r"linear/action-", "linear")):
                            if re.search(pat, txt):
                                ci_integrations.append(
                                    {"file": str(
                                        fn.relative_to(root)), "tool": label})
            elif p.is_file():
                txt = _read_safely(str(p))
                for pat, label in ((r"LINEAR_API_KEY", "linear"),
                                    (r"JIRA_TOKEN|JIRA_USER", "jira")):
                    if re.search(pat, txt):
                        ci_integrations.append(
                            {"file": str(p.relative_to(root)),
                             "tool": label})

    # commit-message ticket-ref sample (last 100 commits)
    ticket_pattern_counts = {}
    if (root / ".git").exists() and _has_tool("git"):
        try:
            r = subprocess.run(
                ["git", "log", "-100", "--format=%s"], cwd=str(root),
                capture_output=True, text=True, timeout=10)
            msgs = r.stdout
            for pat, label in (
                    (r"\b[A-Z]{2,}-\d+\b", "project_key_pattern"),
                    (r"#\d+", "github_issue_ref"),
                    (r"linear:\s*[a-z0-9-]+", "linear_ref")):
                hits = len(re.findall(pat, msgs))
                if hits:
                    ticket_pattern_counts[label] = hits
        except (subprocess.TimeoutExpired, OSError):
            pass

    return {
        "in_repo_ticket_dirs": in_repo_dirs,
        "ci_integrations": ci_integrations,
        "commit_msg_ticket_ref_counts": ticket_pattern_counts,
    }


def check_existing_claude(root: Path) -> dict:
    """R0 step 1 - existing .claude/ check."""
    claude = root / ".claude"
    archived = sorted(p.name for p in root.iterdir()
                      if p.is_dir() and p.name.startswith(".claude.archived"))
    has_bootstrap_state = (claude / ".bootstrap-state.json").exists() \
        if claude.exists() else False
    has_retrofit_state = (claude / ".retrofit-state.json").exists() \
        if claude.exists() else False
    has_root_claude_md = (root / "CLAUDE.md").exists()
    return {
        "has_existing_claude": claude.exists(),
        "has_bootstrap_state": has_bootstrap_state,
        "has_retrofit_state": has_retrofit_state,
        "has_root_claude_md": has_root_claude_md,
        "archived_dirs": archived,
    }


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def scan_repo(root: Path, *, exclude_dirs: set | None = None) -> dict:
    """Run every per-dimension scanner against the repo root."""
    return {
        "structure": scan_structure(root),
        "languages": scan_languages(root),
        "dependencies": scan_dependencies(root),
        "testing": scan_testing(root),
        "git_history": scan_git_history(root),
        "conventions": scan_conventions(root),
        "product_signals": scan_product_signals(root),
        "pm_tooling_signals": scan_pm_tooling_signals(root),
        "existing_claude": check_existing_claude(root),
    }


# --------------------------------------------------------------------------- #
# Markdown rendering
# --------------------------------------------------------------------------- #
def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def render_inventory_files(inv: dict) -> dict[str, str]:
    """Translate the InventoryData dict into a dict of {relative_path: body}."""
    out: dict[str, str] = {}

    s = inv["structure"]
    rows = [[d, str(v["source_files"]), str(v["loc_proxy"])]
            for d, v in s["top_level_dirs"].items()]
    out[".claude/inventory/structure.md"] = (
        "# Project structure (R0)\n\n"
        "Top-level directories and source-file counts. Excludes vendored,\n"
        "generated, docs, and .claude/ paths (RETROFIT.md R-1 exclude list).\n\n"
        + (_md_table(["Directory", "Source files", "LOC proxy"], rows)
           if rows else "_(no top-level dirs detected)_") + "\n\n"
        "## Top-level files\n\n"
        + ("\n".join(f"- `{f}`" for f in s["top_level_files"])
           or "_(none)_") + "\n")

    l = inv["languages"]
    rows = [[ext or "(none)", str(n)]
            for ext, n in l["files_by_extension"].items()][:20]
    manifests = "\n".join(f"- `{k}`: {'yes' if v else 'no'}"
                          for k, v in l["manifests"].items())
    out[".claude/inventory/languages.md"] = (
        "# Languages (R0)\n\n"
        "File-count by extension (top 20) and manifest detection.\n\n"
        "## Files by extension\n\n"
        + _md_table(["Extension", "Count"], rows) + "\n\n"
        "## Manifests\n\n"
        + manifests + "\n\n"
        f"Dockerfile count: **{l['dockerfile_count']}**\n")

    d = inv["dependencies"]
    deps_body = ""
    for manifest_label, names in d["by_manifest"].items():
        deps_body += f"\n### {manifest_label} ({len(names)} package(s))\n\n"
        deps_body += "\n".join(f"- `{n}`" for n in names[:50])
        if len(names) > 50:
            deps_body += f"\n- _(+{len(names) - 50} more)_"
        deps_body += "\n"
    out[".claude/inventory/dependencies.md"] = (
        "# Dependencies (R0)\n\n"
        "Per-manifest declared dependencies. **No outdated-package scan\n"
        "was run** (requires network; deferred to R5.5 with operator).\n"
        + (deps_body or "\n_(no manifests detected)_\n") + "\n"
        f"Inline ticket-reference comments in manifests: "
        f"**{d['inline_ticket_refs_count']}** (a convention-evidence signal).\n")

    t = inv["testing"]
    out[".claude/inventory/testing.md"] = (
        "# Testing (R0)\n\n"
        f"- **Test files detected:** {t['test_file_count']}\n"
        f"- **Source files (non-test):** {t['source_file_count']}\n"
        f"- **Name-match coverage proxy:** "
        f"{t['name_match_coverage_pct']}% "
        f"(strict — actual exercised level may be higher)\n"
        f"- **Frameworks detected:** "
        f"{', '.join(t['frameworks_detected']) or '_(none)_'}\n"
        f"- **Modules without name-matching tests:** "
        f"{t['no_test_module_count']}\n\n"
        "## No-test modules (first 25; legacy-allowlist + grandfather "
        "candidates)\n\n"
        + "\n".join(f"- `{m}`" for m in t['no_test_modules'][:25])
        + ("\n\n_..._" if t['no_test_module_count'] > 25 else "") + "\n")

    g = inv["git_history"]
    if g.get("degraded"):
        out[".claude/inventory/git-history.md"] = (
            "# Git history (R0)\n\n"
            f"**DEGRADED MODE:** {g.get('reason', 'git unavailable')}.\n\n"
            "Per RETROFIT.md R-1, scans that depend on git history\n"
            "(stability cutoff, hotspots, historical secret-leakage)\n"
            "are unavailable in this mode. Operator may `git init` and\n"
            "re-run the scan to restore full mode.\n")
    else:
        hot_rows = [[f, str(n)] for f, n in g["top_hotspots"]]
        out[".claude/inventory/git-history.md"] = (
            "# Git history (R0)\n\n"
            f"- **HEAD SHA:** `{g['head_sha']}`\n"
            f"- **First commit:** {g['first_commit']}\n"
            f"- **Last commit:** {g['last_commit']}\n"
            f"- **Total commits:** {g['total_commits']}\n"
            f"- **Contributors:** {g['contributor_count']}\n"
            f"- **Working tree dirty:** {g['working_tree_dirty']}\n"
            f"- **Calibrated stability cutoff:** "
            f"{g['calibrated_stability_cutoff_days']} days\n\n"
            "## Top 25 hotspots (most-modified files, last 500 commits)\n\n"
            + (_md_table(["File", "Changes"], hot_rows)
               if hot_rows else "_(none)_") + "\n")

    c = inv["conventions"]
    out[".claude/inventory/conventions.md"] = (
        "# Conventions (R0)\n\n"
        "Lightweight automated audit. R2 (`tech.md`) categorizes these\n"
        "manually with the operator into Canonical / Deprecated /\n"
        "Intentional Variation / Modernize.\n\n"
        f"- **Lint config detected:** {c['has_lint_config']}\n"
        f"- **Format config detected:** {c['has_format_config']}\n"
        f"- **`async def` count:** {c['async_function_count']}\n"
        f"- **`def` count:** {c['sync_function_count']}\n"
        f"- **Async-first hint:** "
        + ("yes" if c['async_function_count'] > c['sync_function_count'] / 2
           else "no") + "\n")

    p = inv["product_signals"]
    rows = [[doc["path"], str(doc["bytes"])] for doc in p["documents"]]
    out[".claude/inventory/product-signals.md"] = (
        "# Product signals (R0, input to R1)\n\n"
        f"**Inferred project name (from leading H1):** "
        f"`{p['inferred_project_name'] or '_(none found)_'}`\n\n"
        "## Documents found\n\n"
        + (_md_table(["Path", "Bytes"], rows)
           if rows else "_(no product docs found — sparse signals)_") + "\n")

    pm = inv["pm_tooling_signals"]
    pm_body = ""
    if pm["in_repo_ticket_dirs"]:
        pm_body += "## In-repo ticket directories\n\n"
        for d, n in pm["in_repo_ticket_dirs"].items():
            pm_body += f"- `{d}/` — {n} file(s)\n"
        pm_body += "\n"
    if pm["ci_integrations"]:
        pm_body += "## CI/CD integrations with PM tools\n\n"
        for ci in pm["ci_integrations"]:
            pm_body += f"- {ci['file']} → `{ci['tool']}`\n"
        pm_body += "\n"
    if pm["commit_msg_ticket_ref_counts"]:
        pm_body += "## Commit-message ticket-reference patterns " \
                   "(last 100)\n\n"
        for label, n in pm["commit_msg_ticket_ref_counts"].items():
            pm_body += f"- `{label}`: {n} commit(s)\n"
        pm_body += "\n"
    out[".claude/inventory/pm-tooling-signals.md"] = (
        "# PM tooling signals (R0 step 12, input to R0.7)\n\n"
        + (pm_body or "_(no PM-tooling signals detected)_\n"))

    e = inv["existing_claude"]
    out[".claude/inventory/existing-claude.md"] = (
        "# Existing .claude/ state (R0 step 1)\n\n"
        f"- **`.claude/` present:** {e['has_existing_claude']}\n"
        f"- **`.bootstrap-state.json` present:** "
        f"{e['has_bootstrap_state']}\n"
        f"- **`.retrofit-state.json` present:** "
        f"{e['has_retrofit_state']}\n"
        f"- **Root `CLAUDE.md` present:** {e['has_root_claude_md']}\n"
        f"- **Archived `.claude.archived-*/` dirs:** "
        f"{', '.join(e['archived_dirs']) or '_(none)_'}\n\n"
        + ("\n> R0 step 6 prior-art audit applies — see inventory entries\n"
           "> for each archived directory.\n"
           if e['archived_dirs'] else ""))

    # Baseline metrics: stubs only (DORA values typically need operator
    # input / CI-API access). RETROFIT.md R0 step 8 allows "unavailable,
    # baseline = unknown" as a valid recorded state.
    out[".claude/inventory/baseline-metrics.md"] = (
        "# Baseline metrics (R0 step 8)\n\n"
        "Recorded at retrofit time for 30/60/90-day comparison (R7).\n\n"
        "| Metric | Baseline value | Source |\n|---|---|---|\n"
        "| Lead time for changes | unavailable | requires CI/deploy data |\n"
        "| Change failure rate | unavailable | requires production data |\n"
        "| Test coverage | unavailable | run coverage tool to populate |\n"
        f"| Lint conformance rate | unavailable | run "
        f"{'configured linter' if inv['conventions']['has_lint_config'] else 'no lint config detected'} |\n"
        "| Spec coverage | 0% | no specs exist yet (retrofit starting point) |\n\n"
        "**DORA performance tier:** unavailable — operator confirms.\n")

    # README pointer — pure pointer, no codebase-derived content (C1/OD-5).
    out[".claude/inventory/README.md"] = (
        "# .claude/inventory/ — codebase audit (R0)\n\n"
        "One-time snapshot of pre-retrofit state. Frozen at retrofit\n"
        "time; not maintained going forward. R5/R8.E reference these\n"
        "from the steering docs; R7 re-reads them for the equivalence\n"
        "validation. See RETROFIT.md Phase R0 for the per-file contract.\n")

    return out


def write_inventory(root: Path, inv: dict, *, dry_run: bool = False) -> list[str]:
    """Render and write all inventory markdown files. Returns paths written."""
    files = render_inventory_files(inv)
    written = []
    for rel_path, body in files.items():
        target = root / rel_path
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body)
        written.append(rel_path)
    return written

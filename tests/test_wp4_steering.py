#!/usr/bin/env python3
"""[WP4 / g2] Steering: tech.md's Do Not Touch and Documentation Policy
sections, and ci-cd.md's one agent stopping point.

1. tech.md carries `## Do Not Touch` and `## Documentation Policy` (PRD
   Phase 2 step 5; RETROFIT.md R2 step 8) for every archetype, in both
   modes, each as a `TODO:` scaffold the AI replaces. Do Not Touch names no
   path, because only the operator approves the list, and suggests exactly
   one set: greenfield, Phase 2 step 3's for the archetype; retrofit, the
   union of that and RETROFIT.md R2 step 6's. Both expected sets are parsed
   from the two documents here, never copied from the template's tables, so
   a change to either document's list fails these rows until the template
   follows it. The retrofit Documentation Policy also asks R2 step 7's drift
   question and names the debt.md entry it asks for.
2. ci-cd.md states one stopping point per variant (Phase 5 exit criterion).
2b. CLAUDE.md's lifecycle points at that stop rather than restating it, so
   no other emitted file names a stop.
3. [WP4 commit 5] A re-install never overwrites the AI's sections: same
   config, a changed config, an uninstall, and a doc written before the
   first install. A kept tech.md or ci-cd.md that lacks what this release
   added, or whose Test row is stale, says so once on stderr (8a).
5. [WP4 commit 5, 8a] The other kept-file warnings: a greenfield CLAUDE.md
   with no `## Never` section; a retrofit CLAUDE.md keyed on retrofit's own
   WP4 changes, never on a Never list; a kept .claude/.gitignore that does
   not ignore the state lock; and, on a tree with no installer manifest
   (a fresh clone), the per-file remedy instead of `--adopt`.

Run: python3 tests/test_wp4_steering.py
"""
import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "lib"))

from defaults import resolve_config, ARCHETYPES      # noqa: E402
from installer import build_plan                     # noqa: E402
from minyaml import load_yaml                        # noqa: E402
import templates                                     # noqa: E402

TECH = ".claude/steering/tech.md"
CICD = ".claude/steering/ci-cd.md"

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
            print(f"        {str(detail)[:600]}")


def plan_of(text):
    cfg, errs = resolve_config(load_yaml(text))
    assert not errs, errs
    return {a["path"]: a["body"] for a in build_plan(cfg)}


def flat(s):
    return " ".join(s.split())


def section(body, heading):
    """The text under `## heading`, up to the next `## ` or the end."""
    m = re.search(r"^## " + re.escape(heading) + r"\n(.*?)(?=^## |\Z)",
                  body, re.S | re.M)
    return m.group(1) if m else None


def _retrofit_fixture(name):
    """A retrofit golden fixture's config text, read by ast from
    tests/test_retrofit.py (as tests/test_merge_back.py does)."""
    path = os.path.join(HERE, "test_retrofit.py")
    for node in ast.parse(open(path).read()).body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and getattr(node.targets[0], "id", None) == name):
            return eval(compile(ast.Expression(node.value), path, "eval"))
    raise LookupError(name)


# --------------------------------------------------------------------------- #
# The expected suggestion sets, from the two documents
# --------------------------------------------------------------------------- #
# One emitted phrase per document term, and no two terms share a phrase. A
# term either document adds, or a reworded one, has no entry here and fails
# the parse below instead of passing silently.
PHASE2_TERMS = {"auth": "authentication code", "payment": "payment code",
                "migrations": "database migrations",
                "public API surface": "the public API surface",
                "prompt files": "prompt files",
                "secrets handling": "secrets handling",
                "infrastructure-as-code": "infrastructure-as-code files"}
PHASE2_WHO = {"full-stack": "fullstack", "libraries": "library",
              "AI systems": "ai-agent", "all": "*"}
R2_ANCHORS = {"stable beyond the calibrated cutoff":
              "modules the inventory flags as stable",
              "inherently frozen artifacts":
              "frozen artifacts such as initial database migrations",
              "Pinned-contract files": "pinned-contract files"}
R2_TERMS = {"auth modules": "authentication modules",
            "payment modules": "payment modules",
            "public API surface": "the public API surface",
            "prompt files": "prompt files",
            "eval harness": "the eval harness",
            "cross-component contract files":
            "cross-component contract files"}
R2_WHO = {"Service/API": "service", "Library/SDK": "library",
          "AI/agent": "ai-agent", "Platform": "platform"}
_PHRASES = list(PHASE2_TERMS.values()) + list(R2_ANCHORS.values()) + [
    v for k, v in R2_TERMS.items() if PHASE2_TERMS.get(k) != v]
assert len(_PHRASES) == len(set(_PHRASES)), "two terms share a phrase"
_parse_errors = []


def phase2_sets():
    """{archetype or "*": set of phrases}, from the protocol's Phase 2 step
    3 ("Always ask the "do not touch" question explicitly. Default
    suggestions vary by archetype (...)"), in the file templates names."""
    name = getattr(templates, "PROTOCOL_DOC", None)
    if name is None:
        _parse_errors.append("templates.PROTOCOL_DOC is missing")
        return {}
    doc = open(os.path.join(ROOT, name), encoding="utf-8").read()
    m = re.search(r'Always ask the "do not touch" question explicitly\. '
                  r"Default suggestions vary by archetype \(([^)]*)\)", doc)
    if not m:
        _parse_errors.append("Phase 2 step 3's sentence not found")
        return {}
    out = {}
    for group in m.group(1).split("; "):
        g = re.fullmatch(r"(.+) for (.+)", group)
        if not g or g.group(2) not in PHASE2_WHO:
            _parse_errors.append(("Phase 2 group", group))
            continue
        for term in re.split(r"/| and ", g.group(1)):
            if term not in PHASE2_TERMS:
                _parse_errors.append(("Phase 2 term", term))
                continue
            out.setdefault(PHASE2_WHO[g.group(2)], set()).add(
                PHASE2_TERMS[term])
    return out


def r2_sets():
    """({archetype: set}, set of the general retrofit defaults), from
    RETROFIT.md R2 step 6's bullets ("Default suggestions plus
    retrofit-specific defaults")."""
    doc = open(os.path.join(ROOT, "RETROFIT.md"), encoding="utf-8").read()
    m = re.search(r'^6\. Ask the "do not touch" question\. Default '
                  r"suggestions plus retrofit-specific defaults:\n"
                  r"((?:   - .*\n)+)", doc, re.M)
    if not m:
        _parse_errors.append("R2 step 6 not found")
        return {}, set()
    by_arch, general = {}, set()
    for bullet in re.findall(r"^   - (.*)$", m.group(1), re.M):
        a = re.fullmatch(r"\*\*Archetype-specific defaults:\*\* (.*)\.",
                         bullet)
        if a:
            for part in a.group(1).split("; "):
                who, _, terms = part.partition(" → ")
                if who not in R2_WHO:
                    _parse_errors.append(("R2 archetype", who))
                    continue
                for term in terms.split(" + "):
                    term = re.sub(r" \(.*\)$", "", term)
                    if term not in R2_TERMS:
                        _parse_errors.append(("R2 term", term))
                        continue
                    by_arch.setdefault(R2_WHO[who], set()).add(
                        R2_TERMS[term])
            continue
        hits = [v for k, v in R2_ANCHORS.items() if k in bullet]
        if len(hits) != 1:
            _parse_errors.append(("R2 bullet", bullet[:80]))
            continue
        general.add(hits[0])
    if general != set(R2_ANCHORS.values()):
        _parse_errors.append(("R2 general bullets", sorted(general)))
    return by_arch, general


PHASE2 = phase2_sets()
R2_ARCH, R2_GENERAL = r2_sets()


def expected(arch, retrofit):
    want = PHASE2.get(arch, set()) | PHASE2.get("*", set())
    if retrofit:
        want |= R2_ARCH.get(arch, set()) | R2_GENERAL
    return want


def suggestions(dnt):
    """The `Common choices` list of a flattened Do Not Touch section."""
    sug = dnt.split("archetype: ", 1)[-1].split(". If a task", 1)[0]
    if ", " in sug:
        items = sug.split(", ")
        items[-1] = re.sub(r"^and ", "", items[-1])
        return items
    return sug.split(" and ")


def _drift_question():
    """R2 step 7's question, quoted in RETROFIT.md."""
    doc = open(os.path.join(ROOT, "RETROFIT.md"), encoding="utf-8").read()
    m = re.search(r'^7\. \*\*Documentation policy\*\*.*?explicitly ask: '
                  r'"([^"]+)"', doc, re.M)
    return m.group(1) if m else None


# --------------------------------------------------------------------------- #
# 1. tech.md: the two sections, for every archetype, in both modes
# --------------------------------------------------------------------------- #
print("\n== 1. tech.md: Do Not Touch and Documentation Policy ==")
check("both documents parse into the term tables, with nothing left over",
      not _parse_errors and set(PHASE2) == {"fullstack", "library",
                                             "ai-agent", "*"}
      and set(R2_ARCH) == set(R2_WHO.values()), _parse_errors)
DRIFT_Q = _drift_question()
check("RETROFIT.md R2 step 7 quotes its drift question", bool(DRIFT_Q))
_RETRO_BASE = _retrofit_fixture("SERVICE_RETROFIT_CFG")
assert "archetype: service\n" in _RETRO_BASE
for retrofit in (False, True):
    mode = "retrofit" if retrofit else "greenfield"
    source = "(RETROFIT.md R2)" if retrofit else "(Bootstrap Protocol Phase 2)"
    for arch in sorted(ARCHETYPES):
        text = (_RETRO_BASE.replace("archetype: service\n",
                                    f"archetype: {arch}\n") if retrofit
                else f"project:\n  name: m\n  archetype: {arch}\n")
        t = plan_of(text)[TECH]
        tag = f"[{mode} {arch}]"
        heads = re.findall(r"^## .*$", t, re.M)
        check(f"{tag} tech.md: one Do Not Touch and one Documentation "
              f"Policy heading, after the command table, in that order",
              heads.count("## Do Not Touch") == 1
              and heads.count("## Documentation Policy") == 1
              and heads.index("## Project commands")
              < heads.index("## Do Not Touch")
              < heads.index("## Documentation Policy"), str(heads))
        dnt = flat(section(t, "Do Not Touch") or "")
        doc = flat(section(t, "Documentation Policy") or "")
        check(f"{tag} Do Not Touch is a TODO scaffold that lists no path "
              f"yet, says how the operator approves it, and cites "
              f"{source}",
              dnt.startswith("TODO: not yet approved, so no path is listed.")
              and "get the operator's approval" in dnt and source in dnt,
              dnt)
        got, want = suggestions(dnt), expected(arch, retrofit)
        check(f"{tag} Do Not Touch suggests exactly "
              + ("Phase 2 step 3's set and R2 step 6's" if retrofit else
                 "Phase 2 step 3's set") + f" ({len(want)})",
              len(got) == len(set(got)) and set(got) == want,
              {"extra": sorted(set(got) - want),
               "missing": sorted(want - set(got))})
        # The installer does not know this project's paths, so a
        # suggestion that reads like an approved path would be a claim it
        # cannot make.
        check(f"{tag} the scaffold names no path or glob",
              "archetype: " in dnt and not re.search(r"[/*]", " ".join(got)),
              got)
        check(f"{tag} the rule outlives the scaffold: a listed path means "
              f"stop and ask",
              dnt.endswith("If a task needs to change a path listed here, "
                           "stop and ask the operator first."), dnt[-200:])
        asks = (doc.startswith("TODO: not yet decided.")
                and "where docs live" in doc
                and "who updates the README" in doc
                and "how the changelog works" in doc and source in doc)
        if retrofit:
            check(f"{tag} Documentation Policy asks the three Phase 2 "
                  f"questions, R2 step 7's drift question, and to log drift "
                  f"in debt.md",
                  asks and DRIFT_Q is not None and f'"{DRIFT_Q}"' in doc
                  and "as a debt item in `.claude/debt.md`" in doc, doc)
        else:
            check(f"{tag} Documentation Policy asks the three Phase 2 "
                  f"questions", asks and "debt" not in doc, doc)

# --------------------------------------------------------------------------- #
# 2. One stopping point
# --------------------------------------------------------------------------- #
print("\n== 2. ci-cd.md states one stopping point ==")
base = "project:\n  name: m\n  archetype: service\n"
p_ci = plan_of(base)
p_out = plan_of(base.replace("archetype: service\n",
                             "archetype: service\n  cicd_opt_out: true\n"))
p_nomirror = plan_of(base + "hooks:\n  ci_mirror: false\n")
p_retro = plan_of(_RETRO_BASE)
for label, plan in (("with CI/CD", p_ci), ("opted out", p_out),
                    ("ci-mirror off", p_nomirror)):
    stop = flat(section(plan[CICD], "Agent stopping point") or "")
    check(f"{label}: ci-cd.md has exactly one Agent stopping point section",
          plan[CICD].count("## Agent stopping point") == 1, plan[CICD])
    check(f"{label}: the section names no second stop (no 'or PR merge')",
          "PR merge" not in stop and "(or " not in stop
          and "**PR open**" not in stop, stop)
    check(f"{label}: never deploys", "never deploys" in stop, stop)
ci_stop = flat(section(p_ci[CICD], "Agent stopping point") or "")
check("with CI/CD: the agent stops after it opens a pull request, and a "
      "person merges it",
      ci_stop.startswith("The agent stops after it opens a pull request.")
      and "A person reviews the pull request and merges it." in ci_stop
      and "never merges a pull request" in ci_stop
      and "never pushes to the default branch" in ci_stop, ci_stop)
out_stop = flat(section(p_out[CICD], "Agent stopping point") or "")
check("opted out: the agent stops after its last commit and never pushes",
      out_stop.startswith("The agent stops after its last commit for the "
                          "task.")
      and "never pushes" in out_stop, out_stop)
check("opted out: ci-mirror is not wired, so no push check is claimed",
      "ci-mirror" not in p_out[CICD]
      and ".claude/hooks/ci-mirror.sh" not in p_out, p_out[CICD])
check("with CI/CD: the push-check sentence points at tech.md, which says "
      "what ci-mirror runs (the old 'these same checks' claim is gone)",
      "runs the checks `.claude/steering/tech.md` names" in flat(p_ci[CICD])
      and "these same checks" not in p_ci[CICD]
      and "`ci-mirror` runs CI local before every push" in p_ci[TECH],
      p_ci[CICD])
check("ci-mirror off: ci-cd.md says no hook checks a push",
      "No hook checks a push: `hooks.ci_mirror` is off." in p_nomirror[CICD]
      and "runs the checks" not in p_nomirror[CICD], p_nomirror[CICD])

print("\n== 2b. CLAUDE.md points at the stop instead of restating it ==")
LIFE = ("-> code-review (the reviewer agent) -> merge-back -> spec-validate "
        "-> pr-author -> stop as `ci-cd.md` says.")
for label, plan in (("greenfield", p_ci), ("opted out", p_out),
                    ("retrofit", p_retro)):
    check(f"{label}: CLAUDE.md's lifecycle ends at ci-cd.md's stop",
          LIFE in flat(plan["CLAUDE.md"]), plan["CLAUDE.md"][:800])
# No emitted file but ci-cd.md states where the agent stops.
STOP_WORDS = re.compile(r"(?i)stopping point|last action|stops after|"
                        r"PR merge|PR open")
for label, plan in (("with CI/CD", p_ci), ("opted out", p_out),
                    ("retrofit", p_retro)):
    others = sorted(p for p, b in plan.items()
                    if p != CICD and STOP_WORDS.search(b))
    check(f"{label}: no emitted file but ci-cd.md states a stopping point",
          others == [], str(others))

# --------------------------------------------------------------------------- #
# 3. A re-install keeps what the AI wrote
# --------------------------------------------------------------------------- #
print("\n== 3. re-install preserves the AI's sections ==")
INSTALL = os.path.join(ROOT, "bin", "bootstrap-install")
MANIFEST = ".claude/.installer-manifest.json"
GIT = shutil.which("git")
TMP = tempfile.mkdtemp(prefix="wp4-steer-")
CFG = ("project:\n  name: p\n  archetype: fullstack\n"
       "principles:\n  tdd_policy: encouraged\n"
       "commands:\n  test: \"true\"\n  lint: \"true\"\n")
AI_DNT = ("## Do Not Touch\n\n- `src/billing/**`: payment provider "
          "contract, frozen until v2.\n\nIf a task needs to change a path "
          "listed here, stop and ask the operator first.\n")
AI_STOP = ("## Agent stopping point\n\nThe agent stops after the pull "
           "request's CI turns green. A person merges it.\n")
TWO_STOPS = ("## Agent stopping point\n\nThe agent's last action is **PR "
             "open** (or PR merge). The agent never deploys.\n")


def run(d, *extra):
    return subprocess.run([sys.executable, INSTALL, "-C", d] + list(extra),
                          capture_output=True, text=True,
                          env=dict(os.environ, NO_COLOR="1"))


def ai_writes(d):
    """What the AI does in Phases 2 and 5: replace the scaffolds."""
    tp, cp = os.path.join(d, TECH), os.path.join(d, CICD)
    t = open(tp).read()
    t = re.sub(r"## Do Not Touch\n.*?(?=## Documentation Policy)",
               AI_DNT + "\n", t, flags=re.S)
    open(tp, "w").write(t)
    c = open(cp).read()
    c = re.sub(r"## Agent stopping point\n.*\Z", AI_STOP, c, flags=re.S)
    open(cp, "w").write(c)
    return t, c


def read(d, rel):
    try:
        return open(os.path.join(d, rel)).read()
    except OSError:
        return None


def write(d, rel, text):
    with open(os.path.join(d, rel), "w") as fh:
        fh.write(text)


def steering_warnings(r):
    return [ln for ln in r.stderr.splitlines()
            if ln.startswith("warning: .claude/steering/")]


def warns(r, path):
    """The `warning:` lines about one path."""
    return [ln for ln in r.stderr.splitlines()
            if ln.startswith(f"warning: {path} ")]


def skip_line(out, path):
    return any(ln.strip().startswith("SKIP") and path in ln
               for ln in out.splitlines())


def no_manifest(rel):
    """[WP4 / KEEP-1] The per-file remedy on a tree with no manifest."""
    return (f"This tree has no installer manifest, so the installer can't "
            f"tell whether {rel} was edited. If nobody edited it, move it "
            f"aside and re-install; that re-creates only {rel}. If it holds "
            f"edits, merge the change by hand. Don't use --adopt for this: "
            f"it records every skipped file as the installer's, so the next "
            f"install replaces each steering doc you or Claude filled in, "
            f"with no backup.")


def proj(name, cfg_text=CFG):
    d = os.path.join(TMP, name)
    os.makedirs(d)
    if GIT:
        subprocess.run([GIT, "init", "-q", d], check=True)
    write(d, "bootstrap.config.yaml", cfg_text)
    return d


try:
    d = os.path.join(TMP, "install-first")
    os.makedirs(d)
    cfg = os.path.join(d, "bootstrap.config.yaml")
    open(cfg, "w").write(CFG)
    r0 = run(d)
    check("install-first: the install exits 0 and writes the scaffolds",
          r0.returncode == 0
          and "TODO: not yet approved" in (read(d, TECH) or ""),
          r0.stdout[-600:] + r0.stderr[-600:])
    want_t, want_c = ai_writes(d)
    r1 = run(d)
    check("same config: re-install exits 0, SKIPs both, keeps the AI's text",
          r1.returncode == 0 and skip_line(r1.stdout, TECH)
          and skip_line(r1.stdout, CICD)
          and read(d, TECH) == want_t
          and read(d, CICD) == want_c,
          r1.stdout[-800:])
    open(cfg, "w").write(CFG.replace('test: "true"', 'test: "pytest -q"'))
    r2 = run(d)
    t2 = read(d, TECH) or ""
    check("changed config: re-install still keeps the AI's tech.md (its "
          "command table stays as written: the cost of D1 (c))",
          r2.returncode == 0 and t2 == want_t and "pytest -q" not in t2
          and skip_line(r2.stdout, TECH), r2.stdout[-800:])
    hook = read(d, ".claude/hooks/test-gate.sh") or ""
    check("changed config: the test gate itself runs the new command",
          "pytest -q" in hook)
    r3 = run(d, "--uninstall")
    check("uninstall keeps the AI's tech.md and ci-cd.md",
          r3.returncode == 0
          and read(d, TECH) == want_t
          and read(d, CICD) == want_c,
          r3.stdout[-600:])

    d = os.path.join(TMP, "ai-first")
    os.makedirs(os.path.join(d, ".claude/steering"))
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(CFG)
    mine_t = "# Technical Steering\n\n" + AI_DNT
    open(os.path.join(d, TECH), "w").write(mine_t)
    r4 = run(d)
    check("AI-first (written before any install): the install exits 0 and "
          "keeps it",
          r4.returncode == 0 and skip_line(r4.stdout, TECH)
          and read(d, TECH) == mine_t,
          r4.stdout[-600:])

    d = os.path.join(TMP, "unedited")
    os.makedirs(d)
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(CFG)
    run(d)
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(
        CFG.replace('test: "true"', 'test: "pytest -q"'))
    r5 = run(d)
    t5 = read(d, TECH) or ""
    check("unedited scaffold: a re-install updates tech.md (the installer "
          "still owns it until the AI writes in it)",
          r5.returncode == 0 and "| Test      | `pytest -q` |" in t5
          and "TODO: not yet approved" in t5, r5.stdout[-600:])
    check("unedited scaffold: no steering warning",
          steering_warnings(r5) == [], r5.stderr[-600:])

    # ---- 4. What a kept doc missed is said, once, on stderr ------------- #
    print("\n== 4. a kept tech.md or ci-cd.md says what it missed ==")

    d = os.path.join(TMP, "old-docs")
    os.makedirs(d)
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(CFG)
    run(d)
    # An earlier install's docs, kept by an AI that edited them: no WP4
    # section in tech.md, and the two-stop sentence in ci-cd.md.
    t = read(d, TECH)
    open(os.path.join(d, TECH), "w").write(
        t.split("\n## Do Not Touch", 1)[0] + "\n## Stack\n\nPython.\n")
    c = read(d, CICD)
    open(os.path.join(d, CICD), "w").write(
        c.split("## Agent stopping point", 1)[0] + TWO_STOPS)
    r6 = run(d)
    w6 = steering_warnings(r6)
    check("old docs kept: one warning names both missing tech.md sections, "
          "one names the two-stop ci-cd.md, rc 0",
          r6.returncode == 0 and len(w6) == 2
          and "'## Do Not Touch', '## Documentation Policy'" in w6[0]
          and "still names two stops" in w6[1], "\n".join(w6))

    d = os.path.join(TMP, "filled")
    os.makedirs(d)
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(CFG)
    run(d)
    ai_writes(d)
    r7 = run(d)
    check("filled by the AI, same config: kept, and no steering warning",
          r7.returncode == 0 and steering_warnings(r7) == []
          and skip_line(r7.stdout, TECH), r7.stderr[-600:])
    open(os.path.join(d, "bootstrap.config.yaml"), "w").write(
        CFG.replace('test: "true"', 'test: "pytest -q"'))
    r8 = run(d)
    w8 = steering_warnings(r8)
    check("filled, commands.test changed: one warning names the stale Test "
          "row and the command the gates run",
          r8.returncode == 0 and len(w8) == 1
          and "its Test row says `true`, but commands.test is `pytest -q`"
          in w8[0], "\n".join(w8))

    # ---- 5. The other kept files, and a tree with no manifest (8a) ------ #
    print("\n== 5. a kept CLAUDE.md or .claude/.gitignore; a fresh clone ==")
    # [V7] The clause that CLAUDE.md's lifecycle ends at ci-cd.md's stop is
    # true only when this run wrote CLAUDE.md.
    check("ci-cd.md kept, CLAUDE.md written: the warning says CLAUDE.md's "
          "lifecycle now ends at the stop ci-cd.md names",
          len(w6) == 2 and "CLAUDE.md's lifecycle now ends at the stop this "
          "file names" in w6[1], "\n".join(w6))

    g = proj("g-claude")
    run(g)
    write(g, "CLAUDE.md", re.sub(r"^## Never\n.*?(?=^## )", "",
                                 read(g, "CLAUDE.md"), flags=re.S | re.M))
    write(g, CICD, read(g, CICD).split("## Agent stopping point", 1)[0]
          + TWO_STOPS)
    rg = run(g)
    wc = warns(rg, "CLAUDE.md")
    check("greenfield CLAUDE.md kept with no `## Never` section: one warning "
          "lists the Never list, session hygiene, the steering index and the "
          "/escalate line",
          rg.returncode == 0 and len(wc) == 1
          and "(the Never list, session hygiene, the steering index and the "
              "`/escalate` line)" in wc[0]
          and "'## Never'" in wc[0]
          and "Merge them by hand from a fresh install's CLAUDE.md." in wc[0],
          rg.stderr[-1200:])
    wk = warns(rg, CICD)
    check("ci-cd.md and CLAUDE.md both kept: the ci-cd.md warning makes no "
          "claim about CLAUDE.md's lifecycle",
          len(wk) == 1 and "still names two stops" in wk[0]
          and "CLAUDE.md" not in wk[0]
          and "Keep one, as Bootstrap Protocol Phase 5 asks." in wk[0],
          "\n".join(wk))

    RCFG = _RETRO_BASE
    rd = proj("r-claude", RCFG)
    run(rd)
    fresh = read(rd, "CLAUDE.md")
    write(rd, "CLAUDE.md", fresh.replace(" -> stop as `ci-cd.md` says.", "."))
    rr = run(rd)
    wr = warns(rr, "CLAUDE.md")
    check("retrofit CLAUDE.md kept without this release's lifecycle ending: "
          "one warning names it, and says nothing of a Never list",
          rr.returncode == 0 and len(wr) == 1
          and "-> stop as `ci-cd.md` says." in wr[0]
          and "Never" not in wr[0] and "Phase 8" not in wr[0], "\n".join(wr))
    write(rd, "CLAUDE.md", fresh + "\nA project rule the operator added.\n")
    rr2 = run(rd)
    check("retrofit CLAUDE.md kept as a fresh install's plus one line (what "
          "the warning asks for): no CLAUDE.md warning",
          rr2.returncode == 0 and skip_line(rr2.stdout, "CLAUDE.md")
          and warns(rr2, "CLAUDE.md") == [], rr2.stderr[-800:])

    RCFG_OFF = (RCFG.replace("secrets:\n  enabled: true",
                             "secrets:\n  enabled: false")
                .replace("deps:\n  enabled: true", "deps:\n  enabled: false"))
    ro = proj("r-off", RCFG_OFF)
    run(ro)
    fresh_off = read(ro, "CLAUDE.md")
    write(ro, "CLAUDE.md", fresh_off.replace(
        "1. **🔔** A Do Not Touch path needs access or modification.",
        "1. **🔔** A do-not-touch / never-read path needs access or "
        "modification.").replace(
        "4. **🔔** Implementation reveals",
        "4. **🔔** A dependency not on the `deps.md` approved list is "
        "needed.\n5. **🔔** Implementation reveals"))
    rof = run(ro)
    wo = warns(rof, "CLAUDE.md")
    check("retrofit, gates off: a kept CLAUDE.md whose urgent list still "
          "names `deps.md` and never-read paths gets one warning naming them",
          rof.returncode == 0 and len(wo) == 1 and "`deps.md`" in wo[0]
          and "never-read" in wo[0] and "-> stop as" not in wo[0]
          and "Never" not in wo[0], rof.stderr[-1000:])

    gi = read(rd, ".claude/.gitignore")
    write(rd, ".claude/.gitignore",
          gi.replace(".retrofit-state.json.lock\n", ""))
    rgi = run(rd)
    wg = warns(rgi, ".claude/.gitignore")
    check("retrofit .claude/.gitignore kept without the lock line: one "
          "warning names `.retrofit-state.json.lock` and the line to add",
          not GIT or (rgi.returncode == 0 and len(wg) == 1
                      and "`.retrofit-state.json.lock`" in wg[0]
                      and "Add that line to .claude/.gitignore." in wg[0]),
          rgi.stderr[-800:])
    gg = proj("g-gitignore")
    run(gg)
    write(gg, ".claude/.gitignore",
          read(gg, ".claude/.gitignore") + "scratch/\n")
    rgg = run(gg)
    check("greenfield .claude/.gitignore kept with its lock line: no lock "
          "warning", rgg.returncode == 0 and skip_line(rgg.stdout,
                                                       ".claude/.gitignore")
          and warns(rgg, ".claude/.gitignore") == [], rgg.stderr[-600:])

    # [KEEP-1, NF-1] A fresh clone: the manifest is gitignored, so every
    # file is unproven. --adopt would record the filled product.md as the
    # installer's and the next install would replace it, with no backup.
    fc = proj("clone")
    run(fc)
    PRODUCT = ".claude/steering/product.md"
    write(fc, PRODUCT, read(fc, PRODUCT) + "\nFilled by Claude.\n")
    filled = read(fc, PRODUCT)
    write(fc, CICD, read(fc, CICD).split("## Agent stopping point", 1)[0]
          + TWO_STOPS)
    os.remove(os.path.join(fc, MANIFEST))
    rc1 = run(fc)
    wf = warns(rc1, CICD)
    check("fresh clone, stale ci-cd.md: the warning gives the per-file "
          "remedy (move it aside and re-install), never --adopt",
          rc1.returncode == 0 and len(wf) == 1
          and no_manifest(CICD) in wf[0], "\n".join(wf))
    check("fresh clone: no stderr line advises --adopt; each line that "
          "names it says not to use it",
          all("Don't use --adopt for this" in ln
              for ln in rc1.stderr.splitlines() if "--adopt" in ln)
          and "run with --adopt" not in rc1.stderr, rc1.stderr[-1200:])
    os.rename(os.path.join(fc, CICD), os.path.join(fc, CICD + ".mine"))
    rc2 = run(fc)
    check("following it: the re-install creates only ci-cd.md and keeps the "
          "filled product.md",
          rc2.returncode == 0
          and "CREATE .claude/steering/ci-cd.md" in rc2.stdout
          and "create=1 " in rc2.stdout and read(fc, PRODUCT) == filled,
          rc2.stdout[-600:])

    hk = proj("hook-clone")
    run(hk)
    write(hk, ".claude/hooks/test-gate.sh",
          read(hk, ".claude/hooks/test-gate.sh")
          + "# an earlier install's bytes\n")
    os.remove(os.path.join(hk, MANIFEST))
    rh = run(hk)
    wh = warns(rh, ".claude/hooks/test-gate.sh")
    check("fresh clone, kept hook script: the existing warning uses the same "
          "per-file remedy, and no longer sends anyone to --adopt",
          rh.returncode == 0 and len(wh) == 1
          and no_manifest(".claude/hooks/test-gate.sh") in wh[0]
          and "run with --adopt" not in rh.stderr, rh.stderr[-1000:])

    sg = proj("secrets-clone")
    run(sg)
    write(sg, ".claude/hooks/secrets-gate.sh",
          read(sg, ".claude/hooks/secrets-gate.sh") + "# a local line\n")
    os.remove(os.path.join(sg, MANIFEST))
    rs = run(sg)
    check("fresh clone, kept security gate (exit 3): the note gives the "
          "per-file remedy instead of `--adopt` and a re-run",
          rs.returncode == 3
          and no_manifest(".claude/hooks/secrets-gate.sh") in rs.stderr
          and "records them as ours" not in rs.stderr, rs.stderr[-1200:])
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

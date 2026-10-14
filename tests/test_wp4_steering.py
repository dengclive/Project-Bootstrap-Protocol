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
6. [WP4 fix round 1] What the step 7 review found in 8a: a file a fresh
   clone kept keeps its remedy on later re-installs (K1); headings match
   by prefix, whatever their case (F2), and a greenfield CLAUDE.md is
   checked per Phase 8 element; a Test row that names the command with a
   note or bold is not stale (F3); a kept ci-cd.md with no stop is named
   (F1); a kept .gitignore is checked for the parse guard's copy too (F4);
   and a CLAUDE.md a first install keeps is the project's own (F5).
7. [WP4 fix round 2] What the re-review found in 8a: a Test row naming a
   longer command is stale (F3); a stop stated under another heading or in
   a bold line is a stop (F1); the project's own CLAUDE.md is named so on
   every run, and its own commands do not hide a first install (F5); the
   pins the re-review found missing, each with the mutant it kills (K1's
   later run, the skills-off exemptions, the heading's word boundary and
   whitespace, the dry-run wording).

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
# [WP4 fix round 1 / R9] The hook runs the commands the config held at
# install time and never reads tech.md, so the sentence names the config.
check("with CI/CD: the push-check sentence names the config's commands, as "
      "of the last install, and how to change them; tech.md's table says "
      "the same (the old 'these same checks' and 'the checks tech.md "
      "names' claims are gone)",
      "the `ci-mirror` hook runs `commands.ci_local`, or `commands.test` "
      "when that is empty, as `bootstrap.config.yaml` held them at the "
      "last install" in flat(p_ci[CICD])
      and "change the config and re-install" in flat(p_ci[CICD])
      and "these same checks" not in p_ci[CICD]
      and "tech.md` names" not in flat(p_ci[CICD])
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
    """[WP4 / KEEP-1] The per-file remedy on a tree with no manifest.
    [WP4 fix round 1 / K1, F5] "had", since a later run says it too, and
    the edited branch is the README's move-aside route."""
    return (f"This tree had no installer manifest when an install first "
            f"kept {rel}, so the installer can't tell whether it was edited. "
            f"If nobody edited it, move it aside and re-install; that "
            f"re-creates only {rel}. If it holds edits, move it aside, "
            f"re-install, then merge your edits back from the moved copy. "
            f"Don't use --adopt for this: it records every skipped file as "
            f"the installer's, so the next install replaces each steering "
            f"doc you or Claude filled in, with no backup.")


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
    # [WP4 fix round 1 / F2] Per element: only the Never section is gone,
    # so only it is named.
    check("greenfield CLAUDE.md kept with no `## Never` section: one warning "
          "names that section, and none of the Phase 8 elements still there",
          rg.returncode == 0 and len(wc) == 1
          and "this release's Phase 8 text, and it has no '## Never' "
              "section." in wc[0]
          and not any(e in wc[0] for e in ("session-hygiene", "'## Index'",
                                           "`/escalate`"))
          and "Merge it by hand from a fresh install's CLAUDE.md." in wc[0],
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

    # ---- 6. Fix round 1: the step 7 review's 8a findings --------------- #
    print("\n== 6. fix round 1: kept files the review found misread ==")
    STRIP_NEVER = re.compile(r"^## Never\n.*?(?=^## )", re.S | re.M)
    HYGIENE = re.compile(r"^\*\*Session hygiene:\*\*.*?\n\n", re.S | re.M)
    ESCALATE = "Before you stop for a 🔔 item, run `/escalate` to record why.\n"

    def skip_reason(out, path):
        return next((ln.split("(", 1)[1] for ln in out.splitlines()
                     if ln.strip().startswith("SKIP") and path in ln), "")

    def old_docs(d):
        """An earlier install's three docs: tech.md without the WP4
        sections, ci-cd.md with two stops, CLAUDE.md with no Never list."""
        write(d, TECH, read(d, TECH).split("\n## Do Not Touch", 1)[0]
              + "\n## Stack\n\nPython.\n")
        write(d, CICD, read(d, CICD).split("## Agent stopping point", 1)[0]
              + TWO_STOPS)
        write(d, "CLAUDE.md", STRIP_NEVER.sub("", read(d, "CLAUDE.md")))

    # [K1] A fresh clone's re-install wrote a manifest that recorded the
    # kept files as local edits, so the second re-install called them
    # "locally modified" and sent CLAUDE.md to a hand merge.
    k1 = proj("k1-clone")
    run(k1)
    old_docs(k1)
    os.remove(os.path.join(k1, MANIFEST))
    k1runs = [run(k1) for _ in range(3)]
    for rel in (TECH, CICD, "CLAUDE.md"):
        per_run = [warns(r, rel) for r in k1runs]
        check(f"[K1] fresh clone, three re-installs: {rel}'s warning ends "
              f"with the per-file remedy every time, and says the same each "
              f"run",
              all(r.returncode == 0 for r in k1runs)
              and all(len(w) == 1 and w[0].endswith(no_manifest(rel))
                      for w in per_run)
              and per_run[0] == per_run[1] == per_run[2],
              [w[0][-300:] if w else None for w in per_run])
        check(f"[K1] ... and {rel}'s SKIP line gives the same reason each "
              f"run, never 'locally modified'",
              len({skip_reason(r.stdout, rel) for r in k1runs}) == 1
              and "locally modified" not in skip_reason(k1runs[2].stdout,
                                                        rel)
              and "had no installer manifest" in skip_reason(
                  k1runs[2].stdout, rel),
              [skip_reason(r.stdout, rel) for r in k1runs])
    _k1steps = [r.stdout[r.stdout.find("Next steps:"):] for r in k1runs]
    check("[K1] ... and Next steps is the same each run",
          "Next steps:" in _k1steps[0]
          and _k1steps[0] == _k1steps[1] == _k1steps[2], _k1steps[2][:600])
    # A file someone edits after that is proven edited: the hand fix.
    write(k1, CICD, read(k1, CICD) + "\nA line the team added.\n")
    k1e = run(k1)
    we = warns(k1e, CICD)
    check("[K1] edited after the first re-install: ci-cd.md is a local edit "
          "now, and its warning gives the hand fix",
          k1e.returncode == 0 and "locally modified" in skip_reason(
              k1e.stdout, CICD)
          and len(we) == 1 and no_manifest(CICD) not in we[0]
          and we[0].endswith("Keep one, as Bootstrap Protocol Phase 5 asks."),
          we)
    check("[K1] ... while the files nobody touched keep the remedy",
          all(len(warns(k1e, rel)) == 1
              and warns(k1e, rel)[0].endswith(no_manifest(rel))
              for rel in (TECH, "CLAUDE.md")), k1e.stderr[-800:])

    # [F2] Headings match by prefix, whatever their case or a suffix.
    PCFG = CFG.replace('test: "true"', 'test: "pytest -q"')
    f2 = proj("f2", PCFG)
    run(f2)
    fresh_tech, fresh_md = read(f2, TECH), read(f2, "CLAUDE.md")
    for label, text in (
            ("sentence case", fresh_tech.replace(
                "## Do Not Touch", "## Do not touch").replace(
                "## Documentation Policy", "## Documentation policy")),
            ("a suffix", fresh_tech.replace(
                "## Do Not Touch", "## Do Not Touch (paths agents never "
                "edit)"))):
        write(f2, TECH, text + "\nFilled.\n")
        rt = run(f2)
        check(f"[F2] tech.md kept with its two headings in {label}: no "
              f"warning", rt.returncode == 0 and skip_line(rt.stdout, TECH)
              and warns(rt, TECH) == [], warns(rt, TECH))
    write(f2, TECH, fresh_tech)
    write(f2, "CLAUDE.md", fresh_md.replace("## Never\n",
                                            "## Never do these\n"))
    rn = run(f2)
    check("[F2] CLAUDE.md kept with its Never heading renamed '## Never do "
          "these': no warning", rn.returncode == 0
          and skip_line(rn.stdout, "CLAUDE.md")
          and warns(rn, "CLAUDE.md") == [], warns(rn, "CLAUDE.md"))
    # The other direction: an adopter's own `## Never` does not stand for
    # the index, session hygiene and the /escalate line.
    own_never = re.sub(r"^## Index.*?(?=^## )", "",
                       HYGIENE.sub("", fresh_md.replace(ESCALATE, "")),
                       flags=re.S | re.M)
    write(f2, "CLAUDE.md", own_never)
    ro = run(f2)
    wo = warns(ro, "CLAUDE.md")
    check("[F2] CLAUDE.md kept with a `## Never` section but no index, "
          "session hygiene or /escalate line: one warning names those three, "
          "and not the Never section",
          ro.returncode == 0 and len(wo) == 1
          and "it has no session-hygiene line, '## Index' section or "
              "`/escalate` line." in wo[0]
          and "'## Never'" not in wo[0], wo)
    write(f2, "CLAUDE.md", fresh_md.replace(ESCALATE, ""))
    re_ = run(f2)
    we_ = warns(re_, "CLAUDE.md")
    check("[F2] CLAUDE.md kept without only the /escalate line: the warning "
          "names only that line",
          re_.returncode == 0 and len(we_) == 1
          and "it has no `/escalate` line." in we_[0], we_)
    write(f2, "CLAUDE.md", fresh_md)

    # [F3] A Test row that names the command with a note, or in bold, is
    # not stale; one that names another command still is, quoted as written.
    TEST_ROW = re.compile(r"^\| Test +\|.*\|$", re.M)
    for label, cell, stale in (
            ("a note after it", "`pytest -q` (from the repo root; CI runs "
             "the same)", False),
            ("bold", "**`pytest -q`**", False),
            ("another command", "`make test`", True)):
        write(f2, TECH, TEST_ROW.sub(f"| Test      | {cell} |", fresh_tech))
        r3 = run(f2)
        w3 = warns(r3, TECH)
        if stale:
            check(f"[F3] Test row naming {label}: one warning, the cell "
                  f"quoted as written", r3.returncode == 0 and len(w3) == 1
                  and f"its Test row says {cell}, but commands.test is "
                      f"`pytest -q`" in w3[0], w3)
        else:
            check(f"[F3] Test row naming the command with {label}: no "
                  f"warning", r3.returncode == 0
                  and skip_line(r3.stdout, TECH) and w3 == [], w3)
    write(f2, TECH, fresh_tech)

    # [F1] Before WP4 the opt-out ci-cd.md had no stopping point at all
    # (its body, rendered by 0845862's build_plan, below).
    OLD_OPTOUT = ("# CI/CD Steering\n\n**No CI/CD** (operator opted out in "
                  "Phase 0).\n\nThe agent still runs the test command "
                  "locally:\n`true`\n\nPlaceholder for future CI addition. "
                  "Re-run the wizard's CI setup to populate.\n")
    OCFG = CFG.replace("archetype: fullstack\n",
                       "archetype: fullstack\n  cicd_opt_out: true\n")
    f1 = proj("f1-optout", OCFG)
    run(f1)
    write(f1, CICD, OLD_OPTOUT + "\nA note the team added.\n")
    r1 = run(f1)
    w1 = warns(r1, CICD)
    # [WP4 fix round 2 / LC-12 (b), RR-7] Worded so the lifecycle clause
    # does not contradict "names no stop", and with no Phase 5 citation:
    # its opt-out path skips the step that names a stop.
    check("[F1] opt-out ci-cd.md from before WP4, kept: one warning says "
          "nothing in it says where the agent stops, and that the agent stops "
          "after its last commit and never pushes",
          r1.returncode == 0 and len(w1) == 1
          and "'## Agent stopping point' section, and nothing in it says "
              "where the agent stops." in w1[0]
          and "the agent stops after its last commit for the task, and never "
              "pushes" in w1[0]
          and "CLAUDE.md's lifecycle ends at the stop this file should name."
              in w1[0]
          and "names no stop" not in w1[0] and "Phase 5" not in w1[0]
          and w1[0].endswith("Add a section that says where the agent "
                             "stops."), w1)
    write(f1, CICD, OLD_OPTOUT + "\n## Agent Stopping Point\n\nThe agent "
          "stops after its last commit. A person pushes.\n")
    r1b = run(f1)
    check("[F1] opt-out ci-cd.md kept with its own stop under a title-case "
          "heading: no warning", r1b.returncode == 0
          and skip_line(r1b.stdout, CICD) and warns(r1b, CICD) == [],
          warns(r1b, CICD))
    f1d = proj("f1-default")
    run(f1d)
    write(f1d, CICD, read(f1d, CICD).split("## Agent stopping point", 1)[0])
    r1d = run(f1d)
    w1d = warns(r1d, CICD)
    check("[F1] ci-cd.md kept with no stopping-point section, CI/CD on: the "
          "warning gives this config's stop, the pull request",
          r1d.returncode == 0 and len(w1d) == 1
          and "the agent stops after it opens a pull request, and a person "
              "merges it" in w1d[0], w1d)

    # [F4] The parse guard's copy is ignored only through the
    # `<state>.pre-*` lines, which a kept retrofit .gitignore from before
    # WP4 lacks with the lock line.
    if GIT:
        f4 = proj("f4-retro", RCFG)
        run(f4)
        write(f4, ".claude/.gitignore", read(f4, ".claude/.gitignore")
              .replace(".retrofit-state.json.lock\n", "")
              .replace(".retrofit-state.json.pre-*\n", ""))
        r4 = run(f4)
        w4 = warns(r4, ".claude/.gitignore")
        check("[F4] retrofit .claude/.gitignore kept without both WP4 lines: "
              "one warning names both, the lock and the parse guard's copy",
              r4.returncode == 0 and len(w4) == 1
              and "the lines `.retrofit-state.json.lock` and "
                  "`.retrofit-state.json.pre-*`" in w4[0]
              and "the copy the install keeps of a state file that does not "
                  "parse" in w4[0]
              and w4[0].endswith("Add those lines to .claude/.gitignore."),
              w4)
        f4g = proj("f4-green")
        run(f4g)
        write(f4g, ".claude/.gitignore", read(f4g, ".claude/.gitignore")
              .replace(".bootstrap-state.json.pre-*\n", ""))
        r4g = run(f4g)
        w4g = warns(r4g, ".claude/.gitignore")
        check("[F4] greenfield .claude/.gitignore kept without the pre-* "
              "line: one warning names it, and not the lock",
              r4g.returncode == 0 and len(w4g) == 1
              and "the line `.bootstrap-state.json.pre-*`" in w4g[0]
              and ".lock`" not in w4g[0]
              and w4g[0].endswith("Add that line to .claude/.gitignore."),
              w4g)
    else:                          # pragma: no cover
        print("  SKIP  git not found: the .gitignore rows (NOT measured)")

    # [F5] On a first install, a CLAUDE.md that was there is the project's
    # own, and the route is to move it aside, re-install, and merge it into
    # the new file (RETROFIT.md R8.E.1 in retrofit).
    for label, cfg_text, r8 in (("greenfield", CFG, False),
                                ("retrofit", RCFG, True)):
        f5 = proj("f5-" + label, cfg_text)
        write(f5, "CLAUDE.md", "# My project\n\nUse pnpm. Never push to "
              "main.\n")
        r5 = run(f5)
        w5 = warns(r5, "CLAUDE.md")
        check(f"[F5] {label} first install over the project's own CLAUDE.md: "
              f"the warning calls it the project's own and gives the "
              f"move-aside-and-merge route"
              + (", as RETROFIT.md R8.E.1 says" if r8 else ""),
              r5.returncode == 0 and len(w5) == 1
              and "was there before this project's first install, so it is "
                  "the project's own file" in w5[0]
              and "Move it aside and re-install, which creates only "
                  "CLAUDE.md, then merge your file into the new one" in w5[0]
              and ("as RETROFIT.md R8.E.1 says" in w5[0]) == r8
              and "did not receive" not in w5[0]
              and "merge the change by hand" not in w5[0], w5)
    check("[F5] a fresh clone's CLAUDE.md (an earlier install's) keeps the "
          "missed-update wording and the remedy, whose edited branch is the "
          "move-aside route",
          "did not receive this release's Phase 8 text"
          in warns(k1runs[0], "CLAUDE.md")[0]
          and "If it holds edits, move it aside, re-install, then merge your "
              "edits back from the moved copy."
          in warns(k1runs[0], "CLAUDE.md")[0]
          if warns(k1runs[0], "CLAUDE.md") else False,
          warns(k1runs[0], "CLAUDE.md"))

    # ---- 7. Fix round 2: the re-review's 8a findings ------------------- #
    print("\n== 7. fix round 2: what the re-review found in 8a ==")

    # [F3 / LC-1, P4, MS-1] A Test row whose command contains the configured
    # one inside a longer command still names another command. A cell with
    # code spans names the command only when one span is it, whitespace
    # collapsed; so the split cell "`pytest` `-q`" warns too: neither span
    # is the command, and the implementer copies a span.
    for n, (label, cmd, cell) in enumerate((
            ("make test-all for make test", "make test", "`make test-all`"),
            ("pytest -q --cov for pytest -q", "pytest -q",
             "`pytest -q --cov`"),
            ("pnpm test for npm test", "npm test", "`pnpm test`"),
            ("the command split over two code spans", "pytest -q",
             "`pytest` `-q`"))):
        f3 = proj(f"f3-superset-{n}",
                  CFG.replace('test: "true"', f'test: "{cmd}"'))
        run(f3)
        write(f3, TECH, TEST_ROW.sub(f"| Test      | {cell} |",
                                     read(f3, TECH)) + "\nFilled.\n")
        r3 = run(f3)
        w3 = warns(r3, TECH)
        check(f"[F3] Test row naming {label}: one warning, the cell quoted "
              f"as written", r3.returncode == 0 and skip_line(r3.stdout, TECH)
              and len(w3) == 1
              and f"its Test row says {cell}, but commands.test is `{cmd}`"
              in w3[0], w3)
    # With no code span, the cell is the command, or the command and a
    # parenthetical note.
    for cell, stale in (("pytest -q (from the repo root)", False),
                        ("pytest -q --cov", True)):
        write(f2, TECH, TEST_ROW.sub(f"| Test      | {cell} |", fresh_tech)
              + "\nFilled.\n")
        r3 = run(f2)
        check(f"[F3] Test row with no code span, {cell!r}: "
              + ("one warning" if stale else "no warning"),
              r3.returncode == 0 and skip_line(r3.stdout, TECH)
              and len(warns(r3, TECH)) == stale, warns(r3, TECH))
    write(f2, TECH, fresh_tech)

    # [F1 / LC-3, MS-8] Phase 5 prescribes no heading: a stop stated under
    # another heading, in a bold line or under `###` is still a stop.
    STOP_SECTION = re.compile(r"^## Agent stopping point\n.*", re.S | re.M)
    for n, (label, edit) in enumerate((
            ("under '## Where the agent stops'", lambda t: STOP_SECTION.sub(
                "## Where the agent stops\n\nThe agent stops after it opens "
                "a pull request. A person merges it.\n", t)),
            ("as a bold line", lambda t: STOP_SECTION.sub(
                "**Agent stopping point:** the pull request. A person merges "
                "it.\n", t)),
            ("under '### Agent stopping point'", lambda t: t.replace(
                "## Agent stopping point", "### Agent stopping point")))):
        f1s = proj(f"f1-stop-{n}")
        run(f1s)
        write(f1s, CICD, edit(read(f1s, CICD)))
        r1s = run(f1s)
        check(f"[F1] ci-cd.md kept with its stop stated {label}: no warning",
              r1s.returncode == 0 and skip_line(r1s.stdout, CICD)
              and warns(r1s, CICD) == [], warns(r1s, CICD))
    # [P6] The pre-WP4 opt-out ci-cd.md in a fresh clone: the per-file
    # remedy, not the hand fix.
    f1c = proj("f1-optout-clone", OCFG)
    run(f1c)
    write(f1c, CICD, OLD_OPTOUT)
    os.remove(os.path.join(f1c, MANIFEST))
    r1c = run(f1c)
    w1c = warns(r1c, CICD)
    check("[F1] the pre-WP4 opt-out ci-cd.md on a tree with no manifest: the "
          "warning ends with the per-file remedy, not the hand fix",
          r1c.returncode == 0 and len(w1c) == 1
          and w1c[0].endswith(no_manifest(CICD))
          and "Add a section" not in w1c[0], w1c)

    # [F5 / LC-2, MS-5, RR-8] The project's own CLAUDE.md is named so on
    # every run while it keeps the bytes the first install kept, and its
    # SKIP line says so too.
    OWN_MD = "# My project, from /init\n\nUse pnpm.\n"
    f5o = proj("f5-own-runs")
    write(f5o, "CLAUDE.md", OWN_MD)
    f5runs = [run(f5o) for _ in range(3)]
    f5w = [warns(r, "CLAUDE.md") for r in f5runs]
    check("[F5] three installs over the project's own CLAUDE.md: the same "
          "warning each run, which calls it the project's own",
          all(r.returncode == 0 for r in f5runs)
          and all(len(w) == 1 for w in f5w) and f5w[0] == f5w[1] == f5w[2]
          and "was there before this project's first install, so it is the "
              "project's own file" in f5w[0][0]
          and "did not receive" not in f5w[2][0]
          and "If nobody edited it" not in f5w[2][0]
          if all(f5w) else False, f5w)
    check("[F5] ... and its SKIP line says so each run",
          all("it was there before this project's first install, so it is "
              "the project's own file" in skip_reason(r.stdout, "CLAUDE.md")
              for r in f5runs), [skip_reason(r.stdout, "CLAUDE.md")
                                 for r in f5runs])
    # A project's own command at a plan path does not hide the first install.
    f5c = proj("f5-own-command")
    write(f5c, "CLAUDE.md", OWN_MD)
    os.makedirs(os.path.join(f5c, ".claude", "commands"))
    write(f5c, ".claude/commands/code-review.md", "Review my way.\n")
    r5c = run(f5c)
    w5c = warns(r5c, "CLAUDE.md")
    st5c = read(f5c, ".claude/.bootstrap-state.json") or "{}"
    check("[F5] the project's own .claude/commands/code-review.md and "
          "CLAUDE.md: still a first install (bootstrap_complete false, the "
          "own-file warning)",
          r5c.returncode == 0
          and '"bootstrap_complete": false' in st5c
          and len(w5c) == 1
          and "the project's own file" in w5c[0], (w5c, st5c[-300:]))
    f5d = proj("f5-own-dry")
    write(f5d, "CLAUDE.md", OWN_MD)
    r5d = run(f5d, "--dry-run")
    w5d = warns(r5d, "CLAUDE.md")
    check("[F5] --dry-run of a first install over the project's own "
          "CLAUDE.md: it would leave it, and the route is to move it aside "
          "before installing, then merge it into the new one",
          r5d.returncode == 0 and len(w5d) == 1
          and "the install would leave it as it is" in w5d[0]
          and "Move it aside before you install, then merge your file into "
              "the new one." in w5d[0]
          and "re-install" not in w5d[0], w5d)

    # [LC-12 (d)] "it" for one missing element, "them" for more.
    check("[F2] the hand remedy says 'Merge it' for one missing element and "
          "'Merge them' for three",
          we_ and we_[0].endswith("Merge it by hand from a fresh install's "
                                  "CLAUDE.md.")
          and wo and wo[0].endswith("Merge them by hand from a fresh "
                                    "install's CLAUDE.md."), (we_, wo))

    # [K1 / P1] A later re-install of a fresh clone: the hook-script
    # warning and the exit-3 note keep the per-file remedy (main()).
    k1h = proj("k1-hooks-later")
    run(k1h)
    os.remove(os.path.join(k1h, MANIFEST))
    write(k1h, "bootstrap.config.yaml",
          CFG.replace('test: "true"', 'test: "pytest -q"')
          + "secrets:\n  never_read_paths:\n    - \".env*\"\n"
            "    - \"private/**\"\n")
    k1hr = [run(k1h) for _ in range(2)]
    TG, SG = ".claude/hooks/test-gate.sh", ".claude/hooks/secrets-gate.sh"
    wtg = warns(k1hr[1], TG)
    sec = k1hr[1].stderr[k1hr[1].stderr.find("security-critical files were "
                                             "NOT written"):]
    check("[K1] a fresh clone with a changed commands.test and "
          "never_read_paths, re-installed twice: on run 2 the test-gate.sh "
          "warning ends with the per-file remedy",
          [r.returncode for r in k1hr] == [3, 3] and len(wtg) == 1
          and wtg[0].endswith(no_manifest(TG))
          and "kept your local edits" not in k1hr[1].stderr, wtg)
    check("[K1] ... and the exit-3 block names secrets-gate.sh with the "
          "per-file remedy",
          f"- {SG}" in sec and no_manifest(SG) in sec
          and sec.find(no_manifest(SG)) < sec.find("Exiting 3"),
          sec[:1500])

    # [F2 / P2] With the skills off, CLAUDE.md has no session-hygiene or
    # /escalate line, and a kept one is not asked for them.
    SCFG = CFG + "workflow:\n  install_skills: false\n"
    f2s = proj("f2-skills-off", SCFG)
    run(f2s)
    md_off = read(f2s, "CLAUDE.md")
    write(f2s, "CLAUDE.md", md_off + "\nA project rule.\n")
    r2s = run(f2s)
    check("[F2] skills off, CLAUDE.md edited and kept: no CLAUDE.md warning",
          r2s.returncode == 0 and skip_line(r2s.stdout, "CLAUDE.md")
          and warns(r2s, "CLAUDE.md") == [], warns(r2s, "CLAUDE.md"))
    write(f2s, "CLAUDE.md", re.sub(r"^## Index.*?(?=^## )", "", md_off,
                                   flags=re.S | re.M))
    r2t = run(f2s)
    w2t = warns(r2t, "CLAUDE.md")
    check("[F2] skills off, kept CLAUDE.md without its index: the warning "
          "names only the Index section",
          r2t.returncode == 0 and len(w2t) == 1
          and "and it has no '## Index' section." in w2t[0]
          and "session-hygiene" not in w2t[0] and "/escalate" not in w2t[0],
          w2t)

    # [F2 / P7] A heading's prefix ends at a word boundary, and whitespace
    # inside it is collapsed.
    write(f2, "CLAUDE.md", re.sub(r"^## Index[^\n]*", "## Indexing notes",
                                  fresh_md, flags=re.M))
    rix = run(f2)
    wix = warns(rix, "CLAUDE.md")
    check("[F2] CLAUDE.md kept with '## Indexing notes' for its index: the "
          "warning names the Index section",
          rix.returncode == 0 and len(wix) == 1
          and "it has no '## Index' section." in wix[0], wix)
    write(f2, "CLAUDE.md", fresh_md.replace("## Never\n",
                                            "## Nevertheless\n"))
    rnl = run(f2)
    wnl = warns(rnl, "CLAUDE.md")
    check("[F2] CLAUDE.md kept with '## Nevertheless' for its Never list: "
          "the warning names the Never section",
          rnl.returncode == 0 and len(wnl) == 1
          and "it has no '## Never' section." in wnl[0], wnl)
    write(f2, "CLAUDE.md", fresh_md)
    write(f2, TECH, fresh_tech.replace("## Do Not Touch", "##  Do Not Touch")
          + "\nFilled.\n")
    rdn = run(f2)
    check("[F2] tech.md kept with '##  Do Not Touch' (two spaces): no "
          "warning", rdn.returncode == 0 and skip_line(rdn.stdout, TECH)
          and warns(rdn, TECH) == [], warns(rdn, TECH))
    write(f2, TECH, fresh_tech)
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

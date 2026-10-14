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

Run: python3 tests/test_wp4_steering.py
"""
import ast
import os
import re
import sys

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

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

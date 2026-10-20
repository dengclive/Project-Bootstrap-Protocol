#!/usr/bin/env python3
"""[WP4] The must-not-change pin: hook bodies, gates.py, the SDK template and
_HOOK_HEADER stay byte-identical.

What this guards. The 2026-09-27 pivot builds the PRD minus the security
gates: secrets-gate, dependency-gate, their SDK functions and _HOOK_HEADER
stay byte-identical. WP4 also keeps every emitted hook body byte-identical.
If a row goes red during WP4, stop: one of them moved.

Each pin is a sha256 taken at 0845862, WP4's base, and written in below as
a literal, never read from another suite's tables:
  - every `.claude/hooks/*.sh` body in the six golden fixtures and fixture
    E: 82 bodies, 11/15/11/11/11/15 plus 8;
  - `.claude/sdk_gates/gates.py` in the sdk_callable fixture;
  - the bytes of lib/sdk_gates_template.py;
  - _HOOK_HEADER's source string in lib/templates.py.

The six golden configs are read with ast from tests/test_greenfield_golden.py
and tests/test_retrofit.py, as tests/test_merge_back.py reads them, so this
suite renders the configs those suites pin. Fixture E, the gates-off config,
is a literal below until WP4 adds it to the goldens.

A later package that changes a hook on purpose updates these pins under its
own freeze exception. Freeze exception 87 (the v2.9.0 release) moved two:
iteration-summary-enforcement.sh in full_autonomous and retrofit agent, by
one protocol citation.

Run: python3 tests/test_wp4_must_not_change.py
"""
import ast
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "lib"))

from defaults import resolve_config  # noqa: E402
from installer import build_plan  # noqa: E402
from minyaml import load_yaml  # noqa: E402

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


def sha(data):
    """sha256 of bytes, or of a str encoded as UTF-8."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def golden_fixture_texts():
    """The six golden configs, read with ast (never by running the suites),
    as tests/test_merge_back.py's _golden_fixture_texts reads them."""
    with open(os.path.join(ROOT, "bootstrap.config.yaml"),
              encoding="utf-8") as fh:
        env = {"FIXTURE_DEFAULT": fh.read()}
    for f, names in (("test_greenfield_golden.py",
                      ("FIXTURE_FULL_AUTONOMOUS", "FIXTURE_DESIGN_STEERING",
                       "FIXTURE_SDK_CALLABLE")),
                     ("test_retrofit.py",
                      ("SERVICE_RETROFIT_CFG", "AGENT_RETROFIT_CFG"))):
        path = os.path.join(HERE, f)
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in tree.body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id in names):
                env[node.targets[0].id] = eval(compile(
                    ast.Expression(node.value), path, "eval"), dict(env))
    return env


# Fixture E: the build plan's gates-off config (its section 1 switches, and
# "true" for every command it sets). WP4 adds it to the goldens; until then
# it is a literal here.
FIXTURE_E = """project: {name: "demo", archetype: "fullstack", shell: "bash"}
principles: {tdd_policy: encouraged}
secrets: {enabled: false}
deps: {enabled: false}
hooks: {secrets_gate: false, dependency_gate: false, spec_gate_commit: false}
commands: {test: "true", lint: "true", format: "true", ci_local: "true"}
workflow: {implementer_isolation: "none"}
"""

_fx = golden_fixture_texts()
# (label, config text). The labels are the fixture names
# tests/test_wp3_records.py uses.
FIXTURES = (("default", _fx.get("FIXTURE_DEFAULT")),
            ("full_autonomous", _fx.get("FIXTURE_FULL_AUTONOMOUS")),
            ("design_steering", _fx.get("FIXTURE_DESIGN_STEERING")),
            ("sdk_callable", _fx.get("FIXTURE_SDK_CALLABLE")),
            ("retrofit service", _fx.get("SERVICE_RETROFIT_CFG")),
            ("retrofit agent", _fx.get("AGENT_RETROFIT_CFG")),
            ("fixture E", FIXTURE_E))

# The number of hook bodies each fixture renders at 0845862.
EXPECTED_HOOK_COUNTS = {"default": 11, "full_autonomous": 15,
                        "design_steering": 11, "sdk_callable": 11,
                        "retrofit service": 11, "retrofit agent": 15,
                        "fixture E": 8}

# sha256 of each `.claude/hooks/*.sh` body at 0845862, per fixture, in plan
# order.
HOOK_PINS = {
    "default": {
        ".claude/hooks/spec-gate-entry.sh":
            "9dbfd634bc810d4da4cf7852b8b33ac09eab6d58aa7139a55199e56111ab45f6",
        ".claude/hooks/spec-gate-commit.sh":
            "ff394b90c50ad664d1e53d5207e741a413e71383d2516dccc0def1d1912174a4",
        ".claude/hooks/secrets-gate.sh":
            "02f17a7fa56e59858eeda617327eac1e4bade2b733f6afed09e6a05981edc26e",
        ".claude/hooks/test-gate.sh":
            "f0ed3a112715aab978a9e79ef986fcc6d6f745fa7c582486a61ba1a0399a771d",
        ".claude/hooks/format-lint-gate.sh":
            "36443501f2d00929217d9176a58f756bcc3237a39eb6cddcd99dbc8098cb99f1",
        ".claude/hooks/cost-log.sh":
            "6b9706ddd90835784cf680f9d905397abba041f8d7ec9f7b45277a06b18e1dd4",
        ".claude/hooks/dependency-gate.sh":
            "54bc5d6edc2eaf583f284938e85d5af0cdf4b081de32b6619486c05233f73ca7",
        ".claude/hooks/drift-detector.sh":
            "5d8b8ce131736563e3c77a9e2f222c8dda01074023566ceb0f53cd70859f87dd",
        ".claude/hooks/task-done-alarm.sh":
            "4f68e00fb09d6f11f0e3255018ccd9bbf48ae1cfd99c5cd8d7fb7f22266bd489",
        ".claude/hooks/decision-required-alarm.sh":
            "6970cec262bf0c49deb913ad325e0931fb495dbd204ba6485946371c5e095a13",
        ".claude/hooks/ci-mirror.sh":
            "261e13a56ae6628be80b67a4934b1d593f8cdc69e8a3b345bd38c6d244c41b94",
    },
    "full_autonomous": {
        ".claude/hooks/spec-gate-entry.sh":
            "9dbfd634bc810d4da4cf7852b8b33ac09eab6d58aa7139a55199e56111ab45f6",
        ".claude/hooks/spec-gate-commit.sh":
            "ff394b90c50ad664d1e53d5207e741a413e71383d2516dccc0def1d1912174a4",
        ".claude/hooks/secrets-gate.sh":
            "02f17a7fa56e59858eeda617327eac1e4bade2b733f6afed09e6a05981edc26e",
        ".claude/hooks/test-gate.sh":
            "2f3566cdbba72ee00b3ad946efba172ae625b365282406b9fca6cacb103ab1d8",
        ".claude/hooks/format-lint-gate.sh":
            "5fa72ad0281ab604d6f44970d0e928356cd04dceb581eb119ec61275c0b64408",
        ".claude/hooks/cost-log.sh":
            "6b9706ddd90835784cf680f9d905397abba041f8d7ec9f7b45277a06b18e1dd4",
        ".claude/hooks/dependency-gate.sh":
            "54bc5d6edc2eaf583f284938e85d5af0cdf4b081de32b6619486c05233f73ca7",
        ".claude/hooks/drift-detector.sh":
            "5d8b8ce131736563e3c77a9e2f222c8dda01074023566ceb0f53cd70859f87dd",
        ".claude/hooks/task-done-alarm.sh":
            "4f68e00fb09d6f11f0e3255018ccd9bbf48ae1cfd99c5cd8d7fb7f22266bd489",
        ".claude/hooks/decision-required-alarm.sh":
            "6970cec262bf0c49deb913ad325e0931fb495dbd204ba6485946371c5e095a13",
        ".claude/hooks/ci-mirror.sh":
            "92fd1763767cbbdff1190bd45ac35df418e43417609cd0e32c539ccb6ef963bd",
        ".claude/hooks/tdd-gate.sh":
            "638e586b7095d1c44b7cfbc61059ea904f7de0804d60cffba7e1491fdf963787",
        ".claude/hooks/eval-gate.sh":
            "84c2d532c175ce126a2905c17f8a73c5cae785d2d76804adb297abef2585f32c",
        ".claude/hooks/drift-detector-loop-cooperation.sh":
            "dfeed9329516ef8bda34120fea800a259b8208faec84afc4540cc661037cc377",
        # [freeze-exception no. 87, 2026-10-20] v2.9.0 release. The head
        # block moved the protocol 27 lines; this body's one protocol
        # citation moved with it (:799-800 -> :826-827, the citation
        # tests/test_doc_citations.py pins). Nothing else moved: with that
        # citation reverted the body hashes to the pin it replaces,
        # b154cde91c61..., 0845862's.
        ".claude/hooks/iteration-summary-enforcement.sh":
            "caa4fc9cd60800735e087a437a67ffdbdc1541b6624ff3bd39cb43d774f9c526",
    },
    "design_steering": {
        ".claude/hooks/spec-gate-entry.sh":
            "9dbfd634bc810d4da4cf7852b8b33ac09eab6d58aa7139a55199e56111ab45f6",
        ".claude/hooks/spec-gate-commit.sh":
            "ff394b90c50ad664d1e53d5207e741a413e71383d2516dccc0def1d1912174a4",
        ".claude/hooks/secrets-gate.sh":
            "02f17a7fa56e59858eeda617327eac1e4bade2b733f6afed09e6a05981edc26e",
        ".claude/hooks/test-gate.sh":
            "f0ed3a112715aab978a9e79ef986fcc6d6f745fa7c582486a61ba1a0399a771d",
        ".claude/hooks/format-lint-gate.sh":
            "36443501f2d00929217d9176a58f756bcc3237a39eb6cddcd99dbc8098cb99f1",
        ".claude/hooks/cost-log.sh":
            "6b9706ddd90835784cf680f9d905397abba041f8d7ec9f7b45277a06b18e1dd4",
        ".claude/hooks/dependency-gate.sh":
            "54bc5d6edc2eaf583f284938e85d5af0cdf4b081de32b6619486c05233f73ca7",
        ".claude/hooks/drift-detector.sh":
            "5d8b8ce131736563e3c77a9e2f222c8dda01074023566ceb0f53cd70859f87dd",
        ".claude/hooks/task-done-alarm.sh":
            "4f68e00fb09d6f11f0e3255018ccd9bbf48ae1cfd99c5cd8d7fb7f22266bd489",
        ".claude/hooks/decision-required-alarm.sh":
            "6970cec262bf0c49deb913ad325e0931fb495dbd204ba6485946371c5e095a13",
        ".claude/hooks/ci-mirror.sh":
            "261e13a56ae6628be80b67a4934b1d593f8cdc69e8a3b345bd38c6d244c41b94",
    },
    "sdk_callable": {
        ".claude/hooks/spec-gate-entry.sh":
            "9dbfd634bc810d4da4cf7852b8b33ac09eab6d58aa7139a55199e56111ab45f6",
        ".claude/hooks/spec-gate-commit.sh":
            "ff394b90c50ad664d1e53d5207e741a413e71383d2516dccc0def1d1912174a4",
        ".claude/hooks/secrets-gate.sh":
            "02f17a7fa56e59858eeda617327eac1e4bade2b733f6afed09e6a05981edc26e",
        ".claude/hooks/test-gate.sh":
            "f0ed3a112715aab978a9e79ef986fcc6d6f745fa7c582486a61ba1a0399a771d",
        ".claude/hooks/format-lint-gate.sh":
            "36443501f2d00929217d9176a58f756bcc3237a39eb6cddcd99dbc8098cb99f1",
        ".claude/hooks/cost-log.sh":
            "6b9706ddd90835784cf680f9d905397abba041f8d7ec9f7b45277a06b18e1dd4",
        ".claude/hooks/dependency-gate.sh":
            "54bc5d6edc2eaf583f284938e85d5af0cdf4b081de32b6619486c05233f73ca7",
        ".claude/hooks/drift-detector.sh":
            "5d8b8ce131736563e3c77a9e2f222c8dda01074023566ceb0f53cd70859f87dd",
        ".claude/hooks/task-done-alarm.sh":
            "4f68e00fb09d6f11f0e3255018ccd9bbf48ae1cfd99c5cd8d7fb7f22266bd489",
        ".claude/hooks/decision-required-alarm.sh":
            "6970cec262bf0c49deb913ad325e0931fb495dbd204ba6485946371c5e095a13",
        ".claude/hooks/ci-mirror.sh":
            "261e13a56ae6628be80b67a4934b1d593f8cdc69e8a3b345bd38c6d244c41b94",
    },
    "retrofit service": {
        ".claude/hooks/spec-gate-entry.sh":
            "9dbfd634bc810d4da4cf7852b8b33ac09eab6d58aa7139a55199e56111ab45f6",
        ".claude/hooks/spec-gate-commit.sh":
            "ff394b90c50ad664d1e53d5207e741a413e71383d2516dccc0def1d1912174a4",
        ".claude/hooks/secrets-gate.sh":
            "02f17a7fa56e59858eeda617327eac1e4bade2b733f6afed09e6a05981edc26e",
        ".claude/hooks/test-gate.sh":
            "3d6aced45da04c888899694edbe66ff7c83573268ffe3da3d2640700f3fa56d4",
        ".claude/hooks/format-lint-gate.sh":
            "9552d877c6927ff0c0632c720d1662cdb9b0ad7e5041f3e0196c9cf769eeb5b7",
        ".claude/hooks/cost-log.sh":
            "6b9706ddd90835784cf680f9d905397abba041f8d7ec9f7b45277a06b18e1dd4",
        ".claude/hooks/dependency-gate.sh":
            "54bc5d6edc2eaf583f284938e85d5af0cdf4b081de32b6619486c05233f73ca7",
        ".claude/hooks/drift-detector.sh":
            "5d8b8ce131736563e3c77a9e2f222c8dda01074023566ceb0f53cd70859f87dd",
        ".claude/hooks/task-done-alarm.sh":
            "4f68e00fb09d6f11f0e3255018ccd9bbf48ae1cfd99c5cd8d7fb7f22266bd489",
        ".claude/hooks/decision-required-alarm.sh":
            "6970cec262bf0c49deb913ad325e0931fb495dbd204ba6485946371c5e095a13",
        ".claude/hooks/ci-mirror.sh":
            "261e13a56ae6628be80b67a4934b1d593f8cdc69e8a3b345bd38c6d244c41b94",
    },
    "retrofit agent": {
        ".claude/hooks/spec-gate-entry.sh":
            "9dbfd634bc810d4da4cf7852b8b33ac09eab6d58aa7139a55199e56111ab45f6",
        ".claude/hooks/spec-gate-commit.sh":
            "ff394b90c50ad664d1e53d5207e741a413e71383d2516dccc0def1d1912174a4",
        ".claude/hooks/secrets-gate.sh":
            "02f17a7fa56e59858eeda617327eac1e4bade2b733f6afed09e6a05981edc26e",
        ".claude/hooks/test-gate.sh":
            "041201b4b129838ad17850a2cc760f4f5e518ed4e5bd1898dd6393e61601a846",
        ".claude/hooks/format-lint-gate.sh":
            "5fa72ad0281ab604d6f44970d0e928356cd04dceb581eb119ec61275c0b64408",
        ".claude/hooks/cost-log.sh":
            "6b9706ddd90835784cf680f9d905397abba041f8d7ec9f7b45277a06b18e1dd4",
        ".claude/hooks/dependency-gate.sh":
            "54bc5d6edc2eaf583f284938e85d5af0cdf4b081de32b6619486c05233f73ca7",
        ".claude/hooks/drift-detector.sh":
            "5d8b8ce131736563e3c77a9e2f222c8dda01074023566ceb0f53cd70859f87dd",
        ".claude/hooks/task-done-alarm.sh":
            "4f68e00fb09d6f11f0e3255018ccd9bbf48ae1cfd99c5cd8d7fb7f22266bd489",
        ".claude/hooks/decision-required-alarm.sh":
            "6970cec262bf0c49deb913ad325e0931fb495dbd204ba6485946371c5e095a13",
        ".claude/hooks/ci-mirror.sh":
            "64daadba2e8fe96425d1dadce7a30ddfb347051703d5cc8d4da9c25850340f06",
        ".claude/hooks/tdd-gate.sh":
            "1987750e362d4a2cdffdcce2462befb414051af95b51e1cb5bf6d0150e9a39d1",
        ".claude/hooks/eval-gate.sh":
            "84c2d532c175ce126a2905c17f8a73c5cae785d2d76804adb297abef2585f32c",
        ".claude/hooks/drift-detector-loop-cooperation.sh":
            "dfeed9329516ef8bda34120fea800a259b8208faec84afc4540cc661037cc377",
        # [freeze-exception no. 87, 2026-10-20] v2.9.0 release. The head
        # block moved the protocol 27 lines; this body's one protocol
        # citation moved with it (:799-800 -> :826-827, the citation
        # tests/test_doc_citations.py pins). Nothing else moved: with that
        # citation reverted the body hashes to the pin it replaces,
        # b154cde91c61..., 0845862's.
        ".claude/hooks/iteration-summary-enforcement.sh":
            "caa4fc9cd60800735e087a437a67ffdbdc1541b6624ff3bd39cb43d774f9c526",
    },
    "fixture E": {
        ".claude/hooks/spec-gate-entry.sh":
            "9dbfd634bc810d4da4cf7852b8b33ac09eab6d58aa7139a55199e56111ab45f6",
        ".claude/hooks/test-gate.sh":
            "ee8cef2a492903fc3928033dcd43c08a8854d3a8e47c8a3b2df99111f8a9a767",
        ".claude/hooks/format-lint-gate.sh":
            "9552d877c6927ff0c0632c720d1662cdb9b0ad7e5041f3e0196c9cf769eeb5b7",
        ".claude/hooks/cost-log.sh":
            "6b9706ddd90835784cf680f9d905397abba041f8d7ec9f7b45277a06b18e1dd4",
        ".claude/hooks/drift-detector.sh":
            "5d8b8ce131736563e3c77a9e2f222c8dda01074023566ceb0f53cd70859f87dd",
        ".claude/hooks/task-done-alarm.sh":
            "4f68e00fb09d6f11f0e3255018ccd9bbf48ae1cfd99c5cd8d7fb7f22266bd489",
        ".claude/hooks/decision-required-alarm.sh":
            "6970cec262bf0c49deb913ad325e0931fb495dbd204ba6485946371c5e095a13",
        ".claude/hooks/ci-mirror.sh":
            "261e13a56ae6628be80b67a4934b1d593f8cdc69e8a3b345bd38c6d244c41b94",
    },
}
GATES_PY_SHA = \
    "635d99e4b717d3435e30ca079b670d5b78a627c9b52b5df2dba4bee7a23339a0"
SDK_TEMPLATE_SHA = \
    "2542e114d83a4ebbc70bac0ebc78cc47d2bc2959824759f77a145169379dbcb2"
HOOK_HEADER_SHA = \
    "df29424a0c0fe29ecb5a2d24d8d24ed340b516645e94f91b511e8c5ce058d893"

HOOK_DIR = ".claude/hooks/"
GATES_PY = ".claude/sdk_gates/gates.py"


def render(text):
    """The plan for a config, by path, rendered as test_merge_back's plan_of
    renders it: build_plan(resolve_config(load_yaml(text))). Returns
    (None, errors) when the config is missing or does not resolve."""
    if text is None:
        return None, ["config not found"]
    cfg, errs = resolve_config(load_yaml(text))
    if errs:
        return None, errs
    return {a["path"]: a for a in build_plan(cfg)}, []


def hook_shas(plan):
    return {p: sha(a["body"]) for p, a in plan.items()
            if p.startswith(HOOK_DIR) and p.endswith(".sh")}


# --------------------------------------------------------------------------- #
# 1. The seven fixtures render
# --------------------------------------------------------------------------- #
print("\n=== 1. The seven fixtures render ===")
PLANS, ERRS = {}, {}
for _label, _text in FIXTURES:
    PLANS[_label], ERRS[_label] = render(_text)
check("the seven fixture configs are found and resolve without errors",
      all(PLANS[_label] is not None for _label, _ in FIXTURES),
      {_label: _e for _label, _e in ERRS.items() if _e})
ACTUAL = {_label: (hook_shas(_p) if _p is not None else {})
          for _label, _p in PLANS.items()}

# --------------------------------------------------------------------------- #
# 2. Every hook body, per fixture
# --------------------------------------------------------------------------- #
print("\n=== 2. Every hook body, per fixture ===")
for _label, _ in FIXTURES:
    _pins, _got = HOOK_PINS.get(_label, {}), ACTUAL[_label]
    _moved = sorted(p for p in _pins if p in _got and _got[p] != _pins[p])
    _missing = sorted(p for p in _pins if p not in _got)
    check(f"{_label}: its {len(_pins)} pinned hook bodies match their pins "
          f"(0845862's, or a later freeze exception's)",
          bool(_pins) and not _moved and not _missing,
          "; ".join([f"moved: {p} (sha256 {_got[p][:12]}..., pinned "
                     f"{_pins[p][:12]}...)" for p in _moved]
                    + [f"missing: {p}" for p in _missing]) or "no pins")

# --------------------------------------------------------------------------- #
# 3. The pins are not vacuous
# --------------------------------------------------------------------------- #
print("\n=== 3. The pins are not vacuous ===")
check("the pins hold 82 hook bodies, 11/15/11/11/11/15 in the six golden "
      "fixtures plus 8 in fixture E, the counts each rendered at 0845862",
      {_label: len(_v) for _label, _v in HOOK_PINS.items()}
      == EXPECTED_HOOK_COUNTS
      and sum(len(_v) for _v in HOOK_PINS.values()) == 82,
      {_label: len(_v) for _label, _v in HOOK_PINS.items()})
for _label, _ in FIXTURES:
    _got, _pins = ACTUAL[_label], HOOK_PINS.get(_label, {})
    _added = sorted(set(_got) - set(_pins))
    _removed = sorted(set(_pins) - set(_got))
    check(f"{_label} renders {EXPECTED_HOOK_COUNTS[_label]} hook bodies, "
          f"the pinned set (none added, none removed)",
          len(_got) == EXPECTED_HOOK_COUNTS[_label] and not _added
          and not _removed,
          {"rendered": len(_got), "added": _added, "removed": _removed})
check("each of the seven fixtures renders at least one hook body",
      all(ACTUAL[_label] for _label, _ in FIXTURES),
      [_label for _label, _ in FIXTURES if not ACTUAL[_label]])

# --------------------------------------------------------------------------- #
# 4. gates.py, the SDK template and _HOOK_HEADER
# --------------------------------------------------------------------------- #
print("\n=== 4. gates.py, the SDK template and _HOOK_HEADER ===")
_gates = (PLANS.get("sdk_callable") or {}).get(GATES_PY)
check(f"sdk_callable: {GATES_PY} is byte-identical to 0845862's",
      _gates is not None and sha(_gates["body"]) == GATES_PY_SHA,
      "not rendered" if _gates is None else f"sha256 {sha(_gates['body'])}")
with open(os.path.join(ROOT, "lib", "sdk_gates_template.py"), "rb") as _fh:
    _tpl = _fh.read()
check("lib/sdk_gates_template.py is byte-identical to 0845862's",
      sha(_tpl) == SDK_TEMPLATE_SHA, f"sha256 {sha(_tpl)}")


def hook_header_source():
    """_HOOK_HEADER's source string: the one module-level assignment of a
    string literal to _HOOK_HEADER in lib/templates.py. At import the module
    fills the cmdpos placeholders into it; the hook-body pins above cover
    the filled bytes."""
    with open(os.path.join(ROOT, "lib", "templates.py"),
              encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    hits = [n.value.value for n in tree.body
            if isinstance(n, ast.Assign) and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id == "_HOOK_HEADER"
            and isinstance(n.value, ast.Constant)
            and isinstance(n.value.value, str)]
    return hits[0] if len(hits) == 1 else None


_hdr = hook_header_source()
check("lib/templates.py: _HOOK_HEADER's source string is byte-identical to "
      "0845862's",
      _hdr is not None and sha(_hdr) == HOOK_HEADER_SHA,
      "no single string assignment found" if _hdr is None
      else f"sha256 {sha(_hdr)}")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

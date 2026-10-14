"""[WP4, ruling 2 (b)] The one map from each plugin/toolchain/ copy to its
source. A helper module, not a suite: bin/run-tests discovers only test_*.py.

A plugin installed from a git-hosted marketplace is copied into the plugin
cache, and files outside the plugin directory are not copied. So the
commands cannot reach `${CLAUDE_PLUGIN_ROOT}/../bin`, and plugin/toolchain/
holds real copies of what they run:

  plugin/toolchain/bin/bootstrap-install    <- bin/bootstrap-install    0755
  plugin/toolchain/bin/bootstrap-interview  <- bin/bootstrap-interview  0755
  plugin/toolchain/lib/<name>               <- lib/<name>               0644
      for every git-tracked lib/*.py, so a new module is picked up
  plugin/toolchain/protocol.md              <- the file that
      templates.PROTOCOL_DOC names                                       0644

Not copied: bin/retrofit-interview, bin/run-tests and bin/trust-ramp. No
plugin command calls them; retrofit-interview comes with the RETROFIT.md
copy that publishing needs.

Three suites read this map, so they cannot drift apart:
tests/test_wp4_plugin_toolchain.py checks the copies against it (and its
--sync rewrites them from it), and the two scans that would otherwise read
each copy as a second source file, section 4 of
tests/test_dynamic_workflow_policy.py and of tests/test_doc_citations.py,
skip a copy only while its bytes equal its source and fail on any other
file under plugin/toolchain/ (ignored bytecode aside).
"""
import functools
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "lib"))

import templates                                  # noqa: E402

TOOLCHAIN = "plugin/toolchain"
BIN_TOOLS = ("bootstrap-install", "bootstrap-interview")
SYNC = "python3 tests/test_wp4_plugin_toolchain.py --sync"
# Stages what --sync wrote and the deletion of each stray it removed.
STAGE = f"git add -A {TOOLCHAIN}"


def path_of(root, rel):
    """The file system path of `rel`, a "/"-separated path under `root`."""
    return os.path.join(root, *rel.split("/"))


def rel_of(root, path):
    """`path` relative to `root`, "/"-separated, as git lists it."""
    return os.path.relpath(path, root).replace(os.sep, "/")


def git_files(root, *pathspecs):
    """The tracked paths under `root` that match `pathspecs`."""
    r = subprocess.run(["git", "ls-files", "-z", "--", *pathspecs], cwd=root,
                       capture_output=True, text=True, check=True)
    return sorted(p for p in r.stdout.split("\0") if p)


@functools.lru_cache(maxsize=None)
def copy_map(root=ROOT):
    """{copy: (source, mode)}, both paths relative to `root`."""
    m = {f"{TOOLCHAIN}/bin/{n}": (f"bin/{n}", 0o755) for n in BIN_TOOLS}
    for src in git_files(root, "lib/*.py"):
        m[f"{TOOLCHAIN}/{src}"] = (src, 0o644)
    m[f"{TOOLCHAIN}/protocol.md"] = (templates.PROTOCOL_DOC, 0o644)
    return m


def is_cache(rel):
    """Bytecode that running a copy in place writes. Git ignores it
    (.gitignore: `__pycache__/`, `*.pyc`), so no copy ever ships it."""
    return "__pycache__" in rel.split("/") or rel.endswith(".pyc")


def same_bytes(root, copy, source):
    """True when both files exist and hold the same bytes."""
    try:
        with open(path_of(root, copy), "rb") as a, \
                open(path_of(root, source), "rb") as b:
            return a.read() == b.read()
    except OSError:
        return False


def toolchain_kind(rel, root=ROOT):
    """How a scan treats `rel`: None outside plugin/toolchain/; "cache" for
    ignored bytecode; "copy" for a copy this map names whose bytes equal its
    source (the source is scanned under its own name, so the copy adds
    nothing); "stray" for any other file there, which a scan fails on."""
    if not rel.startswith(TOOLCHAIN + "/"):
        return None
    if is_cache(rel):
        return "cache"
    src = copy_map(root).get(rel)
    if src and not os.path.islink(path_of(root, rel)) \
            and same_bytes(root, rel, src[0]):
        return "copy"
    return "stray"

#!/usr/bin/env python3
"""[WP4, ruling 2 (b)] plugin/toolchain/ holds real copies of the toolchain,
and they match the map in tests/plugin_toolchain_map.py.

A plugin installed from a git-hosted marketplace is copied into the plugin
cache, and files outside the plugin directory are not copied, so the plugin
commands run `"${CLAUDE_PLUGIN_ROOT}/toolchain/bin/..."`, never `../bin`.
The copies are duplicates of tracked files, so this suite stands in for a
review of them: a later edit to bin/, lib/ or the protocol document that is
not re-synced fails here.

  1. `git ls-files plugin/toolchain` equals the map's copy set, so a copy
     that is not committed, or a tracked file the map does not name, fails.
     Ignored bytecode (__pycache__/, *.pyc) is never tracked, so it never
     counts.
  2. Every copy's bytes equal its source.
  3. Every copy's exec bit equals its mode in the map, in the working tree
     and in the index.
  4. No symlink anywhere under plugin/: a link out of the plugin is not
     copied into the cache.
  5. In a scratch repository: --sync makes the copies from nothing; a
     planted .pyc under plugin/toolchain/lib leaves every check green; a
     changed byte, a cleared exec bit, a tracked stray file and a symlink
     each turn their check red; and --sync repairs all four.

The plugin commands' paths, and installs from a copy of plugin/ outside the
repository, are tests/test_installer.py's G11 rows.

Run: python3 tests/test_wp4_plugin_toolchain.py
Re-sync after editing a source, then stage the result:
  python3 tests/test_wp4_plugin_toolchain.py --sync
  git add -A plugin/toolchain
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import plugin_toolchain_map as PTM                # noqa: E402

GIT = shutil.which("git")

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
            print(f"        {str(detail)[:1500]}")


def sync(root):
    """Rewrite plugin/toolchain/ under `root` from the map: copy each source's
    bytes, set its mode, and delete every other file there, links and
    bytecode included. Returns (written, removed)."""
    m = PTM.copy_map(root)
    top = PTM.path_of(root, PTM.TOOLCHAIN)
    written, removed = [], []
    if os.path.islink(top):
        os.unlink(top)
        removed.append(PTM.TOOLCHAIN)
    for base, dirs, files in os.walk(top):
        for n in list(dirs):
            p = os.path.join(base, n)
            if os.path.islink(p) or n == "__pycache__":
                # A link to a directory is unlinked, never followed: the
                # critic's design linked toolchain/lib to ../../lib.
                if os.path.islink(p):
                    os.unlink(p)
                else:
                    shutil.rmtree(p)
                removed.append(PTM.rel_of(root, p))
                dirs.remove(n)
        for n in files:
            p = os.path.join(base, n)
            rel = PTM.rel_of(root, p)
            if rel not in m or os.path.islink(p):
                os.unlink(p)
                removed.append(rel)
    for base, dirs, files in os.walk(top, topdown=False):
        if base != top and not os.listdir(base):
            os.rmdir(base)
    for copy, (src, mode) in sorted(m.items()):
        dst = PTM.path_of(root, copy)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not PTM.same_bytes(root, copy, src):
            if os.path.lexists(dst):
                os.unlink(dst)
            shutil.copyfile(PTM.path_of(root, src), dst)
            written.append(copy)
        os.chmod(dst, mode)
    return written, removed


def index_modes(root):
    """{path: mode} for every tracked path under plugin/toolchain/."""
    r = subprocess.run(["git", "ls-files", "-s", "-z", "--", PTM.TOOLCHAIN],
                       cwd=root, capture_output=True, text=True, check=True)
    out = {}
    for entry in r.stdout.split("\0"):
        if entry:
            meta, path = entry.split("\t", 1)
            out[path] = meta.split()[0]
    return out


def mismatches(root):
    """{check: offenders} for plugin/toolchain/ under `root`; every list is
    empty when the copies match the map."""
    m = PTM.copy_map(root)
    tracked = set(PTM.git_files(root, PTM.TOOLCHAIN))
    modes = index_modes(root)
    bad_mode = []
    for copy, (_src, mode) in sorted(m.items()):
        path = PTM.path_of(root, copy)
        want = bool(mode & 0o100)
        if not os.path.isfile(path) or os.path.islink(path) \
                or bool(os.stat(path).st_mode & 0o100) != want:
            bad_mode.append(f"{copy} (working tree)")
        if copy in modes and modes[copy] != ("100755" if want else "100644"):
            bad_mode.append(f"{copy} (index {modes[copy]})")
    plugin = PTM.path_of(root, "plugin")
    links = [PTM.rel_of(root, plugin)] if os.path.islink(plugin) else []
    for base, dirs, files in os.walk(plugin):
        links += [PTM.rel_of(root, os.path.join(base, n))
                  for n in sorted(dirs + files)
                  if os.path.islink(os.path.join(base, n))]
    return {
        "tracked": sorted(f"{p} ({'untracked' if p in m else 'not in map'})"
                          for p in tracked ^ set(m)),
        "bytes": [c for c, (s, _) in sorted(m.items())
                  if not PTM.same_bytes(root, c, s)],
        "mode": bad_mode,
        "links": links,
    }


ROWS = {
    "tracked": "`git ls-files plugin/toolchain` equals the map's copy set",
    "bytes": "every copy's bytes equal its source",
    "mode": "every copy's exec bit equals its mode in the map",
    "links": "no symlink anywhere under plugin/",
}


if sys.argv[1:] == ["--sync"]:
    _written, _removed = sync(ROOT)
    for _p in _written:
        print(f"  wrote    {_p}")
    for _p in _removed:
        print(f"  removed  {_p}")
    print(f"{PTM.TOOLCHAIN}/ matches the map: {len(PTM.copy_map(ROOT))} "
          f"copies, {len(_written)} written, {len(_removed)} removed. "
          f"Stage it with: {PTM.STAGE}")
    sys.exit(0)


# --------------------------------------------------------------------------- #
print("\n=== 1-4. The copies match the map ===")
MAP = PTM.copy_map(ROOT)
_libs = [c for c in MAP if c.startswith(PTM.TOOLCHAIN + "/lib/")]
check(f"the map names {len(MAP)} copies: the {len(PTM.BIN_TOOLS)} tools, "
      f"every tracked lib/*.py ({len(_libs)}) and the protocol document",
      len(MAP) == len(PTM.BIN_TOOLS) + len(_libs) + 1
      and len(_libs) == len(PTM.git_files(ROOT, "lib/*.py")) >= 10
      and f"{PTM.TOOLCHAIN}/protocol.md" in MAP,
      sorted(MAP))
check("the map leaves out the tools no plugin command calls",
      not any(c.endswith(("/retrofit-interview", "/run-tests", "/trust-ramp"))
              for c in MAP), sorted(MAP))

_found = mismatches(ROOT)
for _key, _label in ROWS.items():
    check(_label, _found[_key] == [], _found[_key])
# --sync rewrites plugin/toolchain/ only; a link elsewhere under plugin/ is
# replaced by hand.
_elsewhere = [p for p in _found["links"]
              if p != PTM.TOOLCHAIN and not p.startswith(PTM.TOOLCHAIN + "/")]
if any(_found[k] for k in ("tracked", "bytes", "mode")) \
        or len(_elsewhere) < len(_found["links"]):
    print(f"\n  {PTM.TOOLCHAIN}/ does not match tests/plugin_toolchain_map.py."
          f"\n  Re-sync it, then stage it:\n      {PTM.SYNC}\n"
          f"      {PTM.STAGE}\n")
if _elsewhere:
    print(f"  --sync does not touch these links outside {PTM.TOOLCHAIN}/; "
          f"replace each with the file it names:\n      "
          + "\n      ".join(_elsewhere) + "\n")


# --------------------------------------------------------------------------- #
print("\n=== 5. The checks fire, and bytecode never counts (scratch repo) ===")


def git(root, *args):
    subprocess.run([GIT, *args], cwd=root, check=True, capture_output=True)


def red(found):
    return sorted(k for k, v in found.items() if v)


TMP = tempfile.mkdtemp(prefix="wp4-toolchain-")
try:
    S = os.path.join(TMP, "repo")
    os.makedirs(S)
    git(S, "init", "-q")
    shutil.copy2(os.path.join(ROOT, ".gitignore"), S)
    _sources = sorted({src for src, _ in MAP.values()})
    for _rel in _sources:
        os.makedirs(os.path.dirname(PTM.path_of(S, _rel)), exist_ok=True)
        shutil.copy2(PTM.path_of(ROOT, _rel), PTM.path_of(S, _rel))
    shutil.copytree(os.path.join(ROOT, "plugin"), os.path.join(S, "plugin"),
                    symlinks=True,
                    ignore=shutil.ignore_patterns("toolchain", "__pycache__"))
    git(S, "add", ".gitignore", *_sources)
    _w, _ = sync(S)
    git(S, "add", "-A", "plugin")
    # The staging command the hint and --sync print, run as printed.
    _stage = PTM.STAGE.split()[1:]
    check(f"--sync makes every copy from nothing ({len(_w)} written)",
          sorted(_w) == sorted(PTM.copy_map(S)) and red(mismatches(S)) == [],
          mismatches(S))

    _cache = os.path.join(S, *PTM.TOOLCHAIN.split("/"), "lib", "__pycache__")
    os.makedirs(_cache)
    for _p in (os.path.join(_cache, "installer.cpython-314.pyc"),
               PTM.path_of(S, f"{PTM.TOOLCHAIN}/lib/stray.pyc")):
        with open(_p, "wb") as fh:
            fh.write(b"\x00bytecode")
    git(S, *_stage)
    check("a planted .pyc under plugin/toolchain/lib leaves every check "
          "green, and the scans read it as bytecode, not as a stray",
          red(mismatches(S)) == []
          and PTM.toolchain_kind(f"{PTM.TOOLCHAIN}/lib/stray.pyc", S)
          == "cache"
          and PTM.toolchain_kind(
              f"{PTM.TOOLCHAIN}/lib/__pycache__/installer.cpython-314.pyc",
              S) == "cache",
          mismatches(S))

    _lib_copy = f"{PTM.TOOLCHAIN}/lib/minyaml.py"
    with open(PTM.path_of(S, _lib_copy), "a") as fh:
        fh.write("# drift\n")
    check("a changed byte in a copy turns only the bytes check red, and the "
          "scans read that copy as a stray",
          red(mismatches(S)) == ["bytes"]
          and PTM.toolchain_kind(_lib_copy, S) == "stray",
          mismatches(S))
    _bin_copy = f"{PTM.TOOLCHAIN}/bin/bootstrap-install"
    os.chmod(PTM.path_of(S, _bin_copy), 0o644)
    check("a cleared exec bit turns the mode check red",
          "mode" in red(mismatches(S)), mismatches(S))
    _stray = f"{PTM.TOOLCHAIN}/lib/extra.py"
    with open(PTM.path_of(S, _stray), "w") as fh:
        fh.write("x = 1\n")
    git(S, "add", _stray)
    check("a tracked file the map does not name turns the tracked check red",
          "tracked" in red(mismatches(S))
          and PTM.toolchain_kind(_stray, S) == "stray", mismatches(S))
    # The critic's design: a link to the source, whose bytes read equal.
    _linked = f"{PTM.TOOLCHAIN}/lib/defaults.py"
    os.unlink(PTM.path_of(S, _linked))
    os.symlink(os.path.join("..", "..", "..", "lib", "defaults.py"),
               PTM.path_of(S, _linked))
    check("a copy replaced by a symlink to its source turns the link check "
          "red, and the scans read it as a stray",
          "links" in red(mismatches(S))
          and PTM.toolchain_kind(_linked, S) == "stray", mismatches(S))

    _src_before = open(PTM.path_of(S, "lib/defaults.py"), "rb").read()
    _w, _r = sync(S)
    git(S, *_stage)
    check("--sync repairs all four, and the printed staging command stages "
          "the repair: it rewrites the changed copy, resets the mode, deletes "
          "the tracked stray and the bytecode, and replaces the link with a "
          "copy without writing through it to the source",
          red(mismatches(S)) == []
          and not os.path.exists(_cache)
          and not os.path.lexists(PTM.path_of(S, _stray))
          and not os.path.islink(PTM.path_of(S, _linked))
          and open(PTM.path_of(S, "lib/defaults.py"), "rb").read()
          == _src_before,
          (mismatches(S), _w, _r))
finally:
    shutil.rmtree(TMP, ignore_errors=True)


print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

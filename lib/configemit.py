"""
Dict -> bootstrap.config.yaml emitter, constrained to the exact YAML subset
that lib/minyaml.py can parse.

Why a bespoke emitter instead of a library: the rest of the package is
stdlib-only and the installer's parser is a deliberate subset. Emitting via
PyYAML would risk producing constructs minyaml rejects. Instead we emit only:

  * nested 2-space mappings
  * block lists of scalars
  * block lists of inline maps  ("- {k: v, k2: v2}")
  * scalars: bool / null / int / float / quoted strings

and we round-trip every emitted document back through minyaml in a test to
prove the contract holds.

Quoting rule: strings are ALWAYS double-quoted with internal quotes/backslashes
escaped. This is the single most important safety property - PRD-derived text
(principles, rationale, names) flows into the config, and unquoted emission
could let a stray ':' or '#' change the parse. Quoting everything makes the
emitter immune to PRD content.
"""

from __future__ import annotations


def _q(s: str, warnings: list[str], ctx: str) -> str:
    """Double-quote a string, keeping it inside minyaml's safe subset.

    minyaml's scalar reader strips a matched surrounding quote pair and does
    NOT process escapes, so an embedded double-quote or backslash would break
    the round-trip. We map `"`->`'` and `\\`->`/` to stay in the safe subset.

    minyaml is also strictly line-oriented: it splits the document on newlines
    BEFORE any quote handling, so a quoted scalar that itself contains a
    newline (or carriage return) is split across physical lines and the
    document fails to parse entirely - silently producing an invalid config
    (review finding R-2). A literal TAB inside a value is likewise dangerous
    because minyaml's indentation rule rejects tabs. Embedded control
    characters therefore cannot survive the round-trip under ANY quoting, so
    we fold every ASCII control char (incl. \\n \\r \\t) to a single space.

    Crucially every one of these substitutions is NOT silent: any value we
    had to alter is appended to `warnings` with its context so the caller can
    surface it to the human (who is reviewing the config anyway). This
    matches the package's fail-loud / "propose, never silently change" ethos
    - a sanitized principle or project name is shown, not quietly corrupted
    (review findings R-1 and R-2).
    """
    # 1. Control characters (newline/CR/tab/vertical-tab/formfeed/NUL/...)
    #    cannot round-trip through minyaml's line-oriented parser at all, so
    #    collapse runs of them to a single space rather than emit an
    #    unparseable document.
    no_ctrl = []
    prev_was_space = False
    stripped_ctrl = False
    for ch in s:
        if ch == "\t" or (ord(ch) < 0x20) or ord(ch) == 0x7F:
            stripped_ctrl = True
            if not prev_was_space:
                no_ctrl.append(" ")
                prev_was_space = True
            continue
        no_ctrl.append(ch)
        prev_was_space = ch == " "
    ctrl_safe = "".join(no_ctrl).strip()
    # 2. Characters minyaml's quoting subset cannot represent.
    safe = ctrl_safe.replace("\\", "/").replace('"', "'")
    if safe != s:
        detail = "control characters" if stripped_ctrl else "\" or \\"
        warnings.append(
            f"{ctx}: contained characters unsupported by the config parser "
            f"({detail}); emitted as {safe!r} instead of {s!r}. Edit the "
            f"config if this is wrong.")
    return '"' + safe + '"'


def _scalar(v, warnings: list[str], ctx: str) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return _q(str(v), warnings, ctx)


def _emit(obj, indent: int, lines: list[str],
          warnings: list[str], path: str) -> None:
    pad = " " * indent
    if isinstance(obj, dict):
        for k, v in obj.items():
            kp = f"{path}.{k}" if path else k
            if isinstance(v, dict):
                if not v:
                    lines.append(f"{pad}{k}: {{}}")
                else:
                    lines.append(f"{pad}{k}:")
                    _emit(v, indent + 2, lines, warnings, kp)
            elif isinstance(v, list):
                if not v:
                    lines.append(f"{pad}{k}: []")
                else:
                    lines.append(f"{pad}{k}:")
                    for idx, item in enumerate(v):
                        ip = f"{kp}[{idx}]"
                        if isinstance(item, dict):
                            inner = ", ".join(
                                f"{ik}: {_scalar(iv, warnings, ip)}"
                                for ik, iv in item.items())
                            lines.append(f"{pad}  - {{{inner}}}")
                        else:
                            lines.append(
                                f"{pad}  - {_scalar(item, warnings, ip)}")
            else:
                lines.append(f"{pad}{k}: {_scalar(v, warnings, kp)}")
    else:  # pragma: no cover - top level is always a mapping here
        raise TypeError("emit() expects a mapping at the top level")


def emit(cfg: dict, *, header: str | None = None,
         warnings: list[str] | None = None) -> str:
    """Serialize cfg to a minyaml-parseable YAML string.

    If `warnings` (a list) is passed, any value the emitter had to sanitize
    to stay within minyaml's subset is appended to it (review finding R-1:
    sanitization must be observable, not silent).
    """
    sink: list[str] = warnings if warnings is not None else []
    lines: list[str] = []
    if header:
        for hl in header.splitlines():
            lines.append(f"# {hl}" if hl else "#")
        lines.append("")
    _emit(cfg, 0, lines, sink, "")
    return "\n".join(lines) + "\n"

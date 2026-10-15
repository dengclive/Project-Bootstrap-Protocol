"""
Tiny YAML-subset parser (stdlib only).

Supports exactly what bootstrap.config.yaml needs:
  - nested mappings via 2-space indentation
  - block lists ("- scalar" / "- {inline: map}" / "- [inline, list]")
  - inline lists ("[a, b, c]") and inline maps ("{k: v}"), nested inside
    each other to any depth: "{ranked: [a, b]}" and "[{name: x}]" both parse
  - scalars: bool / null / int / float / quoted & unquoted strings
  - "# comments" and blank lines

Deliberately NOT general YAML. Unsupported constructs raise rather than guess,
so a malformed config fails loud instead of silently mis-parsing. Every error
is a YAMLError, which names the source line it was raised for.
"""

from __future__ import annotations


class YAMLError(ValueError):
    """A document this parser refuses.

    `line` is the 1-based source line, or None when no single line is to
    blame. A ValueError subclass, so every `except ValueError` caller keeps
    working, and str() keeps the "line N: ..." form the tab error always had.
    """

    def __init__(self, msg: str, line: int | None = None):
        super().__init__(f"line {line}: {msg}" if line else msg)
        self.msg = msg
        self.line = line


def _scalar(tok: str):
    tok = tok.strip()
    if tok in ("", "~") or tok.lower() == "null":
        return None
    if tok.lower() in ("true", "false"):
        return tok.lower() == "true"
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
        return tok[1:-1]
    for caster in (int, float):
        try:
            return caster(tok)
        except ValueError:
            pass
    return tok


_CLOSER = {"[": "]", "{": "}"}


def _opens_quote(s: str, i: int, sep: str) -> bool:
    """Whether the quote character at s[i] opens a quoted run for _split_top.

    24cd8a3's rule is kept: a quote opens a run that the next copy of the
    same character closes, so `-k "a, b"` and `--exclude='a,b'` stay one
    value. Two kinds of quote are apostrophes instead, and stay literal.
    One is a quote with no later partner, which never closes, so in 24cd8a3
    it swallowed the rest of the list (`[Don't guess, B]`). The other is a
    single quote whose run would cover a `sep`, when a letter or digit
    immediately precedes it or immediately follows its partner
    (`[Don't guess, B, users' data]`, `[users', 'B']`). A pair with no
    `sep` inside still pairs, as in 24cd8a3, so the `'` of `'em` closes the
    one in `Don't` instead of opening a run of its own:
    `[Don't use 'em, 'B']` stays two items.

    Known gaps, as in 24cd8a3: a single-quote pair with no letter or digit
    outside it still spans a `sep` (`[Ship 'em fast, Keep users' trust]` is
    one item), and a double-quote pair always does (`[12" pizza, 3" sub]`).
    Keeping a glued delimiter such as `cut -d','` whole, as 24cd8a3 did, was
    measured in review and rejected: it merged `[users', '.env']` and
    refused `[{name: users'}, '.env']`, both of which PyYAML reads."""
    ch = s[i]
    j = s.find(ch, i + 1)
    if j < 0:
        return False
    if ch == "'" and (s[i - 1:i].isalnum() or s[j + 1:j + 2].isalnum()):
        return sep not in s[i + 1:j]
    return True


def _split_top(s: str, sep: str) -> list[str]:
    out, stack, buf, q = [], [], [], None
    for i, ch in enumerate(s):
        if q:
            buf.append(ch)
            if ch == q:
                q = None
        elif ch in ("'", '"') and _opens_quote(s, i, sep):
            q = ch
            buf.append(ch)
        elif ch in "[{":
            stack.append(_CLOSER[ch])
            buf.append(ch)
        elif ch in "]}":
            if not stack or stack.pop() != ch:
                raise YAMLError(f"unmatched {ch!r} in {s.strip()!r}")
            buf.append(ch)
        elif ch == sep and not stack:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if stack:
        raise YAMLError(f"missing {stack[-1]!r} in {s.strip()!r}")
    out.append("".join(buf))
    return out


def _flow_value(tok: str):
    """One value: an inline list, an inline map (either nested to any
    depth), or a scalar."""
    tok = tok.strip()
    if tok.startswith("["):
        return _inline_list(tok)
    if tok.startswith("{"):
        return _inline_map(tok)
    return _scalar(tok)


def _closed(tok: str, opener: str) -> str:
    """Return the text between the brackets of a one-line inline list or
    map, refusing one that does not end with its closing bracket."""
    closer = _CLOSER[opener]
    if not tok.endswith(closer):
        raise YAMLError(
            f"inline {'list' if opener == '[' else 'map'} {tok!r} must end "
            f"with {closer!r} on the same line. If it is a plain string, "
            f"put it in quotes.")
    return tok[1:-1]


def _inline_map(tok: str) -> dict:
    out = {}
    for part in _split_top(_closed(tok.strip(), "{"), ","):
        if not part.strip():
            continue
        k, _, v = part.partition(":")
        out[k.strip()] = _flow_value(v)
    return out


def _inline_list(tok: str) -> list:
    inner = _closed(tok.strip(), "[")
    return [_flow_value(x) for x in _split_top(inner, ",") if x.strip() != ""]


def _value(tok: str, lineno: int):
    """A value written on a block line, with any error pinned to that line."""
    try:
        return _flow_value(tok)
    except YAMLError as exc:
        raise YAMLError(exc.msg, lineno) from None


def _strip_comment(line: str) -> str:
    """Drop a trailing `# comment`, keeping any `#` inside quotes.

    A quote opens a quoted run only when the same quote character appears
    again later on the line, which is exactly where 24cd8a3's rule (every
    quote toggles) closed its runs, so every such line strips as it did
    there: `--grep="#smoke"` keeps its `#`. A quote that never closes is an
    apostrophe, not a quote. 24cd8a3 let it hide the rest of the line, so
    `[Don't guess, B]  # note` kept its comment. After one, a `#` starts a
    comment only after whitespace, YAML's rule for a plain scalar, so
    `Don't#x` stays whole. Known gap, as in 24cd8a3: a second apostrophe
    later on the line closes the first, so `Don't panic  # it's` keeps its
    comment."""
    q, bare = None, False
    last = {"'": line.rfind("'"), '"': line.rfind('"')}
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            if last[ch] > i:
                q = ch
            else:
                bare = True
        elif ch == "#" and (not bare or i == 0 or line[i - 1].isspace()):
            return line[:i]
    return line


def _tokenize(text: str) -> list[tuple[int, str, int]]:
    rows = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        raw = _strip_comment(raw)
        if raw.strip() == "":
            continue
        leading = raw[:len(raw) - len(raw.lstrip())]
        if "\t" in leading:
            raise YAMLError(
                "tab character in indentation. Use spaces "
                "(2-space indent). Tabs are rejected rather than guessed.",
                lineno)
        indent = len(raw) - len(raw.lstrip(" "))
        rows.append((indent, raw.strip(), lineno))
    return rows


class _Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.i = 0

    def peek(self):
        return self.rows[self.i] if self.i < len(self.rows) else None

    def next(self):
        row = self.rows[self.i]
        self.i += 1
        return row


def _parse_block(cur, indent):
    first = cur.peek()
    if first is None or first[0] < indent:
        return {}
    if first[1].startswith("- "):
        return _parse_list(cur, indent)
    return _parse_map(cur, indent)


def _parse_map(cur, indent):
    out = {}
    while True:
        row = cur.peek()
        if row is None or row[0] < indent:
            break
        if row[0] != indent:
            raise YAMLError(
                f"bad indentation near {row[1]!r}: expected {indent} "
                f"spaces, found {row[0]}", row[2])
        cur.next()
        body = row[1]
        if ":" not in body:
            raise YAMLError(f"expected 'key: value', got {body!r}", row[2])
        key, _, val = body.partition(":")
        key, val = key.strip(), val.strip()
        child = cur.peek()
        if val == "":
            if child is not None and child[0] > indent:
                out[key] = _parse_block(cur, child[0])
            else:
                out[key] = {}
            continue
        out[key] = _value(val, row[2])
        # An indented line under a key that already has a value is always
        # an error; say why here instead of "bad indentation" one level up.
        if child is not None and child[0] > indent:
            if val.rstrip("+-0123456789") in ("|", ">"):
                raise YAMLError(
                    f"{key!r} uses a multi-line string ({val!r}), which "
                    f"this parser does not support. Write the value on one "
                    f"line, in quotes.", row[2])
            raise YAMLError(
                f"{child[1]!r} is indented {child[0]} spaces, deeper than "
                f"{key!r} ({indent}) above it, which already has a value. "
                f"Keys at the same level must line up.", child[2])
    return out


def _parse_list(cur, indent):
    out = []
    while True:
        row = cur.peek()
        if row is None or row[0] < indent or not row[1].startswith("- "):
            break
        if row[0] != indent:
            raise YAMLError(
                f"bad list indentation near {row[1]!r}: expected {indent} "
                f"spaces, found {row[0]}", row[2])
        cur.next()
        out.append(_value(row[1][2:], row[2]))
        child = cur.peek()
        if child is not None and child[0] > indent \
                and not child[1].startswith("- "):
            raise YAMLError(
                f"{child[1]!r} continues the list item above it, and a list "
                f"item must fit on one line here. Write a list of maps as "
                f"'- {{name: x, command: y}}', one item per line.", child[2])
    return out


def key_line(text: str, path: tuple[str, ...]) -> int | None:
    """[WP1] The 1-based source line of the block-style key `path`, such as
    ("deps", "enabled"), for an error message that names file and line.

    When the last key is written inline (`deps: {enabled: x}`) the line of
    the deepest key found is returned; None when not even the first is
    found, or the text does not tokenize. It never changes what load_yaml
    returns."""
    try:
        rows = _tokenize(text)
    except YAMLError:
        return None
    start, end, line = 0, len(rows), None
    for key in path:
        found = None
        level = rows[start][0] if start < end else None
        for i in range(start, end):
            indent, body, _ = rows[i]
            if indent < level:
                break
            if indent == level and ":" in body \
                    and body.partition(":")[0].strip() == key:
                found = i
                break
        if found is None:
            return line
        line = rows[found][2]
        start = stop = found + 1
        while stop < end and rows[stop][0] > level:
            stop += 1
        end = stop
    return line


def load_yaml(text: str) -> dict:
    cur = _Cursor(_tokenize(text))
    if cur.peek() is None:
        return {}
    try:
        result = _parse_block(cur, cur.peek()[0])
    except RecursionError:
        # Inline lists and maps, or block indentation, nested some 500
        # levels deep run out of stack. RecursionError is not a ValueError,
        # so without this it escaped the installer as a traceback. The row
        # last read is the one that went too deep.
        raise YAMLError("the config nests too deeply",
                        cur.rows[max(cur.i - 1, 0)][2]) from None
    if cur.peek() is not None:
        row = cur.peek()
        raise YAMLError(f"unparsed trailing content: {row[1]!r}", row[2])
    return result if isinstance(result, dict) else {"_root": result}

"""
Tiny YAML-subset parser (stdlib only).

Supports exactly what bootstrap.config.yaml needs:
  - nested mappings via 2-space indentation
  - block lists ("- scalar" / "- {inline: map}")
  - inline lists ("[a, b, c]") and inline maps via "- {k: v}"
  - scalars: bool / null / int / float / quoted & unquoted strings
  - "# comments" and blank lines

Deliberately NOT general YAML. Unsupported constructs raise rather than guess,
so a malformed config fails loud instead of silently mis-parsing.
"""

from __future__ import annotations


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


def _split_top(s: str, sep: str) -> list[str]:
    out, depth, buf, q = [], 0, [], None
    for ch in s:
        if q:
            buf.append(ch)
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            q = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            buf.append(ch)
        elif ch == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return out


def _inline_map(tok: str) -> dict:
    tok = tok.strip()
    if tok.startswith("{"):
        tok = tok[1:]
    if tok.endswith("}"):
        tok = tok[:-1]
    out = {}
    for part in _split_top(tok, ","):
        if not part.strip():
            continue
        k, _, v = part.partition(":")
        out[k.strip()] = _scalar(v)
    return out


def _inline_list(tok: str) -> list:
    inner = tok.strip()[1:-1]
    return [_scalar(x) for x in _split_top(inner, ",") if x.strip() != ""]


def _strip_comment(line: str) -> str:
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            q = ch
        elif ch == "#":
            return line[:i]
    return line


def _tokenize(text: str) -> list[tuple[int, str]]:
    rows = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        raw = _strip_comment(raw)
        if raw.strip() == "":
            continue
        leading = raw[:len(raw) - len(raw.lstrip())]
        if "\t" in leading:
            raise ValueError(
                f"line {lineno}: tab character in indentation. Use spaces "
                f"(2-space indent). Tabs are rejected rather than guessed.")
        indent = len(raw) - len(raw.lstrip(" "))
        rows.append((indent, raw.strip()))
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
            raise ValueError(f"bad indentation near: {row[1]!r}")
        cur.next()
        body = row[1]
        if ":" not in body:
            raise ValueError(f"expected 'key: ...' got {body!r}")
        key, _, val = body.partition(":")
        key, val = key.strip(), val.strip()
        if val == "":
            child = cur.peek()
            if child is not None and child[0] > indent:
                out[key] = _parse_block(cur, child[0])
            else:
                out[key] = {}
        elif val == "[]":
            out[key] = []
        elif val == "{}":
            out[key] = {}
        elif val.startswith("["):
            out[key] = _inline_list(val)
        elif val.startswith("{"):
            out[key] = _inline_map(val)
        else:
            out[key] = _scalar(val)
    return out


def _parse_list(cur, indent):
    out = []
    while True:
        row = cur.peek()
        if row is None or row[0] < indent or not row[1].startswith("- "):
            break
        if row[0] != indent:
            raise ValueError(f"bad list indentation near: {row[1]!r}")
        cur.next()
        item = row[1][2:].strip()
        if item.startswith("{"):
            out.append(_inline_map(item))
        elif item.startswith("["):
            out.append(_inline_list(item))
        else:
            out.append(_scalar(item))
    return out


def load_yaml(text: str) -> dict:
    cur = _Cursor(_tokenize(text))
    if cur.peek() is None:
        return {}
    result = _parse_block(cur, cur.peek()[0])
    if cur.peek() is not None:
        raise ValueError(f"unparsed trailing content: {cur.peek()[1]!r}")
    return result if isinstance(result, dict) else {"_root": result}

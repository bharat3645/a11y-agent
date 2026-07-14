"""Lightweight tag/attribute extractor for HTML, JSX and TSX source.

This is intentionally NOT a full HTML5 or JSX/Babel AST parser. It is a
regex-based heuristic extractor good enough to answer the narrow questions
the rules in this project need ("what is the alt attribute of this img",
"what is the visible text of this anchor", "what heading levels appear in
this file, in order"). It will get confused by:

  * Deeply nested elements of the *same* tag name inside each other
    (e.g. an <a> inside an <a>, which is invalid HTML anyway).
  * JSX expressions used as attribute values that themselves contain the
    characters '{' '}' in unbalanced ways, e.g. `alt={cond ? "{}" : "x"}`.
  * Tags split across template-literal interpolations.
  * Conditionally-rendered JSX (`{cond && <img ... />}`) — the extractor
    doesn't understand control flow, it just finds every tag-shaped string.

These limitations are called out again in the README. For the purposes of
a heuristic *smell* scanner (not a compiler), "mostly right, occasionally
noisy" is an acceptable trade-off; every rule is designed to be a hint for
a human reviewer, not an authoritative verdict.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


ATTR_PATTERN = re.compile(
    r"""
    ([a-zA-Z_:][-\w:.]*)          # attribute name
    (?:
        \s*=\s*
        (?:
            "([^"]*)"              # double-quoted value
            |'([^']*)'             # single-quoted value
            |\{([^{}]*)\}          # JSX expression value (no nested braces)
        )
    )?
    """,
    re.VERBOSE,
)


@dataclass
class Element:
    tag: str
    attrs: Dict[str, str]
    line: int
    raw: str
    inner_html: Optional[str] = None

    @property
    def text(self) -> str:
        """Visible text of the element with any nested tags stripped."""
        if self.inner_html is None:
            return ""
        return strip_tags(self.inner_html)


def line_index(text: str):
    """Return a function mapping character offset -> 1-indexed line number."""
    newline_offsets = [i for i, c in enumerate(text) if c == "\n"]

    def offset_to_line(offset: int) -> int:
        line = 1
        for no in newline_offsets:
            if no < offset:
                line += 1
            else:
                break
        return line

    return offset_to_line


def parse_attrs(attr_string: str) -> Dict[str, str]:
    """Parse an HTML/JSX attribute string into a dict.

    Boolean/valueless attributes (e.g. `disabled`) are stored with value
    "" (so callers can still test for their presence via `in attrs`).
    JSX expression values (`foo={bar}`) are stored as their raw source text,
    e.g. `alt={imageAlt}` -> attrs["alt"] == "{imageAlt}" so downstream
    rules can detect "this is a dynamic value, not a literal string" and
    treat it conservatively.
    """
    attrs: Dict[str, str] = {}
    for match in ATTR_PATTERN.finditer(attr_string):
        name, dq, sq, expr = match.groups()
        if dq is not None:
            attrs[name] = dq
        elif sq is not None:
            attrs[name] = sq
        elif expr is not None:
            attrs[name] = "{" + expr + "}"
        else:
            attrs[name] = ""
    return attrs


def strip_tags(html: str) -> str:
    """Remove tags from an HTML/JSX fragment and collapse whitespace."""
    text = re.sub(r"<[^>]*>", " ", html)
    # collapse JSX expression braces used purely for whitespace/text, e.g. {' '}
    text = re.sub(r"\{[^{}]*\}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_self_closing(text: str, tag: str) -> List[Element]:
    """Find void/self-closing style elements, e.g. <img ... /> or <img ...>."""
    pattern = re.compile(
        r"<" + re.escape(tag) + r"(?![-\w])([^>]*?)/?>",
        re.IGNORECASE,
    )
    offset_to_line = line_index(text)
    elements = []
    for m in pattern.finditer(text):
        attrs = parse_attrs(m.group(1))
        elements.append(
            Element(tag=tag, attrs=attrs, line=offset_to_line(m.start()), raw=m.group(0))
        )
    return elements


def find_with_content(text: str, tag: str) -> List[Element]:
    """Find elements that have an opening tag, inner content, and a closing tag."""
    pattern = re.compile(
        r"<" + re.escape(tag) + r"(?![-\w])([^>]*)>(.*?)</" + re.escape(tag) + r"\s*>",
        re.IGNORECASE | re.DOTALL,
    )
    offset_to_line = line_index(text)
    elements = []
    for m in pattern.finditer(text):
        attrs = parse_attrs(m.group(1))
        elements.append(
            Element(
                tag=tag,
                attrs=attrs,
                line=offset_to_line(m.start()),
                raw=m.group(0),
                inner_html=m.group(2),
            )
        )
    return elements


def find_headings(text: str) -> List[Element]:
    """Find h1-h6 elements in document order."""
    pattern = re.compile(r"<h([1-6])(?![-\w])([^>]*)>(.*?)</h\1\s*>", re.IGNORECASE | re.DOTALL)
    offset_to_line = line_index(text)
    elements = []
    for m in pattern.finditer(text):
        level = int(m.group(1))
        attrs = parse_attrs(m.group(2))
        elements.append(
            Element(
                tag=f"h{level}",
                attrs=attrs,
                line=offset_to_line(m.start()),
                raw=m.group(0),
                inner_html=m.group(3),
            )
        )
    # sort by position of appearance (finditer already yields in order for a
    # single pattern, but we build one Element per (start) so this is a no-op
    # safety net for clarity).
    return elements


def get_line_snippet(text: str, line: int) -> str:
    lines = text.splitlines()
    if 1 <= line <= len(lines):
        return lines[line - 1].strip()
    return ""

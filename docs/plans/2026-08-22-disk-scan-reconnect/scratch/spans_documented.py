"""Byte-span transplantation: the second write mechanism (DL-007).

apply_text_patches (textpatch.py) substitutes attribute values inside opening
tags it locates by scanning for LOCATION and PRIMARYKEY, and has no concept
of element extent. Inserting or dropping whole ENTRY and NODE subtrees
through it would mean either bolting structural editing onto an attribute
substituter or falling back to ET.tostring, which reformats the document and
loses the byte fidelity the tool exists to protect. This module locates each
element's full opening-to-closing byte range with a depth-aware scanner, and
OutputBuilder assembles output by concatenating verbatim source spans plus
re-serialised fragments only where a rename or redirect actually changes
bytes. splice.py and split.py use only this mechanism; reconnect.py and
rewrite.py use only textpatch.py - the two write paths never mix within one
command.
# The scanner below treats comments, CDATA sections and processing
# instructions as opaque tokens specifically so a literal '<' or '>'
# permitted inside one of them never desynchronises the depth count
# element_span relies on (DL-007).

# The NML schema this module assembles output for is confirmed only
# against VERSION=20 / Traktor Pro 4. recalculate_count_attr is generic
# over any counted container rather than hardcoded to
# COLLECTION/PLAYLIST/SUBNODES, so a counted container this tool has not
# seen - from a schema version not yet verified - is still recalculated
# instead of being silently left stale.

"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# The attribute-list group treats a quoted value as one opaque unit (via the
# quoted alternatives) rather than stopping at the first '>' or '/' inside
# it: XML permits a literal '>' unescaped inside a quoted attribute value, and
# a value legitimately ending in '/' must not be mistaken for the self-closing
# marker, which only the final, unquoted (/?) before '>' may capture.
_ATTRS = r'(?:[^>"\'/]|"[^"]*"|\'[^\']*\'|/(?!>))*'
_TOKEN_RE = re.compile(
    r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<(/?)([A-Za-z_][\w:.-]*)(" + _ATTRS + r")(/?)>",
    re.DOTALL,
)


@dataclass(frozen=True)
class Span:
    start: int
    end: int  # exclusive

    def text(self, source: str) -> str:
        return source[self.start:self.end]


def element_span(source: str, open_lt_pos: int) -> Span:
    """Return the byte range of the element whose opening tag starts at
    open_lt_pos, from '<' through the end of its closing tag (or its own
    tag, if self-closing). Comment, CDATA and processing-instruction regions
    are skipped by construction (via _TOKEN_RE) so tag-like text inside them
    never terminates the scan early or is mistaken for a nested element.
    Nesting depth is tracked by tag name, so a same-named descendant does
    not end the scan prematurely; the outermost requested extent always
    wins.
    """
    match_at_start = _TOKEN_RE.match(source, open_lt_pos)
    if match_at_start is None or match_at_start.group(2) is None:
        raise ValueError(f"no element opening tag at offset {open_lt_pos}")
    tag_name = match_at_start.group(2)
    is_self_closing = bool(match_at_start.group(4))
    if is_self_closing:
        return Span(open_lt_pos, match_at_start.end())

    depth = 1
    pos = match_at_start.end()
    for token in _TOKEN_RE.finditer(source, pos):
        if token.group(2) != tag_name:
            continue
        is_close = bool(token.group(1))
        self_closing = bool(token.group(4))
        if self_closing:
            continue
        if is_close:
            depth -= 1
            if depth == 0:
                return Span(open_lt_pos, token.end())
        else:
            depth += 1

    raise ValueError(f"unclosed element {tag_name!r} starting at offset {open_lt_pos}")


def find_element_span(source: str, tag_name: str, start_from: int = 0) -> Optional[Span]:
    """Locate the next top-level occurrence of tag_name at or after
    start_from and return its full span."""
    idx = source.find(f"<{tag_name}", start_from)
    while idx != -1:
        # Guard against a longer tag name sharing this prefix (e.g. NODE vs NODENAME).
        following = source[idx + 1 + len(tag_name): idx + 2 + len(tag_name)]
        if following and following not in (" ", "\t", "\n", "\r", ">", "/"):
            idx = source.find(f"<{tag_name}", idx + 1)
            continue
        return element_span(source, idx)
    return None


def element_span_by_identity(source: str, root, element) -> Span:
    """Locate element's span by its position among same-tag elements in
    document order, rather than searching source text for one of its
    attribute values (breaks on duplicate values across the document - e.g.
    two ENTRY elements sharing a FILE basename, very common across a real
    corpus - and on XML-escaped characters, since the parsed attribute value
    is unescaped text while the source bytes are not) or by source line
    (unreliable whenever more than one element shares a line, as in a
    compact/minified document with no inter-tag whitespace).

    root.iter(tag) walks the parsed tree in the same pre-order every parser
    produces from a well-formed document, which is exactly the left-to-right
    order that tag's opening tags appear in source - so the Nth element of
    that tag in the tree is unambiguously the Nth "<tag" occurrence in text,
    independent of attribute values or line boundaries.
    """
    tag_name = element.tag
    target_index = next((i for i, el in enumerate(root.iter(tag_name)) if el is element), None)
    if target_index is None:
        raise ValueError(f"element <{tag_name}> is not part of the given root's tree")

    idx = -1
    for _ in range(target_index + 1):
        idx = source.find(f"<{tag_name}", idx + 1)
        while idx != -1:
            # Guard against a longer tag name sharing this prefix (e.g. NODE vs NODENAME).
            following = source[idx + 1 + len(tag_name): idx + 2 + len(tag_name)]
            if following and following not in (" ", "\t", "\n", "\r", ">", "/"):
                idx = source.find(f"<{tag_name}", idx + 1)
                continue
            break
        if idx < 0:
            raise ValueError(f"could not locate occurrence {target_index} of <{tag_name}> in source text")
    return element_span(source, idx)
        """Append text with no patching or re-serialisation - used for
        the untouched bytes surrounding every span this builder
        assembles."""


        """Copy span's source bytes verbatim, patching only the
        attributes named in attr_patches on its own opening tag (e.g. a
        PRIMARYKEY redirect) via the same substitution primitive
        textpatch.py uses."""
class OutputBuilder:
    """Assembles an output document from verbatim source spans and
    re-serialised fragments, applying attribute patches to the spans it
    copies and recalculating COLLECTION/PLAYLIST/SUBNODES count attributes
    from what was actually assembled. Returns the complete byte string
    without touching the filesystem, so callers can validate before any
    file handle opens (DL-012).
    """

    def __init__(self) -> None:
        self._pieces: list[str] = []

    def add_verbatim(self, text: str) -> None:
        self._pieces.append(text)

    def add_span(self, source: str, span: Span, attr_patches: dict[str, str] | None = None) -> None:
        text = span.text(source)
        if attr_patches:
            text = _patch_opening_tag_attrs(text, attr_patches)
        self._pieces.append(text)

    def add_serialized(self, fragment: str) -> None:
        self._pieces.append(fragment)

    def add_counted_span(
        self,
        source: str,
        span: Span,
        tag_name: str,
        count_attr: str,
        children: list[str],
        attr_patches: dict[str, str] | None = None,
        count: int | None = None,
    ) -> None:
        """Copy span verbatim with children spliced in just before its
        closing tag, recalculating count_attr on tag_name's own opening tag
        to the count this class actually assembled - len(children) by
        default, or the explicit count override for a container (e.g.
        splice's root SUBNODES) whose existing children are kept verbatim
        inside span itself rather than passed again here."""
        text = span.text(source)
        if attr_patches:
            text = _patch_opening_tag_attrs(text, attr_patches)
        text = recalculate_count_attr(text, tag_name, count_attr, len(children) if count is None else count)
        insert_at = len(text) - len(f"</{tag_name}>")
        self._pieces.append(text[:insert_at] + "".join(children) + text[insert_at:])

    def build(self) -> str:
        return "".join(self._pieces)


def _patch_opening_tag_attrs(fragment: str, attr_patches: dict[str, str]) -> str:
    """Substitute attribute values in fragment's own opening tag only
    (never inside descendant tags with the same attribute name)."""
    close = fragment.find(">")
    if close < 0:
        return fragment
    opening = fragment[: close + 1]
    rest = fragment[close + 1:]
    for attr, new_value in attr_patches.items():
        pattern = re.compile(r"(\b" + re.escape(attr) + r'\s*=\s*)(["\'])(.*?)\2', re.DOTALL)
        opening = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}{new_value}{m.group(2)}", opening, count=1)
    return opening + rest


def recalculate_count_attr(fragment: str, tag_name: str, count_attr: str, actual_count: int) -> str:
    """Rewrite tag_name's count_attr to actual_count in fragment's own
    opening tag. Generic over any counted container (COLLECTION ENTRIES,
    PLAYLIST ENTRIES, SUBNODES COUNT, or any future counted tag) rather than
    a fixed tag list: the schema is confirmed only against NML VERSION=20 /
    Traktor Pro 4, so a counted container introduced by a later schema
    version is still recalculated correctly instead of silently left stale
    or requiring this function to be extended for every new tag name.
    """
    close = fragment.find(">")
    opening = fragment[: close + 1] if close >= 0 else fragment
    rest = fragment[close + 1:] if close >= 0 else ""
    pattern = re.compile(r"(\b" + re.escape(count_attr) + r'\s*=\s*)(["\'])(\d*)\2')
    if pattern.search(opening):
        opening = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}{actual_count}{m.group(2)}", opening, count=1)
    return opening + rest

"""Byte-preserving attribute substitution over LOCATION and PRIMARYKEY tags.

Two write paths exist because they have fundamentally different fidelity
guarantees for Traktor NML files.

lxml path (default when lxml is installed):
  The source file is read as raw bytes. lxml parses it and records the
  source-line number of every element. Only the attribute values that need
  changing are substituted in the original text; everything else -
  whitespace, indentation, attribute order, empty-element form
  (<HEAD ...></HEAD>), the standalone="no" declaration - is preserved
  byte-for-byte.

stdlib fallback (when lxml is absent):
  The tree is mutated in-place and written back via ET.tostring. This does
  not preserve whitespace, attribute order or the standalone="no" form, but
  is functionally correct for path substitution.

The lxml path is preferred. Do not remove it to simplify the code without
understanding that the stdlib path will silently change the file's
formatting. This module implements only attribute substitution; it has no
concept of element extent and must not be extended to insert or remove whole
elements (splice/split use spans.py instead - see its module docstring).

patch_entry_attributes is the module's second write path. Its unit is one
ENTRY element's span text rather than a whole document, so every substitution
and every insertion it makes is bounded by the span it is handed. That bound
is what lets it write a missing ALBUM or INFO child into the entry: the
no-element-insertion rule above is a property of apply_text_patches' scan,
which matches a locator anywhere in the file and has no notion of where one
element ends and the next begins.
"""

from __future__ import annotations

import html
import re

from .model import ElemPatch


def _xml_escape_attr(value: str) -> str:
    """Escape a replacement value the same way lxml/ET escape attribute
    text on serialisation, so a substituted value stays valid XML without
    ever re-running a full serialiser over the untouched surrounding text."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace('"', "&quot;")
        .replace("\t", "&#x9;")
        .replace("\n", "&#xA;")
        .replace("\r", "&#xD;")
    )


def _find_opening_tag_end(text: str, lt_pos: int) -> int:
    # Assumption: Traktor NML files always place each element's opening tag
    # entirely on one line - no multi-line attribute values. If that
    # assumption is violated, this function will scan past the intended line
    # boundary. apply_text_patches verifies the tag name before patching,
    # which catches the most obvious mismatches.
    i = lt_pos + 1
    while i < len(text):
        c = text[i]
        if c in ('"', "'"):
            q = c
            i += 1
            while i < len(text) and text[i] != q:
                i += 1
        elif c == '>':
            return i
        i += 1
    raise ValueError(f"unclosed opening tag at offset {lt_pos}")


def _patch_attr_in_tag(tag_text: str, attr_name: str, old_value: str, new_value: str) -> tuple[str, bool]:
    pattern = re.compile(r"(\b" + re.escape(attr_name) + r"\s*=\s*)([\"'])(.*?)\2", re.DOTALL)
    changed = False

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        if html.unescape(match.group(3)) != old_value:
            return match.group(0)
        quote = match.group(2)
        escaped = _xml_escape_attr(new_value)
        if quote == "'":
            escaped = escaped.replace("'", "&apos;")
        changed = True
        return f"{match.group(1)}{quote}{escaped}{quote}"

    return pattern.sub(replace, tag_text, count=1), changed


def _tag_attributes(tag_text: str) -> dict[str, str]:
    attr_re = re.compile(r'''\b([A-Za-z_:][\w:.-]*)\s*=\s*(["'])(.*?)\2''', re.DOTALL)
    return {match.group(1): html.unescape(match.group(3)) for match in attr_re.finditer(tag_text)}


def apply_text_patches(text: str, patches: list[ElemPatch]) -> str:
    """Apply attribute edits while retaining every other source byte.

    Patches are located from their original attributes, not XML parser line
    numbers. libxml2 line metadata can be unreliable in large NML files and
    is therefore deliberately not used for writing.
    """
    if not patches:
        return text

    patch_map: dict[tuple[str, tuple[tuple[str, str], ...]], ElemPatch] = {}
    for patch in patches:
        key = (patch.tag_name, patch.locator)
        existing = patch_map.get(key)
        if existing is not None and existing.changes != patch.changes:
            raise ValueError(f"conflicting text patches for {patch.tag_name} {patch.locator}")
        patch_map[key] = patch

    matched: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    result: list[str] = []
    cursor = 0
    tag_start_re = re.compile(r"<(LOCATION|PRIMARYKEY)\b")

    for match in tag_start_re.finditer(text):
        start = match.start()
        if start < cursor:
            continue
        end = _find_opening_tag_end(text, start) + 1
        tag_text = text[start:end]
        attrs = _tag_attributes(tag_text)
        tag_name = match.group(1)

        matching_key = next(
            (
                key
                for key in patch_map
                if key[0] == tag_name and all(attrs.get(name) == value for name, value in key[1])
            ),
            None,
        )
        if matching_key is None:
            continue

        patch = patch_map[matching_key]
        new_tag = tag_text
        for attr_name, old_value, new_value in patch.changes:
            new_tag, changed = _patch_attr_in_tag(new_tag, attr_name, old_value, new_value)
            if not changed:
                raise ValueError(f"could not locate {attr_name}={old_value!r} in {tag_name} {patch.locator}")

        result.extend((text[cursor:start], new_tag))
        cursor = end
        matched.add(matching_key)

    missing = set(patch_map) - matched
    if missing:
        tag_name, locator = next(iter(missing))
        raise ValueError(f"could not locate {tag_name} with original attributes {locator}")

    result.append(text[cursor:])
    return "".join(result)


def location_patch(elem, old, changes: list[tuple[str, str, str]]) -> ElemPatch:
    return ElemPatch(
        elem.sourceline,
        "LOCATION",
        (("VOLUME", old.volume), ("DIR", old.dir_value), ("FILE", old.file_name)),
        changes,
    )


def primarykey_patch(elem, old_key: str, new_key: str) -> ElemPatch:
    return ElemPatch(elem.sourceline, "PRIMARYKEY", (("KEY", old_key),), [("KEY", old_key, new_key)])


_ENTRY_CHILD_ORDER = ("LOCATION", "ALBUM", "MODIFICATION_INFO", "INFO")

# The tracked-attribute vocabulary of splice._TRACKED_ATTRS mapped to the tag
# that carries each one and the attribute name on that tag. ARTIST and TITLE
# sit on the ENTRY opening tag itself; the rest sit on a child element.
_ENTRY_CARRIERS: dict[str, tuple[str, str]] = {
    "artist": ("ENTRY", "ARTIST"),
    "title": ("ENTRY", "TITLE"),
    "album": ("ALBUM", "TITLE"),
    "filesize": ("INFO", "FILESIZE"),
    "playtime_float": ("INFO", "PLAYTIME_FLOAT"),
    "bitrate": ("INFO", "BITRATE"),
}

# The tags _ENTRY_CARRIERS names, deduplicated and ordered so an insertion
# reaches its anchor before a later carrier is written. Derived from the
# carrier table rather than listed again, so a tracked attribute cannot name
# a tag patch_entry_attributes skips; LOCATION and MODIFICATION_INFO carry no
# tracked attribute and are anchors only.
_CARRIER_TAGS = ("ENTRY",) + tuple(
    tag for tag in _ENTRY_CHILD_ORDER if tag in {c for c, _ in _ENTRY_CARRIERS.values()}
)


def _find_tag_start(span: str, tag_name: str) -> int | None:
    match = re.search(r"<" + re.escape(tag_name) + r"(?=[\s/>])", span)
    return None if match is None else match.start()


def _element_end(span: str, start: int, tag_name: str) -> int:
    """Offset one past the last byte of the element opening at ``start``.

    ENTRY's children carry no children of their own, so a close tag search
    needs no depth counter; a self-closed opening tag ends at its own '>'."""
    open_end = _find_opening_tag_end(span, start)
    if span[open_end - 1] == "/":
        return open_end + 1
    close = span.index("</" + tag_name, open_end)
    return _find_opening_tag_end(span, close) + 1


def _set_attr_in_tag(tag_text: str, attr_name: str, value: str) -> str:
    """Return ``tag_text`` carrying ``attr_name=value``.

    An attribute the tag already holds keeps its own quote character and its
    position among the tag's attributes; one the tag lacks is written in
    ahead of the tag's closing angle bracket."""
    pattern = re.compile(r"(\b" + re.escape(attr_name) + r"\s*=\s*)([\"'])(.*?)\2", re.DOTALL)

    def replace(match: re.Match[str]) -> str:
        quote = match.group(2)
        escaped = _xml_escape_attr(value)
        if quote == "'":
            escaped = escaped.replace("'", "&apos;")
        return f"{match.group(1)}{quote}{escaped}{quote}"

    patched, count = pattern.subn(replace, tag_text, count=1)
    if count:
        return patched
    body = tag_text[1:-1].rstrip("/").rstrip()
    tail = "/>" if tag_text.endswith("/>") else ">"
    return f'<{body} {attr_name}="{_xml_escape_attr(value)}"{tail}'


def _insert_child(span: str, tag_name: str) -> str:
    """Write an empty ``tag_name`` child into the ENTRY span, for the caller's
    own loop to write attributes into, placed by _ENTRY_CHILD_ORDER: immediately after the last child
    present that precedes ``tag_name`` in that order. That anchor always
    resolves, because collection_records skips an entry with no LOCATION child
    and LOCATION precedes both insertable tags.

    The insertion composes no whitespace of its own. The whitespace byte run
    that follows the anchor - the run that indents the anchor's following
    sibling - is copied verbatim ahead of the new child, so the child carries
    its siblings' indentation and its file's line terminator, and an entry
    written on one line gains no line."""
    order = _ENTRY_CHILD_ORDER[: _ENTRY_CHILD_ORDER.index(tag_name)]
    anchor_end = None
    for candidate in order:
        start = _find_tag_start(span, candidate)
        if start is not None:
            anchor_end = _element_end(span, start, candidate)
    if anchor_end is None:
        raise ValueError(f"no anchor child precedes {tag_name} in the entry span")

    run_end = anchor_end
    while run_end < len(span) and span[run_end].isspace():
        run_end += 1
    whitespace = span[anchor_end:run_end]
    child = f"<{tag_name}></{tag_name}>"
    return span[:anchor_end] + whitespace + child + span[anchor_end:]


def patch_entry_attributes(span: str, values: dict[str, str]) -> str:
    """Return one ENTRY element's span text carrying ``values``.

    ``values`` is keyed by the tracked-attribute vocabulary artist, title,
    album, filesize, playtime_float and bitrate. Each name's carrier is read
    from _ENTRY_CARRIERS: artist and title land on the ENTRY opening tag,
    album on the TITLE attribute of its ALBUM child, and filesize,
    playtime_float and bitrate on its INFO child.

    Where the carrier tag holds the attribute the value is substituted inside
    that opening tag and every other byte of the span is retained; where the
    carrier tag exists without it the attribute is written into that tag;
    where the carrier element is absent and the value is non-empty a child
    holding only that attribute is written into the ENTRY. An empty value is
    substituted where the carrier tag holds the attribute and is otherwise a
    no-op: it removes no attribute, removes no element and creates no
    carrier. Values are escaped on _xml_escape_attr's rule and each attribute
    keeps the quote character it already uses."""
    by_carrier: dict[str, list[tuple[str, str]]] = {}
    for name, value in values.items():
        carrier, attr_name = _ENTRY_CARRIERS[name]
        by_carrier.setdefault(carrier, []).append((attr_name, value))

    for carrier in _CARRIER_TAGS:
        edits = by_carrier.get(carrier)
        if not edits:
            continue
        if _find_tag_start(span, carrier) is None:
            # An empty value creates no carrier, and where a sibling value
            # creates one it writes nothing into it either.
            edits = [(attr_name, value) for attr_name, value in edits if value]
            if not edits:
                continue
            span = _insert_child(span, carrier)
        for attr_name, value in edits:
            start = _find_tag_start(span, carrier)
            end = _find_opening_tag_end(span, start) + 1
            span = span[:start] + _set_attr_in_tag(span[start:end], attr_name, value) + span[end:]
    return span

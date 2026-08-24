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

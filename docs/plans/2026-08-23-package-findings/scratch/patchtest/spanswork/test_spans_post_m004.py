"""Byte-span scanner: extent, nesting, escaping, and round-trip fidelity."""

from __future__ import annotations

from pathlib import Path

import pytest

from traktor_nml.spans import SpanIndex, element_span, find_element_span, recalculate_count_attr

REAL_FIXTURE = Path(r"C:\codex\general_tasks\collection_textual_patch_test.nml")


def test_self_closing_element_resolves_to_its_own_tag() -> None:
    source = '<PARENT><CHILD A="1"/></PARENT>'
    span = element_span(source, source.index("<CHILD"))
    assert span.text(source) == '<CHILD A="1"/>'


def test_empty_element_form_resolves_to_its_extent() -> None:
    source = '<PARENT><HEAD A="1"></HEAD></PARENT>'
    span = element_span(source, source.index("<HEAD"))
    assert span.text(source) == '<HEAD A="1"></HEAD>'


def test_nested_same_named_elements_resolve_to_outermost_extent() -> None:
    source = '<NODE NAME="outer"><NODE NAME="inner"></NODE></NODE><TAIL/>'
    span = element_span(source, 0)
    assert span.text(source) == '<NODE NAME="outer"><NODE NAME="inner"></NODE></NODE>'


def test_angle_brackets_and_quotes_inside_attribute_values_do_not_end_scan_early() -> None:
    source = '<ENTRY TITLE="a &lt;b&gt; c">text</ENTRY><TAIL/>'
    span = element_span(source, 0)
    assert span.text(source) == '<ENTRY TITLE="a &lt;b&gt; c">text</ENTRY>'


def test_find_element_span_does_not_match_a_longer_tag_name_sharing_a_prefix() -> None:
    source = '<NODENAME>x</NODENAME><NODE A="1"></NODE>'
    span = find_element_span(source, "NODE")
    assert span is not None
    assert span.text(source) == '<NODE A="1"></NODE>'


def test_recalculate_count_attr_rewrites_only_the_named_attribute() -> None:
    """Only COUNT changes; the two child <A/> elements and every other
    byte of the container's own opening tag are untouched."""
    fragment = '<SUBNODES COUNT="3"><A/><A/></SUBNODES>'
    rewritten = recalculate_count_attr(fragment, "SUBNODES", "COUNT", 2)
    assert rewritten == '<SUBNODES COUNT="2"><A/><A/></SUBNODES>'


@pytest.mark.skipif(not REAL_FIXTURE.exists(), reason="real fixture not present in this environment")
def test_reassembling_a_file_from_its_own_spans_reproduces_it_byte_for_byte() -> None:
    source = REAL_FIXTURE.read_text(encoding="utf-8")
    root_span = find_element_span(source, "NML")
    assert root_span is not None
    # The whole document minus any leading XML declaration/whitespace before
    # <NML plus the root span itself, concatenated back, must equal source.
    prefix = source[: root_span.start]
    suffix = source[root_span.end:]
    rebuilt = prefix + root_span.text(source) + suffix
    assert rebuilt == source


@pytest.mark.skipif(not REAL_FIXTURE.exists(), reason="real fixture not present in this environment")
def test_every_entry_and_node_span_in_real_corpus_parses_standalone() -> None:
    import lxml.etree as ET

    source = REAL_FIXTURE.read_text(encoding="utf-8")

    def _walk(tag: str, limit: int) -> int:
        count = 0
        idx = 0
        while True:
            idx = source.find(f"<{tag}", idx)
            if idx == -1:
                break
            span = element_span(source, idx)
            # A standalone fragment must be well-formed on its own.
            ET.fromstring(span.text(source))
            idx = span.end
            count += 1
            if count >= limit:  # bound the walk; the corpus has thousands
                break
        return count

    assert _walk("ENTRY", 200) > 0
    assert _walk("NODE", 200) > 0
def test_span_index_matches_element_span_for_entry_and_node_elements() -> None:
    import lxml.etree as ET

    source = (
        '<ROOT><COLLECTION><ENTRY A="1"><INFO/></ENTRY><ENTRY A="2"/></COLLECTION>'
        '<PLAYLISTS><NODE NAME="outer"><NODE NAME="inner"></NODE></NODE></PLAYLISTS></ROOT>'
    )
    root = ET.fromstring(source)
    index = SpanIndex(source, root)

    entries = root.findall(".//ENTRY")
    assert index.span_of(entries[0]).text(source) == '<ENTRY A="1"><INFO/></ENTRY>'
    assert index.span_of(entries[1]).text(source) == '<ENTRY A="2"/>'

    outer, inner = root.findall(".//NODE")
    assert index.span_of(inner).text(source) == "<NODE NAME=\"inner\"></NODE>"
    assert index.span_of(outer).text(source) == (
        '<NODE NAME="outer"><NODE NAME="inner"></NODE></NODE>'
    )


def test_span_index_handles_tag_names_sharing_a_prefix() -> None:
    import lxml.etree as ET

    source = '<ROOT><NODENAME>x</NODENAME><NODE A="1"></NODE></ROOT>'
    root = ET.fromstring(source)
    index = SpanIndex(source, root)

    node = root.find("NODE")
    nodename = root.find("NODENAME")
    assert index.span_of(node).text(source) == '<NODE A="1"></NODE>'
    assert index.span_of(nodename).text(source) == "<NODENAME>x</NODENAME>"


def test_span_index_raises_value_error_for_element_outside_indexed_tree() -> None:
    import lxml.etree as ET

    source = "<ROOT><ENTRY/></ROOT>"
    root = ET.fromstring(source)
    index = SpanIndex(source, root)
    outsider = ET.fromstring("<ENTRY/>")

    with pytest.raises(ValueError, match="ENTRY"):
        index.span_of(outsider)


def test_span_index_survives_gc_and_resolves_freshly_accessed_elements_correctly() -> None:
    """SpanIndex must retain a reference to every element it walked for
    its entire lifetime: under the lxml backend, an element is a
    transient proxy over the underlying libxml2 node, and once nothing
    references a proxy it can be garbage-collected, after which CPython
    may reuse its freed memory address for a new, unrelated proxy. A
    SpanIndex keyed only on id(element) without retaining a reference
    would then risk a later lookup matching a stale, recycled-address
    entry and silently returning the wrong span.

    This forces a GC cycle immediately after construction, then resolves
    spans via elements obtained from an independent, freshly issued
    lookup (traktor_nml.model.collection_records), rather than reusing
    any object from the original construction walk, and asserts every
    span still comes back correct.
    """
    import gc

    import lxml.etree as ET

    from traktor_nml.model import collection_records

    source = (
        '<NML VERSION="20"><COLLECTION ENTRIES="2">'
        '<ENTRY TITLE="A"><LOCATION DIR="/:" FILE="a.mp3"></LOCATION></ENTRY>'
        '<ENTRY TITLE="B"><LOCATION DIR="/:" FILE="b.mp3"></LOCATION></ENTRY>'
        "</COLLECTION></NML>"
    )
    root = ET.fromstring(source)
    index = SpanIndex(source, root)

    gc.collect()

    records = collection_records(root)
    assert index.span_of(records[0].entry).text(source) == (
        '<ENTRY TITLE="A"><LOCATION DIR="/:" FILE="a.mp3"></LOCATION></ENTRY>'
    )
    assert index.span_of(records[1].entry).text(source) == (
        '<ENTRY TITLE="B"><LOCATION DIR="/:" FILE="b.mp3"></LOCATION></ENTRY>'
    )


@pytest.mark.skipif(not REAL_FIXTURE.exists(), reason="real fixture not present in this environment")
def test_real_fixture_indexed_in_one_pass_and_every_entry_parses_standalone() -> None:
    import lxml.etree as ET

    source = REAL_FIXTURE.read_text(encoding="utf-8")
    root = ET.fromstring(source.encode("utf-8"))
    index = SpanIndex(source, root)

    for entry in root.iter("ENTRY"):
        span = index.span_of(entry)
        ET.fromstring(span.text(source))

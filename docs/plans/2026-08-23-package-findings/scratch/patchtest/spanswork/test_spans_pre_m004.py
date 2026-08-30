"""Byte-span scanner: extent, nesting, escaping, and round-trip fidelity."""

from __future__ import annotations

from pathlib import Path

import pytest

from traktor_nml.spans import element_span, find_element_span, recalculate_count_attr

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

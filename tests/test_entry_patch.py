"""Guards over patch_entry_attributes, the ENTRY-span attribute rewrite."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from traktor_nml.textpatch import patch_entry_attributes

MULTILINE = (
    '<ENTRY MODIFIED_DATE="2024/1/1" ARTIST="Base Artist" TITLE="Base Title">\r\n'
    '      <LOCATION DIR="/:Music/:" FILE="a.mp3" VOLUME="C:"></LOCATION>\r\n'
    '      <MODIFICATION_INFO AUTHOR_TYPE="user"></MODIFICATION_INFO>\r\n'
    '      <INFO BITRATE="128000" PLAYTIME="180" PLAYTIME_FLOAT="180.5" FILESIZE="4200"></INFO>\r\n'
    '      <TEMPO BPM="120" BPM_QUALITY="100"></TEMPO>\r\n'
    '    </ENTRY>'
)

SINGLE_LINE = (
    '<ENTRY ARTIST="Base Artist" TITLE="Base Title">'
    '<LOCATION DIR="/:Music/:" FILE="a.mp3" VOLUME="C:"></LOCATION>'
    '<INFO BITRATE="128000"></INFO>'
    '</ENTRY>'
)


def child_tags(span: str) -> list[str]:
    return [child.tag for child in ET.fromstring(span)]


def test_bitrate_substituted_in_place() -> None:
    """A bitrate value lands on INFO's BITRATE and touches nothing else.

    Made to fail by pointing _ENTRY_CARRIERS' "bitrate" entry at
    ("INFO", "PLAYTIME"): the returned INFO read
    BITRATE="128000" PLAYTIME="320000" PLAYTIME_FLOAT="180.5" FILESIZE="4200"
    against the expected BITRATE="320000" PLAYTIME="180" ...
    """
    out = patch_entry_attributes(MULTILINE, {"bitrate": "320000"})
    assert out == MULTILINE.replace('BITRATE="128000"', 'BITRATE="320000"')
    assert out != MULTILINE
    assert child_tags(out) == ["LOCATION", "MODIFICATION_INFO", "INFO", "TEMPO"]


def test_album_inserted_in_child_order() -> None:
    """An absent ALBUM is inserted between LOCATION and MODIFICATION_INFO.

    Made to fail by dropping the slice in _insert_child so that order is the
    whole _ENTRY_CHILD_ORDER and the anchor became the last child present:
    the returned child tag names read
    ['LOCATION', 'MODIFICATION_INFO', 'INFO', 'ALBUM', 'TEMPO'], differing at
    index 1 where 'MODIFICATION_INFO' stood in place of 'ALBUM'.
    """
    assert child_tags(MULTILINE) == ["LOCATION", "MODIFICATION_INFO", "INFO", "TEMPO"]
    out = patch_entry_attributes(MULTILINE, {"album": "Inserted Album"})
    assert child_tags(out) == ["LOCATION", "ALBUM", "MODIFICATION_INFO", "INFO", "TEMPO"]
    assert ET.fromstring(out).find("ALBUM").attrib == {"TITLE": "Inserted Album"}


def test_info_inserted_after_album() -> None:
    """An absent INFO is inserted after ALBUM, the last preceding child present.

    Made to fail by breaking out of _insert_child's anchor loop at the first
    preceding child found, which anchored on LOCATION: the returned child tag
    names read ['LOCATION', 'INFO', 'ALBUM'] against ['LOCATION', 'ALBUM',
    'INFO'].
    """
    span = (
        '<ENTRY ARTIST="A">\n'
        '      <LOCATION FILE="a.mp3"></LOCATION>\n'
        '      <ALBUM TITLE="Base Album"></ALBUM>\n'
        '    </ENTRY>'
    )
    out = patch_entry_attributes(span, {"filesize": "4200"})
    assert child_tags(out) == ["LOCATION", "ALBUM", "INFO"]
    assert ET.fromstring(out).find("INFO").attrib == {"FILESIZE": "4200"}


def test_crlf_span_keeps_its_line_endings() -> None:
    """An insertion into a CRLF span writes CRLF and no bare LF.

    Made to fail by composing _insert_child's whitespace as a bare LF plus
    the sibling run stripped of its terminator: the returned span held 5 CRLF
    against the 6 expected, its sixth line terminator being the bare LF the
    fragment composed.
    """
    out = patch_entry_attributes(MULTILINE, {"album": "Inserted Album"})
    assert out.count("\r\n") == MULTILINE.count("\r\n") + 1
    assert out.count("\n") - out.count("\r\n") == 0
    assert '\r\n      <ALBUM TITLE="Inserted Album"></ALBUM>\r\n      <MODIFICATION_INFO' in out


def test_single_line_span_gains_no_terminator() -> None:
    """An insertion into a single-line span writes no terminator at all.

    Made to fail by defaulting _insert_child's empty whitespace run to a bare
    LF: the returned span broke after </LOCATION>, its next line reading
    <ALBUM TITLE="Inserted Album"></ALBUM><INFO BITRATE="128000"></INFO>.
    """
    out = patch_entry_attributes(SINGLE_LINE, {"album": "Inserted Album"})
    assert "\n" not in out
    assert "\r" not in out
    assert child_tags(out) == ["LOCATION", "ALBUM", "INFO"]


def test_artist_substituted_on_entry_tag() -> None:
    """An artist value lands on the ENTRY opening tag's own ARTIST.

    Made to fail by pointing _ENTRY_CARRIERS' "artist" entry at
    ("ENTRY", "TITLE"): the returned opening tag read
    ARTIST="Base Artist" TITLE="Source Artist" against the expected
    ARTIST="Source Artist" TITLE="Base Title".
    """
    out = patch_entry_attributes(MULTILINE, {"artist": "Source Artist"})
    assert out == MULTILINE.replace('ARTIST="Base Artist"', 'ARTIST="Source Artist"')


def test_empty_value_without_carrier_is_byte_identical() -> None:
    """An empty value for an absent carrier creates nothing.

    Made to fail by keeping every edit in patch_entry_attributes' absent-
    carrier branch instead of filtering the empty ones: the returned span
    carried an inserted <ALBUM TITLE=""></ALBUM> line ahead of
    MODIFICATION_INFO where the original span had none.
    """
    out = patch_entry_attributes(MULTILINE, {"album": ""})
    assert out == MULTILINE


def test_empty_value_on_an_existing_carrier() -> None:
    """An empty value is substituted, and removes no attribute.

    Made to fail by having _set_attr_in_tag delete the matched attribute when
    the value is empty: the returned INFO's attributes read
    {'PLAYTIME': '180', 'PLAYTIME_FLOAT': '180.5', 'FILESIZE': '4200'},
    missing the BITRATE the assertion expects to read empty.
    """
    out = patch_entry_attributes(MULTILINE, {"bitrate": ""})
    info = ET.fromstring(out).find("INFO")
    assert info.attrib == {
        "BITRATE": "",
        "PLAYTIME": "180",
        "PLAYTIME_FLOAT": "180.5",
        "FILESIZE": "4200",
    }
    assert child_tags(out) == ["LOCATION", "MODIFICATION_INFO", "INFO", "TEMPO"]


def test_markup_characters_round_trip() -> None:
    """An ampersand and a double quote survive a parse of the returned span.

    Made to fail by having _set_attr_in_tag substitute the raw value instead
    of _xml_escape_attr's: the returned tag read
    ARTIST="Simon & Garfunkel "Live"" and ET.fromstring raised
    ParseError: not well-formed (invalid token): line 1, column 47.
    """
    value = 'Simon & Garfunkel "Live"'
    out = patch_entry_attributes(MULTILINE, {"artist": value, "album": value})
    root = ET.fromstring(out)
    assert root.attrib["ARTIST"] == value
    assert root.find("ALBUM").attrib["TITLE"] == value


def test_insertion_anchor_spans_a_child_attribute_holding_a_close_tag() -> None:
    """The INFO lands after ALBUM whose child attribute holds the text </ALBUM.

    Made to fail by restoring the hand-rolled scanner _insert_child's anchor
    loop once used - a _find_tag_start regex plus an _element_end that took
    span.index("</" + tag_name) as the close tag and ran
    _find_opening_tag_end from there: patch_entry_attributes raised
    ValueError: unclosed opening tag at offset 80, the scan having entered
    the SUB attribute value and consumed the rest of the span looking for a
    '>' outside quotes.
    """
    span = (
        '<ENTRY ARTIST="A">'
        '<LOCATION FILE="a.mp3"></LOCATION>'
        '<ALBUM TITLE="X"><SUB NOTE="</ALBUM"></SUB></ALBUM>'
        '</ENTRY>'
    )
    out = patch_entry_attributes(span, {"filesize": "4200"})
    assert out == span.replace(
        "</ALBUM></ENTRY>", '</ALBUM><INFO FILESIZE="4200"></INFO></ENTRY>'
    )


def test_insertion_anchor_spans_a_comment_holding_a_close_tag() -> None:
    """The INFO lands after ALBUM whose own content holds a </ALBUM comment.

    Made to fail by restoring that same hand-rolled scanner: the returned
    span read
    <ENTRY ARTIST="A"><LOCATION FILE="a.mp3"></LOCATION><ALBUM TITLE="X">
    <!-- </ALBUM --><INFO FILESIZE="4200"></INFO></ALBUM></ENTRY>
    (on one line), the anchor extent having ended inside the comment so the
    new INFO was written into ALBUM's content rather than after it.
    """
    span = (
        '<ENTRY ARTIST="A">'
        '<LOCATION FILE="a.mp3"></LOCATION>'
        '<ALBUM TITLE="X"><!-- </ALBUM --></ALBUM>'
        '</ENTRY>'
    )
    out = patch_entry_attributes(span, {"filesize": "4200"})
    assert out == span.replace(
        "</ALBUM></ENTRY>", '</ALBUM><INFO FILESIZE="4200"></INFO></ENTRY>'
    )
    assert child_tags(out) == ["LOCATION", "ALBUM", "INFO"]

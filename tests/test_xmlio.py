"""xmlio: backend-selection parsing helpers."""

from __future__ import annotations

import traktor_nml.xmlio as xmlio


_VALID_NML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
    '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
    '<COLLECTION ENTRIES="0"></COLLECTION>'
    '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS>'
    "<SETS></SETS><INDEXING></INDEXING></NML>"
)


def test_parse_xml_bytes_on_stdlib_fallback_does_not_raise_typeerror(monkeypatch) -> None:
    monkeypatch.setattr(xmlio, "HAS_LXML", False)
    root = xmlio.parse_xml_bytes(_VALID_NML.encode("utf-8"))
    assert root.attrib.get("VERSION") == "20"


def test_parse_xml_bytes_on_stdlib_fallback_raises_parse_error_on_malformed_input(monkeypatch) -> None:
    monkeypatch.setattr(xmlio, "HAS_LXML", False)
    try:
        xmlio.parse_xml_bytes(b"<NML><unclosed>")
    except xmlio.XML_PARSE_ERROR:
        pass
    else:
        raise AssertionError("expected XML_PARSE_ERROR for malformed bytes")

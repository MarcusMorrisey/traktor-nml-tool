"""XML backend selection and shared byte-level constants.

lxml provides two capabilities the stdlib ET cannot: source-line metadata on
every element (needed by textpatch.apply_text_patches to locate the right tag
in the raw text) and whitespace-preserving parse/serialise (so round-trips
don't reformat the document). See traktor_nml.cli for the full write-strategy
rationale. Every other module imports ET and HAS_LXML from here so there is
exactly one place that decides which backend is active.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

try:
    import lxml.etree as ET

    HAS_LXML = True
    XML_PARSE_ERROR = ET.XMLSyntaxError
except ImportError:  # pragma: no cover - fallback for environments without lxml
    import xml.etree.ElementTree as ET

    HAS_LXML = False
    XML_PARSE_ERROR = ET.ParseError


XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'


def parse_xml(path: Path):
    """Parse path via whichever backend xmlio selected at import time,
    keeping blank-text and CDATA handling identical between the lxml
    default and the stdlib fallback."""
    if HAS_LXML:
        parser = ET.XMLParser(remove_blank_text=False, strip_cdata=False, recover=False)
        return ET.parse(str(path), parser)
    return ET.parse(path)


def parse_xml_bytes(source_bytes: bytes):
    """Parse raw bytes, raising XML_PARSE_ERROR on malformed input.

    Only meaningful on the lxml path, where sourceline-carrying elements are
    required for text patching; callers on the stdlib fallback path use
    parse_xml against a file path instead.
    """
    parser = ET.XMLParser(remove_blank_text=False, strip_cdata=False, recover=False)
    return ET.fromstring(source_bytes, parser)


def write_traktor_xml(
    root, output: Path, write_bytes: Optional[Callable[[Path, bytes], None]] = None
) -> None:
    if HAS_LXML:
        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=False, pretty_print=False)
    else:
        xml_bytes = ET.tostring(root, encoding="unicode").encode("utf-8")
    data = XML_DECLARATION.encode("utf-8") + xml_bytes
    if write_bytes is not None:
        # Callers on the byte-preserving write path (write_nml_safely) pass
        # their own atomic (temp file + replace) writer so a mid-write
        # failure here cannot truncate an existing destination either.
        write_bytes(output, data)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        handle.write(data)

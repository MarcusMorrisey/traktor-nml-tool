"""Guards the served-page records under `docs/` against DL-084's
structural requirement.

Four records read a matches verdict on every surface they measure while
the pages they measured are composed nothing like the artboards - the
gap DL-169 closes by requiring a structural reading beside the atom
readings. These guards read the records as text, so they run under the
system interpreter with no nicegui and no browser.

The record set is discovered from the directory rather than listed, so
a record written after this file falls under the gate without an edit
here (DL-084's amendment). Each record's atom reading lines are held as
a digest, which is what makes DL-171 a suite failure rather than a
reviewer's catch: a re-verdict that rewrote a recorded reading changes
the digest.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
README = REPO_ROOT / "traktor_nml" / "README.md"

# A browser record is named for the run that wrote it. The suffix is the
# discovery rule: a record added later matches it and is gated, and a
# plan or an analysis under docs/ does not.
_RECORD_SUFFIXES = ("-browser-record.md", "-focus-ring-record.md", "-paint-record.md")

_STRUCTURAL_HEADING = re.compile(r"^#+\s*Structural verdicts\s*$", re.MULTILINE)
_VERDICT_ROW = re.compile(r"^\|.*\|\s*(matches|differs)\s*\|\s*$", re.MULTILINE)
_COMPOSITION_ENTRY = re.compile(r"^- \*\*(.+?)\.\*\*", re.MULTILINE)


def browser_records() -> list[Path]:
    """Every served-page record under docs/, discovered by name."""
    return sorted(
        path
        for path in DOCS.glob("*.md")
        if any(path.name.endswith(suffix) for suffix in _RECORD_SUFFIXES)
    )


def _reading_digest(text: str) -> str:
    """A digest of one record's verdict rows.

    Reads the verdict rows above the Structural verdicts heading - the
    rows the run itself measured - rather than the whole file. Appending
    a structural section therefore leaves the digest alone, while
    editing a reading the run recorded changes it, which is the
    direction DL-171 constrains.
    """
    heading = _STRUCTURAL_HEADING.search(text)
    atoms = text[: heading.start()] if heading else text
    joined = "\n".join(match.group(0) for match in _VERDICT_ROW.finditer(atoms))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


# The digest of each record's verdict rows as they stand. Held here so a
# reading edited during a re-verdict fails this file (DL-171); a record
# absent from this mapping is new and carries no prior readings to hold.
READING_DIGESTS = {
    "2026-08-27-m001-browser-record.md": "dbef7a4a97c01c5701fe62983e9687be76650039eb9218bd3264c45430e4001e",
    "2026-08-28-w002-browser-record.md": "3a1759dce7ccd384c279c79c3aaa76d9eac3367ef8646e1ea8d8cf76e9a32250",
    "2026-08-29-w004-focus-ring-record.md": "22120b36351a3e10ad6c3706503f04f6ddbb8bc602c3d5377b9a014da0ac3c88",
    "2026-09-03-header-tabs-browser-record.md": "8efef9b91ac577095c5f8c76af04ea522c7dc4e8d473dd34e85fbd134413d5da",
    "2026-09-05-wizard-shell-browser-record.md": "96af8ac3efe80408c6004de8b51b74ccb52b6d2db5a7d093869d3b21c54176da",
    "2026-09-06-wizard-focus-order-browser-record.md": "dd1dc94601c280dee67ed38aee69f945de782d976ff33aab53b3e66084a0203e",
    "2026-09-07-composition-close-browser-record.md": "24f5629d3285c3ed3575c8bb5b16d295a924aafa443f6c6419c60e829e19b696",
    "2026-09-07-reconstruct-resolve-browser-record.md": "ca763fd3ab58186a8444e0aaa0e9f923a60ccf3ef846931405987619c3ce7d96",
    "2026-09-07-reconstruct-preview-and-write-browser-record.md": "a205d5157b6f6ad5c773ffc599236640c986183acebbf7c725097da777adab9d",
    "2026-09-07-reconstruct-setup-browser-record.md": "7faff10b12fd46d23ffeee0c465ecff634032dbc330d476d65b2965fbb74193f",
    "2026-09-07-reconstruct-stale-run-browser-record.md": "ebc2f041052776259c4c6749145de24cb199b50f8db4e25047ff3db519f40cbd",
    "2026-09-15-reconstruct-salvage-browser-record.md": "ab3a0251c15db195d121abffdc1e905e374b4e03f37140dc314761a528077640",
    "2026-09-15-write-step-after-the-write-browser-record.md": "32dfbfadf3db8e36441a21e886003215da2cb59fb63a7665e7b0429757a3c61a",
    # The resolve step's rail closes on a served-page record carrying a
    # verdict row per surface and structural verdicts against
    # design/reconnect-wizard/Resolve.dc.html, its verdict rows
    # registered here by digest (ref: DL-084, DL-169). The digest is
    # computed from the record as the browser run left it, so the rows
    # hashed are the rows that were read.
    "2026-09-15-resolve-rail-fields-browser-record.md": "33066ad27dee9e65b6726bd5c048ffcced89e31fe37f4689d5df3e0ca25c2483",
    # Every button on the action blue closes on a served-page record
    # reading each route's buttons - a disabled one and an exempt one on
    # every route - with structural verdicts against the amended .btn,
    # .btn-pri and .btn.off, its verdict rows registered here by digest
    # (ref: DL-084, DL-169, DL-273). The digest is computed from the
    # record as the browser run left it.
    "2026-09-16-button-fill-browser-record.md": "8e93e5956dd0c07d1ef322d044fa9d2284f7b6becb711fb968e1cabb86babcd7",
    # The build-playlist screen's widened inputs, CSV template and two
    # folders close on a served-page record reading each input format, the
    # downloaded template's bytes, both folder choosers with Full collection
    # off and on, and the written file's location and placement, with
    # structural verdicts against design/build-playlist/Specs.dc.html
    # (ref: DL-084, DL-169, DL-295, DL-297). The digest is computed from the
    # record as the browser run left it.
    "2026-09-16-build-playlist-inputs-browser-record.md": "db998d509708aa74ecdb1284046aaba938098eaaf7a97dceb0afc70cb92934ef",
    # The resolve rail's key track closes on a served-page record reading
    # every label's rendered width against the track, marked and unmarked,
    # the value column left and a long value's truncation, with structural
    # verdicts against the amended .cmpf (ref: DL-084, DL-169, DL-298). The
    # digest is computed from the record as the browser run left it.
    "2026-09-16-resolve-key-track-browser-record.md": "eb2215068db5bb50cbe3dd644ac21e472817b133fcea2e178f13b1fc2428cfbf",
    # The chooser buttons' widths close on a served-page record reading
    # every Choose and Download CSV template button on /, /reconnect and
    # /build-playlist against its label and its container, before and after
    # the /reconnect choosers were composed in their row, with structural
    # verdicts against each route's artboard .row (ref: DL-084, DL-169,
    # DL-299). The digest is computed from the record as the browser run
    # left it.
    "2026-09-16-chooser-width-browser-record.md": "cfd0ec905103370579809cc81b01b5bbef6614d44a4d58f3b70df9ddfaa73507",
    # every Choose button on /, /reconnect and /build-playlist: its centre
    # against its path's, its margins and its row's align-items, and the
    # space below each row, before and after .wizard-control's bottom
    # margin was cancelled inside the chooser rows, with structural verdicts
    # against each route's artboard .row (ref: DL-084, DL-169, DL-301). The
    # digest is computed from the record as the browser run left it.
    "2026-09-16-chooser-offset-browser-record.md": "2acd86830d5e8244eb06a422fae2bedcea3c77fe16da938ac753e5f223cb8bae",
    # The build-playlist report's column headers close on a served-page
    # record reading the header cells' label, each column's left edge and
    # width on the header and every body row, the header and row rules and
    # a long entry's truncation, with structural verdicts against
    # Specs.dc.html's table.rep (ref: DL-084, DL-169, DL-302). The digest is
    # computed from the record as the browser run left it.
    "2026-09-17-report-columns-browser-record.md": "48bf6feacb2fc5caa0f60874eef43823312b06d999d9a9136d2bfc1b0b645ccc",
    # The report card scrolled into view after a refused run and the
    # encoding's display name close on a served-page record reading the
    # middle region's scrollTop before and after each run, the card's box
    # inside the middle at two heights, the document staying unscrolled
    # and the footer for a UTF-8 and a cp1252 CSV, with structural
    # verdicts against the amended .ft-note (ref: DL-084, DL-169,
    # DL-303). The digest is computed from the record as the browser run
    # left it.
    "2026-09-17-report-scroll-and-encoding-browser-record.md": "e7723a0e854a6887b161d6f78e1afcd1a7ccfc595cbb4af50eef8192a43f305b",
    # The unresolved report's kind pills close on a served-page record
    # reading each pill's text, colour, tinted ground and border, the
    # shape the three share, that the pill hugs its word inside the
    # 120px Kind column, the column's left edge and width against the
    # header and the document staying unscrolled, with structural
    # verdicts against Specs.dc.html's .kind (ref: DL-084, DL-169,
    # DL-304). The digest is computed from the record as the browser run
    # left it.
    "2026-09-17-report-kind-pills-browser-record.md": "745dd332bba458251ca1cbff52ac4d4d093688d41ac2ca320a1dae5ba6deb7cf",
}

# A digest is the hash of the readings one run recorded, so it is written
# by the run that takes them and not before: an entry standing here ahead
# of its record would hash the readings this file guessed rather than the
# ones the browser gave. A record is discovered by name and gated by every
# guard below the moment it exists; only the digest guard skips a record
# with no entry, and it stops skipping when the run that writes the record
# writes its digest here too (DL-171, DL-209).


def test_the_record_set_is_discovered_and_is_not_empty():
    """browser_records() finds the served-page records under docs/ by
    name, so a record written after this file is gated without an edit
    here.

    Mutation: _RECORD_SUFFIXES was reduced to ("-paint-record.md",),
    which no record under docs/ carries today, and this guard rerun.
    Observed:
        AssertionError: no browser record discovered under docs/
        assert [] != []
    """
    records = browser_records()
    assert records != [], "no browser record discovered under docs/"
    names = {path.name for path in records}
    assert "2026-08-28-w002-browser-record.md" in names


@pytest.mark.parametrize("record", browser_records(), ids=lambda path: path.name)
def test_every_record_carries_a_structural_verdicts_section(record: Path):
    """Every discovered record carries a Structural verdicts heading.
    A record holding atom verdicts alone is what DL-169 fails.

    Mutation: the '## Structural verdicts' heading line was deleted
    from docs/2026-08-29-w004-focus-ring-record.md and this guard
    rerun. Observed:
        AssertionError: 2026-08-29-w004-focus-ring-record.md carries no
        Structural verdicts section
        assert None
    """
    text = record.read_text(encoding="utf-8")
    assert _STRUCTURAL_HEADING.search(text), (
        f"{record.name} carries no Structural verdicts section"
    )


@pytest.mark.parametrize("record", browser_records(), ids=lambda path: path.name)
def test_a_records_verdict_rows_hash_to_its_recorded_digest(record: Path):
    """A record's verdict rows hash to the digest held above. This is
    DL-171 enforced: a re-verdict inserts a section and leaves every
    recorded reading alone, and an edited reading changes the digest.

    A record with no entry in READING_DIGESTS is one written after this
    mapping and has no prior readings to hold.

    Mutation: in docs/2026-08-28-w002-browser-record.md the Dialog
    Cancel row's reading was changed from 32.0156px to 33.0156px and
    this guard rerun. Observed:
        AssertionError: 2026-08-28-w002-browser-record.md verdict rows
        changed: a recorded reading is edited, which DL-171 forbids
        assert '12b2f4ec2069...bbd4ae3c9000d' ==
        '3a1759dce7cc...8cf76e9a32250'

    Mutation: in docs/2026-09-07-composition-close-browser-record.md the
    Footer height row's reading was changed from 64px to 65px and this
    guard rerun. Observed:
        AssertionError: 2026-09-07-composition-close-browser-record.md
        verdict rows changed: a recorded reading is edited, which DL-171
        forbids
        assert '5a1ca7434f3a...f00df6dc69b7a' ==
        '24f5629d3285...60e829e19b696'

    Mutation: in docs/2026-09-15-resolve-rail-fields-browser-record.md
    the rail width row's reading was changed from 400 to 360 and this
    guard rerun. Observed:
        E       assert 'b5ddea77ebdb...7f6321a8b9917' == '33066ad27dee...f3e0ca25c2483'
        E
        E         - 33066ad27dee9e65b6726bd5c048ffcced89e31fe37f4689d5df3e0ca25c2483
        E         + b5ddea77ebdbad8533d711c98ad68b8feb92e62c91c8b1aefe67f6321a8b9917
    """
    expected = READING_DIGESTS.get(record.name)
    if expected is None:
        pytest.skip(f"{record.name} carries no recorded digest")
    actual = _reading_digest(record.read_text(encoding="utf-8"))
    assert actual == expected, (
        f"{record.name} verdict rows changed: a recorded reading is edited, "
        "which DL-171 forbids"
    )


def test_every_structure_a_record_names_resolves_in_the_decision_log():
    """A structure a record names in a differs verdict is an entry
    under 'Composition not built' in traktor_nml/README.md, so a
    differs verdict cannot point at a section that does not record it.

    Only the newest reading of a structure is checked. A structure a
    later run reads as built stops naming an entry the section does not
    hold, while every standing record keeps the differs rows the run
    that wrote it recorded (DL-171, DL-195).

    Mutation: the '- **Detail rail.**' entry was deleted from the
    Composition not built section and this guard rerun. Observed:
        AssertionError: structures named in a record with no
        Composition not built entry: ['Detail rail']
        assert ['Detail rail'] == []

    Mutation: an 'App shell | .app | one column | differs' row was
    appended to the Structural verdicts section of
    docs/2026-09-06-wizard-focus-order-browser-record.md, the newest
    record, while the App shell structure carries no entry in the
    section, and this guard rerun. Observed:
        AssertionError: structures named in a record with no
        Composition not built entry: ['App shell']
        assert ['App shell'] == []
    """
    readme = README.read_text(encoding="utf-8")
    heading = "## Composition not built"
    assert heading in readme, "traktor_nml/README.md carries no Composition not built section"
    section = readme[readme.index(heading):]
    # entries is the set of structures the 'Composition not built'
    # section still records; a struck structure is absent from it, which
    # is what makes a stale differs row on the newest record fail here.
    entries = {name for name in _COMPOSITION_ENTRY.findall(section)}
    assert entries, "the Composition not built section holds no entries"

    # browser_records() sorts by name and every record is named for the
    # run that wrote it, so the last verdict a structure collects is the
    # newest reading of it.
    newest: dict[str, str] = {}
    for record in browser_records():
        text = record.read_text(encoding="utf-8")
        match = _STRUCTURAL_HEADING.search(text)
        if not match:
            continue
        for row in _VERDICT_ROW.finditer(text[match.end():]):
            cells = [cell.strip() for cell in row.group(0).strip("|").split("|")]
            if cells:
                newest[cells[0].strip("* ")] = row.group(1)

    adrift = sorted(
        name
        for name, verdict in newest.items()
        if verdict == "differs" and name not in entries
    )
    assert adrift == [], (
        f"structures named in a record with no Composition not built entry: {adrift}"
    )


def test_the_three_headings_each_state_their_distinction():
    """Framework shortfalls, Design-set divergences and Composition not
    built each name the other two, so a reader landing on one is told
    what belongs in the others (DL-170).

    Mutation: the sentence naming the other two headings was deleted
    from under '## Composition not built' and this guard rerun.
    Observed:
        AssertionError: Composition not built does not name Framework
        shortfalls
        assert 'Framework shortfalls' in '...'
    """
    readme = README.read_text(encoding="utf-8")
    headings = ["Framework shortfalls", "Design-set divergences", "Composition not built"]
    bodies = {}
    for name in headings:
        marker = f"## {name}"
        assert marker in readme, f"traktor_nml/README.md carries no {name} section"
        start = readme.index(marker) + len(marker)
        rest = readme[start:]
        end = rest.index("\n## ") if "\n## " in rest else len(rest)
        bodies[name] = rest[:end]

    for name, body in bodies.items():
        for other in headings:
            if other == name:
                continue
            assert other in body, f"{name} does not name {other}"

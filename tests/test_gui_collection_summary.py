"""Guards traktor_nml/gui/collection_summary.py: what the reconstruct
page's set-up step reports about a collection it has been given, and the
list of steps it says come next.

The module imports no framework, so these run the rules themselves under
the system interpreter (DL-069). What the browser did with the numbers is
a served-page reading and belongs to the record (DL-084, DL-189).

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation.
"""

from __future__ import annotations

from traktor_nml.gui import collection_summary, reconstruct_steps
from traktor_nml.xmlio import parse_xml_bytes


def _collection(entries: int, playlists: list, declared: dict | None = None) -> object:
    """A parsed collection holding `entries` tracks and one playlist per
    entry in `playlists`, each holding that many primary keys.

    `declared` overrides the ENTRIES attribute of the playlist at that
    index, so a fixture can hold a file whose declared count disagrees
    with what it actually carries - which is the only fixture that tells
    a reading of the attribute apart from a reading of the keys.
    """
    declared = declared or {}
    entry_xml = "".join(
        f'<ENTRY TITLE="t{index}"><LOCATION DIR="/:M/:" FILE="{index}.mp3" '
        f'VOLUME="C:"></LOCATION></ENTRY>'
        for index in range(entries)
    )
    nodes = "".join(
        f'<NODE TYPE="PLAYLIST" NAME="p{index}">'
        f'<PLAYLIST ENTRIES="{declared.get(index, held)}">'
        + "".join(
            f'<ENTRY><PRIMARYKEY TYPE="TRACK" KEY="C:/:M/:{key}.mp3"></PRIMARYKEY>'
            "</ENTRY>"
            for key in range(held)
        )
        + "</PLAYLIST></NODE>"
        for index, held in enumerate(playlists)
    )
    text = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>'
        f'<NML VERSION="20"><COLLECTION ENTRIES="{entries}">{entry_xml}</COLLECTION>'
        f'<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="{len(playlists)}">'
        f"{nodes}</SUBNODES></NODE></PLAYLISTS></NML>"
    )
    return parse_xml_bytes(text.encode("utf-8"))


def test_a_collection_reports_its_tracks_its_playlists_and_the_empty_ones():
    """The three counts the set-up step prints under the collection being
    repaired. A playlist holding no primary key is empty, whatever its
    own ENTRIES attribute says, which is the reading splice.py takes when
    it decides which playlists a reconstruction refilled.

    Mutation: `empty=sum(1 for node in nodes if not node_primary_keys(node))`
    was changed to read the PLAYLIST element's ENTRIES attribute, and the
    fixture's empty playlists declare ENTRIES="0" while one filled
    playlist was left declaring the same. Observed:
        E       AssertionError: CollectionSummary(tracks=4, playlists=4, empty=3)
        E       assert 3 == 2
        E        +  where 3 = CollectionSummary(tracks=4, playlists=4, empty=3).empty
    """
    # The third playlist declares ENTRIES="0" and holds two keys: a file
    # whose declaration disagrees with its contents is reported by what
    # it holds.
    summary = collection_summary.summarise(
        _collection(4, [3, 0, 2, 0], declared={2: 0})
    )
    assert summary.tracks == 4
    assert summary.playlists == 4
    assert summary.empty == 2, summary
    # filled is derived rather than counted again, so the two counts
    # cannot disagree about the same file.
    assert summary.filled == 2
    assert summary.filled + summary.empty == summary.playlists


def test_the_count_that_makes_the_page_worth_running_is_stated_either_way():
    """The count of empty playlists is what this page repairs, so a
    collection with some says how many and one with none says so in
    words rather than printing a zero the reader has to interpret.

    Mutation: the `if self.empty else "none of them empty"` branch was
    removed, so the phrase read a count in both cases. Observed:
        E       AssertionError: ('12 tracks', '3 playlists', '0 of them empty', 'this file is never modified')
        E       assert '0 of them empty' == 'none of them empty'
        E
        E         - none of them empty
        E         + 0 of them empty
    """
    some = collection_summary.summarise(_collection(12, [4, 0, 0]))
    assert some.repair_phrases[2] == "2 of them empty", some.repair_phrases
    none = collection_summary.summarise(_collection(12, [4, 1, 2]))
    assert none.repair_phrases[2] == "none of them empty", none.repair_phrases
    # The phrases are the line, in the order the artboard draws them.
    assert none.repair_phrases[0] == "12 tracks"
    assert none.repair_phrases[1] == "3 playlists"
    assert none.repair_phrases[3] == "this file is never modified"


def test_a_source_reads_how_many_playlists_it_could_supply():
    """A source's own row says what that collection could contribute, and
    a source with nothing to contribute is what the row exists to make
    visible: it says so rather than reading a zero.

    Mutation: the `if not self.filled` branch was removed. Observed:
        E       AssertionError: 0 playlists with contents
        E       assert '0 playlists with contents' == 'no playlists with contents'
        E
        E         - no playlists with contents
        E         ?  ^
        E         + 0 playlists with contents
        E         ?  ^
    """
    empty = collection_summary.summarise(_collection(2, [0, 0]))
    assert empty.source_note == "no playlists with contents", empty.source_note
    one = collection_summary.summarise(_collection(2, [1, 0]))
    assert one.source_note == "1 playlist with contents", one.source_note
    several = collection_summary.summarise(_collection(4, [1, 2, 0]))
    assert several.source_note == "2 playlists with contents", several.source_note


def test_the_steps_it_says_come_next_are_the_steps_the_rail_carries():
    """The set-up step's own account of what follows names the steps by
    the numbers reconstruct_steps holds, so the list and the rail beside
    it cannot disagree about which step resolves the conflicts.

    Mutation: `number=reconstruct_steps.RESOLVE` on the second entry was
    changed to the literal 4. Observed:
        E       AssertionError: (2, 4, 4)
        E       assert (2, 4, 4) == (2, 3, 4)
        E
        E         At index 1 diff: 4 != 3
        E         Use -v to get more diff
    """
    numbers = tuple(step.number for step in collection_summary.NEXT_STEPS)
    expected = tuple(
        number
        for number, _ in reconstruct_steps.STEPS
        if number != reconstruct_steps.SET_UP
    )
    assert numbers == expected, numbers
    # Every one is titled and explained: a numbered row with nothing
    # under it names a step without saying what happens at it.
    assert all(step.title and step.detail for step in collection_summary.NEXT_STEPS)

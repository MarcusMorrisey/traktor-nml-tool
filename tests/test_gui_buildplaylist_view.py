"""Guards for traktor_nml/gui/buildplaylist_view.py's form validation
and report shaping. Each guard constructs its broken scenario in
executable code and records the mutation and the observed output,
matching the register tests/test_gui_review_model.py and
tests/test_gui_navigation.py already use.

Runs on the system pytest interpreter with no nicegui installed,
importing traktor_nml.gui.buildplaylist_view directly (DL-069, DL-261).
"""

from __future__ import annotations

from traktor_nml.buildplaylist import BuildPlaylistResult, UnresolvedRow
from traktor_nml.gui.buildplaylist_view import (
    FormInputs,
    csv_columns_note,
    form_errors,
    playlist_folder_options,
    run_summary,
    unresolved_report_rows,
)
from traktor_nml.playlistinput import InputFormat
from traktor_nml.playlists import PlaylistFolderChoice

_FILLED = FormInputs(
    base_path="D:/Traktor/collection.nml",
    input_path="C:/lists/warehouse.txt",
    name="Warehouse set",
    output_dir="",
    playlist_folder="",
    allow_unmatched=False,
    full_collection=False,
)


def test_form_errors_reports_each_missing_field():
    """A fully filled form reports no refusal; a form missing exactly
    one required field reports exactly one, naming that field.

    Made to fail by mutating form_errors to always return (), which
    hides a missing field from the operator entirely. Observed:
        E       AssertionError: assert () == ('Choose the ...collection.',)
        E
        E         Right contains one more item: 'Choose the base collection.'
        E         Use -v to get more diff
    """
    assert form_errors(_FILLED) == ()

    no_base = FormInputs(**{**_FILLED.__dict__, "base_path": ""})
    assert form_errors(no_base) == ("Choose the base collection.",)

    no_input = FormInputs(**{**_FILLED.__dict__, "input_path": ""})
    assert form_errors(no_input) == ("Choose an input.",)

    no_name = FormInputs(**{**_FILLED.__dict__, "name": ""})
    assert form_errors(no_name) == ("Name the playlist.",)


def test_form_errors_reports_every_missing_field_together():
    """A form missing all three required fields reports all three
    refusals, in the order the form reads top to bottom.

    Made to fail by mutating form_errors to stop after the first
    refusal found (an early return), which would silently drop the
    other two. Observed:
        E       AssertionError: assert ('Choose the ...collection.',) == ('Choose the ...he playlist.')
        E
        E         Right contains 2 more items, first extra item: 'Choose an input.'
        E         Use -v to get more diff
    """
    empty = FormInputs(
        base_path="",
        input_path="",
        name="",
        output_dir="",
        playlist_folder="",
        allow_unmatched=False,
        full_collection=False,
    )
    assert form_errors(empty) == (
        "Choose the base collection.",
        "Choose an input.",
        "Name the playlist.",
    )


def test_unresolved_report_rows_covers_all_kinds():
    """One tuple per unresolved_rows entry, in the same order, covering
    all three UnresolvedRow.kind values: unparseable, unmatched,
    ambiguous.

    Mutation: unresolved_report_rows builds
    `(row.line_number, row.raw_text)`, dropping the kind field. Observed:
        E       AssertionError: assert ((3, ''), (7,... (9, 'B - U')) == ((3, '', 'unp... 'ambiguous'))
        E
        E         At index 0 diff: (3, '') != (3, '', 'unparseable')
        E         Use -v to get more diff
    """
    result = BuildPlaylistResult(
        output=None,
        stats={},
        unresolved_rows=[
            UnresolvedRow(line_number=3, raw_text="", artist="", title="", kind="unparseable"),
            UnresolvedRow(line_number=7, raw_text="A - T", artist="A", title="T", kind="unmatched"),
            UnresolvedRow(line_number=9, raw_text="B - U", artist="B", title="U", kind="ambiguous"),
        ],
        errors=["unresolved_tracks"],
    )
    assert unresolved_report_rows(result) == (
        (3, "", "unparseable"),
        (7, "A - T", "unmatched"),
        (9, "B - U", "ambiguous"),
    )


def test_unresolved_report_rows_is_empty_for_a_clean_run():
    """A result with no unresolved_rows reports an empty tuple rather
    than raising or fabricating a row.

    Mutation: unresolved_report_rows returns `((0, '', ''),)` whatever
    the result holds. Observed:
        E       AssertionError: assert ((0, '', ''),) == ()
        E
        E         Left contains one more item: (0, '', '')
        E         Use -v to get more diff
    """
    clean = BuildPlaylistResult(
        output="<NML/>", stats={"entries_written": 1, "playlist_name": "x"}, unresolved_rows=[], errors=[]
    )
    assert unresolved_report_rows(clean) == ()


def test_run_summary_names_unresolved_tracks():
    """An aborted run naming unresolved_tracks states how many
    track-list lines did not resolve, with the count word matching
    wording.plural.

    Made to fail by mutating run_summary to read
    len(result.errors) instead of len(result.unresolved_rows) for the
    count. Observed:
        E       AssertionError: assert 'Not written:...tched is off.' == 'Not written:...tched is off.'
        E
        E         - Not written: 2 entries did not resolve and Allow unmatched is off.
        E         ?              ^     ^^^
        E         + Not written: 1 entry did not resolve and Allow unmatched is off.
        E         ?              ^     ^
    """
    result = BuildPlaylistResult(
        output=None,
        stats={},
        unresolved_rows=[
            UnresolvedRow(line_number=1, raw_text="x", artist="", title="", kind="unmatched"),
            UnresolvedRow(line_number=2, raw_text="y", artist="", title="", kind="ambiguous"),
        ],
        errors=["unresolved_tracks"],
    )
    summary = run_summary(result)
    assert summary == "Not written: 2 entries did not resolve and Allow unmatched is off."


def test_run_summary_names_unresolved_tracks_singular():
    """The same condition with exactly one unresolved line reads the
    singular word, not "1 lines".

    Made to fail by mutating run_summary to always use the plural word
    regardless of count. Observed:
        E       AssertionError: assert '1 entry ' in 'Not written: 1 entries did not resolve and Allow unmatched is off.'
        E        +  where 'Not written: 1 entries did not resolve and Allow unmatched is off.' = run_summary(BuildPlaylistResult(output=None, stats={}, unresolved_rows=[UnresolvedRow(line_number=1, raw_text='x', artist='', title='', kind='unmatched')], errors=['unresolved_tracks']))
    """
    result = BuildPlaylistResult(
        output=None,
        stats={},
        unresolved_rows=[
            UnresolvedRow(line_number=1, raw_text="x", artist="", title="", kind="unmatched"),
        ],
        errors=["unresolved_tracks"],
    )
    assert "1 entry " in run_summary(result)
    assert "entries" not in run_summary(result)


def test_run_summary_names_no_entries_resolved():
    """An aborted run naming no_entries_resolved states that no line
    resolved, distinct from the unresolved_tracks wording.

    Made to fail by mutating run_summary to return the
    unresolved_tracks sentence for this condition too. Observed:
        E       AssertionError: assert 'Not written:...tched is off.' == 'Not written:...e collection.'
        E
        E         - Not written: no entry resolved against the base collection.
        E         + Not written: 0 entries did not resolve and Allow unmatched is off.
    """
    result = BuildPlaylistResult(
        output=None, stats={}, unresolved_rows=[], errors=["no_entries_resolved"]
    )
    summary = run_summary(result)
    assert summary == "Not written: no entry resolved against the base collection."


def test_run_summary_names_a_target_folder_error():
    """An aborted run naming a target-folder error (any of the four
    shapes buildplaylist._find_target_subnodes returns, or the
    parameterised target_folder_ambiguous=...) states that the target
    folder could not be resolved and names the underlying error.

    Made to fail by mutating run_summary to fall through to the
    generic '; '.join(errors) sentence for this case. Observed:
        E           AssertionError: assert 'Not written:...oot_subnodes.' == 'Not written:...ot_subnodes).'
        E
        E             - Not written: the playlist folder could not be resolved (no_root_subnodes).
        E             + Not written: no_root_subnodes.
    """
    for error in (
        "no_root_subnodes",
        "root_subnodes_span_not_found",
        "target_folder_not_found",
        "target_folder_no_subnodes",
        "target_folder_ambiguous=Sets:count=2",
    ):
        result = BuildPlaylistResult(output=None, stats={}, unresolved_rows=[], errors=[error])
        assert run_summary(result) == f"Not written: the playlist folder could not be resolved ({error})."


def test_run_summary_aborted_and_written():
    """An aborted run and a written run read distinguishably: the
    aborted sentence never mentions entries_written, and the written
    sentence names the final playlist_name and the count of tracks
    added, in the singular for a count of one.

    Made to fail by mutating run_summary to omit the final
    playlist_name from the written sentence. Observed:
        AssertionError: assert 'Warehouse set' in 'Written: with 3
        tracks.'
    """
    written = BuildPlaylistResult(
        output="<NML/>",
        stats={"entries_written": 3, "playlist_name": "Warehouse set"},
        unresolved_rows=[],
        errors=[],
    )
    summary = run_summary(written)
    assert summary == 'Written: "Warehouse set" with 3 tracks.'

    written_one = BuildPlaylistResult(
        output="<NML/>",
        stats={"entries_written": 1, "playlist_name": "Solo"},
        unresolved_rows=[],
        errors=[],
    )
    assert run_summary(written_one) == 'Written: "Solo" with 1 track.'


def test_run_summary_names_format_and_encoding_for_each_format():
    """csv and m3u runs append the format and codec, a folder run the
    format alone, and a text run nothing, for written and aborted runs
    alike (DL-280, DL-296).

    Mutation: _read_note returns '' for every format, so the CSV run's
        summary lacks ' Read as CSV, cp1252.'.
    Observed:
        E       assert 'Written: "L" with 1 track.' == 'Written: "L"... CSV, cp1252.'
        E
        E         - Written: "L" with 1 track. Read as CSV, cp1252.
        E         + Written: "L" with 1 track.
    """
    written = BuildPlaylistResult(output="<NML/>", stats={"entries_written": 1, "playlist_name": "L"})
    aborted = BuildPlaylistResult(
        output=None, stats={},
        unresolved_rows=[UnresolvedRow(1, "x", "", "", "unmatched"), UnresolvedRow(2, "y", "", "", "ambiguous"),
                         UnresolvedRow(3, "z", "", "", "unparseable")],
        errors=["unresolved_tracks"],
    )
    assert run_summary(written, InputFormat.CSV, "cp1252") == 'Written: "L" with 1 track. Read as CSV, cp1252.'
    assert run_summary(written, InputFormat.M3U, "utf-8-sig") == 'Written: "L" with 1 track. Read as M3U, utf-8-sig.'
    assert run_summary(written, InputFormat.FOLDER, "n/a") == 'Written: "L" with 1 track. Read as Folder.'
    assert run_summary(written, InputFormat.TEXT, "utf-8-sig") == 'Written: "L" with 1 track.'
    assert run_summary(aborted, InputFormat.CSV, "cp1252") == (
        "Not written: 3 entries did not resolve and Allow unmatched is off. Read as CSV, cp1252."
    )


def test_playlist_folder_options_disable_shared_names():
    """The root comes first with value "", a unique folder offers its
    NAME, and a shared-name folder is listed disabled with no value.

    Mutation: playlist_folder_options passes enabled=True for every
        folder, so the shared-name 'Warmup' option reads enabled.
    Observed:
        E       assert [True, True, True] == [True, True, False]
        E
        E         At index 2 diff: True != False
        E         Use -v to get more diff
    """
    options = playlist_folder_options([
        PlaylistFolderChoice("Sets\\2026", "2026", True),
        PlaylistFolderChoice("Archive\\Warmup", "Warmup", False),
    ])
    assert [(o.label, o.value) for o in options] == [
        ("Collection root", ""), ("Sets\\2026", "2026"), ("Archive\\Warmup (name also used elsewhere)", ""),
    ]
    assert [o.enabled for o in options] == [True, True, False]


def test_playlist_folder_is_dropped_without_full_collection():
    """With Full collection off the selection never reaches the run.

    Mutation: effective_playlist_folder returns selected
        unconditionally, so effective_playlist_folder(False, 'Sets')
        returns 'Sets' in place of ''.
    Observed:
        E       AssertionError: assert 'Sets' == ''
        E
        E         + Sets
    """
    from traktor_nml.gui.buildplaylist_view import effective_playlist_folder

    assert effective_playlist_folder(False, "Sets") == ""
    assert effective_playlist_folder(True, "Sets") == "Sets"


def test_csv_columns_note_matches_the_artboard():
    """The note beside the CSV template names the required and optional
    columns in the artboard's exact wording (DL-071).

    Mutation: csv_columns_note drops 'File name' from the optional
        columns, so the note reads 'Album and Duration are optional' and
        differs from the artboard's wording.
    Observed:
        E       AssertionError: assert 'Artist and T...ore strictly.' == 'Artist and T...ore strictly.'
        E
        E         - Artist and Title are required. Album, Duration and File name are optional and help a row match more strictly.
        E         ?                                     ^          --------------
        E         + Artist and Title are required. Album and Duration are optional and help a row match more strictly.
        E         ?                                     ^^^^
    """
    assert csv_columns_note() == (
        "Artist and Title are required. Album, Duration and File name are optional "
        "and help a row match more strictly."
    )

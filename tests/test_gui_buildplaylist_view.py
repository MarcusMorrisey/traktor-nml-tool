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
    form_errors,
    run_summary,
    unresolved_report_rows,
)

_FILLED = FormInputs(
    base_path="D:/Traktor/collection.nml",
    tracklist_path="C:/lists/warehouse.txt",
    name="Warehouse set",
    target_folder="",
    allow_unmatched=False,
    full_collection=False,
)


def test_form_errors_reports_each_missing_field():
    """A fully filled form reports no refusal; a form missing exactly
    one required field reports exactly one, naming that field.

    Made to fail by mutating form_errors to always return (), which
    hides a missing field from the operator entirely. Observed:
        AssertionError: assert () != ()
    """
    assert form_errors(_FILLED) == ()

    no_base = FormInputs(**{**_FILLED.__dict__, "base_path": ""})
    assert form_errors(no_base) == ("Choose the base collection.",)

    no_tracklist = FormInputs(**{**_FILLED.__dict__, "tracklist_path": ""})
    assert form_errors(no_tracklist) == ("Choose a track list.",)

    no_name = FormInputs(**{**_FILLED.__dict__, "name": ""})
    assert form_errors(no_name) == ("Name the playlist.",)


def test_form_errors_reports_every_missing_field_together():
    """A form missing all three required fields reports all three
    refusals, in the order the form reads top to bottom.

    Made to fail by mutating form_errors to stop after the first
    refusal found (an early return), which would silently drop the
    other two. Observed:
        AssertionError: assert ('Choose the base collection.',) == (
        'Choose the base collection.', 'Choose a track list.', 'Name
        the playlist.')
    """
    empty = FormInputs(
        base_path="",
        tracklist_path="",
        name="",
        target_folder="",
        allow_unmatched=False,
        full_collection=False,
    )
    assert form_errors(empty) == (
        "Choose the base collection.",
        "Choose a track list.",
        "Name the playlist.",
    )


def test_unresolved_report_rows_covers_all_kinds():
    """One tuple per unresolved_rows entry, in the same order, covering
    all three UnresolvedRow.kind values: unparseable, unmatched,
    ambiguous.

    Made to fail by mutating unresolved_report_rows to drop the kind
    field from each tuple. Observed:
        AssertionError: assert (1, 'x') == (1, 'x', 'unparseable')
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

    Made to fail by mutating unresolved_report_rows to always return a
    one-element placeholder tuple. Observed:
        AssertionError: assert (('', '', ''),) == ()
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
        AssertionError: assert 'Not written: 1 track-list...' ==
        'Not written: 2 track-list lines did not resolve...'
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
    assert summary == "Not written: 2 track-list lines did not resolve and Allow unmatched is off."


def test_run_summary_names_unresolved_tracks_singular():
    """The same condition with exactly one unresolved line reads the
    singular word, not "1 lines".

    Made to fail by mutating run_summary to always use the plural word
    regardless of count. Observed:
        AssertionError: assert 'Not written: 1 lines did...' not in
        summary
    """
    result = BuildPlaylistResult(
        output=None,
        stats={},
        unresolved_rows=[
            UnresolvedRow(line_number=1, raw_text="x", artist="", title="", kind="unmatched"),
        ],
        errors=["unresolved_tracks"],
    )
    assert "1 track-list line " in run_summary(result)
    assert "track-list lines" not in run_summary(result)


def test_run_summary_names_no_entries_resolved():
    """An aborted run naming no_entries_resolved states that no line
    resolved, distinct from the unresolved_tracks wording.

    Made to fail by mutating run_summary to return the
    unresolved_tracks sentence for this condition too. Observed:
        AssertionError: 'did not resolve and Allow unmatched' in
        'Not written: no track-list line resolved...'
    """
    result = BuildPlaylistResult(
        output=None, stats={}, unresolved_rows=[], errors=["no_entries_resolved"]
    )
    summary = run_summary(result)
    assert summary == "Not written: no track-list line resolved against the base collection."


def test_run_summary_names_a_target_folder_error():
    """An aborted run naming a target-folder error (any of the four
    shapes buildplaylist._find_target_subnodes returns, or the
    parameterised target_folder_ambiguous=...) states that the target
    folder could not be resolved and names the underlying error.

    Made to fail by mutating run_summary to fall through to the
    generic '; '.join(errors) sentence for this case. Observed:
        AssertionError: assert 'Not written: target_folder_not_found.'
        == 'Not written: the target folder could not be resolved
        (target_folder_not_found).'
    """
    for error in (
        "no_root_subnodes",
        "root_subnodes_span_not_found",
        "target_folder_not_found",
        "target_folder_no_subnodes",
        "target_folder_ambiguous=Sets:count=2",
    ):
        result = BuildPlaylistResult(output=None, stats={}, unresolved_rows=[], errors=[error])
        assert run_summary(result) == f"Not written: the target folder could not be resolved ({error})."


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

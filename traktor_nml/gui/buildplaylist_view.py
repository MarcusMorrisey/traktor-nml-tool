"""The build-playlist screen's form validation and report shaping, with
no framework import.

Nicegui-free view model for `/build-playlist`, on the
`review_model.py`/`wizard_state.py` precedent (DL-069, DL-261): the
screen's write path drives `buildplaylist.assemble_output` directly
(DL-262), and everything reducible to data or arithmetic over its
inputs and its result - which refusals a Continue-equivalent control
shows, how an unresolved line becomes a report row, and what sentence
the write step shows for either an aborted or a written run - lives
here rather than in `app.py`'s wiring, so the system pytest interpreter
(no `nicegui` installed) reaches it directly.

`run_summary` tracks `build_playlist_cmd.py`'s own condition names
(`unresolved_tracks`, `no_entries_resolved`, a target-folder error,
`entries_written`) rather than inventing separate GUI phrasing (DL-268):
an operator using both surfaces reads the same words for the same
condition. A failed read/parse or write surfaces through the same
sentence path rather than an uncaught exception (DL-269).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..buildplaylist import BuildPlaylistResult
from ..playlistinput import CSV_COLUMNS, InputFormat
from ..playlists import PlaylistFolderChoice
from .wording import plural


@dataclass(frozen=True)
class FormInputs:
    """The build-playlist form's fields, read the moment Write is
    checked. base_path and input_path are the chosen paths - input_path
    a file or a folder - or the empty string when nothing has been
    chosen; name is the playlist-name field. output_dir is the disk
    folder the .nml is written to, empty for the base collection's own
    folder; playlist_folder is the NAME of the collection FOLDER the
    playlist is placed under, empty for the collection root. The two
    never share a value: one is a place on disk, the other a place in
    the collection's playlist tree (DL-297)."""

    base_path: str
    input_path: str
    name: str
    output_dir: str
    playlist_folder: str
    allow_unmatched: bool
    full_collection: bool


def form_errors(inputs: FormInputs) -> tuple[str, ...]:
    """The refusal strings a Continue-equivalent control checks before a
    run starts: one for a missing base path, one for a missing input,
    one for a missing name. Order matches the order the form itself
    reads top to bottom. output_dir, playlist_folder, allow_unmatched
    and full_collection carry no refusal of their own: each has a
    default meaning when left empty."""
    errors = []
    if not inputs.base_path:
        errors.append("Choose the base collection.")
    if not inputs.input_path:
        errors.append("Choose an input.")
    if not inputs.name:
        errors.append("Name the playlist.")
    return tuple(errors)


_FORMAT_LABELS = {
    InputFormat.TEXT: "Text",
    InputFormat.CSV: "CSV",
    InputFormat.M3U: "M3U",
    InputFormat.FOLDER: "Folder",
}


def format_label(fmt: InputFormat) -> str:
    """The label the input card's format tag shows, as the artboard
    draws it."""
    return _FORMAT_LABELS[fmt]


def csv_columns_note() -> str:
    """The CSV note's sentence, built from CSV_COLUMNS so the screen and
    the template can never name different columns (DL-284)."""
    required = [column.header for column in CSV_COLUMNS if column.required]
    optional = [column.header for column in CSV_COLUMNS if not column.required]
    return (
        f"{' and '.join(required)} are required. {', '.join(optional[:-1])} and {optional[-1]} "
        "are optional and help a row match more strictly."
    )


COLLECTION_ROOT_LABEL = "Collection root"

# Appended to a shared-name folder's label. The page's disable predicate
# matches on it, because NiceGUI hands the browser each option's label and
# its index, never its key.
SHARED_NAME_SUFFIX = " (name also used elsewhere)"

# Shown under the disabled playlist-folder chooser. With Full collection
# off the isolation pass (split.build_output) keeps only the new PLAYLIST
# node under the root, so a playlist folder would change nothing in the
# written file; the chooser says so rather than accepting a choice it
# ignores (DL-297).
PLAYLIST_FOLDER_NEEDS_FULL_COLLECTION = (
    "Playlist folder applies only with Full collection on. "
    "Off, the file holds this one playlist at its root."
)


def effective_playlist_folder(full_collection: bool, selected: str) -> str:
    """The playlist folder a run passes on: the selection with Full
    collection on, "" (the collection root) with it off, where the
    isolated output has no folder tree for the playlist to sit in."""
    return selected if full_collection else ""


@dataclass(frozen=True)
class PlaylistFolderOption:
    """One entry in the playlist-folder chooser: the label shown, the
    value a run passes as target_folder, and whether it can be chosen
    (DL-297)."""

    label: str
    value: str  # the NAME passed as target_folder; "" for the collection root
    enabled: bool


def playlist_folder_options(choices: list[PlaylistFolderChoice]) -> list[PlaylistFolderOption]:
    """The playlist-folder chooser's options: the collection root first,
    then every folder in the order choices holds them, each labelled by
    its path. A folder whose NAME another folder shares
    is listed disabled, because assemble_output resolves target_folder
    by NAME and would refuse it as target_folder_ambiguous (DL-297)."""
    options = [PlaylistFolderOption(COLLECTION_ROOT_LABEL, "", True)]
    for choice in choices:
        label = choice.path if choice.unique else f"{choice.path}{SHARED_NAME_SUFFIX}"
        options.append(PlaylistFolderOption(label, choice.name if choice.unique else "", choice.unique))
    return options


def unresolved_report_rows(
    result: BuildPlaylistResult,
) -> tuple[tuple[int, str, str], ...]:
    """Shape result.unresolved_rows into the (line_number, raw_text,
    kind) tuples the report table renders, preserving input order -
    unresolved_rows is already sorted back into document order by
    assemble_output, so this reorders nothing of its own."""
    return tuple(
        (row.line_number, row.raw_text, row.kind) for row in result.unresolved_rows
    )


def _target_folder_error(errors: tuple[str, ...]) -> Optional[str]:
    """The one error string among a target-folder lookup's four shapes
    (no_root_subnodes, root_subnodes_span_not_found,
    target_folder_not_found, target_folder_no_subnodes,
    target_folder_ambiguous=...), or None when errors names none of
    them. assemble_output returns exactly one error in this family per
    aborted run, never combined with unresolved_tracks or
    no_entries_resolved (ref: buildplaylist._find_target_subnodes)."""
    folder_errors = (
        "no_root_subnodes",
        "root_subnodes_span_not_found",
        "target_folder_not_found",
        "target_folder_no_subnodes",
    )
    for error in errors:
        if error in folder_errors or error.startswith("target_folder_ambiguous="):
            return error
    return None


def _read_note(input_format: Optional[InputFormat], input_encoding: str) -> str:
    """' Read as CSV, cp1252.' for a run on csv or m3u input, ' Read as
    Folder.' for a folder, and nothing for text: only a run on CSV, M3U or
    folder input names what it read (DL-296). The codec is named because a cp1252 fallback
    misreads another codepage without an error (DL-283)."""
    if input_format is None or input_format is InputFormat.TEXT:
        return ""
    if input_format is InputFormat.FOLDER:
        return f" Read as {format_label(input_format)}."
    return f" Read as {format_label(input_format)}, {input_encoding}."


def run_summary(
    result: BuildPlaylistResult,
    input_format: Optional[InputFormat] = None,
    input_encoding: str = "",
) -> str:
    """The single sentence the write step shows, covering both an
    aborted run and a written one. Tracks build_playlist_cmd.py's own
    condition names rather than inventing separate GUI phrasing
    (DL-268): unresolved_tracks, no_entries_resolved, a playlist-folder
    error, or entries_written naming the final playlist_name. Counts are
    read off result (DL-215) and the words are format-neutral, since an
    entry may be a line, a CSV row, a playlist path or a file (DL-296)."""
    return _outcome_sentence(result) + _read_note(input_format, input_encoding)


def _outcome_sentence(result: BuildPlaylistResult) -> str:
    if result.output is None:
        if "unresolved_tracks" in result.errors:
            unresolved = len(result.unresolved_rows)
            entries = plural(unresolved, "entry", "entries")
            return (
                f"Not written: {unresolved} {entries} did not "
                "resolve and Allow unmatched is off."
            )
        if "no_entries_resolved" in result.errors:
            return "Not written: no entry resolved against the base collection."
        folder_error = _target_folder_error(result.errors)
        if folder_error is not None:
            return f"Not written: the playlist folder could not be resolved ({folder_error})."
        return f"Not written: {'; '.join(result.errors)}."

    entries = result.stats.get("entries_written", 0)
    name = result.stats.get("playlist_name")
    tracks = plural(entries, "track", "tracks")
    return f"Written: \"{name}\" with {entries} {tracks}."

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
from .wording import plural


@dataclass(frozen=True)
class FormInputs:
    """The build-playlist form's fields, read the moment Write is
    checked. base_path and tracklist_path are the chosen file paths or
    the empty string when nothing has been chosen yet; name is the
    playlist-name field; target_folder is the optional target-folder
    field or the empty string when left blank."""

    base_path: str
    tracklist_path: str
    name: str
    target_folder: str
    allow_unmatched: bool
    full_collection: bool


def form_errors(inputs: FormInputs) -> tuple[str, ...]:
    """The refusal strings a Continue-equivalent control checks before a
    run starts: one for a missing base path, one for a missing
    tracklist path, one for a missing name. Order matches the order the
    form itself reads top to bottom. An otherwise-filled FormInputs
    reports none - target_folder, allow_unmatched and full_collection
    carry no refusal of their own, since every value either is valid."""
    errors = []
    if not inputs.base_path:
        errors.append("Choose the base collection.")
    if not inputs.tracklist_path:
        errors.append("Choose a track list.")
    if not inputs.name:
        errors.append("Name the playlist.")
    return tuple(errors)


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


def run_summary(result: BuildPlaylistResult) -> str:
    """The single sentence the write step shows, covering both an
    aborted run and a written one. Tracks build_playlist_cmd.py's own
    condition names rather than inventing separate GUI phrasing
    (DL-268): unresolved_tracks, no_entries_resolved, a target-folder
    error, or entries_written naming the final playlist_name."""
    if result.output is None:
        if "unresolved_tracks" in result.errors:
            unresolved = len(result.unresolved_rows)
            lines = plural(unresolved, "line", "lines")
            return (
                f"Not written: {unresolved} track-list {lines} did not "
                "resolve and Allow unmatched is off."
            )
        if "no_entries_resolved" in result.errors:
            return "Not written: no track-list line resolved against the base collection."
        folder_error = _target_folder_error(result.errors)
        if folder_error is not None:
            return f"Not written: the target folder could not be resolved ({folder_error})."
        return f"Not written: {'; '.join(result.errors)}."

    entries = result.stats.get("entries_written", 0)
    name = result.stats.get("playlist_name")
    tracks = plural(entries, "track", "tracks")
    return f"Written: \"{name}\" with {entries} {tracks}."

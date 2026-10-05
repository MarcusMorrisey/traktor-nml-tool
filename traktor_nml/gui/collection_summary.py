"""What the reconstruct page's set-up step says about a collection it
has been given, with no framework import.

`Reconstruct.dc.html` reports each chosen file rather than only naming
it: the collection being repaired reads its track count, its playlist
count and how many of those playlists hold nothing, and each source
reads how many playlists it has contents for. Those counts are what make
the choice checkable before the run - a source with no filled playlists
supplies nothing, and a base with no empty playlists has nothing to
repair - so they are derived here from the parsed collection and printed
by `app.py`.

The counts are taken off the collection itself, not off a run: the set-up
step stands before any run exists. What a run reports is
`reconstruct_report.py`'s, and the two are separate because a number that
described the file at the moment it was chosen and a number the run
produced are different claims (DL-220).

The step list the right column prints is derived from
`reconstruct_steps.STEPS`, so a step number stands in one table rather
than in two (DL-221).

No nicegui import, so a guard under the system interpreter runs every
rule in this file (DL-069).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..model import collection_entries
from ..playlists import find_playlist_nodes, node_primary_keys
from . import reconstruct_steps
from .wording import plural


@dataclass(frozen=True)
class CollectionSummary:
    """One collection as the set-up step reports it: how many tracks it
    holds, how many playlists it carries, and how many of those hold
    nothing."""

    tracks: int
    playlists: int
    empty: int

    @property
    def filled(self) -> int:
        """The playlists holding something. Derived rather than counted
        again, so the two counts cannot disagree about the same file."""
        return self.playlists - self.empty

    @property
    def repair_phrases(self) -> tuple[str, ...]:
        """The phrases ``Reconstruct.dc.html:112`` prints under the
        collection being repaired, in the order it draws them.

        The empty count is the reason this page exists, so it is stated
        in both directions: a collection with empty playlists says how
        many, and one with none says so rather than printing a zero the
        reader has to interpret.
        """
        empty = (
            f"{self.empty} of them empty"
            if self.empty
            else "none of them empty"
        )
        return (
            f"{self.tracks:,} {plural(self.tracks, 'track', 'tracks')}",
            f"{self.playlists:,} "
            f"{plural(self.playlists, 'playlist', 'playlists')}",
            empty,
            "this file is never modified",
        )

    @property
    def source_note(self) -> str:
        """What ``Reconstruct.dc.html:121`` prints at the right of a
        source's own row: how many playlists it could supply contents
        from. A source with none is what the row exists to make visible,
        so it says so rather than reading ``0 playlists with contents``."""
        if not self.filled:
            return "no playlists with contents"
        playlists = plural(self.filled, "playlist", "playlists")
        return f"{self.filled:,} {playlists} with contents"


def summarise(root) -> CollectionSummary:
    """The summary of one parsed collection.

    A playlist is empty where it carries no PRIMARYKEY, which is the same
    reading `splice.py` takes when it decides which playlists a
    reconstruction refilled: a NODE holding a PLAYLIST element with no
    entries under it holds nothing, whatever ENTRIES attribute the
    element declares. The attribute is not read here for that reason - a
    file whose declared count disagrees with its own entries would be
    reported by the count it does not hold.
    """
    nodes = find_playlist_nodes(root)
    return CollectionSummary(
        tracks=len(collection_entries(root)),
        playlists=len(nodes),
        empty=sum(1 for node in nodes if not node_primary_keys(node)),
    )


@dataclass(frozen=True)
class NextStep:
    """One row of the set-up step's own account of what follows: the step
    number, what happens at it, and the sentence saying how."""

    number: int
    title: str
    detail: str


# What `Reconstruct.dc.html:167-171` lists at the right: the three steps
# after this one, each numbered by the step it names. The numbers are
# reconstruct_steps' own, so the rail and this list cannot disagree about
# which step resolves the conflicts (DL-221).
NEXT_STEPS: tuple[NextStep, ...] = (
    NextStep(
        number=reconstruct_steps.PREVIEW,
        title="The repair is previewed",
        detail=(
            "Every playlist is rebuilt in memory and counted back to you - "
            "how many were filled and how many tracks each gained. Nothing "
            "is written."
        ),
    ),
    NextStep(
        number=reconstruct_steps.RESOLVE,
        title="You resolve the disagreements",
        detail=(
            "Where two collections hold the same track with different "
            "values, every answer is shown and you pick which one supplies "
            "it."
        ),
    ),
    NextStep(
        number=reconstruct_steps.WRITE,
        title="You confirm the write",
        detail=(
            "A new collection file is written only after you confirm. The "
            "collection you are repairing is left exactly as it is."
        ),
    ),
)

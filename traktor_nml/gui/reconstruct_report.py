"""What the reconstruct page's preview and write steps report, derived
from a held run with no framework import.

`Preview.dc.html` and `Write.dc.html` draw two screens whose every number
is a count of something the run reported: how many empty playlists were
filled, how many entries that added, which playlists the run could not
fill, what the output file will hold, and which collections it read
without touching. This module turns one SpliceResult's stats and the
operator's decisions into those records, and `app.py` renders them.

Every sentence a screen prints is a property here rather than a string
formatted at a call site, for the reason DL-215 states: a count computed
for a sentence and a count computed again for the row beside it can
disagree, and the disagreement shows as a screen contradicting itself.
The run is the authority for all of them (DL-204, DL-215).

The listing is truncated here rather than in the render: `Preview.dc.html`
draws nine rows and a tenth summarising the rest, so the count in that
tenth row and the rows above it are one division of one list, made once
(DL-217).

No nicegui import, so a guard under the system interpreter runs every
rule in this file (DL-069).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence

from . import conflict_model

# How many playlists `Preview.dc.html:110-118` lists by name before the
# row at :119 stands for the rest. The artboard draws nine named rows and
# one summary row; a run with nine or fewer playlists draws no summary
# row at all, because there is nothing left for it to stand for.
LISTED_PLAYLISTS = 9

# The tone tokens a write-step change row carries, naming what the row
# reports rather than a colour: `Write.dc.html:111,116,121` paint the
# three counts a run adds in the found hue and :126's count of playlists
# it left alone in the muted one. Which ink each token wears is
# theme.py's to settle (DL-069, DL-188).
TONE_ADDED = "added"
TONE_UNTOUCHED = "untouched"


@dataclass(frozen=True)
class PlaylistRow:
    """One `.pl` row: a playlist's name and how many entries it holds
    after the run. `Preview.dc.html:110` draws the pair."""

    name: str
    entries: int

    @property
    def entry_count(self) -> str:
        """The row's right-hand cell. `Preview.dc.html:110` prints the
        unit beside the number, so a row reading `214` alone would leave
        the reader to guess what was counted."""
        return f"{self.entries:,} entries"


@dataclass(frozen=True)
class ChangeRow:
    """One `.cr` row on the write step: what the new file will hold,
    the sentence under it saying how, the count, and the tone that count
    reads at (`Write.dc.html:108-127`)."""

    label: str
    detail: str
    count: int
    tone: str

    @property
    def amount(self) -> str:
        """The count as the row prints it, grouped at the thousand the
        way `Write.dc.html:116` draws `4,912`."""
        return f"{self.count:,}"


@dataclass(frozen=True)
class PreviewReport:
    """What step 2 shows: the playlists the run filled, the entries that
    added, the ones it could not fill, and how many tracks are held
    differently by more than one collection.

    listed and remainder are one division of the filled list: remainder
    is None where every filled playlist is listed by name.
    """

    listed: tuple[PlaylistRow, ...]
    remainder: Optional[PlaylistRow]
    filled: int
    empty: int
    entries_added: int
    unfilled: tuple[str, ...]
    conflicts: int
    outstanding: int

    @property
    def filled_caption(self) -> str:
        """The card head's label: how many of the empty playlists this
        run filled. `Preview.dc.html:107` prints both numbers, because
        the count filled means nothing without the count there were."""
        return f"{self.filled} of {self.empty} empty playlists"

    @property
    def conflict_sentence(self) -> str:
        """The note at `Preview.dc.html:127`, or the empty string for a
        run that reported no divergence at all.

        Both counts are read off the same decisions the resolve step
        holds, so the sentence says what that step would say: a preview
        naming decisions still to be made over a step where every one has
        an answer is the screen contradicting the step it points at, and
        a preview promising more decisions than the step offers is the
        same failure in the other direction (DL-215, DL-219).
        """
        if not self.conflicts:
            return ""
        if not self.outstanding:
            held = "track" if self.conflicts == 1 else "tracks"
            return (
                f"Every one of the {self.conflicts} {held} held "
                "differently by more than one collection has an answer. "
                "Step 3 is where those answers are changed."
            )
        held, each = (
            ("track is", "It has")
            if self.outstanding == 1
            else ("tracks are", "Each one has")
        )
        return (
            f"{self.outstanding} {held} held differently by more than one "
            f"collection with no answer yet. {each} to be decided before "
            "anything can be written. That is step 3."
        )

    @property
    def total_sentence(self) -> str:
        """The `.tot` strip's label at `Preview.dc.html:123`."""
        return "Entries that would be added"

    @property
    def total_amount(self) -> str:
        """The `.tot` strip's number, grouped at the thousand."""
        return f"{self.entries_added:,}"

    @property
    def unfilled_title(self) -> str:
        """The head of the card listing what the run could not fill
        (`Preview.dc.html:141`). The count is in the title because the
        card is the count: a run that filled everything draws no card."""
        one = self.unfilled_count == 1
        return (
            f"The {self.unfilled_count} it could not fill"
            if not one
            else "The one it could not fill"
        )

    @property
    def unfilled_count(self) -> int:
        return len(self.unfilled)


@dataclass(frozen=True)
class WriteReport:
    """What step 4 shows before anything is written: where the output
    goes, whether that path already exists, what the new file will hold,
    and which collections the run read without modifying."""

    destination: str
    destination_exists: bool
    rows: tuple[ChangeRow, ...]
    tracks_total: int
    originals: tuple[str, ...]

    @property
    def destination_badge(self) -> str:
        """The badge beside the path at `Write.dc.html:98`. A path that
        already exists is said so plainly rather than left unsaid: the
        write replaces it, and the operator is the one who decides
        whether that is what they meant."""
        return "Already exists" if self.destination_exists else "Does not exist yet"

    @property
    def total_sentence(self) -> str:
        """The `.tot` strip at `Write.dc.html:129`."""
        return "Tracks in the collection the new file holds"

    @property
    def total_amount(self) -> str:
        return f"{self.tracks_total:,}"

    @property
    def confirm_question(self) -> str:
        """The confirmation dialog's own heading at `Write.dc.html:162`.

        It names the count of playlists being filled, which is the first
        change row's count read off the row rather than recounted, so the
        dialog cannot promise a number the list beside it does not carry
        (DL-215).
        """
        filled = self.rows[0].count if self.rows else 0
        playlists = "playlist" if filled == 1 else "playlists"
        return f"Write {filled} rebuilt {playlists}?"


@dataclass(frozen=True)
class PreviewRefusal:
    """What step 2 shows for a run that assembled nothing.

    A refused run reports why it stopped, and the page has to say both
    what stopped it and what settles it: the conflict abort is not a
    failure but a question, and the step that answers it is the next one
    (DL-226).
    """

    conflicts: int
    reasons: tuple[str, ...]

    @property
    def title(self) -> str:
        """The card's own head. A run stopped by conflicts stopped on a
        question; a run stopped by anything else stopped on an error, and
        the two do not read alike."""
        if self.conflicts and not self.reasons:
            return "Nothing was assembled yet"
        return "The repair could not be assembled"

    @property
    def sentence(self) -> str:
        """What stopped the run, and which step settles it.

        The count is the group count the run itself reported, so the
        sentence and the rows the resolve step offers are the one set
        (DL-215).
        """
        if not self.conflicts:
            return (
                "The run stopped on what it read. Nothing was written, and "
                "the reasons it gave are below."
            )
        held = "track is" if self.conflicts == 1 else "tracks are"
        return (
            f"{self.conflicts} {held} held differently by more than one "
            "collection, and the repair cannot be assembled until every one "
            "has an answer. Continue to resolve names each one and offers "
            "its answers."
        )

    @property
    def has_reasons(self) -> bool:
        return bool(self.reasons)


def preview_refusal(errors, groups) -> PreviewRefusal:
    """The step 2 record for a run that produced no output.

    The conflict abort's own token is dropped from the reasons: the rows
    it stands for are the groups beside it, and printing the token as
    well would name the same stop twice, once in the sentence and once as
    a machine word the operator cannot act on (DL-226).
    """
    return PreviewRefusal(
        conflicts=len(groups),
        reasons=tuple(
            error
            for error in errors
            if error != conflict_model.CONFLICT_ABORT_TOKEN
        ),
    )


def preview_report(
    stats: Mapping[str, object],
    groups: Sequence[conflict_model.ConflictGroup],
    decisions: conflict_model.ConflictDecisions,
) -> PreviewReport:
    """The step 2 record for one held run.

    stats is the run's own; groups are the conflict groups derived from
    the same run's rows, and decisions are the answers given to them, so
    the conflict count this reports, the count still outstanding and the
    rows the resolve step offers are all the one set (DL-215).

    The playlists are ordered by entry count, largest first, and by name
    where two hold the same count, so the ordering is total: a dict whose
    iteration order settled the listing would put a different nine rows
    on the screen for two runs reporting the same playlists.
    """
    rebuilt = dict(stats.get("reconstructed_playlists") or {})
    rows = tuple(
        PlaylistRow(name=name, entries=entries)
        for name, entries in sorted(
            rebuilt.items(), key=lambda pair: (-pair[1], pair[0])
        )
    )
    listed = rows[:LISTED_PLAYLISTS]
    rest = rows[LISTED_PLAYLISTS:]
    remainder = (
        PlaylistRow(name=f"and {len(rest)} more", entries=sum(r.entries for r in rest))
        if rest
        else None
    )
    return PreviewReport(
        listed=listed,
        remainder=remainder,
        filled=int(stats.get("refilled_playlists") or 0),
        empty=int(stats.get("empty_playlists") or 0),
        entries_added=sum(r.entries for r in rows),
        unfilled=tuple(stats.get("unfilled_playlists") or ()),
        conflicts=len(groups),
        outstanding=conflict_model.resolve_gate(decisions, groups).outstanding,
    )


def write_report(
    stats: Mapping[str, object],
    groups: Sequence[conflict_model.ConflictGroup],
    decisions: conflict_model.ConflictDecisions,
    destination: str,
    destination_exists: bool,
    originals: Iterable[str],
) -> WriteReport:
    """The step 4 record for one held run and the answers given to it.

    The third change row's count is the decided group count read off
    resolve_gate, which is the same value that opens the step: a screen
    listing a count of chosen answers the gate does not agree with would
    be reporting a run other than the one about to be written (DL-204).
    """
    gate = conflict_model.resolve_gate(decisions, groups)
    filled = int(stats.get("refilled_playlists") or 0)
    unfilled = len(tuple(stats.get("unfilled_playlists") or ()))
    added = sum(int(v) for v in dict(stats.get("reconstructed_playlists") or {}).values())
    rows = (
        ChangeRow(
            label="Playlists filled again",
            detail=(
                "They keep the names, order and position they already have "
                "in the collection being repaired."
            ),
            count=filled,
            tone=TONE_ADDED,
        ),
        ChangeRow(
            label="Entries added to those playlists",
            detail="Each one points at a track the collection already holds.",
            count=added,
            tone=TONE_ADDED,
        ),
        ChangeRow(
            label="Tracks taking the values you chose",
            detail="Decided at step 3, one answer per track held more than one way.",
            count=gate.decided,
            tone=TONE_ADDED,
        ),
        ChangeRow(
            label="Playlists left empty",
            detail="No collection this run read held their contents. They keep their names.",
            count=unfilled,
            tone=TONE_UNTOUCHED,
        ),
    )
    return WriteReport(
        destination=destination,
        destination_exists=destination_exists,
        rows=rows,
        tracks_total=int(stats.get("collection_entries_total") or 0),
        originals=tuple(originals),
    )

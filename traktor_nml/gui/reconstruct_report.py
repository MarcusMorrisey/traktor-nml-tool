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

from . import answer_detail
from . import conflict_model
from .wording import plural

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


def _winner_reading(winner: tuple[int, str], labels: Sequence[str]) -> str:
    """One settled group's winner as a reader sees it: the collection
    name held at the winner's input index, with the record's primary key
    behind it.

    Both halves, because the members of a settled group describe the one
    LOCATION and so carry the identical primary key: the key alone
    repeats the track and names which of them won of neither, and a
    collection name alone is the base-or-source token DL-148 refuses. The
    name comes from the labels the page holds for its inputs, so the
    cell names a collection the way the resolve rail's contributor chips
    name one (DL-150).

    An index outside the labels supplied is worded as the index itself,
    which still tells the two records apart, so a caller composing a
    record without labels reads a row rather than an IndexError.
    """
    input_index, primary_key = winner
    named = (
        labels[input_index] if input_index < len(labels) else f"input {input_index}"
    )
    return f"{named}: {primary_key}"


@dataclass(frozen=True)
class OutlierRow:
    """One listed measured gap: the track it names, the attribute's own
    label, the two values, how far apart they are and the record whose
    number the output keeps.

    A reading rather than a row to decide, so it carries no candidate
    reference and no decision state - there is nothing on this row for
    the operator to answer, and a field that looked like one would
    invite a click the step does not offer (DL-330).

    The label is answer_detail.LABELS' word, so a gap in PLAYTIME_FLOAT
    prints here under the name the resolve rail gives it and the two
    screens cannot call one attribute two things (ref: DL-254). The
    values carry both readings for the reason the rail carries both: the
    raw string is what the file holds and what tells the two numbers
    apart by a digit, and the formatted one is what a kilobyte count, a
    bitrate and a length mean. A value that does not parse has no
    formatted reading and carries None (ref: DL-248).

    winner is _winner_reading's wording of the (input index, primary key)
    pair the run's settled row named the kept record by: the collection
    the number was read from and the key behind it, never a
    base-or-source token standing on its own and never the key alone,
    which every member of a settled group carries (DL-148).
    """

    track: str
    label: str
    low: str
    high: str
    low_detail: Optional[str]
    high_detail: Optional[str]
    relative_gap: float
    winner: str

    @property
    def spread(self) -> str:
        """The two ends as one cell, each with its formatted reading
        where it has one."""
        return f"{self._read(self.low, self.low_detail)} -> {self._read(self.high, self.high_detail)}"

    @property
    def gap_amount(self) -> str:
        """The gap as a percentage of the larger value, at one decimal:
        the band is 1% and a whole-number reading would print 1% for
        every group just past it."""
        return f"{self.relative_gap * 100:.1f}%"

    @staticmethod
    def _read(raw: str, detail: Optional[str]) -> str:
        """One end of the spread: the raw value the file holds, with the
        formatted reading in brackets where the value parses. The raw
        string leads because it is what tells 320000 from 1411000 by a
        digit, and a value with no formatted reading prints as itself
        rather than as a blank (ref: DL-248)."""
        return raw if detail is None else f"{raw} ({detail})"


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
    # What the run answered without asking, and which of those answers
    # are worth reading. settled is the count of groups the tier settled
    # and outliers are the rows naming a measured gap past the band.
    # Both default empty so a caller composing a record for a run that
    # reported neither reads the record it reads (DL-329, DL-331).
    settled: int = 0
    outliers: tuple["OutlierRow", ...] = ()

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
            held = plural(self.conflicts, "track", "tracks")
            return (
                f"Every one of the {self.conflicts} {held} held "
                "differently by more than one collection has an answer. "
                "Step 3 is where those answers are changed."
            )
        held = plural(self.outstanding, "track is", "tracks are")
        each = plural(self.outstanding, "It has", "Each one has")
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

    @property
    def settled_sentence(self) -> str:
        """The note beside the conflict note: how many tracks the run
        answered itself, and where the answer came from.

        Empty for a run the rule settled nothing for, the way
        conflict_sentence is empty for a run that reported no
        divergence: a sentence reading 0 names something this run did
        not do.

        The sentence says the values came from one named record, and the
        row for each listed gap names which record that is - the
        collection it was read from and its primary key, because that is
        what a resolution names (DL-148). It says why no decision was
        asked for: the two numbers are both Traktor's own measurements of
        the one file, so there is no judgement to make. The count is this
        record's own (DL-215) and its word comes from wording.plural
        (DL-233).
        """
        if not self.settled:
            return ""
        held = plural(self.settled, "track is", "tracks are")
        measured = plural(self.settled, "It carries", "Each carries")
        return (
            f"{self.settled} {held} measured differently by the two "
            "collections - file size, length or bitrate. Both numbers are "
            f"Traktor's own, so there is nothing to decide. {measured} the "
            "values of the record the output keeps."
        )

    @property
    def outlier_title(self) -> str:
        """The head of the card listing the wide measured gaps. The card
        is the count, so a run with no outlier draws none and this is
        never read for one.

        The count's word comes from wording.plural like every other count
        sentence on these screens; no conditional stands here, which is
        what tests/test_gui_wording.py reads this module for (DL-215,
        DL-233).
        """
        return plural(
            self.outlier_count,
            "The one measured far apart",
            f"The {self.outlier_count} measured far apart",
        )

    @property
    def outlier_count(self) -> int:
        """How many readings the listing draws. The count of readings
        rather than of groups: a group reading past the band on two
        measured attributes draws two rows, and the card's head names the
        rows under it (DL-215)."""
        return len(self.outliers)

    @property
    def outlier_note(self) -> str:
        """The small print under the listing. These are readings rather
        than rows to decide, and the line says so, so the operator does
        not look for a control that is not there (DL-330)."""
        return (
            "These are read, not decided. The output carries the record "
            "named beside each one; Traktor rewrites its own measurement "
            "the next time it analyses the file."
        )


@dataclass(frozen=True)
class WriteReport:
    """What step 4 shows about the file it is about to write, or has:
    where the output goes, the state of that path, what the file holds,
    and which collections the run read without modifying.

    `written` carries the one difference between the two states. The step
    does not become another screen once the write lands - the operator is
    looking at the card they just confirmed, and every other thing on it
    is still true: the change list described the file and now describes
    it in the present tense, the originals are still unmodified, and the
    note about opening it in Traktor is the next thing to do rather than
    a thing to do later. Only the tense and the status move (DL-240).
    """

    destination: str
    destination_exists: bool
    rows: tuple[ChangeRow, ...]
    tracks_total: int
    originals: tuple[str, ...]
    written: bool = False

    @property
    def head_title(self) -> str:
        """The card's own head at `Write.dc.html:92`."""
        return "Written" if self.written else "Before anything is written"

    @property
    def head_badge(self) -> str:
        """The status beside that head. It is the one place the step
        says whether the file exists yet, so it reads as a state rather
        than as an instruction."""
        return "Written" if self.written else "Nothing written yet"

    @property
    def contents_title(self) -> str:
        """The head of the change list at `Write.dc.html:104`. The list
        itself does not change: it described what the file would hold
        and now describes what it holds."""
        return "What the new file holds" if self.written else "What the new file will hold"

    @property
    def destination_badge(self) -> str:
        """The badge beside the path at `Write.dc.html:98`.

        A written path says so. Before the write, a path that already
        exists is said so plainly rather than left unsaid: the write
        replaces it, and the operator is the one who decides whether
        that is what they meant.
        """
        if self.written:
            return "Written"
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

        A path already holding a file is a different question: the
        operator is not being asked to create something but to destroy
        something, and the question says which (DL-241).
        """
        filled = self.rows[0].count if self.rows else 0
        playlists = plural(filled, "playlist", "playlists")
        if self.destination_exists:
            return f"Replace the file at that path with {filled} rebuilt {playlists}?"
        return f"Write {filled} rebuilt {playlists}?"

    @property
    def confirm_assurances(self) -> tuple[str, ...]:
        """The lines under the dialog's question.

        The first states what happens to the path. The write replaces
        whatever stands there, so on a path already holding a file the
        line that says a new file is created is not true, and a
        confirmation that misstates what it is about to destroy is worse
        than no confirmation at all: it spends the operator's attention
        reassuring them (DL-241).

        The other two hold either way: the run's own inputs are refused
        as an output, and nothing reaches Traktor until the operator
        imports the file themselves.
        """
        if self.destination_exists:
            first = (
                "The file already at that path is replaced, and what it "
                "holds now is not recoverable."
            )
        else:
            first = "A new file is created at the path above."
        return (
            first,
            "No collection you gave this run is touched.",
            "Traktor is not changed until you import the new file yourself.",
        )

    @property
    def confirm_action(self) -> str:
        """The dialog's primary control. It names the act, so a control
        reading `Write collection` never stands under a question about
        replacing one (DL-241)."""
        return "Replace file" if self.destination_exists else "Write collection"

    @property
    def destination_note(self) -> str:
        """The line under the path at `Write.dc.html:100`.

        A path already holding a file says so here as well as in its
        badge, because the badge is a state and this is what the write
        will do about it.
        """
        refuses = (
            "The write refuses any path this run read, so nothing you "
            "gave it is overwritten."
        )
        if self.written or not self.destination_exists:
            return refuses
        return "A file already stands here and the write replaces it. " + refuses


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
        held = plural(self.conflicts, "track is", "tracks are")
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
    settled_rows: Sequence[object] = (),
    labels: Sequence[str] = (),
) -> PreviewReport:
    """The step 2 record for one held run.

    stats is the run's own; groups are the conflict groups derived from
    the same run's rows, and decisions are the answers given to them, so
    the conflict count this reports, the count still outstanding and the
    rows the resolve step offers are all the one set (DL-215).

    settled_rows are the run's own splice.SettledRow list. The count and
    the listing are one division of that one list, made here rather than
    in the render, for the reason LISTED_PLAYLISTS is divided here
    (DL-217): a render that filtered the outliers itself could draw a
    number of rows the sentence above them does not name. It is a
    keyword-shaped trailing parameter with an empty default, so every
    existing positional caller reads the arguments it reads (DL-100's
    precedent, DL-104).

    labels is the collection name held at each input index, the tuple
    _collection_labels builds and the resolve rail's own contributor
    chips are named from. Each listed row's winner is worded here from
    it and from the (input index, primary key) pair the run reported,
    rather than left for the render to word: the members of a settled
    group share the primary key, so the index is the half that says
    which record won, and one reading of the pair keeps the row and the
    rail naming a collection the one way (DL-148, DL-150, DL-215).
    An empty labels reads each winner as its input index, so a caller
    composing a record for a run whose labels it does not hold reads a
    row rather than an IndexError.

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
        entries_added=int(stats.get("playlist_entries_added") or 0),
        unfilled=tuple(stats.get("unfilled_playlists") or ()),
        conflicts=len(groups),
        outstanding=conflict_model.resolve_gate(decisions, groups).outstanding,
        settled=len(settled_rows),
        outliers=tuple(
            OutlierRow(
                track=row.identity_key,
                label=answer_detail.LABELS[reading.attr],
                low=reading.low,
                high=reading.high,
                low_detail=answer_detail.format_value(reading.attr, reading.low),
                high_detail=answer_detail.format_value(reading.attr, reading.high),
                relative_gap=reading.relative_gap,
                winner=_winner_reading(row.winner, labels),
            )
            for row in settled_rows
            for reading in row.outliers
        ),
    )


def write_report(
    stats: Mapping[str, object],
    groups: Sequence[conflict_model.ConflictGroup],
    decisions: conflict_model.ConflictDecisions,
    destination: str,
    destination_exists: bool,
    originals: Iterable[str],
    written: bool = False,
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
    # What the run added, not what the rebuilt playlists hold: a playlist
    # that was not empty keeps its own entries and gains the rest, and
    # counting its contents here would name entries the operator already
    # had as ones this run put there (DL-238).
    added = int(stats.get("playlist_entries_added") or 0)
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
    # A fifth row only where there is something to report: an entry that
    # landed on a track the collection holds more than once is placed
    # rather than dropped, and a row reading zero would name a thing this
    # run did not do (DL-230).
    on_duplicated = int(stats.get("entries_on_duplicated_tracks") or 0)
    if on_duplicated:
        held_by = len(dict(stats.get("playlists_on_duplicated_tracks") or {}))
        playlists = plural(held_by, "playlist", "playlists")
        rows = rows + (
            ChangeRow(
                label="Entries on a track the collection holds more than once",
                detail=(
                    f"Across {held_by} {playlists}. Each is placed on the "
                    "first of those copies, which is the one the merge "
                    "points at too."
                ),
                count=on_duplicated,
                tone=TONE_UNTOUCHED,
            ),
        )
    # A row only where there is something to report: an entry naming a
    # track no collection this run read holds is dropped rather than kept
    # or refused, and a row reading zero would name a thing this run did
    # not do (DL-232).
    dropped = int(stats.get("entries_dropped_unresolvable") or 0)
    if dropped:
        tracks = int(stats.get("tracks_dropped_unresolvable") or 0)
        lost_from = len(dict(stats.get("playlists_with_dropped_entries") or {}))
        track_word = plural(tracks, "track", "tracks")
        playlists = plural(lost_from, "playlist", "playlists")
        rows = rows + (
            ChangeRow(
                label="Entries dropped, pointing at a missing track",
                detail=(
                    f"{tracks} {track_word} across {lost_from} {playlists}. "
                    "Neither collection holds an entry for them, so the "
                    "playlists keep everything else and lose these."
                ),
                count=dropped,
                tone=TONE_UNTOUCHED,
            ),
        )
    return WriteReport(
        written=written,
        destination=destination,
        destination_exists=destination_exists,
        rows=rows,
        tracks_total=int(stats.get("collection_entries_total") or 0),
        originals=tuple(originals),
    )

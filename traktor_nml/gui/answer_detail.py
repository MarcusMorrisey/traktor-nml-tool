"""The rows one answer in the resolve step's detail rail draws.

An answer is a record, not a diff. The rail shows every tracked
attribute the group's records carry - the ones the answers disagree on,
read off the candidate, and the ones they agree on, read off the group -
so the operator picks by reading a record rather than by reading a list
of what is missing from one.

Two values per field, not one. The raw string is what the written file
carries and is what tells the answers apart when they differ by a digit;
the formatted one is what a filesize in kilobytes, a bitrate in bits per
second and a playtime in seconds mean. A rail showing only the formatted
value would hide which record wins, and one showing only the raw value
is the screen this module exists to replace.

Imports splice for the attribute order alone and no nicegui, so the
suite reaches every rule here under the system interpreter (DL-069).

The module stands apart from conflict_model, which is the vocabulary a
pick is recorded in: a display formatting rule there would give that
module a second purpose (ref: DL-246). Every field row, its label, its
formatted value and its mark stand here and app.py only places them.

_TRACKED_ATTRS is imported rather than copied: a second list of the six
names drifts from the one splice computes divergence against, and the
field order on screen is the model's order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..splice import _TRACKED_ATTRS

# The NML attribute each tracked identifier names, which is the word the
# rail prints. The identifiers are Python attribute names on EntryRecord
# and two of them - playtime_float, filesize - are not what the file
# calls them read aloud; the operator is looking at a Traktor
# collection, so the label is the collection's own word, uppercase, as
# Resolve.dc.html:92's .cmpf .k draws it.
#
# One fixed mapping so the same attribute cannot print as PLAYTIME_FLOAT
# on one row and LENGTH on another; the label is the XML attribute name
# the written file carries, uppercased (ref: DL-254). A tracked
# attribute that splice carries without a label here raises KeyError at
# the call site rather than drawing a blank key.
LABELS = {
    "artist": "ARTIST",
    "title": "TITLE",
    "album": "ALBUM",
    "filesize": "FILESIZE",
    "playtime_float": "PLAYTIME_FLOAT",
    "bitrate": "BITRATE",
}


@dataclass(frozen=True)
class AnswerField:
    """One row of one answer.

    formatted is None where the field has no second reading - artist,
    title and album are already what they say - and where the value does
    not parse, which includes the empty string a record with no INFO
    element carries. differs says whether the answers disagree on this
    field, which is what the rail marks; it is never a judgement about
    which value is better.

    No colour ranks one value against another anywhere this dataclass is
    drawn: the tool cannot know that a larger filesize or a higher
    bitrate is the better record, so difference is marked and never
    ranked (ref: DL-249).
    """

    attr: str
    label: str
    raw: str
    formatted: Optional[str]
    differs: bool


def format_value(attr: str, raw: str) -> Optional[str]:
    """The second reading of one raw attribute value, or None.

    filesize is Traktor's own kilobyte count, not a byte count -
    matching.py compares FILESIZE against a file's bytes divided by 1024
    - so megabytes is ONE division by 1024. A second division would put
    an 8 MB file on screen as 0.0 MB.

    playtime_float is seconds as a decimal string and reads as minutes
    and seconds, the seconds truncated toward zero and zero-padded, so
    99.6 seconds is 1:39 rather than 1:99 or 1:40.

    bitrate is bits per second in a Traktor collection, so kilobits is
    one division by 1000, rounded to a whole number.

    No thousands separator is introduced anywhere: the raw string beside
    the formatted one is the file's own text and a grouped copy of it
    reads as a third value.

    Every record the rail answers over came out of a Traktor collection,
    so there is no provenance branch: one unit reading per attribute,
    stated here once.

    That is a property of the model rather than an assumption: splice
    groups over the collection_records of the NML inputs, and a
    disk-scanned record - whose BITRATE diskscan writes in kilobits -
    reaches matching and reconnect_run instead, never a conflict group
    (ref: DL-253).

    The precision is the approved design read literally: one decimal on
    MB, a whole number on kbps, and seconds zero-padded to two digits
    (ref: DL-255).

    Returning None for a value that does not parse covers the empty
    string a record with no INFO element carries: the raw value then
    prints as itself with no formatted companion, rather than a division
    raising inside a page build (ref: DL-248).
    """
    if attr not in ("filesize", "playtime_float", "bitrate"):
        return None
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    if attr == "filesize":
        return f"{number / 1024:.1f} MB"
    if attr == "bitrate":
        return f"{round(number / 1000)} kbps"
    minutes, seconds = divmod(int(number), 60)
    return f"{minutes}:{seconds:02d}"


def answer_fields(
    attrs: tuple[str, ...],
    agreed: tuple[tuple[str, str], ...],
    candidate,
) -> tuple[AnswerField, ...]:
    """One field per tracked attribute the group carries, in
    _TRACKED_ATTRS order.

    attrs names the attributes the answers disagree on and is
    index-aligned with candidate.values; agreed pairs the rest with the
    single value every member holds. A field is marked as differing
    exactly where its name stands in attrs, so the mark says "the
    answers disagree here" and nothing about which one to take.

    The membership test is the whole rule: attrs is the set splice
    computed divergence into, so no second divergence computation exists
    here to disagree with the first (ref: DL-243). Both sources together
    are the complete record the rail draws - the divergent values off the
    candidate, the agreeing ones off the group (ref: DL-242).

    The order is _TRACKED_ATTRS' own rather than attrs-then-agreed, so
    one answer's rows line up against the next answer's rows down the
    rail. An attribute in neither is not a field the group carries and is
    left out.
    """
    divergent = dict(zip(attrs, candidate.values))
    settled = dict(agreed)
    fields = []
    for attr in _TRACKED_ATTRS:
        if attr in divergent:
            raw, differs = divergent[attr], True
        elif attr in settled:
            raw, differs = settled[attr], False
        else:
            continue
        fields.append(
            AnswerField(
                attr=attr,
                label=LABELS[attr],
                raw=raw,
                formatted=format_value(attr, raw),
                differs=differs,
            )
        )
    return tuple(fields)

"""The wording rules a sentence on either page reads its words from.

One function, because the thing worth having in one place is not the
English but the rule that the word follows the count. Every screen in
this package states counts an operator acts on - how many playlists were
filled, how many tracks carry more than one answer, how many entries a
run dropped - and a count of one is the ordinary case on a pair of
collections that barely diverge, not an edge. A sentence reading "1
tracks" is the screen misreporting the model it describes rather than
styling it badly (DL-215, DL-233).

Both forms are given at the call site rather than derived from the
singular. The forms this package needs are not all a trailing "s":
"track carries" against "tracks carry" and "track is" against "tracks
are" carry the verb with them, and a helper that appended a letter would
be right for the nouns and wrong for exactly the sentences that are
hardest to notice reading the code.

Imports nothing, so it runs under the interpreter the suite uses
(DL-069).
"""

from __future__ import annotations


def plural(count: int, one: str, many: str) -> str:
    """The word for count: `one` where it is exactly 1, `many` otherwise.

    Zero takes the plural, which is English and is also what the screens
    want: "0 playlists left empty" is a row of the change list, and "0
    playlist" would read as a typo rather than as a count.
    """
    return one if count == 1 else many

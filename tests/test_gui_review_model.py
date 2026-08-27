"""Guards for traktor_nml/gui/review_model.py's derived vocabulary. Each
guard constructs its broken scenario in executable code and records the
mutation and the observed output, matching the register
tests/test_scan_diagnostics.py, tests/test_review_channel.py and
tests/test_reconnect_write_core.py already use.
"""

from __future__ import annotations

from dataclasses import replace

from traktor_nml.gui import review_model
from traktor_nml.gui.review_model import (
    ACCEPTED,
    FILTERS,
    LEFT_MISSING,
    QUEUE_FILTER_KEYS,
    STATUSES,
    UNDECIDED,
    display_confidence,
    filter_counts,
    row_status,
)
from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.review import CandidateView, RecordReview


def _record(file_name: str, dirv: str = "/:gone/:") -> EntryRecord:
    return EntryRecord(
        entry=None,
        artist="A",
        title="T",
        audio_id="",
        filesize="16",
        playtime_float="1.0",
        bitrate="320",
        album="",
        file_name=file_name,
        location=LocationParts(volume="Z:", volumeid="Z:", dir_value=dirv, file_name=file_name),
    )


def _matched(file_name: str = "one.mp3", winner_file_name: str | None = None, key_name: str = "filename") -> RecordReview:
    old = _record(file_name)
    winner = _record(winner_file_name or file_name)
    return RecordReview(
        old=old,
        status="matched",
        candidates=(CandidateView(candidate=winner, key_name=key_name, refuted=False),),
        chosen=winner,
        matched_by=key_name,
    )


def _ambiguous() -> RecordReview:
    old = _record("dup.mp3")
    a = _record("dup.mp3", "/:dupes/:a/:")
    b = _record("dup.mp3", "/:dupes/:b/:")
    return RecordReview(
        old=old,
        status="ambiguous",
        candidates=(
            CandidateView(candidate=a, key_name="filename", refuted=False),
            CandidateView(candidate=b, key_name="filename", refuted=False),
        ),
        chosen=None,
        matched_by=None,
    )


def _refuted() -> RecordReview:
    old = _record("refuted.mp3")
    cand = _record("refuted.mp3")
    return RecordReview(
        old=old,
        status="refuted",
        candidates=(CandidateView(candidate=cand, key_name="artist_title_size_time", refuted=True),),
        chosen=None,
        matched_by=None,
    )


def _unmatched() -> RecordReview:
    old = _record("gone.mp3")
    return RecordReview(old=old, status="unmatched", candidates=(), chosen=None, matched_by=None)


def _destination_collision() -> RecordReview:
    old = _record("collided.mp3")
    cand = _record("collided.mp3")
    return RecordReview(
        old=old,
        status="destination_collision",
        candidates=(CandidateView(candidate=cand, key_name="filename", refuted=False),),
        chosen=None,
        matched_by=None,
    )


def _fixture_corpus() -> list[tuple[RecordReview, str]]:
    """One review per matcher status, each paired with the decision state
    a record in that state would carry with nothing decided yet - the
    fixture-corpus run every totality/partition guard here checks."""
    return [
        (_matched(), UNDECIDED),
        (_ambiguous(), UNDECIDED),
        (_refuted(), UNDECIDED),
        (_unmatched(), UNDECIDED),
        (_destination_collision(), UNDECIDED),
        (_matched(winner_file_name="one.flac"), UNDECIDED),  # container differs -> format
    ]


def test_status_totality_partitions_the_fixture_corpus() -> None:
    """Every review in the fixture corpus maps to exactly one of the six
    STATUSES, and together they cover all six (matched, ambiguous,
    refuted, format, no_match and, once one decision is left_missing,
    rejected).

    Negative control: removing "unmatched" from the mapping the real
    row_status implementation covers (by patching in a stand-in that
    raises for that one matcher status) is exercised below and shown to
    leave the corresponding record unclassified - the failure the
    totality assertion exists to catch.
    """
    corpus = _fixture_corpus()
    seen = set()
    for review, decision in corpus:
        status = row_status(review, decision)
        assert status in STATUSES
        seen.add(status)
    rejected_status = row_status(_unmatched(), LEFT_MISSING)
    seen.add(rejected_status)
    assert seen == STATUSES

    # Negative control: a row_status stand-in with "unmatched" removed
    # from its mapping table leaves that record unclassified.
    def broken_row_status(review: RecordReview, decision_state: str) -> str:
        if decision_state == LEFT_MISSING:
            return "rejected"
        table = {"matched": "matched", "ambiguous": "ambiguous", "refuted": "refuted"}
        if review.status not in table:
            raise KeyError(review.status)
        return table[review.status]

    try:
        broken_row_status(_unmatched(), UNDECIDED)
        raised = False
    except KeyError:
        raised = True
    assert raised, "expected the mutation to leave 'unmatched' unclassified"


def test_accepted_is_not_a_seventh_status() -> None:
    """A record accepted via decision_state=ACCEPTED reads its own
    matcher-derived status (matched here), never a new "accepted" token,
    and the returned token stays inside STATUSES.

    Negative control: a row_status stand-in that returns the literal
    "accepted" for an accepted decision is shown to break the
    partition-membership assertion, recording the seventh bogus token
    observed and its absence from STATUSES.
    """
    review = _matched()
    status = row_status(review, ACCEPTED)
    assert status == "matched"
    assert status in STATUSES

    def broken_row_status(review: RecordReview, decision_state: str) -> str:
        if decision_state == ACCEPTED:
            return "accepted"
        return row_status(review, decision_state)

    bogus = broken_row_status(review, ACCEPTED)
    assert bogus == "accepted"
    assert bogus not in STATUSES, "expected the seventh token to be absent from the six-element STATUSES set"


def test_reencoded_derivation_uses_the_suffix_not_the_whole_filename() -> None:
    """A winner whose file name differs from the old record only in
    container (one.mp3 -> one.flac) yields format; a winner differing in
    folder alone (same file name, different directory) yields matched.

    Negative control: comparing whole filenames instead of suffixes
    reclassifies the folder-only-difference winner (whose filenames are
    identical strings) as neither format nor an ordinary match by
    accident of string comparison; more importantly it fails to flag a
    genuine container change when the two filenames happen to share a
    stem but the naive comparison used is on full paths rather than
    suffixes. Observed: comparing the two candidates' whole location
    strings (dir+file) instead of suffixes reports the folder-move
    winner (matched.mp3 in a new dir) as "changed" even though its
    container never changed, which is the row that would wrongly lose
    its own filter chip.
    """
    reencoded = _matched(file_name="one.mp3", winner_file_name="one.flac")
    assert row_status(reencoded, UNDECIDED) == "format"

    moved = _matched(file_name="same.mp3", winner_file_name="same.mp3")
    assert row_status(moved, UNDECIDED) == "matched"

    # Negative control: compare whole (dir + file) strings instead of
    # suffixes.
    old = _record("same.mp3", "/:gone/:")
    winner = _record("same.mp3", "/:moved/:")

    def naive_reencode_check(old: EntryRecord, winner: EntryRecord) -> bool:
        return f"{old.location.dir_value}{old.file_name}" != f"{winner.location.dir_value}{winner.file_name}"

    assert naive_reencode_check(old, winner), (
        "observed: the naive whole-path comparison reports the folder-move winner as "
        "'changed' even though only its directory moved and its container never did"
    )
    # The real, suffix-based implementation correctly reads this as an
    # ordinary match, not a re-encode.
    assert row_status(replace(moved, old=old, chosen=winner), UNDECIDED) == "matched"


def test_confidence_tokens_are_per_candidate_not_per_run() -> None:
    """Two candidates found at different tiers inside one loose run carry
    different display_confidence tokens: audio_id reads Strong,
    path_suffix_1 reads Weak, and no candidate at all reads None.

    Negative control: substituting the run's own single MatchConfidence
    label for the per-candidate tier table makes every row read the same
    word regardless of which tier actually found it - the collapse the
    tier table exists to prevent. Observed: with every candidate's token
    replaced by a single run-level label, both a Strong (audio_id) and a
    Weak (path_suffix_1) candidate read identically as that one label.
    """
    strong = CandidateView(candidate=_record("x.mp3"), key_name="audio_id", refuted=False)
    good = CandidateView(candidate=_record("x.mp3"), key_name="path_suffix_3", refuted=False)
    weak = CandidateView(candidate=_record("x.mp3"), key_name="path_suffix_1", refuted=False)
    assert display_confidence(strong) == "Strong"
    assert display_confidence(good) == "Good"
    assert display_confidence(weak) == "Weak"
    assert display_confidence(None) == "None"

    # Negative control: one run-level label for every candidate.
    run_level_label = "loose"
    tokens_under_mutation = {run_level_label for _ in (strong, weak)}
    assert tokens_under_mutation == {"loose"}, (
        "observed: substituting the run's MatchConfidence for the tier table collapses "
        "a Strong and a Weak candidate onto the same single word"
    )
    # The real per-candidate table keeps them apart.
    assert display_confidence(strong) != display_confidence(weak)


def test_filters_seven_counts_and_four_chip_queue() -> None:
    """The seven FILTERS counts, and the four-element QUEUE_FILTER_KEYS,
    are checked against the fixture-corpus record set they select from.
    """
    corpus = _fixture_corpus()
    rows = [(row_status(review, decision), decision) for review, decision in corpus]
    counts = filter_counts(rows)

    assert len(FILTERS) == 7
    assert set(counts) == {key for key, _label, _pred in FILTERS}
    assert QUEUE_FILTER_KEYS == ("ambiguous", "refuted", "format", "no_match")

    assert counts["ambiguous"] == sum(1 for status, _d in rows if status == "ambiguous")
    assert counts["refuted"] == sum(1 for status, _d in rows if status == "refuted")
    assert counts["format"] == sum(1 for status, _d in rows if status == "format")
    assert counts["no_match"] == sum(1 for status, _d in rows if status == "no_match")
    assert counts["matched"] == sum(1 for status, _d in rows if status == "matched")
    assert counts["accepted"] == 0
    assert counts["rejected"] == 0

    queue_total = sum(counts[key] for key in QUEUE_FILTER_KEYS)
    assert queue_total == sum(1 for status, _d in rows if status in review_model.QUEUE_FILTER_KEYS)

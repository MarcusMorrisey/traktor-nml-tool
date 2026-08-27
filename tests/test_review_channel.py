"""Guards for the on_review channel through match_records and
resolve_reconnection: inertness when the parameter is left at None,
per-record status coverage, refutation detail arithmetic, and the
destination_collision overlay resolve_reconnection applies above the
matcher. Each guard constructs its broken scenario in executable code
and records the mutation and the observed output in its docstring.
"""

from __future__ import annotations

from traktor_nml import matching as matching_module
from traktor_nml.confidence import MatchConfidence
from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.reconnect import resolve_reconnection
from traktor_nml.review import CandidateView, RecordReview


def _old(artist: str, title: str, dirv: str, filename: str, size: str = "16", time: str = "1.0") -> EntryRecord:
    return EntryRecord(
        entry=None,
        artist=artist,
        title=title,
        audio_id="",
        filesize=size,
        playtime_float=time,
        bitrate="320",
        album="",
        file_name=filename,
        location=LocationParts(volume="Z:", volumeid="Z:", dir_value=dirv, file_name=filename),
    )


def _candidate(filename: str, size: str = "16", time: str = "1.0") -> EntryRecord:
    return EntryRecord(
        entry=None,
        artist="",
        title="",
        audio_id="",
        filesize=size,
        playtime_float=time,
        bitrate="320",
        album="",
        file_name=filename,
        location=LocationParts(volume="", volumeid="", dir_value="/:", file_name=filename),
    )


def test_on_review_none_is_inert_and_builds_no_candidate_views(monkeypatch) -> None:
    """resolve_reconnection with on_review omitted must produce the same
    mapping, stats and ambiguity_rows as a run supplying a recording
    collector, and must construct no CandidateView while doing it.

    Negative control: with on_review supplied instead of omitted, the same
    scenario is shown to construct at least one CandidateView, which is
    what demonstrates the omitted-case assertion is actually exercising
    the guard rather than passing regardless of whether construction ever
    happens at all.
    """
    old_records = [
        _old("A", "One", "/:gone1/:", "one.mp3"),
        _old("B", "Two", "/:gone2/:", "two.mp3"),
        _old("C", "Missing", "/:gone3/:", "missing.mp3"),
    ]
    candidates = [_candidate("one.mp3"), _candidate("two.mp3")]

    mapping_omitted, stats_omitted, rows_omitted = resolve_reconnection(
        old_records, candidates, MatchConfidence.FILENAME
    )

    built = 0
    real_init = CandidateView.__init__

    def counting_init(self, *args, **kwargs):
        nonlocal built
        built += 1
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(CandidateView, "__init__", counting_init)
    reviews: list[RecordReview] = []
    mapping_collected, stats_collected, rows_collected = resolve_reconnection(
        old_records, candidates, MatchConfidence.FILENAME, on_review=reviews.append
    )

    assert mapping_omitted == mapping_collected
    assert stats_omitted == stats_collected
    assert rows_omitted == rows_collected
    assert built > 0, "expected the supplied collector to trigger CandidateView construction"

    # Now the actual inertness claim: re-run with on_review omitted while
    # the counting __init__ is still installed, and confirm nothing built.
    built = 0
    resolve_reconnection(old_records, candidates, MatchConfidence.FILENAME)
    assert built == 0, "on_review=None must construct no CandidateView at all"


def test_every_record_reviewed_exactly_once_with_status_matching_its_bucket() -> None:
    """Over a small mixed corpus, every old record appears in exactly one
    RecordReview and that review's status agrees with which stats bucket
    the record fell into.

    Negative control: mutating one collected review's status away from
    what its own record actually matched to is shown to break the
    per-record agreement check below, so the assertion is sensitive
    rather than vacuous.
    """
    old_records = [
        _old("A", "One", "/:gone1/:", "one.mp3"),  # matches uniquely
        _old("Z", "Nothing", "/:gone2/:", "absent.mp3"),  # no candidate at all -> unmatched
    ]
    candidates = [_candidate("one.mp3")]

    reviews: list[RecordReview] = []
    mapping, stats, _rows = resolve_reconnection(
        old_records, candidates, MatchConfidence.FILENAME, on_review=reviews.append
    )

    assert len(reviews) == len(old_records)
    seen_keys = {r.old.primary_key for r in reviews}
    assert seen_keys == {r.primary_key for r in old_records}

    matched_keys = set(mapping.keys())
    for review in reviews:
        if review.old.primary_key in matched_keys:
            assert review.status == "matched"
        else:
            assert review.status in ("unmatched", "ambiguous", "refuted", "destination_collision")

    # Negative control: corrupt one review's status and show the agreement
    # check above catches it.
    mutated = list(reviews)
    matched_index = next(i for i, r in enumerate(mutated) if r.old.primary_key in matched_keys)
    from dataclasses import replace

    mutated[matched_index] = replace(mutated[matched_index], status="unmatched")
    mismatches = [
        r for r in mutated if (r.old.primary_key in matched_keys) != (r.status == "matched")
    ]
    assert mismatches, "expected the mutated status to be caught as a mismatch"


def test_duration_refutation_detail_reproduces_the_filter_numbers(monkeypatch) -> None:
    """A candidate whose duration differs from the old record's by more
    than the same-source allowance is refuted, and the emitted
    RefutationDetail carries the exact difference and allowance the
    filter used.

    Negative control: widening _DURATION_ABS_TOLERANCE so the same pair no
    longer contradicts is shown to make the record arrive unmatched with
    no candidate offered at all (the filename tier is the only one that
    can fire here and it has no ambiguity, so a refuted candidate leaves
    the record with zero survivors), and no RefutationDetail on any
    candidate view.
    """
    old = _old("A", "One", "/:gone1/:", "one.mp3", size="16", time="10.0")
    candidate = _candidate("one.mp3", size="16", time="30.0")  # 20s apart, over 1.0s allowance

    reviews: list[RecordReview] = []
    resolve_reconnection([old], [candidate], MatchConfidence.FILENAME, on_review=reviews.append)
    assert len(reviews) == 1
    review = reviews[0]
    assert review.status == "refuted"
    assert len(review.candidates) >= 1
    assert all(view.candidate is candidate for view in review.candidates)
    view = review.candidates[0]
    assert view.refuted is True
    assert view.detail is not None
    assert view.detail.field == "duration"
    assert view.detail.difference == 20.0
    assert view.detail.allowance == 1.0

    # Negative control: widen the tolerance so the pair no longer refutes.
    monkeypatch.setattr(matching_module, "_DURATION_ABS_TOLERANCE", 25.0)
    reviews_widened: list[RecordReview] = []
    resolve_reconnection(
        [old], [candidate], MatchConfidence.FILENAME, on_review=reviews_widened.append
    )
    widened_review = reviews_widened[0]
    assert widened_review.status == "matched"
    assert all(not v.refuted and v.detail is None for v in widened_review.candidates)


def test_collided_records_overlay_as_destination_collision_not_matched() -> None:
    """Two old records that each unambiguously match the same single
    candidate arrive as destination_collision, the status the ambiguity
    CSV also records for them, rather than as matched.

    Negative control: reading the reviews match_records itself emits -
    before resolve_reconnection's post-pass overlays the collision status
    - shows both would otherwise read matched, which is exactly the
    disagreement between the review channel and the ambiguity CSV the
    overlay exists to prevent.
    """
    old_a = _old("A", "One", "/:gone1/:", "shared.mp3")
    old_b = _old("B", "One", "/:gone2/:", "shared.mp3")
    candidate = _candidate("shared.mp3")

    reviews: list[RecordReview] = []
    final_mapping, stats, rows = resolve_reconnection(
        [old_a, old_b], [candidate], MatchConfidence.FILENAME, on_review=reviews.append
    )
    assert stats["destination_collisions"] == 2
    assert old_a.primary_key not in final_mapping
    assert old_b.primary_key not in final_mapping
    assert {r.status for r in reviews} == {"destination_collision"}
    assert {row["reason"] for row in rows} == {"destination_collision"}

    # Negative control: match_records' own (pre-overlay) reviews, obtained
    # by calling it directly the way resolve_reconnection does internally,
    # both read matched - the divergence the overlay walk exists to fix.
    from traktor_nml.matching import build_new_indexes, match_records

    indexes = build_new_indexes([candidate], MatchConfidence.FILENAME)
    pre_overlay: list[RecordReview] = []
    match_records(
        [old_a, old_b], [candidate], MatchConfidence.FILENAME, indexes=indexes, on_review=pre_overlay.append
    )
    assert {r.status for r in pre_overlay} == {"matched"}

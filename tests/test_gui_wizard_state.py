"""Guards for traktor_nml/gui/wizard_state.py's amended mapping. Each
guard constructs its broken scenario in executable code and records the
mutation and the observed output, matching the register
tests/test_scan_diagnostics.py, tests/test_review_channel.py and
tests/test_reconnect_write_core.py already use.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from traktor_nml import reconnect_run
from traktor_nml.gui import wizard_state as wizard_state_module
from traktor_nml.gui.wizard_state import (
    WizardState,
    amended_result,
    apply,
    build_volume_map,
    default_volume_identity,
    fingerprint_control_state,
    write_refusal,
    write_refusal_sentence,
)
from traktor_nml.rewrite import output_collision_refusal
from traktor_nml.model import EntryRecord, LocationParts
from traktor_nml.reconnect_run import ReconnectResult
from traktor_nml.review import CandidateView, RecordReview
from traktor_nml.volumes import VolumeIdentityError, parse_volume_map, resolve_volume_identity


def _record(file_name: str, volume: str = "Z:", volumeid: str = "Z:", dirv: str = "/:gone/:", source_path: Path | None = None) -> EntryRecord:
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
        location=LocationParts(volume=volume, volumeid=volumeid, dir_value=dirv, file_name=file_name),
        source_path=source_path,
    )


def _fixture_result() -> ReconnectResult:
    """Two old records: 'clean' matches uniquely on its first candidate;
    'alt' matches on its first candidate but carries a second, weaker
    candidate the operator can promote instead - both winners already
    carry a resolved (real) VOLUME/VOLUMEID, as reconnect_run's
    _reencode_winning_locations leaves every winner after a real scan.
    """
    clean_old = _record("clean.mp3", volume="Z:", volumeid="Z:", dirv="/:gone/:")
    clean_winner = _record(
        "clean.mp3", volume="D:", volumeid="D:", dirv="/:audio/:",
        source_path=Path("D:/audio/clean.mp3"),
    )
    clean_review = RecordReview(
        old=clean_old, status="matched",
        candidates=(CandidateView(candidate=clean_winner, key_name="filename", refuted=False),),
        chosen=clean_winner, matched_by="filename",
    )

    alt_old = _record("alt.mp3", volume="Z:", volumeid="Z:", dirv="/:gone/:")
    alt_winner = _record(
        "alt.mp3", volume="D:", volumeid="D:", dirv="/:audio/:primary/:",
        source_path=Path("D:/audio/primary/alt.mp3"),
    )
    alt_alternative = _record(
        "alt.mp3", volume="scan-placeholder", volumeid="scan-placeholder", dirv="/:audio/:secondary/:",
        source_path=Path("D:/audio/secondary/alt.mp3"),
    )
    alt_review = RecordReview(
        old=alt_old, status="matched",
        candidates=(
            CandidateView(candidate=alt_winner, key_name="filename", refuted=False),
            CandidateView(candidate=alt_alternative, key_name="bare_name", refuted=False),
        ),
        chosen=alt_winner, matched_by="filename",
    )

    mapping = {clean_old.primary_key: clean_winner, alt_old.primary_key: alt_winner}
    return ReconnectResult(
        mapping=mapping,
        stats={"matched": 2, "unmatched": 0},
        ambiguity_rows=[],
        old_records=[clean_old, alt_old],
        warnings=[],
        diagnostics=(),
        reviews=(clean_review, alt_review),
        volume_identities={Path("D:/"): ("D:", "D:")},
    )


def test_zero_overrides_leaves_the_mapping_equal_key_and_value() -> None:
    """apply with an empty decision set returns a mapping equal to
    result.mapping key for key and value for value.

    Negative control: seeding one decision (rejecting alt) is shown to
    change exactly the one key that decision names, proving the equality
    above is sensitive to decisions rather than trivially always true.
    """
    result = _fixture_result()
    decisions = WizardState()
    amended = apply(result, decisions)
    assert amended == result.mapping

    decisions.reject(result.old_records[1].primary_key)
    mutated = apply(result, decisions)
    differing = {k for k in result.mapping if result.mapping.get(k) != mutated.get(k)} | (
        set(result.mapping) ^ set(mutated)
    )
    assert differing == {result.old_records[1].primary_key}


def test_reject_removes_exactly_that_key() -> None:
    """Rejecting one record removes exactly that key from the amended
    mapping and leaves every other entry identical."""
    result = _fixture_result()
    decisions = WizardState()
    key = result.old_records[0].primary_key
    decisions.reject(key)
    amended = apply(result, decisions)
    assert key not in amended
    other_key = result.old_records[1].primary_key
    assert amended[other_key] == result.mapping[other_key]
    assert len(amended) == len(result.mapping) - 1


def test_accept_alternative_reencodes_its_location() -> None:
    """Accepting the second candidate for 'alt' places that candidate in
    the amended mapping carrying a LOCATION with the resolved VOLUME and
    VOLUMEID (D:/D:, resolved via result.volume_identities against the
    scan root D:/ the candidate's source_path resolves under) rather
    than the scan placeholder.

    Negative control: skipping the re-encoding step is shown below to
    leave the placeholder VOLUME the written LOCATION would then carry -
    the LOCATION Traktor cannot resolve.
    """
    result = _fixture_result()
    decisions = WizardState()
    key = result.old_records[1].primary_key
    decisions.accept(key, index=1)
    amended = apply(result, decisions)
    promoted = amended[key]
    assert promoted.location.volume == "D:"
    assert promoted.location.volumeid == "D:"
    assert promoted.location.volume != "scan-placeholder"

    # Negative control: the raw candidate, before re-encoding, still
    # carries the placeholder identity.
    raw_candidate = result.reviews[1].candidates[1].candidate
    assert raw_candidate.location.volume == "scan-placeholder", (
        "observed: without re-encoding, the promoted candidate's LOCATION would still "
        "carry the scan placeholder VOLUME rather than D:"
    )


def test_accept_alternative_uses_its_own_scan_root_identity_not_a_sibling_roots() -> None:
    """Two scan roots share the anchor D: but were given different
    --volume-map identities (D:/New -> NEW/NEW, D:/Old -> OLD/OLD). The
    promoted candidate's source_path sits under D:/New, and the amended
    mapping must carry NEW/NEW - the identity of the root it actually
    resolves under - not OLD/OLD.

    Observed by restoring the removed heuristic - an anchor-keyed
    ("D:") registry populated from result.mapping's existing winners -
    in place of the current per-candidate volume_identities resolution
    and rerunning this exact scenario: the promoted candidate's LOCATION
    carried OLD/OLD (asserting == "NEW" failed with
    AssertionError: assert 'OLD' == 'NEW'), because the winner from
    D:/Old shares the D: anchor and is the only entry the anchor-keyed
    registry has for it. The current code resolves per candidate against
    volume_identities instead and is asserted below to produce NEW/NEW.
    """
    old = _record("song.mp3", volume="Z:", volumeid="Z:", dirv="/:gone/:")
    winner_from_old_root = _record(
        "other.mp3", volume="OLD", volumeid="OLD", dirv="/:old/:",
        source_path=Path("D:/Old/other.mp3"),
    )
    alternative_from_new_root = _record(
        "song.mp3", volume="scan-placeholder", volumeid="scan-placeholder", dirv="/:new/:",
        source_path=Path("D:/New/song.mp3"),
    )
    review = RecordReview(
        old=old, status="ambiguous",
        candidates=(
            CandidateView(candidate=winner_from_old_root, key_name="filename", refuted=False),
            CandidateView(candidate=alternative_from_new_root, key_name="bare_name", refuted=False),
        ),
        chosen=None, matched_by=None,
    )
    other_old = _record("other.mp3", volume="Z:", volumeid="Z:", dirv="/:gone2/:")
    result = ReconnectResult(
        mapping={other_old.primary_key: winner_from_old_root},
        stats={"matched": 1, "unmatched": 1},
        ambiguity_rows=[],
        old_records=[other_old, old],
        warnings=[],
        diagnostics=(),
        reviews=(review,),
        volume_identities={
            Path("D:/Old"): ("OLD", "OLD"),
            Path("D:/New"): ("NEW", "NEW"),
        },
    )
    decisions = WizardState()
    decisions.accept(old.primary_key, index=1)
    amended = apply(result, decisions)
    promoted = amended[old.primary_key]
    assert promoted.location.volume == "NEW"
    assert promoted.location.volumeid == "NEW"
    assert promoted.location.volume != "OLD", (
        "observed: an anchor-only lookup applies the D: sibling root's OLD/OLD identity "
        "to a candidate that actually resolves under D:/New"
    )


def test_accept_alternative_with_no_winner_from_its_volume_still_resolves() -> None:
    """The promoted candidate is the only record from its volume - no
    already-resolved winner in result.mapping shares its volume at all -
    yet the amended mapping still carries the correct resolved identity,
    because resolution reads result.volume_identities (populated once
    per run from every scan root) rather than searching the mapping's
    existing winners for one to borrow an identity from.

    Observed by restoring the removed heuristic - a registry built only
    from candidates already present in result.mapping - in place of the
    current per-candidate volume_identities resolution and rerunning
    this exact scenario (an empty mapping): the promoted candidate's
    LOCATION was left unchanged, still carrying the scan-placeholder
    VOLUME (asserting == "E:" failed with
    AssertionError: assert 'scan-placeholder' == 'E:'), because the
    registry built from an empty mapping has no entry for this
    candidate's anchor. The current code resolves against
    volume_identities instead and is asserted below to produce E:/E:.
    """
    old = _record("lonely.mp3", volume="Z:", volumeid="Z:", dirv="/:gone/:")
    candidate = _record(
        "lonely.mp3", volume="scan-placeholder", volumeid="scan-placeholder", dirv="/:vault/:",
        source_path=Path("E:/vault/lonely.mp3"),
    )
    review = RecordReview(
        old=old, status="ambiguous",
        candidates=(CandidateView(candidate=candidate, key_name="bare_name", refuted=False),),
        chosen=None, matched_by=None,
    )
    result = ReconnectResult(
        mapping={},
        stats={"matched": 0, "unmatched": 1},
        ambiguity_rows=[],
        old_records=[old],
        warnings=[],
        diagnostics=(),
        reviews=(review,),
        volume_identities={Path("E:/vault"): ("E:", "E:")},
    )
    decisions = WizardState()
    decisions.accept(old.primary_key, index=0)
    amended = apply(result, decisions)
    promoted = amended[old.primary_key]
    assert promoted.location.volume == "E:"
    assert promoted.location.volumeid == "E:"
    assert promoted.location.volume != "scan-placeholder", (
        "observed: with no already-resolved winner sharing this candidate's volume, an "
        "anchor-registry lookup finds no entry and silently leaves the scan-placeholder LOCATION"
    )


def test_accept_alternative_with_no_matching_scan_root_raises() -> None:
    """A promoted candidate whose source_path resolves under no scan
    root in result.volume_identities at all raises
    reconnect_run.UnresolvedCandidateVolume rather than shipping the
    scan-placeholder LOCATION through unchanged."""
    old = _record("orphan.mp3", volume="Z:", volumeid="Z:", dirv="/:gone/:")
    candidate = _record(
        "orphan.mp3", volume="scan-placeholder", volumeid="scan-placeholder", dirv="/:elsewhere/:",
        source_path=Path("F:/elsewhere/orphan.mp3"),
    )
    review = RecordReview(
        old=old, status="ambiguous",
        candidates=(CandidateView(candidate=candidate, key_name="bare_name", refuted=False),),
        chosen=None, matched_by=None,
    )
    result = ReconnectResult(
        mapping={},
        stats={"matched": 0, "unmatched": 1},
        ambiguity_rows=[],
        old_records=[old],
        warnings=[],
        diagnostics=(),
        reviews=(review,),
        volume_identities={Path("E:/vault"): ("E:", "E:")},
    )
    decisions = WizardState()
    decisions.accept(old.primary_key, index=0)
    with pytest.raises(reconnect_run.UnresolvedCandidateVolume):
        apply(result, decisions)


def test_picking_is_not_accepting() -> None:
    """Picking a candidate leaves the row undecided and leaves the
    amended mapping unchanged."""
    result = _fixture_result()
    decisions = WizardState()
    key = result.old_records[1].primary_key
    decisions.pick(key, 1)
    assert decisions.decision_state(key) == "undecided"
    amended = apply(result, decisions)
    assert amended == result.mapping


def test_undo_returns_to_the_zero_override_mapping() -> None:
    """Accept then undo, and reject then undo, both return the amended
    mapping to the zero-override mapping."""
    result = _fixture_result()
    zero = apply(result, WizardState())

    accepted_then_undone = WizardState()
    key = result.old_records[1].primary_key
    accepted_then_undone.accept(key, index=1)
    accepted_then_undone.undo(key)
    assert apply(result, accepted_then_undone) == zero

    rejected_then_undone = WizardState()
    other_key = result.old_records[0].primary_key
    rejected_then_undone.reject(other_key)
    rejected_then_undone.undo(other_key)
    assert apply(result, rejected_then_undone) == zero


def test_write_refusal_reports_the_collision_reason(tmp_path: Path) -> None:
    """A state whose output equals its input reports the refusal string
    as its reason and reports the control disabled."""
    same = tmp_path / "collection.nml"
    reason = write_refusal(same, same)
    assert reason == "output_must_differ_from_input"
    assert write_refusal(same, tmp_path / "different.nml") is None


def test_write_refusal_sentence_covers_the_real_token(tmp_path: Path) -> None:
    """write_refusal_sentence names an operator-facing sentence, not
    the bare diagnostic token, for the one refusal token
    output_collision_refusal (rewrite.py) can actually return -
    constructed here the same way write_refusal does at the write
    core (two paths resolving to the same file), not transcribed as a
    literal string, so a change to that token's spelling would show up
    here too."""
    same = tmp_path / "collection.nml"
    token = output_collision_refusal(same, same)
    assert token is not None
    sentence = write_refusal_sentence(token)
    assert sentence != token
    assert "Output collection path" in sentence
    assert "Set up" in sentence


def test_an_unmapped_refusal_token_falls_back_rather_than_raising() -> None:
    """A token _WRITE_REFUSAL_SENTENCES was never given a sentence for
    still returns a visible string rather than raising - the Write
    step's own render() must not crash if this mapping and
    output_collision_refusal's real return values ever drift apart
    despite the guard below."""
    sentence = write_refusal_sentence("a_token_nobody_mapped")
    assert sentence == "Write refused: a_token_nobody_mapped"


def test_a_missing_sentence_for_the_real_token_is_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutation: wizard_state's real _WRITE_REFUSAL_SENTENCES dict is
    patched to one with its only entry (output_must_differ_from_input)
    removed, standing in for a forgotten mapping the day
    output_collision_refusal gains a second token. Observed:
    write_refusal_sentence, called with the same token
    output_collision_refusal actually returns, falls back to
    'Write refused: output_must_differ_from_input' instead of the real
    operator sentence test_write_refusal_sentence_covers_the_real_token
    checks for."""
    same = tmp_path / "collection.nml"
    token = output_collision_refusal(same, same)
    monkeypatch.setattr(wizard_state_module, "_WRITE_REFUSAL_SENTENCES", {})
    assert write_refusal_sentence(token) == f"Write refused: {token}"


def test_amended_result_carries_everything_but_mapping() -> None:
    """amended_result over an empty decision set is equal field for
    field to the result passed in; over a decision set rejecting one
    record it differs in mapping alone.

    Negative control: an amended_result stand-in that recomputes stats
    from the amended mapping is shown below to diverge from the scan's
    own stats on the two keys a naive recount would touch.
    """
    result = _fixture_result()
    empty = amended_result(result, WizardState())
    assert empty == result

    decisions = WizardState()
    key = result.old_records[1].primary_key
    decisions.reject(key)
    amended = amended_result(result, decisions)
    assert amended.mapping != result.mapping
    assert amended.stats == result.stats
    assert amended.ambiguity_rows == result.ambiguity_rows
    assert amended.old_records == result.old_records
    assert amended.reviews == result.reviews
    assert amended.warnings == result.warnings
    assert amended.diagnostics == result.diagnostics

    # Negative control: recompute stats from the amended mapping instead
    # of carrying the scan's own record through.
    recomputed_matched = len(apply(result, decisions))
    assert recomputed_matched == result.stats["matched"] - 1, (
        "observed: a naive recount from the amended mapping reports matched=1 against "
        "the scan's own stats['matched']=2, the divergence carrying stats through avoids"
    )


def test_fingerprint_control_state_provider_none_skips_the_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """With fingerprint_key_provider set to None, fingerprint_control_state
    returns disabled with the not-installed reason, and
    fingerprint_unavailable_reason is never called."""
    calls: list[None] = []
    monkeypatch.setattr(reconnect_run, "fingerprint_key_provider", None)
    monkeypatch.setattr(reconnect_run, "fingerprint_unavailable_reason", lambda: calls.append(None))

    state = fingerprint_control_state()
    assert state.enabled is False
    assert state.reason == "fingerprint_key_provider unavailable (traktor_nml.fingerprint not installed)"
    assert calls == [], "expected the probe never to be called when the provider is None"


def test_fingerprint_control_state_provider_present_probe_returns_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reconnect_run, "fingerprint_key_provider", lambda *a, **k: None)
    monkeypatch.setattr(reconnect_run, "fingerprint_unavailable_reason", lambda: "pyacoustid is not installed")

    state = fingerprint_control_state()
    assert state.enabled is False
    assert state.reason == "pyacoustid is not installed"


def test_fingerprint_control_state_provider_present_probe_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reconnect_run, "fingerprint_key_provider", lambda *a, **k: None)
    monkeypatch.setattr(reconnect_run, "fingerprint_unavailable_reason", lambda: None)

    state = fingerprint_control_state()
    assert state.enabled is True
    assert state.reason is None


def test_fingerprint_control_state_negative_control_unconditional_probe_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative control for the provider-is-None ordering: replacing the
    real two-step check with an implementation that calls
    fingerprint_unavailable_reason() unconditionally, in the same
    provider-is-None state the first test above sets up, raises
    TypeError: 'NoneType' object is not callable - the exact failure the
    setup screen would raise on a machine with no pyacoustid/fpcalc if
    the ordering were wrong.
    """
    monkeypatch.setattr(reconnect_run, "fingerprint_key_provider", None)
    monkeypatch.setattr(reconnect_run, "fingerprint_unavailable_reason", None)

    def broken_fingerprint_control_state():
        # Unconditional call, skipping the provider-is-None short circuit.
        return reconnect_run.fingerprint_unavailable_reason()

    with pytest.raises(TypeError, match="NoneType.*not callable"):
        broken_fingerprint_control_state()

    # The real implementation does not raise in this state.
    state = fingerprint_control_state()
    assert state.enabled is False


def test_build_volume_map_shape_matches_parse_volume_map_and_resolves() -> None:
    """build_volume_map's output feeds parse_volume_map (the same
    function reconnect_run.py:159 calls with args.volume_map) without
    reshaping, and the resulting mapping resolves a scan root through
    resolve_volume_identity with no old-collection records to infer
    from - the exact situation the wizard hits on every real reconnect,
    since the mapping always wins when the root matches.

    Run with scan_roots=[Path("C:/music")] and
    entries=[("C:", "C:")]: build_volume_map returns
    [["C:\\music", "C:", "C:"]] (observed), which parse_volume_map turns
    into {"C:\\music": ("C:", "C:")}, and resolve_volume_identity(root,
    [], that_map) returns ("C:", "C:") rather than raising, even though
    old_records is empty and prefix inference alone would find nothing
    to agree on.
    """
    root = Path("C:/music")
    triples = build_volume_map([root], [("C:", "C:")])
    assert triples == [[str(root), "C:", "C:"]]

    resolved_map = parse_volume_map(triples)
    assert resolved_map == {str(root): ("C:", "C:")}
    assert resolve_volume_identity(root, [], resolved_map) == ("C:", "C:")


def test_build_volume_map_omits_blank_pairs_and_returns_none_when_all_blank() -> None:
    """A scan root whose VOLUME/VOLUMEID boxes were never filled in must
    not reach parse_volume_map as an empty-string triple - that would
    make resolve_volume_identity match and return ("", ""), a wrong
    identity, instead of falling through to prefix inference or its
    hard error.

    Run with scan_roots=[Path("C:/music"), Path("D:/audio")] and
    entries=[("C:", "C:"), ("", "")]: build_volume_map returns
    [["C:\\music", "C:", "C:"]] (observed) - the second, blank pair is
    dropped rather than sent as ["D:\\audio", "", ""].

    Run again with both pairs blank
    (entries=[("", ""), ("", "")]): build_volume_map returns None
    (observed), not [] - matching parse_volume_map's own entries=None
    default, so the wizard's args.volume_map is None exactly when the
    operator supplied nothing, the same absence
    test_absent_volume_map_and_ambiguous_prefix_is_hard_error
    (tests/test_reconnect.py) exercises as a hard error.
    """
    music = Path("C:/music")
    audio = Path("D:/audio")

    partial = build_volume_map([music, audio], [("C:", "C:"), ("", "")])
    assert partial == [[str(music), "C:", "C:"]]

    all_blank = build_volume_map([music, audio], [("", ""), ("", "")])
    assert all_blank is None


def test_scan_root_without_a_mapping_raises_while_a_mapped_root_resolves() -> None:
    """Same scan root, same (empty) old_records: with a volume_map entry
    resolve_volume_identity resolves it; without one it raises - the
    hard-error contract resolve_volume_identity's own docstring states
    ("no observations ... raises, naming scan_root") and this wizard
    hits on every real reconnect, since the premise is that the files
    moved and no old record's decoded path sits under the scan root.

    Run with root=Path("C:/music"), old_records=[]: resolve_volume_identity(
    root, [], {"C:\\music": ("C:", "C:")}) returns ("C:", "C:")
    (observed); resolve_volume_identity(root, [], None) raises
    VolumeIdentityError with message
    "volume_identity_ambiguous scan_root=C:/music observed_pairs=[]; pass --volume-map"
    (observed).
    """
    root = Path("C:/music")
    mapped = resolve_volume_identity(root, [], {str(root): ("C:", "C:")})
    assert mapped == ("C:", "C:")

    with pytest.raises(VolumeIdentityError, match=r"volume_identity_ambiguous scan_root=C:/music observed_pairs=\[\]"):
        resolve_volume_identity(root, [], None)


def test_default_volume_identity_uses_scan_roots_anchor() -> None:
    """default_volume_identity's guess is the scan root's own filesystem
    anchor, used for both VOLUME and VOLUMEID, trimmed of the trailing
    separator Path.anchor carries on Windows - matching the VOLUME/
    VOLUMEID convention tests/test_reconnect.py's own --volume-map
    triples use (e.g. --volume-map <root> C: C:).

    Run with scan_root=Path("C:/music"): default_volume_identity returns
    ("C:", "C:") (observed) - Path("C:/music").anchor is "C:\\", and
    rstrip("\\\\/") trims it to "C:".
    """
    assert default_volume_identity(Path("C:/music")) == ("C:", "C:")

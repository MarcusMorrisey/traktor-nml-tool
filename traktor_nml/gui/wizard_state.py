"""The operator's decisions and the amended mapping they produce, with no
framework import.

A decision per primary key over undecided, accepted and left_missing,
plus the index of the picked candidate, so picking a candidate changes
which file is proposed while the row stays undecided, as Specs requires.
apply(result, decisions) builds the amended mapping from result.mapping
plus the decision set; amended_result wraps it into the ReconnectResult
the wizard hands to reconnect_run.write_reconnect_result.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from .. import reconnect_run
from ..model import EntryRecord
from ..reconnect import location_from_disk_path
from ..reconnect_run import ReconnectResult
from ..review import RecordReview
from ..rewrite import output_collision_refusal

from .review_model import ACCEPTED, LEFT_MISSING, UNDECIDED


@dataclass(frozen=True)
class _Decision:
    """One record's decision state plus the candidate index it has
    picked, if any. picked_index indexes review.candidates for the
    record this decision belongs to; None means "the matcher's own
    winner" rather than "no candidate available"."""

    state: str = UNDECIDED
    picked_index: Optional[int] = None


class WizardState:
    """The operator's decisions, keyed by old-record primary key.

    Every record starts absent from _decisions, which decision_state and
    picked_index both read back as undecided/None - the same starting
    point a record explicitly set back to undecided by undo() reaches,
    so a fresh WizardState and one that has undone every decision behave
    identically.
    """

    def __init__(self) -> None:
        self._decisions: dict[str, _Decision] = {}

    def decision_state(self, key: str) -> str:
        return self._decisions.get(key, _Decision()).state

    def picked_index(self, key: str) -> Optional[int]:
        return self._decisions.get(key, _Decision()).picked_index

    def pick(self, key: str, index: Optional[int]) -> None:
        """Record which candidate is proposed for key without deciding
        anything: the row stays (or becomes) undecided."""
        self._decisions[key] = _Decision(state=UNDECIDED, picked_index=index)

    def accept(self, key: str, index: Optional[int] = None) -> None:
        """Accept key, either the matcher's own winner (index omitted)
        or the previously picked / explicitly given candidate index."""
        if index is None:
            index = self.picked_index(key)
        self._decisions[key] = _Decision(state=ACCEPTED, picked_index=index)

    def reject(self, key: str) -> None:
        self._decisions[key] = _Decision(state=LEFT_MISSING, picked_index=self.picked_index(key))

    def undo(self, key: str) -> None:
        """Return key to undecided from either terminal state (accepted
        or left_missing)."""
        self._decisions[key] = _Decision(state=UNDECIDED, picked_index=self.picked_index(key))

    def items(self):
        return self._decisions.items()


def _reencoded(candidate: EntryRecord, volume_identities: dict[Path, tuple[str, str]]) -> EntryRecord:
    """A promoted candidate carries a resolved VOLUME/VOLUMEID rather
    than the scan placeholder, found by testing candidate.source_path
    against each scan root's own resolved identity in
    result.volume_identities - the same per-scan-root subtree test
    reconnect_run._reencode_winning_locations applies to a matcher's own
    winner, shared here via reconnect_run.resolve_candidate_volume_identity
    rather than re-derived from source_path.anchor. Raises
    reconnect_run.UnresolvedCandidateVolume when no scan root claims
    candidate.source_path, rather than letting the placeholder LOCATION
    reach the write path."""
    if candidate.source_path is None:
        return candidate
    identity = reconnect_run.resolve_candidate_volume_identity(candidate.source_path, volume_identities)
    return replace(candidate, location=location_from_disk_path(candidate.source_path, *identity))


def apply(result: ReconnectResult, decisions: WizardState) -> dict[str, EntryRecord]:
    """The amended mapping: result.mapping with every left_missing
    record's key dropped and every accepted record's picked candidate
    (when it differs from the matcher's own winner) inserted, re-encoded.

    With no decisions at all the returned mapping equals result.mapping
    key for key and value for value - undecided records, and records
    with no decision entry at all, leave their mapping entry untouched.
    """
    reviews_by_key: dict[str, RecordReview] = {review.old.primary_key: review for review in result.reviews}
    amended: dict[str, EntryRecord] = dict(result.mapping)

    for key, decision in decisions.items():
        if decision.state == LEFT_MISSING:
            amended.pop(key, None)
        elif decision.state == ACCEPTED:
            review = reviews_by_key.get(key)
            if review is None:
                continue
            if decision.picked_index is not None:
                candidate = review.candidates[decision.picked_index].candidate
            else:
                candidate = review.chosen
            if candidate is None:
                continue
            if candidate is not amended.get(key):
                amended[key] = _reencoded(candidate, result.volume_identities)
        # UNDECIDED: the mapping entry, if any, is left exactly as the
        # scan produced it - picking a candidate changes only what a
        # future accept() would promote, not the amended mapping itself.

    return amended


def amended_result(result: ReconnectResult, decisions: WizardState) -> ReconnectResult:
    """The ReconnectResult the wizard hands to write_reconnect_result:
    mapping alone is replaced with apply(result, decisions); stats,
    ambiguity_rows, old_records, reviews, warnings and diagnostics carry
    through as the scan's own record of what the matcher found, which no
    operator decision revises (DL-076)."""
    return replace(result, mapping=apply(result, decisions))


def write_refusal(input_path: Path, output_path: Path, extra_inputs: tuple[Path, ...] = ()) -> Optional[str]:
    """The Write control's inline reason, or None when the write is not
    refused - the same rule output_collision_refusal enforces at the
    write core, asked here before any work is done."""
    return output_collision_refusal(input_path, output_path, extra_inputs)


@dataclass(frozen=True)
class FingerprintControlState:
    enabled: bool
    reason: Optional[str] = None


def fingerprint_control_state() -> FingerprintControlState:
    """Whether the fingerprint control is offered and, when it is not,
    why - in reconnect_run's own two steps and its own order.

    Step one: fingerprint_key_provider is None means traktor_nml.fingerprint
    itself was not importable (the except ImportError block at
    reconnect_run.py:48-53 binds both names to None together), and the
    control is disabled with the not-installed reason without
    fingerprint_unavailable_reason being called at all - calling it in
    this state raises TypeError: 'NoneType' object is not callable.
    Step two, reached only when the provider is not None:
    fingerprint_unavailable_reason() is called, a non-None return
    disables the control carrying that text, and None leaves it enabled.
    Both names are read through the reconnect_run module object rather
    than imported directly, so a test's monkeypatch.setattr on either
    name is visible here.
    """
    if reconnect_run.fingerprint_key_provider is None:
        return FingerprintControlState(
            enabled=False,
            reason="fingerprint_key_provider unavailable (traktor_nml.fingerprint not installed)",
        )
    reason = reconnect_run.fingerprint_unavailable_reason()
    if reason is not None:
        return FingerprintControlState(enabled=False, reason=reason)
    return FingerprintControlState(enabled=True, reason=None)

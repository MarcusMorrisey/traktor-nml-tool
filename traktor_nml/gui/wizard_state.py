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


def default_volume_identity(scan_root: Path) -> tuple[str, str]:
    """The Set up step's starting guess for one scan root's VOLUME and
    VOLUMEID boxes: its filesystem anchor (e.g. "C:" on Windows, "/" on
    POSIX) used for both fields, trimmed of the trailing separator
    Path.anchor carries on Windows ("C:\\" -> "C:") so the guess matches
    the VOLUME/VOLUMEID strings tests/test_reconnect.py's own
    --volume-map triples use (e.g. --volume-map <root> C: C:), rather
    than a value nothing else in this codebase writes. Falls back to the
    untrimmed anchor when trimming empties it (a POSIX root's anchor is
    just "/"), so a POSIX scan root still gets a non-blank guess."""
    anchor = Path(scan_root).anchor
    trimmed = anchor.rstrip("\\/")
    value = trimmed or anchor
    return (value, value)


def build_volume_map(
    scan_roots: list[Path], entries: list[tuple[str, str]]
) -> Optional[list[list[str]]]:
    """The Set up step's per-scan-root VOLUME/VOLUMEID box pairs turned
    into the triple shape parse_volume_map (traktor_nml/volumes.py:83)
    accepts: one [scan_root, volume, volumeid] list per scan_roots entry
    whose paired box in entries (same order, zipped positionally) holds
    a non-blank value in both fields. A pair left blank in either box is
    omitted rather than sent as an empty-string triple, so
    resolve_volume_identity falls through to its own prefix inference -
    or its hard error - for that root instead of matching an empty
    VOLUME/VOLUMEID that was never a real identity. Returns None, not
    [], when no scan root produced an entry at all, matching
    parse_volume_map's own entries=None default and reconnect_run's
    args.volume_map contract (_build_args, traktor_nml/gui/app.py)."""
    triples = [
        [str(root), volume.strip(), volumeid.strip()]
        for root, (volume, volumeid) in zip(scan_roots, entries)
        if volume.strip() and volumeid.strip()
    ]
    return triples or None


def write_refusal(input_path: Path, output_path: Path, extra_inputs: tuple[Path, ...] = ()) -> Optional[str]:
    """The Write control's inline reason, or None when the write is not
    refused - the same rule output_collision_refusal enforces at the
    write core, asked here before any work is done."""
    return output_collision_refusal(input_path, output_path, extra_inputs)


# output_collision_refusal (rewrite.py) has exactly one non-None return
# value - "output_must_differ_from_input", raised when output_path
# resolves to input_path or to any path in extra_inputs; it never
# returns any other string. Errors.dc.html names the same defect under
# its own token, output_collides_with_input (a different literal than
# this codebase's own token, so the two are cited as the same finding
# rather than the same string), with the heading "That would overwrite
# the collection you are repairing" and the fix "Choose another
# file...". This dict is total over output_collision_refusal's actual
# return values, not partial: a token this map does not name is a
# programming error in this module, not a reachable operator-facing
# state, which is what tests/test_gui_wizard_state.py's guard pins.
_WRITE_REFUSAL_SENTENCES = {
    "output_must_differ_from_input": (
        "The output path is the same file this run reads from. "
        "Set a different path in Output collection path, on Set up."
    ),
}


def write_refusal_sentence(token: str) -> str:
    """The operator-facing sentence for one write_refusal() token -
    naming what is wrong and which control fixes it, rather than the
    bare diagnostic token write_refusal() itself returns (which stays
    unchanged, for a log line or a guard pinning the predicate's own
    return value - this function only decides what the Write step
    renders). Falls back to naming the raw token rather than raising,
    so an unmapped token - which _WRITE_REFUSAL_SENTENCES' own guard
    exists to prevent - degrades to a bare but visible label instead
    of an unhandled exception breaking the Write step's render."""
    return _WRITE_REFUSAL_SENTENCES.get(token, f"Write refused: {token}")


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

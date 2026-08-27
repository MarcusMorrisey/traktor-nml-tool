"""Per-record review data: what the matcher considered for one old record.

Imports only from model.py so nothing above the matcher - reconnect.py,
reconnect_run.py, a future review surface - is needed to read a
RecordReview back. match_records builds these only when a caller supplies
on_review; with it left at None nothing here is constructed at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .model import EntryRecord


@dataclass(frozen=True)
class RefutationDetail:
    """The size or duration contradiction that removed one candidate.

    field, old and candidate carry the values _refutation_reason compared;
    difference and allowance are the same two numbers the comparison used,
    in the units that arithmetic used (kilobytes for size, seconds for
    duration), so a caller displaying this detail quantifies it against
    the same allowance that removed the candidate rather than a second
    computation of it.
    """

    field: str  # "duration" or "size"
    old_value: float
    candidate_value: float
    difference: float
    allowance: float


@dataclass(frozen=True)
class CandidateView:
    """One candidate a tier offered for an old record, before or after
    refutation removed it."""

    candidate: EntryRecord
    key_name: str
    refuted: bool
    detail: Optional[RefutationDetail] = None


@dataclass(frozen=True)
class RecordReview:
    """One old record's outcome: the status match_records (and, for
    destination_collision, resolve_reconnection) assigned it, the
    candidates considered in cascade order, and the winner when there was
    one.

    The five statuses are exactly the outcomes the matcher and the
    one-to-one post-pass produce; the two operator statuses a review
    surface may show, rejected and left-missing, are absent because no
    code below that surface can know them - they name a decision an
    operator makes, not an outcome the matcher or the collision pass
    computed.
    """

    old: EntryRecord
    status: str  # matched | ambiguous | refuted | unmatched | destination_collision
    candidates: tuple[CandidateView, ...]
    chosen: Optional[EntryRecord] = None
    matched_by: Optional[str] = None

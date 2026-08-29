"""The reconnect wizard's announcement text and its politeness
(Specs.dc.html, "Accessibility rules"): scan progress as a count of a
total, each decision as the track name with the decision and its
position in the queue, and the error and completion sentences that
name the file consequence in the first clause. Imports no nicegui
(DL-083).
"""

from __future__ import annotations

# The two ARIA live-region politeness levels app.py's live regions carry.
POLITE = "polite"
ASSERTIVE = "assertive"


def progress_message(done: int, total: int) -> str:
    """'4,212 of 12,542' (Specs.dc.html, "Accessibility rules")."""
    return f"{done:,} of {total:,}"


def decision_message(track_name: str, decision: str, position: int, total: int) -> str:
    """'Bar A Thym accepted - 458 of 1,238 done' (Specs.dc.html,
    "Accessibility rules")."""
    return f"{track_name} {decision} - {position:,} of {total:,} done"


def error_message(file_name: str, detail: str) -> str:
    """Names the file consequence in the first clause, assertive
    (Specs.dc.html, "Accessibility rules")."""
    return f"{file_name} was not written: {detail}"


def completion_message(file_name: str) -> str:
    """Names the file consequence in the first clause, assertive
    (Specs.dc.html, "Accessibility rules")."""
    return f"{file_name} was written."


# The politeness Specs assigns each message kind - progress and
# decision are polite, error and completion are assertive
# (Specs.dc.html, "Accessibility rules"; DL-083).
POLITENESS = {
    "progress": POLITE,
    "decision": POLITE,
    "error": ASSERTIVE,
    "completion": ASSERTIVE,
}


class ProgressAnnouncer:
    """Gates progress messages to at most one every two seconds
    (Specs.dc.html, "Accessibility rules"), against a clock value
    passed in rather than read from the module so the throttle is
    exercised by the suite without a real clock (DL-083). Decision,
    error and completion messages are not rated by Specs and pass
    untouched through announce (not gate)."""

    def __init__(self) -> None:
        # None means no progress message has been gated yet, so the first call always emits.
        self._last_emitted_at: float | None = None

    def gate_progress(self, now: float, done: int, total: int) -> str | None:
        """The progress message to announce at clock value `now`, or
        None when fewer than two seconds have passed since the last
        one emitted."""
        if self._last_emitted_at is not None and now - self._last_emitted_at < 2.0:
            return None
        self._last_emitted_at = now
        return progress_message(done, total)

    def reset(self) -> None:
        """Clears the throttle, for a fresh scan starting the count
        over."""
        self._last_emitted_at = None

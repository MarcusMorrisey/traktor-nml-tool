"""Guards the announcement rules (Specs.dc.html, "Accessibility
rules"): the throttle keeps a second progress message inside two
seconds withheld, each message kind carries the politeness Specs
assigns it, the error and completion sentences name the file
consequence first, and every live-region push in app.py routes
through announce.py rather than a literal string (DL-083).
"""

from __future__ import annotations

import re
from pathlib import Path

from traktor_nml.gui import announce

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"


def test_a_second_progress_message_inside_two_seconds_is_withheld():
    """The throttle's core case: a message at 0.0s emits, a second at 1.5s (inside the 2.0s window) is withheld."""
    gate = announce.ProgressAnnouncer()
    first = gate.gate_progress(0.0, 100, 1000)
    second = gate.gate_progress(1.5, 200, 1000)
    assert first == "100 of 1,000"
    assert second is None


def test_the_message_after_two_seconds_is_emitted():
    gate = announce.ProgressAnnouncer()
    gate.gate_progress(0.0, 100, 1000)
    third = gate.gate_progress(2.0, 300, 1000)
    assert third == "300 of 1,000"


def test_a_message_just_under_the_two_second_floor_is_withheld():
    """At 1.9s - inside the real 2.0s window - the gate withholds a
    second message, returning None rather than the progress string a
    caller past the floor would receive; this is the boundary
    test_the_message_after_two_seconds_is_emitted clears from the
    other side, at exactly 2.0s."""
    gate = announce.ProgressAnnouncer()
    gate.gate_progress(0.0, 1, 10)
    assert gate.gate_progress(1.9, 2, 10) is None


def test_each_message_kind_carries_its_specified_politeness():
    assert announce.POLITENESS["progress"] == announce.POLITE
    assert announce.POLITENESS["decision"] == announce.POLITE
    assert announce.POLITENESS["error"] == announce.ASSERTIVE
    assert announce.POLITENESS["completion"] == announce.ASSERTIVE


def test_error_and_completion_name_the_file_consequence_first():
    error = announce.error_message("collection.nml", "disk full")
    completion = announce.completion_message("collection.nml")
    assert error.startswith("collection.nml")
    assert completion.startswith("collection.nml")


_LIVE_REGION_START = re.compile(
    r"(polite_region|assertive_region|state\.polite_region|state\.assertive_region)\.set_text\("
)
# Names assigned directly from ProgressAnnouncer.gate_progress(...) -
# the one non-announce-prefixed expression a live-region push may
# legitimately carry, since gate_progress itself returns
# announce.progress_message(...) or None (DL-083).
_ANNOUNCE_ASSIGNMENT = re.compile(r"(\w+)\s*=\s*state\.progress_announcer\.gate_progress\(")


def _iter_live_region_pushes(source: str):
    """Yields (region_name, expr) for each '<region>.set_text(...)'
    call in source, matching the closing parenthesis by depth rather
    than by a single-level regex, so a call whose argument itself
    contains parentheses - e.g. announce.error_message(str(...), ...)
    spanning multiple lines - is still captured whole rather than cut
    off at the first ')'."""
    pushes = []
    for m in _LIVE_REGION_START.finditer(source):
        region = m.group(1)
        depth = 1
        i = m.end()
        while i < len(source) and depth > 0:
            if source[i] == "(":
                depth += 1
            elif source[i] == ")":
                depth -= 1
            i += 1
        pushes.append((region, source[m.end():i - 1]))
    return pushes


def test_live_region_scan_captures_a_nested_paren_call():
    """The real error-message push (app.py, on_progress's caller)
    spans multiple lines and nests str(...) inside
    announce.error_message(...); the depth-matching scan must still
    capture it whole rather than stopping at the first ')'."""
    source = _APP_PY.read_text(encoding="utf-8")
    pushes = _iter_live_region_pushes(source)
    assert any("error_message" in expr for _region, expr in pushes)


def test_live_regions_are_pushed_only_from_announce_py():
    source = _APP_PY.read_text(encoding="utf-8")
    pushes = _iter_live_region_pushes(source)
    assert pushes, "no live-region .set_text( push found in app.py"
    announce_sourced = set(_ANNOUNCE_ASSIGNMENT.findall(source))
    for _region, expr in pushes:
        assert "announce." in expr or expr.strip() in announce_sourced, (
            f"live region pushed something other than an announce.py "
            f"call or a name assigned from progress_announcer.gate_progress: {expr!r}"
        )


def test_live_region_source_check_catches_a_literal_string():
    """Mutation: a copy of app.py's real source has its real
    announce.py-routed completion push replaced with a literal string
    pushed directly. Observed: the same depth-matching scan
    test_live_regions_are_pushed_only_from_announce_py runs, pointed
    at the mutated copy, finds a push whose expression contains
    neither 'announce.' nor a progress_announcer-sourced name."""
    real_source = _APP_PY.read_text(encoding="utf-8")
    mutated = re.sub(
        r"state\.assertive_region\.set_text\(announce\.completion_message\([^)]*\)\)",
        'state.assertive_region.set_text("Something went wrong")',
        real_source,
        count=1,
    )
    assert mutated != real_source, "fixture assumption stale: completion push not found"
    pushes = _iter_live_region_pushes(mutated)
    announce_sourced = set(_ANNOUNCE_ASSIGNMENT.findall(mutated))
    bad = [
        (region, expr) for region, expr in pushes
        if "announce." not in expr and expr.strip() not in announce_sourced
    ]
    assert bad, "mutation was not detected by the live-region source scan"

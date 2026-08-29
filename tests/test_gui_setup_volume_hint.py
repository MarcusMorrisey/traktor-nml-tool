"""Guard for the Set up step's Volume/Volume ID hint (app.py's
add_scan_root): the design set has no artboard for this control, and
the maintainer reported not understanding what belongs in the two
fields it renders. A note line, visible without hovering and styled
the same as the step's existing cache-path note
(wizard-subtle-3 wizard-note), states what the fields are and why they
exist.
"""

from __future__ import annotations

from pathlib import Path

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"


def _volume_to_cache_span(source: str) -> str:
    """The source between the Volume ID input and the next control
    down, the cache-path input - bounded by a named anchor rather than
    a character count, so the check is not fooled by the step's own
    later cache-path note (also wizard-subtle-3 wizard-note) the way
    an unbounded or fixed-width search would be."""
    volume_index = source.index('ui.input("Volume ID"')
    cache_index = source.index("cache_input = ui.input(", volume_index)
    return source[volume_index:cache_index]


def test_volume_fields_carry_a_visible_hint():
    """A note between the Volume/Volume ID row and the cache-path
    input names VOLUME and VOLUMEID, the collection's own entries, the
    pre-filled drive guess, and PRIMARYKEY - the DL-005 consequence of
    a wrong or empty VOLUMEID - styled wizard-subtle-3 wizard-note like
    the step's existing cache-path note rather than a hover-only
    tooltip."""
    source = _APP_PY.read_text(encoding="utf-8")
    span = _volume_to_cache_span(source)
    assert "wizard-subtle-3 wizard-note" in span, "no note found between the Volume ID input and the cache-path input"
    assert "VOLUME" in span
    assert "VOLUMEID" in span
    assert "PRIMARYKEY" in span


def test_a_removed_volume_hint_is_caught():
    """Mutation: the note's own ui.label(...) call, located by its
    opening 'ui.label(' immediately followed by the word VOLUME,
    through its wizard-subtle-3 wizard-note .classes(...) call, is
    stripped from a copy of app.py's real source, standing in for the
    hint never having been added. Observed: the same bounded check
    test_volume_fields_carry_a_visible_hint uses - a
    wizard-subtle-3 wizard-note occurrence between the Volume ID input
    and the cache-path input - finds none in the mutated copy (the
    step's own later, unrelated cache-path note, also
    wizard-subtle-3 wizard-note, sits past the cache_input anchor and
    is excluded by construction)."""
    source = _APP_PY.read_text(encoding="utf-8")
    volume_index = source.index('ui.input("Volume ID"')
    hint_start = source.index("ui.label(", volume_index)
    while source[hint_start:hint_start + 60].count("VOLUME") == 0:
        hint_start = source.index("ui.label(", hint_start + 1)
    hint_end = source.index("wizard-subtle-3 wizard-note", hint_start) + len('wizard-subtle-3 wizard-note")')
    mutated = source[:hint_start] + source[hint_end:]
    assert mutated != source, "fixture assumption stale: hint block not found"
    assert "wizard-subtle-3 wizard-note" not in _volume_to_cache_span(mutated)

"""Guards for the Scan step's three tiles (Scanning.dc.html:96-107):
each pairs a value with a key naming what it counts - "Matched so
far", "Need your review", "No match found" - the same finding as the
review row's A/R/U initials, since a bare coloured number carries no
meaning past whoever wrote the code (Specs.dc.html, "Accessibility
rules": no row relies on a swatch).
"""

from __future__ import annotations

import re
from pathlib import Path

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"


def test_every_tile_carries_its_key_text():
    """Each of the three tile keys - "Matched so far", "Need your
    review", "No match found" - appears in app.py's source as a
    ui.label(...) call, not only as a comment citing the artboard."""
    source = _APP_PY.read_text(encoding="utf-8")
    for key_text in ("Matched so far", "Need your review", "No match found"):
        assert f'ui.label("{key_text}")' in source, f"tile key text {key_text!r} not found as a real label"


def test_a_removed_tile_key_is_caught():
    """Mutation: the real "Need your review" label call is stripped
    from a copy of app.py's real source, standing in for a tile losing
    its key text. Observed: the same membership check
    test_every_tile_carries_its_key_text uses reports it absent."""
    source = _APP_PY.read_text(encoding="utf-8")
    anchor = 'ui.label("Need your review").classes("wizard-body-11-5 wizard-dim")'
    assert anchor in source, "fixture assumption stale: tile key label not found"
    mutated = source.replace(anchor, "", 1)
    assert 'ui.label("Need your review")' not in mutated


def test_tile_value_and_key_each_carry_one_size_and_one_colour_class():
    """Each tile's value label (wizard-title, wizard-status-*) and key
    label (wizard-body-11-5, wizard-dim) carry exactly one font-size
    class and one colour class apiece - not two of either stacked on
    one element."""
    source = _APP_PY.read_text(encoding="utf-8")
    for value_anchor in (
        'scan_tile_found = ui.label("").classes("wizard-mono wizard-title wizard-status-found")',
        'scan_tile_review = ui.label("").classes("wizard-mono wizard-title wizard-status-review")',
        'scan_tile_missing = ui.label("").classes("wizard-mono wizard-title wizard-status-missing")',
    ):
        assert value_anchor in source
    for key_anchor in (
        'ui.label("Matched so far").classes("wizard-body-11-5 wizard-dim")',
        'ui.label("Need your review").classes("wizard-body-11-5 wizard-dim")',
        'ui.label("No match found").classes("wizard-body-11-5 wizard-dim")',
    ):
        assert key_anchor in source
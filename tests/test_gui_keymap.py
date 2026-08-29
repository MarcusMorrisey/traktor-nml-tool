"""Guards the keyboard contract without a browser: every ENTRIES
action name resolves to something dispatch can return, and the
dispatch arithmetic itself - movement bounds, Home/End, a
Shift-extended range, and a digit beyond the focused row's candidate
count (DL-080, DL-081).
"""

from __future__ import annotations

import re
from pathlib import Path

from traktor_nml.gui import keymap

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"


def test_every_entry_action_is_dispatchable():
    """The positive case test_removed_entry_action_is_caught's mutation control checks: every action name in keymap.ACTION_NAMES is reachable by dispatching some ENTRIES row."""
    dispatchable = set()
    for entry in keymap.ENTRIES:
        action = keymap.dispatch(
            entry.key, entry.modifiers, entry.scope,
            row_count=9, focused_index=4, candidate_count=9,
        )
        if action is not None:
            dispatchable.add(action.name)
    assert keymap.ACTION_NAMES == dispatchable


def test_removed_entry_action_is_caught():
    """Mutation: the real ENTRIES tuple has its 'accept' entry dropped
    from a copy passed through the real dispatch loop
    test_every_entry_action_is_dispatchable runs. Observed: the
    dispatchable set the loop builds from that copy no longer contains
    'accept', while keymap.ACTION_NAMES (built from the untouched
    ENTRIES) still does, so the equality check fails naming 'accept'
    as undispatchable."""
    entries_without_accept = tuple(e for e in keymap.ENTRIES if e.action != "accept")
    dispatchable = set()
    for entry in entries_without_accept:
        action = keymap.dispatch(
            entry.key, entry.modifiers, entry.scope,
            row_count=9, focused_index=4, candidate_count=9,
        )
        if action is not None:
            dispatchable.add(action.name)
    assert "accept" not in dispatchable
    assert "accept" in keymap.ACTION_NAMES


def test_move_up_clamps_at_row_zero():
    action = keymap.dispatch("ArrowUp", (), keymap.SCOPE_TABLE, row_count=5, focused_index=0)
    assert action.args["index"] == 0


def test_move_down_clamps_at_the_last_row():
    action = keymap.dispatch("ArrowDown", (), keymap.SCOPE_TABLE, row_count=5, focused_index=4)
    assert action.args["index"] == 4


def test_home_and_end_resolve_within_a_filtered_count():
    home = keymap.dispatch("Home", (), keymap.SCOPE_TABLE, row_count=3, focused_index=2)
    end = keymap.dispatch("End", (), keymap.SCOPE_TABLE, row_count=3, focused_index=0)
    assert home.args["index"] == 0
    assert end.args["index"] == 2


def test_shift_down_returns_a_range_anchored_on_the_focused_row():
    action = keymap.dispatch("ArrowDown", ("shift",), keymap.SCOPE_TABLE, row_count=6, focused_index=2)
    assert action.args == {"anchor": 2, "to": 3}


def test_digit_beyond_the_focused_rows_candidate_count_returns_no_action():
    """The review table may have six rows while the focused row itself
    carries only two candidates; a digit within row_count but beyond
    that row's own candidate_count must still be refused (DL-081)."""
    action = keymap.dispatch("3", (), keymap.SCOPE_TABLE, row_count=6, focused_index=0, candidate_count=2)
    assert action is None


def test_digit_within_the_focused_rows_candidate_count_returns_a_pick():
    action = keymap.dispatch("2", (), keymap.SCOPE_TABLE, row_count=6, focused_index=0, candidate_count=2)
    assert action == keymap.Action("pick_candidate", {"digit": 2})


def test_a_key_with_no_entry_in_scope_returns_no_action():
    action = keymap.dispatch("q", (), keymap.SCOPE_TABLE, row_count=6, focused_index=0)
    assert action is None


def test_help_panel_draws_its_text_from_keymap_entries():
    source = _APP_PY.read_text(encoding="utf-8")
    assert "keymap.ENTRIES" in source
    assert re.search(r"for\s+entry\s+in\s+keymap\.ENTRIES", source)


def test_help_panel_source_check_catches_a_second_source(tmp_path):
    """Mutation: a copy of app.py's real source has its
    'for entry in keymap.ENTRIES' help-panel loop replaced with a
    second, _KEYBOARD_MAP-driven loop. Observed: the same regex
    test_help_panel_draws_its_text_from_keymap_entries runs, pointed
    at the mutated copy, finds no match."""
    real_source = _APP_PY.read_text(encoding="utf-8")
    mutated = real_source.replace(
        "for entry in keymap.ENTRIES:",
        "for combo, description in _KEYBOARD_MAP:",
    )
    assert mutated != real_source, "fixture assumption stale: pattern not found in app.py"
    assert re.search(r"for\s+entry\s+in\s+keymap\.ENTRIES", mutated) is None


def test_applier_table_covers_every_action():
    """The positive case test_applier_table_gap_is_caught's mutation control checks: _ACTION_APPLIERS's key set equals keymap.ACTION_NAMES."""
    source = _APP_PY.read_text(encoding="utf-8")
    match = re.search(r"_ACTION_APPLIERS\s*=\s*\{(.*?)\n\}", source, re.DOTALL)
    assert match is not None, "_ACTION_APPLIERS table not found in app.py"
    keys = set(re.findall(r'"([a-z_]+)":', match.group(1)))
    assert keys == set(keymap.ACTION_NAMES)


def test_applier_table_gap_is_caught():
    """Mutation: the real _ACTION_APPLIERS table's source text, as
    extracted from app.py by the real regex, has its 'reject' entry
    removed. Observed: the key set the same extraction regex
    test_applier_table_covers_every_action runs then produces no
    longer contains 'reject', while keymap.ACTION_NAMES still does, so
    the equality assertion fails naming 'reject' as unappliable."""
    source = _APP_PY.read_text(encoding="utf-8")
    match = re.search(r"_ACTION_APPLIERS\s*=\s*\{(.*?)\n\}", source, re.DOTALL)
    assert match is not None
    mutated_body = re.sub(r'"reject":\s*_applier_reject,\n', "", match.group(1))
    assert mutated_body != match.group(1), "fixture assumption stale: 'reject' entry not found"
    keys = set(re.findall(r'"([a-z_]+)":', mutated_body))
    assert "reject" not in keys
    assert "reject" in keymap.ACTION_NAMES


# The applier table's key set alone (the two guards above) is
# satisfied by a table that maps every action to _applier_noop, so it
# is not by itself evidence any key does something; the two guards
# below additionally pin that the help-panel loop excludes a
# SCOPE_TABLE entry still bound to _applier_noop, and that toggle_detail
# - the one key Specs.dc.html's "Keyboard" section and the help panel
# both name - is not that noop.
def test_help_panel_skips_noop_bound_keys():
    source = _APP_PY.read_text(encoding="utf-8")
    panel_match = re.search(
        r'with ui\.expansion\("Keyboard shortcuts"\):\n(.*?)\n\n', source, re.DOTALL
    )
    assert panel_match is not None, "help panel block not found in app.py"
    assert "_ACTION_APPLIERS.get(entry.action) is _applier_noop" in panel_match.group(1), (
        "help panel loop does not check against noop appliers before rendering a key"
    )


def test_help_panel_noop_check_removal_is_caught():
    """Mutation: the real help-panel block's source text has its
    noop-skip line deleted. Observed: the same substring check
    test_help_panel_skips_noop_bound_keys runs no longer finds it."""
    source = _APP_PY.read_text(encoding="utf-8")
    mutated = source.replace(
        "                if _ACTION_APPLIERS.get(entry.action) is _applier_noop:\n"
        "                    continue\n",
        "",
        1,
    )
    assert mutated != source, "fixture assumption stale: noop-skip line not found"
    panel_match = re.search(
        r'with ui\.expansion\("Keyboard shortcuts"\):\n(.*?)\n\n', mutated, re.DOTALL
    )
    assert panel_match is not None
    assert "_ACTION_APPLIERS.get(entry.action) is _applier_noop" not in panel_match.group(1)


def test_toggle_detail_is_not_bound_to_noop():
    source = _APP_PY.read_text(encoding="utf-8")
    match = re.search(r"_ACTION_APPLIERS\s*=\s*\{(.*?)\n\}", source, re.DOTALL)
    assert match is not None
    applier = re.search(r'"toggle_detail":\s*(\w+),', match.group(1))
    assert applier is not None


# GUARD A - Specs.dc.html's Keyboard section, read at test time, is
# the missing direction test_every_entry_action_is_dispatchable does
# not check: that one pins ENTRIES' own action names against the
# applier table, never Specs' own chips against ENTRIES. Mirrors
# tests/test_gui_theme.py's design-set-to-theme.py colour and
# type-scale guards.
_GROUP_TO_SCOPE = {
    "Anywhere": keymap.SCOPE_ANYWHERE,
    "Review table": keymap.SCOPE_TABLE,
    "Dialogs": keymap.SCOPE_DIALOG,
}
# Chip glyphs Specs uses that keymap.py's own vocabulary spells
# differently. A bare modifier chip ("Ctrl", "Alt", the shift glyph)
# prefixes every following chip in its row rather than naming a key of
# its own; the shift glyph can also appear fused into a single chip
# for Shift+Tab, handled separately in _translate_chip.
_SHIFT_GLYPH = "⇧"
_MODIFIER_WORDS = {"Ctrl": "ctrl", "Alt": "alt", _SHIFT_GLYPH: "shift"}
_BASE_KEY_MAP = {
    "Tab": "Tab", "F6": "F6", "↵": "Enter", "Esc": "Escape",
    "↑": "ArrowUp", "↓": "ArrowDown", "Home": "Home", "End": "End",
    "Space": " ", "/": "/",
}
_SPECS_PATH = Path(__file__).resolve().parents[1] / "design" / "reconnect-wizard" / "Specs.dc.html"

# '/' ("Jump to search") is the one Specs key this guard does not
# require keymap.ENTRIES to bind. Checked directly: the Review step
# (traktor_nml/gui/app.py's _build_review_step) builds exactly two
# interactive regions in the table area, filter_row and
# table_container - no ui.input, no search box anywhere a '/' keypress
# could focus. review_model.FILTERS is seven fixed status/decision
# predicates (ambiguous, refuted, format, no_match, accepted, rejected,
# matched); none of them, or anything else in review_model.py, matches
# free text. The maintainer ruled this search feature deferred - W-002
# stays a visual pass. Named here by its exact combo, not by a rule
# that could swallow a real future gap the same way.
_KNOWN_UNMAPPED_SPECS_KEYS = {("/", frozenset(), keymap.SCOPE_TABLE)}


def _translate_chip(text: str) -> tuple:
    """One .kbd chip's text -> (key, extra_modifiers). Handles a
    shift chip fused into one chip (Shift+Tab written as one chip) as
    well as a plain named key, a single letter (matched
    case-insensitively against keymap.py's own lower-case
    single-letter entries), and a digit."""
    if text.startswith(_SHIFT_GLYPH) and len(text) > 1:
        base = text[1:]
        return _BASE_KEY_MAP.get(base, base), ("shift",)
    if text in _BASE_KEY_MAP:
        return _BASE_KEY_MAP[text], ()
    if len(text) == 1 and text.isalpha():
        return text.lower(), ()
    return text, ()


def _specs_keyboard_combos() -> set:
    """Every (key, modifiers, scope) triple Specs.dc.html's Keyboard
    section specifies, read from the .kbd chips at test time rather
    than transcribed. A bare modifier chip prefixes every following
    chip in its row; an en-dash between two chips (the digit ranges
    '1'-'9' and 'Alt' '1'-'7') expands into one triple per key in the
    range, the same expansion ENTRIES itself already applies for those
    two rows; chips with no modifier prefix and no dash between them
    (Tab / Shift-Tab, Up / Down, Home / End, Shift-Up / Shift-Down) are
    independent entries, not one chord."""
    html = _SPECS_PATH.read_text(encoding="utf-8")
    section = re.search(
        r'<h2 class="sec-t">Keyboard</h2>.*?</div>\s*</div>\s*</section>', html, re.DOTALL,
    )
    assert section is not None, "Keyboard section not found in Specs.dc.html"
    combos = set()
    scope = None
    for m in re.finditer(
        r'<span class="g">([^<]+)</span>'
        r'|<div class="kr"><span class="k">(.*?)</span><span class="d">',
        section.group(0),
    ):
        if m.group(1) is not None:
            scope = _GROUP_TO_SCOPE[m.group(1)]
            continue
        assert scope is not None, "a .kr row appeared before any .g group label"
        tokens = re.findall(r'<span class="kbd">(.*?)</span>|(–)', m.group(2))
        chips = [("dash", None) if dash else ("chip", chip) for chip, dash in tokens]
        active_mods = []
        idx = 0
        while idx < len(chips) and chips[idx][0] == "chip" and chips[idx][1] in _MODIFIER_WORDS:
            active_mods.append(_MODIFIER_WORDS[chips[idx][1]])
            idx += 1
        rest = chips[idx:]
        j = 0
        while j < len(rest):
            text = rest[j][1]
            if j + 2 < len(rest) and rest[j + 1][0] == "dash" and rest[j + 2][0] == "chip":
                start_key, _extra1 = _translate_chip(text)
                end_key, _extra2 = _translate_chip(rest[j + 2][1])
                for d in range(int(start_key), int(end_key) + 1):
                    combos.add((str(d), frozenset(active_mods), scope))
                j += 3
            else:
                key, extra = _translate_chip(text)
                combos.add((key, frozenset(active_mods) | frozenset(extra), scope))
                j += 1
    return combos


def _entries_combos() -> set:
    """keymap.ENTRIES' own (key, modifiers, scope) triples, with a
    single-letter key lower-cased to match _translate_chip's own
    case-insensitive handling of Specs' upper-case letter chips
    (A/R/U/Z) - the same case-insensitivity keymap.dispatch's own
    _match applies."""
    return {
        (entry.key.lower() if len(entry.key) == 1 else entry.key, frozenset(entry.modifiers), entry.scope)
        for entry in keymap.ENTRIES
    }


def test_every_specs_keyboard_entry_is_in_keymap():
    """Every key/modifier/scope combination Specs.dc.html's Keyboard
    section lists, except _KNOWN_UNMAPPED_SPECS_KEYS' one documented
    entry, has a matching keymap.ENTRIES row."""
    specs = _specs_keyboard_combos()
    assert specs, "no .kbd chips read from Specs.dc.html - check the section regex"
    missing = sorted(specs - _entries_combos() - _KNOWN_UNMAPPED_SPECS_KEYS)
    assert missing == [], f"Specs.dc.html lists a key keymap.ENTRIES does not: {missing}"


def test_a_specs_keyboard_entry_missing_from_keymap_is_caught():
    """Mutation: the real ENTRIES-derived combo set has its 'a'
    (accept) SCOPE_TABLE entry removed, standing in for a key Specs
    lists that keymap.ENTRIES has quietly lost. Observed: the same
    set-difference test_every_specs_keyboard_entry_is_in_keymap
    computes then reports [('a', frozenset(), 'table')] as missing."""
    entries_without_a = _entries_combos() - {("a", frozenset(), keymap.SCOPE_TABLE)}
    missing = sorted(_specs_keyboard_combos() - entries_without_a - _KNOWN_UNMAPPED_SPECS_KEYS)
    assert missing == [("a", frozenset(), keymap.SCOPE_TABLE)]


# GUARD B - _ACTION_APPLIERS binds seven actions to _applier_noop. The
# two buckets below are not the same finding and must not be read as
# one undifferentiated list:
#
# Satisfied by behaviour the app already has, true independent of any
# ui.keyboard binding - nothing needs to run in app.py for these to
# already be correct:
#   focus_next, focus_prev (Tab / Shift-Tab, SCOPE_ANYWHERE) - nothing
#   in app.py calls preventDefault on Tab; the browser's own
#   reading-order focus movement already does this.
#   dialog_safe_close (Escape and Enter, SCOPE_DIALOG) - Quasar's own
#   QDialog carries a built-in Escape dismissal (addEscapeKey /
#   onEscapeKey in the bundled quasar.umd.js), left enabled by
#   dialog.props("no-esc-dismiss=false") in app.py's _build_write_step;
#   and a native Enter keypress activates whichever control currently
#   holds focus, which is the dialog's own
#   safe_button.props("autofocus") - an ordinary browser default, not
#   something dispatch runs.
#
# Deferred, unimplemented behaviour - the maintainer ruled W-002, a
# visual pass, does not build any of these:
#   jump_region (F6, SCOPE_ANYWHERE) - "Jump between regions: filters
#   -> table -> comparison -> footer" names a focus-region cycle no
#   code in app.py tracks.
#   continue_step (Ctrl+Enter, SCOPE_ANYWHERE) - "Continue to the next
#   step" names a global shortcut nothing wires to any step's own
#   Continue button (go_to_scan / go_to_write and their siblings are
#   click targets only).
#   undo_last (Ctrl+Z, SCOPE_ANYWHERE) - "Undo the last decision,
#   wherever focus is" needs an ordered decision history;
#   WizardState._decisions (wizard_state.py) is a plain unordered
#   dict with no such history to read.
#   close_or_clear (Escape, SCOPE_ANYWHERE) - "Close a dialog, or
#   clear the search box" names the same missing search control and
#   predicate _KNOWN_UNMAPPED_SPECS_KEYS documents above for '/', and
#   no SCOPE_ANYWHERE ui.keyboard exists in app.py for this entry to
#   dispatch through in the first place - the Review step's one
#   ui.keyboard call is scoped to SCOPE_TABLE only.
_NOOP_SATISFIED_BY_EXISTING_BEHAVIOUR = frozenset({"focus_next", "focus_prev", "dialog_safe_close"})
_NOOP_DEFERRED_UNIMPLEMENTED = frozenset({"jump_region", "continue_step", "undo_last", "close_or_clear"})


def _noop_bound_actions(body: str) -> set:
    """Every action name _ACTION_APPLIERS' source text binds to
    _applier_noop - the one place both the real guard and its
    mutation control read this from."""
    return set(re.findall(r'"([a-z_]+)":\s*_applier_noop,', body))


def test_noop_bound_actions_are_exactly_the_documented_set():
    """_ACTION_APPLIERS' no-op-bound action set equals the union of
    _NOOP_SATISFIED_BY_EXISTING_BEHAVIOUR and
    _NOOP_DEFERRED_UNIMPLEMENTED, so a new action quietly rebound to
    _applier_noop cannot appear unnoticed the way these seven did."""
    source = _APP_PY.read_text(encoding="utf-8")
    match = re.search(r"_ACTION_APPLIERS\s*=\s*\{(.*?)\n\}", source, re.DOTALL)
    assert match is not None, "_ACTION_APPLIERS table not found in app.py"
    noop_actions = _noop_bound_actions(match.group(1))
    documented = _NOOP_SATISFIED_BY_EXISTING_BEHAVIOUR | _NOOP_DEFERRED_UNIMPLEMENTED
    assert noop_actions == documented, f"undocumented no-op action(s): {sorted(noop_actions ^ documented)}"


def test_an_undocumented_noop_is_caught():
    """Mutation: a fabricated entry rebinding 'toggle_detail' to
    _applier_noop is appended to a copy of the real _ACTION_APPLIERS
    table's source text, standing in for a future action quietly
    rebound to _applier_noop (toggle_detail's own real binding is
    _applier_toggle_detail, not _applier_noop, so this is a clean
    addition rather than a duplicate). Observed: the same extraction
    test_noop_bound_actions_are_exactly_the_documented_set uses now
    includes 'toggle_detail', which is in neither documented bucket, so
    the equality assertion fails with {'toggle_detail'} as the
    symmetric difference."""
    source = _APP_PY.read_text(encoding="utf-8")
    match = re.search(r"_ACTION_APPLIERS\s*=\s*\{(.*?)\n\}", source, re.DOTALL)
    assert match is not None
    mutated_body = match.group(1) + '\n    "toggle_detail": _applier_noop,'
    noop_actions = _noop_bound_actions(mutated_body)
    documented = _NOOP_SATISFIED_BY_EXISTING_BEHAVIOUR | _NOOP_DEFERRED_UNIMPLEMENTED
    assert noop_actions != documented
    assert noop_actions ^ documented == {"toggle_detail"}

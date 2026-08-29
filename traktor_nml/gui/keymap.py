"""The single source for the reconnect wizard's keyboard contract: one
entry per key Specs.dc.html's "Keyboard" section names, feeding both
the rendered help panel and the live ui.keyboard bindings (DL-080).
Imports no nicegui.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

SCOPE_ANYWHERE = "anywhere"
SCOPE_TABLE = "table"
SCOPE_DIALOG = "dialog"


@dataclass(frozen=True)
class Entry:
    """One row of the keyboard contract: the key/modifier combination, the scope it applies in, the action name dispatch returns for it, and the description the help panel renders for the review-table entries it draws from."""
    key: str
    modifiers: Tuple[str, ...]
    scope: str
    action: str
    description: str


# Specs.dc.html, "Keyboard": one row per key/scope pair. Digits 1-9
# and Alt 1-7 each expand to one entry per digit so dispatch can match
# a single pressed key rather than parsing a range at dispatch time.
ENTRIES: Tuple[Entry, ...] = (
    Entry("Tab", (), SCOPE_ANYWHERE, "focus_next", "Move through controls in reading order"),
    Entry("Tab", ("shift",), SCOPE_ANYWHERE, "focus_prev", "Move through controls in reading order"),
    Entry("F6", (), SCOPE_ANYWHERE, "jump_region", "Jump between regions: filters -> table -> comparison -> footer"),
    Entry("Enter", ("ctrl",), SCOPE_ANYWHERE, "continue_step", "Continue to the next step"),
    Entry("z", ("ctrl",), SCOPE_ANYWHERE, "undo_last", "Undo the last decision, wherever focus is"),
    Entry("Escape", (), SCOPE_ANYWHERE, "close_or_clear", "Close a dialog, or clear the search box"),
    Entry("ArrowUp", (), SCOPE_TABLE, "move_up", "Move between tracks"),
    Entry("ArrowDown", (), SCOPE_TABLE, "move_down", "Move between tracks"),
    Entry("Home", (), SCOPE_TABLE, "move_home", "First track in the current filter"),
    Entry("End", (), SCOPE_TABLE, "move_end", "Last track in the current filter"),
    Entry(" ", (), SCOPE_TABLE, "toggle_detail", "Show or hide the detail panel beside the table"),
    Entry("a", (), SCOPE_TABLE, "accept", "Accept the highlighted file"),
    Entry("r", (), SCOPE_TABLE, "reject", "Reject - leave this track missing"),
    Entry("u", (), SCOPE_TABLE, "undo_row", "Undo the decision on this track"),
    Entry("Enter", (), SCOPE_TABLE, "accept_and_advance", "Accept, then jump to the next undecided track"),
    *(Entry(str(d), (), SCOPE_TABLE, "pick_candidate", "Pick that candidate file. Picking is not accepting.") for d in range(1, 10)),
    Entry("ArrowUp", ("shift",), SCOPE_TABLE, "extend_up", "Extend the selection for a bulk decision"),
    Entry("ArrowDown", ("shift",), SCOPE_TABLE, "extend_down", "Extend the selection for a bulk decision"),
    *(Entry(str(d), ("alt",), SCOPE_TABLE, "switch_filter", "Switch filter") for d in range(1, 8)),
    Entry("Escape", (), SCOPE_DIALOG, "dialog_safe_close", "Always the safe choice - keep scanning, cancel the write"),
    Entry("Enter", (), SCOPE_DIALOG, "dialog_safe_close", "Never writes. Focus opens on the safe button; writing needs a deliberate move to it"),
)

# The set of action names ENTRIES can produce - the set app.py's
# _ACTION_APPLIERS table must equal, per the guard in
# tests/test_gui_keymap.py (DL-080).
ACTION_NAMES: frozenset = frozenset(entry.action for entry in ENTRIES)


@dataclass(frozen=True)
class Action:
    """An action dispatch resolves a keypress to: the action name from ACTION_NAMES, and the arguments the applier in app.py's _ACTION_APPLIERS table needs."""
    name: str
    args: dict


def _match(key: str, modifiers: Tuple[str, ...], scope: str):
    """The ENTRIES row whose key, modifiers and scope all match, or None."""
    wanted = frozenset(modifiers)
    for entry in ENTRIES:
        if entry.scope == scope and entry.key.lower() == key.lower() and frozenset(entry.modifiers) == wanted:
            return entry
    return None


def dispatch(
    key: str,
    modifiers: Tuple[str, ...],
    scope: str,
    row_count: int,
    focused_index: int,
    candidate_count: Optional[int] = None,
):
    """The Action `key` (with `modifiers`) resolves to in `scope`, given
    the review table's current `row_count` and `focused_index`; None
    when no ENTRIES row matches in that scope (DL-081).

    Movement clamps at both ends rather than wrapping or raising; Home
    and End resolve within row_count, which is the filtered count
    rather than the whole review set, so they land inside whatever
    filter is active; Shift-Up/Down return a range anchored on
    focused_index rather than moving it; a digit key returns
    pick_candidate only when the digit is within the focused row's own
    `candidate_count` - not row_count, which counts rows rather than
    candidates on one row - since picking a candidate is not accepting
    (Specs.dc.html, "Accept and reject"). Callers that omit
    candidate_count (movement-only dispatch) get no digit bound at all;
    the caller that dispatches digits must pass it.
    """
    entry = _match(key, modifiers, scope)
    if entry is None:
        return None
    if entry.action == "move_up":
        return Action("move_up", {"index": max(0, focused_index - 1)})
    if entry.action == "move_down":
        return Action("move_down", {"index": min(max(row_count - 1, 0), focused_index + 1)})
    if entry.action == "move_home":
        return Action("move_home", {"index": 0 if row_count else focused_index})
    if entry.action == "move_end":
        return Action("move_end", {"index": max(row_count - 1, 0)})
    if entry.action == "extend_up":
        return Action("extend_up", {"anchor": focused_index, "to": max(0, focused_index - 1)})
    if entry.action == "extend_down":
        return Action("extend_down", {"anchor": focused_index, "to": min(max(row_count - 1, 0), focused_index + 1)})
    if entry.action == "pick_candidate":
        digit = int(key)
        bound = candidate_count if candidate_count is not None else 0
        if digit > bound:
            return None
        return Action("pick_candidate", {"digit": digit})
    if entry.action == "switch_filter":
        return Action("switch_filter", {"digit": int(key)})
    return Action(entry.action, {})

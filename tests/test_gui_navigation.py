"""Guards for traktor_nml/gui/navigation.py's section table and the
selection rule over it. Each guard constructs its broken scenario in
executable code and records the mutation and the observed output,
matching the register tests/test_scan_diagnostics.py,
tests/test_review_channel.py and tests/test_gui_review_model.py already
use.

The mechanism every guard here reads with is a pure call to
header_tabs on the system interpreter, which has no nicegui installed.
That establishes which route the selection rule marks, in the order the
table declares, and with which class string and aria-current value. It
cannot establish that app.py renders those records, that nicegui emits
an anchor for one, or that the class survives into a browser's DOM -
those are the second and third mechanisms of DL-133, and they live
elsewhere.

Selection is read back by EQUALITY against the exact list of routes
expected, never by membership and never by any(): a membership check
passes while the wrong tab is marked, while both are, and while none is.
The three negative-control guards below run those three mutations.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Callable

from traktor_nml.gui import navigation
from traktor_nml.gui.navigation import (
    ARIA_CURRENT_SELECTED,
    SECTIONS,
    TAB_CLASS,
    TAB_SELECTED_CLASS,
    header_tabs,
)

NAVIGATION_PATH = Path(navigation.__file__)

_FRAMEWORK_ROOTS = frozenset({"nicegui", "webview"})


def _selected_routes(tabs) -> list[str]:
    """The routes of exactly those records reading selected, in the
    order the records arrive."""
    return [tab.route for tab in tabs if tab.selected]


def _tabs_under(rule: Callable[[str, str], bool], active_route: str):
    """header_tabs with its selection rule replaced by rule(route,
    active_route), so a negative control can run a mutated rule over the
    real SECTIONS table without editing the module."""
    return tuple(
        navigation._tab(route, label, rule(route, active_route))
        for route, label in SECTIONS
    )


def test_root_selects_exactly_the_root_route() -> None:
    """header_tabs('/') marks exactly one record and it is the '/' row.

    Made to fail three ways, each mutation applied to
    header_tabs in navigation.py and run:

    - the comparison changed to `route != active_route` (mark the other
      row): AssertionError: assert ['/reconnect'] == ['/'], At index 0
      diff: '/reconnect' != '/'
    - the comparison changed to the constant True (mark both rows):
      AssertionError: assert ['/', '/reconnect'] == ['/'], Left contains
      one more item: '/reconnect'
    - the comparison changed to the constant False (mark no row):
      AssertionError: assert [] == ['/'], Right contains one more item:
      '/'

    Equality against the whole list is what catches all three; a
    membership check on the selected routes passes under every one of
    them.
    """
    assert _selected_routes(header_tabs("/")) == ["/"]


def test_reconnect_selects_exactly_the_reconnect_route() -> None:
    """header_tabs('/reconnect') marks exactly one record and it is the
    '/reconnect' row.

    Made to fail by the same three mutations to
    header_tabs, run against this route:

    - `route != active_route`: AssertionError: assert ['/'] ==
      ['/reconnect'], At index 0 diff: '/' != '/reconnect'
    - the constant True: AssertionError: assert ['/', '/reconnect'] ==
      ['/reconnect'], Left contains one more item: '/reconnect'
    - the constant False: AssertionError: assert [] == ['/reconnect'],
      Right contains one more item: '/reconnect'
    """
    assert _selected_routes(header_tabs("/reconnect")) == ["/reconnect"]


def test_marking_the_other_row_is_caught() -> None:
    """Negative control: the selection rule inverted to mark every row
    whose route differs from the active route.

    The rule under test is not the module's own: it is
    substituted here, so what this guard establishes is that reading
    selection by equality reports the wrong row rather than passing.

    Made to fail by mutating _tab in navigation.py to build every record
    with selected=False, ignoring the flag its caller passes:
    AssertionError: assert [] == ['/reconnect'], Right contains one more
    item: '/reconnect'.
    """
    selected = _selected_routes(_tabs_under(lambda route, active: route != active, "/"))
    assert selected != ["/"]
    assert selected == ["/reconnect"]


def test_marking_both_rows_is_caught() -> None:
    """Negative control: the selection rule replaced by one that marks
    every row.

    The rule under test is substituted here rather than
    the module's own, so what this guard establishes is that equality
    reports two selected rows rather than passing.

    Made to fail by mutating _tab in navigation.py to build every record
    with selected=False: AssertionError: assert [] == ['/',
    '/reconnect'], Right contains 2 more items, first extra item: '/'.

    Made to fail a second way by reversing the two rows of SECTIONS:
    AssertionError: assert ['/reconnect', '/'] == ['/', '/reconnect'],
    At index 0 diff: '/reconnect' != '/'.
    """
    selected = _selected_routes(_tabs_under(lambda route, active: True, "/"))
    assert selected != ["/"]
    assert selected == ["/", "/reconnect"]


def test_marking_no_row_is_caught() -> None:
    """Negative control: the selection rule replaced by one that marks
    no row.

    The rule under test is substituted here rather than
    the module's own, so what this guard establishes is that equality
    reports an empty selection rather than passing.

    Made to fail by mutating _tab in navigation.py to build every record
    with selected=True, ignoring the flag its caller passes:
    AssertionError: assert ['/', '/reconnect'] == [].
    """
    selected = _selected_routes(_tabs_under(lambda route, active: False, "/"))
    assert selected != ["/"]
    assert selected == []


def test_routes_read_in_table_order_for_either_active_route() -> None:
    """The records arrive in the order SECTIONS declares - '/' first,
    '/reconnect' second - whichever route is active.

    Made to fail by reversing the two rows of SECTIONS in
    navigation.py: AssertionError: assert ['/reconnect', '/'] == ['/',
    '/reconnect'], At index 0 diff: '/reconnect' != '/'.
    """
    assert [tab.route for tab in header_tabs("/")] == ["/", "/reconnect"]
    assert [tab.route for tab in header_tabs("/reconnect")] == ["/", "/reconnect"]


def test_selected_and_unselected_records_carry_their_markers() -> None:
    """The selected record's class string holds both wizard-tab and
    wizard-tab-selected at aria-current 'page'; the unselected record
    holds wizard-tab alone at aria-current None.

    Made to fail two ways, each mutation applied to
    navigation.py and run:

    - the selected branch of the class string reduced to
      TAB_SELECTED_CLASS alone: AssertionError: assert
      ['wizard-tab-selected'] == ['wizard-tab', 'wizard-tab-selected'],
      At index 0 diff: 'wizard-tab-selected' != 'wizard-tab'
    - the aria_current field set to ARIA_CURRENT_SELECTED
      unconditionally: AssertionError: assert 'page' is None, where
      'page' = HeaderTab(route='/reconnect', label='Reconnect wizard',
      selected=False, classes='wizard-tab', aria_current='page')
      .aria_current
    """
    root, reconnect = header_tabs("/")

    assert root.selected is True
    assert root.classes.split() == [TAB_CLASS, TAB_SELECTED_CLASS]
    assert root.aria_current == ARIA_CURRENT_SELECTED == "page"
    assert root.label == "Reconstruct playlists"

    assert reconnect.selected is False
    assert reconnect.classes.split() == [TAB_CLASS]
    assert reconnect.aria_current is None
    assert reconnect.label == "Reconnect wizard"


def test_route_matching_no_row_selects_nothing() -> None:
    """An active route the table does not hold leaves every record
    unselected rather than falling back to the first row.

    Made to fail two ways, each mutation applied to
    navigation.py and run:

    - the comparison in header_tabs changed to `route != active_route`,
      which marks both rows when the active route matches neither:
      AssertionError: assert ['/', '/reconnect'] == []
    - the aria_current field set to ARIA_CURRENT_SELECTED
      unconditionally: AssertionError: assert ['page', 'page'] == [None,
      None], At index 0 diff: 'page' != None
    """
    tabs = header_tabs("/nowhere")

    assert _selected_routes(tabs) == []
    assert [tab.aria_current for tab in tabs] == [None, None]
    assert [tab.classes for tab in tabs] == [TAB_CLASS, TAB_CLASS]


def _imported_roots(source: str) -> set[str]:
    """The top-level package names one module's imports reach, by AST
    walk - the same reading tests/test_gui_view_boundary.py performs
    over the whole gui/ package."""
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return roots


def test_navigation_imports_neither_nicegui_nor_webview() -> None:
    """navigation.py sits below the view boundary (DL-069): its imports
    reach neither nicegui nor webview.

    Made to fail by adding an unused helper to
    navigation.py whose body reads `import nicegui` - deferred inside a
    function, so importing the module still succeeds and only the AST
    walk sees it: AssertionError: assert {'nicegui'} == set(), Extra
    items in the left set: 'nicegui'.
    """
    roots = _imported_roots(NAVIGATION_PATH.read_text(encoding="utf-8"))

    assert roots & _FRAMEWORK_ROOTS == set()


def test_navigation_is_lf_at_zero_crlf() -> None:
    """navigation.py is LF throughout, like the other framework-free
    gui/ modules.

    Made to fail by rewriting navigation.py with CRLF
    endings throughout: AssertionError: assert 77 == 0, where 77 is the
    CRLF count the file then reports.
    """
    data = NAVIGATION_PATH.read_bytes()

    assert data.count(bytes([13, 10])) == 0
    assert data.count(bytes([10])) > 0

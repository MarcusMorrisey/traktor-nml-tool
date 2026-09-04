"""The header's section table and the tab records it renders, with no
framework import.

SECTIONS is the one place either route or either label is written: the
reconstruct page answers '/' and stands leftmost, the reconnect wizard
answers '/reconnect' and stands second. header_tabs(active_route)
derives one record per row in that same order, carrying the row's route
and label plus the three things a tab renders with - whether it is the
selected row, the class string it carries, and its aria-current value.

Two axes are kept apart here: the table is what the header holds, the
active route is what the browser is showing. Selection is the single
point where they meet - the row whose route equals active_route is the
selected one, exactly one row at a time, and an active_route matching no
row selects nothing rather than falling back to the first. Deriving the
class string and the aria-current value from that one comparison keeps
the marker a guard reads back (DL-133) and the colour an operator sees
from ever disagreeing. The rule is a pure computation over strings, so a
guard runs it on an interpreter with no framework present.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# The ordered section table: route first, label second. Every other
# module names a route or a label by reading this table.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("/", "Reconstruct playlists"),
    ("/reconnect", "Reconnect wizard"),
)

# The class every tab carries, and the second class the selected one
# carries alongside it.
TAB_CLASS = "wizard-tab"
TAB_SELECTED_CLASS = "wizard-tab-selected"

# The aria-current value the selected tab reads, and the value the rest
# read: None, which is the absence of the attribute rather than an empty
# string.
ARIA_CURRENT_SELECTED = "page"


@dataclass(frozen=True)
class HeaderTab:
    """One rendered tab: the row's route and label, whether it is the
    selected row, the class string it renders with, and its aria-current
    value or None."""

    route: str
    label: str
    selected: bool
    classes: str
    aria_current: Optional[str]


def header_tabs(active_route: str) -> tuple[HeaderTab, ...]:
    """One record per SECTIONS row in table order. The record whose
    route equals active_route is the selected one and carries both
    TAB_CLASS and TAB_SELECTED_CLASS at aria-current
    ARIA_CURRENT_SELECTED; every other record carries TAB_CLASS alone at
    aria-current None. An active_route equal to no row's route leaves
    every record unselected.
    """
    return tuple(_tab(route, label, route == active_route) for route, label in SECTIONS)


def _tab(route: str, label: str, selected: bool) -> HeaderTab:
    classes = f"{TAB_CLASS} {TAB_SELECTED_CLASS}" if selected else TAB_CLASS
    return HeaderTab(
        route=route,
        label=label,
        selected=selected,
        classes=classes,
        aria_current=ARIA_CURRENT_SELECTED if selected else None,
    )

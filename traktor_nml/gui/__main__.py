"""Entry point that starts the reconnect wizard: `python -m traktor_nml.gui`.

Lives here rather than as a traktor_nml/commands/ subcommand because
commands/__init__.py imports every command module at CLI startup, before
argv is parsed - a nicegui import reachable from there would break the
whole CLI on a machine without the gui extra installed
(docs/nicegui-gui-analysis.md #5).
"""

from __future__ import annotations

from nicegui import ui

from .app import build_wizard

build_wizard()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="traktor-nml-tool - reconnect wizard", native=True, reload=False)

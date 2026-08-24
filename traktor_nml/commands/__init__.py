"""Subcommand discovery.

Each module in this package owns its own parser registration: it exposes a
register(subparsers, handlers) function that adds its argparse subparser(s)
and records its handler(s) in the shared handlers dict keyed by command name.
cli.build_parser enumerates this package at import time (DL-003), so adding a
subcommand is a pure file-add - no hand-maintained registry to edit.
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def iter_command_modules() -> list[ModuleType]:
    """Import and return every non-underscore-prefixed module in this
    package, sorted by name so subcommand registration order is
    deterministic across runs regardless of filesystem directory order."""
    modules = []
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        if info.name.startswith("_"):
            continue
        modules.append(importlib.import_module(f"{__name__}.{info.name}"))
    return modules

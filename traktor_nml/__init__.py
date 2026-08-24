"""traktor_nml: inspect, rewrite, reconnect, splice and split Traktor NML files.

This package is the extraction target for traktor_nml_tool.py, which becomes a
thin argv-forwarding shim over traktor_nml.cli.main. See traktor_nml.cli for the
module docstring describing the two write strategies (attribute patching vs.
byte-span assembly) that every command in this package builds on.
"""

from __future__ import annotations

# Only cli is part of the public import surface; traktor_nml.commands.*
# modules are discovered internally (DL-003), never imported by name
# from outside this package.
__all__ = ["cli"]

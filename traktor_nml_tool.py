#!/usr/bin/env python3
"""Inspect and rewrite Traktor NML paths.

This is a thin argv-forwarding shim over the traktor_nml package (DL-001):
every subcommand, the write-strategy split (attribute patching vs.
byte-span assembly) and the subcommand-discovery mechanism live in
traktor_nml/, not here - see traktor_nml.cli's own module docstring.
This file exists so the historical invocation (`python traktor_nml_tool.py
...`) and the tool's drop-in-a-folder portability keep working unchanged.
"""

from __future__ import annotations

import sys

from traktor_nml.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

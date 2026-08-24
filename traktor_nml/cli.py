#!/usr/bin/env python3
"""Inspect and rewrite Traktor NML paths.

This tool is built around the path patterns observed in the local Traktor corpus:

- Main collection entries store paths in LOCATION/VOLUME, LOCATION/VOLUMEID, LOCATION/DIR, LOCATION/FILE
- Playlist and some history entries store flattened references in PRIMARYKEY/KEY
- PRIMARYKEY/KEY is derived as VOLUME + DIR + FILE

Write strategy - two mechanisms exist and stay separate:

  Attribute patching (reconnect, rewrite, rewrite-from-collection-compare):
    substitutes attribute values inside opening tags located in the raw
    source text; every other byte of the source file is preserved exactly.
    See textpatch.py for the full lxml-vs-stdlib fidelity rationale.

  Byte-span assembly (splice, split):
    copies source byte ranges verbatim to build a new document, re-serialising
    only the specific fragments a rename or redirect actually changes.
    See spans.py.

Subcommands are discovered from traktor_nml.commands at import time (DL-003):
each command module registers its own argparse subparser(s) and handler(s),
so cli.py never needs editing to add a subcommand.
"""

from __future__ import annotations

import argparse
import sys

from .commands import iter_command_modules


def build_parser() -> tuple[argparse.ArgumentParser, dict]:
    """Build the top-level parser by asking every discovered command
    module to register its own subparser and handler, so this function
    never lists a subcommand by name (DL-003)."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    handlers: dict = {}
    for module in iter_command_modules():
        module.register(subparsers, handlers)
    return parser, handlers


def main(argv: list[str]) -> int:
    parser, handlers = build_parser()
    args = parser.parse_args(argv)
    handler = handlers.get(args.command)
    if handler is None:
        print(f"unknown_command={args.command}", file=sys.stderr)
        return 2
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

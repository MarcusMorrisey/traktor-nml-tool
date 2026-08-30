# traktor_nml

Inspect, rewrite, reconnect, splice and split Traktor NML collection files.

## Overview

traktor_nml_tool.py is a thin argv-forwarding shim over this package
(DL-001). Scanning, caching, fingerprinting, span assembly and merge are
separate modules so no single file carries all of them and independent
features do not contend for one file.

## Architecture

Two write mechanisms coexist and never mix within one command:

- Attribute patching (`textpatch.py`, used by `rewrite.py`/`reconnect.py`):
  substitutes attribute values inside opening tags located in the raw
  source text. Every other byte of the source is preserved exactly.
- Byte-span assembly (`spans.py`, used by `splice.py`/`split.py`):
  concatenates verbatim source byte ranges, re-serialising only the
  specific fragments a rename or PRIMARYKEY redirect actually changes
  (DL-007) - `textpatch.py` has no concept of element extent, so
  structural insert/remove could not go through it without falling back
  to a full, format-losing serialisation.

`commands/` holds one module per subcommand; `cli.py` discovers them by
iterating the package rather than listing them, so adding a subcommand
never requires editing `cli.py` (DL-003).

## Design Decisions

- `matching.py`'s cascade accepts injected key providers; `fingerprint.py`
  supplies one behind an availability guard, so the core matching path
  never becomes import-guard-laden for a native chromaprint dependency
  most environments lack (DL-006).
- `--match-confidence` is one ordered enum (strict/loose/filename) rather
  than a second boolean flag, because disk-scan matching's filename-only
  tier and tag-based matching's artist-title-only tier are really one
  cascade, not two independent knobs (DL-010).

## Invariants

- Every write command builds its complete output in memory and validates
  it before any file handle opens; a failure partway through conflict
  resolution or reference redirection leaves every output path untouched
  (DL-012).
- `reconnect.py`'s one-to-one assignment guarantee (DL-004) and
  `volumes.py`'s explicit-VOLUME/VOLUMEID requirement (DL-005) are both
  enforced as post-passes over the shared matching cascade, which itself
  stays unaware either invariant is being layered on top of it.
- The NML schema (COLLECTION/PLAYLISTS/SUBNODES/PRIMARYKEY shapes and
  their count attributes) is confirmed only against NML VERSION=20 /
  Traktor Pro 4; `spans.py`'s count-attribute recalculation is generic
  over any counted container rather than a fixed tag list, so a counted
  container introduced by a later schema version is still recalculated
  correctly instead of being silently left stale.

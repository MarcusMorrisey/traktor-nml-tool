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
- The one-to-one destination-collision post-pass is a named function in
  `reconnect.py` (`enforce_one_to_one`) that both `resolve_reconnection`
  and compare-based rewriting call, so the pre-existing DL-004 guarantee
  has one implementation rather than one per caller (DL-015).
- `write_nml_safely`'s output-equals-input refusal is stated over every
  file the invocation reads, not only its primary input: a command with
  more than one input declares the rest through `extra_inputs`.
  `rewrite-from-collection-compare` reads two collections and declares
  `new_input`, so an output resolving to the newer collection is refused
  the same way one resolving to `old_input` already was (DL-023).
- `volumes.py` owns both directions of the volume-relative to absolute
  transformation: `location_from_disk_path` for the candidate side and
  `local_path_for_location` for the old side (DL-017).
- `local_path_for_location` resolves only against mount anchors this run
  established explicitly - `--volume-map` entries and scan roots whose
  identity `resolve_volume_identity` resolved - and returns nothing for an
  unknown VOLUME/VOLUMEID pair or for two known anchors that both yield a
  readable file. It never parses an anchor out of the VOLUME string and
  never falls back to the filesystem root: a guessed anchor can resolve to
  a different file sitting at the same volume-relative path, whose
  fingerprint could then win a match and rewrite LOCATION and PRIMARYKEY
  onto an unrelated track. This extends the pre-existing DL-005
  explicit-identity rule to the old side rather than carving an exception
  out of it (DL-018).

## Invariants

- Every write command builds its complete output in memory and validates
  it before any file handle opens; a failure partway through conflict
  resolution or reference redirection leaves every output path untouched
  (DL-012).
- `reconnect.py`'s one-to-one assignment guarantee (DL-004) and
  `volumes.py`'s explicit-VOLUME/VOLUMEID requirement (DL-005) are both
  enforced as post-passes over the shared matching cascade, which itself
  stays unaware either invariant is being layered on top of it; the
  guarantee is enforced by one shared post-pass (`reconnect.enforce_one_to_one`)
  that compare-based rewriting also calls, and a withdrawn match is
  reported as `destination_collisions` on both paths (DL-015, DL-016).
- A write command refuses an output path resolving to any of its inputs,
  not only its primary one, so a multi-input command declares its
  remaining inputs through `write_nml_safely`'s `extra_inputs` -
  `rewrite-from-collection-compare` declaring `new_input` is the case
  that motivated stating this generally (DL-023).
- `volumes.py` owns both directions of the volume-relative-to-absolute
  transformation; its old-side inverse (`local_path_for_location`)
  resolves only against mount anchors the run established explicitly,
  returning nothing for an unknown VOLUME/VOLUMEID pair or when two
  anchors for one pair both resolve, because a guessed anchor can
  fingerprint a different file and rewrite a track onto an unrelated
  location - an extension of the DL-005 explicit-identity invariant
  above, not an exception to it (DL-017, DL-018).
- The NML schema (COLLECTION/PLAYLISTS/SUBNODES/PRIMARYKEY shapes and
  their count attributes) is confirmed only against NML VERSION=20 /
  Traktor Pro 4; `spans.py`'s count-attribute recalculation is generic
  over any counted container rather than a fixed tag list, so a counted
  container introduced by a later schema version is still recalculated
  correctly instead of being silently left stale.

## Tradeoffs

- Reporting `destination_collisions` on the compare path costs one
  regenerated baseline manifest case; accepted so a withdrawn match stays
  distinguishable from a genuinely unmatched track (DL-016).
- Old-side volume resolution is confined to explicitly established mount
  anchors, so a record on an unmapped volume is simply not fingerprinted
  and counts as `fingerprint_unavailable_old_side`; accepted because the
  alternative failure mode is fingerprinting the wrong file (DL-018).
- `SpanIndex` holds per-tag offset lists for the whole document in memory;
  accepted because the alternative is a document rescan per element on an
  11.7MB, 6412-entry corpus (DL-014).
- `split`'s multi-output write loop is not transactional across files: each
  destination is individually atomic, but a failure partway through the
  loop leaves earlier group outputs written. Accepted because cross-file
  staging and commit is new machinery beyond a fix-only pass, and recorded
  here rather than left implied by the per-file atomicity claim (DL-022).

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
  (DL-007) - `apply_text_patches` has no concept of element extent, so
  structural insert/remove could not go through it without falling back
  to a full, format-losing serialisation. Where `textpatch.py` does need
  an extent - `patch_entry_attributes` writing a missing child after an
  anchor child - it calls `spans.find_element_span` rather than scanning
  for a close tag itself.

`commands/` holds one module per subcommand; `cli.py` discovers them by
iterating the package rather than listing them, so adding a subcommand
never requires editing `cli.py` (DL-003).

`reconnect_run.py` (the printless reconnection core) and
`reconnect_render.py` (the buffered stdout/stderr renderer for it) sit
beside the other top-level modules, not inside `commands/`:
`commands/reconnect_cmd.py` imports downward into them rather than the
reverse, so a caller other than the CLI - a GUI review table - can reach
the same core and renderer without going through argparse wiring
(DL-052). `shared_args.py` holds `resolve_confidence`/`should_refute`/
`refutation_disabled_line` below `commands/`, on the same side of that
boundary as the reconnect core and renderer, since a core module
importing from `commands/` would create the reverse of the import
direction DL-052 establishes; `commands/_shared_args.py` re-exports the
same three names so `compare_cmd.py` and `reconnect_cmd.py` keep one
import site each.

`build-playlist` synthesizes its playlist node from an external track list
with no source span to transplant, so it always takes the serialization
path this split already sanctions for genuinely new content (DL-028), and
it resolves track identity at a fixed `MatchConfidence.LOOSE` with no
level selector (DL-032, DL-276).

Every `build-playlist` input meets the core at one seam: an ordered list
of `tracklist.Candidate` values, each carrying its position and text for
the report and either the `EntryRecord` the cascade reads as its old side
or `None` for an entry that could not be parsed (DL-274).
`traktor_nml/playlistinput.py` reads a path into that list and names the
format and codec it read (DL-281); `buildplaylist.assemble_output` and
`tracklist.resolve_candidates` never see the input's syntax.

`build-playlist BASE INPUT OUTPUT --name NAME` reads INPUT as a plain-text
`Artist - Title` list, a `.csv` with `Artist` and `Title` columns (and
optional `Album`, `Duration`, `File name`), an `.m3u`/`.m3u8` playlist, or
a folder whose own audio files form the playlist in name order;
`--input-format` overrides detection from the suffix (DL-294).

`traktor_nml.gui` is a fourth package alongside `traktor_nml`,
`traktor_nml.commands` and `traktor_nml.gui`'s own three framework
modules; `[tool.setuptools] packages` in `pyproject.toml` lists it
explicitly (`packages = ["traktor_nml", "traktor_nml.commands",
"traktor_nml.gui"]`), since that array is not automatic discovery and a
package absent from it imports fine from a source checkout while missing
from an installed wheel (DL-070). Within the package, `review_model.py`,
`wizard_state.py`, `conflict_model.py` and `navigation.py` import no
`nicegui` or `pywebview` and are reachable from the test suite's system
interpreter; `app.py`, `file_picker.py` and
`__main__.py` are the only modules that do import them, so the suite -
which runs where `nicegui` is not installed - never crosses into the
three (DL-069).

## Design Decisions

A `DL-nnn` tag marks the decision a statement traces to; the statement lives in
whichever section actually describes it - Overview, Architecture, Invariants
or Tradeoffs - and lands here only when no other section fits. Each decision
is stated once, so a citation resolves against that single statement wherever
it sits, never against a bullet in this section specifically; a second
statement of the same decision would only give it two copies to drift apart.

Three blocks of numbers are stated outside this file, and a citation to one
resolves there. `DL-001`..`DL-013` are defined by the Decision Log table in
`docs/traktor_nml_tool_execution_plan.md`, whose surrounding document is
historical while that table is not; `DL-014`..`DL-023` by
`docs/decision-log-014-023-reconstructed.md`; and `DL-024`..`DL-039` and
`DL-040`..`DL-043` by the two plan documents `docs/README.md` names. Every
other number is stated in this file.

This file is the authority for the log's high-water mark, which is `DL-334`:
an entry numbered against anything else collides with an entry this file
names, so the next plan numbers from there.

- `matching.py`'s cascade accepts injected key providers; `fingerprint.py`
  supplies one behind an availability guard, so the core matching path
  never becomes import-guard-laden for a native chromaprint dependency
  most environments lack (DL-006).
- Fingerprinting is old-side-gated: only attempted when the old track's
  recorded path is still resolvable on disk at scan time, since a
  fingerprint computed only from the new/candidate side has nothing to
  compare against. Duration must agree within +/-1.0s before comparing;
  similarity above 0.95 counts as a match, 0.80-0.95 is logged for human
  review only and never auto-accepted (DL-013).
- Disk-scan reconnection's returned mapping is strictly one-to-one: after
  matching completes, any candidate holding more than one assignment
  removes all of its claimants, counted as destination collisions and
  exported to the ambiguity CSV rather than being rewritten, since two
  distinct old entries unambiguously matching the same physical file must
  never both point their playlist references at one `LOCATION` (DL-004).
- `volumes.py` requires explicit `VOLUME`/`VOLUMEID` identity for a
  disk-scan root rather than inferring it, since a guessed identity risks
  fingerprinting or rewriting the wrong file (DL-005).
- `splice`'s metadata-conflict abort writes a conflict report either way -
  whether the run aborts or `--on-conflict` resolves every conflict -
  so an accepted override still leaves a record of what was dropped
  (DL-008).
- `split`'s dangling references (a kept playlist pointing at a track
  outside the selection) are excluded by default, referentially closing
  every output; pull-in and fail are explicit, opt-in alternatives
  (DL-009).
- `--match-confidence` is one ordered enum (strict/loose/filename) rather
  than a second boolean flag, because disk-scan matching's filename-only
  tier and tag-based matching's artist-title-only tier are really one
  cascade, not two independent knobs (DL-010).
- `FILESIZE` and `PLAYTIME_FLOAT` identify a candidate only when both sides
  are Traktor-recorded, and refute one otherwise. Collection-to-collection
  (`preview-compare`, `rewrite-from-collection-compare`) both sides carry
  Traktor's own strings, so `artist_title_size_time` and `file_size_time`
  remain sound identifying keys and do match - the parity baseline records
  `matched_artist_title_size_time=1` on that path. Against a disk scan they
  cannot: measured over a real 6,386-entry collection and its files,
  Traktor's `FILESIZE` is the audio payload in KILOBYTES and sits 0.17%
  (median) to 0.41% (max) below `bytes / 1024`, because tag and artwork
  overhead is excluded, while a scanned candidate reports `st_size` in
  bytes (these error figures come from a 6,386-entry sample whose basis is
  no longer reconstructible from this repo - unlike the path-suffix
  measurement above, they cannot be re-derived from a named fixture, which
  is part of why DL-042 stopped fitting bounds to them); `PLAYTIME_FLOAT` differs from what mutagen reports by up to 0.172s
  and, compared as strings, never matches at all. Exact equality across
  those two sides is impossible rather than merely unreliable, so
  `matching.py` additionally compares them, and what it does with the
  result differs by quantity, because the two behave differently under a
  change of encoding.

  DURATION is the format-invariant: a transcode preserves length and
  changes bytes. It therefore refutes - a candidate whose length
  contradicts the collection's is removed. Cross-source the allowance is
  relative rather than a fixed offset, because mutagen's figure is exact
  only with a Xing/VBRI header and otherwise drifts by a percentage of
  track length.

  SIZE does not refute across sources at all, and that is deliberate. A
  DJ's library holds one track in several encodings across its life, on
  purpose: upgraded to STEMS, re-encoded to WAV for a performance,
  downgraded to reclaim drive space. Measured over 91
  same-name/different-format pairs in the 6,412-entry fixture and its
  files, disk-to-collection size spans 0.23x to 49.22x - a 0.23x
  space-saving downgrade and a 4.44x WAV upgrade both sat outside the
  factor band an earlier cut applied, so that band was rejecting exactly
  the cases a DJ creates deliberately. Size disagreement carries almost no
  negative information.

  Size keeps the POSITIVE half of the role. When a tier yields several
  candidates and cannot separate them, one whose size agrees to within a
  fraction of a percent is very likely the same bytes while the others are
  the same track re-encoded, so it wins the tie. Applied only when exactly
  one agrees: two agreeing, or none, leaves the ambiguity for the operator
  rather than inventing a winner.

  The `audio_id` tier is exempt from refutation outright - a
  content-derived identity outranks an approximate duration. Same-source
  (collection vs collection) keeps size refutation and its tight bound,
  since both sides are then Traktor's own number for the same quantity
  (DL-040).
- The path-suffix tiers (`path_suffix_3` at strict, `_2` and `_1` at loose)
  key on a file's position within its own folders rather than its absolute
  path, so a library moved as a unit still reconnects. Depth is what sets
  the level, measured over the 6,412-entry `collection_textual_patch_test.nml`
  fixture: three folders deep the key is unique for 97.2% of entries, two
  folders 91.7%, one folder 87.8%. Depth two is only consulted where depth
  three failed, and of the 235 entries depth three cannot resolve, depth two
  resolves 21, collides on 178, and cannot key the remaining 36 at all
  because their paths are too shallow - one automatic match per eight new
  adjudications, which is why it waits for loose rather than sitting at the
  default. Its collisions are ambiguity,
  never a wrong rewrite: every depth-two bucket holds exactly two entries
  and a bucket above one reports rather than picks. Without these, a disk scan against untagged files had no
  reachable tier at the default confidence at all: the documented
  "degrade to filename/filesize matching" fallback was inert, because the
  `filename_size` tier it named needed `--match-confidence filename` AND a
  byte-for-byte size agreement that cannot occur. That tier is retired
  rather than kept as a dead entry: sitting last in the cascade, its only
  possible effect was to break a `filename` ambiguity on a numeric
  coincidence (DL-041).
- The built-in cascade tiers are declared once, in `matching.py`'s
  `_CASCADE`, with each tier carrying the properties other code asks about
  it: whether its stats key is always seeded, whether the size/duration
  check may refute it, and whether it works without readable tags. The table is the one
  place they are declared, so no second list can disagree with it. The confidence ladder in
  `confidence.py` stays separate because it is that module's subject, but
  tests assert the two name the same tiers and that `record_keys` emits in
  the table's order - so reordering the cascade without updating the table
  fails rather than drifting.
- Refutation can be switched off per run with `--no-refute`, on every
  command that runs the cascade. The duration allowance is calibrated
  against one real library, so a library that breaks an assumption behind
  it would otherwise lose correct candidates with no recourse short of
  editing source. It is one switch and not five: exposing the individual tolerances
  would be a configuration surface nobody can calibrate correctly, while the
  constants at least carry the reasoning for their values. A run using it
  warns on stderr, because ignoring the collection's own numbers can commit
  a rewrite onto a file those numbers say is the wrong one (DL-042).
- Every text key component is casefolded before comparison: artist, title,
  album, file name, and path-suffix folder names. Windows and macOS
  filesystems are case-insensitive, so two names differing only in
  capitalisation denote the SAME file, and comparing them byte-for-byte
  manufactures a difference the filesystem does not have - measured on the
  6,412-entry fixture and its files, eight otherwise-perfect matches were
  lost to exactly that (Medjula/MeDJula, "We Like to Party"/"We like to
  Party", McNAiR/MCNAiR). `casefold` rather than `lower`, because it
  applies full Unicode case folding and so matches what macOS actually
  implements. `AUDIO_ID` is deliberately NOT folded: it is base64, where
  case is significant, and folding it would merge distinct identities into
  one bucket. Folding is safe because `record_keys`' output is only ever
  compared against other `record_keys` output; nothing downstream reads a
  key back as a display value. The failure it can introduce is the safe
  one - two different tracks differing only in case collide into an
  ambiguity the operator adjudicates, rather than one silently winning
  (DL-044).
- `bare_name_in_folder` (loose) and `bare_name` (filename) key on the file
  name with its container format stripped, the `.stem` infix included -
  Traktor names stem files `track.stem.m4a`, and without stripping that an
  upgrade reduces to `track.stem` and still misses. They exist because a
  re-encode REPLACES the file rather than moving it, so every tier keying
  on the name as written - `filename`, and the path suffixes, which end in
  it - stops matching and the entry reads as though the track were gone.
  Measured on the 6,412-entry fixture's real counterpart, 61 stem upgrades
  whose replacement sat on the same drive matched at NO confidence level
  at all: not refuted, never found. Levels follow the same evidence
  standard as the path suffixes rather than the desired outcome -
  `bare_name_in_folder` is strictly weaker than `path_suffix_2`, which sits
  at loose after its own uniqueness measurement, so it goes to loose too;
  promoting it to strict so that stem upgrades match by default would have
  contradicted that precedent. `bare_name` drops the folder as well and
  reaches filename level only: one real library holds 208 files named
  `vocals` and 176 named `drums` from stem-extraction folders. These tiers
  are only reachable because DL-040 stopped size refuting across sources -
  a re-encode runs 0.23x to 49x the original, so the earlier band would
  have found these candidates and then discarded them (DL-045).
- A candidate the check withdraws is counted as `refuted` alongside
  `unmatched` rather than folded into it, so "found it and declined" never
  reads as "the file is gone" - the same distinction DL-016 drew for
  `destination_collisions` (DL-043).
- The fingerprint tier needs three independent things - the `pyacoustid`
  module, the `fpcalc` binary to fingerprint with, and the chromaprint
  shared library to compare with - and any one of them missing degrades it
  to matching nothing. `HAS_ACOUSTID` only reports the import, so
  `fingerprint_unavailable_reason()` probes each in turn and the CLI names
  the one that is absent. This matters more than it looks: upstream ships
  no prebuilt shared library for any platform, so a machine with the module
  and the binary but no library is the ordinary case rather than an edge
  one.
- `spans.py` builds one `SpanIndex` per source document in a single pass -
  one pre-order walk for per-tag ordinals, one token scan for opening-tag
  offsets - and it is the only mechanism that maps a parsed element to its
  source byte span. `playlists.py`'s UUID-marker locator is gone, so a
  playlist whose `PLAYLIST` child carries no UUID is still located and no
  locator rescans the document per element (DL-014, DL-021).
- Every element is located in source by tree identity through `spans.py`'s
  shared `SpanIndex`, never by searching for an attribute value and never
  through a second, independent locator: a `PLAYLIST` element whose child
  carries no UUID is located by this same route, and one locator handles
  every case rather than two locators that could disagree about where an
  element sits (DL-021).
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
- The volume-relative-to-absolute transformation is split by side rather
  than owned by one module: `reconnect.py`'s `location_from_disk_path`
  handles the candidate (new) side, and `volumes.py`'s
  `local_path_for_location` handles the old side (DL-017).
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
- `splice_cmd` and `split_cmd` read, parse and write through helpers
  exported from `rewrite.py` rather than carrying their own input handling
  and a plain `write_bytes`, so both inherit the diagnostics and the atomic
  write `write_nml_safely` already implements (DL-019).
- `build-playlist` splits its core resolution/assembly logic into
  `buildplaylist.py` with only the CLI surface in
  `commands/build_playlist_cmd.py`, following the core-module-plus-thin-command
  pairing every other write command uses (DL-024).
- Resolving a track list against the collection calls `match_records` once
  per input line, with a single shared candidate index passed through its
  `indexes` parameter, because the mapping and stats `match_records`
  returns are keyed and aggregated per call and would otherwise collide
  every line onto one result (DL-025).
- In `build-playlist`'s matching call, the track list is the cascade's old
  (iterated, order-preserving) side and the collection is its new
  (indexed, candidate) side, mirroring how disk-scan candidates take the
  new side for reconnection (DL-026).
- An unmatched or ambiguous track-list line aborts `build-playlist`'s
  entire run with nothing written unless `--allow-unmatched` is passed,
  and the unresolved-line report is written whether or not the run
  aborts, matching splice's unresolved-conflict policy (DL-027).
- A playlist synthesized from external text has no source span to
  transplant, so its `NODE`/`PLAYLIST`/`ENTRY`/`PRIMARYKEY` fragment is
  always built as an `ElementTree` subtree and serialized with
  `ET.tostring`, which the existing span-transplant-vs-serialization split
  already treats as the sanctioned path for genuinely new content
  (DL-028).
- A synthesized `PLAYLIST` always gets a fresh `uuid4` hex, and a name
  collision with an existing playlist takes the same deterministic
  `"<name> (2)"` suffix `playlists.py` already applies to imported
  playlists, so playlist naming/UUID policy has one spelling across both
  entry points (DL-029). That suffix governs playlists being imported
  beside base's own; `splice --reconstruct-playlists` fills a matched
  base playlist in place instead, which is why the base node keeps its
  own UUID there and no fresh one is minted (DL-093, DL-095).
- `build-playlist`'s insertion point defaults to the root `FOLDER`'s
  `SUBNODES`, or an existing folder named by `--target-folder`; a named
  folder absent from the base aborts rather than being created, since a
  fabricated folder's `SORTING_INFO`/nesting semantics are unverified
  against the one confirmed schema version (DL-030). `--target-folder`
  naming the root folder's own name (conventionally `"$ROOT"`) resolves to
  the same default-root path as omitting the flag, rather than aborting
  with `target_folder_not_found`, since the root folder is a legitimate,
  reachable target and not merely a fallback. A `--target-folder` name
  matching more than one `FOLDER` anywhere in the `PLAYLISTS` tree aborts
  with `target_folder_ambiguous`, naming the match count, rather than
  inserting into whichever one document order happens to list first.
- The external track-list parser strips a leading numeric track-number
  prefix (`"1 - Artist - Title"`) before splitting, then splits the
  remainder on its first `" - "` occurrence only, never a bare hyphen, and
  reports (rather than silently mis-splits) any line without that
  delimiter, since a bare-hyphen split would corrupt real artist/title
  text like "Jean-Michel" (DL-031).
- `build-playlist` calls the matching cascade at a fixed
  `MatchConfidence.LOOSE` with no `--match-confidence` flag, because a
  plain-text track list carries only artist and title, making every tier
  above `artist_title` structurally unreachable for it (DL-032). That
  reason covers plain-text input only; why LOOSE stays fixed for CSV, M3U
  and folder candidates, which can reach the stricter tiers, is DL-276's
  (see Resolution runs at a fixed `MatchConfidence.LOOSE` below).
- `build-playlist` makes no network or API calls of any kind - track
  identity is resolved entirely against the local base collection through
  the existing matching cascade, consistent with the tool's offline
  posture elsewhere (no live Spotify/Apple/Beatport/Bandcamp lookups).
- ISRC-based matching was considered and rejected for `build-playlist`'s
  v1: Beatport downloads sometimes carry a label-sourced ISRC tag but
  Bandcamp downloads mostly do not, so an ISRC tier would only be a
  partial win while adding new matching-cascade code; deferred rather
  than built.
- `build-playlist`'s output-path refusal covers the track-list path as
  well as the base path, via `rewrite.path_collides`, a small shared
  helper also used by `splice_cmd.py`, rather than `write_nml_safely`'s
  `extra_inputs` parameter (which exists only on the attribute-patching
  write path these span-assembly commands do not use) (DL-033).
- `build-playlist`'s unresolved-line report is written through
  `rewrite.write_row_report`, a shared helper (`csv.DictWriter`, header
  row, `newline=""`, UTF-8 encoding) also used by `splice_cmd.py`'s
  conflict report, rather than each command hand-rolling its own copy of
  the same CSV shape; a write failure (e.g. the report path's parent
  directory doesn't exist) is reported and exits 2 like every other
  input/output error, instead of raising unhandled (DL-034).
- `build-playlist` returns exit code 2 for both an input error (a
  malformed base, a missing track list) and an unresolved-track abort,
  rather than a distinct code per failure class, matching
  `splice_cmd.py`'s own existing convention of not distinguishing them
  (DL-035).
- A `build-playlist` run that resolves zero lines (an empty track list,
  every line unparseable, or every line unmatched with
  `--allow-unmatched`) aborts with a dedicated error and writes nothing,
  rather than writing a `PLAYLIST` with `ENTRIES=0`, matching `split.py`'s
  own convention of dropping a playlist reduced to zero entries rather
  than writing it empty (DL-036).
- Two track-list lines naming the same collection track resolve and
  serialize independently in `build-playlist`, producing duplicate
  `ENTRY`/`PRIMARYKEY` elements rather than being deduplicated, since a
  Traktor `PLAYLIST` is an ordered list of references and the operator's
  input order and repetition are taken as authoritative (DL-037).
  `splice --reconstruct-playlists` deduplicates instead, because a track
  reached twice while folding two documents together is an artefact of
  the fold rather than anything an operator wrote (DL-103).
- A base document `build-playlist` is given with no `PLAYLISTS` section,
  root `FOLDER`, or `SUBNODES` element at all aborts with a
  `no_root_subnodes` error rather than synthesizing the missing
  structure, reusing the same error name `splice.py` already returns for
  the identical failure mode (DL-038). A named `--target-folder` that
  exists but has no `SUBNODES` child of its own reports the distinct
  `target_folder_no_subnodes` instead, so the two failure modes (whole
  document missing its PLAYLISTS structure vs. one malformed named
  folder) are never conflated in the error a user sees.
- `build-playlist`'s synthesized fragment is inserted exactly as
  `ET.tostring` serializes it (attribute quoting, empty-element
  shorthand, absence of extra whitespace), with no attempt to match the
  base document's own formatting conventions, the same as `playlists.py`'s
  existing renamed/redirected fragments already do (DL-039).
- The two reconnect subcommands run behind a printless core that returns
  one typed result per command, with a renderer turning that result into
  stdout lines, stderr lines and an exit code; the argparse handler is
  `emit(render(core(args)))`. A GUI review table needs the mapping, stats
  and ambiguity rows mid-run and as objects, and a transcript parsed after
  the fact arrives too late for that, so the flattening lives behind a
  render boundary the CLI and a future GUI both sit above (DL-046).
- `plan_and_write_nml` is a printless read/parse/patch/write sequence
  returning a `WriteOutcome`; `write_nml_safely` is a thin printing
  wrapper over it. `rewrite-from-reconnect`'s stdout is produced inside
  `write_nml_safely`, not in the handler, so a printing core would leave
  the reconnect core itself writing to stdout; a reconnect-local write
  path would instead duplicate the read/parse/patch/write skeleton
  DL-019 exists to prevent. The separation is proved rather than merely
  asserted, by the unregenerated manifest cases for `rewrite` and
  `rewrite-from-collection-compare` (DL-047).
- `WriteOutcome` carries `stats` as `None` when the run failed before
  stats were collected, and carries both `stats` and `error` when it
  failed after. On the lxml path stats print before `apply_and_write`, so
  a `text_patch_error` emits the full stats block on stdout and then the
  error on stderr; a single error flag cannot reproduce that ordering, so
  the presence of stats is itself the signal (DL-048).
- The output-equals-input refusal stays the first thing
  `plan_and_write_nml` does, ahead of parsing and ahead of the
  `collect_patches`/`mutate_tree` callback: the reconnect callback owns a
  disk scan that can run tens of minutes and writes the tag cache, so
  running it before the collision check would make a refused write cost
  the whole scan. A collision therefore produces no `ReconnectResult` at
  all (DL-049).
- `warn_refutation_disabled` lives in the renderer, not the reconnect
  core, and the fingerprint-dependency warning is a field on the result:
  the refutation warning is a pure function of argv and the fingerprint
  warning is derived from probing the run, so only the second is
  knowledge the core discovers. Argv-derived text belongs above the
  core boundary and run-derived text belongs on the result, and the
  renderer emits the fingerprint line before the refutation line to
  preserve stderr order (DL-050).
- The renderer returns buffered stdout and stderr line lists plus an exit
  code, and a single `emit` helper in the render module performs every
  print: the renderer must be a value-returning function to compare
  against recorded stdout, and the manifest captures stdout and stderr as
  separate streams, so buffering cannot reorder anything it observes.
  `commands/reconnect_cmd.py` then holds no print call at all (DL-051).
- The reconnect core and renderer live in `reconnect_run.py` and
  `reconnect_render.py`, not under `commands/`: `commands/__init__.py`
  imports every command module at CLI startup, so a GUI importing the
  core through `commands/` would drag every subparser with it. The pair
  sits beside `reconnect.py` in the package root, and `commands/` imports
  downward into it (DL-052).
- `ScanCancelled`, `VolumeIdentityError` and the fingerprint-unavailable
  error propagate out of `plan_and_write_nml` unchanged; the reconnect
  core converts the latter two into typed errors on its result and lets
  `ScanCancelled` escape. A cancelled scan must never return partial
  results, because a short candidate list reads as a mostly-missing
  collection - catching it at the write shell would turn a refusal into a
  plausible wrong answer. Only the two errors that already map to a
  printed `key=value` line and exit code 2 become data (DL-053).
- `run_reconnection` and both reconnect cores accept `on_progress` and
  `cancel` keyword arguments and forward them verbatim to
  `index_scan_roots`; both default to `None` and the argparse handlers
  pass neither. `index_scan_roots` already accepts both, and a core
  boundary that dropped them would force a GUI to bypass the core and
  re-implement the pipeline just to get live progress or a cancel token -
  exactly what DL-046 exists to prevent (DL-054).
- The refutation-disabled message has one definition:
  `shared_args.refutation_disabled_line()` returns the text,
  `warn_refutation_disabled` prints what it returns, and
  `reconnect_render` appends what it returns. No manifest case sets
  `--no-refute` for either reconnect command, so a second copy of the
  literal in the renderer would drift from the one in `shared_args`
  without any oracle noticing; routing both callers through one
  text-producing helper makes drift impossible rather than merely
  detectable (DL-055).
- `index_scan_roots` emits `tag_reading_unavailable` once at entry when
  mutagen is absent and `disk_scan_progress` every `progress_every` files
  inside the walk directly to stderr, so a core that calls it writes to
  stderr no matter how carefully the rest of the core is written, and
  DL-046's printless-core property is false in exactly the case that
  matters, a real scan on a machine without mutagen. `index_scan_roots`
  accepts an `on_diagnostic` keyword argument that receives each fully
  formatted diagnostic line; it defaults to `None`, in which case the
  function prints to stderr. `reconnect_run` passes a collector, an
  ordered list appended to at the point each line would have been
  printed, so the core writes to no stream and emission order is
  preserved; the renderer emits the collected diagnostics before the
  fingerprint and refutation warnings, the order the pipeline produces
  them in. The transport is default-inert rather than a signature
  change, because `index_scan_roots` has a second production caller,
  `discover_tracks_cmd.py`, with no manifest case and therefore unpinned
  - a default-`None` parameter leaves it byte-identical by construction
  rather than by test. The callback receives the formatted line rather
  than structured fields, so the message text keeps exactly one
  definition, the same argument DL-055 makes for the refutation line
  (DL-056).
- Buffered renderer equality is not accepted as evidence that the
  reconnect core is printless; the CLI-level stderr assertion is.
  `render(core(args))` compares the lines a renderer returns, so a stray
  print inside the core never enters the comparison and the equality test
  passes while the process still writes to the stream. The only place a
  leak is observable is a real invocation, where stdout and stderr are
  captured from the process, so `tests/test_baseline_parity.py` asserts
  stderr alongside stdout and exit code - free, because the manifest
  already records a stderr field per case. All twelve recorded stderr
  values are empty, which makes that assertion precisely a no-leak
  detector for every pinned path (DL-057).
- `matching.py`'s `match_records` takes an `on_review` keyword defaulting
  to `None`, in the same shape `on_progress`/`cancel`/`on_diagnostic`
  already use; `resolve_reconnection` and `run_reconnection` forward it
  verbatim. `match_records` has a production caller with no manifest
  case - `tracklist.resolve_tracklist` reaches it from `build-playlist` -
  so a required parameter would leave that caller changed with nothing
  pinning its bytes; a default-`None` keyword leaves every call site
  byte-identical by construction instead, the argument DL-056 makes for
  `index_scan_roots`' second caller applied here (DL-058).
- Reviews are built inside the per-record cascade loop `match_records`
  already runs, from the same branch that decides each record's stats
  bucket, rather than re-derived by a second pass over the candidate
  indexes: the loop already computes each record's tier bucket, the
  current-Sync-copy preference, the refutation filter and the
  single-size-agreement tiebreak, and a second implementation of that
  selection logic could drift from the first with no oracle noticing,
  the drift DL-055 already routes the refutation-disabled message through
  one helper to avoid (DL-059).
- The size/duration contradiction rule has one definition:
  `_refutation_reason(old_claims, candidate)` returns a `RefutationDetail`
  or `None`, and `_claims_refute` is that call compared against `None`.
  A Refuted row's detail panel names the contradicting field and
  quantifies it against its allowance, so the display reuses the same
  arithmetic the filter uses rather than a second, display-only copy of
  tolerances calibrated against one real collection that could drift
  from the copy deciding refusals; the detail object is constructed only
  where the boolean form would return `True`, so the common
  non-refuting path allocates the same `_Claims` it always has (DL-060).
- `run_reconnection` takes `reviews` as an optional caller-owned list it
  appends into and populates `ReconnectResult.reviews` from, in the same
  shape `diagnostics` already uses so lines collected before a later
  `VolumeIdentityError` or `_FingerprintUnavailable` raise survive in the
  caller's scope. Omitted, no collector is installed and `match_records`
  constructs no review object at all, which is what leaves matching
  results identical by construction rather than by measurement
  (DL-061).
- `resolve_reconnection` overlays `destination_collision` onto a review
  after `enforce_one_to_one` runs, rather than `match_records` emitting
  it: `reconnect.py`'s module docstring states that `match_records` is
  unaware a one-to-one guarantee is layered on its plain old-to-new
  mapping, so emitting the collision status from inside the matcher
  would push a post-pass concept down into a module that would then be
  wrong about records it matched correctly. `resolve_reconnection`
  already holds `collided_keys` and already walks every unmatched record
  to build `ambiguity_rows`, so the reclassification happens in that
  same walk (DL-062).
- Re-encoded is derived in `traktor_nml/gui/review_model.py`'s
  `row_status`, from an emitted review, not carried as a matcher status:
  matching has no notion of a format change, since `_FORMAT_SUFFIX`
  strips the container so `bare_name_in_folder`, `filename` and
  `bare_name` key a stem, and a stem upgrade matches those tiers exactly
  like any other move. Calling the outcome re-encoded is a comparison of
  the suffix on the old record against the suffix on the winner, which is
  a presentation question about a match the matcher already made, so
  deriving it above the core keeps the matcher's result unchanged and
  puts all six Specs statuses in one module (DL-063).
- The four confidence tokens Specs names - Strong, Good, Weak, None - map
  from the cascade tier that produced a candidate, held as a table
  (`_STRONG_TIERS`/`_GOOD_TIERS`) in `traktor_nml/gui/review_model.py`,
  and are not `MatchConfidence` values: `MatchConfidence` has three
  members (strict/loose/filename) and is a run-wide ladder gating which
  tiers may fire, not a per-candidate judgement, so reusing it as the row
  token would print the same word on every row of a run and would read
  Weak for a strict match found during a loose run. The token is derived
  per candidate from the tier name on its review instead (DL-064).
- `write_reconnect_result(args, provide_result, on_progress, cancel)` is
  parameterised by a result provider called from inside
  `plan_and_write_nml`'s own callback, not by an already-computed
  `ReconnectResult`: the output-collision refusal is
  `plan_and_write_nml`'s first statement, ahead of parsing and ahead of
  either callback, which is what makes a refused write cost nothing
  rather than the scan (DL-049). A signature taking a finished result
  would force every caller to run its scan before that refusal could be
  reached, moving the cost back in front of the check; a provider
  invoked inside the callback keeps the refusal first for both callers,
  with `rewrite_from_reconnect` supplying `run_reconnection` and the
  wizard supplying a provider that returns the reviewed result it
  already holds (DL-065).
- `rewrite_from_reconnect` is one call to `write_reconnect_result`, so
  both write paths share a single implementation of patch collection,
  CSV export, holder population and typed-error mapping. Proving
  zero-override byte identity only by test would leave the two paths
  free to diverge in every commit between test runs; with one
  implementation the wizard write and the CLI write differ solely in
  which provider ran, so identical bytes follow from the provider
  returning the same result object. The three unregenerated
  `rewrite-from-reconnect` manifest cases (dry-run, plain, and `--csv`)
  are what proves the factoring itself changed nothing (DL-066).
- `output_collision_refusal(input_path, output_path, extra_inputs)` in
  `rewrite.py` is the single definition of the collision rule:
  `plan_and_write_nml`'s first statement returns a `WriteOutcome` built
  from it, and the wizard calls it directly to decide whether its Write
  control is enabled and what reason it shows. A wizard-side
  re-implementation of resolve-and-compare-against-every-input would be a
  second copy of a safety rule that could drift silently the moment
  `extra_inputs` grows a member; one predicate with two callers keeps the
  disabled-button reason the same string the CLI prints (DL-067).
- `ScanCancelled` is caught nowhere on the wizard's write path: it
  escapes the provider, escapes `plan_and_write_nml`, and escapes
  `write_reconnect_result`, so a cancelled scan leaves no
  `RewriteReconnectResult` at all. DL-053 already records why a
  cancelled scan yields no result rather than a partial one - a short
  candidate list is indistinguishable from a complete one and would
  report most of the collection as missing - and a review table would be
  an even more persuasive way to deliver that wrong answer than a stats
  line, so the exception is left to cross every function on this path
  untouched (DL-068).
- `design/reconnect-wizard/Specs.dc.html` is read as a committed primary
  source: `.gitignore` excludes only the generated
  `/design/*/reconnect-wizard.html` bundle, and every `.dc.html` plus
  `canvas.json` is tracked. The `.dc.html` files are the artboard sources
  the bundle is seeded from, so `Specs.dc.html` carries the same weight
  as `docs/nicegui-gui-analysis.md`, and `design/reconnect-wizard/README.md`
  fixes disagreements among the design files in `Specs.dc.html` first
  (DL-071).
- Where `Specs.dc.html` and sections 1-5 of `docs/nicegui-gui-analysis.md`
  disagree, `Specs.dc.html` governs the six statuses, the seven filter
  chips and the keyboard map, and section 4 governs `run.io_bound`,
  `ui.log` and the `local_file_picker` component; both splits are
  recorded in `traktor_nml/gui/README.md` rather than one document being
  silently preferred, since a reader who meets only one of the two
  documents would otherwise be unable to tell whether a difference was
  decided or overlooked. `Specs.dc.html` wins on what the operator sees
  and presses because it is the cross-screen contract; section 4 wins on
  framework mechanics because `Specs.dc.html` names no framework at all
  (DL-072).
- `scan-reconnect-candidates`' dual tier membership - primary Tier 1
  assignment and separate Tier 2 form-generator eligibility - is resolved
  by `tests/test_gui_command_classification.py`'s two predicates,
  `PRIMARY_TIER` and `TIER2_ELIGIBLE`, checked against the real
  `build_parser` choices, and is not re-derived anywhere else; the wizard
  reads the dual membership as already settled (DL-073).
- Accepting an alternative candidate resolves its VOLUME/VOLUMEID through
  `reconnect_run.resolve_candidate_volume_identity` against
  `ReconnectResult.volume_identities` - the same per-scan-root identities
  and the same `relative_to` subtree test `_reencode_winning_locations`
  applies to winners - rather than writing the candidate's placeholder
  `LocationParts` or re-deriving identity from `source_path.anchor`. An
  anchor-keyed re-derivation cannot tell apart two scan roots that share
  a filesystem anchor but were given different `--volume-map` identities;
  `resolve_candidate_volume_identity` raises `UnresolvedCandidateVolume`
  rather than passing the placeholder through when no scan root claims
  the candidate (DL-074).
- The wizard imports and drives `run_reconnection` and the two reconnect
  cores directly and renders its own view from `ReconnectResult`;
  subprocess-scraping the CLI's key=value stdout transcript was evaluated
  as the data source, rejected for Tier 1, and survives only as the
  `docs/nicegui-gui-analysis.md` section 5 fallback. Tier 1 needs
  structured data while a run is still open - a live scan progress feed
  and an ambiguous-match table the operator acts on mid-run - and a
  parsed transcript exists only after the process has exited, so a
  scraping wizard could build its review table only after the decision
  point the table exists to serve, with no live object to cancel. `ui.log`
  is fed from `reconnect_render`'s line-producing functions over the
  `RenderedOutput` they already return, not from parsed stdout (DL-075).
- The wizard's provider returns a `ReconnectResult` built by
  `traktor_nml/gui/wizard_state.py`'s `amended_result(result, decisions)`,
  which replaces only `mapping`; `stats`, `ambiguity_rows`, `old_records`,
  `reviews`, `warnings` and `diagnostics` carry through unchanged as the
  scan's own record, and the wizard renders override counts from the
  decision set in a separate panel beside them. Re-deriving `stats` and
  `ambiguity_rows` from an amended mapping would change what those
  fields mean, since `ambiguity_rows` records which records the matcher
  found ambiguous and no operator decision changes what the matcher
  found; carrying the scan's counts through unchanged keeps one meaning
  for those fields on both the wizard and the CLI paths (DL-076).
- The fingerprint control's enabled state comes from
  `traktor_nml/gui/wizard_state.py`'s `fingerprint_control_state()`,
  which mirrors `reconnect_run.py`'s own two-step check in its own
  order: `fingerprint_key_provider` being `None` disables the control
  with the not-installed reason without calling
  `fingerprint_unavailable_reason` at all, since that binding is `None`
  in exactly the case the probe would raise `TypeError: 'NoneType'
  object is not callable`; only when the provider is not `None` is
  `fingerprint_unavailable_reason()` called and a non-`None` return used
  as the reason. Putting the two-step in a plain function rather than
  inside the view gives the deliberately untested view a tested source
  of truth (DL-077).
- `traktor_nml/gui/theme.py` holds every Specs colour, type size,
  spacing step and radius, and emits the page stylesheet as a pure
  string, so a hex or a pixel size is written once rather than
  repeated at a call site - the drift DL-055 closes for the refutation
  message, closed here by holding one definition. The module imports
  no `nicegui`, so the pytest interpreter reads it directly (DL-078).
  (`traktor_nml/gui/CLAUDE.md`'s file table names what `theme.py`,
  `keymap.py` and `announce.py` each hold.)
- The review table is hand-rolled `ui.row` rows per record rather
  than `ui.aggrid`. aggrid claims the arrow keys, and Specs binds
  Up/Down, Shift-Up/Down and 1-9 over exactly that table, so adopting
  aggrid buys a grid and then spends the milestone fighting it back
  for the contract that is the point of the milestone.
  `file_picker.py`'s browser fallback dialog keeps its own aggrid use
  and its own key handling, outside this scope (DL-079).
- `traktor_nml/gui/keymap.py` is the single source for both the
  rendered help panel and the live bindings, and `app.py` applies
  actions from a dict table (`_ACTION_APPLIERS`) whose key set a guard
  pins to `keymap.ACTION_NAMES`. Rendering the help panel from a
  second, hand-written table rather than from `keymap.ENTRIES` lets
  the two drift; a dict from action name to callable, rather than a
  branch chain, leaves no branch an unlisted action falls through, and
  the guard fails the suite instead of the operator (DL-080).
- Keyboard dispatch is a pure function in `keymap.py` taking the key,
  the modifiers, the active scope, the row count, the focused index
  and the focused row's own candidate count, and returning an action;
  `app.py` only applies the action it returns. `app.py` is untested at
  runtime, so the arrow bounds, the Shift-extended ranges and the
  digit-to-candidate mapping - arithmetic that needs no DOM - sit in
  the nicegui-free module on the `_fs_nav.py` precedent (DL-081).
- `ui.keyboard` is registered with `ignore=['input', 'select',
  'textarea']`, dropping `'button'` from NiceGUI's default ignore list
  of `['input', 'select', 'button', 'textarea']`. Every review row
  carries A, R and U buttons, so focus rests on a button through
  ordinary review work, and the default list swallows the review keys
  at exactly that moment (DL-082).
- Announcement text and its cadence are built by pure functions in a
  nicegui-free module (`announce.py`); `app.py` owns only the two live
  regions it pushes into, one polite and one assertive, and pushes
  only the strings `announce.py` returns. Specs fixes both the wording
  and the rate - progress at most every two seconds, each decision as
  it happens, errors and completion assertive and naming the file
  consequence in the first sentence - all computable with no browser
  present (DL-083).
- Every milestone ends with the wizard served over HTTP, driven in a
  browser, and compared screen by screen against the artboard it
  implements; the record written to `docs/` carries a matches or
  differs verdict per named surface, and the milestone passes only
  when every entry reads matches or the differs entry is carried into
  this file as a recorded framework shortfall in the form DL-087
  fixes. Every `gui/` guard reads source text or walks the module
  graph rather than exercising a served page, and the served-page gate
  that closed the keyboard and announcement milestones surfaced
  defects no such guard saw, five of them present in that wave's
  baseline commit. The verdict, not the written record alone, is the
  pass condition (DL-084).
- A surface's verdict carries a structural reading beside its atom
  readings: the app shell, the column model, the card structure and
  the table geometry the artboard draws, each read off the served page
  the way a height or a hex value is. A surface carrying no structural
  reading fails the gate. An atom is a property of one element - a
  height, a colour, a gap, an attribute - and a record can hold every
  atom a surface has while the surface is composed nothing like the
  artboard, which is what four records reading matches on every entry
  do. The structural reading is what a person looking at the two
  screens sees first, so it is the reading the gate cannot omit
  (DL-169).
- The structural gate covers every route a record measures, the
  reconstruct page at `/` included: `Reconstruct.dc.html`,
  `Preview.dc.html`, `Resolve.dc.html` and `Write.dc.html` on canvas
  page 3 draw that page, so a structural verdict has a drawn structure
  to read against and a record covering `/` carries one per surface.
  `Specs.dc.html`, which governs under DL-088, specifies the behaviour
  the four screens render; the composition is read from the screens.
  Atom readings are gated as any other surface's are (DL-172, DL-200).
- A structural differs entry is recorded under its own heading,
  "Composition not built", and not under either heading beside it: a
  framework shortfall is a rule the running framework refuses, a
  design-set divergence is a value the prose supersedes under DL-088,
  and an entry here is work not done. The three are told apart by what
  ends them - a shortfall ends when the framework admits the rule, a
  divergence ends when the prose and the artboard agree, and a
  composition entry ends by being built - so an entry filed under the
  wrong one waits on the wrong event (DL-170).
- Re-verdicting an existing record adds a structural verdict stating
  what that run did not measure and leaves every atom verdict as it
  stands, readings included. A record is the transcript of one run
  against one served page at one commit, and a reading edited
  afterwards transcribes nothing. The guard holds a digest
  of each record's reading lines so an edited reading fails the suite
  rather than waiting on a reviewer's eye (DL-171).
- The token set is one dark theme; no light variant and no theme
  switcher. All ten artboards paint the same `#0F1113` ground and
  Specs states its contrast results against those surfaces; a light
  variant is a second palette owing its own colour-blindness
  simulation, design work Specs does not do (DL-085).
- The seven IBM Plex woff2 faces the artboards import - Sans
  400/500/600/700 and Mono 400/500/600 - live in
  `traktor_nml/gui/fonts/` and are served by the application itself.
  `design/reconnect-wizard/Main.dc.html` line 11 imports exactly those
  seven weights, and the wizard runs under `ui.run(native=True)`,
  where a CDN link resolves to nothing offline and reports nothing
  when it fails - the shape of the defect this fixes, in which
  `theme.py` names a face the page never paints (DL-163).
- `theme.py` holds `FONT_URL_BASE` and emits the `@font-face` blocks;
  `app.py` mounts that same constant through `app.add_static_files`.
  An `@font-face` src and the route that answers it are one fact split
  across two files, and `theme.py` may not import nicegui (DL-069), so
  the constant lives in the nicegui-free module and the mount reads it
  (DL-164).
- The font guards assert the face files, their byte sizes, the
  `@font-face` blocks and the mount argument together, and no guard
  asserts a font-family name alone. `theme.FONT_SANS` already names
  IBM Plex while the page paints Segoe UI, and `document.fonts.check`
  returns true for an absent Plex face, so a name assertion is true in
  exactly the broken state (DL-165).
- `OFL.txt` ships in `traktor_nml/gui/fonts/` beside the faces, and
  the upstream release and per-file SHA-256 are recorded in
  `traktor_nml/gui/README.md`. IBM Plex is SIL OFL 1.1, and both the
  wheel and the frozen build copy that directory (DL-166).
- The faces are the upstream woff2 releases, committed unmodified and
  unsubsetted. Subsetting adds a build step whose output no upstream
  hash can verify, and a vendored binary that cannot be checked
  against its source is a worse failure than the bytes it saves
  (DL-167).
- `pyproject.toml` carries the fonts directory as package data and
  `traktor-nml-spike.spec` carries it in `datas`. `pyproject.toml`
  declares no package data otherwise, so a wheel or a frozen build
  answers 404 for every face and falls back silently - the same
  silence, reached by a different route (DL-168).
- `traktor_nml/gui/README.md` states the exact byte total the
  vendoring step measured, face by face, and a guard asserts the
  directory against that recorded total rather than against a round
  number. A ceiling chosen for looking generous permits any drift
  under it; the measured total names what is actually there, so a face
  swapped for a larger one is a guard failure and a decision, not a
  silent gain (DL-176).
- woff2 ships with no woff or ttf fallback. The only client is the
  WebView2 or WebKit engine pywebview embeds under
  `ui.run(native=True)`, and both have supported woff2 since long
  before any version this project installs (DL-175).
- The `@font-face` blocks and the body font rule are emitted at the
  cascade position DL-086's ladder records, so they win against
  Quasar's own Roboto default, and a guard asserts that ordering in
  the emitted text rather than trusting it (DL-173).
- The installed nicegui version and the module path and signature of
  `app.add_static_files` are read from the installed distribution and
  cited in `traktor_nml/gui/README.md` before `FONT_URL_BASE` is
  fixed. No guard under the system interpreter can execute the mount -
  that interpreter has no nicegui - so the reading is the only check
  the fact gets (DL-174).
- The stylesheet guard asserts the literal seven: `len(FONT_FACES)`
  is 7 and the emitted sheet holds exactly seven `@font-face` blocks.
  A guard that only checks each declared face is emitted stays green
  when a weight is dropped from the tuple (DL-179).
- The suite baseline is 534 passed and 3 skipped under the system
  interpreter, which has no nicegui, so the font guards read source
  text and never import `traktor_nml.gui.app` (DL-178).
- The font work closes with a served-page run from `.venv` that reads
  `document.fonts` for the seven faces and re-measures the two stacks
  whose measurements recorded the defect - the sans stack at Segoe
  UI's width and the mono stack at Consolas' - written up as a record
  under the amended gate (DL-180).
- The network-host invariant and the repository-state invariant carry
  guards rather than resting on a review-time grep and on
  test-procedure prose. Both are conditions a person is asked to
  notice, and the four records that read matches on every atom are
  what asking a person to notice is worth (DL-181).
- The gate amendment runs before the font work and before the
  re-verdicting: the font work's closing record is written under the
  amended gate and checked by the guard the amendment installs, and
  the re-verdicted records name entries the amendment creates. The
  font work and the re-verdicting both write `docs/CLAUDE.md`, so they
  are sequenced rather than parallel (DL-182).
- The wizard's shell is built from `ui.header` and `ui.footer` rather
  than from hand-rolled fixed bands, because Quasar's own `QLayout`
  writes each band's height onto `q-page-container` as padding and a
  fixed band fights that reservation; each is constructed with
  `bordered` and `elevated` off, so the rule and the ground each band
  carries are the ones `theme.py` emits (DL-183).
- The header band, the middle region and the footer band are the three
  rows `.app` draws at `Main.dc.html:15`, and the middle owns the page
  scroll rather than the document (DL-184).
- `_page_chrome` builds both bands and hands back the middle container,
  which each route enters with a `with` statement, so a page's body
  lands inside the scrolling region by construction rather than by
  caller discipline (DL-185).
- Each section a page builds is a card - `.wizard-card` holding a
  `.wizard-card-head` with its `.wizard-card-title`, and a
  `.wizard-card-body` - as `Main.dc.html:32-35` draws it (DL-186).
- Each step's advancing control is built once, in its own group inside
  the footer action row, and the step change decides which group the
  band shows; the control invokes the function the step defines, so its
  enabled state is held once rather than kept in sync between a copy in
  the step and a copy in the band (DL-187).
- Every dimension and every colour the shell and the cards measure at
  is a constant in `theme.py`, sourced in a comment to the artboard line
  that states it, and a call site names a class rather than a value,
  because `theme.py` is the module a guard under the system interpreter
  can read (DL-188).
- A guard asserts a rule's content and where a control is constructed;
  the rendered height, the scroll owner and the computed card padding
  belong to the served-page record, because a guard that reads a name is
  true in exactly the broken state (DL-189).
- An entry leaves "Composition not built" only where a record reads its
  structure built, the prose that strikes it names the record and the
  reading that carries it, and the milestone that strikes it closes on a
  served-page record of its own, taken after the strike (DL-190).
- The reconstruct page composes against the same shell as the reconnect
  wizard - the same bands, the same middle, the same card triplet - and
  DL-172 decides what a record may verdict about that route, not which
  shell it is built from. The two-column `main`, the review table's grid
  geometry and the 400px detail rail are outside this work's scope, so
  each stands as written under "Composition not built" (DL-191).
- `nicegui.css` sets `align-items: flex-start`, `gap: 1rem` and
  `padding: 1rem` on `.nicegui-header` and `.nicegui-footer` and gives
  both `flex-direction: row`, so each band restates the alignment, the
  gap and the padding and takes the direction the framework already
  gives it; the wizard sheet reaches the head after the framework sheet,
  so the restatement wins at equal specificity (DL-192).
- The viewport-height declarations key on Quasar's and nicegui's own
  `q-layout`, `q-page-container`, `q-page` and `nicegui-content` classes
  rather than on `wizard-` names, because `app.py` constructs none of
  those four elements and a `wizard-` class no call site names fails
  `tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py`
  (DL-193).
- A structure a record reads as partly refused keeps a narrowed entry
  naming what the framework refused and the computed value that shows
  it, rather than being struck or left as written (DL-194).
- `test_every_structure_a_record_names_resolves_in_the_decision_log`
  reads the newest record naming a structure rather than every record,
  so a structure a later run reads as built stops naming an entry the
  section does not hold while the standing records keep their differs
  rows untouched (DL-195).
- The card triplet is the whole of the box rule: `.wizard-surface` is
  absent from the stylesheet and from every call site, because a rule no
  call site names fails the class-reach guard (DL-196).
- The keyboard record and the announcement record are not read again
  for this version. Their ground for a re-read stands - each advancing
  control is built in the footer band, and its place in the DOM sets
  both the tab order and the point an announcement is triggered from -
  but accessibility work is out of scope for this version, and a reading
  that changes nothing about the code is a reading this version does not
  take. `docs/2026-09-06-wizard-focus-order-browser-record.md` holds the
  ring as it was walked before the step regions existed, and it says
  which page and which step it covers. A record written after this
  states that the ring is unread and why, rather than leaving it as a
  debt the next record inherits (DL-197).
- The reconstruct page is stepped: `Reconstruct.dc.html`,
  `Preview.dc.html`, `Resolve.dc.html` and `Write.dc.html` each draw the
  header as the brand, its divider and the two section tabs, and each
  draws the four-step rail inside `main` rather than in the header band,
  so the rail and the tab strip sit in different regions and neither
  displaces the other. `Specs.dc.html` and the four screens agree on the
  header, so DL-071 asks nothing of Specs here (DL-198).
- The rail is a `nav` of this module's own spans rendered from
  `reconstruct_steps.rail_records`, placed as the page region's first
  row, rather than a `QStepper` header: `Resolve.dc.html:118` draws
  `.steprail` inside `main` at `grid-column: 1 / -1`, and a QStepper
  draws its own numbered strip above its panels and none of the rail's
  states (DL-199).
- The reconstruct page at `/` is inside the structural gate, read
  against the four artboards on canvas page 3 that draw it. A structural
  verdict needs a drawn structure to read against and now has one, so
  every record covering that route carries a structural reading per
  surface beside its atom readings, as a record covering `/reconnect`
  does (DL-200).
- The reconstruct page's column model, table geometry and detail rail
  are its own entries under "Composition not built", separate from the
  three read against the reconnect wizard's artboards: an entry names
  the artboard file and selector it is read from, and `Review.dc.html`'s
  geometry and `Resolve.dc.html`'s are different geometries on different
  routes, so one entry cannot end for both (DL-201).
- `reconstruct_steps.STEPS` is the one place a step number or a step
  label is written, and position is the single point where the table and
  the step the operator has walked to meet: a row before the current one
  reads done, the row equal to it reads current, a row after it reads
  upcoming, and a current number the table does not name leaves every row
  upcoming rather than marking the first (DL-202).
- `reconstruct_steps.py` imports no framework, so the rail's records and
  the reachability rule are read by the suite under the system
  interpreter; `app.py` renders the records and decides none of them
  (DL-203).
- `conflict_model.resolve_gate` answers the outstanding count, the
  decided count and whether the step may be left in one value over one
  walk of the groups, and the footer's sentence and the advancing
  control's enabled state both read it: a count computed for the sentence
  and an emptiness computed again for the control can disagree, and the
  disagreement shows as a control the operator can press over a sentence
  saying they cannot (DL-204).
- The reconstruct route carries its own name-to-applier table.
  `keymap.py` is unchanged - its entries already bind digits 1-9 to
  `pick_candidate` at `SCOPE_TABLE` - and the wizard's own
  `_ACTION_APPLIERS` is typed on `_WizardPageState`, whose review rows
  and decisions this route holds none of, so the second table dispatches
  the same action names onto the resolve table's own holder rather than
  widening the first. Its key set is a subset of `keymap.ACTION_NAMES`
  and covers every action the resolve table answers, which is what keeps
  DL-080's no-fall-through guarantee over both tables (DL-205).
- The conflict table is a CSS grid: `.wizard-conflict-grid` carries
  `Resolve.dc.html:55`'s five tracks and both the header row and every
  body row are laid out on it, so a heading stands over its column.
  `ui.aggrid` is still not adopted, for the reason DL-079 gives for the
  review table: it claims the arrow keys Specs binds over this same
  table (DL-206).
- The detail rail carries one control per distinct answer, keyed on
  `conflict_model.candidate_reference`, and the strip above the table
  carries one bulk action per input collection, keyed on
  `conflict_model.reference_from_input`. A control names the record that
  wins rather than the collection it came from, so two collections
  holding identical values are one control naming both, and a bulk
  action leaves undecided any group its own collection holds no record
  in. The chosen answer is marked by a class string at the call site and
  a dot element rather than by a `::after`, because a guard can read a
  class and cannot read a pseudo-element (DL-207).
- Steps 1, 2 and 4 hold the content the reconstruct page composes: the
  three configuration cards and the conflict-policy control in step 1,
  the preview report in step 2, and the write card in step 4. Each holds
  its own cards, holders and callbacks; a step region is a container the
  page enters with a `with` statement, so the content keeps its own
  nesting (DL-208).
- Every guard this work adds is run against a named mutation and fails
  under it before it is kept, and its docstring carries both the
  mutation and the verbatim output pytest printed. A line pytest printed
  longer than the margin is cut with an ellipsis rather than rewrapped,
  so what stands is what pytest printed (DL-209).
- A milestone that composes no page takes no served-page record: the
  gate reads what a browser resolved, and a milestone emitting only
  decision-log prose and a guard over it has no surface for a browser
  to read. DL-084's pass condition is read as covering the milestones
  that build, and DL-190's post-strike record is owed by the milestone
  that strikes rather than by the one that documents. Nothing leaves
  "Composition not built" in this work, so DL-190's trigger does not
  fire (DL-210).
- A served-page record states the surfaces it did not read, and why,
  beside the ones it read. The run recording the resolve step could not
  walk the tab ring - `Tab` pressed with focus seated on a named
  control left `document.activeElement` where it was - so the record
  names the keyboard ring unread rather than reporting a ring assembled
  from DOM order, which would read as a walk that happened. A surface
  silently absent from a record reads as a surface not owed (DL-211).
- A record's readings are written above its "Structural verdicts"
  heading, because
  `tests/test_docs_browser_record_structure.py::_reading_digest` hashes
  the verdict rows above that heading: a record written
  structural-verdicts-first hashes the empty string, and every such
  record hashes alike (DL-212).
- The conflict grid's four fixed tracks are sized against the width the
  table resolves to on the built page, not against the width its
  artboard draws. `Resolve.dc.html`'s `main` spans the frame at a 24px
  inset while the built page centres its content at
  `.wizard-content-width`, so the same four fixed tracks leave the
  artboard's flexible track 264px and the built page's 54px, and
  `docs/2026-09-07-reconstruct-resolve-browser-record.md` read a track
  path crossing the two columns beside it. Each fixed track is sized to
  the widest value its column holds plus the cell inset; the artboard is
  retracked first and `theme.py` follows it (DL-071, DL-213).
- The conflict grid's track cell carries `overflow: hidden`,
  `text-overflow: ellipsis` and `white-space: nowrap`, which
  `Resolve.dc.html:62`'s `.trk` draws. A collection path offers no break
  opportunity, so a cell narrower than its path does not wrap: its text
  crosses the tracks beside it, which `min-width: 0` on the row's cells
  permits rather than prevents. The full path stands in the detail
  rail's head, which is what makes shortening it in the table readable
  rather than lossy (DL-214).
- A sentence naming a count reads that count off the model rather than
  spelling it. The rail's head says how many collections hold the
  focused file by counting the distinct inputs its candidates name
  between them; a spelled count is right for the group it was written
  against and wrong beside every row that disagrees with it, which is
  the screen misreporting the model rather than styling it badly
  (DL-215).
- Every documentation edit in this work describes the file as it
  stands, with no "previously", "now does", "no longer" or "added",
  and each documentation milestone carries the grep that proves it
  (DL-177).
- A run reports what it could not do cleanly and writes the rest; it
  does not refuse everything over the part it could not. A playlist entry
  whose track the collection holds more than once is placed on the first
  of those copies - the record the merge redirects that key to - and the
  run counts how many landed that way and in which playlists, which the
  write step prints as a row of its own. Refusing instead answered
  nothing an operator could act on: the duplicates are in their own
  collection, no control in this tool removes them, and one measured run
  refused 1187 playlists over 369 such entries. Dropping the entries
  silently would be worse again, since losing tracks from a playlist is
  the thing this tool exists to undo (DL-094, DL-122, DL-230).
- A comparison between two pieces of one XML document unescapes both
  sides first. The emitted-key self-check reads a LOCATION out of text
  carried through verbatim and a PRIMARYKEY out of a playlist the run
  re-serialised, and the two writers spell a character differently: a
  measured collection writes a tab in a file name as `&#x9;` and the
  serialiser writes the same tab as `&#09;`. Compared as written that is
  a key naming no entry, and the run refuses over a name every reader of
  the output resolves correctly. The check is worth keeping - it reads
  the artefact the operator gets - so it compares values (DL-231).
- A playlist entry naming a track no collection in the run holds is
  dropped from the playlist that carries it, counted, and reported; it
  does not refuse the output. The reference is already broken in the
  files the run reads - Traktor itself resolves it to nothing - so
  keeping it would carry a pointer to nothing into a repaired file, and
  refusing over it discards every playlist the run rebuilt. One measured
  pair of an operator's own collections refused a 684-playlist rebuild
  over 21 such entries naming 8 tracks. Three passes drop them, one per
  place a playlist reaches the output by: the reconstruction pre-pass
  filters its merged union, a base playlist the run leaves in place is
  patched to remove the whole ENTRY, and import_playlists does the same
  to an imported fragment. The count of entries and the count of
  distinct tracks are reported apart, because one missing track sitting
  in many playlists is many entries and one track, and the write step
  prints a row naming both and the playlists that lost one. The
  unresolved_reference check stays, reading what the run emits rather
  than what it read: a reference still standing after those three passes
  is this module's own defect, not the operator's collection (DL-230,
  DL-232).
- A name states what the thing does, not what a reader might hope it
  does. `conflict_model.resolve_where_answered` settles every undecided
  group its predicate answers a reference for and leaves the rest
  standing, which is what a bulk action for one collection needs: a
  group that collection holds no record in keeps no value of anyone
  else's. A name promising every group would describe a control that
  overwrites answers this one leaves alone, and a reader who trusted it
  would look for a bug where there is none (DL-154, DL-235).
- A sentence's noun agrees with the count it follows, read off that
  count. The resolve step's tally strip is
  conflict_model.resolve_tally_sentence, and a run whose collections
  diverge over one track reads "1 track carries more than one answer" -
  the ordinary case on a pair that barely diverge, and one a served page
  read as "1 tracks" while the refusal sentence one step earlier had the
  singular right. Two screens describing one number disagreeing about it
  is the screen misreporting the model rather than styling it badly,
  which is the rule DL-215 states for a spelled count (DL-215, DL-233).
- That rule is stated once, in `gui/wording.py`, and every screen reads
  its word from `plural`. Written out per sentence it was right wherever
  somebody remembered it and wrong everywhere else, which is how one
  served page came to read "1 tracks carry more than one answer" a step
  after a refusal that had the singular right. Both forms are given at
  the call site rather than derived from the singular: the forms this
  package needs are not all a trailing `s` - "track carries" against
  "tracks carry", "track is" against "tracks are" - and a helper
  appending a letter would be right for the nouns and wrong for exactly
  the sentences hardest to catch reading the code. Zero takes the
  plural, because a change-list row reading `0 playlist` reads as a typo
  rather than as a count. The module imports nothing, so it sits below
  every other `gui/` module in the import order, and
  `tests/test_gui_wording.py` sweeps `gui/` for a screen spelling the
  choice out for itself (DL-069, DL-215, DL-233, DL-236).
- A guard and the work it gates ask the same question in the same terms.
  The base-side drop pass reads a playlist's keys as they stand, which is
  what `drop_unresolvable_entries` reads of that same untouched element;
  redirecting them in the guard alone put the two in different key spaces
  and made the guard true in exactly the state where the dropper had
  something to do, which is the shape DL-189 names (DL-189, DL-237).
- A pass that removes an ENTRY reports every key that left with it. An
  ENTRY is removed whole, so a second `PRIMARYKEY` on it goes too, even
  where the collection holds that track; `DroppedEntries` carries the
  unresolvable keys and the resolvable ones apart, and `entries` counts
  elements rather than keys so a caller reporting entries and tracks
  reads each off the thing it names. A Traktor playlist entry names one
  track, so `entries_carried_away` is empty in an ordinary run - which is
  what makes a filled one worth reading, since losing a track the
  collection does hold is the thing this tool exists to undo (DL-232,
  DL-237).
- Bookkeeping over elements is keyed by byte offset, not by `id()`. Under
  lxml an element is a transient proxy, and once nothing references it
  the proxy is collected and its address can be reused by an unrelated
  one - the hazard `spans.py` documents and defends against by retaining
  every element it walks. The reconstruction pre-pass records the span
  start of each playlist it rebuilds and the drop pass skips those, so
  neither depends on another object staying alive to stay correct
  (DL-237).
- A row saying what a run added counts what it added. A rebuilt playlist
  that was not empty keeps its own entries and gains the rest, so its
  contents and the run's additions are two numbers, and
  `playlist_entries_added` is the second. Summing the contents credited
  the run with entries the operator already had - on one measured pair,
  17,311 against the 17,254 it put there - and paired that total with a
  row counting the playlists that had been empty, so two numbers on one
  card described different populations. `reconstructed_playlists` still
  carries the contents, which is what the preview's per-playlist rows
  name and label as entries held (DL-215, DL-238).
- A screen says what this run did and what to do next, and makes no
  promise about what another program will do afterwards. The write
  step's closing note told the operator their existing collection
  "stays where it is until you do" - reassurance the originals card two
  rows above had already given properly, by naming each collection and
  reading NOT MODIFIED beside it, and which read here as a warning that
  importing would move something. What Traktor does with a file it
  imports is Traktor's, and a sentence implying otherwise is this screen
  describing a program it cannot see.

  The same note offered a second route - point Traktor's "collection
  setting" at the file - which names nothing in the program: Traktor's
  directory preference is a root folder, not a path to one `.nml`. It
  was written here unverified and stood until an operator read it
  against Traktor. A screen naming another program's controls can only
  be checked in that program, so it says the one route that was
  confirmed there and nothing more (DL-239).
- The write step draws two states and is redrawn between them: before
  its write, and after. It does not become another screen once the write
  lands - the operator is looking at the card they just confirmed, and
  everything else on it is still true, the change list having described
  the file and now describing it, the originals still unmodified, and
  the note about opening it in Traktor being the next thing to do rather
  than a thing to do later. Only the tense and the status move, which is
  three strings `WriteReport` derives - `head_title`, `head_badge` and
  `contents_title` - plus a destination badge reading `Written`. A
  second screen for the state after a write would put the operator
  somewhere new at the moment they most need to recognise where they
  are; `Write.dc.html` draws no such screen and this composes against
  the design set's own card, label and badge rules instead (DL-071,
  DL-234, DL-240).
- `written` is not "a write happened" but "this run wrote the path this
  field now names". A path the operator edits after writing names a file
  this run did not write, and a run assembled after a write produced
  bytes the file on disk does not hold; either puts the step back before
  its write, which is where it truly is. It is also distinct from
  `destination_exists`: a path holding a file somebody else left there
  reads `Already exists`, which is the badge that warns the operator it
  will be replaced (DL-240).
- A confirmation states what it is about to destroy. `write_bytes_
  atomically` ends in `os.replace`, so the write replaces whatever
  stands at the output path and keeps no copy of it; the dialog's first
  line said "A new file is created at the path above" either way, and an
  operator read that over a file the run then replaced. On a path
  already holding a file the question names the replacement, the line
  says what it holds now is not recoverable, and the primary control
  reads `Replace file` rather than `Write collection`. The note under
  the path says it too, because the badge is a state and the note is
  what the write will do about it. A confirmation that misstates what it
  destroys is worse than none: it spends the operator's attention
  reassuring them. The dialog is filled where the panel is drawn and the
  footer control redraws before opening it, so what it states is what
  stands at that path now (DL-241).
- Each answer in the resolve step's detail rail reads as a complete
  record: every tracked attribute the group's records carry, the ones
  the answers agree on included, one field per line as field name,
  formatted value and raw value. An answer joined into one string of
  values cannot be told from its neighbour, and a rail showing only the
  divergent subset reads as a diff rather than as the record that wins,
  so the rail prints the record and the mark carries the difference
  (DL-242).
- The divergence mark stands on a field exactly where its name is in
  the row's attrs. splice computes attrs as the tracked attributes
  whose values differ across the group's members, which is precisely
  the set of fields that differ across the answers, already computed
  and already carried to the page; the rule is a membership test in a
  nicegui-free module, so no second divergence computation exists to
  disagree with the first (DL-243).
- The agreeing values ride alongside attrs as their own field on
  ConflictRow, ConflictGroup and ConflictRowView, and attrs names the
  divergent set alone. attrs is one of the three columns the conflict
  CSV writes and the line splice_cmd prints
  (traktor_nml/commands/splice_cmd.py:22, :24), so widening it in place
  would rewrite recorded output for every run; the complete record is
  carried as an addition and the CSV columns are guarded unmoved
  (DL-244).
- Every member of a group agrees on every attribute outside attrs, so
  one group-wide mapping of agreeing attribute to value is well defined
  and is computed beside the candidates. divergent_attrs at
  splice.py:340-341 names the attributes whose value set across the group's
  members has more than one member, so an attribute outside it holds
  one value across every member, candidates included: the agreeing
  values belong to the group rather than to a candidate, and a guard
  reads that off a three-answer group rather than asserting it
  (DL-245).
- Formatting and field assembly live in
  `traktor_nml/gui/answer_detail.py`, a module importing no nicegui.
  DL-069 puts every rule the suite reaches below the nicegui boundary,
  and conflict_model.py is the vocabulary a pick is recorded in, so a
  display formatting rule there would give that module a second purpose
  the package's one-purpose-per-module table does not carry; the field
  rows, their labels, their formatted values and the mark stand in one
  module app.py reads from (DL-069, DL-246).
- FILESIZE renders as megabytes by dividing by 1024 once,
  PLAYTIME_FLOAT as minutes and seconds, and BITRATE as kilobits per
  second by dividing by 1000, with the raw string standing beside every
  formatted value in mono. Traktor writes FILESIZE in kilobytes - the
  calibration comment at traktor_nml/matching.py:124-128 records the
  measured error of FILESIZE against bytes/1024, and _size_kb
  (traktor_nml/matching.py:166-180) deliberately does no conversion
  because both sides already carry kilobytes - and BITRATE in bits per
  second. A formatting dividing a kilobyte count twice prints a number
  the collection does not hold, and the raw value stays visible because
  it is what the written file carries (DL-247).
- A value that is empty or does not parse as a number prints as itself
  with no formatted companion. traktor_nml/model.py:217-219 yields an
  empty string for every INFO-borne attribute where a record carries no
  INFO element, and a formatter dividing that string raises inside a
  page build, so each formatter returns the raw string unchanged where
  the value does not parse and a guard covers the empty string
  (DL-248).
- No colour ranks one value against another. The tool has no way to
  know that a larger filesize or a higher bitrate is the better record,
  so a green value would state a judgement the model cannot support:
  difference is marked and never ranked (DL-249).
- The rail head is the one place the file is named, and
  design/reconnect-wizard/Resolve.dc.html carries no "The file" group.
  The head prints the identity key in mono and the artboard's body
  opened with a labelled Path row holding the same string, which prints
  the file twice in a 400px rail; the artboard is amended first and the
  screen is built to it (DL-071, DL-250).
- The gate fixture's conflicting entry carries bits-per-second bitrates
  and a second divergent field agreeing between two of its three
  answers. A fixture diverging on bitrate alone, at values a Traktor
  collection never writes, exercises neither the unit formatting nor a
  mark that discriminates between answers, so the fixture carries a
  field that agrees and a field that differs and the record reads both
  (DL-251).
- A guard proves the page calls the field assembly rather than only
  that the assembly is correct. This repository has shipped guards
  green in exactly the broken state (DL-189), and a formatter guarded
  alone passes while the rail joins raw values into one label: the
  composition guard reads app.py's answer() for the per-field
  construction, and the served-page record reads the rendered rail
  (DL-189, DL-252).
- Every record the resolve rail answers over is Traktor-borne: splice
  builds its groups from records_by_input, the per-input lists of
  collection_records, and hands them to group_identities
  (traktor_nml/splice.py:475, :482), and diskscan feeds matching and
  reconnect_run instead
  (traktor_nml/reconnect_run.py:23,
  traktor_nml/commands/discover_tracks_cmd.py:12). The kilobits BITRATE
  traktor_nml/diskscan.py:59 writes has no path into a ConflictRow, so
  the rail formats one provenance and the bits-per-second division
  needs no provenance condition (DL-253).
- The rail prints each field name as Traktor writes the attribute in
  the NML - ARTIST, TITLE, ALBUM, FILESIZE, PLAYTIME_FLOAT, BITRATE -
  as one fixed mapping from the splice._TRACKED_ATTRS identifier to the
  printed label. _TRACKED_ATTRS holds lowercase python identifiers
  while the artboard draws the key in mono uppercase, and left to the
  call site the same field could print as PLAYTIME_FLOAT, PLAYTIME or
  LENGTH on different rows; the label is the XML attribute name the
  written file carries, uppercased, so the printed key names the thing
  the raw value beside it came from (DL-254).
- The numeric presentation is the approved mockup read literally:
  FILESIZE to one decimal followed by MB, BITRATE rounded to a whole
  number followed by kbps, PLAYTIME_FLOAT as minutes then a colon then
  seconds truncated toward zero and zero-padded to two digits. No
  thousands separator is introduced anywhere and the raw string is
  reproduced exactly as the collection carries it: a grouped copy of
  the same digits beside the ungrouped ones reads as a third value, and
  the raw value is what the written file holds (DL-255).
- This work writes into `C:\codex\traktor-nml-tool-gate`, a tree
  outside the primary working directory, for the three
  reconstruct-conflict fixture collections alone. The gate tree is
  where the served page is produced, and the served-page record DL-084
  and DL-169 require cannot read the unit formatting or a
  discriminating mark without editing that fixture; no other file
  outside the working directory is touched (DL-084, DL-169, DL-256).
- The rail head and the field grid go through
  `traktor_nml/gui/wording.plural` for every word a count picks, and no
  inline conditional on a count stands anywhere under gui/. The head's
  holding-count sentence reads `collection holds` at one and
  `collections hold` otherwise; an inline `x if n == 1 else y` is the
  shape tests/test_gui_wording.py forbids outside wording.py, and a
  count written into a sentence is what DL-215 forbids (DL-215,
  DL-257).
- `traktor_nml/gui/app.py` is read and rewritten with newline set to
  the empty string so its CRLF line endings survive the edit, while
  answer_detail.py, theme.py and every file under tests/ stay LF. app.py
  is the one file in the package carrying CRLF throughout, and a
  default-mode write converts every line ending and shows the whole file
  as changed, hiding the real edit; a guard reads the file bytes for an
  absence of a bare LF (DL-258).
- No work here regenerates tests/baselines/manifest.json or
  fixture/w002gatefix2, restores a file with git checkout, writes into
  build/ or dist/, installs into the system interpreter or spawns a
  background agent, and the suite runs under
  `C:\Users\marcu\AppData\Local\Python\pythoncore-3.14-64\python.exe`.
  M-002 changes a structure the conflict CSV and splice_cmd report
  over, which is exactly the change a baseline regeneration would paper
  over: a regenerated manifest would record the new output as expected
  and the guard that the columns are unmoved would pass in the broken
  state (DL-189, DL-259).
- A playlist is identified by the folder path it sits at, which is what
  Traktor's own SORTING_INFO PATH names it by, and the reconstruction
  pairs base to source on that path. A bare NAME does not identify a
  playlist: a real collection reuses one freely across folders, and the
  collection this was measured against holds 1187 playlists under 768
  distinct names and 1187 distinct paths, so 303 of its names are held by
  two or more playlists that are not the same playlist. Keying by name
  called each of those ambiguous and refused the entire run - a repair
  refused over a name two unrelated playlists happen to share. A path
  held twice inside one collection is still refused, which is the
  collision the name check was reaching for and is rare where a name
  collision is not (DL-098, DL-228).
- A playlist with no counterpart at its own path pairs on its name where
  that name names exactly one playlist on each side, so a playlist moved
  between folders is still rebuilt from its own copy. Where the name is
  held more than once, nothing says which playlist the copy belongs to
  and it is left alone rather than rebuilt from a guess (DL-228).
- A refusal names how many reasons the run gave and the control that
  walks to the step listing them, rather than reciting one machine token
  and leaving the rest unmentioned. The tokens stay on the refusal and
  the preview step prints them, because a token is what the CLI prints
  and what a bug report carries; what a toast carries is what the
  operator does next. A sentence naming a place the operator cannot see
  from where they are standing is a sentence they cannot act on
  (DL-226, DL-229).
- A step that reports a run is reached only on a run that produced one.
  A run that refused is a held result carrying no output, and treating
  "a result is held" as "a run assembled" stood the write step there
  reporting zeros for the playlists filled and for the tracks the file
  holds, beside a count of chosen answers read off the decisions rather
  than off any run - one screen describing a file that was never
  assembled, from two sources at once. `reachable` takes whether the run
  produced an output as an input of its own, and
  `conflict_model.run_assembled` decides it, so the view never tests
  `result.output is None` itself (DL-111, DL-224).
- A held run reports the answers it was handed, and the walk into the
  write step re-assembles where those are not the answers now given. The
  operator settles the conflicts at step 3 and the run that reported
  them refused before any of them were settled; without the re-run their
  answers reach a run only if they know to preview a second time.
  `conflict_model.run_is_current` compares the resolutions mapping the
  run was handed with the one now held, so a decision made and undone
  back to where it started leaves the run current and buys no second
  read of the collections (DL-225).
- The state a step reaches when its run refuses is composed, not
  printed. The reconstruct page's preview refuses whenever the
  collections diverge, which is the first thing most runs see, and it
  read as two labels drawn onto an empty page. It is a card whose head
  names the stop, whose sentence names the count the run reported and
  the step that answers it, and which lists the run's own error tokens
  where the stop was something other than a conflict - the tokens
  themselves, because a token is what the CLI prints and what a bug
  report carries (DL-226).
- The gate reads what a browser resolved, and a fixture walk is a walk
  someone chose. Two of this work's defects were found by an operator on
  their own collection and not by the gate, because the gate's own walk
  previewed a second time before continuing and never reached the write
  step on a stale run. A record states the walk it took, so a walk the
  gate does not take is visible as one it did not take rather than as
  one that passed (DL-084, DL-227).
- A collection the set-up step is given is reported rather than only
  named: how many tracks it holds, how many playlists, how many of those
  hold nothing, and for a source how many it could supply contents from.
  Those counts are what make the choice checkable before any run - a
  source with no filled playlist supplies nothing, and a base with no
  empty playlist has nothing to repair - and they are derived in
  `collection_summary.py` from the parsed file. A file that will not
  parse is refused at the step that took it rather than at Preview. What
  a run reports is `reconstruct_report.py`'s and stays separate: a count
  describing the file at the moment it was chosen and a count the run
  produced are different claims (DL-220).
- A step's own account of what follows it names the steps by
  `reconstruct_steps.STEPS`' numbers. The set-up step lists the three
  after it, and a list numbering them itself would be a second table for
  the rail to disagree with (DL-221).
- The output path is read against the collections the run reads by
  `conflict_model.output_refusal`, and the set-up step's line about the
  output and the write's own refusal both call it. A page describing a
  path as a new file over a write that would refuse it is the screen and
  the rule disagreeing about the same path. A path not yet chosen is not
  a path that collides, and the line says what is missing rather than
  describing a file the page has not been given (DL-222).
- A grid track holding text that does not wrap is written
  `minmax(0, 1fr)` rather than `1fr`, and the box the grid stands in
  takes its column's width rather than its own content's. A bare `1fr`
  takes an automatic minimum of its content, so the set-up step's
  collection paths widened the track to 879px inside a 1024px column and
  the page scrolled sideways; a grid inside a framework column that packs
  its items to the start sizes to its content, so the same split then sat
  62px narrower than its column with its rail off the column's edge; and
  a row inside the source list did the same at 727px inside a 604px card.
  Each rule was right read alone (DL-071, DL-189, DL-223).
- The preview and write steps stand a content column beside a 400px
  rail, and that width is `DETAIL_RAIL_WIDTH`, the value the resolve
  step's own split reads. `Preview.dc.html:27`, `Write.dc.html:27` and
  `Resolve.dc.html:53` draw one rail width between them; where the
  artboards disagreed - Write drew 404px - the artboard is brought to
  the measurement first and `theme.py` follows it. The columns are
  top-aligned rather than stretched, because the two hold different
  amounts and a card stretched to its neighbour's height draws a band of
  empty ground under its last row (DL-071, DL-216).
- A listing that shows some of its rows and sums the rest divides the
  list once, in `reconstruct_report.py`, rather than slicing in the
  render and counting again for the summary row. `Preview.dc.html`
  draws nine named playlists and a tenth standing for the others, and a
  count in that tenth row that disagrees with the rows above it is the
  screen contradicting itself over a division it made twice (DL-217).
- A card is laid out at the content width by carrying
  `wizard-content-width` or by standing inside a box that does, and the
  guard reads the containers it stands in rather than its own class
  string alone. The preview and write steps compose their cards inside a
  two-column split, and a card there carrying the width class as well
  would be a second width declared inside the first. The split's own
  panel is held at the content width by its own guard, so the pair
  covers what one class string cannot (DL-218).
- A step that reports the run is redrawn on entry to it, and every
  sentence it prints is derived from the run and the answers given to
  it. The preview's note names how many tracks are still held more than
  one way with no answer, which is `resolve_gate(...).outstanding` - the
  value the resolve step's own footer prints - so the two cannot
  disagree; a note derived once at preview time stood over a resolve
  step where every group had since been answered and said each one had
  still to be decided. A footer sentence naming a control names the
  control that stands beside it (DL-204, DL-215, DL-219).
- Specs' Focus ring, Accessibility rules and Announcements are applied
  through a three-rung ladder - Quasar's own CSS variables and
  constructor arguments first, an `add_head_html` rule at higher
  specificity where Quasar's styling wins, and a recorded framework
  shortfall under DL-087 where neither reaches - rather than assumed
  to drop in. Quasar's `q-btn` sets its own min-height and paints
  focus through a `.q-focus-helper` overlay, so Specs' 32px control
  height and its 2px outline at 2px offset are the concrete collisions
  this ladder resolves (DL-086).
- A Specs rule the running framework refuses is recorded under the
  "Framework shortfalls" heading below, never as a
  Specs-versus-section-4 disagreement under DL-072; that heading
  carries the recording form, the measured set barred from that route,
  and DL-072's standing precedence (DL-087).
- Where a rule Specs states in prose and a value the artboards render
  disagree, the prose rule governs and `theme.py` carries it; the
  divergence is recorded under the "Design-set divergences" heading
  below, which carries that rule, the divergences recorded so far, and
  how a browser record reads them (DL-088).
- Specs.dc.html's "Keyboard" section names `/` Jump to search under
  the Review table; Phase 1 has no search box for it to focus, so
  `keymap.ENTRIES` carries no entry for `/` and `keymap.py`'s module
  docstring states the omission by name rather than claiming one entry
  per named key. `tests/test_gui_keymap.py`'s
  `test_jump_to_search_has_no_entry` pins the omission executably
  (DL-089). (`keymap.py`'s ENTRIES comment carries the same
  cross-reference.)
- Specs' focus ring reaches a `q-btn` only from inside the layer
  Quasar names `quasar_importants`, so `page_stylesheet()` keeps its
  unlayered `*:focus-visible` rule for every other focusable element
  and re-opens that layer for `.q-btn:focus-visible`. Quasar gives
  every `q-btn` the `no-outline` class, whose `outline: 0 !important`
  is declared in that layer, and the page orders it last; for an
  `!important` declaration the earlier layer wins, so an unlayered
  rule loses at every specificity and so does one in a layer declared
  after it. Both were measured on the served page, with the layered
  form the only `add_head_html` shape that paints the ring, so this is
  where DL-086's rung two lands for the ring rather than a DL-087
  shortfall (DL-090).
- `splice --reconstruct-playlists` decides whether to rebuild a base
  playlist by comparing its redirected `PRIMARYKEY` sequence against the
  same-named incoming side's own ordered union, not by comparing entry
  counts and not against the merged result. Counts cannot separate
  `[one, two]` from `[two, three]`, and the merged sequence puts base's
  keys first, so it cannot differ from base whenever both sides hold the
  same tracks - an ordering difference would be unreachable through
  either. Comparing against the incoming union reaches both (DL-091).
- Every incoming playlist carrying the matched name is folded in, across
  every `--input` file, in the order the inputs are given. A first-match
  rule would silently drop the rest, and the operator naming several
  inputs is asking for all of them; folding in input order makes the
  result a function of the command line rather than of document order
  (DL-092).
- A name that matched a base playlist is excluded from playlist import
  whether or not it needed rebuilding, so no `"<name> (2)"` copy
  accompanies it. A duplicate beside a reconstructed list holds a subset
  of what base already carries, and a duplicate beside an identical list
  holds exactly what base already carries; neither is content the
  operator asked to add (DL-093).
- An incoming `PRIMARYKEY` whose identity group holds more than one base
  record is placed on the record the merge redirects that key to, and the
  run counts it. No single base key is the right redirect target, so the
  entry is placed on the one the collection merge already uses for the
  same key rather than on a second guess of its own.
  `_resolve_conflicts` returns those keys as a named element of its
  result rather than raising, and the reconstruction reads them to count
  what it placed (DL-094, DL-100, DL-230).
- Reconstruction is opt-in behind `--reconstruct-playlists`, and the
  `"<name> (2)"` rename stays the default. Reconstruction changes the
  shape of an existing caller's output rather than adding to it, so
  defaulting it on would rewrite results for invocations that never
  asked for it (DL-095).
- The base source text is rewritten in memory and re-parsed before any
  span is consumed, keeping reconstruction on the byte-span assembly path
  DL-007 separates from attribute patching. Replacements are applied
  end-first so each span offset stays valid against the text it was
  measured in, and every byte outside a rebuilt `PLAYLIST` element and
  outside the attribute values a source pick names inside a base
  `ENTRY` is copied verbatim (DL-096, DL-102).
- Playlist path matching is exact and case-sensitive. Traktor treats two
  playlists whose paths differ only in case as distinct, so a casefolded
  lookup would rebuild one from the other and leave the same track
  reachable through both (DL-098, DL-228).
- A folder path occurring more than once within one document, on either
  side, aborts with nothing written rather than resolving by document
  order. Counting is per contribution rather than across them: one path
  appearing in several `--input` files is the fold DL-092 asks for, while
  the same path twice inside one file offers no single playlist to
  reconstruct or to reconstruct from (DL-098, DL-228).
- The `SORTING_INFO` entry belonging to a skipped incoming playlist is
  discarded, since base's own entry already governs the surviving node
  and a second entry for one name would describe a playlist the output
  does not contain (DL-099).
- A `PRIMARYKEY` with no `old_to_new_key` mapping passes through
  redirection as its own raw value. Absent from the map means no other
  input claimed that identity, so the key already is the only name for
  it - not that it is unknown (DL-101).
- Reconstruction deduplicates on the redirected key while `build-playlist`
  keeps duplicates under DL-037. The two differ in what a repetition is:
  a repeated track-list line is the operator's own authored input, and a
  track reached twice while folding two documents together is an artefact
  of the fold, which no operator wrote (DL-103).
- The renamed-playlist count is taken per surviving output fragment
  rather than from the import result's own rename map, which also counts
  a rename applied to a playlist that is then skipped as matched - a
  rename the output does not contain and the operator cannot see (DL-097).

- Per-key conflict resolutions reach the core as a named `resolutions`
  mapping on `_resolve_conflicts` and `assemble_output`, keyed by the
  identity-group key and valued `base` or `source`; the run-wide
  `on_conflict` parameter keeps its meaning and applies only where no
  per-key entry names that group. `_resolve_conflicts` already computes
  one `ConflictRow` per divergent group and already carries the identity
  key naming it, so the mapping needs no second grouping pass and no
  second identity notion, only a lookup where the abort is raised. It is
  a named keyword parameter and the widened return is a named element
  rather than an appended positional, with every caller enumerated
  first - `assemble_output`, `commands/splice_cmd.py`'s `_handle_splice`,
  the direct uses in `tests/test_splice.py` and the GUI call in
  `gui/app.py` - on DL-100's precedent (DL-104).
- A group carrying divergent attributes with neither a per-key resolution
  nor a run-wide `on_conflict` keeps DL-008's abort exactly: `output` is
  `None`, `errors` carries `unresolved_conflicts`, `conflict_rows` is
  populated and nothing is written. The abort exists because
  `_resolve_conflicts` picks one winner per group, so settling a
  divergence arbitrarily writes a plausible but wrong collection; a
  per-key mapping supplies a winner the operator named, which is what
  makes writing safe. Resolution is additive, so a run with an empty
  mapping is byte-identical to one made without the parameter (DL-105).
- The conflict decision state and the row derivation live in
  `gui/conflict_model.py`, a nicegui-free module, mirroring
  `review_model.py` and `wizard_state.py`'s split of what the tool found
  from what the operator said. DL-069 puts every rule worth testing below
  the nicegui boundary because the suite's system interpreter has no
  nicegui, so resolution logic in `app.py` would be unreachable from the
  suite and would fail `tests/test_gui_view_boundary.py`'s AST walk.
  `conflict_model.py` holds `ConflictDecisions` (per identity key:
  `UNDECIDED`, or a candidate reference naming one of the answers the
  group offers), the row projection over a `ConflictRow` plus its
  decision, the bulk application of one collection's answers and the
  outstanding count, and imports no nicegui (DL-106).
- Per-track picks are held in session state keyed by the identity key,
  surviving a re-preview after an output path change or a further source
  and discarded with the process. The identity key is what
  `_resolve_conflicts` groups on and what `ConflictRow` carries, so it is
  stable across two runs over the same inputs and lets a re-preview
  re-attach a decision without a second identifier or a sidecar file;
  `ConflictDecisions` sits beside the other holders on the `/` page, the way `state.decisions` holds the reconnect flow's picks
  (DL-107).
- The splice CLI carries only the run-wide `--on-conflict
  keep-first|keep-last` flag, and the per-key `resolutions` parameter has
  the GUI as its sole caller. A per-key mapping on a command line needs a
  file format, a parser and a report of keys matching nothing, and that
  surface serves no operator the tool has: the operator resolving
  track-by-track is the one looking at rendered rows. `splice_cmd.py`
  passes no resolutions and the core's default of an empty mapping keeps
  the CLI path identical (DL-108).
- The conflict-resolution screen is drawn into
  `design/reconnect-wizard/Specs.dc.html` before it is built, and built to
  what Specs says. DL-071 makes Specs the cross-screen contract for what
  the operator sees and a screen disagreeing with Specs is fixed in
  Specs, so a screen Specs never described would either carve an
  exception to that rule or be reconciled after the fact against a
  contract written to match the code (DL-109).
- The conflict table renders hand-rolled `ui.row` rows per conflicting
  track, one row showing one control per answer the track offers,
  alongside a run-wide bulk strip of one action per collection the run
  reads.
  DL-079 rejected `ui.aggrid` for the review table because aggrid claims
  the arrow keys Specs binds over that same table, and the conflict table
  sits in the same wizard surface under the same keyboard contract, so
  aggrid here would reintroduce that collision; a conflict set of
  hundreds of rows is made tractable by the bulk actions rather than by a
  grid widget (DL-110).
- The write control refuses on a reason the model returns, and the
  reason is read off the held run's errors rather than off `output`
  alone. `output` is `None` exactly when `errors` is non-empty, which is
  `SpliceResult`'s invariant, so `output` alone cannot tell an absent run
  from a run that aborted, nor a conflict abort from any of the other
  aborts `assemble_output` reports. `conflict_model.py` reads an absent
  result as `no_preview`, errors carrying its own
  `CONFLICT_ABORT_TOKEN` as `conflicts_outstanding` with the count of
  rows still undecided, and every other abort as `run_refused` carrying
  the run's own error strings, whose sentence names the first of them
  and points at the report the page draws above the controls; the
  control renders whichever sentence comes back (DL-111).
- The conflict rows the run produced are rendered on the abort path in
  place of the bare token, and the run-wide choice is offered on the
  page, as the first landing increment before per-row picks exist.
  `conflict_rows` are already computed and already returned on the abort
  path and the page discarded them at the render, so rendering what is
  already returned and passing the CLI's existing `on_conflict` through
  the page's own control needs no core change; those two land first
  inside the page milestone, so an operator can complete a reconstruction
  before the per-key mapping and the per-row picks arrive (DL-112).
- The page milestone is accepted by a served-page gate run from the gate
  repository exercising a conflicting collection pair end to end -
  preview, then per-row picks, then a bulk action, then a write. DL-084
  records that `gui/` defects are found only by serving the page, since
  the suite's system interpreter has no nicegui and `app.py` is guarded
  by AST walk rather than by rendered DOM, so a conflict table whose rows
  and picks are never rendered would pass every guard this work adds
  while being unusable; the gate run is an acceptance criterion of the
  page milestone rather than an optional follow-up (DL-113).
- `ConflictRow` carries a content-derived identity key - the group's sole
  base-input record's primary key, or the sorted tuple of the group's
  member primary keys where the group holds no base record - rather than
  the union-find root index it carries as a group label.
  `group_identities` keys its groups on `find(i)`, an index into the flat
  record list built as base's records followed by each contribution's in
  order, and that root index is positional: a further source collection
  lengthens the list, shifts every later index and can move a group's
  root, so one track's group is labelled differently between two previews
  and a decision keyed on the old label attaches to a different group or
  to none. The derivation is total, since every conflicting group holds
  at least two records spanning at least two inputs, so both branches
  always yield a value (DL-114).
- A held decision survives a re-preview only when its content-derived key
  names a group whose member primary keys are the identical set *and*
  whose candidates are the identical tuple; a group whose membership
  differs, a group whose answers differ, and a key naming no group at
  all, return the row to undecided and count toward outstanding.
  `record_keys` cascades through every tier and `group_identities` unions
  across them, so a further source can merge two separate groups into
  one, pull a record into a group it was not in, or add an answer to a
  group whose member primary keys do not move at all, and the operator's
  pick was made against one specific set of answers and says nothing
  about a different one. Both sets are compared for exact equality and
  only an exact match on both re-attaches, so a re-preview after a
  further source refuses the write and shows the row again rather than
  writing a stale pick (DL-115).
- A source pick on a group holding a base record keeps base's own `ENTRY`
  as the collection's entry for that track and rewrites that entry's
  divergent attribute values to the winning non-base record's; no non-base
  `ENTRY` span joins the collection for such a group. The primary key is
  derived from the location, so two entries for one file carry the same
  key and a playlist `PRIMARYKEY` cannot name one of them (DL-004), and
  transplanting the source's `ENTRY` beside base's therefore makes every
  playlist reference to that track ambiguous - the served gate run over
  such a transplant wrote four COLLECTION entries where base held three,
  two of them at one `LOCATION`. The winner for a group with a base record
  is always base's record and the operator's pick of another
  collection's answer is carried by substituting attribute values inside
  base's own `ENTRY` span, so the
  collection keeps one entry per track and the values the operator read
  are the values written (DL-116).
- The keep-first/keep-last picker over non-base candidates selects the
  entry to transplant only where the group holds no base record: the
  branch condition is `base_member is None` alone. The picker answers
  which of several non-base copies survives, a question arising only
  where nothing base-side already occupies the collection slot, so
  routing a pick on a group base already owns through it would conflate
  two questions and make the transplant - correct for a base-less group -
  an addition for a group base already owns. The base-less branch keeps
  the transplant and falls back to the picker for the groups no
  resolution names; the branch for a group holding a base record names
  which non-base record supplies the attribute values patched into
  base's entry, and reaches the picker not at all (DL-117).
- A pick patches exactly the attributes the group's divergence was
  measured over - the divergent subset of `_TRACKED_ATTRS` - and no
  others. `divergent_attrs` is the tracked attributes whose value set
  across the group's members holds more than one element, so a tracked
  attribute absent from it holds one value across every member including
  base: patching it would substitute base's value for base's own, and
  where that shared value is the empty string it inserts nothing, since
  DL-119's rule is that an empty winning value never creates a carrier -
  so patching
  the divergent subset and patching all six produce identical output
  bytes. The divergent subset is chosen because it is what the conflict
  row showed the operator and what the pick was made about, and because
  it touches the fewest bytes of a file whose byte fidelity is the
  module's contract (DL-118).
- A divergent attribute whose winning value is non-empty is carried into
  base's entry whatever base holds: substituted where the carrier tag
  already holds the attribute, written into the carrier tag where that
  tag exists without it, and where the carrier element is absent, an
  `ALBUM` or `INFO` child carrying only that attribute is written into
  base's `ENTRY`. A divergent attribute whose winning value is empty is
  substituted where base's carrier tag holds the attribute and is
  otherwise a no-op: no attribute is removed, no element is removed and
  an empty value never causes a carrier to be created. The six tracked
  attributes sit on three tags - `ARTIST` and `TITLE` on the `ENTRY`
  opening tag, `FILESIZE`, `PLAYTIME_FLOAT` and `BITRATE` on its `INFO`
  child, album on its `ALBUM` child's `TITLE` - and `collection_records`
  reads an absent `INFO` or `ALBUM` as the empty string, so an attribute
  base lacks and the source carries is by definition divergent and by
  definition on the row the operator read; honouring only the attributes
  whose carrier base happens to hold would drop part of a row the
  operator settled. The empty direction is settled the other way because
  a carrier holds attributes this pick says nothing about - an `INFO`
  also carries `KEY`, `PLAYTIME`, `IMPORT_DATE` and `RANKING`, an `ALBUM`
  also carries `TRACK` - so removing the element to express an empty
  value would discard data no operator chose to discard, while
  substituting the empty string expresses exactly the value picked
  (DL-119).
- The `ENTRY`-span rewrite is a pure function in `textpatch.py`
  (`patch_entry_attributes`) taking one `ENTRY`'s span text and the
  attribute changes and returning the rewritten span text;
  `apply_text_patches` keeps its `LOCATION`/`PRIMARYKEY` tag set and its
  locator-based whole-document scan. `apply_text_patches` locates a patch
  by matching a locator against attributes anywhere in the document and
  has no notion of element extent, so an `ENTRY` patch expressed through
  it would need `ENTRY`, `INFO` and `ALBUM` in its tag set and would
  still be unable to tell one entry's `INFO` from another's, while a
  group's base entry is already addressable as a span, since splice holds
  a `SpanIndex` over `base_source` and already asks it for entry spans.
  The span text as the unit bounds every substitution and every insertion
  to the one entry by construction and leaves `apply_text_patches`'
  contract and its callers untouched (DL-120).
- Entry patches and playlist reconstruction replacements share one
  replacement list declared before the reconstruction block and applied
  after it by `_apply_replacements`, followed by one re-parse of
  `base_root` guarded on that combined list being non-empty; on the
  `duplicate_playlist_name` and `ambiguous_redirect` abort paths the
  function returns before the apply, so the entry patches are discarded
  with everything else and no rewritten `base_source` reaches an output.
  `_apply_replacements` makes one forward pass in ascending offset order,
  collecting the untouched runs of the original text and the fragments
  into a list and joining once, so the document is built a single time
  rather than rebuilt per replacement - a bulk action over several
  hundred conflicting tracks would otherwise copy a multi-megabyte
  collection once per entry. Every span offset in play is measured
  against the original `base_source` by `span_indexes[0]`, and a pass
  that never mutates the text mid-loop reads exactly that text, so no
  offset is ever applied to bytes an earlier fragment has shifted and the
  list's own order carries no meaning beyond the sort. The spans it is
  handed are disjoint - a COLLECTION entry span and a PLAYLISTS
  `PLAYLIST` span cannot overlap - and the pass enforces that rather than
  assuming it, raising on a span that starts before its predecessor's end
  and naming both offsets, because a forward join would otherwise slice
  backwards, drop the bytes the two spans straddle and emit a silently
  garbled document. The list is shared rather than split in two because
  the reconstruction block declares its own list inside itself and after
  two early returns, where entry patches - which must apply with
  reconstruct unset - cannot live. The two aborts return `output` `None`
  with `errors` populated, which is the whole of `SpliceResult`'s shape
  for a refusal, so discarding the patches with the run costs nothing,
  while applying them before an abort would build a rewritten
  `base_source` no return path can carry; the re-parse is guarded on the
  combined list rather than the reconstruction list alone because the
  COLLECTION `ENTRIES` count is read from `base_root` downstream, and
  `span_indexes[0]` is stale from the apply onward, so no base-side span
  lookup occurs after it (DL-121).
- A pick on a group holding more than one base record patches the
  first base record's entry only, and the group's non-base primary keys
  stay in `ambiguous_keys`. Such a group has no single right redirect
  target, which is what `ambiguous_keys` records and what the
  reconstruction path treats as fatal (DL-094, DL-100), and patching
  every base entry in the group would write the source's values over
  several distinct base tracks on the strength of one pick. The patched
  entry is the same `base_members[0]` the winner branch selects, so the
  merge path's behaviour for such a group differs only in the values on
  that one entry, and the reconstruction places its playlist entries on
  that same record (DL-122, DL-230).
- The splice module docstring's scope note states that base's `ENTRY`
  spans are rewritten only for the attributes an operator's source pick
  names, rather than that base's bytes are never rewritten. The note was
  written as a v1 tradeoff record while the reconstruction work rewrites
  `base_source` in memory for playlist nodes, so the absolute form reads
  as an invariant the code does not hold, and a note claiming an
  invariant the code does not hold is worse than no note: a later reader
  takes it as the rule and either works around it or breaks it
  unknowingly. The note carries what is true - base's COLLECTION keeps
  its own entries, in their own positions, with their own identities, the
  only bytes of them a run rewrites are the attribute values an operator
  named, and the base input file on disk is untouched (DL-123).
- `stats`' `collection_entries_added` counts only entries the run puts
  into the COLLECTION, so a source pick on a group base already owns
  contributes nothing to it. The count is derived from `new_entry_texts`,
  itself derived from the `new_entries` records, and a source pick with a
  base record present contributes no record there, so the count follows
  the change without being recomputed; it reads as the number of `ENTRY`
  elements the output holds beyond base's own, which is what a caller
  reporting a merge means by it, and a guard pins that a source pick
  leaves it at the value a base pick leaves it at (DL-124).
- `gui/conflict_model.py` and `gui/app.py` carry no change for this work.
  `conflict_model`'s resolutions mapping is from identity key to the
  tokens `base` and `source` and `app.py`'s preview passes it straight
  into `assemble_output` as `resolutions`, so the vocabulary, the mapping
  shape and the call site are all untouched by what splice does with the
  token `source`; both stand as they are, established by reading the
  resolutions producer and its sole call site rather than assumed, and
  the `/` page's SOURCE control's wording stands because the
  behaviour is the wording (DL-125).
- The served-page gate for this work runs from the gate repository over
  the reconstruct-conflict fixture, extended with a track whose base
  entry carries no `ALBUM` child, and reads the written output back to
  count COLLECTION entries and `LOCATION` values. DL-084 records that
  serving is the only gate that has ever caught a defect in `gui/`, and
  the duplicate-entry defect survived a green suite and was found by a
  served run; a guard asserting the source's value appears in the output
  is exactly the guard that passed while the output held two entries for
  one file, so the acceptance evidence is the written file's entry count
  and its `LOCATION` set rather than a substring. The gate run writes the
  output with a SOURCE pick on every conflicting group, re-reads it, and
  passes only when the COLLECTION holds as many entries as base held and
  no `LOCATION` appears twice (DL-126).
- The reconstruct page answers `/` and the reconnect wizard answers
  `/reconnect`. Reconstruction is the leftmost tab and the route the app
  opens on, and a default selected tab is not a rendering state but the
  route `/` resolves to, because a tab is a link the browser follows. The
  two `@ui.page` registrations in `gui/app.py` carry the assignment -
  `_build_reconstruct_page`'s at `/` and `build_wizard`'s at
  `/reconnect` - and every other place naming a route is found by
  re-running the enumeration command below rather than by recall, since
  three of the places that named the earlier arrangement sat in a
  comment, a test docstring and markdown prose where no AST guard can see
  them (DL-129).
- `/reconnect` is a path nothing else answers, and the enumeration of
  route owners is what establishes that rather than an assumption. The
  owners of paths in this app are the `@ui.page` registrations in the
  package and the routes nicegui mounts for itself: a grep for `ui.page(`
  over `traktor_nml/` returns exactly the two registrations, and
  nicegui's own mounts are `/_nicegui_ws/`, `/_nicegui/{version}/...` and
  `/favicon.ico`. The guard that keeps the path free is the route-set
  assertion in `tests/test_gui_header_tabs.py`, which asserts the set of
  `ui.page` arguments in `app.py` equals `{'/', '/reconnect'}` (DL-130).
- The header carries the brand mark, the divider and the two tabs, and no
  `.task` element. `Main.dc.html`'s header is brand plus bar plus `.task`
  on the left with the `.rail` progress strip on the right, where `.task`
  names the screen; the tab strip names both operations and marks which
  one is open, so the selected tab already carries the screen's name. A
  `.task` beside it would name the screen twice from two sources that can
  disagree with no rule saying which wins. Because this is a cross-screen
  contract rather than one screen's layout it is written into
  `design/reconnect-wizard/Specs.dc.html` under the design set's own
  precedence rule (DL-071), and `_build_header` renders the brand, the
  divider and the strip in that order (DL-131).
- A tab is an anchor the browser follows and its `href` is the route it
  names. The two operations are separate pages registered at separate
  routes and share no pipeline, so a client-side toggle would render one
  page for two routes and cost each operation the URL it is reachable by.
  Each tab is a `ui.link` whose target is that operation's own route, so
  following one is a page load and the address bar carries the route. The
  strip is a `nav` element labelled `Sections` holding exactly two
  anchors: `/` labelled Reconstruct playlists first and `/reconnect`
  labelled Reconnect wizard second (DL-132).
- The selected tab is marked by `aria-current="page"` and the
  `wizard-tab-selected` class, and three mechanisms of stated reach read
  the marking back. A selected state expressed only as a colour is a
  state no guard can read, and a guard asserting the marker merely
  appears passes while the wrong tab carries it, so the state names which
  tab carries it and each guard is a mechanism that exists on the
  interpreter the suite runs on - the system interpreter has no nicegui,
  and `tests/test_gui_view_boundary.py` records that `app.py` is untested
  by interaction because no pytest harness drives rendered DOM. Mechanism
  one is a pure unit guard over `navigation.header_tabs` in
  `tests/test_gui_navigation.py`, which establishes that for each route
  exactly one record is selected and it is the record whose route equals
  the active route in the order the table declares, and cannot establish
  that `app.py` uses the result. Mechanism two is the recording stub in
  `tests/test_gui_header_tabs.py`, following the register
  `tests/test_gui_module_imports.py` uses - minimal nicegui and webview
  stand-ins installed into `sys.modules` for the duration of the test -
  whose `ui.link` records its label and target and whose returned handle
  records its `.classes()` and `.props()` strings; it establishes that
  `app.py` emits two links in table order with the right targets and
  marks exactly the right one, and cannot establish that nicegui renders
  `ui.link` as an anchor or that the class survives Quasar's layers.
  Mechanism three is the served-page gate run, the only one that
  establishes what a browser has. In every mechanism the collected
  markers are compared by equality against exactly the one route under
  test, never by membership and never by `any()`, and a second marker on
  the same anchor counts, so the wrong tab, both tabs and no tab each
  fail (DL-133).
- `_page_chrome` renders the header and takes the active route as its
  argument. It is already the one preamble both routes call, precisely so
  a second route cannot drift from the wizard's theme (DL-078, DL-085); a
  header rendered anywhere else would be two call sites that can disagree
  about the tab set. It takes the active route and renders the header
  after the stylesheet is installed, so both pages carry one header built
  from one tab table, and the active route selects from that table rather
  than each page naming its own tabs (DL-134).
- The header and tab rules are built in `theme.py` from the tokens it
  already carries. `theme.py` holds the stylesheet and imports no nicegui
  (DL-069), and `app.py` carries no hex literal, which
  `tests/test_gui_theme.py` enforces by scanning `app.py`'s source, so a
  rule expressed in `app.py` would either repeat a colour or be
  untestable below the boundary. The header bar, the brand, the divider,
  the tab and the selected tab are five classes in `page_stylesheet`
  built from `GROUND`, `SURFACE_2`, `SURFACE_4`, `BORDER`,
  `BORDER_STRONG`, `TEXT`, `TEXT_FAINT` and the existing type scale. The
  selected tab follows `Main.dc.html`'s `.st.now` treatment: the
  `SURFACE_4` ground, the inset `BORDER_STRONG` border and `TEXT` ink at
  weight 600. No colour enters `theme.py` and no hex reaches `app.py`
  (DL-135).
- `page_stylesheet` carries no `#` comment, and a guard asserts what the
  stylesheet defines. The stylesheet is one f-string of CSS and CSS has
  no `#` comment form: a `#` line inside it parses as an ID selector
  whose block is the text following it, so the rule after it is swallowed
  and no parse error is raised anywhere. Every note inside
  `page_stylesheet` is written in `/* */` form, and
  `tests/test_gui_theme.py` asserts that each of the five header and tab
  class names appears as a selector at the start of a rule in the
  returned string and that no line of that string has `#` as its first
  non-space character. The mutation that makes it fail replaces one
  `/* */` note with a `#` line (DL-136).
- No script in the gate repository takes a code change and the prose in
  five of its files carries the routes. A gate script that named a route
  would fail on the reassignment and one that does not keeps serving
  whatever `app.py` registers, so every gate file was read and the
  enumeration command below was run over that repository too.
  `serve_w002.py` calls `gui_app.build_wizard()` and `ui.run(port=8115)`
  and holds no route string at all; `serve_reconstruct.py` calls
  `gui_app.build_wizard()` and `ui.run(port=8116)` and its only route
  strings sit in its module docstring; `reconstruct_fixture.py` names the
  screen by its route in its module docstring and in the
  `assemble_output` docstring; the gate README's `serve_w002.py` table
  row is the only line in that file naming port 8115, and there is no
  line-by-line driving order in it; and the gate `.gitignore`'s comment
  describes the files a gate run writes. Every executable body stands and
  what carries the routes is prose in those five files. `serve_w002.py`
  is CRLF and the rest LF under that repository's own `* -text` setting,
  and the gate README's file table naming five scripts and not
  `serve_reconstruct.py` predates this work and stands (DL-137).
- Acceptance for the header is a served-page gate run over both routes
  rather than the suite alone. A `gui/` defect has only ever been found
  by serving the page (DL-084), and the duplicate-entry defect surfaced
  there after a green suite; a header is exactly the class of change a
  stylesheet layer or a framework default can defeat while the unit
  guards stay green. The run serves the app from the gate repository and
  reads the header back off each route, and it is recorded in its own
  dated record under `docs/` rather than into either existing record
  (DL-138).
- The tab table and the selection rule sit in
  `traktor_nml/gui/navigation.py`, below the nicegui boundary. The rule
  that decides which tab is selected is the one thing here a defect can
  silently invert, and a rule expressed inside a `@ui.page` body can only
  be read back through a framework the suite does not have. `SECTIONS`,
  the table of route-and-label pairs, and `header_tabs`, which turns an
  active route into tab records, live in a nicegui-free module beside
  `review_model.py`, `wizard_state.py` and `conflict_model.py`, under the
  boundary `tests/test_gui_view_boundary.py` enforces.
  `header_tabs(active_route)` returns one record per table row carrying
  the route, the label, whether it is selected, the class string and the
  `aria-current` value or `None`, so the selection rule is a pure
  computation a guard runs directly. `navigation.py` is LF and imports no
  nicegui; `app.py` renders what it returns and decides nothing (DL-139).
- `__main__.py`'s window title and docstring name the application rather
  than one of its operations. It calls `ui.run(title='traktor-nml-tool',
  native=True)` and native mode opens whatever `/` resolves to, which is
  the reconstruct page, while the window holds both operations and the
  header's selected tab names the one that is open - so a title naming
  either operation contradicts the header on the other route. The module
  docstring states that the entry point starts the application, and its
  second paragraph - why this lives here rather than in `commands/` -
  stands word for word. `__main__.py` is LF at zero CRLF and is written
  as such (DL-140).
- `/reconstruct` is registered by nothing and answers nicegui's own 404.
  The two ways to keep the path alive are registering the page at both
  paths or redirecting one to the other, and both mean two paths
  answering for one page, which is the shape this arrangement exists to
  remove. What makes the plain 404 safe is the enumeration rather than a
  redirect: every reference to the path in either repository is found by
  the command below and carries the route the page answers, so no
  procedure this project owns still holds it. A bookmark a person kept is
  outside what either repository can fix, and a redirect would not tell
  that person the app was rearranged (DL-141).
- Every edit to `app.py` preserves its 100% CRLF and every other touched
  Python file its LF. `app.py` is the one module in the package written
  CRLF throughout, at zero bare LF, while `theme.py`, `navigation.py`,
  `__main__.py`, the model modules and the tests are LF; an editor or a
  helper that normalises on write silently converts the file and the diff
  swallows the whole module. Every read and write of `app.py` passes
  `newline=''`, and a guard in `tests/test_gui_header_tabs.py` asserts
  that `app.py`'s bytes hold zero bare LF and that `navigation.py`,
  `__main__.py` and `theme.py` hold zero CRLF. The gate's
  `serve_w002.py` is CRLF and its other scripts LF under that
  repository's own `* -text` setting, and a byte check reports each
  (DL-142).
- The served-page gate run drives three URLs and reads back what the DOM
  has. The unit mechanisms stop at what `app.py` emits and cannot see a
  framework defeat a rule, and the rendered page is the only place the
  header's anchors, their hrefs, the marker and the painted colour exist
  together. The run serves the app and opens `http://localhost:8115/` and
  `http://localhost:8115/reconnect`, reading back per route the header's
  anchor hrefs in order, which single href carries `aria-current="page"`,
  which single href carries `wizard-tab-selected`, the computed
  background of the selected tab against `theme.SURFACE_4` and the
  computed colour of an unselected tab against `theme.TEXT_FAINT`, with a
  matches-or-differs verdict per named surface. It also opens
  `http://localhost:8115/reconstruct` and records the status the
  framework returns for a path nothing registers. The run is written into
  a new dated record; every browser record already under `docs/` keeps
  every byte (DL-143).
- `_build_header` is the only place in `app.py` naming a route or a tab
  label, and the AST guard reaching that sees string literals only. Two
  places naming a route is the shape that lets one page carry a tab set
  the other does not, and the table sits in `navigation.py`, so any route
  string left in `app.py` is a second source. `app.py` calls
  `navigation.header_tabs(active_route)` and passes each record's route
  to `ui.link`'s target, its class string to `.classes()` and its
  `aria-current` value to `.props()`. An AST guard in
  `tests/test_gui_header_tabs.py` asserts that the only string literals
  matching a route shape in `app.py` are the two `@ui.page` arguments and
  that neither tab label appears in `app.py` at all. Its reach is stated
  rather than assumed: an `ast.Constant` walk sees string literals and a
  docstring, which is one, and it does not see a `#` comment - the
  comment in `app.py` that named the earlier arrangement was invisible to
  it and was found by the text enumeration instead. The guard establishes
  source-level single sourcing for literals, the enumeration covers
  comments and prose, and neither establishes behaviour, which is what
  DL-133's three mechanisms are for (DL-144).
- The enumeration of route references is produced by a recorded command
  so a later reader re-runs it rather than re-deriving the list. Two
  rounds of hand-listing the places that name a route each missed one: a
  list written by recall is not evidence, and a later reader cannot tell
  a complete list from an incomplete one. The command, run in Git Bash at
  the root of the repository, is:

      MSYS_NO_PATHCONV=1 git --no-pager grep -nE "/recon(struct|nect)([^-_a-zA-Z0-9]|$)" -- traktor_nml tests design tools CLAUDE.md

  The pathspec keeps the historical plan documents under `docs/` -
  records of plans already taken - outside the result. The trailing
  character class is what does the work: measured over this tree the
  command returns 67 lines, the same pattern with no pathspec returns
  220, and the same pathspec with the character class dropped returns 85.
  `MSYS_NO_PATHCONV=1` is no part of what makes this command work -
  measured, it returns the same 67 lines with the variable set and unset.
  It is carried as a precaution against a different shape of the same
  search, and that shape reproduces: `git --no-pager grep -n -F
  "/reconstruct"` finds no route reference at all, while the same command
  under `MSYS_NO_PATHCONV=1` returns 69 lines. The cause is visible one
  level down - `python -c "import sys;print(sys.argv[1:])" -F
  "/reconstruct"` prints `['-F',
  'C:/Users/marcu/AppData/Local/Programs/Git/reconstruct']` and the same
  invocation under `MSYS_NO_PATHCONV=1` prints `['-F', '/reconstruct']` -
  so a bare leading-slash argument is rewritten into a Windows path
  before git sees it. The `-E` pattern escapes that conversion because it
  carries parentheses, a pipe, a bracket class and a dollar, which the
  same probe confirms is passed through unchanged. A fixed-string search
  for a route therefore reads as a clean tree while the tree is full of
  hits, which is why the recorded command is the `-E` one, and acceptance
  is that re-running it returns only the lines this work names as
  intentionally carrying the token (DL-145).
- `SCREEN-READER-PASS.md` in the gate repository is a record and keeps
  every byte. Its line 4 says it is written down so the next pass is a
  re-run rather than a rediscovery, which reads as a procedure, while
  line 109 of the same file says it is kept as a record of the pass that
  ran on 2026-08-29 and not as an invitation to run another, and line 107
  says accessibility work is out of scope for this version; the later and
  more specific statement governs and the file is a record. Its Edge
  launch at `http://localhost:8115` is the launch that pass actually
  used, and the reading it produced is
  `docs/2026-08-29-w004-focus-ring-record.md`, which keeps every byte;
  rewriting that line would make the two files disagree about what was
  driven and would point a do-not-run procedure at a route no recorded
  pass ever used. What a later session needs sits in the places that are
  live: the gate README's `serve_w002.py` row names the wizard's URL and
  this file carries the route statement. This entry also records the
  citation error it corrects - an earlier reading cited line 4 alone for
  a classification line 109 contradicts (DL-146).
- A stylesheet class and its only consumer land in one milestone.
  `tests/test_gui_theme.py`'s `test_every_wizard_class_reaches_app_py`
  asserts that every `.wizard-*` class `page_stylesheet()` defines
  appears in `app.py`'s source, and the five header and tab classes have
  exactly one consumer, the header builder in `app.py`, so a milestone
  writing the rules without the builder cannot go green; `theme.py` and
  its guards sit in the milestone that writes `app.py` rather than in one
  of their own. The alternative - entering a class in
  `_KNOWN_UNATTACHED_CLASSES` to get past a milestone gate - is refused
  by that list's own comment, which says its single entry is there
  because no milestone builds a consumer for it and that entries are
  named one at a time rather than by a pattern, precisely so a genuinely
  forgotten class cannot slip through under the same excuse; a class
  whose consumer lands one milestone later is not an unattached class.
  What stays in its own milestone is `navigation.py` and its guards,
  which import no framework and have no consumer to wait for, so the
  boundary follows the coupling the guard reports rather than the file
  types (DL-147).
- A resolution maps an identity key to an `(input index, primary key)`
  pair rather than to a bare primary key. The primary key is derived from
  the location (DL-004), so two records for one file in two inputs carry
  the identical key, and `group_identities` unions them through the
  location tier into one group: a group of base plus a source holding the
  same path has a `member_keys` frozenset of size one while holding two
  records, and a bare primary key therefore cannot name which record wins
  in the commonest conflict shape. The input index is the disambiguator
  `splice.py` already relies on for exactly this reason - `new_entries`
  carries `(input_idx, record)` because two distinct records can carry
  identical field values (DL-148).
- `ConflictRow` carries a `candidates` tuple in place of per-side value
  lists. A per-side pair of value lists folds each side down to its
  distinct sorted values, so which record held which value is discarded
  before the row leaves `splice.py` and a page offering one option per
  answer cannot be built from the row. The row carries one
  `ConflictCandidate` per distinct tuple of divergent-attribute values,
  each holding its contributing `(input index, primary key)` pairs and
  its values in divergent-attribute order; `identity_key`, `attrs` and
  `resolution` keep their meaning, so `_write_conflict_report` reads the
  same three CSV columns (DL-149).
- Two records agreeing on every divergent attribute present as one
  candidate carrying both contributors. Candidates are keyed by their
  tuple of divergent-attribute values, so two sources that agree with
  each other collapse to one entry and the operator sees one option per
  distinct answer rather than two identical controls, with the option
  naming every collection that supplies it. A pick stores the contributor
  of lowest input index, so the recorded pair is deterministic and the
  values written are the same whichever contributor is named (DL-150).
- A resolution moves the redirect target only where the group holds no
  base record; where it holds one, `base_members[0]` stays the target and
  the pick supplies values. `_resolve_conflicts` sets
  `old_to_new_key[record.primary_key] = winner.primary_key` for every
  non-winner, so the winner is the redirect target and the playlist
  `PRIMARYKEY` rewrite behind it. Where the group holds a base record the
  winner is that base record and DL-116 keeps base's own `ENTRY`, so the
  pick reaches only `entry_patches` and the target is unmoved; where the
  group holds no base record the winner is the record the resolution
  names (DL-152), so the pick moves the target and every other member
  redirects to it, which is the point of letting the operator name the
  survivor. DL-122's conclusion is untouched either way: that rule is
  about groups holding several base records and about `ambiguous_keys`,
  and a multi-base group always takes the base branch (DL-151).
- A group holding no base record consults its resolution for the winner.
  A vocabulary of two side tokens cannot name a winner among several
  non-base copies, so such a group could only fall to the run-wide
  picker while its resolution suppressed the unresolved abort and
  labelled the conflict row. The transplant branch reads the resolution
  and appends the named record to `new_entries`, falling back to
  `pick_non_base()` where no resolution names a member, so DL-117 stands:
  the picker still answers the groups no resolution names. Such a group
  needs two or more inputs none of which is input 0, so any fixture where
  base holds the track puts index 0 in the group and the branch is not
  reached (DL-152).
- A resolution naming a pair no member of the group carries is inert.
  DL-105 already makes an identity key naming no group inert rather than
  an error, and a pair naming no member is the same shape of stale input,
  reachable after a re-preview changes membership: the group falls
  through to `on_conflict` or to the unresolved abort, the way an omitted
  key does (DL-153).
- The bulk strip reads "All base" plus one action per source collection,
  labelled from the source's path. `app.py` holds the operator-chosen
  source paths in the order they were listed, and a source's input index
  is its position in that list plus one. A bulk action settles every
  undecided group its collection holds a record in and leaves every other
  group untouched, so a group the collection has no record in stays
  undecided and counts toward `outstanding` rather than silently taking
  another collection's values (DL-154).
- `conflict_model.py`'s decision vocabulary is `UNDECIDED` plus a
  candidate reference, and no side token is a mapping value. `resolve`,
  `resolve_where_answered`, `resolutions`, `decision` and `_Decision`
  each carry the
  mapping value, so each takes a candidate reference and the guard over a
  fixed token set goes with them. The words base and source survive as
  operator-facing labels and in `write_refusal_sentence`, where they name
  what the operator sees rather than what the core reads (DL-155).
- The served-page gate fixture holds a second source collection that
  disagrees with the first and with base. Serving the page is the only
  gate that has ever caught a defect in `gui/` (DL-084), and the defect
  this work repairs is invisible with one source, since naming a side and
  naming a record are the same pick there. `reconstruct_fixture.py` in
  the gate repository builds base plus two sources disagreeing three ways
  on a tracked attribute and the read-back reports which of the three
  values landed; the parity manifest and the `w002gatefix2` fixture are
  untouched (DL-156).
- The display of a candidate's values joins one value per divergent
  attribute and never several answers into one cell. A separator token
  existed because the pick the operator was asked for could not express
  which source, and one control per candidate gives each answer its own
  cell; the join survives only inside a single candidate, whose
  contributing records disagree on nothing divergent by construction, so
  the separator and the absent-value marker leave with the two side
  fields (DL-157).
- DL-115's re-attachment compares the group's candidate set together with
  its member primary keys - a correction to a rule shipped in the tree at
  `aa6ab76`. Measured there: base plus one source at
  `C:/:Music/:track.mp3` gives `member_keys={'C:/:Music/:track.mp3'}` and
  one source-side answer; a second source at that same path leaves
  `member_keys` identical while the answers become two. The primary key
  is derived from the location (DL-004), so records for one file in two
  inputs collide in the frozenset and a further source is invisible to a
  comparison over the member set alone, letting a held pick survive a
  re-preview whose available answers moved underneath it - the
  silently-wrong-value defect this work repairs, reached by a second
  route. Re-attachment therefore compares the candidate set, each
  candidate carrying its contributing pairs and its values, together with
  `member_keys`, so a pick stands only where the answers it was made
  against are the answers on offer; the rule carries its own fail-first
  guard over the two-sources-at-one-path shape above (DL-158).
- An inert pair is inert at the core and refused at the model.
  `resolutions.get(identity_key)` returns `None` for a key naming no
  group and the group falls through to `on_conflict` or the unresolved
  abort (DL-105, DL-153): that is the core reading a mapping it did not
  build, where a stale entry must not abort a run. `conflict_model.py`
  builds the mapping from groups it holds, so a candidate reference
  naming no candidate of its own group is a caller error rather than
  stale operator input, and `resolve` raises on it. The two behaviours
  are one rule read from two sides: the model never emits a pair its
  group does not carry, and the core never trusts that it did not
  (DL-159).
- `write_refusal_sentence` names the controls the page renders rather
  than two sides. The row offers one control per candidate and the strip
  offers "All base" plus one action per source collection, so wording
  naming two sides would describe controls the page does not hold. The
  sentence names choosing a collection for each row, and its guard
  asserts the rendered wording against the rendered controls (DL-160).
- A bulk-action label is the shortest trailing run of path segments that
  tells its source apart from every other listed source, falling back to
  the full resolved path. `conflict_model.source_refusal` refuses only a
  candidate whose resolved path is already listed, so two collections
  sharing a file name in different folders are both admissible, and so
  are two sharing a file name and a parent, since `/a/music/collection.nml`
  and `/b/music/collection.nml` differ only further up: a stem, or a stem
  plus one parent, is a rule with a collision it cannot break. The label
  is built by walking leftward from the file name one segment at a time
  and stopping at the first length unique among the listed sources, which
  gives `collection.nml` where nothing collides, `collection.nml (music)`
  where the file name collides, `collection.nml (a/music)` where the file
  name and its parent both collide, and so on. The walk terminates
  because the full resolved path always distinguishes - `source_refusal`
  has refused any candidate whose resolved path equals a listed one, so
  no two listed sources share one. In the worst case, two sources
  differing only at the drive or the root, the label is each source's
  full resolved path, which is long but never ambiguous, and no input
  index is needed because the path itself carries the distinction the
  operator chose the file by (DL-161).
- The header band and every content column occupy one column, set by a
  single `.wizard-content-width` rule that both carry: the band's ground
  and its lower rule end where the card's edge is, and the brand mark
  starts on the card's own first pixel rather than inset from it. The
  width is written once, as `theme.CONTENT_WIDTH`, because a band wider
  than the content it heads reads as page chrome rather than as the
  application's own top edge, and two places holding the width is how
  they come to disagree. The header row carries no horizontal padding of
  its own for the same reason: padding there would inset the brand from
  the column while leaving the span itself correct, which is the half of
  the alignment a width alone does not settle (DL-162).
- The build-playlist screen is a standalone route at `/build-playlist`
  with its own single-page form, not a step folded into the reconnect
  wizard's stepper or the reconstruct page's step rail: it is a
  separate job with its own inputs and its own review model, not a
  branch of either existing flow (DL-260).
- A nicegui-free `traktor_nml/gui/buildplaylist_view.py` module holds
  the build-playlist screen's form validation, invocation-argument
  shaping, and unresolved-row/report formatting; `app.py` imports it
  rather than holding that logic itself (DL-261).
- The build-playlist screen drives `traktor_nml/buildplaylist.py`'s
  `assemble_output`, `traktor_nml/rewrite.py`'s
  `path_collides`/`read_and_parse_source`/`write_bytes_atomically`, and
  `traktor_nml/split.py`'s `build_output` directly, mirroring
  `build_playlist_cmd.py`'s own sequencing - collision refusal, decode,
  assemble, optional isolation pass, atomic write - without calling the
  CLI handler or building an `argparse.Namespace` (DL-262).
- `navigation.SECTIONS` carries a third row, `("/build-playlist",
  "Build playlist")`, appended after the reconstruct and reconnect
  rows, with no change to `header_tabs`' selection rule (DL-263).
- The first shipped build-playlist screen shows unresolved tracklist
  lines as a read-only report - line, raw text, kind - beside an Allow
  unmatched toggle mirroring `--allow-unmatched`, rather than an
  interactive per-line accept/reject/pick review workflow (DL-264).
- `design/build-playlist/Specs.dc.html` is the build-playlist screen's
  design of record, drafted before its GUI requirements were finalized,
  on the same precedent as the reconnect wizard's own artboard (DL-071,
  DL-265).
- The base collection and the input are both chosen through
  `gui/file_picker.py`'s `pick_file_or_folder`, matching the CLI's
  `base`/`tracklist` positional arguments, rather than a paste-in-text
  tracklist entry (DL-266).
- The build-playlist GUI form omits `--dry-run` and the
  `--unresolved-report` CSV export: a dry run is achieved by simply not
  clicking Write, and the on-screen read-only unresolved-lines report
  (DL-264) replaces the CSV export for a first pass rather than also
  offering a file download (DL-267).
- `buildplaylist_view.run_summary`'s sentence tracks
  `build_playlist_cmd.py`'s own CLI wording for the same underlying
  condition - unresolved tracks, no entries resolved, a target-folder
  error, entries written - rather than inventing separate GUI phrasing
  (DL-268).
- A failed base/tracklist read or parse, or a write failure, surfaces
  through `run_summary` as a refusal sentence naming the failure, the
  same way `form_errors` already surfaces a missing-field refusal,
  rather than an uncaught exception or a silent no-op; there is no GUI
  equivalent of the CLI's non-zero exit code (DL-269).
- The build-playlist report table does not surface
  `MatchConfidence.LOOSE` explicitly: every resolved row in this first
  pass is, by construction, a LOOSE match, so a confidence column would
  carry one constant value on every row (DL-270).
- The build-playlist screen schedules no keyboard-navigation, focus-ring,
  tab-order or screen-reader/announcement work beyond whatever the
  existing header-tab shell and `theme.py` already provide (DL-271).
- The build-playlist form's output path is derived rather than typed:
  the playlist name is the file's stem, and `rewrite.path_collides` and
  the write step both consume the one derived path (DL-272). Its directory
  is the output-folder chooser's, per DL-297.
- Every button in the GUI is drawn on the action blue, `theme.ACTION`,
  with `theme.GROUND` as its ink, 8.2:1: the primary action through
  `wizard-control-primary` and every other button through
  `wizard-control-fill`, the artboards' `.btn` amended to the same blue
  first (DL-071). Four kinds of button keep their own colour, because
  the colour is what they say: `Accept` in the found tint and `Reject`
  in the not-found tint (`Review.dc.html`'s `.btn-ok` and `.btn-no`),
  the Review step's filter chips, whose tint marks the active filter,
  and the Resolve step's answer card, a record read field by field
  rather than a control. A disabled filled or primary button takes
  `.btn.off`'s colours, so it does not read as a blue control waiting to
  be pressed. Every button's label is set in the case it is written in
  rather than in Quasar's capitals. With every button blue, colour does
  not set a screen's primary action apart; weight 600 against 500 does,
  and the primary's `TYPE_13` stands against Quasar's 14px. The call
  sites are guarded in `tests/test_gui_button_fill.py`, and the page is
  read in `docs/2026-09-16-button-fill-browser-record.md` (DL-273).
- Every build-playlist input hands resolution one ordered list of
  `Candidate(line_number, raw_text, artist, title, record)` values; a
  `record` of `None` is an unparseable entry. Refusal (DL-027, DL-036),
  the report rows, synthesis and the splice depend only on a per-entry
  outcome and those four fields, so folding unparseable entries into the
  same list leaves them one input shape (DL-274).
- Candidates sit on `match_records`' old side and the collection on its
  new side. Refutation's cross-source test compares `from_disk` on both
  sides symmetrically and every tolerance reads the larger of the two,
  and ambiguity is counted per old record, one candidate per call, so the
  direction gives the same verdicts either way (DL-278).
- The plain-text path is held byte-identical by a golden corpus under
  `tests/baselines/build_playlist_text/`, recorded from the code before
  the Candidate seam existed and replayed by
  `tests/test_build_playlist_text_parity.py`: argv, stdout, stderr, exit
  code, output bytes and the unresolved report per case, with `uuid4`
  fixed. `tests/baselines/manifest.json` holds no build-playlist case and
  is not regenerated for it (DL-279).
- The build-playlist stats keys and their order - `lines_read`,
  `lines_resolved`, `unresolved_unparseable`, `unresolved_unmatched`,
  `unresolved_ambiguous`, `playlist_name`, `entries_written` - are fixed.
  `lines_read` counts candidates. The input's format and codec travel in
  `InputRead`, not in the stats, because a stats key would change a text
  run's stdout (DL-280).
- `traktor_nml/playlistinput.py` is the nicegui-free input module:
  `detect_format`, and `read_input` returning `InputRead(format, encoding,
  candidates)` or raising `InputReadError(code)`. The CLI handler and the
  GUI's `_run_build_playlist` read an input through `read_input` and
  nothing else (DL-281). An undecodable input refuses with
  `tracklist_decode_error=<path>` for every input format - text, CSV and
  M3U share the decode helpers - the code the CLI prints, kept so a text
  run's output stays the recorded corpus's
  (`tests/baselines/build_playlist_text/decode_error`).
- Resolution runs at a fixed `MatchConfidence.LOOSE`. A candidate carrying
  more than artist and title reaches the stricter tiers at LOOSE because
  the cascade tries tiers strongest first; `FILENAME` would add
  `bare_name`, which collides on stem component files (DL-276).
- Each input format fills every `EntryRecord` field its source carries: a
  folder file or an M3U path present on this machine is indexed from disk
  (size in KB, tags, duration, file name, folder parts, `source_path`); an
  M3U path absent here keeps its file name, folder parts and `#EXTINF`
  artist, title and duration; a CSV row keeps artist, title, album,
  duration and file name. `record_keys` emits the size, file and path
  tiers only for non-empty fields, so a record cut down to artist and
  title reaches only `artist_title`, the tier text lists go ambiguous on
  (DL-275).
- A folder or M3U candidate resolves through `match_records` alone, with
  no exact-location pre-pass. `match_records` marks a tier with several
  survivors ambiguous and keeps descending, so a collection holding one
  track at two locations resolves uniquely at `path_suffix_3`; a pre-pass
  would need collection `VOLUME` naming and resolve nothing more (DL-277).
- Any input file whose suffix is not `.csv`, `.m3u` or `.m3u8` reads as
  plain text, decoded `utf-8-sig` strictly, refusing with
  `tracklist_decode_error` (DL-282).
- Decoding: plain text and `.m3u8` are `utf-8-sig` strict; `.m3u` and
  `.csv` try `utf-8-sig` and fall back to `cp1252`. The codec used is
  `InputRead.encoding`, which the CLI prints raw and the screen names in
  the operator's terms (DL-303), because a `cp1252` fallback misreads
  another single-byte codepage without an error (DL-283).
- `playlistinput.CSV_COLUMNS` - `Artist`, `Title` (required), `Album`,
  `Duration`, `File name` - is the one CSV header definition.
  `csv_template_bytes()` is that header alone, UTF-8 with a BOM and CRLF,
  with no example row, since a forgotten example row is an unmatched entry
  that refuses the run. Headers match case-insensitively after strip,
  unknown columns are ignored, and a file without `Artist` and `Title`
  refuses with `csv_header_missing` (DL-284).
- The CSV delimiter is read off the header line: comma when it yields both
  `Artist` and `Title`, else semicolon when that does, the separator Excel
  writes where the decimal mark is a comma, else `csv_header_missing`.
  `csv.Sniffer` guesses from data rows and misreads titles holding commas
  (DL-285).
- A CSV row with an empty `Artist` or `Title` is unparseable and a row with
  every cell empty is skipped. `Duration` reads seconds, `m:ss` or
  `h:mm:ss`; an unreadable duration is left empty rather than refusing the
  row. `line_number` is the physical line the row starts on, the
  spreadsheet's row number, and `raw_text` the row as read (DL-286).
- In an M3U, `#EXTINF:<seconds>,<Artist - Title>` attaches to the next path
  line and other `#` lines are ignored; seconds of zero or less give no
  duration, and display text without ` - ` leaves artist and title empty.
  A relative path resolves against the playlist's folder and a URL line is
  unparseable. A path that is a file here is indexed from disk and takes
  artist, title and duration from the file; `#EXTINF` fills only a
  path-string record, because its integer seconds sit up to 1.0s from a
  collection's `PLAYTIME_FLOAT`, the same-source tolerance's edge (DL-287).
- A path-string record decodes its path with `PureWindowsPath` when it
  holds a drive letter or a backslash and `PurePosixPath` otherwise, drops
  the anchor, and encodes the folder parts with `model.encode_traktor_dir`
  into a location with an empty volume, so a playlist written on a Mac
  matches a Windows collection by its trailing folders (DL-288).
- A folder input reads only that directory's own files with an audio
  extension, ordered by the casefolded name split into digit and
  non-digit runs with digit runs compared as integers, ties broken by the
  plain name. A plain string sort puts `10 - ...` before `2 - ...`.
  `line_number` is the 1-based position and `raw_text` the file name
  (DL-289).
- `diskscan.index_files(paths, cache=None)` indexes an explicit list: one
  record per path in order, duplicates kept, no walk, built by the same
  `_record_for_file` `index_scan_roots` uses. A failed `stat()` raises
  `DiskReadError` naming the path instead of shortening the list;
  unreadable tags give empty tag fields. With no cache, no cache file is
  read or written, so build-playlist writes no side file (DL-290).
- `index_scan_roots` shares only the per-file `EntryRecord` construction
  with `index_files`; its records, stats, diagnostics and cache behaviour
  are its own (DL-291).
- An input that yields no candidates runs to `no_entries_resolved`. An
  input that cannot be read refuses before assembly with one code:
  `input_not_found=<path>`, `tracklist_decode_error=<path>`,
  `csv_header_missing`, `input_read_error=<path>` for a folder or M3U file
  that cannot be indexed, or `input_format_mismatch=<format>` when
  `--input-format` contradicts whether the path is a directory (DL-292).
- A folder or M3U file the collection does not hold is reported as
  unmatched; build-playlist never adds an `ENTRY` (DL-293).
- The CLI keeps its positional `tracklist` argument for every format,
  directories included, and `--input-format {auto,text,csv,m3u,folder}`
  overrides suffix detection. A run over any input other than plain text
  prints `input_format=` and `input_encoding=` ahead of the stats keys; a
  text run prints neither, so its stdout stays the corpus's. No subcommand
  writes the CSV template; `build-playlist --help` lists the columns from
  `CSV_COLUMNS` (DL-294).
- The `/build-playlist` screen offers `Choose file...` (text, CSV, M3U) and
  `Choose folder...` for its input, shows the detected format and, after a
  run, the codec, and shows the CSV columns beside a `Download CSV
  template` control. Native mode writes the template through a pywebview
  SAVE dialog (`file_picker.pick_save_path`), because pywebview blocks
  browser downloads by default; served over HTTP it goes through
  `ui.download`. The artboard is drawn first (DL-071, DL-295).
- `buildplaylist_view.run_summary` and `form_errors` use format-neutral
  words - `entry`/`entries` through `wording.plural`, `Choose an input.` -
  and a run on CSV, M3U or folder input appends the format, and for CSV
  and M3U the codec, it read; counts are read off the result (DL-215,
  DL-296).
- The build-playlist screen's output folder and playlist folder are two
  controls that never share a value. The output folder is a disk
  directory chosen through `pick_file_or_folder(directories_only=True)`;
  the file is `<output folder>/<playlist name>.nml`, or sits in the base
  collection's directory when none is chosen - the CLI's positional output
  path. The playlist folder is a chooser over the base collection's
  `FOLDER` nodes from `playlists.playlist_folder_choices` plus `Collection
  root`; its `NAME` is `assemble_output`'s `target_folder`, the CLI's
  `--target-folder`, and `None` for the root. A `FOLDER` whose `NAME`
  another `FOLDER` holds is listed disabled with its path, because
  `target_folder` is resolved by `NAME` alone and would refuse as
  `target_folder_ambiguous`. One field cannot serve both: joined onto a
  disk path a `FOLDER` name names a directory that need not exist. The
  playlist-folder chooser is enabled only while Full collection is on:
  otherwise the isolation pass (`split.build_output`) keeps only the new
  playlist directly under the root, so a folder choice would change
  nothing in the file; the disabled chooser carries a note saying so and
  no `target_folder` is passed. The output folder applies either way. This
  supersedes DL-272's statement that the form has no separate output-path
  control (DL-297).
- The resolve rail's key track is sized to the longest label in
  `answer_detail.LABELS` drawn whole with its difference mark, not to
  the artboard's first 60px. `Resolve.dc.html`'s `.cmpf` drew only
  TITLE, ARTIST, BITRATE and FILESIZE, so the longest label was never
  drawn and PLAYTIME_FLOAT overlapped its value; a marked FILESIZE
  overran it too. The labels stay the NML attribute names (DL-254) and a
  key is never truncated, so the track grows: IBM Plex Mono's 0.6em
  advance plus the key's 0.05em spacing is 7.15px a character at 11px,
  PLAYTIME_FLOAT's fourteen are 100.1px, and the 5px mark and 5px gap
  make 110.1px, taken up to `111px`. The artboard is amended first, with
  a PLAYTIME_FLOAT row drawn on both answers (DL-071). The value column
  pays for it: at the rail's 400px it is 115.8px rather than 166.8px, and
  a longer value is clipped by the cell's existing ellipsis, read in
  `docs/2026-09-16-resolve-key-track-browser-record.md`. A guard computes
  the needed width from `LABELS` and the metrics `theme.py` states, so a
  longer label fails the suite rather than the page (DL-298).
- A chooser button is sized to its label and stands in a flex row beside
  the path it chooses, as every artboard's `.row` draws it. On
  `/reconnect`, `Choose collection file...` and `Choose output folder...`
  stood as direct children of `.wizard-card-body`, a flex column whose
  default alignment stretched each to the card's `908px` around a label
  under `150px`. Each is composed in a `wizard-path-row` with its path, the
  path taking the room and the button `flex: none`, following
  `Main.dc.html:92`'s `.row` (DL-071); the path stays a mono label rather
  than the artboard's bordered `.field`. `/` and `/build-playlist` already
  sat their choosers in rows and are unchanged. A guard reads app.py and
  fails when a `Choose` or `Download CSV template` button is built inside
  anything but a class the stylesheet declares as a flex row, and the
  widths are read in `docs/2026-09-16-chooser-width-browser-record.md`
  (DL-299).
- `build-playlist` prints each unresolved row as `unresolved
  position=<n> kind=<kind> text=<raw>` for a folder run and `unresolved
  line=<n> kind=<kind> text=<raw>` for text, CSV and M3U runs. A folder
  row's `line_number` is the file's 1-based position in name order, not a
  line; the other formats keep `line=` so a text run's stdout replays the
  corpus under `tests/baselines/build_playlist_text/` and CSV and M3U
  output is unchanged. The handler passes `InputRead.format` to the
  printer rather than inferring the format from the row. The
  `--unresolved-report` CSV keeps its `line_number` column for every
  format, and the GUI's unresolved table shows the bare number with no
  label (DL-300).
- A chooser button in a `wizard-path-row`, `wizard-field-row` or
  `buildplaylist-input-row` carries no bottom margin. `.wizard-control`'s
  `margin-bottom` of `CONTROL_GAP` spaces stacked controls, but a flex row
  with `align-items: center` centres each item's margin box, so on
  `/reconnect`, `/` and `/build-playlist` every `Choose` button's border
  box stood `4px` above the path beside it and each row stood that margin
  taller than its tallest box. The artboards' `.row` centres a `.btn` on
  its path with no margin (DL-071), so `theme.py` cancels the margin on
  `.wizard-control` children of those three rows only (DL-069), and
  `.wizard-control` keeps it everywhere else. The card body's `12px` gap
  below each row is unchanged, and what stands below a row sits up by
  the height the row loses. A guard reads the sheet for the zero margin
  on each row class and reads app.py for every path chooser standing in
  one of them as a `.wizard-control`; the offsets are read before and
  after in `docs/2026-09-16-chooser-offset-browser-record.md` (DL-301).
- `/build-playlist`'s unresolved-entries report is one CSS grid of three
  tracks, `REPORT_GRID_TRACKS` (`64px`, the rest, `120px`), with a header
  row carrying `buildplaylist_view.REPORT_COLUMN_LABELS` (`#`, `Entry`,
  `Kind`) as a modifier row on the grid every body row uses, so a heading
  stands over its column at every row. `Specs.dc.html:177`-`178` draws a
  `table.rep` with those headers and widths, and the report was label
  rows with no header and no shared widths (DL-071). It is a hand-rolled
  grid rather than `ui.table` or aggrid, on the conflict grid's reasoning
  (DL-079). `theme.py` carries `:57`'s header label and rule, `:58`-`59`'s
  row inset and rules with none under the last row, and an entry cell
  that shortens with an ellipsis rather than pushing `Kind` (DL-069). The
  number cell reads `.wizard-dim`, the artboard's `.dim`. The kind pills
  of `:60`-`63` and the read-only note of `:185` are not built. A guard
  reads the sheet for the three tracks and the header label and reads
  app.py for the header and every body row built on the grid; the
  columns are read in `docs/2026-09-17-report-columns-browser-record.md`
  (DL-302).
- The `/build-playlist` footer names the encoding a run read in the
  operator's terms: `UTF-8` for `utf-8-sig` and `utf-8`,
  `Windows-1252` for `cp1252`, from `buildplaylist_view.encoding_label`'s
  table, and any other codec name as it stands, so a reader returning a
  new codec is named rather than hidden. `utf-8-sig` is Python's name for
  UTF-8 read past a byte-order mark and `csv_template_bytes()` writes
  one (DL-284), so every template-based CSV showed that name. The CLI's
  `input_encoding=` stays `InputRead.encoding` raw, because DL-294 fixes
  that output and `tests/test_build_playlist_inputs.py` pins it; the
  table lives in the nicegui-free `buildplaylist_view.py` (DL-069) and
  `Specs.dc.html:227`'s footer note is amended to the displayed name
  first (DL-071). After a run that leaves unresolved rows,
  `write_playlist` calls `ui.run_javascript` with `scrollIntoView` on the
  report card's element, gated on rows existing, so the card standing
  below the fold is brought into view; the layout is unchanged and the
  scroll owner is `.wizard-middle`, not the document (DL-189). The
  message is queued after the card's own updates, which the outbox sends
  before it. A guard reads `app.py` for the call gated on the rows,
  because a view helper alone is green where the page never calls it; the
  scrollTops, the card's box and the footer texts are read in
  `docs/2026-09-17-report-scroll-and-encoding-browser-record.md`
  (DL-303).
- The unresolved report draws each row's kind as a pill rather than as
  plain text: `design/build-playlist/Specs.dc.html:60`'s `.kind` shape -
  600 11px/1 IBM Plex Mono, uppercase at `.04em`, `3px 6px` inside a
  `4px` radius, never wrapped - on one class every pill carries, and
  `:61`-`63`'s three kinds each on their own rule, so the shared shape is
  declared once and a kind's tint is a colour triple beside it (DL-071).
  `:61`'s `#2B1D14` and `#5A3A24` and `:63`'s `#1B1D20` are colours
  `theme.py` did not name; they are `REPORT_KIND_UNMATCHED_TINT_BG`,
  `REPORT_KIND_UNMATCHED_TINT_BORDER` and
  `REPORT_KIND_UNPARSEABLE_TINT_BG`, named for the pill each paints
  rather than folded into the nearest `STATUS_NOT_FOUND_*` variant,
  which is a different pair of colours (DL-078). The review screen's
  `.wizard-tag-review` and `.wizard-tag-missing` are not reused: the
  first carries its hue on a `strong` child and neither declares the
  pill's type or radius, and `.wizard-tag-missing`'s ground and border
  are `#21160F` and `#6A3F2C`, not `:61`'s pair. The kind-to-class
  decision and the pill's word live in the nicegui-free
  `buildplaylist_view.py` (DL-069) as a closed mapping, so the class the
  page can carry is always one the sheet has a rule for; a kind the
  mapping does not name falls back to the shared class alone and reads
  as an uppercase mono word in the row's own ink rather than raising.
  The Kind cell holds the pill inside it, so the cell keeps the body
  row's inset while `display: inline-block` lets the pill hug its word
  instead of filling the `120px` track. Three guards stand behind this:
  the sheet's rule per kind, `app.py`'s own kind cell read from its AST,
  because a rule the page never applies is green in a sheet guard
  (DL-189), and every kind the model can produce having a rule, with the
  kinds read from `tracklist.resolve_candidates`' `outcome=` literals
  rather than restated, so a kind added there fails rather than arriving
  untinted. The pills' colours, shape, width against the column and the
  column's own edges are read in
  `docs/2026-09-17-report-kind-pills-browser-record.md` (DL-304).
- A mono element names a class the sheet declares `FONT_MONO` for, never
  Quasar's own `font-mono` utility. `font-mono` is Tailwind's utility and
  its stack is a generic monospace one, not the vendored IBM Plex Mono
  `theme.py` names, so an element carrying it reads whatever monospace
  the system supplies. A utility on the element and a class whose rule
  declares `FONT_MONO` sit at equal specificity, and Quasar's sheet is
  loaded after this one, so on an element carrying both the utility is
  what paints - which is why the rule beside it is not a fix. An element
  whose own rule already declares `FONT_MONO` names no font class at
  all, and one that wants the typeface and nothing else carries
  `wizard-mono`, whose rule declares the family and no size or colour
  (DL-069 keeps both in `theme.py`; `app.py` names the class). The two
  rules that describe a row's flexible child by the class it carries,
  `.wizard-path-row > .wizard-mono` and
  `.buildplaylist-input-row > .wizard-mono`, name that class rather than
  the utility, so the ellipsis truncation travels with it. The guard
  reads `app.py`'s own class lists rather than the sheet, because a
  guard asserting the sheet declares `FONT_MONO` is green in exactly the
  state where every call site names the utility and the page paints the
  wrong face (DL-189); the mono-carrying classes it reads app.py against
  are derived from `page_stylesheet()`'s text, so a rule that starts
  declaring `FONT_MONO` later is covered without editing the guard
  (DL-078). The computed family on every element that carried the
  utility, before and after, and what `document.fonts` reports about the
  vendored face are read in
  `docs/2026-09-17-mono-typeface-browser-record.md` (DL-305).
- The switch is Quasar's `q-toggle` restated as `Main.dc.html:54`-`57`'s
  `.sw`: a 34x19 track rounded to 10px, filled `SWITCH_TRACK` inside a
  1px `BORDER_STRONG` border, holding a 13px `SWITCH_KNOB` circle inset
  2px, and an on state filling the track `ACTION_TINT_BORDER` inside
  `ACTION_TINT_BORDER_ALT` with the knob `ACTION` at the other end.
  Three of Quasar's own declarations paint something else and each is
  named: the visible knob is `.q-toggle__thumb:after`, a 50%-rounded
  circle inside a square `.q-toggle__thumb` box, so a knob colour set on
  the box paints square corners around the circle; `.q-toggle__track`
  carries `opacity: .38`, which washes a track colour out against the
  ground; and the on state colours the knob from `--q-primary` rather
  than from `ACTION`. The two rules that place the knob carry a
  `[dir="ltr"]` prefix, matching the specificity of the rules that place
  it at Quasar's own em offsets. The knob's two ends are one dimension
  each in `theme.py` and the second is derived from the first: the
  track's width less the knob and the inset (DL-078). The on-state knob
  against the on-state track is measured as a non-text pair in
  `tests/test_gui_theme.py` on the 3:1 floor, the same footing the off
  pair stands on, because both are painted only as backgrounds. The
  guard reads the emitted stylesheet and so cannot see the cascade; both
  states, the state before the change and the seven rules the page
  carries are read in
  `docs/2026-09-17-switch-contrast-browser-record.md` (DL-306).
- A switch on the build-playlist screen is drawn as the option row
  `Specs.dc.html:47`-`50` and `:155`-`169` draw: the switch, its label,
  and under the label a description of what each state writes. A label
  alone leaves the difference between the two states nowhere on the
  screen, which is what `Full collection` read as. The label stays
  Quasar's own, so it keeps toggling the switch, and the description is
  a sibling of the whole control indented by `OPTION_NOTE_INDENT`, the
  track's width plus the row's gap, because Quasar builds the label as
  the switch's child rather than as a sibling block (DL-078). The
  unresolved report carries `:185`'s note, built once with the card
  rather than beside the rows, because the run that refills the table
  clears it first. Every sentence lives in `buildplaylist_view.py` and
  `tests/test_gui_buildplaylist_options.py` reads it off the artboard
  rather than repeating it, folding the artboard's em dash to the
  hyphen the string carries, so a sentence edited in the design and not
  on the screen fails the same guard as the reverse; the page guards
  read app.py's own call sites, because a guard reading the constants
  is green in exactly the state where the page never builds them
  (DL-189). The rendered rows, the indent under the label, the label
  still toggling and the note under the table are read in
  `docs/2026-09-17-switch-options-browser-record.md` (DL-307).
- The six tracked attributes carry a tier. `filesize`, `playtime_float`
  and `bitrate` are MEASURED: Traktor wrote both numbers by analysing the
  one file at the LOCATION the identity is derived from
  (`model.py:66`-`96`), so both are real recorded facts and there is no
  operator judgement to ask for. `artist`, `title` and `album` are
  EDITORIAL: a disagreement there is a disagreement about something a
  person typed. A group whose divergence is measured-only is settled by
  rule rather than put to the operator. The reason is the absence of a
  judgement, not the unreality of the difference, which is why this is a
  different question from `matching.py:120`-`150`'s tolerant
  verification: that rule compares Traktor's recorded numbers against the
  bytes on disk - two measurement systems, one of which may be stale -
  and answers whether a candidate is the same file. The two share no
  tolerance and no vocabulary, so a reader unifying the two tolerances
  would be unifying two different questions (DL-325).
- The tier tables, the outlier band and the outlier projection live in
  `metadata_tier.py`, which imports nothing from `traktor_nml`, so
  `splice.py`, the CLI report and the GUI report reach one definition of
  the partition and one band, and the suite reads every rule in it under
  the system interpreter (DL-069). `splice.py` takes `TRACKED_ATTRS` from
  it and keeps `_TRACKED_ATTRS` as the name `answer_detail.py` and the
  guards already import, so a second tuple of the six names cannot drift
  from the partition the tier is decided on (DL-326).
- A conflict is raised when at least one EDITORIAL attribute diverges. A
  group raising one carries every divergent attribute in `attrs`, the
  measured names included, so its CSV row, its candidates and its resolve
  rail stand as they stand and its measured divergence is never reported
  twice - once as a conflict attribute and again as a settled row. Moving
  those names out of `attrs` would drop them from `answer_fields`, which
  leaves out any attribute standing in neither `attrs` nor `agreed`
  (DL-327).
- A settled group's measured values are the base record's where the group
  holds one, and the run-wide picker's winner where it holds none. No
  entry patch is collected for it: `entry_patches` is written only where a
  resolution names a record other than base's, and a settled group is
  named by no resolution, so base keeps the numbers its own entry carries
  and a transplanted winner carries its own verbatim (DL-328).
- A settled group reports a `SettledRow` on `SpliceResult` beside
  `conflict_rows` rather than a `ConflictRow`, because a `ConflictRow`
  carrying member keys is projected into a resolve-table row, which is
  the thing being removed. The row carries the identity key, the measured
  names the group diverged on, the values each of them took across the
  members, the `(input index, primary key)` pair naming the record whose
  values the output carries - the record, never a base-or-source token
  (DL-148), and the pair rather than the key alone because both members
  of a settled group describe the one LOCATION and carry the identical
  primary key, so a key standing alone equals the identity key and says
  which record won of neither - and the group's outlier readings. The
  list is populated on every run, a clean one and an abort included, for
  the reason `conflict_rows` is (DL-008): what the rule answered is part
  of what the run did. The conflict CSV's three columns and
  `splice_cmd`'s printed conflict line stand where they are (DL-329).
- An outlier is a settled group whose gap on one measured attribute
  exceeds 1% of the larger of the two values, read per attribute and
  strictly, so a gap exactly at the band is not one. The band is not the
  conflict rule. Measured as one on a real collection pair, group-level
  survivors run 7,279 at 0.01%, 2,679 at 0.1%, 2,203 at 1% and 2,176 at
  10%: past 1% the band separates nothing, so roughly 1,650 measured
  divergences sit above any band and a band read as the rule leaves a
  screen nobody can work, while a tier holding one measured attribute
  outside it would be two rules over the one kind of fact. 1% is the
  knee, and it survives as the threshold above which a settled group is
  worth READING - the six `playtime_float` groups whose gap reaches 3,516
  seconds show as a wrong track length in Traktor until it re-analyses,
  and the listing is what names them rather than leaving them counted. A
  settled group inside the band is named nowhere, which is the price of
  the screen (DL-330).
- The settled count and the outlier listing are read off the run's own
  settled rows by both `gui/reconstruct_report.py` and
  `commands/splice_cmd.py`, so the screen and the printed run cannot
  disagree about how many decisions were made for the operator (DL-215).
  The count and the listing are one division of that one list, made in
  the report rather than in the render, for the reason `LISTED_PLAYLISTS`
  is divided there (DL-217, DL-331).
- A bound on `draw()` - a cap, a window or yielding - is out of this
  work's scope. The 9,052-row build that overran nicegui's 6s socket
  budget is 529 rows under the tier, measured at 0.64ms each, so the
  freeze goes with the rows and a bound would be defence in depth against
  a load the rule removes rather than a fix for one the tool still
  carries (DL-332).
- `reconnect_timeout` stays at its default and `gui/__main__.py` keeps
  its `ui.run` call unchanged. The default sets the ping interval and
  ping timeout the socket lives inside, so widening it lets a slower
  draw survive without making the draw faster: the threshold is not the
  fault, and moving it would hide the next one (DL-333).
- `tests/baselines/manifest.json` is untouched and no recorded CLI output
  moves. Not one of the recorded cases invokes splice, and a settled
  group produces no `ConflictRow`, so the conflict report's three
  fieldnames and its rows stand and the two counts the stats block
  carries are printed beside the ones already there (DL-334).

## Invariants

- The merged COLLECTION holds at most one entry per `LOCATION`. The
  primary key is derived from the location, so two entries for one file
  cannot be told apart and a playlist `PRIMARYKEY` naming that file
  resolves against both, so a source pick on a group base already owns
  rewrites base's entry rather than adding one beside it (DL-004).
- A held conflict pick is applied only to a group offering the same
  answers it was made against. The primary key is derived from the
  location, so two records for one file in two inputs carry one key and
  collapse into a single member of a group's `member_keys` frozenset,
  which is why that set alone cannot tell whether a pick still stands -
  the comparison DL-115 states is what holds this invariant up.
- Every entry a patch can name holds a `LOCATION` child, because
  `collection_records` skips any entry without one, so a COLLECTION
  `ENTRY` reaching the patch path is never self-closing and always
  carries a child an insertion can anchor against. An `ALBUM` or `INFO`
  child written into an entry is placed by the fixed child order
  `LOCATION`, `ALBUM`, `MODIFICATION_INFO`, `INFO` - immediately after
  the last child present that precedes it in that order, which is
  always at least `LOCATION`. Traktor writes an `ENTRY`'s children in
  that order and nothing in this tree, this corpus or Traktor's own
  documentation asserts that it reads them in any other, so an `ALBUM`
  appended after `TEMPO` would be a guess about a format whose reader
  nobody here controls; the `LOCATION` child is what makes the derived
  anchor total (DL-127).
- Every line terminator in an output is a byte copied from an input: the
  base file is read as bytes, decoded UTF-8, spliced as text and
  re-encoded UTF-8 with no newline translation on either end, and an
  inserted child copies its whitespace rather than composing it - it is
  written immediately before its anchor's following sibling, preceded by
  a verbatim copy of the whitespace byte run preceding that sibling in
  the span, or inline against the anchor's closing angle bracket where no
  such run exists. A fragment carrying a generated newline would write LF
  into a CRLF file, so the copy is what keeps an output's counts of CRLF
  and of bare LF equal to base's, an entry written on one line carries no
  line of its own, and an output's line-ending profile is its base file's
  own (DL-128).
- Every write command builds its complete output in memory and validates
  it before any file handle opens; a failure partway through conflict
  resolution or reference redirection leaves every output path untouched
  (DL-012).
- Every output file is additionally committed through a temp file plus
  `os.replace` so a destination holds either its previous bytes or the
  complete new bytes (DL-019). Split's multi-output write loop is not
  transactional across files - a failure partway through leaves earlier
  groups written - accepted because cross-file staging and commit is new
  machinery (DL-022).
- A malformed input yields `xml_parse_error` naming the file and exit code
  2 from every write command, splice and split included, never an escaping
  parser exception (DL-019).
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
- The old-side inverse of the volume-relative-to-absolute transformation
  (`volumes.py`'s `local_path_for_location`) resolves only against mount
  anchors the run established explicitly,
  returning nothing for an unknown VOLUME/VOLUMEID pair or when two
  anchors for one pair both resolve, because a guessed anchor can
  fingerprint a different file and rewrite a track onto an unrelated
  location - an extension of the DL-005 explicit-identity invariant
  above, not an exception to it (DL-017, DL-018).
- An element is located in source by tree identity through one `SpanIndex`
  per document, never by searching for an attribute value and never by a
  second locator (DL-014, DL-021).
- A split output depends only on the playlists its own group names, so an
  untouched playlist elsewhere in the document can neither pull tracks
  into a group nor fail it - what the per-output semantics above already
  imply, stated explicitly (DL-020).
- The NML schema (COLLECTION/PLAYLISTS/SUBNODES/PRIMARYKEY shapes and
  their count attributes) is confirmed only against NML VERSION=20 /
  Traktor Pro 4; `spans.py`'s count-attribute recalculation is generic
  over any counted container rather than a fixed tag list, so a counted
  container introduced by a later schema version is still recalculated
  correctly instead of being silently left stale.
- `match_records`' per-old-record loop does not stop at the first
  ambiguous tier: a tier with more than one candidate sets its ambiguous
  flag but does not break, and a later, weaker tier that lands on a
  single candidate overrides the earlier tier's ambiguity and counts as
  matched. Only a provider-returned AMBIGUOUS sentinel breaks the loop
  immediately. `build-playlist` relies on this - a tracklist line
  ambiguous at a stricter tier can still resolve at `artist_title`.

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
- Every button carries the action blue, so a screen's primary action is
  not set apart from the controls beside it by colour. It is set apart
  by weight, 600 against 500, and by `TYPE_13` against Quasar's 14px,
  which draws the primary the smaller of the two. Accepted because grey
  buttons on the ground did not read as controls, which is what the
  change answers (DL-273).

## Framework shortfalls

A Specs rule the running framework refuses is recorded here, under its
own heading, separate from the Specs-versus-section-4 precedence
statement DL-072 makes (DL-087). DL-072's precedence holds over this
section: `Specs.dc.html` governs what the operator sees and presses,
and a rule the framework refuses is a shortfall, not a resolved
precedence question. An entry names the Specs rule, the exact Quasar
selector or mechanic that won it, the rung-two `add_head_html`
declaration that was tried and lost, and its rung on DL-086's ladder.
This section is distinct from "Design-set divergences" below, which
records a value the prose supersedes, and from "Composition not built"
below, which records a structure the artboards draw and `gui/` does
not. An entry here waits on the framework admitting the rule; an entry
there waits on the work being done.

**This section holds no entries.** The browser records in
`docs/2026-08-27-m001-browser-record.md` and
`docs/2026-08-28-w002-browser-record.md` carry a matches verdict on
every surface they measure and no differs verdict at all. Each control
that first read unringed came right at rung one of DL-086's ladder,
through the framework's own mechanism rather than a stylesheet
override. "Continue to write" and the write dialog's "Write" reach the
page carrying no token class and computing 36px; attaching
`.wizard-control` settles both. The review row's Accept, Reject and
Undo buttons take `color=None` at the `ui.button` constructor, which
is what stops Quasar's `!important` `.bg-primary` outranking the
status tint class attached beside it. A shortfall entry requires a
rung-two `add_head_html` declaration that was tried and lost, and no
declaration reached rung two.

Nothing is recorded here for the measured set DL-087 bars from this
route - the ground, the five surfaces, the two borders, the
foreground, the muted and secondary text greys, the three status hues,
the action blue, any step of the type scale, the spacing steps or the
radii, or any key in Specs' keyboard map.

The evidence behind those verdicts is the value computed off the
served page, quoted in each record beside the value the artboard
fixes. Neither record names a screenshot and neither has one: the
browser pane could not be displayed in the sessions that produced
them, and the maintainer accepted computed values as the evidence for
both. `docs/2026-08-28-w002-browser-record.md` states in its own terms
that the keyboard drive-through and the screen-reader pass are
archived to a later version by the same decision, and that the
keyboard and announcement milestones' acceptance criteria are partly
unmet in consequence.

## Design-set divergences

Where a rule `Specs.dc.html` states in prose and a value the artboards
render disagree, the prose rule governs and `traktor_nml/gui/theme.py`
carries it (DL-088); a browser record measures against the prose rule,
so a surface matching the prose rule and differing from an artboard
reads matches. Each record below is keyed by selector rather than by
artboard, because `Review.dc.html` agrees with the control-height rule
at two of its own selectors and differs at a third, which an
artboard-level record cannot state. This section is distinct from
"Framework shortfalls" above, which records a rule the framework
refuses, and from "Composition not built" below, which records a
structure the artboards draw and `gui/` does not build. A divergence
here is settled - the prose won and `theme.py` carries it - while an
entry there is outstanding. It is distinct too from DL-072, which
resolves Specs against section 4 of `docs/nicegui-gui-analysis.md`.

- **Control height.** Specs' "Accessibility rules" fix controls at
  32px tall with 8px between them, every button on every screen.
  `.btn` renders 32px in `Errors.dc.html`, `Outcomes.dc.html` and
  `Review.dc.html` and 34px in `Cancelling.dc.html`,
  `Confirm.dc.html`, `Main.dc.html`, `Results.dc.html`,
  `Scanning.dc.html` and `Success.dc.html`; `.btn.sm` renders 32px
  wherever it is defined, in `Main.dc.html`, `Review.dc.html` and
  `Success.dc.html`; `.btn-pri` renders 34px in `Review.dc.html`,
  which is the only artboard giving it a height of its own.
  `theme.py`'s `CONTROL_HEIGHT` carries 32px.
- **The gap between decision buttons.** The same rule fixes 8px
  between controls. `Review.dc.html`'s `.dec` and `.decd` groups both
  render a 6px gap. `theme.py` carries the 8px step as `SPACE_8` and
  spaces the review row's decision buttons through
  `.wizard-control-group`, and
  `docs/2026-08-28-w002-browser-record.md` reads that 8px as matches
  on the strength of the prose rule.
- **The secondary text greys.** Specs names two secondary greys in its
  own token table, `#A5ADB4` at `.dim` and `#8E979E` at `.faint`, and
  requires secondary text to meet 4.5:1 against its own surface. The
  artboards paint six further text greys beyond those two, two of them
  inside `Specs.dc.html` itself. `theme.py` carries the two Specs
  names as `TEXT_MUTED` and `TEXT_FAINT` and the six others as
  `TEXT_SUBTLE_1` through `TEXT_SUBTLE_6`, so every grey the set
  paints is named once and measurable against the contrast rule.
- **The 10.5px chip.** Specs' "Accessibility rules" fix no text below
  11px. `Specs.dc.html`'s own scope-fence aside styles the words
  `build-playlist` inline at 10.5px - prose about a command outside
  Phase 1, not a step of this wizard's type scale. `theme.py`'s type
  scale carries the 11px floor, and
  `tests/test_gui_theme.py`'s `_KNOWN_UNNAMED_FONT_SIZES` excludes
  that one size by its exact value and reason rather than by a rule
  that would swallow a future token under 11px.

`traktor_nml/gui/theme.py`'s type-scale comment names the same 11px
floor this section measures against.

## Composition not built

A structure the artboards draw that `gui/` does not build is recorded
here (DL-170). This section is distinct from "Framework shortfalls"
above, which records a rule the running framework refuses, and from
"Design-set divergences" above, which records a value the prose
supersedes under DL-088. The three are told apart by what ends them: a
shortfall ends when the framework admits the rule, a divergence is
already settled and ends never, and an entry here ends by being built.
An entry names the structure, the artboard file and selector it is
read from, and what `gui/` composes in its place.

Each entry names the route and the artboard it is read against. The
three below are read against the reconnect wizard's artboards, and the
reconstruct page's own column model, table geometry and detail rail are
read against `Resolve.dc.html` and its three siblings on canvas page 3:
the two sets are different geometries on different routes, so an entry
ending for one ends nothing for the other (DL-200, DL-201).

An entry ends by being built and read off a served page, not by being
excused; where a run reads a structure only partly built, the entry is
narrowed to what the framework refused rather than struck (DL-190,
DL-194).

Three structures the artboards draw carry no entry here, each read
built in `docs/2026-09-07-composition-close-browser-record.md`, the
record taken with those entries already absent from this section: the
app shell, on the `56px` header, the `64px` footer and the middle at
the full `1280px` between them, with the document not scrolling on
either route and the middle scrolling on `/reconnect`; the card
structure, on the four named cards the record reads on `/` and the one
per rendered step it reads on `/reconnect`, each carrying its head, its
title and its body; and the footer band, on the note at `x=24` and the
visible actions at the right on both routes. Column model, Table
geometry and Detail rail are the three that stand, and that record
reads each of them `differs`: there is one column and no second column
on either route, the review table is `.wizard-row`, a flex row with a
gap and no header row, and no element composes a rail - the candidate
panel is in the same column below the table. Each of those three
entries states beneath it the reason it is open.

- **Column model.** `main` is `grid-template-columns: 1fr 400px` in
  `Main.dc.html`, `1fr 404px` in `Confirm.dc.html` and `1fr 384px` in
  `Results.dc.html`, a content column beside a guidance rail.
  `theme.py` emits no two-column rule, and every page composes one
  column at `.wizard-content-width`.
  This entry stands as written: the two-column `main` is outside this
  work's scope, and `main` is one column at `.wizard-content-width`
  (DL-191).
- **Table geometry.** `.gr` in `Review.dc.html` is
  `grid-template-columns: 126px minmax(0, 1fr) 100px 196px 134px`
  under a `.th` header row. `theme.py` emits `.wizard-row`, a flex row
  with a gap and a zebra ground, so cells take their width from their
  content and no column aligns from one row to the next, and neither
  table carries a header row.
  This entry stands as written: the review table's grid geometry and
  its header row are outside this work's scope (DL-191).
- **Detail rail.** `.det` in `Review.dc.html` is a 400px bordered
  panel with its own header, body and footer holding the candidate
  cards. `theme.py` emits no rail rule for the reconnect wizard's
  review table, and `/reconnect` renders its candidate panel below the
  table in the same column.
  This entry stands as written: the reconnect wizard's detail rail is
  outside this work's scope (DL-191, DL-201).

Three structures the reconstruct page's own artboards draw carry no
entry here, each read built in
`docs/2026-09-10-composition-strike-browser-record.md`, the record taken
with those entries already absent from this section (DL-190): the
reconstruct column model, on `.wizard-resolve-split` resolving to a
content column beside a 400px rail, as `Resolve.dc.html:53`'s `.split`
draws it; the reconstruct table geometry, on `.wizard-conflict-grid`
resolving to the five tracks `Resolve.dc.html:55`'s `.gr` draws, with
`.wizard-conflict-header` standing over the same tracks as every body
row; and the reconstruct detail rail, on `.wizard-detail-rail` resolving
to 400px and carrying the head, body and footer `Resolve.dc.html:70`,
`:71`, `:74` and `:105` draw. The four-step rail and the four step
regions those structures sit under are read in
`docs/2026-09-09-reconstruct-resolve-browser-record.md`, the record the
milestone that built them closed on (DL-200, DL-201).

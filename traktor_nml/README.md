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
level selector, since a track list carrying only artist and title leaves
every stricter tier unreachable (DL-032).

`traktor_nml.gui` is a fourth package alongside `traktor_nml`,
`traktor_nml.commands` and `traktor_nml.gui`'s own three framework
modules; `[tool.setuptools] packages` in `pyproject.toml` lists it
explicitly (`packages = ["traktor_nml", "traktor_nml.commands",
"traktor_nml.gui"]`), since that array is not automatic discovery and a
package absent from it imports fine from a source checkout while missing
from an installed wheel (DL-070). Within the package, `review_model.py`
and `wizard_state.py` import no `nicegui` or `pywebview` and are reachable
from the test suite's system interpreter; `app.py`, `file_picker.py` and
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
  check may refute it, and whether it works without readable tags. Those
  properties used to live in five hand-synchronised string tuples that
  nothing checked against each other. The confidence ladder in
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
  text-only track list carries only artist and title, making every tier
  above `artist_title` structurally unreachable for it (DL-032).
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
  recorded in `traktor_nml/gui/CLAUDE.md` rather than one document being
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
- The token set is one dark theme; no light variant and no theme
  switcher. All ten artboards paint the same `#0F1113` ground and
  Specs states its contrast results against those surfaces; a light
  variant is a second palette owing its own colour-blindness
  simulation, design work Specs does not do (DL-085).
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
  record aborts the whole write with the ambiguity reported, since no
  single base key is the right redirect target and folding it in would
  guess which base track the entry meant. `_resolve_conflicts` returns
  those keys as a named element of its result rather than raising: the
  merge itself is unaffected and only reconstruction treats them as
  fatal (DL-094, DL-100).
- Reconstruction is opt-in behind `--reconstruct-playlists`, and the
  `"<name> (2)"` rename stays the default. Reconstruction changes the
  shape of an existing caller's output rather than adding to it, so
  defaulting it on would rewrite results for invocations that never
  asked for it (DL-095).
- The base source text is rewritten in memory and re-parsed before any
  span is consumed, keeping reconstruction on the byte-span assembly path
  DL-007 separates from attribute patching. Replacements are applied
  end-first so each span offset stays valid against the text it was
  measured in, and every byte outside a rebuilt `PLAYLIST` element is
  still copied verbatim (DL-096, DL-102).
- Playlist name matching is exact and case-sensitive. Traktor treats two
  names differing only in case as distinct playlists, so a casefolded
  lookup would rebuild one from the other and leave the same track
  reachable through both (DL-098).
- A `NAME` occurring more than once within one document, on either side,
  aborts with nothing written rather than resolving by document order.
  Counting is per contribution rather than across them: one name
  appearing in several `--input` files is the fold DL-092 asks for, while
  the same name twice inside one file offers no single playlist to
  reconstruct or to reconstruct from (DL-098).
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

## Invariants

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

## Framework shortfalls

A Specs rule the running framework refuses is recorded here, under its
own heading, separate from the Specs-versus-section-4 precedence
statement DL-072 makes (DL-087). DL-072's precedence holds over this
section: `Specs.dc.html` governs what the operator sees and presses,
and a rule the framework refuses is a shortfall, not a resolved
precedence question. An entry names the Specs rule, the exact Quasar
selector or mechanic that won it, the rung-two `add_head_html`
declaration that was tried and lost, and its rung on DL-086's ladder.

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
refuses, and from DL-072, which resolves Specs against section 4 of
`docs/nicegui-gui-analysis.md`.

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

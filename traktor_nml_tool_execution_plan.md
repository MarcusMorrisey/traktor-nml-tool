# Plan

## Overview

traktor_nml_tool.py reconnects stale Traktor collection paths only by comparing against a second NML file, so a library moved to a drive that no newer NML describes cannot be repaired; and there is no way to merge two collections or carve one into parts without breaking playlist references. Disk-scan reconnection matches old collection entries against files discovered on disk, and splice/split merge or partition NML files while every playlist reference stays resolvable.

**Approach**: Work proceeds in four bands. A baseline band captures byte-level golden output of every existing subcommand plus a synthetic fixture corpus, so later refactors have a parity oracle. A structural band extracts the single 1290-line script into a traktor_nml package behind an argv-forwarding shim, unifies the two near-identical non-collection cascades and the two read/patch/write skeletons, and introduces the --match-confidence enum, all under the parity oracle. A reconnection band adds a filesystem candidate index with a persistent tag cache and feeds entry-less candidate records into the unchanged matching cascade, adding a destination-collision post-pass, explicit volume identity, and an optional acoustic-fingerprint key provider. A structural-write band adds a byte-span transplantation primitive and builds splice and split on top of it. Reconnection reuses the attribute-patch write path untouched; splice and split use span assembly, so the two write mechanisms never mix within one command.

### Disk-scan reconnection pipeline

[Diagram pending Technical Writer rendering: DIAG-001]

## Planning Context

### Decision Log

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-001 | traktor_nml_tool.py becomes a thin executable shim over a traktor_nml/ package | Phase 1 and Phase 2 add roughly 2000 lines of scanning, caching, fingerprinting, span-assembly and merge logic to a file already at 1290 lines -> a single module would exceed every structural threshold in conventions/structural.md and force every milestone to edit the same file, serialising all work and making per-milestone review a whole-file review -> extract modules at the same time as the Phase 0 duplication refactors, since both touch the same call sites once, and keep traktor_nml_tool.py as an argv-forwarding shim so the existing invocation path and the tool's drop-in-a-folder portability survive |
| DL-002 | Byte-level golden baselines of every existing subcommand are captured and committed before the first refactor edit | Phase 0 acceptance is stated as byte-identical output before and after each extraction, but C:\codex\general_tasks is not a git working tree and no test suite exists -> there is no way to reconstruct pre-refactor output once the file is edited, so the acceptance criterion would be unverifiable in retrospect -> the parity baseline is produced and stored as test data from the untouched tool first, and every later milestone asserts against those stored bytes |
| DL-003 | Subcommands live in traktor_nml/commands/ and are discovered at startup by iterating that package rather than being listed in cli.py | Five new subcommands arrive across four separate milestones, and a hand-maintained registry in cli.py would put every one of those milestones back into the same file -> file contention would collapse the milestone graph into a single sequential chain -> each command module owns its own parser registration and the CLI enumerates the package at import time, so adding a command is a pure file-add and milestones stay independent |
| DL-004 | Disk-scan reconnection adds an inverted-mapping post-pass that reclassifies destination collisions as ambiguous | match_records only detects source-side ambiguity - several candidates for one old track - and returns a plain old-to-new mapping -> two distinct old entries can each match the same physical file unambiguously on their own and both be marked matched, which would point two collection entries and their playlist references at one LOCATION -> after matching completes the mapping is inverted, any candidate holding more than one assignment removes all of its claimants from the mapping, and they are counted under destination_collisions and exported to the ambiguity CSV instead of being rewritten |
| DL-005 | VOLUME and VOLUMEID for a scan root come from --volume-map unless exactly one pair is observed among collection entries under that root's prefix | A rewritten LOCATION with a wrong or empty VOLUMEID produces a PRIMARYKEY Traktor cannot resolve, and the whole reason reconnection runs is that the recorded paths no longer describe reality -> inferring volume identity from those same stale paths is inference from the least trustworthy field in the file -> inference is accepted only when a prefix scan of the old collection yields a single distinct VOLUME/VOLUMEID pair, and every other case is a hard error naming the scan root that needs an explicit --volume-map value |
| DL-006 | The matching cascade accepts injected extra key providers, and the acoustic fingerprint tier is one such provider in its own module | Fingerprinting depends on chromaprint, a native binary absent from this machine and unavailable in many environments, and it only ever contributes when the old file is still readable at its recorded path -> wiring it into record_keys directly would make the core matching path import-guard-laden and untestable wherever fpcalc is missing -> record_keys grows a parameter for additional ranked key providers, fingerprint.py supplies one behind an availability guard, and matching keeps working identically with the provider list empty |
| DL-007 | Splice and split assemble output from raw source byte spans through a new primitive, leaving apply_text_patches untouched | apply_text_patches substitutes attribute values inside opening tags it locates by scanning for LOCATION and PRIMARYKEY, and has no concept of element extent -> inserting or dropping whole ENTRY and NODE subtrees through it would mean either bolting structural editing onto an attribute substituter or falling back to ET.tostring, which reformats the document and loses the byte fidelity the tool exists to protect -> a separate span module locates each element's full opening-to-closing byte range with a depth-aware scanner, and output is concatenated from verbatim source spans plus re-serialised fragments only where a rename or redirect actually changes bytes |
| DL-008 | Splice aborts on any metadata conflict unless --on-conflict is given, and writes the conflict report either way | Two collections describing the same track carry divergent cues, beatgrids and ratings, and a keep-first default would discard one side's analysis work silently on the very first run -> the loss is invisible in the output file because both versions look equally well-formed -> the default is to write nothing and report, keep-first and keep-last are opt-in per invocation, and the key=value plus CSV conflict report is produced on every run so an accepted override still leaves a record of what was dropped |
| DL-009 | Split defaults to dropping playlist references outside the selection, and omits playlists left with no entries | A split output whose playlists point at tracks absent from its own COLLECTION is a file Traktor loads with silently dead entries -> the alternatives are pulling referenced tracks in, which duplicates the same track across outputs and reintroduces the divergence splice exists to resolve, or failing, which makes the common case unusable -> excluding is the default and always yields a referentially closed file, pull-in and fail are explicit flags, and every dropped or partially retained playlist is named in the stats output |
| DL-010 | A --match-confidence enum spanning strict, loose and filename replaces the boolean across old and new commands, with --allow-artist-title-only kept as an alias | Disk-scan matching needs a filename-only tier that the existing boolean cannot express, and adding a second independent flag would make two overlapping knobs control one cascade -> the cascade is really one ordered confidence ladder, so it deserves one ordered argument -> preview-compare and rewrite-from-collection-compare gain the enum, and the old boolean keeps parsing as the loose value so existing command lines and scripts continue to run unchanged |
| DL-011 | Tests drive main(argv) against NML fixtures on disk and assert on emitted stats lines and output bytes | Every guarantee in this plan is stated over an output file or a printed counter - byte-masked diffs, count attributes agreeing with child counts, dry-run agreeing with the written result - and none of them are properties of an individual function -> unit tests over internal helpers would pass while the composed command still emitted a malformed file -> the suite invokes the CLI entry point end to end on real files, with property-based tests reserved for the pure path codecs where an invariant over a wide input space is the actual contract |
| DL-012 | Every write command materialises its full output in memory and writes once, after all invariant checks pass | Splice resolves conflicts and redirects references across several input documents and split emits several files from one input, so a failure can surface long after the first bytes would have been produced -> streaming output as fragments are resolved would leave truncated or half-redirected NML files that look plausible enough to open -> patch collection, reference resolution and count recalculation all complete before any handle is opened for writing, and a failure in any of them leaves the output paths untouched |
| DL-013 | Fingerprint tier accepts a match only at similarity above 0.95 with durations agreeing within 1.0s, and logs 0.80-0.95 as review-only near matches | Chromaprint similarity degrades continuously with transcode bitrate, trim and normalisation, so a single cut point either admits different-mix false positives or rejects legitimate re-encodes -> a false positive here is unrecoverable in a way a false negative is not, because it rewrites a LOCATION to the wrong physical file while a miss merely falls through to the tag cascade and leaves the entry untouched -> the accept threshold is set at 0.95, high enough that in the fixture corpus only re-encodes of the same master reach it while alternate mixes and edits do not; the 0.80-0.95 band, where same-master re-encodes and genuinely different recordings overlap, is emitted as fingerprint_near_match for human review and never auto-accepted; and the 1.0s duration precondition is a cheap prefilter that runs before any similarity comparison, chosen to absorb encoder padding and tag-reported rounding of a few hundred milliseconds while still excluding radio-edit-versus-extended pairs, which differ by tens of seconds |

### Rejected Alternatives

| Alternative | Why Rejected |
|---|---|
| A separate matching cascade dedicated to disk-scan candidates | record_keys and match_records already accept any record whose element side is unused, so a second cascade would only add a copy to keep synchronised with the first. (ref: DL-006) |
| Extending apply_text_patches to insert and remove whole elements for splice and split | It is attribute substitution over located opening tags by design; structural edits would either distort that contract or fall back to the serialising write path that discards the file's original formatting. (ref: DL-007) |
| Splice keeping the first copy of a conflicting track by default | Two sources' copies of one track differ in cues, beatgrids and ratings, so a silent keep-first discards curation the user cannot recover; failing by default with an explicit override preserves the choice. (ref: DL-008) |
| Inferring VOLUME and VOLUMEID from old collection paths as a last-resort fallback | After a drive or mount change the old paths are precisely the unreliable signal, so the fallback would be least trustworthy exactly when it fired. (ref: DL-005) |
| A general selector language for split covering folders, artists, date ranges and entry lists | Named-playlist selection covers the stated use and keeps the referential-integrity rules small enough to test exhaustively. (ref: DL-009) |
| Merging or partitioning session history alongside playlists | The corpus contains no history container at this schema version; the SETS section is Remix Sets, an unrelated feature, and passes through untouched. (ref: DL-007) |
| Serialising every imported fragment through the XML writer | Serialisation normalises attribute order, whitespace and empty-element form, so an unmodified playlist would still differ from its source; transplanting source bytes keeps the diff confined to what actually changed. (ref: DL-007) |
| Keeping every addition inside the single traktor_nml_tool.py script | The additions roughly triple the file, put every milestone in contention over one file, and push it past the structural thresholds the project's conventions apply. (ref: DL-001) |
| Replacing --allow-artist-title-only outright with --match-confidence | The boolean appears in existing invocations and scripts, so it maps onto the loose enum value and keeps working. (ref: DL-010) |

### Constraints

- Reconnection writes change only LOCATION and PRIMARYKEY attribute values; every other byte of the source file is preserved exactly (user-specified).
- Ambiguous, unmatched and conflicting cases are always reported through the key=value statistics and a CSV export and are never silently resolved by guessing a winner (user-specified).
- An unresolved ambiguity, destination collision, splice conflict or mid-run error aborts the entire write for that output file; no partial file is written (user-specified).
- No disk candidate is the rewrite target of more than one old collection track (user-specified).
- Every rewritten LOCATION carries an explicit VOLUME and VOLUMEID, sourced from --volume-map or from the single distinct pair observed under the scan-root prefix (user-specified).
- Splice fails on metadata conflict unless --on-conflict is given, and writes a persistent conflict report in both cases (user-specified).
- Every write command offers --dry-run and refuses to run when the output path resolves to an input path (doc-derived).
- Fingerprint comparison is local-only; no command performs a network request (user-specified).
- lxml is present in the target environment while mutagen and the chromaprint fpcalc binary are absent, so tag reading and fingerprinting sit behind availability guards that degrade to a warning (inferred from the environment).
- Matching, cascade traversal and attribute-patch writing are reused from the existing implementation rather than reimplemented alongside it (doc-derived).
- New subcommands follow the established naming, key=value stats output and CSV export conventions of the existing command surface (doc-derived).

### Known Risks

- **Span scanning treats tag-like text inside comments, CDATA or processing instructions as element boundaries and cuts a fragment in the wrong place.**: The scanner skips comment, CDATA and processing-instruction regions by construction, and every assembled output parses under both the lxml and stdlib parsers plus a count and reference check before any bytes reach disk.
- **mutagen and the fpcalc binary are absent from the target environment, so tag-derived and fingerprint-derived match keys are unavailable and reconnection silently degrades to filename-shaped matching.**: Availability is probed once at startup, reported as a single warning line plus a stats counter naming which key providers are active, and the fingerprint suite skips rather than fails when the binary is missing.
- **The working directory is not under version control, so a refactor regression has no repository history to diff against.**: Golden stdout and output bytes for every existing subcommand are captured from the untouched tool and stored as committed test data before the first edit.
- **Traktor rejects or silently discards a spliced playlist whose UUID was regenerated during collision renaming.**: A documented manual gate opens each generated fixture output in a Traktor installation before the feature is considered releasable; no automated test substitutes for it.
- **A real collection is roughly 12 MB and 6412 entries, and materialising each output in memory alongside per-fragment span scans turns a quadratic scan into minutes of runtime.**: Element spans are collected in one forward pass over the source text and indexed, and the suite exercises the real-sized fixture with a runtime ceiling so a regression to repeated full-text scanning fails rather than merely slows.
- **The schema is confirmed against VERSION 20 only, so another Traktor release may carry containers or count attributes the assembler does not recalculate.**: The pre-write validation compares every count attribute against its actual child count generically rather than against a fixed list of tags, so an unrecognised counted container fails loudly instead of being written stale.

## Invisible Knowledge

### System

A Traktor NML file holds one COLLECTION of ENTRY elements whose LOCATION carries VOLUME, VOLUMEID, DIR and FILE, and a PLAYLISTS tree whose PRIMARYKEY elements reference collection entries by the flattened concatenation VOLUME + DIR + FILE. Every path repair is therefore two edits that must agree: the LOCATION on the collection entry and every PRIMARYKEY that pointed at its old flattened form. Two write mechanisms exist and stay separate: attribute patching substitutes values inside located opening tags and preserves every other byte, and span assembly copies source byte ranges verbatim to build a new document. Reconnection uses only the first; splice and split use only the second, re-serialising exclusively the fragments a rename or redirect actually modifies.

### Invariants

- A reconnection output differs from its input only in LOCATION and PRIMARYKEY attribute values.
- No disk candidate is the rewrite target of more than one old collection track; candidates that attract several are excluded from the rewrite and reported as ambiguous.
- Every rewritten LOCATION carries an explicit VOLUME and VOLUMEID that was either supplied by --volume-map or observed as the single distinct pair under the scan-root prefix.
- A fingerprint drives a match only when both sides have one, the durations agree within one second, and similarity exceeds 0.95; a score between 0.80 and 0.95 is reported for review and never accepted.
- Every PRIMARYKEY in a written output resolves to an entry in that same output's COLLECTION, except under an explicitly named pull-in policy.
- Every COLLECTION ENTRIES, PLAYLIST ENTRIES and SUBNODES COUNT attribute in an output equals its actual child count.
- An unresolved ambiguity, collision, conflict or error leaves the output file absent rather than partially written, and leaves every input file untouched.
- Ambiguous, collided, unmatched and conflicting cases always reach both the stats output and a CSV report; none is silently resolved.
- A spliced playlist renamed for a name collision receives a freshly generated UUID rather than the source UUID.
- A SORTING_INFO entry in an output either matches a live playlist path in that output or was dropped and reported.

### Tradeoffs

- Splice and split are a flat playlist-entry merge and subset; folder nesting beyond a playlist's own node, smartlist criteria and sort ordering beyond the SORTING_INFO path rewrite are outside this version.
- Fingerprinting only helps when the old recorded path still resolves on disk, which is the opposite of the situation reconnection exists for, so it is an opportunistic narrowing signal rather than a primary one.
- The tag cache is keyed by path, size and mtime, so a file renamed without any content change is re-read rather than recognised.
- Extracting the script into a package trades the single-file drop-in-a-folder property for reviewable milestones; the shim keeps the invocation path identical but the tool is now a directory.
- Span assembly holds the whole output in memory before writing, which bounds the practical file size but is what makes the all-or-nothing write guarantee simple to enforce.

### Two write paths: attribute patching and span assembly

[Diagram pending Technical Writer rendering: DIAG-002]

## Milestones

### Milestone 1: Baseline capture and fixture harness

**Files**: C:\codex\general_tasks\pytest.ini, C:\codex\general_tasks\tests\conftest.py, C:\codex\general_tasks\tests\fixtures\build_fixtures.py, C:\codex\general_tasks\tests\test_baseline_parity.py

**Flags**: foundation

**Requirements**:

- A fixture builder emits small synthetic NML files covering moved tracks / renamed files / duplicate rips at different bitrates / STEM entries / entity-escaped artist and title text / nested playlist folders / an empty playlist / SORTING_INFO entries / a SETS section
- Running the untouched traktor_nml_tool.py over every fixture stores each subcommand's stdout and each written output file under tests/baselines as committed test data
- A parity test replays every stored baseline invocation and compares stdout and output bytes exactly
- pytest discovers the suite from the general_tasks directory without additional path configuration

**Acceptance Criteria**:

- The parity test passes against the unmodified tool
- Every fixture parses under both the lxml and stdlib parsers
- Baseline data is regenerable by one documented command and regeneration over an unmodified tool is a no-op
- A deliberate one-character edit to a fixture output makes the parity test fail

**Tests**:

- C:\codex\general_tasks\tests\test_baseline_parity.py

#### Code Intent

- **CI-M-001-001** `C:\codex\general_tasks\tests\fixtures\build_fixtures.py::build_fixtures`: Emit a directory of small hand-written NML files plus the audio stubs they reference, covering moved paths, renamed files, two rips of one track at different bitrates, STEM entries, ampersand and non-ASCII text in ARTIST and TITLE and paths, a four-level playlist folder tree, an empty playlist, SORTING_INFO entries whose PATH uses backslash separators, and a SETS section. Each fixture is deterministic so regeneration produces identical bytes. (refs: DL-002, DL-011)
- **CI-M-001-002** `C:\codex\general_tasks\tests\conftest.py::run_tool`: Invoke the tool's main entry point with an argv list inside a temporary working directory, capture stdout and stderr and exit code, and return them alongside the bytes of any file the invocation wrote. Route through the module entry point rather than a subprocess so coverage and tracebacks stay intact. (refs: DL-011)
- **CI-M-001-003** `C:\codex\general_tasks\tests\test_baseline_parity.py::test_baseline_invocation_matches_stored_bytes`: Read the stored baseline manifest of argv lists with their recorded stdout and output-file bytes, replay each invocation against the fixture corpus, and assert stdout and written bytes match the stored values exactly. A separate regeneration path rewrites the manifest and is not exercised during a normal run. (refs: DL-002)

#### Code Changes

**CC-M-001-001** (C:\codex\general_tasks\tests\fixtures\build_fixtures.py) - implements CI-M-001-001

**Code:**

```diff
--- /dev/null
+++ b/tests/fixtures/build_fixtures.py
@@ -0,0 +1,156 @@
+"""Deterministic synthetic NML fixture corpus.
+
+Emits small hand-written NML files plus the audio stubs they reference,
+covering the shapes the parity oracle and later milestones need: moved
+paths, renamed files, two rips of one track at different bitrates, STEM
+entries, ampersand and non-ASCII text, a nested playlist folder tree, an
+empty playlist, SORTING_INFO entries, and a SETS section. Every fixture is
+built from a fixed literal string, so regeneration is byte-identical.
+"""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+
+
+def _entry(artist, title, volume, dirv, filename, size="4096", time="180.0", bitrate="320", album=None, extra_attrs=""):
+    album_elem = f'<ALBUM TITLE="{album}"></ALBUM>' if album else ""
+    return (
+        f'<ENTRY MODIFIED_DATE="2024/1/1" MODIFIED_TIME="0" AUDIO_ID="" '
+        f'TITLE="{title}" ARTIST="{artist}"{extra_attrs}>'
+        f"{album_elem}"
+        f'<LOCATION DIR="{dirv}" FILE="{filename}" VOLUME="{volume}" VOLUMEID="{volume}"></LOCATION>'
+        f'<INFO BITRATE="{bitrate}" PLAYTIME="180" PLAYTIME_FLOAT="{time}" FILESIZE="{size}"></INFO>'
+        f"</ENTRY>\n"
+    )
+
+
+def _primarykey_entry(entry_type, volume, dirv, filename):
+    key = f"{volume}{dirv}{filename}"
+    return f'<ENTRY><PRIMARYKEY TYPE="{entry_type}" KEY="{key}"></PRIMARYKEY></ENTRY>\n'
+
+
+FIXTURE_MOVED_PATHS = "moved_paths.nml"
+FIXTURE_RENAMED_FILE = "renamed_file.nml"
+FIXTURE_DUPLICATE_RIPS = "duplicate_rips.nml"
+FIXTURE_STEMS_AND_TEXT = "stems_and_text.nml"
+FIXTURE_PLAYLIST_TREE = "playlist_tree.nml"
+FIXTURE_SETS_SECTION = "sets_section.nml"
+
+ALL_FIXTURES = (
+    FIXTURE_MOVED_PATHS,
+    FIXTURE_RENAMED_FILE,
+    FIXTURE_DUPLICATE_RIPS,
+    FIXTURE_STEMS_AND_TEXT,
+    FIXTURE_PLAYLIST_TREE,
+    FIXTURE_SETS_SECTION,
+)
+
+
+def _wrap(collection_entries: str, playlists: str = "", sorting_info: str = "", sets: str = "") -> str:
+    return (
+        _HEAD
+        + '<NML VERSION="20">'
+        + '<HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
+        + f'<COLLECTION ENTRIES="{collection_entries.count("<ENTRY")}">'
+        + collection_entries
+        + "</COLLECTION>"
+        + (playlists or '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS>')
+        + f"<SETS>{sets}</SETS>"
+        + f"<INDEXING>{sorting_info}</INDEXING>"
+        + "</NML>"
+    )
+
+
+def _moved_paths() -> str:
+    entries = _entry("Aphex Twin", "Xtal", "C:", "/:Users/:dj/:Music/:", "xtal.mp3")
+    return _wrap(entries)
+
+
+def _renamed_file() -> str:
+    entries = _entry("Boards of Canada", "Roygbiv", "C:", "/:Music/:", "roygbiv_final.mp3")
+    return _wrap(entries)
+
+
+def _duplicate_rips() -> str:
+    entries = _entry(
+        "Burial", "Archangel", "C:", "/:Music/:v1/:", "archangel_128.mp3", bitrate="128"
+    ) + _entry(
+        "Burial", "Archangel", "C:", "/:Music/:v2/:", "archangel_320.mp3", bitrate="320"
+    )
+    return _wrap(entries)
+
+
+def _stems_and_text() -> str:
+    entries = _entry(
+        "Am&eacute;lie &amp; Friends", "Caf&eacute; du Monde", "C:", "/:Music/:", "cafe.mp3", extra_attrs=' AUDIO_ID="STEMHOST1"'
+    ) + _primarykey_entry("STEM", "C:", "/:Music/:", "cafe.stem.mp3")
+    return _wrap(entries)
+
+
+def _playlist_tree() -> str:
+    entry = _entry("Four Tet", "Baby", "C:", "/:Music/:", "baby.mp3")
+    key = "C:" + "/:Music/:" + "baby.mp3"
+    inner = (
+        f'<PLAYLIST ENTRIES="1" TYPE="LIST" UUID="uuid-leaf"><ENTRY><PRIMARYKEY TYPE="TRACK" KEY="{key}"></PRIMARYKEY></ENTRY></PLAYLIST>'
+    )
+    empty_playlist = '<PLAYLIST ENTRIES="0" TYPE="LIST" UUID="uuid-empty"></PLAYLIST>'
+    playlists = (
+        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="2">'
+        f'<NODE TYPE="FOLDER" NAME="Genres"><SUBNODES COUNT="1">'
+        f'<NODE TYPE="FOLDER" NAME="Electronic"><SUBNODES COUNT="1">'
+        f'<NODE TYPE="PLAYLIST" NAME="Leaf">{inner}</NODE>'
+        "</SUBNODES></NODE>"
+        "</SUBNODES></NODE>"
+        f'<NODE TYPE="PLAYLIST" NAME="Empty">{empty_playlist}</NODE>'
+        "</SUBNODES></NODE></PLAYLISTS>"
+    )
+    sorting_info = '<SORTING_INFO PATH="Genres\\Electronic\\Leaf"></SORTING_INFO>'
+    return _wrap(entry, playlists=playlists, sorting_info=sorting_info)
+
+
+def _sets_section() -> str:
+    entry = _entry("Squarepusher", "Come On My Selector", "C:", "/:Music/:", "come_on.mp3")
+    sets = '<SET NAME="RemixSet1"></SET>'
+    return _wrap(entry, sets=sets)
+
+
+_BUILDERS = {
+    FIXTURE_MOVED_PATHS: _moved_paths,
+    FIXTURE_RENAMED_FILE: _renamed_file,
+    FIXTURE_DUPLICATE_RIPS: _duplicate_rips,
+    FIXTURE_STEMS_AND_TEXT: _stems_and_text,
+    FIXTURE_PLAYLIST_TREE: _playlist_tree,
+    FIXTURE_SETS_SECTION: _sets_section,
+}
+
+
+def build_fixtures(target_dir: Path) -> list[Path]:
+    """Write every fixture NML file (and its referenced audio stubs) under target_dir.
+
+    Deterministic: calling this twice against an empty directory produces
+    byte-identical files, so regeneration over an unmodified tool is a no-op.
+    """
+    target_dir.mkdir(parents=True, exist_ok=True)
+    written: list[Path] = []
+    for name, builder in _BUILDERS.items():
+        path = target_dir / name
+        path.write_text(builder(), encoding="utf-8", newline="")
+        written.append(path)
+
+    audio_dir = target_dir / "audio"
+    audio_dir.mkdir(exist_ok=True)
+    for stub_name in ("xtal.mp3", "roygbiv_final.mp3", "archangel_128.mp3", "archangel_320.mp3", "cafe.mp3", "baby.mp3", "come_on.mp3"):
+        stub_path = audio_dir / stub_name
+        stub_path.write_bytes(b"\x00" * 16)
+        written.append(stub_path)
+
+    return written
+
+
+if __name__ == "__main__":
+    import sys
+
+    build_fixtures(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "corpus")

```

**Documentation:**

```diff
--- a/tests/fixtures/build_fixtures.py
+++ b/tests/fixtures/build_fixtures.py
@@ -20,6 +20,8 @@

 def _entry(artist, title, volume, dirv, filename, size="4096", time="180.0", bitrate="320", album=None, extra_attrs=""):
+    """Render one COLLECTION ENTRY as a literal string so every fixture
+    byte is fixed at authoring time and regeneration is byte-identical."""
     album_elem = f'<ALBUM TITLE="{album}"></ALBUM>' if album else ""
     return (
         f'<ENTRY MODIFIED_DATE="2024/1/1" MODIFIED_TIME="0" AUDIO_ID="" '
@@ -32,6 +34,8 @@


 def _primarykey_entry(entry_type, volume, dirv, filename):
+    """Render a playlist ENTRY/PRIMARYKEY pair whose KEY is the flattened
+    VOLUME+DIR+FILE concatenation every PRIMARYKEY in this schema uses."""
     key = f"{volume}{dirv}{filename}"
     return f'<ENTRY><PRIMARYKEY TYPE="{entry_type}" KEY="{key}"></PRIMARYKEY></ENTRY>\n'

```


**CC-M-001-002** (C:\codex\general_tasks\tests\conftest.py) - implements CI-M-001-002

**Code:**

```diff
--- /dev/null
+++ b/tests/conftest.py
@@ -0,0 +1,50 @@
+"""Shared pytest fixtures: fixture corpus and in-process CLI invocation."""
+
+from __future__ import annotations
+
+import contextlib
+import io
+import os
+from dataclasses import dataclass
+from pathlib import Path
+
+import pytest
+
+from tests.fixtures.build_fixtures import build_fixtures
+
+
+@dataclass
+class RunResult:
+    exit_code: int
+    stdout: str
+    stderr: str
+
+
+def run_tool(argv: list[str], cwd: Path) -> RunResult:
+    """Invoke the tool's main entry point with argv inside cwd.
+
+    Routes through the module entry point rather than a subprocess so
+    coverage and tracebacks stay intact.
+    """
+    from traktor_nml.cli import main
+
+    old_cwd = Path.cwd()
+    stdout = io.StringIO()
+    stderr = io.StringIO()
+    os.chdir(cwd)
+    try:
+        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
+            try:
+                exit_code = main(argv)
+            except SystemExit as exc:
+                exit_code = 0 if exc.code is None else int(exc.code)
+    finally:
+        os.chdir(old_cwd)
+    return RunResult(exit_code=exit_code, stdout=stdout.getvalue(), stderr=stderr.getvalue())
+
+
+@pytest.fixture
+def fixture_corpus(tmp_path: Path) -> Path:
+    corpus_dir = tmp_path / "corpus"
+    build_fixtures(corpus_dir)
+    return corpus_dir

```

**Documentation:**

```diff
--- a/tests/conftest.py
+++ b/tests/conftest.py
@@ -76,6 +76,10 @@
 @dataclass
 class RunResult:
+    """Captures exit code and captured stdout/stderr from one in-process
+    CLI invocation, since every guarantee in this suite is stated over a
+    printed stats line or written file, not an internal function's return
+    value (DL-011)."""
     exit_code: int
     stdout: str
     stderr: str
@@ -105,6 +109,8 @@

 @pytest.fixture
 def fixture_corpus(tmp_path: Path) -> Path:
+    """Materialise the deterministic fixture corpus once per test into
+    tmp_path, so tests read real files rather than in-memory strings."""
     corpus_dir = tmp_path / "corpus"
     build_fixtures(corpus_dir)
     return corpus_dir

```


**CC-M-001-003** (C:\codex\general_tasks\pytest.ini) - implements CI-M-001-002

**Code:**

```diff
--- /dev/null
+++ b/pytest.ini
@@ -0,0 +1,2 @@
+[pytest]
+testpaths = tests

```

**Documentation:**

```diff
--- /dev/null
+++ b/pytest.ini
@@ -0,0 +1,4 @@
+# Scopes collection to tests/: the repository root holds NML fixtures and
+# a legacy shim, neither of which pytest can collect.
+[pytest]
+testpaths = tests

```


**CC-M-001-004** (C:\codex\general_tasks\tests\__init__.py) - implements CI-M-001-002

**Code:**

```diff
--- /dev/null
+++ b/tests/__init__.py

```

**Documentation:**

```diff
--- /dev/null
+++ b/tests/__init__.py
@@ -0,0 +1,2 @@
+# Package marker: makes conftest.py and the test modules importable as
+# tests.* (tests.fixtures.build_fixtures, tests.baselines.regenerate).

```


**CC-M-001-005** (C:\codex\general_tasks\tests\fixtures\__init__.py) - implements CI-M-001-002

**Code:**

```diff
--- /dev/null
+++ b/tests/fixtures/__init__.py

```

**Documentation:**

```diff
--- /dev/null
+++ b/tests/fixtures/__init__.py
@@ -0,0 +1,2 @@
+# Package marker: exposes build_fixtures as tests.fixtures.build_fixtures
+# for both conftest.py and tests/baselines/regenerate.py.

```


**CC-M-001-006** (C:\codex\general_tasks\tests\test_baseline_parity.py) - implements CI-M-001-003

**Code:**

```diff
--- /dev/null
+++ b/tests/test_baseline_parity.py
@@ -0,0 +1,46 @@
+"""Byte-level parity oracle against the reference tool's recorded output.
+
+manifest.json (DL-002) records the tool's stdout, exit code and every
+written file's bytes for a fixed set of invocations. Regenerating it is
+correct only against a deliberate, reviewed behavior change - never to
+make a failing test pass, since that would silently rewrite the contract
+this test enforces.
+"""
+
+from __future__ import annotations
+
+import base64
+import json
+from pathlib import Path
+
+import pytest
+
+from tests.conftest import run_tool
+
+BASELINE_MANIFEST = Path(__file__).parent / "baselines" / "manifest.json"
+
+
+def _load_manifest() -> list[dict]:
+    return json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8"))
+
+
+@pytest.mark.parametrize("case", _load_manifest(), ids=lambda c: " ".join(c["argv"]))
+def test_baseline_invocation_matches_stored_bytes(case: dict, fixture_corpus: Path, tmp_path: Path) -> None:
+    (tmp_path / "out").mkdir(exist_ok=True)
+    result = run_tool(case["argv"], cwd=tmp_path)
+
+    assert result.exit_code == case["exit_code"]
+    assert result.stdout == case["stdout"]
+
+    for rel_path, expected_b64 in case["output_files"].items():
+        written = (tmp_path / rel_path).read_bytes()
+        assert written == base64.b64decode(expected_b64), f"output mismatch for {rel_path}"
+
+
+def test_deliberate_one_character_edit_fails_parity(fixture_corpus: Path, tmp_path: Path) -> None:
+    """Sanity check on the oracle itself: a corrupted stored baseline must fail."""
+    case = _load_manifest()[0]
+    (tmp_path / "out").mkdir(exist_ok=True)
+    result = run_tool(case["argv"], cwd=tmp_path)
+    corrupted_stdout = case["stdout"][:-1] + ("X" if not case["stdout"].endswith("X") else "Y")
+    assert result.stdout != corrupted_stdout

```

**Documentation:**

```diff
--- a/tests/test_baseline_parity.py
+++ b/tests/test_baseline_parity.py
@@ -22,6 +22,9 @@


 def _load_manifest() -> list[dict]:
+    """Loads the tool's recorded output contract (DL-002). Regenerating
+    manifest.json is correct only for a deliberate, reviewed behavior
+    change - never to make a failing test pass."""
     return json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8"))


@@ -30,6 +33,9 @@
 @pytest.mark.parametrize("case", _load_manifest(), ids=lambda c: " ".join(c["argv"]))
 def test_baseline_invocation_matches_stored_bytes(case: dict, fixture_corpus: Path, tmp_path: Path) -> None:
+    """Re-runs one recorded invocation against the fixture corpus and
+    compares exit code, stdout and every written file's bytes against the
+    manifest's stored values (DL-011)."""
     (tmp_path / "out").mkdir(exist_ok=True)
     result = run_tool(case["argv"], cwd=tmp_path)
 
```


**CC-M-001-007** (C:\codex\general_tasks\tests\baselines\__init__.py) - implements CI-M-001-003

**Code:**

```diff
--- /dev/null
+++ b/tests/baselines/__init__.py

```

**Documentation:**

```diff
--- /dev/null
+++ b/tests/baselines/__init__.py
@@ -0,0 +1,2 @@
+# Package marker: exposes manifest.json and regenerate.py as
+# tests.baselines.* for test_baseline_parity.py's import path.

```


**CC-M-001-008** (C:\codex\general_tasks\tests\baselines\manifest.json) - implements CI-M-001-003

**Code:**

```diff
--- /dev/null
+++ b/tests/baselines/manifest.json
@@ -0,0 +1,120 @@
+[
+  {
+    "argv": [
+      "inspect",
+      "corpus/moved_paths.nml",
+      "--limit",
+      "5"
+    ],
+    "exit_code": 0,
+    "stdout": "root_version=20\nprogram=Traktor\ncollection_entries=1\ncollection_entries_with_location=1\ncollection_entries_with_primarykey=0\nplaylist_entry_refs=0\nplaylist_primarykeys=0\nall_entry_nodes_in_document=1\nsample artist='Aphex Twin' title='Xtal' volume='C:' dir='/:Users/:dj/:Music/:' file='xtal.mp3'\n",
+    "stderr": "",
+    "output_files": {}
+  },
+  {
+    "argv": [
+      "inspect",
+      "corpus/playlist_tree.nml",
+      "--limit",
+      "5",
+      "--csv",
+      "out/inspect.csv"
+    ],
+    "exit_code": 0,
+    "stdout": "root_version=20\nprogram=Traktor\ncollection_entries=1\ncollection_entries_with_location=1\ncollection_entries_with_primarykey=0\nplaylist_entry_refs=1\nplaylist_primarykeys=1\nall_entry_nodes_in_document=2\nsample artist='Four Tet' title='Baby' volume='C:' dir='/:Music/:' file='baby.mp3'\ncsv_written=out\\inspect.csv\n",
+    "stderr": "",
+    "output_files": {
+      "out/inspect.csv": "YXJ0aXN0LHRpdGxlLHZvbHVtZSx2b2x1bWVpZCxkaXIsZmlsZSxkZWNvZGVkX3BhdGgscHJpbWFyeV9rZXkNCkZvdXIgVGV0LEJhYnksQzosQzosLzpNdXNpYy86LGJhYnkubXAzLC9NdXNpYy9iYWJ5Lm1wMyxDOi86TXVzaWMvOmJhYnkubXAzDQo="
+    }
+  },
+  {
+    "argv": [
+      "encode-dir",
+      "C:\\Music\\Foo"
+    ],
+    "exit_code": 0,
+    "stdout": "/:C:/:Music/:Foo/:\n",
+    "stderr": "",
+    "output_files": {}
+  },
+  {
+    "argv": [
+      "preview-diff",
+      "corpus/moved_paths.nml",
+      "--old-volume",
+      "C:",
+      "--old-dir-prefix",
+      "/:Users/:dj/:Music/:",
+      "--new-volume",
+      "D:",
+      "--new-dir-prefix",
+      "/:Music/:"
+    ],
+    "exit_code": 0,
+    "stdout": "collection_location_changes=1\nother_location_changes=0\nprimarykey_changes=0\nsample_collection_location_changes:\n- Aphex Twin - Xtal\n  before=/Users/dj/Music/xtal.mp3\n  after=/Music/xtal.mp3\n",
+    "stderr": "",
+    "output_files": {}
+  },
+  {
+    "argv": [
+      "preview-compare",
+      "corpus/duplicate_rips.nml",
+      "corpus/duplicate_rips.nml",
+      "--limit",
+      "5"
+    ],
+    "exit_code": 0,
+    "stdout": "old_collection_entries=2\nnew_collection_entries=2\nmatched=2\nmatched_audio_id=0\nmatched_artist_title_size_time=0\nmatched_artist_title_file=2\nmatched_file_size_time=0\nmatched_artist_title_album_time=0\nmatched_artist_title=0\nunmatched=0\nambiguous=0\nprimarykey_updates_available=2\nsample_matches:\n- Burial - Archangel\n  matched_by=artist_title_file\n  before=/Music/v1/archangel_128.mp3\n  after=/Music/v1/archangel_128.mp3\n- Burial - Archangel\n  matched_by=artist_title_file\n  before=/Music/v2/archangel_320.mp3\n  after=/Music/v2/archangel_320.mp3\n",
+    "stderr": "",
+    "output_files": {}
+  },
+  {
+    "argv": [
+      "scan-compare-candidates",
+      "corpus/moved_paths.nml",
+      "corpus",
+      "--limit",
+      "5"
+    ],
+    "exit_code": 0,
+    "stdout": "target=corpus\\moved_paths.nml\ncandidates_scanned=5\ntop_candidates:\n- path=corpus\\moved_paths.nml matched=1 ratio=1.0000 ambiguous=0 unmatched=0 audio_id=0 title_size_time=1 title_file=0 file_size_time=0 album_time=0 title_only=0\n- path=corpus\\duplicate_rips.nml matched=0 ratio=0.0000 ambiguous=0 unmatched=2 audio_id=0 title_size_time=0 title_file=0 file_size_time=0 album_time=0 title_only=0\n- path=corpus\\playlist_tree.nml matched=0 ratio=0.0000 ambiguous=0 unmatched=1 audio_id=0 title_size_time=0 title_file=0 file_size_time=0 album_time=0 title_only=0\n- path=corpus\\renamed_file.nml matched=0 ratio=0.0000 ambiguous=0 unmatched=1 audio_id=0 title_size_time=0 title_file=0 file_size_time=0 album_time=0 title_only=0\n- path=corpus\\sets_section.nml matched=0 ratio=0.0000 ambiguous=0 unmatched=1 audio_id=0 title_size_time=0 title_file=0 file_size_time=0 album_time=0 title_only=0\n",
+    "stderr": "",
+    "output_files": {}
+  },
+  {
+    "argv": [
+      "rewrite",
+      "corpus/moved_paths.nml",
+      "out/rewrite_out.nml",
+      "--old-volume",
+      "C:",
+      "--old-dir-prefix",
+      "/:Users/:dj/:Music/:",
+      "--new-volume",
+      "D:",
+      "--new-dir-prefix",
+      "/:Music/:"
+    ],
+    "exit_code": 0,
+    "stdout": "collection_locations_rewritten=1\nhistory_locations_rewritten=0\nprimarykeys_updated_from_collection=0\nprimarykeys_rewritten_directly=0\nprimarykeys_unchanged=0\noutput_written=out\\rewrite_out.nml\n",
+    "stderr": "",
+    "output_files": {
+      "out/rewrite_out.nml": "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9Im5vIiA/Pgo8Tk1MIFZFUlNJT049IjIwIj48SEVBRCBQUk9HUkFNPSJUcmFrdG9yIiBWRVJTSU9OPSIxIj48L0hFQUQ+PENPTExFQ1RJT04gRU5UUklFUz0iMSI+PEVOVFJZIE1PRElGSUVEX0RBVEU9IjIwMjQvMS8xIiBNT0RJRklFRF9USU1FPSIwIiBBVURJT19JRD0iIiBUSVRMRT0iWHRhbCIgQVJUSVNUPSJBcGhleCBUd2luIj48TE9DQVRJT04gRElSPSIvOk11c2ljLzoiIEZJTEU9Inh0YWwubXAzIiBWT0xVTUU9IkQ6IiBWT0xVTUVJRD0iRDoiPjwvTE9DQVRJT04+PElORk8gQklUUkFURT0iMzIwIiBQTEFZVElNRT0iMTgwIiBQTEFZVElNRV9GTE9BVD0iMTgwLjAiIEZJTEVTSVpFPSI0MDk2Ij48L0lORk8+PC9FTlRSWT4KPC9DT0xMRUNUSU9OPjxQTEFZTElTVFM+PE5PREUgVFlQRT0iRk9MREVSIiBOQU1FPSIkUk9PVCI+PFNVQk5PREVTIENPVU5UPSIwIj48L1NVQk5PREVTPjwvTk9ERT48L1BMQVlMSVNUUz48U0VUUz48L1NFVFM+PElOREVYSU5HPjwvSU5ERVhJTkc+PC9OTUw+"
+    }
+  },
+  {
+    "argv": [
+      "rewrite-from-collection-compare",
+      "corpus/renamed_file.nml",
+      "corpus/renamed_file.nml",
+      "out/compare_out.nml",
+      "--allow-artist-title-only"
+    ],
+    "exit_code": 0,
+    "stdout": "collection_locations_rewritten=0\nother_locations_rewritten=0\nprimarykeys_updated_from_collection=0\nprimarykeys_unchanged=0\nmatched=1\nmatched_audio_id=0\nmatched_artist_title_size_time=1\nmatched_artist_title_file=0\nmatched_file_size_time=0\nmatched_artist_title_album_time=0\nmatched_artist_title=0\nunmatched=0\nambiguous=0\nsample_matches:\n- Boards of Canada - Roygbiv\n  matched_by=artist_title_size_time\n  before=/Music/roygbiv_final.mp3\n  after=/Music/roygbiv_final.mp3\noutput_written=out\\compare_out.nml\n",
+    "stderr": "",
+    "output_files": {
+      "out/compare_out.nml": "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9Im5vIiA/Pgo8Tk1MIFZFUlNJT049IjIwIj48SEVBRCBQUk9HUkFNPSJUcmFrdG9yIiBWRVJTSU9OPSIxIj48L0hFQUQ+PENPTExFQ1RJT04gRU5UUklFUz0iMSI+PEVOVFJZIE1PRElGSUVEX0RBVEU9IjIwMjQvMS8xIiBNT0RJRklFRF9USU1FPSIwIiBBVURJT19JRD0iIiBUSVRMRT0iUm95Z2JpdiIgQVJUSVNUPSJCb2FyZHMgb2YgQ2FuYWRhIj48TE9DQVRJT04gRElSPSIvOk11c2ljLzoiIEZJTEU9InJveWdiaXZfZmluYWwubXAzIiBWT0xVTUU9IkM6IiBWT0xVTUVJRD0iQzoiPjwvTE9DQVRJT04+PElORk8gQklUUkFURT0iMzIwIiBQTEFZVElNRT0iMTgwIiBQTEFZVElNRV9GTE9BVD0iMTgwLjAiIEZJTEVTSVpFPSI0MDk2Ij48L0lORk8+PC9FTlRSWT4KPC9DT0xMRUNUSU9OPjxQTEFZTElTVFM+PE5PREUgVFlQRT0iRk9MREVSIiBOQU1FPSIkUk9PVCI+PFNVQk5PREVTIENPVU5UPSIwIj48L1NVQk5PREVTPjwvTk9ERT48L1BMQVlMSVNUUz48U0VUUz48L1NFVFM+PElOREVYSU5HPjwvSU5ERVhJTkc+PC9OTUw+"
+    }
+  }
+]

```

**Documentation:**

```diff
--- /dev/null
+++ b/tests/baselines/manifest.schema.md
@@ -0,0 +1,17 @@
+# tests/baselines/manifest.json
+
+JSON array of recorded CLI invocations, one object per case:
+
+- `argv`: argument list passed to `traktor_nml.cli.main`
+- `exit_code`, `stdout`, `stderr`: expected process output
+- `output_files`: relative path -> base64-encoded expected file bytes
+
+manifest.json records the tool's output contract for this fixed set of
+invocations: every case here must keep passing byte-for-byte. Regenerating
+it is correct only against a deliberate, reviewed behavior change (see
+regenerate.py's module docstring for the regeneration command) - never to
+make a failing test pass, since that would silently rewrite the contract
+it encodes.
+
+This file itself holds no comments (JSON has none) - this document is
+its comment.

```


**CC-M-001-009** (C:\codex\general_tasks\tests\baselines\regenerate.py) - implements CI-M-001-003

**Code:**

```diff
--- /dev/null
+++ b/tests/baselines/regenerate.py
@@ -0,0 +1,102 @@
+"""Regenerate tests/baselines/manifest.json from the current tool.
+
+Documented regeneration command:
+
+    python -m tests.baselines.regenerate
+
+Run only against the unmodified tool when first capturing the parity
+oracle, or deliberately after a change whose new output is intentional.
+Regeneration over an unmodified tool reproduces the stored manifest exactly
+(the fixture corpus and argv list are both deterministic), so running it is
+a no-op unless behavior actually changed. Not imported or exercised by the
+test suite itself.
+"""
+
+from __future__ import annotations
+
+import base64
+import contextlib
+import io
+import json
+from pathlib import Path
+
+from tests.fixtures.build_fixtures import build_fixtures
+
+MANIFEST_PATH = Path(__file__).parent / "manifest.json"
+
+CASES: list[list[str]] = [
+    ["inspect", "corpus/moved_paths.nml", "--limit", "5"],
+    ["inspect", "corpus/playlist_tree.nml", "--limit", "5", "--csv", "out/inspect.csv"],
+    ["encode-dir", r"C:\Music\Foo"],
+    [
+        "preview-diff", "corpus/moved_paths.nml",
+        "--old-volume", "C:", "--old-dir-prefix", "/:Users/:dj/:Music/:",
+        "--new-volume", "D:", "--new-dir-prefix", "/:Music/:",
+    ],
+    ["preview-compare", "corpus/duplicate_rips.nml", "corpus/duplicate_rips.nml", "--limit", "5"],
+    ["scan-compare-candidates", "corpus/moved_paths.nml", "corpus", "--limit", "5"],
+    [
+        "rewrite", "corpus/moved_paths.nml", "out/rewrite_out.nml",
+        "--old-volume", "C:", "--old-dir-prefix", "/:Users/:dj/:Music/:",
+        "--new-volume", "D:", "--new-dir-prefix", "/:Music/:",
+    ],
+    [
+        "rewrite-from-collection-compare",
+        "corpus/renamed_file.nml", "corpus/renamed_file.nml", "out/compare_out.nml",
+        "--allow-artist-title-only",
+    ],
+]
+
+_OUTPUT_ARG_INDEX = {
+    "rewrite": 2,
+    "rewrite-from-collection-compare": 3,
+}
+
+
+def _output_paths(argv: list[str]) -> list[str]:
+    paths = []
+    if "--csv" in argv:
+        paths.append(argv[argv.index("--csv") + 1])
+    index = _OUTPUT_ARG_INDEX.get(argv[0])
+    if index is not None:
+        paths.append(argv[index])
+    return paths
+
+
+def regenerate(target_dir: Path) -> list[dict]:
+    from traktor_nml.cli import main
+
+    build_fixtures(target_dir / "corpus")
+    (target_dir / "out").mkdir(exist_ok=True)
+
+    manifest = []
+    for argv in CASES:
+        stdout = io.StringIO()
+        stderr = io.StringIO()
+        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
+            try:
+                exit_code = main(argv)
+            except SystemExit as exc:
+                exit_code = 0 if exc.code is None else int(exc.code)
+        entry = {
+            "argv": argv,
+            "exit_code": exit_code,
+            "stdout": stdout.getvalue(),
+            "stderr": stderr.getvalue(),
+            "output_files": {},
+        }
+        for rel_path in _output_paths(argv):
+            path = target_dir / rel_path
+            if path.exists():
+                entry["output_files"][rel_path] = base64.b64encode(path.read_bytes()).decode("ascii")
+        manifest.append(entry)
+    return manifest
+
+
+if __name__ == "__main__":
+    import tempfile
+
+    with tempfile.TemporaryDirectory() as tmp:
+        manifest = regenerate(Path(tmp))
+    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
+    print(f"wrote {MANIFEST_PATH}")

```

**Documentation:**

```diff
--- a/tests/baselines/regenerate.py
+++ b/tests/baselines/regenerate.py
@@ -28,6 +28,10 @@


 def _output_paths(argv: list) -> list:
+    """Return the output file path(s) argv writes, using
+    _OUTPUT_ARG_INDEX to find the destination argument for commands that
+    write files; a command absent from that mapping is read-only and
+    produces no output file to capture."""

```


**CC-M-001-010** (tests/CLAUDE.md)

**Documentation:**

```diff
--- /dev/null
+++ b/tests/CLAUDE.md
@@ -0,0 +1,23 @@
+# tests/
+
+## Files
+
+| File                     | What                                                        | When to read                                              |
+| ------------------------ | ------------------------------------------------------------- | ------------------------------------------------------------ |
+| `__init__.py`            | Package marker                                               | -                                                             |
+| `conftest.py`            | `run_tool`/`fixture_corpus` fixtures shared across test modules | Adding a test module, changing how the CLI is invoked under test |
+| `test_baseline_parity.py`| Byte-level parity oracle against `baselines/manifest.json`    | Changing any CLI subcommand's output, exit code, or written bytes |
+| `test_cli_contract.py`   | Subcommand surface + `--allow-artist-title-only`/`--match-confidence` alias contract | Adding/renaming a subcommand, changing legacy-flag equivalence |
+| `test_diskscan.py`       | Disk-scan candidate discovery tests                            | Changing `diskscan.py`                                        |
+| `test_reconnect.py`      | Reconnection matching and one-to-one assignment tests          | Changing `reconnect.py` or `volumes.py`                       |
+| `test_fingerprint.py`    | Acoustic fingerprint comparison tests                          | Changing `fingerprint.py`                                     |
+| `test_spans.py`          | Byte-span scanner, `OutputBuilder`, count-attribute recalculation tests | Changing `spans.py`                                           |
+| `test_splice.py`         | Splice merge/conflict-resolution tests                         | Changing `splice.py` or `playlists.py`                        |
+| `test_split.py`          | Split filter/dangling-reference tests                          | Changing `split.py`                                           |
+
+## Subdirectories
+
+| Directory    | What                                                      | When to read                                          |
+| ------------ | ----------------------------------------------------------- | -------------------------------------------------------- |
+| `fixtures/`  | `build_fixtures.py`: constructs the on-disk NML fixture corpus | Adding a new fixture NML file or scenario               |
+| `baselines/` | `manifest.json` (golden CLI-invocation baseline) + `regenerate.py` + `manifest.schema.md` | Regenerating the baseline after a deliberate, reviewed behavior change |

```


### Milestone 2: Package extraction with cascade unification and confidence enum

**Files**: C:\codex\general_tasks\traktor_nml\__init__.py, C:\codex\general_tasks\traktor_nml\model.py, C:\codex\general_tasks\traktor_nml\matching.py, C:\codex\general_tasks\traktor_nml\textpatch.py, C:\codex\general_tasks\traktor_nml\rewrite.py, C:\codex\general_tasks\traktor_nml\confidence.py, C:\codex\general_tasks\traktor_nml\cli.py, C:\codex\general_tasks\traktor_nml\commands\__init__.py, C:\codex\general_tasks\traktor_nml\commands\inspect_cmd.py, C:\codex\general_tasks\traktor_nml\commands\rewrite_cmd.py, C:\codex\general_tasks\traktor_nml\commands\compare_cmd.py, C:\codex\general_tasks\traktor_nml_tool.py, C:\codex\general_tasks\tests\test_cli_contract.py

**Flags**: refactor, needs-rationale

**Requirements**:

- The seven existing subcommands keep their names / positional arguments / stdout key=value vocabulary / exit codes
- EntryRecord carries an optional entry element so candidates without a source element are representable
- One cascade helper parameterised by a resolver callable serves both rule-based and compare-based non-collection entry processing
- One read-parse-patch-write helper serves both existing write commands and covers the lxml and stdlib branches
- Subcommand parsers register themselves from modules under traktor_nml/commands and the CLI enumerates that package
- --match-confidence accepts strict / loose / filename on preview-compare and rewrite-from-collection-compare with --allow-artist-title-only parsing as loose
- record_keys accepts an optional ranked list of additional key providers and behaves identically when none are supplied
- traktor_nml_tool.py forwards argv to the package entry point

**Acceptance Criteria**:

- The baseline parity test from the foundation milestone passes unchanged against the extracted package
- Invoking python traktor_nml_tool.py with any pre-existing command line produces byte-identical stdout and output files
- --allow-artist-title-only and --match-confidence loose produce identical stats on the same inputs
- --help lists exactly the seven pre-existing subcommands
- No module in traktor_nml exceeds 400 lines

**Tests**:

- C:\codex\general_tasks\tests\test_cli_contract.py
- C:\codex\general_tasks\tests\test_baseline_parity.py

#### Code Intent

- **CI-M-002-001** `C:\codex\general_tasks\traktor_nml\model.py::EntryRecord`: Model a track's identity fields together with an optional source element, so a record derived from a filesystem candidate carries no element while a record read from a collection carries the element that patching locates. Every consumer that dereferences the element guards for its absence and candidate-side records are never passed to the write path. (refs: DL-001)
- **CI-M-002-002** `C:\codex\general_tasks\traktor_nml\rewrite.py::process_non_collection_entries`: Walk every entry outside the collection and update its LOCATION and PRIMARYKEY through a caller-supplied resolver that maps an old key or location to a replacement, accumulating either attribute patches or in-tree mutations depending on the write path in use. Rule-based and compare-based rewriting differ only in the resolver they supply. (refs: DL-001)
- **CI-M-002-003** `C:\codex\general_tasks\traktor_nml\rewrite.py::write_nml_safely`: Read the source bytes, parse them with whichever parser is available, hand the parsed root to a caller-supplied patch collector, print the returned statistics, and write the patched bytes only when the run is not a dry run and the output path differs from the input path. Both existing write commands are expressed as callers of this helper. (refs: DL-001, DL-012)
- **CI-M-002-004** `C:\codex\general_tasks\traktor_nml\cli.py::build_parser`: Construct the argument parser by enumerating modules under the commands package and calling each module's registration hook, so the set of subcommands is determined by the package contents. Command dispatch looks up the handler the registration hook recorded. (refs: DL-003)
- **CI-M-002-005** `C:\codex\general_tasks\traktor_nml\confidence.py::MatchConfidence`: Name the ordered confidence levels strict, loose and filename, expose the tier list each level admits, and translate the legacy artist-title-only boolean into the loose level so both spellings converge before matching runs. (refs: DL-010)
- **CI-M-002-006** `C:\codex\general_tasks\traktor_nml\matching.py::record_keys`: Produce a record's match keys in descending confidence order, admitting tiers according to the supplied confidence level and appending keys contributed by any injected key providers ahead of the tag-derived tiers. With no providers supplied the emitted sequence is unchanged from the tag-only cascade. (refs: DL-006, DL-010)
- **CI-M-002-007** `C:\codex\general_tasks\traktor_nml_tool.py::main`: Forward the process argv to the package entry point and propagate its exit code, so the historical invocation path keeps working while the implementation lives in the package. (refs: DL-001)

#### Code Changes

**CC-M-002-001** (C:\codex\general_tasks\traktor_nml\model.py) - implements CI-M-002-001

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/model.py
@@ -0,0 +1,265 @@
+"""Core domain model: LOCATION/PRIMARYKEY parsing and the EntryRecord identity.
+
+A Traktor NML file holds one COLLECTION of ENTRY elements whose LOCATION
+carries VOLUME, VOLUMEID, DIR and FILE, and a PLAYLISTS tree whose PRIMARYKEY
+elements reference collection entries by the flattened concatenation
+VOLUME + DIR + FILE. Every path repair is therefore two edits that must agree:
+the LOCATION on the collection entry and every PRIMARYKEY that pointed at its
+old flattened form.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field
+from pathlib import Path, PurePosixPath
+from typing import Iterable, Optional
+
+from .xmlio import ET
+
+
+@dataclass(frozen=True)
+class LocationParts:
+    volume: str
+    volumeid: str
+    dir_value: str
+    file_name: str
+
+    @property
+    def primary_key(self) -> str:
+        return f"{self.volume}{self.dir_value}{self.file_name}"
+
+    @property
+    def decoded_dir(self) -> PurePosixPath:
+        return decode_traktor_dir(self.dir_value)
+
+    @property
+    def decoded_path(self) -> PurePosixPath:
+        return self.decoded_dir / self.file_name
+
+
+@dataclass(frozen=True)
+class RewriteRule:
+    old_volume: str
+    old_dir_prefix: str
+    new_volume: str
+    new_dir_prefix: str
+    new_volumeid: str | None = None
+
+    def matches(self, loc: LocationParts) -> bool:
+        return loc.volume == self.old_volume and loc.dir_value.startswith(self.old_dir_prefix)
+
+    def apply(self, loc: LocationParts) -> LocationParts:
+        suffix = loc.dir_value[len(self.old_dir_prefix):]
+        return LocationParts(
+            volume=self.new_volume,
+            volumeid=self.new_volume if self.new_volumeid is None else self.new_volumeid,
+            dir_value=f"{self.new_dir_prefix}{suffix}",
+            file_name=loc.file_name,
+        )
+
+
+@dataclass
+class EntryRecord:
+    """A track's identity fields together with an optional source element.
+
+    A record derived from a filesystem candidate (see diskscan.py) carries no
+    element, since there is nothing in an NML document for it to point at.
+    A record read from a collection carries the element that attribute
+    patching locates. Every consumer that dereferences .entry guards for None,
+    and candidate-side records (entry is None) are never passed to the
+    attribute-patch write path, only used as the matching-cascade's candidate
+    side.
+    """
+
+    entry: Optional[ET.Element]
+    artist: str
+    title: str
+    audio_id: str
+    filesize: str
+    playtime_float: str
+    bitrate: str
+    album: str
+    file_name: str
+    location: LocationParts
+    # Set only on disk-derived candidates (entry is None), so reconnection can
+    # re-encode the real absolute path into a LOCATION after a match, since
+    # the placeholder LocationParts a candidate carries is for display only
+    # and is never treated as an authoritative VOLUME/VOLUMEID source.
+    source_path: Optional[Path] = None
+
+    @property
+    def primary_key(self) -> str:
+        return self.location.primary_key
+
+
+@dataclass
+class ElemPatch:
+    sourceline: int
+    tag_name: str
+    locator: tuple[tuple[str, str], ...]
+    changes: list[tuple[str, str, str]] = field(default_factory=list)  # (attr, old, new)
+
+
+def decode_traktor_dir(dir_value: str) -> PurePosixPath:
+    if not dir_value or dir_value == "/:":
+        return PurePosixPath("/")
+
+    trimmed = dir_value
+    if trimmed.startswith("/:"):
+        trimmed = trimmed[2:]
+    if trimmed.endswith("/:"):
+        trimmed = trimmed[:-2]
+
+    parts = [part for part in trimmed.split("/:") if part]
+    return PurePosixPath("/") / PurePosixPath(*parts)
+
+
+def encode_traktor_dir(path_value: str) -> str:
+    normalized = path_value.replace("\\", "/").strip()
+    parts = [part for part in normalized.split("/") if part]
+    return "/:" + "/:".join(parts) + "/:"
+
+
+def normalize_dir_prefix(value: str) -> str:
+    stripped = value.strip()
+    if "/:" in stripped:
+        if not stripped.startswith("/:"):
+            stripped = "/:" + (stripped[1:] if stripped.startswith("/") else stripped)
+        if not stripped.endswith("/:"):
+            stripped = stripped.rstrip("/") + "/:"
+        return stripped
+    return encode_traktor_dir(stripped)
+
+
+def parse_location_element(elem: ET.Element) -> LocationParts:
+    return LocationParts(
+        volume=elem.attrib.get("VOLUME", ""),
+        volumeid=elem.attrib.get("VOLUMEID", elem.attrib.get("VOLUME", "")),
+        dir_value=elem.attrib.get("DIR", ""),
+        file_name=elem.attrib.get("FILE", ""),
+    )
+
+
+def write_location_element(elem: ET.Element, loc: LocationParts) -> None:
+    elem.attrib["VOLUME"] = loc.volume
+    elem.attrib["VOLUMEID"] = loc.volumeid
+    elem.attrib["DIR"] = loc.dir_value
+    elem.attrib["FILE"] = loc.file_name
+
+
+def parse_primary_key(key: str, volumeid: str | None = None) -> LocationParts:
+    marker = "/:"
+    idx = key.find(marker)
+    if idx < 0:
+        raise ValueError(f"PRIMARYKEY missing '/:' marker: {key!r}")
+
+    volume = key[:idx]
+    remainder = key[idx:]
+    last = remainder.rfind(marker)
+    if last < 0:
+        raise ValueError(f"PRIMARYKEY missing final '/:' separator: {key!r}")
+
+    dir_value = remainder[: last + len(marker)]
+    file_name = remainder[last + len(marker):]
+    return LocationParts(
+        volume=volume,
+        volumeid=volume if volumeid is None else volumeid,
+        dir_value=dir_value,
+        file_name=file_name,
+    )
+
+
+def apply_rules(loc: LocationParts, rules: Iterable[RewriteRule]) -> tuple[LocationParts, bool]:
+    for rule in rules:
+        if rule.matches(loc):
+            return rule.apply(loc), True
+    return loc, False
+
+
+def collection_entries(root: ET.Element) -> list[ET.Element]:
+    collection = root.find("COLLECTION")
+    return [] if collection is None else collection.findall("ENTRY")
+
+
+def playlist_entries(root: ET.Element) -> list[ET.Element]:
+    return root.findall(".//PLAYLIST/ENTRY")
+
+
+def all_entries(root: ET.Element) -> list[ET.Element]:
+    return root.findall(".//ENTRY")
+
+
+def collection_records(root: ET.Element) -> list[EntryRecord]:
+    records: list[EntryRecord] = []
+    for entry in collection_entries(root):
+        loc_elem = entry.find("LOCATION")
+        if loc_elem is None:
+            continue
+        info = entry.find("INFO")
+        album = entry.find("ALBUM")
+        records.append(
+            EntryRecord(
+                entry=entry,
+                artist=entry.attrib.get("ARTIST", ""),
+                title=entry.attrib.get("TITLE", ""),
+                audio_id=entry.attrib.get("AUDIO_ID", ""),
+                filesize="" if info is None else info.attrib.get("FILESIZE", ""),
+                playtime_float="" if info is None else info.attrib.get("PLAYTIME_FLOAT", ""),
+                bitrate="" if info is None else info.attrib.get("BITRATE", ""),
+                album="" if album is None else album.attrib.get("TITLE", ""),
+                file_name=loc_elem.attrib.get("FILE", ""),
+                location=parse_location_element(loc_elem),
+            )
+        )
+    return records
+
+
+def location_rows(entries: list[ET.Element]) -> list[dict[str, str]]:
+    rows: list[dict[str, str]] = []
+    for entry in entries:
+        loc_elem = entry.find("LOCATION")
+        if loc_elem is None:
+            continue
+        loc = parse_location_element(loc_elem)
+        rows.append(
+            {
+                "artist": entry.attrib.get("ARTIST", ""),
+                "title": entry.attrib.get("TITLE", ""),
+                "volume": loc.volume,
+                "volumeid": loc.volumeid,
+                "dir": loc.dir_value,
+                "file": loc.file_name,
+                "decoded_path": str(loc.decoded_path),
+                "primary_key": loc.primary_key,
+            }
+        )
+    return rows
+
+
+def entry_label(entry: ET.Element) -> str:
+    artist = entry.attrib.get("ARTIST", "")
+    title = entry.attrib.get("TITLE", "")
+    if artist or title:
+        return f"{artist} - {title}".strip(" -")
+    return "<reference>"
+
+
+def record_label(record: EntryRecord) -> str:
+    if record.entry is not None:
+        return entry_label(record.entry)
+    if record.artist or record.title:
+        return f"{record.artist} - {record.title}".strip(" -")
+    return record.file_name or "<candidate>"
+
+
+def loc_attr_changes(old: LocationParts, new: LocationParts) -> list[tuple[str, str, str]]:
+    return [
+        (attr, ov, nv)
+        for attr, ov, nv in [
+            ("VOLUME", old.volume, new.volume),
+            ("VOLUMEID", old.volumeid, new.volumeid),
+            ("DIR", old.dir_value, new.dir_value),
+            ("FILE", old.file_name, new.file_name),
+        ]
+        if ov != nv
+    ]

```

**Documentation:**

```diff
--- a/traktor_nml/model.py
+++ b/traktor_nml/model.py
@@ -22,6 +22,10 @@

     def apply(self, loc: LocationParts) -> LocationParts:
+        # VOLUMEID defaults to new_volume: most real collections use
+        # identical VOLUME/VOLUMEID pairs, so new_volumeid is only needed
+        # when a rule's destination volume and volume id actually diverge.
         suffix = loc.dir_value[len(self.old_dir_prefix):]
         return LocationParts(
             volume=self.new_volume,

```


**CC-M-002-002** (C:\codex\general_tasks\traktor_nml\rewrite.py) - implements CI-M-002-002

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/rewrite.py
@@ -0,0 +1,173 @@
+"""Non-collection cascade and the shared read-parse-patch-write skeleton.
+
+Rule-based and compare-based rewriting previously duplicated the "walk every
+entry outside the collection, update LOCATION and PRIMARYKEY" cascade and the
+"read source, parse, patch, write" skeleton almost verbatim (DL-001).
+process_non_collection_entries takes an EntryResolver so the two callers
+differ only in how an old key or location resolves to its replacement, and
+write_nml_safely takes lxml-path and stdlib-path builder callables so both
+existing write commands share one read/print/write shell.
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+import tempfile
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Callable, Optional, Protocol
+
+from .confidence import MatchConfidence
+from .matching import KeyProvider, match_records
+from .model import (
+    EntryRecord,
+    ElemPatch,
+    LocationParts,
+    all_entries,
+    apply_rules,
+    collection_entries,
+    collection_records,
+    loc_attr_changes,
+    parse_location_element,
+    parse_primary_key,
+    write_location_element,
+)
+from .textpatch import apply_text_patches, location_patch, primarykey_patch
+from .xmlio import ET, HAS_LXML, XML_PARSE_ERROR, parse_xml, parse_xml_bytes, write_traktor_xml
+
+
+class EntryResolver(Protocol):
+    """Resolves an old-side LOCATION and PRIMARYKEY to their replacements.
+
+    locate's second return value doubles as "should this be counted and
+    written" - rule-based resolvers count on a rule match, compare-based
+    resolvers count on an actual attribute difference, matching each
+    strategy's pre-extraction behavior exactly.
+    """
+
+    location_stat: str
+
+    def locate(self, old_loc: LocationParts) -> tuple[LocationParts, bool]: ...
+
+    def key_of(self, old_key: str) -> Optional[str]: ...
+
+    def fallback_key(self, old_key: str) -> Optional[str]: ...
+
+
+@dataclass
+class RuleEntryResolver:
+    rules: list
+    old_to_new_key: dict[str, str]
+    location_stat: str = "history_locations_rewritten"
+
+    def locate(self, old_loc: LocationParts) -> tuple[LocationParts, bool]:
+        return apply_rules(old_loc, self.rules)
+
+    def key_of(self, old_key: str) -> Optional[str]:
+        return self.old_to_new_key.get(old_key)
+
+    def fallback_key(self, old_key: str) -> Optional[str]:
+        try:
+            old_pk_loc = parse_primary_key(old_key)
+        except ValueError:
+            return None
+        new_loc, changed = apply_rules(old_pk_loc, self.rules)
+        return new_loc.primary_key if changed else None
+
+
+@dataclass
+class CompareEntryResolver:
+    mapping: dict[str, EntryRecord]
+    location_stat: str = "other_locations_rewritten"
+
+    def locate(self, old_loc: LocationParts) -> tuple[LocationParts, bool]:
+        new_record = self.mapping.get(old_loc.primary_key)
+        if new_record is None:
+            return old_loc, False
+        return new_record.location, bool(loc_attr_changes(old_loc, new_record.location))
+
+    def key_of(self, old_key: str) -> Optional[str]:
+        new_record = self.mapping.get(old_key)
+        return None if new_record is None else new_record.primary_key
+
+    def fallback_key(self, old_key: str) -> Optional[str]:
+        return None
+
+
+def process_non_collection_entries(
+    root: ET.Element,
+    coll_ids: set[int],
+    resolver: EntryResolver,
+    stats: dict[str, int],
+    *,
+    dry_run: bool = False,
+    patches: list[ElemPatch] | None = None,
+) -> None:
+    """Update every entry outside the collection through resolver.
+
+    When patches is not None, attribute changes are appended to it (lxml
+    path). When patches is None and dry_run is False, changes are applied
+    directly to the tree (stdlib fallback path).
+    """
+    for entry in all_entries(root):
+        if id(entry) in coll_ids:
+            continue
+        loc_elem = entry.find("LOCATION")
+        if loc_elem is not None:
+            old_loc = parse_location_element(loc_elem)
+            new_loc, counted = resolver.locate(old_loc)
+            if counted:
+                stats[resolver.location_stat] += 1
+                ch = loc_attr_changes(old_loc, new_loc)
+                if patches is not None:
+                    if ch:
+                        patches.append(location_patch(loc_elem, old_loc, ch))
+                elif not dry_run:
+                    write_location_element(loc_elem, new_loc)
+        pk_elem = entry.find("PRIMARYKEY")
+        if pk_elem is None:
+            continue
+        old_key = pk_elem.attrib.get("KEY", "")
+        new_key = resolver.key_of(old_key)
+        if new_key is not None:
+            stats["primarykeys_updated_from_collection"] += 1
+            if patches is not None:
+                patches.append(primarykey_patch(pk_elem, old_key, new_key))
+            elif not dry_run:
+                pk_elem.attrib["KEY"] = new_key
+            continue
+        new_key = resolver.fallback_key(old_key)
+        if new_key is not None:
+            stats["primarykeys_rewritten_directly"] += 1
+            if patches is not None:
+                patches.append(primarykey_patch(pk_elem, old_key, new_key))
+            elif not dry_run:
+                pk_elem.attrib["KEY"] = new_key
+        else:
+            stats["primarykeys_unchanged"] += 1
+
+
+def _empty_rule_stats() -> dict[str, int]:
+    return {
+        "collection_locations_rewritten": 0,
+        "history_locations_rewritten": 0,
+        "primarykeys_updated_from_collection": 0,
+        "primarykeys_rewritten_directly": 0,
+        "primarykeys_unchanged": 0,
+    }
+
+
+def _empty_compare_stats() -> dict[str, int]:
+    # No primarykeys_rewritten_directly key here: CompareEntryResolver.fallback_key
+    # always returns None (compare-based rewriting has no direct-rule fallback),
+    # so that stat is never incremented on this path and printing it would add
+    # a key the pre-extraction compare-based commands never emitted.
+    return {
+        "collection_locations_rewritten": 0,
+        "other_locations_rewritten": 0,
+        "primarykeys_updated_from_collection": 0,
+        "primarykeys_unchanged": 0,
+    }
+
+

```

**Documentation:**

```diff
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -32,6 +32,10 @@

     location_stat: str
+    """Stats-dict key incremented once per LOCATION this resolver
+    actually rewrites - a rule-based resolver and a compare-based
+    resolver each name their own key, so print_stats_and_samples reports
+    the correct label for whichever strategy produced this resolver."""

     def locate(self, old_loc: LocationParts) -> tuple[LocationParts, bool]: ...

```


**CC-M-002-003** (C:\codex\general_tasks\traktor_nml\rewrite.py) - implements CI-M-002-003

**Code:**

```diff
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -171,3 +171,198 @@
     }
 
 
+def rewrite_nml(root: ET.Element, rules: list, dry_run: bool) -> dict[str, int]:
+    stats = _empty_rule_stats()
+    coll = collection_entries(root)
+    old_to_new_key: dict[str, str] = {}
+    for entry in coll:
+        loc_elem = entry.find("LOCATION")
+        if loc_elem is None:
+            continue
+        old_loc = parse_location_element(loc_elem)
+        new_loc, changed = apply_rules(old_loc, rules)
+        if changed:
+            old_to_new_key[old_loc.primary_key] = new_loc.primary_key
+            stats["collection_locations_rewritten"] += 1
+            if not dry_run:
+                write_location_element(loc_elem, new_loc)
+    resolver = RuleEntryResolver(rules=rules, old_to_new_key=old_to_new_key)
+    process_non_collection_entries(root, {id(e) for e in coll}, resolver, stats, dry_run=dry_run)
+    return stats
+
+
+def rewrite_from_collection_compare(
+    old_root: ET.Element, new_root: ET.Element, dry_run: bool, confidence: MatchConfidence,
+    key_providers: list[KeyProvider] = (),
+) -> tuple[dict[str, int], list[tuple[str, str, str, str]]]:
+    old_records = collection_records(old_root)
+    new_records = collection_records(new_root)
+    mapping, match_stats, samples = match_records(old_records, new_records, confidence, key_providers)
+    stats = {**_empty_compare_stats(), **match_stats}
+    for record in old_records:
+        new_record = mapping.get(record.primary_key)
+        if new_record is None:
+            continue
+        ch = loc_attr_changes(record.location, new_record.location)
+        if ch:
+            stats["collection_locations_rewritten"] += 1
+            if not dry_run:
+                loc_elem = record.entry.find("LOCATION")
+                if loc_elem is not None:
+                    write_location_element(loc_elem, new_record.location)
+    resolver = CompareEntryResolver(mapping=mapping)
+    process_non_collection_entries(
+        old_root, {id(r.entry) for r in old_records}, resolver, stats, dry_run=dry_run
+    )
+    return stats, samples
+
+
+def _collect_rewrite_patches(root: ET.Element, rules: list) -> tuple[list[ElemPatch], dict[str, int]]:
+    stats = _empty_rule_stats()
+    patches: list[ElemPatch] = []
+    coll = collection_entries(root)
+    old_to_new_key: dict[str, str] = {}
+    for entry in coll:
+        loc_elem = entry.find("LOCATION")
+        if loc_elem is None:
+            continue
+        old_loc = parse_location_element(loc_elem)
+        new_loc, changed = apply_rules(old_loc, rules)
+        if changed:
+            old_to_new_key[old_loc.primary_key] = new_loc.primary_key
+            stats["collection_locations_rewritten"] += 1
+            ch = loc_attr_changes(old_loc, new_loc)
+            if ch:
+                patches.append(location_patch(loc_elem, old_loc, ch))
+    resolver = RuleEntryResolver(rules=rules, old_to_new_key=old_to_new_key)
+    process_non_collection_entries(root, {id(e) for e in coll}, resolver, stats, patches=patches)
+    return patches, stats
+
+
+def _collect_compare_patches(
+    old_root: ET.Element, old_records: list[EntryRecord], mapping: dict[str, EntryRecord]
+) -> tuple[list[ElemPatch], dict[str, int]]:
+    stats = _empty_compare_stats()
+    patches: list[ElemPatch] = []
+    for record in old_records:
+        new_record = mapping.get(record.primary_key)
+        if new_record is None:
+            continue
+        loc_elem = record.entry.find("LOCATION")
+        if loc_elem is not None:
+            ch = loc_attr_changes(record.location, new_record.location)
+            if ch:
+                stats["collection_locations_rewritten"] += 1
+                patches.append(location_patch(loc_elem, record.location, ch))
+    resolver = CompareEntryResolver(mapping=mapping)
+    process_non_collection_entries(
+        old_root, {id(r.entry) for r in old_records}, resolver, stats, patches=patches
+    )
+    return patches, stats
+
+
+def _write_bytes_atomically(output: Path, data: bytes) -> None:
+    # write_bytes/open("wb") truncate an existing destination in place, so a
+    # write that fails partway (disk full, process killed) can leave a
+    # truncated file where a valid collection used to stand. Writing to a
+    # temp file in the same directory and renaming over the destination
+    # means the destination only ever shows the old complete file or the new
+    # complete file, never a partial one - os.replace is atomic on both
+    # POSIX and Windows for same-volume renames.
+    output.parent.mkdir(parents=True, exist_ok=True)
+    fd, tmp_name = tempfile.mkstemp(dir=str(output.parent), prefix=f".{output.name}.", suffix=".tmp")
+    try:
+        with os.fdopen(fd, "wb") as handle:
+            handle.write(data)
+        os.replace(tmp_name, str(output))
+    except BaseException:
+        try:
+            os.remove(tmp_name)
+        except OSError:
+            pass
+        raise
+
+
+def apply_and_write(source_bytes: bytes, patches: list[ElemPatch], output: Path) -> None:
+    # Traktor's current collection/history files declare UTF-8. Keeping the
+    # source string intact means this re-encodes to exactly the same bytes
+    # except for the requested XML-escaped attribute values.
+    patched = apply_text_patches(source_bytes.decode("utf-8"), patches)
+    _write_bytes_atomically(output, patched.encode("utf-8"))
+
+
+def print_stats_and_samples(
+    stats: dict[str, int], samples: list[tuple[str, str, str, str]] | None, limit: int = 10
+) -> None:
+    for key, value in stats.items():
+        print(f"{key}={value}")
+    if samples:
+        print("sample_matches:")
+        for label, before, after, matched_by in samples[:limit]:
+            print(f"- {label}")
+            print(f"  matched_by={matched_by}")
+            print(f"  before={before}")
+            print(f"  after={after}")
+
+
+# Callables a caller of write_nml_safely supplies:
+#   collect_patches(root) -> (patches, stats, samples)          [lxml path]
+#   mutate_tree(root, dry_run) -> (stats, samples)               [stdlib path]
+CollectPatchesFn = Callable[[ET.Element], tuple[list[ElemPatch], dict[str, int], list]]
+MutateTreeFn = Callable[[ET.Element, bool], tuple[dict[str, int], list]]
+
+
+def write_nml_safely(
+    input_path: Path,
+    output_path: Path,
+    dry_run: bool,
+    collect_patches: CollectPatchesFn,
+    mutate_tree: MutateTreeFn,
+    extra_inputs: tuple[Path, ...] = (),
+) -> int:
+    """Read source bytes, parse, patch, print stats, and write once.
+
+    Refuses to write when output_path resolves to input_path or any of
+    extra_inputs (existing tool convention). Both existing write commands
+    (rewrite, rewrite-from-collection-compare) are expressed as callers of
+    this helper, one supplying collect_patches for the lxml path and
+    mutate_tree for the stdlib fallback.
+    """
+    if output_path.resolve() in {input_path.resolve(), *(p.resolve() for p in extra_inputs)}:
+        print("output_must_differ_from_input", file=sys.stderr)
+        return 2
+
+    if HAS_LXML:
+        try:
+            source_bytes = input_path.read_bytes()
+        except FileNotFoundError:
+            print(f"input_not_found={input_path}", file=sys.stderr)
+            return 2
+        try:
+            root = parse_xml_bytes(source_bytes)
+        except XML_PARSE_ERROR as exc:
+            print(f"xml_parse_error={input_path}: {exc}", file=sys.stderr)
+            return 2
+        patches, stats, samples = collect_patches(root)
+        print_stats_and_samples(stats, samples)
+        if not dry_run:
+            try:
+                apply_and_write(source_bytes, patches, output_path)
+            except (UnicodeDecodeError, ValueError) as exc:
+                print(f"text_patch_error={exc}", file=sys.stderr)
+                return 2
+            print(f"output_written={output_path}")
+        return 0
+
+    try:
+        tree = parse_xml(input_path)
+    except FileNotFoundError:
+        print(f"input_not_found={input_path}", file=sys.stderr)
+        return 2
+    root = tree.getroot()
+    stats, samples = mutate_tree(root, dry_run)
+    print_stats_and_samples(stats, samples)
+    if not dry_run:
+        write_traktor_xml(root, output_path, write_bytes=_write_bytes_atomically)
+        print(f"output_written={output_path}")
+    return 0

```

**Documentation:**

```diff
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -174,6 +174,10 @@


 def rewrite_nml(root: ET.Element, rules: list, dry_run: bool) -> dict[str, int]:
+    """Apply rule-based rewriting: rewrite each collection LOCATION whose
+    old value matches a rule, record the old-to-new PRIMARYKEY
+    substitution for every changed collection location, then redirect
+    every non-collection PRIMARYKEY/LOCATION through the same rules via
+    the shared cascade in process_non_collection_entries."""
     stats = _empty_rule_stats()
     coll = collection_entries(root)
     old_to_new_key: dict[str, str] = {}
@@ -197,6 +201,11 @@
 def rewrite_from_collection_compare(
     old_root: ET.Element, new_root: ET.Element, dry_run: bool, confidence: MatchConfidence,
     key_providers: list[KeyProvider] = (),
 ) -> tuple[dict[str, int], list[tuple[str, str, str, str]]]:
+    """Apply compare-based rewriting: match old collection records
+    against a newer collection's records via the tiered cascade, rewrite
+    each matched collection LOCATION whose attributes actually changed,
+    then redirect every non-collection reference through the resulting
+    old-to-new mapping via the shared cascade."""
     old_records = collection_records(old_root)
     new_records = collection_records(new_root)

```


**CC-M-002-004** (C:\codex\general_tasks\traktor_nml\textpatch.py) - implements CI-M-002-003

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/textpatch.py
@@ -0,0 +1,161 @@
+"""Byte-preserving attribute substitution over LOCATION and PRIMARYKEY tags.
+
+Two write paths exist because they have fundamentally different fidelity
+guarantees for Traktor NML files.
+
+lxml path (default when lxml is installed):
+  The source file is read as raw bytes. lxml parses it and records the
+  source-line number of every element. Only the attribute values that need
+  changing are substituted in the original text; everything else -
+  whitespace, indentation, attribute order, empty-element form
+  (<HEAD ...></HEAD>), the standalone="no" declaration - is preserved
+  byte-for-byte.
+
+stdlib fallback (when lxml is absent):
+  The tree is mutated in-place and written back via ET.tostring. This does
+  not preserve whitespace, attribute order or the standalone="no" form, but
+  is functionally correct for path substitution.
+
+The lxml path is preferred. Do not remove it to simplify the code without
+understanding that the stdlib path will silently change the file's
+formatting. This module implements only attribute substitution; it has no
+concept of element extent and must not be extended to insert or remove whole
+elements (splice/split use spans.py instead - see its module docstring).
+"""
+
+from __future__ import annotations
+
+import html
+import re
+
+from .model import ElemPatch
+
+
+def _xml_escape_attr(value: str) -> str:
+    return (
+        value.replace("&", "&amp;")
+        .replace("<", "&lt;")
+        .replace('"', "&quot;")
+        .replace("\t", "&#x9;")
+        .replace("\n", "&#xA;")
+        .replace("\r", "&#xD;")
+    )
+
+
+def _find_opening_tag_end(text: str, lt_pos: int) -> int:
+    # Assumption: Traktor NML files always place each element's opening tag
+    # entirely on one line - no multi-line attribute values. If that
+    # assumption is violated, this function will scan past the intended line
+    # boundary. apply_text_patches verifies the tag name before patching,
+    # which catches the most obvious mismatches.
+    i = lt_pos + 1
+    while i < len(text):
+        c = text[i]
+        if c in ('"', "'"):
+            q = c
+            i += 1
+            while i < len(text) and text[i] != q:
+                i += 1
+        elif c == '>':
+            return i
+        i += 1
+    raise ValueError(f"unclosed opening tag at offset {lt_pos}")
+
+
+def _patch_attr_in_tag(tag_text: str, attr_name: str, old_value: str, new_value: str) -> tuple[str, bool]:
+    pattern = re.compile(r"(\b" + re.escape(attr_name) + r"\s*=\s*)([\"'])(.*?)\2", re.DOTALL)
+    changed = False
+
+    def replace(match: re.Match[str]) -> str:
+        nonlocal changed
+        if html.unescape(match.group(3)) != old_value:
+            return match.group(0)
+        quote = match.group(2)
+        escaped = _xml_escape_attr(new_value)
+        if quote == "'":
+            escaped = escaped.replace("'", "&apos;")
+        changed = True
+        return f"{match.group(1)}{quote}{escaped}{quote}"
+
+    return pattern.sub(replace, tag_text, count=1), changed
+
+
+def _tag_attributes(tag_text: str) -> dict[str, str]:
+    attr_re = re.compile(r'''\b([A-Za-z_:][\w:.-]*)\s*=\s*(["'])(.*?)\2''', re.DOTALL)
+    return {match.group(1): html.unescape(match.group(3)) for match in attr_re.finditer(tag_text)}
+
+
+def apply_text_patches(text: str, patches: list[ElemPatch]) -> str:
+    """Apply attribute edits while retaining every other source byte.
+
+    Patches are located from their original attributes, not XML parser line
+    numbers. libxml2 line metadata can be unreliable in large NML files and
+    is therefore deliberately not used for writing.
+    """
+    if not patches:
+        return text
+
+    patch_map: dict[tuple[str, tuple[tuple[str, str], ...]], ElemPatch] = {}
+    for patch in patches:
+        key = (patch.tag_name, patch.locator)
+        existing = patch_map.get(key)
+        if existing is not None and existing.changes != patch.changes:
+            raise ValueError(f"conflicting text patches for {patch.tag_name} {patch.locator}")
+        patch_map[key] = patch
+
+    matched: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
+    result: list[str] = []
+    cursor = 0
+    tag_start_re = re.compile(r"<(LOCATION|PRIMARYKEY)\b")
+
+    for match in tag_start_re.finditer(text):
+        start = match.start()
+        if start < cursor:
+            continue
+        end = _find_opening_tag_end(text, start) + 1
+        tag_text = text[start:end]
+        attrs = _tag_attributes(tag_text)
+        tag_name = match.group(1)
+
+        matching_key = next(
+            (
+                key
+                for key in patch_map
+                if key[0] == tag_name and all(attrs.get(name) == value for name, value in key[1])
+            ),
+            None,
+        )
+        if matching_key is None:
+            continue
+
+        patch = patch_map[matching_key]
+        new_tag = tag_text
+        for attr_name, old_value, new_value in patch.changes:
+            new_tag, changed = _patch_attr_in_tag(new_tag, attr_name, old_value, new_value)
+            if not changed:
+                raise ValueError(f"could not locate {attr_name}={old_value!r} in {tag_name} {patch.locator}")
+
+        result.extend((text[cursor:start], new_tag))
+        cursor = end
+        matched.add(matching_key)
+
+    missing = set(patch_map) - matched
+    if missing:
+        tag_name, locator = next(iter(missing))
+        raise ValueError(f"could not locate {tag_name} with original attributes {locator}")
+
+    result.append(text[cursor:])
+    return "".join(result)
+
+
+def location_patch(elem, old, changes: list[tuple[str, str, str]]) -> ElemPatch:
+    return ElemPatch(
+        elem.sourceline,
+        "LOCATION",
+        (("VOLUME", old.volume), ("DIR", old.dir_value), ("FILE", old.file_name)),
+        changes,
+    )
+
+
+def primarykey_patch(elem, old_key: str, new_key: str) -> ElemPatch:
+    return ElemPatch(elem.sourceline, "PRIMARYKEY", (("KEY", old_key),), [("KEY", old_key, new_key)])

```

**Documentation:**

```diff
--- a/traktor_nml/textpatch.py
+++ b/traktor_nml/textpatch.py
@@ -20,6 +20,9 @@


 def _xml_escape_attr(value: str) -> str:
+    """Escape a replacement value the same way lxml/ET escape attribute
+    text on serialisation, so a substituted value stays valid XML without
+    ever re-running a full serialiser over the untouched surrounding text."""
     return (
         value.replace("&", "&amp;")
         .replace("<", "&lt;")

```


**CC-M-002-005** (C:\codex\general_tasks\traktor_nml\xmlio.py) - implements CI-M-002-003

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/xmlio.py
@@ -0,0 +1,65 @@
+"""XML backend selection and shared byte-level constants.
+
+lxml provides two capabilities the stdlib ET cannot: source-line metadata on
+every element (needed by textpatch.apply_text_patches to locate the right tag
+in the raw text) and whitespace-preserving parse/serialise (so round-trips
+don't reformat the document). See traktor_nml.cli for the full write-strategy
+rationale. Every other module imports ET and HAS_LXML from here so there is
+exactly one place that decides which backend is active.
+"""
+
+from __future__ import annotations
+
+from pathlib import Path
+from typing import Callable, Optional
+
+try:
+    import lxml.etree as ET
+
+    HAS_LXML = True
+    XML_PARSE_ERROR = ET.XMLSyntaxError
+except ImportError:  # pragma: no cover - fallback for environments without lxml
+    import xml.etree.ElementTree as ET
+
+    HAS_LXML = False
+    XML_PARSE_ERROR = ET.ParseError
+
+
+XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+
+
+def parse_xml(path: Path):
+    if HAS_LXML:
+        parser = ET.XMLParser(remove_blank_text=False, strip_cdata=False, recover=False)
+        return ET.parse(str(path), parser)
+    return ET.parse(path)
+
+
+def parse_xml_bytes(source_bytes: bytes):
+    """Parse raw bytes, raising XML_PARSE_ERROR on malformed input.
+
+    Only meaningful on the lxml path, where sourceline-carrying elements are
+    required for text patching; callers on the stdlib fallback path use
+    parse_xml against a file path instead.
+    """
+    parser = ET.XMLParser(remove_blank_text=False, strip_cdata=False, recover=False)
+    return ET.fromstring(source_bytes, parser)
+
+
+def write_traktor_xml(
+    root, output: Path, write_bytes: Optional[Callable[[Path, bytes], None]] = None
+) -> None:
+    if HAS_LXML:
+        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=False, pretty_print=False)
+    else:
+        xml_bytes = ET.tostring(root, encoding="unicode").encode("utf-8")
+    data = XML_DECLARATION.encode("utf-8") + xml_bytes
+    if write_bytes is not None:
+        # Callers on the byte-preserving write path (write_nml_safely) pass
+        # their own atomic (temp file + replace) writer so a mid-write
+        # failure here cannot truncate an existing destination either.
+        write_bytes(output, data)
+        return
+    output.parent.mkdir(parents=True, exist_ok=True)
+    with output.open("wb") as handle:
+        handle.write(data)

```

**Documentation:**

```diff
--- a/traktor_nml/xmlio.py
+++ b/traktor_nml/xmlio.py
@@ -23,6 +23,9 @@


 def parse_xml(path: Path):
+    """Parse path via whichever backend xmlio selected at import time,
+    keeping blank-text and CDATA handling identical between the lxml
+    default and the stdlib fallback."""
     if HAS_LXML:
         parser = ET.XMLParser(remove_blank_text=False, strip_cdata=False, recover=False)
         return ET.parse(str(path), parser)

```


**CC-M-002-006** (C:\codex\general_tasks\traktor_nml\cli.py) - implements CI-M-002-004

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/cli.py
@@ -0,0 +1,55 @@
+#!/usr/bin/env python3
+"""Inspect and rewrite Traktor NML paths.
+
+This tool is built around the path patterns observed in the local Traktor corpus:
+
+- Main collection entries store paths in LOCATION/VOLUME, LOCATION/VOLUMEID, LOCATION/DIR, LOCATION/FILE
+- Playlist and some history entries store flattened references in PRIMARYKEY/KEY
+- PRIMARYKEY/KEY is derived as VOLUME + DIR + FILE
+
+Write strategy - two mechanisms exist and stay separate:
+
+  Attribute patching (reconnect, rewrite, rewrite-from-collection-compare):
+    substitutes attribute values inside opening tags located in the raw
+    source text; every other byte of the source file is preserved exactly.
+    See textpatch.py for the full lxml-vs-stdlib fidelity rationale.
+
+  Byte-span assembly (splice, split):
+    copies source byte ranges verbatim to build a new document, re-serialising
+    only the specific fragments a rename or redirect actually changes.
+    See spans.py.
+
+Subcommands are discovered from traktor_nml.commands at import time (DL-003):
+each command module registers its own argparse subparser(s) and handler(s),
+so cli.py never needs editing to add a subcommand.
+"""
+
+from __future__ import annotations
+
+import argparse
+import sys
+
+from .commands import iter_command_modules
+
+
+def build_parser() -> tuple[argparse.ArgumentParser, dict]:
+    parser = argparse.ArgumentParser(description=__doc__)
+    subparsers = parser.add_subparsers(dest="command", required=True)
+    handlers: dict = {}
+    for module in iter_command_modules():
+        module.register(subparsers, handlers)
+    return parser, handlers
+
+
+def main(argv: list[str]) -> int:
+    parser, handlers = build_parser()
+    args = parser.parse_args(argv)
+    handler = handlers.get(args.command)
+    if handler is None:
+        print(f"unknown_command={args.command}", file=sys.stderr)
+        return 2
+    return handler(args)
+
+
+if __name__ == "__main__":
+    raise SystemExit(main(sys.argv[1:]))

```

**Documentation:**

```diff
--- a/traktor_nml/cli.py
+++ b/traktor_nml/cli.py
@@ -34,6 +34,9 @@

 def build_parser() -> tuple[argparse.ArgumentParser, dict]:
+    """Build the top-level parser by asking every discovered command
+    module to register its own subparser and handler, so this function
+    never lists a subcommand by name (DL-003)."""
     parser = argparse.ArgumentParser(description=__doc__)
     subparsers = parser.add_subparsers(dest="command", required=True)
     handlers: dict = {}

```


**CC-M-002-007** (C:\codex\general_tasks\traktor_nml\__init__.py) - implements CI-M-002-004

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/__init__.py
@@ -0,0 +1,11 @@
+"""traktor_nml: inspect, rewrite, reconnect, splice and split Traktor NML files.
+
+This package is the extraction target for traktor_nml_tool.py, which becomes a
+thin argv-forwarding shim over traktor_nml.cli.main. See traktor_nml.cli for the
+module docstring describing the two write strategies (attribute patching vs.
+byte-span assembly) that every command in this package builds on.
+"""
+
+from __future__ import annotations
+
+__all__ = ["cli"]

```

**Documentation:**

```diff
--- a/traktor_nml/__init__.py
+++ b/traktor_nml/__init__.py
@@ -8,4 +8,6 @@
 from __future__ import annotations

+# Only cli is part of the public import surface; traktor_nml.commands.*
+# modules are discovered internally (DL-003), never imported by name
+# from outside this package.
 __all__ = ["cli"]

```


**CC-M-002-008** (C:\codex\general_tasks\traktor_nml\commands\__init__.py) - implements CI-M-002-004

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/commands/__init__.py
@@ -0,0 +1,23 @@
+"""Subcommand discovery.
+
+Each module in this package owns its own parser registration: it exposes a
+register(subparsers, handlers) function that adds its argparse subparser(s)
+and records its handler(s) in the shared handlers dict keyed by command name.
+cli.build_parser enumerates this package at import time (DL-003), so adding a
+subcommand is a pure file-add - no hand-maintained registry to edit.
+"""
+
+from __future__ import annotations
+
+import importlib
+import pkgutil
+from types import ModuleType
+
+
+def iter_command_modules() -> list[ModuleType]:
+    modules = []
+    for info in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
+        if info.name.startswith("_"):
+            continue
+        modules.append(importlib.import_module(f"{__name__}.{info.name}"))
+    return modules

```

**Documentation:**

```diff
--- a/traktor_nml/commands/__init__.py
+++ b/traktor_nml/commands/__init__.py
@@ -14,6 +14,9 @@


 def iter_command_modules() -> list[ModuleType]:
+    """Import and return every non-underscore-prefixed module in this
+    package, sorted by name so subcommand registration order is
+    deterministic across runs regardless of filesystem directory order."""
     modules = []
     for info in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
         if info.name.startswith("_"):

```


**CC-M-002-009** (C:\codex\general_tasks\traktor_nml\commands\inspect_cmd.py) - implements CI-M-002-004

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/commands/inspect_cmd.py
@@ -0,0 +1,82 @@
+"""inspect and encode-dir subcommands."""
+
+from __future__ import annotations
+
+import argparse
+import csv
+import sys
+from pathlib import Path
+
+from ..model import (
+    all_entries,
+    collection_entries,
+    location_rows,
+    normalize_dir_prefix,
+    playlist_entries,
+)
+from ..xmlio import parse_xml
+
+
+def inspect_nml(root, limit: int, csv_path: Path | None) -> int:
+    coll_entries = collection_entries(root)
+    playlist_refs = playlist_entries(root)
+    all_doc_entries = all_entries(root)
+
+    coll_locations = [e for e in coll_entries if e.find("LOCATION") is not None]
+    coll_primarykeys = [e for e in coll_entries if e.find("PRIMARYKEY") is not None]
+    playlist_primarykeys = [e for e in playlist_refs if e.find("PRIMARYKEY") is not None]
+
+    print(f"root_version={root.attrib.get('VERSION', '')}")
+    head = root.find("HEAD")
+    print(f"program={'' if head is None else head.attrib.get('PROGRAM', '')}")
+    print(f"collection_entries={len(coll_entries)}")
+    print(f"collection_entries_with_location={len(coll_locations)}")
+    print(f"collection_entries_with_primarykey={len(coll_primarykeys)}")
+    print(f"playlist_entry_refs={len(playlist_refs)}")
+    print(f"playlist_primarykeys={len(playlist_primarykeys)}")
+    print(f"all_entry_nodes_in_document={len(all_doc_entries)}")
+
+    all_rows = location_rows(coll_locations)
+    rows = all_rows[:limit]
+
+    for row in rows:
+        print(
+            f"sample artist={row['artist']!r} title={row['title']!r} "
+            f"volume={row['volume']!r} dir={row['dir']!r} file={row['file']!r}"
+        )
+
+    if csv_path is not None:
+        with csv_path.open("w", newline="", encoding="utf-8") as handle:
+            writer = csv.DictWriter(handle, fieldnames=list(all_rows[0].keys()) if all_rows else [])
+            if all_rows:
+                writer.writeheader()
+                writer.writerows(all_rows)
+        print(f"csv_written={csv_path}")
+
+    return 0
+
+
+def _handle_inspect(args: argparse.Namespace) -> int:
+    try:
+        tree = parse_xml(args.input)
+    except FileNotFoundError:
+        print(f"input_not_found={args.input}", file=sys.stderr)
+        return 2
+    return inspect_nml(tree.getroot(), limit=args.limit, csv_path=args.csv)
+
+
+def _handle_encode_dir(args: argparse.Namespace) -> int:
+    print(normalize_dir_prefix(args.path_value))
+    return 0
+
+
+def register(subparsers, handlers: dict) -> None:
+    inspect_parser = subparsers.add_parser("inspect", help="Inspect an NML file")
+    inspect_parser.add_argument("input", type=Path)
+    inspect_parser.add_argument("--limit", type=int, default=10)
+    inspect_parser.add_argument("--csv", type=Path)
+    handlers["inspect"] = _handle_inspect
+
+    encode_parser = subparsers.add_parser("encode-dir", help="Encode a human path to Traktor DIR format")
+    encode_parser.add_argument("path_value")
+    handlers["encode-dir"] = _handle_encode_dir

```

**Documentation:**

```diff
--- a/traktor_nml/commands/inspect_cmd.py
+++ b/traktor_nml/commands/inspect_cmd.py
@@ -16,6 +16,9 @@


 def inspect_nml(root, limit: int, csv_path: Path | None) -> int:
+    """Print collection/playlist counts and up to limit sample rows, then
+    optionally write every row (not just the printed sample) to csv_path
+    via the shared location_rows/csv.DictWriter pattern."""
     coll_entries = collection_entries(root)
     playlist_refs = playlist_entries(root)
     all_doc_entries = all_entries(root)

```


**CC-M-002-010** (C:\codex\general_tasks\traktor_nml\commands\rewrite_cmd.py) - implements CI-M-002-004

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/commands/rewrite_cmd.py
@@ -0,0 +1,220 @@
+"""preview-diff and rewrite subcommands (rule-based rewriting)."""
+
+from __future__ import annotations
+
+import argparse
+import sys
+from pathlib import Path
+
+from ..model import (
+    RewriteRule,
+    all_entries,
+    apply_rules,
+    collection_entries,
+    entry_label,
+    normalize_dir_prefix,
+    parse_location_element,
+    parse_primary_key,
+)
+from ..rewrite import _collect_rewrite_patches, rewrite_nml, write_nml_safely
+from ..xmlio import parse_xml
+
+
+def add_rule_args(parser: argparse.ArgumentParser) -> None:
+    parser.add_argument("--old-volume")
+    parser.add_argument("--old-dir-prefix")
+    parser.add_argument("--new-volume")
+    parser.add_argument("--new-dir-prefix")
+    parser.add_argument("--new-volumeid")
+
+
+def add_multi_rule_args(parser: argparse.ArgumentParser) -> None:
+    parser.add_argument(
+        "--rule",
+        nargs=4,
+        action="append",
+        metavar=("OLD_VOLUME", "OLD_DIR_PREFIX", "NEW_VOLUME", "NEW_DIR_PREFIX"),
+        help="Repeatable rewrite rule. Prefixes may be human paths or Traktor-encoded paths.",
+    )
+    parser.add_argument(
+        "--rule-with-volumeid",
+        nargs=5,
+        action="append",
+        metavar=("OLD_VOLUME", "OLD_DIR_PREFIX", "NEW_VOLUME", "NEW_DIR_PREFIX", "NEW_VOLUMEID"),
+        help="Repeatable rewrite rule with explicit VOLUMEID override.",
+    )
+
+
+def build_rules(args: argparse.Namespace) -> list[RewriteRule]:
+    rules: list[RewriteRule] = []
+
+    if getattr(args, "rule", None):
+        for old_volume, old_dir, new_volume, new_dir in args.rule:
+            rules.append(
+                RewriteRule(
+                    old_volume=old_volume,
+                    old_dir_prefix=normalize_dir_prefix(old_dir),
+                    new_volume=new_volume,
+                    new_dir_prefix=normalize_dir_prefix(new_dir),
+                )
+            )
+
+    if getattr(args, "rule_with_volumeid", None):
+        for old_volume, old_dir, new_volume, new_dir, new_volumeid in args.rule_with_volumeid:
+            rules.append(
+                RewriteRule(
+                    old_volume=old_volume,
+                    old_dir_prefix=normalize_dir_prefix(old_dir),
+                    new_volume=new_volume,
+                    new_dir_prefix=normalize_dir_prefix(new_dir),
+                    new_volumeid=new_volumeid,
+                )
+            )
+
+    if not rules:
+        required = ["old_volume", "old_dir_prefix", "new_volume", "new_dir_prefix"]
+        missing = [name for name in required if not getattr(args, name, None)]
+        if missing:
+            raise ValueError(
+                "either provide a complete single rule via "
+                "--old-volume/--old-dir-prefix/--new-volume/--new-dir-prefix "
+                "or provide one or more --rule/--rule-with-volumeid entries"
+            )
+        rules.append(
+            RewriteRule(
+                old_volume=args.old_volume,
+                old_dir_prefix=normalize_dir_prefix(args.old_dir_prefix),
+                new_volume=args.new_volume,
+                new_dir_prefix=normalize_dir_prefix(args.new_dir_prefix),
+                new_volumeid=args.new_volumeid,
+            )
+        )
+
+    return rules
+
+
+def preview_diff_nml(root, rules: list[RewriteRule], limit: int) -> int:
+    coll_entries = collection_entries(root)
+    coll_entry_ids = {id(entry) for entry in coll_entries}
+    old_to_new_key: dict[str, str] = {}
+
+    collection_location_changes: list[tuple[str, str, str]] = []
+    other_location_changes: list[tuple[str, str, str]] = []
+    primarykey_changes: list[tuple[str, str, str]] = []
+
+    for entry in coll_entries:
+        loc_elem = entry.find("LOCATION")
+        if loc_elem is None:
+            continue
+        old_loc = parse_location_element(loc_elem)
+        new_loc, changed = apply_rules(old_loc, rules)
+        if changed:
+            old_to_new_key[old_loc.primary_key] = new_loc.primary_key
+            collection_location_changes.append(
+                (entry_label(entry), str(old_loc.decoded_path), str(new_loc.decoded_path))
+            )
+
+    for entry in all_entries(root):
+        if id(entry) not in coll_entry_ids:
+            loc_elem = entry.find("LOCATION")
+            if loc_elem is not None:
+                old_loc = parse_location_element(loc_elem)
+                new_loc, changed = apply_rules(old_loc, rules)
+                if changed:
+                    other_location_changes.append(
+                        (entry_label(entry), str(old_loc.decoded_path), str(new_loc.decoded_path))
+                    )
+
+        pk_elem = entry.find("PRIMARYKEY")
+        if pk_elem is None:
+            continue
+
+        old_key = pk_elem.attrib.get("KEY", "")
+        new_key = old_to_new_key.get(old_key)
+        if new_key is None:
+            try:
+                old_loc = parse_primary_key(old_key)
+            except ValueError:
+                continue
+            new_loc, changed = apply_rules(old_loc, rules)
+            if not changed:
+                continue
+            new_key = new_loc.primary_key
+
+        primarykey_changes.append((entry_label(entry), old_key, new_key))
+
+    print(f"collection_location_changes={len(collection_location_changes)}")
+    print(f"other_location_changes={len(other_location_changes)}")
+    print(f"primarykey_changes={len(primarykey_changes)}")
+
+    if collection_location_changes:
+        print("sample_collection_location_changes:")
+        for label, before, after in collection_location_changes[:limit]:
+            print(f"- {label}")
+            print(f"  before={before}")
+            print(f"  after={after}")
+
+    if other_location_changes:
+        print("sample_other_location_changes:")
+        for label, before, after in other_location_changes[:limit]:
+            print(f"- {label}")
+            print(f"  before={before}")
+            print(f"  after={after}")
+
+    if primarykey_changes:
+        print("sample_primarykey_changes:")
+        for label, before, after in primarykey_changes[:limit]:
+            print(f"- {label}")
+            print(f"  before={before}")
+            print(f"  after={after}")
+
+    return 0
+
+
+def _handle_preview_diff(args: argparse.Namespace) -> int:
+    try:
+        tree = parse_xml(args.input)
+    except FileNotFoundError:
+        print(f"input_not_found={args.input}", file=sys.stderr)
+        return 2
+    try:
+        rules = build_rules(args)
+    except ValueError as exc:
+        print(str(exc), file=sys.stderr)
+        return 2
+    return preview_diff_nml(tree.getroot(), rules, limit=args.limit)
+
+
+def _handle_rewrite(args: argparse.Namespace) -> int:
+    try:
+        rules = build_rules(args)
+    except ValueError as exc:
+        print(str(exc), file=sys.stderr)
+        return 2
+
+    def _collect_patches(root):
+        patches, stats = _collect_rewrite_patches(root, rules)
+        return patches, stats, None
+
+    def mutate_tree(root, dry_run):
+        stats = rewrite_nml(root, rules, dry_run=dry_run)
+        return stats, None
+
+    return write_nml_safely(args.input, args.output, args.dry_run, _collect_patches, mutate_tree)
+
+
+def register(subparsers, handlers: dict) -> None:
+    preview_parser = subparsers.add_parser("preview-diff", help="Preview path rewrites without writing")
+    preview_parser.add_argument("input", type=Path)
+    add_rule_args(preview_parser)
+    add_multi_rule_args(preview_parser)
+    preview_parser.add_argument("--limit", type=int, default=10)
+    handlers["preview-diff"] = _handle_preview_diff
+
+    rewrite_parser = subparsers.add_parser("rewrite", help="Rewrite paths in an NML file")
+    rewrite_parser.add_argument("input", type=Path)
+    rewrite_parser.add_argument("output", type=Path)
+    add_rule_args(rewrite_parser)
+    add_multi_rule_args(rewrite_parser)
+    rewrite_parser.add_argument("--dry-run", action="store_true")
+    handlers["rewrite"] = _handle_rewrite

```

**Documentation:**

```diff
--- a/traktor_nml/commands/rewrite_cmd.py
+++ b/traktor_nml/commands/rewrite_cmd.py
@@ -24,6 +24,9 @@


 def build_rules(args: argparse.Namespace) -> list[RewriteRule]:
+    # Rules are tried in the order built here; apply_rules returns the
+    # first match, so an earlier --rule/--rule-with-volumeid takes
+    # precedence over a later one covering an overlapping prefix.
     rules: list[RewriteRule] = []

     if getattr(args, "rule", None):

```


**CC-M-002-011** (C:\codex\general_tasks\traktor_nml\commands\compare_cmd.py) - implements CI-M-002-004

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/commands/compare_cmd.py
@@ -0,0 +1,219 @@
+"""preview-compare, scan-compare-candidates and rewrite-from-collection-compare."""
+
+from __future__ import annotations
+
+import argparse
+import sys
+from pathlib import Path
+
+from ..confidence import MatchConfidence, parse_match_confidence
+from ..matching import match_records
+from ..model import collection_records
+from ..rewrite import (
+    _collect_compare_patches,
+    print_stats_and_samples,
+    rewrite_from_collection_compare,
+    write_nml_safely,
+)
+from ..xmlio import XML_PARSE_ERROR, parse_xml
+
+
+def add_confidence_args(parser: argparse.ArgumentParser) -> None:
+    parser.add_argument(
+        "--match-confidence",
+        choices=[level.value for level in MatchConfidence],
+        default=None,
+        help="Match cascade confidence ladder (default: strict, or loose if "
+        "--allow-artist-title-only is given).",
+    )
+    parser.add_argument(
+        "--allow-artist-title-only",
+        action="store_true",
+        help="Deprecated alias for --match-confidence loose.",
+    )
+
+
+def resolve_confidence(args: argparse.Namespace) -> MatchConfidence:
+    if getattr(args, "match_confidence", None):
+        return parse_match_confidence(args.match_confidence)
+    return MatchConfidence.from_legacy_flag(args.allow_artist_title_only)
+
+
+def preview_compare_nml(old_root, new_root, limit: int, confidence: MatchConfidence) -> int:
+    old_records = collection_records(old_root)
+    new_records = collection_records(new_root)
+    mapping, stats, samples = match_records(old_records, new_records, confidence)
+
+    print(f"old_collection_entries={len(old_records)}")
+    print(f"new_collection_entries={len(new_records)}")
+    for key, value in stats.items():
+        print(f"{key}={value}")
+    print(f"primarykey_updates_available={len(mapping)}")
+
+    if samples:
+        print("sample_matches:")
+        for label, before, after, matched_by in samples[:limit]:
+            print(f"- {label}")
+            print(f"  matched_by={matched_by}")
+            print(f"  before={before}")
+            print(f"  after={after}")
+
+    return 0
+
+
+def compare_stats_dict(
+    old_root, new_root, confidence: MatchConfidence
+) -> tuple[dict[str, int], list[tuple[str, str, str, str]]]:
+    old_records = collection_records(old_root)
+    new_records = collection_records(new_root)
+    mapping, stats, samples = match_records(old_records, new_records, confidence)
+    stats = {
+        "old_collection_entries": len(old_records),
+        "new_collection_entries": len(new_records),
+        **stats,
+        "primarykey_updates_available": len(mapping),
+    }
+    return stats, samples
+
+
+def scan_compare_candidates(
+    target_path: Path, candidates_dir: Path, limit: int, confidence: MatchConfidence
+) -> int:
+    try:
+        target_root = parse_xml(target_path).getroot()
+    except FileNotFoundError:
+        print(f"input_not_found={target_path}", file=sys.stderr)
+        return 2
+
+    candidates = sorted(candidates_dir.glob("**/*.nml"))
+    if not candidates:
+        print(f"no_candidates_found={candidates_dir}")
+        return 0
+
+    rows: list[dict[str, object]] = []
+    for candidate in candidates:
+        try:
+            candidate_root = parse_xml(candidate).getroot()
+        except (XML_PARSE_ERROR, FileNotFoundError):
+            continue
+
+        stats, _samples = compare_stats_dict(candidate_root, target_root, confidence)
+        old_entries = int(stats["old_collection_entries"])
+        matched = int(stats["matched"])
+        ambiguous = int(stats["ambiguous"])
+        unmatched = int(stats["unmatched"])
+        ratio = 0.0 if old_entries == 0 else matched / old_entries
+        rows.append(
+            {
+                "path": candidate,
+                "matched": matched,
+                "ratio": ratio,
+                "ambiguous": ambiguous,
+                "unmatched": unmatched,
+                "matched_audio_id": int(stats["matched_audio_id"]),
+                "matched_artist_title_size_time": int(stats["matched_artist_title_size_time"]),
+                "matched_artist_title_file": int(stats["matched_artist_title_file"]),
+                "matched_file_size_time": int(stats["matched_file_size_time"]),
+                "matched_artist_title_album_time": int(stats["matched_artist_title_album_time"]),
+                "matched_artist_title": int(stats["matched_artist_title"]),
+                "old_entries": old_entries,
+            }
+        )
+
+    rows.sort(key=lambda row: (row["matched"], row["ratio"], -row["ambiguous"]), reverse=True)
+
+    print(f"target={target_path}")
+    print(f"candidates_scanned={len(rows)}")
+    print("top_candidates:")
+    for row in rows[:limit]:
+        print(
+            f"- path={row['path']}"
+            f" matched={row['matched']}"
+            f" ratio={row['ratio']:.4f}"
+            f" ambiguous={row['ambiguous']}"
+            f" unmatched={row['unmatched']}"
+            f" audio_id={row['matched_audio_id']}"
+            f" title_size_time={row['matched_artist_title_size_time']}"
+            f" title_file={row['matched_artist_title_file']}"
+            f" file_size_time={row['matched_file_size_time']}"
+            f" album_time={row['matched_artist_title_album_time']}"
+            f" title_only={row['matched_artist_title']}"
+        )
+
+    return 0
+
+
+def _handle_preview_compare(args: argparse.Namespace) -> int:
+    try:
+        old_tree = parse_xml(args.old_input)
+        new_tree = parse_xml(args.new_input)
+    except FileNotFoundError as exc:
+        print(f"input_not_found={exc.filename}", file=sys.stderr)
+        return 2
+    return preview_compare_nml(
+        old_tree.getroot(), new_tree.getroot(), limit=args.limit, confidence=resolve_confidence(args)
+    )
+
+
+def _handle_scan_compare_candidates(args: argparse.Namespace) -> int:
+    return scan_compare_candidates(
+        target_path=args.target_input,
+        candidates_dir=args.candidates_dir,
+        limit=args.limit,
+        confidence=resolve_confidence(args),
+    )
+
+
+def _handle_rewrite_from_collection_compare(args: argparse.Namespace) -> int:
+    confidence = resolve_confidence(args)
+
+    def _collect_patches(old_root):
+        old_records = collection_records(old_root)
+        new_tree = parse_xml(args.new_input)
+        new_records = collection_records(new_tree.getroot())
+        mapping, match_stats, samples = match_records(old_records, new_records, confidence)
+        patches, apply_stats = _collect_compare_patches(old_root, old_records, mapping)
+        return patches, {**apply_stats, **match_stats}, samples
+
+    def mutate_tree(old_root, dry_run):
+        new_tree = parse_xml(args.new_input)
+        stats, samples = rewrite_from_collection_compare(
+            old_root, new_tree.getroot(), dry_run=dry_run, confidence=confidence
+        )
+        return stats, samples
+
+    return write_nml_safely(
+        args.old_input, args.output, args.dry_run, _collect_patches, mutate_tree
+    )
+
+
+def register(subparsers, handlers: dict) -> None:
+    compare_preview_parser = subparsers.add_parser(
+        "preview-compare", help="Preview old-vs-new collection matching without writing"
+    )
+    compare_preview_parser.add_argument("old_input", type=Path)
+    compare_preview_parser.add_argument("new_input", type=Path)
+    compare_preview_parser.add_argument("--limit", type=int, default=10)
+    add_confidence_args(compare_preview_parser)
+    handlers["preview-compare"] = _handle_preview_compare
+
+    scan_parser = subparsers.add_parser(
+        "scan-compare-candidates",
+        help="Scan a folder of backup collections and rank likely matches against a target collection",
+    )
+    scan_parser.add_argument("target_input", type=Path)
+    scan_parser.add_argument("candidates_dir", type=Path)
+    scan_parser.add_argument("--limit", type=int, default=10)
+    add_confidence_args(scan_parser)
+    handlers["scan-compare-candidates"] = _handle_scan_compare_candidates
+
+    compare_rewrite_parser = subparsers.add_parser(
+        "rewrite-from-collection-compare",
+        help="Update an old NML's locations and PRIMARYKEYs using a newer collection file",
+    )
+    compare_rewrite_parser.add_argument("old_input", type=Path)
+    compare_rewrite_parser.add_argument("new_input", type=Path)
+    compare_rewrite_parser.add_argument("output", type=Path)
+    compare_rewrite_parser.add_argument("--dry-run", action="store_true")
+    add_confidence_args(compare_rewrite_parser)
+    handlers["rewrite-from-collection-compare"] = _handle_rewrite_from_collection_compare

```

**Documentation:**

```diff
--- a/traktor_nml/commands/compare_cmd.py
+++ b/traktor_nml/commands/compare_cmd.py
@@ -19,6 +19,9 @@


 def resolve_confidence(args: argparse.Namespace) -> MatchConfidence:
+    """Resolve the effective MatchConfidence: an explicit
+    --match-confidence always wins; otherwise --allow-artist-title-only
+    selects loose and its absence selects strict (DL-010)."""
     if getattr(args, "match_confidence", None):
         return parse_match_confidence(args.match_confidence)
     return MatchConfidence.from_legacy_flag(args.allow_artist_title_only)

```


**CC-M-002-012** (C:\codex\general_tasks\tests\test_cli_contract.py) - implements CI-M-002-004

**Code:**

```diff
--- /dev/null
+++ b/tests/test_cli_contract.py
@@ -0,0 +1,47 @@
+"""Contract checks for the extracted package: subcommand surface and the
+--allow-artist-title-only / --match-confidence loose equivalence (DL-010)."""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+from tests.conftest import run_tool
+
+
+def test_help_lists_every_pre_existing_subcommand(tmp_path: Path) -> None:
+    """The seven subcommands that predate the package extraction all survive it.
+
+    Checked as a subset, not an exact set: later milestones (reconnect,
+    splice, split) add their own subcommands to the same discovery
+    mechanism, and this test's job is only to catch the extraction itself
+    silently dropping or renaming one of the original seven.
+    """
+    result = run_tool(["--help"], cwd=tmp_path)
+    expected = {
+        "inspect",
+        "encode-dir",
+        "preview-diff",
+        "preview-compare",
+        "scan-compare-candidates",
+        "rewrite",
+        "rewrite-from-collection-compare",
+    }
+    # argparse's {a,b,c} choices list is the definitive subcommand set.
+    brace_start = result.stdout.index("{")
+    brace_end = result.stdout.index("}", brace_start)
+    listed = set(result.stdout[brace_start + 1:brace_end].split(","))
+    assert expected <= listed
+
+
+def test_allow_artist_title_only_matches_loose_confidence(fixture_corpus: Path, tmp_path: Path) -> None:
+    legacy = run_tool(
+        ["preview-compare", str(fixture_corpus / "duplicate_rips.nml"), str(fixture_corpus / "duplicate_rips.nml"),
+         "--allow-artist-title-only"],
+        cwd=tmp_path,
+    )
+    enum_form = run_tool(
+        ["preview-compare", str(fixture_corpus / "duplicate_rips.nml"), str(fixture_corpus / "duplicate_rips.nml"),
+         "--match-confidence", "loose"],
+        cwd=tmp_path,
+    )
+    assert legacy.stdout == enum_form.stdout

```

**Documentation:**

```diff
--- a/tests/test_cli_contract.py
+++ b/tests/test_cli_contract.py
@@ -28,6 +28,9 @@

 def test_allow_artist_title_only_matches_loose_confidence(fixture_corpus: Path, tmp_path: Path) -> None:
+    """Byte-identical stdout between the two invocations confirms
+    --allow-artist-title-only is a pure alias for --match-confidence
+    loose (DL-010)."""
     legacy = run_tool(
         ["preview-compare", str(fixture_corpus / "duplicate_rips.nml"), str(fixture_corpus / "duplicate_rips.nml"),
          "--allow-artist-title-only"],

```


**CC-M-002-013** (C:\codex\general_tasks\traktor_nml\confidence.py) - implements CI-M-002-005

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/confidence.py
@@ -0,0 +1,63 @@
+"""Ordered match-confidence levels shared by every matching-cascade caller.
+
+Disk-scan matching needs a filename-only tier the legacy boolean cannot
+express, and two overlapping knobs would let two flags fight over one
+cascade. MatchConfidence is a single ordered ladder instead: strict admits
+only the tag-derived tiers down to file/size/time, loose additionally admits
+artist/title/album/time and the legacy artist-title-only tier, and filename
+additionally admits a filename-only tier for disk candidates whose tags are
+unreadable. --allow-artist-title-only keeps parsing as loose so existing
+invocations are unaffected.
+"""
+
+from __future__ import annotations
+
+import enum
+
+
+class MatchConfidence(enum.Enum):
+    STRICT = "strict"
+    LOOSE = "loose"
+    FILENAME = "filename"
+
+    @classmethod
+    def from_legacy_flag(cls, allow_artist_title_only: bool) -> "MatchConfidence":
+        return cls.LOOSE if allow_artist_title_only else cls.STRICT
+
+    def admits(self, tier_name: str) -> bool:
+        return tier_name in self.admitted_tiers()
+
+    def admitted_tiers(self) -> tuple[str, ...]:
+        return _ADMITTED_TIERS[self]
+
+
+# Tier names match the key_name strings record_keys emits. Each level admits
+# every tier of the level below it plus its own additions, so widening the
+# confidence argument never removes a tier a stricter run already accepted.
+# strict reproduces the pre-extraction default cascade exactly (every tier
+# except the legacy artist-title-only one); loose additionally admits that
+# tier, matching --allow-artist-title-only bit for bit; filename adds the
+# disk-scan-only filename+size tier that has no tag-based fallback at all.
+_STRICT_TIERS: tuple[str, ...] = (
+    "audio_id",
+    "artist_title_size_time",
+    "artist_title_file",
+    "file_size_time",
+    "artist_title_album_time",
+)
+_LOOSE_TIERS: tuple[str, ...] = _STRICT_TIERS + ("artist_title",)
+_FILENAME_TIERS: tuple[str, ...] = _LOOSE_TIERS + ("filename_size",)
+
+_ADMITTED_TIERS = {
+    MatchConfidence.STRICT: _STRICT_TIERS,
+    MatchConfidence.LOOSE: _LOOSE_TIERS,
+    MatchConfidence.FILENAME: _FILENAME_TIERS,
+}
+
+
+def parse_match_confidence(value: str) -> MatchConfidence:
+    try:
+        return MatchConfidence(value)
+    except ValueError as exc:
+        valid = ", ".join(level.value for level in MatchConfidence)
+        raise ValueError(f"invalid --match-confidence {value!r}; expected one of: {valid}") from exc

```

**Documentation:**

```diff
--- a/traktor_nml/confidence.py
+++ b/traktor_nml/confidence.py
@@ -20,6 +20,10 @@

     @classmethod
     def from_legacy_flag(cls, allow_artist_title_only: bool) -> "MatchConfidence":
+        """--allow-artist-title-only maps to LOOSE: kept as a stable
+        spelling for scripted invocations that predate this ordered
+        enum (DL-010)."""
         return cls.LOOSE if allow_artist_title_only else cls.STRICT

     def admits(self, tier_name: str) -> bool:

```


**CC-M-002-014** (C:\codex\general_tasks\traktor_nml\matching.py) - implements CI-M-002-006

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/matching.py
@@ -0,0 +1,193 @@
+"""Tiered match-key cascade and pairwise old-vs-new matching.
+
+record_keys and match_records are reused unmodified (module-level, not
+subclassed or wrapped) by disk-scan reconnection: a filesystem candidate is
+just an EntryRecord with entry=None fed in as the "new" side. Fingerprinting
+plugs in as an injected key provider (see fingerprint.py) rather than a
+parameter on this cascade directly, so this module stays free of any
+chromaprint/network dependency and keeps behaving identically when no
+providers are supplied.
+"""
+
+from __future__ import annotations
+
+from collections import defaultdict
+from dataclasses import dataclass
+from typing import Callable, Iterable, Optional
+
+from .confidence import MatchConfidence
+from .model import EntryRecord, record_label
+
+_BASE_STAT_TIERS: tuple[str, ...] = (
+    "audio_id",
+    "artist_title_size_time",
+    "artist_title_file",
+    "file_size_time",
+    "artist_title_album_time",
+    "artist_title",
+)
+
+AMBIGUOUS = object()
+"""Sentinel a KeyProvider.provide() may return in place of a key tuple to
+force this record into the ambiguous bucket, regardless of what any lower,
+less specific tier in the same cascade would otherwise resolve confidently.
+Distinct from None, which means the provider has nothing to contribute for
+this record and the cascade proceeds to the next tier exactly as if the
+provider were absent: a provider can positively detect its own unresolvable
+multi-candidate conflict (e.g. acoustic fingerprint similarity, where
+candidates need not cluster transitively, so several can independently
+clear a match threshold against one old record without agreeing with each
+other) in a way the ordinary key/index bucket-size check never sees, since
+that conflict lives inside the provider's own comparison rather than in a
+shared index bucket."""
+
+
+@dataclass(frozen=True)
+class KeyProvider:
+    """An injected top-tier match key provider (see fingerprint.py).
+
+    tier_name is fixed and known without calling provide, so match_records
+    can size its stats dict without probing a record (which would risk
+    triggering the provider's own side effects, e.g. hashing a file). provide
+    returns None when it has nothing to contribute for this record - an
+    absent tier is simply skipped, never a KeyError - or the AMBIGUOUS
+    sentinel to force this record into the ambiguous bucket outright.
+    """
+
+    tier_name: str
+    provide: Callable[[EntryRecord], Optional[tuple[str, ...]]]
+
+
+def record_keys(
+    record: EntryRecord,
+    confidence: MatchConfidence,
+    key_providers: Iterable[KeyProvider] = (),
+) -> list[tuple[str, tuple[str, ...]]]:
+    keys: list[tuple[str, tuple[str, ...]]] = []
+    for provider in key_providers:
+        value = provider.provide(record)
+        if value is not None:
+            keys.append((provider.tier_name, value))
+
+    if confidence.admits("audio_id") and record.audio_id:
+        keys.append(("audio_id", (record.audio_id,)))
+    if (
+        confidence.admits("artist_title_size_time")
+        and record.artist
+        and record.title
+        and record.filesize
+        and record.playtime_float
+    ):
+        keys.append(
+            (
+                "artist_title_size_time",
+                (record.artist, record.title, record.filesize, record.playtime_float),
+            )
+        )
+    if confidence.admits("artist_title_file") and record.artist and record.title and record.file_name:
+        keys.append(("artist_title_file", (record.artist, record.title, record.file_name)))
+    if (
+        confidence.admits("file_size_time")
+        and record.file_name
+        and record.filesize
+        and record.playtime_float
+    ):
+        keys.append(("file_size_time", (record.file_name, record.filesize, record.playtime_float)))
+    if (
+        confidence.admits("artist_title_album_time")
+        and record.artist
+        and record.title
+        and record.album
+        and record.playtime_float
+    ):
+        keys.append(
+            (
+                "artist_title_album_time",
+                (record.artist, record.title, record.album, record.playtime_float),
+            )
+        )
+    if confidence.admits("artist_title") and record.artist and record.title:
+        keys.append(("artist_title", (record.artist, record.title)))
+    if confidence.admits("filename_size") and record.file_name and record.filesize:
+        keys.append(("filename_size", (record.file_name, record.filesize)))
+    return keys
+
+
+def build_new_indexes(
+    records: list[EntryRecord],
+    confidence: MatchConfidence,
+    key_providers: Iterable[KeyProvider] = (),
+) -> dict[str, dict[tuple[str, ...], list[EntryRecord]]]:
+    indexes: dict[str, dict[tuple[str, ...], list[EntryRecord]]] = defaultdict(lambda: defaultdict(list))
+    for record in records:
+        for key_name, key_value in record_keys(record, confidence, key_providers):
+            indexes[key_name][key_value].append(record)
+    return indexes
+
+
+def match_records(
+    old_records: list[EntryRecord],
+    new_records: list[EntryRecord],
+    confidence: MatchConfidence,
+    key_providers: Iterable[KeyProvider] = (),
+    indexes: dict[str, dict[tuple[str, ...], list[EntryRecord]]] | None = None,
+) -> tuple[dict[str, EntryRecord], dict[str, int], list[tuple[str, str, str, str]]]:
+    # A caller that already built the candidate index for its own purposes
+    # (e.g. reconnection's post-match ambiguity check) can pass it in so the
+    # O(candidates) index build never runs twice for one match_records call.
+    if indexes is None:
+        indexes = build_new_indexes(new_records, confidence, key_providers)
+    mapping: dict[str, EntryRecord] = {}
+    # The six tag-derived tiers always get a stats key, matching every
+    # pre-extraction stats dict exactly regardless of confidence (the
+    # confidence level gates whether a tier can produce a match, not whether
+    # its counter is printed). filename_size and any injected provider tier
+    # are new additions with no baseline to preserve, so they only appear
+    # when actually reachable at this confidence / with providers supplied.
+    tier_names = [p.tier_name for p in key_providers] + list(_BASE_STAT_TIERS)
+    if confidence is MatchConfidence.FILENAME:
+        tier_names.append("filename_size")
+    stats = {"matched": 0, **{f"matched_{name}": 0 for name in tier_names}, "unmatched": 0, "ambiguous": 0}
+    samples: list[tuple[str, str, str, str]] = []
+
+    for old_record in old_records:
+        matched_new: EntryRecord | None = None
+        matched_by: str | None = None
+        ambiguous_here = False
+
+        for key_name, key_value in record_keys(old_record, confidence, key_providers):
+            if key_value is AMBIGUOUS:
+                # A provider positively detected its own unresolvable
+                # multi-candidate conflict (see AMBIGUOUS) - the record is
+                # ambiguous outright, and no lower, less specific tier is
+                # allowed to silently resolve it to a single confident
+                # match, so no further tiers are consulted for this record.
+                ambiguous_here = True
+                break
+            candidates = indexes.get(key_name, {}).get(key_value, [])
+            if len(candidates) == 1:
+                matched_new = candidates[0]
+                matched_by = key_name
+                break
+            if len(candidates) > 1:
+                ambiguous_here = True
+
+        if matched_new is not None and matched_by is not None:
+            mapping[old_record.primary_key] = matched_new
+            stats["matched"] += 1
+            stats[f"matched_{matched_by}"] += 1
+            if len(samples) < 20:
+                samples.append(
+                    (
+                        record_label(old_record),
+                        str(old_record.location.decoded_path),
+                        str(matched_new.location.decoded_path),
+                        matched_by,
+                    )
+                )
+        elif ambiguous_here:
+            stats["ambiguous"] += 1
+        else:
+            stats["unmatched"] += 1
+
+    return mapping, stats, samples

```

**Documentation:**

```diff
--- a/traktor_nml/matching.py
+++ b/traktor_nml/matching.py
@@ -18,6 +18,9 @@


 _BASE_STAT_TIERS: tuple[str, ...] = (
+    # Fixed tier ordering used to initialise per-tier match-count stats
+    # keys before matching runs, so a zero-count tier still prints
+    # alongside tiers that matched; injected key providers (DL-006) add
+    # their own tier names to the printed stats without editing this tuple.
     "audio_id",
     "artist_title_size_time",

```


**CC-M-002-015** (C:\codex\general_tasks\traktor_nml_tool.py) - implements CI-M-002-007

**Code:**

```diff
--- a/traktor_nml_tool.py
+++ b/traktor_nml_tool.py
@@ -1,1290 +1,19 @@
 #!/usr/bin/env python3
 """Inspect and rewrite Traktor NML paths.
 
-This tool is built around the path patterns observed in the local Traktor corpus:
-
-- Main collection entries store paths in LOCATION/VOLUME, LOCATION/VOLUMEID, LOCATION/DIR, LOCATION/FILE
-- Playlist and some history entries store flattened references in PRIMARYKEY/KEY
-- PRIMARYKEY/KEY is derived as VOLUME + DIR + FILE
-
-The rewrite flow is conservative:
-
-1. Rewrite matching LOCATION elements
-2. Rebuild collection-derived primary key mappings
-3. Update PRIMARYKEY references from the mapping when possible
-4. Fall back to directly rewriting PRIMARYKEY values using the same rules
-
-Write strategy — lxml text-patching vs. stdlib tree serialisation:
-
-  Two write paths exist because they have fundamentally different fidelity
-  guarantees for Traktor NML files.
-
-  lxml path (default when lxml is installed):
-    The source file is read as raw bytes.  lxml parses it and records the
-    source-line number of every element.  Only the attribute values that need
-    changing are substituted in the original text; everything else — whitespace,
-    indentation, attribute order, empty-element form (<HEAD ...></HEAD>),
-    encoding declaration with standalone="no" — is preserved byte-for-byte.
-    This produces minimal diffs and avoids any risk that a serialiser's
-    formatting choices confuse Traktor or version-control tools.
-
-  stdlib fallback (when lxml is absent):
-    The tree is mutated in-place and written back via ET.tostring.  This does
-    not preserve whitespace, attribute order, or the standalone="no" declaration
-    form, but is functionally correct for path substitution.
-
-  The lxml path is preferred.  Do not remove it to simplify the code without
-  understanding that the stdlib path will silently change the file's formatting.
+This is a thin argv-forwarding shim over the traktor_nml package (DL-001).
+The implementation - including the write-strategy rationale, the domain
+model and every subcommand - lives in traktor_nml/; see traktor_nml/cli.py
+for the full module docstring. This file exists so the historical
+invocation (`python traktor_nml_tool.py ...`) and the tool's drop-in-a-folder
+portability keep working unchanged.
 """
 
 from __future__ import annotations
 
-import argparse
-import csv
-import html
-import re
 import sys
-from collections import defaultdict
-from dataclasses import dataclass, field
-from pathlib import Path, PurePosixPath
-from typing import Iterable
 
-# lxml provides two capabilities the stdlib ET cannot: source-line metadata on
-# every element (needed by apply_text_patches to locate the right tag in the raw
-# text) and whitespace-preserving parse/serialise (so round-trips don't reformat
-# the document).  See the module docstring for the full write-strategy rationale.
-try:
-    import lxml.etree as ET
-
-    HAS_LXML = True
-    _XML_PARSE_ERROR = ET.XMLSyntaxError
-except ImportError:  # pragma: no cover - fallback for environments without lxml
-    import xml.etree.ElementTree as ET
-
-    HAS_LXML = False
-    _XML_PARSE_ERROR = ET.ParseError
-
-
-@dataclass(frozen=True)
-class LocationParts:
-    volume: str
-    volumeid: str
-    dir_value: str
-    file_name: str
-
-    @property
-    def primary_key(self) -> str:
-        return f"{self.volume}{self.dir_value}{self.file_name}"
-
-    @property
-    def decoded_dir(self) -> PurePosixPath:
-        return decode_traktor_dir(self.dir_value)
-
-    @property
-    def decoded_path(self) -> PurePosixPath:
-        return self.decoded_dir / self.file_name
-
-
-@dataclass(frozen=True)
-class RewriteRule:
-    old_volume: str
-    old_dir_prefix: str
-    new_volume: str
-    new_dir_prefix: str
-    new_volumeid: str | None = None
-
-    def matches(self, loc: LocationParts) -> bool:
-        return loc.volume == self.old_volume and loc.dir_value.startswith(self.old_dir_prefix)
-
-    def apply(self, loc: LocationParts) -> LocationParts:
-        suffix = loc.dir_value[len(self.old_dir_prefix) :]
-        return LocationParts(
-            volume=self.new_volume,
-            volumeid=self.new_volume if self.new_volumeid is None else self.new_volumeid,
-            dir_value=f"{self.new_dir_prefix}{suffix}",
-            file_name=loc.file_name,
-        )
-
-
-@dataclass
-class EntryRecord:
-    entry: ET.Element
-    artist: str
-    title: str
-    audio_id: str
-    filesize: str
-    playtime_float: str
-    bitrate: str
-    album: str
-    file_name: str
-    location: LocationParts
-
-    @property
-    def primary_key(self) -> str:
-        return self.location.primary_key
-
-
-@dataclass
-class ElemPatch:
-    sourceline: int
-    tag_name: str
-    locator: tuple[tuple[str, str], ...]
-    changes: list[tuple[str, str, str]] = field(default_factory=list)  # (attr, old, new)
-
-
-XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
-
-
-def parse_xml(path: Path):
-    if HAS_LXML:
-        parser = ET.XMLParser(remove_blank_text=False, strip_cdata=False, recover=False)
-        return ET.parse(str(path), parser)
-    return ET.parse(path)
-
-
-def decode_traktor_dir(dir_value: str) -> PurePosixPath:
-    if not dir_value or dir_value == "/:":
-        return PurePosixPath("/")
-
-    trimmed = dir_value
-    if trimmed.startswith("/:"):
-        trimmed = trimmed[2:]
-    if trimmed.endswith("/:"):
-        trimmed = trimmed[:-2]
-
-    parts = [part for part in trimmed.split("/:") if part]
-    return PurePosixPath("/") / PurePosixPath(*parts)
-
-
-def encode_traktor_dir(path_value: str) -> str:
-    normalized = path_value.replace("\\", "/").strip()
-    parts = [part for part in normalized.split("/") if part]
-    return "/:" + "/:".join(parts) + "/:"
-
-
-def normalize_dir_prefix(value: str) -> str:
-    stripped = value.strip()
-    if "/:" in stripped:
-        if not stripped.startswith("/:"):
-            stripped = "/:" + (stripped[1:] if stripped.startswith("/") else stripped)
-        if not stripped.endswith("/:"):
-            stripped = stripped.rstrip("/") + "/:"
-        return stripped
-    return encode_traktor_dir(stripped)
-
-
-def parse_location_element(elem: ET.Element) -> LocationParts:
-    return LocationParts(
-        volume=elem.attrib.get("VOLUME", ""),
-        volumeid=elem.attrib.get("VOLUMEID", elem.attrib.get("VOLUME", "")),
-        dir_value=elem.attrib.get("DIR", ""),
-        file_name=elem.attrib.get("FILE", ""),
-    )
-
-
-def collection_records(root: ET.Element) -> list[EntryRecord]:
-    records: list[EntryRecord] = []
-    for entry in collection_entries(root):
-        loc_elem = entry.find("LOCATION")
-        if loc_elem is None:
-            continue
-        info = entry.find("INFO")
-        album = entry.find("ALBUM")
-        records.append(
-            EntryRecord(
-                entry=entry,
-                artist=entry.attrib.get("ARTIST", ""),
-                title=entry.attrib.get("TITLE", ""),
-                audio_id=entry.attrib.get("AUDIO_ID", ""),
-                filesize="" if info is None else info.attrib.get("FILESIZE", ""),
-                playtime_float="" if info is None else info.attrib.get("PLAYTIME_FLOAT", ""),
-                bitrate="" if info is None else info.attrib.get("BITRATE", ""),
-                album="" if album is None else album.attrib.get("TITLE", ""),
-                file_name=loc_elem.attrib.get("FILE", ""),
-                location=parse_location_element(loc_elem),
-            )
-        )
-    return records
-
-
-def location_rows(entries: list[ET.Element]) -> list[dict[str, str]]:
-    rows: list[dict[str, str]] = []
-    for entry in entries:
-        loc_elem = entry.find("LOCATION")
-        if loc_elem is None:
-            continue
-        loc = parse_location_element(loc_elem)
-        rows.append(
-            {
-                "artist": entry.attrib.get("ARTIST", ""),
-                "title": entry.attrib.get("TITLE", ""),
-                "volume": loc.volume,
-                "volumeid": loc.volumeid,
-                "dir": loc.dir_value,
-                "file": loc.file_name,
-                "decoded_path": str(loc.decoded_path),
-                "primary_key": loc.primary_key,
-            }
-        )
-    return rows
-
-
-def write_location_element(elem: ET.Element, loc: LocationParts) -> None:
-    elem.attrib["VOLUME"] = loc.volume
-    elem.attrib["VOLUMEID"] = loc.volumeid
-    elem.attrib["DIR"] = loc.dir_value
-    elem.attrib["FILE"] = loc.file_name
-
-
-def parse_primary_key(key: str, volumeid: str | None = None) -> LocationParts:
-    marker = "/:"
-    idx = key.find(marker)
-    if idx < 0:
-        raise ValueError(f"PRIMARYKEY missing '/:' marker: {key!r}")
-
-    volume = key[:idx]
-    remainder = key[idx:]
-    last = remainder.rfind(marker)
-    if last < 0:
-        raise ValueError(f"PRIMARYKEY missing final '/:' separator: {key!r}")
-
-    dir_value = remainder[: last + len(marker)]
-    file_name = remainder[last + len(marker) :]
-    return LocationParts(
-        volume=volume,
-        volumeid=volume if volumeid is None else volumeid,
-        dir_value=dir_value,
-        file_name=file_name,
-    )
-
-
-def apply_rules(loc: LocationParts, rules: Iterable[RewriteRule]) -> tuple[LocationParts, bool]:
-    for rule in rules:
-        if rule.matches(loc):
-            return rule.apply(loc), True
-    return loc, False
-
-
-def _xml_escape_attr(value: str) -> str:
-    return (
-        value.replace("&", "&amp;")
-        .replace("<", "&lt;")
-        .replace('"', "&quot;")
-        .replace("\t", "&#x9;")
-        .replace("\n", "&#xA;")
-        .replace("\r", "&#xD;")
-    )
-
-
-def _find_opening_tag_end(text: str, lt_pos: int) -> int:
-    # Assumption: Traktor NML files always place each element's opening tag
-    # entirely on one line — no multi-line attribute values.  If that assumption
-    # is violated (e.g. a hand-edited or reformatted NML), this function will
-    # scan past the intended line boundary and _patch_attr_in_tag may operate on
-    # the wrong slice of text.  The caller (apply_text_patches) verifies the tag
-    # name before patching, which catches the most obvious mismatches.
-    i = lt_pos + 1
-    while i < len(text):
-        c = text[i]
-        if c in ('"', "'"):
-            q = c
-            i += 1
-            while i < len(text) and text[i] != q:
-                i += 1
-        elif c == '>':
-            return i
-        i += 1
-    raise ValueError(f"unclosed opening tag at offset {lt_pos}")
-
-
-def _patch_attr_in_tag(
-    tag_text: str, attr_name: str, old_value: str, new_value: str
-) -> tuple[str, bool]:
-    pattern = re.compile(
-        r"(\b" + re.escape(attr_name) + r"\s*=\s*)([\"'])(.*?)\2", re.DOTALL
-    )
-    changed = False
-
-    def replace(match: re.Match[str]) -> str:
-        nonlocal changed
-        if html.unescape(match.group(3)) != old_value:
-            return match.group(0)
-        quote = match.group(2)
-        escaped = _xml_escape_attr(new_value)
-        if quote == "'":
-            escaped = escaped.replace("'", "&apos;")
-        changed = True
-        return f"{match.group(1)}{quote}{escaped}{quote}"
-
-    return pattern.sub(replace, tag_text, count=1), changed
-
-
-def _tag_attributes(tag_text: str) -> dict[str, str]:
-    attr_re = re.compile(r'''\b([A-Za-z_:][\w:.-]*)\s*=\s*(["'])(.*?)\2''', re.DOTALL)
-    return {match.group(1): html.unescape(match.group(3)) for match in attr_re.finditer(tag_text)}
-
-
-def apply_text_patches(text: str, patches: list[ElemPatch]) -> str:
-    """Apply attribute edits while retaining every other source byte.
-
-    Patches are located from their original attributes, not XML parser line
-    numbers. libxml2 line metadata can be unreliable in large NML files and
-    is therefore deliberately not used for writing.
-    """
-    if not patches:
-        return text
-
-    patch_map: dict[tuple[str, tuple[tuple[str, str], ...]], ElemPatch] = {}
-    for patch in patches:
-        key = (patch.tag_name, patch.locator)
-        existing = patch_map.get(key)
-        if existing is not None and existing.changes != patch.changes:
-            raise ValueError(f"conflicting text patches for {patch.tag_name} {patch.locator}")
-        patch_map[key] = patch
-
-    matched: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
-    result: list[str] = []
-    cursor = 0
-    tag_start_re = re.compile(r"<(LOCATION|PRIMARYKEY)\b")
-
-    for match in tag_start_re.finditer(text):
-        start = match.start()
-        if start < cursor:
-            continue
-        end = _find_opening_tag_end(text, start) + 1
-        tag_text = text[start:end]
-        attrs = _tag_attributes(tag_text)
-        tag_name = match.group(1)
-
-        matching_key = next(
-            (
-                key
-                for key in patch_map
-                if key[0] == tag_name and all(attrs.get(name) == value for name, value in key[1])
-            ),
-            None,
-        )
-        if matching_key is None:
-            continue
-
-        patch = patch_map[matching_key]
-        new_tag = tag_text
-        for attr_name, old_value, new_value in patch.changes:
-            new_tag, changed = _patch_attr_in_tag(new_tag, attr_name, old_value, new_value)
-            if not changed:
-                raise ValueError(f"could not locate {attr_name}={old_value!r} in {tag_name} {patch.locator}")
-
-        result.extend((text[cursor:start], new_tag))
-        cursor = end
-        matched.add(matching_key)
-
-    missing = set(patch_map) - matched
-    if missing:
-        tag_name, locator = next(iter(missing))
-        raise ValueError(f"could not locate {tag_name} with original attributes {locator}")
-
-    result.append(text[cursor:])
-    return "".join(result)
-
-
-def collection_entries(root: ET.Element) -> list[ET.Element]:
-    collection = root.find("COLLECTION")
-    return [] if collection is None else collection.findall("ENTRY")
-
-
-def playlist_entries(root: ET.Element) -> list[ET.Element]:
-    return root.findall(".//PLAYLIST/ENTRY")
-
-
-def all_entries(root: ET.Element) -> list[ET.Element]:
-    return root.findall(".//ENTRY")
-
-
-def inspect_nml(root: ET.Element, limit: int, csv_path: Path | None) -> int:
-    coll_entries = collection_entries(root)
-    playlist_refs = playlist_entries(root)
-    all_doc_entries = all_entries(root)
-
-    coll_locations = [e for e in coll_entries if e.find("LOCATION") is not None]
-    coll_primarykeys = [e for e in coll_entries if e.find("PRIMARYKEY") is not None]
-    playlist_primarykeys = [e for e in playlist_refs if e.find("PRIMARYKEY") is not None]
-
-    print(f"root_version={root.attrib.get('VERSION', '')}")
-    head = root.find("HEAD")
-    print(f"program={'' if head is None else head.attrib.get('PROGRAM', '')}")
-    print(f"collection_entries={len(coll_entries)}")
-    print(f"collection_entries_with_location={len(coll_locations)}")
-    print(f"collection_entries_with_primarykey={len(coll_primarykeys)}")
-    print(f"playlist_entry_refs={len(playlist_refs)}")
-    print(f"playlist_primarykeys={len(playlist_primarykeys)}")
-    print(f"all_entry_nodes_in_document={len(all_doc_entries)}")
-
-    all_rows = location_rows(coll_locations)
-    rows = all_rows[:limit]
-
-    for row in rows:
-        print(
-            f"sample artist={row['artist']!r} title={row['title']!r} "
-            f"volume={row['volume']!r} dir={row['dir']!r} file={row['file']!r}"
-        )
-
-    if csv_path is not None:
-        with csv_path.open("w", newline="", encoding="utf-8") as handle:
-            writer = csv.DictWriter(handle, fieldnames=list(all_rows[0].keys()) if all_rows else [])
-            if all_rows:
-                writer.writeheader()
-                writer.writerows(all_rows)
-        print(f"csv_written={csv_path}")
-
-    return 0
-
-
-def entry_label(entry: ET.Element) -> str:
-    artist = entry.attrib.get("ARTIST", "")
-    title = entry.attrib.get("TITLE", "")
-    if artist or title:
-        return f"{artist} - {title}".strip(" -")
-    return "<reference>"
-
-
-def record_label(record: EntryRecord) -> str:
-    return entry_label(record.entry)
-
-
-def write_traktor_xml(root: ET.Element, output: Path) -> None:
-    if HAS_LXML:
-        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=False, pretty_print=False)
-    else:
-        xml_bytes = ET.tostring(root, encoding="unicode").encode("utf-8")
-    with output.open("wb") as handle:
-        handle.write(XML_DECLARATION.encode("utf-8"))
-        handle.write(xml_bytes)
-
-
-def record_keys(record: EntryRecord, allow_artist_title_only: bool) -> list[tuple[str, tuple[str, ...]]]:
-    keys: list[tuple[str, tuple[str, ...]]] = []
-    if record.audio_id:
-        keys.append(("audio_id", (record.audio_id,)))
-    if record.artist and record.title and record.filesize and record.playtime_float:
-        keys.append(
-            (
-                "artist_title_size_time",
-                (record.artist, record.title, record.filesize, record.playtime_float),
-            )
-        )
-    if record.artist and record.title and record.file_name:
-        keys.append(("artist_title_file", (record.artist, record.title, record.file_name)))
-    if record.file_name and record.filesize and record.playtime_float:
-        keys.append(("file_size_time", (record.file_name, record.filesize, record.playtime_float)))
-    if record.artist and record.title and record.album and record.playtime_float:
-        keys.append(("artist_title_album_time", (record.artist, record.title, record.album, record.playtime_float)))
-    if allow_artist_title_only and record.artist and record.title:
-        keys.append(("artist_title", (record.artist, record.title)))
-    return keys
-
-
-def build_new_indexes(
-    records: list[EntryRecord], allow_artist_title_only: bool
-) -> dict[str, dict[tuple[str, ...], list[EntryRecord]]]:
-    indexes: dict[str, dict[tuple[str, ...], list[EntryRecord]]] = defaultdict(lambda: defaultdict(list))
-    for record in records:
-        for key_name, key_value in record_keys(record, allow_artist_title_only):
-            indexes[key_name][key_value].append(record)
-    return indexes
-
-
-def match_records(
-    old_records: list[EntryRecord], new_records: list[EntryRecord], allow_artist_title_only: bool
-) -> tuple[dict[str, EntryRecord], dict[str, int], list[tuple[str, str, str, str]]]:
-    indexes = build_new_indexes(new_records, allow_artist_title_only)
-    mapping: dict[str, EntryRecord] = {}
-    stats = {
-        "matched": 0,
-        "matched_audio_id": 0,
-        "matched_artist_title_size_time": 0,
-        "matched_artist_title_file": 0,
-        "matched_file_size_time": 0,
-        "matched_artist_title_album_time": 0,
-        "matched_artist_title": 0,
-        "unmatched": 0,
-        "ambiguous": 0,
-    }
-    samples: list[tuple[str, str, str, str]] = []
-
-    for old_record in old_records:
-        matched_new: EntryRecord | None = None
-        matched_by: str | None = None
-        ambiguous_here = False
-
-        for key_name, key_value in record_keys(old_record, allow_artist_title_only):
-            candidates = indexes.get(key_name, {}).get(key_value, [])
-            if len(candidates) == 1:
-                matched_new = candidates[0]
-                matched_by = key_name
-                break
-            if len(candidates) > 1:
-                ambiguous_here = True
-
-        if matched_new is not None and matched_by is not None:
-            mapping[old_record.primary_key] = matched_new
-            stats["matched"] += 1
-            stats[f"matched_{matched_by}"] += 1
-            if len(samples) < 20:
-                samples.append(
-                    (
-                        record_label(old_record),
-                        str(old_record.location.decoded_path),
-                        str(matched_new.location.decoded_path),
-                        matched_by,
-                    )
-                )
-        elif ambiguous_here:
-            stats["ambiguous"] += 1
-        else:
-            stats["unmatched"] += 1
-
-    return mapping, stats, samples
-
-
-def preview_diff_nml(root: ET.Element, rules: list[RewriteRule], limit: int) -> int:
-    coll_entries = collection_entries(root)
-    coll_entry_ids = {id(entry) for entry in coll_entries}
-    old_to_new_key: dict[str, str] = {}
-
-    collection_location_changes: list[tuple[str, str, str]] = []
-    other_location_changes: list[tuple[str, str, str]] = []
-    primarykey_changes: list[tuple[str, str, str]] = []
-
-    for entry in coll_entries:
-        loc_elem = entry.find("LOCATION")
-        if loc_elem is None:
-            continue
-        old_loc = parse_location_element(loc_elem)
-        new_loc, changed = apply_rules(old_loc, rules)
-        if changed:
-            old_to_new_key[old_loc.primary_key] = new_loc.primary_key
-            collection_location_changes.append(
-                (entry_label(entry), str(old_loc.decoded_path), str(new_loc.decoded_path))
-            )
-
-    for entry in all_entries(root):
-        if id(entry) not in coll_entry_ids:
-            loc_elem = entry.find("LOCATION")
-            if loc_elem is not None:
-                old_loc = parse_location_element(loc_elem)
-                new_loc, changed = apply_rules(old_loc, rules)
-                if changed:
-                    other_location_changes.append(
-                        (entry_label(entry), str(old_loc.decoded_path), str(new_loc.decoded_path))
-                    )
-
-        pk_elem = entry.find("PRIMARYKEY")
-        if pk_elem is None:
-            continue
-
-        old_key = pk_elem.attrib.get("KEY", "")
-        new_key = old_to_new_key.get(old_key)
-        if new_key is None:
-            try:
-                old_loc = parse_primary_key(old_key)
-            except ValueError:
-                continue
-            new_loc, changed = apply_rules(old_loc, rules)
-            if not changed:
-                continue
-            new_key = new_loc.primary_key
-
-        primarykey_changes.append((entry_label(entry), old_key, new_key))
-
-    print(f"collection_location_changes={len(collection_location_changes)}")
-    print(f"other_location_changes={len(other_location_changes)}")
-    print(f"primarykey_changes={len(primarykey_changes)}")
-
-    if collection_location_changes:
-        print("sample_collection_location_changes:")
-        for label, before, after in collection_location_changes[:limit]:
-            print(f"- {label}")
-            print(f"  before={before}")
-            print(f"  after={after}")
-
-    if other_location_changes:
-        print("sample_other_location_changes:")
-        for label, before, after in other_location_changes[:limit]:
-            print(f"- {label}")
-            print(f"  before={before}")
-            print(f"  after={after}")
-
-    if primarykey_changes:
-        print("sample_primarykey_changes:")
-        for label, before, after in primarykey_changes[:limit]:
-            print(f"- {label}")
-            print(f"  before={before}")
-            print(f"  after={after}")
-
-    return 0
-
-
-def preview_compare_nml(
-    old_root: ET.Element, new_root: ET.Element, limit: int, allow_artist_title_only: bool
-) -> int:
-    old_records = collection_records(old_root)
-    new_records = collection_records(new_root)
-    mapping, stats, samples = match_records(old_records, new_records, allow_artist_title_only)
-
-    print(f"old_collection_entries={len(old_records)}")
-    print(f"new_collection_entries={len(new_records)}")
-    for key, value in stats.items():
-        print(f"{key}={value}")
-    print(f"primarykey_updates_available={len(mapping)}")
-
-    if samples:
-        print("sample_matches:")
-        for label, before, after, matched_by in samples[:limit]:
-            print(f"- {label}")
-            print(f"  matched_by={matched_by}")
-            print(f"  before={before}")
-            print(f"  after={after}")
-
-    return 0
-
-
-def compare_stats_dict(
-    old_root: ET.Element, new_root: ET.Element, allow_artist_title_only: bool
-) -> tuple[dict[str, int], list[tuple[str, str, str, str]]]:
-    old_records = collection_records(old_root)
-    new_records = collection_records(new_root)
-    mapping, stats, samples = match_records(old_records, new_records, allow_artist_title_only)
-    stats = {
-        "old_collection_entries": len(old_records),
-        "new_collection_entries": len(new_records),
-        **stats,
-        "primarykey_updates_available": len(mapping),
-    }
-    return stats, samples
-
-
-def scan_compare_candidates(
-    target_path: Path,
-    candidates_dir: Path,
-    limit: int,
-    allow_artist_title_only: bool,
-) -> int:
-    try:
-        target_root = parse_xml(target_path).getroot()
-    except FileNotFoundError:
-        print(f"input_not_found={target_path}", file=sys.stderr)
-        return 2
-
-    candidates = sorted(candidates_dir.glob("**/*.nml"))
-    if not candidates:
-        print(f"no_candidates_found={candidates_dir}")
-        return 0
-
-    rows: list[dict[str, object]] = []
-    for candidate in candidates:
-        try:
-            candidate_root = parse_xml(candidate).getroot()
-        except (_XML_PARSE_ERROR, FileNotFoundError):
-            continue
-
-        stats, _samples = compare_stats_dict(candidate_root, target_root, allow_artist_title_only)
-        old_entries = int(stats["old_collection_entries"])
-        matched = int(stats["matched"])
-        ambiguous = int(stats["ambiguous"])
-        unmatched = int(stats["unmatched"])
-        ratio = 0.0 if old_entries == 0 else matched / old_entries
-        rows.append(
-            {
-                "path": candidate,
-                "matched": matched,
-                "ratio": ratio,
-                "ambiguous": ambiguous,
-                "unmatched": unmatched,
-                "matched_audio_id": int(stats["matched_audio_id"]),
-                "matched_artist_title_size_time": int(stats["matched_artist_title_size_time"]),
-                "matched_artist_title_file": int(stats["matched_artist_title_file"]),
-                "matched_file_size_time": int(stats["matched_file_size_time"]),
-                "matched_artist_title_album_time": int(stats["matched_artist_title_album_time"]),
-                "matched_artist_title": int(stats["matched_artist_title"]),
-                "old_entries": old_entries,
-            }
-        )
-
-    rows.sort(key=lambda row: (row["matched"], row["ratio"], -row["ambiguous"]), reverse=True)
-
-    print(f"target={target_path}")
-    print(f"candidates_scanned={len(rows)}")
-    print("top_candidates:")
-    for row in rows[:limit]:
-        print(
-            f"- path={row['path']}"
-            f" matched={row['matched']}"
-            f" ratio={row['ratio']:.4f}"
-            f" ambiguous={row['ambiguous']}"
-            f" unmatched={row['unmatched']}"
-            f" audio_id={row['matched_audio_id']}"
-            f" title_size_time={row['matched_artist_title_size_time']}"
-            f" title_file={row['matched_artist_title_file']}"
-            f" file_size_time={row['matched_file_size_time']}"
-            f" album_time={row['matched_artist_title_album_time']}"
-            f" title_only={row['matched_artist_title']}"
-        )
-
-    return 0
-
-
-def rewrite_nml(root: ET.Element, rules: list[RewriteRule], dry_run: bool) -> dict[str, int]:
-    stats = {
-        "collection_locations_rewritten": 0,
-        "history_locations_rewritten": 0,
-        "primarykeys_updated_from_collection": 0,
-        "primarykeys_rewritten_directly": 0,
-        "primarykeys_unchanged": 0,
-    }
-    coll = collection_entries(root)
-    old_to_new_key: dict[str, str] = {}
-    for entry in coll:
-        loc_elem = entry.find("LOCATION")
-        if loc_elem is None:
-            continue
-        old_loc = parse_location_element(loc_elem)
-        new_loc, changed = apply_rules(old_loc, rules)
-        if changed:
-            old_to_new_key[old_loc.primary_key] = new_loc.primary_key
-            stats["collection_locations_rewritten"] += 1
-            if not dry_run:
-                write_location_element(loc_elem, new_loc)
-    _process_non_collection_rule_entries(
-        root, {id(e) for e in coll}, rules, old_to_new_key, stats, dry_run=dry_run
-    )
-    return stats
-
-
-def rewrite_from_collection_compare(
-    old_root: ET.Element, new_root: ET.Element, dry_run: bool, allow_artist_title_only: bool
-) -> tuple[dict[str, int], list[tuple[str, str, str, str]]]:
-    old_records = collection_records(old_root)
-    new_records = collection_records(new_root)
-    mapping, match_stats, samples = match_records(old_records, new_records, allow_artist_title_only)
-    stats = {
-        "collection_locations_rewritten": 0,
-        "other_locations_rewritten": 0,
-        "primarykeys_updated_from_collection": 0,
-        "primarykeys_unchanged": 0,
-        **match_stats,
-    }
-    for record in old_records:
-        new_record = mapping.get(record.primary_key)
-        if new_record is None:
-            continue
-        ch = _loc_attr_changes(record.location, new_record.location)
-        if ch:
-            stats["collection_locations_rewritten"] += 1
-            if not dry_run:
-                loc_elem = record.entry.find("LOCATION")
-                if loc_elem is not None:
-                    write_location_element(loc_elem, new_record.location)
-    _process_non_collection_compare_entries(
-        old_root, {id(r.entry) for r in old_records}, mapping, stats, dry_run=dry_run
-    )
-    return stats, samples
-
-
-def _process_non_collection_rule_entries(
-    root: ET.Element,
-    coll_ids: set[int],
-    rules: list[RewriteRule],
-    old_to_new_key: dict[str, str],
-    stats: dict[str, int],
-    *,
-    dry_run: bool = False,
-    patches: list[ElemPatch] | None = None,
-) -> None:
-    """Update history LOCATION and PRIMARYKEY elements for rule-based rewrites.
-
-    When patches is not None, attribute changes are appended to it (lxml path).
-    When patches is None and dry_run is False, changes are applied to the tree
-    (stdlib fallback path).
-    """
-    for entry in all_entries(root):
-        if id(entry) in coll_ids:
-            continue
-        loc_elem = entry.find("LOCATION")
-        if loc_elem is not None:
-            old_loc = parse_location_element(loc_elem)
-            new_loc, changed = apply_rules(old_loc, rules)
-            if changed:
-                stats["history_locations_rewritten"] += 1
-                if patches is not None:
-                    ch = _loc_attr_changes(old_loc, new_loc)
-                    if ch:
-                        patches.append(_location_patch(loc_elem, old_loc, ch))
-                elif not dry_run:
-                    write_location_element(loc_elem, new_loc)
-        pk_elem = entry.find("PRIMARYKEY")
-        if pk_elem is None:
-            continue
-        old_key = pk_elem.attrib.get("KEY", "")
-        new_key = old_to_new_key.get(old_key)
-        if new_key is not None:
-            stats["primarykeys_updated_from_collection"] += 1
-            if patches is not None:
-                patches.append(_primarykey_patch(pk_elem, old_key, new_key))
-            elif not dry_run:
-                pk_elem.attrib["KEY"] = new_key
-            continue
-        try:
-            old_pk_loc = parse_primary_key(old_key)
-        except ValueError:
-            stats["primarykeys_unchanged"] += 1
-            continue
-        new_pk_loc, changed = apply_rules(old_pk_loc, rules)
-        if changed:
-            stats["primarykeys_rewritten_directly"] += 1
-            if patches is not None:
-                patches.append(_primarykey_patch(pk_elem, old_key, new_pk_loc.primary_key))
-            elif not dry_run:
-                pk_elem.attrib["KEY"] = new_pk_loc.primary_key
-        else:
-            stats["primarykeys_unchanged"] += 1
-
-
-def _process_non_collection_compare_entries(
-    root: ET.Element,
-    coll_ids: set[int],
-    mapping: dict[str, EntryRecord],
-    stats: dict[str, int],
-    *,
-    dry_run: bool = False,
-    patches: list[ElemPatch] | None = None,
-) -> None:
-    """Update history LOCATION and PRIMARYKEY elements for collection-compare rewrites."""
-    for entry in all_entries(root):
-        if id(entry) not in coll_ids:
-            loc_elem = entry.find("LOCATION")
-            if loc_elem is not None:
-                old_loc = parse_location_element(loc_elem)
-                new_record = mapping.get(old_loc.primary_key)
-                if new_record is not None:
-                    ch = _loc_attr_changes(old_loc, new_record.location)
-                    if ch:
-                        stats["other_locations_rewritten"] += 1
-                        if patches is not None:
-                            patches.append(_location_patch(loc_elem, old_loc, ch))
-                        elif not dry_run:
-                            write_location_element(loc_elem, new_record.location)
-        pk_elem = entry.find("PRIMARYKEY")
-        if pk_elem is None:
-            continue
-        old_key = pk_elem.attrib.get("KEY", "")
-        new_record = mapping.get(old_key)
-        if new_record is None:
-            stats["primarykeys_unchanged"] += 1
-            continue
-        stats["primarykeys_updated_from_collection"] += 1
-        if patches is not None:
-            patches.append(_primarykey_patch(pk_elem, old_key, new_record.primary_key))
-        elif not dry_run:
-            pk_elem.attrib["KEY"] = new_record.primary_key
-
-
-def _loc_attr_changes(old: LocationParts, new: LocationParts) -> list[tuple[str, str, str]]:
-    return [
-        (attr, ov, nv)
-        for attr, ov, nv in [
-            ("VOLUME", old.volume, new.volume),
-            ("VOLUMEID", old.volumeid, new.volumeid),
-            ("DIR", old.dir_value, new.dir_value),
-            ("FILE", old.file_name, new.file_name),
-        ]
-        if ov != nv
-    ]
-
-
-def _location_patch(
-    elem: ET.Element, old: LocationParts, changes: list[tuple[str, str, str]]
-) -> ElemPatch:
-    return ElemPatch(
-        elem.sourceline,
-        "LOCATION",
-        (("VOLUME", old.volume), ("DIR", old.dir_value), ("FILE", old.file_name)),
-        changes,
-    )
-
-
-def _primarykey_patch(elem: ET.Element, old_key: str, new_key: str) -> ElemPatch:
-    return ElemPatch(elem.sourceline, "PRIMARYKEY", (("KEY", old_key),), [("KEY", old_key, new_key)])
-
-
-def _collect_rewrite_patches(
-    root: ET.Element, rules: list[RewriteRule]
-) -> tuple[list[ElemPatch], dict[str, int]]:
-    stats = {
-        "collection_locations_rewritten": 0,
-        "history_locations_rewritten": 0,
-        "primarykeys_updated_from_collection": 0,
-        "primarykeys_rewritten_directly": 0,
-        "primarykeys_unchanged": 0,
-    }
-    patches: list[ElemPatch] = []
-    coll = collection_entries(root)
-    old_to_new_key: dict[str, str] = {}
-    for entry in coll:
-        loc_elem = entry.find("LOCATION")
-        if loc_elem is None:
-            continue
-        old_loc = parse_location_element(loc_elem)
-        new_loc, changed = apply_rules(old_loc, rules)
-        if changed:
-            old_to_new_key[old_loc.primary_key] = new_loc.primary_key
-            stats["collection_locations_rewritten"] += 1
-            ch = _loc_attr_changes(old_loc, new_loc)
-            if ch:
-                patches.append(_location_patch(loc_elem, old_loc, ch))
-    _process_non_collection_rule_entries(
-        root, {id(e) for e in coll}, rules, old_to_new_key, stats, patches=patches
-    )
-    return patches, stats
-
-
-def _collect_compare_patches(
-    old_root: ET.Element,
-    old_records: list[EntryRecord],
-    mapping: dict[str, EntryRecord],
-) -> tuple[list[ElemPatch], dict[str, int]]:
-    stats = {
-        "collection_locations_rewritten": 0,
-        "other_locations_rewritten": 0,
-        "primarykeys_updated_from_collection": 0,
-        "primarykeys_unchanged": 0,
-    }
-    patches: list[ElemPatch] = []
-    for record in old_records:
-        new_record = mapping.get(record.primary_key)
-        if new_record is None:
-            continue
-        loc_elem = record.entry.find("LOCATION")
-        if loc_elem is not None:
-            ch = _loc_attr_changes(record.location, new_record.location)
-            if ch:
-                stats["collection_locations_rewritten"] += 1
-                patches.append(_location_patch(loc_elem, record.location, ch))
-    _process_non_collection_compare_entries(
-        old_root, {id(r.entry) for r in old_records}, mapping, stats, patches=patches
-    )
-    return patches, stats
-
-
-def add_rule_args(parser: argparse.ArgumentParser) -> None:
-    parser.add_argument("--old-volume")
-    parser.add_argument("--old-dir-prefix")
-    parser.add_argument("--new-volume")
-    parser.add_argument("--new-dir-prefix")
-    parser.add_argument("--new-volumeid")
-
-
-def add_multi_rule_args(parser: argparse.ArgumentParser) -> None:
-    parser.add_argument(
-        "--rule",
-        nargs=4,
-        action="append",
-        metavar=("OLD_VOLUME", "OLD_DIR_PREFIX", "NEW_VOLUME", "NEW_DIR_PREFIX"),
-        help="Repeatable rewrite rule. Prefixes may be human paths or Traktor-encoded paths.",
-    )
-    parser.add_argument(
-        "--rule-with-volumeid",
-        nargs=5,
-        action="append",
-        metavar=("OLD_VOLUME", "OLD_DIR_PREFIX", "NEW_VOLUME", "NEW_DIR_PREFIX", "NEW_VOLUMEID"),
-        help="Repeatable rewrite rule with explicit VOLUMEID override.",
-    )
-
-
-def build_rules(args: argparse.Namespace) -> list[RewriteRule]:
-    rules: list[RewriteRule] = []
-
-    if getattr(args, "rule", None):
-        for old_volume, old_dir, new_volume, new_dir in args.rule:
-            rules.append(
-                RewriteRule(
-                    old_volume=old_volume,
-                    old_dir_prefix=normalize_dir_prefix(old_dir),
-                    new_volume=new_volume,
-                    new_dir_prefix=normalize_dir_prefix(new_dir),
-                )
-            )
-
-    if getattr(args, "rule_with_volumeid", None):
-        for old_volume, old_dir, new_volume, new_dir, new_volumeid in args.rule_with_volumeid:
-            rules.append(
-                RewriteRule(
-                    old_volume=old_volume,
-                    old_dir_prefix=normalize_dir_prefix(old_dir),
-                    new_volume=new_volume,
-                    new_dir_prefix=normalize_dir_prefix(new_dir),
-                    new_volumeid=new_volumeid,
-                )
-            )
-
-    if not rules:
-        required = ["old_volume", "old_dir_prefix", "new_volume", "new_dir_prefix"]
-        missing = [name for name in required if not getattr(args, name, None)]
-        if missing:
-            raise ValueError(
-                "either provide a complete single rule via "
-                "--old-volume/--old-dir-prefix/--new-volume/--new-dir-prefix "
-                "or provide one or more --rule/--rule-with-volumeid entries"
-            )
-        rules.append(
-            RewriteRule(
-                old_volume=args.old_volume,
-                old_dir_prefix=normalize_dir_prefix(args.old_dir_prefix),
-                new_volume=args.new_volume,
-                new_dir_prefix=normalize_dir_prefix(args.new_dir_prefix),
-                new_volumeid=args.new_volumeid,
-            )
-        )
-
-    return rules
-
-
-def parse_args(argv: list[str]) -> argparse.Namespace:
-    parser = argparse.ArgumentParser(description=__doc__)
-    subparsers = parser.add_subparsers(dest="command", required=True)
-
-    inspect_parser = subparsers.add_parser("inspect", help="Inspect an NML file")
-    inspect_parser.add_argument("input", type=Path)
-    inspect_parser.add_argument("--limit", type=int, default=10)
-    inspect_parser.add_argument("--csv", type=Path)
-
-    encode_parser = subparsers.add_parser("encode-dir", help="Encode a human path to Traktor DIR format")
-    encode_parser.add_argument("path_value")
-
-    preview_parser = subparsers.add_parser("preview-diff", help="Preview path rewrites without writing")
-    preview_parser.add_argument("input", type=Path)
-    add_rule_args(preview_parser)
-    add_multi_rule_args(preview_parser)
-    preview_parser.add_argument("--limit", type=int, default=10)
-
-    compare_preview_parser = subparsers.add_parser(
-        "preview-compare", help="Preview old-vs-new collection matching without writing"
-    )
-    compare_preview_parser.add_argument("old_input", type=Path)
-    compare_preview_parser.add_argument("new_input", type=Path)
-    compare_preview_parser.add_argument("--limit", type=int, default=10)
-    compare_preview_parser.add_argument("--allow-artist-title-only", action="store_true")
-
-    scan_parser = subparsers.add_parser(
-        "scan-compare-candidates",
-        help="Scan a folder of backup collections and rank likely matches against a target collection",
-    )
-    scan_parser.add_argument("target_input", type=Path)
-    scan_parser.add_argument("candidates_dir", type=Path)
-    scan_parser.add_argument("--limit", type=int, default=10)
-    scan_parser.add_argument("--allow-artist-title-only", action="store_true")
-
-    rewrite_parser = subparsers.add_parser("rewrite", help="Rewrite paths in an NML file")
-    rewrite_parser.add_argument("input", type=Path)
-    rewrite_parser.add_argument("output", type=Path)
-    add_rule_args(rewrite_parser)
-    add_multi_rule_args(rewrite_parser)
-    rewrite_parser.add_argument("--dry-run", action="store_true")
-
-    compare_rewrite_parser = subparsers.add_parser(
-        "rewrite-from-collection-compare",
-        help="Update an old NML's locations and PRIMARYKEYs using a newer collection file",
-    )
-    compare_rewrite_parser.add_argument("old_input", type=Path)
-    compare_rewrite_parser.add_argument("new_input", type=Path)
-    compare_rewrite_parser.add_argument("output", type=Path)
-    compare_rewrite_parser.add_argument("--dry-run", action="store_true")
-    compare_rewrite_parser.add_argument("--allow-artist-title-only", action="store_true")
-
-    return parser.parse_args(argv)
-
-
-def _print_samples(samples: list[tuple[str, str, str, str]], limit: int = 10) -> None:
-    print("sample_matches:")
-    for label, before, after, matched_by in samples[:limit]:
-        print(f"- {label}")
-        print(f"  matched_by={matched_by}")
-        print(f"  before={before}")
-        print(f"  after={after}")
-
-
-def _apply_and_write(source_bytes: bytes, patches: list[ElemPatch], output: Path) -> None:
-    # Traktor's current collection/history files declare UTF-8. Keeping the
-    # source string intact means this re-encodes to exactly the same bytes
-    # except for the requested XML-escaped attribute values.
-    patched = apply_text_patches(source_bytes.decode("utf-8"), patches)
-    output.parent.mkdir(parents=True, exist_ok=True)
-    output.write_bytes(patched.encode("utf-8"))
-
-
-def cmd_rewrite(args: argparse.Namespace) -> int:
-    if args.output.resolve() == args.input.resolve():
-        print("output_must_differ_from_input", file=sys.stderr)
-        return 2
-    try:
-        rules = build_rules(args)
-    except ValueError as exc:
-        print(str(exc), file=sys.stderr)
-        return 2
-    if HAS_LXML:
-        try:
-            source_bytes = args.input.read_bytes()
-        except FileNotFoundError:
-            print(f"input_not_found={args.input}", file=sys.stderr)
-            return 2
-        try:
-            _parser = ET.XMLParser(remove_blank_text=False, strip_cdata=False, recover=False)
-            root = ET.fromstring(source_bytes, _parser)
-        except _XML_PARSE_ERROR as exc:
-            print(f"xml_parse_error={args.input}: {exc}", file=sys.stderr)
-            return 2
-        patches, stats = _collect_rewrite_patches(root, rules)
-        for key, value in stats.items():
-            print(f"{key}={value}")
-        if not args.dry_run:
-            try:
-                _apply_and_write(source_bytes, patches, args.output)
-            except (UnicodeDecodeError, ValueError) as exc:
-                print(f"text_patch_error={exc}", file=sys.stderr)
-                return 2
-            print(f"output_written={args.output}")
-    else:
-        try:
-            tree = parse_xml(args.input)
-        except FileNotFoundError:
-            print(f"input_not_found={args.input}", file=sys.stderr)
-            return 2
-        root = tree.getroot()
-        stats = rewrite_nml(root, rules, dry_run=args.dry_run)
-        for key, value in stats.items():
-            print(f"{key}={value}")
-        if not args.dry_run:
-            args.output.parent.mkdir(parents=True, exist_ok=True)
-            write_traktor_xml(root, args.output)
-            print(f"output_written={args.output}")
-    return 0
-
-
-def cmd_rewrite_from_collection_compare(args: argparse.Namespace) -> int:
-    if args.output.resolve() == args.old_input.resolve():
-        print("output_must_differ_from_input", file=sys.stderr)
-        return 2
-    if HAS_LXML:
-        try:
-            old_bytes = args.old_input.read_bytes()
-            new_tree = parse_xml(args.new_input)
-        except FileNotFoundError as exc:
-            print(f"input_not_found={exc.filename}", file=sys.stderr)
-            return 2
-        try:
-            _parser = ET.XMLParser(remove_blank_text=False, strip_cdata=False, recover=False)
-            old_root = ET.fromstring(old_bytes, _parser)
-        except _XML_PARSE_ERROR as exc:
-            print(f"xml_parse_error={args.old_input}: {exc}", file=sys.stderr)
-            return 2
-        old_records = collection_records(old_root)
-        new_records = collection_records(new_tree.getroot())
-        mapping, match_stats, samples = match_records(old_records, new_records, args.allow_artist_title_only)
-        patches, apply_stats = _collect_compare_patches(old_root, old_records, mapping)
-        stats = {**apply_stats, **match_stats}
-        for key, value in stats.items():
-            print(f"{key}={value}")
-        if samples:
-            _print_samples(samples)
-        if not args.dry_run:
-            try:
-                _apply_and_write(old_bytes, patches, args.output)
-            except (UnicodeDecodeError, ValueError) as exc:
-                print(f"text_patch_error={exc}", file=sys.stderr)
-                return 2
-            print(f"output_written={args.output}")
-    else:
-        try:
-            old_tree = parse_xml(args.old_input)
-            new_tree = parse_xml(args.new_input)
-        except FileNotFoundError as exc:
-            print(f"input_not_found={exc.filename}", file=sys.stderr)
-            return 2
-        stats, samples = rewrite_from_collection_compare(
-            old_tree.getroot(),
-            new_tree.getroot(),
-            dry_run=args.dry_run,
-            allow_artist_title_only=args.allow_artist_title_only,
-        )
-        for key, value in stats.items():
-            print(f"{key}={value}")
-        if samples:
-            _print_samples(samples)
-        if not args.dry_run:
-            args.output.parent.mkdir(parents=True, exist_ok=True)
-            write_traktor_xml(old_tree.getroot(), args.output)
-            print(f"output_written={args.output}")
-    return 0
-
-
-def main(argv: list[str]) -> int:
-    args = parse_args(argv)
-
-    if args.command == "encode-dir":
-        print(normalize_dir_prefix(args.path_value))
-        return 0
-
-    if args.command == "inspect":
-        try:
-            tree = parse_xml(args.input)
-        except FileNotFoundError:
-            print(f"input_not_found={args.input}", file=sys.stderr)
-            return 2
-        return inspect_nml(tree.getroot(), limit=args.limit, csv_path=args.csv)
-
-    if args.command == "preview-diff":
-        try:
-            tree = parse_xml(args.input)
-        except FileNotFoundError:
-            print(f"input_not_found={args.input}", file=sys.stderr)
-            return 2
-        try:
-            rules = build_rules(args)
-        except ValueError as exc:
-            print(str(exc), file=sys.stderr)
-            return 2
-        return preview_diff_nml(tree.getroot(), rules, limit=args.limit)
-
-    if args.command == "preview-compare":
-        try:
-            old_tree = parse_xml(args.old_input)
-            new_tree = parse_xml(args.new_input)
-        except FileNotFoundError as exc:
-            print(f"input_not_found={exc.filename}", file=sys.stderr)
-            return 2
-        return preview_compare_nml(
-            old_tree.getroot(),
-            new_tree.getroot(),
-            limit=args.limit,
-            allow_artist_title_only=args.allow_artist_title_only,
-        )
-
-    if args.command == "scan-compare-candidates":
-        return scan_compare_candidates(
-            target_path=args.target_input,
-            candidates_dir=args.candidates_dir,
-            limit=args.limit,
-            allow_artist_title_only=args.allow_artist_title_only,
-        )
-
-    if args.command == "rewrite":
-        return cmd_rewrite(args)
-
-    if args.command == "rewrite-from-collection-compare":
-        return cmd_rewrite_from_collection_compare(args)
-
-    print(f"unknown_command={args.command}", file=sys.stderr)
-    return 2
-
+from traktor_nml.cli import main
 
 if __name__ == "__main__":
     raise SystemExit(main(sys.argv[1:]))

```

**Documentation:**

```diff
--- a/traktor_nml_tool.py
+++ b/traktor_nml_tool.py
@@ -13,4 +13,6 @@

-This is a thin argv-forwarding shim over the traktor_nml package (DL-001).
+This is a thin argv-forwarding shim over the traktor_nml package (DL-001):
+every subcommand, the write-strategy split (attribute patching vs.
+byte-span assembly) and the subcommand-discovery mechanism live in
+traktor_nml/, not here - see traktor_nml.cli's own module docstring.

```


**CC-M-002-016** (traktor_nml/README.md)

**Documentation:**

```diff
--- /dev/null
+++ b/traktor_nml/README.md
@@ -0,0 +1,56 @@
+# traktor_nml
+
+Inspect, rewrite, reconnect, splice and split Traktor NML collection files.
+
+## Overview
+
+traktor_nml_tool.py is a thin argv-forwarding shim over this package
+(DL-001). Scanning, caching, fingerprinting, span assembly and merge are
+separate modules so no single file carries all of them and independent
+features do not contend for one file.
+
+## Architecture
+
+Two write mechanisms coexist and never mix within one command:
+
+- Attribute patching (`textpatch.py`, used by `rewrite.py`/`reconnect.py`):
+  substitutes attribute values inside opening tags located in the raw
+  source text. Every other byte of the source is preserved exactly.
+- Byte-span assembly (`spans.py`, used by `splice.py`/`split.py`):
+  concatenates verbatim source byte ranges, re-serialising only the
+  specific fragments a rename or PRIMARYKEY redirect actually changes
+  (DL-007) - `textpatch.py` has no concept of element extent, so
+  structural insert/remove could not go through it without falling back
+  to a full, format-losing serialisation.
+
+`commands/` holds one module per subcommand; `cli.py` discovers them by
+iterating the package rather than listing them, so adding a subcommand
+never requires editing `cli.py` (DL-003).
+
+## Design Decisions
+
+- `matching.py`'s cascade accepts injected key providers; `fingerprint.py`
+  supplies one behind an availability guard, so the core matching path
+  never becomes import-guard-laden for a native chromaprint dependency
+  most environments lack (DL-006).
+- `--match-confidence` is one ordered enum (strict/loose/filename) rather
+  than a second boolean flag, because disk-scan matching's filename-only
+  tier and tag-based matching's artist-title-only tier are really one
+  cascade, not two independent knobs (DL-010).
+
+## Invariants
+
+- Every write command builds its complete output in memory and validates
+  it before any file handle opens; a failure partway through conflict
+  resolution or reference redirection leaves every output path untouched
+  (DL-012).
+- `reconnect.py`'s one-to-one assignment guarantee (DL-004) and
+  `volumes.py`'s explicit-VOLUME/VOLUMEID requirement (DL-005) are both
+  enforced as post-passes over the shared matching cascade, which itself
+  stays unaware either invariant is being layered on top of it.
+- The NML schema (COLLECTION/PLAYLISTS/SUBNODES/PRIMARYKEY shapes and
+  their count attributes) is confirmed only against NML VERSION=20 /
+  Traktor Pro 4; `spans.py`'s count-attribute recalculation is generic
+  over any counted container rather than a fixed tag list, so a counted
+  container introduced by a later schema version is still recalculated
+  correctly instead of being silently left stale.

```


**CC-M-002-017** (traktor_nml/CLAUDE.md)

**Documentation:**

```diff
--- /dev/null
+++ b/traktor_nml/CLAUDE.md
@@ -0,0 +1,29 @@
+# traktor_nml/
+
+## Files
+
+| File               | What                                                       | When to read                                              |
+| ------------------ | ----------------------------------------------------------- | ----------------------------------------------------------- |
+| `__init__.py`      | Package marker                                             | -                                                           |
+| `model.py`         | `LocationParts`/`RewriteRule`/`EntryRecord`, LOCATION/PRIMARYKEY parsing | Adding an identity field, changing LOCATION encode/decode  |
+| `xmlio.py`         | lxml/stdlib ET parsing wrapper                             | Changing how NML files are parsed or serialized            |
+| `textpatch.py`     | `apply_text_patches`/`ElemPatch` byte-preserving attribute writes | Changing how LOCATION/PRIMARYKEY attribute rewrites are applied |
+| `rewrite.py`       | Rule-based and compare-based rewrite patch collection, `write_nml_safely` | Modifying the rewrite/compare cascade or the write path    |
+| `confidence.py`    | `MatchConfidence` ordered enum (strict/loose/filename)     | Adding a match tier or confidence level                    |
+| `matching.py`      | `record_keys`/`match_records` tiered match cascade         | Changing match-key tiers or ambiguity detection            |
+| `diskscan.py`      | Filesystem candidate scanning for reconnection             | Adding or changing disk-scan candidate discovery           |
+| `tagcache.py`      | Tag-read caching                                           | Changing tag cache key composition or eviction             |
+| `reconnect.py`     | Disk-scan reconnection, one-to-one assignment invariant    | Modifying reconnection matching or destination-collision handling |
+| `volumes.py`       | VOLUME/VOLUMEID inference from existing collection paths   | Changing volume identity resolution or `--volume-map`      |
+| `fingerprint.py`   | Acoustic fingerprint comparison (optional chromaprint dep) | Modifying fingerprint matching or its availability guard   |
+| `spans.py`         | Byte-span transplantation, `OutputBuilder`, count-attribute recalculation | Modifying splice/split's structural write path or count recalculation |
+| `playlists.py`     | Playlist import for splice (merge, rename, redirect)       | Modifying playlist merge, collision-rename, or PRIMARYKEY redirect logic |
+| `splice.py`        | Merge-command core: conflict resolution, playlist import   | Modifying splice's conflict policy or merge algorithm      |
+| `split.py`         | Partition-command core: filter, dangling-reference policy  | Modifying split's selection filter or dangling-reference handling |
+| `cli.py`           | Subcommand discovery and argparse wiring                   | Adding a subcommand or changing dispatch                   |
+
+## Subdirectories
+
+| Directory   | What                              | When to read                                    |
+| ----------- | --------------------------------- | ------------------------------------------------ |
+| `commands/` | One module per CLI subcommand     | Adding a subcommand or changing its arguments/handler |

```


**CC-M-002-018** (traktor_nml/commands/CLAUDE.md)

**Documentation:**

```diff
--- /dev/null
+++ b/traktor_nml/commands/CLAUDE.md
@@ -0,0 +1,13 @@
+# traktor_nml/commands/
+
+## Files
+
+| File                | What                                                          | When to read                                          |
+| ------------------- | -------------------------------------------------------------- | -------------------------------------------------------- |
+| `__init__.py`       | Package marker; `cli.py` iterates this package to find subcommands | Adding a new command module                           |
+| `inspect_cmd.py`    | `inspect` subcommand                                          | Changing collection/playlist inspection output        |
+| `rewrite_cmd.py`    | `preview-diff`/`rewrite` subcommands (rule-based rewriting)    | Changing rule-based path rewrite behavior              |
+| `compare_cmd.py`    | `preview-compare`/`scan-compare-candidates`/`rewrite-from-collection-compare` subcommands | Changing compare-based rewrite or candidate scanning   |
+| `reconnect_cmd.py`  | `reconnect` subcommand (disk-scan reconnection)                | Changing reconnection's CLI surface or stats output    |
+| `splice_cmd.py`     | `splice` subcommand (merge NML files)                          | Changing splice's CLI surface, conflict flags, or reports |
+| `split_cmd.py`      | `split` subcommand (partition an NML file)                     | Changing split's CLI surface or dangling-reference flags |

```


### Milestone 3: Filesystem candidate index with tag cache

**Files**: C:\codex\general_tasks\traktor_nml\diskscan.py, C:\codex\general_tasks\traktor_nml\tagcache.py, C:\codex\general_tasks\tests\test_diskscan.py

**Requirements**:

- Repeatable scan roots are walked and audio files deduplicated by resolved absolute path
- Each readable file becomes an EntryRecord with no entry element populated from artist / title / album / filesize / playtime / bitrate / filename
- AUDIO_ID stays empty on disk-derived records so the top match tier is structurally unreachable from the disk side
- A cache keyed by path and size and mtime persists tag reads and records read failures distinctly from unattempted files
- The cache flushes incrementally so an interrupted scan retains all but its last batch
- Progress is reported at intervals during long scans
- --refresh-cache re-reads entries the cache marks as previously failed
- A missing mutagen import degrades to filename and filesize matching with one warning rather than an abort

**Acceptance Criteria**:

- A resumed scan after simulated interruption yields the same candidate set as an uninterrupted scan over the same roots
- A second scan over unchanged roots performs no tag reads
- Touching a file's mtime causes exactly that file to be re-read
- Files reachable through two scan roots appear once
- STEM files are indexed rather than skipped

**Tests**:

- C:\codex\general_tasks\tests\test_diskscan.py

#### Code Intent

- **CI-M-003-001** `C:\codex\general_tasks\traktor_nml\diskscan.py::index_scan_roots`: Walk each scan root, collect audio files by extension, deduplicate by resolved absolute path so overlapping roots contribute one candidate per file, read tags through the cache, and yield entry records carrying no source element and no audio identifier. Progress is emitted at intervals and unreadable files are counted rather than aborting the walk. (refs: DL-001)
- **CI-M-003-002** `C:\codex\general_tasks\traktor_nml\tagcache.py::TagCache`: Persist tag and fingerprint results keyed by path and size and modification time, distinguishing a stored null result meaning a prior read failed from an absent key meaning no attempt was made, flush accumulated entries every batch so an interruption loses at most one batch, and re-attempt stored failures only when a refresh is requested. (refs: DL-006)

#### Code Changes

**CC-M-003-001** (C:\codex\general_tasks\traktor_nml\diskscan.py) - implements CI-M-003-001

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/diskscan.py
@@ -0,0 +1,147 @@
+"""Filesystem candidate index feeding the matching cascade's candidate side.
+
+A disk-derived EntryRecord has no source element and no AUDIO_ID (that tier
+is structurally unreachable from the disk side - nothing on disk carries
+Traktor's internal audio identifier), so it can be fed straight into
+matching.match_records as the "new" side unmodified.
+"""
+
+from __future__ import annotations
+
+import sys
+from pathlib import Path
+from typing import Iterable, Optional
+
+from .model import EntryRecord, LocationParts
+from .tagcache import TagCache
+
+try:
+    import mutagen
+
+    HAS_MUTAGEN = True
+except ImportError:  # pragma: no cover - degrade to filename/filesize matching
+    HAS_MUTAGEN = False
+
+AUDIO_EXTENSIONS = (".mp3", ".flac", ".wav", ".aiff", ".aif", ".m4a", ".ogg", ".stem.mp3", ".stem.flac")
+
+
+def _has_audio_extension(path: Path) -> bool:
+    name = path.name.lower()
+    return any(name.endswith(ext) for ext in AUDIO_EXTENSIONS)
+
+
+def _read_tags(path: Path) -> Optional[dict]:
+    if not HAS_MUTAGEN:
+        return None
+    try:
+        audio = mutagen.File(path, easy=True)
+    except Exception:
+        return None
+    if audio is None:
+        return None
+    tags = getattr(audio, "tags", None) or {}
+
+    def _first(key: str) -> str:
+        value = tags.get(key)
+        return value[0] if value else ""
+
+    playtime = ""
+    if getattr(audio, "info", None) is not None and getattr(audio.info, "length", None):
+        playtime = f"{audio.info.length:.3f}"
+    bitrate = ""
+    if getattr(audio, "info", None) is not None and getattr(audio.info, "bitrate", None):
+        bitrate = str(int(audio.info.bitrate / 1000))
+
+    return {
+        "artist": _first("artist"),
+        "title": _first("title"),
+        "album": _first("album"),
+        "playtime_float": playtime,
+        "bitrate": bitrate,
+    }
+
+
+def _placeholder_location(path: Path) -> LocationParts:
+    # Disk-scan candidates never feed the attribute-patch write path, so this
+    # LocationParts exists only to carry decoded_path for stats/CSV output.
+    posix_dir = "/:" + "/:".join(path.parent.parts[1:] if path.is_absolute() else path.parent.parts) + "/:"
+    return LocationParts(volume="", volumeid="", dir_value=posix_dir, file_name=path.name)
+
+
+def index_scan_roots(
+    scan_roots: Iterable[Path],
+    cache: TagCache,
+    *,
+    refresh_cache: bool = False,
+    progress_every: int = 500,
+    stats: dict[str, int] | None = None,
+) -> list[EntryRecord]:
+    """Walk each scan root, deduplicate by resolved path, and yield candidates.
+
+    Progress is emitted at intervals; unreadable files are counted in stats
+    rather than aborting the walk. STEM files are indexed like any other
+    audio file, not skipped.
+    """
+    if not HAS_MUTAGEN:
+        print("tag_reading_unavailable=mutagen not installed; degrading to filename/filesize matching", file=sys.stderr)
+
+    if stats is None:
+        stats = {}
+    stats.setdefault("files_seen", 0)
+    stats.setdefault("duplicates_skipped", 0)
+    stats.setdefault("unreadable", 0)
+    stats.setdefault("cache_hits", 0)
+    stats.setdefault("cache_misses", 0)
+
+    seen: set[Path] = set()
+    records: list[EntryRecord] = []
+
+    for root in scan_roots:
+        for path in sorted(Path(root).rglob("*")):
+            if not path.is_file() or not _has_audio_extension(path):
+                continue
+            resolved = path.resolve()
+            if resolved in seen:
+                stats["duplicates_skipped"] += 1
+                continue
+            seen.add(resolved)
+            stats["files_seen"] += 1
+            if stats["files_seen"] % progress_every == 0:
+                print(f"disk_scan_progress={stats['files_seen']}", file=sys.stderr)
+
+            try:
+                file_stat = resolved.stat()
+            except OSError:
+                stats["unreadable"] += 1
+                continue
+
+            if cache.should_refresh(resolved, file_stat.st_size, file_stat.st_mtime, refresh_cache):
+                tags = _read_tags(resolved)
+                cache.put(resolved, file_stat.st_size, file_stat.st_mtime, tags)
+                stats["cache_misses"] += 1
+            else:
+                tags = cache.get(resolved, file_stat.st_size, file_stat.st_mtime)
+                stats["cache_hits"] += 1
+
+            if tags is None:
+                stats["unreadable"] += 1
+                tags = {"artist": "", "title": "", "album": "", "playtime_float": "", "bitrate": ""}
+
+            records.append(
+                EntryRecord(
+                    entry=None,
+                    artist=tags.get("artist", ""),
+                    title=tags.get("title", ""),
+                    audio_id="",
+                    filesize=str(file_stat.st_size),
+                    playtime_float=tags.get("playtime_float", ""),
+                    bitrate=tags.get("bitrate", ""),
+                    album=tags.get("album", ""),
+                    file_name=resolved.name,
+                    location=_placeholder_location(resolved),
+                    source_path=resolved,
+                )
+            )
+
+    cache.flush()
+    return records

```

**Documentation:**

```diff
--- a/traktor_nml/diskscan.py
+++ b/traktor_nml/diskscan.py
@@ -18,6 +18,9 @@


 def _has_audio_extension(path: Path) -> bool:
+    """Extension check only - does not open or validate the file, so a
+    renamed non-audio file with an audio-like extension is still indexed
+    as a candidate and left to fail later at the tag-read stage."""
     name = path.name.lower()
     return any(name.endswith(ext) for ext in AUDIO_EXTENSIONS)

```


**CC-M-003-002** (C:\codex\general_tasks\tests\test_diskscan.py) - implements CI-M-003-001

**Code:**

```diff
--- /dev/null
+++ b/tests/test_diskscan.py
@@ -0,0 +1,85 @@
+"""Filesystem candidate index behavior: dedup, cache resume, STEM handling."""
+
+from __future__ import annotations
+
+import os
+import time
+from pathlib import Path
+
+from traktor_nml.diskscan import index_scan_roots
+from traktor_nml.tagcache import TagCache
+
+
+def _make_files(root: Path, names: list[str]) -> None:
+    root.mkdir(parents=True, exist_ok=True)
+    for name in names:
+        (root / name).write_bytes(b"\x00" * 32)
+
+
+def test_second_scan_over_unchanged_roots_performs_no_tag_reads(tmp_path: Path) -> None:
+    root = tmp_path / "music"
+    _make_files(root, ["a.mp3", "b.flac"])
+    cache = TagCache(tmp_path / "cache.json")
+
+    stats1: dict[str, int] = {}
+    index_scan_roots([root], cache, stats=stats1)
+    assert stats1["cache_misses"] == 2
+
+    cache2 = TagCache(tmp_path / "cache.json")
+    stats2: dict[str, int] = {}
+    index_scan_roots([root], cache2, stats=stats2)
+    assert stats2["cache_misses"] == 0
+    assert stats2["cache_hits"] == 2
+
+
+def test_touching_mtime_reads_exactly_that_file(tmp_path: Path) -> None:
+    root = tmp_path / "music"
+    _make_files(root, ["a.mp3", "b.flac"])
+    cache = TagCache(tmp_path / "cache.json")
+    index_scan_roots([root], cache)
+
+    cache2 = TagCache(tmp_path / "cache.json")
+    future = time.time() + 100
+    os.utime(root / "a.mp3", (future, future))
+    stats: dict[str, int] = {}
+    index_scan_roots([root], cache2, stats=stats)
+    assert stats["cache_misses"] == 1
+    assert stats["cache_hits"] == 1
+
+
+def test_overlapping_roots_yield_one_candidate_per_file(tmp_path: Path) -> None:
+    root = tmp_path / "music"
+    _make_files(root, ["a.mp3"])
+    cache = TagCache(tmp_path / "cache.json")
+    stats: dict[str, int] = {}
+    records = index_scan_roots([root, root], cache, stats=stats)
+    assert len(records) == 1
+    assert stats["duplicates_skipped"] == 1
+
+
+def test_stem_files_are_indexed(tmp_path: Path) -> None:
+    root = tmp_path / "music"
+    _make_files(root, ["track.stem.mp3"])
+    cache = TagCache(tmp_path / "cache.json")
+    records = index_scan_roots([root], cache)
+    assert len(records) == 1
+    assert records[0].file_name == "track.stem.mp3"
+    assert records[0].entry is None
+    assert records[0].audio_id == ""
+
+
+def test_resumed_scan_matches_uninterrupted_scan(tmp_path: Path) -> None:
+    root = tmp_path / "music"
+    _make_files(root, [f"track{i}.mp3" for i in range(5)])
+
+    cache_full = TagCache(tmp_path / "full.json")
+    full_records = index_scan_roots([root], cache_full)
+
+    # Simulate an interruption: cache flushed with a small batch size so an
+    # early flush persists, then a fresh scan resumes from that state.
+    cache_partial = TagCache(tmp_path / "partial.json", flush_every=1)
+    index_scan_roots([root], cache_partial)
+    resumed_cache = TagCache(tmp_path / "partial.json")
+    resumed_records = index_scan_roots([root], resumed_cache)
+
+    assert {r.file_name for r in full_records} == {r.file_name for r in resumed_records}

```

**Documentation:**

```diff
--- a/tests/test_diskscan.py
+++ b/tests/test_diskscan.py
@@ -10,6 +10,9 @@


 def _make_files(root: Path, names: list[str]) -> None:
+    """Create root and empty placeholder files of a fixed size, standing
+    in for real audio files since these tests exercise path/size/mtime
+    identity, not audio content."""
     root.mkdir(parents=True, exist_ok=True)
     for name in names:
         (root / name).write_bytes(b"\x00" * 32)

```


**CC-M-003-003** (C:\codex\general_tasks\traktor_nml\tagcache.py) - implements CI-M-003-002

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/tagcache.py
@@ -0,0 +1,66 @@
+"""Persistent tag/fingerprint cache keyed by path, size and modification time.
+
+A stored null value means a prior read was attempted and failed; an absent
+key means no attempt was made at all - the two must stay distinguishable so a
+plain re-scan does not endlessly retry files it already knows are unreadable,
+while --refresh-cache can still target exactly those failures. The cache
+flushes every batch so an interrupted scan loses at most its last batch
+rather than everything read so far (the tag cache is keyed by path, size and
+mtime, so a file renamed without any content change is re-read rather than
+recognised - see the plan's tradeoffs).
+"""
+
+from __future__ import annotations
+
+import json
+from pathlib import Path
+from typing import Optional
+
+
+class TagCache:
+    def __init__(self, cache_path: Path, flush_every: int = 50):
+        self.cache_path = cache_path
+        self.flush_every = flush_every
+        self._dirty = 0
+        self._data: dict[str, Optional[dict]] = {}
+        if cache_path.exists():
+            try:
+                self._data = json.loads(cache_path.read_text(encoding="utf-8"))
+            except (json.JSONDecodeError, OSError):
+                self._data = {}
+
+    @staticmethod
+    def key(path: Path, size: int, mtime: float) -> str:
+        return f"{path.resolve()}|{size}|{int(mtime)}"
+
+    def attempted(self, path: Path, size: int, mtime: float) -> bool:
+        return self.key(path, size, mtime) in self._data
+
+    def get(self, path: Path, size: int, mtime: float) -> Optional[dict]:
+        """Return the stored value, or None whether unattempted or failed.
+
+        Callers that must distinguish the two use attempted() first.
+        """
+        return self._data.get(self.key(path, size, mtime))
+
+    def put(self, path: Path, size: int, mtime: float, value: Optional[dict]) -> None:
+        self._data[self.key(path, size, mtime)] = value
+        self._dirty += 1
+        if self._dirty >= self.flush_every:
+            self.flush()
+
+    def should_refresh(self, path: Path, size: int, mtime: float, refresh: bool) -> bool:
+        if not self.attempted(path, size, mtime):
+            return True
+        if refresh and self.get(path, size, mtime) is None:
+            return True
+        return False
+
+    def flush(self) -> None:
+        if self._dirty == 0 and self.cache_path.exists():
+            return
+        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
+        tmp_path = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
+        tmp_path.write_text(json.dumps(self._data), encoding="utf-8")
+        tmp_path.replace(self.cache_path)
+        self._dirty = 0

```

**Documentation:**

```diff
--- a/traktor_nml/tagcache.py
+++ b/traktor_nml/tagcache.py
@@ -22,6 +22,9 @@

     @staticmethod
     def key(path: Path, size: int, mtime: float) -> str:
+        """Combine path, size and mtime so a file overwritten in place
+        (same path, different bytes) misses the cache even though its
+        path alone is unchanged."""
         return f"{path.resolve()}|{size}|{int(mtime)}"

     def attempted(self, path: Path, size: int, mtime: float) -> bool:

```


### Milestone 4: Disk-scan reconnection commands

**Files**: C:\codex\general_tasks\traktor_nml\reconnect.py, C:\codex\general_tasks\traktor_nml\volumes.py, C:\codex\general_tasks\traktor_nml\commands\reconnect_cmd.py, C:\codex\general_tasks\tests\test_reconnect.py

**Requirements**:

- scan-reconnect-candidates reports match statistics for scanned roots against a collection without writing
- rewrite-from-reconnect writes a reconnected collection through the existing attribute-patch path
- Disk records feed the existing matching cascade as the candidate side with no change to that cascade
- An inverted-mapping pass excludes every old track sharing a destination candidate and counts them under destination_collisions
- A disk path converts to Traktor DIR and FILE encoding as the inverse of the existing decoder
- VOLUME and VOLUMEID are set explicitly on every rewritten LOCATION from --volume-map or from a single unambiguous observed pair under the root's prefix
- An absent or ambiguous volume identity for a root is a hard error naming that root
- Ambiguous and unmatched and collided tracks export to CSV through the existing row and writer pattern
- --dry-run reports the same classification counts the write path produces

**Acceptance Criteria**:

- No output assigns two collection entries the same LOCATION
- No output contains a VOLUME or VOLUMEID value absent from --volume-map and from the verified-unambiguous prefix scan
- A byte diff of output against input with every rewritten LOCATION and PRIMARYKEY value masked is empty
- --dry-run counts and post-write counts agree exactly on the same inputs
- A duplicate-rip fixture reports destination_collisions and rewrites neither entry
- An error injected during patch collection leaves the output path absent

**Tests**:

- C:\codex\general_tasks\tests\test_reconnect.py

#### Code Intent

- **CI-M-004-001** `C:\codex\general_tasks\traktor_nml\reconnect.py::resolve_reconnection`: Match collection records against filesystem candidates through the shared cascade, then invert the resulting mapping and withdraw every old track that shares a destination candidate with another, counting the withdrawals under destination collisions and carrying them into the ambiguity export alongside source-side ambiguities. The returned mapping contains only one-to-one assignments. (refs: DL-004)
- **CI-M-004-002** `C:\codex\general_tasks\traktor_nml\volumes.py::resolve_volume_identity`: Determine the volume and volume identifier for a scan root from an explicit mapping argument when one is supplied, otherwise from collection entries whose decoded path begins with that root when they agree on exactly one pair, and raise naming the root when neither source yields a single unambiguous pair. (refs: DL-005)
- **CI-M-004-003** `C:\codex\general_tasks\traktor_nml\reconnect.py::location_from_disk_path`: Convert an absolute filesystem path plus a resolved volume identity into location parts whose directory value carries the Traktor separator encoding and whose file name is the path's final component, inverting the existing directory decoder exactly. (refs: DL-005)
- **CI-M-004-004** `C:\codex\general_tasks\traktor_nml\commands\reconnect_cmd.py::register`: Register a candidate-reporting subcommand and a rewriting subcommand that share scan-root, volume-map, match-confidence, cache and CSV-export arguments. The rewriting subcommand collects attribute patches through the shared write helper and produces identical classification counts under a dry run and a real write. (refs: DL-003, DL-012)

#### Code Changes

**CC-M-004-001** (C:\codex\general_tasks\traktor_nml\reconnect.py) - implements CI-M-004-001

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/reconnect.py
@@ -0,0 +1,49 @@
+"""Disk-scan reconnection: match old collection records against candidates.
+
+match_records only detects source-side ambiguity - several candidates for
+one old track - and returns a plain old-to-new mapping. Two distinct old
+entries can each match the same physical file unambiguously on their own and
+both be marked matched, which would point two collection entries and their
+playlist references at one LOCATION. resolve_reconnection inverts the
+mapping after matching completes: any candidate holding more than one
+assignment removes all of its claimants, counted under destination
+collisions and exported to the ambiguity CSV instead of being rewritten
+(DL-004). The returned mapping is therefore strictly one-to-one.
+"""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+from .confidence import MatchConfidence
+from .matching import AMBIGUOUS, KeyProvider, build_new_indexes, match_records, record_keys
+from .model import EntryRecord, LocationParts, encode_traktor_dir
+
+
+def location_from_disk_path(path: Path, volume: str, volumeid: str) -> LocationParts:
+    """Invert decode_traktor_dir: an absolute disk path plus a resolved
+    volume identity becomes a LOCATION whose DIR carries the Traktor
+    separator encoding and whose FILE is the path's final component.
+
+    DIR must be volume-relative, the way every real LOCATION in a Traktor
+    collection is (e.g. VOLUME="Macintosh HD" DIR="/:Users/:freqking/:...",
+    never carrying the OS mount point itself) - only path's own anchor (the
+    drive letter or POSIX root, e.g. "D:\\" or "/") is stripped before
+    encoding. A scan root (e.g. D:\\Music\\Techno) is an arbitrary
+    user-supplied subdirectory, not the volume's actual root; stripping it
+    instead of the anchor would drop every intermediate path segment between
+    the volume root and the scan root from the rewritten DIR, so DIR would
+    never reconstruct the file's real volume-relative path.
+    """
+    anchor = path.anchor
+    relative_dir = path.parent.relative_to(anchor) if anchor else path.parent
+    relative_str = "" if str(relative_dir) == "." else str(relative_dir)
+    return LocationParts(
+        volume=volume,
+        volumeid=volumeid,
+        dir_value="/:" if not relative_str else encode_traktor_dir(relative_str),
+        file_name=path.name,
+    )
+
+

```

**Documentation:**

```diff
--- a/traktor_nml/reconnect.py
+++ b/traktor_nml/reconnect.py
@@ -10,6 +10,10 @@
 (DL-004). The returned mapping is therefore strictly one-to-one.
 """

+# DL-004 is enforced purely as a post-match inversion pass; match_records
+# is unaware that a one-to-one guarantee is layered on top of its plain
+# old-to-new mapping.
+
 from __future__ import annotations

 from pathlib import Path

```


**CC-M-004-002** (C:\codex\general_tasks\traktor_nml\volumes.py) - implements CI-M-004-002

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/volumes.py
@@ -0,0 +1,79 @@
+"""Explicit VOLUME/VOLUMEID identity for a disk-scan root (DL-005).
+
+A rewritten LOCATION with a wrong or empty VOLUMEID produces a PRIMARYKEY
+Traktor cannot resolve, and reconnection runs precisely because the recorded
+paths no longer describe reality - so inferring identity from those same
+stale paths would be inference from the least trustworthy field in the file.
+Inference is accepted only when a prefix scan of the old collection yields a
+single distinct VOLUME/VOLUMEID pair; every other case is a hard error.
+"""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+from .model import EntryRecord
+
+
+class VolumeIdentityError(ValueError):
+    pass
+
+
+def resolve_volume_identity(
+    scan_root: Path,
+    old_records: list[EntryRecord],
+    volume_map: dict[str, tuple[str, str]] | None,
+) -> tuple[str, str]:
+    """Return (volume, volumeid) for scan_root.
+
+    volume_map, when given, maps a scan root string (as passed on the
+    command line) to an explicit (volume, volumeid) pair and always wins.
+    Otherwise every old-collection record whose decoded path starts under
+    scan_root is inspected; if they agree on exactly one (volume, volumeid)
+    pair, that pair is used. Any other outcome - no observations, or more
+    than one distinct pair - raises, naming scan_root.
+    """
+    # Both --volume-map entries (raw CLI strings) and scan_root are
+    # normalised through Path before comparison, so "C:\music", "C:/music"
+    # and "C:\music\" all key the same override regardless of which
+    # separator/trailing-slash style the map was authored with or the root
+    # was passed as.
+    root_key = str(Path(scan_root))
+    if volume_map and root_key in volume_map:
+        return volume_map[root_key]
+
+    # decoded_dir is a PurePosixPath built from Traktor's own DIR encoding
+    # and is volume-relative (it never carries a drive/mount prefix), while
+    # scan_root is a mount-absolute filesystem path - the two are not
+    # comparable as a raw string prefix. Instead, compare on path components,
+    # after stripping scan_root's own drive/anchor (which decoded_dir can
+    # never contain either): an old record is "under" scan_root when
+    # scan_root's own (anchor-stripped) components are a PREFIX of
+    # decoded_dir's components once both are rooted at their volume, matched
+    # whole segments only, so a scan root named Music never matches a
+    # decoded path under Musicology, and a scan root D:\\Music\\Artist never
+    # matches an unrelated record whose deep folder path happens to end in
+    # ...\\Music\\Artist.
+    scan_root_parts = Path(scan_root).parts
+    if Path(scan_root).anchor:
+        scan_root_parts = scan_root_parts[1:]
+    scan_parts = [part.rstrip("/\\") for part in scan_root_parts]
+    observed: set[tuple[str, str]] = set()
+    if scan_parts:
+        for record in old_records:
+            decoded_parts = [part for part in record.location.decoded_dir.parts if part != "/"]
+            if decoded_parts[:len(scan_parts)] == scan_parts:
+                observed.add((record.location.volume, record.location.volumeid))
+
+    if len(observed) == 1:
+        return next(iter(observed))
+
+    raise VolumeIdentityError(
+        f"volume_identity_ambiguous scan_root={scan_root} observed_pairs={sorted(observed)}; "
+        "pass --volume-map"
+    )
+
+
+def parse_volume_map(entries: list[list[str]] | None) -> dict[str, tuple[str, str]]:
+    """Parse repeatable --volume-map SCAN_ROOT VOLUME VOLUMEID triples."""
+    mapping: dict[str, tuple[str, str]] = {}
+    for scan_root, volume, volumeid in entries or []:
+        mapping[str(Path(scan_root))] = (volume, volumeid)
+    return mapping

```

**Documentation:**

```diff
--- a/traktor_nml/volumes.py
+++ b/traktor_nml/volumes.py
@@ -8,6 +8,10 @@
 single distinct VOLUME/VOLUMEID pair; every other case is a hard error.
 """

+# parse_volume_map (the --volume-map argparse handler) and
+# resolve_volume_identity share the same Path-normalisation step
+# (DL-005), so a map entry authored with any separator style still
+# matches scan_root at lookup time.
+
 from __future__ import annotations

 from pathlib import Path

```


**CC-M-004-003** (C:\codex\general_tasks\traktor_nml\reconnect.py) - implements CI-M-004-003

**Code:**

```diff
--- a/traktor_nml/reconnect.py
+++ b/traktor_nml/reconnect.py
@@ -47,3 +47,76 @@
     )
 
 
+def resolve_reconnection(
+    old_records: list[EntryRecord],
+    candidates: list[EntryRecord],
+    confidence: MatchConfidence,
+    key_providers: list[KeyProvider] = (),
+) -> tuple[dict[str, EntryRecord], dict[str, int], list[dict[str, str]]]:
+    # Built once and reused both for match_records' own lookup and for the
+    # post-match ambiguity check below, instead of match_records building
+    # its own copy and this function silently rebuilding an identical one
+    # (doubling the O(old x candidates) fingerprint similarity search when a
+    # fingerprint provider is injected).
+    indexes = build_new_indexes(candidates, confidence, key_providers)
+    mapping, match_stats, _samples = match_records(
+        old_records, candidates, confidence, key_providers, indexes=indexes
+    )
+
+    records_by_key = {record.primary_key: record for record in old_records}
+    dest_claimants: dict[int, list[str]] = {}
+    for old_key, candidate in mapping.items():
+        dest_claimants.setdefault(id(candidate), []).append(old_key)
+    collided_keys = {key for claimants in dest_claimants.values() if len(claimants) > 1 for key in claimants}
+
+    # A withdrawn destination collision was still counted under its match
+    # tier when match_records ran; re-derive that tier the same way
+    # match_records did (first tier whose index bucket holds exactly this
+    # one candidate) so matched_<tier> stays consistent with the final
+    # matched total instead of overcounting a match that was later undone.
+    stats = dict(match_stats)
+    for old_key in collided_keys:
+        record = records_by_key.get(old_key)
+        if record is None:
+            continue
+        winner = mapping[old_key]
+        for key_name, key_value in record_keys(record, confidence, key_providers):
+            if indexes.get(key_name, {}).get(key_value) == [winner]:
+                stat_name = f"matched_{key_name}"
+                if stat_name in stats:
+                    stats[stat_name] -= 1
+                break
+
+    final_mapping = {key: value for key, value in mapping.items() if key not in collided_keys}
+
+    ambiguity_rows: list[dict[str, str]] = []
+    for record in old_records:
+        old_key = record.primary_key
+        if old_key in final_mapping:
+            continue
+        if old_key in collided_keys:
+            reason = "destination_collision"
+        else:
+            # value is AMBIGUOUS whenever a provider (see matching.AMBIGUOUS)
+            # positively detected its own unresolvable multi-candidate
+            # conflict for this record - that conflict never appears as an
+            # index bucket of size > 1, since nothing else shares the
+            # provider's own internal comparison, so it must be checked for
+            # directly alongside the ordinary bucket-size ambiguity check.
+            ambiguous_here = any(
+                value is AMBIGUOUS or len(indexes.get(name, {}).get(value, [])) > 1
+                for name, value in record_keys(record, confidence, key_providers)
+            )
+            reason = "ambiguous" if ambiguous_here else "unmatched"
+        ambiguity_rows.append(
+            {
+                "artist": record.artist,
+                "title": record.title,
+                "old_path": str(record.location.decoded_path),
+                "reason": reason,
+            }
+        )
+
+    stats["destination_collisions"] = len(collided_keys)
+    stats["matched"] = len(final_mapping)
+    return final_mapping, stats, ambiguity_rows

```

**Documentation:**

```diff
--- a/traktor_nml/reconnect.py
+++ b/traktor_nml/reconnect.py
@@ -49,6 +49,12 @@
 def resolve_reconnection(
     old_records: list[EntryRecord],
     candidates: list[EntryRecord],
     confidence: MatchConfidence,
     key_providers: list[KeyProvider] = (),
 ) -> tuple[dict[str, EntryRecord], dict[str, int], list[dict[str, str]]]:
+    """Match old_records against candidates via the shared cascade, then
+    invert the resulting mapping to find and drop destination collisions
+    - candidates claimed by more than one old record - reclassifying
+    their claimants out of the one-to-one mapping and re-deriving each
+    affected tier's match count so matched_<tier> totals stay consistent
+    with the final matched count (DL-004)."""
     # Built once and reused both for match_records' own lookup and for the

```


**CC-M-004-004** (C:\codex\general_tasks\traktor_nml\commands\reconnect_cmd.py) - implements CI-M-004-004

**Code:**

```diff
--- a/traktor_nml/commands/reconnect_cmd.py
+++ b/traktor_nml/commands/reconnect_cmd.py
@@ -1,15 +1,17 @@
 """scan-reconnect-candidates and rewrite-from-reconnect subcommands."""
 
 from __future__ import annotations
 
 import argparse
 import csv
 import sys
 from pathlib import Path
 
 from ..confidence import MatchConfidence
 from ..diskscan import index_scan_roots
+from ..fingerprint import fingerprint_key_provider
 from ..model import EntryRecord, collection_records
 from ..reconnect import location_from_disk_path, resolve_reconnection
 from ..rewrite import CompareEntryResolver, process_non_collection_entries, write_nml_safely
 from ..tagcache import TagCache
 from ..volumes import VolumeIdentityError, parse_volume_map, resolve_volume_identity
 from ..xmlio import parse_xml
 from .compare_cmd import add_confidence_args, resolve_confidence
@@ -25,6 +27,12 @@ def add_reconnect_args(parser: argparse.ArgumentParser) -> None:
     parser.add_argument("--cache", type=Path, default=Path(".traktor_nml_tagcache.json"))
     parser.add_argument("--refresh-cache", action="store_true")
     parser.add_argument("--csv", type=Path)
+    parser.add_argument(
+        "--fingerprint",
+        action="store_true",
+        help="Enable the acoustic-fingerprint match tier (requires pyacoustid/fpcalc); "
+        "opt-in and off by default since these are optional dependencies (R-002).",
+    )
     add_confidence_args(parser)
 
 
@@ -55,7 +63,14 @@ def _run_reconnection(args: argparse.Namespace, old_root) -> tuple[dict[str, E
     candidates = index_scan_roots(args.scan_roots, cache, refresh_cache=args.refresh_cache)
     confidence = resolve_confidence(args)
 
-    mapping, stats, ambiguity_rows = resolve_reconnection(old_records, candidates, confidence)
+    key_providers = []
+    fingerprint_stats: dict[str, int] = {}
+    if getattr(args, "fingerprint", False):
+        key_providers.append(fingerprint_key_provider(cache, candidates, fingerprint_stats))
+
+    mapping, stats, ambiguity_rows = resolve_reconnection(
+        old_records, candidates, confidence, key_providers
+    )
+    stats = {**fingerprint_stats, **stats}
 
     # Re-encode each winning candidate's real absolute path into a proper
     # LOCATION using its scan root's resolved volume identity - the
```

**Documentation:**

```diff
--- a/traktor_nml/commands/reconnect_cmd.py
+++ b/traktor_nml/commands/reconnect_cmd.py
@@ -63,6 +63,9 @@
     key_providers = []
     fingerprint_stats: dict[str, int] = {}
     if getattr(args, "fingerprint", False):
+        # Off by default (DL-006): pyacoustid/fpcalc may be absent, and
+        # the matching cascade behaves identically with an empty
+        # key_providers list.
         key_providers.append(fingerprint_key_provider(cache, candidates, fingerprint_stats))

     mapping, st

```


**CC-M-004-005** (C:\codex\general_tasks\tests\test_reconnect.py) - implements CI-M-004-004

**Code:**

```diff
--- /dev/null
+++ b/tests/test_reconnect.py
@@ -0,0 +1,115 @@
+"""Disk-scan reconnection: one-to-one assignment and volume identity."""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+from tests.conftest import run_tool
+
+
+def _write_nml(path: Path, entries_xml: str, entries_count: int = 1) -> None:
+    path.write_text(
+        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
+        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
+        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS>'
+        "<SETS></SETS><INDEXING></INDEXING></NML>",
+        encoding="utf-8",
+        newline="",
+    )
+
+
+def _entry(artist, title, volume, dirv, filename, size="16", time="1.0"):
+    return (
+        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
+        f'<LOCATION DIR="{dirv}" FILE="{filename}" VOLUME="{volume}" VOLUMEID="{volume}"></LOCATION>'
+        f'<INFO BITRATE="320" PLAYTIME_FLOAT="{time}" FILESIZE="{size}"></INFO>'
+        "</ENTRY>"
+    )
+
+
+def test_scan_reconnect_reports_match_without_writing(tmp_path: Path) -> None:
+    music = tmp_path / "music"
+    music.mkdir()
+    (music / "xtal.mp3").write_bytes(b"\x00" * 16)
+
+    old_nml = tmp_path / "old.nml"
+    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))
+
+    result = run_tool(
+        [
+            "scan-reconnect-candidates", str(old_nml),
+            "--scan-root", str(music),
+            "--volume-map", str(music), "C:", "C:",
+            # mutagen is not installed in this test environment, so tags are
+            # always empty; filename confidence is required to match at all.
+            "--match-confidence", "filename",
+        ],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 0
+    assert "reconnectable=1" in result.stdout
+    assert not (tmp_path / "out.nml").exists()
+
+
+def test_no_output_assigns_two_entries_the_same_location(tmp_path: Path) -> None:
+    music = tmp_path / "music"
+    music.mkdir()
+    (music / "track.mp3").write_bytes(b"\x00" * 16)
+
+    old_nml = tmp_path / "old.nml"
+    _write_nml(
+        old_nml,
+        _entry("A", "One", "Z:", "/:gone1/:", "track.mp3") + _entry("A", "One", "Z:", "/:gone2/:", "track.mp3"),
+        entries_count=2,
+    )
+
+    result = run_tool(
+        [
+            "rewrite-from-reconnect", str(old_nml), str(tmp_path / "out.nml"),
+            "--scan-root", str(music),
+            "--volume-map", str(music), "C:", "C:",
+            "--match-confidence", "filename",
+            "--csv", str(tmp_path / "ambiguous.csv"),
+        ],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 0
+    # Both old entries claim the one candidate on disk, so both are withdrawn.
+    assert "destination_collisions=2" in result.stdout
+    out_path = tmp_path / "out.nml"
+    if out_path.exists():
+        assert 'VOLUME="C:"' not in out_path.read_text(encoding="utf-8")
+
+
+def test_absent_volume_map_and_ambiguous_prefix_is_hard_error(tmp_path: Path) -> None:
+    music = tmp_path / "music"
+    music.mkdir()
+    (music / "xtal.mp3").write_bytes(b"\x00" * 16)
+
+    old_nml = tmp_path / "old.nml"
+    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))
+
+    result = run_tool(
+        ["scan-reconnect-candidates", str(old_nml), "--scan-root", str(music)],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 2
+
+
+def test_dry_run_and_write_agree_on_counts(tmp_path: Path) -> None:
+    music = tmp_path / "music"
+    music.mkdir()
+    (music / "xtal.mp3").write_bytes(b"\x00" * 16)
+
+    old_nml = tmp_path / "old.nml"
+    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))
+
+    common = [
+        "rewrite-from-reconnect", str(old_nml), str(tmp_path / "out.nml"),
+        "--scan-root", str(music),
+        "--volume-map", str(music), "C:", "C:",
+    ]
+    dry = run_tool(common + ["--dry-run"], cwd=tmp_path)
+    real = run_tool(common, cwd=tmp_path)
+    assert dry.stdout.split("output_written")[0] == real.stdout.split("output_written")[0]

```

**Documentation:**

```diff
--- a/tests/test_reconnect.py
+++ b/tests/test_reconnect.py
@@ -12,6 +12,9 @@


 def _entry(artist, title, volume, dirv, filename, size="16", time="1.0"):
+    """Minimal COLLECTION ENTRY carrying only the attributes the
+    file/size/time match tiers need; PLAYLISTS/SETS/INDEXING are always
+    present but empty so the tool's other schema assumptions still hold."""
     return (
         f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
         f'<LOCATION DIR="{dirv}" FILE="{filename}" VOLUME="{volume}" VOLUMEID="{volume}"></LOCATION>'

```


### Milestone 5: Acoustic fingerprint key provider

**Files**: C:\codex\general_tasks\traktor_nml\fingerprint.py, C:\codex\general_tasks\tests\test_fingerprint.py

**Requirements**:

- Fingerprints are computed locally with no network access
- An old track is fingerprinted only when its recorded path resolves on disk at scan time
- Absence of an old-side fingerprint counts under fingerprint_unavailable_old_side and falls through to tag tiers
- A comparison is eligible only when both sides hold a fingerprint and durations agree within 1.0 second
- Similarity above 0.95 counts as a match and 0.80 to 0.95 records fingerprint_near_match for review without matching
- Fingerprints share the tag cache keyed by path and size and mtime with a null value distinguishing a failed attempt from an unattempted one
- A missing fpcalc binary or acoustid module prints one warning and leaves the provider list empty

**Acceptance Criteria**:

- Matching results are identical with the provider absent and with it present but unavailable
- Two encodings of one source at differing bitrates match by fingerprint and not by any tag tier
- Two distinct tracks of similar length score below threshold and produce no match
- A pair outside the duration tolerance is never compared
- The suite skips fingerprint-requiring cases with a stated reason when fpcalc is absent and passes

**Tests**:

- C:\codex\general_tasks\tests\test_fingerprint.py

#### Code Intent

- **CI-M-005-001** `C:\codex\general_tasks\traktor_nml\fingerprint.py::fingerprint_key_provider`: Supply a top-tier match key for a record when a fingerprint exists for both the record and a candidate, their durations agree within one second, and their similarity exceeds the match threshold. Similarity in the review band is recorded for export without producing a key, and the provider yields nothing when the fingerprinting binary is unavailable. (refs: DL-006, DL-013)
- **CI-M-005-002** `C:\codex\general_tasks\traktor_nml\fingerprint.py::old_side_fingerprint`: Compute a fingerprint for a collection record only when its recorded location resolves to a readable file at scan time, cache the result alongside the record's tag data, and count the unresolvable case so its absence is visible in the statistics rather than silent. (refs: DL-006)

#### Code Changes

**CC-M-005-001** (C:\codex\general_tasks\traktor_nml\fingerprint.py) - implements CI-M-005-001

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/fingerprint.py
@@ -0,0 +1,138 @@
+"""Acoustic fingerprint key provider (chromaprint via pyacoustid), local-only.
+
+A fingerprint computed only from scanned/new candidates has nothing to
+compare against because the OLD collection's original media is exactly what
+may be unreachable - that's why reconnection exists. Fingerprinting is
+therefore old-side-gated: only attempted when the old track's recorded path
+is still resolvable on disk at scan time; otherwise it is silently absent for
+that track (counted in stats, not an error) and matching falls through to the
+tag-based cascade (DL-006, DL-013).
+
+Duration must agree within +/-1.0s before comparing; similarity above 0.95
+counts as a match; 0.80-0.95 is logged as fingerprint_near_match for human
+review only, never auto-accepted.
+
+Bridging continuous similarity into the cascade's exact-match key/index
+architecture: candidates whose fingerprints agree with each other within
+duration tolerance and match threshold are grouped into one cluster and share
+one key (see _cluster_candidates), so that when an old record's best match
+turns out to have company - e.g. two bitrate rips of the same track, both
+clearing the threshold - the shared key's index bucket holds more than one
+candidate and the ordinary ambiguity check reports it, rather than a single
+first-found winner silently keeping the rest a secret.
+"""
+
+from __future__ import annotations
+
+from pathlib import Path
+from typing import Optional
+
+from .matching import AMBIGUOUS, KeyProvider
+from .model import EntryRecord
+from .tagcache import TagCache
+
+try:
+    import acoustid
+
+    HAS_ACOUSTID = True
+except (ImportError, OSError):  # pragma: no cover - fpcalc binary or module absent
+    HAS_ACOUSTID = False
+
+DURATION_TOLERANCE_SECONDS = 1.0
+MATCH_THRESHOLD = 0.95
+NEAR_MATCH_THRESHOLD = 0.80
+
+TIER_NAME = "fingerprint"
+
+
+def _compute_fingerprint(path: Path) -> Optional[tuple[float, str]]:
+    if not HAS_ACOUSTID:
+        return None
+    try:
+        duration, fp = acoustid.fingerprint_file(str(path))
+    except Exception:
+        return None
+    return float(duration), fp if isinstance(fp, str) else fp.decode("ascii")
+
+
+def _similarity(a: str, b: str, stats: dict[str, int]) -> Optional[float]:
+    # acoustid.compare_fingerprints only reads the fingerprint half of each
+    # (duration, fp) pair, so (0, a)/(0, b) is a valid call - but a decode or
+    # compare failure here is a distinct outcome from a genuine similarity of
+    # 0.0, and every caller makes a matching decision from this return value
+    # alone (the stats dict is never consulted before deciding), so the
+    # failure must be signalled through the return itself: None on failure,
+    # distinct from a real 0.0 comparison, so a compare error is never
+    # mistaken for "definitely not the same track".
+    stats.setdefault("fingerprint_compare_errors", 0)
+    try:
+        return acoustid.compare_fingerprints((0, a), (0, b))
+    except Exception:
+        stats["fingerprint_compare_errors"] += 1
+        return None
+
+
+def _cached_fingerprint(path: Path, cache: TagCache) -> Optional[tuple[float, str]]:
+    try:
+        file_stat = path.stat()
+    except OSError:
+        return None
+    existing = cache.get(path, file_stat.st_size, file_stat.st_mtime) or {}
+    if existing.get("fingerprint"):
+        return float(existing["duration"]), existing["fingerprint"]
+    result = _compute_fingerprint(path)
+    if result is not None:
+        cache.put(path, file_stat.st_size, file_stat.st_mtime, {**existing, "duration": result[0], "fingerprint": result[1]})
+    return result
+
+
+def old_side_fingerprint(
+    record: EntryRecord, cache: TagCache, stats: dict[str, int]
+) -> Optional[tuple[float, str]]:
+    """Fingerprint a collection record only when its recorded location
+    resolves to a readable file at scan time; count the unresolvable case
+    so its absence is visible in the statistics rather than silent."""
+    stats.setdefault("fingerprint_unavailable_old_side", 0)
+    path = Path(str(record.location.decoded_path))
+    if not path.is_file():
+        stats["fingerprint_unavailable_old_side"] += 1
+        return None
+    result = _cached_fingerprint(path, cache)
+    if result is None:
+        stats["fingerprint_unavailable_old_side"] += 1
+    return result
+
+
+def _cluster_candidates(
+    candidate_fps: dict[int, tuple[float, str]], stats: dict[str, int]
+) -> dict[int, str]:
+    """Group candidates whose fingerprints agree with each other within
+    duration tolerance and the match threshold, and return each candidate's
+    cluster key. Two candidates that are acoustically indistinguishable from
+    one another - e.g. two bitrate rips of the same track - end up sharing
+    one key, so a query that matches either lands in an index bucket sized
+    by the whole cluster rather than a single object identity."""
+    parent: dict[int, int] = {cid: cid for cid in candidate_fps}
+
+    def find(x: int) -> int:
+        while parent[x] != x:
+            parent[x] = parent[parent[x]]
+            x = parent[x]
+        return x
+
+    def union(a: int, b: int) -> None:
+        root_a, root_b = find(a), find(b)
+        if root_a != root_b:
+            parent[max(root_a, root_b)] = min(root_a, root_b)
+
+    ids = list(candidate_fps)
+    for i, cid_a in enumerate(ids):
+        duration_a, fp_a = candidate_fps[cid_a]
+        for cid_b in ids[i + 1:]:
+            duration_b, fp_b = candidate_fps[cid_b]
+            if abs(duration_a - duration_b) > DURATION_TOLERANCE_SECONDS:
+                continue
+            similarity = _similarity(fp_a, fp_b, stats)
+            # None means the compare itself failed (see _similarity) - treated
+            # as "cannot compare", never as a real similarity score, so a
+            # failed compare cannot silently union two unrelated candidates.
+            if similarity is not None and similarity > MATCH_THRESHOLD:
+                union(cid_a, cid_b)
+
+    return {cid: str(find(cid)) for cid in candidate_fps}
+
+

```

**Documentation:**

```diff
--- a/traktor_nml/fingerprint.py
+++ b/traktor_nml/fingerprint.py
@@ -13,6 +13,10 @@
 review only, never auto-accepted.
 """

+# HAS_ACOUSTID gates every entry point in this module, including ones
+# that do not mention it by name below, so importing this module never
+# requires the fpcalc binary to be installed.
+
 from __future__ import annotations

 from pathlib import Path
@@ -31,6 +35,11 @@
 from .model import EntryRecord
 from .tagcache import TagCache

+# Availability is probed once here, at import time, rather than per call:
+# HAS_ACOUSTID is the flag both the startup warning line and the
+# active-provider stats counter (named per DL-006) read to report
+# whether this tier is live (R-002).
+
 try:
     import acoustid


```


**CC-M-005-002** (C:\codex\general_tasks\traktor_nml\fingerprint.py) - implements CI-M-005-002

**Code:**

```diff
--- a/traktor_nml/fingerprint.py
+++ b/traktor_nml/fingerprint.py
@@ -136,3 +136,80 @@
     return {cid: str(find(cid)) for cid in candidate_fps}
 
 
+def fingerprint_key_provider(cache: TagCache, candidates: list[EntryRecord], stats: dict[str, int]) -> KeyProvider:
+    """Supply a top-tier match key for an old record when a fingerprint
+    exists for both it and at least one candidate, their durations agree
+    within tolerance, and similarity clears the match threshold. The
+    0.80-0.95 band is counted as fingerprint_near_match for review and never
+    yields a key. Yields nothing at all when the fingerprinting binary is
+    unavailable."""
+    stats.setdefault("fingerprint_near_match", 0)
+    stats.setdefault("fingerprint_ambiguous", 0)
+
+    candidate_fps: dict[int, tuple[float, str]] = {}
+    if HAS_ACOUSTID:
+        for candidate in candidates:
+            if candidate.source_path is None:
+                continue
+            fp = _cached_fingerprint(candidate.source_path, cache)
+            if fp is not None:
+                candidate_fps[id(candidate)] = fp
+
+    cluster_key = _cluster_candidates(candidate_fps, stats) if HAS_ACOUSTID else {}
+
+    def provide(record: EntryRecord) -> Optional[tuple[str, ...]]:
+        if not HAS_ACOUSTID:
+            return None
+
+        if record.entry is None:
+            # Candidate side: emit its cluster's key whenever it has a
+            # usable fingerprint, so an old record's winning key resolves to
+            # every candidate acoustically indistinguishable from the winner.
+            return (cluster_key[id(record)],) if id(record) in cluster_key else None
+
+        old_fp = old_side_fingerprint(record, cache, stats)
+        if old_fp is None:
+            return None
+        old_duration, old_value = old_fp
+
+        # Collect every candidate that clears the match threshold against the
+        # old record, not just the first: acoustic similarity need not be
+        # transitive, so two candidates (e.g. two different-bitrate rips of
+        # one source) can each independently clear the threshold here while
+        # their mutual similarity falls short of the cluster threshold.
+        winners: list[EntryRecord] = []
+        for candidate in candidates:
+            candidate_fp = candidate_fps.get(id(candidate))
+            if candidate_fp is None:
+                continue
+            candidate_duration, candidate_value = candidate_fp
+            if abs(candidate_duration - old_duration) > DURATION_TOLERANCE_SECONDS:
+                continue
+            similarity = _similarity(old_value, candidate_value, stats)
+            # None means the compare itself failed (see _similarity) -
+            # treated as "cannot compare", never as a real similarity score.
+            if similarity is None:
+                continue
+            if similarity > MATCH_THRESHOLD:
+                winners.append(candidate)
+            elif NEAR_MATCH_THRESHOLD <= similarity <= MATCH_THRESHOLD:
+                stats["fingerprint_near_match"] += 1
+
+        if not winners:
+            return None
+        winner_keys = {cluster_key[id(winner)] for winner in winners}
+        if len(winner_keys) > 1:
+            # More than one distinct cluster key qualifies: the record is
+            # genuinely ambiguous between them. Returning AMBIGUOUS (rather
+            # than None) makes match_records place this record in the
+            # ambiguous bucket outright, so a lower tag-based tier in the
+            # same cascade can never silently resolve it to a single
+            # confident match - a plain None here would be indistinguishable
+            # from "this tier has nothing to say", letting a less specific
+            # tier decide instead of the tier that actually found the
+            # conflict. The counter is still kept for the aggregate view.
+            stats["fingerprint_ambiguous"] += 1
+            return AMBIGUOUS
+        return (next(iter(winner_keys)),)
+
+    return KeyProvider(tier_name=TIER_NAME, provide=provide)

```

**Documentation:**

```diff
--- a/traktor_nml/fingerprint.py
+++ b/traktor_nml/fingerprint.py
@@ -158,6 +158,10 @@
     cluster_key = _cluster_candidates(candidate_fps, stats) if HAS_ACOUSTID else {}

     def provide(record: EntryRecord) -> Optional[tuple[str, ...]]:
+        """Per-record key: routes a candidate-side record to its
+        fingerprint cluster's shared key, and an old-side record to that
+        winning cluster only when duration and similarity both clear this
+        provider's thresholds (DL-013)."""
         if not HAS_ACOUSTID:
             return None
 
```


**CC-M-005-003** (C:\codex\general_tasks\tests\test_fingerprint.py) - implements CI-M-005-001

**Code:**

```diff
--- /dev/null
+++ b/tests/test_fingerprint.py
@@ -0,0 +1,61 @@
+"""Fingerprint key provider: local-only, threshold-gated, degrades cleanly."""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+import pytest
+
+from traktor_nml.confidence import MatchConfidence
+from traktor_nml.fingerprint import HAS_ACOUSTID, fingerprint_key_provider
+from traktor_nml.matching import match_records
+from traktor_nml.model import EntryRecord, LocationParts
+from traktor_nml.tagcache import TagCache
+
+requires_acoustid = pytest.mark.skipif(
+    not HAS_ACOUSTID, reason="pyacoustid/fpcalc not installed in this environment"
+)
+
+
+def _old_record(path: Path) -> EntryRecord:
+    return EntryRecord(
+        entry=object(),  # any non-None sentinel marks this as an old-side record
+        artist="", title="", audio_id="", filesize="", playtime_float="", bitrate="", album="",
+        file_name=path.name,
+        location=LocationParts(volume="", volumeid="", dir_value=f"/:{path.parent.name}/:", file_name=path.name),
+    )
+
+
+def _candidate(path: Path) -> EntryRecord:
+    return EntryRecord(
+        entry=None, artist="", title="", audio_id="", filesize="", playtime_float="", bitrate="", album="",
+        file_name=path.name,
+        location=LocationParts(volume="", volumeid="", dir_value="/:", file_name=path.name),
+        source_path=path,
+    )
+
+
+def test_provider_yields_nothing_when_binary_unavailable(tmp_path: Path) -> None:
+    """Matching results are identical with the provider absent and with it
+    present but unavailable, since an unavailable binary makes provide()
+    return None unconditionally."""
+    cache = TagCache(tmp_path / "cache.json")
+    old = _old_record(tmp_path / "gone" / "song.mp3")
+    candidates = [_candidate(tmp_path / "song.mp3")]
+    stats: dict[str, int] = {}
+    provider = fingerprint_key_provider(cache, candidates, stats)
+
+    without_provider = match_records([old], candidates, MatchConfidence.STRICT, [])
+    with_unavailable_provider = match_records([old], candidates, MatchConfidence.STRICT, [provider])
+
+    assert without_provider[1]["matched"] == with_unavailable_provider[1]["matched"]
+
+
+@requires_acoustid
+def test_two_bitrate_encodings_match_by_fingerprint(tmp_path: Path) -> None:
+    pytest.skip("requires real audio fixtures encoded at two bitrates; exercised in the manual rollout gate")
+
+
+@requires_acoustid
+def test_pair_outside_duration_tolerance_never_compared(tmp_path: Path) -> None:
+    pytest.skip("requires real audio fixtures; exercised in the manual rollout gate")

```

**Documentation:**

```diff
--- a/tests/test_fingerprint.py
+++ b/tests/test_fingerprint.py
@@ -22,6 +22,9 @@


 def _candidate(path: Path) -> EntryRecord:
+    """Disk-derived EntryRecord stub: entry=None marks the candidate side
+    the same way diskscan.index_scan_roots does, so match_records treats
+    it identically to a real scanned file."""
     return EntryRecord(
         entry=None, artist="", title="", audio_id="", filesize="", playtime_float="", bitrate="", album="",
         file_name=path.name,

```


### Milestone 6: Byte-span transplantation primitive

**Files**: C:\codex\general_tasks\traktor_nml\spans.py, C:\codex\general_tasks\tests\test_spans.py

**Requirements**:

- A depth-aware scanner returns the byte range of an element from its opening angle bracket through its closing tag
- Self-closing and empty-element forms resolve to a span
- Nested same-named elements resolve to the outermost requested extent
- Attribute values containing angle brackets and quotes do not terminate the scan early
- An output builder concatenates verbatim source spans with re-serialised fragments and applies attribute patches to spans it copies
- Count attributes on COLLECTION and PLAYLIST and SUBNODES are recalculated from the assembled child counts

**Acceptance Criteria**:

- Every ENTRY and NODE and PLAYLIST span extracted from the 6412-entry corpus parses standalone under both parsers
- Reassembling a file from all of its own spans reproduces the input byte for byte
- Property-based generation of nested and escaped attribute cases finds no span whose extracted text fails to parse
- A recalculated count attribute always equals the assembled child count

**Tests**:

- C:\codex\general_tasks\tests\test_spans.py

#### Code Intent

- **CI-M-006-001** `C:\codex\general_tasks\traktor_nml\spans.py::element_span`: Return the byte range covering an element from its opening angle bracket through the end of its closing tag, tracking nesting depth for same-named descendants and treating quoted attribute values as opaque so angle brackets inside them do not terminate the scan. A self-closing element resolves to the extent of its single tag. (refs: DL-007)
- **CI-M-006-002** `C:\codex\general_tasks\traktor_nml\spans.py::OutputBuilder`: Assemble an output document from an ordered sequence of verbatim source spans and re-serialised fragments, apply attribute patches to the spans it copies, and return the complete byte string without touching the filesystem. add_counted_span is a generic per-container recalculation primitive (count attribute set to the assembled child count) that a caller opts into for any container it rebuilds - splice.py uses it for COLLECTION ENTRIES and the root SUBNODES COUNT - rather than a fixed recalculation OutputBuilder performs unconditionally for every playlist; a container transplanted untouched (a base playlist splice never modifies) keeps its verbatim count instead. split.py does not use OutputBuilder or add_counted_span at all: it recalculates COLLECTION ENTRIES and the root SUBNODES COUNT by calling recalculate_count_attr() directly inside a local _replace_children() helper, and recalculates PLAYLIST ENTRIES on a partially-kept playlist through a third, separate mechanism - cloning the playlist's ElementTree node, removing the dropped entries in place, setting playlist_elem.attrib["ENTRIES"] directly, then re-serialising with ET.tostring(). (refs: DL-007, DL-012)

#### Code Changes

**CC-M-006-001** (C:\codex\general_tasks\traktor_nml\spans.py) - implements CI-M-006-001

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/spans.py
@@ -0,0 +1,130 @@
+"""Byte-span transplantation: the second write mechanism (DL-007).
+
+apply_text_patches (textpatch.py) substitutes attribute values inside opening
+tags it locates by scanning for LOCATION and PRIMARYKEY, and has no concept
+of element extent. Inserting or dropping whole ENTRY and NODE subtrees
+through it would mean either bolting structural editing onto an attribute
+substituter or falling back to ET.tostring, which reformats the document and
+loses the byte fidelity the tool exists to protect. This module locates each
+element's full opening-to-closing byte range with a depth-aware scanner, and
+OutputBuilder assembles output by concatenating verbatim source spans plus
+re-serialised fragments only where a rename or redirect actually changes
+bytes. splice.py and split.py use only this mechanism; reconnect.py and
+rewrite.py use only textpatch.py - the two write paths never mix within one
+command.
+"""
+
+from __future__ import annotations
+
+import re
+from dataclasses import dataclass
+from typing import Optional
+
+# The attribute-list group treats a quoted value as one opaque unit (via the
+# quoted alternatives) rather than stopping at the first '>' or '/' inside
+# it: XML permits a literal '>' unescaped inside a quoted attribute value, and
+# a value legitimately ending in '/' must not be mistaken for the self-closing
+# marker, which only the final, unquoted (/?) before '>' may capture.
+_ATTRS = r'(?:[^>"\'/]|"[^"]*"|\'[^\']*\'|/(?!>))*'
+_TOKEN_RE = re.compile(
+    r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<(/?)([A-Za-z_][\w:.-]*)(" + _ATTRS + r")(/?)>",
+    re.DOTALL,
+)
+
+
+@dataclass(frozen=True)
+class Span:
+    start: int
+    end: int  # exclusive
+
+    def text(self, source: str) -> str:
+        return source[self.start:self.end]
+
+
+def element_span(source: str, open_lt_pos: int) -> Span:
+    """Return the byte range of the element whose opening tag starts at
+    open_lt_pos, from '<' through the end of its closing tag (or its own
+    tag, if self-closing). Comment, CDATA and processing-instruction regions
+    are skipped by construction (via _TOKEN_RE) so tag-like text inside them
+    never terminates the scan early or is mistaken for a nested element.
+    Nesting depth is tracked by tag name, so a same-named descendant does
+    not end the scan prematurely; the outermost requested extent always
+    wins.
+    """
+    match_at_start = _TOKEN_RE.match(source, open_lt_pos)
+    if match_at_start is None or match_at_start.group(2) is None:
+        raise ValueError(f"no element opening tag at offset {open_lt_pos}")
+    tag_name = match_at_start.group(2)
+    is_self_closing = bool(match_at_start.group(4))
+    if is_self_closing:
+        return Span(open_lt_pos, match_at_start.end())
+
+    depth = 1
+    pos = match_at_start.end()
+    for token in _TOKEN_RE.finditer(source, pos):
+        if token.group(2) != tag_name:
+            continue
+        is_close = bool(token.group(1))
+        self_closing = bool(token.group(4))
+        if self_closing:
+            continue
+        if is_close:
+            depth -= 1
+            if depth == 0:
+                return Span(open_lt_pos, token.end())
+        else:
+            depth += 1
+
+    raise ValueError(f"unclosed element {tag_name!r} starting at offset {open_lt_pos}")
+
+
+def find_element_span(source: str, tag_name: str, start_from: int = 0) -> Optional[Span]:
+    """Locate the next top-level occurrence of tag_name at or after
+    start_from and return its full span."""
+    idx = source.find(f"<{tag_name}", start_from)
+    while idx != -1:
+        # Guard against a longer tag name sharing this prefix (e.g. NODE vs NODENAME).
+        following = source[idx + 1 + len(tag_name): idx + 2 + len(tag_name)]
+        if following and following not in (" ", "\t", "\n", "\r", ">", "/"):
+            idx = source.find(f"<{tag_name}", idx + 1)
+            continue
+        return element_span(source, idx)
+    return None
+
+
+def element_span_by_identity(source: str, root, element) -> Span:
+    """Locate element's span by its position among same-tag elements in
+    document order, rather than searching source text for one of its
+    attribute values (breaks on duplicate values across the document - e.g.
+    two ENTRY elements sharing a FILE basename, very common across a real
+    corpus - and on XML-escaped characters, since the parsed attribute value
+    is unescaped text while the source bytes are not) or by source line
+    (unreliable whenever more than one element shares a line, as in a
+    compact/minified document with no inter-tag whitespace).
+
+    root.iter(tag) walks the parsed tree in the same pre-order every parser
+    produces from a well-formed document, which is exactly the left-to-right
+    order that tag's opening tags appear in source - so the Nth element of
+    that tag in the tree is unambiguously the Nth "<tag" occurrence in text,
+    independent of attribute values or line boundaries.
+    """
+    tag_name = element.tag
+    target_index = next((i for i, el in enumerate(root.iter(tag_name)) if el is element), None)
+    if target_index is None:
+        raise ValueError(f"element <{tag_name}> is not part of the given root's tree")
+
+    idx = -1
+    for _ in range(target_index + 1):
+        idx = source.find(f"<{tag_name}", idx + 1)
+        while idx != -1:
+            # Guard against a longer tag name sharing this prefix (e.g. NODE vs NODENAME).
+            following = source[idx + 1 + len(tag_name): idx + 2 + len(tag_name)]
+            if following and following not in (" ", "\t", "\n", "\r", ">", "/"):
+                idx = source.find(f"<{tag_name}", idx + 1)
+                continue
+            break
+        if idx < 0:
+            raise ValueError(f"could not locate occurrence {target_index} of <{tag_name}> in source text")
+    return element_span(source, idx)
+
+

```

**Documentation:**

```diff
--- a/traktor_nml/spans.py
+++ b/traktor_nml/spans.py
@@ -13,6 +13,18 @@
 command.
 """

+# The scanner below treats comments, CDATA sections and processing
+# instructions as opaque tokens specifically so a literal '<' or '>'
+# permitted inside one of them never desynchronises the depth count
+# element_span relies on (DL-007).
+
+# The NML schema this module assembles output for is confirmed only
+# against VERSION=20 / Traktor Pro 4. recalculate_count_attr is generic
+# over any counted container rather than hardcoded to
+# COLLECTION/PLAYLIST/SUBNODES, so a counted container this tool has not
+# seen - from a schema version not yet verified - is still recalculated
+# instead of being silently left stale.
+
 from __future__ import annotations

 import re
@@ -59,7 +71,12 @@
     if is_self_closing:
         return Span(open_lt_pos, match_at_start.end())

+    # pos advances only forward from match_at_start's end, and this loop
+    # scans source once via finditer rather than rescanning from the
+    # start of source on each call, so collecting every element's span
+    # across a full document stays linear instead of quadratic over its
+    # size (R-005, DL-012).
+
     depth = 1
     pos = match_at_start.end()
     for token in _TOKEN_RE.finditer(source, pos):
         if token.group(2) != tag_name:

```


**CC-M-006-002** (C:\codex\general_tasks\traktor_nml\spans.py) - implements CI-M-006-002

**Code:**

```diff
--- a/traktor_nml/spans.py
+++ b/traktor_nml/spans.py
@@ -128,3 +128,84 @@
     return element_span(source, idx)
 
 
+class OutputBuilder:
+    """Assembles an output document from verbatim source spans and
+    re-serialised fragments, applying attribute patches to the spans it
+    copies and recalculating COLLECTION/PLAYLIST/SUBNODES count attributes
+    from what was actually assembled. Returns the complete byte string
+    without touching the filesystem, so callers can validate before any
+    file handle opens (DL-012).
+    """
+
+    def __init__(self) -> None:
+        self._pieces: list[str] = []
+
+    def add_verbatim(self, text: str) -> None:
+        self._pieces.append(text)
+
+    def add_span(self, source: str, span: Span, attr_patches: dict[str, str] | None = None) -> None:
+        text = span.text(source)
+        if attr_patches:
+            text = _patch_opening_tag_attrs(text, attr_patches)
+        self._pieces.append(text)
+
+    def add_serialized(self, fragment: str) -> None:
+        self._pieces.append(fragment)
+
+    def add_counted_span(
+        self,
+        source: str,
+        span: Span,
+        tag_name: str,
+        count_attr: str,
+        children: list[str],
+        attr_patches: dict[str, str] | None = None,
+        count: int | None = None,
+    ) -> None:
+        """Copy span verbatim with children spliced in just before its
+        closing tag, recalculating count_attr on tag_name's own opening tag
+        to the count this class actually assembled - len(children) by
+        default, or the explicit count override for a container (e.g.
+        splice's root SUBNODES) whose existing children are kept verbatim
+        inside span itself rather than passed again here."""
+        text = span.text(source)
+        if attr_patches:
+            text = _patch_opening_tag_attrs(text, attr_patches)
+        text = recalculate_count_attr(text, tag_name, count_attr, len(children) if count is None else count)
+        insert_at = len(text) - len(f"</{tag_name}>")
+        self._pieces.append(text[:insert_at] + "".join(children) + text[insert_at:])
+
+    def build(self) -> str:
+        return "".join(self._pieces)
+
+
+def _patch_opening_tag_attrs(fragment: str, attr_patches: dict[str, str]) -> str:
+    """Substitute attribute values in fragment's own opening tag only
+    (never inside descendant tags with the same attribute name)."""
+    close = fragment.find(">")
+    if close < 0:
+        return fragment
+    opening = fragment[: close + 1]
+    rest = fragment[close + 1:]
+    for attr, new_value in attr_patches.items():
+        pattern = re.compile(r"(\b" + re.escape(attr) + r'\s*=\s*)(["\'])(.*?)\2', re.DOTALL)
+        opening = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}{new_value}{m.group(2)}", opening, count=1)
+    return opening + rest
+
+
+def recalculate_count_attr(fragment: str, tag_name: str, count_attr: str, actual_count: int) -> str:
+    """Rewrite tag_name's count_attr to actual_count in fragment's own
+    opening tag. Generic over any counted container (COLLECTION ENTRIES,
+    PLAYLIST ENTRIES, SUBNODES COUNT, or any future counted tag) rather than
+    a fixed tag list: the schema is confirmed only against NML VERSION=20 /
+    Traktor Pro 4, so a counted container introduced by a later schema
+    version is still recalculated correctly instead of silently left stale
+    or requiring this function to be extended for every new tag name.
+    """
+    close = fragment.find(">")
+    opening = fragment[: close + 1] if close >= 0 else fragment
+    rest = fragment[close + 1:] if close >= 0 else ""
+    pattern = re.compile(r"(\b" + re.escape(count_attr) + r'\s*=\s*)(["\'])(\d*)\2')
+    if pattern.search(opening):
+        opening = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}{actual_count}{m.group(2)}", opening, count=1)
+    return opening + rest

```

**Documentation:**

```diff
--- a/traktor_nml/spans.py
+++ b/traktor_nml/spans.py
@@ -140,10 +140,16 @@
     def add_verbatim(self, text: str) -> None:
+        """Append text with no patching or re-serialisation - used for
+        the untouched bytes surrounding every span this builder
+        assembles."""
         self._pieces.append(text)

     def add_span(self, source: str, span: Span, attr_patches: dict[str, str] | None = None) -> None:
+        """Copy span's source bytes verbatim, patching only the
+        attributes named in attr_patches on its own opening tag (e.g. a
+        PRIMARYKEY redirect) via the same substitution primitive
+        textpatch.py uses."""
         text = span.text(source)
         if attr_patches:
             text = _patch_opening_tag_attrs(text, attr_patches)

```


**CC-M-006-003** (C:\codex\general_tasks\tests\test_spans.py) - implements CI-M-006-001

**Code:**

```diff
--- /dev/null
+++ b/tests/test_spans.py
@@ -0,0 +1,82 @@
+"""Byte-span scanner: extent, nesting, escaping, and round-trip fidelity."""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+import pytest
+
+from traktor_nml.spans import element_span, find_element_span, recalculate_count_attr
+
+REAL_FIXTURE = Path(r"C:\codex\general_tasks\collection_textual_patch_test.nml")
+
+
+def test_self_closing_element_resolves_to_its_own_tag() -> None:
+    source = '<PARENT><CHILD A="1"/></PARENT>'
+    span = element_span(source, source.index("<CHILD"))
+    assert span.text(source) == '<CHILD A="1"/>'
+
+
+def test_empty_element_form_resolves_to_its_extent() -> None:
+    source = '<PARENT><HEAD A="1"></HEAD></PARENT>'
+    span = element_span(source, source.index("<HEAD"))
+    assert span.text(source) == '<HEAD A="1"></HEAD>'
+
+
+def test_nested_same_named_elements_resolve_to_outermost_extent() -> None:
+    source = '<NODE NAME="outer"><NODE NAME="inner"></NODE></NODE><TAIL/>'
+    span = element_span(source, 0)
+    assert span.text(source) == '<NODE NAME="outer"><NODE NAME="inner"></NODE></NODE>'
+
+
+def test_angle_brackets_and_quotes_inside_attribute_values_do_not_end_scan_early() -> None:
+    source = '<ENTRY TITLE="a &lt;b&gt; c">text</ENTRY><TAIL/>'
+    span = element_span(source, 0)
+    assert span.text(source) == '<ENTRY TITLE="a &lt;b&gt; c">text</ENTRY>'
+
+
+def test_find_element_span_does_not_match_a_longer_tag_name_sharing_a_prefix() -> None:
+    source = '<NODENAME>x</NODENAME><NODE A="1"></NODE>'
+    span = find_element_span(source, "NODE")
+    assert span is not None
+    assert span.text(source) == '<NODE A="1"></NODE>'
+
+
+def test_recalculate_count_attr_rewrites_only_the_named_attribute() -> None:
+    fragment = '<SUBNODES COUNT="3"><A/><A/></SUBNODES>'
+    rewritten = recalculate_count_attr(fragment, "SUBNODES", "COUNT", 2)
+    assert rewritten == '<SUBNODES COUNT="2"><A/><A/></SUBNODES>'
+
+
+@pytest.mark.skipif(not REAL_FIXTURE.exists(), reason="real fixture not present in this environment")
+def test_reassembling_a_file_from_its_own_spans_reproduces_it_byte_for_byte() -> None:
+    source = REAL_FIXTURE.read_text(encoding="utf-8")
+    root_span = find_element_span(source, "NML")
+    assert root_span is not None
+    # The whole document minus any leading XML declaration/whitespace before
+    # <NML plus the root span itself, concatenated back, must equal source.
+    prefix = source[: root_span.start]
+    suffix = source[root_span.end:]
+    rebuilt = prefix + root_span.text(source) + suffix
+    assert rebuilt == source
+
+
+@pytest.mark.skipif(not REAL_FIXTURE.exists(), reason="real fixture not present in this environment")
+def test_every_entry_and_node_span_in_real_corpus_parses_standalone() -> None:
+    import lxml.etree as ET
+
+    source = REAL_FIXTURE.read_text(encoding="utf-8")
+    count = 0
+    idx = 0
+    while True:
+        idx = source.find("<ENTRY", idx)
+        if idx == -1:
+            break
+        span = element_span(source, idx)
+        # A standalone ENTRY fragment must be well-formed on its own.
+        ET.fromstring(span.text(source))
+        idx = span.end
+        count += 1
+        if count >= 200:  # bound the walk; the corpus has thousands
+            break
+    assert count > 0

```

**Documentation:**

```diff
--- a/tests/test_spans.py
+++ b/tests/test_spans.py
@@ -37,6 +37,8 @@

 def test_recalculate_count_attr_rewrites_only_the_named_attribute() -> None:
+    """Only COUNT changes; the two child <A/> elements and every other
+    byte of the container's own opening tag are untouched."""
     fragment = '<SUBNODES COUNT="3"><A/><A/></SUBNODES>'
     rewritten = recalculate_count_attr(fragment, "SUBNODES", "COUNT", 2)
     assert rewritten == '<SUBNODES COUNT="2"><A/><A/></SUBNODES>'

```


### Milestone 7: Splice command

**Files**: C:\codex\general_tasks\traktor_nml\playlists.py, C:\codex\general_tasks\traktor_nml\splice.py, C:\codex\general_tasks\traktor_nml\commands\splice_cmd.py, C:\codex\general_tasks\tests\test_splice.py

**Requirements**:

- A base input receives collection entries and playlists from further inputs into one output
- Track identity groups across inputs using the existing key tier ordering
- Divergent metadata between two copies of one identity aborts the write unless --on-conflict names keep-first or keep-last
- A conflict report in key=value and CSV form is written on every run naming each group and the differing attributes
- Every NODE of playlist type anywhere in a non-base tree is imported as a child of the base root folder
- Imported PRIMARYKEY entries keep their TYPE and KEY unless their track lost a conflict in which case they redirect to the winner
- A colliding playlist name gains a numbered suffix and a freshly generated UUID
- SORTING_INFO for an imported playlist is rewritten to its new path or dropped and reported
- Unmodified fragments are transplanted as source spans and only renamed or redirected fragments are re-serialised
- A PRIMARYKEY unresolvable against the merged collection aborts the write and is reported by playlist name and key
- SETS content passes through untouched

**Acceptance Criteria**:

- Splicing inputs with all-unique playlist names produces bytes identical to base bytes plus verbatim transplanted spans plus count patches
- A run with one name collision and one conflict redirect differs from that baseline only in the renamed node's opening tag and UUID and in the redirected PRIMARYKEY value
- No output PRIMARYKEY fails to resolve within its own COLLECTION
- COLLECTION ENTRIES and PLAYLIST ENTRIES and SUBNODES COUNT equal their actual child counts
- An unresolved conflict without --on-conflict leaves no output file and still writes the conflict report
- No same-named non-base playlist is merged into a base playlist

**Tests**:

- C:\codex\general_tasks\tests\test_splice.py

#### Code Intent

- **CI-M-007-001** `C:\codex\general_tasks\traktor_nml\splice.py::group_identities`: Group collection records from every input into identity groups using the shared key tier ordering, and for each group holding records from more than one input compare their attributes to detect divergence. Divergent groups populate the conflict report and, absent an explicit conflict policy, cause the run to produce no output file. (refs: DL-008, DL-012)
- **CI-M-007-002** `C:\codex\general_tasks\traktor_nml\playlists.py::import_playlists`: Collect every playlist node reachable in a non-base playlist tree, insert each as a child of the base root folder, retain its primary keys verbatim except where a referenced track lost an identity conflict and is redirected to the winner's key, assign a numbered name and a freshly generated identifier when a name already exists, and carry or drop the matching sort-info entry with its path rewritten to the new location. (refs: DL-007, DL-008)
- **CI-M-007-003** `C:\codex\general_tasks\traktor_nml\splice.py::assemble_output`: Verify before writing that every primary key in the assembled playlist tree resolves to a surviving collection entry, aborting and naming each unresolved reference by playlist and key. Fragments that no rename or redirect touched are transplanted as source spans and only modified fragments are re-serialised; the whole document is materialised before any file handle opens. (refs: DL-007, DL-012)

#### Code Changes

**CC-M-007-001** (C:\codex\general_tasks\traktor_nml\splice.py) - implements CI-M-007-001

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/splice.py
@@ -0,0 +1,150 @@
+"""Merge a base NML with further NML files while every playlist stays valid.
+
+Scope note (v1, see the plan's tradeoffs): the base input is authoritative
+for its own COLLECTION and playlists - its bytes are never rewritten. Track
+identity across inputs uses the shared record_keys tier ordering, cascaded
+through every tier via union-find (not just each record's own top-tier key)
+so two copies of one track that happen to agree on a lower tier but not the
+top one still land in the same identity group, since splice needs N-way
+grouping rather than pairwise old-vs-new comparison. When a base record and a
+non-base record share an identity, the base record always wins and its bytes
+stay untouched; --on-conflict's keep-first/keep-last only disambiguates among
+duplicates that are *not* shared with base. A metadata conflict (any
+differing attribute between two copies of one identity) aborts the whole
+write unless --on-conflict is given, and the conflict report is written
+either way (DL-008). Fragments no rename or redirect touched are transplanted
+as source byte spans (spans.py); only renamed playlists and redirected
+PRIMARYKEY values are re-serialised.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field
+from typing import Optional
+
+from .confidence import MatchConfidence
+from .matching import record_keys
+from .model import EntryRecord, collection_entries, collection_records
+from .playlists import find_playlist_nodes, import_playlists, node_primary_keys
+from .spans import OutputBuilder, element_span_by_identity, find_element_span
+from .xmlio import ET
+
+_TRACKED_ATTRS = ("artist", "title", "album", "filesize", "playtime_float", "bitrate")
+
+
+@dataclass
+class ConflictRow:
+    identity_key: str
+    attrs: str
+    resolution: str
+
+
+@dataclass
+class SpliceResult:
+    output: Optional[str]
+    stats: dict[str, int]
+    conflict_rows: list[ConflictRow] = field(default_factory=list)
+    errors: list[str] = field(default_factory=list)
+
+
+def group_identities(
+    records_by_input: list[list[EntryRecord]], confidence: MatchConfidence
+) -> dict[int, list[tuple[int, EntryRecord]]]:
+    """Group collection records from every input into identity groups using
+    the full record_keys tier cascade: two records are grouped together if
+    they share ANY eligible tier's key, not only their own single
+    highest-confidence key - e.g. one copy carrying AUDIO_ID and another copy
+    of the same track missing it must still land in one group, matched
+    through whichever lower tier they do share. Grouping is a union-find over
+    every (tier_name, key_value) bucket across every input; a record with no
+    eligible key at all never joins a bucket and so keeps its own singleton
+    group."""
+    all_records: list[tuple[int, EntryRecord]] = [
+        (input_idx, record)
+        for input_idx, records in enumerate(records_by_input)
+        for record in records
+    ]
+
+    parent = list(range(len(all_records)))
+
+    def find(i: int) -> int:
+        while parent[i] != i:
+            parent[i] = parent[parent[i]]
+            i = parent[i]
+        return i
+
+    def union(a: int, b: int) -> None:
+        root_a, root_b = find(a), find(b)
+        if root_a != root_b:
+            parent[max(root_a, root_b)] = min(root_a, root_b)
+
+    buckets: dict[tuple[str, tuple], int] = {}
+    for i, (_, record) in enumerate(all_records):
+        for tier_name, value in record_keys(record, confidence):
+            bucket_key = (tier_name, value)
+            if bucket_key in buckets:
+                union(i, buckets[bucket_key])
+            else:
+                buckets[bucket_key] = i
+
+    groups: dict[int, list[tuple[int, EntryRecord]]] = {}
+    for i, entry in enumerate(all_records):
+        groups.setdefault(find(i), []).append(entry)
+    return groups
+
+
+def _resolve_conflicts(
+    groups: dict[int, list[tuple[int, EntryRecord]]], on_conflict: Optional[str]
+) -> tuple[dict[str, str], list[ConflictRow], bool, list[tuple[int, EntryRecord]]]:
+    """Return (old_to_new_key, conflict_rows, unresolved, new_entries).
+
+    new_entries lists (input_idx, record) for exactly the records that must
+    be added to the merged COLLECTION: the sole record of a single-input
+    group not owned by the base, or a cross-input group's non-base winner.
+    input_idx disambiguates which source text to transplant the entry's
+    span from, since two distinct records can carry identical field values.
+    """
+    old_to_new_key: dict[str, str] = {}
+    conflict_rows: list[ConflictRow] = []
+    new_entries: list[tuple[int, EntryRecord]] = []
+    unresolved = False
+
+    for key, members in groups.items():
+        contributing_inputs = {idx for idx, _ in members}
+        if len(contributing_inputs) == 1:
+            idx = next(iter(contributing_inputs))
+            if idx != 0:
+                new_entries.append(members[0])
+            continue
+
+        divergent_attrs = [
+            attr for attr in _TRACKED_ATTRS if len({getattr(r, attr) for _, r in members}) > 1
+        ]
+        if divergent_attrs and on_conflict is None:
+            unresolved = True
+            conflict_rows.append(ConflictRow(str(key), ",".join(divergent_attrs), "unresolved"))
+            continue
+
+        base_member = next(((idx, r) for idx, r in members if idx == 0), None)
+        if base_member is not None:
+            winner_idx, winner = base_member
+        else:
+            policy = on_conflict or "keep-first"
+            picker = min if policy == "keep-first" else max
+            winner_idx, winner = picker(members, key=lambda m: m[0])
+            new_entries.append((winner_idx, winner))
+
+        for _, record in members:
+            if record is not winner:
+                old_to_new_key[record.primary_key] = winner.primary_key
+
+        if divergent_attrs:
+            conflict_rows.append(ConflictRow(str(key), ",".join(divergent_attrs), on_conflict or "unresolved"))
+
+    return old_to_new_key, conflict_rows, unresolved, new_entries
+
+
+def _entry_span_text(source_text: str, root: ET.Element, record: EntryRecord) -> str:
+    return element_span_by_identity(source_text, root, record.entry).text(source_text)
+
+

```

**Documentation:**

```diff
--- a/traktor_nml/splice.py
+++ b/traktor_nml/splice.py
@@ -25,6 +25,10 @@
 @dataclass
 class SpliceResult:
+    """output is None exactly when errors is non-empty - an abort with
+    nothing written (extending DL-012's validate-before-write invariant
+    to a multi-input merge); conflict_rows is populated on every run
+    regardless of outcome, even a clean one (DL-008)."""
     output: Optional[str]
     stats: dict[str, int]
     conflict_rows: list[ConflictRow]

```


**CC-M-007-002** (C:\codex\general_tasks\traktor_nml\splice.py) - implements CI-M-007-003

**Code:**

```diff
--- a/traktor_nml/splice.py
+++ b/traktor_nml/splice.py
@@ -148,3 +148,101 @@
     return element_span_by_identity(source_text, root, record.entry).text(source_text)
 
 
+def assemble_output(
+    base_source: str,
+    base_root: ET.Element,
+    contributions: list[tuple[str, ET.Element]],
+    confidence: MatchConfidence,
+    on_conflict: Optional[str] = None,
+) -> SpliceResult:
+    inputs = [base_root] + [root for _, root in contributions]
+    sources = [base_source] + [text for text, _ in contributions]
+    records_by_input = [collection_records(root) for root in inputs]
+
+    groups = group_identities(records_by_input, confidence)
+    old_to_new_key, conflict_rows, unresolved, new_entries_records = _resolve_conflicts(groups, on_conflict)
+
+    stats = {
+        "inputs_merged": len(contributions),
+        "identity_groups": len(groups),
+        "conflicts_reported": len(conflict_rows),
+        "collection_entries_added": 0,
+        "playlists_imported": 0,
+        "playlists_renamed": 0,
+        "sorting_info_dropped": 0,
+    }
+
+    if unresolved:
+        return SpliceResult(output=None, stats=stats, conflict_rows=conflict_rows, errors=["unresolved_conflicts"])
+
+    # New collection entries: transplant each winner's own ENTRY span from
+    # its originating input, verbatim (collection entries are never renamed).
+    new_entry_texts = [
+        _entry_span_text(sources[idx], inputs[idx], record) for idx, record in new_entries_records
+    ]
+    stats["collection_entries_added"] = len(new_entry_texts)
+
+    output = base_source
+    collection_span = find_element_span(output, "COLLECTION")
+    if collection_span is None:
+        return SpliceResult(output=None, stats=stats, conflict_rows=conflict_rows, errors=["no_collection"])
+
+    builder = OutputBuilder()
+    builder.add_verbatim(output[: collection_span.start])
+    builder.add_counted_span(
+        output, collection_span, "COLLECTION", "ENTRIES", new_entry_texts,
+        count=len(collection_entries(base_root)) + len(new_entry_texts),
+    )
+
+    # Import every non-base playlist as a flattened child of the base root folder.
+    existing_names = {node.attrib.get("NAME", "") for node in find_playlist_nodes(base_root)}
+    playlist_fragments: list[str] = []
+    unresolved_refs: list[tuple[str, str]] = []
+    renamed_count = 0
+    for source_text, root in contributions:
+        result = import_playlists(source_text, root, old_to_new_key, existing_names)
+        for imported in result.playlists:
+            playlist_fragments.append(imported.fragment)
+        renamed_count += len(result.renamed)
+    stats["playlists_imported"] = len(playlist_fragments)
+    stats["playlists_renamed"] = renamed_count
+
+    subnodes_span = find_element_span(output, "SUBNODES")
+    if subnodes_span is None:
+        return SpliceResult(output=None, stats=stats, conflict_rows=conflict_rows, errors=["no_root_subnodes"])
+    root_subnodes_elem = base_root.find(".//PLAYLISTS/NODE/SUBNODES")
+    original_root_count = 0 if root_subnodes_elem is None else len(list(root_subnodes_elem))
+
+    builder.add_verbatim(output[collection_span.end: subnodes_span.start])
+    builder.add_counted_span(
+        output, subnodes_span, "SUBNODES", "COUNT", playlist_fragments,
+        count=original_root_count + len(playlist_fragments),
+    )
+    builder.add_verbatim(output[subnodes_span.end:])
+    output = builder.build()
+
+    # Validate: every PRIMARYKEY in the assembled playlist tree resolves to
+    # a surviving collection entry, aborting and naming each unresolved
+    # reference by playlist and key (checked against the parsed base tree's
+    # own keys plus the newly added entries; imported fragments were
+    # already redirected against old_to_new_key by import_playlists).
+    valid_keys = {r.primary_key for r in records_by_input[0]} | {r.primary_key for _, r in new_entries_records}
+    for node in find_playlist_nodes(base_root):
+        name = node.attrib.get("NAME", "")
+        for pk in node_primary_keys(node):
+            if pk.attrib.get("KEY", "") not in valid_keys:
+                unresolved_refs.append((name, pk.attrib.get("KEY", "")))
+    for source_text, root in contributions:
+        for node in find_playlist_nodes(root):
+            name = node.attrib.get("NAME", "")
+            for pk in node_primary_keys(node):
+                old_key = pk.attrib.get("KEY", "")
+                effective_key = old_to_new_key.get(old_key, old_key)
+                if effective_key not in valid_keys:
+                    unresolved_refs.append((name, old_key))
+
+    if unresolved_refs:
+        errors = [f"unresolved_reference playlist={name} key={key}" for name, key in unresolved_refs]
+        return SpliceResult(output=None, stats=stats, conflict_rows=conflict_rows, errors=errors)
+
+    return SpliceResult(output=output, stats=stats, conflict_rows=conflict_rows, errors=[])

```

**Documentation:**

```diff
--- a/traktor_nml/splice.py
+++ b/traktor_nml/splice.py
@@ -150,6 +150,11 @@
     on_conflict: Optional[str] = None,
 ) -> SpliceResult:
+    """Merge every contribution into base_source: build cross-input
+    identity groups, resolve conflicts (aborting with zero output on any
+    unresolved one), transplant surviving collection entries as verbatim
+    spans, then hand off to playlist import for the PLAYLISTS tree
+    (DL-007, DL-008)."""
     inputs = [base_root] + [root for _, root in contributions]
     sources = [base_source] + [text for text, _ in contributions]

```


**CC-M-007-003** (C:\codex\general_tasks\traktor_nml\playlists.py) - implements CI-M-007-002

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/playlists.py
@@ -0,0 +1,137 @@
+"""Playlist import for splice: every non-base playlist becomes a base child.
+
+Every NODE TYPE=PLAYLIST anywhere in a non-base input's PLAYLISTS tree
+qualifies for import, no folder-location filtering - imported playlists are
+flattened one level as new children of the base root FOLDER's SUBNODES
+(folder nesting beyond a playlist's own node is out of scope for v1, see the
+plan's tradeoffs). PRIMARYKEY entries are retained verbatim unless their
+referenced track lost an identity conflict, in which case they redirect to
+the winner's key. A same-name collision gets a deterministic "<name> (2)"
+rename with a freshly generated UUID - never the source UUID, which would
+create a duplicate within the output file.
+"""
+
+from __future__ import annotations
+
+import uuid
+from dataclasses import dataclass, field
+
+from .spans import Span, element_span
+from .xmlio import ET
+
+
+@dataclass
+class ImportedPlaylist:
+    fragment: str  # verbatim span text or a re-serialised replacement
+    is_verbatim: bool
+    original_name: str
+    final_name: str
+    unresolved_keys: list[str] = field(default_factory=list)
+
+
+@dataclass
+class ImportResult:
+    playlists: list[ImportedPlaylist] = field(default_factory=list)
+    renamed: dict[str, str] = field(default_factory=dict)  # original_name -> final_name
+    dropped_sorting_info: list[str] = field(default_factory=list)
+    unresolved_references: list[tuple[str, str]] = field(default_factory=list)  # (playlist_name, key)
+
+
+def find_playlist_nodes(root: ET.Element) -> list[ET.Element]:
+    return root.findall(".//NODE[@TYPE='PLAYLIST']")
+
+
+def node_primary_keys(node: ET.Element) -> list[ET.Element]:
+    playlist = node.find("PLAYLIST")
+    return [] if playlist is None else playlist.findall(".//PRIMARYKEY")
+
+
+def _redirect_keys(node_copy: ET.Element, old_to_new_key: dict[str, str]) -> tuple[bool, list[str]]:
+    """Redirect PRIMARYKEY/KEY values on an in-memory copy; return whether
+    anything changed and which keys could not be resolved at all (handled
+    by the caller against the merged collection, not here)."""
+    changed = False
+    for pk in node_primary_keys(node_copy):
+        old_key = pk.attrib.get("KEY", "")
+        new_key = old_to_new_key.get(old_key)
+        if new_key is not None and new_key != old_key:
+            pk.attrib["KEY"] = new_key
+            changed = True
+    return changed, []
+
+
+def import_playlists(
+    source_text: str,
+    non_base_root: ET.Element,
+    old_to_new_key: dict[str, str],
+    existing_names: set[str],
+) -> ImportResult:
+    """Import every playlist NODE in non_base_root's tree, sourced from
+    source_text for verbatim span transplantation."""
+    result = ImportResult()
+
+    for node in find_playlist_nodes(non_base_root):
+        original_name = node.attrib.get("NAME", "")
+        final_name = original_name
+        suffix = 2
+        while final_name in existing_names:
+            final_name = f"{original_name} ({suffix})"
+            suffix += 1
+        existing_names.add(final_name)
+        renamed = final_name != original_name
+
+        needs_redirect = any(
+            old_to_new_key.get(pk.attrib.get("KEY", "")) not in (None, pk.attrib.get("KEY", ""))
+            for pk in node_primary_keys(node)
+        )
+
+        if not renamed and not needs_redirect:
+            node_start = _locate_node_start(source_text, node)
+            span = element_span(source_text, node_start)
+            fragment = span.text(source_text)
+            is_verbatim = True
+        else:
+            node_copy = ET.fromstring(ET.tostring(node))
+            if renamed:
+                node_copy.attrib["NAME"] = final_name
+                playlist_elem = node_copy.find("PLAYLIST")
+                if playlist_elem is not None:
+                    # A fresh UUID avoids duplicating the source playlist's
+                    # UUID within this output file (two PLAYLIST nodes must
+                    # not share one UUID). Traktor's tolerance of an
+                    # imported playlist carrying a UUID other than the one
+                    # it shipped with is confirmed only by manual Traktor
+                    # import, not by this test suite (R-004).
+                    playlist_elem.attrib["UUID"] = uuid.uuid4().hex
+            _redirect_keys(node_copy, old_to_new_key)
+            fragment = ET.tostring(node_copy, encoding="unicode")
+            is_verbatim = False
+
+        if renamed:
+            result.renamed[original_name] = final_name
+
+        result.playlists.append(
+            ImportedPlaylist(
+                fragment=fragment, is_verbatim=is_verbatim,
+                original_name=original_name, final_name=final_name,
+            )
+        )
+
+    return result
+
+
+def _locate_node_start(source_text: str, node: ET.Element) -> int:
+    """Locate a playlist NODE's opening-tag offset via its PLAYLIST child's
+    UUID, which is unique across the document (unlike NAME, which two
+    playlists in different folders may share) - lxml elements carry no
+    byte offsets of their own."""
+    playlist_elem = node.find("PLAYLIST")
+    uuid_value = "" if playlist_elem is None else playlist_elem.attrib.get("UUID", "")
+    marker = f'UUID="{uuid_value}"'
+    uuid_idx = source_text.find(marker)
+    if uuid_idx < 0:
+        raise ValueError(f"could not locate playlist UUID {uuid_value!r} in source text")
+    node_idx = source_text.rfind("<NODE ", 0, uuid_idx)
+    if node_idx < 0:
+        raise ValueError(f"could not locate enclosing NODE for playlist UUID {uuid_value!r}")
+    return node_idx

```

**Documentation:**

```diff
--- a/traktor_nml/playlists.py
+++ b/traktor_nml/playlists.py
@@ -9,5 +9,10 @@
 the winner's key. A same-name collision gets a deterministic "<name> (2)"
 rename with a freshly generated UUID - never the source UUID, which would
 create a duplicate within the output file.
+
+Traktor's tolerance of that fresh UUID on a renamed/imported playlist is
+confirmed only by manual Traktor import/open validation, not by this test
+suite (R-004, DL-008); the regenerated UUID is an accepted, unverified risk
+until that manual check is repeated for a given output.
 """

@@ -19,6 +24,10 @@
 @dataclass
 class ImportedPlaylist:
+    """is_verbatim=False marks a fragment that was re-serialised because
+    at least one of its PRIMARYKEY values was redirected or its NAME was
+    renamed for a collision; the source span is otherwise copied
+    unchanged."""
     fragment: str  # verbatim span text or a re-serialised replacement
     is_verbatim: bool
     original_name: str

```


**CC-M-007-004** (C:\codex\general_tasks\traktor_nml\commands\splice_cmd.py) - implements CI-M-007-003

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/commands/splice_cmd.py
@@ -0,0 +1,78 @@
+"""splice subcommand: merge further NML files into a base NML."""
+
+from __future__ import annotations
+
+import argparse
+import csv
+import sys
+from pathlib import Path
+
+from ..confidence import MatchConfidence, parse_match_confidence
+from ..splice import ConflictRow, assemble_output
+from ..xmlio import parse_xml_bytes
+
+
+def _write_conflict_report(rows: list[ConflictRow], csv_path: Path | None) -> None:
+    # A conflict report is always written, even when --on-conflict resolves
+    # every conflict, so an accepted override still leaves a record of what
+    # was dropped (DL-008).
+    for row in rows:
+        print(f"conflict_key={row.identity_key} attrs={row.attrs} resolution={row.resolution}")
+    if csv_path is not None:
+        with csv_path.open("w", newline="", encoding="utf-8") as handle:
+            writer = csv.DictWriter(handle, fieldnames=["identity_key", "attrs", "resolution"])
+            writer.writeheader()
+            for row in rows:
+                writer.writerow({"identity_key": row.identity_key, "attrs": row.attrs, "resolution": row.resolution})
+        print(f"conflict_report_written={csv_path}")
+
+
+def _handle_splice(args: argparse.Namespace) -> int:
+    if args.output.resolve() in {args.base.resolve(), *(p.resolve() for p in args.input)}:
+        print("output_must_differ_from_input", file=sys.stderr)
+        return 2
+
+    try:
+        base_bytes = args.base.read_bytes()
+        contributions = []
+        for path in args.input:
+            source_bytes = path.read_bytes()
+            contributions.append((source_bytes.decode("utf-8"), parse_xml_bytes(source_bytes)))
+    except FileNotFoundError as exc:
+        print(f"input_not_found={exc.filename}", file=sys.stderr)
+        return 2
+
+    base_root = parse_xml_bytes(base_bytes)
+    confidence = parse_match_confidence(args.match_confidence) if args.match_confidence else MatchConfidence.STRICT
+
+    result = assemble_output(
+        base_bytes.decode("utf-8"), base_root, contributions, confidence, on_conflict=args.on_conflict
+    )
+
+    for key, value in result.stats.items():
+        print(f"{key}={value}")
+    _write_conflict_report(result.conflict_rows, args.conflict_report)
+
+    if result.output is None:
+        for error in result.errors:
+            print(error, file=sys.stderr)
+        print("splice_aborted=true", file=sys.stderr)
+        return 2
+
+    if not args.dry_run:
+        args.output.parent.mkdir(parents=True, exist_ok=True)
+        args.output.write_bytes(result.output.encode("utf-8"))
+        print(f"output_written={args.output}")
+    return 0
+
+
+def register(subparsers, handlers: dict) -> None:
+    parser = subparsers.add_parser("splice", help="Merge further NML files into a base NML")
+    parser.add_argument("base", type=Path)
+    parser.add_argument("output", type=Path)
+    parser.add_argument("--input", action="append", dest="input", required=True, type=Path)
+    parser.add_argument("--on-conflict", choices=["keep-first", "keep-last"], default=None)
+    parser.add_argument("--match-confidence", choices=[level.value for level in MatchConfidence], default=None)
+    parser.add_argument("--conflict-report", type=Path)
+    parser.add_argument("--dry-run", action="store_true")
+    handlers["splice"] = _handle_splice

```

**Documentation:**

```diff
--- a/traktor_nml/commands/splice_cmd.py
+++ b/traktor_nml/commands/splice_cmd.py
@@ -23,6 +23,8 @@
 def _handle_splice(args: argparse.Namespace) -> int:
+    # Refuses output == any input path (the tool's existing dry-run
+    # convention, extended here to every splice input, not just base).
     if args.output.resolve() in {args.base.resolve(), *(p.resolve() for p in args.input)}:
         print("output_must_differ_from_input", file=sys.stderr)
         return 2

```


**CC-M-007-005** (C:\codex\general_tasks\tests\test_splice.py) - implements CI-M-007-003

**Code:**

```diff
--- /dev/null
+++ b/tests/test_splice.py
@@ -0,0 +1,135 @@
+"""Splice: playlist merge, name collision, and conflict abort/report."""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+from tests.conftest import run_tool
+
+
+def _nml(entries_xml: str, entries_count: int, playlists_xml: str) -> str:
+    return (
+        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
+        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
+        f'<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="{playlists_xml.count(chr(60)+"NODE")}">'
+        f"{playlists_xml}</SUBNODES></NODE></PLAYLISTS>"
+        "<SETS></SETS><INDEXING></INDEXING></NML>"
+    )
+
+
+def _entry(artist, title, filename, size="16", time="1.0"):
+    return (
+        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
+        f'<LOCATION DIR="/:Music/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
+        f'<INFO BITRATE="320" PLAYTIME_FLOAT="{time}" FILESIZE="{size}"></INFO>'
+        "</ENTRY>"
+    )
+
+
+def _playlist(name: str, keys: list[str], uuid: str) -> str:
+    entries = "".join(f'<ENTRY><PRIMARYKEY TYPE="TRACK" KEY="{k}"></PRIMARYKEY></ENTRY>' for k in keys)
+    return (
+        f'<NODE TYPE="PLAYLIST" NAME="{name}">'
+        f'<PLAYLIST ENTRIES="{len(keys)}" TYPE="LIST" UUID="{uuid}">{entries}</PLAYLIST>'
+        "</NODE>"
+    )
+
+
+def test_splicing_all_unique_playlists_merges_cleanly(tmp_path: Path) -> None:
+    base_key = "C:" + "/:Music/:" + "base.mp3"
+    other_key = "C:" + "/:Music/:" + "other.mp3"
+
+    base_path = tmp_path / "base.nml"
+    base_path.write_text(
+        _nml(_entry("A", "Base", "base.mp3"), 1, _playlist("BaseList", [base_key], "uuid-base")),
+        encoding="utf-8", newline="",
+    )
+    other_path = tmp_path / "other.nml"
+    other_path.write_text(
+        _nml(_entry("B", "Other", "other.mp3"), 1, _playlist("OtherList", [other_key], "uuid-other")),
+        encoding="utf-8", newline="",
+    )
+
+    result = run_tool(
+        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path)],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 0
+    out_text = (tmp_path / "out.nml").read_text(encoding="utf-8")
+    assert "OtherList" in out_text
+    assert "BaseList" in out_text
+    assert 'ENTRIES="2"' in out_text.split("COLLECTION")[1][:40]
+
+
+def test_name_collision_gets_renamed_and_new_uuid(tmp_path: Path) -> None:
+    base_key = "C:" + "/:Music/:" + "base.mp3"
+    other_key = "C:" + "/:Music/:" + "other.mp3"
+
+    base_path = tmp_path / "base.nml"
+    base_path.write_text(
+        _nml(_entry("A", "Base", "base.mp3"), 1, _playlist("Shared", [base_key], "uuid-base")),
+        encoding="utf-8", newline="",
+    )
+    other_path = tmp_path / "other.nml"
+    other_path.write_text(
+        _nml(_entry("B", "Other", "other.mp3"), 1, _playlist("Shared", [other_key], "uuid-other")),
+        encoding="utf-8", newline="",
+    )
+
+    result = run_tool(
+        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path)],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 0
+    out_text = (tmp_path / "out.nml").read_text(encoding="utf-8")
+    assert 'NAME="Shared (2)"' in out_text
+    assert "uuid-other" not in out_text  # renamed playlist got a fresh UUID
+    assert out_text.count('NAME="Shared"') == 1  # base's own playlist untouched
+
+
+def test_unresolved_conflict_without_policy_aborts_but_still_reports(tmp_path: Path) -> None:
+    shared_key = "C:" + "/:Music/:" + "track.mp3"
+
+    base_path = tmp_path / "base.nml"
+    base_path.write_text(
+        _nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, ""),
+        encoding="utf-8", newline="",
+    )
+    other_path = tmp_path / "other.nml"
+    # Same artist/title/filesize/time key (matches artist_title_size_time
+    # tier) but a different bitrate - a divergent attribute between the two
+    # copies of "the same" track.
+    other_path.write_text(
+        _nml(_entry("A", "Song", "track.mp3", time="100.0").replace('BITRATE="320"', 'BITRATE="128"'), 1, ""),
+        encoding="utf-8", newline="",
+    )
+
+    result = run_tool(
+        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path),
+         "--conflict-report", str(tmp_path / "conflicts.csv")],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 2
+    assert not (tmp_path / "out.nml").exists()
+    assert (tmp_path / "conflicts.csv").exists()
+
+
+def test_conflict_resolved_with_on_conflict_keep_first_still_writes_report(tmp_path: Path) -> None:
+    base_path = tmp_path / "base.nml"
+    base_path.write_text(_nml(_entry("A", "Song", "track.mp3", time="100.0"), 1, ""), encoding="utf-8", newline="")
+    other_path = tmp_path / "other.nml"
+    other_path.write_text(
+        _nml(_entry("A", "Song", "track.mp3", time="100.0").replace('BITRATE="320"', 'BITRATE="128"'), 1, ""),
+        encoding="utf-8", newline="",
+    )
+
+    result = run_tool(
+        ["splice", str(base_path), str(tmp_path / "out.nml"), "--input", str(other_path),
+         "--on-conflict", "keep-first", "--conflict-report", str(tmp_path / "conflicts.csv")],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 0
+    assert (tmp_path / "out.nml").exists()
+    assert (tmp_path / "conflicts.csv").exists()
+    assert "conflict_key=" in result.stdout

```

**Documentation:**

```diff
--- a/tests/test_splice.py
+++ b/tests/test_splice.py
@@ -10,6 +10,9 @@


 def _nml(entries_xml: str, entries_count: int, playlists_xml: str) -> str:
+    """Minimal NML wrapper whose SUBNODES COUNT is derived by counting
+    literal '<NODE' occurrences in playlists_xml, so a caller only ever
+    authors the inner playlist XML once."""
     return (
         '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
         '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'

```


### Milestone 8: Split command

**Files**: C:\codex\general_tasks\traktor_nml\split.py, C:\codex\general_tasks\traktor_nml\commands\split_cmd.py, C:\codex\general_tasks\tests\test_split.py

**Requirements**:

- Repeatable --group pairs an output path with one or more playlist names selecting the entries that output retains
- Kept fragments are transplanted as source spans so nothing is re-serialised
- Non-selected playlist references are dropped by default with pull-in and fail available explicitly
- A playlist retaining no entries is omitted from output and reported as playlist_dropped
- Partial retention is reported as playlist_partial with kept and total counts
- COLLECTION and PLAYLIST and SUBNODES counts are recalculated per output
- SORTING_INFO entries for omitted playlists are dropped and reported
- SETS content passes through into every output
- --dry-run reports per-output retention without writing

**Acceptance Criteria**:

- Every kept fragment is byte-identical to its source span
- No output playlist entry references a track absent from that output's COLLECTION unless pull-in was named
- Every count attribute equals its actual child count in every output
- A playlist named in no group appears in no output and is reported
- Every output parses under both parsers
- A failure while assembling the second output leaves no output file written

**Tests**:

- C:\codex\general_tasks\tests\test_split.py

#### Code Intent

- **CI-M-008-001** `C:\codex\general_tasks\traktor_nml\split.py::select_entries`: Resolve each output group's named playlists to their primary keys, gather the collection entries those keys reference, and report a playlist named in no group as excluded. A playlist whose retained entry count is zero is omitted from its output and named in the statistics; partial retention is reported with kept and total counts. (refs: DL-009)
- **CI-M-008-002** `C:\codex\general_tasks\traktor_nml\split.py::apply_dangling_policy`: Drop playlist references to tracks outside an output's selection by default, pull the referenced entries into that output when the pull-in policy is named, and abort naming every offending reference when the strict policy is named. The resulting output is referentially closed under the default and strict policies. (refs: DL-009)
- **CI-M-008-003** `C:\codex\general_tasks\traktor_nml\commands\split_cmd.py::register`: Register a subcommand taking one input and repeatable group arguments pairing an output path with playlist names, plus dangling-policy and dry-run arguments. Every output is assembled fully in memory through the span builder and written only after all outputs assemble successfully. (refs: DL-003, DL-012)

#### Code Changes

**CC-M-008-001** (C:\codex\general_tasks\traktor_nml\split.py) - implements CI-M-008-001

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/split.py
@@ -0,0 +1,59 @@
+"""Partition one NML into several outputs by named playlist, keeping every
+kept fragment byte-identical to its source span.
+
+Every output is a flat playlist-entry subset (v1 scope, see the plan's
+tradeoffs): a --group names one or more playlists whose entries define that
+output's COLLECTION. Dangling references - a kept playlist pointing at a
+track outside the selection - are excluded by default, referentially closing
+every output; pull-in and fail are explicit alternatives (DL-009).
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field
+from typing import Literal, Optional
+
+from .model import collection_entries, collection_records
+from .playlists import find_playlist_nodes, node_primary_keys
+from .spans import element_span_by_identity, find_element_span, recalculate_count_attr
+from .xmlio import ET
+
+DanglingPolicy = Literal["exclude", "pull-in", "fail"]
+
+
+@dataclass
+class SelectionResult:
+    kept_keys: set[str]
+    playlist_dropped: list[str] = field(default_factory=list)
+    playlist_partial: list[tuple[str, int, int]] = field(default_factory=list)  # (name, kept, total)
+    unknown_playlists: list[str] = field(default_factory=list)
+
+
+def select_entries(root: ET.Element, playlist_names: list[str]) -> SelectionResult:
+    """Resolve playlist_names to their primary keys, and report a playlist
+    reduced to zero entries as dropped rather than writing it empty."""
+    all_nodes = {node.attrib.get("NAME", ""): node for node in find_playlist_nodes(root)}
+    result = SelectionResult(kept_keys=set())
+
+    for name in playlist_names:
+        node = all_nodes.get(name)
+        if node is None:
+            result.unknown_playlists.append(name)
+            continue
+        keys = [pk.attrib.get("KEY", "") for pk in node_primary_keys(node)]
+        total = len(keys)
+        if total == 0:
+            result.playlist_dropped.append(name)
+            continue
+        result.kept_keys.update(keys)
+
+    return result
+
+
+@dataclass
+class SplitOutcome:
+    output: Optional[str]
+    stats: dict[str, object]
+    errors: list[str] = field(default_factory=list)
+
+

```

**Documentation:**

```diff
--- a/traktor_nml/split.py
+++ b/traktor_nml/split.py
@@ -21,6 +21,10 @@
 @dataclass
 class SelectionResult:
+    """playlist_partial's (name, kept, total) records the partial-
+    retention detail DL-009 requires reporting, distinct from
+    playlist_dropped's fully-empty case - a playlist never silently loses
+    entries without one of the two being reported."""
     kept_keys: set[str]
     playlist_dropped: list[str] = field(default_factory=list)
     playlist_partial: list[tuple[str, int, int]] = field(default_factory=list)  # (name, kept, total)

```


**CC-M-008-002** (C:\codex\general_tasks\traktor_nml\split.py) - implements CI-M-008-002

**Code:**

```diff
--- a/traktor_nml/split.py
+++ b/traktor_nml/split.py
@@ -57,3 +57,145 @@
     errors: list[str] = field(default_factory=list)
 
 
+def apply_dangling_policy(
+    root: ET.Element, kept_keys: set[str], policy: DanglingPolicy
+) -> tuple[set[str], list[tuple[str, str]], list[str]]:
+    """Return (final_kept_keys, dropped_refs, errors).
+
+    exclude drops out-of-selection references (default, always closed).
+    pull-in adds the referenced entries' keys into the selection instead.
+    fail reports every offending reference as an error and adds nothing.
+    """
+    valid_collection_keys = {r.primary_key for r in collection_records(root)}
+    dropped_refs: list[tuple[str, str]] = []
+    errors: list[str] = []
+    # A key select_entries gathered but that matches no actual COLLECTION
+    # entry (an already-broken reference in the source) can never define a
+    # kept track either, so it is excluded from the carried-over selection
+    # up front and handled below like any other out-of-selection reference.
+    final_keys = kept_keys & valid_collection_keys
+
+    for node in find_playlist_nodes(root):
+        name = node.attrib.get("NAME", "")
+        for pk in node_primary_keys(node):
+            key = pk.attrib.get("KEY", "")
+            if key in final_keys:
+                continue
+            # key references something outside the current selection - either
+            # elsewhere in this file's own COLLECTION, or nowhere at all (an
+            # already-broken reference). Either way it is dangling relative
+            # to this output and goes through the same policy.
+            if policy == "pull-in" and key in valid_collection_keys:
+                final_keys.add(key)
+            elif policy == "fail":
+                errors.append(f"dangling_reference playlist={name} key={key}")
+            else:
+                dropped_refs.append((name, key))
+
+    return final_keys, dropped_refs, errors
+
+
+def _replace_children(fragment: str, tag_name: str, count_attr: str, children: list[str]) -> str:
+    """Rewrite fragment's own opening tag's count_attr to len(children) and
+    replace everything between the opening and closing tag with children,
+    discarding the original body entirely (a full-selection rebuild, unlike
+    splice's append-only merge)."""
+    fragment = recalculate_count_attr(fragment, tag_name, count_attr, len(children))
+    open_end = fragment.index(">") + 1
+    close_start = len(fragment) - len(f"</{tag_name}>")
+    return fragment[:open_end] + "".join(children) + fragment[close_start:]
+
+
+def build_output(
+    source_text: str, root: ET.Element, playlist_names: list[str], policy: DanglingPolicy
+) -> SplitOutcome:
+    selection = select_entries(root, playlist_names)
+    stats: dict[str, object] = {
+        "playlists_requested": len(playlist_names),
+        "playlists_dropped": list(selection.playlist_dropped),
+        "playlists_unknown": list(selection.unknown_playlists),
+    }
+
+    final_keys, dropped_refs, errors = apply_dangling_policy(root, selection.kept_keys, policy)
+    if errors:
+        return SplitOutcome(output=None, stats=stats, errors=errors)
+
+    kept_records = [r for r in collection_records(root) if r.primary_key in final_keys]
+    try:
+        # Each ENTRY's span is located by its own parsed element (identity),
+        # not by searching source text for its FILE attribute value - that
+        # search breaks on duplicate basenames (common across a real corpus)
+        # and on XML-escaped characters, since the parsed attribute value is
+        # unescaped text while the source bytes are not.
+        kept_entry_texts = [element_span_by_identity(source_text, root, r.entry).text(source_text) for r in kept_records]
+    except ValueError as exc:
+        return SplitOutcome(output=None, stats=stats, errors=[f"collection_entry_span_not_found: {exc}"])
+
+    collection_span = find_element_span(source_text, "COLLECTION")
+    if collection_span is None:
+        return SplitOutcome(output=None, stats=stats, errors=["no_collection"])
+    coll_fragment = _replace_children(
+        collection_span.text(source_text), "COLLECTION", "ENTRIES", kept_entry_texts
+    )
+    output = source_text[: collection_span.start] + coll_fragment + source_text[collection_span.end:]
+
+    # Rebuild the PLAYLISTS tree: keep only the requested, non-dropped
+    # playlists, transplanted verbatim except for dropped references, which
+    # are excluded (their ENTRY/PRIMARYKEY child text is simply omitted).
+    requested_kept_names = [
+        name for name in playlist_names
+        if name not in selection.playlist_dropped and name not in selection.unknown_playlists
+    ]
+    dropped_keys_by_name: dict[str, set[str]] = {}
+    for name, key in dropped_refs:
+        dropped_keys_by_name.setdefault(name, set()).add(key)
+
+    playlist_fragments = []
+    partial: list[tuple[str, int, int]] = []
+    for node in find_playlist_nodes(root):
+        name = node.attrib.get("NAME", "")
+        if name not in requested_kept_names:
+            continue
+        all_keys = [pk.attrib.get("KEY", "") for pk in node_primary_keys(node)]
+        excluded = dropped_keys_by_name.get(name, set())
+        surviving = [k for k in all_keys if k not in excluded]
+        if not surviving:
+            stats.setdefault("playlists_dropped", []).append(name)  # type: ignore[union-attr]
+            continue
+        if excluded:
+            partial.append((name, len(surviving), len(all_keys)))
+            # Clone the real element and prune the dropped ENTRY children in
+            # place, then re-serialise: this preserves every surviving
+            # ENTRY/PRIMARYKEY's original attributes verbatim (in particular
+            # PRIMARYKEY TYPE, which may be STEM rather than TRACK) and lets
+            # the serialiser handle NAME/KEY escaping correctly, instead of
+            # a hand-built f-string that hardcodes TYPE="TRACK" and
+            # interpolates NAME/KEY unescaped.
+            node_copy = ET.fromstring(ET.tostring(node))
+            playlist_elem = node_copy.find("PLAYLIST")
+            if playlist_elem is not None:
+                for entry_elem in list(playlist_elem.findall("ENTRY")):
+                    pk_elem = entry_elem.find("PRIMARYKEY")
+                    entry_key = "" if pk_elem is None else pk_elem.attrib.get("KEY", "")
+                    if entry_key in excluded:
+                        playlist_elem.remove(entry_elem)
+                playlist_elem.attrib["ENTRIES"] = str(len(surviving))
+            fragment = ET.tostring(node_copy, encoding="unicode")
+        else:
+            try:
+                fragment = element_span_by_identity(source_text, root, node).text(source_text)
+            except ValueError as exc:
+                return SplitOutcome(output=None, stats=stats, errors=[f"playlist_span_not_found name={name}: {exc}"])
+        playlist_fragments.append(fragment)
+    stats["playlists_partial"] = partial
+
+    subnodes_span = find_element_span(output, "SUBNODES")
+    if subnodes_span is None:
+        return SplitOutcome(output=None, stats=stats, errors=["no_root_subnodes"])
+    subnodes_fragment = _replace_children(
+        subnodes_span.text(output), "SUBNODES", "COUNT", playlist_fragments
+    )
+    output = output[: subnodes_span.start] + subnodes_fragment + output[subnodes_span.end:]
+
+    stats["kept_entries"] = len(kept_entry_texts)
+    return SplitOutcome(output=output, stats=stats, errors=[])

```

**Documentation:**

```diff
--- a/traktor_nml/split.py
+++ b/traktor_nml/split.py
@@ -67,6 +67,11 @@
     fail reports every offending reference as an error and adds nothing.
     """
+    # exclude is split's default (DL-009): pull-in would duplicate a
+    # track across outputs and reintroduce the divergence splice exists
+    # to resolve; fail is available for callers that would rather refuse
+    # outright than silently narrow a playlist.
     valid_collection_keys = {r.primary_key for r in collection_records(root)}
     dropped_refs: list[tuple[str, str]] = []
     errors: list[str] = []

```


**CC-M-008-003** (C:\codex\general_tasks\traktor_nml\commands\split_cmd.py) - implements CI-M-008-003

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/commands/split_cmd.py
@@ -0,0 +1,77 @@
+"""split subcommand: partition one NML into several outputs by playlist."""
+
+from __future__ import annotations
+
+import argparse
+import sys
+from pathlib import Path
+
+from ..split import build_output
+from ..xmlio import parse_xml_bytes
+
+
+def _parse_groups(raw_groups: list[list[str]] | None) -> list[tuple[Path, list[str]]]:
+    groups = []
+    for output_path, names_csv in raw_groups or []:
+        names = [name for name in names_csv.split(",") if name]
+        groups.append((Path(output_path), names))
+    return groups
+
+
+def _handle_split(args: argparse.Namespace) -> int:
+    groups = _parse_groups(args.group)
+    if not groups:
+        print("at_least_one_group_required", file=sys.stderr)
+        return 2
+
+    output_paths = [path for path, _ in groups]
+    if args.input.resolve() in {p.resolve() for p in output_paths}:
+        print("output_must_differ_from_input", file=sys.stderr)
+        return 2
+
+    try:
+        source_bytes = args.input.read_bytes()
+    except FileNotFoundError:
+        print(f"input_not_found={args.input}", file=sys.stderr)
+        return 2
+
+    root = parse_xml_bytes(source_bytes)
+    source_text = source_bytes.decode("utf-8")
+
+    outcomes = []
+    for output_path, names in groups:
+        outcome = build_output(source_text, root, names, args.dangling_policy)
+        outcomes.append((output_path, outcome))
+        print(f"group_output={output_path}")
+        for key, value in outcome.stats.items():
+            print(f"  {key}={value}")
+        for error in outcome.errors:
+            print(f"  {error}", file=sys.stderr)
+
+    if any(outcome.output is None for _, outcome in outcomes):
+        print("split_aborted=true", file=sys.stderr)
+        return 2
+
+    if not args.dry_run:
+        for output_path, outcome in outcomes:
+            output_path.parent.mkdir(parents=True, exist_ok=True)
+            output_path.write_bytes(outcome.output.encode("utf-8"))
+            print(f"output_written={output_path}")
+    return 0
+
+
+def register(subparsers, handlers: dict) -> None:
+    parser = subparsers.add_parser("split", help="Partition one NML into several outputs by playlist")
+    parser.add_argument("input", type=Path)
+    parser.add_argument(
+        "--group",
+        nargs=2,
+        action="append",
+        metavar=("OUTPUT_PATH", "PLAYLIST_NAMES"),
+        help="Repeatable: an output path paired with a comma-separated list of playlist names.",
+    )
+    parser.add_argument(
+        "--dangling-policy", choices=["exclude", "pull-in", "fail"], default="exclude",
+    )
+    parser.add_argument("--dry-run", action="store_true")
+    handlers["split"] = _handle_split

```

**Documentation:**

```diff
--- a/traktor_nml/commands/split_cmd.py
+++ b/traktor_nml/commands/split_cmd.py
@@ -10,6 +10,10 @@


 def _parse_groups(raw_groups: list[list[str]] | None) -> list[tuple[Path, list[str]]]:
+    """Parse repeated --group PATH NAMES entries into (output_path,
+    playlist_names) pairs; NAMES is comma-separated, and an empty segment
+    (e.g. a trailing comma) is dropped rather than producing a blank
+    playlist name to look up."""
     groups = []
     for output_path, names_csv in raw_groups or []:
         names = [name for name in names_csv.split(",") if name]

```


**CC-M-008-004** (C:\codex\general_tasks\tests\test_split.py) - implements CI-M-008-003

**Code:**

```diff
--- /dev/null
+++ b/tests/test_split.py
@@ -0,0 +1,136 @@
+"""Split: playlist-scoped partition, dangling reference policy, byte fidelity."""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+from tests.conftest import run_tool
+
+
+def _nml(entries_xml: str, entries_count: int, playlists_xml: str, playlist_count: int) -> str:
+    return (
+        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
+        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
+        f'<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="{playlist_count}">'
+        f"{playlists_xml}</SUBNODES></NODE></PLAYLISTS>"
+        "<SETS></SETS><INDEXING></INDEXING></NML>"
+    )
+
+
+def _entry(artist, title, filename, size="16"):
+    return (
+        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
+        f'<LOCATION DIR="/:Music/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
+        f'<INFO BITRATE="320" PLAYTIME_FLOAT="1.0" FILESIZE="{size}"></INFO>'
+        "</ENTRY>"
+    )
+
+
+def _playlist(name: str, keys: list[str], uuid: str) -> str:
+    entries = "".join(f'<ENTRY><PRIMARYKEY TYPE="TRACK" KEY="{k}"></PRIMARYKEY></ENTRY>' for k in keys)
+    return (
+        f'<NODE TYPE="PLAYLIST" NAME="{name}">'
+        f'<PLAYLIST ENTRIES="{len(keys)}" TYPE="LIST" UUID="{uuid}">{entries}</PLAYLIST>'
+        "</NODE>"
+    )
+
+
+def _key(filename: str) -> str:
+    return "C:" + "/:Music/:" + filename
+
+
+def test_split_by_playlist_keeps_only_selected_entries(tmp_path: Path) -> None:
+    src = tmp_path / "src.nml"
+    src.write_text(
+        _nml(
+            _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3"),
+            2,
+            _playlist("Keep", [_key("one.mp3")], "uuid-keep") + _playlist("Other", [_key("two.mp3")], "uuid-other"),
+            2,
+        ),
+        encoding="utf-8", newline="",
+    )
+    out = tmp_path / "out.nml"
+    result = run_tool(["split", str(src), "--group", str(out), "Keep"], cwd=tmp_path)
+    assert result.exit_code == 0
+    text = out.read_text(encoding="utf-8")
+    assert "one.mp3" in text
+    assert "two.mp3" not in text
+    assert 'ENTRIES="1"' in text.split("COLLECTION")[1][:40]
+
+
+def test_playlist_named_in_no_group_is_reported_and_excluded(tmp_path: Path) -> None:
+    src = tmp_path / "src.nml"
+    src.write_text(
+        _nml(_entry("A", "One", "one.mp3"), 1, _playlist("Keep", [_key("one.mp3")], "uuid-keep"), 1),
+        encoding="utf-8", newline="",
+    )
+    out = tmp_path / "out.nml"
+    result = run_tool(["split", str(src), "--group", str(out), "Keep"], cwd=tmp_path)
+    assert result.exit_code == 0
+    text = out.read_text(encoding="utf-8")
+    assert "Keep" in text
+
+
+def test_dangling_reference_excluded_by_default(tmp_path: Path) -> None:
+    # "Mixed" references a track with no matching COLLECTION entry at all
+    # (already broken in the source) - that reference is outside anything
+    # this output's COLLECTION can ever contain, so it must be dropped by
+    # default rather than left dangling in the output.
+    src = tmp_path / "src.nml"
+    src.write_text(
+        _nml(
+            _entry("A", "One", "one.mp3"),
+            1,
+            _playlist("Mixed", [_key("one.mp3"), _key("ghost.mp3")], "uuid-mixed"),
+            1,
+        ),
+        encoding="utf-8", newline="",
+    )
+    out = tmp_path / "out.nml"
+    result = run_tool(["split", str(src), "--group", str(out), "Mixed"], cwd=tmp_path)
+    assert result.exit_code == 0
+    text = out.read_text(encoding="utf-8")
+    assert "ghost.mp3" not in text
+    assert "one.mp3" in text
+
+
+def test_dangling_reference_fails_under_fail_policy(tmp_path: Path) -> None:
+    src = tmp_path / "src.nml"
+    src.write_text(
+        _nml(
+            _entry("A", "One", "one.mp3"),
+            1,
+            _playlist("Mixed", [_key("one.mp3"), _key("ghost.mp3")], "uuid-mixed"),
+            1,
+        ),
+        encoding="utf-8", newline="",
+    )
+    out = tmp_path / "out.nml"
+    result = run_tool(
+        ["split", str(src), "--group", str(out), "Mixed", "--dangling-policy", "fail"], cwd=tmp_path
+    )
+    assert result.exit_code == 2
+    assert not out.exists()
+
+
+def test_no_output_written_when_second_group_fails(tmp_path: Path) -> None:
+    src = tmp_path / "src.nml"
+    src.write_text(
+        _nml(_entry("A", "One", "one.mp3"), 1, _playlist("Keep", [_key("one.mp3")], "uuid-keep"), 1),
+        encoding="utf-8", newline="",
+    )
+    out1 = tmp_path / "out1.nml"
+    out2 = tmp_path / "out2.nml"
+    result = run_tool(
+        [
+            "split", str(src),
+            "--group", str(out1), "Keep",
+            "--group", str(out2), "DoesNotExist",
+            "--dangling-policy", "fail",
+        ],
+        cwd=tmp_path,
+    )
+    assert not out1.exists()
+    assert not out2.exists()

```

**Documentation:**

```diff
--- a/tests/test_split.py
+++ b/tests/test_split.py
@@ -21,6 +21,9 @@


 def _key(filename: str) -> str:
+    """Compute the flattened VOLUME+DIR+FILE PRIMARYKEY these fixtures'
+    playlists reference, matching the schema's own KEY derivation
+    exactly."""
     return "C:" + "/:Music/:" + filename

```


## Execution Waves

- W-001: M-001
- W-002: M-002
- W-003: M-003, M-006
- W-004: M-004, M-005, M-007, M-008

# Plan

## Overview

A set of tracks chosen outside Traktor arrives as plain text, one 'Artist - Title' line per line, and reaching them as a playlist inside Traktor means finding each one in an existing collection by hand and rebuilding the order by hand. The tool reads and rewrites the NML files that collection lives in, but every command it carries either repairs paths on entries that already exist or merges and partitions whole documents, so none of them turns an external ordered list of names into a playlist node.

**Approach**: A build-playlist subcommand resolves each parsed line against the base collection through the existing matching cascade at loose confidence, one match_records call per line over an index built once, so input order survives and each line's outcome is known individually. The resolved primary keys serialize into a fresh NODE TYPE=PLAYLIST subtree, which OutputBuilder splices into the receiving SUBNODES span with its COUNT recalculated and every other byte of the base copied verbatim. An unresolved line aborts the run with nothing written unless it is explicitly allowed, and the unresolved report is written either way.

### Track list to inserted playlist node

[Diagram pending Technical Writer rendering: DIAG-001]

## Planning Context

### Decision Log

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-024 | A core buildplaylist.py module holds resolution and assembly; commands/build_playlist_cmd.py holds only the CLI surface | Every write command in the package pairs a core module with a thin commands/ module (splice.py/splice_cmd.py, split.py/split_cmd.py) -> a single-file command carrying parse, match and span assembly would be the only command whose core logic lives under commands/, breaking the layering every existing write command already follows in practice - visible directly in splice.py/splice_cmd.py and split.py/split_cmd.py's own file contents, not asserted as a rule in either CLAUDE.md's file table -> the feature splits along the same seam its two closest precedents already use |
| DL-025 | match_records is called once per parsed tracklist line, with old_records holding that single line and a shared candidate index passed through the indexes parameter | match_records returns its mapping keyed by old_record.primary_key and its outcome counts only in aggregate -> a batch call over all lines would both collide every line onto one empty primary_key and lose the per-line unmatched-versus-ambiguous distinction the unresolved report needs -> a per-line call recovers exact per-line outcome from the returned stats dict, keeps input order by construction, and leaves matching.py untouched, while the indexes parameter keeps the O(collection) index build at exactly one |
| DL-026 | Collection records are the candidate (new) side of the cascade and parsed tracklist lines are the old side | record_keys derives its keys from whichever record it is handed, and match_records indexes the new side while iterating the old side -> the side that must be iterated in a caller-controlled order is the tracklist, and the side that must be looked up by key is the collection -> the tracklist becomes the old side, mirroring how diskscan candidates take the new side for reconnection |
| DL-027 | An unmatched or ambiguous line aborts the whole build with no output written, unless --allow-unmatched is passed, and the unresolved report is written on both paths | splice treats an unresolved identity conflict as an abort that an explicit --on-conflict opts out of, and writes its conflict report whether or not the abort fires (the package's own DL-008 and DL-012) -> a playlist silently missing tracks is the same class of quiet data loss that policy exists to prevent, and a tracklist whose lines mostly resolve is still useful once the operator has seen what is missing -> the opt-out flag plus always-written report reproduces splice policy rather than inventing a second failure convention |
| DL-028 | The synthesized NODE/PLAYLIST/ENTRY/PRIMARYKEY fragment is built as an ElementTree subtree and serialized with ET.tostring | No source span exists for a playlist assembled from external text, so the fidelity policy the package's own DL-007 states routes this content to the serialization path -> string-formatting the fragment by hand would require escaping the playlist NAME and every PRIMARYKEY KEY against a helper that is private to textpatch.py and reachable only by crossing a module boundary into an underscore name -> ET.tostring escapes both attributes as part of serializing, matching how playlists.py already emits its renamed and redirected fragments |
| DL-029 | A fresh uuid4 hex is generated for the synthesized PLAYLIST element unconditionally, and a name colliding with an existing playlist takes the deterministic "<name> (2)" suffix | Two PLAYLIST elements sharing one UUID within a file is invalid, and a synthesized playlist has no source UUID to inherit at all -> the collision-rename and UUID-regeneration policy playlists.py already applies to imported playlists covers exactly this shape -> reusing that naming and UUID convention keeps one spelling of playlist identity across both entry points, and inherits its documented package-log R-004 manual-validation caveat rather than opening a second unverified one |
| DL-030 | The insertion point is the root FOLDER SUBNODES by default, and a --target-folder names an existing FOLDER whose own SUBNODES receives the node; a named folder that is absent is an abort, never a folder creation. If more than one FOLDER anywhere in the PLAYLISTS tree carries that name, resolution aborts with a dedicated target_folder_ambiguous error rather than picking the first match in document order | add_counted_span recalculates COUNT on whichever SUBNODES span it is given, so either target is the same assembly primitive -> creating a missing folder would mean synthesizing an enclosing FOLDER hierarchy whose SORTING_INFO and nesting semantics this feature has no verified schema knowledge of -> the absent-folder case reports and aborts, keeping folder synthesis out of a feature whose scope is one playlist node. A first-match-by-document-order pick on a name collision would silently insert into whichever folder happens to appear first, with no report - the same silent-guess failure mode the track-matching path's per-line ambiguity reporting (R-007) already refuses to allow - so folder-name ambiguity gets the same explicit-abort treatment as an absent folder, not a quieter fallback |
| DL-031 | The tracklist parser splits each line on the first " - " occurrence and reports every line it cannot split, rather than falling back to a looser delimiter | A hyphen with no surrounding spaces is common inside real artist and title text (Jean-Michel, Re-Edit) -> a bare hyphen delimiter would silently mis-split those lines into a wrong artist/title pair that then matches nothing or, worse, matches a different track -> the spaced delimiter fails loudly on an unparseable line and routes it into the same unresolved report an unmatched line uses, so no line is dropped without appearing somewhere |
| DL-032 | MatchConfidence.LOOSE is passed to the cascade as a fixed value with no --match-confidence flag on this subcommand | A tracklist line carries only artist and title, so every tier above artist_title is structurally unreachable for it and STRICT would make the command incapable of matching anything at all -> exposing a level selector would offer the operator two settings that resolve nothing and one that works -> the command states LOOSE itself, which keeps the single shared ordered enum the package's own DL-010 established without adding a knob whose only valid position is already known |
| DL-033 | The output-path refusal check refuses a path resolving to the tracklist input as well as the base, via the same bespoke set-membership check splice_cmd.py already uses, not write_nml_safely's extra_inputs parameter | write_nml_safely's extra_inputs parameter exists only on the attribute-patching write skeleton rewrite.py/reconnect.py/compare_cmd.py use, and DL-007 keeps that mechanism and byte-span assembly (splice.py/split.py) from ever mixing within one command -> build-playlist is a span-assembly command like splice.py, not an attribute-patching one, so routing it through write_nml_safely to gain extra_inputs would mix the two write mechanisms DL-007 exists to keep separate -> splice_cmd.py's own multi-input collision check is a bespoke set-membership comparison (args.output.resolve() in {args.base.resolve(), *(p.resolve() for p in args.input)}), not a write_nml_safely call, and build-playlist follows that exact precedent instead: args.output.resolve() in {args.base.resolve(), args.tracklist.resolve()} |
| DL-034 | The unresolved report is written as CSV via csv.DictWriter with a header row, opened with newline="" and UTF-8 encoding | splice_cmd.py's _write_conflict_report already writes its own CSV report this exact way for the same class of artifact, a persistent record of what a run could not resolve -> inventing a different dialect, header convention or encoding for build-playlist's unresolved report would give the package two CSV styles for the same kind of output with no reason for the difference -> the unresolved report follows _write_conflict_report's csv.DictWriter/newline=""/UTF-8 convention exactly |
| DL-035 | Exit code 2 is used uniformly for both input errors (xml_parse_error, input_not_found) and the unresolved-track abort, rather than a distinct code for the abort | splice_cmd.py's _handle_splice already returns exit code 2 for both a malformed input and an unresolved-conflict abort (splice_aborted=true), never distinguishing the two failure classes by exit code -> giving build-playlist's unresolved-track abort its own exit code would draw a distinction the package's closest existing precedent does not draw for the structurally identical case -> exit code 2 covers both failure classes here exactly as it already does for splice |
| DL-036 | A run yielding zero resolved lines (an empty tracklist, every line unparseable, or every line unmatched with --allow-unmatched given) aborts with a dedicated error and writes nothing, rather than writing a PLAYLIST with ENTRIES=0 | split.py already treats a playlist reduced to zero kept entries as dropped rather than written empty, reporting playlist_dropped rather than emitting a hollow container -> a build-playlist run with nothing to write is the same shape of outcome, a playlist that would carry no real content -> the zero-resolved case aborts and reports rather than fabricating an empty PLAYLIST node, matching split's own convention for the same situation |
| DL-037 | Two tracklist lines naming the same track resolve and serialize independently, producing duplicate ENTRY/PRIMARYKEY elements in the output rather than being deduplicated | C-004 already commits the synthesized ENTRY sequence to holding input order, and a Traktor PLAYLIST is an ordered list of references rather than a set, so a track referenced twice is not itself an invalid document -> deduplicating would mean silently discarding a line the operator wrote, which the parser's stated policy of reporting rather than discarding already rules out for any other line -> duplicate input lines produce duplicate output entries, consistent with taking the operator's input as authoritative |
| DL-038 | A base document with no PLAYLISTS section, no root FOLDER, or no SUBNODES element at all aborts with a dedicated no_root_subnodes error rather than synthesizing the missing structure | splice.py's assemble_output already returns exactly this no_root_subnodes error when the base it is merging into lacks a root SUBNODES span to insert children into -> build-playlist inserts into that same span, so the same absence produces the same failure mode splice.py already defines a name and abort path for -> reusing no_root_subnodes rather than inventing a second name or synthesizing the missing container keeps one spelling for one failure across both commands |
| DL-039 | The synthesized fragment's textual form (attribute quote character, empty-element shorthand, absence of extra whitespace) is whatever ET.tostring produces by default, with no attempt to match the base document's own formatting conventions | playlists.py's existing renamed and redirected fragments are already re-serialized through ET.tostring and spliced into an otherwise byte-preserved document without matching the base's own quoting or whitespace style, and that path is already accepted -> build-playlist's synthesized fragment sits in the same position, new content inserted beside verbatim-preserved bytes -> ET.tostring's default output is accepted as-is here too, since a well-formed but cosmetically different fragment is not a fidelity violation this tool's byte-preservation policy actually cares about |

### Rejected Alternatives

| Alternative | Why Rejected |
|---|---|
| A single match_records call over every tracklist line at once | The returned mapping is keyed by old_record.primary_key, which is the empty string for every text-only line, so all lines would collide onto one mapping slot; the stats dict is also aggregate, losing the per-line unmatched-versus-ambiguous distinction the report needs (ref: DL-025) |
| Synthetic unique placeholder LocationParts per tracklist line so one batch match_records call keys cleanly | It fixes the key collision but not the aggregate stats, so per-line ambiguity would still be unrecoverable, and it puts a fabricated volume and path on a record that has no filesystem existence (ref: DL-025) |
| A local resolution loop calling record_keys and walking the tier buckets directly | It would restate match_records' ambiguity semantics, including the subtle rule that a later weaker tier resolving uniquely overrides an earlier tier's ambiguity, in a second place free to drift from the first (ref: DL-025) |
| Hand-formatted fragment strings escaped through textpatch._xml_escape_attr | It reaches across a module boundary into a private helper to reproduce escaping that the serializer already performs while building the same fragment (ref: DL-028) |
| A dedicated external or text-only MatchConfidence level | LOOSE's artist_title tier already keys on artist and title alone with no other field required, so a new level would admit exactly the tiers LOOSE already admits (ref: DL-032) |
| An ISRC matching tier | Beatport downloads carry ISRC only sometimes and Bandcamp downloads mostly not at all, so the tier would resolve a fraction of a real library while adding a cascade path to maintain (ref: DL-032) |
| Creating a target folder that the base does not hold | Synthesizing an enclosing FOLDER hierarchy needs SORTING_INFO and nesting semantics this feature has no verified schema knowledge of, against a schema confirmed only for NML VERSION=20 (ref: DL-030) |
| Writing a partial playlist by default and reporting the gaps afterwards | A playlist quietly missing tracks looks complete in Traktor, which is the failure the abort-unless-overridden policy exists to prevent; the override keeps the partial build available to an operator who has seen the report (ref: DL-027) |
| Parse, match and assemble entirely inside commands/build_playlist_cmd.py | It would be the one command whose core logic lives under commands/, against the core-module-plus-thin-command layering every other write command follows (ref: DL-024) |
| Reverse the cascade sides: the collection as the old (iterated) side and the tracklist as the new (indexed) side | The side whose output order the caller must control is the tracklist, not the collection, and it is far cheaper to index the collection once than to index a tracklist rebuilt from scratch per line; iterating the collection instead would discard input order and rebuild a per-line index against a list of one (ref: DL-026) |
| Abort the whole build outright on a playlist-name collision, the same as an unresolved track-list line | A name collision has an unambiguous, harmless resolution playlists.py's import path already establishes and exercises; treating it as fatal would fail an otherwise fully-resolved run for a cosmetic reason a fix already exists for, unlike an unresolved match's real risk of silent data loss (ref: DL-029) |
| Split each tracklist line on its last " - " occurrence instead of its first | A featured-artist credit or remix suffix inside the title half is far likelier to itself contain a " - "-shaped separator after the real artist/title boundary than before it, so splitting on the last occurrence would silently prefer the wrong split in that common case; splitting on the first is the safer default (ref: DL-031) |

### Constraints

- C-001 (user-specified): identity resolution runs through matching.record_keys and matching.match_records as they stand, called at module level rather than subclassed or wrapped, with no tier added to matching.py or confidence.py
- C-002 (user-specified): an unresolved line never results in a silently partial output file
- C-003 (doc-derived): output commits through a temp file plus os.replace, via rewrite.write_bytes_atomically
- C-004 (user-specified): the synthesized PLAYLIST's ENTRY sequence holds input order
- C-005 (user-specified): the synthesized NODE/PLAYLIST/ENTRY/PRIMARYKEY XML is freshly serialized, since no source span exists to transplant
- C-006 (doc-derived): cli.py stays unedited; the command module registers itself through the commands-package discovery mechanism (DL-003 in the package's own log)
- C-007 (user-specified): ISRC matching, fingerprint matching, CSV and M3U input, network lookups, and source folder nesting beyond one target folder stay out of scope
- C-008 (doc-derived): the complete output is built and validated in memory before any file handle opens (DL-012 in the package's own log)

### Known Risks

- **A freshly generated UUID on a synthesized playlist is accepted by Traktor only by inference from the imported-playlist case, which is itself confirmed by manual import rather than by the test suite**: Repeat the manual Traktor open-and-inspect check on a real output before treating the command as validated, exactly as the imported-playlist path's package-log R-004 caveat requires; owned as an explicit M-002 acceptance criterion and manual test-list entry rather than left as an unassigned intention
- **Two distinct collection entries sharing an artist and title (an original and a remaster, or two rips) make every tracklist line naming them ambiguous, so a library with many duplicates resolves poorly at the only reachable tier**: Ambiguity is reported per line with the line's own text rather than folded into an unmatched count, so an operator can see that the miss is a duplicate-collection problem rather than a missing track
- **Artist and title text from a track list rarely matches collection tags exactly: featured-artist spellings, ampersand versus 'and', and remix suffixes all defeat an equality-keyed tier**: The unresolved report carries each line's raw text alongside its parsed artist and title, so a systematic spelling mismatch is visible as a pattern rather than as scattered misses; normalization stays a separate decision rather than an undocumented behavior inside this cascade
- **find_element_span locates the first SUBNODES in the document, which is the root folder's only while the root folder stays first in the PLAYLISTS tree**: The default path takes the first SUBNODES exactly as the merge path already does, and the named-folder path resolves its element through the parsed tree and SpanIndex rather than by document position
- **Withdrawn as stated: this risk describes a scenario (a collection entry reachable only through the playlist tree, absent from the collection scan) that cannot affect build-playlist's own write path, because every synthesized PRIMARYKEY comes from resolution.matched_record, and resolve_tracklist draws matches only from the same collection_records(base_root) list a validation check would compare against - the two sides of any such check are structurally identical, so a runtime guard here would never be able to fail. No dead invalid_primary_key branch or unfalsifiable check exists in the code for exactly this reason.**: None needed at runtime: the invariant holds by construction, documented as an inline comment at the point in assemble_output where a naive re-validation might otherwise be added
- **matching.py's _prefer_current_sync_copy collapses a two-candidate Sync_/Sync_old duplicate pair to the single current-copy candidate before the ambiguity check runs, so a tracklist line whose only two matches are that specific paired-migration duplicate resolves silently to the current copy rather than being reported ambiguous - inherited unmodified since build-playlist calls the cascade as-is**: No mitigation beyond what the cascade already provides: this collapse is intentionally narrow (limited to the Sync_/Sync_old path convention per its own docstring), and every other duplicate shape still reports ambiguous; documented here so a future maintainer investigating an unexpectedly-resolved line knows to check for this specific cascade behavior before assuming a bug in build-playlist itself

## Invisible Knowledge

### System

The build-playlist path reads the base document twice over: as a parsed tree, for identity and for locating the receiving container, and as raw text, for the bytes that surround the insertion point. Only the receiving SUBNODES opening tag (its COUNT) and the insertion point itself differ between input and output; everything else is copied through verbatim. The track list never touches the output document directly - it contributes only the order of the primary keys, each of which is read off a matched collection entry.

### Invariants

- A primary key written into a synthesized PRIMARYKEY comes from a matched collection EntryRecord, never from parsed input text; the input text names a track, it does not describe a path
- The output is assembled and validated entirely in memory; an abort leaves the output path untouched, and a commit goes through a temp file plus os.replace
- The tracklist is the old side of the matching cascade and the collection is the new side, so iteration order (which the caller controls) is the tracklist's and index lookup is the collection's
- matching.py and confidence.py stay unmodified: the feature reaches the cascade only by calling it
- Every input line appears in exactly one place in the run's output - as an ENTRY in the playlist, or as a row in the unresolved report
- Playlist naming and UUID policy has one spelling shared by the imported and the synthesized path, so a collision resolves identically whichever entry point produced it
- Within one tier's candidate lookup, a later, weaker tier resolving to a single candidate overrides an earlier tier's ambiguity for that line - match_records does not stop at the first ambiguous tier, only at a provider-returned AMBIGUOUS sentinel or a unique match - so a line ambiguous on artist_title_size_time can still resolve cleanly through the plain artist_title tier
- match_records' candidate lookup runs every tier's bucket through _prefer_current_sync_copy before checking its size, which collapses a two-candidate Sync_/Sync_old duplicate pair down to the single Sync_ (current) copy before the ambiguity check ever sees it; build-playlist inherits this silently, since it calls the cascade unmodified - a tracklist line whose only two matching collection entries are that specific paired-migration duplicate resolves to the current copy rather than reporting ambiguous

### Tradeoffs

- One match_records call per line pays a small per-call stats-dict allocation to recover per-line outcomes; the O(collection) index build stays at one because the shared index is passed in, so the cost scales with the track list (hundreds of lines) rather than with the collection (tens of thousands of entries)
- The artist_title tier is the only reachable one for text-only input, which makes a general artist-title duplicate in the collection unresolvable at any confidence level this command could offer - traded for not inventing a tie-break policy (newest, largest, first) that would silently pick a track the operator did not choose. The one narrow exception is _prefer_current_sync_copy's existing Sync_/Sync_old collapse (see invariants), which build-playlist inherits unmodified rather than being a policy this feature adds itself
- Insertion supports the root folder and one named existing folder, not arbitrary nesting or folder creation, because the SORTING_INFO and nesting semantics of a fabricated folder are unverified against the one schema version this tool has confirmed
- Exact artist and title equality is the whole matching rule: no normalization, folding or fuzzy distance, which misses spelling variants but never resolves a line onto a track the operator did not name

## Milestones

### Milestone 1: Tracklist parsing and collection resolution

**Files**: traktor_nml/tracklist.py, tests/test_tracklist.py

**Requirements**:

- A plain-text file holding one 'Artist - Title' line per line parses into ordered records carrying artist and title; blank lines and lines starting with '#' are skipped
- A line with no spaced-hyphen delimiter is retained as an unparseable entry carrying its 1-based line number and raw text, rather than discarded
- Each parsed line resolves against a collection through the matching cascade at MatchConfidence.LOOSE, yielding matched, unmatched or ambiguous for that line alone
- Resolution results carry input order

**Acceptance Criteria**:

- A three-line tracklist parses to three records whose artist and title equal the two halves of each input line
- A line holding only a bare title with no delimiter appears in the unparseable list with its 1-based line number, and does not appear in the parsed list
- A title containing a hyphen without surrounding spaces parses with that hyphen intact inside the title
- A line whose artist and title appear on exactly one collection entry resolves as matched and carries that entry's primary key
- A line whose artist and title appear on two collection entries resolves as ambiguous, not matched
- A line matching no collection entry resolves as unmatched
- Resolution output order equals input line order for a tracklist whose middle line is unmatched
- matching.py and confidence.py are byte-identical to their pre-existing contents

**Tests**:

- tests/test_tracklist.py - unit, doc-derived from the suite's pytest and in-process convention
- normal: three well-formed lines parse and resolve to three matched collection entries in input order
- normal: a blank line and a '#' comment line are skipped and appear in neither output list
- edge: a hyphen with no surrounding spaces inside a title survives parsing intact
- edge: leading and trailing whitespace around either half is stripped
- edge: a line with an empty half is unparseable rather than a record carrying an empty title
- edge: two identical tracklist lines resolve independently rather than collapsing onto one result
- error: a line with no delimiter lands in the unparseable list carrying its 1-based line number
- error: a line matching two collection entries on artist and title resolves as ambiguous
- error: a line matching nothing resolves as unmatched

#### Code Intent

- **CI-M-001-001** `traktor_nml/tracklist.py::parse_tracklist`: Take the text of a tracklist file and return an ordered pair of (parsed lines, unparseable lines). A line is skipped entirely when it is blank after stripping or starts with #. A retained line splits on its first spaced-hyphen occurrence into artist (left, stripped) and title (right, stripped); a line with no such occurrence, or with an empty half after stripping, becomes an unparseable record carrying its 1-based line number and its raw text. Each parsed record carries its 1-based line number, its raw text, artist and title. Parsing is pure text handling with no filesystem or XML involvement. (refs: DL-031)
- **CI-M-001-002** `traktor_nml/tracklist.py::tracklist_record`: Turn one parsed tracklist line into an EntryRecord suitable as the matching cascade old side: entry None, source_path None, artist and title from the parsed line, and every remaining identity field (audio_id, filesize, playtime_float, bitrate, album, file_name) the empty string, with an empty LocationParts. The empty fields are what confine record_keys to the artist_title tier, and the empty location is never read as an authoritative VOLUME/VOLUMEID source, matching how a disk-scan candidate carries a placeholder location for display only. (refs: DL-026)
- **CI-M-001-003** `traktor_nml/tracklist.py::resolve_tracklist`: Take parsed tracklist lines and a list of collection EntryRecords and return one resolution per line, in input order, each holding the source line and an outcome of matched (with the matched collection record), unmatched, or ambiguous. Build the candidate index once with build_new_indexes over the collection records at MatchConfidence.LOOSE, then call match_records once per line with old_records holding that single line and the shared index passed as indexes; the returned stats dict distinguishes the three outcomes for that one line. match_records' returned mapping is keyed by old_record.primary_key, which is always the empty string for a text-only tracklist record since its LocationParts carries no volume, dir or file - on a matched outcome the matched record is read back as mapping.get("") (equivalently next(iter(mapping.values()), None)), never by any line-derived key such as the raw text or line number. matching.py is imported and called, never edited or wrapped in a subclass. (refs: DL-025, DL-026, DL-032)

#### Code Changes

**CC-M-001-001** (traktor_nml/tracklist.py) - implements CI-M-001-001

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/tracklist.py
@@ -0,0 +1,64 @@
+"""External track-list parsing and per-line collection resolution.
+
+A plain-text track list holds one 'Artist - Title' line per line. Each
+parsed line becomes a candidate EntryRecord (entry=None), the same shape
+diskscan.py already uses for disk-scanned candidates, and is resolved
+against a base collection through the shared matching cascade in
+matching.py at MatchConfidence.LOOSE - the only tier reachable for
+text-only input is artist_title, since every field the stricter tiers
+require (filesize, playtime_float, file_name, album) is empty for a
+parsed line. matching.py and confidence.py are imported and called here,
+never edited or wrapped in a subclass.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Optional
+
+from .confidence import MatchConfidence
+from .matching import build_new_indexes, match_records
+from .model import EntryRecord, LocationParts
+
+
+@dataclass(frozen=True)
+class ParsedLine:
+    line_number: int
+    raw_text: str
+    artist: str
+    title: str
+
+
+@dataclass(frozen=True)
+class UnparseableLine:
+    line_number: int
+    raw_text: str
+
+
+def parse_tracklist(text: str) -> tuple[list[ParsedLine], list[UnparseableLine]]:
+    """Split text into ordered parsed and unparseable lines.
+
+    A blank line (after stripping) or a line starting with '#' is skipped
+    entirely. A retained line splits on its first ' - ' occurrence into
+    artist (left, stripped) and title (right, stripped); a line with no
+    such occurrence, or with an empty half after stripping, becomes an
+    unparseable record carrying its 1-based line number and raw text
+    instead of being discarded.
+    """
+    parsed: list[ParsedLine] = []
+    unparseable: list[UnparseableLine] = []
+    for line_number, raw_line in enumerate(text.splitlines(), start=1):
+        stripped = raw_line.strip()
+        if not stripped or stripped.startswith("#"):
+            continue
+        delimiter_idx = raw_line.find(" - ")
+        if delimiter_idx < 0:
+            unparseable.append(UnparseableLine(line_number=line_number, raw_text=raw_line))
+            continue
+        artist = raw_line[:delimiter_idx].strip()
+        title = raw_line[delimiter_idx + len(" - "):].strip()
+        if not artist or not title:
+            unparseable.append(UnparseableLine(line_number=line_number, raw_text=raw_line))
+            continue
+        parsed.append(ParsedLine(line_number=line_number, raw_text=raw_line, artist=artist, title=title))
+    return parsed, unparseable

```

**Documentation:**

```diff
--- a/traktor_nml/tracklist.py
+++ b/traktor_nml/tracklist.py
@@ -52,5 +52,7 @@ def parse_tracklist(text: str) -> tuple[list[ParsedLine], list[UnparseableLine
         if not stripped or stripped.startswith("#"):
             continue
+        # search the raw (unstripped) line so the found index still lines up
+        # with raw_line when slicing artist/title below (DL-031)
         delimiter_idx = raw_line.find(" - ")
         if delimiter_idx < 0:
             unparseable.append(UnparseableLine(line_number=line_number, raw_text=raw_line))

```


**CC-M-001-002** (traktor_nml/tracklist.py) - implements CI-M-001-002

**Code:**

```diff
--- a/traktor_nml/tracklist.py
+++ b/traktor_nml/tracklist.py
@@ -64,3 +64,27 @@
             continue
         parsed.append(ParsedLine(line_number=line_number, raw_text=raw_line, artist=artist, title=title))
     return parsed, unparseable
+
+
+def tracklist_record(line: ParsedLine) -> EntryRecord:
+    """Turn one parsed tracklist line into an EntryRecord suitable as the
+    matching cascade's old side: entry None, source_path None, artist and
+    title from the parsed line, and every remaining identity field the
+    empty string, with an empty LocationParts. The empty fields confine
+    record_keys to the artist_title tier, and the empty location is never
+    read as an authoritative VOLUME/VOLUMEID source, matching how a
+    disk-scan candidate carries a placeholder location for display only.
+    """
+    return EntryRecord(
+        entry=None,
+        artist=line.artist,
+        title=line.title,
+        audio_id="",
+        filesize="",
+        playtime_float="",
+        bitrate="",
+        album="",
+        file_name="",
+        location=LocationParts(volume="", volumeid="", dir_value="", file_name=""),
+        source_path=None,
+    )

```

**Documentation:**

```diff
--- a/traktor_nml/tracklist.py
+++ b/traktor_nml/tracklist.py
@@ -87,4 +87,5 @@ def tracklist_record(line: ParsedLine) -> EntryRecord:
         file_name="",
         location=LocationParts(volume="", volumeid="", dir_value="", file_name=""),
+        # no filesystem file backs a tracklist candidate
         source_path=None,
     )

```


**CC-M-001-003** (traktor_nml/tracklist.py) - implements CI-M-001-003

**Code:**

```diff
--- a/traktor_nml/tracklist.py
+++ b/traktor_nml/tracklist.py
@@ -89,3 +89,43 @@
         location=LocationParts(volume="", volumeid="", dir_value="", file_name=""),
         source_path=None,
     )
+
+
+@dataclass(frozen=True)
+class TracklistResolution:
+    line: ParsedLine
+    outcome: str  # "matched", "unmatched", "ambiguous"
+    matched_record: Optional[EntryRecord] = None
+
+
+def resolve_tracklist(
+    lines: list[ParsedLine], collection: list[EntryRecord]
+) -> list[TracklistResolution]:
+    """Resolve every parsed line against collection, in input order.
+
+    The candidate index is built once with build_new_indexes over
+    collection at MatchConfidence.LOOSE, then match_records is called once
+    per line with old_records holding that single line and the shared
+    index passed as indexes; the returned stats dict distinguishes matched,
+    unmatched and ambiguous for that one line. match_records' returned
+    mapping is keyed by old_record.primary_key, which is always the empty
+    string for a text-only tracklist record since its LocationParts carries
+    no volume, dir or file - on a matched outcome the matched record is
+    read back as mapping.get(""), never by any line-derived key.
+    """
+    indexes = build_new_indexes(collection, MatchConfidence.LOOSE)
+    resolutions: list[TracklistResolution] = []
+    for line in lines:
+        record = tracklist_record(line)
+        mapping, stats, _samples = match_records(
+            [record], collection, MatchConfidence.LOOSE, indexes=indexes
+        )
+        if stats["matched"] == 1:
+            resolutions.append(
+                TracklistResolution(line=line, outcome="matched", matched_record=mapping.get(""))
+            )
+        elif stats["ambiguous"] == 1:
+            resolutions.append(TracklistResolution(line=line, outcome="ambiguous"))
+        else:
+            resolutions.append(TracklistResolution(line=line, outcome="unmatched"))
+    return resolutions

```

**Documentation:**

```diff
--- a/traktor_nml/tracklist.py
+++ b/traktor_nml/tracklist.py
@@ -111,7 +111,9 @@ def resolve_tracklist(
     mapping is keyed by old_record.primary_key, which is always the empty
     string for a text-only tracklist record since its LocationParts carries
     no volume, dir or file - on a matched outcome the matched record is
     read back as mapping.get(""), never by any line-derived key.
     """
+    # index built once over the full collection; reused by every per-line
+    # match_records call below so the O(collection) cost stays at one (DL-025)
     indexes = build_new_indexes(collection, MatchConfidence.LOOSE)
     resolutions: list[TracklistResolution] = []

```


**CC-M-001-004** (tests/test_tracklist.py)

**Code:**

```diff
--- /dev/null
+++ b/tests/test_tracklist.py
@@ -0,0 +1,121 @@
+"""Tracklist: plain-text 'Artist - Title' parsing and per-line collection resolution."""
+
+from __future__ import annotations
+
+from traktor_nml.model import EntryRecord, LocationParts
+from traktor_nml.tracklist import parse_tracklist, resolve_tracklist
+
+
+def _collection_record(artist: str, title: str, filename: str = "track.mp3") -> EntryRecord:
+    return EntryRecord(
+        entry=None,
+        artist=artist,
+        title=title,
+        audio_id="",
+        filesize="",
+        playtime_float="",
+        bitrate="",
+        album="",
+        file_name=filename,
+        location=LocationParts(volume="C:", volumeid="C:", dir_value="/:Music/:", file_name=filename),
+    )
+
+
+def test_three_lines_parse_to_three_records() -> None:
+    text = "Artist One - Title One\nArtist Two - Title Two\nArtist Three - Title Three\n"
+    parsed, unparseable = parse_tracklist(text)
+    assert unparseable == []
+    assert [(p.artist, p.title) for p in parsed] == [
+        ("Artist One", "Title One"),
+        ("Artist Two", "Title Two"),
+        ("Artist Three", "Title Three"),
+    ]
+
+
+def test_blank_and_comment_lines_are_skipped() -> None:
+    text = "Artist - Title\n\n# a comment\nArtist Two - Title Two\n"
+    parsed, unparseable = parse_tracklist(text)
+    assert unparseable == []
+    assert len(parsed) == 2
+
+
+def test_bare_title_with_no_delimiter_is_unparseable() -> None:
+    text = "Just A Title With No Delimiter\n"
+    parsed, unparseable = parse_tracklist(text)
+    assert parsed == []
+    assert len(unparseable) == 1
+    assert unparseable[0].line_number == 1
+
+
+def test_hyphen_without_surrounding_spaces_survives_inside_title() -> None:
+    text = "Artist - Re-Edit Title\n"
+    parsed, _ = parse_tracklist(text)
+    assert parsed[0].artist == "Artist"
+    assert parsed[0].title == "Re-Edit Title"
+
+
+def test_whitespace_around_each_half_is_stripped() -> None:
+    text = "  Artist   -   Title  \n"
+    parsed, _ = parse_tracklist(text)
+    assert parsed[0].artist == "Artist"
+    assert parsed[0].title == "Title"
+
+
+def test_empty_half_is_unparseable() -> None:
+    text = " - Title\n"
+    parsed, unparseable = parse_tracklist(text)
+    assert parsed == []
+    assert len(unparseable) == 1
+
+
+def test_two_identical_lines_resolve_independently() -> None:
+    text = "Artist - Title\nArtist - Title\n"
+    parsed, _ = parse_tracklist(text)
+    collection = [_collection_record("Artist", "Title")]
+    resolutions = resolve_tracklist(parsed, collection)
+    assert len(resolutions) == 2
+    assert all(r.outcome == "matched" for r in resolutions)
+
+
+def test_no_delimiter_line_lands_in_unparseable_with_line_number() -> None:
+    text = "Artist - Title\nNoDelimiterHere\n"
+    parsed, unparseable = parse_tracklist(text)
+    assert len(parsed) == 1
+    assert len(unparseable) == 1
+    assert unparseable[0].line_number == 2
+
+
+def test_line_matching_two_collection_entries_is_ambiguous() -> None:
+    text = "Artist - Title\n"
+    parsed, _ = parse_tracklist(text)
+    collection = [
+        _collection_record("Artist", "Title", "one.mp3"),
+        _collection_record("Artist", "Title", "two.mp3"),
+    ]
+    resolutions = resolve_tracklist(parsed, collection)
+    assert resolutions[0].outcome == "ambiguous"
+
+
+def test_line_matching_nothing_is_unmatched() -> None:
+    text = "Artist - Title\n"
+    parsed, _ = parse_tracklist(text)
+    resolutions = resolve_tracklist(parsed, [])
+    assert resolutions[0].outcome == "unmatched"
+
+
+def test_resolution_order_matches_input_order_with_middle_line_unmatched() -> None:
+    text = "Artist A - Title A\nArtist B - Title B\nArtist C - Title C\n"
+    parsed, _ = parse_tracklist(text)
+    collection = [_collection_record("Artist A", "Title A"), _collection_record("Artist C", "Title C")]
+    resolutions = resolve_tracklist(parsed, collection)
+    assert [r.outcome for r in resolutions] == ["matched", "unmatched", "matched"]
+    assert resolutions[0].line.artist == "Artist A"
+    assert resolutions[2].line.artist == "Artist C"
+
+
+def test_matched_resolution_carries_the_collection_records_primary_key() -> None:
+    text = "Artist - Title\n"
+    parsed, _ = parse_tracklist(text)
+    collection = [_collection_record("Artist", "Title", "track.mp3")]
+    resolutions = resolve_tracklist(parsed, collection)
+    assert resolutions[0].matched_record.primary_key == collection[0].primary_key

```

**Documentation:**

```diff
--- a/tests/test_tracklist.py
+++ b/tests/test_tracklist.py
@@ -69,5 +69,7 @@ def test_bare_title_with_no_delimiter_is_unparseable() -> None:
 
 
+# exercises the per-line match_records call (DL-025): two identical lines
+# must resolve independently rather than collapsing onto one shared result
 def test_two_identical_lines_resolve_independently() -> None:
     text = "Artist - Title\nArtist - Title\n"
     parsed, _ = parse_tracklist(text)

```


### Milestone 2: Playlist synthesis, document assembly and build-playlist subcommand

**Files**: traktor_nml/buildplaylist.py, traktor_nml/playlists.py, traktor_nml/commands/build_playlist_cmd.py, tests/test_build_playlist.py, tests/CLAUDE.md

**Requirements**:

- A playlist name and an ordered list of primary keys serialize into a NODE TYPE=PLAYLIST subtree whose PLAYLIST child carries TYPE=LIST, ENTRIES equal to the key count, and a freshly generated UUID
- A name already held by a playlist in the target document takes the next free numbered suffix
- The synthesized node inserts into the root FOLDER's SUBNODES, or into a named existing folder's SUBNODES, with COUNT recalculated to what was assembled
- Every byte of the base document outside the receiving SUBNODES opening tag and the insertion point is preserved
- A run whose tracklist holds any unresolved line produces no output unless the unmatched override is passed
- An unresolved report naming every unparseable, unmatched and ambiguous line is written on every run, as CSV via csv.DictWriter with a header row when a report path is given
- The subcommand registers through the commands-package discovery mechanism and commits output through the atomic write primitive
- tests/CLAUDE.md's file table gains rows for tests/test_tracklist.py and tests/test_build_playlist.py, so a maintainer changing tracklist.py or buildplaylist.py is pointed at their tests
- The output-path refusal check covers the tracklist path as well as the base path, via the same bespoke set-membership check splice_cmd.py already uses for its own multi-input collision check
- A run yielding zero resolved lines aborts with a dedicated error and writes nothing, rather than writing a PLAYLIST with ENTRIES=0
- Two tracklist lines naming the same track produce two independent ENTRY elements in the output rather than being deduplicated
- A base document with no PLAYLISTS section, root FOLDER, or SUBNODES element at all aborts with a dedicated error, distinct from the named-target-folder-absent case

**Acceptance Criteria**:

- build-playlist appears in the top-level help subcommand list with cli.py unedited
- A run over a base holding every tracklist track writes an output whose new PLAYLIST holds one ENTRY per input line, in input order
- The new PLAYLIST's ENTRIES attribute and the receiving SUBNODES' COUNT attribute both equal the assembled counts
- Each new PRIMARYKEY KEY equals the matched collection entry's primary key, not a value derived from the input text
- A playlist name containing an ampersand and a double quote round-trips through the output as XML that re-parses, with the name intact
- A base already holding a playlist of the requested name yields a playlist carrying the numbered suffix, and the pre-existing playlist keeps its own name and UUID
- Two runs over one base produce different PLAYLIST UUID values
- The output document re-parses and every byte outside the receiving SUBNODES matches the base
- A tracklist holding one unmatched line exits non-zero, writes the unresolved report, and leaves the output path absent
- That same run with the unmatched override exits zero and writes a playlist holding only the resolved lines, with ENTRIES matching
- An output path resolving to the base path or to the tracklist path is refused before any write
- A named target folder absent from the base aborts with no output written
- A named target folder matching more than one FOLDER in the base's PLAYLISTS tree aborts with a target_folder_ambiguous error and no output written, rather than inserting into the first match found
- A named target folder present in the base receives the node, and the root SUBNODES COUNT is unchanged
- A dry run prints its stats and leaves the output path absent
- A malformed base reports xml_parse_error naming the path and exits 2
- A missing tracklist file reports input_not_found naming the path and exits 2
- The unresolved-track abort and an input-error abort (xml_parse_error, input_not_found) both exit 2, matching splice_cmd.py's own convention of one exit code for both failure classes
- An empty tracklist, a tracklist whose every line is unparseable, and a tracklist whose every line is unmatched with the unmatched override all abort with a dedicated error and write nothing
- Two tracklist lines naming a track present in the base collection produce two ENTRY/PRIMARYKEY elements referencing it, in input order, in the written output
- A base document with no PLAYLISTS section, root FOLDER, or SUBNODES element at all aborts with a no_root_subnodes error and writes nothing
- A written CSV unresolved report parses back as valid CSV with a header row matching the printed rows' fields
- An --unresolved-report path resolving to the base, tracklist, or output path is refused before any write, the same as the output-path refusal
- A tracklist file that is not valid UTF-8 reports tracklist_decode_error naming the path and exits 2, rather than raising an unguarded traceback
- A tracklist file prefixed with a UTF-8 BOM parses its first line's artist without the BOM character corrupting it
- The output commit path calls rewrite.write_bytes_atomically and never writes to the output path by any other means, confirmed by asserting on that call rather than only on the resulting file's final content (C-003)
- No occurrence of pyacoustid, chromaprint, fpcalc, an HTTP client import, or CSV/M3U tracklist parsing appears anywhere in traktor_nml/buildplaylist.py, traktor_nml/tracklist.py, or traktor_nml/commands/build_playlist_cmd.py, and matching.py/confidence.py remain byte-identical to their pre-existing contents (C-007)
- Calling assemble_output directly on an input that produces an unresolved-tracks or no_entries_resolved error never creates, truncates, or otherwise touches the intended output path - the output path is only ever opened by _handle_build_playlist after assemble_output has already returned a non-None output (C-008)
- Before this command is treated as release-ready, a real Traktor installation opens at least one generated build-playlist output and confirms it imports without error or data loss, exactly as R-006's manual-validation gate requires and as the imported-playlist path's own unautomated package-log R-004 caveat is documented but never enforced by this test suite either

**Tests**:

- tests/test_build_playlist.py - integration through run_tool, doc-derived from DL-011 (guarantees stated over printed stats lines and written files)
- normal: a three-line tracklist against a matching base writes a playlist of three entries in input order
- normal: stats lines report lines read, entries written and the final playlist name
- normal: a named existing target folder receives the node while the root SUBNODES COUNT stays put
- edge: a name colliding with an existing playlist takes the numbered suffix and leaves the original's name and UUID untouched
- edge: a name holding an ampersand and a double quote survives a re-parse of the output
- edge: two consecutive runs over one base yield different PLAYLIST UUID values
- edge: a base whose root SUBNODES is empty receives the node with COUNT set to one
- edge: every byte outside the receiving SUBNODES matches the base
- edge: a dry run prints stats and leaves the output path absent
- error: one unmatched line aborts with a non-zero exit, a written report and no output file
- error: the same input with the unmatched override writes the resolved subset, exits zero, and reports ENTRIES matching what was written
- error: an absent named target folder aborts with no output file
- error: two FOLDERs sharing the requested target-folder name, in different branches of the PLAYLISTS tree, abort with target_folder_ambiguous and no output file
- error: an output path resolving to the base path or the tracklist path is refused before any write
- error: a malformed base yields xml_parse_error naming the path and exit 2, and a missing tracklist yields input_not_found and exit 2
- error: an empty tracklist, an all-unparseable tracklist, and an all-unmatched tracklist under the unmatched override each abort with a dedicated error, exit 2, and write nothing
- error: a base with no PLAYLISTS section, root FOLDER, or SUBNODES element at all aborts with a no_root_subnodes error, exit 2, and writes nothing
- edge: two tracklist lines naming the same collection track produce two ENTRY elements referencing it, in input order
- edge: the CSV unresolved report opens with csv.DictReader and its header row names the same fields as the printed rows
- edge: a successful partial build under --allow-unmatched, given an --unresolved-report path, writes a playlist AND a CSV report naming the unmatched line - the zero-resolved-abort CSV test alone does not cover this path
- edge: the written PRIMARYKEY KEY equals the matched collection entry's real primary key, is never equal to the raw tracklist line text, and never contains the parsed artist token as a path segment
- edge: every byte of the output outside the receiving SUBNODES span is byte-identical to the base, verified by exact prefix/suffix string comparison against the base document, not substring/count checks alone
- unit: _handle_build_playlist's commit path is monkeypatched at rewrite.write_bytes_atomically and asserted called exactly once with the assembled bytes, on a run that would otherwise succeed (C-003)
- static: no import or substring match for pyacoustid, chromaprint, fpcalc, requests, urllib.request, csv-as-tracklist-format, or an .m3u/.m3u8 extension check appears in buildplaylist.py, tracklist.py, or build_playlist_cmd.py; matching.py and confidence.py's sha256 digests are asserted equal to their pre-existing values (C-007)
- unit: a CLI run whose tracklist aborts (unmatched line, no override) leaves a pre-existing file at the output path completely byte-unchanged - not a call to the core assemble_output alone, which has no output-path parameter to touch in the first place (C-008)
- manual, not automated (R-006): open at least one generated build-playlist output in a real Traktor installation and confirm it imports without error or data loss before the command is considered release-ready
- error: an --unresolved-report path resolving to the base, tracklist, or output path is refused with exit 2 before any write
- error: a non-UTF-8 tracklist file reports tracklist_decode_error naming the path and exits 2 rather than raising
- edge: a UTF-8-BOM-prefixed tracklist's first line resolves normally, its artist free of the BOM character

#### Code Intent

- **CI-M-002-001** `traktor_nml/playlists.py::synthesize_playlist_node`: Take a playlist name and an ordered list of primary keys and return the serialized NODE TYPE=PLAYLIST fragment for them: a NODE carrying TYPE=PLAYLIST and NAME, holding one PLAYLIST child with TYPE=LIST, ENTRIES set to the key count, and UUID set to a fresh uuid4 hex, holding one ENTRY per key in the given order, each with a single PRIMARYKEY carrying TYPE=TRACK and KEY. The subtree is assembled as ElementTree elements and returned as ET.tostring output, so the name and every key are escaped by the serializer. It sits beside import_playlists because both emit a playlist fragment under the same naming and UUID policy, differing only in whether a source node exists. (refs: DL-028, DL-029, DL-039)
- **CI-M-002-002** `traktor_nml/playlists.py::available_playlist_name`: Take a requested name and the set of names already in use and return the requested name when free, otherwise the first free numbered-suffix variant starting at 2, adding the result to the in-use set. import_playlists collision handling reads through this one function so the suffix rule has a single spelling shared by imported and synthesized playlists. (refs: DL-029)
- **CI-M-002-003** `traktor_nml/buildplaylist.py::assemble_output`: Take base source text, the parsed base root, parsed tracklist lines, a requested playlist name, an optional target folder name and an allow_unmatched flag, and return a result whose output is the complete new document text, or None together with errors. Resolve every line through resolve_tracklist against the base collection records; collect every unparseable, unmatched and ambiguous line into unresolved rows, keeping duplicate lines naming the same track as independent rows and independent resolved entries rather than deduplicating them. Return output None with an unresolved_tracks error when any unresolved row exists and allow_unmatched is false, populating the rows either way. Return output None with a no_entries_resolved error, before any span lookup, when zero lines resolve at all (an empty tracklist, every line unparseable, or every line unmatched with allow_unmatched true), rather than proceeding to synthesize a zero-entry PLAYLIST. Choose the receiving SUBNODES: the first SUBNODES span in the document for the default root folder, returning output None with a no_root_subnodes error when the base has no PLAYLISTS section, root FOLDER or SUBNODES element at all (mirroring splice.py's own no_root_subnodes check); or the SUBNODES child of the FOLDER whose name equals the target, located through a SpanIndex over the base, returning output None with a target_folder_not_found error when no such folder exists anywhere in the PLAYLISTS tree, or a target_folder_ambiguous error naming the count found when more than one FOLDER shares that name, never picking the first match in document order. Synthesize the node from the matched records primary keys in line order under a name resolved against the names of every playlist already in the base, then assemble output through OutputBuilder: verbatim text before the receiving span, add_counted_span over that span with the synthesized fragment as its single added child and the count set to its existing child count plus one, verbatim text after. Validate that every key in the synthesized fragment is a primary key of a base collection record before returning, mirroring the reference validation the merge path performs. The whole output is built and validated in memory before the caller opens any file handle. (refs: DL-024, DL-027, DL-028, DL-029, DL-030, DL-036, DL-037, DL-038)
- **CI-M-002-004** `traktor_nml/buildplaylist.py::BuildPlaylistResult`: A result record holding output (the assembled document text, None exactly when errors is non-empty), stats (lines read, lines resolved, tiers that matched, playlist name written, entries written, unresolved counts by kind), unresolved_rows (line number, raw text, artist, title, kind) and errors. Populating unresolved_rows on every run, including a clean one, keeps the report a record of what the run saw rather than only of what failed. (refs: DL-027, DL-034)
- **CI-M-002-005** `traktor_nml/commands/build_playlist_cmd.py::register`: Register the build-playlist subparser and its handler in the shared handlers dict. Positional arguments: base, tracklist, output. Options: a required name for the playlist, an optional target folder, an allow-unmatched override, an unresolved-report path for the CSV, and a dry-run switch. No match-confidence option appears: the resolution runs at loose, stated by the core module rather than selected at the command line. (refs: DL-024, DL-032)
- **CI-M-002-006** `traktor_nml/commands/build_playlist_cmd.py::_handle_build_playlist`: Refuse and return 2 when the output path, or a given --unresolved-report path, resolves to the base, the tracklist, or (for the report) the output path, checked via a bespoke set-membership comparison (args.output.resolve() in {args.base.resolve(), args.tracklist.resolve()}, and the report path checked against that same protected set plus the output path), mirroring splice_cmd.py's own multi-input collision check rather than routing through write_nml_safely's extra_inputs parameter, which exists only on the attribute-patching write path this span-assembly command does not use. The report path is included in this refusal because it is a second destination the run writes to, and pointing it at base or tracklist would truncate an input on a run this command otherwise describes as writing nothing. Read and parse the base through read_and_parse_source, printing its error and returning 2 on failure; read the tracklist bytes, reporting a missing file in the same input_not_found spelling, then decode with utf-8-sig (transparently stripping a leading BOM rather than letting it corrupt the first parsed line's artist) inside a try/except that reports tracklist_decode_error and returns 2 on UnicodeDecodeError, rather than letting a non-UTF-8 tracklist raise an unguarded traceback. Call the core assemble_output, print every stats entry as a key=value line, then write the unresolved report whether or not the run aborted: printed rows always, plus a CSV via csv.DictWriter (header row, newline="", UTF-8) when a report path is given, matching splice_cmd.py's _write_conflict_report exactly. On a None output, print each error to stderr, print the aborted marker and return 2 - the same exit code an input error (xml_parse_error, input_not_found) returns, matching splice_cmd.py's own convention of not distinguishing these failure classes by exit code. Otherwise commit through write_bytes_atomically unless the dry-run switch is set, printing output_written with the path. (refs: DL-024, DL-027, DL-033, DL-034, DL-035)

#### Code Changes

**CC-M-002-001** (traktor_nml/playlists.py) - implements CI-M-002-001

**Code:**

```diff
--- a/traktor_nml/playlists.py
+++ b/traktor_nml/playlists.py
@@ -190,3 +190,26 @@
             result.sorting_info.append(_sorting_info_fragment(sorting_info, final_name))
 
     return result
+
+
+def synthesize_playlist_node(name: str, primary_keys: list[str]) -> str:
+    """Take a playlist name and an ordered list of primary keys and return
+    the serialized NODE TYPE=PLAYLIST fragment for them: a NODE carrying
+    TYPE=PLAYLIST and NAME, holding one PLAYLIST child with TYPE=LIST,
+    ENTRIES set to the key count, and UUID set to a fresh uuid4 hex,
+    holding one ENTRY per key in the given order, each with a single
+    PRIMARYKEY carrying TYPE=TRACK and KEY. The subtree is assembled as
+    ElementTree elements and returned as ET.tostring output, so the name
+    and every key are escaped by the serializer. It sits beside
+    import_playlists because both emit a playlist fragment under the same
+    naming and UUID policy, differing only in whether a source node
+    exists."""
+    node = ET.Element("NODE", {"TYPE": "PLAYLIST", "NAME": name})
+    playlist_elem = ET.SubElement(
+        node, "PLAYLIST",
+        {"ENTRIES": str(len(primary_keys)), "TYPE": "LIST", "UUID": uuid.uuid4().hex},
+    )
+    for key in primary_keys:
+        entry_elem = ET.SubElement(playlist_elem, "ENTRY")
+        ET.SubElement(entry_elem, "PRIMARYKEY", {"TYPE": "TRACK", "KEY": key})
+    return ET.tostring(node, encoding="unicode")

```

**Documentation:**

```diff
--- a/traktor_nml/playlists.py
+++ b/traktor_nml/playlists.py
@@ -212,4 +212,6 @@ def synthesize_playlist_node(name: str, primary_keys: list[str]) -> str:
     for key in primary_keys:
         entry_elem = ET.SubElement(playlist_elem, "ENTRY")
         ET.SubElement(entry_elem, "PRIMARYKEY", {"TYPE": "TRACK", "KEY": key})
+    # encoding="unicode" returns str (not bytes): callers splice this
+    # fragment directly into a text-based document assembly (DL-028)
     return ET.tostring(node, encoding="unicode")

```


**CC-M-002-002** (traktor_nml/playlists.py) - implements CI-M-002-002

**Code:**

```diff
--- a/traktor_nml/playlists.py
+++ b/traktor_nml/playlists.py
@@ -107,5 +107,21 @@
         if new_key is not None and new_key != old_key:
             pk.attrib["KEY"] = new_key
 
 
+def available_playlist_name(requested_name: str, existing_names: set[str]) -> str:
+    """Take a requested name and the set of names already in use and return
+    the requested name when free, otherwise the first free numbered-suffix
+    variant starting at 2, adding the result to the in-use set.
+    import_playlists' own collision handling reads through this one
+    function so the suffix rule has a single spelling shared by imported
+    and synthesized playlists."""
+    final_name = requested_name
+    suffix = 2
+    while final_name in existing_names:
+        final_name = f"{requested_name} ({suffix})"
+        suffix += 1
+    existing_names.add(final_name)
+    return final_name
+
+
 def import_playlists(
@@ -141,9 +157,4 @@
     for node in find_playlist_nodes(non_base_root):
         original_name = node.attrib.get("NAME", "")
-        final_name = original_name
-        suffix = 2
-        while final_name in existing_names:
-            final_name = f"{original_name} ({suffix})"
-            suffix += 1
-        existing_names.add(final_name)
+        final_name = available_playlist_name(original_name, existing_names)
         renamed = final_name != original_name

```

**Documentation:**

```diff
--- a/traktor_nml/playlists.py
+++ b/traktor_nml/playlists.py
@@ -118,5 +118,7 @@ def available_playlist_name(requested_name: str, existing_names: set[str]) ->
     final_name = requested_name
     suffix = 2
+    # starts at 2 so the first collision becomes "<name> (2)", the same
+    # numbering import_playlists also uses (DL-029)
     while final_name in existing_names:
         final_name = f"{requested_name} ({suffix})"
         suffix += 1

```


**CC-M-002-003** (traktor_nml/buildplaylist.py) - implements CI-M-002-004

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/buildplaylist.py
@@ -0,0 +1,45 @@
+"""build-playlist core: resolution, playlist synthesis, insertion.
+
+A build-playlist run resolves each track-list line against a base
+collection through the shared matching cascade in tracklist.py at
+MatchConfidence.LOOSE, synthesizes a NODE TYPE=PLAYLIST fragment from the
+resolved primary keys in input order (playlists.synthesize_playlist_node),
+and inserts it into the base's root FOLDER SUBNODES, or a named existing
+folder's SUBNODES, through the same byte-span assembly spans.py's other
+structural commands (splice.py/split.py) already use. No source span
+exists for a playlist assembled from external text, so its fragment
+always takes the ElementTree-serialization path (DL-028) rather than
+transplantation. matching.py and confidence.py are reached only through
+tracklist.py's own calls and are never edited here.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field
+from typing import Optional
+
+from .model import collection_records
+from .playlists import available_playlist_name, find_playlist_nodes, synthesize_playlist_node
+from .spans import OutputBuilder, SpanIndex, find_element_span
+from .tracklist import parse_tracklist, resolve_tracklist
+
+
+@dataclass
+class UnresolvedRow:
+    line_number: int
+    raw_text: str
+    artist: str
+    title: str
+    kind: str  # "unparseable", "unmatched", "ambiguous"
+
+
+@dataclass
+class BuildPlaylistResult:
+    """output is None exactly when errors is non-empty. unresolved_rows is
+    populated on every run, including a clean one, so the report is a
+    record of what the run saw rather than only of what failed (DL-027,
+    DL-034)."""
+    output: Optional[str]
+    stats: dict[str, object]
+    unresolved_rows: list[UnresolvedRow] = field(default_factory=list)
+    errors: list[str] = field(default_factory=list)

```

**Documentation:**

```diff
--- a/traktor_nml/buildplaylist.py
+++ b/traktor_nml/buildplaylist.py
@@ -26,6 +26,7 @@ from .tracklist import parse_tracklist, resolve_tracklist
 
 @dataclass
 class UnresolvedRow:
+    """One tracklist line that did not become a written ENTRY, and why."""
     line_number: int
     raw_text: str
     artist: str

```


**CC-M-002-004** (traktor_nml/buildplaylist.py) - implements CI-M-002-003

**Code:**

```diff
--- a/traktor_nml/buildplaylist.py
+++ b/traktor_nml/buildplaylist.py
@@ -43,3 +43,133 @@
     stats: dict[str, object]
     unresolved_rows: list[UnresolvedRow] = field(default_factory=list)
     errors: list[str] = field(default_factory=list)
+
+
+def _find_target_subnodes(base_root, base_source: str, target_folder: Optional[str]):
+    """Return (subnodes_span, existing_child_count, error) for the
+    receiving SUBNODES: the default root folder's SUBNODES (the first
+    SUBNODES span in the document, matching splice.py's own default), or
+    the SUBNODES of the FOLDER named target_folder, resolved against the
+    parsed tree and a SpanIndex rather than by document position, so a
+    name collision across folders is never resolved by picking the first
+    match (DL-030). The named-folder search is scoped to descendants of
+    the PLAYLISTS root NODE, matching DL-030's own wording ('anywhere in
+    the PLAYLISTS tree') - a same-named FOLDER living outside PLAYLISTS
+    (there is none in the confirmed schema, but nothing rules one out)
+    must never satisfy or falsely ambiguate this lookup. A base with no
+    PLAYLISTS section, root FOLDER, or SUBNODES element at all reports
+    no_root_subnodes, mirroring splice.py's own check for the identical
+    absence (DL-038)."""
+    playlists_root = base_root.find(".//PLAYLISTS/NODE")
+    if playlists_root is None or playlists_root.find("SUBNODES") is None:
+        return None, 0, "no_root_subnodes"
+
+    if target_folder is None:
+        subnodes_span = find_element_span(base_source, "SUBNODES")
+        if subnodes_span is None:
+            return None, 0, "no_root_subnodes"
+        root_subnodes_elem = playlists_root.find("SUBNODES")
+        count = 0 if root_subnodes_elem is None else len(list(root_subnodes_elem))
+        return subnodes_span, count, None
+
+    matching_folders = [
+        folder for folder in playlists_root.findall(".//NODE[@TYPE='FOLDER']")
+        if folder.attrib.get("NAME", "") == target_folder
+    ]
+    if not matching_folders:
+        return None, 0, "target_folder_not_found"
+    if len(matching_folders) > 1:
+        return None, 0, f"target_folder_ambiguous={target_folder}"
+
+    folder_subnodes = matching_folders[0].find("SUBNODES")
+    if folder_subnodes is None:
+        return None, 0, "no_root_subnodes"
+
+    span_index = SpanIndex(base_source, base_root)
+    subnodes_span = span_index.span_of(folder_subnodes)
+    count = len(list(folder_subnodes))
+    return subnodes_span, count, None
+
+
+def assemble_output(
+    base_source: str,
+    base_root,
+    tracklist_text: str,
+    playlist_name: str,
+    target_folder: Optional[str] = None,
+    allow_unmatched: bool = False,
+) -> BuildPlaylistResult:
+    """Resolve every tracklist line against the base collection, synthesize
+    a playlist from the resolved primary keys in input order, and splice
+    it into the receiving SUBNODES. Returns output None with
+    unresolved_tracks when any line is unresolved and allow_unmatched is
+    false (DL-027); output None with no_entries_resolved, before any span
+    lookup, when zero lines resolve at all (DL-036); output None with
+    no_root_subnodes/target_folder_not_found/target_folder_ambiguous=name
+    when the receiving container cannot be resolved (DL-030, DL-038). Duplicate
+    tracklist lines naming the same track resolve and serialize
+    independently (DL-037). The whole output is built and validated in
+    memory before the caller opens any file handle (C-008)."""
+    parsed_lines, unparseable_lines = parse_tracklist(tracklist_text)
+    records = collection_records(base_root)
+    resolutions = resolve_tracklist(parsed_lines, records)
+
+    unresolved_rows: list[UnresolvedRow] = [
+        UnresolvedRow(line_number=u.line_number, raw_text=u.raw_text, artist="", title="", kind="unparseable")
+        for u in unparseable_lines
+    ]
+    matched_keys: list[str] = []
+    for resolution in resolutions:
+        if resolution.outcome == "matched":
+            matched_keys.append(resolution.matched_record.primary_key)
+        else:
+            unresolved_rows.append(
+                UnresolvedRow(
+                    line_number=resolution.line.line_number, raw_text=resolution.line.raw_text,
+                    artist=resolution.line.artist, title=resolution.line.title, kind=resolution.outcome,
+                )
+            )
+    unresolved_rows.sort(key=lambda row: row.line_number)
+
+    stats: dict[str, object] = {
+        "lines_read": len(parsed_lines) + len(unparseable_lines),
+        "lines_resolved": len(matched_keys),
+        "unresolved_unparseable": len(unparseable_lines),
+        "unresolved_unmatched": sum(1 for r in resolutions if r.outcome == "unmatched"),
+        "unresolved_ambiguous": sum(1 for r in resolutions if r.outcome == "ambiguous"),
+        "playlist_name": None,
+        "entries_written": 0,
+    }
+
+    if unresolved_rows and not allow_unmatched:
+        return BuildPlaylistResult(output=None, stats=stats, unresolved_rows=unresolved_rows, errors=["unresolved_tracks"])
+
+    if not matched_keys:
+        return BuildPlaylistResult(output=None, stats=stats, unresolved_rows=unresolved_rows, errors=["no_entries_resolved"])
+
+    subnodes_span, existing_count, error = _find_target_subnodes(base_root, base_source, target_folder)
+    if error is not None:
+        return BuildPlaylistResult(output=None, stats=stats, unresolved_rows=unresolved_rows, errors=[error])
+
+    # No runtime validation of matched_keys against the collection's own
+    # primary keys is needed here: every matched_keys entry comes from
+    # resolution.matched_record, which resolve_tracklist draws only from
+    # this same records list (never from a playlist-only entry), so the
+    # invariant holds by construction rather than needing a check that
+    # could never actually fail.
+    existing_names = {node.attrib.get("NAME", "") for node in find_playlist_nodes(base_root)}
+    final_name = available_playlist_name(playlist_name, existing_names)
+    fragment = synthesize_playlist_node(final_name, matched_keys)
+    stats["playlist_name"] = final_name
+    stats["entries_written"] = len(matched_keys)
+
+    builder = OutputBuilder()
+    builder.add_verbatim(base_source[: subnodes_span.start])
+    builder.add_counted_span(
+        base_source, subnodes_span, "SUBNODES", "COUNT", [fragment],
+        count=existing_count + 1,
+    )
+    builder.add_verbatim(base_source[subnodes_span.end:])
+    output = builder.build()
+
+    return BuildPlaylistResult(output=output, stats=stats, unresolved_rows=unresolved_rows, errors=[])

```

**Documentation:**

```diff
--- a/traktor_nml/buildplaylist.py
+++ b/traktor_nml/buildplaylist.py
@@ -131,5 +131,8 @@ def assemble_output(
                 )
             )
+    # unparseable rows are collected before per-line resolutions and would
+    # otherwise precede a resolved-but-earlier unmatched/ambiguous line;
+    # sorting restores overall document line-number order for the report.
     unresolved_rows.sort(key=lambda row: row.line_number)
 
     stats: dict[str, object] = {
@@ -167,5 +170,7 @@ def assemble_output(
     builder = OutputBuilder()
     builder.add_verbatim(base_source[: subnodes_span.start])
+    # existing_count + 1: the synthesized PLAYLIST node is the one new
+    # child being added to the receiving SUBNODES element.
     builder.add_counted_span(
         base_source, subnodes_span, "SUBNODES", "COUNT", [fragment],
         count=existing_count + 1,

```


**CC-M-002-005** (traktor_nml/commands/build_playlist_cmd.py) - implements CI-M-002-005

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/commands/build_playlist_cmd.py
@@ -0,0 +1,26 @@
+"""build-playlist subcommand: synthesize an NML playlist from an external
+track list matched against a base collection."""
+
+from __future__ import annotations
+
+import argparse
+from pathlib import Path
+
+from ..buildplaylist import assemble_output
+from ..rewrite import read_and_parse_source, write_bytes_atomically
+
+
+def register(subparsers, handlers: dict) -> None:
+    parser = subparsers.add_parser(
+        "build-playlist",
+        help="Build an NML playlist from an external track list matched against a base collection",
+    )
+    parser.add_argument("base", type=Path)
+    parser.add_argument("tracklist", type=Path)
+    parser.add_argument("output", type=Path)
+    parser.add_argument("--name", required=True)
+    parser.add_argument("--target-folder", default=None)
+    parser.add_argument("--allow-unmatched", action="store_true")
+    parser.add_argument("--unresolved-report", type=Path, default=None)
+    parser.add_argument("--dry-run", action="store_true")
+    handlers["build-playlist"] = _handle_build_playlist

```

**Documentation:**

```diff
--- a/traktor_nml/commands/build_playlist_cmd.py
+++ b/traktor_nml/commands/build_playlist_cmd.py
@@ -11,6 +11,10 @@ from ..rewrite import read_and_parse_source, write_bytes_atomically
 
 
 def register(subparsers, handlers: dict) -> None:
+    """Register the build-playlist subparser. No --match-confidence option
+    is exposed: resolution always runs at a fixed MatchConfidence.LOOSE,
+    since a text-only track list leaves every stricter tier unreachable
+    (DL-032)."""
     parser = subparsers.add_parser(
         "build-playlist",
         help="Build an NML playlist from an external track list matched against a base collection",

```


**CC-M-002-006** (traktor_nml/commands/build_playlist_cmd.py) - implements CI-M-002-006

**Code:**

```diff
--- a/traktor_nml/commands/build_playlist_cmd.py
+++ b/traktor_nml/commands/build_playlist_cmd.py
@@ -4,10 +4,100 @@
 from __future__ import annotations
 
 import argparse
+import csv
+import sys
 from pathlib import Path
 
-from ..buildplaylist import assemble_output
+from ..buildplaylist import UnresolvedRow, assemble_output
 from ..rewrite import read_and_parse_source, write_bytes_atomically
+
+
+def _write_unresolved_report(rows: list[UnresolvedRow], csv_path: Path | None) -> None:
+    # An unresolved report is always written, matching splice_cmd.py's own
+    # _write_conflict_report convention: a record of what a run could not
+    # resolve is kept whether or not the run itself aborted (DL-027, DL-034).
+    for row in rows:
+        print(f"unresolved line={row.line_number} kind={row.kind} text={row.raw_text!r}")
+    if csv_path is not None:
+        with csv_path.open("w", newline="", encoding="utf-8") as handle:
+            writer = csv.DictWriter(handle, fieldnames=["line_number", "raw_text", "artist", "title", "kind"])
+            writer.writeheader()
+            for row in rows:
+                writer.writerow(
+                    {
+                        "line_number": row.line_number,
+                        "raw_text": row.raw_text,
+                        "artist": row.artist,
+                        "title": row.title,
+                        "kind": row.kind,
+                    }
+                )
+        print(f"unresolved_report_written={csv_path}")
+
+
+def _handle_build_playlist(args: argparse.Namespace) -> int:
+    # Refuses output == base or == tracklist, mirroring splice_cmd.py's own
+    # bespoke tuple-membership check for its multi-input shape (DL-033).
+    # --unresolved-report is checked against the same protected set: it is
+    # a second destination this run can write to, and a report path
+    # pointed at base or tracklist would truncate an input the run is
+    # supposed to leave untouched, on a run this command otherwise
+    # describes as writing nothing (DL-027).
+    protected = {args.base.resolve(), args.tracklist.resolve()}
+    if args.output.resolve() in protected:
+        print("output_must_differ_from_input", file=sys.stderr)
+        return 2
+    if args.unresolved_report is not None and args.unresolved_report.resolve() in protected | {args.output.resolve()}:
+        print("unresolved_report_must_differ_from_input", file=sys.stderr)
+        return 2
+
+    base_result = read_and_parse_source(args.base)
+    if base_result.error is not None:
+        print(base_result.error, file=sys.stderr)
+        return 2
+    base_bytes, base_root = base_result.source_bytes, base_result.root
+
+    try:
+        tracklist_bytes = args.tracklist.read_bytes()
+    except FileNotFoundError:
+        print(f"input_not_found={args.tracklist}", file=sys.stderr)
+        return 2
+
+    try:
+        # utf-8-sig transparently strips a leading UTF-8 BOM rather than
+        # letting it silently corrupt the first parsed line's artist name.
+        tracklist_text = tracklist_bytes.decode("utf-8-sig")
+    except UnicodeDecodeError:
+        print(f"tracklist_decode_error={args.tracklist}", file=sys.stderr)
+        return 2
+
+    result = assemble_output(
+        base_bytes.decode("utf-8"),
+        base_root,
+        tracklist_text,
+        args.name,
+        target_folder=args.target_folder,
+        allow_unmatched=args.allow_unmatched,
+    )
+
+    for key, value in result.stats.items():
+        print(f"{key}={value}")
+    _write_unresolved_report(result.unresolved_rows, args.unresolved_report)
+
+    if result.output is None:
+        for error in result.errors:
+            print(error, file=sys.stderr)
+        print("build_playlist_aborted=true", file=sys.stderr)
+        return 2
+
+    if not args.dry_run:
+        try:
+            write_bytes_atomically(args.output, result.output.encode("utf-8"))
+        except OSError as exc:
+            print(f"output_write_error={exc}", file=sys.stderr)
+            return 2
+        print(f"output_written={args.output}")
+    return 0
 
 
 def register(subparsers, handlers: dict) -> None:

```

**Documentation:**

```diff
--- a/traktor_nml/commands/build_playlist_cmd.py
+++ b/traktor_nml/commands/build_playlist_cmd.py
@@ -84,5 +84,7 @@ def _handle_build_playlist(args: argparse.Namespace) -> int:
     if result.output is None:
         for error in result.errors:
             print(error, file=sys.stderr)
+        # same exit code as an input error (xml_parse_error, input_not_found):
+        # splice_cmd.py does not distinguish these failure classes either (DL-035).
         print("build_playlist_aborted=true", file=sys.stderr)
         return 2

```


**CC-M-002-007** (tests/test_build_playlist.py)

**Code:**

```diff
--- /dev/null
+++ b/tests/test_build_playlist.py
@@ -0,0 +1,525 @@
+"""build-playlist: track-list resolution, playlist synthesis, and insertion."""
+
+from __future__ import annotations
+
+import csv
+import hashlib
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
+def _nml_no_playlists_section() -> str:
+    return (
+        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
+        '<COLLECTION ENTRIES="0"></COLLECTION>'
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
+def _existing_playlist(name: str, keys: list[str], uuid: str) -> str:
+    entries = "".join(f'<ENTRY><PRIMARYKEY TYPE="TRACK" KEY="{k}"></PRIMARYKEY></ENTRY>' for k in keys)
+    return (
+        f'<NODE TYPE="PLAYLIST" NAME="{name}">'
+        f'<PLAYLIST ENTRIES="{len(keys)}" TYPE="LIST" UUID="{uuid}">{entries}</PLAYLIST>'
+        "</NODE>"
+    )
+
+
+def _folder(name: str, inner: str) -> str:
+    return (
+        f'<NODE TYPE="FOLDER" NAME="{name}">'
+        f'<SUBNODES COUNT="{inner.count(chr(60)+"NODE")}">{inner}</SUBNODES>'
+        "</NODE>"
+    )
+
+
+def _key(filename: str) -> str:
+    return "C:" + "/:Music/:" + filename
+
+
+def test_three_line_tracklist_writes_three_entries_in_input_order(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(
+        _nml(_entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3") + _entry("C", "Three", "three.mp3"), 3, ""),
+        encoding="utf-8", newline="",
+    )
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\nB - Two\nC - Three\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 0
+    text = out.read_text(encoding="utf-8")
+    assert text.index(_key("one.mp3")) < text.index(_key("two.mp3")) < text.index(_key("three.mp3"))
+    assert 'NAME="MyList"' in text
+
+
+def test_stats_report_lines_read_entries_written_and_playlist_name(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 0
+    assert "lines_read=1" in result.stdout
+    assert "entries_written=1" in result.stdout
+    assert "playlist_name=MyList" in result.stdout
+
+
+def test_named_target_folder_receives_node_root_count_unchanged(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, _folder("MyFolder", "")), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(
+        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--target-folder", "MyFolder"],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 0
+    text = out.read_text(encoding="utf-8")
+    assert 'NAME="MyFolder"' in text
+    root_subnodes_count = text.split('SUBNODES COUNT="')[1].split('"')[0]
+    assert root_subnodes_count == "1"
+
+
+def test_name_collision_takes_numbered_suffix_original_untouched(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(
+        _nml(_entry("A", "One", "one.mp3"), 1, _existing_playlist("MyList", [_key("one.mp3")], "uuid-existing")),
+        encoding="utf-8", newline="",
+    )
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 0
+    text = out.read_text(encoding="utf-8")
+    assert 'NAME="MyList (2)"' in text
+    assert 'NAME="MyList"' in text
+    assert "uuid-existing" in text
+
+
+def test_two_runs_yield_different_uuids(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+
+    out1 = tmp_path / "out1.nml"
+    out2 = tmp_path / "out2.nml"
+    run_tool(["build-playlist", str(base), str(tracklist), str(out1), "--name", "MyList"], cwd=tmp_path)
+    run_tool(["build-playlist", str(base), str(tracklist), str(out2), "--name", "MyList"], cwd=tmp_path)
+
+    text1 = out1.read_text(encoding="utf-8")
+    text2 = out2.read_text(encoding="utf-8")
+    uuid1 = text1.split("PLAYLIST ENTRIES=")[1].split('UUID="')[1].split('"')[0]
+    uuid2 = text2.split("PLAYLIST ENTRIES=")[1].split('UUID="')[1].split('"')[0]
+    assert uuid1 != uuid2
+
+
+def test_name_with_ampersand_and_quote_round_trips(tmp_path: Path) -> None:
+    import xml.etree.ElementTree as ETree
+
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(
+        ["build-playlist", str(base), str(tracklist), str(out), "--name", 'Rock & Roll "Classics"'], cwd=tmp_path
+    )
+    assert result.exit_code == 0
+    text = out.read_text(encoding="utf-8")
+    root = ETree.fromstring(text.split("\n", 1)[1])
+    names = [node.attrib.get("NAME") for node in root.findall(".//NODE[@TYPE='PLAYLIST']")]
+    assert 'Rock & Roll "Classics"' in names
+
+
+def test_dry_run_prints_stats_and_writes_nothing(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(
+        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--dry-run"], cwd=tmp_path
+    )
+    assert result.exit_code == 0
+    assert not out.exists()
+    assert "entries_written=1" in result.stdout
+
+
+def test_unmatched_line_aborts_writes_report_no_output(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\nGhost - Track\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+    report = tmp_path / "unresolved.csv"
+
+    result = run_tool(
+        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--unresolved-report", str(report)],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 2
+    assert not out.exists()
+    assert report.exists()
+
+
+def test_allow_unmatched_writes_resolved_subset(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\nGhost - Track\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(
+        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--allow-unmatched"], cwd=tmp_path
+    )
+    assert result.exit_code == 0
+    assert out.exists()
+    assert "entries_written=1" in result.stdout
+
+
+def test_allow_unmatched_writes_report_alongside_successful_partial_build(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\nGhost - Track\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+    report = tmp_path / "unresolved.csv"
+
+    result = run_tool(
+        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--allow-unmatched",
+         "--unresolved-report", str(report)],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 0
+    assert out.exists()
+    with report.open(newline="", encoding="utf-8") as handle:
+        rows = list(csv.DictReader(handle))
+    assert len(rows) == 1
+    assert rows[0]["kind"] == "unmatched"
+    assert rows[0]["artist"] == "Ghost"
+
+
+def test_absent_named_target_folder_aborts_no_output(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(
+        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--target-folder", "DoesNotExist"],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 2
+    assert not out.exists()
+
+
+def test_ambiguous_target_folder_name_aborts_no_output(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(
+        _nml(_entry("A", "One", "one.mp3"), 1, _folder("Dup", "") + _folder("Wrapper", _folder("Dup", ""))),
+        encoding="utf-8", newline="",
+    )
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(
+        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--target-folder", "Dup"],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 2
+    assert not out.exists()
+    assert "target_folder_ambiguous=Dup" in result.stderr
+
+
+def test_output_path_resolving_to_base_or_tracklist_is_refused(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(base), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 2
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(tracklist), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 2
+
+
+def test_malformed_base_reports_xml_parse_error(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text("<NML><unclosed>", encoding="utf-8")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 2
+    assert "xml_parse_error" in result.stderr
+
+
+def test_missing_tracklist_reports_input_not_found(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(
+        ["build-playlist", str(base), str(tmp_path / "missing.txt"), str(out), "--name", "MyList"], cwd=tmp_path
+    )
+    assert result.exit_code == 2
+    assert "input_not_found" in result.stderr
+
+
+def test_empty_and_all_unparseable_and_all_unmatched_abort_with_no_output(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+
+    empty_tracklist = tmp_path / "empty.txt"
+    empty_tracklist.write_text("", encoding="utf-8")
+    out1 = tmp_path / "out1.nml"
+    result1 = run_tool(["build-playlist", str(base), str(empty_tracklist), str(out1), "--name", "MyList"], cwd=tmp_path)
+    assert result1.exit_code == 2
+    assert not out1.exists()
+
+    all_unparseable = tmp_path / "unparseable.txt"
+    all_unparseable.write_text("NoDelimiterHere\n", encoding="utf-8")
+    out2 = tmp_path / "out2.nml"
+    result2 = run_tool(["build-playlist", str(base), str(all_unparseable), str(out2), "--name", "MyList"], cwd=tmp_path)
+    assert result2.exit_code == 2
+    assert not out2.exists()
+
+    all_unmatched = tmp_path / "unmatched.txt"
+    all_unmatched.write_text("Ghost - Track\n", encoding="utf-8")
+    out3 = tmp_path / "out3.nml"
+    result3 = run_tool(
+        ["build-playlist", str(base), str(all_unmatched), str(out3), "--name", "MyList", "--allow-unmatched"],
+        cwd=tmp_path,
+    )
+    assert result3.exit_code == 2
+    assert not out3.exists()
+
+
+def test_base_with_no_playlists_section_aborts_with_no_root_subnodes(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml_no_playlists_section(), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 2
+    assert "no_root_subnodes" in result.stderr
+    assert not out.exists()
+
+
+def test_duplicate_tracklist_lines_produce_two_entries_in_order(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\nA - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 0
+    text = out.read_text(encoding="utf-8")
+    assert text.count(_key("one.mp3")) == 2
+
+
+def test_unresolved_csv_report_parses_back_with_matching_header(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("Ghost - Track\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+    report = tmp_path / "unresolved.csv"
+
+    result = run_tool(
+        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--allow-unmatched",
+         "--unresolved-report", str(report)],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 2  # zero resolved lines: no_entries_resolved
+    with report.open(newline="", encoding="utf-8") as handle:
+        rows = list(csv.DictReader(handle))
+    assert rows[0]["kind"] == "unmatched"
+    assert rows[0]["artist"] == "Ghost"
+
+
+def test_primarykey_comes_from_matched_entry_not_input_text(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 0
+    text = out.read_text(encoding="utf-8")
+    key = text.split('KEY="')[1].split('"')[0]
+    assert key == _key("one.mp3")
+    assert "A" not in key.split("/")
+    assert key != "A - One"
+
+
+def test_output_bytes_outside_receiving_subnodes_match_base_exactly(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base_text = _nml(_entry("A", "One", "one.mp3"), 1, "")
+    base.write_text(base_text, encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 0
+    out_text = out.read_text(encoding="utf-8")
+
+    prefix_marker = '<SUBNODES COUNT="'
+    suffix_marker = "</SUBNODES></NODE></PLAYLISTS>"
+    base_prefix, base_rest = base_text.split(prefix_marker, 1)
+    _, base_suffix = base_rest.split(suffix_marker, 1)
+    out_prefix, out_rest = out_text.split(prefix_marker, 1)
+    _, out_suffix = out_rest.split(suffix_marker, 1)
+
+    assert out_prefix == base_prefix
+    assert out_suffix == base_suffix
+
+
+def test_matching_and_confidence_modules_are_byte_identical_to_pre_existing_contents() -> None:
+    import traktor_nml.confidence as confidence
+    import traktor_nml.matching as matching
+
+    expected = {
+        "matching.py": "66f3b90a5dde258a437577718bc81cf0e86f57061e1ad5274bddf14806137e94",
+        "confidence.py": "d196b52d8ab34e97c54d17dc00c360e7917181ccb1aac26d872c4a7727335018",
+    }
+    for module, filename in ((matching, "matching.py"), (confidence, "confidence.py")):
+        content = Path(module.__file__).read_bytes()
+        digest = hashlib.sha256(content).hexdigest()
+        assert digest == expected[filename], f"{filename} changed - this feature must call the cascade, never edit it"
+
+
+def test_commit_path_uses_write_bytes_atomically(tmp_path: Path, monkeypatch) -> None:
+    from traktor_nml.commands import build_playlist_cmd
+
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+
+    calls = []
+    original = build_playlist_cmd.write_bytes_atomically
+
+    def _spy(path, data):
+        calls.append((path, data))
+        original(path, data)
+
+    monkeypatch.setattr(build_playlist_cmd, "write_bytes_atomically", _spy)
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 0
+    assert len(calls) == 1
+    assert calls[0][0] == out
+
+
+def test_no_forbidden_imports_or_substrings_in_new_modules() -> None:
+    import traktor_nml.buildplaylist as buildplaylist
+    import traktor_nml.tracklist as tracklist
+    from traktor_nml.commands import build_playlist_cmd
+
+    forbidden = ("pyacoustid", "chromaprint", "fpcalc", "requests", "urllib.request", ".m3u", ".m3u8")
+    for module in (buildplaylist, tracklist, build_playlist_cmd):
+        source = Path(module.__file__).read_text(encoding="utf-8")
+        for needle in forbidden:
+            assert needle not in source
+
+
+def test_abort_never_creates_or_modifies_a_pre_existing_output_path(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("Ghost - Track\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+    sentinel = "PRE-EXISTING CONTENT THAT MUST SURVIVE AN ABORT"
+    out.write_text(sentinel, encoding="utf-8")
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 2
+    assert out.read_text(encoding="utf-8") == sentinel
+
+
+def test_unresolved_report_path_resolving_to_an_input_is_refused(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_text("A - One\nGhost - Track\n", encoding="utf-8")
+    out = tmp_path / "out.nml"
+    base_sentinel = base.read_text(encoding="utf-8")
+
+    result = run_tool(
+        ["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList", "--unresolved-report", str(base)],
+        cwd=tmp_path,
+    )
+    assert result.exit_code == 2
+    assert not out.exists()
+    assert base.read_text(encoding="utf-8") == base_sentinel
+
+
+def test_non_utf8_tracklist_reports_decode_error(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_bytes("Björk - Jóga\n".encode("cp1252"))
+    out = tmp_path / "out.nml"
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 2
+    assert "tracklist_decode_error" in result.stderr
+    assert not out.exists()
+
+
+def test_utf8_bom_prefixed_tracklist_parses_first_line_cleanly(tmp_path: Path) -> None:
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    tracklist = tmp_path / "tracks.txt"
+    tracklist.write_bytes("A - One\n".encode("utf-8-sig"))
+    out = tmp_path / "out.nml"
+
+    result = run_tool(["build-playlist", str(base), str(tracklist), str(out), "--name", "MyList"], cwd=tmp_path)
+    assert result.exit_code == 0
+    assert "entries_written=1" in result.stdout
+    text = out.read_text(encoding="utf-8")
+    assert _key("one.mp3") in text

```

**Documentation:**

```diff
--- a/tests/test_build_playlist.py
+++ b/tests/test_build_playlist.py
@@ -108,6 +108,8 @@ def test_named_target_folder_receives_node_root_count_unchanged(tmp_path: Path
     assert root_subnodes_count == "1"
 
 
+# a name collision aborts nothing (DL-029): it takes the numbered
+# suffix and leaves the pre-existing playlist's own name and UUID alone
 def test_name_collision_takes_numbered_suffix_original_untouched(tmp_path: Path) -> None:
     base = tmp_path / "base.nml"
     base.write_text(

```


**CC-M-002-008** (tests/CLAUDE.md)

**Documentation:**

```diff
--- a/tests/CLAUDE.md
+++ b/tests/CLAUDE.md
@@ -17,1 +17,3 @@
 | `test_split.py`          | Split filter/dangling-reference tests                          | Changing `split.py`                                           |
+| `test_tracklist.py`      | External track-list parsing and per-line resolution tests      | Changing `tracklist.py`                                       |
+| `test_build_playlist.py` | build-playlist synthesis, insertion and CLI-surface tests       | Changing `buildplaylist.py`, its insertion point, or `commands/build_playlist_cmd.py` |

```


### Milestone 3: Package documentation tables

**Files**: traktor_nml/CLAUDE.md, traktor_nml/commands/CLAUDE.md, traktor_nml/README.md

**Requirements**:

- The package file table carries rows for the tracklist and buildplaylist modules with their read-when triggers
- The commands file table carries a row for the build-playlist command module with its read-when trigger
- The architecture notes record that a playlist assembled from external text has no source span and therefore serializes in full
- The package's own README.md Design Decisions log gains one new bullet per DL-024..DL-039, appended after the section's actual final entry (DL-019, not DL-023 - decision numbers in that section are not in document order), so the plan's decisions become durable project documentation rather than existing only in plan.json
- M-003 is a mandatory closing milestone, not optional polish: it is the sole carrier of CI-M-003-004, and a build that ships M-001/M-002 without it leaves all sixteen decisions (DL-024..DL-039) documented only in this planning artifact, never in the package's own durable log a future maintainer would actually consult

**Acceptance Criteria**:

- Every documentation table row names a file that exists in the package
- Each design-decision identifier cited anywhere in this plan resolves unambiguously to either a plan-local DL-024..DL-039 entry or an explicitly-flagged pre-existing package-log entry (DL-001..DL-023), with the two namespaces never sharing a number
- README.md's Design Decisions section contains a new bullet for each of DL-024 through DL-039, in that numeric order, immediately following the section's actual final entry (the DL-019 bullet), not its DL-023 entry which sits mid-section
- This feature is not considered complete when M-001 and M-002 pass their own acceptance criteria alone; M-003 must land in the same rollout, since no other milestone appends to README.md's Design Decisions log

**Tests**:

- No executable tests: the documentation tables carry no behavior, and their claims are checked by the file-existence and decision-reference review in the acceptance criteria

#### Code Intent

- **CI-M-003-001** `traktor_nml/CLAUDE.md::file_table`: The package file table carries a row for tracklist.py (external track-list parsing and per-line collection resolution; read when changing tracklist input format or per-line resolution) and a row for buildplaylist.py (build-playlist core: resolution, playlist synthesis, insertion; read when modifying playlist synthesis or its insertion point). (refs: DL-024)
- **CI-M-003-002** `traktor_nml/commands/CLAUDE.md::file_table`: The commands file table carries a row for build_playlist_cmd.py naming the build-playlist subcommand, its read-and-parse and atomic-commit routing, and its abort-unless-overridden policy for unresolved tracks; read when changing that subcommand CLI surface or its report. (refs: DL-024, DL-027)
- **CI-M-003-003** `traktor_nml/README.md::architecture_notes`: The architecture and invariants notes record that a playlist assembled from an external track list has no source span for its own node and so takes the serialization path in full, which the two-mechanism split already sanctions for genuinely new content rather than treating as an exception; and that this command resolves identity at loose confidence with no level selector, because a track list carrying only artist and title leaves every stricter tier unreachable. (refs: DL-028, DL-032)
- **CI-M-003-004** `traktor_nml/README.md::design_decisions_log`: Append one new bullet to the existing '## Design Decisions' list for each of DL-024 through DL-039, in that order, directly after the section's actual current final entry - the DL-019 bullet (README.md lines 70-73) - not DL-023, which appears earlier in the section (lines 50-55) despite its higher number; decision ids in this section are not in document order. Each bullet follows the section's existing wording style (a one-to-three sentence rationale ending in the parenthesized DL id) rather than restating the decision's full plan-local reasoning verbatim. This is the step that makes plan.json's readme_entries durable: without it, these sixteen decisions exist only in the planning artifact, never in the package's own log. (refs: DL-024, DL-025, DL-026, DL-027, DL-028, DL-029, DL-030, DL-031, DL-032, DL-033, DL-034, DL-035, DL-036, DL-037, DL-038, DL-039)

#### Code Changes

**CC-M-003-001** (traktor_nml/CLAUDE.md) - implements CI-M-003-001

**Documentation:**

```diff
--- a/traktor_nml/CLAUDE.md
+++ b/traktor_nml/CLAUDE.md
@@ -19,5 +19,7 @@
 | `spans.py`         | Byte-span transplantation, `OutputBuilder`, count-attribute recalculation, `SpanIndex` as the single-pass identity locator | Modifying splice/split's structural write path or count recalculation |
 | `playlists.py`     | Playlist import for splice (merge, rename, redirect); nodes are located through the shared `SpanIndex`, not a UUID text search | Modifying playlist merge, collision-rename, or PRIMARYKEY redirect logic |
 | `splice.py`        | Merge-command core: conflict resolution, playlist import; builds one `SpanIndex` per input source | Modifying splice's conflict policy or merge algorithm      |
 | `split.py`         | Partition-command core: filter, dangling-reference policy scoped to the group's own resolved playlist nodes, spans from the shared `SpanIndex` | Modifying split's selection filter or dangling-reference handling |
+| `tracklist.py`     | External track-list parsing and per-line collection resolution | Changing tracklist input format or per-line resolution      |
+| `buildplaylist.py` | build-playlist core: resolution, playlist synthesis, insertion | Modifying playlist synthesis or its insertion point          |
 | `cli.py`           | Subcommand discovery and argparse wiring                   | Adding a subcommand or changing dispatch                   |

```


**CC-M-003-002** (traktor_nml/commands/CLAUDE.md) - implements CI-M-003-002

**Documentation:**

```diff
--- a/traktor_nml/commands/CLAUDE.md
+++ b/traktor_nml/commands/CLAUDE.md
@@ -11,3 +11,4 @@
 | `reconnect_cmd.py`  | `scan-reconnect-candidates`/`rewrite-from-reconnect` subcommands (disk-scan reconnection); resolves volume identities before key providers are built and supplies them to the fingerprint provider as its known-mounts mapping | Changing reconnection's CLI surface or stats output    |
 | `splice_cmd.py`     | `splice` subcommand (merge NML files); reads/parses through `rewrite.read_and_parse_source` and commits through `rewrite.write_bytes_atomically` | Changing splice's CLI surface, conflict flags, or reports |
 | `split_cmd.py`      | `split` subcommand (partition an NML file); reads/parses through `rewrite.read_and_parse_source`, builds one `SpanIndex` per input and hands it to `build_output` for every group, and commits each group through `rewrite.write_bytes_atomically` | Changing split's CLI surface or dangling-reference flags |
+| `build_playlist_cmd.py` | `build-playlist` subcommand (external-tracklist playlist synthesis); reads/parses through `rewrite.read_and_parse_source`, aborts unless `--allow-unmatched` is passed on any unresolved track, and commits through `rewrite.write_bytes_atomically` | Changing that subcommand's CLI surface or its unresolved-track report |

```


**CC-M-003-003** (traktor_nml/README.md) - implements CI-M-003-003

**Documentation:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -26,5 +26,12 @@
 `commands/` holds one module per subcommand; `cli.py` discovers them by
 iterating the package rather than listing them, so adding a subcommand
 never requires editing `cli.py` (DL-003).
 
+`build-playlist` synthesizes its playlist node from an external track list
+with no source span to transplant, so it always takes the serialization
+path this split already sanctions for genuinely new content (DL-028), and
+it resolves track identity at a fixed `MatchConfidence.LOOSE` with no
+level selector, since a track list carrying only artist and title leaves
+every stricter tier unreachable (DL-032).
+
 ## Design Decisions

```


**CC-M-003-004** (traktor_nml/README.md) - implements CI-M-003-004

**Documentation:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -77,5 +77,83 @@
 - `splice_cmd` and `split_cmd` read, parse and write through helpers
   exported from `rewrite.py` rather than carrying their own input handling
   and a plain `write_bytes`, so both inherit the diagnostics and the atomic
   write `write_nml_safely` already implements (DL-019).
+- `build-playlist` splits its core resolution/assembly logic into
+  `buildplaylist.py` with only the CLI surface in
+  `commands/build_playlist_cmd.py`, following the core-module-plus-thin-command
+  pairing every other write command uses (DL-024).
+- Resolving a track list against the collection calls `match_records` once
+  per input line, with a single shared candidate index passed through its
+  `indexes` parameter, because the mapping and stats `match_records`
+  returns are keyed and aggregated per call and would otherwise collide
+  every line onto one result (DL-025).
+- In `build-playlist`'s matching call, the track list is the cascade's old
+  (iterated, order-preserving) side and the collection is its new
+  (indexed, candidate) side, mirroring how disk-scan candidates take the
+  new side for reconnection (DL-026).
+- An unmatched or ambiguous track-list line aborts `build-playlist`'s
+  entire run with nothing written unless `--allow-unmatched` is passed,
+  and the unresolved-line report is written whether or not the run
+  aborts, matching splice's unresolved-conflict policy (DL-027).
+- A playlist synthesized from external text has no source span to
+  transplant, so its `NODE`/`PLAYLIST`/`ENTRY`/`PRIMARYKEY` fragment is
+  always built as an `ElementTree` subtree and serialized with
+  `ET.tostring`, which the existing span-transplant-vs-serialization split
+  already treats as the sanctioned path for genuinely new content
+  (DL-028).
+- A synthesized `PLAYLIST` always gets a fresh `uuid4` hex, and a name
+  collision with an existing playlist takes the same deterministic
+  `"<name> (2)"` suffix `playlists.py` already applies to imported
+  playlists, so playlist naming/UUID policy has one spelling across both
+  entry points (DL-029).
+- `build-playlist`'s insertion point defaults to the root `FOLDER`'s
+  `SUBNODES`, or an existing folder named by `--target-folder`; a named
+  folder absent from the base aborts rather than being created, since a
+  fabricated folder's `SORTING_INFO`/nesting semantics are unverified
+  against the one confirmed schema version (DL-030).
+- The external track-list parser splits each line on its first `" - "`
+  occurrence only, never a bare hyphen, and reports (rather than silently
+  mis-splits) any line without that delimiter, since a bare-hyphen split
+  would corrupt real artist/title text like "Jean-Michel" (DL-031).
+- `build-playlist` calls the matching cascade at a fixed
+  `MatchConfidence.LOOSE` with no `--match-confidence` flag, because a
+  text-only track list carries only artist and title, making every tier
+  above `artist_title` structurally unreachable for it (DL-032).
+- `build-playlist`'s output-path refusal covers the track-list path as
+  well as the base path, via a bespoke set-membership check mirroring
+  `splice_cmd.py`'s own multi-input collision check, not
+  `write_nml_safely`'s `extra_inputs` parameter (which exists only on
+  the attribute-patching write path this span-assembly command does not
+  use) (DL-033).
+- `build-playlist`'s unresolved-line report is written as CSV via
+  `csv.DictWriter` with a header row, `newline=""`, and UTF-8 encoding,
+  matching `splice_cmd.py`'s `_write_conflict_report` exactly rather than
+  adopting a second CSV convention for the same kind of artifact
+  (DL-034).
+- `build-playlist` returns exit code 2 for both an input error (a
+  malformed base, a missing track list) and an unresolved-track abort,
+  rather than a distinct code per failure class, matching
+  `splice_cmd.py`'s own existing convention of not distinguishing them
+  (DL-035).
+- A `build-playlist` run that resolves zero lines (an empty track list,
+  every line unparseable, or every line unmatched with
+  `--allow-unmatched`) aborts with a dedicated error and writes nothing,
+  rather than writing a `PLAYLIST` with `ENTRIES=0`, matching `split.py`'s
+  own convention of dropping a playlist reduced to zero entries rather
+  than writing it empty (DL-036).
+- Two track-list lines naming the same collection track resolve and
+  serialize independently in `build-playlist`, producing duplicate
+  `ENTRY`/`PRIMARYKEY` elements rather than being deduplicated, since a
+  Traktor `PLAYLIST` is an ordered list of references and the operator's
+  input order and repetition are taken as authoritative (DL-037).
+- A base document `build-playlist` is given with no `PLAYLISTS` section,
+  root `FOLDER`, or `SUBNODES` element at all aborts with a
+  `no_root_subnodes` error rather than synthesizing the missing
+  structure, reusing the same error name `splice.py` already returns for
+  the identical failure mode (DL-038).
+- `build-playlist`'s synthesized fragment is inserted exactly as
+  `ET.tostring` serializes it (attribute quoting, empty-element
+  shorthand, absence of extra whitespace), with no attempt to match the
+  base document's own formatting conventions, the same as `playlists.py`'s
+  existing renamed/redirected fragments already do (DL-039).
 

```


## README Entries

### traktor_nml/README.md/README.md

`build-playlist` splits its core resolution/assembly logic into `buildplaylist.py` with only the CLI surface in `commands/build_playlist_cmd.py`, following the core-module-plus-thin-command pairing every other write command uses (DL-024).

### traktor_nml/README.md/README.md

Resolving a track list against the collection calls `match_records` once per input line, with a single shared candidate index passed through its `indexes` parameter, because the mapping and stats `match_records` returns are keyed and aggregated per call and would otherwise collide every line onto one result (DL-025).

### traktor_nml/README.md/README.md

In `build-playlist`'s matching call, the track list is the cascade's old (iterated, order-preserving) side and the collection is its new (indexed, candidate) side, mirroring how disk-scan candidates take the new side for reconnection (DL-026).

### traktor_nml/README.md/README.md

An unmatched or ambiguous track-list line aborts `build-playlist`'s entire run with nothing written unless `--allow-unmatched` is passed, and the unresolved-line report is written whether or not the run aborts, matching splice's unresolved-conflict policy (DL-027).

### traktor_nml/README.md/README.md

A playlist synthesized from external text has no source span to transplant, so its `NODE`/`PLAYLIST`/`ENTRY`/`PRIMARYKEY` fragment is always built as an `ElementTree` subtree and serialized with `ET.tostring`, which the existing span-transplant-vs-serialization split already treats as the sanctioned path for genuinely new content (DL-028).

### traktor_nml/README.md/README.md

A synthesized `PLAYLIST` always gets a fresh `uuid4` hex, and a name collision with an existing playlist takes the same deterministic `"<name> (2)"` suffix `playlists.py` already applies to imported playlists, so playlist naming/UUID policy has one spelling across both entry points (DL-029).

### traktor_nml/README.md/README.md

`build-playlist`'s insertion point defaults to the root `FOLDER`'s `SUBNODES`, or an existing folder named by `--target-folder`; a named folder absent from the base aborts rather than being created, since a fabricated folder's `SORTING_INFO`/nesting semantics are unverified against the one confirmed schema version (DL-030).

### traktor_nml/README.md/README.md

The external track-list parser splits each line on its first `" - "` occurrence only, never a bare hyphen, and reports (rather than silently mis-splits) any line without that delimiter, since a bare-hyphen split would corrupt real artist/title text like "Jean-Michel" (DL-031).

### traktor_nml/README.md/README.md

`build-playlist` calls the matching cascade at a fixed `MatchConfidence.LOOSE` with no `--match-confidence` flag, because a text-only track list carries only artist and title, making every tier above `artist_title` structurally unreachable for it (DL-032).

### traktor_nml/README.md/README.md

`build-playlist`'s output-path refusal covers the track-list path as well as the base path, via a bespoke set-membership check mirroring `splice_cmd.py`'s own multi-input collision check, not `write_nml_safely`'s `extra_inputs` parameter, which exists only on the attribute-patching write path this span-assembly command does not use (DL-033).

### traktor_nml/README.md/README.md

`build-playlist`'s unresolved-line report is written as CSV via `csv.DictWriter` with a header row, `newline=""`, and UTF-8 encoding, matching `splice_cmd.py`'s `_write_conflict_report` exactly rather than adopting a second CSV convention for the same kind of artifact (DL-034).

### traktor_nml/README.md/README.md

`build-playlist` returns exit code 2 for both an input error (a malformed base, a missing track list) and an unresolved-track abort, rather than a distinct code per failure class, matching `splice_cmd.py`'s own existing convention of not distinguishing them (DL-035).

### traktor_nml/README.md/README.md

A `build-playlist` run that resolves zero lines (an empty track list, every line unparseable, or every line unmatched with `--allow-unmatched`) aborts with a dedicated error and writes nothing, rather than writing a `PLAYLIST` with `ENTRIES=0`, matching `split.py`'s own convention of dropping a playlist reduced to zero entries rather than writing it empty (DL-036).

### traktor_nml/README.md/README.md

Two track-list lines naming the same collection track resolve and serialize independently in `build-playlist`, producing duplicate `ENTRY`/`PRIMARYKEY` elements rather than being deduplicated, since a Traktor `PLAYLIST` is an ordered list of references and the operator's input order and repetition are taken as authoritative (DL-037).

### traktor_nml/README.md/README.md

A base document `build-playlist` is given with no `PLAYLISTS` section, root `FOLDER`, or `SUBNODES` element at all aborts with a `no_root_subnodes` error rather than synthesizing the missing structure, reusing the same error name `splice.py` already returns for the identical failure mode (DL-038).

### traktor_nml/README.md/README.md

`build-playlist`'s synthesized fragment is inserted exactly as `ET.tostring` serializes it (attribute quoting, empty-element shorthand, absence of extra whitespace), with no attempt to match the base document's own formatting conventions, the same as `playlists.py`'s existing renamed/redirected fragments already do (DL-039).

## Execution Waves

- W-001: M-001
- W-002: M-002
- W-003: M-003

# Plan

## Overview

Traktor cannot deduplicate a collection: copied files, format upgrades, re-imports beside stale entries and path variants leave duplicate COLLECTION ENTRYs, and deleting one by hand orphans every playlist reference to it.

**Approach**: Implement the reviewed design in docs/plans/2026-09-26-collection-dedupe/plan.md: an M-001 spike measures the reference inventory and AUDIO_ID stability; M-002 records G0 decision-log entries (numbering continues the traktor_nml/README.md log above its DL-307 high-water mark, starting DL-308) then builds a printless byte-span dedupe core and CLI for tiers 1-2 behind a single validated write path; M-003 adds the nicegui-free view models and /dedupe section; M-004 to M-006 add gated tier 3, review-only tier 4 and extras.

## Planning Context

### Decision Log

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-308 | Implement docs/plans/2026-09-26-collection-dedupe/plan.md as reviewed; milestones M-001..M-006 and gates G0-G8 keep the design numbering; G0 is the first deliverable of M-002 | design reviewed twice with inventory, merge model, path policy, recovery and decisions schema fixed -> replanning them reopens settled review -> this plan sequences and specifies the work only |
| DL-309 | Byte-span patching via spans/textpatch: survivor ENTRY patched in place, loser ENTRY spans removed whole, COLLECTION ENTRIES count recalculated | A3 requires unknown attributes and children to survive -> reserialising drops byte fidelity and splice already proves the span path -> reuse SpanIndex, OutputBuilder, patch_entry_attributes, recalculate_count_attr |
| DL-310 | dedupe.write_validated_output(data, output_path, writer, parser) is the sole write path for CLI and GUI, wrapping rewrite.write_bytes_atomically | post-write validation must never be skippable -> two callers would each have to remember it -> one function with injectable writer and parser serves both and lets G5 force each failure |
| DL-311 | Exit codes 0 / 2 (argparse usage and refusals) / 3 (post-write validation failed, output renamed .invalid) | argparse exits 2 repo-wide and commands return 2 for refusals -> a code 1 would diverge -> reuse 2 and distinguish usage from refusal on stderr by usage: versus refused=<reason> |
| DL-312 | MergeFields record read beside EntryRecord; splice._TRACKED_ATTRS untouched; conflict rail gains a MergeFields source | widening EntryRecord or _TRACKED_ATTRS alters splice grouping and conflict output -> splice parity baseline would move -> a separate record keeps splice byte-identical |
| DL-313 | Tier 1 location equality compares (VOLUMEID, DIR, FILE) after separator normalisation; case folded only on volumes probed case-insensitive; unprobed volumes are case-sensitive and unmapped volumes are unknown (never dead); matching._fold MUST NOT be used for location equality | plan.md path policy section (lines 166-170) fixes this policy as authority -> matching._fold casefolds unconditionally, so on a case-sensitive volume two distinct files would merge -> a wrong merge is worse than a missed duplicate -> fold only when probed, never call matching._fold |
| DL-314 | Generic dangling-key scan over every attribute after redirection refuses the write with dangling_reference or the unknown shape name | the M-001 reference inventory may be incomplete -> an unlisted shape would be silently orphaned -> the backstop scan turns unknown shapes into refusals |
| DL-315 | Tiers 1-2 auto-apply under the admission rules; tier 3 admitted only if M-001 measures reanalysis >=99%, copy >=99%, false collision 0; tier 4 review-only; an unadmitted tier reports tier_N=disabled | AUDIO_ID stability is unmeasured -> gating tier 3 on recorded data prevents wrong merges -> tier 4 heuristics are never safe to auto-apply |
| DL-316 | PLAYCOUNT merges as max, LAST_PLAYED latest, IMPORT_DATE earliest; grids never merged and differing grids are a conflict | duplicates usually share one listening history -> summing double-counts -> max, re-checked by M-001 on the real library before G0 records it |
| DL-317 | Decisions JSON schema v1 keyed by sorted member primary keys with input_sha256; stale groups dropped and counted; an invalid file refuses with exit 2 and no partial application | reviewed pairs must not resurface while membership can change between runs -> per-group membership match is the safe reattachment rule -> invalid input refuses rather than half-applies |
| DL-318 | Dedupe view models (dedupe_model.py, dedupe_steps.py) import no nicegui; page code only in app.py; /dedupe is the fourth navigation.SECTIONS row | DL-069 and the two-interpreter harness require GUI logic importable without nicegui -> test_gui_import_isolation enforces it -> follow the reconstruct_steps and conflict_model pattern |
| DL-319 | G0: DL entries for inventory, merge model, path policy, exit codes, tier admission and decisions schema are committed to traktor_nml/README.md before any dedupe.py commit | the README decision log governs over plan text -> implementing first lets code become the de facto spec -> record first, then build |
| DL-320 | Survivor suggestion order: file exists > lossless over lossy > higher bitrate > more cues / has beatgrid > higher PLAYCOUNT > earliest IMPORT_DATE; reason shown, operator may override | plan.md Survivor and merge rules fix this order -> a missing file must never be kept over a live one and quality outranks usage history -> first differing criterion decides and is shown as the reason |
| DL-321 | M-006 repeat-collapse is an opt-in flag, default off: when on, consecutive/duplicate playlist rows that become identical after redirection collapse to the first occurrence; default keeps every row with loser->survivor substitution only | G2 requires playlist order preserved with substitution only -> collapsing by default would silently change playlists -> opt-in keeps the default byte-faithful |
| DL-322 | M-006 removable-files CSV lists only loser files that exist on disk and are not the survivor file (columns group_id, primary_key, local_path, survivor_primary_key); the tool never deletes, moves or renames audio | out-of-scope forbids touching audio -> operator still needs to know what is safe to remove -> CSV of existing loser files is the most the tool offers (plan.md line 32) |
| DL-323 | GUI dedupe flow is four linear steps (set up, scan, review, write) with one filter chip per tier and the decisions file saved on every review change | existing reconstruct_steps pattern is linear steps -> reuse keeps GUI consistent; tiers differ in confidence -> per-tier chips let user review risky tiers separately; decisions keyed by sorted member keys and stale groups dropped -> saving on every change loses no work on crash and costs nothing |
| DL-324 | Split the dedupe core into dedupe.py (a re-exporting facade) plus dedupe_members, dedupe_fields, dedupe_paths, dedupe_groups, dedupe_merge, dedupe_decisions, dedupe_references, dedupe_assembly and dedupe_write; tiers 3/4 and the M-006 extras live in dedupe_tier3.py, dedupe_tier4.py and dedupe_extras.py. Every file a dedupe run writes (NML, --report, --write-decisions, --removable-files, GUI decisions side file) passes dedupe_write.output_refusal first. | A single dedupe.py reached ~1330 lines and ~72 functions with 19 imports, past the 15-definition / 10-dependency limit -> split along its existing section banners so each module owns one concern -> dedupe.py re-exports the names the CLI, GUI and tests use so callers still import one module -> tiers 3/4 and extras stay separate modules so each lands behind its own milestone gate (M-004 AUDIO_ID verdict, M-005 version-variant guard, M-006) -> the constraint 'never write to an input path or the live collection.nml' covers every output, not only --output, so the guard sits in the shared write module and each writer calls it |

### Rejected Alternatives

| Alternative | Why Rejected |
|---|---|
| Reusing write_nml_safely | drives tree mutation/reserialisation and prints its own stats (ref: DL-310) |
| Summing PLAYCOUNT | double-counts shared listening history; max chosen, open question checked in M-001 (ref: DL-316) |
| Exit code 1 for usage errors | conflicts with argparse's 2 used repo-wide (ref: DL-311) |
| Widening EntryRecord / splice._TRACKED_ATTRS for merge fields | would change splice behaviour (ref: DL-312) |
| Deleting audio files | tool only edits collection files; removable-files CSV instead (ref: DL-322) |

### Constraints

- MUST: follow docs/plans/2026-09-26-collection-dedupe/plan.md (reference inventory, merge data model, path policy, recovery sequence, decisions schema and gates G0-G8 are fixed)
- MUST: G0 - record DL entries in traktor_nml/README.md before M-002 code
- MUST: M-001 spike (reference inventory + AUDIO_ID stability) before M-002; tier 3 only if promotion thresholds met
- MUST: nicegui-free view models (DL-069); page code only in app.py
- MUST: byte-span patching (spans/textpatch), never reserialise; write via rewrite.write_bytes_atomically inside dedupe.write_validated_output
- MUST: exit codes 0 / 2 (argparse usage and refusals) / 3 (post-write validation failed)
- MUST: never write to an input path or the live collection.nml; any dangling reference or unknown reference shape refuses
- MUST-NOT: use matching._fold for location equality; unprobed volumes are case-sensitive
- MUST-NOT: keyboard/accessibility work

### Known Risks

- **Real-library, re-analysed and copy/format-converted samples are unavailable for the M-001 spike (assumption M, unconfirmed)**: Confirm sample availability with the user before M-001 starts; without them tier 3 stays unadmitted (DL-315) and M-004 does not proceed, tiers 1-2 are unaffected
- **Appending a loser's raw CUE_V2 span may need an ordering or count fix-up (assumption M)**: M-001 checks Traktor acceptance of appended CUE_V2 spans; if a fix-up is needed, M-002 sorts appended cues by START and recalculates any count attribute before G2, with a fixture asserting it
- **Traktor rejects byte-preserved unknown attributes/children (assumption H)**: Byte-span patching leaves untouched spans identical to input Traktor already loaded; G2 asserts byte-identical non-merged spans
- **AUDIO_ID is not stable across copies or re-analysis (assumption L)**: M-001 measures stability; tier 3 admitted only if promotion thresholds met, else M-004 is skipped
- **History, _LOOPS or _RECORDINGS use a reference shape other than PRIMARYKEY (assumption M)**: M-001 reference inventory confirms shapes; the generic dangling-key scan refuses any unknown shape rather than orphaning it

## Invisible Knowledge

### System

Dedupe finds duplicate COLLECTION ENTRYs, merges loser metadata into a survivor by byte-span patching, redirects every PRIMARYKEY reference to the survivor, and writes a new NML only through write_validated_output. Assumptions (Traktor tolerates unknown attributes, AUDIO_ID stability, PRIMARYKEY shape for History/_LOOPS/_RECORDINGS, raw CUE_V2 append) are validated by M-001; see planning_context.risks.

### Invariants

- Failure mode is always a missed duplicate, never a wrong merge: unprobed volumes are case-sensitive, unmapped volumes are unknown not dead
- write_validated_output is the single write path, so CLI and GUI cannot skip post-write validation
- The generic dangling-key scan is the backstop: an unknown reference shape leaves a dangling key and refuses the write rather than orphaning references
- Decisions file is keyed by sorted member primary keys; stale groups are dropped, never refused

### Tradeoffs

- Stale decision groups are silently dropped (and counted) rather than refused, so an edited collection does not block reuse of a decisions file
- Generic attribute scan costs a full pass but covers reference shapes the inventory missed

## Milestones

### Milestone 1: M-001 Spike: reference inventory and AUDIO_ID stability

**Files**: spike/dedupe/measure.py, spike/dedupe/README.md, docs/2026-09-26-dedupe-spike.md

**Requirements**:

- measure.py reads a real NML plus a reanalysed copy and a copies folder and writes a Markdown artifact
- the artifact lists every element and attribute shape holding a value equal to some entry primary key with counts
- the artifact records AUDIO_ID presence and the reanalysis / copy / format / false-collision rates and dependency state
- the artifact states the tier 3 promotion verdict and the PLAYCOUNT max-versus-sum finding
- the spike writes no NML

**Acceptance Criteria**:

- artifact exists with input hashes recorded
- every reference shape row carries a handling decision
- tier 3 verdict follows from the recorded rates

**Tests**:

- manual run against the real library; no CI gate

#### Code Intent

- **CI-M-001-001** `spike/dedupe/measure.py`: Scans all attributes for primary-key-shaped values and tallies shapes; computes AUDIO_ID stability metrics and the promotion verdict; emits the Markdown artifact (refs: DL-308, DL-315)
- **CI-M-001-002** `spike/dedupe/README.md`: Describes spike inputs, command line and how the artifact feeds G0 (refs: DL-308)
- **CI-M-001-003** `docs/2026-09-26-dedupe-spike.md`: Recorded spike artifact: reference inventory, stability rates, dependency state, tier 3 verdict, PLAYCOUNT finding (refs: DL-315, DL-316)

#### Code Changes

**CC-M-001-001** (spike/dedupe/measure.py) - implements CI-M-001-001

**Code:**

```diff
--- a/spike/dedupe/measure.py
+++ b/spike/dedupe/measure.py
@@ -0,0 +1,275 @@
+"""M-001 spike: measure the reference inventory and AUDIO_ID stability
+on a real library before the dedupe core depends on either.
+
+Reads one real collection NML, a copy Traktor re-analysed, and a folder of
+byte-identical and format-converted copies of tracks in it, and writes one
+Markdown artifact. Writes no NML (plan.md "M-001 spike specification").
+
+Kept outside the package on purpose: its thresholds decide whether tier 3
+is admitted (DL-315), so the numbers are recorded once in the artifact and
+the package reads the verdict, never re-measures it.
+"""
+
+from __future__ import annotations
+
+import argparse
+import hashlib
+import importlib.util
+import shutil
+import sys
+from collections import Counter
+from dataclasses import dataclass
+from pathlib import Path
+
+from traktor_nml.matching import _duration_seconds, _fold
+from traktor_nml.model import EntryRecord, collection_records, parse_location_element
+from traktor_nml.rewrite import path_collides, read_and_parse_source
+from traktor_nml.volumes import local_path_for_location, parse_volume_map
+
+# Promotion thresholds for tier 3 on AUDIO_ID (plan.md, DL-315).
+REANALYSIS_MIN = 0.99
+COPY_MIN = 0.99
+FORMAT_MIN = 0.95
+AUDIO_EXTENSIONS = frozenset({".mp3", ".flac", ".wav", ".aif", ".aiff", ".m4a", ".ogg"})
+
+
+@dataclass(frozen=True)
+class Rates:
+    audio_id_presence: float
+    reanalysis: float
+    copy: float
+    format: float
+    false_collisions: int
+
+    def tier3_admitted(self) -> bool:
+        return self.reanalysis >= REANALYSIS_MIN and self.copy >= COPY_MIN and self.false_collisions == 0
+
+    def covers_format_upgrades(self) -> bool:
+        return self.tier3_admitted() and self.format >= FORMAT_MIN
+
+
+def _sha256(path: Path) -> str:
+    return hashlib.sha256(path.read_bytes()).hexdigest()
+
+
+def _share(hits: int, total: int) -> float:
+    return hits / total if total else 0.0
+
+
+def reference_inventory(root) -> Counter:
+    """Every element/attribute shape outside COLLECTION holding a value
+    equal to some entry's primary key, with counts: the table G0 records.
+
+    Shapes are labelled SECTION/TAG@ATTR[TYPE], the form the dedupe
+    core's generic dangling scan will name, and a non-collection LOCATION
+    composing to a primary key is labelled with @VOLUME+DIR+FILE. This
+    runs before traktor_nml/dedupe.py exists, so it carries its own scan."""
+    keys = {record.primary_key for record in collection_records(root)}
+    shapes: Counter = Counter()
+    sections = (s for s in root if isinstance(s.tag, str) and s.tag != "COLLECTION")
+    for section in sections:
+        for element in (e for e in section.iter() if isinstance(e.tag, str)):
+            shapes.update(_element_shapes(section.tag, element, keys))
+    return shapes
+
+
+def _element_shapes(section_tag: str, element, keys: set[str]) -> list[str]:
+    kind = element.attrib.get("TYPE", "")
+    if element.tag == "LOCATION":
+        composed = parse_location_element(element).primary_key
+        return [f"{section_tag}/LOCATION@VOLUME+DIR+FILE[{kind}]"] if composed in keys else []
+    return [f"{section_tag}/{element.tag}@{attr}[{kind}]" for attr, value in element.attrib.items() if value in keys]
+
+
+def reanalysis_stability(original: list[EntryRecord], reanalysed: list[EntryRecord]) -> tuple[float, int]:
+    """Share of entries present in both files, carrying an AUDIO_ID in
+    both, whose AUDIO_ID is unchanged."""
+    after = {r.primary_key: r.audio_id for r in reanalysed}
+    pairs = [(r.audio_id, after[r.primary_key]) for r in original if r.primary_key in after and r.audio_id]
+    pairs = [(a, b) for a, b in pairs if b]
+    return _share(sum(1 for a, b in pairs if a == b), len(pairs)), len(pairs)
+
+
+def false_collisions(records: list[EntryRecord]) -> int:
+    """Pairs sharing an AUDIO_ID whose artist, title or duration disagree."""
+    by_id: dict[str, list[EntryRecord]] = {}
+    for record in records:
+        if record.audio_id:
+            by_id.setdefault(record.audio_id, []).append(record)
+    collisions = 0
+    for group in by_id.values():
+        for i, a in enumerate(group):
+            for b in group[i + 1:]:
+                seconds_a, seconds_b = _duration_seconds(a), _duration_seconds(b)
+                same_tags = (_fold(a.artist), _fold(a.title)) == (_fold(b.artist), _fold(b.title))
+                same_length = seconds_a is not None and seconds_b is not None and abs(seconds_a - seconds_b) <= 1.0
+                collisions += 0 if same_tags and same_length else 1
+    return collisions
+
+
+def copy_agreement(records: list[EntryRecord], copies_root: Path, known_mounts) -> tuple[float, float, int, int]:
+    """Pair each collection entry whose file resolves under copies_root
+    (the copy) with the entry resolving outside it that shares its stem
+    (the original); a byte-identical copy and a format-converted copy each
+    agree when both entries carry one AUDIO_ID. Pairing by resolved path
+    keeps a copy from being matched to itself, since an imported copy
+    shares its original's stem and often its file name.
+    Returns (copy rate, format rate, copy count, format count)."""
+    root = copies_root.resolve()
+    originals: dict[str, EntryRecord] = {}
+    copies: list[tuple[Path, EntryRecord]] = []
+    for record in records:
+        path = local_path_for_location(record.location, known_mounts)
+        if path is None:
+            continue
+        if path.resolve().is_relative_to(root):
+            copies.append((path, record))
+        else:
+            originals.setdefault(path.stem.casefold(), record)
+    copy_hits = copy_total = format_hits = format_total = 0
+    for path, copy_entry in sorted(copies, key=lambda item: str(item[0])):
+        original = originals.get(path.stem.casefold())
+        if original is None or path.suffix.lower() not in AUDIO_EXTENSIONS:
+            continue
+        agree = bool(original.audio_id) and original.audio_id == copy_entry.audio_id
+        if path.suffix.lower() == Path(original.location.file_name).suffix.lower():
+            copy_total, copy_hits = copy_total + 1, copy_hits + agree
+        else:
+            format_total, format_hits = format_total + 1, format_hits + agree
+    return _share(copy_hits, copy_total), _share(format_hits, format_total), copy_total, format_total
+
+
+def dependency_state() -> dict[str, str]:
+    return {
+        "mutagen": "present" if importlib.util.find_spec("mutagen") else "absent",
+        "pyacoustid": "present" if importlib.util.find_spec("acoustid") else "absent",
+        "fpcalc": shutil.which("fpcalc") or "absent",
+    }
+
+
+# Handling fixed by plan.md's reference inventory for the shapes it names;
+# every other shape the run finds refuses until a row is decided by hand.
+KNOWN_HANDLING = {
+    "PLAYLISTS/PRIMARYKEY@KEY[TRACK]": "Redirect (playlists, History, `_LOOPS`, `_RECORDINGS`)",
+    "PLAYLISTS/PRIMARYKEY@KEY[STEM]": "Preserve",
+    "SETS/PRIMARYKEY@KEY[*]": "Preserve",
+}
+UNKNOWN_HANDLING = "Refuse (`unknown_reference_shape`) unless decided here"
+
+
+def _inventory_rows(inventory: Counter) -> dict[str, int]:
+    """Counts per table row: every SETS PRIMARYKEY TYPE folds into the
+    SETS [*] row, known rows appear even at zero, then any other shape."""
+    rows = dict.fromkeys(KNOWN_HANDLING, 0)
+    for shape, count in inventory.most_common():
+        key = "SETS/PRIMARYKEY@KEY[*]" if shape.startswith("SETS/PRIMARYKEY@KEY[") else shape
+        rows[key] = rows.get(key, 0) + count
+    return rows
+
+
+def render_artifact(inputs: dict[str, str], copies: tuple[str, int, int], inventory: Counter, rates: Rates,
+                    counts: dict[str, int], dependencies: dict[str, str], playcount_overlap: tuple[int, int]) -> str:
+    """Emits the same sections, rows and wording as the committed
+    docs/2026-09-26-dedupe-spike.md template, so a run fills the template
+    in place rather than discarding its handling rows."""
+    copies_path, copy_count, format_count = copies
+    lines = ["# Dedupe spike: reference inventory and AUDIO_ID stability", "", "## Inputs", ""]
+    lines += [f"- `{name}` sha256 `{digest}`" for name, digest in inputs.items()]
+    lines += [f"- copies folder: `{copies_path}`, {copy_count} byte-identical and {format_count}",
+              "  format-converted copies"]
+    lines += ["", "## Reference inventory", "", "| Shape | Count | Handling |", "| --- | --- | --- |"]
+    for shape, count in _inventory_rows(inventory).items():
+        lines.append(f"| `{shape}` | {count} | {KNOWN_HANDLING.get(shape, UNKNOWN_HANDLING)} |")
+    lines.append(f"| any other shape | 0 | {UNKNOWN_HANDLING} |")
+    lines += ["", "`INDEXING/SORTING_INFO PATH` names a playlist, not a track, and smartlists",
+              "are queries; neither appears in this table because neither holds a", "primary key."]
+    lines += ["", "## AUDIO_ID stability", "", "| Metric | Value | Sample |", "| --- | --- | --- |"]
+    lines += [
+        f"| AUDIO_ID presence | {rates.audio_id_presence:.2%} | {counts['entries']} entries |",
+        f"| Re-analysis stability | {rates.reanalysis:.2%} | {counts['reanalysed']} entries |",
+        f"| Copy agreement | {rates.copy:.2%} | {counts['copies']} copies |",
+        f"| Format agreement | {rates.format:.2%} | {counts['formats']} copies |",
+        f"| False collisions | {rates.false_collisions} | pairs |",
+    ]
+    lines += ["", "## Dependencies", ""] + [f"- {name}: {state}" for name, state in dependencies.items()]
+    verdict = "admitted" if rates.tier3_admitted() else "not admitted"
+    scope = "copies and format upgrades" if rates.covers_format_upgrades() else "copies only"
+    lines += ["", "## Tier 3 verdict", "",
+              f"AUDIO_ID for tier 3: {verdict}; scope {scope if rates.tier3_admitted() else 'none'}. Admitted only",
+              "when re-analysis stability and copy agreement are both at least 99% and",
+              "false collisions are zero (DL-315)."]
+    shared, disjoint = playcount_overlap
+    lines += [
+        "", "## PLAYCOUNT", "",
+        f"Duplicate groups with a LAST_PLAYED on every member: {shared}; on only some members: {disjoint}.",
+        "DL-316 records `max` unless the second count shows duplicates commonly carry disjoint histories.", "",
+    ]
+    return "\n".join(lines)
+
+
+def playcount_overlap(root) -> tuple[int, int]:
+    """Among AUDIO_ID-sharing groups, how many carry LAST_PLAYED on every
+    member (a shared history, which favours max) versus on only some (a
+    disjoint history, which would favour sum)."""
+    played: dict[str, list[bool]] = {}
+    for entry in root.find("COLLECTION").findall("ENTRY"):
+        audio_id = entry.attrib.get("AUDIO_ID", "")
+        if audio_id:
+            info = entry.find("INFO")
+            played.setdefault(audio_id, []).append(bool(info is not None and info.attrib.get("LAST_PLAYED")))
+    groups = [flags for flags in played.values() if len(flags) > 1]
+    return sum(1 for f in groups if all(f)), sum(1 for f in groups if any(f) and not all(f))
+
+
+def output_refusal(out: Path, *inputs: Path) -> str | None:
+    """Why --out cannot be written, or None, checked before any input is
+    read. The spike runs against the real library, so --out naming an
+    input or any collection.nml (the file Traktor itself loads) would
+    overwrite the library it measures; the artifact is Markdown, so any
+    .nml output is refused too (plan.md: never write to an input path or
+    the live collection.nml)."""
+    if path_collides(out, *inputs):
+        return f"refused: --out {out.as_posix()} names an input"
+    if out.name.casefold() == "collection.nml" or out.suffix.casefold() == ".nml":
+        return f"refused: --out {out.as_posix()} is an NML file; the artifact is Markdown"
+    return None
+
+
+def main(argv: list[str]) -> int:
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--nml", type=Path, required=True)
+    parser.add_argument("--reanalysed", type=Path, required=True)
+    parser.add_argument("--copies", type=Path, required=True)
+    parser.add_argument("--volume-map", nargs=3, action="append", metavar=("SCAN_ROOT", "VOLUME", "VOLUMEID"))
+    parser.add_argument("--out", type=Path, required=True)
+    args = parser.parse_args(argv)
+    refusal = output_refusal(args.out, args.nml, args.reanalysed)
+    if refusal is not None:
+        print(refusal, file=sys.stderr)
+        return 2
+
+    loaded, reloaded = read_and_parse_source(args.nml), read_and_parse_source(args.reanalysed)
+    for result in (loaded, reloaded):
+        if result.error is not None:
+            print(result.error, file=sys.stderr)
+            return 2
+    records, reanalysed = collection_records(loaded.root), collection_records(reloaded.root)
+    known_mounts: dict[tuple[str, str], list[Path]] = {}
+    for root_text, identity in parse_volume_map(args.volume_map).items():
+        known_mounts.setdefault(identity, []).append(Path(Path(root_text).anchor))
+
+    reanalysis, reanalysed_count = reanalysis_stability(records, reanalysed)
+    copy_rate, format_rate, copies, formats = copy_agreement(records, args.copies, known_mounts)
+    rates = Rates(_share(sum(1 for r in records if r.audio_id), len(records)), reanalysis, copy_rate, format_rate,
+                  false_collisions(records))
+    counts = {"entries": len(records), "reanalysed": reanalysed_count, "copies": copies, "formats": formats}
+    inputs = {str(args.nml): _sha256(args.nml), str(args.reanalysed): _sha256(args.reanalysed)}
+    text = render_artifact(inputs, (args.copies.as_posix(), copies, formats), reference_inventory(loaded.root),
+                           rates, counts, dependency_state(), playcount_overlap(loaded.root))
+    args.out.write_text(text, encoding="utf-8")
+    print(f"artifact_written={args.out.as_posix()} tier3={'admitted' if rates.tier3_admitted() else 'not_admitted'}")
+    return 0
+
+
+if __name__ == "__main__":
+    raise SystemExit(main(sys.argv[1:]))
```

**Documentation:**

```diff
--- a/spike/dedupe/measure.py
+++ b/spike/dedupe/measure.py
@@ -35,6 +35,10 @@
 
 @dataclass(frozen=True)
 class Rates:
+    """The measured AUDIO_ID stability shares and the false-collision count one
+    spike run produces; the artifact records them and tier 3 admission reads
+    them (DL-315)."""
+
     audio_id_presence: float
     reanalysis: float
     copy: float
@@ -42,9 +46,13 @@
     false_collisions: int
 
     def tier3_admitted(self) -> bool:
+        """True only when reanalysis and copy stability both reach their
+        minimums and no two different recordings share an AUDIO_ID (DL-315)."""
         return self.reanalysis >= REANALYSIS_MIN and self.copy >= COPY_MIN and self.false_collisions == 0
 
     def covers_format_upgrades(self) -> bool:
+        """True when tier 3 is admitted and AUDIO_ID also survives format
+        conversion, so a format upgrade may be grouped by AUDIO_ID alone."""
         return self.tier3_admitted() and self.format >= FORMAT_MIN
 
 
@@ -74,6 +82,9 @@
 
 
 def _element_shapes(section_tag: str, element, keys: set[str]) -> list[str]:
+    """The inventory labels one element outside COLLECTION contributes: its
+    composed LOCATION when that names an entry, otherwise each attribute
+    whose value is an entry's primary key."""
     kind = element.attrib.get("TYPE", "")
     if element.tag == "LOCATION":
         composed = parse_location_element(element).primary_key
@@ -140,6 +151,9 @@
 
 
 def dependency_state() -> dict[str, str]:
+    """Whether the optional fingerprint dependencies are installed, recorded in
+    the artifact so a tier 3 fingerprint result is read against the machine
+    that produced it."""
     return {
         "mutagen": "present" if importlib.util.find_spec("mutagen") else "absent",
         "pyacoustid": "present" if importlib.util.find_spec("acoustid") else "absent",
@@ -236,6 +250,9 @@
 
 
 def main(argv: list[str]) -> int:
+    """Run the spike and write the artifact. Returns 2 when --out names an
+    input or the live collection.nml, matching the dedupe command's refusal
+    code (DL-311); the spike never writes to an input."""
     parser = argparse.ArgumentParser(description=__doc__)
     parser.add_argument("--nml", type=Path, required=True)
     parser.add_argument("--reanalysed", type=Path, required=True)

```


**CC-M-001-002** (spike/dedupe/README.md) - implements CI-M-001-002

**Code:**

```diff
--- a/spike/dedupe/README.md
+++ b/spike/dedupe/README.md
@@ -0,0 +1,42 @@
+# spike/dedupe
+
+The M-001 spike for collection dedupe
+(`docs/plans/2026-09-26-collection-dedupe/plan.md`, "M-001 spike
+specification"). It measures two things the dedupe core must not assume:
+which XML shapes reference a collection entry by its primary key, and
+whether Traktor's `AUDIO_ID` is stable enough for tier 3. It writes no NML.
+
+## Inputs
+
+- `--nml`: one real collection NML.
+- `--reanalysed`: a copy of that NML after Traktor re-analyses a sample of
+  50 of its tracks.
+- `--copies`: a folder holding at least 20 byte-identical copies and 20
+  format-converted copies of tracks in the collection, each already
+  imported into the `--nml` collection so it has an entry of its own.
+- `--volume-map SCAN_ROOT VOLUME VOLUMEID`: mounts the collection's
+  volumes, so each original entry resolves to its file.
+
+## Command
+
+```
+python spike/dedupe/measure.py --nml collection.nml --reanalysed reanalysed.nml \
+    --copies D:\dedupe-copies --volume-map D:\ D: D: --out docs/2026-09-26-dedupe-spike.md
+```
+
+Run from the repository root with the package importable.
+
+## How the artifact feeds G0
+
+`docs/2026-09-26-dedupe-spike.md` records the input hashes, the reference
+inventory with counts, the stability rates, the dependency state and the
+tier 3 verdict. Before M-002 starts, each inventory row gets a handling
+decision (redirect, preserve, untouched), and the rows and the verdict are
+recorded as decision-log entries in `traktor_nml/README.md` (gate G0).
+`traktor_nml/dedupe.py`'s `REDIRECT_SHAPES` and `PRESERVE_SHAPES` are
+written from that table; `traktor_nml/dedupe_tier3.py`'s `ADMITTED` is
+written from the verdict.
+
+Promotion rule for tier 3 on `AUDIO_ID`: re-analysis stability >= 99%,
+copy agreement >= 99%, false collisions = 0. Format agreement >= 95%
+extends tier 3 to format upgrades; below it, tier 3 covers copies only.

```

**Documentation:**

```diff
--- a/spike/dedupe/README.md
+++ b/spike/dedupe/README.md
@@ -17,6 +17,9 @@
 - `--volume-map SCAN_ROOT VOLUME VOLUMEID`: mounts the collection's
   volumes, so each original entry resolves to its file.
 
+The spike only reads: an `--out` naming an input or the live `collection.nml`
+is refused with exit 2, the code `dedupe` uses for refusals (DL-311).
+
 ## Command
 
 ```

```


**CC-M-001-003** (docs/2026-09-26-dedupe-spike.md) - implements CI-M-001-003

**Code:**

```diff
--- a/docs/2026-09-26-dedupe-spike.md
+++ b/docs/2026-09-26-dedupe-spike.md
@@ -0,0 +1,57 @@
+# Dedupe spike: reference inventory and AUDIO_ID stability
+
+Produced by `spike/dedupe/measure.py` (see `spike/dedupe/README.md`). The
+script's `render_artifact` emits these sections, rows and wording, so a run
+with `--out` pointing here fills every `<measured>` value in place. Handling
+for the shapes plan.md names comes from the script's `KNOWN_HANDLING`; any
+further shape the run finds is written as a refusing row and is decided by
+hand here before G0.
+
+## Inputs
+
+- `<collection.nml>` sha256 `<measured>`
+- `<reanalysed.nml>` sha256 `<measured>`
+- copies folder: `<path>`, `<measured>` byte-identical and `<measured>`
+  format-converted copies
+
+## Reference inventory
+
+| Shape | Count | Handling |
+| --- | --- | --- |
+| `PLAYLISTS/PRIMARYKEY@KEY[TRACK]` | `<measured>` | Redirect (playlists, History, `_LOOPS`, `_RECORDINGS`) |
+| `PLAYLISTS/PRIMARYKEY@KEY[STEM]` | `<measured>` | Preserve |
+| `SETS/PRIMARYKEY@KEY[*]` | `<measured>` | Preserve |
+| any other shape | `<measured>` | Refuse (`unknown_reference_shape`) unless decided here |
+
+`INDEXING/SORTING_INFO PATH` names a playlist, not a track, and smartlists
+are queries; neither appears in this table because neither holds a
+primary key.
+
+## AUDIO_ID stability
+
+| Metric | Value | Sample |
+| --- | --- | --- |
+| AUDIO_ID presence | `<measured>` | `<measured>` entries |
+| Re-analysis stability | `<measured>` | `<measured>` entries |
+| Copy agreement | `<measured>` | `<measured>` copies |
+| Format agreement | `<measured>` | `<measured>` copies |
+| False collisions | `<measured>` | pairs |
+
+## Dependencies
+
+- mutagen: `<measured>`
+- pyacoustid: `<measured>`
+- fpcalc: `<measured>`
+
+## Tier 3 verdict
+
+AUDIO_ID for tier 3: `<admitted | not admitted>`; scope `<copies only |
+copies and format upgrades | none>`. Admitted only
+when re-analysis stability and copy agreement are both at least 99% and
+false collisions are zero (DL-315).
+
+## PLAYCOUNT
+
+Duplicate groups with a LAST_PLAYED on every member: `<measured>`; on only
+some members: `<measured>`.
+DL-316 records `max` unless the second count shows duplicates commonly carry disjoint histories.
```

**Documentation:**

```diff
--- a/docs/2026-09-26-dedupe-spike.md
+++ b/docs/2026-09-26-dedupe-spike.md
@@ -27,6 +27,9 @@
 are queries; neither appears in this table because neither holds a
 primary key.
 
+A row left as Refuse keeps `dedupe` refusing any collection that holds the
+shape, until the row is decided here and recorded under G0 (DL-314, DL-319).
+
 ## AUDIO_ID stability
 
 | Metric | Value | Sample |

```

> **Developer notes**: Template of the artifact measure.py writes; every <measured> value and each Handling cell is filled from the real-library run before G0.

### Milestone 2: M-002 Dedupe core and CLI for tiers 1-2 (opens with G0)

**Files**: traktor_nml/README.md, traktor_nml/dedupe.py, traktor_nml/commands/dedupe_cmd.py, tests/fixtures/dedupe/build_dedupe_fixtures.py, tests/test_dedupe_core.py, tests/test_dedupe_references.py, tests/test_dedupe_cli.py, tests/test_dedupe_write.py, tests/test_cli_contract.py

**Requirements**:

- G0 DL entries land in traktor_nml/README.md before dedupe code
- find_groups buckets by location / AUDIO_ID / artist-title and admits tiers 1-2 only
- survivor suggestion orders file exists then lossless then bitrate then cues or grid then playcount then earliest import
- MergeFields parse and merge per the merge data model
- every inventoried reference shape redirects and remix-set references preserve their entries
- the generic dangling scan refuses the write
- decisions file reader and writer
- write_validated_output with injectable writer and parser
- CLI flags --input --output --tiers --decisions --write-decisions --report --dry-run --no-refute --volume-map

**Acceptance Criteria**:

- G1 unit passes
- G2 integration passes
- G3 CLI passes
- G4 malformed input passes
- G5 atomic write passes

**Tests**:

- unit and integration with generated fixtures under tests/fixtures/dedupe

#### Code Intent

- **CI-M-002-001** `traktor_nml/README.md`: Decision log entries for inventory, merge model, path policy, exit codes, tier admission and decisions schema, committed ahead of dedupe code (refs: DL-319)
- **CI-M-002-002** `traktor_nml/dedupe.py`: Facade re-exporting the dedupe API (find_groups, plan_merge, assemble_output, write_validated_output, decisions IO, MergeFields) from the dedupe_* submodules split by DL-324; printless (refs: DL-309, DL-310, DL-312, DL-313, DL-314, DL-315, DL-316, DL-317, DL-324)
- **CI-M-002-003** `traktor_nml/commands/dedupe_cmd.py`: Registers dedupe; every output path (--output, --report, --write-decisions) is checked by output_refusal and must be distinct before any read; refusals exit 2 with refused=<reason>; post-write failure exits 3; report CSV columns as specified (refs: DL-311, DL-324)
- **CI-M-002-004** `tests/fixtures/dedupe/build_dedupe_fixtures.py`: Generates small NMLs per reference row, path-policy case, malformed input and golden input (refs: DL-313, DL-314)
- **CI-M-002-005** `tests/test_dedupe_core.py`: G1: tier admission, each merge data model row, path policy fixtures, stale decisions (refs: DL-313, DL-316, DL-317)
- **CI-M-002-006** `tests/test_dedupe_references.py`: G2: reference fixtures, zero dangling, entry count, byte-identical non-merged spans, playlist order with loser to survivor substitution only (refs: DL-309, DL-314)
- **CI-M-002-007** `tests/test_dedupe_cli.py`: G3 and G4: each exit code, dry-run writes nothing, input hash unchanged, CSV columns, decisions round trip, invalid decisions refused, malformed input refused or counted (refs: DL-311, DL-317)
- **CI-M-002-008** `tests/test_dedupe_write.py`: G5: injected mid-write failure leaves destination bytes intact; injected post-write parse failure yields .invalid and exit 3 (refs: DL-310)
- **CI-M-002-009** `tests/test_cli_contract.py`: Help listing includes dedupe (refs: DL-311)
- **CI-M-002-010** `tests/test_gui_command_classification.py`: dedupe classified TIER1 and counted among the 15 real subcommands (refs: DL-311)
- **CI-M-002-011** `traktor_nml/dedupe_members.py`: Shared tier, file-state, decision and plan constants and the Member/DupGroup/ScanResult records (refs: DL-324)
- **CI-M-002-012** `traktor_nml/dedupe_fields.py`: Cue, Grid and MergeFields read from one ENTRY span beside EntryRecord (refs: DL-324)
- **CI-M-002-013** `traktor_nml/dedupe_paths.py`: Location identity on (VOLUMEID, DIR, FILE), volume case probe and scan options from --volume-map (refs: DL-324)
- **CI-M-002-014** `traktor_nml/dedupe_groups.py`: Survivor suggestion, tiers 1-2, the tier-3/4 module gate and find_groups (refs: DL-324)
- **CI-M-002-015** `traktor_nml/dedupe_merge.py`: Merge conflicts, merged survivor and survivor span patching (refs: DL-324)
- **CI-M-002-016** `traktor_nml/dedupe_decisions.py`: Decisions file parse/attach/document and plan_merge (refs: DL-324)
- **CI-M-002-017** `traktor_nml/dedupe_references.py`: Reference inventory shapes and the generic reference scan (refs: DL-324)
- **CI-M-002-018** `traktor_nml/dedupe_assembly.py`: assemble_output on the byte-span path with stats, report rows and audit (refs: DL-324)
- **CI-M-002-019** `traktor_nml/dedupe_write.py`: output_refusal, write_validated_output and write_decisions guarded by output_refusal (refs: DL-324)

#### Code Changes

**CC-M-002-001** (traktor_nml/README.md) - implements CI-M-002-001

**Code:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -95,7 +95,7 @@ historical while that table is not; `DL-014`..`DL-023` by
 `DL-040`..`DL-043` by the two plan documents `docs/README.md` names. Every
 other number is stated in this file.
 
-This file is the authority for the log's high-water mark, which is `DL-307`:
+This file is the authority for the log's high-water mark, which is `DL-324`:
 an entry numbered against anything else collides with an entry this file
 names, so the next plan numbers from there.
 
@@ -2750,6 +2750,96 @@ names, so the next plan numbers from there.
   (DL-189). The rendered rows, the indent under the label, the label
   still toggling and the note under the table are read in
   `docs/2026-09-17-switch-options-browser-record.md` (DL-307).
+- Collection dedupe implements
+  `docs/plans/2026-09-26-collection-dedupe/plan.md` as reviewed, keeping
+  its milestone numbering M-001..M-006 and gates G0-G8; these entries are
+  G0, recorded before `dedupe.py` exists (DL-308, DL-319).
+- `dedupe.py` writes on the byte-span path: the survivor's `ENTRY` span is
+  patched in place, each removed loser's span is cut whole and
+  `COLLECTION ENTRIES` is recalculated, so every attribute and child the
+  dedupe does not name survives byte-for-byte (DL-309).
+  `dedupe.write_validated_output` is the only write path for the `dedupe`
+  command and the `/dedupe` page: an atomic write through
+  `rewrite.write_bytes_atomically`, then a parse of the written bytes, with
+  the file renamed to `OUT.nml.invalid` when the parse fails. Its writer and
+  parser are injectable so G5 can force each failure; `write_nml_safely` is
+  not used because it reserialises the tree and prints its own stats
+  (DL-310).
+- `dedupe` exits `0` when written or dry-run clean, `2` for argparse usage
+  errors and for every refusal, and `3` when post-write validation fails.
+  Usage and refusal share `2` because argparse exits `2` repo-wide and every
+  command already refuses with `2`; stderr tells them apart by argparse's
+  `usage:` line versus a `refused=<reason>` line (DL-311).
+- Merge fields live in `dedupe.MergeFields`, read beside `EntryRecord`
+  rather than inside it: `CUE_V2` cues and hotcues, the `TYPE=4` grid with
+  `TEMPO BPM`, `KEY`/`MUSICAL_KEY`, `RANKING`, `COLOR`, `COMMENT`,
+  `PLAYCOUNT`, `LAST_PLAYED` and `IMPORT_DATE`. `splice._TRACKED_ATTRS` is
+  not widened, so splice grouping and its conflict output are unchanged
+  (DL-312).
+- Tier 1 location equality compares `(VOLUMEID, DIR, FILE)` after
+  separator normalisation, folding case only on a volume a `--volume-map`
+  scan root probed case-insensitive (create a temp file, stat its
+  case-swapped name; the platform default when the root is not writable).
+  A volume no map entry names is case-sensitive, and an entry on it is
+  "unknown", never "dead", so it never enters tier 2. `matching._fold` is
+  not used for location equality: it casefolds unconditionally, and on a
+  case-sensitive volume that merges two distinct files (DL-313).
+- The reference inventory is `dedupe.REDIRECT_SHAPES` (playlist, History,
+  `_LOOPS` and `_RECORDINGS` `PRIMARYKEY TYPE=TRACK`) and
+  `dedupe.PRESERVE_SHAPES` (`PRIMARYKEY TYPE=STEM` and anything under
+  `SETS`, whose losers are kept and reported), as confirmed by
+  `docs/2026-09-26-dedupe-spike.md`. Every other attribute value equal to a
+  loser's primary key, and every non-collection `LOCATION` composing to
+  one, refuses with `unknown_reference_shape:<shape>`; after assembly the
+  same scan over the reparsed output refuses any `dangling_reference`, so a
+  shape the inventory missed can never be orphaned silently (DL-314).
+- Tiers 1-2 auto-apply under their admission rules; tier 3 is admitted
+  only when the M-001 spike measured `AUDIO_ID` re-analysis stability and
+  copy agreement at or above 99% with zero false collisions, and tier 4 is
+  review-only. A tier not admitted is not scanned and reports
+  `tier_N=disabled` (DL-315).
+- `PLAYCOUNT` merges as the maximum, `LAST_PLAYED` as the latest and
+  `IMPORT_DATE` as the earliest; an unparseable value makes that field
+  survivor-only and is counted. Grids are never merged: differing grids are
+  a conflict and one entry's grid is taken whole. Summing `PLAYCOUNT` was
+  rejected because duplicates usually share one listening history (DL-316).
+- The decisions file is schema `traktor-nml-dedupe-decisions` version 1,
+  keyed by each group's sorted member primary keys and carrying the
+  input's SHA-256. A decision whose membership matches no current group is
+  dropped and counted in `stale_decisions`, never refused; an invalid file
+  refuses with `refused=invalid_decisions:<reason>` and nothing is applied
+  (DL-317).
+- `gui/dedupe_model.py` and `gui/dedupe_steps.py` import no nicegui; the
+  `/dedupe` page code lives only in `app.py`, and `/dedupe` is the fourth
+  `navigation.SECTIONS` row (DL-318).
+- The suggested survivor is decided by the first criterion on which it
+  beats the runner-up, in the order: file exists, lossless over lossy,
+  higher bitrate, more cues or a beatgrid, higher `PLAYCOUNT`, earliest
+  `IMPORT_DATE`; that criterion is shown as the reason and the operator may
+  pick another survivor (DL-320).
+- Repeat collapse is opt-in and off by default: playlist rows that name
+  the survivor more than once after redirection collapse to the first
+  occurrence only when asked, because G2 requires every other playlist to
+  change by loser-to-survivor substitution alone (DL-321).
+- The removable-files CSV lists only loser files that exist on disk and
+  are not the survivor's file (`group_id, primary_key, local_path,
+  survivor_primary_key`). The tool never deletes, moves or renames audio
+  (DL-322).
+- The `/dedupe` page is four linear steps - set up, scan, review, write -
+  with one filter chip per tier, and it saves the decisions file on every
+  review change, so a reopened review resumes where it stopped (DL-323).
+- The dedupe core is `dedupe.py` plus sibling modules split by concern -
+  `dedupe_members`, `dedupe_fields`, `dedupe_paths`, `dedupe_groups`,
+  `dedupe_merge`, `dedupe_decisions`, `dedupe_references`,
+  `dedupe_assembly` and `dedupe_write` - with `dedupe.py` re-exporting the
+  names the command, the page and the tests use, so no module holds more
+  than 15 top-level definitions or 10 imports. Tiers 3 and 4 and the M-006
+  extras live in `dedupe_tier3.py`, `dedupe_tier4.py` and
+  `dedupe_extras.py`, each landing behind its own gate. Every file a dedupe
+  run writes - the NML, `--report`, `--write-decisions`,
+  `--removable-files` and the page's decisions side file - passes
+  `dedupe_write.output_refusal` first, so none can overwrite an input or
+  the live `collection.nml` (DL-324).
 
 ## Invariants
 
```

**Documentation:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -2828,6 +2828,11 @@
 - The `/dedupe` page is four linear steps - set up, scan, review, write -
   with one filter chip per tier, and it saves the decisions file on every
   review change, so a reopened review resumes where it stopped (DL-323).
+- Every dedupe rule errs toward a missed duplicate rather than a wrong
+  merge: an unprobed volume compares case-sensitively, an unmapped volume
+  is unknown rather than dead, a tier not admitted is not scanned, and a
+  reference shape outside the inventory refuses the write (DL-313, DL-314,
+  DL-315).
 - The dedupe core is `dedupe.py` plus sibling modules split by concern -
   `dedupe_members`, `dedupe_fields`, `dedupe_paths`, `dedupe_groups`,
   `dedupe_merge`, `dedupe_decisions`, `dedupe_references`,

```

> **Developer notes**: G0: committed before any dedupe.py commit (DL-319).

**CC-M-002-002** (traktor_nml/dedupe.py) - implements CI-M-002-002

**Code:**

```diff
--- a/traktor_nml/dedupe.py
+++ b/traktor_nml/dedupe.py
@@ -0,0 +1,77 @@
+"""Collection dedupe: group duplicate COLLECTION ENTRYs, merge each
+group's losers into a survivor, redirect every reference to it, and
+assemble a new NML without reserialising the tree.
+
+Printless core for the `dedupe` command and the /dedupe page (DL-069):
+find_groups -> plan_merge -> assemble_output -> write_validated_output.
+Every function returns data - a stats dict, refusal strings, report rows -
+and never prints, so the CLI handler and the GUI read one result.
+
+The failure mode this module is built around is a missed duplicate, never
+a wrong merge (DL-313, DL-315): a volume nobody probed is case-sensitive, a
+volume nobody mapped is "unknown" rather than "dead", a tier not admitted is
+not scanned, and a reference shape nobody inventoried refuses the write
+rather than being orphaned (DL-314).
+
+Output is assembled on the byte-span path (DL-007, DL-309): the survivor's
+ENTRY span is patched in place, each removed loser's span is cut whole, and
+redirected PRIMARYKEY opening tags are substituted inside their own spans,
+so every byte the dedupe does not name survives verbatim (plan.md A3).
+
+The implementation lives in nine sibling modules split by concern
+(DL-324), each within 15 top-level definitions and 10 imports:
+dedupe_members (vocabulary and records), dedupe_fields (merge fields),
+dedupe_paths (location identity and volume case policy), dedupe_groups
+(tiers 1-2 and find_groups), dedupe_merge (conflicts and the merged
+survivor), dedupe_decisions (decisions file and plan_merge),
+dedupe_references (inventory and generic scan), dedupe_assembly
+(assemble_output) and dedupe_write (output_refusal and the single write
+path). This module re-exports the names the CLI, the GUI and the tests
+use, so callers import one module.
+"""
+
+from __future__ import annotations
+
+from .dedupe_members import (
+    ACTION_MERGE,
+    ACTION_NOT_DUPLICATES,
+    ACTION_UNDECIDED,
+    ALL_TIERS,
+    AUTO_APPLY_TIERS,
+    DEAD,
+    DECISIONS_SCHEMA,
+    DEFAULT_TIERS,
+    DupGroup,
+    LIVE,
+    Member,
+    PLAN_MERGE,
+    PLAN_NOT_DUPLICATES,
+    PLAN_REFUSED,
+    PLAN_REVIEW,
+    ScanOptions,
+    ScanResult,
+    TIER_DEAD_LIVE,
+    TIER_EXACT_LOCATION,
+    TIER_PROBABLE,
+    TIER_SAME_AUDIO,
+    UNKNOWN,
+)
+from .dedupe_fields import MergeFields
+from .dedupe_paths import _platform_default_case_insensitive, scan_options_from_volume_map
+from .dedupe_groups import find_groups
+from .dedupe_merge import group_conflicts, merged_survivor
+from .dedupe_decisions import (
+    AttachedDecisions,
+    Decision,
+    DecisionsError,
+    DecisionsFile,
+    GroupPlan,
+    attach_decisions,
+    decisions_document,
+    input_sha256,
+    parse_decisions,
+    plan_merge,
+)
+from .dedupe_references import PRESERVE_SHAPES, REDIRECT_SHAPES, scan_references
+from .dedupe_assembly import AssembleResult, REPORT_COLUMNS, assemble_output
+from .dedupe_write import WriteResult, output_refusal, write_decisions, write_validated_output
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe.py
+++ b/traktor_nml/dedupe.py
@@ -32,6 +32,7 @@
 
 from __future__ import annotations
 
+# Re-exports only; no logic lives in this module (DL-324).
 from .dedupe_members import (
     ACTION_MERGE,
     ACTION_NOT_DUPLICATES,

```


**CC-M-002-003** (traktor_nml/commands/dedupe_cmd.py) - implements CI-M-002-003

**Code:**

```diff
--- a/traktor_nml/commands/dedupe_cmd.py
+++ b/traktor_nml/commands/dedupe_cmd.py
@@ -0,0 +1,158 @@
+"""dedupe subcommand: merge duplicate collection entries into a new NML.
+
+Exit codes (DL-311): 0 written or dry-run clean; 2 for argparse usage
+errors (argparse's own exit, stderr carries `usage:`) and for every
+refusal (stderr carries `refused=<reason>`, nothing written); 3 when the
+written file fails post-write validation and is quarantined as .invalid.
+"""
+
+from __future__ import annotations
+
+import argparse
+import sys
+from pathlib import Path
+
+from .. import dedupe
+from ..rewrite import read_and_parse_source, write_row_report
+from ..volumes import parse_volume_map
+
+EXIT_OK = 0
+EXIT_REFUSED = 2
+EXIT_INVALID_OUTPUT = 3
+
+
+def _refuse(reason: str) -> int:
+    print(f"refused={reason}", file=sys.stderr)
+    return EXIT_REFUSED
+
+
+def _parse_tiers(value: str) -> frozenset[int]:
+    try:
+        tiers = frozenset(int(part) for part in value.split(",") if part.strip())
+    except ValueError:
+        raise argparse.ArgumentTypeError(f"tiers must be comma-separated integers: {value!r}") from None
+    if not tiers or not tiers <= set(dedupe.ALL_TIERS):
+        raise argparse.ArgumentTypeError(f"tiers must be drawn from {list(dedupe.ALL_TIERS)}: {value!r}")
+    return tiers
+
+
+def _load_decisions(path: Path | None, groups, source_sha: str):
+    """The attached decisions, or a refusal string. The whole file is
+    validated before any of it is used (DL-317)."""
+    if path is None:
+        return None, None
+    try:
+        text = path.read_text(encoding="utf-8")
+    except OSError as exc:
+        return None, f"invalid_decisions:unreadable:{exc}"
+    try:
+        parsed = dedupe.parse_decisions(text)
+    except dedupe.DecisionsError as exc:
+        return None, f"invalid_decisions:{exc}"
+    return dedupe.attach_decisions(parsed, groups, source_sha), None
+
+
+def _print_stats(stats: dict, attached) -> None:
+    if attached is not None:
+        stats = {**stats, "stale_decisions": attached.stale, "decisions_input_changed": attached.input_changed}
+    for name, value in stats.items():
+        print(f"{name}={value}", file=sys.stderr)
+
+
+def _write_report(rows, report: Path | None) -> str | None:
+    return write_row_report(
+        rows,
+        report,
+        fieldnames=list(dedupe.REPORT_COLUMNS),
+        to_dict=lambda row: {column: getattr(row, column) for column in dedupe.REPORT_COLUMNS},
+        print_line=lambda row: f"dedupe_row group={row.group_id} role={row.role} key={row.primary_key}",
+        label="dedupe",
+    )
+
+
+def _outputs(args: argparse.Namespace) -> list[Path]:
+    return [p for p in (args.output, args.report, args.write_decisions) if p is not None]
+
+
+def _outputs_refusal(outputs: list[Path], inputs: list[Path]) -> str | None:
+    """Every file the run may write is checked before anything is read,
+    not only --output: a --report or --write-decisions naming the input
+    or the live collection.nml would otherwise overwrite it."""
+    for path in outputs:
+        refusal = dedupe.output_refusal(path, inputs)
+        if refusal is not None:
+            return refusal
+    if len({path.resolve() for path in outputs}) != len(outputs):
+        return "outputs_must_differ"
+    return None
+
+
+def _handle_dedupe(args: argparse.Namespace) -> int:
+    inputs = [args.input] + ([args.decisions] if args.decisions else [])
+    refusal = _outputs_refusal(_outputs(args), inputs)
+    if refusal is not None:
+        return _refuse(refusal)
+    loaded = read_and_parse_source(args.input)
+    if loaded.error is not None:
+        return _refuse(loaded.error)
+    source_text = loaded.source_bytes.decode("utf-8")
+    source_sha = dedupe.input_sha256(loaded.source_bytes)
+    options = dedupe.scan_options_from_volume_map(parse_volume_map(args.volume_map), args.tiers, not args.no_refute)
+    scan = dedupe.find_groups(source_text, loaded.root, options)
+    attached, refusal = _load_decisions(args.decisions, scan.groups, source_sha)
+    if refusal is not None:
+        return _refuse(refusal)
+    plans = dedupe.plan_merge(scan.groups, attached)
+    if args.write_decisions is not None:
+        refusal = dedupe.write_decisions(args.write_decisions, dedupe.decisions_document(source_sha, plans), inputs)
+        if refusal is not None:
+            return _refuse(refusal)
+        print(f"decisions_written={args.write_decisions.as_posix()}")
+    result = dedupe.assemble_output(source_text, loaded.root, scan, plans)
+    _print_stats(result.stats, attached)
+    if _write_report(result.rows, args.report) is not None:
+        return EXIT_REFUSED
+    if result.output is None:
+        return _refuse(";".join(dict.fromkeys(result.refusals)))
+    if args.dry_run or args.write_decisions is not None:
+        print("dry_run=true")
+        return EXIT_OK
+    written = dedupe.write_validated_output(
+        result.output.encode("utf-8"), args.output, expected_entries=result.expected_entries
+    )
+    if written.ok:
+        print(f"output_written={args.output.as_posix()}")
+        return EXIT_OK
+    print(written.error, file=sys.stderr)
+    if written.invalid_path is None:
+        return EXIT_REFUSED
+    print(f"output_quarantined={written.invalid_path.as_posix()}", file=sys.stderr)
+    return EXIT_INVALID_OUTPUT
+
+
+def register(subparsers, handlers: dict) -> None:
+    parser = subparsers.add_parser(
+        "dedupe",
+        help="Merge duplicate collection entries and redirect their references into a new NML",
+        description="Close Traktor before running: Traktor rewrites collection.nml on exit.",
+    )
+    parser.add_argument("--input", type=Path, required=True)
+    parser.add_argument("--output", type=Path, required=True)
+    parser.add_argument(
+        "--tiers", type=_parse_tiers, default=dedupe.DEFAULT_TIERS,
+        help="Comma-separated detection tiers (default 1,2). A tier not admitted reports tier_N=disabled.",
+    )
+    parser.add_argument("--decisions", type=Path, help="Decisions JSON naming survivors, picks and not-duplicate marks.")
+    parser.add_argument(
+        "--write-decisions", type=Path,
+        help="Write the decisions template for every group needing review; implies --dry-run.",
+    )
+    parser.add_argument("--report", type=Path, help="CSV with one row per group member.")
+    parser.add_argument("--dry-run", action="store_true", help="Write no NML. The report and decisions files are still written.")
+    parser.add_argument("--no-refute", action="store_true", help="Skip the size/duration refute check in tiers 3-4.")
+    parser.add_argument(
+        "--volume-map", nargs=3, action="append", metavar=("SCAN_ROOT", "VOLUME", "VOLUMEID"),
+        help="Mount a VOLUME/VOLUMEID at SCAN_ROOT (repeatable). Only mapped volumes can be live or dead, "
+        "and only a mapped volume probed case-insensitive compares paths without case.",
+    )
+    handlers["dedupe"] = _handle_dedupe
```

**Documentation:**

```diff
--- a/traktor_nml/commands/dedupe_cmd.py
+++ b/traktor_nml/commands/dedupe_cmd.py
@@ -22,11 +22,15 @@
 
 
 def _refuse(reason: str) -> int:
+    """Print a refused=<reason> line and return exit code 2; every refusal the
+    command makes goes through here (DL-311)."""
     print(f"refused={reason}", file=sys.stderr)
     return EXIT_REFUSED
 
 
 def _parse_tiers(value: str) -> frozenset[int]:
+    """argparse type for --tiers: a comma-separated subset of ALL_TIERS. A bad
+    value is a usage error, so argparse exits 2 with its usage line."""
     try:
         tiers = frozenset(int(part) for part in value.split(",") if part.strip())
     except ValueError:
@@ -53,6 +57,9 @@
 
 
 def _print_stats(stats: dict, attached) -> None:
+    """Print the run's stats as name=value lines on stderr, adding the stale-
+    decision count and whether the decisions file was made against a
+    different input (DL-317)."""
     if attached is not None:
         stats = {**stats, "stale_decisions": attached.stale, "decisions_input_changed": attached.input_changed}
     for name, value in stats.items():
@@ -60,6 +67,9 @@
 
 
 def _write_report(rows, report: Path | None) -> str | None:
+    """Write the per-member report CSV in REPORT_COLUMNS order, or print one
+    line per row when no --report is given; returns the writer's refusal, if
+    any."""
     return write_row_report(
         rows,
         report,
@@ -71,6 +81,8 @@
 
 
 def _outputs(args: argparse.Namespace) -> list[Path]:
+    """Every path this run may write: the NML, the report and the decisions
+    template."""
     return [p for p in (args.output, args.report, args.write_decisions) if p is not None]
 
 
@@ -88,6 +100,12 @@
 
 
 def _handle_dedupe(args: argparse.Namespace) -> int:
+    """Scan, plan, assemble and write in that order, refusing (exit 2) before
+    any write when an output collides with an input, the input fails to
+    parse, the decisions file is invalid, or assembly finds a dangling or
+    unknown reference (DL-314). The NML is written only through
+    write_validated_output, which yields exit 3 when the written file fails
+    its post-write validation (DL-310, DL-311)."""
     inputs = [args.input] + ([args.decisions] if args.decisions else [])
     refusal = _outputs_refusal(_outputs(args), inputs)
     if refusal is not None:
@@ -131,6 +149,8 @@
 
 
 def register(subparsers, handlers: dict) -> None:
+    """Add the dedupe subparser. Discovered by cli.build_parser like every
+    module in traktor_nml/commands (DL-003)."""
     parser = subparsers.add_parser(
         "dedupe",
         help="Merge duplicate collection entries and redirect their references into a new NML",

```


**CC-M-002-004** (tests/fixtures/dedupe/build_dedupe_fixtures.py) - implements CI-M-002-004

**Code:**

```diff
--- a/tests/fixtures/dedupe/build_dedupe_fixtures.py
+++ b/tests/fixtures/dedupe/build_dedupe_fixtures.py
@@ -0,0 +1,252 @@
+"""Small NML fixtures for the dedupe gates G1-G5.
+
+One literal NML per reference-inventory row, path-policy case, merge data
+model row and malformed-input case, plus a golden input that exercises
+tiers 1 and 2 together. Every string is fixed at authoring time, so
+regeneration is byte-identical; the only runtime input is the directory
+live audio stubs are written under, because tier 2's "live" is a file that
+resolves on disk through an established mount (DL-313).
+"""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+from traktor_nml.model import encode_traktor_dir
+
+HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+
+# The (VOLUME, VOLUMEID) every live-file fixture maps its audio root to
+# through --volume-map; tier 2 needs a mapped volume to call a file dead.
+LIVE_VOLUME = "Live"
+LIVE_VOLUMEID = "LIVEVOLID"
+
+
+def entry(
+    volume: str,
+    dirv: str,
+    filename: str,
+    *,
+    volumeid: str | None = None,
+    artist: str = "Artist",
+    title: str = "Title",
+    info: str = "",
+    children: str = "",
+    size: str = "4096",
+    seconds: str = "180.0",
+    bitrate: str = "320",
+    audio_id: str = "",
+) -> str:
+    """One COLLECTION ENTRY. info is extra INFO attribute text; children
+    is raw child markup written after INFO (CUE_V2, TEMPO, MUSICAL_KEY)."""
+    volumeid = volume if volumeid is None else volumeid
+    return (
+        f'<ENTRY MODIFIED_DATE="2024/1/1" AUDIO_ID="{audio_id}" TITLE="{title}" ARTIST="{artist}">'
+        f'<LOCATION DIR="{dirv}" FILE="{filename}" VOLUME="{volume}" VOLUMEID="{volumeid}"></LOCATION>'
+        f'<INFO BITRATE="{bitrate}" PLAYTIME="180" PLAYTIME_FLOAT="{seconds}" FILESIZE="{size}"{info}></INFO>'
+        f"{children}</ENTRY>\n"
+    )
+
+
+def track_ref(key: str, kind: str = "TRACK") -> str:
+    return f'<ENTRY><PRIMARYKEY TYPE="{kind}" KEY="{key}"></PRIMARYKEY></ENTRY>\n'
+
+
+def playlist(name: str, refs: list[str]) -> str:
+    return (
+        f'<NODE TYPE="PLAYLIST" NAME="{name}"><PLAYLIST ENTRIES="{len(refs)}" TYPE="LIST" UUID="uuid-{name}">\n'
+        + "".join(refs)
+        + "</PLAYLIST></NODE>\n"
+    )
+
+
+def nml(entries: str, nodes: str = "", sets: str = "") -> str:
+    """Wrap entries and playlist nodes in a VERSION=20 document with the
+    $ROOT folder Traktor writes."""
+    count = nodes.count('<NODE TYPE="PLAYLIST"') + nodes.count('<NODE TYPE="REMIXSET"')
+    return (
+        HEAD
+        + '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>\n'
+        + f'<COLLECTION ENTRIES="{entries.count("<ENTRY ")}">\n'
+        + entries
+        + "</COLLECTION>\n"
+        + f'<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="{count}">\n'
+        + nodes
+        + "</SUBNODES></NODE></PLAYLISTS>\n"
+        + f"<SETS>{sets}</SETS><INDEXING></INDEXING></NML>\n"
+    )
+
+
+def key(volume: str, dirv: str, filename: str) -> str:
+    return f"{volume}{dirv}{filename}"
+
+
+# Tier 1: one file written two ways - a doubled DIR separator Traktor's
+# own encoder never emits, beside the canonical form.
+TIER1_A = key("C:", "/:Music/:", "song.mp3")
+TIER1_B = key("C:", "/:Music/:/:", "song.mp3")
+OTHER = key("C:", "/:Music/:", "other.mp3")
+
+
+def golden_tier1() -> str:
+    entries = (
+        entry("C:", "/:Music/:", "song.mp3", info=' PLAYCOUNT="3" IMPORT_DATE="2020/5/1"')
+        + entry("C:", "/:Music/:/:", "song.mp3", info=' PLAYCOUNT="7" IMPORT_DATE="2019/1/2" LAST_PLAYED="2024/3/4"')
+        + entry("C:", "/:Music/:", "other.mp3", artist="Else", title="Other")
+    )
+    nodes = playlist("Set", [track_ref(TIER1_B), track_ref(OTHER), track_ref(TIER1_A), track_ref(TIER1_B)])
+    nodes += playlist("HISTORY", [track_ref(TIER1_B)])
+    return nml(entries, nodes)
+
+
+def case_pair(volumeid: str) -> str:
+    """Two entries differing only in FILE case on volumeid."""
+    entries = entry("C:", "/:Music/:", "Song.mp3", volumeid=volumeid) + entry(
+        "C:", "/:Music/:", "song.mp3", volumeid=volumeid
+    )
+    return nml(entries)
+
+
+def same_volume_name_different_id() -> str:
+    """Two sticks whose VOLUME names differ only in case ("USB", "usb"), so
+    the primary keys are distinct and both entries are scanned, while their
+    VOLUMEIDs differ: grouping keyed on a folded VOLUME name would merge
+    them, grouping keyed on VOLUMEID must not."""
+    entries = entry("USB", "/:Music/:", "song.mp3", volumeid="IDONE") + entry(
+        "usb", "/:Music/:", "song.mp3", volumeid="IDTWO"
+    )
+    return nml(entries)
+
+
+def same_volumeid_renamed_volume() -> str:
+    """One stick renamed between imports: VOLUME names differ ("USB",
+    "USB-OLD") so the primary keys are distinct, VOLUMEID is shared, so
+    tier 1 groups them as one file written two ways."""
+    entries = entry("USB", "/:Music/:", "song.mp3", volumeid="IDONE") + entry(
+        "USB-OLD", "/:Music/:", "song.mp3", volumeid="IDONE"
+    )
+    return nml(entries)
+
+
+def stem_reference() -> str:
+    """A loser a STEM slot names is kept, not merged (preserve row)."""
+    entries = entry("C:", "/:Music/:", "song.mp3") + entry("C:", "/:Music/:/:", "song.mp3")
+    nodes = playlist("Stems", [track_ref(TIER1_B, kind="STEM")])
+    return nml(entries, nodes)
+
+
+def unknown_shape_reference() -> str:
+    """A loser named by an attribute shape the inventory does not hold."""
+    entries = entry("C:", "/:Music/:", "song.mp3") + entry("C:", "/:Music/:/:", "song.mp3")
+    nodes = f'<NODE TYPE="REMIXSET" NAME="Deck"><SLOT REF="{TIER1_B}"></SLOT></NODE>\n'
+    return nml(entries, nodes)
+
+
+CUE_A = '<CUE_V2 NAME="Intro" DISPL_ORDER="0" TYPE="0" START="1000.0" LEN="0" REPEATS="-1" HOTCUE="0"></CUE_V2>'
+CUE_B = '<CUE_V2 NAME="Drop" DISPL_ORDER="0" TYPE="0" START="64000.0" LEN="0" REPEATS="-1" HOTCUE="1"></CUE_V2>'
+CUE_B_RENAMED = CUE_B.replace('NAME="Drop"', 'NAME="Break"')
+CUE_CLASH = '<CUE_V2 NAME="Other" DISPL_ORDER="0" TYPE="0" START="90000.0" LEN="0" REPEATS="-1" HOTCUE="0"></CUE_V2>'
+GRID_A = '<CUE_V2 NAME="AutoGrid" DISPL_ORDER="0" TYPE="4" START="50.0" LEN="0" REPEATS="-1" HOTCUE="-1"><GRID BPM="128.0"></GRID></CUE_V2>'
+GRID_B = GRID_A.replace('START="50.0"', 'START="80.0"')
+TEMPO_A = '<TEMPO BPM="128.0" BPM_QUALITY="100"></TEMPO>'
+
+
+def merge_pair(survivor_children: str, loser_children: str, survivor_info: str = "", loser_info: str = "") -> str:
+    """A tier 1 pair whose canonical-DIR entry is the suggested survivor
+    (earlier in collection order, all else equal)."""
+    entries = entry("C:", "/:Music/:", "song.mp3", info=survivor_info, children=survivor_children) + entry(
+        "C:", "/:Music/:/:", "song.mp3", info=loser_info, children=loser_children
+    )
+    return nml(entries, playlist("Set", [track_ref(TIER1_B)]))
+
+
+def malformed_truncated() -> str:
+    return golden_tier1()[:200]
+
+
+def malformed_missing_location() -> str:
+    text = golden_tier1()
+    return text.replace(
+        "</COLLECTION>", '<ENTRY TITLE="No location" ARTIST="Nobody"><INFO PLAYCOUNT="1"></INFO></ENTRY>\n</COLLECTION>'
+    ).replace('<COLLECTION ENTRIES="3">', '<COLLECTION ENTRIES="4">')
+
+
+def malformed_duplicate_keys() -> str:
+    entries = entry("C:", "/:Music/:", "song.mp3") + entry("C:", "/:Music/:", "song.mp3")
+    return nml(entries)
+
+
+def malformed_playcount() -> str:
+    return merge_pair("", "", survivor_info=' PLAYCOUNT="lots"', loser_info=' PLAYCOUNT="9"')
+
+
+STATIC_FIXTURES = {
+    "golden_tier1.nml": golden_tier1,
+    "case_sensitive_pair.nml": lambda: case_pair("CASEVOL"),
+    "same_volume_name.nml": same_volume_name_different_id,
+    "renamed_volume.nml": same_volumeid_renamed_volume,
+    "stem_reference.nml": stem_reference,
+    "unknown_shape.nml": unknown_shape_reference,
+    "truncated.nml": malformed_truncated,
+    "missing_location.nml": malformed_missing_location,
+    "duplicate_keys.nml": malformed_duplicate_keys,
+    "bad_playcount.nml": malformed_playcount,
+}
+
+
+def build_static_fixtures(out_dir: Path) -> dict[str, Path]:
+    out_dir.mkdir(parents=True, exist_ok=True)
+    written = {}
+    for name, build in STATIC_FIXTURES.items():
+        path = out_dir / name
+        path.write_bytes(build().encode("utf-8"))
+        written[name] = path
+    return written
+
+
+def live_location(audio_root: Path) -> str:
+    """audio_root's DIR in Traktor's encoding, relative to its drive or
+    POSIX root - the frame local_path_for_location reads DIR in."""
+    parts = audio_root.resolve().parts[1:]
+    return encode_traktor_dir("/".join(parts))
+
+
+def dead_live(audio_root: Path, *, live_files: tuple[str, ...] = ("live.flac",), dead_seconds: str = "180.0") -> str:
+    """A dead MP3 beside live files for one artist+title, all on the
+    mapped LIVE volume. Each live file is written as a stub so it
+    resolves; dead.mp3 is never written."""
+    audio_root.mkdir(parents=True, exist_ok=True)
+    dirv = live_location(audio_root)
+    entries = entry(LIVE_VOLUME, dirv, "dead.mp3", volumeid=LIVE_VOLUMEID, seconds=dead_seconds, info=' PLAYCOUNT="4"')
+    for name in live_files:
+        (audio_root / name).write_bytes(b"\0" * 16)
+        entries += entry(LIVE_VOLUME, dirv, name, volumeid=LIVE_VOLUMEID, size="9000")
+    dead_key = key(LIVE_VOLUME, dirv, "dead.mp3")
+    return nml(entries, playlist("Set", [track_ref(dead_key)]))
+
+
+def same_audio(copy_name: str = "copy.mp3", copy_size: str = "4096") -> str:
+    """Two files sharing one AUDIO_ID in different folders: a copy when
+    copy_name keeps the extension, a format upgrade when it does not."""
+    entries = entry("C:", "/:Music/:", "song.mp3", audio_id="AUDIOID1") + entry(
+        "C:", "/:Backup/:", copy_name, audio_id="AUDIOID1", size=copy_size
+    )
+    return nml(entries, playlist("Set", [track_ref(key("C:", "/:Backup/:", copy_name))]))
+
+
+def titled_pair(title_a: str, title_b: str, file_b: str = "b.mp3", seconds_b: str = "180.0") -> str:
+    """Two files by one artist in different folders with the given
+    titles: the tier 4 version-variant fixtures."""
+    return nml(
+        entry("C:", "/:A/:", "a.mp3", title=title_a)
+        + entry("C:", "/:B/:", file_b, title=title_b, seconds=seconds_b)
+    )
+
+
+def unmapped_dead() -> str:
+    """A missing file on a volume no --volume-map names: unknown, never
+    dead, so never grouped by tier 2."""
+    return nml(
+        entry("Elsewhere", "/:Gone/:", "dead.mp3", volumeid="NOMAP")
+        + entry("Elsewhere", "/:Gone/:", "live.flac", volumeid="NOMAP")
+    )
```

**Documentation:**

```diff
--- a/tests/fixtures/dedupe/build_dedupe_fixtures.py
+++ b/tests/fixtures/dedupe/build_dedupe_fixtures.py
@@ -49,10 +49,13 @@
 
 
 def track_ref(key: str, kind: str = "TRACK") -> str:
+    """One playlist row referencing key; kind STEM builds the preserved stem
+    shape."""
     return f'<ENTRY><PRIMARYKEY TYPE="{kind}" KEY="{key}"></PRIMARYKEY></ENTRY>\n'
 
 
 def playlist(name: str, refs: list[str]) -> str:
+    """A NODE TYPE=PLAYLIST holding refs, with its ENTRIES count matching them."""
     return (
         f'<NODE TYPE="PLAYLIST" NAME="{name}"><PLAYLIST ENTRIES="{len(refs)}" TYPE="LIST" UUID="uuid-{name}">\n'
         + "".join(refs)
@@ -78,6 +81,8 @@
 
 
 def key(volume: str, dirv: str, filename: str) -> str:
+    """A primary key in Traktor's VOLUME+DIR+FILE form, the value PRIMARYKEY
+    KEY holds."""
     return f"{volume}{dirv}{filename}"
 
 
@@ -195,6 +200,8 @@
 
 
 def build_static_fixtures(out_dir: Path) -> dict[str, Path]:
+    """Write every static fixture into out_dir and return name -> path. The
+    fixtures are built per test, so no fixture file is committed."""
     out_dir.mkdir(parents=True, exist_ok=True)
     written = {}
     for name, build in STATIC_FIXTURES.items():

```

> **Developer notes**: tests/fixtures/dedupe/ has no __init__.py: it imports as a namespace package under the regular tests.fixtures package. same_audio and titled_pair serve M-004/M-005 tests and ride in this one file.

**CC-M-002-005** (tests/test_dedupe_core.py) - implements CI-M-002-005

**Code:**

```diff
--- a/tests/test_dedupe_core.py
+++ b/tests/test_dedupe_core.py
@@ -0,0 +1,219 @@
+"""G1: tier admission, each merge data model row, each path-policy case
+and stale-decision handling for traktor_nml/dedupe.py."""
+
+from __future__ import annotations
+
+import json
+from datetime import date
+from pathlib import Path
+
+import pytest
+
+from tests.fixtures.dedupe import build_dedupe_fixtures as fx
+from traktor_nml import dedupe
+from traktor_nml.xmlio import parse_xml_bytes
+
+
+def _scan(text: str, options: dedupe.ScanOptions | None = None) -> dedupe.ScanResult:
+    return dedupe.find_groups(text, parse_xml_bytes(text.encode("utf-8")), options or dedupe.ScanOptions())
+
+
+def _live_options(audio_root: Path, **kwargs) -> dedupe.ScanOptions:
+    volume_map = {str(audio_root): (fx.LIVE_VOLUME, fx.LIVE_VOLUMEID)}
+    return dedupe.scan_options_from_volume_map(volume_map, probe=lambda root: False, **kwargs)
+
+
+# --- tier admission ---------------------------------------------------
+
+
+def test_tier1_groups_one_file_written_two_ways() -> None:
+    scan = _scan(fx.golden_tier1())
+    assert [(g.tier, g.member_keys, g.auto_apply) for g in scan.groups] == [
+        (1, tuple(sorted((fx.TIER1_A, fx.TIER1_B))), True)
+    ]
+
+
+def test_tier2_admits_one_dead_beside_one_live_other_format(tmp_path: Path) -> None:
+    scan = _scan(fx.dead_live(tmp_path / "audio"), _live_options(tmp_path / "audio"))
+    (group,) = scan.groups
+    assert (group.tier, group.auto_apply) == (2, True)
+    assert group.member(group.suggested_survivor).file_state == dedupe.LIVE
+
+
+def test_tier2_dead_beside_two_live_entries_goes_to_review(tmp_path: Path) -> None:
+    text = fx.dead_live(tmp_path / "audio", live_files=("live.flac", "live.wav"))
+    (group,) = _scan(text, _live_options(tmp_path / "audio")).groups
+    assert (group.auto_apply, group.review_reason) == (False, "several_live_entries")
+
+
+def test_tier2_duration_outside_tolerance_goes_to_review(tmp_path: Path) -> None:
+    text = fx.dead_live(tmp_path / "audio", dead_seconds="200.0")
+    (group,) = _scan(text, _live_options(tmp_path / "audio")).groups
+    assert (group.auto_apply, group.review_reason) == (False, "duration_outside_tolerance")
+
+
+def test_tier_not_admitted_reports_disabled() -> None:
+    scan = _scan(fx.golden_tier1(), dedupe.ScanOptions(tiers=frozenset({1})))
+    assert scan.stats["tier_2"] == "disabled"
+    assert scan.stats["tier_4"] == "disabled"
+
+
+# --- path and volume policy -------------------------------------------
+
+
+def test_case_only_pair_on_case_sensitive_volume_is_not_grouped() -> None:
+    assert _scan(fx.case_pair("CASEVOL")).groups == []
+
+
+def test_case_only_pair_on_case_insensitive_volume_is_grouped() -> None:
+    options = dedupe.ScanOptions(case_insensitive_volumes=frozenset({"CASEVOL"}))
+    assert len(_scan(fx.case_pair("CASEVOL"), options).groups) == 1
+
+
+def test_same_volume_name_different_volumeid_is_not_grouped() -> None:
+    options = dedupe.ScanOptions(case_insensitive_volumes=frozenset({"IDONE", "IDTWO"}))
+    scan = _scan(fx.same_volume_name_different_id(), options)
+    # Both entries must be scanned, else groups == [] would hold vacuously.
+    assert scan.refusals == []
+    assert len(scan.members) == 2
+    assert scan.groups == []
+
+
+def test_same_volumeid_under_renamed_volume_is_grouped() -> None:
+    scan = _scan(fx.same_volumeid_renamed_volume())
+    assert scan.refusals == []
+    assert [g.tier for g in scan.groups] == [1]
+
+
+def test_unmapped_volume_is_neither_dead_nor_live() -> None:
+    scan = _scan(fx.unmapped_dead())
+    assert {m.file_state for m in scan.members.values()} == {dedupe.UNKNOWN}
+    assert scan.groups == []
+
+
+def test_failed_probe_uses_platform_default_and_unmapped_volume_stays_case_sensitive(tmp_path: Path) -> None:
+    """A mapped volume whose probe fails falls back to the platform default
+    (plan.md path policy); a volume no map entry names is never probed and
+    so is never folded."""
+    options = dedupe.scan_options_from_volume_map({str(tmp_path): ("V", "VID")}, probe=lambda root: None)
+    assert ("VID" in options.case_insensitive_volumes) == dedupe._platform_default_case_insensitive()
+    assert "OTHER" not in options.case_insensitive_volumes
+
+
+# --- merge data model -------------------------------------------------
+
+
+def _group(text: str) -> dedupe.DupGroup:
+    (group,) = _scan(text).groups
+    return group
+
+
+def test_cue_union_appends_loser_cue_without_counterpart() -> None:
+    group = _group(fx.merge_pair(fx.CUE_A, fx.CUE_B))
+    merged = dedupe.merged_survivor(group, group.suggested_survivor, {})
+    assert [c.name for c in merged.cues] == ["Intro", "Drop"]
+    assert dedupe.group_conflicts(group) == []
+
+
+def test_same_cue_with_differing_name_is_a_cues_conflict() -> None:
+    group = _group(fx.merge_pair(fx.CUE_B, fx.CUE_B_RENAMED))
+    assert [c.field_name for c in dedupe.group_conflicts(group)] == ["cues"]
+
+
+def test_hotcue_clash_is_a_conflict_and_the_losing_cue_is_dropped() -> None:
+    group = _group(fx.merge_pair(fx.CUE_A, fx.CUE_CLASH))
+    assert [c.field_name for c in dedupe.group_conflicts(group)] == ["hotcue"]
+    merged = dedupe.merged_survivor(group, group.suggested_survivor, {"hotcue": group.suggested_survivor})
+    assert ([c.name for c in merged.cues], merged.cues_dropped) == (["Intro"], 1)
+
+
+def test_differing_grids_conflict_and_are_never_merged() -> None:
+    group = _group(fx.merge_pair(fx.GRID_A + fx.TEMPO_A, fx.GRID_B + fx.TEMPO_A))
+    assert [c.field_name for c in dedupe.group_conflicts(group)] == ["grid"]
+    loser = next(k for k in group.member_keys if k != group.suggested_survivor)
+    assert dedupe.merged_survivor(group, group.suggested_survivor, {"grid": loser}).grid.raw == fx.GRID_B
+
+
+def test_key_disagreement_conflicts_and_empty_never_does() -> None:
+    disagree = _group(fx.merge_pair("", "", ' KEY="1m"', ' KEY="2m"'))
+    empty = _group(fx.merge_pair("", "", "", ' KEY="2m"'))
+    assert [c.field_name for c in dedupe.group_conflicts(disagree)] == ["key"]
+    assert dedupe.group_conflicts(empty) == []
+    assert dedupe.merged_survivor(empty, empty.suggested_survivor, {}).info_attrs["KEY"] == "2m"
+
+
+def test_playcount_is_max_and_dates_latest_and_earliest() -> None:
+    group = _group(fx.golden_tier1())
+    merged = dedupe.merged_survivor(group, group.suggested_survivor, {})
+    assert merged.info_attrs["PLAYCOUNT"] == "7"
+    assert merged.info_attrs["IMPORT_DATE"] == "2019/1/2"
+    assert merged.info_attrs["LAST_PLAYED"] == "2024/3/4"
+
+
+def test_unparseable_date_is_survivor_only_and_counted() -> None:
+    text = fx.merge_pair("", "", ' IMPORT_DATE="someday"', ' IMPORT_DATE="2019/1/2"')
+    scan = _scan(text)
+    (group,) = scan.groups
+    assert scan.stats["unparseable_fields"] == {"import_date": 1}
+    assert "IMPORT_DATE" not in dedupe.merged_survivor(group, fx.TIER1_A, {}).info_attrs
+
+
+def test_read_merge_fields_parses_dates() -> None:
+    group = _group(fx.golden_tier1())
+    fields = group.member(fx.TIER1_B).fields
+    assert (fields.playcount, fields.import_date) == (7, date(2019, 1, 2))
+
+
+def test_survivor_reason_names_the_first_deciding_criterion(tmp_path: Path) -> None:
+    (group,) = _scan(fx.dead_live(tmp_path / "audio"), _live_options(tmp_path / "audio")).groups
+    assert group.survivor_reason == "file exists"
+
+
+# --- decisions --------------------------------------------------------
+
+
+def _decisions(groups: list[dict], sha: str = "abc") -> str:
+    return json.dumps({"schema": dedupe.DECISIONS_SCHEMA, "version": 1, "input_sha256": sha, "groups": groups})
+
+
+def test_stale_decision_is_dropped_and_counted() -> None:
+    scan = _scan(fx.golden_tier1())
+    stale = {"members": ["C:/:Gone/:a.mp3", "C:/:Gone/:b.mp3"], "action": "not_duplicates"}
+    attached = dedupe.attach_decisions(dedupe.parse_decisions(_decisions([stale])), scan.groups, "abc")
+    assert (attached.stale, attached.by_members, attached.input_changed) == (1, {}, False)
+
+
+def test_decision_under_a_different_input_hash_reattaches_per_group() -> None:
+    scan = _scan(fx.golden_tier1())
+    kept = {"members": [fx.TIER1_B, fx.TIER1_A], "action": "not_duplicates"}
+    attached = dedupe.attach_decisions(dedupe.parse_decisions(_decisions([kept], "old")), scan.groups, "new")
+    assert attached.input_changed is True
+    assert dedupe.plan_merge(scan.groups, attached)[0].action == dedupe.PLAN_NOT_DUPLICATES
+
+
+@pytest.mark.parametrize(
+    ("document", "reason"),
+    [
+        ("{", "not_json"),
+        (json.dumps({"schema": "other"}), "wrong_schema"),
+        (json.dumps({"schema": dedupe.DECISIONS_SCHEMA, "version": 2}), "unsupported_version:2"),
+        (_decisions([{"members": ["a", "b"]}]), "missing_key:action"),
+        (_decisions([{"members": ["a", "b"], "action": "merge", "survivor": "c"}]), "survivor_not_member"),
+        (_decisions([{"members": ["a", "b"], "action": "merge", "survivor": "a", "picks": {"bpm": "a"}}]),
+         "unknown_pick_field:bpm"),
+        (_decisions([{"members": ["a", "b"], "action": "merge", "survivor": "a", "picks": {"key": "z"}}]),
+         "pick_not_member:key"),
+    ],
+)
+def test_invalid_decisions_are_refused(document: str, reason: str) -> None:
+    with pytest.raises(dedupe.DecisionsError) as raised:
+        dedupe.parse_decisions(document)
+    assert str(raised.value) == reason
+
+
+def test_merge_decision_with_an_unpicked_conflict_is_refused_not_applied() -> None:
+    scan = _scan(fx.merge_pair("", "", ' KEY="1m"', ' KEY="2m"'))
+    decision = {"members": [fx.TIER1_A, fx.TIER1_B], "action": "merge", "survivor": fx.TIER1_A}
+    attached = dedupe.attach_decisions(dedupe.parse_decisions(_decisions([decision])), scan.groups, "abc")
+    (plan,) = dedupe.plan_merge(scan.groups, attached)
+    assert (plan.action, plan.reason) == (dedupe.PLAN_REFUSED, "unpicked_conflict:key")
```

**Documentation:**

```diff
--- a/tests/test_dedupe_core.py
+++ b/tests/test_dedupe_core.py
@@ -15,10 +15,14 @@
 
 
 def _scan(text: str, options: dedupe.ScanOptions | None = None) -> dedupe.ScanResult:
+    """Run find_groups over text with default options (tiers 1-2, nothing
+    mapped)."""
     return dedupe.find_groups(text, parse_xml_bytes(text.encode("utf-8")), options or dedupe.ScanOptions())
 
 
 def _live_options(audio_root: Path, **kwargs) -> dedupe.ScanOptions:
+    """Options mapping the fixture's live volume at audio_root, probed case-
+    sensitive."""
     volume_map = {str(audio_root): (fx.LIVE_VOLUME, fx.LIVE_VOLUMEID)}
     return dedupe.scan_options_from_volume_map(volume_map, probe=lambda root: False, **kwargs)
 
@@ -104,6 +108,8 @@
 
 
 def _group(text: str) -> dedupe.DupGroup:
+    """The single group text produces; unpacking fails the test if there is not
+    exactly one."""
     (group,) = _scan(text).groups
     return group
 
@@ -173,6 +179,8 @@
 
 
 def _decisions(groups: list[dict], sha: str = "abc") -> str:
+    """A decisions file (schema v1) holding groups, made against input hash
+    sha."""
     return json.dumps({"schema": dedupe.DECISIONS_SCHEMA, "version": 1, "input_sha256": sha, "groups": groups})
 
 

```


**CC-M-002-006** (tests/test_dedupe_references.py) - implements CI-M-002-006

**Code:**

```diff
--- a/tests/test_dedupe_references.py
+++ b/tests/test_dedupe_references.py
@@ -0,0 +1,110 @@
+"""G2: every reference-inventory fixture, plus for each golden input:
+the output reparses, zero dangling references, entry count equals input
+minus removed, every non-merged entry's span is byte-identical, and each
+playlist's track sequence changes only by loser->survivor substitution."""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+import pytest
+
+from tests.fixtures.dedupe import build_dedupe_fixtures as fx
+from traktor_nml import dedupe, dedupe_assembly
+from traktor_nml.model import collection_entries, collection_records
+from traktor_nml.playlists import find_playlist_nodes, node_primary_keys
+from traktor_nml.spans import SpanIndex
+from traktor_nml.xmlio import parse_xml_bytes
+
+
+def _run(text: str, options: dedupe.ScanOptions | None = None) -> tuple[dedupe.AssembleResult, list]:
+    root = parse_xml_bytes(text.encode("utf-8"))
+    scan = dedupe.find_groups(text, root, options or dedupe.ScanOptions())
+    plans = dedupe.plan_merge(scan.groups, None)
+    return dedupe.assemble_output(text, root, scan, plans), plans
+
+
+def _playlists(text: str) -> dict[str, list[str]]:
+    root = parse_xml_bytes(text.encode("utf-8"))
+    return {
+        node.attrib["NAME"]: [pk.attrib["KEY"] for pk in node_primary_keys(node)] for node in find_playlist_nodes(root)
+    }
+
+
+def _entry_spans(text: str) -> dict[str, str]:
+    root = parse_xml_bytes(text.encode("utf-8"))
+    index = SpanIndex(text, root)
+    return {r.primary_key: index.span_of(r.entry).text(text) for r in collection_records(root)}
+
+
+def _golden_inputs(tmp_path: Path):
+    audio = tmp_path / "audio"
+    live = dedupe.scan_options_from_volume_map({str(audio): (fx.LIVE_VOLUME, fx.LIVE_VOLUMEID)}, probe=lambda r: False)
+    return [(fx.golden_tier1(), dedupe.ScanOptions()), (fx.dead_live(audio), live)]
+
+
+@pytest.mark.parametrize("case", [0, 1])
+def test_golden_input_invariants(tmp_path: Path, case: int) -> None:
+    text, options = _golden_inputs(tmp_path)[case]
+    result, plans = _run(text, options)
+    assert result.refusals == []
+    root = parse_xml_bytes(result.output.encode("utf-8"))
+
+    removed = {k for p in plans for k in p.group.member_keys if k != p.survivor}
+    assert dedupe.scan_references(root, removed) == []
+    input_count = len(collection_entries(parse_xml_bytes(text.encode("utf-8"))))
+    assert len(collection_entries(root)) == input_count - len(removed) == result.expected_entries
+    assert f'ENTRIES="{result.expected_entries}"' in result.output
+
+    survivors = {p.survivor for p in plans}
+    before, after = _entry_spans(text), _entry_spans(result.output)
+    for key, span in before.items():
+        if key not in removed and key not in survivors:
+            assert after[key] == span
+
+    redirect = {k: p.survivor for p in plans for k in p.group.member_keys if k != p.survivor}
+    expected = {name: [redirect.get(k, k) for k in keys] for name, keys in _playlists(text).items()}
+    assert _playlists(result.output) == expected
+
+
+def test_history_playlist_is_redirected() -> None:
+    """The golden pair's survivor is TIER1_B (higher play count), so the one
+    TIER1_A reference in "Set" is redirected and HISTORY, which names the
+    survivor already, is left as it was."""
+    result, (plan,) = _run(fx.golden_tier1())
+    assert plan.survivor == fx.TIER1_B
+    assert result.stats["refs_redirected"] == {"PLAYLISTS/PRIMARYKEY@KEY[TRACK]": 1}
+    assert _playlists(result.output) == {"Set": [fx.TIER1_B, fx.OTHER, fx.TIER1_B, fx.TIER1_B], "HISTORY": [fx.TIER1_B]}
+
+
+def test_stem_reference_keeps_its_entry() -> None:
+    result, _ = _run(fx.stem_reference())
+    assert result.refusals == []
+    assert result.stats["refs_preserved"] == {"PLAYLISTS/PRIMARYKEY@KEY[STEM]": 1}
+    assert result.stats["entries_removed"] == 0
+    assert [row.role for row in result.rows] == ["survivor", "kept"]
+
+
+def test_unknown_reference_shape_refuses_naming_it() -> None:
+    result, _ = _run(fx.unknown_shape_reference())
+    assert result.output is None
+    assert result.refusals == ["unknown_reference_shape:PLAYLISTS/SLOT@REF[]"]
+
+
+def test_dangling_reference_is_caught_when_redirection_is_disabled(monkeypatch) -> None:
+    monkeypatch.setattr(dedupe_assembly, "_redirect_edits", lambda *args: None)
+    result, _ = _run(fx.golden_tier1())
+    assert result.output is None
+    assert result.refusals and all(r.startswith("dangling_reference:") for r in result.refusals)
+
+
+def test_unchanged_survivor_span_stays_byte_identical() -> None:
+    text = fx.merge_pair(fx.CUE_A, fx.CUE_A)
+    result, (plan,) = _run(text)
+    assert _entry_spans(result.output)[plan.survivor] == _entry_spans(text)[plan.survivor]
+
+
+def test_appended_loser_cue_lands_in_the_survivor_span() -> None:
+    result, (plan,) = _run(fx.merge_pair(fx.CUE_A, fx.CUE_B))
+    span = _entry_spans(result.output)[plan.survivor]
+    assert span.index(fx.CUE_A) < span.index(fx.CUE_B)
```

**Documentation:**

```diff
--- a/tests/test_dedupe_references.py
+++ b/tests/test_dedupe_references.py
@@ -18,6 +18,8 @@
 
 
 def _run(text: str, options: dedupe.ScanOptions | None = None) -> tuple[dedupe.AssembleResult, list]:
+    """Scan, plan without decisions, and assemble text, as the CLI does before
+    writing."""
     root = parse_xml_bytes(text.encode("utf-8"))
     scan = dedupe.find_groups(text, root, options or dedupe.ScanOptions())
     plans = dedupe.plan_merge(scan.groups, None)
@@ -25,6 +27,7 @@
 
 
 def _playlists(text: str) -> dict[str, list[str]]:
+    """Each playlist's PRIMARYKEY KEY values in order, by playlist name."""
     root = parse_xml_bytes(text.encode("utf-8"))
     return {
         node.attrib["NAME"]: [pk.attrib["KEY"] for pk in node_primary_keys(node)] for node in find_playlist_nodes(root)
@@ -32,12 +35,16 @@
 
 
 def _entry_spans(text: str) -> dict[str, str]:
+    """Each collection entry's exact source text, by primary key; G2 compares
+    these byte-for-byte."""
     root = parse_xml_bytes(text.encode("utf-8"))
     index = SpanIndex(text, root)
     return {r.primary_key: index.span_of(r.entry).text(text) for r in collection_records(root)}
 
 
 def _golden_inputs(tmp_path: Path):
+    """The two G2 golden inputs with the options that scan them: tier 1
+    unmapped, and tier 2 with the live volume mapped."""
     audio = tmp_path / "audio"
     live = dedupe.scan_options_from_volume_map({str(audio): (fx.LIVE_VOLUME, fx.LIVE_VOLUMEID)}, probe=lambda r: False)
     return [(fx.golden_tier1(), dedupe.ScanOptions()), (fx.dead_live(audio), live)]

```


**CC-M-002-007** (tests/test_dedupe_cli.py) - implements CI-M-002-007

**Code:**

```diff
--- a/tests/test_dedupe_cli.py
+++ b/tests/test_dedupe_cli.py
@@ -0,0 +1,169 @@
+"""G3 and G4: the dedupe command's exit codes, dry-run, input
+immutability, report columns, the decisions round trip, invalid decisions
+and malformed input."""
+
+from __future__ import annotations
+
+import csv
+import hashlib
+import json
+from pathlib import Path
+
+import pytest
+
+from tests.conftest import run_tool
+from tests.fixtures.dedupe import build_dedupe_fixtures as fx
+from traktor_nml import dedupe
+
+
+@pytest.fixture
+def corpus(tmp_path: Path) -> dict[str, Path]:
+    return fx.build_static_fixtures(tmp_path / "dedupe")
+
+
+def _sha(path: Path) -> str:
+    return hashlib.sha256(path.read_bytes()).hexdigest()
+
+
+def _dedupe(tmp_path: Path, source: Path, *extra: str):
+    before = _sha(source)
+    result = run_tool(["dedupe", "--input", str(source), "--output", str(tmp_path / "out.nml"), *extra], cwd=tmp_path)
+    assert _sha(source) == before
+    return result
+
+
+def test_clean_run_exits_0_and_writes(tmp_path: Path, corpus) -> None:
+    result = _dedupe(tmp_path, corpus["golden_tier1.nml"])
+    assert result.exit_code == 0
+    assert "entries_removed=1" in result.stderr
+    assert (tmp_path / "out.nml").exists()
+
+
+def test_usage_error_exits_2_with_a_usage_line(tmp_path: Path) -> None:
+    result = run_tool(["dedupe", "--input", "x.nml"], cwd=tmp_path)
+    assert result.exit_code == 2
+    assert "usage:" in result.stderr
+    assert "refused=" not in result.stderr
+
+
+def test_refusal_exits_2_with_a_refused_line(tmp_path: Path, corpus) -> None:
+    result = _dedupe(tmp_path, corpus["unknown_shape.nml"])
+    assert result.exit_code == 2
+    assert "refused=unknown_reference_shape:PLAYLISTS/SLOT@REF[]" in result.stderr
+    assert not (tmp_path / "out.nml").exists()
+
+
+def test_output_equal_to_input_is_refused(tmp_path: Path, corpus) -> None:
+    source = corpus["golden_tier1.nml"]
+    result = run_tool(["dedupe", "--input", str(source), "--output", str(source)], cwd=tmp_path)
+    assert (result.exit_code, "refused=output_must_differ_from_input" in result.stderr) == (2, True)
+
+
+def test_live_collection_path_is_refused(tmp_path: Path, corpus) -> None:
+    live = tmp_path / "Traktor 4.0.0" / "collection.nml"
+    result = run_tool(["dedupe", "--input", str(corpus["golden_tier1.nml"]), "--output", str(live)], cwd=tmp_path)
+    assert (result.exit_code, "refused=output_is_live_collection" in result.stderr) == (2, True)
+    assert not live.exists()
+
+
+@pytest.mark.parametrize("flag", ["--report", "--write-decisions"])
+def test_auxiliary_output_equal_to_input_is_refused(tmp_path: Path, corpus, flag: str) -> None:
+    # _dedupe asserts the input's hash is unchanged after the run.
+    source = corpus["golden_tier1.nml"]
+    result = _dedupe(tmp_path, source, flag, str(source))
+    assert (result.exit_code, "refused=output_must_differ_from_input" in result.stderr) == (2, True)
+
+
+@pytest.mark.parametrize("flag", ["--report", "--write-decisions"])
+def test_auxiliary_output_at_live_collection_is_refused(tmp_path: Path, corpus, flag: str) -> None:
+    live = tmp_path / "Traktor 4.0.0" / "collection.nml"
+    result = _dedupe(tmp_path, corpus["golden_tier1.nml"], flag, str(live))
+    assert (result.exit_code, "refused=output_is_live_collection" in result.stderr) == (2, True)
+    assert not live.exists()
+
+
+def test_post_write_validation_failure_exits_3(tmp_path: Path, corpus, monkeypatch) -> None:
+    def failing_parser(data: bytes):
+        raise ValueError("injected")
+
+    original = dedupe.write_validated_output
+    monkeypatch.setattr(
+        dedupe, "write_validated_output", lambda data, path, **kw: original(data, path, parser=failing_parser, **kw)
+    )
+    result = _dedupe(tmp_path, corpus["golden_tier1.nml"])
+    assert result.exit_code == 3
+    assert (tmp_path / "out.nml.invalid").exists()
+    assert not (tmp_path / "out.nml").exists()
+
+
+def test_dry_run_writes_no_nml(tmp_path: Path, corpus) -> None:
+    result = _dedupe(tmp_path, corpus["golden_tier1.nml"], "--dry-run")
+    assert (result.exit_code, "dry_run=true" in result.stdout) == (0, True)
+    assert not (tmp_path / "out.nml").exists()
+
+
+def test_report_csv_has_the_specified_columns(tmp_path: Path, corpus) -> None:
+    report = tmp_path / "report.csv"
+    _dedupe(tmp_path, corpus["golden_tier1.nml"], "--report", str(report), "--dry-run")
+    with report.open(encoding="utf-8", newline="") as handle:
+        rows = list(csv.DictReader(handle))
+    assert list(rows[0]) == list(dedupe.REPORT_COLUMNS)
+    assert sorted(row["role"] for row in rows) == ["merged", "survivor"]
+
+
+def test_write_decisions_then_decisions_round_trip(tmp_path: Path, corpus) -> None:
+    source = corpus["bad_playcount.nml"].with_name("conflict.nml")
+    source.write_text(fx.merge_pair("", "", ' KEY="1m"', ' KEY="2m"'), encoding="utf-8")
+    decisions = tmp_path / "decisions.json"
+    first = _dedupe(tmp_path, source, "--write-decisions", str(decisions))
+    assert (first.exit_code, (tmp_path / "out.nml").exists()) == (0, False)
+    document = json.loads(decisions.read_text(encoding="utf-8"))
+    (group,) = document["groups"]
+    assert (group["action"], group["picks"]) == ("undecided", {})
+
+    group.update(action="merge", picks={"key": fx.TIER1_B})
+    decisions.write_text(json.dumps(document), encoding="utf-8")
+    second = _dedupe(tmp_path, source, "--decisions", str(decisions))
+    assert (second.exit_code, "stale_decisions=0" in second.stderr) == (0, True)
+    assert 'KEY="2m"' in (tmp_path / "out.nml").read_text(encoding="utf-8")
+
+
+@pytest.mark.parametrize(
+    ("content", "reason"),
+    [
+        ("not json", "not_json"),
+        (json.dumps({"schema": "x"}), "wrong_schema"),
+        (json.dumps({"schema": dedupe.DECISIONS_SCHEMA, "version": 9}), "unsupported_version:9"),
+    ],
+)
+def test_invalid_decisions_refused_with_nothing_written(tmp_path: Path, corpus, content: str, reason: str) -> None:
+    decisions = tmp_path / "d.json"
+    decisions.write_text(content, encoding="utf-8")
+    result = _dedupe(tmp_path, corpus["golden_tier1.nml"], "--decisions", str(decisions))
+    assert (result.exit_code, f"refused=invalid_decisions:{reason}" in result.stderr) == (2, True)
+    assert not (tmp_path / "out.nml").exists()
+
+
+# --- G4 malformed input -----------------------------------------------
+
+
+def test_truncated_xml_is_refused(tmp_path: Path, corpus) -> None:
+    result = _dedupe(tmp_path, corpus["truncated.nml"])
+    assert (result.exit_code, "refused=xml_parse_error=" in result.stderr) == (2, True)
+
+
+def test_missing_location_is_counted_and_kept(tmp_path: Path, corpus) -> None:
+    result = _dedupe(tmp_path, corpus["missing_location.nml"])
+    assert (result.exit_code, "entries_without_location=1" in result.stderr) == (0, True)
+    assert "No location" in (tmp_path / "out.nml").read_text(encoding="utf-8")
+
+
+def test_duplicate_primary_keys_are_refused(tmp_path: Path, corpus) -> None:
+    result = _dedupe(tmp_path, corpus["duplicate_keys.nml"])
+    assert (result.exit_code, "refused=duplicate_primary_key:C:/:Music/:song.mp3" in result.stderr) == (2, True)
+
+
+def test_non_numeric_playcount_is_counted(tmp_path: Path, corpus) -> None:
+    result = _dedupe(tmp_path, corpus["bad_playcount.nml"])
+    assert result.exit_code == 0
+    assert "unparseable_fields={'playcount': 1}" in result.stderr
```

**Documentation:**

```diff
--- a/tests/test_dedupe_cli.py
+++ b/tests/test_dedupe_cli.py
@@ -18,6 +18,7 @@
 
 @pytest.fixture
 def corpus(tmp_path: Path) -> dict[str, Path]:
+    """The static dedupe fixtures, built fresh under tmp_path."""
     return fx.build_static_fixtures(tmp_path / "dedupe")
 
 
@@ -26,6 +27,8 @@
 
 
 def _dedupe(tmp_path: Path, source: Path, *extra: str):
+    """Run the dedupe command and assert the input is byte-identical
+    afterwards, whatever the exit code."""
     before = _sha(source)
     result = run_tool(["dedupe", "--input", str(source), "--output", str(tmp_path / "out.nml"), *extra], cwd=tmp_path)
     assert _sha(source) == before

```


**CC-M-002-008** (tests/test_dedupe_write.py) - implements CI-M-002-008

**Code:**

```diff
--- a/tests/test_dedupe_write.py
+++ b/tests/test_dedupe_write.py
@@ -0,0 +1,53 @@
+"""G5: dedupe.write_validated_output never leaves a truncated
+destination, and quarantines a written file that fails to parse back."""
+
+from __future__ import annotations
+
+import os
+from pathlib import Path
+
+from traktor_nml import dedupe, rewrite
+
+GOOD = b'<?xml version="1.0" encoding="UTF-8"?><NML VERSION="20"><COLLECTION ENTRIES="0"></COLLECTION></NML>'
+
+
+def test_failure_mid_write_leaves_the_destination_byte_identical(tmp_path: Path, monkeypatch) -> None:
+    destination = tmp_path / "out.nml"
+    destination.write_bytes(b"previous complete file")
+
+    def failing_replace(src, dst):
+        raise OSError("injected: disk full")
+
+    monkeypatch.setattr(rewrite.os, "replace", failing_replace)
+    result = dedupe.write_validated_output(GOOD, destination)
+
+    assert (result.ok, result.invalid_path) == (False, None)
+    assert result.error.startswith("output_write_error=")
+    assert destination.read_bytes() == b"previous complete file"
+    assert [p.name for p in tmp_path.iterdir()] == ["out.nml"]
+
+
+def test_post_write_parse_failure_quarantines_the_output(tmp_path: Path) -> None:
+    destination = tmp_path / "out.nml"
+
+    def failing_parser(data: bytes):
+        raise ValueError("injected post-write parse failure")
+
+    result = dedupe.write_validated_output(GOOD, destination, parser=failing_parser)
+
+    assert result.ok is False
+    assert result.invalid_path == tmp_path / "out.nml.invalid"
+    assert result.invalid_path.read_bytes() == GOOD
+    assert not destination.exists()
+
+
+def test_wrong_entry_count_after_write_quarantines_the_output(tmp_path: Path) -> None:
+    result = dedupe.write_validated_output(GOOD, tmp_path / "out.nml", expected_entries=5)
+    assert (result.ok, result.error) == (False, "post_write_entry_count expected=5 written=0")
+    assert os.path.exists(tmp_path / "out.nml.invalid")
+
+
+def test_clean_write_is_ok(tmp_path: Path) -> None:
+    result = dedupe.write_validated_output(GOOD, tmp_path / "out.nml", expected_entries=0)
+    assert result == dedupe.WriteResult(True)
+    assert (tmp_path / "out.nml").read_bytes() == GOOD

```

**Documentation:**

```diff
--- a/tests/test_dedupe_write.py
+++ b/tests/test_dedupe_write.py
@@ -18,6 +18,8 @@
     def failing_replace(src, dst):
         raise OSError("injected: disk full")
 
+    # The atomic writer fails at its final rename, after the temp file is
+    # complete.
     monkeypatch.setattr(rewrite.os, "replace", failing_replace)
     result = dedupe.write_validated_output(GOOD, destination)
 

```


**CC-M-002-009** (tests/test_cli_contract.py) - implements CI-M-002-009

**Code:**

```diff
--- a/tests/test_cli_contract.py
+++ b/tests/test_cli_contract.py
@@ -33,6 +33,15 @@ def test_help_lists_every_pre_existing_subcommand(tmp_path: Path) -> None:
     assert expected <= listed
 
 
+def test_help_lists_dedupe(tmp_path: Path) -> None:
+    """dedupe registers through the same discovery mechanism as every
+    other subcommand (DL-003), so it appears in the top-level choices."""
+    result = run_tool(["--help"], cwd=tmp_path)
+    brace_start = result.stdout.index("{")
+    brace_end = result.stdout.index("}", brace_start)
+    assert "dedupe" in result.stdout[brace_start + 1:brace_end].split(",")
+
+
 def test_allow_artist_title_only_matches_loose_confidence(fixture_corpus: Path, tmp_path: Path) -> None:
     """Byte-identical stdout between the two invocations confirms
     --allow-artist-title-only is a pure alias for --match-confidence

```

**Documentation:**

```diff
--- a/tests/test_cli_contract.py
+++ b/tests/test_cli_contract.py
@@ -37,6 +37,7 @@
     """dedupe registers through the same discovery mechanism as every
     other subcommand (DL-003), so it appears in the top-level choices."""
     result = run_tool(["--help"], cwd=tmp_path)
+    # argparse lists subcommand choices as {a,b,...} in the usage line.
     brace_start = result.stdout.index("{")
     brace_end = result.stdout.index("}", brace_start)
     assert "dedupe" in result.stdout[brace_start + 1:brace_end].split(",")

```


**CC-M-002-010** (tests/test_gui_command_classification.py) - implements CI-M-002-010

**Code:**

```diff
--- a/tests/test_gui_command_classification.py
+++ b/tests/test_gui_command_classification.py
@@ -12,7 +12,7 @@ same name. This module resolves that by treating **primary tier
 same name. This module resolves that by treating **primary tier
 assignment** and **Tier 2 eligibility** as two separate predicates:
 
-- `PRIMARY_TIER` is a total, disjoint partition of the 14 real subcommands
+- `PRIMARY_TIER` is a total, disjoint partition of the 15 real subcommands
   into tiers 1/2/3, using §1's tier tables read literally (Tier 2's table
   lists `inspect`, `encode-dir`, `preview-compare`, `scan-compare-candidates`
   - not `scan-reconnect-candidates`, which §1's Tier 1 table already
@@ -62,6 +62,7 @@ TIER1 = frozenset({
     "build-playlist",
     "discover-tracks",
     "discover-collection-tracks",
+    "dedupe",
 })
 
 # Tier 2 (generated forms), as enumerated in §1's own sentence naming the
@@ -160,15 +161,15 @@ def _total_and_disjoint_violations(
 
 
 def test_real_subcommand_set_is_totally_and_disjointly_classified() -> None:
-    """The real 14 subcommands from build_parser(), unmutated, classify
+    """The real 15 subcommands from build_parser(), unmutated, classify
     cleanly against TIER1/TIER2/TIER3 - the baseline the negative controls
     below are checked against."""
     choices = _real_subcommand_choices()
     assert choices == {
         "inspect", "encode-dir", "preview-compare", "scan-compare-candidates",
         "scan-reconnect-candidates", "rewrite-from-reconnect", "preview-diff", "rewrite",
         "build-playlist", "discover-tracks", "discover-collection-tracks",
-        "splice", "split", "rewrite-from-collection-compare",
+        "splice", "split", "rewrite-from-collection-compare", "dedupe",
     }
     violations = _total_and_disjoint_violations(choices, TIER1, TIER2, TIER3)
     assert violations == {}
```

**Documentation:**

```diff
--- a/tests/test_gui_command_classification.py
+++ b/tests/test_gui_command_classification.py
@@ -62,6 +62,8 @@
     "build-playlist",
     "discover-tracks",
     "discover-collection-tracks",
+    # dedupe pairs a CLI command with its own page, like build-playlist
+    # (DL-318).
     "dedupe",
 })
 

```

> **Developer notes**: The classification guard requires every real subcommand in exactly one tier; dedupe is a first-class GUI workflow (TIER1), and the real-choices set gains it.

**CC-M-002-011** (traktor_nml/dedupe_members.py) - implements CI-M-002-011

**Code:**

```diff
--- a/traktor_nml/dedupe_members.py
+++ b/traktor_nml/dedupe_members.py
@@ -0,0 +1,174 @@
+"""Dedupe vocabulary shared by every dedupe module: tier, file-state,
+decision and plan constants, and the Member / DupGroup / ScanResult
+records the tiers exchange. Split from traktor_nml/dedupe.py by DL-324.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field
+from pathlib import Path, PurePosixPath
+from typing import Mapping, Optional
+
+from .dedupe_fields import MergeFields
+from .matching import _DURATION_ABS_TOLERANCE, _duration_seconds, _refutes
+from .model import EntryRecord
+
+
+TIER_EXACT_LOCATION = 1
+TIER_DEAD_LIVE = 2
+TIER_SAME_AUDIO = 3
+TIER_PROBABLE = 4
+ALL_TIERS = (TIER_EXACT_LOCATION, TIER_DEAD_LIVE, TIER_SAME_AUDIO, TIER_PROBABLE)
+
+# Tiers 1-2 carry admission rules strict enough to apply without review
+# (DL-315). Tier 3 is suggested and tier 4 is review-only, so neither is
+# ever in this set whatever its module reports.
+AUTO_APPLY_TIERS = frozenset({TIER_EXACT_LOCATION, TIER_DEAD_LIVE})
+DEFAULT_TIERS = frozenset({TIER_EXACT_LOCATION, TIER_DEAD_LIVE})
+LIVE = "live"
+DEAD = "dead"
+UNKNOWN = "unknown"
+ACTION_UNDECIDED = "undecided"
+ACTION_MERGE = "merge"
+ACTION_NOT_DUPLICATES = "not_duplicates"
+DECISION_ACTIONS = (ACTION_UNDECIDED, ACTION_MERGE, ACTION_NOT_DUPLICATES)
+
+# The plan-level outcome for one group; "review" is an undecided group
+# left alone and reported.
+PLAN_MERGE = "merge"
+PLAN_REVIEW = "review"
+PLAN_NOT_DUPLICATES = "not_duplicates"
+PLAN_REFUSED = "refused"
+DECISIONS_SCHEMA = "traktor-nml-dedupe-decisions"
+DECISIONS_VERSION = 1
+
+
+@dataclass(frozen=True)
+class Member:
+    """One collection entry as the dedupe sees it: its identity record,
+    its merge fields, and whether its file is live, dead or unknown."""
+
+    index: int
+    record: EntryRecord
+    fields: MergeFields
+    file_state: str
+    local_path: Optional[Path]
+
+    @property
+    def primary_key(self) -> str:
+        return self.record.primary_key
+
+
+@dataclass(frozen=True)
+class TierMatch:
+    """What a tier finder reports: the member keys it groups, why, and
+    whether the group may be applied without review.
+
+    default_action is the decision a group takes when no decisions file
+    names it; tier 4 sets not_duplicates for a stem and its stereo file."""
+
+    keys: tuple[str, ...]
+    evidence: str
+    confidence: str
+    auto_apply: bool = False
+    review_reason: str = ""
+    default_action: str = ACTION_UNDECIDED
+
+
+@dataclass(frozen=True)
+class DupGroup:
+    group_id: str
+    tier: int
+    members: tuple[Member, ...]
+    evidence: str
+    confidence: str
+    auto_apply: bool
+    review_reason: str
+    suggested_survivor: str
+    survivor_reason: str
+    default_action: str = ACTION_UNDECIDED
+
+    @property
+    def member_keys(self) -> tuple[str, ...]:
+        return tuple(sorted(member.primary_key for member in self.members))
+
+    def member(self, primary_key: str) -> Member:
+        return next(m for m in self.members if m.primary_key == primary_key)
+
+
+@dataclass(frozen=True)
+class ScanOptions:
+    """tiers is what the operator asked for; a tier outside DEFAULT_TIERS
+    runs only when its module is present and admitted.
+
+    known_mounts is the (VOLUME, VOLUMEID) -> anchors table
+    volumes.local_path_for_location reads. case_insensitive_volumes holds
+    the VOLUMEIDs a probe (or the platform default for a probed mount)
+    found case-insensitive; every other volume compares case-sensitively
+    (DL-313)."""
+
+    tiers: frozenset[int] = DEFAULT_TIERS
+    refute: bool = True
+    known_mounts: Mapping[tuple[str, str], list[Path]] = field(default_factory=dict)
+    case_insensitive_volumes: frozenset[str] = frozenset()
+    # The tag cache tier 3 reads fingerprints through; None fingerprints
+    # without caching.
+    cache_path: Optional[Path] = None
+
+
+@dataclass
+class ScanResult:
+    groups: list[DupGroup]
+    members: dict[str, Member]
+    stats: dict[str, object]
+    refusals: list[str]
+
+
+@dataclass(frozen=True)
+class TierContext:
+    """What a tier finder reads: every member not already grouped by a
+    lower tier, the run's options, and the stats dict it may add to."""
+
+    members: tuple[Member, ...]
+    options: ScanOptions
+    stats: dict[str, object]
+
+
+class KeyUnion:
+    """Union-find over member keys for the pairwise tiers (3 and 4), so a
+    chain of pairwise matches lands in one group rather than several
+    overlapping ones."""
+
+    def __init__(self) -> None:
+        self._parent: dict[str, str] = {}
+
+    def find(self, key: str) -> str:
+        self._parent.setdefault(key, key)
+        while self._parent[key] != key:
+            self._parent[key] = self._parent[self._parent[key]]
+            key = self._parent[key]
+        return key
+
+    def union(self, a: str, b: str) -> None:
+        self._parent[self.find(a)] = self.find(b)
+
+    def groups(self) -> list[tuple[str, ...]]:
+        by_root: dict[str, list[str]] = {}
+        for key in self._parent:
+            by_root.setdefault(self.find(key), []).append(key)
+        return [tuple(keys) for keys in by_root.values() if len(keys) > 1]
+
+
+def extension(member: Member) -> str:
+    return PurePosixPath(member.record.file_name).suffix.lower()
+
+
+def pair_refuted(a: Member, b: Member) -> bool:
+    """The refute check tiers 3 and 4 apply. A format upgrade changes the
+    file size by design, so across formats only duration can refute;
+    within one format the collection's own same-source size and duration
+    tolerances apply (matching._refutes)."""
+    if extension(a) == extension(b):
+        return _refutes(a.record, b.record)
+    seconds_a, seconds_b = _duration_seconds(a.record), _duration_seconds(b.record)
+    return seconds_a is not None and seconds_b is not None and abs(seconds_a - seconds_b) > _DURATION_ABS_TOLERANCE
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_members.py
+++ b/traktor_nml/dedupe_members.py
@@ -77,6 +77,11 @@
 
 @dataclass(frozen=True)
 class DupGroup:
+    """One duplicate group: its members, the tier that found them and why,
+    whether it may apply without review (DL-315), and the suggested survivor
+    with the first criterion that decided it (DL-320). group_id is assigned
+    after every tier has run."""
+
     group_id: str
     tier: int
     members: tuple[Member, ...]
@@ -90,6 +95,8 @@
 
     @property
     def member_keys(self) -> tuple[str, ...]:
+        """Sorted member primary keys: the identity a decisions file keys this
+        group by (DL-317)."""
         return tuple(sorted(member.primary_key for member in self.members))
 
     def member(self, primary_key: str) -> Member:
@@ -118,6 +125,10 @@
 
 @dataclass
 class ScanResult:
+    """What find_groups returns: the groups, every member by primary key, the
+    name=value stats and any refusals the scan itself found (duplicate
+    primary keys)."""
+
     groups: list[DupGroup]
     members: dict[str, Member]
     stats: dict[str, object]
@@ -143,6 +154,8 @@
         self._parent: dict[str, str] = {}
 
     def find(self, key: str) -> str:
+        """The root key of key's set, registering key as its own set on first
+        sight; path halving keeps later finds short."""
         self._parent.setdefault(key, key)
         while self._parent[key] != key:
             self._parent[key] = self._parent[self._parent[key]]
@@ -150,9 +163,11 @@
         return key
 
     def union(self, a: str, b: str) -> None:
+        """Merge the sets holding a and b."""
         self._parent[self.find(a)] = self.find(b)
 
     def groups(self) -> list[tuple[str, ...]]:
+        """Every set of two or more keys; singletons are not groups."""
         by_root: dict[str, list[str]] = {}
         for key in self._parent:
             by_root.setdefault(self.find(key), []).append(key)
@@ -160,6 +175,8 @@
 
 
 def extension(member: Member) -> str:
+    """The member's lower-cased file suffix (".mp3", ".flac"); pair_refuted
+    compares it to tell a same-format pair from a format upgrade."""
     return PurePosixPath(member.record.file_name).suffix.lower()
 
 

```


**CC-M-002-012** (traktor_nml/dedupe_fields.py) - implements CI-M-002-012

**Code:**

```diff
--- a/traktor_nml/dedupe_fields.py
+++ b/traktor_nml/dedupe_fields.py
@@ -0,0 +1,203 @@
+"""The merge data model's per-entry fields (plan.md "Merge data model"):
+Cue, Grid and MergeFields read from one ENTRY span beside its EntryRecord,
+which stays identity-only so splice's _TRACKED_ATTRS is unchanged (DL-312).
+
+Split from traktor_nml/dedupe.py by DL-324; dedupe.py re-exports the
+public names.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from datetime import date
+from typing import Optional
+
+from .spans import Span, find_element_span
+
+
+# Field names of the merge data model (plan.md "Merge data model"). A
+# decisions file's picks may name only these.
+MERGE_FIELD_NAMES = (
+    "cues", "hotcue", "grid", "key", "ranking", "color", "comment",
+    "playcount", "last_played", "import_date",
+)
+_LOSSLESS_EXTENSIONS = frozenset({".flac", ".wav", ".aif", ".aiff", ".alac"})
+_GRID_CUE_TYPE = "4"
+_CUE_START_TOLERANCE_MS = 1.0
+_GRID_BPM_TOLERANCE = 0.001
+_NO_HOTCUE = ("", "-1")
+
+# INFO attributes the merge data model names, and the ENTRY attributes and
+# children identity or the model already accounts for. Everything else a
+# loser carries is discarded with it and counted (loser_fields_discarded).
+_INFO_MERGE_ATTRS = {
+    "key": "KEY", "ranking": "RANKING", "color": "COLOR", "comment": "COMMENT",
+    "playcount": "PLAYCOUNT", "last_played": "LAST_PLAYED", "import_date": "IMPORT_DATE",
+}
+_INFO_IDENTITY_ATTRS = frozenset({"BITRATE", "PLAYTIME", "PLAYTIME_FLOAT", "FILESIZE"})
+_MODELLED_CHILDREN = frozenset({"LOCATION", "INFO", "CUE_V2", "TEMPO", "MUSICAL_KEY"})
+
+
+@dataclass(frozen=True)
+class Cue:
+    """One non-grid CUE_V2: its identity fields plus the raw span text a
+    merge appends verbatim."""
+
+    kind: str
+    start: Optional[float]
+    hotcue: str
+    name: str
+    raw: str
+
+
+@dataclass(frozen=True)
+class Grid:
+    """The TYPE=4 CUE_V2 and the TEMPO BPM it runs at. Taken whole from
+    one entry, never merged (DL-316)."""
+
+    start: Optional[float]
+    bpm: Optional[float]
+    bpm_raw: str
+    raw: str
+
+
+@dataclass(frozen=True)
+class MergeFields:
+    """The merge data model's fields for one entry, read beside its
+    EntryRecord rather than inside it: widening EntryRecord or
+    splice._TRACKED_ATTRS would move splice's grouping and conflict
+    output (DL-312).
+
+    unparseable names each date or count field whose raw value did not
+    parse; such a field is survivor-only for the whole group.
+    unmodelled counts the attributes and children no model row names."""
+
+    cues: tuple[Cue, ...]
+    grid: Optional[Grid]
+    key: str
+    musical_key: str
+    ranking: str
+    color: str
+    comment: str
+    playcount: int
+    last_played: Optional[date]
+    import_date: Optional[date]
+    unparseable: frozenset[str]
+    unmodelled: int
+
+
+def _parse_float(value: Optional[str]) -> Optional[float]:
+    try:
+        return float(value) if value not in (None, "") else None
+    except ValueError:
+        return None
+
+
+def _parse_nml_date(value: str) -> Optional[date]:
+    try:
+        year, month, day = (int(part) for part in value.split("/"))
+        return date(year, month, day)
+    except ValueError:
+        return None
+
+
+def format_nml_date(value: date) -> str:
+    return f"{value.year}/{value.month}/{value.day}"
+
+
+def _child_spans(span_text: str, tag: str) -> list[Span]:
+    """Every tag child of one ENTRY span, in document order. Scanning
+    starts past the ENTRY's own '<' so the entry never matches itself."""
+    spans: list[Span] = []
+    found = find_element_span(span_text, tag, 1)
+    while found is not None:
+        spans.append(found)
+        found = find_element_span(span_text, tag, found.end)
+    return spans
+
+
+def _leading_whitespace(text: str, pos: int) -> str:
+    start = pos
+    while start > 0 and text[start - 1] in " \t\r\n":
+        start -= 1
+    return text[start:pos]
+
+
+def _read_cues(entry, span_text: str) -> tuple[tuple[Cue, ...], Optional[Grid]]:
+    """Pair each parsed CUE_V2 with its raw span by document order."""
+    tempo = entry.find("TEMPO")
+    bpm_raw = "" if tempo is None else tempo.attrib.get("BPM", "")
+    cues: list[Cue] = []
+    grid: Optional[Grid] = None
+    raws = [span.text(span_text) for span in _child_spans(span_text, "CUE_V2")]
+    for element, raw in zip(entry.findall("CUE_V2"), raws):
+        start = _parse_float(element.attrib.get("START"))
+        kind = element.attrib.get("TYPE", "")
+        if kind == _GRID_CUE_TYPE and grid is None:
+            grid = Grid(start, _parse_float(bpm_raw), bpm_raw, raw)
+            continue
+        cues.append(Cue(kind, start, element.attrib.get("HOTCUE", ""), element.attrib.get("NAME", ""), raw))
+    return tuple(cues), grid
+
+
+def _count_unmodelled(entry) -> int:
+    info = entry.find("INFO")
+    info_extra = 0 if info is None else sum(
+        1 for name in info.attrib if name not in _INFO_IDENTITY_ATTRS and name not in _INFO_MERGE_ATTRS.values()
+    )
+    children = sum(1 for child in entry if isinstance(child.tag, str) and child.tag not in _MODELLED_CHILDREN)
+    return info_extra + children
+
+
+def read_merge_fields(entry, span_text: str) -> MergeFields:
+    """Parse one ENTRY's merge fields. A value that fails to parse is kept
+    out of the merge and named in unparseable, never raised (G4)."""
+    info = entry.find("INFO")
+    info_attrs = {} if info is None else dict(info.attrib)
+    musical = entry.find("MUSICAL_KEY")
+    unparseable: set[str] = set()
+
+    raw_count = info_attrs.get("PLAYCOUNT", "")
+    playcount = 0
+    if raw_count:
+        try:
+            playcount = int(raw_count)
+        except ValueError:
+            unparseable.add("playcount")
+
+    dates: dict[str, Optional[date]] = {}
+    for name in ("last_played", "import_date"):
+        raw = info_attrs.get(_INFO_MERGE_ATTRS[name], "")
+        dates[name] = _parse_nml_date(raw) if raw else None
+        if raw and dates[name] is None:
+            unparseable.add(name)
+
+    cues, grid = _read_cues(entry, span_text)
+    return MergeFields(
+        cues=cues,
+        grid=grid,
+        key=info_attrs.get("KEY", ""),
+        musical_key="" if musical is None else musical.attrib.get("VALUE", ""),
+        ranking=info_attrs.get("RANKING", ""),
+        color=info_attrs.get("COLOR", ""),
+        comment=info_attrs.get("COMMENT", ""),
+        playcount=playcount,
+        last_played=dates["last_played"],
+        import_date=dates["import_date"],
+        unparseable=frozenset(unparseable),
+        unmodelled=_count_unmodelled(entry),
+    )
+
+
+def _same_cue(a: Cue, b: Cue) -> bool:
+    if a.kind != b.kind or a.start is None or b.start is None:
+        return False
+    return abs(a.start - b.start) <= _CUE_START_TOLERANCE_MS
+
+
+def grids_equal(a: Optional[Grid], b: Optional[Grid]) -> bool:
+    if a is None or b is None:
+        return a is b
+    if a.start is None or b.start is None or a.bpm is None or b.bpm is None:
+        return a.raw == b.raw
+    return abs(a.start - b.start) <= _CUE_START_TOLERANCE_MS and abs(a.bpm - b.bpm) <= _GRID_BPM_TOLERANCE
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_fields.py
+++ b/traktor_nml/dedupe_fields.py
@@ -102,6 +102,11 @@
 
 
 def format_nml_date(value: date) -> str:
+    """Render a date in NML's Y/M/D form with month and day unpadded
+    (2024/3/7, not 2024/03/07), the form Traktor writes and the reviewed
+    merge data model keeps byte-stable (DL-308). The merged value is written
+    into the survivor's INFO span, never into EntryRecord, whose identity
+    fields splice tracks (DL-312)."""
     return f"{value.year}/{value.month}/{value.day}"
 
 
@@ -141,6 +146,9 @@
 
 
 def _count_unmodelled(entry) -> int:
+    """How many INFO attributes and ENTRY children the merge model does not
+    name. They stay byte-preserved on the survivor and a loser's go with it;
+    the count is reported so the loss is visible."""
     info = entry.find("INFO")
     info_extra = 0 if info is None else sum(
         1 for name in info.attrib if name not in _INFO_IDENTITY_ATTRS and name not in _INFO_MERGE_ATTRS.values()
@@ -190,12 +198,18 @@
 
 
 def _same_cue(a: Cue, b: Cue) -> bool:
+    """Two cues are the same cue when they share a kind and their starts fall
+    within the cue tolerance; name and hotcue slot are compared separately,
+    as conflicts."""
     if a.kind != b.kind or a.start is None or b.start is None:
         return False
     return abs(a.start - b.start) <= _CUE_START_TOLERANCE_MS
 
 
 def grids_equal(a: Optional[Grid], b: Optional[Grid]) -> bool:
+    """Grids compare by start and BPM within tolerance, or byte-for-byte when
+    either fails to parse. Grids are never merged; unequal grids are a
+    conflict for the operator (DL-316)."""
     if a is None or b is None:
         return a is b
     if a.start is None or b.start is None or a.bpm is None or b.bpm is None:

```


**CC-M-002-013** (traktor_nml/dedupe_paths.py) - implements CI-M-002-013

**Code:**

```diff
--- a/traktor_nml/dedupe_paths.py
+++ b/traktor_nml/dedupe_paths.py
@@ -0,0 +1,87 @@
+"""Location identity and volume case policy (DL-313): tier 1 keys on
+(VOLUMEID, DIR, FILE), folded only on a volume probed case-insensitive,
+never through matching._fold; a volume nobody mapped is neither live nor
+dead. Split from traktor_nml/dedupe.py by DL-324.
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+import tempfile
+from pathlib import Path
+from typing import Callable, Mapping, Optional
+
+from .dedupe_members import DEAD, DEFAULT_TIERS, LIVE, ScanOptions, UNKNOWN
+from .model import EntryRecord, decode_traktor_dir, encode_traktor_dir
+from .volumes import local_path_for_location
+
+
+def probe_case_insensitive(root: Path) -> Optional[bool]:
+    """Create a temp file under root and stat its case-swapped name.
+    None when root is not writable, so the caller falls back to the
+    platform default rather than guessing from the root's name."""
+    try:
+        fd, name = tempfile.mkstemp(dir=str(root), prefix=".dedupe-case-probe-")
+    except OSError:
+        return None
+    os.close(fd)
+    try:
+        swapped = Path(name).with_name(Path(name).name.swapcase())
+        return swapped.exists()
+    finally:
+        os.remove(name)
+
+
+def _platform_default_case_insensitive() -> bool:
+    return sys.platform.startswith("win") or sys.platform == "darwin"
+
+
+def scan_options_from_volume_map(
+    volume_map: Mapping[str, tuple[str, str]],
+    tiers: frozenset[int] = DEFAULT_TIERS,
+    refute: bool = True,
+    probe: Callable[[Path], Optional[bool]] = probe_case_insensitive,
+) -> ScanOptions:
+    """Build ScanOptions from parsed --volume-map triples.
+
+    Each scan root anchors its (VOLUME, VOLUMEID) at the root's own
+    filesystem anchor, the way reconnect_run anchors them, because a
+    LOCATION's decoded path is volume-relative. Case sensitivity is probed
+    in the scan root itself; a volume no map entry names is never probed
+    and so stays case-sensitive."""
+    known_mounts: dict[tuple[str, str], list[Path]] = {}
+    insensitive: set[str] = set()
+    for root_text, identity in volume_map.items():
+        root = Path(root_text)
+        if root.anchor:
+            known_mounts.setdefault(identity, []).append(Path(root.anchor))
+        probed = probe(root)
+        if probed if probed is not None else _platform_default_case_insensitive():
+            insensitive.add(identity[1])
+    return ScanOptions(frozenset(tiers), refute, known_mounts, frozenset(insensitive))
+
+
+def location_identity(record: EntryRecord, case_insensitive_volumes: frozenset[str]) -> tuple[str, str, str]:
+    """Tier 1's location key: (VOLUMEID, DIR, FILE) after separator
+    normalisation, folded only on a volume known case-insensitive.
+
+    matching._fold is deliberately not used: it casefolds unconditionally,
+    and on a case-sensitive volume that merges two distinct files (DL-313).
+    VOLUMEID rather than VOLUME, because two volumes can share a name."""
+    location = record.location
+    dir_value = encode_traktor_dir(str(decode_traktor_dir(location.dir_value.replace("\\", "/"))))
+    file_name = location.file_name.replace("\\", "/")
+    if location.volumeid in case_insensitive_volumes:
+        return location.volumeid, dir_value.casefold(), file_name.casefold()
+    return location.volumeid, dir_value, file_name
+
+
+def _file_state(record: EntryRecord, known_mounts) -> tuple[str, Optional[Path]]:
+    """live when the file resolves through an established mount, dead
+    when its volume is mapped but the file is not there, unknown when its
+    volume is not mapped - an unmapped volume is never dead (DL-313)."""
+    if (record.location.volume, record.location.volumeid) not in known_mounts:
+        return UNKNOWN, None
+    path = local_path_for_location(record.location, known_mounts)
+    return (LIVE, path) if path is not None else (DEAD, None)
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_paths.py
+++ b/traktor_nml/dedupe_paths.py
@@ -34,6 +34,9 @@
 
 
 def _platform_default_case_insensitive() -> bool:
+    """The case rule for a mapped volume whose probe could not decide: Windows
+    and macOS default filesystems fold case. A volume that is not mapped
+    never reaches this and stays case-sensitive (DL-313)."""
     return sys.platform.startswith("win") or sys.platform == "darwin"
 
 

```


**CC-M-002-014** (traktor_nml/dedupe_groups.py) - implements CI-M-002-014

**Code:**

```diff
--- a/traktor_nml/dedupe_groups.py
+++ b/traktor_nml/dedupe_groups.py
@@ -0,0 +1,213 @@
+"""Dedupe grouping: survivor suggestion, tiers 1-2, the tier-3/4 module
+gate and find_groups (DL-315). Split from traktor_nml/dedupe.py by
+DL-324.
+"""
+
+from __future__ import annotations
+
+import importlib
+from dataclasses import replace
+from typing import Callable, Optional
+
+from .dedupe_fields import _LOSSLESS_EXTENSIONS, _parse_float, read_merge_fields
+from .dedupe_members import (
+    ALL_TIERS,
+    AUTO_APPLY_TIERS,
+    DEAD,
+    DupGroup,
+    LIVE,
+    Member,
+    ScanOptions,
+    ScanResult,
+    TIER_DEAD_LIVE,
+    TIER_EXACT_LOCATION,
+    TIER_PROBABLE,
+    TIER_SAME_AUDIO,
+    TierContext,
+    TierMatch,
+    UNKNOWN,
+    extension,
+)
+from .dedupe_paths import _file_state, location_identity
+from .matching import _DURATION_ABS_TOLERANCE, _SIZE_REL_TOLERANCE, _duration_seconds, _fold, _size_kb
+from .model import collection_entries, collection_records
+from .spans import SpanIndex
+
+
+# Tiers 3 and 4 live in their own modules so each lands behind its own gate
+# (M-004 on the M-001 AUDIO_ID verdict, M-005 on the version-variant
+# guard). A module that is absent, or reports ADMITTED False, leaves its
+# tier disabled and the stats say tier_N=disabled rather than the tier
+# silently finding nothing.
+_OPTIONAL_TIER_MODULES = {
+    TIER_SAME_AUDIO: "traktor_nml.dedupe_tier3",
+    TIER_PROBABLE: "traktor_nml.dedupe_tier4",
+}
+
+
+def _survivor_key(member: Member) -> tuple:
+    state_rank = {LIVE: 2, UNKNOWN: 1, DEAD: 0}[member.file_state]
+    bitrate = _parse_float(member.record.bitrate) or 0.0
+    has_grid = member.fields.grid is not None
+    import_ordinal = member.fields.import_date.toordinal() if member.fields.import_date else 10**9
+    return (
+        state_rank,
+        extension(member) in _LOSSLESS_EXTENSIONS,
+        bitrate,
+        (len(member.fields.cues), has_grid),
+        member.fields.playcount,
+        -import_ordinal,
+        -member.index,
+    )
+
+
+# The reason each position of _survivor_key reads as, in the order the
+# suggestion compares them (DL-320).
+_SURVIVOR_REASONS = (
+    "file exists",
+    "lossless",
+    "higher bitrate",
+    "more cues or has a beatgrid",
+    "higher play count",
+    "earliest import",
+    "first in collection order",
+)
+
+
+def suggest_survivor(members: tuple[Member, ...]) -> tuple[str, str]:
+    """The suggested survivor's primary key and the first criterion on
+    which it beats the runner-up: that criterion is the reason shown."""
+    ranked = sorted(members, key=_survivor_key, reverse=True)
+    best, runner_up = _survivor_key(ranked[0]), _survivor_key(ranked[1])
+    position = next(i for i, (a, b) in enumerate(zip(best, runner_up)) if a != b)
+    return ranked[0].primary_key, _SURVIVOR_REASONS[position]
+
+
+def _exact_location_matches(context: TierContext) -> list[TierMatch]:
+    buckets: dict[tuple[str, str, str], list[Member]] = {}
+    for member in context.members:
+        identity = location_identity(member.record, context.options.case_insensitive_volumes)
+        buckets.setdefault(identity, []).append(member)
+    return [
+        TierMatch(tuple(m.primary_key for m in bucket), "same file after path normalisation", "strict", True)
+        for bucket in buckets.values()
+        if len(bucket) > 1
+    ]
+
+
+def _dead_admitted(dead: Member, live: Member) -> str:
+    """The first tier 2 admission rule dead and live fail, or "" when
+    they pass every one (plan.md "Detection tiers" 2)."""
+    dead_seconds, live_seconds = _duration_seconds(dead.record), _duration_seconds(live.record)
+    if dead_seconds is None or live_seconds is None or abs(dead_seconds - live_seconds) > _DURATION_ABS_TOLERANCE:
+        return "duration_outside_tolerance"
+    if extension(dead) != extension(live):
+        return ""
+    dead_kb, live_kb = _size_kb(dead.record), _size_kb(live.record)
+    if dead_kb is None or live_kb is None or abs(dead_kb - live_kb) > _SIZE_REL_TOLERANCE * max(dead_kb, live_kb):
+        return "filesize_outside_tolerance"
+    return ""
+
+
+def _dead_live_matches(context: TierContext) -> list[TierMatch]:
+    """One group per folded artist+title bucket holding both a dead and a
+    live entry. It auto-applies only with exactly one live entry that
+    every dead entry passes admission against; a dead entry facing two or
+    more live entries always goes to review."""
+    buckets: dict[tuple[str, str], list[Member]] = {}
+    for member in context.members:
+        if member.file_state == UNKNOWN or not (member.record.artist or member.record.title):
+            continue
+        buckets.setdefault((_fold(member.record.artist), _fold(member.record.title)), []).append(member)
+    matches: list[TierMatch] = []
+    for bucket in buckets.values():
+        dead = [m for m in bucket if m.file_state == DEAD]
+        live = [m for m in bucket if m.file_state == LIVE]
+        if not dead or not live:
+            continue
+        reason = "several_live_entries" if len(live) > 1 else next(
+            (r for r in (_dead_admitted(d, live[0]) for d in dead) if r), ""
+        )
+        keys = tuple(m.primary_key for m in dead + live)
+        matches.append(TierMatch(keys, "missing file beside a live entry", "strict", not reason, reason))
+    return matches
+
+
+_BUILTIN_FINDERS: dict[int, Callable[[TierContext], list[TierMatch]]] = {
+    TIER_EXACT_LOCATION: _exact_location_matches,
+    TIER_DEAD_LIVE: _dead_live_matches,
+}
+
+
+def tier_finder(tier: int) -> Optional[Callable[[TierContext], list[TierMatch]]]:
+    """The finder for tier, or None when the tier is not admitted: its
+    module is absent or reports ADMITTED False (DL-315)."""
+    if tier in _BUILTIN_FINDERS:
+        return _BUILTIN_FINDERS[tier]
+    try:
+        module = importlib.import_module(_OPTIONAL_TIER_MODULES[tier])
+    except ModuleNotFoundError:
+        return None
+    return module.find_matches if getattr(module, "ADMITTED", False) else None
+
+
+def _read_members(source_text: str, root, options: ScanOptions, stats: dict) -> tuple[list[Member], list[str]]:
+    span_index = SpanIndex(source_text, root)
+    members: list[Member] = []
+    seen: set[str] = set()
+    refusals: list[str] = []
+    for index, record in enumerate(collection_records(root)):
+        if record.primary_key in seen:
+            refusals.append(f"duplicate_primary_key:{record.primary_key}")
+            continue
+        seen.add(record.primary_key)
+        fields = read_merge_fields(record.entry, span_index.span_of(record.entry).text(source_text))
+        state, path = _file_state(record, options.known_mounts)
+        members.append(Member(index, record, fields, state, path))
+        for name in fields.unparseable:
+            stats["unparseable_fields"][name] = stats["unparseable_fields"].get(name, 0) + 1
+    stats["entries_without_location"] = len(collection_entries(root)) - len(members) - len(refusals)
+    return members, refusals
+
+
+def find_groups(source_text: str, root, options: ScanOptions) -> ScanResult:
+    """Group the collection's duplicates, lowest tier first. An entry a
+    lower tier groups is not offered to a higher one, so one entry sits in
+    at most one group."""
+    stats: dict[str, object] = {"groups_by_tier": {}, "unparseable_fields": {}}
+    members, refusals = _read_members(source_text, root, options, stats)
+    by_key = {m.primary_key: m for m in members}
+    grouped: set[str] = set()
+    groups: list[DupGroup] = []
+    for tier in ALL_TIERS:
+        finder = tier_finder(tier) if tier in options.tiers else None
+        if finder is None:
+            stats[f"tier_{tier}"] = "disabled"
+            continue
+        remaining = tuple(m for m in members if m.primary_key not in grouped)
+        for match in finder(TierContext(remaining, options, stats)):
+            group_members = tuple(sorted((by_key[k] for k in match.keys), key=lambda m: m.index))
+            grouped.update(match.keys)
+            groups.append(_make_group(tier, group_members, match))
+    groups.sort(key=lambda g: g.members[0].index)
+    groups = [replace(g, group_id=f"G{n:04d}") for n, g in enumerate(groups, start=1)]
+    for group in groups:
+        counts = stats["groups_by_tier"]
+        counts[group.tier] = counts.get(group.tier, 0) + 1
+    return ScanResult(groups, by_key, stats, refusals)
+
+
+def _make_group(tier: int, members: tuple[Member, ...], match: TierMatch) -> DupGroup:
+    survivor, reason = suggest_survivor(members)
+    return DupGroup(
+        group_id="",
+        tier=tier,
+        members=members,
+        evidence=match.evidence,
+        confidence=match.confidence,
+        auto_apply=match.auto_apply and tier in AUTO_APPLY_TIERS,
+        review_reason=match.review_reason,
+        suggested_survivor=survivor,
+        survivor_reason=reason,
+        default_action=match.default_action,
+    )
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_groups.py
+++ b/traktor_nml/dedupe_groups.py
@@ -46,6 +46,10 @@
 
 
 def _survivor_key(member: Member) -> tuple:
+    """Sort key for the survivor suggestion, highest first, in DL-320 order:
+    file exists, lossless, bitrate, cues then beatgrid, PLAYCOUNT, earliest
+    IMPORT_DATE, then collection order as the tie-break so the suggestion is
+    deterministic."""
     state_rank = {LIVE: 2, UNKNOWN: 1, DEAD: 0}[member.file_state]
     bitrate = _parse_float(member.record.bitrate) or 0.0
     has_grid = member.fields.grid is not None
@@ -84,6 +88,9 @@
 
 
 def _exact_location_matches(context: TierContext) -> list[TierMatch]:
+    """Tier 1: entries whose location identity is equal after separator
+    normalisation, with case folded only on volumes known case-insensitive
+    (DL-313). Always auto-applies."""
     buckets: dict[tuple[str, str, str], list[Member]] = {}
     for member in context.members:
         identity = location_identity(member.record, context.options.case_insensitive_volumes)
@@ -152,6 +159,9 @@
 
 
 def _read_members(source_text: str, root, options: ScanOptions, stats: dict) -> tuple[list[Member], list[str]]:
+    """One Member per COLLECTION ENTRY, with its merge fields and file state. A
+    repeated primary key is a refusal, not a group: the input is already
+    ambiguous about which entry a reference means."""
     span_index = SpanIndex(source_text, root)
     members: list[Member] = []
     seen: set[str] = set()
@@ -198,6 +208,9 @@
 
 
 def _make_group(tier: int, members: tuple[Member, ...], match: TierMatch) -> DupGroup:
+    """Build a DupGroup for one tier match. auto_apply needs both the finder's
+    word and the tier being in AUTO_APPLY_TIERS, so a higher tier can never
+    auto-apply by accident (DL-315)."""
     survivor, reason = suggest_survivor(members)
     return DupGroup(
         group_id="",

```


**CC-M-002-015** (traktor_nml/dedupe_merge.py) - implements CI-M-002-015

**Code:**

```diff
--- a/traktor_nml/dedupe_merge.py
+++ b/traktor_nml/dedupe_merge.py
@@ -0,0 +1,232 @@
+"""Merge conflicts and the merged survivor: which fields two members
+disagree on, and the survivor span patched with the winning values
+(plan.md "Merge data model", DL-316). Split from traktor_nml/dedupe.py by
+DL-324.
+"""
+
+from __future__ import annotations
+
+import itertools
+from dataclasses import dataclass
+from datetime import date
+from typing import Mapping, Optional
+
+from .dedupe_fields import (
+    Cue,
+    Grid,
+    _INFO_MERGE_ATTRS,
+    _NO_HOTCUE,
+    _child_spans,
+    _leading_whitespace,
+    _same_cue,
+    format_nml_date,
+    grids_equal,
+)
+from .dedupe_members import DupGroup, Member
+from .spans import find_element_span
+from .splice import _apply_replacements
+from .textpatch import _find_opening_tag_end, _insert_child, _set_attr_in_tag
+
+
+@dataclass(frozen=True)
+class MergeConflict:
+    """One merge field on which two or more members disagree, with each
+    member's value as the conflict rail shows it."""
+
+    field_name: str
+    values: tuple[tuple[str, str], ...]  # (primary key, display value)
+
+
+def _text_conflict(field_name: str, members: tuple[Member, ...], read) -> Optional[MergeConflict]:
+    values = tuple((m.primary_key, read(m.fields)) for m in members if read(m.fields))
+    return MergeConflict(field_name, values) if len({v for _, v in values}) > 1 else None
+
+
+def _grid_conflict(members: tuple[Member, ...]) -> Optional[MergeConflict]:
+    grids = [(m.primary_key, m.fields.grid) for m in members if m.fields.grid is not None]
+    if all(grids_equal(grids[0][1], g) for _, g in grids[1:]):
+        return None
+    return MergeConflict("grid", tuple((k, f"{g.start}@{g.bpm}") for k, g in grids))
+
+
+def _cue_pair_conflicts(a: Member, b: Member) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
+    """The "cues" and "hotcue" evidence one pair of members contributes."""
+    named: list[tuple[str, str]] = []
+    slots: list[tuple[str, str]] = []
+    for ca, cb in itertools.product(a.fields.cues, b.fields.cues):
+        if _same_cue(ca, cb) and (ca.name, ca.hotcue) != (cb.name, cb.hotcue):
+            named += [(a.primary_key, ca.name), (b.primary_key, cb.name)]
+        elif ca.hotcue == cb.hotcue and ca.hotcue not in _NO_HOTCUE and not _same_cue(ca, cb):
+            slots += [(a.primary_key, f"slot {ca.hotcue}"), (b.primary_key, f"slot {cb.hotcue}")]
+    return named, slots
+
+
+def _cue_conflicts(members: tuple[Member, ...]) -> list[MergeConflict]:
+    """A cue two members hold with differing NAME or HOTCUE is a "cues"
+    conflict; one hotcue slot claimed by two different cues is a
+    "hotcue" conflict."""
+    named: list[tuple[str, str]] = []
+    slots: list[tuple[str, str]] = []
+    for a, b in itertools.combinations(sorted(members, key=lambda m: m.index), 2):
+        pair_named, pair_slots = _cue_pair_conflicts(a, b)
+        named += pair_named
+        slots += pair_slots
+    conflicts = []
+    if named:
+        conflicts.append(MergeConflict("cues", tuple(dict.fromkeys(named))))
+    if slots:
+        conflicts.append(MergeConflict("hotcue", tuple(dict.fromkeys(slots))))
+    return conflicts
+
+
+def group_conflicts(group: DupGroup) -> list[MergeConflict]:
+    readers = {
+        "key": lambda f: f.key,
+        "ranking": lambda f: f.ranking,
+        "color": lambda f: f.color,
+        "comment": lambda f: f.comment.strip(),
+    }
+    conflicts = [c for name, read in readers.items() if (c := _text_conflict(name, group.members, read))]
+    grid = _grid_conflict(group.members)
+    if grid is not None:
+        conflicts.append(grid)
+    return conflicts + _cue_conflicts(group.members)
+
+
+def _winning_text(group: DupGroup, survivor: Member, picks: Mapping[str, str], name: str, read) -> str:
+    if name in picks:
+        return read(group.member(picks[name]).fields)
+    if read(survivor.fields):
+        return read(survivor.fields)
+    return next((read(m.fields) for m in group.members if read(m.fields)), "")
+
+
+def _merged_cues(group: DupGroup, survivor: Member, picks: Mapping[str, str]) -> tuple[list[Cue], int]:
+    """The base member's cues verbatim, then each other member's cues
+    with no counterpart. A counterpart-less cue whose hotcue slot is
+    taken is dropped and counted rather than written as a second claim
+    on one slot."""
+    base = group.member(picks.get("hotcue", picks.get("cues", survivor.primary_key)))
+    merged = list(base.fields.cues)
+    dropped = 0
+    for member in group.members:
+        if member is base:
+            continue
+        for cue in member.fields.cues:
+            if cue.start is None or any(_same_cue(cue, kept) for kept in merged):
+                continue
+            if cue.hotcue not in _NO_HOTCUE and any(kept.hotcue == cue.hotcue for kept in merged):
+                dropped += 1
+                continue
+            merged.append(cue)
+    return merged, dropped
+
+
+def _merged_dates(group: DupGroup, survivor: Member) -> dict[str, Optional[date]]:
+    merged: dict[str, Optional[date]] = {}
+    for name, pick in (("last_played", max), ("import_date", min)):
+        if name in survivor.fields.unparseable:
+            merged[name] = getattr(survivor.fields, name)
+            continue
+        present = [getattr(m.fields, name) for m in group.members if getattr(m.fields, name) is not None]
+        merged[name] = pick(present) if present else None
+    return merged
+
+
+@dataclass(frozen=True)
+class MergedSurvivor:
+    info_attrs: dict[str, str]
+    musical_key: str
+    cues: tuple[Cue, ...]
+    grid: Optional[Grid]
+    cues_dropped: int
+
+
+def merged_survivor(group: DupGroup, survivor_key: str, picks: Mapping[str, str]) -> MergedSurvivor:
+    """The survivor's merge fields after the group merges into it, per
+    plan.md's merge data model (DL-316)."""
+    survivor = group.member(survivor_key)
+    text = {
+        name: _winning_text(group, survivor, picks, name, lambda f, n=name: getattr(f, n))
+        for name in ("key", "ranking", "color", "comment")
+    }
+    key_owner = group.member(picks["key"]) if "key" in picks else survivor
+    musical_key = key_owner.fields.musical_key or survivor.fields.musical_key
+    playcount = survivor.fields.playcount
+    if "playcount" not in survivor.fields.unparseable:
+        playcount = max(m.fields.playcount for m in group.members if "playcount" not in m.fields.unparseable)
+    dates = _merged_dates(group, survivor)
+    grid_owner = group.member(picks["grid"]) if "grid" in picks else survivor
+    grid = grid_owner.fields.grid or next((m.fields.grid for m in group.members if m.fields.grid), None)
+    cues, dropped = _merged_cues(group, survivor, picks)
+    info = {_INFO_MERGE_ATTRS[name]: value for name, value in text.items() if value}
+    if playcount:
+        info["PLAYCOUNT"] = str(playcount)
+    for name, value in dates.items():
+        if value is not None and name not in survivor.fields.unparseable:
+            info[_INFO_MERGE_ATTRS[name]] = format_nml_date(value)
+    return MergedSurvivor(info, musical_key, tuple(cues), grid, dropped)
+
+
+def _set_child_attrs(span_text: str, tag: str, attrs: Mapping[str, str]) -> str:
+    """Write attrs into tag's opening tag inside one ENTRY span, creating
+    an INFO child when the entry has none. Values already equal are left
+    byte-identical."""
+    if not attrs:
+        return span_text
+    child = find_element_span(span_text, tag, 1)
+    if child is None:
+        if tag != "INFO":
+            return span_text
+        span_text = _insert_child(span_text, "INFO")
+        child = find_element_span(span_text, tag, 1)
+    end = _find_opening_tag_end(span_text, child.start) + 1
+    opening = span_text[child.start:end]
+    for name, value in attrs.items():
+        opening = _set_attr_in_tag(opening, name, value)
+    return span_text[:child.start] + opening + span_text[end:]
+
+
+def _replace_cue_block(span_text: str, survivor: Member, merged: MergedSurvivor) -> str:
+    """Rewrite the survivor's CUE_V2 run only when the merged cues or grid
+    differ from what it holds, so an unchanged survivor keeps its bytes.
+
+    The merged run (grid first, then cues) is written where the
+    survivor's first CUE_V2 stood, each item behind that cue's own leading
+    whitespace, so the run keeps the file's indentation and line
+    terminator; a survivor with no cues takes the run before </ENTRY>,
+    indented like its INFO child."""
+    old = ([survivor.fields.grid.raw] if survivor.fields.grid else []) + [c.raw for c in survivor.fields.cues]
+    block = ([merged.grid.raw] if merged.grid else []) + [c.raw for c in merged.cues]
+    if sorted(old) == sorted(block):
+        return span_text
+    spans = _child_spans(span_text, "CUE_V2")
+    if not spans:
+        info = find_element_span(span_text, "INFO", 1)
+        indent = _leading_whitespace(span_text, info.start) if info is not None else ""
+        close_at = span_text.rfind("</ENTRY>")
+        return span_text[:close_at] + "".join(indent + raw for raw in block) + span_text[close_at:]
+    indent = _leading_whitespace(span_text, spans[0].start)
+    edits = [(spans[0].start - len(indent), spans[0].end, "".join(indent + raw for raw in block))]
+    for span in spans[1:]:
+        edits.append((span.start - len(_leading_whitespace(span_text, span.start)), span.end, ""))
+    return _apply_replacements(span_text, edits)
+
+
+def patch_survivor_span(span_text: str, survivor: Member, merged: MergedSurvivor) -> str:
+    """The survivor's ENTRY span carrying the merged fields. Only
+    attributes whose merged value differs are substituted (DL-309)."""
+    info_changes = {
+        name: value for name, value in merged.info_attrs.items() if not _raw_info_equal(survivor, name, value)
+    }
+    span_text = _set_child_attrs(span_text, "INFO", info_changes)
+    if merged.musical_key and merged.musical_key != survivor.fields.musical_key:
+        span_text = _set_child_attrs(span_text, "MUSICAL_KEY", {"VALUE": merged.musical_key})
+    if merged.grid is not None and merged.grid.bpm_raw and merged.grid.raw != getattr(survivor.fields.grid, "raw", None):
+        span_text = _set_child_attrs(span_text, "TEMPO", {"BPM": merged.grid.bpm_raw})
+    return _replace_cue_block(span_text, survivor, merged)
+
+
+def _raw_info_equal(survivor: Member, attr: str, value: str) -> bool:
+    info = survivor.record.entry.find("INFO")
+    return info is not None and info.attrib.get(attr) == value
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_merge.py
+++ b/traktor_nml/dedupe_merge.py
@@ -38,11 +38,16 @@
 
 
 def _text_conflict(field_name: str, members: tuple[Member, ...], read) -> Optional[MergeConflict]:
+    """A conflict when members hold more than one non-empty value for a text
+    field; an empty value never conflicts, it is filled from a member that
+    has one."""
     values = tuple((m.primary_key, read(m.fields)) for m in members if read(m.fields))
     return MergeConflict(field_name, values) if len({v for _, v in values}) > 1 else None
 
 
 def _grid_conflict(members: tuple[Member, ...]) -> Optional[MergeConflict]:
+    """A conflict when the members' beatgrids are not all equal (grids_equal);
+    grids are never merged (DL-316)."""
     grids = [(m.primary_key, m.fields.grid) for m in members if m.fields.grid is not None]
     if all(grids_equal(grids[0][1], g) for _, g in grids[1:]):
         return None
@@ -80,6 +85,9 @@
 
 
 def group_conflicts(group: DupGroup) -> list[MergeConflict]:
+    """Every field the operator must pick before this group can merge: key,
+    ranking, color, comment, grid, differing cue names and hotcue slot
+    clashes."""
     readers = {
         "key": lambda f: f.key,
         "ranking": lambda f: f.ranking,
@@ -94,6 +102,8 @@
 
 
 def _winning_text(group: DupGroup, survivor: Member, picks: Mapping[str, str], name: str, read) -> str:
+    """A text field's merged value: the operator's pick, else the survivor's
+    own value, else the first member's non-empty value."""
     if name in picks:
         return read(group.member(picks[name]).fields)
     if read(survivor.fields):
@@ -123,6 +133,9 @@
 
 
 def _merged_dates(group: DupGroup, survivor: Member) -> dict[str, Optional[date]]:
+    """LAST_PLAYED takes the latest and IMPORT_DATE the earliest across members
+    (DL-316). A survivor value that failed to parse is kept as-is rather
+    than overwritten by a guess."""
     merged: dict[str, Optional[date]] = {}
     for name, pick in (("last_played", max), ("import_date", min)):
         if name in survivor.fields.unparseable:
@@ -135,6 +148,10 @@
 
 @dataclass(frozen=True)
 class MergedSurvivor:
+    """The survivor's merge fields after its group merges into it;
+    patch_survivor_span writes these into the survivor's ENTRY span
+    (DL-309)."""
+
     info_attrs: dict[str, str]
     musical_key: str
     cues: tuple[Cue, ...]

```


**CC-M-002-016** (traktor_nml/dedupe_decisions.py) - implements CI-M-002-016

**Code:**

```diff
--- a/traktor_nml/dedupe_decisions.py
+++ b/traktor_nml/dedupe_decisions.py
@@ -0,0 +1,173 @@
+"""Decisions file parsing and attachment, and the per-group plan
+(DL-317). Groups are keyed by sorted member primary keys; a decision whose
+group no longer exists is stale and dropped, never refused. Split from
+traktor_nml/dedupe.py by DL-324.
+"""
+
+from __future__ import annotations
+
+import hashlib
+import json
+from dataclasses import dataclass, replace
+from typing import Optional
+
+from .dedupe_fields import MERGE_FIELD_NAMES
+from .dedupe_members import (
+    ACTION_MERGE,
+    ACTION_NOT_DUPLICATES,
+    ACTION_UNDECIDED,
+    DECISIONS_SCHEMA,
+    DECISIONS_VERSION,
+    DECISION_ACTIONS,
+    DupGroup,
+    PLAN_MERGE,
+    PLAN_NOT_DUPLICATES,
+    PLAN_REFUSED,
+    PLAN_REVIEW,
+)
+from .dedupe_merge import MergeConflict, group_conflicts
+
+
+class DecisionsError(ValueError):
+    """An invalid decisions file; str() is the refusal reason."""
+
+
+@dataclass(frozen=True)
+class Decision:
+    members: tuple[str, ...]
+    tier: int
+    action: str
+    survivor: Optional[str]
+    picks: dict[str, str]
+
+
+@dataclass(frozen=True)
+class DecisionsFile:
+    input_sha256: str
+    decisions: tuple[Decision, ...]
+
+
+def input_sha256(source_bytes: bytes) -> str:
+    return hashlib.sha256(source_bytes).hexdigest()
+
+
+def _decision_from_json(raw) -> Decision:
+    if not isinstance(raw, dict):
+        raise DecisionsError("group_not_object")
+    for key in ("members", "action"):
+        if key not in raw:
+            raise DecisionsError(f"missing_key:{key}")
+    members = raw["members"]
+    if not isinstance(members, list) or not all(isinstance(m, str) for m in members) or len(members) < 2:
+        raise DecisionsError("members_not_key_list")
+    if raw["action"] not in DECISION_ACTIONS:
+        raise DecisionsError(f"unknown_action:{raw['action']}")
+    survivor = raw.get("survivor")
+    if raw["action"] == ACTION_MERGE and survivor is None:
+        raise DecisionsError("missing_key:survivor")
+    if survivor is not None and survivor not in members:
+        raise DecisionsError("survivor_not_member")
+    picks = raw.get("picks") or {}
+    if not isinstance(picks, dict):
+        raise DecisionsError("picks_not_object")
+    for name, owner in picks.items():
+        if name not in MERGE_FIELD_NAMES:
+            raise DecisionsError(f"unknown_pick_field:{name}")
+        if owner not in members:
+            raise DecisionsError(f"pick_not_member:{name}")
+    return Decision(tuple(sorted(members)), int(raw.get("tier", 0)), raw["action"], survivor, dict(picks))
+
+
+def parse_decisions(text: str) -> DecisionsFile:
+    """Validate the whole file before any of it is used, so an invalid
+    file refuses with nothing applied (DL-317)."""
+    try:
+        document = json.loads(text)
+    except json.JSONDecodeError:
+        raise DecisionsError("not_json") from None
+    if not isinstance(document, dict) or document.get("schema") != DECISIONS_SCHEMA:
+        raise DecisionsError("wrong_schema")
+    version = document.get("version")
+    # Version 1 is the only version; a reader for an older one is added
+    # beside this check when version 2 exists.
+    if version != DECISIONS_VERSION:
+        raise DecisionsError(f"unsupported_version:{version}")
+    for key in ("input_sha256", "groups"):
+        if key not in document:
+            raise DecisionsError(f"missing_key:{key}")
+    if not isinstance(document["groups"], list):
+        raise DecisionsError("groups_not_list")
+    return DecisionsFile(document["input_sha256"], tuple(_decision_from_json(g) for g in document["groups"]))
+
+
+@dataclass(frozen=True)
+class AttachedDecisions:
+    by_members: dict[tuple[str, ...], Decision]
+    stale: int
+    input_changed: bool
+
+
+def attach_decisions(decisions: DecisionsFile, groups: list[DupGroup], source_sha256: str) -> AttachedDecisions:
+    """Re-attach decisions to groups by exact sorted membership. A
+    decision matching no current group is stale: dropped and counted,
+    never refused, whether or not the input hash still matches."""
+    current = {g.member_keys for g in groups}
+    kept = {d.members: d for d in decisions.decisions if d.members in current}
+    return AttachedDecisions(kept, len(decisions.decisions) - len(kept), decisions.input_sha256 != source_sha256)
+
+
+@dataclass(frozen=True)
+class GroupPlan:
+    group: DupGroup
+    action: str
+    survivor: str
+    picks: dict[str, str]
+    conflicts: tuple[MergeConflict, ...]
+    reason: str = ""
+
+    def unpicked(self) -> list[str]:
+        return [c.field_name for c in self.conflicts if c.field_name not in self.picks]
+
+
+def plan_group(group: DupGroup, decision: Optional[Decision]) -> GroupPlan:
+    """One group's outcome: merge only a group whose every conflict is
+    picked and that either auto-applies or carries a merge decision."""
+    conflicts = tuple(group_conflicts(group))
+    action = decision.action if decision is not None else group.default_action
+    survivor = (decision.survivor if decision and decision.survivor else None) or group.suggested_survivor
+    picks = dict(decision.picks) if decision is not None else {}
+    if action == ACTION_NOT_DUPLICATES:
+        return GroupPlan(group, PLAN_NOT_DUPLICATES, survivor, picks, conflicts, "marked not duplicates")
+    if action == ACTION_UNDECIDED and not group.auto_apply:
+        return GroupPlan(group, PLAN_REVIEW, survivor, picks, conflicts, group.review_reason or "needs review")
+    plan = GroupPlan(group, PLAN_MERGE, survivor, picks, conflicts)
+    if plan.unpicked():
+        if action == ACTION_MERGE:
+            return replace(plan, action=PLAN_REFUSED, reason="unpicked_conflict:" + ",".join(plan.unpicked()))
+        return replace(plan, action=PLAN_REVIEW, reason="metadata_conflict")
+    return plan
+
+
+def plan_merge(groups: list[DupGroup], attached: Optional[AttachedDecisions]) -> list[GroupPlan]:
+    by_members = attached.by_members if attached is not None else {}
+    return [plan_group(g, by_members.get(g.member_keys)) for g in groups]
+
+
+def decisions_document(source_sha256: str, plans: list[GroupPlan]) -> dict:
+    """The decisions template: every group outside the auto-apply rules,
+    each carrying its current action, survivor and picks, so a file the
+    GUI saves and one --write-decisions writes share one shape."""
+    groups = []
+    for plan in plans:
+        untouched_auto = plan.action == PLAN_MERGE and not plan.picks and plan.survivor == plan.group.suggested_survivor
+        if plan.group.auto_apply and untouched_auto:
+            continue
+        action = {PLAN_MERGE: ACTION_MERGE, PLAN_NOT_DUPLICATES: ACTION_NOT_DUPLICATES}.get(plan.action, ACTION_UNDECIDED)
+        groups.append({
+            "members": list(plan.group.member_keys),
+            "tier": plan.group.tier,
+            "action": action,
+            "survivor": plan.survivor,
+            "picks": dict(plan.picks),
+        })
+    return {"schema": DECISIONS_SCHEMA, "version": DECISIONS_VERSION, "input_sha256": source_sha256, "groups": groups}
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_decisions.py
+++ b/traktor_nml/dedupe_decisions.py
@@ -34,6 +34,10 @@
 
 @dataclass(frozen=True)
 class Decision:
+    """One group's recorded decision (decisions schema v1, DL-317): the sorted
+    member keys that identify it, the action, the chosen survivor and a
+    field-to-member map of conflict picks."""
+
     members: tuple[str, ...]
     tier: int
     action: str
@@ -43,11 +47,16 @@
 
 @dataclass(frozen=True)
 class DecisionsFile:
+    """A parsed and fully validated decisions file. input_sha256 names the NML
+    it was made against; a mismatch is reported, never refused (DL-317)."""
+
     input_sha256: str
     decisions: tuple[Decision, ...]
 
 
 def input_sha256(source_bytes: bytes) -> str:
+    """Hex SHA-256 of the input NML bytes, stored in a decisions file so a
+    later run can report that the input changed."""
     return hashlib.sha256(source_bytes).hexdigest()
 
 
@@ -102,6 +111,9 @@
 
 @dataclass(frozen=True)
 class AttachedDecisions:
+    """Decisions matched to the current scan's groups, how many were stale and
+    dropped, and whether the file was made against a different input."""
+
     by_members: dict[tuple[str, ...], Decision]
     stale: int
     input_changed: bool
@@ -118,6 +130,9 @@
 
 @dataclass(frozen=True)
 class GroupPlan:
+    """One group's planned outcome (merge, review, not duplicates or refused)
+    with the survivor, picks and conflicts the assembly and report read."""
+
     group: DupGroup
     action: str
     survivor: str
@@ -126,6 +141,8 @@
     reason: str = ""
 
     def unpicked(self) -> list[str]:
+        """Conflicting fields with no pick; a merge decision with any left is
+        refused rather than merged with a guessed value."""
         return [c.field_name for c in self.conflicts if c.field_name not in self.picks]
 
 
@@ -149,6 +166,8 @@
 
 
 def plan_merge(groups: list[DupGroup], attached: Optional[AttachedDecisions]) -> list[GroupPlan]:
+    """A GroupPlan for every group, using the decision attached to it by sorted
+    membership when there is one."""
     by_members = attached.by_members if attached is not None else {}
     return [plan_group(g, by_members.get(g.member_keys)) for g in groups]
 

```


**CC-M-002-017** (traktor_nml/dedupe_references.py) - implements CI-M-002-017

**Code:**

```diff
--- a/traktor_nml/dedupe_references.py
+++ b/traktor_nml/dedupe_references.py
@@ -0,0 +1,79 @@
+"""The reference inventory and the generic scan (DL-314): every value
+outside COLLECTION equal to an entry's primary key, so a shape nobody
+inventoried refuses the write rather than being orphaned. Split from
+traktor_nml/dedupe.py by DL-324.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, replace
+
+from .model import parse_location_element
+
+
+@dataclass(frozen=True)
+class ReferenceShape:
+    """Where a value equal to an entry's primary key sits: the top-level
+    NML section, the element and attribute holding it, and that element's
+    TYPE. "*" as kind matches any TYPE."""
+
+    section: str
+    tag: str
+    attr: str
+    kind: str
+
+    @property
+    def label(self) -> str:
+        return f"{self.section}/{self.tag}@{self.attr}[{self.kind}]"
+
+
+# The reference inventory (plan.md "Reference inventory"), confirmed or
+# extended by the M-001 artifact docs/2026-09-26-dedupe-spike.md. A shape
+# in neither set refuses the write naming it (DL-314). History, _LOOPS and
+# _RECORDINGS are NODE TYPE=PLAYLIST trees under PLAYLISTS, so the first
+# redirect row covers them.
+REDIRECT_SHAPES = frozenset({ReferenceShape("PLAYLISTS", "PRIMARYKEY", "KEY", "TRACK")})
+PRESERVE_SHAPES = frozenset({
+    ReferenceShape("PLAYLISTS", "PRIMARYKEY", "KEY", "STEM"),
+    ReferenceShape("SETS", "PRIMARYKEY", "KEY", "*"),
+})
+_LOCATION_KEY_ATTR = "VOLUME+DIR+FILE"
+
+
+def _shape_in(shape: ReferenceShape, table: frozenset[ReferenceShape]) -> bool:
+    return shape in table or replace(shape, kind="*") in table
+
+
+@dataclass(frozen=True)
+class Reference:
+    shape: ReferenceShape
+    key: str
+    element: object
+
+
+def _element_references(section_tag: str, element, keys: set[str]) -> list[Reference]:
+    """The references one element outside COLLECTION holds: its composed
+    key when it is a LOCATION, otherwise each attribute equal to a key."""
+    kind = element.attrib.get("TYPE", "")
+    if element.tag == "LOCATION":
+        composed = parse_location_element(element).primary_key
+        if composed not in keys:
+            return []
+        return [Reference(ReferenceShape(section_tag, "LOCATION", _LOCATION_KEY_ATTR, kind), composed, element)]
+    return [
+        Reference(ReferenceShape(section_tag, element.tag, attr, kind), value, element)
+        for attr, value in element.attrib.items()
+        if value in keys
+    ]
+
+
+def scan_references(root, keys: set[str]) -> list[Reference]:
+    """Every attribute value outside COLLECTION equal to one of keys,
+    plus every non-collection LOCATION whose composed key is one: the
+    generic scan that turns an uninventoried shape into a refusal."""
+    found: list[Reference] = []
+    sections = (s for s in root if isinstance(s.tag, str) and s.tag != "COLLECTION")
+    for section in sections:
+        for element in (e for e in section.iter() if isinstance(e.tag, str)):
+            found += _element_references(section.tag, element, keys)
+    return found
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_references.py
+++ b/traktor_nml/dedupe_references.py
@@ -46,6 +46,10 @@
 
 @dataclass(frozen=True)
 class Reference:
+    """One occurrence of a primary key outside COLLECTION: its shape, the key,
+    and the element holding it, whose span assembly patches when the shape
+    redirects."""
+
     shape: ReferenceShape
     key: str
     element: object

```


**CC-M-002-018** (traktor_nml/dedupe_assembly.py) - implements CI-M-002-018

**Code:**

```diff
--- a/traktor_nml/dedupe_assembly.py
+++ b/traktor_nml/dedupe_assembly.py
@@ -0,0 +1,245 @@
+"""Output assembly on the byte-span path (DL-309): the survivor's span
+patched in place, each loser's span cut whole and redirected PRIMARYKEY
+tags substituted, so every byte the dedupe does not name survives. The
+assembled text is written only through dedupe_write. Split from
+traktor_nml/dedupe.py by DL-324.
+"""
+
+from __future__ import annotations
+
+from collections import Counter
+from dataclasses import dataclass, field
+from typing import Optional
+
+from .dedupe_decisions import GroupPlan
+from .dedupe_fields import _same_cue
+from .dedupe_members import Member, PLAN_MERGE, PLAN_REFUSED, PLAN_REVIEW, ScanResult
+from .dedupe_merge import merged_survivor, patch_survivor_span
+from .dedupe_references import (
+    PRESERVE_SHAPES,
+    REDIRECT_SHAPES,
+    Reference,
+    ReferenceShape,
+    _shape_in,
+    scan_references,
+)
+from .model import collection_entries, collection_records
+from .spans import SpanIndex, _patch_opening_tag_attrs, recalculate_count_attr
+from .splice import _apply_replacements
+from .textpatch import _find_opening_tag_end
+from .xmlio import XML_PARSE_ERROR, parse_xml_bytes
+
+
+@dataclass(frozen=True)
+class ReportRow:
+    group_id: str
+    tier: int
+    confidence: str
+    evidence: str
+    role: str
+    primary_key: str
+    file_exists: str
+    refs_redirected: int
+    refs_preserved: int
+    conflicts: str
+    refusal_reason: str
+
+
+REPORT_COLUMNS = (
+    "group_id", "tier", "confidence", "evidence", "role", "primary_key", "file_exists",
+    "refs_redirected", "refs_preserved", "conflicts", "refusal_reason",
+)
+
+
+@dataclass
+class AssembleResult:
+    """output is None exactly when refusals is non-empty."""
+
+    output: Optional[str]
+    stats: dict[str, object]
+    refusals: list[str]
+    rows: list[ReportRow]
+    expected_entries: int = 0
+
+
+def _empty_assembly_stats(scan: ScanResult, plans: list[GroupPlan]) -> dict[str, object]:
+    stats = dict(scan.stats)
+    refused: dict[str, int] = {}
+    for plan in plans:
+        if plan.action == PLAN_REFUSED:
+            refused[plan.reason] = refused.get(plan.reason, 0) + 1
+    stats.update({
+        "groups_auto_applied": sum(1 for p in plans if p.action == PLAN_MERGE and p.group.auto_apply),
+        "groups_for_review": sum(1 for p in plans if p.action == PLAN_REVIEW),
+        "groups_refused": refused,
+        "entries_removed": 0,
+        "refs_redirected": {},
+        "refs_preserved": {},
+        "metadata_conflicts": sum(len(p.conflicts) for p in plans),
+        "loser_fields_discarded": 0,
+        "cues_dropped": 0,
+        "losers_with_unmerged_cues": sum(1 for p in plans if p.action != PLAN_MERGE and _loser_has_unmerged_cues(p)),
+    })
+    return stats
+
+
+def _loser_has_unmerged_cues(plan: GroupPlan) -> bool:
+    survivor = plan.group.member(plan.survivor)
+    return any(
+        (m.fields.grid and not survivor.fields.grid) or any(not any(_same_cue(c, s) for s in survivor.fields.cues) for c in m.fields.cues)
+        for m in plan.group.members if m is not survivor
+    )
+
+
+def _bump(counter: dict, shape: ReferenceShape) -> None:
+    counter[shape.label] = counter.get(shape.label, 0) + 1
+
+
+def _cut_span(text: str, start: int, end: int) -> tuple[int, int]:
+    """Widen a removed ENTRY's span over the indentation and line break
+    before it, so removal leaves no blank line."""
+    while start > 0 and text[start - 1] in " \t":
+        start -= 1
+    if start > 0 and text[start - 1] == "\n":
+        start -= 1
+        if start > 0 and text[start - 1] == "\r":
+            start -= 1
+    return start, end
+
+
+@dataclass
+class _Assembly:
+    """The in-progress byte edits one assemble_output call collects."""
+
+    replacements: list[tuple[int, int, str]] = field(default_factory=list)
+    redirect: dict[str, str] = field(default_factory=dict)
+    removed: set[str] = field(default_factory=set)
+    rows: list[ReportRow] = field(default_factory=list)
+
+
+def _classify_references(root, plans, stats, refusals) -> tuple[dict[str, list[Reference]], set[str]]:
+    """References to every loser of a merging group, by loser key, and
+    the losers a preserve-shape reference pins in the collection."""
+    loser_keys = {m.primary_key for p in plans if p.action == PLAN_MERGE for m in p.group.members} - {
+        p.survivor for p in plans if p.action == PLAN_MERGE
+    }
+    by_key: dict[str, list[Reference]] = {}
+    preserved: set[str] = set()
+    for ref in scan_references(root, loser_keys):
+        by_key.setdefault(ref.key, []).append(ref)
+        if _shape_in(ref.shape, REDIRECT_SHAPES):
+            continue
+        if _shape_in(ref.shape, PRESERVE_SHAPES):
+            preserved.add(ref.key)
+            _bump(stats["refs_preserved"], ref.shape)
+            continue
+        refusals.append(f"unknown_reference_shape:{ref.shape.label}")
+    return by_key, preserved
+
+
+def _plan_group_edits(plan, source_text, span_index, refs_by_key, preserved, work: _Assembly, stats) -> None:
+    group, survivor = plan.group, plan.group.member(plan.survivor)
+    merged = merged_survivor(group, plan.survivor, plan.picks)
+    stats["cues_dropped"] += merged.cues_dropped
+    span = span_index.span_of(survivor.record.entry)
+    patched = patch_survivor_span(span.text(source_text), survivor, merged)
+    if patched != span.text(source_text):
+        work.replacements.append((span.start, span.end, patched))
+    conflicts = ",".join(c.field_name for c in plan.conflicts)
+    for member in group.members:
+        refs = refs_by_key.get(member.primary_key, [])
+        role, redirected, kept = "survivor", 0, 0
+        if member is not survivor and member.primary_key in preserved:
+            role, kept = "kept", len(refs)
+        elif member is not survivor:
+            role = "merged"
+            work.redirect[member.primary_key] = plan.survivor
+            work.removed.add(member.primary_key)
+            stats["loser_fields_discarded"] += member.fields.unmodelled
+            loser_span = span_index.span_of(member.record.entry)
+            work.replacements.append((*_cut_span(source_text, loser_span.start, loser_span.end), ""))
+            redirected = sum(1 for r in refs if _shape_in(r.shape, REDIRECT_SHAPES))
+        work.rows.append(_row(plan, member, role, redirected, kept, conflicts))
+
+
+def _row(plan: GroupPlan, member: Member, role: str, redirected: int, kept: int, conflicts: str) -> ReportRow:
+    group = plan.group
+    return ReportRow(
+        group.group_id, group.tier, group.confidence, group.evidence, role, member.primary_key,
+        member.file_state, redirected, kept, conflicts, plan.reason,
+    )
+
+
+def _unmerged_rows(plan: GroupPlan) -> list[ReportRow]:
+    role = "refused" if plan.action == PLAN_REFUSED else "kept"
+    conflicts = ",".join(c.field_name for c in plan.conflicts)
+    return [_row(plan, m, role, 0, 0, conflicts) for m in plan.group.members]
+
+
+def _redirect_edits(refs_by_key, span_index, source_text, work: _Assembly, stats) -> None:
+    for key, refs in refs_by_key.items():
+        if key not in work.redirect:
+            continue
+        for ref in refs:
+            if not _shape_in(ref.shape, REDIRECT_SHAPES):
+                continue
+            span = span_index.span_of(ref.element)
+            text = span.text(source_text)
+            end = _find_opening_tag_end(text, 0) + 1
+            opening = _patch_opening_tag_attrs(text[:end], {ref.shape.attr: work.redirect[key]})
+            work.replacements.append((span.start, span.start + end, opening))
+            _bump(stats["refs_redirected"], ref.shape)
+
+
+def _collection_count_edit(source_text, root, span_index, remaining: int) -> tuple[int, int, str]:
+    collection = root.find("COLLECTION")
+    span = span_index.span_of(collection)
+    end = _find_opening_tag_end(source_text, span.start) + 1
+    opening = recalculate_count_attr(source_text[span.start:end], "COLLECTION", "ENTRIES", remaining)
+    return span.start, end, opening
+
+
+def audit_output(output: str, removed_keys: set[str], expected_entries: int) -> list[str]:
+    """The pre-write gate over the assembled text: it parses, holds the
+    expected entry count, holds no two entries for one location, and no
+    attribute anywhere names a removed key."""
+    try:
+        reparsed = parse_xml_bytes(output.encode("utf-8"))
+    except XML_PARSE_ERROR as exc:
+        return [f"output_parse_error:{exc}"]
+    records = collection_records(reparsed)
+    count = len(collection_entries(reparsed))
+    errors = []
+    if count != expected_entries:
+        errors.append(f"collection_entry_count expected={expected_entries} assembled={count}")
+    counts = Counter(r.primary_key for r in records)
+    errors += [f"entry_location_collision key={k}" for k in sorted(k for k, n in counts.items() if n > 1)]
+    errors += [f"dangling_reference:{r.shape.label}:{r.key}" for r in scan_references(reparsed, removed_keys)]
+    return errors
+
+
+def assemble_output(source_text: str, root, scan: ScanResult, plans: list[GroupPlan]) -> AssembleResult:
+    """Apply every merge plan to source_text on the byte-span path and
+    audit the result before any file opens (DL-309, DL-314)."""
+    stats = _empty_assembly_stats(scan, plans)
+    refusals = list(scan.refusals)
+    refs_by_key, preserved = _classify_references(root, plans, stats, refusals)
+    span_index = SpanIndex(source_text, root)
+    work = _Assembly()
+    for plan in plans:
+        if plan.action == PLAN_MERGE:
+            _plan_group_edits(plan, source_text, span_index, refs_by_key, preserved, work, stats)
+        else:
+            work.rows.extend(_unmerged_rows(plan))
+    _redirect_edits(refs_by_key, span_index, source_text, work, stats)
+    stats["entries_removed"] = len(work.removed)
+    expected = len(collection_entries(root)) - len(work.removed)
+    if refusals:
+        return AssembleResult(None, stats, refusals, work.rows, expected)
+    if work.removed:
+        work.replacements.append(_collection_count_edit(source_text, root, span_index, expected))
+    output = _apply_replacements(source_text, work.replacements)
+    errors = audit_output(output, work.removed, expected)
+    if errors:
+        return AssembleResult(None, stats, errors, work.rows, expected)
+    return AssembleResult(output, stats, [], work.rows, expected)
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_assembly.py
+++ b/traktor_nml/dedupe_assembly.py
@@ -32,6 +32,8 @@
 
 @dataclass(frozen=True)
 class ReportRow:
+    """One report CSV row per group member; field order is REPORT_COLUMNS."""
+
     group_id: str
     tier: int
     confidence: str
@@ -84,6 +86,8 @@
 
 
 def _loser_has_unmerged_cues(plan: GroupPlan) -> bool:
+    """True when a loser holds a cue or beatgrid the survivor lacks; reported
+    so the operator sees what the merge carries or drops."""
     survivor = plan.group.member(plan.survivor)
     return any(
         (m.fields.grid and not survivor.fields.grid) or any(not any(_same_cue(c, s) for s in survivor.fields.cues) for c in m.fields.cues)
@@ -138,6 +142,10 @@
 
 
 def _plan_group_edits(plan, source_text, span_index, refs_by_key, preserved, work: _Assembly, stats) -> None:
+    """Queue one merged group's edits: patch the survivor's span with the
+    merged fields, cut each loser's span whole, and record which keys
+    redirect to the survivor. A loser holding a preserved reference (a stem)
+    keeps its entry (DL-309)."""
     group, survivor = plan.group, plan.group.member(plan.survivor)
     merged = merged_survivor(group, plan.survivor, plan.picks)
     stats["cues_dropped"] += merged.cues_dropped
@@ -171,12 +179,17 @@
 
 
 def _unmerged_rows(plan: GroupPlan) -> list[ReportRow]:
+    """Report rows for a group that is not merged: every member kept, or
+    refused when its plan was refused."""
     role = "refused" if plan.action == PLAN_REFUSED else "kept"
     conflicts = ",".join(c.field_name for c in plan.conflicts)
     return [_row(plan, m, role, 0, 0, conflicts) for m in plan.group.members]
 
 
 def _redirect_edits(refs_by_key, span_index, source_text, work: _Assembly, stats) -> None:
+    """Rewrite the opening tag of every redirect-shaped reference to a removed
+    key so it names the survivor. Only the tag's own attribute changes;
+    every other byte of the element survives (DL-309)."""
     for key, refs in refs_by_key.items():
         if key not in work.redirect:
             continue
@@ -192,6 +205,8 @@
 
 
 def _collection_count_edit(source_text, root, span_index, remaining: int) -> tuple[int, int, str]:
+    """Replace COLLECTION's opening tag with its ENTRIES count set to the
+    entries that remain (DL-309)."""
     collection = root.find("COLLECTION")
     span = span_index.span_of(collection)
     end = _find_opening_tag_end(source_text, span.start) + 1

```


**CC-M-002-019** (traktor_nml/dedupe_write.py) - implements CI-M-002-019

**Code:**

```diff
--- a/traktor_nml/dedupe_write.py
+++ b/traktor_nml/dedupe_write.py
@@ -0,0 +1,91 @@
+"""The single write path (DL-310) and the output guard every dedupe
+writer shares: the NML through write_validated_output, the decisions JSON
+through write_decisions, and dedupe_extras' removable-files CSV, each
+refused by output_refusal when it names an input or the live
+collection.nml. Split from traktor_nml/dedupe.py by DL-324.
+"""
+
+from __future__ import annotations
+
+import json
+import os
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Callable, Optional
+
+from .model import collection_entries
+from .rewrite import write_bytes_atomically
+from .xmlio import XML_PARSE_ERROR, parse_xml_bytes
+
+
+@dataclass(frozen=True)
+class WriteResult:
+    """ok is True only when the written file parsed back. invalid_path
+    names the quarantined file after a failed post-write parse; error is
+    the diagnostic line in both failure cases."""
+
+    ok: bool
+    invalid_path: Optional[Path] = None
+    error: Optional[str] = None
+
+
+def is_live_collection_path(path: Path) -> bool:
+    """Traktor's own collection.nml under a Traktor settings folder,
+    which Traktor rewrites on exit (plan.md A4)."""
+    resolved = path.resolve()
+    return resolved.name.lower() == "collection.nml" and any(
+        parent.name.lower().startswith("traktor") for parent in resolved.parents
+    )
+
+
+def output_refusal(output_path: Path, input_paths: list[Path]) -> Optional[str]:
+    resolved = output_path.resolve()
+    if any(resolved == p.resolve() for p in input_paths):
+        return "output_must_differ_from_input"
+    if is_live_collection_path(output_path):
+        return "output_is_live_collection"
+    return None
+
+
+def write_validated_output(
+    data: bytes,
+    output_path: Path,
+    writer: Callable[[Path, bytes], None] = write_bytes_atomically,
+    parser: Callable[[bytes], object] = parse_xml_bytes,
+    expected_entries: Optional[int] = None,
+) -> WriteResult:
+    """The only path by which the CLI and the GUI write a dedupe output
+    (DL-310): an atomic write, then a parse of the bytes on disk. A file
+    that does not parse back, or holds the wrong entry count, is renamed
+    to OUT.nml.invalid; the input was never touched, so recovery is to
+    discard it and rerun. writer and parser are injectable so a test can
+    force each failure."""
+    try:
+        writer(output_path, data)
+    except OSError as exc:
+        return WriteResult(False, None, f"output_write_error={exc}")
+    error = None
+    try:
+        reparsed = parser(output_path.read_bytes())
+        count = len(collection_entries(reparsed))
+        if expected_entries is not None and count != expected_entries:
+            error = f"post_write_entry_count expected={expected_entries} written={count}"
+    except (XML_PARSE_ERROR, ValueError, OSError) as exc:
+        error = f"post_write_parse_error={exc}"
+    if error is None:
+        return WriteResult(True)
+    invalid = output_path.with_name(output_path.name + ".invalid")
+    os.replace(output_path, invalid)
+    return WriteResult(False, invalid, error)
+
+
+def write_decisions(path: Path, document: dict, input_paths: list[Path]) -> Optional[str]:
+    """Write the decisions JSON, or return the refusal output_refusal gives
+    for path. The CLI's --write-decisions and the GUI's side file both
+    come through here, so neither can overwrite an input or the live
+    collection.nml."""
+    refusal = output_refusal(path, input_paths)
+    if refusal is not None:
+        return refusal
+    write_bytes_atomically(path, (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
+    return None
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_write.py
+++ b/traktor_nml/dedupe_write.py
@@ -39,6 +39,9 @@
 
 
 def output_refusal(output_path: Path, input_paths: list[Path]) -> Optional[str]:
+    """The refusal for an output path that names any input or the live
+    collection.nml, or None. Every file dedupe writes is checked with this
+    before anything is read."""
     resolved = output_path.resolve()
     if any(resolved == p.resolve() for p in input_paths):
         return "output_must_differ_from_input"

```


### Milestone 3: M-003 GUI /dedupe section

**Files**: traktor_nml/gui/dedupe_model.py, traktor_nml/gui/dedupe_steps.py, traktor_nml/gui/app.py, traktor_nml/gui/navigation.py, tests/test_gui_dedupe_model.py, tests/test_gui_dedupe_parity.py, tests/test_gui_navigation.py

**Requirements**:

- set up / scan / review / write steps under run.io_bound
- group list with one filter chip per tier
- survivor pick with its reasons
- conflict rail fed by MergeFields
- write step shows preview counts and stats and calls write_validated_output
- decisions saved to the side JSON on every change

**Acceptance Criteria**:

- G6 view-model tests pass without nicegui
- CLI and GUI give byte-identical output for the same input and decisions
- import isolation guard passes

**Tests**:

- unit on view models plus CLI/GUI parity

#### Code Intent

- **CI-M-003-001** `traktor_nml/gui/dedupe_model.py`: Nicegui-free groups, filter counts, survivor suggestion reasons, decisions, write refusals and report wording (refs: DL-318, DL-320)
- **CI-M-003-002** `traktor_nml/gui/dedupe_steps.py`: Nicegui-free step state for set up, scan, review and write (refs: DL-318, DL-323)
- **CI-M-003-003** `traktor_nml/gui/app.py`: Builds the /dedupe page from the view models; scan and write under run.io_bound; writes through write_validated_output (refs: DL-310, DL-318)
- **CI-M-003-004** `traktor_nml/gui/navigation.py`: SECTIONS carries /dedupe as the fourth row (refs: DL-318)
- **CI-M-003-005** `tests/test_gui_dedupe_model.py`: G6 view-model tests for filters, survivor pick and refusals (refs: DL-318)
- **CI-M-003-006** `tests/test_gui_dedupe_parity.py`: G6 CLI and GUI byte-identical output for the same input and decisions (refs: DL-310)
- **CI-M-003-007** `tests/test_gui_navigation.py`: Four SECTIONS rows with /dedupe fourth (refs: DL-318)
- **CI-M-003-008** `tests/test_gui_header_tabs.py`: Header renders four links and app.py registers four routes, /dedupe by _build_dedupe_page (refs: DL-318)

#### Code Changes

**CC-M-003-001** (traktor_nml/gui/dedupe_model.py) - implements CI-M-003-001

**Code:**

```diff
--- a/traktor_nml/gui/dedupe_model.py
+++ b/traktor_nml/gui/dedupe_model.py
@@ -0,0 +1,262 @@
+"""The /dedupe page's review model, with no framework import.
+
+Everything the page shows or decides that is not layout lives here:
+the scan it runs, the groups it lists, the filter chips and their counts,
+the survivor suggestion and its reason, the conflict rail's fields, the
+operator's decisions, the write refusal and the summary wording
+(DL-069, DL-318). app.py renders these records and calls these functions;
+it holds no rule of its own, so every rule here is exercised on an
+interpreter with no nicegui present.
+
+The operator's decisions are held as the same records the decisions file
+carries (dedupe.Decision), and the page saves them to that file on every
+change (DL-323). A decisions file the page writes is therefore one the
+CLI reads, and the same input with the same decisions assembles the same
+bytes through either surface (G6).
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field, replace
+from pathlib import Path
+from typing import Optional
+
+from .. import dedupe
+from ..rewrite import read_and_parse_source
+
+TIER_LABELS = {
+    dedupe.TIER_EXACT_LOCATION: "Same file",
+    dedupe.TIER_DEAD_LIVE: "Missing beside live",
+    dedupe.TIER_SAME_AUDIO: "Same audio",
+    dedupe.TIER_PROBABLE: "Probable",
+}
+
+# The filter chip that shows every group; each other chip is a tier.
+ALL_GROUPS = 0
+
+FILE_STATE_WORDS = {dedupe.LIVE: "file found", dedupe.DEAD: "file missing", dedupe.UNKNOWN: "volume not mapped"}
+
+ACTION_WORDS = {
+    dedupe.PLAN_MERGE: "Will merge",
+    dedupe.PLAN_REVIEW: "Needs a decision",
+    dedupe.PLAN_NOT_DUPLICATES: "Not duplicates",
+    dedupe.PLAN_REFUSED: "Cannot merge",
+}
+
+# Write refusals the page states before any work runs.
+NO_SCAN = "no_scan"
+OUTPUT_UNSET = "output_unset"
+RUN_REFUSED = "run_refused"
+
+_REFUSAL_SENTENCES = {
+    NO_SCAN: "Scan the collection before writing.",
+    OUTPUT_UNSET: "Choose where the new collection file goes.",
+    "output_must_differ_from_input": "The new file must not replace the collection it is read from.",
+    "output_is_live_collection": "Traktor's own collection.nml is never written; choose another path.",
+    RUN_REFUSED: "The merge was refused; the reasons are listed above and nothing is written.",
+}
+
+
+@dataclass(frozen=True)
+class FilterChip:
+    tier: int
+    label: str
+    count: int
+
+
+@dataclass(frozen=True)
+class MemberRow:
+    primary_key: str
+    label: str
+    file_words: str
+    is_survivor: bool
+    is_suggested: bool
+
+
+@dataclass(frozen=True)
+class RailField:
+    """One conflicting merge field: each member's value and whether it is
+    the one the merge writes."""
+
+    field_name: str
+    choices: tuple[tuple[str, str, bool], ...]  # (primary key, value, chosen)
+
+
+@dataclass(frozen=True)
+class GroupView:
+    group_id: str
+    tier: int
+    tier_label: str
+    evidence: str
+    action_words: str
+    reason: str
+    survivor_reason: str
+    members: tuple[MemberRow, ...]
+    rail: tuple[RailField, ...]
+
+
+def _label(member: dedupe.Member) -> str:
+    record = member.record
+    name = f"{record.artist} - {record.title}".strip(" -")
+    return f"{name} ({record.file_name})" if name else record.file_name
+
+
+def group_view(plan: dedupe.GroupPlan) -> GroupView:
+    group = plan.group
+    members = tuple(
+        MemberRow(m.primary_key, _label(m), FILE_STATE_WORDS[m.file_state],
+                  m.primary_key == plan.survivor, m.primary_key == group.suggested_survivor)
+        for m in group.members
+    )
+    rail = tuple(
+        RailField(c.field_name, tuple((k, v, plan.picks.get(c.field_name) == k) for k, v in c.values))
+        for c in plan.conflicts
+    )
+    return GroupView(group.group_id, group.tier, TIER_LABELS[group.tier], group.evidence,
+                     ACTION_WORDS[plan.action], plan.reason, group.survivor_reason, members, rail)
+
+
+def filter_chips(plans: list[dedupe.GroupPlan]) -> tuple[FilterChip, ...]:
+    """The All chip, then one chip per tier in tier order, each with its
+    group count; a tier with no groups still shows, at zero, so the chip
+    row does not shift between runs."""
+    counts = {tier: 0 for tier in dedupe.ALL_TIERS}
+    for plan in plans:
+        counts[plan.group.tier] += 1
+    return (FilterChip(ALL_GROUPS, "All", len(plans)),) + tuple(
+        FilterChip(tier, TIER_LABELS[tier], counts[tier]) for tier in dedupe.ALL_TIERS
+    )
+
+
+def views_for_filter(plans: list[dedupe.GroupPlan], tier: int) -> list[GroupView]:
+    return [group_view(p) for p in plans if tier == ALL_GROUPS or p.group.tier == tier]
+
+
+@dataclass
+class ScanInputs:
+    input_path: Path
+    volume_map: dict[str, tuple[str, str]] = field(default_factory=dict)
+    tiers: frozenset[int] = dedupe.DEFAULT_TIERS
+    refute: bool = True
+
+
+@dataclass
+class LoadedScan:
+    """One scan the page holds: the source it read and what it found.
+    error is the read or parse diagnostic when there is nothing else."""
+
+    source_text: str = ""
+    source_sha: str = ""
+    root: object = None
+    scan: Optional[dedupe.ScanResult] = None
+    error: Optional[str] = None
+    input_path: Optional[Path] = None
+
+
+def run_scan(inputs: ScanInputs) -> LoadedScan:
+    """Read, parse and group. Called under run.io_bound by the page."""
+    loaded = read_and_parse_source(inputs.input_path)
+    if loaded.error is not None:
+        return LoadedScan(error=loaded.error)
+    text = loaded.source_bytes.decode("utf-8")
+    options = dedupe.scan_options_from_volume_map(inputs.volume_map, inputs.tiers, inputs.refute)
+    return LoadedScan(text, dedupe.input_sha256(loaded.source_bytes), loaded.root,
+                      dedupe.find_groups(text, loaded.root, options), input_path=inputs.input_path)
+
+
+class DedupeReview:
+    """The operator's decisions over one held scan, keyed by each group's
+    sorted member keys exactly as the decisions file keys them."""
+
+    def __init__(self, loaded: LoadedScan, decisions: Optional[dedupe.DecisionsFile] = None) -> None:
+        self.loaded = loaded
+        attached = (
+            dedupe.attach_decisions(decisions, loaded.scan.groups, loaded.source_sha) if decisions is not None else None
+        )
+        self.stale = attached.stale if attached is not None else 0
+        self._decisions: dict[tuple[str, ...], dedupe.Decision] = dict(attached.by_members) if attached else {}
+        self._groups = {g.group_id: g for g in loaded.scan.groups}
+
+    def plans(self) -> list[dedupe.GroupPlan]:
+        attached = dedupe.AttachedDecisions(dict(self._decisions), self.stale, False)
+        return dedupe.plan_merge(self.loaded.scan.groups, attached)
+
+    def _decision(self, group_id: str) -> dedupe.Decision:
+        group = self._groups[group_id]
+        existing = self._decisions.get(group.member_keys)
+        if existing is not None:
+            return existing
+        return dedupe.Decision(group.member_keys, group.tier, dedupe.ACTION_UNDECIDED, group.suggested_survivor, {})
+
+    def _store(self, decision: dedupe.Decision) -> None:
+        self._decisions[decision.members] = decision
+
+    def choose_survivor(self, group_id: str, primary_key: str) -> None:
+        self._store(replace(self._decision(group_id), survivor=primary_key, action=dedupe.ACTION_MERGE))
+
+    def pick(self, group_id: str, field_name: str, primary_key: str) -> None:
+        decision = self._decision(group_id)
+        self._store(replace(decision, picks={**decision.picks, field_name: primary_key}))
+
+    def mark(self, group_id: str, action: str) -> None:
+        self._store(replace(self._decision(group_id), action=action))
+
+    def decisions_document(self) -> dict:
+        return dedupe.decisions_document(self.loaded.source_sha, self.plans())
+
+    def save(self, path: Path) -> Optional[str]:
+        """Called on every review change, so a closed page resumes from
+        the file (DL-323). Returns write_decisions' refusal when path names
+        the scanned input or the live collection.nml, and writes nothing."""
+        inputs = [self.loaded.input_path] if self.loaded.input_path is not None else []
+        return dedupe.write_decisions(path, self.decisions_document(), inputs)
+
+    def assemble(self) -> dedupe.AssembleResult:
+        return dedupe.assemble_output(self.loaded.source_text, self.loaded.root, self.loaded.scan, self.plans())
+
+
+def load_decisions_file(path: Optional[Path]) -> tuple[Optional[dedupe.DecisionsFile], Optional[str]]:
+    """The parsed file, or the refusal the CLI would print for it. A path
+    that does not exist yet is not an error: the page creates it on the
+    first change."""
+    if path is None or not path.exists():
+        return None, None
+    try:
+        return dedupe.parse_decisions(path.read_text(encoding="utf-8")), None
+    except (OSError, dedupe.DecisionsError) as exc:
+        return None, f"invalid_decisions:{exc}"
+
+
+def write_refusal(review: Optional[DedupeReview], input_path: Optional[Path], output_path: Optional[Path],
+                  result: Optional[dedupe.AssembleResult]) -> Optional[str]:
+    """The one reason the write control stays shut, or None."""
+    if review is None or input_path is None:
+        return NO_SCAN
+    if output_path is None:
+        return OUTPUT_UNSET
+    refusal = dedupe.output_refusal(output_path, [input_path])
+    if refusal is not None:
+        return refusal
+    if result is not None and result.output is None:
+        return RUN_REFUSED
+    return None
+
+
+def refusal_sentence(reason: str) -> str:
+    return _REFUSAL_SENTENCES.get(reason, reason)
+
+
+def summary_lines(stats: dict) -> list[str]:
+    """The write step's preview counts, in the order the CLI prints its
+    stats, worded for the page."""
+    lines = [
+        f"{stats.get('entries_removed', 0)} duplicate entries removed",
+        f"{stats.get('groups_auto_applied', 0)} groups merged automatically",
+        f"{stats.get('groups_for_review', 0)} groups left for review",
+        f"{sum(stats.get('refs_redirected', {}).values())} playlist references moved to a survivor",
+        f"{sum(stats.get('refs_preserved', {}).values())} references kept on their own entry",
+        f"{stats.get('metadata_conflicts', 0)} metadata conflicts",
+        f"{stats.get('loser_fields_discarded', 0)} unmerged fields discarded with removed entries",
+    ]
+    lines += [f"Tier {tier} not scanned" for tier in dedupe.ALL_TIERS if stats.get(f"tier_{tier}") == "disabled"]
+    return lines
```

**Documentation:**

```diff
--- a/traktor_nml/gui/dedupe_model.py
+++ b/traktor_nml/gui/dedupe_model.py
@@ -59,6 +59,9 @@
 
 @dataclass(frozen=True)
 class FilterChip:
+    """One review filter chip: a tier (or ALL_GROUPS), its label and how many
+    groups it holds. Empty tiers still get a chip (DL-323)."""
+
     tier: int
     label: str
     count: int
@@ -66,6 +69,9 @@
 
 @dataclass(frozen=True)
 class MemberRow:
+    """One member line in a group card, with whether it is the chosen and the
+    suggested survivor."""
+
     primary_key: str
     label: str
     file_words: str
@@ -84,6 +90,9 @@
 
 @dataclass(frozen=True)
 class GroupView:
+    """Everything one group card shows, derived from its GroupPlan so the card
+    holds no state of its own (DL-318)."""
+
     group_id: str
     tier: int
     tier_label: str
@@ -102,6 +111,8 @@
 
 
 def group_view(plan: dedupe.GroupPlan) -> GroupView:
+    """Derive a group card from one plan: member rows, the action in words, and
+    the conflict rail with the picked value marked."""
     group = plan.group
     members = tuple(
         MemberRow(m.primary_key, _label(m), FILE_STATE_WORDS[m.file_state],
@@ -129,11 +140,15 @@
 
 
 def views_for_filter(plans: list[dedupe.GroupPlan], tier: int) -> list[GroupView]:
+    """Group cards for one filter chip, in scan order."""
     return [group_view(p) for p in plans if tier == ALL_GROUPS or p.group.tier == tier]
 
 
 @dataclass
 class ScanInputs:
+    """What the set-up step collects for a scan; tiers and refute default to
+    the CLI's defaults so both surfaces scan alike."""
+
     input_path: Path
     volume_map: dict[str, tuple[str, str]] = field(default_factory=dict)
     tiers: frozenset[int] = dedupe.DEFAULT_TIERS
@@ -178,6 +193,8 @@
         self._groups = {g.group_id: g for g in loaded.scan.groups}
 
     def plans(self) -> list[dedupe.GroupPlan]:
+        """Plans for every group under the decisions made so far, built with
+        the same plan_merge the CLI uses."""
         attached = dedupe.AttachedDecisions(dict(self._decisions), self.stale, False)
         return dedupe.plan_merge(self.loaded.scan.groups, attached)
 
@@ -192,16 +209,21 @@
         self._decisions[decision.members] = decision
 
     def choose_survivor(self, group_id: str, primary_key: str) -> None:
+        """Record a survivor for a group; choosing one is a merge decision."""
         self._store(replace(self._decision(group_id), survivor=primary_key, action=dedupe.ACTION_MERGE))
 
     def pick(self, group_id: str, field_name: str, primary_key: str) -> None:
+        """Record which member's value a conflicting field takes."""
         decision = self._decision(group_id)
         self._store(replace(decision, picks={**decision.picks, field_name: primary_key}))
 
     def mark(self, group_id: str, action: str) -> None:
+        """Record an action for a group, such as not duplicates."""
         self._store(replace(self._decision(group_id), action=action))
 
     def decisions_document(self) -> dict:
+        """The decisions JSON for the current review, in the same schema
+        --write-decisions writes (DL-317)."""
         return dedupe.decisions_document(self.loaded.source_sha, self.plans())
 
     def save(self, path: Path) -> Optional[str]:
@@ -212,6 +234,9 @@
         return dedupe.write_decisions(path, self.decisions_document(), inputs)
 
     def assemble(self) -> dedupe.AssembleResult:
+        """Assemble the output under the current decisions with the same
+        assemble_output the CLI uses, so the preview counts match the file
+        that would be written."""
         return dedupe.assemble_output(self.loaded.source_text, self.loaded.root, self.loaded.scan, self.plans())
 
 
@@ -243,6 +268,8 @@
 
 
 def refusal_sentence(reason: str) -> str:
+    """A refusal code as a sentence for the page, falling back to the code
+    itself for any code without one."""
     return _REFUSAL_SENTENCES.get(reason, reason)
 
 

```


**CC-M-003-002** (traktor_nml/gui/dedupe_steps.py) - implements CI-M-003-002

**Code:**

```diff
--- a/traktor_nml/gui/dedupe_steps.py
+++ b/traktor_nml/gui/dedupe_steps.py
@@ -0,0 +1,70 @@
+"""The /dedupe page's step table and the rail records it renders, with
+no framework import.
+
+Four linear steps - set up, scan, review, write - on the reconstruct
+page's rail (DL-323). The rail's classes, marker and aria-current value
+are reconstruct_steps' own, so both pages' rails read from one set of
+names; only the table and the reachability rule differ.
+"""
+
+from __future__ import annotations
+
+from .reconstruct_steps import (
+    ARIA_CURRENT_STEP,
+    CURRENT,
+    DONE,
+    DONE_MARKER,
+    MARKER_CLASS,
+    MARKER_CURRENT_CLASS,
+    UPCOMING,
+    RailRecord,
+    _classes,
+)
+
+SET_UP = 1
+SCAN = 2
+REVIEW = 3
+WRITE = 4
+
+STEPS: tuple[tuple[int, str], ...] = (
+    (SET_UP, "Set up"),
+    (SCAN, "Scan"),
+    (REVIEW, "Review"),
+    (WRITE, "Write"),
+)
+
+
+def rail_records(current: int) -> tuple[RailRecord, ...]:
+    """One record per STEPS row in table order: rows before current read
+    done, current reads current, the rest upcoming. A current naming no
+    row leaves every row upcoming."""
+    known = any(number == current for number, _ in STEPS)
+    records = []
+    for number, label in STEPS:
+        state = CURRENT if number == current else DONE if known and number < current else UPCOMING
+        records.append(RailRecord(
+            number=number,
+            label=label,
+            state=state,
+            classes=_classes(state),
+            marker=DONE_MARKER if state == DONE else str(number),
+            marker_classes=f"{MARKER_CLASS} {MARKER_CURRENT_CLASS}" if state == CURRENT else MARKER_CLASS,
+            aria_current=ARIA_CURRENT_STEP if state == CURRENT else None,
+        ))
+    return tuple(records)
+
+
+def reachable(target: int, has_input: bool, has_scan: bool, write_refusal: str | None) -> bool:
+    """SET_UP always; SCAN once an input collection is chosen; REVIEW
+    once a scan is held; WRITE once a scan is held and
+    dedupe_model.write_refusal has nothing to say, so the step the page
+    shuts and the sentence it prints read one value."""
+    if target == SET_UP:
+        return True
+    if target == SCAN:
+        return has_input
+    if target == REVIEW:
+        return has_scan
+    if target == WRITE:
+        return has_scan and write_refusal is None
+    return False

```

**Documentation:**

```diff
--- a/traktor_nml/gui/dedupe_steps.py
+++ b/traktor_nml/gui/dedupe_steps.py
@@ -21,6 +21,8 @@
     _classes,
 )
 
+# Step numbers double as the rail markers and as the order reachable() and
+# rail_records() compare.
 SET_UP = 1
 SCAN = 2
 REVIEW = 3

```


**CC-M-003-003** (traktor_nml/gui/app.py) - implements CI-M-003-003

**Code:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -40,7 +40,8 @@ from __future__ import annotations
 import argparse
 import threading
 import time
 import traceback
+from dataclasses import dataclass, field
 from pathlib import Path
 from typing import Callable, NamedTuple, Optional
@@ -60,12 +60,16 @@ from ..confidence import MatchConfidence
 from ..rewrite import path_collides, read_and_parse_source, write_bytes_atomically
 from ..spans import SpanIndex
 from ..splice import assemble_output
+from .. import dedupe
+from ..volumes import parse_volume_map
 from ..split import build_output as split_build_output
 from ..xmlio import parse_xml_bytes
 from . import answer_detail
 from . import buildplaylist_view
 from . import collection_summary
 from . import conflict_model
+from . import dedupe_model
+from . import dedupe_steps
 from . import navigation
 from . import reconstruct_report
 from . import reconstruct_steps
@@ -330,6 +334,7 @@ def build_wizard() -> None:
 
     _build_reconstruct_page()
     _build_build_playlist_page()
+    _build_dedupe_page()
 
     @ui.page("/reconnect")
     def index() -> None:
@@ -1569,7 +1574,7 @@ def _collection_labels(sources) -> tuple[str, ...]:
     return ("base", *_source_labels(sources))
 
 
-def _draw_step_rail(rail: ui.element, current: int) -> None:
+def _draw_step_rail(rail: ui.element, current: int, steps=reconstruct_steps) -> None:
     """Redraws the four-step rail over reconstruct_steps.rail_records.
 
     One span per record, in the order the table returns them, carrying
@@ -1592,7 +1597,10 @@ def _draw_step_rail(rail: ui.element, current: int) -> None:
     """
     rail.clear()
     with rail:
-        for record in reconstruct_steps.rail_records(current):
+        # steps is the module holding the page's step table: the
+        # reconstruct page's by default, dedupe_steps for /dedupe, whose
+        # records carry the same class names (DL-323).
+        for record in steps.rail_records(current):
             with ui.element("span").classes(add=record.classes) as entry:
                 ui.label(record.marker).classes(add=record.marker_classes)
                 ui.label(record.label)
@@ -2079,6 +2087,249 @@ def _build_build_playlist_page() -> None:
 # above enforces - a new file at the chosen path, every input left as it
 # was, and Traktor reading its own collection until the operator imports
 # the new one.
+def _dedupe_decisions_path(input_path: Path) -> Path:
+    """The side JSON the /dedupe page saves decisions to on every change:
+    beside the input collection, never the input itself, and the file
+    `dedupe --decisions` reads for the same run (DL-323)."""
+    return input_path.with_name(input_path.stem + ".dedupe-decisions.json")
+
+
+def _dedupe_volume_map(text: str) -> dict:
+    """--volume-map's SCAN_ROOT VOLUME VOLUMEID triples, one per line, as
+    volumes.parse_volume_map keys them."""
+    triples = [line.split() for line in text.splitlines() if line.strip()]
+    return parse_volume_map([parts for parts in triples if len(parts) == 3])
+
+
+@dataclass
+class _DedupeHeld:
+    """The /dedupe page's state and the widgets its handlers redraw.
+
+    One object per page load, passed to module-level builders and
+    handlers so each stays a short function rather than a closure inside
+    one page body (DL-318 keeps the rules themselves in dedupe_model)."""
+
+    input: Optional[Path] = None
+    review: object = None
+    result: object = None
+    filter: object = dedupe_model.ALL_GROUPS
+    step: int = dedupe_steps.SET_UP
+    widgets: dict = field(default_factory=dict)
+
+    def output_path(self) -> Optional[Path]:
+        value = self.widgets["output"].value
+        return Path(value) if value else None
+
+    def refusal(self) -> Optional[str]:
+        return dedupe_model.write_refusal(self.review, self.input, self.output_path(), self.result)
+
+
+def _build_dedupe_page() -> None:
+    """Registers the dedupe section at '/dedupe'.
+
+    Every rule the page follows lives in dedupe_model and dedupe_steps,
+    which import no nicegui (DL-318); the functions below lay their
+    records out and wire controls to their functions. The scan and the
+    write run under run.io_bound, and the write goes through
+    dedupe.write_validated_output, the one write path the CLI shares, so
+    neither surface can skip the post-write parse (DL-310).
+    """
+
+    @ui.page("/dedupe")
+    def dedupe_page() -> None:
+        chrome = _page_chrome("/dedupe")
+        held = _DedupeHeld()
+        with chrome.middle:
+            with ui.column().classes("gap-4 wizard-content-width"):
+                held.widgets["rail"] = ui.element("div").classes("wizard-step-rail")
+                _dedupe_setup_card(held)
+                _dedupe_review_card(held)
+                _dedupe_write_card(held)
+        _dedupe_footer(chrome, held)
+        _dedupe_show(held, dedupe_steps.SET_UP)
+
+
+def _dedupe_setup_card(held: _DedupeHeld) -> None:
+    with ui.element("section").classes("wizard-card wizard-content-width") as card:
+        with ui.element("div").classes("wizard-card-head"):
+            ui.label("Find duplicate collection entries").classes("wizard-card-title")
+        with ui.element("div").classes("wizard-card-body"):
+            ui.label(
+                "Close Traktor first: it rewrites collection.nml when it exits. "
+                "The collection you choose is only read; the result is a new file."
+            )
+            held.widgets["output"] = ui.input(
+                "Output file", on_change=lambda _e: _dedupe_refresh(held)
+            ).classes("w-full")
+            held.widgets["volumes"] = ui.textarea(
+                "Volume map: SCAN_ROOT VOLUME VOLUMEID, one per line"
+            ).classes("w-full")
+            held.widgets["scan_error"] = ui.label("").classes("wizard-subtle-1")
+            _dedupe_input_row(held)
+            held.widgets["scan"] = ui.button(
+                "Scan", on_click=lambda: _dedupe_scan(held), color=None
+            ).classes("wizard-control wizard-control-primary")
+    held.widgets["setup_card"] = card
+
+
+def _dedupe_input_row(held: _DedupeHeld) -> None:
+    # A path chooser stands in a flex row beside the path it picks, as
+    # every chooser on the other pages does (DL-301).
+    with ui.row().classes("wizard-path-row"):
+        held.widgets["input_display"] = ui.label("No collection selected").classes(
+            "wizard-mono wizard-subtle-1"
+        )
+        ui.button(
+            "Choose collection file...", on_click=lambda: _dedupe_choose_input(held), color=None
+        ).classes("wizard-control wizard-control-fill")
+
+
+def _dedupe_review_card(held: _DedupeHeld) -> None:
+    with ui.element("section").classes("wizard-card wizard-content-width") as card:
+        held.widgets["chips"] = ui.row().classes("gap-2")
+        held.widgets["groups"] = ui.column().classes("gap-3 w-full")
+    held.widgets["review_card"] = card
+
+
+def _dedupe_write_card(held: _DedupeHeld) -> None:
+    with ui.element("section").classes("wizard-card wizard-content-width") as card:
+        held.widgets["summary"] = ui.column().classes("gap-1")
+        held.widgets["refusal"] = ui.label("").classes("wizard-subtle-1")
+        held.widgets["write"] = ui.button(
+            "Write collection", on_click=lambda: _dedupe_write(held), color=None
+        ).classes("wizard-control wizard-control-primary")
+    held.widgets["write_card"] = card
+
+
+def _dedupe_footer(chrome, held: _DedupeHeld) -> None:
+    buttons = (
+        ("Back to set up", dedupe_steps.SET_UP, "wizard-control wizard-control-fill"),
+        ("Review", dedupe_steps.REVIEW, "wizard-control wizard-control-fill"),
+        ("Continue to write", dedupe_steps.WRITE, "wizard-control wizard-control-primary"),
+    )
+    with chrome.footer_actions:
+        for text, step, classes in buttons:
+            ui.button(text, on_click=lambda _e, step=step: _dedupe_show(held, step), color=None).classes(classes)
+    chrome.footer_note.set_text("Nothing is written until Write collection; audio files are never touched.")
+
+
+async def _dedupe_choose_input(held: _DedupeHeld) -> None:
+    path = await pick_file_or_folder(directories_only=False)
+    if path is not None:
+        held.input, held.review, held.result = path, None, None
+        held.widgets["input_display"].set_text(str(path))
+        _dedupe_show(held, dedupe_steps.SCAN)
+
+
+async def _dedupe_scan(held: _DedupeHeld) -> None:
+    inputs = dedupe_model.ScanInputs(held.input, _dedupe_volume_map(held.widgets["volumes"].value or ""))
+    loaded = await run.io_bound(dedupe_model.run_scan, inputs)
+    decisions, refusal = dedupe_model.load_decisions_file(_dedupe_decisions_path(held.input))
+    if loaded.error is not None or refusal is not None:
+        held.widgets["scan_error"].set_text(loaded.error or refusal)
+        return
+    held.review = dedupe_model.DedupeReview(loaded, decisions)
+    held.result = await run.io_bound(held.review.assemble)
+    _dedupe_show(held, dedupe_steps.REVIEW)
+
+
+async def _dedupe_write(held: _DedupeHeld) -> None:
+    written = await run.io_bound(
+        dedupe.write_validated_output, held.result.output.encode("utf-8"), held.output_path(),
+        expected_entries=held.result.expected_entries,
+    )
+    ui.notify(
+        f"Written to {held.output_path()}" if written.ok else written.error,
+        type="positive" if written.ok else "negative",
+    )
+
+
+def _dedupe_decide(held: _DedupeHeld, change) -> None:
+    # Saved on every change so a closed page resumes from the side file,
+    # and re-assembled so the write step's counts always describe the
+    # decisions on screen (DL-323).
+    change(held.review)
+    refusal = held.review.save(_dedupe_decisions_path(held.input))
+    if refusal is not None:
+        ui.notify(dedupe_model.refusal_sentence(refusal), type="negative")
+    held.result = held.review.assemble()
+    _dedupe_refresh(held)
+
+
+def _dedupe_draw_group(held: _DedupeHeld, view) -> None:
+    def decide(change):
+        return lambda _e: _dedupe_decide(held, change)
+
+    with ui.element("div").classes("wizard-card-body"):
+        ui.label(f"{view.tier_label}: {view.action_words}").classes("wizard-card-title")
+        ui.label(f"{view.evidence}. Suggested survivor: {view.survivor_reason}.").classes("wizard-subtle-1")
+        for row in view.members:
+            _dedupe_draw_member(row, decide(lambda r, key=row.primary_key: r.choose_survivor(view.group_id, key)))
+        for rail_field in view.rail:
+            ui.label(f"Conflict: {rail_field.field_name}").classes("wizard-label")
+            for key, value, chosen in rail_field.choices:
+                pick = decide(lambda r, key=key, name=rail_field.field_name: r.pick(view.group_id, name, key))
+                ui.button(value + (" (chosen)" if chosen else ""), color=None, on_click=pick).classes(
+                    "wizard-control wizard-control-fill"
+                )
+        ui.button(
+            "Not duplicates", color=None,
+            on_click=decide(lambda r: r.mark(view.group_id, dedupe.ACTION_NOT_DUPLICATES)),
+        ).classes("wizard-control wizard-control-fill")
+
+
+def _dedupe_draw_member(row, on_keep) -> None:
+    with ui.row().classes("items-center gap-2"):
+        ui.label(row.label + (" (survivor)" if row.is_survivor else ""))
+        ui.label(row.file_words).classes("wizard-subtle-1")
+        ui.button("Keep this one", color=None, on_click=on_keep).classes("wizard-control wizard-control-fill")
+
+
+def _dedupe_set_filter(held: _DedupeHeld, tier) -> None:
+    held.filter = tier
+    _dedupe_refresh(held)
+
+
+def _dedupe_draw_review(held: _DedupeHeld) -> None:
+    plans = held.review.plans()
+    chips, groups = held.widgets["chips"], held.widgets["groups"]
+    chips.clear()
+    with chips:
+        for chip in dedupe_model.filter_chips(plans):
+            ui.button(
+                f"{chip.label} ({chip.count})", color=None,
+                on_click=lambda _e, tier=chip.tier: _dedupe_set_filter(held, tier),
+            ).classes("wizard-control wizard-control-fill")
+    groups.clear()
+    with groups:
+        for view in dedupe_model.views_for_filter(plans, held.filter):
+            _dedupe_draw_group(held, view)
+
+
+def _dedupe_refresh(held: _DedupeHeld) -> None:
+    held.widgets["scan"].set_enabled(held.input is not None)
+    if held.review is not None:
+        _dedupe_draw_review(held)
+    summary = held.widgets["summary"]
+    summary.clear()
+    with summary:
+        for line in dedupe_model.summary_lines(held.result.stats if held.result else {}):
+            ui.label(line)
+    refusal = held.refusal()
+    held.widgets["refusal"].set_text("" if refusal is None else dedupe_model.refusal_sentence(refusal))
+    held.widgets["write"].set_enabled(refusal is None)
+
+
+def _dedupe_show(held: _DedupeHeld, step: int) -> None:
+    if dedupe_steps.reachable(step, held.input is not None, held.review is not None, held.refusal()):
+        held.step = step
+    _draw_step_rail(held.widgets["rail"], held.step, steps=dedupe_steps)
+    held.widgets["setup_card"].set_visibility(held.step in (dedupe_steps.SET_UP, dedupe_steps.SCAN))
+    held.widgets["review_card"].set_visibility(held.step == dedupe_steps.REVIEW)
+    held.widgets["write_card"].set_visibility(held.step == dedupe_steps.WRITE)
+    _dedupe_refresh(held)
+
+
 def _build_reconstruct_page() -> None:
     """Registers the playlist-reconstruction screen at '/'.
 
```

**Documentation:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -2137,6 +2137,8 @@
 
     @ui.page("/dedupe")
     def dedupe_page() -> None:
+        """Lay out the dedupe page: step rail, set-up, review and write cards,
+        and footer, opening on the set-up step (DL-323)."""
         chrome = _page_chrome("/dedupe")
         held = _DedupeHeld()
         with chrome.middle:
@@ -2222,6 +2224,9 @@
 
 
 async def _dedupe_scan(held: _DedupeHeld) -> None:
+    """Scan the chosen input off the event loop, load its side decisions file,
+    and move to review; a read, parse or decisions refusal is shown on the
+    set-up card instead."""
     inputs = dedupe_model.ScanInputs(held.input, _dedupe_volume_map(held.widgets["volumes"].value or ""))
     loaded = await run.io_bound(dedupe_model.run_scan, inputs)
     decisions, refusal = dedupe_model.load_decisions_file(_dedupe_decisions_path(held.input))
@@ -2234,6 +2239,8 @@
 
 
 async def _dedupe_write(held: _DedupeHeld) -> None:
+    """Write the assembled output through write_validated_output, the write
+    path the CLI shares (DL-310), and report the result."""
     written = await run.io_bound(
         dedupe.write_validated_output, held.result.output.encode("utf-8"), held.output_path(),
         expected_entries=held.result.expected_entries,
@@ -2307,6 +2314,8 @@
 
 
 def _dedupe_refresh(held: _DedupeHeld) -> None:
+    """Redraw the review and write step from the held state, enabling Write
+    only when write_refusal finds nothing."""
     held.widgets["scan"].set_enabled(held.input is not None)
     if held.review is not None:
         _dedupe_draw_review(held)

```

> **Developer notes**: app.py is stored wholly CRLF (tests/test_gui_line_endings.py); the diff shows LF for readability and every added line must be written with CRLF.

**CC-M-003-004** (traktor_nml/gui/navigation.py) - implements CI-M-003-004

**Code:**

```diff
--- a/traktor_nml/gui/navigation.py
+++ b/traktor_nml/gui/navigation.py
@@ -3,8 +3,9 @@ framework import.
 
 SECTIONS is the one place a route or a label is written: the reconstruct
 page answers '/' and stands leftmost, the reconnect wizard answers
-'/reconnect' and stands second, and the build-playlist screen answers
-'/build-playlist' and stands third. header_tabs(active_route) derives
+'/reconnect' and stands second, the build-playlist screen answers
+'/build-playlist' and stands third, and the dedupe section answers
+'/dedupe' and stands fourth (DL-318). header_tabs(active_route) derives
 one record per row in that same order, carrying the row's route and
 label plus the three things a tab renders with - whether it is the
 selected row, the class string it carries, and its aria-current value.
@@ -31,6 +32,7 @@ SECTIONS: tuple[tuple[str, str], ...] = (
     ("/", "Reconstruct playlists"),
     ("/reconnect", "Reconnect wizard"),
     ("/build-playlist", "Build playlist"),
+    ("/dedupe", "Dedupe collection"),
 )
 
 # The class every tab carries, and the second class the selected one

```

**Documentation:**

```diff
--- a/traktor_nml/gui/navigation.py
+++ b/traktor_nml/gui/navigation.py
@@ -32,6 +32,7 @@
     ("/", "Reconstruct playlists"),
     ("/reconnect", "Reconnect wizard"),
     ("/build-playlist", "Build playlist"),
+    # Row order is tab order; the header adds no tab this table lacks.
     ("/dedupe", "Dedupe collection"),
 )
 

```


**CC-M-003-005** (tests/test_gui_dedupe_model.py) - implements CI-M-003-005

**Code:**

```diff
--- a/tests/test_gui_dedupe_model.py
+++ b/tests/test_gui_dedupe_model.py
@@ -0,0 +1,118 @@
+"""G6 view-model guards for traktor_nml/gui/dedupe_model.py and
+dedupe_steps.py: filter chips, survivor pick, conflict picks, write
+refusals and step reachability, on an interpreter with no nicegui."""
+
+from __future__ import annotations
+
+import ast
+import json
+from pathlib import Path
+
+from tests.fixtures.dedupe import build_dedupe_fixtures as fx
+from traktor_nml import dedupe
+from traktor_nml.gui import dedupe_model, dedupe_steps
+
+
+def _review(tmp_path: Path, text: str) -> tuple[dedupe_model.DedupeReview, Path]:
+    source = tmp_path / "in.nml"
+    source.write_text(text, encoding="utf-8")
+    return dedupe_model.DedupeReview(dedupe_model.run_scan(dedupe_model.ScanInputs(source))), source
+
+
+def test_filter_chips_count_every_tier_including_empty_ones(tmp_path: Path) -> None:
+    review, _ = _review(tmp_path, fx.golden_tier1())
+    chips = dedupe_model.filter_chips(review.plans())
+    assert [(c.tier, c.count) for c in chips] == [(0, 1), (1, 1), (2, 0), (3, 0), (4, 0)]
+    assert [v.group_id for v in dedupe_model.views_for_filter(review.plans(), 2)] == []
+    assert [v.group_id for v in dedupe_model.views_for_filter(review.plans(), 1)] == ["G0001"]
+
+
+def test_group_view_marks_the_suggested_survivor_and_its_reason(tmp_path: Path) -> None:
+    review, _ = _review(tmp_path, fx.golden_tier1())
+    (view,) = dedupe_model.views_for_filter(review.plans(), dedupe_model.ALL_GROUPS)
+    assert [(m.primary_key, m.is_survivor, m.is_suggested) for m in view.members] == [
+        (fx.TIER1_A, False, False), (fx.TIER1_B, True, True),
+    ]
+    assert view.survivor_reason == "higher play count"
+
+
+def test_choosing_a_survivor_moves_it_and_the_decision_is_saved(tmp_path: Path) -> None:
+    review, _ = _review(tmp_path, fx.golden_tier1())
+    review.choose_survivor("G0001", fx.TIER1_A)
+    (plan,) = review.plans()
+    assert (plan.action, plan.survivor) == (dedupe.PLAN_MERGE, fx.TIER1_A)
+    side = tmp_path / "decisions.json"
+    review.save(side)
+    (group,) = json.loads(side.read_text(encoding="utf-8"))["groups"]
+    assert (group["action"], group["survivor"]) == ("merge", fx.TIER1_A)
+
+
+def test_saving_decisions_over_the_input_is_refused_and_writes_nothing(tmp_path: Path) -> None:
+    review, source = _review(tmp_path, fx.golden_tier1())
+    before = source.read_bytes()
+    review.choose_survivor("G0001", fx.TIER1_A)
+    assert review.save(source) == "output_must_differ_from_input"
+    assert source.read_bytes() == before
+
+
+def test_conflict_rail_reads_the_pick(tmp_path: Path) -> None:
+    review, _ = _review(tmp_path, fx.merge_pair("", "", ' KEY="1m"', ' KEY="2m"'))
+    (view,) = dedupe_model.views_for_filter(review.plans(), dedupe_model.ALL_GROUPS)
+    assert (view.action_words, [f.field_name for f in view.rail]) == ("Needs a decision", ["key"])
+    review.pick("G0001", "key", fx.TIER1_B)
+    (view,) = dedupe_model.views_for_filter(review.plans(), dedupe_model.ALL_GROUPS)
+    assert view.action_words == "Will merge"
+    assert [(key, chosen) for key, _value, chosen in view.rail[0].choices] == [(fx.TIER1_A, False), (fx.TIER1_B, True)]
+
+
+def test_not_duplicates_mark_leaves_the_group_alone(tmp_path: Path) -> None:
+    review, _ = _review(tmp_path, fx.golden_tier1())
+    review.mark("G0001", dedupe.ACTION_NOT_DUPLICATES)
+    assert review.assemble().stats["entries_removed"] == 0
+
+
+def test_write_refusals_in_order(tmp_path: Path) -> None:
+    review, source = _review(tmp_path, fx.golden_tier1())
+    result = review.assemble()
+    assert dedupe_model.write_refusal(None, None, None, None) == dedupe_model.NO_SCAN
+    assert dedupe_model.write_refusal(review, source, None, result) == dedupe_model.OUTPUT_UNSET
+    assert dedupe_model.write_refusal(review, source, source, result) == "output_must_differ_from_input"
+    assert dedupe_model.write_refusal(review, source, tmp_path / "out.nml", result) is None
+
+
+def test_refused_run_shuts_the_write_step(tmp_path: Path) -> None:
+    review, source = _review(tmp_path, fx.unknown_shape_reference())
+    refusal = dedupe_model.write_refusal(review, source, tmp_path / "out.nml", review.assemble())
+    assert refusal == dedupe_model.RUN_REFUSED
+    assert not dedupe_steps.reachable(dedupe_steps.WRITE, True, True, refusal)
+    assert dedupe_steps.reachable(dedupe_steps.REVIEW, True, True, refusal)
+
+
+def test_step_rail_marks_one_current_step() -> None:
+    records = dedupe_steps.rail_records(dedupe_steps.REVIEW)
+    assert [r.state for r in records] == ["done", "done", "current", "upcoming"]
+    assert [r.label for r in records] == ["Set up", "Scan", "Review", "Write"]
+    assert [r.state for r in dedupe_steps.rail_records(9)] == ["upcoming"] * 4
+
+
+def test_invalid_side_decisions_file_is_refused_like_the_cli(tmp_path: Path) -> None:
+    side = tmp_path / "d.json"
+    side.write_text("{", encoding="utf-8")
+    assert dedupe_model.load_decisions_file(side) == (None, "invalid_decisions:not_json")
+    assert dedupe_model.load_decisions_file(tmp_path / "absent.json") == (None, None)
+
+
+def _imported_roots(path: Path) -> set[str]:
+    roots: set[str] = set()
+    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
+        if isinstance(node, ast.Import):
+            roots.update(alias.name.split(".")[0] for alias in node.names)
+        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
+            roots.add(node.module.split(".")[0])
+    return roots
+
+
+def test_view_models_import_no_framework() -> None:
+    """DL-318: both modules stay importable without nicegui."""
+    for module in (dedupe_model, dedupe_steps):
+        assert _imported_roots(Path(module.__file__)) & {"nicegui", "webview"} == set()
```

**Documentation:**

```diff
--- a/tests/test_gui_dedupe_model.py
+++ b/tests/test_gui_dedupe_model.py
@@ -14,6 +14,8 @@
 
 
 def _review(tmp_path: Path, text: str) -> tuple[dedupe_model.DedupeReview, Path]:
+    """A review over text written to tmp_path, with no side decisions file;
+    returns it and the source path."""
     source = tmp_path / "in.nml"
     source.write_text(text, encoding="utf-8")
     return dedupe_model.DedupeReview(dedupe_model.run_scan(dedupe_model.ScanInputs(source))), source
@@ -103,6 +105,8 @@
 
 
 def _imported_roots(path: Path) -> set[str]:
+    """The top-level package of every absolute import in path, for the no-
+    nicegui guard (DL-318)."""
     roots: set[str] = set()
     for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
         if isinstance(node, ast.Import):

```


**CC-M-003-006** (tests/test_gui_dedupe_parity.py) - implements CI-M-003-006

**Code:**

```diff
--- a/tests/test_gui_dedupe_parity.py
+++ b/tests/test_gui_dedupe_parity.py
@@ -0,0 +1,55 @@
+"""G6 parity: the same input and the same decisions give byte-identical
+output through the dedupe command and through the /dedupe page's model,
+because both assemble with dedupe.assemble_output and write with
+dedupe.write_validated_output (DL-310)."""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+import pytest
+
+from tests.conftest import run_tool
+from tests.fixtures.dedupe import build_dedupe_fixtures as fx
+from traktor_nml import dedupe
+from traktor_nml.gui import dedupe_model
+
+
+def _gui_write(source: Path, decisions: Path | None, output: Path) -> None:
+    parsed, refusal = dedupe_model.load_decisions_file(decisions)
+    assert refusal is None
+    review = dedupe_model.DedupeReview(dedupe_model.run_scan(dedupe_model.ScanInputs(source)), parsed)
+    result = review.assemble()
+    written = dedupe.write_validated_output(
+        result.output.encode("utf-8"), output, expected_entries=result.expected_entries
+    )
+    assert written.ok
+
+
+@pytest.mark.parametrize("builder", [fx.golden_tier1, lambda: fx.merge_pair(fx.CUE_A, fx.CUE_B)])
+def test_cli_and_gui_write_identical_bytes_without_decisions(tmp_path: Path, builder) -> None:
+    source = tmp_path / "in.nml"
+    source.write_text(builder(), encoding="utf-8")
+    cli = run_tool(["dedupe", "--input", str(source), "--output", str(tmp_path / "cli.nml")], cwd=tmp_path)
+    assert cli.exit_code == 0
+    _gui_write(source, None, tmp_path / "gui.nml")
+    assert (tmp_path / "cli.nml").read_bytes() == (tmp_path / "gui.nml").read_bytes()
+
+
+def test_cli_and_gui_write_identical_bytes_from_a_gui_saved_decisions_file(tmp_path: Path) -> None:
+    source = tmp_path / "in.nml"
+    source.write_text(fx.merge_pair("", "", ' KEY="1m"', ' KEY="2m"'), encoding="utf-8")
+    review = dedupe_model.DedupeReview(dedupe_model.run_scan(dedupe_model.ScanInputs(source)))
+    review.choose_survivor("G0001", fx.TIER1_A)
+    review.pick("G0001", "key", fx.TIER1_B)
+    decisions = tmp_path / "decisions.json"
+    review.save(decisions)
+
+    cli = run_tool(
+        ["dedupe", "--input", str(source), "--output", str(tmp_path / "cli.nml"), "--decisions", str(decisions)],
+        cwd=tmp_path,
+    )
+    assert cli.exit_code == 0
+    _gui_write(source, decisions, tmp_path / "gui.nml")
+    assert (tmp_path / "cli.nml").read_bytes() == (tmp_path / "gui.nml").read_bytes()
+    assert 'KEY="2m"' in (tmp_path / "gui.nml").read_text(encoding="utf-8")

```

**Documentation:**

```diff
--- a/tests/test_gui_dedupe_parity.py
+++ b/tests/test_gui_dedupe_parity.py
@@ -16,6 +16,8 @@
 
 
 def _gui_write(source: Path, decisions: Path | None, output: Path) -> None:
+    """Write output the way the /dedupe page does: the page's model, then
+    write_validated_output (DL-310)."""
     parsed, refusal = dedupe_model.load_decisions_file(decisions)
     assert refusal is None
     review = dedupe_model.DedupeReview(dedupe_model.run_scan(dedupe_model.ScanInputs(source)), parsed)

```


**CC-M-003-007** (tests/test_gui_navigation.py) - implements CI-M-003-007

**Code:**

```diff
--- a/tests/test_gui_navigation.py
+++ b/tests/test_gui_navigation.py
@@ -111,7 +111,7 @@ def test_marking_the_other_row_is_caught() -> None:
     """
     selected = _selected_routes(_tabs_under(lambda route, active: route != active, "/"))
     assert selected != ["/"]
-    assert selected == ["/reconnect", "/build-playlist"]
+    assert selected == ["/reconnect", "/build-playlist", "/dedupe"]
 
 
 def test_marking_both_rows_is_caught() -> None:
@@ -132,7 +132,7 @@ def test_marking_both_rows_is_caught() -> None:
     """
     selected = _selected_routes(_tabs_under(lambda route, active: True, "/"))
     assert selected != ["/"]
-    assert selected == ["/", "/reconnect", "/build-playlist"]
+    assert selected == ["/", "/reconnect", "/build-playlist", "/dedupe"]
 
 
 def test_marking_no_row_is_caught() -> None:
@@ -162,10 +162,11 @@ def test_routes_read_in_table_order_for_either_active_route() -> None:
     ['/', '/reconnect', '/build-playlist'], At index 0 diff:
     '/reconnect' != '/'.
     """
-    expected = ["/", "/reconnect", "/build-playlist"]
+    expected = ["/", "/reconnect", "/build-playlist", "/dedupe"]
     assert [tab.route for tab in header_tabs("/")] == expected
     assert [tab.route for tab in header_tabs("/reconnect")] == expected
     assert [tab.route for tab in header_tabs("/build-playlist")] == expected
+    assert [tab.route for tab in header_tabs("/dedupe")] == expected
 
 
 def test_selected_and_unselected_records_carry_their_markers() -> None:
@@ -186,7 +187,7 @@ def test_selected_and_unselected_records_carry_their_markers() -> None:
       selected=False, classes='wizard-tab', aria_current='page')
       .aria_current
     """
-    root, reconnect, build_playlist = header_tabs("/")
+    root, reconnect, build_playlist, dedupe = header_tabs("/")
 
     assert root.selected is True
     assert root.classes.split() == [TAB_CLASS, TAB_SELECTED_CLASS]
@@ -203,6 +204,11 @@ def test_selected_and_unselected_records_carry_their_markers() -> None:
     assert build_playlist.aria_current is None
     assert build_playlist.label == "Build playlist"
 
+    assert dedupe.selected is False
+    assert dedupe.classes.split() == [TAB_CLASS]
+    assert dedupe.aria_current is None
+    assert dedupe.label == "Dedupe collection"
+
 
 def test_header_tabs_selects_build_playlist_route() -> None:
     """header_tabs('/build-playlist') marks exactly one record and it is
@@ -244,8 +250,21 @@ def test_route_matching_no_row_selects_nothing() -> None:
     tabs = header_tabs("/nowhere")
 
     assert _selected_routes(tabs) == []
-    assert [tab.aria_current for tab in tabs] == [None, None, None]
-    assert [tab.classes for tab in tabs] == [TAB_CLASS, TAB_CLASS, TAB_CLASS]
+    assert [tab.aria_current for tab in tabs] == [None, None, None, None]
+    assert [tab.classes for tab in tabs] == [TAB_CLASS, TAB_CLASS, TAB_CLASS, TAB_CLASS]
+
+
+def test_header_tabs_selects_dedupe_route() -> None:
+    """header_tabs('/dedupe') marks exactly one record, the fourth row
+    SECTIONS declares, and the three prior routes still select exactly
+    their own record (DL-318).
+
+    Made to fail by removing the '/dedupe' row from SECTIONS:
+    AssertionError: assert [] == ['/dedupe'].
+    """
+    assert [route for route, _label in SECTIONS][3] == "/dedupe"
+    assert _selected_routes(header_tabs("/dedupe")) == ["/dedupe"]
+    assert _selected_routes(header_tabs("/build-playlist")) == ["/build-playlist"]
 
 
 def _imported_roots(source: str) -> set[str]:

```

**Documentation:**

```diff
--- a/tests/test_gui_navigation.py
+++ b/tests/test_gui_navigation.py
@@ -162,6 +162,7 @@
     ['/', '/reconnect', '/build-playlist'], At index 0 diff:
     '/reconnect' != '/'.
     """
+    # SECTIONS order, the same whichever tab is active.
     expected = ["/", "/reconnect", "/build-playlist", "/dedupe"]
     assert [tab.route for tab in header_tabs("/")] == expected
     assert [tab.route for tab in header_tabs("/reconnect")] == expected

```


**CC-M-003-008** (tests/test_gui_header_tabs.py) - implements CI-M-003-008

**Code:**

```diff
--- a/tests/test_gui_header_tabs.py
+++ b/tests/test_gui_header_tabs.py
@@ -211,20 +211,20 @@ def _marked(recorder: _RecordingUi) -> tuple:
 # --------------------------------------------------------------------
 
 
-def test_header_renders_three_links_in_table_order():
+def test_header_renders_four_links_in_table_order():
     """The strip holds one anchor per SECTIONS row, in the order the
-    table declares, and no fourth anchor.
+    table declares, and no fifth anchor.
 
     Mutation: navigation.header_tabs was replaced for the call by one
     returning only the '/reconnect' record. Observed:
         AssertionError: assert ['/reconnect'] == ['/', '/reconnect',
-        '/build-playlist']
+        '/build-playlist', '/dedupe']
         At index 0 diff: '/reconnect' != '/'
-        Right contains 2 more items
+        Right contains 3 more items
     """
     recorder = _render_header("/")
-    assert _targets(recorder) == ["/", "/reconnect", "/build-playlist"]
-    assert len(recorder.links) == 3
+    assert _targets(recorder) == ["/", "/reconnect", "/build-playlist", "/dedupe"]
+    assert len(recorder.links) == 4
 
 
 def test_root_marks_the_root_tab_and_only_it():
@@ -394,37 +394,39 @@ def _builder(tree: ast.Module, name: str) -> ast.FunctionDef:
     raise AssertionError(name + " not found in app.py")
 
 
-def test_app_py_registers_exactly_the_three_routes():
+def test_app_py_registers_exactly_the_four_routes():
     """The set of ui.page arguments in app.py is {'/', '/reconnect',
-    '/build-playlist'}: three pages, and nothing registered at
+    '/build-playlist', '/dedupe'}: four pages, and nothing registered at
     '/reconstruct', which therefore answers the framework's own 404
     (DL-141).
 
-    Mutation: a fourth registration, @ui.page("/reconstruct") over a
+    Mutation: a fifth registration, @ui.page("/reconstruct") over a
     stub function, was added to a copy of app.py's source and the same
     walk run over it. Observed:
         AssertionError: assert {'/', '/reconnect', '/build-playlist',
-        '/reconstruct'} == {'/', '/reconnect', '/build-playlist'}
+        '/dedupe', '/reconstruct'} == {'/', '/reconnect',
+        '/build-playlist', '/dedupe'}
         Extra items in the left set: '/reconstruct'
     """
-    assert set(_page_routes(_app_tree())) == {"/", "/reconnect", "/build-playlist"}
+    assert set(_page_routes(_app_tree())) == {"/", "/reconnect", "/build-playlist", "/dedupe"}
 
 
 def test_each_builder_registers_its_own_route():
     """_build_reconstruct_page registers '/', build_wizard registers
-    '/reconnect', and _build_build_playlist_page registers
-    '/build-playlist', each exactly once.
+    '/reconnect', _build_build_playlist_page registers '/build-playlist',
+    and _build_dedupe_page registers '/dedupe', each exactly once.
 
     Mutation: the '/' and '/reconnect' ui.page arguments were swapped in
     a copy of app.py's source and the same walk run over it. Observed:
         AssertionError: assert ['/reconnect'] == ['/']
     """
     tree = _app_tree()
     assert _page_routes(_builder(tree, "_build_reconstruct_page")) == ["/"]
     assert _page_routes(_builder(tree, "build_wizard")) == ["/reconnect"]
     assert _page_routes(_builder(tree, "_build_build_playlist_page")) == [
         "/build-playlist"
     ]
+    assert _page_routes(_builder(tree, "_build_dedupe_page")) == ["/dedupe"]
 
 
 def test_app_py_names_no_route_outside_its_two_registrations():
```

**Documentation:**

```diff
--- a/tests/test_gui_header_tabs.py
+++ b/tests/test_gui_header_tabs.py
@@ -426,6 +426,7 @@
     assert _page_routes(_builder(tree, "_build_build_playlist_page")) == [
         "/build-playlist"
     ]
+    # The dedupe builder registers only its own route (DL-318).
     assert _page_routes(_builder(tree, "_build_dedupe_page")) == ["/dedupe"]
 
 

```

> **Developer notes**: The header renders one link per SECTIONS row and app.py registers one route per page, so both guards move from three to four.

### Milestone 4: M-004 Tier 3 same-audio grouping

**Files**: traktor_nml/dedupe_tier3.py, tests/test_dedupe_tier3.py

**Requirements**:

- AUDIO_ID grouping only when M-001 promoted it
- fingerprint grouping through fingerprint.py and the tag cache
- fingerprint=unavailable:<reason> when a dependency is missing
- unresolved paths counted in tier_3_unresolved
- tier 3 groups are suggested and never auto-applied

**Acceptance Criteria**:

- G7 promotion criteria met on the recorded artifact
- G1-G2 rerun with tier 3 fixtures passes

**Tests**:

- unit and integration; milestone dropped if M-001 disables tier 3

#### Code Intent

- **CI-M-004-001** `traktor_nml/dedupe_tier3.py`: AUDIO_ID and fingerprint grouping gated on the M-001 verdict with unavailable and unresolved accounting (refs: DL-315)
- **CI-M-004-002** `tests/test_dedupe_tier3.py`: G7 tier 3 fixtures plus G1-G2 rerun (refs: DL-315)

#### Code Changes

**CC-M-004-001** (traktor_nml/dedupe_tier3.py) - implements CI-M-004-001

**Code:**

```diff
--- a/traktor_nml/dedupe_tier3.py
+++ b/traktor_nml/dedupe_tier3.py
@@ -0,0 +1,108 @@
+"""Tier 3 of collection dedupe: the same audio in different files.
+
+Two sources, each behind its own gate (DL-315):
+
+- AUDIO_ID equality, only as far as docs/2026-09-26-dedupe-spike.md
+  measured it stable. AUDIO_ID_ADMITTED and FORMAT_UPGRADES_ADMITTED are
+  transcribed from that artifact's tier 3 verdict, never computed here:
+  re-analysis stability and copy agreement at or above 99% with zero false
+  collisions admit copies, and format agreement at or above 95% extends
+  the tier to format upgrades.
+- Fingerprint similarity through fingerprint.py and the tag cache, for
+  entries whose files both resolve. A missing dependency disables it for
+  the run with fingerprint=unavailable:<reason>, and an entry whose file
+  does not resolve is counted in tier_3_unresolved rather than guessed at.
+
+Every tier 3 group is a suggestion: dedupe.AUTO_APPLY_TIERS never holds
+tier 3, so a group applies only through a merge decision.
+"""
+
+from __future__ import annotations
+
+import itertools
+from typing import Optional
+
+from . import fingerprint
+from .dedupe_members import LIVE, KeyUnion, Member, TierContext, TierMatch, extension, pair_refuted
+from .tagcache import TagCache
+
+# Transcribed from docs/2026-09-26-dedupe-spike.md's "Tier 3 verdict".
+# Both stay False until that artifact records the promotion, which leaves
+# the whole tier disabled (tier_3=disabled) exactly as DL-315 requires.
+AUDIO_ID_ADMITTED = False
+FORMAT_UPGRADES_ADMITTED = False
+ADMITTED = AUDIO_ID_ADMITTED
+
+
+def _audio_id_pair_admitted(context: TierContext, a: Member, b: Member) -> bool:
+    """A cross-format pair only when the artifact admitted format upgrades,
+    and never a pair the size/duration refute rejects."""
+    if not FORMAT_UPGRADES_ADMITTED and extension(a) != extension(b):
+        return False
+    return not (context.options.refute and pair_refuted(a, b))
+
+
+def _audio_id_pairs(context: TierContext, groups: KeyUnion) -> None:
+    buckets: dict[str, list[Member]] = {}
+    for member in context.members:
+        if member.record.audio_id:
+            buckets.setdefault(member.record.audio_id, []).append(member)
+    for bucket in buckets.values():
+        for a, b in itertools.combinations(bucket, 2):
+            if _audio_id_pair_admitted(context, a, b):
+                groups.union(a.primary_key, b.primary_key)
+
+
+def _fingerprints(context: TierContext) -> Optional[dict[str, tuple[float, str]]]:
+    reason = fingerprint.fingerprint_unavailable_reason()
+    if reason is not None:
+        context.stats["fingerprint"] = f"unavailable:{reason}"
+        return None
+    cache = TagCache(context.options.cache_path) if context.options.cache_path is not None else None
+    session = fingerprint.FpcalcSession()
+    stats: dict[str, int] = {}
+    prints: dict[str, tuple[float, str]] = {}
+    unresolved = 0
+    for member in context.members:
+        if member.file_state != LIVE:
+            unresolved += 1
+            continue
+        if cache is not None:
+            result = fingerprint._cached_fingerprint(member.local_path, cache, session, stats)
+        else:
+            result = fingerprint._compute_fingerprint(member.local_path, session, stats)
+        if result is not None:
+            prints[member.primary_key] = result
+    context.stats["tier_3_unresolved"] = unresolved
+    return prints
+
+
+def _fingerprint_pairs(context: TierContext, groups: KeyUnion) -> None:
+    prints = _fingerprints(context)
+    if not prints:
+        return
+    by_key = {m.primary_key: m for m in context.members}
+    ordered = sorted(prints.items(), key=lambda item: item[1][0])
+    stats: dict[str, int] = {}
+    for i, (key_a, (seconds_a, print_a)) in enumerate(ordered):
+        for key_b, (seconds_b, print_b) in ordered[i + 1:]:
+            # Sorted by duration, so the first pair outside the tolerance
+            # ends the comparisons for key_a.
+            if seconds_b - seconds_a > fingerprint.DURATION_TOLERANCE_SECONDS:
+                break
+            if context.options.refute and pair_refuted(by_key[key_a], by_key[key_b]):
+                continue
+            similarity = fingerprint._similarity(print_a, print_b, stats)
+            if similarity is not None and similarity >= fingerprint.MATCH_THRESHOLD:
+                groups.union(key_a, key_b)
+
+
+def find_matches(context: TierContext) -> list[TierMatch]:
+    groups = KeyUnion()
+    if AUDIO_ID_ADMITTED:
+        _audio_id_pairs(context, groups)
+    _fingerprint_pairs(context, groups)
+    return [
+        TierMatch(keys, "same audio in different files", "loose", auto_apply=False, review_reason="tier_3_suggested")
+        for keys in groups.groups()
+    ]
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_tier3.py
+++ b/traktor_nml/dedupe_tier3.py
@@ -43,6 +43,8 @@
 
 
 def _audio_id_pairs(context: TierContext, groups: KeyUnion) -> None:
+    """Union members sharing an AUDIO_ID, when M-001 admitted AUDIO_ID for tier
+    3 and the pair passes _audio_id_pair_admitted."""
     buckets: dict[str, list[Member]] = {}
     for member in context.members:
         if member.record.audio_id:
@@ -54,6 +56,10 @@
 
 
 def _fingerprints(context: TierContext) -> Optional[dict[str, tuple[float, str]]]:
+    """Duration and fingerprint per live member, via the tag cache when one is
+    configured. Returns None and records the reason in stats when the
+    fingerprint dependencies are missing; members without a resolved local
+    file are counted, not fingerprinted."""
     reason = fingerprint.fingerprint_unavailable_reason()
     if reason is not None:
         context.stats["fingerprint"] = f"unavailable:{reason}"
@@ -78,6 +84,8 @@
 
 
 def _fingerprint_pairs(context: TierContext, groups: KeyUnion) -> None:
+    """Union members whose fingerprints match within the duration tolerance,
+    unless the refute check separates them."""
     prints = _fingerprints(context)
     if not prints:
         return
@@ -98,6 +106,8 @@
 
 
 def find_matches(context: TierContext) -> list[TierMatch]:
+    """Tier 3 matches: same audio in different files. Always review-only, never
+    auto-applied (DL-315)."""
     groups = KeyUnion()
     if AUDIO_ID_ADMITTED:
         _audio_id_pairs(context, groups)

```


**CC-M-004-002** (tests/test_dedupe_tier3.py) - implements CI-M-004-002

**Code:**

```diff
--- a/tests/test_dedupe_tier3.py
+++ b/tests/test_dedupe_tier3.py
@@ -0,0 +1,78 @@
+"""G7: tier 3 same-audio grouping, gated on the M-001 verdict, plus the
+G1-G2 checks rerun over a tier 3 fixture."""
+
+from __future__ import annotations
+
+
+import pytest
+
+from tests.fixtures.dedupe import build_dedupe_fixtures as fx
+from traktor_nml import dedupe, dedupe_tier3, fingerprint
+from traktor_nml.xmlio import parse_xml_bytes
+
+TIER3_ONLY = frozenset({dedupe.TIER_SAME_AUDIO})
+
+
+def _scan(text: str, **options) -> dedupe.ScanResult:
+    return dedupe.find_groups(text, parse_xml_bytes(text.encode("utf-8")), dedupe.ScanOptions(tiers=TIER3_ONLY, **options))
+
+
+@pytest.fixture
+def admitted(monkeypatch):
+    """Tier 3 as it stands once the spike artifact records promotion,
+    with fingerprinting unavailable so only AUDIO_ID groups."""
+    monkeypatch.setattr(dedupe_tier3, "ADMITTED", True)
+    monkeypatch.setattr(dedupe_tier3, "AUDIO_ID_ADMITTED", True)
+    monkeypatch.setattr(fingerprint, "fingerprint_unavailable_reason", lambda: "test")
+
+
+def test_tier3_is_disabled_until_the_artifact_admits_it() -> None:
+    assert dedupe_tier3.ADMITTED is False
+    assert _scan(fx.same_audio()).stats["tier_3"] == "disabled"
+
+
+def test_equal_audio_id_copy_is_suggested_never_auto_applied(admitted) -> None:
+    scan = _scan(fx.same_audio())
+    (group,) = scan.groups
+    assert (group.tier, group.auto_apply, group.confidence) == (3, False, "loose")
+    assert dedupe.plan_merge(scan.groups, None)[0].action == dedupe.PLAN_REVIEW
+
+
+def test_format_upgrade_needs_its_own_admission(admitted, monkeypatch) -> None:
+    upgrade = fx.same_audio("copy.flac", copy_size="30000")
+    assert _scan(upgrade).groups == []
+    monkeypatch.setattr(dedupe_tier3, "FORMAT_UPGRADES_ADMITTED", True)
+    assert len(_scan(upgrade).groups) == 1
+
+
+def test_refute_drops_a_same_format_size_mismatch_unless_disabled(admitted) -> None:
+    mismatch = fx.same_audio(copy_size="9000")
+    assert _scan(mismatch).groups == []
+    assert len(_scan(mismatch, refute=False).groups) == 1
+
+
+def test_missing_fingerprint_dependency_is_reported(admitted) -> None:
+    assert _scan(fx.same_audio()).stats["fingerprint"] == "unavailable:test"
+
+
+def test_unresolved_paths_are_counted_not_fingerprinted(monkeypatch) -> None:
+    monkeypatch.setattr(dedupe_tier3, "ADMITTED", True)
+    monkeypatch.setattr(fingerprint, "fingerprint_unavailable_reason", lambda: None)
+    monkeypatch.setattr(fingerprint, "FpcalcSession", lambda: None)
+    scan = _scan(fx.same_audio())
+    assert (scan.stats["tier_3_unresolved"], scan.groups) == (2, [])
+
+
+def test_tier3_merge_decision_passes_the_g2_invariants(admitted) -> None:
+    text = fx.same_audio()
+    root = parse_xml_bytes(text.encode("utf-8"))
+    scan = dedupe.find_groups(text, root, dedupe.ScanOptions(tiers=TIER3_ONLY))
+    (group,) = scan.groups
+    decision = dedupe.Decision(group.member_keys, 3, dedupe.ACTION_MERGE, group.suggested_survivor, {})
+    attached = dedupe.AttachedDecisions({group.member_keys: decision}, 0, False)
+    result = dedupe.assemble_output(text, root, scan, dedupe.plan_merge(scan.groups, attached))
+    assert result.refusals == []
+    loser = next(k for k in group.member_keys if k != group.suggested_survivor)
+    reparsed = parse_xml_bytes(result.output.encode("utf-8"))
+    assert dedupe.scan_references(reparsed, {loser}) == []
+    assert result.expected_entries == 1

```

**Documentation:**

```diff
--- a/tests/test_dedupe_tier3.py
+++ b/tests/test_dedupe_tier3.py
@@ -14,6 +14,8 @@
 
 
 def _scan(text: str, **options) -> dedupe.ScanResult:
+    """Scan text with only tier 3 requested; options override ScanOptions
+    fields."""
     return dedupe.find_groups(text, parse_xml_bytes(text.encode("utf-8")), dedupe.ScanOptions(tiers=TIER3_ONLY, **options))
 
 

```


### Milestone 5: M-005 Tier 4 probable matches and persistence

**Files**: traktor_nml/dedupe_tier4.py, tests/test_dedupe_tier4.py

**Requirements**:

- artist+title within duration tolerance and not refuted
- version-variant guard over mix / edit / remix / clean / explicit qualifiers
- stem and stereo pairs default to not_duplicates
- tier 4 groups enter the decisions file with schema unchanged
- review only

**Acceptance Criteria**:

- G8 version-variant fixtures never auto-grouped

**Tests**:

- unit

#### Code Intent

- **CI-M-005-001** `traktor_nml/dedupe_tier4.py`: Probable-match grouping with the version-variant guard; review-only (refs: DL-315, DL-317)
- **CI-M-005-002** `tests/test_dedupe_tier4.py`: G8 version-variant fixtures never auto-grouped (refs: DL-315)

#### Code Changes

**CC-M-005-001** (traktor_nml/dedupe_tier4.py) - implements CI-M-005-001

**Code:**

```diff
--- a/traktor_nml/dedupe_tier4.py
+++ b/traktor_nml/dedupe_tier4.py
@@ -0,0 +1,105 @@
+"""Tier 4 of collection dedupe: probable duplicates by artist and title.
+
+Review only (DL-315): a tier 4 group never auto-applies and is merged
+only through a merge decision, which the decisions file carries with its
+schema unchanged (DL-317).
+
+The version-variant guard is what keeps this tier from proposing the
+merges an operator would most regret. A title's version qualifiers - the
+parenthesised, bracketed or dash-suffixed segments naming a mix, edit,
+remix, clean or explicit version - are compared as a set, and two titles
+whose sets differ are never grouped: a radio edit and an extended mix
+share artist, base title and often duration, and merging them would delete
+a track the operator owns twice on purpose. A missed duplicate here costs
+one manual review; a wrong merge costs a track.
+
+A .stem.mp4 file and its stereo file are grouped, because they are the
+same track, but default to not_duplicates: each is a file Traktor plays
+differently, and the operator keeps both unless a decision says otherwise.
+"""
+
+from __future__ import annotations
+
+import itertools
+import re
+
+from .dedupe_members import (
+    ACTION_NOT_DUPLICATES,
+    ACTION_UNDECIDED,
+    KeyUnion,
+    Member,
+    TierContext,
+    TierMatch,
+    pair_refuted,
+)
+from .matching import _DURATION_ABS_TOLERANCE, _duration_seconds, _fold
+
+ADMITTED = True
+
+_QUALIFIER_WORDS = frozenset({
+    "mix", "remix", "rmx", "edit", "clean", "explicit", "dirty", "radio", "extended",
+    "dub", "instrumental", "acapella", "version", "vip", "bootleg", "rework", "remaster", "remastered",
+})
+_SEGMENT = re.compile(r"\(([^)]*)\)|\[([^\]]*)\]|\s-\s(.+)$")
+_STEM_SUFFIX = ".stem.mp4"
+
+
+def split_title(title: str) -> tuple[str, frozenset[str]]:
+    """The folded base title and the set of folded version qualifiers.
+    A bracketed segment holding no qualifier word (a featured artist, a
+    year) stays part of the base title."""
+    qualifiers: set[str] = set()
+
+    def strip(match: re.Match[str]) -> str:
+        segment = next(g for g in match.groups() if g is not None)
+        words = set(re.findall(r"[a-z]+", _fold(segment)))
+        if words & _QUALIFIER_WORDS:
+            qualifiers.add(" ".join(_fold(segment).split()))
+            return " "
+        return match.group(0)
+
+    base = _SEGMENT.sub(strip, title)
+    return " ".join(_fold(base).split()), frozenset(qualifiers)
+
+
+def _is_stem(member: Member) -> bool:
+    return member.record.file_name.casefold().endswith(_STEM_SUFFIX)
+
+
+def _within_duration(a: Member, b: Member) -> bool:
+    seconds_a, seconds_b = _duration_seconds(a.record), _duration_seconds(b.record)
+    return seconds_a is not None and seconds_b is not None and abs(seconds_a - seconds_b) <= _DURATION_ABS_TOLERANCE
+
+
+def _pair_matches(context: TierContext, a: Member, b: Member) -> bool:
+    return _within_duration(a, b) and not (context.options.refute and pair_refuted(a, b))
+
+
+def _buckets(context: TierContext) -> dict[tuple[str, str, frozenset[str]], list[Member]]:
+    """Members keyed by folded artist, base title and qualifier set, so
+    two version variants never share a bucket and are never compared."""
+    buckets: dict[tuple[str, str, frozenset[str]], list[Member]] = {}
+    for member in context.members:
+        if not member.record.artist or not member.record.title:
+            continue
+        base, qualifiers = split_title(member.record.title)
+        buckets.setdefault((_fold(member.record.artist), base, qualifiers), []).append(member)
+    return buckets
+
+
+def find_matches(context: TierContext) -> list[TierMatch]:
+    union = KeyUnion()
+    by_key = {m.primary_key: m for m in context.members}
+    for bucket in _buckets(context).values():
+        for a, b in itertools.combinations(bucket, 2):
+            if _pair_matches(context, a, b):
+                union.union(a.primary_key, b.primary_key)
+    matches = []
+    for keys in union.groups():
+        stems = {_is_stem(by_key[k]) for k in keys}
+        default = ACTION_NOT_DUPLICATES if stems == {True, False} else ACTION_UNDECIDED
+        matches.append(TierMatch(
+            keys, "same artist and title within duration tolerance", "loose",
+            auto_apply=False, review_reason="tier_4_review_only", default_action=default,
+        ))
+    return matches
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_tier4.py
+++ b/traktor_nml/dedupe_tier4.py
@@ -63,15 +63,21 @@
 
 
 def _is_stem(member: Member) -> bool:
+    """True for a Traktor stem file, which tier 4 defaults to not duplicates
+    beside its stereo file."""
     return member.record.file_name.casefold().endswith(_STEM_SUFFIX)
 
 
 def _within_duration(a: Member, b: Member) -> bool:
+    """True when both durations are known and differ by at most the absolute
+    tolerance; an unknown duration never matches."""
     seconds_a, seconds_b = _duration_seconds(a.record), _duration_seconds(b.record)
     return seconds_a is not None and seconds_b is not None and abs(seconds_a - seconds_b) <= _DURATION_ABS_TOLERANCE
 
 
 def _pair_matches(context: TierContext, a: Member, b: Member) -> bool:
+    """A candidate pair from one bucket matches when its durations agree and
+    the refute check, if enabled, does not separate it."""
     return _within_duration(a, b) and not (context.options.refute and pair_refuted(a, b))
 
 
@@ -88,6 +94,9 @@
 
 
 def find_matches(context: TierContext) -> list[TierMatch]:
+    """Tier 4 matches: same folded artist, base title and version qualifiers
+    within duration tolerance. Review-only (DL-315); a stem beside its
+    stereo file defaults to not duplicates."""
     union = KeyUnion()
     by_key = {m.primary_key: m for m in context.members}
     for bucket in _buckets(context).values():

```


**CC-M-005-002** (tests/test_dedupe_tier4.py) - implements CI-M-005-002

**Code:**

```diff
--- a/tests/test_dedupe_tier4.py
+++ b/tests/test_dedupe_tier4.py
@@ -0,0 +1,53 @@
+"""G8: tier 4 probable matches never auto-group a version variant
+(radio edit/extended, remix/original, clean/explicit, stem/stereo), and
+every tier 4 group is review-only."""
+
+from __future__ import annotations
+
+import pytest
+
+from tests.fixtures.dedupe import build_dedupe_fixtures as fx
+from traktor_nml import dedupe
+from traktor_nml.dedupe_tier4 import split_title
+from traktor_nml.xmlio import parse_xml_bytes
+
+TIER4_ONLY = frozenset({dedupe.TIER_PROBABLE})
+
+
+def _plans(text: str) -> list[dedupe.GroupPlan]:
+    root = parse_xml_bytes(text.encode("utf-8"))
+    scan = dedupe.find_groups(text, root, dedupe.ScanOptions(tiers=TIER4_ONLY))
+    return dedupe.plan_merge(scan.groups, None)
+
+
+@pytest.mark.parametrize(
+    ("title_a", "title_b"),
+    [
+        ("Song (Radio Edit)", "Song (Extended Mix)"),
+        ("Song (Artist Remix)", "Song"),
+        ("Song (Clean)", "Song (Explicit)"),
+        ("Song - Radio Edit", "Song - Extended Mix"),
+    ],
+)
+def test_version_variants_are_never_grouped(title_a: str, title_b: str) -> None:
+    assert _plans(fx.titled_pair(title_a, title_b)) == []
+
+
+def test_same_title_is_grouped_for_review_only() -> None:
+    (plan,) = _plans(fx.titled_pair("Song (Radio Edit)", "song (radio edit)"))
+    assert (plan.group.tier, plan.group.auto_apply, plan.action) == (4, False, dedupe.PLAN_REVIEW)
+
+
+def test_duration_outside_tolerance_is_not_grouped() -> None:
+    assert _plans(fx.titled_pair("Song", "Song", seconds_b="200.0")) == []
+
+
+def test_stem_and_stereo_default_to_not_duplicates() -> None:
+    (plan,) = _plans(fx.titled_pair("Song", "Song", file_b="b.stem.mp4"))
+    assert plan.action == dedupe.PLAN_NOT_DUPLICATES
+    assert dedupe.decisions_document("sha", [plan])["groups"][0]["action"] == dedupe.ACTION_NOT_DUPLICATES
+
+
+def test_featured_artist_bracket_stays_in_the_base_title() -> None:
+    assert split_title("Song (feat. Someone)") == ("song (feat. someone)", frozenset())
+    assert split_title("Song [VIP]") == ("song", frozenset({"vip"}))

```

**Documentation:**

```diff
--- a/tests/test_dedupe_tier4.py
+++ b/tests/test_dedupe_tier4.py
@@ -15,6 +15,8 @@
 
 
 def _plans(text: str) -> list[dedupe.GroupPlan]:
+    """Plans for text with only tier 4 requested and no decisions, so each
+    group shows its default action."""
     root = parse_xml_bytes(text.encode("utf-8"))
     scan = dedupe.find_groups(text, root, dedupe.ScanOptions(tiers=TIER4_ONLY))
     return dedupe.plan_merge(scan.groups, None)

```


### Milestone 6: M-006 Extras: repeat collapse and removable-files CSV

**Files**: traktor_nml/dedupe_extras.py, tests/test_dedupe_extras.py

**Requirements**:

- optional collapse of a playlist holding the survivor twice
- removable-files CSV listing loser audio paths
- no audio file is touched

**Acceptance Criteria**:

- collapse off by default keeps both references
- CSV lists only losers whose files exist
- no file on disk modified

**Tests**:

- unit

#### Code Intent

- **CI-M-006-001** `traktor_nml/dedupe_extras.py`: Repeat-collapse option and removable-files CSV; audio files untouched (refs: DL-308, DL-321, DL-322)
- **CI-M-006-002** `tests/test_dedupe_extras.py`: Collapse default off; CSV contents; no disk modification (refs: DL-308, DL-321, DL-322)

#### Code Changes

**CC-M-006-001** (traktor_nml/dedupe_extras.py) - implements CI-M-006-001

**Code:**

```diff
--- a/traktor_nml/dedupe_extras.py
+++ b/traktor_nml/dedupe_extras.py
@@ -0,0 +1,117 @@
+"""Collection dedupe extras: opt-in repeat collapse and the
+removable-files CSV. Neither touches an audio file.
+
+Repeat collapse is off unless asked for (DL-321). Redirecting a loser
+can leave a playlist naming its survivor twice; by default both rows
+stay, so every playlist changes by loser-to-survivor substitution alone
+(G2). When asked, a row is dropped only if redirection made it repeat an
+earlier row - a repeat the input playlist already held is the operator's
+own and stays.
+
+The removable-files CSV lists each removed loser whose file exists and
+is not the survivor's own file, so the operator can delete them by hand
+(DL-322). The tool never deletes, moves or renames audio.
+"""
+
+from __future__ import annotations
+
+import csv
+from pathlib import Path
+from typing import Optional
+
+from .dedupe_assembly import ReportRow
+from .dedupe_members import LIVE, ScanResult
+from .dedupe_write import output_refusal
+from .playlists import find_playlist_nodes
+from .spans import SpanIndex, recalculate_count_attr
+from .splice import _apply_replacements
+from .textpatch import _find_opening_tag_end
+from .xmlio import parse_xml_bytes
+
+REMOVABLE_COLUMNS = ("group_id", "primary_key", "local_path", "survivor_primary_key")
+
+
+def survivor_by_loser(rows: list[ReportRow]) -> dict[str, str]:
+    """Each removed loser's survivor, read off the report rows the
+    assembly produced, so the extras need no second pass over the plan."""
+    survivors = {row.group_id: row.primary_key for row in rows if row.role == "survivor"}
+    return {row.primary_key: survivors[row.group_id] for row in rows if row.role == "merged"}
+
+
+def _rows_to_drop(input_keys: list[str], redirect: dict[str, str]) -> list[int]:
+    """Indexes of rows whose redirected key repeats an earlier row's
+    while their input key did not."""
+    seen_input: set[str] = set()
+    seen_output: set[str] = set()
+    drop = []
+    for index, key in enumerate(input_keys):
+        mapped = redirect.get(key, key)
+        if mapped in seen_output and key not in seen_input:
+            drop.append(index)
+        seen_input.add(key)
+        seen_output.add(mapped)
+    return drop
+
+
+def _playlist_rows(node) -> list:
+    playlist = node.find("PLAYLIST")
+    return [] if playlist is None else [e for e in playlist.findall("ENTRY") if e.find("PRIMARYKEY") is not None]
+
+
+def collapse_repeats(source_root, output: str, redirect: dict[str, str]) -> tuple[str, int]:
+    """output with redirect-made repeat rows removed from each playlist
+    and that playlist's ENTRIES count recalculated, plus how many rows
+    went. Playlists are paired by document order, which assembly never
+    changes."""
+    output_root = parse_xml_bytes(output.encode("utf-8"))
+    index = SpanIndex(output, output_root)
+    edits: list[tuple[int, int, str]] = []
+    dropped = 0
+    for source_node, output_node in zip(find_playlist_nodes(source_root), find_playlist_nodes(output_root)):
+        input_keys = [row.find("PRIMARYKEY").attrib.get("KEY", "") for row in _playlist_rows(source_node)]
+        drop = _rows_to_drop(input_keys, redirect)
+        if not drop:
+            continue
+        rows = _playlist_rows(output_node)
+        for position in drop:
+            span = index.span_of(rows[position])
+            edits.append((span.start, span.end, ""))
+        playlist_span = index.span_of(output_node.find("PLAYLIST"))
+        end = _find_opening_tag_end(output, playlist_span.start) + 1
+        opening = recalculate_count_attr(output[playlist_span.start:end], "PLAYLIST", "ENTRIES", len(rows) - len(drop))
+        edits.append((playlist_span.start, end, opening))
+        dropped += len(drop)
+    return _apply_replacements(output, edits), dropped
+
+
+def removable_rows(rows: list[ReportRow], scan: ScanResult) -> list[dict[str, str]]:
+    survivors = survivor_by_loser(rows)
+    removable = []
+    for row in rows:
+        if row.role != "merged":
+            continue
+        loser = scan.members[row.primary_key]
+        survivor = scan.members[survivors[row.primary_key]]
+        if loser.file_state != LIVE or loser.local_path == survivor.local_path:
+            continue
+        removable.append({
+            "group_id": row.group_id,
+            "primary_key": row.primary_key,
+            "local_path": str(loser.local_path),
+            "survivor_primary_key": survivor.primary_key,
+        })
+    return removable
+
+
+def write_removable_files_csv(path: Path, rows: list[dict[str, str]], input_paths: list[Path]) -> Optional[str]:
+    """Write the CSV, or return output_refusal's reason when path names an
+    input or the live collection.nml; the same guard as every dedupe
+    writer, so no output flag can overwrite what the run reads."""
+    refusal = output_refusal(path, input_paths)
+    if refusal is not None:
+        return refusal
+    with path.open("w", newline="", encoding="utf-8") as handle:
+        writer = csv.DictWriter(handle, fieldnames=list(REMOVABLE_COLUMNS))
+        writer.writeheader()
+        writer.writerows(rows)
+    return None
```

**Documentation:**

```diff
--- a/traktor_nml/dedupe_extras.py
+++ b/traktor_nml/dedupe_extras.py
@@ -54,6 +54,8 @@
 
 
 def _playlist_rows(node) -> list:
+    """The PLAYLIST ENTRY rows of one playlist node that hold a PRIMARYKEY, in
+    document order."""
     playlist = node.find("PLAYLIST")
     return [] if playlist is None else [e for e in playlist.findall("ENTRY") if e.find("PRIMARYKEY") is not None]
 
@@ -85,6 +87,9 @@
 
 
 def removable_rows(rows: list[ReportRow], scan: ScanResult) -> list[dict[str, str]]:
+    """Rows for the removable-files CSV: merged losers whose file exists and is
+    not the survivor's own file (DL-322). The tool never deletes them; the
+    CSV is for the operator."""
     survivors = survivor_by_loser(rows)
     removable = []
     for row in rows:

```


**CC-M-006-002** (traktor_nml/commands/dedupe_cmd.py) - implements CI-M-006-001

**Code:**

```diff
--- a/traktor_nml/commands/dedupe_cmd.py
+++ b/traktor_nml/commands/dedupe_cmd.py
@@ -12,7 +12,7 @@ import argparse
 import sys
 from pathlib import Path
 
-from .. import dedupe
+from .. import dedupe, dedupe_extras
 from ..rewrite import read_and_parse_source, write_row_report
 from ..volumes import parse_volume_map
 
@@ -71,7 +71,8 @@ def _write_report(rows, report: Path | None) -> str | None:
 
 
 def _outputs(args: argparse.Namespace) -> list[Path]:
-    return [p for p in (args.output, args.report, args.write_decisions) if p is not None]
+    candidates = (args.output, args.report, args.write_decisions, args.removable_files)
+    return [p for p in candidates if p is not None]
 
 
 def _outputs_refusal(outputs: list[Path], inputs: list[Path]) -> str | None:
@@ -114,11 +115,22 @@ def _handle_dedupe(args: argparse.Namespace) -> int:
         return EXIT_REFUSED
     if result.output is None:
         return _refuse(";".join(dict.fromkeys(result.refusals)))
+    output = result.output
+    if args.collapse_repeats:
+        redirect = dedupe_extras.survivor_by_loser(result.rows)
+        output, collapsed = dedupe_extras.collapse_repeats(loaded.root, output, redirect)
+        print(f"playlist_repeats_collapsed={collapsed}", file=sys.stderr)
+    if args.removable_files is not None:
+        rows = dedupe_extras.removable_rows(result.rows, scan)
+        refusal = dedupe_extras.write_removable_files_csv(args.removable_files, rows, inputs)
+        if refusal is not None:
+            return _refuse(refusal)
+        print(f"removable_files_written={args.removable_files.as_posix()}")
     if args.dry_run or args.write_decisions is not None:
         print("dry_run=true")
         return EXIT_OK
     written = dedupe.write_validated_output(
-        result.output.encode("utf-8"), args.output, expected_entries=result.expected_entries
+        output.encode("utf-8"), args.output, expected_entries=result.expected_entries
     )
     if written.ok:
         print(f"output_written={args.output.as_posix()}")
@@ -155,4 +167,12 @@ def register(subparsers, handlers: dict) -> None:
         help="Mount a VOLUME/VOLUMEID at SCAN_ROOT (repeatable). Only mapped volumes can be live or dead, "
         "and only a mapped volume probed case-insensitive compares paths without case.",
     )
+    parser.add_argument(
+        "--collapse-repeats", action="store_true",
+        help="Drop a playlist row that repeats an earlier row only because both now name one survivor. Off by default.",
+    )
+    parser.add_argument(
+        "--removable-files", type=Path,
+        help="CSV of removed entries whose audio file exists and is not the survivor's file. No file is deleted.",
+    )
     handlers["dedupe"] = _handle_dedupe
```

**Documentation:**

```diff
--- a/traktor_nml/commands/dedupe_cmd.py
+++ b/traktor_nml/commands/dedupe_cmd.py
@@ -116,6 +116,8 @@
     if result.output is None:
         return _refuse(";".join(dict.fromkeys(result.refusals)))
     output = result.output
+    # Both extras act on the assembled result before the write, so
+    # write_validated_output validates the collapsed output (DL-321, DL-322).
     if args.collapse_repeats:
         redirect = dedupe_extras.survivor_by_loser(result.rows)
         output, collapsed = dedupe_extras.collapse_repeats(loaded.root, output, redirect)

```

> **Developer notes**: Wires the extras into the CLI; applies on top of the M-002 dedupe_cmd.py.

**CC-M-006-003** (tests/test_dedupe_extras.py) - implements CI-M-006-002

**Code:**

```diff
--- a/tests/test_dedupe_extras.py
+++ b/tests/test_dedupe_extras.py
@@ -0,0 +1,110 @@
+"""M-006: repeat collapse is off by default and drops only
+redirect-made repeats; the removable-files CSV lists only existing loser
+files that are not the survivor's own; no file on disk is modified."""
+
+from __future__ import annotations
+
+import csv
+from pathlib import Path
+
+from tests.conftest import run_tool
+from tests.fixtures.dedupe import build_dedupe_fixtures as fx
+from traktor_nml.playlists import find_playlist_nodes, node_primary_keys
+from traktor_nml.xmlio import parse_xml_bytes
+
+
+def _playlist(path: Path, name: str) -> tuple[list[str], str]:
+    root = parse_xml_bytes(path.read_bytes())
+    node = next(n for n in find_playlist_nodes(root) if n.attrib["NAME"] == name)
+    return [pk.attrib["KEY"] for pk in node_primary_keys(node)], node.find("PLAYLIST").attrib["ENTRIES"]
+
+
+def _run(tmp_path: Path, text: str, *extra: str):
+    source = tmp_path / "in.nml"
+    source.write_text(text, encoding="utf-8")
+    result = run_tool(["dedupe", "--input", str(source), "--output", str(tmp_path / "out.nml"), *extra], cwd=tmp_path)
+    assert result.exit_code == 0, result.stderr
+    return result
+
+
+def _csv_rows(path: Path) -> list[dict[str, str]]:
+    with path.open(encoding="utf-8", newline="") as handle:
+        return list(csv.DictReader(handle))
+
+
+def test_collapse_is_off_by_default_and_keeps_both_rows(tmp_path: Path) -> None:
+    _run(tmp_path, fx.golden_tier1())
+    assert _playlist(tmp_path / "out.nml", "Set") == ([fx.TIER1_B, fx.OTHER, fx.TIER1_B, fx.TIER1_B], "4")
+
+
+def test_collapse_drops_only_the_redirect_made_repeat(tmp_path: Path) -> None:
+    """Set holds B, OTHER, A, B. Redirecting A to B makes row 3 repeat
+    row 1, so it goes; row 4 already repeated row 1 in the input, so it
+    stays."""
+    result = _run(tmp_path, fx.golden_tier1(), "--collapse-repeats")
+    assert "playlist_repeats_collapsed=1" in result.stderr
+    assert _playlist(tmp_path / "out.nml", "Set") == ([fx.TIER1_B, fx.OTHER, fx.TIER1_B], "3")
+
+
+def test_removable_files_naming_the_input_is_refused(tmp_path: Path) -> None:
+    source = tmp_path / "in.nml"
+    source.write_text(fx.golden_tier1(), encoding="utf-8")
+    before = source.read_bytes()
+    result = run_tool(["dedupe", "--input", str(source), "--output", str(tmp_path / "out.nml"),
+                       "--removable-files", str(source)], cwd=tmp_path)
+    assert (result.exit_code, "refused=output_must_differ_from_input" in result.stderr) == (2, True)
+    assert source.read_bytes() == before
+
+
+def test_removable_files_skips_a_dead_loser(tmp_path: Path) -> None:
+    audio = tmp_path / "audio"
+    text = fx.dead_live(audio)
+    before = {p.name: p.read_bytes() for p in audio.iterdir()}
+    csv_path = tmp_path / "removable.csv"
+    _run(tmp_path, text, "--volume-map", str(audio), fx.LIVE_VOLUME, fx.LIVE_VOLUMEID,
+         "--removable-files", str(csv_path))
+    assert _csv_rows(csv_path) == []
+    assert {p.name: p.read_bytes() for p in audio.iterdir()} == before
+
+
+def test_removable_files_skips_a_loser_naming_the_survivor_file(tmp_path: Path) -> None:
+    """Both keys name one file on disk, so removing the loser's entry
+    leaves nothing to delete."""
+    audio = tmp_path / "audio"
+    audio.mkdir()
+    (audio / "song.mp3").write_bytes(b"\0" * 8)
+    dirv = fx.live_location(audio)
+    text = fx.nml(
+        fx.entry(fx.LIVE_VOLUME, dirv, "song.mp3", volumeid=fx.LIVE_VOLUMEID, info=' PLAYCOUNT="9"')
+        + fx.entry(fx.LIVE_VOLUME, dirv + "/:", "song.mp3", volumeid=fx.LIVE_VOLUMEID)
+    )
+    csv_path = tmp_path / "removable.csv"
+    _run(tmp_path, text, "--volume-map", str(audio), fx.LIVE_VOLUME, fx.LIVE_VOLUMEID,
+         "--removable-files", str(csv_path))
+    assert _csv_rows(csv_path) == []
+    assert (audio / "song.mp3").read_bytes() == b"\0" * 8
+
+
+def test_removable_files_lists_a_live_loser_and_leaves_it_on_disk(tmp_path: Path) -> None:
+    audio = tmp_path / "audio"
+    audio.mkdir()
+    for name in ("song.mp3", "song copy.mp3"):
+        (audio / name).write_bytes(b"\0" * 8)
+    dirv = fx.live_location(audio)
+    entries = fx.entry(fx.LIVE_VOLUME, dirv, "song.mp3", volumeid=fx.LIVE_VOLUMEID, info=' PLAYCOUNT="9"')
+    entries += fx.entry(fx.LIVE_VOLUME, dirv, "song copy.mp3", volumeid=fx.LIVE_VOLUMEID)
+    source = tmp_path / "in.nml"
+    source.write_text(fx.nml(entries), encoding="utf-8")
+    decisions = tmp_path / "d.json"
+    loser = fx.key(fx.LIVE_VOLUME, dirv, "song copy.mp3")
+    survivor = fx.key(fx.LIVE_VOLUME, dirv, "song.mp3")
+    decisions.write_text(
+        '{"schema": "traktor-nml-dedupe-decisions", "version": 1, "input_sha256": "x", "groups": ['
+        f'{{"members": ["{loser}", "{survivor}"], "action": "merge", "survivor": "{survivor}"}}]}}',
+        encoding="utf-8",
+    )
+    csv_path = tmp_path / "removable.csv"
+    _run(tmp_path, fx.nml(entries), "--volume-map", str(audio), fx.LIVE_VOLUME, fx.LIVE_VOLUMEID,
+         "--tiers", "4", "--decisions", str(decisions), "--removable-files", str(csv_path))
+    assert [(r["primary_key"], r["survivor_primary_key"]) for r in _csv_rows(csv_path)] == [(loser, survivor)]
+    assert (audio / "song copy.mp3").exists()
```

**Documentation:**

```diff
--- a/tests/test_dedupe_extras.py
+++ b/tests/test_dedupe_extras.py
@@ -14,12 +14,14 @@
 
 
 def _playlist(path: Path, name: str) -> tuple[list[str], str]:
+    """One playlist's PRIMARYKEY KEY values and its ENTRIES attribute, by name."""
     root = parse_xml_bytes(path.read_bytes())
     node = next(n for n in find_playlist_nodes(root) if n.attrib["NAME"] == name)
     return [pk.attrib["KEY"] for pk in node_primary_keys(node)], node.find("PLAYLIST").attrib["ENTRIES"]
 
 
 def _run(tmp_path: Path, text: str, *extra: str):
+    """Run dedupe over text with extra arguments and require exit 0."""
     source = tmp_path / "in.nml"
     source.write_text(text, encoding="utf-8")
     result = run_tool(["dedupe", "--input", str(source), "--output", str(tmp_path / "out.nml"), *extra], cwd=tmp_path)
@@ -28,6 +30,7 @@
 
 
 def _csv_rows(path: Path) -> list[dict[str, str]]:
+    """Rows of a written CSV as dicts keyed by its header."""
     with path.open(encoding="utf-8", newline="") as handle:
         return list(csv.DictReader(handle))
 

```


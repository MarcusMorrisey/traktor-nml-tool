# traktor_nml/

## Files

| File               | What                                                       | When to read                                              |
| ------------------ | ----------------------------------------------------------- | ----------------------------------------------------------- |
| `README.md`        | Architecture, design decisions, invariants, tradeoffs      | Understanding why the package is structured this way       |
| `__init__.py`      | Package marker                                             | -                                                           |
| `model.py`         | `LocationParts`/`RewriteRule`/`EntryRecord`, LOCATION/PRIMARYKEY parsing | Adding an identity field, changing LOCATION encode/decode  |
| `xmlio.py`         | lxml/stdlib ET parsing wrapper                             | Changing how NML files are parsed or serialized            |
| `textpatch.py`     | `apply_text_patches`/`ElemPatch` byte-preserving attribute writes | Changing how LOCATION/PRIMARYKEY attribute rewrites are applied |
| `rewrite.py`       | Rule-based and compare-based rewrite patch collection, `write_nml_safely`; also `read_and_parse_source`, `write_bytes_atomically`, `path_collides`, and `write_row_report`, reusable read/write/report helpers other commands are expected to call | Modifying the rewrite/compare cascade or the write path    |
| `confidence.py`    | `MatchConfidence` ordered enum (strict/loose/filename) and the tier ladder each level admits | Adding a match tier or confidence level                    |
| `matching.py`      | `record_keys`/`match_records` tiered match cascade, the path-suffix tiers, and the size/duration refutation filter | Changing match-key tiers, matching tolerances, or ambiguity detection |
| `diskscan.py`      | Filesystem candidate scanning for reconnection; candidate `filesize` is bytes on disk, not Traktor's kilobytes | Adding or changing disk-scan candidate discovery            |
| `discovery.py`     | Fuzzy artist/title ranking of disk and collection candidates; review-only, never selects or writes | Changing discovery scoring, normalisation, or stop words   |
| `tagcache.py`      | Tag-read caching                                           | Changing tag cache key composition or eviction             |
| `reconnect.py`     | Disk-scan reconnection; `location_from_disk_path` (candidate-side volume-relative-to-absolute transform) and `enforce_one_to_one`, the shared one-to-one assignment post-pass compare-based rewriting also calls | Modifying reconnection matching or destination-collision handling |
| `volumes.py`       | VOLUME/VOLUMEID inference from existing collection paths, plus `local_path_for_location` resolving a location back to its on-disk path | Changing volume identity resolution or `--volume-map`      |
| `fingerprint.py`   | Acoustic fingerprint comparison (optional chromaprint dep); the old side resolves its path through `volumes.py` rather than from `decoded_path` | Modifying fingerprint matching or its availability guard   |
| `spans.py`         | Byte-span transplantation, `OutputBuilder`, count-attribute recalculation, `SpanIndex` as the single-pass identity locator | Modifying splice/split's structural write path or count recalculation |
| `playlists.py`     | Playlist import for splice (merge, rename, redirect); nodes are located through the shared `SpanIndex`, not a UUID text search | Modifying playlist merge, collision-rename, or PRIMARYKEY redirect logic |
| `splice.py`        | Merge-command core: conflict resolution, playlist import; builds one `SpanIndex` per input source | Modifying splice's conflict policy or merge algorithm      |
| `split.py`         | Partition-command core: filter, dangling-reference policy scoped to the group's own resolved playlist nodes, spans from the shared `SpanIndex` | Modifying split's selection filter or dangling-reference handling |
| `tracklist.py`     | External track-list parsing and per-line collection resolution | Changing tracklist input format or per-line resolution      |
| `buildplaylist.py` | build-playlist core: resolution, playlist synthesis, insertion | Modifying playlist synthesis or its insertion point          |
| `cli.py`           | Subcommand discovery and argparse wiring                   | Adding a subcommand or changing dispatch                   |

## Subdirectories

| Directory   | What                              | When to read                                    |
| ----------- | --------------------------------- | ------------------------------------------------ |
| `commands/` | One module per CLI subcommand     | Adding a subcommand or changing its arguments/handler |

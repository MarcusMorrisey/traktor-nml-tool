# tests/

## Files

| File                     | What                                                        | When to read                                              |
| ------------------------ | ------------------------------------------------------------- | ------------------------------------------------------------ |
| `__init__.py`            | Package marker                                               | -                                                             |
| `conftest.py`            | `run_tool`/`fixture_corpus` fixtures shared across test modules | Adding a test module, changing how the CLI is invoked under test |
| `test_baseline_parity.py`| Byte-level parity oracle against `baselines/manifest.json`    | Changing any CLI subcommand's output, exit code, or written bytes |
| `test_cli_contract.py`   | Subcommand surface + `--allow-artist-title-only`/`--match-confidence` alias contract; splice/split malformed-input and atomic-write tests | Adding/renaming a subcommand, changing legacy-flag equivalence |
| `test_compare.py`        | Compare-based rewrite input-protection and destination-collision tests | Changing `rewrite_from_collection_compare` or `compare_cmd.py`'s write path |
| `test_diskscan.py`       | Disk-scan candidate discovery tests                            | Changing `diskscan.py`                                        |
| `test_discovery.py`      | Fuzzy discovery stays review-only and works on untagged files  | Changing `discovery.py` or either discover subcommand         |
| `test_parity_baseline.py`| Tamper-evidence for the oracle itself: pins `manifest.json`'s own SHA-256 | Regenerating the baseline, or changing what the pin guarantees |
| `test_reconnect.py`      | Reconnection matching, path-suffix tiers, size/duration refutation, one-to-one assignment | Changing `reconnect.py`, `volumes.py`, `matching.py`'s tiers, or a matching tolerance |
| `test_fingerprint.py`    | Acoustic fingerprint comparison tests                          | Changing `fingerprint.py`                                     |
| `test_spans.py`          | Byte-span scanner, `OutputBuilder`, count-attribute recalculation tests | Changing `spans.py`                                           |
| `test_splice.py`         | Splice merge/conflict-resolution tests                         | Changing `splice.py` or `playlists.py`                        |
| `test_split.py`          | Split filter/dangling-reference tests                          | Changing `split.py`                                           |
| `test_tracklist.py`      | External track-list parsing and per-line resolution tests      | Changing `tracklist.py`                                       |
| `test_build_playlist.py` | build-playlist synthesis, insertion and CLI-surface tests       | Changing `buildplaylist.py`, its insertion point, or `commands/build_playlist_cmd.py` |
| `test_xmlio.py`          | `parse_xml_bytes`'s lxml/stdlib backend-selection tests          | Changing `xmlio.py`'s parsing helpers                        |

## Subdirectories

| Directory    | What                                                      | When to read                                          |
| ------------ | ----------------------------------------------------------- | -------------------------------------------------------- |
| `fixtures/`  | `build_fixtures.py`: constructs the on-disk NML fixture corpus | Adding a new fixture NML file or scenario               |
| `baselines/` | `manifest.json` (golden CLI-invocation baseline) + `regenerate.py` + `manifest.schema.md` | Regenerating the baseline after a deliberate, reviewed behavior change |

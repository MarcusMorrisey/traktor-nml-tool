# tests/

## Files

| File                     | What                                                        | When to read                                              |
| ------------------------ | ------------------------------------------------------------- | ------------------------------------------------------------ |
| `__init__.py`            | Package marker                                               | -                                                             |
| `conftest.py`            | `run_tool`/`fixture_corpus` fixtures shared across test modules | Adding a test module, changing how the CLI is invoked under test |
| `test_baseline_parity.py`| Byte-level parity oracle against `baselines/manifest.json`, asserting stdout, stderr, exit code and output bytes per case | Changing any CLI subcommand's output, exit code, or written bytes |
| `test_cli_contract.py`   | Subcommand surface + `--allow-artist-title-only`/`--match-confidence` alias contract; splice/split malformed-input and atomic-write tests | Adding/renaming a subcommand, changing legacy-flag equivalence |
| `test_command_layer_printless.py` | Guard that `commands/reconnect_cmd.py` holds no print call and writes to neither stream | Changing `reconnect_cmd.py`'s handlers, or the printless-command-layer convention |
| `test_compare.py`        | Compare-based rewrite input-protection and destination-collision tests | Changing `rewrite_from_collection_compare` or `compare_cmd.py`'s write path |
| `test_diskscan.py`       | Disk-scan candidate discovery tests                            | Changing `diskscan.py`                                        |
| `test_fpcalc_session.py` | Owned fpcalc child: output parsing, per-file timeout, mid-fingerprint termination, and that a cancelled session spawns nothing further. Uses a stub fpcalc via the FPCALC env var | Changing `FpcalcSession`, the fingerprint timeout, or cancellation |
| `test_scan_progress_cancel.py` | Merge gates for the GUI plan's sections 3.4 and 3.5: progress callback contract (monotonic, final-once, batched, parity) and scan-loop cancellation | Changing `index_scan_roots`' progress or cancel behaviour |
| `test_discovery.py`      | Fuzzy discovery stays review-only and works on untagged files  | Changing `discovery.py` or either discover subcommand         |
| `test_parity_baseline.py`| Tamper-evidence for the oracle itself: pins `manifest.json`'s own SHA-256 | Regenerating the baseline, or changing what the pin guarantees |
| `test_reconnect.py`      | Reconnection matching, path-suffix tiers, size/duration refutation and `--no-refute`, one-to-one assignment, and the `_CASCADE`/ladder consistency checks | Changing `reconnect.py`, `volumes.py`, `matching.py`'s tiers, a matching tolerance, or the cascade table |
| `test_reconnect_render_equivalence.py` | Renderer output compared against the recorded reconnect manifest cases (all four pass `--match-confidence filename`; no `--fingerprint` or strict/normal/loose/bare_name case exists), plus the fingerprint and no-refute warning paths the oracle does not exercise | Changing `reconnect_run.py` or `reconnect_render.py` |
| `test_scan_diagnostics.py` | Direct-core capture tests for the two scan diagnostics the parity oracle cannot reach - the missing-mutagen line and the progress lines - exercising both the default-print-to-stderr and additive-collector transports of `on_diagnostic` | Changing what `index_scan_roots` reports or how it is transported |
| `test_fingerprint.py`    | Fingerprint tier end to end: generates two-bitrate audio fixtures with ffmpeg, pins the duration pre-filter and the degrade-on-broken-comparison path, and gates each test on the dependency it actually needs | Changing `fingerprint.py`, or a test here skipping unexpectedly |
| `test_spans.py`          | Byte-span scanner, `OutputBuilder`, count-attribute recalculation tests | Changing `spans.py`                                           |
| `test_splice.py`         | Splice merge/conflict-resolution tests                         | Changing `splice.py` or `playlists.py`                        |
| `test_split.py`          | Split filter/dangling-reference tests                          | Changing `split.py`                                           |
| `test_tracklist.py`      | External track-list parsing and per-line resolution tests      | Changing `tracklist.py`                                       |
| `test_write_shell_split.py` | `plan_and_write_nml` unit tests: output-collision stats-is-None, text_patch_error keeping its collected stats ahead of the error, callback-exception propagation, and printlessness across every outcome. No manifest case sets an output path equal to its input and no manifest case carries both a stats block and a stderr error, so this is the only test exercising the collision refusal and the stats-before-error ordering | Changing `plan_and_write_nml`, `WriteOutcome`, or `format_stats_and_samples` |
| `test_build_playlist.py` | build-playlist synthesis, insertion and CLI-surface tests       | Changing `buildplaylist.py`, its insertion point, or `commands/build_playlist_cmd.py` |
| `test_xmlio.py`          | `parse_xml_bytes`'s lxml/stdlib backend-selection tests          | Changing `xmlio.py`'s parsing helpers                        |

## Subdirectories

| Directory    | What                                                      | When to read                                          |
| ------------ | ----------------------------------------------------------- | -------------------------------------------------------- |
| `fixtures/`  | `build_fixtures.py`: constructs the on-disk NML fixture corpus | Adding a new fixture NML file or scenario               |
| `baselines/` | `manifest.json` (golden CLI-invocation baseline) + `regenerate.py` + `manifest.schema.md` | Regenerating the baseline after a deliberate, reviewed behavior change |

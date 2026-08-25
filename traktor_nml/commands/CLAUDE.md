# traktor_nml/commands/

## Files

| File                | What                                                          | When to read                                          |
| ------------------- | -------------------------------------------------------------- | -------------------------------------------------------- |
| `__init__.py`       | Package marker; `cli.py` iterates this package to find subcommands | Adding a new command module                           |
| `inspect_cmd.py`    | `inspect`/`encode-dir` subcommands                             | Changing collection/playlist inspection output        |
| `rewrite_cmd.py`    | `preview-diff`/`rewrite` subcommands (rule-based rewriting)    | Changing rule-based path rewrite behavior              |
| `compare_cmd.py`    | `preview-compare`/`scan-compare-candidates`/`rewrite-from-collection-compare` subcommands; the rewrite declares both collections as inputs so an output resolving to either is refused (DL-023), and enforces one-to-one through `reconnect.enforce_one_to_one` (DL-015) | Changing compare-based rewrite or candidate scanning   |
| `reconnect_cmd.py`  | `scan-reconnect-candidates`/`rewrite-from-reconnect` subcommands (disk-scan reconnection); resolves volume identities before key providers are built and supplies them to the fingerprint provider as its known-mounts mapping | Changing reconnection's CLI surface or stats output    |
| `discover_tracks_cmd.py` | `discover-tracks` subcommand: ranks disk-scanned files for an external track list, writing only a CSV report | Changing disk-side discovery's CLI surface or report columns |
| `discover_collection_tracks_cmd.py` | `discover-collection-tracks` subcommand: ranks existing collection entries for an external track list, never altering the NML | Changing collection-side discovery's CLI surface or report columns |
| `splice_cmd.py`     | `splice` subcommand (merge NML files); reads/parses through `rewrite.read_and_parse_source` and commits through `rewrite.write_bytes_atomically` | Changing splice's CLI surface, conflict flags, or reports |
| `split_cmd.py`      | `split` subcommand (partition an NML file); reads/parses through `rewrite.read_and_parse_source`, builds one `SpanIndex` per input and hands it to `build_output` for every group, and commits each group through `rewrite.write_bytes_atomically` | Changing split's CLI surface or dangling-reference flags |
| `build_playlist_cmd.py` | `build-playlist` subcommand (external-tracklist playlist synthesis); reads/parses through `rewrite.read_and_parse_source`, aborts unless `--allow-unmatched` is passed on any unresolved track, and commits through `rewrite.write_bytes_atomically` | Changing that subcommand's CLI surface or its unresolved-track report |

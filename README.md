# traktor-nml-tool

A CLI for inspecting, repairing, merging, and splitting Traktor DJ software's `.nml` collection files.

## What it does

- **Inspect** a collection's stats, or encode a human path into Traktor's own DIR format.
- **Rewrite paths** by an explicit old→new volume/directory rule.
- **Reconnect a stale collection** two ways:
  - against a newer collection covering the same tracks (`rewrite-from-collection-compare`), or
  - against the actual files on disk, scanning one or more directories and matching by audio tags and optionally acoustic fingerprints (`rewrite-from-reconnect`).
- **Merge** additional `.nml` files into a base collection (`splice`), or **partition** one collection into several outputs by playlist (`split`).
- **Build a playlist** from an external plain-text track list, matched against a base collection (`build-playlist`). Outputs a self-contained single-playlist NML by default; use `--full-collection` to retain the source collection.
- **Discover candidate files** for an external track list across one or more folders (`discover-tracks`); writes a review CSV and never modifies an NML.
- **Discover collection candidates** for an external track list with the same relaxed scoring (`discover-collection-tracks`); writes a review CSV and never modifies an NML.

Every command previews before writing, refuses to overwrite any of its own inputs, and reports ambiguous or dangling matches explicitly (via stats and CSV export) rather than silently guessing.

`--dry-run` only suppresses writes to the command's declared output file. One exception: `rewrite-from-reconnect` (and `scan-reconnect-candidates`) still write/update their `--cache` tag-cache file (default `.traktor_nml_tagcache.json`) during the disk scan, since that cache is a scan-speedup side file, not the command's output.

## Install

```bash
pip install lxml mutagen pyacoustid  # lxml required; mutagen/pyacoustid optional (tag reading / fingerprinting)
```

`pyacoustid` also needs the `fpcalc` binary (from [Chromaprint](https://acoustid.org/chromaprint)) on `PATH` for acoustic fingerprinting. Everything else degrades gracefully if these are absent.

## Usage

```bash
python traktor_nml_tool.py --help
python traktor_nml_tool.py inspect collection.nml
python traktor_nml_tool.py rewrite-from-reconnect old.nml new.nml --scan-root D:/Music --dry-run
python traktor_nml_tool.py discover-tracks tracks.txt review.csv --scan-root D:/Music
python traktor_nml_tool.py discover-collection-tracks collection.nml tracks.txt review.csv
```

See [the package architecture guide](traktor_nml/README.md) for design
decisions and invariants. See [the documentation index](docs/README.md) for
project planning material and retained development context.

## Tests

```bash
pytest tests/ -q
```

A few tests in `tests/test_spans.py` exercise a real-world-scale corpus (`collection_textual_patch_test.nml`, not tracked in this repo — see `.gitignore`) and skip gracefully when it's absent.

## Project history

The original design and implementation plans are retained in [`docs/`](docs/)
for reference.
# License

This project is licensed under the GNU General Public License v2.0 only (GPL-2.0-only). See [LICENSE](LICENSE).

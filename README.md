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

Matching also **refutes** a candidate whose `FILESIZE` or `PLAYTIME_FLOAT` contradicts the collection entry, and reports how many it withdrew as `refuted=N` — distinct from `unmatched`, so "found it and declined" never looks like "file is gone". Those tolerances are calibrated against one real library; if they reject files you know are correct, `--no-refute` turns the check off. Both the counter and the flag appear on the five commands that compare records carrying a size and a duration: `preview-compare`, `scan-compare-candidates`, `rewrite-from-collection-compare`, `scan-reconnect-candidates` and `rewrite-from-reconnect`. A run using the flag warns on stderr, because a candidate the collection's own numbers contradict can then win a match.

`build-playlist` is deliberately not in that list even though it runs the same cascade: a plain-text track list carries no size or duration, so there is nothing for the check to contradict and it can never fire. A flag there would do nothing.

`--dry-run` suppresses the write to the command's declared **NML output file only**. Side files are still written, because each is a record of what the run saw rather than the artifact the run produces:

- `rewrite-from-reconnect` and `scan-reconnect-candidates` write/update their `--cache` tag-cache file (default `.traktor_nml_tagcache.json`) during the disk scan.
- `build-playlist` writes its `--unresolved-report` CSV.
- `splice` writes its `--conflict-report` CSV.
- `rewrite-from-reconnect` writes its `--csv` ambiguity report.

So `--dry-run` with a report path is the supported way to review what a run *would* do without touching the collection. If you want no files written at all, omit the report and cache paths.

## Install

```bash
pip install lxml mutagen pyacoustid  # lxml required; mutagen/pyacoustid optional (tag reading / fingerprinting)
```

Installing from a checkout with `pyproject.toml` present, the same optional
dependencies are available as extras: `pip install .[tags]` for `mutagen`,
`pip install .[fingerprint]` for `pyacoustid`, `pip install .[gui]` for
`nicegui`, or `pip install .[all]` for all three together.

`pyacoustid` also needs the `fpcalc` binary (from [Chromaprint](https://acoustid.org/chromaprint)) on `PATH` to compute fingerprints, **and** the chromaprint shared library to compare them - the standalone `fpcalc` download ships the binary only. With any of the three missing, `--fingerprint` names which one and matches nothing rather than failing. Everything else degrades gracefully if these are absent.

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

## Running on a server (Docker)

There is no web interface and nothing listens on a port — this is a CLI, so
the container runs one subcommand and exits:

```bash
docker compose run --rm nml inspect /work/collection.nml
```

The image is worth having for one specific reason: the fingerprint tier needs
`fpcalc` **and** the chromaprint shared library, and upstream ships no
prebuilt shared library for any platform. Debian packages both, so the tier
works in the container even where it is dark on the desktop.

**The mount path is load-bearing.** `rewrite-from-reconnect` writes each
matched file's path back into the collection, stripping only the path's anchor
(`/` on Linux, a drive letter on Windows). So the path *inside* the container
must equal the path Traktor records below its own `VOLUME`:

| Traktor records | volume-relative path | container must see | so mount library root at |
| --- | --- | --- | --- |
| `VOLUME="D:" DIR="/:Music/:Techno/:"` | `Music/Techno/…` | `/Music/Techno/…` | `/Music` |

Mounting the library at `/music` or `/media/music` instead will write those
paths into your collection, and Traktor will not find a single track. Preview
with `--dry-run` and read the `sample_matches` lines before writing anything.

Copy `.env.example` to `.env` for host paths and `PUID`/`PGID` — the collection
is bind-mounted and rewritten in place, so the container must own it.

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

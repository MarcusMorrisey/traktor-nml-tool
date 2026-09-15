# traktor-nml-tool

A CLI for inspecting, repairing, merging, and splitting Traktor DJ software's `.nml` collection files.

## What it does

- **Inspect** a collection's stats, or encode a human path into Traktor's own DIR format.
- **Rewrite paths** by an explicit old→new volume/directory rule.
- **Reconnect a stale collection** two ways:
  - against a newer collection covering the same tracks (`rewrite-from-collection-compare`), or
  - against the actual files on disk, scanning one or more directories and matching by audio tags and optionally acoustic fingerprints (`rewrite-from-reconnect`).
- **Merge** additional `.nml` files into a base collection (`splice`), or **partition** one collection into several outputs by playlist (`split`).
- **Reconstruct playlists** in a base collection from the playlists at the same folder path in an older one (`splice --reconstruct-playlists`), for a collection whose playlists survive by name while their contents do not.
- **Build a playlist** from an external plain-text track list, matched against a base collection (`build-playlist`). Outputs a self-contained single-playlist NML by default; use `--full-collection` to retain the source collection.
- **Discover candidate files** for an external track list across one or more folders (`discover-tracks`); writes a review CSV and never modifies an NML.
- **Discover collection candidates** for an external track list with the same relaxed scoring (`discover-collection-tracks`); writes a review CSV and never modifies an NML.

Every command previews before writing, refuses to overwrite any of its own inputs, and reports ambiguous or dangling matches explicitly (via stats and CSV export) rather than silently guessing.

Matching also **refutes** a candidate whose `FILESIZE` or `PLAYTIME_FLOAT` contradicts the collection entry, and reports how many it withdrew as `refuted=N` — distinct from `unmatched`, so "found it and declined" never looks like "file is gone". Those tolerances are calibrated against one real library; if they reject files you know are correct, `--no-refute` turns the check off. Both the counter and the flag appear on the five commands that compare records carrying a size and a duration: `preview-compare`, `scan-compare-candidates`, `rewrite-from-collection-compare`, `scan-reconnect-candidates` and `rewrite-from-reconnect`. A run using the flag warns on stderr, because a candidate the collection's own numbers contradict can then win a match.

### Reconstructing playlists

`splice --reconstruct-playlists` targets a base collection whose playlists carry their names without their contents, with an older collection holding those contents. A base playlist pairs with the incoming playlist at the same folder path - `Folder\Sub\Name`, the identity Traktor's own `SORTING_INFO PATH` gives it - and is rebuilt only when its contents differ from that one's, compared as an ordered sequence of track identities rather than as entry counts, so `[one, two]` against `[two, three]` is a difference and a reordering is too.

A bare `NAME` does not identify a playlist, because a real collection reuses one freely across folders: one measured collection holds 1,187 playlists under 768 distinct names. A playlist with no counterpart at its own path falls back to its name, but only where that name names exactly one playlist on each side; where it names more, nothing says which playlist the older copy belongs to and base's is left alone rather than rebuilt from a guess.

A rebuilt playlist keeps base's own node, UUID and folder position; its entries become base's own in their existing order, followed by every incoming entry not already among them, folded across each `--input` file in the order given and deduplicated. A playlist whose contents already match is left untouched and its incoming copy is not imported. Without the flag, a same-named incoming playlist is imported beside base's as `"<name> (2)"`, which is the default for every existing invocation.

When two collections hold one track and disagree about its tags, `splice` refuses rather than picking for you. `--on-conflict keep-first` or `keep-last` settles every such track for the whole run; without it the run aborts and the `--conflict-report` CSV names each disagreement. The wizard's Reconstruct playlists screen resolves them one track at a time instead, offering the values each collection holds.

`splice` also refuses to write an output that would break the collection it assembled: two entries for one file (`entry_location_collision`), or an entry count that does not match what it merged (`collection_entry_count`). Each is reported and nothing is written.

One situation aborts the run with nothing written, rather than resolving by document order: a playlist folder path appearing more than once on either side, which offers no single playlist to rebuild or to rebuild from. It is reported through the same `--conflict-report` CSV as a merge conflict.

Two other situations are reported and written rather than refused, because the condition is in the collections the run reads and refusing it would discard every playlist the run rebuilt:

- An incoming entry whose track identity matches more than one entry in base is placed on the first of them - the record the merge already redirects that key to - and counted in `entries_on_duplicated_tracks`, with the playlists carrying them in `playlists_on_duplicated_tracks`.
- A playlist entry naming a track no collection in the run holds an entry for is dropped from the playlist carrying it and counted in `entries_dropped_unresolvable`, with the distinct tracks in `tracks_dropped_unresolvable` and the playlists in `playlists_with_dropped_entries`. Traktor resolves such a reference to nothing, so carrying it into a repaired file would preserve a pointer to nothing.

Track identity is resolved through the same cascade the merge itself uses, so a base and an older collection referring to one track at different paths still pair up.

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

## The desktop app

With the `gui` extra installed, `python -m traktor_nml.gui` opens a
desktop window holding two sections, reached by the tabs in its header.
Both run the same cores the subcommands do, over the same collections,
and neither writes anything until you confirm the write on its last step.

**Reconstruct playlists** is the repair described above, as four steps:

1. **Set up** - name the collection to repair, one or more older
   collections to take playlist contents from, and where the new file
   goes. Each collection reads back its own tracks, playlists and how
   many of those are empty, so you can see you picked the file you meant.
2. **Preview** - assembles the repair in memory and counts it back: which
   playlists were filled, how many entries that added, and which ones no
   collection could fill. Nothing is written.
3. **Resolve** - where the collections hold one track with different
   values, every answer is listed with the collections that hold it and
   you pick which record supplies it, one track at a time or all from one
   collection at once. This is what `--on-conflict` decides in bulk from
   the command line.
4. **Write** - states what the new file will hold before it is written,
   including what the run could not do cleanly: entries placed on a track
   the collection holds twice, and entries dropped because no collection
   holds the track they name.

**Reconnect wizard** is `rewrite-from-reconnect` as four steps - set up,
scan, review, write - for reviewing ambiguous and refuted matches
interactively instead of adjudicating them from the ambiguity CSV.

The window is the same page served over a local port; nothing leaves the
machine, and every collection it reads is opened read-only for the whole
run.

## Usage

```bash
python -m traktor_nml.gui     # the desktop app
python traktor_nml_tool.py --help
python traktor_nml_tool.py inspect collection.nml
python traktor_nml_tool.py rewrite-from-reconnect old.nml new.nml --scan-root D:/Music --dry-run
python traktor_nml_tool.py discover-tracks tracks.txt review.csv --scan-root D:/Music
python traktor_nml_tool.py discover-collection-tracks collection.nml tracks.txt review.csv
```

See [the package architecture guide](traktor_nml/README.md) for design
decisions and invariants. See [the documentation index](docs/README.md) for
project planning material and retained development context.

## API documentation

Sphinx-based code documentation lives under `docs/source/`. The API pages are
generated automatically from the `traktor_nml` package at build time, so the
module inventory stays in sync with the code instead of relying on a
hand-maintained file list.

```bash
pip install .[docs]
sphinx-build -b html docs/source docs/build/html
```

The generated site lands at `docs/build/html/index.html`.

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

The run prints the interpreter it used and the optional packages it found, beside its own totals and under `-q` as well. Both interpreters here are legitimate and both are green — they differ in which optional packages are present and so in which tests can execute, which is why a count is only meaningful next to the conditions printed with it.

## Working on this project

After cloning, activate the tracked hooks. Git reads hooks from `.git/hooks` unless told otherwise, and `core.hooksPath` is config rather than content, so it does not clone:

```bash
git config core.hooksPath hooks
```

`hooks/pre-push` refuses to move or delete a `parity-baseline-*` tag, which pins the parity oracle. Until the line above is run it sits on disk inert, which reads exactly like a hook that is working.

Then, at the start of a session:

```bash
python tools/preflight.py
```

It checks what is cheap to check and silent when it fails — that the hooks are wired, that the plan and gate repositories resolve beside this one, and that `traktor_nml/gui/app.py` is still wholly CRLF against an otherwise-LF tree. It runs no tests; `python -m pytest tests/ -q` is the slow check and is run on its own.

## Project history

The original design and implementation plans are retained in [`docs/`](docs/)
for reference.
# License

This project is licensed under the GNU General Public License v2.0 only (GPL-2.0-only). See [LICENSE](LICENSE).

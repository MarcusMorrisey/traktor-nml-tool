# traktor-nml-tool

A CLI for inspecting, repairing, merging, and splitting Traktor DJ software's `.nml` collection files.

## What it does

- **Inspect** a collection's stats, or encode a human path into Traktor's own DIR format.
- **Rewrite paths** by an explicit old→new volume/directory rule.
- **Reconnect a stale collection** two ways:
  - against a newer collection covering the same tracks (`rewrite-from-collection-compare`), or
  - against the actual files on disk, scanning one or more directories and matching by audio tags and optionally acoustic fingerprints (`rewrite-from-reconnect`).
- **Merge** additional `.nml` files into a base collection (`splice`), or **partition** one collection into several outputs by playlist (`split`).

Every command previews before writing, refuses to overwrite any of its own inputs, and reports ambiguous or dangling matches explicitly (via stats and CSV export) rather than silently guessing.

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
```

See `traktor_nml/README.md` for architecture, design decisions, and invariants.

## Tests

```bash
pytest tests/ -q
```

A few tests in `tests/test_spans.py` exercise a real-world-scale corpus (`collection_textual_patch_test.nml`, not tracked in this repo — see `.gitignore`) and skip gracefully when it's absent.

## Project history

`traktor_nml_tool_plan.md` and `traktor_nml_tool_execution_plan.md` are the original design and implementation plans this project was built from, kept for reference.

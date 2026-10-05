# spike/dedupe

The M-001 spike for collection dedupe
(`docs/plans/2026-09-26-collection-dedupe/plan.md`, "M-001 spike
specification"). It measures two things the dedupe core must not assume:
which XML shapes reference a collection entry by its primary key, and
whether Traktor's `AUDIO_ID` is stable enough for tier 3. It writes no NML.

## Inputs

- `--nml`: one real collection NML.
- `--reanalysed`: a copy of that NML after Traktor re-analyses a sample of
  50 of its tracks.
- `--copies`: a folder holding at least 20 byte-identical copies and 20
  format-converted copies of tracks in the collection, each already
  imported into the `--nml` collection so it has an entry of its own.
- `--volume-map SCAN_ROOT VOLUME VOLUMEID`: mounts the collection's
  volumes, so each original entry resolves to its file.

The spike only reads: an `--out` naming an input or the live `collection.nml`
is refused with exit 2, the code `dedupe` uses for refusals (DL-311).

## Command

```
python -m spike.dedupe.measure --nml collection.nml --reanalysed reanalysed.nml \
    --copies D:\dedupe-copies --volume-map D:\ D: D: --out docs/2026-09-26-dedupe-spike.md
```

Run from the repository root. `-m` puts the root on the import path, so
`traktor_nml` resolves; `python spike/dedupe/measure.py` does not.

## How the artifact feeds G0

`docs/2026-09-26-dedupe-spike.md` records the input hashes, the reference
inventory with counts, the stability rates, the dependency state and the
tier 3 verdict. Before M-002 starts, each inventory row gets a handling
decision (redirect, preserve, untouched), and the rows and the verdict are
recorded as decision-log entries in `traktor_nml/README.md` (gate G0).
`traktor_nml/dedupe.py`'s `REDIRECT_SHAPES` and `PRESERVE_SHAPES` are
written from that table; `traktor_nml/dedupe_tier3.py`'s `ADMITTED` is
written from the verdict.

Promotion rule for tier 3 on `AUDIO_ID`: re-analysis stability >= 99%,
copy agreement >= 99%, false collisions = 0. Format agreement >= 95%
extends tier 3 to format upgrades; below it, tier 3 covers copies only.

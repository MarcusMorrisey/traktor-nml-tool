# Dedupe spike: reference inventory and AUDIO_ID stability

Produced by `spike/dedupe/measure.py` (see `spike/dedupe/README.md`). The
script's `render_artifact` emits these sections, rows and wording, so a run
with `--out` pointing here fills every `<measured>` value in place. Handling
for the shapes plan.md names comes from the script's `KNOWN_HANDLING`; any
further shape the run finds is written as a refusing row and is decided by
hand here before G0.

## Inputs

- `<collection.nml>` sha256 `<measured>`
- `<reanalysed.nml>` sha256 `<measured>`
- copies folder: `<path>`, `<measured>` byte-identical and `<measured>`
  format-converted copies

## Reference inventory

| Shape | Count | Handling |
| --- | --- | --- |
| `PLAYLISTS/PRIMARYKEY@KEY[TRACK]` | `<measured>` | Redirect (playlists, History, `_LOOPS`, `_RECORDINGS`) |
| `PLAYLISTS/PRIMARYKEY@KEY[STEM]` | `<measured>` | Preserve |
| `SETS/PRIMARYKEY@KEY[*]` | `<measured>` | Preserve |
| any other shape | `<measured>` | Refuse (`unknown_reference_shape`) unless decided here |

`INDEXING/SORTING_INFO PATH` names a playlist, not a track, and smartlists
are queries; neither appears in this table because neither holds a
primary key.

A row left as Refuse keeps `dedupe` refusing any collection that holds the
shape, until the row is decided here and recorded under G0 (DL-314, DL-319).

## AUDIO_ID stability

| Metric | Value | Sample |
| --- | --- | --- |
| AUDIO_ID presence | `<measured>` | `<measured>` entries |
| Re-analysis stability | `<measured>` | `<measured>` entries |
| Copy agreement | `<measured>` | `<measured>` copies |
| Format agreement | `<measured>` | `<measured>` copies |
| False collisions | `<measured>` | pairs |

## Dependencies

- mutagen: `<measured>`
- pyacoustid: `<measured>`
- fpcalc: `<measured>`

## Tier 3 verdict

AUDIO_ID for tier 3: `<admitted | not admitted>`; scope `<copies only |
copies and format upgrades | none>`. Admitted only
when re-analysis stability and copy agreement are both at least 99% and
false collisions are zero (DL-315).

## PLAYCOUNT

Duplicate groups with a LAST_PLAYED on every member: `<measured>`; on only
some members: `<measured>`.
DL-316 records `max` unless the second count shows duplicates commonly carry disjoint histories.

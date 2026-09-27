# Collection dedupe

Status: proposed, not started. No `plan.json`/`context.json` yet; this is the
written-up design to feed the planner. Decisions here are provisional until
they land in `traktor_nml/README.md`'s decision log, which governs.

## Problem

Traktor has no way to deduplicate a collection. Duplicates arise from copied
files, format upgrades (MP3 then FLAC), moved or renamed files re-imported
beside a stale entry, and path differences (case, separators, volume name)
that make one file look like two. Deleting an entry by hand in Traktor drops
it from every playlist that references it.

## Goal

A `dedupe` command and a `/dedupe` GUI section that find duplicate
collection entries, let the operator pick a survivor per group, merge the
losers' metadata into it, redirect every playlist reference to it, and write
a new NML. Audio files on disk are never touched.

## Non-goals

- Deleting, moving or renaming audio files (a CSV of removable files is the most it offers).
- Editing the input NML in place.
- Keyboard or accessibility work beyond what the existing shell already provides.

## Architecture

Follows the existing three-layer split (DL-069):

| Layer | New module | Role |
| --- | --- | --- |
| Core, printless | `traktor_nml/dedupe.py` | `find_groups(root, options) -> list[DupGroup]`, `plan_merge(groups, decisions)`, `assemble_output(...)`; a stats dict and refusals in the style of `splice` |
| CLI | `traktor_nml/commands/dedupe_cmd.py` | `--tiers`, `--dry-run`, `--report` CSV, `--no-refute`, `--decisions` (JSON of survivors and not-duplicate marks) |
| View model, no nicegui | `traktor_nml/gui/dedupe_model.py`, `dedupe_steps.py` | Groups, survivor suggestion and its reasons, decisions, filter counts, write refusals, report wording |
| Page | `app.py` plus a row in `navigation.SECTIONS` | Set up → scan → review → write, under `run.io_bound` |

### Reuse

| Need | Existing piece |
| --- | --- |
| Identity of two entries | `matching.py` cascade, `confidence.py` tiers |
| Acoustic identity (optional) | `fingerprint.py`, the tag cache |
| Refuting look-alikes | `FILESIZE` / `PLAYTIME_FLOAT` refute and `--no-refute` |
| Redirecting playlist keys | Redirect logic in `playlists.py` / `splice.py` |
| Per-attribute conflict pick | `conflict_model.py`, the `answer_detail.py` rail |
| Write guards | `entry_location_collision`, `collection_entry_count`, refuse-to-overwrite-inputs |
| Path equality | The tool's existing DIR/volume encode and decode, not string comparison |

## Detection tiers

Grouping is bucketed before comparison so it is never all-pairs: bucket by
normalised location, by `AUDIO_ID`, and by normalised artist+title with a
duration bucket.

1. **Exact location** - one file after normalising case, separators and volume. Safe to apply without review.
2. **Dead + live** - an entry whose file is missing, grouped with a live entry of the same identity. Safe once identity is strong.
3. **Same audio** - equal `AUDIO_ID` or fingerprint, different files (copies, format upgrades). Suggested; the operator confirms.
4. **Probable** - artist+title match within duration tolerance, not refuted. Review only; never applied automatically.

Each group carries its tier, the evidence, and a confidence token from the
existing vocabulary.

## Survivor and merge rules

Suggested survivor, in order: file exists → lossless over lossy → higher
bitrate → more cue points / has a beatgrid → higher play count → earliest
import. The reason is shown and the operator may change it.

Merged into the survivor:

| Field | Rule |
| --- | --- |
| `CUE_V2` (cues, loops, grid) | Union by position; a conflicting grid goes to an operator pick |
| `KEY`, `RANKING`, colour, `COMMENT` | Survivor's unless empty; a disagreement goes to the conflict rail |
| `PLAYCOUNT` | Sum (see open questions) |
| `LAST_PLAYED` | Latest |
| `IMPORT_DATE` | Earliest |

Warn whenever a loser holds cues or a grid the survivor lacks and no merge
was chosen.

## Reference redirection

Every reference to a loser is redirected to the survivor: playlists, the
History folder, `_LOOPS`/`_RECORDINGS`, and remix sets. Where a reference
kind cannot be redirected safely, the loser is kept and reported rather than
removed. A playlist left holding the survivor twice keeps both by default;
an option collapses repeats. Smartlists are query-based and unaffected. The
write refuses if any reference would resolve to nothing.

## Decisions persistence

"Not duplicates" marks and chosen survivors are saved to a side JSON keyed
by the member entries' identities, so reviewed pairs (radio edit vs extended
mix) do not resurface. A mark is dropped when its members change.

## Pitfalls and guards

- Version variants: titles whose mix/edit/remix/clean/explicit qualifiers differ are never grouped in tier 4, and the refute check applies in tiers 3-4.
- `.stem.mp4` and its stereo file default to not-duplicates.
- Traktor rewrites `collection.nml` on exit: the page and CLI warn to close Traktor, and output always goes to a new path.
- Cross-platform paths: compare decoded locations, case-folded only where the volume is case-insensitive.
- Large collections: bucketing plus the existing tag/fingerprint cache; progress reported through the existing announcer.
- `AUDIO_ID` stability is unverified: measure it on the real library before tier 3 depends on it (M-001).

## Milestones

1. **M-001 Spike** - measure on the real library: how many groups each tier yields, whether `AUDIO_ID` is stable across copies and re-analysis, which reference kinds exist beyond playlists.
2. **M-002 Core, tiers 1-2** - `dedupe.py` grouping, survivor rule, merge rules, reference redirection, write guards; the CLI with `--dry-run` and `--report`. Golden tests over fixture NMLs, including the dropped-reference refusal.
3. **M-003 GUI** - the `/dedupe` section: set up, scan, review (group list, a filter chip per tier, survivor pick, detail rail), and write with preview counts.
4. **M-004 Tier 3** - `AUDIO_ID` / fingerprint grouping, gated on M-001's findings.
5. **M-005 Tier 4 and persistence** - probable matches, the version-variant guard, not-duplicate marks.
6. **M-006 Extras** - the repeat-collapse option for playlists; the removable-files CSV.

## Open questions

- Should tiers 1-2 be applied in bulk without per-group review?
- Should play counts sum, or take the maximum in case they already overlap?
- Which remix-set and History references occur in the real library?

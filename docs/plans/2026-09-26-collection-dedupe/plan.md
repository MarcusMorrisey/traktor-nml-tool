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

## Assumptions

- A1. Scope is this repository; the dedupe core reuses `xmlio`, `spans`/`textpatch` and `rewrite.write_bytes_atomically` (the temp-file-and-replace writer splice's byte-span path uses) rather than reserialising the tree. `write_nml_safely` is not used: it drives the tree-mutation path and prints its own stats.
- A2. The only authority on which XML shapes carry track references is what M-001 observes in real files plus the fixtures it produces; nothing in this plan is assumed to be exhaustive until M-001 closes.
- A3. Traktor tolerates an NML whose unknown attributes and child elements are byte-preserved; the dedupe never drops an attribute or element it did not parse.
- A4. The operator runs with Traktor closed. The tool cannot detect a running Traktor reliably, so it warns and never writes the live `collection.nml` path.
- A5. Every rule below is provisional until recorded in `traktor_nml/README.md`'s decision log, which happens before M-002 starts (gate G0).

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
| Path equality | The tool's existing DIR/volume encode and decode, not string comparison - but see "Path and volume policy": `matching._fold` casefolds unconditionally, so it is **not** reused for location equality |

Not reusable as-is, and extended in M-002:

- `playlists.find_playlist_nodes` / `node_primary_keys` see only `NODE TYPE=PLAYLIST` and the `PRIMARYKEY`s under it. Every other reference shape needs its own finder (see "Reference inventory").
- `model.EntryRecord` carries identity fields only, and `splice._TRACKED_ATTRS` six attributes. Merge fields get their own representation (see "Merge data model"), not new `EntryRecord` fields.

### CLI contract

`traktor-nml dedupe --input IN.nml --output OUT.nml [--tiers 1,2] [--decisions D.json] [--report R.csv] [--dry-run] [--no-refute] [--volume-map ...]`

- `--tiers` defaults to `1,2`. Tier 3 is admitted only after M-001 promotes it, tier 4 only after M-005. A tier not admitted is not scanned, and the stats say so (`tier_3=disabled`).
- Without `--decisions`, only groups in auto-apply tiers (see "Detection tiers") are merged; every other group is reported and left alone.
- `--write-decisions D.json` writes the decisions template (see "Decisions file") and implies `--dry-run`.
- Exit codes follow the repository convention: `0` written (or dry-run clean); `2` for both usage errors (argparse's own exit, via `cli.py`; no translation is added) and refusals (any refusal below, nothing written), as the existing commands already return `2` for refusals; `3` post-write validation failed (output quarantined, see "Write sequence"). A usage error and a refusal are told apart by stderr: argparse's `usage:` line versus a `refused=<reason>` line.
- Report CSV, one row per group member: `group_id, tier, confidence, evidence, role (survivor|merged|kept|refused), primary_key, file_exists, refs_redirected, refs_preserved, conflicts, refusal_reason`.

## Detection tiers

Grouping is bucketed before comparison so it is never all-pairs: bucket by
normalised location, by `AUDIO_ID`, and by normalised artist+title with a
duration bucket.

1. **Exact location** - one file after normalising separators and volume identity, and case only where "Path and volume policy" allows it. Auto-apply.
2. **Dead + live** - an entry whose file is missing, grouped with exactly one live entry. Auto-apply only when all hold: the live entry's file resolves through an established mount; artist and title are equal after `_fold`; `PLAYTIME_FLOAT` is within the refute tolerance; and `FILESIZE` is within tolerance **or** the formats differ. A group failing any of these drops to review. A dead entry matching two or more live entries is never auto-applied.
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
| `PLAYCOUNT` | Maximum, not sum (duplicates often share one listening history; summing double-counts) |
| `LAST_PLAYED` | Latest |
| `IMPORT_DATE` | Earliest |

Warn whenever a loser holds cues or a grid the survivor lacks and no merge
was chosen.

### Merge data model

The survivor's `ENTRY` element is patched in place through the span/textpatch
path; losers' elements are removed as whole spans. Nothing is reserialised,
so every attribute and child the dedupe does not name survives byte-for-byte
(A3). Merge fields live in a new `MergeFields` record read alongside, not
inside, `EntryRecord`:

| Field | NML source | Parsed as | Equality / conflict identity | Written as |
| --- | --- | --- | --- | --- |
| Cue point | `CUE_V2` with `TYPE` ≠ 4 | `(TYPE, START, LEN, REPEATS, HOTCUE, NAME)` plus raw span | Same `TYPE` and `START` within 1 ms is one cue; differing `NAME`/`HOTCUE` for it is a conflict | Survivor's cues kept verbatim; a loser cue with no counterpart appended as its raw span |
| Hotcue slot | `CUE_V2 HOTCUE` | int | Two different cues claiming one slot is a conflict | Survivor's slot wins unless the operator picks |
| Grid | `CUE_V2 TYPE=4` and its `GRID` child, `TEMPO BPM` | `(START, BPM)` plus raw spans | Equal when `START` within 1 ms and `BPM` within 0.001 | Never merged: one entry's grid block is taken whole; differing grids are a conflict |
| `KEY` | `MUSICAL_KEY VALUE`, `INFO KEY` | raw strings | String equality | Chosen value patched on both |
| `RANKING`, colour | `INFO RANKING`, `INFO COLOR` | raw strings | String equality; empty never conflicts | Patched attribute |
| `COMMENT` | `INFO COMMENT` | raw string | String equality after trim | Patched attribute |
| `PLAYCOUNT` | `INFO PLAYCOUNT` | int, absent = 0 | Never a conflict | `max` |
| `LAST_PLAYED` / `IMPORT_DATE` | `INFO` attrs, `YYYY/M/D` | date; unparseable kept raw | Never a conflict; an unparseable value makes the field survivor-only and is counted | latest / earliest |
| Anything else | any attribute or child not above | not parsed | - | Survivor's untouched; loser's discarded and counted as `loser_fields_discarded` in the report |

A group with any unresolved conflict is not written in auto-apply; it goes to
review. The conflict rail gains a `MergeFields` source beside
`splice._TRACKED_ATTRS`; `_TRACKED_ATTRS` itself is not widened, so splice
behaviour is unchanged.

## Reference redirection

Every reference to a loser is redirected to the survivor: playlists, the
History folder, `_LOOPS`/`_RECORDINGS`, and remix sets. Where a reference
kind cannot be redirected safely, the loser is kept and reported rather than
removed. A playlist left holding the survivor twice keeps both by default;
an option collapses repeats. Smartlists are query-based and unaffected. The
write refuses if any reference would resolve to nothing.

### Reference inventory

M-002 does not start until M-001 has produced this table from real files,
with every row's handling decided. Initial rows (to be confirmed or
extended):

| Shape | Located by | Handling |
| --- | --- | --- |
| Playlist entry | `NODE[@TYPE='PLAYLIST']/PLAYLIST//PRIMARYKEY[@TYPE='TRACK']` | Redirect (existing helpers) |
| History / `_LOOPS` / `_RECORDINGS` | Same shape under their nodes, if M-001 confirms | Redirect |
| Remix set / stem slot reference | To be discovered | Preserve: every entry any such reference names is kept, not merged |
| `INDEXING/SORTING_INFO` | `PATH` names a playlist, not a track | Untouched |
| Smartlist | `NODE[@TYPE='SMARTLIST']` query | Untouched |
| Any `KEY=`/`PRIMARYKEY` shape not in this table | Generic scan of all attributes shaped like a primary key | **Refuse**: the write stops, naming the shape |

The generic scan is the backstop: after redirection, every attribute value
in the output that equals a removed entry's primary key is a dangling
reference and fails the write (`dangling_reference`), so an unknown shape can
never be silently orphaned.

Fixtures (one small NML each, in `tests/fixtures/dedupe/`): redirect per
redirectable row; preservation for a remix-set reference; refusal for an
unknown shape; dangling detection with redirection deliberately disabled.

## Path and volume policy

- Location equality for tier 1 compares `(VOLUMEID, DIR, FILE)` exactly after separator normalisation. `matching._fold` is not used.
- Case is folded only when the volume is known case-insensitive: from a `--volume-map` entry's resolved mount probed at scan time (create-and-stat a case-swapped temp name in a writable scan root, else the platform default: Windows and default macOS insensitive, Linux sensitive). An unprobed volume is treated as case-sensitive, so the failure mode is a missed group, never a wrong merge.
- Volume identity's source of truth is `VOLUMEID`, as `volumes.resolve_volume_identity` produces it. Two entries whose `VOLUME` names match but `VOLUMEID`s differ are different volumes. File existence (tier 2's "live") uses `local_path_for_location` only, so an entry on an unmapped volume is "unknown", not "dead", and never enters tier 2.
- Fixtures: case-only-differing pair on a volume marked case-sensitive (not grouped), same on case-insensitive (grouped), same `VOLUME` with different `VOLUMEID` (not grouped), unmapped volume (neither dead nor live).

## Decisions persistence

"Not duplicates" marks and chosen survivors are saved to a side JSON keyed
by the member entries' identities, so reviewed pairs (radio edit vs extended
mix) do not resurface. A mark is dropped when its members change.

The file records the input NML's SHA-256. On load, a decision whose group
membership no longer matches is discarded and counted (`stale_decisions`);
a whole file recorded against a different input hash is reported, and its
decisions are re-attached per group under the same membership rule rather
than trusted wholesale.

### Decisions file

Owned by M-002: `dedupe.py` reads and writes it, the CLI takes `--decisions`
and `--write-decisions`, and G1/G3 test it. M-003 adds the GUI as a second
producer of the same file. M-005 adds tier 4 groups to it without changing
the schema.

Schema, version 1:

```json
{
  "schema": "traktor-nml-dedupe-decisions",
  "version": 1,
  "input_sha256": "<hex>",
  "groups": [
    {
      "members": ["<primary key>", "..."],
      "tier": 3,
      "action": "undecided | merge | not_duplicates",
      "survivor": "<primary key, required when action is merge>",
      "picks": { "<field name from the merge data model>": "<primary key whose value wins>" }
    }
  ]
}
```

- A group is identified by its sorted `members`. `tier` is informational; a change of tier alone does not make a decision stale.
- Producer workflow (CLI): run with `--write-decisions D.json`; every group outside the auto-apply rules is written with `action: "undecided"`, the suggested `survivor`, and an empty `picks`. The user edits `action`, `survivor` and `picks`, then reruns with `--decisions D.json`. Only `merge` groups with every conflict picked are applied; `undecided` groups are reported and left alone; `not_duplicates` groups are never regrouped.
- Invalid file (not JSON, wrong `schema`, missing required keys, `survivor` not among `members`, a `picks` key not a merge field or naming a non-member): refused with `refused=invalid_decisions:<reason>`, exit 2, nothing written. No partial application.
- Unknown version: a higher `version` is refused as invalid; a lower one is read by the reader for that version, and the file is rewritten at the current version only by `--write-decisions` or the GUI.
- Stale decisions follow the rules above: dropped per group and counted in `stale_decisions`, never a refusal.

## Refusal, recovery and observability

Refusals (exit 2, nothing written): output path equals an input or the
live Traktor collection path; any `dangling_reference`; any unknown reference
shape; `entry_location_collision`; entry count ≠ input count − removed;
input fails to parse.

Write sequence:

1. Assemble output in memory; parse it back; re-run the reference scan and entry-count check on the reparsed tree (pre-write gate).
2. Write through `rewrite.write_bytes_atomically` (temp file + replace) so a failure never truncates the destination.
3. Parse the written file again. On failure, rename it to `OUT.nml.invalid`, exit 3, and report why. The input is never modified, so recovery is: discard the output and rerun.

Steps 2-3 live in one function, `dedupe.write_validated_output(data, output_path) -> WriteResult`, the only write path the CLI handler and the GUI both call, so neither can write without the post-write check. It takes an injectable writer and parser so G5 can force each failure.

A GUI run interrupted before step 2 leaves nothing; interrupted during
step 2 leaves the previous destination intact. Decisions are saved to the
side JSON on every change, so a reopened review resumes.

Stats (CLI stderr, report footer, GUI write step): `groups_by_tier`,
`groups_auto_applied`, `groups_for_review`, `groups_refused` with reasons,
`entries_removed`, `refs_redirected` by shape, `refs_preserved` by shape,
`metadata_conflicts`, `loser_fields_discarded`, `stale_decisions`,
`tier_N=disabled` for each tier not admitted.

## Test gates

Each milestone closes only when its gate passes in CI.

| Gate | Milestone | Must show |
| --- | --- | --- |
| G0 | before M-002 | Deliverable: a commit adding DL entries to `traktor_nml/README.md` for the reference inventory, merge data model, path policy, exit codes and the decisions schema |
| G1 unit | M-002 | Each tier's admission rule, each "Merge data model" row (including cue union, hotcue clash, grid conflict, unparseable date), each path-policy fixture, stale-decision handling |
| G2 integration | M-002 | Every reference-inventory fixture; for each golden input: output reparses, zero dangling references, entry count = input − removed, every non-merged entry's span byte-identical to the input's, each playlist's track sequence unchanged except loser→survivor substitution |
| G3 CLI | M-002 | `dedupe` added to the existing CLI tests; each exit code reached by a fixture, including an argparse usage error returning 2 with a `usage:` line and a refusal returning 2 with `refused=`; `--dry-run` writes no NML; input file's hash unchanged after every run; report CSV columns as specified; `--write-decisions` then `--decisions` round trip; each invalid-decisions case refused |
| G4 malformed input | M-002 | Truncated XML, missing `LOCATION`, duplicate primary keys in input, non-numeric `PLAYCOUNT`: each refuses or is counted, none raises |
| G5 atomic write | M-002 | Injected failure mid-write leaves an existing destination byte-identical; injected post-write parse failure yields `.invalid` and exit 3 |
| G6 GUI | M-003 | View-model tests (no nicegui) for filters, survivor pick, refusals; CLI/GUI parity: same input and decisions give byte-identical output through both |
| G7 tier 3 | M-004 | M-001's promotion criteria met on the recorded artifact, plus G1-G2 rerun with tier 3 fixtures |
| G8 tier 4 | M-005 | Version-variant fixtures (radio edit/extended, remix/original, clean/explicit, stem/stereo) never auto-grouped |

## Pitfalls and guards

- Version variants: titles whose mix/edit/remix/clean/explicit qualifiers differ are never grouped in tier 4, and the refute check applies in tiers 3-4.
- `.stem.mp4` and its stereo file default to not-duplicates.
- Traktor rewrites `collection.nml` on exit: the page and CLI warn to close Traktor, and output always goes to a new path.
- Cross-platform paths: see "Path and volume policy".
- Large collections: bucketing plus the existing tag/fingerprint cache; progress reported through the existing announcer.
- `AUDIO_ID` stability is unverified: measure it on the real library before tier 3 depends on it (M-001).

## Milestones

1. **M-001 Spike** - see "M-001 spike specification". Produces the reference inventory and the tier 3 decision; writes no NML.
2. **M-002 Core, tiers 1-2** - after G0. `dedupe.py` grouping, survivor rule, `MergeFields`, reference redirection and the generic dangling scan, write sequence and `write_validated_output`; the decisions file reader/writer; the CLI contract. Closes on G1-G5.
3. **M-003 GUI** - the `/dedupe` section: set up, scan, review (group list, a filter chip per tier, survivor pick, detail rail), and write with preview counts and the stats above. Closes on G6.
4. **M-004 Tier 3** - `AUDIO_ID` / fingerprint grouping, only if M-001 promoted it. Closes on G7.
5. **M-005 Tier 4 and persistence** - probable matches, the version-variant guard, tier 4 groups in the decisions file (schema unchanged).
6. **M-006 Extras** - the repeat-collapse option for playlists; the removable-files CSV.

## M-001 spike specification

- Input: one real collection NML, a copy of it after Traktor re-analyses a sample of 50 tracks, and a folder holding at least 20 byte-identical copies and 20 format-converted copies of tracks in it; the input hashes are recorded.
- Command: `python spike/dedupe/measure.py --nml ... --reanalysed ... --copies ... --volume-map ... --out docs/2026-MM-DD-dedupe-spike.md` (the script lives in `spike/`, not the package).
- Artifact: that Markdown file, holding groups per tier; `AUDIO_ID` presence rate; stability rates below; every distinct element/attribute shape holding a value equal to some entry's primary key, with counts (the reference inventory); and the dependency state (mutagen, pyacoustid, `fpcalc`) for the run.
- Stability metrics: *re-analysis stability* = share of the 50 whose `AUDIO_ID` is unchanged; *copy agreement* = share of byte-identical copies with equal `AUDIO_ID`; *format agreement* = the same for converted copies; *false collision* = pairs with equal `AUDIO_ID` whose artist/title/duration disagree.
- Promotion rule for tier 3 on `AUDIO_ID`: re-analysis stability ≥ 99%, copy agreement ≥ 99%, false collision = 0. Format agreement decides whether tier 3 also covers format upgrades (≥ 95%) or only copies. Failing any threshold disables `AUDIO_ID` for tier 3; fingerprints are then the only tier 3 source.
- Dependencies: fingerprinting needs `pyacoustid` and `fpcalc` plus a resolvable path for both entries. When any is missing, fingerprint grouping is disabled for the run with `fingerprint=unavailable:<reason>` in the stats; an entry whose path does not resolve is counted in `tier_3_unresolved` and never grouped by fingerprint.

## Open questions

- Should tiers 1-2 be applied in bulk without per-group review? (Default in this plan: yes, under the admission rules above; the GUI still lists them.)
- Which remix-set and History references occur in the real library? (Answered by M-001.)
- Is `max` right for `PLAYCOUNT`, or should duplicates with disjoint histories sum? Needs a real-library check in M-001.

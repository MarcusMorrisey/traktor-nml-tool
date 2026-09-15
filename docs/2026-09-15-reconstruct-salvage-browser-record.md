# Served-page record: a run writes what it can and reports the rest

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

## How the run was taken

The wizard was served by `serve_salvage.py` in the gate repository at
`C:\codex\traktor-nml-tool-gate`, with only `pick_file_or_folder`
stubbed. The output path was typed, and the write lands in the gate's
own fixture directory, so this run writes a file and reads it back.

The viewport is `1280x900` at `devicePixelRatio: 2.5`.

The fixture is `salvage_fixture.py`, built for this run because the
reconstruct-conflict fixture holds none of the three conditions under
measurement. Two collections, four cases in five tracks:

- `2020\Jan` and `2021\Jan` - two playlists sharing a bare `NAME` in
  different folders, both empty in the collection being repaired.
- `dup.mp3` - a track the base collection holds **two** `ENTRY` elements
  for, which is base's own condition and nothing in this tool removes.
- `ghost.mp3` - a track **no** collection in the run holds an entry for,
  named by an entry in three playlists: one the run rebuilds, one the
  run leaves in place, and one the run imports whole. That is one per
  route a playlist takes to the output.
- `two.mp3` - one `ALBUM` read two ways, so the walk passes through the
  resolve step and the write reports an answer the operator chose.

The walk: fill in step 1, `Preview` - which refuses on the one conflict -
`Continue to resolve`, pick answer 2, `Continue to write`, `Write
collection...`, confirm.

The code under measurement is `79e287e` plus this record's own
correction.

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| Step 1, the collection being repaired | its own counts | `4 tracks`, `3 playlists`, `2 of them empty` | matches |
| Step 1, the older collection | what it can supply | `3 playlists with contents` | matches |
| Preview on a diverging pair | refuses, and says so | the step draws its refusal card | matches |
| The refusal's head | what stopped it, and that nothing was written | `Nothing was assembled yet` beside `NOTHING WRITTEN` | matches |
| The refusal's sentence, on a count of one | singular | `1 track is held differently by more than one collection, and the repair cannot be assembled until every one has an answer. Continue to resolve names each one and offers its answers.` | matches |
| The resolve tally, on a count of one | singular | `1 track carries more than one answer - 0 decided, 1 to go` | matches |
| The resolve tally after the pick | the same count, settled | `1 track carries more than one answer - 1 decided, 0 to go` | matches |
| Two playlists sharing a bare NAME | both rebuilt, neither refused | the run reports `errors= []` and `rebuilt= {'2020\Jan': 2, '2021\Jan': 1}` | matches |
| The write step, playlists filled | the run's own count | `2` | matches |
| The write step, entries added | the run's own count | `3` | matches |
| The write step, answers chosen | the count decided at step 3 | `1` | matches |
| The write step, playlists left empty | the run's own count | `0` | matches |
| The duplicated-track row | entries placed, and across how many playlists | `1`, `Across 1 playlist. Each is placed on the first of those copies, which is the one the merge points at too.` | matches |
| The dropped-entry row | entries, distinct tracks and playlists, each read off the run | `3`, `1 track across 3 playlists. Neither collection holds an entry for them, so the playlists keep everything else and lose these.` | matches |
| The write step, tracks in the collection | the count the output declares | `5` | matches |
| The confirmation's question | the count the first row carries | `Write 2 rebuilt playlists?` | matches |
| The write itself | the file the step described | `Written to ...\reconstruct-salvage\written.nml` | matches |
| The written file, declared count | agrees with its own elements | `COLLECTION ENTRIES="5"` against five `ENTRY` elements | matches |
| The written file, playlist paths | the four the run describes, at the lengths it describes | `{'2020\Jan': 2, '2021\Jan': 1, 'Kept': 1, 'Imported': 1}` | matches |
| The written file, dangling keys | none | `[]` | matches |
| The written file, the operator's pick | the record they named, in the bytes | `ALBUM TITLE="Source Album"`, against `Base Album` in the same run driven headless | matches |
| The written file, bare LF | base's own count | `0` | matches |
| Document scroll | none, either way | `scrollWidth` 1280 and `scrollHeight` 900 against a `1280x900` viewport | matches |

Every row above is read on the corrected page. The two defects this run
found are under "What this run found" rather than as verdict rows.

## What this run found

**The resolve tally disagreeing with the count it names.** The strip
above the conflict table read `1 tracks carry more than one answer - 0
decided, 1 to go` on a run whose collections diverge over one track,
which is the ordinary case on a pair that barely diverge. The refusal
sentence one step earlier had the singular right, so the two screens
describing one number disagreed about it. The sentence is
`conflict_model.resolve_tally_sentence` now, where its noun is read off
the count it follows and a guard holds both forms. This is the
seventeenth defect found on a running page rather than by a source-text
guard (DL-233).

**The write step describing a file that now exists as one that does
not.** After a confirmed write the toast reads `Written to ...`, and the
step behind it still reads `Before anything is written`, `NOTHING
WRITTEN YET` and `DOES NOT EXIST YET`. The step is not redrawn after the
write, so every sentence on it is the sentence it carried before.

This one is **recorded and not corrected**. Redrawing it is a line of
code; what it should then say is not settled, and the obvious redraw
makes the screen worse rather than better - the destination card would
read that the file exists while the head above it reads that nothing has
been written. `Write.dc.html` draws the state before a write and no
artboard draws the state after one, and DL-071 puts that in the design
before the screen. The next milestone on this page is where it belongs.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| Write step split | `Write.dc.html:27`'s content column beside a 400px detail rail | `grid-template-columns: minmax(0px, 1fr) 400px`, content column `604px` at `x=120`, rail `400px` at `x=744` | matches |
| Write step change list | `Write.dc.html`'s change list and totals | the same composition at six rows, the four the artboard draws plus the two a run reports only when it has something to report | matches |
| Resolve tally strip | `Resolve.dc.html`'s tally beside the bulk actions | the same strip, its sentence composed from the model rather than spelled on the page | matches |

The two conditional rows sit inside the artboard's change list rather
than beside it: the artboard draws the list, and how many rows a run
fills it with is the run's, not the drawing's. A row reading zero would
name a thing the run did not do, which is why neither is drawn on a run
that has none (DL-230, DL-232).

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The run was served with `native=False`. The three corrections under
measurement were found by an operator on the shipped `native=True` entry
point, and they are read here on the served page alone.

The written file is checked for the counts the write step promised - its
declared entry count against its own elements, its four playlist paths
with their lengths, that no key in it names a missing entry, and its
terminator counts - and not byte for byte against a baseline. This
fixture records no baseline: the run that would fix one is the run under
measurement.

The operator's own collections are not read here. The three corrections
were measured on them headlessly - a 684-playlist rebuild that had
refused over 21 entries naming 8 tracks - and this fixture is the
smallest pair that carries the same four conditions.

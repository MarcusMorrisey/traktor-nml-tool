# Served-page record: the write step reports the run it is about to write

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

## How the run was taken

The wizard was served by `serve_reconstruct.py` in the gate repository
at `C:\codex\traktor-nml-tool-gate`, with only `pick_file_or_folder`
stubbed. The output path was typed to a scratch directory outside both
repositories, so this run writes a file and reads it back.

The viewport is `1280x900`; the refusal card's own measurements were
taken at `devicePixelRatio: 2.5` and are marked.

This run repeats the walk an operator took on their own collection: fill
in step 1, `Preview` - which refuses, because the collections diverge -
`Continue to resolve`, settle every conflict, then `Continue to write`
**without previewing a second time**. That last step is what this
milestone corrects.

The code under measurement is `51d028f` plus this milestone's changes.

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| Preview on a diverging pair | refuses, and says so | the run reports `unresolved_conflicts` and the step draws its refusal | matches |
| The refusal's own card | a card, not text on the page | `.wizard-card` at `x=128 w=1024 h=110`, radius `8px`, bordered (`dpr: 2.5`) | matches |
| The refusal's head | what stopped it, and that nothing was written | `Nothing was assembled yet` beside `NOTHING WRITTEN` | matches |
| The refusal's sentence | the count and the step that settles it | `6 tracks are held differently by more than one collection, and the repair cannot be assembled until every one has an answer. Continue to resolve names each one and offers its answers.` | matches |
| The refusal's count | the run's own group count | `6`, against a resolve tally reading `6 tracks carry more than one answer` | matches |
| Resolve reachable on a refused run | yes - its rows are what the step settles | `Continue to resolve` walks to step 3 and lists the six | matches |
| Write from resolve, nothing previewed since | re-assembles first | step 4 reports `1` playlist filled, `7` entries added, `6` answers chosen, `0` left empty, `7` tracks in the collection | matches |
| Write with one answer undone | shut, and says why | `Continue to write` reads `disabled: true`, the note reads `1 still to decide. Writing stays closed until every one has an answer.` | matches |
| Write after an answer is changed | re-assembles again | the changed answer decided, step 4 reports `1`, `7`, `6`, `0` and `7` | matches |
| The confirmation's question | the count the first row carries | `Write 1 rebuilt playlist?` | matches |
| The write itself | the file the step described | `Written to ...\e2e\repaired.nml` | matches |
| The written file | what the step promised | `COLLECTION ENTRIES="7"`, seven `ENTRY` elements, playlist `Deep` at `ENTRIES="7"` | matches |
| Document scroll | none, either way | `scrollWidth` 1280 and `scrollHeight` 900 against a `1280x900` viewport | matches |

Every row above is read on the corrected page. What the same walk
reported before the correction is under "What this run corrected" rather
than as a verdict row: it was read on an operator's own collection, not
on this fixture, and a verdict row states what this run measured.

## What this run corrected

**The write step reporting a run that refused.** `reachable` read "a
result is held" as "a run assembled", and a refused run is a held result
carrying no output. An operator who answered all 34 conflicts on their
own collection and walked to step 4 was shown `Playlists filled again:
0`, `Entries added: 0`, `Tracks in the collection: 0` - and `Tracks
taking the values you chose: 34`, that one read off their decisions
rather than off any run. The step read as a file with nothing in it,
described by numbers from two different sources. `reachable` takes
whether the run produced an output as its own input now, and
`conflict_model.run_assembled` is where that is decided.

**The answers never reaching a run.** Nothing re-ran the assembly when
the conflicts were settled, so the answers reached a run only if the
operator knew to press `Preview` a second time. The walk into the write
step re-assembles where the held run reports something other than the
answers now given, which `conflict_model.run_is_current` decides by
comparing the resolutions the run was handed with the ones now held. A
decision made and undone back to where it started leaves the run
current, so the re-read is not paid for a change that was not made.

**The refusal state printed rather than composed.** It was two labels
drawn straight onto the page - `Nothing was written.` and a sentence -
with no card, no head and no account of what to do next, on the screen
most runs reach first. It is a card whose head says nothing was
assembled, whose sentence names the count and the step that answers it,
and which lists the run's own error tokens under it where the stop was
something other than a conflict.

This is the fourteenth, fifteenth and sixteenth defect found on a
running page rather than by a source-text guard, and the first two were
found by an operator on their own collection rather than by this gate:
the gate's own fixture walk had previewed a second time out of habit, so
the stale run never reached the write step (DL-227).

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| Preview refusal | no artboard draws this state | a `.wizard-card` at the content column's width, its head naming the stop and `NOTHING WRITTEN`, its body carrying the sentence and, where the run gave any, its reasons in a `.wizard-callout-warn` | matches |
| Write step contents | `Write.dc.html`'s change list and totals | the same composition, filled from a run that reports the answers now given | matches |

The refusal state is composed from the card, label and callout rules the
design set fixes, against no artboard of its own: `Preview.dc.html` draws
the state where a run assembled. What it composes is read here against
the rules those classes carry, and a screen for it is a design question
this record leaves open rather than answers.

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The run was served with `native=False`. The defect this record corrects
was found on the shipped `native=True` entry point, and the correction
is read here on the served page alone.

The written file is checked for the counts the write step promised - its
collection entry count, its entry elements and its one rebuilt playlist
- and not byte for byte against a baseline. `serve_reconstruct.py
--compare-baseline` is the check that does that, and it is not run here.

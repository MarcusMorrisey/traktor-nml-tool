# Served-page record: the write step after the write

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

## How the run was taken

The wizard was served by `serve_salvage.py` in the gate repository at
`C:\codex\traktor-nml-tool-gate`, over `fixture/reconstruct-salvage`,
with only `pick_file_or_folder` stubbed. The viewport is `1280x900`.

The walk: fill in step 1, `Preview` - which refuses on the fixture's one
conflict - `Continue to resolve`, settle it, `Continue to write`, read
the step, `Write collection...`, confirm, and read the step again
without leaving it. Then back to step 1, `Preview` a second time, and
forward to step 4 once more, to read what a run assembled after a write
leaves the step saying.

The code under measurement is `e741b4f` plus this milestone's changes.

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| The head, before the write | says nothing has been written | `Before anything is written` beside `NOTHING WRITTEN YET` | matches |
| The destination badge, before the write | the state of that path | `DOES NOT EXIST YET` | matches |
| The change list's head, before the write | future tense | `What the new file will hold` | matches |
| The confirmation's question | the count the first row carries | `Write 2 rebuilt playlists?` | matches |
| The head, after the write | says the file exists | `Written` beside `WRITTEN` | matches |
| The destination badge, after the write | the path was written | `WRITTEN` | matches |
| The change list's head, after the write | present tense | `What the new file holds` | matches |
| The change list itself, after the write | unchanged - a write changes the tense of the sentence above it, not what the run did | the same rows in the same order | matches |
| The originals card, after the write | still unmodified | each collection named, `NOT MODIFIED` beside it | matches |
| The toast | names the file written | `Written to ...\reconstruct-salvage\written.nml` | matches |
| The written file | what the step described | `COLLECTION ENTRIES="5"` against five `ENTRY` elements; `{'2020\Jan': 2, '2021\Jan': 1, 'Kept': 1, 'Imported': 1}`; no key naming a missing entry; bare LF `0` | matches |
| A run assembled after the write | puts the step back before its write | `Before anything is written`, `What the new file will hold` | matches |
| That run's destination badge | the path exists but this run did not write it | `ALREADY EXISTS`, not `WRITTEN` | matches |
| Document scroll | none, either way | `scrollWidth` 1280 and `scrollHeight` 900 against a `1280x900` viewport | matches |

## What this run corrected

**A step describing a file it had just written as one that did not
exist.** After a confirmed write the toast named the file and the step
behind it went on reading `Before anything is written`, `NOTHING WRITTEN
YET` and `DOES NOT EXIST YET`. The step was not redrawn, so every
sentence on it was the sentence it carried before the write. It was
found on a served page, recorded in
`docs/2026-09-15-reconstruct-salvage-browser-record.md` and left
standing there because what the step should say instead was a screen no
artboard draws (DL-234).

What it says instead is the smallest true thing. The step does not
become another screen: the operator is looking at the card they just
confirmed, and everything else on it is still true - the change list
described the file and now describes it, the originals are still
unmodified, and the note about opening it in Traktor is the next thing
to do rather than a thing to do later. Only the tense and the status
move, which is three strings the record derives and the page reads.

**A written state that outlived the run that earned it.** `written` is
not "a write happened": it is "this run wrote the path this field now
names". A path the operator edits after writing names a file this run
did not write, and a run assembled after a write produced bytes the file
on disk does not hold. Either one puts the step back before its write,
which is where it truly is. The second is read above as a verdict row.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| Write step, before the write | `Write.dc.html`'s head, destination card, change list and totals | the same composition, at the same classes | matches |
| Write step, after the write | no artboard draws this state | the same composition with three strings changed - head, head badge, change list head - and the destination badge reading `WRITTEN` | matches |

The state after a write is composed from the card, label and badge rules
the design set already fixes, against no artboard of its own. It is the
same structure as the state before the write by intent rather than by
omission: a second screen for it would put the operator somewhere new at
the moment they most need to recognise where they are. A drawn artboard
for it is a design question this record leaves open rather than answers,
and until one exists the composition above is the thing to read against.

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The run was served with `native=False`. The defect this record corrects
was found on the shipped `native=True` entry point, and the correction
is read here on the served page alone.

**The confirmation was dispatched from script.** The Browser pane would
not deliver a click into the `q-dialog`: the dialog measured `0x0` until
a screenshot forced a paint, and clicks at the measured coordinates
landed on the backdrop, twice walking the wizard back a step instead of
confirming. The footer control that opens the dialog was clicked
normally; the button inside it was clicked through
`element.click()`. What that leaves unread is whether a real pointer
reaches that button on this pane - not what the handler does, which is
what this record measures, and which ran the same either way. The same
pane artefact is recorded in
`docs/2026-09-07-reconstruct-stale-run-browser-record.md`.

The written file is checked for the counts the write step promised and
not byte for byte against a baseline; this fixture records none.

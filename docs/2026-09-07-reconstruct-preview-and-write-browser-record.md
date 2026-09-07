# Served-page record: the reconstruct page's Preview and Write steps

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboards that draw it.

## How the run was taken

The wizard was served by `serve_reconstruct.py` in the gate repository
at `C:\codex\traktor-nml-tool-gate`, which imports this tree's own
`build_wizard` and substitutes one thing a browser cannot drive:
`pick_file_or_folder` opens a native dialog, so it hands back
`fixture/reconstruct-conflict/base.nml`, `source.nml` and
`source-two.nml` on its three file calls and the fixture directory on a
directory call. Nothing else is stubbed; every rule, class and
dimension read below is the one `theme.py` emits, every sentence is the
one `reconstruct_report.py` derives, and every number is the one the run
reported.

The viewport is `1280x900`. Every reading below is at
`devicePixelRatio: 1` except the confirmation dialog's, which was taken
after the pane changed ratio and is marked.

The page was driven through its own controls: the three chooser buttons
and the output folder, `Preview`, `Continue to resolve`, `All
source.nml` to settle the six groups, back to `Set up`, `Preview` again
- which is the run that assembles, since the first refuses on the six
undecided groups - then `Continue to resolve`, `Continue to write`, and
the write step's own `Write collection...`.

The fixture reaches this page with one empty playlist, `Deep`, which the
sources fill with seven entries, and six tracks held more than one way:
five over `album`, one over `bitrate`.

The code under measurement is `d5d6360` plus this milestone's own
changes, including the two corrections described under "What this run
corrected".

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| Header band height | `56px` | `56px` at `y=0`, full `1280px` | matches |
| Footer band height | `64px` | `64px` at `y=836`, full `1280px` | matches |
| Middle between the bands | `780px` at the full width | `x=0 y=56 w=1280 h=780` | matches |
| Document scroll, preview step | none | `scrollHeight` 900 against `innerHeight` 900 | matches |
| Document scroll, write step | none | `scrollHeight` 900 against `innerHeight` 900 | matches |
| Step rail, preview step | the content column, Preview current | `x=128 w=1024`; `Set up` check-marked, `wizard-step-current` on `2 Preview` alone | matches |
| Step rail, write step | three done, Write current | `Set up`, `Preview` and `Resolve` check-marked, `wizard-step-current` on `4 Write` alone | matches |
| Preview split tracks | the content column beside a `400px` rail | `grid-template-columns: 604px 400px`, `column-gap: 16px` at `gap: 20px` | matches |
| Preview split geometry | one row, two columns, top-aligned | split `x=128 w=1024`, columns `604px` at `x=128` and `400px` at `x=752`, both from `y=129`, heights `236` and `222` | matches |
| Write split tracks | the same two tracks | `604px 400px` | matches |
| Write split geometry | one row, two columns, top-aligned | split `x=128 w=1024 h=602`, columns `604` at `x=128` and `400` at `x=752`, heights `602` and `405` | matches |
| Card border and radius | `1px` at `8px` | `1px solid rgb(42, 46, 50)`, radius `8px`, on every card in both splits | matches |
| The head's count of filled playlists | both numbers, read off the run | `1 OF 1 EMPTY PLAYLISTS` beside one listed playlist | matches |
| The head's label type | mono 600 at `11px` | `600 11px/11px 'IBM Plex Mono'`, `rgb(142, 151, 158)` | matches |
| A listed playlist row | name at the left, count at the right | `Deep` and `7 entries` on `491.19px 64.81px`, row `x=144 w=572 h=30` | matches |
| The listed count's type | mono 600 at `12px`, muted | `600 12px/12px 'IBM Plex Mono'`, `rgb(165, 173, 180)` | matches |
| The entries total | the summed count | `Entries that would be added` and `7`, box `x=128 w=604 h=43` | matches |
| The total's own surface | tinted panel, `6px`, bordered | `rgb(31, 34, 37)`, radius `6px`, `1px solid rgb(60, 66, 72)` | matches |
| The total's amount type | mono 600 at `15px` | `600 15px/15px 'IBM Plex Mono'` | matches |
| The conflict note, every group decided | agrees with the resolve step | `Every one of the 6 tracks held differently by more than one collection has an answer. Step 3 is where those answers are changed.` beside a tally reading `6 decided, 0 to go` | matches |
| The conflict note, one group undone | agrees with the resolve step | `1 track is held differently by more than one collection with no answer yet. It has to be decided before anything can be written. That is step 3.` beside a tally reading `5 decided, 1 to go` | matches |
| The warn callout's tint | the review hue | `1px solid rgb(90, 78, 42)` on `rgb(31, 29, 20)`, box `x=128 w=604` | matches |
| The info callout's tint | the action hue | `1px solid rgb(47, 90, 114)` on `rgb(18, 34, 43)`, box `x=752 w=400` | matches |
| The output path panel | the path in mono on the page ground | `1px solid rgb(60, 66, 72)`, radius `7px`, ground `rgb(15, 17, 19)`, `500 13px 'IBM Plex Mono'`, box `x=144 w=572 h=95` | matches |
| The output path itself | the run's own output path | `C:\codex\traktor-nml-tool-gate\fixture\reconstruct-conflict\base-reconnected.nml` | matches |
| The path's badge | what the path is | `ALREADY EXISTS`, the fixture's own file | matches |
| Every original's badge | one per collection read | three `NOT MODIFIED` chips at `x=1028`, one per input | matches |
| A badge's own surface | found-hue chip | `1px solid rgb(44, 84, 73)` on `rgb(18, 33, 29)`, ink `rgb(168, 216, 206)` | matches |
| The change rows | one per change, count at the right | four rows at `x=144 w=572 h=51`, tracks `548px 9px`, each ruled off at `1px solid rgb(35, 39, 43)` | matches |
| The change rows' counts | the run's own numbers | `1` filled, `7` entries added, `6` answers chosen, `0` left empty | matches |
| The counts' tone | added in the found hue, untouched muted | the first three `rgb(79, 211, 186)`, the fourth `rgb(165, 173, 180)`, all right-aligned | matches |
| The change detail's type | `11px` under its change | `11px` | matches |
| The collection total | the count the output declares | `Tracks in the collection the new file holds` and `7` | matches |
| The write step's footer note | names the control it stands beside | `Write collection asks before it writes the file the preview assembled.` beside `WRITE COLLECTION...` | matches |
| The write step's controls | back and the asking control | `BACK TO RESOLVE` and `WRITE COLLECTION...`, and no other visible control | matches |
| The confirmation opens | a panel over a backdrop | `q-dialog__backdrop` at `rgba(0, 0, 0, 0.4)` over the full viewport, the panel `369x193` centred at `640,450` | matches |
| The confirmation's heading | the count the first row carries | `Write 1 rebuilt playlist?` beside a row reading `1` | matches |
| The confirmation's assurances | three, each one line | `19px` each: the new file, no collection touched, Traktor unchanged | matches |
| The confirmation's actions | cancel then write, at the right | `CANCEL` `84x32` at `x=559`, `WRITE COLLECTION` `156x32` at `x=652` | matches |
| The confirmation's own surface | raised panel at `8px` | `rgb(31, 34, 37)`, radius `8px`, padding `16px`, gap `12px`, border declared `1px` and resolved `0.8px` at `dpr: 2.5` | matches |
| Cancel closes it | the step stands, nothing written | no backdrop, no panel, step rail still on `4 Write`, the fixture directory's files unmodified | matches |

The confirmation's border reads a declaration and a resolved value that
differ by the browser's rounding of a `1px` border to a device pixel at
`dpr: 2.5`, which is `2.5` device pixels rounded to `2` and reported as
`0.8` CSS pixels. Every other reading above was taken at `dpr: 1`, where
the same border resolves to `1px`.

## What this run corrected

Two defects were read on the served page that the source-text guards
passed, and both were fixed and re-read before the readings above were
taken.

**The preview contradicting the step it points at.** With every group
decided at step 3, the preview's note still read `6 tracks are held
differently by more than one collection. Each one has to be decided
before anything can be written. That is step 3.` beside a resolve step
whose tally read `6 decided, 0 to go`. The count was the group count,
which never changes, rather than the count still outstanding, which is
what the sentence claims to be about. It is `resolve_gate(...)
.outstanding` now, the same value the resolve step's own footer prints,
and the panel is redrawn on entry to the step rather than once, so an
answer given at step 3 reaches the sentence that names it. The panel
carries the settled sentence in the other direction too, which is what
the second conflict-note reading above is.

**The footer naming a control the step does not carry.** The write
step's note read `Write output writes the file the preview assembled.`
beside a control labelled `Write collection...`. It names the control
that stands there.

This is the eighth and ninth defect the served-page gate has found that
the source-text guards did not.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| Preview column model | `Preview.dc.html:27`'s main at `1fr 400px`, two `.col` | `.wizard-step-split` at `604px 400px`, two `.wizard-step-column`, top-aligned | matches |
| Preview listing | `.pl` rows of name and count inside a scrolling card | `.wizard-list-row` at `minmax(0,1fr) auto`, name ellipsised, count in mono, inside `.wizard-scroll` | matches |
| Preview totals strip | `.tot`, label at the left and the summed count at the right | `.wizard-total` at `604px`, tinted and bordered, its amount in mono at `15px` | matches |
| Preview callouts | `.note.warn` and `.note.info`, one tint each | `.wizard-callout-warn` at the review hue and `.wizard-callout-info` at the action hue, both `1px` bordered | matches |
| Write column model | `Write.dc.html:27`'s main at `1fr 400px`, two `.col` | `.wizard-step-split` at `604px 400px`, two `.wizard-step-column` | matches |
| Write destination panel | `.dest`, the path in mono over the page ground with a `.badge` under it | `.wizard-destination` at radius `7px` on the ground, `.wizard-destination-path` in mono, `.wizard-badge` below | matches |
| Write change list | `.cr` rows of change, detail and count, ruled off | four `.wizard-change-row`, each a change and its detail at the left and its count at the right, ruled at `1px` | matches |
| Write originals list | `.cr` rows of path and `Not modified` | one `.wizard-list-row` per input, path in mono, `.wizard-badge` at the right | matches |
| Write confirmation | `.dlg`, a raised panel of heading, three assurances and two actions | `.wizard-dialog` over a backdrop, `.wizard-dialog-list` of three `.wizard-dialog-item`, `.wizard-dialog-actions` right-aligned | matches |

Every structure this record reads is composed. None of the nine carries
an entry under "Composition not built", and none is added by this run:
the three entries that stand there are read against the reconnect
wizard's own artboards on `/reconnect`, which composes none of them
(DL-201).

## What this run does not establish

**The keyboard ring is not walked.** The pane's keyboard channel does
not reach the page - `Tab` pressed with focus seated on a named control
leaves `document.activeElement` where it was - so no ring was walked and
none is reported. That reading is not taken for this version:
accessibility is out of scope for it, and DL-197 says so. Announcements
are unread for the same reason.

**The write itself is not exercised.** The run stops at the
confirmation, which was opened and cancelled. Nothing was written, and
the fixture directory's files carry the timestamps they had before the
run.

**The artboards' icon marks are not built.** `Preview.dc.html` and
`Write.dc.html` draw an SVG mark in each callout and beside each change
row. No page in this tree renders an icon, so neither step does, and the
change row's grid is the two tracks it needs rather than the three the
artboard draws. This is a divergence from the design set of the kind
DL-088 covers, not a structure standing unbuilt.

One reading was taken and discarded. The confirmation panel measured
`0x0` at the viewport's centre with its backdrop up and its
`q-transition--scale-enter-from` class still on, three times in a row
across two waits over a second long. It is the pane not painting rather
than a panel that does not open: a screenshot forces a paint, and the
same panel measured `369x193` immediately after one. It is recorded
here because it was nearly written above as a dialog that opens to
nothing.

The run was served with `native=False`; the shipped entry point runs
`native=True` and builds the same chrome. The listing's truncation at
nine named playlists and a tenth standing for the rest is not read here:
this fixture fills one playlist. `LISTED_PLAYLISTS` and the division
either side of it are held in
`tests/test_gui_preview_and_write_composition.py`.

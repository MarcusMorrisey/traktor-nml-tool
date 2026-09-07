# Served-page record: the reconstruct page's four steps and its Resolve step

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

## How the run was taken

The wizard was served by `serve_reconstruct.py` in the gate repository
at `C:\codex\traktor-nml-tool-gate`, which imports this tree's own
`build_wizard` and substitutes one thing a browser cannot drive:
`pick_file_or_folder` opens a native dialog, so it hands back
`fixture/reconstruct-conflict/base.nml`, `source.nml` and
`source-two.nml` on its three file calls and the fixture directory on a
directory call. Nothing else is stubbed; every rule, class and
dimension read below is the one `theme.py` emits and the one `app.py`
names.

The viewport is `1280x900` at `devicePixelRatio: 1`. The page was
driven through its own controls - the three chooser buttons, `Preview`,
then `Continue to resolve` - to the Resolve step, which the fixture
reaches with six conflicting groups: five over `album`, one over
`bitrate`, four of them holding three answers and two holding two.

The code under measurement is `1c8724b` plus the three corrections this
run produced, which are described under "What this run corrected".

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| Header band height | `56px` | `56px` at `y=0`, full `1280px` | matches |
| Footer band height | `64px` | `64px` at `y=836`, full `1280px` | matches |
| Middle between the bands | `780px` at the full width | `x=0 y=56 w=1280 h=780` | matches |
| Document scroll | none | `scrollHeight` not above `innerHeight` | matches |
| Step rail position | the content column, not the band | `x=128 w=1024`, centred in `.wizard-content-width` | matches |
| Step rail contents | four steps, two done, Resolve current | `Set up` and `Preview` check-marked, `3 Resolve`, `4 Write`; `wizard-step-current` on Resolve alone | matches |
| Split tracks | the content column beside a `400px` rail | `grid-template-columns: 608px 400px`, `column-gap: 16px` | matches |
| Split geometry | table left, rail right, one row | table `x=128 w=608`, rail `x=752 w=400`, both `h=561.98` | matches |
| Detail rail width | `400px` | `400px` | matches |
| Detail rail border | a bordered panel at `8px` | `1px solid rgb(47, 90, 114)`, radius `8px` | matches |
| Detail rail bands | head, body, foot | `84.8px`, `374.17px`, `101.02px`, in that order | matches |
| Conflict grid tracks | `minmax(0, 1fr) 108px 72px 164px 120px` | `142px 108px 72px 164px 120px` | matches |
| Header row on the body's tracks | one set of tracks | every one of the six rows resolves the header's own track string | matches |
| Column alignment | each heading over its column | header and row cells share `x` at `129`, `271`, `379`, `451`, `615` | matches |
| Header row cells | five headings | `TRACK`, `WHAT DIFFERS`, `ANSWERS`, `HELD BY`, `DECISION` | matches |
| Track cell containment | inside its own track | `overflow: hidden`, `text-overflow: ellipsis`, `white-space: nowrap`; every row's cell ends at or before the next column's left edge | matches |
| One control per distinct answer | three answers on the focused group | `BASE 320`, `SOURCE.NML 128`, `SOURCE-TWO.NML 192` | matches |
| The rail's head names the file | the focused row's identity | `C:/:Music/:one.mp3` | matches |
| The rail's head counts its collections | three, matching the row beside it | `3 collections hold this file with different values.` | matches |
| One bulk action per input | three collections read | `ALL BASE`, `ALL SOURCE.NML`, `ALL SOURCE-TWO.NML` | matches |
| The tally | the count and the remainder | `6 tracks carry more than one answer - 0 decided, 6 to go` | matches |
| Footer note inset | `x=24` | `x=24` | matches |
| Footer note, gate shut | the outstanding count | `6 still to decide. Writing stays closed until every one has an answer.` | matches |
| Advancing control, gate shut | disabled | `Continue to write` reads `disabled: true` | matches |
| Bulk action settles its groups | all six decided | `6 decided, 0 to go`; every row's decision cell reads `source.nml` | matches |
| Footer note, gate open | agrees with the control | `Every track has an answer. Writing is open.` | matches |
| Advancing control, gate open | enabled | `Continue to write` reads `disabled: false` | matches |
| Undoing one decision reshuts the gate | back to one outstanding | `5 decided, 1 to go`, the note names one, the control disabled again | matches |
| Answer marker border | `1.5px` declared | declared `1.5px`; resolved `1px` at `dpr: 1` and `1.2px` at `dpr: 2.5` | matches |

The marker row records a declaration and a resolved value that differ
by the browser's rounding of a sub-pixel border to a device pixel, read
twice at two device ratios to establish that it is rounding rather than
a rule. The declaration is what `theme.py` emits.

## What this run corrected

Three defects were read on the served page that the source-text guards
passed, and each was fixed and re-read before the readings above were
taken.

**The track column at `54px`.** The conflict grid's four fixed tracks
totalled `552px`, which is what `Resolve.dc.html` draws for a table
`816px` wide - the artboard's `main` spans the frame at a `24px` inset.
The built page centres its content at `.wizard-content-width`, so the
table is `608px` and the whole `208px` difference came out of the one
flexible track, leaving `54px` for a path measuring `131px` to `283px`.
The cell carried no `.trk` treatment either, so the text neither
wrapped nor shortened: it crossed `WHAT DIFFERS` and `ANSWERS` and was
read over their values. The four fixed tracks are `108px`, `72px`,
`164px` and `120px`, each sized to the widest value its column holds
plus the cell inset, which leaves the track column `142px`; and
`.wizard-conflict-track` carries the artboard's `overflow: hidden`,
`text-overflow: ellipsis` and `white-space: nowrap`, so a path longer
than the track shortens inside it. The full path stands in the rail's
head, which is what makes shortening it readable rather than lossy.
`Resolve.dc.html` was retracked first and `theme.py` follows it
(DL-071).

**The rail's head naming a count it had not read.** The head read
`Two collections hold this file with different values` beside a row
whose `HELD BY` cell named three and whose body offered three answers.
The count is read off the group's candidates.

**The footer's sentence contradicting the control beside it.** With
every group decided, the note read `0 still to decide. Writing stays
closed until every one has an answer.` while `Continue to write` was
enabled two hundred pixels to its right. `ResolveGate`'s own docstring
names this failure - "a control the operator can press over a sentence
saying they cannot" - and the class exists to prevent it, but the
sentence was formatted at the call site rather than read off the gate.
It is `ResolveGate.note`, which is where `all_decided` already lives,
so the sentence and the control are one fact.

This is the fifth, sixth and seventh defect the served-page gate has
found that the source-text guards did not, and the first is of the kind
DL-189 describes: every rule was correct read alone, and what was wrong
was what the browser resolved from two of them together.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| Step scaffold | `.steprail` as `main`'s first row, one `.st` per step, `.st.now` on the current one | `.wizard-step-rail` at the content column's own width, four `.wizard-step`, `wizard-step-done` on the two passed and `wizard-step-current` on Resolve | matches |
| Resolve column model | `main`'s `.split` at `1fr 400px` | `.wizard-resolve-split` at `608px 400px`, the table left and the rail right | matches |
| Resolve table geometry | `.gr`'s five tracks under a `.th` header row | one track string on the header row and on all six body rows, each heading over its column | matches |
| Resolve detail rail | `.det`, a bordered `400px` panel of head, body and foot | `.wizard-detail-rail` at `400px`, bordered, its three bands in order | matches |
| Resolve answer control | one `.cand` per distinct answer, `.rad` marking the chosen | one `.wizard-answer` per distinct answer, `wizard-answer-chosen` on the picked one alone | matches |
| Bulk strip | `.fbar`, the tally then one action per collection | `.wizard-tally` then three `.wizard-bulk-strip` actions, one per input | matches |
| Gated footer | the outstanding count beside a shut advancing control | the note at `x=24` and `Continue to write` disabled, both read off one gate, in both directions | matches |

Every structure this record reads is composed. None of the seven
carries an entry under "Composition not built", and none is added by
this run: the three entries that stand there are read against the
reconnect wizard's own artboards on `/reconnect`, which composes none
of them (DL-201).

## What this run does not establish

**The keyboard ring is not re-walked.** Moving the advancing controls
into per-step footer groups changes the tab order. It is not read here:
the pane's keyboard channel did not reach the page - `Tab` was pressed
with focus seated on a named control and `document.activeElement` did
not move - so no ring was walked and none is reported.
`docs/2026-09-06-wizard-focus-order-browser-record.md` reads the ring on
the Set up step before the step regions existed, and the reading it
holds does not cover this page. That reading is not taken for this
version: accessibility is out of scope for it, and DL-197 says so.

Announcements are not read here for the same reason: nothing was driven
by key.

The run was served with `native=False`; the shipped entry point runs
`native=True` and builds the same chrome. Nothing here exercises the
write itself - the run stops at the gate opening.

The four fixed tracks are sized against the values this fixture holds.
A collection whose `HELD BY` list is longer wraps that cell rather than
widening it, which the `61px` row height carries; a longer path
shortens in the track cell and stands in full in the rail's head.

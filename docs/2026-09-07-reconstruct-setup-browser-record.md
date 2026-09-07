# Served-page record: the reconstruct page's Set up step

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
directory call. Nothing else is stubbed; every rule, class and dimension
read below is the one `theme.py` emits, every count is the one
`collection_summary.py` derives from the parsed file, and every refusal
is the one `conflict_model.py` answers.

The viewport is `1280x900`. Readings are at `devicePixelRatio: 1` except
the right column's, taken after the pane changed ratio, which are marked.

The step was driven through its own controls: `Choose file...`, `Add
collection...` twice, `Choose folder...`, then the output path typed to
a colliding value and back, `Preview`, `Back to set up`, and `Remove` on
the first source.

The fixture's base holds six tracks in one playlist, which is empty;
each source holds one playlist with contents.

The code under measurement is `161b1aa` plus this milestone's own
changes, including the four corrections described under "What this run
corrected".

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| Header band height | `56px` | `56px` at `y=0`, full `1280px` | matches |
| Footer band height | `64px` | `64px` at `y=836`, full `1280px` | matches |
| Middle between the bands | `780px` at the full width | `x=0 y=56 w=1280 h=780` | matches |
| Document scroll, down | none | `scrollHeight` 900 against `innerHeight` 900 | matches |
| Document scroll, sideways | none | `scrollWidth` 1280 against `innerWidth` 1280, and the middle's own `scrollWidth` 1280 | matches |
| Step rail | the content column, Set up current | `x=128 w=1024`; `wizard-step-current` on `1 Set up` alone | matches |
| Split tracks | the content column beside a `400px` rail | `grid-template-columns: 604px 400px` at `gap: 20px` | matches |
| Split geometry | the split at the column's own width | `x=128 w=1024`, columns `604` at `x=128` and `400` at `x=752`, both from `y=129`, top-aligned | matches |
| The four cards | one column, the column's width | four cards at `x=128 w=604`, heights `143`, `212`, `143`, `139` | matches |
| Card border and radius | `1px` at `8px` | `1px solid rgb(42, 46, 50)`, radius `8px` | matches |
| The repair card's own label | `READ ONLY` in the head | `600 11px/11px 'IBM Plex Mono'`, `rgb(142, 151, 158)` | matches |
| The source card's own control | in the head, not the body | `ADD COLLECTION...` `142x32` at `x=575`, inside the card head | matches |
| A chosen path's field | a bordered box on the page ground | `1px solid rgb(60, 66, 72)` on `rgb(15, 17, 19)`, radius `6px`, height `36px` | matches |
| Every field row | the row's own width, not the path's | five rows at `x=144 w=572`, the card's width less its inset | matches |
| A path inside its field | shortened, not spilling | `12.5px 'IBM Plex Mono'`, `text-overflow: ellipsis`, `white-space: nowrap`; every field ends inside its row | matches |
| The repair card, nothing chosen | says so | `No collection selected`, and no `Remove` control | matches |
| The repair card, chosen | the file's own counts | `6 tracks`, `1 playlist`, `1 of them empty`, `this file is never modified` | matches |
| The count's agreement | singular against one | `1 playlist`, not `1 playlists` | matches |
| The phrases' separators | an upright rule between them | three `1x16` dividers at `rgb(60, 66, 72)`, at `x=195`, `261`, `369` | matches |
| The empty count's ink | the review hue | `rgb(245, 217, 107)` at weight `600` on `1 of them empty` alone | matches |
| The source list, nothing added | says so | `No collection added` | matches |
| A source's row | path at the left, what it supplies at the right | `1 playlist with contents` in mono `11.5px`, `rgb(142, 151, 158)`, ending at the field's inner right edge | matches |
| A source's own count | singular against one | `1 playlist with contents`, not `1 playlists` | matches |
| Removing one source | the other stays, named | `source.nml` removed, the row reading `source-two.nml` stands | matches |
| The output row, nothing chosen | says what is missing | `No output path chosen. Choose a folder, or type the path the new collection is written to.` | matches |
| The output row, a folder chosen | the path the write takes | `C:\codex\traktor-nml-tool-gate\fixture\reconstruct-conflict\base-reconnected.nml` | matches |
| The output row, a new file | says so | `A new file. It does not name any collection above.` | matches |
| The output row, naming an input | refuses in the line, not only at the write | `The output path names a collection this run reads. Choose a different name, so nothing you gave it is overwritten.` at `rgb(245, 217, 107)` | matches |
| The conflict choice | inside its own field | the select in a `572px` field, its value reading `Ask me - stop and show every conflicting track` | matches |
| What happens next | three steps, numbered by the step each names | `2 The repair is previewed`, `3 You resolve the disagreements`, `4 You confirm the write`, in an `ol` at `gap: 11px` | matches |
| A next step's marker | a `20px` circle in mono | `20x20`, radius `50%`, `600 11px/11px 'IBM Plex Mono'`, `rgb(142, 151, 158)`, bordered (`dpr: 2.5`) | matches |
| A next step's title | its own line above the sentence | `display: block`, `600 13px 'IBM Plex Sans'`, `rgb(232, 235, 237)` | matches |
| The rail's callout | the action hue, the rail's width | `1px solid rgb(47, 90, 114)` on `rgb(18, 34, 43)`, `x=752 w=400` (`dpr: 2.5`) | matches |
| Preview from this step | reaches step 2 | the rail marks `2 Preview` current and the preview step reports the run | matches |

The two rows marked `dpr: 2.5` record a `1px` declaration resolving to
`0.8px`, which is `2.5` device pixels rounded to `2`. Every other
reading was taken at `dpr: 1`, where the same borders resolve to `1px`.

## What this run corrected

Four defects were read on the served page that the source-text guards
passed, and all four were fixed and re-read before the readings above
were taken.

**The page scrolling sideways.** The split's flexible track was a bare
`1fr`, whose automatic minimum is its own content, and its content is
collection paths that do not wrap. The track resolved to `879px` inside
a `1024px` column, the middle's `scrollWidth` read `1420` against a
`1280` viewport, and the rail was pushed off the right edge. The track
is `minmax(0, 1fr)` now, the column and the field row carry
`min-width: 0`, and the four artboards on canvas page 3 are retracked
first (DL-071). It is the same rule the resolve step's split carries, so
both were corrected.

**The split taking its content's width.** With the overflow fixed the
split measured `962px` inside its `1024px` column: it stands in a
framework column that packs its items to the start, so a grid with no
width of its own sizes to its content and its rail leaves the column's
right edge. The split takes the column's width.

**A source's row taking its path's width.** The source list is a second
framework column of the same kind, so each row sized to its own path and
measured `727px` inside a `604px` card, spilling over the rail beside
it. The field row takes its row's width.

**Two sentences disagreeing with what they described.** The count of
playlists read `1 playlists`, and the line under an output path that had
not been chosen read `A new file. It does not name any collection
above.` - a claim about a file the page had not been given. The counts
agree their nouns, and the line says what is missing until a path is
named.

This is the tenth, eleventh, twelfth and thirteenth defect the served-page
gate has found that the source-text guards did not. The first three are
of the kind DL-189 describes: every rule was correct read alone, and what
was wrong was what the browser resolved from two of them together.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| Set up column model | `Reconstruct.dc.html:27`'s main at `minmax(0,1fr) 400px`, two `.col` | `.wizard-step-split` at `604px 400px` at the column's own width, two `.wizard-step-column` | matches |
| Set up card set | four cards - the collection to repair, the sources, the output, the conflict choice | four `.wizard-card` in the left column, in that order | matches |
| Path field | `.field`, a bordered inset box holding the path in mono with its control beside it | `.wizard-field` inside `.wizard-field-row`, `36px`, the path in `.wizard-field-value` shortened inside it | matches |
| Collection meta line | `.meta`, phrases about the file separated by `.bar`, the empty count emphasised | `.wizard-meta` of the summary's own phrases, `.wizard-meta-divider` between them, `.wizard-meta-count` on the empty count | matches |
| Source row | the path in its field with what it supplies read from the field's right edge, its own Remove beside it | `.wizard-field` holding `.wizard-field-value` and `.wizard-field-note`, the control outside the field | matches |
| Next steps list | `.steps`, one numbered row per step, a bold title over its sentence | `.wizard-next-steps` as an `ol`, one `.wizard-next-step` per `collection_summary.NEXT_STEPS` row, `.wizard-next-step-marker` and `.wizard-next-step-title` | matches |
| Set up callout | `.note.info` under the list | `.wizard-callout-info` at the rail's width | matches |

Every structure this record reads is composed. None of the seven carries
an entry under "Composition not built", and none is added by this run:
the three entries that stand there are read against the reconnect
wizard's own artboards on `/reconnect`, which composes none of them
(DL-201).

## What this run does not establish

**The keyboard ring is not walked.** The pane's keyboard channel does
not reach the page - `Tab` pressed with focus seated on a named control
leaves `document.activeElement` where it was - so no ring was walked and
none is reported. This is the reading DL-197 asks for and it is still
owed, as the two records before this one also say. Announcements are
unread for the same reason.

**The artboard's icon marks are not built.** `Reconstruct.dc.html` draws
an SVG file mark inside each field and one in the callout. No page in
this tree renders an icon, so this step does not either. It is a
divergence from the design set of the kind DL-088 covers, not a
structure standing unbuilt.

**The conflict choice's own chevron is the framework's.** The artboard
draws a chevron inside the field at its right edge; the select renders
Quasar's own dropdown arrow in that position. The field around it is the
artboard's.

**A long path is read shortened, not in full.** No control on this step
shows a path that does not fit its field. The fixture's paths shorten at
`279px` inside a `480px` field, and the full path stands nowhere on this
step. The write step's own destination panel prints it in full, which is
where a path is read whole.

The run was served with `native=False`; the shipped entry point runs
`native=True` and builds the same chrome. Nothing here writes: the run
stops after Preview, and the fixture directory's files carry the
timestamps they had before it.

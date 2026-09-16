# Served-page record: the resolve step's detail rail

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

## How the run was taken

The wizard was served by `serve_reconstruct.py` in the gate repository
at `C:\codex\traktor-nml-tool-gate`, over
`fixture/reconstruct-conflict`, with base, source and source-two given
as the three collections and only `pick_file_or_folder` stubbed. The
viewport is `1280x900`.

The walk: fill in step 1 with the three collections and an output path,
`Preview` - which refuses on the fixture's six conflicts - `Continue to
resolve`, and read the rail over the focused row, which is
`C:/:Music/:one.mp3`. Then pick answer 2 by clicking a field row, read
the rail again, and undo.

The code under measurement is `5c08f96` plus this milestone's changes.

The fixture is the one the gate's `reconstruct_fixture.py` writes, run
before this pass: its conflicting entry carries Traktor's own units and
a field that agrees between two of the three answers, so the page
exercises the unit formatting and a mark that discriminates
(ref: DL-251, DL-256).

Every field the rail draws is a tracked attribute the group's records
carry, the agreeing ones included, so the screen hides no field: attrs
never holds an attribute the answers agree on, and the agreeing values
ride beside it (ref: DL-242, DL-244, DL-245).

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| The rail head | names the file once | `C:/:Music/:one.mp3`, and one occurrence of that string in the whole rail | matches |
| The head's sentence | a count read off the group | `3 collections hold this file with different values. Pick the one that supplies them.` | matches |
| Answer 1's field rows | one row per tracked attribute the group carries, in `_TRACKED_ATTRS` order | `ARTIST`, `TITLE`, `ALBUM`, `FILESIZE`, `PLAYTIME_FLOAT`, `BITRATE` | matches |
| The field keys | the NML attribute names, uppercase | the six keys above, `text-transform: uppercase` on each | matches |
| FILESIZE | one division by 1024 off a kilobyte count | `16.0 MB` beside `16384`, on all three answers | matches |
| BITRATE, answer 1 | one division by 1000 off bits per second | `320 kbps` beside `320000` | matches |
| BITRATE, answers 2 and 3 | the two other answers' own values | `128 kbps` beside `128000`, `192 kbps` beside `192000` | matches |
| PLAYTIME_FLOAT | minutes and zero-padded seconds | `1:39` beside `99.6`, on all three answers | matches |
| ARTIST, TITLE | the raw value alone, no formatted companion | `A` and `One`, third cell empty on both rows of all three answers | matches |
| The marks | on ALBUM and BITRATE alone, on all three answers | `ALBUM` and `BITRATE` carry one; `ARTIST`, `TITLE`, `FILESIZE`, `PLAYTIME_FLOAT` carry none - six marks over three answers | matches |
| ALBUM across the answers | answers 2 and 3 agree, answer 1 does not - the mark stands on a row two answers share | answer 1 `` (empty), answers 2 and 3 `Reissue`, and the row is marked on all three | matches |
| The holders line | under the fields, naming the collections | `held by base`, `held by source.nml`, `held by source-two.nml`, each on its own line below the last field row | matches |
| The control | the field block picks the answer | a pointer click on answer 2's `BITRATE` row set the group's decision to `source.nml` and the progress line to `6 tracks carry more than one answer - 1 decided, 5 to go` | matches |
| The chosen marker after a pick | answer 2 alone | answer 2 `wizard-answer wizard-answer-chosen`, `aria-label="Chosen"`, dot present; answers 1 and 3 `wizard-answer`, `aria-label="Not chosen"`, no dot | matches |
| Undo | puts the group back | `6 tracks carry more than one answer - 0 decided, 6 to go`, no answer chosen | matches |
| No value colouring | no value painted by its magnitude | every FILESIZE cell `rgb(210, 216, 220)`, the same colour as every other value cell on all three answers | matches |
| The rail width | 400px | `400` | matches |
| The field rows' alignment | the three tracks start at one x down the rail | every row `60px 166.8px 82px` at left `794`, width `324.8`, on all eighteen rows | matches |
| The marker against the record | beside the first field row rather than the middle of the block | `8.8px` below the card's own top edge on all three answers | matches |
| The rail's own scroll | the fields make the rail taller; whether it scrolls and whether the footer stays put | the rail measures `1163.89px` in a `900px` viewport, its own `overflow-y` is `hidden` and it does not scroll; `.wizard-middle` scrolls instead (`780px` client against `1340px` scroll), and the rail's foot travels with it from `1247.5` to `687.1` | matches |
| Document scroll | none | `scrollWidth` 1280 and `scrollHeight` 900 against a `1280x900` viewport | matches |

## What this run establishes

**A rail that reads as a record.** Each answer stands as six labelled
rows - the attribute name, what its value means, and the raw string the
written file carries - so two answers differing in one attribute are
told apart by reading the row they differ on rather than by comparing
two runs of text. On this group the three answers agree on `ARTIST`,
`TITLE`, `FILESIZE` and `PLAYTIME_FLOAT` and disagree on `ALBUM` and
`BITRATE`, and the rail draws all six on each answer with the mark on
the two.

**A mark that discriminates.** `ALBUM` is the row that carries the
point: answers 2 and 3 hold `Reissue` and answer 1 holds nothing, so
the mark stands on a row two of the three answers share. Six marks over
three answers, not eighteen and not two: the rule is the membership
test in the group's divergent set and the page reads it back.

**Units the collection actually writes.** The fixture's conflicting
entry carries `FILESIZE="16384"` in kilobytes, `BITRATE` in bits per
second and `PLAYTIME_FLOAT="99.6"` in seconds, and the rail reads them
`16.0 MB`, `320/128/192 kbps` and `1:39`. The raw string stands beside
each one, so what the written file will hold is on screen next to what
it means.

**The block the operator points at is the record.** A pointer click
landing on answer 2's `BITRATE` row decided the group to `source.nml`:
the field block is the control, and the `held by ...` line under it is
the informational line it is.

**Two framework shortfalls the served page found.** Quasar wraps a
button's children in its own `.q-btn__content`, which is a centred,
wrapping row. The column and the left alignment the field block
declares govern that wrapper rather than the rows inside it, so the
rows laid out at their content's widths - read at `165.9px`, `180.2px`,
`158px`, `203.6px`, `183.3px` and `209.1px`, each centred on its own
wrap line and starting at a different x inside a 400px rail - the
values sat at the centre of their tracks, and the `held by` line shared
the last field row's wrap line instead of standing under the fields.
The card heights read `221.46`, `234.48` and `263.49` for three answers
of the same shape. The wrapper carries the column, the nowrap and the
left alignment the block declares, and the eighteen rows above read
`60px 166.8px 82px` at one x.

The second is the answer card's own cross-axis alignment. The answer
beside the chosen marker is a block of six rows, and a centred marker
sat `103px` below the card's top edge, level with no row it names. It
is read above at `8.8px`, which is the card's own padding: the marker
heads the record it marks. `design/reconnect-wizard/Resolve.dc.html`'s
`.cand` carries the same declaration, so the screen is built to the
design rather than against it (DL-071).

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| The rail body | `Resolve.dc.html`'s `.det-b`: answer groups only, no "The file" group | three `.wizard-answer-group` children and one `.wizard-note`; no `Path` row anywhere in the body | matches |
| An answer's field rows | `.cmpf`'s three tracks - key, value, raw - with `.k` mono uppercase | `60px 166.8px 82px` on every row; the key cell at left `794` width `60`, the raw cell at left `1036.8` width `82` right-aligned; the key `11px`, weight `500`, `uppercase`, letter-spacing `0.55px` | matches |
| The difference mark | a 5px dot in the key cell of a divergent row | `5px` by `5px`, `border-radius: 50%`, `rgb(86, 180, 233)`, inside the key cell | matches |
| The holders line | `.cand .m` under the fields | `11px`, `rgb(142, 151, 158)`, `padding-top: 5px`, below the last field row on all three answers | matches |
| The chosen marker | `.rad` and its dot, unchanged by this work | `15px` by `15px`, `border-radius: 50%`, border `rgb(86, 180, 233)` on the chosen answer; the dot `8px` by `8px`, `rgb(86, 180, 233)` | matches |
| The answer card's cross-axis alignment | `.cand` aligns its items to the start | `align-items: flex-start`, marker `8.8px` below the card's top edge | matches |

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The run was served with `native=False`, on `serve_reconstruct.py`'s
port. The shipped `native=True` entry point is not read here.

**The mono typeface is not judged here.** `IBM Plex Mono` is not loaded
in this pane - `document.fonts.check('11px "IBM Plex Mono"')` reads
`false` - and the field key's own label carries a `font-mono` class
whose computed `font-family` reads the generic
`ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation
Mono", "Courier New", monospace` stack rather than the
`"IBM Plex Mono", ui-monospace, Consolas, monospace` that
`.wizard-answer-field-key` declares. What typeface the key would paint
in with the font present is not established by this run. The structural
verdicts above are taken on the size, weight, case, letter-spacing and
colour, which are read, and not on the family, which is not.

**Sub-pixel widths are read at this pane's device pixel ratio.**
`devicePixelRatio` is `2.5`, and the chosen marker's `1.5px` border
reads back `1.2px` and the field row's `1px` bottom border reads back
`0.8px` - both the nearest device pixel divided back. The declared
widths are guarded in `tests/test_gui_resolve_sheet.py`; what this run
reads is what the pane rasterised them to.

**No pointer-click artefact arose on this run.** The known pane
artefact recorded in
`docs/2026-09-15-write-step-after-the-write-browser-record.md` and
`docs/2026-09-07-reconstruct-stale-run-browser-record.md` - that the
Browser pane will not deliver a real pointer click into a `q-dialog` -
did not apply: the resolve step's rail holds no dialog, and every click
this record reports, the pick included, was a real pointer click
delivered at the element's measured position. No reading here was taken
after an `element.click()`.

The gate's own `--headless` expectation table for this fixture is a
separate surface from the page: it lives in the gate's Python, it names
the values this fixture carries, and nothing in this record is taken
from that run.

The rail was read over the first conflicting group alone. The five
other groups the fixture carries are not read here.

A group held by a single collection is not reachable on this fixture,
so the head's singular reading of the holding count is not read on the
page. It is guarded in `tests/test_gui_wording.py`.

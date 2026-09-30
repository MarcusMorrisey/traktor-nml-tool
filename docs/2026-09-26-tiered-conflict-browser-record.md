# Served-page record: what the tier settles, on the Preview step

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

The tier settles a group whose divergence is measured-only and puts an
editorial divergence to the operator (DL-325). Two surfaces say so on the
Preview step: a sentence naming how many groups the rule answered, and a
card listing the settled groups whose gap passes the 1% band (DL-330).
`design/reconnect-wizard/Preview.dc.html` draws both - the sentence at
`:151`-`154` and the listing at `:86`-`92` with its rows at `:179`-`181`.

## How the run was taken

The wizard was served by a scratch script modelled on
`serve_reconstruct.py` in the gate repository at
`C:\codex\traktor-nml-tool-gate`, with `native=False` on a free port and
only `pick_file_or_folder` stubbed: its first file call returns the
case's `base.nml` and every later file call its `source.nml`. The gate
repository was read and not written. The viewport read back as
`innerWidth` `1280` and `innerHeight` `900`, and `devicePixelRatio` read
`2.5`, which is why a `1px` border resolves to `0.8px` in
`getComputedStyle`.

Three collection pairs were built for the run, each a base whose one
playlist has lost its contents and a source that still holds them, over
the same LOCATIONs, so every pair is an identity group and only the
disagreeing attribute varies:

- **outliers** - five groups: two whose FILESIZE the two collections
  measure far apart (`17564` against `69203`, and `5384` against
  `30950`), two that drift by one kilobyte (`8123`/`8124`,
  `9001`/`9002`), one the two agree on entirely.
- **quiet** - the kilobyte drifts and the agreeing pair only.
- **editorial** - one group differing in ARTIST alone, every measured
  value equal.

The pairs were read through `assemble_output` before the browser ran, so
what the page draws is contrasted with what the model reports rather than
assumed. That reading: **outliers** `settled_rows` `4`, of which `2` are
outlying, `conflict_rows` `0`, errors `[]`, `reconstructed_playlists`
`{'Set': 5}`; **quiet** `settled_rows` `2`, outlying `0`, `conflict_rows`
`0`; **editorial** `settled_rows` `0`, `conflict_rows` `1`. The two
outlying gaps read `0.7462` and `0.8260`.

On each case the base `Choose file...` was clicked once,
`Add collection...` once, the source `Choose file...` once, and
`Preview` once; the readings were taken three seconds after that click.

The readings are taken on `cf363ab` plus this plan's M-001 through
M-004: the tier in `metadata_tier.py` and `splice.py`, the printed
settled count and outlier lines in `splice_cmd.py`, the settled sentence
and outlier listing in `gui/reconstruct_report.py`, and the Preview
surfaces in `Preview.dc.html`, `theme.py` and `app.py` (ref: DL-325,
DL-329, DL-330, DL-331). The servers were stopped after the run.

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| The settled sentence: it names the run's own count | `4`, the settled rows the model reported | `4 tracks are measured differently by the two collections - file size, length or bitrate. Both numbers are Traktor's own, so there is nothing to decide. Each carries the values of the record the output keeps.` | matches |
| The settled sentence: its panel | the artboard's info note, not the warn one | `class` `wizard-callout wizard-callout-info` | matches |
| The settled sentence on the quiet case | `2`, and no listing beside it | `2 tracks are measured differently by the two collections - ...`, with `0` elements carrying any `wizard-outlier` class | matches |
| The listing's head | the count of outlying rows, not of settled groups | card title `The 2 measured far apart` against `4` settled | matches |
| The listing's rows | one per outlying group, two here | `2` `.wizard-outlier-row` elements | matches |
| A row's five cells | track, attribute, values, winner, gap | `C:/:Music/:deadly.stem.m4a`, `FILESIZE`, `17564 (17.2 MB) -> 69203 (67.6 MB)`, `base: C:/:Music/:deadly.stem.m4a`, `74.6%` | matches |
| The second row | the wider gap, low value first | `C:/:Music/:believe.stem.m4a`, `FILESIZE`, `5384 (5.3 MB) -> 30950 (30.2 MB)`, `base: C:/:Music/:believe.stem.m4a`, `82.6%` | matches |
| The gap reads the model's own figure | `0.7462` and `0.8260` as percentages | `74.6%` and `82.6%` | matches |
| The winner names a record | a collection and a primary key, never a token | `base: C:/:Music/:deadly.stem.m4a` on both rows | matches |
| The row's grid | four stacked areas against one gap column | `display` `grid`, `grid-template-columns` `313.4px 39px`, `grid-template-areas` `"name gap" "key gap" "values gap" "winner gap"` | matches |
| The row's box | `2px 12px` gaps inside `8px 2px` padding at `12.5px` | `gap` `2px 12px`, `padding` `8px 2px`, `font-size` `12.5px`, box `368.4` by `84.1` | matches |
| The separator | between rows, never under the last | first row `border-top` `0px` and `border-bottom` `0px`; last row `border-top` `0.8px rgb(35, 39, 43)` and `border-bottom` `0px` | matches |
| The attribute cell | `600 11px` mono at `.04em` in `#8E979E` | `font` `600 11px / 11px "IBM Plex Mono", ui-monospace, Consolas, monospace`, `letter-spacing` `0.44px`, `color` `rgb(142, 151, 158)` | matches |
| The values cell | `500 12px/1.4` mono in `#A5ADB4`, breakable | `font` `500 12px / 16.8px "IBM Plex Mono", ...`, `color` `rgb(165, 173, 180)`, `word-break` `break-all` | matches |
| The winner cell | `500 11px/1.4` mono in `#8E979E`, clipped | `font` `500 11px / 15.4px "IBM Plex Mono", ...`, `color` `rgb(142, 151, 158)`, `text-overflow` `ellipsis` | matches |
| The gap cell | `600 13px` mono in `#F5D96B`, at the row's right | `font` `600 13px / 13px "IBM Plex Mono", ...`, `color` `rgb(245, 217, 107)`, `2` from the row's right edge | matches |
| The listing's note | the run's own wording under the rows | `These are read, not decided. The output carries the record named beside each one; Traktor rewrites its own measurement the next time it analyses the file.` | matches |
| The quiet case: no listing | the sentence alone | visible card titles `What would be rebuilt`, `What this run did`; no outlier card, `0` outlier elements, no note | matches |
| The editorial case: no settled surface | neither sentence nor listing | `0` elements carrying any `wizard-outlier` class, `0` visible callouts, no sentence naming `measured differently` | matches |
| The editorial case: the operator is still asked | the run refuses and names the count | one card, `Nothing was assembled yet` / `NOTHING WRITTEN` / `1 track is held differently by more than one collection, and the repair cannot be assembled until every one has an answer. Continue to resolve names each one and offers its answers.` | matches |
| The document | unscrolled | `document.scrollingElement.scrollTop` `0`, `scrollHeight` `900` | matches |

## What this run establishes

**The rule's work is on the screen, not silent.** A run the tier settled
four groups for says so in its own sentence, and the count is the model's:
`4` on the outliers case, `2` on the quiet one, and no sentence at all
where the rule settled nothing.

**The listing counts what is listed.** Its head read `The 2 measured far
apart` while four groups were settled, so the head is the outlying count
and not the settled one - the two numbers are different on this run,
which is what makes the reading discriminating.

**An outlier names a record, a gap and both values.** Each row read the
track's identity key, `FILESIZE`, both raw values with their formatted
forms, the winning record as `base: <primary key>`, and the gap as a
percentage of the larger value - so a reader can see what differs, by how
much, and which number the output keeps.

**The screen says nothing where the rule did nothing.** On the editorial
case neither surface exists in the DOM, and the run still refuses and
still names its one outstanding conflict, so the tier removed no
question the operator is owed.

**The values keep Traktor's units.** `17564 (17.2 MB)` is FILESIZE read
as kilobytes, the unit a Traktor collection writes, so the formatted form
divides once.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| The settled sentence | `Preview.dc.html:151`-`154`'s `<div class="note info">` | a `wizard-callout wizard-callout-info` element holding `record.settled_sentence`, composed in `gui/reconstruct_report.py` and read off the run's settled rows | matches |
| The outlier listing | `:86`-`92`'s `.ol`: a grid of `minmax(0,1fr) auto` over the areas `"nm g" "k g" "v g" "w g"`, `gap:2px 12px`, `padding:8px 2px`, `font-size:12.5px` | `.wizard-outlier-row` declaring the same grid, gaps, padding and size from `theme.py`'s own tokens | matches |
| The listing's separator | `:87`'s `.ol + .ol{border-top:1px solid #23272B}` | `.wizard-outlier-row + .wizard-outlier-row` declaring `border-top: 1px solid` `SURFACE_5`, with no `:last-child` rule standing in the sheet | matches |
| The row's five cells | `:88`-`92`'s `.nm`, `.k`, `.v`, `.w`, `.g` | `.wizard-outlier-name`, `-key`, `-values`, `-winner`, `-gap`, each carrying that cell's own type, colour and clipping | matches |
| A row's content | `:179`-`181`'s three rows, each a track, an attribute, two values, a winner and a percentage | one `outlier_row` per `record.outliers` entry, every string composed in `gui/reconstruct_report.py` and none in `app.py` | matches |

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The shipped `native=True` entry point is not read here.

**No PLAYTIME_FLOAT or BITRATE outlier was read on the page.** Both of
the run's outlying groups diverge on FILESIZE. The artboard draws one of
each at `:179`-`181`, and `metadata_tier.outlier_attrs` reads the three
measured attributes the same way, but only the FILESIZE row was measured
in a browser - which matters most for PLAYTIME_FLOAT, the one whose wrong
value a reader would see in Traktor as a wrong track length.

**No row was read whose track or winner is long enough to clip.** The
`.wizard-outlier-name` and `.wizard-outlier-winner` cells declare
`text-overflow: ellipsis`; every key on this fixture fits.

**The listing was not read at another width or another pixel ratio.** The
`400` card and the `313.4px` name column are what `1280` leaves, and the
`0.8px` border is what `devicePixelRatio` `2.5` snaps a `1px`
declaration to.

**A run mixing a settled group with an outstanding conflict was not
read.** The editorial case refuses before assembling, so what the two
surfaces do beside a refusal card is unread.

**The rule's effect on the written file was not read here.** What a
settled group writes is the CLI's reading, not this one.

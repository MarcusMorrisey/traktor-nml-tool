# Served-page record: what the tier settles, on the Preview step

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

The tier answers one case - one file described twice - and puts every
other divergence to the operator (DL-325). Two surfaces say what it
answered: a sentence naming how many groups the rule settled, and a card
listing the readings whose gap passes the 1% band, widest first, capped
with a remainder row (DL-330, DL-331). Both stand on the assembled
screen, on the refusal, and on a run that rebuilt no playlist.
`design/reconnect-wizard/Preview.dc.html` draws the sentence at
`:164`-`167` and the listing at `:86`-`92`, its remainder rule at `:103`-`105`, with its rows at `:192`-`194`
and its remainder at `:195`.

## How the run was taken

The wizard was served by a scratch script modelled on
`serve_reconstruct.py` in the gate repository at
`C:\codex\traktor-nml-tool-gate`, with `native=False` on a free port and
only `pick_file_or_folder` stubbed: its first file call returns the
case's `base.nml` and every later file call its `source.nml`. The gate
repository was read and not written. The viewport read back as
`innerWidth` `1280` and `innerHeight` `900`, and `devicePixelRatio` read
`2.5`.

Four collection pairs were built for the run, each a base whose one
playlist has lost its contents and a source that still holds them, over
the same LOCATIONs, so every pair is an identity group whose members
share one primary key and hold base's record - the three preconditions
the rule requires (DL-325):

- **outliers** - nine groups: six whose FILESIZE the two collections
  measure far apart, two that drift by one kilobyte, one the two agree on
  entirely.
- **quiet** - the kilobyte drifts and the agreeing pair only.
- **editorial** - one group differing in ARTIST alone.
- **refusal** - one group differing in ARTIST alone beside one the rule
  answers, so the run refuses while the rule still settles something.

Each pair was read through `assemble_output` before the browser ran, so
what the page draws is contrasted with what the model reports rather than
assumed: **outliers** `settled_rows` 8, outlying 6, readings 6,
`conflict_rows` 0, errors `[]`; **quiet** 2 settled, 0 outlying;
**editorial** 0 settled, 1 conflict, `errors` `['unresolved_conflicts']`;
**refusal** 1 settled, 1 outlying, 1 conflict, the same error. The two
widest gaps read `0.8260` and `0.7462`.

On each case the base `Choose file...` was clicked once,
`Add collection...` once, the source `Choose file...` once, and
`Preview` once; the readings were taken three seconds after that click.

The readings are taken on `90f1b2f` plus the fixes a max-effort review of
this work called for: the rule's three preconditions, the exact-rational
band, a reading naming the value the output keeps, the track named off
the winning record, the capped and ordered listing, the reading on the
refusal screen, and the artboard's swallowed `.ol` rule (DL-325,
DL-327..DL-331, DL-336, DL-337). The servers were stopped after the run.

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| The settled sentence: it names the run's own count | `8`, the count the run's stats carry | `8 tracks are measured differently by the two collections - file size, length or bitrate. Both numbers are Traktor's own, so there is nothing to decide. Each carries the values of the record the output keeps.` | matches |
| The settled sentence: its panel | the artboard's info note, not the warn one | `class` `wizard-callout wizard-callout-info` | matches |
| The listing's head | every reading the run made, not the rows drawn | card title `The 6 measured far apart` over three rows, against `8` settled | matches |
| The listing's rows | capped at three | `3` `.wizard-outlier-row` elements for six readings | matches |
| The listing's order | widest gap first | `82.6%`, `74.6%`, `74.5%` in that order | matches |
| The remainder row | what the cap leaves, and how wide those are | `and 3 more measured far apart` / `74.5% and narrower` | matches |
| A row: the track | the artboard's `artist - title`, not a LOCATION | `Koen Groeneveld - You Gotta Believe`, `Eat Static - Deadly Amphibian`, `DharMhar - Ethernaut (Anthill Rmx)` | matches |
| A row: its five cells | track, attribute, values, winner, gap | `Eat Static - Deadly Amphibian`, `FILESIZE`, `17564 (17.2 MB) -> 69203 (67.6 MB)`, `base: C:/:Music/:deadly.stem.m4a`, `74.6%` | matches |
| A row: the value the output keeps | the winning record's own number, named first | `17564 (17.2 MB)` leads, the value it is read against follows; the winner cell names `base` | matches |
| The gap reads the model's own figure | `0.8260` and `0.7462` as percentages | `82.6%` and `74.6%` | matches |
| The listing's note | the run's own wording under the rows | `These are read, not decided. The output carries the record named beside each one; Traktor rewrites its own measurement the next time it analyses the file.` | matches |
| The refusal screen: the sentence | the reading stands beside the refusal | `1 track is measured differently by the two collections - ... It carries the values of the record the output keeps.` | matches |
| The refusal screen: its count reads singular | `track is` and `It carries`, off `wording.plural` | `1 track is`, `It carries` | matches |
| The refusal screen: the listing | the same card, headed for one reading | card `The one measured far apart` holding `Eat Static - Deadly Amphibian ... 74.6%`, no remainder row | matches |
| The refusal screen: the run still refuses | the refusal card stands above the reading | `Nothing was assembled yet` / `NOTHING WRITTEN` / `1 track is held differently by more than one collection, and the repair cannot be assembled until every one has an answer.` | matches |
| The quiet case | the sentence alone | `2 tracks are measured differently ...`; `0` elements carrying any `wizard-outlier` class; visible card titles `What would be rebuilt`, `What this run did` | matches |
| The editorial case | neither surface, the refusal alone | `0` visible callouts, `0` outlier elements, no `measured differently` anywhere in the page text, one card `Nothing was assembled yet` | matches |

## What this run establishes

**The head counts every reading and the rows are capped.** Six readings
gave a head of `The 6 measured far apart`, three rows and a remainder
reading `and 3 more measured far apart`, so the count and the rows are
one division of one list and a run with thousands of readings draws four
rows rather than thousands.

**The listing is ordered by what it exists to surface.** The three drawn
rows are the three widest gaps in descending order, so the reading a
wrong track length would produce stands at the top rather than at an
arbitrary offset.

**A row names a track the way the design draws it.** `Koen Groeneveld -
You Gotta Believe` stands where the path stood, read off the winning
record, and the winner cell still carries `base: <primary key>`.

**A reading names the number the output keeps.** `17564 (17.2 MB)` is the
winning record's own FILESIZE and leads the pair, so the operator reads
what the file will say rather than the group's extremes.

**The refusal screen says what the rule answered.** A run that refuses on
one editorial divergence draws its refusal card and, beside it, the
sentence and the listing for the group the rule settled - the same run
the CLI prints a `settled_outlier` line for.

**The screen says nothing where the rule did nothing.** On the editorial
case neither surface exists in the DOM and no page text names a measured
difference, while the run still refuses and names its one outstanding
conflict.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| The settled sentence | `Preview.dc.html:164`-`167`'s `<div class="note info">` | a `wizard-callout wizard-callout-info` element holding `record.settled_sentence`, composed in `gui/reconstruct_report.py` off the run's stats and settled rows | matches |
| The outlier listing | `:86`-`92`'s `.ol`: a grid of `minmax(0,1fr) auto` over the areas `"nm g" "k g" "v g" "w g"`, `gap:2px 12px`, `padding:8px 2px`, `font-size:12.5px` | `.wizard-outlier-row` declaring the same grid, gaps, padding and size from `theme.py`'s own tokens | matches |
| The listing's separator | `:87`'s `.ol + .ol{border-top:1px solid #23272B}` | `.wizard-outlier-row + .wizard-outlier-row` declaring `border-top: 1px solid` `SURFACE_5`, with no `:last-child` rule in the sheet | matches |
| The remainder row | `:103`-`105`'s `.olr` and its two faint cells | `.wizard-outlier-remainder` with its name and gap cells, built from `record.outlier_remainder` | matches |
| A row's five cells | `:88`-`92`'s `.nm`, `.k`, `.v`, `.w`, `.g` | `.wizard-outlier-name`, `-key`, `-values`, `-winner`, `-gap`, each carrying that cell's own type, colour and clipping | matches |
| A row's content | `:192`-`194`'s three rows, each a track, an attribute, two values, a winner and a percentage | one `outlier_row` per listed reading, every string composed in `gui/reconstruct_report.py` and none in `app.py` | matches |

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The shipped `native=True` entry point is not read here.

**No PLAYTIME_FLOAT or BITRATE reading was drawn.** Every reading on
these pairs is a FILESIZE one. `metadata_tier.outlier_attrs` reads the
three measured attributes the same way and the artboard draws one of each
at `:192`-`194`, but only FILESIZE was measured in a browser - which
matters most for PLAYTIME_FLOAT, the attribute whose wrong value shows in
Traktor as a wrong track length.

**No listing longer than six readings was drawn.** The cap and the
remainder are read at six; a run with thousands of readings draws the
same four rows by construction, and that construction is guarded rather
than measured here.

**No row was read whose track or winner is long enough to clip.** Both
cells declare `text-overflow: ellipsis`; every track on these pairs fits.

**The listing was not read at another width or another pixel ratio.**

**The rule's refusal to settle is read only through what the screen
draws.** That a group spanning two LOCATIONs, a group without base's
record, or a group whose measured value reads as no finite number is a
conflict rather than a settled row is established by the suite and by
CLI runs, not by this page.

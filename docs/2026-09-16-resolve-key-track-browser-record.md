# Served-page record: the resolve rail's key track

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

## How the run was taken

The wizard was served by a scratch script modelled on
`serve_reconstruct.py` in the gate repository at
`C:\codex\traktor-nml-tool-gate`, with `native=False` on a free port
(`60344`) and only `pick_file_or_folder` stubbed, over a copy of that
repository's `fixture/reconstruct-conflict` taken into the session's
scratch directory. The gate repository was read and not written. The
viewport is `1280x900`.

The copy differs from the gate's fixture in one entry: `source-two.nml`'s
`one.mp3` carries `PLAYTIME_FLOAT="372.4"`, `FILESIZE="20480"` and an
`ALBUM` title of `Reissue - The Complete Deluxe Anniversary Edition
Remastered From The Original Tapes`. The gate's own `one.mp3` group
agrees on playtime, so without the change no group marks
`PLAYTIME_FLOAT`; with it, `one.mp3` marks `PLAYTIME_FLOAT` and
`FILESIZE`, `two.mp3` leaves both unmarked, and one value is long enough
to overflow its track.

The walk: step 1 with base, source and source-two and the fixture folder
as output, `Preview`, `Continue to resolve`, and read the rail over
`C:/:Music/:one.mp3`. Then a pointer click on `two.mp3`'s `Choose...`
moved the rail, which was read again, and a click on `one.mp3`'s
`Choose...` moved it back for the long-value reading.

The code under measurement is `3354ec1` plus this change: the key track
at `111px` (ref: DL-298).

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| The key typeface | IBM Plex Mono loaded, so the widths below are its widths | `document.fonts.check('11px "IBM Plex Mono"')` `true`; key and label `font-family` `"IBM Plex Mono", ui-monospace, Consolas, monospace`; `letter-spacing` `0.55px` | matches |
| The field rows' tracks | `111px 1fr 82px` | `111px 115.8px 82px` on all eighteen rows over `one.mp3` and all eighteen over `two.mp3` | matches |
| PLAYTIME_FLOAT, marked | whole, right edge inside its track | `one.mp3`, all three answers: label text `100.1px` wide from `804` to `904.1`, key cell `794` to `905`, `scrollWidth` 111 against `clientWidth` 111 | matches |
| PLAYTIME_FLOAT, unmarked | whole, right edge inside its track | `two.mp3`, all three answers: text `100.1px` from `794` to `894.1`, key cell right `905`, `scrollWidth` 111 against `clientWidth` 111 | matches |
| FILESIZE, marked | whole, right edge inside its track | `one.mp3`: text `57.2px` from `804` to `861.2` on all three answers | matches |
| FILESIZE, unmarked | whole, right edge inside its track | `two.mp3`: text `57.2px` from `794` to `851.2` on all three answers | matches |
| BITRATE, marked and unmarked | whole, right edge inside its track | `50.05px`: `804` to `854.05` marked on `one.mp3`, `794` to `844.05` unmarked on `two.mp3` | matches |
| ALBUM, marked | whole, right edge inside its track | `35.75px` from `804` to `839.75` on both groups, all answers | matches |
| ARTIST, TITLE, unmarked | whole, right edge inside their track | `42.9px` to `836.9` and `35.75px` to `829.75` on both groups | matches |
| No key past its track | every key's right edge at or before `905` | the furthest is PLAYTIME_FLOAT marked at `904.1`; no key cell's `scrollWidth` exceeds its `clientWidth` on any of the thirty-six rows | matches |
| The value column | what is left in a 400px rail | `115.8px`, left `913` right `1028.8`, raw cell left `1036.8` | matches |
| A long value | truncates with the ellipsis, does not overflow | answer 3's ALBUM on `one.mp3`: `scrollWidth` 486 against `clientWidth` 116, `overflow-x: hidden`, `text-overflow: ellipsis`, `white-space: nowrap`; the cell's right edge `1028.8` stays before the raw cell | matches |
| The rail's own horizontal scroll | none | `scrollWidth` 398 against `clientWidth` 398, width `400` | matches |
| Document scroll | none | `scrollWidth` 1280 and `scrollHeight` 900 against a `1280x900` viewport, over both groups | matches |

## What this run establishes

**The arithmetic held.** The derivation in `theme.py` puts one key
character at `0.6em` of advance plus `0.05em` of spacing, `7.15px` at
11px, and the longest label, PLAYTIME_FLOAT, at `100.1px`; the page read
`100.1px` for it with the face loaded. FILESIZE, `57.2px`, is eight of
the same. With the `5px` mark and `5px` gap the marked PLAYTIME_FLOAT
ends at `904.1`, `0.9px` inside the `111px` track, and the marked
FILESIZE at `67.2px` from the cell's left, which the earlier `60px`
track could not hold either.

**The tradeoff is the value column.** The rail's row is `324.8px`
wide either way; the value track goes from `166.8px` to `115.8px`. A
value longer than that is clipped with an ellipsis in its own cell and
does not reach the raw column.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| An answer's field rows | `Resolve.dc.html:90`'s `.cmpf`, `111px 1fr 82px` | `111px 115.8px 82px` on every row | matches |
| The longest label | the amended artboard's PLAYTIME_FLOAT row with its `.d` mark | PLAYTIME_FLOAT drawn whole with its `5px` mark inside the key track | matches |
| The value cell | `.cmpf .v`: `overflow:hidden; text-overflow:ellipsis; white-space:nowrap` | the same three declarations computed on the value cell | matches |

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The shipped `native=True` entry point is not read here.

**The fixture is not the gate's.** The marked PLAYTIME_FLOAT and
FILESIZE rows and the long ALBUM value exist only in the scratch copy
described above; the gate's own fixture produces neither a marked
PLAYTIME_FLOAT nor a marked FILESIZE, and this run did not write it.

**A marked ARTIST or TITLE is not read.** No group in the fixture
differs on either, so those two keys are read unmarked only. Both are
shorter than FILESIZE, so the marked widths are not in question, but
they are not measured.

**The ellipsis glyph is judged from computed style and the scroll
widths, not from pixels.** The one screenshot the pane returned shows
answers 1 and 2 above the fold with PLAYTIME_FLOAT clear of its value;
answer 3's ALBUM row sits below it and was not photographed.

**The 60px state was not served.** The overlap this change fixes is
read from the derivation and the guard's failure recorded in
`tests/test_gui_resolve_sheet.py`, not from a served page at `60px`.

The four other conflicting groups are not read here.

**Sub-pixel widths are read at this pane's device pixel ratio.**
`devicePixelRatio` is `2.5`.

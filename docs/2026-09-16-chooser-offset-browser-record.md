# Served-page record: the chooser buttons' vertical centre

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

## How the run was taken

The wizard was served by a scratch script modelled on `serve_w002.py` in
the gate repository at `C:\codex\traktor-nml-tool-gate`, with
`native=False` on a free port (`8763`) and only `pick_file_or_folder`
stubbed, here to return `None`, because every reading below is taken at
load and no chooser was clicked. The gate repository was read and not
written. The viewport is `1280x900`.

Each route was read at load: `/`, `/reconnect` and `/build-playlist`.
For every button whose label starts `Choose`, the run read the button's
bounding top and height, its computed `margin-top` and `margin-bottom`,
its parent row's class, computed `align-items`, top and height, the
bounding centre and height of each sibling in that row, the distance
from the row's bottom edge to the top of the row's next sibling, and the
height of the element holding the row.

The before readings were taken on the tree at `5c6e965` before any edit,
with `theme.py` copied aside first. The after readings are `5c6e965`
plus this change: the rule cancelling `.wizard-control`'s bottom margin
inside `wizard-path-row`, `wizard-field-row` and
`buildplaylist-input-row` (ref: DL-301). The server was stopped and
restarted between the two passes, and stopped after the second.

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| `/reconnect`, `Choose collection file...`, before | centred on its path | row `wizard-path-row`, `align-items` `center`, height `40.02`; button `margin-top` `0px`, `margin-bottom` `8px`, height `32.02`, centre `245.24`; path label centre `249.23` (height `21.75`); button `3.99` above | differs |
| `/reconnect`, `Choose output folder...`, before | centred on its path | row `wizard-path-row`, `center`, height `56`; button `0px`/`8px`, height `32.02`, centre `663.55`; path input centre `667.56` (height `56`); button `4.01` above | differs |
| `/`, `Choose file...`, before | centred on its path | row `wizard-field-row`, `center`, height `40.02`; button `0px`/`8px`, height `32.02`, centre `202.85`; `wizard-field` centre `206.84` (height `36`); button `3.99` above | differs |
| `/`, `Choose folder...`, before | centred on its path | row `wizard-field-row`, `center`, height `40.02`; button `0px`/`8px`, centre `499.23`; `wizard-field` centre `503.22` (height `36`); button `3.99` above | differs |
| `/build-playlist`, Base collection `Choose file...`, before | centred on its path | row `buildplaylist-input-row`, `center`, height `40.02`; button `0px`/`8px`, height `32.02`, centre `227.45`; path label centre `231.44` (height `21.75`); button `3.99` above | differs |
| `/build-playlist`, Input `Choose file...` and `Choose folder...`, before | centred on their path | one `buildplaylist-input-row`, `center`, height `40.02`; each button `0px`/`8px`, centre `302.46`; path label centre `306.45`; each button `3.99` above | differs |
| `/build-playlist`, Output folder `Choose folder...`, before | centred on its path | row `buildplaylist-input-row`, `center`, height `40.02`; button `0px`/`8px`, centre `547.79`; path label centre `551.78`; button `3.99` above | differs |
| `/reconnect`, `Choose collection file...`, after | centred on its path | row `center`, height `32.01`; button `0px`/`0px`, height `32.01`, centre `244.86`; path label centre `244.86`; offset `0` | matches |
| `/reconnect`, `Choose output folder...`, after | centred on its path | row `center`, height `56`; button `0px`/`0px`, centre `659.2`; path input centre `659.2`; offset `0` | matches |
| `/`, `Choose file...`, after | centred on its path | row `center`, height `36`; button `0px`/`0px`, height `32.02`, centre `204.84`; `wizard-field` centre `204.84`; offset `0` | matches |
| `/`, `Choose folder...`, after | centred on its path | row `center`, height `36`; button `0px`/`0px`, centre `497.2`; `wizard-field` centre `497.2`; offset `0` | matches |
| `/build-playlist`, Base collection `Choose file...`, after | centred on its path | row `center`, height `32.02`; button `0px`/`0px`, centre `227.45`; path label centre `227.44`; offset `0.01` | matches |
| `/build-playlist`, Input `Choose file...` and `Choose folder...`, after | centred on their path | row `center`, height `32.02`; each button `0px`/`0px`, centre `294.46`; path label centre `294.45`; offset `0.01` | matches |
| `/build-playlist`, Output folder `Choose folder...`, after | centred on its path | row `center`, height `32.02`; button `0px`/`0px`, centre `531.79`; path label centre `531.78`; offset `0.01` | matches |
| Space below each chooser row, all three routes | unchanged | row bottom to the next sibling's top: `12` below both `/` rows, below `/reconnect`'s collection row and below `/build-playlist`'s Base collection and Input rows, before and after; `/reconnect`'s output row and `/build-playlist`'s Output folder row have no next sibling | matches |
| Height of what holds each row | shorter by the margin the row no longer carries | `/reconnect` card body `525.72` to `517.75`; `/` card bodies `82.02` to `78` and `99.41` to `95.39`; `/build-playlist` card body `615.53` to `599.53`, Output folder column `57.02` to `49.02` | matches |
| Document and inner scroll | none added | `scrollHeight` 900 on all three routes before and after; `/reconnect`'s `wizard-middle` `scrollHeight` `859` before and `849` after against `clientHeight` `780`; on `/` and `/build-playlist` no element whose `overflow-y` is `auto` or `scroll` has `scrollHeight` above `clientHeight`, before and after | matches |

## What this run establishes

**The margin was the cause, on every chooser row.** Each button carried
`.wizard-control`'s `margin-bottom: 8px` and no top margin, and a flex
row with `align-items: center` centres the margin box, so each border
box stood half the margin, `4px` to within `0.01`, above its path. The
row's height was the button's `32px` plus that `8px` wherever the path
was shorter than `40px`, and the path, centred in that taller row, sat
`4px` below the button. `/reconnect`'s output row is `56px` for its
input, so there the row did not grow, and the offset reads the same.

**The fix cancels the margin where the row places the button.** Each
button reads `margin-bottom: 0px` inside the three row classes and its
centre is its path's. The `12px` from each row to what follows it is
the card body's own gap and is unchanged; each row is as tall as its
tallest box, so what stood below a row sits up by `8px` (`4px` on `/`,
where the field is `36px`, and `0` below `/reconnect`'s `56px` input).

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| `/reconnect`'s collection chooser row | `Main.dc.html:46`'s `.row` (`display:flex;align-items:center;gap:10px`, no margin), and `:92`-`97` holding the path and a `.btn` | a `wizard-path-row`, `align-items` `center`, button `margin-bottom` `0px`, centred on the path | matches |
| `/`'s chooser rows | `Reconstruct.dc.html:46`'s `.row`, the same declaration | `wizard-field-row`, `center`, button `margin-bottom` `0px`, centred on `wizard-field` | matches |
| `/build-playlist`'s chooser rows | `Specs.dc.html:42`'s `.row`, the same declaration | `buildplaylist-input-row`, `center`, each button `margin-bottom` `0px`, centred on the path | matches |
| The space below a row in a card body | `Main.dc.html:35`'s and `Specs.dc.html:31`'s `.card-b` `gap:12px`, the row as tall as its boxes | `12` from row bottom to the next sibling; each row as tall as its tallest box | matches |

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The shipped `native=True` entry point is not read here.

**`/reconnect`'s output row is not drawn on the artboard read here.**
Its reading follows the same rule as the collection row, but no
artboard `.row` for it was compared.

**The resolve step's `Choose...` and the later steps are not read.** No
walk was taken past load. The conflict table's `Choose...` stands in
`wizard-conflict-decision`, not a chooser row, and keeps its margin; its
alignment there is not read.

**`Download CSV template` is not read here.** It stands in a
`wizard-callout` whose `align-items` the earlier record read as
`normal`, not in a chooser row, and this change does not reach it.

**No chooser was clicked.** Every path read is the empty state.

**The typeface and the device pixel ratio were not read.**

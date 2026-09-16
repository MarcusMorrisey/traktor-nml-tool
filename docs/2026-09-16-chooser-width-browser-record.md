# Served-page record: the chooser buttons' widths

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

## How the run was taken

The wizard was served by a scratch script modelled on `serve_w002.py` in
the gate repository at `C:\codex\traktor-nml-tool-gate`, with
`native=False` on a free port (`8761`) and only `pick_file_or_folder`
stubbed, here to return `None`, because every reading below is taken at
load and no chooser was clicked. The gate repository was read and not
written. The viewport is `1280x900`.

Each route was read at load: `/`, `/reconnect` and `/build-playlist`.
For every button whose label starts `Choose` or reads `Download CSV
template`, the run read its bounding width, the width of a range over
its label's content, its parent's width and class, and for the first
reading the button's computed `align-self` and `flex` and the parent's
`display`, `flex-direction` and `align-items`.

The before readings were taken twice on the tree at `c131940`: once
before any edit, and once with the unedited `app.py` and `theme.py`
copied back in from the copies taken beforehand and the server
restarted, for the scroll readings the first pass did not take. The
after readings are `c131940` plus this change: the `wizard-path-row`
rule and the two `/reconnect` choosers composed inside it (ref: DL-299).
The copies restored afterward hash to the edited files' SHA-256.

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| `/reconnect`, `Choose collection file...`, before | sized to its label | width `908` around a `148.8px` label, in a `938px` `wizard-card-body`; button `align-self` `auto`, `flex` `0 1 auto`; parent `display` `flex`, `flex-direction` `column`, `align-items` `normal` | differs |
| `/reconnect`, `Choose output folder...`, before | sized to its label | width `908` around a `145.8px` label, in the same `938px` column, same computed values | differs |
| `/reconnect`, `Choose collection file...`, after | sized to its label, beside its path | width `180.8` around the `148.8px` label; `flex` `0 0 auto`; parent `wizard-path-row`, `908.4px`, `display` `flex`, `flex-direction` `row`, `align-items` `center`; the path label beside it `717.6px` wide, left `196.5` to `913.7`, the button `923.7` to `1104.5` | matches |
| `/reconnect`, `Choose output folder...`, after | sized to its label, beside its path | width `177.8` around the `145.8px` label; `flex` `0 0 auto`; parent `wizard-path-row`, `908.4px`, row, `center`; the path input beside it `720.6px` wide, `196.5` to `916.7`, the button `926.7` to `1104.5` | matches |
| `/reconnect`, vertical alignment in the row, after | the row computes `align-items: center` | `center` on both rows; box centres read: collection row: label centre `249.2`, button centre `245.2`; output row: input centre `667.6` (height `56`), button centre `663.6` (height `32`) | matches |
| `/`, `Choose file...` | sized to its label, before and after | before `114.9` around `82.9px` in a `572.4px` `wizard-field-row` (`flex` row, `align-items` `center`, button `flex` `0 1 auto`); after `114.9` around `82.9px` in `572px` | matches |
| `/`, `Choose folder...` | sized to its label, before and after | before `131.9` around `99.9px` in `572.4px` `wizard-field-row`, same computed values; after `131.9` around `99.9px` in `572px` | matches |
| `/build-playlist`, Base collection `Choose file...` | sized to its label, before and after | `114.9` around `82.9px` in a `992px` `buildplaylist-input-row` (`flex` row, `center`, button `flex` `0 1 auto`), before and after | matches |
| `/build-playlist`, Input `Choose file...` | sized to its label, before and after | `114.9` around `82.9px` in `992px` `buildplaylist-input-row`, before and after | matches |
| `/build-playlist`, Input `Choose folder...` | sized to its label, before and after | `131.9` around `99.9px` in `992px` `buildplaylist-input-row`, before and after | matches |
| `/build-playlist`, `Download CSV template` | sized to its label, before and after | `187` around `155px` in a `992px` `wizard-callout` (`flex` row, `align-items` `normal`, button `flex` `0 0 auto`), before and after | matches |
| `/build-playlist`, Output folder `Choose folder...` | sized to its label, before and after | `131.9` around `99.9px` in a `489px` `buildplaylist-input-row`, before and after | matches |
| Document scroll, all three routes | none | `scrollWidth` 1280 and `scrollHeight` 900 on `/`, `/reconnect` and `/build-playlist`, before and after | matches |
| `/reconnect`, the middle band's own scroll | shorter than before | `wizard-middle` is the one element scrolling: before `scrollHeight` 944 against `clientHeight` 780, card body `611.5px` tall; after `859` against `780`, card body `525.7px` | matches |
| `/` and `/build-playlist`, inner scroll | none | no element whose `overflow-y` is `auto` or `scroll` has `scrollHeight` above `clientHeight`, before and after | matches |

## What this run establishes

**Two buttons stretched, both on `/reconnect`.** Each stood as a
direct child of `.wizard-card-body`, which `theme.py` declares
`display: flex; flex-direction: column`, and neither the column nor the
button sets `align-items` or `align-self`, so the computed
`align-items: normal` stretched each across the column's `908px`
content box. The other seven readings were already sized to their
labels: each stands in a flex row.

**The fix is the artboard's row.** Each `/reconnect` chooser is
composed in a `wizard-path-row` beside the path it chooses, the path
taking the room and the button `flex: none`. The card body is `85.8px`
shorter, and the middle band's overflow goes from `164px` to `79px`.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| `/reconnect`'s collection chooser | `Main.dc.html:92`-`97`: a `.row` holding a `.field` with the path and a `.btn` `Choose file...` | a `wizard-path-row` (`flex` row, `align-items` `center`) holding the path label and the `Choose collection file...` button, the button `180.8px` | matches |
| `/`'s choosers | `Reconstruct.dc.html:46`'s `.row` beside a `.field` | `wizard-field-row` beside `wizard-field`, each button sized to its label | matches |
| `/build-playlist`'s choosers | `Specs.dc.html:42`'s `.row`, `.btn.sm` beside the path | `buildplaylist-input-row` beside the path, each button sized to its label | matches |

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The shipped `native=True` entry point is not read here.

**The path is not drawn in a `.field` box on `/reconnect`.**
`Main.dc.html:93` draws the chosen path inside a bordered `.field`; the
served page draws it as a mono label beside the button. The row is read; the box is not built, and no verdict above
claims it.

**`/reconnect`'s output row is not drawn on the artboard read here.**
The structural row above covers the collection chooser; the output
path's row follows the same rule and its widths are read, but no
artboard `.row` for it was compared.

**The resolve step's `Choose...` and the later steps are not read.** No
walk was taken past load, so `/`'s resolve-step `Choose...`, and any
chooser drawn only after a path is chosen, carries no width reading. The
guard in `tests/test_gui_chooser_width.py` covers its call site.

**The 4px centre offset is not explained.** Both rows compute
`align-items: center`, yet each button's box centre reads `4px` above
its neighbour's; what inside the label or the input's box accounts for
it was not read.

**No chooser was clicked.** The stub returns `None`, so every path read
is the empty state; a long chosen path's truncation in the row is not
read.

**The typeface and the device pixel ratio were not read.** The label
widths are those the pane rendered; whether IBM Plex Sans had loaded
and at what `devicePixelRatio` is not recorded.

The button padding against the artboard's `.btn.sm` `0 12px` is not
judged here: every reading shows `32px` between label and button width,
which this run records and does not change.

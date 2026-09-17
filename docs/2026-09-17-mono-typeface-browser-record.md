# Served-page record: the monospace typeface on three routes

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against what `theme.py` declares for it.

This record closes the **font falls back** notes two earlier records
carry:

- `docs/2026-09-17-report-columns-browser-record.md`:`82` and `:104`
  read both the report's number cell and its entry cell as taking
  Tailwind's `font-mono` stack rather than IBM Plex Mono, and recorded
  that as `differs`.
- `docs/2026-09-15-resolve-rail-fields-browser-record.md`:`136` notes
  the field key's own label carried a `font-mono` class. The resolve
  rail's key and raw cells are read here as a control: they were already
  reading IBM Plex Mono before this change and still are after it.

Both of those records stand as their runs left them and are not edited
here.

## How the run was taken

The wizard was served by one scratch script modelled on `serve_w002.py`
and `serve_reconstruct.py` in the gate repository at
`C:\codex\traktor-nml-tool-gate`, with `native=False`, `show=False` and
`reload=False`, one route per port: `/reconnect` on `8121`,
`/build-playlist` on `8122` and `/` on `8123`. The only thing stubbed is
`pick_file_or_folder`, which opens a native dialog the browser cannot
drive; it returns the next path in that route's ordered list, the last
one repeating. The gate repository was read and not written: its
`fixture/w002gatefix2` and `fixture/reconstruct-conflict` were copied
into the scratchpad and served from there, and the build-playlist run
wrote into a scratchpad folder. The viewport is `1280x900`.

The fixtures:

- `/reconnect` reads `w002gatefix2/stale.nml` as the collection and
  `w002gatefix2/audio` as the one scan root.
- `/build-playlist` reads `reconstruct-conflict/base.nml` as the base
  and a four-line scratch `tracklist.txt` as the input: `A - One`,
  `A - Nonexistent Track With A Deliberately Long Name So The Entry Cell
  Must Truncate`, `NoDelimiterHereAtAll` and `A - Two`. With
  `Allow unmatched lines` on, the run wrote and the footer read
  `Written: "FontProbe" with 2 tracks.`, leaving two report rows: line
  `2` unmatched and line `3` unparseable, so the number and entry cells
  are read on real rows.
- `/` reads `reconstruct-conflict/base.nml` as the base and
  `source.nml` and `source-two.nml` as the two sources, which is the
  fixture `serve_reconstruct.py` documents; `Preview` then
  `Continue to resolve` reaches the conflict table and the rail, and
  `All source.nml` then `Continue to write` reaches the originals list.

Each route was driven twice: once against `0618397`, the tree before
this change, and once against the same tree with this change applied.
The servers were restarted between the two passes, because the page's
class strings are read from the imported module. Every server was
stopped after the run.

Each element is identified by its own class list, read back off the
element with the computed `font-family`, `font-size`,
`text-overflow`/`overflow`/`white-space`, `clientWidth` and
`scrollWidth` in the same call, so the family and the truncation are one
reading rather than two.

The two families that appear below, quoted from `getComputedStyle`:

- Tailwind's utility stack, which is what `font-mono` resolves to:
  `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation
  Mono", "Courier New", monospace`
- `theme.FONT_MONO`, which is what the sheet's own classes declare:
  `"IBM Plex Mono", ui-monospace, Consolas, monospace`

**The vendored face is loaded on the served page.** `document.fonts`
registers three `IBM Plex Mono` faces, at weights `400`, `500` and
`600`. On the `/reconnect` set-up step
`document.fonts.check('11px "IBM Plex Mono"')` reads `false` in both
passes, because that check asks for weight `400` and the mono elements
on that step paint at `600`; at the weights and sizes actually used
there, `document.fonts.check('600 15px "IBM Plex Mono"')` and
`document.fonts.check('600 11px "IBM Plex Mono"')` both read `true`, and
`[...document.fonts]` reads `500 loaded` and `600 loaded` for the
family. Weight `400` reads `unloaded` until an element paints at it, and
reads `loaded` on every state below where one does. So the face is
present and the computed family names a face the document holds, not a
family that is merely spelled.

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

The `Before` and `After` columns are the computed `font-family` on the
same element in the two passes. `T` is Tailwind's utility stack and `P`
is `theme.FONT_MONO`, both spelled in full above.

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| `/reconnect` collection path label | IBM Plex Mono after, not before | before `T` at `15px`; after `P` at `15px`, class list `wizard-mono wizard-body-15 wizard-subtle-1` | matches |
| `/reconnect` collection path label: its truncation | still shortened in its row | `text-overflow` `ellipsis`, `overflow` `hidden`, `white-space` `nowrap` in both passes; `clientWidth` `717` against `scrollWidth` `1204` before and `717` against `1314` after, so it overflows and is clipped in both | matches |
| `/reconnect` scan-root path label | IBM Plex Mono after, not before | before `T` at `11px`; after `P` at `11px`, class list `wizard-mono wizard-body-11 wizard-subtle-2` | matches |
| `/reconnect` candidate panel heading | IBM Plex Mono after, not before | before `T` at `16px`; after `P` at `16px`, text `Old: archangel.mp3` | matches |
| `/reconnect` candidate lines | IBM Plex Mono after, not before | before `T` at `13px` on both `[1] archangel.mp3 - Strong` and `[2] archangel.mp3 - Strong`; after `P` at `13px` on both | matches |
| `/build-playlist` base collection path | IBM Plex Mono after, not before | before `T` at `15px`; after `P` at `15px`, class list `wizard-mono wizard-body-15 wizard-subtle-1` | matches |
| `/build-playlist` base path: its truncation | still shortened in its row | `ellipsis`/`hidden`/`nowrap` in both; `clientWidth` `867` against `scrollWidth` `1262` before and `867` against `1377` after | matches |
| `/build-playlist` input path | IBM Plex Mono after, not before | before `T` at `15px`; after `P` at `15px` | matches |
| `/build-playlist` input path: its truncation | still shortened in its row | `ellipsis`/`hidden`/`nowrap` in both; `clientWidth` `672` against `scrollWidth` `1130` before and `672` against `1233` after | matches |
| `/build-playlist` output folder display | IBM Plex Mono after, not before | before `T` at `15px`; after `P` at `15px`, `ellipsis`/`hidden`/`nowrap` and `clientWidth` `347` in both passes | matches |
| `/build-playlist` report number cell | IBM Plex Mono after, not before | before `T` at `12px` on the cells reading `2` and `3`; after `P` at `12px` on both, class list `wizard-mono wizard-dim` | matches |
| `/build-playlist` report entry cell | IBM Plex Mono after, not before | before `T` at `12px` on `A - Nonexistent Track With A Deliberately ...` and on `NoDelimiterHereAtAll`; after `P` at `12px` on both, class list `wizard-mono buildplaylist-report-entry` | matches |
| `/build-playlist` report entry cell: its clipping rule | unchanged | `ellipsis`/`hidden`/`nowrap` with `clientWidth` `808` in both passes | matches |
| `/build-playlist` report columns | header and rows on the same tracks as before | `grid-template-columns` `64px 808px 120px` on the header row and on both body rows, and cell left edges `137`, `201`, `1009` on the header and on both body rows - the same three values in both passes | matches |
| `/` conflict table track cell | IBM Plex Mono after, not before | before `T` at `12px` on all six rows; after `P` at `12px` on all six, class list `wizard-mono wizard-body-12 wizard-conflict-track` | matches |
| `/` conflict track cell: its truncation | still shortened in its column | `ellipsis`/`hidden`/`nowrap` and `clientWidth` `142` on all six rows in both passes; the longest, `C:/:Music/:seven.mp3|C:/:Music/:seven.mp3`, reads `scrollWidth` `295` before and `319` after | matches |
| `/` conflict table candidate-count cell | IBM Plex Mono after, not before | before `T` at `12px` on the cells reading `3`, `3`, `3`, `3`, `2`, `2`; after `P` at `12px` on all six, `clientWidth` `72` in both passes | matches |
| `/` resolve rail heading | IBM Plex Mono after, not before | before `T` at `14.5px` on `C:/:Music/:one.mp3`; after `P` at `14.5px`, `clientWidth` `370` in both passes | matches |
| `/` resolve rail field key | IBM Plex Mono in both passes | `P` at `11px` on `ARTIST` and `TITLE` before and after, class list `wizard-answer-field-key` with no font class beside it | matches |
| `/` resolve rail field raw value | IBM Plex Mono in both passes | `P` at `11px` before and after, class list `wizard-answer-field-raw wizard-faint` | matches |
| `/` write step originals list | IBM Plex Mono after, not before | before `T` at `12.5px` on all three rows; after `P` at `12.5px` on all three, class list `wizard-mono wizard-list-name` | matches |
| `/` originals list: its truncation | still shortened in its row | `ellipsis`/`hidden`/`nowrap` and `clientWidth` `246` on all three rows in both passes; `scrollWidth` `1052`, `1065`, `1093` before and `1148`, `1163`, `1193` after | matches |
| The document, every route | unscrolled | `documentElement.scrollHeight` not above its `clientHeight`, and the same of `body`, on all three routes in both passes | matches |
| The middle region, every route | the shell's scroll owner, unchanged | `.wizard-middle` overflows its `clientHeight` on the `/reconnect` set-up step, on `/build-playlist` after the run and on `/`'s resolve step, and does not on `/reconnect`'s review step or `/`'s write step - the same five answers in both passes | matches |

## What this run establishes

**Every element that read the system monospace now reads IBM Plex
Mono.** Thirteen of the fourteen call sites were reached on the served
page across the three routes, and each one read Tailwind's utility stack
before and `theme.FONT_MONO` after. No element read the utility stack
after.

**The face the computed family names is a face the document holds.**
`document.fonts` registers `IBM Plex Mono` at weights `400`, `500` and
`600`, and the check at the weight and size each state actually paints
reads `true`. Weight `400` moves from `unloaded` to `loaded` on the
states where a `400` mono element paints, which is the browser reporting
it activated the vendored face rather than a fallback.

**The ellipsis truncation followed the class.** The two rules that
describe a row's children by the class they carry -
`.wizard-path-row > .wizard-mono` and
`.buildplaylist-input-row > .wizard-mono` - still reach the path labels:
`ellipsis`/`hidden`/`nowrap` reads the same on the `/reconnect`
collection path and on the build-playlist base, input and output-folder
paths in both passes, and each overflows its own `clientWidth` and is
clipped. The same holds for the three truncating surfaces whose rule
names the element's class directly:
`.wizard-conflict-track`, `.buildplaylist-report-entry` and
`.wizard-list-name`.

**The report's columns did not move.** `grid-template-columns` reads
`64px 808px 120px` and the cell left edges read `137`, `201` and `1009`
on the header row and on both body rows, in both passes. The `1009`
left edge is the `Kind` column
`docs/2026-09-17-report-kind-pills-browser-record.md` read at
`1008.6000366210938`, rounded here.

**A wider glyph did not start a scroll.** IBM Plex Mono is wider than
the system monospace at these sizes - every truncating surface reads a
larger `scrollWidth` after than before - and the document still does not
scroll on any of the three routes. The scrolling stayed where the shell
puts it, on `.wizard-middle`, on the same states as before.

**The resolve rail was already right and stayed right.** The key and
raw cells read `theme.FONT_MONO` in both passes: their own rules declare
it and they name no font class beside it, which is the shape the rest of
the call sites now take.

## Structural verdicts

| Structure | What theme.py declares | The served page composes | Verdict |
|---|---|---|---|
| The monospace typeface | `FONT_MONO`, `'IBM Plex Mono', ui-monospace, Consolas, monospace`, declared on `.wizard-mono` and on every rule that sets a mono `font:` shorthand | every mono element carries either `wizard-mono` or a class whose own rule declares `FONT_MONO`, and no element carries a `font-*` family utility | matches |
| A path row's flexible child | `.wizard-path-row > .wizard-mono` and `.buildplaylist-input-row > .wizard-mono`, which give the child `flex: 1`, `min-width: 0` and the ellipsis | the path labels in those rows carry `wizard-mono`, so the rules reach them, and read `ellipsis`/`hidden`/`nowrap` with their content overflowing | matches |

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The shipped `native=True` entry point is not read here.

**One of the fourteen call sites was not reached on the served page.**
The refusal reasons inside the preview step's warning callout on `/`
were not rendered by any state this fixture reached, so no before or
after family was read for them and no verdict row stands for them. Its
class string was changed with the other thirteen, and the guards in
`tests/test_gui_theme.py` read it from `app.py`'s AST, but the browser
did not paint it.

**The glyphs were not compared.** What is read is the computed
`font-family` and what `document.fonts` reports about the face at that
weight and size. No rendering of the text was compared against a
reference image, so that the shapes on screen are IBM Plex Mono's rather
than a fallback's is established by the font-set reading, not by the
pixels.

**The type was not read at another width or another pixel ratio.** Every
`clientWidth` and `scrollWidth` above is what `1280x900` leaves.

**No surface was read where the wider glyph changes a line count.**
Every truncating surface above clips on one line, so a mono string that
wrapped to a second line under the wider face was not read.

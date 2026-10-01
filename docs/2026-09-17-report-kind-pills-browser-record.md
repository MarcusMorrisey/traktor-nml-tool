# Served-page record: the unresolved report's kind pills

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

This record closes the **kind cell** difference
`docs/2026-09-17-report-columns-browser-record.md` names under the three
parts of the report card that differ from the artboard: `:60`-`63` draw
a `.kind` pill per row, coloured per kind and uppercase, and that record
read the kind as plain lowercase text at `#97A0A7`. That record stands
as its run left it and is not edited here.

## How the run was taken

The wizard was served by a scratch script modelled on `serve_w002.py` in
the gate repository at `C:\codex\traktor-nml-tool-gate`, with
`native=False` on a free port (`61164`) and only `pick_file_or_folder`
stubbed: its first file call returned a scratch `base.nml`, every later
file call a scratch `tracks.txt`, and a folder call the scratch folder.
The gate repository was read and not written. The viewport is
`1280x900`, read back as `innerWidth` `1280` and `innerHeight` `900`.

`base.nml` is the collection `_base_nml()` in
`tests/test_build_playlist_text_parity.py` builds, which holds
`Dup - Twice` at two locations. `tracks.txt` is the three lines
`Nobody - Nothing`, `Dup - Twice` and `no delimiter here`, so one run
leaves one row of each kind: the first resolves against nothing, the
second resolves equally against both `Dup - Twice` locations, and the
third has no delimiter to parse. `assemble_output` was called on the two
files directly before the run and printed
`errors: ['unresolved_tracks']` with the rows
`1 'Nobody - Nothing' unmatched`, `2 'Dup - Twice' ambiguous` and
`3 'no delimiter here' unparseable`, so the three kinds are read back
rather than assumed.

On `/build-playlist` the base `Choose file...` was clicked once, the
input `Choose file...` clicked once, the playlist name set to `Set`,
`Allow unmatched lines` and `Full collection` left off, and
`Write playlist` clicked. Before the run a `scroll` listener was on
`.wizard-middle` and on `document` and `.wizard-middle`'s `scrollTop`
was set to `0`; the readings were taken three seconds after the click.

The pane's `devicePixelRatio` read `2.5`, which is why a `1px` border
resolves to `0.8px` in `getComputedStyle`: `1` CSS pixel is `2.5`
device pixels, which snaps to `2`. The declaration itself was read back
off the rule through `document.styleSheets` in the same call, and reads
`1px solid rgb(90, 58, 36)` for the unmatched pill.

The readings are taken on `9b1a97d` plus this change: the Kind cell
built as a pill element whose class comes from the row's kind through
`buildplaylist_view.kind_pill_classes`, and the pill's shape and the
three kinds' tints declared in `theme.py` (ref: DL-304). No before pass
was taken here; the state before the change is the kind cell
`docs/2026-09-17-report-columns-browser-record.md` already read. The
server was stopped after the run.

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| The report's rows | one row of each kind with Allow unmatched off | three rows; the footer `Not written: 3 entries did not resolve and Allow unmatched is off.` | matches |
| Unmatched pill: its text | `Unmatched`, drawn uppercase | `textContent` `Unmatched`, `text-transform` `uppercase` | matches |
| Unmatched pill: its colours | `#E07A4C` on `#2B1D14` inside `#5A3A24` | `color` `rgb(224, 122, 76)`, `background-color` `rgb(43, 29, 20)`, `border` `0.8px solid rgb(90, 58, 36)` for a rule declaring `1px solid rgb(90, 58, 36)` | matches |
| Ambiguous pill: its text | `Ambiguous`, drawn uppercase | `textContent` `Ambiguous`, `text-transform` `uppercase` | matches |
| Ambiguous pill: its colours | `#F5D96B` on `#1F1D14` inside `#5A4E2A` | `color` `rgb(245, 217, 107)`, `background-color` `rgb(31, 29, 20)`, `border` `0.8px solid rgb(90, 78, 42)` | matches |
| Unparseable pill: its text | `Unparseable`, drawn uppercase | `textContent` `Unparseable`, `text-transform` `uppercase` | matches |
| Unparseable pill: its colours | `#97A0A7` on `#1B1D20` inside `#3C4248` | `color` `rgb(151, 160, 167)`, `background-color` `rgb(27, 29, 32)`, `border` `0.8px solid rgb(60, 66, 72)` | matches |
| Every pill: its type | 600 11px/1 IBM Plex Mono at `.04em` | `font` `600 11px / 11px "IBM Plex Mono", ui-monospace, Consolas, monospace` and `letter-spacing` `0.44px`, which is `.04em` of `11px`, on all three | matches |
| Every pill: its box | `3px 6px` inside a `4px` radius, never wrapped | `padding` `3px 6px`, `border-radius` `4px`, `white-space` `nowrap` on all three | matches |
| Every pill: it hugs its text | narrower than the `120px` Kind column | `display` `inline-block`; pill widths `76.9625015258789`, `76.9625015258789` and `91.04375457763672` against a Kind cell width of `120` on every row | matches |
| Every pill: where it starts | at its cell's left edge | pill left `1008.6000366210938` and cell left `1008.6000366210938` on all three rows | matches |
| The `Kind` column | same left and width as the header | header `Kind` cell left `1008.6000366210938`, width `120`; every body row's Kind cell left `1008.6000366210938`, width `120`; the header cells read `#`, `Entry`, `Kind` | matches |
| The document | unscrolled | `document.scrollingElement.scrollTop` `0`, `scrollHeight` `900`, `window.scrollY` `0`; no `scroll` event on `document` | matches |
| The middle region | scrolls to bring the card into view | `.wizard-middle` `scrollTop` `0` before the click and `99.5999984741211` after, `scrollHeight` `879` against `clientHeight` `780`; one `scroll` event on `.wizard-middle` | matches |

## What this run establishes

**Each kind is drawn as a coloured pill.** The three pills read the
artboard's own text hue, tinted ground and border: `#E07A4C` on
`#2B1D14`, `#F5D96B` on `#1F1D14` and `#97A0A7` on `#1B1D20`, each
inside its own `1px` border. One run showed all three at once, so no
kind's tint is inferred from another's rule.

**The pill's shape is declared once and reaches every kind.** All three
read the same `600 11px/1` IBM Plex Mono, `0.44px` of letter-spacing,
`uppercase`, `3px 6px` of padding, a `4px` radius and `nowrap`.

**The pill hugs its word.** At `display: inline-block` the widest pill
measured `91.04375457763672` inside a `120` cell, so the tint stops at
the word rather than painting the whole Kind column.

**The Kind column did not move.** Its left edge and width read
`1008.6000366210938` and `120` on the header and on all three body
rows, the values
`docs/2026-09-17-report-columns-browser-record.md` read for that column,
so the pill sits inside the track the header already fixed.

**The document still does not scroll.** `document`'s `scrollTop` read
`0` with no `scroll` event, and the one scroll event reached
`.wizard-middle`, which is the shell's scroll owner.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| The report's kind cell | `Specs.dc.html:180`-`182`'s `<span class="kind unmatched">Unmatched</span>` and its two siblings, tinted by `:60`-`63` | a cell holding one `buildplaylist-report-kind buildplaylist-report-kind-<kind>` element per row, the shape on the shared class and each kind's three colours on its own rule | matches |
| The kind pill's word | `:180`-`182`'s `Unmatched`, `Ambiguous`, `Unparseable`, rendered uppercase by `:60` | `Unmatched`, `Ambiguous` and `Unparseable` with `text-transform: uppercase` | matches |

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The shipped `native=True` entry point is not read here.

**A kind with no tint rule was not read on the page.** The shared pill
class carries the shape with no colour or border of its own, so such a
kind would read as an uppercase mono word in the row's ink; no run
produced one, because the three kinds
`tracklist.resolve_candidates` can return all have a rule.

**The pills were not read at another width or another pixel ratio.**
The `120` Kind track is what `.wizard-content-width` leaves at `1280`,
and the `0.8px` border is what `devicePixelRatio` `2.5` snaps a `1px`
declaration to.

**No pill wider than its column was read.** The longest kind,
`Unparseable`, measured `91.04375457763672` against `120`, so `nowrap`
holding a pill on one line past its track's width was not read.

**The remaining two differences the columns record names were not
closed.** The entry and number cells' font family and the read-only note
under the report stand as that record read them.

# Served-page record: the build-playlist report's column headers

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

## How the run was taken

The wizard was served by a scratch script modelled on `serve_w002.py` in
the gate repository at `C:\codex\traktor-nml-tool-gate`, with
`native=False` on a free port (`52601`) and only `pick_file_or_folder`
stubbed: its first file call returned a scratch `base.nml`, every later
file call a scratch `tracks.txt`, and a folder call the scratch folder.
The gate repository was read and not written. The viewport is
`1280x900`.

`base.nml` is the collection `_base_nml()` in
`tests/test_build_playlist_text_parity.py` builds, where `Dup - Twice`
is held at two locations. `tracks.txt` holds five lines: `Alpha - One`,
`Nobody - Nothing`, `Dup - Twice`, `no delimiter here`, and a
247-character line with no break opportunity in its title. On
`/build-playlist` both `Choose file...` buttons were clicked, the
playlist name was set to `Set`, `Allow unmatched lines` and
`Full collection` read off, and `Write playlist` was clicked. The footer
read `Not written: 4 entries did not resolve and Allow unmatched is off.`
and the report card showed.

The readings are taken on `0d90147` plus this change: the report built
as a header row and body rows on `.buildplaylist-report-grid`'s tracks
(ref: DL-302). No before pass was taken here; the label rows this
replaces are recorded in
`docs/2026-09-16-build-playlist-inputs-browser-record.md`. The server was
stopped after the run.

For each row of `.buildplaylist-report` the run read its class, its
computed `grid-template-columns`, its bottom border and its bounding
top and height, and for each cell its text, bounding left and width,
computed font, `letter-spacing`, `text-transform`, colour and padding,
and `scrollWidth` against `clientWidth` with `overflow`,
`text-overflow` and `white-space`. The device pixel ratio read `2.5`.

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| Header cells' text | `#`, `Entry`, `Kind` | `#`, `Entry`, `Kind`, in that order, in one `buildplaylist-report-grid buildplaylist-report-header` row | matches |
| Header cells' label | 600 11px/1 mono, uppercase, `.06em`, `#8E979E` | each cell `"IBM Plex Mono"` `600` `11px/11px`, `letter-spacing` `0.66px`, `text-transform` `uppercase`, colour `rgb(142, 151, 158)`, padding `0px 0px 8px` | matches |
| Tracks on every row | one set: `64px`, the rest, `120px` | `grid-template-columns` `64px 808.4px 120px` on the header and on all four body rows; the report box `992.4` wide at left `136.2` | matches |
| `#` column | same left and width on every row | left `136.2`, width `64` on the header and on rows `2`, `3`, `4`, `5` | matches |
| `Entry` column | same left and width on every row | left `200.2`, width `808.4` on the header and on rows `2`, `3`, `4`, `5` | matches |
| `Kind` column | same left and width on every row | left `1008.6`, width `120` on the header and on rows `2`, `3`, `4`, `5` | matches |
| Body rows' kinds | one of each kind with Allow unmatched off | row `2` `Nobody - Nothing` `unmatched`, row `3` `Dup - Twice` `ambiguous`, row `4` `no delimiter here` `unparseable`, row `5` the long line `unmatched` | matches |
| Header rule | 1px solid `#2A2E32` under the header | `border-bottom` `0.8px solid rgb(42, 46, 50)`; header bottom `813.64`, first body row top `813.64` | matches |
| Body row rules | 1px solid `#23272B` under each row but the last | rows `2`, `3`, `4` `0.8px solid rgb(35, 39, 43)`; row `5` `0px none` | matches |
| Body cell inset | `7px 0` | every body cell padding `7px 0px`; rows `2`-`4` height `32.2`, row `5` `31.4` | matches |
| Long entry | shortened with an ellipsis, `Kind` not moved | row `5`'s entry cell `overflow` `hidden`, `text-overflow` `ellipsis`, `white-space` `nowrap`, `scrollWidth` `1630` against `clientWidth` `808`; its `Kind` cell left `1008.6`, width `120`, as on every other row | matches |
| Number cell | mono, `#A5ADB4` | colour `rgb(165, 173, 180)`, family `ui-monospace, SFMono...`, `12px` | differs |
| Document and inner scroll | no document scroll | document `scrollHeight` `900` against `clientHeight` `900`, `scrollWidth` `1280` against `1280`; `wizard-middle` `scrollHeight` `907` against `clientHeight` `780`, the only element whose `overflow-y` scrolls with content past its height | matches |

## What this run establishes

**The header stands over its column at every row.** The header and the
four body rows each resolve `64px 808.4px 120px`, and each column's left
edge and width read identical on all five rows, because the header is a
modifier on the grid the body rows use rather than a grid of its own.

**The long entry shortens inside its track.** Its text is `1630` wide in
an `808` cell, and the `Kind` cell beside it stands where it stands on
every other row.

**The rules are the artboard's at this pixel ratio.** The 1px borders
read `0.8px`, which is 2 device pixels at the `2.5` ratio read; the
colours are `#2A2E32` under the header and `#23272B` under each body
row, with none under the last.

**The number cell's colour is the artboard's `.dim`; its family is not
the artboard's `.mono`.** It reads `#A5ADB4`, and it and the entry cell
read Tailwind's `font-mono` stack rather than IBM Plex Mono. That class
is the cells' existing one and this change does not reach it.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| The report's columns | `Specs.dc.html:177`-`178`'s `table.rep` with `#` at `64px`, `Entry` the rest, `Kind` at `120px` | one grid, `64px minmax(0, 1fr) 120px`, the header and every body row on its tracks | matches |
| The header row | `:57`'s `th`: `600 11px/1` mono, `.06em`, uppercase, `#8E979E`, `padding:0 0 8px`, `1px solid #2A2E32` below | `buildplaylist-report-header` on the same grid, its cells carrying that label and inset, the rule below it | matches |
| The body rows | `:58`-`59`'s `td`: `padding:7px 0`, `1px solid #23272B` below, `vertical-align:top`, the last row with no rule | `buildplaylist-report-row` cells padded `7px 0`, `align-items: start`, the rule below each row and none below the last | matches |
| The report's type size | `:56`'s `font-size:12px` | `.buildplaylist-report` `12px` | matches |

This closes the structural difference
`docs/2026-09-16-build-playlist-inputs-browser-record.md` records, that
the report is drawn as label rows rather than the artboard's table.

Three parts of the report card differ from the artboard, and none is
recorded under Composition not built, as that record states for the
report card:

- **The entry and number cells.** `:180`-`182` draw a `mono` entry and a
  `mono dim` number. The number reads `#A5ADB4`, the `.dim` colour, but
  both cells take the `font-mono` family, not IBM Plex Mono: differs.
- **The kind cell.** `:60`-`63` draw a `.kind` pill per row, coloured per
  kind and uppercase. The page draws the kind as plain lowercase text at
  `#97A0A7`: differs.
- **The note under the report.** `:185` draws the read-only note. No text
  on the page contains `read-only`: differs.

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The shipped `native=True` entry point is not read here.

**The report was not read at another width.** The `Entry` track's
`808.4` is what `.wizard-content-width` leaves at `1280`.

**No report with a single row, or with more rows than the card shows,
was read.** Row `5` stands below the viewport inside `wizard-middle`'s
scroll; its readings are bounding boxes, not what was seen on screen.

**The typeface in use was not read beyond the computed family.**

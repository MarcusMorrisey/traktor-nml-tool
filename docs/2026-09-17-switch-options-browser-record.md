# Served-page record: the switches' option rows and the read-only note

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

`design/build-playlist/Specs.dc.html:155`-`169` draws each switch as an
option row: the switch, its label, and under the label a description of
what each state writes. `:185` draws a note under the unresolved
report's table. This record reads all three on the page.

## How the run was taken

The wizard was served by the same scratch script the kind-pills record
used, modelled on `serve_w002.py` in the gate repository at
`C:\codex\traktor-nml-tool-gate`, with `native=False` on a free port
(`8122`) and only `pick_file_or_folder` stubbed: its first file call
returned the scratch `base.nml`, every later file call the scratch
`tracks.txt`. The gate repository was read and not written. The viewport
read back as `innerWidth` `1024` and `innerHeight` `768`, and
`devicePixelRatio` read `2.5`, which is why a `1px` border resolves to
`0.8px` in `getComputedStyle`.

`base.nml` and `tracks.txt` are the fixture
`docs/2026-09-17-report-kind-pills-browser-record.md` describes, so one
run leaves one unresolved row of each kind and the report card is on the
page to read the note in.

The option rows were read on the page as served. The report's note was
read after clicking the base `Choose file...` once, the input
`Choose file...` once, setting the playlist name to `Set` and clicking
`Write playlist` with both switches off.

Whether the label still works as the switch's own control was read by
clicking it: Quasar builds the label as the switch's child, and the
description is a sibling of the whole control, so the two are read
separately.

The readings are taken on `0bc8f88` plus this change: the two option
rows, the description under each switch's label and the note under the
report's table, with their wording held in `buildplaylist_view.py` and
read off the artboard by `tests/test_gui_buildplaylist_options.py`
(ref: DL-307). The server was stopped after the run.

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| The option rows | two, one per switch | two `.buildplaylist-option` elements, `929` wide, `65` and `82` tall | matches |
| An option row's box | `11px 12px` inside a `6px` radius | `padding` `11px 12px`, `border-radius` `6px` on both | matches |
| An option row's ground | `#14171A` inside `1px` of `#2A2E32` | `background-color` `rgb(20, 23, 26)`, `border` `0.8px rgb(42, 46, 50)` for a rule declaring `1px solid rgb(42, 46, 50)`, on both | matches |
| The switch's label: its text | `Allow unmatched lines` and `Full collection` | `textContent` `Allow unmatched lines` and `Full collection` | matches |
| The switch's label: its type | `13px` at `600` | `font-size` `13px`, `font-weight` `600`, on both | matches |
| The switch's label: its gap | `11px` from the switch | `padding-left` `11px` on both | matches |
| The description: its text | `:159` and `:167`'s sentences | `Write the playlist even if some entries could not be matched. Off, a run with any unmatched or ambiguous entry aborts and writes nothing.` and `Keep the whole source collection and playlist tree in the output. Off, the file written holds only this one playlist and the entries it matched - the normal, importable hand-off.` | matches |
| The description: its type | `12px` of `#A5ADB4` at a `1.45` line-height | `font-size` `12px`, `color` `rgb(165, 173, 180)`, `line-height` `17.4px`, which is `1.45` of `12px`, on both | matches |
| The description: where it starts | under the label, not under the switch | `margin` `3px 0px 0px 45px`; measured `45` from the switch's left edge and `11` from the label's, on both | matches |
| The description: how far below | `3px` under the label | measured `3.08` and `3.07` from the label's bottom | matches |
| The description: it wraps | as many lines as its sentence needs | heights `17` for the first and `35` for the second, against a `17.4px` line | matches |
| The label still toggles | clicking the label flips the switch | `--truthy` absent, `true` after one label click, absent again after a second | matches |
| The description does not toggle | clicking it changes nothing | `--truthy` absent after clicking the description | matches |
| The report's note: its text | `:185`'s sentence | `This report is read-only. Fixing an entry means editing the input and choosing it again.` | matches |
| The report's note: its type | `11.5px` of `#8E979E` | `font-size` `11.5px`, `color` `rgb(142, 151, 158)` | matches |
| The report's note: where it sits | under the table, at its left edge | `margin` `8px 0px 0px`; measured `20` below the table and `20` below the last row, `0` from the table's left edge | matches |
| The report's note: it is on the page | visible with the card | height above zero, with `3` report rows and the footer `Not written: 3 entries did not resolve and Allow unmatched is off.` | matches |

## What this run establishes

**Each switch says what its two states write.** Both descriptions read
on the page as the artboard's own sentences, so the difference between
the two states of `Allow unmatched lines` and of `Full collection` is on
the screen rather than only in the design.

**The description sits under the label, not under the switch.** The
measured offset reads `45` from the switch's left edge and `11` from the
label's, which is the `34px` track plus the row's `11px` gap, so the
sentence starts on the same pixel column as the word it explains.

**The label is still the switch's own control.** One click on it flipped
`--truthy` on and a second flipped it off, and a click on the
description did not, so putting the sentence beside the control did not
take the label's toggling away.

**The note under the report reads at the artboard's distance.** The
`8px` margin measures `20` below the table because the card's body is a
flex column with a `12px` gap, which is what `Specs.dc.html:31`'s
`.card-b` is as well: the artboard renders the same `12`-plus-`8`.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| The option row | `Specs.dc.html:47`'s `.opt`: `display: flex`, `gap: 11px`, `padding: 11px 12px`, `border: 1px solid #2A2E32`, `border-radius: 6px`, `background: #14171A` | a `buildplaylist-option` element holding the switch and its description, bordered and padded from `BORDER`, `RADIUS_LG`, `SURFACE_1`, `SPACE_11` and `SPACE_12`, with the row's gap carried by the label's own `padding-left` because Quasar builds the label as the switch's child | matches |
| The option's title | `:49`'s `.opt-t`: `font-size: 13px`, `font-weight: 600` | Quasar's `.q-toggle__label` inside a `buildplaylist-option` row, at `TYPE_13` and `600` | matches |
| The option's description | `:50`'s `.opt-d`: `font-size: 12px`, `color: #A5ADB4`, `line-height: 1.45`, and the sentences at `:159` and `:167` | a `buildplaylist-option-note` label per row at `TYPE_12`, `TEXT_MUTED` and `1.45`, indented by `OPTION_NOTE_INDENT`, its sentence from `buildplaylist_view` | matches |
| The report's note | `:185`'s `<p class="faint" style="margin:8px 0 0;font-size:11.5px">` and its sentence | a `buildplaylist-report-note` label after the report table at `SPACE_8`, `TYPE_11_5` and `TEXT_FAINT`, its sentence from `buildplaylist_view` | matches |

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The shipped `native=True` entry point is not read here.

**The dash in the second description is an ASCII hyphen.** The artboard
typesets `matched — the normal` with an em dash; the string on the
screen carries `matched - the normal`, and the guard that reads the
artboard folds the em dash to the hyphen before comparing, so the two
are read as one sentence rather than two.

**The rows were not read at another width.** At `1024` the row measured
`929` wide and the first description fitted one line; how either
sentence wraps at a narrower width is unread.

**The note was not read on a run that left no rows.** The report card is
hidden when a run resolves everything, and the note is inside that card,
so the state where neither is on the page was not measured.

**The read-only claim itself is not read as behaviour.** The note says
the report is read-only; that no cell in it is a control is what the
page builds, not something this run exercised.

# Served-page record: build-playlist inputs, template and folders

DL-084 as DL-169 amends it: the readings a browser took off the running
`/build-playlist` page, one verdict per surface, followed by a structural
reading of what the page composes against
`design/build-playlist/Specs.dc.html`.

## How the run was taken

The page was served with the repository's `.venv` by a scratch script,
`ui.run(native=False, host="127.0.0.1", port=8131)`, after
`app.build_wizard()`. Two functions were stubbed: `pick_file_or_folder`
returned whichever fixture path the walk had last posted to a stub route,
and `pick_save_path` raised if reached, since a served page has no native
window. `write_bytes_atomically` was wrapped to log each write. The
viewport is `1280x900`.

The fixture was written to a scratch directory: a base collection holding
three entries and the playlist tree `Sets`, `Sets\2026`, `Sets\Warmup`,
`Archive`, `Archive\Warmup`, so `Warmup` is a shared name; two 4 KB files
in `Music\Set` that two of the entries name; `list.txt` and `list.csv`
naming those two tracks, the CSV with a third row naming no track;
`set.m3u8` listing the two files; and an empty `exports` directory.

The walk: read the page with nothing chosen; press `Download CSV
template` and read the bytes the browser was handed; choose the base and
`list.csv`; name the playlist; choose `exports` as the output folder; press
`Write playlist` with Full collection and Allow unmatched off; turn both
on; open the playlist-folder chooser, click a disabled option, then pick
`Sets\2026`; write; then choose `list.txt`, `set.m3u8` and the `Music\Set`
folder in turn, writing each under a new name; turn Full collection off
again.

The download was read in the page: `URL.createObjectURL` was wrapped to
keep the Blob NiceGUI builds for `ui.download`, and the anchor click that
would save it was suppressed, so no file was saved and the bytes were read
from the Blob.

The code under measurement is `05f0c84` plus the working tree of this
plan's milestones M-001 to M-007.

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| The input card's label | `INPUT` | `INPUT`, `text-transform: uppercase` | matches |
| The input choosers | `Choose file...` and `Choose folder...` side by side | both in the input row, tops at 286px | matches |
| The format tag, CSV chosen | `CSV` | `CSV`, colour `rgb(143, 207, 242)` on `rgb(18, 34, 43)` | matches |
| The format tag, text chosen | `TEXT` | `TEXT` | matches |
| The format tag, M3U chosen | `M3U` | `M3U` | matches |
| The format tag, folder chosen | `FOLDER` | `FOLDER` | matches |
| The CSV note | names Artist and Title as required and Album, Duration, File name as optional | `CSV columns.Artist and Title are required. Album, Duration and File name are optional and help a row match more strictly.` as innerText, the lead and the sentence in two inline elements | matches |
| The template control | `Download CSV template`, at the note's right edge | its right edge 14px inside the note's, the note's 13px padding and 1px border | matches |
| The downloaded template | the bytes `csv_template_bytes()` returns | file name `playlist-template.csv`; bytes `efbbbf4172746973742c5469746c652c416c62756d2c4475726174696f6e2c46696c65206e616d650d0a`, equal to `csv_template_bytes().hex()` | matches |
| The target-folder input | absent | the page's inputs are `Playlist name` and the two switches | matches |
| The output-folder chooser, nothing chosen | the base collection's folder, named as the default | `The base collection's folder` before a base; `...\bp_fixture\lib (the base collection's folder)` after one | matches |
| The output-folder chooser, folder chosen | the chosen path | `...\bp_fixture\exports` | matches |
| The playlist-folder chooser, Full collection off | disabled at `Collection root`, `Playlist folder applies only with Full collection on. Off, the file holds this one playlist at its root.` under it | `q-field--disabled`, `Collection root`, that note visible | matches |
| The output-folder chooser, Full collection off | enabled | `Choose folder...` not disabled | matches |
| The playlist-folder chooser, Full collection on | enabled, note hidden | not `q-field--disabled`, note not rendered | matches |
| The playlist-folder chooser's first option | `Collection root`, selected by default | `Collection root`, `q-item--active` | matches |
| The playlist-folder chooser's folder options | the base's folder paths in tree order | `Sets`, `Sets\2026`, `Sets\Warmup ...`, `Archive`, `Archive\Warmup ...` | matches |
| The duplicate-name folder option | listed with its path and `(name also used elsewhere)`, disabled and not selectable | both `Warmup` options `aria-disabled="true"`; clicking `Sets\Warmup` left the value at `Collection root` and the menu open | matches |
| The report card's title | `Unresolved entries` | `Unresolved entries`, one row `4`, `Nobody,Nothing`, `unmatched` | matches |
| The footer after the aborted run | `Not written: N entries did not resolve and Allow unmatched is off. Read as CSV, <codec>.` | `Not written: 1 entry did not resolve and Allow unmatched is off. Read as CSV, utf-8-sig.` | matches |
| The footer after the written CSV run | `Written: "<name>" with N tracks. Read as ...` | `Written: "Warehouse" with 2 tracks. Read as CSV, utf-8-sig.` | matches |
| The footer after the text run | no read note | `Written: "TextSet" with 2 tracks.` | matches |
| The footer after the M3U run | the format and codec | `Written: "M3uSet" with 2 tracks. Read as M3U, utf-8-sig.` | matches |
| The footer after the folder run | the format alone | `Written: "FolderSet" with 2 tracks. Read as Folder.` | matches |
| The written file's location | `<output folder>\<name>.nml`, no directory named after the playlist folder | logged write to `...\bp_fixture\exports\Warehouse.nml`, 2203 bytes; no `Sets` or `2026` directory under the fixture | matches |
| The written playlist's placement | under the chosen FOLDER in the file's playlist tree | `Sets` > `2026` > `PLAYLIST Warehouse`, 2 entries | matches |
| The written file against the CLI | the CLI's bytes for `--target-folder 2026 --full-collection --allow-unmatched` | equal once each playlist `UUID` is masked; the served run's UUID was not fixed | matches |
| Button fills | every neutral button on the action blue; the disabled primary on the off ground | five `wizard-control-fill` buttons `rgb(86, 180, 233)`; `Write playlist` disabled `rgb(21, 23, 26)` | matches |
| The chooser after Full collection turned off again | reset to `Collection root`, disabled, note shown | `Collection root`, `q-field--disabled`, note visible | matches |
| Document scroll | none | `scrollWidth` 1280 and `scrollHeight` 900 against a `1280x900` viewport, with the report card shown and hidden; no element with `overflow-y` auto or scroll overflowing | matches |

## Structural verdicts

- **The input card.** The page composes the artboard's input `.lblrow` as
  a `wizard-label` over one `buildplaylist-input-row` holding the path,
  the `.fmt` tag and both choosers, and the `.note` as a `wizard-callout`
  with its lead and the template control at its right edge: matches. The
  artboard draws each path in a bordered `.field`; the page shows the path
  as mono text with no field box, which differs and is not recorded under
  Composition not built.
- **The folder row.** Output folder and Playlist folder sit side by side
  in `buildplaylist-folder-row`, seen on a screenshot and not measured.
  The playlist folder is a Quasar `q-select` with a floating label rather
  than the artboard's `.lbl` over a `.field`, and its open list is Quasar's
  menu rather than the artboard's `.menu`: differs in drawing, matches in
  content and in which options are disabled.
- **The report card.** The title matches. The artboard's `table.rep`, with
  `#`, `Entry` and `Kind` headers, a `.kind` badge per row and the
  read-only note under it, is not built: the page draws each row as three
  labels. That differs and is not recorded under Composition not built.
- **The page.** The artboard's `main` is two columns, the form beside a
  420px rail holding "How this differs from repair", the "Two different
  folders" note, the disabled chooser and the Buttons card. The page is one
  content column and draws none of the rail, the state the Column model
  entry under Composition not built records for the other screens.

## What this run does not establish

The native path is unread. In the `native=True` window the template goes
through `file_picker.pick_save_path` and `write_bytes_atomically`, and a
served page has no window for that dialog; `pick_save_path` was stubbed to
raise and was not reached. That path is held by
`tests/test_build_playlist_byte_identity.py` and
`tests/test_gui_file_picker_save.py` against stand-ins, not by a reading.

The playlist-folder chooser's disable is read on the served page against
NiceGUI 3.16, which hands the browser each option's label and index; the
predicate matches the label for that reason.

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

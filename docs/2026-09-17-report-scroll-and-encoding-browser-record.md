# Served-page record: the build-playlist report scrolled into view, and the encoding's display name

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

## How the run was taken

The wizard was served by a scratch script modelled on `serve_w002.py` in
the gate repository at `C:\codex\traktor-nml-tool-gate`, with
`native=False` on a free port (`52613`) and only `pick_file_or_folder`
stubbed: its first file call returned a scratch `base.nml`, every later
file call the scratch file named in a scratch `current_input.txt`, and a
folder call the scratch folder. The gate repository was read and not
written. The viewport is `1280x900` unless a row says `1280x700`.

`base.nml` is the collection `_base_nml()` in
`tests/test_build_playlist_text_parity.py` builds. Three CSV files were
written by Python:

- `refused.csv`: `csv_template_bytes()`, which carries a UTF-8
  byte-order mark, followed by the rows `Alpha,One` and `Nobody,Nothing`.
- `clean.csv`: the same template followed by `Alpha,One` and `Beta,Two`.
- `win.csv`: `Artist,Title`, `Alpha,One` and `Beyonc` plus U+00E9 plus `,Halo`, encoded
  with `cp1252`, so U+00E9 is the single byte `0xE9` and the file
  does not decode as UTF-8.

On `/build-playlist` the base `Choose file...` was clicked once, the
input `Choose file...` clicked again for each input, the playlist name
set to `Set`, `Allow unmatched lines` and `Full collection` left off, and
`Write playlist` clicked. Before each run a `scroll` listener was on
`.wizard-middle` and on `document`, and `.wizard-middle`'s `scrollTop`
was read or set to `0`; each reading was taken three seconds after the
click.

The runs, in order: `refused.csv` at `1280x900`, `clean.csv` at
`1280x900`, `clean.csv` at `1280x700`, `refused.csv` at `1280x700`,
`win.csv` at `1280x900`.

The readings are taken on `0d43fd4` plus this change: `write_playlist`
calling `ui.run_javascript` with `scrollIntoView` on the report card when
the run leaves rows, and the footer naming the encoding through
`buildplaylist_view.encoding_label` (ref: DL-303). No before pass was
taken here. The server was stopped after the runs.

The footer rows of
`docs/2026-09-16-build-playlist-inputs-browser-record.md` read
`utf-8-sig` on the aborted CSV, written CSV and M3U runs. That record
stands as its run left it; this record's footer rows supersede those
readings of the encoding's name.

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| Refused run at `1280x900`: the middle's scroll | scrolls to bring the card into view | `.wizard-middle` `scrollTop` `0` before the click, `30.799999237060547` after; `scrollHeight` `780` before and `811` after against `clientHeight` `780`; one `scroll` event on `.wizard-middle` | matches |
| Refused run at `1280x900`: the card's box | inside the middle's visible area | card top `705.5875244140625`, bottom `830.0375289916992`, left `120.4`, width `1024`; the middle's box top `56`, bottom `836` | matches |
| Refused run at `1280x900`: the card at the middle's top | below the fold without the scroll | with `scrollTop` set back to `0` after the run, card top `736.3875122070312`, bottom `860.837516784668`, past the middle's bottom `836` | matches |
| Refused run at `1280x900`: the document | unscrolled | `document.scrollingElement.scrollTop` `0`, `scrollHeight` `900`, `scrollY` `0`; no `scroll` event on `document` | matches |
| Refused run at `1280x900`: the report | one unmatched row | one row, `3 \| Nobody,Nothing \| unmatched` | matches |
| Refused run at `1280x700`: the middle's scroll | scrolls to bring the card into view | `scrollTop` `0` before, `230.8000030517578` after; `scrollHeight` `811` against `clientHeight` `580`; one `scroll` event on `.wizard-middle` | matches |
| Refused run at `1280x700`: the card's box | inside the middle's visible area | card top `505.5874938964844`, bottom `630.0374984741211`; the middle's box top `56`, bottom `636` | matches |
| Refused run at `1280x700`: the document | unscrolled | `scrollTop` `0`; no `scroll` event on `document` | matches |
| Clean run at `1280x900` | no scroll | `scrollTop` `0` before and after; `scrollHeight` `811` before the click with the previous run's card shown, `780` after; no `scroll` event; the report `display` `none`; document `scrollTop` `0` | matches |
| Clean run at `1280x700` | no scroll where the middle can scroll | `scrollTop` `0` before and after with `scrollHeight` `670` against `clientHeight` `580`; no `scroll` event; document `scrollTop` `0` | matches |
| Footer, `refused.csv` (UTF-8 with a byte-order mark) | `Read as CSV, UTF-8.` | `Not written: 1 entry did not resolve and Allow unmatched is off. Read as CSV, UTF-8.` | matches |
| Footer, `clean.csv` (UTF-8 with a byte-order mark) | `Read as CSV, UTF-8.` | `Written: "Set" with 2 tracks. Read as CSV, UTF-8.` at `1280x900` and at `1280x700` | matches |
| Footer, `win.csv` (cp1252) | `Read as CSV, Windows-1252.` | `Not written: 1 entry did not resolve and Allow unmatched is off. Read as CSV, Windows-1252.`; the report row `3 \| Beyonc<U+00E9>,Halo \| unmatched` with U+00E9 drawn; `scrollTop` `0` before, `30.799999237060547` after; card top `705.5875244140625`, bottom `830.0375289916992`; document `scrollTop` `0` | matches |

## What this run establishes

**A refused run brings the report card into view by scrolling the middle
region.** At both heights `.wizard-middle`'s `scrollTop` moved to its
maximum, `scrollHeight` less `clientHeight`, and the card's box stood
inside the middle's. At `1280x900` the card with the middle unscrolled
stands past the fold by `24.8`, which is the user's report at this
viewport.

**The document does not move.** Its `scrollTop` read `0` after every
run and no `scroll` event reached it, so the shell's scroll owner is
still `.wizard-middle` alone.

**A run with no unresolved rows does not scroll.** At `1280x700` the
middle had `90` of overflow to scroll and read `0` with no event after
the clean run. The `1280x900` clean run cannot show this on its own:
once the card hides, the middle has no overflow.

**The footer names the encoding as UTF-8 and Windows-1252.** A
template CSV read `UTF-8` and a cp1252 file read `Windows-1252`, and the
cp1252 file's U+00E9 was drawn in the report.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| The footer's read note | `Specs.dc.html:227`'s `.ft-note`, amended to `Read as CSV, Windows-1252.` | the footer note ending `Read as CSV, Windows-1252.` for a cp1252 file and `Read as CSV, UTF-8.` for a UTF-8 file | matches |
| The report card's place | `:175`'s `Unresolved entries` card after the form card inside `main` | the `Unresolved entries` section after the form card inside `.wizard-middle`, brought into view by the middle's scroll rather than moved | matches |

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The shipped `native=True` entry point is not read here.

**The smooth scroll's motion was not read.** The call asks for
`behavior: 'smooth'`, and each run recorded one `scroll` event on the
middle; whether the pane animated the scroll was not read.

**No report taller than the middle was read.** Every refused run left
one row, and at both heights the scroll stopped at the middle's maximum
before the card's top reached the middle's top, so `block: 'start'`
aligning a card to the middle's top was not read.

**No M3U run was read.** The M3U reader's `utf-8-sig` and `cp1252` pass
through the same `encoding_label` as the CSV reader's.

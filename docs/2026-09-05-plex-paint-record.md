# Served-page record: the wizard paints IBM Plex

The first record written under DL-084 as DL-169 amends it, so it carries
a structural reading beside its atom readings.

Served from `.venv` at `http://localhost:8000` with `native=False`,
driven in the browser pane. `traktor_nml/gui/theme.py` names IBM Plex in
`FONT_SANS` and `FONT_MONO`; this run asks whether the page paints it.

## What was opened

`/`, the reconstruct page. Both routes share `_page_chrome`, which is
where the mount and the stylesheet are applied, so the faces reach
`/reconnect` by the same call.

## The faces the page loaded

`document.fonts` after `await document.fonts.ready`:

| Face | Status |
|---|---|
| IBM Plex Sans 400 | loaded |
| IBM Plex Sans 500 | loaded |
| IBM Plex Sans 600 | loaded |
| IBM Plex Sans 700 | loaded |
| IBM Plex Mono 400 | unloaded at first read, loaded after `document.fonts.load` |
| IBM Plex Mono 500 | loaded |
| IBM Plex Mono 600 | loaded |

Seven faces declared, seven present. Mono 400 reads `unloaded` on the
first pass because no element on `/` had yet demanded it; a
`document.fonts.load('400 11.5px "IBM Plex Mono"')` brings it to
`loaded`, which is the lazy behaviour rather than a missing file.

Every face was fetched from the application's own origin, each `200 OK`:

```
GET http://localhost:8000/fonts/IBMPlexSans-Regular.woff2   -> 200 OK
GET http://localhost:8000/fonts/IBMPlexSans-Medium.woff2    -> 200 OK
GET http://localhost:8000/fonts/IBMPlexSans-SemiBold.woff2  -> 200 OK
GET http://localhost:8000/fonts/IBMPlexSans-Bold.woff2      -> 200 OK
GET http://localhost:8000/fonts/IBMPlexMono-Regular.woff2   -> 200 OK
GET http://localhost:8000/fonts/IBMPlexMono-Medium.woff2    -> 200 OK
GET http://localhost:8000/fonts/IBMPlexMono-SemiBold.woff2  -> 200 OK
```

No request reached a network host. The only other font request in the
run is nicegui's own `/_nicegui/3.16.0/static/fonts/...`, served from
the same origin.

## Atom verdicts

The reading that recorded the defect was a width comparison against
known families: the sans stack drew a test string at exactly Segoe UI's
width, and the mono stack at exactly Consolas'. Re-taken here.

| Surface | The reading that recorded the defect | Read off the page | Verdict |
|---|---|---|---|
| Body sans stack | `485.5078125px`, identical to `"Segoe UI"` and `system-ui` | `515.31982421875px`, and `"Segoe UI"` still measures `485.5078125px` on the same page | matches |
| `.wizard-brand` mono, rendered element | the stack measuring as Consolas | `55.203125px` against Consolas' `50.59375px` for the same string at the same size | matches |
| Body `font-family` | `"IBM Plex Sans", system-ui, -apple-system, sans-serif` | unchanged - the stack was always right; what changed is that its first entry now resolves | matches |
| Emitted `@font-face` blocks | seven | seven, one per `FONT_FACES` entry | matches |

The mono reading is taken from a rendered element rather than from
`canvas.measureText`. Canvas does not trigger a font load, so an
unloaded face measures as the next entry in the stack: the canvas read
of the mono stack returned Consolas' `615.78125px` while the element
beside it was painting Plex. A canvas width is a sound reading only for
a face already loaded, which is why the element reading is the one
recorded here.

## Structural verdicts

Stated under the amended DL-084 (DL-169). This run measured the
typeface, which is an atom of every surface rather than a surface of its
own; it changed no composition and none was expected of it. The
structures below are read against the reconnect wizard's artboards and
carry the verdicts the three earlier records carry, unchanged by this
work.

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| App shell | `.app` grid, rows `56px 1fr 64px` | a header row and one column, the page scrolling as a document | differs |
| Column model | `main` at `1fr 400px` | one column at `.wizard-content-width` | differs |
| Card structure | `.card` + `.card-h` + `.card-b`, three to four per screen | `.wizard-surface` applied once to the whole column | differs |
| Table geometry | `.gr` at `126px minmax(0, 1fr) 100px 196px 134px` under a `.th` header row | `.wizard-row`, a flex row with a gap; no column aligns row to row | differs |
| Footer band | `.ft`, 64px, note left and actions right | actions inline as the column's last children | differs |
| Detail rail | `.det`, a 400px bordered panel | the candidate panel, in the same column below the table | differs |

Each names an entry under "Composition not built" in
`traktor_nml/README.md`.

## What this run does not establish

The faces are read on `/` only. `/reconnect` shares `_page_chrome` and
therefore the mount and the stylesheet, but no reading was taken there.

Nothing here exercises the wheel or the frozen build. That the fonts
directory reaches both is asserted from `pyproject.toml` and the
PyInstaller spec by guard, not by building either and serving it.

The run was served with `native=False` to make the page drivable. The
shipped entry point runs `native=True`, and the font mount is applied
from `_page_chrome` in both, so the difference is the window rather than
the route.

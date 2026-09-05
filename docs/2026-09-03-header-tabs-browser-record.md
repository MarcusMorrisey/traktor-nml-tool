# Served-page record: the app header and its section tabs

The DL-084 served-page run for the header and the two section tabs, taken
2026-09-03 against `C:\codex\traktor-nml-tool` at `1fed6e7` with the gate's
`serve_w002.py` on port 8115, which stubs the native file chooser and otherwise
serves whatever `app.py` registers.

Every reading below was taken off the served DOM through the browser pane -
`getComputedStyle` for the paint, `getAttribute` for the markup - rather than
from `app.py`'s source. A guard reading source cannot see a class Quasar's own
layers overrode, which is why DL-086's ladder exists and why this record is the
milestone's acceptance step.

## What was opened

| URL | Status |
|---|---|
| `http://localhost:8115/` | 200 OK |
| `http://localhost:8115/reconnect` | 200 OK |
| `http://localhost:8115/reconstruct` | 404 Not Found |

The 404 is the framework's own response to a path nothing registers, served as
NiceGUI's page rather than as an application screen: nothing routes
`/reconstruct` and no redirect stands in for it, so the address answers as any
unregistered path does (DL-141). Its body opens `<!doctype html>` with
`<title>NiceGUI</title>`.

## `/` - the reconstruct page

| Surface | Read | Expected | Verdict |
|---|---|---|---|
| header anchors | 2 | 2 | matches |
| anchor hrefs in order | `['/', '/reconnect']` | `['/', '/reconnect']` | matches |
| href carrying `aria-current="page"` | `['/']` | `['/']` | matches |
| href carrying `wizard-tab-selected` | `['/']` | `['/']` | matches |
| selected tab background | `rgb(34, 38, 42)` | `theme.SURFACE_4` `#22262A` | matches |
| selected tab colour | `rgb(232, 235, 237)` | `theme.TEXT` `#E8EBED` | matches |
| selected tab weight | `600` | 600 | matches |
| selected tab inset rule | `rgb(60, 66, 72) 0px 0px 0px 1px inset` | `theme.BORDER_STRONG` `#3C4248` | matches |
| unselected tab colour | `rgb(142, 151, 158)` | `theme.TEXT_FAINT` `#8E979E` | matches |
| unselected tab background | `rgba(0, 0, 0, 0)` | none of its own | matches |
| anchors outside the header | `[]` | none | matches |

## `/reconnect` - the reconnect wizard

| Surface | Read | Expected | Verdict |
|---|---|---|---|
| header anchors | 2 | 2 | matches |
| anchor hrefs in order | `['/', '/reconnect']` | `['/', '/reconnect']` | matches |
| href carrying `aria-current="page"` | `['/reconnect']` | `['/reconnect']` | matches |
| href carrying `wizard-tab-selected` | `['/reconnect']` | `['/reconnect']` | matches |
| selected tab background | `rgb(34, 38, 42)` | `theme.SURFACE_4` `#22262A` | matches |
| selected tab colour | `rgb(232, 235, 237)` | `theme.TEXT` `#E8EBED` | matches |
| selected tab weight | `600` | 600 | matches |
| selected tab inset rule | `rgb(60, 66, 72) 0px 0px 0px 1px inset` | `theme.BORDER_STRONG` `#3C4248` | matches |
| unselected tab colour | `rgb(142, 151, 158)` | `theme.TEXT_FAINT` `#8E979E` | matches |
| unselected tab background | `rgba(0, 0, 0, 0)` | none of its own | matches |
| anchors outside the header | `[]` | none | matches |

The wizard page holds no anchor into the reconstruct page outside the header:
the tab strip is the whole of the navigation between the two operations, and
the link that once sat below the stepper is gone.

## The tab strip navigates

Clicking `Reconstruct playlists` from `/reconnect` left `location.pathname`
reading `/`, with `aria-current="page"` on the `/` anchor and on no other. A
tab is an anchor whose `href` is that operation's route, so following one is a
page load and each operation keeps the address it is reachable by (DL-132).

## The window title

`__main__.py:19` reads `ui.run(title="traktor-nml-tool", native=True,
reload=False)`. The window holds both operations and the selected tab names the
open one, so a title naming either operation contradicts the header on the
other route (DL-140). The reading here is the source line rather than a window
capture: this run served the page over HTTP, and a native launch opens a
pywebview window the browser pane cannot read.

## What this run does not establish

- The paint was read on this machine's browser at one viewport. Nothing here
  states how the strip reflows on a narrow window.
- Accessibility work is out of scope for this version, so no screen reader was
  run against the header and none is to be. `aria-current` is read here as
  markup, not as anything a screen reader announced.
- The four wizard steps, the conflict screen and the write controls were not
  re-driven; this run reads the header and the routes.

## Structural verdicts

Stated under the amended DL-084 (DL-169), which requires a structural
reading - app shell, column model, card structure, table geometry -
beside the atom readings a surface carries. This run measured atoms.
The rows below state, per surface it covered, what it did not measure
and what the served page composes, read against the artboards rather
than re-run. Every atom reading above stands exactly as this run
recorded it (DL-171). Each differs entry names an entry under
"Composition not built" in `traktor_nml/README.md`.


This run opened both routes. The reconstruct page at `/` is outside
the structural gate (DL-172): no artboard draws it, and `Specs.dc.html`
- which governs under DL-088 - specifies its behaviour and no
composition, so there is no drawn structure to read a verdict against.
That is a gate exclusion, not a missing verdict.

The `/reconnect` route this run also opened carries the structural
readings recorded against the wizard's artboards in the three records
above; this run measured the header band and the tab strip, which are
atoms of the shell rather than the shell itself.

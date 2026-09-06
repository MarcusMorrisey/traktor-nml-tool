# Served-page record: the three structures at the moment their entries are struck

Written under DL-084 as DL-169 amends it, so it carries a structural
reading per surface beside its atom readings.

Served from `.venv` at `http://localhost:8000` with `native=False`,
driven in the browser pane at a 1280x900 viewport, with the App shell,
Card structure and Footer band entries absent from "Composition not
built" in `traktor_nml/README.md`. An entry there ends by being built,
so the reading that ends it is taken against the section as it stands
rather than against the section that still held it.

## What was opened

`/`, the reconstruct page, and `/reconnect` on the Set up step. The
three structures below are built in `_page_chrome`, which both routes
call, so each is read on both.

## Atom verdicts

| Surface | Expected | Read off the page | Verdict |
|---|---|---|---|
| Header height | `56px` | `56px` on both routes | matches |
| Footer height | `64px` | `64px` on both routes | matches |
| Middle fills the page | the viewport's width | `1280px` on both routes | matches |
| Card width and placement | one centred column | each of the four cards on `/` is `1024px` at `x=128` | matches |
| Footer note position | the band's left inset | `x=24` on both routes | matches |
| The single-box rule is gone | no element carries it | zero `.wizard-surface` elements on either route | matches |

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| App shell | `.app` grid, rows `56px 1fr 64px`, only the middle scrolling | header `56px`, footer `64px`, the middle between them at the full `1280px`; on `/` the document does not scroll, and on `/reconnect` the middle scrolls while the document does not | matches |
| Card structure | `.card` + `.card-h` + `.card-t` + `.card-b` | four cards on `/` - "The collection to repair", "Collections to take playlists from", "Where the output goes", "Where the collections disagree" - each carrying a head, a title and a body; one per rendered step on `/reconnect` | matches |
| Footer band | `.ft`, `.ft-note` left and `.ft-act` right | the note at `x=24` and the visible actions at the right on both routes: `PREVIEW` and `WRITE OUTPUT` on `/`, `CONTINUE` on `/reconnect` | matches |
| Column model | `main` at `1fr 400px` | one column; no second column on either route | differs |
| Table geometry | `.gr` under a `.th` header row | `.wizard-row`, a flex row with a gap; no header row | differs |
| Detail rail | `.det`, a 400px bordered panel | zero elements composing a rail; the candidate panel is in the same column below the table | differs |

The three `matches` rows are the three entries this milestone strikes.
The three `differs` rows name the entries that stand, and each is
recorded under "Composition not built".

## What this run does not establish

The keyboard ring is not re-walked here; it is read in
`docs/2026-09-06-wizard-focus-order-browser-record.md`, and nothing
between that run and this one changes the DOM.

`/reconnect` is read on the Set up step alone, so the card reading
covers the one step the stepper renders. The other three steps build
their cards from the same builders and are not opened.

Nothing here exercises the wheel or the frozen build. The run was
served with `native=False`; the shipped entry point runs `native=True`
and builds the same chrome.

# Served-page record: the wizard shell

Written under DL-084 as DL-169 amends it, so it carries a structural
reading per surface beside its atom readings.

Served from `.venv` at `http://localhost:8000` with `native=False`,
driven in the browser pane at a 1280x900 viewport. Both routes were
opened. This run asks whether the shell the artboards draw - a header
band, a middle that scrolls on its own, a footer band, and cards with
their own head and body - is the shell the page composes.

Every length below is read off the live page. The pane's device pixel
ratio is 2.5, so a declared `1px` border reads back as `0.8px`
computed; that is the ratio and not a disagreement, and it is stated
once here rather than at each row.

## What was opened

`/reconnect`, the reconnect wizard, against
`design/reconnect-wizard/Main.dc.html`; and `/`, the reconstruct page,
whose atoms are read here and whose structure is not verdicted
(DL-172: no artboard draws it).

## Atom verdicts

### The two bands

| Surface | The artboard draws | Read off the page | Verdict |
|---|---|---|---|
| Header height | `.app` row one at `56px` | `56px`, `position: fixed` | matches |
| Header padding | `.hd` at `0 24px` | `0px 24px`; the brand begins at `x=128` | matches |
| Header ground and rule | `#17191C` under a `1px` `#2A2E32` bottom border | `rgb(23, 25, 28)`, `0.8px solid rgb(42, 46, 50)` | matches |
| Header direction and alignment | a centred row | `flex-direction: row`, `align-items: center` | matches |
| Footer height | `.app` row three at `64px` | `64px`, `position: fixed` | matches |
| Footer padding | `.ft` at `0 24px` | `0px 24px` | matches |
| Footer ground and rule | `#17191C` under a `1px` `#2A2E32` top border | `rgb(23, 25, 28)`, `0.8px solid rgb(42, 46, 50)` | matches |
| Footer distribution | note left, actions right | `justify-content: space-between`; note at `x=24`, actions ending `24px` from the right | matches |

### The middle

| Surface | Expected | Read off the page | Verdict |
|---|---|---|---|
| Owns the scroll | the middle scrolls, the document does not | `overflow-y: auto`; middle `scrollHeight 943` against `clientHeight 780`, document `900` against `900` | matches |
| Fills the page | full viewport width | `1280px` at `x=0`, `align-self: stretch` | matches |
| Padding and gap | `22px 24px 6px`, `20px` between children | `22px 24px 6px`, `gap: 20px` | matches |

### The card triplet

Read against `Main.dc.html:32-35`.

| Surface | The artboard draws | Read off the page | Verdict |
|---|---|---|---|
| `.card` ground, border, radius | `#17191C`, `1px #2A2E32`, `8px` | `rgb(23, 25, 28)`, `0.8px solid rgb(42, 46, 50)`, `8px` | matches |
| `.card-h` padding and rule | `11px 15px` under a bottom border | `11px 15px`, `0.8px solid rgb(42, 46, 50)`, `align-items: center` | matches |
| `.card-t` weight, size, margin | `600`, `13px`, `margin: 0` | `600`, `13px`, `0px` | matches |
| `.card-b` padding, direction, gap | `15px`, column, `12px` | `15px`, `column`, `12px` | matches |
| Column width owner | one width owner | every card `1024px` at `x=128`, its `max-width` `1024px` from `.wizard-content-width`; no band, middle or card rule declares a width | matches |

### The footer's step groups

| Surface | Expected | Read off the page | Verdict |
|---|---|---|---|
| One step's actions visible | the active step's advancing action alone | on the Set up step, one visible group holding `CONTINUE`; the Scan group (`Cancel`, `Start scan`, `Review matches`), the Review group (`Back`, `Continue to write`) and the Write group all `display: none` | matches |
| One note visible | the active step's sentence | one visible `.wizard-footer-note`: "Continue reads the collection and moves on to the scan." | matches |
| The reconstruct page fills the band | its own controls in the band | note "Preview reads the collections; Write output writes a new file."; visible actions `PREVIEW`, `WRITE OUTPUT` | matches |

## Structural verdicts

Read against the reconnect wizard's artboards. Three of the six
entries under "Composition not built" in `traktor_nml/README.md` are
in this milestone's scope; the other three are named so the record
says what still stands rather than falling silent on them.

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| App shell | `.app` grid, rows `56px 1fr 64px`, only the middle scrolling | `.nicegui-header` fixed at `56px` and `.nicegui-footer` fixed at `64px`, both `1280px` at `x=0`; `.wizard-middle` between them at `1280x780`. The document does not scroll - `scrollHeight` and `clientHeight` are both `900` - and the middle does: `943` against `780` | matches |
| Card structure | `.card` + `.card-h` + `.card-t` + `.card-b`, three to four per screen | four `.wizard-card` boxes on `/`, each carrying a `.wizard-card-head`, a `.wizard-card-title` and a `.wizard-card-body`; one per rendered step on `/reconnect`, which is one at a time because the stepper renders the active step alone. No `.wizard-surface` element remains on either route | matches |
| Footer band | `.ft`, 64px, `.ft-note` left and `.ft-act` right | `.nicegui-footer` at `64px`, `justify-content: space-between`, `padding: 0px 24px`; the note begins at `x=24` and the visible action group ends `24px` from the right edge | matches |
| Column model | `main` at `1fr 400px` | one column: every `.wizard-card` on `/` is `1024px` at `x=128`, centred in the page, with no second column | differs |
| Table geometry | `.gr` at `126px minmax(0, 1fr) 100px 196px 134px` under a `.th` header row | `.wizard-row`, a flex row with a gap; no column aligns row to row, and neither table carries a header row | differs |
| Detail rail | `.det`, a 400px bordered panel | the candidate panel, in the same column below the table | differs |

The three `differs` rows are unchanged by this work and name entries
that stand open in `traktor_nml/README.md`.

## The defect this run found

`.wizard-middle` was read at `775px` in a `1280px` viewport, at `x=0`,
with the first card `627px` at `x=84` - the column neither filling the
page nor centred in it. The cause is in the DOM rather than in the
rule: `.wizard-middle`'s parent is `.nicegui-content`, which nicegui's
own `static/nicegui.css` sets to `display: flex; flex-direction:
column; align-items: flex-start` at lines 14-28. A flex child under
`align-items: flex-start` takes its content's width, so the middle
shrank and the centred card centred inside the shrunken box.

`.wizard-middle` carries `align-self: stretch` against that default,
and the same reading now returns `1280px` at `x=0`.

Every guard in the suite was green across that defect, and none could
have been otherwise: they read the emitted stylesheet and `app.py`'s
source text, and the rule they read was correct in isolation. What was
wrong was the width the browser resolved for it under a parent rule
neither file names. That is the reading this gate exists to take
(DL-084).

## What this run does not establish

The keyboard ring, the focus order and the announcements are not read
here. The advancing controls moved from the column into the band, which
moves them in the DOM, and the reading that covers it is the record
DL-197 requires.

Nothing here exercises the wheel or the frozen build.

The run was served with `native=False` to make the page drivable. The
shipped entry point runs `native=True`, and the shell is built in
`_page_chrome` in both, so the difference is the window rather than the
composition.

One observation carrying no verdict: the container the chrome hands to
the routes carries `wizard-footer-actions`, and so does each step's
group nested inside it, so the class matches five elements on the
wizard route rather than four. Both are the same flex row and the page
reads correctly; a guard counting that class counts the container too.

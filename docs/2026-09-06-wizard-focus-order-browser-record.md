# Served-page record: focus order after the actions move to the band

Written under DL-084 as DL-169 amends it, so it carries a structural
reading per surface beside its atom readings.

Served from `.venv` at `http://localhost:8000` with `native=False`,
driven in the browser pane. The advancing controls are built in the
footer band rather than as the last children of the page column, which
moves them in the DOM; the tab ring follows DOM order, so this run
re-takes the keyboard reading the shell changed.

## What was opened

`/reconnect` on the Set up step, and `/` for its own ring. Both share
`_page_chrome`, so both take the same header, middle and footer order.

## Atom verdicts

| Surface | Expected | Read off the page | Verdict |
|---|---|---|---|
| Focus ring colour and width | `FOCUS_RING`, `2px solid` `TEXT` | `rgb(232, 235, 237) solid 2px` on the focused band control | matches |
| Focus ring offset | `FOCUS_RING_OFFSET`, `2px` | `2px` | matches |
| No author tab order | no positive `tabindex` anywhere | every stop reads `tabIndex 0`; the count of stops with `tabIndex > 0` is zero | matches |

## Structural verdicts

| Structure | Expected | Read off the page | Verdict |
|---|---|---|---|
| Ring order | header, then the page's own controls, then the advancing action | `/reconnect`: header, header, middle x6, footer. `/`: header, header, middle x5, footer x2. The regions appear in the order header, middle, footer on both, with no region re-entered | matches |
| The advancing action is last | the band's action is the ring's final stop | `/reconnect`: stop 9 of 9 is `CONTINUE` in the footer. `/`: stops 8 and 9 of 9 are `PREVIEW` and `WRITE OUTPUT` | matches |
| Nothing hidden is reachable | a step group that is not the active one is out of the ring | the Scan, Review and Write groups are `display: none`; zero footer buttons are display-visible yet unreachable, and zero hidden buttons appear in the walk. The ring holds 9 stops against 14 footer buttons present in the DOM | matches |
| Announcement regions | one polite and one assertive, created once per page load | two `aria-live` elements, `polite`/`role=status` and `assertive`/`role=alert`, both in the middle, both empty at load | matches |
| Section marking | the active route alone carries `aria-current` | one element carries it: `Reconnect wizard`; the nav is labelled `Sections` | matches |

## The ring as walked

Nine real `Tab` presses from page load on `/reconnect`:

| Stop | Region | Control |
|---|---|---|
| 1 | header | Reconstruct playlists |
| 2 | header | Reconnect wizard |
| 3 | middle | CHOOSE COLLECTION FILE... |
| 4 | middle | ADD SCAN ROOT... |
| 5 | middle | the tag cache path field |
| 6 | middle | Refresh cache (discard prior scan work) |
| 7 | middle | Enable acoustic fingerprinting |
| 8 | middle | CHOOSE OUTPUT FOLDER... |
| 9 | footer | CONTINUE |

The band sits last in the DOM as well as at the bottom of the screen,
so the ring reaches the advancing action after the controls that feed
it. That is the order the column gave before the action moved, and the
move preserves it rather than restoring it by an author `tabindex`.

## A reading that is sound only when taken by keyboard

Focusing the band's control from script and reading `outline` returned
`rgb(15, 17, 19) none 0px` - no ring - while the same control focused
by a real `Tab` press returned `rgb(232, 235, 237) solid 2px` and
matched `:focus-visible`. The ring is a `:focus-visible` rule, and
programmatic focus does not always satisfy it, so a scripted focus
reads the unfocused outline and looks like a missing ring.

The keyboard reading is the one recorded above. This is the same shape
as the canvas measurement in
`docs/2026-09-05-plex-paint-record.md`: an instrument that does not
trigger the behaviour it is measuring reports the state before it.

## What this run does not establish

No screen reader was run. The regions' presence, their `aria-live`
values and their roles are read here; what a screen reader announces
from them is not, and NVDA is out of scope for this version.

The ring is walked on the Set up step alone. The Scan, Review and Write
steps register their own groups, and those groups are `display: none`
here; their rings are not walked, though the mechanism that hides them
is the one read above.

Nothing here exercises the wheel or the frozen build. The run was
served with `native=False`; the shipped entry point runs `native=True`
and builds the same chrome from `_page_chrome`.

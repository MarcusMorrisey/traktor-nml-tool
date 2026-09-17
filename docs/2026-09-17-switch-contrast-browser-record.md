# Served-page record: the switch against the artboard's switch

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboard that draws it.

The two switches on `/build-playlist`, `Allow unmatched lines` and
`Full collection`, are Quasar `q-toggle`s. `Main.dc.html:54`-`57` draws
the switch this project's screens carry, and `Preview.dc.html:54`-`57`
repeats it.

## How the run was taken

The wizard was served by a scratch script modelled on `serve_w002.py` in
the gate repository at `C:\codex\traktor-nml-tool-gate`, with
`native=False` on a free port (`8121`) and nothing stubbed: both
switches are on the page before any file is picked. The gate repository
was read and not written. The viewport read back as `innerWidth` `1024`
and `innerHeight` `768`, and `devicePixelRatio` read `2.5`, which is why
a `1px` border resolves to `0.8px` in `getComputedStyle`. The
declarations themselves were read back off the rules through
`document.styleSheets` in the same call.

`Allow unmatched lines` was left off and `Full collection` clicked once,
so one run reads both states at once.

**The knob's travel was measured with its transition disabled.** The
knob is placed by `left` with a `0.22s` transition of Quasar's, and in
this browser pane every `CSSTransition` on the thumb reported
`playState` `running` with `currentTime` `0` for as long as it was
polled, so the animated value never advanced off its start. A
`.q-toggle__thumb { transition: none !important; }` rule was injected
for the readings, which reads the resting value the cascade computes
rather than a frame of the animation. The screenshot taken in the same
session therefore shows the on knob still at its start position; the
measured resting values below are what the page settles to.

The before pass was taken on the same served page by deleting the seven
switch rules out of `document.styleSheets` and injecting the two
declarations `theme.py` carried in their place,
`.q-toggle__thumb { background: #7E868D; }` and
`.q-toggle__track { background: #2E3338; }`, so both passes are one
page and one pixel ratio.

The readings are taken on `42b2e5a` plus this change: the switch's
geometry, its border and its on state declared in `theme.py` against
`Main.dc.html:54`-`57`, with the knob colour moved onto
`.q-toggle__thumb:after` (ref: DL-306). The server was stopped after the
run.

The verdict rows are what this record is registered by: their digest
stands in tests/test_docs_browser_record_structure.py, computed from
the record as the run left it (ref: DL-084, DL-169).

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| Before: the knob's box | a `13px` circle | `.q-toggle__thumb` `20px` by `20px` at `border-radius` `0px`, filled `rgb(126, 134, 141)`, with Quasar's own `rgb(255, 255, 255)` circle drawn inside it | differs |
| Before: the track's box | `34px` by `19px` inside a `1px` border | `32px` by `14px`, `border-top-width` `0px`, `border-radius` `7px` | differs |
| Before: the track's paint | `#2E3338` at full strength | `background-color` `rgb(46, 51, 56)` at `opacity` `0.38` off and `0.54` on | differs |
| Before: the on state's track | `#1B3D4E` inside `#2F5A72` | `rgb(46, 51, 56)`, the same colour the off track reads, at `opacity` `0.54` | differs |
| Off: the track's box | `34px` by `19px`, `10px` radius | `width` `34px`, `height` `19px`, `border-radius` `10px`, `box-sizing` `border-box` | matches |
| Off: the track's paint | `#2E3338` inside `1px` of `#3C4248`, undimmed | `background-color` `rgb(46, 51, 56)`, `border` `0.8px rgb(60, 66, 72)` for a rule declaring `1px solid rgb(60, 66, 72)`, `opacity` `1` | matches |
| Off: the knob's box | a `13px` circle, nothing square behind it | `.q-toggle__thumb` `13px` by `13px` with `background-color` `rgba(0, 0, 0, 0)`; its `::after` `border-radius` `50%` and `box-shadow` `none` | matches |
| Off: the knob's paint | `#7E868D` | `::after` `background-color` `rgb(126, 134, 141)` | matches |
| Off: where the knob sits | `2px` in from the track's left edge | `left` `2px`, `top` `2px`; measured gap to the track's left edge `2`, to its right edge `19` | matches |
| On: the track's paint | `#1B3D4E` inside `1px` of `#2F5A72`, undimmed | `background-color` `rgb(27, 61, 78)`, `border` `0.8px rgb(47, 90, 114)`, `opacity` `1` | matches |
| On: the knob's paint | `#56B4E9` | `::after` `background-color` `rgb(86, 180, 233)`, `border-radius` `50%` | matches |
| On: where the knob sits | `2px` in from the track's right edge | `left` `19px`; measured gap to the track's left edge `19`, to its right edge `2` | matches |
| On: the track's box | unchanged from off | `width` `34px`, `height` `19px`, `border-radius` `10px` | matches |
| The switch's own box | `34px` by `19px` with no padding of its own | `.q-toggle__inner` `width` `34px`, `min-width` `34px`, `height` `19px`, `padding` `0px` | matches |
| The rules on the page | seven, the artboard's switch in both states | the seven read back off `document.styleSheets`, the knob colour on `.q-toggle__thumb::after` and the two knob placements on `[dir="ltr"]`-prefixed selectors | matches |

## What this run establishes

**The knob is a circle with nothing square behind it.** The visible knob
is Quasar's `.q-toggle__thumb::after`, a `50%`-rounded box inside the
square `.q-toggle__thumb`. Painting the knob's grey on the square box
read `20px` by `20px` at `border-radius` `0px` in the before pass, which
is the square corner around the circle; painting it on the `::after`
reads a transparent `13px` box and a `50%`-rounded `rgb(126, 134, 141)`
circle.

**The track is not dimmed.** Quasar's `opacity: .38` read on the before
pass and `1` after, so `#2E3338` reaches the page at the value
`theme.py` holds rather than at 38 per cent of it over the ground.

**The two states are told apart by colour.** The before pass read
`rgb(46, 51, 56)` for the track in both states, differing only in
opacity; the after pass reads `rgb(46, 51, 56)` off and `rgb(27, 61, 78)`
on, with the knob `rgb(126, 134, 141)` off and `rgb(86, 180, 233)` on.

**The knob travels the full track.** With the transition disabled the
resting `left` reads `2px` off and `19px` on, which is the `34px` track
less the `13px` knob and the `2px` inset, so the measured gaps are `2`
and `19` off and `19` and `2` on.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| The switch's track | `Main.dc.html:54`'s `.sw`: `34px` by `19px`, `border-radius: 10px`, `background: #2E3338`, `border: 1px solid #3C4248` | `.q-toggle__inner` and `.q-toggle__track` sized and painted from `SWITCH_TRACK_WIDTH`, `SWITCH_TRACK_HEIGHT`, `SWITCH_TRACK_RADIUS`, `SWITCH_TRACK` and `BORDER_STRONG` | matches |
| The switch's knob | `Main.dc.html:55`'s `.sw i`: `13px` by `13px`, `border-radius: 50%`, `background: #7E868D`, `top: 2px; left: 2px` | `.q-toggle__thumb` sized from `SWITCH_KNOB_SIZE` and inset by `SWITCH_KNOB_INSET`, its `::after` painted `SWITCH_KNOB` | matches |
| The switch when on | `Main.dc.html:56`-`57`'s `.sw.on` and `.sw.on i`: `background: #1B3D4E`, `border-color: #2F5A72`, the knob `#56B4E9` at `right: 2px` | `.q-toggle__inner--truthy` rules painting the track `ACTION_TINT_BORDER` inside `ACTION_TINT_BORDER_ALT` and the knob `ACTION`, placed at `SWITCH_KNOB_ON_LEFT` | matches |

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so.

The shipped `native=True` entry point is not read here.

**The knob's travel was not read as an animation.** Every transition on
the thumb reported `currentTime` `0` in this pane, so the two resting
positions are what the readings measure and the `0.22s` slide between
them is not.

**The hover and focus ripple was not read.** Quasar draws it as
`.q-toggle__thumb:before` from `currentColor` and no rule here names it,
so what it paints over the knob is unread.

**The switches on the other routes were not read.** The rules are on the
`q-toggle` element rather than on a screen's class, so they reach every
switch the app builds; only `/build-playlist`'s two were measured.

**No switch was read at another width or another pixel ratio.** The
`0.8px` border is what `devicePixelRatio` `2.5` snaps a `1px`
declaration to.

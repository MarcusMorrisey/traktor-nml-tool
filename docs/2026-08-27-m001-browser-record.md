# M-001 browser record: Specs tokens, applied

Milestone M-001 of the reconnect-wizard visual pass, gated under DL-084.

The wizard was served over HTTP by a scratch driver outside the repository
(`build_wizard()` then `ui.run(native=False, port=8113)`) and opened in a
browser. Each value below is read off the served page with
`getComputedStyle`, against the value the artboard fixes.

Screens compared: `Main.dc.html`, `Scanning.dc.html`, `Results.dc.html`, and
`Confirm.dc.html` for its ground, surfaces and borders only — Confirm's
controls, focus behaviour and spacing are M-003's and are not read here.

## Surfaces

| Surface | Specs fixes | Read off the page | Verdict |
|---|---|---|---|
| Page ground (`body` background) | `#0F1113` | `rgb(15, 17, 19)` = `#0F1113` | matches |
| Foreground text (`body` color) | `#E8EBED` | `rgb(232, 235, 237)` = `#E8EBED` | matches |
| Wizard surface (`.wizard-surface`) | `#17191C` | `rgb(23, 25, 28)` = `#17191C` | matches |
| Stepper card (`.q-stepper`) | `#17191C` | `rgb(23, 25, 28)` = `#17191C` | matches |
| Stepper text (`.q-stepper` color) | `#E8EBED` | `rgb(232, 235, 237)` = `#E8EBED` | matches |
| Field text (`.q-field__native`) | `#E8EBED` | `rgb(232, 235, 237)` = `#E8EBED` | matches |
| Action control (`.q-btn`) | `#56B4E9` | `rgb(86, 180, 233)` = `#56B4E9` | matches |
| Body type step | `14px` | `14px` | matches |
| Palette activation | dark | `body` carries `body--dark` | matches |

Every entry reads `matches`, so no framework shortfall is recorded for this
milestone and nothing enters `traktor_nml/README.md` under DL-087.

## Status labels

The review table's status label is the one element the milestone gives both a
tinted tag surface and a status hue, so it is read separately. The class list
each status produces is injected into the served page and its computed values
read there, which exercises the same stylesheet, the same dark-mode
activation and the same `<head>` order the rendered table sees. This half of
the gate was run on port 8114.

| Status | Class list | Specs fixes | Read off the page | Verdict |
|---|---|---|---|---|
| matched | `wizard-tag-found` | `#A8D8CE` on `#12211D` | `rgb(168, 216, 206)` on `rgb(18, 33, 29)` | matches |
| ambiguous, refuted, format | `wizard-tag-review wizard-status-review` | `#F5D96B` on `#1F1D14` | `rgb(245, 217, 107)` on `rgb(31, 29, 20)` | matches |
| rejected | `wizard-tag-missing` | `#E8956E` on `#21160F` | `rgb(232, 149, 110)` on `rgb(33, 22, 15)` | matches |
| no match | `wizard-faint` | `#8E979E`, no tint | `rgb(142, 151, 158)`, `rgba(0, 0, 0, 0)` | matches |

Each label also computes `12px` from `text-xs` and `96px` from `w-24`, so
Tailwind's utilities are live on the served page and the `0,1,0` contention
the cascade guards are built around is real rather than assumed.

## What the gate caught

Three defects surfaced here that no source-reading guard saw, and all three
were fixed in the milestone's own diffs rather than worked around.

`ui.colors(dark=..., dark_page=...)` sets what Quasar's dark palette
contains; it does not activate it. Without activation the page carried
`body--light`, `.q-stepper` computed `rgb(255, 255, 255)` and
`.q-field__native` computed `rgba(0, 0, 0, 0.87)`, while the tokens reached
only `body` and the wizard's own classes. `ui.dark_mode(True)` alongside the
`ui.colors` call is DL-086's rung one — Quasar's own mechanism — and it
carries every background.

With dark mode active, Quasar paints its component text pure white:
`.q-stepper` and `.q-field__native` both computed `rgb(255, 255, 255)` where
Specs fixes `#E8EBED`. That rule climbs to DL-086's rung two, a declaration
at higher specificity than Quasar's own: the stylesheet scopes the
foreground to `.body--dark`, which is `0,2,0` against Quasar's `0,1,0`.

The status label carried a status class and a tag class together, both
setting `color:` at `0,1,0`. An element given `wizard-status-found
wizard-tag-found` computes `rgb(168, 216, 206)` on the served page and one
given `wizard-status-missing wizard-tag-missing` computes
`rgb(232, 149, 110)`: the tag rule is emitted later in `page_stylesheet()`
and wins both times, so `#4FD3BA` and `#E07A4C` never reach the page. Each
status names one class list carrying at most one colour-setting class,
which is what the Status labels table above reads.

## Evidence limitation

This record carries the computed value behind every verdict, which is the
evidence the milestone requires, and it names the selector and property each
was read from so any reader can re-run the same query against a served page.

It carries no screenshots. The browser pane could not be displayed in the
session that produced it, so `computer{action:"screenshot"}` returned "the
Browser pane is not displayed, so the page is not compositing frames" on
every attempt. `getComputedStyle` reads the same rendered values the
screenshot would show and is the stricter of the two, but the screenshot
half of DL-084's evidence rule is unmet and this record states that rather
than asserting a comparison it cannot show.

The gap was put to the maintainer, who accepted the computed values as
sufficient evidence for this milestone. That is a decision about what
satisfies DL-084 in a session that cannot display the browser pane, not an
omission: every verdict above still carries the value behind it, and a later
reader can re-run each query against a served page to check it.

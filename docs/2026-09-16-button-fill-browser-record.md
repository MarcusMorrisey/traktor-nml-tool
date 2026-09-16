# Served-page record: every button on the action blue

DL-084 as DL-169 amends it: the readings a browser took off the running
page, one verdict per surface, followed by a structural reading of what
the page composes against the artboards that draw it.

## How the run was taken

The app was served from the working tree with the repository's `.venv`
interpreter, `build_wizard()` followed by
`ui.run(native=False, port=8131, show=False, reload=False)`, the same
shape as `serve_wizard.py` in the gate repository at
`C:\codex\traktor-nml-tool-gate`. For `/` and `/reconnect`,
`pick_file_or_folder` was stubbed as the gate's `serve_reconstruct.py`
and `serve_w002.py` stub it: the gate's `fixture/reconstruct-conflict`
collections for `/`, and `fixture/w002gatefixtures`' `stale.nml` and
`audio` folder for `/reconnect`. The fixtures were read and nothing was
written to them; the gate repository's `git status` was clean after the
run. The viewport is `1280x900`.

Every reading is `getComputedStyle` on the `button.q-btn` element: its
`background-color`, `color`, `box-shadow`, `font-weight` and `opacity`,
and the `text-transform` of its `.q-btn__content` child. The label read
is the button's `innerText`, which is the text after `text-transform`
has applied.

The walks: `/build-playlist` at load. `/`: choose the collection to
repair, add `source.nml` and `source-two.nml`, choose a folder,
`Preview`, `Continue to resolve`, `Use answer 1` on the first
conflict. `/reconnect`: choose the collection, add a scan root,
`Continue`, read the Scan step, `Start scan`, then on Review select the
`Not found (3)` chip and `Accept` the first row.

The code under measurement is `c8348bf` plus this change.

## Readings

| Surface | Expected | Read | Verdict |
|---|---|---|---|
| `/build-playlist`, `Choose collection file...` | action blue, ground ink, label as written | `rgb(86, 180, 233)`, `rgb(15, 17, 19)`, `text-transform` `none`, label `Choose collection file...`, weight `500`, height `32.01px` | matches |
| `/build-playlist`, `Choose track list...` | action blue, ground ink, label as written | `rgb(86, 180, 233)`, `rgb(15, 17, 19)`, `none`, label `Choose track list...` | matches |
| `/build-playlist`, `Write playlist`, disabled at load | the off colours, not blue | `disabled` class; `rgb(21, 23, 26)`, `rgb(138, 146, 153)`, `box-shadow` `rgb(42, 46, 50) 0px 0px 0px 1px inset`, opacity `0.7`, `none`, weight `600`, height `32px` | matches |
| `/`, Set up: `Choose file...`, `Add collection...`, `Remove`, `Choose folder...` | action blue, ground ink, label as written | each `rgb(86, 180, 233)` and `rgb(15, 17, 19)`, `none`, weight `500`; `Add collection...` and `Remove` at `12px`, the other two at `14px` | matches |
| `/`, Set up: `Preview` | the primary: action blue, ground ink, weight 600 | `rgb(86, 180, 233)`, `rgb(15, 17, 19)`, `none`, weight `600`, `13px` | matches |
| `/`, Resolve: `All base`, `All source.nml`, `All source-two.nml`, `Choose...`, `Skip for now`, `Back to the preview` | action blue, ground ink, label as written | each `rgb(86, 180, 233)` and `rgb(15, 17, 19)`, `none`, weight `500` | matches |
| `/`, Resolve: `Use answer 1` | the primary | `rgb(86, 180, 233)`, `rgb(15, 17, 19)`, `none`, weight `600` | matches |
| `/`, Resolve: `Continue to write`, disabled with conflicts undecided | the off colours, not blue | `disabled` class; `rgb(21, 23, 26)`, `rgb(138, 146, 153)`, the `rgb(42, 46, 50)` inset shadow, opacity `0.7`, weight `600` | matches |
| `/`, Resolve: the answer card, exempt | no fill of its own | `wizard-answer-fields`; `rgba(0, 0, 0, 0)`, `rgb(232, 235, 237)`, `none` | matches |
| `/`, Resolve: `Undo` in a decided row | action blue, ground ink | `rgb(86, 180, 233)`, `rgb(15, 17, 19)`, `none`, weight `500`, height `32px` | matches |
| `/reconnect`, Set up: `Choose collection file...`, `Add scan root...`, `Choose output folder...` | action blue, ground ink, label as written | each `rgb(86, 180, 233)` and `rgb(15, 17, 19)`, `none`, weight `500`, height `32.01px` | matches |
| `/reconnect`, Set up: `Continue` | the primary | `rgb(86, 180, 233)`, `rgb(15, 17, 19)`, `none`, weight `600` | matches |
| `/reconnect`, Scan: `Cancel` | action blue, ground ink | `rgb(86, 180, 233)`, `rgb(15, 17, 19)`, `none`, weight `500` | matches |
| `/reconnect`, Scan: `Review matches`, disabled before a result | the off colours, not blue | `disabled` class; `rgb(21, 23, 26)`, `rgb(138, 146, 153)`, the `rgb(42, 46, 50)` inset shadow, opacity `0.7`, cursor `not-allowed` | matches |
| `/reconnect`, Review: `Accept`, exempt | the found tint | `wizard-decision-accept`; `rgb(18, 33, 29)`, `rgb(79, 211, 186)`, `none`, `12px` | matches |
| `/reconnect`, Review: `Reject`, exempt | the not-found tint | `wizard-tag-missing`; `rgb(33, 22, 15)`, `rgb(232, 149, 110)`, `none`, `12px` | matches |
| `/reconnect`, Review: the filter chips, exempt | not the action fill | active chip `wizard-tag-action` ink `rgb(143, 207, 242)`, the others `wizard-tag-action-outline` ink `rgb(232, 235, 237)`; every chip background `rgba(0, 0, 0, 0)`; labels `Needs review (0)`, `Not found (3)` and the rest as written | matches |
| `/reconnect`, Review: `Undo` after `Accept` | action blue, ground ink | `rgb(86, 180, 233)`, `rgb(15, 17, 19)`, `none`, `12px` | matches |
| `/reconnect`, Review: `Back` and `Continue to write` | blue at 500 and blue at 600 | both `rgb(86, 180, 233)` and `rgb(15, 17, 19)`; `Back` weight `500` at `14px`, `Continue to write` weight `600` at `13px` | matches |

## What this run corrected

**Grey buttons with capital labels.** Every button that was not a
screen's primary action carried no fill class. It rendered as Quasar's
own q-btn, and Quasar uppercased its label, so `/build-playlist` read
`CHOOSE TRACK LIST...` on a grey box against the ground. Four of those
buttons also carried `wizard-label`, a mono, uppercase, faint caption
rule meant for text beside a control, not for the control itself. Each
of them carries `wizard-control-fill` in its place, and
`.wizard-control` sets its label in the case it is written in.

**A control 34px tall.** The first served reading of the fill measured
`34.015625px` on `Choose collection file...`, and `32.015625px` with its
border set to `0` from script: a 1px blue border against Specs' 32px
rule. The border is the blue itself and cannot be seen on the fill, so
the rule carries none, and every filled control above reads `32px` or
`32.01px`.

## Structural verdicts

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| Neutral button | `.btn` in `Specs.dc.html` (build-playlist) and every reconnect-wizard artboard: `#56B4E9` ground, `#0F1113` ink, weight 500 | `wizard-control-fill`: the same ground, ink and weight, with no border | matches |
| Primary button | `.btn-pri`: the same blue and ink at weight 600 | `wizard-control-primary`: the same blue and ink at weight 600 and 13px | matches |
| Disabled button | `.btn.off`: `#15171A` ground, `#2A2E32` border, `#8A9299` ink | the same ground and ink, the border drawn as a 1px inset shadow | matches |
| Row decisions | `Review.dc.html`'s `.btn-ok` and `.btn-no` in their status tints | `Accept` and `Reject` in the same tints, unfilled | matches |

With every button blue, the primary action is set apart from the others
by weight alone, 600 against 500, and on the Set up steps by `13px`
against Quasar's `14px`, which makes the primary the smaller of the two.
Colour does not separate them, which is what DL-273 accepts.

## What this run does not establish

The keyboard ring and the announcements are not read: accessibility is
out of scope for this version, and DL-197 says so. Whether the focus ring
still shows against the blue fill is not read.

The run was served with `native=False`, not on the shipped `native=True`
entry point.

**Buttons not reached.** `/`'s Write step - `Back to resolve`,
`Write collection...`, the dialog's `Cancel` and `Write collection` -
and `/reconnect`'s Write step - `Back to review`, `Write output`, the
dialog's `Cancel` and `Write` - were not opened, so none of their
readings is taken. `/`'s `Back to set up` was seen in a screenshot of
the Preview step and not read from script.

**The disabled opacity.** Quasar's `disabled` class sets an opacity, read
here as `0.7`, over the off colours. The label's contrast at that opacity
is not computed.

**The filter chips' own backgrounds.** Every chip read `rgba(0, 0, 0, 0)`,
including the active chip, whose rule declares a tinted ground. The chips
are exempt and this change does not touch them; whether that reading
predates it was not compared.

**Hover and pressed states** of the fill are not read.

The Resolve rail's `PLAYTIME_FLOAT` key was seen in a screenshot
overlapping the value beside it. The answer card is exempt and its text
rules are unchanged; whether that overlap predates this change was not
compared.

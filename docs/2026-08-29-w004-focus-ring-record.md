# Browser record, 2026-08-29: the Review step, and the focus ring Quasar removed

The DL-084 gate over the Review step, served from the committed tree at `90f7885`
with a clean working tree, driven at 1280x800.

This record carries what the two before it could not. The browser pane displayed,
so screenshots composite - see "Screenshots" below for what they showed and for
the reason no file is saved beside this record. Real key events reached the page:
a `keydown` listener recorded `isTrusted: true` for every Tab pressed here, and
the focus readings are taken from those presses rather than from
`HTMLElement.focus()`, which does not set `:focus-visible` and would have read
every control as unringed whether or not the ring works.

One caveat holds from the earlier records: a driven key still arrives with
`keyCode: 0`, so Quasar's Escape path, which gates on `evt.keyCode === 27`, is
not exercised by the keys delivered here.

The gate driver, its fixture and their own record live outside the repository at
`C:\codex\traktor-nml-tool-gate`.

## The fixture and the scan

`GATE _build_args` reported `match_confidence: None`, `fingerprint: False`,
`no_refute: False`, `dry_run: True`, one scan root and a volume map row
resolving the audio tree to `C:`. `GATE scan -> error= None reviews= 3`.

The seven filter chips read `NEEDS REVIEW (1)`, `REFUTED (0)`, `RE-ENCODED (0)`,
`NOT FOUND (1)`, `ACCEPTED (0)`, `REJECTED (0)`, `FOUND AUTOMATICALLY (1)` -
three non-zero counts summing to the three reviews the scan returned.

## Controls and colour

| Surface | Specs or the artboard fixes | Read off the page | Verdict |
|---|---|---|---|
| Ground | `#0F1113` | `rgb(15, 17, 19)` | matches |
| Filter chips | `32px` | `32px`, `min-height: 32px`, all seven | matches |
| Row decision controls | `32px` | `32px`, `min-height: 32px` | matches |
| Back, Continue to write | `32px` | `32.0125px` | matches |
| Gap between the decision buttons | `8px` (Specs.dc.html:267) | `8px` between bounding rects, `gap: 8px` on `.wizard-control-group` | matches |
| Accept | `Review.dc.html:37`'s `.btn-ok`: `#12211D` on `#2C5449`, text `#4FD3BA` | `rgb(18, 33, 29)`, border `rgb(44, 84, 73)`, `rgb(79, 211, 186)`, `12px` | matches |
| Reject | `Review.dc.html:38`'s `.btn-no`: `#21160F` on `#6A3F2C`, text `#E8956E` | `rgb(33, 22, 15)`, border `rgb(106, 63, 44)`, `rgb(232, 149, 110)`, `12px` | matches |
| Needs-review status word | `#F5D96B` | `rgb(245, 217, 107)`, `12px` | matches |
| Focused row | `2px` solid on the light foreground, `2px` offset | `outline: rgb(232, 235, 237) solid 2px`, `outline-offset: 2px` on `.wizard-row-focused` | matches |
| Smallest rendered text | no text below 11px | `11px` | matches |

## What the gate caught: no focusable control painted a focus ring

Specs' "Accessibility rules" fix the focus ring at 2px solid on the light
foreground, 2px offset, on every focusable control, and state that it is
**never removed**. Under a real Tab, with `:focus-visible` matching `true`,
every button in the Review step computed:

```
outline: rgb(232, 235, 237) none 0px
outline-offset: 2px
```

The colour and the offset arrive from `page_stylesheet()`'s `*:focus-visible`
rule. The style and the width do not, so nothing paints. `.q-focus-helper`,
Quasar's own focus overlay, computed `opacity: 0` on the same element, so no
second indicator stood in its place. Eleven controls were affected: the seven
filter chips, Accept, Reject, Back and Continue to write.

`docs/2026-08-28-w002-browser-record.md` reads matches for the focus ring on the
strength of the rule's text - `:focus-visible { outline: rgb(232, 235, 237)
solid 2px; outline-offset: 2px }` - which is genuinely in the emitted
stylesheet. It loses at cascade time on every `q-btn`, and no reading of the
sheet can show that. This is the same shape as the twelve `#` comment lines that
sat inside the CSS string, and as the `.bg-primary` blue that outranked an
attached token class: a rule present in the source is not a rule painting on the
control.

### Why, measured rather than inferred

Quasar gives every `q-btn` the `no-outline` class. Removing that one class from
the focused element changed its computed outline from `none 0px` to
`solid 2px`, so the class is what suppresses the ring.

The page declares its layers in this order, read from
`document.styleSheets`: `theme`, `base`, `quasar`, `nicegui`, `components`,
`utilities`, `overrides`, `quasar_importants`. For an `!important` declaration
the **earlier** layer wins, which inverts the ordinary rule and makes
`quasar_importants` unreachable from anything declared after it. Four override
forms were tried against the focused control, each measured on the served page:

| Attempt | Computed outline |
|---|---|
| Baseline, as served | `rgb(232, 235, 237) none 0px` |
| Unlayered `!important` at `html body button.q-btn.no-outline.wizard-control:focus-visible` | `rgb(232, 235, 237) none 0px` |
| `!important` inside a new layer declared last | `rgb(232, 235, 237) none 0px` |
| `!important` inside `@layer quasar_importants` | `rgb(232, 235, 237) solid 2px` |
| Inline `style` with `!important` | `rgb(232, 235, 237) solid 2px` |

So no `add_head_html` rule reaches this at any specificity unless it re-opens
Quasar's own layer. That is DL-086's rung two, reached by naming the layer.

### The fix

`page_stylesheet()` keeps its unlayered `*:focus-visible` rule, which serves
every focusable element that is not a `q-btn`, and adds beside it:

```css
@layer quasar_importants {
  .q-btn:focus-visible { outline: 2px solid #E8EBED !important; outline-offset: 2px !important; }
}
```

Both values come from `FOCUS_RING` and `FOCUS_RING_OFFSET`; no new constant.

Re-served from the same driver and driven with eleven real Tab presses. Every
control reached in reading order - `NEEDS REVIEW (1)`, `REFUTED (0)`,
`RE-ENCODED (0)`, `NOT FOUND (1)`, `ACCEPTED (0)`, `REJECTED (0)`,
`FOUND AUTOMATICALLY (1)`, `Accept`, `Reject`, the Keyboard shortcuts
expansion, `Back` - computed `outline: rgb(232, 235, 237) solid 2px` at
`outline-offset: 2px`, with `:focus-visible` true and the `no-outline` class
still on the element. The screenshots below carry the before and after on the
same focused chip, and the Back button's ring is visible in the last of them.

`tests/test_gui_theme.py::test_button_focus_ring_declares_inside_quasars_own_layer`
pins the layer name with tinycss2. Its docstring says plainly that it reads the
emitted sheet and cannot see the cascade, and names this record as the evidence.

## Screenshots

Four composited and were read in the session that produced this record: the
Review step as served; `REFUTED (0)` focused by a real Tab with no ring; the
same chip ringed under the layered rule; and `Back` focused by a real Tab and
ringed after the fix. The third and fourth are what turned the ring from a
computed value into something seen.

**No image file is saved beside this record.** The driver returns a composited
screenshot to the session rather than to a path, and no headless capture library
is installed in `.venv` - `playwright`, `selenium`, `pyppeteer`, `html2image`
and `imgkit` are all absent, and installing one is outside this pass. So
DL-084's "names the screenshot files saved beside it" is still unmet, for a
different reason than in the two earlier records: the pane composites now, and
the gap is the write-to-disk step. Every verdict above carries the value behind
it, and a later reader can re-run each query against a served page.

## Second pass, same day: the primary button's ink and six unmeasured heights

The ladder was run against `Continue` on the Set up step, which carries the same
`color="primary"` as the other four primaries. Its label computed
`rgb(255, 255, 255)` on `rgb(86, 180, 233)` - **2.31:1**, where
`Review.dc.html:36`'s `.btn-pri` fixes `color: #0F1113` and measures **8.2:1**
against the same blue. Weight read `500` against `.btn-pri`'s `600`, size
`14px` against its `13px`.

| Rung | Form | Ink | Contrast |
|---|---|---|---|
| - | Baseline, as served | `rgb(255, 255, 255)` | 2.31:1 |
| One | Quasar's own palette class (`text-dark`) | `rgb(255, 255, 255)` | 2.31:1 |
| **One** | **`color=None`, background and ink both on a token class** | **`rgb(15, 17, 19)`** | **8.2:1** |
| One | The same token class with `bg-primary text-white` left on | `rgb(255, 255, 255)` | 2.31:1 |
| Two | `add_head_html` at `html body button.q-btn.bg-primary.text-white` | `rgb(255, 255, 255)` | 2.31:1 |
| Two | The same selector with `!important` | `rgb(255, 255, 255)` | 2.31:1 |
| Two | `!important` inside `@layer quasar_importants` | `rgb(15, 17, 19)` | 8.2:1 |

**The ladder stops at rung one.** The fourth row is the control that decides it:
leaving Quasar's own classes on defeats the token class, so `color=None` is
required rather than tidy. `text-white` is `!important` in the same
last-ordered layer as `no-outline`, which is why every rung-two form except the
layered one loses. This is the shape the review row's Accept and Reject already
use, so it is **no DL-087 shortfall** and the "Framework shortfalls" section in
`traktor_nml/README.md` still holds no entries.

`.wizard-control-primary` carries `ACTION`, `GROUND`, weight 600 and `TYPE_13`
together, and all five primaries take `color=None` at the constructor:
Set up's `Continue`, Scan's `Start scan`, Review's `Continue to write`, Write's
`Write output` and the confirm dialog's `Write`.

### Six controls carried no token class at all

The same run measured every control on the Set up and Scan steps, which no
earlier record had reached - both prior gates measured only Review, Write and
the dialog.

| Control | `app.py` | Before | After |
|---|---|---|---|
| Choose collection file... | 211 | `41px` | `32px` |
| Add scan root... | 263 | `80.05px` | `32.0156px` |
| Continue | 304 | `36px` | `32px` |
| Cancel | 357 | `36px` | `32.0156px` |
| Start scan | 359 | `56.03px` | `32px` |
| Review matches | 367 | `56.03px` | `32.0156px` |

Specs fixes controls at 32px, every button on every screen. The `56.03px`
readings are the two-line wrap this gate already diagnosed on `Write output` -
twice the `24.01px` line height plus padding - and `white-space: nowrap` on
`.wizard-control` is what holds a label to one line. None of the six carried
`.wizard-control`, so none carried the floor or the nowrap.

### Verified on the served page

Re-served and driven through all four steps and the confirm dialog:

| Step | Control | Height | Ink on blue |
|---|---|---|---|
| Set up | Choose collection file..., Add scan root... | `32px`, `32.0156px` | - |
| Set up | Continue | `32px` | `rgb(15, 17, 19)`, 8.2:1, 600, `13px` |
| Scan | Cancel, Review matches | `32.0156px` | - |
| Scan | Start scan | `32px` | `rgb(15, 17, 19)`, 8.2:1, 600, `13px` |
| Review | seven chips, Accept, Reject, Back | `32px`, `32.0156px` | - |
| Review | Continue to write | `32px` | `rgb(15, 17, 19)`, 8.2:1, 600, `13px` |
| Write | Back to review | `32.0156px` | - |
| Write | Write output | `32px` | `rgb(15, 17, 19)`, 8.2:1, 600, `13px` |
| Dialog | Cancel (autofocused) | `32.0156px` | - |
| Dialog | Write | `32px` | `rgb(15, 17, 19)`, 8.2:1, 600, `13px` |

The focus ring holds alongside the new class: a real Tab onto `Back to review`
and `Write output` computes `outline: rgb(232, 235, 237) solid 2px` at `2px`
offset on both.

`tests/test_gui_button_color_defaults.py`'s `_EXPECTED_COLOR_BY_CALL` names
`None` for every call in `app.py`. Its prose records that a call carrying
`color="primary"` has left its label to Quasar's `text-white`, which is the
defect above.

### The write refusal, exercised

With the output field left empty, `_build_args` passed `output` equal to
`old_input` - the fixture's own collection. Clicking `Write output` opened no
dialog and rendered instead: "The output path is the same file this run reads
from. Set a different path in Output collection path, on Set up."
`wizard_state.write_refusal`'s `output_must_differ_from_input` reaches the
operator as written copy, ahead of any work.

Setting a distinct output path let the confirm dialog open on
"Write the reconnected collection?" with `Cancel` holding focus, which is where
the dialog's own `Write` was measured. The dialog was dismissed through
`Cancel`. No write was performed in this session: the named output file does not
exist afterwards, and the fixture hashed identical across all 604 files.


## Third pass: the screen-reader attempt, and what it found

The screen-reader pass **was not run**, and the reason is the machine rather
than the wizard. `C:\Windows\System32\Narrator.exe` is present; NVDA and JAWS
are not. Narrator offers no speech transcript to capture, and NVDA's Speech
Viewer - which renders spoken output as text a record could carry - would have
to be installed first. That is where DL-084's screen-reader rule still stands
unmet.

What ran instead is the layer beneath it: the live regions a screen reader
consumes, and the strings that reach them. Recorded here as a prerequisite
check, not as the pass.

| Item | Specs fixes | Read off the page | Verdict |
|---|---|---|---|
| Live regions present | one polite, one assertive | two `[aria-live]` elements, `role="status"`/`aria-live="polite"` and `role="alert"`/`aria-live="assertive"` | matches |
| Both stay in the accessibility tree | announced, not hidden from AT | `display: block`, `visibility: visible`, `1x1px`, `position: absolute`, `overflow: hidden`, `clip-path: inset(50%)` | matches |
| Progress wording | `"4,212 of 12,542"` | `"25 of 603"` in the polite region | matches |
| Decision wording | `"Bar A Thym accepted - 458 of 1,238 done"` | `"archangel.mp3 accepted - 1 of 1 done"` in the polite region | matches |

`display: none` or `visibility: hidden` would drop both regions out of the
accessibility tree and silence every announcement while every source-reading
guard stayed green. They are hidden the other way, so they are spoken.

### What the attempt caught: a decision taken with the pointer announced nothing

Specs fixes the announcement on the decision - "each decision as it happens" -
not on the input device. Clicking the row's `Undo` button applied the decision
and re-rendered: the chip counts moved to `ACCEPTED (1)` and the row redrew with
its `UNDO` control. **Neither live region changed.** A real `a` keypress on the
same row, through `_applier_accept`, produced
`"archangel.mp3 accepted - 1 of 1 done"` in the polite region.

The row's three buttons were constructed with
`on_click=lambda k=key: (state.decisions.accept(k), render_all())`, reaching
`state.decisions` directly and never `_announce_decision`. Only the four
keyboard appliers announced. No guard over the row's labels, classes or colours
could see it, and `tests/test_gui_announce.py` was green throughout: the
announcement text and its cadence were always correct, and the gap was a call
site that never reached them.

`_decide_from_button` applies the decision, announces it and re-renders, and all
three buttons are constructed with it. The row list is read **before** the
decision is applied, the order the appliers already use: `_announce_decision`
reads the track name and the position out of that list, and an accepted row
leaves the Needs review filter, so a list read afterwards would announce the
fallback key at a position of `len(rows)`.

Re-served and driven, every route reaching the polite region with the
pre-decision position:

| Route | Read off the page |
|---|---|
| `Accept` button, pointer | `"archangel.mp3 accepted - 1 of 1 done"` |
| `Reject` button, pointer | `"archangel.mp3 rejected - 1 of 1 done"` |
| `Undo` button, pointer | `"archangel.mp3 undone - 1 of 1 done"` |
| `u` key, trusted keypress | `"archangel.mp3 undone - 1 of 1 done"` |

`tests/test_gui_review_row_controls.py::test_every_decision_button_announces_through_the_shared_path`
pins the wiring, and its docstring records that a button wired straight to
`state.decisions` is the defect it exists to catch.

One measurement artifact worth carrying: a keypress delivered while the browser
pane has lost keyboard focus reaches nothing at all - a `window` keydown
listener recorded an empty array, and the wizard was correctly unchanged. A real
click into the pane restores it. A reading taken in that state looks exactly
like a broken key binding.

## What this record does not carry

No screen reader was run, for the reason given above: none capable of producing
a capturable transcript is installed. The live regions, their politeness and the
text each announcement carries are read from the page and recorded above; that
assistive technology speaks them is still not evidenced.

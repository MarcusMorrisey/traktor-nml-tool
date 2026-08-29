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

## Still open, not fixed here

`Continue to write` renders its label at `rgb(255, 255, 255)` on `rgb(86, 180,
233)`, a contrast of **2.31:1**. `Review.dc.html:36`'s `.btn-pri` fixes
`color: #0F1113`, which measures **8.2:1** against the same background. The
class list carries Quasar's own `text-white` utility and no wizard token for the
ink; the weight reads `500` against `.btn-pri`'s `600` and the size `14px`
against its `13px`. DL-086's ladder was not run against it here, so whether it
settles at rung one or becomes the first DL-087 shortfall is undecided, and no
entry is written for it in either direction.

With the output field left empty, `_build_args` passed `output` equal to
`old_input` - the fixture's own collection. `wizard_state.write_refusal` covers
exactly that case through `output_collision_refusal`'s
`output_must_differ_from_input`, so the Write step is expected to refuse rather
than overwrite. Not exercised: no write was performed in this session, and the
fixture hashed identical afterwards across all 604 files.

## What this record does not carry

No screen reader was run. The live regions, their politeness and their text are
read from the page in the earlier record; that assistive technology speaks them
is still not evidenced.

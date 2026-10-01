# W-002 browser record: the keyboard contract and the announcements

Wave W-002 of the reconnect-wizard visual pass, milestones M-002 and M-003,
gated under DL-084.

The wizard was served over HTTP by a scratch driver outside the repository
(`build_wizard()` then `ui.run(native=False, port=8115)`) and driven in a
browser. Each value below is read off the served page with `getComputedStyle`
or from the DOM, against the value the artboard fixes.

Two accommodations, both outside the repository and both stated here because
they shape what the values below prove:

- The Set up step's collection and scan-root choosers open a native dialog
  the browser cannot drive, so the driver replaces `pick_file_or_folder` with
  a stub returning the fixture's paths. Every other control on the page is
  the wizard's own.
- The fixture is built by a scratch script that writes ID3-tagged MP3s over a
  hand-built MPEG-1 Layer III frame, so file size and duration both survive
  the refutation checks. Under the settings the wizard itself passes - strict
  confidence, refutation on - it yields one matched row, one needs-review row
  and one not-found row. The statuses were read back from
  `review_model.row_status` before the gate ran rather than assumed.

Screens compared: `Specs.dc.html` for the keyboard map and the accessibility
rules, `Review.dc.html` for the table and its controls, `Scanning.dc.html`
for the scan counter and tiles, and `Confirm.dc.html` for the write dialog.

## Controls and the focus ring

| Control | Specs fixes | Read off the page | Verdict |
|---|---|---|---|
| Row controls A, R, U (`.wizard-control`) | `32px` | `32px` height, `32px` min-height | matches |
| Filter chips (`.wizard-tag-action`, `.wizard-tag-action-outline`) | `32px` | `32px`, `box-sizing: border-box` | matches |
| Continue to write (`.wizard-control`) | `32px` | `32.0156px` | matches |
| Write output (`.wizard-control`) | `32px` | `32.0156px`, `white-space: nowrap`, content `24.0156px` on one line | matches |
| Dialog Cancel | `32px` | `32.0156px` | matches |
| Dialog Write | `32px` | `32.0156px` | matches |
| Gap between controls | `8px` | `8px` declared on `.wizard-control-group`, `8px` measured between the decision buttons' bounding rects | matches |
| Focus ring | `2px` solid on the light foreground, `2px` offset | `:focus-visible { outline: rgb(232, 235, 237) solid 2px; outline-offset: 2px }`, and `#E8EBED` is `TEXT` | matches |

## The review table

| Item | The artboard fixes | Read off the page | Verdict |
|---|---|---|---|
| Filter counts against the scan | one of each status | `NEEDS REVIEW (1)`, `NOT FOUND (1)`, `FOUND AUTOMATICALLY (1)` | matches |
| matched status | `#A8D8CE` on `#12211D` | `rgb(168, 216, 206)` on `rgb(18, 33, 29)`, `12px` | matches |
| needs-review status | `#F5D96B` on `#1F1D14` | `rgb(245, 217, 107)` on `rgb(31, 29, 20)`, `12px` | matches |
| not-found status | `#8E979E`, no tint | `rgb(142, 151, 158)`, `rgba(0, 0, 0, 0)`, `12px` | matches |
| Focused row | one row carries the focus treatment | exactly one element carries `wizard-row-focused` | matches |
| Detail panel opens from the map's own key | Space toggles the detail panel | Space through `on_key` opens it; the panel is in the DOM afterwards | matches |

## Announcements

| Item | Specs fixes | Read off the page | Verdict |
|---|---|---|---|
| Polite region | `aria-live=polite` | present, `role="status"` | matches |
| Assertive region | `aria-live=assertive` | present, `role="alert"` | matches |
| Progress, polite | a count of a total | `25 of 603`, then `325 of 603` | matches |
| Decision, polite | track, decision, position in the queue | `archangel.mp3 accepted - 1 of 1 done` | matches |
| No write is claimed before one happens | assertive stays empty until a write | assertive region empty across setup, scan and review | matches |
| Scan failure, assertive | the file consequence in the first clause | `...\stale.nml was not written: scan failed: volume_identity_error=...` | matches |

## The write step and its dialog

| Item | Specs fixes | Read off the page | Verdict |
|---|---|---|---|
| Reconnect count | the count the write applies | `1 tracks to reconnect` | matches |
| Refusal guard | the output must differ from the input | leaving Output blank yields `output_must_differ_from_input` and the write button computes `disabled` | matches |
| Dialog heading | `16px` (`Confirm.dc.html`) | `16px`, `wizard-heading-sm` | matches |
| Dialog opens on the safe control | focus on the safe button | `Cancel` carries `autofocus` and is `document.activeElement` | matches |
| Enter does not write | no write | the dialog stays open and `written.nml` is absent on disk afterwards | matches |
| Escape closes | the dialog closes | `.q-dialog` computes `offsetParent === null` | matches |
| Focus returns to the opener, Cancel path | the opener is refocused | `document.activeElement` is `Write output`, `closest('.q-dialog')` is null | matches |
| Focus returns to the opener, Escape path | the opener is refocused | the focus ring lands back on `Write output`, read by the maintainer from a trusted Escape keypress | matches |

The review row's decision buttons stand `8px` apart where `Review.dc.html:68`'s
`.dec` and `.decd` groups render `6px`. Specs.dc.html:313 states the rule -
controls are 32px tall with 8px between them, every button on every screen -
and a stated rule governs an artboard's own rendering under DL-088, the same
decision that settles the 32px control height against the artboards rendering
34px. The `8px` reading is the correct one and no shortfall follows from it.

`Confirm.dc.html` governs this dialog rather than `Cancelling.dc.html`: its
own heading reads "Write 11,389 changes?", it carries the same Cancel and
Write pair, and it states the Enter and focus rules this dialog implements.
`Cancelling.dc.html`'s `17px` heading belongs to a "Stop scanning?" dialog,
which no milestone in this plan builds.

## Reduced motion

The environment serving this gate reports
`matchMedia('(prefers-reduced-motion: reduce)').matches` as `true`, so these
are the reduced-motion values rather than an emulation of them.

| Item | Specs fixes | Read off the page | Verdict |
|---|---|---|---|
| Progress bar stops animating | no animation | `.q-linear-progress__model` computes `animation-name: none`, `animation-duration: 0s`, `transition-duration: 0s`, sampled during a 603-file scan | matches |
| Counts still update | counts advance | `transform` advances `0.166` to `0.663` to `0.871` while the polite region advances `25 of 603` to `325 of 603` | matches |
| Spinner is a static mark | no animation | the Scan step renders no spinner; an element carrying `.q-spinner` under the same stylesheet computes `animation-name: none` | matches, on the class rather than a rendered spinner |

## Reflow at 1024px and 200% zoom

Measured at a 512px CSS viewport, which is 1024 physical pixels at 200% zoom.

| Item | Specs fixes | Read off the page | Verdict |
|---|---|---|---|
| Detail panel drops below the table | below, not clipped | table row bottom `424`, detail panel top `440` | matches |
| No horizontal scrolling | none | `documentElement.scrollWidth` equals `clientWidth` at `512`; zero elements extend past it | matches |

## What the gate caught

The defects below surfaced here and no source-reading guard saw any of them.
All were fixed in the wave's own diffs. The five functional ones - the
confidence level, the uncaught scan failure, the missing volume map, and the
two steps that never re-render - were each checked against the wave's baseline
commit and are present there, so the visual pass exposed them rather than
introducing them. The scan tiles and the control measurements that follow are
this wave's own work measured against the artboards for the first time, so no
such comparison applies to them.

`_build_args` passed `match_confidence="normal"`, which names no level -
`MatchConfidence` is strict, loose or filename - so `parse_match_confidence`
raised and the scan died. It passes `None`, which `resolve_confidence`
resolves to strict exactly as the CLI does under DL-010.

`run_scan` caught only `ScanCancelled`, so that crash left the wizard silently
dead: nothing announced, nothing notified, the Start button disabled and the
stepper stopped on Scan. An unexpected exception now announces through
`announce.error_message`, notifies, and re-enables the control.

The Set up step offered no equivalent to the CLI's `--volume-map`, and
`resolve_volume_identity` needs one whenever no old record's decoded path sits
under the scan root - which is every reconnect, since the premise is that the
files moved. Observed: `volume_identity_error=volume_identity_ambiguous
scan_root=...\audio observed_pairs=[]; pass --volume-map`. Each scan root now
carries a VOLUME and VOLUMEID the operator can see and edit.

The Review step was built once, at page construction, while `scan_result` was
still `None`, and `run_scan` never called back into it. Observed: the scan
returned three reviews - `GATE scan -> error= None reviews= 3` - while the
page showed zero rows and every filter chip read `(0)`.

The Write step had the same shape and rendered only "Nothing to write.", so
the refusal label, the write button, the confirm dialog and the output log had
never rendered at all. Both are fixed by one `state.step_refreshers` registry
that `run_scan` runs, rather than by two named attributes.

The three scan tiles bucketed a list that `on_progress` can only ever see
empty, because progress fires during disk indexing and the reviews are
appended later. They are set from the completed result.

The filter chips stood `33.9844px` against Specs' `32px`, and the review row
put `12px` between its controls rather than `8px`. `.wizard-control`'s
`min-height` is a floor, so a class raising the content height wins; an
explicit `height` on the chip classes clamps it, and a
`.wizard-control-group` rule carries the gap.

Two controls reached the page unringed. "Continue to write" and the dialog's
"Write" both carried no token class and computed `36px`. DL-086's rung one -
the token class, Quasar's own mechanism - won for both, so neither is a
framework shortfall and no DL-087 entry is written for them. "Write output"
carried `wizard-heading-xs`, a heading step on a control, and wrapped onto two
lines at `56.0312px`, which is twice its `24.01px` line height plus padding;
`white-space: nowrap` on `.wizard-control` holds its label to one line.

Review's "Back" and Write's "Back to review" (added this wave, below) make a
pre-existing reset reachable for the first time rather than introducing it.
`run_scan`'s success path has always set `state.decisions = WizardState()`
unconditionally on every successful scan - the wave that added the two Back
buttons did not touch that line. Before this wave there was no way back into
Scan at all, so the reset was never something an operator's own navigation
could trigger; now, Review's "Back" reaches a Scan step whose "Start scan" is
live, and pressing it discards every decision made so far, silently, with no
confirmation. This is not new behaviour and this record does not propose
changing it - it is recorded here because shipping a route to a pre-existing
trap without recording it would be the omission, not the trap itself.

## Deferred keyboard entries

Specs.dc.html's Keyboard section names three keys the wizard does not act
on, ruled deferred for W-002 by the maintainer rather than treated as a
gap to close here. `/` ("Jump to search") names a Review-table search: the
Review step builds two interactive regions, `filter_row` and
`table_container`, and no search input anywhere a `/` keypress could reach,
and `review_model.FILTERS` is seven fixed status/decision predicates with
no text match among them - a search control and a text predicate in
`review_model` would have to exist first. `F6` ("Jump between regions:
filters -> table -> comparison -> footer") names a focus-region cycle;
nothing in `app.py` tracks a region order or moves focus between the four
named areas - a region cycle would have to exist first. `Ctrl+Z` ("Undo the
last decision, wherever focus is") names an undo keyed to time rather than
to the focused row, which `undo_row` already covers; `WizardState._decisions`
(`wizard_state.py`) is a plain unordered dict, carrying no record of which
decision came last - an ordered decision history would have to exist
first.

The three sit in two different states. `keymap.ENTRIES` carries `F6` and
`Ctrl+Z` as declared rows whose actions, `jump_region` and `undo_last`,
`_ACTION_APPLIERS` binds to `_applier_noop`. `/` has no row in
`keymap.ENTRIES` at all. The help panel renders only entries bound to a real
applier, so neither declared key appears on screen as a key that does
nothing.

`tests/test_gui_keymap.py` holds a guard over each state. One reads Specs'
own `.kbd` chips and requires every key it lists to have a matching
`keymap.ENTRIES` row, naming `/` as its one documented exception. The other
pins `_ACTION_APPLIERS`' no-op set by name and splits it: `jump_region` and
`undo_last` are deferred, unimplemented behaviour, while `focus_next`,
`focus_prev` and the dialog's `dialog_safe_close` are satisfied by behaviour
the browser and Quasar already provide - native tab order, Quasar's own
Escape dismissal left enabled by `no-esc-dismiss=false`, and Enter
activating the autofocused safe button.

Cancelling.dc.html:133-134 names a fourth deferred control, of the same
shape: after a stopped scan, "Scan again" restarts scanning immediately with
the existing configuration, and "Back to setup" returns to the Set up step
to change it first. Neither exists in app.py - there is no stop-scan
confirmation dialog at all, so neither action has a screen to render on.
The stop-scan confirmation dialog would have to exist first.

## What this record does not carry

Three parts of DL-084's evidence rule are unmet here, and the record states
them rather than asserting comparisons it cannot show.

It carries no screenshots. The browser pane could not be displayed in the
session that produced it, so `computer{action:"screenshot"}` returned "the
Browser pane is not displayed, so the page is not compositing frames" on every
attempt. The maintainer accepted computed values as the evidence for this wave,
as for M-001. That is a decision about what satisfies DL-084 in a session that
cannot display the pane, not an omission: every verdict above carries the value
behind it, and a later reader can re-run each query against a served page.

It was not driven from the keyboard alone. Real key events do not reach an
undisplayed pane - a `window` keydown listener recorded nothing for Tab, Down
or `a`. The keys above were delivered as synthetic `KeyboardEvent`s, which do
reach the page's own `on_key` handler and drive the real `keymap.dispatch` and
applier chain, so the dispatch results are the wizard's own. They are not
evidence that the wizard can be driven by a person's keyboard with no mouse,
and are not recorded as such. The maintainer archived that drive-through to a
later version.

No screen reader was run. The live regions, their politeness, and the text
each announcement carries are read from the page and recorded above; that
those regions are spoken by assistive technology is not. The maintainer
decided against running one for this wave.

Those two decisions leave M-002's and M-003's own acceptance criteria
partly unmet, and this record says so rather than reading as though the gate
ran whole. M-002 asks for the review step driven from the keyboard alone with
no mouse; M-003 asks for the wizard driven with a screen reader announcing.
Neither happened. What stands in their place is every value above, each read
off the served page, and the dispatch chain exercised through the wizard's own
handler. A later version that runs both closes the gap; nothing above needs
re-measuring for it.

One entry in the dialog table is read by the maintainer rather than by this
session, and is marked here because of it. Quasar's `QDialog.handleHide` calls
`refocusTarget.focus()` for an ordinary hide, and for a key-triggered hide
calls `refocusTarget.closest('[tabindex]:not([tabindex^="-"])').focus()`
instead - a selector a button without an explicit `tabindex` never matches.
The write button carries `tabindex="0"` so it matches that lookup on both
paths. Under a synthetic Escape the focus does not return, because Quasar's
escape handling gates on `evt.keyCode === 27`, which a synthetic event does not
populate the way a trusted one does; under the maintainer's own Escape
keypress the focus ring lands back on `Write output`. The entry reads matches
on that trusted keypress, and the synthetic reading is recorded here as the
artifact it is rather than left standing as a measurement.

## Structural verdicts

Stated under the amended DL-084 (DL-169), which requires a structural
reading - app shell, column model, card structure, table geometry -
beside the atom readings a surface carries. This run measured atoms.
The rows below state, per surface it covered, what it did not measure
and what the served page composes, read against the artboards rather
than re-run. Every atom reading above stands exactly as this run
recorded it (DL-171). Each differs entry names an entry under
"Composition not built" in `traktor_nml/README.md`.

| Structure | The artboard draws | The served page composes | Verdict |
|---|---|---|---|
| App shell | `.app` grid, rows `56px 1fr 64px` | a header row and one column, the page scrolling as a document | differs |
| Column model | `Review.dc.html`'s `.split` at `1fr 400px` | one column; the candidate panel renders below the table | differs |
| Card structure | `.card` + `.card-h` + `.card-b` | `.wizard-surface` applied once to the whole column | differs |
| Table geometry | `.gr` at `126px minmax(0, 1fr) 100px 196px 134px` under a `.th` header row | `.wizard-row`, a flex row with a gap; no column aligns row to row and no header row is rendered | differs |
| Detail rail | `.det`, a 400px bordered panel with its own header, body and footer | the candidate panel, in the same column below the table | differs |
| Footer band | `.ft`, 64px, note left and actions right | actions inline as the column's last children | differs |

Thirty-seven atom verdicts in this record read matches, and every one
of them is a property of a single element - a height, a hex value, a
gap, an attribute. None of them is a relationship between elements,
which is why the composition above went unreported for the whole of
this run.

# The reconstruct page's resolve step

The reconstruct page at `/` runs a sequence — configure, preview,
decide the conflicts, write — and draws none of it. The four inputs may
be filled in any order, but the three stages are ordered, and
`write_refusal` enforces that order by refusing after the click rather
than by showing it. This plan gives the page the four-step scaffold and
builds step 3 to `design/reconnect-wizard/Resolve.dc.html`.

## What is committed here

All three milestones.

- **M-001** - `conflict_model.py` gains `ResolveGate`, `resolve_gate()`
  and `candidate_for_digit()`, so the footer sentence, the advancing
  control's enabled state and Specs' digit-to-answer arithmetic are all
  answered below the nicegui boundary. `theme.py` gains the step-rail,
  split, conflict-table, detail-rail, answer, bulk-strip and tally
  rules. Guards in `tests/test_gui_resolve_rules.py` and
  `tests/test_gui_resolve_sheet.py`.
- **M-002** - `reconstruct_steps.py` carries the step table, the rail
  records and the reachability rule, and imports no framework.
  `app.py` builds the rail, the four step regions with per-step footer
  groups, and `_render_resolve`: the tally and bulk strip, the conflict
  table under a header row, and the 400px rail holding one control per
  distinct answer. Guards in `tests/test_gui_reconstruct_steps.py`,
  `tests/test_gui_resolve_composition.py`, and additions to
  `tests/test_gui_keymap.py` and
  `tests/test_gui_conflict_page_controls.py`. Closed on
  `docs/2026-09-07-reconstruct-resolve-browser-record.md`.
- **M-003** - `traktor_nml/README.md` carries DL-198 through DL-215,
  DL-172's exemption for `/` is struck rather than restated, and the
  three "Composition not built" entries are narrowed to name the
  reconnect route and the artboard each is read against. Nothing leaves
  the section. `gui/README.md` names `reconstruct_steps.py` and says
  which step mechanism serves which route.
  `tests/test_docs_browser_record_structure.py` holds the new record's
  digest.

The suite reads 616 passed, 4 skipped under the system interpreter.

## What the served run found

The record closing M-002 was taken on the real page, served by
`serve_reconstruct.py` in the gate repository with only the native file
chooser stubbed, and it found three defects the source-text guards
passed.

The conflict grid's four fixed tracks were sized for the width
`Resolve.dc.html` draws its table at, and the built page centres its
content, so the flexible track resolved to `54px` and the track paths
crossed the two columns beside them. The rail's head said "Two
collections hold this file" beside rows held by three. The footer's
note said writing stays closed while the control beside it was enabled
- the exact failure `ResolveGate`'s own docstring names, reached
because the sentence was formatted at the call site rather than read
off the gate.

All three are fixed, each behind a guard proven to fail first, and the
readings above were retaken on the corrected page. DL-213, DL-214 and
DL-215 record the three decisions.

## What this work still owes

**The keyboard ring is not re-walked.** DL-197 asks for it once the
advancing controls are built in the footer band, and they are. The run
could not take it: the pane's keyboard channel did not reach the page -
`Tab` pressed with focus seated on a named control left
`document.activeElement` where it was. The record says so under "What
this run does not establish" rather than reporting a ring assembled
from DOM order (DL-211). Announcements are unread for the same reason.

Step 1's existing content is placed into its step region rather than
built to `Reconstruct.dc.html`. Its structures carry no entry, because
this work's scope is the scaffold and step 3. Steps 2 and 4 are built
to their own artboards and read on a served page in
`docs/2026-09-07-reconstruct-preview-and-write-browser-record.md`.

## What the gate caught before it stopped

The step rail rendered at `x = 24` against its content column's
`x = 128`, 104px out of alignment, on a page where both carry
`wizard-content-width`. `.wizard-step-rail` declared `margin: 0`,
emitted after `.wizard-content-width`, so it overrode that rule's auto
margins. The declaration came from `Resolve.dc.html`'s `.steprail`,
where it is harmless because that artboard's `main` is a grid and
nothing is centred in it. `theme.py` declares no margin on the rail,
and `tests/test_gui_resolve_sheet.py` holds that it declares none.

No guard could have caught it: each rule was correct read alone, and
what was wrong was the margin the browser resolved from two of them
together. That is the reading DL-084 exists to take, and it is the
fourth defect the served-page gate has found that the source-text
guards did not.

## A reading that was taken and discarded

One measurement in that session showed the document scrolling and
Quasar setting `min-height: 1800px` on `.q-layout` — twice the
viewport — which would have been a regression against the shell
record's finding that the middle owns the scroll. A clean page load
returns `min-height: 900px`, a middle of 780, and no document scroll.
The first reading was an artefact of the pane it was taken in, and it
is recorded here because it was nearly written into a record as a
defect.

## The files

`plan.json` is the plan: three milestones, fifteen decisions, the code
and doc diffs. `context.json` is what the plan was written against.
`qr-plan-design.json`, `qr-plan-code.json` and `qr-plan-docs.json` are
the three quality passes, each of which failed the plan at least once
before it passed. `plan.md` is the rendering.

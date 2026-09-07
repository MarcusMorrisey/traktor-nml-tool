# The reconstruct page's resolve step

The reconstruct page at `/` runs a sequence — configure, preview,
decide the conflicts, write — and draws none of it. The four inputs may
be filled in any order, but the three stages are ordered, and
`write_refusal` enforces that order by refusing after the click rather
than by showing it. This plan gives the page the four-step scaffold and
builds step 3 to `design/reconnect-wizard/Resolve.dc.html`.

## What is committed here

M-001 and M-002 of a three-milestone plan.

- **M-001** — `conflict_model.py` gains `ResolveGate`, `resolve_gate()`
  and `candidate_for_digit()`, so the footer sentence, the advancing
  control's enabled state and Specs' digit-to-answer arithmetic are all
  answered below the nicegui boundary. `theme.py` gains the step-rail,
  split, conflict-table, detail-rail, answer, bulk-strip and tally
  rules. Guards in `tests/test_gui_resolve_rules.py` and
  `tests/test_gui_resolve_sheet.py`.
- **M-002** — `reconstruct_steps.py` carries the step table, the rail
  records and the reachability rule, and imports no framework.
  `app.py` builds the rail, the four step regions with per-step footer
  groups, and `_render_resolve`: the tally and bulk strip, the conflict
  table under a header row, and the 400px rail holding one control per
  distinct answer. Guards in `tests/test_gui_reconstruct_steps.py`,
  `tests/test_gui_resolve_composition.py`, and additions to
  `tests/test_gui_keymap.py` and
  `tests/test_gui_conflict_page_controls.py`.

The suite reads 611 passed, 4 skipped under the system interpreter.

## What this commit owes

**M-002 is not closed.** DL-084 as DL-169 amends it makes a milestone's
pass condition a served-page record carrying a structural reading per
surface, and no record is written here. The composition M-002 builds —
the split, the table's grid and header row, the detail rail, the answer
card and its chosen state, the bulk strip, the tally — has been read
only off the emitted stylesheet and `app.py`'s source text. Whether the
browser resolves them as drawn is unread.

Reaching step 3 needs two collections that disagree on a track, loaded
through the page's own file picker. A pair producing four conflict rows
over `artist`, each with two candidates, is obtainable from
`testing/collections/iceJams3_theTroisFroid-playlist-only.nml` against
a copy of `iceJams3_theTroisFroid-complete-playlist-only.nml` with a
few `ARTIST` values altered; that pairing was confirmed against
`assemble_output` directly. Driving the picker to load them was not
possible in the session that wrote this.

**M-003 has not run.** It carries the decision log, so DL-198 through
DL-212 are not in `traktor_nml/README.md`. The code committed here
cites DL-199 and DL-202 through DL-206 in comments and docstrings, and
each of those citations names an entry the log does not yet hold. A
reader following one finds nothing until M-003 lands. M-003 also
revises DL-172, whose stated ground — that no artboard draws `/` — four
artboards on canvas page 3 have made false, and DL-191, which says the
column model, table geometry and detail rail entries stand as written
when this work rewrites all three.

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

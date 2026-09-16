# 2026-09-15 build-playlist GUI tab

A third route, `/build-playlist`, added to the NiceGUI wizard shell so an operator can build an NML playlist from a base collection plus a supplied Artist/Title tracklist entirely through the GUI, driving the same `buildplaylist.py`/`tracklist.py` core the CLI's `build-playlist` subcommand already uses (DL-260..DL-272).

## Status

**Design only.** This directory holds the plan's design phase (context, decisions, milestones, code intents) with QR passed (`qr-plan-design.json`, 41/41 items PASS after one fix iteration). It carries no `code_changes` — nothing here has been implemented yet. Milestones 1-3 are unimplemented work; Milestone 4 (the decision-log and index entries this README partially anticipates) has not been executed either — `traktor_nml/README.md`'s decision log does not yet carry DL-260 onward.

| File | What |
| --- | --- |
| `plan.json` | The plan: overview, DL-260 through DL-272, four milestones with their requirements, acceptance criteria, tests and code intents. No `code_changes` and no waves-with-dependencies beyond simple sequencing - this plan follows the scheme's lighter form. |
| `context.json` | The task spec this plan was designed from: scope, constraints, entry points, rejected alternatives and invisible knowledge. |
| `qr-plan-design.json` | The design-phase quality-review pass: 41 items, all PASS as of iteration 2. |
| `plan.md` | A rendering of `plan.json` for reading. |

## What this plan settles

**Not a step in either existing flow.** `design/reconnect-wizard/Specs.dc.html`'s own scope-fence note already rules out grafting build-playlist onto the reconnect wizard's stepper or the reconstruct page's step rail - it names build-playlist as having "its own review model" and being "its own entry point, not a branch of this one" (DL-260). The new screen is a fourth standalone route.

**A new artboard, drafted first.** Per DL-071's precedent (an artboard is the design of record), Milestone 1 opens with drafting `design/build-playlist/Specs.dc.html` before the screen's requirements are finalized, rather than inventing UI details unmoored from a design source (DL-265).

**The GUI drives the core, never reimplements it.** The screen's write path calls `buildplaylist.assemble_output`, `rewrite.py`'s collision/read/write helpers and `split.py`'s isolation pass directly, in the same order `build_playlist_cmd.py` already calls them - mirroring how `app.py` already drives the reconnect wizard's and reconstruct page's cores rather than duplicating their logic (DL-262). The CLI's own behavior, exit codes and output bytes are untouched.

**A third tab, the existing mechanism.** `navigation.SECTIONS` gains one row, read by `header_tabs` the same equality-only way as the other two (DL-263), per the header-tabs plan's own settled mechanism (`docs/plans/2026-09-03-header-tabs`, DL-129..DL-147).

**First pass ships a read-only report, not a review workflow.** Unresolved tracklist lines are shown read-only rather than through an interactive accept/reject/pick model, since a full review UI is flagged in `context.json` as a possible follow-on rather than assumed in scope (DL-264).

**No keyboard/accessibility milestone.** Per standing user preference, this plan schedules no keyboard-navigation, focus-ring, tab-order or announcement work for the new screen beyond whatever the existing shell already provides (DL-271) - the reconnect wizard's own such work already shipped, in the now-frozen `traktor-nml-tool-plan` repo, but that does not obligate this screen to redo it unasked.

**The DL high-water mark is read off the log, not assumed.** `traktor_nml/README.md` is the authority for the mark and states it as DL-259, the tail of the implemented `docs/plans/2026-09-15-resolve-detail-rail` block, so this plan's thirteen decisions are DL-260..DL-272 and its block shifts whole whenever an implemented block takes the numbers first - the rule `docs/2026-08-26-renderer-split-plan.md:92` states and `docs/plans/2026-09-03-header-tabs/README.md:24` follows. The mark is re-read against the live file immediately before an implementer writes these entries, since this directory is a point-in-time record and further work can land after it.

## Milestones

1. **Build-playlist artboard and route table entry** - `design/build-playlist/Specs.dc.html`, `navigation.py`'s third row, and the two existing-route regression tests it touches.
2. **Nicegui-free build-playlist view model** - `traktor_nml/gui/buildplaylist_view.py` (`form_errors`, `unresolved_report_rows`, `run_summary`), importable with no `nicegui` installed, on the `review_model.py`/`wizard_state.py` precedent.
3. **Build-playlist page wiring on the wizard shell** - `app.py`'s `_build_build_playlist_page`, plus a byte-identity guard (`tests/test_build_playlist_byte_identity.py`) proving the GUI's written output matches the CLI's for the same inputs.
4. **Decision log and plan record** - `traktor_nml/README.md` gains DL-260..DL-272; this README and `docs/plans/README.md`'s table are updated. Documentation-only.

This plan's own decisions are not yet in `traktor_nml/README.md` - that landing, along with Milestones 1-3's actual code, is future work.

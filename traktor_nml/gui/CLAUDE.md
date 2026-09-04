# traktor_nml/gui/

The reconnect wizard: the four-step surface (set up, scan, review, write)
built on the printless cores in `traktor_nml/reconnect_run.py` and the
decision logic below.

## Files

| File               | What                                                        | When to read                                    |
| ------------------- | ------------------------------------------------------------ | ------------------------------------------------ |
| `__init__.py`       | Package marker                                                | -                                                 |
| `review_model.py`   | `row_status` (a `RecordReview` plus a decision state into the six Specs statuses - matched, ambiguous, refuted, format, rejected, no_match), `display_confidence` (the four Strong/Good/Weak/None tokens, per candidate tier), `FILTERS` (the seven filter-chip predicates) and `filter_counts`. Imports no `nicegui`. | Changing a status, confidence-token, or filter derivation |
| `wizard_state.py`   | `WizardState` (per-record decisions: undecided/accepted/left_missing plus a picked candidate index), `apply`/`amended_result` (the amended mapping and the `ReconnectResult` built from it), `write_refusal`, `fingerprint_control_state`. Imports no `nicegui`. | Changing decision state, the amended-mapping/write-refusal rules, or the fingerprint-control-state check |
| `theme.py`          | Specs' measured palette, type scale, spacing and radius tokens, and `page_stylesheet()`, the string built from them. Imports no `nicegui`. | Changing a colour, a font size, a spacing step or a radius |
| `keymap.py`         | `ENTRIES` (one row per Specs key/scope/action/description), `dispatch` (the pure movement/range/pick arithmetic), `ACTION_NAMES`. Imports no `nicegui`. | Changing a key binding, adding an action, or changing dispatch arithmetic |
| `announce.py`       | The announcement text builders (`progress_message`, `decision_message`, `error_message`, `completion_message`), `POLITENESS`, and `ProgressAnnouncer`'s two-second throttle. Imports no `nicegui`. | Changing announcement wording, politeness, or the progress throttle |
| `conflict_model.py` | The conflict screen's candidate vocabulary and the operator's picks over it: `ConflictGroup`/`ConflictDecisions` (per identity key, `UNDECIDED` or a `CandidateRef` - the `(input index, primary key)` pair naming one of the answers the group offers - re-attached across a re-preview only where the group's member primary keys and its candidates are both identical), `candidate_reference`/`candidate_holding_input`/`reference_from_input` (the references a control and a bulk action name), `conflict_groups`, `rows`, `resolve`/`reset`/`decision`/`resolve_all`, `outstanding`, `resolutions` (the identity-key-to-pair mapping `_resolve_conflicts` takes, decided keys only), `write_refusal`/`write_refusal_sentence`, and `source_refusal`/`base_refusal`/`selection_refusal_sentence`. Imports no `nicegui`. | Changing a conflict decision state, the re-attachment rule, the resolutions mapping handed to splice, or a write/selection refusal |
| `navigation.py`     | `SECTIONS` (the ordered route-and-label table - `/` for the reconstruct page, `/reconnect` for the wizard - and the one place either route or either label is written), `header_tabs(active_route)` (one `HeaderTab` per row carrying route, label, selected, class string and `aria-current`), `TAB_CLASS`/`TAB_SELECTED_CLASS`/`ARIA_CURRENT_SELECTED`. Imports no `nicegui`. | Adding or renaming a section, changing a route, or changing which tab reads as selected |
| `_fs_nav.py`        | `LocalFilePicker`'s filesystem arithmetic: `DRIVE_LIST` (the sentinel for the virtual all-drives listing), `list_drive_roots` (the one-time Windows letter probe; empty on POSIX), `is_drive_root`, `parent_target` (where `..` leads, including from a drive root to `DRIVE_LIST`), `resolve_target` (the single computation both picker handlers call) and `entries_for` (the grid rows). Imports no `nicegui` or `webview`. | Changing drive navigation, what `..` resolves to, or which rows the picker lists |
| `app.py`            | Builds the wizard's four steps and drives `run_reconnection`/`write_reconnect_result` under `nicegui.run.io_bound`; feeds `ui.log` from `reconnect_render`'s line-producing functions over `RenderedOutput` | Changing a wizard step, the scan/write wiring, or the log feed |
| `file_picker.py`    | Server-side file/directory selection: pywebview's native dialog in native mode, NiceGUI's `local_file_picker` pattern otherwise | Changing file selection or the native/browser fallback |
| `__main__.py`       | `python -m traktor_nml.gui` entry point                       | Changing how the wizard starts                    |

## The nicegui boundary

`app.py`, `file_picker.py` and `__main__.py` are the only three modules
in this package that import `nicegui` or `pywebview`. Every other
module - `review_model.py`, `wizard_state.py`, `theme.py`, `keymap.py`,
`announce.py`, `conflict_model.py`, `navigation.py`, `_fs_nav.py` and
`__init__.py` - imports neither and is reachable from the test suite's
system interpreter, which has no `nicegui` installed. Every rule worth
testing sits below that boundary, in the nicegui-free modules, so the
suite can reach it (DL-069; guarded by an AST walk in
`tests/test_gui_view_boundary.py`).

## Why the wizard drives the cores directly

The wizard imports and calls `run_reconnection` and the two reconnect
cores in-process and renders its own view from `ReconnectResult`. It
does not shell out to `scan-reconnect-candidates`/`rewrite-from-reconnect`
and parse their key=value stdout. Tier 1 needs structured data while a
run is still open - a live scan progress feed and an interactive
ambiguous-match table the operator acts on mid-run - and a parsed
transcript exists only once the process has exited, so a scraping wizard
could build its review table only after the decision point the table
exists to serve, with no live object to cancel into. `ui.log` is instead
fed from `reconnect_render`'s line-producing functions over the
`RenderedOutput` they already return.

Subprocess-scraping the CLI transcript is not wrong; it was evaluated as
the data source for Tier 1, rejected, and survives as the
`docs/nicegui-gui-analysis.md` section 5 fallback if in-process
integration fails, and remains a correct way to obtain the same numbers
after a run (DL-075, `traktor_nml/README.md`).

## Where Specs.dc.html and docs/nicegui-gui-analysis.md disagree

`design/reconnect-wizard/Specs.dc.html` and sections 1-5 of
`docs/nicegui-gui-analysis.md` disagree in two places, and neither is
resolved by silently preferring one document over the other:

- **Status taxonomy and the keyboard map**: section 4 of
  `docs/nicegui-gui-analysis.md` names three review buckets (matched,
  ambiguous, dangling) against `ui.aggrid` with row selection; Specs
  names six statuses, seven filter chips, and a keyboard contract
  binding digits 1-9 to candidate picking, A/R/U to decisions, and
  Shift-arrow to range selection. **Specs governs** - it is the
  cross-screen contract for what the operator sees and presses.
  The review table renders hand-rolled `ui.row` rows per record;
  aggrid claims the arrow keys Specs binds over that same table, and
  is not adopted for it (DL-079). Section 4's three buckets are read
  against those rows. See `traktor_nml/README.md`'s Design Decisions
  section for DL-078 through DL-089.
- **Framework mechanics**: `run.io_bound` (not `run.cpu_bound`, since
  neither `TagCache` nor an lxml root pickles cleanly across a process
  boundary), `ui.log`, and the `local_file_picker` component are named
  only in section 4 - Specs names no framework at all. **Section 4
  governs** these three.

(DL-072, `traktor_nml/README.md`.)

## Design source of record

`design/reconnect-wizard/Specs.dc.html` is a committed source, read
alongside the other tracked `.dc.html` files and `canvas.json`;
`design/reconnect-wizard/reconnect-wizard.html` is the gitignored bundle
seeded from those sources. A screen disagreeing with Specs is fixed in
Specs, per `design/reconnect-wizard/README.md`'s own precedence rule
(DL-071).

## Tier classification is not re-derived here

`scan-reconnect-candidates`' membership in both Tier 1 (the wizard's
first step) and Tier 2 (generated-form eligibility) is resolved by
`tests/test_gui_command_classification.py`'s two predicates,
`PRIMARY_TIER` and `TIER2_ELIGIBLE`, checked against the real
`build_parser` choices. This package reads that dual membership as
settled rather than re-deriving a second classification (DL-073).

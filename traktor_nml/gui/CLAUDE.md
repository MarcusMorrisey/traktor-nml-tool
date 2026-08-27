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
| `app.py`            | Builds the wizard's four steps and drives `run_reconnection`/`write_reconnect_result` under `nicegui.run.io_bound`; feeds `ui.log` from `reconnect_render`'s line-producing functions over `RenderedOutput` | Changing a wizard step, the scan/write wiring, or the log feed |
| `file_picker.py`    | Server-side file/directory selection: pywebview's native dialog in native mode, NiceGUI's `local_file_picker` pattern otherwise | Changing file selection or the native/browser fallback |
| `__main__.py`       | `python -m traktor_nml.gui` entry point                       | Changing how the wizard starts                    |

## The nicegui boundary

`review_model.py` and `wizard_state.py` import no `nicegui` or `pywebview`
and are reachable from the test suite's system interpreter, which has no
`nicegui` installed. `app.py`, `file_picker.py` and `__main__.py` are the
only three modules in this package that import either; every rule worth
testing sits below that boundary, in the two framework-free modules, so
the suite can reach it (DL-069; guarded by an AST walk in
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

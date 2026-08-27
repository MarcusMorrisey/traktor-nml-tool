"""The reconnect wizard: the four-step surface of the design set - set
up, scan, review, write - built on top of the printless cores in
traktor_nml/reconnect_run.py and the decision logic in review_model.py
and wizard_state.py.

The wizard drives run_reconnection and the two reconnect cores directly
and renders its own view from ReconnectResult; it does not shell out to
the CLI and parse its key=value stdout, because Tier 1 needs structured
data - a live scan progress feed and an interactive ambiguous-match
table the operator acts on - while the run is still open, and a parsed
transcript exists only once the process has exited
(docs/nicegui-gui-analysis.md #2, #5; traktor_nml/gui/CLAUDE.md).

The scan runs under nicegui.run.io_bound: it is I/O-heavy and neither
TagCache nor an lxml root pickles cleanly across a process boundary, so
the thread-pool variant is the one that can carry them at all
(docs/nicegui-gui-analysis.md #4). ui.log is fed from the lines
reconnect_render's renderers produce over the RenderedOutput they
already return - stdout_lines and stderr_lines - rather than from a
stream write, so the same key=value vocabulary the CLI prints stays
visible here without opening a second implementation of it.

This module is deliberately untested by the suite (traktor_nml/README.md,
Tradeoffs): the suite runs on an interpreter with no nicegui installed.
Its one load-bearing property - that the Write control's provider
amends the scan result with the operator's decisions rather than
discarding them - is pinned instead by an AST walk in
tests/test_gui_view_boundary.py, which locates the call below and
asserts wizard_state.amended_result appears in its provider's body.
"""

from __future__ import annotations

import argparse
import threading
from pathlib import Path
from typing import Optional

from nicegui import run, ui

from .. import reconnect_run
from ..diskscan import ScanCancelled
from ..reconnect_render import (
    render_rewrite_from_reconnect,
    render_scan_reconnect_candidates,
)
from ..reconnect_run import ReconnectResult
from ..volumes import VolumeIdentityError
from . import review_model
from . import wizard_state
from .file_picker import pick_file_or_folder
from .wizard_state import WizardState

_KEYBOARD_MAP = (
    ("A", "Accept the highlighted file"),
    ("R", "Reject - leave this track missing"),
    ("U", "Undo the decision on this track"),
    ("Enter", "Accept, then jump to the next undecided track"),
    ("1-9", "Pick that candidate file (picking is not accepting)"),
    ("Shift + Up/Down", "Extend the selection for a bulk decision"),
    ("Alt 1-7", "Switch filter"),
)


class _WizardPageState:
    """One browser tab's worth of wizard state: the argparse Namespace
    the setup step builds, the scan result once it exists, the operator's
    WizardState decisions, and the row the review table has focused."""

    def __init__(self) -> None:
        self.args: Optional[argparse.Namespace] = None
        self.scan_result: Optional[ReconnectResult] = None
        self.scan_error: Optional[str] = None
        self.cancelled: bool = False
        self.decisions = WizardState()
        self.cancel_event: Optional[threading.Event] = None
        self.active_filter: str = review_model.QUEUE_FILTER_KEYS[0]
        self.focused_index: int = 0


def _build_args(
    old_input: Path,
    output: Path,
    scan_roots: list[Path],
    *,
    cache: Path,
    csv: Optional[Path],
    fingerprint: bool,
    refresh_cache: bool,
    dry_run: bool,
) -> argparse.Namespace:
    """The same Namespace shape build_parser() would hand
    reconnect_run's cores, built directly here since the wizard collects
    its inputs through its own widgets rather than argv."""
    return argparse.Namespace(
        old_input=old_input,
        output=output,
        scan_roots=scan_roots,
        volume_map=None,
        cache=cache,
        refresh_cache=refresh_cache,
        csv=csv,
        fingerprint=fingerprint,
        match_confidence="normal",
        no_refute=False,
        fpcalc_timeout=30.0,
        dry_run=dry_run,
    )


def _rows_for_filter(state: _WizardPageState, filter_key: str):
    reviews = state.scan_result.reviews
    rows = []
    for review in reviews:
        key = review.old.primary_key
        decision = state.decisions.decision_state(key)
        status = review_model.row_status(review, decision)
        if any(k == filter_key and pred(status, decision) for k, _label, pred in review_model.FILTERS):
            rows.append(review)
    return rows


def build_wizard() -> None:
    """Registers the wizard's single page at '/'. Called from
    __main__.py; kept separate from ui.run() so a test importing this
    module (which itself imports nicegui) is never exercised by the
    nicegui-free suite - only __main__.py calls both this and ui.run."""

    @ui.page("/")
    def index() -> None:
        state = _WizardPageState()

        with ui.column().classes("w-full max-w-5xl mx-auto gap-4"):
            ui.label("Reconnect wizard").classes("text-xl font-semibold")
            stepper = ui.stepper().props("vertical").classes("w-full")
            with stepper:
                _build_setup_step(state, stepper)
                _build_scan_step(state, stepper)
                _build_review_step(state, stepper)
                _build_write_step(state, stepper)


def _build_setup_step(state: _WizardPageState, stepper: ui.stepper) -> None:
    with ui.step("Set up"):
        ui.label("My playlists are broken: the collection they point at moved.")
        old_input_display = ui.label("No collection selected").classes("font-mono text-sm")
        old_input_holder: dict[str, Optional[Path]] = {"path": None}

        async def choose_old_input() -> None:
            path = await pick_file_or_folder(native=True, directories_only=False)
            if path is not None:
                old_input_holder["path"] = path
                old_input_display.set_text(str(path))

        ui.button("Choose collection file...", on_click=choose_old_input)

        scan_roots_list = ui.column().classes("gap-1")
        scan_roots_holder: list[Path] = []

        async def add_scan_root() -> None:
            path = await pick_file_or_folder(native=True, directories_only=True)
            if path is not None:
                scan_roots_holder.append(path)
                with scan_roots_list:
                    ui.label(str(path)).classes("font-mono text-sm")

        ui.button("Add scan root...", on_click=add_scan_root)

        cache_input = ui.input(
            "Tag cache path", value=".traktor_nml_tagcache.json"
        ).classes("w-full")
        ui.label(
            "Scanning updates this cache file; it is written independently of "
            "whether the collection itself is written."
        ).classes("text-xs text-grey-6")
        refresh_cache_switch = ui.switch("Refresh cache (discard prior scan work)")

        control = wizard_state.fingerprint_control_state()
        fingerprint_switch = ui.switch("Enable acoustic fingerprinting")
        if not control.enabled:
            fingerprint_switch.disable()
            ui.label(control.reason or "").classes("text-xs text-grey-6")

        output_input = ui.input("Output collection path").classes("w-full")

        def go_to_scan() -> None:
            if old_input_holder["path"] is None or not scan_roots_holder:
                ui.notify("Choose a collection file and at least one scan root", type="warning")
                return
            output_path = Path(output_input.value) if output_input.value else old_input_holder["path"]
            state.args = _build_args(
                old_input_holder["path"],
                output_path,
                list(scan_roots_holder),
                cache=Path(cache_input.value),
                csv=None,
                fingerprint=bool(fingerprint_switch.value) if control.enabled else False,
                refresh_cache=bool(refresh_cache_switch.value),
                dry_run=True,
            )
            stepper.next()

        ui.button("Continue", on_click=go_to_scan).props("color=primary")


def _build_scan_step(state: _WizardPageState, stepper: ui.stepper) -> None:
    with ui.step("Scan"):
        progress = ui.linear_progress(value=0).props("instant-feedback")
        progress_label = ui.label("Not started")
        log = ui.log().classes("w-full h-64")
        cancel_button = ui.button("Cancel")
        start_button = ui.button("Start scan").props("color=primary")

        def on_progress(done: int, total: int, path: Path) -> None:
            if total:
                progress.set_value(done / total)
            progress_label.set_text(f"{done} of {total}: {path}")

        async def run_scan() -> None:
            if state.args is None:
                return
            start_button.disable()
            state.cancel_event = threading.Event()

            def do_cancel() -> None:
                if state.cancel_event is not None:
                    state.cancel_event.set()

            cancel_button.on_click(do_cancel)

            reviews: list = []
            args = state.args
            cancel_event = state.cancel_event
            try:
                scan_result = await run.io_bound(
                    reconnect_run.scan_reconnect_candidates,
                    args,
                    on_progress=on_progress,
                    cancel=cancel_event,
                    reviews=reviews,
                )
            except ScanCancelled:
                state.cancelled = True
                log.push("scan_cancelled=true")
                start_button.enable()
                return

            rendered = render_scan_reconnect_candidates(scan_result, args)
            for line in rendered.stdout_lines:
                log.push(line)
            for line in rendered.stderr_lines:
                log.push(line)

            if scan_result.error is not None:
                state.scan_error = scan_result.error
                ui.notify(scan_result.error, type="negative")
                start_button.enable()
                return

            state.scan_result = scan_result.result
            state.decisions = WizardState()
            progress.set_value(1.0)
            stepper.next()

        start_button.on_click(run_scan)


def _candidate_panel(state: _WizardPageState, review) -> ui.column:
    panel = ui.column().classes("gap-2")
    with panel:
        ui.label(f"Old: {review.old.file_name}").classes("font-mono text-xs")
        for i, candidate_view in enumerate(review.candidates, start=1):
            confidence = review_model.display_confidence(candidate_view)
            ui.label(
                f"[{i}] {candidate_view.candidate.file_name} - {confidence}"
                + (" (refuted)" if candidate_view.refuted else "")
            ).classes("font-mono text-xs")
    return panel


def _build_review_step(state: _WizardPageState, stepper: ui.stepper) -> None:
    with ui.step("Review"):
        if state.cancelled:
            ui.label("Scan cancelled - no review table.").classes("text-warning")
            return

        filter_row = ui.row().classes("gap-2")
        table_container = ui.column().classes("w-full gap-1")
        comparison_container = ui.column().classes("w-full")

        def counts() -> dict[str, int]:
            rows = []
            for review in state.scan_result.reviews if state.scan_result else []:
                key = review.old.primary_key
                decision = state.decisions.decision_state(key)
                rows.append((review_model.row_status(review, decision), decision))
            return review_model.filter_counts(rows)

        def render_table() -> None:
            table_container.clear()
            if state.scan_result is None:
                return
            rows = _rows_for_filter(state, state.active_filter)
            with table_container:
                for review in rows:
                    key = review.old.primary_key
                    decision = state.decisions.decision_state(key)
                    status = review_model.row_status(review, decision)
                    with ui.row().classes("items-center gap-3 border-b py-1 w-full"):
                        ui.label(status).classes("w-24 font-mono text-xs")
                        ui.label(review.old.file_name).classes("flex-grow font-mono text-xs")
                        ui.button("A", on_click=lambda k=key: (state.decisions.accept(k), render_all())).props("dense")
                        ui.button("R", on_click=lambda k=key: (state.decisions.reject(k), render_all())).props("dense")
                        ui.button("U", on_click=lambda k=key: (state.decisions.undo(k), render_all())).props("dense")

        def render_filters() -> None:
            filter_row.clear()
            c = counts()
            with filter_row:
                for key, label, _pred in review_model.FILTERS:
                    text = f"{label} ({c[key]})"
                    button = ui.button(text, on_click=lambda k=key: select_filter(k)).props("outline dense")
                    if key == state.active_filter:
                        button.props("color=primary")

        def select_filter(key: str) -> None:
            state.active_filter = key
            render_all()

        def render_all() -> None:
            render_filters()
            render_table()

        render_all()

        with ui.expansion("Keyboard shortcuts"):
            for combo, description in _KEYBOARD_MAP:
                ui.label(f"{combo}: {description}").classes("text-xs")

        def go_to_write() -> None:
            stepper.next()

        ui.button("Continue to write", on_click=go_to_write).props("color=primary")


def _build_write_step(state: _WizardPageState, stepper: ui.stepper) -> None:
    with ui.step("Write"):
        if state.cancelled or state.scan_result is None:
            ui.label("Nothing to write.")
            return

        refusal_label = ui.label().classes("text-xs text-warning")
        write_button = ui.button("Write output").props("color=primary")

        dialog = ui.dialog()
        with dialog, ui.card():
            ui.label("Write the reconnected collection?")
            with ui.row():
                safe_button = ui.button("Cancel", on_click=dialog.close).props("autofocus")
                ui.button("Write", on_click=lambda: (dialog.close(), _do_write())).props("color=primary")
        # Enter never writes: the dialog's default/autofocus control is
        # the safe button, so a stray Enter closes without writing
        # rather than confirming (Specs.dc.html, "Dialogs").
        dialog.props("no-esc-dismiss=false")

        def refresh_refusal() -> None:
            reason = wizard_state.write_refusal(state.args.old_input, state.args.output)
            if reason is not None:
                refusal_label.set_text(reason)
                write_button.disable()
            else:
                refusal_label.set_text("")
                write_button.enable()

        refresh_refusal()

        output_log = ui.log().classes("w-full h-48")

        def _do_write() -> None:
            args = argparse.Namespace(**vars(state.args))
            args.dry_run = False

            def provide_result(old_root):
                """Returns wizard_state.amended_result(...) over the
                already-reviewed scan result and the operator's
                decisions, never the unamended scan result - the one
                load-bearing call this module makes
                (traktor_nml/README.md's DL-076), pinned by the AST
                walk in tests/test_gui_view_boundary.py rather than by
                a runtime test."""
                return wizard_state.amended_result(state.scan_result, state.decisions)

            try:
                result = reconnect_run.write_reconnect_result(args, provide_result)
            except VolumeIdentityError as exc:
                ui.notify(str(exc), type="negative")
                return
            rendered = render_rewrite_from_reconnect(result, args)
            for line in rendered.stdout_lines:
                output_log.push(line)
            for line in rendered.stderr_lines:
                output_log.push(line)
            if rendered.exit_code == 0:
                ui.notify("Collection written", type="positive")
            else:
                ui.notify("Write failed", type="negative")

        write_button.on_click(dialog.open)

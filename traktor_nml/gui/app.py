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
import time
import traceback
from pathlib import Path
from typing import Callable, Optional

from nicegui import run, ui

from .. import reconnect_run
from ..diskscan import ScanCancelled
from ..reconnect_render import (
    render_rewrite_from_reconnect,
    render_scan_reconnect_candidates,
)
from ..reconnect_run import ReconnectResult
from . import review_model
# theme.py is the only source for a colour or size literal in this module (DL-078).
from . import wizard_state
from .file_picker import pick_file_or_folder
from .wizard_state import WizardState
from . import theme
from . import keymap
from . import announce


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
        self.progress_announcer = announce.ProgressAnnouncer()
        self.polite_region = None
        self.assertive_region = None
        self.detail_open: bool = False
        # Every step is built once, up front in index(), before any
        # scan has run (DL-078's four steps are all constructed at
        # page-build time, not lazily on step change), so a step whose
        # initial render depends on state.scan_result - Review and
        # Write, so far - renders against None and stays frozen there:
        # stepper.next() only changes which step is visible, and
        # run_scan cannot reach either step's own render closure
        # directly, since _build_review_step and _build_write_step are
        # separate functions it has no scope into. Each such step
        # appends its own render function here once, at build time,
        # rather than exposing itself through a step-specific named
        # attribute - a second one of those was exactly this class of
        # bug, repeated - and run_scan calls every one of them, in
        # registration order, once a scan result actually lands
        # (state, the one thing every step-builder and run_scan
        # already share).
        self.step_refreshers: list[Callable[[], None]] = []


def _build_args(
    old_input: Path,
    output: Path,
    scan_roots: list[Path],
    *,
    volume_map: Optional[list[list[str]]],
    cache: Path,
    csv: Optional[Path],
    fingerprint: bool,
    refresh_cache: bool,
    dry_run: bool,
) -> argparse.Namespace:
    """The same Namespace shape build_parser() would hand
    reconnect_run's cores, built directly here since the wizard collects
    its inputs through its own widgets rather than argv. volume_map is
    already the [scan_root, volume, volumeid] triple list
    parse_volume_map (traktor_nml/volumes.py:83) accepts, or None - the
    Set up step's own wizard_state.build_volume_map produces exactly
    that shape, so no reshaping happens here."""
    return argparse.Namespace(
        old_input=old_input,
        output=output,
        scan_roots=scan_roots,
        volume_map=volume_map,
        cache=cache,
        refresh_cache=refresh_cache,
        csv=csv,
        fingerprint=fingerprint,
        # None, matching add_confidence_args' own --match-confidence
        # default, so resolve_confidence (shared_args.py, DL-010)
        # resolves it exactly as the CLI does: strict, since
        # allow_artist_title_only is also this wizard's unset default.
        match_confidence=None,
        allow_artist_title_only=False,
        no_refute=False,
        # 30.0, matching add_reconnect_args' own --fpcalc-timeout
        # default (reconnect_cmd.py's FPCALC_TIMEOUT_SECONDS fallback).
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

    def build_live_regions():
        """One polite live region and one assertive live region, each
        a ui.label so its text can be pushed through set_text() rather
        than through a hand-built .props() attribute string; app.py
        pushes into them only the strings announce.py returns, keeping
        the wording and the cadence out of the view entirely
        (DL-083)."""
        polite = ui.label("").props('role="status" aria-live="polite"').classes("sr-only")
        assertive = ui.label("").props('role="alert" aria-live="assertive"').classes("sr-only")
        return polite, assertive

    @ui.page("/")
    def index() -> None:
        # Quasar's primary set carries theme.ACTION; dark/dark-page are
        # fed from the ground and surface tokens so Quasar's own dark
        # components land on the measured surfaces rather than a
        # framework default (DL-078, DL-085).
        ui.colors(primary=theme.ACTION, dark=theme.SURFACE_2, dark_page=theme.GROUND)
        ui.dark_mode(True)
        ui.add_head_html(f"<style>{theme.page_stylesheet()}</style>")

        state = _WizardPageState()

        with ui.column().classes("w-full max-w-5xl mx-auto gap-4 wizard-surface"):
            ui.label("Reconnect wizard").classes("text-xl font-semibold")
            # Created once per page load, before any step that announces into them.
            state.polite_region, state.assertive_region = build_live_regions()
            stepper = ui.stepper().props("vertical").classes("w-full")
            with stepper:
                _build_setup_step(state, stepper)
                _build_scan_step(state, stepper)
                _build_review_step(state, stepper)
                _build_write_step(state, stepper)


def _build_setup_step(state: _WizardPageState, stepper: ui.stepper) -> None:
    with ui.step("Set up").classes("wizard-section-head"):
        ui.label("My playlists are broken: the collection they point at moved.")
        old_input_display = ui.label("No collection selected").classes("font-mono wizard-body-15 wizard-subtle-1")
        old_input_holder: dict[str, Optional[Path]] = {"path": None}

        async def choose_old_input() -> None:
            path = await pick_file_or_folder(directories_only=False)
            if path is not None:
                old_input_holder["path"] = path
                old_input_display.set_text(str(path))

        # ui.button's own color parameter defaults to "primary" (NiceGUI's
        # button.py), which Quasar renders as its own bg-primary/text-white
        # utility classes - both carry !important in the bundled
        # quasar.important.css, so no class this module adds could ever
        # have outranked them; color=None is the only place that works
        # (DL-086 rung one). Main.dc.html:97's "Choose file..." is a plain
        # .btn, not .btn-pri, so this control is deliberately not primary.
        ui.button("Choose collection file...", on_click=choose_old_input, color=None).classes("wizard-control wizard-label")

        scan_roots_list = ui.column().classes("gap-1")
        scan_roots_holder: list[Path] = []
        # One (volume_input, volumeid_input) pair per scan_roots_holder
        # entry, same index - wizard_state.build_volume_map zips the two
        # lists positionally, so a root and its pair of boxes must stay
        # appended together.
        volume_map_inputs: list[tuple[ui.input, ui.input]] = []

        async def add_scan_root() -> None:
            path = await pick_file_or_folder(directories_only=True)
            if path is not None:
                scan_roots_holder.append(path)
                default_volume, default_volumeid = wizard_state.default_volume_identity(path)
                with scan_roots_list:
                    # No design/reconnect-wizard artboard covers a
                    # volume-map control (none exists for it); wizard-control
                    # (theme.py CONTROL_HEIGHT/CONTROL_GAP) is applied here
                    # the same way it already is to this file's other
                    # controls (e.g. the Review step's A/R/U buttons below),
                    # for Specs' general 32px/8px rule rather than any
                    # artboard specific to this row.
                    with ui.row().classes("gap-2 items-center wizard-control"):
                        ui.label(str(path)).classes("font-mono wizard-body-11 wizard-subtle-2")
                        volume_input = ui.input("Volume", value=default_volume).classes("w-24")
                        volumeid_input = ui.input("Volume ID", value=default_volumeid).classes("w-24")
                    # Visible without hovering, matching the cache-path
                    # note below rather than a hover-only tooltip: the
                    # design set has no artboard for this control, so
                    # nothing else states what these two fields are.
                    # VOLUME/VOLUMEID are what this collection's own
                    # entries already record for this scan root; the
                    # pre-filled value, taken from the scan root's own
                    # drive, is usually right. volumes.py (DL-005)
                    # refuses to infer them from the stale recorded
                    # paths reconnection exists to fix, and a wrong or
                    # empty VOLUMEID produces a PRIMARYKEY Traktor
                    # cannot resolve.
                    ui.label(
                        "VOLUME and VOLUMEID are what this collection's own entries "
                        "record for this scan root. The pre-filled value comes from "
                        "the scan root's own drive and is usually right; a wrong or "
                        "empty VOLUMEID produces a PRIMARYKEY Traktor cannot resolve."
                    ).classes("wizard-subtle-3 wizard-note")
                volume_map_inputs.append((volume_input, volumeid_input))

        # No design/reconnect-wizard artboard covers this control (see the
        # comment on the volume-map row below); color=None is a judgement
        # call, not an artboard citation - Specs' single-primary-action
        # principle argues against a second blue button competing with
        # this step's own "Continue".
        ui.button("Add scan root...", on_click=add_scan_root, color=None).classes("wizard-control")

        cache_input = ui.input(
            "Tag cache path", value=".traktor_nml_tagcache.json"
        ).classes("w-full")
        ui.label(
            "Scanning updates this cache file; it is written independently of "
            "whether the collection itself is written."
        ).classes("wizard-subtle-3 wizard-note")
        refresh_cache_switch = ui.switch("Refresh cache (discard prior scan work)")

        control = wizard_state.fingerprint_control_state()
        fingerprint_switch = ui.switch("Enable acoustic fingerprinting")
        if not control.enabled:
            fingerprint_switch.disable()
            ui.label(control.reason or "").classes("wizard-body-11-5 wizard-dim")

        output_input = ui.input("Output collection path").classes("w-full")

        def go_to_scan() -> None:
            if old_input_holder["path"] is None or not scan_roots_holder:
                ui.notify("Choose a collection file and at least one scan root", type="warning")
                return
            output_path = Path(output_input.value) if output_input.value else old_input_holder["path"]
            entries = [(vi.value or "", vidi.value or "") for vi, vidi in volume_map_inputs]
            state.args = _build_args(
                old_input_holder["path"],
                output_path,
                list(scan_roots_holder),
                volume_map=wizard_state.build_volume_map(list(scan_roots_holder), entries),
                cache=Path(cache_input.value),
                csv=None,
                fingerprint=bool(fingerprint_switch.value) if control.enabled else False,
                refresh_cache=bool(refresh_cache_switch.value),
                dry_run=True,
            )
            stepper.next()

        # This step's one advancing action, and .btn-pri in Main.dc.html's
        # own footer. wizard-control-primary carries the action blue and
        # Review.dc.html:36's own ink together, which is why the
        # constructor passes color=None: Quasar's own bg-primary and
        # text-white are !important in the layer it orders last, and
        # text-white holds the label at 2.31:1 against the blue where the
        # artboard's ink measures 8.2:1 (DL-086 rung one).
        ui.button("Continue", on_click=go_to_scan, color=None).classes("wizard-control wizard-control-primary")


def _build_scan_step(state: _WizardPageState, stepper: ui.stepper) -> None:
    with ui.step("Scan").classes("wizard-header"):
        progress = ui.linear_progress(value=0).props("instant-feedback")
        progress_label = ui.label("Not started").classes("wizard-body-12-5 wizard-action")
        # Scanning.dc.html:88's scan counter and :98-106's three tile
        # values are the step's numeric displays, and on_progress is
        # the one live source for all four: the counter reads the
        # artboard's 'indexed / total files', and the tiles the
        # matched / needs-review / no-match counts among the reviews
        # scanned so far. They carry the display, title and status
        # colour tokens onto real Scan-step elements rather than onto
        # the page title or the Write control (DL-078). All four start
        # empty because no count exists before the first progress
        # callback.
        # Scanning.dc.html:88 nests the "/ N files" suffix as its own
        # smaller, faint <span> inside the big counter (<span class="big
        # mono">4,212<span class="faint" style="font-size:17px;...">
        # / 12,542 files</span></span>) rather than sizing the whole
        # string uniformly, so the counter is two labels, not one.
        with ui.row().classes("items-baseline gap-1"):
            scan_counter_display = ui.label("").classes("wizard-mono wizard-display")
            scan_counter_suffix = ui.label("").classes("wizard-mono wizard-heading-xs wizard-faint")
        # Scanning.dc.html:96-107's three <div class="tile"> each pair
        # a value (:97/:101/:105's <span class="v">) with a key
        # (:98/:102/:106's <span class="k">) naming what it counts -
        # "Matched so far", "Need your review", "No match found" - a
        # bare coloured number carries no meaning past whoever wrote
        # the code, which is the same finding as the review row's A/R/U
        # initials (Specs.dc.html, "Accessibility rules": no row relies
        # on a swatch). The icon each key also carries is not built
        # here - the word alone is the fix this finding asks for.
        with ui.row().classes("wizard-tiles w-full"):
            with ui.column().classes("wizard-tile"):
                scan_tile_found = ui.label("").classes("wizard-mono wizard-title wizard-status-found")
                ui.label("Matched so far").classes("wizard-body-11-5 wizard-dim")
            with ui.column().classes("wizard-tile"):
                scan_tile_review = ui.label("").classes("wizard-mono wizard-title wizard-status-review")
                ui.label("Need your review").classes("wizard-body-11-5 wizard-dim")
            with ui.column().classes("wizard-tile"):
                scan_tile_missing = ui.label("").classes("wizard-mono wizard-title wizard-status-missing")
                ui.label("No match found").classes("wizard-body-11-5 wizard-dim")
        log = ui.log().classes("w-full h-64 wizard-panel")
        # Scanning.dc.html:166 fixes "Stop scanning" as .btn-dgr
        # (border/background/text = STATUS_NOT_FOUND_STRONG/
        # STATUS_NOT_FOUND_TINT_BG/STATUS_NOT_FOUND_TINT_TEXT - the same
        # triple wizard-tag-missing already carries), not .btn-pri and
        # not a plain .btn either. color=None only removes the
        # definitely-wrong primary blue this control never should have
        # carried; the danger tint itself is not applied here and is a
        # separate finding, not invented into this fix.
        cancel_button = ui.button("Cancel", color=None).classes("wizard-control")
        # This step's one advancing action, primary for the same reason
        # and by the same mechanism as the Set up step's own Continue.
        start_button = ui.button("Start scan", color=None).classes("wizard-control wizard-control-primary")
        # Scanning.dc.html:166-167 fixes the step's forward control as
        # <button class="btn off" disabled>Review matches</button> -
        # plain, not primary, and disabled until a result exists. Its
        # own artboard footer carries no back-to-setup control (that
        # only appears on Cancelling.dc.html, a stop-scan confirmation
        # screen this wizard does not build), so this step gets a
        # forward control only, not a second Back.
        review_matches_button = ui.button("Review matches", on_click=lambda: go_to_review(), color=None).classes("wizard-control")
        review_matches_button.disable()

        # Populated in place by scan_reconnect_candidates (passed as
        # its reviews= argument below) - but only once run_reconnection
        # reaches resolve_reconnection, which starts after
        # index_scan_roots (the phase on_progress reports on) has
        # already finished, so reviews is still empty on every
        # on_progress callback: the tiles only reach their real counts
        # once the scan itself has completed, set from
        # state.scan_result.reviews in run_scan below rather than here.
        reviews: list = []

        def _set_scan_tiles(source) -> None:
            """Buckets `source` (RecordReview, review_model.UNDECIDED
            since no operator decision exists yet during a scan) into
            Scanning.dc.html:98-106's three tile counts - matched
            so far, needs review, no match found."""
            statuses = [review_model.row_status(r, review_model.UNDECIDED) for r in source]
            scan_tile_found.set_text(f"{sum(1 for s in statuses if s in ('matched', 'format')):,}")
            scan_tile_review.set_text(f"{sum(1 for s in statuses if s in ('ambiguous', 'refuted')):,}")
            scan_tile_missing.set_text(f"{sum(1 for s in statuses if s == 'no_match'):,}")

        def on_progress(done: int, total: int, path: Path) -> None:
            if total:
                progress.set_value(done / total)
            progress_label.set_text(f"{done} of {total}: {path}")
            scan_counter_display.set_text(f"{done:,}")
            scan_counter_suffix.set_text(f"/ {total:,} files")
            _set_scan_tiles(reviews)
            # time.monotonic(), not time.time(): the throttle only ever compares two calls against each other, never against a wall-clock deadline.
            message = state.progress_announcer.gate_progress(time.monotonic(), done, total)
            if message is not None and state.polite_region is not None:
                state.polite_region.set_text(message)

        def _sync_review_matches_button() -> None:
            """Enabled iff a result exists to review - Scanning.dc.html's
            own disabled/enabled distinction for this control, re-applied
            after every run rather than only after a successful one, so
            an earlier successful scan's result stays reachable even if
            a later rescan is cancelled or fails."""
            if state.scan_result is not None:
                review_matches_button.enable()
            else:
                review_matches_button.disable()

        def go_to_review() -> None:
            # Re-entering Review through this control needs the same
            # state.step_refreshers sweep go_to_write already uses - a
            # rescan run while the operator was elsewhere would otherwise
            # leave Review showing whatever it last rendered, the same
            # staleness risk the Write count had.
            for refresh_step in state.step_refreshers:
                refresh_step()
            stepper.next()

        async def run_scan() -> None:
            if state.args is None:
                return
            start_button.disable()
            review_matches_button.disable()
            state.cancel_event = threading.Event()

            def do_cancel() -> None:
                if state.cancel_event is not None:
                    state.cancel_event.set()

            cancel_button.on_click(do_cancel)

            reviews.clear()
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
                # A rescan that gets cancelled after an earlier one
                # succeeded must not leave the Write step showing that
                # earlier result: refreshing here lets its own
                # state.cancelled check land it back on "Nothing to
                # write." instead.
                for refresh_step in state.step_refreshers:
                    refresh_step()
                start_button.enable()
                _sync_review_matches_button()
                return
            except Exception as exc:
                # Broad on purpose, not a narrower type left uncaught:
                # this is the one boundary between the scan and the
                # operator, and scan_reconnect_candidates can fail in
                # ways no single narrower type covers - a bad
                # --match-confidence value raises ValueError, a bad
                # collection path raises OSError, and so on. Catching
                # only ScanCancelled above left every one of those
                # dying silently, which is the defect this closes
                # (Specs.dc.html, "Accessibility rules"). The traceback
                # still reaches the server log via traceback.print_exc,
                # so this is a wider net, not a swallow.
                traceback.print_exc()
                log.push(f"scan_failed={exc}")
                ui.notify(str(exc), type="negative")
                if state.assertive_region is not None:
                    state.assertive_region.set_text(
                        announce.error_message(str(args.output), f"scan failed: {exc}")
                    )
                start_button.enable()
                _sync_review_matches_button()
                return

            rendered = render_scan_reconnect_candidates(scan_result, args)
            for line in rendered.stdout_lines:
                log.push(line)
            for line in rendered.stderr_lines:
                log.push(line)

            if scan_result.error is not None:
                state.scan_error = scan_result.error
                ui.notify(scan_result.error, type="negative")
                # Names the output file first and the scan failure
                # second, the order Specs.dc.html, "Accessibility
                # rules" asks every assertive error to use.
                if state.assertive_region is not None:
                    state.assertive_region.set_text(
                        announce.error_message(str(state.args.output), f"scan failed: {scan_result.error}")
                    )
                start_button.enable()
                _sync_review_matches_button()
                return

            state.scan_result = scan_result.result
            state.decisions = WizardState()
            state.focused_index = 0
            progress.set_value(1.0)
            # The tiles reach their real counts here, not from any
            # on_progress callback: resolve_reconnection (the phase
            # that appends reviews) runs after indexing finishes, so
            # this is the first point at which reviews is complete.
            _set_scan_tiles(state.scan_result.reviews)
            # Every registered step_refreshers entry was built once,
            # up front in index(), against a None scan_result - without
            # this call each one stays frozen at whatever it rendered
            # then (an empty Review table, a bare "Nothing to write."
            # Write step) forever, since stepper.next() only changes
            # which step is visible.
            for refresh_step in state.step_refreshers:
                refresh_step()
            start_button.enable()
            _sync_review_matches_button()
            stepper.next()

        start_button.on_click(run_scan)


def _candidate_panel(state: _WizardPageState, review) -> ui.column:
    panel = ui.column().classes("gap-2")
    with panel:
        ui.label(f"Old: {review.old.file_name}").classes("font-mono wizard-heading-sm")
        for i, candidate_view in enumerate(review.candidates, start=1):
            confidence = review_model.display_confidence(candidate_view)
            # A refuted candidate reads at the inactive-marker weight
            # rather than the ordinary subtle-text weight (Specs.dc.html, "Confidence").
            weight_class = "wizard-inactive" if candidate_view.refuted else "wizard-subtle-4"
            ui.label(
                f"[{i}] {candidate_view.candidate.file_name} - {confidence}"
                + (" (refuted)" if candidate_view.refuted else "")
            ).classes(f"font-mono wizard-body-13 {weight_class}")
    return panel


def _announce_decision(state: "_WizardPageState", key: str, decision: str, rows: list) -> None:
    """Pushes each decision into the polite live region as it happens
    (Specs.dc.html, "Accessibility rules"; DL-083), naming the track,
    the decision and its position in the current filtered queue. A
    page under test (state.polite_region is None until index() creates
    the live regions) is a no-op rather than an AttributeError."""
    if state.polite_region is None:
        return
    position = next((i + 1 for i, r in enumerate(rows) if r.old.primary_key == key), len(rows))
    track_name = next((r.old.file_name for r in rows if r.old.primary_key == key), key)
    state.polite_region.set_text(announce.decision_message(track_name, decision, position, len(rows)))


# The WizardState method each decision name applies. A dict rather than a
# branch chain, for the reason DL-080 gives for _ACTION_APPLIERS: there is
# no branch an unnamed decision can fall through, so a name with no entry
# raises here instead of silently deciding nothing.
_BUTTON_DECISIONS = {
    "accepted": lambda decisions, key: decisions.accept(key),
    "rejected": lambda decisions, key: decisions.reject(key),
    "undone": lambda decisions, key: decisions.undo(key),
}


def _decide_from_button(state: "_WizardPageState", key: str, decision: str, render_all) -> None:
    """Applies a decision taken with the pointer and announces it, so a
    row button reaches the polite live region by the same path
    _applier_accept's keyboard route does - Specs fixes the
    announcement on the decision, not on the input device
    (Specs.dc.html, "Accessibility rules": each decision as it happens;
    DL-083).

    The row list is read before the decision is applied, the order the
    appliers use: _announce_decision reads the track name and the
    position out of it, and an accepted row leaves the Needs review
    filter, so a list read afterwards would announce the fallback key
    and a position of len(rows)."""
    rows = _rows_for_filter(state, state.active_filter)
    _BUTTON_DECISIONS[decision](state.decisions, key)
    _announce_decision(state, key, decision, rows)
    render_all()


def _applier_move(state: "_WizardPageState", args: dict, render_all) -> None:
    state.focused_index = args["index"]
    render_all()


def _applier_extend(state: "_WizardPageState", args: dict, render_all) -> None:
    state.focused_index = args["to"]
    render_all()


def _applier_accept(state: "_WizardPageState", args: dict, render_all) -> None:
    rows = _rows_for_filter(state, state.active_filter)
    if 0 <= state.focused_index < len(rows):
        key = rows[state.focused_index].old.primary_key
        state.decisions.accept(key)
        _announce_decision(state, key, "accepted", rows)
    render_all()


def _applier_accept_and_advance(state: "_WizardPageState", args: dict, render_all) -> None:
    """keymap.py's accept_and_advance entry reads 'Accept, then jump to
    the next undecided track' (Specs.dc.html:93); the next undecided
    row is searched for forward from the accepted row only, so a scan
    with no undecided rows left after it clamps focus in place rather
    than wrapping back to search from the top (Specs.dc.html:83's Home
    / End clamp the same way)."""
    rows = _rows_for_filter(state, state.active_filter)
    if 0 <= state.focused_index < len(rows):
        key = rows[state.focused_index].old.primary_key
        state.decisions.accept(key)
        _announce_decision(state, key, "accepted", rows)
        for i in range(state.focused_index + 1, len(rows)):
            if state.decisions.decision_state(rows[i].old.primary_key) == review_model.UNDECIDED:
                state.focused_index = i
                break
    render_all()


def _applier_reject(state: "_WizardPageState", args: dict, render_all) -> None:
    rows = _rows_for_filter(state, state.active_filter)
    if 0 <= state.focused_index < len(rows):
        key = rows[state.focused_index].old.primary_key
        state.decisions.reject(key)
        _announce_decision(state, key, "rejected", rows)
    render_all()


def _applier_undo_row(state: "_WizardPageState", args: dict, render_all) -> None:
    rows = _rows_for_filter(state, state.active_filter)
    if 0 <= state.focused_index < len(rows):
        key = rows[state.focused_index].old.primary_key
        state.decisions.undo(key)
        _announce_decision(state, key, "undone", rows)
    render_all()


def _applier_pick_candidate(state: "_WizardPageState", args: dict, render_all) -> None:
    """digit is 1-based (Specs' "1-9" keys); state.decisions.pick takes a 0-based candidate index, hence digit - 1."""
    rows = _rows_for_filter(state, state.active_filter)
    if 0 <= state.focused_index < len(rows):
        review = rows[state.focused_index]
        digit = args["digit"]
        if digit <= len(review.candidates):
            state.decisions.pick(review.old.primary_key, digit - 1)
    render_all()


def _applier_switch_filter(state: "_WizardPageState", args: dict, render_all) -> None:
    digit = args["digit"]
    if digit <= len(review_model.FILTERS):
        state.active_filter = review_model.FILTERS[digit - 1][0]
        state.focused_index = 0
    render_all()


def _applier_toggle_detail(state: "_WizardPageState", args: dict, render_all) -> None:
    state.detail_open = not state.detail_open
    render_all()


def _applier_noop(state: "_WizardPageState", args: dict, render_all) -> None:
    render_all()


# Dispatch returns an action name; this table is the only place an
# action name becomes an effect on state and the view, so there is no
# branch an unlisted action can fall through (DL-080). Its key set is
# pinned equal to keymap.ACTION_NAMES by tests/test_gui_keymap.py.
_ACTION_APPLIERS = {
    "move_up": _applier_move,
    "move_down": _applier_move,
    "move_home": _applier_move,
    "move_end": _applier_move,
    "extend_up": _applier_extend,
    "extend_down": _applier_extend,
    "accept": _applier_accept,
    "accept_and_advance": _applier_accept_and_advance,
    "reject": _applier_reject,
    "undo_row": _applier_undo_row,
    "pick_candidate": _applier_pick_candidate,
    "switch_filter": _applier_switch_filter,
    "toggle_detail": _applier_toggle_detail,
    "focus_next": _applier_noop,
    "focus_prev": _applier_noop,
    "jump_region": _applier_noop,
    "continue_step": _applier_noop,
    "undo_last": _applier_noop,
    "close_or_clear": _applier_noop,
    "dialog_safe_close": _applier_noop,
}


def _build_review_step(state: _WizardPageState, stepper: ui.stepper) -> None:
    with ui.step("Review").classes("wizard-hd-alt"):
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

        def _row_focus_style(row: ui.row, is_focused: bool) -> None:
            """Toggles the 'wizard-row-focused' class, whose outline
            and background come from the .wizard-row-focused rule
            page_stylesheet() emits (Specs.dc.html, "Accessibility
            rules"; DL-078, DL-084) - a control class applied from
            state.focused_index, not the browser's own :focus-visible
            pseudo-class, since a ui.row is not a focusable control
            Quasar's focus helper overlays. This is DL-086's rung two:
            a control class the framework's native focus styling does
            not reach on its own."""
            row.classes(
                add="wizard-row-focused" if is_focused else None,
                remove=None if is_focused else "wizard-row-focused",
            )

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
                    # The three review statuses (ambiguous, refuted,
                    # format) share wizard-status-review; a distinct
                    # icon silhouette and the written word tell them
                    # apart rather than a fourth colour
                    # (Specs.dc.html, "Status"; DL-079).
                    #
                    # The status label doubles as the row's tag badge,
                    # so each status names one class list carrying at
                    # most one colour-setting class. matched and
                    # rejected take the tinted tag surface alone,
                    # whose own rule sets the text colour that tint is
                    # designed for; the review statuses pair the
                    # review tint, which sets background and border
                    # only, with the status hue. Two color: rules on
                    # one element are both class selectors at 0,1,0,
                    # so <head> order rather than the token would
                    # decide which paints.
                    status_class = {
                        "matched": "wizard-tag-found",
                        "ambiguous": "wizard-tag-review wizard-status-review",
                        "refuted": "wizard-tag-review wizard-status-review",
                        "format": "wizard-tag-review wizard-status-review",
                        "rejected": "wizard-tag-missing",
                        "no_match": "wizard-faint",
                    }[status]
                    row = ui.row().classes("wizard-row items-center gap-3 border-b py-1 w-full")
                    # Identity comparison, not key comparison: rows is rebuilt fresh each render, so `is` picks out the one row object the current focused_index names.
                    _row_focus_style(row, review is rows[state.focused_index] if rows else False)
                    with row:
                        ui.label(status).classes(f"w-24 wizard-mono text-xs {status_class}")
                        ui.label(review.old.file_name).classes("flex-grow wizard-mono wizard-body-13-5")
                        # Review.dc.html:68's .dec group holds this
                        # row's own decision controls, separate from the
                        # row's own (wider) gap.
                        #
                        # Review.dc.html:156's .dec group carries the
                        # words "Accept"/"Reject", never initials - a
                        # screen reader has only "A button"/"R button"
                        # to announce otherwise (Specs.dc.html,
                        # "Accessibility rules"). Review.dc.html:37-38's
                        # .btn-ok/.btn-no tint each by outcome
                        # (wizard-decision-accept, wizard-tag-missing -
                        # existing status tokens, not action blue, which
                        # Specs reserves for the one primary action and
                        # Reject is not it).
                        #
                        # ui.button's own color parameter defaults to
                        # "primary" (NiceGUI's button.py) regardless of
                        # what .props() carries; Quasar renders that as
                        # its own bg-primary/text-white utility classes,
                        # both !important in the bundled
                        # quasar.important.css, so no class here could
                        # ever have outranked them - color=None at the
                        # constructor is the only place this is fixed
                        # (DL-086 rung one).
                        #
                        # Review.dc.html:148's .decd group is what a row
                        # that already carries a decision renders instead
                        # of .dec: one plain, untinted "Undo" button, not
                        # the accept/reject pair alongside a third
                        # button - undo_row (Specs' 'u') stays real and
                        # reachable, but only where Review.dc.html shows
                        # any undo affordance at all.
                        with ui.row().classes("wizard-control-group"):
                            if decision == review_model.UNDECIDED:
                                ui.button("Accept", on_click=lambda k=key: _decide_from_button(state, k, "accepted", render_all), color=None).props("dense").classes(
                                    "wizard-control wizard-decision-control wizard-body-12 wizard-decision-accept"
                                )
                                ui.button("Reject", on_click=lambda k=key: _decide_from_button(state, k, "rejected", render_all), color=None).props("dense").classes(
                                    "wizard-control wizard-decision-control wizard-body-12 wizard-tag-missing"
                                )
                            else:
                                ui.button("Undo", on_click=lambda k=key: _decide_from_button(state, k, "undone", render_all), color=None).props("dense").classes(
                                    "wizard-control wizard-decision-control wizard-body-12"
                                )

        def render_comparison() -> None:
            """Renders _candidate_panel for the focused row when
            'toggle_detail' (Space) has opened it, clearing
            comparison_container otherwise - the "detail panel beside
            the table" keymap.ENTRIES' toggle_detail description
            promises (Specs.dc.html, "Keyboard")."""
            comparison_container.clear()
            if not state.detail_open:
                return
            rows = _rows_for_filter(state, state.active_filter)
            if not rows or not (0 <= state.focused_index < len(rows)):
                return
            with comparison_container:
                _candidate_panel(state, rows[state.focused_index])

        def render_filters() -> None:
            filter_row.clear()
            c = counts()
            with filter_row:
                for key, label, _pred in review_model.FILTERS:
                    filter_text = f"{label} ({c[key]})"
                    # color=None here for the same reason the review
                    # row's decision buttons need it: ui.button's own
                    # color parameter defaults to "primary" regardless
                    # of what .props() carries, and outline mode maps
                    # that default to Quasar's own text-primary utility
                    # (also !important in quasar.important.css), which
                    # would paint the inactive chip's text primary-blue
                    # over wizard-tag-action-outline's own (colourless)
                    # rule, and would fight wizard-tag-action's own
                    # ACTION_TINT_TEXT for the active chip - the tokens
                    # this control already exists to carry.
                    ui.button(filter_text, on_click=lambda k=key: select_filter(k), color=None).props("outline dense").classes(
                        "wizard-control wizard-tag-action" if key == state.active_filter else "wizard-control wizard-tag-action-outline"
                    )

        def select_filter(key: str) -> None:
            state.active_filter = key
            render_all()

        def render_all() -> None:
            render_filters()
            render_table()
            render_comparison()

        # Registered so run_scan can refresh this step once a scan
        # result lands, since building it here (state.scan_result is
        # still None) is the only render_all call this construction
        # ever makes on its own.
        state.step_refreshers.append(render_all)

        render_all()

        def apply_action(action) -> None:
            """Looks up action.name in _ACTION_APPLIERS and calls the applier with action.args; a name with no applier (there is none, since the table's key set is pinned to keymap.ACTION_NAMES) is a no-op rather than a KeyError."""
            applier = _ACTION_APPLIERS.get(action.name)
            if applier is not None:
                applier(state, action.args, render_all)

        def on_key(e) -> None:
            """ui.keyboard's on_key handler: reads the focused row's own candidate count, resolves the keypress through keymap.dispatch scoped to the review table, and applies the resulting action."""
            rows = _rows_for_filter(state, state.active_filter)
            focused = rows[state.focused_index] if 0 <= state.focused_index < len(rows) else None
            candidate_count = len(focused.candidates) if focused is not None else 0
            action = keymap.dispatch(
                e.key.name,
                tuple(m for m in ("shift", "ctrl", "alt") if getattr(e.modifiers, m, False)),
                keymap.SCOPE_TABLE,
                len(rows),
                state.focused_index,
                candidate_count=candidate_count,
            )
            if action is not None:
                apply_action(action)

        # 'button' is dropped from NiceGUI's default ignore list: every
        # review row carries A/R/U buttons, so focus rests on a button
        # through ordinary review work, and the default list would
        # swallow the review keys at exactly that moment (DL-082).
        ui.keyboard(on_key=on_key, ignore=["input", "select", "textarea"])

        # The help panel renders only the SCOPE_TABLE entries this
        # step's single ui.keyboard actually dispatches; SCOPE_ANYWHERE
        # and SCOPE_DIALOG entries exist in keymap.ENTRIES for other
        # surfaces and are not rendered here, so nothing shown is
        # unbound (DL-080). A SCOPE_TABLE entry still bound to
        # _applier_noop is skipped too, so a key documented here
        # always has a real effect (DL-080).
        with ui.expansion("Keyboard shortcuts"):
            for entry in keymap.ENTRIES:
                if entry.scope != keymap.SCOPE_TABLE:
                    continue
                if _ACTION_APPLIERS.get(entry.action) is _applier_noop:
                    continue
                # Specs.dc.html:80-88's <div class="kr"> pairs a <span
                # class="k"> of one .kbd chip per key with a <span
                # class="d"> description; wizard-dot is Specs.dc.html:49's
                # list bullet, attached here since this shortcuts list
                # is this wave's rendered list of it.
                with ui.row().classes("items-baseline gap-3"):
                    ui.label("").classes("wizard-dot w-1.5 h-1.5 rounded-full")
                    with ui.row().classes("gap-1"):
                        for combo_key in (*entry.modifiers, entry.key):
                            ui.label(combo_key).classes("wizard-kbd")
                    ui.label(entry.description).classes("wizard-body-12-5 wizard-subtle-6")

        def go_to_write() -> None:
            # Every entry into Write, not only the first one after a
            # scan, must recompute its reconnect count and refusal
            # state against whatever state.decisions currently holds -
            # otherwise Write -> Back to review -> revise a decision ->
            # Continue to write again would show the count Write had
            # the first time it rendered, silently wrong rather than
            # missing. Sweeping the same state.step_refreshers registry
            # run_scan already sweeps, rather than a second path to
            # Write's own render, is what keeps this from drifting from
            # it - Review's own render_all is also in that list and
            # re-running it here is harmless, since it is already
            # idempotent against unchanged state.
            for refresh_step in state.step_refreshers:
                refresh_step()
            stepper.next()

        # Review.dc.html:325's <span class="ft-act"> groups "Back"
        # ahead of "Continue" in its own footer.
        with ui.row().classes("wizard-control-group"):
            # Review.dc.html:325 renders <button class="btn">Back</button>,
            # unlabelled - unlike Confirm.dc.html:178's "Back to review",
            # which names Write's own target (Review) explicitly. Scan
            # is this reader's inference from that naming pattern (every
            # other Back control in the design set names the step
            # immediately before it), not something the artboard states
            # outright for this one. Pure navigation - stepper.previous()
            # touches neither state.scan_result nor state.decisions.
            ui.button("Back", on_click=stepper.previous, color=None).classes("wizard-control")
            # This step's one advancing action. wizard-control-primary
            # carries the blue and the artboard's own ink together, so the
            # constructor passes color=None (DL-086 rung one).
            ui.button("Continue to write", on_click=go_to_write, color=None).classes("wizard-control wizard-control-primary")


def _build_write_step(state: _WizardPageState, stepper: ui.stepper) -> None:
    with ui.step("Write").classes("wizard-sec-alt"):
        container = ui.column().classes("w-full")

        def render() -> None:
            """Rebuilds this step's entire contents from state, rather
            than toggling a pre-built visibility flag: at build time
            state.scan_result is still None (every step is built once,
            up front, in index()), so 'Nothing to write.' is the only
            content that can exist yet, and the reconnect-count label,
            refusal label, write button, confirm dialog and output log
            below do not exist until a scan has actually landed a
            result. state.cancelled is re-checked here too, not
            assumed false, so a cancelled scan still lands on 'Nothing
            to write.' on every refresh, not only the first one."""
            container.clear()
            if state.cancelled or state.scan_result is None:
                with container:
                    ui.label("Nothing to write.")
                return

            with container:
                # The hero total (Results.dc.html:47's 40px .hero .n) names
                # the count wizard_state.apply already computes for the
                # Write control's own provider, so the displayed count and
                # the written mapping can never disagree (DL-076).
                reconnect_count = len(wizard_state.apply(state.scan_result, state.decisions))
                ui.label(f"{reconnect_count} tracks to reconnect").classes("wizard-mono wizard-display-xl")

                # Scanning.dc.html:46's .note.warn border and background
                # match STATUS_NEEDS_REVIEW_STRONG and
                # STATUS_NEEDS_REVIEW_TINT_BG - wizard-tag-review's pair,
                # which sets only background and border, so it reads as
                # the warning note here without stacking a second
                # colour-setting class onto the size and text-colour
                # tokens. Carried only while there is a reason to show
                # (refresh_refusal, below): wizard-tag-review paints a
                # background and a border even on empty text, so an
                # unconditional class here left a small tinted box
                # under the reconnect count with nothing refused to
                # show. Starts invisible for the same reason - an
                # empty label still reserves its own line.
                refusal_label = ui.label().classes("wizard-body-14-5 wizard-subtle-5")
                refusal_label.set_visibility(False)
                # Results.dc.html's own write control (.btn-pri) carries
                # the control type (13px), not a heading size - the Write
                # step's own hero total above already carries
                # wizard-display-xl, so this button needs no size token
                # of its own beyond wizard-control's own 32px floor.
                #
                # tabindex=0 is not decorative: QDialog.handleHide (in
                # the bundled quasar.umd.js) restores focus on hide by
                # calling refocusTarget.focus() directly for a
                # non-key-triggered hide, but for a key-triggered one it
                # instead calls
                # refocusTarget.closest('[tabindex]:not([tabindex^="-"])').focus()
                # - an attribute selector a plain <button> with no
                # explicit tabindex never matches, so Quasar's own
                # refocus silently finds nothing on that path. An
                # explicit tabindex=0 makes this element match its own
                # .closest() lookup, so Quasar's built-in mechanism can
                # reach it on both paths rather than only the click one.
                # Confirm.dc.html:178's <span class="ft-act"> groups
                # "Back to review" ahead of "Write collection..." in its
                # own footer.
                with ui.row().classes("wizard-control-group"):
                    # Confirm.dc.html:178 names this control's own
                    # target explicitly, unlike Review.dc.html:325's
                    # unlabelled "Back" - one step, to Review. Pure
                    # navigation - stepper.previous() touches neither
                    # state.scan_result nor state.decisions.
                    ui.button("Back to review", on_click=stepper.previous, color=None).classes("wizard-control")
                    # Results.dc.html's own write control, .btn-pri, through
                    # wizard-control-primary with color=None at the
                    # constructor (DL-086 rung one); tabindex=0 stays in
                    # props, it is not a colour prop.
                    write_button = ui.button("Write output", color=None).props("tabindex=0").classes("wizard-control wizard-control-primary")

                dialog = ui.dialog()
                with dialog, ui.card().classes("wizard-panel wizard-hairline"):
                    # Dialogs trap focus, open on the safe button, and
                    # return focus to whatever opened them (Specs.dc.html,
                    # "Accessibility rules"; DL-083, DL-078).
                    #
                    # Confirm.dc.html:57 (".dlg h2", 16px) governs this
                    # heading, not Cancelling.dc.html:34's 17px: Confirm
                    # is this exact dialog - its own h2 reads "Write
                    # 11,389 changes?", the same Cancel/Write pair, the
                    # same "Enter never writes" copy this dialog carries
                    # below. Cancelling.dc.html's 17px belongs to "Stop
                    # scanning?", a different confirmation this wizard
                    # does not build yet.
                    ui.label("Write the reconnected collection?").classes("wizard-heading-sm")
                    with ui.row():
                        # Confirm.dc.html:159 fixes this dialog's "Cancel" as a plain .btn,
                        # not .btn-pri - color=None removes the primary blue
                        # ui.button's own default would otherwise add.
                        safe_button = ui.button("Cancel", on_click=dialog.close, color=None).props("autofocus").classes("wizard-control")
                        # Confirm.dc.html:160's .btn-pri "Write collection", through
                        # wizard-control-primary with color=None at the constructor.
                        ui.button("Write", on_click=lambda: (dialog.close(), _do_write()), color=None).classes("wizard-control wizard-control-primary")
                # Enter never writes: the dialog's default/autofocus
                # control is the safe button, so a stray Enter closes
                # without writing rather than confirming (Specs.dc.html,
                # "Dialogs").
                dialog.props("no-esc-dismiss=false")
                # Quasar's own QDialog 'hide' event fires once regardless
                # of dismissal route - Cancel, Write, Escape or a
                # backdrop click all set the same model-value change - so
                # binding here (DL-086 rung one, the framework's own
                # mechanism) returns focus to the control that opened the
                # dialog on every path alike, rather than wiring each
                # close route separately (Specs.dc.html, "Accessibility
                # rules": dialogs "return focus to whatever opened
                # them").
                dialog.on("hide", lambda: write_button.run_method("focus"))

                def refresh_refusal() -> None:
                    # write_refusal() itself keeps returning the bare
                    # diagnostic token (output_must_differ_from_input,
                    # currently the only one it ever returns) - this
                    # renders wizard_state.write_refusal_sentence's
                    # operator-facing translation of it instead, so the
                    # Write step never shows the raw token the way it
                    # did before (Errors.dc.html's own card for the
                    # same defect never shows its token bare either).
                    reason = wizard_state.write_refusal(state.args.old_input, state.args.output)
                    if reason is not None:
                        refusal_label.set_text(wizard_state.write_refusal_sentence(reason))
                        refusal_label.classes(add="wizard-tag-review")
                        refusal_label.set_visibility(True)
                        write_button.disable()
                    else:
                        refusal_label.set_text("")
                        refusal_label.classes(remove="wizard-tag-review")
                        refusal_label.set_visibility(False)
                        write_button.enable()

                refresh_refusal()

                output_log = ui.log().classes("w-full h-48 wizard-panel")

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

                    # A volume-identity failure surfaces through
                    # result.error below, on the non-zero-exit_code
                    # branch: write_reconnect_result catches
                    # VolumeIdentityError itself and returns it as
                    # RewriteReconnectResult.error rather than raising.
                    result = reconnect_run.write_reconnect_result(args, provide_result)
                    rendered = render_rewrite_from_reconnect(result, args)
                    for line in rendered.stdout_lines:
                        output_log.push(line)
                    for line in rendered.stderr_lines:
                        output_log.push(line)
                    if rendered.exit_code == 0:
                        ui.notify("Collection written", type="positive")
                        # The write just succeeded, so this is the one
                        # place completion_message's "was written" is true
                        # (Specs.dc.html, "Accessibility rules").
                        if state.assertive_region is not None:
                            state.assertive_region.set_text(announce.completion_message(str(args.output)))
                    else:
                        ui.notify("Write failed", type="negative")
                        if state.assertive_region is not None:
                            state.assertive_region.set_text(
                                announce.error_message(str(args.output), "; ".join(rendered.stderr_lines))
                            )

                write_button.on_click(dialog.open)

        # Registered so run_scan can refresh this step once a scan
        # result lands, since building it here (state.scan_result is
        # still None) is the only render() call this construction ever
        # makes on its own.
        state.step_refreshers.append(render)

        render()

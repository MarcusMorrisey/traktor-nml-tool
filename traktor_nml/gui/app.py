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

# This file carries CRLF line endings throughout, alone in the
# package. Reading and rewriting it with newline set to the empty
# string keeps those endings intact, so a diff shows the edit rather
# than every line in the file; answer_detail.py, theme.py and the
# files under tests/ are LF (ref: DL-258).

from __future__ import annotations

import argparse
import threading
import time
import traceback
from pathlib import Path
from typing import Callable, NamedTuple, Optional

from nicegui import app as nicegui_app, run, ui

from .. import buildplaylist
from .. import playlistinput
from ..playlists import playlist_folder_choices
from .. import reconnect_run
from ..diskscan import ScanCancelled
from ..reconnect_render import (
    render_rewrite_from_reconnect,
    render_scan_reconnect_candidates,
)
from ..reconnect_run import ReconnectResult
from ..confidence import MatchConfidence
from ..rewrite import path_collides, read_and_parse_source, write_bytes_atomically
from ..spans import SpanIndex
from ..splice import assemble_output
from ..split import build_output as split_build_output
from ..xmlio import parse_xml_bytes
from . import answer_detail
from . import buildplaylist_view
from . import collection_summary
from . import conflict_model
from . import navigation
from . import reconstruct_report
from . import reconstruct_steps
from . import review_model
# theme.py is the only source for a colour or size literal in this module (DL-078).
from . import wizard_state
from . import wording
from .buildplaylist_view import FormInputs
from .file_picker import native_window, pick_file_or_folder, pick_save_path
from .wizard_state import WizardState
from . import theme
from . import keymap
from . import announce


class _WizardPageState:
    """One browser tab's worth of wizard state: the argparse Namespace
    the setup step builds, the scan result once it exists, the operator's
    WizardState decisions, the row the review table has focused, and the
    footer band's note and action row.

    The band's two elements live here for the same reason the live
    regions do: a step builder reaches them through the one object it
    already carries. footer_groups maps a step's own title to the pair
    (action row, note sentence) that step registers, which is what lets
    the step change decide which group the band shows rather than which
    group exists (DL-187).
    """

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
        # The footer band's note and its action group, held here for the
        # same reason every other page-wide element is: a step builder
        # reaches them through the one object it already carries, and a
        # step's advancing control is built in the band rather than
        # duplicated there (DL-187).
        self.footer_note = None
        self.footer_actions = None
        # One action group per step, keyed by the step's own title, with
        # the sentence that step's note carries. Every step is built up
        # front, so every group exists before the first step change; the
        # step change decides which one is shown rather than which one is
        # built.
        self.footer_groups: dict[str, tuple] = {}
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


# The directory theme.FONT_URL_BASE names, holding the seven vendored
# IBM Plex faces theme.FONT_FACES declares. Resolved from this file's
# own location so a wheel or a frozen build serves the copy it shipped
# rather than a path from the machine it was built on.
_FONTS_DIR = Path(__file__).resolve().parent / "fonts"

_fonts_mounted = False


def _mount_fonts() -> None:
    """Serve theme.py's font directory at the route theme.py names.

    The @font-face src and the route that answers it are one fact split
    across two modules: theme.py may not import nicegui (DL-069), so it
    holds FONT_URL_BASE and this side reads it rather than repeating the
    path. Mounting is idempotent because both pages call _page_chrome
    and nicegui raises on a route mounted twice.
    """
    global _fonts_mounted
    if _fonts_mounted:
        return
    nicegui_app.add_static_files(theme.FONT_URL_BASE, _FONTS_DIR)
    _fonts_mounted = True


class _PageChrome(NamedTuple):
    """What _page_chrome hands its caller: the middle container the
    route enters, and the two footer elements the route fills.

    One object because the three are built together: a route taking the
    middle alone would compose a page whose footer band still occupies
    its own height with nothing in it.
    """

    middle: ui.element
    footer_note: ui.label
    footer_actions: ui.row
    # middle is the container a route enters; footer_note and
    # footer_actions are the two halves of the band Main.dc.html:29-31
    # draws - .ft, holding .ft-note's sentence at the left and .ft-act's
    # controls at the right.


def _page_chrome(active_route: str) -> _PageChrome:
    """The colour, dark-mode and stylesheet preamble every page in this
    module applies, followed by the header the active route selects a
    tab in. Shared so a second route cannot drift from the wizard's own
    theme (DL-078, DL-085) and so the tab set cannot fork: both pages
    build their header from this one call site (DL-134).

    ui.header and ui.footer put the page into Quasar's own QLayout,
    which writes each band's height onto q-page-container as padding; a
    hand-rolled fixed band fights that reservation instead of using it
    (DL-183). Both are constructed at page top level, which is what
    nicegui's require_top_level_layout demands, and this function is the
    first call on both routes. The middle container is handed back
    rather than entered here, so a route's body lands inside the
    scrolling region by a with statement rather than by caller
    discipline (DL-185).
    """
    # Quasar's primary set carries theme.ACTION; dark/dark-page are fed
    # from the ground and surface tokens so Quasar's own dark components
    # land on the measured surfaces rather than a framework default.
    _mount_fonts()
    ui.colors(primary=theme.ACTION, dark=theme.SURFACE_2, dark_page=theme.GROUND)
    ui.dark_mode(True)
    ui.add_head_html(f"<style>{theme.page_stylesheet()}</style>")
    # bordered and elevated off: the rule and the shadow Quasar draws
    # are not the ones Main.dc.html:16 and :29 draw, and the band's own
    # rule in theme.py is (DL-183). The header row _build_header renders
    # keeps its own classes and its own content: what differs is where
    # the row sits.
    with ui.header(bordered=False, elevated=False).classes("wizard-header-band"):
        _build_header(active_route)
    middle = ui.element("div").classes("wizard-middle")
    with ui.footer(bordered=False, elevated=False).classes("wizard-footer-band"):
        footer_note = ui.label("").classes("wizard-footer-note")
        footer_actions = ui.row().classes("wizard-footer-actions")
    return _PageChrome(middle, footer_note, footer_actions)


def _build_header(active_route: str) -> None:
    """The brand mark, the divider and the section tab strip, in that
    order. One ui.link per record navigation.header_tabs(active_route)
    returns, in the order it returns them: the record's route is the
    link's target, its class string reaches .classes() and its
    aria-current value - present on the selected record alone - is
    rendered as a prop.

    Neither a route nor a label is written here. navigation.SECTIONS is
    the one place either is written and navigation.header_tabs decides
    which record is selected, so this function renders and decides
    nothing (DL-139, DL-144). The class strings it carries are
    navigation.TAB_CLASS and navigation.TAB_SELECTED_CLASS, whose
    values are theme.py's own "wizard-tab" and "wizard-tab-selected"
    rules.

    The class string is computed below the framework boundary, so it
    reaches .classes() through its add= parameter as a value rather
    than as a literal at this call site; what each tab actually carries
    is read back from a recording stub in
    tests/test_gui_header_tabs.py."""
    with ui.row().classes("items-center gap-3 wizard-header-bar wizard-content-width"):
        ui.label("traktor-nml-tool").classes("wizard-brand")
        ui.element("span").classes("wizard-header-divider")
        with ui.element("nav").props('aria-label="Sections"').classes(
            "flex items-center gap-1"
        ):
            for tab in navigation.header_tabs(active_route):
                link = ui.link(tab.label, tab.route).classes(add=tab.classes)
                if tab.aria_current is not None:
                    link.props(f'aria-current="{tab.aria_current}"')


def build_wizard() -> None:
    """Registers all three of the app's pages: the reconstruct page at
    '/', through _build_reconstruct_page below, the reconnect wizard at
    '/reconnect', and the build-playlist screen at '/build-playlist',
    through _build_build_playlist_page. Called from __main__.py; kept
    separate from ui.run() so a test importing this module (which
    itself imports nicegui) is never exercised by the nicegui-free
    suite - only __main__.py calls both this and ui.run."""

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

    _build_reconstruct_page()
    _build_build_playlist_page()

    @ui.page("/reconnect")
    def index() -> None:
        # Quasar's primary set carries theme.ACTION; dark/dark-page are
        # fed from the ground and surface tokens so Quasar's own dark
        # components land on the measured surfaces rather than a
        # framework default (DL-078, DL-085).
        # The three regions are built in the order header, middle,
        # footer, which is the order they read in the DOM and therefore
        # the order the tab ring walks them in; that order is read on a
        # served page rather than asserted here (DL-189, DL-197).
        chrome = _page_chrome("/reconnect")

        state = _WizardPageState()

        # Each step builder registers its own action group and note
        # sentence in state.footer_groups, so the control that advances a
        # step exists once, in the band, and its enabled state is held
        # once (DL-187). Its place in the DOM is what sets the tab order,
        # which is why the keyboard and the announcement records are read
        # again (DL-197).
        state.footer_note = chrome.footer_note
        state.footer_actions = chrome.footer_actions

        with chrome.middle:
            with ui.column().classes("gap-4 wizard-content-width"):
                # Created once per page load, before any step that announces into them.
                state.polite_region, state.assertive_region = build_live_regions()
                stepper = ui.stepper().props("vertical").classes("w-full")
                with stepper:
                    _build_setup_step(state, stepper)
                    _build_scan_step(state, stepper)
                    _build_review_step(state, stepper)
                    _build_write_step(state, stepper)

        def show_footer_for_step() -> None:
            """The band carries the active step's own group and note.

            Every group is built up front, alongside the step that owns
            it, so this decides which one is visible rather than which
            one exists - the same shape state.step_refreshers already
            takes for a step's own render.
            """
            active = stepper.value
            for name, (group, note) in state.footer_groups.items():
                group.set_visibility(name == active)
                if name == active:
                    state.footer_note.set_text(note)

        stepper.on_value_change(lambda _: show_footer_for_step())
        show_footer_for_step()


def _build_setup_step(state: _WizardPageState, stepper: ui.stepper) -> None:
    """The first step: the collection to repair, chosen through the file
    picker, and the Continue that reads it and moves to the scan.

    The step's card holds what the operator reads and acts on; its
    advancing control is built in the footer band and registered under
    this step's own title, so the control exists once and its enabled
    state is held once (DL-186, DL-187).
    """
    with ui.step("Set up").classes("wizard-section-head"):
        # Main.dc.html:32-35 draws each section as a card: a bordered
        # box, a header band carrying the section's title, and a padded
        # body. The class strings are literals at the call site, which is
        # what
        # tests/test_gui_theme.py::test_every_classes_call_expands_to_literals
        # reads - DL-188 keeps a dimension or a colour out of a call site,
        # not a class name.
        with ui.element("section").classes("wizard-card wizard-content-width"):
            with ui.element("div").classes("wizard-card-head"):
                ui.label("Your Traktor collection").classes("wizard-card-title")
            with ui.element("div").classes("wizard-card-body"):
                ui.label("My playlists are broken: the collection they point at moved.")
                # Main.dc.html:92's .row: the chosen path and the control that
                # chooses it on one line, the control sized to its label rather
                # than stretched across the card body's column (DL-299).
                with ui.element("div").classes("wizard-path-row"):
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
                    ui.button("Choose collection file...", on_click=choose_old_input, color=None).classes("wizard-control wizard-control-fill")

                # Main.dc.html:105's .card-t (13px/600) for the section this
                # control belongs to. The button label below names a concept
                # from the CLI's own --scan-root flag rather than anything the
                # operator has; the artboard's heading is what says what the
                # folders are for. (Naming that label here in full would break
                # tests/test_gui_button_color_defaults.py, which anchors on the
                # first occurrence of the literal string.)
                ui.label("Where your music is now").classes("wizard-body-13 font-semibold")
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
                ui.button("Add scan root...", on_click=add_scan_root, color=None).classes("wizard-control wizard-control-fill")
                # Main.dc.html:125's .meta (12px, TEXT_FAINT). Answers the
                # question the control itself raises - these folders are read,
                # nothing in them is written - which no other copy on this step
                # states.
                ui.label(
                    "These folders are read, never modified. Add the drive your music moved to."
                ).classes("wizard-body-12 wizard-faint")

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

                # The same .row for the output path: the typed path takes the
                # room and the control beside it takes its own width (DL-299).
                with ui.element("div").classes("wizard-path-row"):
                    output_input = ui.input("Output collection path").classes("w-full")

                    async def choose_output() -> None:
                        """Fills output_input from a chosen directory, keeping the
                        typed path authoritative - the input stays editable and
                        go_to_scan keeps reading it, so this control is a
                        convenience over typing rather than a second source of
                        truth.

                        Picks a directory rather than a file because the output is a
                        path being named, not an existing file to open: the
                        LocalFilePicker fallback can only select entries that
                        already exist, so a file pick could not name a new one. The
                        filename is appended here and stays editable.
                        """
                        directory = await pick_file_or_folder(directories_only=True)
                        if directory is None:
                            return
                        typed = Path(output_input.value) if output_input.value else None
                        name = (
                            typed.name if typed is not None and typed.name
                            else wizard_state.default_output_name(old_input_holder["path"])
                        )
                        output_input.value = str(directory / name)

                    # Matches "Choose collection file..." above: a plain .btn with
                    # color=None (DL-086 rung one), not primary.
                    ui.button("Choose output folder...", on_click=choose_output, color=None).classes("wizard-control wizard-control-fill")

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
        with state.footer_actions:
            with ui.row().classes("wizard-footer-actions") as group:
                ui.button("Continue", on_click=go_to_scan, color=None).classes(
                    "wizard-control wizard-control-primary"
                )
        state.footer_groups["Set up"] = (
            group,
            "Continue reads the collection and moves on to the scan.",
        )


def _build_scan_step(state: _WizardPageState, stepper: ui.stepper) -> None:
    """The scan step: the progress feed, the counter and the three status
    tiles, all fed from the one on_progress callback.

    Its three controls - cancel, start and the forward control - are
    built together in the footer band, because they read and set each
    other's enabled state and splitting them across the step and the
    band would hold that state in two places (DL-187).
    """
    with ui.step("Scan").classes("wizard-header"):
        # Main.dc.html:32-35 draws each section as a card: a bordered
        # box, a header band carrying the section's title, and a padded
        # body. The class strings are literals at the call site, which is
        # what
        # tests/test_gui_theme.py::test_every_classes_call_expands_to_literals
        # reads - DL-188 keeps a dimension or a colour out of a call site,
        # not a class name.
        with ui.element("section").classes("wizard-card wizard-content-width"):
            with ui.element("div").classes("wizard-card-head"):
                ui.label("Scanning your music folders").classes("wizard-card-title")
            with ui.element("div").classes("wizard-card-body"):
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
        # This step's three controls are built in the band together: the
        # cancel, the start and the forward control read and set each
        # other's enabled state, so splitting them across the step and
        # the band would hold that state in two places (DL-187).
        with state.footer_actions:
            with ui.row().classes("wizard-footer-actions") as group:
                # Scanning.dc.html:166 fixes "Stop scanning" as .btn-dgr
                # (border/background/text = STATUS_NOT_FOUND_STRONG/
                # STATUS_NOT_FOUND_TINT_BG/STATUS_NOT_FOUND_TINT_TEXT - the same
                # triple wizard-tag-missing already carries), not .btn-pri and
                # not a plain .btn either. color=None only removes the
                # definitely-wrong primary blue this control never should have
                # carried; the danger tint itself is not applied here and is a
                # separate finding, not invented into this fix.
                cancel_button = ui.button("Cancel", color=None).classes("wizard-control wizard-control-fill")
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
                review_matches_button = ui.button("Review matches", on_click=lambda: go_to_review(), color=None).classes("wizard-control wizard-control-fill")
        review_matches_button.disable()
        state.footer_groups["Scan"] = (
            group,
            "Review matches opens the rows the scan found.",
        )

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
    """The review step: the filter chips, the table of scanned rows and
    the comparison the focused row opens.

    The table's rows are laid out by the classes this builder names, not
    by the five-track grid the artboard draws; that difference is the
    Table geometry entry under 'Composition not built' in
    traktor_nml/README.md, and the entry states the reason it is open.
    The step's Back and Continue to write are built in the footer band
    (DL-187).
    """
    with ui.step("Review").classes("wizard-hd-alt"):
        # Main.dc.html:32-35 draws each section as a card: a bordered
        # box, a header band carrying the section's title, and a padded
        # body. The class strings are literals at the call site, which is
        # what
        # tests/test_gui_theme.py::test_every_classes_call_expands_to_literals
        # reads - DL-188 keeps a dimension or a colour out of a call site,
        # not a class name.
        # The review table's own grid geometry stays as it stands - the
        # Table geometry entry is outside this work's scope (DL-191).
        with ui.element("section").classes("wizard-card wizard-content-width"):
            with ui.element("div").classes("wizard-card-head"):
                ui.label("What the scan matched").classes("wizard-card-title")
            with ui.element("div").classes("wizard-card-body"):
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
                                    "wizard-control wizard-control-fill wizard-decision-control wizard-body-12"
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
        with state.footer_actions:
            with ui.row().classes("wizard-footer-actions") as group:
                # Review.dc.html:325 renders <button class="btn">Back</button>,
                # unlabelled - unlike Confirm.dc.html:178's "Back to review",
                # which names Write's own target (Review) explicitly. Scan
                # is this reader's inference from that naming pattern (every
                # other Back control in the design set names the step
                # immediately before it), not something the artboard states
                # outright for this one. Pure navigation - stepper.previous()
                # touches neither state.scan_result nor state.decisions.
                ui.button("Back", on_click=stepper.previous, color=None).classes("wizard-control wizard-control-fill")
                # This step's one advancing action. wizard-control-primary
                # carries the blue and the artboard's own ink together, so the
                # constructor passes color=None (DL-086 rung one).
                ui.button("Continue to write", on_click=go_to_write, color=None).classes("wizard-control wizard-control-primary")
        state.footer_groups["Review"] = (
            group,
            "Continue to write carries your decisions to the write step.",
        )


def _build_write_step(state: _WizardPageState, stepper: ui.stepper) -> None:
    """The write step: what the run will write, and the control that
    writes it after asking once more.

    This builder registers its footer group before render() first runs,
    because render() re-enters on every refresh and a group built there
    would be a second row in the band each time; render() clears and
    refills the one group instead (DL-187).
    """
    with ui.step("Write").classes("wizard-sec-alt"):
        # This step's own action group, built and registered here for
        # the same reason every step is built up front in index(): the
        # key has to exist before the first step change, and render()
        # below re-enters on every refresh, so a group built there would
        # be a second row in the band each time. render() fills this one
        # rather than making another (DL-187).
        with state.footer_actions:
            group = ui.row().classes("wizard-footer-actions")
        state.footer_groups["Write"] = (
            group,
            "Write output writes a new file, asking once more first.",
        )

        # Main.dc.html:32-35 draws each section as a card: a bordered
        # box, a header band carrying the section's title, and a padded
        # body. The class strings are literals at the call site, which is
        # what
        # tests/test_gui_theme.py::test_every_classes_call_expands_to_literals
        # reads - DL-188 keeps a dimension or a colour out of a call site,
        # not a class name.
        with ui.element("section").classes("wizard-card wizard-content-width"):
            with ui.element("div").classes("wizard-card-head"):
                ui.label("Writing the repaired collection").classes("wizard-card-title")
            with ui.element("div").classes("wizard-card-body"):
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
                        # The band carries this step's controls, so a state with
                        # nothing to write empties the group rather than leaving
                        # the controls of a run that no longer has a result
                        # beside 'Nothing to write.'
                        group.clear()
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
                        # The group itself is the one registered at the head of
                        # this builder, cleared and refilled, so a refresh
                        # replaces this step's controls rather than adding a
                        # second row beside them. The dialog the write control
                        # opens stays where it is built, a child of the page
                        # rather than of the band (DL-187).
                        group.clear()
                        with group:
                            # Confirm.dc.html:178 names this control's own
                            # target explicitly, unlike Review.dc.html:325's
                            # unlabelled "Back" - one step, to Review. Pure
                            # navigation - stepper.previous() touches neither
                            # state.scan_result nor state.decisions.
                            ui.button("Back to review", on_click=stepper.previous, color=None).classes("wizard-control wizard-control-fill")
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
                                safe_button = ui.button("Cancel", on_click=dialog.close, color=None).props("autofocus").classes("wizard-control wizard-control-fill")
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

# The error token assemble_output reports when a divergent identity group
# is left unresolved. The page the reconstruct screen answers, '/',
# renders the rows the same run
# returned in its place, so the token itself never reaches the operator.
def _source_labels(sources) -> list[str]:
    """One operator-facing name per source collection, in the order the
    operator added them.

    A name is the shortest trailing run of path segments that tells its
    source apart from every other listed source: the file name where
    nothing collides, the file name plus as many parent segments as it
    takes otherwise, and the whole resolved path where nothing shorter
    separates them. The walk terminates because the full resolved path
    always distinguishes - conflict_model.source_refusal has already
    refused any collection whose resolved path equals one already listed,
    so no two listed sources share one - and no input index is needed,
    since the path itself carries the distinction the operator chose the
    file by (DL-161).
    """
    resolved = [Path(path).resolve() for path in sources]
    labels: list[str] = []
    for path in resolved:
        parts = path.parts
        depth = len(parts)
        for run_length in range(1, len(parts) + 1):
            trailing = parts[-run_length:]
            if sum(1 for other in resolved if other.parts[-run_length:] == trailing) == 1:
                depth = run_length
                break
        if depth == len(parts):
            labels.append(str(path))
        elif depth == 1:
            labels.append(parts[-1])
        else:
            labels.append(f"{parts[-1]} ({'/'.join(parts[-depth:-1])})")
    return labels


def _collection_labels(sources) -> tuple[str, ...]:
    """The name of every collection a run reads, positioned at that
    collection's input index: the collection being repaired first, then
    the sources in the order the operator added them. A candidate's
    contributors are named by indexing this tuple with the input index
    each contributor carries (DL-148, DL-150)."""
    return ("base", *_source_labels(sources))


def _draw_step_rail(rail: ui.element, current: int) -> None:
    """Redraws the four-step rail over reconstruct_steps.rail_records.

    One span per record, in the order the table returns them, carrying
    the record's own class string and - on the current record alone -
    its aria-current value. Neither a number nor a label nor a class
    name is written here: reconstruct_steps.STEPS holds the table and
    reconstruct_steps decides which record is current, so this function
    renders and decides nothing (DL-202, DL-203). The class strings it
    carries are reconstruct_steps.STEP_CLASS, STEP_DONE_CLASS and
    STEP_CURRENT_CLASS, whose values are theme.py's own "wizard-step",
    "wizard-step-done" and "wizard-step-current" rules; the marker
    carries MARKER_CLASS and MARKER_CURRENT_CLASS, whose values are
    "wizard-step-number" and "wizard-step-number-current".

    The class string is computed below the framework boundary, so it
    reaches .classes() through its add= parameter as a value rather
    than as a literal at this call site; what each entry actually
    carries is read back from a recording stub in
    tests/test_gui_reconstruct_steps.py.
    """
    rail.clear()
    with rail:
        for record in reconstruct_steps.rail_records(current):
            with ui.element("span").classes(add=record.classes) as entry:
                ui.label(record.marker).classes(add=record.marker_classes)
                ui.label(record.label)
            if record.aria_current is not None:
                entry.props(f'aria-current="{record.aria_current}"')


# The reconstruct route's own name-to-applier table. The wizard's
# _ACTION_APPLIERS above is typed on _WizardPageState - its appliers read
# state.review_rows and state.decisions, neither of which this route
# holds - so the second table dispatches the same action names onto the
# resolve table's own holder rather than widening the first (DL-205).
#
# Its key set is a subset of keymap.ACTION_NAMES and covers every action
# the resolve table answers, which is what
# tests/test_gui_keymap.py holds, so DL-080's no-fall-through guarantee
# covers this table too: a name keymap.dispatch can return and this table
# does not carry is a suite failure rather than a silent no-op.
def _reconstruct_move(table: dict, args: dict) -> None:
    """Moves the resolve table's focus to the index dispatch clamped.

    The move is written through the table's own focus callback rather
    than into a field of its own, so a move applied by key and one
    applied by a control land in the one holder the render reads.
    """
    table["focus"](args["index"])


def _reconstruct_pick(table: dict, args: dict) -> None:
    """Picks the focused row's nth answer, counting the digit from one.

    Specs binds digits 1-9 to candidate picking over the table, and
    keymap.dispatch has already refused a digit past the focused row's
    own candidate count, so the index is inside the row's candidates
    (DL-071, DL-081).
    """
    group = table["groups"][table["holder"]["focused"]]
    candidate = conflict_model.candidate_for_digit(group.candidates, args["digit"])
    if candidate is not None:
        table["pick"](group, conflict_model.candidate_reference(candidate))


def _reconstruct_undo(table: dict, args: dict) -> None:
    """Returns the focused row to undecided, which is the state a key
    absent from the decision mapping already reads back."""
    table["reset"](table["groups"][table["holder"]["focused"]])


_RECONSTRUCT_ACTION_APPLIERS = {
    "move_up": _reconstruct_move,
    "move_down": _reconstruct_move,
    "move_home": _reconstruct_move,
    "move_end": _reconstruct_move,
    "pick_candidate": _reconstruct_pick,
    "undo_row": _reconstruct_undo,
}


CSV_TEMPLATE_FILENAME = "playlist-template.csv"


async def _deliver_csv_template() -> None:
    """Hand the operator csv_template_bytes(). Served over HTTP the
    browser saves it through ui.download. In the native window pywebview
    blocks browser downloads by default, so a SAVE dialog asks for the
    path and the bytes are written atomically here (DL-295). Module-level
    so a test can stub native_window, pick_save_path and ui.download."""
    data = playlistinput.csv_template_bytes()
    window = native_window()
    if window is None:
        ui.download(data, CSV_TEMPLATE_FILENAME)
        return
    path = await pick_save_path(window, save_filename=CSV_TEMPLATE_FILENAME)
    if path is None:
        return
    try:
        await run.io_bound(write_bytes_atomically, path, data)
    except OSError as exc:
        ui.notify(f"output_write_error={exc}", type="negative")
        return
    ui.notify(f"Written to {path}")


def _derive_build_playlist_output_path(base_path: Path, output_dir: str, name: str) -> Path:
    """The build-playlist write destination: <output folder>/<name>.nml,
    or the base collection's own directory when no output folder is
    chosen - the GUI counterpart of the CLI's positional output path.
    It takes no playlist folder: that names a place in the collection's
    playlist tree, not on disk, and a FOLDER NAME joined onto a disk path
    would place the file in a directory that need not exist (DL-297). This is
    the only place a build-playlist output path is computed; path_collides
    and the atomic write both consume its return value."""
    directory = Path(output_dir) if output_dir else base_path.parent
    return directory / f"{name}.nml"


def _run_build_playlist(
    inputs: FormInputs,
) -> tuple[buildplaylist.BuildPlaylistResult, Optional[playlistinput.InputRead]]:
    """The build-playlist write path's whole sequence: collision
    refusal, input read, assemble, the optional isolation pass, atomic
    write - the same order build_playlist_cmd.py's own handler calls
    them in, so neither this screen's behaviour nor its written bytes
    diverge from the CLI's (DL-262). Called under run.io_bound, never
    on the event loop directly. Returns the InputRead beside the result,
    None when the run refused before reading, so the summary can name the
    format and codec (DL-296)."""
    base_path = Path(inputs.base_path)
    input_path = Path(inputs.input_path)
    output_path = _derive_build_playlist_output_path(
        base_path, inputs.output_dir, inputs.name
    )

    if path_collides(output_path, base_path, input_path):
        return buildplaylist.BuildPlaylistResult(
            output=None, stats={}, unresolved_rows=[],
            errors=["output_must_differ_from_input"],
        ), None

    base_result = read_and_parse_source(base_path)
    if base_result.error is not None:
        return buildplaylist.BuildPlaylistResult(
            output=None, stats={}, unresolved_rows=[], errors=[base_result.error],
        ), None
    base_bytes, base_root = base_result.source_bytes, base_result.root

    # playlistinput.read_input is the one reader both surfaces call, so a
    # refusal code here is the string the CLI prints (DL-281).
    try:
        input_read = playlistinput.read_input(input_path)
    except playlistinput.InputReadError as exc:
        return buildplaylist.BuildPlaylistResult(
            output=None, stats={}, unresolved_rows=[],
            errors=[exc.code],
        ), None

    result = buildplaylist.assemble_output(
        base_bytes.decode("utf-8"), base_root, input_read.candidates, inputs.name,
        # The playlist folder is the CLI's --target-folder: a FOLDER NAME in
        # the collection, None for the root. It never touches output_path.
        target_folder=inputs.playlist_folder or None,
        allow_unmatched=inputs.allow_unmatched,
    )
    if result.output is None:
        return result, input_read

    output = result.output
    if not inputs.full_collection:
        # The normal hand-off is an importable, self-contained playlist,
        # not a copy of the whole source collection - build_playlist_cmd.py's
        # own --full-collection default (DL-262).
        isolated_root = parse_xml_bytes(output.encode("utf-8"))
        isolated = split_build_output(
            output, isolated_root, [str(result.stats["playlist_name"])], "fail",
            SpanIndex(output, isolated_root),
        )
        if isolated.output is None:
            return buildplaylist.BuildPlaylistResult(
                output=None, stats=result.stats, unresolved_rows=result.unresolved_rows,
                errors=isolated.errors,
            ), input_read
        output = isolated.output

    try:
        write_bytes_atomically(output_path, output.encode("utf-8"))
    except OSError as exc:
        return buildplaylist.BuildPlaylistResult(
            output=None, stats=result.stats, unresolved_rows=result.unresolved_rows,
            errors=[f"output_write_error={exc}"],
        ), input_read
    return result, input_read


def _build_build_playlist_page() -> None:
    """Registers the build-playlist screen at '/build-playlist'.

    Its own route rather than a step in either existing flow:
    design/build-playlist/Specs.dc.html's own scope-fence note names
    this as a separate job with its own review model, not a branch of
    the reconnect wizard (DL-260). The screen drives
    buildplaylist.assemble_output directly through
    _run_build_playlist above, never through build_playlist_cmd.py's
    own handler or an argparse Namespace (DL-262).
    """

    @ui.page("/build-playlist")
    def build_playlist_page() -> None:
        """The build-playlist screen: choose a base collection and a
        track list, name the playlist, and write it. Composes against
        the same shell as the other two routes - the same bands, the
        same middle, the same card structure."""
        chrome = _page_chrome("/build-playlist")

        base_holder: dict = {"path": None}
        input_holder: dict = {"path": None}
        output_dir_holder: dict = {"path": None}

        with chrome.middle:
            with ui.column().classes("gap-4 wizard-content-width"):
                with ui.element("section").classes("wizard-card wizard-content-width"):
                    with ui.element("div").classes("wizard-card-head"):
                        ui.label("Build a playlist from a track list").classes(
                            "wizard-card-title"
                        )
                    with ui.element("div").classes("wizard-card-body"):
                        ui.label(
                            "Match a track list, CSV, M3U playlist or folder of audio "
                            "files against a collection and write the matches as a new "
                            "NML playlist. Nothing here reads or changes an existing "
                            "playlist's own entries."
                        )

                        ui.label("Base collection").classes("wizard-label")
                        with ui.row().classes("buildplaylist-input-row"):
                            base_display = ui.label("No collection selected").classes(
                                "font-mono wizard-body-15 wizard-subtle-1"
                            )

                            async def choose_base() -> None:
                                path = await pick_file_or_folder(directories_only=False)
                                if path is not None:
                                    base_holder["path"] = path
                                    base_display.set_text(str(path))
                                    _refill_playlist_folders(path)
                                    _show_output_dir()
                                    _refresh_write_button()

                            ui.button(
                                "Choose file...", on_click=choose_base, color=None
                            ).classes("wizard-control wizard-control-fill")

                        ui.label("Input").classes("wizard-label")
                        with ui.row().classes("buildplaylist-input-row"):
                            input_display = ui.label("No input selected").classes(
                                "font-mono wizard-body-15 wizard-subtle-1"
                            )
                            format_tag = ui.label("").classes("buildplaylist-format-tag")
                            format_tag.set_visibility(False)

                            async def choose_input(directories_only: bool) -> None:
                                path = await pick_file_or_folder(directories_only=directories_only)
                                if path is None:
                                    return
                                input_holder["path"] = path
                                input_display.set_text(str(path))
                                # The tag shows what read_input will read the
                                # path as, before any run (DL-295).
                                format_tag.set_text(
                                    buildplaylist_view.format_label(playlistinput.detect_format(path))
                                )
                                format_tag.set_visibility(True)
                                _refresh_write_button()

                            ui.button(
                                "Choose file...", on_click=lambda: choose_input(False), color=None
                            ).classes("wizard-control wizard-control-fill")
                            ui.button(
                                "Choose folder...", on_click=lambda: choose_input(True), color=None
                            ).classes("wizard-control wizard-control-fill")
                        ui.label(
                            'A text file with one "Artist - Title" per line, a CSV, an M3U '
                            "or M3U8 playlist, or a folder whose audio files are read in "
                            "name order."
                        ).classes("wizard-subtle-1")

                        with ui.element("div").classes("wizard-callout"):
                            with ui.element("span").classes("buildplaylist-note-text"):
                                ui.label("CSV columns.").classes("buildplaylist-note-lead")
                                ui.label(buildplaylist_view.csv_columns_note())

                            # One control in both modes; _deliver_csv_template
                            # chooses ui.download or the SAVE dialog (DL-295).
                            ui.button(
                                "Download CSV template", on_click=_deliver_csv_template, color=None
                            ).classes("wizard-control wizard-control-fill buildplaylist-template-control")

                        name_input = ui.input(
                            "Playlist name", on_change=lambda _e: _refresh_write_button()
                        ).classes("w-full")

                        with ui.row().classes("buildplaylist-folder-row"):
                            with ui.column().classes("buildplaylist-folder-col"):
                                ui.label("Output folder").classes("wizard-label")
                                with ui.row().classes("buildplaylist-input-row"):
                                    output_dir_display = ui.label("").classes(
                                        "font-mono wizard-body-15 wizard-subtle-1"
                                    )

                                    async def choose_output_dir() -> None:
                                        path = await pick_file_or_folder(directories_only=True)
                                        if path is not None:
                                            output_dir_holder["path"] = path
                                            _show_output_dir()

                                    ui.button(
                                        "Choose folder...", on_click=choose_output_dir, color=None
                                    ).classes("wizard-control wizard-control-fill")
                            with ui.column().classes("buildplaylist-folder-col"):
                                playlist_folder_select = ui.select(
                                    {"": buildplaylist_view.COLLECTION_ROOT_LABEL},
                                    value="",
                                    label="Playlist folder",
                                ).classes("w-full")
                                # NiceGUI hands the browser each option's label
                                # and index, never its key, so Quasar's
                                # option-disable predicate greys out the
                                # shared-name folders by their label (DL-297).
                                playlist_folder_select.props(
                                    ":option-disable=\"opt => String(opt.label).endsWith('"
                                    + buildplaylist_view.SHARED_NAME_SUFFIX
                                    + "')\""
                                )
                                playlist_folder_note = ui.label(
                                    buildplaylist_view.PLAYLIST_FOLDER_NEEDS_FULL_COLLECTION
                                ).classes("wizard-subtle-1")

                        allow_unmatched_switch = ui.switch("Allow unmatched lines")
                        full_collection_switch = ui.switch(
                            "Full collection", on_change=lambda _e: _sync_playlist_folder()
                        )

                with ui.element("section").classes(
                    "wizard-card wizard-content-width"
                ) as report_section:
                    with ui.element("div").classes("wizard-card-head"):
                        ui.label("Unresolved entries").classes("wizard-card-title")
                    with ui.element("div").classes("wizard-card-body"):
                        report_table = ui.element("div").classes("buildplaylist-report")
                report_section.set_visibility(False)

        def _show_output_dir() -> None:
            # The placeholder names the folder the file goes to when none is
            # chosen, so the default is visible rather than implied.
            if output_dir_holder["path"] is not None:
                output_dir_display.set_text(str(output_dir_holder["path"]))
            elif base_holder["path"] is not None:
                output_dir_display.set_text(f"{base_holder['path'].parent} (the base collection's folder)")
            else:
                output_dir_display.set_text("The base collection's folder")

        def _sync_playlist_folder() -> None:
            # Full collection off: split.build_output keeps only the new
            # playlist under the root, so the chooser is disabled, reset to
            # Collection root, and the note says why (DL-297). The output
            # folder chooser applies either way and is left alone.
            full = bool(full_collection_switch.value)
            playlist_folder_select.set_enabled(full)
            playlist_folder_note.set_visibility(not full)
            if not full:
                playlist_folder_select.set_value("")

        def _refill_playlist_folders(base_path: Path) -> None:
            """Replace the chooser's options with the chosen base's FOLDERs.
            A base that fails to parse leaves only Collection root; the
            run itself reports the parse error."""
            parsed = read_and_parse_source(base_path)
            choices = [] if parsed.error is not None else playlist_folder_choices(parsed.root)
            options = buildplaylist_view.playlist_folder_options(choices)
            # A disabled option still needs its own key, and its NAME is not
            # unique; a NUL-prefixed label is a key no FOLDER NAME can equal.
            playlist_folder_select.set_options(
                {(o.value if o.enabled else "\0" + o.label): o.label for o in options},
                value="",
            )

        def _current_inputs() -> FormInputs:
            return FormInputs(
                base_path=str(base_holder["path"] or ""),
                input_path=str(input_holder["path"] or ""),
                name=name_input.value or "",
                output_dir=str(output_dir_holder["path"] or ""),
                playlist_folder=_selected_playlist_folder(),
                allow_unmatched=bool(allow_unmatched_switch.value),
                full_collection=bool(full_collection_switch.value),
            )

        def _selected_playlist_folder() -> str:
            """The playlist folder the run passes as target_folder: the
            chooser's NAME, "" for Collection root or a disabled key, and
            "" whenever Full collection is off (DL-297)."""
            value = playlist_folder_select.value or ""
            # A disabled option's key starts with NUL and is never a NAME.
            selected = "" if value.startswith("\0") else value
            return buildplaylist_view.effective_playlist_folder(
                bool(full_collection_switch.value), selected
            )

        def _refresh_write_button() -> None:
            errors = buildplaylist_view.form_errors(_current_inputs())
            write_button.set_enabled(not errors)
            chrome.footer_note.set_text(" ".join(errors))

        async def write_playlist() -> None:
            inputs = _current_inputs()
            errors = buildplaylist_view.form_errors(inputs)
            if errors:
                chrome.footer_note.set_text(" ".join(errors))
                return
            result, input_read = await run.io_bound(_run_build_playlist, inputs)
            # The summary names the format and codec the run read, from the
            # InputRead the run returned (DL-296).
            chrome.footer_note.set_text(
                buildplaylist_view.run_summary(
                    result,
                    input_read.format if input_read is not None else None,
                    input_read.encoding if input_read is not None else "",
                )
            )

            report_table.clear()
            rows = buildplaylist_view.unresolved_report_rows(result)
            report_section.set_visibility(bool(rows))
            # The header is a modifier row on the body rows' own grid, so
            # a heading stands over its column at every row (DL-302).
            with report_table:
                with ui.element("div").classes(
                    "buildplaylist-report-grid buildplaylist-report-header"
                ):
                    for column_label in buildplaylist_view.REPORT_COLUMN_LABELS:
                        ui.label(column_label)
                for line_number, raw_text, kind in rows:
                    with ui.element("div").classes(
                        "buildplaylist-report-grid buildplaylist-report-row"
                    ):
                        ui.label(str(line_number)).classes("font-mono wizard-dim")
                        ui.label(raw_text).classes("font-mono buildplaylist-report-entry")
                        # Specs.dc.html:179-181 draws the kind inside
                        # its cell as a pill, so the cell keeps the body
                        # row's own inset and the pill hugs its word.
                        # The class comes from the kind through
                        # buildplaylist_view, so the rule the sheet
                        # gives that kind is the one the page applies.
                        with ui.element("div"):
                            ui.label(
                                buildplaylist_view.kind_pill_label(kind)
                            ).classes(buildplaylist_view.kind_pill_classes(kind))
            # The report card stands below the form, past the fold of
            # wizard-middle, the scroll owner (DL-189). A run that leaves
            # rows brings the card into view; a run with none does not
            # scroll. The message is queued after the card's updates, so
            # the browser shows the card before it scrolls to it (DL-303).
            if rows:
                ui.run_javascript(
                    f"getHtmlElement({report_section.id})"
                    ".scrollIntoView({block: 'start', behavior: 'smooth'})"
                )

        with chrome.footer_actions:
            write_button = ui.button(
                "Write playlist", on_click=write_playlist, color=None
            ).classes("wizard-control wizard-control-primary")

        _refresh_write_button()
        _show_output_dir()
        _sync_playlist_folder()


# Write.dc.html:164-166's three assurances: what the confirmation states
# before the write is made. Each is a fact about this run that the code
# above enforces - a new file at the chosen path, every input left as it
# was, and Traktor reading its own collection until the operator imports
# the new one.
def _build_reconstruct_page() -> None:
    """Registers the playlist-reconstruction screen at '/'.

    Its own route rather than a step in the reconnect stepper: the two
    operations share no pipeline. Reconnection scans a disk and reviews
    per-track matches, while reconstruction reads a second collection and
    resolves whole playlists, so a step wedged into that stepper would sit
    in every reconnect run with nothing to contribute and would inherit
    run_scan's own reset of state.decisions. The theme, the control tokens
    and the file picker are shared; the flow is not.
    """

    @ui.page("/")
    def reconstruct() -> None:
        """The reconstruct page: the collection to repair, the
        collections to take playlists from, where the output goes, and
        what to do where they disagree.

        It composes against the same shell as the wizard - the same
        bands, the same middle, the same card triplet - and its two
        primary controls are built in the footer band. DL-172 decides
        what a served-page record may verdict about this route, not
        which shell it is built from (DL-191).
        """
        chrome = _page_chrome("/")

        base_holder: dict = {"path": None}
        source_holder: list = []
        result_holder: dict = {"result": None}
        # The ConflictGroups the last run reported, as conflict_model
        # derives them. Held beside the result so the write control and the
        # rows read the same set the run produced.
        conflict_holder: list = []
        # The operator's picks, keyed by identity group. Held beside the
        # other holders so they outlive a re-preview and are discarded with
        # the process; a pick whose group membership the new run changed
        # reads back undecided (DL-107, DL-115).
        decisions = conflict_model.ConflictDecisions()

        # Which step the page is showing, and the per-step footer
        # groups the band swaps between. The number is held rather than
        # derived: reconstruct_steps.reachable says where the operator
        # may go and this says where they are, and the two are separate
        # questions (DL-202).
        step_holder: dict = {"current": reconstruct_steps.SET_UP}
        footer_groups: dict = {}
        # The resolve step's advancing control and the row the rail
        # describes, held so the draw that answers a pick reaches both.
        resolve_holder: dict = {"advance": None, "focused": 0}
        # The write step's confirmation heading, held so the render that
        # reads the run reaches the dialog the footer opens.
        write_holder: dict = {"question": None, "assurances": None, "confirm": None}
        # The output path this run has written, or None. Set where the
        # write lands and cleared wherever the file on disk stops being
        # what the step describes - which is any new assembly, since the
        # bytes a later run produces are not the bytes already written.
        written_holder: dict = {"path": None}

        # The rail is the page region's first row and the four step
        # regions follow it, one visible at a time. A region is a
        # container the page enters with a with statement, so each
        # step's content keeps its own nesting rather than being
        # re-parented into framework markup, and the rail is a nav of
        # this module's own spans rather than a QStepper header, which
        # draws its own numbered strip and no step of the artboard's
        # rail (DL-199, DL-203).
        with chrome.middle:
            rail = ui.element("nav").props('aria-label="Progress"').classes(
                "wizard-step-rail wizard-content-width"
            )
            regions = {
                number: ui.column().classes("gap-4 wizard-content-width")
                for number, _ in reconstruct_steps.STEPS
            }

        def show_step(number: int) -> None:
            """Shows one step: its region, its footer group and its
            sentence, and the rail entry marked current.

            Every region and every group is built up front, alongside
            the step that owns it, so this decides which one is visible
            rather than which one exists - the same shape the wizard's
            own show_footer_for_step takes (DL-187).
            """
            step_holder["current"] = number
            for step_number, region in regions.items():
                region.set_visibility(step_number == number)
            for step_number, (group, note) in footer_groups.items():
                group.set_visibility(step_number == number)
                if step_number == number:
                    chrome.footer_note.set_text(note)
            # The two steps that report the run are drawn on the way in
            # rather than once: what each says is answered by controls on
            # the steps beside it - the answers given at resolve, the
            # output path named at set up - so a panel drawn once would
            # state the run as it stood before those answers were given.
            if number == reconstruct_steps.PREVIEW:
                _render_preview()
            if number == reconstruct_steps.WRITE:
                _render_write()
            _draw_step_rail(rail, number)

        def run_is_stale() -> bool:
            """Whether the held run reports something other than the
            answers now given.

            A run that produced no output is stale by definition - there
            is nothing to report - and so is one assembled before an
            answer was given or changed (DL-225).
            """
            if not conflict_model.run_assembled(result_holder["result"]):
                return True
            return not conflict_model.run_is_current(
                result_holder["resolutions"], decisions, conflict_holder
            )

        async def advance_to(number: int) -> None:
            """Walks to one step, or names why it is shut.

            The write step is entered on a run that reports the answers
            now given, so the walk re-assembles first where the held run
            does not. Without it the operator answers every conflict and
            the step still reports the run that refused before they
            started: zeros for what the file holds, beside a count of
            answers read off the decisions (DL-224, DL-225).

            reachable() reads that run and the resolve gate, so the
            refusal and the sentence the resolve footer prints are one
            answer rather than two (DL-204).
            """
            gate = conflict_model.resolve_gate(decisions, conflict_holder)
            if (
                number == reconstruct_steps.WRITE
                and gate.all_decided
                and run_is_stale()
            ):
                await assemble()
                gate = conflict_model.resolve_gate(decisions, conflict_holder)
            result = result_holder["result"]
            if not reconstruct_steps.reachable(
                number,
                result is not None,
                conflict_model.run_assembled(result),
                gate.all_decided,
            ):
                ui.notify(
                    conflict_model.write_refusal_sentence(
                        conflict_model.write_refusal(
                            result_holder["result"], decisions, conflict_holder
                        )
                        or conflict_model.WriteRefusal(conflict_model.NO_PREVIEW)
                    ),
                    type="warning",
                )
                return
            show_step(number)

        with regions[reconstruct_steps.SET_UP]:
            # What each chosen collection reports about itself, keyed the
            # way the page holds the collections themselves: one summary
            # for the collection being repaired and one per source. Held
            # beside the paths rather than derived at render, because
            # summarising parses the file and a render runs on every
            # redraw of the step.
            summaries: dict = {"base": None, "sources": {}}

            def discard_run() -> None:
                """Discards the run and what it reported.

                A held result was assembled over the collections the run
                read, so leaving it in place after one of them leaves the
                page would let the write control write an output built from
                a collection no control names. The picks stay, and
                conflict_model re-attaches the ones whose group membership
                the next run leaves unchanged (DL-115).
                """
                result_holder["result"] = None
                conflict_holder.clear()
                report.clear()

            async def _summarise(path):
                """One chosen collection's own counts, or None with the
                reason already notified.

                Parsing is a file read, so it goes through run.io_bound
                the way every other read on this page does. A file that
                will not parse is refused here rather than at Preview: the
                step that took the file is the step that can say so
                (DL-220).
                """
                loaded = await run.io_bound(read_and_parse_source, path)
                if loaded.error is not None:
                    ui.notify(loaded.error, type="negative")
                    return None
                return collection_summary.summarise(loaded.root)

            async def choose_base() -> None:
                path = await pick_file_or_folder(directories_only=False)
                if path is None:
                    return
                refusal = conflict_model.base_refusal(path, source_holder)
                if refusal is not None:
                    ui.notify(
                        conflict_model.selection_refusal_sentence(refusal), type="warning"
                    )
                    return
                summary = await _summarise(path)
                if summary is None:
                    return
                base_holder["path"] = path
                summaries["base"] = summary
                discard_run()
                draw_base()
                draw_output_note()

            def remove_base() -> None:
                """Returns the page to naming no collection to repair."""
                base_holder["path"] = None
                summaries["base"] = None
                discard_run()
                draw_base()
                draw_output_note()

            def remove_source(path) -> None:
                """Drops one source and discards the run that read it.

                A held result was assembled over the sources the run read,
                so it is discarded with the source that left the list.
                """
                source_holder.remove(path)
                summaries["sources"].pop(path, None)
                discard_run()
                draw_sources()
                draw_output_note()

            async def add_source() -> None:
                path = await pick_file_or_folder(directories_only=False)
                if path is None:
                    return
                refusal = conflict_model.source_refusal(
                    path, base_holder["path"], source_holder
                )
                if refusal is not None:
                    ui.notify(
                        conflict_model.selection_refusal_sentence(refusal), type="warning"
                    )
                    return
                summary = await _summarise(path)
                if summary is None:
                    return
                source_holder.append(path)
                summaries["sources"][path] = summary
                discard_run()
                draw_sources()
                draw_output_note()

            async def choose_output() -> None:
                directory = await pick_file_or_folder(directories_only=True)
                if directory is None:
                    return
                typed = Path(output_input.value) if output_input.value else None
                name = (
                    typed.name if typed is not None and typed.name
                    else wizard_state.default_output_name(base_holder["path"])
                )
                output_input.value = str(directory / name)

            def draw_base() -> None:
                """Reconstruct.dc.html:104-113: the chosen collection in its
                field, and under it what the file itself reports.

                The counts are the summary's own phrases rather than a
                sentence written here, so the count of empty playlists that
                makes this page worth running is stated by the reading that
                took it (DL-215, DL-220).
                """
                base_field.clear()
                base_meta.clear()
                summary = summaries["base"]
                with base_field:
                    ui.label(
                        str(base_holder["path"])
                        if base_holder["path"]
                        else "No collection selected"
                    ).classes("wizard-field-value")
                base_remove.set_visibility(base_holder["path"] is not None)
                if summary is None:
                    return
                with base_meta:
                    for index, phrase in enumerate(summary.repair_phrases):
                        if index:
                            ui.element("span").classes("wizard-meta-divider")
                        # The empty count is the one phrase the page is
                        # about, so it is the one phrase that carries its
                        # own ink.
                        ui.label(phrase).classes(
                            "wizard-meta-count" if index == 2 else "wizard-body-12"
                        )

            def draw_sources() -> None:
                """Reconstruct.dc.html:117-123: one row per source, its path
                in the field and what that collection could supply read from
                the field's right edge.

                Redrawn from source_holder, so the rows and the holder the
                run reads say the same thing after a removal.
                """
                source_list.clear()
                with source_list:
                    if not source_holder:
                        ui.label("No collection added").classes(
                            "wizard-body-12-5 wizard-faint"
                        )
                    for path in list(source_holder):
                        summary = summaries["sources"].get(path)
                        with ui.element("div").classes("wizard-field-row"):
                            with ui.element("span").classes("wizard-field"):
                                ui.label(str(path)).classes("wizard-field-value")
                                if summary is not None:
                                    ui.label(summary.source_note).classes(
                                        "wizard-field-note"
                                    )
                            ui.button(
                                "Remove",
                                on_click=lambda _e, chosen=path: remove_source(chosen),
                                color=None,
                            ).classes(
                                "wizard-control wizard-control-fill wizard-body-12"
                            )

            def draw_output_note() -> None:
                """Reconstruct.dc.html:141: what the output path is, read
                against the collections this run reads.

                conflict_model.output_refusal is the rule, which is the one
                the write itself refuses on, so this line cannot describe a
                path as safe over a write that would refuse it (DL-222).
                """
                output_meta.clear()
                refusal = conflict_model.output_refusal(
                    output_input.value, base_holder["path"], source_holder
                )
                with output_meta:
                    if refusal is not None:
                        ui.label(
                            conflict_model.selection_refusal_sentence(refusal)
                        ).classes("wizard-meta-count")
                    elif output_input.value:
                        ui.label(
                            "A new file. It does not name any collection above."
                        ).classes("wizard-body-12")
                    else:
                        # A path not yet chosen is not a path that is
                        # safe: the line says what is missing rather than
                        # describing a file the page has not been given.
                        ui.label(
                            "No output path chosen. Choose a folder, or type "
                            "the path the new collection is written to."
                        ).classes("wizard-body-12")

            # Reconstruct.dc.html:27: the four cards the step is filled in
            # through stand in the content column, and what the run will do
            # with them stands in the rail beside it. Main.dc.html:32-35
            # draws each card as a bordered box, a header band carrying the
            # section's title and a padded body. The class strings are
            # literals at the call site, which is what
            # tests/test_gui_theme.py::test_every_classes_call_expands_to_literals
            # reads - DL-188 keeps a dimension or a colour out of a call
            # site, not a class name.
            setup_panel = ui.column().classes("w-full gap-4 wizard-content-width")
            with setup_panel:
                with ui.element("div").classes("wizard-step-split"):
                    with ui.element("div").classes("wizard-step-column"):
                        with ui.element("section").classes("wizard-card"):
                            with ui.element("div").classes("wizard-card-head"):
                                ui.label("The collection to repair").classes(
                                    "wizard-card-title"
                                )
                                ui.label("Read only").classes("wizard-label")
                            with ui.element("div").classes("wizard-card-body"):
                                with ui.element("div").classes("wizard-field-row"):
                                    base_field = ui.element("span").classes(
                                        "wizard-field"
                                    )
                                    ui.button(
                                        "Choose file...",
                                        on_click=choose_base,
                                        color=None,
                                    ).classes("wizard-control wizard-control-fill")
                                    base_remove = ui.button(
                                        "Remove",
                                        on_click=lambda: remove_base(),
                                        color=None,
                                    ).classes(
                                        "wizard-control wizard-control-fill "
                                        "wizard-body-12"
                                    )
                                base_meta = ui.element("p").classes("wizard-meta")

                        with ui.element("section").classes("wizard-card"):
                            with ui.element("div").classes("wizard-card-head"):
                                ui.label("Collections to take playlists from").classes(
                                    "wizard-card-title"
                                )
                                ui.button(
                                    "Add collection...",
                                    on_click=add_source,
                                    color=None,
                                ).classes("wizard-control wizard-control-fill wizard-body-12")
                            with ui.element("div").classes("wizard-card-body"):
                                source_list = ui.column().classes("w-full gap-2")
                                ui.label(
                                    "Read, never modified. Several are folded in the "
                                    "order added - the first to name a playlist wins "
                                    "it."
                                ).classes("wizard-meta")

                        with ui.element("section").classes("wizard-card"):
                            with ui.element("div").classes("wizard-card-head"):
                                ui.label("Where the output goes").classes(
                                    "wizard-card-title"
                                )
                            with ui.element("div").classes("wizard-card-body"):
                                with ui.element("div").classes("wizard-field-row"):
                                    with ui.element("span").classes("wizard-field"):
                                        # The output name is typed as well
                                        # as chosen, so the field holds the
                                        # control itself rather than a
                                        # label of its value: borderless,
                                        # because the box around it is the
                                        # artboard's own field and a second
                                        # border inside it would be the
                                        # framework's.
                                        output_input = (
                                            ui.input(
                                                placeholder="No output path chosen",
                                                on_change=lambda _e: draw_output_note(),
                                            )
                                            .props("borderless dense")
                                            .classes("w-full wizard-field-value")
                                        )
                                    ui.button(
                                        "Choose folder...",
                                        on_click=choose_output,
                                        color=None,
                                    ).classes("wizard-control wizard-control-fill")
                                output_meta = ui.element("p").classes("wizard-meta")

                        with ui.element("section").classes("wizard-card"):
                            with ui.element("div").classes("wizard-card-head"):
                                ui.label("Where the collections disagree").classes(
                                    "wizard-card-title"
                                )
                            with ui.element("div").classes("wizard-card-body"):
                                # The run-wide fallback, carrying the splice
                                # subcommand's own two choices onto
                                # assemble_output's on_conflict parameter.
                                # Its default settles nothing, so a
                                # divergent group stops the run and is shown
                                # as a row of its own at step 3.
                                with ui.element("div").classes("wizard-field-row"):
                                    with ui.element("span").classes("wizard-field"):
                                        # Inside the artboard's own field
                                        # rather than beside it: the
                                        # choice is one of the four
                                        # things this step is given, and
                                        # it reads as one. Borderless,
                                        # because the box around it is
                                        # the field and a second border
                                        # inside it would be the
                                        # framework's.
                                        conflict_choice = (
                                            ui.select(
                                                {
                                                    None: "Ask me - stop and show every conflicting track",
                                                    "keep-first": "keep-first - the collection being repaired wins",
                                                    "keep-last": "keep-last - the last source added wins",
                                                },
                                                value=None,
                                            )
                                            .props("borderless dense")
                                            .classes("w-full wizard-field-value")
                                        )
                                ui.label(
                                    "Asking stops at step 3 and shows each one; the "
                                    "alternatives decide them all without stopping."
                                ).classes("wizard-meta")

                    with ui.element("div").classes("wizard-step-column"):
                        with ui.element("section").classes("wizard-card"):
                            with ui.element("div").classes("wizard-card-head"):
                                ui.label("What happens next").classes(
                                    "wizard-card-title"
                                )
                            with ui.element("div").classes("wizard-card-body"):
                                ui.label(
                                    "A playlist can keep its name and lose everything "
                                    "in it. An older collection still holds what was "
                                    "in it, and this puts the contents back without "
                                    "disturbing anything else."
                                ).classes("wizard-body-12-5 wizard-dim")
                                with ui.element("ol").classes("wizard-next-steps"):
                                    for step in collection_summary.NEXT_STEPS:
                                        with ui.element("li").classes(
                                            "wizard-next-step"
                                        ):
                                            ui.label(str(step.number)).classes(
                                                "wizard-next-step-marker"
                                            )
                                            with ui.element("span"):
                                                ui.label(step.title).classes(
                                                    "wizard-next-step-title"
                                                )
                                                ui.label(step.detail)
                        with ui.element("div").classes(
                            "wizard-callout wizard-callout-info"
                        ):
                            ui.label(
                                "Nothing is written before step 4, not even a cache. "
                                "The preview at step 2 reads the collections beside "
                                "it and holds the result in memory, so leaving before "
                                "you confirm leaves every file on disk untouched."
                            )

            draw_base()
            draw_sources()
            draw_output_note()

            def _load():
                """Reads and parses the chosen files, returning
                (base_bytes, base_root, contributions) or None with the
                reason already notified."""
                base_path = base_holder["path"]
                if base_path is None or not source_holder:
                    ui.notify(
                        "Choose a collection to repair and at least one source",
                        type="warning",
                    )
                    return None
                base_result = read_and_parse_source(base_path)
                if base_result.error is not None:
                    ui.notify(base_result.error, type="negative")
                    return None
                contributions = []
                for path in source_holder:
                    loaded = read_and_parse_source(path)
                    if loaded.error is not None:
                        ui.notify(loaded.error, type="negative")
                        return None
                    contributions.append((loaded.source_bytes.decode("utf-8"), loaded.root))
                return base_result.source_bytes, base_result.root, contributions


            def _render_resolve() -> None:
                """The resolve step: the tally and the bulk strip above
                the split, the conflict grid under its header row at the
                left, and the detail rail at the right carrying one
                control per distinct answer (Resolve.dc.html).

                Hand-rolled rows rather than ui.aggrid, which claims the
                arrow keys Specs binds over this same table (DL-079,
                DL-110). Every row and every answer is a grid cell on
                .wizard-conflict-grid, so the header row and the body
                rows read one set of tracks.

                Every state the step shows - the pick held for a group,
                how many are still undecided, what a bulk action leaves
                standing - is read from conflict_model, which is where
                the suite can reach it (DL-069, DL-106).
                """
                groups = conflict_holder
                region = regions[reconstruct_steps.RESOLVE]
                region.clear()
                # One name per input index, the collection being repaired
                # at index 0 and each source at its position in the list
                # the operator built (DL-154, DL-161).
                labels = _collection_labels(source_holder)
                table: dict = {}

                def draw() -> None:
                    """Redraws the step over the current decisions - the
                    whole step rather than the row just picked, since a
                    bulk action moves every undecided row, the count
                    moves with any pick at all, and the rail describes
                    whichever row is focused."""
                    gate = conflict_model.resolve_gate(decisions, groups)
                    views = decisions.rows(groups)
                    region.clear()
                    with region:
                        bulk_strip(gate)
                        with ui.element("div").classes("wizard-resolve-split"):
                            conflict_table(views)
                            detail_rail(views)
                        # Resolve.dc.html:294's .hint: what a bulk action
                        # does not reach. It stands under the split
                        # rather than beside the bulk controls, where it
                        # would read as a label for them.
                        ui.label(
                            "Deciding all from one collection leaves untouched "
                            "any track that collection holds no record of."
                        ).classes("wizard-hint")
                    advance = resolve_holder["advance"]
                    if advance is not None:
                        advance.set_enabled(gate.all_decided)
                    footer_groups[reconstruct_steps.RESOLVE] = (
                        footer_groups[reconstruct_steps.RESOLVE][0],
                        gate.note,
                    )
                    if step_holder["current"] == reconstruct_steps.RESOLVE:
                        chrome.footer_note.set_text(
                            footer_groups[reconstruct_steps.RESOLVE][1]
                        )

                def bulk_strip(gate) -> None:
                    """Resolve.dc.html:41's .fbar: the tally at the left,
                    the "Decide all from" label, and one bulk action per
                    collection the run reads, each settling the undecided
                    groups its own collection holds a record in and
                    leaving the rest undecided (DL-154).

                    The sentence counts the groups and nothing else. A
                    group is one candidate set whose members may span a
                    subset of the inputs, so naming the count of inputs
                    the run read would attribute the difference to inputs
                    a group holds no member in - something the run does
                    not supply. Resolve.dc.html's own copy names the two
                    collections its illustrative run reads (DL-206).
                    """
                    with ui.element("div").classes("wizard-bulk-strip"):
                        ui.label(
                            conflict_model.resolve_tally_sentence(
                                len(groups), gate.decided, gate.outstanding
                            )
                        ).classes("wizard-tally")
                        ui.element("span").classes("wizard-strip-spacer")
                        ui.label("Decide all from").classes("wizard-label")
                        for input_index, label in enumerate(labels):
                            ui.button(
                                f"All {label}",
                                on_click=lambda _e=None, index=input_index: bulk(index),
                                color=None,
                            ).classes("wizard-control wizard-control-fill wizard-decision-control")

                def conflict_table(views) -> None:
                    """Resolve.dc.html:54-60's .tbl: a header row and one
                    body row per group, both laid out on
                    .wizard-conflict-grid's five tracks."""
                    with ui.element("div").classes("wizard-conflict-table"):
                        with ui.element("div").classes(
                            "wizard-conflict-grid wizard-conflict-header"
                        ).props('role="row"'):
                            for heading in (
                                "Track", "What differs", "Answers",
                                "Held by", "Decision",
                            ):
                                ui.label(heading)
                        for index, view in enumerate(views):
                            row(index, view)

                def row(index: int, view) -> None:
                    """One track's row: its identity key, the attribute
                    names that diverge, how many answers it offers, the
                    collections holding it, and its decision. The focused
                    row alone carries the selected class, which is what
                    the arrow keys move (Specs.dc.html, "Keyboard")."""
                    focused = index == resolve_holder["focused"]
                    classes = "wizard-conflict-grid wizard-conflict-row"
                    if focused:
                        classes = (
                            "wizard-conflict-grid wizard-conflict-row "
                            "wizard-conflict-row-selected"
                        )
                    with ui.element("div").classes(add=classes).props(
                        f'role="row" aria-selected="{str(focused).lower()}"'
                    ):
                        ui.label(view.identity_key).classes(
                            "font-mono wizard-body-12 "
                            "wizard-conflict-track"
                        )
                        ui.label(", ".join(view.attrs)).classes("wizard-body-12")
                        ui.label(str(len(view.candidates))).classes(
                            "font-mono wizard-body-12"
                        )
                        ui.label(
                            ", ".join(
                                sorted(
                                    {
                                        labels[input_index]
                                        for candidate in view.candidates
                                        for input_index, _ in candidate.members
                                    }
                                )
                            )
                        ).classes("wizard-body-12 wizard-subtle-2")
                        if view.decision == conflict_model.UNDECIDED:
                            with ui.element("div").classes(
                                "wizard-conflict-decision"
                            ):
                                ui.button(
                                    "Choose...",
                                    on_click=lambda _e=None, at=index: focus(at),
                                    color=None,
                                ).classes(
                                    "wizard-control wizard-control-fill wizard-decision-control"
                                )
                        else:
                            # The decided cell names the collection that
                            # won and carries the undo that takes the
                            # decision back, so a row is reopened where
                            # it was decided rather than only from the
                            # rail, which describes one row at a time.
                            with ui.element("div").classes(
                                "wizard-conflict-decided wizard-status-found"
                            ):
                                ui.label(labels[view.decision[0]])
                                ui.button(
                                    "Undo",
                                    on_click=(
                                        lambda _e=None, chosen=groups[index]:
                                        reset(chosen)
                                    ),
                                    color=None,
                                ).classes(
                                    "wizard-control wizard-control-fill wizard-decision-control"
                                )

                def detail_rail(views) -> None:
                    """Resolve.dc.html:70-109's .det: the focused row's
                    file at the head, one control per distinct answer in
                    the body, and the keys and actions in the footer.

                    One control per distinct answer rather than one per
                    collection: two collections holding identical values
                    are one answer, and deciding it decides both, so a
                    control names the record that wins rather than the
                    collection it came from (DL-148, DL-160).
                    """
                    with ui.element("div").classes("wizard-detail-rail"):
                        if not views:
                            with ui.element("div").classes("wizard-detail-head"):
                                ui.label(
                                    "Nothing is held differently."
                                ).classes("wizard-body-14-5")
                            return
                        view = views[resolve_holder["focused"]]
                        group = groups[resolve_holder["focused"]]
                        with ui.element("div").classes("wizard-detail-head"):
                            # The head is the one place the file is
                            # named. The rail carries no second labelled
                            # Path row, which in a rail this narrow would
                            # print the same string twice (ref: DL-250).
                            ui.label(view.identity_key).classes(
                                "font-mono wizard-body-14-5"
                            )
                            # The count is read off the group rather
                            # than written into the sentence: a group
                            # is held by as many collections as its
                            # candidates have members between them,
                            # and a sentence naming two while the row
                            # beside it names three is the screen
                            # disagreeing with the model (DL-215).
                            holding = len(
                                {
                                    input_index
                                    for candidate in view.candidates
                                    for input_index, _ in candidate.members
                                }
                            )
                            # The word the count picks comes from
                            # wording.plural like every other
                            # count-bearing sentence in this package,
                            # rather than standing flat on the reasoning
                            # that a group held by one collection is not
                            # a conflict: that reasoning is a property of
                            # the model the sentence would then be
                            # silently relying on, and an inline
                            # conditional on a count is the shape
                            # tests/test_gui_wording.py forbids under
                            # gui/ (DL-215, DL-257).
                            #
                            # One f-string rather than three pieces added
                            # together: a `+` anywhere in this page reads
                            # as count arithmetic written where the suite
                            # cannot reach it, which
                            # tests/test_gui_conflict_page_controls.py
                            # bars outright (DL-106).
                            held = wording.plural(
                                holding, "collection holds", "collections hold"
                            )
                            ui.label(
                                f"{holding} {held} this file with different "
                                f"values. Pick the one that supplies them."
                            ).classes("wizard-body-12 wizard-dim")
                        with ui.element("div").classes("wizard-detail-body"):
                            for position, candidate in enumerate(view.candidates, 1):
                                answer(group, view, position, candidate)
                            # Resolve.dc.html:273's .note: what a pick
                            # names, standing under the answers rather
                            # than in the log alone, because the reading
                            # it corrects - that an answer is a
                            # collection - is the one the operator
                            # arrives with (DL-148).
                            with ui.element("div").classes(
                                "wizard-note wizard-faint"
                            ):
                                ui.label(
                                    "A pick names the record that wins, not the "
                                    "collection it came from. Two collections "
                                    "holding the identical values are one answer, "
                                    "and deciding it decides both."
                                )
                        with ui.element("div").classes("wizard-detail-foot"):
                            key_hints()
                            with ui.element("div").classes(
                                "wizard-detail-actions"
                            ):
                                ui.button(
                                    "Skip for now",
                                    on_click=lambda _e=None: focus(
                                        keymap.dispatch(
                                            "ArrowDown",
                                            (),
                                            keymap.SCOPE_TABLE,
                                            row_count=len(views),
                                            focused_index=resolve_holder["focused"],
                                        ).args["index"]
                                    ),
                                    color=None,
                                ).classes("wizard-control wizard-control-fill")
                                # The rail's primary is the pick itself:
                                # the first answer, which is the one the
                                # digit 1 takes, so the pointer and the
                                # key reach the same decision.
                                ui.button(
                                    "Use answer 1",
                                    on_click=(
                                        lambda _e=None, at=group,
                                        named=conflict_model.candidate_reference(
                                            view.candidates[0]
                                        ): pick(at, named)
                                    ),
                                    color=None,
                                ).classes("wizard-control wizard-control-primary")

                def key_hints() -> None:
                    """Resolve.dc.html:108's .keys: three chip groups,
                    each naming its own keys beside what they do, rather
                    than one sentence listing them in prose. A chip is
                    what Specs.dc.html's "Keyboard" section draws, and
                    the digits, the arrows and U are the three rows it
                    binds over a table (DL-071)."""
                    with ui.element("div").classes("wizard-key-row"):
                        # The digits are a range and the artboard sets
                        # its two chips apart with an en dash; the
                        # arrows are two keys side by side and carry
                        # none.
                        for chips, between, phrase in (
                            (("1", "9"), "\u2013", "pick an answer"),
                            (("\u2191", "\u2193"), "", "move"),
                            (("U",), "", "undo"),
                        ):
                            with ui.element("span").classes("wizard-key-hint"):
                                for position, chip in enumerate(chips):
                                    if position and between:
                                        ui.label(between)
                                    ui.label(chip).classes("wizard-kbd")
                                ui.label(phrase)

                def chosen_marker(chosen: bool) -> None:
                    """The dot that says which answer the group holds.

                    Its own function so that answer() reads as the shape
                    of one answer rather than as the drawing of every
                    part of it: the marker, the field rows and the
                    control each stand alone and answer() stays under
                    the size and nesting this package holds a function
                    to.
                    """
                    with ui.element("span").classes(
                        "wizard-answer-marker"
                    ).props(
                        f'role="img" aria-label='
                        f'"{"Chosen" if chosen else "Not chosen"}"'
                    ):
                        if chosen:
                            ui.element("span").classes("wizard-answer-dot")

                def field_row(field) -> None:
                    """One tracked attribute of one answer: its name,
                    what its value means, and the raw string the written
                    file will hold.

                    What a field is called, how its value reads and
                    whether it carries the difference mark are all
                    decided in answer_detail, which imports no nicegui,
                    so the suite reaches every one of them and this
                    function only places them (DL-069, DL-246).
                    """
                    with ui.element("div").classes("wizard-answer-field"):
                        with ui.element("span").classes(
                            "wizard-answer-field-key"
                        ):
                            if field.differs:
                                ui.element("span").classes(
                                    "wizard-answer-field-mark"
                                )
                            # No font class here: the key span states
                            # the artboard's mono itself, and a Quasar
                            # class on the label would set a family over
                            # it (DL-069).
                            ui.label(field.label).classes("wizard-faint")
                        ui.label(field.formatted or field.raw).classes(
                            "wizard-answer-field-value wizard-body-12 "
                            "wizard-subtle-5"
                        )
                        # The raw string stands beside the formatted one
                        # rather than instead of it: what the written
                        # file carries is what tells two answers apart
                        # when they differ by a digit. A field with no
                        # formatted companion has already printed its raw
                        # value in the cell above, so this one is empty
                        # and the three tracks hold (DL-243).
                        ui.label(
                            field.raw if field.formatted else ""
                        ).classes(
                            "wizard-answer-field-raw wizard-faint"
                        )

                def answer_control(group, view, candidate, reference,
                                   supplied_by: str) -> None:
                    """The control that picks this answer: the record,
                    drawn row by row, with the collections holding it
                    under it.

                    The field block is the control, so the thing the
                    operator points at is the record they are choosing
                    and the "held by ..." line reads as the
                    informational line it is rather than as the thing
                    being picked (DL-148, DL-257).

                    What is picked is the record, not the collection
                    that supplied it: two collections holding identical
                    values are one answer, and deciding it decides both.

                    The rows are hand-built ui.element and ui.label, as
                    every table-shaped surface in this package is
                    (ref: DL-079).
                    """
                    with ui.button(
                        on_click=(
                            lambda _e=None, at=group, named=reference:
                            pick(at, named)
                        ),
                        color=None,
                    ).classes("wizard-control wizard-answer-fields"):
                        for field in answer_detail.answer_fields(
                            view.attrs, view.agreed, candidate
                        ):
                            field_row(field)
                        ui.label(f"held by {supplied_by}").classes(
                            "wizard-answer-holders wizard-body-11 "
                            "wizard-faint"
                        )

                def answer(group, view, position: int, candidate) -> None:
                    """One control per distinct answer, carrying the
                    digit that picks it and the record it supplies.

                    The record, not a joined line of values: the rail
                    draws one row per tracked attribute the group
                    carries, each naming the attribute, what its value
                    means and the raw string the written file will hold,
                    so the operator tells the answers apart by reading
                    them (DL-242, DL-243).

                    The decision the view holds is compared against this
                    candidate's own reference, so the chosen answer alone
                    carries the chosen class and this module holds no
                    reading of what a decision means."""
                    reference = conflict_model.candidate_reference(candidate)
                    chosen = view.decision == reference
                    with ui.element("div").classes("wizard-answer-group"):
                        with ui.element("div").classes("wizard-answer-group-head"):
                            ui.label(f"Answer {position}").classes("wizard-label")
                            ui.label(str(position)).classes("wizard-kbd")
                        classes = "wizard-answer"
                        if chosen:
                            classes = "wizard-answer wizard-answer-chosen"
                        supplied_by = ", ".join(
                            labels[index] for index, _ in candidate.members
                        )
                        with ui.element("div").classes(add=classes):
                            chosen_marker(chosen)
                            answer_control(
                                group, view, candidate, reference, supplied_by
                            )

                def bulk(input_index: int) -> None:
                    """Settles every group the collection at
                    input_index holds a record in, on that record.

                    The reference comes from
                    conflict_model.reference_from_input rather than
                    from a collection token, so a group that
                    collection holds no record in is left undecided
                    rather than settled on a name that matches
                    nothing (DL-148).
                    """
                    decisions.resolve_where_answered(
                        groups, conflict_model.reference_from_input(input_index)
                    )
                    draw()

                def pick(group, reference) -> None:
                    """Settles one group on the record `reference`
                    names, then redraws.

                    reference is an (input index, primary key) pair
                    from conflict_model.candidate_reference: one file
                    in two inputs carries the identical
                    location-derived key, so the input index is what
                    tells the two apart, and two collections holding
                    identical values are one answer that this settles
                    for both (DL-004, DL-148).
                    """
                    decisions.resolve(group, reference)
                    draw()

                def reset(group) -> None:
                    """Returns one group to undecided.

                    The decision is dropped from the mapping rather
                    than written as an undecided token, because a key
                    absent from the mapping reads back undecided.
                    """
                    decisions.reset(group.identity_key)
                    draw()

                def focus(index: int) -> None:
                    """Moves the row the detail rail describes.

                    The index is written into the one holder the
                    redraw reads, so a move applied by key and one
                    applied by a control land in the same field.
                    """
                    resolve_holder["focused"] = index
                    draw()

                def on_key(event) -> None:
                    """Resolves a keypress through keymap.dispatch at
                    SCOPE_TABLE and applies it through this route's own
                    applier table.

                    A name dispatch returns that the table does not carry
                    is a no-op here and a suite failure in
                    tests/test_gui_keymap.py, which pins the table's key
                    set against the actions this table answers (DL-080,
                    DL-205).
                    """
                    if not groups or step_holder["current"] != reconstruct_steps.RESOLVE:
                        return
                    action = keymap.dispatch(
                        event.key.name,
                        tuple(
                            name
                            for name, held in (
                                ("shift", event.modifiers.shift),
                                ("ctrl", event.modifiers.ctrl),
                                ("alt", event.modifiers.alt),
                            )
                            if held
                        ),
                        keymap.SCOPE_TABLE,
                        row_count=len(groups),
                        focused_index=resolve_holder["focused"],
                        candidate_count=len(
                            groups[resolve_holder["focused"]].candidates
                        ),
                    )
                    if action is None:
                        return
                    applier = _RECONSTRUCT_ACTION_APPLIERS.get(action.name)
                    if applier is not None:
                        applier(table, action.args)

                # What an applier is handed: the groups it indexes, the
                # holder carrying the focused row, and the three
                # callbacks that write a decision. The holder itself is
                # passed rather than a copy of its value, so a move
                # applied by key and one applied by a control land in the
                # one field the render reads.
                table.update(
                    {
                        "groups": groups,
                        "holder": resolve_holder,
                        "focus": focus,
                        "pick": pick,
                        "reset": reset,
                    }
                )

                # Registered once for the life of the page rather than
                # per redraw: ui.keyboard binds a handler, and a second
                # preview would otherwise bind a second one over the same
                # keys. on_key reads conflict_holder, which preview
                # rewrites in place, so the one handler always dispatches
                # over the groups the last run reported.
                if resolve_holder.get("keyboard") is None:
                    resolve_holder["keyboard"] = ui.keyboard(on_key=on_key)
                draw()

            def _render_preview() -> None:
                """Preview.dc.html: what the held run would write.

                The left column lists the playlists it filled and
                sums the entries that adds; the right names what
                the run is - the repair itself, held in memory -
                and lists the playlists no collection could fill.
                Every number is read off reconstruct_report's
                record for this run, so the count in a heading and
                the rows under it cannot disagree (DL-215, DL-217).
                """
                result = result_holder["result"]
                report.clear()
                if result is None:
                    return
                # Each of the three fills the panel itself rather than
                # being called inside one opened here, so what a
                # composition stands in is readable where it is written.
                if result.errors:
                    _render_preview_refusal(result)
                    return
                if not result.stats.get("reconstructed_playlists"):
                    with report:
                        ui.label(
                            "Every matched playlist already holds these contents."
                        ).classes("wizard-body-13")
                    return
                _render_preview_run()

            def _render_preview_refusal(result) -> None:
                """A run that assembled nothing, composed as a card of its
                own rather than left as loose text.

                A refusal is the state most runs reach first - a
                collection pair with a divergence stops here - so it says
                what stopped the run and which step settles it, and it
                reads as a screen rather than a message printed over an
                empty page. The reasons the run gave stand under it in
                the tokens it gave them, because a token is what the CLI
                prints and what a bug report carries (DL-094, DL-098,
                DL-226).
                """
                record = reconstruct_report.preview_refusal(
                    result.errors, conflict_holder
                )
                with report, ui.element("section").classes("wizard-card"):
                    with ui.element("div").classes("wizard-card-head"):
                        ui.label(record.title).classes("wizard-card-title")
                        ui.label("Nothing written").classes("wizard-label")
                    with ui.element("div").classes("wizard-card-body"):
                        ui.label(record.sentence).classes(
                            "wizard-body-12-5 wizard-dim"
                        )
                        if record.has_reasons:
                            with ui.element("div").classes(
                                "wizard-callout wizard-callout-warn"
                            ):
                                with ui.element("div").classes(
                                    "wizard-step-column"
                                ):
                                    for reason in record.reasons:
                                        ui.label(reason).classes(
                                            "font-mono wizard-body-12"
                                        )

            def _render_preview_run() -> None:
                """The two columns Preview.dc.html draws for a run
                that assembled: what would be rebuilt at the left,
                what the run is and what it could not fill at the
                right."""
                record = reconstruct_report.preview_report(
                    result_holder["result"].stats, conflict_holder, decisions
                )
                with report, ui.element("div").classes("wizard-step-split"):
                    with ui.element("div").classes("wizard-step-column"):
                        with ui.element("section").classes("wizard-card"):
                            with ui.element("div").classes("wizard-card-head"):
                                ui.label("What would be rebuilt").classes(
                                    "wizard-card-title"
                                )
                                ui.label(record.filled_caption).classes(
                                    "wizard-label"
                                )
                            with ui.element("div").classes(
                                "wizard-card-body wizard-scroll"
                            ):
                                for row in record.listed:
                                    playlist_row(row)
                                if record.remainder is not None:
                                    playlist_row(record.remainder)
                        with ui.element("div").classes("wizard-total"):
                            ui.label(record.total_sentence)
                            ui.label(record.total_amount).classes(
                                "wizard-total-amount"
                            )
                        if record.conflict_sentence:
                            with ui.element("div").classes(
                                "wizard-callout wizard-callout-warn"
                            ):
                                ui.label(record.conflict_sentence)
                    with ui.element("div").classes("wizard-step-column"):
                        with ui.element("section").classes("wizard-card"):
                            with ui.element("div").classes("wizard-card-head"):
                                ui.label("What this run did").classes(
                                    "wizard-card-title"
                                )
                                ui.label("Nothing written").classes(
                                    "wizard-label"
                                )
                            with ui.element("div").classes("wizard-card-body"):
                                ui.label(
                                    "The repair was assembled in full and "
                                    "held in memory. This is the run itself, "
                                    "not an estimate of one - the file "
                                    "written at step 4 is what was assembled "
                                    "here, so the write cannot disagree with "
                                    "what is listed."
                                ).classes("wizard-body-12-5 wizard-dim")
                        if record.unfilled:
                            with ui.element("section").classes("wizard-card"):
                                with ui.element("div").classes(
                                    "wizard-card-head"
                                ):
                                    ui.label(record.unfilled_title).classes(
                                        "wizard-card-title"
                                    )
                                with ui.element("div").classes(
                                    "wizard-card-body"
                                ):
                                    for name in record.unfilled:
                                        with ui.element("div").classes(
                                            "wizard-list-row"
                                        ):
                                            ui.label(name).classes(
                                                "wizard-list-name"
                                            )
                                            ui.label(
                                                "no collection held it"
                                            ).classes("wizard-list-count")
                                    ui.label(
                                        "These keep their names and stay "
                                        "empty. Adding another collection at "
                                        "step 1 may fill them."
                                    ).classes("wizard-meta")
                        with ui.element("div").classes(
                            "wizard-callout wizard-callout-info"
                        ):
                            ui.label(
                                "The playlists that already held their "
                                "contents are untouched, and are not listed."
                            )

            def playlist_row(row) -> None:
                """Preview.dc.html:110's .pl: one listed playlist,
                its name at the left and its own entry count at the
                right. The count's sentence is the row's, so the
                unit is written once for every row that prints
                one."""
                with ui.element("div").classes("wizard-list-row"):
                    ui.label(row.name).classes("wizard-list-name")
                    ui.label(row.entry_count).classes("wizard-list-count")

            def _render_write() -> None:
                """Write.dc.html: what the file about to be written
                will hold, and what stays as it is.

                Redrawn on every entry to the step rather than once,
                because two of its numbers - the decided count and
                the output path - are answered by controls on the
                steps behind it, and a panel drawn before those
                answers were given would state the run's size as it
                stood at some earlier moment.
                """
                write_panel.clear()
                result = result_holder["result"]
                if result is None:
                    return
                destination = output_input.value or ""
                record = reconstruct_report.write_report(
                    result.stats,
                    conflict_holder,
                    decisions,
                    destination,
                    bool(destination) and Path(destination).exists(),
                    [
                        str(path)
                        for path in (base_holder["path"], *source_holder)
                        if path
                    ],
                    # This run wrote this path. Both halves matter: a
                    # path the operator has since edited names a file
                    # this run did not write, and a run assembled since
                    # the write produced bytes the file on disk does not
                    # hold. Either one puts the step back before the
                    # write, which is where it truly is (DL-240).
                    written=bool(destination) and written_holder["path"] == destination,
                )
                write_holder["question"].set_text(record.confirm_question)
                write_holder["confirm"].set_text(record.confirm_action)
                write_holder["assurances"].clear()
                with write_holder["assurances"]:
                    for assurance in record.confirm_assurances:
                        with ui.element("div").classes("wizard-dialog-item"):
                            ui.label(assurance)
                with write_panel:
                    with ui.element("div").classes("wizard-step-split"):
                        with ui.element("div").classes("wizard-step-column"):
                            with ui.element("section").classes("wizard-card"):
                                with ui.element("div").classes(
                                    "wizard-card-head"
                                ):
                                    ui.label(record.head_title).classes(
                                        "wizard-card-title"
                                    )
                                    ui.label(record.head_badge).classes(
                                        "wizard-label"
                                    )
                                with ui.element("div").classes(
                                    "wizard-card-body"
                                ):
                                    ui.label("New collection file").classes(
                                        "wizard-label"
                                    )
                                    with ui.element("div").classes(
                                        "wizard-destination"
                                    ):
                                        ui.label(
                                            record.destination
                                            or "No output path chosen"
                                        ).classes("wizard-destination-path")
                                        ui.label(
                                            record.destination_badge
                                        ).classes("wizard-badge")
                                    ui.label(record.destination_note).classes(
                                        "wizard-meta"
                                    )
                            with ui.element("section").classes("wizard-card"):
                                with ui.element("div").classes(
                                    "wizard-card-head"
                                ):
                                    ui.label(record.contents_title).classes(
                                        "wizard-card-title"
                                    )
                                with ui.element("div").classes(
                                    "wizard-card-body"
                                ):
                                    for row in record.rows:
                                        change_row(row)
                                    with ui.element("div").classes(
                                        "wizard-total"
                                    ):
                                        ui.label(record.total_sentence)
                                        ui.label(record.total_amount).classes(
                                            "wizard-total-amount"
                                        )
                        with ui.element("div").classes("wizard-step-column"):
                            with ui.element("section").classes("wizard-card"):
                                with ui.element("div").classes(
                                    "wizard-card-head"
                                ):
                                    ui.label("Your originals").classes(
                                        "wizard-card-title"
                                    )
                                with ui.element("div").classes(
                                    "wizard-card-body"
                                ):
                                    for original in record.originals:
                                        with ui.element("div").classes(
                                            "wizard-list-row"
                                        ):
                                            ui.label(original).classes(
                                                "font-mono wizard-list-name"
                                            )
                                            ui.label("Not modified").classes(
                                                "wizard-badge"
                                            )
                                    ui.label(
                                        "Every one was opened read only for "
                                        "the whole run."
                                    ).classes("wizard-meta")
                            with ui.element("div").classes(
                                "wizard-callout wizard-callout-info"
                            ):
                                ui.label(
                                    "The file is written in one go. It is "
                                    "built whole and moved into place, so an "
                                    "interrupted write leaves no half-written "
                                    "collection behind."
                                )
                            with ui.element("div").classes("wizard-callout"):
                                # What to do with the file, and nothing
                                # else. Whether the run touched the
                                # operator's own collections is answered
                                # by the originals card above, which
                                # names each one and reads NOT MODIFIED
                                # beside it; saying it again here as
                                # "stays where it is until you do" made a
                                # promise about what importing does to
                                # their collection, which is Traktor's
                                # business and not this run's.
                                #
                                # One route, because one route is what
                                # Traktor has. An alternative naming a
                                # "collection setting" to point at the
                                # file was written here unverified and
                                # names nothing in the program: Traktor's
                                # directory preference is a root folder,
                                # not a path to one .nml. Confirmed by an
                                # operator against Traktor itself, which
                                # is the only place this was checkable
                                # (DL-239).
                                ui.label(
                                    "In Traktor, open the new file with "
                                    "File - Import Collection."
                                )

            def change_row(row) -> None:
                """Write.dc.html:108's .cr: one line of what the new
                file will hold - the change and the sentence under
                it at the left, its count at the right. The count's
                ink is the row's own tone token, mapped to a class
                here so no colour is written at a call site
                (DL-188)."""
                with ui.element("div").classes("wizard-change-row"):
                    with ui.element("span"):
                        ui.label(row.label)
                        ui.label(row.detail).classes("wizard-change-detail")
                    # The subscript is at the call site rather
                    # than behind a name: the cascade guards read
                    # every class a classes() call can pass by
                    # expanding the expression it is handed, and a
                    # lookup they cannot expand is a call they stop
                    # checking (DL-188).
                    tone = {
                        reconstruct_report.TONE_ADDED:
                            "wizard-change-count wizard-change-added",
                        reconstruct_report.TONE_UNTOUCHED:
                            "wizard-change-count wizard-change-untouched",
                    }[row.tone]
                    ui.label(row.amount).classes(tone)

            async def assemble() -> bool:
                """Runs the same assemble_output call the CLI makes, with
                reconstruct=True, and holds what it reported. Nothing is
                written here: the run is the preview, so the write cannot
                disagree with what the preview shows.

                The answers it was handed are held beside it, which is
                what lets a later step ask whether the run reports the
                answers now given rather than an earlier set (DL-225).
                """
                loaded = await run.io_bound(_load)
                if loaded is None:
                    return False
                base_bytes, base_root, contributions = loaded
                resolutions = decisions.resolutions(conflict_holder)
                result = await run.io_bound(
                    assemble_output,
                    base_bytes.decode("utf-8"), base_root, contributions,
                    MatchConfidence.STRICT, conflict_choice.value, True,
                    resolutions=resolutions,
                )
                # The groups the page shows are a projection of the rows
                # this run reported: conflict_model reads the membership and
                # the per-side values off the rows themselves, so there is no
                # second pass over the collections to hand run.io_bound.
                groups = conflict_model.conflict_groups(result.conflict_rows)
                conflict_holder[:] = groups
                result_holder["result"] = result
                result_holder["resolutions"] = resolutions
                # A run assembled after a write produced bytes the file
                # on disk does not hold, so the step is before its write
                # again.
                written_holder["path"] = None
                _render_resolve()
                return True

            async def preview() -> None:
                """Runs the repair and shows what it reported."""
                if await assemble():
                    show_step(reconstruct_steps.PREVIEW)

            async def write_output() -> None:
                """Writes the output the held run produced, or names why it
                cannot. A run that never happened, a run that refused on
                conflicts and a run that refused on anything else are three
                distinct refusals; the conflict one names how many are still
                to decide and the third names the run's own error, which the
                report above the controls lists in full (DL-111)."""
                write_dialog.close()
                result = result_holder["result"]
                refusal = conflict_model.write_refusal(
                    result, decisions, conflict_holder
                )
                if refusal is not None:
                    ui.notify(
                        conflict_model.write_refusal_sentence(refusal), type="warning"
                    )
                    return
                if not output_input.value:
                    ui.notify("Choose an output path", type="warning")
                    return
                output_path = Path(output_input.value)
                collision = conflict_model.output_refusal(
                    output_path, base_holder["path"], source_holder
                )
                if collision is not None:
                    ui.notify(
                        conflict_model.selection_refusal_sentence(collision),
                        type="negative",
                    )
                    return
                await run.io_bound(
                    write_bytes_atomically, output_path, result.output.encode("utf-8")
                )
                written_holder["path"] = str(output_path)
                # The step describes the file; the file now exists, so
                # the step is redrawn to say so. Left alone it went on
                # reading "Before anything is written" and "Does not
                # exist yet" behind a toast naming the file it had just
                # written (DL-240).
                _render_write()
                ui.notify(f"Written to {output_path}", type="positive")

        # Both steps are a region holding one column the render fills:
        # what each shows is read off the held run, so the composition is
        # built when a run exists rather than built empty and populated.
        # The two-column split Preview.dc.html:27 and Write.dc.html:27
        # draw is inside that column, so the split spans the content
        # width rather than the page's full frame.
        with regions[reconstruct_steps.PREVIEW]:
            report = ui.column().classes("w-full gap-4 wizard-content-width")

        with regions[reconstruct_steps.WRITE]:
            write_panel = ui.column().classes("w-full gap-4 wizard-content-width")
            # Built once and filled per entry to the step: a dialog is a
            # container the framework mounts at the page root, so
            # rebuilding it per render would leave one behind for every
            # visit to the step. Its question is the panel's own record,
            # set where the panel is drawn.
            with ui.dialog() as write_dialog:
                with ui.element("div").classes("wizard-dialog"):
                    write_holder["question"] = ui.label().classes(
                        "wizard-heading-sm font-semibold"
                    )
                    # Filled where the panel is drawn, like the
                    # question above: what the write is about to do to
                    # the path depends on what stands there now, so a
                    # line built once at page construction would state
                    # the wrong one (DL-241).
                    write_holder["assurances"] = ui.element("div").classes(
                        "wizard-dialog-list"
                    )
                    with ui.element("div").classes("wizard-dialog-actions"):
                        ui.button(
                            "Cancel", on_click=write_dialog.close, color=None
                        ).classes("wizard-control wizard-control-fill")
                        write_holder["confirm"] = ui.button(
                            "Write collection", on_click=write_output, color=None
                        ).classes("wizard-control wizard-control-primary")

        # Main.dc.html:29's .ft holds the screen's advancing action, so
        # every primary control is constructed in the band, one group
        # per step, and show_step decides which group the band shows.
        # Each invokes a function this page defines above - a with
        # statement opens no scope of its own, so every name is in reach
        # here - which is how each control exists once and its enabled
        # state is held once (DL-187).
        with chrome.footer_actions:
            with ui.row().classes("wizard-footer-actions") as setup_actions:
                ui.button("Preview", on_click=preview, color=None).classes(
                    "wizard-control wizard-control-primary"
                )
            with ui.row().classes("wizard-footer-actions") as preview_actions:
                ui.button(
                    "Back to set up",
                    on_click=lambda: show_step(reconstruct_steps.SET_UP),
                    color=None,
                ).classes("wizard-control wizard-control-fill")
                ui.button(
                    "Continue to resolve",
                    on_click=lambda: advance_to(reconstruct_steps.RESOLVE),
                    color=None,
                ).classes("wizard-control wizard-control-primary")
            with ui.row().classes("wizard-footer-actions") as resolve_actions:
                ui.button(
                    "Back to the preview",
                    on_click=lambda: show_step(reconstruct_steps.PREVIEW),
                    color=None,
                ).classes("wizard-control wizard-control-fill")
                resolve_holder["advance"] = ui.button(
                    "Continue to write",
                    on_click=lambda: advance_to(reconstruct_steps.WRITE),
                    color=None,
                ).classes("wizard-control wizard-control-primary")
            with ui.row().classes("wizard-footer-actions") as write_actions:
                ui.button(
                    "Back to resolve",
                    on_click=lambda: show_step(reconstruct_steps.RESOLVE),
                    color=None,
                ).classes("wizard-control wizard-control-fill")
                ui.button(
                    # Redrawn before it opens: a file can appear at the
                    # output path between the step being drawn and the
                    # operator pressing this, and the dialog is where
                    # they are told what the write will do to it.
                    "Write collection...",
                    on_click=lambda: (_render_write(), write_dialog.open()),
                    color=None
                ).classes("wizard-control wizard-control-primary")

        footer_groups[reconstruct_steps.SET_UP] = (
            setup_actions,
            "Preview reads the collections; nothing is written by it.",
        )
        footer_groups[reconstruct_steps.PREVIEW] = (
            preview_actions,
            "This is what the merge would write. Nothing is written yet.",
        )
        footer_groups[reconstruct_steps.RESOLVE] = (
            resolve_actions,
            "Writing stays closed until every track has an answer.",
        )
        footer_groups[reconstruct_steps.WRITE] = (
            write_actions,
            "Write collection asks before it writes the file the preview "
            "assembled.",
        )
        show_step(reconstruct_steps.SET_UP)

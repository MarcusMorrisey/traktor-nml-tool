"""Guards what the conflict surface of the page registered at '/'
delegates and what its controls actually do, on an interpreter with no
nicegui installed.

Two mechanisms, each with a stated reach.

An AST walk over app.py's source, the register
tests/test_gui_view_boundary.py uses, holds the delegation rule: the
conflict rows come from conflict_model's row projection, the write
refusal comes from conflict_model.write_refusal rather than from a
second reading of result.output, the run-wide control offers the splice
subcommand's own two choices onto on_conflict, the decision set reaches
assemble_output as resolutions and by no other route, the rows are
hand-rolled rather than ui.aggrid (DL-079, DL-110), and no count or
decision reading is written inline where the suite cannot reach it
(DL-069, DL-106, DL-111).

A recording stub, the register tests/test_gui_header_tabs.py uses,
installs minimal nicegui and webview stand-ins into sys.modules for the
duration of the test and restores them in a finally. Here it goes
further than recording classes: its ui.page keeps the page builder it
decorates, its elements keep the keyword arguments they were built
with, and its run.io_bound runs the callable it is handed, so the page
can be built and its controls invoked. A test picks the collections
through the page's own file controls, runs Preview, presses one bulk
control and runs Preview again, and reads what reached assemble_output
and what the run wrote. What this cannot establish - that a browser
renders these elements, and that the classes survive Quasar's own
cascade layers - the served-page run carries (DL-084).

Every fixture that drives a control places the named source at an input
index the run-wide picker would not choose: base holds one answer,
alpha holds a second and bravo a third, and the guards drive bravo at
input index 2, so a control resolving through keep-first (base, index
0) or through the first source added (alpha, index 1) fails rather than
coinciding with the answer under test.
"""

from __future__ import annotations

import ast
import asyncio
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

from traktor_nml.gui import conflict_model

APP_PATH = Path(__file__).parent.parent / "traktor_nml" / "gui" / "app.py"

PAGE = "_build_reconstruct_page"

# The two choices traktor_nml/commands/splice_cmd.py gives --on-conflict.
SPLICE_ON_CONFLICT_CHOICES = frozenset({"keep-first", "keep-last"})

# The one decision token conflict_model owns: UNDECIDED. base and source
# are operator-facing words on the page's labels, not decision values, so
# the guard pins the token the model actually owns. A page writing it as
# a literal is reading a decision itself.
DECISION_TOKENS = frozenset({conflict_model.UNDECIDED})

_GUI_MODULES = ["traktor_nml.gui.app", "traktor_nml.gui.file_picker"]


def _app_source() -> str:
    """app.py's source, read with newline='' so its CRLF endings arrive
    as they are stored and no test in this file can be the thing that
    rewrites them."""
    with open(APP_PATH, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _page_tree(source: str | None = None) -> ast.FunctionDef:
    """The _build_reconstruct_page FunctionDef, over the real source or
    over a mutated copy of it."""
    tree = ast.parse(source if source is not None else _app_source())
    pages = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == PAGE
    ]
    assert pages, f"app.py must define {PAGE}"
    return pages[0]


def _calls(node: ast.AST, attr: str) -> list[ast.Call]:
    """Every call in this subtree whose callee ends in `attr`, whether
    written as a bare name or as an attribute of a module or object."""
    found = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name == attr:
                found.append(child)
    return found


def _assemble_call(page: ast.FunctionDef) -> ast.Call:
    """The run.io_bound call that runs assemble_output. The page hands
    assemble_output to nicegui's thread-pool dispatcher rather than
    calling it inline, so its parameters sit one position along: the
    call's args[0] is assemble_output itself."""
    calls = [
        call for call in _calls(page, "io_bound")
        if call.args and isinstance(call.args[0], ast.Name)
        and call.args[0].id == "assemble_output"
    ]
    assert calls, "the page must run assemble_output through run.io_bound"
    return calls[0]


def _select_name(page: ast.FunctionDef) -> str:
    """The variable the run-wide conflict control is bound to - the
    single ui.select the page builds."""
    for node in ast.walk(page):
        if isinstance(node, ast.Assign) and _calls(node.value, "select"):
            target = node.targets[0]
            assert isinstance(target, ast.Name), "the conflict control must be bound to a plain name"
            return target.id
    raise AssertionError("the page must offer a ui.select for the run-wide conflict choice")


# --------------------------------------------------------------------
# The recording stub and the fixtures it is driven over.
# --------------------------------------------------------------------


class _FakeDialog:
    """Stands in for nicegui's ui.dialog, which file_picker.py
    subclasses at import time - a class statement cannot take a
    MagicMock instance as a base."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        return False

    def open(self) -> None:
        """Shown and hidden by the page rather than by the framework:
        the reconstruct page's write control opens its confirmation and
        the write closes it, so the fake carries both."""

    def close(self) -> None:
        pass


class _RecordingElement:
    """One rendered element, keeping the positional and keyword
    arguments it was built with - a button's label is its first
    positional argument and its handler is its on_click keyword, which
    is how a test presses it - together with every string pushed onto it
    through .classes(). `value` is a real attribute rather than a
    recorded call, so a control the page reads back answers what it was
    constructed with; every other call answers with itself so the
    builder's chaining and `with` blocks run unchanged.
    """

    def __init__(self, kind: str, args: tuple, kwargs: dict) -> None:
        self.kind = kind
        self.args = args
        self.kwargs = kwargs
        self.classes_strings: list = []
        self.value = kwargs.get("value")

    def classes(self, add=None, **kwargs):
        value = add if add is not None else kwargs.get("replace")
        if isinstance(value, str):
            self.classes_strings.append(value)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        return False

    def __getattr__(self, name):
        return lambda *args, **kwargs: self


class _RecordingUi:
    """The nicegui ui stand-in the page is built into. Every element it
    creates is appended to `elements`; ui.page keeps the builder it
    decorates under the route it was given, so a test can call the page
    the way nicegui would on a request."""

    dialog = _FakeDialog

    def __init__(self) -> None:
        self.elements: list = []
        self.pages: dict = {}

    def _make(self, kind: str, args: tuple, kwargs: dict) -> _RecordingElement:
        element = _RecordingElement(kind, args, kwargs)
        self.elements.append(element)
        return element

    def page(self, route, *args, **kwargs):
        def decorator(builder):
            self.pages[route] = builder
            return builder

        return decorator

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *args, **kwargs: self._make(name, args, kwargs)


def _uninstall() -> None:
    for name in ("nicegui", "webview", *_GUI_MODULES):
        sys.modules.pop(name, None)


def _install(recording_ui: _RecordingUi) -> None:
    """Installs the stand-ins app.py imports. run.io_bound runs the
    callable it is handed and answers its result, which is what the page
    awaits, so the page's own code runs unchanged by the substitution."""
    nicegui_module = types.ModuleType("nicegui")
    nicegui_module.ui = recording_ui
    run_module = types.ModuleType("nicegui.run")

    async def io_bound(function, *args, **kwargs):
        return function(*args, **kwargs)

    run_module.io_bound = io_bound
    nicegui_module.run = run_module
    nicegui_module.app = MagicMock()
    nicegui_module.events = MagicMock()
    sys.modules["nicegui"] = nicegui_module
    sys.modules["webview"] = MagicMock()


def _nml(entries_xml: str, entries_count: int, playlists_xml: str) -> str:
    """Minimal NML wrapper whose SUBNODES COUNT is derived by counting
    literal '<NODE' occurrences in playlists_xml, matching the wrapper
    tests/test_splice.py authors its fixtures with."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
        f'<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT">'
        f'<SUBNODES COUNT="{playlists_xml.count(chr(60) + "NODE")}">'
        f"{playlists_xml}</SUBNODES></NODE></PLAYLISTS>"
        "<SETS></SETS><INDEXING></INDEXING></NML>"
    )


def _entry(title: str, filename: str) -> str:
    return (
        f'<ENTRY TITLE="{title}" ARTIST="A" AUDIO_ID="">'
        f'<LOCATION DIR="/:Music/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
        '<INFO BITRATE="320" PLAYTIME_FLOAT="1.0" FILESIZE="16"></INFO>'
        "</ENTRY>"
    )


def _playlist(name: str, keys: list, uuid: str) -> str:
    entries = "".join(
        f'<ENTRY><PRIMARYKEY TYPE="TRACK" KEY="{key}"></PRIMARYKEY></ENTRY>' for key in keys
    )
    return (
        f'<NODE TYPE="PLAYLIST" NAME="{name}">'
        f'<PLAYLIST ENTRIES="{len(keys)}" TYPE="LIST" UUID="{uuid}">{entries}</PLAYLIST>'
        "</NODE>"
    )


def _key(filename: str) -> str:
    return "C:/:Music/:" + filename


def _collection(path: Path, titles: dict, playlist_name: str, uuid: str) -> Path:
    """One collection file holding one entry per (file name, title) pair
    and one playlist over them all."""
    entries = "".join(_entry(title, filename) for filename, title in titles.items())
    keys = [_key(filename) for filename in titles]
    path.write_text(
        _nml(entries, len(titles), _playlist(playlist_name, keys, uuid)),
        encoding="utf-8",
        newline="",
    )
    return path


class _Driven:
    """What one drive of the page recorded: the elements it built, the
    resolutions mapping each assemble_output call was handed and the
    SpliceResult each answered."""

    def __init__(self, recording_ui: _RecordingUi) -> None:
        self.ui = recording_ui
        self.resolutions: list = []
        self.results: list = []

    def buttons(self, label: str) -> list:
        return [
            element for element in self.ui.elements
            if element.kind == "button" and element.args and element.args[0] == label
        ]

    def button_labels(self) -> list:
        return [
            element.args[0] for element in self.ui.elements
            if element.kind == "button" and element.args
        ]

    def label_texts(self) -> list:
        return [
            element.args[0] for element in self.ui.elements
            if element.kind == "label" and element.args
        ]

    def _handler(self, label: str):
        found = self.buttons(label)
        assert found, f"no control labelled {label!r}; the page built {self.button_labels()}"
        return found[-1].kwargs["on_click"]

    def press(self, label: str) -> None:
        """Presses the most recently built control carrying this label:
        the table is redrawn after every pick, so the newest is the one
        on screen."""
        self._handler(label)()

    def press_async(self, label: str) -> None:
        """Presses a control whose handler is a coroutine function."""
        asyncio.run(self._handler(label)())


def _open_page(base: Path, sources: list) -> "_Driven":
    """Builds the reconstruct page against a recording ui, picks the
    collection to repair and each source through the page's own file
    controls, and hands back the recorder. The caller drives the rest and
    calls _close_page in a finally."""
    recording_ui = _RecordingUi()
    _uninstall()
    _install(recording_ui)
    app = importlib.import_module("traktor_nml.gui.app")
    driven = _Driven(recording_ui)

    chosen = [base, *sources]

    async def fake_picker(*args, **kwargs):
        return chosen.pop(0)

    app.pick_file_or_folder = fake_picker
    real_assemble = app.assemble_output

    def recording_assemble(*args, **kwargs):
        driven.resolutions.append(kwargs.get("resolutions"))
        result = real_assemble(*args, **kwargs)
        driven.results.append(result)
        return result

    app.assemble_output = recording_assemble
    app._build_reconstruct_page()
    recording_ui.pages["/"]()
    driven.press_async("Choose file...")
    for _ in sources:
        driven.press_async("Add collection...")
    return driven


def _close_page() -> None:
    _uninstall()


def _three_way_fixture(tmp_path: Path, filenames: list) -> tuple:
    """base, alpha and bravo, each holding the same tracks at the same
    locations under a different TITLE, so every named track diverges
    three ways and the answers are told apart by which collection
    supplies them."""
    base = _collection(
        tmp_path / "base.nml",
        {name: "BaseTitle" + name for name in filenames},
        "BaseList",
        "uuid-base",
    )
    alpha = _collection(
        tmp_path / "alpha.nml",
        {name: "AlphaTitle" + name for name in filenames},
        "AlphaList",
        "uuid-alpha",
    )
    bravo = _collection(
        tmp_path / "bravo.nml",
        {name: "BravoTitle" + name for name in filenames},
        "BravoList",
        "uuid-bravo",
    )
    return base, alpha, bravo


def _labels_for(paths: list) -> list:
    """app.py's source labels, read against the recording stub because
    app.py imports nicegui at module scope."""
    recording_ui = _RecordingUi()
    _uninstall()
    _install(recording_ui)
    try:
        app = importlib.import_module("traktor_nml.gui.app")
        return app._source_labels(paths)
    finally:
        _uninstall()


# --------------------------------------------------------------------
# What the page delegates.
# --------------------------------------------------------------------


def test_conflict_rendering_reads_the_model_row_projection() -> None:
    """The page derives its conflict groups through
    conflict_model.conflict_groups and renders them through the decision
    set's rows() projection, rather than reading ConflictRow fields
    itself.

    Observed to fail against a real mutation: replacing
    `conflict_model.conflict_groups(` with `_local_conflict_groups(` and
    `decisions.rows(groups)` with `[(g, g) for g in groups]` in app.py
    and running this test raised:
        AssertionError: the page must derive its groups through
        conflict_model.conflict_groups
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    page = _page_tree()
    assert _calls(page, "conflict_groups"), (
        "the page must derive its groups through conflict_model.conflict_groups"
    )
    assert _calls(page, "rows"), (
        "the page must render conflict_model's row projection"
    )


def test_write_refusal_reads_the_model_not_result_output() -> None:
    """The write control asks conflict_model.write_refusal why it cannot
    write and renders write_refusal_sentence, and nowhere tests
    result.output against None - the test that reads a run that aborted
    and a run that never happened as the same thing (DL-111).

    Observed to fail against a real mutation: restoring the original
    guard `if result is None or result.output is None:` in place of the
    write_refusal call in app.py and running this test raised:
        AssertionError: the write control must refuse on
        conflict_model.write_refusal, not on result.output being None
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    page = _page_tree()
    assert _calls(page, "write_refusal"), "the write control must call write_refusal"
    assert _calls(page, "write_refusal_sentence"), (
        "the write control must render write_refusal_sentence"
    )
    for node in ast.walk(page):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Attribute):
            is_output_none = (
                node.left.attr == "output"
                and any(
                    isinstance(comparator, ast.Constant) and comparator.value is None
                    for comparator in node.comparators
                )
            )
            assert not is_output_none, (
                "the write control must refuse on conflict_model.write_refusal, "
                "not on result.output being None"
            )


def test_run_wide_control_offers_the_splice_subcommands_choices() -> None:
    """The run-wide control's options are the splice subcommand's own
    keep-first and keep-last, and its value is what reaches
    assemble_output's on_conflict parameter.

    Observed to fail against a real mutation: renaming the two option
    keys in app.py's ui.select to "first" and "last" and running this
    test raised:
        AssertionError: the run-wide control must offer {'keep-first',
        'keep-last'}, the splice subcommand's own choices; it offers
        {'keep-last - the last source added wins', 'first', 'keep-first
        - the collection being repaired wins', 'Ask me - stop and show
        every conflicting track', 'last'}
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    page = _page_tree()
    select = _calls(page, "select")[0]
    offered = {
        node.value for node in ast.walk(select)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert SPLICE_ON_CONFLICT_CHOICES <= offered, (
        f"the run-wide control must offer {set(SPLICE_ON_CONFLICT_CHOICES)}, the splice "
        f"subcommand's own choices; it offers {offered}"
    )

    call = _assemble_call(page)
    on_conflict = call.args[5]
    assert isinstance(on_conflict, ast.Attribute) and on_conflict.attr == "value", (
        "assemble_output's on_conflict argument must be the control's value"
    )
    assert isinstance(on_conflict.value, ast.Name)
    assert on_conflict.value.id == _select_name(page), (
        "assemble_output's on_conflict argument must come from the run-wide control"
    )


def test_per_track_picks_reach_resolutions_and_nothing_else() -> None:
    """The decision set reaches assemble_output as the resolutions
    keyword and by no other route: resolutions is its only keyword, and
    no positional argument mentions the decisions object.

    Observed to fail against a real mutation: changing the keyword in
    app.py's assemble_output call from
    `resolutions=decisions.resolutions(conflict_holder)` to
    `on_conflict=decisions.resolutions(conflict_holder)` and running
    this test raised:
        AssertionError: the page's picks must reach assemble_output's
        resolutions parameter
        assert 'resolutions' in ['on_conflict']
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    page = _page_tree()
    call = _assemble_call(page)
    keywords = [keyword.arg for keyword in call.keywords]
    assert "resolutions" in keywords, (
        "the page's picks must reach assemble_output's resolutions parameter"
    )
    extra = [name for name in keywords if name != "resolutions"]
    assert not extra, (
        "the decision set must reach assemble_output as resolutions alone; "
        f"the call also passes {extra}"
    )
    resolutions = [k.value for k in call.keywords if k.arg == "resolutions"][0]
    assert _calls(resolutions, "resolutions"), (
        "the resolutions argument must be the decision set's own projection"
    )
    for argument in call.args:
        names = {
            node.id for node in ast.walk(argument) if isinstance(node, ast.Name)
        }
        assert "decisions" not in names, (
            "no positional argument may carry the decision set"
        )


def test_no_aggrid_call_appears_in_app() -> None:
    """No ui.aggrid call appears anywhere in app.py: aggrid claims the
    arrow keys Specs.dc.html binds over these same rows, so the conflict
    table is hand-rolled ui.row rows like the review table's (DL-079,
    DL-110).

    Observed to fail against a real mutation: replacing the conflict
    table's `table = ui.column().classes("w-full gap-0")` in app.py with
    `table = ui.aggrid({"rowData": []})` and running this test raised:
        AssertionError: app.py must hold no ui.aggrid call; the conflict
        rows are hand-rolled ui.row rows (DL-079, DL-110)
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    tree = ast.parse(_app_source())
    assert not _calls(tree, "aggrid"), (
        "app.py must hold no ui.aggrid call; the conflict rows are "
        "hand-rolled ui.row rows (DL-079, DL-110)"
    )
    assert _calls(_page_tree(), "row"), "the conflict rows must be hand-rolled ui.row rows"


def test_no_decision_arithmetic_is_written_inline() -> None:
    """The page counts nothing and reads no decision token itself: no
    addition or subtraction, no sum() and no decision literal appears
    anywhere in _build_reconstruct_page. The outstanding count and the
    meaning of a pick come from conflict_model, which is where the suite
    can reach them (DL-069, DL-106).

    Observed to fail against a real mutation: replacing the gate's
    `conflict_model.resolve_gate(decisions, groups)` in app.py with
    `sum(1 for view in decisions.rows(groups) if view.decision == "undecided")`
    and running this test raised:
        AssertionError: the page must not count decisions itself; it
        writes sum( and the literal(s) {'undecided'}
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    page = _page_tree()
    counted = bool(_calls(page, "sum"))
    literals = {
        node.value for node in ast.walk(page)
        if isinstance(node, ast.Constant) and node.value in DECISION_TOKENS
    }
    assert not counted and not literals, (
        "the page must not count decisions itself; it writes "
        f"{'sum( and ' if counted else ''}the literal(s) {literals}"
    )
    arithmetic = [
        node for node in ast.walk(page)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub))
    ]
    assert not arithmetic, (
        "the page must hold no count arithmetic; the outstanding count and "
        "the decided count are read from conflict_model.resolve_gate"
    )
    assert _calls(page, "resolve_gate"), (
        "the page must read conflict_model's resolve gate, which carries the "
        "outstanding count and the advancing control's enabled state together"
    )


# --------------------------------------------------------------------
# What the controls do, driven over the page itself.
# --------------------------------------------------------------------


def test_the_bulk_control_for_a_named_source_resolves_to_that_source(tmp_path: Path) -> None:
    """Pressing the bulk control for one named source reaches
    assemble_output's resolutions carrying that source's own (input
    index, primary key) pair, and the run through it writes that
    source's value.

    The fixture answers three ways: base holds BaseTitletrack.mp3 at
    input index 0, alpha holds AlphaTitletrack.mp3 at index 1 and bravo
    holds BravoTitletrack.mp3 at index 2. The control driven is bravo's,
    so neither keep-first's answer (base, the collection being repaired)
    nor the first source added (alpha) is the answer asserted, and a
    control resolving through either fails here.

    Observed to fail against a real mutation: replacing the bulk
    action's `conflict_model.reference_from_input(input_index)` in
    app.py with `lambda candidates: conflict_model.candidate_reference(
    candidates[0])` - the keep-first shape this guard exists to catch -
    and running this test raised:
        AssertionError: the bulk control for bravo must record bravo's
        own pair
        assert {'C:/:Music/:.../:track.mp3')} == {'C:/:Music/:.../:track.mp3')}
        Differing items:
        {'C:/:Music/:track.mp3': (0, 'C:/:Music/:track.mp3')} !=
        {'C:/:Music/:track.mp3': (2, 'C:/:Music/:track.mp3')}
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    base, alpha, bravo = _three_way_fixture(tmp_path, ["track.mp3"])
    driven = _open_page(base, [alpha, bravo])
    try:
        driven.press_async("Preview")
        driven.press("All bravo.nml")
        driven.press_async("Preview")
    finally:
        _close_page()

    key = _key("track.mp3")
    assert driven.resolutions[-1] == {key: (2, key)}, (
        "the bulk control for bravo must record bravo's own pair"
    )
    written = driven.results[-1].output
    assert written is not None, "the run the pick settled must produce output"
    assert 'TITLE="BravoTitletrack.mp3"' in written, (
        "the run must write bravo's value for the track bravo was named for"
    )
    assert 'TITLE="BaseTitletrack.mp3"' not in written, (
        "the run must not write keep-first's answer over a pick naming bravo"
    )
    assert 'TITLE="AlphaTitletrack.mp3"' not in written, (
        "the run must not write the first source's answer over a pick naming bravo"
    )


def test_a_bulk_action_leaves_a_row_its_collection_holds_no_record_in_undecided(
    tmp_path: Path,
) -> None:
    """A bulk action settles the groups its own collection holds a
    record in and leaves every other group undecided, counted by the
    outstanding label rather than silently taking someone else's answer
    (DL-154).

    base and alpha both hold two tracks; bravo holds only the first, so
    the second track's group carries no bravo record. Pressing bravo's
    bulk control settles the first and leaves the second undecided.

    Observed to fail against a real mutation: replacing the bulk
    action's `conflict_model.reference_from_input(input_index)` in
    app.py with `lambda candidates: conflict_model.candidate_reference(
    candidates[0])` and running this test raised:
        AssertionError: bravo's bulk action must settle only the group
        bravo holds a record in
        assert {'C:/:Music/:.../:track.mp3')} == {'C:/:Music/:.../:track.mp3')}
        Differing items:
        {'C:/:Music/:track.mp3': (0, 'C:/:Music/:track.mp3')} !=
        {'C:/:Music/:track.mp3': (2, 'C:/:Music/:track.mp3')}
        Left contains 1 more item:
        {'C:/:Music/:absent.mp3': (0, 'C:/:Music/:absent.mp3')}
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    base, alpha, _ = _three_way_fixture(tmp_path, ["track.mp3", "absent.mp3"])
    bravo = _collection(
        tmp_path / "bravo.nml",
        {"track.mp3": "BravoTitletrack.mp3"},
        "BravoList",
        "uuid-bravo",
    )
    driven = _open_page(base, [alpha, bravo])
    try:
        driven.press_async("Preview")
        driven.press("All bravo.nml")
        driven.press_async("Preview")
    finally:
        _close_page()

    held = _key("track.mp3")
    assert driven.resolutions[-1] == {held: (2, held)}, (
        "bravo's bulk action must settle only the group bravo holds a record in"
    )
    # The phrase read back is the tally's own, the sentence the resolve
    # step's footer prints from conflict_model.resolve_gate's two counts;
    # it is read off the labels the drive recorded rather than off the
    # gate, so what is held is what the page rendered.
    assert any(
        "1 decided, 1 to go" in str(text) for text in driven.label_texts()
    ), (
        "the group bravo holds no record in must still be counted as undecided; "
        f"the page rendered {[text for text in driven.label_texts() if 'to go' in str(text)]}"
    )


def test_the_row_offers_one_control_per_candidate_naming_the_collections_supplying_it(
    tmp_path: Path,
) -> None:
    """Each row offers one control per distinct answer the group carries
    - not one per record - and a control names every collection
    supplying its answer, so two sources that agree present as one
    control naming both (DL-150).

    alpha and bravo hold the same value here, so the group carries two
    answers over three records.

    Observed to fail against a real mutation: replacing
    `for candidate in view.candidates:` in app.py's row builder with
    `for candidate in view.candidates[:1]:` and running this test
    raised:
        AssertionError: the row must offer one control per answer, and
        the two agreeing sources must share one control naming both
        assert ['base BaseTitletrack.mp3'] == ['base BaseTi...o.nml Agreed']
        Right contains one more item: 'alpha.nml, bravo.nml Agreed'
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    base = _collection(
        tmp_path / "base.nml", {"track.mp3": "BaseTitletrack.mp3"}, "BaseList", "uuid-base"
    )
    alpha = _collection(
        tmp_path / "alpha.nml", {"track.mp3": "Agreed"}, "AlphaList", "uuid-alpha"
    )
    bravo = _collection(
        tmp_path / "bravo.nml", {"track.mp3": "Agreed"}, "BravoList", "uuid-bravo"
    )
    driven = _open_page(base, [alpha, bravo])
    try:
        driven.press_async("Preview")
    finally:
        _close_page()

    candidate_controls = [
        label for label in driven.button_labels()
        if "BaseTitletrack.mp3" in str(label) or "Agreed" in str(label)
    ]
    assert candidate_controls == ["base BaseTitletrack.mp3", "alpha.nml, bravo.nml Agreed"], (
        "the row must offer one control per answer, and the two agreeing "
        "sources must share one control naming both"
    )


def test_the_bulk_strip_names_base_and_every_source_in_the_order_added(
    tmp_path: Path,
) -> None:
    """The strip reads All base plus one action per source collection,
    in the order the operator added them (DL-154).

    Observed to fail against a real mutation: replacing
    `for input_index, label in enumerate(labels):` in app.py's bulk
    strip with `for input_index, label in enumerate(labels[:1]):` and
    running this test raised:
        AssertionError: the strip must offer All base plus one action
        per source, in the order added
        assert ['All base'] == ['All base', ...ll bravo.nml']
        Right contains 2 more items, first extra item: 'All alpha.nml'
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    base, alpha, bravo = _three_way_fixture(tmp_path, ["track.mp3"])
    driven = _open_page(base, [alpha, bravo])
    try:
        driven.press_async("Preview")
    finally:
        _close_page()

    strip = [label for label in driven.button_labels() if str(label).startswith("All ")]
    assert strip == ["All base", "All alpha.nml", "All bravo.nml"], (
        "the strip must offer All base plus one action per source, in the order added"
    )


def test_bulk_labels_separate_sources_sharing_a_file_name() -> None:
    """Two sources sharing a file name in different folders carry
    distinguishable labels: the file name plus the one parent segment
    that separates them (DL-161).

    Observed to fail against a real mutation: replacing the label
    rendering in app.py's _source_labels with the file name alone,
    `labels.append(parts[-1])`, and running this test raised:
        AssertionError: two sources sharing a file name must carry
        distinguishable labels
        assert ['collection....llection.nml'] == ['collection....on.nml (two)']
        At index 0 diff: 'collection.nml' != 'collection.nml (one)'
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    labels = _labels_for(["C:/x/one/collection.nml", "C:/x/two/collection.nml"])
    assert labels == ["collection.nml (one)", "collection.nml (two)"], (
        "two sources sharing a file name must carry distinguishable labels"
    )
    assert len(set(labels)) == len(labels)


def test_bulk_labels_separate_sources_sharing_a_file_name_and_a_parent() -> None:
    """Two sources sharing both a file name and a parent directory carry
    distinguishable labels: the walk keeps taking segments until the
    trailing run is unique, which is the case a file-name-plus-one-parent
    rule cannot break (DL-161).

    Observed to fail against a real mutation: replacing the label
    rendering in app.py's _source_labels with the file name plus one
    parent, `labels.append(f"{parts[-1]} ({parts[-2]})")`, and running
    this test raised:
        AssertionError: two sources sharing a file name and a parent
        must still carry distinguishable labels
        assert ['collection.....nml (music)'] == ['collection....ml (b/music)']
        At index 0 diff: 'collection.nml (music)' != 'collection.nml (a/music)'
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    labels = _labels_for(["C:/x/a/music/collection.nml", "C:/x/b/music/collection.nml"])
    assert labels == ["collection.nml (a/music)", "collection.nml (b/music)"], (
        "two sources sharing a file name and a parent must still carry "
        "distinguishable labels"
    )
    assert len(set(labels)) == len(labels)


def test_bulk_labels_fall_back_to_the_full_resolved_path_at_the_root() -> None:
    """Sources separating only at the root label as their full resolved
    paths - the fallback the walk always reaches, because
    conflict_model.source_refusal has already refused a duplicate
    resolved path, so no two listed sources share one (DL-161).

    Observed to fail against a real mutation: replacing the label
    rendering in app.py's _source_labels with the file name plus one
    parent, `labels.append(f"{parts[-1]} ({parts[-2]})")`, and running
    this test raised:
        AssertionError: sources separating only at the root must label
        as their full resolved paths
        assert ['collection.....nml (music)'] == ['Q:\\\\music\\\\...llection.nml']
        At index 0 diff: 'collection.nml (music)' != 'Q:\\\\music\\\\collection.nml'
    app.py was restored from a copy taken beforehand, never via
    `git checkout`, and re-running confirmed it passes.
    """
    paths = ["Q:/music/collection.nml", "R:/music/collection.nml", "S:/music/collection.nml"]
    labels = _labels_for(paths)
    assert labels == [str(Path(path).resolve()) for path in paths], (
        "sources separating only at the root must label as their full resolved paths"
    )
    assert len(set(labels)) == len(labels)


def test_app_holds_no_second_definition_of_the_conflict_abort_token() -> None:
    """The conflict abort token has one definition, in conflict_model, and
    app.py reads it from there rather than declaring its own copy: two
    copies can drift, and the page renders rows for one token while the
    refusal is keyed on the other.

    Observed with app.py's read at the abort render replaced by the
    literal `if error == "unresolved_conflicts" and groups:`:
    AssertionError reported as `app.py must read the conflict abort token
    from conflict_model; it writes the literal 'unresolved_conflicts' on
    line(s) [1628]`. app.py was restored by editing the literal back to
    the attribute read, never via `git checkout`, and re-running
    confirmed it passes.
    """
    source = _app_source()
    tree = ast.parse(source)
    literals = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and node.value == conflict_model.CONFLICT_ABORT_TOKEN
    ]
    assert not literals, (
        "app.py must read the conflict abort token from conflict_model; it "
        f"writes the literal {conflict_model.CONFLICT_ABORT_TOKEN!r} on "
        f"line(s) {sorted(node.lineno for node in literals)}"
    )
    reads = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "CONFLICT_ABORT_TOKEN"
    ]
    assert reads, "app.py must read conflict_model.CONFLICT_ABORT_TOKEN"

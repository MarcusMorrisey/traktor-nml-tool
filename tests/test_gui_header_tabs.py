"""Guards the routes app.py registers and the header it renders on each
of them, on an interpreter with no nicegui installed.

Two mechanisms, each with a stated reach.

An AST walk over app.py's source, the register
tests/test_gui_view_boundary.py uses, collects the arguments of every
ui.page decorator and every route-shaped string literal. It establishes
single sourcing at the literal level: the only routes app.py writes are
its two @ui.page arguments, each builder registers its own, and neither
tab label appears in the file at all - both come from
navigation.SECTIONS. It cannot see a '#' comment, which is why the text
enumeration recorded in traktor_nml/README.md covers comments and prose,
and it establishes nothing about rendering.

A recording stub, the register tests/test_gui_module_imports.py uses,
installs minimal nicegui and webview stand-ins into sys.modules for the
duration of the test and restores them in a finally. Its ui.link records
the label and the target it is called with and the handle it returns
records every .classes() and .props() string pushed onto it. Calling
app.py's header builder for one route, the guards collect the recorded
targets, the targets carrying aria-current="page" and the targets
carrying wizard-tab-selected, and assert each marker collection equals
exactly the route under test - by equality, never by membership and
never through any(), so the wrong tab, both tabs and no tab each fail,
and a second marker landing on one anchor is counted. What this cannot
establish - that nicegui renders a ui.link as an anchor, and that the
class survives Quasar's own cascade layers - the served-page run
carries.
"""

from __future__ import annotations

import ast
import importlib
import re
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

from traktor_nml.gui import navigation

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "traktor_nml" / "gui" / "app.py"
MAIN_PATH = REPO_ROOT / "traktor_nml" / "gui" / "__main__.py"

_ROUTE_SHAPED = re.compile(r"/[A-Za-z0-9_\-/]*")

_GUI_MODULES = ["traktor_nml.gui.app", "traktor_nml.gui.file_picker"]


# --------------------------------------------------------------------
# The recording stub.
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
    """One rendered element. Records every string pushed onto it
    through .classes() and .props(), whether positionally or through
    classes(add=...), and answers any other call with itself so the
    builder's chaining and `with` blocks run unchanged."""

    def __init__(self, kind: str, args: tuple) -> None:
        self.kind = kind
        self.args = args
        self.classes_strings: list = []
        self.props_strings: list = []

    def classes(self, add=None, **kwargs):
        value = add if add is not None else kwargs.get("replace")
        if isinstance(value, str):
            self.classes_strings.append(value)
        return self

    def props(self, add=None, **kwargs):
        if isinstance(add, str):
            self.props_strings.append(add)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        return False

    def __getattr__(self, name):
        return lambda *args, **kwargs: self


class _RecordingUi:
    """The nicegui ui stand-in the header builder renders into. Every
    element it creates is appended to `elements`; a ui.link also lands
    in `links` carrying the label and target it was called with."""

    dialog = _FakeDialog

    def __init__(self) -> None:
        self.elements: list = []
        self.links: list = []

    def _make(self, kind: str, args: tuple) -> _RecordingElement:
        element = _RecordingElement(kind, args)
        self.elements.append(element)
        return element

    def link(self, label, target=None, *args, **kwargs) -> _RecordingElement:
        element = self._make("link", (label, target))
        self.links.append(element)
        return element

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *args, **kwargs: self._make(name, args)


def _uninstall() -> None:
    for name in ("nicegui", "webview", *_GUI_MODULES):
        sys.modules.pop(name, None)


def _install(recording_ui: _RecordingUi) -> None:
    nicegui_module = types.ModuleType("nicegui")
    nicegui_module.ui = recording_ui
    nicegui_module.run = MagicMock()
    nicegui_module.app = MagicMock()
    nicegui_module.events = MagicMock()
    sys.modules["nicegui"] = nicegui_module
    sys.modules["webview"] = MagicMock()


def _render_header(active_route: str, tabs_override=None) -> _RecordingUi:
    """Imports app.py against a recording ui, calls its header builder
    for one route and hands back the recorder. sys.modules is restored
    in a finally so the stand-ins never leak into another test.
    tabs_override, when given, replaces navigation.header_tabs for the
    call - the mutation lever the negative controls below pull."""
    recording_ui = _RecordingUi()
    _uninstall()
    _install(recording_ui)
    try:
        app = importlib.import_module("traktor_nml.gui.app")
        original = app.navigation.header_tabs
        if tabs_override is not None:
            app.navigation.header_tabs = tabs_override
        try:
            app._build_header(active_route)
        finally:
            app.navigation.header_tabs = original
    finally:
        _uninstall()
    return recording_ui


def _targets(recorder: _RecordingUi) -> list:
    return [link.args[1] for link in recorder.links]


def _targets_carrying_aria_current(recorder: _RecordingUi) -> list:
    marker = 'aria-current="' + navigation.ARIA_CURRENT_SELECTED + '"'
    return [
        link.args[1]
        for link in recorder.links
        for prop in link.props_strings
        if marker in prop
    ]


def _targets_carrying_selected_class(recorder: _RecordingUi) -> list:
    return [
        link.args[1]
        for link in recorder.links
        for classes in link.classes_strings
        if navigation.TAB_SELECTED_CLASS in classes.split()
    ]


def _marked(recorder: _RecordingUi) -> tuple:
    return (
        _targets_carrying_aria_current(recorder),
        _targets_carrying_selected_class(recorder),
    )


# --------------------------------------------------------------------
# What the header renders.
# --------------------------------------------------------------------


def test_header_renders_two_links_in_table_order():
    """The strip holds one anchor per SECTIONS row, in the order the
    table declares, and no third anchor.

    Mutation: navigation.header_tabs was replaced for the call by one
    returning only the '/reconnect' record. Observed:
        AssertionError: assert ['/reconnect'] == ['/', '/reconnect']
        At index 0 diff: '/reconnect' != '/'
        Right contains one more item: '/reconnect'
    """
    recorder = _render_header("/")
    assert _targets(recorder) == ["/", "/reconnect"]
    assert len(recorder.links) == 2


def test_root_marks_the_root_tab_and_only_it():
    """On '/', the anchor carrying aria-current="page" and the anchor
    carrying wizard-tab-selected are both the '/' anchor, by equality
    over the collected targets rather than by membership.

    Mutation: navigation.header_tabs was replaced for the call by one
    marking the other record instead. Observed:
        AssertionError: assert ['/reconnect'] == ['/']
    """
    recorder = _render_header("/")
    assert _targets_carrying_aria_current(recorder) == ["/"]
    assert _targets_carrying_selected_class(recorder) == ["/"]


def test_reconnect_marks_the_reconnect_tab_and_only_it():
    """On '/reconnect', both marker collections read ['/reconnect'].

    Mutation: the route passed to the builder was changed to '/' while
    this guard's assertions stood. Observed:
        AssertionError: assert ['/'] == ['/reconnect']
    """
    recorder = _render_header("/reconnect")
    assert _targets_carrying_aria_current(recorder) == ["/reconnect"]
    assert _targets_carrying_selected_class(recorder) == ["/reconnect"]


def _stand_in_tabs(selected_routes):
    """A header_tabs stand-in marking exactly the routes named, built
    from navigation's own record type and class names so only the
    selection differs from what the real function computes."""

    def header_tabs(active_route: str):
        records = []
        for route, label in navigation.SECTIONS:
            selected = route in selected_routes
            records.append(
                navigation.HeaderTab(
                    route=route,
                    label=label,
                    selected=selected,
                    classes=(
                        navigation.TAB_CLASS + " " + navigation.TAB_SELECTED_CLASS
                        if selected
                        else navigation.TAB_CLASS
                    ),
                    aria_current=navigation.ARIA_CURRENT_SELECTED if selected else None,
                )
            )
        return tuple(records)

    return header_tabs


def test_the_other_tab_both_tabs_and_no_tab_each_fail():
    """The three ways the marker can be wrong, each run through the
    same collection the guards above assert on.

    Mutations, applied by replacing navigation.header_tabs for the call
    while '/' is the active route. Observed, as (aria-current targets,
    wizard-tab-selected targets):
        the other record marked: (['/reconnect'], ['/reconnect'])
        both records marked:     (['/', '/reconnect'], ['/', '/reconnect'])
        no record marked:        ([], [])
    None of the three equals ['/'], which is what the guards above
    assert, so each fails there.
    """
    other = _render_header("/", _stand_in_tabs({"/reconnect"}))
    assert _marked(other) == (["/reconnect"], ["/reconnect"])

    both = _render_header("/", _stand_in_tabs({"/", "/reconnect"}))
    assert _marked(both) == (["/", "/reconnect"], ["/", "/reconnect"])

    none = _render_header("/", _stand_in_tabs(set()))
    assert _marked(none) == ([], [])

    for wrong in (other, both, none):
        assert _targets_carrying_aria_current(wrong) != ["/"]
        assert _targets_carrying_selected_class(wrong) != ["/"]


def test_every_tab_carries_the_tab_class():
    """Both anchors carry navigation.TAB_CLASS - the rule that paints
    an unselected tab - and the selected one carries it alongside
    TAB_SELECTED_CLASS rather than instead of it.

    Mutation: navigation.header_tabs was replaced for the call by one
    whose selected record's class string was TAB_SELECTED_CLASS alone.
    Observed, at the loop assertion:
        AssertionError: assert 'wizard-tab' in ['wizard-tab-selected']
         +  where 'wizard-tab' = navigation.TAB_CLASS
    """
    recorder = _render_header("/")
    for link in recorder.links:
        assert link.classes_strings, "a tab carries no classes"
        assert navigation.TAB_CLASS in " ".join(link.classes_strings).split()
    selected = [link for link in recorder.links if link.args[1] == "/"][0]
    assert sorted(" ".join(selected.classes_strings).split()) == [
        navigation.TAB_CLASS,
        navigation.TAB_SELECTED_CLASS,
    ]


def test_header_renders_the_brand_the_divider_and_a_labelled_nav():
    """The row carries wizard-header-bar, a brand mark carrying
    wizard-brand and a divider carrying wizard-header-divider, and the
    strip itself is a nav element labelled Sections.

    Mutation: the 'wizard-header-divider' class string was changed to
    'wizard-divider' in app.py and this guard rerun. Observed:
        AssertionError: assert 'wizard-header-divider' in {'flex
        items-center gap-1', 'items-center gap-3 wizard-header-bar
        wizard-content-width', 'wizard-brand', 'wizard-divider',
        'wizard-tab', 'wizard-tab wizard-tab-selected'}
    """
    recorder = _render_header("/")
    painted = {
        klass
        for element in recorder.elements
        for klass in element.classes_strings
    }
    assert "wizard-header-bar" in " ".join(painted)
    assert "wizard-brand" in painted
    assert "wizard-header-divider" in painted
    navs = [
        element
        for element in recorder.elements
        if element.args and element.args[0] == "nav"
    ]
    assert len(navs) == 1, "the tab strip is not one nav element"
    assert any('aria-label="Sections"' in prop for prop in navs[0].props_strings)


# --------------------------------------------------------------------
# What app.py's source names.
# --------------------------------------------------------------------


def _app_tree() -> ast.Module:
    return ast.parse(APP_PATH.read_text(encoding="utf-8", newline=""))


def _page_routes(tree: ast.AST) -> list:
    """Every argument of every @ui.page(...) decorator in the tree, in
    source order."""
    routes = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not isinstance(func, ast.Attribute) or func.attr != "page":
                continue
            for arg in decorator.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    routes.append(arg.value)
    return routes


def _builder(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(name + " not found in app.py")


def test_app_py_registers_exactly_the_two_routes():
    """The set of ui.page arguments in app.py is {'/', '/reconnect'}:
    two pages, and nothing registered at '/reconstruct', which
    therefore answers the framework's own 404 (DL-141).

    Mutation: a third registration, @ui.page("/reconstruct") over a
    stub function, was added to a copy of app.py's source and the same
    walk run over it. Observed:
        AssertionError: assert {'/', '/recon.../reconstruct'} == {'/',
        '/reconnect'}
        Extra items in the left set: '/reconstruct'
    """
    assert set(_page_routes(_app_tree())) == {"/", "/reconnect"}


def test_each_builder_registers_its_own_route():
    """_build_reconstruct_page registers '/' and build_wizard registers
    '/reconnect', each exactly once.

    Mutation: the two ui.page arguments were swapped in a copy of
    app.py's source and the same walk run over it. Observed:
        AssertionError: assert ['/reconnect'] == ['/']
    """
    tree = _app_tree()
    assert _page_routes(_builder(tree, "_build_reconstruct_page")) == ["/"]
    assert _page_routes(_builder(tree, "build_wizard")) == ["/reconnect"]


def test_app_py_names_no_route_outside_its_two_registrations():
    """Every route-shaped string literal in app.py is one of the two
    ui.page arguments. The reach is stated: an ast.Constant walk sees
    string literals, so a route named in a '#' comment is invisible to
    it and is covered by the text enumeration instead (DL-144, DL-145).

    Mutation: a module-level assignment of the literal '/reconstruct'
    was added to a copy of app.py's source and the same walk run over
    it. Observed:
        AssertionError: route literal outside a ui.page argument:
        ['/reconstruct']
        assert ['/reconstruct'] == []
    """
    tree = _app_tree()
    registered = set(_page_routes(tree))
    stray = sorted(
        {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and _ROUTE_SHAPED.fullmatch(node.value)
            and node.value not in registered
        }
    )
    assert stray == [], "route literal outside a ui.page argument: " + repr(stray)


def test_app_py_names_neither_tab_label():
    """Neither label navigation.SECTIONS carries appears anywhere in
    app.py's source: the header reads them off the table, so app.py
    holds no second copy that could disagree with it.

    Mutation: a ui.label('Reconstruct playlists') call was written back
    into a copy of app.py's source and the same scan run over it.
    Observed:
        AssertionError: app.py names a tab label: ['Reconstruct
        playlists']
        assert ['Reconstruct playlists'] == []
    """
    source = APP_PATH.read_text(encoding="utf-8", newline="")
    named = [label for _, label in navigation.SECTIONS if label in source]
    assert named == [], "app.py names a tab label: " + repr(named)


def test_the_only_ui_links_are_the_header_builders():
    """Every ui.link call in app.py sits inside _build_header, so no
    page carries a hand-written link into the other one alongside the
    tab strip.

    Mutation: a ui.link call into the other page was added to
    build_wizard in a copy of app.py's source and the same walk run
    over it. Observed:
        AssertionError: ui.link outside the header builder in:
        ['build_wizard']
        assert ['build_wizard'] == []
    """
    tree = _app_tree()

    def link_calls(node: ast.AST) -> int:
        return sum(
            1
            for inner in ast.walk(node)
            if isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Attribute)
            and inner.func.attr == "link"
            and isinstance(inner.func.value, ast.Name)
            and inner.func.value.id == "ui"
        )

    header = _builder(tree, "_build_header")
    outside = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node is not header
        and link_calls(node) > 0
    ]
    assert outside == [], "ui.link outside the header builder in: " + repr(outside)
    assert link_calls(header) == 1


# --------------------------------------------------------------------
# The entry point, and the line endings.
# --------------------------------------------------------------------


def _ui_run_kwargs() -> dict:
    tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8", newline=""))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
        ):
            return {
                kw.arg: kw.value.value
                for kw in node.keywords
                if isinstance(kw.value, ast.Constant)
            }
    raise AssertionError("no ui.run call found in __main__.py")


def test_entry_point_title_names_the_application_not_an_operation():
    """__main__.py's ui.run passes title='traktor-nml-tool', and
    neither that argument nor the module docstring names one of the two
    operations - the native window opens whatever '/' resolves to and
    the header's selected tab names the screen, so a title naming
    either operation contradicts the header on the other route
    (DL-140).

    Mutation: the title was set to 'traktor-nml-tool - reconnect
    wizard' in a copy of __main__.py's source and the same walk run
    over it. Observed:
        AssertionError: assert 'traktor-nml-...onnect wizard' ==
        'traktor-nml-tool'
        - traktor-nml-tool
        + traktor-nml-tool - reconnect wizard
    """
    kwargs = _ui_run_kwargs()
    assert kwargs["title"] == "traktor-nml-tool"
    docstring = ast.get_docstring(
        ast.parse(MAIN_PATH.read_text(encoding="utf-8", newline=""))
    )
    haystack = (kwargs["title"] + " " + docstring).lower()
    named = [label for _, label in navigation.SECTIONS if label.lower() in haystack]
    assert named == [], "the entry point names one operation: " + repr(named)


def test_line_endings_hold_after_the_edit():
    """app.py is the one CRLF module in the package and __main__.py is
    LF; an editor normalising either on write buries the change in a
    whole-file diff (DL-142).

    Mutation: the first three CRLF in a copy of app.py's bytes were
    replaced with bare LF and this guard rerun. Observed:
        AssertionError: app.py holds a bare LF
        assert (1647 - 1644) == 0
    - 3 bare LF among 1644 CRLF, against the 0 bare LF asserted here.
    """
    app_bytes = APP_PATH.read_bytes()
    app_crlf = app_bytes.count(b"\r\n")
    assert app_bytes.count(b"\n") - app_crlf == 0, "app.py holds a bare LF"
    assert app_crlf > 0, "app.py has been normalised to LF"

    main_bytes = MAIN_PATH.read_bytes()
    assert main_bytes.count(b"\r\n") == 0, "__main__.py holds a CRLF"
    assert main_bytes.count(b"\n") > 0


def test_the_header_band_and_every_content_column_share_one_width_class():
    """The header row's class string and every content box - the ones
    carrying wizard-card - are laid out at wizard-content-width, either
    by carrying it themselves or by standing inside a container that
    does, which is what makes the band's edges the card's edges. Read
    out of app.py's own source because the boxes are built inside page
    functions the recorder above does not enter.

    The card box is the class this pairing reads because it is the box
    each section a page composes itself carries. .wizard-content-width
    stays the only rule declaring a width, which
    tests/test_gui_shell.py::test_no_shell_or_card_rule_declares_a_width
    holds from the stylesheet's side.

    A card inside a two-column split is laid out by the split, which is
    itself inside a panel carrying the width, so it carries no width of
    its own: a second width declared inside the first would be a card
    sized against the page rather than against its column. The split is
    named here and
    tests/test_gui_preview_and_write_composition.py::test_each_step_region_holds_one_panel_at_the_content_width
    holds the other half - that the panel the split is drawn into
    carries the width (DL-218).

    The ancestor walk stops at the function a card is built in, so a
    card standing inside a nested render function is read against that
    function's own containers rather than against the containers of the
    function it happens to be written inside. A `with` naming a panel
    resolves to the class string that panel was built with: a render
    function draws into a panel the step region holds, and the panel is
    what carries the width.

    Mutation: the preview step's panel was given 'w-full gap-4' with its
    wizard-content-width removed, so the split inside it stood in a panel
    at no width and the cards under it had nothing to be read against.
    Observed - the refusal state's own card, which is drawn into that
    panel directly rather than inside the split its run report stands in:
        E       AssertionError: card boxes laid out at no content width: ['wizard-card']
        E       assert ['wizard-card'] == []
        E
        E         Left contains one more item: 'wizard-card'
        E         Use -v to get more diff
    """
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    header = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and "wizard-header-bar" in node.value.split()
    ]
    assert header, "no class string carries wizard-header-bar"
    assert all("wizard-content-width" in text.split() for text in header), (
        f"the header band carries no width class: {header}"
    )

    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    # Each name a classes() call was assigned to, and the class string it
    # carries: `report = ui.column().classes("... wizard-content-width")`
    # binds the panel the preview step's renders draw into.
    panels = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        for call in ast.walk(node.value):
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "classes"
                and call.args
                and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str)
            ):
                panels.setdefault(target.id, set()).add(call.args[0].value)

    def widths_above(node):
        """Every class string declared by a with-statement enclosing
        this call, which is what "inside" means in a page built out of
        nested context managers."""
        found = []
        walker = parents.get(node)
        while walker is not None:
            if isinstance(walker, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break
            if isinstance(walker, ast.With):
                for item in walker.items:
                    found.extend(
                        text.value
                        for text in ast.walk(item.context_expr)
                        if isinstance(text, ast.Constant)
                        and isinstance(text.value, str)
                    )
                    if isinstance(item.context_expr, ast.Name):
                        found.extend(panels.get(item.context_expr.id, ()))
            walker = parents.get(walker)
        return found

    boxes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "classes"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and "wizard-card" in str(node.args[0].value).split()
    ]
    assert boxes, "no classes() call carries wizard-card"
    adrift = [
        node.args[0].value
        for node in boxes
        if "wizard-content-width" not in node.args[0].value.split()
        and not any(
            {"wizard-content-width", "wizard-step-split"} & set(text.split())
            for text in widths_above(node)
        )
    ]
    assert adrift == [], f"card boxes laid out at no content width: {adrift}"

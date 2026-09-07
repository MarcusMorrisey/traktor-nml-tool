"""Guards how traktor_nml/gui/app.py composes the reconstruct page's four
steps and its resolve screen, read as source text and as an AST under the
system interpreter, which has no nicegui.

What a guard here holds is what the module constructs and which class
string each construction names. What it cannot hold is what the browser
did with them: a guard reading a class name is true in exactly the broken
state, so the rendered rail, the resolved column widths and the rail's
own width are read on a served page and written into a record under
docs/ (DL-084, DL-169, DL-189).

A class string this file reads off a call site is only half of a name:
what the sheet declares for the same name is read in
tests/test_gui_resolve_sheet.py, and tests/test_gui_theme.py sweeps every
.wizard-* class the sheet defines for a call site, so a name carried at
one side and missing at the other fails there rather than passing here.

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation. Where pytest printed an assertion
repr longer than the margin, the line is cut with an ellipsis rather than
rewrapped, so what stands is what pytest printed.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from traktor_nml.gui import reconstruct_steps

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"


def _source() -> str:
    return _APP_PY.read_text(encoding="utf-8")


def _page_tree() -> ast.AST:
    """The _build_reconstruct_page function's own subtree.

    Read as its own subtree rather than as the whole module, so a guard
    below cannot be satisfied by something the reconnect wizard's own
    builders do - the failure a footer assertion the wrong route
    satisfied already produced once on this page.
    """
    module = ast.parse(_source())
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_reconstruct_page":
            return node
    raise AssertionError("app.py defines no _build_reconstruct_page")


def _page_source() -> str:
    """The same subtree as text, for the class strings a call site names."""
    return ast.get_source_segment(_source(), _page_tree()) or ""


def _named_function_source(name: str) -> str:
    """One function defined inside _build_reconstruct_page, as text.

    The page carries more than one keymap.dispatch call - the rail's
    "Skip for now" control resolves an ArrowDown through the same map -
    so a reading of the key handler is taken from the handler's own
    subtree. A substring guard over the whole page is satisfied by
    whichever call site happens to carry it, which is the guard green in
    exactly the broken state this project has shipped three times.
    """
    for node in ast.walk(_page_tree()):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(_source(), node) or ""
    raise AssertionError(f"_build_reconstruct_page defines no {name}")


def test_the_page_builds_one_region_per_step_and_names_each():
    """The route builds one region per reconstruct_steps.STEPS row and
    names all four: "step 3" names nothing unless four regions exist.

    Three of them are entered at composition time and the fourth, the
    resolve region, is taken by the resolve render, which clears and
    refills it on every decision. So the fourth is held by where it is
    taken rather than by an entry, and the three entered are held in the
    order the rail draws them. What decides the order the operator walks
    is reconstruct_steps.STEPS, which tests/test_gui_reconstruct_steps.py
    reads; the order the module happens to define its builders in decides
    nothing and is not read here.

    Mutation: the `with regions[reconstruct_steps.WRITE]:` block header in
    app.py was changed to `with regions[reconstruct_steps.RESOLVE]:` and
    this guard rerun. Observed:
        E       AssertionError: the page names a region for every step
        E       assert {'PREVIEW', '...VE', 'SET_UP'} == {'PREVIEW', '..._UP', 'WRITE'}
        E
        E         Extra items in the right set:
        E         'WRITE'
        E         Use -v to get more diff
    """
    page = _page_source()
    named = set(re.findall(r"regions\[reconstruct_steps\.([A-Z_]+)\]", page))
    assert named == {"SET_UP", "PREVIEW", "RESOLVE", "WRITE"}, (
        "the page names a region for every step"
    )
    entered = re.findall(r"with regions\[reconstruct_steps\.([A-Z_]+)\]", page)
    assert entered == ["SET_UP", "PREVIEW", "WRITE"], (
        "the three regions filled at composition time are entered by name, "
        "in rail order"
    )
    assert "region = regions[reconstruct_steps.RESOLVE]" in page, (
        "the resolve region is taken by the render that refills it"
    )
    built = re.search(
        r"regions = \{.*?for number, _ in reconstruct_steps\.STEPS",
        page,
        re.DOTALL,
    )
    assert built is not None, "the regions are built from reconstruct_steps.STEPS"
    assert len(reconstruct_steps.STEPS) == 4


def test_the_resolve_step_names_the_split_the_grid_and_the_rail():
    """The resolve region names the class strings the artboard's geometry
    lives in: the split, the table, the grid, the header row and the body
    row that both sit on that grid's own tracks, and the rail's three
    bands.

    A class string named nowhere is a rule the page never wears, which is
    the shape the shell milestone's own served-page run caught.

    Mutation: the header row's `"wizard-conflict-grid
    wizard-conflict-header"` literal in app.py was reduced to
    `"wizard-conflict-header"` and this guard rerun. Observed:
        E       AssertionError: the header row sits on the conflict grid's own tracks
        E       assert 'wizard-conflict-grid wizard-conflict-header' in 'def _build_reconstruct_page() - [...]
    """
    page = _page_source()
    for name in (
        "wizard-resolve-split",
        "wizard-conflict-table",
        "wizard-conflict-grid",
        "wizard-conflict-header",
        "wizard-detail-rail",
        "wizard-detail-head",
        "wizard-detail-body",
        "wizard-detail-foot",
    ):
        assert name in page, f"the resolve step names no {name}"
    assert "wizard-conflict-grid wizard-conflict-header" in page, (
        "the header row sits on the conflict grid's own tracks"
    )
    assert "wizard-conflict-grid wizard-conflict-row" in page, (
        "a body row sits on the conflict grid's own tracks"
    )


def test_one_control_per_answer_and_one_bulk_action_per_collection():
    """The rail offers one control per distinct answer the group carries -
    not one per record - and the strip offers one bulk action per
    collection the run reads. Two collections holding identical values are
    one answer, and deciding it decides both (DL-148, DL-150, DL-154).

    Mutation: `enumerate(view.candidates, 1)` in app.py was changed to
    `enumerate(view.candidates[:1], 1)` and this guard rerun. Observed:
        E       AssertionError: the rail offers one control per distinct answer
        E       assert 'enumerate(view.candidates, 1)' in 'def _build_reconstruct_page() -> None:\\n     [...]
    """
    page = _page_source()
    assert "enumerate(view.candidates, 1)" in page, (
        "the rail offers one control per distinct answer"
    )
    assert "for input_index, label in enumerate(labels)" in page, (
        "the strip offers one bulk action per collection the run reads"
    )
    assert "conflict_model.reference_from_input(input_index)" in page, (
        "a bulk action resolves through reference_from_input, not through "
        "the first candidate"
    )
    assert "conflict_model.candidate_reference(candidate)" in page


def test_every_step_registers_a_footer_group_and_a_note():
    """Each of the four steps registers its own action group and its own
    sentence, and show_step decides which the band shows, so the control
    that advances a step exists once and its enabled state is held once
    (DL-187).

    Mutation: the `footer_groups[reconstruct_steps.WRITE] = (...)`
    registration was deleted from app.py and this guard rerun. Observed:
        E       AssertionError: every step registers a footer group and a sentence
        E       assert {'PREVIEW', '...VE', 'SET_UP'} == {'PREVIEW', '..._UP', 'WRITE'}
        E
        E         Extra items in the right set:
        E         'WRITE'
        E         Use -v to get more diff
    """
    registered = set(
        re.findall(r"footer_groups\[reconstruct_steps\.([A-Z_]+)\] = \(", _page_source())
    )
    assert registered == {"SET_UP", "PREVIEW", "RESOLVE", "WRITE"}, (
        "every step registers a footer group and a sentence"
    )
    assert "chrome.footer_note.set_text" in _page_source()


def test_the_gate_is_read_once_for_the_count_and_the_advancing_control():
    """The footer's count and the advancing control's enabled state come
    from one conflict_model.resolve_gate call per draw, not from a count
    computed for the sentence and an emptiness computed again for the
    control: two readings can disagree, and the disagreement shows as a
    control the operator can press over a sentence saying they cannot
    (DL-204).

    Mutation: `advance.set_enabled(gate.all_decided)` in app.py was
    replaced with
    `advance.set_enabled(decisions.outstanding(groups) == 0)` and this
    guard rerun. Observed:
        E       AssertionError: the page reads the gate rather than the count beneath it
        E       assert 'decisions.outstanding(' not in 'def _build_...teps.SET_UP)'
        E
        E         'decisions.outstanding(' is contained here:
        E           t_enabled(decisions.outstanding(groups) == 0)
        E                                       footer_groups[reconstruct_steps.RESOLVE] = (
        E                                           footer_groups[reconstruct_steps.RESOLVE][0],
        E                                           f"{gate.outstanding} still to decide. Writing stays "
        E                                           "closed until every one has an answer.",...
        E
        E         ...Full output truncated (549 lines hidden), use '-vv' to show
    """
    page = _page_source()
    assert "conflict_model.resolve_gate(decisions, groups)" in page
    assert "gate.all_decided" in page, (
        "the advancing control reads the gate the sentence reads"
    )
    assert "gate.outstanding" in page
    assert "gate.decided" in page
    assert "decisions.outstanding(" not in page, (
        "the page reads the gate rather than the count beneath it"
    )


def test_the_page_writes_no_dimension_and_no_class_name_of_its_own():
    """Every dimension and every colour is a constant in theme.py and
    every class name the rail carries is written in reconstruct_steps.py,
    so app.py names class strings and holds neither a value nor a rule
    (DL-069, DL-188).

    tests/test_gui_theme.py already bars a hex literal from the whole
    module; what this adds is the pixel sizes, which that sweep does not
    read.

    Mutation: `"wizard-resolve-split"` in app.py was replaced with
    `"wizard-resolve-split w-[400px]"` and this guard rerun. Observed:
        E       AssertionError: the page writes a dimension: ['400px']
        E       assert ['400px'] == []
        E
        E         Left contains one more item: '400px'
        E         Use -v to get more diff
    """
    written = re.findall(r"\b\d+(?:\.\d+)?px\b", _page_source())
    assert written == [], f"the page writes a dimension: {written}"


def test_the_resolve_table_dispatches_through_the_keymap():
    """Digits 1-9 reach a pick through keymap.dispatch at SCOPE_TABLE and
    this route's own applier table, so the second table honours the map
    Specs binds rather than inventing one (DL-071, DL-205).

    Read out of the on_key handler's own subtree. The page dispatches in
    two places - the rail's "Skip for now" control resolves an ArrowDown
    through the same map - so a scope read anywhere in the page is
    satisfied by the control's call while the handler's own scope is
    wrong.

    Mutation: `keymap.SCOPE_TABLE` in on_key's dispatch call in app.py
    was replaced with `keymap.SCOPE_DIALOG` and this guard rerun.
    Observed:
        E       AssertionError: the resolve table's key handler dispatches in the table scope
        E       assert 'keymap.SCOPE_TABLE,' in 'def on_key(event) -> None:\\n         [...]
    """
    handler = _named_function_source("on_key")
    assert "keymap.dispatch(" in handler
    assert "keymap.SCOPE_TABLE," in handler, (
        "the resolve table's key handler dispatches in the table scope"
    )
    assert "_RECONSTRUCT_ACTION_APPLIERS.get(action.name)" in handler, (
        "a dispatched action reaches this route's own applier table"
    )
    assert "candidate_count=len(" in handler, (
        "a digit past the focused row's answers is refused by dispatch"
    )

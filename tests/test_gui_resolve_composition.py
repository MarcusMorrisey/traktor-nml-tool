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

Two readings this file deliberately does not carry.

app.py's CRLF endings are guarded whole in
tests/test_gui_line_endings.py::test_app_py_is_wholly_crlf, which counts
the bytes; a second copy of that count here would drift from it rather
than reinforce it.

That the rail actually calls answer_detail is guarded by driving the
page in
tests/test_gui_conflict_page_controls.py::test_the_answer_control_is_built_out_of_answer_detail.
A source reading holds that the call is written; only a drive holds that
it runs, and a guard over answer_detail alone is green in the state
where the page never reaches it (ref: DL-189, DL-252).
"""

from __future__ import annotations

import ast
import re
import textwrap
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


# These guards read the page's own construction, not the formatting
# module's output: a guard asserting that answer_detail is correct is
# green in the state where the rail never calls it, which is exactly
# the shape this repository has shipped before (ref: DL-189, DL-252).
# The joined-label reading is the companion half - it holds in the
# broken state where an answer group draws its field rows while a
# single line joining every value stands above them (ref: DL-242).


def test_the_answer_control_draws_one_row_per_field_from_answer_detail():
    """The rail's control is built out of answer_detail.answer_fields,
    one row per field, naming the classes the sheet declares for them.

    Mutation: `answer_detail.answer_fields(view.attrs, view.agreed,
    candidate)` in app.py was changed to `[]` and this guard rerun.
    Observed:
        E       AssertionError: the rail builds its rows from something other than answer_detail.answer_fields
        E       assert 'answer_detail.answer_fields(' in 'def answer_control(group, view, candidate, reference,\n                                   supplied_by: str) -> None:\...        "wizard-answer-holders wizard-body-11 "\n                            "wizard-faint"\n                        )'
    """
    control = _named_function_source("answer_control")
    assert "answer_detail.answer_fields(" in control, (
        "the rail builds its rows from something other than "
        "answer_detail.answer_fields"
    )
    assert "view.attrs" in control and "view.agreed" in control, (
        "the rail asks answer_detail for the divergent values alone; a "
        "field the answers agree on is part of the record too"
    )
    row = _named_function_source("field_row")
    for name in (
        "wizard-answer-field",
        "wizard-answer-field-key",
        "wizard-answer-field-value",
        "wizard-answer-field-raw",
        "wizard-answer-field-mark",
    ):
        assert name in row, f"the rail names no {name}"
    for name in ("wizard-answer-fields", "wizard-answer-holders"):
        assert name in control, f"the rail names no {name}"


def test_no_call_site_joins_the_candidate_values_into_one_label():
    """The single joined label is gone from the page, not merely
    supplemented by a field grid beside it.

    This is the reading that stays true in the broken state the rest of
    this milestone can reach: answer_detail guarded on its own, the rail
    drawing its rows, and the old joined line still printed above them
    (DL-189).

    Mutation: the `' | '.join(candidate.values)` label was restored
    beside the field block in app.py and this guard rerun. Observed:
        E       AssertionError: an answer is drawn as a record, not as a joined line of values
        E       assert 'join(candidate.values)' not in 'def _build_...teps.SET_UP)'
        E
        E         'join(candidate.values)' is contained here:
        E           y} {' | '.join(candidate.values)}"
        E                                       )
        E                                       answer_control(
        E                                           group, view, candidate, reference, supplied_by
        E                                       )...
        E
        E         ...Full output truncated (644 lines hidden), use '-vv' to show
    """
    page = _page_source()
    assert "join(candidate.values)" not in page, (
        "an answer is drawn as a record, not as a joined line of values"
    )


def test_the_mark_is_read_off_the_field_rather_than_drawn_on_every_row():
    """The difference mark is rendered under `if field.differs`, so a
    row the answers agree on carries none. A mark on every row says
    nothing, which is the shape the plan cut.

    Read as an AST rather than as a substring: `if field.differs:`
    standing anywhere in the function is satisfied by a branch that
    guards something else, and what is at issue is which construction
    the branch holds.

    Mutation: `if field.differs:` was changed to `if True:` and this
    guard rerun. Observed:
        E       AssertionError: the difference mark is drawn on every row, not on the rows that differ
        E       assert not True
    """
    tree = ast.parse(textwrap.dedent(_named_function_source("field_row")))
    unguarded = True
    for branch in ast.walk(tree):
        if not isinstance(branch, ast.If):
            continue
        test = branch.test
        reads_differs = (
            isinstance(test, ast.Attribute) and test.attr == "differs"
        )
        if not reads_differs:
            continue
        if "wizard-answer-field-mark" in ast.dump(branch):
            unguarded = False
    assert not unguarded, (
        "the difference mark is drawn on every row, not on the rows that "
        "differ"
    )


def test_the_field_grid_writes_no_count_into_a_sentence():
    """The rows the rail adds state no count at all. A count written
    into a field row would be the screen restating the model beside it,
    and the rail's one count is the head's, read off the group
    (DL-215).

    Mutation: `ui.label(f"held by {supplied_by}")` was changed to
    `ui.label("held by 2 collections")` and this guard rerun. Observed:
        E       AssertionError: the field grid writes a count into a sentence: ['held by 2 collections']
        E       assert ['held by 2 collections'] == []
        E
        E         Left contains one more item: 'held by 2 collections'
        E         Use -v to get more diff
    """
    written = []
    for name in ("answer", "answer_control", "field_row"):
        tree = ast.parse(textwrap.dedent(_named_function_source(name)))
        for node in ast.walk(tree):
            # The label's own argument, not every string in the
            # function: a class string is a name the sheet answers and
            # carries digits of its own - wizard-body-11 is a rule, not
            # a sentence about the model.
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "label"
                and node.args
            ):
                continue
            written += [
                piece.value
                for piece in ast.walk(node.args[0])
                if isinstance(piece, ast.Constant)
                and isinstance(piece.value, str)
                and re.search(r"\b\d+\s+[A-Za-z]", piece.value)
            ]
    assert written == [], (
        f"the field grid writes a count into a sentence: {written}"
    )


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


def test_the_rails_head_counts_the_collections_rather_than_naming_a_number():
    """The detail rail's head says how many collections hold the focused
    file, and it builds that sentence from a count it reads off the
    group rather than from a constant.

    A group is held by as many collections as its candidates name
    between them, and the fixture the served-page record is taken on
    holds groups of three. A sentence carrying a spelled count is right
    for whichever group it was written against and wrong beside every
    row that disagrees with it, which is the screen misreporting the
    model rather than styling it badly.

    What this reads is the label's own argument, in the head's subtree
    alone. A search for a number word over the page's strings passes on
    this page whatever it composes: the rail's note explains that two
    collections holding identical values are one answer, and a docstring
    beside it says the same, so such a search is satisfied by prose that
    is not the sentence at issue.

    The count's word comes from wording.plural, so the sentence carries
    a call rather than a spelled plural; what this reads is still the
    label's own argument, which must be an f-string over the count
    rather than a constant (DL-215, DL-257).

    Mutation: the f-string was replaced with the constant `"Two
    collections hold this file with different values. Pick the one that
    supplies them."` and this guard rerun. Observed:
        E       AssertionError: the rail's head states a count it does not read: 'Two collections hold this file with different values. Pick the one that supplies them.'
        E       assert False
        E        +  where False = isinstance(Constant(value='Two collections hold this file [...]
        E        +    where <class 'ast.JoinedStr'> = ast.JoinedStr
    """
    head = _named_function_source("_render_resolve")
    tree = ast.parse(textwrap.dedent(head))
    labels = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "label"
        and node.args
        and "this file with different" in ast.dump(node.args[0])
    ]
    assert len(labels) == 1, (
        f"the rail's head label was not found once, found {len(labels)}"
    )
    argument = labels[0].args[0]
    assert isinstance(argument, ast.JoinedStr), (
        "the rail's head states a count it does not read: "
        f"{getattr(argument, 'value', argument)!r}"
    )


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

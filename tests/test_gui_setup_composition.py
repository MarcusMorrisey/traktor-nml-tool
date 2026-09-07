"""Guards how traktor_nml/gui/app.py composes the reconstruct page's
set-up step against `Reconstruct.dc.html`.

Read as source text and as an AST under the system interpreter, which
has no nicegui. What a guard here holds is what the module constructs and
which class string each construction names; what the browser resolved
from those names is read on a served page and written into a record under
docs/ (DL-084, DL-169, DL-189).

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation.
"""

from __future__ import annotations

import ast
from pathlib import Path

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"


def _source() -> str:
    return _APP_PY.read_text(encoding="utf-8")


def _page_tree() -> ast.AST:
    """The _build_reconstruct_page function's own subtree, so no guard
    below is satisfied by something the reconnect wizard builds."""
    for node in ast.walk(ast.parse(_source())):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_reconstruct_page":
            return node
    raise AssertionError("app.py defines no _build_reconstruct_page")


def _setup_region() -> ast.With:
    """The `with regions[reconstruct_steps.SET_UP]:` block itself.

    The step's own subtree rather than the page's, so a card the preview
    or the write step builds cannot satisfy a reading of this one - the
    page now composes three stepped screens out of the same class names.
    """
    for node in ast.walk(_page_tree()):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            target = item.context_expr
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == "regions"
                and "SET_UP" in (ast.get_source_segment(_source(), target.slice) or "")
            ):
                return node
    raise AssertionError("the page builds no set-up region")


def _named_function(name: str) -> ast.AST:
    for node in ast.walk(_page_tree()):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    raise AssertionError(f"_build_reconstruct_page defines no {name}")


def _body_source(node) -> str:
    """One function's statements as text, with its docstring left out.

    A guard reading a name out of a function's source is satisfied by
    that name appearing in the prose above the code, which is a guard
    green in exactly the broken state: the docstring here says which rule
    the function calls, so a function that stopped calling it would still
    read as calling it.
    """
    statements = list(node.body)
    if (
        statements
        and isinstance(statements[0], ast.Expr)
        and isinstance(statements[0].value, ast.Constant)
        and isinstance(statements[0].value.value, str)
    ):
        statements = statements[1:]
    return "\n".join(
        ast.get_source_segment(_source(), statement) or "" for statement in statements
    )


def _classes_in(node, descend_into_functions: bool = True) -> list:
    """Every literal class string a classes() call in this subtree names.

    With descend_into_functions off, the walk stops at a nested function
    rather than entering it. The set-up region also holds the render
    functions for the steps after it, and those build splits and columns
    of their own: a reading of the set-up step that counted them would be
    reading the whole page through the one region's name.
    """
    found = []
    stack = [node]
    while stack:
        current = stack.pop()
        for child in ast.iter_child_nodes(current):
            if not descend_into_functions and isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            stack.append(child)
        if (
            isinstance(current, ast.Call)
            and isinstance(current.func, ast.Attribute)
            and current.func.attr == "classes"
            and current.args
            and isinstance(current.args[0], ast.Constant)
            and isinstance(current.args[0].value, str)
        ):
            found.append(current.args[0].value)
    return found


def _composed_classes() -> list:
    """The class strings the set-up step's own composition names, with
    the nested renders left out."""
    return _classes_in(_setup_region(), descend_into_functions=False)


def test_the_set_up_step_composes_two_columns_inside_one_split():
    """Reconstruct.dc.html:27 draws main as a content column beside a
    rail: the four cards the step is filled in through at the left, and
    what the run will do with them at the right. The step composes that
    as one wizard-step-split holding two wizard-step-column boxes, the
    same split the preview and the write steps stand in.

    Mutation: the second wizard-step-column was renamed
    wizard-step-columns. Observed:
        E       AssertionError: the set-up step draws 1 columns in 1 splits
        E       assert 1 == 2
    """
    classes = _composed_classes()
    splits = [text for text in classes if "wizard-step-split" in text.split()]
    columns = [text for text in classes if "wizard-step-column" in text.split()]
    assert len(splits) == 1, f"the set-up step draws {len(splits)} splits"
    assert len(columns) == 2, (
        f"the set-up step draws {len(columns)} columns in {len(splits)} splits"
    )


def test_every_chosen_path_stands_in_a_field_beside_its_own_control():
    """Reconstruct.dc.html:44's .field: each of the three paths the step
    takes - the collection to repair, each source, the output - stands in
    a bordered box with the control that changes it beside it, so what
    the page has been given and what may still be changed are told apart
    by the box around one of them.

    The source's field is read inside draw_sources rather than in the
    composition, because the source list is redrawn from the holder and
    its rows are built there. The other two are built once and filled.

    Mutation: the source row's wizard-field span was given
    wizard-field-row, so the row held a row rather than a field.
    Observed:
        E       AssertionError: draw_sources builds no field for a source's path
        E       assert 0 >= 1
    """
    composed = _composed_classes()
    for name in ("wizard-field", "wizard-field-row"):
        built = [text for text in composed if name in text.split()]
        assert len(built) >= 2, (
            f"the composition builds {len(built)} {name} boxes, "
            "not one for the collection to repair and one for the output"
        )
    # One reading per path, each in the place that path is drawn: the
    # output's in the composition, the other two in the redraws that own
    # them.
    for owner, names in (
        (_setup_region(), ("wizard-field-value",)),
        (_named_function("draw_base"), ("wizard-field-value",)),
        (
            _named_function("draw_sources"),
            ("wizard-field", "wizard-field-row", "wizard-field-value"),
        ),
    ):
        for name in names:
            built = [
                text for text in _classes_in(owner) if name in text.split()
            ]
            assert len(built) >= 1, f"no {name} is built for a path"


def test_what_the_chosen_collection_reports_is_read_off_the_summary():
    """Reconstruct.dc.html:112 prints what the file itself says - its
    tracks, its playlists, how many of those hold nothing - and those
    phrases are collection_summary's own rather than a sentence written
    at the call site, so the count of empty playlists that makes this
    page worth running is stated by the reading that took it (DL-220).

    Mutation: the `for index, phrase in enumerate(summary.repair_phrases)`
    loop was changed to iterate a tuple of literals written in draw_base.
    Observed:
        E       AssertionError: draw_base writes its own phrases rather than reading the summary's
        E       assert 'summary.repair_phrases' in 'base_field.clear()[...]'
    """
    draw_base = _body_source(_named_function("draw_base"))
    assert "summary.repair_phrases" in draw_base, (
        "draw_base writes its own phrases rather than reading the summary's"
    )
    draw_sources = _body_source(_named_function("draw_sources"))
    assert "summary.source_note" in draw_sources, (
        "a source row writes its own note rather than reading the summary's"
    )


def test_the_line_about_the_output_and_the_write_read_one_rule():
    """The set-up step says whether the output path names a collection
    the run reads, and the write refuses on the same question. Both call
    conflict_model.output_refusal, so the step cannot describe a path as
    a new file over a write that would refuse it (DL-222).

    Mutation: draw_output_note's call to conflict_model.output_refusal
    was replaced with a comparison of the output's name against the
    base's. Observed:
        E       AssertionError: the set-up step decides the collision itself
        E       assert 'conflict_model.output_refusal' in 'output_meta.clear()[...]'
    """
    note = _body_source(_named_function("draw_output_note"))
    assert "conflict_model.output_refusal" in note, (
        "the set-up step decides the collision itself"
    )
    write = _body_source(_named_function("write_output"))
    assert "conflict_model.output_refusal" in write, (
        "the write decides the collision itself"
    )


def test_the_step_says_what_happens_next_from_the_step_table():
    """Reconstruct.dc.html:167-171 lists the three steps that follow this
    one. The page renders collection_summary.NEXT_STEPS rather than
    writing three numbered rows, so the numbers on that list and the
    numbers on the rail above it are one table (DL-221).

    Mutation: the `for step in collection_summary.NEXT_STEPS` loop was
    replaced with three literal rows. Observed:
        E       AssertionError: the step writes its own account of what follows
        E       assert 'collection_summary.NEXT_STEPS' in '        with regions[reconstruct_steps.SET_UP]:[...]'
    """
    region = ast.get_source_segment(_source(), _setup_region()) or ""
    assert "collection_summary.NEXT_STEPS" in region, (
        "the step writes its own account of what follows"
    )
    classes = _composed_classes()
    assert any("wizard-next-steps" in text.split() for text in classes)
    assert any("wizard-next-step-marker" in text.split() for text in classes)

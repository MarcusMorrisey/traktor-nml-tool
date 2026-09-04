"""Guards what the conflict surface of the page registered at '/'
delegates, without importing nicegui - the suite runs on the system
interpreter, which has none. What is tested here is app.py's source, by
AST walk, matching the register tests/test_gui_view_boundary.py uses:
each guard constructs its scenario over the real source and its
docstring records the mutation applied to app.py and the output
observed under it.

The rule these five guards hold together is one rule: the page renders
and the model decides. The conflict rows come from conflict_model's row
projection, the write refusal comes from conflict_model.write_refusal
rather than from a second reading of result.output, the run-wide control
offers the splice subcommand's own two choices onto on_conflict, the
per-track picks reach assemble_output through resolutions and nothing
else, the rows are hand-rolled rather than ui.aggrid (DL-079, DL-110),
and no count or decision reading is written inline where the suite
cannot reach it (DL-069, DL-106, DL-111).
"""

from __future__ import annotations

import ast
from pathlib import Path

APP_PATH = Path(__file__).parent.parent / "traktor_nml" / "gui" / "app.py"

PAGE = "_build_reconstruct_page"

# The two choices traktor_nml/commands/splice_cmd.py gives --on-conflict.
SPLICE_ON_CONFLICT_CHOICES = frozenset({"keep-first", "keep-last"})

# The three decision tokens conflict_model owns. A page writing one of
# these as a literal is reading a decision itself.
DECISION_TOKENS = frozenset({"undecided", "base", "source"})


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

    Observed to fail against a real mutation: replacing the outstanding
    count's `decisions.outstanding(groups)` in app.py with
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
        "the page must hold no count arithmetic; the outstanding count is "
        "read from conflict_model.ConflictDecisions.outstanding"
    )
    assert _calls(page, "outstanding"), (
        "the page must render conflict_model's outstanding count"
    )

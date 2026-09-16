"""Guards the reconstruct page's step table in
traktor_nml/gui/reconstruct_steps.py: the four rail records it derives
and the reachability rule that decides which step the page may show.

The module imports no framework, which is what lets these run under the
system interpreter; the AST walk in tests/test_gui_view_boundary.py is
what holds that boundary (DL-069, DL-203). What a guard here holds is the
record a rail entry renders from - its position, its class string, its
marker and its aria-current value. Where the rail actually lands on the
page, and whether it spans the page region, is a served-page reading and
belongs to the record (DL-189).

has_result and all_decided reach reachable() here as plain booleans: what
decides all_decided in the running page is conflict_model.resolve_gate,
and that rule is held in tests/test_gui_resolve_rules.py. Splitting them
this way keeps the step rule readable on its own inputs and leaves the
gate one guard, not two (DL-204).

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation.
"""

from __future__ import annotations

from traktor_nml.gui import reconstruct_steps as steps


def test_the_table_carries_the_four_steps_the_artboards_draw():
    """The four artboards on canvas page 3 draw one rail of four steps:
    Set up, Preview, Resolve, Write, numbered one to four. STEPS is the
    one place either a number or a label is written.

    Mutation: the (RESOLVE, "Resolve") row was deleted from STEPS in
    reconstruct_steps.py and this guard rerun. Observed:
        E       AssertionError: the rail is the four steps the artboards draw
        E       assert ((1, 'Set up'... (4, 'Write')) == ((1, 'Set up'... (4, 'Write'))
        E
        E         At index 2 diff: (4, 'Write') != (3, 'Resolve')
        E         Right contains one more item: (4, 'Write')
        E         Use -v to get more diff
    """
    assert steps.STEPS == (
        (1, "Set up"),
        (2, "Preview"),
        (3, "Resolve"),
        (4, "Write"),
    ), "the rail is the four steps the artboards draw"
    assert (steps.SET_UP, steps.PREVIEW, steps.RESOLVE, steps.WRITE) == (1, 2, 3, 4)


def test_the_rail_reads_done_before_the_current_row_and_upcoming_after_it():
    """One record per row in table order, exactly one current, every row
    before it done and every row after it upcoming. Resolve.dc.html:135-139
    draws exactly that: two done steps, the current step, and one still to
    come.

    Mutation: `number < current` in _record was replaced with
    `number > current` in reconstruct_steps.py and this guard rerun.
    Observed:
        E       AssertionError: exactly one row reads current
        E       assert ['upcoming', ...rent', 'done'] == ['done', 'don...', 'upcoming']
        E
        E         At index 0 diff: 'upcoming' != 'done'
        E         Use -v to get more diff
    """
    records = steps.rail_records(steps.RESOLVE)
    assert [record.number for record in records] == [1, 2, 3, 4]
    assert [record.state for record in records] == [
        steps.DONE,
        steps.DONE,
        steps.CURRENT,
        steps.UPCOMING,
    ], "exactly one row reads current"
    assert sum(1 for record in records if record.state == steps.CURRENT) == 1


def test_each_record_carries_the_class_string_and_the_marker_its_state_names():
    """A done entry carries the done class and the check mark in its
    marker; the current entry carries the current class, the current
    marker class and aria-current "step"; an upcoming entry carries the
    base class alone and its own number. Nothing else on the page decides
    which entry is marked (DL-202).

    Mutation: `aria_current=ARIA_CURRENT_STEP if state == CURRENT else None`
    in _record was replaced with `aria_current=ARIA_CURRENT_STEP` in
    reconstruct_steps.py and this guard rerun. Observed:
        E       AssertionError: only the current entry carries aria-current
        E       assert ['step', 'ste...step', 'step'] == [None, None, 'step', None]
        E
        E         At index 0 diff: 'step' != None
        E         Use -v to get more diff
    """
    done, _preview, current, upcoming = steps.rail_records(steps.RESOLVE)

    assert done.classes == "wizard-step wizard-step-done"
    assert done.marker == steps.DONE_MARKER
    assert done.marker_classes == "wizard-step-number"

    assert current.classes == "wizard-step wizard-step-current"
    assert current.marker == "3"
    assert current.marker_classes == "wizard-step-number wizard-step-number-current"

    assert upcoming.classes == "wizard-step"
    assert upcoming.marker == "4"

    assert [record.aria_current for record in steps.rail_records(steps.RESOLVE)] == [
        None,
        None,
        steps.ARIA_CURRENT_STEP,
        None,
    ], "only the current entry carries aria-current"


def test_a_current_the_table_does_not_name_marks_no_row():
    """A number no row carries leaves every record upcoming rather than
    marking the first row by accident, so a caller holding a step the
    table does not name renders a rail with nothing marked.

    Mutation: the `any(row == current for row, _ in STEPS) and` clause was
    deleted from _record's done branch in reconstruct_steps.py and this
    guard rerun. Observed:
        E       AssertionError: a step the table does not name marks no row
        E       assert ['done', 'don...done', 'done'] == ['upcoming', ...', 'upcoming']
        E
        E         At index 0 diff: 'done' != 'upcoming'
        E         Use -v to get more diff
    """
    assert [record.state for record in steps.rail_records(9)] == [
        steps.UPCOMING
    ] * 4, "a step the table does not name marks no row"


def test_reachability_refuses_a_step_past_a_shut_gate():
    """Set up is always reachable; preview and resolve need a held run;
    write needs a run that produced an output whose divergences are every
    one decided. The gate is conflict_model.resolve_gate's own answer, so
    the step this refuses and the count the footer prints cannot disagree
    (DL-204).

    Mutation: reachable's final `return has_output and all_decided` was
    replaced with `return has_output` in reconstruct_steps.py and this
    guard rerun. Observed:
        E       AssertionError: the write step is shut while a group is undecided
        E       assert not True
        E        +  where True = <function reachable at 0x000001CAD1D99220>(4, True, True, False)
        E        +    where <function reachable at 0x000001CAD1D99220> = steps.reachable
        E        +    and   4 = steps.WRITE
    """
    assert steps.reachable(steps.SET_UP, False, False, False)
    assert not steps.reachable(steps.PREVIEW, False, False, False)
    assert not steps.reachable(steps.RESOLVE, False, False, True)
    assert steps.reachable(steps.RESOLVE, True, False, False)
    assert not steps.reachable(steps.WRITE, True, True, False), (
        "the write step is shut while a group is undecided"
    )
    assert steps.reachable(steps.WRITE, True, True, True)


def test_a_run_that_assembled_nothing_does_not_open_the_write_step():
    """The write step reports what the new file will hold, so it needs a
    run that produced one. A run that refused is a held result carrying
    no output: reaching the write step on it stood the step there
    printing zeros for the playlists filled and for the tracks the file
    holds, beside a count of answers read off the decisions rather than
    off any run (DL-224).

    The resolve step is reachable on that same refused run, and must be:
    the conflicts it reported are what the operator is there to settle.

    Mutation: reachable's final `return has_output and all_decided` was
    replaced with `return has_result and all_decided` in
    reconstruct_steps.py and this guard rerun. Observed:
        E       AssertionError: a run that produced no output opens the write step
        E       assert not True
        E        +  where True = <function reachable at 0x0000020A9EC75220>(4, True, False, True)
        E        +    where <function reachable at 0x0000020A9EC75220> = steps.reachable
        E        +    and   4 = steps.WRITE
    """
    assert not steps.reachable(steps.WRITE, True, False, True), (
        "a run that produced no output opens the write step"
    )
    assert steps.reachable(steps.RESOLVE, True, False, False), (
        "the step that settles the conflicts is shut on the run that "
        "reported them"
    )


def test_a_target_the_table_does_not_name_is_refused():
    """A number no STEPS row carries is refused rather than defaulted, so
    a caller holding a step the table does not name stays where it is.

    Mutation: the `if not any(number == target ...): return False` guard
    was deleted from reachable in reconstruct_steps.py and this guard
    rerun. Observed:
        E       AssertionError: a step the table does not name is refused
        E       assert not True
        E        +  where True = <function reachable at 0x0000027FCCA0C3B0>(9, True, True, True)
        E        +    where <function reachable at 0x0000027FCCA0C3B0> = steps.reachable
    """
    assert not steps.reachable(9, True, True, True), (
        "a step the table does not name is refused"
    )
    assert not steps.reachable(0, True, True, True)

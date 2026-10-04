"""Guards the reconstruct page's preview and write steps: the records
reconstruct_report derives for them, and how traktor_nml/gui/app.py
composes those records against `Preview.dc.html` and `Write.dc.html`.

The record half runs the rules themselves, because reconstruct_report
imports no framework. The composition half reads app.py as source text
and as an AST, and it can hold only what the module constructs and which
class string each construction names: a guard reading a class name is
true in exactly the broken state, so what the browser resolved from those
names is read on a served page and written into a record under docs/
(DL-084, DL-169, DL-189).

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation. Where pytest printed an assertion
repr longer than the margin, the line is cut with an ellipsis rather than
rewrapped, so what stands is what pytest printed.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from traktor_nml import metadata_tier, splice
from traktor_nml.gui import (
    answer_detail,
    conflict_model,
    reconstruct_report,
    reconstruct_steps,
)

_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"
_REPORT_PY = (
    Path(__file__).resolve().parents[1]
    / "traktor_nml"
    / "gui"
    / "reconstruct_report.py"
)

# The two collection names a run over a pair holds at input indices 0 and
# 1, which is what app.py's _collection_labels answers: the collection
# being repaired first, then the source. A listed winner cell is worded
# from this tuple and the input index the settled row carries (DL-150).
_LABELS = ("base", "collection-b.nml")


def _source() -> str:
    return _APP_PY.read_text(encoding="utf-8")


def _page_tree() -> ast.AST:
    """The _build_reconstruct_page function's own subtree, so no guard
    below is satisfied by something the reconnect wizard builds."""
    for node in ast.walk(ast.parse(_source())):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_reconstruct_page":
            return node
    raise AssertionError("app.py defines no _build_reconstruct_page")


def _named_function(name: str) -> ast.FunctionDef:
    for node in ast.walk(_page_tree()):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    raise AssertionError(f"_build_reconstruct_page defines no {name}")


def _body_source_of(name: str) -> str:
    """One nested function's statements as text, with its docstring left
    out.

    A guard reading a call out of a function's source is satisfied by
    that call appearing in the prose above the code, which is a guard
    green in exactly the broken state: these docstrings name the rules
    their functions call.
    """
    node = _named_function(name)
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


def _classes_in(node) -> list:
    """Every literal class string a classes() call in this subtree
    names."""
    return [
        call.args[0].value
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "classes"
        and call.args
        and isinstance(call.args[0], ast.Constant)
        and isinstance(call.args[0].value, str)
    ]


def _stats(**overrides) -> dict:
    """A held run's stats, as splice.assemble_output reports them."""
    stats = {
        "reconstructed_playlists": {},
        "refilled_playlists": 0,
        "empty_playlists": 0,
        "unfilled_playlists": [],
        "collection_entries_total": 0,
        # The count of groups the tier answered, which splice writes from
        # the same list settled_rows is: the record reads its settled
        # count off this rather than off the rows handed in, so the two
        # cannot disagree (DL-204, DL-215).
        "groups_settled_by_rule": 0,
    }
    stats.update(overrides)
    return stats


def _group(identity_key: str, *values: str) -> conflict_model.ConflictGroup:
    """One conflicting group holding one candidate per value, each
    supplied by its own input."""
    return conflict_model.ConflictGroup(
        identity_key=identity_key,
        attrs=("album",),
        member_keys=frozenset({identity_key}),
        candidates=tuple(
            conflict_model.ConflictCandidate(
                values={"album": value}, members=((index, identity_key),)
            )
            for index, value in enumerate(values)
        ),
    )


# --------------------------------------------------------------------
# The records.
# --------------------------------------------------------------------


def test_the_listing_and_the_row_standing_for_the_rest_are_one_division():
    """Preview.dc.html:144-153 draws nine playlists by name and a tenth
    row standing for the rest. The two are one division of one list, so
    the count that row names and the rows above it cannot disagree, and
    the entries it sums are the ones no row above it printed.

    Mutation: `rest = rows[LISTED_PLAYLISTS:]` was changed to
    `rows[LISTED_PLAYLISTS - 1:]`, so the row standing for the rest also
    stood for one the listing had already named. Observed:
        E       AssertionError: assert 'and 12 more' == 'and 11 more'
        E
        E         - and 11 more
        E         ?      ^
        E         + and 12 more
        E         ?      ^
    """
    rebuilt = {f"list-{index:02d}": index for index in range(1, 21)}
    record = reconstruct_report.preview_report(
        _stats(reconstructed_playlists=rebuilt),
        [],
        conflict_model.ConflictDecisions(),
        (),
        (),
    )
    assert record.entries_added == 0, (
        "a run that added nothing reports nothing added, whatever its "
        "rebuilt playlists hold"
    )
    assert len(record.listed) == reconstruct_report.LISTED_PLAYLISTS
    assert record.remainder is not None
    assert record.remainder.name == "and 11 more"
    # The row sums what it stands for: the eleven entry counts no row
    # above it printed.
    assert record.remainder.entries == sum(range(1, 12)), record.remainder.entries
    # Every entry is counted once: the nine listed plus the summed rest
    # is the whole run. Read against the rebuilt totals rather than
    # against entries_added, which counts something else: what the run put
    # there, as against what those playlists hold once it has (DL-238).
    assert sum(row.entries for row in record.listed) + record.remainder.entries == sum(
        rebuilt.values()
    )


def test_a_run_whose_playlists_all_fit_draws_no_row_standing_for_the_rest():
    """A tenth row is drawn for what is left over, so a run with nothing
    left over draws none: a row reading "and 0 more" would be a row
    standing for nothing.

    Mutation: `remainder = (... if rest else None)` was changed to build
    the row unconditionally. Observed:
        E       assert PlaylistRow(name='and 0 more', entries=0) is None
        E        +  where PlaylistRow(name='and 0 more', entries=0) = PreviewReport(listed=(PlaylistRow(name='one', entries=3),), remainder=PlaylistRow(name='and 0 more', entries=0), filled=0, empty=0, entries_added=3, unfilled=(), conflicts=0).remainder
    """
    record = reconstruct_report.preview_report(
        _stats(reconstructed_playlists={"one": 3}),
        [],
        conflict_model.ConflictDecisions(),
        (),
        (),
    )
    assert record.remainder is None


def test_the_head_counts_the_playlists_this_run_filled_against_the_ones_it_found():
    """Preview.dc.html:141's label prints both numbers, because a count
    of playlists filled says nothing without the count there were to
    fill. Both are read off the run's own stats.

    Mutation: `filled=int(stats.get("refilled_playlists") or 0)` was
    changed to read "playlists_reconstructed", a key the stats a caller
    hands this need not carry. Observed:
        E       AssertionError: 0 of 9 empty playlists
        E       assert '0 of 9 empty playlists' == '3 of 9 empty playlists'
        E
        E         - 3 of 9 empty playlists
        E         ? ^
        E         + 0 of 9 empty playlists
        E         ? ^
    """
    record = reconstruct_report.preview_report(
        _stats(
            reconstructed_playlists={"a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
            refilled_playlists=3,
            empty_playlists=9,
        ),
        [],
        conflict_model.ConflictDecisions(),
        (),
        (),
    )
    assert record.filled_caption == "3 of 9 empty playlists", record.filled_caption


def test_the_preview_says_what_the_step_it_points_at_would_say():
    """The note at Preview.dc.html:161 names how many tracks are held
    more than one way with no answer yet, and the resolve step offers one
    row per group. Both counts are the decisions' own, so a preview
    naming decisions still to make over a step where every one has an
    answer is not reachable, and neither is a preview promising more
    decisions than the step offers (DL-215, DL-219).

    Mutation: `outstanding=conflict_model.resolve_gate(decisions,
    groups).outstanding` was changed to `outstanding=len(groups)`.
    Observed:
        E       AssertionError: 2 tracks are held differently by more than one collection with no answer yet. Each one has to be decided before anything can be written. That is step 3.
        E       assert False
        E        +  where False = <built-in method startswith of str object at [...]>('Every one of the 2 tracks')
        E        +    where <built-in method startswith of str object at [...]> = '2 tracks are held differently by [...]'.startswith
        E        +      where '2 tracks are held differently by [...]' = PreviewReport(listed=(), remainder=None, filled=0, empty=0, entries_added=0, unfilled=(), conflicts=2, outstanding=2).conflict_sentence
    """
    groups = [_group("one", "A", "B"), _group("two", "A", "B")]
    decisions = conflict_model.ConflictDecisions()
    undecided = reconstruct_report.preview_report(
        _stats(), groups, decisions, (), ()
    )
    assert undecided.conflict_sentence.startswith("2 tracks are held"), (
        undecided.conflict_sentence
    )
    for group in groups:
        decisions.resolve(
            group, conflict_model.candidate_reference(group.candidates[1])
        )
    settled = reconstruct_report.preview_report(
        _stats(), groups, decisions, (), ()
    )
    assert settled.conflict_sentence.startswith("Every one of the 2 tracks"), (
        settled.conflict_sentence
    )
    # A run reporting no divergence prints no sentence at all rather than
    # one naming zero.
    assert (
        reconstruct_report.preview_report(
            _stats(), [], conflict_model.ConflictDecisions(), (), ()
        ).conflict_sentence
        == ""
    )


def test_the_write_step_counts_the_chosen_answers_off_the_gate_that_opened_it():
    """The third change row at Write.dc.html:118-122 names how many
    tracks take a value the operator chose. That count is
    resolve_gate.decided - the same value reconstruct_steps.reachable
    reads to open the step - so the step cannot list a run other than the
    one about to be written (DL-204).

    Mutation: `count=gate.decided` was changed to `count=len(groups)`.
    Observed:
        E       AssertionError: ChangeRow(label='Tracks taking the values you chose', detail='Decided at step 3, one answer per track held more than one way.', count=2, tone='added')
        E       assert 2 == 1
        E        +  where 2 = ChangeRow(label='Tracks taking the values you chose', [...], count=2, tone='added').count
        E        +  and   1 = ResolveGate(outstanding=1, decided=1, all_decided=False).decided
    """
    groups = [_group("one", "A", "B"), _group("two", "A", "B")]
    decisions = conflict_model.ConflictDecisions()
    decisions.resolve(
        groups[0], conflict_model.candidate_reference(groups[0].candidates[1])
    )
    gate = conflict_model.resolve_gate(decisions, groups)
    record = reconstruct_report.write_report(
        _stats(), groups, decisions, "out.nml", False, ["base.nml"]
    )
    chosen = record.rows[2]
    assert chosen.count == gate.decided, chosen
    assert gate.decided == 1
    # The step is shut while that gate is: the row and the refusal read
    # one value.
    assert not reconstruct_steps.reachable(
        reconstruct_steps.WRITE, True, True, gate.all_decided
    )


def test_the_confirmation_names_the_count_the_list_beside_it_carries():
    """Write.dc.html:162's heading names how many playlists are being
    filled, and the first change row prints the same number. It is read
    off that row rather than recounted, so the two are one fact
    (DL-215).

    Mutation: `filled = self.rows[0].count if self.rows else 0` was
    changed to `filled = len(self.rows)`. Observed:
        E       AssertionError: Write 4 rebuilt playlists?
        E       assert 'Write 4 rebuilt playlists?' == 'Write 7 rebuilt playlists?'
        E
        E         - Write 7 rebuilt playlists?
        E         ?       ^
        E         + Write 4 rebuilt playlists?
        E         ?       ^
    """
    record = reconstruct_report.write_report(
        _stats(refilled_playlists=7), [], conflict_model.ConflictDecisions(),
        "out.nml", False, ["base.nml"],
    )
    assert record.rows[0].count == 7
    assert record.confirm_question == "Write 7 rebuilt playlists?", (
        record.confirm_question
    )


def test_an_output_path_that_exists_is_said_so_rather_than_left_unsaid():
    """The badge at Write.dc.html:98 states what the path is, in both
    directions: the write replaces a file that is already there, and
    whether that is what was meant is the operator's to decide, not the
    screen's to omit.

    Mutation: `"Already exists" if self.destination_exists else` was
    changed to return the not-yet sentence in both branches. Observed:
        E       AssertionError: Does not exist yet
        E       assert 'Does not exist yet' == 'Already exists'
        E
        E         - Already exists
        E         + Does not exist yet
    """
    existing = reconstruct_report.write_report(
        _stats(), [], conflict_model.ConflictDecisions(), "out.nml", True, []
    )
    assert existing.destination_badge == "Already exists", existing.destination_badge
    absent = reconstruct_report.write_report(
        _stats(), [], conflict_model.ConflictDecisions(), "out.nml", False, []
    )
    assert absent.destination_badge == "Does not exist yet"


# The settled half of the preview record. The stand-in below carries the
# attributes the record reads and nothing else, so these guards need no
# splice run and no collection on disk: what is under test is the
# division of one settled-row list into a count and a listing, and the
# wording read off that count (DL-215, DL-217).
#
# splice.SettledRow's own shape is guarded in tests/test_splice.py; a
# stand-in that drifted from it would make these guards green against a
# row the run never reports, so the attribute names here are the ones
# that file asserts (DL-189).


def _settled(identity_key, attr, low, high, gap, winner,
             artist="Drexciya", title="Andreaen Sand Dunes"):
    """One splice.SettledRow-shaped stand-in: the record half reads the
    attributes it reads, so the guards below need no splice run.

    winner is the (input index, primary key) pair the row carries, the
    shape the record words its listed winner cell from (DL-148)."""
    return SimpleNamespace(
        identity_key=identity_key,
        attrs=(attr,),
        winner=winner,
        # The winning record's own artist and title, which is what
        # Preview.dc.html:192 draws in a listed reading's .nm cell.
        artist=artist,
        title=title,
        outliers=(
            # The reading names the value the output keeps and the member
            # value it is read against; low and high are those two in
            # magnitude order, which is what the record reads. The
            # stand-in keeps the high end as the kept value, so the pair
            # the record words its spread cell from is (low, high).
            metadata_tier.OutlierReading(
                attr=attr, kept=high, other=low, relative_gap=gap
            ),
        )
        if gap
        else (),
        is_outlier=bool(gap),
    )


def test_a_run_with_settled_groups_and_outliers_composes_both_readings():
    """The count sentence and the listing are one division of the one
    settled_rows list, so the number the sentence names and the rows
    drawn under it cannot disagree (DL-215, DL-217).

    Fail-first mutation: `settled=len(settled_rows)` replaced by
    `settled=sum(1 for r in settled_rows if r.is_outlier)`, so the
    sentence's count is read off the listing rather than off the whole
    settled list.
    Observed:
        E       AssertionError: assert 1 == 2
        E        +  where 1 = PreviewReport(listed=(), remainder=None, filled=0, empty=0, entries_added=0, unfilled=(), conflicts=0, outstanding=0, ..., high='69203', low_detail='17.2 MB', high_detail='67.6 MB', relative_gap=0.7462, winner='base: C:/:Music/:one.mp3'),)).settled
    """
    record = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=2),
        (),
        conflict_model.ConflictDecisions(),
        (
            _settled("C:/:Music/:one.mp3", "filesize", "17564", "69203", 0.7462,
                     (0, "C:/:Music/:one.mp3")),
            _settled("C:/:Music/:two.mp3", "filesize", "8123", "8124", 0.0,
                     (1, "C:/:Music/:two.mp3")),
        ),
        _LABELS,
    )
    assert record.settled == 2
    assert record.outlier_count == 1
    assert "2 tracks are measured differently" in record.settled_sentence
    assert record.outlier_title == "The one measured far apart"


def test_one_settled_group_reads_the_singular():
    """The sentence's word comes from wording.plural, so one group reads
    "1 track is" and "It carries" (DL-233).

    Fail-first mutation: `held = plural(self.settled, "track is",
    "tracks are")` replaced by `held = "tracks are"`.
    Observed:
        E       assert '1 track is measured differently by the two collections' in "1 tracks are measured differently by the two collections - file size, length or bitrate. Both numbers are Traktor's own, so there is nothing to decide. It carries the values of the record the output keeps."
        E        +  where "1 tracks are measured differently by the two collections - file size, length or bitrate. Both numbers are Traktor's own, so there is nothing to decide. It carries the values of the record the output keeps." = PreviewReport(listed=(), remainder=None, filled=0, empty=0, entries_added=0, unfilled=(), conflicts=0, outstanding=0, ...h='1411000', low_detail='320 kbps', high_detail='1411 kbps', relative_gap=0.7732, winner='base: C:/:Music/:one.mp3'),)).settled_sentence
    """
    record = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=1),
        (),
        conflict_model.ConflictDecisions(),
        (_settled("C:/:Music/:one.mp3", "bitrate", "320000", "1411000", 0.7732,
                  (0, "C:/:Music/:one.mp3")),),
        _LABELS,
    )
    assert "1 track is measured differently by the two collections" in record.settled_sentence
    assert "It carries the values of the record the output keeps." in record.settled_sentence


def test_the_listing_names_the_record_the_output_keeps():
    """The note under the listing says the output carries the record named
    beside each one, so every row names that record by the collection it
    was read from and its primary key together. The key alone is the one
    value every member of a settled group carries, and a collection word
    alone is the base-or-source token DL-148 refuses, so a row naming
    either on its own says which record won of neither.

    The second row is the same track kept from the second collection, so
    a cell worded from the key alone would read identically for both and
    this guard would be green in exactly the broken state (DL-189).

    Fail-first mutation: `winner=_winner_reading(row.winner, labels)`
    replaced by `winner=row.attrs[0]` on the OutlierRow.
    Observed:
        E       AssertionError: assert 'filesize' == 'base: C:/:Music/:one.mp3'
        E
        E         - base: C:/:Music/:one.mp3
        E         + filesize
    """
    record = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=2),
        (),
        conflict_model.ConflictDecisions(),
        (
            # The wider gap of the two, so the listing's widest-first
            # order puts this reading first and the assertions below read
            # the two in a fixed order.
            _settled("C:/:Music/:one.mp3", "filesize", "17564", "69203", 0.7962,
                     (0, "C:/:Music/:one.mp3")),
            _settled("C:/:Music/:one.mp3", "bitrate", "320000", "1411000", 0.7732,
                     (1, "C:/:Music/:one.mp3")),
        ),
        _LABELS,
    )
    first, second = record.outliers
    assert first.winner == f"{_LABELS[0]}: C:/:Music/:one.mp3"
    assert second.winner == f"{_LABELS[1]}: C:/:Music/:one.mp3"
    assert first.winner != second.winner
    assert first.label == answer_detail.LABELS["filesize"]
    assert first.spread == "17564 (17.2 MB) -> 69203 (67.6 MB)"
    assert first.gap_amount == "79.6%"
    for text in (record.settled_sentence, record.outlier_note):
        assert "base" not in text


def test_a_winner_index_outside_the_labels_reads_as_the_index_itself():
    """A caller composing a record for a run whose labels it does not
    hold reads a row rather than an IndexError, and the index still tells
    the two records apart.

    Fail-first mutation: the `if input_index < len(labels)` branch
    dropped, leaving `named = labels[input_index]`.
    Observed:
        winner = (1, 'C:/:Music/:one.mp3'), labels = ()
        E       IndexError: tuple index out of range
    """
    record = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=1),
        (),
        conflict_model.ConflictDecisions(),
        (_settled("C:/:Music/:one.mp3", "filesize", "17564", "69203", 0.7462,
                  (1, "C:/:Music/:one.mp3")),),
        (),
    )
    assert record.outliers[0].winner == "input 1: C:/:Music/:one.mp3"


def test_a_run_with_settled_groups_but_no_outlier_composes_no_listing():
    """The card is its count: the ordinary 1 KB drift answers the sentence
    and draws no rows.

    Fail-first mutation: `outlier_count` returning `self.settled`, so
    the card's head counts settled groups rather than the readings drawn
    under it.
    Observed:
        E       assert 1 == 0
        E        +  where 1 = PreviewReport(listed=(), remainder=None, filled=0, empty=0, entries_added=0, unfilled=(), conflicts=0, outstanding=0, settled=1, outliers=()).outlier_count
    """
    record = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=1),
        (),
        conflict_model.ConflictDecisions(),
        (_settled("C:/:Music/:two.mp3", "filesize", "8123", "8124", 0.0,
                  (0, "C:/:Music/:two.mp3")),),
        _LABELS,
    )
    assert record.settled == 1
    assert record.outlier_count == 0
    assert record.outliers == ()


def test_a_run_the_rule_settled_nothing_for_composes_no_settled_reading():
    """A sentence reading 0 names something the run did not do, so it is
    empty - the way conflict_sentence is empty for a run that reported no
    divergence. A refused run reads the same way.

    Fail-first mutation: the `if not self.settled: return ""` guard
    removed from settled_sentence.
    Observed:
        E       AssertionError: assert '0 tracks are...output keeps.' == ''
        E
        E         + 0 tracks are measured differently by the two collections - file size, length or bitrate. Both numbers are Traktor's own, so there is nothing to decide. Each carries the values of the record the output keeps.
    """
    record = reconstruct_report.preview_report(
        _stats(), (), conflict_model.ConflictDecisions(), (), ()
    )
    assert record.settled_sentence == ""
    assert record.outliers == ()


def test_no_inline_count_of_one_conditional_stands_in_the_module():
    """Every count sentence in reconstruct_report reads its number off the
    record and takes its word from wording.plural; an `x if n == 1 else y`
    beside one is the pattern tests/test_gui_wording.py forbids under gui/
    and this guard reads this module for it directly (DL-215, DL-233).

    Fail-first mutation: outlier_title written as
    `"The one measured far apart" if self.outlier_count == 1 else ...`.
    Observed:
        E       AssertionError: reconstruct_report.py words a count with an inline conditional
        E       assert ['outlier_title'] == []
        E
        E         Left contains one more item: 'outlier_title'
        E         Use -v to get more diff
    """
    tree = ast.parse(_REPORT_PY.read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.IfExp) and any(
                isinstance(cmp_node, ast.Compare)
                and any(
                    isinstance(c, ast.Constant) and c.value == 1
                    for c in cmp_node.comparators
                )
                for cmp_node in ast.walk(inner.test)
            ):
                offenders.append(node.name)
    assert offenders == [], (
        "reconstruct_report.py words a count with an inline conditional"
    )


# --------------------------------------------------------------------
# The composition.
# --------------------------------------------------------------------


def test_each_step_region_holds_one_panel_at_the_content_width():
    """Every step region holds one panel carrying
    wizard-content-width, which is the box the step's own content is
    laid out inside. It is the half
    tests/test_gui_header_tabs.py::test_the_header_band_and_every_content_column_share_one_width_class
    cannot read: that guard credits a card standing inside a split, and
    this one holds that the split's own panel is at the content width
    (DL-218).

    Mutation: the preview region's panel was given
    'w-full gap-4' with its wizard-content-width removed. Observed:
        E       AssertionError: step regions whose panel carries no content width: [2]
        E       assert [2] == []
        E
        E         Left contains one more item: 2
        E         Use -v to get more diff
    """
    adrift = []
    for node in ast.walk(_page_tree()):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            target = item.context_expr
            if not (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == "regions"
            ):
                continue
            step = ast.get_source_segment(_source(), target.slice) or ""
            number = getattr(reconstruct_steps, step.rsplit(".", 1)[-1], step)
            panels = [
                text
                for text in _classes_in(node)
                if "wizard-content-width" in text.split()
            ]
            if not panels:
                adrift.append(number)
    assert adrift == [], f"step regions whose panel carries no content width: {adrift}"


def test_both_steps_compose_two_columns_inside_one_split():
    """Preview.dc.html:27 and Write.dc.html:27 draw main as a content
    column beside a rail, and each step composes that as one
    wizard-step-split holding two wizard-step-column boxes. Two columns,
    because a split whose second column is never built is a one-column
    screen carrying a two-column rule.

    Mutation: the write step's second wizard-step-column was renamed
    wizard-step-columns. Observed:
        E           AssertionError: _render_write draws 1 columns in 1 splits
        E           assert 1 == 2
        E            +  where 1 = len(['wizard-step-column'])
    """
    for name in ("_render_preview_run", "_render_write"):
        classes = _classes_in(_named_function(name))
        splits = [text for text in classes if "wizard-step-split" in text.split()]
        columns = [text for text in classes if "wizard-step-column" in text.split()]
        assert len(splits) == 1, f"{name} draws {len(splits)} splits"
        assert len(columns) == 2, (
            f"{name} draws {len(columns)} columns in {len(splits)} splits"
        )


def test_the_write_is_asked_before_it_is_made_and_the_asking_closes_with_it():
    """Write.dc.html:161-172 draws the write behind a confirmation: the
    footer control opens it and the control inside it writes. The write
    closes the dialog it was asked through, so a write that reported its
    outcome does not leave the question standing over the report.

    The footer's own control opens rather than writes, which is what
    makes the confirmation a gate rather than a notice.

    Mutation: `write_dialog.close()` was removed from write_output's
    first line. Observed:
        E       AssertionError: the write does not close the dialog it was asked through
        E       assert 'write_dialog.close()' in 'async def write_output() -> None:[...]'
    """
    page = ast.get_source_segment(_source(), _page_tree()) or ""
    footer = [
        call
        for call in ast.walk(_page_tree())
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "button"
        and call.args
        and isinstance(call.args[0], ast.Constant)
        and str(call.args[0].value).startswith("Write collection")
    ]
    handlers = {
        ast.get_source_segment(_source(), keyword.value)
        for call in footer
        for keyword in call.keywords
        if keyword.arg == "on_click"
    }
    # One control opens the dialog and writes nothing; the other writes.
    # Read as that property rather than as two exact strings: the opener
    # also redraws the step, so that the dialog states what the write
    # will do to the path as it stands now (DL-241).
    assert len(handlers) == 2, handlers
    opener = {h for h in handlers if "write_dialog.open" in h}
    assert len(opener) == 1, handlers
    assert "write_output" not in opener.pop(), (
        "the footer control writes instead of asking first"
    )
    assert "write_output" in handlers, handlers
    write = ast.get_source_segment(_source(), _named_function("write_output")) or ""
    assert "write_dialog.close()" in write, (
        "the write does not close the dialog it was asked through"
    )
    assert page.count("ui.dialog()") == 1, "the confirmation is built more than once"


def test_both_reporting_steps_are_redrawn_on_the_way_in():
    """What the preview and the write steps say is answered by controls
    on the steps beside them - the answers given at resolve, the output
    path named at set up - so each panel is drawn on entry to its step
    rather than once at composition. A panel drawn once states the run as
    it stood before those answers were given, which is how a preview
    saying six tracks have to be decided stands over a resolve step where
    every one has an answer (DL-219).

    Mutation: the `if number == reconstruct_steps.PREVIEW:
    _render_preview()` branch was removed from show_step. Observed:
        E           AssertionError: show_step draws no panel for step 2
        E           assert '_render_preview()' in 'def show_step(number: int) -> None:[...]'
    """
    show_step = ast.get_source_segment(_source(), _named_function("show_step")) or ""
    for step, render in (
        (reconstruct_steps.PREVIEW, "_render_preview()"),
        (reconstruct_steps.WRITE, "_render_write()"),
    ):
        assert render in show_step, f"show_step draws no panel for step {step}"
    assert "reconstruct_steps.PREVIEW" in show_step
    assert "reconstruct_steps.WRITE" in show_step


def test_a_run_is_stale_where_it_reports_answers_other_than_the_ones_given():
    """A held run reports the answers it was handed. Comparing that
    mapping with the answers now given is what tells a current run from
    one assembled before an answer was made or changed, and a decision
    made and undone back to where it started leaves the run current
    (DL-225).

    Mutation: `return used == decisions.resolutions(groups)` was changed
    to `return used is not None`. Observed:
        E       AssertionError: a run assembled before the answer was given reads current
        E       assert not True
        E        +  where True = <function run_is_current at [...]>({}, <traktor_nml.gui.conflict_model.ConflictDecisions object at [...]>, [ConflictGroup(identity_key='one', [...])])
        E        +    where <function run_is_current at [...]> = conflict_model.run_is_current
    """
    groups = [_group("one", "A", "B"), _group("two", "A", "B")]
    decisions = conflict_model.ConflictDecisions()
    # The run that refused: it was handed nothing, because nothing was
    # decided when it ran.
    used = decisions.resolutions(groups)
    assert conflict_model.run_is_current(used, decisions, groups)
    decisions.resolve(
        groups[0], conflict_model.candidate_reference(groups[0].candidates[1])
    )
    assert not conflict_model.run_is_current(used, decisions, groups), (
        "a run assembled before the answer was given reads current"
    )
    # Undone back to where it started, the same run reports the answers
    # now given again.
    decisions.reset(groups[0].identity_key)
    assert conflict_model.run_is_current(used, decisions, groups)


def test_a_refused_run_is_told_from_one_that_assembled():
    """A run that refused is a held result carrying no output, and the
    page asks conflict_model rather than testing `result.output is None`
    itself - the test DL-111 keeps out of the view because it reads a run
    that aborted and a run that never happened as the same thing.

    Mutation: `return result is not None and result.output is not None`
    was changed to `return result is not None`. Observed:
        E       AssertionError: a run that produced no output reads assembled
        E       assert not True
        E        +  where True = <function run_assembled at [...]>(<tests.test_gui_preview_and_write_composition.[...]._Run object at [...]>)
        E        +    where <function run_assembled at [...]> = conflict_model.run_assembled
    """

    class _Run:
        def __init__(self, output):
            self.output = output

    assert not conflict_model.run_assembled(None)
    assert not conflict_model.run_assembled(_Run(None)), (
        "a run that produced no output reads assembled"
    )
    assert conflict_model.run_assembled(_Run("<NML/>"))


def test_the_walk_to_the_write_step_re_assembles_a_stale_run():
    """The write step reports a run, so the walk into it re-assembles
    where the held run reports something other than the answers now
    given. Without it the operator answers every conflict and the step
    still reports the run that refused before they started (DL-224,
    DL-225).

    Mutation: the `await assemble()` branch was removed from advance_to,
    which takes the step's own name out of the walk with it. Observed:
        E       assert 'reconstruct_steps.WRITE' in 'gate = conflict_model.resolve_gate(decisions, conflict_holder)\nresult = result_holder["result"]\nif not reconstruct_[...]show_step(number)'
    """
    advance = _body_source_of("advance_to")
    assert "reconstruct_steps.WRITE" in advance
    assert "assemble()" in advance, (
        "the walk to the write step never re-assembles"
    )
    assert "run_is_stale()" in advance, (
        "the walk re-assembles without asking whether the run is stale"
    )
    # The staleness rule is the model's, not a second reading here.
    stale = _body_source_of("run_is_stale")
    assert "conflict_model.run_assembled" in stale
    assert "conflict_model.run_is_current" in stale


def test_the_refusal_state_is_composed_rather_than_printed():
    """A run that assembled nothing is the state most runs reach first,
    so it is a card that says what stopped the run and which step settles
    it, not a line of text over an empty page (DL-226).

    Mutation: the wizard-card section was removed from
    _render_preview_refusal, leaving its labels drawn straight into the
    panel. Observed:
        E       AssertionError: the refusal draws no card
        E       assert False
        E        +  where False = any(<generator object test_the_refusal_state_is_composed_rather_than_printed.<locals>.<genexpr> at [...]>)
    """
    classes = _classes_in(_named_function("_render_preview_refusal"))
    assert any("wizard-card" in text.split() for text in classes), (
        "the refusal draws no card"
    )
    assert any("wizard-card-body" in text.split() for text in classes)
    body = _body_source_of("_render_preview_refusal")
    assert "reconstruct_report.preview_refusal" in body, (
        "the refusal writes its own sentence rather than reading the record's"
    )
    assert "record.sentence" in body and "record.title" in body


def test_the_refusal_names_the_step_that_settles_it():
    """The sentence a conflict refusal prints names the count the run
    reported and the step that answers it, because the refusal is a
    question rather than a failure. A run stopped by anything else reads
    as what it is, and its reasons stand under it in the tokens the run
    gave them - with the conflict token dropped, since the sentence
    already stands in its place (DL-226).

    Mutation: `if not self.conflicts` was changed to `if self.conflicts`
    in PreviewRefusal.sentence. Observed:
        E       AssertionError: The run stopped on what it read. Nothing was written, and the reasons it gave are below.
        E       assert 'Continue to resolve' in 'The run stopped on what it read. Nothing was written, and the reasons it gave are below.'
        E        +  where 'The run stopped on what it read. Nothing was written, and the reasons it gave are below.' = PreviewRefusal(conflicts=2, reasons=()).sentence
    """
    groups = [_group("one", "A", "B"), _group("two", "A", "B")]
    conflicts = reconstruct_report.preview_refusal(
        [conflict_model.CONFLICT_ABORT_TOKEN], groups, _stats(), (), ()
    )
    assert "Continue to resolve" in conflicts.sentence, conflicts.sentence
    assert conflicts.sentence.startswith("2 tracks are")
    assert conflicts.reasons == (), (
        "the conflict token stands beside the sentence that replaces it"
    )
    assert not conflicts.has_reasons
    other = reconstruct_report.preview_refusal(
        ["ambiguous_playlist_name x"], [], _stats(), (), ()
    )
    assert other.reasons == ("ambiguous_playlist_name x",)
    assert other.title == "The repair could not be assembled"


def test_the_refusal_names_the_control_as_a_button():
    """`Continue to resolve` is a verb phrase, so the refusal sentence
    has to introduce it as the name of a button rather than let it stand
    as a clause of its own: read as a clause it tells the operator to
    continue, and the words after it ("names each one and offers its
    answers") then have no subject.

    The guard above cannot catch that - it asks only that the control's
    name appear somewhere in the sentence, which is true of both the
    broken wording and the fixed one, so it is green in exactly the
    broken state (DL-189).

    Mutation: the sentence was returned to `Continue to resolve names
    each one and offers its answers.` Observed:
        E       AssertionError: 2 tracks are held differently by more than one collection, and the repair cannot be assembled until every one has an answer. Continue to resolve names each one and offers its answers.
        E       assert 'The Continue to resolve button' in '2 tracks are held differently by more than one collection, and the repair cannot be assembled until every one has an answer. Continue to resolve names each one and offers its answers.'
        E        +  where '2 tracks are held differently by more than one collection, and the repair cannot be assembled until every one has an answer. Continue to resolve names each one and offers its answers.' = PreviewRefusal(conflicts=2, reasons=(), settled=0, outliers=(), outlier_remainder=None, outlier_total=0).sentence
    """
    groups = [_group("one", "A", "B"), _group("two", "A", "B")]
    conflicts = reconstruct_report.preview_refusal(
        [conflict_model.CONFLICT_ABORT_TOKEN], groups, _stats(), (), ()
    )
    assert "The Continue to resolve button" in conflicts.sentence, (
        conflicts.sentence
    )


def test_the_write_step_reports_the_entries_placed_on_a_duplicated_track():
    """An entry whose track the collection holds more than once is placed
    on the first of those copies rather than dropped or refused, and the
    write step says how many landed that way and across how many
    playlists. Placed silently, it would be the one thing the file holds
    that the step describing the file does not mention (DL-230).

    A run with none of them draws no row: a row reading zero names a
    thing the run did not do.

    Mutation: the `if on_duplicated:` guard was removed, so the row was
    appended for every run. Observed:
        E       AssertionError: a run with none of them draws the row anyway
        E       assert 5 == 4
        E        +  where 5 = len((ChangeRow(label='Playlists filled again', [...], count=0, tone='untouched')))
        E        +    where (ChangeRow(label='Playlists filled again', [...])) = WriteReport(destination='out.nml', [...]).rows
    """
    plain = reconstruct_report.write_report(
        _stats(), [], conflict_model.ConflictDecisions(), "out.nml", False, []
    )
    assert len(plain.rows) == 4, "a run with none of them draws the row anyway"

    reported = reconstruct_report.write_report(
        _stats(
            entries_on_duplicated_tracks=369,
            playlists_on_duplicated_tracks={"a": 300, "b": 69},
        ),
        [], conflict_model.ConflictDecisions(), "out.nml", False, [],
    )
    assert len(reported.rows) == 5
    row = reported.rows[4]
    assert row.count == 369
    assert "2 playlists" in row.detail, row.detail
    assert row.tone == reconstruct_report.TONE_UNTOUCHED
    # The first row still carries the count the confirmation names, so the
    # extra row cannot displace it.
    assert reported.confirm_question == "Write 0 rebuilt playlists?"


def test_the_write_step_reports_the_entries_dropped_for_a_missing_track():
    """An entry naming a track no collection this run read holds is
    dropped from the playlist carrying it, and the write step says how
    many entries went, how many distinct tracks they named, and across
    how many playlists. Dropped silently, it would be the one way the
    written playlists differ from the ones they were rebuilt from that
    the step describing them does not mention (DL-232).

    A run with none of them draws no row.

    Mutation: the `if dropped:` guard was replaced by `if True:`, so
    the row was appended for every run. Observed:
        E       AssertionError: a run with none of them draws the row anyway
        E       assert 5 == 4
        E        +  where 5 = len((ChangeRow(label='Playlists filled again', [...], count=0, tone='untouched')))
    """
    plain = reconstruct_report.write_report(
        _stats(), [], conflict_model.ConflictDecisions(), "out.nml", False, []
    )
    assert len(plain.rows) == 4, "a run with none of them draws the row anyway"

    reported = reconstruct_report.write_report(
        _stats(
            entries_dropped_unresolvable=21,
            tracks_dropped_unresolvable=8,
            playlists_with_dropped_entries={"a": 20, "b": 1},
        ),
        [], conflict_model.ConflictDecisions(), "out.nml", False, [],
    )
    assert len(reported.rows) == 5
    row = reported.rows[4]
    assert row.count == 21
    assert row.detail.startswith("8 tracks across 2 playlists."), row.detail
    assert row.tone == reconstruct_report.TONE_UNTOUCHED

    one = reconstruct_report.write_report(
        _stats(
            entries_dropped_unresolvable=1,
            tracks_dropped_unresolvable=1,
            playlists_with_dropped_entries={"a": 1},
        ),
        [], conflict_model.ConflictDecisions(), "out.nml", False, [],
    )
    assert one.rows[4].detail.startswith("1 track across 1 playlist."), one.rows[4].detail


def test_the_write_step_describes_the_file_once_it_exists():
    """A confirmed write leaves the step describing a file that now
    exists, so its head, its status and the tense of its change list say
    so. Everything else on the card stands: the change list described the
    file and now describes it, the originals are still unmodified, and
    the note about opening it in Traktor is the next thing to do
    (DL-240).

    Mutation: the three properties reduced to their pre-write
    branch - `head_title` to `"Before anything is written"`, `head_badge`
    to `"Nothing written yet"`, `contents_title` to `"What the new file
    will hold"`. Observed:
        E       AssertionError: assert 'Before anything is written' == 'Written'
        E         - Written
        E         + Before anything is written
    """
    before = reconstruct_report.write_report(
        _stats(), [], conflict_model.ConflictDecisions(), "out.nml", False, []
    )
    assert before.head_title == "Before anything is written"
    assert before.head_badge == "Nothing written yet"
    assert before.destination_badge == "Does not exist yet"
    assert before.contents_title == "What the new file will hold"

    after = reconstruct_report.write_report(
        _stats(), [], conflict_model.ConflictDecisions(), "out.nml", True, [],
        written=True,
    )
    assert after.head_title == "Written"
    assert after.head_badge == "Written"
    assert after.destination_badge == "Written"
    assert after.contents_title == "What the new file holds"
    # The list itself is the same list: a write changes the tense of the
    # sentence above it, not what the run did.
    assert [row.label for row in after.rows] == [row.label for row in before.rows]
    # The question does change, and should: writing again to a path this
    # run has already written replaces the file that is now there, which
    # is what the dialog has to say (DL-241).
    assert before.confirm_question == "Write 0 rebuilt playlists?"
    assert after.confirm_question.startswith("Replace the file at that path")


def test_a_path_that_exists_but_this_run_did_not_write_is_not_called_written():
    """`destination_exists` and `written` are different facts: a path the
    operator points at a file somebody else left there already exists and
    has not been written by this run, and the badge that warns them it
    will be replaced is the one they need (DL-240).

    Mutation: `if self.written:` in destination_badge widened to
    `if self.written or self.destination_exists:`. Observed:
        E       AssertionError: assert 'Written' == 'Already exists'
        E         - Already exists
        E         + Written
    """
    existing = reconstruct_report.write_report(
        _stats(), [], conflict_model.ConflictDecisions(), "out.nml", True, []
    )
    assert existing.written is False
    assert existing.destination_badge == "Already exists"
    assert existing.head_badge == "Nothing written yet"


def test_the_write_redraws_the_step_and_a_new_run_puts_it_back():
    """The step describes the file, so the handler that writes the file
    redraws the step; and a run assembled afterwards produces bytes the
    file on disk does not hold, so it clears the written path and the
    step is before its write again (DL-240).

    Read as source text: what the browser paints from this is a
    served-page reading (DL-189).

    Mutation: the `_render_write()` call between the write and its
    toast deleted, which is the state DL-234 recorded. Observed:
        E       AssertionError: the step that describes the file is not redrawn when the file appears
        E       assert '_render_write()' in 'write_dialog.close()[...]written_holder["path"] = str(output_path)
ui.notify(f"Written to {output_path}", type="positive")'

    And separately, `written_holder["path"] = None` deleted from
    assemble. Observed:
        E       AssertionError: a new run leaves the step claiming a file it did not write
        E       assert 'written_holder["path"] = None' in 'loaded = await run.io_bound(_load)[...]result_holder["resolutions"] = resolutions
_render_resolve()
return True'
    """
    confirm = _body_source_of("write_output")
    assert 'written_holder["path"] = str(output_path)' in confirm, (
        "the write does not record the path it wrote"
    )
    assert "_render_write()" in confirm, (
        "the step that describes the file is not redrawn when the file appears"
    )
    # Redrawn before the toast that names the file. Anchored to that
    # toast rather than to the first `ui.notify` in the function, which
    # belongs to a refusal branch that returns before any write.
    written_toast = confirm.index('ui.notify(f"Written to')
    assert confirm.index("_render_write()") < written_toast, confirm

    assembled = _body_source_of("assemble")
    assert 'written_holder["path"] = None' in assembled, (
        "a new run leaves the step claiming a file it did not write"
    )

    # The panel reads the two together: a path the operator edited names a
    # file this run did not write.
    render = _body_source_of("_render_write")
    assert 'written_holder["path"] == destination' in render, render


def test_a_write_over_an_existing_file_says_so_before_it_asks():
    """The write replaces whatever stands at the output path, so on a
    path already holding a file the confirmation says what it is about
    to destroy and its control names the act.

    A confirmation that misstates what it destroys is worse than none:
    it spends the operator's attention reassuring them. "A new file is
    created at the path above" was read by an operator over a file the
    run then replaced (DL-241).

    PLACEHOLDER-R1
    """
    fresh = reconstruct_report.write_report(
        _stats(), [], conflict_model.ConflictDecisions(), "out.nml", False, []
    )
    assert fresh.confirm_action == "Write collection"
    assert fresh.confirm_assurances[0] == "A new file is created at the path above."
    assert fresh.destination_note.startswith("The write refuses any path")

    over = reconstruct_report.write_report(
        _stats(), [], conflict_model.ConflictDecisions(), "out.nml", True, []
    )
    assert over.confirm_action == "Replace file"
    assert "replaced" in over.confirm_assurances[0], over.confirm_assurances[0]
    assert "not recoverable" in over.confirm_assurances[0], over.confirm_assurances[0]
    assert over.confirm_question.startswith("Replace the file at that path")
    assert over.destination_note.startswith("A file already stands here")
    # The other two lines hold either way: they are about the run's own
    # inputs and about Traktor, neither of which the path changes.
    assert fresh.confirm_assurances[1:] == over.confirm_assurances[1:]


def test_the_dialog_is_filled_from_the_record_rather_than_built_once():
    """What the write will do to the path depends on what stands there
    now, so the dialog's lines and its control are set where the panel is
    drawn, and the footer control redraws before opening it (DL-241).

    Read as source text: what the browser paints is a served-page
    reading (DL-189).

    PLACEHOLDER-R2
    """
    render = _body_source_of("_render_write")
    assert 'write_holder["confirm"].set_text(record.confirm_action)' in render, render
    assert "record.confirm_assurances" in render, render
    assert "record.destination_note" in _source(), (
        "the step's note under the path is still a literal"
    )
def _real_settled(artist, title):
    """One splice.SettledRow, built the way splice._settled_row builds it,
    so the record half is read against the run's own row rather than a
    stand-in shaped like it."""
    return splice.SettledRow(
        "C:/:Music/:one.mp3",
        ("filesize",),
        (("filesize", ("17564", "69203")),),
        (0, "C:/:Music/:one.mp3"),
        artist,
        title,
        outliers=(
            metadata_tier.OutlierReading(
                attr="filesize", kept="69203", other="17564", relative_gap=0.7462
            ),
        ),
    )


def test_the_listed_track_is_read_off_the_run_s_own_settled_row():
    """The stand-ins above carry an artist and a title because the row the
    run hands the record does, and a guard reading only stand-ins is green
    on a run whose rows carry neither. This one composes the record from a
    splice.SettledRow itself, so the two halves are read against one
    shape (DL-071, DL-189).

    Mutation: the `artist: str` and `title: str` fields dropped from
    splice.SettledRow and the two arguments dropped from _settled_row's
    construction of it.
    Observed:
        E       TypeError: SettledRow.__init__() got multiple values for argument 'outliers'
    """
    named = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=1),
        (),
        conflict_model.ConflictDecisions(),
        (_real_settled("Drexciya", "Andreaen Sand Dunes"),),
        _LABELS,
    )
    assert named.outliers[0].track == "Drexciya - Andreaen Sand Dunes"


def test_one_editorial_name_alone_reads_as_itself_and_neither_as_the_path():
    """A record carrying one of the two names reads as that name: the
    identity key is the reading for a row that names no track at all, and
    a row naming half of one still names something a person recognises.

    Mutation: `if artist and title:` in _track_reading relaxed to `if
    artist or title:`, so a row carrying one name was joined to an empty
    other.
    Observed:
        E       AssertionError: assert ' - Andreaen Sand Dunes' == 'Andreaen Sand Dunes'
        E
        E         - Andreaen Sand Dunes
        E         +  - Andreaen Sand Dunes
        E         ? +++
    """
    def track_of(artist, title):
        record = reconstruct_report.preview_report(
            _stats(groups_settled_by_rule=1),
            (),
            conflict_model.ConflictDecisions(),
            (_real_settled(artist, title),),
            _LABELS,
        )
        return record.outliers[0].track

    assert track_of("", "Andreaen Sand Dunes") == "Andreaen Sand Dunes"
    assert track_of("Drexciya", "") == "Drexciya"
    # The path stands only where the row names neither.
    assert track_of("", "") == "C:/:Music/:one.mp3"
    assert track_of("  ", "  ") == "C:/:Music/:one.mp3"


def test_the_composition_places_the_settled_reading_off_the_record():
    """Preview.dc.html:164's .note info and :192's .ol: the preview places
    the settled sentence beside the conflict note and each listed gap as a
    hand-rolled row, and every cell of both is a string the record already
    composed. A number formatted at this call site could disagree with the
    sentence above it, which is the thing DL-215 and DL-331 exist to stop.

    The record is asked for the run's own settled rows and for the labels
    the page holds for its inputs, so the winner cell names a collection
    the way the resolve rail's contributor chips do (DL-148, DL-150).

    Read as source text and as an AST: what the browser paints is a
    served-page reading (DL-189).

    Mutation: outlier_row's gap cell written as
    `ui.label(f"{row.relative_gap * 100:.1f}%")`. Observed:
        E       AssertionError: ['row.track', 'row.label', 'row.spread', 'row.winner', 'f"{row.relative_gap * 100:.1f}%"']
        E       assert ['row.track',...* 100:.1f}%"'] == ['row.track',...w.gap_amount']
        E
        E         At index 4 diff: 'f"{row.relative_gap * 100:.1f}%"' != 'row.gap_amount'
        E         Use -v to get more diff
        tests\\test_gui_preview_and_write_composition.py:1144: AssertionError
    """
    preview = _body_source_of("_render_preview_run")
    # The record is composed from the run's settled rows and the page's
    # own collection labels, not from a second reading of the result, and
    # that composition is made once for every step 2 screen that reads it.
    composed = _body_source_of("_preview_record")
    assert "result.settled_rows" in composed, composed
    assert "_collection_labels(source_holder)" in composed, composed
    assert "_preview_record()" in preview, preview
    # The sentence stands in its own info panel beside the warn one, and
    # a run the rule settled nothing for places neither.
    note = _body_source_of("settled_note")
    assert "if not record.settled_sentence:" in note, note
    assert "wizard-callout wizard-callout-info" in _classes_in(
        _named_function("settled_note")
    ), note
    # The card is the count: a run with no outlier draws no card.
    assert "if record.outliers:" in preview, preview
    assert "record.outlier_title" in preview, preview
    rows = _body_source_of("outlier_rows")
    for read in ("record.outlier_note", "outlier_row(row)"):
        assert read in rows, read
    # Every cell is the record's own string, and nothing is formatted here.
    row = _named_function("outlier_row")
    cells = [
        ast.get_source_segment(_source(), call.args[0])
        for call in ast.walk(row)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "label"
        and call.args
    ]
    assert cells == [
        "row.track",
        "row.label",
        "row.spread",
        "row.winner",
        "row.gap_amount",
    ], cells
    formatted = [
        cell
        for cell in cells
        if cell is None or "f\"" in cell or ".format(" in cell or "%" in cell
    ]
    assert formatted == [], (
        "outlier_row formats a value instead of placing the record's own"
    )

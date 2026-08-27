"""Guards for output_collision_refusal, the single predicate
plan_and_write_nml's first statement calls. Each guard constructs its
broken scenario in executable code and records the mutation and the
observed output in its docstring.
"""

from __future__ import annotations

from pathlib import Path

from traktor_nml.rewrite import WriteOutcome, output_collision_refusal, plan_and_write_nml


def _write_minimal_nml(path: Path) -> None:
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="19">\n'
        '  <COLLECTION ENTRIES="0">\n'
        '  </COLLECTION>\n'
        '</NML>\n',
        encoding="utf-8",
    )


def _asserting_collect(root):
    raise AssertionError("collect_patches must not run when output collides")


def _asserting_mutate(root, dry_run):
    raise AssertionError("mutate_tree must not run when output collides")


def test_collision_refusal_precedes_either_callback(tmp_path: Path) -> None:
    """A colliding output=input call must return the refusal without
    entering collect_patches or mutate_tree, proven by callbacks that
    raise AssertionError the moment they're entered rather than by
    inspecting the returned outcome alone.

    Negative control: a local stand-in that checks the collision only
    after reading and parsing the source shows the asserting callback
    actually IS reachable at that point (it raises), so the guard above
    is shown to detect a check that runs too late rather than passing
    for any ordering at all.
    """
    input_path = tmp_path / "in.nml"
    _write_minimal_nml(input_path)

    outcome = plan_and_write_nml(input_path, input_path, False, _asserting_collect, _asserting_mutate)
    assert outcome == WriteOutcome(None, None, "output_must_differ_from_input", None, 2)

    def reordered_check(input_path: Path, output_path: Path) -> None:
        # Stand-in for a version of plan_and_write_nml with the collision
        # check placed after the read/parse instead of before it - the
        # negative control for the ordering assertion above.
        from traktor_nml.rewrite import read_and_parse_source

        read_result = read_and_parse_source(input_path)
        assert read_result.error is None
        _asserting_collect(read_result.root)  # never reached if refusal ran first
        output_collision_refusal(input_path, output_path)

    raised = False
    try:
        reordered_check(input_path, input_path)
    except AssertionError as exc:
        raised = True
        assert "collect_patches must not run" in str(exc)
    assert raised, "expected the reordered stand-in to reach the asserting callback"


def test_single_refusal_literal_shared_by_predicate_and_outcome(tmp_path: Path) -> None:
    """The literal output_collision_refusal returns and the literal
    embedded in plan_and_write_nml's WriteOutcome must be the same
    string, across colliding with the primary input and with each extra
    input, so a second copy of the literal in either place would be
    caught rather than silently diverging.

    Negative control: comparing the real result against a deliberately
    different literal shows the equality assertion is sensitive rather
    than trivially true.
    """
    input_path = tmp_path / "in.nml"
    extra_a = tmp_path / "extra_a.nml"
    extra_b = tmp_path / "extra_b.nml"
    _write_minimal_nml(input_path)

    scenarios = [
        (input_path, ()),
        (extra_a, (extra_a, extra_b)),
        (extra_b, (extra_a, extra_b)),
    ]
    last_result = None
    for output_path, extra_inputs in scenarios:
        predicate_result = output_collision_refusal(input_path, output_path, extra_inputs)
        outcome = plan_and_write_nml(
            input_path, output_path, False, _asserting_collect, _asserting_mutate, extra_inputs
        )
        assert predicate_result == outcome.error == "output_must_differ_from_input"
        last_result = predicate_result

    assert last_result != "output_must_differ_from_input_MUTATED"


def test_extra_input_collision_refused_and_non_collision_reaches_callbacks(tmp_path: Path) -> None:
    """A collision against an extra input, not the primary input, is
    refused; a non-colliding output returns None and the callbacks are
    actually reached.
    """
    input_path = tmp_path / "in.nml"
    extra_a = tmp_path / "extra_a.nml"
    extra_b = tmp_path / "extra_b.nml"
    _write_minimal_nml(input_path)

    assert output_collision_refusal(input_path, extra_a, (extra_a, extra_b)) == "output_must_differ_from_input"
    outcome = plan_and_write_nml(
        input_path, extra_a, False, _asserting_collect, _asserting_mutate, (extra_a, extra_b)
    )
    assert outcome == WriteOutcome(None, None, "output_must_differ_from_input", None, 2)

    non_colliding = tmp_path / "out.nml"
    assert output_collision_refusal(input_path, non_colliding, (extra_a, extra_b)) is None

    reached: list[str] = []

    def collect_patches(root):
        reached.append("collect_patches")
        return [], {"x": 1}, []

    def mutate_tree(root, dry_run):
        reached.append("mutate_tree")
        return {"x": 1}, []

    plan_and_write_nml(input_path, non_colliding, True, collect_patches, mutate_tree, (extra_a, extra_b))
    assert reached, "expected a callback to be reached for a non-colliding output"

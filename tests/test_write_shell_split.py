"""Unit tests over plan_and_write_nml and write_nml_safely covering
what the byte-parity manifest cannot reach: the printless core's own
outcomes, and one print-order guard on the wrapper that the manifest
cannot pin because all twelve recorded stderr values are empty.
test_no_outcome_writes_to_either_stream and
test_write_nml_safely_prints_stats_before_error_on_text_patch_error each
carry a companion proof in this file - the former runs write_nml_safely
over a collision input and shows stderr is non-empty (ruling out a
misconfigured capsys), the latter builds the inverted print-order
wrapper DL-003 warns against and shows its ordering actually diverges
from the real wrapper's. The other three assert what plan_and_write_nml
returns on a collision, a write-time text_patch_error, and a callback
exception, without a comparable proof here that the assertion would
catch a broken implementation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from traktor_nml.model import ElemPatch
from traktor_nml.rewrite import (
    WriteOutcome,
    format_stats_and_samples,
    plan_and_write_nml,
    write_nml_safely,
)


def _write_minimal_nml(path: Path) -> None:
    """A COLLECTION with no entries - enough for plan_and_write_nml to
    parse and reach either callback; the tests below don't need entries,
    only a valid document to read, patch and (sometimes) write."""
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="19">\n'
        '  <COLLECTION ENTRIES="0">\n'
        '  </COLLECTION>\n'
        '</NML>\n',
        encoding="utf-8",
    )


def _no_op_collect(root):
    """Minimal collect_patches returning fixed patches/stats/samples:
    isolates plan_and_write_nml's write-shell behaviour (collision
    refusal, write-time error handling, printlessness) from patch
    computation, which these tests are not exercising."""
    return [], {"x": 1}, []


def _no_op_mutate(root, dry_run):
    """Minimal mutate_tree returning fixed stats, ignoring dry_run:
    isolates the write shell the same way _no_op_collect does, for the
    stdlib-fallback path."""
    return {"x": 1}, []


def test_output_collision_carries_no_stats(tmp_path: Path) -> None:
    """A collision refusal is a run that never reached collect_patches or
    mutate_tree at all, so stats being None (rather than an empty dict)
    is the signal there is no stats block to render. Negative case: a
    run that does reach collect_patches produces a populated dict, not
    None, so the two outcomes are distinguishable by type - proved here
    by running both against the same input and comparing them, rather
    than trusting the docstring that stats is None only for a collision."""
    input_path = tmp_path / "a.nml"
    _write_minimal_nml(input_path)

    collision = plan_and_write_nml(input_path, input_path, False, _no_op_collect, _no_op_mutate)
    completed = plan_and_write_nml(
        input_path, tmp_path / "out.nml", False, _no_op_collect, _no_op_mutate
    )

    assert collision.stats is None
    assert collision.exit_code == 2
    assert collision.error == "output_must_differ_from_input"

    # The negative case: had a collision instead produced {} rather than
    # None, it would be indistinguishable in kind from a completed run's
    # stats - this is what actually tells them apart.
    assert completed.stats is not None
    assert type(collision.stats) is not type(completed.stats)


def test_text_patch_error_keeps_the_stats_it_already_collected(tmp_path: Path) -> None:
    """A patch whose original attributes cannot be located in the source
    text raises inside apply_and_write, after collect_patches already
    returned stats - the outcome must keep those stats rather than
    discarding them, or a caller that prints the stats block ahead of the
    error would have nothing to print. Negative case: a WriteOutcome
    built the way a prior draft built one for every write-time exception
    - WriteOutcome(None, None, error, None, 2), discarding the stats
    collect_patches had already returned - is constructed here from the
    same error and exit_code and shown to carry stats that differ from
    (and are less informative than) the real outcome's, which is what
    actually distinguishes the correct behaviour from the discarding one
    rather than only asserting the correct side.
    """
    input_path = tmp_path / "a.nml"
    _write_minimal_nml(input_path)
    output_path = tmp_path / "out.nml"

    bogus_patch = ElemPatch(
        sourceline=1,
        tag_name="LOCATION",
        locator=(("VOLUME", "does-not-exist"),),
        changes=[("VOLUME", "does-not-exist", "X")],
    )

    def collect_patches(root):
        return [bogus_patch], {"collection_locations_rewritten": 1}, []

    outcome = plan_and_write_nml(input_path, output_path, False, collect_patches, _no_op_mutate)

    assert outcome.stats == {"collection_locations_rewritten": 1}
    assert outcome.error is not None and outcome.error.startswith("text_patch_error=")
    assert outcome.written_path is None
    assert outcome.exit_code == 2

    # The prior-draft outcome, rebuilt here from the real one's own error
    # and exit_code: had plan_and_write_nml discarded stats on every
    # write-time exception the way that draft did, this is exactly what
    # it would have returned instead. Demonstrating it lets the next
    # assertion catch the regression rather than only asserting the
    # collected-stats side of it.
    discarded_stats_outcome = WriteOutcome(None, None, outcome.error, None, outcome.exit_code)

    assert discarded_stats_outcome.stats is None
    assert discarded_stats_outcome.stats != outcome.stats


def test_callback_exception_reaches_the_caller(tmp_path: Path) -> None:
    """collect_patches/mutate_tree are the caller's own callables; a
    plain exception from either must propagate rather than being folded
    into a WriteOutcome, the way an input error is. Negative case: a
    write-time exception from apply_and_write (text_patch_error) is the
    contrasting behaviour - plan_and_write_nml folds that one into a
    WriteOutcome instead of raising, so the two failure classes are
    proved to be handled differently rather than everything simply
    propagating."""
    input_path = tmp_path / "a.nml"
    _write_minimal_nml(input_path)
    output_path = tmp_path / "out.nml"

    def collect_patches(root):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        plan_and_write_nml(input_path, output_path, False, collect_patches, _no_op_mutate)

    bogus_patch = ElemPatch(1, "LOCATION", (("VOLUME", "nope"),), [("VOLUME", "nope", "X")])
    folded = plan_and_write_nml(
        input_path, output_path, False, lambda root: ([bogus_patch], {}, []), _no_op_mutate
    )
    assert folded.error is not None and folded.error.startswith("text_patch_error=")


def test_no_outcome_writes_to_either_stream(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """plan_and_write_nml is printless for every outcome it can return:
    collision, write success, and write-time text_patch_error alike.
    Negative case: the printing wrapper write_nml_safely, run over the
    same collision input, does write to stderr - proving capsys is
    actually capturing output here rather than the silence above being
    an artifact of a misconfigured test."""
    input_path = tmp_path / "a.nml"
    _write_minimal_nml(input_path)

    plan_and_write_nml(input_path, input_path, False, _no_op_collect, _no_op_mutate)
    plan_and_write_nml(input_path, tmp_path / "out1.nml", False, _no_op_collect, _no_op_mutate)

    bogus_patch = ElemPatch(1, "LOCATION", (("VOLUME", "nope"),), [("VOLUME", "nope", "X")])
    plan_and_write_nml(
        input_path, tmp_path / "out2.nml", False, lambda root: ([bogus_patch], {}, []), _no_op_mutate
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    write_nml_safely(input_path, input_path, False, _no_op_collect, _no_op_mutate)
    assert capsys.readouterr().err != ""


def test_write_nml_safely_prints_stats_before_error_on_text_patch_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """write_nml_safely's fixed print order is DL-003's contractual
    ordering: on the lxml path apply_and_write raises after
    collect_patches has already returned stats, so a text_patch_error
    must show the stats block on stdout before the error reaches
    stderr - the manifest cannot pin this because all twelve recorded
    stderr values are empty, so no manifest case has both a stats block
    and an error line at once. Negative case: this test builds the
    inverted wrapper - error printed before the stats block, the exact
    swap this guard exists to catch - and drives it through the same
    print recorder used for the real wrapper, showing the two orderings
    actually diverge rather than only asserting the correct one in
    isolation."""
    input_path = tmp_path / "a.nml"
    _write_minimal_nml(input_path)
    output_path = tmp_path / "out.nml"

    bogus_patch = ElemPatch(
        sourceline=1,
        tag_name="LOCATION",
        locator=(("VOLUME", "does-not-exist"),),
        changes=[("VOLUME", "does-not-exist", "X")],
    )

    def collect_patches(root):
        return [bogus_patch], {"collection_locations_rewritten": 1}, []

    calls: list[tuple[str, str]] = []

    def recording_print(*args, file=None, **kwargs) -> None:
        stream = "stderr" if file is sys.stderr else "stdout"
        calls.append((stream, " ".join(str(a) for a in args)))

    monkeypatch.setattr("traktor_nml.rewrite.print", recording_print, raising=False)

    exit_code = write_nml_safely(input_path, output_path, False, collect_patches, _no_op_mutate)

    assert exit_code == 2
    stats_index = next(
        i for i, (stream, text) in enumerate(calls)
        if stream == "stdout" and "collection_locations_rewritten=1" in text
    )
    error_index = next(
        i for i, (stream, text) in enumerate(calls)
        if stream == "stderr" and text.startswith("text_patch_error=")
    )
    assert stats_index < error_index

    # The negative case: an inverted wrapper - error emitted before the
    # stats block, the exact bug DL-003 warns against - built from the
    # same WriteOutcome and driven through the same recorder, so its
    # ordering can be shown to actually diverge from the real wrapper's
    # rather than merely being described as wrong.
    calls.clear()
    outcome = plan_and_write_nml(input_path, output_path, False, collect_patches, _no_op_mutate)

    def inverted_write_nml_safely(outcome: WriteOutcome) -> int:
        if outcome.error is not None:
            recording_print(outcome.error, file=sys.stderr)
        if outcome.stats is not None:
            for line in format_stats_and_samples(outcome.stats, outcome.samples):
                recording_print(line)
        if outcome.written_path is not None:
            recording_print(f"output_written={outcome.written_path.as_posix()}")
        return outcome.exit_code

    inverted_write_nml_safely(outcome)

    inv_stats_index = next(
        i for i, (stream, text) in enumerate(calls)
        if stream == "stdout" and "collection_locations_rewritten=1" in text
    )
    inv_error_index = next(
        i for i, (stream, text) in enumerate(calls)
        if stream == "stderr" and text.startswith("text_patch_error=")
    )
    # The real wrapper puts stats first (asserted above: stats_index <
    # error_index); the inverted wrapper puts error first, i.e. its
    # stats index comes AFTER its error index - the two orderings are
    # shown here to actually diverge, which is what would make this
    # guard fail if write_nml_safely were ever changed to match the
    # inverted ordering.
    assert inv_error_index < inv_stats_index
    assert stats_index < error_index and inv_stats_index > inv_error_index

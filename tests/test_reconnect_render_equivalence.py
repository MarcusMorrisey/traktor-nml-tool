"""Section 3.2 equivalence tests: the renderer over the printless core
must reproduce the recorded CLI output exactly, using the reconnect
cases in tests/baselines/manifest.json as the expectation rather than
restating them.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import threading
from pathlib import Path

import pytest

import argparse

from traktor_nml import reconnect_run
from traktor_nml.cli import build_parser
from traktor_nml.diskscan import ScanCancelled
from traktor_nml.reconnect_render import (
    emit,
    render_rewrite_from_reconnect,
    render_scan_reconnect_candidates,
)
from traktor_nml.reconnect_run import (
    ReconnectResult,
    RewriteReconnectResult,
    ScanReconnectResult,
)
from traktor_nml.rewrite import WriteOutcome
from traktor_nml.xmlio import parse_xml

MANIFEST_PATH = Path(__file__).parent / "baselines" / "manifest.json"


def _reconnect_cases() -> list[dict]:
    """The manifest.json cases whose argv is one of the two reconnect
    subcommands - the population section 3.2's parametrized test runs
    against. If this ever returns an empty list, pytest silently
    collects zero equivalence tests instead of failing the suite; there
    is no explicit assertion here against that, so a manifest edit
    removing both reconnect commands' cases would go unnoticed without
    someone checking collected test counts. Every case here passes
    --match-confidence filename; the manifest carries no --fingerprint
    case and no strict/normal/loose/bare_name case for either reconnect
    command, so those paths rest on the unit tests elsewhere in this
    module rather than on this parity check."""
    cases = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [c for c in cases if c["argv"][0] in ("scan-reconnect-candidates", "rewrite-from-reconnect")]


def _parse_args(argv: list[str]) -> object:
    """Parse argv through the real CLI parser, so a case's args are the
    same argparse.Namespace the CLI itself would build for it."""
    parser, _handlers = build_parser()
    return parser.parse_args(argv)


def _render_for_argv(argv: list[str], cwd: Path):
    """Run core(args) then render(result) for one manifest case, from
    cwd - manifest paths are recorded relative to the fixture corpus
    root, so the working directory must match before parsing argv."""
    args = _parse_args(argv)
    old_cwd = Path.cwd()
    os.chdir(cwd)
    try:
        if argv[0] == "scan-reconnect-candidates":
            result = reconnect_run.scan_reconnect_candidates(args)
            return render_scan_reconnect_candidates(result, args), result
        result = reconnect_run.rewrite_from_reconnect(args)
        return render_rewrite_from_reconnect(result, args), result
    finally:
        os.chdir(old_cwd)


def _lines_to_text(lines: list[str]) -> str:
    """Join rendered lines the way emit() would have printed them, for
    comparison against a manifest case's recorded stdout/stderr text.
    test_dropped_stats_key_breaks_the_comparison proves this comparison
    actually detects a dropped line rather than trivially matching
    regardless of content."""
    return "\n".join(lines) + ("\n" if lines else "")


@pytest.mark.parametrize("case", _reconnect_cases(), ids=lambda case: " ".join(case["argv"][:2]))
def test_render_matches_recorded_case(fixture_corpus: Path, case: dict) -> None:
    """render(core(args)) reproduces the recorded stdout, stderr and exit
    code for each of the four reconnect manifest cases, using the same
    fixture_corpus inputs the manifest case itself was recorded against."""
    cwd = fixture_corpus.parent
    rendered, _result = _render_for_argv(case["argv"], cwd)

    stdout = _lines_to_text(rendered.stdout_lines)
    stderr = _lines_to_text(rendered.stderr_lines)

    expected_stdout = case["stdout"]
    expected_stderr = case["stderr"]
    if case.get("normalise_run_root"):
        run_root = cwd.resolve().as_posix()
        expected_stdout = expected_stdout.replace("{RUN_ROOT}", run_root)
        expected_stderr = expected_stderr.replace("{RUN_ROOT}", run_root)

    assert stdout == expected_stdout
    assert stderr == expected_stderr
    assert rendered.exit_code == case["exit_code"]


def test_dropped_stats_key_breaks_the_comparison(fixture_corpus: Path) -> None:
    """Negative control: proves the equality assertion above actually
    detects drift rather than passing regardless of content. Observed to
    fail the assertion below when run against an unmodified renderer."""
    case = next(c for c in _reconnect_cases() if c["argv"][0] == "scan-reconnect-candidates")
    rendered, _result = _render_for_argv(case["argv"], fixture_corpus.parent)

    tampered = list(rendered.stdout_lines)
    if len(tampered) > 1:
        tampered.pop(1)

    assert _lines_to_text(tampered) != case["stdout"]


_SCAN_ARGV = [
    "scan-reconnect-candidates", "recon/stale.nml",
    "--scan-root", "recon/audio",
    "--volume-map", "recon/audio", "D:", "D:",
    "--match-confidence", "filename",
    "--cache", "out/recon.tagcache.json",
]


def test_fingerprint_warning_lands_in_result_not_printed_by_core(
    fixture_corpus: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-None fingerprint_unavailable_reason() must become a warning
    on ReconnectResult and render to stderr ahead of the refutation line,
    rather than being printed by the core itself - the probe stub
    replaces only that function and leaves fingerprint_key_provider bound
    as the defensive import left it."""
    if reconnect_run.fingerprint_key_provider is None:
        pytest.skip("fingerprint.py not present")

    monkeypatch.setattr(reconnect_run, "fingerprint_unavailable_reason", lambda: "stub reason")

    argv = _SCAN_ARGV + ["--fingerprint"]
    args = _parse_args(argv)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            result = reconnect_run.scan_reconnect_candidates(args)
    finally:
        os.chdir(old_cwd)

    assert buf_out.getvalue() == ""
    assert buf_err.getvalue() == ""
    assert result.result is not None
    assert any("stub reason" in warning for warning in result.result.warnings)

    rendered = render_scan_reconnect_candidates(result, args)
    assert rendered.stderr_lines[0].startswith("fingerprint_dependency_missing=stub reason")


def test_fingerprint_warning_absent_when_reason_returns_none(
    fixture_corpus: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control for test_fingerprint_warning_lands_in_result_not_printed_by_core:
    proves the warning assertions above actually depend on
    fingerprint_unavailable_reason() returning a reason, by monkeypatching it to
    return None instead of "stub reason" and observing the warning disappear from
    both ReconnectResult.warnings and the rendered stderr. Observed to fail
    test_fingerprint_warning_lands_in_result_not_printed_by_core's warning
    assertions when this stub replaces the "stub reason" stub."""
    if reconnect_run.fingerprint_key_provider is None:
        pytest.skip("fingerprint.py not present")

    monkeypatch.setattr(reconnect_run, "fingerprint_unavailable_reason", lambda: None)

    argv = _SCAN_ARGV + ["--fingerprint"]
    args = _parse_args(argv)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        result = reconnect_run.scan_reconnect_candidates(args)
    finally:
        os.chdir(old_cwd)

    assert result.result is not None
    assert not any("stub reason" in warning for warning in result.result.warnings)
    rendered = render_scan_reconnect_candidates(result, args)
    assert not any(
        line.startswith("fingerprint_dependency_missing=") for line in rendered.stderr_lines
    )


def test_fingerprint_key_provider_none_raises(fixture_corpus: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Setting fingerprint_key_provider to None proves the raise path is
    distinct from the warn path rather than being masked by the probe
    stub above."""
    monkeypatch.setattr(reconnect_run, "fingerprint_key_provider", None)

    argv = _SCAN_ARGV + ["--fingerprint"]
    args = _parse_args(argv)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        result = reconnect_run.scan_reconnect_candidates(args)
    finally:
        os.chdir(old_cwd)

    assert result.error is not None and result.error.startswith("fingerprint_unavailable=")


def test_fingerprint_key_provider_present_does_not_raise_unavailable(
    fixture_corpus: Path,
) -> None:
    """Negative control for test_fingerprint_key_provider_none_raises: proves the
    fingerprint_unavailable= error above is actually caused by
    fingerprint_key_provider being None, not by the --fingerprint flag on its own,
    by leaving fingerprint_key_provider at its normal bound value and observing no
    such error. Observed to fail test_fingerprint_key_provider_none_raises'
    assertion when run without the monkeypatch that sets the provider to None."""
    if reconnect_run.fingerprint_key_provider is None:
        pytest.skip("fingerprint.py not present")

    argv = _SCAN_ARGV + ["--fingerprint"]
    args = _parse_args(argv)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        result = reconnect_run.scan_reconnect_candidates(args)
    finally:
        os.chdir(old_cwd)

    assert result.error is None or not result.error.startswith("fingerprint_unavailable=")


def test_no_refute_line_comes_from_renderer(fixture_corpus: Path) -> None:
    """A no-refute run's refutation line is produced by the renderer via
    shared_args.refutation_disabled_line, not restated as a literal
    inside reconnect_render."""
    argv = _SCAN_ARGV + ["--no-refute"]
    rendered, _result = _render_for_argv(argv, fixture_corpus.parent)
    assert any(line.startswith("refutation_disabled=") for line in rendered.stderr_lines)


def test_no_refute_line_absent_when_source_returns_none(
    fixture_corpus: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control for test_no_refute_line_comes_from_renderer: proves
    that assertion actually depends on shared_args.refutation_disabled_line
    rather than passing regardless of --no-refute, by monkeypatching the
    renderer module's bound reference to always return None and observing
    the refutation line disappear from stderr. Observed to fail the
    positive test's assertion when run against an unmodified renderer."""
    import traktor_nml.reconnect_render as reconnect_render_module

    monkeypatch.setattr(reconnect_render_module, "refutation_disabled_line", lambda args: None)
    argv = _SCAN_ARGV + ["--no-refute"]
    rendered, _result = _render_for_argv(argv, fixture_corpus.parent)
    assert not any(line.startswith("refutation_disabled=") for line in rendered.stderr_lines)


def test_on_progress_fires_and_cancel_raises(fixture_corpus: Path) -> None:
    """An on_progress callback passed into the core fires at least once
    with a path from the scan, and a pre-set cancel token raises
    ScanCancelled out of the core rather than yielding a partial
    result."""
    args = _parse_args(_SCAN_ARGV)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        seen: list = []
        reconnect_run.scan_reconnect_candidates(
            args, on_progress=lambda done, total, path: seen.append(path)
        )
        assert seen, "on_progress never fired"

        cancel = threading.Event()
        cancel.set()
        old_root = parse_xml(args.old_input).getroot()
        with pytest.raises(ScanCancelled):
            reconnect_run.run_reconnection(args, old_root, cancel=cancel)
    finally:
        os.chdir(old_cwd)


def test_on_progress_does_not_fire_when_scan_root_is_empty(fixture_corpus: Path) -> None:
    """Negative control for test_on_progress_fires_and_cancel_raises's
    on_progress assertion: proves that assertion actually depends on the
    scan finding files to report on, not on the callback firing
    regardless of scan content, by pointing --scan-root at an empty
    directory and observing on_progress never fire. Observed to fail
    (seen non-empty) if run_reconnection ignored an empty scan tree and
    fired progress anyway."""
    empty_root = fixture_corpus.parent / "empty_audio"
    empty_root.mkdir()
    argv = [
        "scan-reconnect-candidates", "recon/stale.nml",
        "--scan-root", "empty_audio",
        "--volume-map", "empty_audio", "D:", "D:",
        "--match-confidence", "filename",
        "--cache", "out/recon.tagcache.json",
    ]
    args = _parse_args(argv)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        seen: list = []
        reconnect_run.scan_reconnect_candidates(
            args, on_progress=lambda done, total, path: seen.append(path)
        )
    finally:
        os.chdir(old_cwd)

    assert seen == []


def test_cancel_not_set_does_not_raise_scan_cancelled(fixture_corpus: Path) -> None:
    """Negative control for test_on_progress_fires_and_cancel_raises: proves the
    ScanCancelled raise above is actually gated on the cancel token being set,
    not raised unconditionally by run_reconnection, by passing an unset Event
    and observing the run complete instead of raising. Observed to fail
    (raise ScanCancelled) if run_reconnection ignored the cancel token's
    state rather than checking it."""
    args = _parse_args(_SCAN_ARGV)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        old_root = parse_xml(args.old_input).getroot()
        cancel = threading.Event()
        result = reconnect_run.run_reconnection(args, old_root, cancel=cancel)
    finally:
        os.chdir(old_cwd)

    assert result is not None


def test_output_equal_to_input_never_starts_reconnection(fixture_corpus: Path) -> None:
    """A rewrite-from-reconnect run whose output path equals its input
    path is refused before reconnection starts - proved by asserting no
    ReconnectResult is ever produced."""
    argv = [
        "rewrite-from-reconnect", "recon/stale.nml", "recon/stale.nml",
        "--scan-root", "recon/audio",
        "--volume-map", "recon/audio", "D:", "D:",
        "--match-confidence", "filename",
        "--cache", "out/recon.tagcache.json",
    ]
    args = _parse_args(argv)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        result = reconnect_run.rewrite_from_reconnect(args)
    finally:
        os.chdir(old_cwd)

    assert result.reconnect is None
    assert result.outcome is not None and result.outcome.error == "output_must_differ_from_input"


def test_output_differs_from_input_starts_reconnection(fixture_corpus: Path) -> None:
    """Negative control for test_output_equal_to_input_never_starts_reconnection:
    proves the refusal above is gated on output_path equaling input_path, not on
    rewrite-from-reconnect refusing to reconnect regardless of the paths given,
    by pointing output at a different path and observing reconnection actually
    starts. Observed to fail (reconnect is None) if the equality check applied
    to differing paths as well."""
    argv = [
        "rewrite-from-reconnect", "recon/stale.nml", "out/reconnected.nml",
        "--scan-root", "recon/audio",
        "--volume-map", "recon/audio", "D:", "D:",
        "--match-confidence", "filename",
        "--cache", "out/recon.tagcache.json",
        "--dry-run",
    ]
    args = _parse_args(argv)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        result = reconnect_run.rewrite_from_reconnect(args)
    finally:
        os.chdir(old_cwd)

    assert result.reconnect is not None


def _no_refute_args() -> argparse.Namespace:
    """A minimal args namespace with refutation disabled, sufficient for
    refutation_disabled_line (only reads no_refute)."""
    return argparse.Namespace(no_refute=True)


def test_scan_reconnect_stderr_order_is_diagnostics_then_warnings_then_refutation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The full three-part stderr ordering CI-M-002-017 requires - diagnostics,
    then fingerprint warning, then the refutation-disabled line - asserted at the
    emit() level rather than only on the returned RenderedOutput, because M-001
    demonstrated that an ordering assertion on the returned object alone can pass
    even when the printing layer emits the parts in a different order. No manifest
    case produces more than one of the three, so this is the only place the full
    order is checked."""
    reconnect = ReconnectResult(
        mapping={},
        stats={},
        ambiguity_rows=[],
        old_records=[],
        warnings=["fingerprint_dependency_missing=pyacoustid not installed"],
        diagnostics=("tag_reading_unavailable=mutagen not installed",),
    )
    result = ScanReconnectResult(result=reconnect, error=None, csv_path=None)
    rendered = render_scan_reconnect_candidates(result, _no_refute_args())

    emit(rendered)
    captured = capsys.readouterr()
    stderr_lines = captured.err.splitlines()

    assert stderr_lines == [
        "tag_reading_unavailable=mutagen not installed",
        "fingerprint_dependency_missing=pyacoustid not installed",
        "refutation_disabled=size and duration contradictions will be ignored; "
        "a candidate the collection's own FILESIZE/PLAYTIME_FLOAT contradict can now win a match",
    ]


def test_rewrite_from_reconnect_stderr_order_is_diagnostics_then_warnings_then_refutation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Same three-part stderr ordering as
    test_scan_reconnect_stderr_order_is_diagnostics_then_warnings_then_refutation,
    for render_rewrite_from_reconnect's emit() output rather than
    render_scan_reconnect_candidates'."""
    reconnect = ReconnectResult(
        mapping={},
        stats={},
        ambiguity_rows=[],
        old_records=[],
        warnings=["fingerprint_dependency_missing=pyacoustid not installed"],
        diagnostics=("tag_reading_unavailable=mutagen not installed",),
    )
    outcome = WriteOutcome(stats={}, samples=[], error=None, written_path=None, exit_code=0)
    result = RewriteReconnectResult(
        outcome=outcome, reconnect=reconnect, csv_path=None, error=None
    )
    rendered = render_rewrite_from_reconnect(result, _no_refute_args())

    emit(rendered)
    captured = capsys.readouterr()
    stderr_lines = captured.err.splitlines()

    assert stderr_lines == [
        "tag_reading_unavailable=mutagen not installed",
        "fingerprint_dependency_missing=pyacoustid not installed",
        "refutation_disabled=size and duration contradictions will be ignored; "
        "a candidate the collection's own FILESIZE/PLAYTIME_FLOAT contradict can now win a match",
    ]

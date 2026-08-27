"""Every character the reconnect commands put on stdout or stderr.

reconnect_run.py returns typed results rather than printing; this module
turns a result into buffered stdout lines, stderr lines and an exit code,
and emit is the one function that actually writes to a stream.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from . import rewrite
from .reconnect_run import RewriteReconnectResult, ScanReconnectResult
from .shared_args import refutation_disabled_line


@dataclass
class RenderedOutput:
    """Buffered stdout lines, stderr lines and an exit code. emit is the
    one function that writes them to sys.stdout/sys.stderr, so every
    print on the reconnect path lives inside it rather than scattered
    across the pipeline."""

    # Two separate lists rather than one interleaved stream: the parity
    # manifest records stdout and stderr independently, and buffering
    # them separately means this module cannot reorder what it observes.
    stdout_lines: list[str]
    stderr_lines: list[str]
    exit_code: int


def emit(rendered: RenderedOutput) -> int:
    for line in rendered.stdout_lines:
        print(line)
    for line in rendered.stderr_lines:
        print(line, file=sys.stderr)
    return rendered.exit_code


def render_scan_reconnect_candidates(
    result: ScanReconnectResult, args: argparse.Namespace
) -> RenderedOutput:
    """Produces stdout as reconnectable=<count> followed by the stats
    block in mapping order, then csv_written=<path> only when a CSV was
    written; stderr as the run's own diagnostics, then its warnings,
    then the refutation-disabled line when refutation is off.
    tests/baselines/manifest.json's recorded scan-reconnect-candidates
    cases are the oracle for this exact ordering. An error on the result
    short-circuits stderr to result.diagnostics - whatever the scan
    emitted before the typed error was raised - followed by the error
    line, with exit code 2, since no ReconnectResult exists yet.
    """
    if result.error is not None:
        return RenderedOutput([], list(result.diagnostics) + [result.error], 2)

    reconnect = result.result
    stdout_lines = [f"reconnectable={len(reconnect.mapping)}"]
    for key, value in reconnect.stats.items():
        stdout_lines.append(f"{key}={value}")
    if result.csv_path is not None:
        stdout_lines.append(f"csv_written={result.csv_path.as_posix()}")

    # Diagnostics precede the fingerprint and refutation warnings: that
    # reproduces the legacy sequence, in which index_scan_roots runs
    # before the fingerprint tier is built and before
    # warn_refutation_disabled is called (DL-056).
    stderr_lines = list(reconnect.diagnostics) + list(reconnect.warnings)
    refutation_line = refutation_disabled_line(args)
    if refutation_line is not None:
        stderr_lines.append(refutation_line)

    return RenderedOutput(stdout_lines, stderr_lines, 0)


def render_rewrite_from_reconnect(
    result: RewriteReconnectResult, args: argparse.Namespace
) -> RenderedOutput:
    """Produces stdout as csv_written=<path> first when a CSV was
    written, then the stats/samples block and output_written=<path>
    sourced from the WriteOutcome, in the same order write_nml_safely
    prints them. The CSV line comes first because the CSV is written
    inside the reconnection callback, before plan_and_write_nml's write
    step runs. Warnings and the refutation line are gated on
    result.reconnect being populated, so a run that fails before
    reconnection completes (an output collision, or a volume-identity/
    fingerprint error) prints neither. Diagnostics are not gated the same
    way: result.diagnostics carries whatever the scan emitted before such
    a typed error was raised, and is emitted ahead of the error line
    regardless of whether reconnection completed.
    """
    stdout_lines: list[str] = []
    if result.csv_path is not None:
        stdout_lines.append(f"csv_written={result.csv_path.as_posix()}")

    outcome = result.outcome
    if outcome is not None and outcome.stats is not None:
        stdout_lines.extend(rewrite.format_stats_and_samples(outcome.stats, outcome.samples))
    if outcome is not None and outcome.written_path is not None:
        stdout_lines.append(f"output_written={outcome.written_path.as_posix()}")

    stderr_lines: list[str] = []
    if result.reconnect is not None:
        # The refutation warning belongs only to a run that reached
        # matching: volume-identity resolution and the fingerprint check
        # must both have succeeded first - gating on
        # result.reconnect (populated only once run_reconnection returns)
        # reproduces that: an output collision or a volume_identity_error/
        # fingerprint_unavailable failure prints neither warning.
        stderr_lines.extend(result.reconnect.diagnostics)
        stderr_lines.extend(result.reconnect.warnings)
        refutation_line = refutation_disabled_line(args)
        if refutation_line is not None:
            stderr_lines.append(refutation_line)
    else:
        stderr_lines.extend(result.diagnostics)
    if outcome is not None and outcome.error is not None:
        stderr_lines.append(outcome.error)
    elif result.error is not None:
        stderr_lines.append(result.error)

    exit_code = outcome.exit_code if outcome is not None else 2
    return RenderedOutput(stdout_lines, stderr_lines, exit_code)

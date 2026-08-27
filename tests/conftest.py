"""Shared pytest fixtures: fixture corpus and in-process CLI invocation."""

from __future__ import annotations

import contextlib
import io
import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.fixtures.build_fixtures import build_fixtures, build_reconnect_fixtures


@dataclass
class RunResult:
    """Captures exit code and captured stdout/stderr from one in-process
    CLI invocation, since every guarantee in this suite is stated over a
    printed stats line or written file, not an internal function's return
    value."""
    exit_code: int
    stdout: str
    stderr: str


def run_tool(argv: list[str], cwd: Path) -> RunResult:
    """Invoke the tool's main entry point with argv inside cwd.

    Routes through the module entry point rather than a subprocess so
    coverage and tracebacks stay intact.
    """
    from traktor_nml.cli import main

    old_cwd = Path.cwd()
    stdout = io.StringIO()
    stderr = io.StringIO()
    os.chdir(cwd)
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                exit_code = main(argv)
            except SystemExit as exc:
                exit_code = 0 if exc.code is None else int(exc.code)
    finally:
        os.chdir(old_cwd)
    return RunResult(exit_code=exit_code, stdout=stdout.getvalue(), stderr=stderr.getvalue())


@pytest.fixture
def fixture_corpus(tmp_path: Path) -> Path:
    """Materialise the deterministic fixture corpus once per test into
    tmp_path, so tests read real files rather than in-memory strings."""
    corpus_dir = tmp_path / "corpus"
    build_fixtures(corpus_dir)
    # The reconnect tree is a SIBLING of the corpus, never inside it:
    # stored cases that scan the corpus directory would otherwise see an
    # extra .nml and report a different candidate count, invalidating
    # baselines this fixture has no business touching.
    build_reconnect_fixtures(tmp_path / "recon")
    return corpus_dir

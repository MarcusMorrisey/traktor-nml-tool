"""Shared pytest fixtures: fixture corpus and in-process CLI invocation."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.fixtures.build_fixtures import build_fixtures, build_reconnect_fixtures

# The optional packages whose presence moves the suite's pass and skip
# counts. Under the system interpreter the run is 416 passed, 3 skipped;
# under .venv, which carries all of these, it is 417 passed, 2 skipped.
# Both runs are green - the difference is which tests can execute, not
# which pass - so a bare count says nothing without the interpreter it was
# measured under, which is why the summary below prints them.
#
# nicegui and webview do NOT belong to that difference and are listed for a
# separate reason: they are the packages the isolation rules in
# docs/nicegui-gui-analysis.md #5 are about, so a reader checking those
# rules wants to see whether the run had them available. Neither test
# degrades when they are present - test_cli_without_nicegui.py blocks the
# import through sys.meta_path precisely so it holds on a machine that has
# the real package, and test_gui_import_isolation.py walks ASTs and imports
# nothing - which is why this reports rather than refuses.
_REPORTED = ("nicegui", "webview", "pyacoustid", "mutagen", "lxml")


def _conditions() -> list[str]:
    """The interpreter and which of _REPORTED it carries."""
    present = [name for name in _REPORTED if importlib.util.find_spec(name) is not None]
    absent = [name for name in _REPORTED if name not in present]
    return [
        f"interpreter: {sys.executable}",
        f"optional present: {', '.join(present) or 'none'}",
        f"optional absent: {', '.join(absent) or 'none'}",
    ]


def pytest_terminal_summary(terminalreporter) -> None:
    """Print the run's conditions next to its counts.

    This is the terminal summary rather than the report header because the
    header is suppressed by -q, and `python -m pytest tests/ -q` is the
    invocation a count is usually copied out of - the one case where the
    conditions most need to be on screen. Printed through the reporter's
    own write_line so it survives -q, and placed after the counts so a
    number copied out of a run carries them.
    """
    for line in _conditions():
        terminalreporter.write_line(line)


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

"""Guards the nicegui-optional half of the isolation rules in
docs/nicegui-gui-analysis.md #5: nicegui is an optional extra, and the
CLI - including its subcommand discovery, which imports every module
under traktor_nml/commands/ at startup - must work with nicegui blocked.

The invocation chosen for the "one real invocation" #5 asks for is
`inspect corpus/moved_paths.nml --limit 5`: it is one of the recorded
baseline cases in tests/baselines/manifest.json, it reads and parses a
real NML fixture rather than only exercising argument parsing, and its
expected stdout is pinned there, so this test can assert against a
known-good value rather than merely a zero exit code.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.conftest import run_tool

NICEGUI_ROOT = "nicegui"


class _BlockNicegui:
    """A sys.meta_path finder that raises ImportError for `nicegui` and
    every `nicegui.*` submodule, so an accidental import fails even on a
    machine that has the real package installed - a plain sys.modules
    sentinel would not stop a genuine import from succeeding."""

    def find_module(self, fullname, path=None):  # pragma: no cover - legacy hook, Python still probes it
        if fullname == NICEGUI_ROOT or fullname.startswith(NICEGUI_ROOT + "."):
            raise ImportError(f"blocked for test: {fullname}")
        return None

    def find_spec(self, fullname, path, target=None):
        if fullname == NICEGUI_ROOT or fullname.startswith(NICEGUI_ROOT + "."):
            raise ImportError(f"blocked for test: {fullname}")
        return None


@pytest.fixture
def block_nicegui():
    """Installs the finder at the front of sys.meta_path and evicts any
    already-cached nicegui/nicegui.* modules first, since a cached
    module would satisfy `import nicegui` from sys.modules before the
    finder is ever consulted. Restores both the finder list and the
    evicted modules in a finally block, so a test failing partway
    through still leaves sys.meta_path and sys.modules exactly as it
    found them.
    """
    finder = _BlockNicegui()
    evicted = {
        name: mod
        for name, mod in list(sys.modules.items())
        if name == NICEGUI_ROOT or name.startswith(NICEGUI_ROOT + ".")
    }
    for name in evicted:
        del sys.modules[name]

    sys.meta_path.insert(0, finder)
    try:
        yield finder
    finally:
        sys.meta_path.remove(finder)
        sys.modules.update(evicted)


def test_import_nicegui_actually_fails_under_the_block(block_nicegui) -> None:
    """Sanity check on the fixture itself: with the finder installed, a
    direct `import nicegui` raises ImportError, proving the block is a
    real import failure rather than a no-op."""
    with pytest.raises(ImportError):
        __import__(NICEGUI_ROOT)


def test_help_and_a_real_invocation_succeed_with_nicegui_blocked(block_nicegui, fixture_corpus: Path, tmp_path: Path) -> None:
    """--help and one real invocation both succeed with nicegui blocked
    at sys.meta_path, going through commands/__init__.py's
    iter_command_modules (which imports every command module, including
    at --help time, since build_parser() runs before argv is parsed) -
    the path #5 identifies as the one an accidental top-level nicegui
    import under commands/ would break.
    """
    help_result = run_tool(["--help"], cwd=tmp_path)
    assert help_result.exit_code == 0
    assert "usage:" in help_result.stdout.lower()

    (tmp_path / "out").mkdir(exist_ok=True)
    result = run_tool(["inspect", "corpus/moved_paths.nml", "--limit", "5"], cwd=tmp_path)
    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout == (
        "root_version=20\n"
        "program=Traktor\n"
        "collection_entries=1\n"
        "collection_entries_with_location=1\n"
        "collection_entries_with_primarykey=0\n"
        "playlist_entry_refs=0\n"
        "playlist_primarykeys=0\n"
        "all_entry_nodes_in_document=1\n"
        "sample artist='Aphex Twin' title='Xtal' volume='C:' dir='/:Users/:dj/:Music/:' file='xtal.mp3'\n"
    )


def test_cli_help_raises_when_a_command_module_imports_nicegui(block_nicegui, tmp_path: Path) -> None:
    """Standing negative control for the guard above: appends a throwaway
    directory to the real traktor_nml.commands package's __path__
    (pkgutil.iter_modules(__path__) scans every entry, so a regular
    package's __path__ can carry more than one directory) holding one
    module whose only statement is `import nicegui`, then runs the real
    CLI entry point - unmodified production code, not a reimplementation
    - through run_tool(["--help"], ...) with nicegui blocked.

    This reproduces, without editing any tracked file, exactly the
    failure mode #5 warns about: since build_parser() calls
    iter_command_modules() before argv is parsed, even --help imports
    every command module and so fails too, not only a real subcommand.
    Restores commands.__path__ in a finally block whether or not the
    assertion holds.

    Observed to fail (no exception raised) when the probe module's
    `import nicegui` line was replaced with a no-op `register(subparsers,
    handlers)` function - the shape every real command module actually
    exposes: run_tool(["--help"], ...) then returned normally with
    exit_code 0, since nothing under commands/ imported nicegui any
    more - confirming the failure above is caused by the injected
    import, not by the path manipulation itself or by the probe module
    lacking `register`.
    """
    from traktor_nml import commands

    probe_dir = tmp_path / "probe_commands"
    probe_dir.mkdir()
    (probe_dir / "zz_nicegui_probe_cmd.py").write_text(
        "import nicegui\n\n\ndef register(subparsers, handlers):\n    pass\n",
        encoding="utf-8",
    )

    commands.__path__.append(str(probe_dir))
    try:
        with pytest.raises(ImportError):
            run_tool(["--help"], cwd=tmp_path)
    finally:
        commands.__path__.remove(str(probe_dir))

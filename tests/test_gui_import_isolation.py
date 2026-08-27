"""Guards the import-graph half of the isolation rules in
docs/nicegui-gui-analysis.md #5: traktor_nml/gui/ may import from
traktor_nml/ cores, but traktor_nml/commands/ and traktor_nml/cli.py
import nothing from traktor_nml/gui/. A walk of each module's AST
asserts this, so the rule is enforced by a test rather than convention,
as #5 requires.

traktor_nml/gui/ does not exist in this tree yet (#5's sequencing step
4 introduces it); every module checked here currently imports nothing
from it, so the walk finds no violations today.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
COMMANDS_DIR = REPO_ROOT / "traktor_nml" / "commands"
CLI_MODULE = REPO_ROOT / "traktor_nml" / "cli.py"

GUI_PACKAGE = "traktor_nml.gui"


def _resolve_from_base(node: ast.ImportFrom, module_name: str, is_package: bool) -> str:
    """Resolves the dotted package an `ast.ImportFrom` node's names are
    relative to, matching Python's own relative-import resolution: for
    `level == 0` the base is `node.module` itself (an absolute import);
    for `level >= 1`, `level - 1` components are stripped from the
    importing module's own containing package before `node.module` (if
    any) is appended.

    `is_package` distinguishes commands/__init__.py, whose own dotted
    name IS its containing package for relative-import purposes, from an
    ordinary module, whose containing package is its name minus its
    last component.
    """
    if node.level == 0:
        base_parts = node.module.split(".") if node.module else []
        return ".".join(base_parts)

    parts = module_name.split(".")
    pkg_parts = parts if is_package else parts[:-1]
    strip = node.level - 1
    if strip:
        pkg_parts = pkg_parts[: len(pkg_parts) - strip] if len(pkg_parts) > strip else []
    if node.module:
        pkg_parts = pkg_parts + node.module.split(".")
    return ".".join(pkg_parts)


def _targets_gui(dotted: str) -> bool:
    return dotted == GUI_PACKAGE or dotted.startswith(GUI_PACKAGE + ".")


def _gui_import_violations(source: str, module_name: str, is_package: bool) -> list[str]:
    """Walks source's AST for any import reaching traktor_nml.gui,
    covering every import form #5 names: `import traktor_nml.gui` (and
    `.gui.submodule`), `from traktor_nml.gui import x`,
    `from traktor_nml import gui`, and relative forms (`from .gui
    import x`, `from ..gui import x`) at whatever depth applies to the
    module being checked, via module_name/is_package."""
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _targets_gui(alias.name):
                    found.append(f"import {alias.name} at line {node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from_base(node, module_name, is_package)
            if _targets_gui(base):
                found.append(f"from {'.' * node.level}{node.module or ''} import ... at line {node.lineno}")
                continue
            for alias in node.names:
                full = f"{base}.{alias.name}" if base else alias.name
                if _targets_gui(full):
                    found.append(f"from {'.' * node.level}{node.module or ''} import {alias.name} at line {node.lineno}")
    return found


def _checked_modules() -> list[tuple[Path, str, bool]]:
    """Every module under traktor_nml/commands/ plus traktor_nml/cli.py,
    paired with its dotted module name and whether it is the package's
    own __init__.py (see _resolve_from_base)."""
    modules = [(CLI_MODULE, "traktor_nml.cli", False)]
    for path in sorted(COMMANDS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            modules.append((path, "traktor_nml.commands", True))
        else:
            modules.append((path, f"traktor_nml.commands.{path.stem}", False))
    return modules


def test_commands_and_cli_import_nothing_from_gui() -> None:
    """The real commands/ modules and cli.py, unmutated, report no
    import reaching traktor_nml.gui - the baseline the negative
    controls below are checked against."""
    violations: dict[str, list[str]] = {}
    for path, module_name, is_package in _checked_modules():
        source = path.read_text(encoding="utf-8")
        found = _gui_import_violations(source, module_name, is_package)
        if found:
            violations[str(path)] = found
    assert violations == {}


def test_cli_py_with_reintroduced_gui_import_is_caught() -> None:
    """Negative control for the guard above: splices `from .gui import
    wizard` onto the end of the real cli.py source (in memory only - no
    file on disk is touched) and runs _gui_import_violations over the
    mutated text with cli.py's real module_name/is_package. cli.py's
    containing package is traktor_nml, so a level-1 relative import
    (`from .gui import ...`) resolves to traktor_nml.gui, matching the
    form #5 calls out.

    Observed to fail (violations == []) if _gui_import_violations did
    not resolve relative imports against the importing module's own
    package - run against the real, unmutated splice target below,
    confirmed to report none.
    """
    source = CLI_MODULE.read_text(encoding="utf-8")
    mutated = source + "\n\nfrom .gui import wizard  # noqa\n"

    assert _gui_import_violations(mutated, "traktor_nml.cli", is_package=False) != []
    assert _gui_import_violations(source, "traktor_nml.cli", is_package=False) == []


def test_checker_detects_every_gui_import_form_named_in_the_analysis_doc() -> None:
    """Exercises _gui_import_violations against a synthetic module for
    each import form #5 names, so the checker is proven against more
    than the one real splice target above. Covers both a plain module
    (traktor_nml.commands.probe_cmd) and the package __init__.py itself,
    since relative-import resolution differs between the two (see
    _resolve_from_base)."""
    cases = [
        ("import traktor_nml.gui\n", "traktor_nml.commands.probe_cmd", False),
        ("import traktor_nml.gui.wizard\n", "traktor_nml.commands.probe_cmd", False),
        ("from traktor_nml.gui import wizard\n", "traktor_nml.commands.probe_cmd", False),
        ("from traktor_nml import gui\n", "traktor_nml.commands.probe_cmd", False),
        ("from ..gui import wizard\n", "traktor_nml.commands.probe_cmd", False),
        ("from ..gui import wizard\n", "traktor_nml.commands", True),
        ("from .gui import wizard\n", "traktor_nml.cli", False),
    ]
    for source, module_name, is_package in cases:
        found = _gui_import_violations(source, module_name, is_package)
        assert found, f"expected a violation for {source!r} ({module_name}, is_package={is_package})"


def test_checker_reports_no_violation_for_an_unrelated_import() -> None:
    """A synthetic module importing something outside traktor_nml.gui
    entirely (including a sibling name that merely starts with the same
    letters) reports no violation, so the checker is a targeted match
    rather than a substring scan."""
    source = (
        "from traktor_nml.diskscan import index_scan_roots\n"
        "from traktor_nml import guibbon\n"
        "from ..reconnect_run import scan_reconnect_candidates\n"
    )
    assert _gui_import_violations(source, "traktor_nml.commands.probe_cmd", is_package=False) == []

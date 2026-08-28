"""Guards that `pip install .[gui]` installs everything
`python -m traktor_nml.gui` imports, so the documented install path
starts the wizard on a clean machine.

The gap this closes was real and invisible to every other guard. The
gui extra declared only nicegui, while traktor_nml/gui/file_picker.py
imports `webview` at module scope (line 26) and app.py imports
file_picker at line 51, so `python -m traktor_nml.gui` on an
environment built from the documented extra raised ImportError before
the wizard could start. Nothing caught it: the suite runs on the system
interpreter, which has neither framework, and
tests/test_gui_module_imports.py deliberately stubs both `nicegui` and
`webview` in sys.modules - so the very guard that proves the modules
import is the one that cannot see a missing distribution. The AST walks
in tests/test_gui_view_boundary.py read source text and never consult
packaging metadata at all.

The check derives its expectation from the source rather than from a
transcribed list: it walks the three nicegui-importing modules for
module-level imports, discards stdlib and first-party names, maps each
remaining import to the distribution that provides it, and asserts that
distribution is declared in the gui extra. A new third-party import
added to gui/ therefore fails here until it is either declared or
deliberately mapped, rather than passing because a list nobody updated
still matches itself.

Import module name and distribution name differ (`import webview` comes
from `pywebview`), so _DISTRIBUTION_FOR_MODULE maps them explicitly and
an unmapped third-party import is a failure rather than a skip - an
unrecognised import is exactly the case that must not pass silently.

Observed to fail against the actual defect: with "pywebview" removed
from the gui extra in pyproject.toml (the file copied aside first and
restored from the copy, never via `git checkout`), running this test
produced:

    AssertionError: traktor_nml/gui/ imports these at module scope but
    the [gui] extra does not install them: pywebview (from `import
    webview` in file_picker.py). `pip install .[gui]` then leaves
    `python -m traktor_nml.gui` raising ImportError.
    assert not {'pywebview'}

Restoring the line made it pass again.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GUI_DIR = _REPO_ROOT / "traktor_nml" / "gui"

# The three modules docs/nicegui-gui-analysis.md #5 allows to import a
# GUI framework; the rest of gui/ is framework-free by design and is
# guarded by tests/test_gui_import_isolation.py.
_FRAMEWORK_IMPORTING_MODULES = ("app.py", "file_picker.py", "__main__.py")

# Import name -> the distribution that provides it, for names where the
# two differ or where the mapping is worth stating outright.
_DISTRIBUTION_FOR_MODULE = {
    "nicegui": "nicegui",
    "webview": "pywebview",
}


def _module_level_imports(source: str) -> set[str]:
    """Top-level package name of every absolute import at module scope.

    Relative imports (`from . import review_model`) are first-party and
    carry no distribution, so they are skipped. Imports nested inside a
    function or a `try:` are skipped too: this guard is about what fails
    at interpreter start, which is what breaks `python -m`.
    """
    found: set[str] = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return found


def _declared_distributions(extra: str) -> set[str]:
    """Distribution names declared in one optional-dependencies extra,
    with any version specifier and any extras marker stripped."""
    metadata = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requirements = metadata["project"]["optional-dependencies"][extra]
    names = set()
    for requirement in requirements:
        name = requirement.split(";")[0].strip()
        for separator in ("[", "=", ">", "<", "!", "~", " "):
            name = name.split(separator)[0]
        names.add(name.strip().lower())
    return names


def test_gui_extra_installs_every_framework_gui_imports() -> None:
    """Every third-party module traktor_nml/gui/ imports at module
    scope is installed by `pip install .[gui]`.

    See this module's docstring for the mutation run and the output
    observed.
    """
    required: dict[str, str] = {}
    for filename in _FRAMEWORK_IMPORTING_MODULES:
        path = _GUI_DIR / filename
        for imported in _module_level_imports(path.read_text(encoding="utf-8")):
            if imported == "traktor_nml" or imported in sys.stdlib_module_names:
                continue
            assert imported in _DISTRIBUTION_FOR_MODULE, (
                f"{filename} imports third-party module {imported!r}, which "
                f"_DISTRIBUTION_FOR_MODULE does not map to a distribution. Add the "
                f"mapping and declare the distribution in the [gui] extra, so an "
                f"unrecognised import cannot pass this guard silently."
            )
            required[_DISTRIBUTION_FOR_MODULE[imported]] = f"`import {imported}` in {filename}"

    declared = _declared_distributions("gui")
    missing = {dist for dist in required if dist.lower() not in declared}
    detail = ", ".join(f"{dist} (from {required[dist]})" for dist in sorted(missing))
    assert not missing, (
        f"traktor_nml/gui/ imports these at module scope but the [gui] extra does "
        f"not install them: {detail}. `pip install .[gui]` then leaves "
        f"`python -m traktor_nml.gui` raising ImportError."
    )


def test_all_extra_pulls_in_the_gui_extra() -> None:
    """The `all` extra reaches the gui extra, so `pip install .[all]`
    starts the wizard too.

    Observed to fail: with `gui` removed from the `all` extra's
    `traktor-nml-tool[tags,fingerprint,gui]` line (pyproject.toml
    copied aside first and restored from the copy), this raised:

        AssertionError: the [all] extra does not reach [gui], so `pip
        install .[all]` would not install the wizard's frameworks:
        {'fingerprint', 'tags'}
        assert 'gui' in {'fingerprint', 'tags'}
    """
    metadata = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requirements = metadata["project"]["optional-dependencies"]["all"]
    reached: set[str] = set()
    for requirement in requirements:
        if "[" in requirement and "]" in requirement:
            inner = requirement[requirement.index("[") + 1 : requirement.index("]")]
            reached.update(part.strip() for part in inner.split(","))
    assert "gui" in reached, (
        f"the [all] extra does not reach [gui], so `pip install .[all]` would not "
        f"install the wizard's frameworks: {reached}"
    )

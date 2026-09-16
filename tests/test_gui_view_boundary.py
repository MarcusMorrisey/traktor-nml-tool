"""Guards the view boundary of traktor_nml/gui/ (M-005) without ever
importing nicegui or pywebview - the suite runs on the system
interpreter, which has neither. Each guard constructs its broken
scenario in executable code and the docstring records the mutation made
and the output observed under it, matching the register
tests/test_scan_diagnostics.py, tests/test_review_channel.py and
tests/test_reconnect_write_core.py already use.

app.py is deliberately untested by interaction (traktor_nml/README.md,
Tradeoffs): there is no pytest harness driving rendered DOM. What is
tested here is its source, by AST walk - the boundary rule of
docs/nicegui-gui-analysis.md #5 (only app.py, file_picker.py and
__main__.py may import nicegui/pywebview), the threading choice of #4
(run.io_bound, never the process-pool variant), and the one load-bearing
call the plan pins by name: the Write control's provider must return
wizard_state.amended_result(...), never the unamended scan result
(traktor_nml/README.md's DL-076).
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
GUI_DIR = REPO_ROOT / "traktor_nml" / "gui"
APP_PATH = GUI_DIR / "app.py"

_FRAMEWORK_ROOTS = frozenset({"nicegui", "webview"})


def _module_files() -> list[Path]:
    return sorted(p for p in GUI_DIR.glob("*.py") if p.name != "__pycache__")


def _imported_roots(source: str) -> set[str]:
    """The set of top-level package names one module's imports reach -
    "nicegui" for `import nicegui`, `from nicegui import ui`, or
    `from nicegui.x import y`; "webview" likewise for pywebview, whose
    importable name is `webview`."""
    tree = ast.parse(source)
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return roots


def _framework_importing_modules(files: list[Path]) -> set[str]:
    found = set()
    for path in files:
        roots = _imported_roots(path.read_text(encoding="utf-8"))
        if roots & _FRAMEWORK_ROOTS:
            found.add(path.name)
    return found


def test_only_app_file_picker_and_main_import_the_framework() -> None:
    """Over the real traktor_nml/gui/ tree, exactly app.py,
    file_picker.py and __main__.py import nicegui or pywebview -
    review_model.py, wizard_state.py and __init__.py import neither
    (docs/nicegui-gui-analysis.md #5; traktor_nml/README.md DL-069)."""
    found = _framework_importing_modules(_module_files())
    assert found == {"app.py", "file_picker.py", "__main__.py"}


def test_synthetic_fourth_module_is_caught(tmp_path: Path) -> None:
    """Negative control for the guard above: copies the real gui/
    modules' sources into a scratch directory alongside one synthetic
    module importing nicegui, and records the walk reporting that
    fourth module as an addition to the expected three.

    Observed to fail (the extra module absent from the reported set) if
    _framework_importing_modules only checked module names against an
    allowlist instead of actually parsing each file's imports - run
    against this synthetic module, which is named review_model_extra.py
    precisely so a name-based check would misclassify it as one of the
    already-allowed three.
    """
    scratch = tmp_path / "gui_copy"
    scratch.mkdir()
    for path in _module_files():
        (scratch / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    (scratch / "review_model_extra.py").write_text("import nicegui\n", encoding="utf-8")

    files = sorted(p for p in scratch.glob("*.py"))
    found = _framework_importing_modules(files)

    assert "review_model_extra.py" in found
    assert found - {"app.py", "file_picker.py", "__main__.py"} == {"review_model_extra.py"}


def _transitive_imports(module_path: Path, seen: set[str]) -> set[str]:
    """Follows `from . import x` / `from .x import y` edges within
    traktor_nml/gui/ starting at module_path, collecting every
    framework root reached transitively - so a module that imports
    another gui/ module which in turn imports nicegui is still caught,
    not only a module importing nicegui directly."""
    if module_path.name in seen:
        return set()
    seen.add(module_path.name)
    if not module_path.exists():
        return set()
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
            elif node.level >= 1 and node.module:
                sibling = GUI_DIR / f"{node.module.split('.')[0]}.py"
                roots |= _transitive_imports(sibling, seen)
            elif node.level == 1:
                # `from . import x` - x may itself be a sibling module.
                for alias in node.names:
                    sibling = GUI_DIR / f"{alias.name}.py"
                    roots |= _transitive_imports(sibling, seen)
    return roots & _FRAMEWORK_ROOTS


def test_review_model_and_wizard_state_reach_no_framework_transitively() -> None:
    """review_model.py and wizard_state.py, followed through every
    gui/-internal import edge, never reach nicegui or pywebview -
    the decision rules stay reachable by a test on an interpreter
    without either installed."""
    assert _transitive_imports(GUI_DIR / "review_model.py", set()) == set()
    assert _transitive_imports(GUI_DIR / "wizard_state.py", set()) == set()


def test_review_model_importing_app_is_caught(tmp_path: Path) -> None:
    """Negative control for the guard above: splices `from . import
    app` onto a copy of review_model.py's source (no tracked file
    touched) inside a scratch traktor_nml/gui/ directory that also
    holds the real app.py, and records the walk then reporting nicegui
    reached transitively through that edge.
    """
    scratch = tmp_path / "gui_copy"
    scratch.mkdir()
    for path in _module_files():
        (scratch / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    mutated = (scratch / "review_model.py").read_text(encoding="utf-8") + "\n\nfrom . import app  # noqa\n"
    (scratch / "review_model.py").write_text(mutated, encoding="utf-8")

    global GUI_DIR
    original_gui_dir = GUI_DIR
    GUI_DIR = scratch
    try:
        found = _transitive_imports(scratch / "review_model.py", set())
    finally:
        GUI_DIR = original_gui_dir

    assert "nicegui" in found


def test_app_references_io_bound_not_the_process_pool_variant() -> None:
    """app.py's source names nicegui.run.io_bound for the scan and never
    the process-pool run.cpu_bound: cpu_bound dispatches into a process
    pool, and neither TagCache nor an lxml root pickles cleanly across
    that boundary (docs/nicegui-gui-analysis.md #4), so app.py must not
    reference the process-pool call at all.
    """
    source = APP_PATH.read_text(encoding="utf-8")
    assert "run.io_bound" in source
    assert "cpu_bound" not in source


def _find_write_reconnect_result_calls(tree: ast.AST) -> list[ast.Call]:
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name == "write_reconnect_result":
                calls.append(node)
    return calls


def _provider_function_def(tree: ast.AST, call: ast.Call) -> ast.FunctionDef:
    """The FunctionDef the call's second positional argument names - a
    Name resolved by finding the nearest FunctionDef of that name
    anywhere in the module, which is how app.py's inline
    `def provide_result(old_root): ...` defined just above the call
    resolves."""
    assert len(call.args) >= 2, "write_reconnect_result must be called with a provider as its second argument"
    provider_arg = call.args[1]
    assert isinstance(provider_arg, ast.Name), "the provider argument must be a plain name naming a function"
    provider_name = provider_arg.id
    candidates = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == provider_name
    ]
    assert candidates, f"no function named {provider_name!r} found in app.py"
    return candidates[0]


def _calls_amended_result(func_def: ast.FunctionDef) -> bool:
    for node in ast.walk(func_def):
        if isinstance(node, ast.Call):
            callee = node.func
            if isinstance(callee, ast.Attribute) and callee.attr == "amended_result":
                return True
            if isinstance(callee, ast.Name) and callee.id == "amended_result":
                return True
    return False


def test_write_control_provider_calls_amended_result() -> None:
    """An AST walk of app.py finds the call to write_reconnect_result
    and asserts its provider argument's function body contains a call
    to wizard_state.amended_result - the one connecting call the
    deliberately untested view module makes, and the one whose absence
    would silently discard every operator rejection while the write
    still reports success (traktor_nml/README.md DL-076).
    """
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = _find_write_reconnect_result_calls(tree)
    assert calls, "app.py must call reconnect_run.write_reconnect_result"
    provider = _provider_function_def(tree, calls[0])
    assert _calls_amended_result(provider)


def test_provider_returning_unamended_result_is_caught() -> None:
    """Negative control for the guard above: rewrites the provider's
    body in a copy of app.py's source to `return state.scan_result`
    instead of `return wizard_state.amended_result(...)` - exactly the
    silently-discarded-rejections wiring the guard exists to catch -
    and records that the same walk then reports no amended_result call.

    Observed to fail (an AssertionError from _calls_amended_result
    returning True) if the mutation below failed to remove every
    amended_result call from the provider's body; confirmed instead
    that the mutated source's provider is reported to make no such
    call, while the guard against the real source above passes.
    """
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = _find_write_reconnect_result_calls(tree)
    provider = _provider_function_def(tree, calls[0])

    mutated_provider = ast.parse(
        "def provide_result(old_root):\n"
        "    return state.scan_result\n"
    ).body[0]
    mutated_provider.name = provider.name

    class _Replace(ast.NodeTransformer):
        def visit_FunctionDef(self, node):  # noqa: N802 - ast API name
            if node is provider:
                return mutated_provider
            self.generic_visit(node)
            return node

    mutated_tree = _Replace().visit(tree)
    ast.fix_missing_locations(mutated_tree)

    mutated_calls = _find_write_reconnect_result_calls(mutated_tree)
    mutated_provider_def = _provider_function_def(mutated_tree, mutated_calls[0])
    assert not _calls_amended_result(mutated_provider_def)


def _calls_qualified(func_def: ast.FunctionDef, module_name: str, attr_name: str) -> bool:
    """Whether func_def's body calls module_name.attr_name - an
    Attribute call whose value is the bare Name module_name, so
    `assemble_output(...)` alone (splice.py's own, imported unqualified
    into app.py) does not satisfy a check for `buildplaylist.
    assemble_output(...)`."""
    for node in ast.walk(func_def):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == attr_name
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == module_name
        ):
            return True
    return False


def test_build_playlist_page_calls_assemble_output() -> None:
    """_run_build_playlist, the function the build-playlist screen's
    write control drives under run.io_bound, calls
    buildplaylist.assemble_output - the module-qualified call, not
    app.py's own unqualified assemble_output name, which splice.py's
    reconstruct assembly already owns (DL-262).

    Mutation: a copy of app.py's _run_build_playlist body had its
    `buildplaylist.assemble_output(...)` call rewritten to the bare,
    unqualified `assemble_output(...)` - splice.py's own function,
    imported unqualified into app.py - and the same walk run over it.
    Observed:
        AssertionError: assert False
    """
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    candidates = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_run_build_playlist"
    ]
    assert candidates, "_run_build_playlist not found in app.py"
    assert _calls_qualified(candidates[0], "buildplaylist", "assemble_output")

    mutated = ast.parse(
        source.replace(
            "buildplaylist.assemble_output(",
            "assemble_output(",
        )
    )
    mutated_candidates = [
        node for node in ast.walk(mutated)
        if isinstance(node, ast.FunctionDef) and node.name == "_run_build_playlist"
    ]
    assert not _calls_qualified(mutated_candidates[0], "buildplaylist", "assemble_output")

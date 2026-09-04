#!/usr/bin/env python3
"""The cheap checks worth running at the start of a working session.

Three of this project's controls are silent when they fail. The pre-push
hook is tracked but inert until `core.hooksPath` is set, and an inert hook
looks exactly like a working one. The three repositories are resolved as
siblings, so a missing one degrades a later step rather than failing at it.
`gui/app.py` is CRLF against an otherwise-LF tree, and an editor that
normalises it leaves a diff touching every line. None of the three announces
itself; each is reported here.

This is deliberately fast - no suite, no browser - so it costs nothing to
run before anything else. The suite is the slow check and is run on its
own: `python -m pytest tests/ -q` under the system interpreter.

Exit status is 1 if anything is wrong, so this can gate a session the way
--check gates a rewrite. Every check runs regardless of what an earlier one
found: a session wants the whole list, not the first item on it.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# WIZARD is not overridable: this file lives in it, so tools/../ is the only
# tree it can be describing.
WIZARD = Path(__file__).resolve().parent.parent
_SIBLINGS = WIZARD.parent


def _sibling(env: str, name: str) -> Path:
    """A repository beside WIZARD, or wherever `env` points instead.

    Nothing is checked here; check_repos reports a path that is absent or
    is not a repository, so every location reaches the report rather than
    raising out of resolution.
    """
    override = os.environ.get(env)
    return Path(override).expanduser().resolve() if override else _SIBLINGS / name


PLAN = _sibling("TRAKTOR_NML_TOOL_PLAN", "traktor-nml-tool-plan")
GATE = _sibling("TRAKTOR_NML_TOOL_GATE", "traktor-nml-tool-gate")
APP_PY = WIZARD / "traktor_nml" / "gui" / "app.py"


def _line_endings(path: Path) -> tuple[int, int]:
    """(CRLF count, bare LF count) for path."""
    data = path.read_bytes()
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf
OPTIONAL = ("nicegui", "webview", "pyacoustid", "mutagen", "lxml")

OK, BAD = "ok  ", "BAD "


def _report(good: bool, line: str) -> bool:
    print(f"{OK if good else BAD}{line}")
    return good


def check_interpreter() -> bool:
    """Name the interpreter and what it carries. Never fails.

    Both interpreters here are legitimate - the system one for the suite,
    .venv for serving - so there is nothing to fail on. What matters is that
    which one is in play is stated rather than assumed.
    """
    present = [n for n in OPTIONAL if importlib.util.find_spec(n) is not None]
    serves = "nicegui" in present
    _report(True, f"interpreter: {sys.executable}")
    _report(True, f"carries: {', '.join(present) or 'none'} "
                  f"({'serves the app' if serves else 'runs the suite'})")
    return True


def check_hooks() -> bool:
    """core.hooksPath points at the tracked hooks/ and pre-push is there."""
    result = subprocess.run(
        ["git", "-C", str(WIZARD), "config", "core.hooksPath"],
        capture_output=True, text=True,
    )
    configured = result.stdout.strip()
    hook = WIZARD / "hooks" / "pre-push"
    if not hook.is_file():
        return _report(False, f"hooks: {hook} is absent")
    if configured != "hooks":
        return _report(
            False,
            "hooks: core.hooksPath is "
            f"{configured or 'unset'}, so hooks/pre-push is inert. "
            "Fix with: git config core.hooksPath hooks",
        )
    return _report(True, "hooks: core.hooksPath=hooks, pre-push present")


def check_repos() -> bool:
    """The three repositories resolve and are readable git trees."""
    good = True
    for name, repo in (("wizard", WIZARD), ("plan", PLAN), ("gate", GATE)):
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            good = _report(False, f"{name}: {repo} is not a readable git repository") and good
        else:
            _report(True, f"{name}: {result.stdout.strip()}  {repo}")
    return good


def check_line_endings() -> bool:
    """app.py is wholly CRLF; a bare LF in it is the editor that ate it."""
    if not APP_PY.is_file():
        return _report(False, f"line endings: {APP_PY} is absent")
    crlf, bare_lf = _line_endings(APP_PY)
    if bare_lf:
        return _report(
            False,
            f"line endings: app.py has {bare_lf} bare LF among {crlf} CRLF "
            "and must be wholly CRLF. Read and write it with newline=''.",
        )
    return _report(True, f"line endings: app.py {crlf} CRLF, 0 bare LF")


CHECKS = (check_interpreter, check_hooks, check_repos, check_line_endings)


def main() -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    results = [check() for check in CHECKS]
    if all(results):
        print("\npreflight clean. The suite is not run here - "
              "python -m pytest tests/ -q covers that.")
        return 0
    print(f"\n{results.count(False)} check(s) failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

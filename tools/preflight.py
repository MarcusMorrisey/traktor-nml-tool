#!/usr/bin/env python3
"""The cheap checks worth running at the start of a working session.

Three of this project's controls are silent when they fail. The pre-push
hook is tracked but inert until `core.hooksPath` is set, and an inert hook
looks exactly like a working one. The three repositories are resolved as
siblings, so a missing one degrades a later step rather than failing at it.
`gui/app.py` is CRLF against an otherwise-LF tree, and an editor that
normalises it leaves a diff touching every line. None of the three announces
itself; each is reported here.

This is deliberately fast - no suite, no browser. `tools/refresh_handoff.py`
covers what is slow: it runs the full suite to derive the pass and skip
counts, and rewrites the handoff's derived facts. Run this at the start of a
session and that one before writing the handoff at the end.

Exit status is 1 if anything is wrong, so this can gate a session the way
--check gates a rewrite. Every check runs regardless of what an earlier one
found: a session wants the whole list, not the first item on it.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from refresh_handoff import GATE, HANDOFF, PLAN, WIZARD, _line_endings  # noqa: E402

# Imported rather than restated: preflight and the handoff refresh must agree
# on where the four locations are, and one resolution rule is what makes that
# true by construction instead of by matching literals in two files.

APP_PY = WIZARD / "traktor_nml" / "gui" / "app.py"
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
    if not HANDOFF.is_file():
        good = _report(False, f"handoff: {HANDOFF} is absent") and good
    else:
        _report(True, f"handoff: {HANDOFF}")
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
        print("\npreflight clean. The suite and the handoff's derived facts "
              "are not checked here - run tools/refresh_handoff.py --check "
              "for those.")
        return 0
    print(f"\n{results.count(False)} check(s) failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

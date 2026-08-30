#!/usr/bin/env python3
"""Refresh the derivable facts in the reconnect wizard's handoff document.

`CONTINUE-traktor-wizard.md` is the first thing a new session reads, and it
sits outside every repository, so nothing makes it stale loudly. Its prose -
the traps, the project rules, the deferrals, the reasoning - is judgement and
is never touched here. Its *facts* are all derivable from the three
repositories, and those are what this rewrites:

    the three repository HEADs, the suite's pass/skip counts, the decision
    log's high-water mark, the number of tests/test_gui_*.py files, and
    app.py's CRLF and bare-LF counts

Each fact is located by an exact anchor pattern. An anchor that no longer
matches is reported rather than guessed at, because a silently skipped field
is the failure this exists to prevent - the document reading as current while
one of its numbers is not.

Run with --check to report drift and write nothing; the exit code is 1 when
anything is stale, so a hook or a CI step can use it.

The suite is run under the interpreter that runs this script, and that must
be the SYSTEM interpreter rather than .venv: .venv carries extra packages and
reports a different skip count. A system interpreter carrying nicegui or
webview would also make tests/test_cli_without_nicegui.py and
tests/test_gui_import_isolation.py meaningless, so both are refused outright
rather than reported as a mismatch.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import re
import subprocess
import sys
from pathlib import Path

WIZARD = Path("C:/codex/traktor-nml-tool")
PLAN = Path("C:/codex/traktor-nml-tool-plan")
GATE = Path("C:/codex/traktor-nml-tool-gate")
HANDOFF = Path("C:/codex/CONTINUE-traktor-wizard.md")
APP_PY = WIZARD / "traktor_nml" / "gui" / "app.py"
DECISION_LOG = WIZARD / "traktor_nml" / "README.md"


class Stale(Exception):
    """A fact could not be derived, so no field depending on it is written."""


def _git_head(repo: Path) -> str:
    """The short HEAD of repo, or a Stale if it is not a git repository."""
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise Stale(f"{repo} is not a readable git repository: {result.stderr.strip()}")
    return result.stdout.strip()


def _suite_counts() -> tuple[int, int]:
    """(passed, skipped) from a full run under this interpreter."""
    for module in ("nicegui", "webview"):
        if importlib.util.find_spec(module) is not None:
            raise Stale(
                f"this interpreter carries {module}, so it is not the SYSTEM "
                "interpreter the handoff's suite counts are measured under"
            )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=WIZARD, capture_output=True, text=True,
    )
    match = re.search(r"(\d+) passed(?:, (\d+) skipped)?", result.stdout)
    if match is None:
        raise Stale("no pass/skip summary in the pytest output")
    return int(match.group(1)), int(match.group(2) or 0)


def _decision_high_water() -> str:
    """The highest DL-NNN in the decision log, as it is written there."""
    text = DECISION_LOG.read_text(encoding="utf-8")
    ids = [int(n) for n in re.findall(r"DL-(\d{3})", text)]
    if not ids:
        raise Stale(f"no DL-NNN identifiers in {DECISION_LOG}")
    return f"DL-{max(ids):03d}"


def _line_endings(path: Path) -> tuple[int, int]:
    """(CRLF count, bare LF count) for path."""
    data = path.read_bytes()
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf


def _gui_test_count() -> int:
    return len(list((WIZARD / "tests").glob("test_gui_*.py")))


def gather() -> tuple[dict, list[str]]:
    """Every derivable fact, plus the reasons any of them could not be read.

    Each fact is gathered independently so one unreadable source does not
    suppress the rest: a missing plan repository should not stop the suite
    count being refreshed.
    """
    facts: dict = {}
    problems: list[str] = []

    for key, repo in (("wizard_head", WIZARD), ("plan_head", PLAN), ("gate_head", GATE)):
        try:
            facts[key] = _git_head(repo)
        except Stale as exc:
            problems.append(str(exc))

    for key, reader in (
        ("decisions", _decision_high_water),
        ("suite", _suite_counts),
    ):
        try:
            facts[key] = reader()
        except Stale as exc:
            problems.append(str(exc))

    if APP_PY.exists():
        facts["app_py"] = _line_endings(APP_PY)
    else:
        problems.append(f"{APP_PY} is absent")
    facts["gui_tests"] = _gui_test_count()
    return facts, problems


def edits_for(facts: dict) -> list[tuple[str, str, str]]:
    """(label, pattern, replacement) per field, for the facts that were read.

    Each pattern anchors on surrounding literal text rather than on a line
    number, so reordering the document does not silently retarget an edit.
    """
    edits: list[tuple[str, str, str]] = []
    rows = (
        ("wizard head", r"traktor-nml-tool` \| `", "wizard_head", r"the wizard \|"),
        ("plan head", r"traktor-nml-tool-plan` \| `", "plan_head", r"the plan,"),
        ("gate head", r"traktor-nml-tool-gate` \| `", "gate_head", r"the gate,"),
    )
    for label, prefix, key, suffix in rows:
        if key in facts:
            edits.append((
                label,
                rf"({prefix})[0-9a-f]{{7,40}}(` \| {suffix})",
                rf"\g<1>{facts[key]}\g<2>",
            ))
    if "suite" in facts:
        passed, skipped = facts["suite"]
        edits.append((
            "suite counts",
            r"Suite: \*\*\d+ passed, \d+ skipped\*\*",
            f"Suite: **{passed} passed, {skipped} skipped**",
        ))
    if "decisions" in facts:
        edits.append((
            "decision high-water",
            r"decision log runs to \*\*DL-\d{3}\*\*",
            f"decision log runs to **{facts['decisions']}**",
        ))
    if "app_py" in facts:
        crlf, bare = facts["app_py"]
        edits.append((
            "app.py line endings",
            r"is \*\*\d+ CRLF, \d+ bare LF\*\*",
            f"is **{crlf} CRLF, {bare} bare LF**",
        ))
    edits.append((
        "gui test count",
        r"There are \*\*\d+\*\* `tests/test_gui_\*\.py` files",
        f"There are **{facts['gui_tests']}** `tests/test_gui_*.py` files",
    ))
    return edits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true",
        help="Report drift and write nothing. Exits 1 when any fact is stale.",
    )
    args = parser.parse_args()

    if not HANDOFF.exists():
        print(f"handoff absent: {HANDOFF}", file=sys.stderr)
        return 2

    facts, problems = gather()
    # newline="" throughout: the handoff is LF and must stay LF on a platform
    # whose default would rewrite every line on save.
    text = io.open(HANDOFF, encoding="utf-8", newline="").read()

    changed: list[str] = []
    unmatched: list[str] = []
    for label, pattern, replacement in edits_for(facts):
        updated, count = re.subn(pattern, replacement, text, count=1)
        if count == 0:
            unmatched.append(label)
        elif updated != text:
            changed.append(label)
            text = updated

    for problem in problems:
        print(f"could not read: {problem}", file=sys.stderr)
    for label in unmatched:
        print(f"anchor not found, left alone: {label}", file=sys.stderr)

    if args.check:
        for label in changed:
            print(f"stale: {label}")
        if not changed and not unmatched and not problems:
            print("handoff is current")
        return 1 if (changed or unmatched or problems) else 0

    if changed:
        io.open(HANDOFF, "w", encoding="utf-8", newline="").write(text)
        for label in changed:
            print(f"updated: {label}")
    else:
        print("handoff is current")

    # Prose this cannot derive, named so it is checked by a person rather
    # than assumed current.
    print()
    print("not derivable, confirm by hand: the repo table's file counts, the "
          "browser-record count, the backlog, the deferrals, and whether the "
          "close-out narrative still describes the tree.")
    return 1 if (unmatched or problems) else 0


if __name__ == "__main__":
    raise SystemExit(main())

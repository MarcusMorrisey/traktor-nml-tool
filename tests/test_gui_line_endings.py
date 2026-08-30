"""Guards that traktor_nml/gui/app.py is wholly CRLF.

app.py is the one module in this tree stored with CRLF endings, against
320 LF files around it. Nothing in the suite asserted that before this
test: tests/test_gui_module_imports.py reads and writes it with
newline="" and its comment says "app.py is 100% CRLF", but preserving
the endings while doing something else is not the same as checking
them, and a comment is not a guard.

What the absence allowed: an editor or a script that reads app.py in
text mode and writes it back gets os.linesep for every line, which on a
non-Windows host silently converts all 1388 endings to LF. The suite
stays green - no test reads the bytes - and the resulting diff touches
every line of the file, burying whatever change was intended.
.gitattributes' `* -text` stops git from doing this, but not an editor,
and `* -text` was itself absent until recently.

The rule is one-directional on purpose. app.py must be wholly CRLF;
this says nothing about any other file, because the tree is
deliberately not uniform - the patch sets under docs/plans/*/scratch/
are CRLF too, for their own reason, and the parity manifest is pinned
by SHA-256 over its exact bytes.

Observed to fail against a real mutation: replacing the first three
CRLF in a copy of app.py with bare LF
(`b.replace(b"\r\n", b"\n", 3)`) and running this test raised:
    AssertionError: traktor_nml/gui/app.py has 3 bare LF among 1385
    CRLF and must be wholly CRLF (1388 CRLF, 0 bare LF)
The file was restored from the copy taken beforehand, never via
`git checkout`, and re-running confirmed it passes at 1388 CRLF.
"""

from __future__ import annotations

from pathlib import Path

APP_PY = Path(__file__).parent.parent / "traktor_nml" / "gui" / "app.py"


def test_app_py_is_wholly_crlf() -> None:
    raw = APP_PY.read_bytes()
    crlf = raw.count(b"\r\n")
    bare_lf = raw.count(b"\n") - crlf
    assert bare_lf == 0, (
        f"traktor_nml/gui/app.py has {bare_lf} bare LF among {crlf} CRLF "
        f"and must be wholly CRLF. Read and write it with newline=''."
    )
    assert crlf > 0, "app.py has no CRLF at all; it has been normalised to LF"

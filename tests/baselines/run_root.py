"""Run-directory normalisation for the two parity surfaces that cannot
avoid it.

`rewrite-from-reconnect` reconstructs each matched candidate's LOCATION
from its resolved absolute path, so a rewritten DIR embeds the directory
the run happened in:

    DIR="/:tmp/:pytest-of-you/:pytest-31/:recon/:audio/:moved/:"

That directory differs between the regeneration run and every later test
run, so such a case can never be compared byte-for-byte as captured. The
alternative - omitting a matched-writing case - would leave the rewritten
LOCATION bytes unpinned, which is precisely what the renderer split could
break, so the case is kept and the run directory alone is substituted.

Both the writer (regenerate.py) and the reader (test_baseline_parity.py)
call these functions, so the two can never disagree about what was
relaxed. Normalisation is opt-in per case via the manifest's
"normalise_run_root" field: every other case stays provably strict, and
`test_normalised_case_still_detects_a_non_run_root_byte_change` proves
the relaxation is confined to the run directory.
"""

from __future__ import annotations

from pathlib import Path

RUN_ROOT_TOKEN = "{RUN_ROOT}"


def _run_root_forms(run_dir: Path) -> list[str]:
    """Every spelling of run_dir that can reach a compared surface.

    Three forms, longest first so no shorter form can consume a prefix of
    a longer one:

    - native      - str(run_dir), backslash-separated on Windows
    - posix       - run_dir.as_posix(), what the tool now prints
    - encoded     - the Traktor DIR encoding diskscan builds, which drops
                    the filesystem anchor and joins the remaining parts
                    with "/:" (see diskscan.py)

    Built as an explicit ordered list rather than from a set, so the
    ordering is fixed rather than dependent on set iteration under
    PYTHONHASHSEED.
    """
    resolved = run_dir.resolve()
    native = str(resolved)
    posix = resolved.as_posix()
    encoded = "/:" + "/:".join(resolved.parts[1:]) if resolved.parts[1:] else ""

    forms: list[str] = []
    for form in (native, posix, encoded):
        if form and form not in forms:
            forms.append(form)
    return sorted(forms, key=len, reverse=True)


def normalise_run_root(text: str, run_dir: Path) -> str:
    """Replace every spelling of run_dir in text with RUN_ROOT_TOKEN."""
    for form in _run_root_forms(run_dir):
        text = text.replace(form, RUN_ROOT_TOKEN)
    return text


def normalise_run_root_bytes(data: bytes, run_dir: Path) -> bytes:
    """Byte-level counterpart for written NML files.

    Decoded as UTF-8 because every file this tool writes is UTF-8 and the
    substituted forms are path text; a file that failed to decode would be
    a defect worth surfacing here rather than silently passing through.
    """
    return normalise_run_root(data.decode("utf-8"), run_dir).encode("utf-8")

"""Byte-level parity oracle against the reference tool's recorded output.

manifest.json records the tool's stdout, exit code and every written
file's bytes for a fixed set of invocations; its schema and the rules
governing it live in tests/baselines/manifest.schema.md. Regenerating
it is correct only against a deliberate, reviewed behavior change -
never to make a failing test pass, since that would silently rewrite
the contract this test enforces.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from tests.baselines.run_root import normalise_run_root, normalise_run_root_bytes
from tests.conftest import run_tool

BASELINE_MANIFEST = Path(__file__).parent / "baselines" / "manifest.json"


def _load_manifest() -> list[dict]:
    """Loads the tool's recorded output contract. Regenerating
    manifest.json is correct only for a deliberate, reviewed behavior
    change - never to make a failing test pass."""
    return json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _load_manifest(), ids=lambda c: " ".join(c["argv"]))
def test_baseline_invocation_matches_stored_bytes(case: dict, fixture_corpus: Path, tmp_path: Path) -> None:
    """Re-runs one recorded invocation against the fixture corpus and
    compares exit code, stdout and every written file's bytes against the
    manifest's stored values."""
    (tmp_path / "out").mkdir(exist_ok=True)
    result = run_tool(case["argv"], cwd=tmp_path)

    # The same opt-in relaxation the manifest was written with, applied
    # through the same shared helper so writer and reader cannot disagree
    # about what was substituted (see tests/baselines/run_root.py).
    relax = case.get("normalise_run_root", False)
    stdout = normalise_run_root(result.stdout, tmp_path) if relax else result.stdout

    assert result.exit_code == case["exit_code"]
    assert stdout == case["stdout"]

    for rel_path, expected_b64 in case["output_files"].items():
        written = (tmp_path / rel_path).read_bytes()
        if relax:
            written = normalise_run_root_bytes(written, tmp_path)
        assert written == base64.b64decode(expected_b64), f"output mismatch for {rel_path}"


def test_deliberate_one_character_edit_fails_parity(fixture_corpus: Path, tmp_path: Path) -> None:
    """Sanity check on the oracle itself: corrupting one character of a
    stored baseline must make the real parity assertion fail - not just
    prove two arbitrary strings differ, but exercise the same comparison
    test_baseline_invocation_matches_stored_bytes makes, against a
    deliberately corrupted copy of the stored value."""
    case = _load_manifest()[0]
    (tmp_path / "out").mkdir(exist_ok=True)
    result = run_tool(case["argv"], cwd=tmp_path)

    corrupted_case = dict(case)
    corrupted_case["stdout"] = case["stdout"][:-1] + ("X" if not case["stdout"].endswith("X") else "Y")

    with pytest.raises(AssertionError):
        assert result.exit_code == corrupted_case["exit_code"]
        assert result.stdout == corrupted_case["stdout"]
        for rel_path, expected_b64 in corrupted_case["output_files"].items():
            written = (tmp_path / rel_path).read_bytes()
            assert written == base64.b64decode(expected_b64), f"output mismatch for {rel_path}"


def test_no_stored_stream_carries_a_host_path_separator() -> None:
    """Portability guard: no captured stdout or stderr may contain a
    backslash.

    The tool prints paths via Path.as_posix(), so every path it emits is
    forward-slash regardless of host. A backslash in a stored stream means
    some print site interpolates a Path directly again, which silently
    pins the manifest to the OS that captured it: the same invocation then
    fails everywhere else with no diagnostic distinguishing "wrong host"
    from "tool regression", and the obvious fix - regenerating - destroys
    the recorded contract this oracle exists to hold.

    Checked here rather than by running the suite once on another OS,
    because a one-off run proves today while this fails on the commit that
    reintroduces the problem.
    """
    offenders = [
        (case["argv"], stream_name, line)
        for case in _load_manifest()
        for stream_name in ("stdout", "stderr")
        for line in case[stream_name].splitlines()
        if "\\" in line
    ]
    assert not offenders, (
        "host path separator in stored stream(s); print the path with "
        f"Path.as_posix() and regenerate: {offenders}"
    )


def test_normalised_case_still_detects_a_non_run_root_byte_change(
    fixture_corpus: Path, tmp_path: Path
) -> None:
    """Run-root normalisation must not relax anything but the run root.

    Anchored deliberately: it first asserts the substitution round-trips
    EXACTLY, then that a change outside the run-root prefix still fails.
    Without the first assertion the test would pass even if normalisation
    replaced the whole file, which would leave the rewritten LOCATION
    bytes unguarded while looking green.
    """
    case = next(
        (c for c in _load_manifest() if c.get("normalise_run_root") and c["output_files"]),
        None,
    )
    assert case is not None, "no normalised case with an output file in the manifest"

    (tmp_path / "out").mkdir(exist_ok=True)
    run_tool(case["argv"], cwd=tmp_path)

    rel_path, expected_b64 = next(iter(case["output_files"].items()))
    expected = base64.b64decode(expected_b64)
    written = normalise_run_root_bytes((tmp_path / rel_path).read_bytes(), tmp_path)

    # 1. the substitution round-trips exactly
    assert written == expected, f"normalised output did not round-trip for {rel_path}"

    # 2. and a byte OUTSIDE the run-root prefix is still caught. The
    #    filename is well clear of the substituted prefix.
    assert b"xtal_recon.mp3" in expected, "fixture filename missing from stored output"
    mutated = expected.replace(b"xtal_recon.mp3", b"xtal_recoNN.mp3")
    assert mutated != expected
    assert written != mutated, "normalisation masked a change outside the run root"

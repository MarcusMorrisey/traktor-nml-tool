"""Byte-level parity oracle against the reference tool's recorded output.

manifest.json (DL-002) records the tool's stdout, exit code and every
written file's bytes for a fixed set of invocations. Regenerating it is
correct only against a deliberate, reviewed behavior change - never to
make a failing test pass, since that would silently rewrite the contract
this test enforces.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from tests.conftest import run_tool

BASELINE_MANIFEST = Path(__file__).parent / "baselines" / "manifest.json"


def _load_manifest() -> list[dict]:
    """Loads the tool's recorded output contract (DL-002). Regenerating
    manifest.json is correct only for a deliberate, reviewed behavior
    change - never to make a failing test pass."""
    return json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _load_manifest(), ids=lambda c: " ".join(c["argv"]))
def test_baseline_invocation_matches_stored_bytes(case: dict, fixture_corpus: Path, tmp_path: Path) -> None:
    """Re-runs one recorded invocation against the fixture corpus and
    compares exit code, stdout and every written file's bytes against the
    manifest's stored values (DL-011)."""
    (tmp_path / "out").mkdir(exist_ok=True)
    result = run_tool(case["argv"], cwd=tmp_path)

    assert result.exit_code == case["exit_code"]
    assert result.stdout == case["stdout"]

    for rel_path, expected_b64 in case["output_files"].items():
        written = (tmp_path / rel_path).read_bytes()
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

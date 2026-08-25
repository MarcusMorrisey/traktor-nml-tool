"""Tamper-evidence for the parity oracle itself.

test_baseline_parity.py checks the tool against manifest.json. Nothing
there checks the manifest, so regenerating it silently rewrites the
contract the oracle exists to hold: a failing parity test goes green and
the pre-refactor behaviour is unrecoverable. This module pins the
manifest's own bytes.

The pin is a literal constant rather than a git comparison so it runs
under plain pytest, identically in CI, in a shallow clone, and on a
developer's machine. Changing it is a one-line diff to a file named for
the purpose - the escalation path, not an accident.

WHEN THE CONSTANT MAY MOVE
--------------------------
Only alongside a reviewed regeneration and a new parity-baseline-vN tag,
in a commit that changes nothing but manifest.json and this constant and
names the behaviour change in its message. Updating both together to
clear a red test is the exact substitution this module exists to prevent.

HOW IT IS DERIVED
-----------------
    python -m tests.baselines.regenerate
    python -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('tests/baselines/manifest.json').read_bytes()).hexdigest())"

Taken from that regeneration run, never from whatever manifest happens to
be on disk.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

MANIFEST_PATH = Path(__file__).parent / "baselines" / "manifest.json"

# parity-baseline-v1. See "WHEN THE CONSTANT MAY MOVE" above.
PARITY_BASELINE_SHA256 = "b6e17cf08f2dae5044b215509c19b32a8aee14742b933cc5b95749d82a165844"


def _assert_manifest_matches(manifest_path: Path, expected_sha256: str) -> None:
    """The single comparison both the guard and its meta-test run.

    Extracted so the meta-test exercises the real assertion against a
    mutated copy rather than a lookalike of it: a guard only ever seen to
    pass is indistinguishable from one that cannot fail.
    """
    actual = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert actual == expected_sha256, (
        f"parity oracle changed: {manifest_path.name} hashes to {actual}, "
        f"pinned at {expected_sha256}.\n"
        "If you did not intend to change the tool's recorded output, revert "
        "the change rather than this constant.\n"
        "If you did, that is a deliberate behaviour change: regenerate under "
        "review, move PARITY_BASELINE_SHA256 in the same commit, and cut a new "
        "parity-baseline-vN tag. Never update both merely to clear a red test."
    )


def test_manifest_matches_pinned_hash() -> None:
    """The committed manifest still hashes to the pinned baseline."""
    _assert_manifest_matches(MANIFEST_PATH, PARITY_BASELINE_SHA256)


def test_one_character_edit_on_disk_fails_the_guard(tmp_path: Path) -> None:
    """Mutating one character of the manifest ON DISK must fail the guard.

    Deliberately not an in-memory check: the acceptance criterion is
    stated over a file on disk, and a meta-test that mutates a string
    would leave the real file-reading path unproven.
    """
    copied = tmp_path / MANIFEST_PATH.name
    shutil.copyfile(MANIFEST_PATH, copied)

    # Flip one byte in the middle, well away from any structural edge, so
    # the file stays valid JSON and only its content differs.
    data = bytearray(copied.read_bytes())
    midpoint = len(data) // 2
    data[midpoint] = ord("X") if data[midpoint] != ord("X") else ord("Y")
    copied.write_bytes(bytes(data))

    assert copied.read_bytes() != MANIFEST_PATH.read_bytes(), "mutation did not land"

    with pytest.raises(AssertionError, match="parity oracle changed"):
        _assert_manifest_matches(copied, PARITY_BASELINE_SHA256)


def test_unmutated_copy_still_passes_the_guard(tmp_path: Path) -> None:
    """Control for the meta-test above: an untouched copy passes.

    Without this, the mutation test could pass for the wrong reason - a
    guard that rejects every path it is handed would satisfy it.
    """
    copied = tmp_path / MANIFEST_PATH.name
    shutil.copyfile(MANIFEST_PATH, copied)
    _assert_manifest_matches(copied, PARITY_BASELINE_SHA256)

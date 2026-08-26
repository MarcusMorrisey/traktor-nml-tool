"""Owned fpcalc child: timeout, termination, and mid-fingerprint cancel.

Merge gates for the parts of section 3.5 of docs/nicegui-gui-analysis.md that
were unreachable while fingerprinting went through acoustid.fingerprint_file -
that helper exposes neither a timeout nor a handle on the process it spawns,
so there was nothing to time out and nothing to terminate.

Determinism comes from a stub fpcalc that blocks for a controlled duration, so
no test here depends on finding a genuinely slow audio file. The stub is
selected through the FPCALC environment variable, which is pyacoustid's own
override and therefore the real lookup path rather than a monkeypatch.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from traktor_nml.fingerprint import FpcalcSession, _parse_fpcalc_output

# Section 3.5's bound: from the moment cancel is signalled the core returns
# within fpcalc_grace + 2s, and never more than 15s.
HARD_BOUND_SECONDS = 15.0


def _stub_fpcalc(tmp_path: Path, body: str) -> Path:
    """A fake fpcalc: a Python script plus a launcher the session can exec.

    Written as a .py driven by this interpreter rather than a shell script,
    so it behaves the same way regardless of what shell is present.
    """
    script = tmp_path / "stub_fpcalc.py"
    script.write_text(body, encoding="utf-8")
    if sys.platform == "win32":
        launcher = tmp_path / "fpcalc.bat"
        launcher.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
    else:
        launcher = tmp_path / "fpcalc"
        launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        launcher.chmod(0o755)
    return launcher


BLOCKS_FOREVER = "import time\nwhile True:\n    time.sleep(0.05)\n"
ANSWERS = (
    "import sys\n"
    "sys.stdout.buffer.write(b'DURATION=212\\nFINGERPRINT=AQAAAAmkRUmSREmSREmS\\n')\n"
)


# --- parsing (no child needed) -------------------------------------------


def test_parses_the_fields_pyacoustid_parses() -> None:
    parsed = _parse_fpcalc_output(b"DURATION=212.5\nFINGERPRINT=AQAAAA\n")
    assert parsed == (212.5, "AQAAAA")


@pytest.mark.parametrize(
    "output",
    [b"", b"FINGERPRINT=AQAAAA\n", b"DURATION=212.5\n", b"DURATION=nonsense\nFINGERPRINT=AQAAAA\n"],
    ids=["empty", "no-duration", "no-fingerprint", "duration-not-numeric"],
)
def test_incomplete_output_is_absence_not_a_crash(output: bytes) -> None:
    """One unreadable file must not stop a scan, so a malformed answer is
    None for the caller to count - never an exception up the scan loop."""
    assert _parse_fpcalc_output(output) is None


# --- timeout --------------------------------------------------------------


def test_a_blocked_child_times_out_and_the_scan_continues(tmp_path: Path, monkeypatch) -> None:
    """Section 3.5: a single pathological file must not stall a 20-minute run.

    The old code could not express this - acoustid.fingerprint_file offers no
    timeout, so a file that never returns blocked the scan forever.
    """
    monkeypatch.setenv("FPCALC", str(_stub_fpcalc(tmp_path, BLOCKS_FOREVER)))
    session = FpcalcSession(timeout=1.0, grace=2.0)
    stats: dict[str, int] = {}

    started = time.time()
    result = session.fingerprint(tmp_path / "whatever.mp3", stats)
    elapsed = time.time() - started

    assert result is None
    assert stats["fingerprint_timeout"] == 1
    assert elapsed < HARD_BOUND_SECONDS
    assert session.child_pid is None, "a child survived the timeout"


def test_the_session_keeps_working_after_a_timeout(tmp_path: Path, monkeypatch) -> None:
    """Continuing is the point: the file is counted and the run goes on."""
    monkeypatch.setenv("FPCALC", str(_stub_fpcalc(tmp_path, BLOCKS_FOREVER)))
    session = FpcalcSession(timeout=1.0, grace=2.0)
    stats: dict[str, int] = {}
    session.fingerprint(tmp_path / "a.mp3", stats)
    session.fingerprint(tmp_path / "b.mp3", stats)
    assert stats["fingerprint_timeout"] == 2


# --- cancellation ---------------------------------------------------------


def test_cancel_terminates_a_child_already_mid_fingerprint(tmp_path: Path, monkeypatch) -> None:
    """The finding-2 completion condition.

    A cooperative token checked between files can never interrupt a call
    already blocked inside fpcalc; owning the child is what makes this
    possible at all. The bound is wall-clock because a blocked child emits
    no callbacks, so a bound counted in callbacks could never trip.
    """
    monkeypatch.setenv("FPCALC", str(_stub_fpcalc(tmp_path, BLOCKS_FOREVER)))
    session = FpcalcSession(timeout=120.0, grace=2.0)  # timeout far beyond the test
    stats: dict[str, int] = {}
    outcome: list = []

    worker = threading.Thread(
        target=lambda: outcome.append(session.fingerprint(tmp_path / "slow.mp3", stats))
    )
    worker.start()

    # Wait until the child is confirmed running, so this tests termination
    # rather than a race that cancelled before anything spawned.
    deadline = time.time() + 10
    while session.child_pid is None and time.time() < deadline:
        time.sleep(0.02)
    pid = session.child_pid
    assert pid is not None, "stub fpcalc never started"

    signalled = time.time()
    session.terminate()
    worker.join(timeout=HARD_BOUND_SECONDS)
    elapsed = time.time() - signalled

    assert not worker.is_alive(), "fingerprint did not return after cancel"
    assert elapsed < HARD_BOUND_SECONDS, f"took {elapsed:.1f}s, bound is {HARD_BOUND_SECONDS}s"
    assert outcome == [None]
    assert session.child_pid is None, "the child slot still holds a process"
    assert not _pid_alive(pid), f"fpcalc child {pid} survived cancellation"


def test_a_terminated_session_refuses_to_start_more_children(tmp_path: Path, monkeypatch) -> None:
    """Otherwise a cancel racing the next file starts a child nobody reaps."""
    monkeypatch.setenv("FPCALC", str(_stub_fpcalc(tmp_path, BLOCKS_FOREVER)))
    session = FpcalcSession(timeout=1.0, grace=1.0)
    session.terminate()
    started = time.time()
    assert session.fingerprint(tmp_path / "a.mp3", {}) is None
    assert time.time() - started < 1.0, "it waited on a child it should not have spawned"
    assert session.child_pid is None


def test_terminate_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FPCALC", str(_stub_fpcalc(tmp_path, BLOCKS_FOREVER)))
    session = FpcalcSession(timeout=1.0, grace=1.0)
    session.terminate()
    session.terminate()
    assert session.child_pid is None


def test_terminate_on_an_idle_session_is_harmless(tmp_path: Path) -> None:
    FpcalcSession().terminate()


# --- the working path -----------------------------------------------------


def test_a_answering_stub_is_parsed_into_a_fingerprint(tmp_path: Path, monkeypatch) -> None:
    """The replacement must still produce what the cascade consumes."""
    monkeypatch.setenv("FPCALC", str(_stub_fpcalc(tmp_path, ANSWERS)))
    session = FpcalcSession(timeout=30.0)
    result = session.fingerprint(tmp_path / "track.mp3", {})
    assert result is not None
    duration, fingerprint = result
    assert duration == 212.0
    assert fingerprint.startswith("AQAAAA")


def test_a_missing_binary_is_counted_not_raised(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FPCALC", str(tmp_path / "definitely-not-here"))
    stats: dict[str, int] = {}
    assert FpcalcSession().fingerprint(tmp_path / "track.mp3", stats) is None
    assert stats["fingerprint_errors"] == 1


def _pid_alive(pid: int) -> bool:
    """True if a process with this pid is still running."""
    if sys.platform == "win32":
        done = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True
        )
        return str(pid) in done.stdout
    try:
        import os

        os.kill(pid, 0)
    except OSError:
        return False
    return True

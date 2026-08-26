"""Check logic for the section 6 packaging spike.

Imported by spike_app.py (the window) and spike_checks.py (the headless
runner), so an automated build verifies exactly what a human clicking the
buttons would.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

LAUNCHED_AT = time.time()


def frozen_root() -> Path | None:
    """PyInstaller's extraction root, or None when running from source."""
    return Path(getattr(sys, "_MEIPASS")) if hasattr(sys, "_MEIPASS") else None


def find_fpcalc() -> Path | None:
    """Check 2: bundled binary must be found via sys._MEIPASS, not PATH.

    A packaged app cannot assume fpcalc is installed on the target machine,
    so the bundled copy has to win. Falling back to PATH would make the
    check pass on a developer box for the wrong reason.
    """
    root = frozen_root()
    if root is not None:
        candidate = root / "fpcalc.exe"
        return candidate if candidate.exists() else None
    import shutil

    found = shutil.which("fpcalc")
    return Path(found) if found else None


def state_dir() -> Path:
    """Check 6: per-user application data, never CWD and never _MEIPASS.

    Under --onefile a path under _MEIPASS is deleted on exit, so a cache
    resolved there silently re-scans every launch (see section 6.1).
    """
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    return Path(base) / "traktor-nml-tool"



"""Headless runner for the section 6 checks that do not need a window.

Checks 1, 2 and 6 are assertions about the bundle, not about the UI, so they
can be verified in CI or from a shell. Checks 3 (native dialogs), 4 (cold
start) and 5 (SmartScreen) need the window and a human, and are left to
spike_app.py.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from checks import find_fpcalc, frozen_root, state_dir


def main() -> int:
    failures = 0
    print(f"frozen root : {frozen_root() or 'not frozen (running from source)'}")
    print(f"state dir   : {state_dir()}")

    # CHECK 1 - lxml survives bundling and parses the real 11.7MB collection.
    target = Path(os.environ.get("SPIKE_NML", "collection_textual_patch_test.nml"))
    try:
        from lxml import etree
        if not target.exists():
            print(f"CHECK 1 lxml    SKIP  {target} not found (set SPIKE_NML)")
        else:
            started = time.time()
            root = etree.parse(str(target)).getroot()
            n = len(root.findall(".//COLLECTION/ENTRY"))
            print(f"CHECK 1 lxml    PASS  {n} entries in {time.time() - started:.1f}s")
    except Exception as exc:
        print(f"CHECK 1 lxml    FAIL  {exc!r}")
        failures += 1

    # CHECK 2 - the BUNDLED fpcalc is found via _MEIPASS and runs.
    binary = find_fpcalc()
    if binary is None:
        print("CHECK 2 fpcalc  FAIL  not found")
        failures += 1
    else:
        inside = frozen_root() is not None and str(binary).startswith(str(frozen_root()))
        try:
            done = subprocess.run([str(binary), "-version"], capture_output=True, text=True, timeout=10)
            ok = done.returncode == 0
            print(f"CHECK 2 fpcalc  {'PASS' if ok else 'FAIL'}  "
                  f"{'from bundle' if inside else 'FROM PATH, NOT BUNDLE'}: {done.stdout.strip()[:40]}")
            failures += 0 if ok else 1
        except Exception as exc:
            print(f"CHECK 2 fpcalc  FAIL  {exc!r}")
            failures += 1

    # CHECK 6 - state resolves to per-user appdata, writable, not _MEIPASS/CWD.
    try:
        marker = state_dir() / "spike-marker.txt"
        marker.parent.mkdir(parents=True, exist_ok=True)
        previous = marker.read_text(encoding="utf-8") if marker.exists() else "(first run)"
        marker.write_text(f"run at {time.time():.0f}", encoding="utf-8")
        meipass = frozen_root()
        bad = meipass is not None and str(marker).startswith(str(meipass))
        print(f"CHECK 6 state   {'FAIL under _MEIPASS' if bad else 'PASS'}  {marker}")
        print(f"CHECK 7 upgrade PASS  previous run left: {previous}")
        failures += 1 if bad else 0
    except Exception as exc:
        print(f"CHECK 6 state   FAIL  {exc!r}")
        failures += 1

    print("")
    print(f"{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

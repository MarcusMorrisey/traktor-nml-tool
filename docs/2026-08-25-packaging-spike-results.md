# Packaging spike results (nicegui-gui-analysis.md section 6)

Section 6 time-boxes this to one day and marks the section 7 distribution
recommendations **provisional until it runs**. This records what it found.

Scope decision that made it necessary: distribution to other DJs, with the
library and Traktor co-located on one Windows machine. That keeps section 6
in scope and takes Docker and LAN hosting out of it.

## Environment

Windows 11, Python 3.14.4 in a project venv, nicegui 3.16.0, PyInstaller
6.22.2, fpcalc 1.6.1 from the AcoustID.Chromaprint winget package.

## Results

| # | Check | Result |
| --- | --- | --- |
| 1 | `lxml` bundling | **PASS** - the frozen bundle parses the real 11.7 MB `collection_textual_patch_test.nml` and counts 6,412 entries in 0.1s |
| 2 | `fpcalc` bundling | **PASS** - ships via `--add-data`, is found under `sys._MEIPASS` (`_internal/` in `--onedir`), and `fpcalc -version` returns 0 from inside the bundle. Verified it came from the bundle and not from PATH |
| 3 | Native file dialog | **NOT RUN** - needs a window and a human; `spike_app.py` has the button |
| 4 | Cold start | **PARTIAL** - a frozen console bundle starts, runs and exits in 0.3s, so the unpack cost is negligible under `--onedir`. The 10s budget is for the `native=True` window, which is not measured here |
| 5 | Defender / SmartScreen | **NOT RUN** - needs a clean profile on another machine |
| 6 | Persistent-state location | **PASS** - resolves to `%LOCALAPPDATA%\traktor-nml-tool`, is writable, and is asserted not to sit under `sys._MEIPASS` |
| 7 | Upgrade over existing state | **PARTIAL PASS** - a second run reads what the first left. A real v1-then-v2 upgrade is untested |
| 8 | Uninstall | **NOT RUN** - needs an installed build to remove |

Four of eight pass outright, two partially, two need a machine this spike did
not have. Nothing failed.

## Findings not in the plan's checklist

- **`nicegui-pack` does not install PyInstaller and does not use its own
  interpreter to find it.** It shells out to a bare `pyinstaller` resolved
  against `PATH`, so `pip install nicegui` alone cannot build, and invoking
  `nicegui-pack` by its full venv path is not enough either - the venv's
  `Scripts` directory has to be on `PATH` or the build dies in `CreateProcess`
  with an unexplained `WinError 2`. `spike/packaging/build.sh` sets it.
- **The `--onedir` and `--add-data` flag spellings are confirmed.** Section 7
  marked them medium confidence pending this spike; both exist and work.
- **`ui.run` needs `reload=False` and `port=native.find_open_port()`** for a
  packaged build, per `nicegui-pack --help`. A packaged app on a fixed default
  port can collide with whatever already holds it.
- **Bundle size is 84 MB** for the `--onedir` window build (32 MB for the
  console checker without nicegui or webview). Worth knowing before promising
  a download.
- **Python 3.14 is not a barrier.** PyInstaller 6.22.2 builds against it.

## What still blocks section 7

Checks 3, 5 and 8, and the real cold-start number, all need a **clean Windows
11 machine with no Python installed** - which is the condition section 6
actually specifies and which this spike could not meet. `spike/packaging/` is
committed so those can be run there rather than rebuilt from scratch:

```bash
./spike/packaging/build.sh                 # the window build, for checks 3/4/5
./dist/traktor-nml-spike/traktor-nml-spike.exe
```

Until then, section 7's `nicegui-pack --onedir --windowed` recommendation is
supported but not confirmed, and the `pip install traktor-nml-tool[gui]` floor
remains the option that works regardless.

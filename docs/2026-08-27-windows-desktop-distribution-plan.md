# Local Windows Setup Plan

## Goal

Make the existing NiceGUI reconnect wizard straightforward to set up and run
from a source checkout or release ZIP on Windows, without asking users to
install or manage Python themselves. Version 1 ships the GUI by default through
a reproducible local environment; it does not yet ship a frozen `.exe` or an
installer.

The intended experience is:

```powershell
git clone <repository-url>
cd traktor-nml-tool
.\setup.ps1
.\gui.ps1
```

For a release ZIP downloaded through a browser, users review its source and
then unblock each shipped PowerShell script before the first invocation:

```powershell
Unblock-File -LiteralPath .\setup.ps1, .\gui.ps1, .\run.ps1
.\setup.ps1
.\gui.ps1
```

This removes the downloaded-file marker without changing a machine or user
execution policy. The README presents the clone and release-ZIP paths
separately.

The same managed environment also exposes the CLI through `run.ps1`.

## Evidence and Constraints

- The project already provides the NiceGUI reconnect wizard and declares
  optional `tags`, `fingerprint`, and `gui` dependency groups in
  `pyproject.toml`.
- Disk scanning needs `mutagen`; GUI setup therefore installs both `tags` and
  `gui` by default.
- Windows fingerprinting additionally needs `fpcalc` and the Chromaprint shared
  library. Version 1 diagnoses their absence but does not download or bundle
  native binaries.
- Docker already provides the fingerprint stack on Linux, but its mount root is
  load-bearing for repaired Traktor paths. It remains an advanced alternative,
  not the recommended Windows setup path.
- The existing PyInstaller packaging spike is retained as the basis for a future
  self-contained desktop installer, not as a prerequisite for this plan.

## Scope

Included:

- A checked-in `uv.lock` and `.python-version` pinning CPython 3.13.15 x64.
- `setup.ps1` to bootstrap `uv`, create the project environment, and install
  the GUI and local scanning dependencies by default.
- `gui.ps1` to launch the existing native NiceGUI wizard and `run.ps1` for the
  existing CLI.
- Explicit opt-in fingerprint setup and diagnostics.
- Windows CI and a clean-machine validation checklist.

Excluded from version 1:

- PyInstaller, `nicegui-pack`, Inno Setup, code signing, Start Menu shortcuts,
  bundled `fpcalc.exe`, and auto-updates.
- Changes to the CLI's CWD-relative cache default or TagCache schema.
- Hosted operation or network access to a user's music library.

## Architecture Decisions

### Environment Manager

Use `uv` rather than a hand-written `venv` and `pip` sequence. It manages a
supported Python interpreter when one is absent, creates an isolated `.venv`,
and synchronizes the checked-in lockfile. `setup.ps1` uses `uv sync --locked`;
it must never silently resolve newer dependencies on an end-user machine.

`.python-version` pins CPython 3.13.15 and `uv.lock` pins the full resolved
graph. `pyproject.toml` remains the dependency-intent source. A dependency or
interpreter upgrade updates the lockfile in a deliberate, reviewable change;
the Windows CI job runs against the exact pinned interpreter.

### Bootstrap and UI Launch

`setup.ps1` is transparent and idempotent:

1. Confirm it is running from the repository root and can write to the
   checkout.
2. Use an existing `uv` that meets the documented minimum version.
3. When `uv` is absent, offer the official WinGet command
   `winget install --id=astral-sh.uv -e`. If WinGet is unavailable or fails,
   stop with the official manual-install link instead of downloading and
   executing an unverified remote script.
4. Run `uv sync --locked --extra tags --extra gui` by default.
5. Add `--Fingerprint` to install `--extra fingerprint`, record that opt-in in
   `.setup-features.json`, and validate its native prerequisites. Later default
   setup runs preserve that recorded opt-in.
6. Add `--DisableFingerprint` as the only way to remove the fingerprint extra;
   it updates `.setup-features.json` and synchronizes without that extra.
7. Print the exact next commands, including `./gui.ps1` as the recommended
   launch command and `./run.ps1 --help` for the CLI.

`gui.ps1` launches `python -m traktor_nml.gui` through the checkout's
`.venv\\Scripts\\python.exe`. It verifies that the GUI extra is available and
gives the corrective setup command if it is not. It does not start a web server
on a public interface; NiceGUI stays in its existing native-window mode and
accesses only the local machine selected by the user.

`run.ps1` forwards every argument unchanged to the existing CLI:

```powershell
& .\.venv\Scripts\python.exe .\traktor_nml_tool.py @args
```

No global console-script entry point is needed for version 1. Keeping the
wrappers with the source makes the launch target, dependency environment, and
upgrade path clear.

### Optional Fingerprinting

Fingerprinting is an opt-in enhancement, not a prerequisite for the GUI.
`setup.ps1 -Fingerprint` installs the Python extra and runs the project's
availability probe. It reports separately whether `pyacoustid`, `fpcalc`, or
the Chromaprint shared library is missing, and does not claim that fingerprint
matching is active until all checks pass.

The implementation exposes a small structured fingerprint-status command or
helper that reports `available` plus a machine-readable failure reason. The
setup script, GUI toggle, and tests consume that single result rather than
duplicating native-dependency checks.

Users who require a guaranteed fingerprint stack may use the existing Docker
workflow, observing its volume-root mapping and `--dry-run` preview guidance.
The PowerShell setup path remains preferred for normal local GUI use.

## Workstreams

### 1. Lock the GUI Environment

Deliverables:

- Add `.python-version` containing `3.13.15` and confirm `uv` resolves that
  exact x64 interpreter.
- Generate and commit `uv.lock` from `pyproject.toml`.
- Document the minimum supported `uv` version and Windows architecture.
- Add a concise dependency-update procedure to contributor documentation.

Acceptance criteria:

- `uv sync --locked --extra tags --extra gui` succeeds from a clean checkout.
- Changing a declared dependency without regenerating `uv.lock` fails CI.
- The synchronized environment imports `lxml`, `mutagen`, `nicegui`, and
  `webview`.
- CI asserts `sys.version_info[:3] == (3, 13, 15)` before running tests.

### 2. Add Setup and Launch Scripts

Deliverables:

- `setup.ps1`, `gui.ps1`, and `run.ps1` with comment-based PowerShell help.
- Default GUI-plus-tags setup, sticky opt-in fingerprint setup, and explicit
  `-DisableFingerprint` removal.
- Release-ZIP instructions that unblock the reviewed `setup.ps1`, `gui.ps1`,
  and `run.ps1` files without changing execution policy.
- Error messages naming the failed prerequisite and the exact corrective
  command.

Acceptance criteria:

- Running `setup.ps1` twice is safe and does not re-resolve the lockfile.
- Running default setup after `setup.ps1 -Fingerprint` preserves the installed
  Python fingerprint extra; only `-DisableFingerprint` removes it.
- `gui.ps1` starts the native reconnect wizard after default setup.
- `run.ps1 --help` returns the existing CLI help unchanged.
- `setup.ps1 -Fingerprint` reports a missing native prerequisite without
  breaking baseline GUI or CLI setup.
- Removing the checkout's `.venv` and rerunning setup recreates it without
  changing the system Python installation.

### 3. Documentation and Safety Guidance

Deliverables:

- Put the PowerShell GUI setup path first in the README.
- Document separate clone and release-ZIP setup paths, including reviewing and
  unblocking downloaded scripts with `Unblock-File`, never a permanent
  execution-policy change.
- Document the CLI wrapper, optional fingerprinting, and the fact that native
  fingerprint prerequisites are outside Python.
- Keep Docker as an advanced alternative and retain the warning that container
  mount paths determine the paths written to a repaired NML.
- Explain that GUI and CLI cache/output paths remain locally controlled by the
  user in this source-based setup.

Acceptance criteria:

- A new Windows user can reach the reconnect wizard from the README without
  prior Python knowledge.
- A browser-downloaded release ZIP can run all three scripts after the documented
  review-and-unblock step under the default RemoteSigned policy.
- The documentation never implies Docker mount paths are arbitrary.
- Fingerprinting instructions distinguish a usable GUI from a disabled
  fingerprint tier.

### 4. CI and Clean-Machine Validation

Deliverables:

- A Windows GitHub Actions job that installs `uv`, runs
  `uv sync --locked --extra tags --extra gui`, executes the test suite, and
  verifies both wrappers.
- A lockfile freshness check in CI.
- A manual clean-machine checklist for Windows 11 with no preinstalled Python.

Clean-machine checklist:

1. Download or clone the source release and run `setup.ps1`.
2. For the browser-downloaded ZIP path, verify the source, run the documented
   `Unblock-File` command, and run all three scripts under RemoteSigned without
   changing execution policy.
3. Confirm the script explains how to install `uv` when it is absent, then
   rerun successfully after installing it through WinGet or the official method.
4. Run `run.ps1 --help` and a read-only `inspect` command on a sample NML.
5. Run `gui.ps1`, select an NML file and a scan folder through native dialogs,
   and confirm the reconnect wizard opens. This is a release-blocking check.
6. Run `setup.ps1 -Fingerprint` on a machine without native fingerprint
   prerequisites and confirm it emits a specific non-fatal diagnostic.
7. On the documented known-good Windows fingerprint stack, run
   `setup.ps1 -Fingerprint`, confirm the structured status is `available`, and
   confirm the GUI enables the fingerprint control. Then run default setup and
   verify the opt-in remains installed; run `-DisableFingerprint` and verify it
   is removed.

Acceptance criteria:

- CI uses the lockfile and fails if synchronization or wrapper invocation
  fails.
- The clean-machine setup reaches working GUI and CLI use without a manual
  Python installation.
- GUI and fingerprint results are recorded separately from baseline setup
  success.
- A deterministic setup-script test substitutes the structured status helper
  with both `available` and each documented failure reason, proving that the
  script and GUI state respond correctly without depending on a developer's
  native fingerprint installation.
- The known-good Windows validation confirms the real native stack, not only a
  test double.

## Future Upgrades

### Self-Contained Windows Installer

The existing packaging spike in
`docs/2026-08-25-packaging-spike-results.md` remains the starting point for a
future PyInstaller/NiceGUI bundle and Inno Setup installer. That work should
include bundled `fpcalc`, stable per-user cache storage, cache migration,
diagnostic logs, Defender/SmartScreen release gates, code-signing policy, and
upgrade/uninstall tests. It is not a blocker for the UI-first setup path.

### Docker Improvements

The checked-in Dockerfile and Compose configuration remain available for
advanced users, particularly where guaranteed fingerprinting matters. A future
Docker workstream may add a Windows-oriented walkthrough and a helper that
validates the Traktor-to-container volume-root mapping before a write command.

### Direct Package Installation

If the project later publishes stable console entry points and release
artifacts, `uv tool install` or `pipx install` can provide a global command.
Defer that until packaging, artifact hosting, and upgrade policy are established.

## Agent Allocation

With two agents, first agree on CPython 3.13.15, the `uv` minimum version, and
the feature-extra matrix. One agent implements the lockfile and PowerShell
wrappers; the other adds CI, documentation, and deterministic status tests.
Merge only after the wrapper contract (`setup.ps1` flags, sticky feature state,
`gui.ps1`, `run.ps1`, and exit behavior) is documented and tested.

With one agent, implement in this order: lockfile, setup script, wrappers,
README, CI, then clean-machine validation.

## Completion Definition

Version 1 is ready when a Windows user with no Python installed can clone or
unzip the project, follow the README to install `uv`, run `setup.ps1`, and
launch the native reconnect wizard through `gui.ps1`. The same setup must
support CLI use through `run.ps1`; fingerprinting must either pass its full
availability probe or explain exactly why it is unavailable. Docker and a
self-contained installer remain documented future upgrades, not release
blockers.

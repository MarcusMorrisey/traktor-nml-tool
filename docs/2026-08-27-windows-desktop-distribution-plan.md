# Windows Desktop Distribution Plan

## Goal

Ship the existing native NiceGUI reconnect wizard as a self-contained Windows
application for DJs who do not have Python installed. Version 1 targets
Windows 11 x64 and installs a conventional Start Menu application backed by an
`--onedir` PyInstaller bundle.

The CLI remains usable from source and retains its existing CWD-relative
`--cache` default. The packaged GUI receives a stable per-user cache default.

## Evidence Already Available

The section 6 packaging spike has already shown that a Windows `--onedir`
bundle can parse the large real-world collection fixture, bundle and execute
`fpcalc`, and write persistent data below `%LOCALAPPDATA%`. Its bundle was
approximately 84 MB. The reusable starting points are:

- `spike/packaging/build.sh` for the `nicegui-pack` command and bundled
  `fpcalc` handling.
- `spike/packaging/checks.py` and `spike/packaging/spike_checks.py` for
  frozen-bundle and state-directory assertions.
- `docs/2026-08-25-packaging-spike-results.md` for the checks already passed
  and the clean-machine checks still outstanding.

## Scope

Included:

- Native Windows GUI bundle and installer.
- Bundled `lxml`, NiceGUI/pywebview assets, `mutagen`, `pyacoustid`, and the
  Windows `fpcalc.exe` required for optional fingerprinting.
- Stable GUI cache location and cache schema migration behavior.
- Repeatable local and CI builds, release artifacts, and smoke tests.

Excluded from version 1:

- macOS and Linux installers.
- Automatic updates.
- Code signing, except for recording the unsigned SmartScreen result and
  preparing an opt-in signing hook in the release workflow.
- Turning every CLI subcommand into a GUI workflow.

## Architecture Decisions

### Distribution Format

Use `nicegui-pack`/PyInstaller in `--onedir --windowed` mode, then package the
result with Inno Setup. Do not use PyInstaller `--onefile` for version 1: it
adds startup extraction, is more prone to antivirus friction, and makes a
temporary bundle directory an unsafe place for application state.

### App State

Add a small `traktor_nml.app_paths` module. Its GUI-facing function resolves
the default cache path to:

`%LOCALAPPDATA%\\traktor-nml-tool\\tagcache-v1.json`

Use `platformdirs` rather than hand-written platform branches. Keep all CLI
parser defaults unchanged; only the GUI's cache field adopts this path when the
operator has not explicitly selected a cache file.

Change `TagCache` from a bare JSON map to a versioned envelope:

```json
{"schema_version": 1, "entries": {}}
```

`TagCache` must read the current legacy map as schema 0 and migrate it in
memory. Unknown future schemas must start cold, preserve the original file as
`*.unsupported-schema-<timestamp>.json`, and return a visible GUI notice. A
corrupt cache remains a cold cache, as it is today.

Downgrades are supported as safe cold-cache events, not as reverse migrations.
Before writing a newer schema, retain the immediately preceding cache as
`*.pre-schema-<version>-<timestamp>.json`. A prior application version that
encounters the newer envelope must ignore it and build a fresh cache; it must
not mix envelope fields with entry records or crash. The uninstaller never
deletes either cache variant unless the user chooses the optional data-removal
control.

### Frozen GUI Startup

Update the GUI entry point to call `multiprocessing.freeze_support()` as the
first statement in its main guard. Keep `reload=False`; set the packaged native
port through `nicegui.native.find_open_port()` so concurrent local processes do
not collide. Confirm the native page registration remains outside the main
guard, as NiceGUI requires for spawned native processes.

### Native Dependencies

Ship `fpcalc.exe` next to the frozen application assets and resolve it from the
PyInstaller extraction/application root before consulting `PATH`. This must not
change source-mode behavior, where `FPCALC` and `PATH` remain supported. The
resolution order is: explicit `FPCALC`; bundled executable in a frozen build;
then `fpcalc` on `PATH`. Put this resolver in `fingerprint.py` and make
`FpcalcSession` call it rather than constructing the binary name directly.

Record the source, version, and redistribution licence for the selected
Chromaprint binary in `THIRD_PARTY_NOTICES.md`. Verify the exact dependency
licenses before publishing the installer.

### Build Inputs and Versioning

Create `requirements/windows-build.lock` with exact versions and hashes for
the build-only tools, including PyInstaller and Inno Setup's acquisition
method. The build script installs the application explicitly as
`.[gui,tags,fingerprint]`, then installs the locked build tools. Do not rely on
the transitive dependency set of a developer machine.

Store the approved `fpcalc.exe` in a versioned `vendor/` source location or
download it from one documented upstream URL during the build. In either case,
record its version, source URL, SHA-256, and licence in
`vendor/fpcalc-manifest.json`; `build_windows.ps1` verifies the checksum before
packaging and CI fails on a mismatch.

Use the project version in `pyproject.toml` as the canonical version source.
The bundle configuration, Inno Setup script, Windows version resource, release
tag validation, and release artifact names read that value rather than carrying
independent version strings.

### Diagnostics

A persistent local diagnostic log is required for the windowed build because
there is no console for startup, packaging, or native-dependency errors. Write
rotated UTF-8 logs below `%LOCALAPPDATA%\\traktor-nml-tool\\logs`, never next to
the executable or in `sys._MEIPASS`. Exclude media paths, collection contents,
and fingerprint values from routine log messages. The GUI exposes the log
directory and shows a concise failure identifier when startup-adjacent errors
can be recovered from.

## Workstreams

### 1. Productionize the Bundle

Deliverables:

- `scripts/build_windows.ps1` creates a clean virtual environment, installs
  the locked build dependencies plus `.[gui,tags,fingerprint]`, verifies the
  approved `fpcalc.exe` checksum, and runs `nicegui-pack --onedir --windowed
  --noconfirm`.
- A checked-in PyInstaller/nicegui-pack configuration carries the application
  name, icon, version resource, hidden imports, and data-file rules.
- A build smoke test launches the frozen executable, waits for the native port
  to become reachable, then closes it cleanly.
- `traktor_nml.fingerprint` gains the frozen-bundle resolver described above;
  tests cover each resolution branch.

Acceptance criteria:

- A machine without Python can launch the application.
- The frozen app can parse the large NML fixture.
- The bundled `fpcalc.exe -version` succeeds even when `PATH` does not contain
  another copy.
- With `PATH` empty and no `FPCALC` override, a frozen-runtime test proves that
  `FpcalcSession` invokes the bundled executable.
- With `FPCALC` set, the explicit override wins over both the bundled binary and
  `PATH`.
- The app launches with no console window and exits when its native window is
  closed.
- CI rejects an unpinned build dependency, an unexpected application version,
  or an `fpcalc.exe` whose SHA-256 differs from its manifest.

### 2. Persistent State and Upgrade Safety

Deliverables:

- Add `platformdirs` as a runtime dependency.
- Add `app_paths.py`, versioned `TagCache` serialization, and GUI status text
  that shows the resolved cache path.
- Preserve explicit CLI and GUI cache paths exactly as supplied.

Tests:

- GUI default uses a test-controlled `%LOCALAPPDATA%` substitute, not CWD or
  `sys._MEIPASS`.
- Legacy cache data remains usable after migration.
- An unknown schema creates a cold cache and preserves the original file.
- A newer-schema cache is handled as a cold cache by the prior supported
  release; a v2-to-v1 downgrade neither crashes nor mutates the newer file.
- A schema upgrade retains the immediately preceding cache before it writes the
  new envelope.
- Interrupted/atomic cache writes remain reloadable.
- The windowed build writes a diagnostic log outside the bundle; representative
  log lines do not include a media path or fingerprint value.

### 3. Installer

Deliverables:

- `installer/traktor-nml-tool.iss` for Inno Setup.
- Per-user installation under `%LOCALAPPDATA%\\Programs\\traktor-nml-tool` by
  default, avoiding administrator requirements.
- Start Menu shortcut, uninstaller, version display, and optional desktop
  shortcut.
- Installer embeds the license and third-party notices.
- Installer version, bundle version resource, and installed application version
  match the value read from `pyproject.toml`.

Acceptance criteria:

- Install, launch, uninstall, and reinstall work for a standard Windows user.
- Uninstall removes program files but does not remove the user's cache unless
  they explicitly select that option.
- Installing version 2 over version 1 preserves or safely migrates state.
- Reinstalling version 1 after version 2 starts successfully and treats its
  newer cache as cold without modifying it.

### 4. CI and Release Artifacts

Deliverables:

- GitHub Actions workflow on `windows-latest` that runs unit tests, builds the
  frozen bundle, runs headless packaging checks, compiles the installer, and
  uploads both the bundle and installer as separate artifacts.
- Tag-triggered release job that publishes the installer, a SHA-256 checksum,
  and release notes.
- A protected release version source so the Python package and installer show
  the same version, derived from `pyproject.toml`.
- CI verifies `vendor/fpcalc-manifest.json` before the package step and retains
  the verified manifest, notices, and diagnostic build log with each artifact.

Acceptance criteria:

- Every tagged build is reproducible from a clean runner.
- A failed test, missing `fpcalc`, or missing installer output fails the build.
- Release assets have checksums and retain the third-party notices.
- The workflow fails before publishing when the release tag does not equal the
  canonical project version.

### 5. Clean-Machine Validation

Run on a Windows 11 x64 machine with no Python and no globally installed
`fpcalc`:

1. Install from the produced installer.
2. Pick an NML file and a scan folder through the native dialogs. This is a
   release-blocking check, not a visual smoke test.
3. Run a non-fingerprint scan and a fingerprint-enabled scan.
4. Confirm a cache is created under the per-user application-data directory.
5. Time cold launch to an interactive native window; target under 10 seconds.
6. Check Defender and SmartScreen behavior on a clean profile.
7. Install a newer build over the first, reopen the app, and verify cache
   migration or a visible cold-cache notice.
8. Uninstall and verify that application files are removed while user data
   follows the selected uninstall option.

These checks are release gates, not merely exploratory testing. Defender
quarantine, installation prevention, or deletion of the installer is a no-go:
do not publish the affected artifact until the cause is corrected or code
signing is introduced. A SmartScreen reputation warning that still permits an
informed user to install is allowed for unsigned version 1 only when its exact
text, Windows build, and workaround are recorded in the release notes. Any
browser, Defender, or SmartScreen outcome that prevents an informed user from
installing triggers the deferred code-signing work before release.

## Agent Allocation

With two agents, first complete a short build-contract handoff: agree and test
the bundle directory layout, canonical version reader, exact locked dependency
inputs, `fpcalc` manifest format, and produced artifact names. Only after that
handoff passes can one agent complete workstreams 1-2 while the other implements
the installer and CI against the accepted contract. Start workstream 5 as soon
as an installer candidate exists; its manual results feed back into the other
workstreams.

With one agent, implement in order: frozen startup and bundle, app-state
migration, installer, CI, then clean-machine validation. Do not begin signing
or auto-update work until this sequence is green.

## Completion Definition

Version 1 is ready to distribute when a tagged CI build produces an installer,
a clean Windows 11 machine can install and use the native reconnect wizard
without Python, bundled fingerprinting works without a global `fpcalc`, and
upgrade/uninstall behavior has been recorded against the acceptance criteria
above.

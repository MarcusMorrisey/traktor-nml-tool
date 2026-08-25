# NiceGUI GUI for traktor-nml-tool — implementation plan

Plan of record (2026-08-25) for adding a NiceGUI front end. Scope is deliberately
narrow: **Phase 1 is the reconnect wizard and nothing else.** Later phases are
listed so the classification is unambiguous, not because they are committed.

## Findings from the current codebase

- `traktor_nml/cli.py` builds an argparse parser by auto-discovering
  `traktor_nml/commands/*.py`; each module exposes `register(subparsers, handlers)`
  and a handler `(args) -> int`.
- Handlers **print `key=value` lines to stdout** and return exit codes. There is
  no result object.
- Core invariants: every command previews before writing, refuses to overwrite its
  own inputs, and reports ambiguity/dangling matches via stats + CSV rather than
  guessing.
- Real workloads are long: `index_scan_roots` over `D:/Music`, optional `fpcalc`
  fingerprinting, an 11.7 MB collection file.
- `TODO.md` already wants **Guided Repair Review** — a list-by-list accept/reject
  workflow. That is a GUI feature that cannot be done well in a CLI.
- `tests/baselines/manifest.json` already records stdout, exit code, and every
  written file's bytes for a fixed set of invocations (DL-002/DL-011), with
  `tests/baselines/regenerate.py` as the only sanctioned way to update it. **This
  is the parity oracle the whole refactor hangs off.**
- That oracle currently holds **8 cases across 7 subcommands** (`inspect` ×2,
  `encode-dir`, `preview-diff`, `rewrite`, `preview-compare`,
  `scan-compare-candidates`, `rewrite-from-collection-compare`). It covers **none**
  of `scan-reconnect-candidates`, `rewrite-from-reconnect`, `splice`, `split`,
  `build-playlist`, or the `discover-*` pair — i.e. none of the commands Phase 1
  touches. Closing that gap is task 0, before any core is modified.
- `fingerprint.py:62` uses `acoustid.fingerprint_file`, which spawns `fpcalc` with
  no timeout and no handle on the child. Nothing in the current design can
  interrupt a blocked fingerprint (§2, §3.5).
- `TagCache` carries no schema version and defaults to a CWD-relative path. Both
  are latent upgrade defects that only bite once the tool is distributed (§6.1).

## 1. Command classification

This replaces any notion of "100% command coverage". There are 14 subcommands;
every one lands in exactly one tier, and the tier determines the support level.

**Tier 1 — first-class GUI workflows.** Hand-built task UI, shared result object,
progress, cancel, review table, GUI-driven write.

| Subcommand | Phase |
| --- | --- |
| `scan-reconnect-candidates` | 1 (committed) |
| `rewrite-from-reconnect` | 1 (committed) |
| `preview-diff`, `rewrite` | 2 (not committed) |
| `build-playlist` | 3 (not committed) |
| `discover-tracks`, `discover-collection-tracks` | 3 (not committed) |

**Tier 2 — generated forms, no-side-effect by default.** Auto-generated from the
argparse subparser, stdout streamed to `ui.log`, no result object, no review
table, no GUI-driven `.nml` write. Eligibility is a mechanical, checkable rule:
**a command is Tier 2 eligible if and only if its handler writes no `.nml`
output.**

"Preview-only" was ambiguous, because two of these commands do touch the disk:
`inspect --csv` writes a report, and `scan-reconnect-candidates` writes the tag
cache. Resolved as follows — **the generated form runs in no-side-effect mode by
default**, and every departure from that is on a closed allowlist with the
safeguards in §4.1:

| Side effect | Default in a generated form | Allowed how |
| --- | --- | --- |
| `.nml` write | Impossible (tier rule) | — |
| CSV report (`--csv`) | **Off.** The argument is not rendered; results display in `ui.aggrid` | Explicit "Export CSV…" action, operator-chosen path |
| Tag cache (`--cache`) | **On**, unavoidable — the scan is worthless without it | Disclosed, path shown, never silent |
| Any other file-producing argument | Not rendered | Requires adding a row to this table |

The table is closed: the form generator renders a `Path`-typed argument only if it
appears here or is an input. An argument that produces a file and is not listed
fails the classification test in §1 rather than silently appearing as a text box.

`inspect`, `encode-dir`, `preview-compare`, `scan-compare-candidates`.

(`scan-reconnect-candidates` appears in both tiers by design: it is Tier 2
eligible and gets a generated form for free, and is *also* the first step of the
Tier 1 wizard.)

**Tier 3 — out of scope for the GUI; CLI only.** No form is generated and the
landing page does not link them. Stated explicitly so "not built yet" and "not
being built" are distinguishable.

- `splice`, `split` — byte-span assembly with multi-output and conflict semantics
  that need their own review UI, not the reconnect one.
- `rewrite-from-collection-compare` — needs a second-collection review table
  equivalent to reconnect's. Revisit only after the reconnect review table ships
  and proves out.

A test asserts this classification is total and disjoint: every name in
`subparsers.choices` appears in exactly one tier list, so adding a subcommand
without classifying it fails CI rather than silently defaulting into the GUI.

## 2. Architecture

**The GUI does not shell out to `traktor_nml_tool.py` and scrape stdout.** That
would work for Tier 2, but Tier 1 needs live scan progress and an interactive
review table of ambiguous matches — structured data mid-run, not a parsed
transcript at the end. (Subprocess-scraping survives as a *fallback*, see §5.)

The change is additive. `reconnect.resolve_reconnection` and friends already
compute the structured results; the command modules immediately flatten them into
`print()` and CSV. Split that flattening out:

```
core  ->  ReconnectResult (dataclass)  ->  render_reconnect_result() -> stdout lines
                                       \-> GUI review table
```

The argparse handler becomes `render(core(...))`. Its stdout is unchanged by
construction, and the renderer is independently testable.

Two prerequisites, both small:

- `index_scan_roots` gains an optional `on_progress(done, total, path)` callback.
  Without it there is no progress bar, only a spinner, and a 20-minute scan behind
  a spinner is worse than the CLI.
- A cooperative cancel token threaded through the scan loop. A GUI that can start
  an unstoppable 20-minute job is a downgrade.

Both default to inert (`None`), so the CLI path is byte-identical unless it opts in.

**Consequence for fingerprinting.** `fingerprint.py:62` calls
`acoustid.fingerprint_file(str(path))`, which spawns `fpcalc` internally and
exposes **neither a timeout nor a handle on the child process**. A cooperative
token checked between files cannot interrupt a call already blocked inside that
helper. Bounded cancellation therefore requires replacing that one call with a
direct `subprocess.Popen` of `fpcalc` that the scan owns: same arguments, same
parsed output, but with a per-file timeout and a terminable child. This is the
only core change in Phase 1 that is not purely additive, so it carries its own
parity case (§3.1) and its own cancellation test (§3.5). `_similarity` /
`compare_fingerprints` continue to use `pyacoustid` unchanged.

## 3. Test strategy for the shared-core refactor

The failure mode is breaking working CLI behavior while introducing result
objects, progress, and cancelation. Each item below is a merge gate.

### 3.1 CLI parity (task 0 — do this before touching any core)

1. Extend `tests/baselines/manifest.json` via `regenerate.py` to cover, at minimum:
   `scan-reconnect-candidates` and `rewrite-from-reconnect` against a fixture scan
   root, each in a `--dry-run` and a writing form, plus one run with an ambiguous
   match and one with a dangling match so the ambiguity/dangling reporting paths
   are pinned. Commit this **before** the refactor branch diverges.
   Include one case that exercises the fingerprint tier against a fixture with a
   stub `fpcalc` on PATH, so the §2 direct-`Popen` change is covered by the oracle
   rather than only by unit tests.
2. **`manifest.json` must not be regenerated for the duration of the refactor.**
   Non-regeneration *is* the parity check. If a refactor commit needs the manifest
   updated, that commit is by definition a behavior change: revert it or escalate
   it as a reviewed change, never regenerate to go green.

### 3.1a Pinning the oracle against a pre-refactor baseline

A working-tree check (`git diff --exit-code tests/baselines/manifest.json`) is
**not sufficient**: it passes on any commit that regenerated the baseline and
committed it, which is precisely the failure it is meant to catch. The guard must
compare against a designated pre-refactor baseline instead.

1. The task-0 commit is tagged `parity-baseline-v1` (annotated and pushed).

   **Server-side protection is unavailable on this repository.** GitHub rulesets
   return `403 — Upgrade to GitHub Pro or make this repository public`, and the
   legacy `/tags/protection` API has been removed (`404`). The compensating
   control is a `pre-push` hook in `.git/hooks/` that refuses to move or delete
   any `parity-baseline-*` tag, bypassable only with an explicit `--no-verify`.
   It is local to one clone, so it is a speed bump against accident, not a
   control against a determined push. That is acceptable because the tag is the
   *secondary* guard: the authoritative pin is `PARITY_BASELINE_SHA256` below,
   which is asserted by pytest and does not depend on the tag at all. If the repo
   ever goes public or onto a paid plan, replace the hook with a ruleset targeting
   `parity-baseline-*`.
2. `tests/test_parity_baseline.py` records the baseline's content hash as a
   literal module constant:

   ```python
   PARITY_BASELINE_SHA256 = "<hash of manifest.json at parity-baseline-v1>"
   ```

   The test hashes the current `tests/baselines/manifest.json` and asserts
   equality. This runs under plain pytest with no git dependency, so it fails
   identically in CI, in a shallow clone, and on a developer's machine.
3. Because the constant lives in a file named for the purpose, changing the
   baseline requires a visible one-line diff to a guard file — the escalation
   path, not an accident. A CI job additionally asserts
   `git diff --quiet parity-baseline-v1 -- tests/baselines/manifest.json`, so a
   commit that edits *both* the manifest and the constant is still caught by the
   tag comparison. Given that the tag is only hook-protected (step 1), this CI job
   must also verify the tag still resolves to the expected commit SHA, recorded
   alongside the hash constant — otherwise a moved tag would move the comparison
   with it.
4. **Meta-test (completion condition).** Mirroring the repo's existing
   `test_deliberate_one_character_edit_fails_parity`, a test writes a
   one-character mutation of the manifest to a temp copy and asserts the guard's
   own comparison fails against it. A guard that cannot be shown to fail is not a
   guard; this is the test that proves finding 1 is closed.
5. Escape valve, for use **after** the refactor only: a standalone PR that touches
   exactly `manifest.json` and `PARITY_BASELINE_SHA256`, with the behavior change
   named in the message, and a new `parity-baseline-vN` tag.

### 3.2 Renderer equivalence

- For each Tier 1 command, a test asserts
  `render_x(core_x(args)) == <recorded stdout>` using the same fixture inputs as the
  manifest case, so the renderer is pinned independently of the subprocess harness.
- A test asserts the handler body contains no `print` of computed values — the
  handler calls the renderer and returns its exit code. (Cheap AST or grep check;
  the point is to stop flattening logic drifting back into `commands/`.)

### 3.3 Acceptance criteria — preview / review / write

- **Preview.** Running the Tier 1 core in preview mode returns a populated result
  object and writes **zero bytes** anywhere except the documented tag-cache
  exception. Test: snapshot every file's mtime and size under `tmp_path` before and
  after; only `.traktor_nml_tagcache.json` may differ.
- **Review is a no-op by default.** Taking a preview result, applying **zero**
  operator overrides, and writing must produce a file **byte-identical** to the
  equivalent non-dry-run CLI invocation. This is the single strongest property in
  the plan: it proves the review layer cannot silently change outcomes, and it is
  checkable against the manifest bytes directly.
- **Review with overrides.** Rejecting one proposed match must produce an output in
  which that entry is left untouched, and must appear in the unresolved/ambiguity
  report. Test one accept-override and one reject-override against a fixture with a
  known ambiguous pair.
- **Write refusal is typed, not an exit code.** The input-collision rule
  (`output_must_differ_from_input`) must surface from the core as a typed refusal
  the GUI can render as a disabled button with a reason. Test: the core returns the
  refusal without raising and without writing; the CLI handler still exits 2 and
  still prints the same stderr line (covered by §3.1).

### 3.4 Testable completion conditions — progress

Driven by a fake scan root with a known file count:

- `done` is monotonically non-decreasing and never exceeds `total`.
- The final callback fires exactly once with `done == total`.
- `total` is either known before the first callback or explicitly reported as
  `None` for that run; it never changes after being non-`None`.
- At least one callback per 100 files indexed (bounds the UI going silent).
- **Parity:** a scan with `on_progress=None` and the same scan with a recording
  callback produce identical results and an identical tag cache.

### 3.5 Testable completion conditions — cancel

Cancellation is defined in **wall-clock** terms, not callback counts. A
callback-count bound is vacuous against a blocked `fpcalc` child: zero further
callbacks fire while it hangs, so "returns within N callbacks" can never trip.

**Bound.** From the moment cancel is signalled, the core returns a `CANCELLED`
outcome within **`fpcalc_grace + 2 s`, and never more than 15 s**, regardless of
scan size, file count, or whether a child process is mid-fingerprint.

**Subprocess ownership and termination.** Per §2 the scan owns the `fpcalc`
child directly:

- Exactly one live `fpcalc` child per scan worker, published to a slot the
  canceller can reach.
- Every `fpcalc` invocation carries a per-file wall-clock timeout
  (`--fpcalc-timeout`, default 30 s). On timeout the child is terminated, the file
  is recorded as `fingerprint_timeout`, and the scan continues — a single
  pathological file must not stall a 20-minute run. Timeouts are counted into the
  existing `fingerprint_stats` dict and surfaced in the result.
- On cancel: signal the token, then `terminate()` the live child, `wait(grace=5 s)`,
  then `kill()`. On Windows `terminate()` is `TerminateProcess`, which needs no
  signal-handling cooperation from `fpcalc`.
- Termination is in a `finally` so an exception on the scan path cannot orphan a
  child.

**Tests.** Determinism comes from a stub `fpcalc` on PATH that blocks for a
controlled duration, so no test depends on finding a genuinely slow audio file:

- **Mid-fingerprint cancel (the finding-2 completion condition).** Start a scan
  against a fixture whose fingerprint tier is enabled and whose stub `fpcalc`
  blocks indefinitely. Signal cancel while the child is confirmed running. Assert:
  outcome is `CANCELLED`; wall-clock from signal to return is within the bound
  above; **no output `.nml` exists**; no `fpcalc` child remains alive (assert the
  recorded child PID is gone, and that the scan's child slot is empty); the tag
  cache on disk still loads cleanly via `TagCache`.
- **Per-file timeout.** Stub blocks longer than `--fpcalc-timeout`; assert the scan
  completes, the file is reported as `fingerprint_timeout`, and no child survives.
- Cancel signalled **before** start: `CANCELLED`, no output `.nml`, no child ever
  spawned.
- Cancel signalled **mid-scan with fingerprinting off**: `CANCELLED` within the
  same wall-clock bound, no output `.nml`, tag cache still loads.
- Cancel signalled **after preview, before write**: no output `.nml`, preview
  result remains readable.
- Cancel is idempotent: signalling twice behaves as once.
- Cancel never leaves a partially written output file — writes stay atomic via the
  existing `write_bytes_atomically`.

Partial tag-cache updates remain permitted and documented on a cancelled run,
consistent with the existing `--dry-run` cache exception. `TagCache.flush` is
already atomic (temp file + `os.replace` with a Windows lock retry), so a cancel
mid-flush cannot corrupt it; the test asserts reloadability rather than
completeness.

## 4. UI design

**Tier 2 forms are generated.** `build_parser()` hands you every subparser and
action, so widgets come out mechanically: `type=Path` → file/folder picker,
`action="store_true"` → `ui.switch`, `choices=[...]` → `ui.select`,
`action="append"` → repeatable row list, `help=` → tooltip. Roughly one file, and
it tracks the parser automatically — the same property that makes DL-003's
auto-discovery nice. The Tier 2 eligibility rule keeps this machinery away from
anything that writes a collection.

### 4.1 Safeguards for every permitted side effect

Each allowed write from §1's table carries all four safeguards. These are
GUI-layer rules; none of them changes CLI behavior.

**CSV export.**

- *Destination visibility* — the resolved **absolute** path is displayed before the
  action runs, not a bare filename.
- *Collision* — if the path exists, an explicit overwrite confirmation naming the
  file with its size and mtime; the default button is Cancel. The CLI overwrites a
  `--csv` target silently; the GUI must not inherit that.
- *Confirmation* — export never happens as a side effect of running a command. It
  is a separate click on a result already on screen.
- *Failure* — a write failure (permission, disk full, path length) surfaces as both
  a `ui.notify` error and an inline banner carrying the exception text. Never
  swallowed, never reduced to a silent no-op.
- The chosen path is checked against every input for collision, reusing the
  existing `path_collides` rule rather than a second implementation.

**Tag cache.**

- *Destination visibility* — a persistent line in the scan panel states the
  resolved cache path and that scanning updates it, shown **before** the scan
  starts. This is the same documented exception the CLI already carries for
  `--dry-run`, surfaced rather than buried in `--help`.
- *Collision* — not applicable in the overwrite sense; the cache is an accumulating
  side file. A `Refresh cache` control maps to `--refresh-cache`, and is the only
  way the GUI discards prior cache content.
- *Confirmation* — not required for the automatic update, because it is disclosed
  up front and non-destructive to operator data. `Refresh cache` **does** require
  confirmation, since it discards prior scan work.
- *Failure* — a cache write failure must **not** fail the scan (the cache is a
  speedup, not an output), but must appear as a visible warning banner stating that
  the scan will be slow to repeat. A silently failing cache that quietly re-reads
  every file on each run is exactly the outcome to avoid.

**Tier 1 is hand-built and named in the user's language.** Nobody opens this
thinking "I need `rewrite-from-reconnect --match-confidence loose`". They think
*"the set I built on Friday doesn't play any more."* Phase 1 ships one card:

> **My playlists are broken** → pick old `.nml` → add scan roots →
> fingerprinting toggle, *disabled with an explanation* when `HAS_ACOUSTID` is
> false or `fpcalc` isn't on PATH → scan with progress and cancel → **review** →
> write.

The framing is playlist-first, not track-first, and that is a deliberate
correction: a stale `LOCATION` is the mechanism, but a set that will not play is
the reason anyone opens the tool. It also changes what the screens count —
results and success lead with how many playlists play end to end, with track
counts as the supporting line. Two boundaries the copy must hold:

- **This repairs playlists that still exist**, by repointing the collection
  entries they reference. Names, order and history are never touched.
- **A deleted playlist is a different job.** `build-playlist` already rebuilds one
  from a written tracklist, but it needs that list, has its own review model, and
  is Tier 1 *Phase 3* — its own entry point, never a branch of this one. Phase 1
  copy must not imply this wizard recovers a deleted playlist, and must not imply
  the tool cannot.

The design brief for these screens is published as a canvas; the working files
are in [`design/reconnect-wizard/`](../design/reconnect-wizard/).

One opinionated point: **`--dry-run` does not appear as a checkbox.** The existing
invariant is preview-then-write; in a GUI that is a phase, not a flag. Every run
previews, then a "Write output" button unlocks. Likewise the input-collision rule
disables the Write button with an inline reason rather than surfacing
`output_must_differ_from_input` as a failure after the operator committed.

### NiceGUI mapping

- **Review table** — `ui.aggrid` for matched / ambiguous / dangling, with row
  selection. This *is* the Guided Repair Review from `TODO.md`; the existing CSV
  exports are the workaround it replaces.
- **Long jobs** — `nicegui.run.io_bound` for the disk scan (thread; it is I/O-heavy
  and `fpcalc` runs as a subprocess anyway). Avoid `run.cpu_bound`: it uses a
  process pool and `TagCache` / lxml roots are not cleanly picklable. Pair with
  `ui.timer` polling a progress object, or push from the callback.
- **Output** — `ui.log` streaming the same `key=value` lines the CLI prints, so the
  CLI's diagnostic vocabulary stays visible.
- **File selection** — the real friction point. NiceGUI has no built-in server-side
  file picker; `ui.upload` is a *browser* upload and is wrong for scan roots, which
  must live on the server's filesystem. In native mode, call pywebview's
  `create_file_dialog`; otherwise use NiceGUI's `local_file_picker` example
  component. Budget for this — it is the piece most likely to feel clumsy, and it
  is a gate in the packaging spike (§6).
- **Safety** — `ui.dialog` before writes, `ui.notify` for outcomes, and keep the
  timestamped-backup convention the repo already uses
  (`*.pre_playlist_inspection_<ts>.nml`).

## 5. Rollout and rollback

The CLI must stay fully usable at every commit on the refactor branch.

**Isolation rules, enforced by tests, not convention:**

- All GUI code lives in a new `traktor_nml/gui/` package.
- `traktor_nml/gui/` may import from `traktor_nml/` cores. `traktor_nml/commands/`
  and `traktor_nml/cli.py` import **nothing** from `traktor_nml/gui/`. A test walks
  the import graph and asserts this.
- `nicegui` is an optional extra (`pip install traktor-nml-tool[gui]`). A test runs
  the CLI with `nicegui` blocked in `sys.modules` and asserts
  `python traktor_nml_tool.py --help` and one real invocation both still succeed.
  Note that `commands/__init__.py` imports every command module at CLI startup, so
  an accidental top-level `nicegui` import anywhere under `commands/` would break
  the whole CLI — this test is the guard, mirroring the existing defensive
  `fingerprint` import in `reconnect_cmd.py`.

**Sequencing.** Each step is independently shippable and independently revertable:

1. Extend the parity manifest (§3.1). No production code changes.
2. Split renderer out of core for the two reconnect commands. Parity manifest
   unchanged — that is the proof.
3. Add `on_progress` and the cancel token, defaulting to inert. Parity manifest
   unchanged.
4. Add `traktor_nml/gui/` and the Phase 1 wizard. Parity manifest unchanged.

**Rollback.** Because steps 2–3 are additive and step 4 is a separate package,
rollback is: delete `traktor_nml/gui/`, revert the renderer split, drop the `[gui]`
extra. A clean `manifest.json` diff is the evidence that rollback restored the
original contract. Steps 1–3 are worth keeping even if step 4 is abandoned.

**Fallback if the GUI integration fails.** In priority order:

1. Ship Tier 2 only, driven by **subprocess over the existing CLI**. Scraping
   `key=value` stdout is rejected as the primary architecture, but it is acceptable
   for read-only preview commands and needs none of the core refactor.
2. Ship no GUI and keep steps 2–3. Expose the progress callback to the CLI as a
   `--progress` flag and the cancel token as clean Ctrl-C handling. Both are
   independently useful and neither depends on NiceGUI.

## 6. Packaging spike (blocking the distribution section)

The distribution recommendations in §7 are **provisional until this spike runs**.
Time-box: one day. Build a throwaway ~30-line NiceGUI app and a `--onedir`
`nicegui-pack` build of it, then verify on a Windows 11 machine **with no Python
installed**:

| # | Check | Pass condition |
| --- | --- | --- |
| 1 | `lxml` bundling | The packaged app parses the 11.7 MB `collection_textual_patch_test.nml` and prints the entry count |
| 2 | `fpcalc` bundling | `fpcalc` ships via `--add-data`, is located through `sys._MEIPASS`, and `fpcalc -version` returns 0 from inside the bundle |
| 3 | Native file dialog | pywebview `create_file_dialog` returns a real path for both a file and a directory |
| 4 | Cold start | `native=True` window is interactive within 10 s of launch |
| 5 | Defender / SmartScreen | Unsigned build is not quarantined on a clean profile (record the outcome either way) |
| 6 | Persistent-state location | Cache and settings resolve to a stable per-user path, not CWD and not `sys._MEIPASS` |
| 7 | Upgrade over existing state | v2 installed over v1 starts, reads v1's cache without corruption or crash |
| 8 | Uninstall | Removing the app leaves user data intact and documented; no orphaned `fpcalc` children |

### 6.1 Persistent state, upgrade, and cache versioning

A distributed install retains state, which the source-run case never exposed. Two
concrete defects are already visible in the current code:

- **`--cache` defaults to `Path(".traktor_nml_tagcache.json")` — CWD-relative.**
  For a packaged app the working directory is whatever the shell or shortcut
  happened to set, so the cache lands somewhere arbitrary and a second launch from
  a different directory silently re-scans everything. Under `--onefile` a path
  resolved against `sys._MEIPASS` would be *deleted on exit*. The packaged app must
  resolve the default to a per-user application-data directory
  (`%LOCALAPPDATA%\traktor-nml-tool\`), with `--cache` still honoured when passed
  explicitly so CLI behavior is unchanged.
- **`TagCache` has no schema version.** Its JSON is a flat map of
  `path|size|mtime` strings to value dicts, and `__init__` falls back to `{}` only
  for `JSONDecodeError`/`OSError` — not for a value shape it does not recognise. A
  future release that changes the stored value would read a v1 cache as valid and
  produce wrong fingerprints or crash downstream, rather than degrading. Add a
  `schema_version` field and treat an unknown version as a cold cache (discard and
  re-scan, with a visible notice), never as a silent partial read.

Check 7 is the test of both: install v1, run a scan to populate the cache and any
settings, install v2 over it, and assert v2 starts, reads or cleanly discards the
v1 cache, and never crashes on it. A matching automated test at the unit level
feeds `TagCache` a v1-shaped file and asserts the cold-cache path.

**Exit criteria.** All of 1–4 and 6–7 pass → keep the `nicegui-pack` recommendation and
record the working flag set in this document. Any of 1–4 fails → §7 downgrades to
*pipx / pip-install only*, and the `.exe` path is dropped rather than debugged
speculatively. A failure in 6 or 7 does not drop the `.exe` path but **blocks any
second release**: shipping v1 without a versioned cache and a stable state
location creates an upgrade problem that only gets more expensive. Checks 5 and 8
are informational and do not block, though a quarantine result argues for
`--onedir` over `--onefile` regardless.

## 7. Hosting and self-deployment (provisional pending §6)

The decisive constraint: **Traktor's paths are local volumes (`D:/Music`), and
reconnect scans the actual filesystem.** The GUI must run on the machine holding
the music, which turns most "hosting" questions into packaging questions.

**Recommended — `ui.run(native=True)`.** pywebview opens a real desktop window, with
native file dialogs and no "which port, which browser" confusion. Windows 11 already
ships the Edge WebView2 runtime, so there is no extra install.

**Zero-effort fallback — `ui.run(show=True)` on localhost.** Same code, opens the
default browser; bind `127.0.0.1` explicitly. Good for development.

**For people who have Python — `pip install traktor-nml-tool[gui]`** with a
`traktor-nml-gui` console entry point. Cheapest real distribution, and it keeps the
CLI install lean. This is the floor: it works regardless of the §6 outcome.

**For people who don't — `nicegui-pack --onedir --windowed`.** Start `--onedir`, not
`--onefile`: it avoids the slow unpack-on-launch and reduces AV false positives, at
the cost of a folder. Known costs are exactly the §6 checks — `lxml` binaries,
`fpcalc` via `--add-data` + `sys._MEIPASS`, and unsigned-binary SmartScreen
warnings. *(Flag spellings are medium confidence; §6 pins them.)*

**Situationally useful — Docker on a NAS.** Only coherent if the library lives on
that NAS, and there is a trap worth stating plainly: container paths (`/music/...`)
will not match the `VOLUME`/`VOLUMEID` Traktor recorded on Windows, so
`--volume-map` stops being an escape hatch and becomes mandatory for every run. If
supported, the GUI must detect the mismatch and prompt for the mapping rather than
producing a technically-correct collection full of paths Traktor cannot resolve.

**Discourage — LAN or internet exposure.** `ui.run(host='0.0.0.0')` ships **no
authentication**, and this app deliberately exposes a filesystem browser and writes
files. If ever needed, put it behind Tailscale rather than adding a login form, and
never bind a public interface.

## 8. Open questions

- How much of the Tier 1 command-module logic is genuinely reusable versus tangled
  with `print`/`sys.exit`. This plan read the cores' signatures but not every
  handler body; a closer pass on `rewrite.py` (464 lines, the largest) would firm up
  the Phase 2 estimate. Does not block Phase 1.
- Single-user local use, or distribution to other DJs? If local-only, skip §6 and §7
  entirely and run from source — the packaging, Docker, and LAN options all
  evaporate, and the plan shrinks to §1–§5.

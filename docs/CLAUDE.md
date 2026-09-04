# docs/

## Files

| File                                    | What                                                              | When to read                                          |
| ---------------------------------------- | -------------------------------------------------------------------| -------------------------------------------------------- |
| `README.md`                              | Index and purpose of this directory's files                        | Orienting within this directory                        |
| `2026-08-26-renderer-split-plan.md`      | Implementation plan for section 5 step 2 of the GUI plan: the reconnect core/renderer split, the printless write shell, and the tests that pin them | Implementing or reviewing the renderer split; implemented for the reconnect path |
| `nicegui-gui-analysis.md`                | Plan of record for a NiceGUI front end: command tiers, shared-core refactor, CLI parity tests, rollout/rollback, packaging spike | Picking up or scoping GUI work; the Phase 1 reconnect wizard is built, Tier 2/3 and Phase 2/3 are not |
| `2026-08-24-build-playlist-plan.md`      | Full implementation plan for the `build-playlist` feature (design, code diffs, docs) | Understanding why build-playlist is shaped the way it is |
| `decision-log-014-023-reconstructed.md` | DL-014..023, reconstructed from their surviving citations because no original table defined them: SpanIndex, one-to-one enforcement, volume-side split, atomic writes, split isolation, multi-input refusal | Following a DL-014..023 citation, or changing SpanIndex, enforce_one_to_one, atomic writes or the input-collision rule |
| `2026-08-25-packaging-spike-results.md` | Results of the section 6 packaging spike: what passed, what needs a clean Windows machine, and four findings the checklist did not anticipate | Packaging the GUI, or deciding whether section 7's distribution advice is safe to act on |
| `2026-08-27-windows-desktop-distribution-plan.md` | Implementation plan for Windows `uv` and PowerShell setup that ships the local GUI by default; installer and Docker improvements are deferred | Implementing or reviewing local Windows setup |
| `2026-08-25-matching-tolerance-decisions.md` | DL-040/041: measured FILESIZE/PLAYTIME_FLOAT error against a real collection; why size and duration refute rather than identify, and why the path-suffix tiers exist | Changing a match tier, a matching tolerance, or the confidence ladder |
| `2026-08-27-reconnect-wizard-plan.md`    | Implementation plan for the reconnect wizard: the default-None per-record review channel through `match_records`/`resolve_reconnection`/`run_reconnection`, the shared `write_reconnect_result` core both write paths run through, and DL-058..DL-067 | Following a DL-058..DL-067 citation, or changing the review channel or the shared write core |
| `2026-08-27-m001-browser-record.md`      | DL-084 served-page record for milestone M-001: `getComputedStyle` readings of the wizard's surfaces, text, control colour and type step against `Main`/`Scanning`/`Results`/`Confirm.dc.html`, every entry reading `matches` | Checking what M-001's served-page gate measured, or re-running a token comparison against Specs |
| `2026-08-28-w002-browser-record.md`      | DL-084 served-page record for wave W-002 (M-002 and M-003): the keyboard contract, the focus ring, the review table controls, the scan counter and the write dialog read off the served DOM, plus the two out-of-repository accommodations the run needed | Checking what W-002's gate exercised, or re-running the keyboard/announcement gate |
| `2026-08-29-w004-focus-ring-record.md`   | DL-084 served-page record for the Review step at commit `90f7885`: focus readings taken from trusted Tab presses, the seven filter-chip counts, and the focus ring Quasar removed | Checking the Review step's focus behaviour, or the Quasar ring shortfall it records |
| `2026-09-03-header-tabs-browser-record.md` | DL-084 served-page record for the app header and its two section tabs at commit `1fed6e7`: the status of `/`, `/reconnect` and the unrouted `/reconstruct`, and the paint and markup of each tab read off the served DOM | Checking how the header tabs and the `/reconstruct` 404 were verified on a served page |
| `traktor_nml_tool_plan.md`               | Original product/technical design plan (Phase 1 reconnect, Phase 2 splice/split) | Looking up historical design rationale for reconnect/splice/split |
| `traktor_nml_tool_execution_plan.md`     | Detailed implementation plan, decisions, constraints, acceptance criteria for Phase 1/2 | Looking up why a specific pre-existing behavior was implemented that way |
| `chat_export.md`                         | Concise export of the development conversation that shaped the work | Historical context only                                |
| `chat_export_full.md`                    | Complete source export of that conversation                        | Historical context only                                |
| `Makefile`                               | Sphinx driver for POSIX: `SOURCEDIR=source`, `BUILDDIR=build`, `html` and `clean` targets | Building the documentation site on POSIX |
| `make.bat`                               | Sphinx driver for Windows, over the same source and build directories | Building the documentation site on Windows |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `plans/`  | One directory of planner state per piece of work, named for its date and subject; `plans/README.md` maps each to what it covers | Looking up why a milestone is shaped the way it is, beyond the prose plan |
| `source/` | Sphinx project sources: `conf.py`, `index.rst`, `overview.rst`, `cli.rst`; the API reference under `source/generated/` is rebuilt on each Sphinx run | Changing the generated documentation site's content or configuration |
| `build/`  | Sphinx output. Gitignored; regenerate with `make html` (POSIX) or `make.bat html` (Windows) from `docs/` | Never edit directly |

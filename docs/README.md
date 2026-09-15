# Project documentation

## Overview

This directory primarily holds planning material and development context. The
current code documentation now lives in the Sphinx project under
[`source/`](source/), while the command reference still lives in the
[repository README](../README.md) and the architecture in the [package
guide](../traktor_nml/README.md).

The file index is in [CLAUDE.md](CLAUDE.md). What that index cannot tell you is
each document's standing, which is the only thing that decides whether a
statement in it is still true.

## Standing of each document

**Implemented; rationale still binding.** `2026-08-26-renderer-split-plan.md`
covers section 5 step 2 of the GUI plan: the reconnect core/renderer split and
the printless write shell it requires. Its contract is that
`tests/baselines/manifest.json` is not regenerated and `PARITY_BASELINE_SHA256`
does not move - the unchanged manifest is what proves the split behaviour-preserving.
`traktor_nml/reconnect_render.py` holds `RenderedOutput`, `emit` and the two
render functions, and `traktor_nml/commands/reconnect_cmd.py` is argparse wiring
around `emit(render(core(args)))` for both reconnect subcommands.
`index_scan_roots` takes an `on_diagnostic` callback so the core writes to no
stream, and `ReconnectResult.diagnostics` carries the collected lines in
emission order. `tests/test_reconnect_render_equivalence.py`,
`tests/test_scan_diagnostics.py` and `tests/test_command_layer_printless.py`
guard it. The split is scoped to the reconnect path; the other commands under
`traktor_nml/commands/` render inline.

**Partly implemented; authoritative for the rest.** `nicegui-gui-analysis.md`
describes a NiceGUI front end: command tier classification, the shared-core
refactor and its CLI parity test strategy, rollout/rollback, and a blocking
packaging spike. The Phase 1 reconnect wizard is built over the two Tier 1
reconnect subcommands - `traktor_nml/gui/` holds the wizard, with
`review_model.py`, `wizard_state.py` and `_fs_nav.py` framework-free and
`app.py`, `file_picker.py` and `__main__.py` the only modules importing nicegui
or pywebview - and `python -m traktor_nml.gui` starts it. Section 4's UI
mechanics and section 5's tier classification are implemented for that path,
and section 6's packaging spike is recorded in
`2026-08-25-packaging-spike-results.md`. The Tier 2 generated-form machinery,
the Tier 1 Phase 2/3 commands and the Tier 3 commands are not built, and
section 7's hosting advice stays provisional. The document is authoritative for
that remaining work.

**Implemented; rationale still binding.** `2026-08-24-build-playlist-plan.md`
and `2026-08-25-matching-tolerance-decisions.md` carry the decision logs
(DL-024..DL-039, DL-040..DL-043) that `traktor_nml/README.md` cites by number.
The code has moved on from the plans' code listings, but the reasoning chains
are the record of why the current shape was chosen.

**Reconstructed, authoritative for its Decision column only.**
`decision-log-014-023-reconstructed.md` defines DL-014..023, which were cited
about thirty times across the package README, the CLAUDE.md indexes and the
source but defined by no table. The Decision column states what the code
demonstrably does; the Reasoning column is inferred from the citations and is
not recovered deliberation.

**Authoritative for its Decision Log table only.**
`traktor_nml_tool_execution_plan.md`'s "Decision Log" section defines
DL-001..DL-013, the earliest block and the most cited: the package README, the
CLAUDE.md indexes, the source and the tests name those thirteen numbers
between them upward of eighty times, DL-004 alone around thirty. Nothing else
defines them. The rest of that document is historical, below.

**Historical.** `traktor_nml_tool_plan.md` and the remainder of
`traktor_nml_tool_execution_plan.md` record the original Phase 1/2 design, and
`chat_export.md` / `chat_export_full.md` export the development conversation.
These describe intent at the time of writing and have not been maintained since;
where they disagree with the code, the code is correct.

For current behaviour, use the CLI help (`python traktor_nml_tool.py --help`),
the repository README, the Sphinx API docs under `source/`, and the tests.

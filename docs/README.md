# Project documentation

## Overview

This directory holds planning material and development context, not current
documentation. The command reference lives in the [repository
README](../README.md) and the architecture in the [package
guide](../traktor_nml/README.md).

The file index is in [CLAUDE.md](CLAUDE.md). What that index cannot tell you is
each document's standing, which is the only thing that decides whether a
statement in it is still true.

## Standing of each document

**Plan of record, not yet implemented.** `nicegui-gui-analysis.md` describes a
NiceGUI front end: command tier classification, the shared-core refactor and its
CLI parity test strategy, rollout/rollback, and a blocking packaging spike. It
is authoritative for GUI work that has not started; nothing in the codebase
implements it.

**Implemented; rationale still binding.** `2026-08-24-build-playlist-plan.md`
and `2026-08-25-matching-tolerance-decisions.md` carry the decision logs
(DL-024..DL-035, DL-040..DL-041) that `traktor_nml/README.md` cites by number.
The code has moved on from the plans' code listings, but the reasoning chains
are the record of why the current shape was chosen.

**Historical.** `traktor_nml_tool_plan.md` and
`traktor_nml_tool_execution_plan.md` record the original Phase 1/2 design, and
`chat_export.md` / `chat_export_full.md` export the development conversation.
These describe intent at the time of writing and have not been maintained since;
where they disagree with the code, the code is correct.

For current behaviour, use the CLI help (`python traktor_nml_tool.py --help`),
the repository README, and the tests.

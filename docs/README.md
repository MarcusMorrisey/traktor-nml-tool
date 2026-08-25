# Project Documentation

This directory keeps the planning material and development context that
informed the current implementation. The command reference and architecture
for the maintained tool live in the [repository README](../README.md) and the
[package guide](../traktor_nml/README.md).

## Active Plans

- [`nicegui-gui-analysis.md`](nicegui-gui-analysis.md) is the plan of record for
  a NiceGUI front end: command tier classification, the shared-core refactor and
  its CLI parity test strategy, rollout/rollback, and a blocking packaging spike.
  Not yet implemented.

## Planning

- [`traktor_nml_tool_plan.md`](traktor_nml_tool_plan.md) is the original
  product and technical design plan.
- [`traktor_nml_tool_execution_plan.md`](traktor_nml_tool_execution_plan.md)
  records the detailed implementation plan, decisions, constraints, and
  acceptance criteria.
- [`2026-08-24-build-playlist-plan.md`](2026-08-24-build-playlist-plan.md) is
  the implementation plan for the `build-playlist` feature (design, code
  diffs, docs).

## Development Context

- [`chat_export.md`](chat_export.md) is a concise export of the development
  conversation used to shape the work.
- [`chat_export_full.md`](chat_export_full.md) is the complete source export.

The Planning and Development Context files above are historical reference
material. For current behavior, use the
CLI help (`python traktor_nml_tool.py --help`), the repository README, and the
tests.

# Plans

The planner state for each piece of work in this package, one directory per
plan, named for the date the plan was written and the work it covers. These
directories were produced in the system temp directory and are kept here
because temp is subject to cleanup, and a plan is the only record of why a
milestone is shaped the way it is once its diffs are committed.

| Directory | Covers |
|---|---|
| `2026-08-22-disk-scan-reconnect` | Reconnecting stale collection paths by scanning the disk, rather than only against a second NML |
| `2026-08-23-package-findings` | Eight confirmed findings across the package: correctness gaps and skipped checks |
| `2026-08-24-build-playlist` | `build-playlist`: an external `Artist - Title` text list resolved against a collection into a playlist node. Its prose form is `docs/2026-08-24-build-playlist-plan.md` |
| `2026-08-25-matching-tolerance` | Matching tolerances and the refutation check. Its prose form is `docs/2026-08-25-matching-tolerance-decisions.md` |
| `2026-08-26-renderer-split` | Splitting stdout flattening out of the reconnect subcommands so one `ReconnectResult` feeds both renderers. Its prose form is `docs/2026-08-26-renderer-split-plan.md` |
| `2026-08-27-reconnect-phase1` | The Phase 1 reconnect subcommands |
| `2026-08-29-playlist-reconstruction` | `splice --reconstruct-playlists` and the `/reconstruct` wizard route (DL-091..DL-103) |
| `2026-08-31-conflict-resolution` | Per-track conflict resolution: the `resolutions` mapping through the core and the `/reconstruct` conflict screen (DL-104..DL-115) |
| `2026-08-31-source-resolution` | A SOURCE pick rewriting base's own ENTRY in place rather than transplanting the source's beside it (DL-116..DL-129) |
| `2026-09-03-header-tabs` | The app header and its two section tabs: the reconstruct page at `/`, the reconnect wizard at `/reconnect`, and the tab strip that replaces the link between them (DL-129..DL-147) |

The reconnect wizard's own plan is not here: it lives in the sibling
`traktor-nml-tool-plan` repository (see [DEVELOPING.md](../../DEVELOPING.md#the-layout)),
which holds the milestone diffs themselves and a `plan.json.VERIFIED-GOOD`
snapshot, and is large enough to warrant that. **That repository is frozen at
the tag `plan-final-w004` and takes no new plans**; this directory is the
scheme going forward.

The difference is why only one of them needs machinery. A plan here carries no
`code_changes` - the newest, `2026-08-29-playlist-reconstruction`, has none and
no waves - so there is nothing to replay and no byte-identity to protect. The
wizard plan does carry them, and its `verify_frozen.py` checks that its
snapshot and its baseline commits still hold.

## What is in each directory

- `plan.json` is the plan: milestones, decisions with their reasoning chains,
  acceptance criteria and code intents. Some directories carry `plan.md`, a
  rendering of the same content.
- `context.json` is what the plan was written from: the task, the constraints,
  the entry points, the rejected alternatives and the invisible knowledge.
- `qr-*.json` are the quality-review passes over the plan or the
  implementation, one file per phase.
- `scratch/` holds working files from the session that produced the plan -
  diffs, one-off apply scripts, payload dumps. They are kept for provenance
  rather than for reading, and nothing references them.

These are records rather than living documents. The decisions they contain are
restated in `traktor_nml/README.md`'s decision log, which is the authority; a
plan here states how a decision was reached and what else was considered.

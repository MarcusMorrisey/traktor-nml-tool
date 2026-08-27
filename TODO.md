# TODO

## Replace Existing Playlists

Add a `replace-playlist` workflow that updates a same-name playlist in a
target collection instead of creating a renamed duplicate. It must preserve
the target playlist UUID and sorting location, redirect every retained
`PRIMARYKEY` to the target collection, and refuse output when any reference
cannot be resolved.

## Refined Fuzzy Matching

Mostly delivered. `discovery.py`, behind `discover-tracks` and
`discover-collection-tracks`, already provides opt-in fuzzy matching for tracks
whose tags or filenames have changed: it is a separate subcommand so it never
displaces strict matching, it ranks candidates by a weighted artist/title score
with `--min-score` and `--max-candidates` controlling what is surfaced, and it
writes a review CSV carrying the score for each candidate. It never writes an
NML at all.

What remains: the score is a ranking number, not an *explanation* - a reviewer
sees 0.62 without seeing which terms agreed. And because discovery cannot write,
"explicit confirmation before writing" has no counterpart in `discovery.py`
itself; acting on a reviewed CSV from `discover-tracks`/`discover-collection-tracks`
is still manual. Both are questions about the discovery CSVs specifically -
the confirmation step for the reconnect matcher already lives in Guided Repair
Review below.

## Guided Repair Review

The reconnect wizard (`python -m traktor_nml.gui`, the `gui` extra) is this
workflow: a list-by-list review of unresolved and ambiguous playlist entries
that accepts or rejects proposed matches, records each override, and writes a
validated output collection. It is driven in-process against
`run_reconnection` and the two reconnect cores rather than over a parsed CLI
transcript, which is what lets the review happen while the run is still open
instead of after it has exited. Its confirmation dialog before the final write
is the explicit-confirmation-before-writing step the paragraph above defers to.

The CSV exports remain a separate path for scripted use: `rewrite-from-reconnect`
stays one call to the shared write core `write_reconnect_result`, so its `--csv`
ambiguity export keeps producing the same file from the same code the wizard's
write path runs.

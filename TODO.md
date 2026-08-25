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
"explicit confirmation before writing" has no counterpart yet; acting on a
reviewed CSV is still manual. Both belong with Guided Repair Review below,
which is where a confirmation step would live.

## Guided Repair Review

Add a list-by-list repair workflow that presents unresolved and ambiguous
playlist entries, accepts or rejects proposed matches, records each manual
override, and then generates a validated output collection or playlist-only
NML.

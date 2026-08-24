# TODO

## Replace Existing Playlists

Add a `replace-playlist` workflow that updates a same-name playlist in a
target collection instead of creating a renamed duplicate. It must preserve
the target playlist UUID and sorting location, redirect every retained
`PRIMARYKEY` to the target collection, and refuse output when any reference
cannot be resolved.

## Refined Fuzzy Matching

Add reviewable, opt-in fuzzy matching for tracks whose tags, filenames, or
audio identifiers have changed. Candidate matches must include an explanation
and confidence, require explicit confirmation before writing, and never
silently replace strict matching.

## Guided Repair Review

Add a list-by-list repair workflow that presents unresolved and ambiguous
playlist entries, accepts or rejects proposed matches, records each manual
override, and then generates a validated output collection or playlist-only
NML.

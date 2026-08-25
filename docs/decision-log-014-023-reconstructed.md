# Decisions DL-014 .. DL-023 (reconstructed)

## Why this file exists

`DL-014` through `DL-023` are cited about thirty times - from
`traktor_nml/README.md`, `traktor_nml/commands/CLAUDE.md`,
`traktor_nml/commands/split_cmd.py`, `tests/test_compare.py` and
`tests/test_split.py` - but no decision table ever defined them. Every other
number resolves: `DL-001`..`DL-013` in
[`traktor_nml_tool_execution_plan.md`](traktor_nml_tool_execution_plan.md),
`DL-024`..`DL-039` in
[`2026-08-24-build-playlist-plan.md`](2026-08-24-build-playlist-plan.md),
`DL-040`..`DL-041` in
[`2026-08-25-matching-tolerance-decisions.md`](2026-08-25-matching-tolerance-decisions.md).
These ten did not, so a reader following a citation reached nothing.

**These entries are reconstructed from the surviving citations and the code
they describe, not recovered from an original table.** The Decision column
states what the code demonstrably does and what the citing prose asserts. The
Reasoning column is inferred from the same sources; where the original
deliberation is unrecoverable it says so rather than inventing a chain. Treat
the Decision column as authoritative and the Reasoning column as
reconstruction.

## Decision Log

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-014 | `spans.py` builds one `SpanIndex` per source document in a single pass - one pre-order walk for per-tag ordinals, one token scan for opening-tag offsets - and it is the only mechanism mapping a parsed element to its source byte span | An element must be located in source bytes to transplant it -> locating by searching for an attribute value re-scans the document per element, which on the 11.7MB, 6412-entry reference corpus is a per-element document scan -> a single indexed pass costs one traversal and holds per-tag offset lists in memory for the whole document -> that memory cost is accepted, and recorded as a tradeoff, because the alternative is the rescan (see DL-021 for the locator this replaced) |
| DL-015 | The one-to-one destination-collision post-pass is a named function in `reconnect.py`, `enforce_one_to_one`, called by both `resolve_reconnection` and compare-based rewriting | DL-004 already guaranteed that two old entries never resolve to one destination -> implementing that guarantee separately per caller means two implementations of one invariant, which drift independently -> one shared post-pass gives the guarantee a single implementation both paths call |
| DL-016 | A match withdrawn by the one-to-one post-pass is reported as `destination_collisions` on both the reconnect and the compare path, rather than being folded into the unmatched count | A withdrawn match and a genuinely unmatched track are different operator situations: one means the tool found a file and declined to commit to it, the other means it found nothing -> collapsing them hides the distinction the post-pass exists to make -> reporting the count separately costs one regenerated baseline manifest case, which is accepted |
| DL-017 | The volume-relative-to-absolute transformation is split by side rather than owned by one module: `reconnect.py`'s `location_from_disk_path` handles the candidate (new) side, `volumes.py`'s `local_path_for_location` handles the old side | The two directions have different inputs and different failure modes - the new side starts from a real path that exists, the old side starts from a recorded VOLUME/VOLUMEID pair that may name nothing mounted -> one module owning both would need both failure vocabularies -> each side lives with the module that owns its data |
| DL-018 | `local_path_for_location` resolves only against mount anchors the run established explicitly (`--volume-map` entries, and scan roots whose identity `resolve_volume_identity` resolved). It returns nothing for an unknown VOLUME/VOLUMEID pair, and nothing when two known anchors both yield a readable file. It never parses an anchor out of the VOLUME string and never falls back to the filesystem root | DL-005 already requires explicit VOLUME/VOLUMEID identity on the new side -> a guessed anchor on the old side can resolve to a different file sitting at the same volume-relative path -> that wrong file's fingerprint could then win a match and rewrite LOCATION and PRIMARYKEY onto an unrelated track, which is a silent wrong answer rather than a visible failure -> refusing to guess extends DL-005 to the old side rather than carving an exception out of it, and the cost - an unmapped record is simply not fingerprinted, counted as `fingerprint_unavailable_old_side` - is accepted |
| DL-019 | Every output file is committed through a temp file plus `os.replace`, and `splice_cmd`/`split_cmd` read, parse and write through helpers exported from `rewrite.py` rather than carrying their own input handling and a plain `write_bytes` | A destination must hold either its previous bytes or the complete new bytes, never a partial write -> a command with its own write path does not inherit that guarantee, nor the `xml_parse_error`-plus-exit-2 diagnostic every write command owes on malformed input -> routing both through the shared helpers gives every command one atomic write and one error vocabulary |
| DL-020 | A split output depends only on the playlists its own group names: an untouched playlist elsewhere in the document can neither pull tracks into a group nor cause it to fail | The per-output semantics already imply this, but implication is not a guarantee a future change is checked against -> a dangling-reference policy scoped document-wide would let an unrelated playlist fail a group that is internally consistent -> stating the isolation explicitly makes it testable (see `tests/test_split.py`) |
| DL-021 | `playlists.py`'s UUID-marker locator is removed; an element is located by tree identity through the shared `SpanIndex`, never by searching for an attribute value and never by a second locator | The UUID-marker search could not locate a `PLAYLIST` element whose child carries no UUID, so some playlists were unlocatable -> a second locator alongside `SpanIndex` also means two mechanisms that can disagree about where an element is -> deleting it leaves one locator that handles the no-UUID case correctly (see DL-014) |
| DL-022 | `split`'s multi-output write loop is not transactional across files: each destination is individually atomic, but a failure partway through the loop leaves earlier group outputs written | Cross-file staging and commit is new machinery beyond what a fix-only pass should introduce -> per-file atomicity already prevents the corrupt-file failure mode, leaving only the partially-complete-set mode -> the limitation is recorded explicitly rather than left implied by the per-file atomicity claim, so an operator knows to check the set (see `split_cmd.py`) |
| DL-023 | `write_nml_safely`'s output-equals-input refusal is stated over every file the invocation reads, not only its primary input; a command with more than one input declares the rest through `extra_inputs` | Refusing only the primary input leaves a multi-input command able to overwrite its own second input -> `rewrite-from-collection-compare` reads two collections and is the case that surfaced this -> declaring `new_input` through `extra_inputs` makes an output resolving to the newer collection refused the same way one resolving to `old_input` already was, and states the rule generally rather than patching the one command |

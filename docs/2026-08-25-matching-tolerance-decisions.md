# Decisions: tolerant verification and path-suffix matching

## Overview

A disk scan over a moved library reconnected nothing. The cause was not a
bug in any one tier but an assumption shared by several of them: that a
value Traktor records about a file can be compared for exact equality
against the same value measured from the file on disk. It cannot.

Measured against a real 6,386-entry collection and its files:

| Field | Traktor records | Disk reports | Agreement |
|---|---|---|---|
| `FILESIZE` | audio payload, kilobytes | `st_size`, bytes | median 0.17% low, max 0.41% low (tag and artwork overhead excluded) |
| `PLAYTIME_FLOAT` | its own decoded duration | mutagen's duration | differs by up to 0.172s; as strings, never equal |

Five of the seven tiers were therefore structurally dead against a disk
scan, and the `filename_size` fallback the tool advertised on a
mutagen-absent run could never fire: the tool reported graceful
degradation while matching nothing.

## Decision Log

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-040 | `FILESIZE` and `PLAYTIME_FLOAT` are used to refute a candidate, never to identify one, compared with tolerances (2% relative on size, 1.0s absolute on duration) set well above the measured maxima | Exact equality between the two sides is impossible rather than merely unreliable, since the two sides measure different quantities in different units -> any tier keyed on one of these fields cannot match a real file, so the fields must leave the identifying keys entirely -> they still carry real discriminating power against a wrong candidate, so they are kept as a filter applied to each tier's candidate list -> the tolerance is set loose on purpose: a too-tight bound rejects a present file and reports the user's track as missing, whereas a loose one only slightly weakens tie-breaking while the tier keys do the identifying -> absent data on either side never refutes, so a candidate whose tags could not be read is left for the tier keys to judge rather than silently discarded -> the `filename_size` tier, the last user of raw FILESIZE equality, is retired rather than left in place: sitting last in the cascade, its only possible effect was to break a `filename` ambiguity on a numeric coincidence, which is a wrong answer delivered confidently |
| DL-041 | Path-suffix tiers key on the last N folder names plus the filename: `path_suffix_3` and `path_suffix_2` at strict, `path_suffix_1` at loose | A wholesale move of a library changes every absolute path but preserves each file's position within its own folders, which is the dominant real-world reconnect case and the one no tag-derived tier can serve when tags are unreadable -> a suffix key is comparable from either side, since a collection record decodes Traktor's DIR and a disk candidate carries its real parent path -> at three folders deep the key is unique for 97.2% of entries in the measured collection, which is discriminating rather than merely permissive, so the deep tiers belong at strict alongside the tag tiers rather than behind a looser level -> `path_suffix_1` is shallow enough to collide across sibling libraries ("Album/track01.mp3"), so it waits for loose -> the tiers sit below the tag-derived tiers in the cascade, so a run whose tags are readable resolves exactly as it did before |

## Consequences recorded in the parity baseline

`parity-baseline-v1` -> `v2` records, case by case: every
match/unmatched/ambiguous count unchanged, every written output file
byte-identical, and the only stdout deltas are the new per-tier counters
plus the reconnect cases attributing their match to the `filename` tier
instead of `filename_size`, which is retired. That tier had only ever appeared to work
because the test fixture wrote a 16-byte stub beside `FILESIZE="16"`,
making kilobytes and bytes collide by accident - the fixture encoded the
same broken assumption the code did.

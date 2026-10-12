# What the measured tier reaches on a real collection pair

Measured 2026-10-04 on `$COLLECTION2026-08-31-reconnected.nml` against
`traktor\collection.nml` - 12,718 identity groups, 3,366 of them
diverging, the largest real pair available. The run was taken through
`splice.assemble_output`'s own grouping, with each of the rule's three
preconditions reported separately rather than as their conjunction, so
the one that decides a group is named rather than inferred.

## What the rule does with a diverging group

| Groups | Share | Outcome |
|---|---|---|
| 1,790 | 53.2% | carry an editorial name, so the operator answers them |
| 318 | 9.4% | one LOCATION described twice: settled by the rule |
| 982 | 29.2% | two files, different name and stem: a conflict |
| 225 | 6.7% | two paths, same file name: a conflict |
| 46 | 1.4% | a measured value missing on one side: a conflict |
| 5 | 0.1% | a conversion, same stem: a conflict |

## What this establishes

**The rule settles 9.4% of diverging groups, not the share the plan was
written against.** `docs/plans/2026-09-26-metadata-conflict-tier`'s
context records 94.2% of 9,052 groups diverging on nothing but the three
measured attributes. That figure counts attributes alone. On this pair
the same count is 1,576 groups, 46.8% - the same order of magnitude - and
the rule as it stands also requires one primary key and readable values,
which `splice._resolve_conflicts` checks before settling anything. The
primary-key precondition alone accounts for about four fifths of the
difference between 1,576 and 318.

**The preconditions are what make the rule safe, and the difference is
their cost.** A group spanning two LOCATIONs is two files the matching
cascade united on artist and title; settling one merges them, dropping an
ENTRY and redirecting its playlist references, which is the reasoning
DL-325 refuses to apply to two files.

**The widest measured gaps on this pair are two encodings of one
recording, not two analyses of one file.** The design's premise is one
file described twice. Where a group holds a `.mp3` and a `.stem.m4a` of
the same track, the differing FILESIZE and BITRATE are correct facts
about two different files. See `2026-10-04-audio-id-collisions.md`: 98.4%
of the 982 agree on AUDIO_ID, which is dedupe tier 3's case.

**A volume-prefix mismatch is marginal.** One path written with its
volume folded in and once without produces two primary keys for one file.
Over the same 12,718 groups, 398 hold more than one primary key and 11
are that case; 9 of the 11 agree on every tracked attribute and 2 are
measured-only conflicts.

## What this does not establish

**The pair that produced the original 9,052-group measurement was not
located.** All 30 ordered pairs of the six collections under
`D:\Sync\FreqKing_V02` top out at 3,366 diverging groups. The 94.2%
figure is therefore compared across pairs, not re-measured on its own.

**Nothing here is a reading of the screen.** What the tier draws is
`2026-09-26-tiered-conflict-browser-record.md`.

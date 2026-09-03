# 2026-08-31 source resolution

A SOURCE pick on the /reconstruct conflict screen transplanted the source
collection's ENTRY into the merged COLLECTION beside base's own, so a base
holding three tracks wrote an output holding four, two of them carrying one
LOCATION. The primary key is derived from the location, so both answered to
the same key and the playlist's PRIMARYKEY for that track resolved against
both - the shape DL-004 forbids. A SOURCE pick means base's own entry carries
the source's values for the attributes that diverged.

| File | What |
| --- | --- |
| `plan.json` | The plan: overview, DL-116 through DL-129, and four milestones with their files, requirements, acceptance criteria, tests and code intents. No code_changes and no waves. |
| `context.json` | The task spec, constraints, entry points, the measured defect and the invisible knowledge the plan was designed against. |
| `qr-plan-design.json` | The quality-review pass over the plan's design. |

It follows directly from `docs/plans/2026-08-31-conflict-resolution/`, which is
implemented and committed as far as its M-004. That plan's M-005 has not
landed, so DL-104 through DL-115 are minted and cited across six files with no
statement of their own in `traktor_nml/README.md`. M-004 here writes DL-104
through DL-128 into that log, absorbing the eleven statements the earlier plan
owes, so no cited id resolves to nothing.

The acceptance step is a served-page gate run from
`C:\codex\traktor-nml-tool-gate` over the reconstruct-conflict fixture, judged
on the written file's entry count, its LOCATION multiplicities and its
line-terminator counts rather than on a substring of it.

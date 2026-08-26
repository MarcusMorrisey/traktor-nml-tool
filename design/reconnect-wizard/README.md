# Reconnect wizard - design brief

## Overview

Phase 1 visual and interaction design for the one workflow in
[`docs/nicegui-gui-analysis.md`](../../docs/nicegui-gui-analysis.md):
**"my playlists are broken"** - they still exist, but their tracks will not load
because the files moved.

Not implemented. This is the design the GUI is built against, not a record of
what exists.

The canvas is published at
<https://claude.ai/code/artifact/39e2990e-499e-4614-b04b-91fac131f8c6>.
Edit the sources here and re-seed - the regenerate command is in
[CLAUDE.md](CLAUDE.md) - then republish to that same url with
`contract: "0.1.31"` and no `capabilities`. The generated bundle is
gitignored; only the sources are committed.

## Architecture

Each `.dc.html` is one screen and `canvas.json` lays them out; the file index is
in [CLAUDE.md](CLAUDE.md). `Specs.dc.html` is not a screen but the contract the
others are built against: keyboard map, confidence tokens, accept/reject rules,
a11y rules. **If a screen and `Specs.dc.html` disagree, fix `Specs.dc.html`
first** - otherwise a per-screen fix silently forks the rule for every other
screen that shares it.

## Invariants

These are safety properties of the workflow, not stylistic preferences. A screen
edit that breaks one is a behaviour change:

- Preview always precedes a write; `--dry-run` is a phase, never a checkbox.
- An output colliding with an input **disables** writing, with an inline reason.
- Fingerprinting may be unavailable; the control is disabled *and explains why*.
- The tag cache is the only file written before confirmation, and says so.
- Every final collection write needs explicit confirmation. `Enter` never writes.
- Confidence and error state never rely on colour alone - shape, word and column
  position each carry the signal independently.

## Numbers

All counts are illustrative, not measured - but they reconcile across screens.
Keep them consistent when editing, so a reader comparing two screens does not
read the difference as a design decision.

Of 12,418 tracks the scan ends with **10,932 found**, **1,108 needing review**,
**34 refuted**, **96 re-encoded** and **248 not found**. The first four of those
are what the review table shows by default, so the queue is **1,238**.

Mid-review, the state the Review, Outcomes and Confirm screens all depict:
**457 accepted** (412 ordinary, 14 refuted, 31 re-encoded), **88 left missing**,
**693 still undecided**. That writes **11,389 repointed** and leaves **1,029**
exactly as they are. 26 playlists, 21 complete after the write.

## Statuses

Six, and the wizard never blurs them together, because three of them ask
different questions:

| Status | What the operator is deciding |
| --- | --- |
| Needs review | Is this the right file? |
| Refuted | Found it, but the length contradicts - accept anyway? |
| Re-encoded | Same track, different format - take it? |

`Refuted` and `Re-encoded` each carry their own filter chip and count, and both
sit in the default view. A refuted candidate is not a missing file, and a count
you cannot filter to is a count you cannot work through.

**Neither adds a status colour.** Yellow says a row wants a decision; the icon
silhouette and the written word say which decision, both in the first column.
That is deliberate: adding a hue would mean re-running the protanopia /
deuteranopia / tritanopia simulation behind the palette, and nothing here needs
one.

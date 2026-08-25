# Reconnect wizard - design brief

## Overview

Phase 1 visual and interaction design for the one workflow in
[`docs/nicegui-gui-analysis.md`](../../docs/nicegui-gui-analysis.md):
**"my playlists are broken"** - they still exist, but their tracks will not load
because the files moved.

Not implemented. This is the design the GUI is built against, not a record of
what exists.

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

All counts are illustrative, not measured - but they reconcile across screens
(12,418 tracks; 10,932 found, 1,204 to review, 282 not found; 26 playlists, 21
complete after the write). Keep them consistent when editing, so a reader
comparing two screens does not read the difference as a design decision.

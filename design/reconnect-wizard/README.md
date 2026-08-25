# Reconnect wizard — design brief

Phase 1 visual and interaction design for the one workflow in
[`docs/nicegui-gui-analysis.md`](../../docs/nicegui-gui-analysis.md):
**"my playlists are broken"** — they still exist, but their tracks will not load
because the files moved.

Not implemented. This is the design the GUI is built against.

## Files

Each `.dc.html` is one screen. `canvas.json` lays them out on a two-page canvas.

| File | Screen |
| --- | --- |
| `Main.dc.html` | 1 · Set up — collection, scan roots, matching, tag-cache disclosure |
| `Scanning.dc.html` | 2 · Scan in progress — progress, live counts, activity log |
| `Cancelling.dc.html` | 2b · Stopping — confirm, bounded termination, stopped outcome |
| `Results.dc.html` | 3 · Scan results — playlist-first summary, breakdown, CSV export |
| `Review.dc.html` | 3b · Guided review — table, filters, candidate comparison |
| `Confirm.dc.html` | 4 · Before the write — pre-write summary and final confirmation |
| `Success.dc.html` | 4b · Written — files written, what to do in Traktor |
| `Errors.dc.html` | Five recoverable errors, including the two that disable writing |
| `Specs.dc.html` | Keyboard map, confidence tokens, accept/reject rules, a11y rules |

`Specs.dc.html` is the contract the other screens are built against. If a screen
and it disagree, fix `Specs.dc.html` first.

## Constraints the screens hold

- Preview always precedes a write; `--dry-run` is a phase, never a checkbox.
- An output colliding with an input **disables** writing, with an inline reason.
- Fingerprinting may be unavailable; the control is disabled *and explains why*.
- The tag cache is the only file written before confirmation, and says so.
- Every final collection write needs explicit confirmation. `Enter` never writes.
- Confidence and error state never rely on colour alone — shape, word and column
  position each carry the signal independently.

## Rebuilding the canvas

The published `reconnect-wizard.html` is a generated bundle (~2.3 MB) and is
gitignored. Regenerate it from these sources with the `design` skill's helper:

```
node <skill>/seed-canvas.mjs --template <skill>/payload.template.html \
  --out reconnect-wizard.html --title "Reconnect Wizard" \
  --artboard Main.dc.html --artboard Scanning.dc.html \
  --artboard Cancelling.dc.html --artboard Results.dc.html \
  --artboard Review.dc.html --artboard Confirm.dc.html \
  --artboard Success.dc.html --artboard Errors.dc.html \
  --artboard Specs.dc.html --canvas canvas.json
```

Edit the `.dc.html` sources, never the generated bundle.

## Numbers

All counts are illustrative, not measured — but they reconcile across screens
(12,418 tracks; 10,932 found, 1,204 to review, 282 not found; 26 playlists, 21
complete after the write). Keep them consistent when editing.

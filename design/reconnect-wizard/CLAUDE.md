# design/reconnect-wizard/

Phase 1 visual and interaction design for the reconnect workflow, and the four steps of the reconstruct workflow, which shares its shell and its Specs contract.

## Files

| File                  | What                                                          | When to read                                          |
| --------------------- | --------------------------------------------------------------- | -------------------------------------------------------- |
| `README.md`           | Constraints the screens hold, the Specs precedence rule, and the shared illustrative numbers | Editing any screen, or changing a safety-related interaction |
| `Specs.dc.html`       | Keyboard map, confidence tokens, accept/reject rules, a11y rules. The contract the other screens are built against | Changing any cross-screen rule - fix this before the screen that disagrees |
| `Main.dc.html`        | 1 - Set up: collection, scan roots, matching, tag-cache disclosure | Changing the setup step                                |
| `Scanning.dc.html`    | 2 - Scan in progress: progress, live counts, activity log      | Changing scan-progress feedback                        |
| `Cancelling.dc.html`  | 2b - Stopping: confirm, bounded termination, stopped outcome   | Changing cancellation behaviour                        |
| `Results.dc.html`     | 3 - Scan results: playlist-first summary, breakdown, CSV export | Changing how results are summarised                    |
| `Review.dc.html`      | 3b - Guided review: table, filters, candidate comparison       | Changing the review table or candidate comparison      |
| `Outcomes.dc.html`    | 3c - Refuted and re-encoded: both detail rails, and why each is its own status | Changing how a contradicted or a format-changed candidate is presented |
| `Confirm.dc.html`     | 4 - Before the write: pre-write summary and final confirmation | Changing the pre-write confirmation                    |
| `Success.dc.html`     | 4b - Written: files written, what to do in Traktor             | Changing the post-write screen                         |
| `Errors.dc.html`      | Five recoverable errors, including the two that disable writing | Adding an error state or changing recovery copy       |
| `Reconstruct.dc.html` | 1 - Set up for the second job: the collection to repair, the collections to take playlists from, the output, and the conflict policy | Changing the reconstruct page's setup step |
| `Preview.dc.html`     | 2 - Preview for the second job: the playlists that would be rebuilt and the entries each would gain, with nothing written | Changing what the preview reports, or the three playlists it cannot fill |
| `Resolve.dc.html`     | 3 - Resolve for the second job: the conflicting tracks, the distinct answers each offers, and which collection holds each | Changing how a conflict between two collections is presented or decided |
| `Write.dc.html`       | 4 - Write for the second job: the destination, what the new file will hold, and the confirmation the write needs | Changing the pre-write summary or the confirmation for the reconstruct workflow |
| `canvas.json`         | Three-page canvas layout for the artboards above                 | Adding, removing or repositioning a screen            |
| `reconnect-wizard.html` | Generated ~2.3 MB canvas bundle; gitignored                  | Never edit directly - regenerate from the sources above |

## Regenerate the canvas bundle

```bash
node <skill>/seed-canvas.mjs --template <skill>/payload.template.html   --out reconnect-wizard.html --title "Reconnect Wizard"   --artboard Main.dc.html --artboard Scanning.dc.html   --artboard Cancelling.dc.html --artboard Results.dc.html   --artboard Review.dc.html --artboard Outcomes.dc.html --artboard Confirm.dc.html   --artboard Success.dc.html --artboard Errors.dc.html   --artboard Specs.dc.html   --artboard Reconstruct.dc.html --artboard Preview.dc.html   --artboard Resolve.dc.html --artboard Write.dc.html --canvas canvas.json
```

`<skill>` is the `design` skill's directory. Edit the `.dc.html` sources, never
the generated bundle.

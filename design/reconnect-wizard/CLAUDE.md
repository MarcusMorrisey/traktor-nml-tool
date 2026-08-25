# design/reconnect-wizard/

Phase 1 visual and interaction design for the reconnect workflow; not implemented.

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
| `Confirm.dc.html`     | 4 - Before the write: pre-write summary and final confirmation | Changing the pre-write confirmation                    |
| `Success.dc.html`     | 4b - Written: files written, what to do in Traktor             | Changing the post-write screen                         |
| `Errors.dc.html`      | Five recoverable errors, including the two that disable writing | Adding an error state or changing recovery copy       |
| `canvas.json`         | Two-page canvas layout for the artboards above                 | Adding, removing or repositioning a screen            |
| `reconnect-wizard.html` | Generated ~2.3 MB canvas bundle; gitignored                  | Never edit directly - regenerate from the sources above |

## Regenerate the canvas bundle

```bash
node <skill>/seed-canvas.mjs --template <skill>/payload.template.html   --out reconnect-wizard.html --title "Reconnect Wizard"   --artboard Main.dc.html --artboard Scanning.dc.html   --artboard Cancelling.dc.html --artboard Results.dc.html   --artboard Review.dc.html --artboard Confirm.dc.html   --artboard Success.dc.html --artboard Errors.dc.html   --artboard Specs.dc.html --canvas canvas.json
```

`<skill>` is the `design` skill's directory. Edit the `.dc.html` sources, never
the generated bundle.

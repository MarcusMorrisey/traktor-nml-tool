# Handoff: reconnect wizard, next steps

Written 2026-08-26 to carry work into a fresh session. Everything below is
either a pointer into the repo or a fact the repo does not record.

## Repo state at handoff

`master`, latest tag `parity-baseline-v4`. `pytest tests/ -q` gives 191
passed, 3 skipped — the 3 skips are the fingerprint tier, `pyacoustid` and
`fpcalc` being absent, which is expected and documented.

**Other sessions commit to this repo in parallel.** `git fetch` and check
`HEAD` before committing; it moved beneath the last session repeatedly, and
`parity-baseline-v1..v3` were taken by work happening alongside.

## Read these before changing matching or the design

They carry reasoning that was expensive to establish. Do not re-derive it.

- `traktor_nml/README.md` — the decision log. **DL-040** (duration refutes,
  size only corroborates), **DL-041** (path-suffix tiers), **DL-044** (case
  folding), **DL-045** (format-change tiers).
- `docs/2026-08-25-matching-tolerance-decisions.md` — the measurements behind
  DL-040/041.
- `docs/nicegui-gui-analysis.md` — the GUI plan of record. §1 command tiers,
  §3 test strategy, §5 rollout, §6 packaging spike.
- `design/reconnect-wizard/README.md` — the design brief's invariants.
- `tests/baselines/manifest.schema.md` — parity-oracle rules and known gaps.

## Immediate task: three reviewable outcomes on the design canvas

Published canvas:
https://claude.ai/code/artifact/39e2990e-499e-4614-b04b-91fac131f8c6

Working files are `design/reconnect-wizard/*.dc.html` and `canvas.json`. Edit
those, re-seed with the `design` skill's `seed-canvas.mjs` (exact command in
`design/reconnect-wizard/CLAUDE.md`), then republish to the SAME url with
`contract: "0.1.31"` and no `capabilities`. The generated bundle is
gitignored; commit only the sources.

The review table today has Accepted / Needs review / Left missing / Not
found. Two more are needed, because they ask different questions:

| Outcome | What the operator is deciding |
| --- | --- |
| Needs review | Is this the right file? |
| **Refuted** | Found it, but the length contradicts — accept anyway? |
| **Re-encoded** | Same track, different format — take it? |

What to change:

1. **Review table** — refuted and re-encoded become their own statuses, each
   with its own filter chip and count. Today `refuted` is a sub-count of
   `unmatched`: right for the stats, wrong for the workflow, because you
   cannot filter to what you cannot see.
2. **Detail rail** — show the contradicting field, quantified
   (`Length  8:50  ✕ DIFFERS  +87s`). For a re-encode show the evidence
   *for* it: the name matches but for the format, the length matches to
   0.2 s, the size is 3.9× as expected for four stems.
3. **Pre-write summary** — separate lines. Accepting a refuted candidate
   overrides a positive contradiction; accepting a re-encode changes the
   track's format in Traktor. Neither is the same decision as resolving a
   weak match.
4. **`Specs.dc.html`** — add the two status tokens, and record that
   re-encoded candidates come from loose-level tiers which the wizard
   surfaces as review rather than as a `--match-confidence` flag the operator
   must know exists.

Two calls already made: accepting a refuted candidate needs **no extra
friction** (the rail already shows exactly what contradicts), and refuted
**defaults into the review queue** rather than sitting behind a filter.

## Constraints that must hold

From `design/reconnect-wizard/README.md`. A screen edit that breaks one of
these is a behaviour change, not a style change.

- Preview always precedes a write; `--dry-run` is a phase, never a checkbox.
- An output colliding with an input **disables** writing, with an inline
  reason.
- Fingerprinting may be unavailable; the control is disabled *and explains
  why*.
- The tag cache is the only file written before confirmation, and says so.
- Every final collection write needs explicit confirmation. `Enter` never
  writes.
- **Confidence and error state never rely on colour alone** — shape, word and
  column position each carry the signal independently. The palette is
  Okabe-Ito-derived and verified against simulated protanopia, deuteranopia
  and tritanopia, worst-case ΔE 22.6 between status colours. Adding a status
  colour means re-running that check, not eyeballing it.

## Working conventions this project has earned

- **Verify against the real corpus; do not reason from plausibility.** Nearly
  every important finding in the last session contradicted a confident
  assumption, several of them the assistant's own.
- **A guard you have only seen pass is not a guard.** Prove a test fails when
  its invariant breaks. Several tests here do that deliberately, and say so.
- **Never regenerate `manifest.json` to make a test pass.** It is the
  behavioural contract. `PARITY_BASELINE_SHA256` in
  `tests/test_parity_baseline.py` moves only alongside a reviewed
  regeneration and a new `parity-baseline-vN` tag, with the diff reviewed
  case by case first.

## Real test corpus, not in git

- `collection_textual_patch_test.nml` in the repo root — 6,412 real entries,
  gitignored, present on the development machine only.
- `D:\Sync\FreqKing_V02` — 45,899 real audio files, the intended master copy.
- A full `scan-reconnect-candidates` run takes roughly 20 minutes. Last
  result: 5,063 matched (79%), 429 ambiguous, 725 unmatched, 195 destination
  collisions, 10 refuted. Of the 725 unmatched, 640 have no file of that name
  on the master copy at all — Mac-only tracks and unintegrated backups, which
  is correct behaviour rather than a gap.

## After the canvas

Plan §5 step 3 onward — the rest of the shared-core refactor. Steps 1 and 2
(scan progress and cancellation; owning the `fpcalc` child) are committed.

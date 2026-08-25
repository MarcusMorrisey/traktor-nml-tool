# Parity baseline oracle

## Overview

`manifest.json` records what every pinned CLI invocation produced - argv, exit
code, stdout, stderr and the bytes of every file written - so a refactor that
changes observable behaviour fails loudly instead of silently. The manifest is
the contract; `tests/test_baseline_parity.py` checks the tool against it.

## Architecture

Two guards sit at different levels, and the second exists because the first
cannot see its own foundation being moved:

- `test_baseline_parity.py` replays each stored case and compares the result to
  the manifest. It detects a change in the tool.
- `test_parity_baseline.py` pins `manifest.json`'s own SHA-256 in
  `PARITY_BASELINE_SHA256`. It detects a change in the manifest.

Without the second, regenerating the manifest turns a failing parity test green
and makes the pre-refactor behaviour unrecoverable - the oracle would validate
whatever the tool currently does, which is no oracle at all.

## Design Decisions

The pin is a literal constant rather than a comparison against a git tag, so it
runs under plain pytest: identically in CI, in a shallow clone, and on a
developer's machine with no network. Moving it is a one-line diff to a file
named for the purpose - the escalation path, not an accident.

`manifest.json` is written as explicit UTF-8 bytes with LF endings rather than
through text mode, and `.gitattributes` marks it `-text`. Text mode would emit
CRLF on Windows and LF elsewhere, so the same reviewed regeneration would hash
differently per host, and git would rewrite the blob on checkout.

## Invariants

- `PARITY_BASELINE_SHA256` moves **only** alongside a reviewed regeneration and
  a new `parity-baseline-vN` tag, in a change that names the behaviour
  difference. Updating both together to clear a red test is the same
  anti-pattern as regenerating to go green, just cheaper to perform.
- The suite is captured on one host but must pass on any:
  `test_no_stored_stream_carries_a_host_path_separator` enforces that no stored
  stream carries a host path separator.

## Required CI checks

- `pytest tests/test_parity_baseline.py` must run.
- Any job that diffs `manifest.json` against a `parity-baseline-vN` tag must
  **also** assert that tag still resolves to its recorded commit SHA. Tags here
  are protected only by a hook - GitHub rulesets need Pro or a public repo, and
  the legacy tag-protection API is gone - so a moved tag would move the
  comparison with it and the diff would pass vacuously.

## Current baseline

`parity-baseline-v3`, superseding `v2`. Known gaps in what the manifest covers
are recorded in [manifest.schema.md](manifest.schema.md).

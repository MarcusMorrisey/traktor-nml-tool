# tests/baselines/

## Files

| File                  | What                                                      | When to read                                              |
| ---------------------- | ------------------------------------------------------------| ------------------------------------------------------------ |
| `__init__.py`         | Package marker                                             | -                                                             |
| `manifest.json`       | Golden CLI-invocation baseline (argv, exit code, stdout/stderr, output file bytes) | Never edit directly - regenerate via `regenerate.py` |
| `manifest.schema.md`  | Field-by-field description of `manifest.json`'s schema and its regeneration invariant | Understanding a manifest entry's shape, or when regeneration is/isn't appropriate |
| `run_root.py`         | Shared run-directory substitution used by both the writer and the parity test | Changing which cases are compared byte-for-byte |
| `regenerate.py`       | Regenerates `manifest.json` from the current tool: `python -m tests.baselines.regenerate` | Deliberately updating the baseline after a reviewed behavior change |

## Regenerate

```bash
python -m tests.baselines.regenerate
```

Only run after a deliberate, reviewed behavior change - never to make a failing test pass (see `manifest.schema.md`).

## The hash pin

`tests/test_parity_baseline.py` pins `manifest.json`'s own SHA-256 in
`PARITY_BASELINE_SHA256`. **That constant moves only alongside a reviewed
regeneration and a new `parity-baseline-vN` tag**, in a commit that touches
nothing but the manifest and the constant and names the behaviour change.
Updating both together to clear a red test is the same anti-pattern as
regenerating to go green, just cheaper to perform.

## Required checks

- `pytest tests/test_parity_baseline.py` must run in CI.
- Any CI job that diffs `manifest.json` against the `parity-baseline-v1`
  tag must **also** assert that tag still resolves to its recorded commit
  SHA. A tag is only hook-protected here (GitHub rulesets need Pro or a
  public repo, and the legacy tag-protection API is gone), so a moved tag
  would otherwise move the comparison with it and the diff would pass
  vacuously.
- The suite is captured on one host but must pass on any:
  `test_no_stored_stream_carries_a_host_path_separator` enforces that no
  stored stream carries a host path separator.

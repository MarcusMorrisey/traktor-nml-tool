# tests/baselines/

## Files

| File                  | What                                                      | When to read                                              |
| ---------------------- | ------------------------------------------------------------| ------------------------------------------------------------ |
| `README.md`           | Why the hash pin exists, what it does and does not protect, and the CI checks it depends on | Moving `PARITY_BASELINE_SHA256`, or setting up CI for this directory |
| `__init__.py`         | Package marker                                             | -                                                             |
| `manifest.json`       | Golden CLI-invocation baseline (argv, exit code, stdout/stderr, output file bytes) | Never edit directly - regenerate via `regenerate.py` |
| `manifest.schema.md`  | Field-by-field description of `manifest.json`'s schema and its regeneration invariant | Understanding a manifest entry's shape, or when regeneration is/isn't appropriate |
| `run_root.py`         | Shared run-directory substitution used by both the writer and the parity test | Changing which cases are compared byte-for-byte |
| `regenerate.py`       | Regenerates `manifest.json` from the current tool: `python -m tests.baselines.regenerate` | Deliberately updating the baseline after a reviewed behavior change |

## Regenerate

```bash
python -m tests.baselines.regenerate
```

Only run after a deliberate, reviewed behavior change - never to make a failing
test pass. See [README.md](README.md) before moving the hash pin.

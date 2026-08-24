# tests/baselines/

## Files

| File                  | What                                                      | When to read                                              |
| ---------------------- | ------------------------------------------------------------| ------------------------------------------------------------ |
| `__init__.py`         | Package marker                                             | -                                                             |
| `manifest.json`       | Golden CLI-invocation baseline (argv, exit code, stdout/stderr, output file bytes) | Never edit directly - regenerate via `regenerate.py` |
| `manifest.schema.md`  | Field-by-field description of `manifest.json`'s schema and its regeneration invariant | Understanding a manifest entry's shape, or when regeneration is/isn't appropriate |
| `regenerate.py`       | Regenerates `manifest.json` from the current tool: `python -m tests.baselines.regenerate` | Deliberately updating the baseline after a reviewed behavior change |

## Regenerate

```bash
python -m tests.baselines.regenerate
```

Only run after a deliberate, reviewed behavior change - never to make a failing test pass (see `manifest.schema.md`).

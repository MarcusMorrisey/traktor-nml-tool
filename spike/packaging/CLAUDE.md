# spike/packaging/

Not part of the tool: a probe for the section 6 packaging checks. Results are
recorded in [docs/2026-08-25-packaging-spike-results.md](../../docs/2026-08-25-packaging-spike-results.md).

## Files

| File               | What                                                                 | When to read                                          |
| ------------------ | --------------------------------------------------------------------- | -------------------------------------------------------- |
| `checks.py`        | The check logic itself: `frozen_root`, `find_fpcalc`, `state_dir`     | Changing what a check asserts                          |
| `spike_app.py`     | NiceGUI window exercising the checks that need a UI (native dialogs, cold start) | Running checks 3, 4 and 5 on a clean machine  |
| `spike_checks.py`  | Headless runner for the checks that need no window (1, 2, 6, 7)      | Verifying a build from a shell or CI                   |
| `build.sh`         | `nicegui-pack --onedir --windowed` build, with the `PATH` fix nicegui-pack needs | Building either bundle                    |

## Build

```bash
./spike/packaging/build.sh
```

## Run the headless checks against a frozen bundle

```bash
SPIKE_NML=/path/to/collection.nml ./dist/spike-checks/spike-checks.exe
```

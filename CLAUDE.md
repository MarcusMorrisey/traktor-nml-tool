# traktor-nml-tool

A CLI for inspecting, repairing, merging, and splitting Traktor DJ software's `.nml` collection files.

## Files

| File                    | What                                                        | When to read                                    |
| ------------------------ | ------------------------------------------------------------ | ------------------------------------------------ |
| `traktor_nml_tool.py`   | Thin argv-forwarding shim into the `traktor_nml` package    | Changing the CLI entry point itself             |
| `README.md`             | User-facing overview, install, usage                         | Onboarding, understanding what the tool does    |
| `TODO.md`                | Remaining work: replace-playlist, guided repair review, and the parts of refined fuzzy matching `discovery.py` does not already cover | Picking up or scoping a future feature          |
| `LICENSE`                | GPL-2.0-only license text                                    | -                                                |
| `pytest.ini`             | Pytest configuration                                          | Changing test discovery or markers              |
| `.gitignore`             | Excludes caches, the personal collection fixture and its snapshots, tag caches, `/testing/`, the generated design bundle | Adding a new local-only artifact                |
| `.gitattributes`         | Pins `tests/baselines/manifest.json` to exact bytes (`-text`) | Changing how the parity manifest is stored      |

## Subdirectories

| Directory      | What                                              | When to read                                          |
| -------------- | -------------------------------------------------- | ------------------------------------------------------ |
| `traktor_nml/` | The package: parsing, matching, rewrite/reconnect/splice/split/build-playlist cores, and CLI subcommands | Implementing or modifying any tool behavior           |
| `tests/`       | Pytest suite, fixtures, and baseline-parity corpus | Adding or changing tests                               |
| `docs/`        | Retained planning material and development context | Looking up why a past design decision was made         |
| `design/`      | Design briefs and canvas sources for the unimplemented GUI | Working on the GUI's visual or interaction design       |

## Build

No build step; run directly with Python 3.10+.

## Test

```bash
pytest tests/ -q
```

## Development

See [README.md](README.md) for install instructions and [traktor_nml/README.md](traktor_nml/README.md) for architecture, design decisions, and invariants.

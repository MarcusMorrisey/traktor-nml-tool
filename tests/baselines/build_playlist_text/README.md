# build-playlist plain-text corpus

The recorded behaviour of `build-playlist` over a plain-text track list,
replayed byte for byte by `tests/test_build_playlist_text_parity.py`
(DL-279).

Recorded at commit `05f0c84`, before `tracklist.py`
or `buildplaylist.py` took the Candidate seam (DL-274). A recording taken
from any later commit would hold whatever that commit does, including a
regression, so the corpus is never re-recorded to make a replay pass.

## What each case directory holds

| File | Content |
|---|---|
| `argv.json` | The argument list, relative to the run's working directory |
| `stdout.txt` | Everything the CLI printed to stdout |
| `stderr.txt` | Everything the CLI printed to stderr |
| `exit_code.txt` | The exit code |
| `output.nml` | The written NML; absent when the run refused or ran with `--dry-run` |
| `unresolved.csv` | The unresolved report; present only for the case that asks for one |

## The fixture every case reads

No NML file is stored here. Every case reads `base.nml` and `tracks.txt`
as `_base_nml()` and `CASES` in the test module build them: five
entries, one of which (`Dup - Twice`) is held at two locations so a line
naming it is ambiguous, and a `Sets` folder under `$ROOT`. The case name
is the directory name and says what the case exercises.

`uuid.uuid4` is patched to `00000000-0000-4000-8000-000000000000`.

# tests/fixtures/

## Files

| File                | What                                                                 | When to read                                          |
| -------------------- | ----------------------------------------------------------------------| -------------------------------------------------------- |
| `__init__.py`        | Package marker                                                       | -                                                         |
| `build_fixtures.py`  | Builds the deterministic synthetic NML fixture corpus (moved paths, renamed files, duplicate rips, STEM entries, ampersand/non-ASCII text, nested playlist folders, empty playlist, SORTING_INFO, SETS), plus the sibling reconnect tree (stale collection + sized audio stubs) | Adding a new fixture scenario, changing existing fixture NML shapes or stub sizes |

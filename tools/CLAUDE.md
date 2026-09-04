# tools/

Repository-level maintenance scripts, kept out of `traktor_nml/` so nothing importable depends on them.

## Files

| File                 | What                                                                                                                                                                                     | When to read                                                                                          |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `preflight.py`       | Four fast session-start checks, each reporting `ok`/`BAD` and all of them running regardless of an earlier failure: which interpreter is in play and which optional packages it carries, that `core.hooksPath` is `hooks` so `hooks/pre-push` is not inert, that the wizard, plan and gate repositories resolve, and that `traktor_nml/gui/app.py` is wholly CRLF. Exit status 1 if anything is wrong; runs no suite | Starting a session, or adding a check for a control that fails silently                               |

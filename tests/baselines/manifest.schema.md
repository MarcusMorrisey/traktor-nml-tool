# tests/baselines/manifest.json

JSON array of recorded CLI invocations, one object per case:

- `argv`: argument list passed to `traktor_nml.cli.main`
- `exit_code`, `stdout`, `stderr`: expected process output
- `output_files`: relative path -> base64-encoded expected file bytes

manifest.json records the tool's output contract for this fixed set of
invocations: every case here must keep passing byte-for-byte. Regenerating
it is correct only against a deliberate, reviewed behavior change (see
regenerate.py's module docstring for the regeneration command) - never to
make a failing test pass, since that would silently rewrite the contract
it encodes.

This file itself holds no comments (JSON has none) - this document is
its comment.

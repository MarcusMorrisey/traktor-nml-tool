# tests/baselines/manifest.json

JSON array of recorded CLI invocations, one object per case:

- `argv`: argument list passed to `traktor_nml.cli.main`
- `exit_code`, `stdout`, `stderr`: expected process output
- `normalise_run_root`: when true, the run directory was substituted in
  this case's `stdout`, `stderr` and `output_files` before storing, and the
  parity test applies the same substitution before comparing (see below)
- `output_files`: relative path -> base64-encoded expected file bytes

manifest.json records the tool's output contract for this fixed set of
invocations: every case here must keep passing byte-for-byte. Regenerating
it is correct only against a deliberate, reviewed behavior change (see
regenerate.py's module docstring for the regeneration command) - never to
make a failing test pass, since that would silently rewrite the contract
it encodes.

This file itself holds no comments (JSON has none) - this document is
its comment.


## Run-root normalisation

`rewrite-from-reconnect` rebuilds a matched entry's LOCATION from the
candidate's resolved absolute path, so a rewritten `DIR` embeds the
directory the run happened in - which differs between the regeneration run
and every later test run. Such a case cannot be compared byte-for-byte as
captured.

Omitting a writing case instead would leave the rewritten LOCATION bytes
unpinned, which is exactly what a refactor of the write path could break.
So the case is kept and only the run directory is substituted, with a
`{RUN_ROOT}` token, by `run_root.py` - imported by both the writer
(`regenerate.py`) and the reader (`test_baseline_parity.py`) so the two
cannot disagree about what was relaxed.

The relaxation is **opt-in per case** via `normalise_run_root`, so every
other case stays provably strict. It is deliberately narrow: in a stored
matched-write output the token replaces only the run-directory prefix -

    DIR="{RUN_ROOT}/:recon/:audio/:moved/:"

leaving the folder structure, filename, VOLUME and VOLUMEID pinned exactly.
`test_normalised_case_still_detects_a_non_run_root_byte_change` proves the
relaxation cannot mask a change outside that prefix.

## Line endings

`manifest.json` is written as explicit UTF-8 bytes with LF endings, and
`.gitattributes` marks it `-text` so git never rewrites the blob on
checkout. Both are load-bearing: the file is pinned by SHA-256, so a CRLF
round-trip would change the digest without changing the content, and the
failure would be invisible in `git diff`.

## Known gaps in coverage

Recorded so an absence is not mistaken for a guarantee:

- **The acoustic-fingerprint tier is unpinned.** `HAS_ACOUSTID` gates on
  importing the `acoustid` module alone, but the tier needs THREE things:
  the module, the `fpcalc` binary (to fingerprint), and the chromaprint
  shared library (to compare - the standalone fpcalc build does not ship
  it). With the module present and either of the other two missing,
  `HAS_ACOUSTID` still reports True and the tier matches nothing;
  `tests/test_fingerprint.py` probes each dependency separately rather
  than trusting the flag. Pinning it would put a third-party
  dependency behind the oracle, so no baseline to date covers it. The
  commit that gives the scan its own `fpcalc` subprocess must add a case
  under a reviewed re-tag of its own.
- **The lxml and stdlib write paths were verified equivalent for this
  corpus** (the manifest regenerates byte-identically either way), but that
  is verified on small synthetic fixtures, not proven for a real
  multi-megabyte collection.

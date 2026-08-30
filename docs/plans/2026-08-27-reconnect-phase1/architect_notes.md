# Architect exploration notes (steps 1-3), traktor-nml-tool NiceGUI Phase 1

## Environment / test-harness findings (HARD, verified)
- Suite runs on SYSTEM python3 3.14 (pytest 9.0.3). `python3 -m pytest tests/ -q` -> 243 passed, 3 skipped.
- System python3 has NO nicegui. `.venv` HAS nicegui 3.16.0 + pywebview 6.2.1 but NO pytest.
- => Any new test that imports nicegui would ERROR (or add a 4th skip via importorskip), breaking the
  "at least 243 passed / at most 3 skipped" constraint.
- => ALL testable GUI logic must live in nicegui-free modules under traktor_nml/gui/;
  only a thin view module may import nicegui, and it must be import-guarded in tests.
- pyproject `[tool.setuptools] packages = ["traktor_nml", "traktor_nml.commands"]` is an EXPLICIT list.
  Adding traktor_nml/gui/ requires adding "traktor_nml.gui" there or it is not installed.

## Decision log high-water mark
- DL-057 is the highest in traktor_nml/README.md. Plan DL ids must start at DL-058.

## Renderer separability (assumption resolved: TRUE)
- reconnect_render.render_scan_reconnect_candidates / render_rewrite_from_reconnect return a
  RenderedOutput(stdout_lines, stderr_lines, exit_code) dataclass; `emit` is the ONLY stream writer.
  The GUI can call render_*() and feed .stdout_lines/.stderr_lines to ui.log without touching emit.

## Blocking architectural gap 1 - the write path re-scans
- rewrite_from_reconnect() calls run_reconnection() INSIDE plan_and_write_nml's callback
  (_collect_patches / mutate_tree). So "scan -> review -> write" via that entry point re-runs the
  20-minute scan and discards operator overrides. A mapping-injection write path is required.
- plan_and_write_nml checks output-vs-input collision FIRST, before parsing and before either
  callback, so a refused write costs nothing.

## Blocking architectural gap 2 - the review data does not exist
- ReconnectResult carries: mapping{primary_key -> EntryRecord}, stats, ambiguity_rows, old_records,
  warnings, diagnostics.
- ambiguity_rows are PLAIN STRINGS only: {artist, title, old_path, reason} with
  reason in {destination_collision, ambiguous, unmatched}. No candidate objects, no confidence,
  no per-candidate detail.
- design/reconnect-wizard/Specs.dc.html requires SIX statuses (matched / ambiguous / refuted /
  format[re-encoded] / rejected / no_match), per-row candidate lists (keys 1-9 pick a candidate),
  per-candidate confidence (strict/normal/loose/no_match), and a detail panel naming and
  quantifying the contradicting field for a refuted row.
- None of that survives resolve_reconnection: match_records computes per-record candidate buckets
  and refutation internally and discards them; stats["refuted"] is a bare count.
- Accept-an-alternative override is therefore NOT expressible from today's ReconnectResult.
  Reject-a-proposed-match IS (drop the key from mapping).
- _reencode_winning_locations only re-encodes LOCATIONs for records already in mapping, so any
  candidate accepted later by an operator needs the same re-encode applied.

## Other confirmed facts
- diskscan.ScanCancelled is an exception, never caught on the core or write path.
- index_scan_roots(scan_roots, cache, *, refresh_cache, progress_every, stats, on_progress,
  cancel, callback_every, on_diagnostic); all callbacks default None and inert.
- Design brief published as a canvas; screens Main/Scanning/Cancelling/Results/Review/Outcomes/
  Confirm/Success/Errors + Specs (Specs wins on conflict).
- Design invariants: preview always precedes write; output-collides-with-input DISABLES write with
  inline reason; fingerprint control disabled WITH explanation; tag cache is the only file written
  before confirmation and says so; Enter never writes; no colour-only signalling.

## Testing strategy (settled from repo, no user input needed)
- pytest, tests/ package, conftest run_tool + fixture_corpus (fixture corpus + sibling recon tree).
- Guard tests must construct the broken scenario in executable code and record the mutation and the
  observed output in the docstring.
- §3.3 acceptance criteria expressed against cores and the write path, not DOM.
- manifest.json and PARITY_BASELINE_SHA256 untouched; non-regeneration is the proof.

## Questions put to the user (step 3->4 yield)
1. Review fidelity: inert per-record review channel in the core (full design fidelity) vs
   reject-only review from today's ReconnectResult (no core change).
2. Write path: shared write_reconnect_result() in reconnect_run.py that rewrite_from_reconnect also
   uses (byte-identity structural) vs a GUI-local composition of plan_and_write_nml
   (no core file touched, byte-identity proven only by test).

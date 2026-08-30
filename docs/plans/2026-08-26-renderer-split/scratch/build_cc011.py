import re

orig = open('C:/Users/marcu/AppData/Local/Temp/planner-e70yv3f4/CC011_orig.diff', encoding='utf-8').read()
lines = orig.split('\n')
# body lines start at index 3 (0-based), all start with '+'
body = [l[1:] for l in lines[3:] if l != '']  # drop trailing empty from split
# actually last line might be '+    assert ...error' with no trailing blank; check
# reconstruct content
content_lines = []
for l in lines[3:]:
    if l == '':
        continue
    assert l.startswith('+'), repr(l)
    content_lines.append(l[1:])

content = '\n'.join(content_lines) + '\n'

insert_A = '''

def test_fingerprint_warning_absent_when_reason_returns_none(
    fixture_corpus: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control for test_fingerprint_warning_lands_in_result_not_printed_by_core:
    proves the warning assertions above actually depend on
    fingerprint_unavailable_reason() returning a reason, by monkeypatching it to
    return None instead of "stub reason" and observing the warning disappear from
    both ReconnectResult.warnings and the rendered stderr. Observed to fail
    test_fingerprint_warning_lands_in_result_not_printed_by_core's warning
    assertions when this stub replaces the "stub reason" stub."""
    if reconnect_run.fingerprint_key_provider is None:
        pytest.skip("fingerprint.py not present")

    monkeypatch.setattr(reconnect_run, "fingerprint_unavailable_reason", lambda: None)

    argv = _SCAN_ARGV + ["--fingerprint"]
    args = _parse_args(argv)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        result = reconnect_run.scan_reconnect_candidates(args)
    finally:
        os.chdir(old_cwd)

    assert result.result is not None
    assert not any("stub reason" in warning for warning in result.result.warnings)
    rendered = render_scan_reconnect_candidates(result, args)
    assert not any(
        line.startswith("fingerprint_dependency_missing=") for line in rendered.stderr_lines
    )'''

insert_B = '''

def test_fingerprint_key_provider_present_does_not_raise_unavailable(
    fixture_corpus: Path,
) -> None:
    """Negative control for test_fingerprint_key_provider_none_raises: proves the
    fingerprint_unavailable= error above is actually caused by
    fingerprint_key_provider being None, not by the --fingerprint flag on its own,
    by leaving fingerprint_key_provider at its normal bound value and observing no
    such error. Observed to fail test_fingerprint_key_provider_none_raises'
    assertion when run without the monkeypatch that sets the provider to None."""
    if reconnect_run.fingerprint_key_provider is None:
        pytest.skip("fingerprint.py not present")

    argv = _SCAN_ARGV + ["--fingerprint"]
    args = _parse_args(argv)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        result = reconnect_run.scan_reconnect_candidates(args)
    finally:
        os.chdir(old_cwd)

    assert result.error is None or not result.error.startswith("fingerprint_unavailable=")'''

insert_C = '''

def test_cancel_not_set_does_not_raise_scan_cancelled(fixture_corpus: Path) -> None:
    """Negative control for test_on_progress_fires_and_cancel_raises: proves the
    ScanCancelled raise above is actually gated on the cancel token being set,
    not raised unconditionally by run_reconnection, by passing an unset Event
    and observing the run complete instead of raising. Observed to fail
    (raise ScanCancelled) if run_reconnection ignored the cancel token's
    state rather than checking it."""
    args = _parse_args(_SCAN_ARGV)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        old_root = parse_xml(args.old_input).getroot()
        cancel = threading.Event()
        result = reconnect_run.run_reconnection(args, old_root, cancel=cancel)
    finally:
        os.chdir(old_cwd)

    assert result is not None'''

insert_D = '''

def test_output_differs_from_input_starts_reconnection(fixture_corpus: Path) -> None:
    """Negative control for test_output_equal_to_input_never_starts_reconnection:
    proves the refusal above is gated on output_path equaling input_path, not on
    rewrite-from-reconnect refusing to reconnect regardless of the paths given,
    by pointing output at a different path and observing reconnection actually
    starts. Observed to fail (reconnect is None) if the equality check applied
    to differing paths as well."""
    argv = [
        "rewrite-from-reconnect", "recon/stale.nml", "out/reconnected.nml",
        "--scan-root", "recon/audio",
        "--volume-map", "recon/audio", "D:", "D:",
        "--match-confidence", "filename",
        "--cache", "out/recon.tagcache.json",
        "--dry-run",
    ]
    args = _parse_args(argv)
    old_cwd = Path.cwd()
    os.chdir(fixture_corpus.parent)
    try:
        result = reconnect_run.rewrite_from_reconnect(args)
    finally:
        os.chdir(old_cwd)

    assert result.reconnect is not None'''

anchor_A = '    assert rendered.stderr_lines[0].startswith("fingerprint_dependency_missing=stub reason")\n'
anchor_B = '    assert result.error is not None and result.error.startswith("fingerprint_unavailable=")\n'
anchor_C = '    finally:\n        os.chdir(old_cwd)\n\n\ndef test_output_equal_to_input_never_starts_reconnection'
anchor_D_end = '    assert result.outcome is not None and result.outcome.error == "output_must_differ_from_input"\n'

assert content.count(anchor_A) == 1
content = content.replace(anchor_A, anchor_A + insert_A + '\n', 1)

assert content.count(anchor_B) == 1
content = content.replace(anchor_B, anchor_B + insert_B + '\n', 1)

assert content.count(anchor_C) == 1
content = content.replace(anchor_C, '    finally:\n        os.chdir(old_cwd)' + insert_C + '\n\n\ndef test_output_equal_to_input_never_starts_reconnection', 1)

assert content.endswith(anchor_D_end)
content = content[: -len(anchor_D_end)] + anchor_D_end + insert_D + '\n'

open('C:/Users/marcu/AppData/Local/Temp/planner-e70yv3f4/CC011_new_content.py', 'w', encoding='utf-8', newline='\n').write(content)
print('new line count', content.count('\n'))

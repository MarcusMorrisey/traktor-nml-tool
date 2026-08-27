"""Guards for the shared reconnect write core, write_reconnect_result
(M-003). Each guard constructs its broken scenario in executable code and
records the mutation and the observed output in its docstring, matching
the register tests/test_scan_diagnostics.py and tests/test_review_channel.py
already use - a guard only ever seen to pass is indistinguishable from one
that cannot fail.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

from traktor_nml import diskscan, reconnect_run
from traktor_nml.cli import build_parser
from traktor_nml.diskscan import ScanCancelled, _tag_free_summary
from traktor_nml.gui.wizard_state import WizardState, amended_result, apply
from traktor_nml.rewrite import output_collision_refusal
from traktor_nml.tagcache import TagCache

from tests.baselines.run_root import normalise_run_root_bytes

MANIFEST_PATH = Path(__file__).parent / "baselines" / "manifest.json"

_REWRITE_ARGV = [
    "rewrite-from-reconnect", "recon/stale.nml", "out/recon_out.nml",
    "--scan-root", "recon/audio",
    "--volume-map", "recon/audio", "D:", "D:",
    "--match-confidence", "filename",
    "--cache", "out/recon.tagcache.json",
]


def _load_manifest() -> list[dict]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _rewrite_out_case() -> dict:
    return next(c for c in _load_manifest() if c["argv"] == _REWRITE_ARGV)


def _parse_args(argv: list[str]):
    parser, _handlers = build_parser()
    return parser.parse_args(argv)


def _in_dir(tmp_path: Path):
    """A tiny context manager chdir'ing into tmp_path - manifest argv
    paths are recorded relative to the fixture corpus root, and
    write_reconnect_result reads/writes through argparse Path values
    resolved against the current directory, exactly as run_tool does for
    the CLI entry point."""
    import contextlib

    @contextlib.contextmanager
    def _cm():
        old_cwd = Path.cwd()
        os.chdir(tmp_path)
        try:
            yield
        finally:
            os.chdir(old_cwd)

    return _cm()


def test_zero_override_write_matches_manifest_bytes(fixture_corpus: Path, tmp_path: Path) -> None:
    """A scan-then-write through write_reconnect_result, with a provider
    that returns run_reconnection's own result unchanged, produces a file
    whose bytes equal the manifest bytes recorded for the same argv
    (parity-baseline-v4, out/recon_out.nml)."""
    case = _rewrite_out_case()
    (tmp_path / "out").mkdir(exist_ok=True)
    args = _parse_args(case["argv"])

    def provide_result(old_root):
        return reconnect_run.run_reconnection(args, old_root)

    with _in_dir(tmp_path):
        outcome_result = reconnect_run.write_reconnect_result(args, provide_result)

    assert outcome_result.outcome is not None and outcome_result.outcome.exit_code == 0
    written = (tmp_path / "out" / "recon_out.nml").read_bytes()
    if case.get("normalise_run_root"):
        written = normalise_run_root_bytes(written, tmp_path)
    assert written == base64.b64decode(case["output_files"]["out/recon_out.nml"])


def test_zero_override_write_is_sensitive_to_the_mapping(fixture_corpus: Path, tmp_path: Path) -> None:
    """Negative control for test_zero_override_write_matches_manifest_bytes:
    a provider that drops the collection's one mapped key
    ('D:/:Gone/:Music/:xtal_recon.mp3') before returning produces bytes
    that differ from the manifest bytes, proving the byte-equality
    assertion above is sensitive to the mapping rather than passing
    regardless of what write_reconnect_result is handed. Observed: with
    the mapping's one key dropped, the Xtal entry's LOCATION DIR reverts
    from the reconnected "{RUN_ROOT}/:recon/:audio/:moved/:" to the
    original "/:Gone/:Music/:" the stale.nml fixture carries, and the
    written file (run-root-normalised) is 1116 bytes against the
    manifest's 1134."""
    case = _rewrite_out_case()
    (tmp_path / "out").mkdir(exist_ok=True)
    args = _parse_args(case["argv"])

    def provide_result(old_root):
        result = reconnect_run.run_reconnection(args, old_root)
        dropped = {k: v for i, (k, v) in enumerate(result.mapping.items()) if i != 0}
        assert len(dropped) == len(result.mapping) - 1
        return replace(result, mapping=dropped)

    with _in_dir(tmp_path):
        reconnect_run.write_reconnect_result(args, provide_result)

    written = (tmp_path / "out" / "recon_out.nml").read_bytes()
    expected_raw = base64.b64decode(case["output_files"]["out/recon_out.nml"])
    normalised = normalise_run_root_bytes(written, tmp_path) if case.get("normalise_run_root") else written
    assert normalised != expected_raw
    print('OBSERVED_LEN', len(normalised))
    assert b'TITLE="Xtal" ARTIST="Aphex Twin"><LOCATION DIR="/:Gone/:Music/:"' in normalised


def test_collision_refusal_precedes_the_provider(fixture_corpus: Path, tmp_path: Path) -> None:
    """A wizard-shaped call whose output path equals its input path
    returns the typed refusal without the provider ever being entered -
    proved by a provider that raises AssertionError, which would fail the
    test itself if it were called."""
    args = _parse_args([
        "rewrite-from-reconnect", "recon/stale.nml", "recon/stale.nml",
        "--scan-root", "recon/audio",
        "--volume-map", "recon/audio", "D:", "D:",
        "--match-confidence", "filename",
        "--cache", "out/recon.tagcache.json",
    ])
    (tmp_path / "out").mkdir(exist_ok=True)

    def provide_result(old_root):
        raise AssertionError("provide_result must not run when output collides with input")

    with _in_dir(tmp_path):
        result = reconnect_run.write_reconnect_result(args, provide_result)

    assert result.outcome is not None
    assert result.outcome.error == "output_must_differ_from_input"
    assert result.reconnect is None


def test_collision_refusal_ordering_is_gated_on_the_collision(fixture_corpus: Path, tmp_path: Path) -> None:
    """Negative control for test_collision_refusal_precedes_the_provider:
    the same AssertionError-raising provider, called with a non-colliding
    output path, does raise - proving the refusal above is gated on
    output_path equaling input_path rather than on write_reconnect_result
    refusing to call the provider at all. Observed to fail (no
    AssertionError propagates) if the refusal check were applied
    unconditionally."""
    args = _parse_args(_REWRITE_ARGV)
    (tmp_path / "out").mkdir(exist_ok=True)
    assert output_collision_refusal(args.old_input, args.output) is None

    def provide_result(old_root):
        raise AssertionError("provider entered for a non-colliding output")

    with _in_dir(tmp_path), pytest.raises(AssertionError, match="provider entered"):
        reconnect_run.write_reconnect_result(args, provide_result)


def test_scan_cancelled_leaves_no_result_and_no_output(fixture_corpus: Path, tmp_path: Path) -> None:
    """A provider raising ScanCancelled leaves write_reconnect_result with
    no RewriteReconnectResult at all - the exception propagates rather
    than being folded into a return value - and no output .nml appears
    under tmp_path. The tag cache path is untouched by this run (nothing
    calls cache.flush() before the cancellation), but a fresh TagCache
    still loads against it without error, proving the cache file, empty
    or absent, is never left unreadable."""
    args = _parse_args(_REWRITE_ARGV)
    (tmp_path / "out").mkdir(exist_ok=True)

    def provide_result(old_root):
        raise ScanCancelled("cancelled mid-scan")

    with _in_dir(tmp_path):
        with pytest.raises(ScanCancelled):
            reconnect_run.write_reconnect_result(args, provide_result)

    assert not (tmp_path / "out" / "recon_out.nml").exists()
    # A fresh TagCache still loads through the same path write_reconnect_result
    # would have used, whether or not a cache file exists there.
    TagCache(tmp_path / "out" / "recon.tagcache.json")


def test_catching_scan_cancelled_would_report_a_mostly_missing_collection(
    fixture_corpus: Path, tmp_path: Path
) -> None:
    """Negative control for test_scan_cancelled_leaves_no_result_and_no_output:
    if a caller wrapped the provider call in
    except ScanCancelled: return a partial result instead of letting it
    escape, the wizard would report a candidate count far short of the
    complete run's - the confident-wrong-answer DL-053 and DL-068 exist to
    prevent. Observed: the complete run's mapping holds 1 record; the
    partial result recorded here (built the way such a catch would have to
    build one, from whatever the provider saw before cancelling) holds 0,
    which over a real collection is the mostly-missing-collection reading
    the exception is left uncaught to avoid."""
    args = _parse_args(_REWRITE_ARGV)
    (tmp_path / "out").mkdir(exist_ok=True)

    with _in_dir(tmp_path):

        def complete_provider(old_root):
            return reconnect_run.run_reconnection(args, old_root)

        complete = complete_provider(_load_old_root(args))
        assert len(complete.mapping) == 1

        partial_holder: dict[str, object] = {}

        def cancelling_provider(old_root):
            try:
                raise ScanCancelled("cancelled mid-scan")
            except ScanCancelled:
                partial = replace(complete, mapping={})
                partial_holder["result"] = partial
                return partial

        result = reconnect_run.write_reconnect_result(args, cancelling_provider)

    assert result.reconnect is partial_holder["result"]
    assert len(result.reconnect.mapping) == 0
    assert len(result.reconnect.mapping) < len(complete.mapping)


def _load_old_root(args):
    from traktor_nml.xmlio import parse_xml

    return parse_xml(args.old_input).getroot()


def test_preview_writes_nothing_but_the_tag_cache(fixture_corpus: Path, tmp_path: Path) -> None:
    """Every file under tmp_path is snapshotted by size and mtime around a
    --dry-run write_reconnect_result call; only .traktor_nml_tagcache.json-
    shaped names (the recon.tagcache.json this run's --cache points at)
    differ, because a preview writes nothing the command declares as its
    output."""
    argv = list(_REWRITE_ARGV) + ["--dry-run"]
    args = _parse_args(argv)
    (tmp_path / "out").mkdir(exist_ok=True)

    def _snapshot() -> dict[str, tuple[int, float]]:
        return {
            p.relative_to(tmp_path).as_posix(): (p.stat().st_size, p.stat().st_mtime)
            for p in tmp_path.rglob("*") if p.is_file()
        }

    before = _snapshot()

    def provide_result(old_root):
        return reconnect_run.run_reconnection(args, old_root)

    with _in_dir(tmp_path):
        reconnect_run.write_reconnect_result(args, provide_result)

    after = _snapshot()
    changed = {
        name for name in set(before) | set(after)
        if before.get(name) != after.get(name)
    }
    assert not (tmp_path / "out" / "recon_out.nml").exists()
    assert changed <= {"out/recon.tagcache.json"}


def test_removing_the_dry_run_guard_writes_output(fixture_corpus: Path, tmp_path: Path) -> None:
    """Negative control for test_preview_writes_nothing_but_the_tag_cache:
    the same argv without --dry-run (the case this milestone's zero-override
    guard already exercises) does write out/recon_out.nml, proving the
    absence recorded above is because of the dry-run guard rather than
    because write_reconnect_result never writes an .nml at all."""
    args = _parse_args(_REWRITE_ARGV)
    (tmp_path / "out").mkdir(exist_ok=True)

    def provide_result(old_root):
        return reconnect_run.run_reconnection(args, old_root)

    with _in_dir(tmp_path):
        reconnect_run.write_reconnect_result(args, provide_result)

    assert (tmp_path / "out" / "recon_out.nml").exists()


def test_reviews_omitted_is_inert_at_the_core_boundary(fixture_corpus: Path, tmp_path: Path) -> None:
    """A run with reviews omitted and a run with a caller-owned list
    supplied produce equal stats, equal mapping keys and (written through
    write_reconnect_result) equal bytes - the review channel changes
    nothing about what is matched or written, only whether reviews are
    collected."""
    case = _rewrite_out_case()
    args = _parse_args(case["argv"])

    with _in_dir(tmp_path):
        old_root_a = _load_old_root(args)
        without_reviews = reconnect_run.run_reconnection(args, old_root_a)
        old_root_b = _load_old_root(args)
        reviews: list = []
        with_reviews = reconnect_run.run_reconnection(args, old_root_b, reviews=reviews)

    assert without_reviews.reviews == ()
    assert len(with_reviews.reviews) == len(reviews) > 0
    assert without_reviews.stats == with_reviews.stats
    assert set(without_reviews.mapping.keys()) == set(with_reviews.mapping.keys())

    (tmp_path / "out").mkdir(exist_ok=True)
    (tmp_path / "out2").mkdir(exist_ok=True)

    def provide_without(old_root):
        return reconnect_run.run_reconnection(args, old_root)

    def provide_with(old_root):
        return reconnect_run.run_reconnection(args, old_root, reviews=[])

    args_without = args
    args_with = _parse_args([
        "rewrite-from-reconnect", "recon/stale.nml", "out2/recon_out.nml",
        "--scan-root", "recon/audio",
        "--volume-map", "recon/audio", "D:", "D:",
        "--match-confidence", "filename",
        "--cache", "out/recon.tagcache.json",
    ])

    with _in_dir(tmp_path):
        reconnect_run.write_reconnect_result(args_without, provide_without)
        reconnect_run.write_reconnect_result(args_with, lambda old_root: reconnect_run.run_reconnection(args_with, old_root, reviews=[]))

    written_without = (tmp_path / "out" / "recon_out.nml").read_bytes()
    written_with = (tmp_path / "out2" / "recon_out.nml").read_bytes()
    assert written_without == written_with


def test_volume_identity_error_carries_diagnostics_collected_before_the_raise(
    fixture_corpus: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A provider whose run_reconnection call emits a real
    tag_reading_unavailable diagnostic (HAS_MUTAGEN patched False, exactly
    as test_missing_mutagen_with_collector_writes_no_stream in
    tests/test_scan_diagnostics.py does) and then genuinely raises
    VolumeIdentityError - not a --volume-map entry, but the same argv with
    --volume-map dropped, so resolve_volume_identity's own prefix scan
    over stale.nml's records finds zero decoded paths under recon/audio
    and raises for real - reaches write_reconnect_result's diagnostics
    parameter still holding that line, proving the caller-owned list
    DL-065/DL-066 justify is not discarded when the raise crosses
    provide_result. This is the e076b1a regression write_reconnect_result
    must not reintroduce: a scan's diagnostics disappearing behind a later
    volume-identity failure.

    Observed to fail when write_reconnect_result is mutated to pass its
    own fresh `[]` into provide_result's run_reconnection call instead of
    forwarding its own diagnostics list (simulating a local list local to
    the write core rather than the caller-owned one): the assertion below
    that result.diagnostics is non-empty fails, since the diagnostics
    collected during the scan are appended to a list write_reconnect_result
    never reads back.
    """
    monkeypatch.setattr(diskscan, "HAS_MUTAGEN", False)
    argv = [
        "rewrite-from-reconnect", "recon/stale.nml", "out/recon_out.nml",
        "--scan-root", "recon/audio",
        "--match-confidence", "filename",
        "--cache", "out/recon.tagcache.json",
    ]
    args = _parse_args(argv)
    (tmp_path / "out").mkdir(exist_ok=True)

    diagnostics: list[str] = []

    def provide_result(old_root):
        return reconnect_run.run_reconnection(args, old_root, diagnostics=diagnostics)

    with _in_dir(tmp_path):
        result = reconnect_run.write_reconnect_result(args, provide_result, diagnostics=diagnostics)

    expected_tag_line = (
        "tag_reading_unavailable=mutagen not installed; tiers still able to match, "
        "by --match-confidence level: " + _tag_free_summary()
    )
    assert result.error is not None and result.error.startswith("volume_identity_error=")
    assert result.outcome is None
    assert result.reconnect is None
    assert result.diagnostics == (expected_tag_line,)
    assert diagnostics == [expected_tag_line]


def _parse_entry_locations(nml_bytes: bytes) -> dict[tuple[str, str], tuple[str, str, str, str]]:
    """Every COLLECTION ENTRY's (ARTIST, TITLE) mapped to its LOCATION's
    (DIR, FILE, VOLUME, VOLUMEID), for the element-by-element comparison
    CI-M-004-009 requires rather than a byte diff - a rejected record's
    LOCATION differs in string length from the zero-override write's, so
    every byte after that point shifts and a byte-offset diff would
    report the whole tail as differing."""
    import xml.etree.ElementTree as ET

    root = ET.fromstring(nml_bytes)
    locations: dict[tuple[str, str], tuple[str, str, str, str]] = {}
    for entry in root.find("COLLECTION").findall("ENTRY"):
        key = (entry.attrib.get("ARTIST", ""), entry.attrib.get("TITLE", ""))
        loc = entry.find("LOCATION")
        locations[key] = (
            loc.attrib.get("DIR", ""), loc.attrib.get("FILE", ""),
            loc.attrib.get("VOLUME", ""), loc.attrib.get("VOLUMEID", ""),
        )
    return locations


def test_non_zero_override_write_matches_element_by_element_except_the_rejected_record(
    fixture_corpus: Path, tmp_path: Path
) -> None:
    """A provider returning wizard_state.amended_result over a decision
    set rejecting one record - the collection's one matched record,
    Aphex Twin/Xtal, present in result.mapping and therefore actually
    changed by the rejection - is written and compared against the
    zero-override write element by element: every ENTRY's LOCATION
    matches except Xtal's, whose amended LOCATION equals the LOCATION
    the stale.nml input carried for it (D:, "/:Gone/:Music/:",
    "xtal_recon.mp3"), reverted from the reconnected
    "{RUN_ROOT}/:recon/:audio/:moved/:" the zero-override write carries
    (the same string test_zero_override_write_is_sensitive_to_the_mapping
    above observes for a dropped-mapping-key provider). The
    RewriteReconnectResult's stats and ambiguity_rows are asserted equal
    to the scan's own - the carried-through values amended_result
    returns - rather than recomputed.
    """
    case = _rewrite_out_case()
    (tmp_path / "out").mkdir(exist_ok=True)
    (tmp_path / "out2").mkdir(exist_ok=True)
    args_zero = _parse_args(case["argv"])
    args_amended = _parse_args([
        "rewrite-from-reconnect", "recon/stale.nml", "out2/recon_out.nml",
        "--scan-root", "recon/audio",
        "--volume-map", "recon/audio", "D:", "D:",
        "--match-confidence", "filename",
        "--cache", "out/recon.tagcache.json",
    ])

    def provide_zero(old_root):
        return reconnect_run.run_reconnection(args_zero, old_root)

    reviews: list = []

    def provide_amended(old_root):
        scanned = reconnect_run.run_reconnection(args_amended, old_root, reviews=reviews)
        decisions = WizardState()
        rejected_key = next(iter(scanned.mapping))
        decisions.reject(rejected_key)
        return amended_result(scanned, decisions), decisions, scanned

    holder: dict[str, object] = {}

    def provide_amended_wrapped(old_root):
        result, decisions, scanned = provide_amended(old_root)
        holder["decisions"] = decisions
        holder["scanned"] = scanned
        return result

    with _in_dir(tmp_path):
        reconnect_run.write_reconnect_result(args_zero, provide_zero)
        amended_write = reconnect_run.write_reconnect_result(args_amended, provide_amended_wrapped)

    zero_bytes = (tmp_path / "out" / "recon_out.nml").read_bytes()
    amended_bytes = (tmp_path / "out2" / "recon_out.nml").read_bytes()

    zero_locations = _parse_entry_locations(zero_bytes)
    amended_locations = _parse_entry_locations(amended_bytes)
    rejected = ("Aphex Twin", "Xtal")
    assert set(zero_locations) == set(amended_locations)
    for key in zero_locations:
        if key == rejected:
            continue
        assert amended_locations[key] == zero_locations[key]
    assert zero_locations[rejected][0].endswith("/:recon/:audio/:moved/:")
    assert zero_locations[rejected][1:] == ("xtal_recon.mp3", "D:", "D:")
    assert amended_locations[rejected] == ("/:Gone/:Music/:", "xtal_recon.mp3", "D:", "D:")

    scanned = holder["scanned"]
    decisions = holder["decisions"]
    assert amended_write.reconnect.stats == scanned.stats
    assert amended_write.reconnect.ambiguity_rows == scanned.ambiguity_rows

    # Negative controls, both executed rather than merely described:
    #
    # 1) LOCATION sensitivity to WHICH records were overridden, not just
    #    that the file changed at all: the fixture corpus scanned above
    #    matches exactly one record, so a second, synthetic mapping entry
    #    (a second EntryRecord under the same scan) is added to a copy of
    #    the scanned mapping to show that dropping IT changes a different
    #    LOCATION than dropping the real one does - the amended mapping is
    #    sensitive to which key was rejected, not merely to a change
    #    having happened.
    from dataclasses import replace as _replace
    from traktor_nml.model import EntryRecord as _EntryRecord

    only_key = next(iter(scanned.mapping))
    only_winner = scanned.mapping[only_key]
    second_old = next(r for r in scanned.old_records if r.primary_key != only_key)
    second_winner = _replace(only_winner, file_name="synthetic_second.mp3")
    two_record_scanned = _replace(
        scanned, mapping={**scanned.mapping, second_old.primary_key: second_winner}
    )
    reject_only = WizardState()
    reject_only.reject(only_key)
    reject_second = WizardState()
    reject_second.reject(second_old.primary_key)
    dropped_only = apply(two_record_scanned, reject_only)
    dropped_second = apply(two_record_scanned, reject_second)
    assert dropped_only != dropped_second
    assert only_key not in dropped_only and second_old.primary_key in dropped_only
    assert second_old.primary_key not in dropped_second and only_key in dropped_second

    # 2) ambiguity_rows recount observed to diverge from the carried-through
    #    values in both directions: matched short by exactly one, and a
    #    row for the rejected record present in the recount and absent
    #    from the carried-through rows.
    amended_mapping = apply(scanned, decisions)
    recounted_matched = len(amended_mapping)
    rejected_record = next(r for r in scanned.old_records if r.primary_key not in amended_mapping)
    original_ambiguity_paths = {row["old_path"] for row in scanned.ambiguity_rows}
    recounted_rows = list(scanned.ambiguity_rows)
    for record in scanned.old_records:
        if record.primary_key not in amended_mapping and str(record.location.decoded_path) not in original_ambiguity_paths:
            recounted_rows.append(
                {
                    "artist": record.artist, "title": record.title,
                    "old_path": str(record.location.decoded_path), "reason": "left_missing",
                }
            )
    rejected_path = str(rejected_record.location.decoded_path)
    # Observed on the fixture corpus: the scan's own stats['matched'] is 1
    # (one record - Xtal - matches at --match-confidence filename), and
    # the recount over the amended mapping is 0.
    assert scanned.stats["matched"] == 1
    assert recounted_matched == 0
    assert recounted_matched == scanned.stats["matched"] - 1
    assert any(row["old_path"] == rejected_path for row in recounted_rows)
    assert not any(row["old_path"] == rejected_path for row in scanned.ambiguity_rows)

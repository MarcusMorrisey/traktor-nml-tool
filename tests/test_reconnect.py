"""Disk-scan reconnection: one-to-one assignment and volume identity."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from traktor_nml.confidence import MatchConfidence
from traktor_nml.fingerprint import HAS_ACOUSTID
from tests.conftest import run_tool


# Traktor's FILESIZE is the audio payload in KILOBYTES, not the file's byte
# count, so a stub standing in for a FILESIZE="16" entry must be 16 KiB. The
# cascade refutes a candidate whose size contradicts the collection's, and a
# 16-byte stub beside FILESIZE="16" contradicts it by a factor of 1024.
_STUB_KB = 16


def _write_nml(path: Path, entries_xml: str, entries_count: int = 1) -> None:
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
        f'<COLLECTION ENTRIES="{entries_count}">{entries_xml}</COLLECTION>'
        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS>'
        "<SETS></SETS><INDEXING></INDEXING></NML>",
        encoding="utf-8",
        newline="",
    )


def _entry(artist, title, volume, dirv, filename, size=str(_STUB_KB), time="1.0"):
    """Minimal COLLECTION ENTRY carrying only the attributes the
    file/size/time match tiers need; PLAYLISTS/SETS/INDEXING are always
    present but empty so the tool's other schema assumptions still hold."""
    return (
        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
        f'<LOCATION DIR="{dirv}" FILE="{filename}" VOLUME="{volume}" VOLUMEID="{volume}"></LOCATION>'
        f'<INFO BITRATE="320" PLAYTIME_FLOAT="{time}" FILESIZE="{size}"></INFO>'
        "</ENTRY>"
    )


def test_scan_reconnect_reports_match_without_writing(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    (music / "xtal.mp3").write_bytes(b"\x00" * (_STUB_KB * 1024))

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))

    result = run_tool(
        [
            "scan-reconnect-candidates", str(old_nml),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
            # mutagen is not installed in this test environment, so tags are
            # always empty; filename confidence is required to match at all.
            "--match-confidence", "filename",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert "reconnectable=1" in result.stdout
    assert not (tmp_path / "out.nml").exists()


def test_no_output_assigns_two_entries_the_same_location(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    (music / "track.mp3").write_bytes(b"\x00" * (_STUB_KB * 1024))

    old_nml = tmp_path / "old.nml"
    _write_nml(
        old_nml,
        _entry("A", "One", "Z:", "/:gone1/:", "track.mp3") + _entry("A", "One", "Z:", "/:gone2/:", "track.mp3"),
        entries_count=2,
    )

    result = run_tool(
        [
            "rewrite-from-reconnect", str(old_nml), str(tmp_path / "out.nml"),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
            "--match-confidence", "filename",
            "--csv", str(tmp_path / "ambiguous.csv"),
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    # Both old entries claim the one candidate on disk, so both are withdrawn.
    assert "destination_collisions=2" in result.stdout
    out_path = tmp_path / "out.nml"
    if out_path.exists():
        assert 'VOLUME="C:"' not in out_path.read_text(encoding="utf-8")


def test_absent_volume_map_and_ambiguous_prefix_is_hard_error(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    (music / "xtal.mp3").write_bytes(b"\x00" * (_STUB_KB * 1024))

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))

    result = run_tool(
        ["scan-reconnect-candidates", str(old_nml), "--scan-root", str(music)],
        cwd=tmp_path,
    )
    assert result.exit_code == 2


def test_dry_run_and_write_agree_on_counts(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    (music / "xtal.mp3").write_bytes(b"\x00" * (_STUB_KB * 1024))

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))

    common = [
        "rewrite-from-reconnect", str(old_nml), str(tmp_path / "out.nml"),
        "--scan-root", str(music),
        "--volume-map", str(music), "C:", "C:",
    ]
    dry = run_tool(common + ["--dry-run"], cwd=tmp_path)
    real = run_tool(common, cwd=tmp_path)
    assert dry.stdout.split("output_written")[0] == real.stdout.split("output_written")[0]


def test_fingerprint_flag_names_the_dependency_that_is_actually_missing(
    tmp_path: Path, monkeypatch
) -> None:
    """The tier needs three separate things and each can be missing alone.

    A run whose fingerprinting works but whose comparison cannot load the
    chromaprint shared library used to print nothing at all: HAS_ACOUSTID
    was True, so the old diagnostic never fired, and the tier matched
    nothing while looking like a clean run. Whatever is missing, the run
    must say which - "pyacoustid/fpcalc not available" is actively wrong
    advice when both are installed and the library is the gap.
    """
    import traktor_nml.fingerprint as fingerprint_module

    monkeypatch.setattr(
        fingerprint_module,
        "fingerprint_unavailable_reason",
        lambda: "the chromaprint shared library is not available",
    )
    # Patched on both the defining module and reconnect_run's bound name:
    # reconnect_run imports fingerprint_unavailable_reason by value at
    # import time, so patching only traktor_nml.fingerprint would leave
    # the core still calling the pre-patch function object.
    monkeypatch.setattr(
        "traktor_nml.reconnect_run.fingerprint_unavailable_reason",
        lambda: "the chromaprint shared library is not available",
    )

    music = tmp_path / "music"
    _stub(music / "xtal.mp3")
    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))

    result = run_tool(
        [
            "scan-reconnect-candidates", str(old_nml),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
            "--match-confidence", "filename",
            "--fingerprint",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert "fingerprint_dependency_missing=the chromaprint shared library" in result.stderr


@pytest.mark.skipif(HAS_ACOUSTID, reason="exercises the missing-dependency path only")
def test_fingerprint_flag_without_dependency_warns_rather_than_silently_no_ops(tmp_path: Path) -> None:
    """--fingerprint with pyacoustid/fpcalc absent must not silently do
    nothing: the run still completes (the tier just never contributes a
    match), but a diagnostic naming the missing dependency is printed."""
    music = tmp_path / "music"
    music.mkdir()
    (music / "xtal.mp3").write_bytes(b"\x00" * (_STUB_KB * 1024))

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("Aphex Twin", "Xtal", "Z:", "/:gone/:", "xtal.mp3"))

    result = run_tool(
        [
            "scan-reconnect-candidates", str(old_nml),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
            "--match-confidence", "filename",
            "--fingerprint",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert "fingerprint_dependency_missing" in result.stderr


# --- path-suffix tiers and tolerant verification -------------------------


def _stub(path: Path, kb: int = _STUB_KB) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * (kb * 1024))


def _stat(stdout: str, key: str) -> str | None:
    """One stats value read as a whole line.

    Substring assertions cannot be used here: "matched=0" is a substring of
    "unmatched=0", so `assert "matched=0" in stdout` passes for a run that
    matched everything. That false pass hid a real gap in these tests until
    a mutation run exposed it.
    """
    for line in stdout.splitlines():
        name, _, value = line.partition("=")
        if name == key:
            return value
    return None


def test_wholesale_move_reconnects_at_default_confidence_without_tags(tmp_path: Path) -> None:
    """The dominant real-world failure - a library moved as a unit - must
    reconnect at strict confidence with no readable tags at all.

    Every absolute path changed, but each file's position within its own
    folders did not, which is exactly what the path-suffix tiers key on.
    Before those tiers this run matched nothing and the tool reported the
    whole collection as dangling.
    """
    music = tmp_path / "music"
    _stub(music / "Techno" / "Artist" / "Album" / "track.mp3")

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("A", "One", "Z:", "/:Techno/:Artist/:Album/:", "track.mp3"))

    result = run_tool(
        [
            "scan-reconnect-candidates", str(old_nml),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert _stat(result.stdout, "matched_path_suffix_3") == "1"
    assert _stat(result.stdout, "reconnectable") == "1"


def test_one_folder_suffix_is_not_admitted_at_strict(tmp_path: Path) -> None:
    """A single folder plus filename collides across sibling libraries
    ("Album/track01.mp3"), so it must wait for loose. A path too shallow
    for the deep tiers therefore matches nothing at strict."""
    music = tmp_path / "music"
    _stub(music / "Album" / "track.mp3")

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("A", "One", "Z:", "/:Album/:", "track.mp3"))

    common = [
        "scan-reconnect-candidates", str(old_nml),
        "--scan-root", str(music),
        "--volume-map", str(music), "C:", "C:",
    ]
    strict = run_tool(common, cwd=tmp_path)
    loose = run_tool(common + ["--match-confidence", "loose"], cwd=tmp_path)

    assert _stat(strict.stdout, "matched") == "0"
    assert _stat(strict.stdout, "matched_path_suffix_1") is None
    assert _stat(loose.stdout, "matched_path_suffix_1") == "1"


def test_size_gap_of_traktor_tag_overhead_still_matches(tmp_path: Path) -> None:
    """Traktor's FILESIZE counts the audio payload, so it sits below the
    file's real size by whatever tags and artwork occupy - measured at up
    to 0.41% over a real collection. A candidate that far off must still
    match: rejecting it would leave a present file reported as missing,
    which is the failure this tolerance exists to prevent.
    """
    music = tmp_path / "music"
    # 1000 KiB on disk against a collection claiming 996 KB of payload: a
    # 0.4% gap, inside the real-world maximum and inside the tolerance.
    _stub(music / "Techno" / "Artist" / "Album" / "track.mp3", kb=1000)

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("A", "One", "Z:", "/:Techno/:Artist/:Album/:", "track.mp3", size="996"))

    result = run_tool(
        [
            "scan-reconnect-candidates", str(old_nml),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert _stat(result.stdout, "matched_path_suffix_3") == "1"


def test_a_size_difference_alone_does_not_refute_across_sources(tmp_path: Path) -> None:
    """Size must never disqualify a cross-source candidate.

    A DJ legitimately holds one track at wildly different sizes over time -
    upgraded to STEMS, re-encoded to WAV for a performance, downgraded to
    reclaim drive space. Measured over 91 same-name/different-format pairs
    in a real collection, disk/collection size spanned 0.23x to 49.22x, so
    any band tight enough to catch a wrong file also rejects the cases a DJ
    creates on purpose. Duration is the format-invariant and does the
    refuting; size only ever corroborates.

    This test previously asserted the opposite - that an order-of-magnitude
    size gap refutes - and is inverted deliberately, not relaxed to go
    green.
    """
    music = tmp_path / "music"
    _stub(music / "Techno" / "Artist" / "Album" / "track.mp3", kb=1)

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("A", "One", "Z:", "/:Techno/:Artist/:Album/:", "track.mp3", size="5000"))

    result = run_tool(
        [
            "scan-reconnect-candidates", str(old_nml),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert _stat(result.stdout, "matched") == "1"
    assert _stat(result.stdout, "refuted") == "0"


def test_refuting_one_of_two_candidates_resolves_the_ambiguity(tmp_path: Path) -> None:
    """Two files share a filename; one contradicts the entry's size. The
    tier resolves cleanly to the plausible one instead of reporting an
    ambiguity the operator would have to adjudicate by hand."""
    music = tmp_path / "music"
    _stub(music / "a" / "track.mp3", kb=_STUB_KB)
    _stub(music / "b" / "track.mp3", kb=_STUB_KB * 100)

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("A", "One", "Z:", "/:gone/:", "track.mp3"))

    result = run_tool(
        [
            "scan-reconnect-candidates", str(old_nml),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
            "--match-confidence", "filename",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert _stat(result.stdout, "matched_filename") == "1"
    assert _stat(result.stdout, "ambiguous") == "0"


def test_absent_size_never_refutes(tmp_path: Path) -> None:
    """An entry Traktor recorded without a FILESIZE must be judged by the
    tier keys alone; silence is not a contradiction."""
    music = tmp_path / "music"
    _stub(music / "Techno" / "Artist" / "Album" / "track.mp3")

    old_nml = tmp_path / "old.nml"
    _write_nml(old_nml, _entry("A", "One", "Z:", "/:Techno/:Artist/:Album/:", "track.mp3", size=""))

    result = run_tool(
        [
            "scan-reconnect-candidates", str(old_nml),
            "--scan-root", str(music),
            "--volume-map", str(music), "C:", "C:",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0
    assert _stat(result.stdout, "matched_path_suffix_3") == "1"


# --- refutation unit tests ----------------------------------------------
#
# The duration branch cannot be reached through the CLI in this suite: the
# audio stubs carry no tags, so a scanned candidate never has a
# PLAYTIME_FLOAT to contradict the collection's. These exercise _refutes
# directly rather than leaving the branch to a mutation nobody notices.


def _record(
    *,
    filesize: str = "",
    playtime: str = "",
    from_disk: bool = False,
    dir_value: str = "/:Music/:",
    audio_id: str = "",
    artist: str = "A",
    title: str = "One",
    album: str = "",
) -> "EntryRecord":
    from traktor_nml.model import EntryRecord, LocationParts

    return EntryRecord(
        entry=None,
        artist=artist,
        title=title,
        audio_id=audio_id,
        filesize=filesize,
        playtime_float=playtime,
        bitrate="",
        album=album,
        file_name="track.mp3",
        location=LocationParts(volume="C:", volumeid="C:", dir_value=dir_value, file_name="track.mp3"),
        source_path=Path("C:/Music/track.mp3") if from_disk else None,
    )


@pytest.mark.parametrize(
    "old_seconds, new_seconds, refuted",
    [
        # Traktor's PLAYTIME_FLOAT and mutagen's duration disagree by up to
        # 0.172s over a real collection, and as strings they never match at
        # all - so a sub-second gap must not refute.
        ("212.345678", "212.5", False),
        ("212.345678", "212.9", False),
        # A different edit of the same track: minutes apart, refuted.
        ("212.345678", "254.0", True),
        # Silence on either side is not a contradiction.
        ("", "212.5", False),
        ("212.345678", "", False),
    ],
)
def test_duration_refutation_tolerates_the_measured_disagreement(
    old_seconds: str, new_seconds: str, refuted: bool
) -> None:
    from traktor_nml.matching import _refutes

    old = _record(playtime=old_seconds)
    candidate = _record(playtime=new_seconds, from_disk=True)
    assert _refutes(old, candidate) is refuted


def test_a_scanned_file_carries_kilobytes_not_bytes(tmp_path: Path) -> None:
    """The unit is settled where the record is built, not where it is read.

    This is the guard for the original bug - a collection's kilobytes
    compared against stat()'s bytes - and it deliberately goes through
    index_scan_roots against a real file rather than asserting on a
    hand-built record. Converting at comparison time instead would have to
    infer which side is which from another field, and would be wrong by a
    factor of 1024, silently, on any record that did not set it.
    """
    from traktor_nml.diskscan import index_scan_roots
    from traktor_nml.tagcache import TagCache

    audio = tmp_path / "audio"
    audio.mkdir()
    (audio / "track.mp3").write_bytes(b"\x00" * (5000 * 1024))

    records = index_scan_roots([audio], TagCache(tmp_path / "cache.json"))
    assert len(records) == 1
    assert records[0].filesize == "5000", "scanned size must be kilobytes"


def test_size_is_compared_in_one_unit_across_the_two_sources(tmp_path: Path) -> None:
    """The unit contract, now expressed through corroboration.

    Size no longer refutes across sources, so the guard for the original
    kilobytes-versus-bytes bug moved to _size_agrees: the collection entry
    and the real file behind it must be recognised as the same size, and a
    figure 1024x off must not be.
    """
    from traktor_nml.diskscan import index_scan_roots
    from traktor_nml.matching import _Claims, _size_agrees
    from traktor_nml.tagcache import TagCache

    audio = tmp_path / "audio"
    audio.mkdir()
    (audio / "track.mp3").write_bytes(bytes(5000 * 1024))
    scanned = index_scan_roots([audio], TagCache(tmp_path / "cache.json"))[0]

    assert _size_agrees(_Claims(_record(filesize="5000")), scanned) is True
    # The pre-fix bug read the same file as 5,120,000 KB.
    assert _size_agrees(_Claims(_record(filesize=str(5000 * 1024))), scanned) is False


def test_size_never_vetoes_an_audio_id_match() -> None:
    """AUDIO_ID is Traktor's own content-derived identity, so it outranks
    the approximate size check outright rather than merely surviving a
    generous bound.

    The case that needs this is re-encoding: the collection entry recorded a
    5,000 KB MP3 and the user has since replaced it with the same recording
    as a 40 MB lossless file. AUDIO_ID still agrees because the audio is the
    same; the size is eight times over, past any band wide enough to be
    useful. Letting the weakest signal veto the strongest would report the
    track missing when it is sitting right there.
    """
    from traktor_nml.matching import match_records

    old = _record(filesize="5000", audio_id="AUDIOID")
    candidate = _record(filesize=str(40000 * 1024), from_disk=True, audio_id="AUDIOID")
    _, stats, _ = match_records([old], [candidate], MatchConfidence.STRICT)
    assert stats["matched"] == 1
    assert stats["matched_audio_id"] == 1


def test_embedded_artwork_does_not_veto_a_path_suffix_match() -> None:
    """The same overhead on a tier that IS refutable: the band has to be
    wide enough to absorb artwork, or a moved library with cover art
    reconnects nothing."""
    from traktor_nml.matching import match_records

    old = _record(filesize="5000", dir_value="/:Techno/:Artist/:Album/:")
    # Untagged on disk, so no tag tier can fire above the path suffix.
    candidate = _record(
        filesize="5500",
        from_disk=True,
        dir_value="/:Techno/:Artist/:Album/:",
        artist="",
        title="",
    )
    _, stats, _ = match_records([old], [candidate], MatchConfidence.STRICT)
    assert stats["matched_path_suffix_3"] == 1
    assert stats["refuted"] == 0


def test_vbr_duration_estimate_does_not_veto_a_match() -> None:
    """mutagen extrapolates a headerless VBR file's duration from its first
    frame, so its error scales with track length. A fixed sub-second bound
    rejects the correct file; the allowance has to be relative."""
    from traktor_nml.matching import match_records

    old = _record(playtime="374.5")
    candidate = _record(playtime="352.1", from_disk=True)
    _, stats, _ = match_records([old], [candidate], MatchConfidence.LOOSE)
    assert stats["matched"] == 1


def test_a_thirty_second_preview_is_still_refuted() -> None:
    """The widened bands must still separate a preview clip from the track
    it previews - otherwise refutation has stopped doing anything."""
    from traktor_nml.matching import _refutes

    full = _record(filesize="6000", playtime="360.0")
    preview = _record(filesize=str(500 * 1024), playtime="30.0", from_disk=True)
    assert _refutes(full, preview) is True


def test_same_source_comparison_keeps_the_tight_bound() -> None:
    """Collection to collection, both sides are Traktor's own number for the
    same quantity, so the wide cross-source band must not apply."""
    from traktor_nml.matching import _refutes

    assert _refutes(_record(filesize="5000"), _record(filesize="5400")) is True


def test_a_refuted_current_copy_does_not_promote_the_stale_one(tmp_path: Path) -> None:
    """Refutation must not hand the match to Sync_old.

    The active Sync_ copy is the one a migration rewrites, so it is the copy
    most likely to have drifted in size. If refuting it left Sync_old alone
    in the candidate list, the run would rewrite onto the stale copy and
    report a clean match.
    """
    from traktor_nml.matching import match_records

    old = _record(filesize="5000", dir_value="/:Gone/:")
    current = _record(filesize="5400", dir_value="/:Sync_/:Music/:")
    stale = _record(filesize="5000", dir_value="/:Sync_old/:Music/:")

    mapping, stats, _ = match_records([old], [current, stale], MatchConfidence.FILENAME)
    assert mapping.get(old.primary_key) is None
    assert stats["unmatched"] == 1
    # and the operator can tell this from a file that is simply gone
    assert stats["refuted"] == 1


def test_path_suffix_2_waits_for_loose() -> None:
    """Only depth three was measured (97.2% unique). Depth two drops the
    album level, so it stays out of the default confidence until it has
    evidence of its own."""
    assert MatchConfidence.STRICT.admits("path_suffix_3") is True
    assert MatchConfidence.STRICT.admits("path_suffix_2") is False
    assert MatchConfidence.LOOSE.admits("path_suffix_2") is True


# --- the cascade table is the single declaration ------------------------


def test_cascade_table_matches_what_record_keys_actually_emits() -> None:
    """_CASCADE declares the tier order; record_keys is what runs.

    Two listings of one sequence drift silently, so this asserts they agree
    rather than trusting them to be kept in step by hand. A record with every
    field populated and a deep enough path emits every built-in tier, in
    cascade order, at the widest confidence.
    """
    from traktor_nml.matching import _CASCADE, record_keys

    record = _record(
        filesize="5000",
        playtime="212.5",
        audio_id="AID",
        dir_value="/:Techno/:Artist/:Album/:",
        album="Alb",
    )
    emitted = [name for name, _ in record_keys(record, MatchConfidence.FILENAME)]
    assert emitted == [tier.name for tier in _CASCADE]


def test_cascade_table_and_confidence_ladder_name_the_same_tiers() -> None:
    """Every tier the ladder admits must exist in the table, and every tier
    in the table must be admitted by some level - otherwise one of them is
    naming a tier that no longer exists."""
    from traktor_nml.matching import _CASCADE

    table = {tier.name for tier in _CASCADE}
    ladder = set(MatchConfidence.FILENAME.admitted_tiers())
    assert ladder == table


def test_the_only_non_refutable_tier_is_audio_id() -> None:
    """Exempting a similarity tier from refutation would let a wrong
    candidate through; this pins the exemption to the identity tier."""
    from traktor_nml.matching import _CASCADE

    assert {t.name for t in _CASCADE if not t.refutable} == {"audio_id"}


# --- --no-refute ---------------------------------------------------------


def _sized_nml(path: Path, dirv: str, filename: str, size: str) -> None:
    _write_nml(path, _entry("A", "One", "C:", dirv, filename, size=size, time="200.0"))


def test_no_refute_admits_a_candidate_the_size_check_withdraws(tmp_path: Path) -> None:
    """The switch exists because the tolerances are calibrated against one
    library, so a library that breaks an assumption behind them loses
    correct candidates with no way to overrule it.

    Two collections describing the same file at the same path, disagreeing
    on FILESIZE far beyond tolerance: refuted by default, matched with the
    switch.
    """
    _sized_nml(tmp_path / "old.nml", "/:M/:A/:Alb/:", "t.mp3", "5000")
    _sized_nml(tmp_path / "new.nml", "/:M/:A/:Alb/:", "t.mp3", "9000")

    default = run_tool(["preview-compare", "old.nml", "new.nml"], cwd=tmp_path)
    assert _stat(default.stdout, "matched") == "0"
    assert _stat(default.stdout, "refuted") == "1"

    overridden = run_tool(["preview-compare", "old.nml", "new.nml", "--no-refute"], cwd=tmp_path)
    assert _stat(overridden.stdout, "matched") == "1"
    assert _stat(overridden.stdout, "refuted") == "0"


def test_no_refute_announces_itself_on_every_run(tmp_path: Path) -> None:
    """Ignoring the collection's own numbers can commit a rewrite onto the
    wrong file, so the run says so rather than leaving it in --help."""
    _sized_nml(tmp_path / "old.nml", "/:M/:A/:Alb/:", "t.mp3", "5000")
    _sized_nml(tmp_path / "new.nml", "/:M/:A/:Alb/:", "t.mp3", "9000")

    quiet = run_tool(["preview-compare", "old.nml", "new.nml"], cwd=tmp_path)
    assert "refutation_disabled" not in quiet.stderr

    loud = run_tool(["preview-compare", "old.nml", "new.nml", "--no-refute"], cwd=tmp_path)
    assert "refutation_disabled=" in loud.stderr


@pytest.mark.parametrize(
    "argv",
    [
        ["preview-compare", "old.nml", "new.nml"],
        ["scan-compare-candidates", "old.nml", "."],
        ["rewrite-from-collection-compare", "old.nml", "new.nml", "out.nml", "--dry-run"],
        ["scan-reconnect-candidates", "old.nml", "--scan-root", "music",
         "--volume-map", "music", "C:", "C:"],
        ["rewrite-from-reconnect", "old.nml", "out.nml", "--scan-root", "music",
         "--volume-map", "music", "C:", "C:", "--dry-run"],
    ],
    ids=["preview-compare", "scan-compare", "rewrite-compare", "scan-reconnect", "rewrite-reconnect"],
)
def test_every_matching_command_accepts_no_refute(tmp_path: Path, argv: list[str]) -> None:
    """The flag is only useful where the cascade runs, and it has to be on
    ALL of those - a run that rejects the flag sends the operator looking
    for a different command."""
    _sized_nml(tmp_path / "old.nml", "/:M/:A/:Alb/:", "t.mp3", "5000")
    _sized_nml(tmp_path / "new.nml", "/:M/:A/:Alb/:", "t.mp3", "9000")
    _stub(tmp_path / "music" / "t.mp3")

    result = run_tool(argv + ["--no-refute"], cwd=tmp_path)
    # exit 2 would mean argparse rejected the flag outright.
    assert result.exit_code == 0, result.stderr
    assert "refutation_disabled=" in result.stderr


def test_capitalisation_alone_does_not_lose_a_match() -> None:
    """A name differing only in case denotes the same file on Windows and
    macOS, so the cascade must not manufacture a difference the filesystem
    does not have.

    The pairs below are real: measured against a 6,412-entry collection and
    its 46,295 files, these were among eight otherwise-perfect matches lost
    to capitalisation alone before the keys were folded.
    """
    from traktor_nml.matching import match_records

    real_pairs = (
        ("4B_136_We Like to Party! (The Vengabus)_Vengaboys.mp3",
         "4B_136_We like to Party! (The Vengabus)_Vengaboys.mp3"),
        ("9A_125_Into The Future (Feat. Hang Massive)_Future Frequency.mp3",
         "9A_125_Into The Future (feat. Hang Massive)_Future Frequency.mp3"),
        ("4A_134_Madness in the Method_Medjula.mp3",
         "4A_134_Madness in the Method_MeDJula.mp3"),
    )
    for collection_name, disk_name in real_pairs:
        old = _record(dir_value="/:Techno/:Sets/:2025/:")
        old = replace(old, file_name=collection_name,
                      location=replace(old.location, file_name=collection_name))
        disk = _record(dir_value="/:Techno/:Sets/:2025/:", from_disk=True)
        disk = replace(disk, file_name=disk_name,
                       location=replace(disk.location, file_name=disk_name))

        _, stats, _ = match_records([old], [disk], MatchConfidence.STRICT)
        assert stats["matched"] == 1, f"case difference lost the match: {collection_name!r}"


def test_audio_id_is_not_case_folded() -> None:
    """AUDIO_ID is base64, where case is significant: folding it would merge
    genuinely distinct identities into one bucket."""
    from traktor_nml.matching import record_keys

    upper = _record(audio_id="AbCdEf")
    lower = _record(audio_id="abcdef")
    keys_upper = dict(record_keys(upper, MatchConfidence.STRICT))
    keys_lower = dict(record_keys(lower, MatchConfidence.STRICT))
    assert keys_upper["audio_id"] != keys_lower["audio_id"]

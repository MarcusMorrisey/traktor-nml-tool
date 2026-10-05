"""The M-001 spike's AUDIO_ID false-collision count.

The spike is outside the package on purpose (its own module docstring says
so), so it is loaded here by path rather than imported, the way a caller
running `python -m spike.dedupe.measure` reaches it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from traktor_nml.model import EntryRecord, LocationParts

_SPIKE = Path(__file__).resolve().parent.parent / "spike" / "dedupe" / "measure.py"
_spec = importlib.util.spec_from_file_location("dedupe_spike_measure", _SPIKE)
measure = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = measure
_spec.loader.exec_module(measure)


def _record(
    *,
    audio_id: str,
    artist: str = "A",
    title: str = "T",
    filesize: str = "8000",
    playtime: str = "200.000000",
    bitrate: str = "320000",
    file_name: str = "track.mp3",
) -> EntryRecord:
    return EntryRecord(
        entry=None,
        artist=artist,
        title=title,
        audio_id=audio_id,
        filesize=filesize,
        playtime_float=playtime,
        bitrate=bitrate,
        album="",
        file_name=file_name,
        location=LocationParts("C:", "C:", "/:Music/:", file_name),
    )


def test_one_file_titled_twice_is_not_a_collision():
    """A library catalogues one file under two spellings routinely, and the
    tag test alone reads that as a fingerprint failure. Two entries sharing
    an AUDIO_ID and agreeing on FILESIZE, PLAYTIME_FLOAT and BITRATE are one
    file however their titles are typed.

    This is what the count is for: `Rates.tier3_admitted` requires
    false_collisions == 0, so a pair counted here disables tier 3 on
    AUDIO_ID. Measured on three real collections the tag test counts 32
    where the duration test counts 0.

    Mutation: `agrees` was returned to `same_tags and same_length`, dropping
    the `_one_file_twice` term. Observed:
        E       AssertionError: one file titled twice counts as a collision
        E       assert 1 == 0
        E        +  where 1 = <function false_collisions at 0x0000025DF1BC57A0>([EntryRecord(entry=None, artist='A', title='Funkytown (instrumental)', audio_id='AQ==', filesize='8000', playtime_floa...', location=LocationParts(volume='C:', volumeid='C:', dir_value='/:Music/:', file_name='track.mp3'), source_path=None)])
        E        +    where <function false_collisions at 0x0000025DF1BC57A0> = measure.false_collisions
    """
    pair = [
        _record(audio_id="AQ==", title="Funkytown (instrumental)"),
        _record(audio_id="AQ==", title="Funkytown"),
    ]
    assert measure.false_collisions(pair) == 0, (
        "one file titled twice counts as a collision"
    )


def test_two_recordings_sharing_an_audio_id_still_count():
    """The count must still carry a real collision. Two sub-second sample
    loops sharing an AUDIO_ID and a duration are different recordings, and
    their BITRATE differs, so they are not one file catalogued twice.

    Taken from the real library: `Kenkeni 016.flac` and `Kenkeni 017.flac`
    share an AUDIO_ID, FILESIZE 456 and PLAYTIME_FLOAT 0.806984, differing
    only at BITRATE 613000 against 614000.

    Mutation: `_one_file_twice` was weakened to compare FILESIZE and
    PLAYTIME_FLOAT alone, dropping BITRATE. Observed:
        E       AssertionError: a real collision stopped being counted
        E       assert 0 == 1
        E        +  where 0 = <function false_collisions at 0x000002F9DA3457A0>([EntryRecord(entry=None, artist='A', title='Kenkeni 016', audio_id='AA==', filesize='456', playtime_float='0.806984', ...tion=LocationParts(volume='C:', volumeid='C:', dir_value='/:Music/:', file_name='Kenkeni 017.flac'), source_path=None)])
        E        +    where <function false_collisions at 0x000002F9DA3457A0> = measure.false_collisions
    """
    loops = [
        _record(audio_id="AA==", title="Kenkeni 016", filesize="456",
                playtime="0.806984", bitrate="613000", file_name="Kenkeni 016.flac"),
        _record(audio_id="AA==", title="Kenkeni 017", filesize="456",
                playtime="0.806984", bitrate="614000", file_name="Kenkeni 017.flac"),
    ]
    assert measure.false_collisions(loops) == 1, (
        "a real collision stopped being counted"
    )


def test_a_missing_measurement_is_not_agreement():
    """An empty FILESIZE on one side is one measurement and one absence, not
    two readings that agree, so it cannot excuse a tag disagreement.

    Mutation: `_one_file_twice` dropped its `all(measured)` guard. Observed:
        E       AssertionError: an absent measurement read as agreement
        E       assert 0 == 1
        E        +  where 0 = <function false_collisions at 0x00000199F64057A0>([EntryRecord(entry=None, artist='A', title='One', audio_id='Ag==', filesize='', playtime_float='200.000000', bitrate='...', location=LocationParts(volume='C:', volumeid='C:', dir_value='/:Music/:', file_name='track.mp3'), source_path=None)])
        E        +    where <function false_collisions at 0x00000199F64057A0> = measure.false_collisions
    """
    pair = [
        _record(audio_id="Ag==", title="One", filesize=""),
        _record(audio_id="Ag==", title="Two", filesize=""),
    ]
    assert measure.false_collisions(pair) == 1, (
        "an absent measurement read as agreement"
    )

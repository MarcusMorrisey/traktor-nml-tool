"""Guards traktor_nml/metadata_tier.py: which tracked attributes carry an
operator judgement, which the run answers itself, and the outlier
projection over the measured ones.

The module imports nothing from the package, so every rule below runs
under the system interpreter with no nicegui (DL-069).

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation.

The band's own guards stand in pairs: a value inside it and a value past
it, because a band asserted only from above passes for a band of zero and
only from below for a band of one, which is a guard green in exactly the
broken state (DL-189). The two values each pair uses are read off the
user's own collection pair - the 1 KB drift the pair is full of, and the
one file described twice - so a guard failing names a real reading rather
than an invented one (DL-330).

This file is LF, like the rest of tests/.
"""

from __future__ import annotations

import pytest

from traktor_nml import metadata_tier


def test_the_partition_covers_every_tracked_attribute_once():
    """EDITORIAL_ATTRS and MEASURED_ATTRS divide TRACKED_ATTRS: no name in
    both, no name in neither, and the order of each is TRACKED_ATTRS'
    order, because the conflict CSV, the resolve rail and the outlier
    listing all read that order.

    Fail-first mutation: MEASURED_ATTRS = ("filesize", "playtime_float")
    - bitrate dropped from the measured tier.
    Observed:
        AssertionError: assert ('artist', 't...aytime_float') == ('artist', 't...t', 'bitrate')

          Right contains one more item: 'bitrate'
          Use -v to get more diff
    """
    editorial = metadata_tier.EDITORIAL_ATTRS
    measured = metadata_tier.MEASURED_ATTRS
    assert set(editorial) & set(measured) == set()
    assert tuple(
        attr for attr in metadata_tier.TRACKED_ATTRS if attr in editorial
    ) + tuple(
        attr for attr in metadata_tier.TRACKED_ATTRS if attr in measured
    ) == editorial + measured
    assert editorial + measured == metadata_tier.TRACKED_ATTRS


def test_the_measured_tier_is_the_three_names_the_subject_states():
    """filesize, playtime_float and bitrate are what Traktor measured off
    the one file; artist, title and album are what a person answers for.
    Named rather than derived, so a name moving between tiers fails here
    and is read as the decision it is (DL-325).

    Fail-first mutation: "album" moved into MEASURED_ATTRS and out of
    EDITORIAL_ATTRS.
    Observed:
        AssertionError: assert ('filesize', ...ate', 'album') == ('filesize', ...t', 'bitrate')

          Left contains one more item: 'album'
          Use -v to get more diff
    """
    assert metadata_tier.MEASURED_ATTRS == ("filesize", "playtime_float", "bitrate")
    assert metadata_tier.EDITORIAL_ATTRS == ("artist", "title", "album")


def test_split_by_tier_keeps_a_mixed_divergence_whole():
    """A group diverging on an editorial and a measured name answers both
    lists, so the caller can report the conflict over every divergent
    attribute and still know which of them the rule could have settled
    (DL-329).

    Fail-first mutation: split_by_tier's editorial half returned () and
    the measured half the measured names, dropping the editorial side.
    Observed:
        AssertionError: assert () == ('artist',)

          Right contains one more item: 'artist'
          Use -v to get more diff
    """
    editorial, measured = metadata_tier.split_by_tier(["artist", "bitrate"])
    assert editorial == ("artist",)
    assert measured == ("bitrate",)


@pytest.mark.parametrize(
    "values, expected",
    [
        # The user's collection pair's ordinary drift: 1 KB on an 8 MB
        # file. 8123 vs 8124 is 0.0123% and stands inside the band.
        (("8123", "8124"), ()),
        # The .stem.m4a described twice, 17564 vs 69203: 74.6%.
        (("17564", "69203"), ("filesize",)),
    ],
)
def test_the_band_is_a_relative_gap_of_one_percent(values, expected):
    """outlier_attrs answers a reading per measured attribute whose spread
    exceeds OUTLIER_BAND of the larger value, and nothing for the drift
    the pair is full of.

    Fail-first mutation: OUTLIER_BAND = 0.0 - every divergence outlying.
    Observed:
        AssertionError: assert ('filesize',) == ()

          Left contains one more item: 'filesize'
          Use -v to get more diff
    """
    readings = metadata_tier.outlier_attrs({"filesize": values})
    assert tuple(reading.attr for reading in readings) == expected


def test_a_gap_exactly_at_the_band_is_not_an_outlier():
    """Exceeds, not reaches: 99 against 100 is exactly 1% of the larger
    value and is inside the band, so the boundary is stated by a guard
    rather than left to the comparison operator (DL-189).

    Fail-first mutation: the comparison relaxed from > to >=.
    Observed:
        AssertionError: assert (OutlierReadi...ve_gap=0.01),) == ()

          Left contains one more item: OutlierReading(attr='filesize', low='99', high='100', relative_gap=0.01)
          Use -v to get more diff
    """
    assert metadata_tier.outlier_attrs({"filesize": ("99", "100")}) == ()


def test_a_value_that_is_not_a_number_contributes_no_reading():
    """An empty or non-numeric FILESIZE is a fact the collection holds,
    not an error this projection raises: the attribute answers no reading
    and the rest of the group's attributes still do.

    Fail-first mutation: the float() call left unguarded.
    Observed:
        ValueError: could not convert string to float: ''
    """
    readings = metadata_tier.outlier_attrs(
        {"filesize": ("", "69203"), "bitrate": ("320000", "1411000")}
    )
    assert tuple(reading.attr for reading in readings) == ("bitrate",)


def test_a_non_positive_larger_value_yields_no_reading():
    """The band is a fraction of the larger of the two values, and a
    fraction of zero names no spread, so a group whose larger value is
    zero answers no reading rather than dividing by it.

    Fail-first mutation: the `if high[0] <= 0: continue` guard removed.
    Observed:
        ZeroDivisionError: division by zero
    """
    assert metadata_tier.outlier_attrs({"filesize": ("0", "0")}) == ()
    assert metadata_tier.outlier_attrs({"filesize": ("-4", "0")}) == ()


def test_a_reading_names_its_two_ends_low_first():
    """low and high are the values themselves as the file holds them, in
    magnitude order rather than member order, so a listing reads the same
    way whichever collection was given first.

    Fail-first mutation: low and high assigned in member order.
    Observed:
        ValueError: not enough values to unpack (expected 1, got 0)
    """
    (reading,) = metadata_tier.outlier_attrs({"filesize": ("69203", "17564")})
    assert (reading.low, reading.high) == ("17564", "69203")
    assert reading.relative_gap == pytest.approx(0.7462, abs=5e-5)


def test_the_readings_come_back_in_measured_attrs_order():
    """One group's listing reads the same way whichever attribute splice
    found divergent first, so the CLI report and the screen read one
    ordering from one module (DL-326).

    Fail-first mutation: the loop read `for attr in values_by_attr` in
    place of `for attr in MEASURED_ATTRS`.
    Observed:
        AssertionError: assert ('bitrate', '...aytime_float') == ('filesize', ...t', 'bitrate')

          At index 0 diff: 'bitrate' != 'filesize'
          Use -v to get more diff
    """
    readings = metadata_tier.outlier_attrs(
        {
            "bitrate": ("320000", "1411000"),
            "filesize": ("17564", "69203"),
            "playtime_float": ("100.0", "3616.0"),
        }
    )
    assert tuple(r.attr for r in readings) == ("filesize", "playtime_float", "bitrate")

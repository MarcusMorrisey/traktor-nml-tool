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
    readings = metadata_tier.outlier_attrs(
        {"filesize": values}, {"filesize": values[0]}
    )
    assert tuple(reading.attr for reading in readings) == expected


def test_a_gap_exactly_at_the_band_is_not_an_outlier():
    """Exceeds, not reaches: 99 against 100 is exactly 1% of the larger
    value and is inside the band, so the boundary is stated by a guard
    rather than left to the comparison operator (DL-189).

    Fail-first mutation: the comparison relaxed from > to >=.
    Observed:
        Fail-first mutation: the comparison relaxed from > to >=.
    Observed:
        AssertionError: assert (OutlierReadi...ve_gap=0.01),) == ()

          Left contains one more item: OutlierReading(attr='filesize', kept='100', other='99', relative_gap=0.01)
          Use -v to get more diff
    """
    assert metadata_tier.outlier_attrs({"filesize": ("99", "100")}, {"filesize": "100"}) == ()


def test_a_value_that_is_not_a_number_contributes_no_reading():
    """An empty or non-numeric FILESIZE is a fact the collection holds,
    not an error this projection raises: the attribute answers no reading
    and the rest of the group's attributes still do.

    Fail-first mutation: the float() call in measured_number left
    unguarded.
    Observed:
        ValueError: could not convert string to float: ''
    """
    readings = metadata_tier.outlier_attrs(
        {"filesize": ("", "69203"), "bitrate": ("320000", "1411000")},
        {"filesize": "69203", "bitrate": "320000"},
    )
    assert tuple(reading.attr for reading in readings) == ("bitrate",)


def test_a_non_positive_larger_value_yields_no_reading():
    """The band is a fraction of the larger of the two values, and a
    fraction of zero names no spread, so a group whose larger value is
    zero answers no reading rather than dividing by it.

    Fail-first mutation: the `if larger <= 0: continue` guard removed.
    Observed:
        Fail-first mutation: the `if larger <= 0: continue` guard removed.
    Observed:
        ZeroDivisionError: Fraction(1, 0)
    """
    assert metadata_tier.outlier_attrs({"filesize": ("0", "0")}, {"filesize": "0"}) == ()
    assert metadata_tier.outlier_attrs({"filesize": ("-4", "0")}, {"filesize": "0"}) == ()


def test_a_reading_names_its_two_ends_low_first():
    """low and high are the values themselves as the file holds them, in
    magnitude order rather than member order, so a listing reads the same
    way whichever collection was given first.

    Fail-first mutation: `max` in OutlierReading.high replaced by `min`.
    Observed:
        Fail-first mutation: `max` in OutlierReading.high replaced by `min`.
    Observed:
        AssertionError: assert ('17564', '17564') == ('17564', '69203')

          At index 1 diff: '17564' != '69203'
          Use -v to get more diff
    """
    (reading,) = metadata_tier.outlier_attrs(
        {"filesize": ("69203", "17564")}, {"filesize": "69203"}
    )
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
        },
        {"bitrate": "320000", "filesize": "17564", "playtime_float": "100.0"},
    )
    assert tuple(r.attr for r in readings) == ("filesize", "playtime_float", "bitrate")


def test_split_by_tier_reads_an_unclassified_tracked_name_as_editorial():
    """Fail-first mutation: split_by_tier's editorial half read
    `tuple(a for a in EDITORIAL_ATTRS if a in given)` with the unknown
    half dropped - the classified-only reading.
    Observed:
        AssertionError: assert ('artist',) == ('artist', 'unclassified')

          Right contains one more item: 'unclassified'
          Use -v to get more diff

    A tracked name in neither tier tuple is something no rule can answer,
    so it answers the editorial half and the group carrying it is put to
    the operator. Fail closed: the alternative drops it from both halves,
    which leaves editorial_attrs empty and settles the group in silence.
    """
    editorial, measured = metadata_tier.split_by_tier(["artist", "unclassified", "bitrate"])
    assert editorial == ("artist", "unclassified")
    assert measured == ("bitrate",)


def test_split_by_tier_refuses_a_string():
    """Fail-first mutation: the isinstance(attrs, str) raise removed, so the
    string was iterated as its characters.
    Observed:
        Failed: DID NOT RAISE <class 'TypeError'>

    What it answers instead is ((), ()) - no editorial half, so a caller
    deciding on that emptiness settles the group.

    ConflictRow.attrs is the comma-joined string of exactly these names,
    so a caller reaching for it rather than the list is a live mistake. A
    str iterates as its characters, none of which is a tracked name, so
    it would answer ((), ()) - no editorial half at all, which inverts
    the decision the caller makes on it. It raises instead.
    """
    with pytest.raises(TypeError):
        metadata_tier.split_by_tier("artist,bitrate")


def test_an_unreadable_measured_value_is_not_a_disagreement_the_rule_answers():
    """Mutation: the `and not
    metadata_tier.unreadable_measured(dict(measured_values))` clause
    dropped from settled_by_rule in _resolve_conflicts.
    Observed:
        assert '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD... TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS><SETS></SETS><INDEXING></INDEXING></NML>' is None
         +  where '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD... TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0"></SUBNODES></NODE></PLAYLISTS><SETS></SETS><INDEXING></INDEXING></NML>' = SpliceResult(output='<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n<NML VERSION="20"><HEAD PROGRAM="Traktor..., ('', '245.1')), ('bitrate', ('', '320000'))), winner=(0, 'C:/:Music/:Sets/:Deep/:one.mp3'), outliers=())], errors=[]).output

    The row the mutation reports carries values_by_attr of ('', '245.1')
    and ('', '320000') and outliers=(): the group settled, the output kept
    the record with no INFO element, and nothing named the numbers that
    were dropped.

    A record with no INFO element carries the empty string for every
    measured name. That is not two measurements disagreeing - there is
    one measurement and one absence - so the attribute is named
    unreadable and the caller puts the group to the operator rather than
    settling it and discarding the only numbers any input holds.
    """
    assert metadata_tier.unreadable_measured({"filesize": ("", "69203")}) == ("filesize",)
    assert metadata_tier.unreadable_measured({"bitrate": ("320000", "nan")}) == ("bitrate",)
    assert metadata_tier.unreadable_measured({"filesize": ("17564", "69203")}) == ()
    assert metadata_tier.unreadable_measured(
        {"filesize": ("", "69203"), "bitrate": ("320000", "1411000")}
    ) == ("filesize",)


def test_a_reading_names_the_value_the_output_keeps():
    """Fail-first mutation: the OutlierReading built as
    `OutlierReading(attr, other_raw, str(kept_raw), float(gap))` - the
    two values the other way round.
    Observed:
        AssertionError: assert ('69203', '8192') == ('8192', '69203')

          At index 0 diff: '69203' != '8192'
          Use -v to get more diff

    kept is the winning record's own value and other is the member value
    it is read furthest against, so a three-member group cannot name two
    numbers the output holds neither of. 8192 is what the output keeps
    here; 69203 is the far end and 8193 the near one.
    """
    (reading,) = metadata_tier.outlier_attrs(
        {"filesize": ("8192", "8193", "69203")}, {"filesize": "8192"}
    )
    assert (reading.kept, reading.other) == ("8192", "69203")
    assert reading.relative_gap == pytest.approx(0.8816, abs=5e-5)


def test_a_reading_is_taken_against_the_kept_value_not_the_widest_pair():
    """Fail-first mutation: `if widest is None or gap > widest[0]` relaxed to
    `gap < widest[0]`, so the nearest member value was read against
    rather than the furthest.
    Observed:
        ValueError: not enough values to unpack (expected 1, got 0)

    69100 against 69203 is 0.15% and inside the band, so reading the
    nearest value answers no reading at all for a group whose kept value
    is 692 times the smallest number in it.

    The widest pair in this group is 100 against 69203, but the output
    keeps 69203, so the reading the row carries is 69203 against 100 -
    the gap the operator is being told about is the one between what the
    file will hold and what it will not.
    """
    (reading,) = metadata_tier.outlier_attrs(
        {"filesize": ("100", "69203", "69100")}, {"filesize": "69203"}
    )
    assert (reading.kept, reading.other) == ("69203", "100")
    assert (reading.low, reading.high) == ("100", "69203")


def test_a_non_finite_value_is_screened_where_it_is_parsed():
    """Fail-first mutation: `return number if math.isfinite(number) else
    None` in measured_number replaced by `return number`.
    Observed:
        ValueError: Invalid literal for Fraction: 'inf'

        During handling of the above exception, another exception occurred:
        OverflowError: cannot convert Infinity to integer ratio

    float() accepts 'nan', 'inf', '-inf' and '1e400'. None of them is a
    measurement Traktor wrote, an infinite gap passes any band, and a
    NaN poisons the comparison it takes part in, so they answer no
    reading at all.
    """
    assert metadata_tier.outlier_attrs({"filesize": ("17564", "inf")}, {"filesize": "17564"}) == ()
    assert metadata_tier.outlier_attrs({"filesize": ("17564", "1e400")}, {"filesize": "17564"}) == ()
    assert metadata_tier.outlier_attrs({"filesize": ("17564", "-inf")}, {"filesize": "17564"}) == ()
    assert metadata_tier.outlier_attrs({"filesize": ("inf", "17564")}, {"filesize": "inf"}) == ()


def test_a_nan_reads_the_same_way_whichever_place_it_stands_in():
    """Fail-first mutation: `return number if math.isfinite(number) else
    None` in measured_number replaced by `return number`.
    Observed:
        ValueError: Invalid literal for Fraction: 'nan'

        During handling of the above exception, another exception occurred:
        ValueError: cannot convert NaN to integer ratio

    min() and max() over a list holding NaN answer whatever the list
    order makes them answer, so a NaN left in the comparison makes the
    reading depend on which collection was given first: ('nan', '17564',
    '69203') reported nothing while ('17564', 'nan', '69203') reported a
    74.6% reading. Screened, both name the one reading over the two real
    numbers.
    """
    first = metadata_tier.outlier_attrs(
        {"filesize": ("nan", "17564", "69203")}, {"filesize": "17564"}
    )
    second = metadata_tier.outlier_attrs(
        {"filesize": ("17564", "nan", "69203")}, {"filesize": "17564"}
    )
    assert first == second
    assert tuple((r.kept, r.other) for r in first) == (("17564", "69203"),)


def test_a_gap_exactly_at_the_band_is_not_an_outlier_on_a_decimal_attribute():
    """Fail-first mutation: `gap = abs(kept_exact - other_exact) / larger`
    replaced by `gap = Fraction(abs(kept_number - number) /
    max(kept_number, number))`, which is the same division taken in
    floats and then made exact.
    Observed:
        AssertionError: assert (OutlierReadi...00000000024),) == ()

          Left contains one more item: OutlierReading(attr='playtime_float', kept='60.0', other='59.4', relative_gap=0.010000000000000024)
          Use -v to get more diff

    59.4 against 60.0 is exactly 1% of the larger value. In binary
    floating point the division answers 0.010000000000000024, which is
    above the band, so the boundary is decided on the decimal strings
    themselves and an exact 1% gap is inside the band whatever the
    attribute's spelling.
    """
    assert metadata_tier.outlier_attrs(
        {"playtime_float": ("59.4", "60.0")}, {"playtime_float": "60.0"}
    ) == ()
    assert metadata_tier.outlier_attrs(
        {"playtime_float": ("59.39", "60.0")}, {"playtime_float": "60.0"}
    ) != ()


def test_every_exact_one_percent_pair_is_inside_the_band():
    """Fail-first mutation: `gap = abs(kept_exact - other_exact) / larger`
    replaced by `gap = Fraction(abs(kept_number - number) /
    max(kept_number, number))`.
    Observed:
        AssertionError: assert [('0.0990', '..., '0.6'), ...] == []

          Left contains 1018 more items, first extra item: ('0.0990', '0.1')
          Use -v to get more diff

    1,019 of the 1,019 exact-1% pairs the sweep produces land outside the
    band under float division, so the fault is the ordinary case rather
    than a corner of it.

    A sweep rather than one pair: an exact-1% gap between two decimal
    strings divides either side of the float band depending on the two
    spellings, so a single pair could be the one that happens to divide
    cleanly and a guard built on it would be green in the broken state
    (DL-189). The sweep walks every tenth of a second up to 200.0 and
    keeps the pairs whose decimals are exactly 99:100.
    """
    outside = []
    for tenths in range(1, 2001):
        high = tenths / 10
        high_text = f"{high:.1f}"
        low_text = f"{high * 99 / 100:.4f}"
        from decimal import Decimal

        if Decimal(low_text) * 100 != Decimal(high_text) * 99:
            continue
        if metadata_tier.outlier_attrs(
            {"playtime_float": (low_text, high_text)}, {"playtime_float": high_text}
        ):
            outside.append((low_text, high_text))
    assert outside == []


def test_format_value_survives_a_magnitude_float_cannot_hold():
    """Fail-first mutation: format_value's except clause read
    `(TypeError, ValueError)`.
    Observed:
        OverflowError: int too large to convert to float

    The tier screens every non-finite value, so no outlier reading
    carries one to gui/answer_detail.format_value. Its own guard stands
    for the values that reach it by another route, and OverflowError is
    one of them: an int past the double range raises it out of float()
    rather than the ValueError the clause already names, and a page build
    must not die on a value it is only formatting. The raw value prints
    as itself with no formatted companion, the way the empty string does.

    The guard stands beside the tier's own because the value it is about
    is the tier's: format_value is where an unscreened measured number
    surfaced, at reconstruct_report.py:592.
    """
    from traktor_nml.gui import answer_detail

    for attr in ("filesize", "playtime_float", "bitrate"):
        assert answer_detail.format_value(attr, 10 ** 400) is None

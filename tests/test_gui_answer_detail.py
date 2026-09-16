"""Guards traktor_nml/gui/answer_detail.py: the fields one answer draws,
their labels, their formatted companions and their marks.

Every reading here is of the module's return value under the system
interpreter, which has no nicegui. What it cannot hold is that the rail
calls it - a formatter guarded alone while the screen still joins the
values into one label is the guard green in exactly the broken state
this change exists to end (DL-189). That reading is the resolve step's
own composition guard and the served-page record's.

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation.

The units are the collection's own: FILESIZE is Traktor's kilobyte count
and BITRATE is bits per second, so each reading is one division and the
precision is the approved design read literally (ref: DL-247, DL-255).
There is no provenance branch to guard, because a disk-scanned record
never reaches a conflict group (ref: DL-253). The empty string a record
with no INFO element carries prints as itself with no formatted
companion (ref: DL-248), and the mark is a membership test against attrs
rather than a second divergence computation (ref: DL-243).
"""

from __future__ import annotations

import ast
from pathlib import Path

from traktor_nml.gui import answer_detail
from traktor_nml.splice import ConflictCandidate, _TRACKED_ATTRS

MODULE_PATH = Path(__file__).parent.parent / "traktor_nml" / "gui" / "answer_detail.py"


def test_the_fields_come_back_in_tracked_attrs_order_under_their_nml_labels():
    """The rows are ordered by splice._TRACKED_ATTRS, not by attrs then
    agreed, so one answer's rows stand against the next answer's rows.
    Every label is the NML attribute name in uppercase.

    Mutation: the loop in answer_fields was changed to iterate
    `list(divergent) + list(settled)` and this guard rerun. Observed:
        E       AssertionError: assert ['bitrate', '...aytime_float'] == ['artist', 't...t', 'bitrate']
        E
        E         At index 0 diff: 'bitrate' != 'artist'
        E         Use -v to get more diff
        FAILED tests/test_gui_answer_detail.py::test_the_fields_come_back_in_tracked_attrs_order_under_their_nml_labels
        1 failed in 0.47s
    """
    fields = answer_detail.answer_fields(
        attrs=("bitrate", "title"),
        agreed=(
            ("artist", "Kraftwerk"),
            ("album", "Autobahn"),
            ("filesize", "8192"),
            ("playtime_float", "99.6"),
        ),
        candidate=ConflictCandidate(values=("320000", "Autobahn"), members=((0, "k"),)),
    )
    assert [f.attr for f in fields] == list(_TRACKED_ATTRS)
    assert [f.label for f in fields] == [
        "ARTIST",
        "TITLE",
        "ALBUM",
        "FILESIZE",
        "PLAYTIME_FLOAT",
        "BITRATE",
    ]


def test_a_kilobyte_filesize_and_a_bits_per_second_bitrate_read_once_divided():
    """FILESIZE is Traktor's kilobyte count, so 8192 is 8.0 MB under one
    division by 1024; a second division would put it on screen as 0.0
    MB. BITRATE is bits per second, so 320000 is 320 kbps under one
    division by 1000.

    Mutation: `number / 1024` was changed to `number / 1024 / 1024` and
    this guard rerun. Observed:
        E       AssertionError: assert '0.0 MB' == '8.0 MB'
        E
        E         - 8.0 MB
        E         ? ^
        E         + 0.0 MB
        E         ? ^
        FAILED tests/test_gui_answer_detail.py::test_a_kilobyte_filesize_and_a_bits_per_second_bitrate_read_once_divided
        1 failed in 0.47s
    """
    assert answer_detail.format_value("filesize", "8192") == "8.0 MB"
    assert answer_detail.format_value("bitrate", "320000") == "320 kbps"


def test_seconds_read_as_minutes_and_zero_padded_seconds():
    """99.6 seconds is 1:39 - the seconds truncated toward zero and
    padded to two digits, so no row reads 1:9 or 1:99.

    Mutation: the seconds field of the returned string was changed from
    `{seconds:02d}` to `{seconds}` and this guard rerun. Observed:
        E       AssertionError: assert '0:9' == '0:09'
        E
        E         - 0:09
        E         ?   -
        E         + 0:9
        FAILED tests/test_gui_answer_detail.py::test_seconds_read_as_minutes_and_zero_padded_seconds
        1 failed in 0.50s
    """
    assert answer_detail.format_value("playtime_float", "99.6") == "1:39"
    assert answer_detail.format_value("playtime_float", "100.0") == "1:40"
    assert answer_detail.format_value("playtime_float", "9.0") == "0:09"


def test_a_field_the_answers_agree_on_carries_no_mark_and_a_diverging_one_does():
    """The mark says the answers disagree on this field. A field read
    off agreed carries none, which is what keeps the mark from standing
    on every row and saying nothing.

    Mutation: `raw, differs = settled[attr], False` was changed to
    `raw, differs = settled[attr], True` and this guard rerun. Observed:
        E       AssertionError: assert {'album', 'ar...oat', 'title'} == {'bitrate', 'filesize'}
        E
        E         Extra items in the left set:
        E         'playtime_float'
        E         'artist'
        E         'album'
        E         'title'
        E         Use -v to get more diff
        FAILED tests/test_gui_answer_detail.py::test_a_field_the_answers_agree_on_carries_no_mark_and_a_diverging_one_does
        1 failed in 0.47s
    """
    attrs = ("filesize", "bitrate")
    agreed = (
        ("artist", "Kraftwerk"),
        ("title", "Autobahn"),
        ("album", "Autobahn"),
        ("playtime_float", "99.6"),
    )
    fields = answer_detail.answer_fields(
        attrs=attrs,
        agreed=agreed,
        candidate=ConflictCandidate(values=("8192", "320000"), members=((0, "k"),)),
    )
    marks = {f.attr: f.differs for f in fields}
    assert {name for name, marked in marks.items() if marked} == set(attrs)
    assert {name for name, marked in marks.items() if not marked} == {
        name for name, _ in agreed
    }


def test_a_one_answer_group_and_a_six_way_divergence():
    """A group carrying no agreed pairs draws six marked rows; a group
    whose one answer diverges on one attribute draws that row marked and
    five unmarked. Neither drops a field the group carries.

    Mutation: `for attr in _TRACKED_ATTRS` was changed to `for attr in
    attrs` and this guard rerun. Observed:
        E       AssertionError: assert ['bitrate'] == ['artist', 't...t', 'bitrate']
        E
        E         At index 0 diff: 'bitrate' != 'artist'
        E         Right contains 5 more items, first extra item: 'title'
        E         Use -v to get more diff
        FAILED tests/test_gui_answer_detail.py::test_a_one_answer_group_and_a_six_way_divergence
        1 failed in 0.46s
    """
    six_way = answer_detail.answer_fields(
        attrs=_TRACKED_ATTRS,
        agreed=(),
        candidate=ConflictCandidate(
            values=("Kraftwerk", "Autobahn", "Autobahn", "8192", "99.6", "320000"),
            members=((0, "k"),),
        ),
    )
    assert [f.attr for f in six_way] == list(_TRACKED_ATTRS)
    assert all(f.differs for f in six_way)

    one_answer = answer_detail.answer_fields(
        attrs=("bitrate",),
        agreed=(
            ("artist", "Kraftwerk"),
            ("title", "Autobahn"),
            ("album", "Autobahn"),
            ("filesize", "8192"),
            ("playtime_float", "99.6"),
        ),
        candidate=ConflictCandidate(values=("320000",), members=((0, "k"),)),
    )
    assert [f.attr for f in one_answer] == list(_TRACKED_ATTRS)
    assert [f.attr for f in one_answer if f.differs] == ["bitrate"]


def test_no_formatted_value_carries_a_thousands_separator_and_raw_is_verbatim():
    """The raw string comes back exactly as given, and no formatted
    value introduces a separator: a grouped copy of the raw digits beside
    the raw digits reads as a third value.

    Mutation: the bitrate reading was changed from
    `f"{round(number / 1000)} kbps"` to `f"{round(number / 1000):,} kbps"`
    and this guard rerun. Observed:
        E       assert False
        E        +  where False = all(<generator object test_no_formatted_value_carries_a_thousands_separator_and_raw_is_verbatim.<locals>.<genexpr> at 0x000002693F0D31D0>)
        FAILED tests/test_gui_answer_detail.py::test_no_formatted_value_carries_a_thousands_separator_and_raw_is_verbatim
        1 failed in 0.47s
    """
    values = ("12582912", "7200.0", "1411000")
    fields = answer_detail.answer_fields(
        attrs=("filesize", "playtime_float", "bitrate"),
        agreed=(("artist", "Kraftwerk"), ("title", "Autobahn"), ("album", "Autobahn")),
        candidate=ConflictCandidate(values=values, members=((0, "k"),)),
    )
    assert [f.raw for f in fields if f.differs] == list(values)
    assert all("," not in f.formatted for f in fields if f.formatted is not None)
    assert [f.formatted for f in fields if f.differs] == [
        "12288.0 MB",
        "120:00",
        "1411 kbps",
    ]


def test_an_empty_value_and_a_non_numeric_value_return_no_formatted_companion():
    """A record with no INFO element carries "" for filesize, bitrate
    and playtime_float (traktor_nml/model.py), and the rail draws that
    record. An empty or unparseable value falls back to the raw string
    alone rather than raising or printing 0.0 MB.

    Mutation: the `except (TypeError, ValueError): return None` arm was
    deleted from format_value and this guard rerun. Observed:
        >       number = float(raw)
                 ^^^^^^^^^^
        E       ValueError: could not convert string to float: ''
        FAILED tests/test_gui_answer_detail.py::test_an_empty_value_and_a_non_numeric_value_return_no_formatted_companion
        1 failed in 0.46s
    """
    assert answer_detail.format_value("filesize", "") is None
    assert answer_detail.format_value("bitrate", "unknown") is None
    assert answer_detail.format_value("playtime_float", "") is None
    assert answer_detail.format_value("artist", "A") is None

    fields = answer_detail.answer_fields(
        attrs=("filesize",),
        agreed=(("bitrate", ""), ("playtime_float", "")),
        candidate=ConflictCandidate(values=("",), members=((0, "k"),)),
    )
    assert [(f.raw, f.formatted) for f in fields] == [("", None), ("", None), ("", None)]


def test_the_module_imports_no_nicegui():
    """The rule DL-069 states, read here as well as in the boundary
    sweep, because this module is the one a formatting change is most
    likely to be written into a nicegui call from.

    Mutation: `import nicegui` was added to the body of answer_fields -
    an import the module reaches without the suite failing to collect -
    and this guard rerun. Observed:
        E       AssertionError: assert 'nicegui' not in {'__future__', 'dataclasses', 'nicegui', 'typing'}
        FAILED tests/test_gui_answer_detail.py::test_the_module_imports_no_nicegui - ...
        1 failed in 0.48s
    """
    roots = set()
    for node in ast.walk(ast.parse(MODULE_PATH.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    assert "nicegui" not in roots
    assert "webview" not in roots

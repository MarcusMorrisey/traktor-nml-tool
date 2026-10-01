"""Guards the settled reading on the reconstruct page's preview step: the
classes app.py passes for it, the rules theme.page_stylesheet() declares
for those classes, and the artboard the two are built to.

A guard reading a class name is true in exactly the broken state, so what
the browser resolved from those names is read on a served page and
written into docs/2026-09-26-tiered-conflict-browser-record.md, whose
verdict-row digest is registered in
tests/test_docs_browser_record_structure.py (DL-084, DL-169, DL-189).
What this file can close is narrower and exact: every class named in the
page expands to a rule in the sheet, and no dimension or hex for the
reading stands in the page (DL-069, DL-188).

The second half runs reconstruct_report's own rules, which import no
framework either: what a record says its count is, how it divides and
orders its listing, and what a listed row calls a track.

theme.py imports no framework, so these run under the system interpreter
with no nicegui.

app.py is read as text and as an AST here rather than imported, because
importing it would import nicegui, which the system interpreter does not
hold: the classes the page passes are read out of the source and matched
against the sheet's own rules, which is the pairing a guard can close
without a browser (DL-069, DL-189).

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation. This file is LF, like the rest of
tests/.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import tinycss2

from traktor_nml import metadata_tier
from traktor_nml.gui import answer_detail, conflict_model, reconstruct_report, theme

_ROOT = Path(__file__).resolve().parents[1]
_APP_PY = _ROOT / "traktor_nml" / "gui" / "app.py"
_ARTBOARD = _ROOT / "design" / "reconnect-wizard" / "Preview.dc.html"

# The classes the reading is drawn with. Named rather than discovered, so
# a class dropped from the page fails this file rather than shrinking the
# set it checks - a guard green in exactly the broken state (DL-189).
READING_CLASSES = (
    "wizard-callout-info",
    "wizard-outlier-row",
    "wizard-outlier-name",
    "wizard-outlier-key",
    "wizard-outlier-values",
    "wizard-outlier-winner",
    "wizard-outlier-gap",
    "wizard-outlier-remainder",
    "wizard-outlier-remainder-name",
    "wizard-outlier-remainder-gap",
)

# The two collection names a run over a pair holds at input indices 0 and
# 1, which is what app.py's _collection_labels answers: the collection
# being repaired first, then the source. A listed reading's winner cell is
# worded from this tuple and the input index the settled row carries
# (DL-150).
_LABELS = ("base", "collection-b.nml")


def _sheet() -> str:
    return theme.page_stylesheet()


def _source() -> str:
    return _APP_PY.read_text(encoding="utf-8")


def _named_function(name: str) -> ast.FunctionDef:
    for node in ast.walk(ast.parse(_source())):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    raise AssertionError(f"app.py defines no {name}")


def _declares(name: str, sheet: str) -> bool:
    return bool(re.search(rf"\.{re.escape(name)}\b\s*[,{{:]", sheet))


def _artboard_rules() -> dict[str, dict[str, str]]:
    """Every rule the artboard's stylesheet reaches the CSSOM as, read by
    parsing the <style> element rather than by matching its text.

    The text of a rule can stand in the file and still reach no browser:
    an HTML comment between <style> and </style> tokenises as a CSS CDO,
    so the prose after it becomes a selector prelude running to the next
    brace and the rule it swallows is dropped. A guard that regexes the
    rule's literal source out of the file passes in exactly that state,
    which is the blindness DL-189 names. Parsing closes it: a dropped
    rule is a selector this mapping does not hold.

    Declarations are keyed by property, lowercased, with the serialised
    value, so a caller asks what the browser would compute rather than
    how the source happens to be spelled.

    A CDO reaches the parser as a token of its own, which serialising a
    prelude does not put back, so the run-on selector alone does not name
    its cause. The <style> bodies are checked for the token directly and
    the parse then stands on its own: a rule missing from this mapping
    fails whatever swallowed it.
    """
    text = _ARTBOARD.read_text(encoding="utf-8")
    bodies = [
        block.group(1)
        for block in re.finditer(r"<style[^>]*>(.*?)</style>", text, re.S | re.I)
    ]
    assert bodies, "the artboard holds no <style> element"
    assert not [body for body in bodies if "<!--" in body], (
        "an HTML comment stands inside a <style> element: '<!--' tokenises as a "
        "CSS CDO, so the prose after it runs on as a selector prelude to the "
        "next brace and the rule it swallows reaches no browser"
    )
    rules: dict[str, dict[str, str]] = {}
    errors: list[str] = []

    def walk(nodes) -> None:
        for node in nodes:
            if node.type == "error":
                errors.append(f"{node.kind}: {node.message}")
            elif node.type == "at-rule":
                if node.content is not None:
                    walk(
                        tinycss2.parse_rule_list(
                            node.content, skip_comments=True, skip_whitespace=True
                        )
                    )
            elif node.type == "qualified-rule":
                selector = tinycss2.serialize(node.prelude).strip()
                declarations: dict[str, str] = {}
                for entry in tinycss2.parse_declaration_list(
                    node.content, skip_comments=True, skip_whitespace=True
                ):
                    if entry.type == "error":
                        errors.append(f"in {selector!r}: {entry.message}")
                    else:
                        declarations[entry.lower_name] = tinycss2.serialize(
                            entry.value
                        ).strip()
                rules[selector] = declarations

    for body in bodies:
        walk(
            tinycss2.parse_stylesheet(body, skip_comments=True, skip_whitespace=True)
        )
    assert not errors, f"the artboard stylesheet does not parse: {errors}"
    return rules


@pytest.mark.parametrize("name", READING_CLASSES)
def test_every_class_the_reading_names_expands_to_a_rule(name):
    """A class string the sheet does not declare draws an unstyled row and
    no import fails, which is why the cascade is read here rather than
    left to the page (DL-069).

    Fail-first mutation: the .wizard-outlier-winner rule removed from
    page_stylesheet().
    Observed:
        E       AssertionError: page_stylesheet() declares no .wizard-outlier-winner
        E       assert False
        E        +  where False = _declares('wizard-outlier-winner', "\\n@font-face { font-family: 'IBM Plex Sans'; font-style: normal; font-weight: 400; font-display: block; src: url('/fo...izard-control, .wizard-field-row > .wizard-control, .buildplaylist-input-row > .wizard-control { margin-bottom: 0; }\\n")
        E        +    where "\\n@font-face { font-family: 'IBM Plex Sans'; font-style: normal; font-weight: 400; font-display: block; src: url('/fo...izard-control, .wizard-field-row > .wizard-control, .buildplaylist-input-row > .wizard-control { margin-bottom: 0; }\\n" = _sheet()
        tests\\test_gui_settled_reading.py:93: AssertionError
    """
    assert _declares(name, _sheet()), f"page_stylesheet() declares no .{name}"


def test_the_page_names_no_class_the_sheet_does_not_declare():
    """Read the other way round: every class app.py passes for the
    settled reading is one the sheet declares, so a typo in a class
    string fails here rather than on a served page.

    Fail-first mutation: "wizard-outlier-gaps" passed for the gap cell in
    app.py's outlier_row.
    Observed:
        E       AssertionError: app.py names classes the sheet does not declare: ['wizard-outlier-gaps']
        E       assert ['wizard-outlier-gaps'] == []
        E
        E         Left contains one more item: 'wizard-outlier-gaps'
        E         Use -v to get more diff
        tests\\test_gui_settled_reading.py:126: AssertionError
    """
    sheet = _sheet()
    named: set[str] = set()
    for node in ast.walk(ast.parse(_source())):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "classes"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            for name in node.args[0].value.split():
                if name.startswith("wizard-outlier") or name == "wizard-callout-info":
                    named.add(name)
    missing = sorted(name for name in named if not _declares(name, sheet))
    assert missing == [], (
        f"app.py names classes the sheet does not declare: {missing}"
    )


def test_the_page_names_every_class_the_reading_is_drawn_with():
    """The other half of the pairing: a cell dropped from outlier_row
    leaves its rule standing in the sheet with nothing carrying it, which
    is a reading missing a line rather than an unstyled one.

    Fail-first mutation: the winner cell's ui.label removed from
    outlier_row.
    Observed:
        E       AssertionError: the page draws no ['wizard-outlier-winner']
        E       assert ['wizard-outlier-winner'] == []
        E
        E         Left contains one more item: 'wizard-outlier-winner'
        E         Use -v to get more diff
        tests\\test_gui_settled_reading.py:152: AssertionError
    """
    source = _source()
    absent = [
        name
        for name in READING_CLASSES
        if not re.search(rf'"[^"]*\b{re.escape(name)}\b[^"]*"', source)
    ]
    assert absent == [], f"the page draws no {absent}"


def test_the_listing_row_stacks_four_areas_against_the_gap_column():
    """The gap holds its own column against all four stacked cells, which
    is why the row is a grid with named areas rather than a flex column.
    The winner area is one of the four: the row names the record the
    output keeps (DL-148).

    Fail-first mutation: grid-template-areas left at the three-area
    string "name gap" "key gap" "values gap".
    Observed:
        E           assert '"winner gap"' in '.wizard-outlier-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "name gap" "key gap" "values gap"; gap: 2px 12px; align-items: center; padding: 8px 2px; font-size: 12.5px; }'
        tests\\test_gui_settled_reading.py:171: AssertionError
    """
    sheet = _sheet()
    rule = re.search(r"\.wizard-outlier-row\s*\{[^}]*\}", sheet).group(0)
    assert "display: grid" in rule
    for area in ('"name gap"', '"key gap"', '"values gap"', '"winner gap"'):
        assert area in rule
    for cell in ("name", "key", "values", "winner", "gap"):
        assert f"grid-area: {cell}" in sheet, f"no cell claims grid-area: {cell}"


def test_the_listing_draws_its_separator_between_rows():
    """The settled sentence stands in the same container as the rows and
    follows them, so the last row is never its parent's last child. The
    rule that ends the list is a top border on every row after the first:
    an edge no following sibling can defeat. A bottom border on each row
    cancelled by :last-child reads green in the sheet while the served
    page draws a line under the final row (DL-189, DL-325).

    Fail-first mutation: the separator declared the cancelled way -
    `border-bottom: 1px solid {SURFACE_5}` put back inside
    .wizard-outlier-row and `.wizard-outlier-row:last-child {{
    border-bottom: 0; }}` restored in place of the adjacent-sibling rule.
    Observed:
        E       AssertionError: the row itself carries the separator
        E       assert 'border' not in '.wizard-out...e: 12.5px; }'
        E
        E         'border' is contained here:
        E            8px 2px; border-bottom: 1px solid #23272B; font-size: 12.5px; }
        E         ?           ++++++
        tests\\test_gui_settled_reading.py:199: AssertionError
    """
    sheet = _sheet()
    rule = re.search(r"\.wizard-outlier-row\s*\{[^}]*\}", sheet).group(0)
    assert "border" not in rule, "the row itself carries the separator"
    between = re.search(
        r"\.wizard-outlier-row \+ \.wizard-outlier-row\s*\{[^}]*\}", sheet
    )
    assert between, "no rule draws a separator between two rows"
    assert "border-top: 1px solid" in between.group(0)
    assert ".wizard-outlier-row:last-child" not in sheet, (
        "a :last-child rule stands that no composition can match"
    )


def test_the_page_holds_no_dimension_hex_or_percentage_for_the_reading():
    """Every pixel size, hue and formatted number for the reading lives in
    theme.py and in the record, so the page is composition alone (DL-069,
    DL-215).

    Fail-first mutation: `.style("color:#F5D96B")` added to the gap
    cell's label in outlier_row.
    Observed:
        E       AssertionError: the outlier row holds a hex, a dimension or a format
        E       assert ['#F5D96B'] == []
        E
        E         Left contains one more item: '#F5D96B'
        E         Use -v to get more diff
        tests\\test_gui_settled_reading.py:228: AssertionError
    """
    block = ast.get_source_segment(_source(), _named_function("outlier_row")) or ""
    assert block, "app.py defines no outlier_row"
    offenders = re.findall(r"#[0-9A-Fa-f]{6}|\d+px|\d+%|:[.,]\d[fd]", block)
    assert offenders == [], (
        "the outlier row holds a hex, a dimension or a format"
    )


def test_the_artboard_draws_the_surfaces_the_page_composes():
    """DL-071: the screen is built to the artboard, so the artboard holds
    the settled note in the .note info tint and the .ol rows with a .w
    cell before the page names their classes.

    Two info notes: the one under the could-not-fill card about the
    playlists left untouched, and the settled note in the left column
    beside the conflict note.

    The artboard's own .meta sentence closes the .card-b the .ol rows
    stand in, so the artboard draws its separator between rows as well:
    the sheet and the screen agree on which edge carries the line.

    The rules are read out of the parsed stylesheet, not matched in the
    file, so a rule whose text stands in the source while the browser
    drops it fails here. See _artboard_rules.

    Fail-first mutation: the .w span removed from each of the artboard's
    three .ol rows.
    Observed:
        E       assert 0 == 3
        E        +  where 0 = <built-in method count of str object at 0x0000028F5A50EE10>('class="w"')
        E        +    where <built-in method count of str object at 0x0000028F5A50EE10> = '<!doctype html>\\n<html>\\n<head>\\n  <meta charset="utf-8">\\n  <script src="./support.js"></script>\\n</head>\\n<body>\\n<... class="btn btn-pri">Decide the 63 conflicts</button>\\n    </span>\\n  </footer>\\n\\n</div>\\n</x-dc>\\n</body>\\n</html>\\n'.count
        tests\\test_gui_settled_reading.py:257: AssertionError

    Second mutation, the one the parse is here for: the .ol commentary in
    the <style> element written as an HTML comment instead of a CSS one,
    which is the state the literal-text guard read as green.
    Observed:
        >       rules = _artboard_rules()
        tests\\test_gui_settled_reading.py:355:
        >       assert not [body for body in bodies if "<!--" in body], (
        E       AssertionError: an HTML comment stands inside a <style> element: '<!--' tokenises as a CSS CDO, so the prose after it runs on as a selector prelude to the next brace and the rule it swallows reaches no browser
        E       assert not ["\\n@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400... 0 0 1px #3C4248;font-weight:600}\\n.steprail{display:flex;gap:2px;align-items:center;grid-column:1 / -1;margin:0}\\n  "]
        tests\\test_gui_settled_reading.py:123: AssertionError

    With that source check taken out, the parse alone still fails on the
    same mutation, which is what makes it a guard against a dropped rule
    whatever the cause:
        >       assert ".ol" in rules, sorted(rules)
        E       AssertionError: ['*', '.app', '.bar', '.big', '.brand', '.btn', ...]
        E       assert '.ol' in {'*': {'box-sizing': 'border-box'}, '.app': {'display': 'grid', 'grid-template-rows': '56px 1fr 64px', 'height': '800p... 'none', 'height': '16px', 'width': '1px'}, '.big': {'font': '600 15px/1 "IBM Plex Mono",ui-monospace,monospace'}, ...}
    """
    artboard = _ARTBOARD.read_text(encoding="utf-8")
    assert artboard.count('class="note info"') == 2
    assert artboard.count('class="ol"') == 3
    assert artboard.count('class="w"') == 3
    rules = _artboard_rules()
    assert ".ol" in rules, sorted(rules)
    row = rules[".ol"]
    assert row["display"] == "grid"
    for area in ('"nm g"', '"k g"', '"v g"', '"w g"'):
        assert area in row["grid-template-areas"]
    assert not [name for name in row if name.startswith("border")]
    assert rules[".ol + .ol"]["border-top"] == "1px solid #23272B"
    assert not [name for name in rules if name.startswith(".ol:last-child")]
    # The row standing for every reading the three above do not draw. It
    # carries the same top-border rule as an .ol row, so the card reads as
    # one list divided rather than as a list and a footnote.
    assert artboard.count('class="olr"') == 1
    assert ".olr" in rules, sorted(rules)
    assert rules[".olr"]["border-top"] == "1px solid #23272B"
    # The three listed rows stand in gap order, widest first, which is the
    # order the record hands them in.
    gaps = [float(text) for text in re.findall(r'class="g">([\d.]+)%', artboard)]
    assert gaps == sorted(gaps, reverse=True), gaps


def _body_source_of(name: str) -> str:
    node = _named_function(name)
    source = _source()
    return "\n".join(
        ast.get_source_segment(source, statement) or "" for statement in node.body
    )


def _stats(**overrides) -> dict:
    """A held run's stats, as splice.assemble_output reports them. Only
    the keys the settled reading is composed from carry a value here."""
    stats = {
        "reconstructed_playlists": {},
        "refilled_playlists": 0,
        "empty_playlists": 0,
        "unfilled_playlists": [],
        "collection_entries_total": 0,
        "groups_settled_by_rule": 0,
    }
    stats.update(overrides)
    return stats


def _settled(
    identity_key,
    attr,
    kept,
    other,
    gap,
    winner=(0, "C:/:Music/:one.mp3"),
    artist="Drexciya",
    title="Andreaen Sand Dunes",
):
    """One splice.SettledRow-shaped stand-in.

    The record reads identity_key, winner, outliers and - for the track
    cell - artist and title, so those are what this carries.
    splice.SettledRow's own shape is guarded in tests/test_splice.py."""
    return SimpleNamespace(
        identity_key=identity_key,
        attrs=(attr,),
        winner=winner,
        artist=artist,
        title=title,
        outliers=(
            metadata_tier.OutlierReading(
                attr=attr, kept=kept, other=other, relative_gap=gap
            ),
        )
        if gap
        else (),
        is_outlier=bool(gap),
    )


def _readings(count: int, first_gap: float = 0.9):
    """count settled rows, each one reading past the band, with gaps
    descending from first_gap so the widest-first order below is a
    property of the record rather than of the order they are handed in.

    They are handed in ASCENDING, which is the order the record must not
    keep: the union-find walk that produces them on a real run is no
    order at all.
    """
    rows = [
        _settled(
            f"C:/:Music/:{index}.mp3",
            "filesize",
            "69203",
            "17564",
            first_gap - index / 100,
            # No artist, so the track cell reads as the title alone and
            # the ordering below is read off one word.
            artist="",
            title=f"Track {index}",
        )
        for index in range(count)
    ]
    return tuple(reversed(rows))


def test_a_refused_run_reads_what_it_settled():
    """splice.py:187 and splice_cmd.py:110 both state that a run
    populates and prints its settled rows on an abort by design, and the
    CLI's settled_outlier line is printed on exactly that abort. So the
    refusal record carries the same reading the assembled one does: a
    collection pair holding one editorial divergence aborts, which is
    where most operators meet a run at all, and a screen that drops the
    reading there drops it for them entirely (DL-215, DL-329).

    Fail-first mutation: `class PreviewRefusal(_SettledReading)` written
    back as `class PreviewRefusal`. Observed:
        E       AttributeError: 'PreviewRefusal' object has no attribute 'settled_sentence'
    """
    record = reconstruct_report.preview_refusal(
        [conflict_model.CONFLICT_ABORT_TOKEN],
        [],
        _stats(groups_settled_by_rule=2203),
        (_settled("C:/:Music/:one.mp3", "playtime_float", "3828.0", "311.5", 0.9186),),
        _LABELS,
    )
    assert record.settled == 2203
    assert "2203 tracks are measured differently" in record.settled_sentence
    assert record.outlier_count == 1
    assert record.outlier_title == "The one measured far apart"
    listed, = record.outliers
    assert listed.gap_amount == "91.9%"
    assert listed.winner == "base: C:/:Music/:one.mp3"
    assert record.outlier_note == reconstruct_report.PreviewReport(
        listed=(), remainder=None, filled=0, empty=0, entries_added=0,
        unfilled=(), conflicts=0, outstanding=0,
    ).outlier_note, "one note, worded once, for both step 2 records"


def test_a_refused_run_the_rule_settled_nothing_for_reads_nothing():
    """The reading is the run's, not the screen's: a refusal for a run
    that settled no group says what stopped it and nothing else, the way
    a settled sentence naming 0 names something no run did.

    Fail-first mutation: the `if not self.settled: return ""` guard
    removed from _SettledReading.settled_sentence. Observed:
        E       AssertionError: assert '0 tracks are...output keeps.' == ''
        E
        E         + 0 tracks are measured differently by the two collections - file size, length or bitrate. Both numbers are Traktor's own, so there is nothing to decide. Each carries the values of the record the output keeps.
    """
    record = reconstruct_report.preview_refusal(
        ["ambiguous_playlist_name x"], [], _stats(), (), _LABELS
    )
    assert record.settled_sentence == ""
    assert record.outliers == ()
    assert record.outlier_remainder is None


def test_the_settled_count_is_the_runs_own_number():
    """stats carries `groups_settled_by_rule`, which splice writes off the
    same list settled_rows is. The record reads the count from there, so
    it cannot state a count the mapping it was built from disagrees with -
    which is what a count derived from a capped listing would do, naming
    three tracks for a run that settled two thousand (DL-204, DL-215).

    Fail-first mutation: `int(stats.get("groups_settled_by_rule") or 0)`
    in _settled_reading written back as `len(settled_rows)`. Observed:
        E       AssertionError: assert 5 == 2203
        E        +  where 5 = PreviewReport(listed=(), remainder=None, filled=0, empty=0, entries_added=0, unfilled=(), conflicts=0, outstanding=0, ...88, winner='base: C:/:Music/:one.mp3')), outlier_remainder=OutlierRemainder(count=2, widest_gap=0.87), outlier_total=5).settled
    """
    record = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=2203),
        (),
        conflict_model.ConflictDecisions(),
        _readings(5),
        _LABELS,
    )
    assert record.settled == 2203
    assert "2203 tracks are measured differently" in record.settled_sentence


def test_both_step_records_ask_for_the_runs_settled_rows():
    """The rows are a required argument rather than one defaulting empty.
    stats already carries `groups_settled_by_rule`, so a caller that
    omitted them composed a record whose listing was empty for a run whose
    own stats named thousands of settled groups - the record saying less
    than the mapping it was built from, which no default makes safe. A
    caller holding the stats holds the rows beside them (DL-204, DL-215).

    Fail-first mutation: `settled_rows: Sequence[object]` and `labels:
    Sequence[str]` on both functions given back their `= ()` defaults.
    Observed:
        E       Failed: DID NOT RAISE <class 'TypeError'>
    """
    import pytest

    with pytest.raises(TypeError):
        reconstruct_report.preview_report(
            _stats(), (), conflict_model.ConflictDecisions()
        )
    with pytest.raises(TypeError):
        reconstruct_report.preview_refusal(["some_token"], ())


def test_the_measured_listing_is_divided_the_way_the_playlists_are():
    """A real collection pair reads past the band on thousands of
    attributes, and Preview.dc.html draws three rows and one row standing
    for the rest. So the readings are divided at LISTED_OUTLIERS the way
    the playlists are divided at LISTED_PLAYLISTS: the count in the card's
    head names every reading, the rows under it are the listed slice, and
    the remainder row says how many are left and how wide the widest of
    those reaches (DL-217, DL-331).

    Fail-first mutation: `listed = tuple(readings[:LISTED_OUTLIERS])`
    written back as `listed = tuple(readings)`. Observed, cut at the
    margin rather than rewrapped:
        E       AssertionError: assert 7 == 3
        E        +  where 7 = len((OutlierRow(track='Track 0', label='FILESIZE', low='17564', high='69203', low_detail='17.2 MB', high_detail='67.6 MB',... high='69203', low_detail='17.2 MB', high_detail='67.6 MB', relative_gap=0.85, winner='base: C:/:Music/:one.mp3'), ...))
    """
    record = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=7),
        (),
        conflict_model.ConflictDecisions(),
        _readings(7),
        _LABELS,
    )
    assert reconstruct_report.LISTED_OUTLIERS == 3
    assert len(record.outliers) == 3
    # The head counts every reading the run made, not the three drawn.
    assert record.outlier_count == 7
    assert record.outlier_title == "The 7 measured far apart"
    remainder = record.outlier_remainder
    assert remainder is not None
    assert remainder.count == 4
    assert remainder.name == "and 4 more measured far apart"
    # The widest of the four this row stands for, which is the next gap
    # below the narrowest listed one.
    assert remainder.gap_amount == "87.0% and narrower"


def test_a_listing_within_the_cap_draws_no_remainder_row():
    """The remainder row stands for something or it does not stand: a run
    with three readings has nothing left over, the way a run with nine
    filled playlists draws no summary row (DL-217).

    Fail-first mutation: the `if rest else None` on the remainder in
    _settled_reading replaced by an unconditional
    `OutlierRemainder(count=len(rest), widest_gap=readings[-1].relative_gap)`.
    Observed:
        E       AssertionError: assert OutlierRemainder(count=0, widest_gap=0.88) is None
        E        +  where OutlierRemainder(count=0, widest_gap=0.88) = PreviewReport(listed=(), remainder=None, filled=0, empty=0, entries_added=0, unfilled=(), conflicts=0, outstanding=0, ...88, winner='base: C:/:Music/:one.mp3')), outlier_remainder=OutlierRemainder(count=0, widest_gap=0.88), outlier_total=3).outlier_remainder
    """
    record = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=3),
        (),
        conflict_model.ConflictDecisions(),
        _readings(3),
        _LABELS,
    )
    assert len(record.outliers) == 3
    assert record.outlier_remainder is None


def test_the_listing_is_ordered_widest_gap_first():
    """The band exists for the handful of playtime_float groups whose gap
    reaches thousands of seconds, and a listing in union-find order sits
    those at arbitrary offsets among thousands of 2 KB filesize drifts.
    So the readings are ordered by gap, widest first, and the three rows
    drawn are the three widest of them - which is also what makes the
    division deterministic, the way `(-entries, name)` makes the playlist
    listing's is.

    Fail-first mutation: _settled_reading's sort key replaced by
    `key=lambda reading: 0`, which is a stable sort over the order the
    rows arrived in - the union-find order a real run hands them in.
    Observed:
        E       AssertionError: assert ['Track 6', '...5', 'Track 4'] == ['Track 0', '...1', 'Track 2']
        E
        E         At index 0 diff: 'Track 6' != 'Track 0'
        E         Use -v to get more diff
    """
    record = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=7),
        (),
        conflict_model.ConflictDecisions(),
        _readings(7),
        _LABELS,
    )
    assert [row.track for row in record.outliers] == ["Track 0", "Track 1", "Track 2"]
    gaps = [row.relative_gap for row in record.outliers]
    assert gaps == sorted(gaps, reverse=True)


def test_two_readings_at_one_gap_are_ordered_by_what_they_name():
    """The gap alone is not a total order, and two readings at the same
    gap left in the order they arrived would put a different three rows on
    screen for two runs reporting the same readings. The track and the
    attribute behind it settle it.

    Fail-first mutation: the sort key reduced to
    `key=lambda reading: -reading.relative_gap`. Observed:
        E       AssertionError: assert ['Beta', 'Alpha'] == ['Alpha', 'Beta']
        E
        E         At index 0 diff: 'Beta' != 'Alpha'
        E         Use -v to get more diff
    """
    rows = (
        _settled("C:/:Music/:b.mp3", "filesize", "69203", "17564", 0.5,
                 artist="", title="Beta"),
        _settled("C:/:Music/:a.mp3", "filesize", "69203", "17564", 0.5,
                 artist="", title="Alpha"),
    )
    record = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=2),
        (),
        conflict_model.ConflictDecisions(),
        rows,
        _LABELS,
    )
    assert [row.track for row in record.outliers] == ["Alpha", "Beta"]


def test_a_listed_row_names_a_track_rather_than_a_path():
    """Preview.dc.html:192 draws `Drexciya - Andreaen Sand Dunes` in a
    listed reading's `.nm` cell. The identity key is a LOCATION, and the
    path is already on the row in its winner cell, read for which record
    it names; a track cell carrying the same path names no track at all
    (DL-071).

    A row carrying neither artist nor title reads as its identity key,
    which still tells the rows apart, so a record composed from rows that
    predate those two fields reads a listing rather than raising.

    Fail-first mutation: `track=_track_reading(row)` written back as
    `track=row.identity_key`. Observed:
        E       AssertionError: assert 'C:/:Music/:one.mp3' == 'Drexciya - A...en Sand Dunes'
        E
        E         - Drexciya - Andreaen Sand Dunes
        E         + C:/:Music/:one.mp3
    """
    named = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=1),
        (),
        conflict_model.ConflictDecisions(),
        (_settled("C:/:Music/:one.mp3", "filesize", "69203", "17564", 0.7462),),
        _LABELS,
    )
    assert named.outliers[0].track == "Drexciya - Andreaen Sand Dunes"
    # The winner cell carries the path, so the row names the record as
    # well as the track (DL-148).
    assert named.outliers[0].winner == "base: C:/:Music/:one.mp3"

    bare = SimpleNamespace(
        identity_key="C:/:Music/:one.mp3",
        winner=(0, "C:/:Music/:one.mp3"),
        outliers=(
            metadata_tier.OutlierReading(
                attr="filesize", kept="69203", other="17564", relative_gap=0.7462
            ),
        ),
    )
    fallen_back = reconstruct_report.preview_report(
        _stats(groups_settled_by_rule=1),
        (),
        conflict_model.ConflictDecisions(),
        (bare,),
        _LABELS,
    )
    assert fallen_back.outliers[0].track == "C:/:Music/:one.mp3"


def test_the_two_step_screens_with_no_run_report_place_the_reading():
    """_render_preview returned before _render_preview_run on a refused
    run and on a run that rebuilt no playlist, and _render_preview_run
    was the only caller of preview_report - so the settled sentence and
    the listing reached no screen in either state, while the CLI printed
    them for the same run. Both now draw the reading through one render
    (DL-215, DL-329).

    Read as source text: what the browser paints is a served-page reading
    (DL-189).

    Fail-first mutation: the `_render_settled_reading(record)` call
    removed from _render_preview_refusal. Observed - the assertion
    message printed the whole function body, so what stands here is its
    last line, with that function's own docstring quotes elided at the
    left rather than reproduced, which would close this docstring:
        E       assert '_render_settled_reading(' in '[...]A run that assembled nothing, composed as a card of its\\n                own rather than left as loose text.\\n\\n  ...(\\n                                            "wizard-mono wizard-body-12"\\n                                        )'
    """
    refusal = _body_source_of("_render_preview_refusal")
    assert "_render_settled_reading(" in refusal, refusal
    # The refusal record is composed from the run's own stats, settled
    # rows and collection labels, the three the assembled record reads.
    assert "result.settled_rows" in refusal, refusal
    assert "_collection_labels(source_holder)" in refusal, refusal

    preview = _body_source_of("_render_preview")
    assert "_render_settled_reading(_preview_record())" in preview, preview

    # A run that settled nothing and read nothing draws nothing: the
    # render places no column for it at all.
    reading = _body_source_of("_render_settled_reading")
    assert (
        "if not record.settled_sentence and not record.outliers:" in reading
    ), reading
    assert "return" in reading, reading


def test_the_remainder_row_is_drawn_from_the_records_own_strings():
    """The row standing for the unlisted readings carries two strings the
    record composed, like every cell of a drawn reading, so it cannot
    state a count or a percentage the rows above it disagree with. Every
    class it names is declared in theme.page_stylesheet(), so no
    dimension and no hex stands in app.py (DL-069, DL-079, DL-188,
    DL-215).

    Fail-first mutation: the remainder row's left cell written as
    `ui.label(f"and {remainder.count:,} more measured far apart")`.
    Observed:
        E       assert ['f"and {rema...r.gap_amount'] == ['remainder.n...r.gap_amount']
        E
        E         At index 0 diff: 'f"and {remainder.count:,} more measured far apart"' != 'remainder.name'
        E         Use -v to get more diff
    """
    from traktor_nml.gui import theme

    node = _named_function("outlier_remainder_row")
    source = _source()
    cells = [
        ast.get_source_segment(source, call.args[0])
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "label"
        and call.args
    ]
    assert cells == ["remainder.name", "remainder.gap_amount"]

    stylesheet = theme.page_stylesheet()
    for name in (
        "wizard-outlier-remainder",
        "wizard-outlier-remainder-name",
        "wizard-outlier-remainder-gap",
    ):
        assert f".{name} " in stylesheet, name

    # The rows and the remainder row are placed together, so the card
    # cannot draw a listing with its remainder row left off.
    rows = _body_source_of("outlier_rows")
    assert "outlier_remainder_row(record.outlier_remainder)" in rows, rows


def test_the_formatter_answers_none_for_a_value_no_measurement_spells():
    """format_value is total over every str. float() accepts 'nan', 'inf'
    and '1e400', and int() and round() over those raise ValueError and
    OverflowError rather than returning a number, so the reading stands
    inside the guard with the parse rather than after it. metadata_tier
    screens non-finite values where it parses them and nothing reaches
    here today; the reason this formatter answers None rather than raising
    does not depend on which caller found the value (ref: DL-248).

    Fail-first mutation: the three readings moved back below the
    try/except, as `except (TypeError, ValueError, OverflowError): return
    None` followed by the filesize, bitrate and playtime branches.
    Observed:
        E       ValueError: cannot convert float NaN to integer
    """
    for raw in ("nan", "inf", "-inf", "1e400", "-1e400", "", "not a number"):
        for attr in ("filesize", "playtime_float", "bitrate"):
            answer_detail.format_value(attr, raw)
    assert answer_detail.format_value("playtime_float", "inf") is None
    assert answer_detail.format_value("playtime_float", "-inf") is None
    assert answer_detail.format_value("playtime_float", "nan") is None
    assert answer_detail.format_value("bitrate", "nan") is None
    assert answer_detail.format_value("filesize", "inf") == "inf MB", (
        "a float division by 1024 answers inf, which formats; only the "
        "int() and round() readings raise"
    )
    # The readings a measurement does spell are unchanged.
    assert answer_detail.format_value("playtime_float", "99.6") == "1:39"
    assert answer_detail.format_value("filesize", "17564") == "17.2 MB"
    assert answer_detail.format_value("bitrate", "320000") == "320 kbps"

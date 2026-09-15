"""Guards traktor_nml/gui/wording.py and the rule that it is the only
place a count picks a word.

The module imports nothing, so these run the rule itself under the
system interpreter (DL-069). What a screen does with the word it gets
back is a served-page reading and belongs to a record under docs/
(DL-084, DL-189).

Each guard records the mutation applied to make it fail and the verbatim
output observed under that mutation.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from traktor_nml.gui.wording import plural

GUI_DIR = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui"

# A ternary choosing between two string literals on a count of one: the
# shape every screen in this package wrote out for itself before the
# rule had one home. Read as source text, because what it forbids is a
# spelling and not a value.
_INLINE_PLURAL = re.compile(
    r'"[^"]*"\s+if\s+[^\n]*?==\s*1\s+else\s+"[^"]*"'
    r"|'[^']*'\s+if\s+[^\n]*?==\s*1\s+else\s+'[^']*'"
)


def test_a_count_of_one_takes_the_singular_and_every_other_count_the_plural():
    """The rule itself, on the three counts that matter: one, more than
    one, and none. Zero takes the plural, because a change-list row
    reading `0 playlist` reads as a typo rather than as a count.

    Mutation: `return one if count == 1 else many` replaced by
    `return many`. Observed:
        E       AssertionError: assert 'tracks' == 'track'
        E         - track
        E         + tracks
    """
    assert plural(1, "track", "tracks") == "track"
    assert plural(2, "track", "tracks") == "tracks"
    assert plural(0, "playlist", "playlists") == "playlists"


def test_the_verb_travels_with_the_noun_it_agrees_with():
    """Both forms are given at the call site, so a form that is not the
    singular plus an `s` is stated rather than derived. These two are
    the ones a trailing-letter rule would get wrong.

    Mutation: as above. Observed:
        E       AssertionError: assert 'tracks carry' == 'track carries'
        E         - track carries
        E         + tracks carry
    """
    assert plural(1, "track carries", "tracks carry") == "track carries"
    assert plural(1, "track is", "tracks are") == "track is"
    assert plural(3, "It has", "Each one has") == "Each one has"


def test_no_screen_spells_the_choice_out_for_itself():
    """Every module under gui/ reads its word from `plural`, so a count
    of one is right on every screen at once rather than on the screens
    somebody remembered. `wording.py` is where the choice is spelled,
    and is the only file exempt.

    A sentence naming a count is the screen reporting the model it
    describes, so the rule it reads that count's word by is held in one
    place (DL-215, DL-233, DL-236).

    Mutation: in `reconstruct_report.write_report`, the call
    `plural(lost_from, "playlist", "playlists")` was restored to the
    inline form `"playlist" if lost_from == 1 else "playlists"`.
    Observed:
        E       AssertionError: a screen spells a plural out instead of
        reading it from wording.plural
        E       assert {'reconstruct_report.py': ['"playlist" if lost_from == 1 else "playlists"']} == {}
    """
    offenders = {}
    for path in sorted(GUI_DIR.glob("*.py")):
        if path.name == "wording.py":
            continue
        found = _INLINE_PLURAL.findall(path.read_text(encoding="utf-8"))
        if found:
            offenders[path.name] = found
    assert offenders == {}, (
        "a screen spells a plural out instead of reading it from wording.plural"
    )


def test_wording_imports_nothing_so_the_suite_can_reach_it():
    """The module stands on its own: no import at all, which is what
    puts it below every other gui module in the import order and keeps
    it reachable from an interpreter with no nicegui (DL-069).

    Mutation: `import re` added to wording.py. Observed:
        E       AssertionError: wording.py imports ['re']
        E       assert ['re'] == []
        E         Left contains one more item: 're'

    A sibling import was the first mutation tried and it fails this file
    earlier and louder - `ImportError: cannot import name 'plural' from
    partially initialized module 'traktor_nml.gui.wording' (most likely
    due to a circular import)` - which proves the import order this
    module sits at but not the assertion below, so the recorded mutation
    is the one that reaches it.
    """
    tree = ast.parse((GUI_DIR / "wording.py").read_text(encoding="utf-8"))
    imported = [
        name.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for name in node.names
    ] + [
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        # __future__ carries no module and binds no name at runtime.
        and node.module != "__future__"
    ]
    assert imported == [], f"wording.py imports {imported}"

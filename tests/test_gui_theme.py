"""Guards theme.py's token set: every hex literal
traktor_nml/gui/app.py uses comes from theme.py rather than being
repeated at the call site (DL-078), every colour, type, spacing and
radius token constant reaches page_stylesheet()'s emitted string, and
the measured foreground/background pairs Specs.dc.html and
Main.dc.html actually paint clear their contrast floors.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import tinycss2

from traktor_nml.gui import theme

_HEX_LITERAL = re.compile(r"#[0-9A-Fa-f]{6}\b")
_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"

# Every constant theme.py names, gathered by introspection rather than
# a hand-maintained list, so a constant added later is covered without
# this file changing (DL-078).
_ALL_TOKENS = [v for k, v in vars(theme).items() if k.isupper() and isinstance(v, str)]


def _missing_tokens(sheet: str, tokens) -> list:
    """The one place that decides whether a token reaches a
    stylesheet string; both the real guard and its mutation control
    call this rather than each re-implementing the membership check."""
    return [t for t in tokens if t not in sheet]


def test_hex_literal_scan_catches_a_planted_literal(tmp_path):
    """Mutation: a copy of app.py's real source has a six-digit hex
    literal '#123456' inserted into it. Observed: running the same
    _HEX_LITERAL regex test_app_py_carries_no_hex_literal uses,
    pointed at the mutated copy instead of the real file, finds that
    literal in the scan's result."""
    real_source = _APP_PY.read_text(encoding="utf-8")
    planted = tmp_path / "app.py"
    planted.write_text(real_source + "\n# #123456\n", encoding="utf-8")
    found = _HEX_LITERAL.findall(planted.read_text(encoding="utf-8"))
    assert found == ["#123456"]


def test_app_py_carries_no_hex_literal():
    """The positive case test_hex_literal_scan_catches_a_planted_literal's mutation control checks: app.py's real source has no six-digit hex literal."""
    source = _APP_PY.read_text(encoding="utf-8")
    found = _HEX_LITERAL.findall(source)
    assert found == [], f"app.py repeats a hex literal outside theme.py: {found}"


def test_every_status_and_action_token_reaches_the_stylesheet():
    """The positive case test_a_token_withheld_from_the_stylesheet_is_caught's mutation control checks: every constant theme.py names reaches page_stylesheet()'s emitted string."""
    sheet = theme.page_stylesheet()
    missing = _missing_tokens(sheet, _ALL_TOKENS)
    assert missing == [], f"token defined and never applied: {missing}"


def test_a_token_withheld_from_the_stylesheet_is_caught():
    """Mutation: page_stylesheet()'s real emitted string has
    STATUS_NOT_FOUND stripped out of it. Observed: the same
    _missing_tokens helper test_every_status_and_action_token_reaches_the_stylesheet
    calls, run against that stripped string with STATUS_NOT_FOUND as
    the only token checked, reports STATUS_NOT_FOUND missing."""
    stripped = theme.page_stylesheet().replace(theme.STATUS_NOT_FOUND, "")
    missing = _missing_tokens(stripped, [theme.STATUS_NOT_FOUND])
    assert missing == [theme.STATUS_NOT_FOUND]


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    channels = (int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def _linear(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (_linear(c) for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(a: str, b: str) -> float:
    la, lb = _relative_luminance(a), _relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


# Each pair below is a foreground/background/floor triple taken from an
# actual CSS rule in the design set - the background of the rule that
# carries the color: declaration - rather than every muted colour
# checked against every surface uniformly.
_TEXT_PAIRS = (
    # Main.dc.html:24 .st.done and :30 .ft-note against .hd/.ft's
    # SURFACE_2 background (Main.dc.html:16, :29); ratio 7.75:1.
    (theme.TEXT_MUTED, theme.SURFACE_2, 4.5),
    # Main.dc.html:18 .brand against .hd's SURFACE_2 background; ratio
    # 5.93:1.
    (theme.TEXT_FAINT, theme.SURFACE_2, 4.5),
    # Main.dc.html:47 .note against its own SURFACE_1 background
    # (Main.dc.html:47); ratio 7.91:1.
    (theme.TEXT_MUTED, theme.SURFACE_1, 4.5),
    # Main.dc.html:53 .meta against the page's GROUND background
    # (Main.dc.html:13 body); ratio 6.37:1.
    (theme.TEXT_FAINT, theme.GROUND, 4.5),
)

# Main.dc.html:55 .sw i (the switch-knob) painted only as a background,
# never as text, against its own track colour at Main.dc.html:54 .sw;
# ratio 3.45:1, cleared against the 3:1 non-text floor rather than
# folded into the 4.5:1 text floor above.
_NON_TEXT_PAIRS = (
    (theme.SWITCH_KNOB, theme.SWITCH_TRACK, 3.0),
)


def test_accessibility_floors():
    """Every measured text pair clears 4.5:1 against the specific
    surface the design set paints it on, and the switch-knob's
    non-text pair clears the 3:1 floor separately (Specs.dc.html,
    "Accessibility rules"), computed here from theme.py's own
    constants with the WCAG relative-luminance formula rather than
    asserted."""
    for fg, bg, floor in _TEXT_PAIRS:
        ratio = _contrast_ratio(fg, bg)
        assert ratio >= floor, f"{fg} against {bg} reaches only {ratio:.2f}:1"
    for fg, bg, floor in _NON_TEXT_PAIRS:
        ratio = _contrast_ratio(fg, bg)
        assert ratio >= floor, f"{fg} against {bg} reaches only {ratio:.2f}:1"

    sheet = theme.page_stylesheet()
    sizes = [
        float(m)
        for m in re.findall(r"font(?:-size)?:\s*(?:\d+\s+)?(\d+(?:\.\d+)?)px", sheet)
    ]
    assert sizes, "no font-size rules found in the stylesheet"
    assert min(sizes) >= 11
    body_sizes = [
        float(m)
        for m in re.findall(r"body\s*\{[^}]*?font(?:-size)?:\s*(?:\d+\s+)?(\d+(?:\.\d+)?)px", sheet)
    ]
    assert body_sizes and all(s >= 12 for s in body_sizes)


def test_contrast_floor_catches_a_pair_below_it():
    """Mutation: TEXT_FAINT (#8E979E) is fed to the real
    _contrast_ratio function against a stand-in surface (#7E868D)
    engineered to fall under 4.5:1 by lightening the background toward
    the text colour rather than darkening it - darkening a background
    RAISES contrast against light text. Observed: _contrast_ratio, the
    same function test_accessibility_floors calls, returns 1.24:1 for
    this pair, below the 4.5 floor."""
    lighter_surface = "#7E868D"
    ratio = _contrast_ratio(theme.TEXT_FAINT, lighter_surface)
    assert ratio < 4.5


def test_font_size_floor_catches_a_size_below_it():
    """Mutation: TYPE_14 is substituted with TYPE_11 minus a further
    stand-in 2px (i.e. a 9px value) inside a copy of the real
    stylesheet's body rule. Observed: the same regex
    test_accessibility_floors uses then parses a size below the 11px
    floor from that copy."""
    stand_in = theme.page_stylesheet().replace(theme.TYPE_14, "9px")
    sizes = [
        float(m)
        for m in re.findall(r"font(?:-size)?:\s*(?:\d+\s+)?(\d+(?:\.\d+)?)px", stand_in)
    ]
    assert min(sizes) < 11


_CLASS_RULE = re.compile(r"\.(wizard-[\w-]+)\s*\{([^}]*)\}")
_FONT_SIZE_IN_RULE = re.compile(r"font(?:-size)?:\s*(?:\d+\s+)?\d+(?:\.\d+)?px")


def _stylesheet_classes() -> dict:
    """Every top-level .wizard-* selector page_stylesheet() defines,
    mapped to whether its own rule body sets a font-size, via either
    font-size: or the font: shorthand - read from the sheet text
    itself rather than a hand-maintained list."""
    sheet = theme.page_stylesheet()
    return {name: bool(_FONT_SIZE_IN_RULE.search(body)) for name, body in _CLASS_RULE.findall(sheet)}


# A classes() argument is not always one literal: app.py builds some
# of them from an f-string over a name a dict subscript or a
# conditional assigns. Reading the source with a regex captures
# "{status_class}" verbatim, so every class name reached through an
# interpolation escapes the cascade guards below - the blind spot that
# hid a label carrying two colour-setting classes. These helpers parse
# app.py instead and expand each call into every literal it can
# produce. A part that does not resolve to string literals expands to
# _UNRESOLVED, which test_every_classes_call_expands_to_literals fails
# on, so an unreadable call is reported rather than skipped.
_UNRESOLVED = "<unresolved>"


def _literal_options(node, choices: dict) -> list:
    """Every string one expression node can evaluate to, given the
    names already resolved in choices."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _literal_options(node.body, choices) + _literal_options(node.orelse, choices)
    if isinstance(node, ast.Name):
        return sorted(choices[node.id]) if node.id in choices else [_UNRESOLVED]
    if isinstance(node, ast.JoinedStr):
        variants = [""]
        for part in node.values:
            inner = part.value if isinstance(part, ast.FormattedValue) else part
            options = _literal_options(inner, choices)
            variants = [v + option for v in variants for option in options]
        return variants
    return [_UNRESOLVED]


def _string_choices(module: ast.Module) -> dict:
    """Each name the module assigns string literals to, mapped to
    every literal it can hold. A dict subscript contributes all of the
    dict's values, since which key is read is a runtime choice."""
    choices: dict = {}
    for node in ast.walk(module):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = node.value
        if isinstance(value, ast.Subscript) and isinstance(value.value, ast.Dict):
            sources = value.value.values
        else:
            sources = [value]
        options = [opt for src in sources for opt in _literal_options(src, {})]
        if _UNRESOLVED not in options:
            choices.setdefault(target.id, set()).update(options)
    return choices


def _classes_calls(source: str) -> list:
    """Every literal class list a .classes(...) call in source can
    pass at run time, one entry per branch of an interpolation."""
    module = ast.parse(source)
    choices = _string_choices(module)
    calls = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "classes" or len(node.args) != 1:
            continue
        calls.extend(_literal_options(node.args[0], choices))
    return calls


def test_every_classes_call_expands_to_literals():
    """No .classes(...) call in app.py is opaque to the expansion the
    cascade guards read it through; an unresolved one would leave that
    call unchecked."""
    calls = _classes_calls(_APP_PY.read_text(encoding="utf-8"))
    assert calls, "no classes() calls found - the parser is broken"
    assert _UNRESOLVED not in calls, "a classes() call did not expand to string literals"


def test_an_interpolated_class_name_is_expanded():
    """Mutation: a synthetic module assigns tone from a dict subscript
    and interpolates it into a classes() f-string, the shape app.py
    uses at app.py:354. Observed: _classes_calls, the same helper the
    cascade guards route app.py through, returns
    ['w-24 wizard-tag-found', 'w-24 wizard-tag-missing'] for it - the
    dict's values in place of the unexpanded '{tone}'."""
    source = (
        "tone = {'a': 'wizard-tag-found', 'b': 'wizard-tag-missing'}[status]\n"
        "ui.label(status).classes(f'w-24 {tone}')\n"
    )
    assert _classes_calls(source) == ["w-24 wizard-tag-found", "w-24 wizard-tag-missing"]


# Tailwind's text-size utilities set font-size too, and are class
# selectors at the same 0,1,0 specificity as a .wizard-* rule, so an
# element carrying one of each has its size decided by <head> source
# order rather than by the token. Counting only wizard-* names is the
# blind spot this guard exists to close.
_TAILWIND_TEXT_SIZE = re.compile(r"^text-(?:xs|sm|base|lg|\d*xl)$")


def _size_setting_tokens(call: str) -> list:
    """Every token in one classes() literal that sets a font-size -
    the .wizard-* classes whose own rule sets one, plus Tailwind's
    text-size utilities."""
    font_size_classes = {name for name, sets_size in _stylesheet_classes().items() if sets_size}
    return [
        tok
        for tok in call.split()
        if tok in font_size_classes or _TAILWIND_TEXT_SIZE.match(tok)
    ]


def test_no_classes_call_sets_font_size_twice():
    offending = []
    for call in _classes_calls(_APP_PY.read_text(encoding="utf-8")):
        used = _size_setting_tokens(call)
        if len(used) > 1:
            offending.append((call, used))
    assert offending == [], f"classes() call sets font-size twice: {offending}"


def test_two_font_size_classes_on_one_call_is_caught():
    """Mutation: a synthetic classes() literal pairs Tailwind's
    text-xs with wizard-heading-sm - one utility and one token, the
    shape that stacks at equal specificity and is decided by <head>
    order. Observed: _size_setting_tokens, the same helper
    test_no_classes_call_sets_font_size_twice routes every real call
    through, returns ['text-xs', 'wizard-heading-sm'] for it, so the
    call is reported as setting font-size twice."""
    literal = "font-mono text-xs wizard-heading-sm"
    used = _size_setting_tokens(literal)
    assert used == ["text-xs", "wizard-heading-sm"]
    assert len(used) > 1


# wizard-heading-lg is the one class this guard does not require app.py
# to use: TYPE_23/wizard-heading-lg is restored byte-for-byte from the
# baseline commit because Success.dc.html:48's .hero h1 measures 23px
# and DL-078 keeps every measured type step theme.py names regardless
# of current wiring, but no milestone in this plan builds a Success
# step for that heading to attach to. Named here explicitly, one entry
# at a time, rather than by a pattern (e.g. every wizard-heading-*)
# that could let an unrelated, genuinely-forgotten class slip through
# unnoticed under the same excuse.
_KNOWN_UNATTACHED_CLASSES = {"wizard-heading-lg"}


def test_every_wizard_class_reaches_app_py():
    """The positive case test_a_withheld_class_is_caught's mutation control checks: every .wizard-* class page_stylesheet() defines, except _KNOWN_UNATTACHED_CLASSES's one documented entry, appears somewhere in app.py's source."""
    source = _APP_PY.read_text(encoding="utf-8")
    missing = [
        name for name in _stylesheet_classes()
        if name not in source and name not in _KNOWN_UNATTACHED_CLASSES
    ]
    assert missing == [], f"stylesheet defines a class app.py never uses: {missing}"


def test_a_withheld_class_is_caught():
    """Mutation: every occurrence of 'wizard-title' is stripped out of
    a copy of app.py's real source. Observed: scanning the mutated
    copy for the literal name, the way
    test_every_wizard_class_reaches_app_py scans the real file, finds
    zero occurrences."""
    source = _APP_PY.read_text(encoding="utf-8").replace("wizard-title", "")
    assert "wizard-title" not in source


_DESIGN_SET = Path(__file__).resolve().parent.parent / "design" / "reconnect-wizard"
_HEX_IN_DESIGN = re.compile(r"#[0-9A-Fa-f]{6}")


def _design_set_colours() -> set:
    """Every six-digit hex the artboards paint, read from the design
    set at test time rather than from a list transcribed into this
    file, so a colour added to an artboard cannot pass unnoticed.
    Matched case-insensitively and compared upper-case."""
    found = set()
    for artboard in sorted(_DESIGN_SET.glob("*.dc.html")):
        found.update(m.upper() for m in _HEX_IN_DESIGN.findall(artboard.read_text(encoding="utf-8")))
    return found


def _theme_colours() -> set:
    return {
        value.upper()
        for name, value in vars(theme).items()
        if name.isupper() and isinstance(value, str) and _HEX_IN_DESIGN.fullmatch(value)
    }


def test_every_design_set_colour_is_named_in_theme():
    """Every colour the design set paints is a constant in theme.py."""
    design = _design_set_colours()
    assert design, "no colours read from the design set - check the glob"
    unnamed = sorted(design - _theme_colours())
    assert unnamed == [], f"design set paints a colour theme.py does not name: {unnamed}"


def test_a_colour_missing_from_theme_is_caught():
    """Mutation: GROUND (#0F1113) is dropped from the set of theme.py
    constants the check compares against, standing in for a colour an
    artboard paints and theme.py never names. Observed: the same
    set-difference test_every_design_set_colour_is_named_in_theme
    computes then reports ['#0F1113'] as unnamed."""
    design = _design_set_colours()
    without_ground = _theme_colours() - {theme.GROUND.upper()}
    unnamed = sorted(design - without_ground)
    assert unnamed == [theme.GROUND.upper()]


_FONT_SIZE_PX = re.compile(r"font(?:-size)?:\s*(?:\d+\s+)?(\d+(?:\.\d+)?px)")


def _design_set_font_sizes() -> set:
    """Every px font-size the artboards specify, read from the design
    set at test time rather than from a list transcribed into this
    file - both a bare font-size: declaration and a size embedded in a
    font: shorthand (theme.py's own TYPE_15/21/30/40 comment notes the
    same shorthand exists), and an inline style="font-size:...px"
    attribute alike, so a type step added to an artboard cannot pass
    unnoticed the way TYPE_17 did."""
    found = set()
    for artboard in sorted(_DESIGN_SET.glob("*.dc.html")):
        found.update(_FONT_SIZE_PX.findall(artboard.read_text(encoding="utf-8")))
    return found


def _theme_font_sizes() -> set:
    return {
        value
        for name, value in vars(theme).items()
        if name.isupper() and isinstance(value, str) and re.fullmatch(r"\d+(\.\d+)?px", value)
    }


def _unnamed_sizes(design: set, theme_sizes: set) -> list:
    """The one place that decides which design-set sizes theme.py
    fails to name; both the real guard and its mutation control call
    this rather than each re-implementing the set difference."""
    return sorted(design - theme_sizes, key=lambda s: float(s[:-2]))


# 10.5px is the one design-set font-size this guard does not require a
# theme.py token for: Specs.dc.html:277 uses it once, inline, to style
# the literal words "build-playlist" inside a "not in Phase 1"
# scope-fence aside - prose about a future, out-of-scope command, not
# a step of this wizard's own type scale. Named here by its exact
# value and reason, not by a rule like "ignore anything under 11px",
# which would silently swallow a real, future token the same way.
_KNOWN_UNNAMED_FONT_SIZES = {"10.5px"}


def test_every_design_set_font_size_is_named_in_theme():
    """Every font-size the design set specifies, except
    _KNOWN_UNNAMED_FONT_SIZES's one documented entry, has a token in
    theme.py - the type-scale equivalent of
    test_every_design_set_colour_is_named_in_theme, whose absence let
    TYPE_17 get deleted along with .wizard-heading-xs without any
    guard catching that a type step the artboards use had gone
    missing."""
    design = _design_set_font_sizes()
    assert design, "no font sizes read from the design set - check the glob"
    unnamed = _unnamed_sizes(design, _theme_font_sizes() | _KNOWN_UNNAMED_FONT_SIZES)
    assert unnamed == [], f"design set specifies a font-size theme.py does not name: {unnamed}"


def test_a_font_size_missing_from_theme_is_caught():
    """Mutation: a synthetic theme-sizes set with 30px removed is
    compared against a synthetic design-sizes set of {12px, 30px} -
    isolated from the real design set, so this stays a controlled
    check of _unnamed_sizes' own arithmetic rather than depending on
    whatever test_every_design_set_font_size_is_named_in_theme finds
    against the real design set at the time this runs. Observed:
    _unnamed_sizes reports ['30px'] as unnamed."""
    design = {"12px", "30px"}
    theme_sizes_without_30 = {"12px"}
    unnamed = _unnamed_sizes(design, theme_sizes_without_30)
    assert unnamed == ["30px"]



_RULE_WITH_COLOUR = re.compile(r"\{([^}]*)\}")
_COLOUR_DECL = re.compile(r"(?<!-)\bcolor:\s*(#[0-9A-Fa-f]{6})")
_BACKGROUND_DECL = re.compile(r"background(?:-color)?:\s*(#[0-9A-Fa-f]{6})")


def _derived_text_pairs() -> list:
    """Every (text, surface) pair the design set actually renders -
    read from each CSS rule that carries BOTH a color: declaration and
    the background it sits on, so the surface is the one that rule
    paints rather than every surface in the palette. Derived at test
    time; nothing here is transcribed."""
    pairs = set()
    for artboard in sorted(_DESIGN_SET.glob("*.dc.html")):
        for body in _RULE_WITH_COLOUR.findall(artboard.read_text(encoding="utf-8")):
            fg = _COLOUR_DECL.search(body)
            bg = _BACKGROUND_DECL.search(body)
            if fg and bg:
                pairs.add((fg.group(1).upper(), bg.group(1).upper()))
    return sorted(pairs)


def test_every_rendered_text_pair_clears_the_contrast_floor():
    """Specs fixes 4.5:1 for secondary text against its own surface
    rather than against the page (Specs.dc.html:270). The pairs are
    derived from the design set, so a grey moved onto a lighter
    surface fails here even though every token is unchanged."""
    pairs = _derived_text_pairs()
    assert pairs, "no colour/background pairs derived - check the parser"
    below = [
        (fg, bg, round(_contrast_ratio(fg, bg), 2))
        for fg, bg in pairs
        if _contrast_ratio(fg, bg) < 4.5
    ]
    assert below == [], f"text pair below Specs' 4.5:1 floor: {below}"


def test_a_text_pair_below_the_floor_is_caught():
    """Mutation: TEXT_SUBTLE_3 is paired with SURFACE_5, the lightest
    surface, then that surface is lightened further to #6E767D -
    lightening a background lowers contrast against light text, where
    darkening it would raise it. Observed: the same _contrast_ratio
    test_every_rendered_text_pair_clears_the_contrast_floor calls
    returns 1.46:1 for the pair, below the 4.5 floor."""
    ratio = _contrast_ratio(theme.TEXT_SUBTLE_3, "#6E767D")
    assert ratio < 4.5


# Quasar ships colour utilities (text-grey-6 and friends) that are class
# selectors at the same 0,1,0 specificity as a .wizard-* rule, so an
# element carrying one of each has its colour decided by <head> source
# order rather than by the token - the same cascade hazard as the
# stacked font sizes above, in the colour dimension. text-grey-6 is
# #757575, which theme.py does not name and which falls under Specs'
# 4.5:1 floor on three of the six surfaces.
# Quasar names its palette semantically as well as by hue, and the
# compound hues have to precede the short ones in the alternation or
# "deep-orange" matches "orange" and the numeric suffix anchor then
# rejects the "deep-" that is left over.
_QUASAR_COLOUR_UTILITY = re.compile(
    r"^text-(?:"
    r"primary|secondary|accent|positive|negative|warning|info|dark|white|black"
    r"|blue-grey|light-blue|light-green|deep-orange|deep-purple"
    r"|grey|red|pink|purple|indigo|blue|cyan|teal|green"
    r"|lime|yellow|amber|orange|brown"
    r")(?:-\d{1,2})?$"
)
_COLOUR_IN_RULE = re.compile(r"(?<!-)\bcolor:\s*#[0-9A-Fa-f]{6}")


def _colour_setting_tokens(call: str) -> list:
    """Every token in one classes() literal that sets a colour - the
    .wizard-* classes whose own rule sets one, plus Quasar's colour
    utilities."""
    sheet = theme.page_stylesheet()
    wizard_colour = {
        name
        for name, body in _CLASS_RULE.findall(sheet)
        if _COLOUR_IN_RULE.search(body)
    }
    return [
        tok
        for tok in call.split()
        if tok in wizard_colour or _QUASAR_COLOUR_UTILITY.match(tok)
    ]


def test_no_classes_call_sets_colour_twice():
    """No element carries both a Quasar colour utility and a
    colour-setting wizard class; where a token governs the colour the
    utility is dropped rather than left to source order."""
    offending = []
    for call in _classes_calls(_APP_PY.read_text(encoding="utf-8")):
        used = _colour_setting_tokens(call)
        if len(used) > 1:
            offending.append((call, used))
    assert offending == [], f"classes() call sets colour twice: {offending}"


def test_two_colour_classes_on_one_call_is_caught():
    """Mutation: a synthetic classes() literal pairs Quasar's
    text-grey-6 with wizard-subtle-3 - one Quasar utility and one
    token class, both class selectors at 0,1,0 so <head> order decides
    which paints. Observed: _colour_setting_tokens, the
    same helper test_no_classes_call_sets_colour_twice routes every
    real call through, returns ['text-grey-6', 'wizard-subtle-3'], so
    the call is reported as setting colour twice."""
    used = _colour_setting_tokens("text-grey-6 wizard-subtle-3 wizard-note")
    assert used == ["text-grey-6", "wizard-subtle-3"]
    assert len(used) > 1


def test_a_semantic_quasar_colour_class_is_caught():
    """Mutation: a synthetic classes() literal pairs Quasar's
    text-negative - a semantic palette name rather than a hue-plus-
    shade one - with wizard-subtle-3. Observed: _colour_setting_tokens,
    the same helper test_no_classes_call_sets_colour_twice routes
    every real call through, returns
    ['text-negative', 'wizard-subtle-3'], so the call is reported as
    setting colour twice. text-grey-6, which the other control plants,
    matches the hue-and-shade half of the pattern and so cannot show
    the semantic half is live."""
    used = _colour_setting_tokens("text-negative wizard-subtle-3 wizard-note")
    assert used == ["text-negative", "wizard-subtle-3"]
    assert len(used) > 1


def test_the_quasar_pattern_reads_compound_hues_whole():
    """Mutation: the compound hue names are matched against the
    pattern that decides whether a token is a Quasar colour utility.
    Observed: text-deep-orange, text-light-blue, text-blue-grey and
    text-deep-purple-4 all match, so the compound-before-short
    ordering holds; were "orange" to precede "deep-orange" the leading
    "deep-" would be left over and the match would fail."""
    for token in ("text-deep-orange", "text-light-blue", "text-blue-grey", "text-deep-purple-4"):
        assert _QUASAR_COLOUR_UTILITY.match(token), token


_STYLESHEET_COLOUR = re.compile(r"(?<!-)\bcolor:\s*(#[0-9A-Fa-f]{6})")


def _stylesheet_text_colours() -> set:
    """Every colour page_stylesheet() emits through a color:
    declaration - i.e. every colour the wizard actually paints text
    in. Selected by role rather than by constant name, so a token
    cannot escape the contrast floor by being named something other
    than TEXT_*."""
    return {m.upper() for m in _STYLESHEET_COLOUR.findall(theme.page_stylesheet())}


_SHEET_RULE = re.compile(r"([^{}]+)\{([^}]*)\}")


def _stylesheet_descendant_pairs() -> list:
    """(text, background) pairs the stylesheet itself establishes one
    level up: a rule like `.wizard-tag-review strong { color: X }`
    paints on the background `.wizard-tag-review { background: Y }`
    sets, so the surface is that tag's tint rather than a ground or
    surface token. Derived from the emitted sheet, not transcribed."""
    sheet = theme.page_stylesheet()
    backgrounds = {}
    for selector, body in _SHEET_RULE.findall(sheet):
        bg = _BACKGROUND_DECL.search(body)
        if bg:
            backgrounds[selector.strip()] = bg.group(1).upper()
    pairs = set()
    for selector, body in _SHEET_RULE.findall(sheet):
        fg = _COLOUR_DECL.search(body)
        if not fg:
            continue
        parts = selector.strip().split()
        if len(parts) > 1 and parts[0] in backgrounds:
            pairs.add((fg.group(1).upper(), backgrounds[parts[0]]))
    return sorted(pairs)


def test_stylesheet_descendant_pairs_clear_the_contrast_floor():
    """Text the stylesheet paints inside a tinted container is held to
    4.5:1 against that container's own background rather than against
    a ground or surface token it never sits on."""
    pairs = _stylesheet_descendant_pairs()
    assert pairs, "no descendant pairs derived - the parser is broken"
    below = [
        (fg, bg, round(_contrast_ratio(fg, bg), 2))
        for fg, bg in pairs
        if _contrast_ratio(fg, bg) < 4.5
    ]
    assert below == [], f"emphasis text below the floor on its own tint: {below}"


def _unpaired_text_tokens() -> list:
    """Colours the wizard paints text in that neither the design set
    nor the stylesheet's own nesting gives a surface for."""
    paired = {fg for fg, _ in _derived_text_pairs()}
    paired |= {fg for fg, _ in _stylesheet_descendant_pairs()}
    return sorted(_stylesheet_text_colours() - paired)


def test_text_tokens_without_a_derived_surface_clear_the_floor():
    """A text token the design set paints only on an inherited
    background has no rule-level surface to derive, so it is held to
    the worst case instead: the lightest of the six ground and surface
    tokens, which is the surface that would fail first."""
    lightest = max(
        (theme.GROUND, theme.SURFACE_1, theme.SURFACE_2,
         theme.SURFACE_3, theme.SURFACE_4, theme.SURFACE_5),
        key=_relative_luminance,
    )
    unpaired = _unpaired_text_tokens()
    assert unpaired, "no unpaired text tokens selected - the selection is broken"
    below = [
        (tok, round(_contrast_ratio(tok, lightest), 2))
        for tok in unpaired
        if _contrast_ratio(tok, lightest) < 4.5
    ]
    assert below == [], f"unpaired text token below the floor on {lightest}: {below}"


_TAG_ACTION_HEIGHT = re.compile(r"\.wizard-tag-action(?:-outline)?\s*\{([^}]*)\}")
_HEIGHT_DECL = re.compile(r"(?<!min-)(?<!-)\bheight:\s*(\S+?);")


def _tag_action_heights() -> dict:
    """Every .wizard-tag-action(-outline) rule's own height:
    declaration, read from the emitted stylesheet rather than
    transcribed - both chip classes carry a real border on top of
    .wizard-control's min-height, so an explicit height: is what
    clamps the box to CONTROL_HEIGHT once that border and the dense
    button's padding would otherwise push it taller (measured 34px on
    the served page before this rule existed)."""
    sheet = theme.page_stylesheet()
    heights = {}
    for selector in ("wizard-tag-action", "wizard-tag-action-outline"):
        match = re.search(rf"\.{selector}\s*\{{([^}}]*)\}}", sheet)
        assert match, f".{selector} rule not found in the stylesheet"
        found = _HEIGHT_DECL.search(match.group(1))
        heights[selector] = found.group(1) if found else None
    return heights


def test_filter_chip_classes_fix_control_height():
    """Both filter-chip classes carry an explicit height: at
    CONTROL_HEIGHT, not merely the inherited min-height: - a border on
    top of dense padding otherwise grows the box past 32px regardless
    of min-height, which only floors a box, never caps one."""
    heights = _tag_action_heights()
    assert heights == {
        "wizard-tag-action": theme.CONTROL_HEIGHT,
        "wizard-tag-action-outline": theme.CONTROL_HEIGHT,
    }


def test_a_missing_chip_height_declaration_is_caught():
    """Mutation: the height: declaration is stripped from a copy of
    the real .wizard-tag-action rule's body, standing in for the
    regression this guard exists to catch. Observed: the same
    _HEIGHT_DECL search test_filter_chip_classes_fix_control_height
    uses finds no match against that stripped body."""
    sheet = theme.page_stylesheet()
    match = re.search(r"\.wizard-tag-action\s*\{([^}]*)\}", sheet)
    stripped_body = match.group(1).replace(f"height: {theme.CONTROL_HEIGHT};", "")
    assert _HEIGHT_DECL.search(stripped_body) is None


def test_control_group_class_fixes_control_gap():
    """.wizard-control-group carries CONTROL_GAP as its gap: -
    app.py groups the Review row's A/R/U buttons under this class
    instead of the row's own wider gap, so the 8px between them comes
    from the same token the row controls' own height does, rather
    than a bare Tailwind utility a future edit could drift from it."""
    sheet = theme.page_stylesheet()
    match = re.search(r"\.wizard-control-group\s*\{([^}]*)\}", sheet)
    assert match, ".wizard-control-group rule not found in the stylesheet"
    found = re.search(r"\bgap:\s*(\S+?);", match.group(1))
    assert found is not None
    assert found.group(1) == theme.CONTROL_GAP


def test_a_missing_control_group_gap_is_caught():
    """Mutation: the gap: declaration is stripped from a copy of the
    real .wizard-control-group rule's body. Observed: the same gap:
    search test_control_group_class_fixes_control_gap uses finds no
    match against that stripped body."""
    sheet = theme.page_stylesheet()
    match = re.search(r"\.wizard-control-group\s*\{([^}]*)\}", sheet)
    stripped_body = match.group(1).replace(f"gap: {theme.CONTROL_GAP};", "")
    assert re.search(r"\bgap:\s*(\S+?);", stripped_body) is None


def test_an_unpaired_token_below_the_floor_is_caught():
    """Mutation: a stand-in stylesheet paints .wizard-inactive in
    #6E767D, a grey under the floor, and the selection runs against
    that sheet instead of the real one. Observed: _unpaired_text_tokens'
    own set-difference then carries '#6E767D', and _contrast_ratio -
    the same function the floor guard calls - returns 3.26:1 for it
    against the lightest surface, below 4.5."""
    lightest = max(
        (theme.GROUND, theme.SURFACE_1, theme.SURFACE_2,
         theme.SURFACE_3, theme.SURFACE_4, theme.SURFACE_5),
        key=_relative_luminance,
    )
    planted = "#6E767D"
    stand_in_sheet = theme.page_stylesheet() + f"\n.wizard-planted {{ color: {planted}; }}\n"
    painted = {m.upper() for m in _STYLESHEET_COLOUR.findall(stand_in_sheet)}
    unpaired = sorted(painted - {fg for fg, _ in _derived_text_pairs()})
    assert planted.upper() in unpaired
    assert _contrast_ratio(planted, lightest) < 4.5


# GUARD - page_stylesheet()'s emitted string is not the same thing as
# the CSS a browser parses from it. A Python "# comment" line emitted
# verbatim into the CSS string is not a CSS comment - "#" opens an ID
# selector - so a real CSS parser reads the comment text as a
# malformed selector and swallows the *next* rule as its own
# declaration block: the rule's exact text is still present in the
# string, and every guard above that greps the string as text (this
# includes test_every_status_and_action_token_reaches_the_stylesheet
# and test_every_wizard_class_reaches_app_py) cannot see that it never
# reached the parsed stylesheet at all. Twelve such "#" lines, three
# swallowed rules (wizard-decision-control, wizard-decision-accept,
# wizard-body-12), were served this way before being converted to
# CSS's own /* ... */ comment syntax.
def _parsed_wizard_selectors(sheet: str) -> set:
    """Every top-level .wizard-* class selector tinycss2 - a real CSS
    parser, not a regex - actually parses as a qualified rule's own
    prelude. A descendant or pseudo-class selector (e.g.
    '.wizard-tag-found strong') is not a bare class selector and is
    excluded, the same restriction _CLASS_RULE's own regex applies."""
    selectors = set()
    for rule in tinycss2.parse_stylesheet(sheet, skip_whitespace=True, skip_comments=True):
        if rule.type != "qualified-rule":
            continue
        prelude = tinycss2.serialize(rule.prelude).strip()
        for selector in prelude.split(","):
            match = re.fullmatch(r"\.(wizard-[\w-]+)", selector.strip())
            if match:
                selectors.add(match.group(1))
    return selectors


def test_stylesheet_parses_with_no_css_errors():
    """page_stylesheet()'s emitted string parses as valid CSS with
    zero errors from tinycss2 - a real parser, not the string-level
    reading every other guard in this file does."""
    sheet = theme.page_stylesheet()
    errors = [r for r in tinycss2.parse_stylesheet(sheet, skip_whitespace=True, skip_comments=True) if r.type == "error"]
    assert errors == [], f"stylesheet failed to parse: {[e.message for e in errors]}"


def test_every_wizard_class_the_text_finds_is_actually_parsed():
    """Every top-level .wizard-* class _stylesheet_classes() finds by
    reading the emitted string is also reachable as tinycss2's own
    parsed selector - the direction no text-only guard in this file
    can check, since a rule can be present in the string and absent
    from the parsed stylesheet, which is exactly what happened to
    wizard-decision-control, wizard-decision-accept and
    wizard-body-12 here."""
    sheet = theme.page_stylesheet()
    text_classes = set(_stylesheet_classes())
    parsed_classes = _parsed_wizard_selectors(sheet)
    missing = sorted(text_classes - parsed_classes)
    assert missing == [], f"class present in the stylesheet text but not parsed as a real rule: {missing}"


def test_a_planted_hash_comment_swallows_the_next_rule():
    """Mutation: a Python-style '# a stray python-style comment' line
    - not CSS syntax - is planted immediately before a copy of the
    real .wizard-dot rule's text, reproducing the exact defect twelve
    such lines caused here. Observed: tinycss2 parses zero
    wizard-dot selectors from the mutated sheet - the "#" line is read
    as a malformed ID selector that swallows the following rule as its
    own declaration block - while the substring '.wizard-dot' is still
    present in the mutated string, the gap a text-only reading could
    never see."""
    sheet = theme.page_stylesheet()
    anchor = ".wizard-dot { background:"
    assert anchor in sheet, "fixture assumption stale: .wizard-dot rule not found"
    mutated = sheet.replace(anchor, "# a stray python-style comment\n" + anchor, 1)
    assert ".wizard-dot" in mutated
    parsed_after = _parsed_wizard_selectors(mutated)
    assert "wizard-dot" not in parsed_after


def _button_focus_ring_layers(sheet: str) -> list:
    """The name of every layer whose block declares an !important
    outline for .q-btn:focus-visible, read with tinycss2 rather than by
    a regex over the emitted text."""
    names = []
    for rule in tinycss2.parse_stylesheet(sheet, skip_whitespace=True, skip_comments=True):
        if rule.type != "at-rule" or rule.lower_at_keyword != "layer":
            continue
        layer = tinycss2.serialize(rule.prelude).strip()
        for inner in tinycss2.parse_rule_list(rule.content, skip_whitespace=True, skip_comments=True):
            if inner.type != "qualified-rule":
                continue
            if ".q-btn:focus-visible" not in tinycss2.serialize(inner.prelude):
                continue
            body = tinycss2.serialize(inner.content)
            if "outline" in body and "!important" in body:
                names.append(layer)
    return names


def test_button_focus_ring_declares_inside_quasars_own_layer():
    """Specs' focus ring is never removed, and Quasar's q-btn carries
    the no-outline class whose outline: 0 !important sits in a layer
    Quasar names quasar_importants and orders last. For an !important
    declaration the earlier layer wins, so the layer name is the whole
    fix: re-opening quasar_importants reaches the control and any other
    name does not.

    This guard reads the emitted stylesheet and cannot see the cascade
    that decides the question - the same blindness that let the
    unlayered *:focus-visible rule read as matches while no button
    painted a ring. The evidence is the served page, measured in
    docs/2026-08-29-w004-focus-ring-record.md, and this pins the one
    value that measurement turned on.

    Mutation control: renaming the layer to a name declared after
    Quasar's own - the case measured as losing on the served page -
    makes _button_focus_ring_layers return ['wizard_overrides'] against
    the ['quasar_importants'] asserted here, so the first assertion
    fails. Dropping the layer wrapper entirely returns [].

    Observed on the module as it stands: ['quasar_importants']."""
    sheet = theme.page_stylesheet()
    assert _button_focus_ring_layers(sheet) == ["quasar_importants"]
    renamed = sheet.replace("@layer quasar_importants", "@layer wizard_overrides")
    assert _button_focus_ring_layers(renamed) == ["wizard_overrides"]

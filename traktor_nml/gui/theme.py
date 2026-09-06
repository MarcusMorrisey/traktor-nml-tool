"""Specs' measured token set: traktor_nml/gui/app.py's colour, type,
spacing and radius values, held once so a hex or a pixel size is never
repeated at a call site (DL-078). Imports no nicegui, so the pytest
interpreter reads it directly (DL-078, DL-085).

The shell the pages compose against measures here too: the two band
heights and the spacing steps the header band, the middle region, the
footer band and the card triplet are drawn at. This module is the one a
guard under the system interpreter can read, so a dimension written at
an app.py call site would be invisible to every guard and to the hex-
and size-scanning sweeps in tests/test_gui_theme.py; app.py names class
strings and this module holds the values behind them (DL-069, DL-188).
"""

from __future__ import annotations

# Ground and surfaces (Specs.dc.html body/.hd/.sec/.sec-h backgrounds).
GROUND = "#0F1113"
SURFACE_1 = "#14171A"
SURFACE_2 = "#17191C"
SURFACE_3 = "#1F2225"
SURFACE_4 = "#22262A"
SURFACE_5 = "#23272B"

# Borders (Specs.dc.html .sec/.hd and .kbd/.kr borders).
BORDER = "#2A2E32"
BORDER_STRONG = "#3C4248"

# Text.
TEXT = "#E8EBED"
TEXT_MUTED = "#A5ADB4"
TEXT_FAINT = "#8E979E"

# Six further secondary text greys the design set paints beyond the two
# Specs names; two of them, TEXT_SUBTLE_1 and TEXT_SUBTLE_5, are also
# painted by Specs.dc.html itself (DL-088).
TEXT_SUBTLE_1 = "#97A0A7"
TEXT_SUBTLE_2 = "#9BA4AB"
TEXT_SUBTLE_3 = "#8A9299"
TEXT_SUBTLE_4 = "#C2C9CE"
TEXT_SUBTLE_5 = "#D2D8DC"
TEXT_SUBTLE_6 = "#BEC5CA"

# The switch-knob grey: painted only as the background of .sw i at
# Main.dc.html:55, never as text, so it carries no contrast-floor
# obligation against a 4.5:1 text ratio - only the 3:1 non-text floor
# against its track colour (SWITCH_TRACK below).
SWITCH_KNOB = "#7E868D"
SWITCH_TRACK = "#2E3338"

# Status hues: the three review statuses (ambiguous, refuted, format)
# share STATUS_NEEDS_REVIEW on purpose - a distinct icon silhouette and
# the written word tell them apart, not a fourth colour
# (Specs.dc.html, "Status - what the row wants from you").
STATUS_FOUND = "#4FD3BA"
STATUS_NEEDS_REVIEW = "#F5D96B"
STATUS_NOT_FOUND = "#E07A4C"
ACTION = "#56B4E9"

# Status emphasis variants (icon/heading weight) and their tinted
# surfaces and borders, named for the role each carries.
STATUS_FOUND_STRONG = "#22C4A8"
STATUS_FOUND_TINT_BG = "#12211D"
STATUS_FOUND_TINT_BORDER = "#2C5449"
STATUS_FOUND_TINT_TEXT = "#A8D8CE"
STATUS_NEEDS_REVIEW_STRONG = "#5A4E2A"
STATUS_NEEDS_REVIEW_TINT_BG = "#1F1D14"
STATUS_NEEDS_REVIEW_TINT_BG_ALT = "#1E1B12"
STATUS_NOT_FOUND_STRONG = "#6A3F2C"
STATUS_NOT_FOUND_TINT_BG = "#21160F"
STATUS_NOT_FOUND_TINT_TEXT = "#E8956E"
ACTION_STRONG = "#7FC4E8"
ACTION_TINT_BG = "#12181C"
ACTION_TINT_BG_ALT = "#16242C"
ACTION_TINT_BORDER = "#1B3D4E"
ACTION_TINT_BORDER_ALT = "#2F5A72"
ACTION_TINT_TEXT = "#8FCFF2"
ACTION_TINT_TEXT_ALT = "#9BD4F5"

# Further border greys, named for the surface pair each separates.
BORDER_SUBTLE_1 = "#131619"
BORDER_SUBTLE_2 = "#141C21"
BORDER_SUBTLE_3 = "#15171A"
BORDER_SUBTLE_4 = "#22292E"
BORDER_SUBTLE_5 = "#253038"
BORDER_SUBTLE_6 = "#262A2E"
BORDER_SUBTLE_7 = "#454C52"
BORDER_SUBTLE_8 = "#0D0F11"
BORDER_SUBTLE_9 = "#12222B"

# Neutral inactive marker: Specs.dc.html's own .dot and the inactive
# progress-bar/radio-outline grey (Specs.dc.html:49; Cancelling.dc.html:54;
# Outcomes.dc.html:76; Review.dc.html:79).
NEUTRAL_INACTIVE = "#5A6167"

# Type scale (Specs.dc.html body/.lbl/.tok .g/.sec-t/.task and the
# nine artboards' font-size and font-shorthand declarations). No step
# below 11px; the 9 and 10px values in the artboards are gap and
# padding, and belong to the spacing steps below.
TYPE_11 = "11px"
TYPE_11_5 = "11.5px"
TYPE_12 = "12px"
TYPE_12_5 = "12.5px"
TYPE_13 = "13px"
TYPE_13_5 = "13.5px"
TYPE_14 = "14px"
TYPE_14_5 = "14.5px"
# TYPE_15, TYPE_21, TYPE_30 and TYPE_40 back the four sizes the
# artboards carry only inside a font: shorthand rather than a
# font-size declaration (Confirm.dc.html:53; Scanning.dc.html:48,:54;
# Results.dc.html:47), so a font-size-only search misses them.
TYPE_15 = "15px"
TYPE_16 = "16px"
TYPE_17 = "17px"
TYPE_21 = "21px"
TYPE_23 = "23px"
TYPE_30 = "30px"
TYPE_40 = "40px"

# Spacing steps and radii (Specs.dc.html .sec-b/.kr/.tok gaps and
# .kbd/.pill/.warn/.sec radii).
SPACE_1 = "1px"
SPACE_2 = "2px"
SPACE_4 = "4px"
SPACE_8 = "8px"
SPACE_9 = "9px"
SPACE_10 = "10px"
# Review.dc.html:35's .btn.sm padding (0 12px) - the row decision
# controls' own padding, distinct from CONTROL_GAP's 8px between them.
SPACE_12 = "12px"
# Scanning.dc.html:53's .tile own padding (11px 12px) and internal gap
# (5px, between its value and its key).
SPACE_5 = "5px"
SPACE_11 = "11px"
# Main.dc.html:22's .st vertical padding (6px 12px), :19's .bar
# height, and :16's .hd horizontal padding (0 24px) - the three
# spacing steps the header row, its divider and its tabs measure at.
SPACE_6 = "6px"
SPACE_16 = "16px"
SPACE_24 = "24px"
# The steps below carry no meaning of their own beyond the artboard
# line each comment names: a step is a measured value, and the rule that
# spends it says which region it insets (DL-188).
#
# Main.dc.html:27's main padding (22px 24px 6px) and its 20px grid gap -
# the page region's own inset and the gap between the boxes it holds.
SPACE_22 = "22px"
SPACE_20 = "20px"
# Main.dc.html:33's .card-h padding (11px 15px) and :35's .card-b
# padding (15px) - the inset both card regions measure at.
SPACE_15 = "15px"
# The width the page's content occupies. One value because the header
# band and the content column below it are one column: the band's ground
# and rule end where the card's edge is, so the brand mark sits over the
# card's own first column rather than over the page margin.
CONTENT_WIDTH = "64rem"
# Main.dc.html:15's .app grid-template-rows (56px 1fr 64px), the same
# three rows Confirm.dc.html, Results.dc.html and Review.dc.html draw.
# The bands are fixed and the middle row takes what is left, which is
# what makes the middle the scroll owner rather than the document.
HEADER_BAND_HEIGHT = "56px"
FOOTER_BAND_HEIGHT = "64px"
RADIUS_SM = "4px"
RADIUS_MD = "5px"
RADIUS_LG = "6px"
RADIUS_XL = "8px"
# Scanning.dc.html:53's .tile own border-radius.
RADIUS_7 = "7px"

FONT_SANS = "'IBM Plex Sans', system-ui, -apple-system, sans-serif"
FONT_MONO = "'IBM Plex Mono', ui-monospace, Consolas, monospace"

# The route app.py mounts the vendored directory at, held here because
# an @font-face src and the route that answers it are one fact; app.py
# reads this constant rather than repeating the path (DL-164).
FONT_URL_BASE = "/fonts"

# The seven faces design/reconnect-wizard/Main.dc.html line 11 imports:
# IBM Plex Sans 400/500/600/700 and IBM Plex Mono 400/500/600. Each
# entry is (family, weight, file name), and page_stylesheet() emits one
# @font-face per entry, so a weight dropped here is a weight the page
# stops carrying rather than a rule that silently names a missing file.
# No italic: no artboard sets one.
FONT_FACES = (
    ("IBM Plex Sans", 400, "IBMPlexSans-Regular.woff2"),
    ("IBM Plex Sans", 500, "IBMPlexSans-Medium.woff2"),
    ("IBM Plex Sans", 600, "IBMPlexSans-SemiBold.woff2"),
    ("IBM Plex Sans", 700, "IBMPlexSans-Bold.woff2"),
    ("IBM Plex Mono", 400, "IBMPlexMono-Regular.woff2"),
    ("IBM Plex Mono", 500, "IBMPlexMono-Medium.woff2"),
    ("IBM Plex Mono", 600, "IBMPlexMono-SemiBold.woff2"),
)


def font_face_rules() -> str:
    """One @font-face block per FONT_FACES entry.

    woff2 alone: the only client is the WebView2 or WebKit engine
    pywebview embeds under ui.run(native=True), and both have carried
    woff2 since long before any version this project installs (DL-175).

    font-display: block rather than swap. A swap paints the fallback
    first and reflows when the face arrives; the faces are served from
    the application's own process over the loopback interface, so the
    wait is not a wait, and a first paint in Segoe UI is the exact
    appearance this work exists to remove.
    """
    return "\n".join(
        f"@font-face {{ font-family: '{family}'; font-style: normal; "
        f"font-weight: {weight}; font-display: block; "
        f"src: url('{FONT_URL_BASE}/{file_name}') format('woff2'); }}"
        for family, weight, file_name in FONT_FACES
    )


# Specs' focus ring: 2px solid on the light foreground, 2px offset, on
# every focusable control, never removed and never colour-only - it
# changes the outline rather than the fill (Specs.dc.html,
# "Accessibility rules"; DL-078).
FOCUS_RING = f"2px solid {TEXT}"
FOCUS_RING_OFFSET = "2px"

# Specs' 32px control height with 8px separation, carried up to the
# rung the framework reaches per DL-086.
# .wizard-control (below) carries CONTROL_HEIGHT and CONTROL_GAP onto
# the dense table buttons; where Quasar's own q-btn min-height wins
# instead, the rung-two override and any surviving framework shortfall
# are recorded under Framework shortfalls in traktor_nml/README.md (DL-087).
# .wizard-control also carries white-space: nowrap - no .btn/.btn-pri
# rule in the design set (Results.dc.html:39-40; Confirm.dc.html's own
# copy of the same rule) sets an explicit width for a control, relying
# instead on inline-flex's own shrink-to-fit sizing to keep a label on
# one line; min-height alone cannot recover a label Quasar's own
# flex-wrap: wrap on .q-btn__content has already wrapped onto a second
# line once some narrower width forces it (measured 56.03px on a
# two-word label against Specs' 32px), so this stops the wrap itself
# instead.
CONTROL_HEIGHT = "32px"
CONTROL_GAP = SPACE_8


def page_stylesheet() -> str:
    """The wizard's stylesheet as one string, every colour and size
    drawn from this module's own constants rather than a literal
    (DL-078).

    The order of the sheet is load-bearing at two points. The
    @font-face blocks font_face_rules() returns stand at the head,
    unlayered and above the body rule that names the family, which is
    the offset relationship
    tests/test_gui_font_faces.py::test_the_face_blocks_precede_the_body_rule_that_names_the_family
    holds; the shell, band, footer and card rules are emitted after that
    rule and outside the layer block that follows it. The sheet itself
    reaches the head through add_head_html, after nicegui's own sheet,
    so a band rule restating a declaration nicegui.css sets on the same
    element wins at equal specificity (DL-192).
    """
    return f"""
{font_face_rules()}
/* The body rule names FONT_SANS and the blocks above it load that
   family, so the two cannot drift apart: both read the same constants.
   Emitted unlayered, which places them after Quasar's own layered
   Roboto default in the cascade - DL-086's ladder, rung two - so the
   page paints Plex rather than Roboto (DL-173). */
body {{ background: {GROUND}; color: {TEXT}; font: 400 {TYPE_14}/1.45 {FONT_SANS}; }}
.q-page {{ background: {GROUND}; color: {TEXT}; }}
/* Main.dc.html:32-35's .card, .card-h, .card-t and .card-b: a bordered
   box with its own header band, its title, and a padded body. Every
   section a page composes itself carries the triplet, which leaves the
   single-box rule the triplet replaces without a call site, and a rule
   no call site names fails test_every_wizard_class_reaches_app_py
   (DL-196). A step's own header band is Quasar's QStepper markup and is
   not one of those sections: the four ui.step call sites carry
   .wizard-section-head, .wizard-header, .wizard-hd-alt and
   .wizard-sec-alt, and those rules stand in this sheet beside the
   triplet. No card rule declares a width: .wizard-content-width stays
   the one width owner. */
/* The four rules are one structure: a box that carries the ground, the
   border and the radius, a head that carries the inset and the rule
   below it, a title inside that head, and a body that carries its own
   inset and the gap between the controls it holds. What the QStepper
   markup refuses of the triplet is named in the served-page record by
   the computed value that shows the refusal, and stands as a narrowed
   entry under "Composition not built" in traktor_nml/README.md
   (DL-186, DL-194). What the browser computes for these four rules is
   read on a served page for the same reason: a guard reading these
   declarations is true whether or not the layout landed (DL-189). */
.wizard-card {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: {RADIUS_XL}; }}
.wizard-card-head {{ display: flex; align-items: center; justify-content: space-between; gap: {SPACE_12}; padding: {SPACE_11} {SPACE_15}; border-bottom: 1px solid {BORDER}; }}
.wizard-card-title {{ font-weight: 600; font-size: {TYPE_13}; margin: 0; }}
.wizard-card-body {{ padding: {SPACE_15}; display: flex; flex-direction: column; gap: {SPACE_12}; }}
.wizard-header {{ background: {SURFACE_2}; border-bottom: 1px solid {BORDER}; font-size: {TYPE_14}; }}
.wizard-section-head {{ background: {SURFACE_3}; border-bottom: 1px solid {BORDER}; font-size: {TYPE_12}; font-weight: 600; }}
.wizard-label {{ font: 600 {TYPE_11}/1 {FONT_MONO}; letter-spacing: .1em; text-transform: uppercase; color: {TEXT_FAINT}; }}
.wizard-mono {{ font-family: {FONT_MONO}; }}
.wizard-dim {{ color: {TEXT_MUTED}; }}
.wizard-faint {{ color: {TEXT_FAINT}; }}
.wizard-status-found {{ color: {STATUS_FOUND}; }}
.wizard-status-review {{ color: {STATUS_NEEDS_REVIEW}; }}
.wizard-status-missing {{ color: {STATUS_NOT_FOUND}; }}
.wizard-action {{ color: {ACTION}; }}
.wizard-kbd {{ font: 500 {TYPE_11}/1 {FONT_MONO}; background: {SURFACE_4}; border: 1px solid {BORDER_STRONG}; border-bottom-width: 2px; border-radius: {RADIUS_SM}; padding: 3px 5px; color: {TEXT}; }}
.wizard-control {{ min-height: {CONTROL_HEIGHT}; margin-bottom: {CONTROL_GAP}; white-space: nowrap; }}
.wizard-control-group {{ display: flex; align-items: center; gap: {CONTROL_GAP}; }}
/* Review.dc.html:35's .btn.sm padding (0 12px), distinct from
   .wizard-control's own height/nowrap-only rule so the two compose
   rather than one absorbing the other's job. */
.wizard-decision-control {{ padding: 0 {SPACE_12}; }}
/* Review.dc.html:36's .btn-pri: the action blue carrying the ground as
   its ink, at weight 600 and TYPE_13. Quasar's color="primary" paints
   bg-primary and text-white, both !important in the layer Quasar orders
   last, so the ink reaches the label only when the constructor passes
   color=None and this class carries the background too - DL-086's rung
   one, with every rung measured in
   docs/2026-08-29-w004-focus-ring-record.md. Every value is an existing
   constant; this is a new combination of them. */
.wizard-control-primary {{ background: {ACTION}; color: {GROUND}; font-weight: 600; font-size: {TYPE_13}; }}
*:focus-visible {{ outline: {FOCUS_RING}; outline-offset: {FOCUS_RING_OFFSET}; }}
/* Quasar's q-btn carries the no-outline class, whose outline: 0
   !important is declared inside a layer Quasar names quasar_importants
   and orders last. For an !important declaration the earlier layer wins,
   so an unlayered rule loses at every specificity and so does one in a
   layer declared after it; a declaration re-opening Quasar's own layer
   reaches the control. All four were measured on the served page
   (docs/2026-08-29-w004-focus-ring-record.md). Specs' focus ring is
   never removed, so this is where DL-086's rung two lands for it. */
@layer quasar_importants {{
  .q-btn:focus-visible {{ outline: {FOCUS_RING} !important; outline-offset: {FOCUS_RING_OFFSET} !important; }}
}}
@media (prefers-reduced-motion: reduce) {{
  .q-spinner, .q-linear-progress__model {{ animation: none !important; }}
}}
.wizard-row {{ border-bottom: 1px solid {BORDER_SUBTLE_6}; }}
.wizard-row:nth-child(odd) {{ background: {SURFACE_1}; }}
.wizard-row:nth-child(even) {{ background: {SURFACE_5}; }}
.wizard-row-focused {{ outline: {FOCUS_RING}; outline-offset: {FOCUS_RING_OFFSET}; background: {BORDER_SUBTLE_5}; border-color: {BORDER_SUBTLE_7}; }}
/* Main.dc.html:16's .hd - the header's own row: the SURFACE_2 ground,
   the BORDER bottom rule and the 24px horizontal padding it carries. */
.wizard-header-bar {{ display: flex; align-items: center; gap: {SPACE_12}; background: {SURFACE_2}; border-bottom: 1px solid {BORDER}; }}
/* The one rule that sets the page's column: the header band and every
   content column carry it, so neither can be widened without the other. */
.wizard-content-width {{ width: 100%; max-width: {CONTENT_WIDTH}; margin-left: auto; margin-right: auto; }}
/* Main.dc.html:18's .brand: the mono face at TYPE_11_5 in TEXT_FAINT
   at the letter spacing it carries. */
.wizard-brand {{ font: 500 {TYPE_11_5}/1 {FONT_MONO}; color: {TEXT_FAINT}; letter-spacing: .05em; white-space: nowrap; }}
/* Main.dc.html:19's .bar: a one pixel BORDER_STRONG rule at its height. */
.wizard-header-divider {{ width: {SPACE_1}; height: {SPACE_16}; background: {BORDER_STRONG}; flex: none; }}
/* Main.dc.html:22's .st: TEXT_FAINT ink at TYPE_12_5 with its padding
   and radius and no background of its own, so an unselected tab reads
   on the header row's own ground. */
.wizard-tab {{ display: flex; align-items: center; padding: {SPACE_6} {SPACE_12}; border-radius: {RADIUS_LG}; font-size: {TYPE_12_5}; color: {TEXT_FAINT}; text-decoration: none; white-space: nowrap; }}
/* Main.dc.html:25's .st.now: the SURFACE_4 ground, the inset one pixel
   BORDER_STRONG border, TEXT ink and weight 600. It carries ground,
   border, ink and weight together because nothing else separates the
   two tab states, and it is declared after .wizard-tab so the ink of
   the selected tab wins at equal specificity. */
.wizard-tab-selected {{ background: {SURFACE_4}; color: {TEXT}; box-shadow: inset 0 0 0 {SPACE_1} {BORDER_STRONG}; font-weight: 600; }}
.wizard-title {{ font-size: {TYPE_21}; font-weight: 700; margin-bottom: {SPACE_8}; }}
.wizard-subtle-1 {{ color: {TEXT_SUBTLE_1}; }}
.wizard-subtle-2 {{ color: {TEXT_SUBTLE_2}; }}
.wizard-subtle-3 {{ color: {TEXT_SUBTLE_3}; }}
.wizard-subtle-4 {{ color: {TEXT_SUBTLE_4}; }}
.wizard-subtle-5 {{ color: {TEXT_SUBTLE_5}; }}
.wizard-subtle-6 {{ color: {TEXT_SUBTLE_6}; }}
.wizard-inactive {{ color: {TEXT_FAINT}; }}
.wizard-dot {{ background: {NEUTRAL_INACTIVE}; }}
.wizard-tag-found {{ background: {STATUS_FOUND_TINT_BG}; border: 1px solid {STATUS_FOUND_TINT_BORDER}; color: {STATUS_FOUND_TINT_TEXT}; }}
.wizard-tag-found strong {{ color: {STATUS_FOUND_STRONG}; }}
/* Review.dc.html:37's .btn-ok: the same background and border tokens
   as wizard-tag-found's own tinted surface, but its text carries
   STATUS_FOUND directly rather than STATUS_FOUND_TINT_TEXT - a button
   reads at the brighter status hue Review.dc.html fixes for it, not
   the softer tag-chip text weight wizard-tag-found's own text colour
   is tuned for. Every value here is an existing constant; this is a
   new combination of them, not a new one. */
.wizard-decision-accept {{ background: {STATUS_FOUND_TINT_BG}; border: 1px solid {STATUS_FOUND_TINT_BORDER}; color: {STATUS_FOUND}; }}
.wizard-tag-review {{ background: {STATUS_NEEDS_REVIEW_TINT_BG}; border: 1px solid {STATUS_NEEDS_REVIEW_STRONG}; }}
.wizard-tag-review.alt {{ background: {STATUS_NEEDS_REVIEW_TINT_BG_ALT}; }}
.wizard-tag-review strong {{ color: {STATUS_NEEDS_REVIEW}; }}
.wizard-tag-missing {{ background: {STATUS_NOT_FOUND_TINT_BG}; border: 1px solid {STATUS_NOT_FOUND_STRONG}; color: {STATUS_NOT_FOUND_TINT_TEXT}; }}
.wizard-tag-missing strong {{ color: {STATUS_NOT_FOUND}; }}
.wizard-tag-action {{ background: {ACTION_TINT_BG}; border: 1px solid {ACTION_TINT_BORDER}; color: {ACTION_TINT_TEXT}; box-sizing: border-box; height: {CONTROL_HEIGHT}; }}
.wizard-tag-action.alt {{ background: {ACTION_TINT_BG_ALT}; border-color: {ACTION_TINT_BORDER_ALT}; color: {ACTION_TINT_TEXT_ALT}; }}
.wizard-tag-action strong {{ color: {ACTION_STRONG}; }}
.wizard-panel {{ background: {SURFACE_4}; border: 1px solid {BORDER_SUBTLE_4}; border-radius: {RADIUS_MD}; padding: {SPACE_9} {SPACE_10}; }}
/* Scanning.dc.html:52's .tiles: a three-column grid, 10px apart
   (SPACE_10, already this module's own token). */
.wizard-tiles {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: {SPACE_10}; }}
/* Scanning.dc.html:53's .tile: SURFACE_1 and BORDER already name
   this exact background and border - #14171A and #2A2E32 - for
   other surfaces in this module; this is a new combination of
   them, not a new colour. */
.wizard-tile {{ border: 1px solid {BORDER}; border-radius: {RADIUS_7}; background: {SURFACE_1}; padding: {SPACE_11} {SPACE_12}; display: flex; flex-direction: column; gap: {SPACE_5}; }}
.wizard-note {{ font-size: {TYPE_12_5}; padding: {SPACE_2} {SPACE_4}; border-left: {SPACE_1} solid {BORDER_SUBTLE_1}; }}
.wizard-hd-alt {{ border-bottom: 1px solid {BORDER_SUBTLE_2}; }}
.wizard-sec-alt {{ border: 1px solid {BORDER_SUBTLE_3}; border-radius: {RADIUS_LG}; }}
.wizard-hairline {{ border-top: 1px solid {BORDER_SUBTLE_8}; }}
.wizard-tag-action-outline {{ border: 1px solid {BORDER_SUBTLE_9}; box-sizing: border-box; height: {CONTROL_HEIGHT}; }}
.wizard-heading-lg {{ font-size: {TYPE_23}; }}
.wizard-display {{ font-size: {TYPE_30}; }}
.wizard-display-xl {{ font-size: {TYPE_40}; }}
.wizard-heading-sm {{ font-size: {TYPE_16}; }}
.wizard-heading-xs {{ font-size: {TYPE_17}; }}
.wizard-body-11 {{ font-size: {TYPE_11}; }}
/* Review.dc.html:35's .btn.sm font-size - the row decision controls'
   own type, distinct from wizard-body-12-5 which nothing here uses. */
.wizard-body-12 {{ font-size: {TYPE_12}; }}
.wizard-body-11-5 {{ font-size: {TYPE_11_5}; }}
.wizard-body-12-5 {{ font-size: {TYPE_12_5}; }}
.wizard-body-13 {{ font-size: {TYPE_13}; }}
.wizard-body-13-5 {{ font-size: {TYPE_13_5}; }}
.wizard-body-14-5 {{ font-size: {TYPE_14_5}; }}
.wizard-body-15 {{ font-size: {TYPE_15}; }}
.q-toggle__thumb {{ background: {SWITCH_KNOB}; }}
.q-toggle__track {{ background: {SWITCH_TRACK}; }}
.body--dark, .body--dark .q-stepper, .body--dark .q-field__native, .body--dark .q-field__control {{ color: {TEXT}; }}
/* Main.dc.html:15's .app: a header band, a middle that takes what is
   left, and a footer band, at the viewport's height.

   nicegui's client.py:110-113 builds q-layout > q-page-container >
   q-page > div.nicegui-content, and Quasar's own sheet gives that chain
   no height at all: .q-layout carries width and outline, .q-page only
   position, and q-page-container is not styled by it, so every element
   between the viewport and the middle needs a bounded height before the
   middle can scroll rather than grow. QLayout writes
   the two band heights onto q-page-container as inline padding, which
   border-box turns into exactly the space the middle is left with. The
   four selectors are Quasar's and nicegui's own: app.py constructs none
   of these elements, and a wizard- class no call site names fails
   tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py
   (DL-193). */
.q-layout {{ height: 100vh; }}
.q-page-container {{ box-sizing: border-box; height: 100vh; overflow: hidden; }}
.q-page {{ height: 100%; }}
.nicegui-content {{ height: 100%; min-height: 0; padding: 0; gap: 0; }}
/* Main.dc.html:27's main: the page region's own 22px 24px 6px inset and
   its 20px gap, owning the scroll its parents have bounded.

   The parent is .nicegui-content, which nicegui.css lines 14-28 give
   align-items: flex-start; a flex child under that shrinks to its
   content instead of filling the cross axis, so the middle would take
   its content's width and the centred column would centre inside that
   shrunken box rather than inside the page. align-self: stretch
   counters that one framework default. It is the cross-axis
   declaration rather than a width because .wizard-content-width stays
   the sheet's one width owner (DL-193). */
.wizard-middle {{ align-self: stretch; flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: {SPACE_22} {SPACE_24} {SPACE_6}; gap: {SPACE_20}; display: flex; flex-direction: column; }}
/* nicegui.css lines 14-28 set align-items: flex-start, gap: 1rem and
   padding: 1rem on .nicegui-header and .nicegui-footer, and lines 41-46
   set both to flex-direction: row. Each band therefore restates the
   gap and the padding, and takes the row direction the framework
   already gives it. The wizard sheet reaches the head after the
   framework sheet, so the restatement wins at equal specificity
   (DL-192). Main.dc.html:16's .hd and :29's .ft carry the SURFACE_2
   ground and a one pixel rule on the edge each faces the middle
   across. */
.wizard-header-band {{ align-items: center; justify-content: space-between; gap: {SPACE_24}; padding: 0 {SPACE_24}; height: {HEADER_BAND_HEIGHT}; background: {SURFACE_2}; border-bottom: 1px solid {BORDER}; }}
.wizard-footer-band {{ align-items: center; justify-content: space-between; gap: {SPACE_24}; padding: 0 {SPACE_24}; height: {FOOTER_BAND_HEIGHT}; background: {SURFACE_2}; border-top: 1px solid {BORDER}; }}
/* Main.dc.html:30's .ft-note and :31's .ft-act. */
.wizard-footer-note {{ margin: 0; font-size: {TYPE_12_5}; color: {TEXT_MUTED}; display: flex; align-items: center; gap: {SPACE_9}; }}
.wizard-footer-actions {{ display: flex; align-items: center; gap: {SPACE_10}; flex: none; }}
"""

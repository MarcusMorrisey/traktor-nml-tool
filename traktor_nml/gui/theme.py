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

# Resolve.dc.html's own spacing steps, each named for the line that
# states it: :53's .split gap (16px is SPACE_16 already), :55's .gr cell
# padding, :57's .th cell padding, the .cand row gap, and the
# .det-h/.det-b/.det-f insets. A step is a measured value and the rule
# that spends it says which region it insets (DL-188).
SPACE_3 = "3px"
SPACE_7 = "7px"
SPACE_13 = "13px"
SPACE_14 = "14px"
# Resolve.dc.html:53's .split - the content column beside the detail
# rail, the rail at the width Review.dc.html's own .det carries.
DETAIL_RAIL_WIDTH = "400px"
# Resolve.dc.html:55's .gr grid-template-columns, held as one string
# because the five tracks are one measurement: a column widened alone
# moves every column beside it, and the header row and the body rows
# read the identical string so a cell cannot align in one and not the
# other. The four fixed tracks are sized against the width the table
# resolves to inside .wizard-content-width beside the rail, not against
# the width the artboard's full-bleed main gives it (DL-213).
CONFLICT_GRID_TRACKS = "minmax(0, 1fr) 108px 72px 164px 120px"
# Reconstruct.dc.html:44's .field height - the box a chosen path stands
# in, taller than a control so the path inside it is not crowded by its
# own border.
FIELD_HEIGHT = "36px"
# Reconstruct.dc.html:19's .bar height, as the meta line spends it: the
# upright rule between two phrases about one file.
META_DIVIDER_HEIGHT = "16px"
# Reconstruct.dc.html:67's .steps .n - the numbered circle beside one of
# the steps the set-up card lists, a step smaller than the rail's own
# marker because it is read inside a paragraph rather than as a control.
NEXT_STEP_MARKER_SIZE = "20px"
# Resolve.dc.html:23's .st .num - the step rail's own numbered marker,
# a circle at this size holding the step number or its check mark.
STEP_MARKER_SIZE = "19px"
# Resolve.dc.html:83-85's .rad and the dot it carries when chosen. The
# dot is an element the page renders only for the chosen answer rather
# than a ::after on the marker, so what carries the chosen state is a
# class string a guard can read at the call site (DL-189).
ANSWER_MARKER_SIZE = "15px"
ANSWER_MARKER_DOT_SIZE = "8px"
# Resolve.dc.html:83's .rad carries a 1.5px border, thicker than the 1px
# every other outline on the page takes, so the unchosen marker reads as
# a control rather than as a hairline. Its own constant because it is the
# one border width on this screen that is not 1px.
ANSWER_MARKER_BORDER = "1.5px"
# Every dimension the field rows draw with stands here, the one source
# this package allows for a size or colour literal (ref: DL-069,
# DL-078), and each is read off the artboard the screen is built to
# (ref: DL-071).
#
# Resolve.dc.html:92's .cmpf .k - the key's own metrics. IBM Plex Mono
# advances every glyph 600 units of its 1000-unit em, and the key adds
# .05em of letter-spacing after each glyph, the last one included, so
# one key character costs 0.65em: 7.15px at TYPE_11. The advance is a
# number rather than a CSS string because it is a property of the face
# the sheet never emits, read only to size ANSWER_FIELD_KEY_TRACK.
ANSWER_FIELD_KEY_ADVANCE_EM = 0.6
ANSWER_FIELD_KEY_TRACKING = "0.05em"
# Resolve.dc.html:90's .cmpf - the field row's three tracks: the
# attribute name, the value, and the raw string the file carries. The
# key track is fixed so every answer's keys align down the rail; the
# value takes what is left; the raw track is fixed so the strings the
# operator compares stand at one edge.
#
# The key track is derived, not picked: it holds the longest label in
# answer_detail.LABELS whole, with its difference mark beside it. That
# label is PLAYTIME_FLOAT, 14 characters at 7.15px = 100.1px, plus
# ANSWER_FIELD_MARK_SIZE (5px) and the key's SPACE_5 gap (5px) = 110.1px,
# rounded up to the whole pixel: 111px. A key is never truncated and the
# labels are the NML attribute names (ref: DL-254), so the track grows to
# the label rather than the label shrinking to the track; the value
# track gives up the 51px (ref: DL-298).
ANSWER_FIELD_KEY_TRACK = "111px"
ANSWER_FIELD_RAW_TRACK = "82px"
# Resolve.dc.html:101's .cmpf .d - the mark on a row whose value differs
# across the answers. Smaller than ANSWER_MARKER_DOT_SIZE, which is the
# chosen marker's dot: the two dots mean different things and are not
# one size.
ANSWER_FIELD_MARK_SIZE = "5px"


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
/* text-transform: none sets every button's label in the case it is
   written in, as the artboards draw it: Quasar's q-btn uppercases its
   label from inside a layer, so this unlayered rule is the one that
   paints (DL-273). */
.wizard-control {{ min-height: {CONTROL_HEIGHT}; margin-bottom: {CONTROL_GAP}; white-space: nowrap; text-transform: none; }}
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
/* The artboards' .btn, which every neutral button carries: the same
   action blue and ground ink as the primary, at .btn's weight of 500.
   The primary is set apart from it by weight alone, 600 against 500;
   colour does not separate the two. The artboard's border is the blue
   itself and cannot be seen against the fill, and a 1px border here
   measured the control 34px tall on the served page against Specs'
   32px, so the rule carries none. No font-size here, because the row
   controls carry wizard-body-12 and a size in this rule would set
   theirs twice (DL-273). */
.wizard-control-fill {{ background: {ACTION}; color: {GROUND}; font-weight: 500; }}
/* The artboards' .btn.off. Quasar marks a disabled q-btn with the
   disabled class, and two classes outrank the one the fill or the
   primary rule is selected by, so a disabled blue button is drawn in
   the off colours rather than as a paler blue. The off border is drawn
   as an inset shadow, as .wizard-tab-selected draws its own, so it
   adds nothing to the control's 32px height (DL-273). */
.wizard-control-fill.disabled {{ background: {BORDER_SUBTLE_3}; box-shadow: inset 0 0 0 {SPACE_1} {BORDER}; color: {TEXT_SUBTLE_3}; }}
.wizard-control-primary.disabled {{ background: {BORDER_SUBTLE_3}; box-shadow: inset 0 0 0 {SPACE_1} {BORDER}; color: {TEXT_SUBTLE_3}; }}
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
/* Resolve.dc.html:118's .steprail: the four-step rail as the page
   region's first row. grid-column: 1 / -1 is carried here for fidelity
   with the artboard's own declaration and is inert as the sheet stands:
   .wizard-middle is display: flex; flex-direction: column, and
   grid-column applies only to a grid item, so the rail already fills the
   width .wizard-content-width leaves it, because a flex column stretches
   its items across. The artboard's own main is a single-column grid, where the declaration is equally inert.
   Giving .wizard-middle a grid display is what would make it live. This
   is a determinate reading of the sheet, not a question for the served
   page (DL-189, DL-199). */
.wizard-step-rail {{ display: flex; gap: {SPACE_2}; align-items: center; grid-column: 1 / -1; }}
/* Resolve.dc.html:22's .st and :23's .num: one step of the rail and the
   circular marker it carries. The marker takes its border from
   currentColor, so a step's own ink is the only thing the two state
   rules below change. */
.wizard-step {{ display: flex; align-items: center; gap: {SPACE_8}; padding: {SPACE_6} {SPACE_12}; border-radius: {RADIUS_LG}; font-size: {TYPE_12_5}; color: {TEXT_FAINT}; white-space: nowrap; }}
.wizard-step-number {{ font: 600 {TYPE_11}/1 {FONT_MONO}; width: {STEP_MARKER_SIZE}; height: {STEP_MARKER_SIZE}; border-radius: 50%; display: grid; place-items: center; border: 1px solid currentColor; flex: none; }}
/* Resolve.dc.html:24's .st.done and :25-26's .st.now. Both are declared
   after .wizard-step so the ink of a done or a current step wins at
   equal specificity, the same ordering .wizard-tab-selected takes
   against .wizard-tab. */
.wizard-step-done {{ color: {TEXT_MUTED}; }}
.wizard-step-current {{ background: {SURFACE_4}; color: {TEXT}; box-shadow: inset 0 0 0 {SPACE_1} {BORDER_STRONG}; font-weight: 600; }}
/* Resolve.dc.html:26's .st.now .num: the current step's marker,
   carrying the action blue as its ground and the page ground as its
   ink - the same pair .wizard-control-primary carries. Its own class
   rather than a descendant of .wizard-step-current, so the ink is read
   against the ground the marker actually paints rather than against
   the ground of the step around it. */
.wizard-step-number-current {{ background: {ACTION}; border-color: {ACTION}; color: {GROUND}; }}
/* Resolve.dc.html:41's .fbar and :112's .tally: the strip carrying the
   bulk actions, and the count sentence at its left. Resolve.dc.html:145
   sets the two apart with a flex:1 span, so the count reads from the
   strip's left and the bulk actions from its right. */
.wizard-bulk-strip {{ display: flex; align-items: center; gap: {SPACE_9}; flex-wrap: wrap; row-gap: {SPACE_9}; }}
.wizard-strip-spacer {{ flex: 1; }}
.wizard-tally {{ display: flex; align-items: center; gap: {SPACE_9}; font-size: {TYPE_12_5}; color: {TEXT_MUTED}; white-space: nowrap; margin: 0; }}
/* Resolve.dc.html:53's .split: the conflict table at the left taking
   what is left, the detail rail at the right at its fixed width. */
.wizard-resolve-split {{ display: grid; grid-template-columns: minmax(0, 1fr) {DETAIL_RAIL_WIDTH}; gap: {SPACE_16}; min-height: 0; }}
/* Resolve.dc.html:54's .tbl and :55's .gr: the bordered box the rows
   sit in, and the five-track grid a header row and every body row are
   laid out on. Both rows read CONFLICT_GRID_TRACKS, so a cell cannot
   align in the header and not in the body. */
.wizard-conflict-table {{ border: 1px solid {BORDER}; border-radius: {RADIUS_XL}; background: {SURFACE_2}; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }}
.wizard-conflict-grid {{ display: grid; grid-template-columns: {CONFLICT_GRID_TRACKS}; align-items: center; }}
/* Resolve.dc.html:56-57's .th: the header row's own ground, the rule
   below it and the mono label its cells carry. */
.wizard-conflict-header {{ border-bottom: 1px solid {BORDER_STRONG}; background: {SURFACE_3}; }}
.wizard-conflict-header > * {{ padding: {SPACE_10} {SPACE_12}; font: 600 {TYPE_11}/1.2 {FONT_MONO}; letter-spacing: .07em; text-transform: uppercase; color: {TEXT_FAINT}; }}
/* Resolve.dc.html:58-59's .tr: the rule under each body row and the
   inset its cells carry. min-width: 0 is what lets a cell ellipsis
   inside its own track rather than widening it. */
.wizard-conflict-row {{ border-bottom: 1px solid {SURFACE_5}; }}
.wizard-conflict-row > * {{ padding: {SPACE_10} {SPACE_12}; min-width: 0; }}
/* Resolve.dc.html:62's .trk: the identity cell holds a path with no
   break opportunity in it, so without this it neither wraps nor
   shortens and its text crosses the tracks beside it. The full path
   stands in the detail rail's head, which is what makes shortening it
   here readable rather than lossy (DL-214). */
.wizard-conflict-track {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
/* Resolve.dc.html:60's .tr.sel: the selected row's tinted ground and
   the action-blue marker inset at its leading edge. */
.wizard-conflict-row-selected {{ background: {ACTION_TINT_BG_ALT}; box-shadow: inset {SPACE_3} 0 0 {ACTION}; }}
/* Resolve.dc.html:70's .det and :71, :74, :105's .det-h, .det-b and
   .det-f: the rail as a bordered column of three bands - a head naming
   the file, a body holding one control per answer, and a footer holding
   the keys and the rail's own actions. The rail takes its width from
   .wizard-resolve-split's second track, so DETAIL_RAIL_WIDTH is
   written once. */
.wizard-detail-rail {{ border: 1px solid {ACTION_TINT_BORDER_ALT}; border-radius: {RADIUS_XL}; background: {BORDER_SUBTLE_2}; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }}
.wizard-detail-head {{ padding: {SPACE_12} {SPACE_14}; border-bottom: 1px solid {BORDER_SUBTLE_5}; display: flex; flex-direction: column; gap: {SPACE_4}; }}
.wizard-detail-body {{ padding: {SPACE_12} {SPACE_14}; display: flex; flex-direction: column; gap: {SPACE_13}; flex: 1; min-height: 0; }}
.wizard-detail-foot {{ padding: {SPACE_11} {SPACE_14}; border-top: 1px solid {BORDER_SUBTLE_5}; display: flex; flex-direction: column; gap: {SPACE_9}; }}
/* Resolve.dc.html:75's .grp and :76's .grp-h: one answer's own block
   inside the rail's body, and the label row above it carrying the
   digit that picks it. */
.wizard-answer-group {{ display: flex; flex-direction: column; gap: {SPACE_7}; }}
.wizard-answer-group-head {{ display: flex; align-items: center; justify-content: space-between; gap: {SPACE_8}; }}
/* Resolve.dc.html:81's .cand and :82's .cand.on: one control per
   distinct answer, and the chosen one's own border and ground.
   align-items is flex-start, as the artboard's .cand declares: the
   answer beside the marker is a block of field rows a dozen lines
   tall, and a centred marker floats at its middle - 103px below the
   card's own top edge on the served page, level with no row it names.
   Level with the first row it reads as the mark on the record it
   heads. */
.wizard-answer {{ border: 1px solid {BORDER}; background: {ACTION_TINT_BG}; border-radius: {RADIUS_LG}; padding: {SPACE_8} {SPACE_10}; display: flex; gap: {SPACE_9}; align-items: flex-start; }}
.wizard-answer-chosen {{ border-color: {ACTION_TINT_BORDER_ALT}; background: {BORDER_SUBTLE_9}; }}
/* Resolve.dc.html:83's .rad and :85's dot. The dot is its own element,
   rendered for the chosen answer alone, so what carries the chosen
   state is a class string at a call site rather than a pseudo-element
   no guard can read (DL-189). */
.wizard-answer-marker {{ width: {ANSWER_MARKER_SIZE}; height: {ANSWER_MARKER_SIZE}; border-radius: 50%; border: {ANSWER_MARKER_BORDER} solid {NEUTRAL_INACTIVE}; flex: none; display: grid; place-items: center; }}
.wizard-answer-chosen .wizard-answer-marker {{ border-color: {ACTION}; }}
.wizard-answer-dot {{ width: {ANSWER_MARKER_DOT_SIZE}; height: {ANSWER_MARKER_DOT_SIZE}; border-radius: 50%; background: {ACTION}; }}
/* Resolve.dc.html:90-93's .cmpf, .cmpf .k and .cmpf .v, plus :97's .r
   and :101's .d the rail draws beside them. The block is the control
   that picks the answer, so it carries the button's own reset: a
   ui.button with children still paints nicegui's ground and centres
   them. */
.wizard-answer-fields {{ flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: stretch; text-align: left; background: none; box-shadow: none; padding: 0; text-transform: none; }}
/* Quasar wraps a button's children in its own .q-btn__content, so the
   column declared on the button above governs that wrapper and not the
   rows inside it. The wrapper's own rule is a centred, wrapping row:
   left as it is, each field row takes its content's width and is
   centred on its own wrap line, so the three tracks start at a
   different x on every row and the "held by" line shares the last
   row's line instead of standing under the fields. The rows are the
   artboard's aligned grid, so the wrapper is turned back into the
   column the block declares (ref: DL-069, DL-071).

   text-align is here for the same reason: the wrapper carries
   Quasar's own text-center, which reads every field value from the
   middle of its track - "A" and "One" sitting at the centre of a
   166.8px track rather than at its start - so the value column does
   not read down the rail. The artboard's .cmpf .v states no
   text-align and inherits its block's left. */
.wizard-answer-fields .q-btn__content {{ width: 100%; flex-direction: column; flex-wrap: nowrap; align-items: stretch; justify-content: flex-start; text-align: left; }}
.wizard-answer-field {{ display: grid; grid-template-columns: {ANSWER_FIELD_KEY_TRACK} 1fr {ANSWER_FIELD_RAW_TRACK}; gap: {SPACE_8}; align-items: center; padding: {SPACE_5} 0; border-bottom: 1px solid {BORDER_SUBTLE_4}; }}
.wizard-answer-field:last-child {{ border-bottom: 0; }}
.wizard-answer-field-key {{ display: flex; align-items: center; gap: {SPACE_5}; min-width: 0; font: 500 {TYPE_11}/1 {FONT_MONO}; letter-spacing: {ANSWER_FIELD_KEY_TRACKING}; text-transform: uppercase; }}
.wizard-answer-field-value {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
/* Resolve.dc.html:97's .cmpf .r. The typeface is stated here beside the
   key's, because a Quasar font class on the label would set a family of
   its own and the artboard's mono would not be the one that renders
   (ref: DL-069). */
.wizard-answer-field-raw {{ font: 400 {TYPE_11}/1.3 {FONT_MONO}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: right; }}
/* The mark on a row the answers disagree on. A dot and nothing else:
   no rule here states a colour conditioned on a value's magnitude, so
   the screen never claims a larger filesize is the better one
   (ref: DL-249). Its size is its own constant rather than the chosen
   marker's: the two dots mean different things. */
.wizard-answer-field-mark {{ width: {ANSWER_FIELD_MARK_SIZE}; height: {ANSWER_FIELD_MARK_SIZE}; border-radius: 50%; background: {ACTION}; flex: none; }}
/* Resolve.dc.html:88's .cand .m: who holds this record, under the
   fields rather than in front of them - informational, not the thing
   being picked (DL-148). */
.wizard-answer-holders {{ padding-top: {SPACE_5}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
/* Resolve.dc.html:68's .dec and :69's .decd: the decision column reads
   from its right edge in both states - a Choose control while the group
   is undecided, the winning collection's name beside its own Undo once
   it is decided. The header's fifth cell is right-aligned by the same
   reading (Resolve.dc.html:155), so the heading sits over the column it
   names rather than over the column's empty left. The gap is
   CONTROL_GAP, not the 6px the artboard's own .dec draws: Specs' 8px
   between controls is the settled reading wherever the two disagree,
   which is the divergence "The gap between decision buttons" already
   records for Review.dc.html's identical pair (DL-088). */
.wizard-conflict-decision {{ display: flex; gap: {CONTROL_GAP}; justify-content: flex-end; }}
.wizard-conflict-decided {{ display: flex; align-items: center; gap: {CONTROL_GAP}; justify-content: flex-end; font-size: {TYPE_11_5}; font-weight: 600; white-space: nowrap; }}
.wizard-conflict-header > *:last-child {{ text-align: right; }}
/* Resolve.dc.html:106's .det-a and :107's .det-a .btn: the rail's two
   actions split the footer's width between them, which is why this is
   its own rule rather than .wizard-control-group - that one packs its
   controls to the left at their own widths. */
.wizard-detail-actions {{ display: flex; gap: {SPACE_8}; }}
.wizard-detail-actions .wizard-control {{ flex: 1; justify-content: center; }}
/* Resolve.dc.html:108's .keys and :109's .kb: three key hints, each a chip
   group beside the phrase it performs, rather than one sentence naming
   the keys in prose - the chips are what Specs' keyboard map draws. */
/* The chips themselves are .wizard-kbd, the rule emitted above; these
   two rules set the row and the hint around them, so a key chip reads
   the same here as it does wherever else the page names one. */
.wizard-key-row {{ display: flex; align-items: center; gap: {SPACE_13}; flex-wrap: wrap; padding: {SPACE_1} 0 {SPACE_8}; }}
.wizard-key-hint {{ display: inline-flex; align-items: center; gap: {SPACE_6}; font-size: {TYPE_11_5}; color: {TEXT_FAINT}; }}
/* Resolve.dc.html:273's .note in the rail's body and :294's .hint under
   main. .wizard-hint reproduces Resolve.dc.html:114's .hint rule; the
   artboard declares no rule for .note, and that note sets no colour, so
   the call site names the ink token it wears and one element cannot end
   up carrying two colour-setting classes, which tests/test_gui_theme.py
   holds over every classes() call. */
.wizard-note {{ display: flex; gap: {SPACE_8}; font-size: {TYPE_12}; line-height: 1.45; }}
.wizard-hint {{ margin: 0; font-size: {TYPE_12}; color: {TEXT_FAINT}; display: flex; align-items: center; gap: {SPACE_8}; padding-bottom: {SPACE_8}; }}
/* Preview.dc.html:27 and Write.dc.html:27's main: the two step screens
   that read a run put their content beside a rail of the same width the
   resolve step's own split gives it, so DETAIL_RAIL_WIDTH is the one
   value all three read. The columns start at the top rather than
   stretching, because the two hold different amounts and a card
   stretched to its neighbour's height draws a band of empty ground under
   its last row (DL-216). */
.wizard-step-split {{ display: grid; grid-template-columns: minmax(0, 1fr) {DETAIL_RAIL_WIDTH}; gap: {SPACE_20}; align-items: start; min-height: 0; width: 100%; }}
/* Preview.dc.html:28's .col: one column of the split, its boxes stacked
   at the artboard's own 14px. */
.wizard-step-column {{ display: flex; flex-direction: column; gap: {SPACE_14}; min-height: 0; min-width: 0; }}
/* Preview.dc.html:68-71's .pl: one listed playlist, its name at the left
   taking what is left and its count at the right at its own width, ruled
   off from the row below it. The last row's rule is removed rather than
   drawn over, so the card's own padding is what ends the list. */
.wizard-list-row {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: {SPACE_12}; align-items: center; padding: {SPACE_6} {SPACE_2}; border-bottom: 1px solid {SURFACE_5}; font-size: {TYPE_12_5}; }}
.wizard-list-row:last-child {{ border-bottom: 0; }}
.wizard-list-name {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.wizard-list-count {{ font: 600 {TYPE_12}/1 {FONT_MONO}; color: {TEXT_MUTED}; white-space: nowrap; }}
/* Preview.dc.html:72's .scroll: the listing scrolls inside its own card
   rather than growing the page, which is what keeps the middle the
   scroll owner the shell record reads it as. */
.wizard-scroll {{ overflow-y: auto; min-height: 0; display: flex; flex-direction: column; }}
/* Preview.dc.html:73's .tot and :74's .big: the summed count under the
   listing, its label at the left and its number at the right. */
.wizard-total {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: {SPACE_12}; align-items: center; padding: {SPACE_11} {SPACE_12}; border-radius: {RADIUS_LG}; background: {SURFACE_3}; border: 1px solid {BORDER_STRONG}; font-size: {TYPE_13}; font-weight: 600; }}
.wizard-total-amount {{ font: 600 {TYPE_15}/1 {FONT_MONO}; }}
/* Preview.dc.html:47-50 and Write.dc.html:42-45's .note: a bordered
   panel carrying a sentence about the run, tinted by what it is about -
   the action hue where it states something the run did, the review hue
   where it names something still to be decided. Its own rule rather than
   .wizard-note, which is the rail's borderless inline note. */
.wizard-callout {{ display: flex; gap: {SPACE_10}; padding: {SPACE_11} {SPACE_13}; border-radius: {RADIUS_LG}; border: 1px solid {BORDER}; background: {SURFACE_1}; font-size: {TYPE_12_5}; line-height: 1.5; color: {TEXT_MUTED}; }}
.wizard-callout-info {{ border-color: {ACTION_TINT_BORDER_ALT}; background: {BORDER_SUBTLE_9}; }}
.wizard-callout-warn {{ border-color: {STATUS_NEEDS_REVIEW_STRONG}; background: {STATUS_NEEDS_REVIEW_TINT_BG}; }}
/* Preview.dc.html:53's .meta: the small print under a card's own rows. */
.wizard-meta {{ margin: 0; font-size: {TYPE_12}; color: {TEXT_FAINT}; display: flex; gap: {SPACE_8}; align-items: center; flex-wrap: wrap; }}
/* Write.dc.html:47-48's .dest: the output path as its own panel, the
   path itself set in mono and broken anywhere, because a Windows path
   offers no break opportunity and this panel is where it is read in
   full. */
.wizard-destination {{ display: flex; flex-direction: column; gap: {SPACE_8}; padding: {SPACE_13} {SPACE_14}; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS_7}; background: {GROUND}; }}
.wizard-destination-path {{ font: 500 {TYPE_13}/1.4 {FONT_MONO}; word-break: break-all; }}
/* Write.dc.html:49's .badge: a chip stating one fact about the file
   beside it. */
.wizard-badge {{ display: inline-flex; align-items: center; gap: {SPACE_6}; font: 600 {TYPE_11}/1 {FONT_MONO}; letter-spacing: .08em; text-transform: uppercase; padding: {SPACE_5} {SPACE_7}; border-radius: {RADIUS_SM}; border: 1px solid {STATUS_FOUND_TINT_BORDER}; color: {STATUS_FOUND_TINT_TEXT}; background: {STATUS_FOUND_TINT_BG}; align-self: flex-start; }}
/* Write.dc.html:51-54's .cr: one line of what the new file will hold -
   its mark, the change and the sentence under it, and the count at the
   right. The count's ink is its own class, so which tone a row reads at
   is a class string at the call site rather than a colour written there
   (DL-188). */
.wizard-change-row {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: {SPACE_11}; align-items: center; padding: {SPACE_7} {SPACE_2}; border-bottom: 1px solid {SURFACE_5}; font-size: {TYPE_12_5}; }}
.wizard-change-row:last-child {{ border-bottom: 0; }}
.wizard-change-detail {{ display: block; font-size: {TYPE_11}; color: {TEXT_SUBTLE_1}; margin-top: {SPACE_2}; line-height: 1.4; }}
.wizard-change-count {{ font: 600 {TYPE_15}/1 {FONT_MONO}; text-align: right; }}
.wizard-change-added {{ color: {STATUS_FOUND}; }}
.wizard-change-untouched {{ color: {TEXT_MUTED}; }}
/* Write.dc.html:56-60's .dlg: the confirmation the write is asked
   through, a raised panel over the step, its three assurances listed and
   its two actions at the right. */
.wizard-dialog {{ border: 1px solid {BORDER_SUBTLE_7}; border-radius: {RADIUS_XL}; background: {SURFACE_3}; padding: {SPACE_16}; display: flex; flex-direction: column; gap: {SPACE_12}; }}
.wizard-dialog-list {{ display: flex; flex-direction: column; gap: {SPACE_8}; }}
.wizard-dialog-item {{ display: flex; gap: {SPACE_9}; font-size: {TYPE_12_5}; color: {TEXT_MUTED}; line-height: 1.5; }}
.wizard-dialog-actions {{ display: flex; justify-content: flex-end; gap: {SPACE_9}; }}
/* Reconstruct.dc.html:44's .field and :46's .row: a chosen path stands
   in a bordered inset box on the page's own ground rather than as loose
   text beside its button, so what the operator gave the page and what
   they may still change are told apart by the box around one of them.
   The box takes the row's width and the control beside it takes its own,
   which is why the row is its own rule rather than
   .wizard-control-group. */
.wizard-field-row {{ display: flex; align-items: center; gap: {SPACE_10}; min-width: 0; width: 100%; }}
.wizard-field {{ display: flex; align-items: center; gap: {SPACE_10}; background: {GROUND}; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS_LG}; padding: 0 {SPACE_12}; height: {FIELD_HEIGHT}; flex: 1; min-width: 0; }}
/* Reconstruct.dc.html:45's .field .mono: a path has no break
   opportunity in it, so a field narrower than its path shortens rather
   than spilling past the box that holds it. */
.wizard-field-value {{ font-family: {FONT_MONO}; font-size: {TYPE_12_5}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
/* Reconstruct.dc.html:121: what a source's own row reports about the
   file, read from the field's right edge. */
.wizard-field-note {{ font-family: {FONT_MONO}; font-size: {TYPE_11_5}; color: {TEXT_FAINT}; white-space: nowrap; margin-left: auto; }}
/* Reconstruct.dc.html:112's .bar inside a .meta: the upright rule
   between two phrases about one file. It is the header band's own
   divider at the meta line's own scale, and it is a separator rather
   than a bullet because the phrases are read as one line. */
.wizard-meta-divider {{ width: {SPACE_1}; height: {META_DIVIDER_HEIGHT}; background: {BORDER_STRONG}; flex: none; }}
/* Reconstruct.dc.html:112's own emphasis: the count of empty playlists
   is what the page exists to repair, so it reads at the review hue
   rather than at the muted ink of the phrases beside it. */
.wizard-meta-count {{ color: {STATUS_NEEDS_REVIEW}; font-weight: 600; }}
/* Reconstruct.dc.html:64-67's .steps: what happens after this step, one
   row per step, each numbered by the step it names. The marker is the
   rail's own circle at the list's own size, drawn on the card's ground
   rather than on the rail's. */
.wizard-next-steps {{ display: flex; flex-direction: column; gap: {SPACE_11}; margin: 0; padding: 0; list-style: none; }}
.wizard-next-step {{ display: flex; gap: {SPACE_11}; font-size: {TYPE_12_5}; color: {TEXT_MUTED}; line-height: 1.5; }}
.wizard-next-step-marker {{ flex: none; width: {NEXT_STEP_MARKER_SIZE}; height: {NEXT_STEP_MARKER_SIZE}; border-radius: 50%; border: 1px solid {BORDER_STRONG}; color: {TEXT_FAINT}; font: 600 {TYPE_11}/1 {FONT_MONO}; display: grid; place-items: center; margin-top: {SPACE_1}; }}
.wizard-next-step-title {{ display: block; color: {TEXT}; font-weight: 600; font-size: {TYPE_13}; margin-bottom: {SPACE_1}; }}
/* design/build-playlist/Specs.dc.html's input .row: the chosen path, the
   detected format tag and the two choosers on one line, the path taking
   the room and truncating rather than pushing the buttons off the card. */
.buildplaylist-input-row {{ display: flex; align-items: center; gap: {SPACE_10}; flex-wrap: nowrap; min-width: 0; width: 100%; }}
.buildplaylist-input-row > .font-mono {{ flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
/* Specs.dc.html's .fmt: the format read_input will read the input as,
   tinted with the action hue because it describes what the run does. */
.buildplaylist-format-tag {{ flex: none; font: 600 {TYPE_11}/1 {FONT_MONO}; letter-spacing: .06em; text-transform: uppercase; color: {ACTION_TINT_TEXT}; background: {BORDER_SUBTLE_9}; border: 1px solid {ACTION_TINT_BORDER_ALT}; border-radius: {RADIUS_SM}; padding: {SPACE_3} {SPACE_6}; white-space: nowrap; }}
/* Specs.dc.html's .note strong: the CSV note's lead reads at full ink,
   and the note's two phrases run on as one sentence. */
.buildplaylist-note-text {{ min-width: 0; }}
.buildplaylist-note-text > div {{ display: inline; }}
.buildplaylist-note-lead {{ color: {TEXT}; font-weight: 600; margin-right: {SPACE_4}; }}
/* Specs.dc.html's template button sits at the note's right edge. */
.buildplaylist-template-control {{ margin-left: auto; flex: none; }}
/* Specs.dc.html's folder .row: Output folder and Playlist folder side by
   side at equal width, tops aligned because only the output side carries
   a button under its label. */
.buildplaylist-folder-row {{ display: flex; gap: {SPACE_14}; align-items: flex-start; flex-wrap: nowrap; width: 100%; }}
.buildplaylist-folder-col {{ flex: 1; min-width: 0; gap: {SPACE_6}; }}
"""

"""Specs' measured token set: traktor_nml/gui/app.py's colour, type,
spacing and radius values, held once so a hex or a pixel size is never
repeated at a call site (DL-078). Imports no nicegui, so the pytest
interpreter reads it directly (DL-078, DL-085).
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
RADIUS_SM = "4px"
RADIUS_MD = "5px"
RADIUS_LG = "6px"
RADIUS_XL = "8px"

FONT_SANS = "'IBM Plex Sans', system-ui, -apple-system, sans-serif"
FONT_MONO = "'IBM Plex Mono', ui-monospace, Consolas, monospace"

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
CONTROL_HEIGHT = "32px"
CONTROL_GAP = SPACE_8


def page_stylesheet() -> str:
    """The wizard's stylesheet as one string, every colour and size
    drawn from this module's own constants rather than a literal
    (DL-078)."""
    return f"""
body {{ background: {GROUND}; color: {TEXT}; font: 400 {TYPE_14}/1.45 {FONT_SANS}; }}
.q-page {{ background: {GROUND}; color: {TEXT}; }}
.wizard-surface {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: {RADIUS_XL}; }}
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
.wizard-control {{ min-height: {CONTROL_HEIGHT}; margin-bottom: {CONTROL_GAP}; }}
*:focus-visible {{ outline: {FOCUS_RING}; outline-offset: {FOCUS_RING_OFFSET}; }}
@media (prefers-reduced-motion: reduce) {{
  .q-spinner, .q-linear-progress__model {{ animation: none !important; }}
}}
.wizard-row {{ border-bottom: 1px solid {BORDER_SUBTLE_6}; }}
.wizard-row:nth-child(odd) {{ background: {SURFACE_1}; }}
.wizard-row:nth-child(even) {{ background: {SURFACE_5}; }}
.wizard-row-focused {{ outline: {FOCUS_RING}; outline-offset: {FOCUS_RING_OFFSET}; background: {BORDER_SUBTLE_5}; border-color: {BORDER_SUBTLE_7}; }}
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
.wizard-tag-review {{ background: {STATUS_NEEDS_REVIEW_TINT_BG}; border: 1px solid {STATUS_NEEDS_REVIEW_STRONG}; }}
.wizard-tag-review.alt {{ background: {STATUS_NEEDS_REVIEW_TINT_BG_ALT}; }}
.wizard-tag-review strong {{ color: {STATUS_NEEDS_REVIEW}; }}
.wizard-tag-missing {{ background: {STATUS_NOT_FOUND_TINT_BG}; border: 1px solid {STATUS_NOT_FOUND_STRONG}; color: {STATUS_NOT_FOUND_TINT_TEXT}; }}
.wizard-tag-missing strong {{ color: {STATUS_NOT_FOUND}; }}
.wizard-tag-action {{ background: {ACTION_TINT_BG}; border: 1px solid {ACTION_TINT_BORDER}; color: {ACTION_TINT_TEXT}; }}
.wizard-tag-action.alt {{ background: {ACTION_TINT_BG_ALT}; border-color: {ACTION_TINT_BORDER_ALT}; color: {ACTION_TINT_TEXT_ALT}; }}
.wizard-tag-action strong {{ color: {ACTION_STRONG}; }}
.wizard-panel {{ background: {SURFACE_4}; border: 1px solid {BORDER_SUBTLE_4}; border-radius: {RADIUS_MD}; padding: {SPACE_9} {SPACE_10}; }}
.wizard-note {{ font-size: {TYPE_12_5}; padding: {SPACE_2} {SPACE_4}; border-left: {SPACE_1} solid {BORDER_SUBTLE_1}; }}
.wizard-hd-alt {{ border-bottom: 1px solid {BORDER_SUBTLE_2}; }}
.wizard-sec-alt {{ border: 1px solid {BORDER_SUBTLE_3}; border-radius: {RADIUS_LG}; }}
.wizard-hairline {{ border-top: 1px solid {BORDER_SUBTLE_8}; }}
.wizard-tag-action-outline {{ border: 1px solid {BORDER_SUBTLE_9}; }}
.wizard-heading-lg {{ font-size: {TYPE_23}; }}
.wizard-display {{ font-size: {TYPE_30}; }}
.wizard-display-xl {{ font-size: {TYPE_40}; }}
.wizard-heading-sm {{ font-size: {TYPE_16}; }}
.wizard-heading-xs {{ font-size: {TYPE_17}; }}
.wizard-body-11 {{ font-size: {TYPE_11}; }}
.wizard-body-11-5 {{ font-size: {TYPE_11_5}; }}
.wizard-body-12-5 {{ font-size: {TYPE_12_5}; }}
.wizard-body-13 {{ font-size: {TYPE_13}; }}
.wizard-body-13-5 {{ font-size: {TYPE_13_5}; }}
.wizard-body-14-5 {{ font-size: {TYPE_14_5}; }}
.wizard-body-15 {{ font-size: {TYPE_15}; }}
.q-toggle__thumb {{ background: {SWITCH_KNOB}; }}
.q-toggle__track {{ background: {SWITCH_TRACK}; }}
.body--dark, .body--dark .q-stepper, .body--dark .q-field__native, .body--dark .q-field__control {{ color: {TEXT}; }}
"""

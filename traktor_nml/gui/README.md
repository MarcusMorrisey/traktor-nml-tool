# traktor_nml/gui/

What is not visible from reading the modules: the import boundary the
test suite depends on, why the wizard calls the cores in process, how
the two design documents are resolved where they disagree, and what the
vendored typeface is.

## The nicegui boundary

`app.py`, `file_picker.py` and `__main__.py` are the only three modules
in this package that import `nicegui` or `pywebview`. Every other
module - `review_model.py`, `wizard_state.py`, `theme.py`, `keymap.py`,
`announce.py`, `conflict_model.py`, `navigation.py`,
`reconstruct_steps.py`, `reconstruct_report.py`,
`collection_summary.py`, `answer_detail.py`, `wording.py`, `_fs_nav.py`
and `__init__.py` - imports neither
and is reachable from the test suite's
system interpreter, which has no `nicegui` installed. Every rule worth
testing sits below that boundary, in the nicegui-free modules, so the
suite can reach it (DL-069; guarded by an AST walk in
`tests/test_gui_view_boundary.py`).

The list is documentation; `tests/test_gui_view_boundary.py` sweeps the
directory rather than reading it, so a module named here is named for a
reader and guarded by the sweep (ref: DL-069).

## Why the wizard drives the cores directly

The wizard imports and calls `run_reconnection` and the two reconnect
cores in-process and renders its own view from `ReconnectResult`. It
does not shell out to `scan-reconnect-candidates`/`rewrite-from-reconnect`
and parse their key=value stdout. Tier 1 needs structured data while a
run is still open - a live scan progress feed and an interactive
ambiguous-match table the operator acts on mid-run - and a parsed
transcript exists only once the process has exited, so a scraping wizard
could build its review table only after the decision point the table
exists to serve, with no live object to cancel into. `ui.log` is instead
fed from `reconnect_render`'s line-producing functions over the
`RenderedOutput` they already return.

Subprocess-scraping the CLI transcript is not wrong; it was evaluated as
the data source for Tier 1, rejected, and survives as the
`docs/nicegui-gui-analysis.md` section 5 fallback if in-process
integration fails, and remains a correct way to obtain the same numbers
after a run (DL-075, `traktor_nml/README.md`).

## Where Specs.dc.html and docs/nicegui-gui-analysis.md disagree

`design/reconnect-wizard/Specs.dc.html` and sections 1-5 of
`docs/nicegui-gui-analysis.md` disagree in two places, and neither is
resolved by silently preferring one document over the other:

- **Status taxonomy and the keyboard map**: section 4 of
  `docs/nicegui-gui-analysis.md` names three review buckets (matched,
  ambiguous, dangling) against `ui.aggrid` with row selection; Specs
  names six statuses, seven filter chips, and a keyboard contract
  binding digits 1-9 to candidate picking, A/R/U to decisions, and
  Shift-arrow to range selection. **Specs governs** - it is the
  cross-screen contract for what the operator sees and presses.
  The review table renders hand-rolled `ui.row` rows per record;
  aggrid claims the arrow keys Specs binds over that same table, and
  is not adopted for it (DL-079). Section 4's three buckets are read
  against those rows. See `traktor_nml/README.md`'s Design Decisions
  section for DL-078 through DL-089.
- **Framework mechanics**: `run.io_bound` (not `run.cpu_bound`, since
  neither `TagCache` nor an lxml root pickles cleanly across a process
  boundary), `ui.log`, and the `local_file_picker` component are named
  only in section 4 - Specs names no framework at all. **Section 4
  governs** these three.

(DL-072, `traktor_nml/README.md`.)

## Design source of record

`design/reconnect-wizard/Specs.dc.html` is a committed source, read
alongside the other tracked `.dc.html` files and `canvas.json`;
`design/reconnect-wizard/reconnect-wizard.html` is the gitignored bundle
seeded from those sources. The precedence rule the design set carries is
that a screen disagreeing with Specs is fixed in Specs rather than the
other way round: Specs is the cross-screen contract, and an artboard is
one screen's rendering of it (DL-071).

## Tier classification is not re-derived here

`scan-reconnect-candidates`' membership in both Tier 1 (the wizard's
first step) and Tier 2 (generated-form eligibility) is resolved by
`tests/test_gui_command_classification.py`'s two predicates,
`PRIMARY_TIER` and `TIER2_ELIGIBLE`, checked against the real
`build_parser` choices. This package reads that dual membership as
settled rather than re-deriving a second classification (DL-073).

## The vendored typeface

`theme.py`'s `FONT_SANS` and `FONT_MONO` name IBM Plex, and `fonts/`
holds the faces that make those names paint. Naming a family the page
cannot load is silent: the browser walks the stack to the next entry it
has, so the page renders in Segoe UI and Consolas while the stylesheet
says IBM Plex, and nothing reports it. The measurement that found it
compared the two stacks against known families in the served page's own
canvas: the sans stack drew a test string at 485.5078125px, identical to
`system-ui` and to `"Segoe UI"`, and the mono stack at 615.78125px,
identical to `Consolas`.

### What is vendored, and from where

The seven faces `design/reconnect-wizard/Main.dc.html` line 11 imports:
IBM Plex Sans 400/500/600/700 and IBM Plex Mono 400/500/600. No italic,
because no artboard sets one.

Upstream is IBM's own npm publication of the families, `@ibm/plex-sans`
and `@ibm/plex-mono`, both at version **1.1.0**, taken from the
`fonts/complete/woff2/` directory of each package. The files are
committed unmodified and unsubsetted (DL-167).

| File | Family, weight | Bytes | SHA-256 |
|---|---|---|---|
| `IBMPlexSans-Regular.woff2` | Sans 400 | 63020 | `ba711a3085ff9f27440b6b9c4550cfc47c97bf36591d5da958b975bb3add8c1a` |
| `IBMPlexSans-Medium.woff2` | Sans 500 | 66740 | `5660f8a658f8bb50dbc005232f885eadffd2bc1c235c4f6fbb63469d1f9cde6d` |
| `IBMPlexSans-SemiBold.woff2` | Sans 600 | 67060 | `f78048030eab62e860efa39a0df79e2e5581bf122eb95b9bc42c0b8a4988d205` |
| `IBMPlexSans-Bold.woff2` | Sans 700 | 63012 | `fa7130d854a660b39a7fc9e6e0f2dc23dba5f1346e2adea3e1fe37b6d884133d` |
| `IBMPlexMono-Regular.woff2` | Mono 400 | 45640 | `49ce58b41a0e1cb921c0f58d9a5b8b96a2cc21437c7066f3ba4f24873076d131` |
| `IBMPlexMono-Medium.woff2` | Mono 500 | 46724 | `8c2c290cbd998fa1f647e4572aca6ebbd72589551b0f3f9f8bb8628fbb8219d5` |
| `IBMPlexMono-SemiBold.woff2` | Mono 600 | 47016 | `ed5eaca7522336959d6c3810bd9bb78424f0d964082d581bfbea169ee08d14e3` |

The measured total is **399212 bytes** across the seven faces, and
`tests/test_gui_font_assets.py` asserts each file against its size and
hash above and the directory against that total. A ceiling picked for
looking generous admits any drift beneath it; the measured total names
what is there, so a face swapped for another is a guard failure and a
decision rather than a quiet gain (DL-176).

`OFL.txt` beside the faces is the licence they ship under, SIL Open Font
License 1.1 (DL-166).

### How they reach the page

`theme.py` holds `FONT_URL_BASE` and `FONT_FACES` and emits one
`@font-face` block per entry; `app.py` mounts the directory at that same
constant. The src and the route that answers it are one fact, and
`theme.py` may not import nicegui (DL-069), so the constant lives on the
nicegui-free side and the mount reads it (DL-164).

The mount is `nicegui.app.app.add_static_files`, whose signature in the
installed **nicegui 3.16.0** is
`(url_path: str, local_directory: str | Path, *, follow_symlink: bool = False, max_cache_age: int = 3600) -> None`.
That reading is recorded here because no guard can execute the mount:
the suite runs under the system interpreter, which has no nicegui
(DL-174, DL-178).

`_mount_fonts()` is called from `_page_chrome`, which both pages call,
and it is idempotent because nicegui raises on a route mounted twice.

### What the guards can and cannot see

No guard asserts a font-family name on its own. `theme.FONT_SANS`
already named IBM Plex throughout the period the page painted Segoe UI,
and `document.fonts.check('14px "IBM Plex Sans"')` returns `True` for an
absent face, so a name assertion is true in exactly the broken state
(DL-165). The guards read the files, their sizes and hashes, the count
and content of the emitted `@font-face` blocks, and the argument the
mount is given. What none of them can read is whether the face actually
painted; that is a served-page reading, and it belongs to the record
DL-180 requires.

## The shell both pages compose against

`_page_chrome` applies the theme, builds the header band and the footer
band, and hands back the middle container. Both routes enter that
container with a `with` statement, so a page's body lands inside the
scrolling region rather than beside it (DL-185). The header band, the
middle region and the footer band are the three rows `.app` draws at
`Main.dc.html:15`, and the middle owns the page scroll rather than the
document (DL-184). The footer band is `Main.dc.html:29-31`: `.ft`
holding `.ft-note`'s sentence at the left and `.ft-act`'s controls at
the right.

The bands are `ui.header` and `ui.footer`, each with `bordered` and
`elevated` off: Quasar's own `QLayout` writes each band's height onto
`q-page-container` as padding, and the rule and the ground each band
carries are the ones `theme.py` emits (DL-183). The middle owns
`overflow-y`, and `q-layout`, `q-page-container`, `q-page` and
`nicegui-content` - the four elements nicegui builds between the
viewport and the page's content - each carry a bounded height, which is
what leaves the middle a height to scroll inside (DL-193). The reading
is in `docs/2026-09-05-wizard-shell-browser-record.md`, which reads the
middle at `1280x780` between a `56px` header and a `64px` footer, the
middle's `scrollHeight` at `943` against a `clientHeight` of `780`, and
the document's at `900` against `900`.

Each section both pages build is a card: `.wizard-card` holding a
`.wizard-card-head` with its `.wizard-card-title`, and a
`.wizard-card-body`, as `Main.dc.html:32-35` draws it (DL-186). A step's
own header is Quasar's `QStepper` markup rather than one of those
sections. `docs/2026-09-07-composition-close-browser-record.md` reads
the triplet on both routes - four cards on `/`, one per rendered step on
`/reconnect`, each carrying a head, a title and a body - and records no
part of it refused, so the Card structure entry carries no narrowing
under "Composition not built" in `traktor_nml/README.md` (DL-194).

Each of the four steps registers its own action group in the footer
band and the step change decides which group the band shows, so the
control that advances a step exists once and its enabled state is held
once (DL-187). Its place in the DOM is what sets the tab order, and the
ring that walk produces is read in
`docs/2026-09-06-wizard-focus-order-browser-record.md` (DL-197).

## The two step mechanisms

Both routes are walked in four steps and neither drives the other's
mechanism. `/reconnect` runs a `ui.stepper` with a `footer_groups`
mapping keyed by step title. `/` composes four plain regions inside the
chrome's middle, one visible at a time, under a `nav` of spans rendered
from `reconstruct_steps.rail_records`: `Resolve.dc.html:118` draws
`.steprail` inside `main` at `grid-column: 1 / -1`, and a QStepper draws
its own numbered strip above its panels and none of the rail's states
(DL-199).

`reconstruct_steps.py` holds the four-step table, the rail records it
derives and the reachability rule that decides which step the page may
show. It is the one place a step number or a step label is written, and
it imports no framework, so the suite reads it directly and `app.py`
renders the records and decides none of them (DL-202, DL-203). The
resolve step's own gate is `conflict_model.resolve_gate`, which answers
the outstanding count, the decided count and whether the step may be
left over one walk of the groups, so the footer's sentence and the
advancing control's enabled state are one reading (DL-204).

`reconstruct_report.py` holds what the two reporting steps say. The
preview and the write steps each report a held run, and every number and
every sentence on them is derived there from that run's stats, the
conflict groups it reported and the answers given to those groups: how
many empty playlists were filled against how many there were, the
listing's division into named rows and a row standing for the rest, how
many tracks are still held more than one way with no answer, what the
new file will hold, and the confirmation's own question. `app.py` draws
those records and derives none of them, and both panels are redrawn on
entry to their step, because what they say is answered by controls on
the steps beside them (DL-215, DL-217, DL-219).

A step that reports a run is reached only on a run that produced one,
and the walk into the write step re-assembles where the held run reports
answers other than the ones now given. `conflict_model.run_assembled`
answers the first and `conflict_model.run_is_current` the second, so the
page never reads `result.output` itself and never asks twice whether the
answers have changed. `reconstruct_report.preview_refusal` holds what
the preview says when its run assembled nothing (DL-224, DL-225,
DL-226).

`collection_summary.py` holds what the set-up step says about a
collection it has been given: its tracks, its playlists, how many of
those hold nothing, and for a source how many it could supply contents
from, all read off the parsed file rather than off a run. It also holds
`NEXT_STEPS`, the three steps that follow set-up, numbered by
`reconstruct_steps.STEPS` so the list and the rail above it cannot
disagree (DL-220, DL-221).

The resolve step's table dispatches through `keymap.dispatch` at
`SCOPE_TABLE` and applies through the reconstruct route's own
name-to-applier table, since the wizard's `_ACTION_APPLIERS` appliers
are typed on the wizard's page state. `keymap.py` itself carries the
digit bindings both tables read (DL-205).

Every dimension either the shell or the cards measure at is a constant
in `theme.py`, sourced in a comment to the artboard line that states
it. `theme.py` imports no nicegui, so it is the module a guard under
the system interpreter can read (DL-069, DL-188).

What a guard in `tests/` holds of all this is the text: which rule the
stylesheet emits, which class string a call site names, and where each
control is constructed. Whether the browser gave the middle the
viewport, and what it computed for a card, is read on a served page and
written into a record under `docs/` (DL-084, DL-169, DL-189). The step
rail's rendered position across the page region, the conflict grid's
resolved column widths and the detail rail's resolved width belong to
that record for the same reason: a guard reading
`grid-template-columns: 1fr 400px` out of the emitted sheet is true
whether or not the browser laid the split out on those tracks.

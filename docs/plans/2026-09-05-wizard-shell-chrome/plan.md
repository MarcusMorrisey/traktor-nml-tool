# Plan

## Overview

The reconnect wizard's artboards draw .app as grid-template-rows 56px 1fr 64px: a header band, a middle that scrolls under it, and a footer band carrying a note at the left and the screen's advancing action at the right, with three to four .card boxes inside the middle, each a bordered box with its own header band, title and padded body. gui/ composes a header row followed by one column carrying .wizard-surface once, with the document itself scrolling and the actions sitting inline as the column's last children. Four served-page records read matches on every atom while all six structures differ, which is the gap DL-169 amended the gate to catch and which traktor_nml/README.md records as the App shell, Card structure and Footer band entries under Composition not built.

**Approach**: The bands are ui.header and ui.footer built once in _page_chrome, the one call site both routes share, with Quasar's border and elevation switched off at the constructor and every dimension, colour and class name held in theme.py, the only module a guard under the system interpreter can read. theme.py gains the 56px and 64px band heights beside CONTENT_WIDTH, height rules keyed on the framework's own layout classes because app.py never constructs that element, band rules that restate the direction, alignment and padding nicegui.css sets on the same elements, footer note and action rules, and the four card rules in place of .wizard-surface. _page_chrome yields a chrome object holding the note, the action row and the middle container, and both routes enter that container. One wave builds all of it with its guards and one served-page record. The second wave re-reads the keyboard map, the focus order and the announcements, because moving the advancing actions into the footer changes DOM order and therefore tab order. The third strikes a Composition-not-built entry only where a record read its structure built, narrows any entry the QStepper markup refused, and leaves Column model, Table geometry and Detail rail standing with the statement that keeps them open cited beside them.

## Planning Context

### Decision Log

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-183 | The header and footer bands are ui.header and ui.footer built in _page_chrome, not hand-rolled position:fixed elements | Quasar QLayout already reserves space for its own header and footer and offsets the page container by their heights -> a hand-rolled fixed band is laid over a container that has reserved nothing, so the band overlaps content and every fix is a second offset chasing the first -> the bands are the framework elements, and theme.py supplies their paint through .nicegui-header and .nicegui-footer overrides |
| DL-184 | Both nicegui layout elements are constructed with bordered=False and elevated=False; the band paint - ground - one pixel rule - 56px and 64px heights - 0 24px padding - alignment is declared by theme.py on the .wizard-header-band and .wizard-footer-band classes app.py attaches to those elements | nicegui.css lines 14-28 give .nicegui-header and .nicegui-footer display flex - flex-direction column - align-items flex-start - 1rem gap - 1rem padding, and lines 41-46 override those two selectors to flex-direction row; Quasar adds its own border and shadow -> a band left at those defaults sits at the wrong alignment and padding and paints a rule the artboard does not draw, while the direction it needs the framework already gives it -> the two framework flags remove what the constructor owns and theme.py restates alignment - gap - padding - height - ground and rule on the wizard band classes it emits (DL-192), keeping every value below the nicegui boundary (DL-069) |
| DL-185 | The middle owns the viewport by height-constraining the layout: theme.py fixes the q-layout container and its page container to the viewport height and gives the middle region its own overflow-y: auto, so the document itself does not scroll | The artboards draw .app as grid-template-rows: 56px 1fr 64px at a fixed height, which is a middle that scrolls under stationary bands -> Quasar fixed bands alone leave the document scrolling with the bands floating over it, which is a different silhouette that happens to look similar until the page is long -> the shell rule sets the height and the scroll owner explicitly, and the served-page record reads scrollHeight against clientHeight on both the document and the middle to say which one scrolled |
| DL-186 | The card triplet is applied to the sections each page already builds, and the vertical ui.stepper keeps a Composition-not-built entry of its own if Quasar QStepper markup refuses the classes | ui.stepper renders QStepper own step header and step-inner markup, whose padding and borders are declared in a Quasar layer -> a .card-h attached to a QStepper header may be outranked or may land on a wrapper that is not the band the artboard draws -> the triplet lands where the page composes its own containers, what the stepper refuses is measured on the served page rather than assumed, and any residue is filed as a named entry rather than absorbed into a matches verdict |
| DL-187 | The advancing action for each step is constructed inside the footer band and the step exposes the callable it invokes, rather than a widget re-parented out of the step or duplicated beside it | A re-parented widget keeps one object but moves it after the step built it, so the DOM order depends on construction order across two builders -> a duplicate keeps DOM order simple but has two enabled/disabled states to hold in step -> the footer constructs the control and the step hands over the function it already calls, which leaves one object, one state and a DOM order that reads header, middle, footer |
| DL-188 | Shell dimensions live in theme.py beside CONTENT_WIDTH as named constants - the 56px and 64px band heights and the 15px, 20px and 22px steps Main.dc.html measures - and app.py names only class strings | theme.py may not import nicegui, so it is the only module a guard under the system interpreter can read (DL-069, DL-164) -> a dimension written at an app.py call site is invisible to every guard and to the hex- and size-scanning tests in tests/test_gui_theme.py -> every band height, padding and gap this shell measures is a constant in theme.py and reaches the page through a rule, never through a .classes() literal |
| DL-189 | The new guards assert the presence and the content of each shell, card and footer rule in the emitted stylesheet and the class strings app.py names, and assert nothing about layout | theme.FONT_SANS named IBM Plex throughout the period the page painted Segoe UI, so a guard that reads a name is true in exactly the broken state (DL-165) -> a guard asserting that a .wizard-shell rule exists says nothing about whether the browser gave it the viewport -> the guards are the regression net over the text, and whether the middle scrolled under stationary bands is read off a served page and written into the docs record, which is the pass condition (DL-084, DL-169) |
| DL-190 | The three Composition-not-built entries are struck only in the documentation milestone, after the served-page record carries a structural reading for each of them | An entry under Composition not built ends by being built, not by being excused (DL-170) -> striking it while the only evidence is a guard that reads theme.py source repeats exactly the failure DL-169 amended the gate to catch -> the code milestone builds the structure and writes the record, and the documentation milestone strikes the three entries citing that record readings, leaving Column model, Table geometry and Detail rail standing |
| DL-191 | main stays one column at .wizard-content-width and the vertical ui.stepper stays: the Column model, Table geometry and Detail rail entries stand under Composition not built, the reconstruct page at / gains no structural verdict, and accessibility work is the re-run of the existing keyboard and announcement records with no NVDA fetched | The artboards draw a two-column main with a 400px detail rail over a five-track review grid, and porting them touches the review table keyboard contract Specs binds and carries responsive risk at every width -> a wave that ports the shell and the table at once cannot tell a shell regression from a table one when the record reads differs -> the shell silhouette is built and the three remaining structures stay open as written entries with this statement as the reason they are open, so a later wave that absorbs them does it deliberately |
| DL-192 | The band paint is declared on the .wizard-header-band and .wizard-footer-band classes app.py attaches to the ui.header and ui.footer elements; each band rule restates every declaration nicegui.css sets on .nicegui-header and .nicegui-footer that the artboard contradicts - alignment, gap, padding - and leaves the flex-direction row those elements already carry from that same sheet unrestated; the stylesheet reaches the document after nicegui own sheet through add_head_html | nicegui.css and the wizard stylesheet both declare single-class selectors at equal specificity, so the winner is source order -> add_head_html appends the wizard sheet to the head after the framework sheet, which gives the later declaration the cascade, but only for a declaration that is actually restated -> the band rules name their own classes rather than the framework ones and restate alignment, gap and padding explicitly, so nothing the artboard contradicts is left to a framework default, and the row direction lines 41-46 already set is not repeated because a restatement there would say what the framework says |
| DL-193 | The viewport-height rules key on the framework own layout and page-container classes rather than on a wizard- class, because app.py never constructs those elements | ui.header and ui.footer are inserted into a q-layout nicegui builds before any page function runs, so app.py has no element to attach a class to there -> a .wizard-shell class emitted by theme.py and named by no .classes() call fails tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py -> the height and overflow declarations key on .nicegui-layout and the page container directly, and every wizard- class the sheet emits is one app.py attaches |
| DL-194 | A Composition-not-built entry is struck only where the milestone record reads its structure built; a structure the record reads as partly refused keeps an entry naming what was refused and the value that shows it | An entry ends by being built rather than by being excused (DL-170) -> the card triplet may be partly refused by Quasar QStepper own markup, which is a measured outcome rather than a failure of the work -> the strike is conditioned on the reading, and a refusal is rewritten as a narrower entry citing the record rather than removed |
| DL-195 | The existing records keep their differs rows and the resolves guard reads the newest record that names a structure, so a structure built later stops naming an entry that no longer exists | tests/test_docs_browser_record_structure.py::test_every_structure_a_record_names_resolves_in_the_decision_log fails a differs row whose structure has no Composition-not-built entry, and four standing records carry differs rows for App shell, Card structure and Footer band -> editing those rows to keep the guard green would rewrite the transcript of a run, which DL-171 forbids -> the guard reads the latest record per structure, the older transcripts stand untouched, and the guard docstring records the mutation that proves the new reading fails |
| DL-196 | theme.py emits no .wizard-surface rule once every section carries the card triplet, and the pairing assertion in tests/test_gui_header_tabs.py reads the card box class against .wizard-content-width in its place | tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py fails a rule no call site names, and tests/test_gui_header_tabs.py asserts that some class string carries wizard-surface and that every such string also carries wizard-content-width -> leaving the rule with no call site fails the first guard and deleting it fails the second, so the two must move together -> the rule goes, the call sites carry .wizard-card, and the pairing assertion reads the card box instead |
| DL-197 | The keyboard and announcement records are re-run in the wave that follows the move of the advancing actions into the footer band, and the run reads focus order across the whole page rather than within the middle alone | The advancing control moves from the last child of a step to a child of the footer band, and nicegui places the header above the other layout elements in the DOM for accessibility -> tab order therefore changes for every page, which is exactly what the standing keyboard record measured and what the announcement cadence assumes about where focus is when a step advances -> the re-run is a milestone with its own record rather than a line in the shell record |

### Rejected Alternatives

| Alternative | Why Rejected |
|---|---|
| Option A: the typeface fix and the gate amendment alone | Shipped earlier in this session; it corrected the atoms and built no composition, so all six structures still read differs and the three Composition-not-built entries it was meant to close stayed open. (ref: DL-191) |
| Option C: the full artboard port - two-column main, the 400px detail rail, the five-track review grid | It carries responsive risk at every width and touches the review table's keyboard contract, which Specs binds; a record reading differs could not then be attributed to the shell rather than the table. (ref: DL-191) |
| Hand-rolled position:fixed bands instead of ui.header and ui.footer | Quasar's QLayout reserves space for its own header and footer and offsets the page container by their heights; a hand-rolled fixed band is laid over a container that reserved nothing, so the band overlaps content and every fix is a second offset chasing the first. (ref: DL-183) |
| A CDN link or an @import for any asset the shell needs | The whole emitted stylesheet is guarded against network hosts (DL-163), and the wizard runs under ui.run(native=True) where a CDN link resolves to nothing offline and reports nothing when it fails. (ref: DL-183) |

### Constraints

- C-001 [technical, user-specified] traktor_nml/README.md is the decision-log authority: one statement per decision, cited in prose as (DL-NNN). The high-water mark is DL-182, so entries minted by this work start at DL-183.
- C-002 [technical, user-specified] MUST: DL-069's nicegui boundary. Only app.py, file_picker.py and __main__.py import nicegui or pywebview; every other gui/ module stays importable under the system interpreter, which has no nicegui. Every CSS rule, class name and dimension this work introduces lives in theme.py, and app.py only names them.
- C-003 [technical, user-specified] MUST: each milestone closes with a served-page record in docs/, driven in a browser over HTTP, carrying a matches or differs verdict per named surface (DL-084) and a structural reading per surface beside the atom readings (DL-169). A surface carrying no structural reading fails the gate.
- C-004 [technical, user-specified] MUST: every new guard is proven to fail first, and its docstring records the specific mutation applied and the specific observed output, not a paraphrase.
- C-005 [technical, user-specified] MUST: traktor_nml/gui/app.py is 100% CRLF against an otherwise-LF tree; it is read and written with newline='' and no LF line is let in.
- C-006 [organizational, user-specified] MUST: documentation describes the code as it stands. No 'previously', 'now does', 'no longer' or 'added'.
- C-007 [organizational, user-specified] MUST: never cite a source for something it does not say.
- C-008 [organizational, user-specified] MUST: the three Composition-not-built entries this work closes (App shell, Card structure, Footer band) leave that section only once the structure is built and read off a served page; the other three stay.
- C-009 [technical, user-specified] MUST NOT: regenerate tests/baselines/manifest.json or the fixture/w002gatefix2 gate fixture.
- C-010 [technical, user-specified] MUST NOT: restore a file with git checkout; copy aside and restore from the copy.
- C-011 [technical, user-specified] MUST NOT: write into or delete build/ or dist/.
- C-012 [dependency, user-specified] MUST NOT: install anything into the system interpreter; the suite runs with the system interpreter, not .venv.
- C-013 [technical, user-specified] MUST NOT: reach a network host from the stylesheet; tests/test_gui_font_faces.py::test_the_whole_stylesheet_names_no_network_host guards the whole emitted sheet.
- C-014 [technical, user-specified] SHOULD: reuse the existing .wizard-content-width rule for the page column rather than introducing a second width owner.
- C-015 [technical, user-specified] SHOULD: keep the header's content - brand, divider, tab strip - exactly as _build_header renders it; this work changes where that row sits, not what it holds.
- C-016 [organizational, user-specified] Out of scope: the 400px detail rail (.det in Review.dc.html), the review table's grid geometry (.gr and its .th header row), the two-column main (1fr 400px), replacing the vertical ui.stepper with the artboards' own step rendering, accessibility work beyond re-running the existing keyboard and announcement records, fetching NVDA, and a structural verdict for the reconstruct page at / (DL-172).

### Known Risks

- **ui.header and ui.footer put the page into a QLayout whose middle region scrolls, and the prop names for removing Quasar's own elevation and padding are as named (confidence: medium). The prop names and the layout structure are recalled rather than read.**: M-001 begins by reading the installed nicegui 3.16.0 package - elements/header.py, elements/footer.py, client.py and static/nicegui.css - and the intents name the constructor flags and the framework classes found there; the served-page record then reads the rendered result rather than trusting either.
- **The artboards' 56px header band and the existing .wizard-header-bar row render at compatible heights, so moving the row into ui.header is a wrapping change rather than a re-layout (confidence: medium).**: M-001's record reads the computed height of the header band against 56px; where the row does not fit, the band height is the measured value and the difference is recorded as a divergence rather than absorbed into a matches verdict.
- **The card triplet can be applied to the stepper's existing steps without replacing ui.stepper (confidence: low). QStepper renders Quasar's own markup and may not admit the classes.**: The triplet lands on the sections each page composes; what the stepper refuses is read off the served page, quoted with the computed value that shows the refusal, and written as a narrowed Composition-not-built entry rather than assumed away (DL-186, DL-194).
- **The footer's advancing action can be the same widget object the step builds (confidence: low).**: The footer constructs the control and the step hands over the function it already calls, so no widget is re-parented and no duplicate state is held; the DOM order this produces changes tab order, which M-002 re-reads against the standing keyboard record (DL-187, DL-197).
- **M-001's record reads differs on App shell or Footer band, leaving M-002 and M-003 standing on a structure that was not built.**: M-002 and M-003 are separate waves for this reason: a differs reading stops the wave, the structure named in the reading keeps its Composition-not-built entry, and nothing is struck. The rollback is the copy-aside restore the constraints require, never git checkout.
- **The viewport-height shell leaves the middle unusable in a short or resized native pywebview window, where 56px and 64px bands eat a large share of the height.**: M-001's record is taken at two window heights and the middle's scrollHeight against clientHeight is read at each, so the short window is measured rather than assumed.
- **The .wizard-surface rule is withdrawn while tests/test_gui_header_tabs.py asserts that some class string carries it, so deleting the rule and leaving the guard fails the suite.**: The rule, the call sites and the pairing assertion move together in M-001, which owns all three files; the amended assertion reads .wizard-card and its docstring records the mutation that proves it fails (DL-196).

## Invisible Knowledge

### System

_page_chrome is the single chrome call both routes make, so the shell is built there or it forks. Read off the installed nicegui 3.16.0 package: client.py:110 builds q-layout with view="hhh lpr fff" wrapping q-page-container > q-page > div.nicegui-content; elements/header.py calls require_top_level_layout, takes bordered and elevated keyword flags defaulting to False, flips the view code to H and moves itself to index 0, and elements/footer.py is its mirror - so neither band can be nested and both must be built at page top level. static/nicegui.css gives .nicegui-header, .nicegui-footer and .nicegui-content display flex, flex-direction column, align-items flex-start and 1rem padding, so a band left at those defaults stacks its children vertically at the wrong padding. Quasar's fixed bands offset the page container but leave the document scrolling, so the middle owning the viewport is a height the stylesheet sets, not a side effect of the bands. app.py never constructs the q-layout element, which is why the height declarations key on the framework's own classes and every wizard- class the sheet emits is one a .classes() call names.

### Invariants

- Only app.py, file_picker.py and __main__.py import nicegui or pywebview; every CSS rule, class name and dimension lives in theme.py.
- traktor_nml/gui/app.py is 100% CRLF against an otherwise-LF tree.
- .wizard-content-width is the single owner of the page column's width; no band, footer or card rule sets a width.
- The @font-face blocks and the body rule keep their offsets: new rules are emitted after them and outside the quasar_importants layer block.
- The stylesheet names no network host; every face is served from the application's own origin.
- Every wizard- class theme.py emits is named by a .classes() call in app.py, and every class string at a call site is a literal.
- A milestone closes with a served-page record carrying a verdict per named surface and a structural reading per surface.
- Every guard added or amended is proven to fail first, with the mutation and the observed output in its docstring.
- A Composition-not-built entry leaves the section only where a record reads its structure built.
- A recorded reading is never edited; a later run adds its own record.

### Tradeoffs

- The bands are framework elements rather than hand-rolled fixed elements: Quasar reserves their space, at the cost of overriding nicegui's own band defaults in theme.py.
- The middle is given the viewport explicitly rather than left to Quasar's fixed-band behaviour, because a document that still scrolls looks the same until the page is long.
- The advancing control is constructed in the footer and the step hands over its function, rather than a widget re-parented or duplicated: one object and one enabled state, at the cost of a DOM order change that M-002 re-reads.
- The card triplet lands on the sections each page composes; what QStepper's own markup refuses is measured and named as a narrowed entry rather than worked around.
- main stays one column at .wizard-content-width and the vertical ui.stepper stays: Column model, Table geometry and Detail rail stay open by the statement that keeps them open (DL-191), because the two-column port carries responsive risk and touches the review table's keyboard contract.
- The reconstruct page at / gets the shell and the cards but no structural verdict, because DL-172 puts it outside the structural gate; its card reading is recorded as an atom reading.
- Accessibility work is the re-run of the standing keyboard and announcement records and nothing more; no screen reader is fetched.

## Milestones

### Milestone 1: The shell built: header band - scrolling middle - footer band - card triplet

**Files**: traktor_nml/gui/theme.py, traktor_nml/gui/app.py, tests/test_gui_shell.py, tests/test_gui_cards.py, tests/test_gui_header_tabs.py, docs/2026-09-05-wizard-shell-browser-record.md

**Requirements**:

- theme.py holds the 56px and 64px band heights beside CONTENT_WIDTH with the Main.dc.html spacing steps the bands and the cards measure at
- theme.py emits the shell rule set: the framework layout and page container at viewport height - both bands at their heights with 0 24px padding and row direction - the middle region owning overflow-y
- theme.py emits the four card rules and emits no .wizard-surface rule
- _page_chrome builds ui.header around the row _build_header renders with its brand and divider and tab strip unchanged
- _page_chrome builds ui.footer holding a note element at the left and an action group at the right and yields the middle container both routes enter
- both routes compose their body inside the middle container: the reconnect wizard and the reconstruct page at /
- every section both routes build is a card box holding a header band with its title and a padded body
- each reconnect step advancing action is constructed in the footer action group and invokes the function the step already calls
- the reconstruct page Preview and Write output controls are constructed in the same footer action group and invoke the functions that route already defines
- app.py names class strings only - no hex literal and no pixel value reaches a call site

**Acceptance Criteria**:

- pytest tests/ -q passes under the system interpreter with no nicegui installed
- tests/test_gui_view_boundary.py passes so the nicegui boundary holds
- the font-face ordering guard in tests/test_gui_font_faces.py passes with the shell and card rules inserted
- tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py passes for every shell class and every card class
- tests/test_gui_header_tabs.py pairs the card box class with .wizard-content-width and no rule beside .wizard-content-width sets a width
- traktor_nml/gui/app.py reads as 100 percent CRLF
- every guard added or amended in this milestone carries a docstring recording the exact mutation applied and the exact output observed
- the served-page record - named for its run date and ending -record.md so the suffix discovery in tests/test_docs_browser_record_structure.py finds it - carries a verdict per named surface and a structural reading for App shell and Card structure and Footer band
- that record quotes the computed height of each band - scrollHeight against clientHeight on the document and on the middle region - and the computed padding and border and title weight of at least one card
- that record states what the QStepper markup refuses with the computed value showing the refusal
- that record is taken at two window heights so the short-window case is read rather than assumed

**Tests**:

- tests/test_gui_shell.py
- tests/test_gui_cards.py
- tests/test_gui_header_tabs.py

#### Code Intent

- **CI-M-001-001** `traktor_nml/gui/theme.py::module constants`: HEADER_BAND_HEIGHT is 56px and FOOTER_BAND_HEIGHT is 64px, read off the .app grid-template-rows at Main.dc.html:15 that Confirm.dc.html, Results.dc.html and Review.dc.html also draw. They sit beside CONTENT_WIDTH with a comment naming the artboard line each is read from. Three spacing steps join the existing ones, each sourced to the line that states it: SPACE_22 and SPACE_20 from main at Main.dc.html:27, whose padding is 22px 24px 6px and whose grid gap is 20px, and SPACE_15 from .card-h at Main.dc.html:33 and .card-b at :35, whose padding is 11px 15px and 15px. SPACE_24, SPACE_12, SPACE_11, SPACE_10, SPACE_9 and SPACE_6 already carry the rest. (refs: DL-188)
- **CI-M-001-002** `traktor_nml/gui/theme.py::page_stylesheet`: A shell rule set is emitted after the existing rules, below the @font-face blocks and the body rule and outside the quasar_importants layer block, so the offsets tests/test_gui_font_faces.py asserts are undisturbed. nicegui's client.py:110-113 builds q-layout > q-page-container > q-page > div.nicegui-content, and Quasar's own sheet sets only .q-layout { min-height: 100% } on that chain, so all four carry a height: q-layout and q-page-container at the viewport height with the container at border-box so QLayout's own inline band padding leaves the middle the right space, q-page and nicegui-content at 100% with min-height 0 and no padding or gap of their own. The declarations key on those framework class names because app.py constructs none of the four elements and a wizard- class no call site names fails test_every_wizard_class_reaches_app_py (DL-193). .wizard-middle is the flex column that owns overflow-y auto and min-height 0, carrying Main.dc.html:27's own 22px 24px 6px padding and its 20px gap. nicegui.css lines 14-28 set align-items: flex-start, gap: 1rem and padding: 1rem on .nicegui-header and .nicegui-footer, and lines 41-46 give both flex-direction: row, so .wizard-header-band and .wizard-footer-band restate the alignment, the gap and the padding over what the framework sets and take the row direction it already gives them; the wizard sheet reaches the head after the framework sheet, so the restatement wins at equal specificity (DL-192). Each band carries its own band height, the SURFACE_2 ground and a one pixel BORDER rule - border-bottom on the header, border-top on the footer - as .hd and .ft draw them. .wizard-footer-note carries TYPE_12_5 in TEXT_MUTED with the SPACE_9 gap .ft-note draws; .wizard-footer-actions is a flex row at SPACE_10 with flex none, as .ft-act draws it. No rule in the set declares a width, so .wizard-content-width stays the single width owner. Every value is an existing constant or one of the three added beside CONTENT_WIDTH. (refs: DL-184, DL-185, DL-188, DL-192, DL-193)
- **CI-M-001-003** `traktor_nml/gui/app.py::_page_chrome`: After the colours, dark mode and stylesheet are applied, _page_chrome builds a ui.header with bordered=False and elevated=False carrying .wizard-header-band and wraps the _build_header call, so the brand, divider and tab strip render inside the band with their own row and content-width classes unchanged. A ui.footer built with the same two flags carries .wizard-footer-band and holds a note element classed .wizard-footer-note and a row classed .wizard-footer-actions. Both are constructed at page top level, which is what require_top_level_layout in nicegui demands, and _page_chrome is the first call on both routes. _page_chrome hands back one chrome object holding the note element, the action row and the middle container - an element classed .wizard-middle - and the route enters that container with a with statement, so the body lands inside the middle region rather than beside it by caller discipline. (refs: DL-183, DL-184, DL-185)
- **CI-M-001-004** `traktor_nml/gui/app.py::index`: The reconnect page composes inside the middle container the chrome object yields. The live regions and the vertical ui.stepper sit there at .wizard-content-width, which stays the single width owner. _WizardPageState declares footer_note, footer_actions and footer_groups beside its other attributes, and index() fills the first two from the chrome object before building the steps. Each step builder opens a row in state.footer_actions at its own top level, unconditionally, and registers that row with the sentence its note carries in state.footer_groups under the step's own title, so every key exists before the first step change; a step whose contents re-render - the Write step, whose render() runs again on every refresh - clears and refills that standing row rather than opening a second one, so the band never accumulates rows and never lacks the active step's key. A state with nothing to act on empties the row rather than leaving a stale control in it. index() binds stepper.on_value_change to a function that shows the active step's group and sets the note from it, and calls that function once at build time. The control therefore exists once, in the band, and its enabled state is held once (DL-187). app.py imports NamedTuple beside Callable and Optional, which _PageChrome needs. The control's place in the DOM sets the tab order, which is why the keyboard and announcement records are re-read in the wave that follows (DL-197). (refs: DL-187, DL-197)
- **CI-M-001-005** `tests/test_gui_shell.py::module`: Guards reading theme.page_stylesheet() text under the system interpreter. They assert that the stylesheet carries a rule naming HEADER_BAND_HEIGHT and one naming FOOTER_BAND_HEIGHT; that each band rule restates the align-items: flex-start and the 1rem padding nicegui.css sets on .nicegui-header and .nicegui-footer, and does not restate the row direction those elements already carry; that the middle rule declares overflow-y auto and min-height 0 while q-layout, q-page-container, q-page and nicegui-content each carry the bounded height the middle's scroll rests on, with border-box on the page container; and that no shell, band, footer or card rule declares a width, so .wizard-content-width stays the only width owner. No guard here asserts that a wizard- class reaches app.py: tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py already sweeps every class the sheet defines. Each guard docstring records the exact mutation applied to prove it fails - the constant withheld, the declaration deleted, a width planted - and the exact assertion output observed. No guard asserts a rendered height or a scroll position: what the browser laid out belongs to the record (DL-189). (refs: DL-189, DL-192, DL-193)
- **CI-M-001-006** `docs/2026-09-05-wizard-shell-browser-record.md::document`: A served-page record of one run, named for its run date and ending -browser-record.md, which is one of the suffixes tests/test_docs_browser_record_structure.py already discovers, written in the shape docs/2026-09-05-plex-paint-record.md takes: what was opened, the atom readings with a verdict each, then a Structural verdicts section carrying all six structures. App shell, Card structure and Footer band carry their readings - the computed height of the header band against 56px and of the footer band against 64px, the computed height of q-page-container, q-page and nicegui-content that the middle's scroll rests on, document.scrollingElement scrollHeight against clientHeight showing the document does not scroll, the same pair on the middle region showing it does, the computed padding, border, radius and title weight of at least one card on each route including one inside a ui.step, and each of the four steps' advancing control found in the band with the band holding exactly the active step's group. The run is taken at two window heights, so the short window is read rather than assumed. Where the QStepper markup refuses part of the triplet, the record quotes the computed value showing the refusal and names what the stepper composes instead, which is what the narrowed Composition-not-built entry is written from (DL-194). The reconstruct page reading is recorded as an atom reading: that route carries no structural verdict, because DL-172 puts it outside the structural gate. Column model, Table geometry and Detail rail carry the verdict this run measured them at. A closing section states what the run does not establish. The run is served with native=False over HTTP so the page is drivable, which is how docs/2026-09-05-plex-paint-record.md was taken; the shipped entry point runs native=True and shares _page_chrome, so the difference is the window rather than the route. (refs: DL-189, DL-185, DL-194)
- **CI-M-001-007** `traktor_nml/gui/theme.py::page_stylesheet card rules`: Four card rules join the shell rule set and the .wizard-surface rule is withdrawn, because every section carries the triplet and a rule no call site names fails test_every_wizard_class_reaches_app_py (DL-196). .wizard-card carries the SURFACE_2 ground, a one pixel BORDER and RADIUS_XL, as .card draws it at Main.dc.html:32. .wizard-card-head is a flex row at align-items center and justify-content space-between with a SPACE_12 gap, SPACE_11 SPACE_15 padding and a one pixel BORDER bottom rule, as .card-h draws it at :33. .wizard-card-title is weight 600 at TYPE_13 with no margin, as .card-t draws it at :34. .wizard-card-body is a flex column at SPACE_15 padding with a SPACE_12 gap, as .card-b draws it at :35. No card rule declares a width. Every colour and radius is a constant this module already holds. (refs: DL-186, DL-188)
- **CI-M-001-008** `traktor_nml/gui/app.py::section builders`: Each section the reconnect wizard and the reconstruct page build is a .wizard-card box holding a .wizard-card-head with its .wizard-card-title and a .wizard-card-body, in place of one .wizard-surface applied to a whole column; no call site carries .wizard-surface. On the reconnect route each of the four ui.step bodies is one card; on the reconstruct route each heading the column already carries becomes a card title and the controls under it become that card's body. Opening a card is a with statement, so every line of the region it encloses shifts one indent level - a nested def keeps its meaning, because a with block opens no scope of its own. The class strings are literals at the call site, which is what tests/test_gui_theme.py::test_every_classes_call_expands_to_literals reads - DL-188 forbids a dimension or a colour at a call site, not a class name. The card box class string carries .wizard-content-width wherever the column it replaces did. Where the QStepper markup refuses part of the triplet, what it refuses is measured on the served page and kept as a narrowed Composition-not-built entry rather than claimed built (DL-194). (refs: DL-186, DL-194)
- **CI-M-001-009** `tests/test_gui_cards.py::module`: Guards asserting that theme.page_stylesheet() carries .wizard-card with the SURFACE_2 ground, the one pixel BORDER and RADIUS_XL; .wizard-card-head with SPACE_11 SPACE_15 padding and the one pixel BORDER bottom rule; .wizard-card-title at weight 600 and TYPE_13 with no margin; and .wizard-card-body at SPACE_15 padding with a SPACE_12 column gap - the values .card, .card-h, .card-t and .card-b measure at Main.dc.html:32-35. A further guard asserts that no .wizard-surface rule is emitted and that no call site names it, which is the direction test_every_wizard_class_reaches_app_py cannot hold; that the four card class names reach app.py is left to that existing sweep. Each docstring records the mutation proven to fail and the output observed. (refs: DL-186, DL-189, DL-196)
- **CI-M-001-010** `tests/test_gui_header_tabs.py::the surface pairing assertion`: The assertion that pairs a box class with .wizard-content-width reads .wizard-card, the class the sections carry, so the pairing it exists to hold - a box that sets no width of its own sitting inside the one column owner - is asserted against the class the page actually carries. The header-bar assertions beside it are untouched. The docstring records the mutation applied to prove the amended assertion fails and the output observed (DL-196). (refs: DL-196, DL-189)
- **CI-M-001-011** `traktor_nml/gui/app.py::reconstruct`: The reconstruct route at / composes against the same chrome object _page_chrome yields as the reconnect route does: it enters the middle container with a with statement, and its column sits there at .wizard-content-width. Its two primary controls, Preview and Write output, are constructed in the footer action group and invoke the preview and write_output functions the page already defines, so they sit in the band rather than as the last children of the column; the footer note carries the sentence the page wants said about what the action does. The route keeps its own holders, its conflict rendering and its file-picker calls exactly as they stand - what moves is where the column and the two controls sit. DL-172 keeps this route out of the structural gate, which decides what a record may verdict about it and not whether it shares the shell both routes are built from (DL-191). (refs: DL-183, DL-187, DL-191)

#### Code Changes

**CC-M-001-001** (traktor_nml/gui/theme.py) - implements CI-M-001-001

**Code:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ the spacing steps and CONTENT_WIDTH
 SPACE_6 = "6px"
 SPACE_16 = "16px"
 SPACE_24 = "24px"
+# Main.dc.html:27's main padding (22px 24px 6px) and its 20px grid gap -
+# the page region's own inset and the gap between the boxes it holds.
+SPACE_22 = "22px"
+SPACE_20 = "20px"
+# Main.dc.html:33's .card-h padding (11px 15px) and :35's .card-b
+# padding (15px) - the inset both card regions measure at.
+SPACE_15 = "15px"
 # The width the page's content occupies. One value because the header
 # band and the content column below it are one column: the band's ground
 # and rule end where the card's edge is, so the brand mark sits over the
 # card's own first column rather than over the page margin.
 CONTENT_WIDTH = "64rem"
+# Main.dc.html:15's .app grid-template-rows (56px 1fr 64px), the same
+# three rows Confirm.dc.html, Results.dc.html and Review.dc.html draw.
+# The bands are fixed and the middle row takes what is left, which is
+# what makes the middle the scroll owner rather than the document.
+HEADER_BAND_HEIGHT = "56px"
+FOOTER_BAND_HEIGHT = "64px"
 RADIUS_SM = "4px"
 RADIUS_MD = "5px"

```

**Documentation:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ the module docstring
 """Specs' measured token set: traktor_nml/gui/app.py's colour, type,
 spacing and radius values, held once so a hex or a pixel size is never
 repeated at a call site (DL-078). Imports no nicegui, so the pytest
 interpreter reads it directly (DL-078, DL-085).
+
+The shell the pages compose against measures here too: the two band
+heights and the spacing steps the header band, the middle region, the
+footer band and the card triplet are drawn at. This module is the one a
+guard under the system interpreter can read, so a dimension written at
+an app.py call site would be invisible to every guard and to the hex-
+and size-scanning sweeps in tests/test_gui_theme.py; app.py names class
+strings and this module holds the values behind them (DL-069, DL-188).
 """
@@ the spacing steps
+# The steps below carry no meaning of their own beyond the artboard
+# line each comment names: a step is a measured value, and the rule that
+# spends it says which region it insets (DL-188).
 SPACE_22 = "22px"

```


**CC-M-001-002** (traktor_nml/gui/theme.py) - implements CI-M-001-002

**Code:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ def page_stylesheet() -> str: the tail of the emitted sheet
 .q-toggle__thumb {{ background: {SWITCH_KNOB}; }}
 .q-toggle__track {{ background: {SWITCH_TRACK}; }}
 .body--dark, .body--dark .q-stepper, .body--dark .q-field__native, .body--dark .q-field__control {{ color: {TEXT}; }}
+/* Main.dc.html:15's .app: a header band, a middle that takes what is
+   left, and a footer band, at the viewport's height.
+
+   nicegui's client.py:110-113 builds q-layout > q-page-container >
+   q-page > div.nicegui-content, and Quasar's own sheet sets
+   .q-layout {{ min-height: 100% }} and nothing else on that chain, so
+   every element between the viewport and the middle needs a bounded
+   height before the middle can scroll rather than grow. QLayout writes
+   the two band heights onto q-page-container as inline padding, which
+   border-box turns into exactly the space the middle is left with. The
+   four selectors are Quasar's and nicegui's own: app.py constructs none
+   of these elements, and a wizard- class no call site names fails
+   tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py
+   (DL-193). */
+.q-layout {{ height: 100vh; }}
+.q-page-container {{ box-sizing: border-box; height: 100vh; overflow: hidden; }}
+.q-page {{ height: 100%; }}
+.nicegui-content {{ height: 100%; min-height: 0; padding: 0; gap: 0; }}
+/* Main.dc.html:27's main: the page region's own 22px 24px 6px inset and
+   its 20px gap, owning the scroll its parents have bounded. */
+.wizard-middle {{ flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: {SPACE_22} {SPACE_24} {SPACE_6}; gap: {SPACE_20}; display: flex; flex-direction: column; }}
+/* nicegui.css lines 14-28 set align-items: flex-start, gap: 1rem and
+   padding: 1rem on .nicegui-header and .nicegui-footer, and lines 41-46
+   set both to flex-direction: row. Each band therefore restates the
+   alignment, the gap and the padding, and takes the row direction the
+   framework already gives it. The wizard sheet reaches the head after
+   the framework sheet, so the restatement wins at equal specificity
+   (DL-192). Main.dc.html:16's .hd and :30's .ft carry the SURFACE_2
+   ground and a one pixel rule on the edge each faces the middle
+   across. */
+.wizard-header-band {{ align-items: center; justify-content: space-between; gap: {SPACE_24}; padding: 0 {SPACE_24}; height: {HEADER_BAND_HEIGHT}; background: {SURFACE_2}; border-bottom: 1px solid {BORDER}; }}
+.wizard-footer-band {{ align-items: center; justify-content: space-between; gap: {SPACE_24}; padding: 0 {SPACE_24}; height: {FOOTER_BAND_HEIGHT}; background: {SURFACE_2}; border-top: 1px solid {BORDER}; }}
+/* Main.dc.html:31's .ft-note and :32's .ft-act. */
+.wizard-footer-note {{ margin: 0; font-size: {TYPE_12_5}; color: {TEXT_MUTED}; display: flex; align-items: center; gap: {SPACE_9}; }}
+.wizard-footer-actions {{ display: flex; align-items: center; gap: {SPACE_10}; flex: none; }}
 """

```

**Documentation:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ def page_stylesheet() -> str:
 def page_stylesheet() -> str:
     """The wizard's stylesheet as one string, every colour and size
     drawn from this module's own constants rather than a literal
-    (DL-078)."""
+    (DL-078).
+
+    The order of the sheet is load-bearing at two points. The
+    @font-face blocks font_face_rules() returns stand at the head,
+    unlayered and above the body rule that names the family, which is
+    the offset relationship
+    tests/test_gui_font_faces.py::test_the_face_blocks_precede_the_body_rule_that_names_the_family
+    holds; the shell, band, footer and card rules are emitted after that
+    rule and outside the layer block that follows it. The sheet itself
+    reaches the head through add_head_html, after nicegui's own sheet,
+    so a band rule restating a declaration nicegui.css sets on the same
+    element wins at equal specificity (DL-192).
+    """

```


**CC-M-001-003** (traktor_nml/gui/theme.py) - implements CI-M-001-007

**Code:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ def page_stylesheet() -> str: the box rules
 .q-page {{ background: {GROUND}; color: {TEXT}; }}
-.wizard-surface {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: {RADIUS_XL}; }}
+/* Main.dc.html:32-35's .card, .card-h, .card-t and .card-b: a bordered
+   box with its own header band, its title, and a padded body. Every
+   section a page builds carries the triplet, so the single-box rule the
+   triplet replaces has no call site left, and a rule no call site names
+   fails test_every_wizard_class_reaches_app_py (DL-196). No card rule
+   declares a width: .wizard-content-width stays the one width owner. */
+.wizard-card {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: {RADIUS_XL}; }}
+.wizard-card-head {{ display: flex; align-items: center; justify-content: space-between; gap: {SPACE_12}; padding: {SPACE_11} {SPACE_15}; border-bottom: 1px solid {BORDER}; }}
+.wizard-card-title {{ font-weight: 600; font-size: {TYPE_13}; margin: 0; }}
+.wizard-card-body {{ padding: {SPACE_15}; display: flex; flex-direction: column; gap: {SPACE_12}; }}
 .wizard-header {{ background: {SURFACE_2}; border-bottom: 1px solid {BORDER}; font-size: {TYPE_14}; }}
 .wizard-section-head {{ background: {SURFACE_3}; border-bottom: 1px solid {BORDER}; font-size: {TYPE_12}; font-weight: 600; }}

```

**Documentation:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ the card rules
 /* Main.dc.html:32-35's .card, .card-h, .card-t and .card-b: a bordered
    box with its own header band, its title, and a padded body. Every
-   section a page builds carries the triplet, so the single-box rule the
-   triplet replaces has no call site left, and a rule no call site names
-   fails test_every_wizard_class_reaches_app_py (DL-196). No card rule
-   declares a width: .wizard-content-width stays the one width owner. */
+   section a page composes itself carries the triplet, which leaves the
+   single-box rule the triplet replaces without a call site, and a rule
+   no call site names fails test_every_wizard_class_reaches_app_py
+   (DL-196). A step's own header band is Quasar's QStepper markup and
+   is not one of those sections: the four ui.step call sites carry
+   .wizard-section-head, .wizard-header, .wizard-hd-alt and
+   .wizard-sec-alt, and those rules stand in this sheet beside the
+   triplet. No card rule declares a width: .wizard-content-width stays
+   the one width owner. */
+/* The four rules are one structure: a box that carries the ground, the
+   border and the radius, a head that carries the inset and the rule
+   below it, a title inside that head, and a body that carries its own
+   inset and the gap between the controls it holds. What the QStepper
+   markup refuses of the triplet is named in
+   docs/2026-09-05-wizard-shell-browser-record.md by the computed value
+   that shows the refusal, and stands as a narrowed entry under
+   "Composition not built" in traktor_nml/README.md (DL-186, DL-194).
+   What the browser computes for these four rules is read on a served
+   page for the same reason: a guard reading these declarations is true
+   whether or not the layout landed (DL-189). */
 .wizard-card {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: {RADIUS_XL}; }}

```


**CC-M-001-004** (traktor_nml/gui/app.py) - implements CI-M-001-003

**Code:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -34,7 +34,7 @@ the module imports
 import argparse
 import threading
 import time
 import traceback
 from pathlib import Path
-from typing import Callable, Optional
+from typing import Callable, NamedTuple, Optional

 from nicegui import app as nicegui_app, run, ui
@@ -76,10 +76,17 @@ class _WizardPageState: def __init__
         self.progress_announcer = announce.ProgressAnnouncer()
         self.polite_region = None
         self.assertive_region = None
         self.detail_open: bool = False
+        # The footer band's note and its action group, held here for the
+        # same reason every other page-wide element is: a step builder
+        # reaches them through the one object it already carries, and a
+        # step's advancing control is built in the band rather than
+        # duplicated there (DL-187).
+        self.footer_note = None
+        self.footer_actions = None
+        # One action group per step, keyed by the step's own title, with
+        # the sentence that step's note carries. Every step is built up
+        # front, so every group exists before the first step change; the
+        # step change decides which one is shown rather than which one
+        # is built.
+        self.footer_groups: dict[str, tuple] = {}
@@ -181,14 +188,49 @@ def _page_chrome(active_route: str) -> None:
-def _page_chrome(active_route: str) -> None:
+class _PageChrome(NamedTuple):
+    """What _page_chrome hands its caller: the middle container the
+    route enters, and the two footer elements the route fills.
+
+    One object because the three are built together: a route taking the
+    middle alone would compose a page whose footer band still occupies
+    its own height with nothing in it.
+    """
+
+    middle: ui.element
+    footer_note: ui.label
+    footer_actions: ui.row
+
+
+def _page_chrome(active_route: str) -> _PageChrome:
     """The colour, dark-mode and stylesheet preamble every page in this
     module applies, followed by the header the active route selects a
     tab in. Shared so a second route cannot drift from the wizard's own
     theme (DL-078, DL-085) and so the tab set cannot fork: both pages
-    build their header from this one call site (DL-134)."""
+    build their header from this one call site (DL-134).
+
+    ui.header and ui.footer put the page into Quasar's own QLayout,
+    which writes each band's height onto q-page-container as padding; a
+    hand-rolled fixed band fights that reservation instead of using it
+    (DL-183). Both are constructed at page top level, which is what
+    nicegui's require_top_level_layout demands, and this function is the
+    first call on both routes. The middle container is handed back
+    rather than entered here, so a route's body lands inside the
+    scrolling region by a with statement rather than by caller
+    discipline (DL-185).
+    """
     # Quasar's primary set carries theme.ACTION; dark/dark-page are fed
     # from the ground and surface tokens so Quasar's own dark components
     # land on the measured surfaces rather than a framework default.
     _mount_fonts()
     ui.colors(primary=theme.ACTION, dark=theme.SURFACE_2, dark_page=theme.GROUND)
     ui.dark_mode(True)
     ui.add_head_html(f"<style>{theme.page_stylesheet()}</style>")
-    _build_header(active_route)
+    # bordered and elevated off: the rule and the shadow Quasar draws
+    # are not the ones Main.dc.html:16 and :30 draw, and the band's own
+    # rule in theme.py is (DL-183). The header row _build_header renders
+    # keeps its own classes and its own content: what differs is where
+    # the row sits.
+    with ui.header(bordered=False, elevated=False).classes("wizard-header-band"):
+        _build_header(active_route)
+    middle = ui.element("div").classes("wizard-middle")
+    with ui.footer(bordered=False, elevated=False).classes("wizard-footer-band"):
+        footer_note = ui.label("").classes("wizard-footer-note")
+        footer_actions = ui.row().classes("wizard-footer-actions")
+    return _PageChrome(middle, footer_note, footer_actions)

```

**Documentation:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ class _WizardPageState: the class docstring
 class _WizardPageState:
     """One browser tab's worth of wizard state: the argparse Namespace
     the setup step builds, the scan result once it exists, the operator's
-    WizardState decisions, and the row the review table has focused."""
+    WizardState decisions, the row the review table has focused, and the
+    footer band's note and action row.
+
+    The band's two elements live here for the same reason the live
+    regions do: a step builder reaches them through the one object it
+    already carries. footer_groups maps a step's own title to the pair
+    (action row, note sentence) that step registers, which is what lets
+    the step change decide which group the band shows rather than which
+    group exists (DL-187).
+    """
@@ class _PageChrome: the field list
     middle: ui.element
     footer_note: ui.label
     footer_actions: ui.row
+    # middle is the container a route enters; footer_note and
+    # footer_actions are the two halves of the band Main.dc.html:29-31
+    # draws - .ft, holding .ft-note's sentence at the left and .ft-act's
+    # controls at the right.

```


**CC-M-001-005** (traktor_nml/gui/app.py) - implements CI-M-001-004

**Code:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -253,20 +253,55 @@ def index() -> None:
     @ui.page("/reconnect")
     def index() -> None:
         # Quasar's primary set carries theme.ACTION; dark/dark-page are
         # fed from the ground and surface tokens so Quasar's own dark
         # components land on the measured surfaces rather than a
         # framework default (DL-078, DL-085).
-        _page_chrome("/reconnect")
+        chrome = _page_chrome("/reconnect")

         state = _WizardPageState()

-        with ui.column().classes("gap-4 wizard-surface wizard-content-width"):
-            # Created once per page load, before any step that announces into them.
-            state.polite_region, state.assertive_region = build_live_regions()
-            stepper = ui.stepper().props("vertical").classes("w-full")
-            with stepper:
-                _build_setup_step(state, stepper)
-                _build_scan_step(state, stepper)
-                _build_review_step(state, stepper)
-                _build_write_step(state, stepper)
+        # Each step builder registers its own action group and note
+        # sentence in state.footer_groups, so the control that advances
+        # a step exists once, in the band, and its enabled state is held
+        # once (DL-187). Its place in the DOM is what sets the tab
+        # order, which is why the keyboard and the announcement records
+        # are read again (DL-197).
+        state.footer_note = chrome.footer_note
+        state.footer_actions = chrome.footer_actions
+
+        with chrome.middle:
+            with ui.column().classes("gap-4 wizard-content-width"):
+                # Created once per page load, before any step that announces into them.
+                state.polite_region, state.assertive_region = build_live_regions()
+                stepper = ui.stepper().props("vertical").classes("w-full")
+                with stepper:
+                    _build_setup_step(state, stepper)
+                    _build_scan_step(state, stepper)
+                    _build_review_step(state, stepper)
+                    _build_write_step(state, stepper)
+
+        def show_footer_for_step() -> None:
+            """The band carries the active step's own group and note.
+
+            Every group is built up front, alongside the step that owns
+            it, so this decides which one is visible rather than which
+            one exists - the same shape state.step_refreshers already
+            takes for a step's own render.
+            """
+            active = stepper.value
+            for name, (group, note) in state.footer_groups.items():
+                group.set_visibility(name == active)
+                if name == active:
+                    state.footer_note.set_text(note)
+
+        stepper.on_value_change(lambda _: show_footer_for_step())
+        show_footer_for_step()

```

**Documentation:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ def index() -> None: the chrome call
+        # The three regions are built in the order header, middle,
+        # footer, which is the order they read in the DOM and therefore
+        # the order the tab ring walks them in; that order is read on a
+        # served page in
+        # docs/2026-09-06-wizard-focus-order-browser-record.md rather
+        # than asserted here (DL-189, DL-197).
         chrome = _page_chrome("/reconnect")

```


**CC-M-001-006** (traktor_nml/gui/app.py) - implements CI-M-001-008

**Code:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -272,5 +272,18 @@ def _build_setup_step(state, stepper) -> None: card opener; every remaining line of this builder shifts one indent level into the card body
 def _build_setup_step(state: _WizardPageState, stepper: ui.stepper) -> None:
     with ui.step("Set up").classes("wizard-section-head"):
-        ui.label("My playlists are broken: the collection they point at moved.")
-        old_input_display = ui.label("No collection selected").classes("font-mono wizard-body-15 wizard-subtle-1")
-        old_input_holder: dict[str, Optional[Path]] = {"path": None}
+        # Main.dc.html:32-35 draws each section as a card: a bordered
+        # box, a header band carrying the section's title, and a padded
+        # body. The class strings are literals at the call site, which is
+        # what
+        # tests/test_gui_theme.py::test_every_classes_call_expands_to_literals
+        # reads - DL-188 keeps a dimension or a colour out of a call site,
+        # not a class name.
+        with ui.element("section").classes("wizard-card wizard-content-width"):
+            with ui.element("div").classes("wizard-card-head"):
+                ui.label("Your Traktor collection").classes("wizard-card-title")
+            with ui.element("div").classes("wizard-card-body"):
+                ui.label("My playlists are broken: the collection they point at moved.")
+                old_input_display = ui.label("No collection selected").classes(
+                    "font-mono wizard-body-15 wizard-subtle-1"
+                )
+                old_input_holder: dict[str, Optional[Path]] = {"path": None}
@@ -424,7 +438,15 @@ def _build_setup_step(state, stepper) -> None: the Continue control
         # own footer. wizard-control-primary carries the action blue and
         # Review.dc.html:36's own ink together, which is why the
         # constructor passes color=None: Quasar's own bg-primary and
         # text-white are !important in the layer it orders last, and
         # text-white holds the label at 2.31:1 against the blue where the
         # artboard's ink measures 8.2:1 (DL-086 rung one).
-        ui.button("Continue", on_click=go_to_scan, color=None).classes("wizard-control wizard-control-primary")
+        with state.footer_actions:
+            with ui.row().classes("wizard-footer-actions") as group:
+                ui.button("Continue", on_click=go_to_scan, color=None).classes(
+                    "wizard-control wizard-control-primary"
+                )
+        state.footer_groups["Set up"] = (
+            group,
+            "Continue reads the collection and moves on to the scan.",
+        )
@@ -433,14 +447,27 @@ def _build_scan_step(state, stepper) -> None: card opener; every remaining line of this builder shifts one indent level into the card body
 def _build_scan_step(state: _WizardPageState, stepper: ui.stepper) -> None:
     with ui.step("Scan").classes("wizard-header"):
-        progress = ui.linear_progress(value=0).props("instant-feedback")
-        progress_label = ui.label("Not started").classes("wizard-body-12-5 wizard-action")
-        # Scanning.dc.html:88's scan counter and :98-106's three tile
-        # values are the step's numeric displays, and on_progress is
-        # the one live source for all four: the counter reads the
-        # artboard's 'indexed / total files', and the tiles the
-        # matched / needs-review / no-match counts among the reviews
-        # scanned so far. They carry the display, title and status
-        # colour tokens onto real Scan-step elements rather than onto
-        # the page title or the Write control (DL-078). All four start
-        # empty because no count exists before the first progress
-        # callback.
+        # Main.dc.html:32-35 draws each section as a card: a bordered
+        # box, a header band carrying the section's title, and a padded
+        # body. The class strings are literals at the call site, which is
+        # what
+        # tests/test_gui_theme.py::test_every_classes_call_expands_to_literals
+        # reads - DL-188 keeps a dimension or a colour out of a call site,
+        # not a class name.
+        with ui.element("section").classes("wizard-card wizard-content-width"):
+            with ui.element("div").classes("wizard-card-head"):
+                ui.label("Scanning your music folders").classes("wizard-card-title")
+            with ui.element("div").classes("wizard-card-body"):
+                progress = ui.linear_progress(value=0).props("instant-feedback")
+                progress_label = ui.label("Not started").classes(
+                    "wizard-body-12-5 wizard-action"
+                )
+                # Scanning.dc.html:88's scan counter and :98-106's three
+                # tile values are the step's numeric displays, and
+                # on_progress is the one live source for all four: the
+                # counter reads the artboard's 'indexed / total files',
+                # and the tiles the matched / needs-review / no-match
+                # counts among the reviews scanned so far. They carry the
+                # display, title and status colour tokens onto real
+                # Scan-step elements rather than onto the page title or
+                # the Write control (DL-078). All four start empty because
+                # no count exists before the first progress callback.
@@ -483,6 +512,21 @@ def _build_scan_step(state, stepper) -> None: the scan controls
-        cancel_button = ui.button("Cancel", color=None).classes("wizard-control")
-        # This step's one advancing action, primary for the same reason
-        # and by the same mechanism as the Set up step's own Continue.
-        start_button = ui.button("Start scan", color=None).classes("wizard-control wizard-control-primary")
-        review_matches_button = ui.button("Review matches", on_click=lambda: go_to_review(), color=None).classes("wizard-control")
-        review_matches_button.disable()
+        # This step's three controls are built in the band together: the
+        # cancel, the start and the forward control read and set each
+        # other's enabled state, so splitting them across the step and the
+        # band would hold that state in two places (DL-187).
+        with state.footer_actions:
+            with ui.row().classes("wizard-footer-actions") as group:
+                cancel_button = ui.button("Cancel", color=None).classes("wizard-control")
+                # This step's one advancing action, primary for the same
+                # reason and by the same mechanism as the Set up step's own
+                # Continue.
+                start_button = ui.button("Start scan", color=None).classes(
+                    "wizard-control wizard-control-primary"
+                )
+                review_matches_button = ui.button(
+                    "Review matches", on_click=lambda: go_to_review(), color=None
+                ).classes("wizard-control")
+        review_matches_button.disable()
+        state.footer_groups["Scan"] = (
+            group,
+            "Review matches opens the rows the scan found.",
+        )
@@ -825,9 +872,22 @@ def _build_review_step(state, stepper) -> None: card opener; every remaining line of this builder shifts one indent level into the card body
 def _build_review_step(state: _WizardPageState, stepper: ui.stepper) -> None:
     with ui.step("Review").classes("wizard-hd-alt"):
-        if state.cancelled:
-            ui.label("Scan cancelled - no review table.").classes("text-warning")
-            return
-
-        filter_row = ui.row().classes("gap-2")
-        table_container = ui.column().classes("w-full gap-1")
-        comparison_container = ui.column().classes("w-full")
+        # Main.dc.html:32-35 draws each section as a card: a bordered
+        # box, a header band carrying the section's title, and a padded
+        # body. The class strings are literals at the call site, which is
+        # what
+        # tests/test_gui_theme.py::test_every_classes_call_expands_to_literals
+        # reads - DL-188 keeps a dimension or a colour out of a call site,
+        # not a class name.
+        # The review table's own grid geometry stays as it stands - the
+        # Table geometry entry is outside this work's scope (DL-191).
+        with ui.element("section").classes("wizard-card wizard-content-width"):
+            with ui.element("div").classes("wizard-card-head"):
+                ui.label("What the scan matched").classes("wizard-card-title")
+            with ui.element("div").classes("wizard-card-body"):
+                if state.cancelled:
+                    ui.label("Scan cancelled - no review table.").classes("text-warning")
+                    return
+
+                filter_row = ui.row().classes("gap-2")
+                table_container = ui.column().classes("w-full gap-1")
+                comparison_container = ui.column().classes("w-full")
@@ -1076,5 +1130,15 @@ def _build_review_step(state, stepper) -> None: the step's controls
-            ui.button("Back", on_click=stepper.previous, color=None).classes("wizard-control")
-            # This step's one advancing action. wizard-control-primary
-            # carries the blue and the artboard's own ink together, so the
-            # constructor passes color=None (DL-086 rung one).
-            ui.button("Continue to write", on_click=go_to_write, color=None).classes("wizard-control wizard-control-primary")
+        with state.footer_actions:
+            with ui.row().classes("wizard-footer-actions") as group:
+                ui.button("Back", on_click=stepper.previous, color=None).classes(
+                    "wizard-control"
+                )
+                # This step's one advancing action. wizard-control-primary
+                # carries the blue and the artboard's own ink together, so
+                # the constructor passes color=None (DL-086 rung one).
+                ui.button("Continue to write", on_click=go_to_write, color=None).classes(
+                    "wizard-control wizard-control-primary"
+                )
+        state.footer_groups["Review"] = (
+            group,
+            "Continue to write carries your decisions to the write step.",
+        )
@@ -1085,15 +1148,39 @@ def _build_write_step(state, stepper) -> None: card opener; every remaining line of this builder shifts one indent level into the card body
 def _build_write_step(state: _WizardPageState, stepper: ui.stepper) -> None:
     with ui.step("Write").classes("wizard-sec-alt"):
+        # This step's own action group, built and registered here for
+        # the same reason every step is built up front in index(): the
+        # key has to exist before the first step change, and render()
+        # below re-enters on every refresh, so a group built there would
+        # be a second row in the band each time. render() fills this one
+        # rather than making another (DL-187).
+        with state.footer_actions:
+            group = ui.row().classes("wizard-footer-actions")
+        state.footer_groups["Write"] = (
+            group,
+            "Write output writes a new file, asking once more first.",
+        )
-        container = ui.column().classes("w-full")
-
-        def render() -> None:
-            """Rebuilds this step's entire contents from state, rather
-            than toggling a pre-built visibility flag: at build time
-            state.scan_result is still None (every step is built once,
-            up front, in index()), so 'Nothing to write.' is the only
-            content that can exist yet, and the reconnect-count label,
-            refusal label, write button, confirm dialog and output log
-            below do not exist until a scan has actually landed a
-            result. state.cancelled is re-checked here too, not
-            assumed false, so a cancelled scan still lands on 'Nothing
-            to write.' on every refresh, not only the first one."""
+        # Main.dc.html:32-35 draws each section as a card: a bordered
+        # box, a header band carrying the section's title, and a padded
+        # body. The class strings are literals at the call site, which is
+        # what
+        # tests/test_gui_theme.py::test_every_classes_call_expands_to_literals
+        # reads - DL-188 keeps a dimension or a colour out of a call site,
+        # not a class name.
+        with ui.element("section").classes("wizard-card wizard-content-width"):
+            with ui.element("div").classes("wizard-card-head"):
+                ui.label("Writing the repaired collection").classes("wizard-card-title")
+            with ui.element("div").classes("wizard-card-body"):
+                container = ui.column().classes("w-full")
+
+                def render() -> None:
+                    """Rebuilds this step's entire contents from state,
+                    rather than toggling a pre-built visibility flag: at
+                    build time state.scan_result is still None (every step
+                    is built once, up front, in index()), so 'Nothing to
+                    write.' is the only content that can exist yet, and the
+                    reconnect-count label, refusal label, write button,
+                    confirm dialog and output log below do not exist until a
+                    scan has actually landed a result. state.cancelled is
+                    re-checked here too, not assumed false, so a cancelled
+                    scan still lands on 'Nothing to write.' on every refresh,
+                    not only the first one."""
@@ -1100,5 +1175,10 @@ def _build_write_step(state, stepper) -> None: render()'s no-result branch
-            container.clear()
-            if state.cancelled or state.scan_result is None:
-                with container:
-                    ui.label("Nothing to write.")
-                return
+                    container.clear()
+                    if state.cancelled or state.scan_result is None:
+                        # The band carries this step's controls, so a state
+                        # with nothing to write empties the group rather
+                        # than leaving the controls of a run that no longer
+                        # has a result beside 'Nothing to write.'
+                        group.clear()
+                        with container:
+                            ui.label("Nothing to write.")
+                        return
@@ -1150,3 +1225,15 @@ def _build_write_step(state, stepper) -> None: the write controls
-                with ui.row().classes("wizard-control-group"):
-                    ui.button("Back to review", on_click=stepper.previous, color=None).classes("wizard-control")
-                    write_button = ui.button("Write output", color=None).props("tabindex=0").classes("wizard-control wizard-control-primary")
+                    # The write control's own dialog stays where it is built,
+                    # inside the step's refresh: the dialog is a child of the
+                    # page, not of the band, and only the control that opens it
+                    # is built in the band (DL-187). The group itself is the
+                    # one registered at the head of this builder, cleared and
+                    # refilled, so a refresh replaces this step's controls
+                    # rather than adding a second row beside them.
+                    group.clear()
+                    with group:
+                        ui.button(
+                            "Back to review", on_click=stepper.previous, color=None
+                        ).classes("wizard-control")
+                        write_button = ui.button("Write output", color=None).props(
+                            "tabindex=0"
+                        ).classes("wizard-control wizard-control-primary")

```

**Documentation:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ def _build_setup_step(state, stepper) -> None:
 def _build_setup_step(state: _WizardPageState, stepper: ui.stepper) -> None:
+    """The first step: the collection to repair, chosen through the file
+    picker, and the Continue that reads it and moves to the scan.
+
+    The step's card holds what the operator reads and acts on; its
+    advancing control is built in the footer band and registered under
+    this step's own title, so the control exists once and its enabled
+    state is held once (DL-186, DL-187).
+    """
     with ui.step("Set up").classes("wizard-section-head"):
@@ def _build_scan_step(state, stepper) -> None:
 def _build_scan_step(state: _WizardPageState, stepper: ui.stepper) -> None:
+    """The scan step: the progress feed, the counter and the three status
+    tiles, all fed from the one on_progress callback.
+
+    Its three controls - cancel, start and the forward control - are
+    built together in the footer band, because they read and set each
+    other's enabled state and splitting them across the step and the
+    band would hold that state in two places (DL-187).
+    """
     with ui.step("Scan").classes("wizard-header"):
@@ def _build_review_step(state, stepper) -> None:
 def _build_review_step(state: _WizardPageState, stepper: ui.stepper) -> None:
+    """The review step: the filter chips, the table of scanned rows and
+    the comparison the focused row opens.
+
+    The table's rows are laid out by the classes this builder names, not
+    by the five-track grid the artboard draws; that difference is the
+    Table geometry entry under 'Composition not built' in
+    traktor_nml/README.md, and the entry states the reason it is open.
+    The step's Back and Continue to write are built in the footer band
+    (DL-187).
+    """
     with ui.step("Review").classes("wizard-hd-alt"):
@@ def _build_write_step(state, stepper) -> None:
 def _build_write_step(state: _WizardPageState, stepper: ui.stepper) -> None:
+    """The write step: what the run will write, and the control that
+    writes it after asking once more.
+
+    This builder registers its footer group before render() first runs,
+    because render() re-enters on every refresh and a group built there
+    would be a second row in the band each time; render() clears and
+    refills the one group instead (DL-187).
+    """
     with ui.step("Write").classes("wizard-sec-alt"):

```


**CC-M-001-007** (traktor_nml/gui/app.py) - implements CI-M-001-011

**Code:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -1335,6 +1335,6 @@ def reconstruct() -> None:
     @ui.page("/")
     def reconstruct() -> None:
-        _page_chrome("/")
+        chrome = _page_chrome("/")
 
         base_holder: dict = {"path": None}
         source_holder: list = []
@@ -1350,19 +1350,33 @@ def reconstruct() -> None: the first card; every line it encloses shifts one indent level
         decisions = conflict_model.ConflictDecisions()
 
-        with ui.column().classes("gap-4 wizard-surface wizard-content-width"):
-            ui.label(
-                "My playlists kept their names but lost their contents; an older "
-                "collection still has them."
-            )
-
-            ui.label("The collection to repair").classes("wizard-body-13 font-semibold")
-            with ui.row().classes("items-center wizard-control-group"):
-                base_display = ui.label("No collection selected").classes(
-                    "font-mono wizard-body-15 wizard-subtle-1 grow"
-                )
-                base_remove = ui.button(
-                    "Remove",
-                    on_click=lambda: remove_base(),
-                    color=None,
-                ).classes("wizard-control wizard-tag-action-outline wizard-body-12")
-            base_remove.set_visibility(False)
+        # This route composes against the shell both pages are built
+        # from. DL-172 decides what a record may verdict about it, not
+        # which shell it is built from (DL-191). Its holders, its
+        # conflict rendering and its file-picker calls stand as they are:
+        # what differs is where the column and the two primary controls
+        # sit, and that each heading and the controls under it are a card
+        # rather than one box around the whole column.
+        with chrome.middle, ui.column().classes("gap-4 wizard-content-width"):
+            ui.label(
+                "My playlists kept their names but lost their contents; an older "
+                "collection still has them."
+            )
+
+            # Main.dc.html:32-35's .card, .card-h, .card-t and .card-b. The
+            # heading each section already carries becomes the card title,
+            # and every line from here to the next card opener shifts one
+            # indent level into the body.
+            with ui.element("section").classes("wizard-card wizard-content-width"):
+                with ui.element("div").classes("wizard-card-head"):
+                    ui.label("The collection to repair").classes("wizard-card-title")
+                with ui.element("div").classes("wizard-card-body"):
+                    with ui.row().classes("items-center wizard-control-group"):
+                        base_display = ui.label("No collection selected").classes(
+                            "font-mono wizard-body-15 wizard-subtle-1 grow"
+                        )
+                        base_remove = ui.button(
+                            "Remove",
+                            on_click=lambda: remove_base(),
+                            color=None,
+                        ).classes("wizard-control wizard-tag-action-outline wizard-body-12")
+                    base_remove.set_visibility(False)
@@ -1410,9 +1428,13 @@ def reconstruct() -> None: the second card; every line it encloses shifts one indent level
-            ui.label("Collections to take playlists from").classes(
-                "wizard-body-13 font-semibold"
-            )
-            source_list = ui.column().classes("gap-1")
-
-            def draw_sources() -> None:
-                """Redraws the list from source_holder, so the rows and the
-                holder the run reads say the same thing after a removal."""
-                source_list.clear()
+            with ui.element("section").classes("wizard-card wizard-content-width"):
+                with ui.element("div").classes("wizard-card-head"):
+                    ui.label("Collections to take playlists from").classes(
+                        "wizard-card-title"
+                    )
+                with ui.element("div").classes("wizard-card-body"):
+                    source_list = ui.column().classes("gap-1")
+
+                    def draw_sources() -> None:
+                        """Redraws the list from source_holder, so the rows
+                        and the holder the run reads say the same thing after
+                        a removal."""
+                        source_list.clear()
@@ -1462,8 +1489,13 @@ def reconstruct() -> None: the third card; every line it encloses shifts one indent level
-            ui.label(
-                "These are read, never modified. Several are folded in the order added."
-            ).classes("wizard-body-12 wizard-faint")
-
-            output_input = ui.input("Output collection path").classes("w-full")
-
-            async def choose_output() -> None:
-                directory = await pick_file_or_folder(directories_only=True)
+            with ui.element("section").classes("wizard-card wizard-content-width"):
+                with ui.element("div").classes("wizard-card-head"):
+                    ui.label("Where the output goes").classes("wizard-card-title")
+                with ui.element("div").classes("wizard-card-body"):
+                    ui.label(
+                        "These are read, never modified. Several are folded in "
+                        "the order added."
+                    ).classes("wizard-body-12 wizard-faint")
+
+                    output_input = ui.input("Output collection path").classes("w-full")
+
+                    async def choose_output() -> None:
+                        directory = await pick_file_or_folder(directories_only=True)
@@ -1483,17 +1517,21 @@ def reconstruct() -> None: the fourth card; every line it encloses shifts one indent level
-            ui.label("Where the collections disagree").classes(
-                "wizard-body-13 font-semibold"
-            )
-            # The run-wide fallback, carrying the splice subcommand's own
-            # two choices onto assemble_output's on_conflict parameter. Its
-            # default settles nothing, so a divergent group stops the run
-            # and is shown as a row of its own below.
-            conflict_choice = ui.select(
-                {
-                    None: "Ask me - stop and show every conflicting track",
-                    "keep-first": "keep-first - the collection being repaired wins",
-                    "keep-last": "keep-last - the last source added wins",
-                },
-                value=None,
-            ).classes("w-full")
-
-            report = ui.column().classes("w-full gap-1")
+            with ui.element("section").classes("wizard-card wizard-content-width"):
+                with ui.element("div").classes("wizard-card-head"):
+                    ui.label("Where the collections disagree").classes(
+                        "wizard-card-title"
+                    )
+                with ui.element("div").classes("wizard-card-body"):
+                    # The run-wide fallback, carrying the splice subcommand's
+                    # own two choices onto assemble_output's on_conflict
+                    # parameter. Its default settles nothing, so a divergent
+                    # group stops the run and is shown as a row of its own
+                    # below.
+                    conflict_choice = ui.select(
+                        {
+                            None: "Ask me - stop and show every conflicting track",
+                            "keep-first": "keep-first - the collection being repaired wins",
+                            "keep-last": "keep-last - the last source added wins",
+                        },
+                        value=None,
+                    ).classes("w-full")
+
+                    report = ui.column().classes("w-full gap-1")
@@ -1673,8 +1720,6 @@ def reconstruct() -> None: the Preview control leaves the column
                         ui.label(f"{name} - {count} entries").classes(
                             "font-mono wizard-body-13 wizard-subtle-1"
                         )
 
-            ui.button("Preview", on_click=preview, color=None).classes("wizard-control")
-
             async def write_output() -> None:
                 """Writes the output the held run produced, or names why it
@@ -1708,5 +1753,16 @@ def reconstruct() -> None: the Write output control moves to the band
                 ui.notify(f"Written to {output_path}", type="positive")
 
-            ui.button("Write output", on_click=write_output, color=None).classes(
-                "wizard-control wizard-control-primary"
-            )
+        # Main.dc.html:30's .ft holds the screen's advancing action, so
+        # both primary controls are constructed in the band. Each invokes
+        # the function this page defines above - a with statement opens no
+        # scope of its own, so both names are in reach here - which is how
+        # each control exists once and its enabled state is held once
+        # (DL-187).
+        chrome.footer_note.set_text(
+            "Preview reads the collections; Write output writes a new file."
+        )
+        with chrome.footer_actions:
+            ui.button("Preview", on_click=preview, color=None).classes("wizard-control")
+            ui.button("Write output", on_click=write_output, color=None).classes(
+                "wizard-control wizard-control-primary"
+            )

```

**Documentation:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ def reconstruct() -> None:
     @ui.page("/")
     def reconstruct() -> None:
+        """The reconstruct page: the collection to repair, the
+        collections to take playlists from, where the output goes, and
+        what to do where they disagree.
+
+        It composes against the same shell as the wizard - the same
+        bands, the same middle, the same card triplet - and its two
+        primary controls are built in the footer band. DL-172 decides
+        what a served-page record may verdict about this route, not
+        which shell it is built from (DL-191).
+        """
         chrome = _page_chrome("/")

```


**CC-M-001-008** (tests/test_gui_shell.py) - implements CI-M-001-005

**Code:**

```diff
--- /dev/null
+++ b/tests/test_gui_shell.py
@@ -0,0 +1,147 @@
+"""Guards the shell rules theme.py emits, read as source text under the
+system interpreter, which has no nicegui.
+
+What a guard here asserts is a rule's presence and content. What it
+cannot assert is that the browser gave the layout the viewport:
+theme.FONT_SANS named IBM Plex throughout the period the page painted
+Segoe UI, so a guard that reads a name is true in exactly the broken
+state. The rendered height and the scroll owner belong to the
+served-page record (DL-189).
+
+That every .wizard-* class the sheet defines reaches app.py is already
+swept by tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py,
+so no guard here repeats it.
+"""
+
+from __future__ import annotations
+
+import re
+
+from traktor_nml.gui import theme
+
+
+def _rule(selector: str) -> str:
+    """One rule's declaration block, by selector."""
+    match = re.search(
+        re.escape(selector) + r"\s*\{([^}]*)\}", theme.page_stylesheet()
+    )
+    assert match is not None, f"the stylesheet emits no {selector} rule"
+    return match.group(1)
+
+
+def test_each_band_rule_carries_its_band_height():
+    """The header band measures at HEADER_BAND_HEIGHT and the footer band
+    at FOOTER_BAND_HEIGHT, the two fixed rows Main.dc.html:15 draws.
+
+    Mutation: the height declaration was deleted from the
+    .wizard-header-band rule and this guard rerun. Observed:
+        AssertionError: .wizard-header-band declares no height
+        assert 'height: 56px' in ' align-items: center; justify-content:
+        space-between; gap: 24px; padding: 0 24px; background: #17191C;
+        border-bottom: 1px solid #2A2E32; '
+    """
+    assert f"height: {theme.HEADER_BAND_HEIGHT}" in _rule(".wizard-header-band"), (
+        ".wizard-header-band declares no height"
+    )
+    assert f"height: {theme.FOOTER_BAND_HEIGHT}" in _rule(".wizard-footer-band"), (
+        ".wizard-footer-band declares no height"
+    )
+
+
+def test_each_band_restates_the_alignment_and_padding_the_framework_sets():
+    """The block at nicegui.css lines 14-28 sets display: flex,
+    flex-direction: column, align-items: flex-start, gap:
+    var(--nicegui-default-gap) and padding: var(--nicegui-default-padding)
+    on a selector list that includes .nicegui-header and .nicegui-footer -
+    the elements ui.header and ui.footer build - and the block at lines
+    41-46 then overrides those two selectors to flex-direction: row. So the alignment and the gap
+    are what survive for a band to restate, and the row direction is
+    already the framework's own; a band rule restating it would be
+    redundant with the sheet it sits after (DL-192).
+
+    Mutation: 'align-items: center;' was deleted from the
+    .wizard-footer-band rule and this guard rerun. Observed:
+        AssertionError: .wizard-footer-band does not restate the
+        alignment the framework sets to flex-start
+        assert 'align-items: center' in ' justify-content:
+        space-between; gap: 24px; padding: 0 24px; height: 64px;
+        background: #17191C; border-top: 1px solid #2A2E32; '
+
+    Mutation: 'flex-direction: row;' was planted in the
+    .wizard-header-band rule and this guard rerun. Observed:
+        AssertionError: .wizard-header-band restates flex-direction,
+        which nicegui.css already sets to row for this element
+        assert 'flex-direction' not in ' display: flex; flex-direction:
+        row; align-items: center; justify-content: space-between; gap:
+        24px; padding: 0 24px; height: 56px; background: #17191C;
+        border-bottom: 1px solid #2A2E32; '
+    """
+    for selector in (".wizard-header-band", ".wizard-footer-band"):
+        block = _rule(selector)
+        assert "align-items: center" in block, (
+            f"{selector} does not restate the alignment the framework sets "
+            "to flex-start"
+        )
+        assert f"padding: 0 {theme.SPACE_24}" in block, (
+            f"{selector} does not restate the padding the framework sets to 1rem"
+        )
+        assert "flex-direction" not in block, (
+            f"{selector} restates flex-direction, which nicegui.css already "
+            "sets to row for this element"
+        )
+
+
+def test_the_middle_owns_the_scroll_and_every_parent_bounds_its_height():
+    """nicegui's client.py builds q-layout > q-page-container > q-page >
+    div.nicegui-content, and Quasar sets only .q-layout { min-height:
+    100% } on that chain, so the middle can scroll rather than grow only
+    if every element between the viewport and it carries a bounded
+    height. app.py constructs none of those four elements, which is why
+    the height rules key on the framework's own class names (DL-193).
+
+    Mutation: the .q-page rule was deleted from page_stylesheet(),
+    leaving q-page unbounded between the page container and the content,
+    and this guard rerun. Observed:
+        AssertionError: the stylesheet emits no .q-page rule
+        assert None is not None
+    """
+    middle = _rule(".wizard-middle")
+    assert "overflow-y: auto" in middle, (
+        ".wizard-middle declares no overflow-y, so the document is the scroll owner"
+    )
+    assert "min-height: 0" in middle
+    assert "height: 100vh" in _rule(".q-layout")
+    page_container = _rule(".q-page-container")
+    assert "height: 100vh" in page_container
+    # QLayout writes each band's height onto this element as inline
+    # padding, so the middle is left the right space only under
+    # border-box.
+    assert "box-sizing: border-box" in page_container
+    assert "height: 100%" in _rule(".q-page")
+    content = _rule(".nicegui-content")
+    assert "height: 100%" in content
+    assert "min-height: 0" in content
+
+
+def test_no_shell_or_card_rule_declares_a_width():
+    """.wizard-content-width stays the single width owner, so no band,
+    middle, footer or card rule declares a width of its own.
+
+    Mutation: 'max-width: 64rem;' was planted in the .wizard-middle rule
+    and this guard rerun. Observed:
+        AssertionError: .wizard-middle declares a width, so
+        .wizard-content-width is not the only width owner
+        assert 'width' not in ' flex: 1 1 auto; min-height: 0;
+        overflow-y: auto; padding: 22px 24px 6px; gap: 20px; display:
+        flex; flex-direction: column; max-width: 64rem; '
+    """
+    for selector in (
+        ".wizard-header-band", ".wizard-footer-band", ".wizard-middle",
+        ".wizard-footer-note", ".wizard-footer-actions",
+        ".wizard-card", ".wizard-card-head", ".wizard-card-title",
+        ".wizard-card-body",
+    ):
+        assert "width" not in _rule(selector), (
+            f"{selector} declares a width, so .wizard-content-width is not "
+            "the only width owner"
+        )

```

**Documentation:**

```diff
--- a/tests/test_gui_shell.py
+++ b/tests/test_gui_shell.py
@@ the module docstring
 That every .wizard-* class the sheet defines reaches app.py is already
 swept by tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py,
 so no guard here repeats it.
+
+The reading that says the shell works is in
+docs/2026-09-05-wizard-shell-browser-record.md: the two band heights the
+browser computed, and the scrollHeight/clientHeight pair on the document
+and on the middle region that says which of the two scrolled (DL-084,
+DL-169).
 """
@@ def _rule(selector: str) -> str:
 def _rule(selector: str) -> str:
-    """One rule's declaration block, by selector."""
+    """One rule's declaration block, by selector.
+
+    Read out of page_stylesheet()'s return value rather than out of
+    theme.py's source, so a constant renamed or a value interpolated
+    from somewhere else is still read as the sheet emits it.
+    """

```


**CC-M-001-009** (tests/test_gui_cards.py) - implements CI-M-001-009

**Code:**

```diff
--- /dev/null
+++ b/tests/test_gui_cards.py
@@ -0,0 +1,95 @@
+"""Guards the card triplet: the four rules theme.py emits for
+Main.dc.html:32-35's .card, .card-h, .card-t and .card-b.
+
+What the browser laid out - the computed padding, the border, the radius
+- belongs to the served-page record (DL-189); what these guards hold is
+each rule's content. That the four class names reach app.py is already
+swept by
+tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py, so no
+guard here repeats it; what that sweep cannot see is a rule the sheet
+keeps emitting with no call site left, which the last guard holds.
+"""
+
+from __future__ import annotations
+
+import re
+from pathlib import Path
+
+from traktor_nml.gui import theme
+
+_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"
+
+
+def _rule(selector: str) -> str:
+    match = re.search(
+        re.escape(selector) + r"\s*\{([^}]*)\}", theme.page_stylesheet()
+    )
+    assert match is not None, f"the stylesheet emits no {selector} rule"
+    return match.group(1)
+
+
+def test_the_card_box_carries_the_ground_border_and_radius():
+    """Main.dc.html:32's .card.
+
+    Mutation: RADIUS_XL was replaced by RADIUS_LG in the .wizard-card
+    rule and this guard rerun. Observed:
+        AssertionError: assert 'border-radius: 8px' in ' background:
+        #17191C; border: 1px solid #2A2E32; border-radius: 6px; '
+    """
+    block = _rule(".wizard-card")
+    assert f"background: {theme.SURFACE_2}" in block
+    assert f"border: 1px solid {theme.BORDER}" in block
+    assert f"border-radius: {theme.RADIUS_XL}" in block
+
+
+def test_the_card_head_carries_its_padding_and_its_rule():
+    """Main.dc.html:33's .card-h.
+
+    Mutation: the border-bottom declaration was deleted from the
+    .wizard-card-head rule and this guard rerun. Observed:
+        AssertionError: assert 'border-bottom: 1px solid #2A2E32' in
+        ' display: flex; align-items: center; justify-content:
+        space-between; gap: 12px; padding: 11px 15px; '
+    """
+    block = _rule(".wizard-card-head")
+    assert f"padding: {theme.SPACE_11} {theme.SPACE_15}" in block
+    assert f"border-bottom: 1px solid {theme.BORDER}" in block
+
+
+def test_the_card_title_carries_its_weight_size_and_no_margin():
+    """Main.dc.html:34's .card-t.
+
+    Mutation: 'margin: 0;' was deleted from the .wizard-card-title rule
+    and this guard rerun. Observed:
+        AssertionError: assert 'margin: 0' in ' font-weight: 600;
+        font-size: 13px; '
+    """
+    block = _rule(".wizard-card-title")
+    assert "font-weight: 600" in block
+    assert f"font-size: {theme.TYPE_13}" in block
+    assert "margin: 0" in block
+
+
+def test_the_card_body_carries_its_padding_and_column_gap():
+    """Main.dc.html:35's .card-b.
+
+    Mutation: SPACE_12 was replaced by SPACE_8 in the .wizard-card-body
+    gap and this guard rerun. Observed:
+        AssertionError: assert 'gap: 12px' in ' padding: 15px; display:
+        flex; flex-direction: column; gap: 8px; '
+    """
+    block = _rule(".wizard-card-body")
+    assert f"padding: {theme.SPACE_15}" in block
+    assert "flex-direction: column" in block
+    assert f"gap: {theme.SPACE_12}" in block
+
+
+def test_no_single_box_rule_survives_beside_the_triplet():
+    """Every section carries the triplet, so the single-box rule the
+    triplet replaces has no call site and is not emitted (DL-196). This
+    is the direction test_every_wizard_class_reaches_app_py cannot hold:
+    that sweep skips a class listed in its own
+    _KNOWN_UNATTACHED_CLASSES, and it reads the sheet for classes
+    app.py lacks rather than the reverse.
+
+    Mutation: the .wizard-surface rule was restored to
+    page_stylesheet() and this guard rerun. Observed:
+        AssertionError: the stylesheet emits a .wizard-surface rule no
+        call site names
+    """
+    assert ".wizard-surface" not in theme.page_stylesheet(), (
+        "the stylesheet emits a .wizard-surface rule no call site names"
+    )
+    assert "wizard-surface" not in _APP_PY.read_text(encoding="utf-8")

```

**Documentation:**

```diff
--- a/tests/test_gui_cards.py
+++ b/tests/test_gui_cards.py
@@ def _rule(selector: str) -> str:
 def _rule(selector: str) -> str:
+    """One rule's declaration block, by selector, read out of the sheet
+    page_stylesheet() emits rather than out of theme.py's source."""
     match = re.search(
@@ the app.py path constant
 _APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"
+# app.py is read as text here for one reason only: the last guard holds
+# that no call site names the single-box class, which is a direction the
+# class-reach sweep in tests/test_gui_theme.py does not walk (DL-196).

```


**CC-M-001-010** (tests/test_gui_header_tabs.py) - implements CI-M-001-010

**Code:**

```diff
--- a/tests/test_gui_header_tabs.py
+++ b/tests/test_gui_header_tabs.py
@@ def test_the_header_band_and_every_content_column_share_one_width_class():
 def test_the_header_band_and_every_content_column_share_one_width_class():
     """The header row's class string and the class string of every
-    content column - the ones carrying wizard-surface - all carry
+    content box - the ones carrying wizard-card - all carry
     wizard-content-width, which is what makes the band's edges the
-    card's edges. Read out of app.py's own source because the two
-    columns are built inside page functions the recorder above does
+    card's edges. Read out of app.py's own source because the boxes
+    are built inside page functions the recorder above does
     not enter.

-    Mutation: the reconstruct page's column was given back
+    Mutation: the reconstruct page's card box was given
     'max-w-5xl mx-auto' in place of 'wizard-content-width' and this
     guard rerun. Observed:
-        AssertionError: class strings carrying wizard-surface without
-        wizard-content-width: ['gap-4 wizard-surface max-w-5xl
-        mx-auto']
+        AssertionError: class strings carrying wizard-card without
+        wizard-content-width: ['wizard-card max-w-5xl mx-auto']
     """
     source = APP_PATH.read_text(encoding="utf-8")
@@ the box pairing assertion
     assert all("wizard-content-width" in text.split() for text in header), (
         f"the header band carries no width class: {header}"
     )
-    surfaces = [text for text in literals if "wizard-surface" in text.split()]
-    assert surfaces, "no class string carries wizard-surface"
-    adrift = [text for text in surfaces if "wizard-content-width" not in text.split()]
+    boxes = [text for text in literals if "wizard-card" in text.split()]
+    assert boxes, "no class string carries wizard-card"
+    adrift = [text for text in boxes if "wizard-content-width" not in text.split()]
     assert adrift == [], (
-        f"class strings carrying wizard-surface without wizard-content-width: {adrift}"
+        f"class strings carrying wizard-card without wizard-content-width: {adrift}"
     )

```

**Documentation:**

```diff
--- a/tests/test_gui_header_tabs.py
+++ b/tests/test_gui_header_tabs.py
@@ def test_the_header_band_and_every_content_column_share_one_width_class():
     content box - the ones carrying wizard-card - all carry
     wizard-content-width, which is what makes the band's edges the
     card's edges. Read out of app.py's own source because the boxes
     are built inside page functions the recorder above does
     not enter.
+
+    The card box is the class this pairing reads because it is the box
+    each section a page composes itself carries.
+    .wizard-content-width stays the only rule declaring a width, which
+    tests/test_gui_shell.py::test_no_shell_or_card_rule_declares_a_width
+    holds from the stylesheet's side.

```


**CC-M-001-011** (docs/2026-09-05-wizard-shell-browser-record.md) - implements CI-M-001-006

**Code:**

```diff
--- /dev/null
+++ b/docs/2026-09-05-wizard-shell-browser-record.md
@@ -0,0 +1,72 @@
+# Wizard shell - served-page record
+
+The name ends `-browser-record.md`, which is one of the suffixes
+`tests/test_docs_browser_record_structure.py` discovers a record by, so
+this record falls under the gate with no edit to that rule. The shape
+follows `docs/2026-09-05-plex-paint-record.md`: what was opened, the
+atom readings, then the structural verdicts.
+
+## What was opened
+
+Served from `.venv` with `native=False` over HTTP, so the page is
+drivable from a browser; the shipped entry point runs `native=True` and
+enters the same `_page_chrome`, so the difference is the window rather
+than the route. Both routes are read, and the run is taken at two window
+heights so the short window is read rather than assumed. The exact
+nicegui and Quasar versions, the URL, the two viewport sizes and the
+commit are stated here.
+
+## Atom readings
+
+| Surface | Expected | Read | Verdict |
+|---|---|---|---|
+
+One row per atom the run measured, each carrying `matches` or `differs`.
+The reconstruct page's readings are atom readings: DL-172 puts that
+route outside the structural gate, so it carries no structural verdict.
+
+## Structural verdicts
+
+All six structures, one row each, with a `matches` or `differs` verdict.
+A surface carrying no structural reading fails the gate (DL-169).
+
+| Structure | Artboard | Read | Verdict |
+|---|---|---|---|
+
+- **App shell** - the computed height of the header band against `56px`
+  and of the footer band against `64px`; `document.scrollingElement`
+  `scrollHeight` against `clientHeight`, showing the document does not
+  scroll; the same pair on the middle region, showing it does; and the
+  computed height of `.q-page-container`, `.q-page` and
+  `.nicegui-content`, which is the chain the middle's scroll rests on.
+  Both window heights.
+- **Card structure** - the computed padding, border, radius and title
+  weight of at least one card on each route, against
+  `Main.dc.html:32-35`, including one card inside a `ui.step`. Where the
+  QStepper markup refuses part of the triplet, the computed value
+  showing the refusal is quoted and what the stepper composes instead is
+  named; that quotation is what a narrowed "Composition not built" entry
+  is written from (DL-194).
+- **Footer band** - the note at the left and the action group at the
+  right, the advancing control of each of the four wizard steps found in
+  the band rather than in the step, and the band holding exactly the
+  active step's group.
+- **Column model**, **Table geometry**, **Detail rail** - the verdict
+  this run measured each at.
+
+## What this run does not establish
+
+Named explicitly: no screen reader was run; the focus order and the
+keyboard map are read in
+`docs/2026-09-06-wizard-focus-order-browser-record.md`; the two window
+heights are the only two read.

```

**Documentation:**

```diff
--- a/docs/2026-09-05-wizard-shell-browser-record.md
+++ b/docs/2026-09-05-wizard-shell-browser-record.md
@@ under "What was opened"
+A record is a transcript of one run: the rows state what that run read,
+and a later run that reads something else is a record of its own rather
+than an edit here (DL-171). The verdict rows are digested in
+`tests/test_docs_browser_record_structure.py`, so an edit to a reading
+fails that guard.

```


**CC-M-001-012** (tests/CLAUDE.md)

**Documentation:**

```diff
--- a/tests/CLAUDE.md
+++ b/tests/CLAUDE.md
@@ the Files table
+| `test_gui_shell.py` | The shell rules `theme.py` emits, read out of `page_stylesheet()`'s return value: each band's height against `HEADER_BAND_HEIGHT`/`FOOTER_BAND_HEIGHT`, each band restating the alignment, gap and padding `nicegui.css` sets on `.nicegui-header`/`.nicegui-footer` and leaving the row direction that sheet already gives them, the middle owning `overflow-y` with every element between the viewport and it carrying a bounded height, and no shell rule declaring a width | Changing a band, the middle region, the viewport-height chain, or which module owns the page column's width |
+| `test_gui_cards.py` | The four card rules against `Main.dc.html:32-35`: the box's ground, border and radius, the head's padding and rule, the title's weight, size and zero margin, the body's padding and column gap, and that the single-box rule the triplet replaces is left in neither the sheet nor a call site. The step-header rules the four `ui.step` call sites carry are a separate set and are not read here | Changing a card rule, or the class a section's box carries |

```


**CC-M-001-013** (docs/CLAUDE.md)

**Documentation:**

```diff
--- a/docs/CLAUDE.md
+++ b/docs/CLAUDE.md
@@ the Files table
+| `2026-09-05-wizard-shell-browser-record.md` | DL-084 served-page record for the shell: the two band heights the browser computed, the `scrollHeight`/`clientHeight` pair on the document and on the middle region saying which of the two scrolls, the height chain the middle's scroll rests on, one card's computed padding, border, radius and title weight on each route, and the footer holding each step's advancing control; read at two window heights, with structural verdicts on all six structures | Checking what the shell run measured, or what the `QStepper` markup refused of the card triplet |

```


### Milestone 2: Focus order - the keyboard map - the announcements - read again after the actions move to the footer

**Files**: tests/test_gui_keymap.py, tests/test_gui_announce.py, docs/2026-09-06-wizard-focus-order-browser-record.md

**Requirements**:

- the keyboard record and the announcement record are re-run against the served shell and written as one record
- the run reads focus order across the whole page - header band then middle then footer band - rather than within the middle alone
- every key in the Specs keyboard map is exercised with the advancing control in the footer
- the announcement cadence is read where a step advances from a control that no longer sits inside the step
- no accessibility work beyond re-running these records is done and NVDA is not fetched

**Acceptance Criteria**:

- pytest tests/ -q passes under the system interpreter|docs/2026-09-06-wizard-focus-order-browser-record.md carries a verdict per named surface and a structural reading per surface as the gate requires|the record states the tab order it read - element by element - against the order the standing keyboard record read|every key in the Specs keyboard map carries a verdict in the record|any guard amended in tests/test_gui_keymap.py or tests/test_gui_announce.py carries a docstring recording the mutation applied and the output observed|no NVDA run appears in the record and no accessibility change beyond the re-read is made

**Tests**:

- tests/test_gui_keymap.py
- tests/test_gui_announce.py

#### Code Intent

- **CI-M-002-001** `tests/test_gui_keymap.py::module`: The keyboard guards read the advancing control where it is built - in each step's own group inside the footer action row - so a key bound to advancing resolves against the control the footer holds rather than against a child of the step. One guard reads all four wizard steps by name, so it fails while any one step's control is still built inline rather than passing on another route's group. Any guard whose assertion moves carries a docstring recording the exact mutation applied to prove it fails and the exact output observed. The Specs keyboard map itself is unchanged: this reads the same map against a page whose DOM order differs (DL-197). (refs: DL-197, DL-189)
- **CI-M-002-002** `docs/2026-09-06-wizard-focus-order-browser-record.md::document`: A served-page record of the run that reads focus order, the keyboard map and the announcement cadence against the built shell, named to end -browser-record.md so the discovery rule finds it. It lists the tab order element by element from the header band through the middle to the footer band, on each of the four steps, beside the order the standing keyboard record read, with a verdict on each; a verdict for every key in the Specs keyboard map; and a reading of what is announced when a step advances from the footer control. It carries a Structural verdicts section as the gate requires (DL-084, DL-169), naming the structures this run measured and the verdict each carries. A closing section states what the run does not establish, including that no screen reader was run. (refs: DL-197, DL-189)
- **CI-M-002-003** `tests/test_gui_announce.py::module`: The announcement guards read the strings announce.py returns for a step that advances from the footer control, so the wording and the cadence stay out of the view (DL-083) while the control that triggers them sits outside the step. Any guard whose assertion moves carries a docstring recording the mutation applied and the output observed. (refs: DL-197, DL-189)

#### Code Changes

**CC-M-002-001** (docs/2026-09-06-wizard-focus-order-browser-record.md) - implements CI-M-002-002

**Code:**

```diff
--- /dev/null
+++ b/docs/2026-09-06-wizard-focus-order-browser-record.md
@@ -0,0 +1,62 @@
+# Focus order, keyboard map and announcements - served-page record
+
+Each step's advancing control is built in the footer band, which places
+it after the middle region in the DOM. The order the standing keyboard
+record read was measured with those controls inside the steps, so this
+run reads the order again (DL-197).
+
+## What was opened
+
+Served from `.venv` with `native=False` over HTTP. The nicegui and
+Quasar versions, the URL, the viewport size and the commit are stated
+here.
+
+## Tab order
+
+Element by element, from the header band through the middle to the
+footer band, beside the order
+`docs/2026-08-29-w004-focus-ring-record.md` read, with a verdict on
+each. Read on each of the four steps, because each step shows its own
+action group.
+
+| # | Element read | Order the standing record read | Verdict |
+|---|---|---|---|
+
+## Keyboard map
+
+One row per key in `Specs.dc.html`'s Keyboard section, exercised with
+the advancing control in the footer.
+
+| Key | Scope | What it did | Verdict |
+|---|---|---|---|
+
+## Announcements
+
+What is announced when a step advances from the footer control, and the
+cadence between announcements, read against the strings `announce.py`
+returns.
+
+| Trigger | Announced | Verdict |
+|---|---|---|
+
+## Structural verdicts
+
+The structures this run measured, one row each with its verdict, as the
+gate requires (DL-084, DL-169).
+
+| Structure | Artboard | Read | Verdict |
+|---|---|---|---|
+
+## What this run does not establish
+
+No screen reader was run: the announcement rows read the live region's
+text content and the politeness attribute, not what NVDA speaks. The
+rendered geometry is read in
+`docs/2026-09-05-wizard-shell-browser-record.md`.

```

**Documentation:**

```diff
--- a/docs/2026-09-06-wizard-focus-order-browser-record.md
+++ b/docs/2026-09-06-wizard-focus-order-browser-record.md
@@ under "Tab order"
+The order is read across the whole page rather than within the middle
+alone, because nicegui places the header above the other layout
+elements in the DOM and each step's advancing control sits in the
+footer band; a reading taken inside the middle would miss both ends of
+the ring (DL-197).

```


**CC-M-002-002** (tests/test_gui_keymap.py) - implements CI-M-002-001

**Code:**

```diff
--- a/tests/test_gui_keymap.py
+++ b/tests/test_gui_keymap.py
@@ def test_toggle_detail_is_not_bound_to_noop():
 def test_toggle_detail_is_not_bound_to_noop():
     source = _APP_PY.read_text(encoding="utf-8")
     match = re.search(r"_ACTION_APPLIERS\s*=\s*\{(.*?)\n\}", source, re.DOTALL)
     assert match is not None
     applier = re.search(r'"toggle_detail":\s*(\w+),', match.group(1))
     assert applier is not None
+
+
+def test_every_wizard_step_builds_its_advancing_control_in_the_footer_group():
+    """A key bound to advancing resolves against the control the footer
+    band holds, so this reads each step builder for the group it
+    registers rather than accepting that some route somewhere fills the
+    band. Specs' keyboard map is unchanged: the same map is read against
+    a page whose DOM order differs (DL-197). What the browser gave focus
+    to is read in
+    docs/2026-09-06-wizard-focus-order-browser-record.md; this guard
+    reads only where each control is constructed (DL-189).
+
+    Mutation: the Review step's 'with state.footer_actions:' block was
+    replaced by a plain row, leaving 'Continue to write' inline in the
+    step, and this guard rerun. Observed:
+        AssertionError: steps whose advancing control is not built in
+        the footer group: ['Review']
+        assert ['Review'] == []
+    """
+    source = _APP_PY.read_text(encoding="utf-8")
+    adrift = []
+    for step in ("Set up", "Scan", "Review", "Write"):
+        registered = re.search(
+            r"state\.footer_groups\[\s*[\"']" + re.escape(step) + r"[\"']\s*\]\s*=",
+            source,
+        )
+        if registered is None:
+            adrift.append(step)
+    assert adrift == [], (
+        f"steps whose advancing control is not built in the footer group: {adrift}"
+    )
+    groups = re.findall(
+        r"with state\.footer_actions:\n(.*?)state\.footer_groups\[", source, re.DOTALL
+    )
+    assert len(groups) == 4, (
+        f"the wizard route builds {len(groups)} footer action groups, not four"
+    )
+    assert all("ui.button(" in block for block in groups), (
+        "a footer action group holds no control"
+    )

```

**Documentation:**

```diff
--- a/tests/test_gui_keymap.py
+++ b/tests/test_gui_keymap.py
@@ def test_every_wizard_step_builds_its_advancing_control_in_the_footer_group():
     source = _APP_PY.read_text(encoding="utf-8")
+    # Two readings, because either alone passes in a broken state: the
+    # registration says a step's title has a group, and the block sweep
+    # says each group is built inside the band and holds a control.
     adrift = []

```


**CC-M-002-003** (tests/test_gui_announce.py) - implements CI-M-002-003

**Code:**

```diff
--- a/tests/test_gui_announce.py
+++ b/tests/test_gui_announce.py
@@ def test_live_regions_are_pushed_only_from_announce_py():
 def test_live_regions_are_pushed_only_from_announce_py():
+    """The control that triggers an announcement is built in the footer
+    band while the wording and the cadence stay in announce.py, so what
+    reaches a live region is a string announce.py returns wherever the
+    control that triggers it is constructed (DL-083, DL-197).
+
+    Mutation: a literal sentence was pushed into the polite region from
+    the footer action group in app.py and this guard rerun. Observed:
+        AssertionError: a live region is pushed a string announce.py
+        does not return
+    """

```

**Documentation:**

```diff
--- a/tests/test_gui_announce.py
+++ b/tests/test_gui_announce.py
@@ def test_live_regions_are_pushed_only_from_announce_py():
     Mutation: a literal sentence was pushed into the polite region from
     the footer action group in app.py and this guard rerun. Observed:
         AssertionError: a live region is pushed a string announce.py
         does not return
+
+    What a screen reader speaks is not read here and not read by any
+    guard: the announcement rows in
+    docs/2026-09-06-wizard-focus-order-browser-record.md read the live
+    region's text content and its politeness attribute, and that run
+    states that no screen reader was run (DL-189).
     """

```


**CC-M-002-004** (docs/CLAUDE.md)

**Documentation:**

```diff
--- a/docs/CLAUDE.md
+++ b/docs/CLAUDE.md
@@ the Files table
+| `2026-09-06-wizard-focus-order-browser-record.md` | DL-084 served-page record of the tab order from the header band through the middle to the footer band on each of the four steps, beside the order `2026-08-29-w004-focus-ring-record.md` read; every key in `Specs.dc.html`'s Keyboard section exercised with the advancing control in the footer; and what each live region carries when a step advances | Checking the focus order or the keyboard map against a page whose advancing controls sit in the footer band |

```


### Milestone 3: The decision log - the entries this closes - the entries this leaves open

**Files**: traktor_nml/README.md, traktor_nml/gui/README.md, tests/test_docs_browser_record_structure.py, docs/2026-09-07-composition-close-browser-record.md

**Requirements**:

- traktor_nml/README.md carries one statement per decision starting at DL-183 cited in prose as (DL-NNN).
- an entry is struck from Composition not built only where a record reads its structure built - a structure a record reads as partly refused keeps a narrowed entry naming the refusal and the value that shows it
- Column model and Table geometry and Detail rail stand as written and the statement that keeps them open is cited beside them
- traktor_nml/gui/README.md describes where the bands are built - who owns the page scroll - where the card triplet lands - and cites the records that read each
- the resolves guard reads the newest record that names a structure so the standing records keep their differs rows untouched
- tests/test_docs_browser_record_structure.py holds a reading digest for each record this work writes

**Acceptance Criteria**:

- pytest tests/ -q passes|every DL-NNN this work mints resolves to a statement in traktor_nml/README.md and collides with no existing entry|no prose in either README says previously or now does or no longer or added|docs/2026-09-07-composition-close-browser-record.md is written from a run taken after the section is struck and carries a verdict per named surface and a structural reading for all six structures|each struck entry names that record and the structural reading that struck it|any structure that record read as partly refused has an entry in Composition not built naming what was refused and the computed value that shows it|every guard amended in tests/test_docs_browser_record_structure.py carries a docstring recording the mutation applied and the output observed|the four reading digests already held are unchanged

**Tests**:

- tests/test_docs_browser_record_structure.py

#### Code Intent

- **CI-M-003-001** `traktor_nml/README.md::decision log and Composition not built`: The decision entries this work settles are appended to the log in sequence from DL-183, one statement per decision, each cited in prose where the decision governs. An entry is struck from Composition not built where docs/2026-09-07-composition-close-browser-record.md - the record this milestone closes with, taken after the strike - reads its structure built, and the prose names that record and the reading that struck it; a structure the record reads as partly refused keeps a narrowed entry naming what the framework refused and the computed value that shows it, which is the shape DL-194 fixes for a measured refusal. Column model, Table geometry and Detail rail stand exactly as written, with the statement that keeps them open cited beside them (DL-191), and the sentence recording that the reconstruct page carries no entry stands (DL-172). Nothing in the section is phrased against a previous state. (refs: DL-190, DL-194, DL-191)
- **CI-M-003-002** `traktor_nml/gui/README.md::module description`: The shell the module composes is described as it stands, each claim citing the record that read it: _page_chrome builds the header and footer bands and yields the middle container both routes enter; the middle owns the page scroll and the document does not; the card triplet lands on the sections each page builds, with whatever the QStepper markup refuses named as the record measured it rather than claimed built; theme.py holds every dimension because it is the module a guard under the system interpreter can read. (refs: DL-188, DL-190, DL-194)
- **CI-M-003-003** `tests/test_docs_browser_record_structure.py::READING_DIGESTS and the resolves guard`: The mapping carries a digest for each of the three records this work writes, computed from the verdict rows above the Structural verdicts heading, so a reading edited in a later re-verdict fails the suite; the four digests already held are unchanged, and each new record's name ends -browser-record.md so _RECORD_SUFFIXES discovers it without amendment. test_every_structure_a_record_names_resolves_in_the_decision_log reads the newest record that names a structure rather than every record, so a structure a later run read as built stops naming an entry that no longer exists while the standing records keep their differs rows untouched (DL-171, DL-195). Both the amended guard and each added digest carry a docstring recording the exact mutation applied to prove failure - a digest altered by one character, and an App shell differs row appended to the newest record while the entry is struck - and the exact output observed. (refs: DL-190, DL-195, DL-189)
- **CI-M-003-004** `docs/2026-09-07-composition-close-browser-record.md::document`: A served-page record of the run taken after the Composition-not-built entries are struck, named to end -browser-record.md so the discovery rule finds it. It re-reads the atoms the strike rests on - the two bands' grounds and rules and one card's ground, border and radius - and carries a Structural verdicts section naming all six structures: each row reading matches names the entry it strikes, and each row reading differs resolves to an entry standing in the section, which is the condition test_every_structure_a_record_names_resolves_in_the_decision_log holds while reading this record as the newest one (DL-195). Striking an entry is a claim that the structure exists (DL-170), so the milestone that strikes them closes on its own run rather than on the two records taken before the strike (DL-084, DL-169, DL-190). A closing section states what the run does not establish. (refs: DL-190, DL-189)

#### Code Changes

**CC-M-003-001** (traktor_nml/README.md) - implements CI-M-003-001

**Code:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ the decision log, appended after DL-182's statement
   font work and the re-verdicting both write `docs/CLAUDE.md`, so they
   are sequenced rather than parallel (DL-182).
+- The wizard's shell is built from `ui.header` and `ui.footer` rather
+  than from hand-rolled fixed bands, because Quasar's own `QLayout`
+  writes each band's height onto `q-page-container` as padding and a
+  fixed band fights that reservation; each is constructed with
+  `bordered` and `elevated` off, so the rule and the ground each band
+  carries are the ones `theme.py` emits (DL-183).
+- The header band, the middle region and the footer band are the three
+  rows `.app` draws at `Main.dc.html:15`, and the middle owns the page
+  scroll rather than the document (DL-184).
+- `_page_chrome` builds both bands and hands back the middle container,
+  which each route enters with a `with` statement, so a page's body
+  lands inside the scrolling region by construction rather than by
+  caller discipline (DL-185).
+- Each section a page builds is a card - `.wizard-card` holding a
+  `.wizard-card-head` with its `.wizard-card-title`, and a
+  `.wizard-card-body` - as `Main.dc.html:32-35` draws it (DL-186).
+- Each step's advancing control is built once, in its own group inside
+  the footer action row, and the step change decides which group the
+  band shows; the control invokes the function the step defines, so its
+  enabled state is held once rather than kept in sync between a copy in
+  the step and a copy in the band (DL-187).
+- Every dimension the shell and the cards measure at is a constant in
+  `theme.py`, sourced in a comment to the artboard line that states it,
+  because `theme.py` is the module a guard under the system interpreter
+  can read (DL-188).
+- A guard asserts a rule's content and where a control is constructed;
+  the rendered height, the scroll owner and the computed card padding
+  belong to the served-page record, because a guard that reads a name is
+  true in exactly the broken state (DL-189).
+- An entry leaves "Composition not built" only where a record reads its
+  structure built, the prose that strikes it names the record and the
+  reading, and the milestone that strikes it closes with a record of its
+  own taken after the strike (DL-190).
+- The reconstruct page composes against the same shell as the reconnect
+  wizard. DL-172 decides what a record may verdict about that route, not
+  which shell it is built from (DL-191).
+- `nicegui.css` sets `align-items: flex-start`, `gap: 1rem` and
+  `padding: 1rem` on `.nicegui-header` and `.nicegui-footer` and gives
+  both `flex-direction: row`, so each band restates the alignment, the
+  gap and the padding and takes the direction the framework already
+  gives it; the wizard sheet reaches the head after the framework sheet,
+  so the restatement wins at equal specificity (DL-192).
+- The viewport-height declarations key on Quasar's and nicegui's own
+  `q-layout`, `q-page-container`, `q-page` and `nicegui-content` classes
+  rather than on `wizard-` names, because `app.py` constructs none of
+  those four elements and a `wizard-` class no call site names fails
+  `tests/test_gui_theme.py::test_every_wizard_class_reaches_app_py`
+  (DL-193).
+- A structure a record reads as partly refused keeps a narrowed entry
+  naming what the framework refused and the computed value that shows
+  it, rather than being struck or left as written (DL-194).
+- `test_every_structure_a_record_names_resolves_in_the_decision_log`
+  reads the newest record naming a structure rather than every record,
+  so a structure a later run reads as built stops naming an entry that
+  no longer exists while the standing records keep their differs rows
+  untouched (DL-195).
+- The card triplet replaces the single box rule outright: `.wizard-surface`
+  is withdrawn from the stylesheet and from every call site, because a
+  rule no call site names fails the class-reach guard (DL-196).
+- The keyboard record and the announcement record are read again once
+  each advancing control is built in the footer band, because its place
+  in the DOM sets the tab order (DL-197).
@@ ## Composition not built - App shell
-- **App shell.** `.app` in `Main.dc.html`, `Confirm.dc.html`,
-  `Results.dc.html` and `Review.dc.html` is
-  `display: grid; grid-template-rows: 56px 1fr 64px; height: 800px` -
-  a header band, a scrolling middle and a footer band. `theme.py`
-  emits no shell rule, and both pages compose a header row followed by
-  one column, each page scrolling as a document.
+<!-- The App shell entry is struck where
+     docs/2026-09-07-composition-close-browser-record.md reads the
+     structure built, and the prose that strikes it names that record
+     and the reading - the two band heights and the scroll pair on the
+     document and on the middle - that struck it (DL-190). Where the run
+     reads part of the structure refused, a narrowed entry stands in its
+     place naming what the framework refused and the computed value that
+     shows it (DL-194). -->
 - **Column model.** `main` is `grid-template-columns: 1fr 400px` in
   `Main.dc.html`, `1fr 404px` in `Confirm.dc.html` and `1fr 384px` in
   `Results.dc.html`, a content column beside a guidance rail.
   `theme.py` emits no two-column rule, and every page composes one
   column at `.wizard-content-width`.
+  This entry stands as written: the two-column `main` is outside this
+  work's scope, and `main` is one column at `.wizard-content-width`
+  (DL-191).
@@ ## Composition not built - Card structure
-- **Card structure.** `.card`, `.card-h`, `.card-t` and `.card-b` in
-  `Main.dc.html` are a bordered box with its own header band, title
-  and padded body, three to four of them per screen. `theme.py` emits
-  `.wizard-surface`, which carries the box's ground, border and
-  radius and nothing else, and each page applies it once to the whole
-  column.
+<!-- The Card structure entry is struck on
+     docs/2026-09-07-composition-close-browser-record.md's card reading
+     - the computed padding, border, radius and title weight of a card
+     on each route (DL-190). Where that run reads the QStepper markup
+     refusing part of the triplet, a narrowed entry stands here naming
+     the refusal, the computed value the record quotes and what the
+     stepper composes instead (DL-194). -->
@@ ## Composition not built - Table geometry and Footer band
   table carries a header row.
+  This entry stands as written: the review table's grid geometry and
+  its header row are outside this work's scope (DL-191).
-- **Footer band.** `.ft` in `Main.dc.html` is a 64px band with
-  `.ft-note` at the left and `.ft-act` at the right, holding the
-  screen's advancing action. `theme.py` emits no footer rule, and each
-  page carries its actions inline as the last children of its column.
+<!-- The Footer band entry is struck on
+     docs/2026-09-07-composition-close-browser-record.md's footer
+     reading - the band's computed height, the note at the left, the
+     action group at the right, and each step's advancing control found
+     in the band (DL-190). -->
 - **Detail rail.** `.det` in `Review.dc.html` is a 400px bordered
   panel with its own header, body and footer holding the candidate
   cards. `theme.py` emits no rail rule, and the reconstruct page
   renders its candidate panel below the table in the same column.
+  This entry stands as written: the 400px detail rail is outside this
+  work's scope (DL-191).

```

**Documentation:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ the head of "Composition not built"
+The entries below are the structures the artboards draw that the code
+does not compose. An entry ends by being built and read off a served
+page, not by being excused; where a run reads a structure only partly
+built, the entry is narrowed to what the framework refused rather than
+struck (DL-170, DL-190, DL-194).
+
+The App shell, Card structure and Footer band structures are struck
+from this section, each on the reading in
+`docs/2026-09-07-composition-close-browser-record.md` that carries it:
+the two band heights and the scroll pair on the document and on the
+middle, a card's computed padding, border, radius and title weight on
+each route, and the note and action group found in the band with each
+step's advancing control inside it. Column model, Table geometry and
+Detail rail are the three that stand: `main` is one column at
+`.wizard-content-width`, the review table keeps its own grid geometry
+and header row, and the reconstruct page renders its candidate panel
+below the table in the same column. Each of those three entries states
+beneath it the reason it is open.

```


**CC-M-003-002** (traktor_nml/gui/README.md) - implements CI-M-003-002

**Code:**

```diff
--- a/traktor_nml/gui/README.md
+++ b/traktor_nml/gui/README.md
@@ a section appended after "The vendored typeface"
+## The shell both pages compose against
+
+`_page_chrome` applies the theme, builds the header band and the footer
+band, and hands back the middle container. Both routes enter that
+container with a `with` statement, so a page's body lands inside the
+scrolling region rather than beside it (DL-185).
+
+The bands are `ui.header` and `ui.footer`, each with `bordered` and
+`elevated` off: Quasar's own `QLayout` writes each band's height onto
+`q-page-container` as padding, and the rule and the ground each band
+carries are the ones `theme.py` emits (DL-183). The middle owns
+`overflow-y`, and `q-layout`, `q-page-container`, `q-page` and
+`nicegui-content` - the four elements nicegui's `client.py` builds
+between the viewport and the page's content - each carry a bounded
+height, which is what leaves the middle a height to scroll inside
+(DL-193). The reading is in
+`docs/2026-09-07-composition-close-browser-record.md`.
+
+Each section both pages build is a card: `.wizard-card` holding a
+`.wizard-card-head` with its `.wizard-card-title`, and a
+`.wizard-card-body`. Whatever the `QStepper` markup refuses of that
+triplet is named as
+`docs/2026-09-05-wizard-shell-browser-record.md` measured it, and in
+the narrowed entry under "Composition not built" in
+`traktor_nml/README.md` (DL-190, DL-194).
+
+Each of the four steps registers its own action group in the footer
+band and the step change decides which group the band shows, so the
+control that advances a step exists once and its enabled state is held
+once (DL-187).
+
+Every dimension either the shell or the cards measure at is a constant
+in `theme.py`, sourced in a comment to the artboard line that states
+it. `theme.py` imports no nicegui, so it is the module a guard under
+the system interpreter can read (DL-069, DL-188).

```

**Documentation:**

```diff
--- a/traktor_nml/gui/README.md
+++ b/traktor_nml/gui/README.md
@@ the end of "The shell both pages compose against"
+The header band, the middle region and the footer band are the three
+rows `.app` draws at `Main.dc.html:15`, and the middle owns the page
+scroll rather than the document (DL-184). The footer band is
+`Main.dc.html:29-31`: `.ft` holding `.ft-note`'s sentence at the left
+and `.ft-act`'s controls at the right.
+
+The card triplet is composed where each page builds its own containers.
+A step's own header is Quasar's `QStepper` markup, and what that markup
+refuses of the triplet is named by the computed value that shows the
+refusal, in `docs/2026-09-05-wizard-shell-browser-record.md` and in the
+narrowed entry under "Composition not built" in `traktor_nml/README.md`
+(DL-186, DL-194).
+
+What a guard in `tests/` holds of all this is the text: which rule the
+stylesheet emits, which class string a call site names, and where each
+control is constructed. Whether the browser gave the middle the
+viewport, and what it computed for a card, is read on a served page and
+written into a record under `docs/` (DL-084, DL-169, DL-189).

```


**CC-M-003-003** (tests/test_docs_browser_record_structure.py) - implements CI-M-003-003

**Code:**

```diff
--- a/tests/test_docs_browser_record_structure.py
+++ b/tests/test_docs_browser_record_structure.py
@@ READING_DIGESTS
     "2026-08-29-w004-focus-ring-record.md": "22120b36351a3e10ad6c3706503f04f6ddbb8bc602c3d5377b9a014da0ac3c88",
     "2026-09-03-header-tabs-browser-record.md": "8efef9b91ac577095c5f8c76af04ea522c7dc4e8d473dd34e85fbd134413d5da",
+    # Each value is the sha256 _reading_digest() returns for the record
+    # named, read back once that record is written; the four above are
+    # untouched. A digest guessed here would fail the guard it exists to
+    # arm (DL-171). Each name ends -browser-record.md, which
+    # _RECORD_SUFFIXES already discovers.
+    "2026-09-05-wizard-shell-browser-record.md": "<sha256 read back from _reading_digest()>",
+    "2026-09-06-wizard-focus-order-browser-record.md": "<sha256 read back from _reading_digest()>",
+    "2026-09-07-composition-close-browser-record.md": "<sha256 read back from _reading_digest()>",
 }
@@ def test_a_records_verdict_rows_hash_to_its_recorded_digest(record: Path):
     A record with no entry in READING_DIGESTS is one written after this
     mapping and has no prior readings to hold.

+    Mutation: the first character of the
+    2026-09-05-wizard-shell-browser-record.md digest was changed and
+    this guard rerun. Observed:
+        AssertionError: 2026-09-05-wizard-shell-browser-record.md
+        verdict rows changed: a recorded reading is edited, which
+        DL-171 forbids
+
     Mutation: in docs/2026-08-28-w002-browser-record.md the Dialog
@@ def test_every_structure_a_record_names_resolves_in_the_decision_log():
 def test_every_structure_a_record_names_resolves_in_the_decision_log():
     """A structure a record names in a differs verdict is an entry
     under 'Composition not built' in traktor_nml/README.md, so a
     differs verdict cannot point at a section that does not record it.

+    Only the newest reading of a structure is checked. A structure a
+    later run reads as built stops naming an entry that no longer
+    exists, while every standing record keeps the differs rows the run
+    that wrote it recorded (DL-171, DL-195).
+
     Mutation: the '- **Footer band.**' entry was deleted from the
     Composition not built section and this guard rerun. Observed:
         AssertionError: structures named in a record with no
         Composition not built entry: ['Footer band']
         assert ['Footer band'] == []
+
+    Mutation: an 'App shell | ... | differs' row was appended to the
+    Structural verdicts section of
+    docs/2026-09-07-composition-close-browser-record.md, the newest
+    record, while the App shell entry stands struck from the section,
+    and this guard rerun. Observed:
+        AssertionError: structures named in a record with no
+        Composition not built entry: ['App shell']
+        assert ['App shell'] == []
     """
     readme = README.read_text(encoding="utf-8")
@@ the differs sweep
-    named: set[str] = set()
+    # browser_records() sorts by name and every record is named for the
+    # run that wrote it, so the last verdict a structure collects is the
+    # newest reading of it.
+    newest: dict[str, str] = {}
     for record in browser_records():
         text = record.read_text(encoding="utf-8")
         match = _STRUCTURAL_HEADING.search(text)
         if not match:
             continue
         for row in _VERDICT_ROW.finditer(text[match.end():]):
-            if row.group(1) != "differs":
-                continue
             cells = [cell.strip() for cell in row.group(0).strip("|").split("|")]
             if cells:
-                named.add(cells[0].strip("* "))
+                newest[cells[0].strip("* ")] = row.group(1)

-    adrift = sorted(name for name in named if name not in entries)
+    adrift = sorted(
+        name for name, verdict in newest.items()
+        if verdict == "differs" and name not in entries
+    )
     assert adrift == [], (
         f"structures named in a record with no Composition not built entry: {adrift}"
     )

```

**Documentation:**

```diff
--- a/tests/test_docs_browser_record_structure.py
+++ b/tests/test_docs_browser_record_structure.py
@@ def test_every_structure_a_record_names_resolves_in_the_decision_log():
     readme = README.read_text(encoding="utf-8")
+    # entries is the set of structures the 'Composition not built'
+    # section still records; a struck structure is absent from it, which
+    # is what makes a stale differs row on the newest record fail here.

```


**CC-M-003-004** (docs/2026-09-07-composition-close-browser-record.md) - implements CI-M-003-004

**Code:**

```diff
--- /dev/null
+++ b/docs/2026-09-07-composition-close-browser-record.md
@@ -0,0 +1,52 @@
+# Composition entries closed - served-page record
+
+Striking an entry from "Composition not built" is a claim that the
+structure exists (DL-170), so the milestone that strikes them closes
+with a run of its own rather than resting on the two records taken
+before the strike (DL-084, DL-169, DL-190).
+
+## What was opened
+
+Served from `.venv` with `native=False` over HTTP, at the commit that
+carries the struck section. The nicegui and Quasar versions, the URL,
+the viewport size and the commit are stated here.
+
+## Atom readings
+
+| Surface | Expected | Read | Verdict |
+|---|---|---|---|
+
+The atoms this run re-read: the header band's ground and rule, the
+footer band's ground and rule, and one card's ground, border and
+radius.
+
+## Structural verdicts
+
+All six structures, one row each, as the gate requires (DL-169). The
+three this work settles carry the reading that settles them; the three
+that stay open carry the verdict this run measured them at.
+
+| Structure | Artboard | Read | Verdict |
+|---|---|---|---|
+
+Each row that reads `matches` names the entry it strikes, and each row
+that reads `differs` resolves to an entry standing in the section -
+which is the condition
+`test_every_structure_a_record_names_resolves_in_the_decision_log`
+holds, reading this record as the newest one (DL-195).
+
+## What this run does not establish
+
+Named explicitly: no screen reader was run; the focus order and the
+keyboard map were read in
+`docs/2026-09-06-wizard-focus-order-browser-record.md` and are not
+re-read here.

```

**Documentation:**

```diff
--- a/docs/2026-09-07-composition-close-browser-record.md
+++ b/docs/2026-09-07-composition-close-browser-record.md
@@ under "Structural verdicts"
+This is the newest record naming these structures, which is the one
+`test_every_structure_a_record_names_resolves_in_the_decision_log`
+reads; the records taken before the strike keep the rows their own runs
+recorded (DL-171, DL-195).

```


**CC-M-003-005** (docs/CLAUDE.md)

**Documentation:**

```diff
--- a/docs/CLAUDE.md
+++ b/docs/CLAUDE.md
@@ the Files table
+| `2026-09-07-composition-close-browser-record.md` | DL-084 served-page record taken at the commit that carries the struck `Composition not built` section: the header and footer bands' ground and rule and one card's ground, border and radius re-read, and a structural verdict on all six structures - the three this work settles carrying the reading that settles them, the three that stay open carrying the verdict this run measured | Following the reading a struck composition entry cites, or writing the record a strike rests on |

```


## Execution Waves

- W-001: M-001
- W-002: M-002
- W-003: M-003

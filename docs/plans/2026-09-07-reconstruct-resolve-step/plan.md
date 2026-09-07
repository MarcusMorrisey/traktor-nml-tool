# Plan

## Overview

The reconstruct workflow at the / route composes one column of four cards with two primary controls in the footer band. Its configure -> preview -> resolve -> write sequence exists only inside write_refusal, so an operator meets it as a warning after clicking Write rather than as visible state, and its conflicts render as hand-rolled flex rows with no header row, no column alignment, no detail rail and no gate on the advancing control. design/reconnect-wizard/Resolve.dc.html and its three siblings draw that page in four steps: a conflict table on a five-track grid under a header row, a 400px detail rail, one bulk action per input collection, and a footer whose advancing control is shut while any group is undecided. One thing blocks building to that contract: DL-172 exempts / from the structural gate on the ground that no artboard draws it, which fourteen artboards and four drawings of / make false. The header is not in dispute. Specs.dc.html lines 154-169 already fix the band as brand, the .bar divider and the two section tabs, name both labels verbatim, and state that the band carries no .task element; the four artboards were the things that disagreed, and at commit 5a6e469 they were fixed to Specs, with the four-step rail moved out of the band into the page as <nav class="steprail"> spanning main's first row. gui/'s header already builds what Specs contracts, so no header work remains.

**Approach**: Nothing in the header changes: Specs settles it, the artboards now agree with it, and navigation.py and both tab labels are untouched. The four-step rail is a page element, main's first row spanning both columns, so its rules join the other page rules in theme.py rather than the header band's. DL-172's exemption is struck rather than restated: / is inside the structural gate, read against the four page-3 artboards. Nothing is struck from 'Composition not built' and nothing is added to it: the three entries there are read against the reconnect wizard's artboards and that route composes none of them, so they stand, each narrowed to say so, and DL-191's statement is revised in the same edit because the ground it gives - that theme.py emits no rule of the kind - is one this work falsifies. /'s own split, grid and rail earn no entry at any commit, since gui/ composes all three; they are read built in the served-page record M-002 closes on. The step scaffold is a nicegui-free step table in reconstruct_steps.py driving four plain regions rather than a ui.stepper whose own step header the artboards do not draw. Steps 1, 2 and 4 take the existing cards unchanged. Step 3 is built to Resolve.dc.html: the split, the grid and the rail as rules in theme.py, the rows hand-rolled per DL-079, the picks keyed on candidate references per DL-148, digits 1-9 resolved through the keymap entries that already carry them, and one conflict_model call answering both the footer's count and the advancing control's gate. Each milestone that composes a page closes on its own served-page record; M-001 emits rules and M-003 writes documentation, so neither takes one and M-001's rules are read in M-002's record. The decision log lands in M-003's commit, so the DL-198..DL-212 citations M-001 and M-002 carry are forward references into this plan until it does, and the log is written once against code that stands rather than three times against code that does not. Three milestones in three serial waves; the header milestone the earlier plan carried is gone.

### The stepped reconstruct page and the boundary its rules sit below

[Diagram pending Technical Writer rendering: DIAG-001]

## Planning Context

### Decision Log

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-198 | The header band is not touched. Specs.dc.html already contracts it as brand, the .bar divider and the section tab strip carrying 'Reconstruct playlists' at / and 'Reconnect wizard' at /reconnect, with exactly one aria-current="page" and no .task element; gui/'s header and navigation.SECTIONS build that already, and both tab labels stand as written. | Specs.dc.html lines 154-169 carry a normative 'App header - brand, divider, section tabs' section stating that this strip 'is the whole of the header' and that the band 'carries no .task element', because a second name beside the selected tab would come from a source that can disagree with it -> the .task at Specs line 67 is Specs' own artboard chrome, not a header rule, so there was never a Specs gap to amend and no plan may claim one -> the four page-3 artboards were the things disagreeing with Specs, and under DL-071 the screens were fixed rather than Specs, which is what commit 5a6e469 did; no header, navigation or tab-label change remains for this work. |
| DL-199 | The four-step progress rail is a page element, not header furniture: <nav class="steprail" aria-label="Progress"> is main's first row spanning both columns of the page grid, and its rules are emitted from theme.py beside the other page rules. | Specs states .task and .rail 'belong to the wizard artboard's own screen', so the reconstruct band cannot carry a rail -> the four artboards at 5a6e469 draw .steprail inside main at grid-column 1 / -1 above the step's content, where it marks progress without naming the screen a second time -> a page element's geometry is a page rule, so theme.py owns the rail's rules on the same terms as .wizard-card and the split, and app.py names class strings alone (DL-069, DL-188). |
| DL-200 | DL-172's exemption is struck. The reconstruct page at / is inside the structural gate, read against Reconstruct.dc.html, Preview.dc.html, Resolve.dc.html and Write.dc.html, and each record names which of the four a surface is read against. | DL-172 exempts / on the stated ground that no artboard draws it and all ten draw the reconnect wizard -> canvas.json carries fourteen artboards and four of them draw /, so the ground is false and the entry cannot stand as written -> a structural verdict now has a drawn structure to read against, so the gate covers / on the same terms as /reconnect rather than the exemption being restated or silently kept. |
| DL-201 | The reconstruct page's column model, table geometry and detail rail carry no entry under 'Composition not built': gui/ composes all three on /. The three standing entries stay, each narrowed to name the reconnect wizard's route and the artboard it is read against, and DL-191's statement is revised to give that narrowing as the reason they stand rather than the absence of a rule of the kind. | An entry under 'Composition not built' asserts a structure gui/ does not compose, and by the end of this work gui/ composes a split, a five-track grid and a 400px rail on / -> there is no commit in this plan at which an entry for /'s three would be true, so minting one and striking it would write a false statement and then delete it; the end state is no entry, and the built structures are read in the served-page record M-002 closes on (DL-084, DL-169) -> the reconnect wizard's three are read against Review.dc.html and its siblings and that route composes none of them, so they stand, narrowed to say so; DL-191's stated ground - that theme.py emits no two-column rule, no grid table and no rail - is falsified by this work the moment .wizard-resolve-split is emitted, so DL-191 is revised the way DL-200 revises DL-172 rather than left standing on it -> and because nothing is struck, DL-190's post-strike trigger never fires and no milestone here owes a post-strike record. |
| DL-202 | The four step regions at / are plain containers whose visibility one nicegui-free step table drives, with the rail rendered as main's first row; ui.stepper is not adopted at /, and the /reconnect wizard keeps its own ui.stepper unchanged. | A QStepper draws its own step header and the artboards draw the rail as a page row, so adopting the widget buys navigation and then spends the milestone suppressing chrome the artboard does not draw, which is the objection DL-079 raises against aggrid -> the two routes therefore run two step mechanisms, which is acceptable because the mechanisms are private to each route while the shared facts are not: the rail's states, the step order and the reachability rule all live in reconstruct_steps.py where a guard reads them, and the per-step footer follows the wizard's own footer_groups shape -> what would be costly to fork, the keyboard map and the header, stays single-sourced in keymap.py and navigation.py, and /reconnect's composition is out of scope so converting it to match would be a change this work is forbidden to make. |
| DL-203 | traktor_nml/gui/reconstruct_steps.py holds the four-step table, the per-step rail records (done, current, upcoming) and the predicate deciding which step the page may advance to; it imports no nicegui. | Every rail state and every advance rule is a pure computation over the step table and the decision state -> DL-069 puts the only side the suite reaches below the framework boundary, and navigation.py already proves the shape for the header tabs -> a module mirroring navigation.py carries the step rule where a guard on the system interpreter reads it, and app.py renders records it is handed. |
| DL-204 | One predicate in conflict_model.py decides both the footer's outstanding sentence and whether the advancing control is enabled at step 3. | The artboard's footer states '45 still to decide. Writing stays closed until every one has an answer.' beside a control drawn aria-disabled -> a count computed for the sentence and an enabled state computed beside it are one fact written twice and drift the moment either moves -> the count and the gate come from a single conflict_model call, which is the side DL-069 leaves reachable and where write_refusal already holds the same rule for the write. |
| DL-205 | Digit keys 1-9 pick an answer on the resolve table through keymap.dispatch at SCOPE_TABLE. keymap.py is not edited - its entries already bind 1-9 to pick_candidate - and the reconstruct route carries its own applier mapping in app.py for the actions the resolve table answers, since the existing _ACTION_APPLIERS appliers take the wizard's _WizardPageState. | Specs binds 1-9 to candidate picking over a decision table and keymap.py is the single source feeding both the help panel and the live bindings (DL-080), so a binding written at / would fork that map for one screen -> keymap.ENTRIES already carry the digits at SCOPE_TABLE, so nothing in keymap.py needs to change and the reconstruct route resolves keypresses through the same dispatch -> the effect side cannot be shared, because every applier in _ACTION_APPLIERS is typed on the wizard's page state, so the resolve table gets its own name-to-applier mapping in app.py whose key set a guard pins as a subset of keymap.ACTION_NAMES, keeping the map single-sourced while the effects stay per-route. |
| DL-206 | The conflict table is a CSS grid at grid-template-columns: minmax(0, 1fr) 132px 84px 196px 140px under a header row, emitted from theme.py as .wizard-conflict-grid and its header and row modifiers, with each row hand-rolled in app.py. | Resolve.dc.html line 55 draws .gr at those five tracks under the .th header rule at line 56, and a flex row takes each cell's width from its content so no column aligns from one row to the next -> the geometry has to be a grid the sheet owns, since app.py may carry no dimension and no hex (DL-069, DL-188) -> theme.py emits the track list and the header rule and app.py names class strings alone; the rows stay hand-rolled because aggrid claims the arrow keys Specs binds over this same table (DL-079). |
| DL-207 | The detail rail is theme.py's .wizard-detail-rail inside a .wizard-resolve-split at grid-template-columns: 1fr 400px, carrying a head, a body and a footer; the body holds one control per distinct answer and the strip above the split holds one bulk action per input collection. | Resolve.dc.html line 53 draws .split at 1fr 400px and line 70 .det with .det-h, .det-b and .det-f, one .cand per answer and 'Decide all from' buttons per collection -> a pick names the record that wins rather than a base-or-source token, because one file in two inputs carries the identical location-derived key and two collections holding identical values are one answer (DL-148) -> the rail's controls are keyed on conflict_model.candidate_reference and the bulk actions on reference_from_input, so the drawn per-answer shape and the model's own vocabulary are the same shape. |
| DL-208 | Steps 1, 2 and 4 hold the content the reconstruct page composes today, moved into their step regions with their cards, holders and callbacks unchanged. | The page cannot carry a step 3 unless it is stepped, and the artboards draw the rail on all four screens -> building step 3 alone leaves 'step 3' naming nothing, while redesigning all four is a far larger change whose risk the resolve work does not need to carry -> the three other regions take the existing cards verbatim and their artboards are built in later work. |
| DL-209 | Every guard this work adds is proven to fail first: the named mutation is applied, the guard is run, the verbatim pytest output is captured, the mutation is reverted, and the docstring carries both the mutation and that output. | A guard that reads a class name back is true in exactly the broken state, which is how FONT_SANS named IBM Plex while the page painted Segoe UI, how a footer assertion was satisfied by the wrong route and how a digest hashed the empty string -> the only proof a guard discriminates is a run in which it fails, so the mutation and the exact output pytest printed are recorded beside it (DL-165, DL-189) -> a line pytest printed longer than the margin is cut with an ellipsis rather than rewrapped, so what stands is what pytest printed. |
| DL-210 | A milestone that emits rules and composes no page closes on its guards and its diff and takes no served-page record; the rules it emits are read off a served page in the record of the milestone that first composes them. M-001 closes this way and its rules are named among the surfaces M-002's record reads. | DL-084's gate is driven in a browser over HTTP and DL-169's structural reading reads a composed surface -> M-001 touches conflict_model.py, theme.py and two guard files and composes nothing, so a page served after it carries no element any new rule selects and a record taken there would name no new surface and say so -> an empty record reports a pass the gate never performed, which is the failure mode DL-165 and DL-189 name and the trap this project has been bitten by three times -> the rules therefore carry forward to M-002's record, where the four step regions and the resolve screen that paint them exist, and that record names each M-001 rule among its surfaces so no rule reaches the tree unread. |
| DL-211 | Each milestone that composes a page closes on its own served-page record under docs/, driven in a browser over HTTP, carrying a matches or differs verdict and a structural reading per named surface. | Every gui/ guard reads source text or walks the AST under an interpreter with no nicegui, and the served-page gate is the only gate that has caught a defect in gui/ - five in one baseline commit, and .wizard-middle at 775px under nicegui's own align-items in the last one -> a guard reading a class name is true in exactly the broken state (DL-165, DL-189) -> the record is the pass condition and the guards are the regression net (DL-084, DL-169); a milestone that composes no page takes none, and its rules are read in the record of the milestone that first composes them (DL-210). |
| DL-212 | The decision-log statements for DL-198 through DL-212 land in one commit, M-003's, and the citations these numbers carry in the code and guard docstrings written by M-001 and M-002 are forward references until that commit lands. The work is not complete at W-002. | Each of these entries states what the code as it stands does, and the section on 'Composition not built' can only be written against structures a served-page record has read built -> writing the log in three passes would mean three edits to the same two sections, the first two of them describing code the commit does not yet carry, which is exactly the change-relative prose the log forbids -> the log therefore trails the code by design, the plan carries M-003 as a required milestone rather than an optional tidy-up, and the forward reference is recorded here so a reader of the W-001 or W-002 commit knows the number resolves in this plan rather than naming nothing by accident. |

### Rejected Alternatives

| Alternative | Why Rejected |
|---|---|
| Amend Specs.dc.html's header section - fix the band at brand, divider and a task label with the progress rail beside it - and reword navigation.SECTIONS to the two task sentences. | Specs lines 154-169 already settle the header the other way: the strip 'is the whole of the header', both labels are named verbatim and bound to their routes, and line 169 states the band 'carries no .task element' precisely because a second name can disagree with the selected tab. The four page-3 artboards were the things disagreeing, and DL-071 fixes the screens in that case, which commit 5a6e469 did. Amending Specs would strike a standing rule to restore the disagreement it was written to prevent. (ref: DL-198) |
| Render the four-step rail in the 56px header band beside the brand, where Main.dc.html draws the wizard's .rail. | Specs states .task and .rail belong to the wizard artboard's own screen, and the band's contracted contents are brand, divider and the tab strip. The rail is a page row instead - main's first row at grid-column 1 / -1 - which is what the four artboards draw. (ref: DL-199) |
| Adopt ui.stepper at / so both routes share one step mechanism. | A QStepper draws its own step header, which the artboards do not draw, so the widget's navigation is bought and then spent suppressing chrome - the objection DL-079 raises against aggrid. Converting /reconnect the other way is out of scope. (ref: DL-202) |
| aggrid for the conflict table. | DL-079 rejects it for the review table because it claims the arrow keys Specs binds over that table; the same keys are bound over this one. (ref: DL-206) |
| Write a second digit binding at the reconstruct route rather than dispatching through keymap. | keymap.py is the single source feeding both the help panel and the live bindings (DL-080), and its entries already bind 1-9 to pick_candidate at SCOPE_TABLE. Only the effect side forks, because every applier in _ACTION_APPLIERS is typed on the wizard's page state. (ref: DL-205) |
| Build step 3's content without the four-step scaffold, or redesign steps 1, 2 and 4 in this pass. | Without the scaffold 'step 3' names nothing and contradicts the artboards, which draw the rail on all four screens; redesigning all four is a far larger change whose risk the resolve work does not need to carry. (ref: DL-208) |
| Strike the three standing 'Composition not built' entries once / builds a split, a grid table and a rail. | Those three are read against the reconnect wizard's artboards and name what /reconnect does not compose; building a split, a grid table and a rail at / leaves every one of those readings untouched, so nothing is struck. Nor does / get entries of its own: an entry names a structure gui/ does not compose, and gui/ composes all three there, so at no commit in this plan would such an entry be true. The reconnect three stand, each narrowed to name that route and its artboard, and /'s three are read built in the served-page record (DL-084, DL-169). (ref: DL-201) |

### Constraints

- MUST: `design/reconnect-wizard/Resolve.dc.html` is the contract this screen is built to. Its siblings on canvas page 3 are Reconstruct.dc.html (step 1), Preview.dc.html (step 2) and Write.dc.html (step 4). Read the artboard rather than the prose describing it.
- MUST: DL-071 - a screen disagreeing with `Specs.dc.html` is fixed in Specs first, never per-screen. Specs binds digits 1-9 to candidate picking, and step 3's rail has to honour that map rather than invent one.
- MUST: revisit DL-172. It exempts `/` from the structural gate on the stated ground that 'no artboard draws that page - all ten draw the reconnect wizard'. canvas.json now carries FOURTEEN artboards and four of them draw `/`, so that ground is gone and `/` has a drawn structure a structural verdict can read against. The exemption cannot be left standing on a false premise; decide what replaces it and say so in the log.
- MUST NOT: strike Column model, Table geometry or Detail rail from 'Composition not built'. All three are read against the RECONNECT wizard's artboards (Review.dc.html and friends) and name what `/reconnect` does not build. Building a split, a grid table and a rail on `/` does not close them. Decide explicitly whether `/`'s versions need entries of their own, and record that decision either way.
- MUST: DL-069's nicegui boundary - only app.py, file_picker.py and __main__.py may import nicegui or pywebview. Every CSS rule, class name and dimension constant lives in theme.py; every decision rule lives in conflict_model.py or another nicegui-free module, because that is the only side the suite can reach. Enforced by an AST walk in tests/test_gui_view_boundary.py.
- MUST: DL-079 - the review table is hand-rolled `ui.row` per record and aggrid is NOT adopted, because aggrid claims the arrow keys Specs binds over that same table. The same reasoning governs any table built here.
- MUST: each milestone closes with a served-page record in docs/, driven in a browser over HTTP, carrying a matches/differs verdict per named surface (DL-084) AND a structural reading per surface (DL-169). DL-190: a milestone that strikes any 'Composition not built' entry closes on its own post-strike record.
- MUST: every new guard is proven to FAIL first - apply the specific mutation, run it, capture the verbatim output, revert, and record both mutation and exact output in the docstring. Beware the guard that is green in exactly the broken state: this project has been bitten three times (FONT_SANS naming IBM Plex while the page painted Segoe UI; a footer assertion the wrong route satisfied; a digest that hashed the empty string).
- MUST: traktor_nml/README.md is the decision-log authority; one statement per decision, cited in prose as `(DL-NNN).`; high-water mark is DL-197, so new entries start at DL-198.
- MUST: line endings per file - app.py is 100% CRLF (read/write with newline=''); theme.py, conflict_model.py, tests/*.py, traktor_nml/README.md and docs/*.md are LF; docs/CLAUDE.md and tests/CLAUDE.md are CRLF with one pre-existing bare LF each. A mixed-ending edit produces a whole-file diff that hides the real change.
- MUST: documentation describes the code as it stands - no 'previously', 'now does', 'no longer', 'added', 'moved'.
- MUST: never cite a source for something it does not say, line numbers included. Open and check.
- MUST: re-run the keyboard and announcement records - moving the advancing controls between step regions changes tab order.
- MUST NOT: regenerate tests/baselines/manifest.json or the fixture/w002gatefix2 gate fixture.
- MUST NOT: restore a file with `git checkout` - copy aside and restore from the copy.
- MUST NOT: write into or delete build/ or dist/.
- MUST NOT: install anything into the system interpreter. The suite runs with the SYSTEM interpreter at C:\Users\marcu\AppData\Local\Python\pythoncore-3.14-64\python.exe, not .venv.
- SHOULD: reuse `.wizard-content-width` and the existing shell rules rather than introducing a second width or band owner; the shell (header band, scrolling middle, footer band, card triplet) is already built and verdicted `matches`.
- MUST NOT: amend design/reconnect-wizard/Specs.dc.html's header section or reword either entry in navigation.SECTIONS. Specs settles the header and the screens were fixed to it at 5a6e469.
- MUST: read the four page-3 artboards as they stand at 5a6e469 - the band carries brand, divider and the two tabs, and .steprail is main's first row at grid-column 1 / -1.

### Known Risks

- **nicegui and Quasar defaults on containers the framework builds silently override the sheet's geometry for every new container this work adds - the step regions, the resolve split, the conflict grid and the detail rail. The previous milestone's .wizard-middle rendered at 775px because its parent .nicegui-content carries align-items: flex-start, and no source-text guard could see it.**: Each milestone closes on a served-page record driven over HTTP that reads the RESOLVED width of the split's two columns, the grid's five tracks and the rail, not the declared rule. A differs verdict on any of them keeps the milestone open.
- **A guard that reads a class name back is true in exactly the broken state - the trap that bit this project three times (FONT_SANS naming IBM Plex while the page painted Segoe UI, a footer assertion the wrong route satisfied, a digest hashing the empty string).**: Every sheet guard asserts the rule's declaration - the track list, the 400px width, the header-row rule - not the presence of a selector, and every new guard is proven to fail first with the mutation and its verbatim output recorded in the docstring.
- **Moving the advancing controls into per-step footer groups changes the tab ring's DOM order, so the recorded keyboard and announcement readings stop describing the page.**: The M-002 record retakes the keyboard and announcement readings on the served page, noting that a focus ring read from script reports the unfocused outline.
- **The two routes run two different step mechanisms (ui.stepper at /reconnect, plain regions at /), so a later change to step behaviour can be made in one and missed in the other.**: The shared facts - step order, rail states, reachability - live in reconstruct_steps.py rather than in either route's widget, and gui/README.md's module table states which mechanism serves which route.
- **The reconstruct route's applier mapping is a second name-to-effect table beside _ACTION_APPLIERS, and DL-080's guarantee that no action name falls through a branch chain holds only if that second table is pinned too.**: A guard pins the reconstruct mapping's key set as a subset of keymap.ACTION_NAMES and pins which actions the resolve table answers, so an unlisted name is a test failure rather than a silent no-op.

## Invisible Knowledge

### System

The reconstruct page at / and the reconnect wizard at /reconnect are two operations of one app sharing one header, one keyboard map and one design contract. Specs.dc.html is that contract and governs the header band, the status taxonomy and the keyboard map; an artboard is one screen's rendering of it, so a screen that disagrees with Specs is fixed in Specs first and never per screen (DL-071, DL-072). Under gui/ only app.py, file_picker.py and __main__.py may import nicegui: every CSS rule, class name and dimension lives in theme.py and every decision rule in a nicegui-free module, because the suite runs under a system interpreter with no nicegui and that is the only side it can reach (DL-069). Consequently no guard here exercises a served page. The served-page record under docs/ - driven in a browser over HTTP, one matches-or-differs verdict plus a structural reading per named surface - is the pass condition (DL-084, DL-169), and the source-text and AST guards are the regression net. traktor_nml/README.md is the decision-log authority: one statement per decision, cited in prose as (DL-NNN), and its 'Composition not built' section is a claim about structures that are drawn but not composed, struck only by building them.

### Invariants

- Preview precedes a write; the preview run IS the run, and the write is gated on the held result.
- A resolution names the record that wins - an (input index, primary key) pair - never a base-or-source token.
- Two collections holding identical values are one answer, and deciding it decides both.
- Only app.py, file_picker.py and __main__.py import nicegui or pywebview.
- Every class string reaching .classes() expands to a literal at the call site, and app.py carries no hex.
- Every new guard is proven to fail first, with the mutation and its verbatim output in the docstring.
- app.py is CRLF throughout; theme.py, conflict_model.py, tests/*.py, traktor_nml/README.md and docs/*.md are LF.
- A surface's verdict carries a structural reading beside its atom readings, or it fails the gate.

### Tradeoffs

- No header work at all: Specs already contracts the band and the artboards were fixed to it, so the cost of the header question was paid in the design set rather than in this plan. Nothing in the suite pins either tab's wording - tests/test_gui_header_tabs.py reads every label off navigation.SECTIONS and pins routes, order, ARIA and class strings, never words - so a reword would have been cheap in the suite and expensive in the contract, which is the reverse of the usual case.
- Four plain regions rather than a ui.stepper costs the widget's own navigation and buys a page rail the artboards actually draw; the price is two step mechanisms across the two routes, paid down by keeping the step facts in reconstruct_steps.py.
- The resolve table gets its own applier mapping because every existing applier is typed on the wizard's page state; the keyboard MAP stays single-sourced in keymap.py, only the effects fork.
- Steps 1, 2 and 4 keep their existing content, so their artboards stay unbuilt and their records read differs until later work.
- The served-page record, not the guards, is the pass condition: no guard here exercises a served page, and framework defaults on containers nicegui builds have already cost one milestone a 775px middle.

## Milestones

### Milestone 1: The resolve step's rules, the rail's rules and the sheet

**Files**: traktor_nml/gui/conflict_model.py, traktor_nml/gui/theme.py, tests/test_gui_resolve_rules.py, tests/test_gui_resolve_sheet.py

**Requirements**:

- conflict_model.py holds one predicate returning the outstanding count and the all-decided fact together, and imports no nicegui (DL-204, DL-069).
- theme.py emits the resolve split at 1fr 400px, the conflict grid at minmax(0, 1fr) 132px 84px 196px 140px with its header-row and row modifiers, the detail rail's head/body/footer rules, the answer card and its chosen state, the bulk strip, the tally, and the step rail as a page row spanning both columns (DL-199, DL-206, DL-207).
- Every dimension and colour is a named constant in theme.py; nothing dimensional or hex reaches app.py (DL-069, DL-188).
- theme.py, conflict_model.py and tests/*.py are written LF.
- M-001 composes no page and takes no served-page record; every rule and constant it emits is carried into the surface list of M-002's record, which is the first record with a composed surface those rules paint (DL-210).

**Acceptance Criteria**:

- resolve_gate over groups with one undecided returns the count of undecided groups and a shut gate; over fully decided groups returns zero and an open gate.
- The emitted sheet's .wizard-resolve-split rule declares grid-template-columns: 1fr 400px, matching Resolve.dc.html's .split at line 53.
- The emitted sheet's .wizard-conflict-grid rule declares the five tracks verbatim, matching Resolve.dc.html's .gr at line 55, and a header-row rule sits beneath it.
- The emitted sheet's step-rail rule places the rail across both page columns, matching Resolve.dc.html's .steprail at line 104.
- tests/test_gui_view_boundary.py and tests/test_gui_theme.py pass unchanged.
- Every new guard has been run against its specific mutation and FAILED, with the mutation and the verbatim failure output recorded in its docstring.
- M-001 closes on its guards and its diff with no docs/ record, because it emits rules and composes no surface for a served-page gate to read, and the enumerated list of rules M-002's record must read is carried into M-002 (DL-210).
- The DL-198..DL-212 numbers this milestone's code and docstrings cite are forward references: their statements land in M-003's commit, and the plan is not complete until it does (DL-212).

**Tests**:

- tests/test_gui_resolve_rules.py: an undecided group leaves the gate shut and names its count; a bulk resolution over an input index settles only the groups that collection holds a record in; a pick names a candidate reference, not a collection token.
- tests/test_gui_resolve_sheet.py: the split's two tracks, the grid's five tracks, the header row, the rail's 400px width and its three bands, and the step rail's column span - each asserted as the rule's declaration rather than the presence of a class name.
- Re-run tests/test_gui_theme.py and tests/test_gui_view_boundary.py.

#### Code Intent

- **CI-M-001-001** `traktor_nml/gui/conflict_model.py::resolve_gate`: Returns the outstanding count over the held groups and the decisions beside it, and whether every group carries an answer. One call answers both the footer's sentence and the advancing control's enabled state. Imports no nicegui. (refs: DL-204)
- **CI-M-001-002** `traktor_nml/gui/theme.py::page_stylesheet`: The sheet emits .wizard-resolve-split at grid-template-columns 1fr 400px, .wizard-conflict-grid at minmax(0, 1fr) 132px 84px 196px 140px with its header-row, row and right-aligned decision-cell modifiers, .wizard-detail-rail with its head, body, footer, action-pair and key-hint rules, the answer card with its 1.5px marker and its chosen state, the bulk strip with its spacer, the tally, the standing note and the page hint, and the four-step rail. The rail carries Resolve.dc.html's own grid-column: 1 / -1 for fidelity with that rule and the declaration is inert under .wizard-middle's flex column, which the rule's comment says. Every dimension and colour is a named constant in this module. (refs: DL-199, DL-206, DL-207)
- **CI-M-001-003** `tests/test_gui_resolve_rules.py`: Guards over conflict_model's gate: an undecided group leaves the gate shut and names its count, a bulk resolution over an input index settles only the groups that collection holds a record in, and a pick names a candidate reference rather than a collection token. Each guard is proven to fail first, with the mutation and its verbatim output in the docstring. (refs: DL-204, DL-207, DL-209)
- **CI-M-001-004** `tests/test_gui_resolve_sheet.py`: Guards reading the emitted sheet's rule content: the split's two tracks, the grid's five tracks and its header row, the rail's 400px width and its three bands. Each asserts the rule's declaration rather than the presence of a class name, and each is proven to fail first with the verbatim output recorded. (refs: DL-206, DL-207, DL-209)

#### Code Changes

**CC-M-001-001** (traktor_nml/gui/conflict_model.py) - implements CI-M-001-001

**Code:**

```diff
diff --git a/traktor_nml/gui/conflict_model.py b/traktor_nml/gui/conflict_model.py
index be706ab..35c8a17 100644
--- a/traktor_nml/gui/conflict_model.py
+++ b/traktor_nml/gui/conflict_model.py
@@ -314,6 +314,67 @@ class ConflictDecisions:
         ]
 
 
+@dataclass(frozen=True)
+class ResolveGate:
+    """The resolve step's own gate: how many groups carry no answer,
+    how many carry one, and whether the step may be left.
+
+    One value carrying both, because the footer's sentence and the
+    advancing control's enabled state are one fact read twice: a count
+    computed for the sentence and an emptiness computed again for the
+    control can disagree, and the disagreement shows as a control the
+    operator can press over a sentence saying they cannot (DL-204).
+    """
+
+    outstanding: int
+    decided: int
+    all_decided: bool
+
+
+def resolve_gate(
+    decisions: ConflictDecisions, groups: Iterable[ConflictGroup]
+) -> ResolveGate:
+    """The gate over these groups: the count of undecided groups and
+    whether every one carries an answer.
+
+    groups is walked once and all_decided is derived from that one
+    count, so the two can never disagree. A group whose membership or
+    whose answers differ from the ones its held pick was made against
+    reads undecided here for the reason decision() gives, so a
+    re-preview offering different answers shuts the gate (DL-158,
+    DL-204).
+
+    No group at all reads zero outstanding and an open gate: a run that
+    reported no divergence has nothing to resolve, and the step it gates
+    is one the operator passes straight through.
+    """
+    held = list(groups)
+    outstanding = decisions.outstanding(held)
+    return ResolveGate(
+        outstanding=outstanding,
+        decided=len(held) - outstanding,
+        all_decided=outstanding == 0,
+    )
+
+
+def candidate_for_digit(
+    candidates: tuple[ConflictCandidate, ...], digit: int
+) -> Optional[ConflictCandidate]:
+    """The answer Specs' digit keys name, counting from one, or None
+    where the group offers no such answer.
+
+    Specs binds digits 1-9 to candidate picking and the page renders the
+    same digit beside each answer, so the digit and the position are one
+    fact and it is counted here rather than at a call site: a page
+    subtracting one itself would hold a decision rule the suite cannot
+    reach (DL-069, DL-071). A digit outside the group's answers reads
+    None rather than raising, which is the same answer keymap.dispatch
+    gives for a digit past the focused row's candidate count.
+    """
+    if digit < 1 or digit > len(candidates):
+        return None
+    return candidates[digit - 1]
+
+
 def write_refusal(
     result: Optional[SpliceResult],
     decisions: ConflictDecisions,

```

**Documentation:**

```diff
--- a/traktor_nml/gui/conflict_model.py
+++ b/traktor_nml/gui/conflict_model.py
@@ -326,6 +326,13 @@ class ResolveGate:
     operator can press over a sentence saying they cannot (DL-204).
     """
 
+    # Groups carrying no answer yet: the number the footer's sentence
+    # prints.
     outstanding: int
+    # Groups carrying one: the second number of the same sentence, held
+    # beside the first so the two are read off one walk rather than
+    # counted twice.
     decided: int
+    # Whether the resolve step may be left, which is `outstanding == 0`
+    # and not a second count over the groups (DL-204).
     all_decided: bool

```


**CC-M-001-002** (traktor_nml/gui/theme.py) - implements CI-M-001-002

**Code:**

```diff
diff --git a/traktor_nml/gui/theme.py b/traktor_nml/gui/theme.py
index 91b7dca..b9acad5 100644
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ -238,6 +238,39 @@ FOCUS_RING_OFFSET = "2px"
 CONTROL_HEIGHT = "32px"
 CONTROL_GAP = SPACE_8
 
+# Resolve.dc.html's own spacing steps, each named for the line that
+# states it: :53's .split gap (16px is SPACE_16 already), :55's .gr cell
+# padding, :57's .th cell padding, the .cand row gap, and the
+# .det-h/.det-b/.det-f insets. A step is a measured value and the rule
+# that spends it says which region it insets (DL-188).
+SPACE_3 = "3px"
+SPACE_7 = "7px"
+SPACE_13 = "13px"
+SPACE_14 = "14px"
+# Resolve.dc.html:53's .split - the content column beside the detail
+# rail, the rail at the width Review.dc.html's own .det carries.
+DETAIL_RAIL_WIDTH = "400px"
+# Resolve.dc.html:55's .gr grid-template-columns, held as one string
+# because the five tracks are one measurement: a column widened alone
+# moves every column beside it, and the header row and the body rows
+# read the identical string so a cell cannot align in one and not the
+# other.
+CONFLICT_GRID_TRACKS = "minmax(0, 1fr) 132px 84px 196px 140px"
+# Resolve.dc.html:23's .st .num - the step rail's own numbered marker,
+# a circle at this size holding the step number or its check mark.
+STEP_MARKER_SIZE = "19px"
+# Resolve.dc.html:79-81's .rad and the dot it carries when chosen. The
+# dot is an element the page renders only for the chosen answer rather
+# than a ::after on the marker, so what carries the chosen state is a
+# class string a guard can read at the call site (DL-189).
+ANSWER_MARKER_SIZE = "15px"
+ANSWER_MARKER_DOT_SIZE = "8px"
+# Resolve.dc.html:79's .rad carries a 1.5px border, thicker than the 1px
+# every other outline on the page takes, so the unchosen marker reads as
+# a control rather than as a hairline. Its own constant because it is the
+# one border width on this screen that is not 1px.
+ANSWER_MARKER_BORDER = "1.5px"
+
 
 def page_stylesheet() -> str:
     """The wizard's stylesheet as one string, every colour and size
@@ -459,4 +492,120 @@ body {{ background: {GROUND}; color: {TEXT}; font: 400 {TYPE_14}/1.45 {FONT_SANS
 /* Main.dc.html:30's .ft-note and :31's .ft-act. */
 .wizard-footer-note {{ margin: 0; font-size: {TYPE_12_5}; color: {TEXT_MUTED}; display: flex; align-items: center; gap: {SPACE_9}; }}
 .wizard-footer-actions {{ display: flex; align-items: center; gap: {SPACE_10}; flex: none; }}
+/* Resolve.dc.html:104's .steprail: the four-step rail as the page
+   region's first row. grid-column: 1 / -1 is carried here for fidelity
+   with the artboard's own declaration and is inert as the sheet stands:
+   .wizard-middle is display: flex; flex-direction: column, and
+   grid-column applies only to a grid item, so the rail already runs the
+   region's width because a flex column stretches it. The artboard's own
+   main is a single-column grid, where the declaration is equally inert.
+   Giving .wizard-middle a grid display is what would make it live. This
+   is a determinate reading of the sheet, not a question for the served
+   page (DL-189, DL-199). */
+.wizard-step-rail {{ display: flex; gap: {SPACE_2}; align-items: center; grid-column: 1 / -1; margin: 0; }}
+/* Resolve.dc.html:22's .st and :23's .num: one step of the rail and the
+   circular marker it carries. The marker takes its border from
+   currentColor, so a step's own ink is the only thing the two state
+   rules below change. */
+.wizard-step {{ display: flex; align-items: center; gap: {SPACE_8}; padding: {SPACE_6} {SPACE_12}; border-radius: {RADIUS_LG}; font-size: {TYPE_12_5}; color: {TEXT_FAINT}; white-space: nowrap; }}
+.wizard-step-number {{ font: 600 {TYPE_11}/1 {FONT_MONO}; width: {STEP_MARKER_SIZE}; height: {STEP_MARKER_SIZE}; border-radius: 50%; display: grid; place-items: center; border: 1px solid currentColor; flex: none; }}
+/* Resolve.dc.html:24's .st.done and :25-26's .st.now. Both are declared
+   after .wizard-step so the ink of a done or a current step wins at
+   equal specificity, the same ordering .wizard-tab-selected takes
+   against .wizard-tab. */
+.wizard-step-done {{ color: {TEXT_MUTED}; }}
+.wizard-step-current {{ background: {SURFACE_4}; color: {TEXT}; box-shadow: inset 0 0 0 {SPACE_1} {BORDER_STRONG}; font-weight: 600; }}
+/* Resolve.dc.html:26's .st.now .num: the current step's marker,
+   carrying the action blue as its ground and the page ground as its
+   ink - the same pair .wizard-control-primary carries. Its own class
+   rather than a descendant of .wizard-step-current, so the ink is read
+   against the ground the marker actually paints rather than against
+   the ground of the step around it. */
+.wizard-step-number-current {{ background: {ACTION}; border-color: {ACTION}; color: {GROUND}; }}
+/* Resolve.dc.html:41's .fbar and :98's .tally: the strip carrying the
+   bulk actions, and the count sentence at its left. Resolve.dc.html:131
+   sets the two apart with a flex:1 span, so the count reads from the
+   strip's left and the bulk actions from its right. */
+.wizard-bulk-strip {{ display: flex; align-items: center; gap: {SPACE_9}; flex-wrap: wrap; row-gap: {SPACE_9}; }}
+.wizard-strip-spacer {{ flex: 1; }}
+.wizard-tally {{ display: flex; align-items: center; gap: {SPACE_9}; font-size: {TYPE_12_5}; color: {TEXT_MUTED}; white-space: nowrap; margin: 0; }}
+/* Resolve.dc.html:53's .split: the conflict table at the left taking
+   what is left, the detail rail at the right at its fixed width. */
+.wizard-resolve-split {{ display: grid; grid-template-columns: 1fr {DETAIL_RAIL_WIDTH}; gap: {SPACE_16}; min-height: 0; }}
+/* Resolve.dc.html:54's .tbl and :55's .gr: the bordered box the rows
+   sit in, and the five-track grid a header row and every body row are
+   laid out on. Both rows read CONFLICT_GRID_TRACKS, so a cell cannot
+   align in the header and not in the body. */
+.wizard-conflict-table {{ border: 1px solid {BORDER}; border-radius: {RADIUS_XL}; background: {SURFACE_2}; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }}
+.wizard-conflict-grid {{ display: grid; grid-template-columns: {CONFLICT_GRID_TRACKS}; align-items: center; }}
+/* Resolve.dc.html:56-57's .th: the header row's own ground, the rule
+   below it and the mono label its cells carry. */
+.wizard-conflict-header {{ border-bottom: 1px solid {BORDER_STRONG}; background: {SURFACE_3}; }}
+.wizard-conflict-header > * {{ padding: {SPACE_10} {SPACE_12}; font: 600 {TYPE_11}/1.2 {FONT_MONO}; letter-spacing: .07em; text-transform: uppercase; color: {TEXT_FAINT}; }}
+/* Resolve.dc.html:58-59's .tr: the rule under each body row and the
+   inset its cells carry. min-width: 0 is what lets a cell ellipsis
+   inside its own track rather than widening it. */
+.wizard-conflict-row {{ border-bottom: 1px solid {SURFACE_5}; }}
+.wizard-conflict-row > * {{ padding: {SPACE_10} {SPACE_12}; min-width: 0; }}
+/* Resolve.dc.html:60's .tr.sel: the selected row's tinted ground and
+   the action-blue marker inset at its leading edge. */
+.wizard-conflict-row-selected {{ background: {ACTION_TINT_BG_ALT}; box-shadow: inset {SPACE_3} 0 0 {ACTION}; }}
+/* Resolve.dc.html:70's .det and :71, :74, :91's .det-h, .det-b and
+   .det-f: the rail as a bordered column of three bands - a head naming
+   the file, a body holding one control per answer, and a footer holding
+   the keys and the rail's own actions. The rail takes its width from
+   .wizard-resolve-split's second track, so DETAIL_RAIL_WIDTH is
+   written once. */
+.wizard-detail-rail {{ border: 1px solid {ACTION_TINT_BORDER_ALT}; border-radius: {RADIUS_XL}; background: {BORDER_SUBTLE_2}; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }}
+.wizard-detail-head {{ padding: {SPACE_12} {SPACE_14}; border-bottom: 1px solid {BORDER_SUBTLE_5}; display: flex; flex-direction: column; gap: {SPACE_4}; }}
+.wizard-detail-body {{ padding: {SPACE_12} {SPACE_14}; display: flex; flex-direction: column; gap: {SPACE_13}; flex: 1; min-height: 0; }}
+.wizard-detail-foot {{ padding: {SPACE_11} {SPACE_14}; border-top: 1px solid {BORDER_SUBTLE_5}; display: flex; flex-direction: column; gap: {SPACE_9}; }}
+/* Resolve.dc.html:75's .grp and :76's .grp-h: one answer's own block
+   inside the rail's body, and the label row above it carrying the
+   digit that picks it. */
+.wizard-answer-group {{ display: flex; flex-direction: column; gap: {SPACE_7}; }}
+.wizard-answer-group-head {{ display: flex; align-items: center; justify-content: space-between; gap: {SPACE_8}; }}
+/* Resolve.dc.html:77's .cand and :78's .cand.on: one control per
+   distinct answer, and the chosen one's own border and ground. */
+.wizard-answer {{ border: 1px solid {BORDER}; background: {ACTION_TINT_BG}; border-radius: {RADIUS_LG}; padding: {SPACE_8} {SPACE_10}; display: flex; gap: {SPACE_9}; align-items: center; }}
+.wizard-answer-chosen {{ border-color: {ACTION_TINT_BORDER_ALT}; background: {BORDER_SUBTLE_9}; }}
+/* Resolve.dc.html:79's .rad and :81's dot. The dot is its own element,
+   rendered for the chosen answer alone, so what carries the chosen
+   state is a class string at a call site rather than a pseudo-element
+   no guard can read (DL-189). */
+.wizard-answer-marker {{ width: {ANSWER_MARKER_SIZE}; height: {ANSWER_MARKER_SIZE}; border-radius: 50%; border: {ANSWER_MARKER_BORDER} solid {NEUTRAL_INACTIVE}; flex: none; display: grid; place-items: center; }}
+.wizard-answer-chosen .wizard-answer-marker {{ border-color: {ACTION}; }}
+.wizard-answer-dot {{ width: {ANSWER_MARKER_DOT_SIZE}; height: {ANSWER_MARKER_DOT_SIZE}; border-radius: 50%; background: {ACTION}; }}
+/* Resolve.dc.html:68's .dec and :69's .decd: the decision column reads
+   from its right edge in both states - a Choose control while the group
+   is undecided, the winning collection's name beside its own Undo once
+   it is decided. The header's fifth cell is right-aligned by the same
+   reading (Resolve.dc.html:141), so the heading sits over the column it
+   names rather than over the column's empty left. The gap is
+   CONTROL_GAP, not the 6px the artboard's own .dec draws: Specs' 8px
+   between controls is the settled reading wherever the two disagree,
+   which is the divergence "The gap between decision buttons" already
+   records for Review.dc.html's identical pair (DL-088). */
+.wizard-conflict-decision {{ display: flex; gap: {CONTROL_GAP}; justify-content: flex-end; }}
+.wizard-conflict-decided {{ display: flex; align-items: center; gap: {CONTROL_GAP}; justify-content: flex-end; font-size: {TYPE_11_5}; font-weight: 600; white-space: nowrap; }}
+.wizard-conflict-header > *:last-child {{ text-align: right; }}
+/* Resolve.dc.html:92's .det-a and :93's .det-a .btn: the rail's two
+   actions split the footer's width between them, which is why this is
+   its own rule rather than .wizard-control-group - that one packs its
+   controls to the left at their own widths. */
+.wizard-detail-actions {{ display: flex; gap: {SPACE_8}; }}
+.wizard-detail-actions .wizard-control {{ flex: 1; justify-content: center; }}
+/* Resolve.dc.html:94's .keys and :95's .kb: three key hints, each a chip
+   group beside the phrase it performs, rather than one sentence naming
+   the keys in prose - the chips are what Specs' keyboard map draws. */
+.wizard-key-row {{ display: flex; align-items: center; gap: {SPACE_13}; flex-wrap: wrap; padding: {SPACE_1} 0 {SPACE_8}; }}
+.wizard-key-hint {{ display: inline-flex; align-items: center; gap: {SPACE_6}; font-size: {TYPE_11_5}; color: {TEXT_FAINT}; }}
+/* Resolve.dc.html:245's .note in the rail's body and :266's .hint under
+   main. .wizard-hint reproduces Resolve.dc.html:100's .hint rule; the
+   artboard declares no rule for .note, and that note sets no colour, so
+   the call site names the ink token it wears and one element cannot end
+   up carrying two colour-setting classes, which tests/test_gui_theme.py
+   holds over every classes() call. */
+.wizard-note {{ display: flex; gap: {SPACE_8}; font-size: {TYPE_12}; line-height: 1.45; }}
+.wizard-hint {{ margin: 0; font-size: {TYPE_12}; color: {TEXT_FAINT}; display: flex; align-items: center; gap: {SPACE_8}; padding-bottom: {SPACE_8}; }}
 """

```

**Documentation:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ -598,5 +598,8 @@
 /* Resolve.dc.html:94's .keys and :95's .kb: three key hints, each a chip
    group beside the phrase it performs, rather than one sentence naming
    the keys in prose - the chips are what Specs' keyboard map draws. */
+/* The chips themselves are .wizard-kbd, the rule emitted above; these
+   two rules set the row and the hint around them, so a key chip reads
+   the same here as it does wherever else the page names one. */
 .wizard-key-row {{ display: flex; align-items: center; gap: {SPACE_13}; flex-wrap: wrap; padding: {SPACE_1} 0 {SPACE_8}; }}
 .wizard-key-hint {{ display: inline-flex; align-items: center; gap: {SPACE_6}; font-size: {TYPE_11_5}; color: {TEXT_FAINT}; }}

```


**CC-M-001-003** (tests/test_gui_resolve_rules.py) - implements CI-M-001-003

**Code:**

```diff
diff --git a/tests/test_gui_resolve_rules.py b/tests/test_gui_resolve_rules.py
new file mode 100644
index 0000000..7842e5f
--- /dev/null
+++ b/tests/test_gui_resolve_rules.py
@@ -0,0 +1,212 @@
+"""Guards for the resolve step's own rules in
+traktor_nml/gui/conflict_model.py: the gate the footer's sentence and the
+advancing control both read, the digit-to-answer lookup Specs' keyboard
+map needs, and the two rules a bulk action and a pick already carry, read
+through the gate rather than through a count of their own.
+
+Every guard here runs under the system interpreter, which has no nicegui:
+conflict_model imports none, which is what puts the resolve step's
+decision rules on the side the suite can reach (DL-069, DL-204).
+
+Each guard records the mutation applied to make it fail and the verbatim
+output observed under that mutation, in the register
+tests/test_gui_conflict_model.py uses.
+"""
+
+from __future__ import annotations
+
+from traktor_nml.gui import conflict_model
+from traktor_nml.splice import ConflictCandidate
+
+
+def _group(key: str, *answers: tuple[str, tuple[int, ...]]) -> conflict_model.ConflictGroup:
+    """One group over `answers`, each an (value, input indices) pair.
+
+    Every member carries `key` as its primary key, which is what a
+    location-derived key does for one file held by several collections
+    (DL-004, DL-148); the input index is what tells the records apart.
+    """
+    candidates = tuple(
+        ConflictCandidate(
+            values=(value,), members=tuple((index, key) for index in indices)
+        )
+        for value, indices in answers
+    )
+    return conflict_model.ConflictGroup(
+        identity_key=key,
+        attrs=("title",),
+        member_keys=frozenset({key}),
+        candidates=candidates,
+    )
+
+
+def _two_groups() -> list:
+    """Two groups: the first held by all three collections, the second by
+    the collection being repaired and the source at index 1 alone, so a
+    bulk action for index 2 has an answer for one and none for the other.
+    """
+    return [
+        _group("track.mp3", ("Base", (0,)), ("Alpha", (1,)), ("Bravo", (2,))),
+        _group("absent.mp3", ("Base", (0,)), ("Alpha", (1,))),
+    ]
+
+
+def test_an_undecided_group_leaves_the_gate_shut_and_names_its_count():
+    """One group decided of two reads one outstanding, one decided and a
+    shut gate; deciding the second reads zero outstanding, two decided
+    and an open gate. The count and the gate come from one walk, so the
+    sentence the footer prints and the state of the advancing control
+    cannot disagree (DL-204).
+
+    Mutation: resolve_gate's `all_decided=outstanding == 0` was replaced
+    with `all_decided=True` in traktor_nml/gui/conflict_model.py and this
+    guard rerun. Observed:
+        E       AssertionError: one group undecided must shut the gate
+        E       assert not True
+        E        +  where True = ResolveGate(outstanding=1, decided=1, all_decided=True).all_decided
+    """
+    groups = _two_groups()
+    decisions = conflict_model.ConflictDecisions()
+    decisions.resolve(groups[0], (2, "track.mp3"))
+
+    gate = conflict_model.resolve_gate(decisions, groups)
+    assert gate.outstanding == 1
+    assert gate.decided == 1
+    assert not gate.all_decided, "one group undecided must shut the gate"
+
+    decisions.resolve(groups[1], (1, "absent.mp3"))
+    settled = conflict_model.resolve_gate(decisions, groups)
+    assert settled.outstanding == 0
+    assert settled.decided == 2
+    assert settled.all_decided
+
+
+def test_no_groups_at_all_reads_an_open_gate():
+    """A run that reported no divergence has nothing to resolve, so the
+    gate over an empty group set is open at zero outstanding rather than
+    shut on an absent answer.
+
+    Mutation: resolve_gate's `all_decided=outstanding == 0` was replaced
+    with `all_decided=len(held) > 0 and outstanding == 0` and this guard
+    rerun. Observed:
+        E       AssertionError: an empty group set must leave the gate open
+        E       assert False
+        E        +  where False = ResolveGate(outstanding=0, decided=0, all_decided=False).all_decided
+    """
+    gate = conflict_model.resolve_gate(conflict_model.ConflictDecisions(), [])
+    assert gate.outstanding == 0
+    assert gate.decided == 0
+    assert gate.all_decided, "an empty group set must leave the gate open"
+
+
+def test_a_bulk_resolution_settles_only_the_groups_that_collection_holds():
+    """A bulk action for the source at input index 2 settles the group
+    that source holds a record in and leaves the other one counted by the
+    gate, rather than taking someone else's answer for it (DL-154).
+
+    Index 2 is the second source added, which the run-wide keep-first
+    picker would not choose, so this cannot pass by coinciding with that
+    picker's own answer.
+
+    Mutation: resolve_all's `if reference is not None:` in
+    traktor_nml/gui/conflict_model.py was replaced with
+    `if reference is None: reference = candidate_reference(group.candidates[0])`
+    followed by the unconditional resolve, and this guard rerun.
+    Observed:
+        E       AssertionError: a group the collection holds no record in must stay undecided
+        E       assert 0 == 1
+        E        +  where 0 = ResolveGate(outstanding=0, decided=2, all_decided=True).outstanding
+    """
+    groups = _two_groups()
+    decisions = conflict_model.ConflictDecisions()
+    decisions.resolve_all(groups, conflict_model.reference_from_input(2))
+
+    gate = conflict_model.resolve_gate(decisions, groups)
+    assert gate.outstanding == 1, (
+        "a group the collection holds no record in must stay undecided"
+    )
+    assert decisions.resolutions(groups) == {"track.mp3": (2, "track.mp3")}
+
+
+def test_a_pick_names_a_candidate_reference_rather_than_a_collection_token():
+    """The resolution a pick records is the (input index, primary key)
+    pair naming the record that wins, not a base-or-source word: one file
+    held by two collections carries the identical location-derived key,
+    so the pair is the only thing that tells the two records apart
+    (DL-004, DL-148).
+
+    Mutation: resolve()'s recorded value was replaced with
+    `_Decision("source", group.member_keys, group.candidates)` in
+    traktor_nml/gui/conflict_model.py and this guard rerun. Observed:
+        E       AssertionError: a resolution names the record that wins, as an (input index, primary key [...]
+        E       assert 'source' == (2, 'track.mp3')
+    """
+    groups = _two_groups()
+    decisions = conflict_model.ConflictDecisions()
+    decisions.resolve(groups[0], (2, "track.mp3"))
+
+    held = decisions.resolutions(groups)["track.mp3"]
+    assert held == (2, "track.mp3"), (
+        "a resolution names the record that wins, as an "
+        "(input index, primary key) pair"
+    )
+    assert not isinstance(held, str)
+
+
+def test_two_collections_holding_one_answer_are_one_candidate():
+    """A group whose two sources hold identical values offers two answers
+    over three records, and deciding the shared one settles both sources
+    at once - the reference recorded is the contributor of lowest input
+    index (DL-148, DL-150).
+
+    Mutation: candidate_reference's `candidate.members[0]` was replaced
+    with `candidate.members[-1]` in traktor_nml/gui/conflict_model.py and
+    this guard rerun. Observed:
+        E       AssertionError: the shared answer records its lowest contributor
+        E       assert (2, 'track.mp3') == (1, 'track.mp3')
+        E
+        E         At index 0 diff: 2 != 1
+        E         Use -v to get more diff
+    """
+    group = _group("track.mp3", ("Base", (0,)), ("Agreed", (1, 2)))
+    decisions = conflict_model.ConflictDecisions()
+    decisions.resolve(group, (2, "track.mp3"))
+
+    assert decisions.resolutions([group])["track.mp3"] == (1, "track.mp3"), (
+        "the shared answer records its lowest contributor"
+    )
+    assert conflict_model.resolve_gate(decisions, [group]).all_decided
+
+
+def test_a_digit_names_the_answer_at_that_position_counting_from_one():
+    """Specs binds digits 1-9 to candidate picking, and the page renders
+    the same digit beside each answer, so digit 1 names the first answer
+    and a digit past the group's answers names none (DL-071).
+
+    Mutation: candidate_for_digit's `candidates[digit - 1]` was replaced
+    with `candidates[digit]` in traktor_nml/gui/conflict_model.py and
+    this guard rerun. Observed:
+        E       AssertionError: digit 1 names the first answer
+        E       assert ConflictCandi...track.mp3'),)) == ConflictCandi...track.mp3'),))
+        E
+        E         Differing attributes:
+        E         ['values', 'members']
+        E
+    """
+    group = _group("track.mp3", ("Base", (0,)), ("Alpha", (1,)))
+    first = conflict_model.candidate_for_digit(group.candidates, 1)
+    assert first == group.candidates[0], "digit 1 names the first answer"
+    assert conflict_model.candidate_for_digit(group.candidates, 2) == group.candidates[1]
+    assert conflict_model.candidate_for_digit(group.candidates, 3) is None
+    assert conflict_model.candidate_for_digit(group.candidates, 0) is None
+
+
+# conflict_model's freedom from nicegui is enforced by the AST walk in
+# tests/test_gui_view_boundary.py, which reads every module under
+# traktor_nml/gui/ against the allowlist DL-069 names and is the one
+# place that rule is held. A second reading here would either duplicate
+# that walk or, read as file text, forbid this module from naming the
+# framework in a comment describing its own boundary. What the guards
+# above hold instead is the consequence: each runs under the system
+# interpreter, which has no nicegui installed, so an import added to
+# conflict_model.py stops this whole file at collection.

```

**Documentation:**

```diff
--- a/tests/test_gui_resolve_rules.py
+++ b/tests/test_gui_resolve_rules.py
@@ -8,6 +8,12 @@
 conflict_model imports none, which is what puts the resolve step's
 decision rules on the side the suite can reach (DL-069, DL-204).
 
+What no guard here holds is that the page reads the gate rather than
+counting the undecided groups itself. That reading is an AST walk over
+app.py and it lives in
+tests/test_gui_conflict_page_controls.py::test_no_decision_arithmetic_is_written_inline,
+so the rule and its single call site are held on their own terms.
+
 Each guard records the mutation applied to make it fail and the verbatim
 output observed under that mutation, in the register
 tests/test_gui_conflict_model.py uses.

```


**CC-M-001-004** (tests/test_gui_resolve_sheet.py) - implements CI-M-001-004

**Code:**

```diff
diff --git a/tests/test_gui_resolve_sheet.py b/tests/test_gui_resolve_sheet.py
new file mode 100644
index 0000000..a49b949
--- /dev/null
+++ b/tests/test_gui_resolve_sheet.py
@@ -0,0 +1,212 @@
+"""Guards the resolve step's rules as traktor_nml/gui/theme.py emits
+them, read out of the returned sheet under the system interpreter, which
+has no nicegui.
+
+What a guard here asserts is a rule's own declaration. What it cannot
+assert is that the browser laid the step out that way: theme.FONT_SANS
+named IBM Plex throughout the period the page painted Segoe UI, so a
+guard that reads a name is true in exactly the broken state. The resolved
+column widths, the rail's rendered width and the rail's position across
+the page region belong to the served-page record (DL-189).
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
+    """Everything the sheet declares for one selector, as one block.
+
+    Read out of page_stylesheet()'s return value rather than out of
+    theme.py's source, so a constant renamed or a value interpolated from
+    somewhere else is still read as the sheet emits it. The selector is
+    anchored on a brace so `.wizard-answer` does not also collect
+    `.wizard-answer-chosen`'s block.
+    """
+    blocks = re.findall(
+        re.escape(selector) + r"\s*\{([^}]*)\}", theme.page_stylesheet()
+    )
+    assert blocks, f"the stylesheet emits no {selector} rule"
+    return "".join(blocks)
+
+
+def test_the_split_declares_the_content_column_beside_the_400px_rail():
+    """Resolve.dc.html:53's .split is
+    `grid-template-columns: 1fr 400px`, the content column taking what is
+    left beside a rail at a fixed width, and the sheet declares the same
+    two tracks.
+
+    Mutation: DETAIL_RAIL_WIDTH was changed from "400px" to "360px" in
+    theme.py and this guard rerun. Observed:
+        E       AssertionError: assert '360px' == '400px'
+        E
+        E         - 400px
+        E         + 360px
+    """
+    assert theme.DETAIL_RAIL_WIDTH == "400px"
+    assert "grid-template-columns: 1fr 400px" in _rule(".wizard-resolve-split"), (
+        ".wizard-resolve-split declares tracks other than 1fr 400px"
+    )
+    assert "display: grid" in _rule(".wizard-resolve-split")
+
+
+def test_the_conflict_grid_declares_the_five_tracks_the_artboard_draws():
+    """Resolve.dc.html:55's .gr is `grid-template-columns: minmax(0,1fr)
+    132px 84px 196px 140px` - the track column taking what is left and
+    four fixed columns beside it - and the sheet declares the same five.
+
+    Mutation: the third track was changed from 84px to 96px in
+    CONFLICT_GRID_TRACKS in theme.py and this guard rerun. Observed:
+        E       AssertionError: assert 'minmax(0, 1f...x 196px 140px' == 'minmax(0, 1f...x 196px 140px'
+        E
+        E         - minmax(0, 1fr) 132px 84px 196px 140px
+        E         ?                      ^^
+        E         + minmax(0, 1fr) 132px 96px 196px 140px
+        E         ?                      ^^
+    """
+    assert theme.CONFLICT_GRID_TRACKS == "minmax(0, 1fr) 132px 84px 196px 140px"
+    assert (
+        f"grid-template-columns: {theme.CONFLICT_GRID_TRACKS}"
+        in _rule(".wizard-conflict-grid")
+    ), ".wizard-conflict-grid declares tracks other than the artboard's five"
+
+
+def test_the_header_row_sits_on_the_same_tracks_as_the_body_rows():
+    """Resolve.dc.html:56's .th is a modifier on .gr rather than a grid of
+    its own, so the header row and the body rows are laid out on one set
+    of tracks. The sheet's header rule therefore declares the row's own
+    ground and rule and no tracks at all, and its cells carry the mono
+    label the artboard draws.
+
+    A header rule declaring tracks of its own is the failure this holds:
+    two grids drift, and a heading stops standing over its column.
+
+    Mutation: `grid-template-columns: 1fr 1fr 1fr 1fr 1fr; ` was added to
+    the .wizard-conflict-header rule in page_stylesheet() and this guard
+    rerun. Observed:
+        E       AssertionError: the header row must take .wizard-conflict-grid's tracks, not declare its [...]
+        E       assert 'grid-template-columns' not in ' grid-templ...d: #1F2225; '
+        E
+        E         'grid-template-columns' is contained here:
+        E            grid-template-columns: 1fr 1fr 1fr 1fr 1fr; border-bottom: 1px solid #3C4248; backg [...]
+        E         ?  +++++++++++++++++++++
+    """
+    header = _rule(".wizard-conflict-header")
+    assert "grid-template-columns" not in header, (
+        "the header row must take .wizard-conflict-grid's tracks, not declare its own"
+    )
+    assert f"background: {theme.SURFACE_3}" in header
+    assert f"border-bottom: 1px solid {theme.BORDER_STRONG}" in header
+    assert theme.FONT_MONO in _rule(".wizard-conflict-header > *")
+
+
+def test_the_detail_rail_carries_its_three_bands():
+    """Resolve.dc.html:70 draws .det as a bordered column and :71, :74 and
+    :87 draw its head, its body and its footer. The sheet emits one rule
+    per band, each carrying the inset and the edge rule that separates it
+    from the band beside it, and the rail itself carries no width: it
+    takes the second track of .wizard-resolve-split, so the 400px is
+    written once.
+
+    Mutation: `width: {DETAIL_RAIL_WIDTH}; ` was added to the
+    .wizard-detail-rail rule in page_stylesheet() and this guard rerun.
+    Observed:
+        E       AssertionError: the rail takes its width from the split's second track
+        E       assert 'width' not in ' width: 400...ow: hidden; '
+        E
+        E         'width' is contained here:
+        E            width: 400px; border: 1px solid #2F5A72; border-radius: 8px; background: #141C21; d [...]
+        E         ?  +++++
+    """
+    rail = _rule(".wizard-detail-rail")
+    assert "flex-direction: column" in rail
+    assert "width" not in rail, (
+        "the rail takes its width from the split's second track"
+    )
+    assert f"border-bottom: 1px solid {theme.BORDER_SUBTLE_5}" in _rule(
+        ".wizard-detail-head"
+    )
+    assert "flex: 1" in _rule(".wizard-detail-body")
+    assert f"border-top: 1px solid {theme.BORDER_SUBTLE_5}" in _rule(
+        ".wizard-detail-foot"
+    )
+
+
+def test_the_answer_control_carries_its_chosen_state_as_its_own_rule():
+    """Resolve.dc.html:77's .cand and :78's .cand.on: one control per
+    answer, and the chosen one's own border and ground. The chosen rule is
+    declared after the base rule, so the chosen border wins at equal
+    specificity, and the dot the chosen marker carries is its own rule
+    rather than a pseudo-element, since a call site can name a class and
+    cannot name a ::after (DL-189).
+
+    Mutation: the .wizard-answer-chosen rule was moved above the
+    .wizard-answer rule in page_stylesheet() and this guard rerun.
+    Observed:
+        E       AssertionError: the chosen rule must be declared after the base rule
+        E       assert 20675 > 20745
+        E        +  where 20675 = <built-in method index of str object at [...]
+        E        +  and   20745 = <built-in method index of str object at [...]
+    """
+    sheet = theme.page_stylesheet()
+    assert sheet.index(".wizard-answer-chosen {") > sheet.index(".wizard-answer {"), (
+        "the chosen rule must be declared after the base rule"
+    )
+    assert f"background: {theme.ACTION}" in _rule(".wizard-answer-dot")
+    assert f"width: {theme.ANSWER_MARKER_SIZE}" in _rule(".wizard-answer-marker")
+
+
+def test_the_step_rail_carries_the_artboards_span_declaration():
+    """Resolve.dc.html:104's .steprail carries `grid-column: 1 / -1`, and
+    the sheet carries the same declaration for fidelity with the
+    artboard's rule.
+
+    The declaration is inert as the sheet stands, and this guard claims
+    no more than that it is present: `grid-column` applies to a grid
+    item, and the rail's parent `.wizard-middle` is
+    `display: flex; flex-direction: column`, so the rail runs the
+    region's width because a flex column stretches it rather than
+    because of this rule. The artboard's own `main` is a single-column
+    grid, where the declaration is equally inert. A name claiming the
+    rail spans the region would be claiming a rendered fact this
+    reading knows to be produced by something else (DL-165, DL-189,
+    DL-199).
+
+    Mutation: `grid-column: 1 / -1; ` was deleted from the
+    .wizard-step-rail rule in page_stylesheet() and this guard rerun.
+    Observed:
+        E       AssertionError: the step rail must span the page region's columns
+        E       assert 'grid-column: 1 / -1' in ' display: flex; gap: 2px; align-items: center; margin:  [...]
+    """
+    rail = _rule(".wizard-step-rail")
+    assert "grid-column: 1 / -1" in rail, (
+        "the step rail must span the page region's columns"
+    )
+    assert "display: flex" in rail
+
+
+def test_the_current_step_marker_carries_the_action_ground_and_the_page_ink():
+    """Resolve.dc.html:26's .st.now .num: the current step's marker
+    carries the action blue as its ground and the page ground as its ink.
+    It is its own class rather than a rule descending from the current
+    step, so the ink is read against the ground the marker paints.
+
+    Mutation: `background: {ACTION}; ` was deleted from the
+    .wizard-step-number-current rule in page_stylesheet() and this guard
+    rerun. Observed:
+        E       AssertionError: the current marker must carry the action ground under its ink
+        E       assert 'background: #56B4E9' in ' border-color: #56B4E9; color: #0F1113; '
+    """
+    marker = _rule(".wizard-step-number-current")
+    assert f"background: {theme.ACTION}" in marker, (
+        "the current marker must carry the action ground under its ink"
+    )
+    assert f"color: {theme.GROUND}" in marker
+    assert f"width: {theme.STEP_MARKER_SIZE}" in _rule(".wizard-step-number")

```

**Documentation:**

```diff
--- a/tests/test_gui_resolve_sheet.py
+++ b/tests/test_gui_resolve_sheet.py
@@ -29,6 +29,11 @@ def _rule(selector: str) -> str:
     somewhere else is still read as the sheet emits it. The selector is
     anchored on a brace so `.wizard-answer` does not also collect
     `.wizard-answer-chosen`'s block.
+
+    A selector the sheet emits no rule for fails here as a missing rule
+    rather than reading back as an empty declaration, so a guard below
+    asserting what a rule contains cannot pass over a rule that is not
+    emitted at all.
     """
     blocks = re.findall(
         re.escape(selector) + r"\s*\{([^}]*)\}", theme.page_stylesheet()

```


### Milestone 2: The four-step scaffold and the resolve screen

**Files**: traktor_nml/gui/reconstruct_steps.py, traktor_nml/gui/app.py, tests/test_gui_reconstruct_steps.py, tests/test_gui_resolve_composition.py, tests/test_gui_keymap.py, docs/2026-09-07-reconstruct-resolve-browser-record.md, docs/CLAUDE.md

**Flags**: error-handling, needs-rationale

**Requirements**:

- reconstruct_steps.py holds the four-step table, the rail records and the reachability predicate, and imports no nicegui (DL-203).
- The / route composes four step regions inside the chrome's middle, one visible at a time, with the rail rendered as the page's first row from reconstruct_steps.rail_records (DL-199, DL-202).
- Steps 1, 2 and 4 hold today's cards, holders and callbacks unchanged (DL-208).
- Step 3 composes the tally and bulk strip above the split, the conflict grid under its header row, and the 400px detail rail with one control per distinct answer keyed on candidate_reference and one bulk action per input collection keyed on reference_from_input (DL-148, DL-206, DL-207).
- The footer's count and the advancing control's enabled state come from one resolve_gate call (DL-204).
- Digits 1-9 resolve through keymap.dispatch at SCOPE_TABLE; keymap.py is NOT edited; the reconstruct route carries its own name-to-applier mapping (DL-205).
- app.py is read and written with newline='' and stays 100% CRLF; every class string is a literal at the call site and no dimension or hex is written there.
- M-002's record closes M-001 as well as M-002: it carries a verdict and a structural reading for each rule M-001 emits alongside its own surfaces (DL-210).
- The record is named for the day its run happens. Every filename and citation here reads 2026-09-07; if the run lands on a later day, the filename, the docs/CLAUDE.md index row and every citation of it take that day's date instead.
- docs/CLAUDE.md's Files table carries a row for docs/2026-09-07-reconstruct-resolve-browser-record.md, and that row lands in the commit that writes the record, so the index names every record the directory holds. docs/CLAUDE.md is CRLF apart from one pre-existing bare LF: the inserted row ends CRLF and no other line is rewritten.

**Acceptance Criteria**:

- rail_records yields four records in rail order with exactly one current, the rows before it done and the rows after upcoming.
- reachable refuses a step past a shut gate.
- The served page at / shows four step regions with one visible, the rail as the page's first row, and step 3 rendering the tally, the bulk strip, the grid under its header row and the 400px rail.
- With one group undecided the footer names the outstanding count and the advancing control is disabled; with every group decided the count is zero and the control is enabled.
- A digit key on the resolve table picks that candidate; an action name not in the reconstruct mapping is a test failure, not a silent no-op.
- tests/test_gui_view_boundary.py, tests/test_gui_theme.py and tests/test_gui_keymap.py pass.
- docs/2026-09-07-reconstruct-resolve-browser-record.md exists, is driven over HTTP, carries a matches-or-differs verdict plus a structural reading per named surface, and retakes the keyboard and announcement readings, and names among its surfaces every rule M-001 emits - the resolve split at 1fr 400px, the conflict grid's five tracks and its header row, the detail rail's head, body and footer, the answer card and its chosen state, the bulk strip, the tally and the step rail - so no M-001 rule reaches the tree without a served-page reading (DL-210).
- Every new guard has been run against its specific mutation and FAILED, with the mutation and the verbatim failure output recorded in its docstring.
- git diff on app.py shows only the changed lines, no whole-file rewrite.
- If any of the reconstruct page's three structures - the split's two columns, the grid's five tracks under its header row, the rail's 400px - reads `differs` in this record, the milestone does not close: the composition is corrected and the record retaken. Only where a run shows the framework refusing the rule outright does a 'Composition not built' entry for `/` get written, naming exactly what was refused and nothing more, and DL-201's statement is narrowed in M-003 to the structures that did build (DL-190, DL-194, DL-201).
- The DL-198..DL-212 numbers this milestone's code, comments and guard docstrings cite are forward references: their statements land in M-003's commit in W-003, and the plan is not complete at the end of W-002 (DL-212).
- The commit that writes docs/2026-09-07-reconstruct-resolve-browser-record.md names docs/CLAUDE.md as well, git diff on docs/CLAUDE.md shows one added line and no others, and the file's CRLF count is one higher with its single bare LF untouched.

**Tests**:

- tests/test_gui_reconstruct_steps.py: four rows in rail order, exactly one current, done before and upcoming after, reachability refused past a shut gate.
- tests/test_gui_resolve_composition.py: four step regions constructed in rail order; the resolve region naming the split, grid, header-row and rail class strings; one control per candidate and one bulk control per input collection; a footer action group registered per step; the advancing control's enabled state read from a single conflict_model call; the nicegui boundary and the literal-class rules holding.
- tests/test_gui_keymap.py: the reconstruct route's applier mapping's key set is a subset of keymap.ACTION_NAMES and covers every action the resolve table answers.
- The served-page record is the pass condition; the guards are the regression net.
- docs/CLAUDE.md: the record's row read back out of the Files table, and the file's line endings counted - CRLF everywhere but the one bare LF that already stands.

#### Code Intent

- **CI-M-002-001** `traktor_nml/gui/reconstruct_steps.py::STEPS`: The four-step table pairs each step's number with its rail label: 1 Set up, 2 Preview, 3 Resolve, 4 Write. rail_records(current) derives one record per row carrying the number, the label, whether the row reads done, current or upcoming, its class string and its aria-current value, exactly one row current at a time. reachable(current, gate) decides which step the page may show. The module imports no nicegui. (refs: DL-202, DL-203)
- **CI-M-002-002** `traktor_nml/gui/app.py::reconstruct`: The route composes four step regions inside the chrome's middle, one visible at a time, with the rail rendered as the page's first row from reconstruct_steps.rail_records. Steps 1, 2 and 4 hold the cards, holders and callbacks the page composes today. Step 3 holds the tally and bulk strip above a .wizard-resolve-split: the conflict grid under its header row at the left, its decision column right-aligned and carrying a per-row Undo once a group is decided, and the 400px detail rail at the right carrying the file, one control per distinct answer, the standing note on what a pick names, three key-hint chip groups and a footer pair whose primary takes the first answer. The tally's collection count is the length of the label list the run built, not the two the artboard's illustrative copy names, and a hint under the split says what a bulk decision leaves untouched. Each step registers its footer note and action group in a title-keyed mapping the region switch reads, following the wizard's own footer_groups pattern; step 3's advancing control takes its enabled state and the footer's count from one conflict_model.resolve_gate call. Digit keys resolve through keymap.dispatch at SCOPE_TABLE and reach a pick through the reconstruct route's own name-to-applier mapping, since the existing _ACTION_APPLIERS appliers are typed on the wizard's page state. Every class string is a literal at the call site and no dimension or hex is written here. The file is read and written with newline='' and stays CRLF throughout. (refs: DL-199, DL-202, DL-203, DL-204, DL-205, DL-206, DL-207, DL-208)
- **CI-M-002-003** `tests/test_gui_reconstruct_steps.py`: Guards over the step table: four rows in rail order, exactly one record current, the rows before it reading done and the rows after it upcoming, and reachability refused past a shut gate. Each guard is proven to fail first with the mutation and its verbatim output in the docstring. (refs: DL-203, DL-209)
- **CI-M-002-004** `tests/test_gui_resolve_composition.py`: Source-text and AST guards over app.py: a region named for every one of the four steps with the three entered at composition time read in rail order, the resolve region naming the split, grid, header-row and rail class strings, one control per candidate and one bulk control per input collection, the footer action group registered per step, the advancing control's enabled state read from a single conflict_model call, and the key handler's scope read out of on_key's own subtree rather than anywhere in the page, since the rail's skip control dispatches through the same map. The nicegui boundary and the literal-class rules hold. Each guard is proven to fail first with the verbatim output recorded. (refs: DL-202, DL-204, DL-206, DL-207, DL-209)
- **CI-M-002-005** `docs/2026-09-07-reconstruct-resolve-browser-record.md`: A served-page record driven over HTTP, carrying a matches or differs verdict and a structural reading per named surface at '/': the step rail, the four step regions, the tally and bulk strip, the split's two columns, the conflict grid's five tracks and header row, the 400px rail's three bands, and the footer's count beside its gated control, each read against Resolve.dc.html or its named sibling. It retakes the keyboard and announcement readings, since the advancing controls sit in step regions and the tab ring reads them in DOM order. (refs: DL-200, DL-211)
- **CI-M-002-006** `tests/test_gui_keymap.py`: The keymap guards pin the reconstruct route's applier mapping: its key set is a subset of keymap.ACTION_NAMES and it holds an applier for every action the resolve table answers, so DL-080's no-fall-through guarantee covers the second table too. keymap.py itself is unchanged - its entries already bind digits 1-9 to pick_candidate at SCOPE_TABLE. Proven to fail first, with the mutation and verbatim output recorded. (refs: DL-205, DL-209)
- **CI-M-002-007** `docs/CLAUDE.md`: The Files table holds one row per file docs/ carries, and the reconstruct-resolve browser record has its own: the filename, what the record reads - the step rail, the four step regions, the tally and bulk strip, the split's two columns, the conflict grid's five tracks under its header row, the 400px detail rail's three bands and the footer's outstanding count beside its gated control, each against Resolve.dc.html and each carrying a structural reading - and when to read it. The row sits among the other served-page records, above the historical plan rows. The file is CRLF apart from the one bare LF it already carries, so the row ends CRLF and every other line is left byte-for-byte. (refs: DL-200, DL-211)

#### Code Changes

**CC-M-002-001** (traktor_nml/gui/app.py) - implements CI-M-002-002

**Code:**

```diff
diff --git a/traktor_nml/gui/app.py b/traktor_nml/gui/app.py
index d4cd62b..f01b8fe 100644
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -52,6 +52,7 @@ from ..rewrite import read_and_parse_source, write_bytes_atomically
 from ..splice import assemble_output
 from . import conflict_model
 from . import navigation
+from . import reconstruct_steps
 from . import review_model
 # theme.py is the only source for a colour or size literal in this module (DL-078).
 from . import wizard_state
@@ -1541,6 +1542,88 @@ def _collection_labels(sources) -> tuple[str, ...]:
     return ("base", *_source_labels(sources))
 
 
+def _draw_step_rail(rail: ui.element, current: int) -> None:
+    """Redraws the four-step rail over reconstruct_steps.rail_records.
+
+    One span per record, in the order the table returns them, carrying
+    the record's own class string and - on the current record alone -
+    its aria-current value. Neither a number nor a label nor a class
+    name is written here: reconstruct_steps.STEPS holds the table and
+    reconstruct_steps decides which record is current, so this function
+    renders and decides nothing (DL-202, DL-203). The class strings it
+    carries are reconstruct_steps.STEP_CLASS, STEP_DONE_CLASS and
+    STEP_CURRENT_CLASS, whose values are theme.py's own "wizard-step",
+    "wizard-step-done" and "wizard-step-current" rules; the marker
+    carries MARKER_CLASS and MARKER_CURRENT_CLASS, whose values are
+    "wizard-step-number" and "wizard-step-number-current".
+
+    The class string is computed below the framework boundary, so it
+    reaches .classes() through its add= parameter as a value rather
+    than as a literal at this call site; what each entry actually
+    carries is read back from a recording stub in
+    tests/test_gui_reconstruct_steps.py.
+    """
+    rail.clear()
+    with rail:
+        for record in reconstruct_steps.rail_records(current):
+            with ui.element("span").classes(add=record.classes) as entry:
+                ui.label(record.marker).classes(add=record.marker_classes)
+                ui.label(record.label)
+            if record.aria_current is not None:
+                entry.props(f'aria-current="{record.aria_current}"')
+
+
+# The reconstruct route's own name-to-applier table. The wizard's
+# _ACTION_APPLIERS above is typed on _WizardPageState - its appliers read
+# state.review_rows and state.decisions, neither of which this route
+# holds - so the second table dispatches the same action names onto the
+# resolve table's own holder rather than widening the first (DL-205).
+#
+# Its key set is a subset of keymap.ACTION_NAMES and covers every action
+# the resolve table answers, which is what
+# tests/test_gui_keymap.py holds, so DL-080's no-fall-through guarantee
+# covers this table too: a name keymap.dispatch can return and this table
+# does not carry is a suite failure rather than a silent no-op.
+def _reconstruct_move(table: dict, args: dict) -> None:
+    """Moves the resolve table's focus to the index dispatch clamped.
+
+    The move is written through the table's own focus callback rather
+    than into a field of its own, so a move applied by key and one
+    applied by a control land in the one holder the render reads.
+    """
+    table["focus"](args["index"])
+
+
+def _reconstruct_pick(table: dict, args: dict) -> None:
+    """Picks the focused row's nth answer, counting the digit from one.
+
+    Specs binds digits 1-9 to candidate picking over the table, and
+    keymap.dispatch has already refused a digit past the focused row's
+    own candidate count, so the index is inside the row's candidates
+    (DL-071, DL-081).
+    """
+    group = table["groups"][table["holder"]["focused"]]
+    candidate = conflict_model.candidate_for_digit(group.candidates, args["digit"])
+    if candidate is not None:
+        table["pick"](group, conflict_model.candidate_reference(candidate))
+
+
+def _reconstruct_undo(table: dict, args: dict) -> None:
+    """Returns the focused row to undecided, which is the state a key
+    absent from the decision mapping already reads back."""
+    table["reset"](table["groups"][table["holder"]["focused"]])
+
+
+_RECONSTRUCT_ACTION_APPLIERS = {
+    "move_up": _reconstruct_move,
+    "move_down": _reconstruct_move,
+    "move_home": _reconstruct_move,
+    "move_end": _reconstruct_move,
+    "pick_candidate": _reconstruct_pick,
+    "undo_row": _reconstruct_undo,
+}
+
+
 def _build_reconstruct_page() -> None:
     """Registers the playlist-reconstruction screen at '/'.
 
@@ -1580,14 +1663,76 @@ def _build_reconstruct_page() -> None:
         # reads back undecided (DL-107, DL-115).
         decisions = conflict_model.ConflictDecisions()
 
-        # This route composes against the shell both pages are built
-        # from. DL-172 decides what a record may verdict about it, not
-        # which shell it is built from (DL-191). Its holders, its
-        # conflict rendering and its file-picker calls stand as they
-        # are: what differs is where the column and the two primary
-        # controls sit, and that each heading and the controls under it
-        # are a card rather than one box around the whole column.
-        with chrome.middle, ui.column().classes("gap-4 wizard-content-width"):
+        # Which step the page is showing, and the per-step footer
+        # groups the band swaps between. The number is held rather than
+        # derived: reconstruct_steps.reachable says where the operator
+        # may go and this says where they are, and the two are separate
+        # questions (DL-202).
+        step_holder: dict = {"current": reconstruct_steps.SET_UP}
+        footer_groups: dict = {}
+        # The resolve step's advancing control and the row the rail
+        # describes, held so the draw that answers a pick reaches both.
+        resolve_holder: dict = {"advance": None, "focused": 0}
+
+        # The rail is the page region's first row and the four step
+        # regions follow it, one visible at a time. A region is a
+        # container the page enters with a with statement, so each
+        # step's content keeps its own nesting rather than being
+        # re-parented into framework markup, and the rail is a nav of
+        # this module's own spans rather than a QStepper header, which
+        # draws its own numbered strip and no step of the artboard's
+        # rail (DL-199, DL-203).
+        with chrome.middle:
+            rail = ui.element("nav").props('aria-label="Progress"').classes(
+                "wizard-step-rail wizard-content-width"
+            )
+            regions = {
+                number: ui.column().classes("gap-4 wizard-content-width")
+                for number, _ in reconstruct_steps.STEPS
+            }
+
+        def show_step(number: int) -> None:
+            """Shows one step: its region, its footer group and its
+            sentence, and the rail entry marked current.
+
+            Every region and every group is built up front, alongside
+            the step that owns it, so this decides which one is visible
+            rather than which one exists - the same shape the wizard's
+            own show_footer_for_step takes (DL-187).
+            """
+            step_holder["current"] = number
+            for step_number, region in regions.items():
+                region.set_visibility(step_number == number)
+            for step_number, (group, note) in footer_groups.items():
+                group.set_visibility(step_number == number)
+                if step_number == number:
+                    chrome.footer_note.set_text(note)
+            _draw_step_rail(rail, number)
+
+        def advance_to(number: int) -> None:
+            """Walks to one step, or names why it is shut.
+
+            reachable() reads the held run and the resolve gate, so the
+            refusal and the sentence the resolve footer prints are one
+            answer rather than two (DL-204).
+            """
+            gate = conflict_model.resolve_gate(decisions, conflict_holder)
+            if not reconstruct_steps.reachable(
+                number, result_holder["result"] is not None, gate.all_decided
+            ):
+                ui.notify(
+                    conflict_model.write_refusal_sentence(
+                        conflict_model.write_refusal(
+                            result_holder["result"], decisions, conflict_holder
+                        )
+                        or conflict_model.WriteRefusal(conflict_model.NO_PREVIEW)
+                    ),
+                    type="warning",
+                )
+                return
+            show_step(number)
+
+        with regions[reconstruct_steps.SET_UP]:
             ui.label(
                 "My playlists kept their names but lost their contents; an older "
                 "collection still has them."
@@ -1751,8 +1896,6 @@ def _build_reconstruct_page() -> None:
                         value=None,
                     ).classes("w-full")
 
-                    report = ui.column().classes("w-full gap-1")
-
                     def _load():
                         """Reads and parses the chosen files, returning
                         (base_bytes, base_root, contributions) or None with the
@@ -1778,55 +1921,321 @@ def _build_reconstruct_page() -> None:
                         return base_result.source_bytes, base_result.root, contributions
 
 
-                    def _render_conflicts(groups) -> None:
-                        """One hand-rolled ui.row per conflicting track, carrying the
-                        identity key, the attribute names that diverge and one
-                        control per answer the track offers, under the bulk strip
-                        and the outstanding count (Specs.dc.html, "Splice
-                        conflicts").
+                    def _render_resolve() -> None:
+                        """The resolve step: the tally and the bulk strip above
+                        the split, the conflict grid under its header row at the
+                        left, and the detail rail at the right carrying one
+                        control per distinct answer (Resolve.dc.html).
 
-                        Hand-rolled rather than ui.aggrid, which claims the arrow
-                        keys Specs binds over this same table (DL-079, DL-110).
+                        Hand-rolled rows rather than ui.aggrid, which claims the
+                        arrow keys Specs binds over this same table (DL-079,
+                        DL-110). Every row and every answer is a grid cell on
+                        .wizard-conflict-grid, so the header row and the body
+                        rows read one set of tracks.
 
-                        Every state the rows show - the pick held for a group, how
-                        many are still undecided, what a bulk action leaves standing
-                        - is read from conflict_model, which is where the suite can
-                        reach it (DL-069, DL-106).
+                        Every state the step shows - the pick held for a group,
+                        how many are still undecided, what a bulk action leaves
+                        standing - is read from conflict_model, which is where
+                        the suite can reach it (DL-069, DL-106).
                         """
-                        ui.label(
-                            "These tracks are held differently by the collections. "
-                            "Nothing is written while any of them is unsettled."
-                        ).classes("wizard-body-13")
-                        table = ui.column().classes("w-full gap-0")
-                        # One name per input index, the collection being repaired at
-                        # index 0 and each source at its position in the list the
-                        # operator built (DL-154, DL-161).
+                        groups = conflict_holder
+                        region = regions[reconstruct_steps.RESOLVE]
+                        region.clear()
+                        # One name per input index, the collection being repaired
+                        # at index 0 and each source at its position in the list
+                        # the operator built (DL-154, DL-161).
                         labels = _collection_labels(source_holder)
+                        table: dict = {}
 
                         def draw() -> None:
-                            """Redraws the table over the current decisions - the
-                            whole table rather than the row just picked, since a bulk
-                            action moves every undecided row and the count moves with
-                            any pick at all."""
-                            table.clear()
-                            with table:
-                                with ui.row().classes("w-full items-center gap-2"):
-                                    # One bulk action per collection the run reads,
-                                    # each settling the undecided groups its own
-                                    # collection holds a record in and leaving the
-                                    # rest undecided (DL-154).
-                                    for input_index, label in enumerate(labels):
+                            """Redraws the step over the current decisions - the
+                            whole step rather than the row just picked, since a
+                            bulk action moves every undecided row, the count
+                            moves with any pick at all, and the rail describes
+                            whichever row is focused."""
+                            gate = conflict_model.resolve_gate(decisions, groups)
+                            views = decisions.rows(groups)
+                            region.clear()
+                            with region:
+                                bulk_strip(gate)
+                                with ui.element("div").classes("wizard-resolve-split"):
+                                    conflict_table(views)
+                                    detail_rail(views)
+                                # Resolve.dc.html:266's .hint: what a bulk action
+                                # does not reach. It stands under the split
+                                # rather than beside the bulk controls, where it
+                                # would read as a label for them.
+                                ui.label(
+                                    "Deciding all from one collection leaves untouched "
+                                    "any track that collection holds no record of."
+                                ).classes("wizard-hint")
+                            advance = resolve_holder["advance"]
+                            if advance is not None:
+                                advance.set_enabled(gate.all_decided)
+                            footer_groups[reconstruct_steps.RESOLVE] = (
+                                footer_groups[reconstruct_steps.RESOLVE][0],
+                                f"{gate.outstanding} still to decide. Writing stays "
+                                "closed until every one has an answer.",
+                            )
+                            if step_holder["current"] == reconstruct_steps.RESOLVE:
+                                chrome.footer_note.set_text(
+                                    footer_groups[reconstruct_steps.RESOLVE][1]
+                                )
+
+                        def bulk_strip(gate) -> None:
+                            """Resolve.dc.html:41's .fbar: the tally at the left,
+                            the "Decide all from" label, and one bulk action per
+                            collection the run reads, each settling the undecided
+                            groups its own collection holds a record in and
+                            leaving the rest undecided (DL-154).
+
+                            The sentence counts the groups and nothing else. A
+                            group is one candidate set whose members may span a
+                            subset of the inputs, so naming the count of inputs
+                            the run read would attribute the difference to inputs
+                            a group holds no member in - something the run does
+                            not supply. Resolve.dc.html's own copy names the two
+                            collections its illustrative run reads (DL-206).
+                            """
+                            with ui.element("div").classes("wizard-bulk-strip"):
+                                ui.label(
+                                    f"{len(groups)} tracks carry more than one "
+                                    f"answer - {gate.decided} decided, "
+                                    f"{gate.outstanding} to go"
+                                ).classes("wizard-tally")
+                                ui.element("span").classes("wizard-strip-spacer")
+                                ui.label("Decide all from").classes("wizard-label")
+                                for input_index, label in enumerate(labels):
+                                    ui.button(
+                                        f"All {label}",
+                                        on_click=lambda _e=None, index=input_index: bulk(index),
+                                        color=None,
+                                    ).classes("wizard-control wizard-decision-control")
+
+                        def conflict_table(views) -> None:
+                            """Resolve.dc.html:54-60's .tbl: a header row and one
+                            body row per group, both laid out on
+                            .wizard-conflict-grid's five tracks."""
+                            with ui.element("div").classes("wizard-conflict-table"):
+                                with ui.element("div").classes(
+                                    "wizard-conflict-grid wizard-conflict-header"
+                                ).props('role="row"'):
+                                    for heading in (
+                                        "Track", "What differs", "Answers",
+                                        "Held by", "Decision",
+                                    ):
+                                        ui.label(heading)
+                                for index, view in enumerate(views):
+                                    row(index, view)
+
+                        def row(index: int, view) -> None:
+                            """One track's row: its identity key, the attribute
+                            names that diverge, how many answers it offers, the
+                            collections holding it, and its decision. The focused
+                            row alone carries the selected class, which is what
+                            the arrow keys move (Specs.dc.html, "Keyboard")."""
+                            focused = index == resolve_holder["focused"]
+                            classes = "wizard-conflict-grid wizard-conflict-row"
+                            if focused:
+                                classes = (
+                                    "wizard-conflict-grid wizard-conflict-row "
+                                    "wizard-conflict-row-selected"
+                                )
+                            with ui.element("div").classes(add=classes).props(
+                                f'role="row" aria-selected="{str(focused).lower()}"'
+                            ):
+                                ui.label(view.identity_key).classes(
+                                    "font-mono wizard-body-12"
+                                )
+                                ui.label(", ".join(view.attrs)).classes("wizard-body-12")
+                                ui.label(str(len(view.candidates))).classes(
+                                    "font-mono wizard-body-12"
+                                )
+                                ui.label(
+                                    ", ".join(
+                                        sorted(
+                                            {
+                                                labels[input_index]
+                                                for candidate in view.candidates
+                                                for input_index, _ in candidate.members
+                                            }
+                                        )
+                                    )
+                                ).classes("wizard-body-12 wizard-subtle-2")
+                                if view.decision == conflict_model.UNDECIDED:
+                                    with ui.element("div").classes(
+                                        "wizard-conflict-decision"
+                                    ):
                                         ui.button(
-                                            f"All {label}",
-                                            on_click=lambda _e=None, index=input_index: bulk(index),
+                                            "Choose...",
+                                            on_click=lambda _e=None, at=index: focus(at),
                                             color=None,
-                                        ).classes("wizard-control")
+                                        ).classes(
+                                            "wizard-control wizard-decision-control"
+                                        )
+                                else:
+                                    # The decided cell names the collection that
+                                    # won and carries the undo that takes the
+                                    # decision back, so a row is reopened where
+                                    # it was decided rather than only from the
+                                    # rail, which describes one row at a time.
+                                    with ui.element("div").classes(
+                                        "wizard-conflict-decided wizard-status-found"
+                                    ):
+                                        ui.label(labels[view.decision[0]])
+                                        ui.button(
+                                            "Undo",
+                                            on_click=(
+                                                lambda _e=None, chosen=groups[index]:
+                                                reset(chosen)
+                                            ),
+                                            color=None,
+                                        ).classes(
+                                            "wizard-control wizard-decision-control"
+                                        )
+
+                        def detail_rail(views) -> None:
+                            """Resolve.dc.html:70-95's .det: the focused row's
+                            file at the head, one control per distinct answer in
+                            the body, and the keys and actions in the footer.
+
+                            One control per distinct answer rather than one per
+                            collection: two collections holding identical values
+                            are one answer, and deciding it decides both, so a
+                            control names the record that wins rather than the
+                            collection it came from (DL-148, DL-160).
+                            """
+                            with ui.element("div").classes("wizard-detail-rail"):
+                                if not views:
+                                    with ui.element("div").classes("wizard-detail-head"):
+                                        ui.label(
+                                            "Nothing is held differently."
+                                        ).classes("wizard-body-14-5")
+                                    return
+                                view = views[resolve_holder["focused"]]
+                                group = groups[resolve_holder["focused"]]
+                                with ui.element("div").classes("wizard-detail-head"):
+                                    ui.label(view.identity_key).classes(
+                                        "font-mono wizard-body-14-5"
+                                    )
                                     ui.label(
-                                        f"{decisions.outstanding(groups)} of {len(groups)}"
-                                        " still undecided"
-                                    ).classes("wizard-body-12 wizard-faint")
-                                for group, view in zip(groups, decisions.rows(groups)):
-                                    row(group, view)
+                                        "Two collections hold this file with different "
+                                        "values. Pick the one that supplies them."
+                                    ).classes("wizard-body-12 wizard-dim")
+                                with ui.element("div").classes("wizard-detail-body"):
+                                    for position, candidate in enumerate(view.candidates, 1):
+                                        answer(group, view, position, candidate)
+                                    # Resolve.dc.html:245's .note: what a pick
+                                    # names, standing under the answers rather
+                                    # than in the log alone, because the reading
+                                    # it corrects - that an answer is a
+                                    # collection - is the one the operator
+                                    # arrives with (DL-148).
+                                    with ui.element("div").classes(
+                                        "wizard-note wizard-faint"
+                                    ):
+                                        ui.label(
+                                            "A pick names the record that wins, not the "
+                                            "collection it came from. Two collections "
+                                            "holding the identical values are one answer, "
+                                            "and deciding it decides both."
+                                        )
+                                with ui.element("div").classes("wizard-detail-foot"):
+                                    key_hints()
+                                    with ui.element("div").classes(
+                                        "wizard-detail-actions"
+                                    ):
+                                        ui.button(
+                                            "Skip for now",
+                                            on_click=lambda _e=None: focus(
+                                                keymap.dispatch(
+                                                    "ArrowDown",
+                                                    (),
+                                                    keymap.SCOPE_TABLE,
+                                                    row_count=len(views),
+                                                    focused_index=resolve_holder["focused"],
+                                                ).args["index"]
+                                            ),
+                                            color=None,
+                                        ).classes("wizard-control")
+                                        # The rail's primary is the pick itself:
+                                        # the first answer, which is the one the
+                                        # digit 1 takes, so the pointer and the
+                                        # key reach the same decision.
+                                        ui.button(
+                                            "Use answer 1",
+                                            on_click=(
+                                                lambda _e=None, at=group,
+                                                named=conflict_model.candidate_reference(
+                                                    view.candidates[0]
+                                                ): pick(at, named)
+                                            ),
+                                            color=None,
+                                        ).classes("wizard-control wizard-control-primary")
+
+                        def key_hints() -> None:
+                            """Resolve.dc.html:91's .keys: three chip groups,
+                            each naming its own keys beside what they do, rather
+                            than one sentence listing them in prose. A chip is
+                            what Specs.dc.html's "Keyboard" section draws, and
+                            the digits, the arrows and U are the three rows it
+                            binds over a table (DL-071)."""
+                            with ui.element("div").classes("wizard-key-row"):
+                                # The digits are a range and the artboard sets
+                                # its two chips apart with an en dash; the
+                                # arrows are two keys side by side and carry
+                                # none.
+                                for chips, between, phrase in (
+                                    (("1", "9"), "\u2013", "pick an answer"),
+                                    (("\u2191", "\u2193"), "", "move"),
+                                    (("U",), "", "undo"),
+                                ):
+                                    with ui.element("span").classes("wizard-key-hint"):
+                                        for position, chip in enumerate(chips):
+                                            if position and between:
+                                                ui.label(between)
+                                            ui.label(chip).classes("wizard-kbd")
+                                        ui.label(phrase)
+
+                        def answer(group, view, position: int, candidate) -> None:
+                            """One control per distinct answer, carrying the
+                            digit that picks it and the values it supplies. The
+                            decision the view holds is compared against this
+                            candidate's own reference, so the chosen answer alone
+                            carries the chosen class and this module holds no
+                            reading of what a decision means."""
+                            reference = conflict_model.candidate_reference(candidate)
+                            chosen = view.decision == reference
+                            with ui.element("div").classes("wizard-answer-group"):
+                                with ui.element("div").classes("wizard-answer-group-head"):
+                                    ui.label(f"Answer {position}").classes("wizard-label")
+                                    ui.label(str(position)).classes("wizard-kbd")
+                                classes = "wizard-answer"
+                                if chosen:
+                                    classes = "wizard-answer wizard-answer-chosen"
+                                supplied_by = ", ".join(
+                                    labels[index] for index, _ in candidate.members
+                                )
+                                with ui.element("div").classes(add=classes):
+                                    with ui.element("span").classes(
+                                        "wizard-answer-marker"
+                                    ).props(
+                                        f'role="img" aria-label='
+                                        f'"{"Chosen" if chosen else "Not chosen"}"'
+                                    ):
+                                        if chosen:
+                                            ui.element("span").classes("wizard-answer-dot")
+                                    ui.button(
+                                        f"{supplied_by} {' | '.join(candidate.values)}",
+                                        on_click=(
+                                            lambda _e=None, at=group, named=reference:
+                                            pick(at, named)
+                                        ),
+                                        color=None,
+                                    ).classes(
+                                        "wizard-control font-mono wizard-body-11-5 "
+                                        "wizard-subtle-5"
+                                    )
 
                         def bulk(input_index: int) -> None:
                             decisions.resolve_all(
@@ -1838,36 +2247,75 @@ def _build_reconstruct_page() -> None:
                             decisions.resolve(group, reference)
                             draw()
 
-                        def row(group, view) -> None:
-                            """One track's row, offering one control per answer the
-                            group carries. The decision the view holds indexes the
-                            selected class straight onto the candidate reference the
-                            view names, so the chosen answer alone carries the
-                            selected fill and this module holds no reading of what a
-                            decision means."""
-                            selected = {view.decision: "wizard-decision-accept"}
-                            with ui.row().classes("w-full items-center gap-3 wizard-row"):
-                                ui.label(view.identity_key).classes(
-                                    "font-mono wizard-body-12 grow"
-                                )
-                                ui.label(", ".join(view.attrs)).classes("wizard-label")
-                                for candidate in view.candidates:
-                                    reference = conflict_model.candidate_reference(candidate)
-                                    supplied_by = ", ".join(
-                                        labels[index] for index, _ in candidate.members
-                                    )
-                                    ui.button(
-                                        f"{supplied_by} {' | '.join(candidate.values)}",
-                                        on_click=(
-                                            lambda _e=None, chosen=group, named=reference:
-                                            pick(chosen, named)
-                                        ),
-                                        color=None,
-                                    ).classes(
-                                        "wizard-control font-mono wizard-body-12 "
-                                        f"{selected.get(reference, 'wizard-tag-action-outline')}"
+                        def reset(group) -> None:
+                            decisions.reset(group.identity_key)
+                            draw()
+
+                        def focus(index: int) -> None:
+                            resolve_holder["focused"] = index
+                            draw()
+
+                        def on_key(event) -> None:
+                            """Resolves a keypress through keymap.dispatch at
+                            SCOPE_TABLE and applies it through this route's own
+                            applier table.
+
+                            A name dispatch returns that the table does not carry
+                            is a no-op here and a suite failure in
+                            tests/test_gui_keymap.py, which pins the table's key
+                            set against the actions this table answers (DL-080,
+                            DL-205).
+                            """
+                            if not groups or step_holder["current"] != reconstruct_steps.RESOLVE:
+                                return
+                            action = keymap.dispatch(
+                                event.key.name,
+                                tuple(
+                                    name
+                                    for name, held in (
+                                        ("shift", event.modifiers.shift),
+                                        ("ctrl", event.modifiers.ctrl),
+                                        ("alt", event.modifiers.alt),
                                     )
+                                    if held
+                                ),
+                                keymap.SCOPE_TABLE,
+                                row_count=len(groups),
+                                focused_index=resolve_holder["focused"],
+                                candidate_count=len(
+                                    groups[resolve_holder["focused"]].candidates
+                                ),
+                            )
+                            if action is None:
+                                return
+                            applier = _RECONSTRUCT_ACTION_APPLIERS.get(action.name)
+                            if applier is not None:
+                                applier(table, action.args)
+
+                        # What an applier is handed: the groups it indexes, the
+                        # holder carrying the focused row, and the three
+                        # callbacks that write a decision. The holder itself is
+                        # passed rather than a copy of its value, so a move
+                        # applied by key and one applied by a control land in the
+                        # one field the render reads.
+                        table.update(
+                            {
+                                "groups": groups,
+                                "holder": resolve_holder,
+                                "focus": focus,
+                                "pick": pick,
+                                "reset": reset,
+                            }
+                        )
 
+                        # Registered once for the life of the page rather than
+                        # per redraw: ui.keyboard binds a handler, and a second
+                        # preview would otherwise bind a second one over the same
+                        # keys. on_key reads conflict_holder, which preview
+                        # rewrites in place, so the one handler always dispatches
+                        # over the groups the last run reported.
+                        if resolve_holder.get("keyboard") is None:
+                            resolve_holder["keyboard"] = ui.keyboard(on_key=on_key)
                         draw()
 
                     async def preview() -> None:
@@ -1892,6 +2340,8 @@ def _build_reconstruct_page() -> None:
                         groups = conflict_model.conflict_groups(result.conflict_rows)
                         conflict_holder[:] = groups
                         result_holder["result"] = result
+                        _render_resolve()
+                        show_step(reconstruct_steps.PREVIEW)
                         report.clear()
                         with report:
                             if result.errors:
@@ -1907,7 +2357,11 @@ def _build_reconstruct_page() -> None:
                                     # run returned, so those rows stand in its place;
                                     # every other token renders as the token it is.
                                     if error == conflict_model.CONFLICT_ABORT_TOKEN and groups:
-                                        _render_conflicts(groups)
+                                        ui.label(
+                                            f"{len(groups)} tracks are held differently "
+                                            "by two collections. Resolve names each one "
+                                            "and offers its answers."
+                                        ).classes("wizard-body-13")
                                         continue
                                     ui.label(error).classes("font-mono wizard-body-12 text-warning")
                                 return
@@ -1960,19 +2414,81 @@ def _build_reconstruct_page() -> None:
                         )
                         ui.notify(f"Written to {output_path}", type="positive")
 
+        with regions[reconstruct_steps.PREVIEW]:
+            with ui.element("section").classes("wizard-card wizard-content-width"):
+                with ui.element("div").classes("wizard-card-head"):
+                    ui.label("What this merge would write").classes("wizard-card-title")
+                with ui.element("div").classes("wizard-card-body"):
+                    report = ui.column().classes("w-full gap-1")
+
+        with regions[reconstruct_steps.WRITE]:
+            with ui.element("section").classes("wizard-card wizard-content-width"):
+                with ui.element("div").classes("wizard-card-head"):
+                    ui.label("Write the output").classes("wizard-card-title")
+                with ui.element("div").classes("wizard-card-body"):
+                    ui.label(
+                        "The preview is the run, so this writes the output that "
+                        "preview already assembled."
+                    ).classes("wizard-body-13")
+
         # Main.dc.html:29's .ft holds the screen's advancing action, so
-        # both primary controls are constructed in the band. Each invokes
-        # the function this page defines above - a with statement opens
-        # no scope of its own, so both names are in reach here - which is
-        # how each control exists once and its enabled state is held once
-        # (DL-187).
-        chrome.footer_note.set_text(
-            "Preview reads the collections; Write output writes a new file."
-        )
+        # every primary control is constructed in the band, one group
+        # per step, and show_step decides which group the band shows.
+        # Each invokes a function this page defines above - a with
+        # statement opens no scope of its own, so every name is in reach
+        # here - which is how each control exists once and its enabled
+        # state is held once (DL-187).
         with chrome.footer_actions:
-            ui.button("Preview", on_click=preview, color=None).classes(
-                "wizard-control"
-            )
-            ui.button("Write output", on_click=write_output, color=None).classes(
-                "wizard-control wizard-control-primary"
-            )
+            with ui.row().classes("wizard-footer-actions") as setup_actions:
+                ui.button("Preview", on_click=preview, color=None).classes(
+                    "wizard-control wizard-control-primary"
+                )
+            with ui.row().classes("wizard-footer-actions") as preview_actions:
+                ui.button(
+                    "Back to set up",
+                    on_click=lambda: show_step(reconstruct_steps.SET_UP),
+                    color=None,
+                ).classes("wizard-control")
+                ui.button(
+                    "Continue to resolve",
+                    on_click=lambda: advance_to(reconstruct_steps.RESOLVE),
+                    color=None,
+                ).classes("wizard-control wizard-control-primary")
+            with ui.row().classes("wizard-footer-actions") as resolve_actions:
+                ui.button(
+                    "Back to the preview",
+                    on_click=lambda: show_step(reconstruct_steps.PREVIEW),
+                    color=None,
+                ).classes("wizard-control")
+                resolve_holder["advance"] = ui.button(
+                    "Continue to write",
+                    on_click=lambda: advance_to(reconstruct_steps.WRITE),
+                    color=None,
+                ).classes("wizard-control wizard-control-primary")
+            with ui.row().classes("wizard-footer-actions") as write_actions:
+                ui.button(
+                    "Back to resolve",
+                    on_click=lambda: show_step(reconstruct_steps.RESOLVE),
+                    color=None,
+                ).classes("wizard-control")
+                ui.button("Write output", on_click=write_output, color=None).classes(
+                    "wizard-control wizard-control-primary"
+                )
+
+        footer_groups[reconstruct_steps.SET_UP] = (
+            setup_actions,
+            "Preview reads the collections; nothing is written by it.",
+        )
+        footer_groups[reconstruct_steps.PREVIEW] = (
+            preview_actions,
+            "This is what the merge would write. Nothing is written yet.",
+        )
+        footer_groups[reconstruct_steps.RESOLVE] = (
+            resolve_actions,
+            "Writing stays closed until every track has an answer.",
+        )
+        footer_groups[reconstruct_steps.WRITE] = (
+            write_actions,
+            "Write output writes the file the preview assembled.",
+        )
+        show_step(reconstruct_steps.SET_UP)

```

**Documentation:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -2176,5 +2176,5 @@ def _build_reconstruct_page() -> None:
                         def key_hints() -> None:
-                            """Resolve.dc.html:91's .keys: three chip groups,
+                            """Resolve.dc.html:94's .keys: three chip groups,
                             each naming its own keys beside what they do, rather
                             than one sentence listing them in prose. A chip is
                             what Specs.dc.html's "Keyboard" section draws, and
@@ -2240,17 +2240,50 @@ def _build_reconstruct_page() -> None:
                         def bulk(input_index: int) -> None:
+                            """Settles every group the collection at
+                            input_index holds a record in, on that record.
+
+                            The reference comes from
+                            conflict_model.reference_from_input rather than
+                            from a collection token, so a group that
+                            collection holds no record in is left undecided
+                            rather than settled on a name that matches
+                            nothing (DL-148).
+                            """
                             decisions.resolve_all(
                                 groups, conflict_model.reference_from_input(input_index)
                             )
                             draw()
 
                         def pick(group, reference) -> None:
+                            """Settles one group on the record `reference`
+                            names, then redraws.
+
+                            reference is an (input index, primary key) pair
+                            from conflict_model.candidate_reference: one file
+                            in two inputs carries the identical
+                            location-derived key, so the input index is what
+                            tells the two apart, and two collections holding
+                            identical values are one answer that this settles
+                            for both (DL-004, DL-148).
+                            """
                             decisions.resolve(group, reference)
                             draw()
 
                         def reset(group) -> None:
+                            """Returns one group to undecided.
+
+                            The decision is dropped from the mapping rather
+                            than written as an undecided token, because a key
+                            absent from the mapping reads back undecided.
+                            """
                             decisions.reset(group.identity_key)
                             draw()
 
                         def focus(index: int) -> None:
+                            """Moves the row the detail rail describes.
+
+                            The index is written into the one holder the
+                            redraw reads, so a move applied by key and one
+                            applied by a control land in the same field.
+                            """
                             resolve_holder["focused"] = index
                             draw()

```


**CC-M-002-002** (tests/test_gui_reconstruct_steps.py) - implements CI-M-002-003

**Code:**

```diff
diff --git a/tests/test_gui_reconstruct_steps.py b/tests/test_gui_reconstruct_steps.py
new file mode 100644
index 0000000..a41fd73
--- /dev/null
+++ b/tests/test_gui_reconstruct_steps.py
@@ -0,0 +1,167 @@
+"""Guards the reconstruct page's step table in
+traktor_nml/gui/reconstruct_steps.py: the four rail records it derives
+and the reachability rule that decides which step the page may show.
+
+The module imports no framework, which is what lets these run under the
+system interpreter; the AST walk in tests/test_gui_view_boundary.py is
+what holds that boundary (DL-069, DL-203). What a guard here holds is the
+record a rail entry renders from - its position, its class string, its
+marker and its aria-current value. Where the rail actually lands on the
+page, and whether it spans the page region, is a served-page reading and
+belongs to the record (DL-189).
+
+Each guard records the mutation applied to make it fail and the verbatim
+output observed under that mutation.
+"""
+
+from __future__ import annotations
+
+from traktor_nml.gui import reconstruct_steps as steps
+
+
+def test_the_table_carries_the_four_steps_the_artboards_draw():
+    """The four artboards on canvas page 3 draw one rail of four steps:
+    Set up, Preview, Resolve, Write, numbered one to four. STEPS is the
+    one place either a number or a label is written.
+
+    Mutation: the (RESOLVE, "Resolve") row was deleted from STEPS in
+    reconstruct_steps.py and this guard rerun. Observed:
+        E       AssertionError: the rail is the four steps the artboards draw
+        E       assert ((1, 'Set up'... (4, 'Write')) == ((1, 'Set up'... (4, 'Write'))
+        E
+        E         At index 2 diff: (4, 'Write') != (3, 'Resolve')
+        E         Right contains one more item: (4, 'Write')
+        E         Use -v to get more diff
+    """
+    assert steps.STEPS == (
+        (1, "Set up"),
+        (2, "Preview"),
+        (3, "Resolve"),
+        (4, "Write"),
+    ), "the rail is the four steps the artboards draw"
+    assert (steps.SET_UP, steps.PREVIEW, steps.RESOLVE, steps.WRITE) == (1, 2, 3, 4)
+
+
+def test_the_rail_reads_done_before_the_current_row_and_upcoming_after_it():
+    """One record per row in table order, exactly one current, every row
+    before it done and every row after it upcoming. Resolve.dc.html:121-125
+    draws exactly that: two done steps, the current step, and one still to
+    come.
+
+    Mutation: `number < current` in _record was replaced with
+    `number > current` in reconstruct_steps.py and this guard rerun.
+    Observed:
+        E       AssertionError: exactly one row reads current
+        E       assert ['upcoming', ...rent', 'done'] == ['done', 'don...', 'upcoming']
+        E
+        E         At index 0 diff: 'upcoming' != 'done'
+        E         Use -v to get more diff
+    """
+    records = steps.rail_records(steps.RESOLVE)
+    assert [record.number for record in records] == [1, 2, 3, 4]
+    assert [record.state for record in records] == [
+        steps.DONE,
+        steps.DONE,
+        steps.CURRENT,
+        steps.UPCOMING,
+    ], "exactly one row reads current"
+    assert sum(1 for record in records if record.state == steps.CURRENT) == 1
+
+
+def test_each_record_carries_the_class_string_and_the_marker_its_state_names():
+    """A done entry carries the done class and the check mark in its
+    marker; the current entry carries the current class, the current
+    marker class and aria-current "step"; an upcoming entry carries the
+    base class alone and its own number. Nothing else on the page decides
+    which entry is marked (DL-202).
+
+    Mutation: `aria_current=ARIA_CURRENT_STEP if state == CURRENT else None`
+    in _record was replaced with `aria_current=ARIA_CURRENT_STEP` in
+    reconstruct_steps.py and this guard rerun. Observed:
+        E       AssertionError: only the current entry carries aria-current
+        E       assert ['step', 'ste...step', 'step'] == [None, None, 'step', None]
+        E
+        E         At index 0 diff: 'step' != None
+        E         Use -v to get more diff
+    """
+    done, _preview, current, upcoming = steps.rail_records(steps.RESOLVE)
+
+    assert done.classes == "wizard-step wizard-step-done"
+    assert done.marker == steps.DONE_MARKER
+    assert done.marker_classes == "wizard-step-number"
+
+    assert current.classes == "wizard-step wizard-step-current"
+    assert current.marker == "3"
+    assert current.marker_classes == "wizard-step-number wizard-step-number-current"
+
+    assert upcoming.classes == "wizard-step"
+    assert upcoming.marker == "4"
+
+    assert [record.aria_current for record in steps.rail_records(steps.RESOLVE)] == [
+        None,
+        None,
+        steps.ARIA_CURRENT_STEP,
+        None,
+    ], "only the current entry carries aria-current"
+
+
+def test_a_current_the_table_does_not_name_marks_no_row():
+    """A number no row carries leaves every record upcoming rather than
+    marking the first row by accident, so a caller holding a step the
+    table does not name renders a rail with nothing marked.
+
+    Mutation: the `any(row == current for row, _ in STEPS) and` clause was
+    deleted from _record's done branch in reconstruct_steps.py and this
+    guard rerun. Observed:
+        E       AssertionError: a step the table does not name marks no row
+        E       assert ['done', 'don...done', 'done'] == ['upcoming', ...', 'upcoming']
+        E
+        E         At index 0 diff: 'done' != 'upcoming'
+        E         Use -v to get more diff
+    """
+    assert [record.state for record in steps.rail_records(9)] == [
+        steps.UPCOMING
+    ] * 4, "a step the table does not name marks no row"
+
+
+def test_reachability_refuses_a_step_past_a_shut_gate():
+    """Set up is always reachable; preview and resolve need a held run;
+    write needs a held run whose divergences are every one decided. The
+    gate is conflict_model.resolve_gate's own answer, so the step this
+    refuses and the count the footer prints cannot disagree (DL-204).
+
+    Mutation: reachable's final `return has_result and all_decided` was
+    replaced with `return has_result` in reconstruct_steps.py and this
+    guard rerun. Observed:
+        E       AssertionError: the write step is shut while a group is undecided
+        E       assert not True
+        E        +  where True = <function reachable at 0x000001E0F96BC3B0>(4, True, False)
+        E        +    where <function reachable at 0x000001E0F96BC3B0> = steps.reachable
+        E        +    and   4 = steps.WRITE
+    """
+    assert steps.reachable(steps.SET_UP, False, False)
+    assert not steps.reachable(steps.PREVIEW, False, False)
+    assert not steps.reachable(steps.RESOLVE, False, True)
+    assert steps.reachable(steps.RESOLVE, True, False)
+    assert not steps.reachable(steps.WRITE, True, False), (
+        "the write step is shut while a group is undecided"
+    )
+    assert steps.reachable(steps.WRITE, True, True)
+
+
+def test_a_target_the_table_does_not_name_is_refused():
+    """A number no STEPS row carries is refused rather than defaulted, so
+    a caller holding a step the table does not name stays where it is.
+
+    Mutation: the `if not any(number == target ...): return False` guard
+    was deleted from reachable in reconstruct_steps.py and this guard
+    rerun. Observed:
+        E       AssertionError: a step the table does not name is refused
+        E       assert not True
+        E        +  where True = <function reachable at 0x0000027FCCA0C3B0>(9, True, True)
+        E        +    where <function reachable at 0x0000027FCCA0C3B0> = steps.reachable
+    """
+    assert not steps.reachable(9, True, True), (
+        "a step the table does not name is refused"
+    )
+    assert not steps.reachable(0, True, True)

```

**Documentation:**

```diff
--- a/tests/test_gui_reconstruct_steps.py
+++ b/tests/test_gui_reconstruct_steps.py
@@ -10,6 +10,12 @@
 page, and whether it spans the page region, is a served-page reading and
 belongs to the record (DL-189).
 
+has_result and all_decided reach reachable() here as plain booleans: what
+decides all_decided in the running page is conflict_model.resolve_gate,
+and that rule is held in tests/test_gui_resolve_rules.py. Splitting them
+this way keeps the step rule readable on its own inputs and leaves the
+gate one guard, not two (DL-204).
+
 Each guard records the mutation applied to make it fail and the verbatim
 output observed under that mutation.
 """

```


**CC-M-002-003** (tests/test_gui_resolve_composition.py) - implements CI-M-002-004

**Code:**

```diff
diff --git a/tests/test_gui_resolve_composition.py b/tests/test_gui_resolve_composition.py
new file mode 100644
index 0000000..cd2738f
--- /dev/null
+++ b/tests/test_gui_resolve_composition.py
@@ -0,0 +1,278 @@
+"""Guards how traktor_nml/gui/app.py composes the reconstruct page's four
+steps and its resolve screen, read as source text and as an AST under the
+system interpreter, which has no nicegui.
+
+What a guard here holds is what the module constructs and which class
+string each construction names. What it cannot hold is what the browser
+did with them: a guard reading a class name is true in exactly the broken
+state, so the rendered rail, the resolved column widths and the rail's
+own width are read on a served page and written into a record under
+docs/ (DL-084, DL-169, DL-189).
+
+Each guard records the mutation applied to make it fail and the verbatim
+output observed under that mutation. Where pytest printed an assertion
+repr longer than the margin, the line is cut with an ellipsis rather than
+rewrapped, so what stands is what pytest printed.
+"""
+
+from __future__ import annotations
+
+import ast
+import re
+from pathlib import Path
+
+from traktor_nml.gui import reconstruct_steps
+
+_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"
+
+
+def _source() -> str:
+    return _APP_PY.read_text(encoding="utf-8")
+
+
+def _page_tree() -> ast.AST:
+    """The _build_reconstruct_page function's own subtree.
+
+    Read as its own subtree rather than as the whole module, so a guard
+    below cannot be satisfied by something the reconnect wizard's own
+    builders do - the failure a footer assertion the wrong route
+    satisfied already produced once on this page.
+    """
+    module = ast.parse(_source())
+    for node in ast.walk(module):
+        if isinstance(node, ast.FunctionDef) and node.name == "_build_reconstruct_page":
+            return node
+    raise AssertionError("app.py defines no _build_reconstruct_page")
+
+
+def _page_source() -> str:
+    """The same subtree as text, for the class strings a call site names."""
+    return ast.get_source_segment(_source(), _page_tree()) or ""
+
+
+def _named_function_source(name: str) -> str:
+    """One function defined inside _build_reconstruct_page, as text.
+
+    The page carries more than one keymap.dispatch call - the rail's
+    "Skip for now" control resolves an ArrowDown through the same map -
+    so a reading of the key handler is taken from the handler's own
+    subtree. A substring guard over the whole page is satisfied by
+    whichever call site happens to carry it, which is the guard green in
+    exactly the broken state this project has shipped three times.
+    """
+    for node in ast.walk(_page_tree()):
+        if isinstance(node, ast.FunctionDef) and node.name == name:
+            return ast.get_source_segment(_source(), node) or ""
+    raise AssertionError(f"_build_reconstruct_page defines no {name}")
+
+
+def test_the_page_builds_one_region_per_step_and_names_each():
+    """The route builds one region per reconstruct_steps.STEPS row and
+    names all four: "step 3" names nothing unless four regions exist.
+
+    Three of them are entered at composition time and the fourth, the
+    resolve region, is taken by the resolve render, which clears and
+    refills it on every decision. So the fourth is held by where it is
+    taken rather than by an entry, and the three entered are held in the
+    order the rail draws them. What decides the order the operator walks
+    is reconstruct_steps.STEPS, which tests/test_gui_reconstruct_steps.py
+    reads; the order the module happens to define its builders in decides
+    nothing and is not read here.
+
+    Mutation: the `with regions[reconstruct_steps.WRITE]:` block header in
+    app.py was changed to `with regions[reconstruct_steps.RESOLVE]:` and
+    this guard rerun. Observed:
+        E       AssertionError: the page names a region for every step
+        E       assert {'PREVIEW', '...VE', 'SET_UP'} == {'PREVIEW', '..._UP', 'WRITE'}
+        E
+        E         Extra items in the right set:
+        E         'WRITE'
+        E         Use -v to get more diff
+    """
+    page = _page_source()
+    named = set(re.findall(r"regions\[reconstruct_steps\.([A-Z_]+)\]", page))
+    assert named == {"SET_UP", "PREVIEW", "RESOLVE", "WRITE"}, (
+        "the page names a region for every step"
+    )
+    entered = re.findall(r"with regions\[reconstruct_steps\.([A-Z_]+)\]", page)
+    assert entered == ["SET_UP", "PREVIEW", "WRITE"], (
+        "the three regions filled at composition time are entered by name, "
+        "in rail order"
+    )
+    assert "region = regions[reconstruct_steps.RESOLVE]" in page, (
+        "the resolve region is taken by the render that refills it"
+    )
+    built = re.search(
+        r"regions = \{.*?for number, _ in reconstruct_steps\.STEPS",
+        page,
+        re.DOTALL,
+    )
+    assert built is not None, "the regions are built from reconstruct_steps.STEPS"
+    assert len(reconstruct_steps.STEPS) == 4
+
+
+def test_the_resolve_step_names_the_split_the_grid_and_the_rail():
+    """The resolve region names the class strings the artboard's geometry
+    lives in: the split, the table, the grid, the header row and the body
+    row that both sit on that grid's own tracks, and the rail's three
+    bands.
+
+    A class string named nowhere is a rule the page never wears, which is
+    the shape the shell milestone's own served-page run caught.
+
+    Mutation: the header row's `"wizard-conflict-grid
+    wizard-conflict-header"` literal in app.py was reduced to
+    `"wizard-conflict-header"` and this guard rerun. Observed:
+        E       AssertionError: the header row sits on the conflict grid's own tracks
+        E       assert 'wizard-conflict-grid wizard-conflict-header' in 'def _build_reconstruct_page() - [...]
+    """
+    page = _page_source()
+    for name in (
+        "wizard-resolve-split",
+        "wizard-conflict-table",
+        "wizard-conflict-grid",
+        "wizard-conflict-header",
+        "wizard-detail-rail",
+        "wizard-detail-head",
+        "wizard-detail-body",
+        "wizard-detail-foot",
+    ):
+        assert name in page, f"the resolve step names no {name}"
+    assert "wizard-conflict-grid wizard-conflict-header" in page, (
+        "the header row sits on the conflict grid's own tracks"
+    )
+    assert "wizard-conflict-grid wizard-conflict-row" in page, (
+        "a body row sits on the conflict grid's own tracks"
+    )
+
+
+def test_one_control_per_answer_and_one_bulk_action_per_collection():
+    """The rail offers one control per distinct answer the group carries -
+    not one per record - and the strip offers one bulk action per
+    collection the run reads. Two collections holding identical values are
+    one answer, and deciding it decides both (DL-148, DL-150, DL-154).
+
+    Mutation: `enumerate(view.candidates, 1)` in app.py was changed to
+    `enumerate(view.candidates[:1], 1)` and this guard rerun. Observed:
+        E       AssertionError: the rail offers one control per distinct answer
+        E       assert 'enumerate(view.candidates, 1)' in 'def _build_reconstruct_page() -> None:\\n     [...]
+    """
+    page = _page_source()
+    assert "enumerate(view.candidates, 1)" in page, (
+        "the rail offers one control per distinct answer"
+    )
+    assert "for input_index, label in enumerate(labels)" in page, (
+        "the strip offers one bulk action per collection the run reads"
+    )
+    assert "conflict_model.reference_from_input(input_index)" in page, (
+        "a bulk action resolves through reference_from_input, not through "
+        "the first candidate"
+    )
+    assert "conflict_model.candidate_reference(candidate)" in page
+
+
+def test_every_step_registers_a_footer_group_and_a_note():
+    """Each of the four steps registers its own action group and its own
+    sentence, and show_step decides which the band shows, so the control
+    that advances a step exists once and its enabled state is held once
+    (DL-187).
+
+    Mutation: the `footer_groups[reconstruct_steps.WRITE] = (...)`
+    registration was deleted from app.py and this guard rerun. Observed:
+        E       AssertionError: every step registers a footer group and a sentence
+        E       assert {'PREVIEW', '...VE', 'SET_UP'} == {'PREVIEW', '..._UP', 'WRITE'}
+        E
+        E         Extra items in the right set:
+        E         'WRITE'
+        E         Use -v to get more diff
+    """
+    registered = set(
+        re.findall(r"footer_groups\[reconstruct_steps\.([A-Z_]+)\] = \(", _page_source())
+    )
+    assert registered == {"SET_UP", "PREVIEW", "RESOLVE", "WRITE"}, (
+        "every step registers a footer group and a sentence"
+    )
+    assert "chrome.footer_note.set_text" in _page_source()
+
+
+def test_the_gate_is_read_once_for_the_count_and_the_advancing_control():
+    """The footer's count and the advancing control's enabled state come
+    from one conflict_model.resolve_gate call per draw, not from a count
+    computed for the sentence and an emptiness computed again for the
+    control: two readings can disagree, and the disagreement shows as a
+    control the operator can press over a sentence saying they cannot
+    (DL-204).
+
+    Mutation: `advance.set_enabled(gate.all_decided)` in app.py was
+    replaced with
+    `advance.set_enabled(decisions.outstanding(groups) == 0)` and this
+    guard rerun. Observed:
+        E       AssertionError: the page reads the gate rather than the count beneath it
+        E       assert 'decisions.outstanding(' not in 'def _build_...teps.SET_UP)'
+        E
+        E         'decisions.outstanding(' is contained here:
+        E           t_enabled(decisions.outstanding(groups) == 0)
+        E                                       footer_groups[reconstruct_steps.RESOLVE] = (
+    """
+    page = _page_source()
+    assert "conflict_model.resolve_gate(decisions, groups)" in page
+    assert "gate.all_decided" in page, (
+        "the advancing control reads the gate the sentence reads"
+    )
+    assert "gate.outstanding" in page
+    assert "gate.decided" in page
+    assert "decisions.outstanding(" not in page, (
+        "the page reads the gate rather than the count beneath it"
+    )
+
+
+def test_the_page_writes_no_dimension_and_no_class_name_of_its_own():
+    """Every dimension and every colour is a constant in theme.py and
+    every class name the rail carries is written in reconstruct_steps.py,
+    so app.py names class strings and holds neither a value nor a rule
+    (DL-069, DL-188).
+
+    tests/test_gui_theme.py already bars a hex literal from the whole
+    module; what this adds is the pixel sizes, which that sweep does not
+    read.
+
+    Mutation: `"wizard-resolve-split"` in app.py was replaced with
+    `"wizard-resolve-split w-[400px]"` and this guard rerun. Observed:
+        E       AssertionError: the page writes a dimension: ['400px']
+        E       assert ['400px'] == []
+        E
+        E         Left contains one more item: '400px'
+        E         Use -v to get more diff
+    """
+    written = re.findall(r"\b\d+(?:\.\d+)?px\b", _page_source())
+    assert written == [], f"the page writes a dimension: {written}"
+
+
+def test_the_resolve_table_dispatches_through_the_keymap():
+    """Digits 1-9 reach a pick through keymap.dispatch at SCOPE_TABLE and
+    this route's own applier table, so the second table honours the map
+    Specs binds rather than inventing one (DL-071, DL-205).
+
+    Read out of the on_key handler's own subtree. The page dispatches in
+    two places - the rail's "Skip for now" control resolves an ArrowDown
+    through the same map - so a scope read anywhere in the page is
+    satisfied by the control's call while the handler's own scope is
+    wrong.
+
+    Mutation: `keymap.SCOPE_TABLE` in on_key's dispatch call in app.py
+    was replaced with `keymap.SCOPE_DIALOG` and this guard rerun.
+    Observed:
+        E       AssertionError: the resolve table's key handler dispatches in the table scope
+        E       assert 'keymap.SCOPE_TABLE,' in 'def on_key(event) -> None:\\n         [...]
+    """
+    handler = _named_function_source("on_key")
+    assert "keymap.dispatch(" in handler
+    assert "keymap.SCOPE_TABLE," in handler, (
+        "the resolve table's key handler dispatches in the table scope"
+    )
+    assert "_RECONSTRUCT_ACTION_APPLIERS.get(action.name)" in handler, (
+        "a dispatched action reaches this route's own applier table"
+    )
+    assert "candidate_count=len(" in handler, (
+        "a digit past the focused row's answers is refused by dispatch"
+    )

```

**Documentation:**

```diff
--- a/tests/test_gui_resolve_composition.py
+++ b/tests/test_gui_resolve_composition.py
@@ -9,6 +9,12 @@
 own width are read on a served page and written into a record under
 docs/ (DL-084, DL-169, DL-189).
 
+A class string this file reads off a call site is only half of a name:
+what the sheet declares for the same name is read in
+tests/test_gui_resolve_sheet.py, and tests/test_gui_theme.py sweeps every
+.wizard-* class the sheet defines for a call site, so a name carried at
+one side and missing at the other fails there rather than passing here.
+
 Each guard records the mutation applied to make it fail and the verbatim
 output observed under that mutation. Where pytest printed an assertion
 repr longer than the margin, the line is cut with an ellipsis rather than

```


**CC-M-002-004** (tests/test_gui_conflict_page_controls.py) - implements CI-M-002-004

**Code:**

```diff
diff --git a/tests/test_gui_conflict_page_controls.py b/tests/test_gui_conflict_page_controls.py
index f299ffc..85ce41a 100644
--- a/tests/test_gui_conflict_page_controls.py
+++ b/tests/test_gui_conflict_page_controls.py
@@ -573,8 +573,8 @@ def test_no_decision_arithmetic_is_written_inline() -> None:
     meaning of a pick come from conflict_model, which is where the suite
     can reach them (DL-069, DL-106).
 
-    Observed to fail against a real mutation: replacing the outstanding
-    count's `decisions.outstanding(groups)` in app.py with
+    Observed to fail against a real mutation: replacing the gate's
+    `conflict_model.resolve_gate(decisions, groups)` in app.py with
     `sum(1 for view in decisions.rows(groups) if view.decision == "undecided")`
     and running this test raised:
         AssertionError: the page must not count decisions itself; it
@@ -597,11 +597,12 @@ def test_no_decision_arithmetic_is_written_inline() -> None:
         if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub))
     ]
     assert not arithmetic, (
-        "the page must hold no count arithmetic; the outstanding count is "
-        "read from conflict_model.ConflictDecisions.outstanding"
+        "the page must hold no count arithmetic; the outstanding count and "
+        "the decided count are read from conflict_model.resolve_gate"
     )
-    assert _calls(page, "outstanding"), (
-        "the page must render conflict_model's outstanding count"
+    assert _calls(page, "resolve_gate"), (
+        "the page must read conflict_model's resolve gate, which carries the "
+        "outstanding count and the advancing control's enabled state together"
     )
 
 
@@ -709,9 +710,11 @@ def test_a_bulk_action_leaves_a_row_its_collection_holds_no_record_in_undecided(
     assert driven.resolutions[-1] == {held: (2, held)}, (
         "bravo's bulk action must settle only the group bravo holds a record in"
     )
-    assert "1 of 2 still undecided" in driven.label_texts(), (
+    assert any(
+        "1 decided, 1 to go" in str(text) for text in driven.label_texts()
+    ), (
         "the group bravo holds no record in must still be counted as undecided; "
-        f"the page rendered {[text for text in driven.label_texts() if 'undecided' in str(text)]}"
+        f"the page rendered {[text for text in driven.label_texts() if 'to go' in str(text)]}"
     )
 
 

```

**Documentation:**

```diff
--- a/tests/test_gui_conflict_page_controls.py
+++ b/tests/test_gui_conflict_page_controls.py
@@ -710,6 +710,10 @@ def test_a_bulk_action_leaves_a_row_its_collection_holds_no_record_in_undecided(
     assert driven.resolutions[-1] == {held: (2, held)}, (
         "bravo's bulk action must settle only the group bravo holds a record in"
     )
+    # The phrase read back is the tally's own, the sentence the resolve
+    # step's footer prints from conflict_model.resolve_gate's two counts;
+    # it is read off the labels the drive recorded rather than off the
+    # gate, so what is held is what the page rendered.
     assert any(
         "1 decided, 1 to go" in str(text) for text in driven.label_texts()
     ), (

```


**CC-M-002-005** (tests/test_gui_keymap.py) - implements CI-M-002-006

**Code:**

```diff
diff --git a/tests/test_gui_keymap.py b/tests/test_gui_keymap.py
index cf19fb4..fdd4519 100644
--- a/tests/test_gui_keymap.py
+++ b/tests/test_gui_keymap.py
@@ -532,3 +532,97 @@ def test_jump_to_search_has_no_entry():
         candidate_count=9,
     )
     assert action is None
+
+
+# The reconstruct route carries a second applier table. keymap.py itself
+# carries the digit bindings both tables read: its entries bind digits
+# 1-9 to pick_candidate at SCOPE_TABLE. What these two guards hold is
+# that the second table is inside the contract the first is held to
+# (DL-205).
+_RECONSTRUCT_TABLE = re.compile(
+    r"_RECONSTRUCT_ACTION_APPLIERS\s*=\s*\{(.*?)\n\}", re.DOTALL
+)
+
+# The actions the resolve table answers: the four movements Specs binds
+# over a table, the digit pick, and the per-row undo. Written here rather
+# than derived from the table under test, so a name dropped from the
+# table is a failure rather than a shrinking expectation.
+_RESOLVE_TABLE_ACTIONS = {
+    "move_up",
+    "move_down",
+    "move_home",
+    "move_end",
+    "pick_candidate",
+    "undo_row",
+}
+
+
+def _reconstruct_applier_keys() -> set:
+    """The key set _RECONSTRUCT_ACTION_APPLIERS' source text binds."""
+    source = _APP_PY.read_text(encoding="utf-8")
+    match = _RECONSTRUCT_TABLE.search(source)
+    assert match is not None, "_RECONSTRUCT_ACTION_APPLIERS table not found in app.py"
+    return set(re.findall(r'"([a-z_]+)":', match.group(1)))
+
+
+def test_the_reconstruct_applier_table_is_inside_the_keymap_contract():
+    """Every key _RECONSTRUCT_ACTION_APPLIERS binds is an action name
+    keymap.dispatch can return, and the table holds an applier for every
+    action the resolve table answers. A name the table does not carry
+    would be a keypress that resolves and then does nothing, which is
+    what DL-080's no-fall-through guarantee exists to prevent.
+
+    Mutation: the `"undo_row": _reconstruct_undo,` line was deleted from
+    _RECONSTRUCT_ACTION_APPLIERS in app.py and this guard rerun.
+    Observed:
+        E       AssertionError: the resolve table answers an action with no applier: {'undo_row'}
+        E       assert {'undo_row'} == set()
+        E
+        E         Extra items in the left set:
+        E         'undo_row'
+        E         Use -v to get more diff
+
+    Mutation, the other direction: `"pick_collection": _reconstruct_pick,`
+    - a name keymap.ENTRIES carries no row for - was added to
+    _RECONSTRUCT_ACTION_APPLIERS in app.py and this guard rerun.
+    Observed:
+        E       AssertionError: the table binds a name keymap cannot return: {'pick_collection'}
+        E       assert {'pick_collection'} == set()
+        E
+        E         Extra items in the left set:
+        E         'pick_collection'
+        E         Use -v to get more diff
+    """
+    keys = _reconstruct_applier_keys()
+    outside = keys - set(keymap.ACTION_NAMES)
+    assert outside == set(), (
+        f"the table binds a name keymap cannot return: {outside}"
+    )
+    unanswered = _RESOLVE_TABLE_ACTIONS - keys
+    assert unanswered == set(), (
+        f"the resolve table answers an action with no applier: {unanswered}"
+    )
+
+
+def test_the_digit_entries_stay_bound_to_pick_candidate_over_the_table():
+    """keymap.py carries the digit bindings: digits 1-9 resolve to
+    pick_candidate at SCOPE_TABLE, and the resolve table reads that
+    binding rather than declaring one of its own (DL-071, DL-205).
+
+    Mutation: the digit expansion's scope in ENTRIES was changed from
+    SCOPE_TABLE to SCOPE_DIALOG in keymap.py and this guard rerun.
+    Observed:
+        E           AssertionError: digits 1-9 pick a candidate over the table
+        E           assert None is not None
+    """
+    for digit in range(1, 10):
+        action = keymap.dispatch(
+            str(digit),
+            (),
+            keymap.SCOPE_TABLE,
+            row_count=9,
+            focused_index=0,
+            candidate_count=9,
+        )
+        assert action is not None, "digits 1-9 pick a candidate over the table"
+        assert action.name == "pick_candidate"
+        assert action.args == {"digit": digit}

```

**Documentation:**

```diff
--- a/tests/test_gui_keymap.py
+++ b/tests/test_gui_keymap.py
@@ -538,7 +538,12 @@ def test_jump_to_search_has_no_entry():
 # carries the digit bindings both tables read: its entries bind digits
 # 1-9 to pick_candidate at SCOPE_TABLE. What these two guards hold is
 # that the second table is inside the contract the first is held to
 # (DL-205).
+#
+# The table is read out of app.py's source text rather than imported:
+# app.py imports nicegui and the suite runs under an interpreter that has
+# none, so a regex over the file is the only reading of that module
+# available here (DL-069).
 _RECONSTRUCT_TABLE = re.compile(
     r"_RECONSTRUCT_ACTION_APPLIERS\s*=\s*\{(.*?)\n\}", re.DOTALL
 )

```


**CC-M-002-006** (traktor_nml/gui/reconstruct_steps.py) - implements CI-M-002-001

**Code:**

```diff
diff --git a/traktor_nml/gui/reconstruct_steps.py b/traktor_nml/gui/reconstruct_steps.py
new file mode 100644
index 0000000..5b76568
--- /dev/null
+++ b/traktor_nml/gui/reconstruct_steps.py
@@ -0,0 +1,180 @@
+"""The reconstruct page's step table and the rail records it renders,
+with no framework import.
+
+STEPS is the one place a step number or a step label is written:
+`Reconstruct.dc.html`, `Preview.dc.html`, `Resolve.dc.html` and
+`Write.dc.html` draw one rail of four steps and each names its own row,
+so the four artboards agree on the order and this table carries it.
+rail_records(current) derives one record per row in that same order,
+carrying the row's number and label plus the three things a rail entry
+renders with - whether it reads done, current or upcoming, the class
+string it carries, and its aria-current value.
+
+Two axes are kept apart here, the way navigation.py keeps the section
+table apart from the active route: the table is what the rail holds, and
+the step the page is showing is what the operator has walked to.
+Position is the single point where they meet - a row before the current
+one reads done, the row equal to it reads current, and a row after it
+reads upcoming, exactly one current at a time, and a current number
+matching no row leaves every row upcoming rather than falling back to
+the first (DL-202).
+
+reachable() is the second rule and is separate from the first on
+purpose: a rail says where the operator is, and reachability says where
+they may go. The resolve step's gate is conflict_model.resolve_gate's
+own answer, so the rule that shuts the write step and the sentence the
+footer prints read one value (DL-204).
+
+Every rule here is a pure computation over integers and strings, so a
+guard runs it on an interpreter with no framework present (DL-203).
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+# The four step numbers, named so a call site names a step rather than a
+# digit. The numbers are the rail's own, counted from one, because the
+# rail renders them.
+SET_UP = 1
+PREVIEW = 2
+RESOLVE = 3
+WRITE = 4
+
+# The ordered step table: number first, label second. Every other module
+# names a step or a label by reading this table.
+STEPS: tuple[tuple[int, str], ...] = (
+    (SET_UP, "Set up"),
+    (PREVIEW, "Preview"),
+    (RESOLVE, "Resolve"),
+    (WRITE, "Write"),
+)
+
+# The three positions a rail entry reads, as tokens rather than as
+# booleans: a done row and an upcoming row differ in what has happened
+# to them, not in a single flag's polarity.
+DONE = "done"
+CURRENT = "current"
+UPCOMING = "upcoming"
+
+# The class every rail entry carries, and the second class a done or a
+# current entry carries alongside it. The three name theme.py's own
+# ".wizard-step", ".wizard-step-done" and ".wizard-step-current" rules;
+# this module writes the names and theme.py holds the values behind them
+# (DL-069, DL-188).
+STEP_CLASS = "wizard-step"
+STEP_DONE_CLASS = "wizard-step-done"
+STEP_CURRENT_CLASS = "wizard-step-current"
+
+# The class the marker inside every entry carries, and the second class
+# the current entry's marker carries alongside it. The current marker is
+# its own class rather than a rule descending from STEP_CURRENT_CLASS,
+# because its ink is read against the ground the marker paints rather
+# than against the ground of the entry around it.
+MARKER_CLASS = "wizard-step-number"
+MARKER_CURRENT_CLASS = "wizard-step-number-current"
+
+# The aria-current value the current entry reads, and the value the rest
+# read: None, which is the absence of the attribute rather than an empty
+# string. "step" rather than "page", which is what Resolve.dc.html:124
+# carries on the entry it draws as current.
+ARIA_CURRENT_STEP = "step"
+
+# What a done entry renders in its marker in place of its number: the
+# check mark Resolve.dc.html:122-123 draws on the two steps behind the
+# current one. Written as an escape rather than as the glyph, so this
+# module stays ASCII on disk and a tool reading it under a codepage
+# that has no U+2713 reads it at all.
+DONE_MARKER = "\u2713"
+
+
+@dataclass(frozen=True)
+class RailRecord:
+    """One rendered rail entry: the row's number and label, the position
+    it reads, the class string it renders with, the text its marker
+    carries, and its aria-current value or None."""
+
+    number: int
+    label: str
+    state: str
+    classes: str
+    marker: str
+    marker_classes: str
+    aria_current: str | None
+
+
+def rail_records(current: int) -> tuple[RailRecord, ...]:
+    """One record per STEPS row in table order.
+
+    The record whose number equals current reads CURRENT and carries
+    both STEP_CLASS and STEP_CURRENT_CLASS at aria-current
+    ARIA_CURRENT_STEP; a record before it reads DONE and carries
+    STEP_CLASS and STEP_DONE_CLASS at aria-current None; a record after
+    it reads UPCOMING and carries STEP_CLASS alone. A current equal to
+    no row's number leaves every record UPCOMING, so a caller holding a
+    number the table does not name renders a rail with nothing marked
+    rather than a rail marking the first row by accident.
+    """
+    return tuple(_record(number, label, current) for number, label in STEPS)
+
+
+def _record(number: int, label: str, current: int) -> RailRecord:
+    if number == current:
+        state = CURRENT
+    elif any(row == current for row, _ in STEPS) and number < current:
+        state = DONE
+    else:
+        state = UPCOMING
+    return RailRecord(
+        number=number,
+        label=label,
+        state=state,
+        classes=_classes(state),
+        marker=DONE_MARKER if state == DONE else str(number),
+        marker_classes=(
+            f"{MARKER_CLASS} {MARKER_CURRENT_CLASS}"
+            if state == CURRENT
+            else MARKER_CLASS
+        ),
+        aria_current=ARIA_CURRENT_STEP if state == CURRENT else None,
+    )
+
+
+def _classes(state: str) -> str:
+    if state == CURRENT:
+        return f"{STEP_CLASS} {STEP_CURRENT_CLASS}"
+    if state == DONE:
+        return f"{STEP_CLASS} {STEP_DONE_CLASS}"
+    return STEP_CLASS
+
+
+def reachable(target: int, has_result: bool, all_decided: bool) -> bool:
+    """Whether the page may show `target`.
+
+    SET_UP is always reachable: it is where the collections are named
+    and a run is discarded whenever one of them changes, so an operator
+    walking back to it is walking to the controls that fix whatever
+    stopped them.
+
+    PREVIEW and RESOLVE need a held run. The preview is the run - the
+    page calls assemble_output with dry_run and holds what it returned -
+    so a resolve step without one would offer answers over groups no run
+    reported (DL-107).
+
+    WRITE needs a held run whose divergences are every one decided.
+    all_decided is conflict_model.resolve_gate's own answer, so the step
+    this refuses and the count the footer prints cannot disagree
+    (DL-204). A run that reported no divergence at all reads all_decided
+    True and passes straight through, which is the same answer the gate
+    gives for an empty group set.
+
+    A target no STEPS row names is refused rather than defaulted, so a
+    caller holding a number the table does not carry stays where it is.
+    """
+    if not any(number == target for number, _ in STEPS):
+        return False
+    if target == SET_UP:
+        return True
+    if target in (PREVIEW, RESOLVE):
+        return has_result
+    return has_result and all_decided

```

**Documentation:**

```diff
--- a/traktor_nml/gui/reconstruct_steps.py
+++ b/traktor_nml/gui/reconstruct_steps.py
@@ -121,2 +121,11 @@ def rail_records(current: int) -> tuple[RailRecord, ...]:
 def _record(number: int, label: str, current: int) -> RailRecord:
+    """One row's record, read from its position against `current`.
+
+    DONE is guarded on `current` naming a row of its own, so a number
+    the table does not carry leaves the rows after it UPCOMING rather
+    than reading every row done. The marker is the check mark for a done
+    row and the row's own number otherwise, which is what
+    Resolve.dc.html:122-123 draws on the two steps behind the current
+    one and :124 on the current one.
+    """
     if number == current:
@@ -143,2 +152,10 @@ def _record(number: int, label: str, current: int) -> RailRecord:
 def _classes(state: str) -> str:
+    """The class string one entry carries for its position.
+
+    STEP_CLASS is on every entry and a done or a current entry carries
+    its state class beside it. Which of the two paints is theme.py's
+    to settle - it declares the state rules after .wizard-step, so they
+    win at equal specificity - and this module writes names alone
+    (DL-069).
+    """
     if state == CURRENT:

```


**CC-M-002-007** (docs/CLAUDE.md) - implements CI-M-002-007

**Code:**

```diff
diff --git a/docs/CLAUDE.md b/docs/CLAUDE.md
--- a/docs/CLAUDE.md
+++ b/docs/CLAUDE.md
@@ -21,6 +21,7 @@
 | `2026-09-03-header-tabs-browser-record.md` | DL-084 served-page record for the app header and its two section tabs at commit `1fed6e7`: the status of `/`, `/reconnect` and the unrouted `/reconstruct`, and the paint and markup of each tab read off the served DOM, and a structural section stating that `/` is outside the structural gate under DL-172 | Checking how the header tabs and the `/reconstruct` 404 were verified on a served page, or why `/` carries no structural verdict |
 | `2026-09-06-wizard-focus-order-browser-record.md` | DL-084 served-page record of the tab ring walked by nine real `Tab` presses on the Set up step: header, then the middle, then the footer band, with the advancing control the last stop and no hidden step group reachable; the focus ring read as `2px solid` `TEXT` at a `2px` offset; and the two live regions present and empty at load | Checking the focus order against a page whose advancing controls sit in the footer band, or why a focus reading taken from script reports no ring |
 | `2026-09-07-composition-close-browser-record.md` | The post-strike served-page record at 1280x900, taken with the App shell, Card structure and Footer band entries absent from "Composition not built": the two band heights, the middle at the full width, the centred card column and the band's note inset re-read on both routes; carries structural verdicts reading `matches` on those three structures and `differs` on the three that stand | Checking the reading a struck Composition-not-built entry rests on, or how a milestone closes on a record taken after its strike |
+| `2026-09-07-reconstruct-resolve-browser-record.md` | DL-084 served-page record for the reconstruct route's four-step scaffold and its Resolve step at 1280x900: the step rail, the four step regions, the tally and bulk strip, the split's two columns, the conflict grid's five tracks under its header row, the 400px detail rail's three bands, and the footer's outstanding count beside its gated control, each read against `Resolve.dc.html` and carrying a structural reading, with the keyboard and announcement readings retaken | Checking what the reconstruct page composes at `/`, or reading the tab ring for a page whose advancing controls sit in step regions |
 | `traktor_nml_tool_plan.md`               | Original product/technical design plan (Phase 1 reconnect, Phase 2 splice/split) | Looking up historical design rationale for reconnect/splice/split |
 | `traktor_nml_tool_execution_plan.md`     | Detailed implementation plan, decisions, constraints, acceptance criteria for Phase 1/2 | Looking up why a specific pre-existing behavior was implemented that way |
 | `chat_export.md`                         | Concise export of the development conversation that shaped the work | Historical context only                                |

```

**Documentation:**

```diff
--- a/docs/CLAUDE.md
+++ b/docs/CLAUDE.md

```


### Milestone 3: The decision log and the structural gate

**Files**: traktor_nml/README.md, traktor_nml/gui/README.md, tests/test_docs_browser_record_structure.py

**Requirements**:

- traktor_nml/README.md carries DL-198 through DL-212, one statement per decision, cited in prose as (DL-NNN), continuing from the DL-197 high-water mark.
- DL-172's entry states that / is inside the structural gate read against the four page-3 artboards; the exemption is struck, not restated (DL-200).
- The three entries under 'Composition not built' each name the reconnect wizard's route and the artboard they are read against; the reconstruct page's column model, table geometry and detail rail carry no entry, because gui/ composes all three (DL-201).
- DL-191's statement is revised in the same edit: the reconnect wizard's three entries stand because each is read against that route's own artboards and that route composes none of them, not because theme.py emits no rule of the kind (DL-191, DL-201).
- Nothing leaves 'Composition not built', so DL-190's post-strike trigger does not fire, no prose here cites DL-190 for a strike, and this milestone takes no served-page record: it composes no page (DL-210).
- The reconstruct page's three structures are cited to docs/2026-09-07-reconstruct-resolve-browser-record.md, the record M-002 closes on, under DL-084 and DL-169.
- gui/README.md's module table names reconstruct_steps.py and states which step mechanism serves which route (DL-202).
- README.md and docs/*.md are LF; prose describes the code as it stands, with no 'previously', 'now does', 'no longer', 'added' or 'moved'.

**Acceptance Criteria**:

- Every DL-198..DL-212 statement resolves to prose that cites it, each number carries exactly one statement, and no citation names a source for something it does not say.
- DL-172's entry states that the gate covers /, read against the four page-3 artboards, and carries no exemption.
- Each of the reconnect wizard's three 'Composition not built' entries still names the same structure it names now - the two-column `main` in Main.dc.html, Confirm.dc.html and Results.dc.html; `.gr`'s five tracks under `.th` in Review.dc.html; the 400px `.det` panel with its head, body and footer in Review.dc.html - against the same artboard file and selector, and each still reads `differs` for `/reconnect`. The only edit to each is the narrowing that names the reconnect route and appends its citation: no entry is struck, added, moved or given a different structure, artboard, selector or verdict (DL-191, DL-201).
- No entry for the reconstruct page's column model, table geometry or detail rail exists anywhere in the section, at this commit or any earlier one in this plan.
- DL-191's statement gives the per-route reading as the reason its three entries stand, and names no absent theme.py rule.
- No prose added by this milestone cites DL-190, and this milestone adds no file under docs/.
- tests/test_docs_browser_record_structure.py passes, reading the reconstruct page's record against the reconstruct page's own section of the decision log.
- tests/baselines/manifest.json and the fixture/w002gatefix2 gate fixture are untouched.

**Tests**:

- tests/test_docs_browser_record_structure.py: docs/2026-09-07-reconstruct-resolve-browser-record.md is discovered by name and reached by every guard in the file; READING_DIGESTS carries no entry for it and the comment says why.
- The full suite under the system interpreter at C:\Users\marcu\AppData\Local\Python\pythoncore-3.14-64\python.exe.

#### Code Intent

- **CI-M-003-001** `traktor_nml/README.md`: DL-198 through DL-212 are recorded, one statement per decision. DL-172's entry states that the reconstruct page is inside the structural gate and read against the four page-3 artboards, the exemption struck rather than restated. The three 'Composition not built' entries read against the reconnect wizard's artboards stand, each narrowed to name that route, and DL-191's statement is revised to give that narrowing as the reason they stand. The reconstruct page's own column model, table geometry and detail rail carry no entry there: gui/ composes all three, so the section's prose names them as structures read built in docs/2026-09-07-reconstruct-resolve-browser-record.md under DL-084 and DL-169, and cites DL-190 nowhere, since nothing is struck. (refs: DL-200, DL-201, DL-209, DL-210, DL-211, DL-212)
- **CI-M-003-002** `traktor_nml/gui/README.md`: The module table names reconstruct_steps.py and what it holds, states that / drives plain step regions from that table while /reconnect drives a ui.stepper, and the section on what the guards can and cannot see states that the step rail's rendered position, the grid's resolved column widths and the rail's resolved width belong to the served-page record. (refs: DL-202, DL-203, DL-211)
- **CI-M-003-003** `tests/test_docs_browser_record_structure.py`: READING_DIGESTS carries no entry for the record M-002 adds and a note says why: a digest hashes the readings a run recorded, so it is written by the run that takes them. Every other guard in the file reaches that record by name as soon as it exists, and the structural gate reads the reconstruct page's record against the decision log's own section for that route. (refs: DL-200, DL-201)

#### Code Changes

**CC-M-003-001** (traktor_nml/README.md) - implements CI-M-003-001

**Code:**

```diff
diff --git a/traktor_nml/README.md b/traktor_nml/README.md
index a920dbc..89685ff 100644
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -741,14 +741,14 @@ statement of the same decision would only give it two copies to drift apart.
   do. The structural reading is what a person looking at the two
   screens sees first, so it is the reading the gate cannot omit
   (DL-169).
-- The reconstruct page at `/` is outside the structural gate, and the
-  ground is stated wherever a record covers it: no artboard draws that
-  page - all ten draw the reconnect wizard - and `Specs.dc.html`,
-  which governs under DL-088, specifies its behaviour and no
-  composition. A structural verdict needs a drawn structure to read
-  against, so the gate has nothing to compare and says so rather than
-  reading matches by default. Its atom readings are gated as any other
-  surface's are (DL-172).
+- The structural gate covers every route a record measures, the
+  reconstruct page at `/` included: `Reconstruct.dc.html`,
+  `Preview.dc.html`, `Resolve.dc.html` and `Write.dc.html` on canvas
+  page 3 draw that page, so a structural verdict has a drawn structure
+  to read against and a record covering `/` carries one per surface.
+  `Specs.dc.html`, which governs under DL-088, specifies the behaviour
+  the four screens render; the composition is read from the screens.
+  Atom readings are gated as any other surface's are (DL-172, DL-200).
 - A structural differs entry is recorded under its own heading,
   "Composition not built", and not under either heading beside it: a
   framework shortfall is a rule the running framework refuses, a
@@ -882,12 +882,16 @@ statement of the same decision would only give it two copies to drift apart.
   structure built, the prose that strikes it names the record and the
   reading that carries it, and the milestone that strikes it closes on a
   served-page record of its own, taken after the strike (DL-190).
-- The reconstruct page composes against the same shell as the reconnect
-  wizard - the same bands, the same middle, the same card triplet - and
-  DL-172 decides what a record may verdict about that route, not which
-  shell it is built from. The two-column `main`, the review table's grid
-  geometry and the 400px detail rail are outside this work's scope, so
-  each stands as written under "Composition not built" (DL-191).
+- The reconstruct page composes against the same shell as the reconnect
+  wizard - the same bands, the same middle, the same card triplet - and
+  DL-172 decides what a record may verdict about that route, not which
+  shell it is built from. The two-column `main`, the review table's grid
+  geometry and the 400px detail rail stand under "Composition not built"
+  because each is read against the reconnect wizard's own artboards and
+  that route composes none of the three, not because `theme.py` emits no
+  rule of the kind: it emits `.wizard-resolve-split`,
+  `.wizard-conflict-grid` and `.wizard-detail-rail`, which `/` composes
+  (DL-191, DL-201).
 - `nicegui.css` sets `align-items: flex-start`, `gap: 1rem` and
   `padding: 1rem` on `.nicegui-header` and `.nicegui-footer` and gives
   both `flex-direction: row`, so each band restates the alignment, the
@@ -915,6 +919,117 @@ statement of the same decision would only give it two copies to drift apart.
   each advancing control is built in the footer band, because its place
   in the DOM sets both the tab order and the point an announcement is
   triggered from (DL-197).
+- The reconstruct page is stepped: `Reconstruct.dc.html`,
+  `Preview.dc.html`, `Resolve.dc.html` and `Write.dc.html` each draw the
+  header as the brand, its divider and the two section tabs, and each
+  draws the four-step rail inside `main` rather than in the header band,
+  so the rail and the tab strip sit in different regions and neither
+  displaces the other. `Specs.dc.html` and the four screens agree on the
+  header, so DL-071 asks nothing of Specs here (DL-198).
+- The rail is a `nav` of this module's own spans rendered from
+  `reconstruct_steps.rail_records`, placed as the page region's first
+  row, rather than a `QStepper` header: `Resolve.dc.html:121` places
+  `nav.steprail` as `main`'s first child and `:104` states its rule, and
+  a QStepper draws its own numbered strip above its panels and none of
+  the rail's states. `.wizard-step-rail`
+  carries the artboard's `grid-column: 1 / -1` for fidelity with that
+  rule and the declaration is inert: `grid-column` applies to a grid
+  item, and the rail's parent `.wizard-middle` is a flex column, which
+  stretches the rail across the region on its own. The artboard's own
+  `main` is a single-column grid, where the declaration is equally
+  inert. Giving `.wizard-middle` a grid display is what would make it
+  live (DL-199).
+- The reconstruct page at `/` is inside the structural gate, read
+  against the four artboards on canvas page 3 that draw it. A structural
+  verdict reads against a drawn structure, so
+  every record covering that route carries a structural reading per
+  surface beside its atom readings, as a record covering `/reconnect`
+  does (DL-200).
+- The three entries under "Composition not built" each name the
+  reconnect wizard's route and the artboard they are read against, and
+  the reconstruct page's column model, table geometry and detail rail
+  carry no entry beside them: an entry there names a structure `gui/`
+  does not compose, and `gui/` composes all three on `/`.
+  `Review.dc.html`'s geometry and `Resolve.dc.html`'s are different
+  geometries on different routes, so one entry cannot end for both,
+  which is why the reconnect wizard's three stand while `/`'s versions
+  are read built in
+  `docs/2026-09-07-reconstruct-resolve-browser-record.md` (DL-084,
+  DL-169, DL-201).
+- `reconstruct_steps.STEPS` is the one place a step number or a step
+  label is written, and position is the single point where the table and
+  the step the operator has walked to meet: a row before the current one
+  reads done, the row equal to it reads current, a row after it reads
+  upcoming, and a current number the table does not name leaves every row
+  upcoming rather than marking the first (DL-202).
+- `reconstruct_steps.py` imports no framework, so the rail's records and
+  the reachability rule are read by the suite under the system
+  interpreter; `app.py` renders the records and decides none of them
+  (DL-203).
+- `conflict_model.resolve_gate` answers the outstanding count, the
+  decided count and whether the step may be left in one value over one
+  walk of the groups, and the footer's sentence and the advancing
+  control's enabled state both read it: a count computed for the sentence
+  and an emptiness computed again for the control can disagree, and the
+  disagreement shows as a control the operator can press over a sentence
+  saying they cannot (DL-204).
+- The reconstruct route carries its own name-to-applier table.
+  `keymap.py` carries the digit bindings both tables read, binding
+  digits 1-9 to `pick_candidate` at `SCOPE_TABLE`, and the wizard's own
+  `_ACTION_APPLIERS` is typed on `_WizardPageState`, whose review rows
+  and decisions this route holds none of, so the second table dispatches
+  the same action names onto the resolve table's own holder rather than
+  widening the first. DL-080's guard pins the wizard's table to
+  `keymap.ACTION_NAMES` exactly and covers that table alone; the second
+  table is held to a subset-and-coverage claim of its own - its key set
+  is a subset of `keymap.ACTION_NAMES`, and it answers every action the
+  resolve table dispatches - which is what leaves no action falling
+  through here (DL-205).
+- The conflict table is a CSS grid: `.wizard-conflict-grid` carries
+  `Resolve.dc.html:55`'s five tracks and both the header row and every
+  body row are laid out on it, so a heading stands over its column.
+  `ui.aggrid` is not adopted, for the reason DL-079 gives for the
+  review table: it claims the arrow keys Specs binds over this same
+  table (DL-206).
+- The detail rail carries one control per distinct answer, keyed on
+  `conflict_model.candidate_reference`, and the strip above the table
+  carries one bulk action per input collection, keyed on
+  `conflict_model.reference_from_input`. A control names the record that
+  wins rather than the collection it came from, so two collections
+  holding identical values are one control naming both, and a bulk
+  action leaves undecided any group its own collection holds no record
+  in. The chosen answer is marked by a class string at the call site and
+  a dot element rather than by a `::after`, because a guard can read a
+  class and cannot read a pseudo-element (DL-207).
+- Steps 1, 2 and 4 hold the content the reconstruct page composes: the
+  three configuration cards and the conflict-policy control in step 1,
+  the preview report in step 2, and the write card in step 4. Each holds
+  its own cards, holders and callbacks; a step region is a container the
+  page enters with a `with` statement, so the content keeps its own
+  nesting (DL-208).
+- Every guard this work adds is run against a named mutation and fails
+  under it before it is kept, and its docstring carries both the
+  mutation and the verbatim output pytest printed. A line pytest printed
+  longer than the margin is cut with an ellipsis rather than rewrapped,
+  so what stands is what pytest printed (DL-209).
+- A milestone that emits rules and composes no page closes on its
+  guards and its diff and takes no served-page record, and the rules it
+  emits are read off a served page in the record of the milestone that
+  first composes them. The resolve step's sheet rules and its gate
+  predicate select no element until the four step regions and the
+  resolve screen exist, so the record that reads them is the one the
+  composition closes on (DL-210).
+- A milestone that composes a page closes on a served-page record under
+  `docs/` of its own, driven in a browser over HTTP and carrying a
+  matches-or-differs verdict and a structural reading per named surface.
+  Every guard over `gui/` reads source text or walks the AST under an
+  interpreter with no nicegui, so the served page is the only reading
+  that can contradict the sheet, and it is the only gate that has caught
+  a defect in `gui/` (DL-084, DL-169, DL-211).
+- The statements for DL-198 through DL-212 stand in one commit, and the
+  code and guard docstrings that carry these numbers are written in the
+  two commits before it, where each number is a forward reference into
+  this plan. Each statement describes the code as it stands, and the
+  "Composition not built" section can only be written against a record
+  that has read the structures built, so the log trails the code it
+  describes rather than being split across three edits to the same two
+  sections (DL-212).
 - Every documentation edit in this work describes the file as it
   stands, with no "previously", "now does", "no longer" or "added",
   and each documentation milestone carries the grep that proves it
@@ -1969,51 +2084,75 @@ An entry names the structure, the artboard file and selector it is
 An entry names the structure, the artboard file and selector it is
 read from, and what `gui/` composes in its place.

-Every entry below is read against the reconnect wizard's artboards.
-The reconstruct page at `/` carries no entry, because no artboard
-draws it and the structural gate does not cover it (DL-172).
+Each entry names the route and the artboard it is read against. The
+three below are read against the reconnect wizard's artboards. The
+reconstruct page's own column model, table geometry and detail rail are
+read against `Resolve.dc.html` and its three siblings on canvas page 3
+and carry no entry, because `gui/` composes all three: the two sets are
+different geometries on different routes, so an entry ending for one
+ends nothing for the other (DL-200, DL-201).

 An entry ends by being built and read off a served page, not by being
 excused; where a run reads a structure only partly built, the entry is
 narrowed to what the framework refused rather than struck (DL-190,
 DL-194).

 Three structures the artboards draw carry no entry here, each read
 built in `docs/2026-09-07-composition-close-browser-record.md`, the
 record taken with those entries already absent from this section: the
 app shell, on the `56px` header, the `64px` footer and the middle at
 the full `1280px` between them, with the document not scrolling on
 either route and the middle scrolling on `/reconnect`; the card
 structure, on the four named cards the record reads on `/` and the one
 per rendered step it reads on `/reconnect`, each carrying its head, its
 title and its body; and the footer band, on the note at `x=24` and the
 visible actions at the right on both routes. Column model, Table
 geometry and Detail rail are the three that stand, and that record
-reads each of them `differs`: there is one column and no second column
-on either route, the review table is `.wizard-row`, a flex row with a
-gap and no header row, and no element composes a rail - the candidate
-panel is in the same column below the table. Each of those three
-entries states beneath it the reason it is open.
+reads each of them `differs`: on `/reconnect` there is one column and no
+second column, its review table is `.wizard-row`, a flex row with a gap
+and no header row, and no element composes a rail there - that route's
+candidate panel is in the same column below the table. Each of those
+three entries states beneath it the reason it is open.

 - **Column model.** `main` is `grid-template-columns: 1fr 400px` in
   `Main.dc.html`, `1fr 404px` in `Confirm.dc.html` and `1fr 384px` in
   `Results.dc.html`, a content column beside a guidance rail.
-  `theme.py` emits no two-column rule, and every page composes one
-  column at `.wizard-content-width`.
-  This entry stands as written: the two-column `main` is outside this
-  work's scope, and `main` is one column at `.wizard-content-width`
-  (DL-191).
+  `theme.py` emits no two-column rule for the reconnect wizard, and
+  every page of that route composes one column at
+  `.wizard-content-width`.
+  This entry stands as written: the reconnect wizard's two-column `main`
+  is outside this work's scope, and its `main` is one column at
+  `.wizard-content-width` (DL-191, DL-201).
 - **Table geometry.** `.gr` in `Review.dc.html` is
   `grid-template-columns: 126px minmax(0, 1fr) 100px 196px 134px`
   under a `.th` header row. `theme.py` emits `.wizard-row`, a flex row
-  with a gap and a zebra ground, so cells take their width from their
-  content and no column aligns from one row to the next, and neither
-  table carries a header row.
+  with a gap and a zebra ground, for the reconnect wizard's review
+  table, so that table's cells take their width from their content, no
+  column aligns from one row to the next, and it carries no header row.
   This entry stands as written: the review table's grid geometry and
-  its header row are outside this work's scope (DL-191).
+  its header row are outside this work's scope (DL-191, DL-201).
 - **Detail rail.** `.det` in `Review.dc.html` is a 400px bordered
   panel with its own header, body and footer holding the candidate
-  cards. `theme.py` emits no rail rule, and the reconstruct page
-  renders its candidate panel below the table in the same column.
-  This entry stands as written: the 400px detail rail is outside this
-  work's scope (DL-191).
+  cards. `theme.py` emits no rail rule for the reconnect wizard's
+  review table, and `/reconnect` renders its candidate panel below the
+  table in the same column.
+  This entry stands as written: the reconnect wizard's detail rail is
+  outside this work's scope (DL-191, DL-201).
+
+Three structures the reconstruct page's own artboards draw carry no
+entry here, each read built in
+`docs/2026-09-07-reconstruct-resolve-browser-record.md`, the record the
+milestone that composed them closed on (DL-084, DL-169): the
+reconstruct column model, on
+`.wizard-resolve-split` resolving to a content column beside a 400px
+rail, as `Resolve.dc.html:53`'s `.split` draws it; the reconstruct table
+geometry, on `.wizard-conflict-grid` resolving to the five tracks
+`Resolve.dc.html:55`'s `.gr` draws, with `.wizard-conflict-header`
+standing over the same tracks as every body row; and the reconstruct
+detail rail, on `.wizard-detail-rail` resolving to 400px and carrying
+the head, body and footer `Resolve.dc.html:70`, `:71`, `:74` and `:91`
+draw. The four-step rail and the four step regions those structures sit
+under are read in the same record. Where a run reads one of the three
+`differs`, the composition is corrected and the record retaken; only a
+structure the framework refuses outright earns an entry here, narrowed
+to what was refused (DL-194, DL-200, DL-201).

```

**Documentation:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md

```


**CC-M-003-002** (traktor_nml/gui/README.md) - implements CI-M-003-002

**Code:**

```diff
diff --git a/traktor_nml/gui/README.md b/traktor_nml/gui/README.md
index 81b0a01..f2ca7cd 100644
--- a/traktor_nml/gui/README.md
+++ b/traktor_nml/gui/README.md
@@ -10,8 +10,9 @@ vendored typeface is.
 `app.py`, `file_picker.py` and `__main__.py` are the only three modules
 in this package that import `nicegui` or `pywebview`. Every other
 module - `review_model.py`, `wizard_state.py`, `theme.py`, `keymap.py`,
-`announce.py`, `conflict_model.py`, `navigation.py`, `_fs_nav.py` and
-`__init__.py` - imports neither and is reachable from the test suite's
+`announce.py`, `conflict_model.py`, `navigation.py`,
+`reconstruct_steps.py`, `_fs_nav.py` and `__init__.py` - imports neither
+and is reachable from the test suite's
 system interpreter, which has no `nicegui` installed. Every rule worth
 testing sits below that boundary, in the nicegui-free modules, so the
 suite can reach it (DL-069; guarded by an AST walk in
@@ -197,6 +198,37 @@ once (DL-187). Its place in the DOM is what sets the tab order, and the
 ring that walk produces is read in
 `docs/2026-09-06-wizard-focus-order-browser-record.md` (DL-197).
 
+## The two step mechanisms
+
+Both routes are walked in four steps and neither drives the other's
+mechanism. `/reconnect` runs a `ui.stepper` with a `footer_groups`
+mapping keyed by step title. `/` composes four plain regions inside the
+chrome's middle, one visible at a time, under a `nav` of spans rendered
+from `reconstruct_steps.rail_records`: `Resolve.dc.html:121` places
+`nav.steprail` as `main`'s first child and `:104` states its rule, and a
+QStepper draws its own numbered strip above its panels and none of the
+rail's states. `.wizard-step-rail` carries the artboard's
+`grid-column: 1 / -1` and the declaration is inert: `grid-column`
+applies to a grid item and `.wizard-middle` is a flex column, so the
+declaration selects nothing. That inertness is a reading of the sheet.
+The width the rail resolves to in the page region is not: a flex column
+is expected to stretch it, and what the browser gave it is read on a
+served page and written into the record (DL-199).
+
+`reconstruct_steps.py` holds the four-step table, the rail records it
+derives and the reachability rule that decides which step the page may
+show. It is the one place a step number or a step label is written, and
+it imports no framework, so the suite reads it directly and `app.py`
+renders the records and decides none of them (DL-202, DL-203). The
+resolve step's own gate is `conflict_model.resolve_gate`, which answers
+the outstanding count, the decided count and whether the step may be
+left over one walk of the groups, so the footer's sentence and the
+advancing control's enabled state are one reading (DL-204).
+
+The resolve step's table dispatches through `keymap.dispatch` at
+`SCOPE_TABLE` and applies through the reconstruct route's own
+name-to-applier table, since the wizard's `_ACTION_APPLIERS` appliers
+are typed on the wizard's page state. `keymap.py` itself carries the
+digit bindings both tables read (DL-205).
+
 Every dimension either the shell or the cards measure at is a constant
 in `theme.py`, sourced in a comment to the artboard line that states
 it. `theme.py` imports no nicegui, so it is the module a guard under
@@ -206,4 +238,12 @@ What a guard in `tests/` holds of all this is the text: which rule the
 stylesheet emits, which class string a call site names, and where each
 control is constructed. Whether the browser gave the middle the
 viewport, and what it computed for a card, is read on a served page and
-written into a record under `docs/` (DL-084, DL-169, DL-189).
+written into a record under `docs/` (DL-084, DL-169, DL-189). The
+conflict grid's resolved column widths, the detail rail's resolved width
+and where the step rail lands in the page region belong to that record
+for the same reason: a guard reading
+`grid-template-columns: 1fr 400px` out of the emitted sheet is true
+whether or not the browser laid the split out on those tracks. What is
+not a question for the record is whether the rail's
+`grid-column: 1 / -1` does anything: it applies to a grid item, its
+parent is a flex column, and the sheet says so.

```

**Documentation:**

```diff
--- a/traktor_nml/gui/README.md
+++ b/traktor_nml/gui/README.md

```


**CC-M-003-003** (tests/test_docs_browser_record_structure.py) - implements CI-M-003-003

**Code:**

```diff
diff --git a/tests/test_docs_browser_record_structure.py b/tests/test_docs_browser_record_structure.py
index 2e66c21..5c48b36 100644
--- a/tests/test_docs_browser_record_structure.py
+++ b/tests/test_docs_browser_record_structure.py
@@ -74,6 +74,17 @@ READING_DIGESTS = {
     "2026-09-07-composition-close-browser-record.md": "24f5629d3285c3ed3575c8bb5b16d295a924aafa443f6c6419c60e829e19b696",
 }
 
+# docs/2026-09-07-reconstruct-resolve-browser-record.md carries no entry
+# above. A digest is the hash of the readings a run recorded, so it is
+# written by the run that takes them and not before: an entry standing
+# here ahead of the record would hash the readings this file guessed
+# rather than the ones the browser gave, which is the shape of the digest
+# that hashed the empty string. The record is discovered by name and
+# gated by every guard below the moment it exists; the digest guard skips
+# a record this mapping has no entry for. Every entry above hashes
+# readings a run has taken (DL-171, DL-209).
+
 
 def test_the_record_set_is_discovered_and_is_not_empty():
     """browser_records() finds the served-page records under docs/ by
```

**Documentation:**

```diff
--- a/tests/test_docs_browser_record_structure.py
+++ b/tests/test_docs_browser_record_structure.py

```


## README Entries

### traktor_nml/README.md

traktor_nml/README.md is the decision-log authority and carries one statement per decision for DL-198 through DL-212, continuing from the DL-197 high-water mark. DL-198 records that the header band is settled by Specs.dc.html and untouched here, and that the four page-3 artboards were the screens fixed to it. DL-199 records the four-step rail as a page element whose rules theme.py owns. DL-200 rewrites DL-172's entry: the reconstruct page is inside the structural gate, read against the four page-3 artboards, the exemption struck rather than restated. DL-201 records that the reconstruct page's column model, table geometry and detail rail carry no entry under 'Composition not built', because gui/ composes all three on /, and that the three entries read against the reconnect wizard's artboards stand, each narrowed to name that route and its artboard; DL-191's statement is revised in the same edit, since the ground it gives - that theme.py emits no two-column rule, no grid table and no rail - is one this work falsifies. Nothing is struck, so DL-190's post-strike trigger does not fire and no milestone here owes a post-strike record. DL-202 through DL-208 record the step mechanism, reconstruct_steps.py, the single resolve gate, the keymap routing, the grid, the split and rail, and steps 1, 2 and 4 holding the content the page composes. DL-209 records the fail-first mutation and its verbatim output in every guard docstring. DL-210 records that a milestone composing no page takes no served-page record and its rules are read in the record of the milestone that first composes them. DL-211 records the served-page record each composing milestone closes on. DL-212 records that all of these statements land in one commit and that the citations M-001 and M-002 carry are forward references until it does. The file is LF.

### traktor_nml/gui/README.md

gui/README.md's module table names reconstruct_steps.py - the four-step table, the rail records and the reachability predicate, nicegui-free like navigation.py and conflict_model.py - and states that / drives plain step regions from that table while /reconnect drives a ui.stepper. The section on what the guards can and cannot see states that the step rail's rendered position, the conflict grid's resolved column widths and the detail rail's resolved width are readable only on a served page, so they belong to the docs/ record rather than to any guard.

## Execution Waves

- W-001: M-001
- W-002: M-002
- W-003: M-003

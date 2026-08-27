# Plan

## Overview

A Traktor collection whose files have moved leaves every playlist referencing it unplayable. The two Phase 1 subcommands, scan-reconnect-candidates and rewrite-from-reconnect, already repair it from a terminal, and reconnect_run.py returns objects rather than printing so a review surface can sit beside the CLI renderer. Two things stand between that and the wizard the design set describes. First, the data an operator adjudicates does not survive the pipeline: ambiguity_rows carry four strings per unresolved record, refuted is a bare count on stats, and match_records discards the per-record candidate buckets and the refutation verdicts it computed, so accepting an alternative candidate, filtering to Refuted or Re-encoded, and showing a candidate-comparison panel are all inexpressible. Second, rewrite_from_reconnect runs the whole reconnection inside plan_and_write_nml's callback, so scan-review-write through that entry point re-runs a twenty-minute scan and discards the operator's decisions.

**Approach**: A default-None per-record review channel through match_records, resolve_reconnection and run_reconnection, and a shared write core both write paths run through. The channel is the shape this repository has used three times: on_progress, cancel and on_diagnostic all default to None and inert, and DL-056 records the reason it had to be additive rather than a signature change, that index_scan_roots has a second production caller, discover_tracks_cmd.py, with no manifest case. The same reasoning holds here and is made explicit: match_records is reached from tracklist.resolve_tracklist through buildplaylist for build-playlist, which has no manifest case among the twelve, so only default-inertness keeps it byte-identical by construction rather than by coverage. resolve_reconnection is by contrast fully pinned, its only production caller being run_reconnection under the two reconnect commands. Matching behaviour, refutation and the confidence ladder produce identical results because with on_review left at None no review object is constructed at all and the cascade runs the code it runs today; the unregenerated parity manifest is the proof. On the write side, write_reconnect_result holds the whole path and takes provide_result, a callable returning the ReconnectResult, so rewrite_from_reconnect is one call to it with run_reconnection as the provider and the wizard is one call with a provider returning the result it already reviewed. Parameterising by a provider rather than by a finished result is what keeps the output-collision refusal first: it is still the first statement of plan_and_write_nml, ahead of parsing and ahead of the callback the provider is called from, so a refused write never costs a scan. Section 3.3's zero-override byte-identity then holds structurally, since the two writes differ only in which provider ran. ScanCancelled is caught nowhere on either path.

### Reconnect wizard: review channel and shared write core

[Diagram pending Technical Writer rendering: DIAG-001]

## Planning Context

### Decision Log

Continues the package sequence at DL-058; DL-001 through DL-057 are committed entries of `traktor_nml/README.md`, not entries of this plan.

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-058 | The per-record review channel is a default-None on_review keyword on match_records, forwarded verbatim by resolve_reconnection and run_reconnection, in the shape on_progress/cancel/on_diagnostic already established | match_records has a production caller with no oracle case: tracklist.resolve_tracklist reaches it from buildplaylist for build-playlist, and the twelve manifest cases pin inspect, encode-dir, preview-diff, preview-compare, scan-compare-candidates, rewrite, rewrite-from-collection-compare and the two reconnect commands, not build-playlist -> a required parameter would leave that caller changed with nothing pinning its bytes, so its stability would rest on coverage -> a default-None keyword leaves every call site byte-identical by construction, which is the argument DL-056 makes verbatim for the second caller of index_scan_roots, discover_tracks_cmd.py |
| DL-059 | Reviews are emitted from inside the per-record cascade loop of match_records rather than re-derived by a second pass over the candidate indexes | the cascade loop already computes each record tier bucket, the current-Sync-copy preference, the refutation filter and the single-size-agreement tiebreak -> a re-derivation pass outside it would be a second implementation of exactly the candidate selection that decides matches -> the two would drift with no oracle noticing, which is the drift DL-055 routes the refutation-disabled message through one helper to make impossible |
| DL-060 | The size and duration contradiction rule has one definition: _refutation_reason(old_claims, candidate) returns a RefutationDetail or None, and _claims_refute is that call compared against None | the Refuted detail panel names the contradicting field and quantifies it against its allowance, so the display needs the same arithmetic the filter uses -> a separate display-only computation would be a second copy of tolerances calibrated against one real collection and would drift from the copy that decides refusals -> delegation keeps one definition, and because the detail object is constructed only where the boolean form returned True, the common non-refuting path allocates exactly the _Claims it allocates today |
| DL-061 | run_reconnection takes reviews as an optional caller-owned list it appends into, and populates ReconnectResult.reviews from it; when omitted no collector is installed and no review object is constructed | diagnostics already uses this exact shape so lines collected before a later VolumeIdentityError or _FingerprintUnavailable raise survive in the scope of the caller -> reusing the shape gives reviews the same survival property and the same reading for anyone who knows one of them -> and the omitted case installs no callback at all, so the CLI path runs the cascade with on_review None and allocates nothing, which is what makes matching results identical by construction rather than by measurement |
| DL-062 | The destination_collision status is overlaid on the reviews by resolve_reconnection after enforce_one_to_one, not emitted by match_records | the module docstring of reconnect.py states that match_records is unaware a one-to-one guarantee is layered on its plain old-to-new mapping -> emitting a collision status from inside the matcher would push a post-pass concept down into it and make the matcher wrong about records it matched correctly -> resolve_reconnection already holds collided_keys and already walks every unmatched record to build ambiguity_rows, so the reclassification happens in that same walk, where the reason already lives |
| DL-063 | Re-encoded is derived in traktor_nml/gui/review_model.py from an emitted review, not carried as a matcher status | matching has no notion of a format change: _FORMAT_SUFFIX strips the container so bare_name_in_folder, filename and bare_name key a stem, and a stem upgrade matches those tiers exactly like any other move -> calling the outcome re-encoded is a comparison of the suffix on the old record against the suffix on the winner, which is a presentation question about a match the matcher already made -> deriving it above the core keeps the result of the matcher identical and puts all six Specs statuses in one module |
| DL-064 | The four displayed confidence tokens (Strong, Good, Weak, None) map from the tier that produced a candidate, held as a table in traktor_nml/gui/review_model.py, and are not MatchConfidence values | Specs.dc.html names four tokens including normal while MatchConfidence has three members, STRICT, LOOSE and FILENAME, and is a run-wide ladder gating which tiers may fire rather than a per-candidate judgement -> reusing it as the row token would print the same word on every row of a run and would read Weak for a strict match found during a loose run -> the token is derived per candidate from the key_name on the review, which is already the tier that produced it |
| DL-065 | write_reconnect_result(args, provide_result, on_progress, cancel) is parameterised by a result provider called from inside the callback of plan_and_write_nml, not by an already-computed ReconnectResult | plan_and_write_nml resolves the output collision as its first statement, ahead of parsing and ahead of either callback, which is what makes a refused write cost nothing rather than a twenty-minute scan (DL-049) -> a signature taking a finished result would force every caller to run its scan before that refusal could be reached, moving the cost back in front of the check -> a provider invoked inside the callback keeps the refusal first for both callers, with rewrite-from-reconnect supplying run_reconnection and the wizard supplying a provider that returns the reviewed result it already holds |
| DL-066 | rewrite_from_reconnect is one call to write_reconnect_result, so both write paths share a single implementation of patch collection, CSV export, holder population and typed-error mapping | section 3.3 names zero-override byte-identity the strongest property in the plan -> proving it only by test leaves the two paths free to diverge in every commit between test runs -> with one implementation the wizard write and the CLI write differ solely in which provider ran, so identical bytes follow from the provider returning the same result object; the three unregenerated rewrite-from-reconnect manifest cases (dry-run, plain, and the --csv case) are what proves the factoring itself changed nothing |
| DL-067 | output_collision_refusal(input_path, output_path, extra_inputs) is the single definition of the collision rule: the first statement of plan_and_write_nml returns a WriteOutcome built from it, and the wizard calls it to decide whether the Write control is enabled and what reason it shows | section 4 requires the collision to disable writing with an inline reason rather than surface as a failure after the operator committed -> a wizard-side re-implementation of resolve-and-compare-against-every-input would be a second copy of a safety rule, drifting silently the moment extra_inputs grows a member -> one predicate with two callers keeps the disabled-button reason literally the string the CLI prints, while the exit-code-2 mapping stays in the renderer where DL-053 put it |
| DL-068 | ScanCancelled is caught nowhere on the wizard path: it escapes the provider, escapes plan_and_write_nml, escapes write_reconnect_result and reaches the io_bound worker, which surfaces a CANCELLED phase carrying no ReconnectResult | DL-053 records why a cancelled scan yields no result at all, that a short candidate list is indistinguishable from a complete one and would report most of the collection as missing -> a wizard that caught it to show partial rows would deliver exactly that confident wrong answer, and a review table is a more persuasive way to deliver it than a stats line -> the exception crosses every new function untouched, and a guard test cancels mid-write and asserts both that no ReconnectResult reached the caller and that no output .nml exists |
| DL-069 | Every rule worth testing lives in nicegui-free modules (review_model.py, wizard_state.py); traktor_nml/gui/app.py, file_picker.py and __main__.py are the only modules importing nicegui or pywebview | the suite runs on the system interpreter, which has no nicegui, while .venv has nicegui 3.16.0 and no pytest -> a test importing nicegui would error outright, or add a fourth skip through importorskip, and either breaks the floor of at least 243 passed and at most 3 skipped -> the decision rules sit below the view boundary where the suite can reach them, and a guard test walks the AST of traktor_nml/gui/ and asserts the set of nicegui-importing modules is exactly those three |
| DL-070 | traktor_nml.gui is listed in the packages array of pyproject.toml alongside traktor_nml and traktor_nml.commands | [tool.setuptools] packages is an explicit two-entry list rather than automatic discovery -> a package absent from that list imports fine from a source checkout and is missing from an installed wheel -> the failure appears only once something packages the tool, which is precisely the PyInstaller path the section 6 spike validated, so the omission would be found late and far from its cause |
| DL-071 | design/reconnect-wizard/Specs.dc.html is read as a committed primary source; conflicts among the design files follow the precedence rule in design/reconnect-wizard/README.md, which fixes Specs first | .gitignore excludes only /design/*/reconnect-wizard.html and git ls-files lists every .dc.html plus canvas.json as tracked -> the .dc.html files are the artboard sources the 2.3 MB bundle is seeded from, so Specs.dc.html is authored material and the bundle is the artifact -> it carries the same weight as docs/nicegui-gui-analysis.md, and its own README rule (a screen disagreeing with Specs is fixed in Specs, not in the screen) governs disagreements inside the design set |
| DL-072 | Where Specs.dc.html and docs/nicegui-gui-analysis.md sections 1 to 5 disagree, Specs governs status taxonomy and the keyboard map and section 4 governs framework mechanics; both disagreements are recorded in traktor_nml/gui/CLAUDE.md rather than resolved silently | the NiceGUI mapping in section 4 names three review buckets, matched, ambiguous and dangling, against the six statuses and seven filter chips of Specs, and names ui.aggrid with row selection against a keyboard contract in Specs that binds digits 1 to 9 to candidate picking, A/R/U to decisions and Shift-arrow to range selection -> preferring one silently would leave a reader of the other unable to tell whether the difference was decided or overlooked -> Specs wins on what the operator sees and presses because it is the later document and the one written as a cross-screen contract, section 4 wins on run.io_bound, ui.log and the local_file_picker component because Specs names no framework at all, and the split is written down where the next reader of either document will find it |
| DL-073 | The tier contradiction in section 1 is taken as already resolved by tests/test_gui_command_classification.py and is not re-derived; no third classification of scan-reconnect-candidates exists | section 1 says each subcommand appears in exactly one tier list and also says scan-reconnect-candidates appears in both tiers by design -> that module already resolves it by splitting primary tier assignment from Tier 2 eligibility, records the contradiction in its own docstring, and checks both predicates against the real build_parser choices -> a second resolution reached independently would be a fork of a rule that already has one home, so the wizard reads the dual membership as settled and Phase 1 introduces no form generator that would need the eligibility set at all |
| DL-074 | Accepting an alternative candidate routes through _reencode_winning_locations rather than writing the raw candidate LOCATION | a disk-scan candidate carries a placeholder LocationParts with no real VOLUME or VOLUMEID, and _reencode_winning_locations rewrites every winner using the volume identity resolved once per run for its scan root -> a candidate promoted to winner after that pass would reach the write path still carrying the placeholder, producing a LOCATION Traktor cannot resolve -> the accept path re-runs the same function over the amended mapping, which is idempotent because it recomputes each entry from source_path, and a guard test accepts an alternative and asserts the written LOCATION carries the resolved VOLUME and VOLUMEID |
| DL-075 | The wizard imports and drives run_reconnection and the two reconnect cores directly and renders its own view from ReconnectResult; subprocess-scraping the CLI key=value transcript was evaluated as the data source, rejected for Tier 1, and survives only as the section 5 fallback | Tier 1 needs structured data while the run is still open - a live scan progress feed and an ambiguous-match table the operator acts on mid-run - and a parsed key=value transcript exists only after the process has exited -> a scraping wizard could build its review table only after the decision point the table exists to serve, and would have no live object to cancel or to feed ui.log from -> so the cores are called in-process and ui.log is fed from the renderer's line-producing functions over RenderedOutput rather than from parsed stdout, while docs/nicegui-gui-analysis.md section 5 keeps scraping as the fallback rung if in-process integration fails, which is why this is recorded as a rejection of the data source and not of the technique |
| DL-076 | The wizard's provider returns a ReconnectResult built by wizard_state.amended_result(result, decisions), which replaces only mapping; stats, ambiguity_rows, old_records, reviews, warnings and diagnostics are carried through unchanged as the scan's own record, and the wizard renders override counts from the decision set in a separate panel beside them | write_reconnect_result takes a provider returning a whole frozen ReconnectResult while wizard_state.apply produces only a mapping, so some function must own the gap and no code_intent in M-003, M-004 or M-005 does -> re-deriving stats and ambiguity_rows from an amended mapping would change what those fields mean, since ambiguity_rows records which records the matcher found ambiguous and no operator decision changes what the matcher found, so a recount would silently redefine a CSV that also ships from the CLI -> carrying the scan's counts through unchanged keeps one meaning for those fields on both paths, and rendering the override counts separately makes the divergence an operator sees explicit rather than hidden inside a merged number; the ambiguity CSV and the stats block, both written even under --dry-run because neither is the command's declared output, therefore stay the scan's own record rather than a half-updated hybrid |
| DL-077 | The fingerprint control's enabled state comes from wizard_state.fingerprint_control_state(), which mirrors the core's two-step in the core's order: fingerprint_key_provider is None disables the control with the not-installed reason and the probe is not called at all; only when the provider is not None is fingerprint_unavailable_reason() called and a non-None return used as the reason | traktor_nml/reconnect_run.py binds both names to None in one except ImportError block (:48-53), and the pipeline tests fingerprint_key_provider is None and raises _FingerprintUnavailable before it ever reaches unavailable = fingerprint_unavailable_reason() (:181-185) -> calling the probe unconditionally raises TypeError: 'NoneType' object is not callable on exactly the machines the tier is unavailable on, which is the condition producing this project's three expected skips, so the setup screen would fail to render where the wizard most needs to degrade -> putting the two-step in a plain function rather than inside the view gives the deliberately untested view a tested source of truth, and keeps the two failure modes distinct in the GUI - provider-is-None against probe-returns-a-reason, a distinction that lives in the _FingerprintUnavailable docstring and the comment at traktor_nml/reconnect_run.py:183-193 rather than in any decision entry, which is why this entry states it |

### Rejected Alternatives

| Alternative | Why Rejected |
|---|---|
| Subprocess-scraping the CLI key=value stdout as the GUI's data source: the wizard shells out to scan-reconnect-candidates and rewrite-from-reconnect and parses the emitted key=value transcript instead of importing the cores | REJECTED AS THE PRIMARY ARCHITECTURE, RETAINED AS THE SECTION 5 FALLBACK - not a flat rejection. Tier 1 needs structured data mid-run: a live scan progress feed and an interactive ambiguous-match table the operator acts on while the run is still open -> a parsed key=value transcript exists only once the process has exited, so the review table could only ever be built after the decision point it exists to serve, and cancel would have no live object to cancel into -> the wizard therefore drives run_reconnection and the two cores in-process and renders its own view from ReconnectResult, feeding ui.log from the renderer's line-producing functions over RenderedOutput rather than from parsed stdout. It is not wrong, only unfit as the data source: docs/nicegui-gui-analysis.md section 5 keeps subprocess-scraping as the fallback rung of the rollout ladder if in-process GUI integration fails, and it remains a correct way to obtain the same numbers after a run. Routed to committed documents by CI-M-006-001 (traktor_nml/README.md, DL-075) and CI-M-006-003 (traktor_nml/gui/CLAUDE.md), because plan.json is planner scratch and the concrete failure this prevents is a maintainer wiring ui.log from parsed CLI output instead of from RenderedOutput (ref: DL-075) |
| nicegui.run.cpu_bound for the disk scan instead of run.io_bound | run.cpu_bound dispatches into a process pool, which requires the callable and its arguments to pickle -> TagCache and the lxml roots the scan holds are not cleanly picklable, so the scan would fail at the pool boundary rather than in code anyone could read -> run.io_bound keeps the scan in a thread against the same objects, and the scan is I/O bound in any case. Carried as a plan constraint and by the section 4 half of the DL-072 precedence split (ref: DL-072) |
| ui.upload for choosing scan roots | ui.upload is a browser file upload, which transfers file contents to the server -> scan roots are server-side directory trees that must be walked in place, and a directory cannot be uploaded at all -> file selection goes through pywebview's create_file_dialog in native mode and NiceGUI's local_file_picker component otherwise, which section 4 already names as the known friction point to budget for. Carried by CI-M-005-002 (ref: DL-071) |
| Placing the GUI modules under traktor_nml/commands/ | commands/__init__.py imports every command module at CLI startup, before argv is parsed -> a GUI module living there would put a nicegui import on the path of every CLI invocation, breaking the optional-extra contract tests/test_cli_without_nicegui.py enforces -> the GUI lives in its own traktor_nml/gui/ package, with the import direction guarded one way by tests/test_gui_import_isolation.py. Carried by invisible_knowledge.structure_rationale (ref: DL-069) |

### Constraints

- Suite runs on system python3 which has no nicegui; .venv has nicegui but no pytest. New tests must import no nicegui or the 243-passed/3-skipped floor breaks.
- pyproject [tool.setuptools] packages is an explicit list; traktor_nml.gui must be added to it.
- Decision log high-water mark is DL-057; plan ids start at DL-058.
- tests/baselines/manifest.json and PARITY_BASELINE_SHA256 in tests/test_parity_baseline.py are unmodified. Non-regeneration IS the parity check, and it is the proof for both the review channel and the write-path factoring.
- stdout, stderr, exit codes and written output bytes stay byte-identical for every existing CLI command; typed errors keep exit code 2.
- Matching behaviour, refutation and the confidence ladder produce identical results. The channel makes this structurally true by constructing nothing when no collector is supplied, rather than testing that it happens to hold.
- No import from traktor_nml/gui/ in traktor_nml/commands/ or traktor_nml/cli.py, and no top-level nicegui import reachable from commands/__init__.py, which imports every command module before argv is parsed.
- The suite runs on the system interpreter, which has no nicegui; .venv has nicegui 3.16.0 and pywebview 6.2.1 but no pytest. A test importing nicegui would error or add a fourth skip, and either breaks the floor.
- pytest tests/ -q stays at or above 243 passed and at most 3 skipped, read off the summary line. The 3 skips are the fingerprint tier with pyacoustid and fpcalc absent. A silently lost or newly skipped test fails this as surely as a red one.
- Every guard constructs its broken scenario in executable code and demonstrates the divergence; the docstring records the specific mutation and the specific observed output. Prose-only proof claims and tautological controls whose mock decides the outcome have both been caught and rejected in this project.
- Documentation describes the code as it stands: no previously, used to, now does, no longer, as before, gains, moves or added. Largest finding category across this project, seven instances.
- A file is never restored with git checkout. Copy aside and restore from the copy.
- Nothing is deleted from or written into build/ or dist/, which hold untracked PyInstaller spike bundles.
- nicegui stays an optional extra; pyproject declares gui = ['nicegui>=3.16.0'] and its packages array is an explicit list that must name traktor_nml.gui.
- run.io_bound for the disk scan, never run.cpu_bound: cpu_bound uses a process pool and neither TagCache nor an lxml root is cleanly picklable.
- The tier contradiction in section 1 is not re-derived; tests/test_gui_command_classification.py already resolves it as two predicates and records the contradiction.

### Known Risks

- **Emitting a review per record over a 12,418-entry collection holds every candidate view in memory for the length of the session.**: Only the wizard supplies a collector, and it holds the reviews it is already rendering; the CLI path constructs none. A fixture-corpus run bounds the shape, and the real-corpus cost is the same order as the mapping the run already holds. (anchor: `traktor_nml/matching.py:match_records`; ref: DL-058)
- **A candidate promoted by the operator after run_reconnection has already re-encoded the winners reaches the write path carrying a scan placeholder LocationParts with no real VOLUME or VOLUMEID, producing a LOCATION Traktor cannot resolve.**: The accept path runs the amended mapping through _reencode_winning_locations, which recomputes each entry from source_path and is therefore idempotent; a guard accepts an alternative and asserts the written LOCATION carries the resolved VOLUME and VOLUMEID, with its negative control recording the placeholder that appears without the step. (anchor: `traktor_nml/reconnect_run.py:_reencode_winning_locations`; ref: DL-074)
- **Factoring the write path is the one change that touches bytes an existing command writes, so a mistake there is a silent regression in the only two commands that repair a collection.**: The three rewrite-from-reconnect manifest cases run unregenerated as the merge gate, and all twelve recorded stderr values are empty, which makes the stderr assertion a leak detector for every pinned path. (anchor: `traktor_nml/reconnect_run.py:write_reconnect_result`; ref: DL-066)
- **A test reaching nicegui, directly or through an import of traktor_nml.gui.app, turns the floor of 243 passed and 3 skipped into an error or a fourth skip, and the failure reads as unrelated.**: Every rule worth testing sits in nicegui-free modules and the boundary is itself guarded by an AST walk whose negative control adds a synthetic importing module and records the extra name reported. (anchor: `traktor_nml/gui/`; ref: DL-069)
- **Specs.dc.html and sections 1 to 5 of docs/nicegui-gui-analysis.md disagree on the review taxonomy, so building against one leaves a reader of the other unable to tell whether the difference was decided or overlooked.**: Both disagreements are named in traktor_nml/gui/CLAUDE.md with which document governs each and why, rather than one being silently preferred. (anchor: `traktor_nml/gui/CLAUDE.md`; ref: DL-072)

## Invisible Knowledge

### System

The reconnect path runs in three layers and the split exists so a review surface can sit beside the CLI renderer: reconnect_run.py owns the pipeline and returns objects, reconnect_render.py owns every character reaching a stream through a single emit helper, and commands/reconnect_cmd.py owns only argparse. The wizard drives the cores and renders its own view, taking the RenderedOutput stdout_lines and stderr_lines for its log rather than routing through emit. Everything the test suite can reach lives below the framework boundary, because the suite runs on an interpreter that has no nicegui while the interpreter that has nicegui has no pytest.

### Invariants

- With on_review left at None, match_records constructs no review object and returns the same mapping, stats and samples for every call site, which is what leaves build-playlist byte-identical without a manifest case pinning it.
- The output-collision refusal is the first statement of plan_and_write_nml, ahead of reading, parsing and both caller callbacks, so a refused write costs nothing (DL-049), and it reaches a caller as a typed refusal rather than an exit code.
- ScanCancelled escapes every function on the core and write path with no result at all, because a short candidate list is indistinguishable from a complete one and would report most of the collection as missing (DL-053).
- The size and duration contradiction rule has exactly one definition, and the number the Refuted panel quantifies against is the allowance that rule used.
- Volume identities are resolved once per run and reused by the fingerprint tier and the LOCATION re-encoding; a candidate promoted after that pass is re-encoded through the same function rather than written with its scan placeholder.
- The tag cache and the ambiguity CSV are written on every run regardless of dry-run, because neither is the command's declared output; a preview writes nothing else anywhere.
- stderr order is scan diagnostics, then the fingerprint dependency warning, then the refutation-disabled line, then any error; stdout order for rewrite-from-reconnect is csv_written, then the stats and sample_matches block, then output_written.
- Each decision in traktor_nml/README.md is stated once, in the section describing what it decides, so a second copy would drift.
- DL-001 through DL-057 are committed entries of traktor_nml/README.md's decision log, not entries of this plan; DL-058 onward extend that same log and same numbering, which is why this plan's decision_refs resolve into two places - anything at or below DL-057 is read in the README, anything above it is defined here and reaches the README at M-006.

### Tradeoffs

- Emitting reviews allocates per-record objects over a collection that can hold 12,418 entries. Accepted because the allocation happens only when a caller supplies a collector, so the cost lands on the one surface that needs the data and never on the CLI.
- write_reconnect_result takes a provider rather than a result, which reads less directly than a function handed the thing it writes. Accepted because the direct signature would move a twenty-minute scan in front of the refusal that exists to avoid paying it.
- The six statuses and the four confidence tokens are derived above the core rather than carried on the result. Accepted because both are questions about how a match is described rather than which match was made, and deriving them keeps matching results identical.
- Phase 1 ships no pytest harness driving rendered DOM, so app.py is verified by boundary and source checks rather than by interaction tests. Accepted because section 3.3's criteria are expressed against the cores and the write path, and adding a browser harness would put nicegui on the suite's import path.

## Milestones

### Milestone 1: Review channel through the matcher

**Files**: traktor_nml/review.py, traktor_nml/matching.py, traktor_nml/reconnect.py, tests/test_review_channel.py

**Requirements**:

- match_records accepts on_review and emits one RecordReview per old record when it is supplied; a RecordReview carries the old record; its status; its ordered candidate views (each with the tier that produced it; whether refutation removed it; and the RefutationDetail when it did); and the chosen candidate when one exists;resolve_reconnection forwards on_review and reclassifies the reviews of collided keys to destination_collision in the same walk that builds ambiguity_rows;the refutation rule has one definition and both the boolean filter and the detail come from it;with on_review left at None the mapping; stats and ambiguity_rows of every existing call site are identical values

**Acceptance Criteria**:

- pytest tests/ -q reports at least 243 passed and at most 3 skipped;tests/baselines/manifest.json and PARITY_BASELINE_SHA256 are unmodified and tests/test_baseline_parity.py passes;a run with on_review set and the same run with it left at None produce equal mapping; equal stats and equal ambiguity_rows;every review emitted for a fixture-corpus run carries a status drawn from the five matcher statuses and no record appears twice;a refuted record carries a RefutationDetail naming the contradicting field; both values; the difference and the allowance that was exceeded

**Tests**:

- tests/test_review_channel.py

#### Code Intent

- **CI-M-001-001** `traktor_nml/review.py::module`: Frozen dataclasses describing one record's matching outcome, importing only from model.py so nothing above the matcher is needed to read them. RefutationDetail holds field (duration or size), the old value, the candidate value, their difference and the allowance that was exceeded, in the units the arithmetic used. CandidateView holds the candidate EntryRecord, the tier key_name whose bucket produced it, refuted as a bool, and detail as a RefutationDetail or None. RecordReview holds the old EntryRecord, status as one of matched, ambiguous, refuted, unmatched or destination_collision, candidates as a tuple of CandidateView in the order the cascade considered them, chosen as the winning EntryRecord or None, and matched_by as the winning tier name or None. The five statuses are exactly the outcomes the matcher and the one-to-one post-pass produce; the two operator statuses Specs names, rejected and left-missing, are absent because no code below the wizard can know them. (refs: DL-058, DL-062, DL-063)
- **CI-M-001-002** `traktor_nml/matching.py::_refutation_reason`: The whole size-and-duration contradiction rule, returning a RefutationDetail when the candidate is contradicted and None otherwise. Every early return that _claims_refute reaches with False returns None here, so the non-refuting path allocates nothing beyond the _Claims it already builds; the detail object is constructed only on the path that reports a contradiction. Same-source size disagreement beyond _SIZE_REL_TOLERANCE yields a size detail; duration disagreement beyond the allowance (absolute, widened to the cross-source relative band when exactly one side is disk-derived) yields a duration detail carrying that allowance, which is the number the Refuted panel quantifies against. (refs: DL-060)
- **CI-M-001-003** `traktor_nml/matching.py::_claims_refute`: Returns whether _refutation_reason found a contradiction, so the filter inside the cascade and the detail beside the row are the same rule read twice rather than two implementations of one tolerance table. (refs: DL-060)
- **CI-M-001-004** `traktor_nml/matching.py::match_records`: An on_review keyword defaulting to None. When it is None the per-record loop runs exactly as it does without the parameter: no CandidateView is built, no tuple is assembled, and the mapping, stats and samples are the same objects for every call site, which is what leaves build-playlist byte-identical without a manifest case to pin it. When it is supplied, each iteration records the candidates each consulted tier offered after _prefer_current_sync_copy and before the refutation filter, marks the ones _refutation_reason removed and attaches their detail, and calls on_review once per old record with a RecordReview whose status is the branch that iteration took: matched with chosen and matched_by set, ambiguous where a bucket held more than one survivor or a provider reported AMBIGUOUS, refuted where the record ended unmatched with at least one candidate withdrawn, and unmatched otherwise. The call happens after the branch is decided, so the status a review carries is the branch that produced the record's stats entry rather than a re-derivation of it. (refs: DL-058, DL-059)
- **CI-M-001-005** `traktor_nml/reconnect.py::resolve_reconnection`: An on_review keyword defaulting to None, forwarded to match_records. When it is supplied, reviews are collected into a local list rather than handed straight out, because the one-to-one post-pass is not finished at the point match_records emits them: after enforce_one_to_one returns collided_keys, the walk that already builds ambiguity_rows for every record outside final_mapping replaces the review of each collided key with one whose status is destination_collision, then calls on_review for every review in the order match_records produced them. A record the matcher called matched and the post-pass withdrew therefore reaches the caller as destination_collision, which is the reason the ambiguity CSV records for it, and match_records stays unaware that a one-to-one guarantee sits above it. (refs: DL-058, DL-062)
- **CI-M-001-006** `tests/test_review_channel.py::module`: Guards for the channel, each constructing its broken scenario in executable code and recording in its docstring the mutation made and the output observed under it. Inertness: a fixture-corpus resolve_reconnection run with on_review omitted and the same run with a recording collector produce equal mapping, equal stats and equal ambiguity_rows; the negative control removes the guard against building candidate views when on_review is None and records the resulting divergence. Status coverage: over the fixture corpus every old record appears in exactly one review and every status a review carries agrees with the stats bucket that record fell into; the negative control mutates one record's emitted status and records the mismatch the checker reports. Refutation detail: a record whose candidate differs in duration beyond the allowance carries a duration RefutationDetail whose difference and allowance reproduce the numbers _refutation_reason used; the negative control widens the tolerance constant so the same pair no longer refutes and records that the review arrives as unmatched with no detail. Collision overlay: two old records constructed to claim one candidate arrive as destination_collision rather than matched; the negative control skips the overlay and records that both arrive as matched while the ambiguity CSV calls them destination_collision, the exact disagreement the overlay exists to prevent. (refs: DL-058, DL-059, DL-060, DL-062)

#### Code Changes

**CC-M-001-001** (traktor_nml/review.py) - implements CI-M-001-001

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/review.py
@@ -0,0 +1,66 @@
+"""Per-record review data: what the matcher considered for one old record.
+
+Imports only from model.py so nothing above the matcher - reconnect.py,
+reconnect_run.py, a future review surface - is needed to read a
+RecordReview back. match_records builds these only when a caller supplies
+on_review; with it left at None nothing here is constructed at all.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Optional
+
+from .model import EntryRecord
+
+
+@dataclass(frozen=True)
+class RefutationDetail:
+    """The size or duration contradiction that removed one candidate.
+
+    field, old and candidate carry the values _refutation_reason compared;
+    difference and allowance are the same two numbers the comparison used,
+    in the units that arithmetic used (kilobytes for size, seconds for
+    duration), so a caller displaying this detail quantifies it against
+    the same allowance that removed the candidate rather than a second
+    computation of it.
+    """
+
+    field: str  # "duration" or "size"
+    old_value: float
+    candidate_value: float
+    difference: float
+    allowance: float
+
+
+@dataclass(frozen=True)
+class CandidateView:
+    """One candidate a tier offered for an old record, before or after
+    refutation removed it."""
+
+    candidate: EntryRecord
+    key_name: str
+    refuted: bool
+    detail: Optional[RefutationDetail] = None
+
+
+@dataclass(frozen=True)
+class RecordReview:
+    """One old record's outcome: the status match_records (and, for
+    destination_collision, resolve_reconnection) assigned it, the
+    candidates considered in cascade order, and the winner when there was
+    one.
+
+    The five statuses are exactly the outcomes the matcher and the
+    one-to-one post-pass produce; the two operator statuses a review
+    surface may show, rejected and left-missing, are absent because no
+    code below that surface can know them - they name a decision an
+    operator makes, not an outcome the matcher or the collision pass
+    computed.
+    """
+
+    old: EntryRecord
+    status: str  # matched | ambiguous | refuted | unmatched | destination_collision
+    candidates: tuple[CandidateView, ...]
+    chosen: Optional[EntryRecord] = None
+    matched_by: Optional[str] = None
```

**CC-M-001-002** (traktor_nml/matching.py) - implements CI-M-001-002

**Code:**

```diff
diff --git a/traktor_nml/matching.py b/traktor_nml/matching.py
index ac6caff..440a470 100644
--- a/traktor_nml/matching.py
+++ b/traktor_nml/matching.py
@@ -18,6 +18,7 @@ from typing import Callable, Iterable, Optional
 
 from .confidence import MatchConfidence
 from .model import EntryRecord, record_label
+from .review import CandidateView, RecordReview, RefutationDetail
 
 @dataclass(frozen=True)
 class _TierSpec:
@@ -206,13 +207,18 @@ class _Claims:
         self.from_disk = record.source_path is not None
 
 
-def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
-    """True when duration positively contradicts the candidate.
+def _refutation_reason(old: _Claims, candidate: EntryRecord) -> Optional[RefutationDetail]:
+    """The size or duration contradiction that refutes the candidate, or
+    None when neither field contradicts it.
 
     Absent data never refutes: a candidate whose tags could not be read is
     left for the tier keys to judge rather than silently discarded. Size
     refutes only when both sides come from the same source; across sources
-    it is corroboration only, for the reasons set out below.
+    it is corroboration only, for the reasons set out below. The detail
+    object is built only on the path that reports a contradiction, so the
+    common non-refuting path allocates nothing beyond the _Claims already
+    built for it - every other branch below returns None rather than
+    constructing one.
     """
     new = _Claims(candidate)
     # Only when one side is disk-derived and the other is not do the two
@@ -246,8 +252,15 @@ def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
         #
         # Size still earns its keep as POSITIVE evidence - see
         # _size_agrees, which breaks ambiguity rather than creating it.
-        if abs(old_kb - new_kb) / max(old_kb, new_kb) > _SIZE_REL_TOLERANCE:
-            return True
+        size_diff = abs(old_kb - new_kb) / max(old_kb, new_kb)
+        if size_diff > _SIZE_REL_TOLERANCE:
+            return RefutationDetail(
+                field="size",
+                old_value=old_kb,
+                candidate_value=new_kb,
+                difference=abs(old_kb - new_kb),
+                allowance=_SIZE_REL_TOLERANCE * max(old_kb, new_kb),
+            )
 
     old_s, new_s = old.seconds, new.seconds
     if old_s is not None and new_s is not None:
@@ -256,10 +269,27 @@ def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
             # Relative, because mutagen's error on a headerless VBR file
             # scales with track length rather than being a fixed offset.
             allowance = max(allowance, _CROSS_DURATION_REL_TOLERANCE * max(old_s, new_s))
-        if abs(old_s - new_s) > allowance:
-            return True
+        duration_diff = abs(old_s - new_s)
+        if duration_diff > allowance:
+            return RefutationDetail(
+                field="duration",
+                old_value=old_s,
+                candidate_value=new_s,
+                difference=duration_diff,
+                allowance=allowance,
+            )
 
-    return False
+    return None
+
+
+def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
+    """True when duration positively contradicts the candidate.
+
+    The filter inside the cascade and the detail beside a review row are
+    the same tolerance table read twice, not two implementations of it:
+    this is _refutation_reason compared against None.
+    """
+    return _refutation_reason(old, candidate) is not None
 
 
 def _size_agrees(old: _Claims, candidate: EntryRecord) -> bool:
@@ -493,6 +523,7 @@ def match_records(
     key_providers: Iterable[KeyProvider] = (),
     indexes: dict[str, dict[tuple[str, ...], list[EntryRecord]]] | None = None,
     refute: bool = True,
+    on_review: Optional[Callable[[RecordReview], None]] = None,
 ) -> tuple[dict[str, EntryRecord], dict[str, int], list[tuple[str, str, str, str]]]:
     """refute=False disables the size/duration contradiction filter.
 
@@ -500,7 +531,18 @@ def match_records(
     library that breaks an assumption behind them loses correct candidates
     with no way to overrule it from outside this module. That is what the
     switch is for; it is not a general-purpose knob, and the default stays
-    on because a contradiction is usually real."""
+    on because a contradiction is usually real.
+
+    on_review defaults to None, in the shape on_progress/cancel/diagnostics
+    already use elsewhere in this project: with it left at None the loop
+    below builds no CandidateView and calls nothing, so match_records
+    returns the same mapping, stats and samples for every call site
+    regardless of whether that site knows this parameter exists - which is
+    what leaves tracklist.resolve_tracklist's build-playlist caller, which
+    has no manifest case pinning it, byte-identical by construction rather
+    than by coverage. When supplied, on_review is called once per old
+    record with a RecordReview built from the same branch that already
+    decided that record's stats bucket."""
     # A caller that already built the candidate index for its own purposes
     # (e.g. reconnection's post-match ambiguity check) can pass it in so the
     # O(candidates) index build never runs twice for one match_records call.
@@ -544,6 +586,11 @@ def match_records(
         matched_by: str | None = None
         ambiguous_here = False
         refuted_here = False
+        # Built only when a caller opted in: the review a 12,418-entry
+        # collection would hold in memory for every record is a cost that
+        # must land on the one surface asking for it, never on a call site
+        # that supplied nothing.
+        record_candidates: list[CandidateView] | None = [] if on_review is not None else None
 
         for key_name, key_value in record_keys(old_record, confidence, key_providers):
             if key_value is AMBIGUOUS:
@@ -568,10 +615,27 @@ def match_records(
                 # removes a candidate, so a tier with one plausible and one
                 # implausible hit resolves cleanly instead of reporting a
                 # false ambiguity the operator would have to adjudicate.
-                kept = [c for c in candidates if not _claims_refute(old_claims, c)]
+                if record_candidates is not None:
+                    # Same rule read twice (DL-060): the detail beside a
+                    # review row and the boolean that filters here both come
+                    # from _refutation_reason, so the two can never disagree
+                    # about which candidate was removed or why.
+                    details = [_refutation_reason(old_claims, c) for c in candidates]
+                    record_candidates.extend(
+                        CandidateView(candidate=c, key_name=key_name, refuted=d is not None, detail=d)
+                        for c, d in zip(candidates, details)
+                    )
+                    kept = [c for c, d in zip(candidates, details) if d is None]
+                else:
+                    kept = [c for c in candidates if not _claims_refute(old_claims, c)]
                 if len(kept) != len(candidates):
                     refuted_here = True
                 candidates = kept
+            elif record_candidates is not None:
+                record_candidates.extend(
+                    CandidateView(candidate=c, key_name=key_name, refuted=False, detail=None)
+                    for c in candidates
+                )
             if len(candidates) > 1:
                 # Size as POSITIVE evidence, the only role it has across
                 # sources: when a tier cannot separate its candidates on its
@@ -613,4 +677,27 @@ def match_records(
             if refuted_here:
                 stats["refuted"] += 1
 
+        if on_review is not None:
+            # Read off the same branch that just decided this record's stats
+            # bucket, rather than re-derived from the candidate list, so the
+            # status a review carries can never disagree with where the
+            # record actually landed.
+            if matched_new is not None and matched_by is not None:
+                status = "matched"
+            elif ambiguous_here:
+                status = "ambiguous"
+            elif refuted_here:
+                status = "refuted"
+            else:
+                status = "unmatched"
+            on_review(
+                RecordReview(
+                    old=old_record,
+                    status=status,
+                    candidates=tuple(record_candidates or ()),
+                    chosen=matched_new,
+                    matched_by=matched_by,
+                )
+            )
+
     return mapping, stats, samples
```

**CC-M-001-003** (traktor_nml/matching.py) - implements CI-M-001-003

**Code:**

```diff
diff --git a/traktor_nml/matching.py b/traktor_nml/matching.py
index ac6caff..440a470 100644
--- a/traktor_nml/matching.py
+++ b/traktor_nml/matching.py
@@ -18,6 +18,7 @@ from typing import Callable, Iterable, Optional
 
 from .confidence import MatchConfidence
 from .model import EntryRecord, record_label
+from .review import CandidateView, RecordReview, RefutationDetail
 
 @dataclass(frozen=True)
 class _TierSpec:
@@ -206,13 +207,18 @@ class _Claims:
         self.from_disk = record.source_path is not None
 
 
-def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
-    """True when duration positively contradicts the candidate.
+def _refutation_reason(old: _Claims, candidate: EntryRecord) -> Optional[RefutationDetail]:
+    """The size or duration contradiction that refutes the candidate, or
+    None when neither field contradicts it.
 
     Absent data never refutes: a candidate whose tags could not be read is
     left for the tier keys to judge rather than silently discarded. Size
     refutes only when both sides come from the same source; across sources
-    it is corroboration only, for the reasons set out below.
+    it is corroboration only, for the reasons set out below. The detail
+    object is built only on the path that reports a contradiction, so the
+    common non-refuting path allocates nothing beyond the _Claims already
+    built for it - every other branch below returns None rather than
+    constructing one.
     """
     new = _Claims(candidate)
     # Only when one side is disk-derived and the other is not do the two
@@ -246,8 +252,15 @@ def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
         #
         # Size still earns its keep as POSITIVE evidence - see
         # _size_agrees, which breaks ambiguity rather than creating it.
-        if abs(old_kb - new_kb) / max(old_kb, new_kb) > _SIZE_REL_TOLERANCE:
-            return True
+        size_diff = abs(old_kb - new_kb) / max(old_kb, new_kb)
+        if size_diff > _SIZE_REL_TOLERANCE:
+            return RefutationDetail(
+                field="size",
+                old_value=old_kb,
+                candidate_value=new_kb,
+                difference=abs(old_kb - new_kb),
+                allowance=_SIZE_REL_TOLERANCE * max(old_kb, new_kb),
+            )
 
     old_s, new_s = old.seconds, new.seconds
     if old_s is not None and new_s is not None:
@@ -256,10 +269,27 @@ def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
             # Relative, because mutagen's error on a headerless VBR file
             # scales with track length rather than being a fixed offset.
             allowance = max(allowance, _CROSS_DURATION_REL_TOLERANCE * max(old_s, new_s))
-        if abs(old_s - new_s) > allowance:
-            return True
+        duration_diff = abs(old_s - new_s)
+        if duration_diff > allowance:
+            return RefutationDetail(
+                field="duration",
+                old_value=old_s,
+                candidate_value=new_s,
+                difference=duration_diff,
+                allowance=allowance,
+            )
 
-    return False
+    return None
+
+
+def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
+    """True when duration positively contradicts the candidate.
+
+    The filter inside the cascade and the detail beside a review row are
+    the same tolerance table read twice, not two implementations of it:
+    this is _refutation_reason compared against None.
+    """
+    return _refutation_reason(old, candidate) is not None
 
 
 def _size_agrees(old: _Claims, candidate: EntryRecord) -> bool:
@@ -493,6 +523,7 @@ def match_records(
     key_providers: Iterable[KeyProvider] = (),
     indexes: dict[str, dict[tuple[str, ...], list[EntryRecord]]] | None = None,
     refute: bool = True,
+    on_review: Optional[Callable[[RecordReview], None]] = None,
 ) -> tuple[dict[str, EntryRecord], dict[str, int], list[tuple[str, str, str, str]]]:
     """refute=False disables the size/duration contradiction filter.
 
@@ -500,7 +531,18 @@ def match_records(
     library that breaks an assumption behind them loses correct candidates
     with no way to overrule it from outside this module. That is what the
     switch is for; it is not a general-purpose knob, and the default stays
-    on because a contradiction is usually real."""
+    on because a contradiction is usually real.
+
+    on_review defaults to None, in the shape on_progress/cancel/diagnostics
+    already use elsewhere in this project: with it left at None the loop
+    below builds no CandidateView and calls nothing, so match_records
+    returns the same mapping, stats and samples for every call site
+    regardless of whether that site knows this parameter exists - which is
+    what leaves tracklist.resolve_tracklist's build-playlist caller, which
+    has no manifest case pinning it, byte-identical by construction rather
+    than by coverage. When supplied, on_review is called once per old
+    record with a RecordReview built from the same branch that already
+    decided that record's stats bucket."""
     # A caller that already built the candidate index for its own purposes
     # (e.g. reconnection's post-match ambiguity check) can pass it in so the
     # O(candidates) index build never runs twice for one match_records call.
@@ -544,6 +586,11 @@ def match_records(
         matched_by: str | None = None
         ambiguous_here = False
         refuted_here = False
+        # Built only when a caller opted in: the review a 12,418-entry
+        # collection would hold in memory for every record is a cost that
+        # must land on the one surface asking for it, never on a call site
+        # that supplied nothing.
+        record_candidates: list[CandidateView] | None = [] if on_review is not None else None
 
         for key_name, key_value in record_keys(old_record, confidence, key_providers):
             if key_value is AMBIGUOUS:
@@ -568,10 +615,27 @@ def match_records(
                 # removes a candidate, so a tier with one plausible and one
                 # implausible hit resolves cleanly instead of reporting a
                 # false ambiguity the operator would have to adjudicate.
-                kept = [c for c in candidates if not _claims_refute(old_claims, c)]
+                if record_candidates is not None:
+                    # Same rule read twice (DL-060): the detail beside a
+                    # review row and the boolean that filters here both come
+                    # from _refutation_reason, so the two can never disagree
+                    # about which candidate was removed or why.
+                    details = [_refutation_reason(old_claims, c) for c in candidates]
+                    record_candidates.extend(
+                        CandidateView(candidate=c, key_name=key_name, refuted=d is not None, detail=d)
+                        for c, d in zip(candidates, details)
+                    )
+                    kept = [c for c, d in zip(candidates, details) if d is None]
+                else:
+                    kept = [c for c in candidates if not _claims_refute(old_claims, c)]
                 if len(kept) != len(candidates):
                     refuted_here = True
                 candidates = kept
+            elif record_candidates is not None:
+                record_candidates.extend(
+                    CandidateView(candidate=c, key_name=key_name, refuted=False, detail=None)
+                    for c in candidates
+                )
             if len(candidates) > 1:
                 # Size as POSITIVE evidence, the only role it has across
                 # sources: when a tier cannot separate its candidates on its
@@ -613,4 +677,27 @@ def match_records(
             if refuted_here:
                 stats["refuted"] += 1
 
+        if on_review is not None:
+            # Read off the same branch that just decided this record's stats
+            # bucket, rather than re-derived from the candidate list, so the
+            # status a review carries can never disagree with where the
+            # record actually landed.
+            if matched_new is not None and matched_by is not None:
+                status = "matched"
+            elif ambiguous_here:
+                status = "ambiguous"
+            elif refuted_here:
+                status = "refuted"
+            else:
+                status = "unmatched"
+            on_review(
+                RecordReview(
+                    old=old_record,
+                    status=status,
+                    candidates=tuple(record_candidates or ()),
+                    chosen=matched_new,
+                    matched_by=matched_by,
+                )
+            )
+
     return mapping, stats, samples
```

**CC-M-001-004** (traktor_nml/matching.py) - implements CI-M-001-004

**Code:**

```diff
diff --git a/traktor_nml/matching.py b/traktor_nml/matching.py
index ac6caff..440a470 100644
--- a/traktor_nml/matching.py
+++ b/traktor_nml/matching.py
@@ -18,6 +18,7 @@ from typing import Callable, Iterable, Optional
 
 from .confidence import MatchConfidence
 from .model import EntryRecord, record_label
+from .review import CandidateView, RecordReview, RefutationDetail
 
 @dataclass(frozen=True)
 class _TierSpec:
@@ -206,13 +207,18 @@ class _Claims:
         self.from_disk = record.source_path is not None
 
 
-def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
-    """True when duration positively contradicts the candidate.
+def _refutation_reason(old: _Claims, candidate: EntryRecord) -> Optional[RefutationDetail]:
+    """The size or duration contradiction that refutes the candidate, or
+    None when neither field contradicts it.
 
     Absent data never refutes: a candidate whose tags could not be read is
     left for the tier keys to judge rather than silently discarded. Size
     refutes only when both sides come from the same source; across sources
-    it is corroboration only, for the reasons set out below.
+    it is corroboration only, for the reasons set out below. The detail
+    object is built only on the path that reports a contradiction, so the
+    common non-refuting path allocates nothing beyond the _Claims already
+    built for it - every other branch below returns None rather than
+    constructing one.
     """
     new = _Claims(candidate)
     # Only when one side is disk-derived and the other is not do the two
@@ -246,8 +252,15 @@ def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
         #
         # Size still earns its keep as POSITIVE evidence - see
         # _size_agrees, which breaks ambiguity rather than creating it.
-        if abs(old_kb - new_kb) / max(old_kb, new_kb) > _SIZE_REL_TOLERANCE:
-            return True
+        size_diff = abs(old_kb - new_kb) / max(old_kb, new_kb)
+        if size_diff > _SIZE_REL_TOLERANCE:
+            return RefutationDetail(
+                field="size",
+                old_value=old_kb,
+                candidate_value=new_kb,
+                difference=abs(old_kb - new_kb),
+                allowance=_SIZE_REL_TOLERANCE * max(old_kb, new_kb),
+            )
 
     old_s, new_s = old.seconds, new.seconds
     if old_s is not None and new_s is not None:
@@ -256,10 +269,27 @@ def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
             # Relative, because mutagen's error on a headerless VBR file
             # scales with track length rather than being a fixed offset.
             allowance = max(allowance, _CROSS_DURATION_REL_TOLERANCE * max(old_s, new_s))
-        if abs(old_s - new_s) > allowance:
-            return True
+        duration_diff = abs(old_s - new_s)
+        if duration_diff > allowance:
+            return RefutationDetail(
+                field="duration",
+                old_value=old_s,
+                candidate_value=new_s,
+                difference=duration_diff,
+                allowance=allowance,
+            )
 
-    return False
+    return None
+
+
+def _claims_refute(old: _Claims, candidate: EntryRecord) -> bool:
+    """True when duration positively contradicts the candidate.
+
+    The filter inside the cascade and the detail beside a review row are
+    the same tolerance table read twice, not two implementations of it:
+    this is _refutation_reason compared against None.
+    """
+    return _refutation_reason(old, candidate) is not None
 
 
 def _size_agrees(old: _Claims, candidate: EntryRecord) -> bool:
@@ -493,6 +523,7 @@ def match_records(
     key_providers: Iterable[KeyProvider] = (),
     indexes: dict[str, dict[tuple[str, ...], list[EntryRecord]]] | None = None,
     refute: bool = True,
+    on_review: Optional[Callable[[RecordReview], None]] = None,
 ) -> tuple[dict[str, EntryRecord], dict[str, int], list[tuple[str, str, str, str]]]:
     """refute=False disables the size/duration contradiction filter.
 
@@ -500,7 +531,18 @@ def match_records(
     library that breaks an assumption behind them loses correct candidates
     with no way to overrule it from outside this module. That is what the
     switch is for; it is not a general-purpose knob, and the default stays
-    on because a contradiction is usually real."""
+    on because a contradiction is usually real.
+
+    on_review defaults to None, in the shape on_progress/cancel/diagnostics
+    already use elsewhere in this project: with it left at None the loop
+    below builds no CandidateView and calls nothing, so match_records
+    returns the same mapping, stats and samples for every call site
+    regardless of whether that site knows this parameter exists - which is
+    what leaves tracklist.resolve_tracklist's build-playlist caller, which
+    has no manifest case pinning it, byte-identical by construction rather
+    than by coverage. When supplied, on_review is called once per old
+    record with a RecordReview built from the same branch that already
+    decided that record's stats bucket."""
     # A caller that already built the candidate index for its own purposes
     # (e.g. reconnection's post-match ambiguity check) can pass it in so the
     # O(candidates) index build never runs twice for one match_records call.
@@ -544,6 +586,11 @@ def match_records(
         matched_by: str | None = None
         ambiguous_here = False
         refuted_here = False
+        # Built only when a caller opted in: the review a 12,418-entry
+        # collection would hold in memory for every record is a cost that
+        # must land on the one surface asking for it, never on a call site
+        # that supplied nothing.
+        record_candidates: list[CandidateView] | None = [] if on_review is not None else None
 
         for key_name, key_value in record_keys(old_record, confidence, key_providers):
             if key_value is AMBIGUOUS:
@@ -568,10 +615,27 @@ def match_records(
                 # removes a candidate, so a tier with one plausible and one
                 # implausible hit resolves cleanly instead of reporting a
                 # false ambiguity the operator would have to adjudicate.
-                kept = [c for c in candidates if not _claims_refute(old_claims, c)]
+                if record_candidates is not None:
+                    # Same rule read twice (DL-060): the detail beside a
+                    # review row and the boolean that filters here both come
+                    # from _refutation_reason, so the two can never disagree
+                    # about which candidate was removed or why.
+                    details = [_refutation_reason(old_claims, c) for c in candidates]
+                    record_candidates.extend(
+                        CandidateView(candidate=c, key_name=key_name, refuted=d is not None, detail=d)
+                        for c, d in zip(candidates, details)
+                    )
+                    kept = [c for c, d in zip(candidates, details) if d is None]
+                else:
+                    kept = [c for c in candidates if not _claims_refute(old_claims, c)]
                 if len(kept) != len(candidates):
                     refuted_here = True
                 candidates = kept
+            elif record_candidates is not None:
+                record_candidates.extend(
+                    CandidateView(candidate=c, key_name=key_name, refuted=False, detail=None)
+                    for c in candidates
+                )
             if len(candidates) > 1:
                 # Size as POSITIVE evidence, the only role it has across
                 # sources: when a tier cannot separate its candidates on its
@@ -613,4 +677,27 @@ def match_records(
             if refuted_here:
                 stats["refuted"] += 1
 
+        if on_review is not None:
+            # Read off the same branch that just decided this record's stats
+            # bucket, rather than re-derived from the candidate list, so the
+            # status a review carries can never disagree with where the
+            # record actually landed.
+            if matched_new is not None and matched_by is not None:
+                status = "matched"
+            elif ambiguous_here:
+                status = "ambiguous"
+            elif refuted_here:
+                status = "refuted"
+            else:
+                status = "unmatched"
+            on_review(
+                RecordReview(
+                    old=old_record,
+                    status=status,
+                    candidates=tuple(record_candidates or ()),
+                    chosen=matched_new,
+                    matched_by=matched_by,
+                )
+            )
+
     return mapping, stats, samples
```

**CC-M-001-005** (traktor_nml/reconnect.py) - implements CI-M-001-005

**Code:**

```diff
diff --git a/traktor_nml/reconnect.py b/traktor_nml/reconnect.py
index 2f4b879..9bb5ddf 100644
--- a/traktor_nml/reconnect.py
+++ b/traktor_nml/reconnect.py
@@ -17,11 +17,14 @@ collisions and exported to the ambiguity CSV instead of being rewritten
 
 from __future__ import annotations
 
+from dataclasses import replace
 from pathlib import Path
+from typing import Callable, Optional
 
 from .confidence import MatchConfidence
 from .matching import AMBIGUOUS, KeyProvider, build_new_indexes, match_records, record_keys
 from .model import EntryRecord, LocationParts, encode_traktor_dir
+from .review import RecordReview
 
 
 def location_from_disk_path(path: Path, volume: str, volumeid: str) -> LocationParts:
@@ -104,27 +107,54 @@ def resolve_reconnection(
     confidence: MatchConfidence,
     key_providers: list[KeyProvider] = (),
     refute: bool = True,
+    on_review: Optional[Callable[[RecordReview], None]] = None,
 ) -> tuple[dict[str, EntryRecord], dict[str, int], list[dict[str, str]]]:
     """Match old_records against candidates via the shared cascade, then
     invert the resulting mapping to find and drop destination collisions
     - candidates claimed by more than one old record - reclassifying
     their claimants out of the one-to-one mapping and re-deriving each
     affected tier's match count so matched_<tier> totals stay consistent
-    with the final matched count (DL-004)."""
+    with the final matched count (DL-004).
+
+    on_review defaults to None and is forwarded to match_records with
+    nothing else changed, so a caller supplying nothing gets the identical
+    mapping, stats and ambiguity_rows this function has always returned.
+    When supplied, the reviews match_records emits are held here rather
+    than handed straight to the caller, because the one-to-one guarantee
+    match_records is deliberately unaware of (see the module docstring)
+    is not resolved until enforce_one_to_one runs below: a review is
+    reclassified to destination_collision in the same walk that already
+    builds ambiguity_rows for every collided key, then on_review is called
+    for each review in the order match_records produced them.
+    """
     # Built once and reused both for match_records' own lookup and for the
     # post-match ambiguity check below, instead of match_records building
     # its own copy and this function silently rebuilding an identical one
     # (doubling the O(old x candidates) fingerprint similarity search when a
     # fingerprint provider is injected).
     indexes = build_new_indexes(candidates, confidence, key_providers)
+    reviews: list[RecordReview] | None = [] if on_review is not None else None
     mapping, match_stats, _samples = match_records(
-        old_records, candidates, confidence, key_providers, indexes=indexes, refute=refute
+        old_records,
+        candidates,
+        confidence,
+        key_providers,
+        indexes=indexes,
+        refute=refute,
+        on_review=None if reviews is None else reviews.append,
     )
 
     final_mapping, stats, collided_keys = enforce_one_to_one(
         mapping, match_stats, old_records, indexes, confidence, key_providers
     )
 
+    if reviews is not None:
+        for index, review in enumerate(reviews):
+            if review.old.primary_key in collided_keys:
+                reviews[index] = replace(review, status="destination_collision")
+        for review in reviews:
+            on_review(review)
+
     ambiguity_rows: list[dict[str, str]] = []
     for record in old_records:
         old_key = record.primary_key
```

**CC-M-001-006** (tests/test_review_channel.py) - implements CI-M-001-006

**Code:**

```diff
--- /dev/null
+++ b/tests/test_review_channel.py
@@ -0,0 +1,217 @@
+"""Guards for the on_review channel through match_records and
+resolve_reconnection: inertness when the parameter is left at None,
+per-record status coverage, refutation detail arithmetic, and the
+destination_collision overlay resolve_reconnection applies above the
+matcher. Each guard constructs its broken scenario in executable code
+and records the mutation and the observed output in its docstring.
+"""
+
+from __future__ import annotations
+
+from traktor_nml import matching as matching_module
+from traktor_nml.confidence import MatchConfidence
+from traktor_nml.model import EntryRecord, LocationParts
+from traktor_nml.reconnect import resolve_reconnection
+from traktor_nml.review import CandidateView, RecordReview
+
+
+def _old(artist: str, title: str, dirv: str, filename: str, size: str = "16", time: str = "1.0") -> EntryRecord:
+    return EntryRecord(
+        entry=None,
+        artist=artist,
+        title=title,
+        audio_id="",
+        filesize=size,
+        playtime_float=time,
+        bitrate="320",
+        album="",
+        file_name=filename,
+        location=LocationParts(volume="Z:", volumeid="Z:", dir_value=dirv, file_name=filename),
+    )
+
+
+def _candidate(filename: str, size: str = "16", time: str = "1.0") -> EntryRecord:
+    return EntryRecord(
+        entry=None,
+        artist="",
+        title="",
+        audio_id="",
+        filesize=size,
+        playtime_float=time,
+        bitrate="320",
+        album="",
+        file_name=filename,
+        location=LocationParts(volume="", volumeid="", dir_value="/:", file_name=filename),
+    )
+
+
+def test_on_review_none_is_inert_and_builds_no_candidate_views(monkeypatch) -> None:
+    """resolve_reconnection with on_review omitted must produce the same
+    mapping, stats and ambiguity_rows as a run supplying a recording
+    collector, and must construct no CandidateView while doing it.
+
+    Negative control: with on_review supplied instead of omitted, the same
+    scenario is shown to construct at least one CandidateView, which is
+    what demonstrates the omitted-case assertion is actually exercising
+    the guard rather than passing regardless of whether construction ever
+    happens at all.
+    """
+    old_records = [
+        _old("A", "One", "/:gone1/:", "one.mp3"),
+        _old("B", "Two", "/:gone2/:", "two.mp3"),
+        _old("C", "Missing", "/:gone3/:", "missing.mp3"),
+    ]
+    candidates = [_candidate("one.mp3"), _candidate("two.mp3")]
+
+    mapping_omitted, stats_omitted, rows_omitted = resolve_reconnection(
+        old_records, candidates, MatchConfidence.FILENAME
+    )
+
+    built = 0
+    real_init = CandidateView.__init__
+
+    def counting_init(self, *args, **kwargs):
+        nonlocal built
+        built += 1
+        real_init(self, *args, **kwargs)
+
+    monkeypatch.setattr(CandidateView, "__init__", counting_init)
+    reviews: list[RecordReview] = []
+    mapping_collected, stats_collected, rows_collected = resolve_reconnection(
+        old_records, candidates, MatchConfidence.FILENAME, on_review=reviews.append
+    )
+
+    assert mapping_omitted == mapping_collected
+    assert stats_omitted == stats_collected
+    assert rows_omitted == rows_collected
+    assert built > 0, "expected the supplied collector to trigger CandidateView construction"
+
+    # Now the actual inertness claim: re-run with on_review omitted while
+    # the counting __init__ is still installed, and confirm nothing built.
+    built = 0
+    resolve_reconnection(old_records, candidates, MatchConfidence.FILENAME)
+    assert built == 0, "on_review=None must construct no CandidateView at all"
+
+
+def test_every_record_reviewed_exactly_once_with_status_matching_its_bucket() -> None:
+    """Over a small mixed corpus, every old record appears in exactly one
+    RecordReview and that review's status agrees with which stats bucket
+    the record fell into.
+
+    Negative control: mutating one collected review's status away from
+    what its own record actually matched to is shown to break the
+    per-record agreement check below, so the assertion is sensitive
+    rather than vacuous.
+    """
+    old_records = [
+        _old("A", "One", "/:gone1/:", "one.mp3"),  # matches uniquely
+        _old("Z", "Nothing", "/:gone2/:", "absent.mp3"),  # no candidate at all -> unmatched
+    ]
+    candidates = [_candidate("one.mp3")]
+
+    reviews: list[RecordReview] = []
+    mapping, stats, _rows = resolve_reconnection(
+        old_records, candidates, MatchConfidence.FILENAME, on_review=reviews.append
+    )
+
+    assert len(reviews) == len(old_records)
+    seen_keys = {r.old.primary_key for r in reviews}
+    assert seen_keys == {r.primary_key for r in old_records}
+
+    matched_keys = set(mapping.keys())
+    for review in reviews:
+        if review.old.primary_key in matched_keys:
+            assert review.status == "matched"
+        else:
+            assert review.status in ("unmatched", "ambiguous", "refuted", "destination_collision")
+
+    # Negative control: corrupt one review's status and show the agreement
+    # check above catches it.
+    mutated = list(reviews)
+    matched_index = next(i for i, r in enumerate(mutated) if r.old.primary_key in matched_keys)
+    from dataclasses import replace
+
+    mutated[matched_index] = replace(mutated[matched_index], status="unmatched")
+    mismatches = [
+        r for r in mutated if (r.old.primary_key in matched_keys) != (r.status == "matched")
+    ]
+    assert mismatches, "expected the mutated status to be caught as a mismatch"
+
+
+def test_duration_refutation_detail_reproduces_the_filter_numbers(monkeypatch) -> None:
+    """A candidate whose duration differs from the old record's by more
+    than the same-source allowance is refuted, and the emitted
+    RefutationDetail carries the exact difference and allowance the
+    filter used.
+
+    Negative control: widening _DURATION_ABS_TOLERANCE so the same pair no
+    longer contradicts is shown to make the record arrive unmatched with
+    no candidate offered at all (the filename tier is the only one that
+    can fire here and it has no ambiguity, so a refuted candidate leaves
+    the record with zero survivors), and no RefutationDetail on any
+    candidate view.
+    """
+    old = _old("A", "One", "/:gone1/:", "one.mp3", size="16", time="10.0")
+    candidate = _candidate("one.mp3", size="16", time="30.0")  # 20s apart, over 1.0s allowance
+
+    reviews: list[RecordReview] = []
+    resolve_reconnection([old], [candidate], MatchConfidence.FILENAME, on_review=reviews.append)
+    assert len(reviews) == 1
+    review = reviews[0]
+    assert review.status == "refuted"
+    assert len(review.candidates) >= 1
+    assert all(view.candidate is candidate for view in review.candidates)
+    view = review.candidates[0]
+    assert view.refuted is True
+    assert view.detail is not None
+    assert view.detail.field == "duration"
+    assert view.detail.difference == 20.0
+    assert view.detail.allowance == 1.0
+
+    # Negative control: widen the tolerance so the pair no longer refutes.
+    monkeypatch.setattr(matching_module, "_DURATION_ABS_TOLERANCE", 25.0)
+    reviews_widened: list[RecordReview] = []
+    resolve_reconnection(
+        [old], [candidate], MatchConfidence.FILENAME, on_review=reviews_widened.append
+    )
+    widened_review = reviews_widened[0]
+    assert widened_review.status == "matched"
+    assert all(not v.refuted and v.detail is None for v in widened_review.candidates)
+
+
+def test_collided_records_overlay_as_destination_collision_not_matched() -> None:
+    """Two old records that each unambiguously match the same single
+    candidate arrive as destination_collision, the status the ambiguity
+    CSV also records for them, rather than as matched.
+
+    Negative control: reading the reviews match_records itself emits -
+    before resolve_reconnection's post-pass overlays the collision status
+    - shows both would otherwise read matched, which is exactly the
+    disagreement between the review channel and the ambiguity CSV the
+    overlay exists to prevent.
+    """
+    old_a = _old("A", "One", "/:gone1/:", "shared.mp3")
+    old_b = _old("B", "One", "/:gone2/:", "shared.mp3")
+    candidate = _candidate("shared.mp3")
+
+    reviews: list[RecordReview] = []
+    final_mapping, stats, rows = resolve_reconnection(
+        [old_a, old_b], [candidate], MatchConfidence.FILENAME, on_review=reviews.append
+    )
+    assert stats["destination_collisions"] == 2
+    assert old_a.primary_key not in final_mapping
+    assert old_b.primary_key not in final_mapping
+    assert {r.status for r in reviews} == {"destination_collision"}
+    assert {row["reason"] for row in rows} == {"destination_collision"}
+
+    # Negative control: match_records' own (pre-overlay) reviews, obtained
+    # by calling it directly the way resolve_reconnection does internally,
+    # both read matched - the divergence the overlay walk exists to fix.
+    from traktor_nml.matching import build_new_indexes, match_records
+
+    indexes = build_new_indexes([candidate], MatchConfidence.FILENAME)
+    pre_overlay: list[RecordReview] = []
+    match_records(
+        [old_a, old_b], [candidate], MatchConfidence.FILENAME, indexes=indexes, on_review=pre_overlay.append
+    )
+    assert {r.status for r in pre_overlay} == {"matched"}
```


### Milestone 2: Collision refusal as a callable predicate

**Files**: traktor_nml/rewrite.py, tests/test_write_refusal_predicate.py

**Requirements**:

- output_collision_refusal(input_path; output_path; extra_inputs) returns the refusal string when the resolved output equals the resolved input or any extra input and None otherwise;the first statement of plan_and_write_nml calls it and returns WriteOutcome(None; None; refusal; None; 2) when it is not None;no filesystem read; no parse and neither caller callback runs ahead of that call

**Acceptance Criteria**:

- the three rewrite-from-reconnect manifest cases and the rewrite and rewrite-from-collection-compare cases pass unregenerated;a collision refusal returns before collect_patches or mutate_tree is entered; proven by a callback that raises;the refusal string is the exact literal output_must_differ_from_input and the exit code is 2

**Tests**:

- tests/test_write_refusal_predicate.py

#### Code Intent

- **CI-M-002-001** `traktor_nml/rewrite.py::output_collision_refusal`: Resolves output_path against input_path and every extra input and returns the literal refusal string when any of them is the same file, None otherwise. One definition of the rule, reachable from above the CLI so a caller can ask the question before doing any work rather than discovering the answer from a WriteOutcome. (refs: DL-067)
- **CI-M-002-002** `traktor_nml/rewrite.py::plan_and_write_nml`: The first statement calls output_collision_refusal and returns WriteOutcome(None, None, refusal, None, 2) when it is not None, so the refusal still precedes reading, parsing and both caller callbacks and a refused write still costs nothing. The refusal string reaching stderr through write_nml_safely, and the exit code, are unchanged values because they come from the same expression the inline check produced. (refs: DL-067)
- **CI-M-002-003** `tests/test_write_refusal_predicate.py::module`: Guards that the refusal precedes every cost. Ordering: plan_and_write_nml is called with output equal to input and with a collect_patches and a mutate_tree that each raise AssertionError if entered; the outcome carries the refusal and neither raise fires. The negative control moves the check to after the parse in a local copy of the function body and records that the callback raised, demonstrating the test detects the ordering rather than only the return value, and is not a mock deciding its own outcome. Single definition: the string on the WriteOutcome and the string output_collision_refusal returns for the same three paths are compared as equal, so a second literal in either place fails; the negative control changes one of the two literals and records the inequality reported. Extra inputs: a collision against an extra input, not the primary input, is refused, and a non-colliding output returns None with the callbacks reached. (refs: DL-067)

#### Code Changes

**CC-M-002-001** (traktor_nml/rewrite.py) - implements CI-M-002-001

**Code:**

```diff
diff --git a/traktor_nml/rewrite.py b/traktor_nml/rewrite.py
index f86ad3e..7798050 100644
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -451,6 +451,22 @@ CollectPatchesFn = Callable[[ET.Element], tuple[list[ElemPatch], dict[str, int],
 MutateTreeFn = Callable[[ET.Element, bool], tuple[dict[str, int], list]]
 
 
+def output_collision_refusal(
+    input_path: Path, output_path: Path, extra_inputs: tuple[Path, ...] = ()
+) -> Optional[str]:
+    """The refusal string when output_path resolves to input_path or any
+    path in extra_inputs, None otherwise.
+
+    One definition of the rule, reachable from above the CLI so a caller -
+    the wizard's Write control - can ask the question before doing any
+    work rather than discovering the answer from a WriteOutcome after
+    committing to a run.
+    """
+    if output_path.resolve() in {input_path.resolve(), *(p.resolve() for p in extra_inputs)}:
+        return "output_must_differ_from_input"
+    return None
+
+
 def plan_and_write_nml(
     input_path: Path,
     output_path: Path,
@@ -469,12 +485,13 @@ def plan_and_write_nml(
     exceptions apply_and_write can raise are caught and folded into the
     outcome.
     """
-    if output_path.resolve() in {input_path.resolve(), *(p.resolve() for p in extra_inputs)}:
+    refusal = output_collision_refusal(input_path, output_path, extra_inputs)
+    if refusal is not None:
         # Checked before parsing and before either callback runs: the
         # reconnect callback owns a long disk scan, and running it ahead
         # of this refusal would make a refused write cost the whole scan
         # instead of returning immediately.
-        return WriteOutcome(None, None, "output_must_differ_from_input", None, 2)
+        return WriteOutcome(None, None, refusal, None, 2)
 
     if HAS_LXML:
         read_result = read_and_parse_source(input_path)
```

**CC-M-002-002** (traktor_nml/rewrite.py) - implements CI-M-002-002

**Code:**

```diff
diff --git a/traktor_nml/rewrite.py b/traktor_nml/rewrite.py
index f86ad3e..7798050 100644
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -451,6 +451,22 @@ CollectPatchesFn = Callable[[ET.Element], tuple[list[ElemPatch], dict[str, int],
 MutateTreeFn = Callable[[ET.Element, bool], tuple[dict[str, int], list]]
 
 
+def output_collision_refusal(
+    input_path: Path, output_path: Path, extra_inputs: tuple[Path, ...] = ()
+) -> Optional[str]:
+    """The refusal string when output_path resolves to input_path or any
+    path in extra_inputs, None otherwise.
+
+    One definition of the rule, reachable from above the CLI so a caller -
+    the wizard's Write control - can ask the question before doing any
+    work rather than discovering the answer from a WriteOutcome after
+    committing to a run.
+    """
+    if output_path.resolve() in {input_path.resolve(), *(p.resolve() for p in extra_inputs)}:
+        return "output_must_differ_from_input"
+    return None
+
+
 def plan_and_write_nml(
     input_path: Path,
     output_path: Path,
@@ -469,12 +485,13 @@ def plan_and_write_nml(
     exceptions apply_and_write can raise are caught and folded into the
     outcome.
     """
-    if output_path.resolve() in {input_path.resolve(), *(p.resolve() for p in extra_inputs)}:
+    refusal = output_collision_refusal(input_path, output_path, extra_inputs)
+    if refusal is not None:
         # Checked before parsing and before either callback runs: the
         # reconnect callback owns a long disk scan, and running it ahead
         # of this refusal would make a refused write cost the whole scan
         # instead of returning immediately.
-        return WriteOutcome(None, None, "output_must_differ_from_input", None, 2)
+        return WriteOutcome(None, None, refusal, None, 2)
 
     if HAS_LXML:
         read_result = read_and_parse_source(input_path)
```

**CC-M-002-003** (tests/test_write_refusal_predicate.py) - implements CI-M-002-003

**Code:**

```diff
--- /dev/null
+++ b/tests/test_write_refusal_predicate.py
@@ -0,0 +1,134 @@
+"""Guards for output_collision_refusal, the single predicate
+plan_and_write_nml's first statement calls. Each guard constructs its
+broken scenario in executable code and records the mutation and the
+observed output in its docstring.
+"""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+from traktor_nml.rewrite import WriteOutcome, output_collision_refusal, plan_and_write_nml
+
+
+def _write_minimal_nml(path: Path) -> None:
+    path.write_text(
+        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+        '<NML VERSION="19">\n'
+        '  <COLLECTION ENTRIES="0">\n'
+        '  </COLLECTION>\n'
+        '</NML>\n',
+        encoding="utf-8",
+    )
+
+
+def _asserting_collect(root):
+    raise AssertionError("collect_patches must not run when output collides")
+
+
+def _asserting_mutate(root, dry_run):
+    raise AssertionError("mutate_tree must not run when output collides")
+
+
+def test_collision_refusal_precedes_either_callback(tmp_path: Path) -> None:
+    """A colliding output=input call must return the refusal without
+    entering collect_patches or mutate_tree, proven by callbacks that
+    raise AssertionError the moment they're entered rather than by
+    inspecting the returned outcome alone.
+
+    Negative control: a local stand-in that checks the collision only
+    after reading and parsing the source shows the asserting callback
+    actually IS reachable at that point (it raises), so the guard above
+    is shown to detect a check that runs too late rather than passing
+    for any ordering at all.
+    """
+    input_path = tmp_path / "in.nml"
+    _write_minimal_nml(input_path)
+
+    outcome = plan_and_write_nml(input_path, input_path, False, _asserting_collect, _asserting_mutate)
+    assert outcome == WriteOutcome(None, None, "output_must_differ_from_input", None, 2)
+
+    def reordered_check(input_path: Path, output_path: Path) -> None:
+        # Stand-in for a version of plan_and_write_nml with the collision
+        # check placed after the read/parse instead of before it - the
+        # negative control for the ordering assertion above.
+        from traktor_nml.rewrite import read_and_parse_source
+
+        read_result = read_and_parse_source(input_path)
+        assert read_result.error is None
+        _asserting_collect(read_result.root)  # never reached if refusal ran first
+        output_collision_refusal(input_path, output_path)
+
+    raised = False
+    try:
+        reordered_check(input_path, input_path)
+    except AssertionError as exc:
+        raised = True
+        assert "collect_patches must not run" in str(exc)
+    assert raised, "expected the reordered stand-in to reach the asserting callback"
+
+
+def test_single_refusal_literal_shared_by_predicate_and_outcome(tmp_path: Path) -> None:
+    """The literal output_collision_refusal returns and the literal
+    embedded in plan_and_write_nml's WriteOutcome must be the same
+    string, across colliding with the primary input and with each extra
+    input, so a second copy of the literal in either place would be
+    caught rather than silently diverging.
+
+    Negative control: comparing the real result against a deliberately
+    different literal shows the equality assertion is sensitive rather
+    than trivially true.
+    """
+    input_path = tmp_path / "in.nml"
+    extra_a = tmp_path / "extra_a.nml"
+    extra_b = tmp_path / "extra_b.nml"
+    _write_minimal_nml(input_path)
+
+    scenarios = [
+        (input_path, ()),
+        (extra_a, (extra_a, extra_b)),
+        (extra_b, (extra_a, extra_b)),
+    ]
+    last_result = None
+    for output_path, extra_inputs in scenarios:
+        predicate_result = output_collision_refusal(input_path, output_path, extra_inputs)
+        outcome = plan_and_write_nml(
+            input_path, output_path, False, _asserting_collect, _asserting_mutate, extra_inputs
+        )
+        assert predicate_result == outcome.error == "output_must_differ_from_input"
+        last_result = predicate_result
+
+    assert last_result != "output_must_differ_from_input_MUTATED"
+
+
+def test_extra_input_collision_refused_and_non_collision_reaches_callbacks(tmp_path: Path) -> None:
+    """A collision against an extra input, not the primary input, is
+    refused; a non-colliding output returns None and the callbacks are
+    actually reached.
+    """
+    input_path = tmp_path / "in.nml"
+    extra_a = tmp_path / "extra_a.nml"
+    extra_b = tmp_path / "extra_b.nml"
+    _write_minimal_nml(input_path)
+
+    assert output_collision_refusal(input_path, extra_a, (extra_a, extra_b)) == "output_must_differ_from_input"
+    outcome = plan_and_write_nml(
+        input_path, extra_a, False, _asserting_collect, _asserting_mutate, (extra_a, extra_b)
+    )
+    assert outcome == WriteOutcome(None, None, "output_must_differ_from_input", None, 2)
+
+    non_colliding = tmp_path / "out.nml"
+    assert output_collision_refusal(input_path, non_colliding, (extra_a, extra_b)) is None
+
+    reached: list[str] = []
+
+    def collect_patches(root):
+        reached.append("collect_patches")
+        return [], {"x": 1}, []
+
+    def mutate_tree(root, dry_run):
+        reached.append("mutate_tree")
+        return {"x": 1}, []
+
+    plan_and_write_nml(input_path, non_colliding, True, collect_patches, mutate_tree, (extra_a, extra_b))
+    assert reached, "expected a callback to be reached for a non-colliding output"
```


### Milestone 3: Shared reconnect write core and result surface

**Files**: traktor_nml/reconnect_run.py, tests/test_reconnect_write_core.py

**Requirements**:

- ReconnectResult carries reviews as a tuple defaulting to empty;run_reconnection accepts an optional reviews list; installs a collector only when one is supplied; appends into the list the caller owns and populates ReconnectResult.reviews from it;scan_reconnect_candidates accepts and forwards reviews alongside on_progress and cancel;write_reconnect_result(args; provide_result; on_progress; cancel) holds the whole write path: both the lxml patch-collection branch and the stdlib mutate branch; the ambiguity CSV write; the holder that carries reconnect and csv_path; and the VolumeIdentityError and fingerprint-unavailable mapping onto RewriteReconnectResult;rewrite_from_reconnect is one call to write_reconnect_result whose provider is run_reconnection;ScanCancelled crosses write_reconnect_result untouched

**Acceptance Criteria**:

- the three rewrite-from-reconnect manifest cases pass unregenerated; which is the proof the factoring changed nothing;a write driven by write_reconnect_result from a result obtained by an earlier scan; with zero overrides; produces bytes equal to the recorded manifest bytes for the same argv;a collision refusal from a wizard-shaped call returns before the provider is invoked; proven by a provider that raises;a provider raising ScanCancelled leaves no RewriteReconnectResult and no output file;a run with reviews omitted produces ReconnectResult.reviews equal to the empty tuple and stats equal to a run with reviews supplied

**Tests**:

- tests/test_reconnect_write_core.py

#### Code Intent

- **CI-M-003-001** `traktor_nml/reconnect_run.py::ReconnectResult`: A reviews field holding a tuple of RecordReview, defaulting to empty. A tuple in cascade order for the same reason diagnostics is a sequence: the review table reads rows in the order the pipeline produced them, and a set or mapping would lose that. Empty for every CLI run, because the CLI supplies no reviews list and therefore no collector is installed. (refs: DL-061)
- **CI-M-003-002** `traktor_nml/reconnect_run.py::run_reconnection`: A reviews keyword defaulting to None, in the shape diagnostics already has: when a list is supplied the function passes reviews.append as on_review to resolve_reconnection and builds ReconnectResult.reviews from that list, so reviews collected before a later raise still exist in the scope of the caller; when it is None no on_review is passed at all and resolve_reconnection runs the cascade with the parameter left inert, so the CLI path constructs no review object. Neither branch touches the mapping, the stats, the ambiguity rows or the LOCATION re-encoding. (refs: DL-058, DL-061)
- **CI-M-003-003** `traktor_nml/reconnect_run.py::scan_reconnect_candidates`: A reviews keyword defaulting to None, passed straight to run_reconnection beside on_progress and cancel, so the wizard reaches the review data through the same core the CLI runs rather than through a pipeline of its own. (refs: DL-058, DL-061)
- **CI-M-003-004** `traktor_nml/reconnect_run.py::write_reconnect_result`: The whole reconnect write path, parameterised by provide_result, a callable taking the parsed old root and returning a ReconnectResult. It owns the holder dict with reconnect and csv_path, the lxml _collect_patches branch, the stdlib mutate_tree branch, the ambiguity CSV write, the diagnostics list, the call to plan_and_write_nml, the VolumeIdentityError and _FingerprintUnavailable mapping onto RewriteReconnectResult, and the final RewriteReconnectResult assembly. Because provide_result is called from inside the callback, the collision refusal still runs first for every caller: a wizard supplying a provider that returns a result it already holds gets the same refusal-before-anything ordering as a CLI run whose provider is a twenty-minute scan. ScanCancelled raised by a provider is caught nowhere here, so it leaves the function with no RewriteReconnectResult at all. (refs: DL-065, DL-066, DL-068)
- **CI-M-003-005** `traktor_nml/reconnect_run.py::rewrite_from_reconnect`: One call to write_reconnect_result whose provider runs run_reconnection over the supplied root with the same args, on_progress, cancel and diagnostics list. The stdout and stderr of rewrite-from-reconnect are the same bytes because the lines come from the same stats and the same WriteOutcome, produced by the same code, differing only in which callable supplied the result. (refs: DL-065, DL-066)
- **CI-M-003-006** `tests/test_reconnect_write_core.py::module`: Guards for the shared write core, each constructing its broken scenario in executable code and recording the mutation and the observed output in its docstring. Zero-override byte identity: a scan-then-write through write_reconnect_result with a provider returning the scan result unchanged produces a file whose bytes equal the manifest bytes recorded for the same argv; the negative control drops one key from the mapping before the write and records the byte difference and which LOCATION it lands on, so the assertion is shown to be sensitive to the mapping rather than passing on any file. Refusal ordering: a wizard-shaped call whose output equals its input with a provider that raises AssertionError returns the typed refusal and the provider is never entered; the negative control calls plan_and_write_nml with a non-colliding output and records that the same provider does raise, so the first result is the ordering rather than a provider that never runs. Cancellation: a provider raising ScanCancelled leaves no RewriteReconnectResult, no output .nml under tmp_path, and a tag cache that still loads through TagCache; the negative control wraps the provider call in an except ScanCancelled returning a partial result and records the candidate count that partial result reports against the complete run, which is the mostly-missing-collection reading DL-053 exists to prevent. Preview writes nothing: every file under tmp_path is snapshotted by size and mtime around a preview run and only .traktor_nml_tagcache.json differs; the negative control removes the dry-run guard and records the output file that appears. Review inertness at the core boundary: a run with reviews omitted and a run with a list supplied produce equal stats, equal mapping keys and equal written bytes. Every byte assertion in this module pins the zero-override case; the non-zero-override property is pinned by CI-M-004-009, which extends this same module at M-004's gate, once wizard_state.amended_result exists to be driven. (refs: DL-061, DL-065, DL-066, DL-068)

#### Code Changes

Not yet registered as code changes at plan-freeze time; the milestone's Code Intent entries above are what the executor workflow builds M-003 through M-006 from.


### Milestone 4: Wizard decision logic

**Files**: traktor_nml/gui/__init__.py, traktor_nml/gui/review_model.py, traktor_nml/gui/wizard_state.py, pyproject.toml, tests/test_gui_review_model.py, tests/test_gui_wizard_state.py, tests/test_reconnect_write_core.py

**Requirements**:

- review_model derives the six Specs statuses from a RecordReview plus operator state: matched; ambiguous; refuted; format; rejected and no_match. These six are the whole status set; accepted is not among them. Accepted is a decision state, not a status: wizard_state's three decision states are undecided; accepted and left-missing, a left-missing decision is what yields the status rejected, and an accepted decision leaves the row's matcher-derived status standing so an audited automatic match still reads matched. The Accepted chip of Specs therefore filters on the decision axis, not on a status;review_model derives the four display confidence tokens from the tier that produced a candidate;review_model exposes the seven filters of Specs with their counts and the queue as the first four;wizard_state holds one decision per record over undecided; accepted and left-missing; supports picking a candidate without accepting it; and supports undo;wizard_state.apply produces an amended mapping from a ReconnectResult plus its decisions; re-encoding the LOCATION of any candidate it promotes;wizard_state exposes the write refusal by calling output_collision_refusal; so the Write control carries a reason;wizard_state.amended_result(result; decisions) returns the ReconnectResult the wizard hands to write_reconnect_result: the amended mapping alone is replaced and stats; ambiguity_rows; old_records; reviews; warnings and diagnostics carry through as the scan produced them;wizard_state.fingerprint_control_state() reads fingerprint_key_provider and fingerprint_unavailable_reason through traktor_nml.reconnect_run and returns disabled with the not-installed reason when the provider is None without calling the probe at all;neither module imports nicegui; pywebview or anything under traktor_nml/commands/;traktor_nml.gui is listed in the packages array of pyproject.toml;tests/test_reconnect_write_core.py gains the non-zero-override write guard here; because it drives wizard_state.amended_result; which this milestone creates

**Acceptance Criteria**:

- an amended mapping built from zero decisions is equal to the mapping of the ReconnectResult it came from;rejecting one record removes exactly that key from the amended mapping and leaves every other key identical;accepting an alternative candidate places that candidate in the amended mapping carrying a LOCATION with the resolved VOLUME and VOLUMEID rather than the scan placeholder;the six statuses - matched; ambiguous; refuted; format; rejected and no_match - partition every record of a fixture-corpus run, row_status returns no token outside that set for any decision state including accepted, and the seven filter counts sum consistently with the queue;pytest tests/ -q reports at least 243 passed and at most 3 skipped on the system interpreter; which has no nicegui;amended_result over an empty decision set returns a ReconnectResult equal field for field to the one passed in, and over a non-empty decision set changes mapping alone, leaving stats, ambiguity_rows, old_records, reviews, warnings and diagnostics identical to the scan's;fingerprint_control_state returns disabled with the not-installed reason when reconnect_run.fingerprint_key_provider is None and does not call fingerprint_unavailable_reason, which is the state of the machine this plan is verified on;a write whose provider returns wizard_state.amended_result over a decision set rejecting one record - a record the scan matched, so it is present in result.mapping and absent from ambiguity_rows, which is what makes rejecting it change the written bytes at all - is compared against the zero-override write element by element rather than byte by byte, because a rejected record keeps its original LOCATION and the two strings differ in length, so every byte after that point shifts and a byte-offset diff would report the whole tail: both outputs are parsed and every record's LOCATION asserted equal except the rejected record's, whose LOCATION equals the input's. This does not touch the zero-override byte-identity property above, which is a whole-file comparison and stays one. The RewriteReconnectResult it returns carries the scan's own stats and ambiguity_rows unchanged rather than a recount, and the ambiguity_rows half is a real negative control rather than a tautology because the guard executes the recount rather than predicting it: in test code it re-derives the pair over amended_result(result, decisions).mapping by reconnect.py's own rule - a row for every old record absent from the mapping, a matched count from the mapping's size - asserts the recounted matched count is exactly one less than the carried-through count, asserts a recounted ambiguity row keyed on the rejected record's old path exists and that no such row exists in the carried-through ambiguity_rows, and the docstring records the two counts actually observed on the fixture corpus rather than counts predicted for a mutation nobody ran. This is the plan's one criterion pinning a non-zero-override write

**Tests**:

- tests/test_gui_review_model.py
- tests/test_gui_wizard_state.py
- tests/test_reconnect_write_core.py

#### Code Intent

- **CI-M-004-001** `traktor_nml/gui/__init__.py::module`: The package marker, importing nothing. Empty of imports on purpose: tests/test_cli_without_nicegui.py blocks nicegui in sys.modules and any import here would run for anything touching the package name at all. (refs: DL-069)
- **CI-M-004-002** `traktor_nml/gui/review_model.py::module`: Turns a RecordReview plus one operator decision into a row the table renders, with no framework import. row_status maps the five matcher statuses and the operator decision onto the six statuses Specs names - matched, ambiguous, refuted, format, rejected and no_match - and returns nothing outside that set. The two axes are kept apart: a left-missing decision wins outright and yields rejected, which is the status Specs labels Left missing; an accepted decision yields no status of its own and leaves the matcher-derived status standing, so a Strong match the operator has audited still reads matched and stays rejectable afterwards. Accepted is therefore a wizard_state decision state, never a row_status return, and the Accepted chip of FILTERS selects on decisions rather than on statuses - which is also why the seven chips outnumber the six statuses rather than mapping one to one. With that split, matched yields matched unless the winner's suffix differs from the old record's, which yields format; ambiguous and destination_collision yield ambiguous; refuted yields refuted; and unmatched with no candidates yields no_match. display_confidence maps a candidate's key_name through a table to Strong, Good, Weak or None: the audio_id and the three artist-title-plus-field tiers read Strong, artist_title_album_time and the deep path suffix read Good, the shallow path suffixes and the container-stripped name tiers read Weak, and absence of a candidate reads None. FILTERS names the seven chips of Specs in order with the predicate each selects, and the first four are the queue. The tier table and the suffix comparison live here rather than in matching.py because both are questions about how a match is described, not about which match was made. (refs: DL-063, DL-064, DL-072, DL-067)
- **CI-M-004-003** `traktor_nml/gui/wizard_state.py::module`: The operator's decisions and the amended mapping they produce, with no framework import. A decision per primary key over undecided, accepted and left-missing, plus the index of the picked candidate, so picking a candidate changes which file is proposed while the row stays undecided, as Specs requires. undo returns a record to undecided from either terminal state. apply(result, decisions) builds the amended mapping: it starts from result.mapping, drops the key of every left-missing record, inserts the picked candidate for every accepted record whose pick differs from the matcher's winner, and runs the amended mapping through the same LOCATION re-encoding the core applies to winners, so a promoted candidate carries a resolved VOLUME and VOLUMEID rather than the scan placeholder. With no decisions at all the amended mapping is equal to result.mapping, which is what makes a zero-override write byte-identical rather than merely usually identical. write_refusal asks output_collision_refusal, so the Write control's enabled state and its inline reason come from the rule the CLI enforces. (refs: DL-067, DL-074, DL-066)
- **CI-M-004-004** `pyproject.toml::tool.setuptools`: The packages array lists traktor_nml, traktor_nml.commands and traktor_nml.gui, so an installed wheel and a PyInstaller bundle carry the wizard rather than only a source checkout. (refs: DL-070)
- **CI-M-004-005** `tests/test_gui_review_model.py::module`: Guards for the derived vocabulary, each constructing its broken scenario in executable code and recording the mutation and the observed output. Status totality: over a fixture-corpus run every review maps to exactly one of the six statuses and the six partition the record set; the negative control removes one matcher status from the mapping table and records the record left unclassified. Accepted is not a seventh status: a record is accepted and its row_status is asserted to be its matcher-derived status rather than any new token, and the returned token is asserted to be a member of the six-element set; the negative control makes row_status return the literal accepted for an accepted decision and records the partition assertion failing with a seventh token present in the row set and absent from the status set, which is the divergence between the requirement's list and the filter chips this guard exists to catch. Re-encoded derivation: a review whose winner differs from the old record only in container yields format while a winner differing in folder yields matched; the negative control compares whole filenames instead of suffixes and records the re-encode it then reads as an ordinary match, which is the row that would lose its own filter chip. Confidence tokens are per candidate: two candidates found at different tiers inside one loose run carry different tokens; the negative control substitutes the run's MatchConfidence for the tier table and records every row reading the same word, the failure that motivates the table. Filters: the seven counts and the four-chip queue are checked against the record set they select from. (refs: DL-063, DL-064)
- **CI-M-004-006** `tests/test_gui_wizard_state.py::module`: Guards for the amended mapping, each constructing its broken scenario in executable code and recording the mutation and the observed output. Zero overrides: apply with an empty decision set returns a mapping equal to result.mapping key for key and value for value; the negative control seeds one decision and records the single key that differs, so the equality is shown to be sensitive. Reject: rejecting one record removes exactly that key and leaves every other entry identical, and that record appears in the unresolved rows. Accept an alternative: a record with two candidates is accepted on the second, and the amended mapping holds that candidate with a LOCATION carrying the resolved VOLUME and VOLUMEID; the negative control skips the re-encoding step and records the placeholder VOLUME the written LOCATION then carries, which is the LOCATION Traktor cannot resolve. Picking is not accepting: picking a candidate leaves the row undecided and leaves the amended mapping unchanged. Undo: accept then undo, and reject then undo, both return the amended mapping to the zero-override mapping. Write refusal: a state whose output equals its input reports the refusal string as its reason and reports the control disabled. Result identity: amended_result over an empty decision set is asserted equal field for field to the result passed in, and over a decision set rejecting one record is asserted to differ in mapping alone while stats, ambiguity_rows, old_records, reviews, warnings and diagnostics compare equal; the negative control makes amended_result recompute stats from the amended mapping and records the two stats keys that then differ from the scan's, so the carry-through is shown to be asserted rather than assumed. Fingerprint control, two failure modes kept apart: with traktor_nml.reconnect_run.fingerprint_key_provider set to None and fingerprint_unavailable_reason substituted by a callable that records its calls, fingerprint_control_state is asserted to return disabled with the not-installed reason and that callable is asserted never to have been called; with the provider non-None and the probe returning a fixed reason the control is asserted disabled carrying that text; with the provider non-None and the probe returning None it is asserted enabled. The negative control replaces the implementation with an unconditional fingerprint_unavailable_reason() call in the provider-is-None case and records the observed TypeError: 'NoneType' object is not callable, which is the failure the setup screen would have raised on this machine. (refs: DL-067, DL-074, DL-076, DL-077)
- **CI-M-004-007** `traktor_nml/gui/wizard_state.py::amended_result`: Builds the ReconnectResult the wizard's provider hands to write_reconnect_result, closing the seam between apply's amended mapping and the provider signature CI-M-003-004 defines. amended_result(result, decisions) returns dataclasses.replace(result, mapping=apply(result, decisions)) and replaces nothing else: stats, ambiguity_rows, old_records, reviews, warnings and diagnostics are carried through as the scan's own record of what the matcher found, which no operator decision revises. So the ambiguity CSV and the stats block - both written even under --dry-run, because neither is the command's declared output - stay the scan's record, and the counts the operator's decisions imply are rendered by app.py as a separate override panel driven by the decision set rather than merged into the scan's numbers. With an empty decision set the returned result is equal to the one passed in, field for field, so the zero-override byte identity of CI-M-003-006 holds by construction rather than by coincidence. (refs: DL-076, DL-067, DL-074)
- **CI-M-004-008** `traktor_nml/gui/wizard_state.py::fingerprint_control_state`: Computes whether the fingerprint control is offered and, when it is not, why - in the core's own two steps and the core's own order, with no framework import so it is reachable by a test on a machine without the fingerprint dependency. It reads fingerprint_key_provider and fingerprint_unavailable_reason through traktor_nml.reconnect_run rather than binding them at import, so a test can substitute either. Step one: fingerprint_key_provider is None means traktor_nml.fingerprint itself was not importable, and the control is disabled with the not-installed reason without the probe being called at all - the same except ImportError block binds both names to None (traktor_nml/reconnect_run.py:48-53), so calling the probe in this state raises TypeError: 'NoneType' object is not callable. Step two, reached only when the provider is not None: fingerprint_unavailable_reason() is called, a non-None return disables the control carrying that text, and None leaves it enabled. This is the ordering the pipeline itself uses, testing fingerprint_key_provider is None and raising _FingerprintUnavailable before evaluating unavailable = fingerprint_unavailable_reason() (:181-185), so the two failure modes stay distinct here: provider-is-None, meaning traktor_nml.fingerprint was not importable, against probe-returns-a-reason, meaning it was but fpcalc is not usable. The fingerprint-unavailable error is one of the two the core converts to typed data rather than letting escape (DL-053); the two-mode distinction itself is DL-077's, drawn from the docstring of _FingerprintUnavailable and the comment at traktor_nml/reconnect_run.py:183-193. (refs: DL-077)
- **CI-M-004-009** `tests/test_reconnect_write_core.py::module`: Extends the shared-write-core guard module created at M-003 with the one guard that could not run at M-003's gate, because it drives wizard_state.amended_result and wizard_state is created here. It is added here rather than stubbed there deliberately: a local re-implementation of the amend rule inside the test would be a second definition of it, and would keep passing while the real amended_result drifted away from it, which is exactly the drift DL-076 exists to prevent. Non-zero override: a provider returning wizard_state.amended_result over a decision set that rejects one record is written, both outputs are parsed and every record's LOCATION is asserted equal to the zero-override write's except the rejected record's, whose LOCATION is asserted equal to the input's - element by element rather than byte by byte, because a rejected record keeps its original LOCATION and the two strings differ in length, so every byte after that point shifts and a byte-offset diff would report the whole tail as differing. Whole-file byte identity stays the zero-override criterion's property alone, and the RewriteReconnectResult's stats and ambiguity_rows are asserted equal to the scan result's own; the negative controls are two: dropping a second key from the amended mapping records both the second LOCATION that then differs and the assertion that caught it, so the LOCATION half is shown to be sensitive to which records were overridden rather than merely to the file having changed at all; and for the ambiguity_rows half the guard builds the recounted pair itself over amended_result(result, decisions).mapping by reconnect.py's own rule - a row per old record absent from the mapping, a matched count from the mapping's size - and asserts the recount diverges from the carried-through values in both directions: matched short by exactly one, and a row for the rejected record present in the recount and absent from the carried-through rows. The docstring records the two counts observed, not counts predicted, so no claim here rests on a mutation that was never executed. Every other byte assertion in this module pins the zero-override case deliberately; the two together bound the review layer from both sides. (refs: DL-061, DL-065, DL-066, DL-068, DL-076, DL-067)

#### Code Changes

Not yet registered as code changes at plan-freeze time; the milestone's Code Intent entries above are what the executor workflow builds M-003 through M-006 from.


### Milestone 5: Wizard view

**Files**: traktor_nml/gui/app.py, traktor_nml/gui/file_picker.py, traktor_nml/gui/__main__.py, tests/test_gui_view_boundary.py

**Requirements**:

- app.py builds the four-step wizard of the design set: set up; scan; review; write;the scan runs under nicegui.run.io_bound and feeds on_progress and the diagnostics collector into a progress bar and a ui.log carrying the same key=value vocabulary the renderer produces;the Write control is disabled with the refusal string as its inline reason whenever output_collision_refusal returns one;the fingerprint control's enabled state and inline reason come from wizard_state.fingerprint_control_state(), never from a direct fingerprint_unavailable_reason() call - the same except ImportError block binds fingerprint_key_provider and fingerprint_unavailable_reason to None together, so a direct call on a machine without traktor_nml.fingerprint raises TypeError: 'NoneType' object is not callable before the setup screen renders;the Write control's provider returns wizard_state.amended_result(result, decisions) over the scan result and the operator's decision set rather than the unamended scan result;a ui.dialog opens on the safe button before every collection write and Enter does not write;a cancelled scan shows a cancelled outcome and no review table;file_picker calls create_file_dialog from pywebview in native mode and the local_file_picker component otherwise;app.py; file_picker.py and __main__.py are the only modules under traktor_nml/gui/ importing nicegui or pywebview

**Acceptance Criteria**:

- an AST walk of traktor_nml/gui/ reports the nicegui-importing and pywebview-importing module set as exactly app.py; file_picker.py and __main__.py;tests/test_gui_import_isolation.py and tests/test_cli_without_nicegui.py both pass against the tree containing traktor_nml/gui/;python traktor_nml_tool.py --help and one real invocation succeed with nicegui blocked in sys.modules;pytest tests/ -q reports at least 243 passed and at most 3 skipped;an AST walk of traktor_nml/gui/app.py finds the call to write_reconnect_result and asserts its provider argument - the function passed as provide_result - has wizard_state.amended_result in its body, which is the only reachable guard on the one connecting call in the deliberately untested module; the negative control rewrites that provider body in a copy of the source to return the scan result unamended, runs the same walk over the copy and records that it reports no amended_result call while every M-003 and M-004 criterion still passes, which is exactly the silently-discarded-rejections wiring the guard exists to catch

**Tests**:

- tests/test_gui_view_boundary.py

#### Code Intent

- **CI-M-005-001** `traktor_nml/gui/app.py::module`: The four-step wizard of the design set: set up, scan, review, write. The scan runs under nicegui.run.io_bound, not run.cpu_bound, because cpu_bound uses a process pool and neither TagCache nor an lxml root is cleanly picklable; it drives scan_reconnect_candidates with an on_progress feeding the progress bar, a cancel token behind the stop control, and a reviews list feeding the table. ui.log carries the lines reconnect_render produces, taken from the RenderedOutput stdout_lines and stderr_lines rather than through emit, so the key=value vocabulary of the CLI stays visible without any stream write. The review table renders rows from review_model against decisions held in wizard_state, with the seven filter chips and their counts, the candidate-comparison panel beside the table, and the keyboard map Specs defines. The Write control is disabled with wizard_state's refusal as its inline reason, the fingerprint control's enabled state and inline reason come from wizard_state.fingerprint_control_state() rather than from a direct call to fingerprint_unavailable_reason, which is bound to None on a machine without traktor_nml.fingerprint and would raise TypeError: 'NoneType' object is not callable before the setup screen could render, the resolved tag-cache path and the statement that scanning updates it are shown before the scan starts, a ui.dialog opens on the safe button before the collection write and Enter does not write, and a ScanCancelled arriving from the worker shows a cancelled outcome with no review table at all. The Write control, once enabled, calls write_reconnect_result with a provider that returns wizard_state.amended_result(result, decisions) over the scan result and the operator's decision set - not the unamended scan result, which would discard every rejection while reporting a successful write (DL-076). dry-run is a phase rather than a checkbox: every run previews and the write unlocks afterwards. (refs: DL-068, DL-069, DL-072, DL-076, DL-077)
- **CI-M-005-002** `traktor_nml/gui/file_picker.py::module`: Server-side selection of the collection file and the scan roots. In native mode it calls create_file_dialog from pywebview; otherwise it uses the local_file_picker component pattern. A browser upload is the wrong shape here: scan roots are directories on the machine holding the library, and an upload moves bytes to the server rather than naming a path on it. (refs: DL-069)
- **CI-M-005-003** `traktor_nml/gui/__main__.py::module`: The entry point that starts the wizard, so python -m traktor_nml.gui runs it. It lives here rather than as a subcommand because commands/__init__.py imports every command module at CLI startup, before argv is parsed, and a nicegui import reachable from there would break the whole CLI on a machine without the gui extra. (refs: DL-069)
- **CI-M-005-004** `tests/test_gui_view_boundary.py::module`: Guards the view boundary without importing nicegui, each constructing its broken scenario in executable code and recording the mutation and the observed output. Boundary: an AST walk over every module under traktor_nml/gui/ collects those importing nicegui or pywebview and asserts the set is exactly app.py, file_picker.py and __main__.py; the negative control adds a synthetic module source importing nicegui to the walked set and records the extra module name reported, so the walk is shown to detect an addition rather than merely returning the expected three. Reachability: the walk follows the import graph from review_model.py and wizard_state.py and asserts neither reaches a framework module transitively; the negative control inserts an import of app.py into a copy of review_model's source and records the path the walk then reports. Threading choice: the source of app.py is checked to reference run.io_bound and not run.cpu_bound, with the docstring recording that cpu_bound's process pool cannot carry a TagCache or an lxml root. (refs: DL-069)

#### Code Changes

Not yet registered as code changes at plan-freeze time; the milestone's Code Intent entries above are what the executor workflow builds M-003 through M-006 from.


### Milestone 6: Decision log and navigation indexes

**Files**: traktor_nml/README.md, traktor_nml/CLAUDE.md, traktor_nml/gui/CLAUDE.md, tests/CLAUDE.md, CLAUDE.md, README.md, TODO.md

**Requirements**:

- traktor_nml/README.md carries DL-058 through DL-077; each stated once; in the section describing what it decides;traktor_nml/CLAUDE.md indexes review.py and the gui/ subdirectory with when-to-read triggers;traktor_nml/gui/CLAUDE.md indexes the package; states why the wizard drives the cores directly rather than scraping the CLI transcript and that scraping survives only as the section 5 fallback; and records the two places Specs.dc.html and sections 1 to 5 of docs/nicegui-gui-analysis.md disagree and which governs each;tests/CLAUDE.md indexes the guard modules of this work;the root CLAUDE.md and README.md describe the wizard and the gui extra;TODO.md describes the Guided Repair Review as the workflow this wizard is;every statement describes the code as it stands with no previously; used to; now does; no longer; as before; gains; moves or added

**Acceptance Criteria**:

- a grep for previously; used to; now does; no longer; as before; gains and moves over the touched documents returns nothing describing the code;every DL id between DL-058 and DL-077 resolves to exactly one entry in traktor_nml/README.md, and DL-075 states both that the wizard drives the cores directly and that subprocess-scraping the CLI transcript remains the section 5 fallback;every file listed in a CLAUDE.md index exists and every file in the indexed directory appears in its index

**Tests**:

- none - documentation only

#### Code Intent

- **CI-M-006-001** `traktor_nml/README.md::decision log`: DL-058 through DL-077 stated once each, in the section describing what each decides rather than gathered into a block, matching the convention that a DL tag marks the decision a statement traces to and a second copy would drift. The reasoning DL-058 records is the one DL-056 records for index_scan_roots, applied to match_records: a production caller with no manifest case makes default-inertness the property that keeps it identical by construction rather than by coverage. DL-075 is the one entry in this range that records a rejected alternative rather than a chosen one, and it is stated in the section describing the GUI's data source: it says the wizard calls run_reconnection and the two cores in-process because Tier 1 needs structured data mid-run, and that subprocess-scraping the key=value transcript is not wrong but is the section 5 fallback, available only after a run and therefore unable to feed a live progress display or an interactive ambiguity table. Recording it here rather than leaving it in planner scratch follows the precedent of the renderer split, whose twelve decision chains reached this log at M-003 of that plan; the concrete failure it prevents is a maintainer wiring ui.log from parsed CLI output instead of from RenderedOutput. (refs: DL-058, DL-059, DL-060, DL-061, DL-062, DL-063, DL-064, DL-065, DL-066, DL-067, DL-068, DL-069, DL-070, DL-071, DL-072, DL-073, DL-074, DL-075, DL-076, DL-077)
- **CI-M-006-002** `traktor_nml/CLAUDE.md::file index`: Rows for review.py and for the gui/ subdirectory with when-to-read triggers, in the table shape the file already uses. (refs: DL-069)
- **CI-M-006-003** `traktor_nml/gui/CLAUDE.md::module index`: Indexes the package, states the nicegui boundary and which three modules sit above it, carries a paragraph stating that the wizard drives run_reconnection and the two cores directly - never parsing the CLI's key=value stdout - because Tier 1 needs structured data mid-run for live progress and the ambiguity table, and that subprocess-scraping remains available as the section 5 fallback if in-process integration fails, so a reader who meets scraping in section 5 can tell it was decided against as the data source rather than overlooked (DL-075), and records the two places design/reconnect-wizard/Specs.dc.html and sections 1 to 5 of docs/nicegui-gui-analysis.md disagree, with which governs each and why: Specs governs the six statuses, the seven filters and the keyboard map; section 4 governs run.io_bound, ui.log and the local_file_picker component. It also records that Specs.dc.html is a committed source and reconnect-wizard.html is the gitignored bundle seeded from it, and that scan-reconnect-candidates' dual tier membership is resolved in tests/test_gui_command_classification.py and is not re-derived here. (refs: DL-071, DL-072, DL-073, DL-075)
- **CI-M-006-004** `tests/CLAUDE.md::file index`: Rows for test_review_channel.py, test_write_refusal_predicate.py, test_reconnect_write_core.py, test_gui_review_model.py, test_gui_wizard_state.py and test_gui_view_boundary.py, each naming the property it guards. (refs: DL-069)
- **CI-M-006-005** `CLAUDE.md::subdirectory index`: Describes the wizard as a surface the package carries beside the CLI, in the existing table. (refs: DL-070)
- **CI-M-006-006** `README.md::install and usage`: The gui extra and how the wizard starts, in the user-facing voice the file already uses. (refs: DL-070)
- **CI-M-006-007** `TODO.md::guided repair review`: Describes the Guided Repair Review as the workflow the wizard is: a list-by-list review of unresolved and ambiguous entries that accepts or rejects proposed matches, records each override and writes a validated output collection - driven in-process against run_reconnection and the two reconnect cores, which is what lets the review happen while the run is still open rather than over a transcript after it (DL-075). The CSV exports are described as the path that remains for scripted use, not as a workaround being removed: rewrite-from-reconnect stays one call to the shared write core, so its --csv export keeps producing the same file from the same code, which is what the three unregenerated manifest cases pin (DL-066). The paragraph under Refined Fuzzy Matching that defers explicit-confirmation-before-writing to this section is left pointing here, because the wizard's ui.dialog is that confirmation step. (refs: DL-075, DL-066)

#### Code Changes

Not yet registered as code changes at plan-freeze time; the milestone's Code Intent entries above are what the executor workflow builds M-003 through M-006 from.


## Execution Waves

| Wave | Milestones |
|---|---|
| W-001 | M-001, M-002 |
| W-002 | M-003 |
| W-003 | M-004 |
| W-004 | M-005 |
| W-005 | M-006 |

Wave 1 (M-001, M-002) is implemented and committed at `f76c1f5`. Waves 2 through 5 (M-003 through M-006) are designed to Code Intent and remain to be built; M-006 appends this plan's twenty decisions (DL-058..DL-077) to `traktor_nml/README.md`'s decision log.

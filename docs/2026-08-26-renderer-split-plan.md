# Plan

## Overview

Split stdout flattening out of the two reconnect subcommands so one structured ReconnectResult feeds both the CLI renderer and a future NiceGUI review table (docs/nicegui-gui-analysis.md section 5 step 2).

**Approach**: traktor_nml/reconnect_run.py holds a printless core returning ReconnectResult, traktor_nml/reconnect_render.py turns that result into buffered stdout lines, stderr lines and an exit code, and commands/reconnect_cmd.py shrinks to argparse wiring whose handlers emit the render of the core call. Because rewrite-from-reconnect's stdout is produced inside rewrite.write_nml_safely, that function splits into a printless plan_and_write_nml returning WriteOutcome plus a thin printing wrapper; the wrapper's other two callers keep byte-identical output and the parity manifest cases for them are what proves it. tests/baselines/manifest.json is not regenerated and PARITY_BASELINE_SHA256 does not move. index_scan_roots writes its two diagnostics through an on_diagnostic callback that defaults to printing, so the core is printless without touching its other caller.

**Completion**: every character the reconnect commands put on stdout or stderr is emitted by reconnect_render, and stdout, stderr, exit code and written output bytes are each asserted against the recorded CLI contract. Renderer equality is necessary but not sufficient - it compares returned lines and cannot see a leaked stream write, so the CLI-level stderr assertion and the direct-core capture tests carry that half.

### Reconnect core/renderer boundary

[Diagram pending Technical Writer rendering: DIAG-001]

## Planning Context

### Decision Log

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-046 | A printless core returns one typed result per reconnect command and a renderer turns that result into stdout lines, stderr lines and an exit code; the argparse handler is emit(render(core(args))) | Tier 1 GUI needs the mapping, stats and ambiguity rows mid-run and as objects -> a core that prints cannot serve it and a transcript parsed after the fact arrives too late -> the flattening moves behind a render boundary the CLI and the GUI both sit above |
| DL-047 | write_nml_safely splits into a printless plan_and_write_nml returning WriteOutcome, with write_nml_safely retained as a thin printing wrapper over it | rewrite-from-reconnect stdout is produced inside write_nml_safely, not in the handler -> leaving it printing means the reconnect core still emits stdout and misses section 3.2 -> a reconnect-local write path would duplicate the read/parse/patch/write skeleton the package's own DL-019 in traktor_nml/README.md (splice_cmd/split_cmd read, parse and write through rewrite.py's helpers so both inherit its diagnostics and atomic write) exists to prevent - a package-log number, not this plan's DL-046, which is the printless-core/renderer decision -> extract once, keep the wrapper byte-identical, and let the manifest cases for rewrite and rewrite-from-collection-compare prove the extraction |
| DL-048 | WriteOutcome carries stats as None when the run failed before stats were collected, and carries both stats and error when it failed after | on the lxml path stats print before apply_and_write, so a text_patch_error emits the full stats block on stdout and then the error on stderr -> a single error flag cannot reproduce that ordering -> the presence of stats is itself the signal, and output_must_differ_from_input, input_not_found and xml_parse_error carry stats=None because they occur before any stats exist |
| DL-049 | The output_must_differ_from_input check stays at the top of plan_and_write_nml, ahead of parsing and ahead of the collect_patches/mutate_tree callback | the reconnect callback owns a 20-minute disk scan and writes the tag cache -> running it before the collision check would make a refused write cost a full scan -> the refusal must remain the first thing the function does, which also means a collision produces no ReconnectResult at all |
| DL-050 | warn_refutation_disabled moves out of the reconnect core into the renderer, while the fingerprint_dependency_missing warning becomes a field on the result | the refutation warning is a pure function of argv and the fingerprint warning is derived from probing the run -> only the second is knowledge the core discovers -> argv-derived text belongs above the core boundary and run-derived text belongs on the result, and the renderer emits the fingerprint line before the refutation line to preserve stderr order |
| DL-051 | The renderer returns buffered stdout and stderr line lists plus an exit code, and a single emit helper in the render module performs every print | section 3.2 asserts render_x(core_x(args)) equals the recorded stdout, which requires the renderer to be a value-returning function -> and the manifest captures stdout and stderr as separate streams, so buffering cannot reorder anything it observes -> commands/reconnect_cmd.py then contains no print call at all, making the anti-drift guard a grep rather than an AST walk |
| DL-052 | The core and renderer live in traktor_nml/reconnect_run.py and traktor_nml/reconnect_render.py, not under commands/ | commands/__init__.py imports every command module at CLI startup and commands/ is being reduced to argparse wiring -> a GUI importing the core through commands/ would drag every subparser with it -> the pair sits beside reconnect.py in the package root, and commands/ imports downward into it |
| DL-053 | ScanCancelled, VolumeIdentityError and _FingerprintUnavailable propagate out of plan_and_write_nml unchanged; the reconnect core converts the latter two into typed errors on its result and lets ScanCancelled escape | a cancelled scan must never return partial results because a short candidate list reads as a mostly-missing collection -> catching it at the write shell would turn a refusal into a plausible wrong answer -> only the two errors that already map to a printed key=value line and exit 2 become data |
| DL-054 | run_reconnection and both reconnect cores accept on_progress and cancel keyword arguments and forward them verbatim to index_scan_roots; both default to None and the argparse handlers pass neither | index_scan_roots (traktor_nml/diskscan.py:155) already accepts on_progress and cancel -> a core boundary that drops them forces a GUI to bypass the core and re-implement the pipeline to get live progress or a cancel token, which is exactly what DL-046 of this plan exists to prevent -> the parameters are threaded through the core with None defaults, so the CLI path is byte-identical while the GUI channel reaches the scan |
| DL-055 | The refutation-disabled message has one definition: _shared_args.refutation_disabled_line() returns the text, warn_refutation_disabled prints what it returns, and reconnect_render appends what it returns | No manifest case sets --no-refute for either reconnect command -> a second copy of the literal in reconnect_render would drift from the one in _shared_args without any oracle noticing -> the renderer calls a text-producing helper and the existing printing wrapper becomes a caller of the same helper, so drift is impossible rather than merely detectable |
| DL-056 | index_scan_roots gains an on_diagnostic keyword argument that receives each fully formatted diagnostic line; it defaults to None, in which case the function prints to stderr exactly as it does today. reconnect_run passes a collector, so the core writes to no stream and the lines reach the renderer in emission order | index_scan_roots emits two diagnostics directly to stderr - tag_reading_unavailable once at entry when mutagen is absent (traktor_nml/diskscan.py:183) and disk_scan_progress every progress_every files inside the walk (:211) - so a core that calls it writes to stderr no matter how carefully the rest of the core is written, and DL-046's printless-core property is false in exactly the case that matters, a real scan on a machine without mutagen -> the transport must be additive because index_scan_roots has a second production caller, discover_tracks_cmd.py, which has no manifest case and is therefore unpinned; a default-inert parameter leaves it byte-identical by construction rather than by test -> the callback receives the formatted line rather than structured fields, so the message text keeps exactly one definition, the same argument DL-055 makes for the refutation line -> ordering is preserved because the collector is an ordered list appended to at the point each line would have been printed, and the renderer emits the collected lines before the fingerprint and refutation warnings, which is the order the legacy pipeline produces them in |
| DL-057 | Buffered renderer equality is not accepted as evidence that the core is printless; the CLI-level stderr assertion is | render(core(args)) compares the lines a renderer RETURNS, so a stray print inside the core never enters the comparison and the equality test passes while the process still writes to the stream -> the only place a leak is observable is a real invocation, where stdout and stderr are captured from the process -> tests/test_baseline_parity.py therefore asserts stderr alongside stdout and exit code, which is free because the manifest already records a stderr field per case -> and because all twelve recorded stderr values are empty, that assertion is precisely a no-leak detector for every pinned path |

### Rejected Alternatives

| Alternative | Why Rejected |
|---|---|
| Leave write_nml_safely printing and give the reconnect core a seam only for the stats block | output_written and the stats block would still be emitted from inside the write shell, so the reconnect core would still write to stdout and rewrite-from-reconnect would miss section 3.2 rather than satisfying it (ref: DL-047) |
| Give rewrite-from-reconnect its own reconnect-local read/parse/patch/write path so write_nml_safely is untouched | it duplicates the skeleton write_nml_safely exists to prevent (the package's own DL-019 in traktor_nml/README.md (splice_cmd/split_cmd read, parse and write through rewrite.py's helpers so both inherit its diagnostics and atomic write); not this plan's DL-046), and a second copy of the collision refusal and the lxml/stdlib fork is exactly the drift the shared shell was built to stop (ref: DL-047) |
| Subprocess-scraping the CLI key=value stdout as the GUI's data source | Tier 1 needs structured data mid-run for live scan progress and an interactive ambiguous-match table; a parsed transcript exists only after the run finishes. It survives as the section 5 fallback only (ref: DL-046) |
| Renderers that print directly rather than returning line lists | section 3.2 asserts equality between a renderer's output and recorded stdout, which needs a value-returning function; a printing renderer forces every test through capsys and leaves print calls scattered across the layer (ref: DL-051) |
| Regenerating tests/baselines/manifest.json when a case diverges | the manifest is the behavioural contract, not a snapshot; a commit that needs it updated is by definition a behaviour change, which this split is not (ref: DL-047) |
| Placing the core and renderer under traktor_nml/commands/ | commands/__init__.py imports every command module at CLI startup, so a GUI importing the core through commands/ drags every subparser with it (ref: DL-052) |
| Returning the scan diagnostics in the stats dict index_scan_roots already fills | stats is an unordered mapping accumulated across the whole walk, so it cannot express that tag_reading_unavailable precedes the first disk_scan_progress line or that the progress lines are interleaved with the scan in file order; the legacy stderr transcript is a sequence and only a sequence reproduces it (ref: DL-056) |
| Wrapping the core in contextlib.redirect_stderr and re-emitting what it captured | it makes the core printless in appearance only - the writes still happen and are merely intercepted - so the anti-drift guard would pass over a core that prints, and it captures unrelated writes from any library the scan touches into the reconnect transcript. It also does nothing for a GUI, which needs the diagnostics as they occur, not as a blob at the end (ref: DL-056, DL-057) |
| Asserting only render(core(args)) equality and treating the core as printless because the renderer output matches | a returned line list and a written stream are different things; a core that prints to stderr and returns the correct lines passes every equality test while doubling its own output at the CLI. Only a captured invocation can see it (ref: DL-057) |

### Constraints

- tests/baselines/manifest.json is not regenerated. Non-regeneration is the parity check (section 3.1 rule 2).
- PARITY_BASELINE_SHA256 in tests/test_parity_baseline.py does not move. It is the authoritative pin asserted by pytest, independent of the parity-baseline tag.
- stdout, stderr, exit codes and written output bytes stay identical for scan-reconnect-candidates, rewrite-from-reconnect, rewrite and rewrite-from-collection-compare. Typed errors keep exit code 2.
- The CLI is fully usable at every commit on the refactor branch. Rollback is an ordered revert - M-003, then M-002, then M-001 - not a per-milestone one: M-002's rewrite_from_reconnect calls plan_and_write_nml, which M-001 introduces, so M-001 cannot be reverted while M-002 stands. Reverted in that order the whole change is still the single discrete 'revert the renderer split' step section 5 asks for.
- No import from traktor_nml/gui/ appears in commands/ or cli.py, and no top-level nicegui import appears anywhere reachable from commands/__init__.py, which imports every command module at CLI startup.
- Every new guard test is demonstrated failing when its invariant breaks, and the test says so - a guard only seen to pass is not a guard.
- Matching, refutation and the confidence ladder are untouched; traktor_nml/reconnect.py keeps its current behaviour and signatures.
- index_scan_roots keeps its current default behaviour: with on_diagnostic unset it prints tag_reading_unavailable and disk_scan_progress to stderr exactly as it does today. discover_tracks_cmd.py, its other production caller, is not modified and has no manifest case, so default-inertness is the only thing keeping it unchanged.
- Completion is defined as: every character the reconnect commands put on stdout or stderr is emitted by reconnect_render, and stdout, stderr, exit code and written output bytes are each asserted against the recorded CLI contract for every manifest case. A renderer equality test alone does not satisfy this.
- Other sessions commit to this repo in parallel; git fetch and check HEAD before committing.
- A full scan-reconnect-candidates run against the real corpus takes about 20 minutes, so verification runs on the fixture corpus rather than the corpus.

### Known Risks

- **The write-shell extraction touches rewrite and rewrite-from-collection-compare, which are not the subject of this step, so a mistake there breaks two working commands.**: The manifest already holds cases for both. They run unaltered against an unregenerated manifest, so any drift in their stdout, stderr, exit code or output bytes fails the suite rather than shipping.
- **On the lxml path the stats block prints before apply_and_write, so a text_patch_error emits stats on stdout and then the error on stderr. Collapsing the outcome into a single error flag silently reorders that.**: WriteOutcome carries stats and error together and stats is None only when no stats existed; tests/test_write_shell_split.py asserts the pairing and is shown failing when the order is inverted.
- **The fingerprint branch is the code that emits to stderr mid-core and is the one branch the parity oracle cannot prove unchanged - no manifest case passes --fingerprint, and the three fingerprint tests skip when pyacoustid and fpcalc are absent.**: The equivalence module monkeypatches traktor_nml.reconnect_run.fingerprint_unavailable_reason to return a fixed reason, so the warn path is exercised without pyacoustid, fpcalc or chromaprint, asserting the reason reaches ReconnectResult.warnings and renders ahead of the refutation line. That stub replaces only the probe; the separate fingerprint_key_provider-is-None path, which raises _FingerprintUnavailable rather than warning, is left as the defensive import bound it and gets its own test that sets traktor_nml.reconnect_run.fingerprint_key_provider to None and asserts the raise. The two failure modes are therefore proved distinct rather than one masking the other. The documented manifest gap for the fingerprint tier stays open and is not closed by this work.
- **Hoisting the reconnection out of the collect_patches callback to make the core easier to call would run a 20-minute scan and write the tag cache before the output-collision refusal fires.**: The refusal stays the first statement of plan_and_write_nml and the reconnection stays inside the callback; a test asserts a colliding output path produces no ReconnectResult.
- **Buffering all output until the run ends means csv_written no longer appears while a long scan is still running, changing what a user watching a live run sees.**: Accepted, and the live-feedback channel is reachable from the core: run_reconnection and both cores take on_progress and cancel and forward them to index_scan_roots (DL-054, CI-M-002-002), so a caller that wants progress while the scan runs has one that does not depend on print ordering. The manifest captures stdout and stderr as separate completed streams so parity is unaffected, and the CLI passes neither argument, keeping today's behaviour exactly.
- **Two stderr emissions exist per run and their relative order is observable: the fingerprint dependency warning precedes the refutation-disabled warning.**: Both renderers emit warnings in that fixed order and a unit test asserts it, because no manifest case sets both switches together.
- **Splitting run_reconnection could cause volume identities to be resolved twice, once for the fingerprint tier and once for LOCATION re-encoding.**: Identity resolution stays a single up-front pass inside run_reconnection whose result both consumers read, and the mapping is a local of that one function.
- **A plan whose decisions restart at DL-001 collides with the package log and leaks wrong citations into repo code. This has already happened twice.**: docs/traktor_nml_tool_execution_plan.md minted its own DL-001..DL-0NN and its doc_diffs put DL-002 and DL-011 into tests/conftest.py and tests/test_baseline_parity.py, where they resolved to nothing until this plan cleared them; an earlier review recorded the same clash being raised and not structurally fixed. This plan's twelve decisions are therefore numbered in the package sequence (DL-046..DL-057) rather than a second one, so a citation copied out of an intent into repo code resolves to the entry it means, and M-003's resolve check makes the property mechanical rather than a matter of reviewer vigilance.
- **index_scan_roots is shared with discover_tracks_cmd.py, which has no manifest case, so a change to its stderr behaviour would not be caught by the oracle.**: on_diagnostic defaults to None and the print calls stay on that path, so discover-tracks is untouched by construction rather than by coverage. A unit test calls index_scan_roots with no on_diagnostic and asserts the legacy lines still reach stderr, and the same test with a collector asserts stderr is empty, so the default is pinned in both directions.
- **The manifest cannot pin the two scan diagnostics at all: no recorded case runs without mutagen and no fixture is large enough to cross the 500-file progress threshold, and regenerating to add such cases is forbidden.**: The manifest's role here is the no-leak assertion - all twelve recorded stderr values are empty, so asserting stderr proves no reconnect path writes to the stream. Content and ordering of the two diagnostics are pinned instead by direct-core capture tests that force each condition (HAS_MUTAGEN patched False; progress_every lowered so a small fixture crosses it). The two mechanisms are complementary and neither substitutes for the other. The documented manifest gaps stay open and are not closed by this work.

## Invisible Knowledge

### System

The reconnect path runs in three layers. reconnect_run.py owns the pipeline and returns objects; reconnect_render.py owns every character that reaches a stream; commands/reconnect_cmd.py owns only argparse. rewrite.py's shared write shell splits the same way: plan_and_write_nml returns a WriteOutcome and write_nml_safely is the printing wrapper the other two write commands still call. The reason for the split is that a GUI review table needs the mapping and the ambiguity rows as objects while the run is still going, and a key=value transcript only exists once the run is over. The parity manifest is what makes the split safe: it is a behavioural contract, so the refactor is correct precisely when the manifest and its SHA pin do not have to change.

### Invariants

- The output-collision refusal is the first thing plan_and_write_nml does, ahead of parsing and ahead of the caller's callback, so a refused write never costs a 20-minute scan or a tag-cache write.
- WriteOutcome.stats is None only when the attempt ended before any stats existed; a populated stats alongside a populated error means the stats block belongs on stdout ahead of the error on stderr.
- A cancelled scan raises ScanCancelled rather than returning partial results, because a short candidate list is indistinguishable from a complete one and would report most of the collection as missing. Nothing on the core or write path catches it.
- Volume identities are resolved once per run and reused by both the fingerprint key provider and the LOCATION re-encoding.
- The tag cache and the ambiguity CSV are written even under --dry-run, because neither is the command's declared output.
- stdout order for rewrite-from-reconnect is csv_written, then the stats and sample_matches block, then output_written. stderr order is the fingerprint dependency warning, then the refutation-disabled warning, then any error.
- commands/reconnect_cmd.py contains no print call and no stream write at all; that is the form the anti-drift guard checks.
- Argv-derived text (the refutation-disabled warning) is emitted by the renderer; run-derived text (the fingerprint dependency reason) travels on the result as data.
- The full-suite baseline is 191 passed and 3 skipped, the 3 skips being the fingerprint tier (pyacoustid and fpcalc absent). Every acceptance criterion that says 'pytest passes' means that count: a test that silently disappears or newly skips fails the criterion as surely as a red test, so the counts are read off the pytest summary line, not just the exit code.
- This plan's decisions are numbered in the package sequence, not a second one. traktor_nml/README.md's decision log runs DL-046..DL-045 at planning time, so this plan's twelve decisions are DL-046..DL-057 and M-003 appends all twelve to that log. A DL number therefore means the same thing in this plan, in the package log, and in any repo file that cites it, which is what makes a citation copied out of an intent into repo code resolve to the entry it means. Precedent: docs/2026-08-24-build-playlist-plan.md numbered its own DL-024..DL-039 continuing the package sequence from its then high-water mark of DL-023, had its M-003 append all sixteen, and made 'the two namespaces never sharing a number' an acceptance criterion. Pre-existing package entries this plan cites - DL-016, DL-019, DL-028, DL-040, DL-045 - are unchanged; DL-019 in particular is the rule that commands read, parse and write through rewrite.py's shared helpers. The block is re-read against HEAD at commit time and shifted whole if another session has taken numbers.

### Tradeoffs

- The write shell is refactored even though it serves three commands and only two of them are in scope, because the alternative was duplicating the read/parse/patch/write skeleton the package's own DL-019 in traktor_nml/README.md (splice_cmd/split_cmd read, parse and write through rewrite.py's helpers so both inherit its diagnostics and atomic write) exists to prevent (a package-log number; this plan's own DL-046 is the printless-core/renderer decision). The wider blast radius is paid for by the manifest cases for rewrite and rewrite-from-collection-compare, which prove the extraction rather than anyone asserting it.
- Output is buffered until the run completes, trading live print feedback for a renderer that returns values and can be asserted against recorded stdout. Live feedback belongs to the on_progress callback instead.
- The fingerprint branch gets unit tests with a stubbed probe rather than an oracle case, because adding a --fingerprint manifest case requires a reviewed re-tag. That documented gap stays open.
- The four reconnect manifest cases all pass --match-confidence filename, so the strict, normal, loose, bare_name and bare_name_in_folder tiers are unproven by the oracle for these commands; the split touches none of that code, which is why the gap is tolerable here.

## Milestones

### Milestone 1: Printless write shell

**Files**: traktor_nml/rewrite.py, tests/test_write_shell_split.py

**Requirements**:

- plan_and_write_nml performs the read/parse/patch/write sequence and returns a WriteOutcome without writing to stdout or stderr;write_nml_safely is a printing wrapper whose output and exit codes are unchanged for rewrite and rewrite-from-collection-compare;the output-collision refusal remains the first action taken and precedes both parsing and the caller callback;exceptions raised inside collect_patches or mutate_tree propagate to the caller of plan_and_write_nml;format_stats_and_samples returns the stats and sample_matches block as lines and print_stats_and_samples prints exactly those lines

**Acceptance Criteria**:

- pytest passes with tests/baselines/manifest.json unmodified and PARITY_BASELINE_SHA256 unchanged
- and the run reports at least the baseline 191 passed and no more than the baseline 3 skipped (the 3 being the fingerprint tier)
- so a test that silently disappears or newly skips fails this criterion as surely as a red test;the rewrite and rewrite-from-collection-compare manifest cases pass unaltered and are the proof of byte-identical stdout;a WriteOutcome from a text_patch_error carries populated stats and a non-empty error so the stats block precedes the error line;a WriteOutcome from an output collision carries stats of None;grep finds no print call inside plan_and_write_nml;the guard test fails when write_nml_safely emits the stats block after the error line;the stats and sample_matches block has one definition that both the printing wrapper and the reconnect renderer call

**Tests**:

- tests/test_write_shell_split.py

#### Code Intent

- **CI-M-001-001** `traktor_nml/rewrite.py::WriteOutcome`: A frozen dataclass describing one attempt at the read/parse/patch/write sequence. Fields: stats (dict of str to int, or None when the attempt ended before any stats existed), samples (the sample-match tuples, or None), error (the key=value text destined for stderr, or None), written_path (the Path actually written, or None on a dry run or a failure) and exit_code (0 or 2). stats being None rather than empty is the signal that no stats block belongs in the output at all, which is what separates an output collision from a run that collected stats and then failed to write. (refs: DL-047, DL-048)
- **CI-M-001-002** `traktor_nml/rewrite.py::plan_and_write_nml`: Takes the same parameters as the printing wrapper (input_path, output_path, dry_run, collect_patches, mutate_tree, extra_inputs) and returns a WriteOutcome. It resolves the output against input_path and extra_inputs first and returns the output_must_differ_from_input outcome with stats of None before touching the filesystem or the callbacks. On the lxml path it reads and parses, returns the read error as an outcome with stats of None, otherwise calls collect_patches, keeps the returned stats and samples on the outcome, and when not dry_run applies the patches and records written_path; a UnicodeDecodeError or ValueError from apply_and_write becomes the text_patch_error outcome with the collected stats still populated. The stdlib path maps FileNotFoundError and XML_PARSE_ERROR to their outcomes, calls mutate_tree, and writes through write_traktor_xml when not dry_run. It performs no I/O to stdout or stderr and catches nothing raised by the two callables. (refs: DL-047, DL-048, DL-049, DL-053)
- **CI-M-001-003** `traktor_nml/rewrite.py::write_nml_safely`: Delegates to plan_and_write_nml and turns the outcome into the stream writes the CLI contract requires: print_stats_and_samples when stats is not None, then the error to stderr when error is not None, then the output_written line to stdout when written_path is set, returning exit_code. Its signature, its docstring contract and its byte-level output for rewrite_cmd and compare_cmd are unchanged. (refs: DL-047, DL-048)
- **CI-M-001-004** `tests/test_write_shell_split.py`: Unit tests over plan_and_write_nml that cover what the manifest cannot reach. An output-collision case asserts stats is None and exit_code is 2. A text_patch_error case (a collect_patches returning a patch that apply_text_patches rejects) asserts stats is populated alongside the error, and a companion assertion demonstrates that rendering the error before the stats produces output the recorded ordering rejects, so the ordering guard is one that has been seen to fail. A callback-raises case asserts a RuntimeError from collect_patches leaves plan_and_write_nml and reaches the caller. A no-output case asserts no captured stdout or stderr for every outcome the function can return. Each test names in its docstring the invariant it breaks to prove it guards. (refs: DL-048, DL-049, DL-053)
- **CI-M-001-005** `traktor_nml/rewrite.py::format_stats_and_samples`: Returns the stats and sample_matches block as a list of lines: one key=value line per stats entry in insertion order, then the sample_matches header and the label, matched_by, before and after lines for each of the first limit samples. print_stats_and_samples prints exactly these lines and nothing else, so one definition of the block serves both the printing wrapper and reconnect_render.render_rewrite_from_reconnect, which composes the same block into its buffered stdout without restating the format. (refs: DL-047, DL-051)

#### Code Changes

**CC-M-001-001** (traktor_nml/rewrite.py) - implements CI-M-001-001

**Code:**

```diff
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -392,6 +392,25 @@ def apply_and_write(source_bytes: bytes, patches: list[ElemPatch], output: Path)
     write_bytes_atomically(output, patched.encode("utf-8"))
 
 
+@dataclass(frozen=True)
+class WriteOutcome:
+    """One attempt at the read/parse/patch/write sequence, returned
+    rather than printed so a caller other than the CLI - the reconnect
+    renderer, a future GUI - can read it as data.
+
+    stats is None rather than empty when the attempt ended before any
+    stats existed - the signal that separates an output collision, which
+    has no stats block at all, from a run that collected stats and then
+    failed to write.
+    """
+
+    stats: Optional[dict[str, int]]
+    samples: Optional[list[tuple[str, str, str, str]]]
+    error: Optional[str]
+    written_path: Optional[Path]
+    exit_code: int
+
+
 def print_stats_and_samples(
     stats: dict[str, int], samples: list[tuple[str, str, str, str]] | None, limit: int = 10
 ) -> None:
```

**Documentation:**

```diff
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -406,8 +406,13 @@ class WriteOutcome:
     failed to write.
     """
 
     stats: Optional[dict[str, int]]
     samples: Optional[list[tuple[str, str, str, str]]]
+    # error and written_path are never both non-None: a run either fails
+    # (error set) or writes (written_path set), and a dry run and a
+    # collision both leave both fields None.
     error: Optional[str]
     written_path: Optional[Path]
+    # 0 on success, 2 on any of the four typed failures: input_not_found,
+    # xml_parse_error, output_must_differ_from_input, or text_patch_error.
     exit_code: int

```


**CC-M-001-002** (traktor_nml/rewrite.py) - implements CI-M-001-005

**Code:**

```diff
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -411,18 +411,29 @@ class WriteOutcome:
     exit_code: int
 
 
-def print_stats_and_samples(
+def format_stats_and_samples(
     stats: dict[str, int], samples: list[tuple[str, str, str, str]] | None, limit: int = 10
-) -> None:
-    for key, value in stats.items():
-        print(f"{key}={value}")
+) -> list[str]:
+    """The stats and sample_matches block as lines rather than prints, so
+    print_stats_and_samples and reconnect_render.render_rewrite_from_reconnect
+    compose the same block into their own output instead of each
+    restating its format."""
+    lines = [f"{key}={value}" for key, value in stats.items()]
     if samples:
-        print("sample_matches:")
+        lines.append("sample_matches:")
         for label, before, after, matched_by in samples[:limit]:
-            print(f"- {label}")
-            print(f"  matched_by={matched_by}")
-            print(f"  before={before}")
-            print(f"  after={after}")
+            lines.append(f"- {label}")
+            lines.append(f"  matched_by={matched_by}")
+            lines.append(f"  before={before}")
+            lines.append(f"  after={after}")
+    return lines
+
+
+def print_stats_and_samples(
+    stats: dict[str, int], samples: list[tuple[str, str, str, str]] | None, limit: int = 10
+) -> None:
+    for line in format_stats_and_samples(stats, samples, limit):
+        print(line)
 
 
 # Callables a caller of write_nml_safely supplies:
```

**Documentation:**

```diff
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -418,6 +418,9 @@ def format_stats_and_samples(
     lines = [f"{key}={value}" for key, value in stats.items()]
     if samples:
         lines.append("sample_matches:")
+        # limit applies only to sample_matches, never to the stats block
+        # above it: both callers of format_stats_and_samples print the
+        # full stats block and only ever truncate sample_matches.
         for label, before, after, matched_by in samples[:limit]:
             lines.append(f"- {label}")
             lines.append(f"  matched_by={matched_by}")

```


**CC-M-001-003** (traktor_nml/rewrite.py) - implements CI-M-001-002

**Code:**

```diff
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -443,6 +443,55 @@ CollectPatchesFn = Callable[[ET.Element], tuple[list[ElemPatch], dict[str, int],
 MutateTreeFn = Callable[[ET.Element, bool], tuple[dict[str, int], list]]
 
 
+def plan_and_write_nml(
+    input_path: Path,
+    output_path: Path,
+    dry_run: bool,
+    collect_patches: CollectPatchesFn,
+    mutate_tree: MutateTreeFn,
+    extra_inputs: tuple[Path, ...] = (),
+) -> WriteOutcome:
+    """Read, parse, patch, and write once, returning a WriteOutcome
+    rather than printing. Resolves output_path against
+    input_path and extra_inputs before touching the filesystem or either
+    callback, so the output-collision refusal precedes both parsing and
+    the caller's own collect_patches/mutate_tree. Raises nothing
+    collect_patches or mutate_tree themselves raise; only
+    FileNotFoundError, the XML parse error, and the two write-time
+    exceptions apply_and_write can raise are caught and folded into the
+    outcome.
+    """
+    if output_path.resolve() in {input_path.resolve(), *(p.resolve() for p in extra_inputs)}:
+        return WriteOutcome(None, None, "output_must_differ_from_input", None, 2)
+
+    if HAS_LXML:
+        read_result = read_and_parse_source(input_path)
+        if read_result.error is not None:
+            return WriteOutcome(None, None, read_result.error, None, 2)
+        source_bytes, root = read_result.source_bytes, read_result.root
+        patches, stats, samples = collect_patches(root)
+        if not dry_run:
+            try:
+                apply_and_write(source_bytes, patches, output_path)
+            except (UnicodeDecodeError, ValueError) as exc:
+                return WriteOutcome(stats, samples, f"text_patch_error={exc}", None, 2)
+            return WriteOutcome(stats, samples, None, output_path, 0)
+        return WriteOutcome(stats, samples, None, None, 0)
+
+    try:
+        tree = parse_xml(input_path)
+    except FileNotFoundError:
+        return WriteOutcome(None, None, f"input_not_found={input_path.as_posix()}", None, 2)
+    except XML_PARSE_ERROR as exc:
+        return WriteOutcome(None, None, f"xml_parse_error={input_path.as_posix()}: {exc}", None, 2)
+    root = tree.getroot()
+    stats, samples = mutate_tree(root, dry_run)
+    if not dry_run:
+        write_traktor_xml(root, output_path, write_bytes=write_bytes_atomically)
+        return WriteOutcome(stats, samples, None, output_path, 0)
+    return WriteOutcome(stats, samples, None, None, 0)
+
+
 def write_nml_safely(
     input_path: Path,
     output_path: Path,
```

**Documentation:**

```diff
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -448,4 +448,8 @@ def plan_and_write_nml(
     outcome.
     """
     if output_path.resolve() in {input_path.resolve(), *(p.resolve() for p in extra_inputs)}:
+        # Checked before parsing and before either callback runs: the
+        # reconnect callback owns a long disk scan, and running it ahead
+        # of this refusal would make a refused write cost the whole scan
+        # instead of returning immediately.
         return WriteOutcome(None, None, "output_must_differ_from_input", None, 2)

```


**CC-M-001-004** (traktor_nml/rewrite.py) - implements CI-M-001-003

**Code:**

```diff
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -506,41 +506,17 @@ def write_nml_safely(
     extra_inputs (existing tool convention). Both existing write commands
     (rewrite, rewrite-from-collection-compare) are expressed as callers of
     this helper, one supplying collect_patches for the lxml path and
-    mutate_tree for the stdlib fallback.
+    mutate_tree for the stdlib fallback. Delegates to plan_and_write_nml
+    and turns the returned WriteOutcome into the same stream writes this
+    contract requires, in that fixed order.
     """
-    if output_path.resolve() in {input_path.resolve(), *(p.resolve() for p in extra_inputs)}:
-        print("output_must_differ_from_input", file=sys.stderr)
-        return 2
-
-    if HAS_LXML:
-        read_result = read_and_parse_source(input_path)
-        if read_result.error is not None:
-            print(read_result.error, file=sys.stderr)
-            return 2
-        source_bytes, root = read_result.source_bytes, read_result.root
-        patches, stats, samples = collect_patches(root)
-        print_stats_and_samples(stats, samples)
-        if not dry_run:
-            try:
-                apply_and_write(source_bytes, patches, output_path)
-            except (UnicodeDecodeError, ValueError) as exc:
-                print(f"text_patch_error={exc}", file=sys.stderr)
-                return 2
-            print(f"output_written={output_path.as_posix()}")
-        return 0
-
-    try:
-        tree = parse_xml(input_path)
-    except FileNotFoundError:
-        print(f"input_not_found={input_path.as_posix()}", file=sys.stderr)
-        return 2
-    except XML_PARSE_ERROR as exc:
-        print(f"xml_parse_error={input_path.as_posix()}: {exc}", file=sys.stderr)
-        return 2
-    root = tree.getroot()
-    stats, samples = mutate_tree(root, dry_run)
-    print_stats_and_samples(stats, samples)
-    if not dry_run:
-        write_traktor_xml(root, output_path, write_bytes=write_bytes_atomically)
-        print(f"output_written={output_path.as_posix()}")
-    return 0
+    outcome = plan_and_write_nml(
+        input_path, output_path, dry_run, collect_patches, mutate_tree, extra_inputs
+    )
+    if outcome.stats is not None:
+        print_stats_and_samples(outcome.stats, outcome.samples)
+    if outcome.error is not None:
+        print(outcome.error, file=sys.stderr)
+    if outcome.written_path is not None:
+        print(f"output_written={outcome.written_path.as_posix()}")
+    return outcome.exit_code
```

**Documentation:**

```diff
--- a/traktor_nml/rewrite.py
+++ b/traktor_nml/rewrite.py
@@ -519,6 +519,10 @@ def write_nml_safely(
     outcome = plan_and_write_nml(
         input_path, output_path, dry_run, collect_patches, mutate_tree, extra_inputs
     )
+    # Prints in one fixed order: the stats/samples block when stats was
+    # collected, then the error line when present, then output_written=
+    # when a write happened. tests/baselines/manifest.json's recorded
+    # reconnect cases are the oracle that pins this order byte-for-byte.
     if outcome.stats is not None:
         print_stats_and_samples(outcome.stats, outcome.samples)
     if outcome.error is not None:

```


**CC-M-001-005** (tests/test_write_shell_split.py) - implements CI-M-001-004

**Code:**

```diff
--- /dev/null
+++ b/tests/test_write_shell_split.py
@@ -0,0 +1,158 @@
+"""Unit tests over plan_and_write_nml covering what the byte-parity
+manifest cannot reach: the printless core's own outcomes rather than the
+stream writes a caller layers on top of it.
+"""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+import pytest
+
+from traktor_nml.model import ElemPatch
+from traktor_nml.rewrite import WriteOutcome, plan_and_write_nml, write_nml_safely
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
+def _no_op_collect(root):
+    return [], {"x": 1}, []
+
+
+def _no_op_mutate(root, dry_run):
+    return {"x": 1}, []
+
+
+def test_output_collision_carries_no_stats(tmp_path: Path) -> None:
+    """A collision refusal is a run that never reached collect_patches or
+    mutate_tree at all, so stats being None (rather than an empty dict)
+    is the signal there is no stats block to render. Negative case: a
+    run that does reach collect_patches produces a populated dict, not
+    None, so the two outcomes are distinguishable by type - proved here
+    by running both against the same input and comparing them, rather
+    than trusting the docstring that stats is None only for a collision."""
+    input_path = tmp_path / "a.nml"
+    _write_minimal_nml(input_path)
+
+    collision = plan_and_write_nml(input_path, input_path, False, _no_op_collect, _no_op_mutate)
+    completed = plan_and_write_nml(
+        input_path, tmp_path / "out.nml", False, _no_op_collect, _no_op_mutate
+    )
+
+    assert collision.stats is None
+    assert collision.exit_code == 2
+    assert collision.error == "output_must_differ_from_input"
+
+    # The negative case: had a collision instead produced {} rather than
+    # None, it would be indistinguishable in kind from a completed run's
+    # stats - this is what actually tells them apart.
+    assert completed.stats is not None
+    assert type(collision.stats) is not type(completed.stats)
+
+
+def test_text_patch_error_keeps_the_stats_it_already_collected(tmp_path: Path) -> None:
+    """A patch whose original attributes cannot be located in the source
+    text raises inside apply_and_write, after collect_patches already
+    returned stats - the outcome must keep those stats rather than
+    discarding them, or a caller that prints the stats block ahead of the
+    error would have nothing to print. Negative case: a WriteOutcome
+    built the way a prior draft built one for every write-time exception
+    - WriteOutcome(None, None, error, None, 2), discarding the stats
+    collect_patches had already returned - is constructed here from the
+    same error and exit_code and shown to carry stats that differ from
+    (and are less informative than) the real outcome's, which is what
+    actually distinguishes the correct behaviour from the discarding one
+    rather than only asserting the correct side.
+    """
+    input_path = tmp_path / "a.nml"
+    _write_minimal_nml(input_path)
+    output_path = tmp_path / "out.nml"
+
+    bogus_patch = ElemPatch(
+        sourceline=1,
+        tag_name="LOCATION",
+        locator=(("VOLUME", "does-not-exist"),),
+        changes=[("VOLUME", "does-not-exist", "X")],
+    )
+
+    def collect_patches(root):
+        return [bogus_patch], {"collection_locations_rewritten": 1}, []
+
+    outcome = plan_and_write_nml(input_path, output_path, False, collect_patches, _no_op_mutate)
+
+    assert outcome.stats == {"collection_locations_rewritten": 1}
+    assert outcome.error is not None and outcome.error.startswith("text_patch_error=")
+    assert outcome.written_path is None
+    assert outcome.exit_code == 2
+
+    # The prior-draft outcome, rebuilt here from the real one's own error
+    # and exit_code: had plan_and_write_nml discarded stats on every
+    # write-time exception the way that draft did, this is exactly what
+    # it would have returned instead. Demonstrating it lets the next
+    # assertion catch the regression rather than only asserting the
+    # collected-stats side of it.
+    discarded_stats_outcome = WriteOutcome(None, None, outcome.error, None, outcome.exit_code)
+
+    assert discarded_stats_outcome.stats is None
+    assert discarded_stats_outcome.stats != outcome.stats
+
+
+def test_callback_exception_reaches_the_caller(tmp_path: Path) -> None:
+    """collect_patches/mutate_tree are the caller's own callables; a
+    plain exception from either must propagate rather than being folded
+    into a WriteOutcome, the way an input error is. Negative case: a
+    write-time exception from apply_and_write (text_patch_error) is the
+    contrasting behaviour - plan_and_write_nml folds that one into a
+    WriteOutcome instead of raising, so the two failure classes are
+    proved to be handled differently rather than everything simply
+    propagating."""
+    input_path = tmp_path / "a.nml"
+    _write_minimal_nml(input_path)
+    output_path = tmp_path / "out.nml"
+
+    def collect_patches(root):
+        raise RuntimeError("boom")
+
+    with pytest.raises(RuntimeError, match="boom"):
+        plan_and_write_nml(input_path, output_path, False, collect_patches, _no_op_mutate)
+
+    bogus_patch = ElemPatch(1, "LOCATION", (("VOLUME", "nope"),), [("VOLUME", "nope", "X")])
+    folded = plan_and_write_nml(
+        input_path, output_path, False, lambda root: ([bogus_patch], {}, []), _no_op_mutate
+    )
+    assert folded.error is not None and folded.error.startswith("text_patch_error=")
+
+
+def test_no_outcome_writes_to_either_stream(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
+    """plan_and_write_nml is printless for every outcome it can return:
+    collision, write success, and write-time text_patch_error alike.
+    Negative case: the printing wrapper write_nml_safely, run over the
+    same collision input, does write to stderr - proving capsys is
+    actually capturing output here rather than the silence above being
+    an artifact of a misconfigured test."""
+    input_path = tmp_path / "a.nml"
+    _write_minimal_nml(input_path)
+
+    plan_and_write_nml(input_path, input_path, False, _no_op_collect, _no_op_mutate)
+    plan_and_write_nml(input_path, tmp_path / "out1.nml", False, _no_op_collect, _no_op_mutate)
+
+    bogus_patch = ElemPatch(1, "LOCATION", (("VOLUME", "nope"),), [("VOLUME", "nope", "X")])
+    plan_and_write_nml(
+        input_path, tmp_path / "out2.nml", False, lambda root: ([bogus_patch], {}, []), _no_op_mutate
+    )
+
+    captured = capsys.readouterr()
+    assert captured.out == ""
+    assert captured.err == ""
+
+    write_nml_safely(input_path, input_path, False, _no_op_collect, _no_op_mutate)
+    assert capsys.readouterr().err != ""

```

**Documentation:**

```diff
--- a/tests/test_write_shell_split.py
+++ b/tests/test_write_shell_split.py
@@ -1,7 +1,19 @@
 """Unit tests over plan_and_write_nml covering what the byte-parity
 manifest cannot reach: the printless core's own outcomes rather than the
-stream writes a caller layers on top of it.
+stream writes a caller layers on top of it. Of the four guards below,
+only test_no_outcome_writes_to_either_stream carries a companion proof
+in this file: it runs the printing wrapper write_nml_safely over the
+same collision input and shows stderr is non-empty, which is what
+rules out the printlessness assertions above it being an artifact of a
+misconfigured capsys rather than real silence. The other three assert
+what plan_and_write_nml returns on a collision, a write-time
+text_patch_error, and a callback exception, without a comparable
+proof here that the assertion would catch a broken implementation.
 """

 from __future__ import annotations
@@ -17,19 +29,29 @@ from traktor_nml.rewrite import WriteOutcome, plan_and_write_nml, write_nml_sa


 def _write_minimal_nml(path: Path) -> None:
+    """A COLLECTION with no entries - enough for plan_and_write_nml to
+    parse and reach either callback; the tests below don't need entries,
+    only a valid document to read, patch and (sometimes) write."""
     path.write_text(
         '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
         '<NML VERSION="19">\n'
         '  <COLLECTION ENTRIES="0">\n'
         '  </COLLECTION>\n'
         '</NML>\n',
         encoding="utf-8",
     )


 def _no_op_collect(root):
+    """Minimal collect_patches returning fixed patches/stats/samples:
+    isolates plan_and_write_nml's write-shell behaviour (collision
+    refusal, write-time error handling, printlessness) from patch
+    computation, which these tests are not exercising."""
     return [], {"x": 1}, []


 def _no_op_mutate(root, dry_run):
+    """Minimal mutate_tree returning fixed stats, ignoring dry_run:
+    isolates the write shell the same way _no_op_collect does, for the
+    stdlib-fallback path."""
     return {"x": 1}, []

```


### Milestone 2: Reconnect core and renderer

**Files**: traktor_nml/reconnect_run.py, traktor_nml/reconnect_render.py, traktor_nml/commands/reconnect_cmd.py, traktor_nml/commands/_shared_args.py, tests/test_reconnect_render_equivalence.py, tests/test_reconnect.py, traktor_nml/shared_args.py, traktor_nml/diskscan.py, tests/test_scan_diagnostics.py

**Requirements**:

- scan_reconnect_candidates and rewrite_from_reconnect return typed results carrying mapping stats ambiguity rows old records warnings and typed errors;ScanReconnectResult and RewriteReconnectResult are defined dataclasses with stated field semantics not implicit tuples;neither core function writes to stdout or stderr;run_reconnection and both cores accept on_progress and cancel and forward them to index_scan_roots with None defaults;render functions accept a result and return buffered stdout lines stderr lines and an exit code;the refutation-disabled message text has exactly one definition in traktor_nml/shared_args.py and both the printing wrapper in commands/_shared_args.py and the renderer read it from there;neither reconnect_run.py nor reconnect_render.py imports anything from commands/;ReconnectResult is a frozen dataclass;a FpcalcSession opened for the fingerprint tier is terminated inside run_reconnection before it returns, on every path resolve_reconnection can take;the two argparse handlers consist of emit applied to render applied to core;volume identities are resolved once per run and reused by the fingerprint tier and the LOCATION re-encoding;ScanCancelled escapes the core rather than becoming a result field
;index_scan_roots accepts an on_diagnostic callback that defaults to None and prints to stderr when unset;run_reconnection passes a collector so no scan diagnostic is written to a stream from inside the core;the collected diagnostics reach the renderer in emission order and are emitted before the fingerprint and refutation warnings

**Acceptance Criteria**:

- pytest passes with tests/baselines/manifest.json unmodified and PARITY_BASELINE_SHA256 unchanged
- and the run reports at least the baseline 191 passed and no more than the baseline 3 skipped (the 3 being the fingerprint tier)
- so a newly skipped or silently lost test fails this criterion;all four reconnect manifest cases pass unaltered;render applied to core produces stdout identical to each recorded reconnect case using the fixture_corpus inputs;stdout order for rewrite-from-reconnect is csv_written then the stats block then output_written;stderr order is the fingerprint dependency line then the refutation-disabled line;the typed failures input_not_found xml_parse_error volume_identity_error and fingerprint_unavailable each render to stderr and exit code 2;run_reconnection passes an on_progress callback through to index_scan_roots and a test asserts the callback fires
- and a set cancel token raises ScanCancelled out of the core;grep finds the refutation-disabled message literal in exactly one file, traktor_nml/shared_args.py
- traktor_nml/reconnect_run.py and traktor_nml/reconnect_render.py import nothing from traktor_nml/gui/ or traktor_nml/commands/, and import nicegui nowhere;the equivalence test fails when a stats key is dropped from the renderer;the whole of tests/test_reconnect.py passes and its fingerprint-diagnostic test patches a name the running code actually reads
- capsys records nothing on stdout or stderr while either core runs, including a run with HAS_MUTAGEN patched False and a run whose file count crosses progress_every, and the same two runs through the CLI reproduce the legacy stderr text and order byte for byte
- index_scan_roots called with no on_diagnostic still writes tag_reading_unavailable and disk_scan_progress to stderr, so discover-tracks is unchanged

**Tests**:

- tests/test_reconnect_render_equivalence.py

#### Code Intent

- **CI-M-002-001** `traktor_nml/reconnect_run.py::ReconnectResult`: A frozen dataclass carrying everything one reconnection pass produced: mapping (primary key to winning EntryRecord), stats, ambiguity_rows, old_records, and warnings (the run-derived notices, currently the fingerprint dependency reason). It replaces the bare four-tuple and is the object a GUI review table reads directly. (refs: DL-046, DL-050)
- **CI-M-002-002** `traktor_nml/reconnect_run.py::run_reconnection`: Signature run_reconnection(args, old_root, *, on_progress=None, cancel=None) -> ReconnectResult. on_progress and cancel are forwarded verbatim to index_scan_roots (traktor_nml/diskscan.py:155), which already accepts both; both default to None so the CLI path indexes exactly as it does today, and a GUI gets live indexing progress and a cancel token without bypassing the core. The pipeline is split across three helpers rather than inlined in one body: _resolve_volume_identities_and_mounts (one up-front resolution reused by both the fingerprint key provider and the LOCATION re-encoding), _build_fingerprint_tier (the optional FpcalcSession-owned key provider), and _reencode_winning_locations, so run_reconnection itself stays a short orchestration of collection_records, TagCache, index_scan_roots, the three helpers, resolve_reconnection and cache.flush. The FpcalcSession _build_fingerprint_tier opens is terminated in a try/finally around the resolve_reconnection call, because resolve_reconnection's fingerprint provide() closure is the last consumer of the session's fpcalc child; no session escapes run_reconnection. The two fingerprint failure modes stay distinct: fingerprint_key_provider being None still raises _FingerprintUnavailable, while a non-None fingerprint_unavailable_reason() is appended to warnings instead of being printed to stderr. warn_refutation_disabled is not called here. ScanCancelled propagates. (refs: DL-046, DL-050, DL-053, DL-054)
- **CI-M-002-003** `traktor_nml/reconnect_run.py::scan_reconnect_candidates`: Signature scan_reconnect_candidates(args, *, on_progress=None, cancel=None) -> ScanReconnectResult; both keyword arguments are passed straight through to run_reconnection (DL-054). It parses the input NML and maps FileNotFoundError to the input_not_found line and XML_PARSE_ERROR to the xml_parse_error line, and maps VolumeIdentityError to the volume_identity_error line and _FingerprintUnavailable to the fingerprint_unavailable line, each in the exact text used today. It writes the ambiguity CSV when args.csv is set, after run_reconnection has returned, and records the written path on the result rather than printing it. It writes to neither stream. (refs: DL-046, DL-051, DL-053, DL-054)
- **CI-M-002-004** `traktor_nml/reconnect_run.py::rewrite_from_reconnect`: Signature rewrite_from_reconnect(args, *, on_progress=None, cancel=None) -> RewriteReconnectResult; both keyword arguments reach run_reconnection through the callback (DL-054). It builds the collect_patches and mutate_tree callables exactly as they are built today, each running run_reconnection, merging apply stats under the reconnection stats in the same order, and writing the ambiguity CSV. A mutable holder dict with keys reconnect and csv_path, both initially None, is populated by the callback and read by the outer function after plan_and_write_nml returns. The write order inside the callback fixes the holder meaning in every case: run_reconnection returns first and the holder reconnect key is set immediately, then the CSV is written and csv_path is set. So (a) callback never ran, the output-collision refusal fired first: both keys stay None and RewriteReconnectResult carries reconnect None, csv_path None, the WriteOutcome from the collision, and error None. (b) callback ran and run_reconnection raised VolumeIdentityError or _FingerprintUnavailable: both keys are still None, because the raise precedes both assignments, and the outer function converts the exception into the typed error text with outcome None. There is no state in which csv_path is set while reconnect is None, and no partial ReconnectResult is ever stored. (c) callback ran to completion: both keys are populated. ScanCancelled escapes rather than becoming a field. (refs: DL-046, DL-047, DL-049, DL-053, DL-054)
- **CI-M-002-005** `traktor_nml/reconnect_render.py::RenderedOutput`: A dataclass of stdout_lines, stderr_lines and exit_code, plus an emit function that writes stdout_lines to sys.stdout and stderr_lines to sys.stderr and returns exit_code. Every print in the reconnect path lives inside emit. (refs: DL-051)
- **CI-M-002-006** `traktor_nml/reconnect_render.py::render_scan_reconnect_candidates`: Takes a ScanReconnectResult and the namespace and returns RenderedOutput. On a typed error the error text is the only stderr line and exit_code is 2. Otherwise stdout is the reconnectable count line followed by one key=value line per stats entry in insertion order and then the csv_written line when result.csv_path is set; stderr carries the fingerprint dependency warning from ReconnectResult.warnings first and the refutation-disabled line second, the latter obtained from shared_args.refutation_disabled_line(args) rather than from a literal in this module (DL-055). (refs: DL-046, DL-050, DL-051, DL-055)
- **CI-M-002-007** `traktor_nml/reconnect_render.py::render_rewrite_from_reconnect`: Takes a RewriteReconnectResult and the namespace and returns RenderedOutput. stdout is the csv_written line when csv_path is set, then the stats and sample_matches block from rewrite.format_stats_and_samples when outcome.stats is not None, then the output_written line when outcome.written_path is set; stderr carries the fingerprint dependency warning, then the refutation-disabled line from shared_args.refutation_disabled_line(args) (DL-055), then outcome.error or the typed reconnection error. exit_code mirrors outcome.exit_code, or is 2 when the typed reconnection error is set and outcome is None. (refs: DL-046, DL-048, DL-050, DL-051, DL-055)
- **CI-M-002-008** `traktor_nml/commands/reconnect_cmd.py`: Holds argparse wiring only: add_reconnect_args, register, and two handlers each one expression that emits the render of the core call. The pipeline, the CSV write, the stats merging and every stream write live in reconnect_run and reconnect_render, which this module imports. The module contains no print call and no sys.stdout or sys.stderr write. The defensive fingerprint import block and the _FingerprintUnavailable exception move to reconnect_run alongside the code that raises them. Import side effect of that move: commands/__init__.py imports every command module at CLI startup, so the try/except around traktor_nml.fingerprint now executes transitively via commands/__init__.py -> reconnect_cmd.py -> reconnect_run.py instead of directly in reconnect_cmd.py. Startup cost and failure behaviour are unchanged because the block stays defensive and reconnect_run imports nothing heavier than reconnect_cmd already did; what changes is the owning module, which is why tests/test_reconnect.py must patch traktor_nml.reconnect_run.fingerprint_unavailable_reason (CI-M-002-010) and not the old name. (refs: DL-046, DL-051, DL-052)
- **CI-M-002-009** `tests/test_reconnect_render_equivalence.py`: The section 3.2 equality tests. For each of the four reconnect manifest cases it builds the same argv against the fixture_corpus inputs the manifest case uses, runs the renderer over the core result in-process, and asserts the joined stdout lines equal the recorded stdout of that case and the stderr lines equal its recorded stderr and the exit code equals its recorded exit code, reading the expectations from tests/baselines/manifest.json rather than restating them. A negative control drops one stats key inside the renderer and asserts the comparison fails, and the docstring records that this was observed. Unit tests cover what the oracle cannot reach: (a) monkeypatching traktor_nml.reconnect_run.fingerprint_unavailable_reason to return a fixed reason asserts that reason lands in ReconnectResult.warnings and renders to stderr ahead of the refutation line rather than being printed by the core - the stub replaces only that probe and leaves traktor_nml.reconnect_run.fingerprint_key_provider bound as the defensive import left it; (b) a separate test sets traktor_nml.reconnect_run.fingerprint_key_provider to None and asserts the core raises _FingerprintUnavailable, so the raise path is proved distinct from the warn path rather than being masked by the probe stub; (c) a no-refute run asserts the refutation line comes from the renderer via _shared_args.refutation_disabled_line; (d) an on_progress callback passed into the core is asserted to have fired at least once with a path from the scan, and a pre-set cancel token is asserted to raise ScanCancelled out of the core rather than yielding a partial result; (e) a run with the output path equal to the input asserts reconnection never started. (refs: DL-046, DL-049, DL-050, DL-051, DL-054, DL-055)
- **CI-M-002-010** `tests/test_reconnect.py::test_fingerprint_flag_names_the_dependency_that_is_actually_missing`: The second monkeypatch target names traktor_nml.reconnect_run.fingerprint_unavailable_reason, the module-level alias the defensive fingerprint import binds and the probe the pipeline calls. run_tool invokes the CLI in-process, so this patch is load-bearing rather than decorative: patching a name the running code no longer reads leaves the real probe in place and the assertion on the fingerprint_dependency_missing stderr line then passes or fails by whatever the machine has installed. Every other assertion in the module is unchanged. (refs: DL-052)
- **CI-M-002-011** `traktor_nml/reconnect_run.py::ScanReconnectResult`: A frozen dataclass carrying one scan-reconnect pass. Fields: result (the ReconnectResult, or None when the pass ended in a typed error), error (the exact key=value text destined for stderr - input_not_found, xml_parse_error, volume_identity_error or fingerprint_unavailable - or None), and csv_path (the Path of the ambiguity CSV, or None when --csv was not passed or the pass failed before the CSV was written). Exactly one of result and error is non-None; csv_path is non-None only alongside a non-None result, because the CSV is written after run_reconnection returns. The renderer reads nothing else, and a GUI reads result directly. (refs: DL-046, DL-051, DL-053)
- **CI-M-002-012** `traktor_nml/reconnect_run.py::RewriteReconnectResult`: A frozen dataclass carrying one rewrite-from-reconnect pass. Fields: outcome (the WriteOutcome from plan_and_write_nml, or None when a typed reconnection error escaped the callback), reconnect (the ReconnectResult, or None per the holder rules in CI-M-002-004), csv_path (the ambiguity CSV Path, or None), and error (the typed reconnection error text for stderr - volume_identity_error or fingerprint_unavailable - or None). outcome and error are never both non-None: a WriteOutcome carries its own error field for write-path failures, and this error field is only for a failure that came out of the reconnection callback. csv_path is non-None only alongside a non-None reconnect. The renderer derives its exit code from outcome, or uses 2 when error is set. (refs: DL-046, DL-048, DL-051, DL-053)
- **CI-M-002-013** `traktor_nml/commands/_shared_args.py::refutation_disabled_line`: warn_refutation_disabled keeps its signature, its docstring contract and its stderr side effect, but now delegates to shared_args.refutation_disabled_line (CI-M-002-014) for the message text, so its byte output for compare_cmd's three call sites and every other existing caller is unchanged. resolve_confidence, should_refute and refutation_disabled_line themselves move to traktor_nml/shared_args.py and are imported back into this module, which keeps compare_cmd.py and reconnect_cmd.py's own `from ._shared_args import resolve_confidence, should_refute` (and, for reconnect_cmd.py, warn_refutation_disabled) working unchanged. reconnect_render calls shared_args.refutation_disabled_line directly and appends the returned string to its buffered stderr lines rather than restating the literal; warn_refutation_disabled is never called on the reconnect path. shared_args.py is the single source of the message text: no manifest case sets --no-refute for either reconnect command, so a second copy of the literal would drift invisibly (DL-055). (refs: DL-050, DL-051, DL-055)
- **CI-M-002-014** `traktor_nml/shared_args.py`: resolve_confidence, should_refute and refutation_disabled_line, moved out of commands/_shared_args.py: all three are pure functions of an argparse.Namespace with no argparse registration or stream dependency of their own, and reconnect_run.py/reconnect_render.py need them without importing anything from commands/, which commands/__init__.py auto-imports at CLI startup and which reconnect_run/reconnect_render must sit below rather than beside (DL-052). commands/_shared_args.py imports the same three names from here and keeps add_confidence_args, add_no_refute_argument and warn_refutation_disabled, so every existing importer of the moved names (compare_cmd.py, reconnect_cmd.py) is unaffected. (refs: DL-052, DL-055)
- **CI-M-002-015** `traktor_nml/diskscan.py::index_scan_roots`: Signature gains one keyword argument, on_diagnostic: Optional[Callable[[str], None]] = None. The two existing emission sites are rewritten to build the line and hand it to a single module-local helper, _emit_diagnostic(on_diagnostic, line), which calls on_diagnostic(line) when it is not None and otherwise does print(line, file=sys.stderr) - the branch lives in one place so the two sites cannot diverge. The line text is unchanged at both sites: 'tag_reading_unavailable=mutagen not installed; tiers still able to match, by --match-confidence level: ' + _tag_free_summary() at entry when HAS_MUTAGEN is false (traktor_nml/diskscan.py:183), and f'disk_scan_progress={stats["files_seen"]}' inside the walk when files_seen % progress_every == 0 (:211). Nothing else about the function changes: the mutagen check stays the first statement so its line precedes every progress line, the progress check stays inside the loop so its lines interleave with the walk in file order, and the docstring's existing promise that an unset callback behaves exactly as before now covers three parameters rather than two. discover_tracks_cmd.py passes nothing and is byte-identical. (refs: DL-056)
- **CI-M-002-016** `traktor_nml/reconnect_run.py::run_reconnection` diagnostics collection: run_reconnection builds a list and passes its append as on_diagnostic to index_scan_roots, so every diagnostic the scan would have printed is captured in emission order and the core writes to no stream. The list is carried on ReconnectResult as a new field, diagnostics: tuple[str, ...], frozen with the rest of the dataclass (CI-M-002-001), defaulting to an empty tuple. It is a sequence and not a set or a mapping because tag_reading_unavailable must precede the first disk_scan_progress line and the progress lines are ordered by file (DL-056). ScanCancelled still escapes, and the diagnostics collected before the cancel are discarded with the rest of the partial run rather than being reported - a cancelled run yields no result, per DL-053. (refs: DL-046, DL-056)
- **CI-M-002-017** `traktor_nml/reconnect_render.py` diagnostic ordering: both render functions prepend result.diagnostics, in stored order, to their stderr lines, ahead of the fingerprint dependency warning and the refutation-disabled line. That reproduces the legacy sequence, in which index_scan_roots runs before the fingerprint tier is built and before warn_refutation_disabled is called, so the scan's stderr precedes both warnings. On a typed error that occurred after the scan the diagnostics still precede the error line, for the same reason. A unit test asserts the full three-part order - diagnostics, fingerprint warning, refutation line - because no manifest case produces more than one of the three. (refs: DL-050, DL-051, DL-056)
- **CI-M-002-018** `tests/test_scan_diagnostics.py`: The direct-core capture tests for the two conditions the parity oracle cannot reach, each proving both halves of DL-056. (a) Missing mutagen: monkeypatch traktor_nml.diskscan.HAS_MUTAGEN to False; with no on_diagnostic, capsys shows the exact tag_reading_unavailable line on stderr and nothing on stdout; with a collector, capsys shows nothing on either stream and the collector holds that same line. The expected text is built from traktor_nml.diskscan._tag_free_summary() rather than restated, so the test cannot pin a stale message. (b) Above the progress threshold: a fixture root with enough files and progress_every lowered so the walk crosses it more than once; with no on_diagnostic the disk_scan_progress lines appear on stderr in ascending order, and with a collector they appear in the collector in that same order and stderr is empty. (c) Both conditions together assert tag_reading_unavailable precedes every disk_scan_progress line. (d) run_reconnection under both conditions asserts capsys is empty on both streams - this is the leak detector at core level, and it is the test that fails first if a future change reintroduces a print into the pipeline. Each test states its negative case and demonstrates it: the collector variants are run against a build with the on_diagnostic branch forced to the print path and observed to fail, and the docstring records that. (refs: DL-056, DL-057)

#### Code Changes

**CC-M-002-001** (traktor_nml/reconnect_run.py) - implements CI-M-002-001

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/reconnect_run.py
@@ -0,0 +1,84 @@
+"""Printless reconnection core: match an old collection's tracks against
+disk-scan candidates and return typed results.
+
+commands/reconnect_cmd.py holds argparse wiring only; the pipeline lives
+here and prints nothing. A GUI review table needs the mapping and the
+ambiguity rows as objects while a run is in progress, and a transcript
+parsed after the fact arrives too late for that. run_reconnection returns a
+ReconnectResult, and scan_reconnect_candidates/rewrite_from_reconnect wrap
+it with the CSV write and the typed-error mapping each command needs,
+also as results rather than prints. reconnect_render turns these into
+buffered stdout/stderr lines and an exit code.
+"""
+
+from __future__ import annotations
+
+import argparse
+import csv
+from dataclasses import dataclass, field
+from pathlib import Path
+from typing import Callable, Optional
+
+from .shared_args import resolve_confidence, should_refute
+from .diskscan import index_scan_roots
+from .model import EntryRecord, collection_records, loc_attr_changes, write_location_element
+from .reconnect import location_from_disk_path, resolve_reconnection
+from .rewrite import (
+    CompareEntryResolver,
+    WriteOutcome,
+    _collect_compare_patches,
+    plan_and_write_nml,
+    process_non_collection_entries,
+)
+from .tagcache import TagCache
+from .volumes import VolumeIdentityError, parse_volume_map, resolve_volume_identity
+from .xmlio import XML_PARSE_ERROR, parse_xml
+
+try:
+    # fingerprint.py is the M-005 acoustic-fingerprint key provider; it may
+    # not exist yet when this module is developed concurrently with M-005.
+    # Importing it defensively keeps every other subcommand (this module is
+    # reachable from commands/__init__.py, which imports every command
+    # module at CLI startup) working even when fingerprint.py, pyacoustid
+    # and fpcalc are absent - --fingerprint simply becomes unavailable
+    # until M-005 lands, rather than the whole CLI failing to import.
+    from .fingerprint import (
+        FPCALC_TIMEOUT_SECONDS,
+        FpcalcSession,
+        fingerprint_key_provider,
+        fingerprint_unavailable_reason,
+    )
+except ImportError:  # pragma: no cover - fingerprint tier lands in M-005
+    fingerprint_key_provider = None
+    fingerprint_unavailable_reason = None
+    FpcalcSession = None
+    FPCALC_TIMEOUT_SECONDS = 30.0
+
+
+class _FingerprintUnavailable(RuntimeError):
+    pass
+
+
+@dataclass(frozen=True)
+class ReconnectResult:
+    """Everything one reconnection pass produced: the primary-key-to-
+    winning-EntryRecord mapping, its stats, the rows a caller may export
+    as an ambiguity CSV, the old records the mapping was matched against,
+    and warnings - run-derived notices, currently the fingerprint
+    dependency reason - that travel with the result instead of printing
+    to stderr mid-pipeline. A GUI review table reads this
+    directly."""
+
+    mapping: dict[str, EntryRecord]
+    stats: dict[str, int]
+    ambiguity_rows: list[dict[str, str]]
+    old_records: list[EntryRecord]
+    warnings: list[str] = field(default_factory=list)

```

**Documentation:**

```diff
--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -59,4 +59,9 @@ except ImportError:  # pragma: no cover - fingerprint tier lands in M-005
 
 
 class _FingerprintUnavailable(RuntimeError):
+    """--fingerprint was requested but fingerprint_key_provider is None -
+    fingerprint.py itself wasn't importable, not merely one of its
+    runtime dependencies missing. Distinct from the
+    fingerprint_dependency_missing warning, which fires when the module
+    imported fine but pyacoustid/fpcalc/chromaprint are not usable."""
     pass

```


**CC-M-002-002** (traktor_nml/reconnect_run.py) - implements CI-M-002-011

**Code:**

```diff
--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -80,3 +80,14 @@ class ReconnectResult:
     ambiguity_rows: list[dict[str, str]]
     old_records: list[EntryRecord]
     warnings: list[str] = field(default_factory=list)
+
+
+@dataclass(frozen=True)
+class ScanReconnectResult:
+    """One scan-reconnect-candidates pass. Exactly one of result and
+    error is non-None; csv_path is non-None only alongside a non-None
+    result, because the CSV is written after run_reconnection returns.
+    """
+
+    result: Optional[ReconnectResult]
+    error: Optional[str]
+    csv_path: Optional[Path]

```

**Documentation:**

```diff
--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -95,7 +95,10 @@ class ScanReconnectResult:
     error is non-None; csv_path is non-None only alongside a non-None
     result, because the CSV is written after run_reconnection returns.
     """
 
+    # error carries one of input_not_found=, xml_parse_error=,
+    # volume_identity_error= or fingerprint_unavailable= - the same four
+    # typed failures the renderer maps to exit code 2.
     result: Optional[ReconnectResult]
     error: Optional[str]
     csv_path: Optional[Path]

```


**CC-M-002-003** (traktor_nml/reconnect_run.py) - implements CI-M-002-012

**Code:**

```diff
--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -91,3 +91,17 @@ class ScanReconnectResult:
     result: Optional[ReconnectResult]
     error: Optional[str]
     csv_path: Optional[Path]
+
+
+@dataclass(frozen=True)
+class RewriteReconnectResult:
+    """One rewrite-from-reconnect pass. outcome and error are never both
+    non-None: a WriteOutcome carries its own error field for write-path
+    failures, and this error field is only for a failure that came out of
+    the reconnection callback before plan_and_write_nml could produce an
+    outcome at all. csv_path is non-None only alongside a non-None
+    reconnect.
+    """
+
+    outcome: Optional[WriteOutcome]
+    reconnect: Optional[ReconnectResult]
+    csv_path: Optional[Path]
+    error: Optional[str]

```

**Documentation:**

```diff
--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -101,7 +101,11 @@ class RewriteReconnectResult:
     outcome could produce one at all. csv_path is non-None only alongside a non-None
     reconnect.
     """
 
+    # outcome is None only when error is set: a volume_identity_error or
+    # fingerprint_unavailable raised out of the reconnection callback
+    # before plan_and_write_nml's own WriteOutcome could be built, so
+    # there is nothing to hold its error/exit_code fields instead.
     outcome: Optional[WriteOutcome]
     reconnect: Optional[ReconnectResult]
     csv_path: Optional[Path]

```


**CC-M-002-004** (traktor_nml/reconnect_run.py) - implements CI-M-002-002

**Code:**

```diff
--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -105,3 +105,150 @@ class RewriteReconnectResult:
     reconnect: Optional[ReconnectResult]
     csv_path: Optional[Path]
     error: Optional[str]
+
+
+def _resolve_volume_identities_and_mounts(
+    args: argparse.Namespace, old_records: list[EntryRecord]
+) -> tuple[dict[Path, tuple[str, str]], dict[tuple[str, str], list[Path]]]:
+    """Resolve each scan root's volume identity once, up front: both the
+    fingerprint tier's old-side resolver and the candidate-side LOCATION
+    re-encoding reuse the same resolved identities rather than resolving
+    twice.
+    """
+    volume_map = parse_volume_map(args.volume_map)
+    volume_identities: dict[Path, tuple[str, str]] = {}
+    for scan_root in args.scan_roots:
+        volume_identities[Path(scan_root)] = resolve_volume_identity(scan_root, old_records, volume_map)
+
+    # known_mounts anchors each scan root at its own filesystem anchor (the
+    # drive letter or POSIX root, e.g. "C:\\" or "/"), never at scan_root
+    # itself - decoded_path is volume-relative (relative to the volume
+    # root), not relative to an arbitrary scan-root subdirectory, so
+    # anchoring at scan_root would reconstruct the wrong absolute path for
+    # every record whose file sits outside that particular subdirectory.
+    known_mounts: dict[tuple[str, str], list[Path]] = {}
+    for scan_root, identity in volume_identities.items():
+        anchor = Path(scan_root).anchor
+        if anchor:
+            known_mounts.setdefault(identity, []).append(Path(anchor))
+    return volume_identities, known_mounts
+
+
+def _build_fingerprint_tier(
+    args: argparse.Namespace,
+    cache: TagCache,
+    candidates: list[EntryRecord],
+    known_mounts: dict[tuple[str, str], list[Path]],
+):
+    """Build the fingerprint key provider when --fingerprint is set, or
+    return an empty tier when it is not. The returned session (or None)
+    is the caller's to terminate once resolve_reconnection has finished
+    with it - this function only opens it, because the fingerprint
+    provider's provide() closure fingerprints old-side records lazily
+    during matching, after this function has already returned.
+    """
+    key_providers = []
+    fingerprint_stats: dict[str, int] = {}
+    warnings: list[str] = []
+    if not getattr(args, "fingerprint", False):
+        return key_providers, fingerprint_stats, warnings, None
+
+    if fingerprint_key_provider is None:
+        raise _FingerprintUnavailable(
+            "fingerprint_key_provider unavailable (traktor_nml.fingerprint not installed)"
+        )
+    unavailable = fingerprint_unavailable_reason()
+    if unavailable is not None:
+        # Every way this tier can be unusable degrades to matching
+        # nothing, so an undiagnosed run looks exactly like one that
+        # searched and found no candidates. The reason is named rather
+        # than the dependency set listed, because the three pieces fail
+        # independently and "pyacoustid/fpcalc not available" is wrong
+        # advice when the missing piece is the chromaprint library and
+        # both of those are installed.
+        warnings.append(
+            f"fingerprint_dependency_missing={unavailable}; "
+            "--fingerprint tier will find no matches"
+        )
+    # The session owns the fpcalc child, so a per-file timeout is
+    # enforceable and a caller can terminate one mid-fingerprint.
+    fpcalc_session = FpcalcSession(timeout=getattr(args, "fpcalc_timeout", FPCALC_TIMEOUT_SECONDS))
+    key_providers.append(
+        fingerprint_key_provider(cache, candidates, fingerprint_stats, known_mounts, fpcalc_session)
+    )
+    return key_providers, fingerprint_stats, warnings, fpcalc_session
+
+
+def _reencode_winning_locations(
+    mapping: dict[str, EntryRecord], volume_identities: dict[Path, tuple[str, str]]
+) -> None:
+    """Re-encode each winning candidate's real absolute path into a
+    proper LOCATION using its scan root's resolved volume identity - the
+    placeholder LocationParts a disk-scan candidate carries has no real
+    VOLUME/VOLUMEID and is never written as-is.
+    """
+    for candidate in mapping.values():
+        if candidate.source_path is None:
+            continue
+        for scan_root, identity in volume_identities.items():
+            try:
+                candidate.source_path.relative_to(scan_root.resolve())
+            except ValueError:
+                continue
+            candidate.location = location_from_disk_path(candidate.source_path, *identity)
+            break
+
+
+def run_reconnection(
+    args: argparse.Namespace,
+    old_root,
+    *,
+    on_progress: Optional[Callable[[int, int, Path], None]] = None,
+    cancel=None,
+) -> ReconnectResult:
+    """Run the whole reconnection pipeline and return a ReconnectResult.
+
+    on_progress and cancel are forwarded verbatim to index_scan_roots,
+    which already accepts both; both default to None so the CLI path
+    indexes exactly as it does without them, and a GUI gets live indexing
+    progress and a cancel token without bypassing this core.
+    ScanCancelled propagates rather than becoming a field on the result:
+    a short candidate list is indistinguishable from a complete one, so a
+    partial result would report most of the collection as missing - a
+    wrong answer delivered confidently.
+    """
+    old_records = collection_records(old_root)
+    cache = TagCache(args.cache)
+    candidates = index_scan_roots(
+        args.scan_roots, cache, refresh_cache=args.refresh_cache,
+        on_progress=on_progress, cancel=cancel,
+    )
+    confidence = resolve_confidence(args)
+
+    volume_identities, known_mounts = _resolve_volume_identities_and_mounts(args, old_records)
+    key_providers, fingerprint_stats, warnings, fpcalc_session = _build_fingerprint_tier(
+        args, cache, candidates, known_mounts
+    )
+    try:
+        # fpcalc_session, when the fingerprint tier is active, is opened
+        # by _build_fingerprint_tier above and its child process must not
+        # outlive this function: resolve_reconnection is the last
+        # consumer (its provide() closure fingerprints old-side records
+        # lazily during matching), so the session is terminated here
+        # regardless of how matching finishes.
+        mapping, stats, ambiguity_rows = resolve_reconnection(
+            old_records, candidates, confidence, key_providers,
+            refute=should_refute(args),
+        )
+    finally:
+        if fpcalc_session is not None:
+            fpcalc_session.terminate()
+    stats = {**fingerprint_stats, **stats}
+
+    _reencode_winning_locations(mapping, volume_identities)
+
+    cache.flush()
+    return ReconnectResult(mapping, stats, ambiguity_rows, old_records, warnings)

```

**Documentation:**

```diff
--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -113,5 +113,9 @@ def run_reconnection(
     on_progress and cancel are forwarded verbatim to index_scan_roots,
     which already accepts both; both default to None so the CLI path
     indexes exactly as it does without them, and a GUI gets live indexing
     progress and a cancel token without bypassing this core.
+    Neither parameter has an in-repo caller yet - both argparse handlers
+    pass neither - and that absence is intentional: this is the channel
+    a future GUI review table is meant to call once it exists, not dead
+    code to remove (DL-054).
     ScanCancelled propagates rather than becoming a field on the result:
@@ -119,6 +123,10 @@ def run_reconnection(
     ScanCancelled propagates rather than becoming a field on the result:
     a short candidate list is indistinguishable from a complete one, so a
     partial result would report most of the collection as missing - a
     wrong answer delivered confidently.
     """
+    # Volume identities are resolved once here and reused by both the
+    # fingerprint tier (_build_fingerprint_tier's known_mounts) and the
+    # candidate-side LOCATION re-encoding below, so a core-boundary
+    # redesign must not reintroduce a second resolution (ref: DL-046).
     old_records = collection_records(old_root)

```


**CC-M-002-005** (traktor_nml/reconnect_run.py) - implements CI-M-002-003

**Code:**

```diff
--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -192,3 +192,42 @@ def run_reconnection(
+
+
+def _write_ambiguity_csv(rows: list[dict[str, str]], csv_path: Path) -> None:
+    fieldnames = list(rows[0].keys()) if rows else ["artist", "title", "old_path", "reason"]
+    with csv_path.open("w", newline="", encoding="utf-8") as handle:
+        writer = csv.DictWriter(handle, fieldnames=fieldnames)
+        if rows:
+            writer.writeheader()
+            writer.writerows(rows)
+
+
+def scan_reconnect_candidates(
+    args: argparse.Namespace,
+    *,
+    on_progress: Optional[Callable[[int, int, Path], None]] = None,
+    cancel=None,
+) -> ScanReconnectResult:
+    """Run one scan-reconnect-candidates pass, printless.
+
+    on_progress and cancel pass straight through to run_reconnection.
+    Writes the ambiguity CSV when args.csv is set, after
+    run_reconnection has returned, and records the written path on the
+    result rather than printing it. Writes to neither stream.
+    """
+    try:
+        old_tree = parse_xml(args.old_input)
+    except FileNotFoundError:
+        return ScanReconnectResult(None, f"input_not_found={args.old_input.as_posix()}", None)
+    except XML_PARSE_ERROR as exc:
+        return ScanReconnectResult(None, f"xml_parse_error={args.old_input.as_posix()}: {exc}", None)
+
+    try:
+        result = run_reconnection(args, old_tree.getroot(), on_progress=on_progress, cancel=cancel)
+    except VolumeIdentityError as exc:
+        return ScanReconnectResult(None, f"volume_identity_error={exc}", None)
+    except _FingerprintUnavailable as exc:
+        return ScanReconnectResult(None, f"fingerprint_unavailable={exc}", None)
+
+    csv_path = None
+    if args.csv is not None:
+        _write_ambiguity_csv(result.ambiguity_rows, args.csv)
+        csv_path = args.csv
+    return ScanReconnectResult(result, None, csv_path)

```

**Documentation:**

```diff
--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -197,6 +197,9 @@ def scan_reconnect_candidates(
     Writes the ambiguity CSV when args.csv is set, after
     run_reconnection has returned, and records the written path on the
     result rather than printing it. Writes to neither stream.
     """
+    # Both typed failures below are returned as an
+    # error=<key>=<value> string; the renderer, not this function,
+    # decides how they reach stdout/stderr and maps them to exit code 2.
     try:
         old_tree = parse_xml(args.old_input)

```


**CC-M-002-006** (traktor_nml/reconnect_run.py) - implements CI-M-002-004

**Code:**

```diff
--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -233,3 +233,79 @@ def scan_reconnect_candidates(
+
+
+def _apply_mapping_stdlib(
+    old_root, old_records: list[EntryRecord], mapping: dict[str, EntryRecord], stats: dict[str, int], dry_run: bool
+) -> None:
+    for record in old_records:
+        new_record = mapping.get(record.primary_key)
+        if new_record is None:
+            continue
+        ch = loc_attr_changes(record.location, new_record.location)
+        if ch:
+            stats["collection_locations_rewritten"] += 1
+            if not dry_run:
+                loc_elem = record.entry.find("LOCATION")
+                if loc_elem is not None:
+                    write_location_element(loc_elem, new_record.location)
+    resolver = CompareEntryResolver(mapping=mapping)
+    process_non_collection_entries(
+        old_root, {id(r.entry) for r in old_records}, resolver, stats, dry_run=dry_run
+    )
+
+
+def rewrite_from_reconnect(
+    args: argparse.Namespace,
+    *,
+    on_progress: Optional[Callable[[int, int, Path], None]] = None,
+    cancel=None,
+) -> RewriteReconnectResult:
+    """Run one rewrite-from-reconnect pass, printless.
+
+    on_progress and cancel reach run_reconnection through the callback.
+    A mutable holder dict with keys reconnect and csv_path,
+    both initially None, is populated by the callback and read after
+    plan_and_write_nml returns. The write order inside the callback fixes
+    the holder's meaning in every case: run_reconnection returns first
+    and the holder's reconnect key is set immediately, then the CSV is
+    written and csv_path is set - so there is no state in which csv_path
+    is set while reconnect is None, and no partial ReconnectResult is
+    ever stored. ScanCancelled escapes rather than becoming a field.
+    """
+    holder: dict[str, object] = {"reconnect": None, "csv_path": None}
+
+    def _collect_patches(old_root):
+        result = run_reconnection(args, old_root, on_progress=on_progress, cancel=cancel)
+        holder["reconnect"] = result
+        patches, apply_stats = _collect_compare_patches(old_root, result.old_records, result.mapping)
+        merged_stats = {**apply_stats, **result.stats}
+        if args.csv is not None:
+            _write_ambiguity_csv(result.ambiguity_rows, args.csv)
+            holder["csv_path"] = args.csv
+        return patches, merged_stats, []
+
+    def mutate_tree(old_root, dry_run):
+        result = run_reconnection(args, old_root, on_progress=on_progress, cancel=cancel)
+        holder["reconnect"] = result
+        merged_stats = {
+            "collection_locations_rewritten": 0,
+            "other_locations_rewritten": 0,
+            "primarykeys_updated_from_collection": 0,
+            "primarykeys_unchanged": 0,
+            **result.stats,
+        }
+        _apply_mapping_stdlib(old_root, result.old_records, result.mapping, merged_stats, dry_run)
+        if args.csv is not None:
+            _write_ambiguity_csv(result.ambiguity_rows, args.csv)
+            holder["csv_path"] = args.csv
+        return merged_stats, []
+
+    try:
+        outcome = plan_and_write_nml(args.old_input, args.output, args.dry_run, _collect_patches, mutate_tree)
+    except VolumeIdentityError as exc:
+        return RewriteReconnectResult(None, None, None, f"volume_identity_error={exc}")
+    except _FingerprintUnavailable as exc:
+        return RewriteReconnectResult(None, None, None, f"fingerprint_unavailable={exc}")
+
+    return RewriteReconnectResult(outcome, holder["reconnect"], holder["csv_path"], None)

```

**Documentation:**

```diff
--- a/traktor_nml/reconnect_run.py
+++ b/traktor_nml/reconnect_run.py
@@ -235,4 +235,11 @@ def scan_reconnect_candidates(
 def _apply_mapping_stdlib(
     old_root, old_records: list[EntryRecord], mapping: dict[str, EntryRecord], stats: dict[str, int], dry_run: bool
 ) -> None:
+    """Both writers - this stdlib path and rewrite.py's compare-based
+    lxml path - must share one PRIMARYKEY/entry-rewrite rule, so every
+    non-collection entry here is handed to CompareEntryResolver, the same
+    resolver rewrite.py uses. Each matched record's LOCATION is rewritten
+    directly (rather than through the resolver) since a disk-scan match
+    carries no compare-report entry of its own.
+    """
     for record in old_records:
@@ -271,3 +278,9 @@ def rewrite_from_reconnect(
     ever stored. ScanCancelled escapes rather than becoming a field.
+
+    Both the tag cache (via run_reconnection's cache.flush()) and the
+    ambiguity CSV are written on every call regardless of args.dry_run:
+    dry_run governs only the final write_nml_safely/plan_and_write_nml
+    step, and neither the cache nor the CSV is this command's declared
+    output.
     """
     holder: dict[str, object] = {"reconnect": None, "csv_path": None}

```


**CC-M-002-007** (traktor_nml/reconnect_render.py) - implements CI-M-002-005

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/reconnect_render.py
@@ -0,0 +1,31 @@
+"""Every character the reconnect commands put on stdout or stderr.
+
+reconnect_run.py returns typed results rather than printing; this module
+turns a result into buffered stdout lines, stderr lines and an exit code,
+and emit is the one function that actually writes to a stream.
+"""
+
+from __future__ import annotations
+
+import argparse
+import sys
+from dataclasses import dataclass
+
+from . import rewrite
+from .reconnect_run import RewriteReconnectResult, ScanReconnectResult
+from .shared_args import refutation_disabled_line
+
+
+@dataclass
+class RenderedOutput:
+    """Buffered stdout lines, stderr lines and an exit code. emit is the
+    one function that writes them to sys.stdout/sys.stderr, so every
+    print on the reconnect path lives inside it rather than scattered
+    across the pipeline."""
+
+    stdout_lines: list[str]
+    stderr_lines: list[str]
+    exit_code: int
+
+
+def emit(rendered: RenderedOutput) -> int:
+    for line in rendered.stdout_lines:
+        print(line)
+    for line in rendered.stderr_lines:
+        print(line, file=sys.stderr)
+    return rendered.exit_code

```

**Documentation:**

```diff
--- a/traktor_nml/reconnect_render.py
+++ b/traktor_nml/reconnect_render.py
@@ -27,6 +27,9 @@ class RenderedOutput:
     print on the reconnect path lives inside it rather than scattered
     across the pipeline."""

+    # Two separate lists rather than one interleaved stream: the parity
+    # manifest records stdout and stderr independently, and buffering
+    # them separately means this module cannot reorder what it observes.
     stdout_lines: list[str]
     stderr_lines: list[str]
     exit_code: int

```


**CC-M-002-008** (traktor_nml/reconnect_render.py) - implements CI-M-002-006

**Code:**

```diff
--- a/traktor_nml/reconnect_render.py
+++ b/traktor_nml/reconnect_render.py
@@ -30,3 +30,21 @@ def emit(rendered: RenderedOutput) -> int:
     for line in rendered.stderr_lines:
         print(line, file=sys.stderr)
     return rendered.exit_code
+
+
+def render_scan_reconnect_candidates(
+    result: ScanReconnectResult, args: argparse.Namespace
+) -> RenderedOutput:
+    if result.error is not None:
+        return RenderedOutput([], [result.error], 2)
+
+    reconnect = result.result
+    stdout_lines = [f"reconnectable={len(reconnect.mapping)}"]
+    for key, value in reconnect.stats.items():
+        stdout_lines.append(f"{key}={value}")
+    if result.csv_path is not None:
+        stdout_lines.append(f"csv_written={result.csv_path.as_posix()}")
+
+    stderr_lines = list(reconnect.warnings)
+    refutation_line = refutation_disabled_line(args)
+    if refutation_line is not None:
+        stderr_lines.append(refutation_line)
+
+    return RenderedOutput(stdout_lines, stderr_lines, 0)

```

**Documentation:**

```diff
--- a/traktor_nml/reconnect_render.py
+++ b/traktor_nml/reconnect_render.py
@@ -34,5 +34,14 @@ def emit(rendered: RenderedOutput) -> int:
 def render_scan_reconnect_candidates(
     result: ScanReconnectResult, args: argparse.Namespace
 ) -> RenderedOutput:
+    """Produces stdout as reconnectable=<count> followed by the stats
+    block in mapping order, then csv_written=<path> only when a CSV was
+    written; stderr as the run's own warnings followed by the
+    refutation-disabled line when refutation is off. tests/baselines/
+    manifest.json's recorded scan-reconnect-candidates cases are the
+    oracle for this exact ordering. An error on the result short-
+    circuits to a single stderr line and exit code 2, since no
+    ReconnectResult exists yet.
+    """
     if result.error is not None:
         return RenderedOutput([], [result.error], 2)

```


**CC-M-002-009** (traktor_nml/reconnect_render.py) - implements CI-M-002-007

**Code:**

```diff
--- a/traktor_nml/reconnect_render.py
+++ b/traktor_nml/reconnect_render.py
@@ -48,3 +48,26 @@ def render_scan_reconnect_candidates(
     return RenderedOutput(stdout_lines, stderr_lines, 0)
+
+
+def render_rewrite_from_reconnect(
+    result: RewriteReconnectResult, args: argparse.Namespace
+) -> RenderedOutput:
+    stdout_lines: list[str] = []
+    if result.csv_path is not None:
+        stdout_lines.append(f"csv_written={result.csv_path.as_posix()}")
+
+    outcome = result.outcome
+    if outcome is not None and outcome.stats is not None:
+        stdout_lines.extend(rewrite.format_stats_and_samples(outcome.stats, outcome.samples))
+    if outcome is not None and outcome.written_path is not None:
+        stdout_lines.append(f"output_written={outcome.written_path.as_posix()}")
+
+    stderr_lines: list[str] = []
+    if result.reconnect is not None:
+        # The refutation warning belongs only to a run that reached
+        # matching: volume-identity resolution and the fingerprint check
+        # must both have succeeded first - gating on
+        # result.reconnect (populated only once run_reconnection returns)
+        # reproduces that: an output collision or a volume_identity_error/
+        # fingerprint_unavailable failure prints neither warning.
+        stderr_lines.extend(result.reconnect.warnings)
+        refutation_line = refutation_disabled_line(args)
+        if refutation_line is not None:
+            stderr_lines.append(refutation_line)
+    if outcome is not None and outcome.error is not None:
+        stderr_lines.append(outcome.error)
+    elif result.error is not None:
+        stderr_lines.append(result.error)
+
+    exit_code = outcome.exit_code if outcome is not None else 2
+    return RenderedOutput(stdout_lines, stderr_lines, exit_code)

```

**Documentation:**

```diff
--- a/traktor_nml/reconnect_render.py
+++ b/traktor_nml/reconnect_render.py
@@ -51,5 +51,15 @@ def render_scan_reconnect_candidates(
 def render_rewrite_from_reconnect(
     result: RewriteReconnectResult, args: argparse.Namespace
 ) -> RenderedOutput:
+    """Produces stdout as csv_written=<path> first when a CSV was
+    written, then the stats/samples block and output_written=<path>
+    sourced from the WriteOutcome, in the same order write_nml_safely
+    prints them. The CSV line comes first because the CSV is written
+    inside the reconnection callback, before plan_and_write_nml's write
+    step runs. Warnings and the refutation line are gated on
+    result.reconnect being populated, so a run that fails before
+    reconnection completes (an output collision, or a volume-identity/
+    fingerprint error) prints neither.
+    """
     stdout_lines: list[str] = []
     if result.csv_path is not None:

```


**CC-M-002-010** (traktor_nml/commands/reconnect_cmd.py) - implements CI-M-002-008

**Code:**

```diff
--- a/traktor_nml/commands/reconnect_cmd.py
+++ b/traktor_nml/commands/reconnect_cmd.py
@@ -1,302 +1,89 @@
 """scan-reconnect-candidates and rewrite-from-reconnect subcommands."""

 from __future__ import annotations

 import argparse
-import csv
-import sys
 from pathlib import Path

-from ..diskscan import index_scan_roots
-from ..model import EntryRecord, collection_records, loc_attr_changes, write_location_element
-from ..reconnect import location_from_disk_path, resolve_reconnection
-from ..rewrite import (
-    CompareEntryResolver,
-    _collect_compare_patches,
-    process_non_collection_entries,
-    write_nml_safely,
-)
-from ..tagcache import TagCache
-from ..volumes import VolumeIdentityError, parse_volume_map, resolve_volume_identity
-from ..xmlio import XML_PARSE_ERROR, parse_xml
-from ._shared_args import (
-    add_confidence_args,
-    add_no_refute_argument,
-    resolve_confidence,
-    should_refute,
-    warn_refutation_disabled,
-)
+from .. import reconnect_run
+from ..reconnect_render import emit, render_rewrite_from_reconnect, render_scan_reconnect_candidates
+from ._shared_args import add_confidence_args, add_no_refute_argument

 try:
-    # fingerprint.py is the M-005 acoustic-fingerprint key provider; it may
-    # not exist yet when this module is developed concurrently with M-005.
-    # Importing it defensively keeps every other subcommand (this module is
-    # auto-imported at CLI startup, see commands/__init__.py) working even
-    # when fingerprint.py, pyacoustid and fpcalc are absent - --fingerprint
-    # simply becomes unavailable until M-005 lands, rather than the whole
-    # CLI failing to import.
-    from ..fingerprint import (
-        FPCALC_TIMEOUT_SECONDS,
-        FpcalcSession,
-        fingerprint_key_provider,
-        fingerprint_unavailable_reason,
-    )
+    # See reconnect_run.py's own defensive import: --fpcalc-timeout's
+    # default needs FPCALC_TIMEOUT_SECONDS whether or not fingerprint.py
+    # (the M-005 acoustic-fingerprint tier) is present yet.
+    from ..fingerprint import FPCALC_TIMEOUT_SECONDS
 except ImportError:  # pragma: no cover - fingerprint tier lands in M-005
-    fingerprint_key_provider = None
-    fingerprint_unavailable_reason = None
-    FpcalcSession = None
     FPCALC_TIMEOUT_SECONDS = 30.0
-
-
-class _FingerprintUnavailable(RuntimeError):
-    pass


 def add_reconnect_args(parser: argparse.ArgumentParser) -> None:
     add_no_refute_argument(parser)
     parser.add_argument(
         "--fpcalc-timeout",
         type=float,
         default=FPCALC_TIMEOUT_SECONDS,
         help=f"Seconds to allow one file's fingerprint before giving up on it "
         f"(default {FPCALC_TIMEOUT_SECONDS:g}). The file is counted as "
         f"fingerprint_timeout and the scan continues, so one pathological "
         f"file cannot stall a long run.",
     )
     parser.add_argument(
         "--scan-root",
         type=Path,
         action="append",
         dest="scan_roots",
         required=True,
         help="Filesystem root to scan for candidate audio files (repeatable).",
     )
     parser.add_argument(
         "--volume-map",
         nargs=3,
         action="append",
         metavar=("SCAN_ROOT", "VOLUME", "VOLUMEID"),
         help="Explicit VOLUME/VOLUMEID for a scan root (repeatable); required when the "
         "prefix scan of the old collection cannot resolve a single unambiguous pair.",
     )
     parser.add_argument(
         "--cache",
         type=Path,
         default=Path(".traktor_nml_tagcache.json"),
         help="Disk-scan tag cache path. Written/updated as scan roots are indexed, "
         "independently of --dry-run: --dry-run only suppresses writes to the output "
         "NML, not this cache file.",
     )
     parser.add_argument("--refresh-cache", action="store_true")
     parser.add_argument("--csv", type=Path)
     parser.add_argument(
         "--fingerprint",
         action="store_true",
         help="Enable the acoustic-fingerprint match tier (requires pyacoustid, the fpcalc binary, and the chromaprint shared library); "
         "opt-in and off by default since these are optional dependencies.",
     )
     add_confidence_args(parser)


-def _write_ambiguity_csv(rows: list[dict[str, str]], csv_path: Path) -> None:
-    fieldnames = list(rows[0].keys()) if rows else ["artist", "title", "old_path", "reason"]
-    with csv_path.open("w", newline="", encoding="utf-8") as handle:
-        writer = csv.DictWriter(handle, fieldnames=fieldnames)
-        if rows:
-            writer.writeheader()
-            writer.writerows(rows)
-    print(f"csv_written={csv_path.as_posix()}")
-
-
-def _run_reconnection(
-    args: argparse.Namespace, old_root
-) -> tuple[dict[str, EntryRecord], dict[str, int], list[dict[str, str]], list[EntryRecord]]:
-    old_records = collection_records(old_root)
-    cache = TagCache(args.cache)
-    candidates = index_scan_roots(args.scan_roots, cache, refresh_cache=args.refresh_cache)
-    confidence = resolve_confidence(args)
-
-    # Volume identities are resolved once, up front, before any key
-    # provider is built: both the fingerprint tier's old-side resolver
-    # below and the candidate-side LOCATION re-encoding further down this
-    # function reuse the same resolved identities, rather than resolving
-    # twice.
-    volume_map = parse_volume_map(args.volume_map)
-    volume_identities: dict[Path, tuple[str, str]] = {}
-    for scan_root in args.scan_roots:
-        volume_identities[Path(scan_root)] = resolve_volume_identity(scan_root, old_records, volume_map)
-
-    # known_mounts anchors each scan root at its own filesystem anchor (the
-    # drive letter or POSIX root, e.g. "C:\\" or "/"), never at scan_root
-    # itself - decoded_path is volume-relative (relative to the volume
-    # root), not relative to an arbitrary scan-root subdirectory, so
-    # anchoring at scan_root would reconstruct the wrong absolute path for
-    # every record whose file sits outside that particular subdirectory.
-    known_mounts: dict[tuple[str, str], list[Path]] = {}
-    for scan_root, identity in volume_identities.items():
-        anchor = Path(scan_root).anchor
-        if anchor:
-            known_mounts.setdefault(identity, []).append(Path(anchor))
-
-    key_providers = []
-    fingerprint_stats: dict[str, int] = {}
-    if getattr(args, "fingerprint", False):
-        if fingerprint_key_provider is None:
-            raise _FingerprintUnavailable(
-                "fingerprint_key_provider unavailable (traktor_nml.fingerprint not installed)"
-            )
-        unavailable = fingerprint_unavailable_reason()
-        if unavailable is not None:
-            # Every way this tier can be unusable degrades to matching
-            # nothing, so an undiagnosed run looks exactly like one that
-            # searched and found no candidates. The reason is named rather
-            # than the dependency set listed, because the three pieces fail
-            # independently and "pyacoustid/fpcalc not available" is wrong
-            # advice when the missing piece is the chromaprint library and
-            # both of those are installed.
-            print(
-                f"fingerprint_dependency_missing={unavailable}; "
-                "--fingerprint tier will find no matches",
-                file=sys.stderr,
-            )
-        # The session owns the fpcalc child, so a per-file timeout is
-        # enforceable and a caller can terminate one mid-fingerprint.
-        fpcalc_session = FpcalcSession(
-            timeout=getattr(args, "fpcalc_timeout", FPCALC_TIMEOUT_SECONDS)
-        )
-        key_providers.append(
-            fingerprint_key_provider(
-                cache, candidates, fingerprint_stats, known_mounts, fpcalc_session
-            )
-        )
-
-    warn_refutation_disabled(args)
-    mapping, stats, ambiguity_rows = resolve_reconnection(
-        old_records, candidates, confidence, key_providers,
-        refute=should_refute(args),
-    )
-    stats = {**fingerprint_stats, **stats}
-
-    # Re-encode each winning candidate's real absolute path into a proper
-    # LOCATION using its scan root's resolved volume identity - the
-    # placeholder LocationParts a disk-scan candidate carries has no real
-    # VOLUME/VOLUMEID and is never written as-is.
-    for candidate in mapping.values():
-        if candidate.source_path is None:
-            continue
-        for scan_root, identity in volume_identities.items():
-            try:
-                candidate.source_path.relative_to(scan_root.resolve())
-            except ValueError:
-                continue
-            candidate.location = location_from_disk_path(candidate.source_path, *identity)
-            break
-
-    cache.flush()
-    return mapping, stats, ambiguity_rows, old_records
-
-
-def _apply_mapping_stdlib(
-    old_root, old_records: list[EntryRecord], mapping: dict[str, EntryRecord], stats: dict[str, int], dry_run: bool
-) -> None:
-    for record in old_records:
-        new_record = mapping.get(record.primary_key)
-        if new_record is None:
-            continue
-        ch = loc_attr_changes(record.location, new_record.location)
-        if ch:
-            stats["collection_locations_rewritten"] += 1
-            if not dry_run:
-                loc_elem = record.entry.find("LOCATION")
-                if loc_elem is not None:
-                    write_location_element(loc_elem, new_record.location)
-    resolver = CompareEntryResolver(mapping=mapping)
-    process_non_collection_entries(
-        old_root, {id(r.entry) for r in old_records}, resolver, stats, dry_run=dry_run
-    )
-
-
-def _handle_scan_reconnect_candidates(args: argparse.Namespace) -> int:
-    try:
-        old_tree = parse_xml(args.old_input)
-    except FileNotFoundError:
-        print(f"input_not_found={args.old_input.as_posix()}", file=sys.stderr)
-        return 2
-    except XML_PARSE_ERROR as exc:
-        print(f"xml_parse_error={args.old_input.as_posix()}: {exc}", file=sys.stderr)
-        return 2
-    try:
-        mapping, stats, ambiguity_rows, _old_records = _run_reconnection(args, old_tree.getroot())
-    except VolumeIdentityError as exc:
-        print(f"volume_identity_error={exc}", file=sys.stderr)
-        return 2
-    except _FingerprintUnavailable as exc:
-        print(f"fingerprint_unavailable={exc}", file=sys.stderr)
-        return 2
-
-    print(f"reconnectable={len(mapping)}")
-    for key, value in stats.items():
-        print(f"{key}={value}")
-    if args.csv is not None:
-        _write_ambiguity_csv(ambiguity_rows, args.csv)
-    return 0
-
-
-def _handle_rewrite_from_reconnect(args: argparse.Namespace) -> int:
-    def _collect_patches(old_root):
-        mapping, stats, ambiguity_rows, old_records = _run_reconnection(args, old_root)
-        patches, apply_stats = _collect_compare_patches(old_root, old_records, mapping)
-        merged_stats = {**apply_stats, **stats}
-        if args.csv is not None:
-            _write_ambiguity_csv(ambiguity_rows, args.csv)
-        return patches, merged_stats, []
-
-    def mutate_tree(old_root, dry_run):
-        mapping, stats, ambiguity_rows, old_records = _run_reconnection(args, old_root)
-        merged_stats = {
-            "collection_locations_rewritten": 0,
-            "other_locations_rewritten": 0,
-            "primarykeys_updated_from_collection": 0,
-            "primarykeys_unchanged": 0,
-            **stats,
-        }
-        _apply_mapping_stdlib(old_root, old_records, mapping, merged_stats, dry_run)
-        if args.csv is not None:
-            _write_ambiguity_csv(ambiguity_rows, args.csv)
-        return merged_stats, []
-
-    try:
-        return write_nml_safely(args.old_input, args.output, args.dry_run, _collect_patches, mutate_tree)
-    except VolumeIdentityError as exc:
-        print(f"volume_identity_error={exc}", file=sys.stderr)
-        return 2
-    except _FingerprintUnavailable as exc:
-        print(f"fingerprint_unavailable={exc}", file=sys.stderr)
-        return 2
+def _handle_scan_reconnect_candidates(args: argparse.Namespace) -> int:
+    return emit(render_scan_reconnect_candidates(reconnect_run.scan_reconnect_candidates(args), args))
+
+
+def _handle_rewrite_from_reconnect(args: argparse.Namespace) -> int:
+    return emit(render_rewrite_from_reconnect(reconnect_run.rewrite_from_reconnect(args), args))


 def register(subparsers, handlers: dict) -> None:
     scan_parser = subparsers.add_parser(
         "scan-reconnect-candidates",
         help="Match an old collection's tracks against disk-scan candidates without writing",
     )
     scan_parser.add_argument("old_input", type=Path)
     add_reconnect_args(scan_parser)
     handlers["scan-reconnect-candidates"] = _handle_scan_reconnect_candidates

     rewrite_parser = subparsers.add_parser(
         "rewrite-from-reconnect",
         help="Rewrite an old collection's LOCATIONs and PRIMARYKEYs from a disk scan",
     )
     rewrite_parser.add_argument("old_input", type=Path)
     rewrite_parser.add_argument("output", type=Path)
     rewrite_parser.add_argument(
         "--dry-run",
         action="store_true",
         help="Print stats without writing the output NML. Note: the --cache tag cache "
         "and the --csv ambiguity report are still written, since neither is the "
         "command's declared output - the cache is a scan speed-up and the report "
         "is a record of what the run saw.",
     )
     add_reconnect_args(rewrite_parser)
     handlers["rewrite-from-reconnect"] = _handle_rewrite_from_reconnect

```

**Documentation:**

```diff
--- a/traktor_nml/commands/reconnect_cmd.py
+++ b/traktor_nml/commands/reconnect_cmd.py
@@ -284,8 +284,14 @@ def add_reconnect_args(parser: argparse.ArgumentParser) -> None:
 
 
 def _handle_scan_reconnect_candidates(args: argparse.Namespace) -> int:
+    """Argparse wiring only: emit(render(core(args))). Holds no print
+    call and writes to neither stream itself - the command layer never
+    computes a value it prints, per tests/test_command_layer_printless.py."""
     return emit(render_scan_reconnect_candidates(reconnect_run.scan_reconnect_candidates(args), args))
 
 
 def _handle_rewrite_from_reconnect(args: argparse.Namespace) -> int:
+    """Argparse wiring only: emit(render(core(args))), same shape as
+    _handle_scan_reconnect_candidates above and covered by the same
+    printless guard."""
     return emit(render_rewrite_from_reconnect(reconnect_run.rewrite_from_reconnect(args), args))

```


**CC-M-002-011** (tests/test_reconnect_render_equivalence.py) - implements CI-M-002-009

**Code:**

```diff
--- /dev/null
+++ b/tests/test_reconnect_render_equivalence.py
@@ -0,0 +1,358 @@
+"""Section 3.2 equivalence tests: the renderer over the printless core
+must reproduce the recorded CLI output exactly, using the reconnect
+cases in tests/baselines/manifest.json as the expectation rather than
+restating them.
+"""
+
+from __future__ import annotations
+
+import contextlib
+import io
+import json
+import os
+import threading
+from pathlib import Path
+
+import pytest
+
+from traktor_nml import reconnect_run
+from traktor_nml.cli import build_parser
+from traktor_nml.diskscan import ScanCancelled
+from traktor_nml.reconnect_render import (
+    render_rewrite_from_reconnect,
+    render_scan_reconnect_candidates,
+)
+from traktor_nml.xmlio import parse_xml
+
+MANIFEST_PATH = Path(__file__).parent / "baselines" / "manifest.json"
+
+
+def _reconnect_cases() -> list[dict]:
+    cases = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
+    return [c for c in cases if c["argv"][0] in ("scan-reconnect-candidates", "rewrite-from-reconnect")]
+
+
+def _parse_args(argv: list[str]) -> object:
+    parser, _handlers = build_parser()
+    return parser.parse_args(argv)
+
+
+def _render_for_argv(argv: list[str], cwd: Path):
+    args = _parse_args(argv)
+    old_cwd = Path.cwd()
+    os.chdir(cwd)
+    try:
+        if argv[0] == "scan-reconnect-candidates":
+            result = reconnect_run.scan_reconnect_candidates(args)
+            return render_scan_reconnect_candidates(result, args), result
+        result = reconnect_run.rewrite_from_reconnect(args)
+        return render_rewrite_from_reconnect(result, args), result
+    finally:
+        os.chdir(old_cwd)
+
+
+def _lines_to_text(lines: list[str]) -> str:
+    return "\n".join(lines) + ("\n" if lines else "")
+
+
+@pytest.mark.parametrize("case", _reconnect_cases(), ids=lambda case: " ".join(case["argv"][:2]))
+def test_render_matches_recorded_case(fixture_corpus: Path, case: dict) -> None:
+    """render(core(args)) reproduces the recorded stdout, stderr and exit
+    code for each of the four reconnect manifest cases, using the same
+    fixture_corpus inputs the manifest case itself was recorded against."""
+    cwd = fixture_corpus.parent
+    rendered, _result = _render_for_argv(case["argv"], cwd)
+
+    stdout = _lines_to_text(rendered.stdout_lines)
+    stderr = _lines_to_text(rendered.stderr_lines)
+
+    expected_stdout = case["stdout"]
+    expected_stderr = case["stderr"]
+    if case.get("normalise_run_root"):
+        run_root = cwd.resolve().as_posix()
+        expected_stdout = expected_stdout.replace("{RUN_ROOT}", run_root)
+        expected_stderr = expected_stderr.replace("{RUN_ROOT}", run_root)
+
+    assert stdout == expected_stdout
+    assert stderr == expected_stderr
+    assert rendered.exit_code == case["exit_code"]
+
+
+def test_dropped_stats_key_breaks_the_comparison(fixture_corpus: Path) -> None:
+    """Negative control: proves the equality assertion above actually
+    detects drift rather than passing regardless of content. Observed to
+    fail the assertion below when run against an unmodified renderer."""
+    case = next(c for c in _reconnect_cases() if c["argv"][0] == "scan-reconnect-candidates")
+    rendered, _result = _render_for_argv(case["argv"], fixture_corpus.parent)
+
+    tampered = list(rendered.stdout_lines)
+    if len(tampered) > 1:
+        tampered.pop(1)
+
+    assert _lines_to_text(tampered) != case["stdout"]
+
+
+_SCAN_ARGV = [
+    "scan-reconnect-candidates", "recon/stale.nml",
+    "--scan-root", "recon/audio",
+    "--volume-map", "recon/audio", "D:", "D:",
+    "--match-confidence", "filename",
+    "--cache", "out/recon.tagcache.json",
+]
+
+
+def test_fingerprint_warning_lands_in_result_not_printed_by_core(
+    fixture_corpus: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """A non-None fingerprint_unavailable_reason() must become a warning
+    on ReconnectResult and render to stderr ahead of the refutation line,
+    rather than being printed by the core itself - the probe stub
+    replaces only that function and leaves fingerprint_key_provider bound
+    as the defensive import left it."""
+    if reconnect_run.fingerprint_key_provider is None:
+        pytest.skip("fingerprint.py not present")
+
+    monkeypatch.setattr(reconnect_run, "fingerprint_unavailable_reason", lambda: "stub reason")
+
+    argv = _SCAN_ARGV + ["--fingerprint"]
+    args = _parse_args(argv)
+    old_cwd = Path.cwd()
+    os.chdir(fixture_corpus.parent)
+    try:
+        buf_out, buf_err = io.StringIO(), io.StringIO()
+        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
+            result = reconnect_run.scan_reconnect_candidates(args)
+    finally:
+        os.chdir(old_cwd)
+
+    assert buf_out.getvalue() == ""
+    assert buf_err.getvalue() == ""
+    assert result.result is not None
+    assert any("stub reason" in warning for warning in result.result.warnings)
+
+    rendered = render_scan_reconnect_candidates(result, args)
+    assert rendered.stderr_lines[0].startswith("fingerprint_dependency_missing=stub reason")
+
+
+def test_fingerprint_warning_absent_when_reason_returns_none(
+    fixture_corpus: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """Negative control for test_fingerprint_warning_lands_in_result_not_printed_by_core:
+    proves the warning assertions above actually depend on
+    fingerprint_unavailable_reason() returning a reason, by monkeypatching it to
+    return None instead of "stub reason" and observing the warning disappear from
+    both ReconnectResult.warnings and the rendered stderr. Observed to fail
+    test_fingerprint_warning_lands_in_result_not_printed_by_core's warning
+    assertions when this stub replaces the "stub reason" stub."""
+    if reconnect_run.fingerprint_key_provider is None:
+        pytest.skip("fingerprint.py not present")
+
+    monkeypatch.setattr(reconnect_run, "fingerprint_unavailable_reason", lambda: None)
+
+    argv = _SCAN_ARGV + ["--fingerprint"]
+    args = _parse_args(argv)
+    old_cwd = Path.cwd()
+    os.chdir(fixture_corpus.parent)
+    try:
+        result = reconnect_run.scan_reconnect_candidates(args)
+    finally:
+        os.chdir(old_cwd)
+
+    assert result.result is not None
+    assert not any("stub reason" in warning for warning in result.result.warnings)
+    rendered = render_scan_reconnect_candidates(result, args)
+    assert not any(
+        line.startswith("fingerprint_dependency_missing=") for line in rendered.stderr_lines
+    )
+
+
+def test_fingerprint_key_provider_none_raises(fixture_corpus: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    """Setting fingerprint_key_provider to None proves the raise path is
+    distinct from the warn path rather than being masked by the probe
+    stub above."""
+    monkeypatch.setattr(reconnect_run, "fingerprint_key_provider", None)
+
+    argv = _SCAN_ARGV + ["--fingerprint"]
+    args = _parse_args(argv)
+    old_cwd = Path.cwd()
+    os.chdir(fixture_corpus.parent)
+    try:
+        result = reconnect_run.scan_reconnect_candidates(args)
+    finally:
+        os.chdir(old_cwd)
+
+    assert result.error is not None and result.error.startswith("fingerprint_unavailable=")
+
+
+def test_fingerprint_key_provider_present_does_not_raise_unavailable(
+    fixture_corpus: Path,
+) -> None:
+    """Negative control for test_fingerprint_key_provider_none_raises: proves the
+    fingerprint_unavailable= error above is actually caused by
+    fingerprint_key_provider being None, not by the --fingerprint flag on its own,
+    by leaving fingerprint_key_provider at its normal bound value and observing no
+    such error. Observed to fail test_fingerprint_key_provider_none_raises'
+    assertion when run without the monkeypatch that sets the provider to None."""
+    if reconnect_run.fingerprint_key_provider is None:
+        pytest.skip("fingerprint.py not present")
+
+    argv = _SCAN_ARGV + ["--fingerprint"]
+    args = _parse_args(argv)
+    old_cwd = Path.cwd()
+    os.chdir(fixture_corpus.parent)
+    try:
+        result = reconnect_run.scan_reconnect_candidates(args)
+    finally:
+        os.chdir(old_cwd)
+
+    assert result.error is None or not result.error.startswith("fingerprint_unavailable=")
+
+
+def test_no_refute_line_comes_from_renderer(fixture_corpus: Path) -> None:
+    """A no-refute run's refutation line is produced by the renderer via
+    shared_args.refutation_disabled_line, not restated as a literal
+    inside reconnect_render."""
+    argv = _SCAN_ARGV + ["--no-refute"]
+    rendered, _result = _render_for_argv(argv, fixture_corpus.parent)
+    assert any(line.startswith("refutation_disabled=") for line in rendered.stderr_lines)
+
+
+def test_no_refute_line_absent_when_source_returns_none(
+    fixture_corpus: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    """Negative control for test_no_refute_line_comes_from_renderer: proves
+    that assertion actually depends on shared_args.refutation_disabled_line
+    rather than passing regardless of --no-refute, by monkeypatching the
+    renderer module's bound reference to always return None and observing
+    the refutation line disappear from stderr. Observed to fail the
+    positive test's assertion when run against an unmodified renderer."""
+    import traktor_nml.reconnect_render as reconnect_render_module
+
+    monkeypatch.setattr(reconnect_render_module, "refutation_disabled_line", lambda args: None)
+    argv = _SCAN_ARGV + ["--no-refute"]
+    rendered, _result = _render_for_argv(argv, fixture_corpus.parent)
+    assert not any(line.startswith("refutation_disabled=") for line in rendered.stderr_lines)
+
+
+def test_on_progress_fires_and_cancel_raises(fixture_corpus: Path) -> None:
+    """An on_progress callback passed into the core fires at least once
+    with a path from the scan, and a pre-set cancel token raises
+    ScanCancelled out of the core rather than yielding a partial
+    result."""
+    args = _parse_args(_SCAN_ARGV)
+    old_cwd = Path.cwd()
+    os.chdir(fixture_corpus.parent)
+    try:
+        seen: list = []
+        reconnect_run.scan_reconnect_candidates(
+            args, on_progress=lambda done, total, path: seen.append(path)
+        )
+        assert seen, "on_progress never fired"
+
+        cancel = threading.Event()
+        cancel.set()
+        old_root = parse_xml(args.old_input).getroot()
+        with pytest.raises(ScanCancelled):
+            reconnect_run.run_reconnection(args, old_root, cancel=cancel)
+    finally:
+        os.chdir(old_cwd)
+
+
+def test_on_progress_does_not_fire_when_scan_root_is_empty(fixture_corpus: Path) -> None:
+    """Negative control for test_on_progress_fires_and_cancel_raises's
+    on_progress assertion: proves that assertion actually depends on the
+    scan finding files to report on, not on the callback firing
+    regardless of scan content, by pointing --scan-root at an empty
+    directory and observing on_progress never fire. Observed to fail
+    (seen non-empty) if run_reconnection ignored an empty scan tree and
+    fired progress anyway."""
+    empty_root = fixture_corpus.parent / "empty_audio"
+    empty_root.mkdir()
+    argv = [
+        "scan-reconnect-candidates", "recon/stale.nml",
+        "--scan-root", "empty_audio",
+        "--volume-map", "empty_audio", "D:", "D:",
+        "--match-confidence", "filename",
+        "--cache", "out/recon.tagcache.json",
+    ]
+    args = _parse_args(argv)
+    old_cwd = Path.cwd()
+    os.chdir(fixture_corpus.parent)
+    try:
+        seen: list = []
+        reconnect_run.scan_reconnect_candidates(
+            args, on_progress=lambda done, total, path: seen.append(path)
+        )
+    finally:
+        os.chdir(old_cwd)
+
+    assert seen == []
+
+
+def test_cancel_not_set_does_not_raise_scan_cancelled(fixture_corpus: Path) -> None:
+    """Negative control for test_on_progress_fires_and_cancel_raises: proves the
+    ScanCancelled raise above is actually gated on the cancel token being set,
+    not raised unconditionally by run_reconnection, by passing an unset Event
+    and observing the run complete instead of raising. Observed to fail
+    (raise ScanCancelled) if run_reconnection ignored the cancel token's
+    state rather than checking it."""
+    args = _parse_args(_SCAN_ARGV)
+    old_cwd = Path.cwd()
+    os.chdir(fixture_corpus.parent)
+    try:
+        old_root = parse_xml(args.old_input).getroot()
+        cancel = threading.Event()
+        result = reconnect_run.run_reconnection(args, old_root, cancel=cancel)
+    finally:
+        os.chdir(old_cwd)
+
+    assert result is not None
+
+
+def test_output_equal_to_input_never_starts_reconnection(fixture_corpus: Path) -> None:
+    """A rewrite-from-reconnect run whose output path equals its input
+    path is refused before reconnection starts - proved by asserting no
+    ReconnectResult is ever produced."""
+    argv = [
+        "rewrite-from-reconnect", "recon/stale.nml", "recon/stale.nml",
+        "--scan-root", "recon/audio",
+        "--volume-map", "recon/audio", "D:", "D:",
+        "--match-confidence", "filename",
+        "--cache", "out/recon.tagcache.json",
+    ]
+    args = _parse_args(argv)
+    old_cwd = Path.cwd()
+    os.chdir(fixture_corpus.parent)
+    try:
+        result = reconnect_run.rewrite_from_reconnect(args)
+    finally:
+        os.chdir(old_cwd)
+
+    assert result.reconnect is None
+    assert result.outcome is not None and result.outcome.error == "output_must_differ_from_input"
+
+
+def test_output_differs_from_input_starts_reconnection(fixture_corpus: Path) -> None:
+    """Negative control for test_output_equal_to_input_never_starts_reconnection:
+    proves the refusal above is gated on output_path equaling input_path, not on
+    rewrite-from-reconnect refusing to reconnect regardless of the paths given,
+    by pointing output at a different path and observing reconnection actually
+    starts. Observed to fail (reconnect is None) if the equality check applied
+    to differing paths as well."""
+    argv = [
+        "rewrite-from-reconnect", "recon/stale.nml", "out/reconnected.nml",
+        "--scan-root", "recon/audio",
+        "--volume-map", "recon/audio", "D:", "D:",
+        "--match-confidence", "filename",
+        "--cache", "out/recon.tagcache.json",
+        "--dry-run",
+    ]
+    args = _parse_args(argv)
+    old_cwd = Path.cwd()
+    os.chdir(fixture_corpus.parent)
+    try:
+        result = reconnect_run.rewrite_from_reconnect(args)
+    finally:
+        os.chdir(old_cwd)
+
+    assert result.reconnect is not None
```

**Documentation:**

```diff
--- a/tests/test_reconnect_render_equivalence.py
+++ b/tests/test_reconnect_render_equivalence.py
@@ -31,16 +31,33 @@ MANIFEST_PATH = Path(__file__).parent / "baselines" / "manifest.json"
 
 
 def _reconnect_cases() -> list[dict]:
+    """The manifest.json cases whose argv is one of the two reconnect
+    subcommands - the population section 3.2's parametrized test runs
+    against. If this ever returns an empty list, pytest silently
+    collects zero equivalence tests instead of failing the suite; there
+    is no explicit assertion here against that, so a manifest edit
+    removing both reconnect commands' cases would go unnoticed without
+    someone checking collected test counts. Every case here passes
+    --match-confidence filename; the manifest carries no --fingerprint
+    case and no strict/normal/loose/bare_name case for either reconnect
+    command, so those paths rest on the unit tests elsewhere in this
+    module and in test_write_shell_split.py rather than on this parity
+    check."""
     cases = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
     return [c for c in cases if c["argv"][0] in ("scan-reconnect-candidates", "rewrite-from-reconnect")]
 
 
 def _parse_args(argv: list[str]) -> object:
+    """Parse argv through the real CLI parser, so a case's args are the
+    same argparse.Namespace the CLI itself would build for it."""
     parser, _handlers = build_parser()
     return parser.parse_args(argv)
 
 
 def _render_for_argv(argv: list[str], cwd: Path):
+    """Run core(args) then render(result) for one manifest case, from
+    cwd - manifest paths are recorded relative to the fixture corpus
+    root, so the working directory must match before parsing argv."""
     args = _parse_args(argv)
     old_cwd = Path.cwd()
     os.chdir(cwd)
@@ -53,4 +70,9 @@ def _render_for_argv(argv: list[str], cwd: Path):
 
 
 def _lines_to_text(lines: list[str]) -> str:
+    """Join rendered lines the way emit() would have printed them, for
+    comparison against a manifest case's recorded stdout/stderr text.
+    test_dropped_stats_key_breaks_the_comparison proves this comparison
+    actually detects a dropped line rather than trivially matching
+    regardless of content."""
     return "\n".join(lines) + ("\n" if lines else "")

```


**CC-M-002-012** (tests/test_reconnect.py) - implements CI-M-002-010

**Code:**

```diff
--- a/tests/test_reconnect.py
+++ b/tests/test_reconnect.py
@@ -150,7 +150,7 @@ def test_fingerprint_flag_names_the_dependency_that_is_actually_missing(
         lambda: "the chromaprint shared library is not available",
     )
     monkeypatch.setattr(
-        "traktor_nml.commands.reconnect_cmd.fingerprint_unavailable_reason",
+        "traktor_nml.reconnect_run.fingerprint_unavailable_reason",
         lambda: "the chromaprint shared library is not available",
     )

```

**Documentation:**

```diff
--- a/tests/test_reconnect.py
+++ b/tests/test_reconnect.py
@@ -150,6 +150,10 @@ def test_fingerprint_flag_names_the_dependency_that_is_actually_missing(
         lambda: "the chromaprint shared library is not available",
     )
+    # Patched on both the defining module and reconnect_run's bound name:
+    # reconnect_run imports fingerprint_unavailable_reason by value at
+    # import time, so patching only traktor_nml.fingerprint would leave
+    # the core still calling the pre-patch function object.
     monkeypatch.setattr(
         "traktor_nml.reconnect_run.fingerprint_unavailable_reason",
         lambda: "the chromaprint shared library is not available",
     )

```


**CC-M-002-013** (traktor_nml/commands/_shared_args.py) - implements CI-M-002-013

**Code:**

```diff
--- a/traktor_nml/commands/_shared_args.py
+++ b/traktor_nml/commands/_shared_args.py
@@ -11,7 +11,9 @@ from __future__ import annotations
 import argparse
 import sys
 
 from ..confidence import MatchConfidence, parse_match_confidence
+from ..shared_args import refutation_disabled_line, resolve_confidence, should_refute
 
 
 def add_confidence_args(parser: argparse.ArgumentParser) -> None:
@@ -28,20 +30,6 @@ def add_confidence_args(parser: argparse.ArgumentParser) -> None:
     )
 
 
-def resolve_confidence(args: argparse.Namespace) -> MatchConfidence:
-    """Resolve the effective MatchConfidence: an explicit
-    --match-confidence always wins; otherwise --allow-artist-title-only
-    selects loose and its absence selects strict (DL-055)."""
-    if getattr(args, "match_confidence", None):
-        return parse_match_confidence(args.match_confidence)
-    return MatchConfidence.from_legacy_flag(args.allow_artist_title_only)
-
-
 def add_no_refute_argument(parser: argparse.ArgumentParser) -> None:
     parser.add_argument(
         "--no-refute",
@@ -52,26 +40,12 @@ def add_no_refute_argument(parser: argparse.ArgumentParser) -> None:
     )
 
 
-def should_refute(args: argparse.Namespace) -> bool:
-    """Whether the cascade should apply the size/duration check.
-
-    Pure: safe to call anywhere, any number of times. The warning is a
-    separate call precisely so this one carries no call-once contract -
-    reading a flag and announcing it are different jobs, and conflating
-    them meant a caller with two passes over the same run had to know to
-    cache the result or the warning printed twice.
-    """
-    return not getattr(args, "no_refute", False)
-
-
 def warn_refutation_disabled(args: argparse.Namespace) -> None:
     """Announce --no-refute once per run, if it is set.
 
     A run that ignores size and duration contradictions can commit a
     rewrite onto a file the collection's own numbers say is the wrong one,
     so the switch says so on every run rather than only in --help.
     """
-    if not should_refute(args):
-        print(
-            "refutation_disabled=size and duration contradictions will be ignored; "
-            "a candidate the collection's own FILESIZE/PLAYTIME_FLOAT contradict can now win a match",
-            file=sys.stderr,
-        )
+    line = refutation_disabled_line(args)
+    if line is not None:
+        print(line, file=sys.stderr)

```

**Documentation:**

```diff
--- a/traktor_nml/commands/_shared_args.py
+++ b/traktor_nml/commands/_shared_args.py
@@ -8,4 +8,9 @@ import argparse
 import sys
 
 from ..confidence import MatchConfidence, parse_match_confidence
+# Re-exported from shared_args.py: reconnect_run.py and reconnect_render.py
+# also need resolve_confidence/should_refute/refutation_disabled_line, and
+# commands/ is the only side of that import boundary allowed to depend on
+# the other (ref: DL-052). compare_cmd.py and reconnect_cmd.py import these
+# three names from this module rather than from shared_args.py directly.
 from ..shared_args import refutation_disabled_line, resolve_confidence, should_refute

```


**CC-M-002-014** (traktor_nml/shared_args.py) - implements CI-M-002-014

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/shared_args.py
@@ -0,0 +1,42 @@
+"""Confidence and refutation semantics shared below the commands/ layer.
+
+resolve_confidence, should_refute and refutation_disabled_line are pure
+functions of an argparse.Namespace with no argparse registration or
+stream dependency of their own. reconnect_run.py and reconnect_render.py
+import them from here rather than from commands/_shared_args.py, because
+commands/ imports downward into reconnect_run.py and reconnect_render.py
+and never the reverse - a core or renderer module importing from
+commands/ would create the cycle that direction forbids.
+commands/_shared_args.py imports these same three names from here, so
+every existing importer of them (compare_cmd.py, reconnect_cmd.py) keeps
+working unchanged.
+"""
+
+from __future__ import annotations
+
+import argparse
+from typing import Optional
+
+from .confidence import MatchConfidence, parse_match_confidence
+
+
+def resolve_confidence(args: argparse.Namespace) -> MatchConfidence:
+    """Resolve the effective MatchConfidence: an explicit
+    --match-confidence always wins; otherwise --allow-artist-title-only
+    selects loose and its absence selects strict (DL-055)."""
+    if getattr(args, "match_confidence", None):
+        return parse_match_confidence(args.match_confidence)
+    return MatchConfidence.from_legacy_flag(args.allow_artist_title_only)
+
+
+def should_refute(args: argparse.Namespace) -> bool:
+    """Whether the cascade should apply the size/duration check.
+
+    Pure: safe to call anywhere, any number of times. The warning is a
+    separate call precisely so this one carries no call-once contract -
+    reading a flag and announcing it are different jobs, and conflating
+    them meant a caller with two passes over the same run had to know to
+    cache the result or the warning printed twice.
+    """
+    return not getattr(args, "no_refute", False)
+
+
+def refutation_disabled_line(args: argparse.Namespace) -> Optional[str]:
+    """The refutation-disabled message text, or None when refutation is
+    still active. warn_refutation_disabled and reconnect_render both read
+    this so the literal has one definition: no manifest case sets
+    --no-refute for either reconnect command, so a second copy of the
+    text would drift invisibly.
+    """
+    if should_refute(args):
+        return None
+    return (
+        "refutation_disabled=size and duration contradictions will be ignored; "
+        "a candidate the collection's own FILESIZE/PLAYTIME_FLOAT contradict can now win a match"
+    )

```

**Documentation:**

```diff
--- a/traktor_nml/shared_args.py
+++ b/traktor_nml/shared_args.py
@@ -50,6 +50,9 @@ def refutation_disabled_line(args: argparse.Namespace) -> Optional[str]:
     this so the literal has one definition: no manifest case sets
     --no-refute for either reconnect command, so a second copy of the
     text would drift invisibly.
     """
+    # should_refute is the single source of truth for the flag reading;
+    # this function only decides the message text, so the two never
+    # disagree about whether refutation is active.
     if should_refute(args):
         return None

```


### Milestone 3: Anti-drift guard and decision log

**Files**: tests/test_command_layer_printless.py, traktor_nml/README.md, traktor_nml/CLAUDE.md, tests/CLAUDE.md, tests/test_baseline_parity.py

**Requirements**:

- a test asserts commands/reconnect_cmd.py contains no print call and no sys.stdout or sys.stderr write;traktor_nml/README.md's decision log gains one entry per plan decision - twelve, DL-046..DL-057 - each in the established reasoning-chain style
- tests/test_baseline_parity.py asserts the recorded stderr of every manifest case alongside the stdout, exit code and output bytes it already asserts, so a stream write leaked from anywhere in the pipeline fails parity rather than passing unnoticed
- the block starts at the next free number read off traktor_nml/README.md at HEAD at commit time (DL-046 at planning time) and shifts whole if it has moved;the inherited citations that blocked the resolve check are already cleared: tests/conftest.py and tests/test_baseline_parity.py cited DL-002 and DL-011, which resolved to nothing in traktor_nml/README.md, having come from docs/traktor_nml_tool_execution_plan.md's own plan-local numbering - the same defect this plan's numbering exists to prevent, left behind by an earlier plan. The surrounding prose already carried the reasoning in every case, so the bare refs were dropped and the module docstring now points at tests/baselines/manifest.schema.md, which does document the oracle's rules. The resolve check therefore starts from a clean state;the CLAUDE.md navigation indexes list every module and test module the split introduces

**Acceptance Criteria**:

- pytest passes with tests/baselines/manifest.json unmodified and PARITY_BASELINE_SHA256 unchanged
- and the run reports at least the baseline 191 passed and no more than the baseline 3 skipped (the 3 being the fingerprint tier);the guard test fails when a print call is reintroduced into commands/reconnect_cmd.py and the test says so in its own docstring;git fetch is run and traktor_nml/README.md at HEAD is re-read immediately before writing the entry
- and the twelve entries occupy consecutive numbers from the next free one there (DL-046..DL-057 at planning time
- shifted whole if another session has taken numbers);traktor_nml/README.md carries one entry per plan decision, so every reasoning chain here reaches the package log instead of surviving only in this artifact;traktor_nml/CLAUDE.md and tests/CLAUDE.md list every file the plan creates with a when-to-read trigger
- every DL number cited in any file under traktor_nml/ or tests/ resolves to a bullet that exists in traktor_nml/README.md's Design Decisions log, verified by reading them back at HEAD before the commit
- every one of the twelve manifest cases passes with stderr asserted, and the stderr assertion is demonstrated failing against a build that writes one extra line to stderr

**Tests**:

- tests/test_command_layer_printless.py

#### Code Intent

- **CI-M-003-001** `tests/test_command_layer_printless.py`: Parses traktor_nml/commands/reconnect_cmd.py with ast and asserts no call to print and no write on sys.stdout or sys.stderr appears anywhere in the module. The docstring states the invariant and records that the test was run against a copy with a print reintroduced and failed there; a companion test asserts the checker reports a violation for a synthetic source string containing a print call so the guard is exercised in both directions. (refs: DL-051)
- **CI-M-003-002** `traktor_nml/README.md`: The Design Decisions log gains one bullet for each of this plan's twelve decisions, DL-046 through DL-057, appended in numeric order after the section's current final entry, each in the surrounding reasoning-chain style rather than restating the plan's full text. This is the step that makes the reasoning durable: without it, twelve decision chains exist only in a planning artifact and never in the package's own log, which is the failure docs/2026-08-24-build-playlist-plan.md's own M-003 was written to prevent for its DL-024..DL-039. Because the plan's numbers ARE package numbers, the bullets carry the same identifiers the plan and the repo files cite, and no translation step exists to get wrong. Antecedents cited inside the entries are package numbers that already exist - DL-019 is rewrite.py's shared read/parse/atomic-write helpers - and are confirmed by re-reading traktor_nml/README.md at HEAD. That same re-read establishes the starting number: DL-045 was the last entry when this plan was written, so DL-046 is expected, but other sessions commit in parallel, so the README is re-read immediately before the entries are written and the whole block shifted if the high-water mark has moved. The package architecture section names reconnect_run.py and reconnect_render.py and the rule that commands/ imports downward into them. (refs: DL-046, DL-047, DL-052)
- **CI-M-003-003** `traktor_nml/CLAUDE.md`: The Files table carries a row for reconnect_run.py (the reconnect pipeline as one printless pass returning a ReconnectResult; read when changing what a reconnection run computes or what it reports) and a row for reconnect_render.py (every character the reconnect commands put on stdout or stderr, returned as buffered lines; read when changing reconnect output text or ordering), and the rewrite.py row names plan_and_write_nml as the printless write sequence under the write_nml_safely wrapper. The rows sit in the same read-when-you-need-this form as their neighbours, so the index still answers which file to open rather than restating what the modules do. (refs: DL-052)
- **CI-M-003-004** `tests/CLAUDE.md`: The Files table carries rows for test_write_shell_split.py (the write-shell outcomes the manifest cannot reach: output collision, text_patch_error ordering, callback exceptions, and that the function writes to no stream), test_reconnect_render_equivalence.py (renderer output compared against the recorded reconnect manifest cases, plus the fingerprint and no-refute warning paths the oracle does not exercise) and test_command_layer_printless.py (the guard that reconnect_cmd.py holds no print call), each with the when-to-read trigger its neighbours use. (refs: DL-051)
- **CI-M-003-005** `tests/test_baseline_parity.py::test_baseline_invocation_matches_stored_bytes`: The case comparison gains one assertion, on stderr, beside the exit_code, stdout and output-file assertions it already makes. The manifest already records a stderr field per case (the schema keys are argv, exit_code, normalise_run_root, output_files, stderr, stdout) and the portability guard at test_no_stored_stream_carries_a_host_path_separator already iterates both streams, so the data is present and only the assertion was missing; nothing in tests/baselines/manifest.json changes and PARITY_BASELINE_SHA256 does not move. stderr goes through the same normalise_run_root treatment stdout gets when the case sets that flag, so a captured temp path does not make the assertion machine-specific. All twelve recorded stderr values are empty, which is what makes this the leak detector: any stream write that escapes the renderer - from the core, from the write shell, or from index_scan_roots - turns a passing case red. The docstring states that and records that the assertion was demonstrated failing against a build with one extra stderr line, per the guard convention. This is the assertion CI-M-002-009's renderer equality cannot make: that test compares lines a function returns, so a stray print never enters the comparison. (refs: DL-057)
- **CI-M-003-006** `tests/CLAUDE.md` diagnostics row: The Files table also carries a row for test_scan_diagnostics.py - the scan diagnostics the parity oracle cannot reach, being the missing-mutagen line and the progress lines, captured directly off the core; read when changing what index_scan_roots reports or how it is transported - and the test_baseline_parity.py row names stderr among the streams that case comparison asserts. (refs: DL-056, DL-057)

#### Code Changes

**CC-M-003-001** (tests/test_command_layer_printless.py) - implements CI-M-003-001

**Code:**

```diff
--- /dev/null
+++ b/tests/test_command_layer_printless.py
@@ -0,0 +1,62 @@
+"""Guards the printless-command-layer boundary: reconnect_cmd.py holds no
+print call and writes to neither stream, all reconnect output living in
+reconnect_render.emit instead.
+"""
+
+from __future__ import annotations
+
+import ast
+from pathlib import Path
+
+RECONNECT_CMD = Path(__file__).parent.parent / "traktor_nml" / "commands" / "reconnect_cmd.py"
+
+
+def _violations(source: str) -> list[str]:
+    tree = ast.parse(source)
+    found = []
+    for node in ast.walk(tree):
+        if not isinstance(node, ast.Call):
+            continue
+        func = node.func
+        if isinstance(func, ast.Name) and func.id == "print":
+            found.append(f"print call at line {node.lineno}")
+        elif isinstance(func, ast.Attribute) and func.attr == "write":
+            value = func.value
+            if (
+                isinstance(value, ast.Attribute)
+                and isinstance(value.value, ast.Name)
+                and value.value.id == "sys"
+                and value.attr in ("stdout", "stderr")
+            ):
+                found.append(f"sys.{value.attr}.write at line {node.lineno}")
+    return found
+
+
+def test_reconnect_cmd_holds_no_print_call() -> None:
+    """The real module, unmutated, reports no violations - the baseline
+    the negative control below is checked against."""
+    source = RECONNECT_CMD.read_text(encoding="utf-8")
+    assert _violations(source) == []
+
+
+def test_reconnect_cmd_with_reintroduced_print_is_caught() -> None:
+    """Negative control for test_reconnect_cmd_holds_no_print_call: proves
+    the guard actually fails on its own invariant breaking, not merely on
+    an unrelated synthetic snippet, by splicing a print of a computed
+    value onto the end of the real reconnect_cmd.py source and running
+    _violations() over the mutated text. Observed to fail (violations ==
+    []) if _violations() were checking something other than this
+    module's own calls."""
+    source = RECONNECT_CMD.read_text(encoding="utf-8")
+    mutated = source + "\n\nprint(f'leaked={len(source)}')\n"
+
+    assert _violations(mutated) != []
+    assert _violations(source) == []
+
+
+def test_checker_detects_a_reintroduced_print() -> None:
+    """The checker also catches a print call in an unrelated synthetic
+    module, so _violations is exercised against more than one source
+    shape rather than only the real file."""
+    synthetic = "def handler(args):\n    print('leaked')\n    return 0\n"
+    assert _violations(synthetic) != []

```

**Documentation:**

```diff
--- a/tests/test_command_layer_printless.py
+++ b/tests/test_command_layer_printless.py
@@ -14,5 +14,13 @@ RECONNECT_CMD = Path(__file__).parent.parent / "traktor_nml" / "commands" / "reconnect_cmd.py"
 
 
 def _violations(source: str) -> list[str]:
+    """Walk source's AST for a call to print(...) or sys.stdout/stderr
+    .write(...). An AST walk rather than a text grep, because a grep for
+    "print(" would also match the word inside a docstring or comment
+    explaining why the module holds none. Verified to report a
+    violation when run against reconnect_cmd.py with a print call
+    spliced onto its source - see
+    test_reconnect_cmd_with_reintroduced_print_is_caught below - and to
+    report none against the real, unmutated module."""
     tree = ast.parse(source)
     found = []

```


**CC-M-003-002** (traktor_nml/README.md) - implements CI-M-003-002

**Code:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -25,6 +25,12 @@ Two write mechanisms coexist and never mix within one command:
 `commands/` holds one module per subcommand; `cli.py` discovers them by
 iterating the package rather than listing them, so adding a subcommand
 never requires editing `cli.py` (DL-048).

+`reconnect_run.py` (the printless reconnection core) and
+`reconnect_render.py` (the buffered stdout/stderr renderer for it) sit
+beside the other top-level modules, not inside `commands/`:
+`commands/reconnect_cmd.py` imports downward into them rather than the
+reverse, so a caller other than the CLI - a GUI review table - can reach
+the same core and renderer without going through argparse wiring (DL-052).
+
 `build-playlist` synthesizes its playlist node from an external track list
 with no source span to transplant, so it always takes the serialization
 path this split already sanctions for genuinely new content (DL-028), and
@@ -192,6 +198,15 @@ manufactures a difference the filesystem does not have - measured on the
   promoting it to strict so that stem upgrades match by default would have
   contradicted that precedent. `bare_name` drops the folder as well and
   reaches filename level only: one real library holds 208 files named
   `vocals` and 176 named `drums` from stem-extraction folders. These tiers
   are only reachable because DL-040 stopped size refuting across sources -
   a re-encode runs 0.23x to 49x the original, so the earlier band would
   have found these candidates and then discarded them (DL-045).
+- The reconnect commands run behind a printless core in `reconnect_run.py`
+  that returns a `ReconnectResult`, and a renderer in `reconnect_render.py`
+  that turns it into buffered stdout/stderr lines and an exit code,
+  because a GUI review table needs the mapping and the ambiguity rows as
+  objects while a run is in progress and a parsed transcript arrives only
+  at the end. `write_nml_safely` is a printing wrapper over a printless
+  `plan_and_write_nml` for the same reason: the reconnect stdout was
+  produced inside the write shell, and a reconnect-local write path would
+  duplicate the read/parse/patch/write skeleton DL-019 exists to prevent
+  (DL-047).
 - A candidate the check withdraws is counted as `refuted` alongside
   `unmatched` rather than folded into it, so "found it and declined" never
   reads as "the file is gone" - the same distinction DL-016 drew for

```

**Documentation:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -13,3 +13,8 @@ the same core and renderer without going through argparse wiring (DL-052).
 `build-playlist` synthesizes its playlist node from an external track list
 with no source span to transplant, so it always takes the serialization
 path this split already sanctions for genuinely new content (DL-028), and
+`shared_args.py` holds `resolve_confidence`/`should_refute`/
+`refutation_disabled_line` below `commands/`: both `reconnect_run.py` and
+`commands/_shared_args.py` import them from here, since a core module
+importing from `commands/` would create the reverse of the import
+direction DL-052 establishes.
@@ -204,3 +209,12 @@ manufactures a difference the filesystem does not have - measured on the
   duplicate the read/parse/patch/write skeleton DL-019 exists to prevent
   (DL-047).
+  `run_reconnection` and both reconnect cores also accept `on_progress`
+  and `cancel`, forwarded to `index_scan_roots`, so the same core can
+  report live indexing progress and be cancelled by a caller other than
+  the CLI; neither argparse handler passes them today, and that absence
+  is intended rather than dead code (DL-054). A cancelled scan raises
+  `ScanCancelled` rather than returning a partial `ReconnectResult`,
+  because a short candidate list is indistinguishable from a complete
+  one and would report most of the collection as missing - a wrong
+  answer delivered confidently.
 - A candidate the check withdraws is counted as `refuted` alongside

```


**CC-M-003-003** (traktor_nml/CLAUDE.md) - implements CI-M-003-003

**Code:**

```diff
--- a/traktor_nml/CLAUDE.md
+++ b/traktor_nml/CLAUDE.md
@@ -9,7 +9,7 @@
 | `model.py`         | `LocationParts`/`RewriteRule`/`EntryRecord`, LOCATION/PRIMARYKEY parsing; `decode_traktor_dir` is memoised because the cascade reads `decoded_dir` several times per record | Adding an identity field, changing LOCATION encode/decode  |
 | `xmlio.py`         | lxml/stdlib ET parsing wrapper                             | Changing how NML files are parsed or serialized            |
 | `textpatch.py`     | `apply_text_patches`/`ElemPatch` byte-preserving attribute writes | Changing how LOCATION/PRIMARYKEY attribute rewrites are applied |
-| `rewrite.py`       | Rule-based and compare-based rewrite patch collection, `write_nml_safely`; also `read_and_parse_source`, `write_bytes_atomically`, `path_collides`, and `write_row_report`, reusable read/write/report helpers other commands are expected to call, plus `add_no_refute_argument`/`warn_if_refutation_disabled`, the shared `--no-refute` surface | Modifying the rewrite/compare cascade, the write path, or the `--no-refute` flag |
+| `rewrite.py`       | Rule-based and compare-based rewrite patch collection; `plan_and_write_nml`, the printless read/parse/patch/write sequence, and `write_nml_safely`, the printing wrapper over it; also `read_and_parse_source`, `write_bytes_atomically`, `path_collides`, and `write_row_report`, reusable read/write/report helpers other commands are expected to call, plus `add_no_refute_argument`/`warn_if_refutation_disabled`, the shared `--no-refute` surface | Modifying the rewrite/compare cascade, the write path, or the `--no-refute` flag |
 | `confidence.py`    | `MatchConfidence` ordered enum (strict/loose/filename), the tier ladder each level admits, and the measured uniqueness behind each path-suffix tier's level | Adding a match tier or confidence level, or moving a tier between levels |
 | `matching.py`      | `record_keys`/`match_records` tiered match cascade; `_CASCADE`, the one table declaring every built-in tier and its properties; the size/duration refutation filter and its `refute` switch | Changing match-key tiers, matching tolerances, tier ordering, or ambiguity detection |
 | `diskscan.py`      | Filesystem candidate scanning for reconnection; candidate `filesize` is bytes on disk, not Traktor's kilobytes; optional `on_progress` and `cancel` for a UI driving the scan | Adding or changing disk-scan candidate discovery, progress reporting, or cancellation |
 | `discovery.py`     | Fuzzy artist/title ranking of disk and collection candidates; review-only, never selects or writes | Changing discovery scoring, normalisation, or stop words   |
 | `tagcache.py`      | Tag-read caching                                           | Changing tag cache key composition or eviction             |
 | `reconnect.py`     | Disk-scan reconnection; `location_from_disk_path` (candidate-side volume-relative-to-absolute transform) and `enforce_one_to_one`, the shared one-to-one assignment post-pass compare-based rewriting also calls | Modifying reconnection matching or destination-collision handling |
+| `reconnect_render.py` | Every character the reconnect commands put on stdout or stderr, returned as buffered lines rather than printed | Changing reconnect output text or ordering |
+| `reconnect_run.py` | The reconnect pipeline as one printless pass returning a `ReconnectResult` | Changing what a reconnection run computes or what it reports |
 | `volumes.py`       | VOLUME/VOLUMEID inference from existing collection paths, plus `local_path_for_location` resolving a location back to its on-disk path | Changing volume identity resolution or `--volume-map`      |

```

**Documentation:**

```diff
--- a/traktor_nml/CLAUDE.md
+++ b/traktor_nml/CLAUDE.md
@@ -13,2 +13,3 @@
-| `reconnect_run.py` | The reconnect pipeline as one printless pass returning a `ReconnectResult` | Changing what a reconnection run computes or what it reports |
+| `reconnect_run.py` | The reconnect pipeline as one printless pass returning a `ReconnectResult` | Changing what a reconnection run computes or reports, or its `on_progress`/`cancel` progress-reporting and cancellation channel |
+| `shared_args.py` | `resolve_confidence`/`should_refute`/`refutation_disabled_line`, pure functions of an argparse.Namespace shared below `commands/` | Changing confidence resolution or the refutation-disabled message |
 | `volumes.py`       | VOLUME/VOLUMEID inference from existing collection paths, plus `local_path_for_location` resolving a location back to its on-disk path | Changing volume identity resolution or `--volume-map`      |

```


**CC-M-003-004** (tests/CLAUDE.md) - implements CI-M-003-004

**Code:**

```diff
--- a/tests/CLAUDE.md
+++ b/tests/CLAUDE.md
@@ -7,6 +7,7 @@
 | `conftest.py`            | `run_tool`/`fixture_corpus` fixtures shared across test modules | Adding a test module, changing how the CLI is invoked under test |
 | `test_baseline_parity.py`| Byte-level parity oracle against `baselines/manifest.json`    | Changing any CLI subcommand's output, exit code, or written bytes |
 | `test_cli_contract.py`   | Subcommand surface + `--allow-artist-title-only`/`--match-confidence` alias contract; splice/split malformed-input and atomic-write tests | Adding/renaming a subcommand, changing legacy-flag equivalence |
+| `test_command_layer_printless.py` | Guard that `commands/reconnect_cmd.py` holds no print call and writes to neither stream | Changing `reconnect_cmd.py`'s handlers, or the printless-command-layer convention |
 | `test_compare.py`        | Compare-based rewrite input-protection and destination-collision tests | Changing `rewrite_from_collection_compare` or `compare_cmd.py`'s write path |
 | `test_diskscan.py`       | Disk-scan candidate discovery tests                            | Changing `diskscan.py`                                        |
 | `test_fpcalc_session.py` | Owned fpcalc child: output parsing, per-file timeout, mid-fingerprint termination, and that a cancelled session spawns nothing further. Uses a stub fpcalc via the FPCALC env var | Changing `FpcalcSession`, the fingerprint timeout, or cancellation |
@@ -15,6 +16,7 @@
 | `test_parity_baseline.py`| Tamper-evidence for the oracle itself: pins `manifest.json`'s own SHA-256 | Regenerating the baseline, or changing what the pin guarantees |
 | `test_reconnect.py`      | Reconnection matching, path-suffix tiers, size/duration refutation and `--no-refute`, one-to-one assignment, and the `_CASCADE`/ladder consistency checks | Changing `reconnect.py`, `volumes.py`, `matching.py`'s tiers, a matching tolerance, or the cascade table |
+| `test_reconnect_render_equivalence.py` | Renderer output compared against the recorded reconnect manifest cases, plus the fingerprint and no-refute warning paths the oracle does not exercise | Changing `reconnect_run.py` or `reconnect_render.py` |
 | `test_fingerprint.py`    | Fingerprint tier end to end: generates two-bitrate audio fixtures with ffmpeg, pins the duration pre-filter and the degrade-on-broken-comparison path, and gates each test on the dependency it actually needs | Changing `fingerprint.py`, or a test here skipping unexpectedly |
 | `test_spans.py`          | Byte-span scanner, `OutputBuilder`, count-attribute recalculation tests | Changing `spans.py`                                           |
 | `test_splice.py`         | Splice merge/conflict-resolution tests                         | Changing `splice.py` or `playlists.py`                        |
@@ -22,6 +24,7 @@
 | `test_tracklist.py`      | External track-list parsing and per-line resolution tests      | Changing `tracklist.py`                                       |
 | `test_build_playlist.py` | build-playlist synthesis, insertion and CLI-surface tests       | Changing `buildplaylist.py`, its insertion point, or `commands/build_playlist_cmd.py` |
 | `test_xmlio.py`          | `parse_xml_bytes`'s lxml/stdlib backend-selection tests          | Changing `xmlio.py`'s parsing helpers                        |
+| `test_write_shell_split.py` | Write-shell outcomes the manifest cannot reach: output collision, `text_patch_error` ordering, callback exceptions, and that `plan_and_write_nml` writes to no stream | Changing `plan_and_write_nml` or `write_nml_safely` |

```

**Documentation:**

```diff
--- a/tests/CLAUDE.md
+++ b/tests/CLAUDE.md
@@ -13,2 +13,2 @@
 | `test_reconnect.py`      | Reconnection matching, path-suffix tiers, size/duration refutation and `--no-refute`, one-to-one assignment, and the `_CASCADE`/ladder consistency checks | Changing `reconnect.py`, `volumes.py`, `matching.py`'s tiers, a matching tolerance, or the cascade table |
-| `test_reconnect_render_equivalence.py` | Renderer output compared against the recorded reconnect manifest cases, plus the fingerprint and no-refute warning paths the oracle does not exercise | Changing `reconnect_run.py` or `reconnect_render.py` |
+| `test_reconnect_render_equivalence.py` | Renderer output compared against the recorded reconnect manifest cases (all four pass `--match-confidence filename`; no `--fingerprint` or strict/normal/loose/bare_name case exists), plus the fingerprint and no-refute warning paths the oracle does not exercise | Changing `reconnect_run.py` or `reconnect_render.py` |

```


## Execution Waves

- W-001: M-001
- W-002: M-002
- W-003: M-003

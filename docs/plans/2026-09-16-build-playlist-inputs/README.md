# Plan

## Overview

build-playlist accepts only a plain-text 'Artist - Title' list, which reduces every entry to artist and title and so reaches only the LOOSE artist_title tier, producing ambiguous rows. Operators hold their track lists as CSV exports, M3U/M3U8 playlists and folders of audio files, which carry file names, paths, sizes and durations the matching cascade already knows how to use.

**Approach**: Give every input format one seam - an ordered list of Candidate values carrying a fully populated EntryRecord or none for an unparseable entry - that tracklist.resolve_candidates and buildplaylist.assemble_output consume through the unchanged resolution, refusal, synthesis and splice path. A golden corpus recorded before the seam proves the text path byte-identical. traktor_nml/playlistinput.py detects the format and reads text, folder (non-recursive, numeric-aware name order, indexed through diskscan.index_files), M3U/M3U8 (present files indexed, absent paths kept as path-string records with #EXTINF data) and CSV (one column definition shared with a header-only template). The CLI and the /build-playlist screen both call read_input; the screen follows an updated artboard, offers a file and a folder chooser and a CSV template written through a native SAVE dialog or ui.download, and closes on a served-page record. The repository keeps its own DL log (high-water DL-273), so decision numbering starts at DL-274.

## Planning Context

### Decision Log

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-274 | The one seam every input format meets is an ordered list of Candidate values (line_number, raw_text, artist, title, record: EntryRecord or None). A Candidate whose record is None is an unparseable entry; every other Candidate carries the EntryRecord the matching cascade reads as its old side. tracklist.resolve_candidates resolves the list and buildplaylist.assemble_output takes the list in place of tracklist_text. | Refusal (DL-027, DL-036), report rows, synthesis and splice already depend only on per-entry outcome plus line_number/raw_text/artist/title -> an unparseable line is the only reason text parsing leaks past the parser -> folding unparseable into the Candidate list (record None) lets every format hand over one list and leaves resolution, refusal, synthesis and splice with a single input shape |
| DL-275 | Each format fills every EntryRecord field its source genuinely carries: a folder file or an M3U path present on this machine is indexed through diskscan (size in KB, tags, duration, file name, placeholder location, source_path set); an M3U path absent on this machine keeps file name, decoded folder parts, #EXTINF artist/title and #EXTINF duration with source_path None; a CSV row keeps artist, title, album, duration and file name. No format reduces its input to artist and title. | record_keys emits artist_title_size_time, artist_title_file, file_size_time, path_suffix_3/2/1 and bare_name_in_folder only when their fields are non-empty -> a candidate reduced to artist/title reaches only the artist_title tier, the tier that yields the ambiguous rows text lists produce -> keeping every carried field is the whole value of file-based input |
| DL-276 | Resolution stays at a fixed MatchConfidence.LOOSE for every format; no --match-confidence option is exposed. | LOOSE admits every STRICT tier plus artist_title, path_suffix_2/1 and bare_name_in_folder -> file-derived candidates already reach the stricter tiers at LOOSE because the cascade tries tiers strongest first -> FILENAME would add bare_name, which collides with stem component files (208 named vocals in one library), so LOOSE stays the one level (DL-032's rule, with its reason widened from text-only input to every input) |
| DL-277 | No exact-location pre-pass runs before the cascade; a folder or M3U candidate resolves through match_records alone. | match_records marks a tier with more than one surviving candidate ambiguous but keeps descending, and stops only on a single-candidate tier -> a collection holding one track at two locations is ambiguous at artist_title_size_time yet resolves uniquely at path_suffix_3, whose key includes three folder names -> a pre-pass would need collection VOLUME naming (volumes.py) for no additional resolution; a test pins the two-location case to matched |
| DL-278 | Candidates from every format sit on the old side of match_records and the collection on the new side, the direction resolve_tracklist already uses. | _refutation_reason computes cross = old.from_disk != new.from_disk, which is symmetric, and every tolerance compares against max() of both sides -> refutation gives the same verdict in either direction; ambiguity is counted per old record, which is one candidate per call -> the text path's direction carries over unchanged, and a test pins a disk candidate refuted by duration and one kept across a size difference |
| DL-279 | The plain-text path is proven byte-identical by a golden corpus recorded from the pre-seam code before any seam change lands: tests/baselines/build_playlist_text/ holds per case the argv, stdout, stderr, exit code and output bytes (uuid4 patched to a fixed value), and tests/test_build_playlist_text_parity.py replays each case through run_tool. tests/baselines/manifest.json is not touched. | manifest.json has no build-playlist case and must not be regenerated -> unit tests alone would pass a refactor that shifts line numbering, report row order or stats key order -> a separate golden directory recorded at the pre-seam commit is the only oracle that fails on those shifts; the record step names the commit it ran against |
| DL-280 | The stats dict keeps its keys and order (lines_read, lines_resolved, unresolved_unparseable, unresolved_unmatched, unresolved_ambiguous, playlist_name, entries_written) for every format. The CLI prints input_format=<name> and input_encoding=<codec> before those keys only when the input is not plain text. | CLI stdout for a text run is part of the byte-parity oracle -> any key added to stats changes that stdout -> format and encoding travel on the InputRead result beside the candidates, and the CLI prints them only for csv, m3u and folder runs, whose output has no prior bytes to preserve |
| DL-281 | traktor_nml/playlistinput.py is the nicegui-free input module: detect_format(path) (a directory is folder; .csv is csv; .m3u and .m3u8 are m3u; any other file is text), read_input(path, fmt) -> InputRead(format, encoding, candidates) or raises InputReadError(code), and the CSV column definition with csv_template_bytes(). | DL-069 requires every parser and every decision rule to be reachable by the suite without nicegui -> the CLI handler and app.py's _run_build_playlist both need the same read-decode-parse step, which today each duplicate for text -> one module owning detection, decode fallback and dispatch leaves both call sites a single call, so the GUI and CLI cannot diverge (DL-262) |
| DL-282 | Any file whose suffix is not .csv, .m3u or .m3u8 is read as plain text with utf-8-sig strict decoding and the tracklist_decode_error refusal, exactly as before the seam. | Plain-text track lists carry .txt, no suffix, or arbitrary suffixes in the wild -> narrowing text to .txt would refuse inputs that work today and break the parity corpus -> suffix-based detection names only the three structured formats and leaves everything else on the text path |
| DL-283 | Decoding: text stays utf-8-sig strict; .m3u8 is utf-8-sig strict; .m3u and .csv try utf-8-sig and fall back to cp1252; InputRead.encoding names the codec used and both surfaces show it. | RFC 8216 section 4 defines the .m3u8 extension as a UTF-8 playlist, so .m3u8 decodes strictly as UTF-8, while a plain .m3u declares no encoding and Windows writes legacy-encoded text in the system ANSI code page, which Microsoft's code page reference names as Windows-1252 (cp1252) for Western European locales; Excel's 'CSV (Comma delimited)' save type writes that ANSI code page and its 'CSV UTF-8' type a BOM-prefixed UTF-8 file -> trying utf-8-sig first accepts both UTF-8 variants and cp1252 covers the ANSI case -> cp1252 decodes every byte, so a wrong guess shows as mojibake rather than an error -> naming the codec on every csv/m3u run makes a mojibake guess visible to the operator; text keeps its refusal so its parity holds |
| DL-284 | One CSV column definition, CSV_COLUMNS = (Artist, Title, Album, Duration, File name), with Artist and Title required. csv_template_bytes() is the header row built from CSV_COLUMNS, UTF-8 with BOM and CRLF, no data row. The parser matches headers case-insensitively after strip, ignores unrecognised columns, and refuses a file missing Artist or Title with csv_header_missing. | A template whose header drifts from the parser's accepted names stops being uploadable -> deriving both from one tuple removes the drift, and a test round-trips the template through the parser to zero candidates and no error -> an example row left in by accident becomes an unmatched row that refuses the run, so the template is header-only and the guidance lives on screen; the BOM makes Excel open the UTF-8 file correctly |
| DL-285 | The CSV delimiter is chosen from the header line alone: comma if splitting on comma yields both Artist and Title headers, else semicolon if splitting on semicolon does, else csv_header_missing. csv.Sniffer is not used. | Microsoft's Excel documentation states that saving as CSV uses the list separator from Windows regional settings, which is ';' in locales whose decimal symbol is ',' -> context.json left sniff-or-refuse open; refusing would reject every CSV an Excel user in such a locale saves, and the downloaded template (DL-284) reopened and re-saved there becomes semicolon-separated, so refusing breaks the template round trip -> csv.Sniffer guesses from data rows and misreads titles containing commas -> the header is known text, so testing comma then semicolon against the required Artist/Title header names is deterministic, and any other file fails with the named csv_header_missing code |
| DL-286 | A CSV row with empty Artist or Title becomes an unparseable Candidate; a row with every cell empty is skipped. Duration accepts seconds (215, 215.4), m:ss and h:mm:ss; an unparseable duration leaves playtime_float empty rather than refusing the row. line_number is the physical line the row starts on (header is line 1, so it equals the spreadsheet row number) and raw_text is that row's text as read. | The report must point the operator at the row to fix -> the spreadsheet row number is what they see in Excel -> a bad duration is weaker evidence missing, not a malformed entry, so it degrades to artist/title tiers instead of blocking a run |
| DL-287 | M3U parsing: #EXTM3U and other # lines are directives; #EXTINF:<secs>,<Artist - Title> attaches to the next path line (seconds <= 0 give no duration; the display text splits on its first ' - ' into artist/title, otherwise both stay empty). A path line is resolved against the playlist's folder when relative; a scheme://-style URL line is an unparseable Candidate. A path that is an existing file on this machine is indexed through diskscan.index_files; any other path is a path-string record. line_number is the path line's number and raw_text the path line. #EXTINF duration and display text fill only a path-string record; a path indexed through index_files takes playtime, artist and title from the file itself and ignores its #EXTINF. | The collections span machines, so a Mac-authored M3U names /Users/... paths absent on this PC -> a path-string record still carries file name and folder parts, which path_suffix_3/2/1 and bare_name_in_folder key on, plus #EXTINF artist/title/duration for artist_title and duration refutation -> a present file adds size and tags on top; a URL has no file name to match on -> a present file's measured duration is at least as precise as #EXTINF's integer seconds, so #EXTINF is carried only where nothing better exists; a path-string record against a collection PLAYTIME_FLOAT is non-disk on both sides, and integer truncation stays under the 1.0s tolerance (R-001) |
| DL-288 | A path-string record decodes the path with PureWindowsPath when it carries a drive letter or backslash and PurePosixPath otherwise, strips the anchor, and encodes the folder parts through model.encode_traktor_dir into a placeholder LocationParts with empty volume and volumeid. | _folder_parts reads location.decoded_dir, so path-suffix tiers need DIR in Traktor's /: encoding -> a Windows path parsed as POSIX yields one folder part containing backslashes and matches nothing -> choosing the flavour from the path's own syntax gives the same folder parts whichever machine reads the playlist |
| DL-289 | Folder input lists only the chosen directory's own files (no recursion) whose names pass diskscan's audio-extension check, ordered by a numeric-aware key: the casefolded name split into digit and non-digit runs, digit runs compared as integers, ties broken by the plain name. line_number is the 1-based position in that order and raw_text the file name. | User decided this folder only, in name order -> a plain string sort puts '10 - x' before '2 - y' while Explorer and Finder do not -> a digit-run key matches what the operator sees in their file manager, and the plain-name tiebreak keeps the order total so the playlist order is deterministic |
| DL-290 | diskscan.index_files(paths, cache=None) indexes an explicit ordered list: one EntryRecord per path in the given order, duplicates kept, no directory walk, built through the same per-file record builder index_scan_roots uses. A path whose stat() fails raises InputReadError-equivalent DiskReadError naming the path; unreadable tags produce a record with empty tag fields, never a dropped file. With cache None, tags are read directly and no cache file is read or written. | A partial candidate list is indistinguishable from a complete one (ScanCancelled's docstring) -> index_scan_roots counts a stat failure and skips the file, which for a playlist silently shortens it -> an explicit list must raise instead; duplicates are kept because playlist order and repetition are authoritative (DL-037); build-playlist writes no side files, so no tag cache path is introduced and the TIER2 side-effect allowlist is unchanged |
| DL-291 | index_scan_roots keeps its records, stats, diagnostics and cache behaviour; only the per-file EntryRecord construction moves into a helper both functions call. | reconnect and discover depend on index_scan_roots and are pinned by manifest.json cases -> changing its skip-on-OSError or dedupe rule would change those baselines -> sharing just the record builder gives index_files identical record fields without altering the walk |
| DL-292 | An input that yields zero candidates (empty folder, header-only CSV, M3U with no path lines) runs to the existing no_entries_resolved refusal; an input that cannot be read at all refuses before assembly with one named code: input_not_found=<path> (the input path cannot be opened), tracklist_decode_error=<path> (strict decode failed), csv_header_missing (no delimiter yields Artist and Title), input_read_error=<path> (diskscan.DiskReadError raised by index_files for a folder file or present M3U file, carrying that file's posix path), input_format_mismatch=<format> (--input-format folder on a non-directory, or a file format on a directory). | DL-036 already refuses a run with zero resolved entries -> an empty input reaching it gives the operator the same sentence as an all-unmatched list -> only unreadability needs its own code; diskscan must stay free of playlistinput's error type, so index_files raises DiskReadError and playlistinput translates it at its call sites, naming the file that failed rather than the folder so the operator can act on it; an explicit --input-format contradicting what the path is cannot be parsed either way, and naming the requested format tells the operator which flag to drop |
| DL-293 | A file in a folder or M3U that the collection does not hold is reported as unmatched; build-playlist never adds ENTRY elements. | User decided build-playlist stays a playlist tool -> adding entries would need LOCATION volume identity, INFO fields and a COLLECTION count change -> the unmatched report plus Allow unmatched already covers the case |
| DL-294 | The CLI keeps its positional tracklist argument, which accepts a file of any supported format or a directory; --input-format {auto,text,csv,m3u,folder} (default auto) overrides detection. No CLI subcommand writes the CSV template; build-playlist --help lists the CSV columns from CSV_COLUMNS. | Renaming the positional or adding a subcommand changes the command surface test_cli_contract.py and test_gui_command_classification.py pin -> an override flag covers a mis-suffixed file without that churn -> the template is a GUI affordance; a CLI user reads the header from --help, drawn from the same tuple |
| DL-295 | The /build-playlist screen offers 'Choose file...' (text, CSV, M3U) and 'Choose folder...' for the input, shows the detected format and, after a run, the encoding, shows the CSV columns and a 'Download CSV template' control, and renames the report to entries. In native mode the template is written through a pywebview SAVE dialog (file_picker.pick_save_path); served over HTTP it is sent with ui.download. Artboard first (DL-071). | pywebview blocks browser downloads by default -> ui.download in the native window does nothing -> a SAVE dialog plus write_bytes_atomically is the native path, ui.download the served path, both fed the same csv_template_bytes(); every CSS rule lives in theme.py (DL-069) and plurals go through wording.plural |
| DL-296 | buildplaylist_view.run_summary and form_errors use format-neutral words: 'entry/entries' via wording.plural, 'Choose an input.' for the missing input, and a run on csv/m3u/folder input appends the format and encoding it read; the counts are read off result.stats and result.unresolved_rows (DL-215). | The sentence 'track-list lines did not resolve' is false for a folder of files -> DL-268 keeps condition names aligned with the CLI, which the sentences still name -> neutral nouns keep one sentence true for every format |
| DL-297 | The /build-playlist screen's single 'Target folder (optional)' input is a defect and is replaced by two controls that never share a value. (1) Output folder: a 'Choose folder...' button through file_picker.pick_file_or_folder(directories_only=True) with the chosen path displayed; the output .nml is <output folder>/<playlist name>.nml, and with no folder chosen it is the base collection's own directory. This is the GUI counterpart of the CLI's positional output path. (2) Playlist folder: a chooser listing the base collection's existing FOLDER nodes, read nicegui-free by playlists.playlist_folder_choices(root) as (display path, NAME, unique) in tree order with the root excluded, plus a 'Collection root' option meaning none; the chosen NAME is passed to assemble_output as target_folder, the counterpart of --target-folder, and None for the root. A FOLDER whose NAME is held by another FOLDER is listed disabled with its path, because assemble_output resolves target_folder by NAME alone and would refuse it as target_folder_ambiguous. The chooser is refilled when a base collection is chosen. FormInputs.target_folder is replaced by output_dir and playlist_folder. The CLI's flags and meanings are unchanged. The playlist-folder chooser is enabled only while the Full collection switch is on; while it is off the chooser is disabled showing 'Collection root', the note 'Playlist folder applies only with Full collection on. Off, the file holds this one playlist at its root.' sits under it, and _current_inputs sends playlist_folder '' so no target_folder reaches assemble_output. The output-folder chooser applies either way. This supersedes DL-272's statement that no separate output-path control exists on the form. | _derive_build_playlist_output_path joins the input's string onto the base's directory as a disk subdirectory, while _run_build_playlist passes the same string to assemble_output, where _find_target_subnodes looks it up as a Traktor FOLDER NAME inside PLAYLISTS -> one value cannot be both a disk path and a playlist folder name, so a run naming a folder writes into a disk directory named after a Traktor folder, or asks for a Traktor folder named after a disk directory -> build_playlist_cmd.py already separates the two as the positional output Path and --target-folder -> the user chose both meanings as two controls: a disk folder chosen the way the other screens choose paths (pick_file_or_folder), and a playlist folder chosen from what the collection holds so it cannot name a folder that does not exist -> listing and disabling same-named folders reads the collection nicegui-free (DL-069) and keeps GUI and CLI resolution identical (DL-262) instead of changing the core's name lookup and with it the CLI's --target-folder meaning -> both controls are drawn on Specs.dc.html first (DL-071) and use the artboard's existing button and label rules, so a separate app-wide button fill change applies to them unchanged -> with Full collection off (the default) both _run_build_playlist and build_playlist_cmd pass the assembled output through split.build_output([playlist_name]), which replaces the root SUBNODES children with the kept PLAYLIST nodes alone (split.py: 'Every output is a flat playlist-entry subset'); a probe placing playlist Set under FOLDER Sets and isolating it wrote Set directly under $ROOT with no Sets folder -> a playlist-folder choice changes nothing in the default file, so the chooser is enabled only when it changes the output and states why otherwise |

### Rejected Alternatives

| Alternative | Why Rejected |
|---|---|
| Parse M3U and folder inputs down to 'Artist - Title' text and reuse parse_tracklist | Discards size, duration, path and file name, leaving only the artist_title tier and its ambiguous rows (ref: DL-275) |
| Add collection ENTRY elements for files the collection does not hold | User chose report-as-unmatched; build-playlist stays a playlist tool (ref: DL-293) |
| Recursive folder walk or tag track-number ordering | User chose this folder only, sorted by name (ref: DL-289) |
| Plain string sort for folder order | Misorders unpadded track numbers ('10 - ...' before '2 - ...') (ref: DL-289) |
| CSV with Artist and Title only | User chose optional Album, Duration and File name so rows reach stronger tiers (ref: DL-284) |
| An example row in the CSV template | Left in by accident it becomes an unmatched row that refuses the run (ref: DL-284) |
| csv.Sniffer delimiter detection | Guesses from data rows and misreads titles containing commas; header-based choice is deterministic (ref: DL-285) |
| ui.download in the native window | pywebview blocks browser downloads by default (ref: DL-295) |
| An exact-location pre-pass keyed on collection VOLUME naming | match_records descends past an ambiguous tier to path_suffix_3, so the pre-pass resolves nothing more and needs volume identity (ref: DL-277) |
| Record the text baseline into tests/baselines/manifest.json | manifest.json must not be regenerated (ref: DL-279) |
| Report input_format and input_encoding as stats keys | Changes CLI stdout for text runs and breaks byte parity (ref: DL-280) |
| A persistent tag cache for folder and M3U reads | Introduces a side file build-playlist does not write and widens the TIER2 side-effect allowlist (ref: DL-290) |

### Constraints

- traktor_nml/README.md is the decision-log authority; its high-water mark is DL-273 and this plan mints from DL-274
- DL-069: only app.py, file_picker.py and __main__.py import nicegui; parsers, template bytes and decision rules live in nicegui-free modules; every CSS rule lives in theme.py
- DL-071: design/build-playlist/Specs.dc.html is drawn before the screen changes
- DL-084 as amended by DL-169: the screen milestone closes on a served-page record in docs/ with its verdict-row digest in tests/test_docs_browser_record_structure.py
- The plain-text path produces byte-identical CLI stdout, stderr, exit code and output against a golden corpus recorded before the seam
- DL-027 and DL-036 refusals hold; unresolved report columns stay line_number, raw_text, artist, title, kind
- Every guard is shown failing first against a named mutation with the verbatim output in its docstring (DL-189)
- app.py is CRLF (write with newline=''); theme.py and tests/ are LF; docs/CLAUDE.md and tests/CLAUDE.md are CRLF
- Plurals go through traktor_nml/gui/wording.plural; a sentence naming a count reads it off the model (DL-215)
- Documentation describes code as it stands, with no change-relative wording and no citation of a source for something it does not say
- Never regenerate tests/baselines/manifest.json or fixture/w002gatefix2; never restore a file with git checkout - copy it aside first and restore from the copy; never write into build/ or dist/; never install into the system interpreter; never spawn background agents
- Suite interpreter: C:\Users\marcu\AppData\Local\Python\pythoncore-3.14-64\python.exe
- matching.py and confidence.py are not edited
- Existing plan repository traktor-nml-tool-plan is archival; this plan lands under traktor-nml-tool/docs/plans/

### Known Risks

- **#EXTINF durations are integer seconds, so a same-source comparison against a collection PLAYTIME_FLOAT can differ by up to 1.0s, the abs tolerance edge**: M-003: #EXTINF duration fills only path-string records and a present file's own duration replaces it (DL-287); tests/test_playlistinput_m3u.py pins a 0.9s truncation matched and a 5s gap refuted; if real playlists refute at the edge, drop #EXTINF duration rather than touch matching.py
- **cp1252 fallback misdecodes a file in another single-byte codepage without any error**: M-005 prints input_encoding on the CLI and M-007 shows the encoding in run_summary for every csv and m3u run; M-003 and M-004 tests pin a cp1252 file reporting cp1252
- **Refactoring index_scan_roots' record construction alters reconnect baselines**: M-002: only the EntryRecord construction moves into _record_for_file; test_baseline_parity.py reconnect and discover cases and test_scan_progress_cancel.py run unchanged
- **Golden text corpus recorded after a seam edit would bless a regression**: M-001: the corpus is recorded and committed before tracklist.py or buildplaylist.py change, and the corpus README names that commit
- **pywebview SAVE dialog return shape differs across versions (str vs tuple)**: M-007: pick_save_path normalises both shapes and tests/test_gui_file_picker_save.py covers each with a stub window
- **A collection holding two playlist FOLDER nodes with the same NAME cannot be targeted from the playlist-folder chooser, because the core resolves target_folder by NAME**: M-007: playlist_folder_choices marks such folders non-unique and the chooser lists them disabled with their full path; tests/test_playlists_folder_choices.py pins the flag over a two-same-named-folder base

## Invisible Knowledge

### System

Input file/folder -> playlistinput.detect_format -> read_input (text | folder | m3u | csv parsers; diskscan.index_files for files present on disk) -> InputRead(format, encoding, candidates) -> buildplaylist.assemble_output(candidates) -> tracklist.resolve_candidates (match_records at LOOSE, candidate old side, collection new side) -> refusal (DL-027/DL-036) -> synthesize_playlist_node -> SUBNODES splice -> optional split isolation -> atomic write. CLI build_playlist_cmd and gui/app.py _run_build_playlist both enter at read_input.

### Invariants

- The value of file-based input is stronger evidence, not new syntax: a parser that leaves filesize, playtime_float, file_name or folder parts empty when its source carries them discards the tiers above artist_title
- CSV_COLUMNS is the only definition of the CSV header; csv_template_bytes() and the parser both derive from it, and the template parses to zero candidates with no error
- build-playlist references collection entries only and never adds ENTRY elements
- A folder or M3U read that cannot index a file raises; it never returns fewer candidates than entries
- The plain-text path's CLI stdout, stderr, exit code and output bytes match tests/baselines/build_playlist_text/ exactly; stats keys and order are identical for every format
- Candidate order is input order and duplicates are kept (DL-037); the report is sorted by line_number
- match_records descends past an ambiguous tier, so a uniquely placed path resolves at path_suffix_3 even when a stronger tier saw two copies

### Tradeoffs

- Tags are read without a cache on every folder or M3U run: slower on large folders, but no side file and no allowlist change
- cp1252 fallback accepts any byte sequence: fewer refusals at the cost of possible mojibake, made visible by naming the encoding
- Suffix-based detection with an --input-format override instead of content sniffing: predictable, and a mis-suffixed file needs the flag

## Milestones

### Milestone 1: Text-path golden corpus and the Candidate seam

**Files**: tests/baselines/build_playlist_text/, tests/test_build_playlist_text_parity.py, traktor_nml/tracklist.py, traktor_nml/buildplaylist.py, traktor_nml/playlistinput.py, traktor_nml/commands/build_playlist_cmd.py, traktor_nml/gui/app.py, tests/test_tracklist.py, tests/test_playlistinput.py, traktor_nml/README.md, tests/CLAUDE.md

**Requirements**:

- Golden corpus recorded and committed before tracklist.py or buildplaylist.py change, covering: clean list; unparseable line; ambiguous line; unmatched with and without --allow-unmatched; duplicate lines; UTF-8 BOM; track-number prefix; '#' comment and blank lines; --target-folder found, missing and $ROOT; --full-collection; --dry-run; --unresolved-report; zero resolved; decode error; missing tracklist
- Candidate dataclass and text_candidates(text) in tracklist.py merge parsed and unparseable lines in line order
- resolve_candidates resolves Candidates with a record and passes record-None Candidates through as unparseable
- assemble_output takes candidates; stats keys, order and report sort are unchanged
- playlistinput.read_input handles the text format; CLI handler and app.py _run_build_playlist call it and nothing else for reading
- README decision log gains DL-274 onward for the seam, parity corpus, stats keys and input module

**Acceptance Criteria**:

- test_build_playlist_text_parity.py passes against the corpus after the seam lands
- Mutating text_candidates to number unparseable lines from 0 fails the parity test (verbatim output in docstring)
- tests/test_build_playlist.py, test_build_playlist_byte_identity.py and test_baseline_parity.py pass unchanged
- app.py remains 100% CRLF

**Tests**:

- integration: golden replay of every corpus case through run_tool with uuid4 patched
- unit: text_candidates line order with interleaved unparseable lines
- unit: resolve_candidates passes a record-None Candidate through as unparseable without calling match_records

#### Code Intent

- **CI-M-001-001** `tests/test_build_playlist_text_parity.py`: Records (behind an explicit RECORD env switch, run once at the pre-seam commit) and replays each case directory: argv.json, stdout.txt, stderr.txt, exit_code.txt, output.nml (absent under refusal or --dry-run), unresolved.csv when requested; compares bytes exactly with uuid.uuid4 patched to a fixed UUID (refs: DL-279)
- **CI-M-001-002** `tests/baselines/build_playlist_text/`: Corpus directory with one subdirectory per case plus a README naming the commit it was recorded at and the fixture NML each case reads (refs: DL-279)
- **CI-M-001-003** `traktor_nml/tracklist.py::Candidate/text_candidates/resolve_candidates`: Candidate(line_number, raw_text, artist, title, record: Optional[EntryRecord]); text_candidates(text) returns parse_tracklist's parsed lines as Candidates with tracklist_record(line) and its unparseable lines as record-None Candidates, sorted by line_number; resolve_candidates(candidates, collection) builds the LOOSE index once and returns one CandidateResolution(candidate, outcome, matched_record) per candidate, outcome 'unparseable' for record None; resolve_tracklist delegates to it (refs: DL-274, DL-276, DL-278)
- **CI-M-001-004** `traktor_nml/buildplaylist.py::assemble_output/_resolve_lines`: assemble_output(base_source, base_root, candidates, playlist_name, target_folder, allow_unmatched); _resolve_lines builds UnresolvedRow from each non-matched resolution with the candidate's line_number, raw_text, artist, title and outcome as kind; lines_read counts all candidates, unresolved_unparseable counts record-None candidates; rows sorted by line_number (refs: DL-274, DL-280, DL-292)
- **CI-M-001-005** `traktor_nml/playlistinput.py::detect_format/read_input`: InputFormat (text, csv, m3u, folder); InputRead(format, encoding, candidates); InputReadError(code); detect_format by directory or suffix; read_input for text reads bytes (OSError -> input_not_found=<posix path>), decodes utf-8-sig strict (-> tracklist_decode_error=<posix path>) and returns text_candidates (refs: DL-281, DL-282, DL-283)
- **CI-M-001-006** `traktor_nml/commands/build_playlist_cmd.py::_handle_build_playlist`: Reads through playlistinput.read_input, prints InputReadError.code to stderr with exit 2, passes candidates to assemble_output; remaining ordering unchanged (refs: DL-281, DL-279)
- **CI-M-001-007** `traktor_nml/gui/app.py::_run_build_playlist`: Reads through playlistinput.read_input and maps InputReadError.code into BuildPlaylistResult.errors; file written with newline='' to stay CRLF (refs: DL-281)
- **CI-M-001-008** `traktor_nml/README.md`: Decision log entries DL-274 onward for the decisions this milestone implements, and the build-playlist architecture section describing the Candidate seam (refs: DL-274, DL-279, DL-280, DL-281)
- **CI-M-001-009** `tests/test_tracklist.py::test_text_candidates_order/test_resolve_candidates_unparseable`: Unit tests: text_candidates over text interleaving parsed and unparseable lines returns Candidates in line_number order; resolve_candidates passes a record-None Candidate through as 'unparseable' without calling match_records (match_records patched to raise); each guard's docstring names its mutation and quotes the verbatim failing output (refs: DL-274, DL-278)
- **CI-M-001-010** `tests/test_playlistinput.py::test_detect_format/test_read_input_text`: Unit tests: detect_format for a directory, .csv, .m3u, .m3u8 and other suffixes including none; read_input on a text file returns format text, encoding utf-8-sig and text_candidates; a missing path raises input_not_found=<posix path>; invalid UTF-8 raises tracklist_decode_error=<posix path>; fail-first docstrings (refs: DL-281, DL-282, DL-283, DL-292)
- **CI-M-001-011** `tests/CLAUDE.md`: Index rows (CRLF) for test_build_playlist_text_parity.py, tests/baselines/build_playlist_text/, test_tracklist.py's Candidate tests and test_playlistinput.py, each stating what the file proves (refs: DL-279, DL-281)

#### Code Changes

**CC-M-001-001** (tests/test_build_playlist_text_parity.py) - implements CI-M-001-001

**Code:**

```diff
--- /dev/null
+++ b/tests/test_build_playlist_text_parity.py
@@ -0,0 +1,168 @@
+"""Golden replay of the plain-text build-playlist path (DL-279).
+
+Each case under tests/baselines/build_playlist_text/<case>/ holds what
+the CLI printed, the exit code it returned and every byte it wrote for
+one invocation over the base collection and track list this module
+builds. The corpus was recorded from the code as it stood before the
+Candidate seam (DL-274) existed; replaying it here is the proof that
+the seam left the text path's stdout, stderr, exit code, output file
+and unresolved report byte-identical. Unit tests alone would pass a
+seam that renumbered a line or reordered a report row.
+
+tests/baselines/manifest.json holds no build-playlist case and is not
+regenerated; this corpus is a separate directory.
+
+Recording: set BUILD_PLAYLIST_TEXT_RECORD=1 and run this file once, at
+the commit the corpus README names. A normal suite run only replays.
+"""
+
+from __future__ import annotations
+
+import json
+import os
+import uuid
+from pathlib import Path
+from unittest.mock import patch
+
+import pytest
+
+from tests.conftest import run_tool
+
+CORPUS = Path(__file__).resolve().parent / "baselines" / "build_playlist_text"
+RECORD = os.environ.get("BUILD_PLAYLIST_TEXT_RECORD") == "1"
+
+# playlists.synthesize_playlist_node stamps uuid.uuid4() onto every
+# synthesized PLAYLIST node (DL-008); a fixed value leaves the corpus
+# comparing behaviour rather than randomness.
+_FIXED_UUID = uuid.UUID("00000000-0000-4000-8000-000000000000")
+
+
+def _entry(artist: str, title: str, filename: str, folder: str = "Music") -> str:
+    return (
+        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
+        f'<LOCATION DIR="/:{folder}/:" FILE="{filename}" VOLUME="C:" VOLUMEID="C:"></LOCATION>'
+        '<INFO BITRATE="320" PLAYTIME_FLOAT="200.0" FILESIZE="8000"></INFO>'
+        "</ENTRY>"
+    )
+
+
+def _base_nml() -> str:
+    # "Dup - Twice" is held at two locations so a line naming it is
+    # ambiguous; the "Sets" FOLDER gives --target-folder a found case.
+    entries = (
+        _entry("Alpha", "One", "alpha-one.mp3")
+        + _entry("Beta", "Two", "beta-two.mp3")
+        + _entry("Gamma", "Three", "gamma-three.mp3")
+        + _entry("Dup", "Twice", "dup-a.mp3", "A")
+        + _entry("Dup", "Twice", "dup-b.mp3", "B")
+    )
+    return (
+        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
+        f'<COLLECTION ENTRIES="5">{entries}</COLLECTION>'
+        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="1">'
+        '<NODE TYPE="FOLDER" NAME="Sets"><SUBNODES COUNT="0"></SUBNODES></NODE>'
+        "</SUBNODES></NODE></PLAYLISTS>"
+        "<SETS></SETS><INDEXING></INDEXING></NML>"
+    )
+
+
+_CLEAN = b"Alpha - One\nBeta - Two\n"
+
+# (case name, track-list bytes or None for no file, extra argv)
+CASES: list[tuple[str, bytes | None, list[str]]] = [
+    ("clean", _CLEAN, []),
+    ("unparseable", b"Alpha - One\nno delimiter here\nBeta - Two\n", []),
+    ("unparseable_allowed", b"Alpha - One\nno delimiter here\nBeta - Two\n", ["--allow-unmatched"]),
+    ("ambiguous", b"Alpha - One\nDup - Twice\n", []),
+    ("unmatched", b"Alpha - One\nNobody - Nothing\n", []),
+    ("unmatched_allowed", b"Alpha - One\nNobody - Nothing\n", ["--allow-unmatched"]),
+    ("duplicates", b"Alpha - One\nAlpha - One\nBeta - Two\n", []),
+    ("utf8_bom", b"\xef\xbb\xbfAlpha - One\nBeta - Two\n", []),
+    ("track_number_prefix", b"1 - Alpha - One\n02 - Beta - Two\n", []),
+    ("comments_and_blanks", b"# set list\n\nAlpha - One\n   \n# end\nBeta - Two\n", []),
+    ("target_folder_found", _CLEAN, ["--target-folder", "Sets"]),
+    ("target_folder_missing", _CLEAN, ["--target-folder", "Nowhere"]),
+    ("target_folder_root", _CLEAN, ["--target-folder", "$ROOT"]),
+    ("full_collection", _CLEAN, ["--full-collection"]),
+    ("dry_run", _CLEAN, ["--dry-run"]),
+    ("unresolved_report", b"Alpha - One\nNobody - Nothing\nno delimiter\n", ["--allow-unmatched", "--unresolved-report", "unresolved.csv"]),
+    ("zero_resolved", b"Nobody - Nothing\n", ["--allow-unmatched"]),
+    ("decode_error", b"Alpha - One\n\xff\xfe\xfa\n", []),
+    ("missing_tracklist", None, []),
+]
+
+
+def _invoke(tmp_path: Path, tracklist: bytes | None, extra: list[str]):
+    (tmp_path / "base.nml").write_text(_base_nml(), encoding="utf-8", newline="")
+    if tracklist is not None:
+        (tmp_path / "tracks.txt").write_bytes(tracklist)
+    # Relative paths under cwd=tmp_path keep every path the CLI prints
+    # identical between the recording run and any replay.
+    argv = ["build-playlist", "base.nml", "tracks.txt", "out.nml", "--name", "Set", *extra]
+    with patch("uuid.uuid4", return_value=_FIXED_UUID):
+        result = run_tool(argv, cwd=tmp_path)
+    return argv, result
+
+
+def _observed(tmp_path: Path, argv, result) -> dict[str, bytes]:
+    files = {
+        "argv.json": json.dumps(argv).encode("utf-8"),
+        "stdout.txt": result.stdout.encode("utf-8"),
+        "stderr.txt": result.stderr.encode("utf-8"),
+        "exit_code.txt": str(result.exit_code).encode("utf-8"),
+    }
+    # Absent under a refusal or --dry-run; its absence is part of the record.
+    for written in ("out.nml", "unresolved.csv"):
+        path = tmp_path / written
+        if path.exists():
+            files["output.nml" if written == "out.nml" else written] = path.read_bytes()
+    return files
+
+
+@pytest.mark.parametrize("case,tracklist,extra", CASES, ids=[c[0] for c in CASES])
+def test_text_path_replays_its_recorded_corpus(tmp_path: Path, case, tracklist, extra):
+    """Every recorded case replays byte-identically: the same argv, the
+    same stdout and stderr, the same exit code, the same output file and
+    unresolved report, and no file the recording did not write.
+
+    Mutation: tracklist.text_candidates builds each unparseable
+        Candidate with line.line_number - 1, so the unresolved_report
+        case's unresolved.csv carries a shifted line_number column and
+        its bytes differ from the recording.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    argv, result = _invoke(tmp_path, tracklist, extra)
+    observed = _observed(tmp_path, argv, result)
+    case_dir = CORPUS / case
+
+    if RECORD:
+        case_dir.mkdir(parents=True, exist_ok=True)
+        for name, data in observed.items():
+            (case_dir / name).write_bytes(data)
+        return
+
+    assert case_dir.is_dir(), f"corpus case {case} was never recorded"
+    recorded = {path.name: path.read_bytes() for path in case_dir.iterdir()}
+    assert sorted(observed) == sorted(recorded), f"file set differs for {case}"
+    for name, data in recorded.items():
+        assert observed[name].decode("utf-8", "replace") == data.decode("utf-8", "replace"), (
+            f"{name} differs for {case}"
+        )
+        assert observed[name] == data, f"{name} bytes differ for {case}"
+
+
+def test_corpus_holds_every_case_and_nothing_else():
+    """The corpus directory holds a subdirectory for exactly the cases
+    above, so a case dropped from CASES cannot silently stop being
+    replayed while its recording lingers.
+
+    Mutation: the recorded corpus loses its
+        tests/baselines/build_playlist_text/dry_run/ directory, so the
+        directories on disk no longer equal the CASES names.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    if RECORD:
+        pytest.skip("recording run")
+    on_disk = sorted(path.name for path in CORPUS.iterdir() if path.is_dir())
+    assert on_disk == sorted(case for case, _t, _e in CASES)

```

**Documentation:**

```diff
--- a/tests/test_build_playlist_text_parity.py
+++ b/tests/test_build_playlist_text_parity.py
@@ -124,2 +124,12 @@
 def test_text_path_replays_its_recorded_corpus(tmp_path: Path, case, tracklist, extra):
+    """Every recorded case replays byte-identically: the same argv, the
+    same stdout and stderr, the same exit code, the same output file and
+    unresolved report, and no file the recording did not write.
+
+    Mutation: tracklist.text_candidates builds each unparseable
+        Candidate with line.line_number - 1, so the unresolved_report
+        case's unresolved.csv carries a shifted line_number column and
+        its bytes differ from the recording.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     argv, result = _invoke(tmp_path, tracklist, extra)
@@ -145,2 +155,11 @@
 def test_corpus_holds_every_case_and_nothing_else():
+    """The corpus directory holds a subdirectory for exactly the cases
+    above, so a case dropped from CASES cannot silently stop being
+    replayed while its recording lingers.
+
+    Mutation: the recorded corpus loses its
+        tests/baselines/build_playlist_text/dry_run/ directory, so the
+        directories on disk no longer equal the CASES names.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     if RECORD:

```


**CC-M-001-002** (tests/baselines/build_playlist_text/README.md) - implements CI-M-001-002

**Code:**

```diff
--- /dev/null
+++ b/tests/baselines/build_playlist_text/README.md
@@ -0,0 +1,31 @@
+# build-playlist plain-text corpus
+
+The recorded behaviour of `build-playlist` over a plain-text track list,
+replayed byte for byte by `tests/test_build_playlist_text_parity.py`
+(DL-279).
+
+Recorded at commit `<hash of the pre-seam commit>`, before `tracklist.py`
+or `buildplaylist.py` took the Candidate seam (DL-274). A recording taken
+from any later commit would hold whatever that commit does, including a
+regression, so the corpus is never re-recorded to make a replay pass.
+
+## What each case directory holds
+
+| File | Content |
+|---|---|
+| `argv.json` | The argument list, relative to the run's working directory |
+| `stdout.txt` | Everything the CLI printed to stdout |
+| `stderr.txt` | Everything the CLI printed to stderr |
+| `exit_code.txt` | The exit code |
+| `output.nml` | The written NML; absent when the run refused or ran with `--dry-run` |
+| `unresolved.csv` | The unresolved report; present only for the case that asks for one |
+
+## The fixture every case reads
+
+No NML file is stored here. Every case reads `base.nml` and `tracks.txt`
+as `_base_nml()` and `CASES` in the test module build them: five
+entries, one of which (`Dup - Twice`) is held at two locations so a line
+naming it is ambiguous, and a `Sets` folder under `$ROOT`. The case name
+is the directory name and says what the case exercises.
+
+`uuid.uuid4` is patched to `00000000-0000-4000-8000-000000000000`.

```

**Documentation:**

```diff
--- a/tests/baselines/build_playlist_text/README.md
+++ b/tests/baselines/build_playlist_text/README.md

```

> **Developer notes**: Corpus directory. The case subdirectories are produced, not hand-written:
at the pre-seam commit (before tracklist.py or buildplaylist.py change),
run
  set BUILD_PLAYLIST_TEXT_RECORD=1
  C:\Users\marcu\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest tests/test_build_playlist_text_parity.py
unset the variable, commit the corpus in its own commit, then fill that
commit's hash into the README below. Only the README is authored text.

**CC-M-001-003** (traktor_nml/tracklist.py) - implements CI-M-001-003

**Code:**

```diff
--- a/traktor_nml/tracklist.py
+++ b/traktor_nml/tracklist.py
@@ -1,14 +1,19 @@
-"""External track-list parsing and per-line collection resolution.
+"""External track-list parsing and per-candidate collection resolution.
 
-A plain-text track list holds one 'Artist - Title' line per line. Each
-parsed line becomes a candidate EntryRecord (entry=None), the same shape
-diskscan.py already uses for disk-scanned candidates, and is resolved
-against a base collection through the shared matching cascade in
-matching.py at MatchConfidence.LOOSE - the only tier reachable for
-text-only input is artist_title, since every field the stricter tiers
-require (filesize, playtime_float, file_name, album) is empty for a
-parsed line. matching.py and confidence.py are imported and called here,
-never edited or wrapped in a subclass.
+Every build-playlist input format hands resolution one ordered list of
+Candidate values (DL-274). A Candidate carries the entry's position and
+text for the report, and either the EntryRecord the matching cascade
+reads as its old side or None for an entry that could not be parsed.
+resolve_candidates resolves that list against a base collection through
+matching.py at MatchConfidence.LOOSE (DL-276), candidates on the old
+side and the collection on the new (DL-278).
+
+A plain-text track list holds one 'Artist - Title' line per line; each
+parsed line becomes a record carrying artist and title only, so the only
+tier it reaches is artist_title. Formats that carry a path, size or
+duration (playlistinput.py) fill those fields and reach the stricter
+tiers (DL-275). matching.py and confidence.py are imported and called
+here, never edited or wrapped in a subclass.
 """
 
 from __future__ import annotations
@@ -105,44 +110,109 @@ def tracklist_record(line: ParsedLine) -> EntryRecord:
         source_path=None,
     )
 
 
+@dataclass(frozen=True)
+class Candidate:
+    """One input entry in input order. record None marks an entry that
+    could not be parsed; the report still needs its line_number and
+    raw_text, which is why unparseable entries travel in the same list
+    rather than beside it (DL-274). artist and title are what the report
+    shows, and may be empty for a file-derived entry with no tags."""
+
+    line_number: int
+    raw_text: str
+    artist: str
+    title: str
+    record: Optional[EntryRecord]
+
+
+def text_candidates(text: str) -> list[Candidate]:
+    """parse_tracklist's parsed and unparseable lines as one Candidate
+    list in line order. line_number is the physical 1-based line, the
+    same number parse_tracklist assigns, so the text path's report is
+    unchanged by the seam (DL-279)."""
+    parsed, unparseable = parse_tracklist(text)
+    candidates = [
+        Candidate(line.line_number, line.raw_text, line.artist, line.title, tracklist_record(line))
+        for line in parsed
+    ]
+    candidates.extend(
+        Candidate(line.line_number, line.raw_text, "", "", None) for line in unparseable
+    )
+    candidates.sort(key=lambda candidate: candidate.line_number)
+    return candidates
+
+
 @dataclass(frozen=True)
 class TracklistResolution:
     line: ParsedLine
     outcome: str  # "matched", "unmatched", "ambiguous"
     matched_record: Optional[EntryRecord] = None
 
 
+@dataclass(frozen=True)
+class CandidateResolution:
+    candidate: Candidate
+    outcome: str  # "matched", "unmatched", "ambiguous", "unparseable"
+    matched_record: Optional[EntryRecord] = None
+
+
+def resolve_candidates(
+    candidates: list[Candidate], collection: list[EntryRecord]
+) -> list[CandidateResolution]:
+    """Resolve every candidate against collection, in input order.
+
+    The candidate index is built once with build_new_indexes over
+    collection at MatchConfidence.LOOSE, then match_records is called once
+    per candidate with old_records holding that single record and the
+    shared index passed as indexes; the returned stats dict distinguishes
+    matched, unmatched and ambiguous for that one record. A candidate
+    whose record is None is 'unparseable' and never reaches match_records.
+    match_records' returned mapping is keyed by old_record.primary_key -
+    on a matched outcome the matched record is read back via
+    record.primary_key, so the lookup stays correct for a file-derived
+    record whose placeholder location is non-empty.
+    """
+    # index built once over the full collection; reused by every
+    # per-candidate match_records call below so the O(collection) cost
+    # stays at one (DL-025)
+    indexes = build_new_indexes(collection, MatchConfidence.LOOSE)
+    resolutions: list[CandidateResolution] = []
+    for candidate in candidates:
+        record = candidate.record
+        if record is None:
+            resolutions.append(CandidateResolution(candidate=candidate, outcome="unparseable"))
+            continue
+        # One record per call: ambiguity is counted per old record, so a
+        # folder holding the same track twice cannot make either copy
+        # ambiguous against the other (DL-278).
+        mapping, stats, _samples = match_records(
+            [record], collection, MatchConfidence.LOOSE, indexes=indexes
+        )
+        if stats["matched"] == 1:
+            resolutions.append(
+                CandidateResolution(
+                    candidate=candidate, outcome="matched", matched_record=mapping.get(record.primary_key)
+                )
+            )
+        elif stats["ambiguous"] == 1:
+            resolutions.append(CandidateResolution(candidate=candidate, outcome="ambiguous"))
+        else:
+            resolutions.append(CandidateResolution(candidate=candidate, outcome="unmatched"))
+    return resolutions
+
+
 def resolve_tracklist(
     lines: list[ParsedLine], collection: list[EntryRecord]
 ) -> list[TracklistResolution]:
-    """Resolve every parsed line against collection, in input order.
-
-    The candidate index is built once with build_new_indexes over
-    collection at MatchConfidence.LOOSE, then match_records is called once
-    per line with old_records holding that single line and the shared
-    index passed as indexes; the returned stats dict distinguishes matched,
-    unmatched and ambiguous for that one line. match_records' returned
-    mapping is keyed by old_record.primary_key - on a matched outcome the
-    matched record is read back via record.primary_key (not a hardcoded ""),
-    so the lookup stays correct even if LocationParts.primary_key's
-    concatenation formula ever changes.
-    """
-    # index built once over the full collection; reused by every per-line
-    # match_records call below so the O(collection) cost stays at one (DL-025)
-    indexes = build_new_indexes(collection, MatchConfidence.LOOSE)
-    resolutions: list[TracklistResolution] = []
-    for line in lines:
-        record = tracklist_record(line)
-        mapping, stats, _samples = match_records(
-            [record], collection, MatchConfidence.LOOSE, indexes=indexes
-        )
-        if stats["matched"] == 1:
-            resolutions.append(
-                TracklistResolution(line=line, outcome="matched", matched_record=mapping.get(record.primary_key))
-            )
-        elif stats["ambiguous"] == 1:
-            resolutions.append(TracklistResolution(line=line, outcome="ambiguous"))
-        else:
-            resolutions.append(TracklistResolution(line=line, outcome="unmatched"))
-    return resolutions
+    """Resolve parsed lines through resolve_candidates, one
+    TracklistResolution per line in input order. Kept for callers that
+    hold ParsedLine values rather than Candidates."""
+    candidates = [
+        Candidate(line.line_number, line.raw_text, line.artist, line.title, tracklist_record(line))
+        for line in lines
+    ]
+    return [
+        TracklistResolution(line=line, outcome=resolution.outcome, matched_record=resolution.matched_record)
+        for line, resolution in zip(lines, resolve_candidates(candidates, collection))
+    ]

```

**Documentation:**

```diff
--- a/traktor_nml/tracklist.py
+++ b/traktor_nml/tracklist.py
@@ -134,6 +134,8 @@ def text_candidates(text: str) -> list[Candidate]:
     candidates.extend(
         Candidate(line.line_number, line.raw_text, "", "", None) for line in unparseable
     )
+    # One list in physical line order, the order the report rows of the
+    # recorded text corpus hold (DL-279).
     candidates.sort(key=lambda candidate: candidate.line_number)
     return candidates

@@ -155,5 +157,10 @@ class TracklistResolution:
 @dataclass(frozen=True)
 class CandidateResolution:
+    """One Candidate's outcome. matched_record is the collection record
+    it resolved to, set only when outcome is 'matched'. 'unparseable' is
+    the outcome of a record-None Candidate, which never reaches
+    match_records (DL-274)."""
+
     candidate: Candidate
     outcome: str  # "matched", "unmatched", "ambiguous", "unparseable"
     matched_record: Optional[EntryRecord] = None
@@ -181,6 +188,15 @@ def resolve_candidates(
     # index built once over the full collection; reused by every
     # per-candidate match_records call below so the O(collection) cost
     # stays at one (DL-025)
+    # LOOSE for every format: the cascade tries tiers strongest first, so a
+    # candidate carrying size, duration or path already reaches the strict
+    # tiers at this level, and FILENAME's bare_name collides on stem
+    # component files (DL-276). Every field a reader filled is a key the
+    # cascade can use (DL-275). No exact-location pre-pass runs first:
+    # match_records descends past an ambiguous tier, so a track held at two
+    # locations still resolves uniquely at path_suffix_3 (DL-277). The
+    # candidate is the old side and the collection the new, the direction
+    # whose refutation verdicts are symmetric in which side is disk (DL-278).
     indexes = build_new_indexes(collection, MatchConfidence.LOOSE)
     resolutions: list[CandidateResolution] = []
     for candidate in candidates:

```

> **Developer notes**: Three changes to traktor_nml/tracklist.py: the module docstring widens from
text-only input to the Candidate seam; Candidate and text_candidates follow
tracklist_record; resolve_candidates takes over resolve_tracklist's loop and
resolve_tracklist becomes a thin wrapper, so its existing callers and tests
keep their shape.

**CC-M-001-004** (traktor_nml/buildplaylist.py) - implements CI-M-001-004

**Code:**

```diff
--- a/traktor_nml/buildplaylist.py
+++ b/traktor_nml/buildplaylist.py
@@ -1,13 +1,16 @@
 """build-playlist core: resolution, playlist synthesis, insertion.
 
-A build-playlist run resolves each track-list line against a base
-collection through the shared matching cascade in tracklist.py at
-MatchConfidence.LOOSE, synthesizes a NODE TYPE=PLAYLIST fragment from the
-resolved primary keys in input order (playlists.synthesize_playlist_node),
-and inserts it into the base's root FOLDER SUBNODES, or a named existing
-folder's SUBNODES, through the same byte-span assembly spans.py's other
-structural commands (splice.py/split.py) already use. No source span
-exists for a playlist assembled from external text, so its fragment
+A build-playlist run takes the ordered Candidate list an input reader
+produced (playlistinput.read_input, DL-274), resolves each candidate
+against a base collection through tracklist.resolve_candidates at
+MatchConfidence.LOOSE, synthesizes a NODE TYPE=PLAYLIST fragment from the
+resolved primary keys in input order (playlists.synthesize_playlist_node),
+and inserts it into the base's root FOLDER SUBNODES, or a named existing
+folder's SUBNODES, through the same byte-span assembly spans.py's other
+structural commands (splice.py/split.py) already use. It never adds an
+ENTRY: a candidate the collection does not hold is reported as unmatched
+(DL-293). No source span exists for a playlist assembled from external
+input, so its fragment
 always takes the ElementTree-serialization path (DL-028) rather than
 transplantation. matching.py and confidence.py are reached only through
 tracklist.py's own calls and are never edited here.
@@ -24,12 +27,12 @@ from typing import Optional
 from .model import collection_records
 from .playlists import available_playlist_name, find_playlist_nodes, synthesize_playlist_node
 from .spans import OutputBuilder, SpanIndex, find_element_span
-from .tracklist import parse_tracklist, resolve_tracklist
+from .tracklist import Candidate, resolve_candidates
 
 
 @dataclass
 class UnresolvedRow:
-    """One tracklist line that did not become a written ENTRY, and why."""
+    """One input entry that did not become a written ENTRY, and why."""
     line_number: int
     raw_text: str
     artist: str
@@ -113,36 +116,41 @@ def _find_target_subnodes(base_root, base_source: str, target_folder: Optional[str]):
     return subnodes_span, count, None
 
 
-def _resolve_lines(parsed_lines, unparseable_lines, records):
-    """Resolve every parsed line against records and split the results into
-    matched primary keys, unresolved rows (sorted back into overall
-    document line-number order, since unparseable rows are collected before
-    per-line resolutions), and the run's stats dict."""
-    resolutions = resolve_tracklist(parsed_lines, records)
-
-    unresolved_rows: list[UnresolvedRow] = [
-        UnresolvedRow(line_number=u.line_number, raw_text=u.raw_text, artist="", title="", kind="unparseable")
-        for u in unparseable_lines
-    ]
+def _resolve_lines(candidates: list[Candidate], records):
+    """Resolve every candidate against records and split the results into
+    matched primary keys, unresolved rows sorted by line_number, and the
+    run's stats dict. The stats keys and their order are the same for
+    every input format (DL-280): the CLI prints them as they stand, and
+    the text corpus replays that output byte for byte (DL-279)."""
+    resolutions = resolve_candidates(candidates, records)
+
+    unresolved_rows: list[UnresolvedRow] = []
     matched_keys: list[str] = []
     for resolution in resolutions:
         if resolution.outcome == "matched":
             matched_keys.append(resolution.matched_record.primary_key)
         else:
+            candidate = resolution.candidate
             unresolved_rows.append(
                 UnresolvedRow(
-                    line_number=resolution.line.line_number, raw_text=resolution.line.raw_text,
-                    artist=resolution.line.artist, title=resolution.line.title, kind=resolution.outcome,
+                    line_number=candidate.line_number, raw_text=candidate.raw_text,
+                    artist=candidate.artist, title=candidate.title, kind=resolution.outcome,
                 )
             )
+    # Stable sort: candidates already arrive in input order, and a folder or
+    # M3U never repeats a line_number, so this only fixes the text path's
+    # interleaving without reordering equal keys.
     unresolved_rows.sort(key=lambda row: row.line_number)
 
+    def _count(outcome: str) -> int:
+        return sum(1 for r in resolutions if r.outcome == outcome)
+
     stats: dict[str, object] = {
-        "lines_read": len(parsed_lines) + len(unparseable_lines),
+        "lines_read": len(candidates),
         "lines_resolved": len(matched_keys),
-        "unresolved_unparseable": len(unparseable_lines),
-        "unresolved_unmatched": sum(1 for r in resolutions if r.outcome == "unmatched"),
-        "unresolved_ambiguous": sum(1 for r in resolutions if r.outcome == "ambiguous"),
+        "unresolved_unparseable": _count("unparseable"),
+        "unresolved_unmatched": _count("unmatched"),
+        "unresolved_ambiguous": _count("ambiguous"),
         "playlist_name": None,
         "entries_written": 0,
     }
@@ -157,28 +165,28 @@ def _resolve_lines(parsed_lines, unparseable_lines, records):
 def assemble_output(
     base_source: str,
     base_root,
-    tracklist_text: str,
+    candidates: list[Candidate],
     playlist_name: str,
     target_folder: Optional[str] = None,
     allow_unmatched: bool = False,
 ) -> BuildPlaylistResult:
-    """Resolve every tracklist line against the base collection, synthesize
+    """Resolve every candidate against the base collection, synthesize
     a playlist from the resolved primary keys in input order, and splice
     it into the receiving SUBNODES. Returns output None with
-    unresolved_tracks when any line is unresolved and allow_unmatched is
+    unresolved_tracks when any candidate is unresolved and allow_unmatched is
     false (DL-027); output None with no_entries_resolved, before any span
-    lookup, when zero lines resolve at all (DL-036); output None with
+    lookup, when zero candidates resolve, including an input that yielded
+    no candidates at all (DL-036, DL-292); output None with
     no_root_subnodes/root_subnodes_span_not_found/target_folder_not_found/
     target_folder_no_subnodes/target_folder_ambiguous=name:count=N when the
     receiving container cannot be resolved (DL-030, DL-038). Duplicate
-    tracklist lines naming the same track resolve and serialize
+    candidates naming the same track resolve and serialize
     independently (DL-037). Every synthesized key is validated against the
     base collection's own primary keys before returning, mirroring
     splice.py's validate-before-write convention. The whole output is built
     and validated in memory before the caller opens any file handle."""
-    parsed_lines, unparseable_lines = parse_tracklist(tracklist_text)
     records = collection_records(base_root)
-    matched_keys, unresolved_rows, stats = _resolve_lines(parsed_lines, unparseable_lines, records)
+    matched_keys, unresolved_rows, stats = _resolve_lines(candidates, records)
 
     if unresolved_rows and not allow_unmatched:
         return BuildPlaylistResult(output=None, stats=stats, unresolved_rows=unresolved_rows, errors=["unresolved_tracks"])
@@ -192,6 +200,6 @@ def assemble_output(
 
     # Every matched_keys entry comes from resolution.matched_record, which
-    # resolve_tracklist draws only from this same records list, so this can
+    # resolve_candidates draws only from this same records list, so this can
     # never actually fail - checked anyway to match splice.py's own
     # validate-before-write convention for playlist PRIMARYKEY references.
     valid_keys = {r.primary_key for r in records}

```

**Documentation:**

```diff
--- a/traktor_nml/buildplaylist.py
+++ b/traktor_nml/buildplaylist.py
@@ -188,5 +188,9 @@ def assemble_output(
     and validated in memory before the caller opens any file handle."""
     records = collection_records(base_root)
+    # candidates arrive already read and ordered by playlistinput.read_input
+    # (DL-281); whatever format produced them, resolution, refusal and the
+    # report see one shape (DL-274). A candidate the collection does not
+    # hold becomes an unmatched row; no ENTRY is synthesized for it (DL-293).
     matched_keys, unresolved_rows, stats = _resolve_lines(candidates, records)

     if unresolved_rows and not allow_unmatched:

```


**CC-M-001-005** (traktor_nml/playlistinput.py) - implements CI-M-001-005

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/playlistinput.py
@@ -0,0 +1,98 @@
+"""build-playlist input formats, read into one Candidate list.
+
+detect_format names the format a path holds and read_input reads it into
+an InputRead: the format, the codec it was decoded with, and the ordered
+Candidate list tracklist.resolve_candidates and
+buildplaylist.assemble_output consume unchanged (DL-274, DL-281). Every
+reader fills each EntryRecord field its source carries, because those
+fields are what lets a candidate match on a tier stronger than
+artist_title (DL-275).
+
+An input that cannot be read raises InputReadError carrying the one
+refusal code both surfaces print (DL-292). A reader never returns fewer
+candidates than its input holds entries: a partial list is
+indistinguishable from a complete one by inspection.
+
+No nicegui import: the CLI, the GUI and the suite all reach this module
+directly (DL-069).
+"""
+
+from __future__ import annotations
+
+import enum
+from dataclasses import dataclass
+from pathlib import Path
+
+from .tracklist import Candidate, text_candidates
+
+
+class InputFormat(enum.Enum):
+    TEXT = "text"
+    CSV = "csv"
+    M3U = "m3u"
+    FOLDER = "folder"
+
+
+@dataclass(frozen=True)
+class InputRead:
+    format: InputFormat
+    # The codec the bytes were decoded with, or "n/a" for a folder, which
+    # holds no text of its own.
+    encoding: str
+    candidates: list[Candidate]
+
+
+class InputReadError(Exception):
+    """An input that cannot be read at all. code is the exact refusal
+    string the CLI prints to stderr and the GUI shows (DL-292)."""
+
+    def __init__(self, code: str) -> None:
+        super().__init__(code)
+        self.code = code
+
+
+def detect_format(path: Path) -> InputFormat:
+    """A directory is a folder input; .csv is CSV; .m3u and .m3u8 are
+    M3U; any other file, with or without a suffix, is plain text
+    (DL-281, DL-282). Suffix-based rather than content sniffing, so the
+    format a file is read as is predictable from its name."""
+    if path.is_dir():
+        return InputFormat.FOLDER
+    suffix = path.suffix.casefold()
+    if suffix == ".csv":
+        return InputFormat.CSV
+    if suffix in (".m3u", ".m3u8"):
+        return InputFormat.M3U
+    return InputFormat.TEXT
+
+
+def _read_bytes(path: Path) -> bytes:
+    try:
+        return path.read_bytes()
+    except OSError:
+        # OSError, not just FileNotFoundError: a permission-denied path
+        # reports the same clean refusal rather than a traceback.
+        raise InputReadError(f"input_not_found={path.as_posix()}") from None
+
+
+def _decode_strict(data: bytes, path: Path) -> str:
+    try:
+        # utf-8-sig strips a leading BOM rather than letting it corrupt the
+        # first entry's artist name.
+        return data.decode("utf-8-sig")
+    except UnicodeDecodeError:
+        raise InputReadError(f"tracklist_decode_error={path.as_posix()}") from None
+
+
+def read_text(path: Path) -> InputRead:
+    """A plain-text track list, decoded utf-8-sig strict exactly as the
+    text path has always been (DL-282), so its refusal codes and its
+    candidates replay the text corpus byte for byte (DL-279)."""
+    text = _decode_strict(_read_bytes(path), path)
+    return InputRead(InputFormat.TEXT, "utf-8-sig", text_candidates(text))
+
+
+def read_input(path: Path) -> InputRead:
+    """Read path as a plain-text track list; a directory refuses with
+    input_not_found."""
+    return read_text(path)

```

**Documentation:**

```diff
--- a/traktor_nml/playlistinput.py
+++ b/traktor_nml/playlistinput.py
@@ -29,13 +29,21 @@ from .tracklist import Candidate, text_candidates
 class InputFormat(enum.Enum):
+    """The four input formats. Each value is the name --input-format
+    accepts and the name input_format= prints (DL-280, DL-294)."""
+
     TEXT = "text"
     CSV = "csv"
     M3U = "m3u"
     FOLDER = "folder"
 
 
 @dataclass(frozen=True)
 class InputRead:
+    """What a reader returns: the format read, the codec used and the
+    ordered Candidate list. format and encoding travel here rather than
+    in the run's stats, so a text run's stats and CLI stdout stay those
+    the text corpus records (DL-280)."""
+
     format: InputFormat
     # The codec the bytes were decoded with, or "n/a" for a folder, which
     # holds no text of its own.
     encoding: str

```

> **Developer notes**: New module. M-001 lands the text reader and the dispatch skeleton; M-002,
M-003, M-004 add the folder, M3U and CSV readers, and M-005 adds the
format override to read_input.

**CC-M-001-006** (traktor_nml/commands/build_playlist_cmd.py) - implements CI-M-001-006

**Code:**

```diff
--- a/traktor_nml/commands/build_playlist_cmd.py
+++ b/traktor_nml/commands/build_playlist_cmd.py
@@ -1,13 +1,14 @@
 """build-playlist subcommand: synthesize an NML playlist from an external
-track list matched against a base collection."""
+track list, playlist file or folder matched against a base collection."""
 
 from __future__ import annotations
 
 import argparse
 import sys
 from pathlib import Path
 
 from ..buildplaylist import UnresolvedRow, assemble_output
+from ..playlistinput import InputReadError, read_input
 from ..rewrite import path_collides, read_and_parse_source, write_bytes_atomically, write_row_report
 from ..spans import SpanIndex
 from ..split import build_output
@@ -61,27 +62,18 @@ def _handle_build_playlist(args: argparse.Namespace) -> int:
     base_bytes, base_root = base_result.source_bytes, base_result.root
 
+    # Base first, then the input: the same order the refusals have always
+    # been checked in, which the text corpus replays (DL-279).
     try:
-        tracklist_bytes = args.tracklist.read_bytes()
-    except OSError:
-        # OSError, not just FileNotFoundError: a directory or a
-        # permission-denied path must report the same clean diagnostic
-        # rather than an unhandled traceback.
-        print(f"input_not_found={args.tracklist.as_posix()}", file=sys.stderr)
-        return 2
-
-    try:
-        # utf-8-sig transparently strips a leading UTF-8 BOM rather than
-        # letting it silently corrupt the first parsed line's artist name.
-        tracklist_text = tracklist_bytes.decode("utf-8-sig")
-    except UnicodeDecodeError:
-        print(f"tracklist_decode_error={args.tracklist.as_posix()}", file=sys.stderr)
+        input_read = read_input(args.tracklist)
+    except InputReadError as exc:
+        print(exc.code, file=sys.stderr)
         return 2
 
     result = assemble_output(
         base_bytes.decode("utf-8"),
         base_root,
-        tracklist_text,
+        input_read.candidates,
         args.name,
         target_folder=args.target_folder,
         allow_unmatched=args.allow_unmatched,
     )

```

**Documentation:**

```diff
--- a/traktor_nml/commands/build_playlist_cmd.py
+++ b/traktor_nml/commands/build_playlist_cmd.py
@@ -63,5 +63,8 @@ def _handle_build_playlist(args: argparse.Namespace) -> int:
     # Base first, then the input: the same order the refusals have always
     # been checked in, which the text corpus replays (DL-279).
+    # read_input is the reader the GUI's _run_build_playlist calls as well,
+    # so both surfaces refuse an unreadable input with the same code
+    # (DL-262, DL-281).
     try:
         input_read = read_input(args.tracklist)
     except InputReadError as exc:

```


**CC-M-001-007** (traktor_nml/gui/app.py) - implements CI-M-001-007

**Code:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -49,3 +49,4 @@
 from .. import buildplaylist
+from .. import playlistinput
 from .. import reconnect_run
 from ..diskscan import ScanCancelled
@@ -1659,49 +1660,41 @@ def _run_build_playlist(inputs: FormInputs) -> buildplaylist.BuildPlaylistResult:
 def _run_build_playlist(inputs: FormInputs) -> buildplaylist.BuildPlaylistResult:
     """The build-playlist write path's whole sequence: collision
-    refusal, decode, assemble, the optional isolation pass, atomic
+    refusal, input read, assemble, the optional isolation pass, atomic
     write - the same order build_playlist_cmd.py's own handler calls
     them in, so neither this screen's behaviour nor its written bytes
     diverge from the CLI's (DL-262). Called under run.io_bound, never
     on the event loop directly."""
     base_path = Path(inputs.base_path)
     tracklist_path = Path(inputs.tracklist_path)
     output_path = _derive_build_playlist_output_path(
         base_path, inputs.name, inputs.target_folder
     )
 
     if path_collides(output_path, base_path, tracklist_path):
         return buildplaylist.BuildPlaylistResult(
             output=None, stats={}, unresolved_rows=[],
             errors=["output_must_differ_from_input"],
         )
 
     base_result = read_and_parse_source(base_path)
     if base_result.error is not None:
         return buildplaylist.BuildPlaylistResult(
             output=None, stats={}, unresolved_rows=[], errors=[base_result.error],
         )
     base_bytes, base_root = base_result.source_bytes, base_result.root
 
+    # playlistinput.read_input is the one reader both surfaces call, so a
+    # refusal code here is the string the CLI prints (DL-281).
     try:
-        tracklist_bytes = tracklist_path.read_bytes()
-    except OSError:
-        return buildplaylist.BuildPlaylistResult(
-            output=None, stats={}, unresolved_rows=[],
-            errors=[f"input_not_found={tracklist_path.as_posix()}"],
-        )
-    try:
-        # utf-8-sig transparently strips a leading UTF-8 BOM, matching
-        # build_playlist_cmd.py's own decode rather than letting it
-        # silently corrupt the first parsed line's artist name.
-        tracklist_text = tracklist_bytes.decode("utf-8-sig")
-    except UnicodeDecodeError:
+        input_read = playlistinput.read_input(tracklist_path)
+    except playlistinput.InputReadError as exc:
         return buildplaylist.BuildPlaylistResult(
             output=None, stats={}, unresolved_rows=[],
-            errors=[f"tracklist_decode_error={tracklist_path.as_posix()}"],
+            errors=[exc.code],
         )
 
     result = buildplaylist.assemble_output(
-        base_bytes.decode("utf-8"), base_root, tracklist_text, inputs.name,
+        base_bytes.decode("utf-8"), base_root, input_read.candidates, inputs.name,
         target_folder=inputs.target_folder or None,
         allow_unmatched=inputs.allow_unmatched,
     )

```

**Documentation:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py

```

> **Developer notes**: app.py is CRLF: apply this change with the file opened and written with
newline='' so every line keeps its CRLF; the lines below are shown without
the carriage return. Anchor by content, not line number - an app-wide
button-colour change lands in app.py before this plan executes.

**CC-M-001-008** (traktor_nml/README.md) - implements CI-M-001-008

**Code:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -47,8 +47,15 @@
 `build-playlist` synthesizes its playlist node from an external track list
 with no source span to transplant, so it always takes the serialization
 path this split already sanctions for genuinely new content (DL-028), and
 it resolves track identity at a fixed `MatchConfidence.LOOSE` with no
-level selector, since a track list carrying only artist and title leaves
-every stricter tier unreachable (DL-032).
+level selector (DL-032, DL-276).
+
+Every `build-playlist` input meets the core at one seam: an ordered list
+of `tracklist.Candidate` values, each carrying its position and text for
+the report and either the `EntryRecord` the cascade reads as its old side
+or `None` for an entry that could not be parsed (DL-274).
+`traktor_nml/playlistinput.py` reads a path into that list and names the
+format and codec it read (DL-281); `buildplaylist.assemble_output` and
+`tracklist.resolve_candidates` never see the input's syntax.
 
 `traktor_nml.gui` is a fourth package alongside `traktor_nml`,
@@ -92,3 +99,3 @@
-This file is the authority for the log's high-water mark, which is `DL-273`:
+This file is the authority for the log's high-water mark, which is `DL-281`:
 an entry numbered against anything else collides with an entry this file
 names, so the next plan numbers from there.
@@ -2378,4 +2385,37 @@
   directory, the same way `rewrite.path_collides` and the write step
   consume it (DL-272).
+- Every build-playlist input format hands resolution one ordered list of
+  `Candidate(line_number, raw_text, artist, title, record)` values; a
+  `record` of `None` is an unparseable entry. Refusal (DL-027, DL-036),
+  the report rows, synthesis and the splice already depend only on a
+  per-entry outcome and those four fields, so folding unparseable entries
+  into the same list leaves them one input shape (DL-274).
+- Candidates sit on `match_records`' old side and the collection on its
+  new side for every format. Refutation's cross-source test compares
+  `from_disk` on both sides symmetrically and every tolerance reads the
+  larger of the two, and ambiguity is counted per old record, one
+  candidate per call, so the direction gives the same verdicts either way
+  (DL-278).
+- The plain-text path is held byte-identical by a golden corpus under
+  `tests/baselines/build_playlist_text/`, recorded from the code before
+  the Candidate seam existed and replayed by
+  `tests/test_build_playlist_text_parity.py`: argv, stdout, stderr, exit
+  code, output bytes and the unresolved report per case, with `uuid4`
+  fixed. `tests/baselines/manifest.json` holds no build-playlist case and
+  is not regenerated for it (DL-279).
+- The build-playlist stats keys and their order - `lines_read`,
+  `lines_resolved`, `unresolved_unparseable`, `unresolved_unmatched`,
+  `unresolved_ambiguous`, `playlist_name`, `entries_written` - are the
+  same for every input format. `lines_read` counts candidates. Adding the
+  format or codec as a stats key would change a text run's stdout (DL-280).
+- `traktor_nml/playlistinput.py` is the nicegui-free input module:
+  `detect_format`, `read_input` returning `InputRead(format, encoding,
+  candidates)` or raising `InputReadError(code)`, and the CSV column
+  definition. The CLI handler and the GUI's `_run_build_playlist` read an
+  input through `read_input` and nothing else (DL-281).
+- Resolution runs at a fixed `MatchConfidence.LOOSE` for every input
+  format. A file-derived candidate reaches the stricter tiers at LOOSE
+  because the cascade tries tiers strongest first; `FILENAME` would add
+  `bare_name`, which collides on stem component files (DL-276).
 
 ## Invariants

```

**Documentation:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md

```

> **Developer notes**: Three hunks in traktor_nml/README.md (LF): the high-water mark, the
Architecture paragraph on build-playlist, and decision bullets appended
after the DL-272 bullet at the end of Design Decisions.

**CC-M-001-009** (tests/test_tracklist.py) - implements CI-M-001-009

**Code:**

```diff
--- a/tests/test_tracklist.py
+++ b/tests/test_tracklist.py
@@ -1,6 +1,14 @@
 """Tracklist: plain-text 'Artist - Title' parsing and per-line collection resolution."""
 
 from __future__ import annotations
 
+from unittest.mock import patch
+
 from traktor_nml.model import EntryRecord, LocationParts
-from traktor_nml.tracklist import parse_tracklist, resolve_tracklist
+from traktor_nml.tracklist import (
+    Candidate,
+    parse_tracklist,
+    resolve_candidates,
+    resolve_tracklist,
+    text_candidates,
+)
@@ -145,3 +153,49 @@ def test_matched_resolution_carries_the_collection_records_primary_key() -> None:
     collection = [_collection_record("Artist", "Title", "track.mp3")]
     resolutions = resolve_tracklist(parsed, collection)
     assert resolutions[0].matched_record.primary_key == collection[0].primary_key
+
+
+def test_text_candidates_order() -> None:
+    """Parsed and unparseable lines come back as one list in physical
+    line order, each numbered as parse_tracklist numbers it, with a None
+    record exactly on the unparseable lines.
+
+    Mutation: text_candidates drops its
+        candidates.sort(key=line_number), so the unparseable lines
+        follow every parsed line and line_number reads [1, 4, 2, 5].
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    text = "A - One\nno delimiter\n# comment\nB - Two\nalso bad\n"
+    candidates = text_candidates(text)
+    assert [c.line_number for c in candidates] == [1, 2, 4, 5]
+    assert [c.record is None for c in candidates] == [False, True, False, True]
+    assert candidates[1].raw_text == "no delimiter"
+    assert (candidates[2].artist, candidates[2].title) == ("B", "Two")
+
+
+def test_resolve_candidates_unparseable() -> None:
+    """A record-None Candidate resolves as 'unparseable' without
+    match_records ever being called for it, and a parsed candidate
+    beside it still resolves.
+
+    Mutation: resolve_candidates calls match_records([record], ...)
+        before its `record is None` check, so the patched match_records
+        raises for the unparseable candidate.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    unparseable = Candidate(3, "no delimiter", "", "", None)
+
+    def _refuse(*_args, **_kwargs):
+        raise AssertionError("match_records called for an unparseable candidate")
+
+    with patch("traktor_nml.tracklist.match_records", _refuse):
+        resolutions = resolve_candidates([unparseable], [_collection_record("A", "One")])
+    assert [(r.candidate, r.outcome, r.matched_record) for r in resolutions] == [
+        (unparseable, "unparseable", None)
+    ]
+
+    parsed = text_candidates("A - One\n")[0]
+    collection = [_collection_record("A", "One")]
+    mixed = resolve_candidates([parsed, unparseable], collection)
+    assert [r.outcome for r in mixed] == ["matched", "unparseable"]
+    assert mixed[0].matched_record.primary_key == collection[0].primary_key

```

**Documentation:**

```diff
--- a/tests/test_tracklist.py
+++ b/tests/test_tracklist.py
@@ -158,2 +158,11 @@
 def test_text_candidates_order() -> None:
+    """Parsed and unparseable lines come back as one list in physical
+    line order, each numbered as parse_tracklist numbers it, with a None
+    record exactly on the unparseable lines.
+
+    Mutation: text_candidates drops its
+        candidates.sort(key=line_number), so the unparseable lines
+        follow every parsed line and line_number reads [1, 4, 2, 5].
+    Observed: the implementer records the verbatim assertion output here.
+    """
     text = "A - One\nno delimiter\n# comment\nB - Two\nalso bad\n"
@@ -167,2 +176,11 @@
 def test_resolve_candidates_unparseable() -> None:
+    """A record-None Candidate resolves as 'unparseable' without
+    match_records ever being called for it, and a parsed candidate
+    beside it still resolves.
+
+    Mutation: resolve_candidates calls match_records([record], ...)
+        before its `record is None` check, so the patched match_records
+        raises for the unparseable candidate.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     unparseable = Candidate(3, "no delimiter", "", "", None)

```


**CC-M-001-010** (tests/test_playlistinput.py) - implements CI-M-001-010

**Code:**

```diff
--- /dev/null
+++ b/tests/test_playlistinput.py
@@ -0,0 +1,93 @@
+"""playlistinput: format detection and the plain-text reader.
+
+Runs on the system interpreter with no nicegui installed (DL-069).
+Each guard names the mutation it was proven against and quotes the
+output that mutation produced.
+"""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+import pytest
+
+from traktor_nml.playlistinput import InputFormat, InputReadError, detect_format, read_input
+from traktor_nml.tracklist import text_candidates
+
+
+@pytest.mark.parametrize(
+    "name,expected",
+    [
+        ("list.csv", InputFormat.CSV),
+        ("LIST.CSV", InputFormat.CSV),
+        ("set.m3u", InputFormat.M3U),
+        ("set.m3u8", InputFormat.M3U),
+        ("tracks.txt", InputFormat.TEXT),
+        ("tracks", InputFormat.TEXT),
+        ("tracks.nml", InputFormat.TEXT),
+    ],
+)
+def test_detect_format(tmp_path: Path, name: str, expected: InputFormat) -> None:
+    """Suffix decides a file's format, case-insensitively, and any
+    suffix other than .csv, .m3u or .m3u8 - or none - is text (DL-282).
+
+    Mutation: detect_format compares path.suffix without casefold(), so
+        LIST.CSV detects as InputFormat.TEXT.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    path = tmp_path / name
+    path.write_bytes(b"")
+    assert detect_format(path) is expected
+
+
+def test_detect_format_directory(tmp_path: Path) -> None:
+    """A directory is a folder input whatever its name looks like: the
+    is_dir check decides before any suffix is read (DL-281).
+
+    Mutation: detect_format tests the suffix before path.is_dir(), so
+        the folder named looks.csv detects as InputFormat.CSV.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    folder = tmp_path / "looks.csv"
+    folder.mkdir()
+    assert detect_format(folder) is InputFormat.FOLDER
+
+
+def test_read_input_text(tmp_path: Path) -> None:
+    """A text file reads as format text, codec utf-8-sig, with exactly
+    the candidates text_candidates gives for its decoded text - a BOM
+    stripped, not left on the first artist.
+
+    Mutation: _decode_strict decodes with 'utf-8' in place of
+        'utf-8-sig', so the BOM stays on the first artist and the
+        candidates differ from text_candidates('A - One\nbad\n').
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    path = tmp_path / "tracks.txt"
+    path.write_bytes(b"\xef\xbb\xbfA - One\nbad\n")
+    read = read_input(path)
+    assert read.format is InputFormat.TEXT
+    assert read.encoding == "utf-8-sig"
+    assert read.candidates == text_candidates("A - One\nbad\n")
+    assert read.candidates[0].artist == "A"
+
+
+def test_read_input_text_refusals(tmp_path: Path) -> None:
+    """A missing path refuses with input_not_found and bytes that are
+    not UTF-8 with tracklist_decode_error, each naming the posix path -
+    the codes the CLI has always printed (DL-292).
+
+    Mutation: _decode_strict decodes with errors='replace', so the
+        non-UTF-8 file reads without raising InputReadError.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    missing = tmp_path / "absent.txt"
+    with pytest.raises(InputReadError) as missing_error:
+        read_input(missing)
+    assert missing_error.value.code == f"input_not_found={missing.as_posix()}"
+
+    bad = tmp_path / "bad.txt"
+    bad.write_bytes(b"A - One\n\xff\xfe\n")
+    with pytest.raises(InputReadError) as decode_error:
+        read_input(bad)
+    assert decode_error.value.code == f"tracklist_decode_error={bad.as_posix()}"

```

**Documentation:**

```diff
--- a/tests/test_playlistinput.py
+++ b/tests/test_playlistinput.py
@@ -30,2 +30,9 @@
 def test_detect_format(tmp_path: Path, name: str, expected: InputFormat) -> None:
+    """Suffix decides a file's format, case-insensitively, and any
+    suffix other than .csv, .m3u or .m3u8 - or none - is text (DL-282).
+
+    Mutation: detect_format compares path.suffix without casefold(), so
+        LIST.CSV detects as InputFormat.TEXT.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     path = tmp_path / name
@@ -36,2 +43,9 @@
 def test_detect_format_directory(tmp_path: Path) -> None:
+    """A directory is a folder input whatever its name looks like: the
+    is_dir check decides before any suffix is read (DL-281).
+
+    Mutation: detect_format tests the suffix before path.is_dir(), so
+        the folder named looks.csv detects as InputFormat.CSV.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     folder = tmp_path / "looks.csv"
@@ -42,2 +56,11 @@
 def test_read_input_text(tmp_path: Path) -> None:
+    """A text file reads as format text, codec utf-8-sig, with exactly
+    the candidates text_candidates gives for its decoded text - a BOM
+    stripped, not left on the first artist.
+
+    Mutation: _decode_strict decodes with 'utf-8' in place of
+        'utf-8-sig', so the BOM stays on the first artist and the
+        candidates differ from text_candidates('A - One\nbad\n').
+    Observed: the implementer records the verbatim assertion output here.
+    """
     path = tmp_path / "tracks.txt"
@@ -52,2 +75,10 @@
 def test_read_input_text_refusals(tmp_path: Path) -> None:
+    """A missing path refuses with input_not_found and bytes that are
+    not UTF-8 with tracklist_decode_error, each naming the posix path -
+    the codes the CLI has always printed (DL-292).
+
+    Mutation: _decode_strict decodes with errors='replace', so the
+        non-UTF-8 file reads without raising InputReadError.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     missing = tmp_path / "absent.txt"

```


**CC-M-001-011** (tests/CLAUDE.md) - implements CI-M-001-011

**Code:**

```diff
--- a/tests/CLAUDE.md
+++ b/tests/CLAUDE.md
@@ -34,3 +34,5 @@
-| `test_tracklist.py`      | External track-list parsing and per-line resolution tests      | Changing `tracklist.py`                                       |
+| `test_tracklist.py`      | External track-list parsing and per-line resolution tests, plus `text_candidates` keeping parsed and unparseable lines in one line-ordered list and `resolve_candidates` passing a record-less candidate through as unparseable without calling `match_records` | Changing `tracklist.py`                                       |
+| `test_playlistinput.py`  | `detect_format` by directory and suffix, and the plain-text reader's format, codec, candidates and `input_not_found`/`tracklist_decode_error` refusals | Changing `playlistinput.py`'s detection or text reader |
 | `test_write_shell_split.py` | `plan_and_write_nml` unit tests: output-collision stats-is-None, text_patch_error keeping its collected stats ahead of the error, callback-exception propagation, and printlessness across every outcome. No manifest case sets an output path equal to its input and no manifest case carries both a stats block and a stderr error, so this is the only test exercising the collision refusal and the stats-before-error ordering | Changing `plan_and_write_nml`, `WriteOutcome`, or `format_stats_and_samples` |
 | `test_build_playlist.py` | build-playlist synthesis, insertion and CLI-surface tests       | Changing `buildplaylist.py`, its insertion point, or `commands/build_playlist_cmd.py` |
+| `test_build_playlist_text_parity.py` | Byte-for-byte replay of the plain-text build-playlist path against `baselines/build_playlist_text/`: argv, stdout, stderr, exit code, output NML and unresolved report per case, recorded before the Candidate seam | Changing `tracklist.py`, `buildplaylist.py`, `playlistinput.py`'s text reader, or `build_playlist_cmd.py`'s output |
@@ -84,1 +86,2 @@
 | `baselines/` | `manifest.json` (golden CLI-invocation baseline) + `regenerate.py` + `manifest.schema.md` | Regenerating the baseline after a deliberate, reviewed behavior change |
+| `baselines/build_playlist_text/` | One directory per plain-text build-playlist case replayed by `test_build_playlist_text_parity.py`, and a README naming the commit it was recorded at; never re-recorded to make a replay pass | A text-parity replay failing, or adding a text case |

```

**Documentation:**

```diff
--- a/tests/CLAUDE.md
+++ b/tests/CLAUDE.md

```

> **Developer notes**: tests/CLAUDE.md is CRLF; write the rows with CRLF endings (newline='').

### Milestone 2: Explicit file indexing and folder input

**Files**: traktor_nml/diskscan.py, traktor_nml/playlistinput.py, tests/test_diskscan.py, tests/test_playlistinput_folder.py, tests/test_build_playlist_inputs.py

**Requirements**:

- diskscan.index_files(paths, cache=None) returns one record per path in order with duplicates kept, raising DiskReadError on stat failure
- index_scan_roots output, stats and cache behaviour unchanged
- read_input for a directory lists its own audio files, numeric-aware ordered, indexed through index_files, line_number = position, raw_text = file name
- Two-location collection case resolves by path_suffix_3; a duration-contradicting disk candidate is refuted and a size-different one kept

**Acceptance Criteria**:

- Folder '1 - a.mp3, 2 - b.mp3, 10 - c.mp3' yields that order; mutation to plain sort fails with verbatim output
- A subdirectory's files are not candidates
- Stat failure mid-list raises; mutation to skip-and-count fails the guard
- test_baseline_parity.py reconnect and discover cases pass unchanged

**Tests**:

- unit: index_files order, duplicates, tag-less record, stat failure
- unit: numeric-aware order key including case and equal-number tiebreak
- integration: build-playlist over a fixture folder whose files sit at collection locations writes the playlist in folder order
- integration: collection holding one track at two locations resolves to the folder's copy

#### Code Intent

- **CI-M-002-001** `traktor_nml/diskscan.py::index_files/_record_for_file`: _record_for_file(resolved, file_stat, tags) builds the EntryRecord index_scan_roots constructs today; index_files(paths, cache=None) stats each path (OSError -> DiskReadError naming the path), reads tags through cache when given or _read_tags directly, substitutes empty tags when unreadable, and returns records in input order (refs: DL-290, DL-291)
- **CI-M-002-002** `traktor_nml/playlistinput.py::read_folder/folder_order_key`: folder_order_key(name) splits the casefolded name into digit and non-digit runs with digits as ints, then the plain name; read_folder lists only direct children that are files passing diskscan's audio-extension check, sorts by folder_order_key, indexes through index_files and returns Candidates (encoding 'n/a'); DiskReadError -> InputReadError('input_read_error=<posix path>'); candidates resolve through match_records alone with no exact-location pre-pass (DL-277), and a file the collection does not hold flows to the unresolved report as unmatched with no ENTRY added (DL-293) (refs: DL-289, DL-275, DL-292, DL-277, DL-293)
- **CI-M-002-003** `tests/test_diskscan.py::test_index_files_*`: Guards index_files: order and duplicates kept, stat failure raises DiskReadError naming the path, no cache file without a cache; each guard's docstring names its mutation and the verbatim output it produced (refs: DL-290, DL-291)
- **CI-M-002-004** `tests/test_playlistinput_folder.py::test_folder_*`: Guards read_folder and folder_order_key: numeric-aware order, casefold and plain-name tiebreak, no recursion and no non-audio files, disk fields on each record, DiskReadError refused as input_read_error; each guard's docstring names its mutation and the verbatim output it produced (refs: DL-289, DL-275, DL-292)
- **CI-M-002-005** `tests/test_build_playlist_inputs.py::test_folder_input_*/test_two_location_*/test_disk_candidate_*`: Integration over the real cascade: folder input writes the playlist in folder order, a file the collection lacks is unmatched with no ENTRY added, a two-location collection resolves to the folder's copy at path_suffix_3, duration refutes and size band keeps a disk candidate (refs: DL-277, DL-278, DL-293)

#### Code Changes

**CC-M-002-001** (traktor_nml/diskscan.py) - implements CI-M-002-001

**Code:**

```diff
--- a/traktor_nml/diskscan.py
+++ b/traktor_nml/diskscan.py
@@ -74,5 +74,50 @@ def _placeholder_location(path: Path) -> LocationParts:
     return LocationParts(volume="", volumeid="", dir_value=posix_dir, file_name=path.name)
 
 
+_EMPTY_TAGS = {"artist": "", "title": "", "album": "", "playtime_float": "", "bitrate": ""}
+
+
+def _record_for_file(resolved: Path, file_stat, tags: Optional[dict]) -> EntryRecord:
+    """The disk-side EntryRecord for one file, shared by index_scan_roots
+    and index_files so a scanned file and an explicitly listed one carry
+    identical fields (DL-291). tags None gives empty tag fields: the file
+    is still a candidate for the path and size tiers."""
+    tags = tags if tags is not None else _EMPTY_TAGS
+    return EntryRecord(
+        entry=None,
+        artist=tags.get("artist", ""),
+        title=tags.get("title", ""),
+        audio_id="",
+        # KILOBYTES, matching the unit Traktor writes into
+        # FILESIZE, so EntryRecord.filesize means one thing
+        # regardless of which side produced the record. The
+        # alternative - storing bytes and converting at
+        # comparison time - has to infer provenance from
+        # another field, and infers it silently: a candidate
+        # built without that field is out by 1024x with no
+        # error, only wrong answers.
+        filesize=str(round(file_stat.st_size / 1024)),
+        playtime_float=tags.get("playtime_float", ""),
+        bitrate=tags.get("bitrate", ""),
+        album=tags.get("album", ""),
+        file_name=resolved.name,
+        location=_placeholder_location(resolved),
+        source_path=resolved,
+    )
+
+
+class DiskReadError(OSError):
+    """A file named explicitly to index_files could not be stat()ed.
+
+    Raised rather than counted: index_scan_roots may skip an unreadable
+    file because the caller asked for whatever a walk finds, but a caller
+    of index_files named every file it wants, and a list one short is
+    indistinguishable from a complete one (DL-290)."""
+
+    def __init__(self, path: Path) -> None:
+        super().__init__(f"cannot read {path.as_posix()}")
+        self.path = path
+
+
 
 def _tag_free_summary() -> str:
@@ -248,33 +293,40 @@ def index_scan_roots(
 
             if tags is None:
                 stats["unreadable"] += 1
-                tags = {"artist": "", "title": "", "album": "", "playtime_float": "", "bitrate": ""}
 
-            records.append(
-                EntryRecord(
-                    entry=None,
-                    artist=tags.get("artist", ""),
-                    title=tags.get("title", ""),
-                    audio_id="",
-                    # KILOBYTES, matching the unit Traktor writes into
-                    # FILESIZE, so EntryRecord.filesize means one thing
-                    # regardless of which side produced the record. The
-                    # alternative - storing bytes and converting at
-                    # comparison time - has to infer provenance from
-                    # another field, and infers it silently: a candidate
-                    # built without that field is out by 1024x with no
-                    # error, only wrong answers.
-                    filesize=str(round(file_stat.st_size / 1024)),
-                    playtime_float=tags.get("playtime_float", ""),
-                    bitrate=tags.get("bitrate", ""),
-                    album=tags.get("album", ""),
-                    file_name=resolved.name,
-                    location=_placeholder_location(resolved),
-                    source_path=resolved,
-                )
-            )
+            records.append(_record_for_file(resolved, file_stat, tags))
             _report_progress(on_progress, done, total, resolved, callback_every)
     finally:
         cache.flush()
 
     return records
+
+
+def index_files(paths: Iterable[Path], cache: Optional[TagCache] = None) -> list[EntryRecord]:
+    """One EntryRecord per path, in the order given, duplicates kept.
+
+    No directory walk and no deduplication: the caller's list is the
+    playlist, so its order and repetitions are the playlist's (DL-037,
+    DL-290). A path whose stat() fails raises DiskReadError naming it. A
+    file whose tags cannot be read still yields a record, with empty tag
+    fields. With cache None tags are read directly and no cache file is
+    read or written, so build-playlist leaves no side file (DL-290).
+    """
+    records: list[EntryRecord] = []
+    for path in paths:
+        resolved = Path(path).resolve()
+        try:
+            file_stat = resolved.stat()
+        except OSError:
+            raise DiskReadError(resolved) from None
+        if cache is None:
+            tags = _read_tags(resolved)
+        elif cache.should_refresh(resolved, file_stat.st_size, file_stat.st_mtime, False):
+            tags = _read_tags(resolved)
+            cache.put(resolved, file_stat.st_size, file_stat.st_mtime, tags)
+        else:
+            tags = cache.get(resolved, file_stat.st_size, file_stat.st_mtime)
+        records.append(_record_for_file(resolved, file_stat, tags))
+    if cache is not None:
+        cache.flush()
+    return records

```

**Documentation:**

```diff
--- a/traktor_nml/diskscan.py
+++ b/traktor_nml/diskscan.py
@@ -293,7 +293,10 @@ def index_scan_roots(

             if tags is None:
                 stats["unreadable"] += 1

+            # Only the record construction is shared with index_files; this
+            # walk keeps its own skip, dedupe, stats and cache rules, which
+            # the reconnect and discover baselines pin (DL-291).
             records.append(_record_for_file(resolved, file_stat, tags))
             _report_progress(on_progress, done, total, resolved, callback_every)
     finally:
@@ -320,5 +323,8 @@ def index_files(paths: Iterable[Path], cache: Optional[TagCache] = None) -> list[EntryRecord]:
             file_stat = resolved.stat()
         except OSError:
             raise DiskReadError(resolved) from None
+        # A caller-supplied cache follows index_scan_roots' refresh rule;
+        # build-playlist passes none, so its runs read tags directly and
+        # leave no cache file behind (DL-290).
         if cache is None:
             tags = _read_tags(resolved)

```


**CC-M-002-002** (traktor_nml/playlistinput.py) - implements CI-M-002-002

**Code:**

```diff
--- a/traktor_nml/playlistinput.py
+++ b/traktor_nml/playlistinput.py
@@ -22,5 +22,8 @@
 import enum
+import re
 from dataclasses import dataclass
 from pathlib import Path
 
+from .diskscan import DiskReadError, _has_audio_extension, index_files
+from .model import EntryRecord
 from .tracklist import Candidate, text_candidates
@@ -95,4 +98,58 @@ def read_text(path: Path) -> InputRead:
     return InputRead(InputFormat.TEXT, "utf-8-sig", text_candidates(text))
 
 
+_DIGIT_RUN = re.compile(r"(\d+)")
+
+
+def folder_order_key(name: str) -> tuple:
+    """Numeric-aware order for a folder's file names, the order Explorer
+    and Finder show: '2 - b.mp3' before '10 - c.mp3', where a plain string
+    sort puts '10' first (DL-289). The casefolded name is split into digit
+    and non-digit runs, digit runs compared as integers; each run is
+    tagged so a digit run and a text run at the same position compare
+    without a TypeError. The plain name breaks ties ('01 a' and '1 a'),
+    so the order is total and repeatable."""
+    runs = tuple(
+        (0, int(run), "") if run.isdigit() else (1, 0, run)
+        for run in _DIGIT_RUN.split(name.casefold())
+        if run
+    )
+    return (runs, name)
+
+
+def _file_candidate(position: int, raw_text: str, record: EntryRecord) -> Candidate:
+    # artist/title shown in the report come from the record's own tags,
+    # empty for an untagged file; raw_text already names the file.
+    return Candidate(position, raw_text, record.artist, record.title, record)
+
+
+def _index_or_refuse(paths: list[Path]) -> list[EntryRecord]:
+    try:
+        return index_files(paths)
+    except DiskReadError as exc:
+        # One named refusal rather than a shorter list (DL-292).
+        raise InputReadError(f"input_read_error={exc.path.as_posix()}") from None
+
+
+def read_folder(path: Path) -> InputRead:
+    """The folder's own audio files - no recursion (DL-289) - in
+    folder_order_key order, each indexed from disk so its size, duration,
+    tags, file name and folder parts reach the stricter tiers (DL-275).
+    line_number is the 1-based position in that order and raw_text the
+    file name. Candidates resolve through match_records alone (DL-277),
+    and a file the collection does not hold is reported unmatched; no
+    ENTRY is ever added for it (DL-293)."""
+    try:
+        children = [child for child in path.iterdir() if child.is_file() and _has_audio_extension(child)]
+    except OSError:
+        raise InputReadError(f"input_not_found={path.as_posix()}") from None
+    children.sort(key=lambda child: folder_order_key(child.name))
+    records = _index_or_refuse(children)
+    candidates = [
+        _file_candidate(position, child.name, record)
+        for position, (child, record) in enumerate(zip(children, records), start=1)
+    ]
+    return InputRead(InputFormat.FOLDER, "n/a", candidates)
+
+
 def read_input(path: Path) -> InputRead:

```

**Documentation:**

```diff
--- a/traktor_nml/playlistinput.py
+++ b/traktor_nml/playlistinput.py
@@ -120,5 +120,7 @@ def folder_order_key(name: str) -> tuple:
 def _file_candidate(position: int, raw_text: str, record: EntryRecord) -> Candidate:
     # artist/title shown in the report come from the record's own tags,
     # empty for an untagged file; raw_text already names the file.
+    # The record goes on whole: size, duration, file name and folder parts
+    # are what let the entry match above artist_title (DL-275).
     return Candidate(position, raw_text, record.artist, record.title, record)

@@ -125,5 +127,10 @@

 def _index_or_refuse(paths: list[Path]) -> list[EntryRecord]:
+    """index_files over paths, its DiskReadError translated into the
+    input_read_error=<path> refusal. diskscan stays free of this module's
+    error type, so the translation happens here, and the code names the
+    file that failed rather than the folder or playlist holding it
+    (DL-292)."""
     try:
         return index_files(paths)
     except DiskReadError as exc:
@@ -142,5 +149,7 @@ def read_folder(path: Path) -> InputRead:
     ENTRY is ever added for it (DL-293)."""
     try:
+        # iterdir, not a recursive walk: the chosen folder's own files only
+        # (DL-289).
         children = [child for child in path.iterdir() if child.is_file() and _has_audio_extension(child)]
     except OSError:
         raise InputReadError(f"input_not_found={path.as_posix()}") from None

```

> **Developer notes**: Adds the folder reader to traktor_nml/playlistinput.py (as M-001 left it),
plus tests/test_diskscan.py, tests/test_playlistinput_folder.py and
tests/test_build_playlist_inputs.py for the milestone. read_input's
dispatch for folders lands with the full dispatch in CI-M-005-002; until
then tests call read_folder directly.

**CC-M-002-003** (tests/test_diskscan.py) - implements CI-M-002-003

**Code:**

```diff
--- a/tests/test_diskscan.py
+++ b/tests/test_diskscan.py
@@ -131,0 +132,59 @@
+
+
+def test_index_files_keeps_order_and_duplicates(tmp_path):
+    """index_files returns one record per path in the order given, a
+    repeated path twice, sizes in KB, source_path set, and a file with no
+    readable tags as a record with empty tag fields (DL-290).
+
+    Mutation: index_files skips a resolved path it has already indexed,
+        the way _enumerate_candidates deduplicates, so [b, a, b] yields
+        two records.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    from traktor_nml.diskscan import index_files
+
+    a = tmp_path / "a.mp3"
+    b = tmp_path / "b.mp3"
+    a.write_bytes(b"\0" * 4096)
+    b.write_bytes(b"\0" * 2048)
+    records = index_files([b, a, b])
+    assert [r.file_name for r in records] == ["b.mp3", "a.mp3", "b.mp3"]
+    assert [r.filesize for r in records] == ["2", "4", "2"]
+    assert all(r.source_path is not None and r.entry is None for r in records)
+    assert (records[0].artist, records[0].title, records[0].playtime_float) == ("", "", "")
+
+
+def test_index_files_raises_on_stat_failure(tmp_path):
+    """A path that cannot be stat()ed mid-list raises DiskReadError
+    naming it; no shorter list comes back (DL-290).
+
+    Mutation: index_files catches OSError from stat() with `continue` in
+        place of raising DiskReadError, so no exception is raised.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    import pytest
+
+    from traktor_nml.diskscan import DiskReadError, index_files
+
+    present = tmp_path / "a.mp3"
+    present.write_bytes(b"\0")
+    missing = tmp_path / "gone.mp3"
+    with pytest.raises(DiskReadError) as error:
+        index_files([present, missing, present])
+    assert error.value.path == missing.resolve()
+
+
+def test_index_files_writes_no_cache_file_without_a_cache(tmp_path):
+    """With cache None no file other than the inputs appears (DL-290).
+
+    Mutation: index_files, given cache None, creates
+        TagCache(resolved.parent / 'tag_cache.json') and flushes it, so
+        a tag_cache.json file appears beside a.mp3.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    from traktor_nml.diskscan import index_files
+
+    track = tmp_path / "a.mp3"
+    track.write_bytes(b"\0")
+    index_files([track])
+    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.mp3"]

```

**Documentation:**

```diff
--- a/tests/test_diskscan.py
+++ b/tests/test_diskscan.py
@@ -134,2 +134,11 @@
 def test_index_files_keeps_order_and_duplicates(tmp_path):
+    """index_files returns one record per path in the order given, a
+    repeated path twice, sizes in KB, source_path set, and a file with no
+    readable tags as a record with empty tag fields (DL-290).
+
+    Mutation: index_files skips a resolved path it has already indexed,
+        the way _enumerate_candidates deduplicates, so [b, a, b] yields
+        two records.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     from traktor_nml.diskscan import index_files
@@ -148,2 +157,9 @@
 def test_index_files_raises_on_stat_failure(tmp_path):
+    """A path that cannot be stat()ed mid-list raises DiskReadError
+    naming it; no shorter list comes back (DL-290).
+
+    Mutation: index_files catches OSError from stat() with `continue` in
+        place of raising DiskReadError, so no exception is raised.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     import pytest
@@ -161,2 +177,9 @@
 def test_index_files_writes_no_cache_file_without_a_cache(tmp_path):
+    """With cache None no file other than the inputs appears (DL-290).
+
+    Mutation: index_files, given cache None, creates
+        TagCache(resolved.parent / 'tag_cache.json') and flushes it, so
+        a tag_cache.json file appears beside a.mp3.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     from traktor_nml.diskscan import index_files

```


**CC-M-002-004** (tests/test_playlistinput_folder.py) - implements CI-M-002-004

**Code:**

```diff
--- /dev/null
+++ b/tests/test_playlistinput_folder.py
@@ -0,0 +1,98 @@
+"""playlistinput's folder reader: its own files only, in numeric-aware
+name order, indexed from disk. System interpreter, no nicegui."""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+import pytest
+
+from traktor_nml.playlistinput import InputFormat, InputReadError, folder_order_key, read_folder
+
+
+def _touch(path: Path, size: int = 1024) -> Path:
+    path.write_bytes(b"\0" * size)
+    return path
+
+
+def test_folder_order_is_numeric_aware(tmp_path: Path) -> None:
+    """'1 - a', '2 - b', '10 - c' read in that order.
+
+    Mutation: read_folder sorts children with key=lambda child:
+        child.name, so '10 - c.mp3' reads before '2 - b.mp3'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    for name in ("10 - c.mp3", "2 - b.mp3", "1 - a.mp3"):
+        _touch(tmp_path / name)
+    read = read_folder(tmp_path)
+    assert read.format is InputFormat.FOLDER
+    assert read.encoding == "n/a"
+    assert [c.raw_text for c in read.candidates] == ["1 - a.mp3", "2 - b.mp3", "10 - c.mp3"]
+    assert [c.line_number for c in read.candidates] == [1, 2, 3]
+
+
+def test_folder_order_key_case_and_ties() -> None:
+    """Case does not split the order, and names equal after casefolding
+    and integer comparison still order totally by the plain name.
+
+    Mutation: folder_order_key splits name without casefold(), so 'B
+        2.mp3' sorts before 'a 10.mp3'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    names = ["B 2.mp3", "a 10.mp3", "A 2.mp3", "01 x.mp3", "1 x.mp3", "track.mp3"]
+    assert sorted(names, key=folder_order_key) == [
+        "01 x.mp3", "1 x.mp3", "A 2.mp3", "a 10.mp3", "B 2.mp3", "track.mp3",
+    ]
+
+
+def test_subdirectory_files_are_not_candidates(tmp_path: Path) -> None:
+    """A file inside a subfolder is not read, and a non-audio file is
+    skipped (DL-289).
+
+    Mutation: read_folder iterates path.rglob('*') in place of
+        path.iterdir(), so sub/inner.mp3 becomes a candidate.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    _touch(tmp_path / "top.mp3")
+    _touch(tmp_path / "cover.jpg")
+    (tmp_path / "sub").mkdir()
+    _touch(tmp_path / "sub" / "inner.mp3")
+    assert [c.raw_text for c in read_folder(tmp_path).candidates] == ["top.mp3"]
+
+
+def test_folder_candidates_carry_disk_fields(tmp_path: Path) -> None:
+    """Each record carries size in KB, the file name and the folder's
+    own name in its placeholder location - the fields the path and size
+    tiers read (DL-275).
+
+    Mutation: _record_for_file sets filesize=str(file_stat.st_size), so
+        the record holds '8192' in place of '8'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    _touch(tmp_path / "a.mp3", 8192)
+    record = read_folder(tmp_path).candidates[0].record
+    assert record.filesize == "8"
+    assert record.file_name == "a.mp3"
+    assert record.location.decoded_dir.name == tmp_path.resolve().name
+
+
+def test_folder_stat_failure_refuses(tmp_path: Path, monkeypatch) -> None:
+    """A file that cannot be indexed refuses the read with
+    input_read_error naming it, never a shorter list (DL-292).
+
+    Mutation: _index_or_refuse returns [] on DiskReadError, so
+        read_folder returns zero candidates without raising
+        InputReadError.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    from traktor_nml import diskscan
+
+    _touch(tmp_path / "a.mp3")
+
+    def _fail(paths, cache=None):
+        raise diskscan.DiskReadError(Path(tmp_path / "a.mp3"))
+
+    monkeypatch.setattr("traktor_nml.playlistinput.index_files", _fail)
+    with pytest.raises(InputReadError) as error:
+        read_folder(tmp_path)
+    assert error.value.code == f"input_read_error={(tmp_path / 'a.mp3').as_posix()}"

```

**Documentation:**

```diff
--- a/tests/test_playlistinput_folder.py
+++ b/tests/test_playlistinput_folder.py
@@ -18,2 +18,8 @@
 def test_folder_order_is_numeric_aware(tmp_path: Path) -> None:
+    """'1 - a', '2 - b', '10 - c' read in that order.
+
+    Mutation: read_folder sorts children with key=lambda child:
+        child.name, so '10 - c.mp3' reads before '2 - b.mp3'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     for name in ("10 - c.mp3", "2 - b.mp3", "1 - a.mp3"):
@@ -28,2 +34,9 @@
 def test_folder_order_key_case_and_ties() -> None:
+    """Case does not split the order, and names equal after casefolding
+    and integer comparison still order totally by the plain name.
+
+    Mutation: folder_order_key splits name without casefold(), so 'B
+        2.mp3' sorts before 'a 10.mp3'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     names = ["B 2.mp3", "a 10.mp3", "A 2.mp3", "01 x.mp3", "1 x.mp3", "track.mp3"]
@@ -35,2 +48,9 @@
 def test_subdirectory_files_are_not_candidates(tmp_path: Path) -> None:
+    """A file inside a subfolder is not read, and a non-audio file is
+    skipped (DL-289).
+
+    Mutation: read_folder iterates path.rglob('*') in place of
+        path.iterdir(), so sub/inner.mp3 becomes a candidate.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     _touch(tmp_path / "top.mp3")
@@ -43,2 +63,10 @@
 def test_folder_candidates_carry_disk_fields(tmp_path: Path) -> None:
+    """Each record carries size in KB, the file name and the folder's
+    own name in its placeholder location - the fields the path and size
+    tiers read (DL-275).
+
+    Mutation: _record_for_file sets filesize=str(file_stat.st_size), so
+        the record holds '8192' in place of '8'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     _touch(tmp_path / "a.mp3", 8192)
@@ -51,2 +79,10 @@
 def test_folder_stat_failure_refuses(tmp_path: Path, monkeypatch) -> None:
+    """A file that cannot be indexed refuses the read with
+    input_read_error naming it, never a shorter list (DL-292).
+
+    Mutation: _index_or_refuse returns [] on DiskReadError, so
+        read_folder returns zero candidates without raising
+        InputReadError.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     from traktor_nml import diskscan

```


**CC-M-002-005** (tests/test_build_playlist_inputs.py) - implements CI-M-002-005

**Code:**

```diff
--- /dev/null
+++ b/tests/test_build_playlist_inputs.py
@@ -0,0 +1,134 @@
+"""build-playlist over file-derived inputs, resolved through the real
+cascade against a collection built to sit where the input files sit.
+M-003, M-004 and M-005 add their formats' cases to this module."""
+
+from __future__ import annotations
+
+import uuid
+from pathlib import Path
+from unittest.mock import patch
+
+from traktor_nml.buildplaylist import assemble_output
+from traktor_nml.model import EntryRecord, LocationParts, collection_records, encode_traktor_dir
+from traktor_nml.playlistinput import read_folder
+from traktor_nml.tracklist import Candidate, resolve_candidates
+from traktor_nml.xmlio import parse_xml_bytes
+
+_FIXED_UUID = uuid.UUID("00000000-0000-4000-8000-000000000000")
+
+
+def _entry_for(path: Path, artist: str = "", title: str = "", time: str = "", size_kb: str = "") -> str:
+    resolved = path.resolve()
+    dir_value = encode_traktor_dir("/".join(resolved.parent.parts[1:]))
+    drive = resolved.drive or "C:"
+    return (
+        f'<ENTRY TITLE="{title}" ARTIST="{artist}" AUDIO_ID="">'
+        f'<LOCATION DIR="{dir_value}" FILE="{resolved.name}" VOLUME="{drive}" VOLUMEID="{drive}"></LOCATION>'
+        f'<INFO BITRATE="320" PLAYTIME_FLOAT="{time}" FILESIZE="{size_kb}"></INFO>'
+        "</ENTRY>"
+    )
+
+
+def _nml(entries: list[str]) -> str:
+    return (
+        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
+        f'<COLLECTION ENTRIES="{len(entries)}">{"".join(entries)}</COLLECTION>'
+        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0">'
+        "</SUBNODES></NODE></PLAYLISTS><SETS></SETS><INDEXING></INDEXING></NML>"
+    )
+
+
+def test_folder_input_writes_playlist_in_folder_order(tmp_path: Path) -> None:
+    """Files sitting at their collection locations resolve, and the
+    playlist lists them in the folder's numeric-aware order.
+
+    Mutation: read_folder sorts children with key=lambda child:
+        child.name, so the playlist's primary keys read '1 - a.mp3', '10
+        - c.mp3', '2 - b.mp3'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    music = tmp_path / "Music" / "Techno" / "Set"
+    music.mkdir(parents=True)
+    names = ["10 - c.mp3", "2 - b.mp3", "1 - a.mp3"]
+    for name in names:
+        (music / name).write_bytes(b"\0" * 4096)
+    source = _nml([_entry_for(music / name, size_kb="4") for name in names])
+    root = parse_xml_bytes(source.encode("utf-8"))
+    with patch("uuid.uuid4", return_value=_FIXED_UUID):
+        result = assemble_output(source, root, read_folder(music).candidates, "Set")
+    assert result.errors == []
+    keys = [line.split('KEY="')[1].split('"')[0] for line in result.output.split("<PRIMARYKEY")[1:]]
+    assert [key.rsplit("/:", 1)[1] for key in keys] == ["1 - a.mp3", "2 - b.mp3", "10 - c.mp3"]
+
+
+def test_folder_file_not_in_collection_is_unmatched(tmp_path: Path) -> None:
+    """A file the collection does not hold is an unmatched row, and no
+    ENTRY is added for it (DL-293).
+
+    Mutation: _resolve_lines appends an UnresolvedRow only when
+        resolution.outcome is not 'unmatched', so stray.mp3 is missing
+        from unresolved_rows.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    (tmp_path / "stray.mp3").write_bytes(b"\0" * 4096)
+    source = _nml([])
+    root = parse_xml_bytes(source.encode("utf-8"))
+    result = assemble_output(source, root, read_folder(tmp_path).candidates, "Set", allow_unmatched=True)
+    assert [(row.raw_text, row.kind) for row in result.unresolved_rows] == [("stray.mp3", "unmatched")]
+    assert result.errors == ["no_entries_resolved"]
+
+
+def test_two_location_collection_resolves_to_the_folders_copy(tmp_path: Path) -> None:
+    """A collection holding the same file name, artist, title and size
+    at two locations resolves the folder's file uniquely at
+    path_suffix_3, with no exact-location pre-pass (DL-277).
+
+    Mutation: diskscan._placeholder_location returns a location with an
+        empty dir_value, so path_suffix_3 cannot fire and both
+        collection copies tie on the file-name tiers as ambiguous.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    here = tmp_path / "Music" / "Techno" / "Artist"
+    here.mkdir(parents=True)
+    track = here / "track.mp3"
+    track.write_bytes(b"\0" * 4096)
+    elsewhere = tmp_path / "Backup" / "Old" / "Other" / "track.mp3"
+    source = _nml([
+        _entry_for(track, "A", "T", size_kb="4"),
+        _entry_for(elsewhere, "A", "T", size_kb="4"),
+    ])
+    root = parse_xml_bytes(source.encode("utf-8"))
+    candidate = read_folder(here).candidates[0]
+    resolution = resolve_candidates([candidate], collection_records(root))[0]
+    assert resolution.outcome == "matched"
+    assert resolution.matched_record.location.file_name == "track.mp3"
+    assert resolution.matched_record.location.decoded_dir.parts[-3:] == ("Music", "Techno", "Artist")
+
+
+def _collection_record(time: str, size: str, dir_value: str = "/:Music/:") -> EntryRecord:
+    return EntryRecord(
+        entry=None, artist="A", title="T", audio_id="", filesize=size, playtime_float=time,
+        bitrate="", album="", file_name="track.mp3",
+        location=LocationParts("C:", "C:", dir_value, "track.mp3"),
+    )
+
+
+def test_disk_candidate_refuted_by_duration_kept_across_size(tmp_path: Path) -> None:
+    """With the disk candidate on the old side, a collection entry whose
+    duration is a factor off is refuted, and one whose size differs
+    within the cross-source band is kept (DL-278).
+
+    Mutation: resolve_candidates calls match_records(collection,
+        [record], ...) with the candidate on the new side, so the 30.0s
+        entry is not refuted and the first outcome is not 'unmatched'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    disk = EntryRecord(
+        entry=None, artist="A", title="T", audio_id="", filesize="8000", playtime_float="200.000",
+        bitrate="", album="", file_name="track.mp3",
+        location=LocationParts("", "", "/:x/:", "track.mp3"), source_path=tmp_path / "track.mp3",
+    )
+    candidate = Candidate(1, "track.mp3", "A", "T", disk)
+    assert resolve_candidates([candidate], [_collection_record("30.0", "8000")])[0].outcome == "unmatched"
+    assert resolve_candidates([candidate], [_collection_record("200.0", "9000")])[0].outcome == "matched"

```

**Documentation:**

```diff
--- a/tests/test_build_playlist_inputs.py
+++ b/tests/test_build_playlist_inputs.py
@@ -42,2 +42,10 @@
 def test_folder_input_writes_playlist_in_folder_order(tmp_path: Path) -> None:
+    """Files sitting at their collection locations resolve, and the
+    playlist lists them in the folder's numeric-aware order.
+
+    Mutation: read_folder sorts children with key=lambda child:
+        child.name, so the playlist's primary keys read '1 - a.mp3', '10
+        - c.mp3', '2 - b.mp3'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     music = tmp_path / "Music" / "Techno" / "Set"
@@ -57,2 +65,10 @@
 def test_folder_file_not_in_collection_is_unmatched(tmp_path: Path) -> None:
+    """A file the collection does not hold is an unmatched row, and no
+    ENTRY is added for it (DL-293).
+
+    Mutation: _resolve_lines appends an UnresolvedRow only when
+        resolution.outcome is not 'unmatched', so stray.mp3 is missing
+        from unresolved_rows.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     (tmp_path / "stray.mp3").write_bytes(b"\0" * 4096)
@@ -66,2 +82,11 @@
 def test_two_location_collection_resolves_to_the_folders_copy(tmp_path: Path) -> None:
+    """A collection holding the same file name, artist, title and size
+    at two locations resolves the folder's file uniquely at
+    path_suffix_3, with no exact-location pre-pass (DL-277).
+
+    Mutation: diskscan._placeholder_location returns a location with an
+        empty dir_value, so path_suffix_3 cannot fire and both
+        collection copies tie on the file-name tiers as ambiguous.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     here = tmp_path / "Music" / "Techno" / "Artist"
@@ -92,2 +117,11 @@
 def test_disk_candidate_refuted_by_duration_kept_across_size(tmp_path: Path) -> None:
+    """With the disk candidate on the old side, a collection entry whose
+    duration is a factor off is refuted, and one whose size differs
+    within the cross-source band is kept (DL-278).
+
+    Mutation: resolve_candidates calls match_records(collection,
+        [record], ...) with the candidate on the new side, so the 30.0s
+        entry is not refuted and the first outcome is not 'unmatched'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     disk = EntryRecord(

```


### Milestone 3: M3U and M3U8 input

**Files**: traktor_nml/playlistinput.py, tests/test_playlistinput_m3u.py, tests/test_build_playlist_inputs.py

**Requirements**:

- #EXTINF duration and 'Artist - Title' attach to the next path line; other directives ignored
- Relative paths resolve against the playlist's folder; URL lines become unparseable Candidates
- Existing files are indexed via index_files; absent paths become path-string records with Windows or POSIX folder decoding
- .m3u8 utf-8-sig strict; .m3u utf-8-sig then cp1252, reported as InputRead.encoding

**Acceptance Criteria**:

- A Mac path '/Users/x/Music/Techno/Artist/track.mp3' absent here matches the collection entry at D:/Sync/Music/Techno/Artist/track.mp3 by path_suffix_3
- A Windows path string yields the same folder parts as the equivalent POSIX path
- A cp1252 .m3u reports encoding cp1252; a cp1252 .m3u8 refuses with tracklist_decode_error
- Mutating path flavour detection to always POSIX fails the Windows-path guard with verbatim output

**Tests**:

- unit: EXTINF attachment, -1 duration, display text without ' - '
- unit: relative, absolute Windows, absolute POSIX, URL lines
- unit: 0.9s EXTINF truncation matched; 5s gap refuted
- integration: CLI build-playlist over an M3U mixing present and absent files

#### Code Intent

- **CI-M-003-001** `traktor_nml/playlistinput.py::read_m3u/_path_string_record`: read_m3u decodes per DL encoding rule, walks lines holding the pending #EXTINF, and emits Candidates in path-line order: present files through index_files with artist/title from tags, else _path_string_record(path_text, extinf) building EntryRecord with file_name, placeholder LocationParts(volume '', volumeid '', dir_value from encode_traktor_dir of anchor-stripped folder parts), artist/title/playtime_float from #EXTINF (a present file ignores its #EXTINF) and source_path None; URL lines are record-None Candidates; DiskReadError -> InputReadError('input_read_error=<posix path>'); a path the collection does not hold flows to the unresolved report as unmatched with no ENTRY added (DL-293), resolved through match_records alone (DL-277) (refs: DL-287, DL-288, DL-283, DL-275, DL-278, DL-292, DL-293, DL-277)
- **CI-M-003-002** `tests/test_playlistinput_m3u.py::test_extinf_*/test_path_*/test_windows_*/test_mac_*/test_encodings/test_present_*`: Guards read_m3u: #EXTINF attaches to the next path line only, path flavours and URL lines, Windows and POSIX strings decode alike, absent Mac path matches by path_suffix_3, EXTINF truncation tolerance, .m3u cp1252 fallback and strict .m3u8, present file ignores #EXTINF; each guard's docstring names its mutation and the verbatim output it produced (refs: DL-287, DL-288, DL-283, DL-275, DL-278)
- **CI-M-003-003** `tests/test_build_playlist_inputs.py::test_cli_build_playlist_over_m3u_*`: CLI build-playlist over an M3U mixing a present file and an absent path writes both entries (refs: DL-275, DL-277)

#### Code Changes

**CC-M-003-001** (traktor_nml/playlistinput.py) - implements CI-M-003-001

**Code:**

```diff
--- a/traktor_nml/playlistinput.py
+++ b/traktor_nml/playlistinput.py
@@ -22,8 +22,9 @@
 import enum
 import re
 from dataclasses import dataclass
-from pathlib import Path
+from pathlib import Path, PurePosixPath, PureWindowsPath
+from typing import Optional
 
 from .diskscan import DiskReadError, _has_audio_extension, index_files
-from .model import EntryRecord
+from .model import EntryRecord, LocationParts, encode_traktor_dir
 from .tracklist import Candidate, text_candidates
@@ -88,4 +89,21 @@ def _decode_strict(data: bytes, path: Path) -> str:
         raise InputReadError(f"tracklist_decode_error={path.as_posix()}") from None
 
 
+def _decode_with_fallback(data: bytes, path: Path) -> tuple[str, str]:
+    """(text, codec): utf-8-sig when the bytes are UTF-8, else cp1252,
+    which decodes the bytes an .m3u or a CSV saved by Windows software
+    carries (DL-283). cp1252 accepts almost any byte sequence, so a file in
+    another single-byte codepage decodes wrongly without an error; the
+    codec is returned so both surfaces can name it."""
+    try:
+        return data.decode("utf-8-sig"), "utf-8-sig"
+    except UnicodeDecodeError:
+        pass
+    try:
+        return data.decode("cp1252"), "cp1252"
+    except UnicodeDecodeError:
+        # cp1252 leaves five bytes undefined (0x81, 0x8D, 0x8F, 0x90, 0x9D).
+        raise InputReadError(f"tracklist_decode_error={path.as_posix()}") from None
+
+
 def read_text(path: Path) -> InputRead:
@@ -167,4 +185,129 @@ def read_folder(path: Path) -> InputRead:
     return InputRead(InputFormat.FOLDER, "n/a", candidates)
 
 
+_EXTINF = re.compile(r"^#EXTINF:\s*(-?\d+(?:\.\d+)?)\s*(?:[^,]*),(.*)$", re.IGNORECASE)
+# A drive letter ("C:") is not a URL scheme; a scheme needs two or more letters.
+_URL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+://")
+_DRIVE = re.compile(r"^[A-Za-z]:")
+
+
+@dataclass(frozen=True)
+class _ExtInf:
+    seconds: str  # "" when the directive gave no positive duration
+    artist: str
+    title: str
+
+
+def _parse_extinf(line: str) -> Optional[_ExtInf]:
+    match = _EXTINF.match(line)
+    if match is None:
+        return None
+    seconds = float(match.group(1))
+    display = match.group(2).strip()
+    artist, sep, title = display.partition(" - ")
+    if not sep or not artist.strip() or not title.strip():
+        # Display text that is not 'Artist - Title' cannot be split without
+        # guessing which half is which, so both stay empty (DL-287).
+        artist = title = ""
+    return _ExtInf(
+        seconds=f"{seconds:.3f}" if seconds > 0 else "",
+        artist=artist.strip(),
+        title=title.strip(),
+    )
+
+
+def _path_flavour(path_text: str):
+    """PureWindowsPath for a drive letter or a backslash, PurePosixPath
+    otherwise, so a playlist written on a Mac and one written on Windows
+    decode to the same folder parts on either machine (DL-288)."""
+    if _DRIVE.match(path_text) or "\\" in path_text:
+        return PureWindowsPath(path_text)
+    return PurePosixPath(path_text)
+
+
+def _path_string_record(path_text: str, extinf: Optional[_ExtInf]) -> EntryRecord:
+    """A record for a path this machine does not hold: file name and
+    folder parts from the path string, artist, title and duration from
+    its #EXTINF (DL-275, DL-288). The folder parts are encoded the way a
+    collection DIR is, so the path_suffix tiers compare them directly; the
+    volume stays empty because this path names no volume this collection
+    knows. source_path None marks it as not read from disk."""
+    pure = _path_flavour(path_text)
+    folder_parts = [part for part in pure.parent.parts if part != pure.anchor]
+    return EntryRecord(
+        entry=None,
+        artist=extinf.artist if extinf else "",
+        title=extinf.title if extinf else "",
+        audio_id="",
+        filesize="",
+        playtime_float=extinf.seconds if extinf else "",
+        bitrate="",
+        album="",
+        file_name=pure.name,
+        location=LocationParts(
+            volume="", volumeid="", dir_value=encode_traktor_dir("/".join(folder_parts)), file_name=pure.name
+        ),
+        source_path=None,
+    )
+
+
+def _resolve_playlist_path(path_text: str, playlist_dir: Path) -> Path:
+    pure = _path_flavour(path_text)
+    return Path(pure) if pure.is_absolute() else playlist_dir / Path(pure)
+
+
+def read_m3u(path: Path) -> InputRead:
+    """An .m3u or .m3u8 playlist, one Candidate per path line in order.
+
+    .m3u8 is UTF-8 by definition and decodes strictly; .m3u falls back to
+    cp1252 (DL-283). #EXTINF attaches to the next path line and every
+    other '#' line is ignored. A relative path resolves against the
+    playlist's own folder. A path that is a file on this machine is
+    indexed from disk and takes its artist, title and duration from the
+    file, ignoring #EXTINF; any other path becomes a path-string record.
+    A URL line is an unparseable Candidate (DL-287). line_number is the
+    path line's number and raw_text the path line.
+    """
+    data = _read_bytes(path)
+    if path.suffix.casefold() == ".m3u8":
+        text, encoding = _decode_strict(data, path), "utf-8-sig"
+    else:
+        text, encoding = _decode_with_fallback(data, path)
+
+    pending: Optional[_ExtInf] = None
+    # (line_number, raw_text, present file or None, path-string record or None)
+    entries: list[tuple[int, str, Optional[Path], Optional[EntryRecord]]] = []
+    for line_number, raw_line in enumerate(text.splitlines(), start=1):
+        stripped = raw_line.strip()
+        if not stripped:
+            continue
+        if stripped.startswith("#"):
+            extinf = _parse_extinf(stripped)
+            if extinf is not None:
+                pending = extinf
+            continue
+        extinf, pending = pending, None
+        if _URL.match(stripped):
+            entries.append((line_number, raw_line, None, None))
+            continue
+        target = _resolve_playlist_path(stripped, path.parent)
+        if target.is_file():
+            entries.append((line_number, raw_line, target, None))
+        else:
+            entries.append((line_number, raw_line, None, _path_string_record(stripped, extinf)))
+
+    # Present files are indexed in one call, so a stat failure names the
+    # file and refuses the whole read (DL-292).
+    present = iter(_index_or_refuse([target for _n, _r, target, _rec in entries if target is not None]))
+    candidates: list[Candidate] = []
+    for line_number, raw_line, target, record in entries:
+        if target is not None:
+            record = next(present)
+        if record is None:
+            candidates.append(Candidate(line_number, raw_line, "", "", None))
+        else:
+            candidates.append(_file_candidate(line_number, raw_line, record))
+    return InputRead(InputFormat.M3U, encoding, candidates)
+
+
 def read_input(path: Path) -> InputRead:

```

**Documentation:**

```diff
--- a/traktor_nml/playlistinput.py
+++ b/traktor_nml/playlistinput.py
@@ -193,12 +193,20 @@ _DRIVE = re.compile(r"^[A-Za-z]:")

 @dataclass(frozen=True)
 class _ExtInf:
+    """A parsed #EXTINF directive, waiting for the path line it
+    describes (DL-287)."""
+
     seconds: str  # "" when the directive gave no positive duration
     artist: str
     title: str


 def _parse_extinf(line: str) -> Optional[_ExtInf]:
+    """The duration and 'Artist - Title' display text of an #EXTINF line,
+    or None for any other directive. Seconds of zero or less give no
+    duration; display text splits on its first ' - ' (DL-287). Whole
+    seconds sit up to 1.0s under a collection's PLAYTIME_FLOAT, the edge
+    of the duration tolerance (R-001)."""
     match = _EXTINF.match(line)
     if match is None:
         return None
@@ -244,5 +252,7 @@ def _path_string_record(path_text: str, extinf: Optional[_ExtInf]) -> EntryRecord:
     knows. source_path None marks it as not read from disk."""
     pure = _path_flavour(path_text)
+    # The anchor ('C:\' or '/') names a drive or root, not a folder, so it
+    # is left out of the folder parts whichever flavour parsed it (DL-288).
     folder_parts = [part for part in pure.parent.parts if part != pure.anchor]
     return EntryRecord(
         entry=None,
@@ -264,5 +274,9 @@ def _path_string_record(path_text: str, extinf: Optional[_ExtInf]) -> EntryRecord:


 def _resolve_playlist_path(path_text: str, playlist_dir: Path) -> Path:
+    """The path a playlist line names on this machine: an absolute path
+    as written, a relative one joined onto the playlist's own folder
+    (DL-287). Whether a file exists there decides between indexing it
+    from disk and a path-string record."""
     pure = _path_flavour(path_text)
     return Path(pure) if pure.is_absolute() else playlist_dir / Path(pure)

```

> **Developer notes**: Adds the M3U reader to traktor_nml/playlistinput.py after read_folder, and
the milestone's tests. The shared decoder _decode_with_fallback is also used
by the CSV reader (CI-M-004-001).

**CC-M-003-002** (tests/test_playlistinput_m3u.py) - implements CI-M-003-002

**Code:**

```diff
--- /dev/null
+++ b/tests/test_playlistinput_m3u.py
@@ -0,0 +1,167 @@
+"""playlistinput's M3U reader: #EXTINF attachment, path flavours, URL
+lines, encodings, and the duration edge the matching tolerance sets.
+System interpreter, no nicegui."""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+import pytest
+
+from traktor_nml.model import EntryRecord, LocationParts
+from traktor_nml.playlistinput import InputFormat, InputReadError, _path_string_record, read_m3u
+from traktor_nml.tracklist import resolve_candidates
+
+
+def _write(path: Path, text: str, encoding: str = "utf-8") -> Path:
+    path.write_bytes(text.encode(encoding))
+    return path
+
+
+def test_extinf_attaches_to_next_path_line(tmp_path: Path) -> None:
+    """Duration and 'Artist - Title' fill the next path line's record;
+    a directive does not carry past its path line; -1 gives no duration;
+    display text with no ' - ' leaves artist and title empty.
+
+    The bare path directly follows a populated directive's path line, so
+    a directive carried forward shows as filled fields rather than as
+    empty ones indistinguishable from the correct result (DL-189).
+
+    Mutation: read_m3u assigns extinf = pending without resetting
+        pending to None, so /absent/Music/two.mp3 carries Alpha - One
+        and 215.000.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    playlist = _write(tmp_path / "set.m3u8", (
+        "#EXTM3U\n"
+        "#EXTINF:215,Alpha - One\n"
+        "/absent/Music/Alpha/one.mp3\n"
+        "/absent/Music/two.mp3\n"
+        "#EXTINF:-1,Just a name\n"
+        "/absent/Music/three.mp3\n"
+    ))
+    read = read_m3u(playlist)
+    records = [c.record for c in read.candidates]
+    assert [(r.artist, r.title, r.playtime_float) for r in records] == [
+        ("Alpha", "One", "215.000"), ("", "", ""), ("", "", ""),
+    ]
+    assert [c.line_number for c in read.candidates] == [3, 4, 6]
+
+
+def test_path_lines_relative_windows_posix_and_url(tmp_path: Path) -> None:
+    """A relative path present beside the playlist is indexed from disk;
+    an absent Windows path and an absent POSIX path become path-string
+    records; a URL line is unparseable.
+
+    Mutation: read_m3u skips its _URL check, so the https:// line
+        becomes a path-string record in place of None.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    (tmp_path / "Local").mkdir()
+    (tmp_path / "Local" / "here.mp3").write_bytes(b"\0" * 2048)
+    playlist = _write(tmp_path / "set.m3u8", (
+        "Local/here.mp3\n"
+        "Z:\\Music\\Techno\\gone.mp3\n"
+        "/Users/x/Music/Techno/gone.mp3\n"
+        "https://example.com/stream.mp3\n"
+    ))
+    candidates = read_m3u(playlist).candidates
+    assert candidates[0].record.source_path is not None
+    assert candidates[0].record.filesize == "2"
+    assert candidates[1].record.source_path is None
+    assert candidates[2].record.source_path is None
+    assert candidates[3].record is None
+
+
+def test_windows_and_posix_path_strings_decode_alike() -> None:
+    """The same folders written as a Windows path and as a POSIX path
+    give the same folder parts (DL-288).
+
+    Mutation: _path_flavour always returns PurePosixPath, so the Windows
+        path string keeps its backslashes and its dir_value differs from
+        the POSIX one.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    windows = _path_string_record("D:\\Sync\\Music\\Techno\\Artist\\track.mp3", None)
+    posix = _path_string_record("/Sync/Music/Techno/Artist/track.mp3", None)
+    assert windows.location.dir_value == posix.location.dir_value == "/:Sync/:Music/:Techno/:Artist/:"
+    assert windows.file_name == posix.file_name == "track.mp3"
+
+
+def _collection(dir_value: str, time: str = "215.9") -> EntryRecord:
+    return EntryRecord(
+        entry=None, artist="Alpha", title="One", audio_id="", filesize="8000", playtime_float=time,
+        bitrate="", album="", file_name="track.mp3",
+        location=LocationParts("D:", "D:", dir_value, "track.mp3"),
+    )
+
+
+def test_mac_path_absent_here_matches_by_path_suffix_3(tmp_path: Path) -> None:
+    """A Mac path that does not exist on this machine matches the
+    collection entry under D:/Sync/Music/Techno/Artist through its last
+    three folders, while a decoy with the same file name elsewhere does
+    not make it ambiguous.
+
+    Mutation: _path_string_record sets the location's dir_value to '',
+        so path_suffix_3 cannot fire and the decoy with the same file
+        name makes the outcome ambiguous.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    playlist = _write(tmp_path / "mac.m3u8", "/Users/x/Music/Techno/Artist/track.mp3\n")
+    candidate = read_m3u(playlist).candidates[0]
+    target = _collection("/:Sync/:Music/:Techno/:Artist/:")
+    decoy = _collection("/:Sync/:Other/:Place/:Else/:")
+    resolution = resolve_candidates([candidate], [target, decoy])[0]
+    assert resolution.outcome == "matched"
+    assert resolution.matched_record is target
+
+
+def test_extinf_truncation_matched_and_gap_refuted(tmp_path: Path) -> None:
+    """#EXTINF's integer seconds 0.9s under the collection's duration
+    still match; a 5s gap is refuted (R-001).
+
+    Mutation: _parse_extinf returns seconds='' for every directive, so
+        the 220.0s collection entry is not refuted by duration and the
+        second outcome is 'matched'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    playlist = _write(tmp_path / "t.m3u8", "#EXTINF:215,Alpha - One\n/nowhere/a/b/c/track.mp3\n")
+    candidate = read_m3u(playlist).candidates[0]
+    assert resolve_candidates([candidate], [_collection("/:x/:", "215.9")])[0].outcome == "matched"
+    assert resolve_candidates([candidate], [_collection("/:x/:", "220.0")])[0].outcome == "unmatched"
+
+
+def test_encodings(tmp_path: Path) -> None:
+    """A cp1252 .m3u reads and reports cp1252; the same bytes as .m3u8
+    refuse with tracklist_decode_error (DL-283).
+
+    Mutation: read_m3u decodes a .m3u8 through _decode_with_fallback, so
+        the cp1252 .m3u8 reads without raising InputReadError.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    body = "#EXTINF:100,Beyonc\u00e9 - Halo\n/nowhere/halo.mp3\n"
+    m3u = _write(tmp_path / "set.m3u", body, "cp1252")
+    read = read_m3u(m3u)
+    assert read.format is InputFormat.M3U
+    assert read.encoding == "cp1252"
+    assert read.candidates[0].record.artist == "Beyonc\u00e9"
+
+    m3u8 = _write(tmp_path / "set.m3u8", body, "cp1252")
+    with pytest.raises(InputReadError) as error:
+        read_m3u(m3u8)
+    assert error.value.code == f"tracklist_decode_error={m3u8.as_posix()}"
+
+
+def test_present_file_ignores_extinf(tmp_path: Path) -> None:
+    """A file present on disk takes artist, title and duration from the
+    file, not from its #EXTINF (DL-287).
+
+    Mutation: read_m3u fills a present file's empty artist, title and
+        playtime_float from its #EXTINF, so the record reads ('Wrong',
+        'Name', '300.000').
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    (tmp_path / "real.mp3").write_bytes(b"\0" * 1024)
+    playlist = _write(tmp_path / "s.m3u8", "#EXTINF:300,Wrong - Name\nreal.mp3\n")
+    record = read_m3u(playlist).candidates[0].record
+    assert (record.artist, record.title, record.playtime_float) == ("", "", "")

```

**Documentation:**

```diff
--- a/tests/test_playlistinput_m3u.py
+++ b/tests/test_playlistinput_m3u.py
@@ -21,2 +21,15 @@
 def test_extinf_attaches_to_next_path_line(tmp_path: Path) -> None:
+    """Duration and 'Artist - Title' fill the next path line's record;
+    a directive does not carry past its path line; -1 gives no duration;
+    display text with no ' - ' leaves artist and title empty.
+
+    The bare path directly follows a populated directive's path line, so
+    a directive carried forward shows as filled fields rather than as
+    empty ones indistinguishable from the correct result (DL-189).
+
+    Mutation: read_m3u assigns extinf = pending without resetting
+        pending to None, so /absent/Music/two.mp3 carries Alpha - One
+        and 215.000.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     playlist = _write(tmp_path / "set.m3u8", (
@@ -38,2 +51,10 @@
 def test_path_lines_relative_windows_posix_and_url(tmp_path: Path) -> None:
+    """A relative path present beside the playlist is indexed from disk;
+    an absent Windows path and an absent POSIX path become path-string
+    records; a URL line is unparseable.
+
+    Mutation: read_m3u skips its _URL check, so the https:// line
+        becomes a path-string record in place of None.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     (tmp_path / "Local").mkdir()
@@ -55,2 +76,10 @@
 def test_windows_and_posix_path_strings_decode_alike() -> None:
+    """The same folders written as a Windows path and as a POSIX path
+    give the same folder parts (DL-288).
+
+    Mutation: _path_flavour always returns PurePosixPath, so the Windows
+        path string keeps its backslashes and its dir_value differs from
+        the POSIX one.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     windows = _path_string_record("D:\\Sync\\Music\\Techno\\Artist\\track.mp3", None)
@@ -70,2 +99,12 @@
 def test_mac_path_absent_here_matches_by_path_suffix_3(tmp_path: Path) -> None:
+    """A Mac path that does not exist on this machine matches the
+    collection entry under D:/Sync/Music/Techno/Artist through its last
+    three folders, while a decoy with the same file name elsewhere does
+    not make it ambiguous.
+
+    Mutation: _path_string_record sets the location's dir_value to '',
+        so path_suffix_3 cannot fire and the decoy with the same file
+        name makes the outcome ambiguous.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     playlist = _write(tmp_path / "mac.m3u8", "/Users/x/Music/Techno/Artist/track.mp3\n")
@@ -80,2 +119,10 @@
 def test_extinf_truncation_matched_and_gap_refuted(tmp_path: Path) -> None:
+    """#EXTINF's integer seconds 0.9s under the collection's duration
+    still match; a 5s gap is refuted (R-001).
+
+    Mutation: _parse_extinf returns seconds='' for every directive, so
+        the 220.0s collection entry is not refuted by duration and the
+        second outcome is 'matched'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     playlist = _write(tmp_path / "t.m3u8", "#EXTINF:215,Alpha - One\n/nowhere/a/b/c/track.mp3\n")
@@ -87,2 +134,9 @@
 def test_encodings(tmp_path: Path) -> None:
+    """A cp1252 .m3u reads and reports cp1252; the same bytes as .m3u8
+    refuse with tracklist_decode_error (DL-283).
+
+    Mutation: read_m3u decodes a .m3u8 through _decode_with_fallback, so
+        the cp1252 .m3u8 reads without raising InputReadError.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     body = "#EXTINF:100,Beyonc\u00e9 - Halo\n/nowhere/halo.mp3\n"
@@ -101,2 +155,10 @@
 def test_present_file_ignores_extinf(tmp_path: Path) -> None:
+    """A file present on disk takes artist, title and duration from the
+    file, not from its #EXTINF (DL-287).
+
+    Mutation: read_m3u fills a present file's empty artist, title and
+        playtime_float from its #EXTINF, so the record reads ('Wrong',
+        'Name', '300.000').
+    Observed: the implementer records the verbatim assertion output here.
+    """
     (tmp_path / "real.mp3").write_bytes(b"\0" * 1024)

```


**CC-M-003-003** (tests/test_build_playlist_inputs.py) - implements CI-M-003-003

**Code:**

```diff
--- a/tests/test_build_playlist_inputs.py
+++ b/tests/test_build_playlist_inputs.py
@@ -134,0 +135,28 @@
+
+
+def test_cli_build_playlist_over_m3u_mixing_present_and_absent(tmp_path: Path) -> None:
+    """The CLI builds a playlist from an M3U whose first path is a file
+    on this machine and whose second exists only in the collection:
+    both entries are written, the absent one matched from its path
+    string (DL-275).
+
+    Mutation: read_m3u drops a path line whose file does not exist on
+        this machine, so only present.mp3 is written and stdout holds
+        entries_written=1.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    from tests.conftest import run_tool
+
+    music = tmp_path / "Music" / "Techno" / "Set"
+    music.mkdir(parents=True)
+    present = music / "present.mp3"
+    present.write_bytes(b"\0" * 4096)
+    absent = music / "absent.mp3"
+    (tmp_path / "base.nml").write_text(
+        _nml([_entry_for(present, size_kb="4"), _entry_for(absent)]), encoding="utf-8", newline=""
+    )
+    (tmp_path / "set.m3u").write_text(f"{present}\n/Volumes/Mac/Music/Techno/Set/absent.mp3\n", encoding="utf-8")
+    with patch("uuid.uuid4", return_value=_FIXED_UUID):
+        result = run_tool(["build-playlist", "base.nml", "set.m3u", "out.nml", "--name", "Set"], cwd=tmp_path)
+    assert result.exit_code == 0, result.stderr
+    assert "entries_written=2" in result.stdout

```

**Documentation:**

```diff
--- a/tests/test_build_playlist_inputs.py
+++ b/tests/test_build_playlist_inputs.py
@@ -137,2 +137,12 @@
 def test_cli_build_playlist_over_m3u_mixing_present_and_absent(tmp_path: Path) -> None:
+    """The CLI builds a playlist from an M3U whose first path is a file
+    on this machine and whose second exists only in the collection:
+    both entries are written, the absent one matched from its path
+    string (DL-275).
+
+    Mutation: read_m3u drops a path line whose file does not exist on
+        this machine, so only present.mp3 is written and stdout holds
+        entries_written=1.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     from tests.conftest import run_tool

```


### Milestone 4: CSV input and its template definition

**Files**: traktor_nml/playlistinput.py, tests/test_playlistinput_csv.py, tests/test_build_playlist_inputs.py

**Requirements**:

- CSV_COLUMNS drives csv_template_bytes() and header recognition
- Delimiter chosen from the header line (comma, then semicolon)
- Rows missing Artist or Title are unparseable; empty rows skipped; Duration parsed from seconds, m:ss, h:mm:ss
- utf-8-sig then cp1252 decoding reported as encoding

**Acceptance Criteria**:

- csv_template_bytes() parses to zero candidates and no error; mutation renaming one template header fails the round-trip guard with verbatim output
- Semicolon CSV from a comma-decimal Excel parses identically to its comma twin
- A CSV row whose File name matches a collection entry resolves at artist_title_file where artist/title alone is ambiguous
- line_number equals spreadsheet row number, including after a quoted multi-line cell

**Tests**:

- unit: header case and whitespace, unknown columns ignored, missing Title refused with csv_header_missing
- unit: duration forms and unparseable duration
- integration: CLI run over CSV prints input_format=csv and input_encoding before stats keys

#### Code Intent

- **CI-M-004-001** `traktor_nml/playlistinput.py::CSV_COLUMNS/csv_template_bytes/read_csv`: CSV_COLUMNS tuple with required flags; csv_template_bytes() returns BOM + header joined by commas + CRLF; read_csv decodes per the encoding rule, picks the delimiter from the first non-empty line, maps headers case-insensitively, reads rows with csv.reader tracking reader.line_num for the starting physical line, and returns Candidates whose records carry artist, title, album, playtime_float and file_name with empty location dir and source_path None (refs: DL-284, DL-285, DL-286, DL-283, DL-275)
- **CI-M-004-002** `tests/test_playlistinput_csv.py::test_template_*/test_headers_*/test_missing_*/test_semicolon_*/test_duration_forms/test_rows_*/test_cp1252_*/test_file_name_*`: Guards CSV_COLUMNS, csv_template_bytes, parse_duration and read_csv: template round-trip, header matching, csv_header_missing, semicolon delimiter, duration forms, row skipping and physical line numbers, cp1252 fallback reported, File name reaching artist_title_file; each guard's docstring names its mutation and the verbatim output it produced (refs: DL-284, DL-285, DL-286, DL-283, DL-275)
- **CI-M-004-003** `tests/test_build_playlist_inputs.py::test_cli_run_over_csv_*`: CLI run over a CSV prints input_format=csv and input_encoding before the stats keys (refs: DL-280)

#### Code Changes

**CC-M-004-001** (traktor_nml/playlistinput.py) - implements CI-M-004-001

**Code:**

```diff
--- a/traktor_nml/playlistinput.py
+++ b/traktor_nml/playlistinput.py
@@ -20,5 +20,7 @@
 from __future__ import annotations
 
+import csv
 import enum
+import io
 import re
 from dataclasses import dataclass
@@ -294,4 +296,135 @@ def read_m3u(path: Path) -> InputRead:
     return InputRead(InputFormat.M3U, encoding, candidates)
 
 
+@dataclass(frozen=True)
+class CsvColumn:
+    header: str
+    field: str  # the EntryRecord field the column fills
+    required: bool
+
+
+# The one definition of the CSV header: csv_template_bytes() writes it,
+# read_csv recognises it and the CLI's --help lists it, so a downloaded
+# template can never stop being uploadable (DL-284). Album, Duration and
+# File name are optional but let a row reach tiers stronger than
+# artist_title.
+CSV_COLUMNS: tuple[CsvColumn, ...] = (
+    CsvColumn("Artist", "artist", True),
+    CsvColumn("Title", "title", True),
+    CsvColumn("Album", "album", False),
+    CsvColumn("Duration", "playtime_float", False),
+    CsvColumn("File name", "file_name", False),
+)
+
+
+def csv_template_bytes() -> bytes:
+    """The header row alone, UTF-8 with a BOM so Excel opens it as UTF-8,
+    CRLF-terminated. No example row: one left in by accident is an
+    unmatched entry that refuses the run (DL-284)."""
+    header = ",".join(column.header for column in CSV_COLUMNS)
+    return ("\ufeff" + header + "\r\n").encode("utf-8")
+
+
+def _header_index(cells: list[str]) -> dict[str, int]:
+    """EntryRecord field -> column index, headers matched after strip and
+    casefold; unrecognised columns are ignored (DL-284)."""
+    by_header = {column.header.casefold(): column.field for column in CSV_COLUMNS}
+    index: dict[str, int] = {}
+    for position, cell in enumerate(cells):
+        field = by_header.get(cell.strip().casefold())
+        if field is not None and field not in index:
+            index[field] = position
+    return index
+
+
+def _choose_delimiter(header_line: str) -> str:
+    """Comma if the header splits into Artist and Title on commas, else
+    semicolon - what Excel writes in locales whose decimal mark is a comma
+    - else csv_header_missing (DL-285). Chosen from the header alone:
+    csv.Sniffer guesses from data rows and misreads titles holding
+    commas."""
+    required = {column.field for column in CSV_COLUMNS if column.required}
+    for delimiter in (",", ";"):
+        cells = next(csv.reader([header_line], delimiter=delimiter), [])
+        if required <= set(_header_index(cells)):
+            return delimiter
+    raise InputReadError("csv_header_missing")
+
+
+_DURATION = re.compile(r"^(?:(\d+):)?(?:(\d+):)?(\d+(?:\.\d+)?)$")
+
+
+def parse_duration(text: str) -> str:
+    """Seconds ('215', '215.4'), m:ss or h:mm:ss as a PLAYTIME_FLOAT
+    string, or '' when the cell is empty or unreadable - an unreadable
+    duration drops the evidence, not the row (DL-286)."""
+    match = _DURATION.match(text.strip())
+    if match is None:
+        return ""
+    first, second, seconds = match.groups()
+    hours, minutes = (first, second) if second is not None else (None, first)
+    total = float(seconds) + 60 * int(minutes or 0) + 3600 * int(hours or 0)
+    return f"{total:.3f}" if total > 0 else ""
+
+
+def _csv_record(cells: list[str], index: dict[str, int]) -> dict[str, str]:
+    def cell(field: str) -> str:
+        position = index.get(field)
+        return cells[position].strip() if position is not None and position < len(cells) else ""
+
+    return {column.field: cell(column.field) for column in CSV_COLUMNS}
+
+
+def read_csv(path: Path) -> InputRead:
+    """A CSV with CSV_COLUMNS' headers, one Candidate per non-empty row.
+
+    A row with an empty Artist or Title is unparseable; a row with every
+    cell empty is skipped. line_number is the physical line the row
+    starts on - the header is line 1 when it is the first line, so it is
+    the spreadsheet's row number, a quoted multi-line cell included - and
+    raw_text is that row's physical lines as read (DL-286).
+    """
+    text, encoding = _decode_with_fallback(_read_bytes(path), path)
+    # csv counts one line per "\n"; normalising first keeps its line_num
+    # and this list of physical lines in step.
+    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
+    physical = normalised.split("\n")
+    header_number = next((n for n, line in enumerate(physical, start=1) if line.strip()), None)
+    if header_number is None:
+        raise InputReadError("csv_header_missing")
+    delimiter = _choose_delimiter(physical[header_number - 1])
+
+    reader = csv.reader(io.StringIO("\n".join(physical[header_number - 1:])), delimiter=delimiter)
+    index = _header_index(next(reader))
+    candidates: list[Candidate] = []
+    previous_end = header_number
+    for cells in reader:
+        start = previous_end + 1
+        previous_end = header_number - 1 + reader.line_num
+        if not any(cell.strip() for cell in cells):
+            continue
+        raw_text = "\n".join(physical[start - 1:previous_end])
+        fields = _csv_record(cells, index)
+        if not fields["artist"] or not fields["title"]:
+            candidates.append(Candidate(start, raw_text, fields["artist"], fields["title"], None))
+            continue
+        record = EntryRecord(
+            entry=None,
+            artist=fields["artist"],
+            title=fields["title"],
+            audio_id="",
+            filesize="",
+            playtime_float=parse_duration(fields["playtime_float"]),
+            bitrate="",
+            album=fields["album"],
+            file_name=fields["file_name"],
+            # No folder: a CSV row names no path, so the path tiers stay
+            # silent and the location is never read as a volume.
+            location=LocationParts(volume="", volumeid="", dir_value="", file_name=fields["file_name"]),
+            source_path=None,
+        )
+        candidates.append(Candidate(start, raw_text, record.artist, record.title, record))
+    return InputRead(InputFormat.CSV, encoding, candidates)
+
+
 def read_input(path: Path) -> InputRead:

```

**Documentation:**

```diff
--- a/traktor_nml/playlistinput.py
+++ b/traktor_nml/playlistinput.py
@@ -298,6 +298,10 @@ def read_m3u(path: Path) -> InputRead:

 @dataclass(frozen=True)
 class CsvColumn:
+    """One CSV column: the header text the template writes and the
+    parser recognises, the EntryRecord field it fills, and whether a
+    file without it refuses with csv_header_missing (DL-284)."""
+
     header: str
     field: str  # the EntryRecord field the column fills
     required: bool
@@ -381,6 +385,10 @@ def parse_duration(text: str) -> str:


 def _csv_record(cells: list[str], index: dict[str, int]) -> dict[str, str]:
+    """EntryRecord field -> stripped cell text for every CSV_COLUMNS
+    field, "" for a column the header lacks or a row too short to reach
+    it, so a ragged row reads as missing optional cells rather than
+    raising."""
     def cell(field: str) -> str:
         position = index.get(field)
         return cells[position].strip() if position is not None and position < len(cells) else ""
@@ -404,5 +412,7 @@ def read_csv(path: Path) -> InputRead:
     if header_number is None:
         raise InputReadError("csv_header_missing")
+    # Comma or semicolon, decided by the header line alone (DL-285); the
+    # data rows are read with that one delimiter.
     delimiter = _choose_delimiter(physical[header_number - 1])

     reader = csv.reader(io.StringIO("\n".join(physical[header_number - 1:])), delimiter=delimiter)
@@ -413,4 +423,6 @@ def read_csv(path: Path) -> InputRead:
         start = previous_end + 1
         previous_end = header_number - 1 + reader.line_num
+        # A row of empty cells is a blank spreadsheet line, not an entry, so
+        # it is neither a candidate nor a report row (DL-286).
         if not any(cell.strip() for cell in cells):
             continue

```

> **Developer notes**: Adds the CSV column definition, the template bytes and the CSV reader to
traktor_nml/playlistinput.py after read_m3u, plus the milestone's tests.

**CC-M-004-002** (tests/test_playlistinput_csv.py) - implements CI-M-004-002

**Code:**

```diff
--- /dev/null
+++ b/tests/test_playlistinput_csv.py
@@ -0,0 +1,159 @@
+"""playlistinput's CSV reader and template. System interpreter, no nicegui."""
+
+from __future__ import annotations
+
+from pathlib import Path
+
+import pytest
+
+from traktor_nml.model import EntryRecord, LocationParts
+from traktor_nml.playlistinput import (
+    CSV_COLUMNS,
+    InputFormat,
+    InputReadError,
+    csv_template_bytes,
+    parse_duration,
+    read_csv,
+)
+from traktor_nml.tracklist import resolve_candidates
+
+
+def _write(tmp_path: Path, text: str, encoding: str = "utf-8", name: str = "list.csv") -> Path:
+    path = tmp_path / name
+    path.write_bytes(text.encode(encoding))
+    return path
+
+
+def test_template_round_trips_to_zero_candidates(tmp_path: Path) -> None:
+    """The template parses with no error to zero candidates, and its
+    header is CSV_COLUMNS in order (DL-284).
+
+    Mutation: csv_template_bytes writes 'Track' in place of the Title
+        column's header, so read_csv raises InputReadError
+        csv_header_missing on the template.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    path = tmp_path / "template.csv"
+    path.write_bytes(csv_template_bytes())
+    read = read_csv(path)
+    assert read.candidates == []
+    assert csv_template_bytes().startswith(b"\xef\xbb\xbf")
+    assert csv_template_bytes().endswith(b"\r\n")
+    assert csv_template_bytes().decode("utf-8-sig").strip() == ",".join(c.header for c in CSV_COLUMNS)
+
+
+def test_headers_case_whitespace_and_unknown_columns(tmp_path: Path) -> None:
+    """Headers match after strip and casefold, and an unknown column is
+    ignored.
+
+    Mutation: _header_index compares cell.strip() without casefold(), so
+        ' artist ' and 'TITLE' match no column and read_csv raises
+        csv_header_missing.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    path = _write(tmp_path, " artist ,Notes,TITLE\nA,ignore me,T\n")
+    candidate = read_csv(path).candidates[0]
+    assert (candidate.artist, candidate.title) == ("A", "T")
+
+
+def test_missing_title_header_refuses(tmp_path: Path) -> None:
+    """A header without Title refuses with csv_header_missing.
+
+    Mutation: _header_index returns the columns it found without
+        requiring Title, so read_csv reads 'Artist,Album' as unparseable
+        rows and raises nothing.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    with pytest.raises(InputReadError) as error:
+        read_csv(_write(tmp_path, "Artist,Album\nA,B\n"))
+    assert error.value.code == "csv_header_missing"
+
+
+def test_semicolon_csv_parses_like_its_comma_twin(tmp_path: Path) -> None:
+    """A semicolon file from a comma-decimal Excel reads identically to
+    the comma file, commas inside a title included (DL-285).
+
+    Mutation: _choose_delimiter always returns ',', so the semicolon
+        header is one unknown column and read_csv raises
+        csv_header_missing.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    comma = read_csv(_write(tmp_path, 'Artist,Title,Duration\nA,"One, Two",3:35\n', name="c.csv"))
+    semi = read_csv(_write(tmp_path, "Artist;Title;Duration\nA;One, Two;3:35\n", name="s.csv"))
+    assert [c.record for c in comma.candidates] == [c.record for c in semi.candidates]
+
+
+@pytest.mark.parametrize(
+    "text,expected",
+    [("215", "215.000"), ("215.4", "215.400"), ("3:35", "215.000"), ("1:02:03", "3723.000"),
+     ("", ""), ("abc", ""), ("3:xx", "")],
+)
+def test_duration_forms(text: str, expected: str) -> None:
+    """Seconds, m:ss and h:mm:ss convert; empty and unreadable cells give
+    '' (DL-286).
+
+    Mutation: parse_duration assigns hours, minutes = first, second for
+        two-part values as well as three-part ones, so '3:35' converts
+        to 12900.000 in place of 215.000.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    assert parse_duration(text) == expected
+
+
+def test_rows_empty_unparseable_and_line_numbers(tmp_path: Path) -> None:
+    """An all-empty row is skipped, a row missing Title is unparseable,
+    and line_number is the row's starting physical line even after a
+    quoted multi-line cell (DL-286).
+
+    Mutation: read_csv numbers each row by its position in the reader,
+        enumerate(reader, start=2), in place of the physical line it
+        starts on, so the multi-line cell shifts the later line numbers.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    text = 'Artist,Title\nA,"Line one\nline two"\n,\nB,\nC,Three\n'
+    candidates = read_csv(_write(tmp_path, text)).candidates
+    assert [c.line_number for c in candidates] == [2, 5, 6]
+    assert [c.record is None for c in candidates] == [False, True, False]
+    assert candidates[0].raw_text == 'A,"Line one\nline two"'
+
+
+def test_cp1252_csv_reports_its_encoding(tmp_path: Path) -> None:
+    """Bytes that are not UTF-8 decode as cp1252 and the read names that
+    codec (DL-283).
+
+    Mutation: _decode_with_fallback decodes utf-8-sig with
+        errors='replace', so the read reports 'utf-8-sig' in place of
+        'cp1252'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    read = read_csv(_write(tmp_path, "Artist,Title\nBeyonc\u00e9,Halo\n", "cp1252"))
+    assert read.format is InputFormat.CSV
+    assert read.encoding == "cp1252"
+    assert read.candidates[0].artist == "Beyonc\u00e9"
+
+
+def _collection(file_name: str) -> EntryRecord:
+    return EntryRecord(
+        entry=None, artist="A", title="T", audio_id="", filesize="", playtime_float="",
+        bitrate="", album="", file_name=file_name,
+        location=LocationParts("C:", "C:", "/:Music/:", file_name),
+    )
+
+
+def test_file_name_column_resolves_where_artist_title_is_ambiguous(tmp_path: Path) -> None:
+    """Two collection entries share artist and title; the File name
+    column resolves the row at artist_title_file, where the same row
+    without it is ambiguous.
+
+    Mutation: read_csv builds the EntryRecord with file_name='', so the
+        row with a File name column is ambiguous at artist_title like
+        the row without it.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    collection = [_collection("a.mp3"), _collection("b.mp3")]
+    with_file = read_csv(_write(tmp_path, "Artist,Title,File name\nA,T,b.mp3\n", name="f.csv")).candidates
+    without = read_csv(_write(tmp_path, "Artist,Title\nA,T\n", name="n.csv")).candidates
+    matched = resolve_candidates(with_file, collection)[0]
+    assert matched.outcome == "matched"
+    assert matched.matched_record.file_name == "b.mp3"
+    assert resolve_candidates(without, collection)[0].outcome == "ambiguous"

```

**Documentation:**

```diff
--- a/tests/test_playlistinput_csv.py
+++ b/tests/test_playlistinput_csv.py
@@ -27,2 +27,10 @@
 def test_template_round_trips_to_zero_candidates(tmp_path: Path) -> None:
+    """The template parses with no error to zero candidates, and its
+    header is CSV_COLUMNS in order (DL-284).
+
+    Mutation: csv_template_bytes writes 'Track' in place of the Title
+        column's header, so read_csv raises InputReadError
+        csv_header_missing on the template.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     path = tmp_path / "template.csv"
@@ -37,2 +45,10 @@
 def test_headers_case_whitespace_and_unknown_columns(tmp_path: Path) -> None:
+    """Headers match after strip and casefold, and an unknown column is
+    ignored.
+
+    Mutation: _header_index compares cell.strip() without casefold(), so
+        ' artist ' and 'TITLE' match no column and read_csv raises
+        csv_header_missing.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     path = _write(tmp_path, " artist ,Notes,TITLE\nA,ignore me,T\n")
@@ -43,2 +59,9 @@
 def test_missing_title_header_refuses(tmp_path: Path) -> None:
+    """A header without Title refuses with csv_header_missing.
+
+    Mutation: _header_index returns the columns it found without
+        requiring Title, so read_csv reads 'Artist,Album' as unparseable
+        rows and raises nothing.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     with pytest.raises(InputReadError) as error:
@@ -49,2 +72,10 @@
 def test_semicolon_csv_parses_like_its_comma_twin(tmp_path: Path) -> None:
+    """A semicolon file from a comma-decimal Excel reads identically to
+    the comma file, commas inside a title included (DL-285).
+
+    Mutation: _choose_delimiter always returns ',', so the semicolon
+        header is one unknown column and read_csv raises
+        csv_header_missing.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     comma = read_csv(_write(tmp_path, 'Artist,Title,Duration\nA,"One, Two",3:35\n', name="c.csv"))
@@ -60,2 +91,10 @@
 def test_duration_forms(text: str, expected: str) -> None:
+    """Seconds, m:ss and h:mm:ss convert; empty and unreadable cells give
+    '' (DL-286).
+
+    Mutation: parse_duration assigns hours, minutes = first, second for
+        two-part values as well as three-part ones, so '3:35' converts
+        to 12900.000 in place of 215.000.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     assert parse_duration(text) == expected
@@ -64,2 +103,11 @@
 def test_rows_empty_unparseable_and_line_numbers(tmp_path: Path) -> None:
+    """An all-empty row is skipped, a row missing Title is unparseable,
+    and line_number is the row's starting physical line even after a
+    quoted multi-line cell (DL-286).
+
+    Mutation: read_csv numbers each row by its position in the reader,
+        enumerate(reader, start=2), in place of the physical line it
+        starts on, so the multi-line cell shifts the later line numbers.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     text = 'Artist,Title\nA,"Line one\nline two"\n,\nB,\nC,Three\n'
@@ -72,2 +120,10 @@
 def test_cp1252_csv_reports_its_encoding(tmp_path: Path) -> None:
+    """Bytes that are not UTF-8 decode as cp1252 and the read names that
+    codec (DL-283).
+
+    Mutation: _decode_with_fallback decodes utf-8-sig with
+        errors='replace', so the read reports 'utf-8-sig' in place of
+        'cp1252'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     read = read_csv(_write(tmp_path, "Artist,Title\nBeyonc\u00e9,Halo\n", "cp1252"))
@@ -87,2 +143,11 @@
 def test_file_name_column_resolves_where_artist_title_is_ambiguous(tmp_path: Path) -> None:
+    """Two collection entries share artist and title; the File name
+    column resolves the row at artist_title_file, where the same row
+    without it is ambiguous.
+
+    Mutation: read_csv builds the EntryRecord with file_name='', so the
+        row with a File name column is ambiguous at artist_title like
+        the row without it.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     collection = [_collection("a.mp3"), _collection("b.mp3")]

```


**CC-M-004-003** (tests/test_build_playlist_inputs.py) - implements CI-M-004-003

**Code:**

```diff
--- a/tests/test_build_playlist_inputs.py
+++ b/tests/test_build_playlist_inputs.py
@@ -162,0 +163,19 @@
+
+
+def test_cli_run_over_csv_prints_format_and_encoding_first(tmp_path: Path) -> None:
+    """A CSV run prints input_format=csv and input_encoding before the
+    stats keys (DL-280). Passes once CI-M-005-001 lands the printing.
+
+    Mutation: _handle_build_playlist prints input_format and
+        input_encoding after the stats loop, so stdout's first line is
+        lines_read=1.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    from tests.conftest import run_tool
+
+    track = tmp_path / "Music" / "a.mp3"
+    (tmp_path / "base.nml").write_text(_nml([_entry_for(track, "A", "T")]), encoding="utf-8", newline="")
+    (tmp_path / "list.csv").write_text("Artist,Title\nA,T\n", encoding="utf-8")
+    result = run_tool(["build-playlist", "base.nml", "list.csv", "out.nml", "--name", "L"], cwd=tmp_path)
+    assert result.exit_code == 0, result.stderr
+    assert result.stdout.splitlines()[:3] == ["input_format=csv", "input_encoding=utf-8-sig", "lines_read=1"]

```

**Documentation:**

```diff
--- a/tests/test_build_playlist_inputs.py
+++ b/tests/test_build_playlist_inputs.py
@@ -165,2 +165,10 @@
 def test_cli_run_over_csv_prints_format_and_encoding_first(tmp_path: Path) -> None:
+    """A CSV run prints input_format=csv and input_encoding before the
+    stats keys (DL-280). Passes once CI-M-005-001 lands the printing.
+
+    Mutation: _handle_build_playlist prints input_format and
+        input_encoding after the stats loop, so stdout's first line is
+        lines_read=1.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     from tests.conftest import run_tool

```


### Milestone 5: CLI format override and reporting

**Files**: traktor_nml/commands/build_playlist_cmd.py, traktor_nml/playlistinput.py, tests/test_build_playlist.py, tests/test_cli_contract.py, traktor_nml/README.md

**Requirements**:

- --input-format {auto,text,csv,m3u,folder} overrides detect_format
- input_format and input_encoding printed before stats for non-text runs only
- --help lists CSV columns from CSV_COLUMNS
- path_collides checks unchanged; a folder input is accepted as the tracklist positional

**Acceptance Criteria**:

- Text corpus still passes byte-identically
- --input-format text on a .csv file parses it as text
- Mutation printing input_format for text runs fails the parity replay with verbatim output

**Tests**:

- integration: each format end to end through run_tool, including refusal codes

#### Code Intent

- **CI-M-005-001** `traktor_nml/commands/build_playlist_cmd.py::register/_handle_build_playlist`: register adds --input-format with choices and help naming CSV_COLUMNS; handler passes the override to read_input and prints input_format=/input_encoding= lines before stats keys when the format is not text (refs: DL-294, DL-280)
- **CI-M-005-002** `traktor_nml/playlistinput.py::read_input`: read_input(path, fmt=None) dispatches on fmt or detect_format to text, folder, m3u or csv readers; a folder format on a non-directory or a file format on a directory raises InputReadError('input_format_mismatch=<format>') (refs: DL-281, DL-294, DL-292)
- **CI-M-005-003** `traktor_nml/README.md`: Decision log entries for folder, M3U, CSV, encoding, index_files, CLI parity decisions, and the build-playlist usage section naming the accepted inputs (refs: DL-289, DL-287, DL-284, DL-294)

#### Code Changes

**CC-M-005-001** (traktor_nml/commands/build_playlist_cmd.py) - implements CI-M-005-001

**Code:**

```diff
--- a/traktor_nml/commands/build_playlist_cmd.py
+++ b/traktor_nml/commands/build_playlist_cmd.py
@@ -10,3 +10,3 @@
 from ..buildplaylist import UnresolvedRow, assemble_output
-from ..playlistinput import InputReadError, read_input
+from ..playlistinput import CSV_COLUMNS, InputFormat, InputReadError, read_input
 from ..rewrite import path_collides, read_and_parse_source, write_bytes_atomically, write_row_report
@@ -63,7 +63,9 @@ def _handle_build_playlist(args: argparse.Namespace) -> int:
     # Base first, then the input: the same order the refusals have always
     # been checked in, which the text corpus replays (DL-279).
+    # "auto" leaves detection to the suffix; any other value names the format.
+    fmt = None if args.input_format == "auto" else InputFormat(args.input_format)
     try:
-        input_read = read_input(args.tracklist)
+        input_read = read_input(args.tracklist, fmt)
     except InputReadError as exc:
         print(exc.code, file=sys.stderr)
         return 2
@@ -79,5 +81,11 @@ def _handle_build_playlist(args: argparse.Namespace) -> int:
         allow_unmatched=args.allow_unmatched,
     )
 
+    # Printed ahead of the stats and only for non-text input: a text run's
+    # stdout stays byte-identical to the corpus (DL-279, DL-280), and a
+    # cp1252 fallback is named where the operator reads the counts (DL-283).
+    if input_read.format is not InputFormat.TEXT:
+        print(f"input_format={input_read.format.value}")
+        print(f"input_encoding={input_read.encoding}")
     for key, value in result.stats.items():
         print(f"{key}={value}")
@@ -131,14 +139,27 @@ def _handle_build_playlist(args: argparse.Namespace) -> int:
 def register(subparsers, handlers: dict) -> None:
     """Register the build-playlist subparser. No --match-confidence option
-    is exposed: resolution always runs at a fixed MatchConfidence.LOOSE,
-    since a text-only track list leaves every stricter tier unreachable
-    (DL-032)."""
+    is exposed: resolution always runs at a fixed MatchConfidence.LOOSE for
+    every input format, which already admits every stricter tier a
+    file-derived candidate can reach (DL-032, DL-276)."""
+    csv_columns = ", ".join(
+        f"{column.header}{'' if column.required else ' (optional)'}" for column in CSV_COLUMNS
+    )
     parser = subparsers.add_parser(
         "build-playlist",
-        help="Build an NML playlist from an external track list matched against a base collection",
+        help="Build an NML playlist from a track list, CSV, M3U/M3U8 playlist or folder matched against a base collection",
     )
     parser.add_argument("base", type=Path)
-    parser.add_argument("tracklist", type=Path)
+    parser.add_argument(
+        "tracklist",
+        type=Path,
+        help="A plain-text 'Artist - Title' list, a .csv, an .m3u/.m3u8 playlist, or a folder whose own audio files are read in name order.",
+    )
     parser.add_argument("output", type=Path)
     parser.add_argument("--name", required=True)
+    parser.add_argument(
+        "--input-format",
+        choices=["auto", "text", "csv", "m3u", "folder"],
+        default="auto",
+        help=f"Read the input as this format instead of detecting it from the suffix. CSV columns: {csv_columns}.",
+    )
     parser.add_argument("--target-folder", default=None)
--- a/tests/test_build_playlist.py
+++ b/tests/test_build_playlist.py
@@ -687,0 +688,53 @@
+
+
+def test_each_input_format_end_to_end_with_refusal_codes(tmp_path: Path) -> None:
+    """text, csv, m3u and folder inputs each build through the CLI, and
+    each read refusal prints its one code with exit 2 (DL-292).
+
+    Mutation: _handle_build_playlist returns exit code 1 in place of 2
+        when read_input raises InputReadError, so the refusal cases fail
+        their exit_code == 2 assertion.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    base = tmp_path / "base.nml"
+    base.write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    (tmp_path / "t.txt").write_text("A - One\n", encoding="utf-8")
+    (tmp_path / "l.csv").write_text("Artist,Title\nA,One\n", encoding="utf-8")
+    (tmp_path / "p.m3u8").write_text("#EXTINF:1,A - One\n/elsewhere/one.mp3\n", encoding="utf-8")
+    for source in ("t.txt", "l.csv", "p.m3u8"):
+        result = run_tool(["build-playlist", "base.nml", source, f"{source}.nml", "--name", "L"], cwd=tmp_path)
+        assert result.exit_code == 0, (source, result.stderr)
+
+    empty = tmp_path / "empty"
+    empty.mkdir()
+    cases = [
+        (["empty"], "no_entries_resolved"),
+        (["missing.m3u"], "input_not_found=missing.m3u"),
+        (["t.txt", "--input-format", "folder"], "input_format_mismatch=folder"),
+    ]
+    (tmp_path / "noheader.csv").write_text("Name,Album\nx,y\n", encoding="utf-8")
+    cases.append((["noheader.csv"], "csv_header_missing"))
+    for extra, code in cases:
+        argv = ["build-playlist", "base.nml", extra[0], "out.nml", "--name", "L", *extra[1:]]
+        result = run_tool(argv, cwd=tmp_path)
+        assert result.exit_code == 2
+        assert code in result.stderr.splitlines()
+
+
+def test_input_format_text_reads_a_csv_as_text(tmp_path: Path) -> None:
+    """--input-format text on a .csv parses it line by line and prints no
+    input_format line (DL-280, DL-294).
+
+    Mutation: _handle_build_playlist calls read_input(path) without the
+        --input-format value, so list.csv reads as CSV, its 'A - One'
+        header has no Title column, and the run refuses
+        csv_header_missing with exit code 2.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    (tmp_path / "base.nml").write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
+    (tmp_path / "list.csv").write_text("A - One\n", encoding="utf-8")
+    result = run_tool(
+        ["build-playlist", "base.nml", "list.csv", "out.nml", "--name", "L", "--input-format", "text"], cwd=tmp_path
+    )
+    assert result.exit_code == 0, result.stderr
+    assert result.stdout.splitlines()[0] == "lines_read=1"
--- a/tests/test_cli_contract.py
+++ b/tests/test_cli_contract.py
@@ -167,0 +168,19 @@
+
+
+def test_build_playlist_help_lists_csv_columns_from_their_definition(tmp_path):
+    """--help names every CSV_COLUMNS header and the --input-format
+    choices, read from the definition rather than restated (DL-294).
+
+    Mutation: the --input-format argument's choices drop 'folder', so
+        --help prints {auto,text,csv,m3u} in place of
+        {auto,text,csv,m3u,folder}.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    from traktor_nml.playlistinput import CSV_COLUMNS
+
+    result = run_tool(["build-playlist", "--help"], cwd=tmp_path)
+    assert result.exit_code == 0
+    flat = " ".join(result.stdout.split())
+    for column in CSV_COLUMNS:
+        assert column.header in flat
+    assert "{auto,text,csv,m3u,folder}" in flat

```

**Documentation:**

```diff
--- a/traktor_nml/commands/build_playlist_cmd.py
+++ b/traktor_nml/commands/build_playlist_cmd.py
--- a/tests/test_build_playlist.py
+++ b/tests/test_build_playlist.py
@@ -690,2 +690,10 @@
 def test_each_input_format_end_to_end_with_refusal_codes(tmp_path: Path) -> None:
+    """text, csv, m3u and folder inputs each build through the CLI, and
+    each read refusal prints its one code with exit 2 (DL-292).
+
+    Mutation: _handle_build_playlist returns exit code 1 in place of 2
+        when read_input raises InputReadError, so the refusal cases fail
+        their exit_code == 2 assertion.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     base = tmp_path / "base.nml"
@@ -716,2 +724,11 @@
 def test_input_format_text_reads_a_csv_as_text(tmp_path: Path) -> None:
+    """--input-format text on a .csv parses it line by line and prints no
+    input_format line (DL-280, DL-294).
+
+    Mutation: _handle_build_playlist calls read_input(path) without the
+        --input-format value, so list.csv reads as CSV, its 'A - One'
+        header has no Title column, and the run refuses
+        csv_header_missing with exit code 2.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     (tmp_path / "base.nml").write_text(_nml(_entry("A", "One", "one.mp3"), 1, ""), encoding="utf-8", newline="")
--- a/tests/test_cli_contract.py
+++ b/tests/test_cli_contract.py
@@ -170,2 +170,10 @@
 def test_build_playlist_help_lists_csv_columns_from_their_definition(tmp_path):
+    """--help names every CSV_COLUMNS header and the --input-format
+    choices, read from the definition rather than restated (DL-294).
+
+    Mutation: the --input-format argument's choices drop 'folder', so
+        --help prints {auto,text,csv,m3u} in place of
+        {auto,text,csv,m3u,folder}.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     from traktor_nml.playlistinput import CSV_COLUMNS

```

> **Developer notes**: Parity note: a text run must print nothing new, so input_format and
input_encoding are printed only when the format is not text; the corpus
(M-001) is the guard. tests/test_cli_contract.py and tests/test_build_playlist.py
gain the end-to-end cases listed at the bottom.

**CC-M-005-002** (traktor_nml/playlistinput.py) - implements CI-M-005-002

**Code:**

```diff
--- a/traktor_nml/playlistinput.py
+++ b/traktor_nml/playlistinput.py
@@ -425,7 +425,27 @@ def read_csv(path: Path) -> InputRead:
     return InputRead(InputFormat.CSV, encoding, candidates)
 
 
-def read_input(path: Path) -> InputRead:
-    """Read path as a plain-text track list; a directory refuses with
-    input_not_found."""
-    return read_text(path)
+_READERS = {
+    InputFormat.TEXT: read_text,
+    InputFormat.CSV: read_csv,
+    InputFormat.M3U: read_m3u,
+    InputFormat.FOLDER: read_folder,
+}
+
+
+def read_input(path: Path, fmt: Optional[InputFormat] = None) -> InputRead:
+    """Read path as fmt, or as detect_format names it when fmt is None.
+
+    An explicit fmt overrides the suffix, so a mis-suffixed file is read
+    as what it holds (DL-294). fmt folder on a path that is not a
+    directory, or a file format on a directory, refuses with
+    input_format_mismatch=<format>. A path that does not exist refuses
+    with input_not_found whatever the format (DL-292).
+    """
+    if not path.exists():
+        raise InputReadError(f"input_not_found={path.as_posix()}")
+    if fmt is None:
+        fmt = detect_format(path)
+    if (fmt is InputFormat.FOLDER) != path.is_dir():
+        raise InputReadError(f"input_format_mismatch={fmt.value}")
+    return _READERS[fmt](path)
--- a/tests/test_playlistinput.py
+++ b/tests/test_playlistinput.py
@@ -93,0 +94,26 @@
+
+
+def test_read_input_dispatch_and_override(tmp_path: Path) -> None:
+    """A .csv read with fmt text is parsed as text; each detected format
+    reaches its own reader; a format that contradicts the path refuses
+    with input_format_mismatch (DL-292, DL-294).
+
+    Mutation: read_input ignores fmt and always calls detect_format, so
+        read_input(csv_file, InputFormat.TEXT) returns format
+        InputFormat.CSV.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    csv_file = tmp_path / "list.csv"
+    csv_file.write_text("Artist,Title\nA - One\n", encoding="utf-8")
+    as_text = read_input(csv_file, InputFormat.TEXT)
+    assert as_text.format is InputFormat.TEXT
+    assert [c.artist for c in as_text.candidates if c.record is not None] == ["A"]
+    assert read_input(csv_file).format is InputFormat.CSV
+    assert read_input(tmp_path).format is InputFormat.FOLDER
+
+    with pytest.raises(InputReadError) as folder_on_file:
+        read_input(csv_file, InputFormat.FOLDER)
+    assert folder_on_file.value.code == "input_format_mismatch=folder"
+    with pytest.raises(InputReadError) as csv_on_dir:
+        read_input(tmp_path, InputFormat.CSV)
+    assert csv_on_dir.value.code == "input_format_mismatch=csv"

```

**Documentation:**

```diff
--- a/traktor_nml/playlistinput.py
+++ b/traktor_nml/playlistinput.py
@@ -425,6 +425,8 @@ def read_csv(path: Path) -> InputRead:
     return InputRead(InputFormat.CSV, encoding, candidates)


+# Each reader owns its decoding: text and .m3u8 strict, .m3u and .csv with
+# the cp1252 fallback, a folder none (DL-282, DL-283).
 _READERS = {
     InputFormat.TEXT: read_text,
     InputFormat.CSV: read_csv,
--- a/tests/test_playlistinput.py
+++ b/tests/test_playlistinput.py
@@ -96,2 +96,11 @@
 def test_read_input_dispatch_and_override(tmp_path: Path) -> None:
+    """A .csv read with fmt text is parsed as text; each detected format
+    reaches its own reader; a format that contradicts the path refuses
+    with input_format_mismatch (DL-292, DL-294).
+
+    Mutation: read_input ignores fmt and always calls detect_format, so
+        read_input(csv_file, InputFormat.TEXT) returns format
+        InputFormat.CSV.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     csv_file = tmp_path / "list.csv"

```


**CC-M-005-003** (traktor_nml/README.md) - implements CI-M-005-003

**Code:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -46,0 +47,5 @@ Overview section: the build-playlist usage entry
+`build-playlist BASE INPUT OUTPUT --name NAME` reads INPUT as a plain-text
+`Artist - Title` list, a `.csv` with `Artist` and `Title` columns (and
+optional `Album`, `Duration`, `File name`), an `.m3u`/`.m3u8` playlist, or
+a folder whose own audio files form the playlist in name order;
+`--input-format` overrides detection from the suffix (DL-294).
@@ -92,3 +97,3 @@
-This file is the authority for the log's high-water mark, which is `DL-281`:
+This file is the authority for the log's high-water mark, which is `DL-294`:
 an entry numbered against anything else collides with an entry this file
 names, so the next plan numbers from there.
@@ -2412,1 +2417,79 @@ Design Decisions: after the DL-276 bullet
   `bare_name`, which collides on stem component files (DL-276).
+- Each input format fills every `EntryRecord` field its source carries: a
+  folder file or an M3U path present on this machine is indexed from disk
+  (size in KB, tags, duration, file name, folder parts, `source_path`); an
+  M3U path absent here keeps its file name, folder parts and `#EXTINF`
+  artist, title and duration; a CSV row keeps artist, title, album,
+  duration and file name. `record_keys` emits the size, file and path
+  tiers only for non-empty fields, so a record cut down to artist and
+  title reaches only `artist_title`, the tier text lists go ambiguous on
+  (DL-275).
+- A folder or M3U candidate resolves through `match_records` alone, with
+  no exact-location pre-pass. `match_records` marks a tier with several
+  survivors ambiguous and keeps descending, so a collection holding one
+  track at two locations resolves uniquely at `path_suffix_3`; a pre-pass
+  would need collection `VOLUME` naming and resolve nothing more (DL-277).
+- Any input file whose suffix is not `.csv`, `.m3u` or `.m3u8` reads as
+  plain text, decoded `utf-8-sig` strictly, refusing with
+  `tracklist_decode_error` (DL-282).
+- Decoding: plain text and `.m3u8` are `utf-8-sig` strict; `.m3u` and
+  `.csv` try `utf-8-sig` and fall back to `cp1252`. The codec used is
+  `InputRead.encoding`, printed by the CLI and shown by the screen, because
+  a `cp1252` fallback misreads another single-byte codepage without an
+  error (DL-283).
+- `playlistinput.CSV_COLUMNS` - `Artist`, `Title` (required), `Album`,
+  `Duration`, `File name` - is the one CSV header definition.
+  `csv_template_bytes()` is that header alone, UTF-8 with a BOM and CRLF,
+  with no example row, since a forgotten example row is an unmatched entry
+  that refuses the run. Headers match case-insensitively after strip,
+  unknown columns are ignored, and a file without `Artist` and `Title`
+  refuses with `csv_header_missing` (DL-284).
+- The CSV delimiter is read off the header line: comma when it yields both
+  `Artist` and `Title`, else semicolon, the separator Excel writes where
+  the decimal mark is a comma. `csv.Sniffer` guesses from data rows and
+  misreads titles holding commas (DL-285).
+- A CSV row with an empty `Artist` or `Title` is unparseable and a row with
+  every cell empty is skipped. `Duration` reads seconds, `m:ss` or
+  `h:mm:ss`; an unreadable duration is left empty rather than refusing the
+  row. `line_number` is the physical line the row starts on, the
+  spreadsheet's row number, and `raw_text` the row as read (DL-286).
+- In an M3U, `#EXTINF:<seconds>,<Artist - Title>` attaches to the next path
+  line and other `#` lines are ignored; seconds of zero or less give no
+  duration, and display text without ` - ` leaves artist and title empty.
+  A relative path resolves against the playlist's folder and a URL line is
+  unparseable. A path that is a file here is indexed from disk and takes
+  artist, title and duration from the file; `#EXTINF` fills only a
+  path-string record, because its integer seconds sit up to 1.0s from a
+  collection's `PLAYTIME_FLOAT`, the same-source tolerance's edge (DL-287).
+- A path-string record decodes its path with `PureWindowsPath` when it
+  holds a drive letter or a backslash and `PurePosixPath` otherwise, drops
+  the anchor, and encodes the folder parts with `model.encode_traktor_dir`
+  into a location with an empty volume, so a playlist written on a Mac
+  matches a Windows collection by its trailing folders (DL-288).
+- A folder input reads only that directory's own files with an audio
+  extension, ordered by the casefolded name split into digit and
+  non-digit runs with digit runs compared as integers, ties broken by the
+  plain name. A plain string sort puts `10 - ...` before `2 - ...`.
+  `line_number` is the 1-based position and `raw_text` the file name
+  (DL-289).
+- `diskscan.index_files(paths, cache=None)` indexes an explicit list: one
+  record per path in order, duplicates kept, no walk, built by the same
+  `_record_for_file` `index_scan_roots` uses. A failed `stat()` raises
+  `DiskReadError` naming the path instead of shortening the list;
+  unreadable tags give empty tag fields. With no cache, no cache file is
+  read or written, so build-playlist writes no side file (DL-290).
+- `index_scan_roots` shares only the per-file `EntryRecord` construction
+  with `index_files`; its records, stats, diagnostics and cache behaviour
+  are its own (DL-291).
+- An input that yields no candidates runs to `no_entries_resolved`. An
+  input that cannot be read refuses before assembly with one code:
+  `input_not_found=<path>`, `tracklist_decode_error=<path>`,
+  `csv_header_missing`, `input_read_error=<path>` for a folder or M3U file
+  that cannot be indexed, or `input_format_mismatch=<format>` when
+  `--input-format` contradicts whether the path is a directory (DL-292).
+- A folder or M3U file the collection does not hold is reported as
+  unmatched; build-playlist never adds an `ENTRY` (DL-293).
+- The CLI keeps its positional `tracklist` argument for every format,
+  directories included, and `--input-format {auto,text,csv,m3u,folder}`
+  overrides suffix detection. No subcommand writes the CSV template;
+  `build-playlist --help` lists the columns from `CSV_COLUMNS` (DL-294).

```

**Documentation:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md

```

> **Developer notes**: traktor_nml/README.md (LF): the high-water mark moves to DL-294, the
Overview's build-playlist usage sentence names the accepted inputs, and the
decision bullets follow the DL-276 bullet CI-M-001-008 added.

### Milestone 6: Build-playlist artboard for multi-format input

**Files**: design/build-playlist/Specs.dc.html

**Requirements**:

- Input card draws 'Choose file...' and 'Choose folder...', the chosen path, and the detected format label
- A CSV note lists Artist and Title as required and Album, Duration, File name as optional, beside a 'Download CSV template' control
- Report card titled 'Unresolved entries' with #, Entry and Kind columns; footer sentence uses entry wording and names format and encoding
- Form card draws two separate controls in place of the single target-folder text input: 'Output folder' with a 'Choose folder...' button and the chosen path (placeholder naming the base collection's folder when none is chosen), and 'Playlist folder' as a chooser showing a 'Collection root' default, collection folder paths, and one disabled same-named folder

**Acceptance Criteria**:

- Artboard renders at 1280x900 with no document scroll
- Every string the screen shows appears on the artboard
- No artboard control is labelled 'Target folder'; the output-folder and playlist-folder controls use the artboard's existing btn and lbl rules

**Tests**:

- manual: artboard opened in the design canvas and compared against the surface list

#### Code Intent

- **CI-M-006-001** `design/build-playlist/Specs.dc.html`: Input card, CSV guidance note with template control, and entries report drawn with the card, lbl, note and btn rules the artboard already defines; the form card's output-folder chooser (button plus path) and playlist-folder chooser (Collection root default, folder paths, one disabled duplicate-name option) replace the target-folder text input The playlist-folder chooser is enabled only while Full collection is on; with it off the chooser is disabled at 'Collection root' with the note 'Playlist folder applies only with Full collection on. Off, the file holds this one playlist at its root.' and no target_folder is passed, because the isolation pass keeps only the new playlist under the root (DL-297). Full collection is drawn ON with the chooser enabled; the disabled state with its note is drawn in the right column. (refs: DL-295, DL-296, DL-297)

#### Code Changes

**CC-M-006-001** (design/build-playlist/Specs.dc.html) - implements CI-M-006-001

**Code:**

```diff
--- a/design/build-playlist/Specs.dc.html
+++ b/design/build-playlist/Specs.dc.html
@@ -61,6 +61,14 @@
 .kind.unmatched{color:#E07A4C;background:#2B1D14;border:1px solid #5A3A24}
 .kind.ambiguous{color:#F5D96B;background:#1F1D14;border:1px solid #5A4E2A}
 .kind.unparseable{color:#97A0A7;background:#1B1D20;border:1px solid #3C4248}
+.fmt{font:600 11px/1 'IBM Plex Mono',monospace;letter-spacing:.06em;text-transform:uppercase;color:#8FCFF2;background:#12222B;border:1px solid #2F5A72;border-radius:4px;padding:3px 6px;white-space:nowrap;flex:none}
+.chooser{position:relative;flex:1;min-width:0}
+.chooser .field{justify-content:space-between}
+.menu{position:absolute;left:0;right:0;top:40px;z-index:2;background:#17191C;border:1px solid #3C4248;border-radius:6px;padding:4px;display:flex;flex-direction:column;gap:1px;box-shadow:0 8px 24px rgba(0,0,0,.45)}
+.menu span{font:400 12.5px/1 'IBM Plex Mono',monospace;padding:8px 9px;border-radius:4px;color:#E8EBED}
+.menu span.on{background:#22262A}
+.menu span.off{color:#5A6167}
+.field.off{background:#15171A;border-color:#2A2E32;cursor:not-allowed}
   </style>
 </helmet>
 <div class="app">
@@ -92,46 +100,70 @@
       <section class="card">
         <div class="card-h"><h2 class="card-t">Build a playlist from a track list</h2><span class="lbl">Reads your collection, writes a new file</span></div>
         <div class="card-b">
-          <p class="dim" style="margin:0;font-size:12.5px;line-height:1.55">Match a plain-text "Artist - Title" list against a collection and write the matches as a new NML playlist. This is a separate job from repairing a broken playlist: nothing here reads or changes an existing playlist's own entries.</p>
+          <p class="dim" style="margin:0;font-size:12.5px;line-height:1.55">Match a track list, CSV, M3U playlist or folder of audio files against a collection and write the matches as a new NML playlist. Nothing here reads or changes an existing playlist's own entries.</p>
 
           <div class="lblrow">
             <span class="lbl">Base collection</span>
             <div class="row">
               <span class="field">
                 <svg class="ico" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="#8E979E" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 1.8h5.2L13 6.1v8.1H3.5z"/><path d="M8.6 1.9v4.3h4.3"/></svg>
                 <span class="mono">D:\Traktor\collection.nml</span>
               </span>
               <button class="btn sm">Choose file…</button>
             </div>
           </div>
 
           <div class="lblrow">
-            <span class="lbl">Track list</span>
+            <span class="lbl">Input</span>
             <div class="row">
               <span class="field">
                 <svg class="ico" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="#8E979E" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true"><path d="M3.5 1.8h5.2L13 6.1v8.1H3.5z"/><path d="M8.6 1.9v4.3h4.3"/></svg>
-                <span class="mono">C:\Users\marcus\Desktop\warehouse-set.txt</span>
+                <span class="mono">C:\Users\marcus\Desktop\warehouse-set.csv</span>
               </span>
+              <span class="fmt">CSV</span>
               <button class="btn sm">Choose file…</button>
+              <button class="btn sm">Choose folder…</button>
             </div>
-            <p class="faint" style="margin:0;font-size:11.5px">One "Artist - Title" per line. 1,238 lines read.</p>
+            <p class="faint" style="margin:0;font-size:11.5px">A text file with one "Artist - Title" per line, a CSV, an M3U or M3U8 playlist, or a folder whose audio files are read in name order.</p>
           </div>
 
-          <div class="row" style="gap:14px">
-            <div class="lblrow" style="flex:1">
-              <span class="lbl">Playlist name</span>
-              <span class="field"><span class="mono">Warehouse set — Aug 2026</span></span>
-            </div>
-            <div class="lblrow" style="flex:1">
-              <span class="lbl">Target folder <span class="faint" style="text-transform:none;letter-spacing:0;font-weight:400">(optional)</span></span>
-              <span class="field empty"><span class="mono">Root of the collection</span></span>
-            </div>
-          </div>
+          <div class="note">
+            <span><strong>CSV columns.</strong> Artist and Title are required. Album, Duration and File name are optional and help a row match more strictly.</span>
+            <button class="btn sm" style="margin-left:auto;flex:none">Download CSV template</button>
+          </div>
+
+          <div class="lblrow">
+            <span class="lbl">Playlist name</span>
+            <span class="field"><span class="mono">Warehouse set — Aug 2026</span></span>
+          </div>
+
+          <div class="row" style="gap:14px;align-items:flex-start">
+            <div class="lblrow" style="flex:1;min-width:0">
+              <span class="lbl">Output folder</span>
+              <div class="row">
+                <span class="field empty"><span class="mono">D:\Traktor (the base collection's folder)</span></span>
+                <button class="btn sm">Choose folder…</button>
+              </div>
+            </div>
+            <div class="lblrow" style="flex:1;min-width:0">
+              <span class="lbl">Playlist folder</span>
+              <div class="chooser">
+                <span class="field"><span class="mono">Sets\2026</span><span class="faint" aria-hidden="true">&#9662;</span></span>
+                <div class="menu" role="listbox" aria-label="Playlist folder">
+                  <span>Collection root</span>
+                  <span>Sets</span>
+                  <span class="on">Sets\2026</span>
+                  <span class="off" aria-disabled="true">Archive\Warmup (name also used elsewhere)</span>
+                  <span class="off" aria-disabled="true">Sets\Warmup (name also used elsewhere)</span>
+                </div>
+              </div>
+            </div>
+          </div>
 
           <div class="opt">
             <span class="sw on" role="img" aria-label="On"><i></i></span>
             <span class="opt-b">
               <span class="opt-t">Allow unmatched lines</span>
-              <span class="opt-d">Write the playlist even if some lines could not be matched. Off, a run with any unmatched or ambiguous line aborts and writes nothing.</span>
+              <span class="opt-d">Write the playlist even if some entries could not be matched. Off, a run with any unmatched or ambiguous entry aborts and writes nothing.</span>
             </span>
           </div>
@@ -163,4 +195,4 @@
           <div class="opt">
-            <span class="sw" role="img" aria-label="Off"><i></i></span>
+            <span class="sw on" role="img" aria-label="On"><i></i></span>
             <span class="opt-b">
               <span class="opt-t">Full collection</span>
@@ -174,15 +206,14 @@
       <section class="card" style="flex:1;min-height:0;display:flex;flex-direction:column">
-        <div class="card-h"><h2 class="card-t">Unresolved lines</h2><span class="lbl">4 of 1,238</span></div>
+        <div class="card-h"><h2 class="card-t">Unresolved entries</h2><span class="lbl">3 of 1,238</span></div>
         <div class="card-b" style="overflow:auto">
           <table class="rep">
-            <thead><tr><th style="width:64px">Line</th><th>Text</th><th style="width:120px">Reason</th></tr></thead>
+            <thead><tr><th style="width:64px">#</th><th>Entry</th><th style="width:120px">Kind</th></tr></thead>
             <tbody>
               <tr><td class="mono dim">214</td><td class="mono">Boards of Canadaa - Dayvan Cowboy</td><td><span class="kind unmatched">Unmatched</span></td></tr>
               <tr><td class="mono dim">507</td><td class="mono">Recondite - Levo</td><td><span class="kind ambiguous">Ambiguous</span></td></tr>
-              <tr><td class="mono dim">812</td><td class="mono">(blank line)</td><td><span class="kind unparseable">Unparseable</span></td></tr>
-              <tr><td class="mono dim">1190</td><td class="mono">Not an artist title line at all</td><td><span class="kind unparseable">Unparseable</span></td></tr>
+              <tr><td class="mono dim">1190</td><td class="mono">,Levo,Recondite</td><td><span class="kind unparseable">Unparseable</span></td></tr>
             </tbody>
           </table>
-          <p class="faint" style="margin:8px 0 0;font-size:11.5px">This report is read-only in this first version. Fixing a line means editing the track list file and choosing it again — there is no accept, reject or pick control here yet.</p>
+          <p class="faint" style="margin:8px 0 0;font-size:11.5px">This report is read-only. Fixing an entry means editing the input and choosing it again.</p>
         </div>
       </section>
@@ -196,3 +227,3 @@
           <ul style="margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:8px">
-            <li style="display:flex;gap:9px;font-size:12px;color:#A5ADB4;line-height:1.5"><span style="width:5px;height:5px;border-radius:50%;background:#5A6167;flex:none;margin-top:6px"></span><span>Each line is matched against the base collection the same way a disk scan matches a file — by artist and title only, since a text line carries no path, size or time to match on more strictly.</span></li>
+            <li style="display:flex;gap:9px;font-size:12px;color:#A5ADB4;line-height:1.5"><span style="width:5px;height:5px;border-radius:50%;background:#5A6167;flex:none;margin-top:6px"></span><span>Each entry is matched against the base collection the same way a disk scan matches a file. A text line carries only artist and title; a folder, an M3U path or a CSV file name also carries a path, size or time, which lets it match more strictly. A file the collection does not hold is reported, never added.</span></li>
             <li style="display:flex;gap:9px;font-size:12px;color:#A5ADB4;line-height:1.5"><span style="width:5px;height:5px;border-radius:50%;background:#5A6167;flex:none;margin-top:6px"></span><span>The base collection is read, never modified. A brand-new file is written at the path you choose next.</span></li>
@@ -204,5 +235,11 @@
       <div class="note info">
         <svg class="ico" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="#7FC4E8" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><circle cx="8" cy="8" r="6.2"/><path d="M8 7.3v4"/><path d="M8 4.9h.01"/></svg>
-        <span><strong>The output path is not typed directly.</strong> It is the playlist name plus the target folder (or the collection's own folder, when target folder is left empty) — the same two fields already on this form.</span>
+        <span><strong>Two different folders.</strong> The output folder is where the new .nml file is written on disk, named after the playlist. The playlist folder is where the playlist sits inside the collection's own playlist tree. A folder whose name another folder also uses cannot be chosen.</span>
       </div>
+
+      <div class="lblrow" aria-label="Playlist folder with Full collection off">
+        <span class="lbl">Playlist folder</span>
+        <span class="field empty off" aria-disabled="true"><span class="mono">Collection root</span><span class="faint" aria-hidden="true">&#9662;</span></span>
+        <p class="faint" style="margin:0;font-size:11.5px">Playlist folder applies only with Full collection on. Off, the file holds this one playlist at its root.</p>
+      </div>
     </div>
@@ -218,5 +255,5 @@
   <footer class="ft">
     <p class="ft-note">
       <svg class="ico" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="#8E979E" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="1.5"/><path d="M5.5 7V5a2.5 2.5 0 015 0v2"/></svg>
-      Nothing is written until you press Write. The base collection is never modified.
+      Not written: 3 entries did not resolve and Allow unmatched is off. Read as CSV, cp1252.
     </p>

```

**Documentation:**

```diff
--- a/design/build-playlist/Specs.dc.html
+++ b/design/build-playlist/Specs.dc.html

```

> **Developer notes**: design/build-playlist/Specs.dc.html. Every new element uses rules the sheet
already defines (card, lbl, lblrow, row, field, btn sm, note, faint, dim,
mono, table.rep, kind); three small additions to the <style> block give the
format tag, the closed chooser's caret and the open option list. The
button-fill change landing before this plan may have restyled .btn; keep
whatever .btn/.btn-pri rules the file holds then and add only the rules
below. After editing, open the artboard at 1280x900 and confirm no document
scroll (scrollHeight 900); if the left column overflows, shorten the
report's sample rows rather than dropping a surface.

The main drawing shows Full collection ON, the only state in which the
playlist-folder chooser is enabled (DL-297: with it off the isolation pass
writes the playlist at the root, so the choice would change nothing). The
disabled state is drawn once more in the right column, under the
two-folders note, so every string the screen shows appears here.

### Milestone 7: Build-playlist screen: inputs, CSV template, output and playlist folders

**Files**: traktor_nml/gui/app.py, traktor_nml/gui/file_picker.py, traktor_nml/gui/buildplaylist_view.py, traktor_nml/gui/theme.py, tests/test_gui_buildplaylist_view.py, tests/test_gui_file_picker_save.py, tests/test_build_playlist_byte_identity.py, docs/2026-09-16-build-playlist-inputs-browser-record.md, tests/test_docs_browser_record_structure.py, docs/CLAUDE.md, traktor_nml/gui/README.md, traktor_nml/playlists.py, tests/test_playlists_folder_choices.py, tests/test_gui_buildplaylist_output_path.py, traktor_nml/README.md

**Requirements**:

- Screen matches the artboard: file and folder choosers, format label, CSV note and template control, entries report
- Native mode writes csv_template_bytes() through pick_save_path and write_bytes_atomically; served mode uses ui.download with the same bytes
- FormInputs.input_path replaces tracklist_path; form_errors and run_summary use entry wording through wording.plural and name format and encoding
- GUI and CLI output bytes identical for csv, m3u and folder inputs
- Served-page record with per-surface verdicts and structural verdicts; digest registered
- The 'Target folder (optional)' input is removed; an output-folder chooser (pick_file_or_folder directories_only=True) sets where the .nml is written, defaulting to the base collection's directory, and a playlist-folder chooser filled from playlists.playlist_folder_choices on the parsed base sets target_folder, None for 'Collection root'
- FormInputs carries output_dir and playlist_folder and no shared target_folder; _derive_build_playlist_output_path(base_path, output_dir, name) never reads the playlist folder

**Acceptance Criteria**:

- test_build_playlist_byte_identity.py covers text, csv, m3u and folder
- Mutation of csv template control to ui.download in native mode fails the native-path guard with verbatim output
- test_gui_wording.py, test_gui_view_boundary.py, test_gui_line_endings.py pass
- Record's digest test passes
- Choosing output folder X and playlist folder F writes X/<name>.nml whose playlist sits under FOLDER F, byte-identical to the CLI run with output X/<name>.nml and --target-folder F
- Mutation passing playlist_folder into _derive_build_playlist_output_path fails the output-path guard with verbatim output; mutation passing output_dir as target_folder fails the byte-identity case
- playlist_folder_choices on a base with two FOLDERs named 'Sets' marks both non-unique; mutation dropping the uniqueness check fails its guard with verbatim output

**Tests**:

- unit: pick_save_path normalises str and tuple dialog results and None on cancel
- unit: run_summary for each format, singular and plural entries
- integration: GUI vs CLI bytes per format
- browser record: served page walked for file, folder and template download
- unit: playlist_folder_choices paths, tree order, root excluded, duplicate-name flag, base with no PLAYLISTS
- unit: output path with and without an output folder, independent of playlist folder
- integration: GUI vs CLI bytes with output folder and --target-folder set

#### Code Intent

- **CI-M-007-001** `traktor_nml/gui/file_picker.py::pick_save_path`: pick_save_path(window, *, save_filename, start_dir=None) awaits create_file_dialog(webview.FileDialog.SAVE, save_filename=...), returning Path from a str or first element of a sequence, None on cancel (refs: DL-295)
- **CI-M-007-002** `traktor_nml/gui/app.py::_build_build_playlist_page/_run_build_playlist`: Page composes the artboard's input card with 'Choose file...' and 'Choose folder...' (pick_file_or_folder with directories_only True for folder), shows detect_format's label, the CSV columns from CSV_COLUMNS, and 'Download CSV template' writing through pick_save_path in native mode or ui.download otherwise; report card titled 'Unresolved entries'; CRLF preserved; the target-folder ui.input is removed; an 'Output folder' 'Choose folder...' button calls pick_file_or_folder(directories_only=True) and displays the path; a 'Playlist folder' ui.select is refilled from playlist_folder_choices each time a base is chosen (parsed through read_and_parse_source, duplicate-name options disabled, 'Collection root' maps to None); _derive_build_playlist_output_path(base_path, output_dir, name) returns (Path(output_dir) if output_dir else base_path.parent) / f'{name}.nml' and _run_build_playlist passes inputs.playlist_folder or None as target_folder; buttons take the page's existing control classes The playlist-folder chooser is enabled only while Full collection is on; with it off the chooser is disabled at 'Collection root' with the note 'Playlist folder applies only with Full collection on. Off, the file holds this one playlist at its root.' and no target_folder is passed, because the isolation pass keeps only the new playlist under the root (DL-297). _sync_playlist_folder enables/disables the select and shows the note on the Full collection switch's change and on page build; _current_inputs routes the selection through effective_playlist_folder. (refs: DL-295, DL-281, DL-297)
- **CI-M-007-003** `traktor_nml/gui/buildplaylist_view.py::FormInputs/form_errors/run_summary/format_label`: FormInputs.input_path; form_errors says 'Choose an input.'; run_summary uses plural(n, 'entry', 'entries') and appends format and encoding read from the result for non-text runs; format_label maps InputFormat to the artboard's label; FormInputs replaces target_folder with output_dir (empty for the base's directory) and playlist_folder (empty for the collection root) The playlist-folder chooser is enabled only while Full collection is on; with it off the chooser is disabled at 'Collection root' with the note 'Playlist folder applies only with Full collection on. Off, the file holds this one playlist at its root.' and no target_folder is passed, because the isolation pass keeps only the new playlist under the root (DL-297). effective_playlist_folder(full_collection, selected) returns '' when full_collection is off; PLAYLIST_FOLDER_NEEDS_FULL_COLLECTION holds the note. (refs: DL-296, DL-280, DL-297)
- **CI-M-007-004** `traktor_nml/gui/theme.py`: Rules for the CSV note and the template control, taken from the artboard (refs: DL-295)
- **CI-M-007-005** `docs/2026-09-16-build-playlist-inputs-browser-record.md`: Served-page record: how the run was taken, a verdict row per surface, structural verdicts against Specs.dc.html, including verdict rows for the output-folder chooser and the playlist-folder chooser The playlist-folder chooser is enabled only while Full collection is on; with it off the chooser is disabled at 'Collection root' with the note 'Playlist folder applies only with Full collection on. Off, the file holds this one playlist at its root.' and no target_folder is passed, because the isolation pass keeps only the new playlist under the root (DL-297). Verdict rows cover the chooser disabled with its note when Full collection is off, enabled when on, and the output-folder chooser enabled in both. (refs: DL-295, DL-297)
- **CI-M-007-006** `traktor_nml/playlists.py::playlist_folder_choices`: playlist_folder_choices(root) -> list[PlaylistFolderChoice(path, name, unique)]: walks PLAYLISTS top-down like playlist_path_pairs, one entry per FOLDER node below the root in tree order, path the backslash-joined ancestor names plus its own, unique False when another FOLDER under the root shares its NAME (the scope _find_target_subnodes searches); empty list when PLAYLISTS or the root SUBNODES is absent; nicegui-free (refs: DL-297)
- **CI-M-007-007** `tests/test_playlists_folder_choices.py`: Unit tests for playlist_folder_choices: nested paths in tree order, root excluded, playlists not listed, duplicate NAME flagged on both nodes, missing PLAYLISTS gives []; fail-first docstrings with verbatim output (refs: DL-297)
- **CI-M-007-008** `tests/test_gui_buildplaylist_output_path.py`: Tests _derive_build_playlist_output_path with and without output_dir and proves it ignores playlist_folder; a byte-identity case runs _run_build_playlist and the CLI with output folder and --target-folder set and compares output bytes; fail-first docstrings (refs: DL-297, DL-281)
- **CI-M-007-009** `traktor_nml/gui/README.md`: The build-playlist screen section describes the output-folder and playlist-folder controls and how each maps to the CLI's output positional and --target-folder The playlist-folder chooser is enabled only while Full collection is on; with it off the chooser is disabled at 'Collection root' with the note 'Playlist folder applies only with Full collection on. Off, the file holds this one playlist at its root.' and no target_folder is passed, because the isolation pass keeps only the new playlist under the root (DL-297). (refs: DL-297)
- **CI-M-007-010** `traktor_nml/README.md`: Decision log entry DL-297 for the separation of output folder and playlist folder, stating it supersedes DL-272's no-output-control statement The playlist-folder chooser is enabled only while Full collection is on; with it off the chooser is disabled at 'Collection root' with the note 'Playlist folder applies only with Full collection on. Off, the file holds this one playlist at its root.' and no target_folder is passed, because the isolation pass keeps only the new playlist under the root (DL-297). (refs: DL-297)

#### Code Changes

**CC-M-007-001** (traktor_nml/gui/file_picker.py) - implements CI-M-007-001

**Code:**

```diff
--- a/traktor_nml/gui/file_picker.py
+++ b/traktor_nml/gui/file_picker.py
@@ -77,4 +77,27 @@ async def pick_folder(window, *, start_dir: Optional[Path] = None) -> Optional[Path]:
     return Path(result[0])
 
 
+async def pick_save_path(window, *, save_filename: str, start_dir: Optional[Path] = None) -> Optional[Path]:
+    """A destination file path chosen through pywebview's native SAVE
+    dialog, or None when the operator cancels.
+
+    Native mode only: pywebview blocks browser downloads by default, so
+    ui.download cannot deliver a file inside the native window (DL-295).
+    pywebview has returned the SAVE result as a plain string in some
+    versions and as a one-element sequence in others; both are accepted
+    so a pywebview upgrade cannot silently turn a chosen path into a
+    cancel."""
+    result = await window.create_file_dialog(
+        webview.FileDialog.SAVE,
+        directory=str(start_dir) if start_dir is not None else "",
+        save_filename=save_filename,
+    )
+    if not result:
+        return None
+    if isinstance(result, str):
+        return Path(result)
+    first = result[0]
+    return Path(first) if first else None
+
+
 class LocalFilePicker(ui.dialog):
--- /dev/null
+++ b/tests/test_gui_file_picker_save.py
@@ -0,0 +1,79 @@
+"""pick_save_path's normalisation of pywebview's SAVE dialog result.
+
+file_picker.py imports nicegui and webview, which the system interpreter
+lacks; this module installs the stand-ins
+tests/test_build_playlist_byte_identity.py uses and removes them in a
+finally so they never leak into another test.
+"""
+
+from __future__ import annotations
+
+import asyncio
+import importlib
+import sys
+from pathlib import Path
+
+from tests.test_build_playlist_byte_identity import _install_nicegui_stub, _uninstall
+
+
+class _StubWindow:
+    def __init__(self, result) -> None:
+        self.result = result
+        self.calls: list[tuple] = []
+
+    async def create_file_dialog(self, dialog_type, **kwargs):
+        self.calls.append((dialog_type, kwargs))
+        return self.result
+
+
+def _pick(result):
+    _uninstall()
+    _install_nicegui_stub()
+    try:
+        file_picker = importlib.import_module("traktor_nml.gui.file_picker")
+        window = _StubWindow(result)
+        path = asyncio.run(file_picker.pick_save_path(window, save_filename="playlist-template.csv"))
+        dialog_type = window.calls[0][0]
+        expected_type = sys.modules["webview"].FileDialog.SAVE
+        return path, window.calls[0][1], dialog_type is expected_type
+    finally:
+        _uninstall()
+
+
+def test_pick_save_path_accepts_a_string() -> None:
+    """A str result is the chosen path, asked for through the SAVE
+    dialog with the template's file name.
+
+    Mutation: pick_save_path returns Path(result[0]) for every non-empty
+        result, so the str result 'C:/out/t.csv' becomes Path('C').
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    path, kwargs, is_save = _pick("C:/out/t.csv")
+    assert path == Path("C:/out/t.csv")
+    assert kwargs["save_filename"] == "playlist-template.csv"
+    assert is_save
+
+
+def test_pick_save_path_accepts_a_sequence() -> None:
+    """A one-element sequence result is the chosen path: the other shape
+    pywebview returns from a SAVE dialog (R-005).
+
+    Mutation: pick_save_path returns Path(result) when result is a str
+        and None for any other shape, so the one-element tuple reads as
+        cancel.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    path, _kwargs, _is_save = _pick(("C:/out/t.csv",))
+    assert path == Path("C:/out/t.csv")
+
+
+def test_pick_save_path_cancel_is_none() -> None:
+    """None, an empty string and an empty sequence all mean cancel.
+
+    Mutation: pick_save_path treats only None as cancel, so the empty
+        string returns Path('') in place of None.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    for cancelled in (None, "", (), [""]):
+        path, _kwargs, _is_save = _pick(cancelled)
+        assert path is None

```

**Documentation:**

```diff
--- a/traktor_nml/gui/file_picker.py
+++ b/traktor_nml/gui/file_picker.py
--- a/tests/test_gui_file_picker_save.py
+++ b/tests/test_gui_file_picker_save.py
@@ -43,2 +43,9 @@
 def test_pick_save_path_accepts_a_string() -> None:
+    """A str result is the chosen path, asked for through the SAVE
+    dialog with the template's file name.
+
+    Mutation: pick_save_path returns Path(result[0]) for every non-empty
+        result, so the str result 'C:/out/t.csv' becomes Path('C').
+    Observed: the implementer records the verbatim assertion output here.
+    """
     path, kwargs, is_save = _pick("C:/out/t.csv")
@@ -50,2 +57,10 @@
 def test_pick_save_path_accepts_a_sequence() -> None:
+    """A one-element sequence result is the chosen path: the other shape
+    pywebview returns from a SAVE dialog (R-005).
+
+    Mutation: pick_save_path returns Path(result) when result is a str
+        and None for any other shape, so the one-element tuple reads as
+        cancel.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     path, _kwargs, _is_save = _pick(("C:/out/t.csv",))
@@ -55,2 +70,8 @@
 def test_pick_save_path_cancel_is_none() -> None:
+    """None, an empty string and an empty sequence all mean cancel.
+
+    Mutation: pick_save_path treats only None as cancel, so the empty
+        string returns Path('') in place of None.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     for cancelled in (None, "", (), [""]):

```


**CC-M-007-002** (traktor_nml/gui/app.py) - implements CI-M-007-002

**Code:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -49,3 +49,4 @@ imports
 from .. import buildplaylist
 from .. import playlistinput
+from ..playlists import playlist_folder_choices
 from .. import reconnect_run
@@ -77,1 +78,1 @@ imports
-from .file_picker import pick_file_or_folder
+from .file_picker import native_window, pick_file_or_folder, pick_save_path
@@ -1646,0 +1648,25 @@ before def _derive_build_playlist_output_path
+CSV_TEMPLATE_FILENAME = "playlist-template.csv"
+
+
+async def _deliver_csv_template() -> None:
+    """Hand the operator csv_template_bytes(). Served over HTTP the
+    browser saves it through ui.download. In the native window pywebview
+    blocks browser downloads by default, so a SAVE dialog asks for the
+    path and the bytes are written atomically here (DL-295). Module-level
+    so a test can stub native_window, pick_save_path and ui.download."""
+    data = playlistinput.csv_template_bytes()
+    window = native_window()
+    if window is None:
+        ui.download(data, CSV_TEMPLATE_FILENAME)
+        return
+    path = await pick_save_path(window, save_filename=CSV_TEMPLATE_FILENAME)
+    if path is None:
+        return
+    try:
+        await run.io_bound(write_bytes_atomically, path, data)
+    except OSError as exc:
+        ui.notify(f"output_write_error={exc}", type="negative")
+        return
+    ui.notify(f"Written to {path}")
+
+
@@ -1646,59 +1672,65 @@ def _run_build_playlist
-def _derive_build_playlist_output_path(base_path: Path, name: str, target_folder: str) -> Path:
-    """The build-playlist write destination: the playlist name as the
-    file's stem, in the base collection's own directory, or in a
-    subdirectory named by target_folder when one is given. No separate
-    output-path control exists on the form (DL-272): this is the only
-    place a build-playlist output path is computed, and both
-    path_collides and the atomic write below consume its return value."""
-    directory = base_path.parent
-    if target_folder:
-        directory = directory / target_folder
+def _derive_build_playlist_output_path(base_path: Path, output_dir: str, name: str) -> Path:
+    """The build-playlist write destination: <output folder>/<name>.nml,
+    or the base collection's own directory when no output folder is
+    chosen - the GUI counterpart of the CLI's positional output path.
+    It takes no playlist folder: that names a place in the collection's
+    playlist tree, not on disk, and a FOLDER NAME joined onto a disk path
+    would place the file in a directory that need not exist (DL-297). This is
+    the only place a build-playlist output path is computed; path_collides
+    and the atomic write both consume its return value."""
+    directory = Path(output_dir) if output_dir else base_path.parent
     return directory / f"{name}.nml"
 
 
-def _run_build_playlist(inputs: FormInputs) -> buildplaylist.BuildPlaylistResult:
+def _run_build_playlist(
+    inputs: FormInputs,
+) -> tuple[buildplaylist.BuildPlaylistResult, Optional[playlistinput.InputRead]]:
     """The build-playlist write path's whole sequence: collision
     refusal, input read, assemble, the optional isolation pass, atomic
     write - the same order build_playlist_cmd.py's own handler calls
     them in, so neither this screen's behaviour nor its written bytes
     diverge from the CLI's (DL-262). Called under run.io_bound, never
-    on the event loop directly."""
+    on the event loop directly. Returns the InputRead beside the result,
+    None when the run refused before reading, so the summary can name the
+    format and codec (DL-296)."""
     base_path = Path(inputs.base_path)
-    tracklist_path = Path(inputs.tracklist_path)
+    input_path = Path(inputs.input_path)
     output_path = _derive_build_playlist_output_path(
-        base_path, inputs.name, inputs.target_folder
+        base_path, inputs.output_dir, inputs.name
     )
 
-    if path_collides(output_path, base_path, tracklist_path):
+    if path_collides(output_path, base_path, input_path):
         return buildplaylist.BuildPlaylistResult(
             output=None, stats={}, unresolved_rows=[],
             errors=["output_must_differ_from_input"],
-        )
+        ), None
 
     base_result = read_and_parse_source(base_path)
     if base_result.error is not None:
         return buildplaylist.BuildPlaylistResult(
             output=None, stats={}, unresolved_rows=[], errors=[base_result.error],
-        )
+        ), None
     base_bytes, base_root = base_result.source_bytes, base_result.root
 
     # playlistinput.read_input is the one reader both surfaces call, so a
     # refusal code here is the string the CLI prints (DL-281).
     try:
-        input_read = playlistinput.read_input(tracklist_path)
+        input_read = playlistinput.read_input(input_path)
     except playlistinput.InputReadError as exc:
         return buildplaylist.BuildPlaylistResult(
             output=None, stats={}, unresolved_rows=[],
             errors=[exc.code],
-        )
+        ), None
 
     result = buildplaylist.assemble_output(
         base_bytes.decode("utf-8"), base_root, input_read.candidates, inputs.name,
-        target_folder=inputs.target_folder or None,
+        # The playlist folder is the CLI's --target-folder: a FOLDER NAME in
+        # the collection, None for the root. It never touches output_path.
+        target_folder=inputs.playlist_folder or None,
         allow_unmatched=inputs.allow_unmatched,
     )
     if result.output is None:
-        return result
+        return result, input_read
 
     output = result.output
     if not inputs.full_collection:
@@ -1714,7 +1746,7 @@ def _run_build_playlist
             return buildplaylist.BuildPlaylistResult(
                 output=None, stats=result.stats, unresolved_rows=result.unresolved_rows,
                 errors=isolated.errors,
-            )
+            ), input_read
         output = isolated.output
 
     try:
@@ -1723,5 +1755,5 @@ def _run_build_playlist
         return buildplaylist.BuildPlaylistResult(
             output=None, stats=result.stats, unresolved_rows=result.unresolved_rows,
             errors=[f"output_write_error={exc}"],
-        )
-    return result
+        ), input_read
+    return result, input_read
@@ -1776,76 +1808,185 @@ def build_playlist_page (inside _build_build_playlist_page)
         chrome = _page_chrome("/build-playlist")
 
         base_holder: dict = {"path": None}
-        tracklist_holder: dict = {"path": None}
+        input_holder: dict = {"path": None}
+        output_dir_holder: dict = {"path": None}
 
         with chrome.middle:
             with ui.column().classes("gap-4 wizard-content-width"):
                 with ui.element("section").classes("wizard-card wizard-content-width"):
                     with ui.element("div").classes("wizard-card-head"):
                         ui.label("Build a playlist from a track list").classes(
                             "wizard-card-title"
                         )
                     with ui.element("div").classes("wizard-card-body"):
                         ui.label(
-                            'Match a plain-text "Artist - Title" list against a '
-                            "collection and write the matches as a new NML playlist."
+                            "Match a track list, CSV, M3U playlist or folder of audio "
+                            "files against a collection and write the matches as a new "
+                            "NML playlist. Nothing here reads or changes an existing "
+                            "playlist's own entries."
                         )
 
                         base_display = ui.label("No collection selected").classes(
                             "font-mono wizard-body-15 wizard-subtle-1"
                         )
 
                         async def choose_base() -> None:
                             path = await pick_file_or_folder(directories_only=False)
                             if path is not None:
                                 base_holder["path"] = path
                                 base_display.set_text(str(path))
+                                _refill_playlist_folders(path)
+                                _show_output_dir()
                                 _refresh_write_button()
 
                         ui.button(
-                            "Choose collection file...", on_click=choose_base, color=None
+                            "Choose file...", on_click=choose_base, color=None
                         ).classes("wizard-control wizard-label")
 
-                        tracklist_display = ui.label("No track list selected").classes(
-                            "font-mono wizard-body-15 wizard-subtle-1"
-                        )
-
-                        async def choose_tracklist() -> None:
-                            path = await pick_file_or_folder(directories_only=False)
-                            if path is not None:
-                                tracklist_holder["path"] = path
-                                tracklist_display.set_text(str(path))
-                                _refresh_write_button()
-
-                        ui.button(
-                            "Choose track list...", on_click=choose_tracklist, color=None
-                        ).classes("wizard-control wizard-label")
+                        ui.label("Input").classes("wizard-label")
+                        with ui.row().classes("buildplaylist-input-row"):
+                            input_display = ui.label("No input selected").classes(
+                                "font-mono wizard-body-15 wizard-subtle-1"
+                            )
+                            format_tag = ui.label("").classes("buildplaylist-format-tag")
+                            format_tag.set_visibility(False)
+
+                            async def choose_input(directories_only: bool) -> None:
+                                path = await pick_file_or_folder(directories_only=directories_only)
+                                if path is None:
+                                    return
+                                input_holder["path"] = path
+                                input_display.set_text(str(path))
+                                # The tag shows what read_input will read the
+                                # path as, before any run (DL-295).
+                                format_tag.set_text(
+                                    buildplaylist_view.format_label(playlistinput.detect_format(path))
+                                )
+                                format_tag.set_visibility(True)
+                                _refresh_write_button()
+
+                            ui.button(
+                                "Choose file...", on_click=lambda: choose_input(False), color=None
+                            ).classes("wizard-control wizard-label")
+                            ui.button(
+                                "Choose folder...", on_click=lambda: choose_input(True), color=None
+                            ).classes("wizard-control wizard-label")
+                        ui.label(
+                            'A text file with one "Artist - Title" per line, a CSV, an M3U '
+                            "or M3U8 playlist, or a folder whose audio files are read in "
+                            "name order."
+                        ).classes("wizard-subtle-1")
+
+                        with ui.element("div").classes("wizard-callout"):
+                            ui.label(
+                                "CSV columns. " + buildplaylist_view.csv_columns_note()
+                            )
+
+                            ui.button(
+                                "Download CSV template", on_click=_deliver_csv_template, color=None
+                            ).classes("wizard-control wizard-label buildplaylist-template-control")
 
                         name_input = ui.input(
                             "Playlist name", on_change=lambda _e: _refresh_write_button()
                         ).classes("w-full")
-                        target_folder_input = ui.input("Target folder (optional)").classes(
-                            "w-full"
-                        )
+
+                        with ui.row().classes("buildplaylist-folder-row"):
+                            with ui.column().classes("buildplaylist-folder-col"):
+                                ui.label("Output folder").classes("wizard-label")
+                                output_dir_display = ui.label("").classes(
+                                    "font-mono wizard-body-15 wizard-subtle-1"
+                                )
+
+                                async def choose_output_dir() -> None:
+                                    path = await pick_file_or_folder(directories_only=True)
+                                    if path is not None:
+                                        output_dir_holder["path"] = path
+                                        _show_output_dir()
+
+                                ui.button(
+                                    "Choose folder...", on_click=choose_output_dir, color=None
+                                ).classes("wizard-control wizard-label")
+                            with ui.column().classes("buildplaylist-folder-col"):
+                                playlist_folder_select = ui.select(
+                                    {"": buildplaylist_view.COLLECTION_ROOT_LABEL},
+                                    value="",
+                                    label="Playlist folder",
+                                ).classes("w-full")
+                                # ui.select has no per-option disable; Quasar's
+                                # option-disable predicate greys out the
+                                # shared-name folders, whose keys start with NUL (DL-297).
+                                playlist_folder_select.props(
+                                    ':option-disable="opt => String(opt.value).charCodeAt(0) === 0"'
+                                )
+                                playlist_folder_note = ui.label(
+                                    buildplaylist_view.PLAYLIST_FOLDER_NEEDS_FULL_COLLECTION
+                                ).classes("wizard-subtle-1")
+
                         allow_unmatched_switch = ui.switch("Allow unmatched lines")
-                        full_collection_switch = ui.switch("Full collection")
+                        full_collection_switch = ui.switch(
+                            "Full collection", on_change=lambda _e: _sync_playlist_folder()
+                        )
 
                 with ui.element("section").classes(
                     "wizard-card wizard-content-width"
                 ) as report_section:
                     with ui.element("div").classes("wizard-card-head"):
-                        ui.label("Unresolved lines").classes("wizard-card-title")
+                        ui.label("Unresolved entries").classes("wizard-card-title")
                     with ui.element("div").classes("wizard-card-body"):
                         report_table = ui.column().classes("gap-1")
                 report_section.set_visibility(False)
 
+        def _show_output_dir() -> None:
+            # The placeholder names the folder the file goes to when none is
+            # chosen, so the default is visible rather than implied.
+            if output_dir_holder["path"] is not None:
+                output_dir_display.set_text(str(output_dir_holder["path"]))
+            elif base_holder["path"] is not None:
+                output_dir_display.set_text(f"{base_holder['path'].parent} (the base collection's folder)")
+            else:
+                output_dir_display.set_text("The base collection's folder")
+
+        def _sync_playlist_folder() -> None:
+            # Full collection off: split.build_output keeps only the new
+            # playlist under the root, so the chooser is disabled, reset to
+            # Collection root, and the note says why (DL-297). The output
+            # folder chooser applies either way and is left alone.
+            full = bool(full_collection_switch.value)
+            playlist_folder_select.set_enabled(full)
+            playlist_folder_note.set_visibility(not full)
+            if not full:
+                playlist_folder_select.set_value("")
+
+        def _refill_playlist_folders(base_path: Path) -> None:
+            """Replace the chooser's options with the chosen base's FOLDERs.
+            A base that fails to parse leaves only Collection root; the
+            run itself reports the parse error."""
+            parsed = read_and_parse_source(base_path)
+            choices = [] if parsed.error is not None else playlist_folder_choices(parsed.root)
+            options = buildplaylist_view.playlist_folder_options(choices)
+            # A disabled option still needs its own key, and its NAME is not
+            # unique; a NUL-prefixed label is a key no FOLDER NAME can equal.
+            playlist_folder_select.set_options(
+                {(o.value if o.enabled else "\0" + o.label): o.label for o in options},
+                value="",
+            )
+
         def _current_inputs() -> FormInputs:
             return FormInputs(
                 base_path=str(base_holder["path"] or ""),
-                tracklist_path=str(tracklist_holder["path"] or ""),
+                input_path=str(input_holder["path"] or ""),
                 name=name_input.value or "",
-                target_folder=target_folder_input.value or "",
+                output_dir=str(output_dir_holder["path"] or ""),
+                playlist_folder=_selected_playlist_folder(),
                 allow_unmatched=bool(allow_unmatched_switch.value),
                 full_collection=bool(full_collection_switch.value),
             )
 
+        def _selected_playlist_folder() -> str:
+            value = playlist_folder_select.value or ""
+            # A disabled option's key starts with NUL and is never a NAME.
+            selected = "" if value.startswith("\0") else value
+            return buildplaylist_view.effective_playlist_folder(
+                bool(full_collection_switch.value), selected
+            )
+
@@ -1972,2 +2113,8 @@ async def write_playlist
-            result = await run.io_bound(_run_build_playlist, inputs)
-            chrome.footer_note.set_text(buildplaylist_view.run_summary(result))
+            result, input_read = await run.io_bound(_run_build_playlist, inputs)
+            chrome.footer_note.set_text(
+                buildplaylist_view.run_summary(
+                    result,
+                    input_read.format if input_read is not None else None,
+                    input_read.encoding if input_read is not None else "",
+                )
+            )
@@ -1996,1 +2143,3 @@ after the footer_actions block
         _refresh_write_button()
+        _show_output_dir()
+        _sync_playlist_folder()

```

**Documentation:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -1890,6 +1890,8 @@ def build_playlist_page (inside _build_build_playlist_page)
                                 "CSV columns. " + buildplaylist_view.csv_columns_note()
                             )

+                            # One control in both modes; _deliver_csv_template
+                            # chooses ui.download or the SAVE dialog (DL-295).
                             ui.button(
                                 "Download CSV template", on_click=_deliver_csv_template, color=None
                             ).classes("wizard-control wizard-label buildplaylist-template-control")
@@ -1940,6 +1942,9 @@ def build_playlist_page (inside _build_build_playlist_page)
                 playlist_folder_select.set_value("")

         def _selected_playlist_folder() -> str:
+            """The playlist folder the run passes as target_folder: the
+            chooser's NAME, "" for Collection root or a disabled key, and
+            "" whenever Full collection is off (DL-297)."""
             value = playlist_folder_select.value or ""
             # A disabled option's key starts with NUL and is never a NAME.
             selected = "" if value.startswith("\0") else value
@@ -2113,4 +2118,6 @@ async def write_playlist
             result, input_read = await run.io_bound(_run_build_playlist, inputs)
+            # The summary names the format and codec the run read, from the
+            # InputRead the run returned (DL-296).
             chrome.footer_note.set_text(
                 buildplaylist_view.run_summary(
                     result,

```

> **Developer notes**: INTENT, not a pinned patch. An app-wide change filling buttons with the
action blue (#56B4E9) lands in app.py and theme.py before this plan runs, so
the classes on the buttons below (wizard-control, wizard-control-primary,
color=None) are whatever that change leaves the page's existing buttons
carrying: give every new button the class set the page's existing
secondary buttons carry at that time, and do not re-add or remove colour
classes here. Anchor by content (function names, label strings), not line
numbers. app.py is 100% CRLF: open and write it with newline='' and give
every added line CRLF; tests/test_gui_line_endings.py is the check.

What changes, in order:
1. Imports: playlistinput (M-001 already added it), pick_save_path, and
   playlists.playlist_folder_choices.
2. _derive_build_playlist_output_path(base_path, output_dir, name): disk
   folder only; never reads the playlist folder.
3. _run_build_playlist: output path from output_dir; target_folder from
   playlist_folder; returns (result, input_read) so the summary can name
   format and encoding.
4. _build_build_playlist_page: input card (file + folder chooser, format
   tag, CSV note + template control), playlist name, output-folder
   chooser, playlist-folder select refilled on base choice, report card
   "Unresolved entries".

Also update tests/test_build_playlist_byte_identity.py (listed in this
milestone): FormInputs(input_path=..., output_dir="", playlist_folder="",
...); `gui_result, _read = app._run_build_playlist(inputs)`;
`app._derive_build_playlist_output_path(base, "", "MyList")`; and add
csv, m3u and folder cases that write the same base and run the CLI and the
GUI over a .csv, an .m3u8 and a folder, asserting equal output bytes. Add
test_native_template_goes_through_the_save_dialog to that file: with the
nicegui stub installed, patch app.native_window to return a stub window,
app.pick_save_path to an AsyncMock returning tmp_path/"t.csv", app.run.io_bound
to an async function calling its argument, and app.ui.download to a
MagicMock; asyncio.run(app._deliver_csv_template()); assert t.csv holds
csv_template_bytes() and ui.download was not called. Prove it fails first by
mutating _deliver_csv_template to call ui.download in both branches, and
paste the verbatim output into its docstring.

**CC-M-007-003** (traktor_nml/gui/buildplaylist_view.py) - implements CI-M-007-003

**Code:**

```diff
--- a/traktor_nml/gui/buildplaylist_view.py
+++ b/traktor_nml/gui/buildplaylist_view.py
@@ -22,23 +22,30 @@
 from __future__ import annotations
 
 from dataclasses import dataclass
 from typing import Optional
 
 from ..buildplaylist import BuildPlaylistResult
+from ..playlistinput import CSV_COLUMNS, InputFormat
+from ..playlists import PlaylistFolderChoice
 from .wording import plural
 
 
 @dataclass(frozen=True)
 class FormInputs:
     """The build-playlist form's fields, read the moment Write is
-    checked. base_path and tracklist_path are the chosen file paths or
-    the empty string when nothing has been chosen yet; name is the
-    playlist-name field; target_folder is the optional target-folder
-    field or the empty string when left blank."""
+    checked. base_path and input_path are the chosen paths - input_path
+    a file or a folder - or the empty string when nothing has been
+    chosen; name is the playlist-name field. output_dir is the disk
+    folder the .nml is written to, empty for the base collection's own
+    folder; playlist_folder is the NAME of the collection FOLDER the
+    playlist is placed under, empty for the collection root. The two
+    never share a value: one is a place on disk, the other a place in
+    the collection's playlist tree (DL-297)."""
 
     base_path: str
-    tracklist_path: str
+    input_path: str
     name: str
-    target_folder: str
+    output_dir: str
+    playlist_folder: str
     allow_unmatched: bool
     full_collection: bool
@@ -55,17 +62,81 @@ def form_errors(inputs: FormInputs) -> tuple[str, ...]:
     """The refusal strings a Continue-equivalent control checks before a
-    run starts: one for a missing base path, one for a missing
-    tracklist path, one for a missing name. Order matches the order the
-    form itself reads top to bottom. An otherwise-filled FormInputs
-    reports none - target_folder, allow_unmatched and full_collection
-    carry no refusal of their own, since every value either is valid."""
+    run starts: one for a missing base path, one for a missing input,
+    one for a missing name. Order matches the order the form itself
+    reads top to bottom. output_dir, playlist_folder, allow_unmatched
+    and full_collection carry no refusal of their own: each has a
+    default meaning when left empty."""
     errors = []
     if not inputs.base_path:
         errors.append("Choose the base collection.")
-    if not inputs.tracklist_path:
-        errors.append("Choose a track list.")
+    if not inputs.input_path:
+        errors.append("Choose an input.")
     if not inputs.name:
         errors.append("Name the playlist.")
     return tuple(errors)
 
 
+_FORMAT_LABELS = {
+    InputFormat.TEXT: "Text",
+    InputFormat.CSV: "CSV",
+    InputFormat.M3U: "M3U",
+    InputFormat.FOLDER: "Folder",
+}
+
+
+def format_label(fmt: InputFormat) -> str:
+    """The label the input card's format tag shows, as the artboard
+    draws it."""
+    return _FORMAT_LABELS[fmt]
+
+
+def csv_columns_note() -> str:
+    """The CSV note's sentence, built from CSV_COLUMNS so the screen and
+    the template can never name different columns (DL-284)."""
+    required = [column.header for column in CSV_COLUMNS if column.required]
+    optional = [column.header for column in CSV_COLUMNS if not column.required]
+    return (
+        f"{' and '.join(required)} are required. {', '.join(optional[:-1])} and {optional[-1]} "
+        "are optional and help a row match more strictly."
+    )
+
+
+COLLECTION_ROOT_LABEL = "Collection root"
+
+# Shown under the disabled playlist-folder chooser. With Full collection
+# off the isolation pass (split.build_output) keeps only the new PLAYLIST
+# node under the root, so a playlist folder would change nothing in the
+# written file; the chooser says so rather than accepting a choice it
+# ignores (DL-297).
+PLAYLIST_FOLDER_NEEDS_FULL_COLLECTION = (
+    "Playlist folder applies only with Full collection on. "
+    "Off, the file holds this one playlist at its root."
+)
+
+
+def effective_playlist_folder(full_collection: bool, selected: str) -> str:
+    """The playlist folder a run passes on: the selection with Full
+    collection on, "" (the collection root) with it off, where the
+    isolated output has no folder tree for the playlist to sit in."""
+    return selected if full_collection else ""
+
+
+@dataclass(frozen=True)
+class PlaylistFolderOption:
+    label: str
+    value: str  # the NAME passed as target_folder; "" for the collection root
+    enabled: bool
+
+
+def playlist_folder_options(choices: list[PlaylistFolderChoice]) -> list[PlaylistFolderOption]:
+    """The playlist-folder chooser's options: the collection root first,
+    then every folder by path. A folder whose NAME another folder shares
+    is listed disabled, because assemble_output resolves target_folder
+    by NAME and would refuse it as target_folder_ambiguous (DL-297)."""
+    options = [PlaylistFolderOption(COLLECTION_ROOT_LABEL, "", True)]
+    for choice in choices:
+        label = choice.path if choice.unique else f"{choice.path} (name also used elsewhere)"
+        options.append(PlaylistFolderOption(label, choice.name if choice.unique else "", choice.unique))
+    return options
+
+
 def unresolved_report_rows(
@@ -164,23 +235,45 @@ def _target_folder_error(errors: tuple[str, ...]) -> Optional[str]:
     return None
 
 
-def run_summary(result: BuildPlaylistResult) -> str:
+def _read_note(input_format: Optional[InputFormat], input_encoding: str) -> str:
+    """' Read as CSV, cp1252.' for a run on csv or m3u input, ' Read as
+    Folder.' for a folder, and nothing for text, whose runs read as they
+    always have (DL-280). The codec is named because a cp1252 fallback
+    misreads another codepage without an error (DL-283)."""
+    if input_format is None or input_format is InputFormat.TEXT:
+        return ""
+    if input_format is InputFormat.FOLDER:
+        return f" Read as {format_label(input_format)}."
+    return f" Read as {format_label(input_format)}, {input_encoding}."
+
+
+def run_summary(
+    result: BuildPlaylistResult,
+    input_format: Optional[InputFormat] = None,
+    input_encoding: str = "",
+) -> str:
     """The single sentence the write step shows, covering both an
     aborted run and a written one. Tracks build_playlist_cmd.py's own
     condition names rather than inventing separate GUI phrasing
-    (DL-268): unresolved_tracks, no_entries_resolved, a target-folder
-    error, or entries_written naming the final playlist_name."""
+    (DL-268): unresolved_tracks, no_entries_resolved, a playlist-folder
+    error, or entries_written naming the final playlist_name. Counts are
+    read off result (DL-215) and the words are format-neutral, since an
+    entry may be a line, a CSV row, a playlist path or a file (DL-296)."""
+    return _outcome_sentence(result) + _read_note(input_format, input_encoding)
+
+
+def _outcome_sentence(result: BuildPlaylistResult) -> str:
     if result.output is None:
         if "unresolved_tracks" in result.errors:
             unresolved = len(result.unresolved_rows)
-            lines = plural(unresolved, "line", "lines")
+            entries = plural(unresolved, "entry", "entries")
             return (
-                f"Not written: {unresolved} track-list {lines} did not "
+                f"Not written: {unresolved} {entries} did not "
                 "resolve and Allow unmatched is off."
             )
         if "no_entries_resolved" in result.errors:
-            return "Not written: no track-list line resolved against the base collection."
+            return "Not written: no entry resolved against the base collection."
         folder_error = _target_folder_error(result.errors)
         if folder_error is not None:
-            return f"Not written: the target folder could not be resolved ({folder_error})."
+            return f"Not written: the playlist folder could not be resolved ({folder_error})."
         return f"Not written: {'; '.join(result.errors)}."
--- a/tests/test_gui_buildplaylist_view.py
+++ b/tests/test_gui_buildplaylist_view.py
@@ -13,16 +13,21 @@
 from traktor_nml.buildplaylist import BuildPlaylistResult, UnresolvedRow
 from traktor_nml.gui.buildplaylist_view import (
     FormInputs,
+    csv_columns_note,
     form_errors,
+    playlist_folder_options,
     run_summary,
     unresolved_report_rows,
 )
+from traktor_nml.playlistinput import InputFormat
+from traktor_nml.playlists import PlaylistFolderChoice
 
 _FILLED = FormInputs(
     base_path="D:/Traktor/collection.nml",
-    tracklist_path="C:/lists/warehouse.txt",
+    input_path="C:/lists/warehouse.txt",
     name="Warehouse set",
-    target_folder="",
+    output_dir="",
+    playlist_folder="",
     allow_unmatched=False,
     full_collection=False,
 )
@@ -232,0 +238,72 @@
+
+
+def test_run_summary_names_format_and_encoding_for_each_format():
+    """csv and m3u runs append the format and codec, a folder run the
+    format alone, and a text run nothing, for written and aborted runs
+    alike (DL-280, DL-296).
+
+    Mutation: _read_note returns '' for every format, so the CSV run's
+        summary lacks ' Read as CSV, cp1252.'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    written = BuildPlaylistResult(output="<NML/>", stats={"entries_written": 1, "playlist_name": "L"})
+    aborted = BuildPlaylistResult(
+        output=None, stats={},
+        unresolved_rows=[UnresolvedRow(1, "x", "", "", "unmatched"), UnresolvedRow(2, "y", "", "", "ambiguous"),
+                         UnresolvedRow(3, "z", "", "", "unparseable")],
+        errors=["unresolved_tracks"],
+    )
+    assert run_summary(written, InputFormat.CSV, "cp1252") == 'Written: "L" with 1 track. Read as CSV, cp1252.'
+    assert run_summary(written, InputFormat.M3U, "utf-8-sig") == 'Written: "L" with 1 track. Read as M3U, utf-8-sig.'
+    assert run_summary(written, InputFormat.FOLDER, "n/a") == 'Written: "L" with 1 track. Read as Folder.'
+    assert run_summary(written, InputFormat.TEXT, "utf-8-sig") == 'Written: "L" with 1 track.'
+    assert run_summary(aborted, InputFormat.CSV, "cp1252") == (
+        "Not written: 3 entries did not resolve and Allow unmatched is off. Read as CSV, cp1252."
+    )
+
+
+def test_playlist_folder_options_disable_shared_names():
+    """The root comes first with value "", a unique folder offers its
+    NAME, and a shared-name folder is listed disabled with no value.
+
+    Mutation: playlist_folder_options passes enabled=True for every
+        folder, so the shared-name 'Warmup' option reads enabled.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    options = playlist_folder_options([
+        PlaylistFolderChoice("Sets\\2026", "2026", True),
+        PlaylistFolderChoice("Archive\\Warmup", "Warmup", False),
+    ])
+    assert [(o.label, o.value) for o in options] == [
+        ("Collection root", ""), ("Sets\\2026", "2026"), ("Archive\\Warmup (name also used elsewhere)", ""),
+    ]
+    assert [o.enabled for o in options] == [True, True, False]
+
+
+def test_playlist_folder_is_dropped_without_full_collection():
+    """With Full collection off the selection never reaches the run.
+
+    Mutation: effective_playlist_folder returns selected
+        unconditionally, so effective_playlist_folder(False, 'Sets')
+        returns 'Sets' in place of ''.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    from traktor_nml.gui.buildplaylist_view import effective_playlist_folder
+
+    assert effective_playlist_folder(False, "Sets") == ""
+    assert effective_playlist_folder(True, "Sets") == "Sets"
+
+
+def test_csv_columns_note_matches_the_artboard():
+    """The note beside the CSV template names the required and optional
+    columns in the artboard's exact wording (DL-071).
+
+    Mutation: csv_columns_note drops 'File name' from the optional
+        columns, so the note reads 'Album and Duration are optional' and
+        differs from the artboard's wording.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    assert csv_columns_note() == (
+        "Artist and Title are required. Album, Duration and File name are optional "
+        "and help a row match more strictly."
+    )

```

**Documentation:**

```diff
--- a/traktor_nml/gui/buildplaylist_view.py
+++ b/traktor_nml/gui/buildplaylist_view.py
@@ -108,13 +108,18 @@ def effective_playlist_folder(full_collection: bool, selected: str) -> str:
 
 @dataclass(frozen=True)
 class PlaylistFolderOption:
+    """One entry in the playlist-folder chooser: the label shown, the
+    value a run passes as target_folder, and whether it can be chosen
+    (DL-297)."""
+
     label: str
     value: str  # the NAME passed as target_folder; "" for the collection root
     enabled: bool
 
 
 def playlist_folder_options(choices: list[PlaylistFolderChoice]) -> list[PlaylistFolderOption]:
-    """The playlist-folder chooser's options: the collection root first,
-    then every folder by path. A folder whose NAME another folder shares
+    """The playlist-folder chooser's options: the collection root first,
+    then every folder in the order choices holds them, each labelled by
+    its path. A folder whose NAME another folder shares
     is listed disabled, because assemble_output resolves target_folder
     by NAME and would refuse it as target_folder_ambiguous (DL-297)."""
--- a/tests/test_gui_buildplaylist_view.py
+++ b/tests/test_gui_buildplaylist_view.py
@@ -240,2 +240,10 @@
 def test_run_summary_names_format_and_encoding_for_each_format():
+    """csv and m3u runs append the format and codec, a folder run the
+    format alone, and a text run nothing, for written and aborted runs
+    alike (DL-280, DL-296).
+
+    Mutation: _read_note returns '' for every format, so the CSV run's
+        summary lacks ' Read as CSV, cp1252.'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     written = BuildPlaylistResult(output="<NML/>", stats={"entries_written": 1, "playlist_name": "L"})
@@ -257,2 +265,9 @@
 def test_playlist_folder_options_disable_shared_names():
+    """The root comes first with value "", a unique folder offers its
+    NAME, and a shared-name folder is listed disabled with no value.
+
+    Mutation: playlist_folder_options passes enabled=True for every
+        folder, so the shared-name 'Warmup' option reads enabled.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     options = playlist_folder_options([
@@ -268,2 +283,9 @@
 def test_playlist_folder_is_dropped_without_full_collection():
+    """With Full collection off the selection never reaches the run.
+
+    Mutation: effective_playlist_folder returns selected
+        unconditionally, so effective_playlist_folder(False, 'Sets')
+        returns 'Sets' in place of ''.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     from traktor_nml.gui.buildplaylist_view import effective_playlist_folder
@@ -275,2 +297,10 @@
 def test_csv_columns_note_matches_the_artboard():
+    """The note beside the CSV template names the required and optional
+    columns in the artboard's exact wording (DL-071).
+
+    Mutation: csv_columns_note drops 'File name' from the optional
+        columns, so the note reads 'Album and Duration are optional' and
+        differs from the artboard's wording.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     assert csv_columns_note() == (

```

> **Developer notes**: Apply the same field rename in every FormInputs(...) in this file
(tracklist_path -> input_path; target_folder -> output_dir="" and
playlist_folder=""), and these expectation changes, keeping each test's
docstring mutation but re-running it and pasting the new verbatim output:
  "Choose a track list."  -> "Choose an input."   (both form_errors tests)
  "Not written: 2 track-list lines did not resolve and Allow unmatched is off."
      -> "Not written: 2 entries did not resolve and Allow unmatched is off."
  singular test: assert "1 entry " in ...; assert "entries" not in ...
  "Not written: no track-list line resolved against the base collection."
      -> "Not written: no entry resolved against the base collection."
  "the target folder could not be resolved" -> "the playlist folder could not be resolved"

**CC-M-007-004** (traktor_nml/gui/theme.py) - implements CI-M-007-004

**Code:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ -794,2 +794,17 @@ end of page_stylesheet()
 .wizard-next-step-title {{ display: block; color: {TEXT}; font-weight: 600; font-size: {TYPE_13}; margin-bottom: {SPACE_1}; }}
+/* design/build-playlist/Specs.dc.html's input .row: the chosen path, the
+   detected format tag and the two choosers on one line, the path taking
+   the room and truncating rather than pushing the buttons off the card. */
+.buildplaylist-input-row {{ display: flex; align-items: center; gap: {SPACE_10}; flex-wrap: nowrap; min-width: 0; }}
+.buildplaylist-input-row > .font-mono {{ flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
+/* Specs.dc.html's .fmt: the format read_input will read the input as,
+   tinted with the action hue because it describes what the run does. */
+.buildplaylist-format-tag {{ flex: none; font: 600 {TYPE_11}/1 {FONT_MONO}; letter-spacing: .06em; text-transform: uppercase; color: {ACTION_TINT_TEXT}; background: {BORDER_SUBTLE_9}; border: 1px solid {ACTION_TINT_BORDER_ALT}; border-radius: {RADIUS_SM}; padding: {SPACE_3} {SPACE_6}; white-space: nowrap; }}
+/* Specs.dc.html's template button sits at the note's right edge. */
+.buildplaylist-template-control {{ margin-left: auto; flex: none; }}
+/* Specs.dc.html's folder .row: Output folder and Playlist folder side by
+   side at equal width, tops aligned because only the output side carries
+   a button under its label. */
+.buildplaylist-folder-row {{ display: flex; gap: {SPACE_14}; align-items: flex-start; flex-wrap: nowrap; width: 100%; }}
+.buildplaylist-folder-col {{ flex: 1; min-width: 0; gap: {SPACE_6}; }}
 """

```

**Documentation:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py

```

> **Developer notes**: INTENT against traktor_nml/gui/theme.py (LF) as it stands after the
app-wide button-fill change. Append these rules at the end of the
page_stylesheet() f-string, before its closing triple quote; take every
colour, size and radius from the module's existing tokens (no literal),
and if the button-fill change renamed or added a token the artboard value
maps to, use that token. The CSV note itself carries the existing
.wizard-callout rule (the artboard's .note is the same panel), and every
button keeps the class set the button-fill change gives secondary buttons,
so no button colour rule is added here. Cite the artboard by selector, not
line number: its line numbers move with M-006.

**CC-M-007-005** (docs/2026-09-16-build-playlist-inputs-browser-record.md) - implements CI-M-007-005

**Code:**

```diff
--- /dev/null
+++ b/docs/2026-09-16-build-playlist-inputs-browser-record.md
@@ -0,0 +1,58 @@
+# Served-page record: build-playlist inputs, template and folders
+
+DL-084 as DL-169 amends it: the readings a browser took off the running
+`/build-playlist` page, one verdict per surface, followed by a structural
+reading of what the page composes against
+`design/build-playlist/Specs.dc.html`.
+
+## How the run was taken
+
+<Server and fixture used, which functions were stubbed (only
+`pick_file_or_folder` and `pick_save_path`), the viewport (`1280x900`),
+and the commit under measurement plus this milestone's changes.>
+
+The walk: choose a base collection holding a duplicated folder name;
+choose a CSV input and read the format tag; press `Download CSV template`
+served over HTTP and read the downloaded bytes; choose a folder input;
+choose an output folder; read the playlist-folder chooser with Full
+collection off; turn Full collection on; open the chooser; pick a folder;
+press `Write playlist` once with an unresolved entry and Allow unmatched
+off, then once with it on; read the written file.
+
+## Readings
+
+| Surface | Expected | Read | Verdict |
+|---|---|---|---|
+| The input card's label | `INPUT` | <read> | <verdict> |
+| The input choosers | `Choose file...` and `Choose folder...` side by side | <read> | <verdict> |
+| The format tag, CSV chosen | `CSV` | <read> | <verdict> |
+| The format tag, folder chosen | `FOLDER` | <read> | <verdict> |
+| The CSV note | names Artist and Title as required and Album, Duration, File name as optional | <read> | <verdict> |
+| The template control | `Download CSV template`, at the note's right edge | <read> | <verdict> |
+| The downloaded template | the header row alone, BOM, CRLF: `Artist,Title,Album,Duration,File name` | <read> | <verdict> |
+| The target-folder input | absent | <read> | <verdict> |
+| The output-folder chooser, nothing chosen | `Choose folder...` beside the base collection's folder, named as the default | <read> | <verdict> |
+| The output-folder chooser, folder chosen | the chosen path | <read> | <verdict> |
+| The playlist-folder chooser, Full collection off | disabled at `Collection root`, `Playlist folder applies only with Full collection on. Off, the file holds this one playlist at its root.` under it | <read> | <verdict> |
+| The output-folder chooser, Full collection off | enabled | <read> | <verdict> |
+| The playlist-folder chooser, Full collection on | enabled, note hidden | <read> | <verdict> |
+| The playlist-folder chooser's first option | `Collection root`, selected by default | <read> | <verdict> |
+| The playlist-folder chooser's folder options | the base's folder paths in tree order | <read> | <verdict> |
+| The duplicate-name folder option | listed with its path and `(name also used elsewhere)`, disabled and not selectable | <read> | <verdict> |
+| The report card's title | `Unresolved entries` | <read> | <verdict> |
+| The footer after the aborted run | `Not written: N entries did not resolve and Allow unmatched is off. Read as CSV, <codec>.` | <read> | <verdict> |
+| The footer after the written run | `Written: "<name>" with N tracks. Read as ...` | <read> | <verdict> |
+| The written file's location | `<output folder>\<name>.nml`, no directory named after the playlist folder | <read> | <verdict> |
+| The written playlist's placement | under the chosen FOLDER in the file's playlist tree | <read> | <verdict> |
+| Document scroll | none | `scrollWidth` and `scrollHeight` against a `1280x900` viewport | <verdict> |
+
+## Structural verdicts
+
+- **The input card.** <How the page composes the input row, format tag and
+  CSV note against Specs.dc.html's input `.lblrow`, `.fmt` and `.note`.>
+- **The folder row.** <Output folder and Playlist folder side by side
+  against the artboard's folder `.row`, and whether the chooser's open
+  list draws as the artboard's `.menu`.>
+- **The report card.** <Title and column headers against the artboard's
+  `table.rep`.>
+
--- a/tests/test_docs_browser_record_structure.py
+++ b/tests/test_docs_browser_record_structure.py
@@ -80,1 +80,2 @@ READING_DIGESTS
     "2026-09-15-write-step-after-the-write-browser-record.md": "32dfbfadf3db8e36441a21e886003215da2cb59fb63a7665e7b0429757a3c61a",
+    "2026-09-16-build-playlist-inputs-browser-record.md": "<sha256 from _reading_digest over the finished record>",
--- a/docs/CLAUDE.md
+++ b/docs/CLAUDE.md
@@ -45,0 +46,1 @@ after the 2026-09-15-write-step-after-the-write-browser-record.md row
+| `2026-09-16-build-playlist-inputs-browser-record.md` | The build-playlist screen read after its inputs widened: file and folder choosers with the format tag, the CSV note and template download, the output-folder and playlist-folder choosers replacing the target-folder field with the duplicate-name folder disabled, the entries report and footer, and the written file's location and placement; readings plus structural verdicts against `design/build-playlist/Specs.dc.html` | Changing the build-playlist screen, or checking what its record measured |

```

**Documentation:**

```diff
--- a/docs/2026-09-16-build-playlist-inputs-browser-record.md
+++ b/docs/2026-09-16-build-playlist-inputs-browser-record.md

```

> **Developer notes**: A served-page record holds readings taken off the running page, so its
Read and Verdict columns cannot be written at planning time. The file
below is the record's skeleton: the implementer serves the page, walks it,
and fills every Read cell with what the browser returned and every Verdict
with matches or differs. A differs row is fixed in the artboard first
(DL-071), never by editing the reading. Then compute the digest with
tests/test_docs_browser_record_structure.py's _reading_digest over the
finished file and register it, add the docs/CLAUDE.md index row (CRLF),
and run the digest guard.

**CC-M-007-006** (traktor_nml/playlists.py) - implements CI-M-007-006

**Code:**

```diff
--- a/traktor_nml/playlists.py
+++ b/traktor_nml/playlists.py
@@ -106,4 +106,56 @@ def playlist_path_pairs(root: ET.Element) -> list[tuple[str, ET.Element]]:
     return pairs
 
 
+@dataclass(frozen=True)
+class PlaylistFolderChoice:
+    """One FOLDER a new playlist can be placed under. path is the
+    backslash-joined chain of FOLDER names below the root, the encoding
+    playlist_path_pairs uses; name is the FOLDER's own NAME, the value
+    assemble_output's target_folder takes. unique is False when another
+    FOLDER under the root holds the same NAME."""
+
+    path: str
+    name: str
+    unique: bool
+
+
+def playlist_folder_choices(root: ET.Element) -> list[PlaylistFolderChoice]:
+    """Every FOLDER node below the PLAYLISTS root, in tree order.
+
+    buildplaylist._find_target_subnodes resolves target_folder by NAME
+    alone over the root's descendants and refuses a NAME two FOLDERs
+    share as target_folder_ambiguous, so such a folder cannot be the
+    target of a run; unique=False lets a chooser show it without offering
+    it (DL-297). The root itself is excluded: choosing it is the absence
+    of a target folder. Playlists are not listed. An NML without a
+    PLAYLISTS root or its SUBNODES gives an empty list.
+    """
+    playlists_root = root.find(".//PLAYLISTS/NODE")
+    if playlists_root is None or playlists_root.find("SUBNODES") is None:
+        return []
+
+    found: list[tuple[str, str]] = []
+
+    def walk(node: ET.Element, prefix: list[str]) -> None:
+        if node.attrib.get("TYPE") != "FOLDER":
+            return
+        name = node.attrib.get("NAME", "")
+        found.append(("\\".join(prefix + [name]), name))
+        subnodes = node.find("SUBNODES")
+        if subnodes is not None:
+            for child in subnodes:
+                walk(child, prefix + [name])
+
+    for child in playlists_root.find("SUBNODES"):
+        walk(child, [])
+
+    # The same scope _find_target_subnodes searches: every FOLDER under the
+    # root. The root's own NAME is counted too, because a target_folder equal
+    # to it selects the root rather than the descendant that shares it.
+    name_counts: dict[str, int] = {playlists_root.attrib.get("NAME", ""): 1}
+    for _path, name in found:
+        name_counts[name] = name_counts.get(name, 0) + 1
+    return [PlaylistFolderChoice(path, name, name_counts[name] == 1) for path, name in found]
+
+
 def playlist_paths(root: ET.Element) -> dict[str, ET.Element]:

```

**Documentation:**

```diff
--- a/traktor_nml/playlists.py
+++ b/traktor_nml/playlists.py

```


**CC-M-007-007** (tests/test_playlists_folder_choices.py) - implements CI-M-007-007

**Code:**

```diff
--- /dev/null
+++ b/tests/test_playlists_folder_choices.py
@@ -0,0 +1,89 @@
+"""playlists.playlist_folder_choices: the FOLDER nodes the build-playlist
+screen's playlist-folder chooser lists (DL-297). System interpreter."""
+
+from __future__ import annotations
+
+from traktor_nml.playlists import PlaylistFolderChoice, playlist_folder_choices
+from traktor_nml.xmlio import parse_xml_bytes
+
+
+def _root(playlists: str):
+    return parse_xml_bytes((
+        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
+        '<COLLECTION ENTRIES="0"></COLLECTION>'
+        f"{playlists}<SETS></SETS><INDEXING></INDEXING></NML>"
+    ).encode("utf-8"))
+
+
+def _folder(name: str, inner: str = "") -> str:
+    return f'<NODE TYPE="FOLDER" NAME="{name}"><SUBNODES COUNT="0">{inner}</SUBNODES></NODE>'
+
+
+def _playlist(name: str) -> str:
+    return f'<NODE TYPE="PLAYLIST" NAME="{name}"><PLAYLIST ENTRIES="0" TYPE="LIST" UUID="u"></PLAYLIST></NODE>'
+
+
+def _tree(inner: str) -> str:
+    return f'<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="0">{inner}</SUBNODES></NODE></PLAYLISTS>'
+
+
+def test_nested_paths_in_tree_order_root_and_playlists_excluded() -> None:
+    """Folders come back parent before child in document order, paths
+    joined with backslashes below $ROOT, no playlist and no root.
+
+    Mutation: walk joins prefix + [name] with '/' in place of a
+        backslash, so the nested folder's path reads 'Sets/2026'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    root = _root(_tree(
+        _folder("Sets", _folder("2026", _playlist("Aug")) + _playlist("Loose"))
+        + _playlist("Top")
+        + _folder("Archive")
+    ))
+    assert playlist_folder_choices(root) == [
+        PlaylistFolderChoice("Sets", "Sets", True),
+        PlaylistFolderChoice("Sets\\2026", "2026", True),
+        PlaylistFolderChoice("Archive", "Archive", True),
+    ]
+
+
+def test_duplicate_name_flags_both_folders() -> None:
+    """Two FOLDERs named 'Warmup' under different parents are both
+    non-unique; their parents stay unique.
+
+    Mutation: playlist_folder_choices passes True for unique on every
+        choice, so both 'Warmup' folders read unique.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    root = _root(_tree(_folder("Sets", _folder("Warmup")) + _folder("Archive", _folder("Warmup"))))
+    choices = playlist_folder_choices(root)
+    assert [c.path for c in choices] == ["Sets", "Sets\\Warmup", "Archive", "Archive\\Warmup"]
+    assert [c.unique for c in choices] == [True, False, True, False]
+
+
+def test_two_top_level_folders_named_sets_are_both_non_unique() -> None:
+    """The acceptance case: a base with two FOLDERs named 'Sets' offers
+    neither, since target_folder resolves by NAME alone (DL-297).
+
+    Mutation: playlist_folder_choices marks a choice unique when its
+        name has not appeared earlier in the walk, so the first 'Sets'
+        reads unique.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    root = _root(_tree(_folder("Sets") + _folder("Sets")))
+    assert [c.unique for c in playlist_folder_choices(root)] == [False, False]
+
+
+def test_missing_playlists_or_subnodes_gives_empty_list() -> None:
+    """An NML with no PLAYLISTS root, or a root without SUBNODES, gives
+    an empty list rather than an error.
+
+    Mutation: playlist_folder_choices drops its
+        `playlists_root.find('SUBNODES') is None` check, so the root
+        without SUBNODES raises TypeError when its missing SUBNODES is
+        iterated.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    assert playlist_folder_choices(_root("")) == []
+    assert playlist_folder_choices(_root('<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"></NODE></PLAYLISTS>')) == []

```

**Documentation:**

```diff
--- a/tests/test_playlists_folder_choices.py
+++ b/tests/test_playlists_folder_choices.py
@@ -31,2 +31,9 @@
 def test_nested_paths_in_tree_order_root_and_playlists_excluded() -> None:
+    """Folders come back parent before child in document order, paths
+    joined with backslashes below $ROOT, no playlist and no root.
+
+    Mutation: walk joins prefix + [name] with '/' in place of a
+        backslash, so the nested folder's path reads 'Sets/2026'.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     root = _root(_tree(
@@ -44,2 +51,9 @@
 def test_duplicate_name_flags_both_folders() -> None:
+    """Two FOLDERs named 'Warmup' under different parents are both
+    non-unique; their parents stay unique.
+
+    Mutation: playlist_folder_choices passes True for unique on every
+        choice, so both 'Warmup' folders read unique.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     root = _root(_tree(_folder("Sets", _folder("Warmup")) + _folder("Archive", _folder("Warmup"))))
@@ -51,2 +65,10 @@
 def test_two_top_level_folders_named_sets_are_both_non_unique() -> None:
+    """The acceptance case: a base with two FOLDERs named 'Sets' offers
+    neither, since target_folder resolves by NAME alone (DL-297).
+
+    Mutation: playlist_folder_choices marks a choice unique when its
+        name has not appeared earlier in the walk, so the first 'Sets'
+        reads unique.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     root = _root(_tree(_folder("Sets") + _folder("Sets")))
@@ -56,2 +78,11 @@
 def test_missing_playlists_or_subnodes_gives_empty_list() -> None:
+    """An NML with no PLAYLISTS root, or a root without SUBNODES, gives
+    an empty list rather than an error.
+
+    Mutation: playlist_folder_choices drops its
+        `playlists_root.find('SUBNODES') is None` check, so the root
+        without SUBNODES raises TypeError when its missing SUBNODES is
+        iterated.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     assert playlist_folder_choices(_root("")) == []

```


**CC-M-007-008** (tests/test_gui_buildplaylist_output_path.py) - implements CI-M-007-008

**Code:**

```diff
--- /dev/null
+++ b/tests/test_gui_buildplaylist_output_path.py
@@ -0,0 +1,109 @@
+"""The build-playlist screen's two folders never share a value (DL-297):
+the output folder decides where the .nml is written on disk, and the
+playlist folder decides where the playlist sits in the collection.
+
+Importing traktor_nml.gui.app needs nicegui; the stand-ins from
+tests/test_build_playlist_byte_identity.py are installed per test and
+removed in a finally.
+"""
+
+from __future__ import annotations
+
+import importlib
+import inspect
+from pathlib import Path
+from unittest.mock import patch
+
+from tests.conftest import run_tool
+from tests.test_build_playlist_byte_identity import _FIXED_UUID, _entry, _install_nicegui_stub, _uninstall
+
+
+def _app():
+    _uninstall()
+    _install_nicegui_stub()
+    return importlib.import_module("traktor_nml.gui.app")
+
+
+def test_output_path_with_and_without_an_output_folder(tmp_path: Path) -> None:
+    """No output folder writes beside the base collection; a chosen one
+    writes <folder>/<name>.nml. The function has no playlist-folder
+    parameter at all.
+
+    Mutation: _derive_build_playlist_output_path takes a fourth
+        playlist_folder parameter and joins it onto the directory, so
+        its parameter list is not ['base_path', 'output_dir', 'name'].
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    try:
+        app = _app()
+        base = tmp_path / "lib" / "collection.nml"
+        assert app._derive_build_playlist_output_path(base, "", "Set") == tmp_path / "lib" / "Set.nml"
+        chosen = tmp_path / "exports"
+        assert app._derive_build_playlist_output_path(base, str(chosen), "Set") == chosen / "Set.nml"
+        params = list(inspect.signature(app._derive_build_playlist_output_path).parameters)
+        assert params == ["base_path", "output_dir", "name"]
+    finally:
+        _uninstall()
+
+
+def _base_with_folder() -> str:
+    entries = _entry("A", "One", "one.mp3") + _entry("B", "Two", "two.mp3")
+    return (
+        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
+        '<NML VERSION="20"><HEAD PROGRAM="Traktor" VERSION="1"></HEAD>'
+        f'<COLLECTION ENTRIES="2">{entries}</COLLECTION>'
+        '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="1">'
+        '<NODE TYPE="FOLDER" NAME="Sets"><SUBNODES COUNT="0"></SUBNODES></NODE>'
+        "</SUBNODES></NODE></PLAYLISTS><SETS></SETS><INDEXING></INDEXING></NML>"
+    )
+
+
+def test_output_folder_and_playlist_folder_match_the_cli(tmp_path: Path) -> None:
+    """Choosing output folder X and playlist folder Sets writes
+    X/<name>.nml with the playlist under FOLDER Sets, byte-identical to
+    the CLI run with output X/<name>.nml and --target-folder Sets.
+
+    Mutation: _run_build_playlist passes inputs.output_dir as
+        target_folder, so the run refuses with target_folder_not_found
+        and result.errors is not empty.
+    Observed: the implementer records the verbatim assertion output here.
+    """
+    base = tmp_path / "base.nml"
+    base.write_text(_base_with_folder(), encoding="utf-8", newline="")
+    tracks = tmp_path / "tracks.txt"
+    tracks.write_text("A - One\nB - Two\n", encoding="utf-8")
+    cli_dir = tmp_path / "cli"
+    gui_dir = tmp_path / "gui"
+    cli_dir.mkdir()
+    gui_dir.mkdir()
+
+    with patch("uuid.uuid4", return_value=_FIXED_UUID):
+        cli = run_tool(
+            ["build-playlist", str(base), str(tracks), str(cli_dir / "Set.nml"), "--name", "Set",
+             "--target-folder", "Sets", "--full-collection"],
+            cwd=tmp_path,
+        )
+    assert cli.exit_code == 0, cli.stderr
+
+    try:
+        app = _app()
+        inputs = app.FormInputs(
+            base_path=str(base), input_path=str(tracks), name="Set",
+            output_dir=str(gui_dir), playlist_folder="Sets",
+            allow_unmatched=False, full_collection=True,
+        )
+        with patch("uuid.uuid4", return_value=_FIXED_UUID):
+            result, _read = app._run_build_playlist(inputs)
+        assert result.errors == []
+    finally:
+        _uninstall()
+
+    gui_bytes = (gui_dir / "Set.nml").read_bytes()
+    assert gui_bytes == (cli_dir / "Set.nml").read_bytes()
+    # --full-collection keeps the tree, so the placement is visible: the
+    # playlist is Sets' child, not $ROOT's.
+    from traktor_nml.xmlio import parse_xml_bytes
+
+    sets = parse_xml_bytes(gui_bytes).find(".//PLAYLISTS/NODE/SUBNODES/NODE[@NAME='Sets']")
+    assert [node.attrib.get("NAME") for node in sets.find("SUBNODES")] == ["Set"]
+    assert not (tmp_path / "Sets").exists()

```

**Documentation:**

```diff
--- a/tests/test_gui_buildplaylist_output_path.py
+++ b/tests/test_gui_buildplaylist_output_path.py
@@ -27,2 +27,11 @@
 def test_output_path_with_and_without_an_output_folder(tmp_path: Path) -> None:
+    """No output folder writes beside the base collection; a chosen one
+    writes <folder>/<name>.nml. The function has no playlist-folder
+    parameter at all.
+
+    Mutation: _derive_build_playlist_output_path takes a fourth
+        playlist_folder parameter and joins it onto the directory, so
+        its parameter list is not ['base_path', 'output_dir', 'name'].
+    Observed: the implementer records the verbatim assertion output here.
+    """
     try:
@@ -52,2 +61,11 @@
 def test_output_folder_and_playlist_folder_match_the_cli(tmp_path: Path) -> None:
+    """Choosing output folder X and playlist folder Sets writes
+    X/<name>.nml with the playlist under FOLDER Sets, byte-identical to
+    the CLI run with output X/<name>.nml and --target-folder Sets.
+
+    Mutation: _run_build_playlist passes inputs.output_dir as
+        target_folder, so the run refuses with target_folder_not_found
+        and result.errors is not empty.
+    Observed: the implementer records the verbatim assertion output here.
+    """
     base = tmp_path / "base.nml"

```


**CC-M-007-009** (traktor_nml/gui/README.md) - implements CI-M-007-009

**Code:**

```diff
--- a/traktor_nml/gui/README.md
+++ b/traktor_nml/gui/README.md
@@ -277,0 +278,40 @@
+
+## The build-playlist screen's inputs and its two folders
+
+The screen reads its input through `playlistinput.read_input`, the same
+call the CLI makes, so a refusal the screen shows is the code the CLI
+prints (DL-281). `Choose file...` takes a text list, a CSV or an M3U;
+`Choose folder...` takes a folder. The format tag shows what
+`detect_format` names before any run, and the footer names the format and
+codec after one, because a `cp1252` fallback misreads another codepage
+without an error (DL-283, DL-296).
+
+`Download CSV template` delivers `playlistinput.csv_template_bytes()`.
+Served over HTTP that is `ui.download`. In the native window pywebview
+blocks browser downloads by default, so `app._deliver_csv_template` asks
+for a path through `file_picker.pick_save_path` and writes the bytes
+itself (DL-295).
+
+Two controls hold two different places, and no value passes between them
+(DL-297):
+
+| Control | Names | CLI counterpart | Empty means |
+|---|---|---|---|
+| Output folder | a directory on disk; the file is `<folder>/<playlist name>.nml` | the positional `output` path | the base collection's own directory |
+| Playlist folder | a `FOLDER` in the base collection's playlist tree, by its `NAME` | `--target-folder` | the collection root |
+
+The playlist-folder chooser is refilled from
+`playlists.playlist_folder_choices` each time a base collection is chosen.
+`buildplaylist.assemble_output` finds `target_folder` by `NAME` alone and
+refuses a `NAME` two folders share, so such a folder is listed with its
+path and disabled rather than offered; its option key starts with a NUL
+character, which no `NAME` equals, so it cannot reach `target_folder` even
+if the disable were lost.
+
+The playlist-folder chooser is enabled only while Full collection is on.
+With it off, the isolation pass (`split.build_output` over the one new
+playlist) keeps only that playlist directly under the root, so no folder
+the chooser names survives into the file; the chooser is disabled at
+`Collection root`, a note under it says why, and
+`buildplaylist_view.effective_playlist_folder` passes no `target_folder`.
+The output folder applies either way.

```

**Documentation:**

```diff
--- a/traktor_nml/gui/README.md
+++ b/traktor_nml/gui/README.md

```

> **Developer notes**: traktor_nml/gui/README.md (LF) holds no build-playlist section; add one
after "## The two step mechanisms" section's end (the end of the file).

**CC-M-007-010** (traktor_nml/README.md) - implements CI-M-007-010

**Code:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -92,3 +92,3 @@ high-water mark paragraph
-This file is the authority for the log's high-water mark, which is `DL-294`:
+This file is the authority for the log's high-water mark, which is `DL-297`:
 an entry numbered against anything else collides with an entry this file
 names, so the next plan numbers from there.
@@ -2349,4 +2349,4 @@ the DL-266 bullet
-- The base collection and the tracklist file are both chosen through
-  `gui/file_picker.py`'s existing `pick_file_or_folder`, matching the
-  CLI's `base`/`tracklist` positional file arguments, rather than a
-  paste-in-text tracklist entry (DL-266).
+- The base collection and the input are both chosen through
+  `gui/file_picker.py`'s `pick_file_or_folder`, matching the CLI's
+  `base`/`tracklist` positional arguments, rather than a paste-in-text
+  tracklist entry (DL-266).
@@ -2375,5 +2375,4 @@ the DL-272 bullet
-- The build-playlist form's output path is not a separate literal path
-  chooser: it is derived by combining the playlist name field with the
-  optional target-folder field, relative to the base collection's own
-  directory, the same way `rewrite.path_collides` and the write step
-  consume it (DL-272).
+- The build-playlist form's output path is derived rather than typed:
+  the playlist name is the file's stem, and `rewrite.path_collides` and
+  the write step both consume the one derived path (DL-272). Its directory
+  is the output-folder chooser's, per DL-297.
@@ -2787,0 +2787,32 @@ Design Decisions: after the DL-294 bullet
+- The `/build-playlist` screen offers `Choose file...` (text, CSV, M3U) and
+  `Choose folder...` for its input, shows the detected format and, after a
+  run, the codec, and shows the CSV columns beside a `Download CSV
+  template` control. Native mode writes the template through a pywebview
+  SAVE dialog (`file_picker.pick_save_path`), because pywebview blocks
+  browser downloads by default; served over HTTP it goes through
+  `ui.download`. The artboard is drawn first (DL-071, DL-295).
+- `buildplaylist_view.run_summary` and `form_errors` use format-neutral
+  words - `entry`/`entries` through `wording.plural`, `Choose an input.` -
+  and a run on CSV, M3U or folder input appends the format, and for CSV
+  and M3U the codec, it read; counts are read off the result (DL-215,
+  DL-296).
+- The build-playlist screen's output folder and playlist folder are two
+  controls that never share a value. The output folder is a disk
+  directory chosen through `pick_file_or_folder(directories_only=True)`;
+  the file is `<output folder>/<playlist name>.nml`, or sits in the base
+  collection's directory when none is chosen - the CLI's positional output
+  path. The playlist folder is a chooser over the base collection's
+  `FOLDER` nodes from `playlists.playlist_folder_choices` plus `Collection
+  root`; its `NAME` is `assemble_output`'s `target_folder`, the CLI's
+  `--target-folder`, and `None` for the root. A `FOLDER` whose `NAME`
+  another `FOLDER` holds is listed disabled with its path, because
+  `target_folder` is resolved by `NAME` alone and would refuse as
+  `target_folder_ambiguous`. One field cannot serve both: joined onto a
+  disk path a `FOLDER` name names a directory that need not exist. The
+  playlist-folder chooser is enabled only while Full collection is on:
+  otherwise the isolation pass (`split.build_output`) keeps only the new
+  playlist directly under the root, so a folder choice would change
+  nothing in the file; the disabled chooser carries a note saying so and
+  no `target_folder` is passed. The output folder applies either way. This
+  supersedes DL-272's statement that the form has no separate output-path
+  control (DL-297).

```

**Documentation:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md

```

> **Developer notes**: traktor_nml/README.md (LF): high-water mark to DL-297, the DL-266 and
DL-272 bullets reworded so the README describes the form as it stands, and
three decision bullets after the DL-294 bullet CI-M-005-003 added.

## Execution Waves

- W-001: M-001
- W-002: M-002, M-006
- W-003: M-003
- W-004: M-004
- W-005: M-005
- W-006: M-007

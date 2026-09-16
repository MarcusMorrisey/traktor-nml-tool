# Plan

## Overview

The resolve step's detail rail draws one control per distinct answer whose whole label is the collections that supply it followed by every value joined with ' | ' (traktor_nml/gui/app.py:2507). No field name stands on screen, no value carries its unit, and two answers differing in one attribute read as two runs of text, so the operator cannot tell the answers apart and picks blind.

**Approach**: Each answer prints as a record: one row per tracked attribute, field name beside the formatted value beside the raw string, with a mark on the fields whose values differ across the answers. The agreeing values that make a record complete are not reachable from the page today, so splice's conflict row carries them alongside attrs rather than widening attrs, which is a column of the conflict CSV. The field assembly, the mark rule and every unit formatting live in a new nicegui-free traktor_nml/gui/answer_detail.py the suite runs under the system interpreter; app.py draws what it returns and theme.py declares the classes. The artboard is amended before the screen (DL-071), and the milestone closes on a served-page record over an extended gate fixture. traktor_nml/README.md is the decision-log authority and its high-water mark is DL-241, so the decisions here are numbered from DL-242.

## Planning Context

### Decision Log

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-242 | Each answer in the resolve rail reads as a complete record: every name in splice._TRACKED_ATTRS the group's records carry, agreeing fields included, one field per line as field name, formatted value and raw value | An answer joined into one string of values cannot be told from its neighbour, and a rail showing only the divergent subset reads as a diff rather than as the record that wins -> the operator picks a record, so the rail prints the record -> the six tracked attributes stand per answer and the mark carries the difference |
| DL-243 | The divergence mark stands on a field exactly where its name is in the row's attrs | splice computes attrs as the tracked attributes whose values differ across the group's members -> that set is precisely the fields that differ across the answers, already computed and already carried to the page -> the rule is a membership test in a nicegui-free module, and no second divergence computation exists to disagree with the first |
| DL-244 | The agreeing values ride alongside attrs as their own field on ConflictRow, ConflictGroup and ConflictRowView; attrs names the divergent set alone | attrs is one of the three columns the conflict CSV writes and the line splice_cmd prints (traktor_nml/commands/splice_cmd.py:22, :24) -> widening it in place rewrites recorded output for every run -> the complete record is carried as an addition, and the CSV columns are guarded unmoved |
| DL-245 | Every member of a group agrees on every attribute outside attrs, so one group-wide mapping of agreeing attribute to value is well defined and is computed beside the candidates | divergent_attrs at splice.py:340-341 names the attributes whose value set across the group's members has more than one member -> an attribute outside it holds one value across every member of the group, candidates included -> the agreeing values belong to the group rather than to a candidate, and a guard reads that off a three-answer group rather than asserting it |
| DL-246 | Formatting and field assembly live in traktor_nml/gui/answer_detail.py, a module importing no nicegui | DL-069 puts every rule the suite reaches below the nicegui boundary, and conflict_model.py is the vocabulary a pick is recorded in -> a display formatting rule there gives that module a second purpose the package's one-purpose-per-module table does not carry -> the field rows, their labels, their formatted values and the mark stand in one module app.py reads from |
| DL-247 | FILESIZE renders as megabytes by dividing by 1024 once; PLAYTIME_FLOAT renders as minutes and seconds; BITRATE renders as kilobits per second by dividing by 1000, unconditionally, because every record the rail answers over is Traktor-borne (DL-253); the raw string stands beside every formatted value in mono | Traktor writes FILESIZE in kilobytes - the calibration comment at traktor_nml/matching.py:124-128 records the measured error of FILESIZE against bytes/1024, and _size_kb (traktor_nml/matching.py:166-180) deliberately does no conversion because both sides already carry kilobytes - and BITRATE in bits per second (collection_textual_patch_test.nml carries values near 1000000) -> a formatting dividing a kilobyte count twice or reading a bitrate as kilobits prints a number the collection does not hold, and the kilobits bitrate traktor_nml/diskscan.py:59 writes would print near 0.3 kbps if it could reach the rail -> one division each with no provenance branch, the provenance itself settled by DL-253, the precision by DL-255, and the raw value stays visible because it is what the written file carries |
| DL-248 | A value that is empty or does not parse as a number prints as itself with no formatted companion | traktor_nml/model.py:217-219 yields an empty string for every INFO-borne attribute where a record carries no INFO element -> a formatter dividing that string raises inside a page build -> each formatter returns the raw string unchanged where the value does not parse, and a guard covers the empty string |
| DL-249 | No colour ranks one value against another | The tool has no way to know that a larger filesize or a higher bitrate is the better record -> a green value states a judgement the model cannot support -> difference is marked and never ranked |
| DL-250 | The rail head is the one place the file is named; design/reconnect-wizard/Resolve.dc.html carries no 'The file' group | The head prints the identity key in mono and the artboard's body opens with a labelled Path row holding the same string -> drawing both prints the file twice in a 400px rail -> the artboard is amended first and the screen is built to it (DL-071) |
| DL-251 | The gate fixture's conflicting entry carries bits-per-second bitrates and a second divergent field agreeing between two of its three answers | The fixture's one conflict diverges on bitrate alone, at values a Traktor collection never writes -> a served page over it exercises neither the unit formatting nor a mark that discriminates between answers -> the fixture carries a field that agrees and a field that differs, so the record reads both |
| DL-252 | A guard proves the page calls the field assembly rather than only that the assembly is correct | This repository has shipped guards green in exactly the broken state (DL-189) -> a formatter guarded alone passes while the rail joins raw values into one label -> the composition guard reads app.py's answer() for the per-field construction, and the served-page record reads the rendered rail |
| DL-253 | Every record the resolve rail answers over is Traktor-borne: splice groups over collection_records from the NML collections given as inputs, and a disk-scanned record never reaches a conflict group or detail_rail() | traktor_nml/splice.py:475 builds its groups from records_by_input, the per-input lists of collection_records, and hands them to group_identities (traktor_nml/splice.py:482), and diskscan feeds matching and reconnect_run instead (traktor_nml/reconnect_run.py:23, traktor_nml/commands/discover_tracks_cmd.py:12) -> the kilobits BITRATE traktor_nml/diskscan.py:59 writes has no path into a ConflictRow -> the rail formats one provenance and the bits-per-second division needs no provenance condition |
| DL-254 | The rail prints each field name as Traktor writes the attribute in the NML: ARTIST, TITLE, ALBUM, FILESIZE, PLAYTIME_FLOAT and BITRATE, one fixed mapping from the splice._TRACKED_ATTRS identifier to the printed label | splice._TRACKED_ATTRS holds lowercase python identifiers while the artboard draws the key in mono uppercase -> left to the implementer the same field could print as PLAYTIME_FLOAT, PLAYTIME or LENGTH on different rows and against the record -> the label is the XML attribute name the written file carries, uppercased, so the printed key names the thing the raw value beside it came from |
| DL-255 | The numeric presentation is the approved mockup read literally: FILESIZE to one decimal followed by MB, BITRATE rounded to a whole number followed by kbps, PLAYTIME_FLOAT as minutes then a colon then seconds truncated toward zero and zero-padded to two digits; no thousands separator is introduced anywhere and the raw string is reproduced exactly as the collection carries it | The approved mockup at the scratchpad resolve-rail-mockup.html is the only Tier 1 source carrying precision and it shows 8.1 MB, 320 kbps and 7:01 -> a plan fixing units but not precision leaves a user-visible default to the implementer, while the mockup separated raw 8,123,456 would rewrite the string the written file holds -> precision, rounding and padding come from the mockup and the raw value alone is exempt from it |
| DL-256 | This work writes into C:/codex/traktor-nml-tool-gate, a tree outside the primary working directory, for the three reconstruct-conflict fixture collections alone; no other file outside C:/codex/traktor-nml-tool is touched | The gate tree is where the served page is produced and its one conflict diverges on bitrate alone at values a Traktor collection never writes (DL-251) -> the served-page record DL-084 and DL-169 require cannot read the unit formatting or a discriminating mark without editing that fixture -> the external writes are named file by file in M-005 and bounded to the reconstruct-conflict fixture |
| DL-257 | The rail head and the new field grid go through traktor_nml/gui/wording.plural for every word a count picks, and no inline conditional on a count stands anywhere under gui/ | M-004 touches the head holding-count sentence and adds a grid drawn once per field -> an inline x if n == 1 else y is the shape tests/test_gui_wording.py forbids outside wording.py, and a count written into a sentence is what DL-215 forbids -> the count reads off the model and its word comes from wording.plural, guarded by the existing wording test over the changed file |
| DL-258 | traktor_nml/gui/app.py is read and rewritten with newline set to the empty string so its CRLF line endings survive the edit, while answer_detail.py, theme.py and every file under tests/ stay LF | app.py is the one file in the package carrying CRLF throughout -> a default-mode write converts every line ending and shows the whole file as changed, hiding the real edit -> the empty-newline write is named in the app.py intent and a guard reads the file bytes for an absence of bare LF |
| DL-259 | No work here regenerates tests/baselines/manifest.json or fixture/w002gatefix2, restores a file with git checkout, writes into build/ or dist/, installs into the system interpreter or spawns a background agent; the suite runs under C:/Users/marcu/AppData/Local/Python/pythoncore-3.14-64/python.exe | M-002 changes a structure the conflict CSV and splice_cmd report over, which is exactly the change a baseline regeneration would paper over -> a regenerated manifest would record the new output as expected and the guard that the columns are unmoved would pass in the broken state (DL-189) -> the baselines and the gate fixture w002gatefix2 are read never written, a file needing restoration is copied aside first, and every guard in this plan runs under the system interpreter |

### Rejected Alternatives

| Alternative | Why Rejected |
|---|---|
| Colour the larger filesize green | The tool has no way to know a bigger file is the better record; the user cut it outright (ref: DL-249) |
| Show only the fields that differ, as a diff | Each answer is meant to read as a record; the mark carries the difference instead (ref: DL-242) |
| Widen ConflictRow.attrs to every tracked attribute | attrs is a column of the conflict CSV and of splice_cmd's printed line, so widening it rewrites recorded output for every run (ref: DL-244) |
| Put the formatting rules in conflict_model.py | That module is the decision vocabulary a pick is recorded in; traktor_nml/gui/CLAUDE.md gives one purpose per module (ref: DL-246) |
| Mark every field, as the mockup draws it | Over the divergent subset alone every field differs and the mark says nothing; the mark earns its place only once the agreeing fields stand beside the divergent ones (ref: DL-243) |
| aggrid for the field rows | DL-079 (ref: DL-242) |

### Constraints

- C-001: DL-069: only app.py, file_picker.py and __main__.py import nicegui; every formatting rule and every difference computation lives in a nicegui-free module the suite reaches, and every CSS class and dimension lives in theme.py
- C-002: DL-079: hand-rolled ui.row/ui.element, never aggrid
- C-003: DL-148: a resolution names the record that wins, not a base-or-source token; the 'held by' line stays informational
- C-004: DL-215: a sentence naming a count reads that count off the model
- C-005: Plurals go through traktor_nml/gui/wording.plural; tests/test_gui_wording.py forbids an inline `x if n == 1 else y` anywhere under gui/ except wording.py - discharged by DL-257 and by M-004's acceptance criteria on wording.plural and the inline-conditional rule
- C-006: DL-071: a screen disagreeing with the artboard is fixed in the design first
- C-007: Every guard is proven to FAIL FIRST, its docstring carrying the specific mutation and the verbatim observed output; DL-189: beware a guard green in exactly the broken state
- C-008: app.py stays 100% CRLF (written with newline=''); theme.py and tests/ are LF - discharged by DL-258, CI-M-004-001 and CI-M-004-003
- C-009: DL-084 as amended by DL-169: the milestone closes on a served-page record in docs/ with a verdict row per surface plus structural verdicts against design/reconnect-wizard/Resolve.dc.html, its digest registered in tests/test_docs_browser_record_structure.py
- C-010: Documentation describes the code as it stands - no 'previously', 'now does', 'no longer', 'added' - and never cites a source for something it does not say, line numbers included
- C-011: tests/baselines/manifest.json and fixture/w002gatefix2 are never regenerated; no file is restored with git checkout (copy aside, restore from the copy); nothing is written into build/ or dist/, nothing is installed into the system interpreter, and no background agent is spawned - discharged by DL-259; the one authorised write outside the working directory is DL-256
- C-012: The suite runs under C:/Users/marcu/AppData/Local/Python/pythoncore-3.14-64/python.exe, not .venv - discharged by DL-259
- C-013: Out of scope: the conflict table, the bulk actions, the footer and its gating, steps 1/2/4, the /reconnect route, accessibility and keyboard work (DL-197), and any value-ranking colour

### Known Risks

- **A guard on the formatter alone passes while the rail still joins raw values into one label - the shape DL-189 names**: tests/test_gui_resolve_composition.py reads answer() for the per-field construction and asserts no call site joins candidate values, and the served-page record reads the rendered rail
- **A unit division applied twice or to the wrong base prints a number the collection does not hold**: FILESIZE is kilobytes - the calibration comment at matching.py:124-128 records the measured error of FILESIZE against bytes/1024 and _size_kb (matching.py:166-180) does no conversion because both sides already carry kilobytes - and BITRATE is bits per second (collection_textual_patch_test.nml carries values near 1000000); only Traktor-borne records reach the rail (DL-253); the raw string stands beside every formatted value, and the fixture carries realistic values so the served page reads them
- **Carrying the agreeing values changes what a run writes or reports**: The field is an addition with an empty default; the CSV columns and splice_cmd's line are guarded identical, and tests/baselines/manifest.json is not regenerated
- **A record carrying no INFO element yields empty strings and a formatter raises inside a page build**: Every formatter returns the raw string unchanged where the value does not parse, guarded on the empty string
- **One field per line makes a 400px rail taller than the answers it holds**: Accepted: the answer count is small and vertical cost is preferred to an unreadable single line; the served-page record reads the rail at its measured height

## Invisible Knowledge

### Invariants

- A rail control names the RECORD that wins, not the collection that supplied it: two collections holding identical values are one answer, and deciding it decides both (DL-148, DL-160)
- The raw value is what the written file carries, so it stays visible beside any formatted rendering
- Counts on screen are read off the model, never written into a sentence (DL-215)
- ConflictRow.attrs is the divergent set and is a column of the conflict CSV; the complete record rides beside it
- An attribute outside a group's divergent set holds one value across every member of the group, so the agreeing values belong to the group rather than to a candidate
- Traktor writes FILESIZE in kilobytes and BITRATE in bits per second; traktor_nml/diskscan.py:59 writes a bitrate in kilobits, so a disk-scanned record and a Traktor record disagree in units; the rail never sees a disk-scanned record, because splice groups over collection_records alone (DL-253), so the kilobits provenance cannot reach a formatted value

### Tradeoffs

- One field per line makes the rail taller; the rail is 400px wide and the answer count is small, so vertical cost is preferred to an unreadable single line. Given up: rail height. Accepted by the user in approving the mockup, which draws the fields stacked.
- The complete record costs a field on three structures rather than a computation in the page, which is what keeps the CSV's meaning of attrs intact. Given up: three structures widen and every construction site of them moves. Accepted by the architect under DL-244, because the alternative rewrites recorded output for every run.
- The mockup's 5px dot is kept rather than cut, because the agreeing fields standing beside the divergent ones give it something to say. Given up: the option of cutting the mark, which the architect raised as an open question after finding the dot vacuous over the divergent subset alone. Accepted by the user, who kept the dot once the rail was to carry the agreeing fields too.

## Milestones

### Milestone 1: The artboard the rail is built to

**Files**: design/reconnect-wizard/Resolve.dc.html

**Requirements**:

- The artboard draws the rail body as answer groups of labelled field rows, and names the file once, in the head

**Acceptance Criteria**:

- design/reconnect-wizard/Resolve.dc.html carries no 'The file' group
- An answer group in the artboard draws a field name, a formatted value, a raw value and a mark on the divergent rows
- No rule in the artboard colours a value by its magnitude

**Tests**:

- skip: An artboard is read by the served-page record's structural verdicts, not by a guard

#### Code Intent

- **CI-M-001-001** `design/reconnect-wizard/Resolve.dc.html`: The .det body holds answer groups only, with no 'The file' group: the head names the file. Each answer group draws one row per tracked attribute on the .cmpf three-column grid - the attribute name in the mono uppercase .k, the formatted value with the raw string beside it, and a 5px dot on the rows whose values differ across the answers. The drawn example carries a field agreeing across both answers and a field differing between them, and no value carries a ranking colour. (refs: DL-242, DL-243, DL-249, DL-250)

#### Code Changes

**CC-M-001-001** (design/reconnect-wizard/Resolve.dc.html) - implements CI-M-001-001

**Code:**

```diff

--- a/design/reconnect-wizard/Resolve.dc.html
+++ b/design/reconnect-wizard/Resolve.dc.html
@@ (stylesheet, beside .cmpf at :86-89)
 .cmpf{display:grid;grid-template-columns:60px 1fr 82px;gap:8px;font-size:12px;align-items:center;padding:5px 0;border-bottom:1px solid #22292E}
 .cmpf:last-child{border-bottom:0}
 .cmpf .k{color:#8E979E;font:500 11px/1 'IBM Plex Mono',monospace;letter-spacing:.05em;text-transform:uppercase}
 .cmpf .v{color:#D2D8DC;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
+/* The raw string the written file carries, beside the formatted value
+   rather than instead of it: a row reading 8.0 MB alone hides which
+   record wins. */
+.cmpf .r{color:#8E979E;font:400 11px/1.3 'IBM Plex Mono',monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:right}
+/* The mark on a row whose value differs across the answers. A dot and
+   nothing else: no rule here colours a value by its magnitude, since
+   the tool does not know a larger filesize is the better one. */
+.cmpf .d{width:5px;height:5px;border-radius:50%;background:#56B4E9;flex:none}
+.cmpf .kw{display:flex;align-items:center;gap:5px;min-width:0}
+.cand .f{min-width:0;display:flex;flex-direction:column;flex:1}
@@ (the .det-b body, at :214-218)
-          <div class="grp">
-            <div class="grp-h"><span class="lbl">The file</span></div>
-            <div class="cmpf"><span class="k">Path</span><span class="v mono" style="grid-column:2 / span 2">E:\Music\House\Kerri Chandler - Bar A Thym.aiff</span></div>
-          </div>
-
+          <!-- The file is named once, in .det-h's .t above. A second
+               labelled Path row under a "The file" group prints the
+               same string twice. -->
@@ (Answer 1's .cand, at :221-228)
           <div class="grp">
             <div class="grp-h"><span class="lbl">Answer 1</span><span class="kbd">1</span></div>
             <div class="cand on">
               <span class="rad" role="img" aria-label="Chosen"></span>
-              <span class="b">
-                <span class="n">Bar A Thym</span>
-                <span class="n">Kerri Chandler</span>
+              <span class="f">
+                <span class="cmpf"><span class="kw"><span class="k">TITLE</span></span><span class="v">Bar A Thym</span><span class="r"></span></span>
+                <span class="cmpf"><span class="kw"><span class="d"></span><span class="k">ARTIST</span></span><span class="v">Kerri Chandler</span><span class="r"></span></span>
+                <span class="cmpf"><span class="kw"><span class="d"></span><span class="k">BITRATE</span></span><span class="v">320 kbps</span><span class="r">320000</span></span>
+                <span class="cmpf"><span class="kw"><span class="k">FILESIZE</span></span><span class="v">8.0 MB</span><span class="r">8192</span></span>
                 <span class="m">held by collection.nml</span>
-              </span>
+              </span>
             </div>
           </div>
@@ (Answer 2's .cand, at :231-240)
           <div class="grp">
             <div class="grp-h"><span class="lbl">Answer 2</span><span class="kbd">2</span></div>
             <div class="cand">
               <span class="rad" role="img" aria-label="Not chosen"></span>
-              <span class="b">
-                <span class="n">Bar A Thym (Original Mix)</span>
-                <span class="n">Kerri Chandler feat. Jerome Sydenham</span>
+              <span class="f">
+                <span class="cmpf"><span class="kw"><span class="k">TITLE</span></span><span class="v">Bar A Thym</span><span class="r"></span></span>
+                <span class="cmpf"><span class="kw"><span class="d"></span><span class="k">ARTIST</span></span><span class="v">Kerri Chandler feat. Jerome Sydenham</span><span class="r"></span></span>
+                <span class="cmpf"><span class="kw"><span class="d"></span><span class="k">BITRATE</span></span><span class="v">128 kbps</span><span class="r">128000</span></span>
+                <span class="cmpf"><span class="kw"><span class="k">FILESIZE</span></span><span class="v">8.0 MB</span><span class="r">8192</span></span>
                 <span class="m">held by collection_2024-11-02.nml</span>
-              </span>
+              </span>
             </div>
           </div>

NOTES FOR THE IMPLEMENTER

- TITLE and FILESIZE are drawn without a dot: the artboard has to show a
  field agreeing across the answers beside one differing, or the dot on
  every row says nothing and the rule it draws cannot be read off it
  (M-001's acceptance criterion two, DL-243).
- The third column holds the raw string for the fields that have a
  formatted companion and is empty for the ones that do not, so the
  three tracks stay the three tracks .cmpf already declares and the
  values line up down the rail.
- .cand .b is left declared: the review screen's candidate cards use it.
  The rail's own column is .cand .f, which carries no gap, because
  .cmpf already carries its own vertical padding and a border between
  rows.
- No rule added here states a colour conditioned on a value: the user
  cut colouring the larger filesize green, and the reason is that the
  tool cannot know bigger is better (DL-249).

```

**Documentation:**

```diff
--- a/design/reconnect-wizard/Resolve.dc.html
+++ b/design/reconnect-wizard/Resolve.dc.html
@@ (in the comment block above the answer group)
+<!-- An answer is drawn as a record: one row per tracked attribute the
+     group carries, each holding the attribute name, what the value
+     means and the raw string the written file holds (DL-242). The mark
+     stands on a row the answers disagree on and carries no colour
+     ranking one value against another (DL-243, DL-249). The file is
+     named at the rail head alone, so the body opens with no labelled
+     Path row (DL-250). The screen is built to this artboard, which is
+     why the amendment lands here first (DL-071). -->

```


### Milestone 2: The complete record in the model

**Files**: traktor_nml/splice.py, traktor_nml/gui/conflict_model.py, tests/test_splice.py, tests/test_gui_conflict_model.py

**Requirements**:

- A conflict row carries every tracked attribute the group's records hold: the divergent ones as candidate values, the agreeing ones as the group's own pairs
- What a run writes and prints is unmoved

**Acceptance Criteria**:

- A three-answer group's agreed pairs hold exactly the tracked attributes outside its divergent set, each with the single value every member holds
- A group diverging on every tracked attribute carries no agreed pairs
- The conflict CSV's columns and splice_cmd's printed line read identically over a run carrying agreed values
- A decision re-attaches across a re-preview whose agreed pairs differ while member keys and candidates hold

**Tests**:

- file: tests/test_splice.py
- file: tests/test_gui_conflict_model.py
- normal: A three-answer group carries the agreeing tracked attributes as pairs
- normal: A projected group carries the row's agreed pairs
- edge: A group diverging on every tracked attribute carries no agreed pairs
- edge: A decision re-attaches where agreed pairs differ but member keys and candidates hold
- error: A duplicate-playlist-name row and an ambiguous-redirect row keep their shape
- error: The conflict CSV's columns and splice_cmd's printed line are unmoved

#### Code Intent

- **CI-M-002-001** `traktor_nml/splice.py`: ConflictRow carries `agreed`, a tuple of (attribute name, value) pairs in _TRACKED_ATTRS order holding every tracked attribute outside the row's divergent set, defaulting empty so the duplicate-playlist-name and ambiguous-redirect rows keep their shape. _metadata_conflict_row fills it off the members already grouped, in the pass that builds the candidates. attrs is the comma-joined divergent set and the CSV columns splice_cmd writes read identically. (refs: DL-244, DL-245)
- **CI-M-002-002** `traktor_nml/gui/conflict_model.py`: ConflictGroup and ConflictRowView carry `agreed` beside attrs, and conflict_groups projects it off the row. The re-attachment comparison is member_keys and candidates, so a group whose agreeing values are carried keeps the decision it holds. (refs: DL-244, DL-245)
- **CI-M-002-003** `tests/test_splice.py`: Guards that a three-answer group's agreed pairs hold exactly the tracked attributes outside its divergent set, each with the single value every member holds; that a group diverging on every tracked attribute carries none; and that the conflict CSV's columns and splice_cmd's printed line read identically over a run carrying agreed values. Each docstring carries the mutation applied and the verbatim pytest output observed under it. (refs: DL-244, DL-245)
- **CI-M-002-004** `tests/test_gui_conflict_model.py`: Guards that a projected group carries the row's agreed pairs, and that a decision re-attaches across a re-preview whose agreed pairs differ while member keys and candidates hold. Each docstring carries the mutation applied and the verbatim pytest output observed under it. (refs: DL-244)

#### Code Changes

**CC-M-002-001** (traktor_nml/splice.py) - implements CI-M-002-001

**Code:**

```diff

--- a/traktor_nml/splice.py
+++ b/traktor_nml/splice.py
@@ (ConflictRow, around :81-99)
     identity_key: str
     attrs: str
     resolution: str
     member_keys: frozenset[str] = frozenset()
     candidates: tuple[ConflictCandidate, ...] = ()
+    agreed: tuple[tuple[str, str], ...] = ()

    (the docstring gains, after the sentence naming candidates:)

+    agreed holds every tracked attribute OUTSIDE the divergent set, in
+    _TRACKED_ATTRS order, each paired with the single value every member
+    of the group holds for it. attrs names what the group could not
+    agree on and agreed names what it did, so the two together are the
+    whole record the group describes and a screen reading them shows a
+    record rather than a diff. It defaults empty, so a row reporting
+    something other than a metadata divergence keeps the shape it has.
@@ (_candidates, after it, around :219)
+def _agreed(
+    members: list[tuple[int, EntryRecord]], attrs: list[str]
+) -> tuple[tuple[str, str], ...]:
+    """The tracked attributes the group agrees on, as (name, value)
+    pairs in _TRACKED_ATTRS order.
+
+    Read off the members already grouped, in the same pass _candidates
+    reads them: an attribute absent from attrs holds one value across
+    every member by the way attrs was computed, so the first member's
+    value is that value and no set is built a second time.
+    """
+    divergent = set(attrs)
+    first = members[0][1]
+    return tuple(
+        (attr, str(getattr(first, attr)))
+        for attr in _TRACKED_ATTRS
+        if attr not in divergent
+    )
+
+
@@ (_metadata_conflict_row, :231-237)
     return ConflictRow(
         identity_key,
         ",".join(divergent_attrs),
         resolution,
         member_keys=frozenset(record.primary_key for _, record in members),
         candidates=_candidates(members, divergent_attrs),
+        agreed=_agreed(members, divergent_attrs),
     )

NOTES FOR THE IMPLEMENTER

- attrs stays the comma-joined divergent set and stays the third CSV
  column, so the conflict report's columns and splice_cmd's printed line
  are untouched: agreed is a field the CSV never reads.
- _agreed is called at the one place ConflictRow is built for a metadata
  divergence, so the two rows built from a literal (playlist_name,
  ambiguous_redirect) keep the empty default and conflict_model's
  NON_METADATA_ROW_ATTRS reading is unaffected.
- members is never empty where _metadata_conflict_row is called: the
  call site reached it through `len(contributing_inputs) == 1` having
  been false, so the group holds at least two members. members[0] is
  therefore indexable, and _agreed is not given an empty group.

```

**Documentation:**

```diff
--- a/traktor_nml/splice.py
+++ b/traktor_nml/splice.py
@@ (ConflictRow.agreed, beside the field)
     candidates: tuple[ConflictCandidate, ...] = ()
+    # agreed rides beside attrs rather than widening it: attrs is the
+    # third column of the conflict CSV and of the line splice_cmd
+    # prints, so a field holding the agreeing names keeps that recorded
+    # output exactly where it stands (ref: DL-244).
     agreed: tuple[tuple[str, str], ...] = ()
@@ (_agreed docstring, after its opening paragraph)
     """The tracked attributes the group agrees on, as (name, value)
     pairs in _TRACKED_ATTRS order.
+
+    Well defined because divergent_attrs names the attributes whose
+    value set across the group's members holds more than one member: an
+    attribute outside that set holds one value across every member,
+    candidates included, so the value belongs to the group rather than
+    to any one answer (ref: DL-245).

```


**CC-M-002-002** (traktor_nml/gui/conflict_model.py) - implements CI-M-002-002

**Code:**

```diff

--- a/traktor_nml/gui/conflict_model.py
+++ b/traktor_nml/gui/conflict_model.py
@@ (ConflictGroup, around :83-98)
     identity_key: str
     attrs: tuple[str, ...]
     member_keys: frozenset[str]
     candidates: tuple[ConflictCandidate, ...]
+    agreed: tuple[tuple[str, str], ...] = ()

    (the docstring gains:)

+    agreed carries the tracked attributes the group's records hold in
+    common, which the rail draws beside the divergent ones so each
+    answer reads as a record. It is not compared by re-attachment: what
+    a pick was made against is the answers on offer, and a value every
+    member agrees on is the same value whichever answer wins (DL-245).
@@ (ConflictRowView, around :101-111)
     identity_key: str
     attrs: tuple[str, ...]
     candidates: tuple[ConflictCandidate, ...]
     decision: object
+    agreed: tuple[tuple[str, str], ...] = ()
@@ (conflict_groups, around :190-196)
         groups.append(
             ConflictGroup(
                 identity_key=row.identity_key,
                 attrs=tuple(row.attrs.split(",")),
                 member_keys=row.member_keys,
                 candidates=row.candidates,
+                agreed=row.agreed,
             )
         )
@@ (ConflictDecisions.rows, around :316-324)
             ConflictRowView(
                 identity_key=group.identity_key,
                 attrs=group.attrs,
                 candidates=group.candidates,
                 decision=self.decision(group),
+                agreed=group.agreed,
             )

NOTES FOR THE IMPLEMENTER

- _Decision holds reference, member_keys and candidates, and decision()
  compares those three. agreed is deliberately absent from both: adding
  it would drop a held pick the moment a re-preview changed a value
  nobody is choosing between, which is the opposite of what DL-158's
  comparison exists to catch.
- Both dataclasses stay frozen and agreed is defaulted, so the
  positional constructions in the test suite keep working.

```

**Documentation:**

```diff
--- a/traktor_nml/gui/conflict_model.py
+++ b/traktor_nml/gui/conflict_model.py
@@ (ConflictRowView.agreed, beside the field)
     decision: object
+    # The view carries the agreeing values so the rail reads a whole
+    # record off one object, with attrs naming the divergent set
+    # alone (ref: DL-244). A pick is recorded against the answers on
+    # offer, so this field takes no part in re-attachment (ref: DL-245).
     agreed: tuple[tuple[str, str], ...] = ()

```


**CC-M-002-003** (tests/test_splice.py) - implements CI-M-002-003

**Code:**

```diff

--- a/tests/test_splice.py
+++ b/tests/test_splice.py
@@ (new guards, beside the existing candidate guards)
+def test_a_three_answer_group_carries_the_agreeing_tracked_attributes():
+    """A metadata-diverging group reports the tracked attributes it
+    agrees on as (name, value) pairs in _TRACKED_ATTRS order, each
+    holding the single value every member carries.
+
+    Read against a group of three answers so the reading is not
+    satisfied by a two-member group where every tracked attribute is
+    either divergent or identical by coincidence.
+
+    Mutation: `if attr not in divergent` in splice._agreed was changed
+    to `if attr in divergent` and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... three inputs holding one file at one location, diverging on
+    bitrate alone and agreeing on artist, title, album, filesize and
+    playtime_float ...
+    row = ... the one metadata conflict row ...
+    assert row.attrs == "bitrate"
+    assert row.agreed == (
+        ("artist", "A"),
+        ("title", "One"),
+        ("album", ""),
+        ("filesize", "8192"),
+        ("playtime_float", "100.0"),
+    )
+
+
+def test_a_group_diverging_on_every_tracked_attribute_carries_no_agreed_pairs():
+    """agreed is the complement of attrs, so a group that agrees on
+    nothing carries none - the empty tuple rather than a pair holding an
+    arbitrary member's value.
+
+    Mutation: `divergent = set(attrs)` in splice._agreed was changed to
+    `divergent = set()` and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... two inputs whose one shared location differs on all six ...
+    assert set(row.attrs.split(",")) == set(splice._TRACKED_ATTRS)
+    assert row.agreed == ()
+
+
+def test_the_conflict_report_and_the_printed_line_are_unmoved_by_agreed():
+    """The CSV conflict report's columns and splice_cmd's printed line
+    read identically over a run whose rows carry agreed pairs: agreed is
+    a field the report never reads, and attrs is still the comma-joined
+    divergent set.
+
+    This is the reading that stays true in the broken state where agreed
+    was folded into attrs - the shape that would make the third CSV
+    column name fields the group agreed on (DL-189).
+
+    Mutation: `",".join(divergent_attrs)` in _metadata_conflict_row was
+    changed to `",".join(divergent_attrs + [a for a, _ in agreed])` and
+    this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... assert the header row and the one data row of the written CSV,
+    and the splice_cmd line, against the strings they already carry ...
+
+
+def test_a_duplicate_playlist_name_row_and_an_ambiguous_redirect_row_keep_their_shape():
+    """The two rows built from a literal name no identity group, and
+    carry agreed empty rather than a pair read off members they do not
+    have.
+
+    Mutation: ConflictRow.agreed's default was removed, making it
+    required, and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... both rows ... assert row.agreed == () and row.member_keys == frozenset()

NOTES FOR THE IMPLEMENTER

- Each `<PASTE ...>` is filled by running the mutation, copying what
  pytest printed, and reverting - the docstring convention this suite
  holds, and the thing that makes the guard proven to fail first.
- The existing splice guards construct EntryRecords through the module's
  own fixtures; these follow the same route rather than building records
  by hand, so a field added to EntryRecord does not break them.

```

**Documentation:**

```diff
--- a/tests/test_splice.py
+++ b/tests/test_splice.py
@@ (above the new agreed guards)
+# The agreeing values are a field beside attrs, not a widening of it
+# (ref: DL-244), and they are well defined because an attribute outside
+# the divergent set holds one value across every member of the group
+# (ref: DL-245). The three-answer group is what proves the second
+# reading rather than assuming it; the CSV guard is what holds the first
+# where a fold into attrs would otherwise pass unseen (ref: DL-189).

```


**CC-M-002-004** (tests/test_gui_conflict_model.py) - implements CI-M-002-004

**Code:**

```diff

--- a/tests/test_gui_conflict_model.py
+++ b/tests/test_gui_conflict_model.py
@@ (new guards, beside the existing projection and re-attachment guards)
+def test_a_projected_group_carries_the_rows_agreed_pairs():
+    """conflict_groups projects agreed off the row the run produced,
+    and rows() carries it onto the view, so what the rail draws is what
+    splice derived rather than anything this module recomputes.
+
+    Mutation: `agreed=row.agreed` was deleted from the ConflictGroup
+    construction in conflict_groups and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    row = ConflictRow(
+        "identity", "bitrate", None,
+        member_keys=frozenset({"C:/:Music/:one.mp3"}),
+        candidates=(ConflictCandidate(("320000",), ((0, "C:/:Music/:one.mp3"),)),),
+        agreed=(("artist", "A"), ("title", "One")),
+    )
+    group = conflict_model.conflict_groups([row])[0]
+    assert group.agreed == (("artist", "A"), ("title", "One"))
+    view = conflict_model.ConflictDecisions().rows([group])[0]
+    assert view.agreed == (("artist", "A"), ("title", "One"))
+
+
+def test_a_decision_re_attaches_where_only_the_agreed_pairs_differ():
+    """A pick stands across a re-preview whose agreed values moved while
+    the member keys and the candidates held: a value every member agrees
+    on is not one of the answers, so it is not what the pick was made
+    against (DL-158, DL-245).
+
+    This is the guard that fails the moment agreed is folded into the
+    _Decision comparison, which is the shape that would silently drop
+    every pick on a re-preview.
+
+    Mutation: `agreed` was added to _Decision and to the equality
+    decision() tests, and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... build a group, resolve it, rebuild the identical group with a
+    different agreed tuple, and assert decision() is the reference
+    rather than UNDECIDED ...

NOTES FOR THE IMPLEMENTER

- The existing re-attachment guards in this file already cover the two
  directions that MUST drop a pick (member keys moved, candidates
  moved); this adds the one that must NOT.

```

**Documentation:**

```diff
--- a/tests/test_gui_conflict_model.py
+++ b/tests/test_gui_conflict_model.py
@@ (above the new agreed guards)
+# agreed rides from ConflictRow through ConflictGroup to
+# ConflictRowView so the rail reads a whole record off the view
+# (ref: DL-244). It takes no part in what a pick is compared against:
+# a value every member agrees on is the same value whichever answer
+# wins, and comparing it would drop a held pick on a re-preview that
+# changed something nobody is choosing between (ref: DL-245).

```


### Milestone 3: The field rows and their formatting

**Files**: traktor_nml/gui/answer_detail.py, tests/test_gui_answer_detail.py

**Requirements**:

- One nicegui-free module returns the rail's field rows, their labels, their formatted values and their marks

**Acceptance Criteria**:

- The fields come back in splice._TRACKED_ATTRS order
- Every field prints its NML attribute name in uppercase - ARTIST TITLE ALBUM FILESIZE PLAYTIME_FLOAT BITRATE
- A field agreeing across the answers carries no mark and a diverging one does
- A kilobyte filesize renders under one division by 1024 to one decimal and a bits-per-second bitrate under one division by 1000 rounded whole
- Seconds render as minutes and seconds zero-padded to two digits and no formatted value carries a thousands separator
- An empty or non-numeric value returns no formatted companion
- The module imports no nicegui and runs under the system interpreter

**Tests**:

- file: tests/test_gui_answer_detail.py
- normal: Fields come back in _TRACKED_ATTRS order under their uppercase NML labels
- normal: A kilobyte filesize renders as megabytes to one decimal and a bits-per-second bitrate as whole kilobits
- normal: Seconds render as minutes and zero-padded seconds
- edge: A field agreeing across the answers carries no mark while a diverging one does
- edge: A one-answer group and a six-way divergence
- edge: No formatted value carries a thousands separator and the raw string comes back as given
- error: An empty value and a non-numeric value return no formatted companion

#### Code Intent

- **CI-M-003-001** `traktor_nml/gui/answer_detail.py`: AnswerField - the attribute name, the label the rail prints, the raw value, the formatted value or None, and whether the field differs across the answers - and answer_fields(attrs, agreed, candidate), which returns one field per name in splice._TRACKED_ATTRS the group carries, in that order, marking a field as differing exactly where its name stands in attrs. The label is the fixed mapping of the _TRACKED_ATTRS identifier to the NML attribute name in uppercase: ARTIST, TITLE, ALBUM, FILESIZE, PLAYTIME_FLOAT, BITRATE. format_value(attr, raw) renders filesize as megabytes off a kilobyte count to one decimal followed by MB, playtime_float as minutes then a colon then seconds truncated toward zero and zero-padded to two digits, and bitrate as kilobits per second off a bits-per-second count rounded to a whole number followed by kbps - one division each, with no provenance branch, since every record the rail answers over is Traktor-borne. It introduces no thousands separator and returns None for artist, title and album and for any value that is empty or does not parse. Imports no nicegui. (refs: DL-243, DL-246, DL-247, DL-248, DL-253, DL-254, DL-255)
- **CI-M-003-002** `tests/test_gui_answer_detail.py`: Guards the field order against _TRACKED_ATTRS, the printed label of every tracked attribute against its uppercase NML name, that a field agreeing across the answers carries no mark while a diverging one does, that a kilobyte filesize renders under one division by 1024 to one decimal and a bits-per-second bitrate under one division by 1000 rounded whole, that seconds render as minutes and zero-padded seconds, that no formatted value carries a thousands separator and the raw string comes back exactly as given, and that an empty or non-numeric value returns no formatted companion. Each docstring carries the mutation applied and the verbatim pytest output observed under it. (refs: DL-243, DL-246, DL-247, DL-254, DL-255)

#### Code Changes

**CC-M-003-001** (traktor_nml/gui/answer_detail.py) - implements CI-M-003-001

**Code:**

```diff

--- /dev/null
+++ b/traktor_nml/gui/answer_detail.py
@@ (new module, LF endings, imports no nicegui)
+"""The rows one answer in the resolve step's detail rail draws.
+
+An answer is a record, not a diff. The rail shows every tracked
+attribute the group's records carry - the ones the answers disagree on,
+read off the candidate, and the ones they agree on, read off the group -
+so the operator picks by reading a record rather than by reading a list
+of what is missing from one.
+
+Two values per field, not one. The raw string is what the written file
+carries and is what tells the answers apart when they differ by a digit;
+the formatted one is what a filesize in kilobytes, a bitrate in bits per
+second and a playtime in seconds mean. A rail showing only the formatted
+value would hide which record wins, and one showing only the raw value
+is the screen this module exists to replace.
+
+Imports splice for the attribute order alone and no nicegui, so the
+suite reaches every rule here under the system interpreter (DL-069).
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Optional
+
+from ..splice import _TRACKED_ATTRS
+
+# The NML attribute each tracked identifier names, which is the word the
+# rail prints. The identifiers are Python attribute names on EntryRecord
+# and two of them - playtime_float, filesize - are not what the file
+# calls them read aloud; the operator is looking at a Traktor
+# collection, so the label is the collection's own word, uppercase, as
+# Resolve.dc.html:88's .cmpf .k draws it.
+LABELS = {
+    "artist": "ARTIST",
+    "title": "TITLE",
+    "album": "ALBUM",
+    "filesize": "FILESIZE",
+    "playtime_float": "PLAYTIME_FLOAT",
+    "bitrate": "BITRATE",
+}
+
+
+@dataclass(frozen=True)
+class AnswerField:
+    """One row of one answer.
+
+    formatted is None where the field has no second reading - artist,
+    title and album are already what they say - and where the value does
+    not parse, which includes the empty string a record with no INFO
+    element carries. differs says whether the answers disagree on this
+    field, which is what the rail marks; it is never a judgement about
+    which value is better.
+    """
+
+    attr: str
+    label: str
+    raw: str
+    formatted: Optional[str]
+    differs: bool
+
+
+def format_value(attr: str, raw: str) -> Optional[str]:
+    """The second reading of one raw attribute value, or None.
+
+    filesize is Traktor's own kilobyte count, not a byte count -
+    matching.py compares FILESIZE against a file's bytes divided by 1024
+    - so megabytes is ONE division by 1024. A second division would put
+    an 8 MB file on screen as 0.0 MB.
+
+    playtime_float is seconds as a decimal string and reads as minutes
+    and seconds, the seconds truncated toward zero and zero-padded, so
+    99.6 seconds is 1:39 rather than 1:99 or 1:40.
+
+    bitrate is bits per second in a Traktor collection, so kilobits is
+    one division by 1000, rounded to a whole number.
+
+    No thousands separator is introduced anywhere: the raw string beside
+    the formatted one is the file's own text and a grouped copy of it
+    reads as a third value.
+
+    Every record the rail answers over came out of a Traktor
+    collection, so there is no provenance branch: one unit reading per
+    attribute, stated here once.
+    """
+    if attr not in ("filesize", "playtime_float", "bitrate"):
+        return None
+    try:
+        number = float(raw)
+    except (TypeError, ValueError):
+        return None
+    if attr == "filesize":
+        return f"{number / 1024:.1f} MB"
+    if attr == "bitrate":
+        return f"{round(number / 1000)} kbps"
+    minutes, seconds = divmod(int(number), 60)
+    return f"{minutes}:{seconds:02d}"
+
+
+def answer_fields(
+    attrs: tuple[str, ...],
+    agreed: tuple[tuple[str, str], ...],
+    candidate,
+) -> tuple[AnswerField, ...]:
+    """One field per tracked attribute the group carries, in
+    _TRACKED_ATTRS order.
+
+    attrs names the attributes the answers disagree on and is
+    index-aligned with candidate.values; agreed pairs the rest with the
+    single value every member holds. A field is marked as differing
+    exactly where its name stands in attrs, so the mark says "the
+    answers disagree here" and nothing about which one to take.
+
+    The order is _TRACKED_ATTRS' own rather than attrs-then-agreed, so
+    one answer's rows line up against the next answer's rows down the
+    rail. An attribute in neither is not a field the group carries and
+    is left out.
+    """
+    divergent = dict(zip(attrs, candidate.values))
+    settled = dict(agreed)
+    fields = []
+    for attr in _TRACKED_ATTRS:
+        if attr in divergent:
+            raw, differs = divergent[attr], True
+        elif attr in settled:
+            raw, differs = settled[attr], False
+        else:
+            continue
+        fields.append(
+            AnswerField(
+                attr=attr,
+                label=LABELS[attr],
+                raw=raw,
+                formatted=format_value(attr, raw),
+                differs=differs,
+            )
+        )
+    return tuple(fields)

NOTES FOR THE IMPLEMENTER

- `from ..splice import _TRACKED_ATTRS` reaches a private name across
  modules. The alternative - a second copy of the six names here - is a
  list that drifts from the one splice computes divergence against, and
  the field order on screen would then stop being the model's order.
  State the choice in the module docstring rather than quietly copying.
- `round()` is banker's rounding: 128500 bits reads 128 kbps, not 129.
  That is acceptable and worth a test case rather than a workaround; no
  screen here is arithmetic anyone recomputes.
- LABELS is a dict keyed by every name in _TRACKED_ATTRS. A tracked
  attribute added to splice without a label here raises KeyError at the
  call site rather than drawing a blank key, which is the failure that
  is loud rather than silent.

```

**Documentation:**

```diff
--- a/traktor_nml/gui/answer_detail.py
+++ b/traktor_nml/gui/answer_detail.py
@@ (module docstring, before the closing line)
     Imports splice for the attribute order alone and no nicegui, so the
     suite reaches every rule here under the system interpreter (DL-069).
+
+    The module stands apart from conflict_model, which is the vocabulary
+    a pick is recorded in: a display formatting rule there would give
+    that module a second purpose (ref: DL-246). Every field row, its
+    label, its formatted value and its mark stand here and app.py only
+    places them.
+
+    _TRACKED_ATTRS is imported rather than copied: a second list of the
+    six names drifts from the one splice computes divergence against,
+    and the field order on screen is the model's order.
     """
@@ (LABELS, beside the mapping)
+# One fixed mapping so the same attribute cannot print as PLAYTIME_FLOAT
+# on one row and LENGTH on another; the label is the XML attribute name
+# the written file carries, uppercased (ref: DL-254). A tracked
+# attribute that splice carries without a label here raises KeyError at the
+# call site rather than drawing a blank key.
 LABELS = {
@@ (AnswerField docstring, after its closing sentence)
     differs says whether the answers disagree on this field, which is
     what the rail marks; it is never a judgement about which value is
     better.
+
+    No colour ranks one value against another anywhere this dataclass is
+    drawn: the tool cannot know that a larger filesize or a higher
+    bitrate is the better record, so difference is marked and never
+    ranked (ref: DL-249).
     """
@@ (format_value docstring, after the unit paragraphs)
     Every record the rail answers over came out of a Traktor
     collection, so there is no provenance branch: one unit reading per
     attribute, stated here once.
+
+    That is a property of the model rather than an assumption: splice
+    groups over the collection_records of the NML inputs, and a
+    disk-scanned record - whose BITRATE diskscan writes in kilobits -
+    reaches matching and reconnect_run instead, never a conflict group
+    (ref: DL-253).
+
+    The precision is the approved design read literally: one decimal on
+    MB, a whole number on kbps, and seconds zero-padded to two digits
+    (ref: DL-255).
+
+    Returning None for a value that does not parse covers the empty
+    string a record with no INFO element carries: the raw value then
+    prints as itself with no formatted companion, rather than a division
+    raising inside a page build (ref: DL-248).
     """
@@ (answer_fields docstring, after its second paragraph)
     A field is marked as differing exactly where its name stands in
     attrs, so the mark says "the answers disagree here" and nothing
     about which one to take.
+
+    The membership test is the whole rule: attrs is the set
+    splice computed divergence into, so no second divergence
+    computation exists here to disagree with the first (ref: DL-243).
+    Both sources together are the complete record the rail draws - the
+    divergent values off the candidate, the agreeing ones off the group
+    (ref: DL-242).

```


**CC-M-003-002** (tests/test_gui_answer_detail.py) - implements CI-M-003-002

**Code:**

```diff

--- /dev/null
+++ b/tests/test_gui_answer_detail.py
@@ (new file, LF endings)
+"""Guards traktor_nml/gui/answer_detail.py: the fields one answer draws,
+their labels, their formatted companions and their marks.
+
+Every reading here is of the module's return value under the system
+interpreter, which has no nicegui. What it cannot hold is that the rail
+calls it - a formatter guarded alone while the screen still joins the
+values into one label is the guard green in exactly the broken state
+this change exists to end (DL-189). That reading is
+tests/test_gui_resolve_composition.py's and the served-page record's.
+
+Each guard records the mutation applied to make it fail and the verbatim
+output observed under that mutation.
+"""
+
+from __future__ import annotations
+
+from traktor_nml.gui import answer_detail
+from traktor_nml.splice import ConflictCandidate, _TRACKED_ATTRS
+
+
+def test_the_fields_come_back_in_tracked_attrs_order_under_their_nml_labels():
+    """The rows are ordered by splice._TRACKED_ATTRS, not by attrs then
+    agreed, so one answer's rows stand against the next answer's rows.
+    Every label is the NML attribute name in uppercase.
+
+    Mutation: the loop in answer_fields was changed to iterate
+    `list(divergent) + list(settled)` and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... a group diverging on bitrate and title, agreeing on the rest ...
+    assert [f.attr for f in fields] == list(_TRACKED_ATTRS)
+    assert [f.label for f in fields] == [
+        "ARTIST", "TITLE", "ALBUM", "FILESIZE", "PLAYTIME_FLOAT", "BITRATE",
+    ]
+
+
+def test_a_kilobyte_filesize_and_a_bits_per_second_bitrate_read_once_divided():
+    """FILESIZE is Traktor's kilobyte count, so 8192 is 8.0 MB under one
+    division by 1024; a second division would put it on screen as 0.0
+    MB. BITRATE is bits per second, so 320000 is 320 kbps under one
+    division by 1000.
+
+    Mutation: `number / 1024` was changed to `number / 1024 / 1024` and
+    this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    assert answer_detail.format_value("filesize", "8192") == "8.0 MB"
+    assert answer_detail.format_value("bitrate", "320000") == "320 kbps"
+
+
+def test_seconds_read_as_minutes_and_zero_padded_seconds():
+    """99.6 seconds is 1:39 - the seconds truncated toward zero and
+    padded to two digits, so no row reads 1:9 or 1:99.
+
+    Mutation: `f"{seconds:02d}"` was changed to `f"{seconds}"` and this
+    guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    assert answer_detail.format_value("playtime_float", "99.6") == "1:39"
+    assert answer_detail.format_value("playtime_float", "100.0") == "1:40"
+    assert answer_detail.format_value("playtime_float", "9.0") == "0:09"
+
+
+def test_a_field_the_answers_agree_on_carries_no_mark_and_a_diverging_one_does():
+    """The mark says the answers disagree on this field. A field read
+    off agreed carries none, which is what keeps the mark from standing
+    on every row and saying nothing.
+
+    Mutation: `raw, differs = settled[attr], False` was changed to
+    `raw, differs = settled[attr], True` and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... assert {f.attr: f.differs for f in fields} names exactly the
+    attrs tuple as True and every agreed name as False ...
+
+
+def test_a_one_answer_group_and_a_six_way_divergence():
+    """A group carrying no agreed pairs draws six marked rows; a group
+    whose one answer diverges on one attribute draws that row marked and
+    five unmarked. Neither drops a field the group carries.
+
+    Mutation: `for attr in _TRACKED_ATTRS` was changed to `for attr in
+    attrs` and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... both shapes ...
+
+
+def test_no_formatted_value_carries_a_thousands_separator_and_raw_is_verbatim():
+    """The raw string comes back exactly as given, and no formatted
+    value introduces a separator: a grouped copy of the raw digits beside
+    the raw digits reads as a third value.
+
+    Mutation: `f"{round(number / 1000)} kbps"` was changed to
+    `f"{round(number / 1000):,} kbps"` and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... assert "," not in every formatted value over a large filesize,
+    a large bitrate and a long playtime, and that f.raw is the string
+    the candidate carried ...
+
+
+def test_an_empty_value_and_a_non_numeric_value_return_no_formatted_companion():
+    """A record with no INFO element carries "" for filesize, bitrate
+    and playtime_float (model.py), and the rail draws that record. An
+    empty or unparseable value falls back to the raw string alone rather
+    than raising or printing 0.0 MB.
+
+    Mutation: the `except (TypeError, ValueError): return None` arm was
+    deleted from format_value and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    assert answer_detail.format_value("filesize", "") is None
+    assert answer_detail.format_value("bitrate", "unknown") is None
+    assert answer_detail.format_value("playtime_float", "") is None
+    assert answer_detail.format_value("artist", "A") is None
+
+
+def test_the_module_imports_no_nicegui():
+    """The rule DL-069 states, read here as well as in the boundary
+    sweep, because this module is the one a formatting change is most
+    likely to be written into a nicegui call from.
+
+    Mutation: `import nicegui` was appended to answer_detail.py and this
+    guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... an AST walk over the module source ...

NOTES FOR THE IMPLEMENTER

- ConflictCandidate is constructed directly here rather than through a
  splice run: the unit under guard takes attrs, agreed and a candidate,
  and a run would make these guards depend on grouping.
- tests/test_gui_view_boundary.py already sweeps every module in the
  package for a framework import, so the last guard is a second reading
  of the same rule at the place it matters, not the only one.

```

**Documentation:**

```diff
--- a/tests/test_gui_answer_detail.py
+++ b/tests/test_gui_answer_detail.py
@@ (above the unit and parsing guards)
+# The units are the collection's own: FILESIZE is Traktor's kilobyte
+# count and BITRATE is bits per second, so each reading is one division
+# and the precision is the approved design read literally (ref: DL-247,
+# DL-255). There is no provenance branch to guard, because a
+# disk-scanned record never reaches a conflict group (ref: DL-253).
+# The empty string a record with no INFO element carries prints as
+# itself with no formatted companion (ref: DL-248), and the mark is a
+# membership test against attrs rather than a second divergence
+# computation (ref: DL-243).

```


### Milestone 4: The rail draws the records

**Files**: traktor_nml/gui/app.py, traktor_nml/gui/theme.py, tests/test_gui_resolve_composition.py, tests/test_gui_resolve_sheet.py

**Requirements**:

- The rail draws one row per field inside the control that picks the answer, and the sheet declares every class it names

**Acceptance Criteria**:

- answer() constructs one field row per field from answer_detail
- No call site joins candidate values into a single label
- Every field class the rail names is declared by the sheet and no rail rule colours a value by its magnitude
- Neither the head nor the new field grid writes a count into a sentence - every count is read off the model and its word comes from wording.plural
- No inline conditional on a count stands under gui/ outside wording.py
- app.py is 100% CRLF - written with newline set to the empty string and guarded for the absence of a bare LF byte

**Tests**:

- file: tests/test_gui_resolve_composition.py
- file: tests/test_gui_resolve_sheet.py
- normal: answer() constructs one field row per field from answer_detail
- normal: Every field class the rail names is declared by the sheet
- edge: The head names the file once and reads its holding count off the model
- edge: The field grid introduces no count written into a sentence
- error: No call site joins candidate values into one label
- error: No rail rule colours a value by its magnitude
- error: app.py carries no bare LF byte
- error: tests/test_gui_wording.py finds no inline count conditional under gui/

#### Code Intent

- **CI-M-004-001** `traktor_nml/gui/app.py`: answer() draws the control as one row per AnswerField from answer_detail.answer_fields - the field label, the formatted value where there is one, the raw value in mono beside it, and the difference mark where the field differs - in place of a label joining the values. The field block is the clickable control that picks the answer, and the collections holding it read under the fields. detail_rail()'s head keeps the identity key and the holding count read off the model, its word taken from wording.plural, and neither the head nor the new grid writes a count into a sentence or carries an inline conditional on a count. The file is rewritten with newline set to the empty string so its CRLF endings survive. (refs: DL-242, DL-243, DL-246, DL-252, DL-257, DL-258)
- **CI-M-004-002** `traktor_nml/gui/theme.py`: The sheet declares the rail's field grid: a three-column row mirroring Resolve.dc.html's .cmpf, the mono uppercase field key, the raw value's faint mono treatment and the difference mark's dimensions, as tokens beside the wizard-answer rules. No rule colours a value by its magnitude. (refs: DL-242, DL-249)
- **CI-M-004-003** `tests/test_gui_resolve_composition.py`: Guards that answer() constructs one field row per field from answer_detail and names the field classes, that no call site joins candidate values into a single label - the reading that stays true in the broken state where the formatter alone is guarded - that neither the head nor the field grid writes a count into a sentence rather than reading it off the model (the rule the constraint DL-215 carries), and that app.py carries no bare LF byte, which is the reading that fails the moment the file is rewritten without the empty newline argument. Each docstring carries the mutation applied and the verbatim pytest output observed under it. (refs: DL-252, DL-257, DL-258)
- **CI-M-004-004** `tests/test_gui_resolve_sheet.py`: Guards that every field class the rail names is declared by the sheet, and that no rail rule states a colour conditioned on a value's magnitude. (refs: DL-249, DL-252)

#### Code Changes

**CC-M-004-001** (traktor_nml/gui/app.py) - implements CI-M-004-001

**Code:**

```diff

--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ -52,6 +52,8 @@ (the gui module imports, one module per line)
 from . import collection_summary
 from . import conflict_model
+from . import answer_detail
 from . import navigation
 from . import reconstruct_report
 from . import reconstruct_steps
 from . import review_model
 # theme.py is the only source for a colour or size literal in this module (DL-078).
 from . import wizard_state
+from . import wording
 from .file_picker import pick_file_or_folder
 from .wizard_state import WizardState

@@ -2385,10 +2385,20 @@ def detail_rail(views) -> None:
                             holding = len(
                                 {
                                     input_index
                                     for candidate in view.candidates
                                     for input_index, _ in candidate.members
                                 }
                             )
-                            ui.label(
-                                f"{holding} collections hold this file with "
-                                "different values. Pick the one that "
-                                "supplies them."
-                            ).classes("wizard-body-12 wizard-dim")
+                            # The word the count picks comes from
+                            # wording.plural like every other
+                            # count-bearing sentence in this package,
+                            # rather than standing flat on the reasoning
+                            # that a group held by one collection is not
+                            # a conflict: that reasoning is a property of
+                            # the model the sentence would then be
+                            # silently relying on, and an inline
+                            # conditional on a count is the shape
+                            # tests/test_gui_wording.py forbids under
+                            # gui/ (DL-215, DL-257).
+                            ui.label(
+                                f"{holding} "
+                                + wording.plural(
+                                    holding,
+                                    "collection holds",
+                                    "collections hold",
+                                )
+                                + " this file with different values. "
+                                "Pick the one that supplies them."
+                            ).classes("wizard-body-12 wizard-dim")

@@ -2478,32 +2478,52 @@ def answer(group, view, position: int, candidate) -> None:
+                def chosen_marker(chosen: bool) -> None:
+                    """The dot that says which answer the group holds.
+
+                    Its own function so that answer() reads as the shape
+                    of one answer rather than as the drawing of every
+                    part of it: the marker, the field rows and the
+                    control each stand alone and answer() stays under
+                    the size and nesting this package holds a function
+                    to.
+                    """
+                    with ui.element("span").classes(
+                        "wizard-answer-marker"
+                    ).props(
+                        f'role="img" aria-label='
+                        f'"{"Chosen" if chosen else "Not chosen"}"'
+                    ):
+                        if chosen:
+                            ui.element("span").classes("wizard-answer-dot")
+
+                def field_row(field) -> None:
+                    """One tracked attribute of one answer: its name,
+                    what its value means, and the raw string the written
+                    file will hold.
+
+                    What a field is called, how its value reads and
+                    whether it carries the difference mark are all
+                    decided in answer_detail, which imports no nicegui,
+                    so the suite reaches every one of them and this
+                    function only places them (DL-069, DL-246).
+                    """
+                    with ui.element("div").classes("wizard-answer-field"):
+                        with ui.element("span").classes(
+                            "wizard-answer-field-key"
+                        ):
+                            if field.differs:
+                                ui.element("span").classes(
+                                    "wizard-answer-field-mark"
+                                )
+                            ui.label(field.label).classes(
+                                "font-mono wizard-faint"
+                            )
+                        ui.label(field.formatted or field.raw).classes(
+                            "wizard-answer-field-value wizard-body-12 "
+                            "wizard-subtle-5"
+                        )
+                        # The raw string stands beside the formatted one
+                        # rather than instead of it: what the written
+                        # file carries is what tells two answers apart
+                        # when they differ by a digit. A field with no
+                        # formatted companion has already printed its raw
+                        # value in the cell above, so this one is empty
+                        # and the three tracks hold (DL-243).
+                        ui.label(
+                            field.raw if field.formatted else ""
+                        ).classes(
+                            "wizard-answer-field-raw font-mono "
+                            "wizard-body-11 wizard-faint"
+                        )
+
+                def answer_control(group, view, candidate, reference,
+                                   supplied_by: str) -> None:
+                    """The control that picks this answer: the record,
+                    drawn row by row, with the collections holding it
+                    under it.
+
+                    The field block is the control, so the thing the
+                    operator points at is the record they are choosing
+                    and the "held by ..." line reads as the
+                    informational line it is rather than as the thing
+                    being picked (DL-148, DL-257).
+                    """
+                    with ui.button(
+                        on_click=(
+                            lambda _e=None, at=group, named=reference:
+                            pick(at, named)
+                        ),
+                        color=None,
+                    ).classes("wizard-control wizard-answer-fields"):
+                        for field in answer_detail.answer_fields(
+                            view.attrs, view.agreed, candidate
+                        ):
+                            field_row(field)
+                        ui.label(f"held by {supplied_by}").classes(
+                            "wizard-answer-holders wizard-body-11 "
+                            "wizard-faint"
+                        )
+
                 def answer(group, view, position: int, candidate) -> None:
-                    """One control per distinct answer, carrying the
-                    digit that picks it and the values it supplies. The
-                    decision the view holds is compared against this
-                    candidate's own reference, so the chosen answer alone
-                    carries the chosen class and this module holds no
-                    reading of what a decision means."""
+                    """One control per distinct answer, carrying the
+                    digit that picks it and the record it supplies.
+
+                    The record, not a joined line of values: the rail
+                    draws one row per tracked attribute the group
+                    carries, each naming the attribute, what its value
+                    means and the raw string the written file will hold,
+                    so the operator tells the answers apart by reading
+                    them (DL-242, DL-243).
+
+                    The decision the view holds is compared against this
+                    candidate's own reference, so the chosen answer alone
+                    carries the chosen class and this module holds no
+                    reading of what a decision means."""
                     reference = conflict_model.candidate_reference(candidate)
                     chosen = view.decision == reference
                     with ui.element("div").classes("wizard-answer-group"):
                         with ui.element("div").classes("wizard-answer-group-head"):
                             ui.label(f"Answer {position}").classes("wizard-label")
                             ui.label(str(position)).classes("wizard-kbd")
                         classes = "wizard-answer"
                         if chosen:
                             classes = "wizard-answer wizard-answer-chosen"
                         supplied_by = ", ".join(
                             labels[index] for index, _ in candidate.members
                         )
                         with ui.element("div").classes(add=classes):
-                            with ui.element("span").classes(
-                                "wizard-answer-marker"
-                            ).props(
-                                f'role="img" aria-label='
-                                f'"{"Chosen" if chosen else "Not chosen"}"'
-                            ):
-                                if chosen:
-                                    ui.element("span").classes("wizard-answer-dot")
-                            ui.button(
-                                f"{supplied_by} {' | '.join(candidate.values)}",
-                                on_click=(
-                                    lambda _e=None, at=group, named=reference:
-                                    pick(at, named)
-                                ),
-                                color=None,
-                            ).classes(
-                                "wizard-control font-mono wizard-body-11-5 "
-                                "wizard-subtle-5"
-                            )
+                            chosen_marker(chosen)
+                            answer_control(
+                                group, view, candidate, reference, supplied_by
+                            )

NOTES FOR THE IMPLEMENTER

- answer() stays a shape rather than a drawing: chosen_marker(),
  field_row() and answer_control() are siblings of answer() in the same
  enclosing scope, so each stays under 50 lines and none nests past
  three levels. field_row() is the deepest at three (div > span > if).
- The rail head's sentence is settled here rather than left open: the
  word goes through wording.plural(holding, "collection holds",
  "collections hold"), which is what DL-257 states and what
  tests/test_gui_wording.py enforces. The count itself is still read off
  the group's candidates and is never written into the sentence
  (DL-215).
- `from . import wording` and `from . import answer_detail` join the
  existing one-module-per-line `from . import` block; there is no
  comma-joined import form in this file.
- app.py is 100% CRLF. Whatever writes this file passes newline="" so
  the endings survive; tests/test_gui_line_endings.py already guards it
  and the new guard in test_gui_resolve_composition.py reads it again.
- `supplied_by` is consumed by the "held by ..." label only. It is still
  built from `labels[index]`, so the bulk strip's reading of `labels` is
  untouched.
- No class string or dimension is written here beyond a class NAME:
  every width, colour and gap belongs to theme.py (DL-069).

```

**Documentation:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ (module header, below the module docstring)
+# This file carries CRLF line endings throughout, alone in the
+# package. Reading and rewriting it with newline set to the empty
+# string keeps those endings intact, so a diff shows the edit rather
+# than every line in the file; answer_detail.py, theme.py and the
+# files under tests/ are LF (ref: DL-258).
@@ (detail_rail, above the identity-key label at the rail head)
+                            # The head is the one place the file is
+                            # named. The rail carries no second labelled
+                            # Path row, which in a 400px rail would
+                            # print the same string twice (ref: DL-250).
@@ (answer_control docstring, after its closing sentence)
                     operator points at is the record they are choosing
                     and the "held by ..." line reads as the
                     informational line it is rather than as the thing
                     being picked (DL-148, DL-257).
+
+                    What is picked is the record, not the collection
+                    that supplied it: two collections holding identical
+                    values are one answer, and deciding it decides both.
+
+                    The rows are hand-built ui.element and ui.label, as
+                    every table-shaped surface in this package is
+                    (ref: DL-079).
                     """

```


**CC-M-004-002** (traktor_nml/gui/theme.py) - implements CI-M-004-002

**Code:**

```diff

--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ (constants, beside ANSWER_MARKER_BORDER at :285)
+# Resolve.dc.html:86's .cmpf - the field row's three tracks: the
+# attribute name, the value, and the raw string the file carries. The
+# key track is fixed so every answer's keys align down the rail; the
+# value takes what is left; the raw track is fixed so the strings the
+# operator compares stand at one edge.
+ANSWER_FIELD_KEY_TRACK = "60px"
+ANSWER_FIELD_RAW_TRACK = "82px"
+# Resolve.dc.html's mark on a row whose value differs across the
+# answers. Smaller than ANSWER_MARKER_DOT_SIZE, which is the chosen
+# marker's dot: the two dots mean different things and are not one size.
+ANSWER_FIELD_MARK_SIZE = "5px"
@@ (page_stylesheet, beside the .wizard-answer rules at :589-597)
+/* Resolve.dc.html:86-89's .cmpf, .cmpf .k and .cmpf .v, plus the raw
+   value and the difference mark the rail draws beside them. The block
+   is the control that picks the answer, so it carries the button's own
+   reset: a ui.button with children still paints nicegui's ground and
+   centres them. */
+.wizard-answer-fields {{ flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: stretch; text-align: left; background: none; box-shadow: none; padding: 0; text-transform: none; }}
+.wizard-answer-field {{ display: grid; grid-template-columns: {ANSWER_FIELD_KEY_TRACK} 1fr {ANSWER_FIELD_RAW_TRACK}; gap: {SPACE_8}; align-items: center; padding: {SPACE_5} 0; border-bottom: 1px solid {BORDER}; }}
+.wizard-answer-field:last-child {{ border-bottom: 0; }}
+.wizard-answer-field-key {{ display: flex; align-items: center; gap: {SPACE_5}; min-width: 0; font: 500 {TYPE_11}/1 {FONT_MONO}; letter-spacing: 0.05em; text-transform: uppercase; }}
+.wizard-answer-field-value {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
+.wizard-answer-field-raw {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: right; }}
+/* The mark on a row the answers disagree on. A dot and nothing else:
+   no rule here states a colour conditioned on a value's magnitude, so
+   the screen never claims a larger filesize is the better one. */
+.wizard-answer-field-mark {{ width: {ANSWER_FIELD_MARK_SIZE}; height: {ANSWER_FIELD_MARK_SIZE}; border-radius: 50%; background: {ACTION}; flex: none; }}
+/* Resolve.dc.html:84's .cand .m: who holds this record, under the
+   fields rather than in front of them - informational, not the thing
+   being picked (DL-148). */
+.wizard-answer-holders {{ padding-top: {SPACE_5}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

NOTES FOR THE IMPLEMENTER

- .wizard-answer's own rule stays as it is: flex, gap SPACE_9, centred,
  so the marker sits beside the field block. Its `align-items: center`
  may want to become `flex-start` now that the block is tall - read that
  on the served page and record it rather than guessing here.
- Every value above is a constant or an existing token. No literal
  colour or size is introduced (DL-078).
- tests/test_gui_theme.py sweeps every .wizard-* class the sheet defines
  for a call site in app.py, so each of the five names added here must
  be named by CI-M-004-001 or that sweep fails - which is the pairing
  that keeps the two halves of a name from drifting.

```

**Documentation:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ (ANSWER_FIELD_* constants, above them)
+# Every dimension and colour the field rows draw with stands here, the
+# one source this package allows for a size or colour literal (ref:
+# DL-069, DL-078), and each is read off the artboard the screen is
+# built to (ref: DL-071).
 ANSWER_FIELD_KEY_TRACK = "60px"
@@ (.wizard-answer-field-mark rule, in its comment)
 /* The mark on a row the answers disagree on. A dot and nothing else:
    no rule here states a colour conditioned on a value's magnitude, so
-   the screen never claims a larger filesize is the better one. */
+   the screen never claims a larger filesize is the better one
+   (ref: DL-249). Its size is its own constant rather than the chosen
+   marker's: the two dots mean different things. */

```


**CC-M-004-003** (tests/test_gui_resolve_composition.py) - implements CI-M-004-003

**Code:**

```diff

--- a/tests/test_gui_resolve_composition.py
+++ b/tests/test_gui_resolve_composition.py
@@ (new guards, beside test_one_control_per_answer_and_one_bulk_action_per_collection)
+def test_the_answer_control_draws_one_row_per_field_from_answer_detail():
+    """The rail's control is built out of answer_detail.answer_fields,
+    one row per field, naming the classes the sheet declares for them.
+
+    Mutation: `answer_detail.answer_fields(view.attrs, view.agreed,
+    candidate)` in app.py was changed to `[]` and this guard rerun.
+    Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    source = _named_function_source("answer")
+    assert "answer_detail.answer_fields(" in source
+    assert "view.attrs" in source and "view.agreed" in source
+    for name in (
+        "wizard-answer-fields",
+        "wizard-answer-field",
+        "wizard-answer-field-key",
+        "wizard-answer-field-value",
+        "wizard-answer-field-raw",
+        "wizard-answer-field-mark",
+        "wizard-answer-holders",
+    ):
+        assert name in source, f"the rail names no {name}"
+
+
+def test_no_call_site_joins_the_candidate_values_into_one_label():
+    """The single joined label is gone from the page, not merely
+    supplemented by a field grid beside it.
+
+    This is the reading that stays true in the broken state the rest of
+    this milestone can reach: answer_detail guarded on its own, the rail
+    drawing its rows, and the old joined line still printed above them
+    (DL-189).
+
+    Mutation: the `' | '.join(candidate.values)` label was restored
+    beside the field block in app.py and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    page = _page_source()
+    assert "join(candidate.values)" not in page, (
+        "an answer is drawn as a record, not as a joined line of values"
+    )
+
+
+def test_the_mark_is_read_off_the_field_rather_than_drawn_on_every_row():
+    """The difference mark is rendered under `if field.differs`, so a
+    row the answers agree on carries none. A mark on every row says
+    nothing, which is the shape the plan cut.
+
+    Mutation: `if field.differs:` was changed to `if True:` and this
+    guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... an AST walk over the answer() subtree, asserting the
+    wizard-answer-field-mark construction stands inside an ast.If whose
+    test reads the field's differs attribute ...
+
+
+def test_the_field_grid_writes_no_count_into_a_sentence():
+    """The rows added to the rail state no count at all, and the head's
+    sentence still reads its count off the group. A count written into a
+    field row would be the screen restating the model beside it
+    (DL-215).
+
+    Mutation: `ui.label(f"held by {supplied_by}")` was changed to
+    `ui.label(f"held by 2 collections")` and this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    ... assert no ast.Constant string inside answer() matches a digit
+    followed by a word, and that the head guard above still holds ...
+
+
+def test_app_py_carries_no_bare_lf_byte():
+    """app.py is 100% CRLF. This is the reading that fails the moment
+    the file is rewritten without newline="", which is the way an edit
+    to a 2500-line module silently converts it whole.
+
+    Mutation: app.py was rewritten with `path.write_text(source)` and
+    this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    data = _APP_PY.read_bytes()
+    assert data.count(b"\n") == data.count(b"\r\n"), (
+        "app.py carries a bare LF byte"
+    )

NOTES FOR THE IMPLEMENTER

- tests/test_gui_line_endings.py may already hold the CRLF reading. If
  it does, the guard here is redundant and should be dropped rather than
  duplicated - check it before writing, and if it is absent there, write
  it there instead and cite it from this file's module docstring.
- _named_function_source("answer") already exists in this file and
  raises where the function is gone, so a renamed answer() fails these
  guards rather than skipping them.

```

**Documentation:**

```diff
--- a/tests/test_gui_resolve_composition.py
+++ b/tests/test_gui_resolve_composition.py
@@ (above the rail-composition guards)
+# These guards read the page's own construction, not the formatting
+# module's output: a guard asserting that answer_detail is correct is
+# green in the state where the rail never calls it, which is exactly
+# the shape this repository has shipped before (ref: DL-189, DL-252).
+# The joined-label reading is the companion half - it holds in the
+# broken state where an answer group draws its field rows while a
+# single line joining every value stands above them (ref: DL-242).

```


**CC-M-004-004** (tests/test_gui_resolve_sheet.py) - implements CI-M-004-004

**Code:**

```diff

--- a/tests/test_gui_resolve_sheet.py
+++ b/tests/test_gui_resolve_sheet.py
@@ (new guards, beside test_the_answer_control_carries_its_chosen_state_as_its_own_rule)
+def test_the_field_row_declares_the_three_tracks_the_artboard_draws():
+    """Resolve.dc.html:86's .cmpf: a fixed key track, a flexible value
+    track and a fixed raw track, so every answer's keys align down the
+    rail and the raw strings the operator compares stand at one edge.
+
+    Mutation: `grid-template-columns` in .wizard-answer-field was
+    changed to `{theme.ANSWER_FIELD_KEY_TRACK} 1fr 1fr` and this guard
+    rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    rule = _rule(".wizard-answer-field")
+    assert (
+        f"grid-template-columns: {theme.ANSWER_FIELD_KEY_TRACK} 1fr "
+        f"{theme.ANSWER_FIELD_RAW_TRACK}"
+    ) in rule
+
+
+def test_the_field_key_and_the_difference_mark_carry_their_own_rules():
+    """The key is mono and uppercase (Resolve.dc.html:88) and the mark
+    is a dot at its own size, distinct from the chosen marker's dot,
+    which means something else.
+
+    Mutation: ANSWER_FIELD_MARK_SIZE was changed to
+    ANSWER_MARKER_DOT_SIZE in the .wizard-answer-field-mark rule and
+    this guard rerun. Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    key = _rule(".wizard-answer-field-key")
+    assert "text-transform: uppercase" in key and theme.FONT_MONO in key
+    mark = _rule(".wizard-answer-field-mark")
+    assert f"width: {theme.ANSWER_FIELD_MARK_SIZE}" in mark
+    assert theme.ANSWER_FIELD_MARK_SIZE != theme.ANSWER_MARKER_DOT_SIZE
+
+
+def test_no_rail_rule_colours_a_value_by_its_magnitude():
+    """The tool does not know a larger filesize is the better one, so no
+    rule on this rail states a colour for a value at all - only for the
+    mark that says the answers disagree.
+
+    This is the reading that fails the moment a "the bigger one is
+    green" rule is reintroduced, which the user cut explicitly (DL-249).
+
+    Mutation: `.wizard-answer-field-value-larger {{ color: {STATUS_
+    FOUND}; }}` was added to page_stylesheet() and this guard rerun.
+    Observed:
+        <PASTE THE VERBATIM pytest OUTPUT OBSERVED UNDER THE MUTATION>
+    """
+    sheet = theme.page_stylesheet()
+    named = re.findall(r"\.wizard-answer-field[\w-]*", sheet)
+    assert not [
+        name for name in named
+        if any(word in name for word in ("larger", "smaller", "better", "worse"))
+    ]
+    assert "color:" not in _rule(".wizard-answer-field-value")

NOTES FOR THE IMPLEMENTER

- The colour of a value comes from the class the call site names
  (wizard-subtle-5, wizard-faint), which are the design set's own ink
  tokens applied to every value alike. The last assertion holds that the
  field rule itself states none, so a magnitude rule cannot be hidden in
  it.

```

**Documentation:**

```diff
--- a/tests/test_gui_resolve_sheet.py
+++ b/tests/test_gui_resolve_sheet.py
@@ (above the new sheet guards)
+# Every class the rail names is declared in theme.py and every
+# dimension and colour with it, so no size or colour literal stands in
+# app.py (ref: DL-069, DL-078). No rule here conditions a colour on a
+# value's magnitude: difference is marked and never ranked
+# (ref: DL-249).

```


### Milestone 5: The served page and the record it closes on

**Files**: C:/codex/traktor-nml-tool-gate/fixture/reconstruct-conflict/base.nml, C:/codex/traktor-nml-tool-gate/fixture/reconstruct-conflict/source.nml, C:/codex/traktor-nml-tool-gate/fixture/reconstruct-conflict/source-two.nml, docs/2026-09-15-resolve-rail-fields-browser-record.md, tests/test_docs_browser_record_structure.py, traktor_nml/README.md, traktor_nml/gui/CLAUDE.md, traktor_nml/gui/README.md

**Requirements**:

- The page the gate serves over the fixture is read and recorded, and the documentation describes the code as it stands

**Acceptance Criteria**:

- The fixture's conflict carries three answers a bits-per-second bitrate differing across all three and a further tracked field agreeing between two of them
- The only files written outside C:/codex/traktor-nml-tool are the three reconstruct-conflict fixture collections named by this milestone
- The record carries a verdict row per surface plus structural verdicts against Resolve.dc.html
- The record's verdict-row digest is registered in tests/test_docs_browser_record_structure.py and the suite passes
- traktor_nml/README.md carries DL-242 through DL-259 and its high-water mark line names DL-259
- traktor_nml/README.md and the gui file tables name answer_detail.py

**Tests**:

- file: tests/test_docs_browser_record_structure.py
- normal: The record is discovered by its -browser-record.md suffix and carries a verdict row per surface
- edge: The record carries structural verdicts against Resolve.dc.html
- error: A re-verdict rewriting a recorded reading changes the digest and fails the suite

#### Code Intent

- **CI-M-005-001** `C:/codex/traktor-nml-tool-gate/fixture/reconstruct-conflict/base.nml`: The conflicting entry carries a bits-per-second BITRATE and a kilobyte FILESIZE a served rail formats. The file lies in the gate tree outside the working directory, written under DL-256. (refs: DL-251, DL-256)
- **CI-M-005-002** `C:/codex/traktor-nml-tool-gate/fixture/reconstruct-conflict/source.nml`: The conflicting entry offers a second answer diverging on bitrate and on one further tracked field, with a third tracked field agreeing with the base record. The file lies in the gate tree outside the working directory, written under DL-256. (refs: DL-251, DL-256)
- **CI-M-005-003** `C:/codex/traktor-nml-tool-gate/fixture/reconstruct-conflict/source-two.nml`: The conflicting entry offers a third answer whose further tracked field agrees with one of the other two answers while its bitrate differs from both, so a mark discriminates between answers rather than standing on every row. The file lies in the gate tree outside the working directory, written under DL-256. (refs: DL-251, DL-256)
- **CI-M-005-004** `docs/2026-09-15-resolve-rail-fields-browser-record.md`: The served-page record for the resolve step's rail: a verdict row per surface read on the page the gate serves over the fixture, and structural verdicts against design/reconnect-wizard/Resolve.dc.html covering the labelled field rows, the head naming the file once, the formatted and raw values, and the marks standing on the divergent fields alone. (refs: DL-250, DL-251, DL-252)
- **CI-M-005-005** `tests/test_docs_browser_record_structure.py`: The record's verdict-row digest is registered, so a re-verdict rewriting a recorded reading fails the suite. (refs: DL-252)
- **CI-M-005-006** `traktor_nml/README.md`: The decision log carries every decision this work settles - DL-242 through DL-259 - numbered from DL-242 above the high-water mark DL-241, each written as a decision and its reasoning in the log's existing shape. The line recording the log's high-water mark is moved to the last decision written, so the next plan numbers from there rather than from DL-241. (refs: DL-242, DL-243, DL-244, DL-245, DL-246, DL-247, DL-248, DL-249, DL-250, DL-251, DL-252, DL-253, DL-254, DL-255, DL-256, DL-257, DL-258, DL-259)
- **CI-M-005-007** `traktor_nml/gui/CLAUDE.md`: The file table names answer_detail.py, what it holds and when to read it, and conflict_model.py's row names the agreeing values it carries. (refs: DL-244, DL-246)
- **CI-M-005-008** `traktor_nml/gui/README.md`: The nicegui boundary's list of modules below it names answer_detail.py. (refs: DL-246)

#### Code Changes

**CC-M-005-001** (C:/codex/traktor-nml-tool-gate/fixture/reconstruct-conflict/base.nml) - implements CI-M-005-001

**Code:**

```diff

--- a/fixture/reconstruct-conflict/base.nml
+++ b/fixture/reconstruct-conflict/base.nml
@@ (the conflicting entry, one.mp3)
-<ENTRY TITLE="One" ARTIST="A" AUDIO_ID=""><LOCATION DIR="/:Music/:" FILE="one.mp3" VOLUME="C:" VOLUMEID="C:"></LOCATION><ALBUM TITLE=""></ALBUM><INFO BITRATE="320" PLAYTIME_FLOAT="100.0" FILESIZE="16"></INFO></ENTRY>
+<ENTRY TITLE="One" ARTIST="A" AUDIO_ID=""><LOCATION DIR="/:Music/:" FILE="one.mp3" VOLUME="C:" VOLUMEID="C:"></LOCATION><ALBUM TITLE=""></ALBUM><INFO BITRATE="320000" PLAYTIME_FLOAT="99.6" FILESIZE="16384"></INFO></ENTRY>

WHAT THIS MAKES THE RAIL DRAW

base's answer for one.mp3: BITRATE 320000 (320 kbps), FILESIZE 16384
(16.0 MB), PLAYTIME_FLOAT 99.6 (1:39), ALBUM "", TITLE "One", ARTIST
"A".

NOTES FOR THE IMPLEMENTER

- BITRATE moves from 320 to 320000 because Traktor writes bits per
  second and 320 formatted as kbps reads 0. The served page is where the
  kbps reading is confirmed against a real unit, so the fixture has to
  carry the real unit.
- FILESIZE moves from 16 to 16384 so the megabyte reading is a number
  worth reading (16.0 MB) rather than 0.0 MB.
- PLAYTIME_FLOAT moves to 99.6 so the minutes-and-seconds reading is
  exercised on a value whose truncation is visible (1:39, not 1:40).
- These three attributes are identical across all three collections
  before this milestone EXCEPT bitrate, which already diverges. After
  it, playtime_float and filesize still agree across all three, so they
  are agreed pairs and draw UNMARKED rows - which is what the served
  page needs to show that the mark discriminates.
- Only the one.mp3 entry moves. The other five entries in this file are
  what the salvage and playlist readings of this fixture rest on and are
  left alone.
- This file lies outside C:/codex/traktor-nml-tool. Before writing it,
  copy it aside; it is restored from the copy rather than with git
  checkout.
- The gate's own baselines over this fixture - baseline-base-pick.nml,
  headless-keep-first.nml, headless-named-record.nml,
  base-reconnected.nml - carry the OLD values for whichever record wins.
  Check each after the fixture moves and update the ones this change
  makes stale, in the same gate tree. tests/baselines/manifest.json and
  fixture/w002gatefix2 are not touched by any of this.

```

**Documentation:**

```diff
--- a/fixture/reconstruct-conflict/base.nml
+++ b/fixture/reconstruct-conflict/base.nml
@@ (above the COLLECTION element)
+<!-- one.mp3 carries the units a Traktor collection writes: BITRATE in
+     bits per second and FILESIZE in kilobytes, so the served page
+     reads the rail's one-division formatting against a real unit
+     (ref: DL-247, DL-251). PLAYTIME_FLOAT 99.6 truncates to 1:39, so
+     the padding and truncation are visible (ref: DL-255). filesize and
+     playtime_float agree across all three collections and draw
+     unmarked rows, which is what shows the mark discriminating
+     (ref: DL-243). Only the one.mp3 entry carries this reading; the
+     other entries are what the salvage and playlist readings of this
+     fixture rest on. -->

```


**CC-M-005-002** (C:/codex/traktor-nml-tool-gate/fixture/reconstruct-conflict/source.nml) - implements CI-M-005-002

**Code:**

```diff

--- a/fixture/reconstruct-conflict/source.nml
+++ b/fixture/reconstruct-conflict/source.nml
@@ (the conflicting entry, one.mp3)
-<ENTRY TITLE="One" ARTIST="A" AUDIO_ID=""><LOCATION DIR="/:Music/:" FILE="one.mp3" VOLUME="C:" VOLUMEID="C:"></LOCATION><ALBUM TITLE=""></ALBUM><INFO BITRATE="128" PLAYTIME_FLOAT="100.0" FILESIZE="16"></INFO></ENTRY>
+<ENTRY TITLE="One" ARTIST="A" AUDIO_ID=""><LOCATION DIR="/:Music/:" FILE="one.mp3" VOLUME="C:" VOLUMEID="C:"></LOCATION><ALBUM TITLE="Reissue"></ALBUM><INFO BITRATE="128000" PLAYTIME_FLOAT="99.6" FILESIZE="16384"></INFO></ENTRY>

WHAT THIS MAKES THE RAIL DRAW

source's answer: BITRATE 128000 (128 kbps), ALBUM "Reissue". Its
filesize and playtime agree with the other two collections, so those two
rows are drawn from agreed and carry no mark.

NOTES FOR THE IMPLEMENTER

- ALBUM is the second divergent attribute this milestone needs: base
  holds "", source and source-two both hold "Reissue". The group's
  divergent set is therefore (album, bitrate), which is what makes the
  mark worth drawing - see CI-M-005-003.
- The remaining entries of this file are untouched.
- The same copy-aside rule and the same baseline check as
  CI-M-005-001 apply.

```

**Documentation:**

```diff
--- a/fixture/reconstruct-conflict/source.nml
+++ b/fixture/reconstruct-conflict/source.nml
@@ (above the COLLECTION element)
+<!-- source's one.mp3 diverges from base on the attributes the rail
+     marks and agrees on the rest, so its answer reads as a whole
+     record with both marked and unmarked rows (ref: DL-242, DL-251).
+     The bitrate is bits per second, as Traktor writes it
+     (ref: DL-247). -->

```


**CC-M-005-003** (C:/codex/traktor-nml-tool-gate/fixture/reconstruct-conflict/source-two.nml) - implements CI-M-005-003

**Code:**

```diff

--- a/fixture/reconstruct-conflict/source-two.nml
+++ b/fixture/reconstruct-conflict/source-two.nml
@@ (the conflicting entry, one.mp3)
-<ENTRY TITLE="One" ARTIST="A" AUDIO_ID=""><LOCATION DIR="/:Music/:" FILE="one.mp3" VOLUME="C:" VOLUMEID="C:"></LOCATION><ALBUM TITLE=""></ALBUM><INFO BITRATE="192" PLAYTIME_FLOAT="100.0" FILESIZE="16"></INFO></ENTRY>
+<ENTRY TITLE="One" ARTIST="A" AUDIO_ID=""><LOCATION DIR="/:Music/:" FILE="one.mp3" VOLUME="C:" VOLUMEID="C:"></LOCATION><ALBUM TITLE="Reissue"></ALBUM><INFO BITRATE="192000" PLAYTIME_FLOAT="99.6" FILESIZE="16384"></INFO></ENTRY>

WHAT THE THREE FILES TOGETHER MAKE THE RAIL DRAW

One group, three answers, and this is the shape the served-page record
is taken on:

  divergent set: album, bitrate
  agreed pairs:  artist "A", title "One", filesize "16384",
                 playtime_float "99.6"

  Answer 1 (base)        ARTIST A | TITLE One | ALBUM (empty) * |
                         FILESIZE 16.0 MB / 16384 |
                         PLAYTIME_FLOAT 1:39 / 99.6 |
                         BITRATE 320 kbps / 320000 *
  Answer 2 (source)      ... ALBUM Reissue * ... BITRATE 128 kbps *
  Answer 3 (source-two)  ... ALBUM Reissue * ... BITRATE 192 kbps *

  (* marks the rows the answers disagree on.)

ALBUM is the field that carries the plan's point: answers 2 and 3 hold
the same album while answer 1 does not, so the mark stands on a row
where two answers agree with each other - the case that cannot arise
with only two answers, and the reason the fixture needs a third
collection.

NOTES FOR THE IMPLEMENTER

- Read the drawn rail against this table on the served page. If the
  rail draws six marks or two, the mark rule is wrong and the record
  says so rather than being rewritten to match the screen.
- The same copy-aside rule and the same baseline check as
  CI-M-005-001 apply.

```

**Documentation:**

```diff
--- a/fixture/reconstruct-conflict/source-two.nml
+++ b/fixture/reconstruct-conflict/source-two.nml
@@ (above the COLLECTION element)
+<!-- source-two makes the group a three-answer group, which is what the
+     mark needs to say something: a field can agree between two answers
+     and differ at the third, so a mark on every row would be no
+     reading at all (ref: DL-243, DL-251). Its bitrate is bits per
+     second (ref: DL-247). -->

```


**CC-M-005-004** (docs/2026-09-15-resolve-rail-fields-browser-record.md) - implements CI-M-005-004

**Code:**

```diff

--- /dev/null
+++ b/docs/2026-09-15-resolve-rail-fields-browser-record.md
@@ (new record, LF endings, discovered by its -browser-record.md suffix)
+# Served-page record: the resolve step's detail rail
+
+DL-084 as DL-169 amends it: the readings a browser took off the running
+page, one verdict per surface, followed by a structural reading of what
+the page composes against the artboard that draws it.
+
+## How the run was taken
+
+The wizard was served by the gate repository's own serve script at
+`C:\codex\traktor-nml-tool-gate`, over
+`fixture/reconstruct-conflict`, with base, source and source-two given
+as the three collections and only `pick_file_or_folder` stubbed. The
+viewport is `1280x900`.
+
+The walk: fill in step 1 with the three collections, `Preview` - which
+refuses on the fixture's one conflict - `Continue to resolve`, and read
+the rail over the focused row. Then pick answer 2, read the rail again,
+and undo.
+
+The code under measurement is <COMMIT> plus this milestone's changes.
+
+## Readings
+
+| Surface | Expected | Read | Verdict |
+|---|---|---|---|
+| The rail head | names the file once | <PASTE> | <matches/differs> |
+| The head's sentence | a count read off the group | <PASTE> | <matches/differs> |
+| Answer 1's field rows | one row per tracked attribute the group carries, in _TRACKED_ATTRS order | <PASTE the six keys in the order read> | <matches/differs> |
+| The field keys | the NML attribute names, uppercase | <PASTE> | <matches/differs> |
+| FILESIZE | one division by 1024 off a kilobyte count | <PASTE, expected `16.0 MB` beside `16384`> | <matches/differs> |
+| BITRATE, answer 1 | one division by 1000 off bits per second | <PASTE, expected `320 kbps` beside `320000`> | <matches/differs> |
+| BITRATE, answers 2 and 3 | the two other answers' own values | <PASTE, expected `128 kbps` and `192 kbps`> | <matches/differs> |
+| PLAYTIME_FLOAT | minutes and zero-padded seconds | <PASTE, expected `1:39` beside `99.6`> | <matches/differs> |
+| ARTIST, TITLE | the raw value alone, no formatted companion | <PASTE> | <matches/differs> |
+| The marks | on ALBUM and BITRATE alone, on all three answers | <PASTE which rows carry one> | <matches/differs> |
+| ALBUM across the answers | answers 2 and 3 agree, answer 1 does not - the mark stands on a row two answers share | <PASTE> | <matches/differs> |
+| The holders line | under the fields, naming the collections | <PASTE> | <matches/differs> |
+| The control | the field block picks the answer | <PASTE what a click on a field row did> | <matches/differs> |
+| The chosen marker after a pick | answer 2 alone | <PASTE> | <matches/differs> |
+| No value colouring | no value painted by its magnitude | <PASTE the computed colours of the two FILESIZE cells> | <matches/differs> |
+| The rail width | 400px | <PASTE> | <matches/differs> |
+| The rail's own scroll | the fields make the rail taller; whether it scrolls and whether the footer stays put | <PASTE> | <matches/differs> |
+| Document scroll | none | <PASTE `scrollWidth`/`scrollHeight` against the viewport> | <matches/differs> |
+
+## What this run establishes
+
+<Written after the readings: what the rail now says that it did not,
+in the shape the other records under docs/ use - what was wrong, what
+it says instead, and why that is the smallest true thing. No
+"previously" or "now does": the record describes what was read.>
+
+## Structural verdicts
+
+| Structure | The artboard draws | The served page composes | Verdict |
+|---|---|---|---|
+| The rail body | `Resolve.dc.html`'s `.det-b`: answer groups only, no "The file" group | <PASTE> | <matches/differs> |
+| An answer's field rows | `.cmpf`'s three tracks - key, value, raw - with `.k` mono uppercase | <PASTE the resolved track widths> | <matches/differs> |
+| The difference mark | a 5px dot in the key cell of a divergent row | <PASTE> | <matches/differs> |
+| The holders line | `.cand .m` under the fields | <PASTE> | <matches/differs> |
+| The chosen marker | `.rad` and its dot, unchanged by this work | <PASTE> | <matches/differs> |
+
+## What this run does not establish
+
+The keyboard ring and the announcements are not read: accessibility is
+out of scope for this version, and DL-197 says so.
+
+<Anything the pane would not deliver, in the shape the other records
+use.>

NOTES FOR THE IMPLEMENTER

- Every `<PASTE>` is filled from the browser. A row written before the
  reading is a record of what was expected, which is the thing DL-171
  exists to stop.
- A `differs` verdict is recorded as differs and fixed in the design
  first where the disagreement is with the artboard (DL-071).
- The record is written to docs/ inside C:/codex/traktor-nml-tool; only
  the three fixture files of this milestone are written outside it.

```

**Documentation:**

```diff
--- a/docs/2026-09-15-resolve-rail-fields-browser-record.md
+++ b/docs/2026-09-15-resolve-rail-fields-browser-record.md
@@ (after "How the run was taken")
+The fixture is read rather than regenerated: its conflicting entry
+carries Traktor's own units and a field that agrees between two of the
+three answers, so the page exercises the unit formatting and a mark
+that discriminates (ref: DL-251, DL-256).
+
+Every field the rail draws is a tracked attribute the group's records
+carry, the agreeing ones included, so the screen hides no field: attrs
+never holds an attribute the answers agree on, and the agreeing values
+ride beside it (ref: DL-242, DL-244, DL-245).
+
+The verdict rows are what this record is registered by: their digest
+stands in tests/test_docs_browser_record_structure.py, computed from
+the record as the run left it (ref: DL-084, DL-169).

```


**CC-M-005-005** (tests/test_docs_browser_record_structure.py) - implements CI-M-005-005

**Code:**

```diff

--- a/tests/test_docs_browser_record_structure.py
+++ b/tests/test_docs_browser_record_structure.py
@@ (READING_DIGESTS, at the end of the mapping)
     "2026-09-15-write-step-after-the-write-browser-record.md": "32dfbfadf3db8e36441a21e886003215da2cb59fb63a7665e7b0429757a3c61a",
+    "2026-09-15-resolve-rail-fields-browser-record.md": "<THE SHA-256 OF THE RECORD'S VERDICT ROWS AS WRITTEN>",
 }

NOTES FOR THE IMPLEMENTER

- The digest is written AFTER the record is, from the record as the
  browser run left it: an entry standing here ahead of its record hashes
  what the plan guessed rather than what was read. The comment already
  under this mapping says so.
- Compute it with the file's own _reading_digest over the written
  record rather than by hand, so the rows hashed are the rows the regex
  matches.
- No existing digest moves. This file's other guards - the structural
  heading, the verdict-row shape - apply to the new record by discovery
  and need no edit.

```

**Documentation:**

```diff
--- a/tests/test_docs_browser_record_structure.py
+++ b/tests/test_docs_browser_record_structure.py
@@ (beside the new READING_DIGESTS entry)
+    # The milestone closes on a served-page record carrying a verdict
+    # row per surface and structural verdicts against
+    # design/reconnect-wizard/Resolve.dc.html, its verdict rows
+    # registered here by digest (ref: DL-084, DL-169). The digest is
+    # computed from the record as the browser run left it, so the rows
+    # hashed are the rows that were read.

```


**CC-M-005-006** (traktor_nml/README.md) - implements CI-M-005-006

**Code:**

```diff

--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ (Design Decisions, after the DL-241 bullet at :1206-1218)
+- Each answer in the resolve step's detail rail reads as a complete
+  record: every tracked attribute the group's records carry, the ones
+  the answers agree on included, one field per line as field name,
+  formatted value and raw value. An answer joined into one string of
+  values cannot be told from its neighbour, and a rail showing only the
+  divergent subset reads as a diff rather than as the record that wins,
+  so the rail prints the record and the mark carries the difference
+  (DL-242).
+- The divergence mark stands on a field exactly where its name is in
+  the row's attrs. splice computes attrs as the tracked attributes
+  whose values differ across the group's members, which is precisely
+  the set of fields that differ across the answers, already computed
+  and already carried to the page; the rule is a membership test in a
+  nicegui-free module, so no second divergence computation exists to
+  disagree with the first (DL-243).
+- The agreeing values ride alongside attrs as their own field on
+  ConflictRow, ConflictGroup and ConflictRowView, and attrs names the
+  divergent set alone. attrs is one of the three columns the conflict
+  CSV writes and the line splice_cmd prints
+  (traktor_nml/commands/splice_cmd.py:22, :24), so widening it in place
+  would rewrite recorded output for every run; the complete record is
+  carried as an addition and the CSV columns are guarded unmoved
+  (DL-244).
+- Every member of a group agrees on every attribute outside attrs, so
+  one group-wide mapping of agreeing attribute to value is well defined
+  and is computed beside the candidates. divergent_attrs at
+  splice.py:340-341 names the attributes whose value set across the group's
+  members has more than one member, so an attribute outside it holds
+  one value across every member, candidates included: the agreeing
+  values belong to the group rather than to a candidate, and a guard
+  reads that off a three-answer group rather than asserting it
+  (DL-245).
+- Formatting and field assembly live in
+  `traktor_nml/gui/answer_detail.py`, a module importing no nicegui.
+  DL-069 puts every rule the suite reaches below the nicegui boundary,
+  and conflict_model.py is the vocabulary a pick is recorded in, so a
+  display formatting rule there would give that module a second purpose
+  the package's one-purpose-per-module table does not carry; the field
+  rows, their labels, their formatted values and the mark stand in one
+  module app.py reads from (DL-069, DL-246).
+- FILESIZE renders as megabytes by dividing by 1024 once,
+  PLAYTIME_FLOAT as minutes and seconds, and BITRATE as kilobits per
+  second by dividing by 1000, with the raw string standing beside every
+  formatted value in mono. Traktor writes FILESIZE in kilobytes - the
+  calibration comment at traktor_nml/matching.py:124-128 records the
+  measured error of FILESIZE against bytes/1024, and _size_kb
+  (traktor_nml/matching.py:166-180) deliberately does no conversion
+  because both sides already carry kilobytes - and BITRATE in bits per
+  second. A formatting dividing a kilobyte count twice prints a number
+  the collection does not hold, and the raw value stays visible because
+  it is what the written file carries (DL-247).
+- A value that is empty or does not parse as a number prints as itself
+  with no formatted companion. traktor_nml/model.py:217-219 yields an
+  empty string for every INFO-borne attribute where a record carries no
+  INFO element, and a formatter dividing that string raises inside a
+  page build, so each formatter returns the raw string unchanged where
+  the value does not parse and a guard covers the empty string
+  (DL-248).
+- No colour ranks one value against another. The tool has no way to
+  know that a larger filesize or a higher bitrate is the better record,
+  so a green value would state a judgement the model cannot support:
+  difference is marked and never ranked (DL-249).
+- The rail head is the one place the file is named, and
+  design/reconnect-wizard/Resolve.dc.html carries no "The file" group.
+  The head prints the identity key in mono and the artboard's body
+  opened with a labelled Path row holding the same string, which prints
+  the file twice in a 400px rail; the artboard is amended first and the
+  screen is built to it (DL-071, DL-250).
+- The gate fixture's conflicting entry carries bits-per-second bitrates
+  and a second divergent field agreeing between two of its three
+  answers. A fixture diverging on bitrate alone, at values a Traktor
+  collection never writes, exercises neither the unit formatting nor a
+  mark that discriminates between answers, so the fixture carries a
+  field that agrees and a field that differs and the record reads both
+  (DL-251).
+- A guard proves the page calls the field assembly rather than only
+  that the assembly is correct. This repository has shipped guards
+  green in exactly the broken state (DL-189), and a formatter guarded
+  alone passes while the rail joins raw values into one label: the
+  composition guard reads app.py's answer() for the per-field
+  construction, and the served-page record reads the rendered rail
+  (DL-189, DL-252).
+- Every record the resolve rail answers over is Traktor-borne: splice
+  builds its groups from records_by_input, the per-input lists of
+  collection_records, and hands them to group_identities
+  (traktor_nml/splice.py:475, :482), and diskscan
+  feeds matching and reconnect_run instead
+  (traktor_nml/reconnect_run.py:23,
+  traktor_nml/commands/discover_tracks_cmd.py:12). The kilobits BITRATE
+  traktor_nml/diskscan.py:59 writes has no path into a ConflictRow, so
+  the rail formats one provenance and the bits-per-second division
+  needs no provenance condition (DL-253).
+- The rail prints each field name as Traktor writes the attribute in
+  the NML - ARTIST, TITLE, ALBUM, FILESIZE, PLAYTIME_FLOAT, BITRATE -
+  as one fixed mapping from the splice._TRACKED_ATTRS identifier to the
+  printed label. _TRACKED_ATTRS holds lowercase python identifiers
+  while the artboard draws the key in mono uppercase, and left to the
+  call site the same field could print as PLAYTIME_FLOAT, PLAYTIME or
+  LENGTH on different rows; the label is the XML attribute name the
+  written file carries, uppercased, so the printed key names the thing
+  the raw value beside it came from (DL-254).
+- The numeric presentation is the approved mockup read literally:
+  FILESIZE to one decimal followed by MB, BITRATE rounded to a whole
+  number followed by kbps, PLAYTIME_FLOAT as minutes then a colon then
+  seconds truncated toward zero and zero-padded to two digits. No
+  thousands separator is introduced anywhere and the raw string is
+  reproduced exactly as the collection carries it: a grouped copy of
+  the same digits beside the ungrouped ones reads as a third value, and
+  the raw value is what the written file holds (DL-255).
+- This work writes into `C:\codex\traktor-nml-tool-gate`, a tree
+  outside the primary working directory, for the three
+  reconstruct-conflict fixture collections alone. The gate tree is
+  where the served page is produced, and the served-page record DL-084
+  and DL-169 require cannot read the unit formatting or a
+  discriminating mark without editing that fixture; no other file
+  outside the working directory is touched (DL-084, DL-169, DL-256).
+- The rail head and the field grid go through
+  `traktor_nml/gui/wording.plural` for every word a count picks, and no
+  inline conditional on a count stands anywhere under gui/. The head's
+  holding-count sentence reads `collection holds` at one and
+  `collections hold` otherwise; an inline `x if n == 1 else y` is the
+  shape tests/test_gui_wording.py forbids outside wording.py, and a
+  count written into a sentence is what DL-215 forbids (DL-215,
+  DL-257).
+- `traktor_nml/gui/app.py` is read and rewritten with newline set to
+  the empty string so its CRLF line endings survive the edit, while
+  answer_detail.py, theme.py and every file under tests/ stay LF. app.py
+  is the one file in the package carrying CRLF throughout, and a
+  default-mode write converts every line ending and shows the whole file
+  as changed, hiding the real edit; a guard reads the file bytes for an
+  absence of a bare LF (DL-258).
+- No work here regenerates tests/baselines/manifest.json or
+  fixture/w002gatefix2, restores a file with git checkout, writes into
+  build/ or dist/, installs into the system interpreter or spawns a
+  background agent, and the suite runs under
+  `C:\Users\marcu\AppData\Local\Python\pythoncore-3.14-64\python.exe`.
+  M-002 changes a structure the conflict CSV and splice_cmd report
+  over, which is exactly the change a baseline regeneration would paper
+  over: a regenerated manifest would record the new output as expected
+  and the guard that the columns are unmoved would pass in the broken
+  state (DL-189, DL-259).

NOTES FOR THE IMPLEMENTER

- Eighteen bullets, DL-242 through DL-259, one for each id the plan's
  readme_entries defines, in that order and with no id reused and none
  left as a placeholder. DL-252 is written here because the guards and
  the served-page record cite it by number; it states the composition
  requirement rather than restating DL-084, DL-169 or DL-189, which it
  cites.
- The log's high-water mark in this file is the highest DL number any
  statement in it defines; writing these bullets moves it from DL-241 to
  DL-259. There is no separate line naming the mark, so nothing else in
  this file needs editing for it.
- Each decision is stated ONCE. Where a statement belongs in Overview,
  Architecture, Invariants or Tradeoffs it goes there and carries its
  tag, and this section carries no second copy - the rule stated at the
  head of the section.
- Nothing here is written as "previously", "now does", "no longer" or
  "added": each bullet states what the code does and why, and where a
  sentence names the defect a decision settles it does so in the past
  tense of the thing that was drawn or measured, which is what the
  existing bullets do.

```

**Documentation:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ (above the DL-242 bullet)
+The entries below run from DL-242 and the high-water mark line names
+DL-259. This file is the authority for that number: an entry numbered
+against anything else collides with an entry this file names.

```


**CC-M-005-007** (traktor_nml/gui/CLAUDE.md) - implements CI-M-005-007

**Code:**

```diff

--- a/traktor_nml/gui/CLAUDE.md
+++ b/traktor_nml/gui/CLAUDE.md
@@ (the Files table, a new row between wording.py and theme.py)
+| `answer_detail.py` | The rows one answer in the resolve step's detail rail draws: `AnswerField` (an attribute, the NML name the rail prints, the raw value, what it means and whether the answers disagree on it), `answer_fields(attrs, agreed, candidate)` (one field per tracked attribute the group carries, in `splice._TRACKED_ATTRS` order, marked as differing exactly where its name stands in attrs), `format_value` (FILESIZE as megabytes off Traktor's kilobyte count, BITRATE as kilobits off bits per second, PLAYTIME_FLOAT as minutes and seconds; `None` for a text field and for a value that is empty or does not parse) and `LABELS`. Imports no `nicegui`. | Changing what a rail field is called, how a value reads, or which rows the rail marks |
@@ (the conflict_model.py row, in its "What" cell)
-... `ConflictGroup`/`ConflictDecisions` (per identity key, `UNDECIDED` or a `CandidateRef` ...
+... `ConflictGroup`/`ConflictDecisions` (per identity key, `UNDECIDED` or a `CandidateRef` ... , carrying `agreed` - the tracked attributes every member of the group holds the same value for, beside `attrs`, the ones they diverge on, so the rail draws each answer as a whole record; `agreed` is not compared when a pick re-attaches) ...

NOTES FOR THE IMPLEMENTER

- The table's rows are ordered by the import order the boundary
  section describes, so answer_detail.py sits with the other
  nicegui-free modules rather than at the end.
- The app.py row's "When to read" already covers a rail change and
  needs no edit.

```

**Documentation:**

```diff
--- a/traktor_nml/gui/CLAUDE.md
+++ b/traktor_nml/gui/CLAUDE.md
@@ (in the boundary note above the Files table)
+`answer_detail.py` sits with the nicegui-free modules: every rule about
+what a rail field is called, how its value reads and which rows carry
+the mark lives below the boundary where the suite reaches it, and
+`app.py` only places what it returns (ref: DL-069, DL-246). Every width,
+colour and gap those rows draw with belongs to `theme.py`.

```


**CC-M-005-008** (traktor_nml/gui/README.md) - implements CI-M-005-008

**Code:**

```diff

--- a/traktor_nml/gui/README.md
+++ b/traktor_nml/gui/README.md
@@ (The nicegui boundary, :10-21)
 `app.py`, `file_picker.py` and `__main__.py` are the only three modules
 in this package that import `nicegui` or `pywebview`. Every other
 module - `review_model.py`, `wizard_state.py`, `theme.py`, `keymap.py`,
 `announce.py`, `conflict_model.py`, `navigation.py`,
 `reconstruct_steps.py`, `reconstruct_report.py`,
-`collection_summary.py`, `_fs_nav.py` and `__init__.py` - imports
+`collection_summary.py`, `answer_detail.py`, `_fs_nav.py` and
+`__init__.py` - imports
 neither

NOTES FOR THE IMPLEMENTER

- `wording.py` is absent from this list as it stands. If that is an
  omission rather than an intention, it belongs in the same edit; check
  before adding, and say nothing about it in the decision log either way
  unless a decision is actually being made.
- tests/test_gui_view_boundary.py sweeps the directory rather than
  reading this list, so the list is documentation and the guard is the
  guard - which is why it can fall behind and why this edit is part of
  the milestone rather than optional.

```

**Documentation:**

```diff
--- a/traktor_nml/gui/README.md
+++ b/traktor_nml/gui/README.md
@@ (below the nicegui boundary paragraph)
+The list is documentation; tests/test_gui_view_boundary.py sweeps the
+directory rather than reading it, so a module named here is named for a
+reader and guarded by the sweep (ref: DL-069).

```


## README Entries

### traktor_nml/README.md

# Decision log entries this work writes into traktor_nml/README.md

Numbered from DL-242, above the log's high-water mark DL-241. The high-water mark line moves to DL-259 once these are written (CI-M-005-006).

- **DL-242.** Each answer in the resolve rail reads as a complete record: every name in splice._TRACKED_ATTRS the group's records carry, agreeing fields included, one field per line as field name, formatted value and raw value.
  An answer joined into one string of values cannot be told from its neighbour, and a rail showing only the divergent subset reads as a diff rather than as the record that wins -> the operator picks a record, so the rail prints the record -> the six tracked attributes stand per answer and the mark carries the difference

- **DL-243.** The divergence mark stands on a field exactly where its name is in the row's attrs.
  splice computes attrs as the tracked attributes whose values differ across the group's members -> that set is precisely the fields that differ across the answers, already computed and already carried to the page -> the rule is a membership test in a nicegui-free module, and no second divergence computation exists to disagree with the first

- **DL-244.** The agreeing values ride alongside attrs as their own field on ConflictRow, ConflictGroup and ConflictRowView; attrs names the divergent set alone.
  attrs is one of the three columns the conflict CSV writes and the line splice_cmd prints (traktor_nml/commands/splice_cmd.py:22, :24) -> widening it in place rewrites recorded output for every run -> the complete record is carried as an addition, and the CSV columns are guarded unmoved

- **DL-245.** Every member of a group agrees on every attribute outside attrs, so one group-wide mapping of agreeing attribute to value is well defined and is computed beside the candidates.
  divergent_attrs at splice.py:340-341 names the attributes whose value set across the group's members has more than one member -> an attribute outside it holds one value across every member of the group, candidates included -> the agreeing values belong to the group rather than to a candidate, and a guard reads that off a three-answer group rather than asserting it

- **DL-246.** Formatting and field assembly live in traktor_nml/gui/answer_detail.py, a module importing no nicegui.
  DL-069 puts every rule the suite reaches below the nicegui boundary, and conflict_model.py is the vocabulary a pick is recorded in -> a display formatting rule there gives that module a second purpose the package's one-purpose-per-module table does not carry -> the field rows, their labels, their formatted values and the mark stand in one module app.py reads from

- **DL-247.** FILESIZE renders as megabytes by dividing by 1024 once; PLAYTIME_FLOAT renders as minutes and seconds; BITRATE renders as kilobits per second by dividing by 1000, unconditionally, because every record the rail answers over is Traktor-borne (DL-253); the raw string stands beside every formatted value in mono.
  Traktor writes FILESIZE in kilobytes - the calibration comment at traktor_nml/matching.py:124-128 records the measured error of FILESIZE against bytes/1024, and _size_kb (traktor_nml/matching.py:166-180) deliberately does no conversion because both sides already carry kilobytes - and BITRATE in bits per second (collection_textual_patch_test.nml carries values near 1000000) -> a formatting dividing a kilobyte count twice or reading a bitrate as kilobits prints a number the collection does not hold, and the kilobits bitrate traktor_nml/diskscan.py:59 writes would print near 0.3 kbps if it could reach the rail -> one division each with no provenance branch, the provenance itself settled by DL-253, the precision by DL-255, and the raw value stays visible because it is what the written file carries

- **DL-248.** A value that is empty or does not parse as a number prints as itself with no formatted companion.
  traktor_nml/model.py:217-219 yields an empty string for every INFO-borne attribute where a record carries no INFO element -> a formatter dividing that string raises inside a page build -> each formatter returns the raw string unchanged where the value does not parse, and a guard covers the empty string

- **DL-249.** No colour ranks one value against another.
  The tool has no way to know that a larger filesize or a higher bitrate is the better record -> a green value states a judgement the model cannot support -> difference is marked and never ranked

- **DL-250.** The rail head is the one place the file is named; design/reconnect-wizard/Resolve.dc.html carries no 'The file' group.
  The head prints the identity key in mono and the artboard's body opens with a labelled Path row holding the same string -> drawing both prints the file twice in a 400px rail -> the artboard is amended first and the screen is built to it (DL-071)

- **DL-251.** The gate fixture's conflicting entry carries bits-per-second bitrates and a second divergent field agreeing between two of its three answers.
  The fixture's one conflict diverges on bitrate alone, at values a Traktor collection never writes -> a served page over it exercises neither the unit formatting nor a mark that discriminates between answers -> the fixture carries a field that agrees and a field that differs, so the record reads both

- **DL-252.** A guard proves the page calls the field assembly rather than only that the assembly is correct.
  This repository has shipped guards green in exactly the broken state (DL-189) -> a formatter guarded alone passes while the rail joins raw values into one label -> the composition guard reads app.py's answer() for the per-field construction, and the served-page record reads the rendered rail

- **DL-253.** Every record the resolve rail answers over is Traktor-borne: splice groups over collection_records from the NML collections given as inputs, and a disk-scanned record never reaches a conflict group or detail_rail().
  traktor_nml/splice.py:475 builds its groups from records_by_input, the per-input lists of collection_records, and hands them to group_identities (traktor_nml/splice.py:482), and diskscan feeds matching and reconnect_run instead (traktor_nml/reconnect_run.py:23, traktor_nml/commands/discover_tracks_cmd.py:12) -> the kilobits BITRATE traktor_nml/diskscan.py:59 writes has no path into a ConflictRow -> the rail formats one provenance and the bits-per-second division needs no provenance condition

- **DL-254.** The rail prints each field name as Traktor writes the attribute in the NML: ARTIST, TITLE, ALBUM, FILESIZE, PLAYTIME_FLOAT and BITRATE, one fixed mapping from the splice._TRACKED_ATTRS identifier to the printed label.
  splice._TRACKED_ATTRS holds lowercase python identifiers while the artboard draws the key in mono uppercase -> left to the implementer the same field could print as PLAYTIME_FLOAT, PLAYTIME or LENGTH on different rows and against the record -> the label is the XML attribute name the written file carries, uppercased, so the printed key names the thing the raw value beside it came from

- **DL-255.** The numeric presentation is the approved mockup read literally: FILESIZE to one decimal followed by MB, BITRATE rounded to a whole number followed by kbps, PLAYTIME_FLOAT as minutes then a colon then seconds truncated toward zero and zero-padded to two digits; no thousands separator is introduced anywhere and the raw string is reproduced exactly as the collection carries it.
  The approved mockup at the scratchpad resolve-rail-mockup.html is the only Tier 1 source carrying precision and it shows 8.1 MB, 320 kbps and 7:01 -> a plan fixing units but not precision leaves a user-visible default to the implementer, while the mockup separated raw 8,123,456 would rewrite the string the written file holds -> precision, rounding and padding come from the mockup and the raw value alone is exempt from it

- **DL-256.** This work writes into C:/codex/traktor-nml-tool-gate, a tree outside the primary working directory, for the three reconstruct-conflict fixture collections alone; no other file outside C:/codex/traktor-nml-tool is touched.
  The gate tree is where the served page is produced and its one conflict diverges on bitrate alone at values a Traktor collection never writes (DL-251) -> the served-page record DL-084 and DL-169 require cannot read the unit formatting or a discriminating mark without editing that fixture -> the external writes are named file by file in M-005 and bounded to the reconstruct-conflict fixture

- **DL-257.** The rail head and the new field grid go through traktor_nml/gui/wording.plural for every word a count picks, and no inline conditional on a count stands anywhere under gui/.
  M-004 touches the head holding-count sentence and adds a grid drawn once per field -> an inline x if n == 1 else y is the shape tests/test_gui_wording.py forbids outside wording.py, and a count written into a sentence is what DL-215 forbids -> the count reads off the model and its word comes from wording.plural, guarded by the existing wording test over the changed file

- **DL-258.** traktor_nml/gui/app.py is read and rewritten with newline set to the empty string so its CRLF line endings survive the edit, while answer_detail.py, theme.py and every file under tests/ stay LF.
  app.py is the one file in the package carrying CRLF throughout -> a default-mode write converts every line ending and shows the whole file as changed, hiding the real edit -> the empty-newline write is named in the app.py intent and a guard reads the file bytes for an absence of bare LF

- **DL-259.** No work here regenerates tests/baselines/manifest.json or fixture/w002gatefix2, restores a file with git checkout, writes into build/ or dist/, installs into the system interpreter or spawns a background agent; the suite runs under C:/Users/marcu/AppData/Local/Python/pythoncore-3.14-64/python.exe.
  M-002 changes a structure the conflict CSV and splice_cmd report over, which is exactly the change a baseline regeneration would paper over -> a regenerated manifest would record the new output as expected and the guard that the columns are unmoved would pass in the broken state (DL-189) -> the baselines and the gate fixture w002gatefix2 are read never written, a file needing restoration is copied aside first, and every guard in this plan runs under the system interpreter

## Execution Waves

- W-001: M-001, M-002
- W-002: M-003
- W-003: M-004
- W-004: M-005

# Plan

## Overview

splice.py's divergence rule compares the six tracked attribute strings by set size, so an 8,123-versus-8,124 KB FILESIZE is a divergence and the group becomes a conflict the operator must decide. Measured over the user's own collection pair - 9,052 identity groups across two inputs - 8,113 groups (89.6%) diverge on filesize alone and 8,523 (94.2%) on nothing but the three measured attributes, leaving 529 (5.8%) that touch artist, title or album. A conflict compares Traktor against Traktor, so a measured difference is a real recorded fact; what it is not is a question an operator can answer, because no judgement exists over a measurement. The volume is also what holds the event loop: draw() builds every one of those 9,052 rows at 8.5-10.1s against nicegui's 6s socket budget, the socket drops, the client is deleted after 3s, and because the wizard's state lives in the page builder's closures the reconnect can only rebuild - the run is lost and the window returns to step 1.

**Approach**: The six tracked attributes carry a tier. A group whose divergence is measured-only is settled by rule: it raises no conflict, takes no resolution, and its measured values travel with the record the output holds. A group diverging on any editorial attribute is a conflict exactly as before, carrying every divergent attribute it has so the rail still draws a whole record. What the rule settles is not silent: the run reports one settled row per group it answered, and the groups whose measured gap exceeds 1% of the larger value are listed by name as an outlier reading rather than a row to decide - which is what the playtime_float exposure needs, since 6 groups sit beyond the band with a worst gap of 3,516s. The tier tables, the band and the projection live in one leaf module, so the screen and the printed run read one definition. The decision log in traktor_nml/README.md stands at DL-307 and docs/plans/2026-09-26-collection-dedupe holds DL-308 through DL-324, so this plan mints DL-325 onward.

### Where a divergence is tiered and where each side is reported

[Diagram pending Technical Writer rendering: DIAG-001]

## Planning Context

### Decision Log

| ID | Decision | Reasoning Chain |
|---|---|---|
| DL-325 | The six tracked attributes carry a tier: filesize, playtime_float and bitrate are MEASURED, artist, title and album are EDITORIAL, and a group whose divergence is measured-only is settled by rule rather than put to the operator. | A conflict compares Traktor against Traktor, so a measured difference is a recorded fact rather than a mistake -> no operator judgement exists over a recorded measurement, while a differing artist or title is exactly a judgement -> the divergence rule splits on which kind of attribute diverges, not on how far apart the values are. |
| DL-326 | The tier tables, the outlier band and the outlier projection live in traktor_nml/metadata_tier.py, which imports nothing from traktor_nml; splice.py takes TRACKED_ATTRS from it and keeps _TRACKED_ATTRS as the name its callers already read. | DL-069 puts every decision rule in a module the suite reaches with no nicegui -> splice.py is such a module but is also what gui/answer_detail.py imports _TRACKED_ATTRS from, and a tier table defined in splice.py that the CLI report and conflict_model both read would make splice.py the import root of the report layer -> a leaf module holds the tables, splice.py re-exports the name already in use, and the screen and the printed run read one definition. |
| DL-327 | A conflict is raised when at least one EDITORIAL attribute diverges; a group raising one carries every divergent attribute in attrs, measured names included. | The tier changes which groups are put to the operator, not what a group being put to them shows -> a mixed group's rail draws the whole record it describes, and moving its measured names out of attrs would drop those rows from answer_fields, which leaves out any attribute standing in neither attrs nor agreed -> attrs keeps its meaning, conflict_model, answer_detail and the conflict CSV's third column stand unchanged, and no group is both a conflict and a settled one. |
| DL-328 | A settled group's measured values are the base record's where the group holds one, and the run-wide picker's winner where it holds none; no entry patch is collected for it. | _resolve_conflicts patches base's ENTRY span only where a resolution names a non-base record, and a settled group is named by no resolution -> base keeps its own measured numbers and the transplant branch carries the picked non-base record's span verbatim -> the winner's values travel either way, and the plan says so rather than leaving 'follows the winning record' to be read as a patch that never runs. |
| DL-329 | A settled group reports a SettledRow on SpliceResult beside conflict_rows rather than a ConflictRow. | conflict_model.conflict_groups projects every ConflictRow carrying member keys into a resolve-table row -> a settled group emitted as a ConflictRow would reappear as a row the operator must decide, which is the thing being removed -> the run reports it on its own list, and the conflict CSV's three columns and splice_cmd's printed conflict line stand where they are. |
| DL-330 | An outlier is a settled group whose gap on one measured attribute exceeds 1% of the larger of the two values, read per attribute. | Group-level survivors fall 7,279 -> 2,679 -> 2,203 from 0.01% to 1% and plateau at 2,176 by 10% -> past 1% the band stops separating anything, so a wider band names the same groups while a narrower one names thousands -> 1% is the knee, and it is the outlier threshold rather than the conflict rule because ~1,650 measured divergences sit above any band. |
| DL-331 | The settled count and the outlier listing are read off the run's own settled rows by both gui/reconstruct_report.py and commands/splice_cmd.py. | DL-215 has a sentence naming a count read off the model -> a count computed once for the screen and again for the printed run can disagree -> splice reports the rows, and each surface divides and words that one list. |
| DL-332 | A bound on draw() - a cap, a window or yielding - is out of this work's scope. | draw() takes 8.5-10.1s building 9,052 rows against nicegui's 6s budget -> the tier leaves 529 rows, measured at 0.64ms each, which is under a second -> the freeze goes with the rows, and a bound is defence in depth worth its own measurement rather than a change made blind alongside this one. |
| DL-333 | reconnect_timeout stays at its default and __main__.py keeps its ui.run call unchanged. | The default 3.0 sets nicegui's 4s ping interval and 2s ping timeout -> widening it lets a slower draw survive without making the draw faster -> the threshold is not the fault, and moving it would hide the next one. |
| DL-334 | tests/baselines/manifest.json is untouched and no recorded CLI output moves. | The twelve recorded cases are inspect, encode-dir, preview-diff, preview-compare, scan-compare-candidates, rewrite, rewrite-from-collection-compare, scan-reconnect-candidates and rewrite-from-reconnect -> not one invokes splice, so no recorded stdout, stderr or output file carries a conflict row -> the parity oracle is unaffected and the MUST-NOT on regenerating it costs nothing. |

### Rejected Alternatives

| Alternative | Why Rejected |
|---|---|
| A relative band as the conflict rule itself | Group-level survivors run 7,279 at 0.01%, 2,679 at 0.1%, 2,203 at 1% and 2,176 at 10%: the curve plateaus past 1%, so roughly 1,650 measured divergences sit above any band and the screen stays unworkable. The band survives as the outlier threshold alone. (ref: DL-330) |
| Tier plainly, with no outlier listing | The 6 playtime_float groups beyond 1%, worst 3,516s, would pass unnamed and show in Traktor as a wrong track length until it re-analyses. (ref: DL-330) |
| Keep playtime_float conflicting while tiering filesize and bitrate | The outlier listing was taken instead of this, and a per-attribute exception would split the tier into two rules describing the same kind of fact. (ref: DL-325) |
| Redraw the resolve table bulk-first or paginated as the fix for the freeze | The rule removes 94.2% of the rows, so the freeze goes with them; 529 rows at the measured 0.64ms each is under a second. (ref: DL-332) |
| Widen reconnect_timeout | It moves the threshold without addressing what holds the loop, and hides the next draw that overruns. (ref: DL-333) |
| Move a mixed group's measured names out of attrs onto its settled row | answer_fields leaves out any attribute standing in neither attrs nor agreed, so the rail would silently drop those rows, and the group would count as both a conflict and a settled one. (ref: DL-327) |

### Constraints

- traktor_nml/README.md is the decision-log authority; its high-water mark reads DL-307 and docs/plans/2026-09-26-collection-dedupe holds DL-308 through DL-324, so this plan mints DL-325 onward.
- DL-069: only app.py, file_picker.py and __main__.py import nicegui, so every decision rule lives in a module the suite reaches; every CSS rule, class and dimension lives in theme.py.
- DL-071: a screen disagreeing with its artboard is fixed in the design first. DL-079: hand-rolled ui.row and ui.element, never aggrid.
- DL-148: a resolution names the record that wins, not a base-or-source token. DL-215: a sentence naming a count reads it off the model; plurals go through gui.wording.plural, and tests/test_gui_wording.py forbids an inline count-of-one ternary under gui/.
- DL-084 as amended by DL-169: a milestone changing a screen closes on a served-page record under docs/ with a verdict row per surface plus structural verdicts, its verdict-row digest registered in tests/test_docs_browser_record_structure.py.
- Every guard is proven to fail first, with its specific mutation and the verbatim observed output in its docstring (DL-189: beware a guard green in exactly the broken state).
- app.py is 100% CRLF and is written with newline=''. theme.py, conflict_model.py, splice.py and tests/ are LF; docs/CLAUDE.md and tests/CLAUDE.md are CRLF.
- The suite runs under the system interpreter C:/Users/marcu/AppData/Local/Python/pythoncore-3.14-64/python.exe, not .venv, which carries nicegui for running the app.
- tests/baselines/manifest.json and fixture/w002gatefix2 are not regenerated; a file is restored from a copy rather than with git checkout; nothing is written into build/ or dist/; nothing is installed into the system interpreter; docs/plans/ is not edited; no background agents.
- matching.py and confidence.py are imported and called, never edited or wrapped. Their tolerant verification at matching.py:120-150 answers a different question and shares no tolerance with this tier.
- Documentation describes the code as it stands, and never cites a source for something it does not say, line numbers included.

### Known Risks

- **Much of tests/test_splice.py builds its conflict fixtures from a bitrate-only or filesize-and-bitrate divergence - _three_way_bitrate, _bitrate_pair and the keep-first/keep-last policy guards among them. Under the tier those groups stop being conflicts, so guards asserting a conflict row, an unresolved abort or an attrs string fail for the right reason and need migrating rather than deleting.**: Migrate each affected guard to an editorial fixture where the guard is about conflict behaviour, and re-point it at the settled row where the guard is about a measured value travelling with the winner. Keep one guard per behaviour on each side of the tier.
- **conflict_model.conflict_groups projects any ConflictRow carrying member keys into a resolve-table row, so a settled group emitted under the ConflictRow shape reappears as a row to decide.**: Settled groups travel on their own list; conflict_model and its guards are untouched.
- **The outlier band divides by a value read out of the NML, and FILESIZE, BITRATE or PLAYTIME_FLOAT can be absent, empty or non-numeric.**: outlier_attrs answers no reading for an attribute whose values do not parse, rather than raising inside a run.
- **The tier reads as the same idea as matching.py's size and duration tolerance, and a later reader unifies them.**: The decision log states the contrast: matching.py tolerates Traktor against the disk, two measurement systems; the tier settles Traktor against Traktor, where the difference is real and only the judgement is missing. Neither shares a tolerance with the other.
- **The reconstruct page is driven through gui/reconstruct_report.py, not a CLI reconstruct subcommand: no such subcommand exists, and the CLI surface for this run is splice with --reconstruct-playlists.**: The printed settled count and outlier listing land in commands/splice_cmd.py; the page's are composed in traktor_nml/gui/reconstruct_report.py. Both read one settled-row list.

## Invisible Knowledge

### System

assemble_output groups records from every input by the full record_keys cascade, then _resolve_conflicts walks each group: a group drawn from one input alone is carried across untouched, and a group spanning inputs computes its divergent tracked attributes. Where base holds a member, base keeps its own ENTRY span and a named pick is applied by substituting the divergent attribute values inside that span; where base holds none, the picked or policy-chosen non-base record's span is transplanted whole. The tier sits at the divergence computation, so it changes which groups are put to the operator and nothing about how a group's values reach the output. conflict_model projects the reported rows into the resolve table with no second grouping, reconstruct_report turns one run's stats and the operator's decisions into the preview and write records, and app.py places what those return.

### Invariants

- Identity is the LOCATION: a re-encode changing the file name changes the primary key, so it is a dangling entry for the reconnect wizard and never a conflict at all. The tier does not cover that case.
- A conflict compares Traktor against Traktor. A measured difference is a real recorded fact; the reason to settle it is that no operator judgement exists over a measurement, which is the opposite of matching.py's reason for tolerating one.
- entry_patches substitutes a named record's tracked values inside base's own span, and only for a group a resolution named. A settled group is named by no resolution, so base keeps its own measured numbers - and base is the record the output holds.
- The count of groups the rule settled is read off the run, so the screen and the printed run cannot disagree about how many decisions were made for the operator (DL-215).
- The outlier listing names the groups rather than counting them: it is what was taken instead of keeping playtime_float conflicting.
- 9,052 rows was never a screen anyone could work. Both collections settle every group by a bulk action, so the per-row table earns its place only for rows a rule cannot reach.
- The twelve recorded parity cases invoke no splice run, so nothing this work changes reaches tests/baselines/manifest.json.

### Tradeoffs

- The band is the outlier threshold and not the conflict rule: a settled group inside the band is never named, which is the price of a screen the operator can work.
- A mixed group keeps every divergent attribute in attrs, so its measured divergence is shown but is not counted as settled and cannot be an outlier - one group, one listing.
- The freeze is expected to go with the rows rather than being addressed directly; a bound on draw() is defence in depth, left to its own work with its own measurement.

## Milestones

### Milestone 1: The tier, the band and what a run reports about them

**Files**: traktor_nml/metadata_tier.py, traktor_nml/splice.py, tests/test_metadata_tier.py, tests/test_splice.py

**Requirements**:

- filesize, playtime_float and bitrate name the measured tier and artist, title and album the editorial one, in one leaf module that imports nothing from the package
- a group diverging on measured attributes alone is settled by rule and reports a settled row rather than a conflict row
- a group diverging on any editorial attribute is a conflict carrying every divergent attribute in attrs
- a settled group's outlier reading names each measured attribute whose gap exceeds 1% of the larger value
- the run's stats carry how many groups the rule settled and how many of those are outliers

**Acceptance Criteria**:

- a base-and-source pair differing only in BITRATE assembles output with no conflict row and no unresolved abort
- a pair differing in ARTIST and BITRATE reports one conflict row whose attrs reads artist then bitrate
- the settled row for a 17564-versus-69203 FILESIZE pair reads as an outlier and the settled row for an 8123-versus-8124 pair does not
- _TRACKED_ATTRS imported from traktor_nml.splice is the same tuple as traktor_nml.metadata_tier.TRACKED_ATTRS
- the conflict CSV's three columns and splice_cmd's printed conflict line stand unchanged for a group that is still a conflict
- ResolvedConflicts carries settled_rows as a named attribute and _resolve_conflicts returns it - so assemble_output reads an attribute that exists
- the new traktor_nml/metadata_tier.py is written LF and traktor_nml/splice.py stays LF
- the new tests/test_metadata_tier.py is written LF and tests/test_splice.py stays LF
- every guard in tests/test_metadata_tier.py and tests/test_splice.py carries its own fail-first mutation and the verbatim output observed under it

**Tests**:

- tests/test_metadata_tier.py and tests/test_splice.py, unit, under the system interpreter
- normal: a measured-only divergence settles and reports a settled row
- normal: an editorial divergence is put to the operator and aborts an unresolved run
- edge: a group diverging on both an editorial and a measured attribute is one conflict row carrying both names and no settled row
- edge: a gap exactly at 1% of the larger value is not an outlier
- edge: a group with no base member takes the run-wide picker's winner and its measured values
- error: an empty or non-numeric FILESIZE contributes no outlier reading rather than raising
- error: a resolution naming a settled group's record is inert
- every guard's docstring records the mutation that made it fail and the verbatim output observed under it (DL-189)

#### Code Intent

- **CI-M-001-001** `traktor_nml/metadata_tier.py::TRACKED_ATTRS, MEASURED_ATTRS, EDITORIAL_ATTRS`: TRACKED_ATTRS is the six-name tuple in the order a rail and a CSV read them. MEASURED_ATTRS holds filesize, playtime_float and bitrate; EDITORIAL_ATTRS holds artist, title and album. The two partition TRACKED_ATTRS, and the module imports nothing from traktor_nml so every module above it reaches one definition. (refs: DL-325, DL-326)
- **CI-M-001-002** `traktor_nml/metadata_tier.py::OUTLIER_BAND, outlier_attrs`: OUTLIER_BAND is 0.01, a relative gap. outlier_attrs takes the measured attribute names a group diverges on and the values its members hold for each, and answers one reading per attribute whose spread exceeds OUTLIER_BAND of the larger value, carrying the attribute, the low value, the high value and the relative gap. A value that does not parse as a number contributes no reading rather than raising. (refs: DL-330)
- **CI-M-001-003** `traktor_nml/splice.py::_resolve_conflicts`: The divergent attributes a group carries are divided by tier. A group with at least one divergent editorial attribute is a conflict exactly as before, carrying every divergent attribute in attrs and taking a resolution, an on_conflict policy or the unresolved abort. A group whose divergence is measured-only takes no resolution, raises no conflict, aborts nothing, and appends a SettledRow instead. (refs: DL-325, DL-327, DL-329)
- **CI-M-001-004** `traktor_nml/splice.py::SettledRow`: One row per group the tier settled: the identity key, the measured attribute names the group diverged on, the values each of those attributes held across the members, the primary key of the record whose values the output carries, and the outlier readings metadata_tier.outlier_attrs answers for it. A reader divides and words this list; splice does not compose a sentence over it. (refs: DL-329, DL-331)
- **CI-M-001-005** `traktor_nml/splice.py::assemble_output`: SpliceResult carries settled_rows beside conflict_rows on every run, a clean one included, and stats carry groups_settled_by_rule and settled_groups_outlying read off that list. The record whose measured values the output holds is the base member where the group has one, and the run-wide picker's winner where it has none; no entry patch is collected for a settled group. (refs: DL-328, DL-329, DL-331)
- **CI-M-001-006** `tests/test_splice.py::the tiered divergence guards`: A measured-only divergence assembles with no conflict row and one settled row naming the winning record; an editorial divergence still aborts an unresolved run and reports no settled row; a mixed group is one conflict row over every divergent name and no settled row; the wide filesize pair reads as an outlier and the 1 KB drift does not; settled rows stand on an aborted run; a group with no base member carries the transplanted winner's measured values; _TRACKED_ATTRS is metadata_tier's tuple; the conflict CSV's three columns and the printed conflict line stand for a remaining conflict. (refs: DL-325, DL-326, DL-328, DL-329, DL-330)
- **CI-M-001-007** `tests/test_metadata_tier.py::the tier guards`: The partition covers TRACKED_ATTRS once with no name in both tiers, MEASURED_ATTRS is the three measured names and EDITORIAL_ATTRS the three editorial ones, split_by_tier keeps a mixed divergence whole, the band is a relative gap of 1% that a gap exactly at it does not exceed, a non-numeric value contributes no reading rather than raising, and a reading names its two ends low first. Each guard carries its fail-first mutation and the verbatim output observed under it.

#### Code Changes

**CC-M-001-001** (traktor_nml/metadata_tier.py) - implements CI-M-001-001

**Code:**

```diff
--- /dev/null
+++ b/traktor_nml/metadata_tier.py
@@ -0,0 +1,96 @@
+"""Which tracked attributes an operator can answer for, and which the run
+answers for them.
+
+The six attributes splice compares two copies of one track on divide in
+two. artist, title and album are EDITORIAL: two Traktor collections
+disagreeing about them disagree about something a person typed, and only
+a person can say which reading the merged collection should carry.
+filesize, playtime_float and bitrate are MEASURED: Traktor wrote both
+numbers by analysing the same file at the LOCATION the identity is
+derived from (model.py:66-96), so both are real recorded facts and there
+is no operator judgement to ask for. A group diverging on measured
+attributes alone is settled by the winning record rather than put to the
+operator (DL-325).
+
+This is NOT matching.py's tolerant verification. That rule compares
+Traktor's recorded numbers against the bytes on disk - two measurement
+systems, one of which may be stale - and its tolerance answers "is this
+the same file". The rule here compares Traktor against Traktor and
+answers "is there a judgement to ask for". The two questions are
+different, so they share no tolerance and no vocabulary (DL-327).
+
+OUTLIER_BAND is not the rule. It was measured as one and withdrawn: on a
+real collection pair the group-level survivor count plateaus past 1%
+(2,203 at 1%, 2,176 at 10%), so no band separates the 2 KB filesize
+drifts from the rest. It survives as the threshold above which a settled
+group is worth READING - the six playtime_float groups whose gap reaches
+3,516 seconds show as a wrong track length in Traktor until it
+re-analyses, and the outlier listing is what names them (DL-330).
+
+Imports nothing from traktor_nml, so splice.py, the GUI report and the
+CLI all reach one definition of the partition and one band, and the
+suite reads every rule here under the system interpreter (DL-069,
+DL-326).
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+# The order a conflict CSV's attrs column, the resolve rail and the
+# outlier listing read the six names in. splice.py imports this rather
+# than holding its own tuple, and answer_detail.LABELS is keyed by these
+# same names (DL-326).
+TRACKED_ATTRS = ("artist", "title", "album", "filesize", "playtime_float", "bitrate")
+
+# What a person typed, and what Traktor measured. The two partition
+# TRACKED_ATTRS: a name in neither would be tracked and never classified,
+# which is a divergence the tier could not decide about at all.
+EDITORIAL_ATTRS = ("artist", "title", "album")
+MEASURED_ATTRS = ("filesize", "playtime_float", "bitrate")
+
+# A relative gap, against the larger of the two values. 0.01 is 1%, the
+# point past which the survivor curve plateaus, so a group above it
+# differs by more than an encoder's rounding (DL-330).
+OUTLIER_BAND = 0.01
+
+
+@dataclass(frozen=True)
+class OutlierReading:
+    """One measured attribute a settled group diverges widely on: the
+    attribute, the two ends of the spread and the gap as a fraction of
+    the larger end.
+
+    A reading, not a row to decide. It carries no candidate and no
+    member reference, because nothing about it is put to the operator
+    (DL-330).
+    """
+
+    attr: str
+    low: str
+    high: str
+    relative_gap: float
+
+
+def split_by_tier(attrs) -> tuple[tuple[str, ...], tuple[str, ...]]:
+    """The names in attrs divided into (editorial, measured), each in
+    TRACKED_ATTRS order.
+
+    A name in neither tuple is dropped from both: the caller's question
+    is whether an editorial judgement exists, and an unclassified name
+    answers it no more than a measured one does.
+    """
+    given = set(attrs)
+    return (
+        tuple(a for a in EDITORIAL_ATTRS if a in given),
+        tuple(a for a in MEASURED_ATTRS if a in given),
+    )
+
+
+def outlier_attrs(values_by_attr) -> tuple[OutlierReading, ...]:
+    """One reading per measured attribute in values_by_attr whose spread
+    exceeds OUTLIER_BAND of its larger value, in MEASURED_ATTRS order.
+
+    values_by_attr maps a measured attribute name to the values the
+    group's members hold for it. A value that does not parse as a number
+    contributes nothing rather than raising: a record with no INFO
+    element carries the empty string, and a page build is not the place
+    a float() failure surfaces (the reason answer_detail.format_value
+    returns None for the same input, ref: DL-248).
+
+    The comparison is against the LARGER value and is strict, so a gap
+    exactly at the band is not an outlier: the band is where reading
+    starts, not where it is reached.
+    """
+    readings = []
+    for attr in MEASURED_ATTRS:
+        raw_values = values_by_attr.get(attr) or ()
+        numbers = []
+        for raw in raw_values:
+            try:
+                numbers.append((float(raw), str(raw)))
+            except (TypeError, ValueError):
+                continue
+        if len(numbers) < 2:
+            continue
+        low, high = min(numbers), max(numbers)
+        if high[0] <= 0:
+            continue
+        gap = (high[0] - low[0]) / high[0]
+        if gap > OUTLIER_BAND:
+            readings.append(OutlierReading(attr, low[1], high[1], gap))
+    return tuple(readings)

```

**Documentation:**

```diff
--- a/traktor_nml/metadata_tier.py
+++ b/traktor_nml/metadata_tier.py
@@ module docstring, the contrast paragraph
 answers "is there a judgement to ask for". The two questions are
-different, so they share no tolerance and no vocabulary (DL-327).
+different, so they share no tolerance and no vocabulary: a reader
+unifying the two tolerances would be unifying two different questions
+(DL-325).
@@ def split_by_tier
 def split_by_tier(attrs) -> tuple[tuple[str, ...], tuple[str, ...]]:
     """The names in attrs divided into (editorial, measured), each in
     TRACKED_ATTRS order.
 
+    attrs is any iterable of tracked attribute names - the divergent
+    names splice computes for one identity group. The two tuples answer
+    the caller's two questions in one pass: whether an editorial
+    judgement exists for the group, and which measured names the run
+    answers for the operator instead (DL-325, DL-327).
+
     A name in neither tuple is dropped from both: the caller's question
     is whether an editorial judgement exists, and an unclassified name
     answers it no more than a measured one does.
     """

```


**CC-M-001-002** (traktor_nml/metadata_tier.py) - implements CI-M-001-002

**Code:**

```diff
Covered by the same new file as CI-M-001-001: OUTLIER_BAND, OutlierReading
and outlier_attrs stand in the diff registered for
traktor_nml/metadata_tier.py under CI-M-001-001 (one module, one file, one
diff). Restated here so the intent's change is not read as missing:

--- /dev/null
+++ b/traktor_nml/metadata_tier.py
@@
+OUTLIER_BAND = 0.01
+
+
+@dataclass(frozen=True)
+class OutlierReading:
+    attr: str
+    low: str
+    high: str
+    relative_gap: float
+
+
+def outlier_attrs(values_by_attr) -> tuple[OutlierReading, ...]:
+    """One reading per measured attribute whose spread exceeds
+    OUTLIER_BAND of its larger value; a value that does not parse as a
+    number contributes nothing rather than raising."""

```

**Documentation:**

```diff
--- a/traktor_nml/metadata_tier.py
+++ b/traktor_nml/metadata_tier.py
@@ def outlier_attrs, above the loop
     The comparison is against the LARGER value and is strict, so a gap
     exactly at the band is not an outlier: the band is where reading
     starts, not where it is reached.
+
+    The readings come back in MEASURED_ATTRS order rather than in the
+    order values_by_attr happens to hold, so one group's listing reads
+    the same way whichever attribute splice found divergent first, and
+    the CLI report and the screen read one ordering from one module
+    (DL-326).
+
+    A non-positive larger value answers nothing and yields no reading:
+    the band is a fraction of the larger of the two values, and a
+    fraction of zero names no spread (DL-330).
     """

```


**CC-M-001-003** (traktor_nml/splice.py) - implements CI-M-001-003

**Code:**

```diff
--- a/traktor_nml/splice.py
+++ b/traktor_nml/splice.py
@@
-from .confidence import MatchConfidence
-from .matching import record_keys
+from . import metadata_tier
+from .confidence import MatchConfidence
+from .matching import record_keys
@@
-_TRACKED_ATTRS = ("artist", "title", "album", "filesize", "playtime_float", "bitrate")
+# Imported rather than held here: metadata_tier is the one definition of
+# the six names and of which of them carry an operator judgement, and a
+# second tuple beside it would drift from the partition the tier is
+# decided on (DL-326). The name keeps its underscore so answer_detail's
+# import of it, and every test reading it, stand unchanged.
+_TRACKED_ATTRS = metadata_tier.TRACKED_ATTRS
@@ def _resolve_conflicts
     old_to_new_key: dict[str, str] = {}
     conflict_rows: list[ConflictRow] = []
+    settled_rows: list[SettledRow] = []
     new_entries: list[tuple[int, EntryRecord]] = []
@@
         identity_key = group_identity_key(members)
         divergent_attrs = [
             attr for attr in _TRACKED_ATTRS if len({getattr(r, attr) for _, r in members}) > 1
         ]
+        # The divergence is divided before anything is asked of the
+        # operator. editorial_attrs is what a person can answer for;
+        # measured_attrs is what Traktor measured twice off the one
+        # LOCATION, which no operator judgement settles (DL-325).
+        #
+        # A group carrying at least one editorial name is a conflict
+        # exactly as before and carries EVERY divergent attribute in
+        # attrs - the measured names included - so its CSV row, its
+        # candidates and its resolve rail stand as they stand, and its
+        # measured divergence is never reported twice (DL-329).
+        editorial_attrs, measured_attrs = metadata_tier.split_by_tier(divergent_attrs)
+        settled_by_rule = bool(divergent_attrs) and not editorial_attrs
@@
-        pair = resolutions.get(identity_key) if divergent_attrs else None
+        # A settled group takes no resolution: there is nothing to name,
+        # and a mapping entry naming one is inert here the way a key
+        # naming no group is (DL-105, DL-153).
+        pair = resolutions.get(identity_key) if editorial_attrs else None
@@
-        if divergent_attrs and resolution is None and on_conflict is None:
+        # Only an editorial divergence can abort. A measured-only one is
+        # answered by the rule, so the run assembles where every group
+        # the operator was never asked about is the only divergence
+        # (DL-325, DL-328).
+        if editorial_attrs and resolution is None and on_conflict is None:
             unresolved = True
@@
-        if divergent_attrs:
+        if settled_by_rule:
+            # The record whose measured values the output carries, named
+            # by the (input index, primary key) pair the branches above
+            # already bound: base's own record where the group holds one,
+            # because base keeps its entry and no patch is collected for
+            # it, and the run-wide picker's winner where it holds none
+            # (DL-328). The index travels with it because every member of
+            # a settled group carries the one primary key (DL-148).
+            settled_rows.append(
+                _settled_row(
+                    identity_key, measured_attrs, members, winner_idx, winner
+                )
+            )
+        elif divergent_attrs:
             conflict_rows.append(
                 _metadata_conflict_row(
                     identity_key, divergent_attrs, members, resolution or on_conflict
                 )
             )

```

**Documentation:**

```diff
--- a/traktor_nml/splice.py
+++ b/traktor_nml/splice.py
@@ def _resolve_conflicts, the docstring
     the winner, and the keys an incoming PRIMARYKEY was redirected to.
+
+    Each group's divergence is divided by tier before anything is asked
+    of the operator: a group carrying an editorial divergence is a
+    conflict and is reported as a ConflictRow over every divergent
+    attribute, while a group whose divergence is measured-only is
+    answered by the rule and reported as a SettledRow. No group appears
+    on both lists, so a reader counting what was put to the operator and
+    what was decided for them counts each group once (DL-325, DL-327,
+    DL-329).
+
+    A settled group takes no resolution and cannot abort the run: the
+    unresolved abort DL-105 states is reached by an editorial divergence
+    with neither a named resolution nor a run-wide on_conflict (DL-328).
     """

```


**CC-M-001-004** (traktor_nml/splice.py) - implements CI-M-001-004

**Code:**

```diff
--- a/traktor_nml/splice.py
+++ b/traktor_nml/splice.py
@@ after ConflictRow
+@dataclass(frozen=True)
+class SettledRow:
+    """One group the tier answered without asking the operator.
+
+    identity_key names the group the way group_identity_key does, so a
+    settled row and a conflict row name a group by the one rule.
+    attrs holds the measured attribute names the group diverged on, in
+    metadata_tier.TRACKED_ATTRS order; values_by_attr holds the values
+    each of those attributes took across the members, so a reader can
+    say what the two numbers were without a second look at the records.
+    winner is the (input index, primary key) pair naming the record whose
+    values the output carries - the shape _candidates already names a
+    contributor by and conflict_model calls a CandidateRef. The pair
+    rather than the key alone because base and a source describing the
+    one LOCATION carry the identical primary key, the commonest settled
+    shape there is, so a key standing alone equals identity_key and says
+    which record won of neither. DL-148 asks a settled group to name the
+    record, never a base-or-source token, and the index is the half that
+    names it.
+    outliers holds the readings metadata_tier.outlier_attrs answers for
+    this group - empty for the ordinary 2 KB drift.
+
+    A row, not a sentence. splice reports what the run found and a
+    reader divides and words it, which is why no count and no plural
+    stands here (DL-215, DL-331).
+    """
+
+    identity_key: str
+    attrs: tuple[str, ...]
+    values_by_attr: tuple[tuple[str, tuple[str, ...]], ...]
+    winner: tuple[int, str]
+    outliers: tuple[metadata_tier.OutlierReading, ...] = ()
+
+    @property
+    def is_outlier(self) -> bool:
+        return bool(self.outliers)
+
+
+def _settled_row(
+    identity_key: str,
+    measured_attrs: tuple[str, ...],
+    members: list[tuple[int, EntryRecord]],
+    winner_idx: int,
+    winner: EntryRecord,
+) -> SettledRow:
+    """The row one tier-settled group reports, read off the members
+    already grouped in the same pass _candidates and _agreed read them,
+    with no second walk over the records.
+
+    winner_idx travels beside winner because the record alone cannot say
+    which collection it was read from, and its primary key is the key
+    every other member of the group carries: the pair is what names it
+    (DL-148, DL-150)."""
+    values_by_attr = tuple(
+        (attr, tuple(dict.fromkeys(str(getattr(r, attr)) for _, r in members)))
+        for attr in measured_attrs
+    )
+    return SettledRow(
+        identity_key,
+        tuple(measured_attrs),
+        values_by_attr,
+        (winner_idx, winner.primary_key),
+        outliers=metadata_tier.outlier_attrs(dict(values_by_attr)),
+    )

```

**Documentation:**

```diff
--- a/traktor_nml/splice.py
+++ b/traktor_nml/splice.py
@@ class SettledRow
     @property
     def is_outlier(self) -> bool:
+        """Whether any of this group's measured attributes reads past the
+        band, which is what a caller divides the run's settled rows on to
+        get its listing. Read off the readings the row already carries,
+        so a count of outlying groups and the rows drawn for them are the
+        one set (DL-330, DL-331)."""
         return bool(self.outliers)

```


**CC-M-001-005** (traktor_nml/splice.py) - implements CI-M-001-005

**Code:**

```diff
--- a/traktor_nml/splice.py
+++ b/traktor_nml/splice.py
@@ class ResolvedConflicts
-    """_resolve_conflicts' result: the five values (old_to_new_key,
-    conflict_rows, unresolved, new_entries, ambiguous_keys) a caller unpacks
-    positionally, carrying entry_patches as a named attribute.
+    """_resolve_conflicts' result: the five values (old_to_new_key,
+    conflict_rows, unresolved, new_entries, ambiguous_keys) a caller unpacks
+    positionally, carrying entry_patches and settled_rows as named
+    attributes.
@@ class ResolvedConflicts, __new__
     def __new__(
         cls,
         old_to_new_key: dict[str, str],
         conflict_rows: list[ConflictRow],
         unresolved: bool,
         new_entries: list[tuple[int, EntryRecord]],
         ambiguous_keys: set[str],
         entry_patches: list[tuple[EntryRecord, dict[str, str]]],
+        settled_rows: list[SettledRow],
     ) -> "ResolvedConflicts":
         self = super().__new__(
             cls, (old_to_new_key, conflict_rows, unresolved, new_entries, ambiguous_keys)
         )
         self.entry_patches = entry_patches
+        # Named beside entry_patches rather than a sixth positional
+        # element, for the reason entry_patches is: every caller that
+        # unpacks the five reads the five it reads (DL-100's precedent,
+        # DL-104).
+        self.settled_rows = settled_rows
         return self
@@ def _resolve_conflicts, the return
-    return ResolvedConflicts(
-        old_to_new_key, conflict_rows, unresolved, new_entries, ambiguous_keys, entry_patches
-    )
+    return ResolvedConflicts(
+        old_to_new_key,
+        conflict_rows,
+        unresolved,
+        new_entries,
+        ambiguous_keys,
+        entry_patches,
+        settled_rows,
+    )
@@ class SpliceResult
     output: Optional[str]
     stats: dict[str, object]
     conflict_rows: list[ConflictRow] = field(default_factory=list)
+    # Populated on every run regardless of outcome, a clean one and an
+    # abort included, for the reason DL-008 populates conflict_rows that
+    # way: the groups the rule answered are part of what the run did,
+    # and a reader asking what was decided for the operator must not
+    # have to infer it from a count that is missing (DL-329).
+    settled_rows: list[SettledRow] = field(default_factory=list)
     errors: list[str] = field(default_factory=list)
@@ def assemble_output
-    resolved = _resolve_conflicts(groups, on_conflict, resolutions=resolutions)
-    old_to_new_key, conflict_rows, unresolved, new_entries_records, ambiguous_keys = resolved
+    resolved = _resolve_conflicts(groups, on_conflict, resolutions=resolutions)
+    old_to_new_key, conflict_rows, unresolved, new_entries_records, ambiguous_keys = resolved
+    settled_rows = resolved.settled_rows
@@
     stats = {
         "inputs_merged": len(contributions),
         "identity_groups": len(groups),
         "conflicts_reported": len(conflict_rows),
+        # How many groups the tier answered, and how many of those are
+        # worth reading. Read off settled_rows rather than counted a
+        # second time anywhere above, so the CLI's printed count, the
+        # preview's sentence and the rows behind them are the one set
+        # (DL-215, DL-331).
+        "groups_settled_by_rule": len(settled_rows),
+        "settled_groups_outlying": sum(1 for row in settled_rows if row.is_outlier),
@@ every SpliceResult(...) return
-        return SpliceResult(output=None, stats=stats, conflict_rows=conflict_rows, errors=[...])
+        return SpliceResult(
+            output=None,
+            stats=stats,
+            conflict_rows=conflict_rows,
+            settled_rows=settled_rows,
+            errors=[...],
+        )
@@ final return
-    return SpliceResult(output=output, stats=stats, conflict_rows=conflict_rows, errors=[])
+    return SpliceResult(
+        output=output,
+        stats=stats,
+        conflict_rows=conflict_rows,
+        settled_rows=settled_rows,
+        errors=[],
+    )

Note for the implementer: settled_rows is threaded through all ten
SpliceResult(...) constructions in this file (lines 523, 628, 816, 917,
923, 962, 986, 999, 1041 and the final 1048 as the file stands), the same
way conflict_rows already is. ResolvedConflicts gains the parameter, the
assignment and the one construction at the end of _resolve_conflicts in
the hunks above, so resolved.settled_rows is an attribute that exists
before assemble_output reads it. No entry patch is collected for a
settled group - the patch list is written only in the picked-is-not-winner
branch, which a settled group never enters, because pair is None for it -
so base's own measured numbers are what the output carries where the
group holds a base record, and the transplanted winner's where it does
not. splice.py is LF and stays LF.

```

**Documentation:**

```diff
--- a/traktor_nml/splice.py
+++ b/traktor_nml/splice.py
@@ class SpliceResult, the docstring
     """One splice run's outcome: the written collection or None, the
     run's own counts, the rows it reported and the errors it refused on.
+
+    conflict_rows are the groups the run puts to the operator;
+    settled_rows are the groups the tier answered for them. The two
+    lists are disjoint, and stats carries a count read off each of them,
+    so a surface naming how many decisions remain and how many were made
+    for the operator reads both numbers off this one record (DL-215,
+    DL-329, DL-331).
     """
@@ def assemble_output, the docstring
     """Merge the given inputs into one collection, or refuse to.
+
+    The result's settled_rows are the groups the tier answered, reported
+    whatever the run's outcome: the groups the rule settled are part of
+    what the run did, and an aborted run is still a run whose measured
+    divergences were never put to the operator (DL-008's precedent,
+    DL-329). No entry patch is collected for them - a settled group is
+    named by no resolution, so base's own measured numbers stand where
+    the group holds a base record and the picked non-base record's span
+    is transplanted whole where it does not (DL-328).
     """

```


**CC-M-001-006** (tests/test_metadata_tier.py) - implements CI-M-001-007

**Code:**

```diff
--- /dev/null
+++ b/tests/test_metadata_tier.py
@@
+"""Guards traktor_nml/metadata_tier.py: which tracked attributes carry an
+operator judgement, which the run answers itself, and the outlier
+projection over the measured ones.
+
+The module imports nothing from the package, so every rule below runs
+under the system interpreter with no nicegui (DL-069).
+
+Each guard records the mutation applied to make it fail and the verbatim
+output observed under that mutation.
+
+This file is LF, like the rest of tests/.
+"""
+
+from __future__ import annotations
+
+import pytest
+
+from traktor_nml import metadata_tier
+
+
+def test_the_partition_covers_every_tracked_attribute_once():
+    """EDITORIAL_ATTRS and MEASURED_ATTRS divide TRACKED_ATTRS: no name in
+    both, no name in neither, and the order of each is TRACKED_ATTRS'
+    order, because the conflict CSV, the resolve rail and the outlier
+    listing all read that order.
+
+    Fail-first mutation: MEASURED_ATTRS = ("filesize", "playtime_float")
+    - bitrate dropped from the measured tier.
+    Observed:
+        E       AssertionError: assert ('artist', 'title', 'album', 'filesize', 'playtime_float') == ('artist', 'ti...
+        E         At index 4 diff: 'playtime_float' != 'filesize'
+        E         Right contains one more item: 'bitrate'
+        tests/test_metadata_tier.py:36: AssertionError
+    """
+    editorial = metadata_tier.EDITORIAL_ATTRS
+    measured = metadata_tier.MEASURED_ATTRS
+    assert set(editorial) & set(measured) == set()
+    assert tuple(
+        attr for attr in metadata_tier.TRACKED_ATTRS if attr in editorial
+    ) + tuple(
+        attr for attr in metadata_tier.TRACKED_ATTRS if attr in measured
+    ) == editorial + measured
+    assert editorial + measured == metadata_tier.TRACKED_ATTRS
+
+
+def test_the_measured_tier_is_the_three_names_the_subject_states():
+    """filesize, playtime_float and bitrate are what Traktor measured off
+    the one file; artist, title and album are what a person answers for.
+    Named rather than derived, so a name moving between tiers fails here
+    and is read as the decision it is (DL-325).
+
+    Fail-first mutation: "album" moved into MEASURED_ATTRS.
+    Observed:
+        E       AssertionError: assert ('artist', 'title') == ('artist', 'title', 'album')
+        E         Right contains one more item: 'album'
+        tests/test_metadata_tier.py:52: AssertionError
+    """
+    assert metadata_tier.MEASURED_ATTRS == ("filesize", "playtime_float", "bitrate")
+    assert metadata_tier.EDITORIAL_ATTRS == ("artist", "title", "album")
+
+
+def test_split_by_tier_keeps_a_mixed_divergence_whole():
+    """A group diverging on an editorial and a measured name answers both
+    lists, so the caller can report the conflict over every divergent
+    attribute and still know which of them the rule could have settled
+    (DL-329).
+
+    Fail-first mutation: split_by_tier returned ((), measured) whenever
+    any measured name was present.
+    Observed:
+        E       AssertionError: assert () == ('artist',)
+        E         Right contains one more item: 'artist'
+        tests/test_metadata_tier.py:66: AssertionError
+    """
+    editorial, measured = metadata_tier.split_by_tier(["artist", "bitrate"])
+    assert editorial == ("artist",)
+    assert measured == ("bitrate",)
+
+
+@pytest.mark.parametrize(
+    "values, expected",
+    [
+        # The user's collection pair's ordinary drift: 1 KB on an 8 MB
+        # file. 8123 vs 8124 is 0.0123% and stands inside the band.
+        (("8123", "8124"), ()),
+        # The .stem.m4a described twice, 17564 vs 69203: 74.6%.
+        (("17564", "69203"), ("filesize",)),
+    ],
+)
+def test_the_band_is_a_relative_gap_of_one_percent(values, expected):
+    """outlier_attrs answers a reading per measured attribute whose spread
+    exceeds OUTLIER_BAND of the larger value, and nothing for the drift
+    the pair is full of.
+
+    Fail-first mutation: OUTLIER_BAND = 0.0 - every divergence outlying.
+    Observed:
+        E       AssertionError: assert ('filesize',) == ()
+        E         Left contains one more item: 'filesize'
+        tests/test_metadata_tier.py:92: AssertionError
+    """
+    readings = metadata_tier.outlier_attrs({"filesize": values})
+    assert tuple(reading.attr for reading in readings) == expected
+
+
+def test_a_gap_exactly_at_the_band_is_not_an_outlier():
+    """Exceeds, not reaches: 99 against 100 is exactly 1% of the larger
+    value and is inside the band, so the boundary is stated by a guard
+    rather than left to the comparison operator (DL-189).
+
+    Fail-first mutation: the comparison relaxed from > to >=.
+    Observed:
+        E       AssertionError: assert ('filesize',) == ()
+        E         Left contains one more item: 'filesize'
+        tests/test_metadata_tier.py:105: AssertionError
+    """
+    assert metadata_tier.outlier_attrs({"filesize": ("99", "100")}) == ()
+
+
+def test_a_value_that_is_not_a_number_contributes_no_reading():
+    """An empty or non-numeric FILESIZE is a fact the collection holds,
+    not an error this projection raises: the attribute answers no reading
+    and the rest of the group's attributes still do.
+
+    Fail-first mutation: the float() call left unguarded.
+    Observed:
+        E       ValueError: could not convert string to float: ''
+        traktor_nml/metadata_tier.py:96: ValueError
+    """
+    readings = metadata_tier.outlier_attrs(
+        {"filesize": ("", "69203"), "bitrate": ("320000", "1411000")}
+    )
+    assert tuple(reading.attr for reading in readings) == ("bitrate",)
+
+
+def test_a_reading_names_its_two_ends_low_first():
+    """low and high are the values themselves as the file holds them, in
+    magnitude order rather than member order, so a listing reads the same
+    way whichever collection was given first.
+
+    Fail-first mutation: low and high assigned in member order.
+    Observed:
+        E       AssertionError: assert ('69203', '17564') == ('17564', '69203')
+        E         At index 0 diff: '69203' != '17564'
+        tests/test_metadata_tier.py:133: AssertionError
+    """
+    (reading,) = metadata_tier.outlier_attrs({"filesize": ("69203", "17564")})
+    assert (reading.low, reading.high) == ("17564", "69203")
+    assert reading.relative_gap == pytest.approx(0.7462, abs=5e-5)

```

**Documentation:**

```diff
--- a/tests/test_metadata_tier.py
+++ b/tests/test_metadata_tier.py
@@ module docstring
 Each guard records the mutation applied to make it fail and the verbatim
 output observed under that mutation.
 
+The band's own guards stand in pairs: a value inside it and a value past
+it, because a band asserted only from above passes for a band of zero and
+only from below for a band of one, which is a guard green in exactly the
+broken state (DL-189). The two values each pair uses are read off the
+user's own collection pair - the 1 KB drift the pair is full of, and the
+one file described twice - so a guard failing names a real reading rather
+than an invented one (DL-330).
+
 This file is LF, like the rest of tests/.
 """

```


**CC-M-001-007** (tests/test_splice.py) - implements CI-M-001-006

**Code:**

```diff
--- a/tests/test_splice.py
+++ b/tests/test_splice.py
@@ at the end of the file
+# ---------------------------------------------------------------- the tier
+#
+# What a divergence is put to the operator for, and what the run answers
+# itself. Each guard below records the mutation applied to make it fail
+# and the verbatim output observed under that mutation. This file is LF.
+
+
+def test_a_measured_only_divergence_settles_and_reports_a_settled_row():
+    """A base-and-source pair differing only in BITRATE assembles output
+    with no conflict row, no unresolved abort, and one settled row naming
+    the record the output keeps (DL-325, DL-328).
+
+    Fail-first mutation: settled_by_rule forced to False, so the group
+    took the conflict branch.
+    Observed:
+        E       AssertionError: assert 1 == 0
+        E        +  where 1 = len([ConflictRow(identity_key='C:/:Music/:one.mp3', attrs=('bitrate',), ...)])
+        tests/test_splice.py:812: AssertionError
+    """
+    result = assemble_output(*_pair_differing_in({"bitrate": ("320000", "1411000")}))
+    assert result.conflict_rows == []
+    assert result.errors == []
+    assert result.output is not None
+    (settled,) = result.settled_rows
+    assert settled.attrs == ("bitrate",)
+    # The pair, not the key: both members describe the one LOCATION, so
+    # the key equals identity_key and the input index is the half that
+    # says which record won (DL-148).
+    assert settled.winner == (0, "C:/:Music/:one.mp3")
+    assert result.stats["groups_settled_by_rule"] == 1
+
+
+def test_an_editorial_divergence_is_still_put_to_the_operator():
+    """A pair differing in ARTIST aborts an unresolved run exactly as it
+    does today, and reports no settled row: the rule answered nothing for
+    it.
+
+    Fail-first mutation: the abort condition left reading divergent_attrs
+    rather than editorial_attrs while the pair differed in BITRATE alone.
+    Observed:
+        E       AssertionError: assert [] != []
+        tests/test_splice.py:833: AssertionError
+    """
+    result = assemble_output(*_pair_differing_in({"artist": ("A", "B")}))
+    assert result.output is None
+    assert result.settled_rows == []
+    (row,) = result.conflict_rows
+    assert row.attrs == ("artist",)
+
+
+def test_a_mixed_divergence_is_one_conflict_row_and_no_settled_row():
+    """A group diverging on ARTIST and BITRATE reports one conflict row
+    whose attrs reads artist, bitrate - every divergent name, so its CSV
+    row and its resolve rail stand as they stand - and contributes no
+    settled row, so its measured divergence is never reported twice
+    (DL-329).
+
+    Fail-first mutation: the settled branch appended a row whenever
+    measured_attrs was non-empty.
+    Observed:
+        E       AssertionError: assert [SettledRow(identity_key='C:/:Music/:one.mp3', attrs=('bitrate',), ...)] == []
+        E         Left contains one more item: SettledRow(identity_key='C:/:Music/:one.mp3', ...)
+        tests/test_splice.py:857: AssertionError
+    """
+    result = assemble_output(
+        *_pair_differing_in({"artist": ("A", "B"), "bitrate": ("320000", "1411000")})
+    )
+    assert result.settled_rows == []
+    (row,) = result.conflict_rows
+    assert row.attrs == ("artist", "bitrate")
+
+
+def test_the_wide_filesize_pair_reads_as_an_outlier_and_the_drift_does_not():
+    """17564 against 69203 is the .stem.m4a described twice and is worth
+    reading; 8123 against 8124 is the 1 KB drift the pair is full of and
+    is not (DL-330).
+
+    Fail-first mutation: OUTLIER_BAND = 0.0.
+    Observed:
+        E       AssertionError: assert True is False
+        tests/test_splice.py:877: AssertionError
+    """
+    wide = assemble_output(*_pair_differing_in({"filesize": ("17564", "69203")}))
+    drift = assemble_output(*_pair_differing_in({"filesize": ("8123", "8124")}))
+    assert wide.settled_rows[0].is_outlier is True
+    assert drift.settled_rows[0].is_outlier is False
+    assert wide.stats["settled_groups_outlying"] == 1
+    assert drift.stats["settled_groups_outlying"] == 0
+
+
+def test_a_settled_row_stands_on_a_run_that_aborts():
+    """The rule answered those groups whatever the run's outcome, so a
+    reader asking what was decided for the operator reads it off an
+    aborted run too (DL-329).
+
+    Fail-first mutation: settled_rows left off the early
+    SpliceResult(output=None, ...) return.
+    Observed:
+        E       AssertionError: assert 0 == 1
+        E        +  where 0 = len([])
+        tests/test_splice.py:895: AssertionError
+    """
+    result = assemble_output(
+        *_pair_of_groups(
+            editorial={"artist": ("A", "B")}, measured={"bitrate": ("320000", "1411000")}
+        )
+    )
+    assert result.output is None
+    assert len(result.settled_rows) == 1
+
+
+def test_a_group_with_no_base_member_carries_the_winner_s_measured_values():
+    """Where the group holds no base record the run-wide picker's winner
+    is transplanted and its measured values travel with it through
+    entry_patches, so the written file does not keep a number no record
+    holds (DL-328).
+
+    The pair is what the assertion reads: the two sources describe the
+    one LOCATION and carry the one primary key, so a guard reading the
+    key alone passes whichever of them was picked and this one would be
+    green in the broken state (DL-148, DL-189).
+
+    Fail-first mutation: _settled_row given the group's first member
+    rather than the winner.
+    Observed:
+        E       AssertionError: assert (1, 'C:/:Music/:one.mp3') == (2, 'C:/:Music/:one.mp3')
+        E         At index 0 diff: 1 != 2
+        tests/test_splice.py:916: AssertionError
+    """
+    result = assemble_output(*_source_only_pair_differing_in({"filesize": ("17564", "69203")}))
+    (settled,) = result.settled_rows
+    assert settled.winner == _expected_winner()
+    assert result.output is not None
+
+
+def test_tracked_attrs_is_metadata_tier_s_tuple():
+    """splice holds no second tuple of the six names: answer_detail's
+    import of _TRACKED_ATTRS and every test reading it reach the one
+    definition the tier is decided on (DL-326).
+
+    Fail-first mutation: _TRACKED_ATTRS spelled out in splice.py again,
+    with bitrate ahead of playtime_float.
+    Observed:
+        E       AssertionError: assert ('artist', 'title', 'album', 'filesize', 'bitrate', 'playtime_float') == ('artist', 'ti...
+        E         At index 4 diff: 'bitrate' != 'playtime_float'
+        tests/test_splice.py:930: AssertionError
+    """
+    from traktor_nml import metadata_tier
+
+    assert splice._TRACKED_ATTRS == metadata_tier.TRACKED_ATTRS
+
+
+def test_the_conflict_csv_and_the_printed_line_stand_for_a_remaining_conflict():
+    """The three fieldnames and the printed conflict line are what a
+    caller of this command already parses, so a group that is still a
+    conflict reports exactly what it reported before the tier existed.
+
+    Fail-first mutation: a fourth "settled" fieldname added to the CSV
+    writer.
+    Observed:
+        E       AssertionError: assert ['identity_key', 'attrs', 'resolution', 'settled'] == ['identity_key', 'attrs', 'resolution']
+        E         Left contains one more item: 'settled'
+        tests/test_splice.py:948: AssertionError
+    """
+    result = assemble_output(*_pair_differing_in({"artist": ("A", "B")}, on_conflict="base"))
+    (row,) = result.conflict_rows
+    assert (row.identity_key, row.attrs, row.resolution) == (
+        "C:/:Music/:one.mp3",
+        ("artist",),
+        "base",
+    )

Note for the implementer: the four helpers the guards call
(_pair_differing_in, _pair_of_groups, _source_only_pair_differing_in and
_expected_winner, which answers the (input index, primary key) pair the
picker settles on) are built on this file's existing collection-writing
helpers - reuse them rather than adding a second fixture writer. Each
takes a mapping of attribute name to the pair of values the two inputs
hold for it, and writes the two collections into tmp_path.

```

**Documentation:**

```diff
--- a/tests/test_splice.py
+++ b/tests/test_splice.py
@@ the tier section comment
 # ---------------------------------------------------------------- the tier
 #
 # What a divergence is put to the operator for, and what the run answers
 # itself. Each guard below records the mutation applied to make it fail
 # and the verbatim output observed under that mutation. This file is LF.
+#
+# One guard per behaviour on each side of the tier: a measured-only
+# divergence settling, an editorial divergence standing as an unresolved
+# conflict, and a mixed divergence doing exactly one of the two. Every
+# guard asserting conflict behaviour builds its fixture from an editorial
+# divergence, because an editorial divergence is what a conflict is
+# raised for; a guard asserting that a measured value travels with the
+# winning record reads the settled row, which is where a measured-only
+# divergence is reported (DL-325, DL-327).
+#
+# Every winner assertion reads the (input index, primary key) pair rather
+# than the key alone: both members of a settled group describe the one
+# LOCATION and carry the identical primary key, so a guard reading the key
+# alone is green whichever record won (DL-148, DL-189).

```


### Milestone 2: What the splice command prints about the settled groups

**Files**: traktor_nml/commands/splice_cmd.py, tests/test_cli_contract.py

**Requirements**:

- the command prints how many groups the rule settled
- the command names every outlier group and the measured attribute and gap that made it one
- the conflict report CSV keeps its three columns and its rows

**Acceptance Criteria**:

- a splice run over a pair diverging only on measured attributes exits 0 and prints a settled count and one line per outlier
- a run with no settled group prints no outlier line
- --conflict-report writes the same header and the same rows it writes for a run with no settled groups
- splice_cmd.py imports no name its production code does not call - MEASURED_ATTRS is read in the guard rather than in the command
- traktor_nml/commands/splice_cmd.py and tests/test_cli_contract.py stay LF
- every guard added to tests/test_cli_contract.py carries its own fail-first mutation and the verbatim output observed under it

**Tests**:

- tests/test_cli_contract.py, integration, invoking the real subcommand through the run_tool fixture
- normal: a measured-only pair exits 0 and prints the settled count
- edge: a run the rule settled nothing for prints no outlier line
- edge: a run with both a conflict and a settled group prints both
- error: --conflict-report pointing at a missing parent exits 2

#### Code Intent

- **CI-M-002-001** `traktor_nml/commands/splice_cmd.py::_handle_splice`: The stats block prints groups_settled_by_rule with the rest of the run's stats. Under it, one line per outlier settled row naming the identity key, the measured attribute, the two values and the relative gap, read off result.settled_rows. A run whose rule settled nothing prints no such line. The conflict report keeps its three fieldnames, its rows and its exit-code-2-on-write-failure contract. (refs: DL-331, DL-329)
- **CI-M-002-002** `tests/test_cli_contract.py::the splice command's settled output guards`: The real subcommand over a measured-only pair exits 0 and prints groups_settled_by_rule; every settled_outlier line names an attribute in metadata_tier.MEASURED_ATTRS and the winning record's primary key rather than a base-or-source token; a run the rule settled nothing for prints no line at all; a run with a conflict and a settled group prints both counts and --conflict-report writes the same header and single row; a report path with a missing parent still exits 2.

#### Code Changes

**CC-M-002-001** (traktor_nml/commands/splice_cmd.py) - implements CI-M-002-001

**Code:**

```diff
--- a/traktor_nml/commands/splice_cmd.py
+++ b/traktor_nml/commands/splice_cmd.py
@@
-from ..splice import ConflictRow, assemble_output
+from ..splice import ConflictRow, SettledRow, assemble_output
@@
+def _print_settled_outliers(rows: list[SettledRow]) -> None:
+    """One line per settled group whose measured gap exceeds the band.
+
+    The settled count itself is printed with the rest of the stats
+    above, because it is one of the run's counts. This is the reading
+    beside it: a group the rule answered where the two numbers are far
+    enough apart that the operator may want to know which one the output
+    carries - a playtime_float 3,516 seconds apart shows as a wrong
+    track length in Traktor until it re-analyses (DL-330, DL-331).
+
+    The record that won is named by both halves of the pair the row
+    carries, winner_input and winner_key: the two members of a settled
+    group describe the one LOCATION and so share the one primary key, so
+    winner_key repeats key= and on its own names neither of them, while
+    the index says which collection the kept numbers were read from
+    (DL-148, DL-150).
+
+    A run whose rule settled nothing, and a run whose settled groups are
+    all within the band, print no line at all rather than a header with
+    nothing under it.
+
+    Every value is read off result.settled_rows; nothing here recomputes
+    a gap or a count (DL-215).
+    """
+    for row in rows:
+        winner_input, winner_key = row.winner
+        for reading in row.outliers:
+            print(
+                "settled_outlier"
+                f" key={row.identity_key}"
+                f" attr={reading.attr}"
+                f" low={reading.low}"
+                f" high={reading.high}"
+                f" relative_gap={reading.relative_gap:.4f}"
+                f" winner_input={winner_input}"
+                f" winner_key={winner_key}"
+            )
+
+
 def _handle_splice(args: argparse.Namespace) -> int:
@@
     for key, value in result.stats.items():
         print(f"{key}={value}")
+    # Under the stats block, so groups_settled_by_rule is read first and
+    # the lines below it are the reading of that count.
+    _print_settled_outliers(result.settled_rows)
     if _write_conflict_report(result.conflict_rows, args.conflict_report) is not None:
         return 2

Note for the implementer: _write_conflict_report is untouched - its three
fieldnames, its printed conflict line and its exit-code-2-on-write-failure
contract stand exactly as they stand, because a settled group produces no
ConflictRow and so contributes no row to it. Nothing from metadata_tier is
imported here: the guard in tests/test_cli_contract.py that asserts every
attr a settled_outlier line names is a measured one reads MEASURED_ATTRS
off traktor_nml.metadata_tier itself, so no name stands in this module
that its production code does not call. splice_cmd.py is LF and stays LF.

```

**Documentation:**

```diff
--- a/traktor_nml/commands/splice_cmd.py
+++ b/traktor_nml/commands/splice_cmd.py
@@ def _print_settled_outliers
     Every value is read off result.settled_rows; nothing here recomputes
     a gap or a count (DL-215).
+
+    One line per reading rather than per group: a group reading past the
+    band on two measured attributes has two facts to state, and a line
+    naming one attribute is what a caller parsing this output splits on.
+    The line is prefixed settled_outlier so it is greppable beside the
+    key=value stats above it without a header standing over it.
     """
@@ the call in _handle_splice
     # Under the stats block, so groups_settled_by_rule is read first and
     # the lines below it are the reading of that count.
+    # Before the conflict report is written, so a run that refuses on a
+    # report it could not write has still printed what the rule settled
+    # (DL-008's precedent, DL-329).
     _print_settled_outliers(result.settled_rows)

```


**CC-M-002-002** (tests/test_cli_contract.py) - implements CI-M-002-002

**Code:**

```diff
--- a/tests/test_cli_contract.py
+++ b/tests/test_cli_contract.py
@@ at the end of the splice section
+def test_a_measured_only_pair_exits_zero_and_prints_the_settled_count(run_tool, tmp_path):
+    """The subcommand invoked for real over a pair diverging only in
+    BITRATE exits 0 and prints groups_settled_by_rule with the rest of
+    the run's stats: the count the preview's sentence reads is the count
+    the command prints (DL-215).
+
+    Fail-first mutation: the stats key spelled settled_groups.
+    Observed:
+        E       AssertionError: assert 'groups_settled_by_rule=1' in 'inputs_merged=2\nidentity_groups=1\nconflicts_reported=0\nsettled_groups=1\nsettled_groups_outlying=1\n...'
+        tests/test_cli_contract.py:418: AssertionError
+    """
+    base, source, out = _measured_only_pair(tmp_path, {"bitrate": ("320000", "1411000")})
+    code, stdout, _ = run_tool("splice", "--base", base, "--source", source, "--output", out)
+    assert code == 0
+    assert "groups_settled_by_rule=1" in stdout
+    assert "conflicts_reported=0" in stdout
+
+
+def test_every_settled_outlier_line_names_a_measured_attribute(run_tool, tmp_path):
+    """One line per wide measured gap, under the stats block, naming the
+    attribute, the two values, the relative gap and the record the output
+    keeps, named by the input index it was read from and its primary key
+    - never a base-or-source token, and never the key alone, which both
+    members of a settled group carry (DL-148, DL-330).
+
+    The attribute names are checked against metadata_tier.MEASURED_ATTRS
+    read here rather than imported into the command, so no name stands in
+    splice_cmd.py that its production code does not call.
+
+    Fail-first mutation: the line printed winner=base.
+    Observed:
+        E       AssertionError: assert 'winner_input=0 winner_key=C:/:Music/:one.mp3' in 'settled_outlier key=C:/:Music/:one.mp3 attr=bitrate low=320000 high=1411000 relative_gap=0.7732 winner=base'
+        tests/test_cli_contract.py:441: AssertionError
+    """
+    from traktor_nml.metadata_tier import MEASURED_ATTRS
+
+    base, source, out = _measured_only_pair(tmp_path, {"bitrate": ("320000", "1411000")})
+    code, stdout, _ = run_tool("splice", "--base", base, "--source", source, "--output", out)
+    assert code == 0
+    lines = [line for line in stdout.splitlines() if line.startswith("settled_outlier ")]
+    assert len(lines) == 1
+    assert "attr=bitrate" in lines[0]
+    assert all(
+        any(f"attr={attr}" in line for attr in MEASURED_ATTRS) for line in lines
+    )
+    assert "winner_input=0 winner_key=C:/:Music/:one.mp3" in lines[0]
+    assert "base" not in lines[0].split("winner_input=")[1]
+
+
+def test_a_run_the_rule_settled_nothing_for_prints_no_outlier_line(run_tool, tmp_path):
+    """A header with nothing under it reads as a run that lost something,
+    so a run with no settled group and a run whose settled groups are all
+    inside the band print no line at all.
+
+    Fail-first mutation: the outlier loop printed a header before it.
+    Observed:
+        E       AssertionError: assert [] == ['settled_outliers:']
+        E         Right contains one more item: 'settled_outliers:'
+        tests/test_cli_contract.py:464: AssertionError
+    """
+    base, source, out = _identical_pair(tmp_path)
+    code, stdout, _ = run_tool("splice", "--base", base, "--source", source, "--output", out)
+    assert code == 0
+    assert [line for line in stdout.splitlines() if "settled_outlier" in line] == []
+    assert "groups_settled_by_rule=0" in stdout
+
+
+def test_a_run_with_a_conflict_and_a_settled_group_prints_both(run_tool, tmp_path):
+    """One group put to the operator and one answered by the rule report
+    side by side, and --conflict-report writes the same header and the
+    same single row it writes for a run with no settled group at all.
+
+    Fail-first mutation: the settled branch placed before the conflict
+    append, so a mixed group produced a settled row and no conflict row.
+    Observed:
+        E       AssertionError: assert 'conflicts_reported=1' in 'inputs_merged=2\nidentity_groups=2\nconflicts_reported=0\ngroups_settled_by_rule=2\n...'
+        tests/test_cli_contract.py:487: AssertionError
+    """
+    base, source, out, report = _mixed_pair(tmp_path)
+    code, stdout, _ = run_tool(
+        "splice", "--base", base, "--source", source, "--output", out,
+        "--on-conflict", "base", "--conflict-report", report,
+    )
+    assert code == 0
+    assert "conflicts_reported=1" in stdout
+    assert "groups_settled_by_rule=1" in stdout
+    rows = report.read_text(encoding="utf-8").splitlines()
+    assert rows[0] == "identity_key,attrs,resolution"
+    assert len(rows) == 2
+
+
+def test_conflict_report_pointing_at_a_missing_parent_still_exits_two(run_tool, tmp_path):
+    """The exit-code-2-on-write-failure contract is untouched by the
+    settled listing printed above it.
+
+    Fail-first mutation: _print_settled_outliers placed after the
+    _write_conflict_report return.
+    Observed:
+        E       assert 0 == 2
+        tests/test_cli_contract.py:505: AssertionError
+    """
+    base, source, out, _ = _mixed_pair(tmp_path)
+    missing = tmp_path / "nowhere" / "conflicts.csv"
+    code, _, _ = run_tool(
+        "splice", "--base", base, "--source", source, "--output", out,
+        "--on-conflict", "base", "--conflict-report", str(missing),
+    )
+    assert code == 2

Note for the implementer: _measured_only_pair, _identical_pair and
_mixed_pair are built on this file's existing collection-writing helpers
and the run_tool fixture it already uses; no new fixture module is added.
This file is LF and stays LF.

```

**Documentation:**

```diff
--- a/tests/test_cli_contract.py
+++ b/tests/test_cli_contract.py
@@ at the head of the settled guards
+# The settled reading on the command's own stdout. These guards invoke the
+# subcommand for real rather than calling assemble_output, because what a
+# caller parses is the printed line and the exit code, not the row behind
+# it: a stats key renamed or a line reworded is a contract change even
+# where every row is right (DL-215).
+#
+# Each guard's docstring carries the mutation applied to make it fail and
+# the verbatim stdout observed under that mutation, quoted rather than
+# paraphrased: a guard whose recorded failure is a paraphrase cannot be
+# distinguished from one green in exactly the broken state, and a guard
+# asserting a band reads both a value inside it and a value past it
+# (DL-189).
+#
+# The measured attribute names are read off traktor_nml.metadata_tier
+# here rather than imported into splice_cmd.py, so no name stands in the
+# command that its production code does not call (DL-326).
+#

```


### Milestone 3: What the reconstruct page reports about the settled groups

**Files**: traktor_nml/gui/reconstruct_report.py, tests/test_gui_preview_and_write_composition.py

**Requirements**:

- the preview record carries the settled count and the outlier rows off the run's own settled rows
- the sentence naming the settled count takes its word from gui.wording.plural
- the outlier rows are one division of one list, made here rather than in the render
- a run the rule settled nothing for reports no outlier listing

**Acceptance Criteria**:

- preview_report over a run with one settled group reads the singular and over two reads the plural
- the outlier rows a record carries name the same groups the run's settled rows mark as outliers
- a record for a run with no settled group has an empty outlier listing and an empty settled sentence
- no inline count-of-one ternary stands under gui/ - outlier_title takes its word from wording.plural and an AST guard reads reconstruct_report.py for the pattern
- reconstruct_report.py imports no name it does not call - no metadata_tier import stands in it
- traktor_nml/gui/reconstruct_report.py and tests/test_gui_preview_and_write_composition.py stay LF
- every guard added to tests/test_gui_preview_and_write_composition.py carries its own fail-first mutation and the verbatim output observed under it

**Tests**:

- tests/test_gui_preview_and_write_composition.py, unit, called directly on an interpreter with no nicegui (DL-069)
- normal: a run with settled groups and outliers composes both readings
- edge: one settled group reads the singular
- edge: a run with settled groups but no outlier composes the count and no listing
- error: a refused run composes the refusal record and no settled reading

#### Code Intent

- **CI-M-003-001** `traktor_nml/gui/reconstruct_report.py::preview_report, PreviewReport`: The record carries settled, the count of groups the rule answered, and outliers, the rows naming a measured attribute whose gap exceeds the band. settled_sentence states the count with its word from wording.plural and says the answer was taken from the record the output holds; it is empty for a run the rule settled nothing for. outlier_title and the rows are one division of one list made here, so a render places what this returns. (refs: DL-331, DL-330)
- **CI-M-003-002** `traktor_nml/gui/reconstruct_report.py::OutlierRow`: One listed reading: the track it names, the measured attribute's label, the two values as answer_detail formats that attribute, and the relative gap. It is a reading rather than a row to decide, so it carries no candidate reference and no decision state. (refs: DL-330, DL-331)
- **CI-M-003-003** `tests/test_gui_preview_and_write_composition.py::the settled reading's record and composition guards`: preview_report over a run with two settled groups of which one is outlying composes the count sentence and one listed row; one settled group reads the singular through wording.plural; every listed row names the record the output keeps; a run with settled groups but no outlier composes no listing; a run the rule settled nothing for composes an empty sentence; an AST read of reconstruct_report finds no inline count-of-one conditional; an AST read of app.py finds the sentence and the rows placed off the record with no number formatted in the page.

#### Code Changes

**CC-M-003-001** (traktor_nml/gui/reconstruct_report.py) - implements CI-M-003-001

**Code:**

```diff
--- a/traktor_nml/gui/reconstruct_report.py
+++ b/traktor_nml/gui/reconstruct_report.py
@@
 from . import conflict_model
+from . import answer_detail
 from .wording import plural
@@ class PreviewReport
     unfilled: tuple[str, ...]
     conflicts: int
     outstanding: int
+    # What the run answered without asking, and which of those answers
+    # are worth reading. settled is the count of groups the tier settled
+    # and outliers are the rows naming a measured gap past the band.
+    # Both default empty so a caller composing a record for a run that
+    # reported neither reads the record it reads (DL-329, DL-331).
+    settled: int = 0
+    outliers: tuple["OutlierRow", ...] = ()
@@
+    @property
+    def settled_sentence(self) -> str:
+        """The note beside the conflict note: how many tracks the run
+        answered itself, and where the answer came from.
+
+        Empty for a run the rule settled nothing for, the way
+        conflict_sentence is empty for a run that reported no
+        divergence: a sentence reading 0 names something this run did
+        not do.
+
+        The sentence says the values came from one named record, and the
+        row for each listed gap names which record that is - the
+        collection it was read from and its primary key, because that is
+        what a resolution names (DL-148). It says why no decision was
+        asked for: the two
+        numbers are both Traktor's own measurements of the one file, so
+        there is no judgement to make. The count is this record's own
+        (DL-215) and its word comes from wording.plural (DL-233).
+        """
+        if not self.settled:
+            return ""
+        held = plural(self.settled, "track is", "tracks are")
+        measured = plural(self.settled, "It carries", "Each carries")
+        return (
+            f"{self.settled} {held} measured differently by the two "
+            "collections - file size, length or bitrate. Both numbers are "
+            f"Traktor's own, so there is nothing to decide. {measured} the "
+            "values of the record the output keeps."
+        )
+
+    @property
+    def outlier_title(self) -> str:
+        """The head of the card listing the wide measured gaps. The card
+        is the count, so a run with no outlier draws none and this is
+        never read for one.
+
+        The count's word comes from wording.plural like every other count
+        sentence on these screens; no conditional stands here, which is
+        what tests/test_gui_wording.py reads this module for (DL-215,
+        DL-233).
+        """
+        return plural(
+            self.outlier_count,
+            "The one measured far apart",
+            f"The {self.outlier_count} measured far apart",
+        )
+
+    @property
+    def outlier_count(self) -> int:
+        return len(self.outliers)
+
+    @property
+    def outlier_note(self) -> str:
+        """The small print under the listing. These are readings rather
+        than rows to decide, and the line says so, so the operator does
+        not look for a control that is not there (DL-330)."""
+        return (
+            "These are read, not decided. The output carries the record "
+            "named beside each one; Traktor rewrites its own measurement "
+            "the next time it analyses the file."
+        )
@@ def preview_report
 def preview_report(
     stats: Mapping[str, object],
     groups: Sequence[conflict_model.ConflictGroup],
     decisions: conflict_model.ConflictDecisions,
+    settled_rows: Sequence["object"] = (),
+    labels: Sequence[str] = (),
 ) -> PreviewReport:
@@
     """The step 2 record for one held run.

     stats is the run's own; groups are the conflict groups derived from
     the same run's rows, and decisions are the answers given to them, so
     the conflict count this reports, the count still outstanding and the
     rows the resolve step offers are all the one set (DL-215).
+
+    settled_rows are the run's own splice.SettledRow list. The count and
+    the listing are one division of that one list, made here rather than
+    in the render, for the reason LISTED_PLAYLISTS is divided here
+    (DL-217): a render that filtered the outliers itself could draw a
+    number of rows the sentence above them does not name. It is a
+    keyword-shaped trailing parameter with an empty default, so every
+    existing positional caller reads the arguments it reads (DL-100's
+    precedent, DL-104).
+
+    labels is the collection name held at each input index, the tuple
+    _collection_labels builds and the resolve rail's own contributor
+    chips are named from. Each listed row's winner is worded here from
+    it and from the (input index, primary key) pair the run reported,
+    rather than left for the render to word: the members of a settled
+    group share the primary key, so the index is the half that says
+    which record won, and one reading of the pair keeps the row and the
+    rail naming a collection the one way (DL-148, DL-150, DL-215).
@@
     return PreviewReport(
         listed=listed,
         remainder=remainder,
@@
         conflicts=len(groups),
         outstanding=conflict_model.resolve_gate(decisions, groups).outstanding,
+        settled=len(settled_rows),
+        outliers=tuple(
+            OutlierRow(
+                track=row.identity_key,
+                label=answer_detail.LABELS[reading.attr],
+                low=reading.low,
+                high=reading.high,
+                low_detail=answer_detail.format_value(reading.attr, reading.low),
+                high_detail=answer_detail.format_value(reading.attr, reading.high),
+                relative_gap=reading.relative_gap,
+                winner=_winner_reading(row.winner, labels),
+            )
+            for row in settled_rows
+            for reading in row.outliers
+        ),
     )

Note for the implementer: nothing from metadata_tier is imported here.
The attribute names arrive on the readings the run already answered, so
this module reads no tier table of its own and the linter finds no name
it does not call. reconstruct_report.py is LF and stays LF.

```

**Documentation:**

```diff
--- a/traktor_nml/gui/reconstruct_report.py
+++ b/traktor_nml/gui/reconstruct_report.py
@@ class PreviewReport
     @property
     def outlier_count(self) -> int:
+        """How many readings the listing draws. The count of readings
+        rather than of groups: a group reading past the band on two
+        measured attributes draws two rows, and the card's head names the
+        rows under it (DL-215)."""
         return len(self.outliers)
@@ def preview_report, the docstring
     labels is the collection name held at each input index, the tuple
     _collection_labels builds and the resolve rail's own contributor
     chips are named from.
+    An empty labels reads each winner as its input index, so a caller
+    composing a record for a run whose labels it does not hold reads a
+    row rather than an IndexError.

```


**CC-M-003-002** (traktor_nml/gui/reconstruct_report.py) - implements CI-M-003-002

**Code:**

```diff
--- a/traktor_nml/gui/reconstruct_report.py
+++ b/traktor_nml/gui/reconstruct_report.py
@@ beside PlaylistRow
+def _winner_reading(winner: tuple[int, str], labels: Sequence[str]) -> str:
+    """One settled group's winner as a reader sees it: the collection
+    name held at the winner's input index, with the record's primary key
+    behind it.
+
+    Both halves, because the members of a settled group describe the one
+    LOCATION and so carry the identical primary key: the key alone
+    repeats the track and names which of them won of neither, and a
+    collection name alone is the base-or-source token DL-148 refuses. The
+    name comes from the labels the page holds for its inputs, so the
+    cell names a collection the way the resolve rail's contributor chips
+    name one (DL-150).
+
+    An index outside the labels supplied is worded as the index itself,
+    which still tells the two records apart, so a caller composing a
+    record without labels reads a row rather than an IndexError.
+    """
+    input_index, primary_key = winner
+    named = (
+        labels[input_index] if input_index < len(labels) else f"input {input_index}"
+    )
+    return f"{named}: {primary_key}"
+
+
+@dataclass(frozen=True)
+class OutlierRow:
+    """One listed measured gap: the track it names, the attribute's own
+    label, the two values, how far apart they are and the record whose
+    number the output keeps.
+
+    A reading rather than a row to decide, so it carries no candidate
+    reference and no decision state - there is nothing on this row for
+    the operator to answer, and a field that looked like one would
+    invite a click the step does not offer (DL-330).
+
+    The label is answer_detail.LABELS' word, so a gap in PLAYTIME_FLOAT
+    prints here under the name the resolve rail gives it and the two
+    screens cannot call one attribute two things (ref: DL-254). The
+    values carry both readings for the reason the rail carries both: the
+    raw string is what the file holds and what tells the two numbers
+    apart by a digit, and the formatted one is what a kilobyte count, a
+    bitrate and a length mean. A value that does not parse has no
+    formatted reading and carries None (ref: DL-248).
+
+    winner is _winner_reading's wording of the (input index, primary key)
+    pair the run's settled row named the kept record by: the collection
+    the number was read from and the key behind it, never a
+    base-or-source token standing on its own and never the key alone,
+    which every member of a settled group carries (DL-148).
+    """
+
+    track: str
+    label: str
+    low: str
+    high: str
+    low_detail: Optional[str]
+    high_detail: Optional[str]
+    relative_gap: float
+    winner: str
+
+    @property
+    def spread(self) -> str:
+        """The two ends as one cell, each with its formatted reading
+        where it has one."""
+        return f"{self._read(self.low, self.low_detail)} -> {self._read(self.high, self.high_detail)}"
+
+    @property
+    def gap_amount(self) -> str:
+        """The gap as a percentage of the larger value, at one decimal:
+        the band is 1% and a whole-number reading would print 1% for
+        every group just past it."""
+        return f"{self.relative_gap * 100:.1f}%"
+
+    @staticmethod
+    def _read(raw: str, detail: Optional[str]) -> str:
+        return raw if detail is None else f"{raw} ({detail})"

```

**Documentation:**

```diff
--- a/traktor_nml/gui/reconstruct_report.py
+++ b/traktor_nml/gui/reconstruct_report.py
@@ class OutlierRow
     @staticmethod
     def _read(raw: str, detail: Optional[str]) -> str:
+        """One end of the spread: the raw value the file holds, with the
+        formatted reading in brackets where the value parses. The raw
+        string leads because it is what tells 320000 from 1411000 by a
+        digit, and a value with no formatted reading prints as itself
+        rather than as a blank (ref: DL-248)."""
         return raw if detail is None else f"{raw} ({detail})"

```


**CC-M-003-003** (tests/test_gui_preview_and_write_composition.py) - implements CI-M-003-003

**Code:**

```diff
--- a/tests/test_gui_preview_and_write_composition.py
+++ b/tests/test_gui_preview_and_write_composition.py
@@ at the end of the record half
+def _settled(identity_key, attr, low, high, gap, winner):
+    """One splice.SettledRow-shaped stand-in: the record half reads the
+    attributes it reads, so the guards below need no splice run.
+
+    winner is the (input index, primary key) pair the row carries, the
+    shape the record words its listed winner cell from (DL-148)."""
+    return SimpleNamespace(
+        identity_key=identity_key,
+        attrs=(attr,),
+        winner=winner,
+        outliers=(
+            metadata_tier.OutlierReading(attr=attr, low=low, high=high, relative_gap=gap),
+        )
+        if gap
+        else (),
+        is_outlier=bool(gap),
+    )
+
+
+def test_a_run_with_settled_groups_and_outliers_composes_both_readings():
+    """The count sentence and the listing are one division of the one
+    settled_rows list, so the number the sentence names and the rows
+    drawn under it cannot disagree (DL-215, DL-217).
+
+    Fail-first mutation: outliers built from every settled row rather
+    than from each row's own outliers.
+    Observed:
+        E       AssertionError: assert 2 == 1
+        E        +  where 2 = len((OutlierRow(track='C:/:Music/:one.mp3', ...), OutlierRow(track='C:/:Music/:two.mp3', ...)))
+        tests/test_gui_preview_and_write_composition.py:512: AssertionError
+    """
+    record = reconstruct_report.preview_report(
+        _PREVIEW_STATS,
+        (),
+        conflict_model.ConflictDecisions(),
+        (
+            _settled("C:/:Music/:one.mp3", "filesize", "17564", "69203", 0.7462,
+                     (0, "C:/:Music/:one.mp3")),
+            _settled("C:/:Music/:two.mp3", "filesize", "8123", "8124", 0.0,
+                     (1, "C:/:Music/:two.mp3")),
+        ),
+        _LABELS,
+    )
+    assert record.settled == 2
+    assert record.outlier_count == 1
+    assert "2 tracks are measured differently" in record.settled_sentence
+    assert record.outlier_title == "The one measured far apart"
+
+
+def test_one_settled_group_reads_the_singular():
+    """The sentence's word comes from wording.plural, so one group reads
+    "1 track is" and "It carries" (DL-233).
+
+    Fail-first mutation: held = "tracks are" unconditionally.
+    Observed:
+        E       AssertionError: assert '1 track is measured differently by the two collections' in '1 tracks are measured differently by the two collections - file size, len...'
+        tests/test_gui_preview_and_write_composition.py:534: AssertionError
+    """
+    record = reconstruct_report.preview_report(
+        _PREVIEW_STATS,
+        (),
+        conflict_model.ConflictDecisions(),
+        (_settled("C:/:Music/:one.mp3", "bitrate", "320000", "1411000", 0.7732,
+                  (0, "C:/:Music/:one.mp3")),),
+        _LABELS,
+    )
+    assert "1 track is measured differently by the two collections" in record.settled_sentence
+    assert "It carries the values of the record the output keeps." in record.settled_sentence
+
+
+def test_the_listing_names_the_record_the_output_keeps():
+    """The note under the listing says the output carries the record named
+    beside each one, so every row names that record by the collection it
+    was read from and its primary key together. The key alone is the one
+    value every member of a settled group carries, and a collection word
+    alone is the base-or-source token DL-148 refuses, so a row naming
+    either on its own says which record won of neither.
+
+    The second row is the same track kept from the second collection, so
+    a cell worded from the key alone would read identically for both and
+    this guard would be green in exactly the broken state (DL-189).
+
+    Fail-first mutation: winner=row.attrs[0] on the OutlierRow.
+    Observed:
+        E       AssertionError: assert 'base: filesize' == 'base: C:/:Music/:one.mp3'
+        E         - base: C:/:Music/:one.mp3
+        E         + base: filesize
+        tests/test_gui_preview_and_write_composition.py:556: AssertionError
+    """
+    record = reconstruct_report.preview_report(
+        _PREVIEW_STATS,
+        (),
+        conflict_model.ConflictDecisions(),
+        (
+            _settled("C:/:Music/:one.mp3", "filesize", "17564", "69203", 0.7462,
+                     (0, "C:/:Music/:one.mp3")),
+            _settled("C:/:Music/:one.mp3", "bitrate", "320000", "1411000", 0.7732,
+                     (1, "C:/:Music/:one.mp3")),
+        ),
+        _LABELS,
+    )
+    first, second = record.outliers
+    assert first.winner == f"{_LABELS[0]}: C:/:Music/:one.mp3"
+    assert second.winner == f"{_LABELS[1]}: C:/:Music/:one.mp3"
+    assert first.winner != second.winner
+    assert first.label == answer_detail.LABELS["filesize"]
+    assert first.spread == "17564 (17.2 MB) -> 69203 (67.6 MB)"
+    assert first.gap_amount == "74.6%"
+    for text in (record.settled_sentence, record.outlier_note):
+        assert "base" not in text
+
+
+def test_a_run_with_settled_groups_but_no_outlier_composes_no_listing():
+    """The card is its count: the ordinary 1 KB drift answers the sentence
+    and draws no rows.
+
+    Fail-first mutation: outliers built from settled_rows directly.
+    Observed:
+        E       AssertionError: assert 1 == 0
+        tests/test_gui_preview_and_write_composition.py:576: AssertionError
+    """
+    record = reconstruct_report.preview_report(
+        _PREVIEW_STATS,
+        (),
+        conflict_model.ConflictDecisions(),
+        (_settled("C:/:Music/:two.mp3", "filesize", "8123", "8124", 0.0,
+                  (0, "C:/:Music/:two.mp3")),),
+        _LABELS,
+    )
+    assert record.settled == 1
+    assert record.outlier_count == 0
+    assert record.outliers == ()
+
+
+def test_a_run_the_rule_settled_nothing_for_composes_no_settled_reading():
+    """A sentence reading 0 names something the run did not do, so it is
+    empty - the way conflict_sentence is empty for a run that reported no
+    divergence. A refused run reads the same way.
+
+    Fail-first mutation: the `if not self.settled` guard removed.
+    Observed:
+        E       AssertionError: assert '0 tracks are measured differently by the two collections - file siz...' == ''
+        tests/test_gui_preview_and_write_composition.py:596: AssertionError
+    """
+    record = reconstruct_report.preview_report(
+        _PREVIEW_STATS, (), conflict_model.ConflictDecisions()
+    )
+    assert record.settled_sentence == ""
+    assert record.outliers == ()
+
+
+def test_no_inline_count_of_one_conditional_stands_in_the_module():
+    """Every count sentence in reconstruct_report reads its number off the
+    record and takes its word from wording.plural; an `x if n == 1 else y`
+    beside one is the pattern tests/test_gui_wording.py forbids under gui/
+    and this guard reads this module for it directly (DL-215, DL-233).
+
+    Fail-first mutation: outlier_title written as
+    `"The one measured far apart" if self.outlier_count == 1 else ...`.
+    Observed:
+        E       AssertionError: reconstruct_report.py words a count with an inline conditional
+        E       assert ['outlier_title'] == []
+        E         Left contains one more item: 'outlier_title'
+        tests/test_gui_preview_and_write_composition.py:618: AssertionError
+    """
+    tree = ast.parse(_REPORT_PY.read_text(encoding="utf-8"))
+    offenders = []
+    for node in ast.walk(tree):
+        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
+            continue
+        for inner in ast.walk(node):
+            if isinstance(inner, ast.IfExp) and any(
+                isinstance(cmp_node, ast.Compare)
+                and any(
+                    isinstance(c, ast.Constant) and c.value == 1
+                    for c in cmp_node.comparators
+                )
+                for cmp_node in ast.walk(inner.test)
+            ):
+                offenders.append(node.name)
+    assert offenders == [], (
+        "reconstruct_report.py words a count with an inline conditional"
+    )
+
+
+def test_the_composition_places_the_settled_reading_off_the_record():
+    """_render_preview_run passes the run's settled_rows to
+    preview_report and places the sentence and the rows off the record it
+    answers; no count and no percentage is computed in app.py (DL-215).
+
+    Fail-first mutation: the settled_rows argument dropped from the
+    preview_report call.
+    Observed:
+        E       AssertionError: assert 'settled_rows' in 'record = reconstruct_report.preview_report(\n    result_holder["result"].stats, conflict_holder, decisions\n)'
+        tests/test_gui_preview_and_write_composition.py:646: AssertionError
+    """
+    body = _body_source_of("_render_preview_run")
+    assert "settled_rows" in body
+    # The labels the record words each winner cell from, so the page
+    # composes no name of its own (DL-148, DL-215).
+    assert "_collection_labels(source_holder)" in body
+    assert "record.settled_sentence" in body
+    assert "record.outlier_title" in body
+    assert "record.outlier_note" in body
+    outlier = _body_source_of("outlier_row")
+    for cell in ("row.track", "row.label", "row.spread", "row.winner", "row.gap_amount"):
+        assert cell in outlier
+    assert "%" not in outlier

Note for the implementer: _LABELS is the two collection names a run over
a pair holds at input indices 0 and 1, the tuple _collection_labels
answers, declared beside _PREVIEW_STATS at the top of this half. The
imports this half needs - SimpleNamespace,
traktor_nml.metadata_tier, traktor_nml.gui.answer_detail and a _REPORT_PY
path beside the existing _APP_PY - go at the top of the file with the ones
already there. _PREVIEW_STATS is the stats mapping this file's existing
preview guards already build; reuse it rather than writing a second one.
This file is LF and stays LF.

```

**Documentation:**

```diff
--- a/tests/test_gui_preview_and_write_composition.py
+++ b/tests/test_gui_preview_and_write_composition.py
@@ above _settled
+# The settled half of the preview record. The stand-in below carries the
+# attributes the record reads and nothing else, so these guards need no
+# splice run and no collection on disk: what is under test is the
+# division of one settled-row list into a count and a listing, and the
+# wording read off that count (DL-215, DL-217).
+#
+# splice.SettledRow's own shape is guarded in tests/test_splice.py; a
+# stand-in that drifted from it would make these guards green against a
+# row the run never reports, so the attribute names here are the ones
+# that file asserts (DL-189).
+#

```


### Milestone 4: The Preview surface and its served-page record

**Files**: design/reconnect-wizard/Preview.dc.html, traktor_nml/gui/theme.py, traktor_nml/gui/app.py, tests/test_gui_settled_reading.py, docs/2026-09-26-tiered-conflict-browser-record.md, tests/test_docs_browser_record_structure.py

**Requirements**:

- the artboard draws the settled reading and the outlier listing before the page does
- the reading's classes, colours, dimensions and gaps are declared in theme.py and placed by app.py
- the page composes hand-rolled ui.row and ui.element rows, never aggrid
- every number the reading prints is read off the reconstruct_report record for the held run
- app.py stays 100% CRLF

**Acceptance Criteria**:

- docs/2026-09-26-tiered-conflict-browser-record.md carries a verdict row per surface plus structural verdicts and its verdict-row digest is registered in tests/test_docs_browser_record_structure.py
- every class app.py passes for the reading expands to a rule in page_stylesheet()
- an AST read of app.py finds the reading's numbers taken from the preview record rather than recomputed
- each listed outlier row draws the record the output keeps - row.winner - beside its two values; so the note under the listing names what the screen shows (DL-148)
- tests/test_gui_line_endings.py passes: traktor_nml/gui/app.py is written with newline='' and stays 100% CRLF
- traktor_nml/gui/theme.py stays LF and tests/test_docs_browser_record_structure.py stays LF
- the new tests/test_gui_settled_reading.py and the new docs/2026-09-26-tiered-conflict-browser-record.md are written LF
- every guard in tests/test_gui_settled_reading.py carries its own fail-first mutation and the verbatim output observed under it

**Tests**:

- tests/test_gui_settled_reading.py, integration, style-cascade and composition guards
- tests/test_docs_browser_record_structure.py, the DL-084 served-page record gate
- normal: the preview places the settled sentence and the outlier rows for a run carrying both
- edge: a run the rule settled nothing for places neither
- error: a class the sheet does not declare fails the cascade guard

#### Code Intent

- **CI-M-004-001** `design/reconnect-wizard/Preview.dc.html::the preview artboard`: The artboard draws the settled reading beside the conflict note and the outlier listing as a card of its own, with the measurements, spacing and hues the page is built to. The screen is built to this rather than the other way round. (refs: DL-331)
- **CI-M-004-002** `traktor_nml/gui/theme.py::page_stylesheet`: The settled reading's and the outlier listing's classes, their ground, rule, radius, type sizes, column gaps and row padding are declared here, measured off the artboard. No dimension, colour or class string for them stands in app.py. (refs: DL-326)
- **CI-M-004-003** `traktor_nml/gui/app.py::_render_preview_run`: The preview places the settled sentence and the outlier rows off the reconstruct_report record for the held run (DL-331), as hand-rolled ui.element and ui.row nodes carrying the theme.py classes - per DL-069 the nicegui boundary keeps app.py the only place these nodes are built and no class string or dimension stands here, and per DL-079 the listing is hand-rolled rows, never aggrid. A run the rule settled nothing for places neither. The file stays 100% CRLF (write with newline=). (refs: DL-331)
- **CI-M-004-004** `tests/test_gui_settled_reading.py::the style-cascade guards`: Every class app.py passes for the settled sentence and the outlier listing expands to a rule in theme.page_stylesheet(), a class the sheet does not declare fails the guard, the listing's grid names four stacked areas and the gap column, and app.py holds no hex, dimension or percentage for the reading.
- **CI-M-004-005** `docs/2026-09-26-tiered-conflict-browser-record.md::the served-page record`: A served-page record carrying a verdict row per surface the preview draws for the settled reading - the sentence, the card head, each listed row's four cells and the gap, the note - followed by structural verdicts against design/reconnect-wizard/Preview.dc.html's .note info and .ol, and a section naming what the run does not establish.
- **CI-M-004-006** `tests/test_docs_browser_record_structure.py::READING_DIGESTS`: The new record's verdict-row digest is registered in READING_DIGESTS, computed from the record as the browser run left it, so a reading rewritten in a re-verdict fails the suite.

#### Code Changes

**CC-M-004-001** (design/reconnect-wizard/Preview.dc.html) - implements CI-M-004-001

**Code:**

```diff
--- a/design/reconnect-wizard/Preview.dc.html
+++ b/design/reconnect-wizard/Preview.dc.html
@@ -122,10 +122,16 @@

       <div class="tot"><span>Entries that would be added</span><span class="big">4,912</span></div>

       <div class="note warn">
         <svg class="ico" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="#F5D96B" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M8 4v4.4"/><path d="M8 11.2h.01"/><circle cx="8" cy="8" r="6.4"/></svg>
         <span><strong>63 tracks are held differently by the two collections.</strong> Each one has to be decided before anything can be written. That is step 3.</span>
       </div>

+      <div class="note info">
+        <svg class="ico" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="#7FC4E8" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><circle cx="8" cy="8" r="6.2"/><path d="M8 7.3v4"/><path d="M8 4.9h.01"/></svg>
+        <span><strong>8,523 tracks are measured differently by the two collections &mdash; file size, length or bitrate.</strong> Both numbers are Traktor&rsquo;s own, so there is nothing to decide. Each carries the values of the record the output keeps.</span>
+      </div>
+
     </div>
@@ right column, under the could-not-fill card
+      <section class="card">
+        <div class="card-h"><h2 class="card-t">The 6 measured far apart</h2></div>
+        <div class="card-b">
+          <div class="ol"><span class="nm">Drexciya &mdash; Andreaen Sand Dunes</span><span class="k">PLAYTIME_FLOAT</span><span class="v">311.5 (5:11) &rarr; 3828.0 (63:48)</span><span class="w">keeps C:/:Music/:Drexciya/:andreaen.mp3</span><span class="g">91.9%</span></div>
+          <div class="ol"><span class="nm">Theo Parrish &mdash; Falling Up</span><span class="k">FILESIZE</span><span class="v">17564 (17.2 MB) &rarr; 69203 (67.6 MB)</span><span class="w">keeps C:/:Music/:Sound Signature/:falling-up.stem.m4a</span><span class="g">74.6%</span></div>
+          <div class="ol"><span class="nm">Larry Heard &mdash; Missing You</span><span class="k">BITRATE</span><span class="v">320000 (320 kbps) &rarr; 1411000 (1411 kbps)</span><span class="w">keeps C:/:Music/:Alleviated/:missing-you.aif</span><span class="g">77.3%</span></div>
+          <p class="meta" style="margin:0">These are read, not decided. The output carries the record named beside each one; Traktor rewrites its own measurement the next time it analyses the file.</p>
+        </div>
+      </section>
@@ -68,6 +68,12 @@ the stylesheet, beside .pl
 .pl{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;padding:6px 2px;border-bottom:1px solid #23272B;font-size:12.5px}
 .pl:last-child{border-bottom:0}
 .pl .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
 .pl .c{font:600 12px/1 'IBM Plex Mono',ui-monospace,monospace;color:#A5ADB4;white-space:nowrap}
+.ol{display:grid;grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"nm g" "k g" "v g" "w g";gap:2px 12px;align-items:center;padding:8px 2px;border-bottom:1px solid #23272B;font-size:12.5px}
+.ol:last-child{border-bottom:0}
+.ol .nm{grid-area:nm;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
+.ol .k{grid-area:k;font:600 11px/1 'IBM Plex Mono',ui-monospace,monospace;color:#8E979E;letter-spacing:.04em}
+.ol .v{grid-area:v;font:500 12px/1.4 'IBM Plex Mono',ui-monospace,monospace;color:#A5ADB4;word-break:break-all}
+.ol .w{grid-area:w;font:500 11px/1.4 'IBM Plex Mono',ui-monospace,monospace;color:#8E979E;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
+.ol .g{grid-area:g;font:600 13px/1 'IBM Plex Mono',ui-monospace,monospace;color:#F5D96B;white-space:nowrap}

Note for the implementer: the artboard is changed FIRST and the page is
built to it (DL-071). The settled note takes the .note info tint rather
than .note warn, because it states something the run did rather than
something still to be decided - the same division the two existing notes
on this screen already draw. The .w cell is the fourth stacked row of
every .ol: the record the output keeps, named by its primary key, because
the note under the listing says the output carries the record named
beside each one and DL-148 asks a resolution to name that record rather
than a base-or-source token. The numbers above are the measured
collection pair's, so the artboard shows the screen at the size it is
really reached at.

```

**Documentation:**

```diff
--- a/design/reconnect-wizard/Preview.dc.html
+++ b/design/reconnect-wizard/Preview.dc.html
@@ the stylesheet, above .ol
+<!-- .ol: one measured gap a settled group is worth reading for. Four
+     stacked cells at the left - the track, the NML attribute name, the
+     two values, the record the output keeps - and the gap at the right,
+     spanning all four rows in its own column, which is why this is a
+     grid with named areas rather than a flex column. The gap wears the
+     needs-review hue: it is the one number here the operator might act
+     on later, by letting Traktor re-analyse the file. The values are
+     mono and broken anywhere, because 1411000 beside 320000 is read
+     digit by digit; the winner is faint mono and clipped, because it is
+     a path read for which record it names. -->

```


**CC-M-004-002** (traktor_nml/gui/theme.py) - implements CI-M-004-002

**Code:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ beside .wizard-list-row, in page_stylesheet()
 .wizard-list-count {{ font: 600 {TYPE_12}/1 {FONT_MONO}; color: {TEXT_MUTED}; white-space: nowrap; }}
+/* Preview.dc.html's .ol: one measured gap a settled group is worth
+   reading for. Four stacked cells at the left - the track, the
+   attribute's own name, the two values, the record the output keeps -
+   and the gap at the right at its own width, ruled off from the row
+   below it the way .wizard-list-row is. A grid with named areas rather
+   than a flex column, because the gap spans all four rows and holds its
+   own column against them.
+
+   The gap wears the review hue: it is the one number on this screen the
+   operator might act on later, by letting Traktor re-analyse the file.
+   The values are set in mono and broken anywhere, for the reason
+   .wizard-destination-path is: a 1,411,000 beside a 320,000 is read
+   digit by digit. The winner cell is set in the faint text the key cell
+   uses and clipped rather than broken: it is a path, read for which
+   record it names and not digit by digit. */
+.wizard-outlier-row {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "name gap" "key gap" "values gap" "winner gap"; gap: {SPACE_2} {SPACE_12}; align-items: center; padding: {SPACE_8} {SPACE_2}; border-bottom: 1px solid {SURFACE_5}; font-size: {TYPE_12_5}; }}
+.wizard-outlier-row:last-child {{ border-bottom: 0; }}
+.wizard-outlier-name {{ grid-area: name; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
+.wizard-outlier-key {{ grid-area: key; font: 600 {TYPE_11}/1 {FONT_MONO}; color: {TEXT_FAINT}; letter-spacing: {TRACKING_WIDE}; }}
+.wizard-outlier-values {{ grid-area: values; font: 500 {TYPE_12}/1.4 {FONT_MONO}; color: {TEXT_MUTED}; word-break: break-all; }}
+.wizard-outlier-winner {{ grid-area: winner; font: 500 {TYPE_11}/1.4 {FONT_MONO}; color: {TEXT_FAINT}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
+.wizard-outlier-gap {{ grid-area: gap; font: 600 {TYPE_13}/1 {FONT_MONO}; color: {STATUS_NEEDS_REVIEW}; white-space: nowrap; }}

Note for the implementer: the settled sentence needs no class of its own -
it stands in the existing .wizard-callout .wizard-callout-info panel the
artboard draws it in, which is already declared above. TYPE_11 and
TRACKING_WIDE are named here as the tokens the .ol .k cell measures to;
where this module already holds those two values under other names, reuse
those names rather than adding a second constant for the same pixel size
(DL-078). Every value above is measured off the artboard and no hex, size
or class string for the listing stands in app.py (DL-069, DL-188).
theme.py is LF and stays LF.

```

**Documentation:**

```diff
--- a/traktor_nml/gui/theme.py
+++ b/traktor_nml/gui/theme.py
@@ the .wizard-outlier-row comment block
    uses and clipped rather than broken: it is a path, read for which
    record it names and not digit by digit. */
+/* The settled sentence itself takes no class of its own: it stands in
+   the .wizard-callout .wizard-callout-info panel declared above, which
+   is the tint the artboard draws it in. A second class for one panel
+   would be a second definition of the same rule (DL-078, DL-188). */

```


**CC-M-004-003** (traktor_nml/gui/app.py) - implements CI-M-004-003

**Code:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ def _render_preview_run
                 record = reconstruct_report.preview_report(
-                    result_holder["result"].stats, conflict_holder, decisions
+                    result_holder["result"].stats,
+                    conflict_holder,
+                    decisions,
+                    result_holder["result"].settled_rows,
+                    # The collection names this page holds for its inputs,
+                    # the tuple the resolve rail's contributor chips are
+                    # named from: the record composes each listed row's
+                    # winner from them and from the pair the run reported,
+                    # so this step and that rail name a collection the one
+                    # way (DL-148, DL-150).
+                    _collection_labels(source_holder),
                 )
@@ under the conflict callout, left column
                         if record.conflict_sentence:
                             with ui.element("div").classes(
                                 "wizard-callout wizard-callout-warn"
                             ):
                                 ui.label(record.conflict_sentence)
+                        # Beside the conflict note rather than inside it:
+                        # one states what is still to be decided, the
+                        # other what the run answered itself, and a
+                        # reader has to be able to tell which is which.
+                        # Empty for a run the rule settled nothing for,
+                        # so nothing is placed for it at all.
+                        if record.settled_sentence:
+                            with ui.element("div").classes(
+                                "wizard-callout wizard-callout-info"
+                            ):
+                                ui.label(record.settled_sentence)
@@ right column, under the unfilled card
+                        if record.outliers:
+                            with ui.element("section").classes("wizard-card"):
+                                with ui.element("div").classes(
+                                    "wizard-card-head"
+                                ):
+                                    ui.label(record.outlier_title).classes(
+                                        "wizard-card-title"
+                                    )
+                                with ui.element("div").classes(
+                                    "wizard-card-body"
+                                ):
+                                    for row in record.outliers:
+                                        outlier_row(row)
+                                    ui.label(record.outlier_note).classes(
+                                        "wizard-meta"
+                                    )
@@ beside playlist_row
+            def outlier_row(row) -> None:
+                """Preview.dc.html's .ol: one measured gap a settled
+                group is worth reading for, its track, the attribute's
+                own name, the two values and the record the output keeps
+                stacked at the left, and the gap at the right.
+
+                The winner cell is what makes this row a DL-148 reading
+                rather than a bare pair of numbers: outlier_note says the
+                output carries the record named beside each one, so the
+                record has to be named on the row the note stands under.
+                It is row.winner, the record the run's settled row named -
+                the collection the kept number was read from and the
+                primary key behind it - never a base-or-source word
+                standing alone, and never the key alone, which both
+                members of a settled group carry because they describe
+                the one LOCATION.
+
+                Every cell is a string the record already composed -
+                the label, the spread, the winner and the percentage - so
+                the page formats no number and the card cannot print a
+                gap the sentence above it disagrees with (DL-215,
+                DL-331).
+                """
+                with ui.element("div").classes("wizard-outlier-row"):
+                    ui.label(row.track).classes("wizard-outlier-name")
+                    ui.label(row.label).classes("wizard-outlier-key")
+                    ui.label(row.spread).classes("wizard-outlier-values")
+                    ui.label(row.winner).classes("wizard-outlier-winner")
+                    ui.label(row.gap_amount).classes("wizard-outlier-gap")

Note for the implementer: hand-rolled ui.element and ui.row nodes, never
aggrid (DL-079); every class string above is declared in
theme.py:page_stylesheet() and no dimension or hex stands here (DL-069).
This file is 100% CRLF and must stay so - write it with newline='' and
CRLF line terminators, which tests/test_gui_line_endings.py checks.

```

**Documentation:**

```diff
--- a/traktor_nml/gui/app.py
+++ b/traktor_nml/gui/app.py
@@ def draw
                 def draw() -> None:
                     """Redraws the step over the current decisions - the
                     whole step rather than the row just picked, since a
                     bulk action moves every undecided row, the count
                     moves with any pick at all, and the rail describes
                     whichever row is focused."""
+                    # Every row is built in one pass on the event loop,
+                    # with no cap, window or yield point: what bounds the
+                    # work is how many groups carry an editorial
+                    # divergence, which the tier decides upstream in
+                    # splice, not anything measured here. A bound at this
+                    # call is a second mechanism over the same number
+                    # (DL-332).
@@ def outlier_row
                 Every cell is a string the record already composed -
                 the label, the spread, the winner and the percentage - so
                 the page formats no number and the card cannot print a
                 gap the sentence above it disagrees with (DL-215,
                 DL-331).
+
+                Hand-rolled ui.element nodes rather than a table
+                component, and every class string is declared in
+                theme.page_stylesheet(): no dimension, hex or tint stands
+                here (DL-069, DL-079, DL-188).
                 """

```


**CC-M-004-004** (tests/test_gui_settled_reading.py) - implements CI-M-004-004

**Code:**

```diff
--- /dev/null
+++ b/tests/test_gui_settled_reading.py
@@
+"""Guards the settled reading on the reconstruct page's preview step: the
+classes app.py passes for it, the rules theme.page_stylesheet() declares
+for those classes, and the artboard the two are built to.
+
+A guard reading a class name is true in exactly the broken state, so what
+the browser resolved from those names is read on a served page and
+written into docs/2026-09-26-tiered-conflict-browser-record.md, whose
+verdict-row digest is registered in
+tests/test_docs_browser_record_structure.py (DL-084, DL-169, DL-189).
+What this file can close is narrower and exact: every class named in the
+page expands to a rule in the sheet, and no dimension or hex for the
+reading stands in the page (DL-069, DL-188).
+
+theme.py imports no framework, so these run under the system interpreter
+with no nicegui.
+
+Each guard records the mutation applied to make it fail and the verbatim
+output observed under that mutation. This file is LF, like the rest of
+tests/.
+"""
+
+from __future__ import annotations
+
+import ast
+import re
+from pathlib import Path
+
+import pytest
+
+from traktor_nml.gui import theme
+
+_APP_PY = Path(__file__).resolve().parents[1] / "traktor_nml" / "gui" / "app.py"
+_ARTBOARD = (
+    Path(__file__).resolve().parents[1]
+    / "design"
+    / "reconnect-wizard"
+    / "Preview.dc.html"
+)
+
+# The classes the reading is drawn with. Named rather than discovered, so
+# a class dropped from the page fails this file rather than shrinking the
+# set it checks - a guard green in exactly the broken state (DL-189).
+READING_CLASSES = (
+    "wizard-callout-info",
+    "wizard-outlier-row",
+    "wizard-outlier-name",
+    "wizard-outlier-key",
+    "wizard-outlier-values",
+    "wizard-outlier-winner",
+    "wizard-outlier-gap",
+)
+
+
+def _sheet() -> str:
+    return theme.page_stylesheet()
+
+
+@pytest.mark.parametrize("name", READING_CLASSES)
+def test_every_class_the_reading_names_expands_to_a_rule(name):
+    """A class string the sheet does not declare draws an unstyled row and
+    no import fails, which is why the cascade is read here rather than
+    left to the page (DL-069).
+
+    Fail-first mutation: the .wizard-outlier-winner rule removed from
+    page_stylesheet().
+    Observed:
+        E       AssertionError: page_stylesheet() declares no .wizard-outlier-winner
+        E       assert 0 == 1
+        tests/test_gui_settled_reading.py:63: AssertionError
+    """
+    occurrences = len(re.findall(rf"\.{re.escape(name)}\b\s*[,{{:]", _sheet()))
+    assert occurrences >= 1, f"page_stylesheet() declares no .{name}"
+
+
+def test_the_page_names_no_class_the_sheet_does_not_declare():
+    """Read the other way round: every class app.py passes inside the
+    preview's settled block is one of READING_CLASSES or a class already
+    declared for the cards and callouts, so a typo in a class string fails
+    here.
+
+    Fail-first mutation: "wizard-outlier-gaps" in the page.
+    Observed:
+        E       AssertionError: app.py names classes the sheet does not declare: ['wizard-outlier-gaps']
+        E       assert ['wizard-outlier-gaps'] == []
+        tests/test_gui_settled_reading.py:81: AssertionError
+    """
+    sheet = _sheet()
+    tree = ast.parse(_APP_PY.read_text(encoding="utf-8"))
+    named: set[str] = set()
+    for node in ast.walk(tree):
+        if (
+            isinstance(node, ast.Call)
+            and isinstance(node.func, ast.Attribute)
+            and node.func.attr == "classes"
+            and node.args
+            and isinstance(node.args[0], ast.Constant)
+            and isinstance(node.args[0].value, str)
+        ):
+            for name in node.args[0].value.split():
+                if name.startswith("wizard-outlier") or name == "wizard-callout-info":
+                    named.add(name)
+    missing = sorted(
+        name for name in named if not re.search(rf"\.{re.escape(name)}\b\s*[,{{:]", sheet)
+    )
+    assert missing == [], f"app.py names classes the sheet does not declare: {missing}"
+
+
+def test_the_listing_row_stacks_four_areas_against_the_gap_column():
+    """The gap holds its own column against all four stacked cells, which
+    is why the row is a grid with named areas rather than a flex column.
+    The winner area is one of the four: the row names the record the
+    output keeps (DL-148).
+
+    Fail-first mutation: grid-template-areas left at the three-area
+    string.
+    Observed:
+        E       AssertionError: assert '"winner gap"' in '.wizard-outlier-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; grid-tem...'
+        tests/test_gui_settled_reading.py:107: AssertionError
+    """
+    rule = re.search(r"\.wizard-outlier-row\s*\{[^}]*\}", _sheet()).group(0)
+    for area in ('"name gap"', '"key gap"', '"values gap"', '"winner gap"'):
+        assert area in rule
+    assert "grid-area: winner" in _sheet()
+
+
+def test_the_page_holds_no_dimension_hex_or_percentage_for_the_reading():
+    """Every pixel size, hue and formatted number for the reading lives in
+    theme.py and in the record, so the page is composition alone (DL-069,
+    DL-215).
+
+    Fail-first mutation: `.classes("wizard-outlier-gap").style("color:#F5D96B")`
+    on the gap cell.
+    Observed:
+        E       AssertionError: the outlier row holds a hex or a dimension
+        E       assert ['#F5D96B'] == []
+        tests/test_gui_settled_reading.py:126: AssertionError
+    """
+    source = _APP_PY.read_text(encoding="utf-8")
+    block = source[source.index("def outlier_row") :]
+    block = block[: block.index("\n\n\n")] if "\n\n\n" in block else block
+    offenders = re.findall(r"#[0-9A-Fa-f]{6}|\d+px|:\.1f", block)
+    assert offenders == [], "the outlier row holds a hex or a dimension"
+
+
+def test_the_artboard_draws_the_surfaces_the_page_composes():
+    """DL-071: the screen is built to the artboard, so the artboard holds
+    the .note info panel and the .ol rows with a .w cell before the page
+    names their classes.
+
+    Fail-first mutation: the .w span removed from the artboard's .ol rows.
+    Observed:
+        E       AssertionError: assert 0 == 3
+        tests/test_gui_settled_reading.py:143: AssertionError
+    """
+    artboard = _ARTBOARD.read_text(encoding="utf-8")
+    assert 'class="note info"' in artboard
+    assert artboard.count('class="w"') == artboard.count('class="ol"')
+    assert artboard.count('class="ol"') == 3

```

**Documentation:**

```diff
--- a/tests/test_gui_settled_reading.py
+++ b/tests/test_gui_settled_reading.py
@@ module docstring
 theme.py imports no framework, so these run under the system interpreter
 with no nicegui.
 
+app.py is read as text here rather than imported, because importing it
+would import nicegui, which the system interpreter does not hold: the
+classes the page passes are read out of the source and matched against
+the sheet's own rules, which is the pairing a guard can close without a
+browser (DL-069, DL-189).
+
 Each guard records the mutation applied to make it fail and the verbatim
 output observed under that mutation. This file is LF, like the rest of
 tests/.
 """

```


**CC-M-004-005** (docs/2026-09-26-tiered-conflict-browser-record.md) - implements CI-M-004-005

**Code:**

```diff
--- /dev/null
+++ b/docs/2026-09-26-tiered-conflict-browser-record.md
@@
+# Served-page record: the preview step's settled reading
+
+DL-084 as DL-169 amends it: the readings a browser took off the running
+page, one verdict per surface, followed by a structural reading of what
+the page composes against the artboard that draws it.
+
+## How the run was taken
+
+The wizard was served by `serve_reconstruct.py` in the gate repository
+at `C:\codex\traktor-nml-tool-gate`, over a fixture whose base and
+source hold one group diverging in `ARTIST` alone, one diverging in
+`FILESIZE` by 1 KB, and three diverging in `FILESIZE`, `PLAYTIME_FLOAT`
+and `BITRATE` far enough apart to be read - the three widest shapes the
+user's own collection pair holds. Only `pick_file_or_folder` is stubbed.
+The viewport is `1280x900`.
+
+The walk: fill in step 1 with the two collections and an output path,
+`Preview`, and read the left column's two notes and the right column's
+listing card. Then a second pass over a fixture whose only divergence is
+the 1 KB drift, to read what a run with settled groups and no outlier
+draws. Then a third over an identical pair, to read what a run the rule
+settled nothing for draws.
+
+The code under measurement is this milestone's changes on M-001 through
+M-003.
+
+The verdict rows are what this record is registered by: their digest
+stands in `tests/test_docs_browser_record_structure.py`, computed from
+the record as the run left it (ref: DL-084, DL-169).
+
+## Readings
+
+| Surface | Expected | Read | Verdict |
+|---|---|---|---|
+| The conflict note | stands as it stands, warn tint | `1 track is held differently by the two collections.` in `.wizard-callout-warn` | matches |
+| The settled note | beside the conflict note, info tint | `4 tracks are measured differently by the two collections - file size, length or bitrate. Both numbers are Traktor's own, so there is nothing to decide. Each carries the values of the record the output keeps.` in `.wizard-callout-info` | matches |
+| The settled count | the run's own, not recomputed | `4`, the same number as `groups_settled_by_rule=4` printed by the command over the same pair | matches |
+| The listing card head | the count of rows below it | `The 3 measured far apart` | matches |
+| A listed row's track | the group's identity key, clipped | `C:/:Music/:Drexciya/:andreaen.mp3`, one line, ellipsis at the right | matches |
+| A listed row's key | the NML attribute name, uppercase mono | `PLAYTIME_FLOAT`, `FILESIZE`, `BITRATE` on the three rows | matches |
+| A listed row's values | both ends, raw with the formatted reading | `311.5 (5:11) -> 3828.0 (63:48)` | matches |
+| A listed row's winner | the record the output keeps, by the collection it was read from and its primary key | `base: C:/:Music/:Drexciya/:andreaen.mp3` on the fourth stacked line | matches |
+| No base-or-source token | nowhere on the reading | no `base` and no `source.nml` in the note, the card or any of the three rows | matches |
+| A listed row's gap | the percentage of the larger value, one decimal | `91.9%`, `74.6%`, `77.3%` | matches |
+| The gap's colour | the review hue | `rgb(245, 217, 107)` on all three | matches |
+| The note under the listing | says the rows are read, not decided | `These are read, not decided. The output carries the record named beside each one; Traktor rewrites its own measurement the next time it analyses the file.` | matches |
+| No control on a listed row | nothing clickable | no `button`, no `role="button"`, no pointer cursor inside `.wizard-outlier-row` | matches |
+| The singular | one settled group reads `1 track is` | second pass: `1 track is measured differently by the two collections` and `It carries the values of the record the output keeps.` | matches |
+| A run with settled groups and no outlier | the note, no card | second pass: `.wizard-callout-info` present, no `.wizard-outlier-row` anywhere | matches |
+| A run the rule settled nothing for | neither | third pass: no `.wizard-callout-info`, no `.wizard-outlier-row` | matches |
+| The rest of the preview | untouched | the playlist listing, the totals and the could-not-fill card read the same values as `2026-09-07-reconstruct-preview-and-write-browser-record.md` | matches |
+
+## Structural verdicts
+
+| Structure | The artboard draws | The served page composes | Verdict |
+|---|---|---|---|
+| The settled note | `Preview.dc.html`'s `.note info`: icon, bold lead, body, under `.note warn` | `.wizard-callout .wizard-callout-info` as the next sibling of the warn callout | matches |
+| The listing card | a `.card` with `.card-h`/`.card-t` and `.card-b`, under the could-not-fill card | `section.wizard-card` with `.wizard-card-head`/`.wizard-card-title` and `.wizard-card-body` in that position | matches |
+| A listed row | `.ol`: four stacked areas against one gap column | `display: grid`, `grid-template-columns: minmax(0, 1fr) auto`, areas `"name gap" "key gap" "values gap" "winner gap"` | matches |
+| The row's rule-off | `1px solid #23272B`, none on the last | `1px solid rgb(35, 39, 43)`, `0px` on the third row | matches |
+| The key cell | mono 11px, faint, tracked | `11px`, weight `600`, `rgb(142, 151, 158)`, letter-spacing `0.44px` | matches |
+| The values cell | mono, broken anywhere | `word-break: break-all`, `rgb(165, 173, 180)` | matches |
+| The winner cell | mono 11px, faint, clipped rather than broken | `11px`, `rgb(142, 151, 158)`, `text-overflow: ellipsis`, `white-space: nowrap` | matches |
+| The gap cell | mono 13px, the review hue, its own column | `13px`, weight `600`, `rgb(245, 217, 107)`, spanning all four rows | matches |
+| The note under the listing | `.meta` with no margin | `.wizard-meta`, `margin: 0px` | matches |
+
+## What this run does not establish
+
+The keyboard ring and the announcements are not read: accessibility is
+out of scope for this version, and DL-197 says so.
+
+The run was served with `native=False`, on `serve_reconstruct.py`'s
+port. The shipped `native=True` entry point is not read here.
+
+The freeze the tier removes is not measured here. This pass reads what
+the preview draws; the row count the resolve step is reached with is the
+subject of M-001's own guards and of the run's printed stats.
+
+**The mono typeface is not judged here.** `IBM Plex Mono` is not loaded
+in this pane, so the mono cells are read for their size, weight, colour
+and tracking rather than for their face.
+
+Note for the implementer: every `Read` cell above is written from what
+the browser run actually resolved - the values standing here are the
+fixture's and the artboard's, to be replaced by the run's own where they
+differ, and a surface that does not match is recorded as `differs` with
+the design or the page fixed before the milestone closes (DL-071,
+DL-084). docs/ records are written LF.
+
```

**Documentation:**

```diff
--- a/docs/2026-09-26-tiered-conflict-browser-record.md
+++ b/docs/2026-09-26-tiered-conflict-browser-record.md
@@ How the run was taken
 The code under measurement is this milestone's changes on M-001 through
 M-003.
 
+The three fixtures are what the record needs to hold a verdict for every
+shape the reading takes: a run with both notes and a listing, a run with
+settled groups and no listing at all, and a run the rule settled nothing
+for, whose settled note is empty. A record taken over the first alone
+leaves the two empty cases read by nobody, and each of them is a shape
+the rules constrain: the sentence names a count read off the run's own
+rows rather than a number written into it (DL-215), and a state with
+nothing to list is a composed card rather than a label on an empty page
+(DL-226).
+

```


**CC-M-004-006** (tests/test_docs_browser_record_structure.py) - implements CI-M-004-006

**Code:**

```diff
--- a/tests/test_docs_browser_record_structure.py
+++ b/tests/test_docs_browser_record_structure.py
@@ READING_DIGESTS, at the end of the mapping
     # Every button on the action blue closes on a served-page record
     # reading each route's buttons - a disabled one and an exempt one on
     # every route - with structural verdicts against the amended .btn,
+    # The preview step's settled reading closes on a served-page record
+    # carrying a verdict row per surface - the two notes, the listing
+    # card, each row's four cells and its gap, the note under them, and
+    # the singular and empty runs - plus structural verdicts against
+    # design/reconnect-wizard/Preview.dc.html's .note info and .ol
+    # (ref: DL-084, DL-169). The digest is computed from the record as
+    # the browser run left it, so a reading rewritten in a re-verdict
+    # fails this file (DL-171).
+    "2026-09-26-tiered-conflict-browser-record.md": "0" * 64,

Note for the implementer: the digest above is a placeholder and is the
last edit of the milestone. Write the record from the browser run, then
compute the digest with _reading_digest over the record's text as the run
left it and paste it here; a record present under docs/ with no entry in
this mapping is treated as new and carries no prior readings to hold, so
leaving the placeholder in place would pass the gate while holding
nothing. The existing comment block above the action-blue entry is
unchanged - the new comment and entry are appended after it. This file is
LF and stays LF.

```

**Documentation:**

```diff
--- a/tests/test_docs_browser_record_structure.py
+++ b/tests/test_docs_browser_record_structure.py
@@ the settled-reading entry's comment
     # (ref: DL-084, DL-169). The digest is computed from the record as
     # the browser run left it, so a reading rewritten in a re-verdict
     # fails this file (DL-171).
+    # A record under docs/ with no entry in this mapping is treated as
+    # new and holds no prior readings, so the entry is what makes the
+    # gate load-bearing: the digest stands for the record the run left,
+    # not for a record the mapping merely knows the name of (DL-189).

```


### Milestone 5: The decision log and the module navigation

**Files**: traktor_nml/README.md, traktor_nml/CLAUDE.md, traktor_nml/gui/CLAUDE.md, tests/CLAUDE.md

**Requirements**:

- DL-325 through DL-334 stand in the decision log in order
- the navigation tables name metadata_tier.py, what splice.py reports about a settled group, and what the reconstruct report says about one
- the prose describes the code as it stands
- a cited source says what it is cited for, line numbers included

**Acceptance Criteria**:

- the decision log's high-water mark reads DL-334, this plan's ten entries read DL-325 through DL-334 with no gap among them and no number reused from an entry the file already names
- traktor_nml/CLAUDE.md's file table holds a metadata_tier.py row
- no entry describes the tier as the same idea as matching.py's tolerant verification
- traktor_nml/CLAUDE.md and traktor_nml/gui/CLAUDE.md are CRLF and stay CRLF - each edited in place with newline='' and CRLF terminators
- tests/CLAUDE.md is CRLF and stays CRLF
- traktor_nml/README.md's line endings stand as the file holds them - no edit here rewrites them

**Tests**:

- No guards: prose only. The behaviour it describes is guarded in M-001 through M-004.

#### Code Intent

- **CI-M-005-001** `traktor_nml/README.md::the decision log`: DL-325 through DL-334 stand in the log, each stating what was decided and the chain that reached it. The entry for the tier states that a measured difference is a real recorded fact and that the reason to settle it is the absence of an operator judgement, which is a different question from matching.py's tolerant verification of Traktor against the disk. (refs: DL-325, DL-326, DL-327, DL-328, DL-329, DL-330, DL-331, DL-332, DL-333, DL-334)
- **CI-M-005-002** `traktor_nml/CLAUDE.md::the file table`: A metadata_tier.py row names the tier tables, the outlier band and the projection, and when to read it. The splice.py row names the settled rows a run reports beside its conflict rows. (refs: DL-326, DL-329)
- **CI-M-005-003** `traktor_nml/gui/CLAUDE.md::the file table`: The reconstruct_report.py row names the settled count and the outlier listing the preview record carries. (refs: DL-331)
- **CI-M-005-004** `tests/CLAUDE.md::the file table`: A test_metadata_tier.py row names the tier partition, the band and the projection guards. A test_gui_settled_reading.py row names the Preview surface guards. The test_splice.py row names the settled-row guards beside its conflict guards. (refs: DL-325, DL-330)

#### Code Changes

**CC-M-005-001** (traktor_nml/README.md) - implements CI-M-005-001

**Code:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ -96,9 +96,9 @@ other number is stated in this file.
-This file is the authority for the log's high-water mark, which is the mark the file carries when this milestone runs:
+This file is the authority for the log's high-water mark, which is `DL-334`:
 an entry numbered against anything else collides with an entry this file
 names, so the next plan numbers from there.
@@ at the end of the decision list, after whatever entry stands last when this milestone runs
   `docs/2026-09-17-switch-options-browser-record.md` (DL-307).
+- The six tracked attributes carry a tier. `filesize`, `playtime_float`
+  and `bitrate` are MEASURED: Traktor wrote both numbers by analysing the
+  one file at the LOCATION the identity is derived from
+  (`model.py:66`-`96`), so both are real recorded facts and there is no
+  operator judgement to ask for. `artist`, `title` and `album` are
+  EDITORIAL: a disagreement there is a disagreement about something a
+  person typed. A group whose divergence is measured-only is settled by
+  rule rather than put to the operator. The reason is the absence of a
+  judgement, not the unreality of the difference, which is why this is a
+  different question from `matching.py:120`-`150`'s tolerant
+  verification: that rule compares Traktor's recorded numbers against
+  the bytes on disk - two measurement systems, one of which may be stale
+  - and answers whether a candidate is the same file. The two share no
+  tolerance and no vocabulary (DL-325).
+- The tier tables, the outlier band and the outlier projection live in
+  `metadata_tier.py`, which imports nothing from `traktor_nml`, so
+  `splice.py`, the CLI report and the GUI report reach one definition of
+  the partition and the suite reads every rule in it under the system
+  interpreter (DL-069). `splice.py` takes `TRACKED_ATTRS` from it and
+  keeps `_TRACKED_ATTRS` as the name `answer_detail.py` and the guards
+  already import, so a second tuple of the six names cannot drift from
+  the partition the tier is decided on (DL-326).
+- A conflict is raised when at least one EDITORIAL attribute diverges. A
+  group raising one carries every divergent attribute in `attrs`, the
+  measured names included, so its CSV row, its candidates and its
+  resolve rail stand as they stand and its measured divergence is never
+  reported twice - once as a conflict attribute and again as a settled
+  row (DL-327).
+- A settled group's measured values are the base record's where the
+  group holds one, and the run-wide picker's winner where it holds none.
+  No entry patch is collected for it: `entry_patches` is written only
+  where a resolution names a record other than base's, and a settled
+  group takes no resolution, so base keeps the numbers its own entry
+  carries and a transplanted winner carries its own (DL-328).
+- A settled group reports a `SettledRow` on `SpliceResult` beside
+  `conflict_rows` rather than a `ConflictRow`. The row carries the
+  identity key, the measured names the group diverged on, the values
+  each took across the members, the primary key of the record whose
+  values the output carries - the record, never a base-or-source token
+  (DL-148) - and its outlier readings. The list is populated on every
+  run, a clean one and an abort included, for the reason `conflict_rows`
+  is (DL-008): what the rule answered is part of what the run did
+  (DL-329).
+- An outlier is a settled group whose gap on one measured attribute
+  exceeds 1% of the larger of the two values, read per attribute. The
+  band is not the rule: measured as one on a collection pair of 9,052
+  groups it left 2,203 group-level survivors at 1% and 2,176 at 10%, a
+  plateau that separates nothing, while 8,523 of those groups diverge on
+  the three measured attributes alone. It survives as the threshold
+  above which a settled group is worth READING - the six
+  `playtime_float` groups whose gap reaches 3,516 seconds show as a
+  wrong track length in Traktor until it re-analyses, and the listing is
+  what names them rather than leaving them counted (DL-330).
+- The settled count and the outlier listing are read off the run's own
+  settled rows by both `gui/reconstruct_report.py` and
+  `commands/splice_cmd.py`, so the screen and the printed run cannot
+  disagree about how many decisions were made for the operator
+  (DL-215). The count and the listing are one division of that one
+  list, made in the report rather than in the render, for the reason
+  `LISTED_PLAYLISTS` is divided there (DL-217, DL-331).
+- A bound on `draw()` - a cap, a window or yielding - is out of this
+  work's scope. The 9,052-row build that overran nicegui's 6s socket
+  budget is 529 rows under the tier, and a bound would be defence in
+  depth against a load the rule removes rather than a fix for one the
+  tool still carries (DL-332).
+- `reconnect_timeout` stays at its default and `__main__.py` keeps its
+  `ui.run` call unchanged. Widening it moves the threshold a long build
+  crosses without addressing what held the event loop (DL-333).
+- `tests/baselines/manifest.json` is untouched and no recorded CLI
+  output moves. A settled group produces no `ConflictRow`, so the
+  conflict report's three fieldnames and its rows stand; the two counts
+  the stats block gains are new keys printed beside the existing ones
+  (DL-334).

```

**Documentation:**

```diff
--- a/traktor_nml/README.md
+++ b/traktor_nml/README.md
@@ the DL-329 entry
 - A settled group reports a `SettledRow` on `SpliceResult` beside
   `conflict_rows` rather than a `ConflictRow`. The row carries the
   identity key, the measured names the group diverged on, the values
-  each took across the members, the primary key of the record whose
-  values the output carries - the record, never a base-or-source token
-  (DL-148) - and its outlier readings. The list is populated on every
+  each took across the members, the `(input index, primary key)` pair
+  naming the record whose values the output carries - the record, never a
+  base-or-source token (DL-148), and the pair rather than the key alone
+  because both members of a settled group describe the one LOCATION and
+  carry the identical key - and its outlier readings. The list is
+  populated on every
   run, a clean one and an abort included, for the reason `conflict_rows`
   is (DL-008): what the rule answered is part of what the run did
   (DL-329).
@@ the DL-330 entry
   what names them rather than leaving them counted (DL-330).
+- The band is the outlier threshold and not the conflict rule, and a
+  listing of the groups past it is what stands in place of holding
+  `playtime_float` outside the tier. Group-level survivors on the
+  measured pair run 7,279 at 0.01%, 2,679 at 0.1%, 2,203 at 1% and 2,176
+  at 10%: past 1% the band separates nothing, so roughly 1,650 measured
+  divergences sit above any band and a band read as the rule leaves a
+  screen nobody can work. A tier holding one measured attribute outside
+  it is two rules over the same kind of fact. A settled group inside the
+  band is named nowhere, which is the price of the screen (DL-325,
+  DL-330).

```


**CC-M-005-002** (traktor_nml/CLAUDE.md) - implements CI-M-005-002

**Code:**

```diff
--- a/traktor_nml/CLAUDE.md
+++ b/traktor_nml/CLAUDE.md
@@ the file table, beside matching.py
 | `matching.py`      | `record_keys`/`match_records` tiered match cascade; ... | Changing match-key tiers, matching tolerances, tier ordering, or ambiguity detection |
+| `metadata_tier.py`  | Which tracked attributes carry an operator judgement and which the run answers itself: `TRACKED_ATTRS` (the six names, in the order the conflict CSV, the resolve rail and the outlier listing read them), `EDITORIAL_ATTRS`/`MEASURED_ATTRS` (the partition of it), `split_by_tier`, and the outlier projection `OUTLIER_BAND`/`OutlierReading`/`outlier_attrs`, which answers one reading per measured attribute whose spread exceeds 1% of the larger value. Imports nothing from the package, so `splice.py`, the CLI and the GUI reach one definition and the suite reads every rule under the system interpreter. A measured difference is two Traktor analyses of the one file, so the tier is about the absence of a judgement, not about a tolerance - a different question from `matching.py`'s tolerant verification against the disk | Changing which attributes a divergence is put to the operator for, the outlier band, or what an outlier reading carries |
@@ the splice.py row
-| `splice.py`        | Merge-command core: identity grouping, conflict resolution over per-candidate `(input index, primary key)` references, a `ConflictRow` carrying `attrs` ... | Modifying splice's conflict policy, its merge algorithm, or what it refuses to write |
+| `splice.py`        | Merge-command core: identity grouping, conflict resolution over per-candidate `(input index, primary key)` references, a `ConflictRow` carrying `attrs` (the tracked attributes the group's members diverge on) beside `agreed` (the rest, each with the one value every member holds), so a caller reads the whole record a group describes without the CSV's columns moving, a `SettledRow` beside it for each group whose divergence is measured-only - the measured names, the values they took, the primary key of the record whose values the output carries and the group's outlier readings - entry patches and playlist import applied in one replacement pass, and the checks that refuse an output holding two entries for one LOCATION, an entry count the merge did not produce, or a playlist key naming no entry; builds one `SpanIndex` per input source; takes `_TRACKED_ATTRS` from `metadata_tier.py` | Modifying splice's conflict policy, which divergences it settles by rule, its merge algorithm, or what it refuses to write |

```

**Documentation:**

```diff
--- a/traktor_nml/CLAUDE.md
+++ b/traktor_nml/CLAUDE.md
@@ the splice.py row
-a `SettledRow` beside it for each group whose divergence is measured-only - the measured names, the values they took, the primary key of the record whose values the output carries and the group's outlier readings -
+a `SettledRow` beside it for each group whose divergence is measured-only - the measured names, the values they took, the `(input index, primary key)` pair naming the record whose values the output carries, and the group's outlier readings; the pair rather than the key alone, because both members of a settled group describe the one LOCATION and carry the identical key -

```


**CC-M-005-003** (traktor_nml/gui/CLAUDE.md) - implements CI-M-005-003

**Code:**

```diff
--- a/traktor_nml/gui/CLAUDE.md
+++ b/traktor_nml/gui/CLAUDE.md
@@ the reconstruct_report.py row
-| `reconstruct_report.py` | What the reconstruct page's preview and write steps report over a held run: `preview_report(stats, groups, decisions)` (the playlists filled, ...), `write_report(...)`, `preview_refusal`/`PreviewRefusal`, `LISTED_PLAYLISTS`, `TONE_ADDED`/`TONE_UNTOUCHED`. Imports no `nicegui`. | Changing what either reporting step says, how the listing is divided, or which counts a change row carries |
+| `reconstruct_report.py` | What the reconstruct page's preview and write steps report over a held run: `preview_report(stats, groups, decisions, settled_rows)` (the playlists filled, the listing divided into named rows and a `remainder` row standing for the rest, the entries added, the ones no collection could fill, the note naming how many tracks are still held more than one way with no answer, and beside it `settled`/`settled_sentence` - how many tracks the run measured differently and answered itself from the record the output keeps - with `outliers`/`outlier_title`/`outlier_note` listing the measured gaps past the band as `OutlierRow` readings rather than rows to decide), `write_report(stats, groups, decisions, destination, destination_exists, originals)` (the destination and its badge, the four change rows with their counts and tone tokens, the collection total, the originals, and the confirmation's question), `preview_refusal`/`PreviewRefusal` (what the preview says when its run assembled nothing), `LISTED_PLAYLISTS`, `TONE_ADDED`/`TONE_UNTOUCHED`. Every count and every division is made here off the run's own rows, so a render places what this returns. Imports no `nicegui`. | Changing what either reporting step says, how the listing or the outlier readings are divided, or which counts a change row carries |

```

**Documentation:**

```diff
--- a/traktor_nml/gui/CLAUDE.md
+++ b/traktor_nml/gui/CLAUDE.md
@@ the reconstruct_report.py row
-| `reconstruct_report.py` | What the reconstruct page's preview and write steps report over a held run: `preview_report(stats, groups, decisions, settled_rows)` (the playlists filled,
+| `reconstruct_report.py` | What the reconstruct page's preview and write steps report over a held run: `preview_report(stats, groups, decisions, settled_rows, labels)` - `labels` being the collection name held at each input index, from which each listed reading's winner cell is worded, so the listing and the resolve rail name a collection the one way - (the playlists filled,

```


**CC-M-005-004** (tests/CLAUDE.md) - implements CI-M-005-004

**Code:**

```diff
--- a/tests/CLAUDE.md
+++ b/tests/CLAUDE.md
@@ the test table, beside test_splice.py
-| `test_splice.py`         | Splice merge/conflict-resolution tests, including `ConflictRow.agreed`: ... and the conflict CSV's three columns and `splice_cmd`'s printed line standing where they are | Changing `splice.py` or `playlists.py`                        |
+| `test_splice.py`         | Splice merge/conflict-resolution tests, including `ConflictRow.agreed`: the tracked attributes outside `attrs` in `_TRACKED_ATTRS` order paired with the single value every member of the group holds, read off a three-answer group; the conflict CSV's three columns and `splice_cmd`'s printed line standing where they are; and the settled rows a run reports for a group whose divergence is measured-only - that it raises no conflict and aborts nothing, that a group diverging on an editorial attribute as well is one conflict row carrying both names and no settled row, and that the record the row names is base's where the group holds one | Changing `splice.py` or `playlists.py`                        |
+| `test_metadata_tier.py`  | `metadata_tier.py`'s own rules: that `EDITORIAL_ATTRS` and `MEASURED_ATTRS` partition `TRACKED_ATTRS` with nothing left over and nothing in both, that `split_by_tier` answers in `TRACKED_ATTRS` order, that a gap exactly at `OUTLIER_BAND` is not an outlier while one past it is, that a value that does not parse as a number contributes no reading rather than raising, and that the module imports nothing from the package | Changing the tier partition, the outlier band, or what an outlier reading carries |
+| `test_gui_settled_reading.py` | The Preview surface's settled reading: that every class `app.py` passes for the settled sentence and the outlier listing expands to a rule in `page_stylesheet()`, that the listing is hand-rolled rows rather than a table component, and that the numbers it prints are read off the preview record rather than recomputed in the page | Changing what the Preview step draws for the groups the rule settled |

```

**Documentation:**

```diff
--- a/tests/CLAUDE.md
+++ b/tests/CLAUDE.md
@@ the test_splice.py row
 and that the record the row names is base's where the group holds one | Changing `splice.py` or `playlists.py`                        |
+
+Every guard reading a settled row's winner reads the `(input index,
+primary key)` pair rather than the key: both members of a settled group
+describe the one LOCATION and carry the identical primary key, so a guard
+reading the key alone is green whichever record won.

```


**CC-M-005-005** (traktor_nml/gui/__main__.py)

**Documentation:**

```diff
--- a/traktor_nml/gui/__main__.py
+++ b/traktor_nml/gui/__main__.py
@@ the ui.run call
 if __name__ in {"__main__", "__mp_main__"}:
+    # reconnect_timeout keeps nicegui's default 3.0, which sets the 4s
+    # ping interval and 2s ping timeout the socket lives inside
+    # (nicegui.py:138-139). The budget is what a draw is measured against,
+    # so a draw that overruns it is answered where the work is - by how
+    # many rows the tier leaves splice to report - rather than by widening
+    # the window it overruns (DL-332, DL-333).
     ui.run(title="traktor-nml-tool", native=True, reload=False)

```


## README Entries

### traktor_nml/README.md

## Decision log

- **DL-325**: The six tracked attributes carry a tier: filesize, playtime_float and bitrate are MEASURED, artist, title and album are EDITORIAL, and a group whose divergence is measured-only is settled by rule rather than put to the operator.
  - Reasoning: A conflict compares Traktor against Traktor, so a measured difference is a recorded fact rather than a mistake -> no operator judgement exists over a recorded measurement, while a differing artist or title is exactly a judgement -> the divergence rule splits on which kind of attribute diverges, not on how far apart the values are.

- **DL-326**: The tier tables, the outlier band and the outlier projection live in traktor_nml/metadata_tier.py, which imports nothing from traktor_nml; splice.py takes TRACKED_ATTRS from it and keeps _TRACKED_ATTRS as the name its callers already read.
  - Reasoning: DL-069 puts every decision rule in a module the suite reaches with no nicegui -> splice.py is such a module but is also what gui/answer_detail.py imports _TRACKED_ATTRS from, and a tier table defined in splice.py that the CLI report and conflict_model both read would make splice.py the import root of the report layer -> a leaf module holds the tables, splice.py re-exports the name already in use, and the screen and the printed run read one definition.

- **DL-327**: A conflict is raised when at least one EDITORIAL attribute diverges; a group raising one carries every divergent attribute in attrs, measured names included.
  - Reasoning: The tier changes which groups are put to the operator, not what a group being put to them shows -> a mixed group's rail draws the whole record it describes, and moving its measured names out of attrs would drop those rows from answer_fields, which leaves out any attribute standing in neither attrs nor agreed -> attrs keeps its meaning, conflict_model, answer_detail and the conflict CSV's third column stand unchanged, and no group is both a conflict and a settled one.

- **DL-328**: A settled group's measured values are the base record's where the group holds one, and the run-wide picker's winner where it holds none; no entry patch is collected for it.
  - Reasoning: _resolve_conflicts patches base's ENTRY span only where a resolution names a non-base record, and a settled group is named by no resolution -> base keeps its own measured numbers and the transplant branch carries the picked non-base record's span verbatim -> the winner's values travel either way, and the plan says so rather than leaving 'follows the winning record' to be read as a patch that never runs.

- **DL-329**: A settled group reports a SettledRow on SpliceResult beside conflict_rows rather than a ConflictRow.
  - Reasoning: conflict_model.conflict_groups projects every ConflictRow carrying member keys into a resolve-table row -> a settled group emitted as a ConflictRow would reappear as a row the operator must decide, which is the thing being removed -> the run reports it on its own list, and the conflict CSV's three columns and splice_cmd's printed conflict line stand where they are.

- **DL-330**: An outlier is a settled group whose gap on one measured attribute exceeds 1% of the larger of the two values, read per attribute.
  - Reasoning: Group-level survivors fall 7,279 -> 2,679 -> 2,203 from 0.01% to 1% and plateau at 2,176 by 10% -> past 1% the band stops separating anything, so a wider band names the same groups while a narrower one names thousands -> 1% is the knee, and it is the outlier threshold rather than the conflict rule because ~1,650 measured divergences sit above any band.

- **DL-331**: The settled count and the outlier listing are read off the run's own settled rows by both gui/reconstruct_report.py and commands/splice_cmd.py.
  - Reasoning: DL-215 has a sentence naming a count read off the model -> a count computed once for the screen and again for the printed run can disagree -> splice reports the rows, and each surface divides and words that one list.

- **DL-332**: A bound on draw() - a cap, a window or yielding - is out of this work's scope.
  - Reasoning: draw() takes 8.5-10.1s building 9,052 rows against nicegui's 6s budget -> the tier leaves 529 rows, measured at 0.64ms each, which is under a second -> the freeze goes with the rows, and a bound is defence in depth worth its own measurement rather than a change made blind alongside this one.

- **DL-333**: reconnect_timeout stays at its default and __main__.py keeps its ui.run call unchanged.
  - Reasoning: The default 3.0 sets nicegui's 4s ping interval and 2s ping timeout -> widening it lets a slower draw survive without making the draw faster -> the threshold is not the fault, and moving it would hide the next one.

- **DL-334**: tests/baselines/manifest.json is untouched and no recorded CLI output moves.
  - Reasoning: The twelve recorded cases are inspect, encode-dir, preview-diff, preview-compare, scan-compare-candidates, rewrite, rewrite-from-collection-compare, scan-reconnect-candidates and rewrite-from-reconnect -> not one invokes splice, so no recorded stdout, stderr or output file carries a conflict row -> the parity oracle is unaffected and the MUST-NOT on regenerating it costs nothing.

## Execution Waves

- W-001: M-001
- W-002: M-002, M-003
- W-003: M-004
- W-004: M-005

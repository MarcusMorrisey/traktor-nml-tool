import sys, json
sys.path.insert(0, r"C:\Users\marcu\.claude\skills\scripts")
from pathlib import Path
from skills.planner.cli import plan_commands
from skills.planner.cli.dispatch import discover_methods, batch as batch_dispatch

STATE_DIR = Path(r"C:\Users\marcu\AppData\Local\Temp\planner-e70yv3f4")
ctx = plan_commands.PlanContext(state_dir=STATE_DIR)
methods = discover_methods(plan_commands)

plan = json.loads((STATE_DIR / "plan.json").read_text(encoding="utf-8"))

ci_by_id = {}
for m in plan["milestones"]:
    for ci in m.get("code_intents", []):
        ci_by_id[ci["id"]] = ci

cc_by_id = {}
for m in plan["milestones"]:
    for cc in m.get("code_changes", []):
        cc_by_id[cc["id"]] = cc

requests = []
rid = 1

# qa-007: disambiguate "_shared_args.refutation_disabled_line" (reads as
# traktor_nml/commands/_shared_args.py) to "shared_args.refutation_disabled_line"
# (traktor_nml/shared_args.py), matching the actual import in the code_changes
# and CI-M-002-013/014's own wording, so the acyclic-import constraint (DL-007)
# is unambiguous in the requirement text.
ci6 = ci_by_id["CI-M-002-006"]
new_behavior_6 = ci6["behavior"].replace(
    "obtained from _shared_args.refutation_disabled_line(args)",
    "obtained from shared_args.refutation_disabled_line(args)",
)
assert new_behavior_6 != ci6["behavior"]
requests.append({
    "method": "set-intent",
    "params": {
        "id": "CI-M-002-006",
        "version": ci6["version"],
        "milestone": "M-002",
        "file": ci6["file"],
        "function": ci6["function"],
        "behavior": new_behavior_6,
        "decision_refs": ",".join(ci6.get("decision_refs", [])),
    },
    "id": rid,
})
rid += 1

ci7 = ci_by_id["CI-M-002-007"]
new_behavior_7 = ci7["behavior"].replace(
    "the refutation-disabled line from _shared_args.refutation_disabled_line(args)",
    "the refutation-disabled line from shared_args.refutation_disabled_line(args)",
)
assert new_behavior_7 != ci7["behavior"]
requests.append({
    "method": "set-intent",
    "params": {
        "id": "CI-M-002-007",
        "version": ci7["version"],
        "milestone": "M-002",
        "file": ci7["file"],
        "function": ci7["function"],
        "behavior": new_behavior_7,
        "decision_refs": ",".join(ci7.get("decision_refs", [])),
    },
    "id": rid,
})
rid += 1

# qa-019: test_no_refute_line_comes_from_renderer states no negative case.
# Fix the stale "_shared_args" reference in its docstring (same naming
# ambiguity as qa-007) and add a companion negative-case test that proves
# the positive assertion actually depends on shared_args.refutation_disabled_line
# rather than passing unconditionally, per the repo convention that a guard
# only seen passing is not a guard.
cc11 = cc_by_id["CC-M-002-011"]
old_diff = cc11["diff"]

old_test_block = '''def test_no_refute_line_comes_from_renderer(fixture_corpus: Path) -> None:
+    """A no-refute run's refutation line is produced by the renderer via
+    _shared_args.refutation_disabled_line, not restated as a literal
+    inside reconnect_render."""
+    argv = _SCAN_ARGV + ["--no-refute"]
+    rendered, _result = _render_for_argv(argv, fixture_corpus.parent)
+    assert any(line.startswith("refutation_disabled=") for line in rendered.stderr_lines)'''

assert old_test_block in old_diff, "anchor block not found"

new_test_block = '''def test_no_refute_line_comes_from_renderer(fixture_corpus: Path) -> None:
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
+    assert not any(line.startswith("refutation_disabled=") for line in rendered.stderr_lines)'''

new_diff = old_diff.replace(old_test_block, new_test_block)
assert new_diff != old_diff

# The file's total added-line count (+N in the @@ header) grows by the
# number of new '+' lines the companion test adds.
added_lines = new_test_block.count("\n+") + 1 - old_test_block.count("\n+") - 1
lines = new_diff.split("\n")
for i, l in enumerate(lines):
    if l.startswith("@@"):
        rest = l[2:]
        body_start = rest.index("@@", 1)
        hunk_spec = rest[:body_start].strip()
        suffix = rest[body_start:]
        parts = hunk_spec.split()
        old_part, new_part = parts[0], parts[1]
        old_start = old_part.split(",")[0]
        old_count = old_part.split(",")[1]
        new_start = new_part.split(",")[0]
        new_count = int(new_part.split(",")[1])
        new_count += added_lines
        lines[i] = f"@@ {old_start},{old_count} {new_start},{new_count} {suffix}"
        break
new_diff = "\n".join(lines)

requests.append({
    "method": "set-change",
    "params": {
        "id": "CC-M-002-011",
        "version": cc11["version"],
        "milestone": "M-002",
        "diff": new_diff,
    },
    "id": rid,
})
rid += 1

results = batch_dispatch(methods, requests, ctx)
for r in results:
    print(json.dumps(r, indent=2))

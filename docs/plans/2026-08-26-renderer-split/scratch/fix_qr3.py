import json

PATH = r"C:\Users\marcu\AppData\Local\Temp\planner-e70yv3f4\plan.json"
p = json.load(open(PATH, encoding="utf-8"))

ccs = {}
cis = {}
for m in p["milestones"]:
    for cc in m.get("code_changes", []):
        ccs[cc["id"]] = cc
    for ci in m.get("code_intents", []):
        cis[ci["id"]] = ci


def bump(obj):
    obj["version"] = obj.get("version", 1) + 1


# =====================================================================
# qa-002: CC-M-001-002's context must reflect CC-M-001-001 already
# applied - the WriteOutcome dataclass CC-001 inserts sits between
# write_bytes_atomically and print_stats_and_samples, so CC-002 anchors
# on WriteOutcome's tail fields rather than on the pre-CC-001 blank
# lines. Also drops the plan-local "(DL-006)" tag (qa-021).
# =====================================================================
cc = ccs["CC-M-001-002"]
cc["diff"] = (
    "--- a/traktor_nml/rewrite.py\n"
    "+++ b/traktor_nml/rewrite.py\n"
    "@@ -404,17 +404,31 @@ class WriteOutcome:\n"
    "     error: Optional[str]\n"
    "     written_path: Optional[Path]\n"
    "     exit_code: int\n"
    " \n"
    " \n"
    "-def print_stats_and_samples(\n"
    "+def format_stats_and_samples(\n"
    "     stats: dict[str, int], samples: list[tuple[str, str, str, str]] | None, limit: int = 10\n"
    "-) -> None:\n"
    "-    for key, value in stats.items():\n"
    "-        print(f\"{key}={value}\")\n"
    "+) -> list[str]:\n"
    "+    \"\"\"The stats and sample_matches block as lines rather than prints, so\n"
    "+    print_stats_and_samples and reconnect_render.render_rewrite_from_reconnect\n"
    "+    compose the same block into their own output instead of each\n"
    "+    restating its format.\"\"\"\n"
    "+    lines = [f\"{key}={value}\" for key, value in stats.items()]\n"
    "     if samples:\n"
    "-        print(\"sample_matches:\")\n"
    "+        lines.append(\"sample_matches:\")\n"
    "         for label, before, after, matched_by in samples[:limit]:\n"
    "-            print(f\"- {label}\")\n"
    "-            print(f\"  matched_by={matched_by}\")\n"
    "-            print(f\"  before={before}\")\n"
    "-            print(f\"  after={after}\")\n"
    "+            lines.append(f\"- {label}\")\n"
    "+            lines.append(f\"  matched_by={matched_by}\")\n"
    "+            lines.append(f\"  before={before}\")\n"
    "+            lines.append(f\"  after={after}\")\n"
    "+    return lines\n"
    "+\n"
    "+\n"
    "+def print_stats_and_samples(\n"
    "+    stats: dict[str, int], samples: list[tuple[str, str, str, str]] | None, limit: int = 10\n"
    "+) -> None:\n"
    "+    for line in format_stats_and_samples(stats, samples, limit):\n"
    "+        print(line)\n"
)
bump(cc)
print("CC-M-001-002 rewritten")

# =====================================================================
# qa-019: three tests in CC-M-001-005 state rationale but never
# demonstrate the failure they guard against. Add a concrete negative
# case to each, matching the convention the fourth test
# (test_text_patch_error_keeps_the_stats_it_already_collected) and the
# M-002/M-003 tests already follow.
# =====================================================================
cc = ccs["CC-M-001-005"]
old = cc["diff"]

old_collision_test = (
    '+def test_output_collision_carries_no_stats(tmp_path: Path) -> None:\n'
    '+    """A collision refusal is a run that never reached collect_patches or\n'
    '+    mutate_tree at all, so stats being None (rather than an empty dict)\n'
    '+    is the signal there is no stats block to render - proved here by\n'
    '+    checking the field directly rather than trusting the docstring."""\n'
    '+    input_path = tmp_path / "a.nml"\n'
    '+    _write_minimal_nml(input_path)\n'
    '+\n'
    '+    outcome = plan_and_write_nml(input_path, input_path, False, _no_op_collect, _no_op_mutate)\n'
    '+\n'
    '+    assert outcome.stats is None\n'
    '+    assert outcome.exit_code == 2\n'
    '+    assert outcome.error == "output_must_differ_from_input"\n'
)
new_collision_test = (
    '+def test_output_collision_carries_no_stats(tmp_path: Path) -> None:\n'
    '+    """A collision refusal is a run that never reached collect_patches or\n'
    '+    mutate_tree at all, so stats being None (rather than an empty dict)\n'
    '+    is the signal there is no stats block to render. Negative case: a\n'
    '+    run that does reach collect_patches produces a populated dict, not\n'
    '+    None, so the two outcomes are distinguishable by type - proved here\n'
    '+    by running both against the same input and comparing them, rather\n'
    '+    than trusting the docstring that stats is None only for a collision."""\n'
    '+    input_path = tmp_path / "a.nml"\n'
    '+    _write_minimal_nml(input_path)\n'
    '+\n'
    '+    collision = plan_and_write_nml(input_path, input_path, False, _no_op_collect, _no_op_mutate)\n'
    '+    completed = plan_and_write_nml(\n'
    '+        input_path, tmp_path / "out.nml", False, _no_op_collect, _no_op_mutate\n'
    '+    )\n'
    '+\n'
    '+    assert collision.stats is None\n'
    '+    assert collision.exit_code == 2\n'
    '+    assert collision.error == "output_must_differ_from_input"\n'
    '+\n'
    '+    # The negative case: had a collision instead produced {} rather than\n'
    '+    # None, it would be indistinguishable in kind from a completed run\'s\n'
    '+    # stats - this is what actually tells them apart.\n'
    '+    assert completed.stats is not None\n'
    '+    assert type(collision.stats) is not type(completed.stats)\n'
)
assert old_collision_test in old
old = old.replace(old_collision_test, new_collision_test)

old_callback_test = (
    '+def test_callback_exception_reaches_the_caller(tmp_path: Path) -> None:\n'
    '+    """collect_patches/mutate_tree are the caller\'s own callables; a\n'
    '+    plain exception from either must propagate rather than being folded\n'
    '+    into a WriteOutcome, the way an input error is."""\n'
    '+    input_path = tmp_path / "a.nml"\n'
    '+    _write_minimal_nml(input_path)\n'
    '+    output_path = tmp_path / "out.nml"\n'
    '+\n'
    '+    def collect_patches(root):\n'
    '+        raise RuntimeError("boom")\n'
    '+\n'
    '+    with pytest.raises(RuntimeError, match="boom"):\n'
    '+        plan_and_write_nml(input_path, output_path, False, collect_patches, _no_op_mutate)\n'
)
new_callback_test = (
    '+def test_callback_exception_reaches_the_caller(tmp_path: Path) -> None:\n'
    '+    """collect_patches/mutate_tree are the caller\'s own callables; a\n'
    '+    plain exception from either must propagate rather than being folded\n'
    '+    into a WriteOutcome, the way an input error is. Negative case: a\n'
    '+    write-time exception from apply_and_write (text_patch_error) is the\n'
    '+    contrasting behaviour - plan_and_write_nml folds that one into a\n'
    '+    WriteOutcome instead of raising, so the two failure classes are\n'
    '+    proved to be handled differently rather than everything simply\n'
    '+    propagating."""\n'
    '+    input_path = tmp_path / "a.nml"\n'
    '+    _write_minimal_nml(input_path)\n'
    '+    output_path = tmp_path / "out.nml"\n'
    '+\n'
    '+    def collect_patches(root):\n'
    '+        raise RuntimeError("boom")\n'
    '+\n'
    '+    with pytest.raises(RuntimeError, match="boom"):\n'
    '+        plan_and_write_nml(input_path, output_path, False, collect_patches, _no_op_mutate)\n'
    '+\n'
    '+    bogus_patch = ElemPatch(1, "LOCATION", (("VOLUME", "nope"),), [("VOLUME", "nope", "X")])\n'
    '+    folded = plan_and_write_nml(\n'
    '+        input_path, output_path, False, lambda root: ([bogus_patch], {}, []), _no_op_mutate\n'
    '+    )\n'
    '+    assert folded.error is not None and folded.error.startswith("text_patch_error=")\n'
)
assert old_callback_test in old
old = old.replace(old_callback_test, new_callback_test)

old_noop_test = (
    '+def test_no_outcome_writes_to_either_stream(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:\n'
    '+    """plan_and_write_nml is printless for every outcome it can return:\n'
    '+    collision, write success, and write-time text_patch_error alike."""\n'
    '+    input_path = tmp_path / "a.nml"\n'
    '+    _write_minimal_nml(input_path)\n'
    '+\n'
    '+    plan_and_write_nml(input_path, input_path, False, _no_op_collect, _no_op_mutate)\n'
    '+    plan_and_write_nml(input_path, tmp_path / "out1.nml", False, _no_op_collect, _no_op_mutate)\n'
    '+\n'
    '+    bogus_patch = ElemPatch(1, "LOCATION", (("VOLUME", "nope"),), [("VOLUME", "nope", "X")])\n'
    '+    plan_and_write_nml(\n'
    '+        input_path, tmp_path / "out2.nml", False, lambda root: ([bogus_patch], {}, []), _no_op_mutate\n'
    '+    )\n'
    '+\n'
    '+    captured = capsys.readouterr()\n'
    '+    assert captured.out == ""\n'
    '+    assert captured.err == ""\n'
)
new_noop_test = (
    '+def test_no_outcome_writes_to_either_stream(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:\n'
    '+    """plan_and_write_nml is printless for every outcome it can return:\n'
    '+    collision, write success, and write-time text_patch_error alike.\n'
    '+    Negative case: the printing wrapper write_nml_safely, run over the\n'
    '+    same collision input, does write to stderr - proving capsys is\n'
    '+    actually capturing output here rather than the silence above being\n'
    '+    an artifact of a misconfigured test."""\n'
    '+    input_path = tmp_path / "a.nml"\n'
    '+    _write_minimal_nml(input_path)\n'
    '+\n'
    '+    plan_and_write_nml(input_path, input_path, False, _no_op_collect, _no_op_mutate)\n'
    '+    plan_and_write_nml(input_path, tmp_path / "out1.nml", False, _no_op_collect, _no_op_mutate)\n'
    '+\n'
    '+    bogus_patch = ElemPatch(1, "LOCATION", (("VOLUME", "nope"),), [("VOLUME", "nope", "X")])\n'
    '+    plan_and_write_nml(\n'
    '+        input_path, tmp_path / "out2.nml", False, lambda root: ([bogus_patch], {}, []), _no_op_mutate\n'
    '+    )\n'
    '+\n'
    '+    captured = capsys.readouterr()\n'
    '+    assert captured.out == ""\n'
    '+    assert captured.err == ""\n'
    '+\n'
    '+    write_nml_safely(input_path, input_path, False, _no_op_collect, _no_op_mutate)\n'
    '+    assert capsys.readouterr().err != ""\n'
)
assert old_noop_test in old
old = old.replace(old_noop_test, new_noop_test)

old = old.replace(
    "+from traktor_nml.rewrite import plan_and_write_nml\n",
    "+from traktor_nml.rewrite import plan_and_write_nml, write_nml_safely\n",
)
assert "write_nml_safely" in old.split("plan_and_write_nml, write_nml_safely")[0] or True

cc["diff"] = old
bump(cc)
print("CC-M-001-005 rewritten")

json.dump(p, open(PATH, "w", encoding="utf-8"), indent=2)
print("ok - stage 2")

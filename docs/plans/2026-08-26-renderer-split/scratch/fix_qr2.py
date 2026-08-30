import json

PATH = r"C:\Users\marcu\AppData\Local\Temp\planner-e70yv3f4\plan.json"
p = json.load(open(PATH, encoding="utf-8"))

milestones = {m["id"]: m for m in p["milestones"]}
ccs = {}
cis = {}
for m in p["milestones"]:
    for cc in m.get("code_changes", []):
        ccs[cc["id"]] = cc
    for ci in m.get("code_intents", []):
        cis[ci["id"]] = ci


def bump(obj):
    obj["version"] = obj.get("version", 1) + 1


def set_diff(cc_id, new_diff):
    cc = ccs[cc_id]
    cc["diff"] = new_diff
    bump(cc)


def replace_in_diff(cc_id, old, new, count=None):
    cc = ccs[cc_id]
    assert old in cc["diff"], f"{cc_id}: text not found:\n{old!r}"
    if count is None:
        cc["diff"] = cc["diff"].replace(old, new)
    else:
        cc["diff"] = cc["diff"].replace(old, new, count)
    bump(cc)


# =====================================================================
# qa-021: strip bare plan-local "(DL-00N)" citations that leak into
# shipped code comments/docstrings. Package traktor_nml/README.md's own
# decision log already runs DL-001..DL-045, so a bare "(DL-002)" etc.
# left in shipped code does not merely dangle - it silently resolves to
# an unrelated, real package decision. Only the single new package entry
# (DL-046, written by CC-M-003-002) documents this split once it ships;
# per-comment plan-local citations are removed rather than renumbered.
# =====================================================================

replace_in_diff(
    "CC-M-001-001",
    "renderer, a future GUI - can read it as data (DL-002).",
    "renderer, a future GUI - can read it as data.",
)
replace_in_diff(
    "CC-M-001-001",
    "failed to write (DL-003).\n+    \"\"\"",
    "failed to write.\n+    \"\"\"",
)

replace_in_diff(
    "CC-M-001-003",
    "+    \"\"\"Read, parse, patch, and write once, returning a WriteOutcome\n+    rather than printing (DL-002). Resolves output_path against",
    "+    \"\"\"Read, parse, patch, and write once, returning a WriteOutcome\n+    rather than printing. Resolves output_path against",
)

replace_in_diff(
    "CC-M-001-004",
    "+    function made when it owned the sequence directly (DL-002).\n     \"\"\"",
    "+    function made when it owned the sequence directly.\n     \"\"\"",
)

print("qa-021 partial (M-001) done")

json.dump(p, open(PATH, "w", encoding="utf-8"), indent=2)
print("ok - stage 1")

import json

PATH = r"C:\Users\marcu\AppData\Local\Temp\planner-e70yv3f4\plan.json"
p = json.load(open(PATH, encoding="utf-8"))

m002 = next(m for m in p["milestones"] if m["id"] == "M-002")
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
# qa-012 + qa-021 (partial): ReconnectResult must be frozen; drop the
# plan-local DL tags from the module docstring and the class docstring.
# =====================================================================
cc = ccs["CC-M-002-001"]
d = cc["diff"]
d = d.replace(
    "the fact arrives too late for that (DL-001). run_reconnection returns a",
    "the fact arrives too late for that. run_reconnection returns a",
)
d = d.replace(
    "from .commands._shared_args import resolve_confidence, should_refute\n",
    "from .shared_args import resolve_confidence, should_refute\n",
)
d = d.replace(
    "+@dataclass\n+class ReconnectResult:",
    "+@dataclass(frozen=True)\n+class ReconnectResult:",
)
d = d.replace(
    "to stderr mid-pipeline (DL-005). A GUI review table reads this",
    "to stderr mid-pipeline. A GUI review table reads this",
)
assert d != cc["diff"]
cc["diff"] = d
bump(cc)
print("CC-M-002-001 updated (frozen, import path, DL tags)")

ci = cis["CI-M-002-001"]
ci["behavior"] = ci["behavior"].replace(
    "A dataclass carrying everything",
    "A frozen dataclass carrying everything",
)
bump(ci)

# =====================================================================
# qa-021: drop plan-local DL tags from ScanReconnectResult /
# RewriteReconnectResult docstrings (CC-M-002-002, CC-M-002-003).
# =====================================================================
for cid in ("CC-M-002-002", "CC-M-002-003"):
    cc = ccs[cid]
    old = "result, because the CSV is written after run_reconnection returns\n+    (DL-006, DL-008).\"\"\""
    new = "result, because the CSV is written after run_reconnection returns."
    if old in cc["diff"]:
        cc["diff"] = cc["diff"].replace(old, "result, because the CSV is written after run_reconnection returns.\n+    \"\"\"")
        bump(cc)
        continue
    old2 = "outcome all. csv_path is non-None only alongside a non-None\n+    reconnect (DL-006, DL-008).\"\"\""
    if old2 in cc["diff"]:
        cc["diff"] = cc["diff"].replace(old2, "outcome all. csv_path is non-None only alongside a non-None\n+    reconnect.\n+    \"\"\"")
        bump(cc)

print("CC-M-002-002 / CC-M-002-003 DL tags stripped")

json.dump(p, open(PATH, "w", encoding="utf-8"), indent=2)
print("ok - stage 3")

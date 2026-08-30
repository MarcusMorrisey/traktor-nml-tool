import json
import os

state_dir = r"C:\Users\marcu\AppData\Local\Temp\planner-e70yv3f4"
d = json.load(open(os.path.join(state_dir, "plan.json"), encoding="utf-8"))
items = []
i = 1
base = os.path.join(state_dir, "docdiffs")
for m in d["milestones"]:
    for cc in m.get("code_changes", []):
        cf = os.path.join(base, cc["id"] + ".diff")
        items.append({
            "method": "set-doc-diff",
            "params": {"change": cc["id"], "version": cc["version"], "content_file": cf},
            "id": i,
        })
        i += 1

with open(os.path.join(state_dir, "batch_setdocdiff.json"), "w", encoding="utf-8") as f:
    json.dump(items, f)
print(len(items))

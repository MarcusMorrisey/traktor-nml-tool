import sys, json
sys.path.insert(0, r"C:\Users\marcu\.claude\skills\scripts")
from pathlib import Path
from skills.planner.cli import plan_commands
from skills.planner.cli.dispatch import discover_methods, batch as batch_dispatch

STATE_DIR = Path(r"C:\Users\marcu\AppData\Local\Temp\planner-e70yv3f4")
ctx = plan_commands.PlanContext(state_dir=STATE_DIR)
methods = discover_methods(plan_commands)

plan = json.loads((STATE_DIR / "plan.json").read_text(encoding="utf-8"))
by_id = {}
for m in plan["milestones"]:
    for cc in m.get("code_changes", []):
        by_id[cc["id"]] = cc

def fix_header(cid, old_count, new_count):
    diff = by_id[cid]["diff"]
    lines = diff.split("\n")
    for i, l in enumerate(lines):
        if l.startswith("@@"):
            # @@ -OLDSTART,OLDCOUNT +NEWSTART,NEWCOUNT @@ rest
            rest = l[2:]
            body_start = rest.index("@@", 1)
            hunk_spec = rest[:body_start].strip()
            suffix = rest[body_start:]
            parts = hunk_spec.split()
            old_part, new_part = parts[0], parts[1]
            old_start = old_part.split(",")[0]
            new_start = new_part.split(",")[0]
            new_hunk = f"@@ {old_start},{old_count} {new_start},{new_count} {suffix}"
            lines[i] = new_hunk
            break
    else:
        raise ValueError("no @@ line found")
    return "\n".join(lines)

requests = []
rid = 1

fixes = {
    "CC-M-001-001": (6, 25),
    "CC-M-001-002": (17, 28),
    "CC-M-001-003": (7, 56),
    "CC-M-001-004": (48, 24),
}
for cid, (oc, nc) in fixes.items():
    cc = by_id[cid]
    new_diff = fix_header(cid, oc, nc)
    requests.append({
        "method": "set-change",
        "params": {
            "id": cid,
            "version": cc["version"],
            "milestone": "M-001",
            "diff": new_diff,
        },
        "id": rid,
    })
    rid += 1

results = batch_dispatch(methods, requests, ctx)
for r in results:
    print(json.dumps(r, indent=2))

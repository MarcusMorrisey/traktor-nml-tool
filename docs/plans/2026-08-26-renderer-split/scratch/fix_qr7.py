# -*- coding: utf-8 -*-
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


# CC-M-002-007: reconnect_render.py creation - fix the import path
# (qa-007) and strip the plan-local DL tags (qa-021).
cc = ccs["CC-M-002-007"]
cc["diff"] = (
    "--- /dev/null\n"
    "+++ b/traktor_nml/reconnect_render.py\n"
    "@@ -0,0 +1,31 @@\n"
    "+\"\"\"Every character the reconnect commands put on stdout or stderr.\n"
    "+\n"
    "+reconnect_run.py returns typed results rather than printing; this module\n"
    "+turns a result into buffered stdout lines, stderr lines and an exit code,\n"
    "+and emit is the one function that actually writes to a stream.\n"
    "+\"\"\"\n"
    "+\n"
    "+from __future__ import annotations\n"
    "+\n"
    "+import argparse\n"
    "+import sys\n"
    "+from dataclasses import dataclass\n"
    "+\n"
    "+from . import rewrite\n"
    "+from .reconnect_run import RewriteReconnectResult, ScanReconnectResult\n"
    "+from .shared_args import refutation_disabled_line\n"
    "+\n"
    "+\n"
    "+@dataclass\n"
    "+class RenderedOutput:\n"
    "+    \"\"\"Buffered stdout lines, stderr lines and an exit code. emit is the\n"
    "+    one function that writes them to sys.stdout/sys.stderr, so every\n"
    "+    print on the reconnect path lives inside it rather than scattered\n"
    "+    across the pipeline.\"\"\"\n"
    "+\n"
    "+    stdout_lines: list[str]\n"
    "+    stderr_lines: list[str]\n"
    "+    exit_code: int\n"
    "+\n"
    "+\n"
    "+def emit(rendered: RenderedOutput) -> int:\n"
    "+    for line in rendered.stdout_lines:\n"
    "+        print(line)\n"
    "+    for line in rendered.stderr_lines:\n"
    "+        print(line, file=sys.stderr)\n"
    "+    return rendered.exit_code\n"
)
bump(cc)
print("CC-M-002-007 rewritten")

# CC-M-002-009: render_rewrite_from_reconnect - gate the fingerprint and
# refutation warnings on result.reconnect being populated (qa-003), so an
# early failure (output collision, volume_identity_error,
# fingerprint_unavailable) prints neither, matching the pre-split core
# where warn_refutation_disabled ran only after volume-identity
# resolution and the fingerprint check both succeeded.
cc = ccs["CC-M-002-009"]
old = (
    "+    stderr_lines: list[str] = []\n"
    "+    if result.reconnect is not None:\n"
    "+        stderr_lines.extend(result.reconnect.warnings)\n"
    "+    refutation_line = refutation_disabled_line(args)\n"
    "+    if refutation_line is not None:\n"
    "+        stderr_lines.append(refutation_line)\n"
    "+    if outcome is not None and outcome.error is not None:\n"
)
new = (
    "+    stderr_lines: list[str] = []\n"
    "+    if result.reconnect is not None:\n"
    "+        # warn_refutation_disabled in the pre-split core only ran after\n"
    "+        # volume-identity resolution and the fingerprint check both\n"
    "+        # succeeded, i.e. only on a run that reached matching - gating on\n"
    "+        # result.reconnect (populated only once run_reconnection returns)\n"
    "+        # reproduces that: an output collision or a volume_identity_error/\n"
    "+        # fingerprint_unavailable failure prints neither warning.\n"
    "+        stderr_lines.extend(result.reconnect.warnings)\n"
    "+        refutation_line = refutation_disabled_line(args)\n"
    "+        if refutation_line is not None:\n"
    "+            stderr_lines.append(refutation_line)\n"
    "+    if outcome is not None and outcome.error is not None:\n"
)
assert old in cc["diff"]
cc["diff"] = cc["diff"].replace(old, new)
bump(cc)
print("CC-M-002-009 rewritten (refutation gating)")

json.dump(p, open(PATH, "w", encoding="utf-8"), indent=2)
print("ok - stage 6")

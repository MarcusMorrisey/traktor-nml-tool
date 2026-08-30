# -*- coding: utf-8 -*-
import json

PATH = r"C:\Users\marcu\AppData\Local\Temp\planner-e70yv3f4\plan.json"
p = json.load(open(PATH, encoding="utf-8"))

milestones = {m["id"]: m for m in p["milestones"]}
m002 = milestones["M-002"]
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
# qa-007: reconnect_run.py and reconnect_render.py must not import from
# commands/ (DL-007's direction is commands/ -> reconnect_run/render,
# never the reverse). resolve_confidence, should_refute and
# refutation_disabled_line move to a new traktor_nml/shared_args.py that
# sits beside reconnect_run.py; commands/_shared_args.py imports the same
# three names from there so compare_cmd.py and reconnect_cmd.py, which
# already import them from ._shared_args, keep working unchanged.
# =====================================================================

new_intent = {
    "id": "CI-M-002-014",
    "version": 1,
    "file": "traktor_nml/shared_args.py",
    "function": None,
    "behavior": (
        "resolve_confidence, should_refute and refutation_disabled_line, moved out of "
        "commands/_shared_args.py: all three are pure functions of an argparse.Namespace with no "
        "argparse registration or stream dependency of their own, and reconnect_run.py/"
        "reconnect_render.py need them without importing anything from commands/, which "
        "commands/__init__.py auto-imports at CLI startup and which reconnect_run/reconnect_render "
        "must sit below rather than beside (DL-007). commands/_shared_args.py imports the same three "
        "names from here and keeps add_confidence_args, add_no_refute_argument and "
        "warn_refutation_disabled, so every existing importer of the moved names "
        "(compare_cmd.py, reconnect_cmd.py) is unaffected."
    ),
    "decision_refs": ["DL-007", "DL-010"],
}
m002["code_intents"].append(new_intent)

new_change = {
    "id": "CC-M-002-014",
    "version": 1,
    "intent_ref": "CI-M-002-014",
    "file": "traktor_nml/shared_args.py",
    "diff": (
        "--- /dev/null\n"
        "+++ b/traktor_nml/shared_args.py\n"
        "@@ -0,0 +1,42 @@\n"
        "+\"\"\"Confidence and refutation semantics shared below the commands/ layer.\n"
        "+\n"
        "+resolve_confidence, should_refute and refutation_disabled_line are pure\n"
        "+functions of an argparse.Namespace with no argparse registration or\n"
        "+stream dependency of their own. reconnect_run.py and reconnect_render.py\n"
        "+import them from here rather than from commands/_shared_args.py, because\n"
        "+commands/ imports downward into reconnect_run.py and reconnect_render.py\n"
        "+and never the reverse - a core or renderer module importing from\n"
        "+commands/ would create the cycle that direction forbids.\n"
        "+commands/_shared_args.py imports these same three names from here, so\n"
        "+every existing importer of them (compare_cmd.py, reconnect_cmd.py) keeps\n"
        "+working unchanged.\n"
        "+\"\"\"\n"
        "+\n"
        "+from __future__ import annotations\n"
        "+\n"
        "+import argparse\n"
        "+from typing import Optional\n"
        "+\n"
        "+from .confidence import MatchConfidence, parse_match_confidence\n"
        "+\n"
        "+\n"
        "+def resolve_confidence(args: argparse.Namespace) -> MatchConfidence:\n"
        "+    \"\"\"Resolve the effective MatchConfidence: an explicit\n"
        "+    --match-confidence always wins; otherwise --allow-artist-title-only\n"
        "+    selects loose and its absence selects strict (DL-010).\"\"\"\n"
        "+    if getattr(args, \"match_confidence\", None):\n"
        "+        return parse_match_confidence(args.match_confidence)\n"
        "+    return MatchConfidence.from_legacy_flag(args.allow_artist_title_only)\n"
        "+\n"
        "+\n"
        "+def should_refute(args: argparse.Namespace) -> bool:\n"
        "+    \"\"\"Whether the cascade should apply the size/duration check.\n"
        "+\n"
        "+    Pure: safe to call anywhere, any number of times. The warning is a\n"
        "+    separate call precisely so this one carries no call-once contract -\n"
        "+    reading a flag and announcing it are different jobs, and conflating\n"
        "+    them meant a caller with two passes over the same run had to know to\n"
        "+    cache the result or the warning printed twice.\n"
        "+    \"\"\"\n"
        "+    return not getattr(args, \"no_refute\", False)\n"
        "+\n"
        "+\n"
        "+def refutation_disabled_line(args: argparse.Namespace) -> Optional[str]:\n"
        "+    \"\"\"The refutation-disabled message text, or None when refutation is\n"
        "+    still active. warn_refutation_disabled and reconnect_render both read\n"
        "+    this so the literal has one definition: no manifest case sets\n"
        "+    --no-refute for either reconnect command, so a second copy of the\n"
        "+    text would drift invisibly.\n"
        "+    \"\"\"\n"
        "+    if should_refute(args):\n"
        "+        return None\n"
        "+    return (\n"
        "+        \"refutation_disabled=size and duration contradictions will be ignored; \"\n"
        "+        \"a candidate the collection's own FILESIZE/PLAYTIME_FLOAT contradict can now win a match\"\n"
        "+    )\n"
    ),
    "doc_diff": "",
    "comments": "",
}
m002["code_changes"].append(new_change)

if "traktor_nml/shared_args.py" not in m002["files"]:
    m002["files"].append("traktor_nml/shared_args.py")

bump(m002)
print("shared_args.py CI/CC added, milestone files updated")

json.dump(p, open(PATH, "w", encoding="utf-8"), indent=2)
print("ok - stage 5")

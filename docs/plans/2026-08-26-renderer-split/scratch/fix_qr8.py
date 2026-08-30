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


# CC-M-002-013: commands/_shared_args.py now imports resolve_confidence,
# should_refute and refutation_disabled_line from the new
# traktor_nml/shared_args.py rather than defining them itself (qa-007),
# and warn_refutation_disabled calls the imported refutation_disabled_line.
cc = ccs["CC-M-002-013"]
cc["diff"] = (
    "--- a/traktor_nml/commands/_shared_args.py\n"
    "+++ b/traktor_nml/commands/_shared_args.py\n"
    "@@ -11,7 +11,9 @@ from __future__ import annotations\n"
    " import argparse\n"
    " import sys\n"
    " \n"
    " from ..confidence import MatchConfidence, parse_match_confidence\n"
    "+from ..shared_args import refutation_disabled_line, resolve_confidence, should_refute\n"
    " \n"
    " \n"
    " def add_confidence_args(parser: argparse.ArgumentParser) -> None:\n"
    "@@ -28,20 +30,6 @@ def add_confidence_args(parser: argparse.ArgumentParser) -> None:\n"
    "     )\n"
    " \n"
    " \n"
    "-def resolve_confidence(args: argparse.Namespace) -> MatchConfidence:\n"
    "-    \"\"\"Resolve the effective MatchConfidence: an explicit\n"
    "-    --match-confidence always wins; otherwise --allow-artist-title-only\n"
    "-    selects loose and its absence selects strict (DL-010).\"\"\"\n"
    "-    if getattr(args, \"match_confidence\", None):\n"
    "-        return parse_match_confidence(args.match_confidence)\n"
    "-    return MatchConfidence.from_legacy_flag(args.allow_artist_title_only)\n"
    "-\n"
    "-\n"
    " def add_no_refute_argument(parser: argparse.ArgumentParser) -> None:\n"
    "     parser.add_argument(\n"
    "         \"--no-refute\",\n"
    "@@ -52,26 +40,12 @@ def add_no_refute_argument(parser: argparse.ArgumentParser) -> None:\n"
    "     )\n"
    " \n"
    " \n"
    "-def should_refute(args: argparse.Namespace) -> bool:\n"
    "-    \"\"\"Whether the cascade should apply the size/duration check.\n"
    "-\n"
    "-    Pure: safe to call anywhere, any number of times. The warning is a\n"
    "-    separate call precisely so this one carries no call-once contract -\n"
    "-    reading a flag and announcing it are different jobs, and conflating\n"
    "-    them meant a caller with two passes over the same run had to know to\n"
    "-    cache the result or the warning printed twice.\n"
    "-    \"\"\"\n"
    "-    return not getattr(args, \"no_refute\", False)\n"
    "-\n"
    "-\n"
    " def warn_refutation_disabled(args: argparse.Namespace) -> None:\n"
    "     \"\"\"Announce --no-refute once per run, if it is set.\n"
    " \n"
    "     A run that ignores size and duration contradictions can commit a\n"
    "     rewrite onto a file the collection's own numbers say is the wrong one,\n"
    "     so the switch says so on every run rather than only in --help.\n"
    "     \"\"\"\n"
    "-    if not should_refute(args):\n"
    "-        print(\n"
    "-            \"refutation_disabled=size and duration contradictions will be ignored; \"\n"
    "-            \"a candidate the collection's own FILESIZE/PLAYTIME_FLOAT contradict can now win a match\",\n"
    "-            file=sys.stderr,\n"
    "-        )\n"
    "+    line = refutation_disabled_line(args)\n"
    "+    if line is not None:\n"
    "+        print(line, file=sys.stderr)\n"
)
bump(cc)
print("CC-M-002-013 rewritten (delegates to shared_args)")

# CI-M-002-013 behavior text: reflect the relocation.
ci = cis["CI-M-002-013"]
ci["file"] = "traktor_nml/commands/_shared_args.py"
ci["behavior"] = (
    "warn_refutation_disabled keeps its signature, its docstring contract and its stderr side effect, "
    "but now delegates to shared_args.refutation_disabled_line (CI-M-002-014) for the message text, so "
    "its byte output for compare_cmd's three call sites and every other existing caller is unchanged. "
    "resolve_confidence, should_refute and refutation_disabled_line themselves move to "
    "traktor_nml/shared_args.py and are imported back into this module, which keeps compare_cmd.py and "
    "reconnect_cmd.py's own `from ._shared_args import resolve_confidence, should_refute` (and, for "
    "reconnect_cmd.py, warn_refutation_disabled) working unchanged. reconnect_render calls "
    "shared_args.refutation_disabled_line directly and appends the returned string to its buffered stderr "
    "lines rather than restating the literal; warn_refutation_disabled is never called on the reconnect "
    "path. shared_args.py is the single source of the message text: no manifest case sets --no-refute for "
    "either reconnect command, so a second copy of the literal would drift invisibly (DL-010)."
)
bump(ci)
print("CI-M-002-013 behavior updated")

json.dump(p, open(PATH, "w", encoding="utf-8"), indent=2)
print("ok - stage 7")

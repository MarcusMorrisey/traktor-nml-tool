import json

PATH = r"C:\Users\marcu\AppData\Local\Temp\planner-e70yv3f4\plan.json"
p = json.load(open(PATH, encoding="utf-8"))

PKG = ("the package's own DL-019 in traktor_nml/README.md (splice_cmd/split_cmd read, parse and "
       "write through rewrite.py's helpers so both inherit its diagnostics and atomic write)")

# --- qa-001a: DL-002 reasoning ---
dl = {x["id"]: x for x in p["planning_context"]["decisions"]}
d2 = dl["DL-002"]
old = "duplicate the read/parse/patch/write skeleton DL-001 exists to prevent"
assert old in d2["reasoning"]
d2["reasoning"] = d2["reasoning"].replace(
    old,
    "duplicate the read/parse/patch/write skeleton " + PKG + " exists to prevent - a package-log "
    "number, not this plan's DL-001, which is the printless-core/renderer decision",
)
d2["version"] = d2.get("version", 1) + 1

# --- disambiguate the one legitimately plan-local citation ---
d9 = dl["DL-009"]
old9 = "which is exactly what DL-001 exists to prevent"
assert old9 in d9["reasoning"]
d9["reasoning"] = d9["reasoning"].replace(
    old9, "which is exactly what DL-001 of this plan exists to prevent"
)
d9["version"] = d9.get("version", 1) + 1

# --- qa-001b: RA-002 ---
ra = {x["id"]: x for x in p["planning_context"]["rejected_alternatives"]}
r2 = ra["RA-002"]
oldr = "it duplicates the skeleton write_nml_safely exists to prevent (DL-001)"
assert oldr in r2["rejection_reason"]
r2["rejection_reason"] = r2["rejection_reason"].replace(
    oldr,
    "it duplicates the skeleton write_nml_safely exists to prevent (" + PKG +
    "; not this plan's DL-001)",
)

# --- same collision in the tradeoff text ---
t = p["invisible_knowledge"]["tradeoffs"]
oldt = "duplicating the read/parse/patch/write skeleton DL-001 exists to prevent"
assert oldt in t[0]
t[0] = t[0].replace(
    oldt,
    "duplicating the read/parse/patch/write skeleton " + PKG + " exists to prevent (a package-log "
    "number; this plan's own DL-001 is the printless-core/renderer decision)",
)

# --- the namespace rule itself, so it survives into implementation ---
p["invisible_knowledge"]["invariants"].append(
    "Two DL namespaces are in play and they never share a number. DL-001..DL-010 in this plan are "
    "plan-local decisions; traktor_nml/README.md's package decision log runs DL-001..DL-045 and is a "
    "separate sequence, where DL-001 is the argv-forwarding cli.py shim and DL-019 is the rule that "
    "commands read, parse and write through rewrite.py's shared helpers rather than carrying their own "
    "write path. Every reference in this plan to the package log is written as \"the package's own "
    "DL-NNN\" with traktor_nml/README.md named; a bare DL-NNN in this plan always means a plan-local "
    "decision. The single number this plan contributes to the package sequence is the new entry M-003 "
    "writes (DL-046 at planning time, re-read at HEAD), and that entry - because it lives inside the "
    "package log - cites package numbers bare and cites no plan-local number at all. Precedent: "
    "docs/2026-08-24-build-playlist-plan.md, which flags every package entry it cites as \"in the "
    "package's own log\"."
)

# --- qa-001c: the text committed into the package decision log ---
for m in p["milestones"]:
    for ci in m.get("code_intents", []):
        if ci["id"] == "CI-M-003-002":
            oldc = "would duplicate the skeleton DL-001 exists to prevent."
            assert oldc in ci["behavior"], ci["behavior"]
            ci["behavior"] = ci["behavior"].replace(
                oldc,
                "would duplicate the read/parse/patch/write skeleton DL-019 exists to prevent. The "
                "entry is written in the package log's own namespace, so DL-019 there is the package "
                "entry for rewrite.py's shared read/parse/atomic-write helpers, not this plan's DL-001 "
                "(the printless-core decision); the entry cites package numbers bare and cites no "
                "plan-local DL number, and the DL-019 antecedent is confirmed by re-reading "
                "traktor_nml/README.md at HEAD alongside the free-number check below.",
            )
            ci["version"] = ci.get("version", 1) + 1
    if m["id"] == "M-003":
        m["acceptance_criteria"].append(
            "the committed decision-log entry cites only package-log DL numbers - the shared "
            "read/parse/patch/write skeleton is DL-019, not DL-001, which in that log is the "
            "argv-forwarding cli.py shim - and cites no plan-local DL number, checked by reading the "
            "cited entries back out of traktor_nml/README.md at HEAD before the commit"
        )
        m["version"] = m.get("version", 1) + 1

json.dump(p, open(PATH, "w", encoding="utf-8"), indent=2)
print("ok")

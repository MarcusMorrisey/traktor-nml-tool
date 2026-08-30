import json

PATH = r"C:\Users\marcu\AppData\Local\Temp\planner-e70yv3f4\plan.json"
p = json.load(open(PATH, encoding="utf-8"))

# qa-005: rollback is an ordered revert, not per-milestone independence
cons = p["planning_context"]["constraints"]
old = "The CLI is fully usable at every commit on the refactor branch, and each milestone is revertable on its own so the rollback story stays 'revert the renderer split'."
new = (
    "The CLI is fully usable at every commit on the refactor branch. Rollback is an ordered revert - "
    "M-003, then M-002, then M-001 - not a per-milestone one: M-002's rewrite_from_reconnect calls "
    "plan_and_write_nml, which M-001 introduces, so M-001 cannot be reverted while M-002 stands. "
    "Reverted in that order the whole change is still the single discrete 'revert the renderer split' "
    "step section 5 asks for."
)
assert old in cons, cons
cons[cons.index(old)] = new

# qa-009: carry the suite baseline count into the plan
inv = p["invisible_knowledge"]["invariants"]
inv.append(
    "The full-suite baseline is 191 passed and 3 skipped, the 3 skips being the fingerprint tier "
    "(pyacoustid and fpcalc absent). Every acceptance criterion that says 'pytest passes' means that "
    "count: a test that silently disappears or newly skips fails the criterion as surely as a red test, "
    "so the counts are read off the pytest summary line, not just the exit code."
)

risks = {r["id"]: r for r in p["planning_context"]["risks"]}

# qa-013: name the stubbed symbol and keep the raise path distinct
risks["R-003"]["mitigation"] = (
    "The equivalence module monkeypatches traktor_nml.reconnect_run.fingerprint_unavailable_reason to "
    "return a fixed reason, so the warn path is exercised without pyacoustid, fpcalc or chromaprint, "
    "asserting the reason reaches ReconnectResult.warnings and renders ahead of the refutation line. "
    "That stub replaces only the probe; the separate fingerprint_key_provider-is-None path, which raises "
    "_FingerprintUnavailable rather than warning, is left as the defensive import bound it and gets its "
    "own test that sets traktor_nml.reconnect_run.fingerprint_key_provider to None and asserts the raise. "
    "The two failure modes are therefore proved distinct rather than one masking the other. The documented "
    "manifest gap for the fingerprint tier stays open and is not closed by this work."
)

# qa-003: mitigation must be reachable given the core signature
risks["R-005"]["mitigation"] = (
    "Accepted, and the live-feedback channel is reachable from the core: run_reconnection and both cores "
    "take on_progress and cancel and forward them to index_scan_roots (DL-009, CI-M-002-002), so a caller "
    "that wants progress while the scan runs has one that does not depend on print ordering. The manifest "
    "captures stdout and stderr as separate completed streams so parity is unaffected, and the CLI passes "
    "neither argument, keeping today's behaviour exactly."
)

json.dump(p, open(PATH, "w", encoding="utf-8"), indent=2)
print("ok")

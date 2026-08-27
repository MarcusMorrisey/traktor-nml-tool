"""Guards §1 of docs/nicegui-gui-analysis.md (command classification): the
tier classification is total and disjoint over the real `subparsers.choices`,
and the Tier 2 generated-form side-effect allowlist is closed over every
Tier 2 eligible command's `Path`-typed arguments.

§1's own prose is internally inconsistent about what "exactly one tier list"
means: the classification paragraph says every subcommand "appears in
exactly one tier list", but §1 also says `scan-reconnect-candidates`
"appears in both tiers by design: it is Tier 2 eligible and gets a
generated form for free, and is also the first step of the Tier 1 wizard."
Taken literally, "exactly one" and "both tiers" cannot both be true of the
same name. This module resolves that by treating **primary tier
assignment** and **Tier 2 eligibility** as two separate predicates:

- `PRIMARY_TIER` is a total, disjoint partition of the 14 real subcommands
  into tiers 1/2/3, using §1's tier tables read literally (Tier 2's table
  lists `inspect`, `encode-dir`, `preview-compare`, `scan-compare-candidates`
  - not `scan-reconnect-candidates`, which §1's Tier 1 table already
  places in Phase 1). This is the partition the "total and disjoint" claim
  is actually true of.
- `TIER2_ELIGIBLE` is a separate, non-partitioning set of commands the form
  generator may build a generated form for. It is `PRIMARY_TIER`'s tier-2
  members plus `scan-reconnect-candidates`, which is how §1's parenthetical
  is encoded: eligible-for-a-form is orthogonal to which hand-built surface
  (if any) also owns the command.

Both properties are checked against the real parser from
`traktor_nml/cli.py:build_parser()`, per §1's own statement that
`subparsers.choices` is "the definitive subcommand set", and each has a
standing negative control that mutates a synthetic parser/classification
and asserts the checker actually reports a violation - see
tests/test_gui_import_isolation.py and tests/test_command_layer_printless.py
for the repo's established idiom for this ("a guard you have only seen
pass is not a guard").

The tier lists and the side-effect allowlist are kept in this test module
rather than in a new production module. `docs/nicegui-gui-analysis.md` §5
step 4 introduces `traktor_nml/gui/` and a Tier 2 form generator; when that
lands, the generator MUST import `TIER2_ELIGIBLE` and
`ALLOWED_SIDE_EFFECT_DESTS` from this module (or a module both sides
import) rather than re-declaring its own copy, for the same reason
`traktor_nml/README.md`'s DL-055 gives for the refutation-disabled message
having one definition: a second copy of the allowlist would drift from
this one without any oracle noticing.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from traktor_nml.cli import build_parser

# --- §1's tier tables, read literally -------------------------------------
#
# Tier 1 (first-class GUI workflows, Phases 1-3):
TIER1 = frozenset({
    "scan-reconnect-candidates",
    "rewrite-from-reconnect",
    "preview-diff",
    "rewrite",
    "build-playlist",
    "discover-tracks",
    "discover-collection-tracks",
})

# Tier 2 (generated forms), as enumerated in §1's own sentence naming the
# tier's members - this list, unlike TIER2_ELIGIBLE below, does not repeat
# scan-reconnect-candidates, which §1's Tier 1 table already claims.
TIER2 = frozenset({
    "inspect",
    "encode-dir",
    "preview-compare",
    "scan-compare-candidates",
})

# Tier 3 (CLI only, out of scope for the GUI):
TIER3 = frozenset({
    "splice",
    "split",
    "rewrite-from-collection-compare",
})

# TIER2_ELIGIBLE: the mechanical predicate §1 states as "a command is Tier 2
# eligible if and only if its handler writes no .nml output", encoded here
# as the closed set of commands the generated-form machinery may build a
# form for. This is TIER2 plus scan-reconnect-candidates, which is exactly
# §1's parenthetical: eligible for a generated form AND the first step of
# the Tier 1 wizard.
TIER2_ELIGIBLE = TIER2 | {"scan-reconnect-candidates"}

# --- §1's side-effect allowlist table --------------------------------------
#
# The only two argparse `dest` names a Tier 2 eligible command's parser may
# attach to a `Path`-typed, file-producing optional argument: CSV report
# (--csv, off by default) and tag cache (--cache, on, disclosed). Any other
# Path-typed optional argument on a Tier 2 eligible command fails the guard
# below.
ALLOWED_SIDE_EFFECT_DESTS = frozenset({"csv", "cache"})

# The remaining Path-typed arguments each Tier 2 eligible command's real
# parser carries today, read from traktor_nml/commands/*.py's register()
# calls: positional or --scan-root-style paths the command only reads
# (collections, scan roots). Enumerated per command, not inferred from
# "positional vs optional", because scan-reconnect-candidates' scan roots
# are an optional flag (--scan-root, repeatable) that is nonetheless an
# input, not a side effect.
TIER2_PATH_INPUT_DESTS: dict[str, frozenset[str]] = {
    "inspect": frozenset({"input"}),
    "encode-dir": frozenset(),
    "preview-compare": frozenset({"old_input", "new_input"}),
    "scan-compare-candidates": frozenset({"target_input", "candidates_dir"}),
    "scan-reconnect-candidates": frozenset({"old_input", "scan_roots"}),
}


def _real_subparsers() -> dict[str, argparse.ArgumentParser]:
    """The real subparser objects keyed by subcommand name, from the
    production build_parser() - not a hand-copied list."""
    parser, _handlers = build_parser()
    action = next(a for a in parser._subparsers._group_actions if hasattr(a, "choices"))
    return dict(action.choices)


def _real_subcommand_choices() -> frozenset[str]:
    """§1 calls `subparsers.choices` "the definitive subcommand set"."""
    return frozenset(_real_subparsers())


# --- Property 1: total and disjoint ----------------------------------------


def _total_and_disjoint_violations(
    choices: frozenset[str], tier1: frozenset[str], tier2: frozenset[str], tier3: frozenset[str]
) -> dict[str, object]:
    """Checks the classification §1 requires: every name in `choices`
    appears in exactly one of tier1/tier2/tier3. Returns a dict of
    violation categories, empty when the classification is total and
    disjoint. Total and disjoint are checked separately, so a totality
    break and a disjointness break are both individually visible rather
    than collapsed into one boolean."""
    union = tier1 | tier2 | tier3
    violations: dict[str, object] = {}
    unclassified = choices - union
    if unclassified:
        violations["unclassified"] = unclassified
    stale = union - choices
    if stale:
        violations["stale_tier_entries"] = stale
    overlap_12 = tier1 & tier2
    overlap_13 = tier1 & tier3
    overlap_23 = tier2 & tier3
    if overlap_12:
        violations["tier1_tier2_overlap"] = overlap_12
    if overlap_13:
        violations["tier1_tier3_overlap"] = overlap_13
    if overlap_23:
        violations["tier2_tier3_overlap"] = overlap_23
    return violations


def test_real_subcommand_set_is_totally_and_disjointly_classified() -> None:
    """The real 14 subcommands from build_parser(), unmutated, classify
    cleanly against TIER1/TIER2/TIER3 - the baseline the negative controls
    below are checked against."""
    choices = _real_subcommand_choices()
    assert choices == {
        "inspect", "encode-dir", "preview-compare", "scan-compare-candidates",
        "scan-reconnect-candidates", "rewrite-from-reconnect", "preview-diff", "rewrite",
        "build-playlist", "discover-tracks", "discover-collection-tracks",
        "splice", "split", "rewrite-from-collection-compare",
    }
    violations = _total_and_disjoint_violations(choices, TIER1, TIER2, TIER3)
    assert violations == {}


def test_unclassified_subcommand_is_caught() -> None:
    """Negative control for totality: adds a synthetic subcommand name to
    the real choices set without adding it to any tier set, and asserts
    the checker reports it.

    Run against the real, unmutated tier sets with this one synthetic
    addition to `choices`, `_total_and_disjoint_violations` reports
    `{'unclassified': {'discover-new-thing'}}` - reproducing exactly the
    failure §1 warns about: "adding a subcommand without classifying it
    fails CI rather than silently defaulting into the GUI."
    """
    choices = _real_subcommand_choices() | {"discover-new-thing"}
    violations = _total_and_disjoint_violations(choices, TIER1, TIER2, TIER3)
    assert violations.get("unclassified") == {"discover-new-thing"}


def test_removed_subcommand_leaves_a_stale_tier_entry() -> None:
    """Negative control for totality's other direction: a tier set names a
    subcommand no longer produced by build_parser() (e.g. renamed or
    removed), and the checker reports the mismatch rather than silently
    treating the stale name as still classified."""
    choices = _real_subcommand_choices() - {"encode-dir"}
    violations = _total_and_disjoint_violations(choices, TIER1, TIER2, TIER3)
    assert violations.get("stale_tier_entries") == {"encode-dir"}


def test_overlapping_tier_assignment_is_caught() -> None:
    """Negative control for disjointness: constructs a synthetic TIER3
    that (wrongly) also claims a real TIER1 member, and asserts the
    checker reports the overlap.

    Observed to fail when the overlap computation was changed from
    `tier1 & tier3` (intersection) to `tier1 | tier3` (union): run against
    this fixture (mutated_tier3, real choices), the buggy union version
    returns `tier1_tier3_overlap` equal to the 10-member union of TIER1
    and mutated_tier3 (`{'discover-collection-tracks', 'build-playlist',
    'preview-diff', 'split', 'rewrite', 'rewrite-from-collection-compare',
    'scan-reconnect-candidates', 'rewrite-from-reconnect',
    'discover-tracks', 'splice'}`) rather than `{'rewrite'}`, so this
    test's `== {"rewrite"}` assertion fails against it - confirming the
    test is actually checking the shared member, not merely that the key
    is present."""
    mutated_tier3 = TIER3 | {"rewrite"}  # "rewrite" is a real TIER1 member
    violations = _total_and_disjoint_violations(_real_subcommand_choices(), TIER1, TIER2, mutated_tier3)
    assert violations.get("tier1_tier3_overlap") == {"rewrite"}


def test_scan_reconnect_candidates_is_the_one_documented_two_tier_exception() -> None:
    """Encodes §1's parenthetical directly: scan-reconnect-candidates is
    the one name that is Tier 2 eligible while also holding a Tier 1
    primary-tier slot, and it is the *only* such name - every other Tier 2
    eligible command has no Tier 1 slot at all."""
    assert "scan-reconnect-candidates" in TIER1
    assert "scan-reconnect-candidates" in TIER2_ELIGIBLE
    assert TIER2_ELIGIBLE - TIER2 == {"scan-reconnect-candidates"}
    other_eligible = TIER2_ELIGIBLE - {"scan-reconnect-candidates"}
    assert other_eligible.isdisjoint(TIER1)
    assert other_eligible.isdisjoint(TIER3)


# --- Property 2: the side-effect allowlist is closed ------------------------


def _path_typed_actions(parser: argparse.ArgumentParser) -> list[argparse.Action]:
    return [action for action in parser._actions if action.type is Path]


def _allowlist_violations(parser: argparse.ArgumentParser, command: str, input_dests: frozenset[str]) -> list[str]:
    """Every Path-typed argument on `parser` must be an input (its dest is
    in `input_dests`) or on the closed side-effect allowlist
    (ALLOWED_SIDE_EFFECT_DESTS). Anything else - a new file-producing
    argument the classification tables don't know about - is reported."""
    violations = []
    for action in _path_typed_actions(parser):
        if action.dest in input_dests or action.dest in ALLOWED_SIDE_EFFECT_DESTS:
            continue
        violations.append(f"{command}: unlisted Path argument {action.dest!r} ({action.option_strings or 'positional'})")
    return violations


def test_tier2_eligible_commands_carry_no_unlisted_path_argument() -> None:
    """The real parsers for all five Tier 2 eligible commands, unmutated,
    report no allowlist violations - the baseline the negative control
    below is checked against."""
    subparsers = _real_subparsers()
    violations: list[str] = []
    for command in TIER2_ELIGIBLE:
        violations.extend(_allowlist_violations(subparsers[command], command, TIER2_PATH_INPUT_DESTS[command]))
    assert violations == []


def test_new_unlisted_path_argument_on_a_tier2_eligible_command_is_caught() -> None:
    """Negative control for the allowlist: builds a synthetic parser
    shaped like a Tier 2 eligible command (an input plus the real --csv
    allowlisted export) and adds one more Path-typed optional argument,
    `--report-dir`, that is on neither the input list nor the allowlist -
    reproducing §1's stated failure mode, "An argument that produces a
    file and is not listed fails the classification test in §1 rather
    than silently appearing as a text box."

    Observed to fail (violations == []) when `--report-dir` was left off
    the mutation and only the allowlisted `--csv` argument was present:
    re-run without the `--report-dir` line, `_allowlist_violations`
    returned `[]`, confirming the checker only flags the newly added,
    genuinely unlisted argument rather than every Path argument on the
    parser.
    """
    probe = argparse.ArgumentParser()
    probe.add_argument("input", type=Path)
    probe.add_argument("--csv", type=Path)
    probe.add_argument("--report-dir", type=Path)

    violated = _allowlist_violations(probe, "probe-tier2-cmd", frozenset({"input"}))
    assert violated == ["probe-tier2-cmd: unlisted Path argument 'report_dir' (['--report-dir'])"]

    without_the_new_argument = argparse.ArgumentParser()
    without_the_new_argument.add_argument("input", type=Path)
    without_the_new_argument.add_argument("--csv", type=Path)
    assert _allowlist_violations(without_the_new_argument, "probe-tier2-cmd", frozenset({"input"})) == []


def test_checker_accepts_scan_roots_as_an_input_despite_being_an_optional_flag() -> None:
    """scan-reconnect-candidates' --scan-root is an optional (flag-form)
    Path argument that is nonetheless an input, not a side effect -
    confirms the allowlist checker does not use "positional vs optional"
    as its input/output signal (it would wrongly flag --scan-root if it
    did), matching the real parser's shape checked in the baseline test
    above."""
    subparsers = _real_subparsers()
    scan_roots_action = next(
        a for a in subparsers["scan-reconnect-candidates"]._actions if a.dest == "scan_roots"
    )
    assert scan_roots_action.option_strings == ["--scan-root"]
    assert scan_roots_action.type is Path
    violated = _allowlist_violations(
        subparsers["scan-reconnect-candidates"], "scan-reconnect-candidates", TIER2_PATH_INPUT_DESTS["scan-reconnect-candidates"]
    )
    assert violated == []


# --- Mechanical eligibility rule (partial, documented proxy) ---------------


def test_no_tier2_eligible_command_declares_an_output_argument() -> None:
    """Partial encoding of §1's mechanical rule, "a command is Tier 2
    eligible if and only if its handler writes no .nml output": every
    .nml-writing command in this codebase receives its destination
    through an argument whose argparse `dest` is literally `output`
    (confirmed for build-playlist, rewrite, rewrite-from-reconnect,
    rewrite-from-collection-compare and splice), so the absence of a
    `dest == "output"` Path argument is a necessary condition for
    eligibility that this test checks directly against the real parsers.

    This is a proxy, not a full re-derivation of the rule: it is
    one-directional, since `discover-tracks` and `discover-collection-tracks`
    both have a `dest == "output"` Path argument that writes a CSV report,
    not an .nml file, and both are Tier 1 (not Tier 2 eligible) regardless.
    Likewise `split`'s multi-output `--group` argument carries no `dest ==
    "output"` at all (its outputs are `nargs=2` string pairs, not a single
    Path), so the proxy could not have flagged it either. This test does
    not claim to detect every way a future command could write an .nml
    file; it only confirms the naming convention holds for the commands
    §1 currently lists as Tier 2 eligible.
    """
    subparsers = _real_subparsers()
    for command in TIER2_ELIGIBLE:
        output_dests = [a.dest for a in _path_typed_actions(subparsers[command]) if a.dest == "output"]
        assert output_dests == [], f"{command} declares an 'output' Path argument"


def test_output_dest_naming_convention_holds_for_every_nml_writing_command() -> None:
    """Supporting evidence for the proxy above: every command this repo's
    own §1 table assigns to Tier 1 or Tier 3 *because* it writes an .nml
    file names that destination `output`, except `split` (multi-output,
    no single `output` Path arg at all) - recorded here so a future
    change to that naming convention is visible as a failing assertion
    rather than silently invalidating the proxy test above."""
    subparsers = _real_subparsers()
    nml_writers_named_output = {
        "build-playlist", "rewrite", "rewrite-from-reconnect",
        "rewrite-from-collection-compare", "splice",
    }
    for command in nml_writers_named_output:
        output_dests = [a.dest for a in _path_typed_actions(subparsers[command]) if a.dest == "output"]
        assert output_dests == ["output"], f"{command} does not name its .nml destination 'output'"

    split_output_dests = [a.dest for a in _path_typed_actions(subparsers["split"]) if a.dest == "output"]
    assert split_output_dests == []

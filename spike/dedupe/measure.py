"""M-001 spike: measure the reference inventory and AUDIO_ID stability
on a real library before the dedupe core depends on either.

Reads one real collection NML, a copy Traktor re-analysed, and a folder of
byte-identical and format-converted copies of tracks in it, and writes one
Markdown artifact. Writes no NML (plan.md "M-001 spike specification").

Kept outside the package on purpose: its thresholds decide whether tier 3
is admitted (DL-315), so the numbers are recorded once in the artifact and
the package reads the verdict, never re-measures it.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from traktor_nml.matching import _duration_seconds, _fold
from traktor_nml.model import EntryRecord, collection_records, parse_location_element
from traktor_nml.rewrite import path_collides, read_and_parse_source
from traktor_nml.volumes import local_path_for_location, parse_volume_map

# Promotion thresholds for tier 3 on AUDIO_ID (plan.md, DL-315).
REANALYSIS_MIN = 0.99
COPY_MIN = 0.99
FORMAT_MIN = 0.95
AUDIO_EXTENSIONS = frozenset({".mp3", ".flac", ".wav", ".aif", ".aiff", ".m4a", ".ogg"})


@dataclass(frozen=True)
class Rates:
    """The measured AUDIO_ID stability shares and the false-collision count one
    spike run produces; the artifact records them and tier 3 admission reads
    them (DL-315)."""

    audio_id_presence: float
    reanalysis: float
    copy: float
    format: float
    false_collisions: int

    def tier3_admitted(self) -> bool:
        """True only when reanalysis and copy stability both reach their
        minimums and no two different recordings share an AUDIO_ID (DL-315)."""
        return self.reanalysis >= REANALYSIS_MIN and self.copy >= COPY_MIN and self.false_collisions == 0

    def covers_format_upgrades(self) -> bool:
        """True when tier 3 is admitted and AUDIO_ID also survives format
        conversion, so a format upgrade may be grouped by AUDIO_ID alone."""
        return self.tier3_admitted() and self.format >= FORMAT_MIN


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _share(hits: int, total: int) -> float:
    return hits / total if total else 0.0


def reference_inventory(root) -> Counter:
    """Every element/attribute shape outside COLLECTION holding a value
    equal to some entry's primary key, with counts: the table G0 records.

    Shapes are labelled SECTION/TAG@ATTR[TYPE], the form the dedupe
    core's generic dangling scan will name, and a non-collection LOCATION
    composing to a primary key is labelled with @VOLUME+DIR+FILE. This
    runs before traktor_nml/dedupe.py exists, so it carries its own scan."""
    keys = {record.primary_key for record in collection_records(root)}
    shapes: Counter = Counter()
    sections = (s for s in root if isinstance(s.tag, str) and s.tag != "COLLECTION")
    for section in sections:
        for element in (e for e in section.iter() if isinstance(e.tag, str)):
            shapes.update(_element_shapes(section.tag, element, keys))
    return shapes


def _element_shapes(section_tag: str, element, keys: set[str]) -> list[str]:
    """The inventory labels one element outside COLLECTION contributes: its
    composed LOCATION when that names an entry, otherwise each attribute
    whose value is an entry's primary key."""
    kind = element.attrib.get("TYPE", "")
    if element.tag == "LOCATION":
        composed = parse_location_element(element).primary_key
        return [f"{section_tag}/LOCATION@VOLUME+DIR+FILE[{kind}]"] if composed in keys else []
    return [f"{section_tag}/{element.tag}@{attr}[{kind}]" for attr, value in element.attrib.items() if value in keys]


def reanalysis_stability(original: list[EntryRecord], reanalysed: list[EntryRecord]) -> tuple[float, int]:
    """Share of entries present in both files, carrying an AUDIO_ID in
    both, whose AUDIO_ID is unchanged."""
    after = {r.primary_key: r.audio_id for r in reanalysed}
    pairs = [(r.audio_id, after[r.primary_key]) for r in original if r.primary_key in after and r.audio_id]
    pairs = [(a, b) for a, b in pairs if b]
    return _share(sum(1 for a, b in pairs if a == b), len(pairs)), len(pairs)


def false_collisions(records: list[EntryRecord]) -> int:
    """Pairs sharing an AUDIO_ID whose artist, title or duration disagree."""
    by_id: dict[str, list[EntryRecord]] = {}
    for record in records:
        if record.audio_id:
            by_id.setdefault(record.audio_id, []).append(record)
    collisions = 0
    for group in by_id.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                seconds_a, seconds_b = _duration_seconds(a), _duration_seconds(b)
                same_tags = (_fold(a.artist), _fold(a.title)) == (_fold(b.artist), _fold(b.title))
                same_length = seconds_a is not None and seconds_b is not None and abs(seconds_a - seconds_b) <= 1.0
                collisions += 0 if same_tags and same_length else 1
    return collisions


def copy_agreement(records: list[EntryRecord], copies_root: Path, known_mounts) -> tuple[float, float, int, int]:
    """Pair each collection entry whose file resolves under copies_root
    (the copy) with the entry resolving outside it that shares its stem
    (the original); a byte-identical copy and a format-converted copy each
    agree when both entries carry one AUDIO_ID. Pairing by resolved path
    keeps a copy from being matched to itself, since an imported copy
    shares its original's stem and often its file name.
    Returns (copy rate, format rate, copy count, format count)."""
    root = copies_root.resolve()
    originals: dict[str, EntryRecord] = {}
    copies: list[tuple[Path, EntryRecord]] = []
    for record in records:
        path = local_path_for_location(record.location, known_mounts)
        if path is None:
            continue
        if path.resolve().is_relative_to(root):
            copies.append((path, record))
        else:
            originals.setdefault(path.stem.casefold(), record)
    copy_hits = copy_total = format_hits = format_total = 0
    for path, copy_entry in sorted(copies, key=lambda item: str(item[0])):
        original = originals.get(path.stem.casefold())
        if original is None or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        agree = bool(original.audio_id) and original.audio_id == copy_entry.audio_id
        if path.suffix.lower() == Path(original.location.file_name).suffix.lower():
            copy_total, copy_hits = copy_total + 1, copy_hits + agree
        else:
            format_total, format_hits = format_total + 1, format_hits + agree
    return _share(copy_hits, copy_total), _share(format_hits, format_total), copy_total, format_total


def dependency_state() -> dict[str, str]:
    """Whether the optional fingerprint dependencies are installed, recorded in
    the artifact so a tier 3 fingerprint result is read against the machine
    that produced it."""
    return {
        "mutagen": "present" if importlib.util.find_spec("mutagen") else "absent",
        "pyacoustid": "present" if importlib.util.find_spec("acoustid") else "absent",
        "fpcalc": shutil.which("fpcalc") or "absent",
    }


# Handling fixed by plan.md's reference inventory for the shapes it names;
# every other shape the run finds refuses until a row is decided by hand.
KNOWN_HANDLING = {
    "PLAYLISTS/PRIMARYKEY@KEY[TRACK]": "Redirect (playlists, History, `_LOOPS`, `_RECORDINGS`)",
    "PLAYLISTS/PRIMARYKEY@KEY[STEM]": "Preserve",
    "SETS/PRIMARYKEY@KEY[*]": "Preserve",
}
UNKNOWN_HANDLING = "Refuse (`unknown_reference_shape`) unless decided here"


def _inventory_rows(inventory: Counter) -> dict[str, int]:
    """Counts per table row: every SETS PRIMARYKEY TYPE folds into the
    SETS [*] row, known rows appear even at zero, then any other shape."""
    rows = dict.fromkeys(KNOWN_HANDLING, 0)
    for shape, count in inventory.most_common():
        key = "SETS/PRIMARYKEY@KEY[*]" if shape.startswith("SETS/PRIMARYKEY@KEY[") else shape
        rows[key] = rows.get(key, 0) + count
    return rows


def render_artifact(inputs: dict[str, str], copies: tuple[str, int, int], inventory: Counter, rates: Rates,
                    counts: dict[str, int], dependencies: dict[str, str], playcount_overlap: tuple[int, int]) -> str:
    """Emits the same sections, rows and wording as the committed
    docs/2026-09-26-dedupe-spike.md template, so a run fills the template
    in place rather than discarding its handling rows."""
    copies_path, copy_count, format_count = copies
    lines = ["# Dedupe spike: reference inventory and AUDIO_ID stability", "", "## Inputs", ""]
    lines += [f"- `{name}` sha256 `{digest}`" for name, digest in inputs.items()]
    lines += [f"- copies folder: `{copies_path}`, {copy_count} byte-identical and {format_count}",
              "  format-converted copies"]
    lines += ["", "## Reference inventory", "", "| Shape | Count | Handling |", "| --- | --- | --- |"]
    for shape, count in _inventory_rows(inventory).items():
        lines.append(f"| `{shape}` | {count} | {KNOWN_HANDLING.get(shape, UNKNOWN_HANDLING)} |")
    lines.append(f"| any other shape | 0 | {UNKNOWN_HANDLING} |")
    lines += ["", "`INDEXING/SORTING_INFO PATH` names a playlist, not a track, and smartlists",
              "are queries; neither appears in this table because neither holds a", "primary key."]
    lines += ["", "## AUDIO_ID stability", "", "| Metric | Value | Sample |", "| --- | --- | --- |"]
    lines += [
        f"| AUDIO_ID presence | {rates.audio_id_presence:.2%} | {counts['entries']} entries |",
        f"| Re-analysis stability | {rates.reanalysis:.2%} | {counts['reanalysed']} entries |",
        f"| Copy agreement | {rates.copy:.2%} | {counts['copies']} copies |",
        f"| Format agreement | {rates.format:.2%} | {counts['formats']} copies |",
        f"| False collisions | {rates.false_collisions} | pairs |",
    ]
    lines += ["", "## Dependencies", ""] + [f"- {name}: {state}" for name, state in dependencies.items()]
    verdict = "admitted" if rates.tier3_admitted() else "not admitted"
    scope = "copies and format upgrades" if rates.covers_format_upgrades() else "copies only"
    lines += ["", "## Tier 3 verdict", "",
              f"AUDIO_ID for tier 3: {verdict}; scope {scope if rates.tier3_admitted() else 'none'}. Admitted only",
              "when re-analysis stability and copy agreement are both at least 99% and",
              "false collisions are zero (DL-315)."]
    shared, disjoint = playcount_overlap
    lines += [
        "", "## PLAYCOUNT", "",
        f"Duplicate groups with a LAST_PLAYED on every member: {shared}; on only some members: {disjoint}.",
        "DL-316 records `max` unless the second count shows duplicates commonly carry disjoint histories.", "",
    ]
    return "\n".join(lines)


def playcount_overlap(root) -> tuple[int, int]:
    """Among AUDIO_ID-sharing groups, how many carry LAST_PLAYED on every
    member (a shared history, which favours max) versus on only some (a
    disjoint history, which would favour sum)."""
    played: dict[str, list[bool]] = {}
    for entry in root.find("COLLECTION").findall("ENTRY"):
        audio_id = entry.attrib.get("AUDIO_ID", "")
        if audio_id:
            info = entry.find("INFO")
            played.setdefault(audio_id, []).append(bool(info is not None and info.attrib.get("LAST_PLAYED")))
    groups = [flags for flags in played.values() if len(flags) > 1]
    return sum(1 for f in groups if all(f)), sum(1 for f in groups if any(f) and not all(f))


def output_refusal(out: Path, *inputs: Path) -> str | None:
    """Why --out cannot be written, or None, checked before any input is
    read. The spike runs against the real library, so --out naming an
    input or any collection.nml (the file Traktor itself loads) would
    overwrite the library it measures; the artifact is Markdown, so any
    .nml output is refused too (plan.md: never write to an input path or
    the live collection.nml)."""
    if path_collides(out, *inputs):
        return f"refused: --out {out.as_posix()} names an input"
    if out.name.casefold() == "collection.nml" or out.suffix.casefold() == ".nml":
        return f"refused: --out {out.as_posix()} is an NML file; the artifact is Markdown"
    return None


def main(argv: list[str]) -> int:
    """Run the spike and write the artifact. Returns 2 when --out names an
    input or the live collection.nml, matching the dedupe command's refusal
    code (DL-311); the spike never writes to an input."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nml", type=Path, required=True)
    parser.add_argument("--reanalysed", type=Path, required=True)
    parser.add_argument("--copies", type=Path, required=True)
    parser.add_argument("--volume-map", nargs=3, action="append", metavar=("SCAN_ROOT", "VOLUME", "VOLUMEID"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    refusal = output_refusal(args.out, args.nml, args.reanalysed)
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return 2

    loaded, reloaded = read_and_parse_source(args.nml), read_and_parse_source(args.reanalysed)
    for result in (loaded, reloaded):
        if result.error is not None:
            print(result.error, file=sys.stderr)
            return 2
    records, reanalysed = collection_records(loaded.root), collection_records(reloaded.root)
    known_mounts: dict[tuple[str, str], list[Path]] = {}
    for root_text, identity in parse_volume_map(args.volume_map).items():
        known_mounts.setdefault(identity, []).append(Path(Path(root_text).anchor))

    reanalysis, reanalysed_count = reanalysis_stability(records, reanalysed)
    copy_rate, format_rate, copies, formats = copy_agreement(records, args.copies, known_mounts)
    rates = Rates(_share(sum(1 for r in records if r.audio_id), len(records)), reanalysis, copy_rate, format_rate,
                  false_collisions(records))
    counts = {"entries": len(records), "reanalysed": reanalysed_count, "copies": copies, "formats": formats}
    inputs = {str(args.nml): _sha256(args.nml), str(args.reanalysed): _sha256(args.reanalysed)}
    text = render_artifact(inputs, (args.copies.as_posix(), copies, formats), reference_inventory(loaded.root),
                           rates, counts, dependency_state(), playcount_overlap(loaded.root))
    args.out.write_text(text, encoding="utf-8")
    print(f"artifact_written={args.out.as_posix()} tier3={'admitted' if rates.tier3_admitted() else 'not_admitted'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

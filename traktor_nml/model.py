"""Core domain model: LOCATION/PRIMARYKEY parsing and the EntryRecord identity.

A Traktor NML file holds one COLLECTION of ENTRY elements whose LOCATION
carries VOLUME, VOLUMEID, DIR and FILE, and a PLAYLISTS tree whose PRIMARYKEY
elements reference collection entries by the flattened concatenation
VOLUME + DIR + FILE. Every path repair is therefore two edits that must agree:
the LOCATION on the collection entry and every PRIMARYKEY that pointed at its
old flattened form.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Iterable, Optional

from .xmlio import ET


@dataclass(frozen=True)
class LocationParts:
    volume: str
    volumeid: str
    dir_value: str
    file_name: str

    @property
    def primary_key(self) -> str:
        return f"{self.volume}{self.dir_value}{self.file_name}"

    @property
    def decoded_dir(self) -> PurePosixPath:
        return decode_traktor_dir(self.dir_value)

    @property
    def decoded_path(self) -> PurePosixPath:
        return self.decoded_dir / self.file_name


@dataclass(frozen=True)
class RewriteRule:
    old_volume: str
    old_dir_prefix: str
    new_volume: str
    new_dir_prefix: str
    new_volumeid: str | None = None

    def matches(self, loc: LocationParts) -> bool:
        return loc.volume == self.old_volume and loc.dir_value.startswith(self.old_dir_prefix)

    def apply(self, loc: LocationParts) -> LocationParts:
        # VOLUMEID defaults to new_volume: most real collections use
        # identical VOLUME/VOLUMEID pairs, so new_volumeid is only needed
        # when a rule's destination volume and volume id actually diverge.
        suffix = loc.dir_value[len(self.old_dir_prefix):]
        return LocationParts(
            volume=self.new_volume,
            volumeid=self.new_volume if self.new_volumeid is None else self.new_volumeid,
            dir_value=f"{self.new_dir_prefix}{suffix}",
            file_name=loc.file_name,
        )


@dataclass
class EntryRecord:
    """A track's identity fields together with an optional source element.

    A record derived from a filesystem candidate (see diskscan.py) carries no
    element, since there is nothing in an NML document for it to point at.
    A record read from a collection carries the element that attribute
    patching locates. Every consumer that dereferences .entry guards for None,
    and candidate-side records (entry is None) are never passed to the
    attribute-patch write path, only used as the matching-cascade's candidate
    side.
    """

    entry: Optional[ET.Element]
    artist: str
    title: str
    audio_id: str
    filesize: str
    playtime_float: str
    bitrate: str
    album: str
    file_name: str
    location: LocationParts
    # Set only on disk-derived candidates (entry is None), so reconnection can
    # re-encode the real absolute path into a LOCATION after a match, since
    # the placeholder LocationParts a candidate carries is for display only
    # and is never treated as an authoritative VOLUME/VOLUMEID source.
    source_path: Optional[Path] = None

    @property
    def primary_key(self) -> str:
        return self.location.primary_key


@dataclass
class ElemPatch:
    sourceline: int
    tag_name: str
    locator: tuple[tuple[str, str], ...]
    changes: list[tuple[str, str, str]] = field(default_factory=list)  # (attr, old, new)


# Bounded rather than unbounded: a disk scan can index tens of thousands of
# files, and an uncapped cache would hold an entry per distinct folder for the
# life of the run. Tracks cluster heavily by folder, so a few thousand entries
# already collapse most of the repetition - LocationParts.decoded_dir is a
# plain property that re-decodes on every access, and the match cascade reads
# it several times per record.
@lru_cache(maxsize=4096)
def decode_traktor_dir(dir_value: str) -> PurePosixPath:
    if not dir_value or dir_value == "/:":
        return PurePosixPath("/")

    trimmed = dir_value
    if trimmed.startswith("/:"):
        trimmed = trimmed[2:]
    if trimmed.endswith("/:"):
        trimmed = trimmed[:-2]

    parts = [part for part in trimmed.split("/:") if part]
    return PurePosixPath("/") / PurePosixPath(*parts)


def encode_traktor_dir(path_value: str) -> str:
    normalized = path_value.replace("\\", "/").strip()
    parts = [part for part in normalized.split("/") if part]
    return "/:" + "/:".join(parts) + "/:"


def normalize_dir_prefix(value: str) -> str:
    stripped = value.strip()
    if "/:" in stripped:
        if not stripped.startswith("/:"):
            stripped = "/:" + (stripped[1:] if stripped.startswith("/") else stripped)
        if not stripped.endswith("/:"):
            stripped = stripped.rstrip("/") + "/:"
        return stripped
    return encode_traktor_dir(stripped)


def parse_location_element(elem: ET.Element) -> LocationParts:
    return LocationParts(
        volume=elem.attrib.get("VOLUME", ""),
        volumeid=elem.attrib.get("VOLUMEID", elem.attrib.get("VOLUME", "")),
        dir_value=elem.attrib.get("DIR", ""),
        file_name=elem.attrib.get("FILE", ""),
    )


def write_location_element(elem: ET.Element, loc: LocationParts) -> None:
    elem.attrib["VOLUME"] = loc.volume
    elem.attrib["VOLUMEID"] = loc.volumeid
    elem.attrib["DIR"] = loc.dir_value
    elem.attrib["FILE"] = loc.file_name


def parse_primary_key(key: str, volumeid: str | None = None) -> LocationParts:
    marker = "/:"
    idx = key.find(marker)
    if idx < 0:
        raise ValueError(f"PRIMARYKEY missing '/:' marker: {key!r}")

    volume = key[:idx]
    remainder = key[idx:]
    last = remainder.rfind(marker)
    if last < 0:
        raise ValueError(f"PRIMARYKEY missing final '/:' separator: {key!r}")

    dir_value = remainder[: last + len(marker)]
    file_name = remainder[last + len(marker):]
    return LocationParts(
        volume=volume,
        volumeid=volume if volumeid is None else volumeid,
        dir_value=dir_value,
        file_name=file_name,
    )


def apply_rules(loc: LocationParts, rules: Iterable[RewriteRule]) -> tuple[LocationParts, bool]:
    for rule in rules:
        if rule.matches(loc):
            return rule.apply(loc), True
    return loc, False


def collection_entries(root: ET.Element) -> list[ET.Element]:
    collection = root.find("COLLECTION")
    return [] if collection is None else collection.findall("ENTRY")


def playlist_entries(root: ET.Element) -> list[ET.Element]:
    return root.findall(".//PLAYLIST/ENTRY")


def all_entries(root: ET.Element) -> list[ET.Element]:
    return root.findall(".//ENTRY")


def collection_records(root: ET.Element) -> list[EntryRecord]:
    records: list[EntryRecord] = []
    for entry in collection_entries(root):
        loc_elem = entry.find("LOCATION")
        if loc_elem is None:
            continue
        info = entry.find("INFO")
        album = entry.find("ALBUM")
        records.append(
            EntryRecord(
                entry=entry,
                artist=entry.attrib.get("ARTIST", ""),
                title=entry.attrib.get("TITLE", ""),
                audio_id=entry.attrib.get("AUDIO_ID", ""),
                filesize="" if info is None else info.attrib.get("FILESIZE", ""),
                playtime_float="" if info is None else info.attrib.get("PLAYTIME_FLOAT", ""),
                bitrate="" if info is None else info.attrib.get("BITRATE", ""),
                album="" if album is None else album.attrib.get("TITLE", ""),
                file_name=loc_elem.attrib.get("FILE", ""),
                location=parse_location_element(loc_elem),
            )
        )
    return records


def location_rows(entries: list[ET.Element]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in entries:
        loc_elem = entry.find("LOCATION")
        if loc_elem is None:
            continue
        loc = parse_location_element(loc_elem)
        rows.append(
            {
                "artist": entry.attrib.get("ARTIST", ""),
                "title": entry.attrib.get("TITLE", ""),
                "volume": loc.volume,
                "volumeid": loc.volumeid,
                "dir": loc.dir_value,
                "file": loc.file_name,
                "decoded_path": str(loc.decoded_path),
                "primary_key": loc.primary_key,
            }
        )
    return rows


def entry_label(entry: ET.Element) -> str:
    artist = entry.attrib.get("ARTIST", "")
    title = entry.attrib.get("TITLE", "")
    if artist or title:
        return f"{artist} - {title}".strip(" -")
    return "<reference>"


def record_label(record: EntryRecord) -> str:
    if record.entry is not None:
        return entry_label(record.entry)
    if record.artist or record.title:
        return f"{record.artist} - {record.title}".strip(" -")
    return record.file_name or "<candidate>"


def loc_attr_changes(old: LocationParts, new: LocationParts) -> list[tuple[str, str, str]]:
    return [
        (attr, ov, nv)
        for attr, ov, nv in [
            ("VOLUME", old.volume, new.volume),
            ("VOLUMEID", old.volumeid, new.volumeid),
            ("DIR", old.dir_value, new.dir_value),
            ("FILE", old.file_name, new.file_name),
        ]
        if ov != nv
    ]

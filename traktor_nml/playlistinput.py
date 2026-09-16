"""build-playlist input formats, read into one Candidate list.

detect_format names the format a path holds and read_input reads it into
an InputRead: the format, the codec it was decoded with, and the ordered
Candidate list tracklist.resolve_candidates and
buildplaylist.assemble_output consume unchanged (DL-274, DL-281).
read_input dispatches on detect_format, or on an explicit format that
overrides it (DL-294): read_text reads a plain-text track list,
read_folder a directory's own audio files, read_m3u an .m3u or .m3u8
playlist and read_csv a CSV whose header names CSV_COLUMNS.

An input that cannot be read raises InputReadError carrying the one
refusal code both surfaces print. A reader never returns fewer
candidates than its input holds entries: a partial list is
indistinguishable from a complete one by inspection.

No nicegui import: the CLI, the GUI and the suite all reach this module
directly (DL-069).
"""

from __future__ import annotations

import csv
import enum
import io
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Optional

from .diskscan import DiskReadError, _has_audio_extension, index_files
from .model import EntryRecord, LocationParts, encode_traktor_dir
from .tracklist import Candidate, text_candidates


class InputFormat(enum.Enum):
    """The four input formats detect_format names."""

    TEXT = "text"
    CSV = "csv"
    M3U = "m3u"
    FOLDER = "folder"


@dataclass(frozen=True)
class InputRead:
    """What a reader returns: the format read, the codec used and the
    ordered Candidate list. format and encoding travel here rather than
    in the run's stats, so a text run's stats and CLI stdout stay those
    the text corpus records (DL-280)."""

    format: InputFormat
    # The codec the bytes were decoded with.
    encoding: str
    candidates: list[Candidate]


class InputReadError(Exception):
    """An input that cannot be read at all. code is the exact refusal
    string the CLI prints to stderr and the GUI shows."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def detect_format(path: Path) -> InputFormat:
    """A directory is a folder input; .csv is CSV; .m3u and .m3u8 are
    M3U; any other file, with or without a suffix, is plain text
    (DL-281). Suffix-based rather than content sniffing, so the format a
    file is read as is predictable from its name."""
    if path.is_dir():
        return InputFormat.FOLDER
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return InputFormat.CSV
    if suffix in (".m3u", ".m3u8"):
        return InputFormat.M3U
    return InputFormat.TEXT


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        # OSError, not just FileNotFoundError: a directory or a
        # permission-denied path reports the same clean refusal rather
        # than a traceback.
        raise InputReadError(f"input_not_found={path.as_posix()}") from None


def _decode_strict(data: bytes, path: Path) -> str:
    try:
        # utf-8-sig strips a leading BOM rather than letting it corrupt the
        # first entry's artist name.
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InputReadError(f"tracklist_decode_error={path.as_posix()}") from None


def _decode_with_fallback(data: bytes, path: Path) -> tuple[str, str]:
    """(text, codec): utf-8-sig when the bytes are UTF-8, else cp1252,
    which decodes the bytes an .m3u saved by Windows software carries.
    cp1252 accepts almost any byte sequence, so a file in another
    single-byte codepage decodes wrongly without an error; the codec is
    returned so the run can name it."""
    try:
        return data.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("cp1252"), "cp1252"
    except UnicodeDecodeError:
        # cp1252 leaves five bytes undefined (0x81, 0x8D, 0x8F, 0x90, 0x9D).
        raise InputReadError(f"tracklist_decode_error={path.as_posix()}") from None


def read_text(path: Path) -> InputRead:
    """A plain-text track list, decoded utf-8-sig strict, so its refusal
    codes and its candidates replay the text corpus byte for byte
    (DL-279)."""
    text = _decode_strict(_read_bytes(path), path)
    return InputRead(InputFormat.TEXT, "utf-8-sig", text_candidates(text))


_DIGIT_RUN = re.compile(r"(\d+)")


def folder_order_key(name: str) -> tuple:
    """Numeric-aware order for a folder's file names, the order Explorer
    and Finder show: '2 - b.mp3' before '10 - c.mp3', where a plain string
    sort puts '10' first. The casefolded name is split into digit and
    non-digit runs, digit runs compared as integers; each run is tagged so
    a digit run and a text run at the same position compare without a
    TypeError. The plain name breaks ties ('01 a' and '1 a'), so the order
    is total and repeatable."""
    runs = tuple(
        (0, int(run), "") if run.isdigit() else (1, 0, run)
        for run in _DIGIT_RUN.split(name.casefold())
        if run
    )
    return (runs, name)


def _file_candidate(position: int, raw_text: str, record: EntryRecord) -> Candidate:
    # artist/title shown in the report come from the record's own tags,
    # empty for an untagged file; raw_text already names the file.
    # The record goes on whole: size, duration, file name and folder parts
    # are what let the entry match above artist_title.
    return Candidate(position, raw_text, record.artist, record.title, record)


def _index_or_refuse(paths: list[Path]) -> list[EntryRecord]:
    """index_files over paths, its DiskReadError translated into the
    input_read_error=<path> refusal. diskscan stays free of this module's
    error type, so the translation happens here, and the code names the
    file that failed rather than the folder holding it."""
    try:
        return index_files(paths)
    except DiskReadError as exc:
        # One named refusal rather than a shorter list.
        raise InputReadError(f"input_read_error={exc.path.as_posix()}") from None


def read_folder(path: Path) -> InputRead:
    """The folder's own audio files - no recursion - in folder_order_key
    order, each indexed from disk so its size, duration, tags, file name
    and folder parts reach the stricter tiers. line_number is the 1-based
    position in that order and raw_text the file name. Candidates resolve
    through match_records alone, and a file the collection does not hold
    is reported unmatched; no ENTRY is ever added for it."""
    try:
        # iterdir, not a recursive walk: the chosen folder's own files only.
        children = [child for child in path.iterdir() if child.is_file() and _has_audio_extension(child)]
    except OSError:
        raise InputReadError(f"input_not_found={path.as_posix()}") from None
    children.sort(key=lambda child: folder_order_key(child.name))
    records = _index_or_refuse(children)
    candidates = [
        _file_candidate(position, child.name, record)
        for position, (child, record) in enumerate(zip(children, records), start=1)
    ]
    return InputRead(InputFormat.FOLDER, "n/a", candidates)


_EXTINF = re.compile(r"^#EXTINF:\s*(-?\d+(?:\.\d+)?)\s*(?:[^,]*),(.*)$", re.IGNORECASE)
# A drive letter ("C:") is not a URL scheme; a scheme needs two or more letters.
_URL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]+://")
_DRIVE = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True)
class _ExtInf:
    """A parsed #EXTINF directive, waiting for the path line it
    describes."""

    seconds: str  # "" when the directive gave no positive duration
    artist: str
    title: str


def _parse_extinf(line: str) -> Optional[_ExtInf]:
    """The duration and 'Artist - Title' display text of an #EXTINF line,
    or None for any other directive. Seconds of zero or less give no
    duration; display text splits on its first ' - '. Whole seconds sit
    up to 1.0s from a collection's PLAYTIME_FLOAT, the edge of the
    duration tolerance."""
    match = _EXTINF.match(line)
    if match is None:
        return None
    seconds = float(match.group(1))
    display = match.group(2).strip()
    artist, sep, title = display.partition(" - ")
    if not sep or not artist.strip() or not title.strip():
        # Display text that is not 'Artist - Title' cannot be split without
        # guessing which half is which, so both stay empty.
        artist = title = ""
    return _ExtInf(
        seconds=f"{seconds:.3f}" if seconds > 0 else "",
        artist=artist.strip(),
        title=title.strip(),
    )


def _path_flavour(path_text: str):
    """PureWindowsPath for a drive letter or a backslash, PurePosixPath
    otherwise, so a playlist written on a Mac and one written on Windows
    decode to the same folder parts on either machine."""
    if _DRIVE.match(path_text) or "\\" in path_text:
        return PureWindowsPath(path_text)
    return PurePosixPath(path_text)


def _path_string_record(path_text: str, extinf: Optional[_ExtInf]) -> EntryRecord:
    """A record for a path this machine does not hold: file name and
    folder parts from the path string, artist, title and duration from
    its #EXTINF. The folder parts are encoded the way a collection DIR
    is, so the path_suffix tiers compare them directly; the volume stays
    empty because this path names no volume this collection knows.
    source_path None marks it as not read from disk."""
    pure = _path_flavour(path_text)
    # The anchor ('C:\' or '/') names a drive or root, not a folder, so it
    # is left out of the folder parts whichever flavour parsed it.
    folder_parts = [part for part in pure.parent.parts if part != pure.anchor]
    return EntryRecord(
        entry=None,
        artist=extinf.artist if extinf else "",
        title=extinf.title if extinf else "",
        audio_id="",
        filesize="",
        playtime_float=extinf.seconds if extinf else "",
        bitrate="",
        album="",
        file_name=pure.name,
        location=LocationParts(
            volume="", volumeid="", dir_value=encode_traktor_dir("/".join(folder_parts)), file_name=pure.name
        ),
        source_path=None,
    )


def _resolve_playlist_path(path_text: str, playlist_dir: Path) -> Path:
    """The path a playlist line names on this machine: an absolute path
    as written, a relative one joined onto the playlist's own folder.
    Whether a file exists there decides between indexing it from disk
    and a path-string record."""
    pure = _path_flavour(path_text)
    return Path(pure) if pure.is_absolute() else playlist_dir / Path(pure)


def read_m3u(path: Path) -> InputRead:
    """An .m3u or .m3u8 playlist, one Candidate per path line in order.

    .m3u8 is UTF-8 by definition and decodes strictly; .m3u falls back to
    cp1252, and InputRead.encoding names the codec used. #EXTINF attaches
    to the next path line and every other '#' line is ignored. A relative
    path resolves against the playlist's own folder. A path that is a
    file on this machine is indexed from disk and takes its artist, title
    and duration from the file, ignoring #EXTINF; any other path becomes
    a path-string record. A URL line is an unparseable Candidate.
    line_number is the path line's number and raw_text the path line.
    """
    data = _read_bytes(path)
    if path.suffix.casefold() == ".m3u8":
        text, encoding = _decode_strict(data, path), "utf-8-sig"
    else:
        text, encoding = _decode_with_fallback(data, path)

    pending: Optional[_ExtInf] = None
    # (line_number, raw_text, present file or None, path-string record or None)
    entries: list[tuple[int, str, Optional[Path], Optional[EntryRecord]]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            extinf = _parse_extinf(stripped)
            if extinf is not None:
                pending = extinf
            continue
        extinf, pending = pending, None
        if _URL.match(stripped):
            entries.append((line_number, raw_line, None, None))
            continue
        target = _resolve_playlist_path(stripped, path.parent)
        if target.is_file():
            entries.append((line_number, raw_line, target, None))
        else:
            entries.append((line_number, raw_line, None, _path_string_record(stripped, extinf)))

    # Present files are indexed in one call, so a stat failure names the
    # file and refuses the whole read.
    present = iter(_index_or_refuse([target for _n, _r, target, _rec in entries if target is not None]))
    candidates: list[Candidate] = []
    for line_number, raw_line, target, record in entries:
        if target is not None:
            record = next(present)
        if record is None:
            candidates.append(Candidate(line_number, raw_line, "", "", None))
        else:
            candidates.append(_file_candidate(line_number, raw_line, record))
    return InputRead(InputFormat.M3U, encoding, candidates)


@dataclass(frozen=True)
class CsvColumn:
    """One CSV column: the header text the template writes and the
    parser recognises, the EntryRecord field it fills, and whether a
    file without it refuses with csv_header_missing."""

    header: str
    field: str  # the EntryRecord field the column fills
    required: bool


# The one definition of the CSV header: csv_template_bytes() writes it and
# read_csv recognises it, so a downloaded template stays uploadable.
# Album, Duration and File name are optional but let a row reach tiers
# stronger than artist_title.
CSV_COLUMNS: tuple[CsvColumn, ...] = (
    CsvColumn("Artist", "artist", True),
    CsvColumn("Title", "title", True),
    CsvColumn("Album", "album", False),
    CsvColumn("Duration", "playtime_float", False),
    CsvColumn("File name", "file_name", False),
)


def csv_template_bytes() -> bytes:
    """The header row alone, UTF-8 with a BOM so Excel opens it as UTF-8,
    CRLF-terminated. No example row: one left in by accident is an
    unmatched entry that refuses the run."""
    header = ",".join(column.header for column in CSV_COLUMNS)
    return ("\ufeff" + header + "\r\n").encode("utf-8")


def _header_index(cells: list[str]) -> dict[str, int]:
    """EntryRecord field -> column index, headers matched after strip and
    casefold; unrecognised columns are ignored, and a repeated header
    keeps its first column."""
    by_header = {column.header.casefold(): column.field for column in CSV_COLUMNS}
    index: dict[str, int] = {}
    for position, cell in enumerate(cells):
        field = by_header.get(cell.strip().casefold())
        if field is not None and field not in index:
            index[field] = position
    return index


def _choose_delimiter(header_line: str) -> str:
    """Comma if the header splits into every required column on commas,
    else semicolon - what Excel writes in locales whose decimal mark is a
    comma - else csv_header_missing. Chosen from the header alone:
    csv.Sniffer guesses from data rows and misreads titles holding
    commas."""
    required = {column.field for column in CSV_COLUMNS if column.required}
    for delimiter in (",", ";"):
        cells = next(csv.reader([header_line], delimiter=delimiter), [])
        if required <= set(_header_index(cells)):
            return delimiter
    raise InputReadError("csv_header_missing")


_DURATION = re.compile(r"^(?:(\d+):)?(?:(\d+):)?(\d+(?:\.\d+)?)$")


def parse_duration(text: str) -> str:
    """Seconds ('215', '215.4'), m:ss or h:mm:ss as a PLAYTIME_FLOAT
    string, or '' when the cell is empty or unreadable - an unreadable
    duration drops the evidence, not the row."""
    match = _DURATION.match(text.strip())
    if match is None:
        return ""
    first, second, seconds = match.groups()
    hours, minutes = (first, second) if second is not None else (None, first)
    total = float(seconds) + 60 * int(minutes or 0) + 3600 * int(hours or 0)
    return f"{total:.3f}" if total > 0 else ""


def _csv_record(cells: list[str], index: dict[str, int]) -> dict[str, str]:
    """EntryRecord field -> stripped cell text for every CSV_COLUMNS
    field, "" for a column the header lacks or a row too short to reach
    it, so a ragged row reads as missing optional cells rather than
    raising."""

    def cell(field: str) -> str:
        position = index.get(field)
        return cells[position].strip() if position is not None and position < len(cells) else ""

    return {column.field: cell(column.field) for column in CSV_COLUMNS}


def read_csv(path: Path) -> InputRead:
    """A CSV with CSV_COLUMNS' headers, one Candidate per non-empty row.

    Decoded utf-8-sig, falling back to cp1252, and InputRead.encoding
    names the codec used. A row with an empty Artist or Title is
    unparseable; a row with every cell empty is skipped. line_number is
    the physical line the row starts on - the header is line 1 when it is
    the first line, so it is the spreadsheet's row number, a quoted
    multi-line cell included - and raw_text is that row's physical lines
    as read.
    """
    text, encoding = _decode_with_fallback(_read_bytes(path), path)
    # csv counts one line per "\n"; normalising first keeps its line_num
    # and this list of physical lines in step.
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    physical = normalised.split("\n")
    header_number = next((n for n, line in enumerate(physical, start=1) if line.strip()), None)
    if header_number is None:
        raise InputReadError("csv_header_missing")
    # Comma or semicolon, decided by the header line alone; the data rows
    # are read with that one delimiter.
    delimiter = _choose_delimiter(physical[header_number - 1])

    reader = csv.reader(io.StringIO("\n".join(physical[header_number - 1:])), delimiter=delimiter)
    index = _header_index(next(reader))
    candidates: list[Candidate] = []
    previous_end = header_number
    for cells in reader:
        start = previous_end + 1
        previous_end = header_number - 1 + reader.line_num
        # A row of empty cells is a blank spreadsheet line, not an entry, so
        # it is neither a candidate nor a report row.
        if not any(cell.strip() for cell in cells):
            continue
        raw_text = "\n".join(physical[start - 1:previous_end])
        fields = _csv_record(cells, index)
        if not fields["artist"] or not fields["title"]:
            candidates.append(Candidate(start, raw_text, fields["artist"], fields["title"], None))
            continue
        record = EntryRecord(
            entry=None,
            artist=fields["artist"],
            title=fields["title"],
            audio_id="",
            filesize="",
            playtime_float=parse_duration(fields["playtime_float"]),
            bitrate="",
            album=fields["album"],
            file_name=fields["file_name"],
            # No folder: a CSV row names no path, so the path tiers stay
            # silent and the location is never read as a volume.
            location=LocationParts(volume="", volumeid="", dir_value="", file_name=fields["file_name"]),
            source_path=None,
        )
        candidates.append(Candidate(start, raw_text, record.artist, record.title, record))
    return InputRead(InputFormat.CSV, encoding, candidates)


# Each reader owns its decoding: text and .m3u8 strict, .m3u and .csv with
# the cp1252 fallback, a folder none (DL-282, DL-283).
_READERS = {
    InputFormat.TEXT: read_text,
    InputFormat.CSV: read_csv,
    InputFormat.M3U: read_m3u,
    InputFormat.FOLDER: read_folder,
}


def read_input(path: Path, fmt: Optional[InputFormat] = None) -> InputRead:
    """Read path as fmt, or as detect_format names it when fmt is None.

    An explicit fmt overrides the suffix, so a mis-suffixed file is read
    as what it holds (DL-294). fmt folder on a path that is not a
    directory, or a file format on a directory, refuses with
    input_format_mismatch=<format>. A path that does not exist refuses
    with input_not_found whatever the format (DL-292).
    """
    if not path.exists():
        raise InputReadError(f"input_not_found={path.as_posix()}")
    if fmt is None:
        fmt = detect_format(path)
    if (fmt is InputFormat.FOLDER) != path.is_dir():
        raise InputReadError(f"input_format_mismatch={fmt.value}")
    return _READERS[fmt](path)

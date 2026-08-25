"""Rank disk-scanned audio candidates for an external artist/title list.

This is deliberately a review workflow: fuzzy scores surface possible files,
but never select collection entries or modify an NML document.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .model import EntryRecord
from .tracklist import ParsedLine

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_PREFIX_RE = re.compile(r"^(?:\d{1,2}[a-z]|\d{1,3})[ _-]+", re.IGNORECASE)
_STOP_WORDS = frozenset({"a", "and", "edit", "feat", "featuring", "mix", "mp3", "original", "remix", "the", "vs"})


@dataclass(frozen=True)
class DiscoveryMatch:
    line: ParsedLine
    candidate_path: Path | None
    candidate_artist: str
    candidate_title: str
    source: str
    score: float
    artist_score: float
    title_score: float


@dataclass(frozen=True)
class CollectionDiscoveryMatch:
    line: ParsedLine
    candidate: EntryRecord | None
    score: float
    artist_score: float
    title_score: float


def normalize(value: str) -> str:
    """Case-fold punctuation and accents so filename variants can compare."""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return _NON_ALNUM_RE.sub(" ", ascii_value.casefold()).strip()


def _tokens(value: str) -> set[str]:
    return {token for token in normalize(value).split() if token not in _STOP_WORDS}


def _sequence_score(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, normalize(left), normalize(right)).ratio()


def _coverage_score(query: str, candidate: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    return len(query_tokens & _tokens(candidate)) / len(query_tokens)


def _filename_label(path: Path) -> str:
    """Remove a common Traktor key/BPM prefix without assuming a file schema."""
    return _PREFIX_RE.sub("", path.stem.replace("_", " "))


def _score_candidate(line: ParsedLine, artist: str, title: str, fallback_label: str) -> tuple[float, float, float] | None:
    artist_basis = artist if artist else fallback_label
    title_basis = title if title else fallback_label
    title_coverage = _coverage_score(line.title, title_basis)
    # On large archives, most files share no meaningful title term with a
    # request. They cannot make a credible review candidate, so avoid costly
    # character-level comparisons for that majority.
    if title_coverage == 0.0:
        return None
    artist_score = max(_sequence_score(line.artist, artist_basis), _coverage_score(line.artist, artist_basis))
    title_score = max(_sequence_score(line.title, title_basis), title_coverage)
    full_basis = f"{artist_basis} {title_basis}" if artist or title else fallback_label
    full_score = _sequence_score(f"{line.artist} {line.title}", full_basis)
    return 0.30 * artist_score + 0.55 * title_score + 0.15 * full_score, artist_score, title_score


def rank_candidates(
    lines: list[ParsedLine], candidates: list[EntryRecord], *, max_candidates: int, min_score: float
) -> list[DiscoveryMatch]:
    """Return the strongest review candidates for each input line.

    Embedded tags are preferred when present. Untagged files are compared as
    normalized filename text; the score combines artist, title, and full-line
    evidence, and is only a ranking signal rather than an identity claim.
    """
    matches: list[DiscoveryMatch] = []
    for line in lines:
        ranked: list[DiscoveryMatch] = []
        for candidate in candidates:
            if candidate.source_path is None:
                continue
            filename_label = _filename_label(candidate.source_path)
            result = _score_candidate(line, candidate.artist, candidate.title, filename_label)
            if result is None:
                continue
            score, artist_score, title_score = result
            ranked.append(
                DiscoveryMatch(
                    line=line,
                    candidate_path=candidate.source_path,
                    candidate_artist=candidate.artist,
                    candidate_title=candidate.title,
                    source="tags" if candidate.artist or candidate.title else "filename",
                    score=score,
                    artist_score=artist_score,
                    title_score=title_score,
                )
            )

        accepted = [match for match in ranked if match.score >= min_score]
        accepted.sort(key=lambda match: (-match.score, str(match.candidate_path).casefold()))
        matches.extend(accepted[:max_candidates])
        if not accepted:
            matches.append(
                DiscoveryMatch(
                    line=line,
                    candidate_path=None,
                    candidate_artist="",
                    candidate_title="",
                    source="none",
                    score=0.0,
                    artist_score=0.0,
                    title_score=0.0,
                )
            )
    return matches


def rank_collection_candidates(
    lines: list[ParsedLine], candidates: list[EntryRecord], *, max_candidates: int, min_score: float
) -> list[CollectionDiscoveryMatch]:
    """Rank existing collection records with the same relaxed review score."""
    matches: list[CollectionDiscoveryMatch] = []
    for line in lines:
        ranked: list[CollectionDiscoveryMatch] = []
        for candidate in candidates:
            result = _score_candidate(line, candidate.artist, candidate.title, candidate.file_name)
            if result is None:
                continue
            score, artist_score, title_score = result
            ranked.append(CollectionDiscoveryMatch(line, candidate, score, artist_score, title_score))
        accepted = [match for match in ranked if match.score >= min_score]
        accepted.sort(
            key=lambda match: (-match.score, match.candidate.primary_key if match.candidate is not None else "")
        )
        matches.extend(accepted[:max_candidates])
        if not accepted:
            matches.append(CollectionDiscoveryMatch(line, None, 0.0, 0.0, 0.0))
    return matches

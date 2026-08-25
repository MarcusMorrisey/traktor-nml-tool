"""Persistent tag/fingerprint cache keyed by path, size and modification time.

A stored null value means a prior read was attempted and failed; an absent
key means no attempt was made at all - the two must stay distinguishable so a
plain re-scan does not endlessly retry files it already knows are unreadable,
while --refresh-cache can still target exactly those failures. The cache
flushes every batch so an interrupted scan loses at most its last batch
rather than everything read so far (the tag cache is keyed by path, size and
mtime, so a file renamed without any content change is re-read rather than
recognised - see the plan's tradeoffs).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
from typing import Optional


class TagCache:
    def __init__(self, cache_path: Path, flush_every: int = 50):
        self.cache_path = cache_path
        self.flush_every = flush_every
        self._dirty = 0
        self._data: dict[str, Optional[dict]] = {}
        if cache_path.exists():
            try:
                self._data = json.loads(cache_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    @staticmethod
    def key(path: Path, size: int, mtime: float) -> str:
        """Combine path, size and mtime so a file overwritten in place
        (same path, different bytes) misses the cache even though its
        path alone is unchanged."""
        return f"{path.resolve()}|{size}|{int(mtime)}"

    def attempted(self, path: Path, size: int, mtime: float) -> bool:
        return self.key(path, size, mtime) in self._data

    def get(self, path: Path, size: int, mtime: float) -> Optional[dict]:
        """Return the stored value, or None whether unattempted or failed.

        Callers that must distinguish the two use attempted() first.
        """
        return self._data.get(self.key(path, size, mtime))

    def put(self, path: Path, size: int, mtime: float, value: Optional[dict]) -> None:
        self._data[self.key(path, size, mtime)] = value
        self._dirty += 1
        if self._dirty >= self.flush_every:
            self.flush()

    def should_refresh(self, path: Path, size: int, mtime: float, refresh: bool) -> bool:
        if not self.attempted(path, size, mtime):
            return True
        if refresh and self.get(path, size, mtime) is None:
            return True
        return False

    def flush(self) -> None:
        if self._dirty == 0 and self.cache_path.exists():
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, tmp_name = tempfile.mkstemp(
            prefix=f"{self.cache_path.name}.", suffix=".tmp", dir=self.cache_path.parent
        )
        os.close(descriptor)
        tmp_path = Path(tmp_name)
        try:
            tmp_path.write_text(json.dumps(self._data), encoding="utf-8")
            # Antivirus and indexers can briefly hold a just-written cache on
            # Windows. Keep the atomic replace, but tolerate that short lock.
            for attempt in range(5):
                try:
                    os.replace(tmp_path, self.cache_path)
                    self._dirty = 0
                    return
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        finally:
            tmp_path.unlink(missing_ok=True)

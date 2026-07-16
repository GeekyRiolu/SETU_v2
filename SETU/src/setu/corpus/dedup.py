"""Exact deduplication over normalised sentence pairs."""

from __future__ import annotations

import hashlib

from setu.types import CorpusEntry


class Deduplicator:
    def __init__(self) -> None:
        self._seen: set[bytes] = set()

    def is_duplicate(self, entry: CorpusEntry) -> bool:
        key = hashlib.md5(f"{entry.src_text}\t{entry.tgt_text}".encode()).digest()
        if key in self._seen:
            return True
        self._seen.add(key)
        return False

    def __len__(self) -> int:
        return len(self._seen)

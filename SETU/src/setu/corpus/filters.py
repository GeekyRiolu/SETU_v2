"""Cleaning and alignment-sanity filters.

BPCC and Samanantar arrive sentence-aligned, so "alignment" here means
verifying each pair looks like a real 1:1 alignment (length ratio, script,
non-degenerate text) and dropping pairs that don't.
"""

from __future__ import annotations

from typing import Any

from setu.types import CorpusEntry

# Unicode letter ranges keyed by FLORES script subtag.
SCRIPT_RANGES: dict[str, list[tuple[int, int]]] = {
    "Latn": [(0x0041, 0x005A), (0x0061, 0x007A), (0x00C0, 0x024F)],
    "Deva": [(0x0900, 0x097F), (0xA8E0, 0xA8FF)],
    "Beng": [(0x0980, 0x09FF)],
    "Gujr": [(0x0A80, 0x0AFF)],
    "Guru": [(0x0A00, 0x0A7F)],
    "Knda": [(0x0C80, 0x0CFF)],
    "Mlym": [(0x0D00, 0x0D7F)],
    "Orya": [(0x0B00, 0x0B7F)],
    "Taml": [(0x0B80, 0x0BFF)],
    "Telu": [(0x0C00, 0x0C7F)],
    "Arab": [(0x0600, 0x06FF), (0x0750, 0x077F)],
    "Olck": [(0x1C50, 0x1C7F)],
    "Mtei": [(0xABC0, 0xABFF), (0xAAE0, 0xAAFF)],
}


def script_subtag(flores_code: str) -> str:
    return flores_code.split("_", 1)[1]


def script_fraction(text: str, subtag: str) -> float:
    """Fraction of alphabetic characters belonging to the given script."""
    ranges = SCRIPT_RANGES[subtag]
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    in_script = sum(1 for c in letters if any(lo <= ord(c) <= hi for lo, hi in ranges))
    return in_script / len(letters)


class PairFilter:
    """Applies the cleaning rules from configs/data.yaml. check() returns a
    rejection reason string, or None when the pair is clean."""

    def __init__(self, cleaning: dict[str, Any]):
        self.min_chars = cleaning.get("min_chars", 3)
        self.max_chars = cleaning.get("max_chars", 1024)
        self.max_length_ratio = cleaning.get("max_length_ratio", 3.0)
        self.min_script_fraction = cleaning.get("min_script_fraction", 0.5)

    def check(self, entry: CorpusEntry) -> str | None:
        src, tgt = entry.src_text, entry.tgt_text
        if len(src) < self.min_chars or len(tgt) < self.min_chars:
            return "too_short"
        if len(src) > self.max_chars or len(tgt) > self.max_chars:
            return "too_long"
        if src == tgt:
            return "identical_src_tgt"
        ratio = max(len(src), len(tgt)) / min(len(src), len(tgt))
        if ratio > self.max_length_ratio:
            return "length_ratio"
        if script_fraction(src, script_subtag(entry.src_lang)) < self.min_script_fraction:
            return "src_wrong_script"
        if script_fraction(tgt, script_subtag(entry.tgt_lang)) < self.min_script_fraction:
            return "tgt_wrong_script"
        return None

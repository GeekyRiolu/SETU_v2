"""Text normalisation for parallel corpora.

Conservative on purpose: Unicode NFC, whitespace collapsing, and removal of
formatting control characters. ZWJ/ZWNJ are KEPT — they are meaningful in
Indic scripts (conjunct control), stripping them corrupts text.
"""

from __future__ import annotations

import re
import unicodedata

# Formatting/control chars that are never linguistic: BOM, bidi marks,
# soft hyphen, word joiner. NOT zwj/zwnj (U+200C/U+200D).
_STRIP_CHARS = re.compile("[­​‎‏⁠﻿؜‪-‮]")

_WHITESPACE = re.compile(r"\s+")

# Curly quotes and unicode dashes to plain ASCII equivalents.
_PUNCT_MAP = str.maketrans({
    "‘": "'", "’": "'", "‚": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-",
    "…": "...",
})


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = _STRIP_CHARS.sub("", text)
    text = text.translate(_PUNCT_MAP)
    text = _WHITESPACE.sub(" ", text)
    return text.strip()

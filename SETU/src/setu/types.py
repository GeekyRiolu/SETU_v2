"""Core data objects shared by every SETU module.

Field names are part of the contract between modules — renaming one here
without updating every consumer causes silent breakage. Keep them stable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CorpusEntry:
    """One aligned sentence pair from a parallel corpus."""

    src_lang: str
    tgt_lang: str
    src_text: str
    tgt_text: str
    source: str  # corpus of origin, e.g. "bpcc", "samanantar"


@dataclass
class PreferencePair:
    """A preferred/dispreferred translation pair for DPO training."""

    src_text: str
    src_lang: str
    tgt_lang: str
    preferred_tgt: str
    dispreferred_tgt: str
    quality_delta: float  # ChrF(preferred) - ChrF(dispreferred); must be > 0


@dataclass
class ModelConfig:
    """Configuration of one student model."""

    language_pair: str  # e.g. "hin_Deva-eng_Latn"
    params: dict[str, Any] = field(default_factory=dict)
    quantization: dict[str, Any] = field(default_factory=dict)


@dataclass
class TranslationResult:
    """Output of the inference engine, shared by all four interfaces."""

    translated_text: str
    src_lang: str
    tgt_lang: str
    bleu: float | None = None
    chrf: float | None = None
    latency_ms: float | None = None

"""Route a translation to the right student.

Uses the directly-trained model for a pair when it exists, otherwise pivots
through English (source -> English -> target) using the two half-models. Shared
by every interface (REST, CLI, ...) so routing logic lives in exactly one place.
"""

from __future__ import annotations

from functools import lru_cache

from setu.config import load_languages, resolve_language
from setu.inference.engine import InferenceEngine
from setu.types import ModelConfig, TranslationResult


@lru_cache(maxsize=None)
def engine_for_pair(pair: str) -> InferenceEngine:
    """One cached engine per language pair; a pair with no model stays a stub."""
    return InferenceEngine(ModelConfig(language_pair=pair))


def _available(pair: str) -> bool:
    return not engine_for_pair(pair).is_stub


def translate(text: str, src_lang: str, tgt_lang: str) -> tuple[TranslationResult, str | None, bool]:
    """Translate ``text`` from ``src_lang`` to ``tgt_lang`` (ISO or FLORES codes).

    Returns ``(result, pivot, stub)`` where ``pivot`` is ``"en"`` when the text
    was routed through English and ``stub`` is True when no direct or pivot model
    exists (the engine passes the text through). Raises ValueError on unknown or
    identical language codes.
    """
    src = resolve_language(src_lang)
    tgt = resolve_language(tgt_lang)
    if src["iso"] == tgt["iso"]:
        raise ValueError(f"Source and target language are both {src['iso']!r}")

    direct = f"{src['flores']}-{tgt['flores']}"
    if _available(direct):
        return engine_for_pair(direct).translate(text, src["iso"], tgt["iso"]), None, False

    # English pivot for Indic<->Indic when both halves are trained
    eng = load_languages()["en"]["flores"]  # eng_Latn
    if src["iso"] != "en" and tgt["iso"] != "en":
        hop1, hop2 = f"{src['flores']}-{eng}", f"{eng}-{tgt['flores']}"
        if _available(hop1) and _available(hop2):
            r1 = engine_for_pair(hop1).translate(text, src["iso"], "en")
            r2 = engine_for_pair(hop2).translate(r1.translated_text, "en", tgt["iso"])
            latency = (r1.latency_ms or 0.0) + (r2.latency_ms or 0.0)
            return (
                TranslationResult(
                    translated_text=r2.translated_text,
                    src_lang=src["iso"], tgt_lang=tgt["iso"], latency_ms=latency,
                ),
                "en",
                False,
            )

    # nothing trained for this pair (or its pivot) -> passthrough stub
    return engine_for_pair(direct).translate(text, src["iso"], tgt["iso"]), None, True

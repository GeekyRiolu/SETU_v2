"""The single translation engine every interface (REST, CLI, SDK, PWA) calls.

M0 stub: validates the language pair and returns the input text as a
passthrough "translation" so the whole pipeline is callable end-to-end.
Replaced by the quantised ONNX student in M5. The inference path must stay
fully offline — no network calls may ever be added here.
"""

from __future__ import annotations

import time

from setu.config import load_model_config, resolve_language
from setu.types import ModelConfig, TranslationResult

STUB_ENGINE = True  # flipped off when the real ONNX engine lands in M5


class InferenceEngine:
    def __init__(self, config: ModelConfig | None = None):
        self.config = config or load_model_config()

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> TranslationResult:
        """Translate ``text`` from ``src_lang`` to ``tgt_lang``.

        Accepts ISO ("hi") or FLORES ("hin_Deva") codes. Raises ValueError on
        unknown codes or identical source/target.
        """
        src = resolve_language(src_lang)
        tgt = resolve_language(tgt_lang)
        if src["iso"] == tgt["iso"]:
            raise ValueError(f"Source and target language are both {src['iso']!r}")

        start = time.perf_counter()
        translated = text  # passthrough until the ONNX student replaces this stub
        latency_ms = (time.perf_counter() - start) * 1000

        return TranslationResult(
            translated_text=translated,
            src_lang=src["iso"],
            tgt_lang=tgt["iso"],
            bleu=None,
            chrf=None,
            latency_ms=latency_ms,
        )

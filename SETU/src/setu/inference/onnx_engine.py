"""ONNX-backed inference — the real engine behind InferenceEngine once a
quantised student exists.

Fully offline: ONNX Runtime executes locally and the tokenizer is a local
SentencePiece model. No class here makes a network call; the InferenceEngine
offline guard (and a networking-disabled test) enforce that.
"""

from __future__ import annotations

import time
from pathlib import Path

from setu.config import resolve_language
from setu.training.dataset import _truncate
from setu.training.tokenizer import BOS, EOS, StudentTokenizer
from setu.types import TranslationResult


class ONNXTranslator:
    def __init__(self, model_dir: Path | str, tokenizer_model: Path | str, max_length: int = 128):
        from optimum.onnxruntime import ORTModelForSeq2SeqLM

        self.model = ORTModelForSeq2SeqLM.from_pretrained(str(model_dir))
        self.tokenizer = StudentTokenizer(tokenizer_model)
        self.max_length = max_length

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> TranslationResult:
        import torch

        src = resolve_language(src_lang)
        tgt = resolve_language(tgt_lang)
        if src["iso"] == tgt["iso"]:
            raise ValueError(f"Source and target language are both {src['iso']!r}")

        start = time.perf_counter()
        max_pos = getattr(self.model.config, "max_position_embeddings", self.max_length)
        ids = _truncate(self.tokenizer.encode_source(text, src["flores"], tgt["flores"]), max_pos)
        input_ids = torch.tensor([ids], dtype=torch.long)
        attention_mask = torch.ones_like(input_ids)
        generated = self.model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_length=min(self.max_length, max_pos),
            num_beams=1,
            decoder_start_token_id=BOS,
            eos_token_id=EOS,
            pad_token_id=0,
        )
        out_ids = generated[0].tolist() if hasattr(generated[0], "tolist") else list(generated[0])
        translated = self.tokenizer.decode(out_ids)
        latency_ms = (time.perf_counter() - start) * 1000

        return TranslationResult(
            translated_text=translated,
            src_lang=src["iso"], tgt_lang=tgt["iso"],
            latency_ms=latency_ms,
        )

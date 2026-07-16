"""IndicTrans2 teacher backend.

THIS IS THE ONLY FILE in SETU allowed to import IndicTrans2 internals
(transformers checkpoints with its remote code, IndicTransToolkit, torch).
A test enforces that wall.

Local clone: the repo root two levels up provides the reference implementation
(`huggingface_interface/example.py`); the actual weights come from the official
AI4Bharat HF checkpoints configured in configs/teacher.yaml.
"""

from __future__ import annotations

from typing import Any

from setu.config import _load_yaml, resolve_language
from setu.teacher.base import TeacherModel


class IndicTrans2Teacher(TeacherModel):
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or _load_yaml("teacher.yaml")
        self._models: dict[str, tuple[Any, Any]] = {}  # direction -> (tokenizer, model)
        self._processor: Any = None

    # --- direction routing --------------------------------------------------

    @staticmethod
    def _direction(src_flores: str, tgt_flores: str) -> str:
        if src_flores == "eng_Latn":
            return "en-indic"
        if tgt_flores == "eng_Latn":
            return "indic-en"
        return "indic-indic"

    # --- lazy loading -------------------------------------------------------

    def _processor_instance(self) -> Any:
        if self._processor is None:
            from IndicTransToolkit.processor import IndicProcessor

            self._processor = IndicProcessor(inference=True)
        return self._processor

    def _load(self, direction: str) -> tuple[Any, Any]:
        if direction not in self._models:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            checkpoint = self.config["checkpoints"][direction]
            if not checkpoint:
                raise ValueError(
                    f"No teacher checkpoint configured for direction {direction!r} "
                    "(see configs/teacher.yaml — the gated ai4bharat checkpoint "
                    "needs HF login + accepted terms)"
                )
            tokenizer = AutoTokenizer.from_pretrained(checkpoint, trust_remote_code=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                checkpoint, trust_remote_code=True, low_cpu_mem_usage=True
            )
            model.to(self.config.get("device", "cpu"))
            model.eval()
            self._models[direction] = (tokenizer, model)
        return self._models[direction]

    # --- TeacherModel interface ----------------------------------------------

    def generate_candidates(
        self, src_text: str, src_lang: str, tgt_lang: str, n: int = 4
    ) -> list[str]:
        return self.generate_candidates_batch([src_text], src_lang, tgt_lang, n)[0]

    def generate_candidates_batch(
        self, src_texts: list[str], src_lang: str, tgt_lang: str, n: int = 4
    ) -> list[list[str]]:
        import torch

        src_flores = resolve_language(src_lang)["flores"]
        tgt_flores = resolve_language(tgt_lang)["flores"]
        direction = self._direction(src_flores, tgt_flores)
        tokenizer, model = self._load(direction)
        processor = self._processor_instance()

        gen = self.config.get("generation", {})
        num_beams = max(gen.get("num_beams", 5), n)

        batch = processor.preprocess_batch(src_texts, src_lang=src_flores, tgt_lang=tgt_flores)
        inputs = tokenizer(
            batch, truncation=True, padding="longest",
            return_tensors="pt", return_attention_mask=True,
        ).to(model.device)

        with torch.no_grad():
            generated = model.generate(
                **inputs,
                use_cache=True,
                min_length=0,
                max_length=gen.get("max_length", 256),
                num_beams=num_beams,
                num_return_sequences=n,
            )

        decoded = tokenizer.batch_decode(
            generated, skip_special_tokens=True, clean_up_tokenization_spaces=True
        )
        # num_return_sequences here is load-bearing: postprocess_batch pops one
        # entity-placeholder map per INPUT from an internal blocking queue; with
        # the default (1) it would try to pop len(decoded) maps and deadlock.
        candidates = processor.postprocess_batch(
            decoded, lang=tgt_flores, num_return_sequences=n
        )
        # generate() returns n sequences per input, flattened in input order
        return [candidates[i * n:(i + 1) * n] for i in range(len(src_texts))]

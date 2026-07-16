"""Evaluation harness: BLEU, ChrF, and latency for a student model.

Reports the four-target-relevant numbers and, when a teacher score is supplied,
the student/teacher BLEU ratio the ≥80% quality target is measured against.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from setu.types import TranslationResult


def corpus_bleu_chrf(hypotheses: list[str], references: list[str]) -> dict[str, float]:
    from sacrebleu.metrics import BLEU, CHRF

    refs = [references]  # sacrebleu wants list-of-reference-streams
    return {
        "bleu": BLEU().corpus_score(hypotheses, refs).score,
        "chrf": CHRF().corpus_score(hypotheses, refs).score,
    }


def evaluate_model(
    translate_fn: Callable[[str], str],
    sources: list[str],
    references: list[str],
    teacher_bleu: float | None = None,
) -> dict[str, Any]:
    """translate_fn maps a source sentence to a hypothesis. Returns metrics +
    mean latency; if teacher_bleu given, adds bleu_ratio vs the ≥0.80 target."""
    hyps, latencies = [], []
    for src in sources:
        t0 = time.perf_counter()
        hyps.append(translate_fn(src))
        latencies.append((time.perf_counter() - t0) * 1000)

    scores = corpus_bleu_chrf(hyps, references)
    result = {
        **scores,
        "latency_ms_mean": sum(latencies) / len(latencies),
        "latency_ms_max": max(latencies),
        "n": len(sources),
    }
    if teacher_bleu:
        result["teacher_bleu"] = teacher_bleu
        result["bleu_ratio"] = scores["bleu"] / teacher_bleu if teacher_bleu else 0.0
        result["meets_quality_target"] = result["bleu_ratio"] >= 0.80
    return result


def to_translation_result(
    hypothesis: str, src_lang: str, tgt_lang: str, metrics: dict[str, Any], latency_ms: float
) -> TranslationResult:
    return TranslationResult(
        translated_text=hypothesis,
        src_lang=src_lang,
        tgt_lang=tgt_lang,
        bleu=metrics.get("bleu"),
        chrf=metrics.get("chrf"),
        latency_ms=latency_ms,
    )

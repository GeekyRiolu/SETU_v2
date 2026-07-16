"""Eval harness tests — pure metric math, no model."""

import pytest

pytest.importorskip("sacrebleu")

from setu.eval.metrics import corpus_bleu_chrf, evaluate_model


def test_perfect_translation_scores_high():
    refs = ["The weather is nice today.", "I like reading books."]
    scores = corpus_bleu_chrf(refs, refs)
    assert scores["bleu"] > 99
    assert scores["chrf"] > 99


def test_evaluate_model_reports_targets():
    sources = ["a", "b"]
    references = ["The cat sat.", "The dog ran."]
    result = evaluate_model(
        translate_fn=lambda s: "The cat sat." if s == "a" else "The dog ran.",
        sources=sources, references=references, teacher_bleu=50.0,
    )
    assert result["n"] == 2
    assert result["latency_ms_mean"] >= 0
    assert result["bleu_ratio"] == result["bleu"] / 50.0
    assert result["meets_quality_target"] is True  # perfect hyps beat 80% of 50


def test_quality_target_gate():
    result = evaluate_model(
        translate_fn=lambda s: "wrong output entirely",
        sources=["x"], references=["completely different reference text"],
        teacher_bleu=50.0,
    )
    assert result["meets_quality_target"] is False

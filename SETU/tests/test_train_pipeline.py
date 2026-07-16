"""M4 end-to-end integration: tokenizer -> SFT -> DPO -> eval, on a tiny model
and synthetic data. Slow-ish but no downloads; proves the whole pipeline wires
together and emits real (small) metrics.
"""

import dataclasses
import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")
pytest.importorskip("sentencepiece")

from setu.config import config_dir
from setu.types import CorpusEntry, PreferencePair

EN = ["the sun is bright", "she reads many books", "we walk in the park",
      "the food tastes good", "birds sing every morning", "the river flows fast"]
HI = ["सूरज चमकीला है", "वह बहुत किताबें पढ़ती है", "हम पार्क में चलते हैं",
      "खाना स्वादिष्ट है", "पक्षी हर सुबह गाते हैं", "नदी तेज़ बहती है"]


@pytest.fixture
def tiny_project(tmp_path, monkeypatch):
    # config dir: real languages.yaml + tiny model/training
    cfg = tmp_path / "configs"
    cfg.mkdir()
    shutil.copy(config_dir() / "languages.yaml", cfg / "languages.yaml")
    (cfg / "model.yaml").write_text(
        "language_pair: hin_Deva-eng_Latn\n"
        "params: {architecture: transformer, encoder_layers: 1, decoder_layers: 1,\n"
        "  hidden_size: 32, ffn_size: 64, attention_heads: 2, vocab_size: 120, max_seq_len: 32}\n"
        "quantization: {mode: none, format: onnx}\n", encoding="utf-8")
    (cfg / "training.yaml").write_text(
        "seed: 42\n"
        "sft: {epochs: 2, lr: 0.001, batch_size: 4, warmup_steps: 0}\n"
        "dpo: {beta: 0.1, lr: 0.0005, epochs: 1, batch_size: 4, reference_checkpoint: null}\n",
        encoding="utf-8")
    monkeypatch.setenv("SETU_CONFIG_DIR", str(cfg))

    # data: corpus + preferences (repeat for enough rows)
    pair = "hin_Deva-eng_Latn"
    corpus_dir = tmp_path / "data" / "processed" / pair
    corpus_dir.mkdir(parents=True)
    with open(corpus_dir / "train.jsonl", "w", encoding="utf-8") as f:
        for _ in range(20):
            for en, hi in zip(EN, HI):
                e = CorpusEntry("hin_Deva", "eng_Latn", hi, en, "synthetic")
                f.write(json.dumps(dataclasses.asdict(e), ensure_ascii=False) + "\n")

    pref_dir = tmp_path / "data" / "preferences" / pair
    pref_dir.mkdir(parents=True)
    with open(pref_dir / "pairs.jsonl", "w", encoding="utf-8") as f:
        for en, hi in zip(EN, HI):
            p = PreferencePair(hi, "hin_Deva", "eng_Latn", en, "zzz wrong output", 40.0)
            f.write(json.dumps(dataclasses.asdict(p), ensure_ascii=False) + "\n")

    return tmp_path


def test_full_training_pipeline(tiny_project):
    from setu.training.pipeline import run

    report = run(
        pair="hin_Deva-eng_Latn", limit=60,
        ckpt_root=tiny_project / "checkpoints", data_root=tiny_project / "data",
        dev_size=6, teacher_bleu=30.0,
    )

    assert report["student_params"] > 0
    assert report["train_entries"] > 0 and report["dev_entries"] == 6
    assert report["sft_final_loss"] is not None
    # eval ran and produced the target-relevant fields on real (tiny) output
    assert "bleu" in report["sft_eval"] and "latency_ms_mean" in report["sft_eval"]
    assert "bleu_ratio" in report["sft_eval"]
    assert "dpo_eval" in report and "bleu" in report["dpo_eval"]

    ck = tiny_project / "checkpoints" / "hin_Deva-eng_Latn"
    assert (ck / "sft" / "model.safetensors").exists()
    assert (ck / "dpo" / "model.safetensors").exists()
    assert (ck / "train_report.json").exists()

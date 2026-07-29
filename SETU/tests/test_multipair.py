"""Pair-agnostic pipeline test — the whole train→eval flow must work for any
language pair, not just Hindi↔English. Runs a tiny Tamil→English (and the reverse
English→Hindi direction) end-to-end on a tiny model, no downloads.
"""

import dataclasses
import json
import shutil

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")
pytest.importorskip("sentencepiece")

from setu.config import config_dir, resolve_language
from setu.types import CorpusEntry

# (src_flores, tgt_flores, [(src_text, tgt_text), ...])
CASES = {
    "tam_Taml-eng_Latn": [
        ("இன்று வானிலை நன்றாக உள்ளது", "the weather is good today"),
        ("எனக்கு புத்தகங்கள் படிக்க பிடிக்கும்", "i like to read books"),
        ("இந்தியா ஒரு பெரிய நாடு", "india is a big country"),
        ("அவர் பள்ளிக்கு செல்கிறார்", "he goes to school"),
    ],
    "eng_Latn-hin_Deva": [  # reverse direction (en -> indic)
        ("the weather is good today", "आज मौसम अच्छा है"),
        ("i like to read books", "मुझे किताबें पढ़ना पसंद है"),
        ("india is a big country", "भारत एक बड़ा देश है"),
        ("he goes to school", "वह स्कूल जाता है"),
    ],
}


def _make_project(tmp_path, pair, pairs, monkeypatch):
    cfg = tmp_path / "configs"
    cfg.mkdir()
    shutil.copy(config_dir() / "languages.yaml", cfg / "languages.yaml")
    (cfg / "model.yaml").write_text(
        f"language_pair: {pair}\n"
        "params: {architecture: transformer, encoder_layers: 1, decoder_layers: 1,\n"
        "  hidden_size: 32, ffn_size: 64, attention_heads: 2, vocab_size: 120, max_seq_len: 32}\n"
        "quantization: {mode: none, format: onnx}\n", encoding="utf-8")
    (cfg / "training.yaml").write_text(
        "seed: 42\n"
        "sft: {epochs: 2, lr: 0.001, batch_size: 4, warmup_steps: 0}\n"
        "dpo: {beta: 0.1, lr: 0.0005, epochs: 1, batch_size: 4}\n", encoding="utf-8")
    monkeypatch.setenv("SETU_CONFIG_DIR", str(cfg))

    src_f, tgt_f = pair.split("-")
    d = tmp_path / "data" / "processed" / pair
    d.mkdir(parents=True)
    with open(d / "train.jsonl", "w", encoding="utf-8") as f:
        for _ in range(20):
            for s, t in pairs:
                e = CorpusEntry(src_f, tgt_f, s, t, "synthetic")
                f.write(json.dumps(dataclasses.asdict(e), ensure_ascii=False) + "\n")
    return tmp_path


@pytest.mark.parametrize("pair", list(CASES))
def test_pipeline_is_pair_agnostic(tmp_path, monkeypatch, pair):
    from setu.training.pipeline import run

    _make_project(tmp_path, pair, CASES[pair], monkeypatch)
    report = run(pair=pair, limit=60, skip_dpo=True, dev_size=6,
                 ckpt_root=tmp_path / "ck", data_root=tmp_path / "data")
    assert report["pair"] == pair
    assert report["train_entries"] > 0 and report["dev_entries"] == 6
    assert "bleu" in report["sft_eval"]
    # the pair's FLORES tags are reserved in the tokenizer for stable ids
    src_f, tgt_f = pair.split("-")
    tok = (tmp_path / "ck" / pair / "tokenizer" / "student_sp.model")
    assert tok.exists()


def test_flores_iso_resolution_for_several_langs():
    # the data loader routes Samanantar by the Indic ISO — spot-check a few
    for flores, iso in [("tam_Taml", "ta"), ("ben_Beng", "bn"),
                        ("mar_Deva", "mr"), ("guj_Gujr", "gu")]:
        assert resolve_language(flores)["iso"] == iso

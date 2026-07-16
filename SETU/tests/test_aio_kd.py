"""M7 AIO-KD tests — balancing math + a tiny multi-direction training loop."""

import pytest

from setu.training.aio_kd import balancing_weights


def test_balancing_protects_low_resource():
    sizes = {"hi-en": 10000, "brx-en": 100}
    proportional = balancing_weights(sizes, temperature=1.0)
    balanced = balancing_weights(sizes, temperature=5.0)
    # higher temperature raises the low-resource share
    assert balanced["brx-en"] > proportional["brx-en"]
    # still a valid distribution
    assert abs(sum(balanced.values()) - 1.0) < 1e-9


def test_uniform_at_high_temperature():
    sizes = {"a": 900, "b": 100}
    near_uniform = balancing_weights(sizes, temperature=1000.0)
    assert abs(near_uniform["a"] - near_uniform["b"]) < 0.05


def test_empty_raises():
    with pytest.raises(ValueError):
        balancing_weights({"a": 0}, temperature=1.0)


def test_orchestrator_trains_and_covers_all_directions():
    torch = pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from setu.training.aio_kd import AIOKDOrchestrator
    from setu.training.student import build_student
    from setu.training.dataset import CorpusDataset
    from setu.training.tokenizer import StudentTokenizer
    from setu.types import CorpusEntry, ModelConfig

    # reuse a real tiny tokenizer trained on a couple of scripts
    import tempfile, random
    from pathlib import Path
    d = Path(tempfile.mkdtemp())
    random.seed(0)
    en = "the sun is bright and warm today over the green hills".split()
    hi = "सूरज आज हरी पहाड़ियों पर चमकीला और गर्म है".split()
    ta = "இன்று சூரியன் பசுமையான மலைகளில் பிரகாசமாக உள்ளது".split()
    lines = []
    for _ in range(200):
        lines += [" ".join(random.sample(en, 5)), " ".join(random.sample(hi, 5)), " ".join(random.sample(ta, 5))]
    (d / "c.txt").write_text("\n".join(lines), encoding="utf-8")
    tok = StudentTokenizer.train(d / "c.txt", d / "tok", vocab_size=180)

    def ds_for(src_flores, texts_src, texts_tgt):
        entries = [CorpusEntry(src_flores, "eng_Latn", s, t, "syn")
                   for s, t in zip(texts_src * 20, texts_tgt * 20)]
        return CorpusDataset.from_entries(entries, tok)

    datasets = {
        "hin_Deva-eng_Latn": ds_for("hin_Deva", hi, en),
        "tam_Taml-eng_Latn": ds_for("tam_Taml", ta, en),
    }
    mc = ModelConfig("multi", dict(hidden_size=32, encoder_layers=1, decoder_layers=1,
                                   attention_heads=2, ffn_size=64, max_seq_len=32), {})
    model = build_student(tok.vocab_size, mc)

    orch = AIOKDOrchestrator(model, datasets, {"sampling_temperature": 1.5, "lr": 1e-3, "batch_size": 4})
    history = orch.train(steps=20)
    assert len(history) == 20
    # both directions were trained on (coverage report is non-trivial)
    assert set(orch.coverage()) == {"hin_Deva-eng_Latn", "tam_Taml-eng_Latn"}
    assert all(v > 0 for v in orch.coverage().values())

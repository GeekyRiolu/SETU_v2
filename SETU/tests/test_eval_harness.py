"""Track B eval tests — test-set loaders (mocked), bootstrap significance (real),
and the setu-eval CLI wiring (fake test set + stub engine). No downloads.
"""

import json

import pytest

pytest.importorskip("sacrebleu")

from setu.eval.significance import paired_bootstrap
from setu.eval.testsets import _text_field, load_flores, load_testset


# --- test-set loaders (mock datasets.load_dataset) --------------------------

def _fake_flores(monkeypatch, field="sentence"):
    data = {
        "hin_Deva": [{field: "नमस्ते दुनिया"}, {field: "यह एक परीक्षण है"}],
        "eng_Latn": [{field: "hello world"}, {field: "this is a test"}],
    }

    def fake_load_dataset(dataset, config, split=None):
        return data[config]

    monkeypatch.setattr("datasets.load_dataset", fake_load_dataset)


def test_load_flores_aligns_src_and_tgt(monkeypatch):
    _fake_flores(monkeypatch)
    srcs, refs = load_flores("hin_Deva-eng_Latn", split="devtest")
    assert srcs == ["नमस्ते दुनिया", "यह एक परीक्षण है"]
    assert refs == ["hello world", "this is a test"]


def test_load_flores_handles_text_field(monkeypatch):
    _fake_flores(monkeypatch, field="text")  # flores_plus layout
    srcs, refs = load_flores("hin_Deva-eng_Latn")
    assert srcs[0] == "नमस्ते दुनिया" and refs[0] == "hello world"


def test_text_field_detection():
    assert _text_field({"sentence": "x"}) == "sentence"
    assert _text_field({"text": "x"}) == "text"
    with pytest.raises(KeyError):
        _text_field({"other": "x"})


def test_load_testset_unknown_name():
    with pytest.raises(ValueError):
        load_testset("nope", "hin_Deva-eng_Latn")


# --- paired bootstrap significance ------------------------------------------

def test_bootstrap_detects_clear_winner():
    refs = ["the cat sat on the mat"] * 20
    good = ["the cat sat on the mat"] * 20          # perfect
    bad = ["dog"] * 20                               # terrible
    r = paired_bootstrap(good, bad, refs, n_samples=200)
    assert r["system_a"] > r["system_b"]
    assert r["delta"] > 0
    assert r["a_win_rate"] == 1.0 and r["significant_at_0.05"]


def test_bootstrap_deterministic_and_tie():
    refs = ["alpha beta gamma"] * 15
    same = ["alpha beta"] * 15
    r1 = paired_bootstrap(same, same, refs, n_samples=100)
    r2 = paired_bootstrap(same, same, refs, n_samples=100)
    assert r1 == r2                       # seeded -> reproducible
    assert r1["delta"] == 0.0 and not r1["significant_at_0.05"]


def test_bootstrap_length_mismatch():
    with pytest.raises(ValueError):
        paired_bootstrap(["a"], ["b", "c"], ["r", "r"])


# --- setu-eval CLI wiring (fake test set + stub engine) ---------------------

def test_setu_eval_happy_path(tmp_path, monkeypatch):
    import setu.inference.engine as eng_mod
    from setu.eval import cli
    from setu.types import TranslationResult

    # fake FLORES: source == reference, so a passthrough engine scores BLEU 100
    src = ["the weather is nice", "i like books", "india is large"]
    monkeypatch.setattr(cli, "load_testset", lambda name, pair, split: (src, list(src)))

    class FakeEngine:
        is_stub = False
        def __init__(self, *a, **k): pass
        def translate(self, text, s, t):
            return TranslationResult(text, s, t)  # passthrough -> hyp == ref

    monkeypatch.setattr(eng_mod, "InferenceEngine", FakeEngine)
    report = cli.run(pair="hin_Deva-eng_Latn", testset="flores",
                     out=str(tmp_path / "eval.json"))
    assert report["n"] == 3
    assert report["student"]["bleu"] > 99 and "chrf" in report["student"]
    assert json.load(open(report["report_path"]))["testset"] == "flores"


def test_setu_eval_errors_without_a_model(tmp_path, monkeypatch):
    from setu.eval import cli

    monkeypatch.setattr(cli, "load_testset", lambda name, pair, split: (["a"], ["a"]))
    # empty models dir -> engine is a stub -> clear RuntimeError, not a crash
    with pytest.raises(RuntimeError):
        cli.run(pair="hin_Deva-eng_Latn", testset="flores",
                models_root=str(tmp_path / "empty"))

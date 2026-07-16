"""M0 smoke tests: package imports, config loads, stub engine translates."""

import dataclasses

import pytest

import setu
from setu import InferenceEngine, TranslationResult
from setu.cli import main
from setu.config import load_languages, load_model_config, load_training_config, resolve_language


def test_package_imports():
    assert setu.__version__


def test_language_registry_covers_all_22_plus_pivot():
    registry = load_languages()
    assert len(registry) == 23  # 22 scheduled languages + English pivot
    assert registry["en"]["flores"] == "eng_Latn"
    assert registry["hi"]["flores"] == "hin_Deva"
    for lang in registry.values():
        assert lang["name"] and lang["iso"] and lang["flores"] and lang["script"]


def test_resolve_language_accepts_iso_and_flores():
    assert resolve_language("hi")["name"] == "Hindi"
    assert resolve_language("hin_Deva")["name"] == "Hindi"
    assert resolve_language("kas_Deva")["name"] == "Kashmiri"  # alt script
    with pytest.raises(ValueError):
        resolve_language("xx")


def test_model_config_is_config_driven():
    config = load_model_config()
    assert config.language_pair == "hin_Deva-eng_Latn"
    assert config.quantization["mode"] == "none"
    assert load_training_config()["dpo"]["beta"] == 0.1


def test_stub_engine_translates_passthrough():
    result = InferenceEngine().translate("नमस्ते दुनिया", "hi", "en")
    assert isinstance(result, TranslationResult)
    assert result.translated_text == "नमस्ते दुनिया"  # M0 passthrough
    assert result.src_lang == "hi"
    assert result.tgt_lang == "en"
    assert result.latency_ms is not None and result.latency_ms >= 0
    # Contract fields all present
    assert {f.name for f in dataclasses.fields(result)} == {
        "translated_text", "src_lang", "tgt_lang", "bleu", "chrf", "latency_ms",
    }


def test_engine_rejects_bad_pairs():
    engine = InferenceEngine()
    with pytest.raises(ValueError):
        engine.translate("hello", "hi", "hi")
    with pytest.raises(ValueError):
        engine.translate("hello", "zz", "en")


def test_cli_end_to_end(capsys):
    assert main(["--src", "hi", "--tgt", "en", "--text", "नमस्ते"]) == 0
    assert "नमस्ते" in capsys.readouterr().out
    assert main(["--src", "hi", "--tgt", "hi", "--text", "x"]) == 2

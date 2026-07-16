"""M1 corpus pipeline tests — run entirely on local fixtures, no network."""

import json

import pytest

from setu.corpus.dedup import Deduplicator
from setu.corpus.filters import PairFilter, script_fraction
from setu.corpus.normalize import normalize_text
from setu.corpus.pipeline import CorpusPipeline
from setu.types import CorpusEntry

GOOD_ROWS = [
    ("The weather is nice today.", "आज मौसम अच्छा है।"),
    ("India has twenty-two scheduled languages.", "भारत में बाईस अनुसूचित भाषाएँ हैं।"),
]


@pytest.fixture
def corpus_dir(tmp_path):
    rows = GOOD_ROWS + [
        GOOD_ROWS[0],                                # exact duplicate
        ("Completely English pair", "Also English"),  # tgt wrong script
        ("Tiny", "यह एक बहुत ही लंबा और असंतुलित वाक्य है जो अनुपात जाँच में विफल होना चाहिए क्योंकि यह स्रोत से कहीं अधिक लंबा है।"),  # length ratio
        ("ab", "कख"),                                 # too short
        ("नमस्ते दुनिया", "नमस्ते दुनिया"),               # identical src == tgt
    ]
    tsv = tmp_path / "fixture.tsv"
    tsv.write_text("\n".join(f"{e}\t{i}" for e, i in rows), encoding="utf-8")
    return tmp_path


def data_config(path="fixture.tsv"):
    return {
        "sources": [{"name": "fixture", "type": "tsv", "path": path, "columns": ["eng", "indic"]}],
        "cleaning": {"min_chars": 3, "max_chars": 1024, "max_length_ratio": 3.0, "min_script_fraction": 0.5},
    }


def test_normalize_text():
    assert normalize_text("“Hello”…  world‎") == '"Hello"... world'
    assert normalize_text("  a\t\nb  ") == "a b"
    # ZWNJ is linguistic in Indic scripts and must survive
    assert "‌" in normalize_text("क‌ख")


def test_script_fraction():
    assert script_fraction("आज मौसम अच्छा है", "Deva") == 1.0
    assert script_fraction("hello world", "Deva") == 0.0
    # matras are combining marks, not alpha: दुनिया contributes 3 base letters
    assert script_fraction("hello दुनिया", "Deva") == pytest.approx(3 / 8)


def test_filter_reasons():
    f = PairFilter({"min_chars": 3, "max_length_ratio": 3.0, "min_script_fraction": 0.5})
    make = lambda s, t: CorpusEntry("hin_Deva", "eng_Latn", s, t, "x")
    assert f.check(make("आज मौसम अच्छा है।", "The weather is nice.")) is None
    assert f.check(make("कख", "ab")) == "too_short"
    assert f.check(make("नमस्ते", "नमस्ते")) == "identical_src_tgt"
    assert f.check(make("hello there friend", "Hello there!")) == "src_wrong_script"


def test_dedup():
    d = Deduplicator()
    e = CorpusEntry("hin_Deva", "eng_Latn", "नमस्ते", "hello", "x")
    assert not d.is_duplicate(e)
    assert d.is_duplicate(CorpusEntry("hin_Deva", "eng_Latn", "नमस्ते", "hello", "y"))
    assert len(d) == 1


def test_pipeline_end_to_end(corpus_dir):
    pipeline = CorpusPipeline(
        data_config=data_config(), pair="hin_Deva-eng_Latn",
        base_dir=corpus_dir, output_dir=corpus_dir / "processed",
    )
    report = pipeline.run()

    assert report["raw_total"] == 7
    assert report["kept_total"] == 2
    assert report["duplicates"] == 1
    # hin->eng orientation puts the (English-text) indic column on the src side
    assert report["rejections"] == {
        "src_wrong_script": 1, "length_ratio": 1, "too_short": 1, "identical_src_tgt": 1,
    }

    entries = [json.loads(l) for l in open(report["output"], encoding="utf-8")]
    assert len(entries) == 2
    # Requested direction hin->eng: Hindi text on the src side
    assert entries[0]["src_lang"] == "hin_Deva"
    assert entries[0]["src_text"] == "आज मौसम अच्छा है।"
    assert entries[0]["tgt_text"] == "The weather is nice today."
    assert entries[0]["source"] == "fixture"
    assert (corpus_dir / "processed" / "hin_Deva-eng_Latn" / "report.md").exists()


def test_pipeline_reverse_direction(corpus_dir):
    report = CorpusPipeline(
        data_config=data_config(), pair="eng_Latn-hin_Deva",
        base_dir=corpus_dir, output_dir=corpus_dir / "processed",
    ).run()
    entries = [json.loads(l) for l in open(report["output"], encoding="utf-8")]
    assert entries[0]["src_lang"] == "eng_Latn"
    assert entries[0]["src_text"] == "The weather is nice today."

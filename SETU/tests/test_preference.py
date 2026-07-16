"""M3 preference generation tests — FakeTeacher, no model downloads."""

import json

import pytest

from setu.preference import KNNIndex, PreferenceGenerator, validate_pairs
from setu.preference.pipeline import run as run_prefs
from setu.preference.validate import PreferenceValidationError, spot_check_chrf
from setu.teacher.base import TeacherModel
from setu.types import CorpusEntry, PreferencePair

CONFIG = {
    "teacher_candidates": 2,
    "knn": {"neighbors": 2, "ngram_range": [2, 4]},
    "pairing": "best_vs_each",
    "min_quality_delta": 5.0,
}

ENTRIES = [
    CorpusEntry("hin_Deva", "eng_Latn", "आज मौसम अच्छा है।", "The weather is nice today.", "t"),
    CorpusEntry("hin_Deva", "eng_Latn", "मुझे किताबें पढ़ना पसंद है।", "I like reading books.", "t"),
    CorpusEntry("hin_Deva", "eng_Latn", "वह हर रोज़ पार्क जाता था।", "He used to go to the park every day.", "t"),
    CorpusEntry("hin_Deva", "eng_Latn", "भारत एक विशाल देश है।", "India is a vast country.", "t"),
]


class GoodBadTeacher(TeacherModel):
    """First candidate near-perfect, second garbage — deterministic ranking."""

    def __init__(self, references):
        self.references = references

    def generate_candidates(self, src_text, src_lang, tgt_lang, n=4):
        return [self.references[src_text], "zzz completely unrelated qqq"][:n]


@pytest.fixture
def teacher():
    return GoodBadTeacher({e.src_text: e.tgt_text for e in ENTRIES})


def test_knn_excludes_self_and_ranks_similarity():
    texts = [e.src_text for e in ENTRIES]
    index = KNNIndex().fit(texts)
    neighbors = index.query(texts[0], k=2, exclude=0)
    assert 0 not in neighbors
    assert len(neighbors) == 2


def test_generator_produces_valid_pairs(teacher):
    pairs = PreferenceGenerator(teacher, CONFIG).generate(ENTRIES)
    assert pairs, "expected pairs from clearly separated candidates"
    stats = validate_pairs(pairs)
    assert stats["delta_min"] > 0
    for p in pairs:
        assert isinstance(p, PreferencePair)
        # preferred is the near-perfect candidate, never the garbage one
        assert p.preferred_tgt != "zzz completely unrelated qqq"
        assert p.quality_delta >= CONFIG["min_quality_delta"]


def test_validator_rejects_bad_delta():
    bad = [PreferencePair("s", "hin_Deva", "eng_Latn", "good", "bad", -1.0)]
    with pytest.raises(PreferenceValidationError):
        validate_pairs(bad)
    with pytest.raises(PreferenceValidationError):
        validate_pairs([])


def test_spot_check_catches_swapped_pairs():
    swapped = [PreferencePair(
        ENTRIES[0].src_text, "hin_Deva", "eng_Latn",
        preferred_tgt="zzz completely unrelated qqq",
        dispreferred_tgt=ENTRIES[0].tgt_text,
        quality_delta=10.0,  # lies about quality
    )]
    with pytest.raises(PreferenceValidationError):
        spot_check_chrf(swapped, {ENTRIES[0].src_text: ENTRIES[0].tgt_text})


def test_pipeline_end_to_end(tmp_path, teacher):
    corpus_dir = tmp_path / "processed" / "hin_Deva-eng_Latn"
    corpus_dir.mkdir(parents=True)
    import dataclasses
    with open(corpus_dir / "train.jsonl", "w", encoding="utf-8") as f:
        for e in ENTRIES:
            f.write(json.dumps(dataclasses.asdict(e), ensure_ascii=False) + "\n")

    report = run_prefs(
        pair="hin_Deva-eng_Latn", config=CONFIG, teacher=teacher,
        corpus_dir=tmp_path / "processed", output_dir=tmp_path / "preferences",
    )
    assert report["pairs"] > 0
    out = tmp_path / "preferences" / "hin_Deva-eng_Latn" / "pairs.jsonl"
    assert out.exists()
    loaded = [json.loads(l) for l in open(out, encoding="utf-8")]
    assert set(loaded[0]) == {
        "src_text", "src_lang", "tgt_lang", "preferred_tgt", "dispreferred_tgt", "quality_delta",
    }
    assert (tmp_path / "preferences" / "hin_Deva-eng_Latn" / "report.md").exists()

"""SeqKD distillation tests — FakeTeacher, no model downloads."""

import dataclasses
import json

import pytest

from setu.distill import SeqKDDistiller
from setu.distill.pipeline import run as run_distill
from setu.teacher.base import TeacherModel
from setu.types import CorpusEntry

# reuse the tiny-model project fixture (configs + processed corpus)
from tests.test_train_pipeline import tiny_project  # noqa: F401

ENTRIES = [
    CorpusEntry("hin_Deva", "eng_Latn", "स्रोत एक", "human ref one", "proc"),
    CorpusEntry("hin_Deva", "eng_Latn", "स्रोत दो", "human ref two", "proc"),
    CorpusEntry("hin_Deva", "eng_Latn", "स्रोत तीन", "human ref three", "proc"),
]


class EchoTeacher(TeacherModel):
    """Teacher 1-best is a deterministic function of the source."""

    def generate_candidates(self, src_text, src_lang, tgt_lang, n=4):
        return [f"teacher translation of {src_text}"] * n


def test_distiller_replaces_target_with_teacher_output():
    distilled = SeqKDDistiller(EchoTeacher(), batch_size=2).distill(ENTRIES)
    assert len(distilled) == len(ENTRIES)
    for orig, d in zip(ENTRIES, distilled):
        assert d.src_text == orig.src_text          # source unchanged
        assert d.src_lang == orig.src_lang and d.tgt_lang == orig.tgt_lang
        assert d.tgt_text == f"teacher translation of {orig.src_text}"  # teacher target
        assert d.tgt_text != orig.tgt_text          # not the human reference
        assert d.source == "seqkd"


def test_empty_teacher_output_falls_back_to_reference():
    class EmptyTeacher(TeacherModel):
        def generate_candidates(self, src_text, src_lang, tgt_lang, n=4):
            return [""] * n

    distilled = SeqKDDistiller(EmptyTeacher()).distill(ENTRIES)
    assert distilled[0].tgt_text == ENTRIES[0].tgt_text  # kept the reference
    assert SeqKDDistiller(EmptyTeacher()).distill(ENTRIES) is not None


def test_distill_pipeline_writes_corpus(tmp_path):
    pair = "hin_Deva-eng_Latn"
    src_dir = tmp_path / "processed" / pair
    src_dir.mkdir(parents=True)
    import dataclasses
    with open(src_dir / "train.jsonl", "w", encoding="utf-8") as f:
        for e in ENTRIES:
            f.write(json.dumps(dataclasses.asdict(e), ensure_ascii=False) + "\n")

    report = run_distill(pair=pair, teacher=EchoTeacher(), data_root=tmp_path)
    assert report["entries"] == 3
    out = tmp_path / "distilled" / pair / "train.jsonl"
    assert out.exists()
    loaded = [json.loads(l) for l in open(out, encoding="utf-8")]
    assert loaded[0]["tgt_text"].startswith("teacher translation of")
    assert loaded[0]["source"] == "seqkd"


def test_seqkd_training_path(tiny_project):  # noqa: F811
    """S1 SeqKD end-to-end: train the student on teacher targets (distilled),
    eval on real references (processed). Verifies the --train-corpus flow."""
    pytest.importorskip("torch")
    from setu.training.pipeline import run

    pair = "hin_Deva-eng_Latn"
    # build a distilled corpus (teacher targets) aligned with processed
    proc = tiny_project / "data" / "processed" / pair / "train.jsonl"
    entries = [CorpusEntry(**json.loads(l)) for l in open(proc, encoding="utf-8")]
    dist_dir = tiny_project / "data" / "distilled" / pair
    dist_dir.mkdir(parents=True)
    with open(dist_dir / "train.jsonl", "w", encoding="utf-8") as f:
        for e in entries:
            d = CorpusEntry(e.src_lang, e.tgt_lang, e.src_text, e.tgt_text, "seqkd")
            f.write(json.dumps(dataclasses.asdict(d), ensure_ascii=False) + "\n")

    report = run(pair=pair, limit=60, skip_dpo=True, dev_size=6,
                 ckpt_root=tiny_project / "ck_seqkd", data_root=tiny_project / "data",
                 train_corpus="distilled")
    assert report["train_corpus"] == "distilled"
    assert report["train_entries"] > 0 and report["dev_entries"] == 6
    assert "bleu" in report["sft_eval"]  # evaluated on real references

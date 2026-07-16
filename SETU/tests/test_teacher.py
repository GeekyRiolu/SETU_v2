"""M2 teacher tests. The real-model smoke test is opt-in (needs the ~850 MB
checkpoint): SETU_TEACHER_SMOKE=1 pytest tests/test_teacher.py -k smoke
"""

import os
import re
from pathlib import Path

import pytest

from setu.config import _load_yaml
from setu.teacher import IndicTrans2Teacher, TeacherModel

SRC_ROOT = Path(__file__).parent.parent / "src" / "setu"


class FakeTeacher(TeacherModel):
    def generate_candidates(self, src_text, src_lang, tgt_lang, n=4):
        return [f"candidate {i} for {src_text}" for i in range(n)]


def test_teacher_wall():
    """Nothing outside setu/teacher/ may touch IndicTrans2 internals: no
    IndicTransToolkit import and no IndicTrans2 checkpoint identifier. Generic
    infra (torch, transformers) and prose mentions are allowed elsewhere — the
    wall is about the teacher staying swappable, not the word being unspeakable."""
    forbidden = re.compile(
        r"(^\s*(import|from)\s+IndicTransToolkit\b)"      # importing the toolkit
        r"|(indictrans2-)"                                 # a checkpoint id, e.g. indictrans2-en-indic
        r"|(ai4bharat/indictrans)",                        # a gated teacher repo
        re.M | re.I,
    )
    offenders = [
        str(p) for p in SRC_ROOT.rglob("*.py")
        if "teacher" not in p.parts and forbidden.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_interface_contract():
    teacher = FakeTeacher()
    candidates = teacher.generate_candidates("नमस्ते", "hi", "en", n=3)
    assert len(candidates) == 3
    assert all(isinstance(c, str) for c in candidates)


def test_chrf_scoring_orders_quality():
    scores = TeacherModel.score_candidates(
        ["The weather is nice today.", "Weather nice.", "Completely unrelated text."],
        reference="The weather is nice today.",
    )
    assert scores[0] == 100.0
    assert scores[0] > scores[1] > scores[2]


def test_teacher_config_has_all_directions():
    config = _load_yaml("teacher.yaml")
    assert set(config["checkpoints"]) == {"indic-en", "en-indic", "indic-indic"}
    assert config["generation"]["num_beams"] >= 4


def test_direction_routing():
    assert IndicTrans2Teacher._direction("hin_Deva", "eng_Latn") == "indic-en"
    assert IndicTrans2Teacher._direction("eng_Latn", "hin_Deva") == "en-indic"
    assert IndicTrans2Teacher._direction("hin_Deva", "tam_Taml") == "indic-indic"


@pytest.mark.skipif(not os.environ.get("SETU_TEACHER_SMOKE"), reason="needs model download")
def test_smoke_real_teacher():
    teacher = IndicTrans2Teacher()
    candidates = teacher.generate_candidates(
        "जब मैं छोटा था, मैं हर रोज़ पार्क जाता था।", "hi", "en", n=4
    )
    assert len(candidates) == 4
    scores = teacher.score_candidates(
        candidates, "When I was young, I used to go to the park every day."
    )
    assert max(scores) > 40  # a sensible translation, not noise

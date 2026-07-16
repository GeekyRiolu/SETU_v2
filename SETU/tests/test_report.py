"""M9 scorecard tests — scores targets from artifacts, marks missing UNVERIFIED."""

import json

from setu.report import build_scorecard, format_scorecard


def _write(root, pair, name, obj):
    d = root / pair
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(obj), encoding="utf-8")


def test_all_targets_pass(tmp_path):
    ck, mo = tmp_path / "ck", tmp_path / "mo"
    _write(ck, "hin_Deva-eng_Latn", "train_report.json",
           {"dpo_eval": {"bleu_ratio": 0.85}})
    _write(mo, "hin_Deva-eng_Latn", "quantize_report.json",
           {"stages": {"int8": {"size_mb": 60.0, "latency_ms_p90": 120.0},
                       "int4": {"size_mb": 45.0, "latency_ms_p90": 140.0}}})
    sc = build_scorecard("hin_Deva-eng_Latn", ck, mo, offline_proof=True)
    assert sc["targets"]["quality"]["status"] == "PASS"
    assert sc["targets"]["size"]["status"] == "PASS"  # picks smallest = 45 MB
    assert sc["targets"]["size"]["value"] == 45.0
    assert sc["targets"]["latency"]["status"] == "PASS"
    assert sc["targets"]["offline"]["status"] == "PASS"
    assert sc["passed"] == 4


def test_missing_artifacts_are_unverified(tmp_path):
    sc = build_scorecard("hin_Deva-eng_Latn", tmp_path / "ck", tmp_path / "mo", offline_proof=None)
    assert all(t["status"] == "UNVERIFIED" for t in sc["targets"].values())
    assert "UNVERIFIED" in format_scorecard(sc)


def test_failing_thresholds(tmp_path):
    ck, mo = tmp_path / "ck", tmp_path / "mo"
    _write(ck, "p", "train_report.json", {"dpo_eval": {"bleu_ratio": 0.5}})
    _write(mo, "p", "quantize_report.json", {"stages": {"int8": {"size_mb": 250.0, "latency_ms_p90": 900.0}}})
    sc = build_scorecard("p", ck, mo, offline_proof=False)
    assert sc["targets"]["quality"]["status"] == "FAIL"
    assert sc["targets"]["size"]["status"] == "FAIL"
    assert sc["targets"]["latency"]["status"] == "FAIL"
    assert sc["targets"]["offline"]["status"] == "FAIL"
    assert sc["passed"] == 0

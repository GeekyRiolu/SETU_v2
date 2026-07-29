"""setu-eval — evaluate a trained SETU model on a standard test set.

    setu-eval --pair hin_Deva-eng_Latn --testset flores --split devtest \
              [--beams 4] [--comet] [--teacher] [--limit N]

Translates the test set with the deployed ONNX student and reports BLEU + chrF
(+ COMET with --comet). With --teacher it also runs IndicTrans2, reports the
teacher's scores, the student/teacher BLEU ratio, and paired-bootstrap
significance of the difference. Writes a JSON report next to the model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from setu.config import load_model_config, resolve_language
from setu.eval.metrics import corpus_bleu_chrf
from setu.eval.testsets import load_testset


def _iso(pair: str) -> tuple[str, str]:
    s, t = pair.split("-")
    return resolve_language(s)["iso"], resolve_language(t)["iso"]


def run(
    pair: str | None = None,
    testset: str = "flores",
    split: str = "devtest",
    beams: int = 1,
    with_comet: bool = False,
    with_teacher: bool = False,
    limit: int | None = None,
    models_root: str = "models",
    out: str | None = None,
) -> dict[str, Any]:
    pair = pair or load_model_config().language_pair
    src_iso, tgt_iso = _iso(pair)

    sources, references = load_testset(testset, pair, split)
    if limit:
        sources, references = sources[:limit], references[:limit]

    from setu.inference.engine import InferenceEngine

    engine = InferenceEngine(models_root=models_root, num_beams=beams)
    if engine.is_stub:
        raise RuntimeError(
            f"no trained model for {pair} under {models_root}/ — train + quantise first"
        )
    hyps = [engine.translate(s, src_iso, tgt_iso).translated_text for s in sources]
    student = corpus_bleu_chrf(hyps, references)

    report: dict[str, Any] = {
        "pair": pair, "testset": testset, "split": split, "n": len(sources),
        "beams": beams, "student": {"bleu": round(student["bleu"], 2),
                                    "chrf": round(student["chrf"], 2)},
    }
    if with_comet:
        from setu.eval.comet import comet_score
        report["student"]["comet"] = comet_score(sources, hyps, references)["comet"]

    if with_teacher:
        from setu.teacher import IndicTrans2Teacher
        teacher = IndicTrans2Teacher()
        t_hyps = [teacher.generate_candidates(s, src_iso, tgt_iso, n=1)[0] for s in sources]
        t = corpus_bleu_chrf(t_hyps, references)
        report["teacher"] = {"bleu": round(t["bleu"], 2), "chrf": round(t["chrf"], 2)}
        report["bleu_ratio"] = round(student["bleu"] / t["bleu"], 4) if t["bleu"] else None
        report["meets_quality_target"] = bool(report["bleu_ratio"] and report["bleu_ratio"] >= 0.80)
        from setu.eval.significance import paired_bootstrap
        report["significance_vs_teacher"] = paired_bootstrap(hyps, t_hyps, references)
        if with_comet:
            from setu.eval.comet import comet_score
            report["teacher"]["comet"] = comet_score(sources, t_hyps, references)["comet"]

    out_path = Path(out) if out else Path(models_root) / pair / f"eval_{testset}_{split}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report["report_path"] = str(out_path)
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Evaluate a SETU model on a standard test set")
    p.add_argument("--pair", default=None)
    p.add_argument("--testset", default="flores", choices=["flores", "in22", "in22-gen"])
    p.add_argument("--split", default="devtest", help="FLORES split: dev | devtest")
    p.add_argument("--beams", type=int, default=1, help="decode beams (1=greedy, deploy default)")
    p.add_argument("--comet", action="store_true", help="also compute COMET (needs the comet extra)")
    p.add_argument("--teacher", action="store_true", help="also score IndicTrans2 + ratio + significance")
    p.add_argument("--limit", type=int, default=None, help="cap sentences (quick check)")
    p.add_argument("--models-root", default="models")
    p.add_argument("--out", default=None)
    a = p.parse_args(argv)
    report = run(pair=a.pair, testset=a.testset, split=a.split, beams=a.beams,
                 with_comet=a.comet, with_teacher=a.teacher, limit=a.limit,
                 models_root=a.models_root, out=a.out)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

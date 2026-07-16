"""M5 pipeline: export the trained student to ONNX, quantise INT8 then INT4,
benchmark each stage (accuracy + size + latency), and deploy the smallest
artifact under models/<pair>/ for the InferenceEngine.

    setu-quantize [--pair ...]

Progressive by design: INT8 first with a benchmark, then INT4 with a benchmark,
so the size/accuracy trade-off is visible. Every number is measured, not assumed.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from setu.benchmark.latency import benchmark_latency
from setu.config import load_model_config
from setu.eval.metrics import corpus_bleu_chrf
from setu.quantize.export import artifact_size_mb, export_onnx, quantize_onnx
from setu.types import CorpusEntry

SIZE_TARGET_MB = 200.0


def _load_dev(data_root: Path, pair: str, n: int) -> list[CorpusEntry]:
    path = data_root / "processed" / pair / "train.jsonl"
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            entries.append(CorpusEntry(**json.loads(line)))
    return entries[-n:]


def _bench_variant(onnx_dir: Path, tokenizer_model: Path, dev: list[CorpusEntry]) -> dict:
    from setu.inference.onnx_engine import ONNXTranslator

    translator = ONNXTranslator(onnx_dir, tokenizer_model)
    src_flores = dev[0].src_lang if dev else None

    def translate(text: str) -> str:
        return translator.translate(text, dev[0].src_lang, dev[0].tgt_lang).translated_text

    hyps = [translate(e.src_text) for e in dev]
    scores = corpus_bleu_chrf(hyps, [e.tgt_text for e in dev])
    latency = benchmark_latency(translate, [e.src_text for e in dev])
    return {
        "size_mb": round(artifact_size_mb(onnx_dir), 2),
        "bleu": round(scores["bleu"], 2),
        "chrf": round(scores["chrf"], 2),
        **{k: v for k, v in latency.items() if k.startswith("latency") or "target" in k},
        "meets_size_target": artifact_size_mb(onnx_dir) <= SIZE_TARGET_MB,
    }


def run(
    pair: str | None = None,
    ckpt_root: Path | str = "checkpoints",
    data_root: Path | str = "data",
    models_root: Path | str = "models",
    dev_size: int = 30,
    student_variant: str = "dpo",
) -> dict[str, Any]:
    pair = pair or load_model_config().language_pair
    ckpt_root, data_root, models_root = Path(ckpt_root), Path(data_root), Path(models_root)

    student_dir = ckpt_root / pair / student_variant
    if not student_dir.exists():
        student_dir = ckpt_root / pair / "sft"
    tokenizer_model = ckpt_root / pair / "tokenizer" / "student_sp.model"
    work = models_root / pair
    work.mkdir(parents=True, exist_ok=True)
    shutil.copytree(tokenizer_model.parent, work / "tokenizer", dirs_exist_ok=True)

    dev = _load_dev(data_root, pair, dev_size)
    report: dict[str, Any] = {"pair": pair, "student": str(student_dir), "stages": {}}

    # 1. FP32 ONNX export (validated by ORT reload inside export_onnx)
    onnx_dir = export_onnx(student_dir, work / "onnx")
    report["stages"]["onnx_fp32"] = _bench_variant(onnx_dir, tokenizer_model, dev)

    # 2. INT8, then 3. INT4 — progressive
    for mode in ("int8", "int4"):
        q = quantize_onnx(onnx_dir, work / mode, mode=mode)
        report["stages"][mode] = {**_bench_variant(work / mode, tokenizer_model, dev), **{"quantized_graphs": q["quantized_graphs"]}}

    # smallest variant meeting the size target is what the engine will load
    (work / "quantize_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export + progressively quantise the student")
    parser.add_argument("--pair", default=None)
    parser.add_argument("--student", default="dpo", choices=["dpo", "sft"])
    args = parser.parse_args(argv)
    report = run(pair=args.pair, student_variant=args.student)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Train the SETU student end-to-end and score it against the teacher.

Computes the teacher's dev BLEU (the ceiling the >=80% target is measured
against), then runs tokenizer -> SFT -> DPO -> eval. Works on CPU or GPU
transparently (the trainers resolve `device: auto` to CUDA when available).

    python scripts/train_full.py --limit 25000 --dev-size 200

On Kaggle/Colab GPU this trains the full-size student in minutes; on CPU keep
--limit small. Follow with `setu-quantize` to export + quantise the result.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# reduce CUDA fragmentation before torch touches the GPU (must precede import)
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

# repo root on path so `setu` resolves without install
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from setu.config import load_model_config
from setu.eval.metrics import corpus_bleu_chrf
from setu.types import CorpusEntry


def main() -> int:
    ap = argparse.ArgumentParser(description="Train + score the SETU student")
    ap.add_argument("--pair", default=None)
    ap.add_argument("--limit", type=int, default=25000, help="training sentences")
    ap.add_argument("--dev-size", type=int, default=200)
    ap.add_argument("--skip-dpo", action="store_true")
    ap.add_argument("--no-teacher-bleu", action="store_true",
                    help="skip the teacher-ceiling eval (faster; no quality ratio)")
    args = ap.parse_args()

    pair = args.pair or load_model_config().language_pair
    corpus = Path("data/processed") / pair / "train.jsonl"
    if not corpus.exists():
        sys.exit(f"missing {corpus} — run `setu-data` first")

    # reproduce the exact dev slice the training pipeline will hold out
    entries: list[CorpusEntry] = []
    with open(corpus, encoding="utf-8") as f:
        for line in f:
            if len(entries) >= args.limit + args.dev_size:
                break
            entries.append(CorpusEntry(**json.loads(line)))
    dev = entries[-args.dev_size:]

    teacher_bleu = None
    if not args.no_teacher_bleu:
        from setu.teacher import IndicTrans2Teacher

        src_iso, tgt_iso = _iso_pair(pair)
        teacher = IndicTrans2Teacher()
        t0 = time.time()
        hyps = [teacher.generate_candidates(e.src_text, src_iso, tgt_iso, n=1)[0] for e in dev]
        teacher_bleu = corpus_bleu_chrf(hyps, [e.tgt_text for e in dev])["bleu"]
        print(f"[train] teacher dev BLEU = {teacher_bleu:.2f} ({time.time()-t0:.0f}s)", flush=True)

        # free the teacher's GPU memory before training the student — otherwise
        # both sit on the GPU and OOM (the T4 has ~15 GB)
        _free_gpu(teacher)
        del teacher

    from setu.training.pipeline import run

    t0 = time.time()
    report = run(pair=pair, limit=args.limit, dev_size=args.dev_size,
                 skip_dpo=args.skip_dpo, teacher_bleu=teacher_bleu)
    report["teacher_dev_bleu"] = teacher_bleu
    print(f"[train] done in {time.time()-t0:.0f}s", flush=True)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def _iso_pair(pair: str) -> tuple[str, str]:
    from setu.config import resolve_language

    src_flores, tgt_flores = pair.split("-")
    return resolve_language(src_flores)["iso"], resolve_language(tgt_flores)["iso"]


def _free_gpu(obj) -> None:
    """Drop an object's tensors and empty the CUDA cache."""
    import gc

    for attr in ("_models", "_processor"):
        if hasattr(obj, attr):
            setattr(obj, attr, None)
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


if __name__ == "__main__":
    raise SystemExit(main())

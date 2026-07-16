"""M4 training pipeline: train tokenizer -> SFT baseline -> DPO -> eval report.

    setu-train [--pair ...] [--limit N] [--skip-dpo]

Produces checkpoints under checkpoints/<pair>/{sft,dpo} and an eval report
comparing SFT baseline vs DPO student vs (optional) teacher BLEU.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from setu.config import _load_yaml, load_model_config, load_training_config
from setu.eval.metrics import evaluate_model
from setu.training.dataset import CorpusDataset, PreferenceDataset
from setu.training.dpo import DPOTrainer
from setu.training.sft import SFTTrainer
from setu.training.student import build_student, load_student, param_count, save_student
from setu.training.tokenizer import StudentTokenizer
from setu.training.translate import student_translate
from setu.types import CorpusEntry


def _read_entries(path: Path, limit: int | None) -> list[CorpusEntry]:
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if limit is not None and len(entries) >= limit:
                break
            entries.append(CorpusEntry(**json.loads(line)))
    return entries


def _eval_student(model, tokenizer, dev: list[CorpusEntry], teacher_bleu: float | None) -> dict:
    if not dev:
        return {}
    src_flores, tgt_flores = dev[0].src_lang, dev[0].tgt_lang
    return evaluate_model(
        translate_fn=lambda s: student_translate(model, tokenizer, s, src_flores, tgt_flores),
        sources=[e.src_text for e in dev],
        references=[e.tgt_text for e in dev],
        teacher_bleu=teacher_bleu,
    )


def run(
    pair: str | None = None,
    limit: int | None = None,
    skip_dpo: bool = False,
    ckpt_root: Path | str = "checkpoints",
    data_root: Path | str = "data",
    dev_size: int = 50,
    teacher_bleu: float | None = None,
) -> dict[str, Any]:
    model_config = load_model_config()
    training_config = load_training_config()
    pair = pair or model_config.language_pair

    ckpt_dir = Path(ckpt_root) / pair
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = Path(data_root) / "processed" / pair / "train.jsonl"

    # held-out dev set (last dev_size entries of the used slice) for eval
    all_entries = _read_entries(corpus_path, (limit + dev_size) if limit else None)
    dev = all_entries[-dev_size:] if len(all_entries) > dev_size else []
    train_entries = all_entries[: len(all_entries) - len(dev)]

    # 1. tokenizer (trained on the train split only)
    text_file = ckpt_dir / "sp_train.txt"
    with open(text_file, "w", encoding="utf-8") as f:
        for e in train_entries:
            f.write(e.src_text + "\n")
            f.write(e.tgt_text + "\n")
    vocab_size = model_config.params.get("vocab_size", 16000)
    tokenizer = StudentTokenizer.train(text_file, ckpt_dir / "tokenizer", vocab_size)

    # 2. SFT baseline
    max_len = model_config.params.get("max_seq_len", 128)
    student = build_student(tokenizer.vocab_size, model_config)
    corpus_ds = CorpusDataset.from_entries(train_entries, tokenizer, max_len=max_len)
    sft_history = SFTTrainer(student, training_config["sft"]).train(corpus_ds)
    save_student(student, ckpt_dir / "sft")

    report: dict[str, Any] = {
        "pair": pair,
        "student_params": param_count(student),
        "train_entries": len(train_entries),
        "dev_entries": len(dev),
        "sft_final_loss": sft_history[-1]["loss"] if sft_history else None,
        "sft_eval": _eval_student(student, tokenizer, dev, teacher_bleu),
    }

    # 3. DPO
    if not skip_dpo:
        pref_path = Path(data_root) / "preferences" / pair / "pairs.jsonl"
        pref_ds = PreferenceDataset(pref_path, tokenizer, limit, max_len=max_len)
        dpo = DPOTrainer(load_student(ckpt_dir / "sft"), training_config["dpo"])
        dpo_history = dpo.train(pref_ds)
        save_student(dpo.policy, ckpt_dir / "dpo")
        report["dpo_final_loss"] = dpo_history[-1]["loss"] if dpo_history else None
        report["dpo_margin_accuracy"] = dpo_history[-1]["margin_accuracy"] if dpo_history else None
        report["dpo_eval"] = _eval_student(dpo.policy, tokenizer, dev, teacher_bleu)

    (ckpt_dir / "train_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train the SETU student (SFT + DPO)")
    parser.add_argument("--pair", default=None)
    parser.add_argument("--limit", type=int, default=None, help="training entries (excludes dev)")
    parser.add_argument("--dev-size", type=int, default=50, help="held-out dev entries for eval")
    parser.add_argument("--teacher-bleu", type=float, default=None, help="teacher BLEU for the 80%% ratio")
    parser.add_argument("--skip-dpo", action="store_true")
    args = parser.parse_args(argv)
    report = run(
        pair=args.pair, limit=args.limit, skip_dpo=args.skip_dpo,
        dev_size=args.dev_size, teacher_bleu=args.teacher_bleu,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

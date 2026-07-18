"""Generate a sequence-level-distilled corpus: teacher 1-best targets for each
source. The output feeds the SeqKD baseline (train the student on it).

    setu-distill [--pair ...] [--limit N] [--batch-size 32]

Writes data/distilled/<pair>/train.jsonl (CorpusEntry shape, target = teacher
output). Same source order as data/processed, so the eval pipeline can hold out
real references from data/processed while training on these teacher targets.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any

from setu.config import load_model_config
from setu.distill.distiller import SeqKDDistiller
from setu.types import CorpusEntry


def _read_entries(path: Path, limit: int | None) -> list[CorpusEntry]:
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if limit is not None and len(entries) >= limit:
                break
            entries.append(CorpusEntry(**json.loads(line)))
    return entries


def run(
    pair: str | None = None,
    limit: int | None = None,
    batch_size: int = 32,
    teacher: Any | None = None,
    data_root: Path | str = "data",
) -> dict[str, Any]:
    pair = pair or load_model_config().language_pair
    data_root = Path(data_root)
    src_path = data_root / "processed" / pair / "train.jsonl"
    if not src_path.exists():
        raise FileNotFoundError(f"missing {src_path} — run `setu-data` first")

    entries = _read_entries(src_path, limit)
    if teacher is None:
        from setu.teacher import IndicTrans2Teacher

        teacher = IndicTrans2Teacher()

    distiller = SeqKDDistiller(teacher, batch_size=batch_size)
    distilled = distiller.distill(entries)

    out_dir = data_root / "distilled" / pair
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "train.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for e in distilled:
            f.write(json.dumps(dataclasses.asdict(e), ensure_ascii=False) + "\n")

    report = {
        "pair": pair,
        "entries": len(distilled),
        "empty_fallback_to_ref": distiller.stats["empty"],
        "output": str(out_path),
        "samples": [dataclasses.asdict(e) for e in distilled[:3]],
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a SeqKD (teacher-target) corpus")
    parser.add_argument("--pair", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args(argv)
    report = run(pair=args.pair, limit=args.limit, batch_size=args.batch_size)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

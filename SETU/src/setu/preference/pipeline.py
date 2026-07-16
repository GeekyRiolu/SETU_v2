"""Preference-generation pipeline: processed corpus -> validated PreferencePair
JSONL + report.

Run:  setu-prefs [--pair hin_Deva-eng_Latn] [--max-entries N]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any

from setu.config import _load_yaml, load_model_config
from setu.preference.generator import PreferenceGenerator
from setu.preference.validate import spot_check_chrf, validate_pairs
from setu.types import CorpusEntry


def load_corpus(path: Path, limit: int | None = None) -> list[CorpusEntry]:
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if limit is not None and len(entries) >= limit:
                break
            entries.append(CorpusEntry(**json.loads(line)))
    return entries


def run(
    pair: str | None = None,
    max_entries: int | None = None,
    config: dict[str, Any] | None = None,
    teacher: Any | None = None,
    corpus_dir: Path | str = "data/processed",
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    config = config or _load_yaml("preference.yaml")
    pair = pair or load_model_config().language_pair
    max_entries = max_entries if max_entries is not None else config.get("max_entries")

    corpus_path = Path(corpus_dir) / pair / "train.jsonl"
    entries = load_corpus(corpus_path, max_entries)

    if teacher is None:
        from setu.teacher import IndicTrans2Teacher

        teacher = IndicTrans2Teacher()

    generator = PreferenceGenerator(teacher, config)
    pairs = generator.generate(entries)

    stats = validate_pairs(pairs)  # raises on bad data — nothing bad reaches disk
    spot_check_chrf(pairs, {e.src_text: e.tgt_text for e in entries})

    out_dir = Path(output_dir or config.get("output_dir", "data/preferences")) / pair
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "pairs.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(dataclasses.asdict(p), ensure_ascii=False) + "\n")

    report = {"pair": pair, **generator.stats, **stats, "output": str(out_path)}
    (out_dir / "report.md").write_text(_format_report(report, pairs), encoding="utf-8")
    return report


def _format_report(r: dict[str, Any], pairs: list) -> str:
    lines = [
        f"# Preference report — {r['pair']}", "",
        "| Metric | Value |", "|--------|-------|",
        f"| Corpus entries used | {r['entries']} |",
        f"| Candidates scored | {r['candidates']} |",
        f"| Pairs kept | {r['pairs']} |",
        f"| Dropped (delta < min) | {r['dropped_low_delta']} |",
        f"| quality_delta min / p50 / p90 / max | {r['delta_min']:.1f} / {r['delta_p50']:.1f} / {r['delta_p90']:.1f} / {r['delta_max']:.1f} |",
        f"| quality_delta mean | {r['delta_mean']:.1f} |",
        "", "## Examples", "",
    ]
    for p in pairs[:3]:
        lines += [
            f"- **src** {p.src_text}",
            f"  **preferred** {p.preferred_tgt}",
            f"  **dispreferred** {p.dispreferred_tgt} _(Δ {p.quality_delta:.1f})_",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate DPO preference pairs")
    parser.add_argument("--pair", default=None)
    parser.add_argument("--max-entries", type=int, default=None)
    args = parser.parse_args(argv)
    report = run(pair=args.pair, max_entries=args.max_entries)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

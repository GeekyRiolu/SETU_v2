"""End-to-end corpus pipeline: load → normalise → filter → dedup → write.

Writes the clean parallel set as JSONL (one CorpusEntry per line) plus a
markdown data report with per-stage counts.

Run:  python -m setu.corpus.pipeline [--limit N] [--pair hin_Deva-eng_Latn]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from collections import Counter
from pathlib import Path
from typing import Any

from setu.config import load_model_config, _load_yaml
from setu.corpus.dedup import Deduplicator
from setu.corpus.filters import PairFilter
from setu.corpus.loader import CorpusLoader
from setu.corpus.normalize import normalize_text
from setu.types import CorpusEntry

N_SAMPLES = 5


class CorpusPipeline:
    def __init__(
        self,
        data_config: dict[str, Any] | None = None,
        pair: str | None = None,
        base_dir: Path | str = ".",
        output_dir: Path | str | None = None,
    ):
        self.config = data_config or _load_yaml("data.yaml")
        self.pair = pair or load_model_config().language_pair
        self.base_dir = Path(base_dir)
        self.output_dir = Path(output_dir or self.config.get("output_dir", "data/processed"))

    def run(self, limit: int | None = None) -> dict[str, Any]:
        src_flores, tgt_flores = self.pair.split("-")
        limit = limit if limit is not None else self.config.get("sample_limit")

        loader = CorpusLoader(self.config["sources"], self.base_dir)
        pair_filter = PairFilter(self.config.get("cleaning", {}))
        dedup = Deduplicator()

        raw_counts: Counter[str] = Counter()
        kept_counts: Counter[str] = Counter()
        rejections: Counter[str] = Counter()
        duplicates = 0
        samples: list[CorpusEntry] = []

        out_dir = self.output_dir / self.pair
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "train.jsonl"

        with open(out_path, "w", encoding="utf-8") as out:
            for source_name, entry in loader.load(src_flores, tgt_flores, limit):
                raw_counts[source_name] += 1
                entry.src_text = normalize_text(entry.src_text)
                entry.tgt_text = normalize_text(entry.tgt_text)

                reason = pair_filter.check(entry)
                if reason is not None:
                    rejections[reason] += 1
                    continue
                if dedup.is_duplicate(entry):
                    duplicates += 1
                    continue

                kept_counts[source_name] += 1
                if len(samples) < N_SAMPLES:
                    samples.append(entry)
                out.write(json.dumps(dataclasses.asdict(entry), ensure_ascii=False) + "\n")

        report = {
            "pair": self.pair,
            "skipped_sources": loader.skipped,
            "raw": dict(raw_counts),
            "raw_total": sum(raw_counts.values()),
            "rejections": dict(rejections),
            "duplicates": duplicates,
            "kept": dict(kept_counts),
            "kept_total": sum(kept_counts.values()),
            "output": str(out_path),
            "samples": [dataclasses.asdict(s) for s in samples],
        }
        report_path = out_dir / "report.md"
        report_path.write_text(self._format_report(report), encoding="utf-8")
        report["report"] = str(report_path)
        return report

    @staticmethod
    def _format_report(r: dict[str, Any]) -> str:
        lines = [
            f"# Data report — {r['pair']}",
            "",
            "| Stage | Count |",
            "|-------|-------|",
            f"| Raw entries loaded | {r['raw_total']} |",
        ]
        for name, n in sorted(r["raw"].items()):
            lines.append(f"| &nbsp;&nbsp;from `{name}` | {n} |")
        lines.append(f"| Rejected by filters | {sum(r['rejections'].values())} |")
        for reason, n in sorted(r["rejections"].items(), key=lambda kv: -kv[1]):
            lines.append(f"| &nbsp;&nbsp;{reason} | {n} |")
        lines += [
            f"| Duplicates removed | {r['duplicates']} |",
            f"| **Kept (clean, deduped)** | **{r['kept_total']}** |",
            "",
            f"Output: `{r['output']}`",
            "",
        ]
        if r["skipped_sources"]:
            lines.append("## Skipped sources")
            lines.append("")
            for s in r["skipped_sources"]:
                lines.append(f"- **{s['name']}**: {s['reason']}")
            lines.append("")
        lines += ["## Samples", ""]
        for s in r["samples"]:
            lines += [
                f"- **{s['src_lang']}** {s['src_text']}",
                f"  **{s['tgt_lang']}** {s['tgt_text']} _(source: {s['source']})_",
            ]
        return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the SETU corpus pipeline")
    parser.add_argument("--pair", default=None, help="FLORES pair, e.g. hin_Deva-eng_Latn")
    parser.add_argument("--limit", type=int, default=None, help="max raw entries per source")
    args = parser.parse_args(argv)

    report = CorpusPipeline(pair=args.pair).run(limit=args.limit)
    print(json.dumps({k: v for k, v in report.items() if k != "samples"}, indent=2))
    print(f"\nReport written to {report['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

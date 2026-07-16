"""Final scorecard — reads the artifacts each milestone leaves on disk and
scores the build against the four targets. Every number traces to a file; a
target with no evidence is reported UNVERIFIED rather than assumed pass.

    setu-report [--pair ...]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

QUALITY_RATIO_TARGET = 0.80
LATENCY_TARGET_MS = 500.0
SIZE_TARGET_MB = 200.0


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def build_scorecard(
    pair: str, ckpt_root: Path, models_root: Path, offline_proof: bool | None
) -> dict[str, Any]:
    train = _load_json(ckpt_root / pair / "train_report.json")
    quant = _load_json(models_root / pair / "quantize_report.json")

    targets: dict[str, Any] = {}

    # Quality — student BLEU ratio vs teacher (from DPO eval if present)
    dpo_eval = (train or {}).get("dpo_eval") or (train or {}).get("sft_eval") or {}
    ratio = dpo_eval.get("bleu_ratio")
    targets["quality"] = {
        "metric": "student BLEU / teacher BLEU",
        "value": round(ratio, 3) if ratio is not None else None,
        "target": f">= {QUALITY_RATIO_TARGET}",
        "status": _status(ratio, QUALITY_RATIO_TARGET, higher_better=True),
        "evidence": str(ckpt_root / pair / "train_report.json") if train else None,
    }

    # Latency — smallest quantised variant's p90 (from quantize report)
    smallest = _smallest_variant(quant)
    latency = smallest.get("latency_ms_p90") if smallest else None
    targets["latency"] = {
        "metric": "p90 ms/sentence (quantised, this host)",
        "value": latency,
        "target": f"< {LATENCY_TARGET_MS} ms",
        "status": _status(latency, LATENCY_TARGET_MS, higher_better=False),
        "evidence": str(models_root / pair / "quantize_report.json") if quant else None,
    }

    # Size — smallest quantised artifact
    size = smallest.get("size_mb") if smallest else None
    targets["size"] = {
        "metric": "quantised ONNX artifact MB",
        "value": size,
        "target": f"<= {SIZE_TARGET_MB} MB",
        "status": _status(size, SIZE_TARGET_MB, higher_better=False),
        "evidence": str(models_root / pair / "quantize_report.json") if quant else None,
    }

    # Offline — proven by the networking-disabled test
    targets["offline"] = {
        "metric": "inference with networking disabled",
        "value": offline_proof,
        "target": "no network calls",
        "status": "PASS" if offline_proof else ("FAIL" if offline_proof is False else "UNVERIFIED"),
        "evidence": "tests/test_quantize.py::test_onnx_engine_translates_offline",
    }

    passed = sum(1 for t in targets.values() if t["status"] == "PASS")
    return {"pair": pair, "targets": targets, "passed": passed, "total": len(targets)}


def _smallest_variant(quant: dict | None) -> dict | None:
    if not quant or "stages" not in quant:
        return None
    sized = [s for s in quant["stages"].values() if isinstance(s, dict) and s.get("size_mb")]
    return min(sized, key=lambda s: s["size_mb"]) if sized else None


def _status(value, threshold, higher_better: bool) -> str:
    if value is None:
        return "UNVERIFIED"
    ok = value >= threshold if higher_better else value <= threshold
    return "PASS" if ok else "FAIL"


def format_scorecard(sc: dict[str, Any]) -> str:
    lines = [
        f"# SETU final scorecard — {sc['pair']}",
        "",
        f"**{sc['passed']} / {sc['total']} targets PASS**",
        "",
        "| Target | Metric | Value | Threshold | Status | Evidence |",
        "|--------|--------|-------|-----------|--------|----------|",
    ]
    for name, t in sc["targets"].items():
        lines.append(
            f"| {name} | {t['metric']} | {t['value']} | {t['target']} | "
            f"**{t['status']}** | {t['evidence'] or '—'} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    from setu.config import load_model_config

    parser = argparse.ArgumentParser(description="Score the build against the four targets")
    parser.add_argument("--pair", default=None)
    parser.add_argument("--ckpt-root", default="checkpoints")
    parser.add_argument("--models-root", default="models")
    parser.add_argument("--offline-proof", action="store_true",
                        help="mark the offline target proven (the offline test passed)")
    args = parser.parse_args(argv)
    pair = args.pair or load_model_config().language_pair
    sc = build_scorecard(pair, Path(args.ckpt_root), Path(args.models_root),
                         True if args.offline_proof else None)
    print(format_scorecard(sc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

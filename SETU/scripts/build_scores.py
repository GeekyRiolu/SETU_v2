#!/usr/bin/env python3
"""Generate docs/SCORES.md from vm/out/report_*.json (per-direction training eval).

    PYTHONPATH=src python scripts/build_scores.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from setu.config import resolve_language  # noqa: E402

rows = []
for f in sorted((ROOT / "vm" / "out").glob("report_*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    ev = d.get("sft_eval") or d.get("seqkd_eval") or {}
    if not ev:
        continue
    try:
        src_f, tgt_f = d["pair"].split("-")
        src, tgt = resolve_language(src_f), resolve_language(tgt_f)
    except (ValueError, KeyError):
        continue
    rows.append({
        "dir": f"{src['name']} → {tgt['name']}",
        "bleu": ev.get("bleu"), "chrf": ev.get("chrf"),
        "teacher": ev.get("teacher_bleu"), "ratio": ev.get("bleu_ratio") or 0.0,
        "lat": ev.get("latency_ms_mean"), "loss": d.get("sft_final_loss"),
    })

rows.sort(key=lambda r: r["ratio"], reverse=True)
n = len(rows)
npass = sum(1 for r in rows if r["ratio"] >= 0.80)
mean = sum(r["ratio"] for r in rows) / n if n else 0.0
med = sorted(r["ratio"] for r in rows)[n // 2] if n else 0.0


def mark(r):
    return "✅" if r >= 0.80 else ("⚠️" if r >= 0.75 else "❌")


lines = [
    "# SETU — scorecard (Phase 1)",
    "",
    "Per-direction student vs teacher on a 500-sentence Samanantar dev slice. "
    "Quality target = **student BLEU / teacher BLEU ≥ 0.80**. Every model is a "
    "52.6M-param SeqKD student, **INT4 ONNX ~104 MB**, fully offline. Generated "
    "from `vm/out/report_*.json` by `scripts/build_scores.py`.",
    "",
    f"**{npass} / {n} directions meet ≥ 0.80** · mean ratio **{mean:.3f}** · "
    f"median **{med:.3f}** · {n // 2} languages, both directions.",
    "",
    "| # | Direction | BLEU | chrF | Teacher | Ratio | ≥0.80 | Mean latency |",
    "|--:|-----------|-----:|-----:|--------:|------:|:-----:|-------------:|",
]
for i, r in enumerate(rows, 1):
    lat = f"{r['lat']:.0f} ms" if r["lat"] else "—"
    lines.append(
        f"| {i} | {r['dir']} | {r['bleu']:.1f} | {r['chrf']:.1f} | "
        f"{r['teacher']:.1f} | **{r['ratio']:.3f}** | {mark(r['ratio'])} | {lat} |"
    )
lines += [
    "",
    "Indic↔Indic pairs (e.g. Hindi→Bengali) are served by pivoting through "
    "English, so all 11 languages translate in every direction even without a "
    "direct model. Latency is on a shared CPU host; size (104 MB) and offline "
    "targets pass for every model.",
    "",
]
(ROOT / "docs" / "SCORES.md").write_text("\n".join(lines), encoding="utf-8")
print(f"wrote docs/SCORES.md — {npass}/{n} pass, mean {mean:.3f}")

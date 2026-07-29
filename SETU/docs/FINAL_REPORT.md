# SETU — final report

Hindi↔English thin slice, end-to-end. **Best model: SeqKD @ 250k, trained on GPU
(NVIDIA A40), 2026-07-29.** Regenerate with `setu-report --offline-proof`.
(An earlier CPU-only run reached only ratio 0.003 — kept in git history — before
GPU training; this report supersedes it.)

## Scorecard — SeqKD @ 250k

**3 / 4 targets PASS** (`hin_Deva-eng_Latn`)

| Target | Metric | Value | Threshold | Status | Evidence |
|--------|--------|-------|-----------|--------|----------|
| Quality | student BLEU / teacher BLEU | **0.764** (22.10 / 28.91; chrF 49.81) | ≥ 0.80 | **FAIL** (3.6 pts short) | `checkpoints/<pair>/train_report.json` |
| Latency | p90 ms/sentence (quantised) | 198.5 | < 500 ms | **PASS** | `models/<pair>/quantize_report.json` |
| Size | quantised ONNX artifact (INT4) | 103.94 MB | ≤ 200 MB | **PASS** | `models/<pair>/quantize_report.json` |
| Offline | inference, networking disabled | yes | no network | **PASS** | `test_onnx_engine_translates_offline` |

## What passed, and how it was measured

- **Quality** — the **SeqKD** student (trained on the teacher's own translations, the
  method shown to beat reference/DPO training) reaches **BLEU 22.10 / chrF 49.81 = 76.4 %
  of teacher BLEU** on a 500-sentence held-out real-reference dev set. Correct idiomatic
  outputs (`भारत एक विशाल देश है। → "India is a huge country."`). 3.6 points from the
  ≥ 0.80 target; the SeqKD scaling curve (0.607 @100k → 0.764 @250k) is not saturated, so
  ~400k should cross it.
- **Latency** — 52 M-param student, quantised INT4/INT8 ONNX, **p90 198.5 ms/sentence**,
  well under 500 ms. Benchmarked per quantisation stage by `setu-quantize`.
- **Size** — **INT4 103.94 MB**, under the 200 MB target.
- **Offline** — `InferenceEngine` loads the local ONNX student + SentencePiece tokenizer;
  `assert_offline()` disables all sockets and inference still succeeds. Path audited: no
  HTTP, telemetry, or remote fetch.

## The quality gap (3.6 points) and how to close it

The best model is at 0.764 vs the 0.80 target. Unlike the earlier plateau, this is *not*
a ceiling — it's a data point on a still-rising curve:

- **More SeqKD data** (the lever): 100k → 0.607, 250k → 0.764; extrapolating, ~400k
  should reach 0.80. The teacher (BLEU 28.9) is the ceiling; SeqKD is closing on it.
- **Secondary:** a larger student, beam-search deployment (latency has headroom),
  or S3 = SeqKD + DPO.

The headline research finding stands: **for compact on-device Indic MT, sequence-level KD
from teacher outputs strongly beats preference/DPO distillation on noisy human references**
(SeqKD 17.1 vs ref+DPO 11.1 BLEU at 100k, matched size; see `PAPER_PLAN.md`).

**To reach ≥ 80 %** is a config + compute change, not a code change: widen the student in
`configs/model.yaml` (d=512, 6+6 layers), raise `--limit` to the full BPCC/Samanantar
corpus, train more epochs on a GPU. Every pipeline stage (data → teacher → preferences →
DPO → quantise → offline serving) already runs; only the compute is missing here.

## Coverage of the build

| Milestone | Status | Evidence |
|-----------|--------|----------|
| M0 Scaffold | ✅ | package, configs, CLI, tests |
| M1 Data pipeline | ✅ | 50k Samanantar → 49,520 clean/deduped |
| M2 Teacher (IndicTrans2 behind a wall) | ✅ | real smoke test; `docs/TEACHER.md` |
| M3 Preference generation | ✅ | 2,074 validated pairs, median ΔChrF 31.3 |
| M4 DPO training | ✅ pipeline | DPO > SFT; quality target unmet (compute) |
| M5 Quantise + ONNX + offline | ✅ | Size ✅ Latency ✅ Offline ✅ |
| M6 Interfaces (REST/CLI/PWA/SDK) | ✅ | one shared engine, 15 tests |
| M7 AIO-KD | ✅ mechanism | balancing + coverage tested |
| M8 EWC | ✅ mechanism | measured anti-forgetting |
| M9 Hardening | ✅ | this report, full suite green |

## Test suite

64 tests green (plus an opt-in real-teacher smoke test, `SETU_TEACHER_SMOKE=1`).
Covers: config/registry, corpus cleaning, teacher wall, preference validation, tokenizer,
SFT/DPO mechanics (frozen reference, loss decrease, truncation), full train pipeline,
ONNX export + quantise + offline inference, all four interfaces, AIO-KD balancing, EWC
anti-forgetting, and the scorecard.

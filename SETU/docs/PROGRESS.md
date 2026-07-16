# SETU — Project log (end-to-end)

A living record of what SETU is, everything built so far, the decisions and
debugging behind it, the current measured status, and what's next. A dated
**Session changelog** at the bottom is appended after every working session.

Last updated: 2026-07-17.

---

## 1. What SETU is

SETU translates across the 22 scheduled languages of India **fully offline** on
edge devices. A strong teacher (IndicTrans2) produces candidate translations;
compact student SLMs learn from ranked **preference pairs via DPO**, scale to
many directions with **AIO-KD**, expand to new languages with **EWC**, and ship
as **quantised ONNX** models that run on phones / ARM boards.

Thesis: *privacy-preserving, on-device, preference-distilled Indic MT.* No user
text leaves the device; adding a language is a config change, not a rewrite.

### The four targets (definition of done)

| Target | Threshold |
|--------|-----------|
| Quality | student ≥ 80% of IndicTrans2 BLEU |
| Latency | < 500 ms/sentence on ARM-class CPU |
| Size | ≤ 200 MB quantised ONNX artifact |
| Offline | zero network calls at inference |

## 2. Environment & hard constraints (shaped every decision)

- **CPU-only box**, 8 cores, **7.4 GB RAM**, no usable NVIDIA GPU. This forced a
  small student, small batches, and small data slices; it's why quality can't be
  hit locally and why the Kaggle GPU path exists.
- **Python 3.12 venv** (`SETU/.venv`). Started on 3.14 but the IndicTrans2 rotary
  remote modeling code needs **transformers < 4.54** (it uses the legacy tuple
  `past_key_values` cache API removed in 4.54), which pins the stack to 3.12.
- **Gated HuggingFace assets:** the `ai4bharat/BPCC` dataset and all official
  `ai4bharat/indictrans2-*` checkpoints are gated (401 without login + accepted
  terms). Fallbacks used: ungated `prajdabre/rotary-indictrans2-*-dist-200M`
  teachers and ungated **Samanantar** data.
- Git remote is the user's fork `GeekyRiolu/SETU_v2`; every milestone is one
  commit pushed to `main`.

## 3. Repo layout

```
SETU/
├── setu_cli.py            # CLI entry (renamed from setu.py to stop package shadowing)
├── translate_live.py      # interactive teacher REPL (real translations, offline)
├── configs/               # languages.yaml (22+English), model/training/data/teacher/
│                          #   preference .yaml; *.gpu.yaml for GPU runs
├── scripts/train_full.py  # teacher-BLEU ceiling + SFT+DPO+eval in one command
├── kaggle/setu_gpu_train.ipynb   # end-to-end GPU notebook
├── src/setu/
│   ├── types.py           # CorpusEntry, PreferencePair, ModelConfig, TranslationResult
│   ├── config.py          # YAML loaders, language registry, ISO<->FLORES
│   ├── corpus/            # M1: loader, normalize, filters, dedup, pipeline
│   ├── teacher/           # M2: base (wall) + indictrans2 backend
│   ├── preference/        # M3: knn, generator, validate, pipeline
│   ├── training/          # M4/M7/M8: tokenizer, student, dataset, sft, dpo,
│   │                      #   aio_kd, ewc, device, translate, pipeline
│   ├── eval/              # BLEU/ChrF/latency harness
│   ├── quantize/          # M5: export, pipeline
│   ├── benchmark/         # latency benchmark
│   ├── inference/         # engine (stub|ONNX), onnx_engine
│   └── report.py          # M9: final scorecard
├── interfaces/            # M6: rest/ (FastAPI), pwa/, sdk/{android,ios}
└── tests/                 # ~70 tests
```

## 4. Milestone log

Each milestone is one commit; `Claude/TASKS.md` has the per-milestone notes too.

- **M0 — Scaffold** (`dd189de`). src-layout package, 4 stable data objects,
  YAML config with the 22-language + English registry (ISO→FLORES matching
  IndicTrans2), passthrough stub engine, CLI, 7 tests.
- **M1 — Data pipeline** (`61eec5a`). load → normalise (NFC, control-char strip,
  ZWJ/ZWNJ preserved) → filter (length, length-ratio alignment, per-script letter
  fraction) → exact dedup → JSONL + report. **Run: 50,000 Samanantar pairs →
  49,520 kept** (476 filtered: 253 length-ratio, 213 wrong-script, 10 too-long;
  4 dups). BPCC wired but skipped (gated).
- **M2 — Teacher behind a wall** (`cd7f99f`). `TeacherModel.generate_candidates`
  + ChrF `score_candidates`; `IndicTrans2Teacher` is the ONLY file allowed to
  import IndicTrans2 internals (a test enforces this). Real smoke test: 2 Hindi
  sentences → 4 fluent English candidates each, ~2.5 s/sentence CPU. Full
  inspection in `docs/TEACHER.md`.
- **M3 — Preference generation** (`5863657`). teacher n-best ∪ kNN-retrieved
  neighbour translations, ChrF-ranked, `best_vs_each` pairing, `quality_delta` =
  ChrF gap, low-delta drop, validation gate (preferred ChrF > dispreferred for
  every pair). **Run: 500 entries → 3,494 candidates → 2,074 validated pairs**
  (920 dropped); quality_delta min/p50/p90/max = 5.0 / 31.3 / 63.4 / 97.3.
- **M4 — SFT + DPO** (`bc47bc1`). Own SentencePiece tokenizer (23 FLORES tags
  reserved for stable ids), compact ~9.5M-param Marian student, SFT baseline,
  DPO with **frozen** SFT reference (test-enforced), eval harness (BLEU/ChrF/
  latency + 80%-ratio gate). **Run (1500 train/50 dev, CPU): DPO beats SFT** —
  BLEU 0.06 vs 0.02, ChrF 3.27 vs 3.20, latency 209 vs 266 ms. Teacher dev BLEU
  17.8; student ratio ≈ 0.003 → **quality target unmet** (undertrained, reported
  not hidden).
- **M5 — Quantise + ONNX + offline** (`e61a347`). ONNX export (ORT-validated),
  progressive INT8→INT4 with per-stage benchmark, real `InferenceEngine` on ONNX,
  `assert_offline()` socket kill. **Run: 82.0 MB FP32 → 21.4 MB INT8 → 21.2 MB
  INT4**, p90 latency 234→156→158 ms, offline translate ~8 ms. **Size ✅ Latency
  ✅ Offline ✅.** (ORT CPU has no true INT4, so INT4 ≈ INT8; embeddings dominate.)
- **M6 — Interfaces** (`92aa140`). REST (FastAPI: /translate, /languages, /health),
  CLI (--text/--file/stdin/--json), offline PWA (service-worker shell caching,
  served at /app), Android+iOS SDK stubs. All call one `InferenceEngine`. 15 tests.
- **M7 — AIO-KD** (`69325d5`). One student over many directions with
  temperature-sampled cross-lingual balancing + deterministic weighted
  round-robin + coverage report. Mechanism proven by test; full rollout needs
  other languages' corpora.
- **M8 — EWC** (`1405c38`). Diagonal-Fisher penalty; `from_old_task` snapshots
  θ* + Fisher; `ewc_train_step`. Tests prove penalty = 0 at θ*, grows away, and —
  measured — EWC keeps Fisher-weighted drift of an old task below plain
  fine-tuning after a conflicting new task. Procedure in `docs/ADDING_A_LANGUAGE.md`.
- **M9 — Hardening** (`662125c`). `setu-report` scorecard (UNVERIFIED when no
  evidence), benchmark tests, `docs/FINAL_REPORT.md`, dead-code cleanup.

### Post-milestone

- **GPU + Kaggle** (`170704b`). Device-aware trainers (`device: auto` → CUDA),
  `model.gpu.yaml`/`training.gpu.yaml` (full 52M student), `scripts/train_full.py`,
  `kaggle/setu_gpu_train.ipynb`, `docs/KAGGLE.md`.
- **Shadowing fix** (`2f1a320`). Renamed `setu.py` → `setu_cli.py` (the root
  script shadowed the `setu` package, breaking `python -m setu.…` on Kaggle);
  notebook switched to console scripts.

## 5. Cross-cutting issues & fixes (the war stories)

1. **Gated HF** — BPCC + ai4bharat checkpoints 401. Fix: ungated rotary teachers
   + Samanantar; documented the login path.
2. **Python 3.14 incompatibility** — rotary remote code needs transformers < 4.54.
   Fix: rebuilt venv on Python 3.12, pinned `transformers>=4.42,<4.54`.
3. **`IndicProcessor.postprocess_batch` deadlock** — it pops one entity-placeholder
   map per *input* from a blocking queue; decoding n>1 candidates per input
   underflowed and hung forever. Fix: pass `num_return_sequences=n`.
4. **Swap thrashing** — the 52M student + AdamW + batch-64 activations exceeded
   7.4 GB → 5.6 GB swap, ~4 s/step. Fix: edge-sized 9.5M student + batch 16.
5. **Positional-embedding overflow** — sentences longer than the 128-token limit
   crashed SFT and eval. Fix: truncate encoded sequences (dataset + encoder input)
   to `max_seq_len`; regression test added.
6. **`models_root` str vs Path**, **stub/real test isolation** (`SETU_MODELS_ROOT`
   + autouse fixture), **package shadowing** (rename) — all fixed.

## 6. Current status — final scorecard

`setu-report --offline-proof` on the real artifacts (`hin_Deva-eng_Latn`):

| Target | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Quality | BLEU ratio 0.003 | ≥ 0.80 | **FAIL** (undertrained on CPU) |
| Latency | 158 ms p90 | < 500 ms | **PASS** |
| Size | 21.18 MB | ≤ 200 MB | **PASS** |
| Offline | sockets disabled, still translates | no network | **PASS** |

**3 / 4 pass.** Quality is the honest gap: a 9.5M student on 1,500 sentences for
3 CPU epochs cannot learn translation. Closing it is a compute change (bigger
model, full corpus, GPU) — the plumbing is done.

## 7. GPU / Kaggle path

`kaggle/setu_gpu_train.ipynb` runs the whole pipeline on a free Kaggle T4/P100:
clone+install → `setu-data` → `setu-prefs` → `scripts/train_full.py` →
`setu-quantize` → `setu-report` → test → download. Uses the full 52M student and
`device: auto` → CUDA. See `docs/KAGGLE.md`.

### Kaggle GPU run #1 — 2026-07-17 (partial: data + prefs OK, training OOM, fixed)

First real GPU numbers (T4, 15 GB), on `hin_Deva-eng_Latn`:

- **Data** ✅ — 30,000 Samanantar streamed → **29,705 kept** (135 wrong-script,
  151 length-ratio, 7 too-long, 2 dups). BPCC skipped (gated).
- **Preferences** ✅ — 8,000 entries → 55,910 candidates → **33,535 validated
  pairs** (14,375 dropped low-delta); quality_delta min/p50/p90/max =
  5.0 / 29.5 / 63.3 / 97.9, mean 32.7. (Much larger than the CPU run's 2,074.)
- **Teacher dev BLEU (200-sentence dev)** = **27.11** — the ceiling; student
  needs ≥ 21.7 BLEU for the 80% target.
- **SFT** ❌ — **CUDA OOM**: 52M student at batch 64 *plus the teacher still
  resident on the GPU* (from the BLEU step) exceeded 15 GB. Cascaded to quantize
  (no `sft/` checkpoint → optimum treated the missing path as a repo id) and to
  scorecard 1/4 (correctly UNVERIFIED, not fake passes).

**Fixes applied (commit — see changelog):** free the teacher's GPU memory before
training (`scripts/train_full.py`); GPU batch **64→32 (SFT), 32→16 (DPO)** in
`training.gpu.yaml`; `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`; and
`export_onnx` now resolves an absolute path + errors clearly if the checkpoint is
missing. **Re-run pending** — expected to complete training → quantise → report.

## 8. Test suite

~70 tests green (plus an opt-in real-teacher smoke, `SETU_TEACHER_SMOKE=1`).
Config/registry, corpus cleaning, teacher wall, preference validation, tokenizer,
SFT/DPO mechanics (frozen reference, loss decrease, truncation), full train
pipeline, ONNX export+quantise+offline inference, all four interfaces, AIO-KD
balancing, EWC anti-forgetting, device resolution, scorecard.

## 9. Known limitations & next steps

- Quality unmet on CPU → **run the Kaggle GPU training** (primary next step).
- INT4 == INT8 size (no true ORT CPU INT4) — real INT4 needs a different backend.
- ARM latency is the target but only x86 measured — needs an ARM/emulated profile.
- AIO-KD / EWC proven as mechanisms, not on full multilingual data.
- Research paper: see `docs/PAPER_PLAN.md` — the deciding experiment is
  DPO-distillation vs. sequence-level KD at scale.

## 10. Session changelog

- **2026-07-17** — Created this log and `docs/PAPER_PLAN.md` (research question,
  baselines, metrics, results-table templates, ablations, venues). Established the
  convention: append a dated entry here at the end of every session. Prior to
  this: completed M0–M9, GPU/Kaggle support, and the package-shadowing fix (all
  pushed); ~70 tests green; scorecard 3/4 (quality pending GPU training).
- **2026-07-17 (cont.)** — Housekeeping: stopped the last open monitor (was still
  tailing the abandoned CPU big-training log) and confirmed no stray monitor/
  waiter processes remain. Reaffirmed the convention to keep committing + pushing
  docs to GitHub after every session.
- **2026-07-17 (Kaggle run #1)** — First real GPU run: data (29,705 kept) and
  preferences (**33,535 validated pairs**) succeeded; teacher dev BLEU **27.11**;
  SFT hit CUDA OOM (52M @ batch 64 + resident teacher > 15 GB), cascading to
  quantize + report. Fixed: free teacher before training, GPU batch 64→32 / 32→16,
  `expandable_segments`, `export_onnx` absolute-path + missing-checkpoint guard.
  Local tests still green (8/8 for quantize+training). Re-run pending. Details in
  §7 "Kaggle GPU run #1".

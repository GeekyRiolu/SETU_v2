# SETU

Offline multilingual translation for the **22 scheduled Indian languages**, built to run
on edge devices with no network access.

**How it works:** a strong teacher ([IndicTrans2](../README.md), cloned at the repo root)
produces candidate translations; compact student models learn from ranked preference
pairs via **DPO**, scale to many directions with **AIO-KD**, expand to new languages with
**EWC**, and ship as quantised **ONNX** models.

## Targets (definition of done)

| Target  | Threshold | Status (Hindi↔English, CPU box) |
|---------|-----------|--------------------------------|
| Quality | student ≥ 80% of IndicTrans2 BLEU | ⚠️ **unmet** — pipeline proven, needs GPU-scale training |
| Latency | < 500 ms/sentence on ARM-class CPU | ✅ **156 ms p90** (quantised, x86 CPU) |
| Size    | ≤ 200 MB quantised ONNX artifact | ✅ **21 MB** (INT8/INT4) |
| Offline | zero network calls at inference | ✅ proven (sockets disabled) |

Full scorecard and the honest quality analysis: [`docs/FINAL_REPORT.md`](docs/FINAL_REPORT.md)
(regenerate with `setu-report --offline-proof`).

## Setup

```bash
cd SETU
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"            # core + tests
pip install -e ".[dev,data]"       # + corpus pipeline (HF datasets streaming)
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU boxes
pip install -e ".[dev,data,teacher]"   # + IndicTrans2 teacher stack
```

Optional HF credentials: the `ai4bharat` BPCC dataset and original IndicTrans2
checkpoints are gated — accept their terms on huggingface.co and run
`huggingface-cli login` to use them. Without credentials SETU falls back to
ungated author-released checkpoints and Samanantar data (see `docs/TEACHER.md`).

## Run

```bash
python setu_cli.py --src hi --tgt en --text "नमस्ते दुनिया"
# or, after install:
setu --src hi --tgt en --text "नमस्ते दुनिया" --json
```

## Pipeline

Each stage is a CLI entry point; all are config-driven (no hard-coded language pairs).

```bash
setu-data      # M1  BPCC/Samanantar -> clean, deduped data/processed/<pair>/train.jsonl
setu-prefs     # M3  teacher candidates + kNN -> validated data/preferences/<pair>/pairs.jsonl
setu-train     # M4  tokenizer -> SFT baseline -> DPO -> eval (BLEU/ChrF/latency)
setu-quantize  # M5  ONNX export -> INT8 -> INT4, benchmarked, deployed to models/<pair>/
setu-report    # M9  score the build against the four targets
```

The best model uses **SeqKD** (`setu-distill` → `train_full.py --train-corpus
distilled`): training on the teacher's outputs beats reference/DPO training —
BLEU 22.1 / **0.764 of teacher** at 250k (`docs/PAPER_PLAN.md`).

**Train on a GPU** (the CPU box can't reach quality):
- **Colab** — `colab/setu_seqkd_deploy.ipynb` (resumable, Drive-persisted, one-click)
- **Your own GPU VM / SSH** — `vm/setu_vm_train.sh` + `vm/README_VM.md` (tmux,
  resumable done-markers, reuses the VM's CUDA torch, zips the model for download)
- **Kaggle** — `kaggle/setu_gpu_train.ipynb` (note: 12 h session cap)

The teacher (IndicTrans2) stays behind `setu.teacher.TeacherModel`; scaling to more
languages uses `AIOKDOrchestrator` (M7) and adding one without forgetting uses
`EWCRegularizer` (M8) — see `docs/ADDING_A_LANGUAGE.md`.

> **Status:** the engine loads a quantised ONNX student when one is deployed under
> `models/<pair>/`, else a passthrough stub. See `Claude/TASKS.md` for milestone
> notes and `docs/TEACHER.md` for the teacher inspection report.

## Test

```bash
pytest
```

## Layout

```
SETU/
├── setu_cli.py              # CLI entry point
├── configs/             # languages.yaml (22-language registry), model.yaml, training.yaml
├── src/setu/            # package: types, config, inference/ (later: corpus, teacher,
│                        #   preference, training, quantise)
├── interfaces/          # REST / SDK / PWA front-ends (M6) — all share one InferenceEngine
├── data/                # raw/ processed/ preferences/ (gitignored artifacts)
├── benchmarks/          # latency / size / quality benchmark outputs
└── tests/
```

Language pairs, model params, and hyperparameters are **config-driven** —
adding a language is a config change, not a rewrite.

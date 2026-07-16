# SETU

Offline multilingual translation for the **22 scheduled Indian languages**, built to run
on edge devices with no network access.

**How it works:** a strong teacher ([IndicTrans2](../README.md), cloned at the repo root)
produces candidate translations; compact student models learn from ranked preference
pairs via **DPO**, scale to many directions with **AIO-KD**, expand to new languages with
**EWC**, and ship as quantised **ONNX** models.

## Targets (definition of done)

| Target  | Threshold |
|---------|-----------|
| Quality | student ≥ 80% of IndicTrans2 BLEU |
| Latency | < 500 ms/sentence on ARM-class CPU |
| Size    | ≤ 200 MB quantised ONNX artifact |
| Offline | zero network calls at inference |

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
python setu.py --src hi --tgt en --text "नमस्ते दुनिया"
# or, after install:
setu --src hi --tgt en --text "नमस्ते दुनिया" --json
```

> **Status:** M0 scaffold — the engine is a passthrough stub; real translation lands
> after DPO training (M4) and quantised ONNX export (M5). See `Claude/TASKS.md` for
> the milestone checklist.

## Test

```bash
pytest
```

## Layout

```
SETU/
├── setu.py              # CLI entry point
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

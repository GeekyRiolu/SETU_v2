# Training SETU on a free Kaggle GPU

The CPU box can only prove the pipeline runs; a GPU is what makes the student
actually translate (and can hit the ≥80%-of-teacher quality target). Kaggle
gives ~30 GPU hours/week free — enough to train the full-size student.

## Quick start

1. Go to <https://www.kaggle.com/code> → **New Notebook**.
2. Right panel: **Accelerator → GPU T4 x2**, and **Internet → On**.
3. Either **File → Import Notebook** and upload `kaggle/setu_gpu_train.ipynb`,
   or paste the cells below into a fresh notebook.
4. Run all cells top to bottom. Total time on a T4 is roughly 30–50 min,
   dominated by preference generation and data streaming.
5. Download `setu_model.zip` from the **Output** tab when it finishes.

## What the notebook does

| Cell | Step | Command |
|------|------|---------|
| 1 | check GPU | `torch.cuda.is_available()` |
| 2 | clone + install | `git clone …/SETU_v2` · `pip install -e ".[data,teacher,prefs,quantize]"` |
| 3 | switch to GPU config | copies `model.gpu.yaml` / `training.gpu.yaml`, sets teacher `device: cuda` |
| 4 | data | `python -m setu.corpus.pipeline --limit 30000` |
| 5 | preferences | `python -m setu.preference.pipeline --max-entries 8000` |
| 6 | train | `python scripts/train_full.py --limit 25000 --dev-size 200` |
| 7 | quantise + score | `setu.quantize.pipeline` · `setu.report --offline-proof` |
| 8 | test | runs the offline ONNX engine on real sentences |
| 9 | download | zips `models/hin_Deva-eng_Latn` to the Output panel |

## The GPU config (vs the CPU defaults)

`configs/model.gpu.yaml` / `configs/training.gpu.yaml` scale up what the 7.4 GB
CPU box couldn't hold:

- student **d=512, 6+6 layers, 32k vocab** (~52M params) instead of the ~9.5M CPU model
- SFT **batch 64, 10 epochs**; `device: auto` → CUDA
- teacher runs on `cuda` so preference generation is fast

The trainers resolve `device: auto` to CUDA automatically — the *same code*
runs on CPU here and GPU there, no branches.

## Scaling further

- **More data:** raise `--limit` on `setu.corpus.pipeline` (needs Internet On) and
  on `train_full.py`. Samanantar is ungated; BPCC needs an HF token (see
  `docs/TEACHER.md`).
- **Better teacher preferences:** with an HF token that accepted the ai4bharat
  terms, point `configs/teacher.yaml` at `ai4bharat/indictrans2-*-1B` for a
  stronger teacher.
- **Another language pair:** change `language_pair` in `model.yaml` and rerun
  (see `docs/ADDING_A_LANGUAGE.md`).

## Using the downloaded model back on any machine

Unzip into `SETU/models/` and the `InferenceEngine` (and all four interfaces)
pick it up automatically:

```bash
unzip setu_model.zip -d SETU/models/
cd SETU && python setu.py --src hi --tgt en --text "भारत एक विशाल देश है।"
```

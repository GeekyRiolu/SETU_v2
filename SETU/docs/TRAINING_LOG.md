# SETU training log: A40 VM campaign (SeqKD @ 500k, 9 languages bidirectional)

Reconstructed from the 2026-07-29 to 2026-08-07 training session on the user's
GPU VM. This is the canonical record of how the deployable SETU students were
trained, the environment fixes needed to get there, every run's result, and the
findings that came out of it. Some companion artifacts referenced here
(`translate.py`, `vm/out/ANALYSIS.md`, `vm/out/SCORES.md`,
`vm/out/complex_translations.md`, and the per-direction `report_*.json` beyond
the five in this repo) were produced on the training machine and are not all
committed here; their numbers are captured below.

---

## 1. Hardware and environment

- **GPU:** NVIDIA **A40-16Q**, a 16 GB **vGPU slice** (software partition of a
  48 GB A40, not MIG), Ampere cc 8.6, driver **535**, CUDA **12.2**.
- **Host:** Debian, ~640 GB disk (575 GB free). Conda env `ftenv`, Python 3.11.2.
- **Access:** PuTTY (SSH) + WinSCP (file transfer); training kept alive across
  disconnects with **tmux** (or `nohup` fallback).
- **Teacher:** ungated `prajdabre/rotary-indictrans2-{indic-en,en-indic}-dist-200M`
  (rotary remote code; needs `einops`, `transformers<4.54`).
- **Runners:** `vm/setu_vm_train.sh` (one pair, resumable via per-pair `.done_*`
  markers, reuses the VM's CUDA torch), `vm/setu_train_all.sh` (bidirectional
  batch over the top languages, fault-tolerant), `vm/README_VM.md` (walkthrough).

## 2. Environment fixes (all baked into the runner + README)

The pipeline reached the teacher load and then hit four environment issues in
sequence. Each was diagnosed and its fix folded into `setu_vm_train.sh` so a
clean run never repeats it:

1. **transformers vs torch (CVE-2025-32434).** The VM had transformers 4.36; the
   install floor bumped it to 4.53, whose `torch.load` security guard refuses the
   teacher's non-safetensors `.bin` unless **torch >= 2.6**. Resolution: upgrade
   torch to **2.6.0+cu124** (works on driver 535 via CUDA minor-version compat).
   The runner now auto-picks the transformers ceiling from the torch it finds
   (torch>=2.6 allows <4.54; older torch pins <4.50).
2. **torchvision ABI mismatch.** After the torch upgrade, loading the teacher
   crashed with `operator torchvision::nms does not exist` (torchvision 0.20.1
   was built against torch 2.5.1). Resolution: `torchvision==0.21.0` (cu124) to
   match torch 2.6.0. The `CHECK_ONLY=1` audit now flags a torch/torchvision
   mismatch before a run.
3. **vGPU allocator crash.** SFT died on the first CUDA allocation with
   `CUDA driver error: operation not supported`. Cause: `train_full.py` sets
   `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, whose CUDA virtual-memory
   APIs are unsupported on the A40-16Q vGPU. Distill survived because it does not
   set the flag. Resolution: export `expandable_segments:False` (now the runner
   default; also the repo default in `train_full.py`).
4. **Resume re-clone bug.** The clone check looked for `.git` in the `SETU/`
   subdir, but git puts it at the clone root `SETU_v2/.git`, so every resume tried
   to re-clone over the existing (distilled-corpus-bearing) tree and aborted.
   Fixed to detect the repo by the root `.git` or `pyproject.toml`.

## 3. Pipeline and model

Stages, each guarded by a `.done_*` marker so any disconnect resumes in place:

```
data  ->  distill (teacher 1-best, ~40 min)  ->  SeqKD SFT (multi-hour)  ->  quantize (INT8/INT4 ONNX)  ->  offline smoke-test  ->  zip
```

- **Student:** 52.6M-param Marian seq2seq, 16k SentencePiece vocab.
- **Data:** Samanantar (ungated); `LIMIT=500000` yields ~497k distilled pairs
  (the 250k run distilled 249,636).
- **Deployable artifact:** INT4 ONNX, **~103.9 MB** per direction (from ~410.9 MB
  FP32, ~4x compression), fully offline (ONNX Runtime + local SentencePiece).

## 4. Chronological runs

- **2026-07-29, Hindi->English @ 250k.** First full VM run. BLEU **22.10** / chrF
  49.81 / teacher 28.91 / **ratio 0.764**; p90 **198.5 ms**; **103.94 MB**;
  offline. **3/4 targets** (quality just short). Clean output
  ("भारत एक विशाल देश है।" -> "India is a huge country."). A clear jump over the
  notebook's 17.1 BLEU @ 100k, confirming SeqKD keeps scaling with data.
- **Hindi->English @ 500k.** BLEU 21.8 / teacher 27.1 / **ratio 0.806**: crosses
  the >=0.80 quality target on the primary pair. Scaling curve:
  **0.607 @100k -> 0.764 @250k -> 0.806 @500k**.
- **Bidirectional expansion @ 500k.** Trained both directions for 9 languages
  (Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, Kannada, Odia, Malayalam);
  Urdu explicitly out of scope. 18 directions total.
- **Two training collapses (LR 5e-4).** `tel_Telu-eng_Latn` (SFT loss 3.13, ratio
  0.036) and `mal_Mlym-eng_Latn` (loss 3.96, ratio 0.013) collapsed to degenerate
  "stock news" output ("The police have registered a case.") regardless of input.
  Tamil->En and Kannada->En at the same scale did **not** collapse, so this is
  training instability at LR 5e-4, not a data problem.
- **Recovery (LR 3e-4).** Keeping each collapsed run's good distilled corpus and
  redoing only SFT + quantize at `sft.lr: 3.0e-4` recovered both cleanly:
  - Telugu->En: loss 3.13 -> **1.49**, ratio 0.036 -> **0.817** (pass).
  - Malayalam->En: loss 3.96 -> ~1.91, ratio 0.013 -> **0.898** (pass);
    En->Malayalam also lifted 0.570 -> **0.863** (pass).

## 5. Final scorecard (18 directions, internal Samanantar dev slice, ratio = student BLEU / teacher BLEU)

| # | Direction | Pair | BLEU | Teacher | Ratio | >=0.80 |
|--:|-----------|------|-----:|--------:|------:|:------:|
| 1 | Marathi->En | mar_Deva-eng_Latn | 16.4 | 17.1 | **0.955** | pass |
| 2 | En->Kannada | eng_Latn-kan_Knda | 10.0 | 11.0 | **0.915** | pass |
| 3 | En->Marathi | eng_Latn-mar_Deva | 12.5 | 13.8 | **0.901** | pass |
| 4 | Malayalam->En (recovered) | mal_Mlym-eng_Latn | ~17 | 19.1 | **0.898** | pass |
| 5 | Odia->En | ory_Orya-eng_Latn | 18.9 | 21.0 | **0.898** | pass |
| 6 | En->Odia | eng_Latn-ory_Orya | 6.9 | 7.7 | **0.895** | pass |
| 7 | En->Hindi | eng_Latn-hin_Deva | 20.3 | 23.3 | **0.871** | pass |
| 8 | En->Malayalam (recovered) | eng_Latn-mal_Mlym | ~5 | 6.1 | **0.863** | pass |
| 9 | En->Gujarati | eng_Latn-guj_Gujr | 12.5 | 14.6 | **0.855** | pass |
| 10 | En->Bengali | eng_Latn-ben_Beng | 11.1 | 13.1 | **0.848** | pass |
| 11 | Telugu->En (recovered) | tel_Telu-eng_Latn | 18.9 | 23.1 | **0.817** | pass |
| 12 | Hindi->En | hin_Deva-eng_Latn | 21.8 | 27.1 | **0.806** | pass |
| 13 | Gujarati->En | guj_Gujr-eng_Latn | 18.8 | 23.9 | 0.787 | near |
| 14 | En->Telugu | eng_Latn-tel_Telu | 11.0 | 14.0 | 0.780 | near |
| 15 | Kannada->En | kan_Knda-eng_Latn | 16.3 | 21.4 | 0.763 | near |
| 16 | Tamil->En | tam_Taml-eng_Latn | 16.1 | 21.1 | 0.761 | near |
| 17 | Bengali->En | ben_Beng-eng_Latn | 19.1 | 25.2 | 0.756 | near |
| 18 | En->Tamil | eng_Latn-tam_Taml | 8.0 | 10.6 | 0.755 | near |

**After both recoveries: 12 / 18 directions pass >=0.80** (6 near-misses at
0.75-0.79, no collapses left). Mean ratio ~0.84, median ~0.85. Every model is
103.9 MB (<=200), mean latency 96-202 ms (<500), fully offline: the non-quality
targets pass across the board.

> Timeline note: the session's own `ANALYSIS.md` / `SCORES.md` (on the training
> machine) were last regenerated at the **10/18** point, just before the
> Malayalam retrain landed. The two Malayalam directions above (0.898, 0.863)
> were confirmed at the very end of the session, bringing the total to 12/18;
> those files need one more `--store` + rebuild to show it.

## 6. Findings

- **SeqKD scales with data.** 0.607 -> 0.764 -> 0.806 for Hindi->En at 100k/250k/500k,
  breaking the ~0.66 plateau that reference-target SFT hit.
- **Learning rate is the stability knob.** LR 5e-4 collapsed two Indic->En
  students to degenerate output; **LR 3e-4 is the safe default** and recovered
  both to passing. **SFT loss is the tell**: healthy runs sit at 1.5-2.3,
  collapses at 3-4.
- **BLEU understates agglutinative languages.** En->Malayalam produces correct
  output yet scored BLEU 3.5 (the teacher itself only 6.1). Judge Malayalam and
  Tamil with **COMET** (`setu-eval --comet`); several near-misses may already
  pass there.
- **Direction symmetry.** En->Indic (~0.82 mean) and Indic->En are level once the
  collapses are excluded.
- **Complex-syntax probe held up.** Conditionals, reported speech, and 5+-clause
  sentences survived across Tier-A/B models; round-trip (En->Hindi->En) preserved
  meaning. Weak spots (Kannada, the pre-recovery collapses) matched the scorecard.

## 7. Quality tiers and companion artifacts

- **Tier A (ship both ways):** Marathi, Odia, Hindi, Malayalam (post-recovery).
- **Tier B (one pass, one near):** Kannada, Gujarati, Bengali, Telugu.
- **Tier C (both near):** Tamil.

Companion tooling built during the campaign (on the training machine):
`translate.py` (per-pair inference wrapper, no `model.yaml` edit, plus a
`--store` showcase generator), `vm/out/sample_translations.md`,
`vm/out/complex_translations.md`, `vm/out/ANALYSIS.md`, `vm/out/SCORES.md`.

## 8. Remaining work

- **The other 12 scheduled languages** (Assamese, Bodo, Dogri, Konkani, Kashmiri,
  Maithili, Manipuri, Nepali, Punjabi, Sanskrit, Santali, Sindhi) are the main
  outstanding goal: train them bidirectionally to the same bar, using LR 3e-4 and
  whatever Samanantar volume the low-resource tail has.
- **Lift the 6 near-misses** with `--beams 4` at eval, more SFT epochs, or more
  distilled data.
- **Publishable numbers:** re-score every direction on FLORES-200 with
  `setu-eval --testset flores --teacher` (the ratios above are the internal
  Samanantar dev slice), and add COMET.

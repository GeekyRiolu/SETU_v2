# SeqKD vs DPO-distill — the paper's head-to-head

The core research question is whether **preference/DPO distillation (S2)** beats
the standard **sequence-level KD baseline (S1)** at matched student size. This
doc is how to run that comparison. Infra is built (`setu-distill` + the
`--train-corpus` flag); the turnkey notebook is `kaggle/setu_seqkd_compare.ipynb`.

## The systems (all same 52M student, same dev set)

| System | SFT targets | DPO? | Command |
|--------|-------------|------|---------|
| **S0** SFT (refs) | human references | no | `train_full.py --train-corpus processed --skip-dpo` |
| **S1** SeqKD | teacher 1-best | no | `train_full.py --train-corpus distilled --skip-dpo` |
| **S2** DPO-distill (ours) | human references | yes | `train_full.py --train-corpus processed` |
| **S3** SeqKD + DPO | teacher 1-best | yes | `train_full.py --train-corpus distilled` |

Eval is **always on real references** held out from `data/processed` — fair
regardless of what the student trained on (the pipeline enforces this).

## Steps

```bash
# 0. data + preferences (prefs only needed for the DPO variants)
setu-data   --limit 102000
setu-prefs  --max-entries 8000

# 1. teacher-distilled corpus (teacher 1-best targets) — the expensive step
setu-distill --limit 100000        # writes data/distilled/<pair>/train.jsonl

# 2. train the variants (save each report — train_report.json is overwritten)
python scripts/train_full.py --train-corpus distilled --skip-dpo --limit 100000 --dev-size 500
cp checkpoints/<pair>/train_report.json report_S1_seqkd.json

python scripts/train_full.py --train-corpus processed --limit 100000 --dev-size 500
cp checkpoints/<pair>/train_report.json report_S2_dpo.json     # has S0 (sft_eval) + S2 (dpo_eval)
```

## What to read from the reports

- **S1** = `report_S1_seqkd.json` → `sft_eval` (BLEU/chrF/ratio).
- **S0** = `report_S2_dpo.json` → `sft_eval`.
- **S2** = `report_S2_dpo.json` → `dpo_eval`.

Fill `docs/PAPER_PLAN.md` Table 1. The headline question: **does S2 (or S3) beat
S1** on BLEU/chrF at matched size? A win — or a clean, analysed null — is the
paper's contribution.

## Cost & scale

Each training is hours on a T4; the distill step is teacher inference over
`--limit` sources. Use `--limit 100000` for a controlled comparison (~5–6 h
total in `setu_seqkd_compare.ipynb`); lower it if GPU budget is tight. Keep the
limit identical across S0–S3 so the comparison is fair.

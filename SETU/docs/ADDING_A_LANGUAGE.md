# Adding a language

Adding a language to SETU is a **config + data** change, not a rewrite — the
whole architecture is built around that. Two paths, depending on whether you
already have a multilingual student:

## The identity layer (always start here)

1. Confirm the language is in `configs/languages.yaml` (all 22 scheduled
   languages + English pivot ship by default, with dual-script entries for
   Kashmiri, Manipuri, Sindhi). Its `flores` code is reserved as a tokenizer
   tag, so token ids stay stable as you widen — no re-tokenisation of old
   languages.
2. Point the data pipeline at a corpus for the new direction (`configs/data.yaml`)
   and run `setu-data --pair <flores>-eng_Latn`.
3. Generate preferences and (if training from scratch) run `setu-train`.

## Path A — batch expansion with AIO-KD (`src/setu/training/aio_kd.py`)

Best when growing the student across several new directions at once.

1. Build a `CorpusDataset` per direction and pass them to `AIOKDOrchestrator`
   keyed by `<src_flores>-<tgt_flores>`.
2. Set `sampling_temperature` in `configs/training.yaml` (`aio_kd`): `1.0`
   samples in proportion to data size (high-resource dominates), higher values
   flatten toward uniform and protect low-resource directions. `1.5` is a good
   default.
3. Train; check `orchestrator.coverage()` to confirm every direction was
   sampled, and run the per-direction eval for a coverage report (BLEU / ChrF /
   latency per language).

## Path B — incremental expansion with EWC (`src/setu/training/ewc.py`)

Best when adding **one** language to an existing student **without a full
retrain** and without forgetting the old languages.

1. Snapshot the current student and estimate Fisher importance on the OLD
   languages' data:
   `reg = EWCRegularizer.from_old_task(model, old_dataset, lam, fisher_samples)`.
   Tune `lambda` in `configs/training.yaml` (`ewc.lambda`): higher = protect old
   languages harder (less plasticity for the new one).
2. Train on the new language with `ewc_train_step(model, opt, batch, reg)` — the
   Fisher-weighted penalty is added to the task loss automatically.
3. **Prove it worked.** Catastrophic forgetting is invisible unless you measure
   the old languages *after* expansion:

   ```
   before = evaluate_model(old_translate, old_sources, old_refs)   # pre-expansion
   ...train new language with EWC...
   after  = evaluate_model(old_translate, old_sources, old_refs)   # post-expansion
   assert after["bleu"] >= before["bleu"] * RETENTION_THRESHOLD     # e.g. 0.95
   ```

   Record both numbers. If old-language BLEU drops below the retention
   threshold, raise `lambda` or add rehearsal data and repeat.

## Checklist for a new language

- [ ] Present in `configs/languages.yaml` with correct FLORES + script
- [ ] Corpus wired in `configs/data.yaml`; `setu-data` run
- [ ] Preferences generated (`setu-prefs`) if using DPO
- [ ] Trained via AIO-KD (Path A) or EWC (Path B)
- [ ] Coverage report (per-direction BLEU/ChrF/latency)
- [ ] For EWC: before/after eval on existing languages proving retention

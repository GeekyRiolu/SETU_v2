# SETU — research paper plan

Turns the SETU engineering into a publishable empirical study. The framework is
the *apparatus*; the paper needs a *finding*. This document defines the finding,
the experiments, and the exact tables to fill so the Kaggle runs produce
paper-ready numbers instead of just "it works".

Status: draft plan, pre-results. Update as GPU results land.

---

## 1. The research question

> **Does preference-based distillation (rank teacher hypotheses → DPO) produce
> better compact multilingual NMT students than standard sequence-level knowledge
> distillation, particularly for low-resource Indic languages — and can such a
> student be expanded to new languages without catastrophic forgetting?**

Two contributions if the answers are yes (or interestingly no):
1. **Preference distillation vs. sequence-level KD** for compact NMT (the core).
2. **EWC-based language expansion** of an on-device multilingual student, with
   measured retention (a systems/continual-learning angle).

Plus a **systems contribution**: the offline, ≤200 MB, <500 ms deployment.

## 2. Positioning (verify against recent work before submitting)

- Sequence-level KD for NMT: Kim & Rush (2016) — the standard strong baseline.
- DPO: Rafailov et al. (2023) — preference optimization without a reward model.
- IndicTrans2 (AI4Bharat) — the teacher and the 200M distilled comparison point.
- EWC: Kirkpatrick et al. (2017) — continual learning.
- Multilingual KD / temperature sampling for balancing — prior multilingual NMT.

**Gap we occupy:** preference/DPO-style distillation is well studied for LLM
alignment but under-explored for *NMT distillation into tiny on-device students*,
especially low-resource Indic. That's the novelty lever — confirm no 2025/26
paper already did exactly this.

## 3. Hypotheses

- **H1:** At a fixed small student size, DPO-distillation ≥ sequence-level KD in
  BLEU/chrF/COMET on Indic↔English (esp. low-resource).
- **H2:** ChrF-ranked preference pairs (+ kNN-retrieved negatives) beat random or
  score-agnostic negatives (ablation).
- **H3:** EWC-expansion adds a new language while retaining ≥ 95% of prior-language
  BLEU, vs. large drops for naïve fine-tuning.
- **H4:** The quantised student meets <500 ms (ARM) and ≤200 MB with < X BLEU drop.

## 4. Experimental design

### 4.1 Models (all at matched student size for fair comparison)

| System | Description |
|--------|-------------|
| Teacher | IndicTrans2 (1B if HF-authorised; else dist-200M) — ceiling |
| S0: SFT-only | student trained on teacher/ref targets, no distillation objective |
| S1: SeqKD | **baseline** — sequence-level KD on teacher 1-best (Kim & Rush) |
| S2: DPO-distill | **ours** — SFT then DPO on ChrF-ranked preference pairs |
| S3: SeqKD+DPO | SeqKD init, then DPO (does DPO help *on top of* strong KD?) |

Student: the `model.gpu.yaml` config (d=512, 6+6, ~52M) and at least one smaller
size for a size-vs-quality curve.

### 4.2 Data

- Train: BPCC + Samanantar (full where feasible; Samanantar is ungated).
- Languages: start Hindi↔English; extend to a **high/mid/low-resource spread**
  (e.g. hi, ta, bn = higher; as, mai, brx = lower) for the multilingual claim.
- Eval: **FLORES-200 devtest** and **IN22** (standard, comparable to IndicTrans2).

### 4.3 Metrics

- **BLEU** (sacreBLEU, report signature), **chrF++**, and **COMET** (learned;
  expected by reviewers now).
- **Statistical significance:** paired bootstrap resampling (sacreBLEU) between
  S1 and S2.
- **Systems:** artifact MB (FP32/INT8/INT4), latency p50/p90/max on x86 **and an
  ARM profile** (Raspberry Pi 4 / Cortex-A55 or QEMU), offline verification.

## 5. Results tables to fill (templates)

### Table 1 — main comparison (per direction, FLORES/IN22)

| System | Params | hi→en BLEU | chrF++ | COMET | en→hi BLEU | … | % of teacher BLEU |
|--------|-------:|-----------:|-------:|------:|-----------:|---|------------------:|
| Teacher | — | | | | | | 100% |
| S0 SFT | | | | | | | |
| S1 SeqKD | | | | | | | |
| **S2 DPO-distill** | | | | | | | |
| S3 SeqKD+DPO | | | | | | | |

Headline number: **% of teacher BLEU** (the ≥80% target) and S2 − S1 with
significance.

### Table 2 — preference-construction ablation (H2)

| Negatives | Ranking | BLEU | chrF++ |
|-----------|---------|-----:|-------:|
| random | none | | |
| teacher n-best only | ChrF | | |
| **+ kNN neighbours** | **ChrF** | | |

### Table 3 — quantisation (H4)

| Precision | Size (MB) | BLEU | chrF++ | p90 latency x86 | p90 latency ARM |
|-----------|----------:|-----:|-------:|----------------:|----------------:|
| FP32 ONNX | | | | | |
| INT8 | | | | | |
| INT4 | | | | | |

### Table 4 — EWC language expansion (H3)

| Setting | new-lang BLEU | old-lang BLEU (before→after) | retention % |
|---------|--------------:|:----------------------------:|------------:|
| naïve fine-tune | | → | |
| **EWC** | | → | |

### Table 5 — size-vs-quality curve

Student sizes (e.g. 9.5M / 25M / 52M) × BLEU × latency × MB — the on-device
Pareto front.

## 6. Ablations & analysis

- DPO β sweep; effect of `quality_delta` threshold and #candidates.
- Cross-lingual balancing temperature (AIO-KD) vs. per-language BLEU.
- Qualitative error analysis (adequacy/fluency on a sample).
- Failure modes of the tiny student (what the ≤200 MB budget costs).

## 7. Threats to validity

- Teacher choice (dist-200M vs 1B) caps the ceiling — report which.
- BLEU limitations → COMET + human/qualitative check.
- Single-reference eval; script/tokenisation effects for Indic → chrF++ helps.

## 8. Target venues

- **Workshops (best fit):** WMT, LoResMT, Indic-NLP (ICON / ACL-NAACL-EMNLP
  workshops). Value reproducibility, low-resource, on-device.
- **Demo track:** ACL/EMNLP system demonstrations — the offline toolkit.
- **Main track:** only if S2 vs S1 is a strong, significant, multi-language result.
- **arXiv preprint** regardless.

## 9. What to run on Kaggle to get paper-ready numbers

Beyond the current single-run notebook:

1. Train **S1 (SeqKD)** and **S2 (DPO-distill)** at the *same* student size —
   add a SeqKD trainer (train on teacher 1-best) alongside the existing DPO path.
2. Evaluate on **FLORES devtest + IN22** (not just a held-out slice) with
   **BLEU + chrF++ + COMET** and bootstrap significance.
3. Run the **preference ablation** (Table 2) and **β sweep**.
4. Add ≥ 2 more languages (incl. a low-resource one) for the multilingual claim.
5. Run the **EWC expansion** experiment (Table 4) with real before/after BLEU.
6. Produce the **quantisation table** (Table 3) incl. an ARM latency profile.

### Engineering deltas needed (not yet built)

- [ ] SeqKD trainer (sequence-level KD on teacher 1-best) as the S1 baseline.
- [ ] COMET into the eval harness.
- [ ] FLORES/IN22 eval-set loaders.
- [ ] Bootstrap significance in the eval report.
- [ ] Multi-language training config + per-language eval loop.
- [ ] ARM latency benchmark (QEMU or a Pi).

## 10. Honest go/no-go

Publish-worthy **iff** S2 (or S3) shows a real, significant BLEU/COMET advantage
over S1 SeqKD at matched size across languages — or a clean, well-analysed
negative result. Without that comparison it's a good system, not a paper.

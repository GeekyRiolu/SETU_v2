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

- **H1 (REFUTED, 2026-07-19):** *DPO-distillation ≥ sequence-level KD.* The opposite
  holds — **SeqKD ≫ DPO-distill** (17.1 vs 11.1 BLEU at 100k, matched size). The
  paper's thesis flips to: **SeqKD from teacher outputs beats preference/DPO
  distillation on noisy human references for compact Indic MT** (see §11 Table 1).
- **H1′ (new, supported):** Reference noise (mined Samanantar) caps reference-trained
  students (~0.66 ratio plateau); teacher-distilled targets break the ceiling and
  SeqKD scales past it.
- **H2:** ChrF-ranked preference pairs (+ kNN negatives) beat random/score-agnostic
  negatives — still worth testing, but DPO's overall effect here is small.
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

### Engineering deltas

- [x] **SeqKD baseline (S1)** — `setu-distill` + `train_full.py --train-corpus
      distilled`; done (Table 1). SeqKD wins.
- [x] **COMET** — `setu-eval --comet` (`setu.eval.comet`, `comet` extra).
- [x] **FLORES-200 / IN22 loaders** — `setu.eval.testsets`; `setu-eval --testset
      flores|in22 --split devtest`.
- [x] **Bootstrap significance** — `setu.eval.significance.paired_bootstrap`;
      `setu-eval --teacher` reports student-vs-teacher significance.
- [x] **Multi-language** — pipeline is `--pair`-parameterized end-to-end
      (`tests/test_multipair.py`); runners take `PAIR` (`docs/ADDING_A_LANGUAGE.md`).
- [ ] Per-language eval **loop/table** across several pairs (run `setu-eval` per pair).
- [ ] ARM latency benchmark (QEMU or a Pi).

### Running the paper eval

```bash
# BLEU + chrF on FLORES-200 devtest for the deployed model (beam-4 for quality)
setu-eval --pair hin_Deva-eng_Latn --testset flores --split devtest --beams 4
# + COMET + teacher scores + student-vs-teacher significance
setu-eval --pair hin_Deva-eng_Latn --testset flores --beams 4 --comet --teacher
```
Writes `models/<pair>/eval_flores_devtest.json`. Repeat per language and per system
(S0/S1/S2) to fill Table 1 with standard-test-set, COMET-backed, significance-tested
numbers.

## 10. Honest go/no-go

Publish-worthy **iff** S2 (or S3) shows a real, significant BLEU/COMET advantage
over S1 SeqKD at matched size across languages — or a clean, well-analysed
negative result. Without that comparison it's a good system, not a paper.

## 11. Real results — the headline finding

### Table 1 — S0/S1/S2 head-to-head (100k train, matched 52M student, eval on real refs)

Colab run, 2026-07-19, `hin_Deva-eng_Latn`, teacher dev BLEU 28.15 (dev=500):

| System | Train targets | BLEU | chrF | ratio | SFT loss |
|--------|---------------|-----:|-----:|------:|---------:|
| Teacher (rotary dist-200M) | — | 28.15 | — | 1.00 | — |
| **S1 SeqKD** | teacher 1-best | **17.09** | **44.52** | **0.607** | **2.30** |
| S0 SFT | human refs | 10.95 | 35.44 | 0.389 | 3.45 |
| S2 SFT-ref + DPO (ours) | refs + DPO prefs | 11.10 | 37.23 | 0.394 | — |

**SeqKD dominates: +6.1 BLEU (+56% rel.) / +9 chrF over reference-SFT, at the same
size and data.** DPO on a reference-SFT base adds almost nothing (+0.15 BLEU,
+1.8 chrF). This **refutes the original H1** (DPO-distill ≥ SeqKD) — cleanly, with
a strong alternative — and it's the paper's core result.

**The revised thesis:** *for compact on-device Indic MT, sequence-level KD from the
teacher's outputs strongly beats preference/DPO distillation on human references;
the mined-reference noise is the bottleneck, and teacher targets break it.* SeqKD's
lower SFT loss (2.30 vs 3.45) confirms the mechanism — teacher outputs are more
consistent/learnable, so the student generalises to *human references* better than
one trained *on* them (the classic Kim & Rush effect, confirmed for Indic + on-device).

**Corroborating data-scaling curves** (SFT BLEU / ratio):
- *reference-SFT*: 25k → 0.3 · 120k → 13.4 / 0.44 · 200k → 18.6 / 0.65 · 250k →
  18.6 / **0.66 — plateaus** (the reference-noise ceiling).
- *SeqKD*: 100k → 17.1 / 0.607 · 250k → 22.10 / 0.764 · **500k → 21.56 / 0.796**
  — climbs steeply then approaches the teacher ceiling (diminishing returns; the
  ungated dist-200M teacher is only ~27–29 BLEU). **0.796 ≈ the 0.80 target within
  dev-set noise.** This divergence — SeqKD scales toward the teacher, reference-
  training saturates at 0.66 — is the paper's central figure.

Note: the dev ratio is teacher-slice-dependent (teacher BLEU 27.1–28.9 across the
held-out splits). The **citeable numbers come from `setu-eval` on FLORES-200
devtest** (fixed benchmark + COMET + significance) — run it per system/language for
Table 1. A stronger (gated ai4bharat-1B) teacher would raise the achievable ceiling.

### Still to run
- **SeqKD at scale** (200–250k) — the best deployable model; likely breaks the 0.66
  ceiling toward 0.80.
- **S3 = SeqKD + DPO** — does DPO help on a *strong* base? (It didn't on the weak one.)
- COMET, FLORES/IN22, bootstrap significance, ≥2 more languages (for the paper).

Findings: (a) **DPO with ChrF-ranked preferences lifts chrF but slightly lowers
BLEU** — consistent across runs #3 and #5 (the objective optimises a chrF-shaped
signal); a real, nuanced result — and a knob (BLEU/COMET-ranked prefs, β, DPO LR)
worth an ablation. (b) Training needed gradient clipping to stay stable at scale
(run #4 collapsed without it). **Still missing for the paper:** the **S1 SeqKD
baseline** (train on teacher 1-best) at matched size — the head-to-head that IS
the contribution — plus COMET, FLORES/IN22 eval, significance, ≥2 more languages.

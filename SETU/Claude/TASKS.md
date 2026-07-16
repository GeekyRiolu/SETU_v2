# SETU — Task Checklist

Offline multilingual translation for the 22 scheduled Indian languages. Teacher = IndicTrans2 (already cloned). Students = compact SLMs trained with preference pairs + DPO, scaled with AIO-KD, expanded with EWC, deployed as quantised ONNX on edge devices.

**Golden rule:** build one language pair end-to-end first (Hindi↔English), then widen. Don't start all 22 at once.

**Definition of done (targets to verify, not assume):**
- Quality: student keeps ≥ 80% of IndicTrans2 BLEU
- Latency: < 500 ms/sentence on ARM-class CPU
- Size: ≤ 200 MB quantised ONNX artifact
- Offline: no network calls at inference; no user text leaves the device

Tick boxes as you go. Each milestone should end with a short note on what was built and which target it moves.

---

## M0 — Scaffold
Get a skeleton that runs before any real logic exists.

- [x] Create repo structure (`src/setu/`, `interfaces/`, `configs/`, `data/`, `benchmarks/`, `tests/`)
- [x] `pyproject.toml` or `requirements.txt` (Python 3.10+)
- [x] `configs/languages.yaml` — registry of all 22 languages with ISO codes + script per language
- [x] `configs/model.yaml` and `configs/training.yaml` stubs (no hard-coded language pairs anywhere)
- [x] Stub `InferenceEngine` that returns a passthrough "translation" so the pipeline is callable
- [x] Minimal CLI wired to the stub: `python setu.py --src hi --tgt en --text "..."`
- [x] `README.md` with setup + run instructions
- [x] Basic test that imports the package and runs the stub

**Done when:** the CLI runs end-to-end with a fake translation and one test passes. ✅

> **M0 note (2026-07-16):** Scaffold complete. `src/`-layout package with the four stable
> data objects (`types.py`), YAML-driven config (`config.py` — 22 languages + English
> pivot with ISO→FLORES mapping matching IndicTrans2), passthrough `InferenceEngine`,
> CLI (`setu.py` / `setu.cli`), 7 smoke tests green. No target moved yet (stub engine) —
> this milestone makes the pipeline callable so later milestones can be measured.

---

## M1 — Data Pipeline (one pair)
Get clean Hindi↔English data ready for training.

- [x] `CorpusLoader` reads BPCC + Samanantar into the `CorpusEntry` shape
- [x] Script normalisation & cleaning
- [x] Sentence alignment
- [x] Deduplication + basic quality filtering
- [x] Write processed data to `data/processed/`
- [x] Short data report: counts, before/after dedup, a few sample rows
- [x] Ask before any large download; check disk space first

**Done when:** a clean, deduped Hindi↔English parallel set exists on disk with a summary. ✅

> **M1 note (2026-07-16):** Pipeline = load → normalise (NFC, control-char strip, ZWJ/ZWNJ
> preserved) → filter (length, length-ratio alignment check, script check) → exact dedup →
> JSONL + report. Sample run: 50,000 Samanantar pairs streamed → **49,520 kept** (476
> filtered: 253 length_ratio, 213 wrong-script, 10 too_long; 4 dups) at
> `data/processed/hin_Deva-eng_Latn/train.jsonl`. Disk checked first (378 GB free).
> **Open items:** (1) BPCC is a *gated* HF dataset — the `hf_zip` adapter for BPCC-seed
> (67 MB) is wired but skipped until the user accepts terms + `huggingface-cli login`;
> (2) full corpora (14.8 GB mined BPCC, ~1.9 GB Samanantar-hi) are opt-in — set
> `sample_limit: null` after approval. Target moved: none directly — this feeds M3/M4 quality.

---

## M2 — Teacher Integration (IndicTrans2)
Wrap the already-cloned teacher behind a stable interface.

- [ ] Inspect the local IndicTrans2 clone: report its path, required checkpoints, and language-code mapping; flag anything missing
- [ ] Implement `TeacherModel` exposing `generate_candidates(src_text, src_lang, tgt_lang) -> list[str]`
- [ ] Add a quality score per candidate (ChrF)
- [ ] Nothing outside this module may import IndicTrans2 internals
- [ ] Smoke test: feed a few Hindi sentences, confirm sensible English candidates

**Done when:** the pipeline can call `TeacherModel` and get candidates + scores, with IndicTrans2 fully hidden behind the interface.

---

## M3 — Preference Generation
Turn teacher outputs into preference pairs for DPO.

- [ ] Build the candidate set via kNN retrieval
- [ ] Rank candidates by ChrF
- [ ] Construct `PreferencePair` objects (preferred / dispreferred) with `quality_delta`
- [ ] Write pairs to `data/preferences/`
- [ ] Add an automated sanity check: preferred ChrF > dispreferred ChrF for every pair
- [ ] Report: number of pairs, quality_delta distribution, a few examples

**Done when:** a validated `PreferencePair` dataset exists for Hindi↔English.

---

## M4 — DPO Training (one pair)
Train the student and prove it beats the plain baseline.

- [ ] Set up an SFT/distilled student baseline (this becomes the frozen reference model)
- [ ] Implement `DPOTrainer` with the standard DPO loss (no reward model, no policy gradient)
- [ ] Reference model = frozen student snapshot
- [ ] Config-driven hyperparameters (`configs/training.yaml`)
- [ ] Eval harness reporting BLEU, ChrF, latency vs the baseline and vs the teacher
- [ ] Pick best checkpoint

**Done when:** the DPO student beats the SFT baseline on Hindi↔English and the eval report shows how close it is to teacher BLEU (target ≥ 80%).

---

## M5 — Quantise + Export + Offline Inference
Make it small, fast, and internet-free.

- [ ] INT8 post-training quantisation with a benchmark (accuracy + size)
- [ ] INT4 quantisation with a benchmark (do INT8 first, then INT4 — progressive)
- [ ] Export to ONNX; validate with ONNX Runtime
- [ ] Real `InferenceEngine` running the ONNX model (replaces the M0 stub)
- [ ] Latency benchmark on ARM-class device (Raspberry Pi 4 / Cortex-A55, or emulated)
- [ ] Size check: artifact ≤ 200 MB
- [ ] Offline test: run inference with networking disabled — must succeed
- [ ] Audit the inference path for any outbound request — there should be none

**Done when:** a ≤ 200 MB ONNX model translates Hindi↔English offline under 500 ms/sentence, verified by benchmarks.

---

## M6 — Interfaces
Expose the same engine four ways.

- [ ] REST API (FastAPI): `POST /translate` with `{source_lang, target_lang, text}` → `TranslationResult`
- [ ] CLI: finalise `python setu.py --src hi --tgt en --text "..."` (file / stdin input too)
- [ ] Mobile SDK stubs: `translate(text, srcLang, tgtLang)` for Android + iOS
- [ ] Offline PWA: pick languages, enter text, get translation; caches assets so it works with no connectivity after first load
- [ ] All four call the **same** `InferenceEngine` — no duplicated translation logic
- [ ] Integration test hitting the REST endpoint

**Done when:** all four interfaces translate through one shared engine.

---

## M7 — Multilingual (AIO-KD)
Scale from one pair to many.

- [ ] Language-wise student initialisation
- [ ] `AIOKDOrchestrator` trains one student across multiple directions at once
- [ ] Cross-lingual balancing so high-resource languages don't drown out low-resource ones
- [ ] Roll out in batches of languages, not all 22 at once
- [ ] Per-language eval coverage report (BLEU / ChrF / latency)

**Done when:** a single student covers several languages with a coverage report, and adding more is a config change, not a rewrite.

---

## M8 — Continual Learning (EWC)
Add languages without breaking old ones.

- [ ] `EWCRegularizer`: Fisher-weighted penalty protecting parameters important to already-learned languages
- [ ] Add one new language incrementally (no full retrain)
- [ ] Before/after eval on existing languages proving quality is preserved within threshold
- [ ] Document the expansion procedure so it's repeatable

**Done when:** a new language is added and prior-language quality holds steady (no catastrophic forgetting).

---

## M9 — Hardening & Wrap-up
Make it robust and prove the targets.

- [ ] Cross-device benchmark matrix (a few hardware profiles)
- [ ] Fill out unit + integration tests; get the suite green
- [ ] Complete docs: README, per-module notes, how to add a language
- [ ] Final report scoring the build against every target above (pass/fail per criterion)
- [ ] Clean up configs and remove dead code

**Done when:** the final report shows each success criterion as pass, with links to the benchmarks that prove it.

---

## Data objects (keep these names stable everywhere)

- **PreferencePair** — `src_text, src_lang, tgt_lang, preferred_tgt, dispreferred_tgt, quality_delta`
- **ModelConfig** — `language_pair, params, quantization`
- **TranslationResult** — `translated_text, src_lang, tgt_lang, bleu, chrf, latency_ms`
- **CorpusEntry** — `src_lang, tgt_lang, src_text, tgt_text, source`

## Risks & mitigations (watch for these)

- Low-resource data scarcity → synthetic augmentation + retrieval-based expansion
- Catastrophic forgetting on expansion → EWC
- Quantisation accuracy drop → progressive benchmarking (INT8 before INT4)
- Weak low-end hardware → cross-device optimisation
- Bad preference data → automated preference validation (M3 sanity check)

## Not in Phase I

Speech translation, document-layout-preserving translation, a hosted cloud service, dialect coverage beyond the 22 languages. Note them, don't build them yet.

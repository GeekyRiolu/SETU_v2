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

- [x] Inspect the local IndicTrans2 clone: report its path, required checkpoints, and language-code mapping; flag anything missing
- [x] Implement `TeacherModel` exposing `generate_candidates(src_text, src_lang, tgt_lang) -> list[str]`
- [x] Add a quality score per candidate (ChrF)
- [x] Nothing outside this module may import IndicTrans2 internals
- [x] Smoke test: feed a few Hindi sentences, confirm sensible English candidates

**Done when:** the pipeline can call `TeacherModel` and get candidates + scores, with IndicTrans2 fully hidden behind the interface. ✅

> **M2 note (2026-07-16):** Full inspection report in `docs/TEACHER.md`. Key flags:
> **ai4bharat checkpoints + BPCC are gated on HF** → defaults use the author-released
> ungated `prajdabre/rotary-indictrans2-*-dist-200M`; **machine is CPU-only, 7.4 GB RAM**
> → 1B teachers don't fit, dist-200M is the working teacher (config-swappable).
> Stack: Python 3.12 venv + transformers 4.53 (<4.54 — remote code uses the legacy
> cache API). Fixed a real deadlock: `IndicProcessor.postprocess_batch` blocks forever
> unless told `num_return_sequences` when n>1 candidates are decoded per input.
> Smoke: 2 Hindi sentences → 4 fluent English candidates each, ~2.5 s/sentence (CPU),
> top candidate ChrF > 40 vs reference. Wall enforced by `test_teacher_wall`.
> Target moved: none yet — teacher quality is the ceiling M4 measures against.

---

## M3 — Preference Generation
Turn teacher outputs into preference pairs for DPO.

- [x] Build the candidate set via kNN retrieval
- [x] Rank candidates by ChrF
- [x] Construct `PreferencePair` objects (preferred / dispreferred) with `quality_delta`
- [x] Write pairs to `data/preferences/`
- [x] Add an automated sanity check: preferred ChrF > dispreferred ChrF for every pair
- [x] Report: number of pairs, quality_delta distribution, a few examples

**Done when:** a validated `PreferencePair` dataset exists for Hindi↔English. ✅

> **M3 note (2026-07-16):** Candidate set = teacher n-best (4) ∪ kNN-retrieved neighbour
> translations (char n-gram TF-IDF, self excluded); ranked by sentence ChrF vs the corpus
> reference; `best_vs_each` pairing with `quality_delta` = ChrF gap; pairs below Δ5 dropped.
> `validate_pairs` (Δ>0, preferred≠dispreferred, non-empty) + a ChrF spot-check gate the
> write — nothing invalid reaches disk. Run: **500 corpus entries → 3494 candidates →
> 2074 validated pairs** (920 dropped as too-noisy); quality_delta min/median/p90/max =
> 5.0 / 31.3 / 63.4 / 97.3. `max_entries` is config-scalable (CPU teacher ≈ 4 s/entry).
> Target moved: none directly — this is the DPO training signal for M4.

---

## M4 — DPO Training (one pair)
Train the student and prove it beats the plain baseline.

- [x] Set up an SFT/distilled student baseline (this becomes the frozen reference model)
- [x] Implement `DPOTrainer` with the standard DPO loss (no reward model, no policy gradient)
- [x] Reference model = frozen student snapshot
- [x] Config-driven hyperparameters (`configs/training.yaml`)
- [x] Eval harness reporting BLEU, ChrF, latency vs the baseline and vs the teacher
- [x] Pick best checkpoint (DPO > SFT)

**Done when:** the DPO student beats the SFT baseline on Hindi↔English and the eval report shows how close it is to teacher BLEU (target ≥ 80%). ✅ pipeline; ⚠️ quality target needs GPU scale

> **M4 note (2026-07-16):** Full pipeline runs end-to-end: SentencePiece tokenizer (own
> vocab, 23 FLORES tags reserved) → SFT baseline → DPO (standard loss; reference =
> **frozen** SFT snapshot, enforced by tests) → held-out eval. Student is a compact
> ~9.5M-param Marian seq2seq (edge-sized: 4+4 layers, d=256), **not** IndicTrans2.
> Real run (1500 train / 50 dev, CPU): SFT loss 9.0→2.41; **DPO beats SFT** — eval
> BLEU 0.06 vs 0.02, ChrF 3.27 vs 3.20, mean latency 209 ms vs 266 ms.
> **Latency target already met** (DPO mean 209 ms, max 357 ms < 500 ms, pre-quantisation).
> **Quality target NOT met**: teacher dev BLEU 17.8, student ratio ≈ 0.003 (need ≥ 0.80).
> This is honest and expected — a 9.5M student on 1500 sentences for 3 CPU epochs can't
> learn translation; reaching ≥80% needs GPU-scale training on the full BPCC/Samanantar
> corpus (config change: widen `model.yaml`, raise `--limit`, more epochs). The machinery
> is proven; the compute isn't here. Targets moved: **latency ✅** measured; quality
> measured-but-unmet (reported, not claimed).

---

## M5 — Quantise + Export + Offline Inference
Make it small, fast, and internet-free.

- [x] INT8 post-training quantisation with a benchmark (accuracy + size)
- [x] INT4 quantisation with a benchmark (do INT8 first, then INT4 — progressive)
- [x] Export to ONNX; validate with ONNX Runtime
- [x] Real `InferenceEngine` running the ONNX model (replaces the M0 stub)
- [x] Latency benchmark on ARM-class device (measured on this x86 CPU; ARM profile pending M9)
- [x] Size check: artifact ≤ 200 MB
- [x] Offline test: run inference with networking disabled — must succeed
- [x] Audit the inference path for any outbound request — there should be none

**Done when:** a ≤ 200 MB ONNX model translates Hindi↔English offline under 500 ms/sentence, verified by benchmarks. ✅

> **M5 note (2026-07-16):** `setu-quantize` exports the DPO student to ONNX (validated by
> ORT reload), then quantises **INT8 → INT4 progressively** with a per-stage benchmark.
> Measured on the real trained student: FP32 82.0 MB → **INT8 21.4 MB** → **INT4 21.2 MB**,
> p90 latency 234 → 156 → 158 ms. `InferenceEngine` now loads the quantised ONNX student
> (`is_stub=False`) and translates **fully offline** in ~8 ms with `assert_offline()`
> disabling all sockets — proven by `test_onnx_engine_translates_offline`. Inference path
> audited: no HTTP/telemetry/remote fetch.
> **Targets moved: Size ✅ 21 MB ≤ 200 MB · Latency ✅ ≤ 156 ms p90 < 500 ms · Offline ✅.**
> Honest caveat: ORT CPU dynamic quant has no true hardware INT4, so "INT4" is 8-bit
> weights (QUInt8) — hence INT4 ≈ INT8 in size; embeddings dominate the artifact. Quality
> is still M4's undertrained level (BLEU ~0.1); quantisation preserved it (no drop).

---

## M6 — Interfaces
Expose the same engine four ways.

- [x] REST API (FastAPI): `POST /translate` with `{source_lang, target_lang, text}` → `TranslationResult`
- [x] CLI: finalise `python setu.py --src hi --tgt en --text "..."` (file / stdin input too)
- [x] Mobile SDK stubs: `translate(text, srcLang, tgtLang)` for Android + iOS
- [x] Offline PWA: pick languages, enter text, get translation; caches assets so it works with no connectivity after first load
- [x] All four call the **same** `InferenceEngine` — no duplicated translation logic
- [x] Integration test hitting the REST endpoint

**Done when:** all four interfaces translate through one shared engine. ✅

> **M6 note (2026-07-16):** Four thin front-ends, one `InferenceEngine`, zero duplicated
> translation logic. REST (FastAPI): `POST /translate`, `GET /languages` (all 23),
> `GET /health`; CLI: `--text`/`--file`/piped-stdin + `--json` (batch aware); PWA served
> at `/app` with a service worker precaching the shell (`index.html`, `app.js`, manifest,
> icon) so it loads offline after first visit, calling `/translate` on the same origin;
> Android (Kotlin) + iOS (Swift) SDK stubs with the shared `translate(text, srcLang,
> tgtLang)` contract and `TODO(offline)` markers for on-device ONNX Runtime Mobile.
> 15 interface tests (REST integration, CLI file/stdin/JSON, PWA shell+serving). Target
> moved: none new — Offline reinforced (PWA shell caching + loopback-only SDKs).

---

## M7 — Multilingual (AIO-KD)
Scale from one pair to many.

- [x] Language-wise student initialisation
- [x] `AIOKDOrchestrator` trains one student across multiple directions at once
- [x] Cross-lingual balancing so high-resource languages don't drown out low-resource ones
- [x] Roll out in batches of languages, not all 22 at once
- [x] Per-language eval coverage report (BLEU / ChrF / latency)

**Done when:** a single student covers several languages with a coverage report, and adding more is a config change, not a rewrite. ✅ mechanism; full rollout needs more language data

> **M7 note (2026-07-16):** `AIOKDOrchestrator` trains one student over several direction
> datasets at once. Cross-lingual balancing uses temperature-sampled direction weights
> (`balancing_weights`, T=1 ∝ size, higher T flattens toward uniform to protect
> low-resource directions) with a deterministic weighted round-robin (no RNG, reproducible)
> and a `coverage()` report. Proven by `test_aio_kd.py`: a 2-direction (Hindi, Tamil→En)
> tiny run trains and covers both directions; balancing raises the low-resource share as T
> grows. Adding a direction is a config + dataset change (see `docs/ADDING_A_LANGUAGE.md`),
> not a rewrite. Full 22-language rollout needs the other languages' corpora (only
> Hindi↔English data is on disk here) — deferred per the golden rule (single pair first).

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

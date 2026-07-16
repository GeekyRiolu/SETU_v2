---
name: setu-build
description: Guidance for building and working on SETU — an offline multilingual translation framework for the 22 scheduled Indian languages that distils compact SLMs from an IndicTrans2 teacher using preference pairs + DPO, scales with AIO-KD, expands with EWC, and deploys quantised ONNX models on edge devices. Use this whenever the task touches the SETU repo: writing or editing corpus/teacher/preference/training/quantise/inference modules, wiring IndicTrans2 as a teacher, generating preference pairs, running DPO/AIO-KD/EWC training, quantising or exporting to ONNX, building the REST/CLI/SDK/PWA interfaces, or checking work against SETU's latency/size/offline targets. Also use when the user mentions SETU, offline Indian-language translation, preference distillation, or asks to continue any SETU milestone.
---

# Building SETU

SETU translates across the 22 scheduled Indian languages **fully offline** on edge devices. A strong teacher (IndicTrans2, already cloned locally) produces candidate translations; compact student SLMs learn from ranked preference pairs via DPO, scale to many languages with AIO-KD, and expand to new languages with EWC. Final models are quantised and exported to ONNX to run under 500 ms on phones and ARM boards.

The full task breakdown lives in `TASKS.md` and the complete spec in the PRD. Read `TASKS.md` to see where the build is and what's next. This skill is the *how to work well here* layer.

## The one rule that matters most

**Build one language pair end-to-end before widening.** Get Hindi↔English working through the whole pipeline (data → teacher → preferences → DPO → quantise → offline inference → interfaces) before adding a second language, before AIO-KD, before EWC. A working thin slice beats a half-built system that covers 22 languages on paper. The milestones in `TASKS.md` are ordered for exactly this reason — follow them.

## The four targets are the definition of done

Everything is measured against these. Verify them with benchmarks; never assume them.

- **Quality:** student keeps ≥ 80% of IndicTrans2 BLEU
- **Latency:** < 500 ms/sentence on ARM-class CPU
- **Size:** ≤ 200 MB quantised ONNX artifact
- **Offline:** zero network calls at inference; no user text leaves the device

When you finish a milestone, state which target it moved and show the number. If you can't measure a target yet, say so rather than claiming it.

## Working style

Keep changes small and reviewable. At the end of each milestone, write a short summary: what you built, how you verified it against the targets, and what's next. This keeps a long build legible.

Ask before anything expensive or irreversible: large dataset downloads, long training runs, anything that eats significant disk. Check available disk before downloading corpora. It's fine to scaffold and propose first, then proceed once the plan is clear.

Everything is config-driven. Language pairs, model params, and training hyperparameters live in `configs/*.yaml`. Never hard-code a language pair in the source — the whole point is that adding a language is a config change, not a rewrite.

## Keep IndicTrans2 behind a wall

IndicTrans2 is the teacher and it's already cloned. Wrap it in a single `TeacherModel` interface:

```
generate_candidates(src_text, src_lang, tgt_lang) -> list[str]   # plus a quality score
```

Nothing else in the codebase may import IndicTrans2 internals. This keeps the teacher swappable and the rest of the pipeline stable. Before wiring it in, inspect the local clone and report its path, the checkpoints it needs, and its language-code mapping — flag anything missing so it surfaces early instead of mid-training.

## Data objects — keep the names stable

These flow through every module. Don't rename fields between modules; drift here causes silent breakage.

- **PreferencePair** — `src_text, src_lang, tgt_lang, preferred_tgt, dispreferred_tgt, quality_delta`
- **ModelConfig** — `language_pair, params, quantization`
- **TranslationResult** — `translated_text, src_lang, tgt_lang, bleu, chrf, latency_ms`
- **CorpusEntry** — `src_lang, tgt_lang, src_text, tgt_text, source`

## Algorithm notes (the parts that are easy to get subtly wrong)

**Preference generation** — retrieve a candidate set with kNN, rank by ChrF, then form preferred/dispreferred pairs and record `quality_delta` (the ChrF gap). Add a sanity check that preferred ChrF always exceeds dispreferred ChrF; bad preference data poisons DPO quietly.

**DPO** — standard DPO loss, no reward model and no policy gradient (that's the whole appeal versus RLHF). The reference model is a *frozen* SFT/distilled student snapshot. Getting the reference model wrong (not frozen, or the wrong snapshot) is the most common DPO mistake.

**AIO-KD** — one student trained across many directions at once, with cross-lingual balancing so high-resource languages don't drown out low-resource ones. This is a multilingual concern; don't reach for it until the single pair works.

**EWC** — when adding a language, apply a Fisher-weighted penalty that protects parameters important to already-learned languages. Always prove it worked with a before/after eval on the existing languages — the failure mode (catastrophic forgetting) is invisible unless you measure the old languages after expansion.

**Quantisation** — do INT8 first, benchmark, then INT4, benchmark. Progressive, so you can see exactly where accuracy drops off relative to size. Export to ONNX and validate with ONNX Runtime; the packaged artifact must stay ≤ 200 MB.

## Offline is a hard constraint, not a nice-to-have

The inference path must make no outbound network requests. Add a test that runs inference with networking disabled — it must pass. Audit the inference code for any HTTP call, telemetry, or remote model fetch. Privacy (no user text leaving the device) is a headline feature, so treat any network call in the inference path as a bug.

## Interfaces share one engine

REST API (`POST /translate`), CLI (`python setu.py --src hi --tgt en --text "..."`), mobile SDK stubs (`translate(text, srcLang, tgtLang)`), and the offline PWA must all call the **same** `InferenceEngine`. Don't duplicate translation logic per interface — one engine, four thin front-ends. The PWA additionally has to cache its assets so it works with no connectivity after first load.

## When unsure

If a design choice isn't pinned down by `TASKS.md` or the PRD (e.g. the exact student architecture, or which pair to slice first), propose a sensible default with a one-line rationale and proceed — but surface it so the user can redirect. Don't stall, and don't silently bake in a big decision.

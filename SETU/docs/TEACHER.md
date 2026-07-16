# Teacher: IndicTrans2 — inspection report (M2)

## Local clone

The IndicTrans2 repo is cloned at the **repository root** (two levels above
`src/setu/`). It contains *code only* — no model weights:

- `huggingface_interface/` — the path SETU uses: HF checkpoints with remote
  modeling code (`trust_remote_code=True`), preprocessing via
  `IndicTransToolkit.processor.IndicProcessor`. Reference: `example.py`.
- `inference/` — legacy fairseq path (needs Python ≤3.9 + fairseq). **Not used.**
- `utils.map_token_lang.tsv`, `inference/flores_codes_map_indic.py` — language
  code mappings, mirrored into `configs/languages.yaml`.

## Checkpoints

| Direction | Default (ungated) | Gated original (config-swap) |
|-----------|-------------------|------------------------------|
| indic→en | `prajdabre/rotary-indictrans2-indic-en-dist-200M` | `ai4bharat/indictrans2-indic-en-dist-200M` / `-1B` |
| en→indic | `prajdabre/rotary-indictrans2-en-indic-dist-200M` | `ai4bharat/indictrans2-en-indic-dist-200M` / `-1B` |
| indic↔indic | — (none ungated) | `ai4bharat/indictrans2-indic-indic-dist-320M` |

### Flags (things that surfaced early, as required)

1. **All `ai4bharat/indictrans2-*` checkpoints are gated on HF** (401 without
   login + accepted terms). Same for the `ai4bharat/BPCC` dataset. To use them:
   accept terms on each repo page, then `huggingface-cli login`.
   Until then, the defaults are the **RoPE variants released by IndicTrans2
   author Raj Dabre** (linked from the IndicTrans2 README, not gated).
2. **Hardware ceiling:** this machine is CPU-only with 7.4 GB RAM. The 1B
   teachers (~4.5 GB fp32 weights) don't fit alongside the OS; the distilled
   200M variants are the working teachers. The ≥80%-of-teacher-BLEU target is
   therefore measured against dist-200M quality on this box.
3. **indic↔indic direction is unavailable** until the gated 320M checkpoint is
   accessible — fine for the Hindi↔English thin slice, which pivots through
   the en↔indic models.
4. Extra runtime deps discovered: `sentencepiece`, `einops` (rotary remote
   code). Both are in the `teacher` extra.

## Language-code mapping

IndicTrans2 uses script-qualified FLORES codes (`hin_Deva`, `eng_Latn`, …).
`configs/languages.yaml` maps CLI ISO codes → FLORES for all 22 scheduled
languages + English, including dual-script entries (Kashmiri, Manipuri,
Sindhi). `IndicProcessor` consumes FLORES codes directly — no extra mapping.

## The wall

`src/setu/teacher/indictrans2.py` is the **only** file that may import
`transformers`, `torch`, or `IndicTransToolkit`. `tests/test_teacher.py::
test_teacher_wall` enforces this by scanning the source tree.

Interface (`src/setu/teacher/base.py`):

```python
TeacherModel.generate_candidates(src_text, src_lang, tgt_lang, n=4) -> list[str]
TeacherModel.score_candidates(candidates, reference) -> list[float]  # sentence ChrF
```

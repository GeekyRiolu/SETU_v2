# SETU — scorecard (Phase 1)

Per-direction student vs teacher on a 500-sentence Samanantar dev slice. Quality target = **student BLEU / teacher BLEU ≥ 0.80**. Every model is a 52.6M-param SeqKD student, **INT4 ONNX ~104 MB**, fully offline. Generated from `vm/out/report_*.json` by `scripts/build_scores.py`.

**14 / 22 directions meet ≥ 0.80** · mean ratio **0.838** · median **0.855** · 11 languages, both directions.

| # | Direction | BLEU | chrF | Teacher | Ratio | ≥0.80 | Mean latency |
|--:|-----------|-----:|-----:|--------:|------:|:-----:|-------------:|
| 1 | Marathi → English | 16.4 | 43.8 | 17.1 | **0.955** | ✅ | 131 ms |
| 2 | English → Kannada | 10.0 | 43.0 | 11.0 | **0.915** | ✅ | 105 ms |
| 3 | English → Punjabi | 15.8 | 42.3 | 17.5 | **0.904** | ✅ | 175 ms |
| 4 | English → Marathi | 12.5 | 40.9 | 13.8 | **0.901** | ✅ | 111 ms |
| 5 | Odia → English | 18.9 | 46.5 | 21.0 | **0.898** | ✅ | 133 ms |
| 6 | Malayalam → English | 17.1 | 44.6 | 19.1 | **0.898** | ✅ | 128 ms |
| 7 | English → Odia | 6.9 | 40.8 | 7.7 | **0.895** | ✅ | 128 ms |
| 8 | Punjabi → English | 21.1 | 47.6 | 24.0 | **0.877** | ✅ | 158 ms |
| 9 | English → Hindi | 20.3 | 46.6 | 23.3 | **0.871** | ✅ | 202 ms |
| 10 | English → Malayalam | 5.2 | 38.8 | 6.1 | **0.863** | ✅ | 113 ms |
| 11 | English → Gujarati | 12.5 | 41.1 | 14.6 | **0.855** | ✅ | 114 ms |
| 12 | English → Bengali | 11.1 | 41.5 | 13.1 | **0.848** | ✅ | 130 ms |
| 13 | Telugu → English | 18.9 | 46.5 | 23.1 | **0.817** | ✅ | 129 ms |
| 14 | Hindi → English | 21.8 | 49.5 | 27.1 | **0.806** | ✅ | 199 ms |
| 15 | Gujarati → English | 18.8 | 46.2 | 23.9 | **0.787** | ⚠️ | 130 ms |
| 16 | English → Telugu | 11.0 | 42.8 | 14.0 | **0.780** | ⚠️ | 113 ms |
| 17 | English → Assamese | 6.7 | 33.7 | 8.7 | **0.764** | ⚠️ | 155 ms |
| 18 | Kannada → English | 16.3 | 45.6 | 21.4 | **0.763** | ⚠️ | 132 ms |
| 19 | Tamil → English | 16.1 | 41.0 | 21.1 | **0.761** | ⚠️ | 155 ms |
| 20 | Assamese → English | 13.1 | 33.5 | 17.3 | **0.757** | ⚠️ | 154 ms |
| 21 | Bengali → English | 19.1 | 45.2 | 25.2 | **0.756** | ⚠️ | 150 ms |
| 22 | English → Tamil | 8.0 | 43.0 | 10.6 | **0.755** | ⚠️ | 135 ms |

Indic↔Indic pairs (e.g. Hindi→Bengali) are served by pivoting through English, so all 11 languages translate in every direction even without a direct model. Latency is on a shared CPU host; size (104 MB) and offline targets pass for every model.

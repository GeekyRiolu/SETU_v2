# SETU diagrams (Mermaid) — corrected to the real SeqKD + English-pivot system

Paste any block into <https://mermaid.live> to preview and **export SVG/PNG** for
the slides, or import into draw.io (Arrange → Insert → Advanced → Mermaid). These
replace the deck's old DPO / kNN-preference / AIO-KD diagrams.

---

## 1. System Design — SeqKD distillation & offline deployment pipeline (slide 18)

```mermaid
flowchart LR
  A[("Samanantar corpus<br/>(Indic-English)")] --> B["Preprocess<br/>script norm · SentencePiece · align"]
  B --> C{{"Teacher: IndicTrans2 dist-200M"}}
  C -->|"1-best translations"| D[("Distilled corpus")]
  D --> E["SeqKD training<br/>52M student · PAD-masked CE<br/>LR warmup · grad clip"]
  E --> F["Student SLM<br/>52M params · 16k vocab"]
  F --> G["Quantise INT8/INT4<br/>ONNX ~104 MB / direction"]
  G --> H["Offline Inference Engine<br/>ONNX Runtime + SentencePiece"]
  H --> P{"English-pivot router"}
  P -->|"direct pair"| O["Translation"]
  P -->|"Indic-Indic: src to en to tgt"| O
  H --> R["REST API<br/>/translate /languages /models /health"]
  H --> W["Next.js Web App"]
  H --> PW["Offline PWA"]
  H --> CL["CLI"]
  O --> EDGE["Edge / on-device · fully offline · 0 network"]
```

---

## 2. Use Case diagram (slide 15a)

```mermaid
flowchart LR
  U(["End User"]):::actor
  M(["ML Engineer"]):::actor
  E(["Edge Device"]):::actor
  subgraph SETU
    UC1(("Translate Text"))
    UC2(("Pivot Translate<br/>via English"))
    UC3(("Distil Teacher<br/>Targets"))
    UC4(("Train Student<br/>SeqKD"))
    UC5(("Quantise &<br/>Export ONNX"))
    UC6(("Evaluate<br/>BLEU / chrF"))
  end
  U --> UC1
  U --> UC2
  M --> UC3
  M --> UC4
  M --> UC5
  M --> UC6
  UC1 --> E
  UC2 --> E
  classDef actor fill:#f4efe7,stroke:#8a3b2e,stroke-width:1px;
```

---

## 3. Sequence diagram — translate request (slide 15b)

```mermaid
sequenceDiagram
  actor User
  participant API as REST API / Web
  participant Eng as Inference Engine
  participant S1 as Student ONNX (hop 1)
  participant S2 as Student ONNX (hop 2)
  User->>API: text, source_lang, target_lang
  API->>Eng: translate(...)
  alt direct model exists
    Eng->>S1: encode + generate
    S1-->>Eng: translation
  else Indic to Indic (English pivot)
    Eng->>S1: source to English
    S1-->>Eng: English text
    Eng->>S2: English to target
    S2-->>Eng: translation
  end
  Eng-->>API: translated_text + latency + pivot flag
  API-->>User: translation
```

---

## 4. Data Flow Diagram (slide 15c)

```mermaid
flowchart LR
  C[("Samanantar corpus")] --> P["Preprocess<br/>normalise · tokenise · align"]
  P --> T{{"IndicTrans2 teacher"}}
  T -->|"1-best"| D[("Distilled corpus")]
  D --> K["SeqKD Trainer"]
  K --> ST["52M Student"]
  ST --> Q["Quantiser<br/>INT4 ONNX ~104 MB"]
  Q --> IE["Inference Engine<br/>+ English pivot"]
  IE --> O["Translation output"]
  T -. "teacher BLEU" .-> EV["Evaluator<br/>student/teacher ratio"]
  ST -. "student BLEU" .-> EV
```

---

## 5. Project timeline — Gantt (slide 17)

Phase 1 is complete (where we are today, mid-Aug 2026); Phase 2 runs to the
**final presentation at the end of October 2026**.

```mermaid
gantt
  title SETU Project Timeline - Phase 1 done, Final end Oct 2026
  dateFormat YYYY-MM-DD
  axisFormat %b
  section Phase 1 (done)
  Literature survey and requirements   :done, a1, 2026-01-15, 2026-02-28
  System design and pipeline build     :done, a2, 2026-03-01, 2026-04-30
  Data and corpus prep (Samanantar)    :done, a3, 2026-04-15, 2026-05-31
  Teacher distillation 1-best          :done, a4, 2026-05-15, 2026-06-30
  SeqKD student training 52M           :done, a5, 2026-06-15, 2026-08-05
  Quantisation and ONNX export         :done, a6, 2026-07-10, 2026-08-05
  Interfaces API Web PWA CLI and pivot :done, a7, 2026-07-15, 2026-08-08
  Phase 1 languages 11 of 22           :active, a8, 2026-06-15, 2026-08-20
  Interim presentation                 :milestone, m1, 2026-08-12, 0d
  section Phase 2 (upcoming)
  Assamese and Punjabi finish          :active, b1, 2026-08-10, 2026-08-31
  Remaining 11 languages               :b2, 2026-09-01, 2026-10-15
  FLORES and COMET benchmarking        :b3, 2026-09-15, 2026-10-20
  Mobile and edge packaging            :b4, 2026-09-20, 2026-10-22
  Final report and paper writeup       :b5, 2026-10-01, 2026-10-25
  Final presentation                   :milestone, m2, 2026-10-28, 0d
```

> Old deck's phases were Data Prep -> Teacher -> **Preference Gen (kNN)** -> **DPO**
> -> **AIO-KD** -> Quantise -> Deploy. Corrected here: the middle three collapse
> into a single **SeqKD training** stage (no preference/kNN/AIO-KD), and Phase 2
> is added through the October final.

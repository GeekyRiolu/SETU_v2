"""Proposal text for the KSCST 50th Series SPP application (2026-27).

Everything here is non-personal and drawn from the Phase-II report. Personal
details (phones, emails, categories, payment) live in details.json, outside
the repository.

Block types used in PART_B:
  ("p",    text)                 plain paragraph
  ("lead", label, text)          paragraph with a bold run-in label
  ("ul",   [items])              bullet list (items may use **bold**)
  ("ol",   [items])              numbered list
  ("fig",  file, width_in, cap)  figure with caption (proposal only)
Citations are written {key} and numbered in order of first use.
"""

TITLE = ("SETU: MULTILINGUAL PREFERENCE DISTILLATION FOR OFFLINE INDIAN "
         "LANGUAGE SLM TRANSLATORS")
FILE_STEM = "SETU_Offline_Indian_Language_SLM_Translators"

KEYWORDS = ("NEURAL MACHINE TRANSLATION; KNOWLEDGE DISTILLATION; SMALL LANGUAGE "
            "MODELS; INDIAN LANGUAGES; KANNADA; OFFLINE ON-DEVICE INFERENCE; "
            "MODEL QUANTISATION; DIRECT PREFERENCE OPTIMIZATION")

THEME_NO = "4"
THEME_NAME = "ARTIFICIAL INTELLIGENCE, DATA SCIENCE AND DIGITAL TECHNOLOGIES"
SUB_THEME = "NATURAL LANGUAGE PROCESSING (NLP) AND GENERATIVE AI"

INSTITUTION = {
    # Must match the Google Form dropdown entry exactly.
    "name": "BANGALORE INSTITUTE OF TECHNOLOGY, BENGALURU URBAN",
    "course": "B.E.",
    "department": "ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING",
    "university": "VISVESVARAYA TECHNOLOGICAL UNIVERSITY, BELAGAVI",
    "district": "BENGALURU URBAN",
    "address": "BANGALORE INSTITUTE OF TECHNOLOGY, K.R. ROAD, V.V. PURA, "
               "BENGALURU, KARNATAKA - 560004",
}

DEGREE = "B.E."
BRANCH = "ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING"
SEMESTER = "7"

# --------------------------------------------------------------------------
REFERENCES = {
    "indictrans2": 'J. Gala, P. A. Chitale, A. K. Raghavan, V. Gumma, S. Doddapaneni, A. Kumar M, and J. A. Nawale, "IndicTrans2: Towards High-Quality and Accessible Machine Translation Models for All 22 Scheduled Indian Languages," Transactions on Machine Learning Research (TMLR), 2023.',
    "transformer": 'A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, Ł. Kaiser, and I. Polosukhin, "Attention Is All You Need," in Advances in Neural Information Processing Systems (NeurIPS), vol. 30, 2017.',
    "samanantar": 'G. Ramesh, S. Doddapaneni, A. Bheemaraj, M. Jobanputra, R. AK, A. Sharma, S. Sahoo, H. Diddee, M. J, D. Kakwani, N. Kumar, A. Pradeep, K. Nagaraj, A. Kumar, P. Kumar, M. S. Khapra, R. Dabre, P. Kumar, and A. Kunchukuttan, "Samanantar: The Largest Publicly Available Parallel Corpora Collection for 11 Indic Languages," Transactions of the Association for Computational Linguistics (TACL), vol. 10, pp. 145-162, 2022.',
    "mt5indic": 'A. Jha, H. Y. Patil, S. K. Jindal, and S. M. N. Islam, "Multilingual Indian Language Neural Machine Translation System Using mT5 Transformer," IEEE, 2023.',
    "indic2indic": 'S. B. Das, D. Panda, T. K. Mishra, B. K. Patra, and A. Ekbal, "Multilingual Neural Machine Translation System for Indic to Indic Languages," ScienceDirect, 2024.',
    "distilbert": 'V. Sanh, L. Debut, J. Chaumond, and T. Wolf, "DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter," arXiv preprint arXiv:1910.01108, 2019.',
    "seqkd": 'Y. Kim and A. M. Rush, "Sequence-Level Knowledge Distillation," in Proceedings of the 2016 Conference on Empirical Methods in Natural Language Processing (EMNLP), 2016, pp. 1317-1327.',
    "small100": 'A. Mohammadshahi, V. Nikoulina, A. Bérard, C. Brun, J. Henderson, and L. Besacier, "SMaLL-100: Introducing Shallow Multilingual Machine Translation for Low-Resource Languages," Springer, 2020.',
    "mobilenmt": 'B. Li, Z. Wang, H. Liu, Y. Jiang, Q. Du, T. Xiao, H. Wang, and J. Zhu, "Neural Machine Translation on Mobile Devices," IEEE, 2020.',
    "dpo": 'R. Rafailov, A. Sharma, E. Mitchell, C. D. Manning, S. Ermon, and C. Finn, "Direct Preference Optimization: Your Language Model is Secretly a Reward Model," in Advances in Neural Information Processing Systems (NeurIPS), vol. 36, 2023.',
    "dpomt": 'G. Yang, J. Chen, W. Lin, and B. Byrne, "Direct Preference Optimization for Neural Machine Translation with Minimum Bayes Risk Decoding," in Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics (NAACL), 2024.',
    "offlinesmt": 'S. Gangwar and I. Naim, "Offline English-to-Hindi Statistical Machine Translation System," ScienceDirect, 2024.',
    "surya": 'P. S. Bohra and K. Berwal, "LLM-based AI-Powered Offline Portable Transcriptor (OPT) - SURYA-TAC: A Tactical Speech-to-Speech Translation System," IEEE, 2024.',
    "pat1": 'X. Li, Y. Sun, J. Li, and J. Jiang, "Method and device for compressing a neural network model for machine translation and storage medium," U.S. Patent 11 556 761 B2, Jan. 17, 2023 (assignee: Beijing Xiaomi Intelligent Technology Co., Ltd.).',
    "pat2": 'X. Li, Y. Sun, J. Jiang, and J. Cui, "Neural network model compression method, corpus translation method and device," U.S. Patent 11 556 723 B2, Jan. 17, 2023 (assignee: Beijing Xiaomi Intelligent Technology Co., Ltd.).',
    "marian": 'M. Junczys-Dowmunt, R. Grundkiewicz, T. Dwojak, H. Hoang, K. Heafield, T. Neckermann, F. Seide, U. Germann, A. Fikri Aji, N. Bogoychev, A. F. T. Martins, and A. Birch, "Marian: Fast Neural Machine Translation in C++," in Proceedings of ACL 2018, System Demonstrations, 2018, pp. 116-121.',
    "sentencepiece": 'T. Kudo and J. Richardson, "SentencePiece: A Simple and Language Independent Subword Tokenizer and Detokenizer for Neural Text Processing," in Proceedings of EMNLP 2018, System Demonstrations, 2018, pp. 66-71.',
    "onnx": 'ONNX Runtime Developers, "ONNX Runtime: Cross-platform Accelerated Machine Learning," 2021. [Online]. Available: https://onnxruntime.ai',
    "sacrebleu": 'M. Post, "A Call for Clarity in Reporting BLEU Scores," in Proceedings of the Third Conference on Machine Translation (WMT), 2018, pp. 186-191.',
    "chrf": 'M. Popović, "chrF: Character n-gram F-score for Automatic MT Evaluation," in Proceedings of the Tenth Workshop on Statistical Machine Translation (WMT), 2015, pp. 392-395.',
    "flores": 'NLLB Team et al., "No Language Left Behind: Scaling Human-Centered Machine Translation," arXiv preprint arXiv:2207.04672, 2022.',
    "comet": 'R. Rei, C. Stewart, A. C. Farinha, and A. Lavie, "COMET: A Neural Framework for MT Evaluation," in Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP), 2020, pp. 2685-2702.',
}

# --------------------------------------------------------------------------
# PART B. Keys are the template row labels (matched by prefix).
PART_B = {}

PART_B["Background and Need of the Project"] = [
    ("lead", "Background:",
     "The Eighth Schedule of the Constitution recognises 22 Indian languages, "
     "and Kannada is the official language of Karnataka. Health advisories, "
     "government notices, agricultural information and most digital services "
     "are still produced mainly in English, so machine translation is the "
     "practical bridge between a public service and the citizen it is meant "
     "to reach."),
    ("lead", "Existing scenario:",
     "High-quality Indic translators such as IndicTrans2 {indictrans2} cover "
     "all 22 scheduled languages, but they run in data centres, hold up to a "
     "billion parameters and need several gigabytes of memory. Using them "
     "requires a working internet connection, and every sentence a user types "
     "is sent to a remote server."),
    ("lead", "Problem statement:",
     "Translation is therefore unavailable exactly where it is needed most: a "
     "primary health centre with intermittent connectivity, a gram panchayat "
     "counter, a relief camp after a flood. Cloud translation also discloses "
     "sensitive text, such as symptoms, grievances and legal matters, to a "
     "third party."),
    ("lead", "Need for the project:",
     "Karnataka needs a translator an order of magnitude smaller than these "
     "models that runs fully offline on an entry-level Android phone, keeps "
     "most of the large model's quality and costs nothing per use. The team "
     "has already built and tested a working prototype of such a system "
     "(Phase I). KSCST support is sought to deploy it on real ARM handsets, "
     "benchmark it on public test sets and validate it with Kannada-speaking "
     "users in Karnataka."),
    ("lead", "Beneficiaries:",
     "ASHA workers and primary health centre staff; gram panchayat and Grama "
     "One service counters; teachers of migrant children in Bengaluru "
     "schools; farmers receiving advisories; disaster-relief teams; and any "
     "citizen whose text should not leave their own device."),
]

PART_B["Review of Existing Work"] = [
    ("lead", "Existing technologies:",
     "Neural machine translation is built on the Transformer encoder-decoder "
     "{transformer}. For Indian languages, IndicTrans2 {indictrans2}, trained "
     "on the Samanantar {samanantar} and BPCC corpora, is the state of the "
     "art; mT5-based multilingual systems {mt5indic} and Indic-to-Indic "
     "systems {indic2indic} show that related Indian languages transfer well "
     "to one another. Model compression offers the route to small models: "
     "knowledge distillation trains a small student to imitate a large "
     "teacher {distilbert}; sequence-level knowledge distillation trains the "
     "student on the teacher's own decoded output {seqkd}; and SMaLL-100 "
     "{small100} and work on translation for mobile devices {mobilenmt} show "
     "that shallow translators can remain usable. Direct Preference "
     "Optimization (DPO) {dpo} and its application to translation with "
     "minimum Bayes risk decoding {dpomt} make preference-based training "
     "practical without a separate reward model."),
    ("lead", "Commercial products:",
     "Google Translate, Microsoft Translator and the Government of India's "
     "Bhashini platform provide Indic translation mainly as cloud services "
     "and APIs. Their offline modes, where offered, are closed: an "
     "institution cannot audit, extend or host them on its own hardware, and "
     "has no control over which languages remain available without a "
     "network."),
    ("lead", "Research papers:",
     "The surveyed systems reach high quality only at the cost of size and "
     "connectivity. The two offline systems found are narrow: an offline "
     "English-to-Hindi system {offlinesmt} uses phrase-based statistical "
     "translation for a single language pair, and SURYA-TAC {surya} "
     "addresses tactical speech-to-speech use, a different task from "
     "general text translation across the scheduled languages. No surveyed "
     "work compares preference-based distillation with sequence-level "
     "distillation for a compact Indic student under matched conditions."),
    ("lead", "Patents:",
     "US 11,556,761 B2 {pat1} and US 11,556,723 B2 {pat2}, both granted to "
     "Beijing Xiaomi Intelligent Technology in 2023, compress machine "
     "translation models for mobile terminals by distilling from one or more "
     "teacher models. Neither addresses Indian languages, quantised offline "
     "deployment across many languages, or routing through a pivot "
     "language."),
    ("lead", "Existing solutions:",
     "Field staff without connectivity rely on bilingual colleagues, printed "
     "bilingual material or dictionary apps that translate single words "
     "rather than sentences."),
    ("lead", "Shortcomings and research gaps:", ""),
    ("ul", [
        "High-quality Indic translators are cloud-bound and gigabyte-sized; "
        "none fits an entry-level phone.",
        "Existing offline systems cover a single pair or a different task, at "
        "clearly lower quality.",
        "No controlled comparison exists of preference-based (DPO) and "
        "sequence-level distillation for compact Indic students.",
        "No system covers all 22 scheduled languages offline within a few "
        "hundred megabytes per direction while also reaching every "
        "Indic-to-Indic pair.",
        "Translation quality on Karnataka public-service text has not been "
        "measured with native Kannada speakers.",
    ]),
]

PART_B["Problem Statement"] = [
    ("p",
     "To design, build and validate a machine translation system for the 22 "
     "scheduled Indian languages that runs entirely on low-cost ARM devices "
     "with no network connection, needs at most 200 MB per translation "
     "direction, translates a sentence in under 500 ms and retains at least "
     "80% of a large teacher model's BLEU score; and to establish, with "
     "native Kannada speakers, whether its output is usable for "
     "public-service communication in Karnataka."),
    ("p",
     "Phase I has answered the research question at the core of the project: "
     "under matched conditions, training the student on the teacher's own "
     "output (sequence-level distillation) beats preference-based "
     "distillation with DPO. The remaining problem is to prove the system on "
     "the hardware and with the users it is meant for."),
]

PART_B["Objectives"] = [
    ("ol", [
        "To deploy the 44 distilled SETU students (22 scheduled languages to "
        "and from English) in an offline Android application, and to verify on "
        "an entry-level ARM Cortex-A55 handset a per-sentence latency below "
        "500 ms and a model size of at most 200 MB per direction.",
        "To raise the eight directions currently below target "
        "(student/teacher BLEU ratio 0.755 to 0.787, including Kannada to "
        "English at 0.763) to a ratio of at least 0.80, using beam-search "
        "decoding, additional training epochs and additional distilled data.",
        "To benchmark every direction on the public FLORES-200 devtest set "
        "with BLEU, chrF and COMET, so that results are directly comparable "
        "with published systems.",
        "To evaluate Kannada-English translation of Karnataka public-service "
        "text (health advisories, government notices and agricultural "
        "advisories) with at least five native Kannada speakers rating at "
        "least 200 sentences for adequacy and fluency on a 1 to 5 scale, "
        "with a target mean of 3.5 or higher.",
        "To validate the offline application with at least 20 users in a "
        "field setting in Bengaluru, such as a primary health centre or a "
        "gram panchayat service counter, and to document usability findings "
        "and failure cases.",
        "To release the code, the models and a standard operating procedure "
        "for adding a new language as open source.",
    ]),
]

PART_B["Innovation / Novelty"] = [
    ("lead", "What is new?", ""),
    ("ul", [
        "**A controlled finding:** at matched student size (52.6 million "
        "parameters) and identical data (100,000 sentences), sequence-level "
        "knowledge distillation reached 17.09 BLEU against 11.10 for "
        "preference-based DPO distillation, a gain of 54%. The result refuted "
        "the project's own founding hypothesis and showed that noise in "
        "web-mined human references, not the training objective, limits "
        "compact Indic students.",
        "**A complete offline system:** all 22 scheduled languages to and "
        "from English, 103.9 MB per direction, 105 to 202 ms mean latency per "
        "sentence on a commodity CPU, verified with every network socket "
        "disabled.",
        "**Quadratic coverage from linear storage:** an English-pivot router "
        "chains two students where no direct model exists, so 44 trained "
        "models serve 506 translation directions; direct models for every "
        "pair would need more than 11 GB.",
    ]),
    ("lead", "How is it different from existing work?",
     "IndicTrans2 {indictrans2} needs a data centre or a GPU; commercial "
     "translators are cloud services whose offline modes are closed; the "
     "Xiaomi patents {pat1}, {pat2} compress a translation model for mobile "
     "use but do not target Indian languages or many-language offline "
     "deployment; the offline English-to-Hindi system {offlinesmt} covers one "
     "pair with statistical translation. SETU is open, offline, covers every "
     "scheduled language and reaches every Indic-to-Indic pair from one "
     "shared engine."),
    ("lead", "Why is it innovative?",
     "Privacy is guaranteed by architecture rather than by policy: there is "
     "no server to trust because there is no server. The cost per "
     "translation is zero, so a public institution can deploy it on hardware "
     "it already owns. Adding a language is a configuration and data change, "
     "not a code change. The proposed work adds a field validation of an "
     "offline Indic translator with Kannada-speaking users on Karnataka "
     "public-service text."),
]

PART_B["Proposed Methodology"] = [
    ("lead", "Overall methodology:",
     "SETU distils a large teacher, the ungated IndicTrans2 distilled-200M "
     "model {indictrans2}, into one compact student per translation "
     "direction. The teacher translates about 497,000 source sentences from "
     "the Samanantar corpus {samanantar}; its one-best outputs become the "
     "student's training targets (sequence-level knowledge distillation "
     "{seqkd}). Each student is a 52.6-million-parameter Marian "
     "encoder-decoder {marian} with a 16,000-token SentencePiece vocabulary "
     "{sentencepiece}, trained with label smoothing, warm-up and gradient "
     "clipping. Students are exported to ONNX, quantised to INT8 and INT4, "
     "and executed on the CPU by ONNX Runtime {onnx}. Quality is measured "
     "with sacreBLEU {sacrebleu} and chrF {chrf} against real human "
     "references held out from training; the headline metric is the "
     "student/teacher BLEU ratio, with a target of at least 0.80."),
    ("lead", "Block diagram / flow chart:", ""),
    ("fig", "fig1_pipeline.png", 5.4,
     "Figure 1: SETU pipeline, from corpus and teacher through distillation "
     "and quantisation to the offline inference engine."),
    ("lead", "System architecture:",
     "All client interfaces share one offline inference engine. The engine "
     "loads the quantised student for the requested direction from local "
     "storage, tokenises with SentencePiece and decodes on the CPU. Where no "
     "direct student exists, the English-pivot router chains two students "
     "(source to English, then English to target), as Figure 2 shows."),
    ("fig", "fig2_deployment.png", 5.0,
     "Figure 2: Deployment architecture. The proposed Android application is "
     "one more client of the same engine."),
    ("lead", "Design approach:", ""),
    ("ul", [
        "One student per direction, which avoids interference between "
        "languages and keeps each model small enough for a phone.",
        "The teacher sits behind an abstraction layer, so a stronger teacher "
        "can be substituted without changing the pipeline.",
        "Languages are configuration-driven: adding one means adding its "
        "configuration and data, not code.",
        "Offline by construction: the inference path opens no network socket, "
        "and this is checked by the automated test suite (85 tests in "
        "Phase I).",
    ]),
    ("lead", "Experimental plan:", ""),
    ("ul", [
        "**On-device latency:** run 500 sentences per direction on an "
        "entry-level ARM Cortex-A55 Android handset and report median and "
        "90th-percentile latency against the 500 ms budget.",
        "**Closing the near-misses:** for each of the eight directions below "
        "0.80, change one factor at a time (beam search at decoding, extra "
        "training epochs, more distilled data) and keep a change only if the "
        "ratio improves on held-out data.",
        "**Public benchmark:** score every direction on FLORES-200 devtest "
        "{flores} with BLEU, chrF and COMET {comet}, with paired bootstrap "
        "significance tests.",
        "**Kannada human evaluation:** at least five native Kannada speakers "
        "rate at least 200 sentences of Karnataka public-service text for "
        "adequacy and fluency on a 1 to 5 scale; inter-rater agreement is "
        "reported.",
        "**Field validation:** at least 20 users at a field site in Bengaluru "
        "use the offline app on real tasks; task success, time taken and "
        "failure cases are recorded.",
    ]),
    ("lead", "Preliminary results (Phase I):",
     "The controlled comparison that set the method, and the effect of "
     "quantisation on one deployed student, are shown in Figures 3 and 4."),
    ("fig", "fig3_head_to_head.png", 5.2,
     "Figure 3: Matched comparison at 100,000 sentences. Sequence-level "
     "distillation (S1) beats DPO preference distillation (S2) and the "
     "reference-trained baseline (S0)."),
    ("fig", "fig4_quantisation.png", 5.2,
     "Figure 4: Size, 90th-percentile latency and BLEU of the Hindi to "
     "English student at FP32, INT8 and INT4."),
    ("lead", "Software / hardware to be used:",
     "Software (all open source): Python, PyTorch, Hugging Face "
     "Transformers, ONNX Runtime and ONNX Runtime Mobile, SentencePiece, "
     "sacreBLEU, COMET, FastAPI, Next.js and Android Studio. Hardware: the "
     "team's laptops and the department laboratory computers for "
     "development, cloud GPU hours for retraining, and one entry-level ARM "
     "Android handset for on-device testing and field trials."),
]

PART_B["Expected Deliverables"] = [
    ("ul", [
        "**Software:** 44 quantised INT4 ONNX students with their tokenizers, "
        "and the offline inference engine with English-pivot routing (506 "
        "directions).",
        "**Mobile app:** an offline Android translator that requests no "
        "network permission.",
        "**Web portal:** the offline progressive web application, the Next.js "
        "client and the REST API service.",
        "**Design:** documented system architecture and a reproducible, "
        "resumable training pipeline.",
        "**Dataset:** a human-rated Kannada-English evaluation set of "
        "Karnataka public-service sentences.",
        "**Standard operating procedure:** for adding a new language and for "
        "deploying the translator on institutional hardware.",
        "**Reports:** a FLORES-200 benchmark report and a research paper on "
        "distillation for compact Indic translation.",
    ]),
]

PART_B["Expected Outcomes and Impact"] = [
    ("lead", "Technical:",
     "Offline translation for all 22 scheduled languages within 200 MB per "
     "direction and 500 ms per sentence on ARM hardware, with publicly "
     "comparable benchmark scores."),
    ("lead", "Social:",
     "Citizens can be served in their own language where there is no "
     "network, and sensitive text such as symptoms or grievances never "
     "leaves the device."),
    ("lead", "Environmental:",
     "No data centre or GPU is needed at the point of use; the models run on "
     "low-power phones that people already own."),
    ("lead", "Economic:",
     "Zero cost per translation and no API subscription, so deployment "
     "across many offices, schools or health centres is affordable."),
    ("lead", "Industrial:",
     "An open, reusable translation component for MSMEs and start-ups "
     "building Kannada-first and multilingual applications."),
    ("lead", "Academic:",
     "A controlled, reproducible result on which training signal to use for "
     "compact translators, prepared for publication, with a documented "
     "record of training failures and their fixes."),
    ("lead", "Potential users:",
     "ASHA workers and primary health centre staff, gram panchayat and Grama "
     "One operators, teachers, agricultural extension workers, police and "
     "disaster-relief teams, and NGOs working across language boundaries."),
]

# Ticked boxes in section 16, matched against the template's option text.
RELEVANCE = ["SDGs", "Karnataka Priority Sector", "Rural Development",
             "Healthcare", "Digital India", "Others"]
SDG_NOTE = "SDG 3, SDG 4, SDG 9, SDG 10"
RELEVANCE_OTHER = ("INDIAN LANGUAGE TECHNOLOGY (NATIONAL LANGUAGE TRANSLATION "
                   "MISSION, BHASHINI)")
# Google Form option labels for the same ticks.
RELEVANCE_FORM = ["SDG (SUSTAINABLE DEVELOPMENT GOALS)",
                  "KARNATAKA PRIORITY SECTOR", "RURAL DEVELOPMENT",
                  "HEALTHCARE", "DIGITAL INDIA", "OTHER: " + RELEVANCE_OTHER]

MONTHS = ["Dec 2026", "Jan 2027", "Feb 2027", "Mar 2027", "Apr 2027"]
WORK_PLAN = {                       # activity -> months ticked (1-based)
    "Literature Survey": [1],
    "Design": [1, 2],
    "Development": [2, 3, 4],
    "Testing": [3, 4],
    "Validation": [4, 5],
    "Final Report": [5],
}

FACILITIES = {   # defaults; details.json may override any entry
    "Laboratory": "Department of Artificial Intelligence and Machine "
                  "Learning computing laboratory, Bangalore Institute of "
                  "Technology.",
    "Equipment": "Desktop computers in the department laboratory and the "
                 "team's own laptops (x86 CPUs), used for development and "
                 "CPU latency testing.",
    "Software": "Open-source stack: Python, PyTorch, Hugging Face "
                "Transformers, ONNX Runtime, SentencePiece, sacreBLEU, "
                "FastAPI, Next.js, Git and GitHub.",
    "Instruments": "NONE",
    "Workshop": "NONE",
    "Institutional facilities": "Central library and digital library "
                                "resources, campus internet connectivity, "
                                "and seminar halls for user evaluation "
                                "sessions.",
}

REQUIREMENTS = [
    ("lead", "Hardware:",
     "One entry-level Android smartphone with an ARM Cortex-A55 class "
     "processor and 4 GB RAM, for on-device latency measurement and field "
     "trials."),
    ("lead", "Cloud compute:",
     "GPU hours for retraining the eight near-miss directions and for COMET "
     "scoring."),
    ("lead", "Software:",
     "Python, PyTorch, Hugging Face Transformers, ONNX Runtime (including "
     "Mobile), SentencePiece, sacreBLEU, COMET and Android Studio; all free "
     "and open source."),
    ("lead", "Data:",
     "Samanantar parallel corpus, FLORES-200 devtest, and Kannada-English "
     "public-service text collected from Karnataka government notices and "
     "health and agricultural advisories."),
    ("lead", "Field studies:",
     "Local travel to field sites for user evaluation sessions; printed "
     "consent and rating sheets."),
]

# Rupees. Keys follow the template rows; the total is computed.
BUDGET = {   # defaults; details.json may override
    "Equipment / Components": 7000,
    "Consumables": 0,
    "Fabrication": 0,
    "Software / Cloud Services": 2000,
    "Field Survey / Data Collection": 1000,
    "Testing / Analysis": 0,
    "Miscellaneous": 0,
}
BUDGET_NOTE = ("Equipment: one entry-level ARM Android handset, the reference "
               "device for latency tests and field trials. Software / cloud: "
               "GPU hours for retraining and COMET scoring. Field survey: "
               "local travel and printed rating sheets. All software used is "
               "free and open source.")

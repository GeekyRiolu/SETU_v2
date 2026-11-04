# KSCST Student Project Programme (50th series, 2026-27) application

Builds the SETU application pack for KSCST's Student Project Programme from
KSCST's own Word template, so their layout, logos and footers are kept.

```
python3 build_kscst.py                      # build everything
python3 build_kscst.py compress scan.pdf 1  # shrink a signed scan to upload slot 1-4
python3 build_kscst.py receipt shot.png     # payment screenshot -> file 04
```

Output goes to `~/Downloads/KSCST_SETU/` (override with `KSCST_OUT`):

| File | What it is | Upload limit |
|---|---|---|
| `01_SETU_..._Translators.pdf` | Project proposal (Part A, Part B, signatures, fee page) | 3 MB |
| `02_..._declaration_endorsement.pdf` | Declaration (2 pages) + endorsement (2 pages, top left blank for the department letterhead) | 1 MB |
| `03_..._Processing_Fee.pdf` | Processing-fee details page | 1 MB |
| `04_..._Payment_Receipt.pdf` | Made from the payment screenshot | 1 MB |
| `START_HERE_form_answers.html` | Every Google Form answer in order, uppercase, with copy buttons and a list of what is still missing | |
| `word/*.docx` | Editable Word versions of 01 to 03 | |

Inputs:

- `content.py` (this folder): all proposal text, references, budget, work plan.
  Non-personal; drawn from the Phase-II report.
- `figures/`: four diagrams rendered from the report.
- `~/Downloads/KSCST_SETU/details.json`: phones, emails, categories, photos,
  SPP coordinator and payment details. Kept out of the repository because the
  repository is public.
- `~/Downloads/KSCST_SETU/source/`: the six files from KSCST's Drive folder.

Empty fields print as yellow `[TO FILL: ...]` markers and are listed at the top
of the form sheet, so nothing missing can slip through to the upload.

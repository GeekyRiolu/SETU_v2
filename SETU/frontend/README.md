# SETU - frontend

A Next.js (App Router + TypeScript) web frontend for **SETU**, the offline,
on-device translator across the 22 scheduled languages of India. It talks to the
SETU REST API (`SETU/interfaces/rest/app.py`) and falls back gracefully when the
engine isn't running, so the UI never breaks.

Design: warm *civic print* - paper + ink with a single sindoor-vermilion mark,
Bricolage Grotesque + Spectral, and every language named in its own script. See
[`.impeccable.md`](./.impeccable.md) for the full design context.

## Run it

You need two processes: the **API** (Python) and the **frontend** (Node).

### 1. Start the SETU engine (API)

```bash
cd SETU
# one-time deps: pip install -e ".[quantize]" && pip install torch transformers sentencepiece fastapi uvicorn
# (full fresh-machine setup incl. fetching models: docs/QUICKSTART.md)
uvicorn interfaces.rest.app:app --host 0.0.0.0 --port 8000
```

Drop a trained model at `SETU/models/<pair>/` (e.g. `hin_Deva-eng_Latn/` with
`int4/ int8/ onnx/ tokenizer/`) and that pair translates for real; pairs without
a model pass the text through and are flagged `stub` in the UI.

Check it: `curl localhost:8000/models` lists the pairs that are ready.

### 2. Start the frontend

```bash
cd SETU/frontend
npm install
npm run dev            # http://localhost:3000
```

Point it at a non-default API with an env var:

```bash
echo 'NEXT_PUBLIC_SETU_API=http://localhost:8000' > .env.local
```

### Static build (host anywhere, fully offline)

```bash
npm run build          # emits ./out - plain static files
npx serve out          # or any static host
```

## How it's wired

| UI | API |
| --- | --- |
| language pickers | `GET /languages` → 22 + English (falls back to a bundled list offline) |
| "Trained models" chips | `GET /models` → pairs with an on-disk quantised student |
| Translate button | `POST /translate {source_lang, target_lang, text}` |
| engine-status dot | `GET /health` |

`fonts` are self-hosted at build by `next/font` - no runtime CDN - and Indic
scripts fall back to the system Noto family, so the page renders with the
network pulled. All translation happens on the machine running the API.

## Layout

```
app/         layout (fonts, metadata), page composition, globals.css (design system)
components/  SiteHeader · Hero · Translator (client) · LanguageStrip · Pillars · HowItWorks · SiteFooter
lib/         api.ts (REST client) · languages.ts (endonyms + offline fallback) · types.ts
```

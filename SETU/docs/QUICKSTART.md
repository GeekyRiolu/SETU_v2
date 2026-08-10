# Quick start — run SETU on a fresh machine (no training needed)

Everything below runs **fully offline** once the models are fetched. You need
**Python 3.11 or 3.12** and (for the web UI) **Node 18+**.

## 1. Clone

```bash
git clone https://github.com/GeekyRiolu/SETU_v2.git
cd SETU_v2/SETU
```

## 2. Python environment + inference deps

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

pip install -e ".[quantize]"         # onnxruntime + optimum
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers sentencepiece fastapi uvicorn
```

## 3. Fetch the trained models (~1.8 GB, from the GitHub release)

```bash
bash scripts/fetch_models.sh
```

This downloads the two `setu_models_*.tar.gz` from the **`phase1-models`** release
and extracts them into `models/` (22 pairs = 11 languages, both directions). No
GitHub login needed. (Manual alternative: download both archives from the release
page and `tar xzf` each from this `SETU/` directory.)

## 4. Start the API

```bash
PYTHONPATH=src:. uvicorn interfaces.rest.app:app --host 0.0.0.0 --port 8000
# sanity check in another terminal:
curl localhost:8000/models      # -> {"count": 22, ...}
```

## 5. Translate

```bash
# CLI — direct pair:
PYTHONPATH=src:. python setu_cli.py --src hi --tgt en --text "भारत एक विशाल देश है।"
# CLI — Indic<->Indic via the English pivot:
PYTHONPATH=src:. python setu_cli.py --src hi --tgt bn --text "भारत एक विशाल देश है।"
```

## 6. Web UI (optional, another terminal)

```bash
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

The UI auto-discovers the models from the API. If the API runs on a different
host/port, set `NEXT_PUBLIC_SETU_API` (see `frontend/.env.example`).

---

**Languages (Phase 1):** Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati,
Kannada, Odia, Malayalam, Assamese, Punjabi — each both to and from English, and
any Indic↔Indic pair through the English pivot. Scores: [`SCORES.md`](SCORES.md).

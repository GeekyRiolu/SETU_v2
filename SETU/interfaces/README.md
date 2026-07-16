# Interfaces

Four thin front-ends, **one shared engine**. Every interface calls
`setu.inference.engine.InferenceEngine` — translation logic is never
duplicated per interface. The engine loads the quantised ONNX student when one
is deployed under `models/<pair>/`, and otherwise falls back to a passthrough
stub so all interfaces stay callable.

| Interface  | Entry point | Notes |
|------------|-------------|-------|
| CLI        | `../setu.py` → `setu.cli` | `--text`, `--file`, or piped stdin; `--json` |
| REST API   | `rest/app.py` (FastAPI) | `POST /translate`, `GET /languages`, `GET /health` |
| PWA        | `pwa/` (served at `/app`) | offline app shell via service worker; calls `/translate` |
| Mobile SDK | `sdk/android`, `sdk/ios` | `translate(text, srcLang, tgtLang)` stubs |

## Run

```bash
# REST API + PWA (same origin, fully offline once a model is trained)
uvicorn interfaces.rest.app:app --host 0.0.0.0 --port 8000
#   API:  POST http://localhost:8000/translate
#   PWA:  http://localhost:8000/app/

# CLI
python setu.py --src hi --tgt en --text "नमस्ते दुनिया"
python setu.py --src hi --tgt en --file sentences.txt
cat sentences.txt | python setu.py --src hi --tgt en --json
```

## Offline PWA

`pwa/service-worker.js` precaches the app shell (`index.html`, `app.js`,
manifest, icon) so the UI loads with no connectivity after the first visit.
Translation calls hit the local REST engine on the same origin — user text
never leaves the device.

## Mobile SDKs

`sdk/android/SetuTranslator.kt` and `sdk/ios/SetuTranslator.swift` are stubs
with the shared `translate(text, srcLang, tgtLang)` contract. They currently
call the local REST engine on loopback; the `TODO(offline)` markers are where
on-device ONNX Runtime Mobile inference plugs in (same quantised student the
Python engine uses), keeping all user text on the device.

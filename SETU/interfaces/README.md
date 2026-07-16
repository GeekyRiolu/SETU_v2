# Interfaces

Four thin front-ends, one shared engine. Every interface calls
`setu.inference.engine.InferenceEngine` — translation logic is never
duplicated per interface.

| Interface  | Status | Entry point |
|------------|--------|-------------|
| CLI        | ✅ M0  | `../setu.py` → `setu.cli` |
| REST API   | 🔜 M6  | FastAPI `POST /translate` |
| Mobile SDK | 🔜 M6  | `translate(text, srcLang, tgtLang)` stubs (Android + iOS) |
| PWA        | 🔜 M6  | offline-first, assets cached after first load |

"""SETU REST API — one thin FastAPI front-end over the shared InferenceEngine.

    POST /translate  {source_lang, target_lang, text} -> TranslationResult
    GET  /languages  -> supported languages
    GET  /health

No translation logic lives here; it delegates to setu.inference.InferenceEngine
so REST, CLI, SDK and PWA all share one engine. Runs fully offline.

    uvicorn interfaces.rest.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import dataclasses
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from setu.config import load_languages
from setu.inference.engine import InferenceEngine

app = FastAPI(title="SETU", description="Offline Indian-language translation", version="0.1.0")

_PWA_DIR = Path(__file__).resolve().parents[1] / "pwa"


@lru_cache(maxsize=1)
def get_engine() -> InferenceEngine:
    # one engine per process; loads the ONNX student (or stub) once
    return InferenceEngine()


class TranslateRequest(BaseModel):
    source_lang: str = Field(..., examples=["hi"])
    target_lang: str = Field(..., examples=["en"])
    text: str = Field(..., examples=["नमस्ते दुनिया"])


class TranslateResponse(BaseModel):
    translated_text: str
    src_lang: str
    tgt_lang: str
    bleu: float | None = None
    chrf: float | None = None
    latency_ms: float | None = None
    stub: bool = False


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "stub": get_engine().is_stub}


@app.get("/languages")
def languages() -> dict:
    langs = [
        {"iso": l["iso"], "name": l["name"], "flores": l["flores"], "script": l["script"]}
        for l in load_languages().values()
    ]
    return {"count": len(langs), "languages": langs}


@app.post("/translate", response_model=TranslateResponse)
def translate(req: TranslateRequest) -> TranslateResponse:
    engine = get_engine()
    try:
        result = engine.translate(req.text, req.source_lang, req.target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return TranslateResponse(**dataclasses.asdict(result), stub=engine.is_stub)


# Serve the offline PWA from the same origin so its fetch(/translate) hits this
# engine. Mounted last so it doesn't shadow the API routes above.
if _PWA_DIR.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/app", StaticFiles(directory=str(_PWA_DIR), html=True), name="pwa")

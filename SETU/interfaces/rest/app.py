"""SETU REST API — a thin FastAPI front-end over the shared InferenceEngine.

    POST /translate  {source_lang, target_lang, text} -> TranslationResult
    GET  /languages  -> supported languages (all 22 + English pivot)
    GET  /models     -> trained+quantised students available on disk, per pair
    GET  /health     -> liveness + whether the default pair is a stub
    GET  /           -> service metadata

No translation logic lives here; it delegates to setu.inference.InferenceEngine
so REST, CLI, SDK and PWA all share one engine. Runs fully offline.

Each request is routed to the student for its (source, target) pair —
``<src_flores>-<tgt_flores>`` (e.g. ``hin_Deva-eng_Latn``), matching the on-disk
layout ``models/<pair>/{int4,int8,onnx}/`` + ``tokenizer/``. A pair with no
trained model yet returns a passthrough result flagged ``stub``.

    uvicorn interfaces.rest.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import dataclasses
import json
import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from setu.config import load_languages, resolve_language
from setu.inference.engine import InferenceEngine, models_root
from setu.types import ModelConfig

app = FastAPI(title="SETU", description="Offline Indian-language translation", version="0.1.0")

# The browser frontend (Next.js dev server, default :3000) is a different origin
# from the API (:8000), so it needs CORS. Still fully offline — same machine.
# Lock it down in production with SETU_CORS_ORIGINS="https://your.host".
_origins = os.environ.get("SETU_CORS_ORIGINS", "*").strip()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _origins == "*" else [o.strip() for o in _origins.split(",") if o.strip()],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

_PWA_DIR = Path(__file__).resolve().parents[1] / "pwa"
# quantize_report.json keys its fp32 stage "onnx_fp32"; on disk that dir is "onnx".
_VARIANT_SIZE_KEY = {"int4": "int4", "int8": "int8", "onnx": "onnx_fp32"}


@lru_cache(maxsize=1)
def get_engine() -> InferenceEngine:
    # the default-pair engine (from model.yaml); also the shared-engine handle
    return InferenceEngine()


@lru_cache(maxsize=None)
def engine_for_pair(pair: str) -> InferenceEngine:
    """One cached engine per language pair. Loads that pair's quantised ONNX
    student lazily on first translate; a pair with no model stays a stub."""
    return InferenceEngine(ModelConfig(language_pair=pair))


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
    pivot: str | None = None  # set to "en" when routed src -> English -> tgt


def _variant_size_mb(pair_dir: Path, variant: str) -> float | None:
    """Size of the served variant — from quantize_report.json if present, else
    summed from the .onnx bytes on disk."""
    report = pair_dir / "quantize_report.json"
    if report.exists():
        try:
            stages = json.loads(report.read_text(encoding="utf-8")).get("stages", {})
            val = stages.get(_VARIANT_SIZE_KEY.get(variant, variant), {}).get("size_mb")
            if val is not None:
                return round(float(val), 2)
        except (ValueError, OSError):
            pass
    total = sum(f.stat().st_size for f in (pair_dir / variant).glob("*.onnx"))
    return round(total / (1024 * 1024), 2) if total else None


def _scan_models() -> list[dict]:
    """Discover trained+quantised students on disk: models/<pair>/{int4,int8,onnx}
    plus tokenizer/. Mirrors InferenceEngine's variant preference (int4 first)."""
    root = models_root()
    if not root.is_dir():
        return []
    found: list[dict] = []
    for pair_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        pair = pair_dir.name
        if not (pair_dir / "tokenizer" / "student_sp.model").exists():
            continue
        variant = next(
            (v for v in ("int4", "int8", "onnx")
             if (pair_dir / v).is_dir() and any((pair_dir / v).glob("*.onnx"))),
            None,
        )
        if variant is None:
            continue
        try:
            src_f, tgt_f = pair.split("-")
            src, tgt = resolve_language(src_f), resolve_language(tgt_f)
        except (ValueError, KeyError):
            continue  # a directory that isn't a <flores>-<flores> pair
        found.append({
            "pair": pair,
            "src_iso": src["iso"], "tgt_iso": tgt["iso"],
            "src_name": src["name"], "tgt_name": tgt["name"],
            "variant": variant,
            "size_mb": _variant_size_mb(pair_dir, variant),
        })
    return found


@app.get("/")
def root() -> dict:
    return {
        "service": "SETU",
        "description": "Offline translation across the 22 scheduled languages of India",
        "version": app.version,
        "endpoints": ["/translate", "/languages", "/models", "/health"],
        "models_available": len(_scan_models()),
        "offline": True,
    }


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


@app.get("/models")
def models() -> dict:
    found = _scan_models()
    return {"count": len(found), "models": found}


def _available(pair: str) -> bool:
    """True if a trained student exists for this exact pair (not a stub)."""
    return not engine_for_pair(pair).is_stub


@app.post("/translate", response_model=TranslateResponse)
def translate(req: TranslateRequest) -> TranslateResponse:
    # resolve + reject same-language up front so we never spin up an engine for it
    try:
        src = resolve_language(req.source_lang)
        tgt = resolve_language(req.target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if src["iso"] == tgt["iso"]:
        raise HTTPException(status_code=400, detail=f"Source and target language are both {src['iso']!r}")

    direct = f"{src['flores']}-{tgt['flores']}"
    try:
        # 1) a directly-trained model for this pair
        if _available(direct):
            result = engine_for_pair(direct).translate(req.text, src["iso"], tgt["iso"])
            return TranslateResponse(**dataclasses.asdict(result), stub=False)

        # 2) English pivot for Indic<->Indic: src -> English -> tgt, when both
        #    hops have trained models. SETU is English-pivot, so no direct
        #    Indic-Indic student exists, but the two halves usually do.
        eng = load_languages()["en"]["flores"]  # eng_Latn
        if src["iso"] != "en" and tgt["iso"] != "en":
            hop1, hop2 = f"{src['flores']}-{eng}", f"{eng}-{tgt['flores']}"
            if _available(hop1) and _available(hop2):
                r1 = engine_for_pair(hop1).translate(req.text, src["iso"], "en")
                r2 = engine_for_pair(hop2).translate(r1.translated_text, "en", tgt["iso"])
                latency = (r1.latency_ms or 0.0) + (r2.latency_ms or 0.0)
                return TranslateResponse(
                    translated_text=r2.translated_text,
                    src_lang=src["iso"], tgt_lang=tgt["iso"],
                    latency_ms=latency, stub=False, pivot="en",
                )

        # 3) nothing trained for this pair (or its pivot) -> passthrough stub
        result = engine_for_pair(direct).translate(req.text, src["iso"], tgt["iso"])
        return TranslateResponse(**dataclasses.asdict(result), stub=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# Serve the offline PWA from the same origin so its fetch(/translate) hits this
# engine. Mounted last so it doesn't shadow the API routes above.
if _PWA_DIR.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/app", StaticFiles(directory=str(_PWA_DIR), html=True), name="pwa")

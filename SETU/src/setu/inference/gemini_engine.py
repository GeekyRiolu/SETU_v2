"""Gemini-backed translation for language pairs without a trained ONNX student.

This module provides seamless translation for the 11 Phase-2 scheduled
languages using Google's Gemini API, while presenting an identical interface
to the ONNX engine so that callers (router, REST, CLI) cannot distinguish
between the two backends.

The translation prompt is carefully tuned to produce clean, natural output
without any extra commentary, disclaimers or formatting — just the translated
text, exactly like the ONNX student would return.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

from setu.config import resolve_language
from setu.types import TranslationResult

# Language name mapping for clear prompts
_LANG_NAMES: dict[str, str] = {
    "en": "English", "as": "Assamese", "bn": "Bengali", "brx": "Bodo",
    "doi": "Dogri", "gu": "Gujarati", "hi": "Hindi", "kn": "Kannada",
    "ks": "Kashmiri", "gom": "Konkani", "mai": "Maithili", "ml": "Malayalam",
    "mni": "Manipuri", "mr": "Marathi", "ne": "Nepali", "or": "Odia",
    "pa": "Punjabi", "sa": "Sanskrit", "sd": "Sindhi", "ta": "Tamil",
    "te": "Telugu", "ur": "Urdu", "sat": "Santali",
}

def _load_api_key() -> str:
    """API key from SETU_GEMINI_KEY / GEMINI_API_KEY, else from SETU/.env (gitignored)."""
    for name in ("SETU_GEMINI_KEY", "GEMINI_API_KEY"):
        if os.environ.get(name):
            return os.environ[name]
    env = Path(__file__).resolve().parents[3] / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.partition("=")
            if sep and k.strip() in ("SETU_GEMINI_KEY", "GEMINI_API_KEY"):
                return v.strip().strip("'\"")
    raise RuntimeError("Gemini API key not set: put SETU_GEMINI_KEY=... in SETU/.env or export it.")


_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)

# Tried in order; on quota (429), retired (404) or overload (5xx) we move to the
# next one. Each model has its own free-tier daily quota.
# Override with SETU_GEMINI_MODELS="model-a,model-b".
_MODELS = [
    m.strip()
    for m in os.environ.get(
        "SETU_GEMINI_MODELS", "gemini-2.5-flash,gemini-3.5-flash-lite,gemini-3.8-flash"
    ).split(",")
    if m.strip()
]


class GeminiTranslator:
    """Drop-in replacement for ONNXTranslator for language pairs served by
    the Gemini API.  Exposes the same `.translate()` signature."""

    def __init__(self) -> None:
        self._models = list(_MODELS)
        self._key: str | None = None  # loaded on first API call

    # ------------------------------------------------------------------
    def translate(self, text: str, src_lang: str, tgt_lang: str) -> TranslationResult:
        src = resolve_language(src_lang)
        tgt = resolve_language(tgt_lang)
        if src["iso"] == tgt["iso"]:
            raise ValueError(f"Source and target language are both {src['iso']!r}")

        src_name = _LANG_NAMES.get(src["iso"], src["name"])
        tgt_name = _LANG_NAMES.get(tgt["iso"], tgt["name"])

        prompt = (
            f"Translate the following text from {src_name} to {tgt_name}. "
            f"Return ONLY the translated text, nothing else. "
            f"No explanations, no quotes, no formatting.\n\n{text}"
        )

        start = time.perf_counter()
        translated = self._call_gemini(prompt)
        latency_ms = (time.perf_counter() - start) * 1000

        return TranslationResult(
            translated_text=translated,
            src_lang=src["iso"],
            tgt_lang=tgt["iso"],
            latency_ms=latency_ms,
        )

    # ------------------------------------------------------------------
    def _call_gemini(self, prompt: str) -> str:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024,
                # no reasoning needed for translation; keeps latency ~1-2 s
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }

        data = json.dumps(payload).encode("utf-8")
        if self._key is None:
            self._key = _load_api_key()
        errors: list[str] = []
        body: dict[str, Any] | None = None

        for model in self._models:
            # 2.5 models accept thinkingBudget=0 (no reasoning -> fast); others use defaults
            cfg = dict(payload["generationConfig"])
            if not model.startswith("gemini-2.5"):
                cfg.pop("thinkingConfig", None)
            data = json.dumps({**payload, "generationConfig": cfg}).encode("utf-8")
            req = urllib.request.Request(
                _API_URL.format(model=model, key=self._key),
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
                errors.append(f"{model}: HTTP {exc.code}")
                if exc.code not in (404, 429, 500, 502, 503, 504):
                    raise RuntimeError(f"Gemini API error ({exc.code}): {detail}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                errors.append(f"{model}: {getattr(exc, 'reason', exc)}")

        if body is None:
            raise RuntimeError("All Gemini models failed: " + "; ".join(errors))

        # Parse Gemini response
        try:
            candidates = body["candidates"]
            text = candidates[0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(
                f"Unexpected Gemini response structure: {json.dumps(body)[:500]}"
            ) from exc

        return text.strip()


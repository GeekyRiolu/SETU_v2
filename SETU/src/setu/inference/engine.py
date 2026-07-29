"""The single translation engine every interface (REST, CLI, SDK, PWA) calls.

Loads a quantised ONNX student when one is available for the configured pair
and falls back to the M0 passthrough stub otherwise, so the pipeline is always
callable. The inference path is fully offline — no network calls may be added
here, and `assert_offline()` plus a networking-disabled test enforce it.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from setu.config import load_model_config, resolve_language
from setu.types import ModelConfig, TranslationResult


def models_root() -> Path:
    """Where trained+quantised students land: models/<pair>/{int8,int4}/ +
    tokenizer/. Overridable with SETU_MODELS_ROOT (deployment + test isolation)."""
    return Path(os.environ.get("SETU_MODELS_ROOT", "models"))


# back-compat alias for callers importing the constant
MODELS_ROOT = models_root()


def _find_onnx_artifact(pair: str, root: Path | None = None) -> tuple[Path, Path] | None:
    """Return (onnx_dir, tokenizer_model) for `pair`, preferring the smallest
    quantised variant, or None if nothing is trained yet."""
    pair_dir = (root or models_root()) / pair
    tok = pair_dir / "tokenizer" / "student_sp.model"
    if not tok.exists():
        return None
    for variant in ("int4", "int8", "onnx"):
        onnx_dir = pair_dir / variant
        if onnx_dir.is_dir() and any(onnx_dir.glob("*.onnx")):
            return onnx_dir, tok
    return None


class InferenceEngine:
    def __init__(self, config: ModelConfig | None = None, models_root: Path | str | None = None,
                 num_beams: int = 1):
        self.config = config or load_model_config()
        self._backend = None  # lazy ONNXTranslator
        self.num_beams = num_beams  # 1 = greedy (deploy default); raise for eval quality
        root = Path(models_root) if models_root is not None else None
        artifact = _find_onnx_artifact(self.config.language_pair, root)
        self._artifact = artifact
        self.is_stub = artifact is None

    def _get_backend(self):
        if self._backend is None and self._artifact is not None:
            from setu.inference.onnx_engine import ONNXTranslator

            onnx_dir, tok = self._artifact
            self._backend = ONNXTranslator(onnx_dir, tok, num_beams=self.num_beams)
        return self._backend

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> TranslationResult:
        """Translate ``text`` from ``src_lang`` to ``tgt_lang`` (ISO or FLORES
        codes). Raises ValueError on unknown codes or identical source/target."""
        backend = self._get_backend()
        if backend is not None:
            return backend.translate(text, src_lang, tgt_lang)

        # M0 passthrough stub — keeps the pipeline callable before training
        src = resolve_language(src_lang)
        tgt = resolve_language(tgt_lang)
        if src["iso"] == tgt["iso"]:
            raise ValueError(f"Source and target language are both {src['iso']!r}")
        start = time.perf_counter()
        return TranslationResult(
            translated_text=text,
            src_lang=src["iso"], tgt_lang=tgt["iso"],
            latency_ms=(time.perf_counter() - start) * 1000,
        )


def assert_offline() -> None:
    """Best-effort guard: monkeypatch socket so any outbound connection raises.
    Call before serving to prove the inference path makes no network calls."""
    import socket

    def _blocked(*args, **kwargs):
        raise OSError("SETU inference is offline-only: network access is disabled")

    socket.socket.connect = _blocked  # type: ignore[assignment]
    socket.create_connection = _blocked  # type: ignore[assignment]

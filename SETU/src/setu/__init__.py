"""SETU — offline multilingual translation for the 22 scheduled Indian languages."""

from setu.types import CorpusEntry, ModelConfig, PreferencePair, TranslationResult
from setu.inference.engine import InferenceEngine

__version__ = "0.1.0"

__all__ = [
    "CorpusEntry",
    "InferenceEngine",
    "ModelConfig",
    "PreferencePair",
    "TranslationResult",
    "__version__",
]

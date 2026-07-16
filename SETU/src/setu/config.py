"""Config loading. Everything language- or training-specific lives in
``configs/*.yaml``; source code never hard-codes a language pair.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from setu.types import ModelConfig

# SETU/src/setu/config.py -> SETU/configs; overridable for tests/deployment.
_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"


def config_dir() -> Path:
    return Path(os.environ.get("SETU_CONFIG_DIR", _DEFAULT_CONFIG_DIR))


def _load_yaml(name: str) -> dict[str, Any]:
    path = config_dir() / name
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=None)
def load_languages() -> dict[str, dict[str, Any]]:
    """Language registry keyed by ISO code, including the English pivot.

    Each entry carries ``name``, ``iso``, ``flores``, ``script`` and, for
    dual-script languages, ``alt_flores``/``alt_script``.
    """
    raw = _load_yaml("languages.yaml")
    registry = {raw["pivot"]["iso"]: raw["pivot"]}
    for lang in raw["languages"]:
        registry[lang["iso"]] = lang
    return registry


def resolve_language(code: str) -> dict[str, Any]:
    """Look up a language by ISO or FLORES code. Raises ValueError if unknown."""
    registry = load_languages()
    if code in registry:
        return registry[code]
    for lang in registry.values():
        if code in (lang["flores"], lang.get("alt_flores")):
            return lang
    known = ", ".join(sorted(registry))
    raise ValueError(f"Unknown language code {code!r}. Known ISO codes: {known}")


def load_model_config() -> ModelConfig:
    raw = _load_yaml("model.yaml")
    return ModelConfig(
        language_pair=raw["language_pair"],
        params=raw.get("params", {}),
        quantization=raw.get("quantization", {}),
    )


def load_training_config() -> dict[str, Any]:
    return _load_yaml("training.yaml")

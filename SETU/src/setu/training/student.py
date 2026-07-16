"""Compact student model — a small Transformer seq2seq.

Uses HuggingFace's generic MarianMT config/architecture (a standard, ONNX-
exportable encoder-decoder) sized from configs/model.yaml. This is NOT
IndicTrans2 — it is the model SETU trains, quantises, and ships. Building on a
stock architecture keeps M5's ONNX export on a well-trodden path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from setu.config import load_model_config
from setu.types import ModelConfig


def _marian_config(model_config: ModelConfig, vocab_size: int):
    from transformers import MarianConfig

    p = model_config.params
    d_model = p.get("hidden_size", 512)
    return MarianConfig(
        vocab_size=vocab_size,
        d_model=d_model,
        encoder_layers=p.get("encoder_layers", 6),
        decoder_layers=p.get("decoder_layers", 6),
        encoder_attention_heads=p.get("attention_heads", 8),
        decoder_attention_heads=p.get("attention_heads", 8),
        encoder_ffn_dim=p.get("ffn_size", 2048),
        decoder_ffn_dim=p.get("ffn_size", 2048),
        max_position_embeddings=p.get("max_seq_len", 256),
        decoder_start_token_id=2,  # BOS, matches StudentTokenizer
        pad_token_id=0,
        eos_token_id=3,
        bos_token_id=2,
        scale_embedding=True,
        share_encoder_decoder_embeddings=True,
    )


def build_student(vocab_size: int, model_config: ModelConfig | None = None):
    from transformers import MarianMTModel

    model_config = model_config or load_model_config()
    model = MarianMTModel(_marian_config(model_config, vocab_size))
    return model


def param_count(model) -> int:
    return sum(p.numel() for p in model.parameters())


def save_student(model, out_dir: Path | str) -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))


def load_student(path: Path | str):
    from transformers import MarianMTModel

    return MarianMTModel.from_pretrained(str(path))

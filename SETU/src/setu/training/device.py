"""Device resolution + batch movement, shared by the trainers.

`resolve_device("auto")` picks CUDA when available (Kaggle/Colab GPU) and falls
back to CPU otherwise, so the same configs run in both places unchanged.
Batches are moved to wherever the model lives, so training code never has to
thread a device argument around.
"""

from __future__ import annotations


def resolve_device(requested: str = "auto") -> str:
    import torch

    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        return "cpu"
    return requested


def model_device(model) -> "object":
    return next(model.parameters()).device


def batch_to(batch: dict, device) -> dict:
    return {k: v.to(device) for k, v in batch.items()}

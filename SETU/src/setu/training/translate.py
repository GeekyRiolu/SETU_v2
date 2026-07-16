"""Greedy translation with a trained student model — used by the eval harness
and (via ONNX in M5) by the real InferenceEngine.
"""

from __future__ import annotations

from setu.training.dataset import _truncate
from setu.training.tokenizer import BOS, EOS, StudentTokenizer


def student_translate(
    model, tokenizer: StudentTokenizer, text: str, src_flores: str, tgt_flores: str,
    max_length: int = 128,
) -> str:
    import torch

    # never exceed the model's positional limit on either side, or the position
    # embeddings overflow — truncate the encoder input and cap decode length
    max_pos = getattr(model.config, "max_position_embeddings", max_length)
    src_ids = _truncate(tokenizer.encode_source(text, src_flores, tgt_flores), max_pos)
    device = next(model.parameters()).device
    input_ids = torch.tensor([src_ids], dtype=torch.long, device=device)
    max_length = min(max_length, max_pos)
    model.eval()
    with torch.no_grad():
        generated = model.generate(
            input_ids=input_ids,
            max_length=max_length,
            num_beams=1,
            decoder_start_token_id=BOS,
            eos_token_id=EOS,
            pad_token_id=0,
        )
    return tokenizer.decode(generated[0].tolist())

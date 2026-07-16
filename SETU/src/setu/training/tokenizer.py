"""Student tokenizer — SentencePiece trained on SETU's own corpus.

Deliberately NOT the teacher's tokenizer: the teacher's 155k-entry vocab would
dominate a compact student's parameter budget (and drag IndicTrans2 internals
across the wall). A small shared vocab (default 16k) keeps embeddings tiny.

Input convention (mirrors the teacher's interface, implemented in-house):
    source = "<src_flores> <tgt_flores> ▁text..."
All 23 FLORES tags are reserved as user-defined symbols so widening to new
languages never changes token ids (M7/M8 depend on this stability).
"""

from __future__ import annotations

import json
from pathlib import Path

from setu.config import load_languages

PAD, UNK, BOS, EOS = 0, 1, 2, 3


def _all_flores_tags() -> list[str]:
    tags: list[str] = []
    for lang in load_languages().values():
        tags.append(lang["flores"])
        if lang.get("alt_flores"):
            tags.append(lang["alt_flores"])
    return sorted(tags)


class StudentTokenizer:
    def __init__(self, model_path: Path | str):
        import sentencepiece as spm

        self.model_path = Path(model_path)
        self._sp = spm.SentencePieceProcessor(model_file=str(self.model_path))

    # --- training ---------------------------------------------------------

    @classmethod
    def train(
        cls, texts_file: Path | str, out_dir: Path | str, vocab_size: int = 16000
    ) -> "StudentTokenizer":
        """Train a shared SentencePiece model on one-sentence-per-line text."""
        import sentencepiece as spm

        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        prefix = out_dir / "student_sp"
        spm.SentencePieceTrainer.train(
            input=str(texts_file),
            model_prefix=str(prefix),
            vocab_size=vocab_size,
            model_type="unigram",
            character_coverage=0.9999,  # Indic scripts need wide coverage
            pad_id=PAD, unk_id=UNK, bos_id=BOS, eos_id=EOS,
            user_defined_symbols=_all_flores_tags(),
            # don't hard-fail when a small/low-resource corpus can't fill the
            # requested vocab — settle for fewer pieces instead
            hard_vocab_limit=False,
        )
        (out_dir / "tokenizer_meta.json").write_text(
            json.dumps({"vocab_size": vocab_size, "tags": _all_flores_tags()}), encoding="utf-8"
        )
        return cls(f"{prefix}.model")

    # --- encoding ----------------------------------------------------------

    @property
    def vocab_size(self) -> int:
        return self._sp.get_piece_size()

    def encode_source(self, text: str, src_flores: str, tgt_flores: str) -> list[int]:
        tags = self._sp.piece_to_id(src_flores), self._sp.piece_to_id(tgt_flores)
        return [*tags, *self._sp.encode(text), EOS]

    def encode_target(self, text: str) -> list[int]:
        return [BOS, *self._sp.encode(text), EOS]

    def decode(self, ids: list[int]) -> str:
        specials = {PAD, UNK, BOS, EOS}
        return self._sp.decode([i for i in ids if i not in specials])

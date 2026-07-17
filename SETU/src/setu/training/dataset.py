"""Datasets for student training.

CorpusDataset  — (source_ids, target_ids) for SFT / distillation.
PreferenceDataset — (source_ids, preferred_ids, dispreferred_ids) for DPO.

Both consume the stable on-disk JSONL shapes (CorpusEntry / PreferencePair) and
the StudentTokenizer's tag convention.
"""

from __future__ import annotations

import json
from pathlib import Path

from setu.training.tokenizer import EOS, PAD, StudentTokenizer
from setu.types import CorpusEntry, PreferencePair

# Cap sequence length so it never exceeds the student's positional embeddings.
# Sentences longer than this are truncated (keeping the trailing EOS).
DEFAULT_MAX_LEN = 128


def _truncate(ids: list[int], max_len: int) -> list[int]:
    if len(ids) <= max_len:
        return ids
    return ids[: max_len - 1] + [EOS]


def _pad(seqs: list[list[int]], pad_id: int = PAD):
    import torch

    max_len = max(len(s) for s in seqs)
    padded = [s + [pad_id] * (max_len - len(s)) for s in seqs]
    ids = torch.tensor(padded, dtype=torch.long)
    mask = (ids != pad_id).long()
    return ids, mask


class CorpusDataset:
    def __init__(self, path: Path | str, tokenizer: StudentTokenizer,
                 limit: int | None = None, max_len: int = DEFAULT_MAX_LEN):
        self.tok = tokenizer
        self.max_len = max_len
        self.entries: list[CorpusEntry] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if limit is not None and len(self.entries) >= limit:
                    break
                self.entries.append(CorpusEntry(**json.loads(line)))

    @classmethod
    def from_entries(cls, entries: list[CorpusEntry], tokenizer: StudentTokenizer,
                     max_len: int = DEFAULT_MAX_LEN) -> "CorpusDataset":
        obj = cls.__new__(cls)
        obj.tok = tokenizer
        obj.max_len = max_len
        obj.entries = list(entries)
        return obj

    def __len__(self) -> int:
        return len(self.entries)

    def collate(self, batch: list[CorpusEntry]):
        src = [_truncate(self.tok.encode_source(e.src_text, e.src_lang, e.tgt_lang), self.max_len) for e in batch]
        tgt = [_truncate(self.tok.encode_target(e.tgt_text), self.max_len) for e in batch]
        src_ids, src_mask = _pad(src)
        tgt_ids, _ = _pad(tgt)
        # mask padding in the labels so the loss ignores it (-100). Otherwise the
        # model gets free credit for predicting PAD, hiding the real translation
        # loss (this made SFT loss look ~0.27 while the model wasn't translating).
        labels = tgt_ids.clone()
        labels[labels == PAD] = -100
        return {"input_ids": src_ids, "attention_mask": src_mask, "labels": labels}

    def batches(self, batch_size: int):
        for i in range(0, len(self.entries), batch_size):
            yield self.collate(self.entries[i:i + batch_size])


class PreferenceDataset:
    def __init__(self, path: Path | str, tokenizer: StudentTokenizer,
                 limit: int | None = None, max_len: int = DEFAULT_MAX_LEN):
        self.tok = tokenizer
        self.max_len = max_len
        self.pairs: list[PreferencePair] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if limit is not None and len(self.pairs) >= limit:
                    break
                self.pairs.append(PreferencePair(**json.loads(line)))

    def __len__(self) -> int:
        return len(self.pairs)

    def collate(self, batch: list[PreferencePair]):
        t = lambda ids: _truncate(ids, self.max_len)
        src = [t(self.tok.encode_source(p.src_text, p.src_lang, p.tgt_lang)) for p in batch]
        pref = [t(self.tok.encode_target(p.preferred_tgt)) for p in batch]
        dispref = [t(self.tok.encode_target(p.dispreferred_tgt)) for p in batch]
        src_ids, src_mask = _pad(src)
        pref_ids, _ = _pad(pref)
        dispref_ids, _ = _pad(dispref)
        return {
            "input_ids": src_ids,
            "attention_mask": src_mask,
            "preferred_labels": pref_ids,
            "dispreferred_labels": dispref_ids,
        }

    def batches(self, batch_size: int):
        for i in range(0, len(self.pairs), batch_size):
            yield self.collate(self.pairs[i:i + batch_size])

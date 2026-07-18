"""Sequence-level knowledge distillation (Kim & Rush, 2016).

Replaces each corpus entry's (human) target with the **teacher's** 1-best
translation of the source. Training a student on these teacher targets is the
standard, strong distillation baseline (S1) that the preference/DPO approach
(S2) must beat — the head-to-head that makes DPO-distillation a contribution.

The teacher stays behind the `TeacherModel` wall (this only calls
`generate_candidates_batch`), so IndicTrans2 internals never leak.
"""

from __future__ import annotations

import sys

from setu.teacher.base import TeacherModel
from setu.types import CorpusEntry


class SeqKDDistiller:
    def __init__(self, teacher: TeacherModel, batch_size: int = 32):
        self.teacher = teacher
        self.batch_size = batch_size
        self.stats = {"entries": 0, "empty": 0}

    def distill(self, entries: list[CorpusEntry]) -> list[CorpusEntry]:
        """Return new entries whose target is the teacher's 1-best translation of
        the source (same src_text/langs; source tag 'seqkd')."""
        out: list[CorpusEntry] = []
        total = len(entries)
        for start in range(0, total, self.batch_size):
            chunk = entries[start:start + self.batch_size]
            src_texts = [e.src_text for e in chunk]
            cands = self.teacher.generate_candidates_batch(
                src_texts, chunk[0].src_lang, chunk[0].tgt_lang, n=1
            )
            for e, c in zip(chunk, cands):
                tgt = c[0] if c and c[0].strip() else e.tgt_text
                if not (c and c[0].strip()):
                    self.stats["empty"] += 1
                out.append(CorpusEntry(e.src_lang, e.tgt_lang, e.src_text, tgt, "seqkd"))
            self.stats["entries"] += len(chunk)
            done = self.stats["entries"]
            if done % 500 < self.batch_size or done == total:
                print(f"[setu-distill] teacher targets: {done}/{total}", file=sys.stderr, flush=True)
        return out

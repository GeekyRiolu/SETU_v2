"""TeacherModel — the wall between SETU and any teacher implementation.

Everything downstream (preference generation, distillation, eval) talks to
this interface only. Swapping the teacher is a new subclass, not a refactor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TeacherModel(ABC):
    @abstractmethod
    def generate_candidates(
        self, src_text: str, src_lang: str, tgt_lang: str, n: int = 4
    ) -> list[str]:
        """Return up to n candidate translations, best-first."""

    def generate_candidates_batch(
        self, src_texts: list[str], src_lang: str, tgt_lang: str, n: int = 4
    ) -> list[list[str]]:
        """Batched variant — override for real throughput; default just loops."""
        return [self.generate_candidates(t, src_lang, tgt_lang, n) for t in src_texts]

    @staticmethod
    def score_candidates(candidates: list[str], reference: str) -> list[float]:
        """Quality score per candidate: sentence-level ChrF against a reference
        (e.g. the corpus target side). Higher is better, range 0-100."""
        from sacrebleu.metrics import CHRF

        chrf = CHRF()
        return [chrf.sentence_score(c, [reference]).score for c in candidates]

"""Turns corpus entries + teacher candidates into DPO preference pairs.

Candidate set per source sentence = teacher n-best ∪ kNN-retrieved neighbour
translations (close-but-wrong, ideal dispreferred signal). Candidates are
ranked by sentence ChrF against the corpus reference; pairs record
quality_delta = ChrF(preferred) − ChrF(dispreferred).
"""

from __future__ import annotations

import sys
from typing import Any

from setu.preference.knn import KNNIndex
from setu.teacher.base import TeacherModel
from setu.types import CorpusEntry, PreferencePair


class PreferenceGenerator:
    def __init__(self, teacher: TeacherModel, config: dict[str, Any]):
        self.teacher = teacher
        self.config = config
        self.stats: dict[str, int] = {"entries": 0, "candidates": 0, "pairs": 0, "dropped_low_delta": 0}

    def generate(self, entries: list[CorpusEntry]) -> list[PreferencePair]:
        knn_cfg = self.config.get("knn", {})
        k = knn_cfg.get("neighbors", 3)
        index = KNNIndex(tuple(knn_cfg.get("ngram_range", (2, 4)))).fit(
            [e.src_text for e in entries]
        )

        n_teacher = self.config.get("teacher_candidates", 4)
        batch_size = self.config.get("teacher_batch_size", 8)
        max_gen_length = self.config.get("max_gen_length")
        if max_gen_length is not None and hasattr(self.teacher, "config"):
            # cap decode length for this run without mutating teacher.yaml
            self.teacher.config = {
                **self.teacher.config,
                "generation": {**self.teacher.config.get("generation", {}), "max_length": max_gen_length},
            }

        pairs: list[PreferencePair] = []
        teacher_candidates: list[list[str]] = []
        for start in range(0, len(entries), batch_size):
            chunk = entries[start:start + batch_size]
            teacher_candidates.extend(self.teacher.generate_candidates_batch(
                [e.src_text for e in chunk], chunk[0].src_lang, chunk[0].tgt_lang, n=n_teacher
            ))
            done = min(start + batch_size, len(entries))
            if done % 200 < batch_size or done == len(entries):
                print(f"[setu-prefs] teacher candidates: {done}/{len(entries)}", file=sys.stderr, flush=True)

        for i, entry in enumerate(entries):
            candidates = list(teacher_candidates[i])
            for j in index.query(entry.src_text, k, exclude=i):
                candidates.append(entries[j].tgt_text)
            # unique, order-preserving; a candidate equal to the reference is
            # legitimate (perfect teacher output) and simply scores 100
            candidates = list(dict.fromkeys(c for c in candidates if c.strip()))
            if len(candidates) < 2:
                continue

            scores = self.teacher.score_candidates(candidates, entry.tgt_text)
            ranked = sorted(zip(candidates, scores), key=lambda cs: -cs[1])
            self.stats["entries"] += 1
            self.stats["candidates"] += len(candidates)
            pairs.extend(self._pair_up(entry, ranked))

        self.stats["pairs"] = len(pairs)
        return pairs

    def _pair_up(
        self, entry: CorpusEntry, ranked: list[tuple[str, float]]
    ) -> list[PreferencePair]:
        min_delta = self.config.get("min_quality_delta", 5.0)
        best_text, best_score = ranked[0]
        if self.config.get("pairing", "best_vs_each") == "best_vs_worst":
            losers = [ranked[-1]]
        else:
            losers = ranked[1:]

        pairs = []
        for text, score in losers:
            delta = best_score - score
            if delta < min_delta:
                self.stats["dropped_low_delta"] += 1
                continue
            pairs.append(PreferencePair(
                src_text=entry.src_text,
                src_lang=entry.src_lang,
                tgt_lang=entry.tgt_lang,
                preferred_tgt=best_text,
                dispreferred_tgt=text,
                quality_delta=delta,
            ))
        return pairs

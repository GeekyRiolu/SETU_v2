"""Paired bootstrap resampling — is system A significantly better than B?

Standard MT significance test (Koehn 2004): resample the test set with
replacement many times, recompute both systems' metric on each resample, and
report how often A wins. p-value = fraction of resamples where A does NOT beat B.
Deterministic (seeded) so results are reproducible.
"""

from __future__ import annotations

import random
from typing import Callable


def _bleu(hyps: list[str], refs: list[str]) -> float:
    from sacrebleu.metrics import BLEU

    return BLEU().corpus_score(hyps, [refs]).score


def _chrf(hyps: list[str], refs: list[str]) -> float:
    from sacrebleu.metrics import CHRF

    return CHRF().corpus_score(hyps, [refs]).score


def paired_bootstrap(
    hyps_a: list[str],
    hyps_b: list[str],
    refs: list[str],
    metric: str = "bleu",
    n_samples: int = 1000,
    seed: int = 12345,
) -> dict:
    """Compare system A vs B on the same references. Returns each system's score,
    the delta, A's win rate over the resamples, and the p-value (1 - win_rate)."""
    if not (len(hyps_a) == len(hyps_b) == len(refs)):
        raise ValueError("hyps_a, hyps_b, refs must be the same length")
    score_fn: Callable = _bleu if metric == "bleu" else _chrf

    full_a, full_b = score_fn(hyps_a, refs), score_fn(hyps_b, refs)
    rng = random.Random(seed)
    n = len(refs)
    wins = 0
    for _ in range(n_samples):
        idx = [rng.randrange(n) for _ in range(n)]
        ra = [refs[i] for i in idx]
        a = score_fn([hyps_a[i] for i in idx], ra)
        b = score_fn([hyps_b[i] for i in idx], ra)
        if a > b:
            wins += 1
    win_rate = wins / n_samples
    return {
        "metric": metric,
        "system_a": round(full_a, 2),
        "system_b": round(full_b, 2),
        "delta": round(full_a - full_b, 2),
        "a_win_rate": win_rate,
        "p_value": round(1.0 - win_rate, 4),
        "significant_at_0.05": win_rate >= 0.95,
        "n_samples": n_samples,
    }

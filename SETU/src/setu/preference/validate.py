"""Automated sanity checks on preference data.

Bad preference data poisons DPO quietly — this validator runs after every
generation batch and must pass before pairs are written to disk.
"""

from __future__ import annotations

from setu.teacher.base import TeacherModel
from setu.types import PreferencePair


class PreferenceValidationError(ValueError):
    pass


def validate_pairs(pairs: list[PreferencePair]) -> dict[str, float]:
    """Raises PreferenceValidationError on any violation; returns summary stats.

    Checks, per pair:
      - preferred ChrF strictly exceeds dispreferred ChrF is encoded as
        quality_delta > 0 (recomputed spot check below)
      - preferred and dispreferred differ
      - no empty texts
    """
    if not pairs:
        raise PreferenceValidationError("no preference pairs generated")

    for i, p in enumerate(pairs):
        if p.quality_delta <= 0:
            raise PreferenceValidationError(
                f"pair {i}: quality_delta {p.quality_delta} <= 0 "
                f"(preferred must out-score dispreferred)"
            )
        if p.preferred_tgt == p.dispreferred_tgt:
            raise PreferenceValidationError(f"pair {i}: preferred == dispreferred")
        if not (p.src_text.strip() and p.preferred_tgt.strip() and p.dispreferred_tgt.strip()):
            raise PreferenceValidationError(f"pair {i}: empty text field")

    deltas = sorted(p.quality_delta for p in pairs)
    n = len(deltas)
    return {
        "pairs": n,
        "delta_min": deltas[0],
        "delta_p50": deltas[n // 2],
        "delta_p90": deltas[int(n * 0.9)],
        "delta_max": deltas[-1],
        "delta_mean": sum(deltas) / n,
    }


def spot_check_chrf(pairs: list[PreferencePair], references: dict[str, str], sample: int = 20) -> None:
    """Recompute ChrF for a sample and confirm preferred > dispreferred against
    the true reference. references maps src_text -> reference target."""
    step = max(1, len(pairs) // sample)
    for p in pairs[::step]:
        ref = references.get(p.src_text)
        if ref is None:
            continue
        pref_score, dispref_score = TeacherModel.score_candidates(
            [p.preferred_tgt, p.dispreferred_tgt], ref
        )
        if pref_score <= dispref_score:
            raise PreferenceValidationError(
                f"spot check failed: ChrF(preferred)={pref_score:.2f} <= "
                f"ChrF(dispreferred)={dispref_score:.2f} for src {p.src_text[:60]!r}"
            )

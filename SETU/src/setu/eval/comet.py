"""COMET scoring — the learned MT metric reviewers now expect alongside BLEU/chrF.

Optional (heavy) dependency: `pip install -e ".[comet]"`. The model (~2 GB) is
downloaded on first use and runs best on a GPU. Kept behind an import guard so
the rest of the eval harness works without it.
"""

from __future__ import annotations


def comet_available() -> bool:
    try:
        import comet  # noqa: F401
        return True
    except ImportError:
        return False


def comet_score(
    sources: list[str],
    hypotheses: list[str],
    references: list[str],
    model: str = "Unbabel/wmt22-comet-da",
    gpus: int | None = None,
) -> dict:
    """Reference-based COMET. Returns the system score (0-1) and per-sentence scores.
    `gpus=None` auto-uses a GPU if torch sees one."""
    from comet import download_model, load_from_checkpoint

    if gpus is None:
        try:
            import torch

            gpus = 1 if torch.cuda.is_available() else 0
        except ImportError:
            gpus = 0

    ckpt = download_model(model)
    scorer = load_from_checkpoint(ckpt)
    data = [{"src": s, "mt": h, "ref": r} for s, h, r in zip(sources, hypotheses, references)]
    out = scorer.predict(data, gpus=gpus, progress_bar=False)
    return {"comet": round(float(out.system_score), 4), "model": model, "scores": list(out.scores)}

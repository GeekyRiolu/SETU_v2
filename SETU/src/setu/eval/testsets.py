"""Standard MT test-set loaders (for paper-grade eval).

FLORES-200 and IN22 use exactly SETU's FLORES language codes (`hin_Deva`,
`eng_Latn`, ...), so a `pair` maps straight onto their per-language configs. Each
loader returns aligned `(sources, references)` for the requested direction.
"""

from __future__ import annotations


def _text_field(record: dict) -> str:
    """FLORES variants store the sentence under 'sentence' (facebook/flores) or
    'text' (openlanguagedata/flores_plus)."""
    for k in ("sentence", "text"):
        if k in record:
            return k
    raise KeyError(f"no sentence/text field in FLORES record: {list(record)}")


def load_flores(
    pair: str,
    split: str = "devtest",
    dataset: str = "facebook/flores",
) -> tuple[list[str], list[str]]:
    """Aligned (sources, references) for `pair` from FLORES-200.

    Loads the source and target languages as separate per-language configs and
    zips them by index (FLORES is sentence-aligned across all languages).
    split: "dev" (997) or "devtest" (1012).
    """
    from datasets import load_dataset

    src_flores, tgt_flores = pair.split("-")
    src_ds = load_dataset(dataset, src_flores, split=split)
    tgt_ds = load_dataset(dataset, tgt_flores, split=split)
    if len(src_ds) != len(tgt_ds):
        raise ValueError(f"FLORES src/tgt length mismatch: {len(src_ds)} vs {len(tgt_ds)}")
    sf, tf = _text_field(src_ds[0]), _text_field(tgt_ds[0])
    return [r[sf] for r in src_ds], [r[tf] for r in tgt_ds]


def load_in22(
    pair: str,
    subset: str = "conv",
    dataset: str = "ai4bharat/IN22-Conv",
) -> tuple[list[str], list[str]]:
    """Aligned (sources, references) from IN22 (IndicTrans2's test set).

    subset: "conv" (conversational) or "gen" (general). IN22 may be gated on HF —
    accept its terms + `huggingface-cli login` first. Columns are FLORES codes.
    """
    from datasets import load_dataset

    src_flores, tgt_flores = pair.split("-")
    ds = load_dataset(dataset, split="test")
    cols = set(ds.column_names)
    if src_flores not in cols or tgt_flores not in cols:
        raise KeyError(
            f"IN22 has no columns {src_flores!r}/{tgt_flores!r}; available: {sorted(cols)}"
        )
    return [r[src_flores] for r in ds], [r[tgt_flores] for r in ds]


def load_testset(name: str, pair: str, split: str = "devtest") -> tuple[list[str], list[str]]:
    """Dispatch by name: 'flores' | 'in22' | 'in22-gen'."""
    if name == "flores":
        return load_flores(pair, split=split)
    if name == "in22":
        return load_in22(pair, subset="conv")
    if name == "in22-gen":
        return load_in22(pair, subset="gen", dataset="ai4bharat/IN22-Gen")
    raise ValueError(f"unknown test set {name!r} (use flores | in22 | in22-gen)")

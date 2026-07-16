"""CorpusLoader — reads configured parallel-corpus sources into CorpusEntry.

Source adapters:
  hf_stream      — HuggingFace datasets in streaming mode (BPCC, Samanantar);
                   nothing is fully downloaded, entries are drawn up to a limit
  tsv            — local tab-separated file (also used by tests)
  parallel_text  — two aligned plain-text files, one sentence per line

English↔Indic corpora store the two sides under corpus-specific fields; each
source config maps them via `fields: {eng: ..., indic: ...}` (or `columns` for
tsv). The loader orients every entry to the requested (src, tgt) direction.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from setu.config import resolve_language
from setu.types import CorpusEntry


def _hf_token_available() -> bool:
    try:
        from huggingface_hub import get_token
    except ImportError:
        return False
    return get_token() is not None


class CorpusLoader:
    def __init__(self, sources: list[dict[str, Any]], base_dir: Path | str = "."):
        self.sources = sources
        self.base_dir = Path(base_dir)
        self.skipped: list[dict[str, str]] = []

    def load(
        self, src_flores: str, tgt_flores: str, limit: int | None = None
    ) -> Iterator[tuple[str, CorpusEntry]]:
        """Yield (source_name, CorpusEntry) for the requested direction,
        drawing up to `limit` raw entries from each source."""
        self.skipped = []
        for source in self.sources:
            if source.get("requires_auth") and not _hf_token_available():
                self.skipped.append({
                    "name": source["name"],
                    "reason": f"gated dataset {source['dataset']!r} — accept its terms on "
                              "huggingface.co and run `huggingface-cli login`",
                })
                continue
            count = 0
            for eng_text, indic_text in self._iter_source(source, src_flores, tgt_flores):
                if limit is not None and count >= limit:
                    break
                entry = self._orient(
                    eng_text, indic_text, src_flores, tgt_flores, source["name"]
                )
                if entry is not None:
                    yield source["name"], entry
                    count += 1

    # --- orientation -----------------------------------------------------

    @staticmethod
    def _orient(
        eng_text: str, indic_text: str, src_flores: str, tgt_flores: str, name: str
    ) -> CorpusEntry | None:
        if not eng_text or not indic_text:
            return None
        if src_flores == "eng_Latn":
            src_text, tgt_text = eng_text, indic_text
        elif tgt_flores == "eng_Latn":
            src_text, tgt_text = indic_text, eng_text
        else:
            raise ValueError(
                f"English-pivot corpora need eng_Latn on one side, got {src_flores}-{tgt_flores}"
            )
        return CorpusEntry(
            src_lang=src_flores,
            tgt_lang=tgt_flores,
            src_text=str(src_text),
            tgt_text=str(tgt_text),
            source=name,
        )

    # --- adapters ---------------------------------------------------------

    def _iter_source(
        self, source: dict[str, Any], src_flores: str, tgt_flores: str
    ) -> Iterator[tuple[str, str]]:
        kind = source["type"]
        if kind == "hf_stream":
            yield from self._iter_hf_stream(source, src_flores, tgt_flores)
        elif kind == "hf_zip":
            yield from self._iter_hf_zip(source, src_flores, tgt_flores)
        elif kind == "tsv":
            yield from self._iter_tsv(source)
        elif kind == "parallel_text":
            yield from self._iter_parallel_text(source)
        else:
            raise ValueError(f"Unknown corpus source type: {kind!r}")

    def _iter_hf_stream(
        self, source: dict[str, Any], src_flores: str, tgt_flores: str
    ) -> Iterator[tuple[str, str]]:
        from datasets import load_dataset  # heavy import, only for real runs

        indic_flores = tgt_flores if src_flores == "eng_Latn" else src_flores
        if source.get("config_from") == "indic_iso":
            config = resolve_language(indic_flores)["iso"]
        else:
            config = source.get("config")
        fields = source["fields"]
        stream = load_dataset(source["dataset"], config, split="train", streaming=True)
        for record in stream:
            yield record[fields["eng"]], record[fields["indic"]]

    def _iter_hf_zip(
        self, source: dict[str, Any], src_flores: str, tgt_flores: str
    ) -> Iterator[tuple[str, str]]:
        """BPCC-style zip: <subset>/eng_Latn-<indic>/train.eng_Latn + train.<indic>."""
        import io
        import zipfile

        from huggingface_hub import hf_hub_download

        indic = tgt_flores if src_flores == "eng_Latn" else src_flores
        zip_path = hf_hub_download(source["dataset"], source["file"], repo_type="dataset")
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            eng_members = sorted(
                n for n in names if n.endswith(".eng_Latn") and indic in n
            )
            indic_members = sorted(
                n for n in names if n.endswith(f".{indic}") and "eng_Latn" in n
            )
            if not eng_members or not indic_members:
                sample = [n for n in names if indic in n][:10]
                raise ValueError(
                    f"No {indic} pair files found in {source['file']}; members with "
                    f"{indic!r}: {sample}"
                )
            for eng_name, indic_name in zip(eng_members, indic_members):
                with z.open(eng_name) as fe, z.open(indic_name) as fi:
                    te = io.TextIOWrapper(fe, encoding="utf-8")
                    ti = io.TextIOWrapper(fi, encoding="utf-8")
                    for eng_line, indic_line in zip(te, ti):
                        yield eng_line.rstrip("\n"), indic_line.rstrip("\n")

    def _iter_tsv(self, source: dict[str, Any]) -> Iterator[tuple[str, str]]:
        columns = source.get("columns", ["eng", "indic"])
        eng_idx, indic_idx = columns.index("eng"), columns.index("indic")
        with open(self.base_dir / source["path"], encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2:
                    continue
                yield parts[eng_idx], parts[indic_idx]

    def _iter_parallel_text(self, source: dict[str, Any]) -> Iterator[tuple[str, str]]:
        eng_path = self.base_dir / source["eng_path"]
        indic_path = self.base_dir / source["indic_path"]
        with open(eng_path, encoding="utf-8") as fe, open(indic_path, encoding="utf-8") as fi:
            for eng_line, indic_line in zip(fe, fi):
                yield eng_line.rstrip("\n"), indic_line.rstrip("\n")

"""kNN retrieval over corpus source sentences.

Char n-gram TF-IDF + cosine — script-agnostic, no model download, fast on CPU.
Used to pull the translations of similar source sentences into the candidate
set (they are usually close-but-wrong, which is exactly what DPO needs as
dispreferred signal).
"""

from __future__ import annotations


class KNNIndex:
    def __init__(self, ngram_range: tuple[int, int] = (2, 4)):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.neighbors import NearestNeighbors

        self._vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=tuple(ngram_range))
        self._nn = NearestNeighbors(metric="cosine")
        self._fitted = False

    def fit(self, texts: list[str]) -> "KNNIndex":
        matrix = self._vectorizer.fit_transform(texts)
        self._nn.fit(matrix)
        self._n = len(texts)
        self._fitted = True
        return self

    def query(self, text: str, k: int, exclude: int | None = None) -> list[int]:
        """Indices of the k nearest sources; `exclude` drops the query's own
        corpus position (its reference must never become a candidate)."""
        if not self._fitted:
            raise RuntimeError("KNNIndex.query() before fit()")
        vec = self._vectorizer.transform([text])
        n_query = min(k + (1 if exclude is not None else 0), self._n)
        _, indices = self._nn.kneighbors(vec, n_neighbors=n_query)
        result = [int(i) for i in indices[0] if exclude is None or int(i) != exclude]
        return result[:k]

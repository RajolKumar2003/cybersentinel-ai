"""
Embedding provider abstraction.

Default is `local_hashing`: a deterministic, dependency-free (numpy only)
hashing-trick bag-of-words embedder. It is genuinely free, offline, and
requires no model download — which is why it's the default and why it's the
one path actually exercised by this sandbox's tests. `sentence_transformers`
is available as a strictly-better optional upgrade (semantic, not just
lexical, similarity) when that package is installed.
"""

from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod

import numpy as np

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Filtering common stopwords matters a lot for a bag-of-words hashing
# embedder specifically: without it, words like "the"/"from"/"with" that
# appear in almost every chunk dominate the cosine similarity and swamp the
# distinctive domain terms that should actually drive retrieval. This was
# discovered by running real queries against the knowledge base and seeing
# wrong top matches — see docs/rag.md.
_STOPWORDS = frozenset(
    "a an the this that these those is are was were be been being have has had "
    "do does did will would shall should may might must can could "
    "of to in on at by for with from as into onto over under "
    "and or but if then than so not no nor "
    "it its it's they them their he she his her we us our you your i "
    "single one event source destination".split()
)


def _tokenize(text: str) -> list[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 2]


class EmbeddingProvider(ABC):
    dimension: int

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (n_texts, dimension) float32 array of L2-normalized vectors."""


class LocalHashingEmbedder(EmbeddingProvider):
    """Deterministic hashing-trick embedder — no model weights, no download,
    no network. Captures lexical overlap well; does not capture true
    semantic similarity the way a trained embedding model would. This
    tradeoff is documented in docs/rag.md rather than hidden.
    """

    def __init__(self, dimension: int = 256):
        self.dimension = dimension

    def _embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dimension, dtype=np.float32)
        tokens = _tokenize(text)
        if not tokens:
            return vec
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h // self.dimension) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.stack([self._embed_one(t) for t in texts]).astype(np.float32)


class SentenceTransformersEmbedder(EmbeddingProvider):
    """Optional real semantic embedder. Only imports sentence-transformers
    when instantiated, so the rest of the app works without it installed.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # local import by design

        self._model = SentenceTransformer(model_name)
        self.dimension = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float32)


def get_embedder(provider: str = "local_hashing", **kwargs) -> EmbeddingProvider:
    if provider == "local_hashing":
        return LocalHashingEmbedder(**kwargs)
    if provider == "sentence_transformers":
        return SentenceTransformersEmbedder(**kwargs)
    raise ValueError(f"Unknown embedding provider: {provider}")

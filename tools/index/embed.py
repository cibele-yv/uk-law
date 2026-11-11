"""Text embeddings from a small, free model that runs locally on CPU.

The model (about 70 MB) is downloaded once on first use and cached by fastembed.
Vectors are normalised, so a dot product is the cosine similarity.
"""
from functools import lru_cache

import numpy as np

MODEL = "BAAI/bge-small-en-v1.5"
# bge models expect this prefix on queries (not on documents).
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding  # imported lazily: slow to load

    return TextEmbedding(MODEL)


def embed_documents(texts: list[str]) -> np.ndarray:
    return _normalise(np.array(list(_model().embed(texts)), dtype=np.float32))


def embed_query(text: str) -> np.ndarray:
    return _normalise(np.array(list(_model().embed([QUERY_PREFIX + text])), dtype=np.float32))[0]


def _normalise(m: np.ndarray) -> np.ndarray:
    return m / np.linalg.norm(m, axis=1, keepdims=True)

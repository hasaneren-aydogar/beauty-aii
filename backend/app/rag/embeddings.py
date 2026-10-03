import hashlib
import logging
import math
import re
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings

log = logging.getLogger(__name__)


class Embedder(ABC):
    dim: int

    @abstractmethod
    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...


def _tr_lower(text: str) -> str:
    return text.replace("İ", "i").replace("I", "ı").lower()


class HashEmbedder(Embedder):
    """Offline, deterministic, lexical embedder (hashed word + char n-grams).

    No model download, good enough for dev/tests and keyword-style matching.
    Use SentenceTransformerEmbedder for real semantic search.
    """

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        words = re.findall(r"\w+", _tr_lower(text))
        feats: list[tuple[str, float]] = [(f"w:{w}", 2.0) for w in words]
        for w in words:
            padded = f"^{w}$"
            for n in (3, 4, 5):
                feats.extend((f"c:{padded[i:i + n]}", 1.0) for i in range(max(len(padded) - n + 1, 0)))
        for f, weight in feats:
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "big")
            v[h % self.dim] += weight if (h >> 63) & 1 else -weight
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str, dim: int) -> None:
        from sentence_transformers import SentenceTransformer  # optional dependency

        self.model = SentenceTransformer(model_name)
        actual = self.model.get_sentence_embedding_dimension()
        if actual != dim:
            raise RuntimeError(f"EMBEDDING_DIM={dim} but model outputs {actual}. Fix .env and recreate the DB column.")
        self.dim = dim
        self.e5 = "e5" in model_name.lower()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        if self.e5:
            texts = [f"passage: {t}" for t in texts]
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode(f"query: {text}" if self.e5 else text, normalize_embeddings=True).tolist()


@lru_cache
def get_embedder() -> Embedder:
    s = get_settings()
    if s.embedding_backend == "sentence_transformers":
        log.info("Embedding backend: sentence-transformers (%s)", s.embedding_model)
        return SentenceTransformerEmbedder(s.embedding_model, s.embedding_dim)
    log.info("Embedding backend: hash (offline, lexical)")
    return HashEmbedder(s.embedding_dim)

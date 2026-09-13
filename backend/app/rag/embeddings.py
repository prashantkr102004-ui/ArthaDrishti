import math
import re
from abc import ABC, abstractmethod

from app.core.config import settings


class EmbeddingProviderError(RuntimeError):
    pass


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def model(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def dimensions(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


class LocalHashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic local embeddings for development and tests.

    This is not a semantic production embedding model. It preserves the RAG
    architecture without requiring paid external API calls in the normal suite.
    """

    VOCABULARY = (
        "fee",
        "late",
        "payment",
        "interest",
        "rate",
        "minimum",
        "annual",
        "address",
        "cash",
        "withdrawal",
        "charge",
        "term",
        "balance",
        "outstanding",
        "statement",
        "document",
    )

    def __init__(self, model: str, dimensions: int) -> None:
        if dimensions <= 0:
            raise EmbeddingProviderError("Embedding dimensions must be positive.")
        self._model = model
        self._dimensions = dimensions

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in _tokens(text):
            canonical = _canonical_token(token)
            if canonical in self.VOCABULARY:
                vector[self.VOCABULARY.index(canonical) % self._dimensions] += 1.0

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]


def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.embedding_provider.strip().casefold()
    if provider in {"local", "mock", "development"}:
        return LocalHashingEmbeddingProvider(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
    raise EmbeddingProviderError(
        f"Embedding provider '{settings.embedding_provider}' is not available in this build."
    )


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def _canonical_token(token: str) -> str:
    if token in {"fees"}:
        return "fee"
    if token in {"charges", "charged"}:
        return "charge"
    if token in {"terms"}:
        return "term"
    if token in {"payments"}:
        return "payment"
    return token

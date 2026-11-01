"""Embedding provider abstraction with OpenAI and deterministic fake providers."""
from abc import ABC, abstractmethod
import hashlib
import math
from typing import List
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.exceptions import DocumentProcessingError


def validate_embedding(embedding: List[float], expected_dimension: int = None) -> None:
    """
    Validate embedding vector for correctness.
    
    Args:
        embedding: The embedding vector to validate
        expected_dimension: Expected dimension (defaults to settings.EMBEDDING_DIMENSION)
        
    Raises:
        DocumentProcessingError: If embedding is invalid
    """
    if expected_dimension is None:
        expected_dimension = settings.EMBEDDING_DIMENSION
    
    if not isinstance(embedding, list):
        raise DocumentProcessingError(f"Embedding must be a list, got {type(embedding).__name__}")
    
    if len(embedding) != expected_dimension:
        raise DocumentProcessingError(
            f"Embedding dimension mismatch: expected {expected_dimension}, got {len(embedding)}"
        )
    
    for i, val in enumerate(embedding):
        if not isinstance(val, (int, float)):
            raise DocumentProcessingError(f"Embedding value at index {i} is not numeric: {type(val).__name__}")
        if not math.isfinite(val):
            raise DocumentProcessingError(f"Embedding value at index {i} is not finite: {val}")


def validate_embedding_batch(embeddings: List[List[float]], expected_dimension: int = None) -> None:
    """
    Validate a batch of embedding vectors.
    
    Args:
        embeddings: List of embedding vectors to validate
        expected_dimension: Expected dimension (defaults to settings.EMBEDDING_DIMENSION)
        
    Raises:
        DocumentProcessingError: If any embedding is invalid
    """
    if not embeddings:
        raise DocumentProcessingError("Empty embedding batch")
    
    for i, emb in enumerate(embeddings):
        try:
            validate_embedding(emb, expected_dimension)
        except DocumentProcessingError as e:
            raise DocumentProcessingError(f"Invalid embedding at batch index {i}: {e}")


class BaseEmbeddingProvider(ABC):
    """Abstract interface for embedding generation."""
    
    def __init__(self, dimension: int = None):
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of strings."""
        pass
    
    def _validate_and_return(self, embedding: List[float]) -> List[float]:
        """Validate embedding and return it."""
        validate_embedding(embedding, self.dimension)
        return embedding
    
    def _validate_and_return_batch(self, embeddings: List[List[float]]) -> List[List[float]]:
        """Validate embedding batch and return it."""
        validate_embedding_batch(embeddings, self.dimension)
        return embeddings


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic pseudo-embedding generator.
    Produces repeatable normalized 1536-dimensional vectors using SHA-256 seeds.
    Enables offline unit testing, CI pipelines, and local development without paid APIs.
    """
    def __init__(self, dimension: int = 1536):
        super().__init__(dimension)

    def _generate_vector(self, text: str) -> List[float]:
        # Hash text to generate repeatable floats
        seed_hash = hashlib.sha256(text.encode("utf-8")).digest()
        vector = []
        for i in range(self.dimension):
            byte_idx = (i * 4) % len(seed_hash)
            val = seed_hash[byte_idx] / 255.0 - 0.5
            # Add semantic token bias
            if any(term in text.lower() for term in ["database", "postgres", "pool", "connection"]):
                val += 0.2 if i % 3 == 0 else -0.1
            if any(term in text.lower() for term in ["gateway", "timeout", "latency", "http", "504"]):
                val += 0.2 if i % 5 == 0 else -0.1
            if any(term in text.lower() for term in ["auth", "token", "jwt", "key", "expire"]):
                val += 0.2 if i % 7 == 0 else -0.1
            vector.append(val)
            
        # L2-normalize vector
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [round(x / norm, 6) for x in vector]

    def embed_text(self, text: str) -> List[float]:
        return self._validate_and_return(self._generate_vector(text))

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return self._validate_and_return_batch([self._generate_vector(t) for t in texts])


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI Embedding Provider using text-embedding-3-small."""
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        super().__init__()
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def embed_text(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            input=[text],
            model=self.model,
        )
        return self._validate_and_return(response.data[0].embedding)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            input=texts,
            model=self.model,
        )
        return self._validate_and_return_batch([item.embedding for item in response.data])


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Factory to retrieve configured embedding provider."""
    if settings.USE_FAKE_EMBEDDINGS or not settings.OPENAI_API_KEY:
        logger.info("Using FakeEmbeddingProvider (offline/test mode)")
        return FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    try:
        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL,
        )
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAIEmbeddingProvider: {e}. Falling back to FakeEmbeddingProvider.")
        return FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)


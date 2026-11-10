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
    def embed_batch(self, texts: List[str], batch_size: int = 256) -> List[List[float]]:
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

    def embed_batch(self, texts: List[str], batch_size: int = 256) -> List[List[float]]:
        return self._validate_and_return_batch([self._generate_vector(t) for t in texts])


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI Embedding Provider using text-embedding-3-small."""
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        super().__init__()
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def embed_text(self, text: str) -> List[float]:
        clean_text = text.strip() or " "
        response = self.client.embeddings.create(
            input=[clean_text],
            model=self.model,
        )
        return self._validate_and_return(response.data[0].embedding)

    def embed_batch(self, texts: List[str], batch_size: int = 256) -> List[List[float]]:
        """Generate embedding vectors for a batch of strings, chunked to stay within API limits."""
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk_slice = texts[i : i + batch_size]
            clean_slice = [t.strip() or " " for t in chunk_slice]

            max_retries = 3
            last_err = None
            for attempt in range(max_retries):
                try:
                    response = self.client.embeddings.create(
                        input=clean_slice,
                        model=self.model,
                    )
                    sorted_items = sorted(response.data, key=lambda x: x.index)
                    all_embeddings.extend([item.embedding for item in sorted_items])
                    break
                except Exception as e:
                    last_err = e
                    logger.warning(
                        f"Embedding batch [{i}:{i + len(clean_slice)}] attempt {attempt + 1} failed: {e}"
                    )
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1.0 * (attempt + 1))
            else:
                raise DocumentProcessingError(
                    f"Failed to generate embeddings after {max_retries} attempts: {last_err}"
                )

        return self._validate_and_return_batch(all_embeddings)


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Factory to retrieve configured embedding provider with explicit errors for missing credentials."""
    if settings.USE_FAKE_EMBEDDINGS:
        logger.info("Using FakeEmbeddingProvider (explicit offline/test mode)")
        return FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    if not settings.OPENAI_API_KEY:
        raise DocumentProcessingError(
            "OpenAI is configured as embedding provider, but OPENAI_API_KEY is not set. "
            "Please configure OPENAI_API_KEY in backend/.env or set USE_FAKE_EMBEDDINGS=true for offline testing."
        )
    try:
        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL,
        )
    except Exception as e:
        logger.error(f"Failed to initialize OpenAIEmbeddingProvider: {e}")
        raise DocumentProcessingError(f"Failed to initialize OpenAIEmbeddingProvider: {e}")


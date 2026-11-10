"""Unit tests for embedding providers and vector calculations."""
import math
import pytest
from backend.app.embeddings.provider import (
    FakeEmbeddingProvider,
    validate_embedding,
    validate_embedding_batch,
    DocumentProcessingError,
)
from backend.app.repositories.vector_repo import vector_repo
from backend.app.core.config import settings


def test_fake_embedding_provider_properties():
    provider = FakeEmbeddingProvider(dimension=1536)
    vec = provider.embed_text("PostgreSQL database connection pool")
    assert len(vec) == 1536
    # Verify L2 norm is approximately 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 0.01


def test_fake_embedding_batch():
    provider = FakeEmbeddingProvider(dimension=1536)
    texts = ["Authentication token service", "API gateway latency 504", "Database replication"]
    vectors = provider.embed_batch(texts)
    assert len(vectors) == 3
    assert len(vectors[0]) == 1536


def test_embedding_batch_chunking_large_list():
    """Verify that batches larger than batch_size are handled properly."""
    provider = FakeEmbeddingProvider(dimension=1536)
    texts = [f"Text item #{i}" for i in range(600)]
    vectors = provider.embed_batch(texts, batch_size=256)
    assert len(vectors) == 600
    assert all(len(v) == 1536 for v in vectors)


def test_cosine_similarity_calculation():
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]

    # Identical vectors should have similarity 1.0
    sim_identical = vector_repo.cosine_similarity(vec_a, vec_b)
    assert abs(sim_identical - 1.0) < 1e-5

    # Orthogonal vectors should have similarity 0.0
    sim_orthogonal = vector_repo.cosine_similarity(vec_a, vec_c)
    assert abs(sim_orthogonal - 0.0) < 1e-5


def test_validate_embedding_valid():
    """Test that valid embeddings pass validation."""
    valid_embedding = [0.1] * settings.EMBEDDING_DIMENSION
    # Should not raise
    validate_embedding(valid_embedding)


def test_validate_embedding_invalid_dimension():
    """Test that embeddings with wrong dimension are rejected."""
    wrong_dim_embedding = [0.1] * (settings.EMBEDDING_DIMENSION + 100)
    with pytest.raises(DocumentProcessingError, match="dimension mismatch"):
        validate_embedding(wrong_dim_embedding)


def test_validate_embedding_non_numeric():
    """Test that non-numeric values are rejected."""
    invalid_embedding = [0.1] * (settings.EMBEDDING_DIMENSION - 1) + ["not_a_number"]
    with pytest.raises(DocumentProcessingError, match="not numeric"):
        validate_embedding(invalid_embedding)


def test_validate_embedding_non_finite():
    """Test that non-finite values (inf, nan) are rejected."""
    import math
    # Test infinity
    inf_embedding = [0.1] * (settings.EMBEDDING_DIMENSION - 1) + [float('inf')]
    with pytest.raises(DocumentProcessingError, match="not finite"):
        validate_embedding(inf_embedding)
    
    # Test NaN
    nan_embedding = [0.1] * (settings.EMBEDDING_DIMENSION - 1) + [float('nan')]
    with pytest.raises(DocumentProcessingError, match="not finite"):
        validate_embedding(nan_embedding)


def test_validate_embedding_not_a_list():
    """Test that non-list embeddings are rejected."""
    with pytest.raises(DocumentProcessingError, match="must be a list"):
        validate_embedding("not_a_list")


def test_validate_embedding_batch_valid():
    """Test that valid embedding batches pass validation."""
    valid_batch = [[0.1] * settings.EMBEDDING_DIMENSION for _ in range(5)]
    # Should not raise
    validate_embedding_batch(valid_batch)


def test_validate_embedding_batch_empty():
    """Test that empty batches are rejected."""
    with pytest.raises(DocumentProcessingError, match="Empty embedding batch"):
        validate_embedding_batch([])


def test_validate_embedding_batch_invalid_dimension():
    """Test that batches with wrong dimension are rejected."""
    invalid_batch = [[0.1] * settings.EMBEDDING_DIMENSION, [0.1] * (settings.EMBEDDING_DIMENSION + 50)]
    with pytest.raises(DocumentProcessingError, match="Invalid embedding at batch index 1"):
        validate_embedding_batch(invalid_batch)


def test_validate_embedding_batch_invalid_value():
    """Test that batches with invalid values are rejected."""
    invalid_batch = [[0.1] * settings.EMBEDDING_DIMENSION, [0.1] * (settings.EMBEDDING_DIMENSION - 1) + [float('inf')]]
    with pytest.raises(DocumentProcessingError, match="Invalid embedding at batch index 1"):
        validate_embedding_batch(invalid_batch)


def test_fake_embedding_provider_validation():
    """Test that FakeEmbeddingProvider validates its own output."""
    provider = FakeEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    vec = provider.embed_text("test")
    assert len(vec) == settings.EMBEDDING_DIMENSION
    
    batch = provider.embed_batch(["test1", "test2", "test3"])
    assert len(batch) == 3
    assert all(len(v) == settings.EMBEDDING_DIMENSION for v in batch)


def test_fake_embedding_provider_wrong_dimension_config():
    """Test that FakeEmbeddingProvider validates against its configured dimension."""
    # Create provider with custom dimension
    provider = FakeEmbeddingProvider(dimension=100)
    vec = provider.embed_text("test")
    assert len(vec) == 100  # Provider validates against its own dimension
    
    # But if we manually create a vector with wrong dimension and try to validate
    # using the global settings, it should fail
    from backend.app.embeddings.provider import validate_embedding
    from backend.app.core.config import settings
    with pytest.raises(DocumentProcessingError, match="dimension mismatch"):
        validate_embedding(vec)  # Uses global EMBEDDING_DIMENSION (1536)

